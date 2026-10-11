# Who's This Animal — System Design

Architecture and the main runtime flows. Tech choices are explained in [IMPLEMENTATION.md](IMPLEMENTATION.md) and the tables are defined in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

## 1. Components

```mermaid
flowchart LR
    subgraph Browser
        UI[React SPA<br/>shadcn/ui + Motion]
        MAP[Leaflet map]
    end

    subgraph docker-compose
        VITE[client<br/>Vite dev server :5173]
        API[server<br/>Django + DRF :8000]
        MS[model<br/>gRPC :50051<br/>OpenCV + ONNX]
        DB[(db<br/>PostgreSQL :5433 on host)]
        LLM[ollama<br/>:11434, GPU]
        MAIL[mailpit<br/>SMTP :1025 / UI :8025]
        MEDIA[(media volume)]
    end

    OSM[(OpenStreetMap<br/>tiles · Overpass · Nominatim)]

    UI -->|/api, /media via proxy| VITE --> API
    API -->|gRPC Classify| MS
    API -->|SQL| DB
    API -->|HTTP /api/generate| LLM
    API -->|SMTP| MAIL
    API --- MEDIA
    MAP -->|HTTPS| OSM
```

| Component | Responsibility | Talks to |
|---|---|---|
| React SPA | Landing page, auth pages, workspace, care sheet, map | Django (REST via proxy), OSM (direct) |
| Django | Auth, owner data, scan orchestration, feeding math, LLM prompting, email | Postgres, model service, Ollama, Mailpit |
| Model service | Image quality checks + breed classification. Stateless; no database access | Nothing outbound |
| Postgres | Users, pets, scans, curated breed and food data, LLM text cache | — |
| Ollama | Personal notes at scan time; seed drafting (offline) | — |
| Mailpit | Catches verification and reset emails in development | — |

**The model service has no database access and doesn't know about users.** It takes bytes and returns labels, so it can be retrained and replaced without touching Django, as long as the labels in `meta.json` still match `breeds.model_label` (checked by `manage.py check_labels`).

## 2. Flow: photo scan

```mermaid
sequenceDiagram
    actor O as Owner
    participant UI as React
    participant API as Django
    participant MS as Model service
    participant DB as Postgres
    participant L as Ollama

    O->>UI: take or choose photo, tap Identify
    UI->>API: POST /api/scans/ (multipart)
    API->>API: validate size ≤ 10 MB, type JPEG/PNG/WEBP
    alt invalid upload
        API-->>UI: 400 + message (nothing saved)
    end
    API->>MS: Classify(image bytes, top_k=3), deadline 10 s
    alt service down / timeout
        API-->>UI: 503 "Identification service unavailable"
    end
    MS->>MS: OpenCV decode + quality checks
    MS->>MS: preprocess + ONNX inference + thresholds
    MS-->>API: recognized, predictions, model_version, reject_reason
    API->>DB: save image to media, INSERT scans
    alt recognized
        API->>DB: SELECT breed, matching food_products
        API->>API: feeding math (breed-average range)
        API-->>UI: 201 scan + curated care sheet
        UI->>API: GET /api/care-text/?scan=id
        API->>DB: SELECT care_texts by (breed, profile_hash)
        alt cache miss
            API->>L: generate (timeout 30 s)
            L-->>API: text
            API->>DB: INSERT care_texts
        end
        API-->>UI: personal notes (or 503, so the section is hidden)
    else rejected
        API-->>UI: 201 scan with reject_reason → tips page
    end
```

The pet detail page follows the same path, from `GET /api/pets/{id}/` to `GET /api/care-text/?pet=id`, using the pet's profile instead of breed averages.

## 3. Flow: signup and email verification

