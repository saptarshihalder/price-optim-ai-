import os
import json
import base64
import sqlite3
import asyncio
from typing import Iterable, TYPE_CHECKING, List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv, find_dotenv

import gspread
from google.oauth2.service_account import Credentials
import requests

if TYPE_CHECKING:  # pragma: no cover
    from app.apis.competitor_scraping import ScrapedProduct


# ---- Environment loading ----
_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path)
    except Exception:
        pass
    try:
        backend_env = Path(__file__).resolve().parents[2] / ".env"
        if backend_env.exists():
            load_dotenv(backend_env, override=False)
    except Exception:
        pass
    _ENV_LOADED = True


# ---- Storage backend selection ----
def _get_storage_backend() -> str:
    _ensure_env_loaded()
    sb = os.getenv("STORAGE_BACKEND")
    if sb:
        return sb.lower()
    # Auto-detect order: SheetDB -> Airtable -> Sheets -> Postgres -> SQLite
    if os.getenv("SHEETDB_API_URL"):
        return "sheetdb"
    if os.getenv("AIRTABLE_API_KEY") and os.getenv("AIRTABLE_BASE_ID"):
        return "airtable"
    if (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        or (os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL") and os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY"))
        or os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE")
    ):
        return "sheets"
    if os.getenv("DATABASE_URL"):
        return "postgres"
    return "sqlite"

# ---- Google Sheets helpers ----
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_gspread_client() -> gspread.Client:
    _ensure_env_loaded()
    # Optional: OAuth user flow for a regular Google account
    oauth_credentials = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE")
    if oauth_credentials:
        oauth_token = os.getenv("GOOGLE_OAUTH_TOKEN_FILE") or "authorized_user.json"
        return gspread.oauth(
            scopes=SCOPES,
            credentials_filename=oauth_credentials,
            authorized_user_filename=oauth_token,
        )
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sa_json_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    sa_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    sa_private_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY")

    creds: Credentials | None = None

    # 1) Explicit JSON string
    if not creds and sa_json:
        try:
            info = json.loads(sa_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        except json.JSONDecodeError as e:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON must be a valid JSON string") from e

    # 2) Base64 encoded JSON (sa_json_b64)
    if not creds and sa_json_b64:
        try:
            decoded = base64.b64decode(sa_json_b64).decode("utf-8")
            info = json.loads(decoded)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 is invalid") from e

    # 3) File path
    if not creds and sa_file:
        if not os.path.exists(sa_file):
            raise RuntimeError(f"Service account file not found: {sa_file}")
        creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)

    # 4) Email + private key pair (as env vars)
    if not creds and sa_email and sa_private_key:
        # Private key often has literal \n when stored in env; normalize to real newlines
        private_key = sa_private_key.replace("\\n", "\n")
        info = {
            "type": "service_account",
            "client_email": sa_email,
            "private_key": private_key,
            # token_uri optional for most environments, set explicitly for reliability
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)

    if not creds:
        raise RuntimeError(
            "Missing Google credentials. Set one of: GOOGLE_SERVICE_ACCOUNT_JSON, "
            "GOOGLE_SERVICE_ACCOUNT_JSON_BASE64, GOOGLE_SERVICE_ACCOUNT_FILE, or "
            "GOOGLE_SERVICE_ACCOUNT_EMAIL + GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY."
        )
    return gspread.authorize(creds)


def _open_spreadsheet(client: gspread.Client):
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet_url = os.getenv("GOOGLE_SHEET_URL")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME")

    # Prefer ID; derive from URL if provided
    if not sheet_id and sheet_url:
        # Typical: https://docs.google.com/spreadsheets/d/<ID>/edit#...
        parts = sheet_url.split("/d/")
        if len(parts) > 1:
            tail = parts[1]
            sheet_id = tail.split("/")[0]

    if sheet_id:
        return client.open_by_key(sheet_id)
    if sheet_name:
        return client.open(sheet_name)
    raise RuntimeError("Set GOOGLE_SHEET_ID, GOOGLE_SHEET_URL, or GOOGLE_SHEET_NAME to select a spreadsheet")


