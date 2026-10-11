# Who's This Animal — Product Requirements Document

## 1. Problem

First-time pet owners often don't know their pet's exact breed, and they don't know what that breed needs: how much food per day, which food, how much exercise, what a normal day looks like. Advice online is generic, contradictory and rarely tied to the owner's country or to the shops near them.

**Who's This Animal** is a web app: the owner takes a photo of their pet, the app identifies the breed (or the species for birds), and it returns a complete care sheet tailored to that pet. Every scan is kept in the owner's history.

## 2. Target users

- **Primary:** new owners of a dog, cat or pet bird in **Algeria**, with no prior pet experience.
- **Secondary:** owners of a newly adopted animal of unknown breed who want to know what it probably is.

Users are assumed to own a phone with a camera and a modern browser. The UI is in **English**.

## 3. Goals and non-goals

### Goals
1. Identify a pet's breed from a single photo: ~120 dog breeds, 12 cat breeds and ~15 pet bird species.
2. Give a full care sheet: overview, food per day in grams, recommended food and brands sold in Algeria, daily routine, foods to avoid, health watch-outs.
3. Personalise the feeding amounts and text to the pet's profile (age, weight, sex, neutered status, activity level).
4. Show nearby pet shops and vets on a map.
5. Keep a history of every scan and a list of the owner's pets.

### Non-goals
- No veterinary diagnosis or medical advice. Every care sheet carries a disclaimer.
- No e-commerce: the app does not sell or price products online.
- No multi-language support (English only).
- No public deployment. The app runs locally with docker-compose for demos (school/portfolio project).
- No mobile native app. The web app works in mobile browsers.

## 4. Supported animals

| Species | Granularity | Source of classes |
|---|---|---|
| Dog | Breed (~120, plus extra Oxford-IIIT dog breeds) | Stanford Dogs, Oxford-IIIT Pet |
| Cat | Breed (12) | Oxford-IIIT Pet: Abyssinian, Bengal, Birman, Bombay, British Shorthair, Egyptian Mau, Maine Coon, Persian, Ragdoll, Russian Blue, Siamese, Sphynx |
| Bird | Species (15) | iNaturalist: budgerigar, cockatiel, rosy-faced lovebird, Fischer's lovebird, domestic canary, zebra finch, Gouldian finch, society finch, grey parrot, monk parakeet, rose-ringed parakeet, sun conure, green-cheeked conure, blue-and-yellow macaw, domestic pigeon |

Known gaps (see IMPLEMENTATION.md §6.6): the Algerian dog breeds Sloughi and Aidi, and the domestic shorthair / mixed-breed cat, the most common cat in Algeria.

## 5. Pages

| Page | Access | Purpose |
|---|---|---|
| Landing `/` | Public | Explains the purpose, shows "how it works" in 3 steps (Snap → Identify → Care plan), sample care sheet, sign-up / log-in buttons |
| Sign up `/signup` | Public | Email, password, password confirmation |
| Verify email `/verify-email/:uid/:token` | Public | Confirms the account from the emailed link |
| Log in `/login` | Public | Email + password |
| Forgot password `/forgot-password` | Public | Request a reset link |
| Reset password `/reset-password/:uid/:token` | Public | Set a new password |
| Workspace home `/app` | Owner | Big "Scan my pet" button, recent scans, my pets |
| Scan result `/app/scans/:id` | Owner | Identification result + care sheet + "Save as new pet" / "Attach to a pet" |
| History `/app/history` | Owner | All scans, newest first, with thumbnails |
| My pets `/app/pets` | Owner | Pet cards |
| Pet detail `/app/pets/:id` | Owner | Profile (editable), personalised care sheet, the pet's scans |
| Nearby shops `/app/shops` | Owner | Map of pet shops and vets around the owner |

## 6. The care sheet

Shown on a scan result (breed-average values) and on a pet's detail page (values personalised to that pet).

