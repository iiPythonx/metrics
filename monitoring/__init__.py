# Copyright (c) 2025 iiPython

# Modules
from json import loads
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Initialization
app = FastAPI(openapi_url = None)
app.state.metrics = {}

# Configuration
config_file = Path.cwd() / "settings.json"
if not config_file.is_file():
    exit("iiPython Monitoring requires a `settings.json` file in the current directory.")

config = loads(config_file.read_text())

# Node reverse mapping
reversed_nodes = {v["auth"]: (v["lock"], v["name"]) for v in config["nodes"]}

# Modeling
class Metric(BaseModel):
    tfb: int
    rwl: int
    cpt: int
    tcp: int
    tls: int
    htc: int

# Routing
@app.get("/v1/nodes")
async def api_nodes() -> JSONResponse:
    return JSONResponse({
        "code": 200,
        "data": [
            {k: v for k, v in node.items() if k not in ["lock", "auth"]}
            for node in config["nodes"]
        ]
    })

@app.get("/v1/metrics")
async def api_metrics() -> JSONResponse:
    metrics = {}
    for endpoint in config["endpoints"]:
        metrics[endpoint["name"]] = {"nodes": {}, "overall": {}}

    # Global metrics
    for payload in app.state.metrics.values():
        for endpoint, data in payload.items():
            if endpoint not in metrics:
                metrics[endpoint] = {}

            for field, value in data.items():
                if field not in metrics[endpoint]:
                    metrics[endpoint]["overall"][field] = []

                metrics[endpoint]["overall"][field].append(value)

    for endpoint, data in metrics.items():
        for field, values in data["overall"].items():
            if field == "status":
                metrics[endpoint]["overall"][field] = max(set(values), key = values.count)
                continue

            metrics[endpoint]["overall"][field] = round(sum(values) / len(values))

    # Per-node metrics
    for auth, payload in app.state.metrics.items():
        for endpoint, data in payload.items():
            metrics[endpoint]["nodes"][reversed_nodes[auth][1]] = data

    return JSONResponse({
        "code": 200,
        "data": metrics
    })

async def verify_private(request: Request, authorization: Annotated[str, Header()]) -> str:
    if request.client is None:
        raise HTTPException(400, detail = "Client address could not be determined.")

    ip = request.headers.get("CF-Connecting-IP") or request.client.host

    # Validate authorization
    if authorization is None or authorization not in reversed_nodes:
        raise HTTPException(401, detail = "Invalid authorization code.")

    # Validate IP
    if reversed_nodes[authorization][0] and reversed_nodes[authorization][0] != ip:
        raise HTTPException(401, detail = "Authorization code has been misused.")

    return authorization

@app.get("/v1/private/endpoints", dependencies = [Depends(verify_private)])
async def api_private_endpoints() -> JSONResponse:
    return JSONResponse({
        "code": 200,
        "data": config["endpoints"]
    })

@app.post("/v1/private/metrics")
async def api_private_metrics(payload: dict[str, Metric], authorization: str = Depends(verify_private)) -> JSONResponse:
    app.state.metrics[authorization] = {k: v.model_dump() for k, v in payload.items()}
    return JSONResponse({"code": 200})

# Static files
app.mount("/", StaticFiles(directory = Path(__file__).parent / "frontend", html = True))