# ---- Airtable helpers ----
def _get_airtable_tables():
    """Return a dict of Airtable Table clients keyed by logical table name.

    Requires env:
      - AIRTABLE_API_KEY
      - AIRTABLE_BASE_ID
    Optional overrides for table names:
      - AIRTABLE_TABLE_PRODUCTS (default 'scraped_products')
      - AIRTABLE_TABLE_PRODUCTS_RUN (default 'scraped_products_run')
      - AIRTABLE_TABLE_RUNS (default 'scraping_runs')
    """
    _ensure_env_loaded()
    from pyairtable import Table  # type: ignore

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        raise RuntimeError("Missing Airtable config: set AIRTABLE_API_KEY and AIRTABLE_BASE_ID")

    t_products = os.getenv("AIRTABLE_TABLE_PRODUCTS", "scraped_products")
    t_products_run = os.getenv("AIRTABLE_TABLE_PRODUCTS_RUN", "scraped_products_run")
    t_runs = os.getenv("AIRTABLE_TABLE_RUNS", "scraping_runs")

    return {
        "products": Table(api_key, base_id, t_products),
        "products_run": Table(api_key, base_id, t_products_run),
        "runs": Table(api_key, base_id, t_runs),
    }


def _get_or_create_ws(spreadsheet, title: str, headers: List[str]):
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1, cols=max(26, len(headers)))
        ws.update("A1", [headers])
        return ws

    # Ensure headers exist in first row
    try:
        first_row = ws.row_values(1)
    except Exception:
        first_row = []
    if [h.strip() for h in first_row] != headers:
        ws.update("A1", [headers])
    return ws


def _iso(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _clear_and_write(ws, headers: List[str], rows: List[Dict[str, Any]]):
    # Build matrix with headers first
    matrix: List[List[Any]] = [headers]
    for r in rows:
        matrix.append([_iso(r.get(h, "")) for h in headers])
    ws.clear()
    if len(matrix) == 1:
        # write only headers
        ws.update("A1", matrix)
    else:
        ws.update("A1", matrix)


def _read_all(ws, headers: List[str]) -> List[Dict[str, Any]]:
    values = ws.get_all_values()
    if not values:
        return []
    if values[0] and [h.strip() for h in values[0]] == headers:
        start = 1
    else:
        start = 0
    out: List[Dict[str, Any]] = []
    for row in values[start:]:
        d: Dict[str, Any] = {}
        for i, h in enumerate(headers):
            d[h] = row[i] if i < len(row) else ""
        out.append(d)
    return out


# ---- SheetDB helpers ----
def _sheetdb_base() -> tuple[str, dict]:
    """Return base URL and headers for SheetDB.

    Respects env:
      - SHEETDB_API_URL (e.g., https://sheetdb.io/api/v1/xxxx)
      - SHEETDB_API_KEY (optional)

    If url not provided, uses the user's provided endpoint as a fallback.
    """
    _ensure_env_loaded()
    base = os.getenv("SHEETDB_API_URL") or "https://sheetdb.io/api/v1/ervv91ugijy7e"
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = os.getenv("SHEETDB_API_KEY")
    if api_key:
        headers["SheetDB-API-Key"] = api_key
    return base, headers


def _sheetdb_insert(sheet: str, rows: List[Dict[str, Any]]):
    base, headers = _sheetdb_base()
    # SheetDB expects { "data": [ {..}, {..} ] }
    # If the sheet is empty (no headers), API returns an error; we surface it up.
    url = base
    params = {"sheet": sheet} if sheet else None
    resp = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json={"data": rows}, params=params, timeout=20)
    if resp.status_code >= 300:
        raise RuntimeError(f"SheetDB insert failed ({resp.status_code}): {resp.text}")
    return resp.json()


