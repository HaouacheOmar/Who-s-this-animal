# Who's This Animal — Implementation

How the app is built: the tech used, why, the model choice, and how each part works. Product behaviour is defined in [PRD.md](PRD.md), the architecture in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and the tables in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

## 1. Tech stack

| Layer | Tech | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite, React Router | SPA with a fast dev server; routes as listed in PRD §5 |
| UI components | shadcn/ui (Radix primitives) + Tailwind CSS v4 | Accessible components that live in our code, styled with design tokens |
| Animation | Motion (`motion/react`) | Page transitions, scan animation, result reveal, layout animations |
| Forms | Native HTML validation + the API's field errors | Forms are small; no form library needed |
| Map | Leaflet + react-leaflet, OpenStreetMap tiles | Free, no API key |
| Shop search | OSM Overpass API (`shop=pet`, `amenity=veterinary`) | Free; called from the browser |
| Geocoding fallback | OSM Nominatim | Free; used when geolocation is denied |
| Backend | Django + Django REST Framework | Auth, ORM, admin and migrations built in |
| Database | PostgreSQL 17 | Relational data + JSONB for routines and top-k results |
| Model service | Python gRPC server (`grpcio`) + `onnxruntime` (CPU) | Fast binary contract between Django and the model |
| Image processing | OpenCV (`opencv-python-headless`) | Decoding, quality checks, resizing and normalising |
| Training | PyTorch + `timm`, on the local RTX 4060 (8 GB) | Pretrained backbones, mixed precision |
| LLM | Ollama (local, GPU), default model `qwen3:8b` | Personalised care text and seed-data drafting; free and offline |
| Email (dev) | Mailpit | Catches verification and reset emails; web UI to read them |
| Orchestration | docker-compose | One command starts every service |

**FastAPI was dropped.** It and gRPC would both be ways for Django to call the model. The model service exposes gRPC only, and health is checked with the standard gRPC health service (`grpc_health.v1`).

Pin exact package versions in `requirements.txt` / `package.json` when each part is scaffolded.

## 2. Repository layout

```
client/              React app (Vite)
server/              Django project
  config/            settings, urls
  accounts/          custom User, auth API
  pets/              Pet model + API
  scans/             Scan model, upload API, gRPC client
  care/              Species, Breed, FoodProduct, CareText, feeding math, Ollama client
  fixtures/          breeds.json, foods.json (seed data)
model/
  training/          dataset prep, train, evaluate, export to ONNX
  service/           gRPC server: OpenCV checks + ONNX inference
  artifacts/         model.onnx, meta.json (git-ignored, produced by training)
proto/
  classifier.proto   shared gRPC contract
docker/
  docker-compose.yml + Dockerfiles
docs/
```

Generated gRPC stubs are built from `proto/classifier.proto` and aren't committed:
- `server/`: `python -m grpc_tools.protoc -Iscans=../proto --python_out=. --grpc_python_out=. scans/classifier.proto` (package-correct imports)
- `model/service/`: `python -m grpc_tools.protoc -I ../../proto --python_out=. --grpc_python_out=. ../../proto/classifier.proto`

## 3. Frontend

### 3.1 Styling: shadcn/ui + Tailwind v4

- Setup: `npm create vite@latest client -- --template react-ts`, then `npm i -D tailwindcss @tailwindcss/vite`, then `npx shadcn@latest init`.
- Components to add: `button card input label form dialog drawer select radio-group switch badge progress skeleton tabs avatar dropdown-menu sonner alert separator`.
- **Design direction: warm and friendly, not clinical.** A cream background, a warm terracotta primary, sage green for "healthy/ok" states, generous rounding and soft shadows. The pet photo is always the visual hero of its page.
- Tokens: shadcn CSS variables in `src/index.css`, overriding the default theme.

  | Token | Use | Value (oklch, starting point) |
  |---|---|---|
  | `--background` | page | cream `oklch(0.98 0.015 85)` |
  | `--foreground` | text | warm charcoal `oklch(0.25 0.02 50)` |
  | `--primary` | CTAs, links, active nav | terracotta `oklch(0.65 0.15 45)` |
  | `--secondary` | soft surfaces, chips | sand `oklch(0.93 0.03 80)` |
  | `--accent` | success, "healthy" badges | sage `oklch(0.72 0.08 150)` |
  | `--destructive` | delete, errors | `oklch(0.6 0.2 25)` |
  | `--radius` | cards, inputs | `1rem` |

  Check text and primary-button contrast against WCAG AA (4.5:1) once the values are final.
