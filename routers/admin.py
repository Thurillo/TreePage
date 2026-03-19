"""
TreePage - Admin router
CRUD for users, tiles, and scripts registry.
"""

import re
import shutil
import pathlib

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import (
    BASE_DIR,
    PROJECTS_DIR,
    SCRIPTS_DIR,
    list_users,
    load_user,
    save_user,
    delete_user,
    load_registry,
    save_registry,
    list_projects,
    normalize_tile,
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter(tags=["admin"])

_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(400, "Slug non valido: usa solo lettere minuscole, numeri, - e _")


# ── Admin index ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request):
    users = []
    for slug in list_users():
        data = load_user(slug) or {}
        users.append({
            "slug": slug,
            "name": data.get("name", slug),
            "icon": data.get("icon", "👤"),
            "tile_count": len(data.get("tiles", [])),
        })
    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "users": users,
            "projects": list_projects(),
            "scripts": load_registry(),
        },
    )


# ── Users CRUD ─────────────────────────────────────────────────────────────

@router.get("/users/new", response_class=HTMLResponse)
async def new_user_form(request: Request):
    return templates.TemplateResponse(
        "admin/user_edit.html",
        {"request": request, "user": None, "slug": "", "projects": list_projects(), "scripts": load_registry()},
    )


@router.post("/users/new")
async def create_user(
    slug: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("👤"),
):
    _validate_slug(slug)
    if load_user(slug) is not None:
        raise HTTPException(409, f"Utente '{slug}' già esistente")
    save_user(slug, {"name": name, "description": description, "icon": icon, "tiles": []})
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.get("/users/{slug}", response_class=HTMLResponse)
async def edit_user_form(request: Request, slug: str):
    data = load_user(slug)
    if data is None:
        raise HTTPException(404, f"Utente '{slug}' non trovato")
    tiles = [normalize_tile(t) for t in data.get("tiles", [])]
    return templates.TemplateResponse(
        "admin/user_edit.html",
        {
            "request": request,
            "user": data,
            "slug": slug,
            "tiles": tiles,
            "projects": list_projects(),
            "scripts": load_registry(),
        },
    )


@router.post("/users/{slug}/update")
async def update_user(
    slug: str,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("👤"),
):
    data = load_user(slug)
    if data is None:
        raise HTTPException(404, f"Utente '{slug}' non trovato")
    data["name"] = name
    data["description"] = description
    data["icon"] = icon
    save_user(slug, data)
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.post("/users/{slug}/delete")
async def delete_user_route(slug: str):
    if not delete_user(slug):
        raise HTTPException(404, f"Utente '{slug}' non trovato")
    return RedirectResponse(url="/admin/", status_code=303)


# ── Tiles CRUD ─────────────────────────────────────────────────────────────

@router.post("/users/{slug}/tiles/add")
async def add_tile(
    slug: str,
    title: str = Form(...),
    tile_type: str = Form(...),
    url: str = Form(""),
    project: str = Form(""),
    script: str = Form(""),
    icon: str = Form("🔗"),
    description: str = Form(""),
    category: str = Form("Generale"),
    color: str = Form(""),
):
    data = load_user(slug)
    if data is None:
        raise HTTPException(404)
    tile: dict = {
        "title": title,
        "type": tile_type,
        "icon": icon,
        "description": description,
        "category": category,
    }
    if tile_type == "project" and project:
        tile["project"] = project
    elif tile_type == "script" and script:
        tile["script"] = script
    else:
        tile["url"] = url
    if color:
        tile["color"] = color
    data.setdefault("tiles", []).append(tile)
    save_user(slug, data)
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.post("/users/{slug}/tiles/{index}/delete")
async def delete_tile(slug: str, index: int):
    data = load_user(slug)
    if data is None:
        raise HTTPException(404)
    tiles = data.get("tiles", [])
    if index < 0 or index >= len(tiles):
        raise HTTPException(400, "Indice tile non valido")
    tiles.pop(index)
    data["tiles"] = tiles
    save_user(slug, data)
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.post("/users/{slug}/tiles/{index}/move")
async def move_tile(slug: str, index: int, direction: str = Form(...)):
    data = load_user(slug)
    if data is None:
        raise HTTPException(404)
    tiles = data.get("tiles", [])
    if direction == "up" and index > 0:
        tiles[index], tiles[index - 1] = tiles[index - 1], tiles[index]
    elif direction == "down" and index < len(tiles) - 1:
        tiles[index], tiles[index + 1] = tiles[index + 1], tiles[index]
    data["tiles"] = tiles
    save_user(slug, data)
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


# ── Scripts registry CRUD ──────────────────────────────────────────────────

@router.post("/scripts/add")
async def add_script(
    name: str = Form(...),
    display_name: str = Form(...),
    port: int = Form(...),
    description: str = Form(""),
    autostart: bool = Form(False),
):
    _validate_slug(name)
    registry = load_registry()
    registry[name] = {
        "name": display_name,
        "port": port,
        "description": description,
        "autostart": autostart,
        "path": str(SCRIPTS_DIR / name),
    }
    save_registry(registry)
    # Create script directory if not exists
    (SCRIPTS_DIR / name).mkdir(exist_ok=True)
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/scripts/{name}/delete")
async def delete_script(name: str):
    registry = load_registry()
    if name not in registry:
        raise HTTPException(404, f"Script '{name}' non trovato")
    del registry[name]
    save_registry(registry)
    return RedirectResponse(url="/admin/", status_code=303)


# ── Projects management ────────────────────────────────────────────────────

@router.post("/projects/create")
async def create_project(name: str = Form(...)):
    _validate_slug(name)
    project_dir = PROJECTS_DIR / name
    project_dir.mkdir(exist_ok=True)
    index_file = project_dir / "index.html"
    if not index_file.exists():
        index_file.write_text(
            f"<!DOCTYPE html>\n<html>\n<head><title>{name}</title></head>\n"
            f"<body><h1>{name}</h1><p>Inserisci qui il contenuto del progetto.</p></body>\n</html>\n",
            encoding="utf-8",
        )
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/projects/{name}/delete")
async def delete_project(name: str):
    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        shutil.rmtree(project_dir)
    return RedirectResponse(url="/admin/", status_code=303)