def _sheetdb_select(sheet: str, query: Dict[str, Any] | None = None, limit: int | None = None) -> List[Dict[str, Any]]:
    base, headers = _sheetdb_base()
    params: Dict[str, Any] = {}
    if sheet:
        params["sheet"] = sheet
    if limit is not None:
        params["limit"] = limit
    # search[foo]=bar style
    if query:
        for k, v in query.items():
            params[f"search[{k}]"] = v
    resp = requests.get(base, headers=headers, params=params, timeout=20)
    if resp.status_code >= 300:
        raise RuntimeError(f"SheetDB select failed ({resp.status_code}): {resp.text}")
    try:
        return resp.json() or []
    except Exception:
        return []

# ---- SQLite helpers ----
def _sqlite_db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "data.sqlite3"


def _sqlite_connect() -> sqlite3.Connection:
    path = _sqlite_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_products (
            product_url TEXT PRIMARY KEY,
            store_name TEXT,
            product_id TEXT,
            title TEXT,
            price TEXT,
            currency TEXT,
            brand TEXT,
            description TEXT,
            image_url TEXT,
            in_stock TEXT,
            scraped_at TEXT,
            match_score TEXT,
            match_confidence TEXT,
            match_reasoning TEXT,
            raw_data TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_products_run (
            run_id TEXT,
            product_url TEXT,
            store_name TEXT,
            product_id TEXT,
            title TEXT,
            price TEXT,
            currency TEXT,
            brand TEXT,
            description TEXT,
            image_url TEXT,
            in_stock TEXT,
            scraped_at TEXT,
            match_score TEXT,
            match_confidence TEXT,
            match_reasoning TEXT,
            raw_data TEXT,
            PRIMARY KEY (run_id, product_url)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraping_runs (
            id TEXT PRIMARY KEY,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            target_products TEXT,
            total_stores TEXT,
            completed_stores TEXT,
            products_found TEXT,
            errors TEXT
        )
        """
    )
    conn.commit()


# ---- Postgres helpers ----
def _pg_connect():
    import psycopg2  # type: ignore
    _ensure_env_loaded()
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def _pg_ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_products (
            product_url TEXT PRIMARY KEY,
            store_name TEXT,
            product_id TEXT,
            title TEXT,
            price TEXT,
            currency TEXT,
            brand TEXT,
            description TEXT,
            image_url TEXT,
            in_stock TEXT,
            scraped_at TEXT,
            match_score TEXT,
            match_confidence TEXT,
            match_reasoning TEXT,
            raw_data TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_products_run (
            run_id TEXT,
            product_url TEXT,
            store_name TEXT,
            product_id TEXT,
            title TEXT,
            price TEXT,
            currency TEXT,
            brand TEXT,
            description TEXT,
            image_url TEXT,
            in_stock TEXT,
            scraped_at TEXT,
            match_score TEXT,
            match_confidence TEXT,
            match_reasoning TEXT,
            raw_data TEXT,
            PRIMARY KEY (run_id, product_url)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraping_runs (
            id TEXT PRIMARY KEY,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            target_products TEXT,
            total_stores TEXT,
            completed_stores TEXT,
            products_found TEXT,
            errors TEXT
        )
        """
    )
    conn.commit()


# ---- Public API (replacing DB with Sheets) ----
PRODUCT_HEADERS = [
    "store_name",
    "product_id",
    "title",
    "price",
    "currency",
    "brand",
    "description",
    "image_url",
    "product_url",
    "in_stock",
    "scraped_at",
    "match_score",
    "match_confidence",
    "match_reasoning",
    "raw_data",
]

RUN_PRODUCT_HEADERS = ["run_id"] + PRODUCT_HEADERS

RUN_HEADERS = [
    "id",
    "status",
    "started_at",
    "completed_at",
    "target_products",
    "total_stores",
    "completed_stores",
    "products_found",
    "errors",
]


def _product_to_dict(p: "ScrapedProduct") -> Dict[str, Any]:
    return {
        "store_name": p.store_name,
        "product_id": p.product_id or "",
        "title": p.title,
        "price": p.price if p.price is not None else "",
        "currency": p.currency,
        "brand": p.brand or "",
        "description": p.description or "",
        "image_url": p.image_url or "",
        "product_url": p.product_url,
        "in_stock": str(bool(p.in_stock)),
        "scraped_at": _iso(p.scraped_at),
        "match_score": p.match_score if p.match_score is not None else "",
        "match_confidence": p.match_confidence or "",
        "match_reasoning": p.match_reasoning or "",
        "raw_data": json.dumps(p.raw_data) if p.raw_data else "",
    }


async def save_scraped_products(products: Iterable["ScrapedProduct"]) -> None:
    products = list(products)
    if not products:
        return

    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                for p in products:
                    d = _product_to_dict(p)
                    cols = [
                        "product_url","store_name","product_id","title","price","currency","brand",
                        "description","image_url","in_stock","scraped_at","match_score","match_confidence",
                        "match_reasoning","raw_data"
                    ]
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products ({', '.join(cols)})
                        VALUES ({', '.join(['%s']*len(cols))})
                        ON CONFLICT (product_url) DO UPDATE SET
                        {', '.join([f"{c}=EXCLUDED.{c}" for c in cols if c != 'product_url'])}
                        """,
                        vals,
                    )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                for p in products:
                    d = _product_to_dict(p)
                    cols = [
                        "product_url","store_name","product_id","title","price","currency","brand",
                        "description","image_url","in_stock","scraped_at","match_score","match_confidence",
                        "match_reasoning","raw_data"
                    ]
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products ({', '.join(cols)})
                        VALUES ({', '.join(['?']*len(cols))})
                        ON CONFLICT(product_url) DO UPDATE SET
                        {', '.join([f"{c}=excluded.{c}" for c in cols if c != 'product_url'])}
                        """,
                        vals,
                    )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            # Append-only to keep it simple; relies on the sheet having headers
            rows = [_product_to_dict(p) for p in products]
            _sheetdb_insert("scraped_products", rows)
        await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl = tables["products"]
            # Fetch existing (could be heavy; for modest sizes it's fine)
            existing = tbl.all()
            by_url: Dict[str, Dict[str, Any]] = {}
            id_by_url: Dict[str, str] = {}
            for rec in existing:
                fields = rec.get("fields", {})
                url = fields.get("product_url")
                if url:
                    by_url[url] = fields
                    id_by_url[url] = rec["id"]
            for p in products:
                d = _product_to_dict(p)
                url = d["product_url"]
                if url in id_by_url:
                    tbl.update(id_by_url[url], d)
                else:
                    tbl.create(d)
        await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)
            ws = _get_or_create_ws(ss, "scraped_products", PRODUCT_HEADERS)
            existing = _read_all(ws, PRODUCT_HEADERS)
            by_key: Dict[str, Dict[str, Any]] = {row.get("product_url", ""): row for row in existing if row.get("product_url")}
            for p in products:
                by_key[_product_to_dict(p)["product_url"]] = _product_to_dict(p)
            merged = list(by_key.values())
            _clear_and_write(ws, PRODUCT_HEADERS, merged)
        await asyncio.to_thread(_sync_sheets)


