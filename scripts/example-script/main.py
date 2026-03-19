"""
TreePage – Example Python microservice
Dimostra come strutturare uno script Python come microservizio FastAPI
che viene esposto tramite il proxy di TreePage.

Avvio manuale:
    uvicorn main:app --port 9001

Con systemd (vedi deploy/treepage-script@.service):
    systemctl start treepage-script@example-script
"""

import platform
import datetime
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Example Script", version="1.0.0")


@app.get("/")
async def info():
    """Restituisce informazioni di sistema di base."""
    return {
        "status": "ok",
        "script": "example-script",
        "timestamp": datetime.datetime.now().isoformat(),
        "system": {
            "hostname": platform.node(),
            "os": platform.system(),
            "python": platform.python_version(),
            "pid": os.getpid(),
        },
    }


@app.get("/ping")
async def ping():
    return {"pong": True}


@app.post("/echo")
async def echo(body: dict):
    """Restituisce il body JSON ricevuto."""
    return {"echo": body, "timestamp": datetime.datetime.now().isoformat()}
