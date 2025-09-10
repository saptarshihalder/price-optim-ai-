from fastapi import APIRouter, HTTPException
from app.libs.database import _get_gspread_client, _open_spreadsheet, _get_storage_backend, _sqlite_connect, _sqlite_ensure_schema
from app.libs.database import _sheetdb_base  # type: ignore
import requests

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/sheets")
def sheets_healthcheck():
    """Verify Google Sheets connectivity and access.

    Returns spreadsheet title and worksheet titles on success.
    """
    try:
        client = _get_gspread_client()
        ss = _open_spreadsheet(client)
        ws_titles = [ws.title for ws in ss.worksheets()]
        return {
            "status": "ok",
            "spreadsheet_title": ss.title,
            "worksheets": ws_titles,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets connection failed: {e}")


@router.get("/storage")
def storage_healthcheck():
    """Verify active storage backend connectivity.

    - postgres: checks DB and basic counts
    - sqlite: checks file and basic counts
    - airtable: not actively checked here
    - sheets: use /sheets
    """
    backend = _get_storage_backend()
    try:
        if backend == "postgres":
            import psycopg2  # type: ignore
            from app.libs.database import _pg_connect, _pg_ensure_schema  # type: ignore
            conn = _pg_connect()
            try:
                _pg_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM scraping_runs")
                runs = cur.fetchone()[0]
                return {"status": "ok", "backend": backend, "runs": runs}
            finally:
                conn.close()
        elif backend == "sqlite":
            conn = _sqlite_connect()
            try:
                _sqlite_ensure_schema(conn)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM scraping_runs")
                runs = cur.fetchone()[0]
                return {"status": "ok", "backend": backend, "runs": runs}
            finally:
                conn.close()
        elif backend == "airtable":
            return {"status": "ok", "backend": backend}
        elif backend == "sheetdb":
            base, headers = _sheetdb_base()
            r = requests.get(base, headers=headers, params={"limit": 1}, timeout=10)
            detail = r.text
            try:
                detail = r.json()
            except Exception:
                pass
            return {"status": "ok" if r.status_code < 300 else "error", "backend": backend, "probe": detail}
        elif backend == "sheets":
            return {"status": "ok", "backend": backend, "hint": "Call /routes/health/sheets"}
        else:
            return {"status": "unknown", "backend": backend}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage connection failed: {e}")