async def save_scraped_products_for_run(products: Iterable["ScrapedProduct"], run_id: str) -> None:
    products = list(products)
    if not products:
        return

    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                # history upserts
                for p in products:
                    dprod = _product_to_dict(p)
                    d = {"run_id": run_id, **dprod}
                    cols = ["run_id"] + PRODUCT_HEADERS
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products_run ({', '.join(cols)})
                        VALUES ({', '.join(['%s']*len(cols))})
                        ON CONFLICT (run_id, product_url) DO UPDATE SET
                        {', '.join([f"{c}=EXCLUDED.{c}" for c in cols if c not in ('run_id','product_url')])}
                        """,
                        vals,
                    )
                # latest snapshot upserts
                for p in products:
                    d = _product_to_dict(p)
                    cols = [
                        "product_url","store_name","product_id","title","price","currency","brand",
                        "description","image_url","in_stock","scraped_at","match_score","match_confidence",
                        "match_reasoning","raw_data"
                    ]
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products ({', '.join(cols)})
                        VALUES ({', '.join(['%s']*len(cols))})
                        ON CONFLICT (product_url) DO UPDATE SET
                        {', '.join([f"{c}=EXCLUDED.{c}" for c in cols if c != 'product_url'])}
                        """,
                        vals,
                    )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                for p in products:
                    dprod = _product_to_dict(p)
                    d = {"run_id": run_id, **dprod}
                    cols = ["run_id"] + PRODUCT_HEADERS
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products_run ({', '.join(cols)})
                        VALUES ({', '.join(['?']*len(cols))})
                        ON CONFLICT(run_id, product_url) DO UPDATE SET
                        {', '.join([f"{c}=excluded.{c}" for c in cols if c not in ('run_id','product_url')])}
                        """,
                        vals,
                    )
                for p in products:
                    d = _product_to_dict(p)
                    cols = [
                        "product_url","store_name","product_id","title","price","currency","brand",
                        "description","image_url","in_stock","scraped_at","match_score","match_confidence",
                        "match_reasoning","raw_data"
                    ]
                    vals = [d.get(c, "") for c in cols]
                    cur.execute(
                        f"""
                        INSERT INTO scraped_products ({', '.join(cols)})
                        VALUES ({', '.join(['?']*len(cols))})
                        ON CONFLICT(product_url) DO UPDATE SET
                        {', '.join([f"{c}=excluded.{c}" for c in cols if c != 'product_url'])}
                        """,
                        vals,
                    )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            rows_hist = []
            rows_latest = []
            for p in products:
                d = _product_to_dict(p)
                rows_latest.append(d)
                rows_hist.append({"run_id": run_id, **d})
            # Append to history and latest; no upsert
            _sheetdb_insert("scraped_products_run", rows_hist)
            _sheetdb_insert("scraped_products", rows_latest)
        await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl_hist = tables["products_run"]
            tbl_latest = tables["products"]

            # Upsert history rows by (run_id, product_url)
            for p in products:
                d = {"run_id": run_id}
                d.update(_product_to_dict(p))
                formula = f"AND({{run_id}}='{run_id}',{{product_url}}='{d['product_url']}')"
                matches = tbl_hist.all(formula=formula)
                if matches:
                    tbl_hist.update(matches[0]["id"], d)
                else:
                    tbl_hist.create(d)

            # Update latest snapshot by product_url
            for p in products:
                d = _product_to_dict(p)
                formula = f"{{product_url}}='{d['product_url']}'"
                matches = tbl_latest.all(formula=formula)
                if matches:
                    tbl_latest.update(matches[0]["id"], d)
                else:
                    tbl_latest.create(d)
        await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)

            # Update run history sheet
            ws_hist = _get_or_create_ws(ss, "scraped_products_run", RUN_PRODUCT_HEADERS)
            existing = _read_all(ws_hist, RUN_PRODUCT_HEADERS)
            def key(row: Dict[str, Any]) -> tuple[str, str]:
                return (str(row.get("run_id", "")), str(row.get("product_url", "")))
            by_key: Dict[tuple[str, str], Dict[str, Any]] = {
                key(row): row for row in existing if row.get("run_id") and row.get("product_url")
            }
            for p in products:
                d = {"run_id": run_id}
                d.update(_product_to_dict(p))
                by_key[(run_id, d["product_url"])] = d
            merged = list(by_key.values())
            _clear_and_write(ws_hist, RUN_PRODUCT_HEADERS, merged)

            # Update latest snapshot sheet as well
            ws_latest = _get_or_create_ws(ss, "scraped_products", PRODUCT_HEADERS)
            existing_latest = _read_all(ws_latest, PRODUCT_HEADERS)
            latest_by_key: Dict[str, Dict[str, Any]] = {row.get("product_url", ""): row for row in existing_latest if row.get("product_url")}
            for p in products:
                latest_by_key[_product_to_dict(p)["product_url"]] = _product_to_dict(p)
            merged_latest = list(latest_by_key.values())
            _clear_and_write(ws_latest, PRODUCT_HEADERS, merged_latest)
        await asyncio.to_thread(_sync_sheets)


async def create_scraping_run(run_id: str, target_products: List[str], total_stores: int) -> None:
    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        run_id,
                        "running",
                        _iso(datetime.utcnow()),
                        "",
                        json.dumps(target_products),
                        str(total_stores),
                        "0",
                        "0",
                        json.dumps([]),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT OR IGNORE INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        "running",
                        _iso(datetime.utcnow()),
                        "",
                        json.dumps(target_products),
                        str(total_stores),
                        "0",
                        "0",
                        json.dumps([]),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            _sheetdb_insert("scraping_runs", [{
                "id": run_id,
                "status": "running",
                "started_at": _iso(datetime.utcnow()),
                "completed_at": "",
                "target_products": json.dumps(target_products),
                "total_stores": str(total_stores),
                "completed_stores": "0",
                "products_found": "0",
                "errors": json.dumps([]),
            }])
        await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl = tables["runs"]
            formula = f"{{id}}='{run_id}'"
            matches = tbl.all(formula=formula)
            if not matches:
                tbl.create({
                    "id": run_id,
                    "status": "running",
                    "started_at": _iso(datetime.utcnow()),
                    "completed_at": "",
                    "target_products": json.dumps(target_products),
                    "total_stores": str(total_stores),
                    "completed_stores": "0",
                    "products_found": "0",
                    "errors": json.dumps([]),
                })
        await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)
            ws = _get_or_create_ws(ss, "scraping_runs", RUN_HEADERS)
            rows = _read_all(ws, RUN_HEADERS)
            by_id = {r.get("id"): r for r in rows if r.get("id")}
            if run_id not in by_id:
                by_id[run_id] = {
                    "id": run_id,
                    "status": "running",
                    "started_at": _iso(datetime.utcnow()),
                    "completed_at": "",
                    "target_products": json.dumps(target_products),
                    "total_stores": str(total_stores),
                    "completed_stores": "0",
                    "products_found": "0",
                    "errors": json.dumps([]),
                }
            _clear_and_write(ws, RUN_HEADERS, list(by_id.values()))
        await asyncio.to_thread(_sync_sheets)


async def update_scraping_run(
    run_id: str,
    completed_stores: int,
    products_found: int,
    errors: List[str] | None = None,
) -> None:
    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                # read existing errors
                cur.execute("SELECT errors FROM scraping_runs WHERE id=%s", (run_id,))
                row = cur.fetchone()
                existing_errors: List[str] = []
                if row and row[0]:
                    try:
                        existing_errors = json.loads(row[0])
                    except Exception:
                        existing_errors = []
                merged_errors = json.dumps((existing_errors or []) + list(errors or []))
                cur.execute(
                    """
                    INSERT INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      completed_stores=EXCLUDED.completed_stores,
                      products_found=EXCLUDED.products_found,
                      errors=EXCLUDED.errors
                    """,
                    (
                        run_id,
                        "running",
                        _iso(datetime.utcnow()),
                        "",
                        json.dumps([]),
                        "0",
                        str(completed_stores),
                        str(products_found),
                        merged_errors,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute("SELECT errors FROM scraping_runs WHERE id=?", (run_id,))
                row = cur.fetchone()
                existing_errors: List[str] = []
                if row and row[0]:
                    try:
                        existing_errors = json.loads(row[0])
                    except Exception:
                        existing_errors = []
                merged_errors = json.dumps((existing_errors or []) + list(errors or []))
                cur.execute(
                    """
                    INSERT INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                      completed_stores=excluded.completed_stores,
                      products_found=excluded.products_found,
                      errors=excluded.errors
                    """,
                    (
                        run_id,
                        "running",
                        _iso(datetime.utcnow()),
                        "",
                        json.dumps([]),
                        "0",
                        str(completed_stores),
                        str(products_found),
                        merged_errors,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            # append a progress row (no upsert)
            row = {
                "id": run_id,
                "status": "running",
                "started_at": _iso(datetime.utcnow()),
                "completed_at": "",
                "target_products": json.dumps([]),
                "total_stores": "0",
                "completed_stores": str(completed_stores),
                "products_found": str(products_found),
                "errors": json.dumps(list(errors or [])),
            }
            _sheetdb_insert("scraping_runs", [row])
        await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl = tables["runs"]
            formula = f"{{id}}='{run_id}'"
            matches = tbl.all(formula=formula)
            if matches:
                rec = matches[0]
                fields = rec.get("fields", {})
            else:
                fields = {
                    "id": run_id,
                    "status": "running",
                    "started_at": _iso(datetime.utcnow()),
                    "completed_at": "",
                    "target_products": json.dumps([]),
                    "total_stores": "0",
                    "completed_stores": "0",
                    "products_found": "0",
                    "errors": json.dumps([]),
                }
            fields["completed_stores"] = str(completed_stores)
            fields["products_found"] = str(products_found)
            if errors:
                try:
                    existing_errors = json.loads(fields.get("errors") or "[]")
                except Exception:
                    existing_errors = []
                fields["errors"] = json.dumps((existing_errors or []) + list(errors))
            if matches:
                tbl.update(matches[0]["id"], fields)
            else:
                tbl.create(fields)
        await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)
            ws = _get_or_create_ws(ss, "scraping_runs", RUN_HEADERS)
            rows = _read_all(ws, RUN_HEADERS)
            by_id = {r.get("id"): r for r in rows if r.get("id")}
            row = by_id.get(run_id) or {
                "id": run_id,
                "status": "running",
                "started_at": _iso(datetime.utcnow()),
                "completed_at": "",
                "target_products": json.dumps([]),
                "total_stores": "0",
                "completed_stores": "0",
                "products_found": "0",
                "errors": json.dumps([]),
            }
            row["completed_stores"] = str(completed_stores)
            row["products_found"] = str(products_found)
            if errors:
                try:
                    existing_errors = json.loads(row.get("errors") or "[]")
                except Exception:
                    existing_errors = []
                row["errors"] = json.dumps((existing_errors or []) + list(errors))
            by_id[run_id] = row
            _clear_and_write(ws, RUN_HEADERS, list(by_id.values()))
        await asyncio.to_thread(_sync_sheets)


async def finalize_scraping_run(run_id: str, status: str) -> None:
    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                now = _iso(datetime.utcnow())
                cur.execute(
                    """
                    INSERT INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      status=EXCLUDED.status,
                      completed_at=EXCLUDED.completed_at
                    """,
                    (
                        run_id,
                        status,
                        now,
                        now,
                        json.dumps([]),
                        "0",
                        "0",
                        "0",
                        json.dumps([]),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                now = _iso(datetime.utcnow())
                cur.execute(
                    """
                    INSERT INTO scraping_runs (id, status, started_at, completed_at, target_products, total_stores, completed_stores, products_found, errors)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                      status=excluded.status,
                      completed_at=excluded.completed_at
                    """,
                    (run_id, status, now, now, json.dumps([]), "0", "0", "0", json.dumps([])),
                )
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            now = _iso(datetime.utcnow())
            _sheetdb_insert("scraping_runs", [{
                "id": run_id,
                "status": status,
                "started_at": now,
                "completed_at": now,
                "target_products": json.dumps([]),
                "total_stores": "0",
                "completed_stores": "0",
                "products_found": "0",
                "errors": json.dumps([]),
            }])
        await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl = tables["runs"]
            formula = f"{{id}}='{run_id}'"
            matches = tbl.all(formula=formula)
            now = _iso(datetime.utcnow())
            if matches:
                fields = matches[0].get("fields", {})
                fields["status"] = status
                fields["completed_at"] = now
                tbl.update(matches[0]["id"], fields)
            else:
                tbl.create({
                    "id": run_id,
                    "status": status,
                    "started_at": now,
                    "completed_at": now,
                    "target_products": json.dumps([]),
                    "total_stores": "0",
                    "completed_stores": "0",
                    "products_found": "0",
                    "errors": json.dumps([]),
                })
        await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)
            ws = _get_or_create_ws(ss, "scraping_runs", RUN_HEADERS)
            rows = _read_all(ws, RUN_HEADERS)
            by_id = {r.get("id"): r for r in rows if r.get("id")}
            row = by_id.get(run_id)
            if not row:
                row = {
                    "id": run_id,
                    "status": status,
                    "started_at": _iso(datetime.utcnow()),
                    "completed_at": _iso(datetime.utcnow()),
                    "target_products": json.dumps([]),
                    "total_stores": "0",
                    "completed_stores": "0",
                    "products_found": "0",
                    "errors": json.dumps([]),
                }
            else:
                row["status"] = status
                row["completed_at"] = _iso(datetime.utcnow())
            by_id[run_id] = row
            _clear_and_write(ws, RUN_HEADERS, list(by_id.values()))
        await asyncio.to_thread(_sync_sheets)


async def get_run_rows(run_id: str) -> List[Dict[str, Any]]:
    """Return all product rows for a given run from storage history."""
    STORAGE_BACKEND = _get_storage_backend()
    if STORAGE_BACKEND == "postgres":
        def _sync_pg():
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute(
                    f"SELECT {', '.join(RUN_PRODUCT_HEADERS)} FROM scraped_products_run WHERE run_id=%s",
                    (run_id,),
                )
                rows = cur.fetchall()
                out: List[Dict[str, Any]] = []
                for r in rows:
                    d = {h: r[i] for i, h in enumerate(RUN_PRODUCT_HEADERS)}
                    out.append(d)
                return out
            finally:
                conn.close()
        return await asyncio.to_thread(_sync_pg)
    elif STORAGE_BACKEND == "sqlite":
        def _sync_sqlite():
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute(
                    f"SELECT {', '.join(RUN_PRODUCT_HEADERS)} FROM scraped_products_run WHERE run_id=?",
                    (run_id,),
                )
                rows = cur.fetchall()
                out: List[Dict[str, Any]] = []
                for r in rows:
                    d = {h: r[i] for i, h in enumerate(RUN_PRODUCT_HEADERS)}
                    out.append(d)
                return out
            finally:
                conn.close()
        return await asyncio.to_thread(_sync_sqlite)
    elif STORAGE_BACKEND == "sheetdb":
        def _sync_sheetdb():
            recs = _sheetdb_select("scraped_products_run", {"run_id": run_id})
            # Ensure all expected keys in each row
            out: List[Dict[str, Any]] = []
            for r in recs:
                out.append({h: r.get(h, "") for h in RUN_PRODUCT_HEADERS})
            return out
        return await asyncio.to_thread(_sync_sheetdb)
    elif STORAGE_BACKEND == "airtable":
        def _sync_airtable():
            tables = _get_airtable_tables()
            tbl = tables["products_run"]
            formula = f"{{run_id}}='{run_id}'"
            recs = tbl.all(formula=formula)
            out: List[Dict[str, Any]] = []
            for rec in recs:
                out.append({h: rec.get("fields", {}).get(h, "") for h in RUN_PRODUCT_HEADERS})
            return out
        return await asyncio.to_thread(_sync_airtable)
    else:
        def _sync_sheets():
            client = _get_gspread_client()
            ss = _open_spreadsheet(client)
            ws = _get_or_create_ws(ss, "scraped_products_run", RUN_PRODUCT_HEADERS)
            rows = _read_all(ws, RUN_PRODUCT_HEADERS)
            return [r for r in rows if str(r.get("run_id")) == str(run_id)]
        return await asyncio.to_thread(_sync_sheets)
