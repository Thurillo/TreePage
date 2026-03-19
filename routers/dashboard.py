"""
TreePage - Dashboard router
Handles public user dashboards and the users listing page.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pathlib

from config import list_users, load_user, normalize_tile

BASE_DIR = pathlib.Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/", response_class=HTMLResponse)
async def users_list(request: Request):
    """Show all available dashboards."""
    users = []
    for slug in list_users():
        data = load_user(slug) or {}
        users.append({
            "slug": slug,
            "name": data.get("name", slug),
            "description": data.get("description", ""),
            "icon": data.get("icon", "👤"),
        })
    return templates.TemplateResponse(
        "users_list.html",
        {"request": request, "users": users},
    )


@router.get("/dashboard/{slug}", response_class=HTMLResponse)
async def user_dashboard(request: Request, slug: str):
    """Render a specific user's dashboard."""
    data = load_user(slug)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{slug}' non trovata")

    # Group tiles by category
    categories: dict[str, list] = {}
    for tile_raw in data.get("tiles", []):
        tile = normalize_tile(tile_raw)
        cat = tile["category"]
        categories.setdefault(cat, []).append(tile)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": {
                "slug": slug,
                "name": data.get("name", slug),
                "description": data.get("description", ""),
                "icon": data.get("icon", "👤"),
            },
            "categories": categories,
        },
    )