- Typography: **Fraunces** for display headings (rounded serif, friendly) and **Plus Jakarta Sans** for body/UI text, loaded from Google Fonts. Scale: 14 / 16 / 20 / 28 / 40 / 56 px.
- Layout: mobile-first. The workspace uses a bottom tab bar on phones (Scan, History, Pets, Shops) and a left sidebar from `md:` up.
- Light theme only. Dark mode is skipped; shadcn's variables make it a token swap if wanted later.

### 3.2 Motion (`motion/react`)

| Where | Animation |
|---|---|
| Route changes | `AnimatePresence` + fade/slide 8 px, 200 ms |
| Landing hero | headline and "how it works" steps fade up with a 100 ms stagger; sample care-sheet card floats in |
| Scan in progress | photo preview with a pulsing ring and a sweeping "scan line"; loops until the response arrives |
| Result reveal | breed name pops in (spring), confidence bar animates 0 → value, care-sheet sections stagger in |
| Personal notes | skeleton, then the text fades in when the LLM response arrives |
| History & pets grids | `layout` animation when items are added or deleted |
| Cards | subtle hover lift (`whileHover={{ y: -2 }}`) |

Wrap the app in `<MotionConfig reducedMotion="user">` so animations respect the OS "reduce motion" setting.

### 3.3 Other frontend details

- **Camera:** `<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment">`. Phones open the camera; desktops open the file picker.
- **API calls:** a small `api.ts` wrapper around `fetch` with `credentials: "include"` that sends the `X-CSRFToken` header. Skipped a data-fetching library (TanStack Query); add one if caching and refetch logic grows.
- **Dev proxy:** Vite proxies `/api` and `/media` to Django, so the browser sees a single origin and session cookies + CSRF work without CORS.

## 4. Backend (Django + DRF)

### 4.1 Auth

- Custom `accounts.User` (`db_table = "users"`), with `email` as `USERNAME_FIELD` and no username.
- `email_verified` is a separate boolean, and `is_active` stays reserved for disabling accounts. Login checks `email_verified` and returns a specific error, as PRD S3 requires.
- Tokens:
  - Reset links use Django's `default_token_generator`. It hashes the password and `last_login`, so a link dies once the password changes.
  - Verification uses a subclass of `PasswordResetTokenGenerator` that adds `email_verified` to `_make_hash_value`, so a link dies once the email is verified.
  - `PASSWORD_RESET_TIMEOUT = 86400` (24 h) applies to both.
- Session authentication + CSRF. No JWT: the SPA and the API share an origin through the proxy.
- Email: SMTP to Mailpit in dev (`EMAIL_HOST=mailpit`, port 1025).
- Password validators: Django's defaults.

### 4.2 REST endpoints

All under `/api/`. Every owner-data endpoint filters by `request.user`.

| Method | Path | Purpose |
|---|---|---|
| GET | `auth/csrf/` | Set the CSRF cookie |
| POST | `auth/register/` | Create account + send verification email |
| POST | `auth/verify-email/` | `{uid, token}` |
| POST | `auth/resend-verification/` | `{email}`; same response whether or not the email exists |
| POST | `auth/login/` · `auth/logout/` | Session |
| GET | `auth/me/` | Current user |
| POST | `auth/password-reset/` · `auth/password-reset/confirm/` | Reset flow |
| POST | `scans/` | Multipart image, then classify, then return the scan + curated care sheet |
| GET | `scans/` · `scans/{id}/` | History (paginated, 20) · one scan with its care sheet |
| DELETE | `scans/{id}/` | Delete scan + file |
| POST | `scans/{id}/attach/` | `{pet_id}` |
| GET / POST | `pets/` | List / create (optionally `from_scan`) |
| GET / PATCH / DELETE | `pets/{id}/` | Pet detail with personalised care sheet |
| GET | `care-text/?scan={id}` or `?pet={id}` | LLM personal notes; returns 503 if Ollama is down |
| GET | `breeds/?search=` | Breed picker in the pet form |

The care sheet is returned inside the scan and pet responses. The LLM text is a separate request, so the page renders immediately (PRD S5 step 5).

### 4.3 Upload limits

Django validates before calling the model: size ≤ 10 MB, and the content type and Pillow-detected format must be JPEG, PNG or WEBP. Files are stored under `MEDIA_ROOT/scans/<owner_id>/<uuid>.<ext>` on a Docker volume.

## 5. Model service (gRPC + OpenCV + ONNX)

### 5.1 Contract: `proto/classifier.proto`

