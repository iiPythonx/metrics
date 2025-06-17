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

# Configuration
config_file = Path.cwd() / "settings.json"
if not config_file.is_file():
    exit("iiPython Monitoring requires a `settings.json` file in the current directory.")

config = loads(config_file.read_text())

# Node reverse mapping
app.state.metrics = {endpoint["name"]: {"nodes": {}, "overall": {}} for endpoint in config["endpoints"]}
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
    for data in app.state.metrics.values():

        # Throw together node data
        results = {}
        for node_data in data["nodes"].values():
            for field, value in node_data.items():
                results[field] = results.get(field, []) + [value]

        # Exclude endpoints with bad data
        if not results:
            data["overall"] = {}
            continue

        # Compute average, excluding HTTP status
        data["overall"] = {
            k: round(sum(v) / len(v))
            for k, v in results.items() if k != "htc"
        } | {"htc": max(set(results["htc"]), key = results["htc"].count)}

    return JSONResponse({
        "code": 200,
        "data": app.state.metrics
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
    node_name = reversed_nodes[authorization][1]
    for endpoint, data in payload.items():
        app.state.metrics[endpoint]["nodes"][node_name] = data.model_dump()

    return JSONResponse({"code": 200})

# Static files
app.mount("/", StaticFiles(directory = Path(__file__).parent / "frontend", html = True))
