"""
TreePage - Configuration management
Handles reading/writing YAML configs for users and scripts registry.
"""

import pathlib
import yaml
from typing import Any

BASE_DIR = pathlib.Path(__file__).parent
USERS_DIR = BASE_DIR / "users"
PROJECTS_DIR = BASE_DIR / "projects"
SCRIPTS_DIR = BASE_DIR / "scripts"
REGISTRY_FILE = BASE_DIR / "scripts_registry.yaml"

USERS_DIR.mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)
SCRIPTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Low-level YAML helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: pathlib.Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def list_users() -> list[str]:
    """Return list of user slugs (filenames without .yaml)."""
    return sorted(p.stem for p in USERS_DIR.glob("*.yaml"))


def load_user(slug: str) -> dict | None:
    path = USERS_DIR / f"{slug}.yaml"
    if not path.exists():
        return None
    return _load_yaml(path)


def save_user(slug: str, data: dict) -> None:
    _save_yaml(USERS_DIR / f"{slug}.yaml", data)


def delete_user(slug: str) -> bool:
    path = USERS_DIR / f"{slug}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# Scripts registry
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """Return the full scripts registry dict."""
    data = _load_yaml(REGISTRY_FILE)
    return data.get("scripts", {})


def save_registry(scripts: dict) -> None:
    _save_yaml(REGISTRY_FILE, {"scripts": scripts})


def get_script(name: str) -> dict | None:
    return load_registry().get(name)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def list_projects() -> list[str]:
    """Return list of project directory names that contain an index.html."""
    return sorted(
        d.name
        for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and (d / "index.html").exists()
    )


# ---------------------------------------------------------------------------
# Tile helpers
# ---------------------------------------------------------------------------

TILE_DEFAULTS: dict[str, Any] = {
    "title": "Senza titolo",
    "type": "external",
    "url": "#",
    "icon": "🔗",
    "description": "",
    "category": "Generale",
    "color": "",
}


def normalize_tile(tile: dict) -> dict:
    """Fill in missing fields with defaults."""
    result = dict(TILE_DEFAULTS)
    result.update(tile)
    # For 'project' type, build URL from project slug
    if result["type"] == "project" and "project" in result:
        result.setdefault("url", f"/projects/{result['project']}/")
    # For 'script' type, build URL from script name
    if result["type"] == "script" and "script" in result:
        result.setdefault("url", f"/api/scripts/{result['script']}/")
    return result
