# Zorvi AI Studio

Zorvi AI Studio is a small-business product marketing studio. It combines product-photo editing, an editable social creative builder, a template-based copy generator, an optional Gemini-powered AI Marketing Brain, and an optional Gemini vision-powered AI Product Photo Assistant.

## Feature status at a glance

- **Create Content:** upload and edit a product photo, enter product details, choose a style, edit marketing copy, design a social graphic, and export PNG/JPG or a marketing-kit ZIP.
- **AI Marketing Brain:** when a valid Gemini API key and supported model are configured, generates captions, hashtags, headlines, product descriptions, calls to action, promo copy and content ideas. A separately labelled template-based draft is available as a fallback.
- **AI Product Photo Assistant:** when Gemini is configured, analyses a product image and suggests a title, description, background, composition, lighting, framing and colour palette.
- **My Assets / Product Library:** Photo Assistant products and their analysis are saved in this browser's IndexedDB. Saved products can be reopened or handed off to Create Content.
- **Brand Kit, History, Dashboard and ZIP export:** existing features for brand defaults and project management.

AI features require a real API key and a model that is available to your Google AI account. Live Gemini calls have not been verified as part of this package's automated checks. Do not describe a result as AI-generated unless the request actually reaches the configured model.

## Requirements (Windows 10/11)

- Python 3.11 recommended (3.12 may also work)
- Node.js 20 LTS or newer, including npm
- VS Code is optional but useful
- Internet access for installing packages and calling Gemini

## 1. Set up and run the backend

Open a terminal in the `backend` folder (VS Code: Terminal → New Terminal):

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If `.venv` already exists, skip the virtual-environment creation command. If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.

Open `backend/.env` and set your key if you want the Gemini-powered features:

```dotenv
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

The model name above is the current project default, not a guarantee that Google currently offers it to your account. If it is unavailable, set `GEMINI_MODEL` to a supported model from Google's official model list: https://ai.google.dev/gemini-api/docs/models. Get API keys from https://aistudio.google.com/apikey. Never put the key in frontend code, screenshots, or Git.

Start the backend from `backend`:

```powershell
uvicorn app.main:app --reload --port 8000
```

Keep this terminal open. Verify:

- Health endpoint: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs

## 2. Set up and run the frontend

Open a **second terminal** in the `frontend` folder:

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

If `frontend/.env.local` already exists, do not overwrite it; check that it contains:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Open http://localhost:3000. Keep both backend and frontend terminals running while using the app.

## 3. Test the backend

In a terminal inside `backend`, with `.venv` activated:

```powershell
python -m pytest -q
```

The bundled backend test suite passed **173 tests** in the project packaging environment. This does not verify the live Gemini API, the browser UI, or a production deployment.

To run a frontend type check after `npm install`:

```powershell
npm run typecheck
```

To create a production frontend build:

```powershell
npm run build
```

## Suggested end-to-end acceptance test

1. Open **AI Photo Assistant**, upload a non-confidential JPG, PNG or WebP product photo, and run analysis.
2. Confirm the result contains product type, visible features, title, description and photography suggestions.
3. Revisit the page or refresh the browser; check the saved product is still available under **My Assets**.
4. Use **Use in Create** or the equivalent handoff to bring the saved photo and available details into **Create Content**.
5. Create and edit a graphic; verify that the photo, text, colours and template behave as expected.
6. Download the graphic and/or marketing-kit ZIP and open the exported files.
7. Test **AI Marketing Brain** separately with a valid key. Confirm the backend is calling Gemini and the returned text is model-generated. Test missing-key and provider-error messages too.
8. Refresh the browser and reopen saved products/projects.

## Accounts: sign up, sign in, email verification, password reset

The sidebar has **Sign in** / **Create account**. Pages: `/signup`, `/login`, `/verify-email`, `/forgot-password`, `/reset-password`.

- Accounts live in the backend SQLite database (`backend/storage/zorvi.db`). Passwords are hashed with scrypt; the plain password is never stored. An older database is upgraded automatically, and accounts that existed before verification was added count as verified.
- **Email verification:** a new account gets an email with a link (valid 24 hours, single use) and cannot sign in until it is clicked. Turn this off with `REQUIRE_EMAIL_VERIFICATION=false` in `backend/.env`.
- **Password reset:** "Forgot password?" on the sign-in page emails a link (valid 60 minutes, single use). Resetting signs the account out everywhere. The "forgot password" and "resend verification" answers are identical whether or not the email has an account, and are limited to 3 emails per address per 15 minutes.
- **Sessions:** a successful sign-in returns a token (valid 30 days) kept in the browser's `localStorage`; signing out deletes it on the server too. After 8 wrong passwords for one email, sign-in pauses for 15 minutes (resets when the backend restarts).
- API: `POST /api/auth/signup`, `login`, `logout`, `verify-email`, `resend-verification`, `forgot-password`, `reset-password`, and `GET /api/auth/me` (token sent as `Authorization: Bearer <token>`). To require sign-in on a backend route, add `user: UserOut = Depends(get_current_user)` (from `app.api.auth`).
- Existing features still work without signing in; sign-in is optional and does not yet separate one user's saved data from another's.

### Email while developing (no mail account needed)

Leave `SMTP_HOST` empty in `backend/.env`. Instead of sending, the backend **prints each email, including its link, in the backend terminal** (between `===== DEV EMAIL` lines). Copy the link into your browser to verify an account or reset a password.

### Sending real emails

Fill in the SMTP settings in `backend/.env` (see `.env.example`) and restart the backend. For Gmail, turn on 2-step verification, create an *App password* at https://myaccount.google.com/apppasswords, and use `smtp.gmail.com`, port `587`, your Gmail address as `SMTP_USERNAME` and the app password as `SMTP_PASSWORD`. Set `FRONTEND_URL` to the address people use to open the site, because that is what the email links point to. Mail failures are logged in the backend terminal and never break the page.

## HTTPS

Browsers only allow secure behaviour (and people should only type passwords) over HTTPS. The app itself does not handle certificates: local development uses a locally trusted certificate, and production uses a reverse proxy or a hosting platform that provides HTTPS. What the code does: adds security headers, can redirect HTTP to HTTPS, and sends the HSTS header in production.

### Local HTTPS (optional, Windows/macOS/Linux)

1. Install [mkcert](https://github.com/FiloSottile/mkcert#installation) (for example `choco install mkcert` or `scoop install mkcert` on Windows), then run once: `mkcert -install`
2. In the project root (the folder containing `backend` and `frontend`):
   ```powershell
   mkdir certs
   mkcert -key-file certs/localhost-key.pem -cert-file certs/localhost.pem localhost 127.0.0.1
   ```
   `certs/` is git-ignored; never commit the key.
3. `backend/.env`: set `CORS_ORIGINS=https://localhost:3000` and `FRONTEND_URL=https://localhost:3000`. Start the backend from `backend`:
   ```powershell
   uvicorn app.main:app --reload --port 8000 --ssl-keyfile ../certs/localhost-key.pem --ssl-certfile ../certs/localhost.pem
   ```