```proto
syntax = "proto3";
package classifier.v1;

service BreedClassifier {
  rpc Classify(ClassifyRequest) returns (ClassifyReply);
}

message ClassifyRequest {
  bytes image = 1;   // raw file bytes
  int32 top_k = 2;   // default 3
}

message Prediction {
  string label = 1;      // matches breeds.model_label
  float confidence = 2;  // softmax probability
}

message ClassifyReply {
  bool recognized = 1;
  repeated Prediction predictions = 2;
  string model_version = 3;
  string reject_reason = 4;  // "", "unreadable", "too_small", "blurry", "too_dark", "low_confidence"
  bool possible_mix = 5;     // recognized, but top1 < sure threshold and top1 + top2 >= 0.75
}
```

Django calls it with a 10 s deadline. If the service is unavailable, the API returns 503 "Identification service unavailable", and no scan is saved.

### 5.2 OpenCV pipeline

1. `cv2.imdecode` the bytes. It applies EXIF orientation itself, which matters because phone photos are often rotated. Failure → `unreadable`.
2. Shortest side < 224 px → `too_small`.
3. Brightness: mean of the grayscale image < `DARK_THRESHOLD` (start at 40) → `too_dark`.
4. Blur: variance of `cv2.Laplacian` on the grayscale image < `BLUR_THRESHOLD` (start at 60) → `blurry`.
5. Resize the short side to 256, center-crop 224, BGR → RGB, scale to [0, 1] and normalise with the mean/std from `meta.json`, HWC → NCHW float32. Each backbone has its own mean/std, so they're saved at evaluation time.

`BLUR_THRESHOLD` and `DARK_THRESHOLD` are environment variables, tuned on real phone photos.

### 5.3 Inference and decision

- `onnxruntime` on CPU, with one session loaded at startup. `meta.json` holds the labels (index → `model_label`), mean/std, thresholds and `model_version`.
- Softmax → top-k.
- `top1 < REJECT_THRESHOLD` → `recognized=false, reject_reason=low_confidence`.
- `top1 < SURE_THRESHOLD` and `top1 + top2 ≥ 0.75` → recognized with `possible_mix=true` (PRD S7).
- Both thresholds are picked on the validation set (§6.4) and stored in `meta.json`. Environment variables override them. The thresholds live only in the model service.

Training code: `model/training/` (`prepare_data.py`, `train.py`, `evaluate.py`, `compare.py`). Service: `model/service/server.py`, tested by `test_server.py`.

## 6. Model selection

### 6.1 Classes and data

| Group | Source | Classes | Images |
|---|---|---|---|
| Dogs | Stanford Dogs | 120 | ~20.6 k |
| Dogs (extra) + cats | Oxford-IIIT Pet | 25 dog + 12 cat; dog breeds already in Stanford Dogs are merged | ~7.4 k |
| Birds | iNaturalist, research-grade observations, CC-licensed only | 15 (list in PRD §4) | ~300–500 per species |
| Out-of-distribution (for threshold tuning only) | Other animals and non-animal images, e.g. COCO or Open Images | not a class | ~2 k |

That's about 150 classes. Labels are snake_case `model_label`s (e.g. `dog_golden_retriever`, `cat_maine_coon`, `bird_budgerigar`) and are the join key to `breeds.model_label`.

Splits: 70 / 15 / 15, stratified per class, with a fixed seed. The test split is touched once, for the final comparison.

**Leakage caveat:** Stanford Dogs images come from ImageNet, so ImageNet-pretrained backbones may have seen some of them. Report this next to the scores. The bird and cat classes aren't affected.

### 6.2 Candidates

| Model | Params | Why it's a candidate |
|---|---|---|
| **ConvNeXt-Tiny** (`convnext_tiny.fb_in22k_ft_in1k`) | ~28 M | Strong fine-grained transfer; ImageNet-22k pretraining helps with rare classes |
| **EfficientNetV2-S** (`tf_efficientnetv2_s.in21k_ft_in1k`) | ~21 M | Smaller and faster on CPU, similar accuracy |

Both fine-tune comfortably on 8 GB with mixed precision at batch size 32–48.

### 6.3 Training recipe (same for both)

- 224 px input. Augmentation: RandomResizedCrop (0.6–1.0), horizontal flip, ColorJitter (0.2), RandAugment (n=2, m=9).
- AdamW, lr 3e-4 (head) / 1e-4 (backbone), weight decay 0.05, cosine schedule with 1 warm-up epoch, 15–20 epochs, label smoothing 0.1, AMP.
- Class-balanced sampling, because the birds have fewer images.
- Keep the best checkpoint by validation top-1 accuracy, then export to ONNX (opset 17) and verify the ONNX outputs match PyTorch within 1e-4.

