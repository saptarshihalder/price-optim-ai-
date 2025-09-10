import os
import pathlib
import json
import dotenv
from fastapi import FastAPI, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

dotenv.load_dotenv()
os.environ.setdefault("DATABUTTON_PROJECT_ID", "local-dev")

# Prefer SheetDB automatically if configured, even if other .env files load earlier
if not os.environ.get("STORAGE_BACKEND") and os.environ.get("SHEETDB_API_URL"):
    os.environ["STORAGE_BACKEND"] = "sheetdb"

try:
    # When imported as a package (uvicorn backend.main:app)
    from .databutton_app.mw.auth_mw import AuthConfig, get_authorized_user  # type: ignore
except Exception:
    # When executed as a script (python backend/main.py)
    from databutton_app.mw.auth_mw import AuthConfig, get_authorized_user  # type: ignore


def get_router_config() -> dict:
    """Load router configuration from JSON.

    Tries CWD `routers.json`, then falls back to file beside this module.
    Returns an empty config if not available.
    """
    # Try current working directory
    try:
        with open("routers.json", "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except Exception:
        pass

    # Try path next to this file (backend/routers.json)
    try:
        cfg_path = pathlib.Path(__file__).parent / "routers.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return {}


def is_auth_disabled(router_config: dict, name: str) -> bool:
    """Default to disabled auth if config missing."""
    try:
        return bool(router_config["routers"][name]["disableAuth"])
    except Exception:
        return True


def import_api_routers() -> APIRouter:
    """Create top level router including all user defined endpoints."""
    routes = APIRouter(prefix="/routes")

    router_config = get_router_config()

    src_path = pathlib.Path(__file__).parent

    # Import API routers from "src/app/apis/*/__init__.py"
    apis_path = src_path / "app" / "apis"

    api_names = [
        p.relative_to(apis_path).parent.as_posix()
        for p in apis_path.glob("*/__init__.py")
    ]

    # Compute module prefix to support both package imports and direct execution
    root_pkg = __package__.split(".")[0] if __package__ else None
    api_module_prefix = (root_pkg + "." if root_pkg else "") + "app.apis."

    for name in api_names:
        print(f"Importing API: {name}")
        try:
            api_module = __import__(api_module_prefix + name, fromlist=[name])
            api_router = getattr(api_module, "router", None)
            if isinstance(api_router, APIRouter):
                routes.include_router(
                    api_router,
                    dependencies=(
                        []
                        if is_auth_disabled(router_config, name)
                        else [Depends(get_authorized_user)]
                    ),
                )
        except ImportError as e:
            print(f"Error importing API router {name}: {e}")
            continue
        except AttributeError as e:
            print(f"Error getting router attribute for API {name}: {e}")
            continue
        except Exception as e:
            print(f"An unexpected error occurred while importing API {name}: {e}")
            continue

    print(routes.routes)

    return routes


def get_firebase_config() -> dict | None:
    extensions = os.environ.get("DATABUTTON_EXTENSIONS", "[]")
    extensions = json.loads(extensions)

    for ext in extensions:
        if ext["name"] == "firebase-auth":
            return ext["config"]["firebaseConfig"]

    return None


def create_app() -> FastAPI:
    """Create the app. This is called by uvicorn with the factory option to construct the app object."""
    app = FastAPI()
    # Primary API mount
    app.include_router(import_api_routers())
    # Compatibility mount: also expose all routes under /api/routes/* for builds that expect that prefix
    app.include_router(import_api_routers(), prefix="/api")

    # Allow both 127.0.0.1 and localhost (and any origin in dev) to call the API
    # This avoids CORS issues for builds that hardcode API_URL differently than the page origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve built frontend (dist/) so opening the backend URL loads the UI
    # Resolve repo root and dist paths
    # Repo root is the parent of the backend folder
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    # Built frontend is at <repo_root>/dist
    dist_path = repo_root / "dist"
    assets_path = dist_path / "assets"
    index_html = dist_path / "index.html"

    try:
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    except Exception as e:
        print(f"Static mount skipped: {e}")

    for route in app.routes:
        if hasattr(route, "methods"):
            for method in route.methods:
                print(f"{method} {route.path}")

    firebase_config = get_firebase_config()

    if firebase_config is None:
        print("No firebase config found")
        app.state.auth_config = None
    else:
        print("Firebase config found")
        auth_config = {
            "jwks_url": "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
            "audience": firebase_config["projectId"],
            "header": "authorization",
        }

        app.state.auth_config = AuthConfig(**auth_config)

    return app


app = create_app()

# SPA history fallback to index.html for non-API, non-static paths
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    # Let API routes and docs pass through (they are already registered earlier)
    if full_path.startswith("routes") or full_path in {"docs", "openapi.json", "redoc"}:
        # FastAPI will handle these; return 404 so original route resolution applies
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    index_file = (repo_root / "dist" / "index.html")
    if index_file.exists():
        return FileResponse(str(index_file))
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="index.html not found. Build frontend or run dev server.")