```mermaid
sequenceDiagram
    actor V as Visitor
    participant UI as React
    participant API as Django
    participant DB as Postgres
    participant M as Mailpit

    V->>UI: email + password
    UI->>API: GET /api/auth/csrf/
    UI->>API: POST /api/auth/register/
    API->>API: validate email unique, password validators
    API->>DB: INSERT users (email_verified=false)
    API->>M: email with /verify-email/uid/token
    API-->>UI: 201 "check your inbox"
    V->>UI: opens link
    UI->>API: POST /api/auth/verify-email/ {uid, token}
    API->>API: check token (24 h, dies once verified)
    API->>DB: UPDATE users SET email_verified=true
    API-->>UI: 200, redirect to login
```

Password reset follows the same pattern, using `default_token_generator`: the token dies once the password changes.

## 4. Flow: nearby shops

```mermaid
sequenceDiagram
    actor O as Owner
    participant UI as React
    participant N as Nominatim
    participant OP as Overpass

    O->>UI: Find shops near me
    UI->>UI: navigator.geolocation
    alt denied
        O->>UI: types city or neighbourhood
        UI->>N: search (countrycodes=dz)
        N-->>UI: lat, lon
    end
    UI->>OP: pet shops + vets around(5 km)
    alt empty
        UI->>OP: around(15 km)
    end
    OP-->>UI: nodes / ways with tags
    UI->>UI: markers + list sorted by distance
```

Our backend is never involved in this flow, so the owner's location stays in the browser.

## 5. Deployment (local, docker-compose)

| Service | Image / build | Ports | Volumes | Depends on |
|---|---|---|---|---|
| db | `postgres:17` | 5433 → 5432 (a host Postgres already uses 5432) | `pgdata` | — |
| server | `docker/server.Dockerfile` | 8000 | `media`, `./server` (dev mount) | db, model, mailpit |
| model | `docker/model.Dockerfile` | 50051 | `./model/artifacts` (read-only) | — |
| client | `docker/client.Dockerfile` | 5173 | `./client` (dev mount) | server |
| ollama | `ollama/ollama` | 11434 | `ollama` (model weights) | — (GPU reserved via `deploy.resources.reservations.devices`) |
| mailpit | `axllent/mailpit` | 1025, 8025 | — | — |

Configuration lives in environment variables in `docker/.env`, which is git-ignored, with a committed `.env.example`. Examples: `DATABASE_URL`, `DJANGO_SECRET_KEY`, `MODEL_GRPC_ADDR`, `OLLAMA_URL`, `OLLAMA_MODEL`, `REJECT_THRESHOLD`, `SURE_THRESHOLD`, `BLUR_THRESHOLD`, `DARK_THRESHOLD`.

The GPU in Docker on Windows needs Docker Desktop with the WSL 2 backend and a current NVIDIA driver. Training runs on the host, not in Docker.

## 6. Failure handling

| Failure | Effect | User sees |
|---|---|---|
| Model service down or slow (> 10 s) | Scan isn't saved | "Identification service unavailable, try again" |
| Ollama down or slow (> 30 s) | Care sheet without personal notes | "Personal notes are unavailable right now" |
| OSM unreachable | Map page only | "Map service unavailable, try again later" |
| Mailpit / SMTP down | Account created, email not sent | "Resend email" button |
| Postgres down | API returns 500 | Generic error page |

## 7. Security basics

- **Owner scoping:** every queryset for pets, scans and care text is filtered by `request.user`. Requesting another owner's id returns 404, not 403, so ids aren't confirmed.
- **Uploads:** at most 10 MB, JPEG/PNG/WEBP only, checked by both content type and Pillow decoding. Files are stored under random UUID names, outside any executable path, and served only in development by Django; their URLs aren't guessable.
- **Auth:** session cookies (`HttpOnly`, `SameSite=Lax`), CSRF on every unsafe method, Django password validators. Login, register, resend-verification and password-reset are throttled with DRF `ScopedRateThrottle` (e.g. 10 per minute per IP).
- **Account enumeration:** the reset and resend-verification endpoints always return the same response.
- **LLM:** the prompt only contains curated fields and the pet profile. LLM output is rendered as plain text, never HTML.
- **Secrets:** `.env` is git-ignored; `DEBUG=False` outside development.
