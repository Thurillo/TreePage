"""
TreePage - File manager router
Browse, upload, create, edit and delete files within the TreePage directory.
All routes require an active admin session.
"""

import mimetypes
import pathlib
import shutil
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import BASE_DIR, flash, pop_flashes

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["pop_flashes"] = pop_flashes

router = APIRouter(tags=["files"])

# Directories to hide from the listing
_HIDDEN_DIRS = {".git", "venv", "__pycache__", ".venv"}

# Extensions allowed for the text editor
_TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".yaml", ".yml",
    ".json", ".md", ".txt", ".py", ".xml", ".svg", ".sh", ".conf",
}


def _check_admin(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


def _safe_path(rel: str) -> pathlib.Path:
    """Resolve *rel* relative to BASE_DIR; raise 403 if outside."""
    base = BASE_DIR.resolve()
    # Empty string → base directory itself
    target = (base / rel.lstrip("/")).resolve() if rel.strip("/") else base
    if not str(target).startswith(str(base)):
        raise HTTPException(403, "Percorso non consentito")
    return target


def _rel(path: pathlib.Path) -> str:
    """Return the path relative to BASE_DIR as a POSIX string."""
    try:
        return path.relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return ""


def _breadcrumbs(rel: str) -> list[dict]:
    """Build breadcrumb list: [{"name": "root", "path": ""}, ...]"""
    crumbs = [{"name": "root", "path": ""}]
    parts = [p for p in rel.split("/") if p]
    for i, part in enumerate(parts):
        crumbs.append({"name": part, "path": "/".join(parts[: i + 1])})
    return crumbs


def _file_info(path: pathlib.Path) -> dict:
    """Build a file/dir info dict for template rendering."""
    stat = path.stat()
    is_dir = path.is_dir()
    size = stat.st_size if not is_dir else None
    ext = path.suffix.lower()
    return {
        "name": path.name,
        "path": _rel(path),
        "is_dir": is_dir,
        "size": size,
        "editable": not is_dir and ext in _TEXT_EXTENSIONS,
        "hidden": is_dir and path.name in _HIDDEN_DIRS,
    }


def _fmt_size(size: Optional[int]) -> str:
    if size is None:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ── Browse ──────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def browse(request: Request, path: str = ""):
    if r := _check_admin(request):
        return r
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(404, "Percorso non trovato")
    if target.is_file():
        # Redirect to edit if it's a text file, otherwise download
        ext = target.suffix.lower()
        rel = _rel(target)
        if ext in _TEXT_EXTENSIONS:
            return RedirectResponse(url=f"/admin/files/edit?path={rel}", status_code=303)
        return RedirectResponse(url=f"/admin/files/download?path={rel}", status_code=303)

    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    items = [_file_info(e) for e in entries if not (e.is_dir() and e.name in _HIDDEN_DIRS)]

    return templates.TemplateResponse("admin/files.html", {
        "request": request,
        "current_path": _rel(target),
        "breadcrumbs": _breadcrumbs(_rel(target)),
        "items": items,
        "fmt_size": _fmt_size,
        "mode": "browse",
    })


# ── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload(request: Request, path: str = Form(""), files: List[UploadFile] = None):
    if r := _check_admin(request):
        return r
    target_dir = _safe_path(path)
    if not target_dir.is_dir():
        raise HTTPException(400, "Il percorso di destinazione non è una directory")
    if not files:
        flash(request, "Nessun file selezionato.", "warning")
        return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)
    for f in files:
        if not f.filename:
            continue
        dest = target_dir / pathlib.Path(f.filename).name
        content = await f.read()
        dest.write_bytes(content)
    flash(request, f"{len(files)} file caricati con successo.", "success")
    return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)


# ── Create directory ─────────────────────────────────────────────────────────

@router.post("/mkdir")
async def mkdir(request: Request, path: str = Form(""), name: str = Form(...)):
    if r := _check_admin(request):
        return r
    parent = _safe_path(path)
    new_dir = _safe_path(f"{path}/{name}" if path else name)
    if new_dir.exists():
        flash(request, f"'{name}' esiste già.", "error")
        return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)
    new_dir.mkdir(parents=True, exist_ok=True)
    flash(request, f"Cartella '{name}' creata.", "success")
    return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)


# ── Create new text file ─────────────────────────────────────────────────────

@router.post("/newfile")
async def newfile(request: Request, path: str = Form(""), name: str = Form(...)):
    if r := _check_admin(request):
        return r
    parent = _safe_path(path)
    new_file = _safe_path(f"{path}/{name}" if path else name)
    if new_file.exists():
        flash(request, f"'{name}' esiste già.", "error")
        return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)
    new_file.touch()
    rel = _rel(new_file)
    if new_file.suffix.lower() in _TEXT_EXTENSIONS:
        return RedirectResponse(url=f"/admin/files/edit?path={rel}", status_code=303)
    return RedirectResponse(url=f"/admin/files/?path={path}", status_code=303)


# ── Edit (GET) ───────────────────────────────────────────────────────────────

@router.get("/edit", response_class=HTMLResponse)
async def edit_file(request: Request, path: str = ""):
    if r := _check_admin(request):
        return r
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File non trovato")
    if target.suffix.lower() not in _TEXT_EXTENSIONS:
        raise HTTPException(400, "Tipo di file non modificabile")
    content = target.read_text(encoding="utf-8", errors="replace")
    parent_rel = _rel(target.parent)
    return templates.TemplateResponse("admin/files.html", {
        "request": request,
        "current_path": path,
        "breadcrumbs": _breadcrumbs(path),
        "mode": "edit",
        "content": content,
        "filename": target.name,
        "parent_path": parent_rel,
    })


# ── Save (POST) ──────────────────────────────────────────────────────────────

@router.post("/save")
async def save_file(request: Request, path: str = Form(...), content: str = Form(...)):
    if r := _check_admin(request):
        return r
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File non trovato")
    target.write_text(content, encoding="utf-8")
    flash(request, f"'{target.name}' salvato.", "success")
    return RedirectResponse(url=f"/admin/files/edit?path={path}", status_code=303)


# ── Delete ───────────────────────────────────────────────────────────────────

@router.post("/delete")
async def delete(request: Request, path: str = Form(...)):
    if r := _check_admin(request):
        return r
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(404, "Percorso non trovato")
    parent_rel = _rel(target.parent)
    name = target.name
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    flash(request, f"'{name}' eliminato.", "success")
    return RedirectResponse(url=f"/admin/files/?path={parent_rel}", status_code=303)


# ── Download ─────────────────────────────────────────────────────────────────

@router.get("/download")
async def download(request: Request, path: str = ""):
    if r := _check_admin(request):
        return r
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File non trovato")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=media_type,
    )