4. `frontend/.env.local`: set `NEXT_PUBLIC_API_URL=https://localhost:8000`. Start the frontend from `frontend`:
   ```powershell
   npm run dev:https
   ```
5. Open https://localhost:3000. A page served over HTTPS cannot call an `http://` backend (the browser blocks it), so the frontend and backend must both use HTTPS or both use HTTP.

### Going live with HTTPS (production)

Hosting platforms such as Render, Railway, Fly.io, Vercel and Netlify give you HTTPS automatically. On your own server, use the included [Caddy](https://caddyserver.com) setup, which gets and renews free certificates by itself:

1. Point your domain at the server and open ports 80 and 443.
2. `backend/.env`:
   ```dotenv
   APP_ENV=production
   FORCE_HTTPS=true
   CORS_ORIGINS=https://zorvi.example.com
   FRONTEND_URL=https://zorvi.example.com
   # plus the SMTP_* settings, so verification and reset emails are really sent
   ```
3. `frontend/.env.local`: `NEXT_PUBLIC_API_URL=https://zorvi.example.com` and `ENABLE_HSTS=true`, then `npm run build` (the API address is fixed into the build).
4. Run the apps without `--reload`: `uvicorn app.main:app --host 127.0.0.1 --port 8000` in `backend`, and `npm start` in `frontend`.
5. From the `deploy` folder: `APP_DOMAIN=zorvi.example.com caddy run --config Caddyfile`. The site and API then share one HTTPS address.

If the proxy runs on a different machine than the backend, start uvicorn with `--forwarded-allow-ips <proxy address>` so `FORCE_HTTPS` can tell the original request was HTTPS. HSTS makes browsers refuse plain HTTP for the whole host name for a year, so enable it only on the real production domain.

Still not included: two-factor sign-in, "sign out everywhere" on demand, account deletion, and per-user separation of saved projects. Review these before storing real customer data.

## Storage, privacy and limitations

- Photo Assistant product records, image blobs and analysis are saved in **IndexedDB in the current browser on the current device**. They are not synced across browsers/devices and may be deleted if site data is cleared.
- Create Content draft state uses browser storage; the existing History feature uses backend-side storage. Keep exported copies of important work.
- The backend stores temporary image uploads under `backend/storage/`; temporary originals follow the configured `FILE_TTL_HOURS` retention policy. Review your privacy needs before using real customer images.
- The Gemini API key stays on the backend. Do not upload confidential content to third-party AI services. Check Google's current data handling, model availability, quotas and pricing before use; free-tier limits and terms can change.
- AI output can be wrong or invent details. Verify prices, discounts, claims and product descriptions before publishing.
- Social graphics are rendered from templates and product photos using image-processing code; they are not automatically AI-generated images. Text rendering support for scripts and emoji may be limited.
- This package has not been fully verified against a live Gemini API or in a complete frontend browser run. Run the acceptance test above on your machine before treating it as production-ready.

## Troubleshooting

- **`python` not found:** install Python 3.11 and reopen VS Code.
- **`npm` not found:** install Node.js 20 LTS or newer and reopen the terminal.
- **Frontend cannot reach backend:** confirm the backend is running on port 8000 and `NEXT_PUBLIC_API_URL` is set in `frontend/.env.local`.
- **AI feature says key is missing:** set `GEMINI_API_KEY` in `backend/.env`, then restart the backend.
- **Gemini reports model not found:** update `GEMINI_MODEL` to a currently supported model.
- **Quota/rate-limit error:** check your Google AI usage limits and try again later.
- **Saved product is missing:** make sure you are using the same browser profile and origin (`localhost:3000`); clearing browser site data can erase IndexedDB records.
