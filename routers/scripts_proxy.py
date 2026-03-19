"""
TreePage - Scripts proxy router
Forwards requests to Python microservices running on separate ports.
"""

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

from config import get_script

router = APIRouter(tags=["scripts"])

_TIMEOUT = httpx.Timeout(30.0)


async def _forward(request: Request, script_name: str, path: str) -> Response:
    """Forward an incoming request to the target microservice."""
    script = get_script(script_name)
    if script is None:
        raise HTTPException(404, f"Script '{script_name}' non registrato")

    port = script.get("port")
    target_url = f"http://127.0.0.1:{port}/{path.lstrip('/')}"

    # Preserve query string
    if request.url.query:
        target_url += f"?{request.url.query}"

    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
            )
        except httpx.ConnectError:
            raise HTTPException(
                503,
                f"Impossibile connettersi allo script '{script_name}' (porta {port}). "
                "Verificare che il servizio sia in esecuzione.",
            )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


@router.api_route("/{script_name}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_root(request: Request, script_name: str):
    return await _forward(request, script_name, "/")


@router.api_route("/{script_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_path(request: Request, script_name: str, path: str):
    return await _forward(request, script_name, path)
