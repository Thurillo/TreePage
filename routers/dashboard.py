"""
TreePage - Dashboard router
Handles personal user dashboards (no public listing).
"""

from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pathlib

from config import load_user, normalize_tile, pop_flashes, verify_password

BASE_DIR = pathlib.Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["pop_flashes"] = pop_flashes

router = APIRouter(tags=["dashboard"])


def _dash_user_ctx(slug: str, data: dict) -> dict:
    return {
        "slug": slug,
        "name": data.get("name", slug),
        "description": data.get("description", ""),
        "icon": data.get("icon", "👤"),
    }


@router.get("/dashboard/{slug}", response_class=HTMLResponse)
async def user_dashboard(request: Request, slug: str):
    """Render a specific user's dashboard."""
    data = load_user(slug)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{slug}' non trovata")

    pwd_hash = data.get("password_hash")
    if pwd_hash and not request.session.get(f"dash_auth_{slug}"):
        return templates.TemplateResponse(request, "dashboard_login.html", {
            "user": _dash_user_ctx(slug, data),
            "error": False,
        })

    categories: dict[str, list] = {}
    for tile_raw in data.get("tiles", []):
        tile = normalize_tile(tile_raw)
        cat = tile["category"]
        categories.setdefault(cat, []).append(tile)

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": _dash_user_ctx(slug, data),
        "categories": categories,
    })


@router.post("/dashboard/{slug}/login")
async def dashboard_login(request: Request, slug: str, password: str = Form(...)):
    data = load_user(slug)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{slug}' non trovata")

    pwd_hash = data.get("password_hash")
    if pwd_hash and verify_password(password, pwd_hash):
        request.session[f"dash_auth_{slug}"] = True
        return RedirectResponse(url=f"/dashboard/{slug}", status_code=303)

    return templates.TemplateResponse(request, "dashboard_login.html", {
        "user": _dash_user_ctx(slug, data),
        "error": True,
    })
