"""
TreePage - Admin router
CRUD for users, tiles, and scripts registry.
All routes except /login and /logout require an active admin session.
"""

import re
import shutil
import subprocess
import os
import pathlib

import yaml
from fastapi import APIRouter, BackgroundTasks, Request, Form, HTTPException
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
    load_auth,
    save_auth,
    flash,
    pop_flashes,
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["pop_flashes"] = pop_flashes

router = APIRouter(tags=["admin"])

_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")

_DB_QUERIES_FILE = BASE_DIR / "db_queries.yaml"
_DB_CONFIGS_DIR = BASE_DIR / "db_configs"


def _load_db_queries() -> dict:
    if not _DB_QUERIES_FILE.exists():
        return {}
    return yaml.safe_load(_DB_QUERIES_FILE.read_text(encoding="utf-8")) or {}


def _save_db_queries(data: dict) -> None:
    _DB_QUERIES_FILE.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _list_db_configs() -> list[str]:
    if not _DB_CONFIGS_DIR.exists():
        return []
    return sorted(p.stem for p in _DB_CONFIGS_DIR.glob("*.yaml"))


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(400, "Slug non valido: usa solo lettere minuscole, numeri, - e _")


def _check_admin(request: Request):
    """Return a redirect response if the user is not authenticated, else None."""
    if not request.session.get("admin"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


# ── Auth routes ─────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("admin"):
        return RedirectResponse(url="/admin/", status_code=303)
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    auth = load_auth()
    if username == auth["username"] and password == auth["password"]:
        request.session["admin"] = True
        return RedirectResponse(url="/admin/", status_code=303)
    flash(request, "Credenziali non valide.", "error")
    return RedirectResponse(url="/admin/login", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    if r := _check_admin(request):
        return r
    return templates.TemplateResponse("admin/change_password.html", {"request": request})


@router.post("/change-password")
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    if r := _check_admin(request):
        return r
    auth = load_auth()
    if old_password != auth["password"]:
        flash(request, "Password attuale non corretta.", "error")
        return RedirectResponse(url="/admin/change-password", status_code=303)
    if new_password != confirm_password:
        flash(request, "Le nuove password non coincidono.", "error")
        return RedirectResponse(url="/admin/change-password", status_code=303)
    if len(new_password) < 4:
        flash(request, "La nuova password deve essere di almeno 4 caratteri.", "error")
        return RedirectResponse(url="/admin/change-password", status_code=303)
    auth["password"] = new_password
    save_auth(auth)
    flash(request, "Password aggiornata con successo.", "success")
    return RedirectResponse(url="/admin/", status_code=303)


# ── Update & restart ────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    """Run a command, return (returncode, combined stdout+stderr)."""
    env = {**__import__("os").environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        cmd, cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=120, env=env,
    )
    return result.returncode, result.stdout


@router.get("/update", response_class=HTMLResponse)
async def update_page(request: Request):
    if r := _check_admin(request):
        return r
    return templates.TemplateResponse("admin/update.html", {
        "request": request,
        "output": None,
    })


@router.post("/update", response_class=HTMLResponse)
async def run_update(request: Request):
    if r := _check_admin(request):
        return r

    lines: list[str] = []
    ok = True

    # 0. Check that BASE_DIR is a git repo
    if not (BASE_DIR / ".git").exists():
        lines.append(
            "Errore: questa directory non è un repository git.\n"
            "L'installazione precedente usava rsync (senza .git).\n\n"
            "Per abilitare gli aggiornamenti automatici, riesegui il setup:\n\n"
            "  cd <cartella-sorgente>\n"
            "  sudo bash deploy/setup.sh\n\n"
            "Il nuovo setup.sh usa 'git clone' e mantiene il .git in /opt/treepage.\n"
            "In alternativa, come root sul server:\n\n"
            "  cd /opt/treepage\n"
            "  git init\n"
            "  git remote add origin <URL-del-repo>\n"
            "  git fetch origin\n"
            "  git reset --hard origin/main"
        )
        return templates.TemplateResponse("admin/update.html", {
            "request": request,
            "output": "\n".join(lines),
            "ok": False,
        })

    # 0b. Check that the treepage user can write to .git (common issue when git
    #     was initialized as root but the app runs as a different user).
    git_dir = BASE_DIR / ".git"
    if not os.access(git_dir, os.W_OK):
        import pwd, stat as _stat
        try:
            owner = pwd.getpwuid(git_dir.stat().st_uid).pw_name
        except Exception:
            owner = str(git_dir.stat().st_uid)
        lines.append(
            f"Errore: la directory .git è di proprietà di '{owner}' e non è "
            f"scrivibile dall'utente corrente.\n\n"
            f"Correggi i permessi come root sul server:\n\n"
            f"  chown -R treepage:treepage /opt/treepage/.git"
        )
        return templates.TemplateResponse("admin/update.html", {
            "request": request,
            "output": "\n".join(lines),
            "ok": False,
        })

    # 1. git pull
    lines.append("$ git pull")
    code, out = _run(["git", "pull"], cwd=BASE_DIR)
    pull_out = out.rstrip()
    lines.append(pull_out)
    if code != 0:
        if "read-only file system" in pull_out.lower():
            lines.append(
                "\nIl filesystem .git non è scrivibile dall'utente corrente.\n"
                "Esegui come root:\n\n"
                "  chown -R treepage:treepage /opt/treepage/.git"
            )
        ok = False
    elif "already up to date" in pull_out.lower():
        # git pull succeeded, no new commits — skip pip install
        lines.append("\n✓ Nessun aggiornamento disponibile. Il codice è già all'ultima versione.")
        return templates.TemplateResponse("admin/update.html", {
            "request": request,
            "output": "\n".join(lines),
            "ok": True,
        })

    # 2. pip install (only if git pull succeeded and there were changes)
    if ok:
        venv_pip = BASE_DIR / "venv" / "bin" / "pip"
        pip_cmd = str(venv_pip) if venv_pip.exists() else "pip"
        lines.append(f"\n$ {pip_cmd} install -r requirements.txt")
        code, out = _run(
            [pip_cmd, "install", "-r", "requirements.txt"],
            cwd=BASE_DIR,
        )
        lines.append(out.rstrip())
        if code != 0:
            ok = False

    return templates.TemplateResponse("admin/update.html", {
        "request": request,
        "output": "\n".join(lines),
        "ok": ok,
    })


@router.post("/restart")
async def restart_service(request: Request, background_tasks: BackgroundTasks):
    if r := _check_admin(request):
        return r

    def _do_restart():
        import time
        time.sleep(2)
        subprocess.run(["sudo", "systemctl", "restart", "treepage"], check=False)

    background_tasks.add_task(_do_restart)
    flash(request, "Riavvio in corso — ricarica la pagina tra qualche secondo.", "warning")
    return RedirectResponse(url="/admin/login", status_code=303)


# ── Admin index ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request):
    if r := _check_admin(request):
        return r
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
            "db_queries": _load_db_queries(),
            "db_configs_list": _list_db_configs(),
        },
    )


