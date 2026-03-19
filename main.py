"""
TreePage - Main application entry point
HTML aggregator & service dashboard for intranet operators.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import pathlib

from config import init_auth, load_auth
from routers import dashboard, admin, scripts_proxy

BASE_DIR = pathlib.Path(__file__).parent

# Ensure auth.yaml exists before reading the secret key
init_auth()
_auth = load_auth()

app = FastAPI(
    title="TreePage",
    description="Aggregatore di servizi e dashboard per operatori",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=_auth["secret_key"],
    same_site="lax",
    https_only=False,
)

# ── Static assets ──────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── Hosted HTML projects (served as-is by directory) ──────────────────────
app.mount(
    "/projects",
    StaticFiles(directory=str(BASE_DIR / "projects"), html=True),
    name="projects",
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(dashboard.router)
app.include_router(admin.router, prefix="/admin")
app.include_router(scripts_proxy.router, prefix="/api/scripts")


# ── Root redirect ──────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard/")
