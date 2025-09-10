# Backend Application

This directory contains the backend application for the Price Optimization AI project. It is built using FastAPI and handles API routing, authentication, and integration with various services.

## Project Structure

- `main.py`: The main entry point for the FastAPI application. It handles router imports, authentication configuration, and application creation.
- `app/apis/`: Contains subdirectories for different API modules (e.g., `competitor_scraping`, `price_optimization`). Each subdirectory is expected to have an `__init__.py` file that exposes a FastAPI `APIRouter` instance.
- `app/auth/`: Contains authentication-related logic, including user authorization.
- `app/libs/`: Contains shared libraries and utility functions, such as database interactions and product matching.
- `databutton_app/mw/`: Middleware for the Databutton application, including authentication middleware.
- `routers.json`: (Expected) A JSON file that defines the API routers and their authentication settings. This file is not version controlled and is expected to be generated or provided at runtime.

## Dependencies

The backend dependencies are managed using `poetry` and are listed in `pyproject.toml` and `requirements.txt`. Key dependencies include:

- `fastapi`: Web framework for building APIs.
- `uvicorn`: ASGI server for running the FastAPI application.
- `databutton`: (Specific to Databutton platform)
- `openai`: For AI model interactions.
- `beautifulsoup4`, `requests`, `aiohttp`, `lxml`: For web scraping.
- `gspread`, `google-auth`: For Google Sheets-based persistence.

## Setup and Running

To set up and run the backend, refer to the `install.sh` and `run.sh` scripts in this directory.

### Zero-Setup Default (Online DB)

If `DATABASE_URL` is present (already in `backend/.env`), the backend auto-uses Postgres and creates the tables on first write — no extra steps required. This works locally and when deployed online.

 - Data lives in your Postgres database and is accessible 24/7.
- Schema is created automatically if missing.
- Health: `GET /routes/health/storage`.

If `DATABASE_URL` is not set, the backend falls back to SQLite (`data.sqlite3`) for local-only persistence. You can still switch to Sheets or Airtable with envs below.

### Option A: Google Sheets (Spreadsheet UI)

Use a Google Cloud service account with Google Sheets API enabled and Editor access to your target spreadsheet.

1) Create credentials
- Create a Google Cloud project (if needed) and enable:
  - Google Sheets API
 - Google Drive API (readonly is fine)
- Create a Service Account and generate a JSON key.
- Share your Google Sheet with the service account email (as Editor):
  `your-sa@your-project.iam.gserviceaccount.com`.

2) Provide credentials via env vars (choose one)
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Absolute path to the JSON key file (recommended locally).
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Raw JSON string of the key.
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`: Base64-encoded key JSON (avoids quoting issues).
- Pair: `GOOGLE_SERVICE_ACCOUNT_EMAIL` + `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` (escape newlines as `\\n`).

Alternatively (less ideal for servers), use OAuth as a regular Google user:
- `GOOGLE_OAUTH_CREDENTIALS_FILE`: Path to OAuth client credentials JSON from Google Cloud (type Desktop or Web). On first run it prompts for consent and creates `authorized_user.json` (path override via `GOOGLE_OAUTH_TOKEN_FILE`).

3) Select the spreadsheet (choose one)
- `GOOGLE_SHEET_ID`: The ID from the URL `.../d/<ID>/edit`.
- `GOOGLE_SHEET_URL`: Full spreadsheet URL (ID is extracted automatically).
- `GOOGLE_SHEET_NAME`: Spreadsheet title (must be visible to the service account).

See `backend/.env.example` for a template.

On successful configuration, the backend creates/uses these worksheets:
- `scraping_runs`: Run metadata and progress.
- `scraped_products_run`: Per-run product history (includes `run_id`).
- `scraped_products`: Latest snapshot across runs (deduplicated by `product_url`).

#### Health check
Run the server and open `GET /routes/health/sheets` to verify connectivity. Returns spreadsheet title and the list of worksheet tabs if configured correctly.

### Option B: Airtable (Simple hosted DB + spreadsheet-like UI)

If you want a simpler hosted place to edit data directly with a spreadsheet-like UI, Airtable is a great fit. This backend supports Airtable with a single env switch.

1) Create an Airtable base and three tables with these names (or set env vars to rename):
- `scraping_runs`
- `scraped_products_run`
- `scraped_products`

2) Fields: You can let the backend create fields on-the-fly via API creates; to align types, you can manually add fields matching the headers used in code:
- `scraping_runs`: id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors
- `scraped_products_run`: run_id + all product fields in `PRODUCT_HEADERS`
- `scraped_products`: all product fields in `PRODUCT_HEADERS`

3) Set env vars:
- `STORAGE_BACKEND=airtable`
- `AIRTABLE_API_KEY=pat_...` (create from Airtable account)
- `AIRTABLE_BASE_ID=app...` (find in Airtable API docs for your base)
- Optional table name overrides:
  - `AIRTABLE_TABLE_RUNS`, `AIRTABLE_TABLE_PRODUCTS_RUN`, `AIRTABLE_TABLE_PRODUCTS`

This replaces Sheets entirely. The app will upsert by keys (id/product_url or run_id+product_url) and you can edit directly in Airtable’s UI.

## API Endpoints

API endpoints are dynamically loaded from the `app/apis/` directory. Each API module is expected to expose a FastAPI `APIRouter`. Authentication for each router can be configured via the `routers.json` file.

## Authentication

The application supports Firebase authentication. The Firebase configuration is loaded from the `DATABUTTON_EXTENSIONS` environment variable.
### Option C: SheetDB (REST API to your Google Sheet)

If you already connected a Google Sheet to SheetDB and have an endpoint, you can stream data there without managing Google credentials. Minimal setup:

- `STORAGE_BACKEND=sheetdb`
- `SHEETDB_API_URL=https://sheetdb.io/api/v1/xxxx` (your endpoint)
- Optional `SHEETDB_API_KEY=...` if your endpoint is private

Notes:
- SheetDB requires the first row (headers) to exist in the sheet before writes are allowed. If the spreadsheet is empty, create a header row or one blank record via the SheetDB UI to initialize columns.
- This backend appends rows for run progress and products; there is no deduping/upsert.
- Health: `GET /routes/health/storage` shows probe result from SheetDB.