1. **Identification:** breed or species name, confidence as a percentage, photo, and the 2 runner-up guesses when confidence is moderate.
2. **Overview:** origin, size class, adult weight range, life expectancy, temperament.
3. **Food per day:**
   - Dogs and cats: daily energy (kcal), grams per day for each recommended food, and meals per day for the pet's life stage.
   - Birds: grams per day from the species table.
4. **Recommended food:** food type (e.g. "large-breed puppy dry food", "seed mix + pellets") plus product suggestions from brands sold in Algeria, with where to find them (pet shops, vets).
5. **Daily routine:** timeline of the day: meals, walks or play, training, grooming, rest, and for birds, cage time and out-of-cage time.
6. **Foods to avoid:** for example chocolate, grapes and onions for dogs, or avocado for birds.
7. **Health watch-outs:** common health issues for the breed, and when to see a vet.
8. **Personal notes:** friendly text written by the local LLM, using the pet's name and profile. If the LLM is unavailable, this section is hidden and a notice is shown.
9. **Where to buy:** "Find shops near me" button linking to the map.
10. **Disclaimer:** "This is general guidance, not veterinary advice. Consult a vet for your pet's specific needs."

## 7. Detailed scenarios

Each scenario lists the actor, preconditions, main flow, alternate and error flows, and acceptance criteria (AC).

### S1 — A visitor reads the landing page and signs up
- **Actor:** visitor. **Preconditions:** not logged in.
- **Main flow:**
  1. Visitor opens `/`. The page shows the app's purpose, the 3-step "how it works", a sample care sheet, and "Get started" / "Log in" buttons.
  2. Visitor clicks "Get started" and lands on `/signup`.
  3. Visitor enters email, password and password confirmation, then submits.
  4. System validates: email format, email not already used, passwords match, password passes Django's password validators (min 8 chars, not too common, not all numeric, not too similar to the email).
  5. System creates the account with `email_verified = false` and sends a verification email.
  6. Page shows "Check your inbox to verify your email" with a "Resend email" button.
- **Alternate / error flows:**
  - 4a. Email already registered: show "An account with this email already exists" and offer a "Log in" link.
  - 4b. Password invalid: show the specific validator messages next to the field.
  - 5a. Email sending fails: the account is still created and the page offers "Resend email".
- **AC:** an account can't be used before verification; the error messages say exactly which field is wrong; the landing page is reachable without logging in.

### S2 — Email verification
- **Actor:** new owner. **Preconditions:** account created, not verified.
- **Main flow:**
  1. Owner opens the email and clicks the link `/verify-email/:uid/:token`.
  2. Frontend sends uid + token to the API. System checks the token and sets `email_verified = true`.
  3. Page shows "Email verified" and a "Log in" button.
- **Alternate / error flows:**
  - 2a. Token expired (older than 24 h) or invalid: show "This link is invalid or expired" with a form to resend the verification email.
  - 2b. Already verified: show "Your email is already verified" with a "Log in" button.
  - Resend: the owner enters their email and the system sends a new link. The response is the same whether or not the email exists, so the form can't be used to find out which emails have accounts.
- **AC:** a used or expired link never verifies the account; resending works; the response never reveals whether an email is registered.

### S3 — Login
- **Actor:** owner. **Preconditions:** account exists.
- **Main flow:**
  1. Owner opens `/login` and enters email + password.
  2. System authenticates, starts a session and redirects to `/app`.
- **Alternate / error flows:**
  - 2a. Wrong email or password: show "Email or password is incorrect". The message doesn't say which one is wrong.
  - 2b. Correct credentials but email not verified: show "Please verify your email first" with a "Resend email" button.
  - 2c. Owner is already logged in and visits `/login`: redirect to `/app`.
- **AC:** visiting any `/app/*` route while logged out redirects to `/login` and returns the owner to the requested page after login.

### S4 — Forgot or reset password
- **Actor:** owner. **Preconditions:** none.
- **Main flow:**
  1. Owner clicks "Forgot password?" on `/login` and enters their email.
  2. System shows "If an account exists, we sent a reset link" and, if the account exists, emails the link `/reset-password/:uid/:token`.
  3. Owner opens the link and enters a new password twice.
  4. System validates the token and the password, saves the password and redirects to `/login` with "Password changed".
