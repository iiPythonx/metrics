# Copyright (c) 2025 iiPython

# Modules
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Initialization
app = FastAPI(openapi_url = None)

# Routing
@app.get("/v1/nodes")
async def api_nodes() -> JSONResponse:
    return JSONResponse({
        "code": 200,
        "data": []
    })

@app.get("/v1/metrics")
async def api_metrics() -> JSONResponse:
    return JSONResponse({
        "code": 200,
        "data": []
    })

# Static files
app.mount("/", StaticFiles(directory = Path(__file__).parent / "frontend", html = True))