# ── Users CRUD ─────────────────────────────────────────────────────────────

@router.get("/users/new", response_class=HTMLResponse)
async def new_user_form(request: Request):
    if r := _check_admin(request):
        return r
    return templates.TemplateResponse(
        "admin/user_edit.html",
        {"request": request, "user": None, "slug": "", "projects": list_projects(), "scripts": load_registry()},
    )


@router.post("/users/new")
async def create_user(
    request: Request,
    slug: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("👤"),
):
    if r := _check_admin(request):
        return r
    _validate_slug(slug)
    if load_user(slug) is not None:
        raise HTTPException(409, f"Utente '{slug}' già esistente")
    save_user(slug, {"name": name, "description": description, "icon": icon, "tiles": []})
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.get("/users/{slug}", response_class=HTMLResponse)
async def edit_user_form(request: Request, slug: str):
    if r := _check_admin(request):
        return r
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
    request: Request,
    slug: str,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("👤"),
):
    if r := _check_admin(request):
        return r
    data = load_user(slug)
    if data is None:
        raise HTTPException(404, f"Utente '{slug}' non trovato")
    data["name"] = name
    data["description"] = description
    data["icon"] = icon
    save_user(slug, data)
    return RedirectResponse(url=f"/admin/users/{slug}", status_code=303)


@router.post("/users/{slug}/delete")
async def delete_user_route(request: Request, slug: str):
    if r := _check_admin(request):
        return r
    if not delete_user(slug):
        raise HTTPException(404, f"Utente '{slug}' non trovato")
    return RedirectResponse(url="/admin/", status_code=303)


# ── Tiles CRUD ─────────────────────────────────────────────────────────────

@router.post("/users/{slug}/tiles/add")
async def add_tile(
    request: Request,
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
    if r := _check_admin(request):
        return r
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
async def delete_tile(request: Request, slug: str, index: int):
    if r := _check_admin(request):
        return r
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
async def move_tile(request: Request, slug: str, index: int, direction: str = Form(...)):
    if r := _check_admin(request):
        return r
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
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    port: int = Form(...),
    description: str = Form(""),
    autostart: bool = Form(False),
):
    if r := _check_admin(request):
        return r
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
    (SCRIPTS_DIR / name).mkdir(exist_ok=True)
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/scripts/{name}/delete")
async def delete_script(request: Request, name: str):
    if r := _check_admin(request):
        return r
    registry = load_registry()
    if name not in registry:
        raise HTTPException(404, f"Script '{name}' non trovato")
    del registry[name]
    save_registry(registry)
    return RedirectResponse(url="/admin/", status_code=303)


# ── Projects management ────────────────────────────────────────────────────

@router.post("/projects/create")
async def create_project(request: Request, name: str = Form(...)):
    if r := _check_admin(request):
        return r
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
async def delete_project(request: Request, name: str):
    if r := _check_admin(request):
        return r
    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        shutil.rmtree(project_dir)
    return RedirectResponse(url="/admin/", status_code=303)


# ── DB Queries CRUD ─────────────────────────────────────────────────────────

@router.post("/db-query/add")
async def add_db_query(
    request: Request,
    name: str = Form(...),
    config: str = Form(...),
    sql: str = Form(...),
):
    if r := _check_admin(request):
        return r
    _validate_slug(name)
    queries = _load_db_queries()
    queries[name] = {"config": config, "sql": sql}
    _save_db_queries(queries)
    flash(request, f"Query '{name}' salvata.", "success")
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/db-query/{name}/delete")
async def delete_db_query(request: Request, name: str):
    if r := _check_admin(request):
        return r
    queries = _load_db_queries()
    if name not in queries:
        raise HTTPException(404, f"Query '{name}' non trovata")
    del queries[name]
    _save_db_queries(queries)
    flash(request, f"Query '{name}' rimossa.", "success")
    return RedirectResponse(url="/admin/", status_code=303)
