"""
Generic Database query proxy router.

Loads query definitions at runtime from db_queries.yaml — no Python needed
for new queries, just add an entry to that file (or use the admin panel).

Endpoints:
  GET  /api/db/{name}?param=X  → runs SELECT, returns {"rows":[...], "total": N}
  POST /api/db/{name}          → runs write query (INSERT/UPDATE/DELETE),
                                  body: JSON {"param": "X"},
                                  returns {"affected": N}
"""

import datetime
import decimal
import pathlib

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from lib.db import get_connection

router = APIRouter(prefix="/api/db", tags=["db"])

_QUERIES_FILE = pathlib.Path(__file__).parent.parent / "db_queries.yaml"


def _load_queries() -> dict:
    if not _QUERIES_FILE.exists():
        return {}
    return yaml.safe_load(_QUERIES_FILE.read_text(encoding="utf-8")) or {}


def _serialize(row: dict) -> dict:
    """Convert non-JSON-serializable types to plain Python types."""
    result = {}
    for k, v in row.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            result[k] = v.isoformat()
        elif isinstance(v, decimal.Decimal):
            result[k] = float(v)
        else:
            result[k] = v
    return result


@router.get("/{name}")
async def run_select(name: str, request: Request):
    queries = _load_queries()
    if name not in queries:
        raise HTTPException(404, f"Query '{name}' non trovata in db_queries.yaml")
    entry = queries[name]
    params = dict(request.query_params)
    try:
        conn = get_connection(entry["config"])
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Connessione DB fallita: {e}")
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(entry["sql"], params)
                rows = [_serialize(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(500, f"Errore query: {e}")
    return JSONResponse({"rows": rows, "total": len(rows)})


@router.post("/{name}")
async def run_write(name: str, request: Request):
    queries = _load_queries()
    if name not in queries:
        raise HTTPException(404, f"Query '{name}' non trovata in db_queries.yaml")
    entry = queries[name]
    try:
        params = await request.json()
    except Exception:
        params = {}
    try:
        conn = get_connection(entry["config"])
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Connessione DB fallita: {e}")
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(entry["sql"], params)
                affected = cur.rowcount
    except Exception as e:
        raise HTTPException(500, f"Errore query: {e}")
    return {"affected": affected}