- **Alternate / error flows:**
  - 4a. Token invalid or expired, or already used: show "This link is invalid or expired" with a link to request a new one. Changing the password invalidates every older reset link.
  - 4b. New password fails validation: show the validator messages.
- **AC:** the response in step 2 is identical whether or not the email exists; a reset link works only once.

### S5 — Scanning a dog photo (happy path)
- **Actor:** owner. **Preconditions:** logged in.
- **Main flow:**
  1. Owner taps "Scan my pet" on `/app`. On a phone this opens the camera; on desktop it opens a file picker.
  2. Owner takes or chooses a photo (JPEG, PNG or WEBP, ≤ 10 MB). A preview is shown and the owner taps "Identify".
  3. System checks image quality, classifies the photo and stores the scan in history.
  4. Owner is taken to `/app/scans/:id`, which shows "Golden Retriever — 94%" and the care sheet with **breed-average** values: a grams-per-day range for the breed's adult weight range, meals per day, routine, food and the rest of the care sheet.
  5. The personal notes section loads a few seconds later.
  6. The page offers "Save as new pet" and "Attach to an existing pet".
- **AC:** the identification and the curated care sheet appear in under 10 s on the dev machine; the scan appears at the top of history.

### S6 — Scanning a cat; scanning a bird
- **Cat:** same as S5. Feeding uses the cat energy factors (see IMPLEMENTATION.md §7.2), and the routine includes litter box and play sessions instead of walks.
- **Bird:**
  1. Owner scans a budgie, and the result shows the **species** ("Budgerigar — 91%") rather than a breed.
  2. Food per day comes from the species table as grams/day of seed mix + pellets, plus fresh vegetables. No energy formula is used for birds.
  3. The routine covers cage cleaning, fresh water, out-of-cage time, social interaction and sleep hours (cover the cage).
- **AC:** the care sheet never shows dog-specific content (walks, kcal formulas) for a bird.

### S7 — Low confidence, or not a dog, cat or bird
- **Actor:** owner. **Preconditions:** logged in.
- **Main flow:**
  1. Owner scans a photo of, for example, a hamster or a mixed-breed dog.
  2. The model's top confidence is **below the rejection threshold**.
  3. Scan is saved with `reject_reason = low_confidence`. The page shows "We couldn't identify this animal" and tips: fill the frame with the animal, use good light, show the face and body, keep it to one animal per photo.
  4. "Try again" button.
- **Alternate flow (possible mix):** top confidence is above the rejection threshold but below the "sure" threshold, and the top 2 together are high. The page shows "Possibly a mix of Labrador Retriever and German Shepherd" with both percentages, and the care sheet uses the top guess with a visible note.
- **AC:** no care sheet is shown for a rejected scan; rejected scans still appear in history and are marked "Not recognized".

### S8 — Bad image
- **Actor:** owner.
- **Main flow:** owner uploads a photo that fails a quality check. System saves the scan with a reject reason and shows a specific message:

  | Check | Message |
  |---|---|
  | Not JPEG/PNG/WEBP, or larger than 10 MB | "Please upload a JPEG, PNG or WEBP image under 10 MB." The upload is refused before saving. |
  | File can't be decoded | "This file isn't a readable image." |
  | Shortest side < 224 px | "This photo is too small. Use a larger photo." |
  | Too blurry | "This photo is blurry. Hold still and try again." |
  | Too dark | "This photo is too dark. Try in better light." |
- **AC:** each case shows its own message; the model is never called for a rejected image.

### S9 — Saving a scan as a new pet
- **Actor:** owner. **Preconditions:** a recognised scan.
- **Main flow:**
  1. On the scan result, owner taps "Save as new pet".
  2. A form opens. The breed is prefilled and can be changed with a searchable list. Fields: name, birth date (or "approximate age" in years + months, which the app converts to a birth date), sex (male / female / unknown), neutered (yes / no), current weight in kg, activity level (low / normal / high).
  3. Owner saves. The pet is created, the scan is attached to it, and the scan photo becomes the pet's photo.
  4. Owner lands on `/app/pets/:id`, which shows the **personalised** care sheet: exact grams per day for this pet's weight, life stage and neutered status, meals per day for its age, and personal notes using its name.