### 6.4 Evaluation and choice

Both candidates were measured on the same test split (5,093 images, 152 classes), after 15 epochs each on the RTX 4060 (log: `model/runs/train_all.log`, about 25–30 min per model):

| Metric | ConvNeXt-Tiny | EfficientNetV2-S |
|---|---|---|
| Top-1 accuracy | 89.0 % | 88.6 % |
| Top-5 accuracy | 98.5 % | 98.3 % |
| Macro-F1 | 0.878 | 0.875 |
| Best validation top-1 | 89.7 % | 88.7 % |
| Worst-5 classes (F1) | eskimo dog 0.30, miniature poodle 0.52, collie 0.59, lhasa 0.67, wire-haired fox terrier 0.67 | eskimo dog 0.39, miniature poodle 0.54, collie 0.56, siberian husky 0.62, american staffordshire terrier 0.63 |
| CPU latency, ONNX, batch 1 (ms) | 28.9 | 21.0 |
| ONNX size (MB) | 106.6 | 77.6 |
| ONNX vs PyTorch max abs diff | 3.1e-6 | 2.4e-6 |

**Decision rule:** pick the higher macro-F1, unless it's within 1 point of the other model, in which case pick the one with lower CPU latency. Targets are top-1 ≥ 85 % and top-5 ≥ 97 % (PRD §8). Both models meet the targets.

**Winner: EfficientNetV2-S.** Macro-F1 differs by 0.003, which is inside the 1-point margin, so the faster model wins: 21 ms vs 29 ms on CPU, and 27 % smaller. Installed as `model/artifacts/` with version `efficientnetv2_s-20261011-nogit` (no git commit existed yet).

The weakest classes are look-alike pairs. Only 6 of the 582 test errors confuse species; the rest are same-species look-alikes. The most frequent are Eskimo dog ↔ Siberian husky (9 + 7), miniature → toy poodle (7), Staffordshire bull terrier → AmStaff (7), Yorkshire → Australian terrier (7), Cardigan → Pembroke corgi (6), Ragdoll → Birman (5), collie → Shetland sheepdog (5). Expect them in "possibly a mix" results.

**Thresholds** (picked on the validation set):
- `REJECT_THRESHOLD = 0.383`: keeps 95 % of correctly classified validation images. No out-of-distribution set was used for this run, so the share of non-pet photos it rejects hasn't been measured yet. To measure it, run `evaluate.py --ood-dir <folder of non-pet photos>`. In a spot check, a random-noise image scored 0.21 and was rejected.
- `SURE_THRESHOLD = 0.678`: above this confidence, validation precision is ≥ 97 %.

Label smoothing (0.1) keeps confidences modest, so correct answers often score 0.5–0.9 rather than 0.99. That's expected, and the thresholds were picked with it in place.

### 6.5 Model versioning

`model_version` is `<arch>-<date>-<short git sha>`. It's stored on every scan, so history shows which model made each prediction.

### 6.6 Known gaps (later)

- **Sloughi** and **Aidi**, Algerian dog breeds that aren't in Stanford Dogs: collect ~300 images each and add them as classes.
- **Domestic shorthair / mixed-breed cat**, the most common cat in Algeria: add a class so these cats aren't forced into a pedigree breed.

## 7. Care pipeline

### 7.1 Seed data (one-time)

1. `server/care/management/commands/draft_breeds.py` loops over the labels in `meta.json` and asks Ollama for a JSON object per breed matching the `breeds` columns, validated against a schema. The output is `fixtures/breeds.json`.
2. A human spot-checks at least 20 % of entries, all birds, and every weight range and energy-relevant field, against AKC, TICA, FCI and avian-vet sources.
3. `fixtures/foods.json` holds **simulated demo data** for now: 19 products under fictional brands (Atlas Pet, Sahara Nutrition, Casbah Feed, Kabylie Seeds), with typical kcal/100 g for each food type and indicative DZD prices. Each product's `where_to_find` says "[simulated demo data]", so the UI shows it. The products cover every species × life stage, and every dog size class, so each breed gets matches. Before real use, replace them with products found in Algerian pet shops and vet clinics, with kcal per 100 g taken from the packaging (candidate brands to check: Royal Canin, Purina Pro Plan, Brit, Reflex, Josera, Whiskas, Pedigree, Versele-Laga / Vitakraft for birds). Fictional brands were used so that no real product gets made-up numbers.
4. Load with `python manage.py loaddata species breeds foods`.

