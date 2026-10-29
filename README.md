# Zorvi AI Studio

[![CI](https://github.com/aafu22/zorvi-ai-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/aafu22/zorvi-ai-studio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A product marketing studio for small businesses. Upload a product photo, get marketing copy, design an editable social graphic, and export everything as a ready-to-post kit.

**Live demo:** [zorvi-ai-studio.vercel.app](https://zorvi-ai-studio.vercel.app)

<!-- Add 2-3 screenshots here before publishing, e.g.:
![Create Content](docs/screenshots/create.png)
![AI Marketing Brain](docs/screenshots/marketing-brain.png)
-->

## Features

| Feature | What it does | Account needed? | Gemini key needed? |
|---|---|---|---|
| **Create Content** | Upload a product photo, edit it (background colour, resize, crop, adjust), add product details, pick a style, edit the copy, design a social graphic, export. | No | No |
| **AI Marketing Brain** | Generates captions, hashtags, headlines, product descriptions, calls to action, promo copy and content ideas. A clearly labelled template-based draft is available as a fallback. | AI: yes. Template draft: no | AI: yes. Template draft: no |
| **AI Photo Assistant** | Analyses a product photo and suggests a title, description, background, composition, lighting, framing and colour palette. | Yes | Yes |
| **My Assets** | Photo Assistant products (kept in your browser) plus your saved project photos and logo. | Saved photos and logo: yes | No |
| **Brand Kit** | Your colours, font, tone and logo, applied to new graphics and copy. | Yes | No |
| **History** | Save and reopen your projects. | Yes | No |
| **Export** | Download graphics as PNG/JPG (1080×1080, 1080×1350, 1080×1920) or a marketing-kit ZIP. | No | No |
| **Demo mode** | Loads a built-in sample product so you can try the app without uploading anything. | No | No |
| **Accounts** | Sign up, email verification, sign in, password reset. | n/a | No |

History, Brand Kit and logo belong to your account: nobody else can see or change them. The two AI features need an account and are rate limited because every call uses a paid model.

Graphics are composed from templates (Classic, Full photo, Framed) with Pillow. They are **not** AI-generated images, and the app does not label anything as AI-generated unless the request actually reached Gemini.

## Tech stack

- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Pydantic v2, Pillow
- **Database:** SQLite by default, PostgreSQL (for example [Neon](https://neon.tech)) when `DATABASE_URL` is set
- **AI:** Google Gemini via the `google-genai` SDK (optional)
- **Email:** SMTP or the [Brevo](https://www.brevo.com) API (optional; emails print to the terminal in development)

## Project structure

```
backend/      FastAPI app: api/ (routes), schemas/, services/ (logic), database/, core/ (config, errors), tests/
frontend/     Next.js app: src/app (pages), src/components, src/lib
deploy/       Caddyfile for self-hosted HTTPS
docs/         Architecture notes
sample_assets/ Demo product photo
```

Routes stay thin and all logic lives in `services/`, so it can be tested without HTTP. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Quick start

**Requirements:** Python 3.11+ (3.12 also works), Node.js 20 LTS or newer.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Check it at <http://localhost:8000/api/health> and <http://localhost:8000/docs>.

To use the AI features, set `GEMINI_API_KEY` in `backend/.env` (get one at [Google AI Studio](https://aistudio.google.com/apikey)). Everything else works without it.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local  # Windows: Copy-Item .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. Keep both terminals running.

> While `SMTP_HOST` and `BREVO_API_KEY` are empty, verification and password-reset emails are **printed in the backend terminal** with their links. Copy the link into your browser.

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Set to `production` to enable HSTS over HTTPS. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated frontend origins allowed to call the API. |
| `FRONTEND_URL` | `http://localhost:3000` | Public site address; used for links in emails. |
| `DATABASE_URL` | *(empty → SQLite)* | `postgresql://USER:PASSWORD@HOST/DB?sslmode=require`. Use this on hosts where the disk is wiped on restart. |
| `STORAGE_DIR` | `storage` | Where uploads, processed images and exports are stored. |
| `MAX_UPLOAD_MB` | `10` | Upload size limit (1–50). |
| `FILE_TTL_HOURS` | `24` | Temporary files older than this are removed on startup. |
| `GEMINI_API_KEY` | *(empty)* | Enables AI Marketing Brain and AI Photo Assistant. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model name. See Google's [model list](https://ai.google.dev/gemini-api/docs/models). |
| `GEMINI_TIMEOUT_SECONDS` | `30` | Per-request timeout (5–120). |
| `AI_REQUESTS_PER_MINUTE` / `AI_REQUESTS_PER_HOUR` | `5` / `30` | AI requests allowed per signed-in user. |
| `AI_DAILY_LIMIT_TOTAL` | `500` | Daily cap on AI requests for the whole server, as a backstop against many accounts. |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | New accounts must click the emailed link before signing in. |
| `VERIFICATION_TOKEN_HOURS` / `RESET_TOKEN_MINUTES` | `24` / `60` | Lifetime of emailed links. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_SSL` | empty / `587` | SMTP email. For Gmail use an [App password](https://myaccount.google.com/apppasswords) with `smtp.gmail.com:587`. |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` | empty | Email through Brevo's web API. Takes priority over SMTP. Useful on hosts that block SMTP ports. |
| `FORCE_HTTPS` | `false` | Redirect HTTP to HTTPS. Only enable when the site is really served over HTTPS. |
| `SAMPLE_ASSETS_DIR` | *(repo `sample_assets`)* | Folder containing the demo photo. |

### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend address. Baked into the build, so rebuild after changing it. Never put secrets in `NEXT_PUBLIC_*` variables. |
| `ENABLE_HSTS` | Optional. Send the HSTS header. Enable only on the real production domain. |

The Gemini key lives only on the backend and is never sent to the browser. Never commit `.env` files.

## Testing

```bash
# Backend (from backend/, with the venv active)
python -m pytest -q

# Frontend (from frontend/)
npm run typecheck
npm run build
```

The backend tests cover auth, access control (who may call what, and that accounts cannot see each other's data), AI rate limits, the database upgrade, copy, graphics, images, export, history, Brand Kit, security headers and the Marketing Brain (with the Gemini client faked). They never call the live Gemini API. The same checks run on every push through GitHub Actions (`.github/workflows/ci.yml`).

### Manual acceptance test

1. **Demo mode:** start the demo from the dashboard and walk through Create Content to export.
2. **Photo Assistant:** upload a JPG/PNG/WebP, run analysis, check the result is saved under **My Assets** and survives a refresh, then use **Use in Create**.
3. **Marketing Brain:** with a valid key, confirm the output is model-generated; also test the missing-key and provider-error messages.
4. **Export:** download a graphic and a marketing-kit ZIP and open them.
5. **Accounts:** sign up, verify by email link, sign in, sign out, and reset a password.
6. **Privacy:** create two accounts and confirm each one sees only its own History and Brand Kit. Signed out, confirm History, Brand Kit and the AI features ask you to sign in while Create Content still works.

## Deployment

A typical free-tier setup:

- **Frontend → Vercel.** Set the project root to `frontend` and `NEXT_PUBLIC_API_URL` to your backend's HTTPS address.
- **Backend → any Python host** (Render, Railway, Fly.io…). Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Database → Neon (PostgreSQL).** Set `DATABASE_URL`; otherwise accounts and saved data are lost whenever the host's disk is reset.
- **Email → Brevo.** Set `BREVO_API_KEY` and a verified `BREVO_SENDER_EMAIL`.

Production checklist for the backend:

```
APP_ENV=production
FORCE_HTTPS=true
CORS_ORIGINS=https://<your-frontend-domain>
FRONTEND_URL=https://<your-frontend-domain>
DATABASE_URL=postgresql://...
GEMINI_API_KEY=...
BREVO_API_KEY=...   # or the SMTP_* settings
BREVO_SENDER_EMAIL=...
```

<details>
<summary><strong>Self-hosting with Caddy (automatic HTTPS)</strong></summary>

1. Point your domain at the server and open ports 80 and 443.
2. In `backend/.env`: `APP_ENV=production`, `FORCE_HTTPS=true`, `CORS_ORIGINS` and `FRONTEND_URL` set to `https://your-domain`, plus email settings.
3. In `frontend/.env.local`: `NEXT_PUBLIC_API_URL=https://your-domain` and `ENABLE_HSTS=true`, then `npm run build`.
4. Run without `--reload`: `uvicorn app.main:app --host 127.0.0.1 --port 8000` in `backend`, and `npm start` in `frontend`.
5. From `deploy/`: `APP_DOMAIN=your-domain caddy run --config Caddyfile`.

If the proxy is on a different machine than the backend, start uvicorn with `--forwarded-allow-ips <proxy address>` so `FORCE_HTTPS` can detect the original scheme.
</details>

<details>
<summary><strong>Local HTTPS with mkcert (optional)</strong></summary>

1. Install [mkcert](https://github.com/FiloSottile/mkcert#installation) and run `mkcert -install`.
2. In the project root: `mkdir certs && mkcert -key-file certs/localhost-key.pem -cert-file certs/localhost.pem localhost 127.0.0.1` (`certs/` is git-ignored).
3. `backend/.env`: `CORS_ORIGINS=https://localhost:3000`, `FRONTEND_URL=https://localhost:3000`. Run `uvicorn app.main:app --reload --port 8000 --ssl-keyfile ../certs/localhost-key.pem --ssl-certfile ../certs/localhost.pem`.
4. `frontend/.env.local`: `NEXT_PUBLIC_API_URL=https://localhost:8000`. Run `npm run dev:https`.
5. Open <https://localhost:3000>. Frontend and backend must both use HTTPS or both use HTTP.
</details>

## Accounts and security

- Passwords are hashed with scrypt. Sessions are random tokens (valid 30 days); only a SHA-256 hash is stored server-side, and signing out deletes the session.
- Email verification links last 24 hours and are single-use. Password-reset links last 60 minutes, are single-use, and sign the account out everywhere.
- "Forgot password" and "resend verification" respond identically whether or not the email has an account, and are limited to 3 emails per address per 15 minutes.
- After 8 wrong passwords for one email, sign-in pauses for 15 minutes.
- History, Brand Kit and logo routes require sign-in and only ever return the caller's own data. Someone else's project answers 404, the same as one that does not exist.
- AI routes require sign-in and are rate limited per user (per minute and per hour) plus one daily cap for the whole server. **These limits, and the sign-in lockout above, are counted in memory: they reset when the backend restarts and are per worker.**
- The API adds security headers, can redirect to HTTPS, and sends HSTS in production.

## Privacy and storage

- Photo Assistant products, images and analysis live in **IndexedDB in the current browser**. They are not synced across devices and are lost if site data is cleared.
- Create Content drafts use browser storage. History, Brand Kit and accounts use the backend database, and every saved project and Brand Kit belongs to one account.
- Uploaded images are stored temporarily under `backend/storage/` and removed after `FILE_TTL_HOURS`.
- Images and text sent to AI features go to Google's Gemini API. Do not upload confidential content, and check Google's current data-handling terms, quotas and pricing (free-tier terms can differ from paid).

## Known limitations

- **Photo Assistant products are per browser, not per account.** They live in IndexedDB, so two people sharing one browser profile share that list.
- **Rate limits and the sign-in lockout reset on restart** and are counted per worker. For a large public service, move them to Redis or an upstream limiter.
- Sessions are kept in `localStorage`, so a cross-site-scripting bug would expose them. The app sets security headers, but treat that as a known trade-off.
- AI output can be wrong or invent details. Verify prices, discounts, claims and product descriptions before publishing.
- Text rendering for some scripts and emoji in graphics may be limited.
- Not included yet: two-factor sign-in, "sign out everywhere" on demand, account deletion, background removal.

## Upgrading an existing deployment

The database upgrades itself the first time the new backend connects (SQLite and PostgreSQL). Two things to know:

- Projects saved before accounts owned data have no owner, so they no longer appear for anyone. Their files stay in `storage/campaigns/` until you delete them. Save them again from an account if you still need them.
- The old shared Brand Kit is not migrated. Each account starts with a blank kit and sets its own.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` or `npm` not found | Install Python 3.11+ / Node.js 20+ and reopen the terminal. |
| PowerShell blocks venv activation | Use Command Prompt: `.venv\Scripts\activate.bat`. |
| Frontend can't reach backend | Check the backend is running on port 8000 and `NEXT_PUBLIC_API_URL` is set in `frontend/.env.local`. Restart `npm run dev` after changing it. |
| CORS error in the browser | Add your frontend's exact origin to `CORS_ORIGINS` and restart the backend. |
| "AI feature needs a key" | Set `GEMINI_API_KEY` in `backend/.env` and restart the backend. |
| Gemini "model not found" | Set `GEMINI_MODEL` to a model your account can use. |
| Quota / rate-limit error | Check your Google AI usage limits and retry later. |
| Accounts disappear after a deploy | The host's disk is ephemeral. Set `DATABASE_URL` to a PostgreSQL database. |
| No verification email arrives | Check the backend logs. If no email service is configured the email is printed there instead of sent. |
| Saved product missing | Use the same browser profile and origin; clearing site data erases IndexedDB. |

## Roadmap

- Account deletion and two-factor sign-in
- "Sign out everywhere" on demand
- Optional background removal
- Shared (Redis) rate limiting for multi-worker deployments

## License

[MIT](LICENSE). Bundled fonts (Bricolage Grotesque, Instrument Sans, Lora) are under the SIL Open Font License; see `backend/assets/fonts/`.