- **Alternate / error flows:**
  - 2a. Weight missing or ≤ 0, or birth date in the future: validation error on the field.
  - 2b. Weight far outside the breed's range (more than 50 % above the adult max): warning "This is heavier than usual for a [breed]. Double-check the weight or ask a vet." Saving is still allowed.
- **AC:** grams per day on the pet page match the formula in IMPLEMENTATION.md §7.2 for the entered profile.

### S10 — Attaching a scan to an existing pet
- **Main flow:**
  1. On a scan result, the owner taps "Attach to an existing pet" and picks one of their pets.
  2. The scan is linked to that pet and appears in the pet's scan list.
  3. If the scan's breed differs from the pet's breed, the app asks: "Update Rex's breed to Beagle?" The owner chooses Yes or No.
- **AC:** an owner can only attach scans to their own pets.

### S11 — Editing a pet's profile
- **Main flow:**
  1. On `/app/pets/:id`, the owner edits the weight from 8 kg to 10 kg and saves.
  2. Grams per day are recalculated immediately.
  3. Personal notes are regenerated for the new profile, or loaded from cache if this exact profile was seen before.
- **Alternate flow:** the pet has a birthday and moves from "puppy" to "adult" life stage. The care sheet uses the adult factors and meals per day on the next view, with no edit needed.
- **AC:** values on the page always reflect the current profile.

### S12 — Browsing history
- **Main flow:**
  1. Owner opens `/app/history` and sees scans newest first: thumbnail, result (breed / "Not recognized"), confidence, date, linked pet name.
  2. Owner taps a scan to reopen its result page. The care sheet is rebuilt from the stored breed using current data, and the personal notes come from cache.
- **AC:** history is paginated (20 per page); an owner never sees another owner's scans.

### S13 — Finding nearby shops and vets
- **Main flow:**
  1. Owner taps "Find shops near me" on a care sheet or opens `/app/shops`.
  2. Browser asks for location permission and the owner allows it.
  3. A map centred on the owner shows pet shops and veterinarians within 5 km, with icons and a list sorted by distance. Each entry shows name, address if known, opening hours if known, distance, and an "Open in maps" link.
- **Alternate / error flows:**
  - 2a. Permission denied or unavailable: show a search box ("Enter your city or neighbourhood", e.g. "Bab Ezzouar, Alger") and centre the map on the chosen place.
  - 3a. No results within 5 km: widen automatically to 15 km, then show "No shops found nearby on OpenStreetMap" with a tip to ask a local vet. Shop data in Algeria on OpenStreetMap may be sparse.
  - 3b. Map service unreachable: show "Map service unavailable, try again later". The rest of the app keeps working.
- **AC:** the owner's location is never sent to or stored by our backend.

### S14 — Local LLM unavailable
- **Main flow:** the Ollama service is down or takes longer than 30 s. The care sheet shows every curated section normally; the personal notes section shows "Personal notes are unavailable right now". Nothing else breaks.
- **AC:** a scan never fails because of the LLM.

### S15 — Deleting a scan or pet; logout
- **Delete scan:** from history or the result page, then confirm. The scan and its image file are removed. If it was a pet's photo, the pet keeps its own copy.
- **Delete pet:** from pet detail, then confirm ("Rex will be removed. Its scans stay in your history."). The pet is removed and its scans are unlinked, not deleted.
- **Logout:** from the user menu. The session ends and the owner is redirected to `/`.
- **AC:** deletions require a confirmation; an owner can only delete their own data.

## 8. Success criteria

| Criterion | Target |
|---|---|
| Model top-1 accuracy on the held-out test set | ≥ 85 % |
| Model top-5 accuracy | ≥ 97 % |
| Scan to curated care sheet on the dev machine | < 10 s |
| Personal notes generated (uncached) | < 15 s |
| All 15 scenarios above pass in a manual demo run | 15 / 15 |
