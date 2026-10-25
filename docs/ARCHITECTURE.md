# Zorvi AI Studio: Architecture, Dependencies and Plan

## 1. Architecture

```
Browser (Next.js, port 3000)
        |  fetch() via ONE configurable base URL (NEXT_PUBLIC_API_URL)
        v
FastAPI (port 8000)
  api/        HTTP routes only: parse, validate, call services, return
  schemas/    Pydantic request/response models
  services/   business logic: image processing, copy generation, ZIP export
  core/       settings (env vars), logging, errors, security helpers
  database/   SQLite access (brand kit, history)  [Phase 5]
        |
        v
  storage/ (git-ignored): originals/, processed/, exports/
  SQLite file (git-ignored)
```

Key design decisions:

- **Two independent apps in one monorepo.** Frontend and backend start separately. Each has its own `.env.example`.
- **Thin routes, fat services.** Routes never contain image or copy logic, so services are unit-testable without HTTP.
- **Originals are immutable.** Uploads are stored under a server-generated UUID name (no user-supplied filenames touch the filesystem, which prevents path traversal). All edits write new files in `processed/`.
- **Temporary storage.** Uploaded and generated files are cleaned up after a configurable TTL (Phase 2 onward).
- **Honest AI labelling.** Copy providers implement one interface (`CopyProvider`). The default `RuleBasedProvider` is labelled "Template-based", never "AI". An LLM provider can be added later without touching routes or UI.
- **Optional heavy dependencies.** `rembg` lives in `requirements-optional.txt` and is imported lazily only when background removal is requested.
- **Auth is out of scope** for the MVP (single local user).

## 2. Dependency choices

Backend (Python 3.11 target; also works on newer versions):

| Package | Purpose | Phase |
|---|---|---|
| fastapi | API framework | 1 |
| uvicorn[standard] | ASGI server | 1 |
| pydantic / pydantic-settings | validation, env config | 1 |
| python-multipart | file uploads | 2 |
| Pillow | resize, crop, compose, text overlays | 2 |
| pytest, httpx | tests | 1 |
| opencv-python-headless | only if a feature clearly needs it (not required) | optional |
| rembg + onnxruntime | background removal, CPU only | 6, optional |

SQLite uses Python's built-in `sqlite3`, so no ORM is needed.

Frontend: Next.js (App Router) + TypeScript, Tailwind CSS, lucide-react. No UI kit and no state library; React state and small hooks are enough.

## 3. Phases

1. **Skeleton** (this milestone): dashboard shell, health endpoint, config, tests, Windows instructions.
2. Upload, validation, preview, background colour, resize/crop/adjust, download.
3. Rule-based copy generator + provider interface, editable output, copy buttons.
4. Template-based graphics (1080x1080, 1080x1350, 1080x1920), editable text/colours, export.
5. Brand Kit, history (SQLite), ZIP marketing kit, demo mode.
6. Optional rembg, hardening, README polish, deployment notes.

## 4. Target file tree (final)

```
zorvi-ai-studio/
  README.md  .gitignore
  docs/ARCHITECTURE.md
  sample_assets/
  backend/
    requirements.txt  requirements-optional.txt  .env.example
    app/
      main.py
      api/        health.py  (later: uploads.py, images.py, copy.py, graphics.py, brand.py, export.py)
      core/       config.py  errors.py
      schemas/    health.py
      services/   (later: image_service.py, copy_service.py, export_service.py)
      database/   (later: db.py)
    tests/        test_health.py
  frontend/
    package.json  .env.example  next.config.mjs  tailwind.config.ts  tsconfig.json
    src/
      app/        layout.tsx  page.tsx  globals.css  create/  brand-kit/  assets/  history/
      components/ Sidebar.tsx  AppShell.tsx  Stepper.tsx  BackendStatus.tsx  ComingSoon.tsx
      lib/        api.ts  nav.ts
      types/      api.ts
```
