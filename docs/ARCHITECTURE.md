# Zorvi AI Studio: architecture

## Overview

```
Browser (Next.js, port 3000)
        |  fetch() through ONE configurable base URL (NEXT_PUBLIC_API_URL)
        |  adds "Authorization: Bearer <token>" when the person is signed in
        v
FastAPI (port 8000)
  api/        HTTP routes only: parse, check sign-in, call services, return
  schemas/    Pydantic request/response models
  services/   business logic: images, graphics, copy, AI, export, history, brand, auth, email
  core/       settings (env vars), errors, AI rate limiter
  database/   SQLite (default) or PostgreSQL, one small helper, no ORM
        |
        v
  storage/ (git-ignored): originals/, processed/, campaigns/, brand/   +  SQLite file when no DATABASE_URL
  Google Gemini (optional, server side only)
```

Two independent apps live in one monorepo. Each has its own `.env.example` and starts separately.

## Who can do what

| Area | Signed out | Signed in |
|---|---|---|
| Create Content (upload, edit photo, copy, graphics, export, demo) | yes | yes |
| Template-based copy and marketing drafts (not AI) | yes | yes |
| AI Marketing Brain, AI Photo Assistant | no (401) | yes, rate limited |
| History (saved projects) | no (401) | own projects only |
| Brand Kit and logo | no (401) | own kit only |

Routes that need an account use the `get_current_user` dependency (`app/api/auth.py`). Routes that call a paid
AI model use `get_ai_user`, which also applies the rate limit. `get_optional_user` is for open routes that add
something when signed in, such as drawing the person's own logo on a graphic.

A project or Brand Kit that belongs to someone else is answered with **404**, the same as one that does not
exist, so ids cannot be probed.

## Key design decisions

- **Thin routes, fat services.** Routes hold no image, copy or AI logic, so services are unit-testable without HTTP.
- **Originals are immutable.** Uploads get a server-generated UUID name (no user-supplied filename touches the
  filesystem, which prevents path traversal). Edits write new files.
- **Temporary uploads.** Files under `originals/` and `processed/` are removed after `FILE_TTL_HOURS`. Only a
  project the person explicitly saves keeps its own copy of the photo.
- **Honest AI labelling.** Copy providers share one interface. The default template provider is labelled
  "Template-based", never "AI". AI output is labelled only when the request really reached Gemini, and the AI
  endpoints never silently fall back to template text.
- **Secrets stay on the server.** The Gemini key is read from `backend/.env` and never sent to the browser.
- **Private images are fetched with the token.** `<img src>` cannot send an Authorization header, so the frontend
  loads saved photos, thumbnails and the logo through `fetchBlob()` (see `AuthedImage`).
- **Two databases, one interface.** `database/db.py` gives services the same `execute("... ? ...")` API on SQLite
  and PostgreSQL (placeholders are converted). Older databases are upgraded automatically on first connect.
- **Rate limits are in memory.** `core/rate_limit.py` counts per user per minute and hour, plus one daily cap for
  the whole server. Counters reset on restart and are per worker; use Redis or an upstream limiter if you scale out.

## Data model

| Table | Purpose |
|---|---|
| `users` | name, lower-cased email, scrypt password hash, `email_verified` |
| `sessions` | SHA-256 of the session token, owner, expiry (30 days) |
| `email_tokens` | SHA-256 of single-use verification / password-reset tokens |
| `brand_kits` | one row per user: brand name, colours, font, tone |
| `campaigns` | saved projects: owner (`user_id`), name, product, photo extension, JSON state |

Projects saved before accounts owned data have `user_id = NULL` after the upgrade and are no longer visible to
anyone. Their files remain in `storage/campaigns/` until you delete them.

## Backend layout

```
backend/app/
  main.py            app, CORS, security headers, optional HTTPS redirect, router wiring
  api/               auth, brand, copy, demo, export, graphics, health, history, images, marketing, photo_assistant
  core/              config.py (settings), errors.py (AppError), rate_limit.py
  database/db.py     SQLite / PostgreSQL helper and schema
  schemas/           request and response models
  services/          business logic (copywriting/ and marketing/ are packages)
  tools/check_db.py  run with: python -m app.tools.check_db
backend/tests/       pytest suite (uses a throw-away storage folder; Gemini is faked)
backend/assets/fonts bundled open-licence fonts
```

## Frontend layout

```
frontend/src/
  app/          pages (App Router): create, marketing-brain, photo-assistant, brand-kit, assets, history, auth pages
  components/   UI; RequireSignIn gates private pages, AuthedImage loads private images
  lib/          api.ts (single fetch wrapper), auth.tsx (session context), create-flow.tsx (wizard state), helpers
  types/api.ts  response types shared by the components
```

Photo Assistant products are kept in the browser's IndexedDB on purpose (they never leave the device except for
the analysis request), so they are per browser, not per account.