### 7.2 Feeding math (dogs and cats)

```
RER (kcal/day) = 70 × weight_kg ^ 0.75
MER            = RER × life_stage_factor × activity_multiplier
grams/day      = MER ÷ (food.kcal_per_100g / 100)
```

| Species | Life stage / status | Factor |
|---|---|---|
| Dog | Puppy < 4 months | 3.0 |
| Dog | Puppy 4 months – adult | 2.0 |
| Dog | Adult, neutered | 1.6 |
| Dog | Adult, intact | 1.8 |
| Dog | Senior | 1.4 |
| Cat | Kitten < 12 months | 2.5 |
| Cat | Adult, neutered | 1.2 |
| Cat | Adult, intact | 1.4 |
| Cat | Senior | 1.1 |

- Activity multiplier: low 0.9 / normal 1.0 / high 1.2.
- Adult age: dogs 12 months, large and giant breeds 18–24 months (from `breeds.adult_age_months`); cats 12 months.
- Senior age: dogs 7 years, giant breeds 5; cats 11 years.
- Without a pet profile, the care sheet shows the range for the breed's `adult_weight_min_kg`–`adult_weight_max_kg` as a neutered adult with normal activity.
- **Birds:** no formula; show `daily_food_g_min`–`daily_food_g_max` from the breed row.

This lives in one pure function, `care/feeding.py`, with one `test_feeding.py` checking a known case: a 10 kg neutered adult dog has RER ≈ 393.6 kcal and MER ≈ 629.8 kcal.

### 7.3 Personal notes (scan time)

- Prompt contents: the breed's curated fields and the computed numbers, plus the pet profile (name, age, weight, sex, neutered, activity). The instructions say: write 3 short warm paragraphs for a first-time owner in Algeria; don't change any numbers; don't give medical diagnoses.
- Cache key: `profile_hash = sha256(breed_id, pet name, age in months, weight rounded to 0.5 kg, sex, neutered, activity, PROMPT_VERSION)`. A row in `care_texts` is reused when the key matches.
- Ollama `/api/generate` with a 30 s timeout. On failure the API returns 503 and the UI hides the section (PRD S14).

## 8. Nearby shops

- Browser geolocation, or a Nominatim search for a city or neighbourhood (country code `dz`) when it's denied.
- Overpass query within 5 km, widened to 15 km if empty:
  ```
  [out:json][timeout:25];
  (nwr["shop"="pet"](around:5000,LAT,LON);
   nwr["amenity"="veterinary"](around:5000,LAT,LON););
  out center tags;
  ```
- **Fallback:** the public Overpass server is often overloaded (504s and 20 s+ responses were seen during testing). The query gives up after 12 s and falls back to Nominatim POI search inside the same box: `q=pet shop` (keeps `shop=pet`) and `q=vétérinaire` (keeps `amenity=veterinary`). The French term is needed because Algerian vets are named in French; English terms found almost none. In Bab Ezzouar this returned 21 pet shops and 11 vets within 15 km.
- The calls go straight from the browser to OSM, so the owner's location never reaches our backend.
- Respect the usage policies: Nominatim allows at most 1 request per second, and searches are debounced. "Open in maps" links to `https://www.openstreetmap.org/?mlat=..&mlon=..`.

## 9. Running locally

```
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml exec ollama ollama pull qwen3:8b
docker compose -f docker/docker-compose.yml exec server python manage.py migrate
docker compose -f docker/docker-compose.yml exec server python manage.py loaddata species breeds foods
```

| Service | URL |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:8000/api/ |
| Django admin | http://localhost:8000/admin/ |
| Mailpit | http://localhost:8025 |

Training runs outside Docker, on the host GPU, from the repo's `venv/`, with `python model/training/train.py --arch convnext_tiny` and `--arch efficientnetv2_s`, then `evaluate.py` and `export.py`.

Tests: `python manage.py test` (server), `pytest model/` (model service and feeding math).

## 10. Milestones

1. **Data & training:** dataset prep, train both candidates, evaluate, pick the winner, export to ONNX, tune thresholds.
2. **Model service:** proto, gRPC server, OpenCV checks, Docker image.
3. **Backend:** auth, models + migrations, seed data, scan/pet/care endpoints, Ollama client.
4. **Frontend:** design tokens, landing page, auth pages, workspace, care sheet, map, Motion pass.
5. **Integration:** docker-compose and an end-to-end run of all 15 PRD scenarios.
6. **Demo:** fill in the model comparison table, record a demo, polish.
