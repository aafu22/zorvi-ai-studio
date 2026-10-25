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
