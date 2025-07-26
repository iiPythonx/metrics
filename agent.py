# Copyright (c) 2025 iiPython

# Modules
import sys
import ssl
import time
import json
import socket
import typing
from datetime import datetime, timedelta
from dataclasses import dataclass

from urllib import request
from urllib.error import URLError
from urllib.parse import urlparse

# Initialization
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEBUG_MODE = "--oneshot" in sys.argv

@dataclass
class TimingInformation:
    proto:         typing.Literal["TCP", "UDP"]
    rtt:           int
    min_rtt:       int
    rtt_var:       int
    sent:          int
    recv:          int
    lost:          int
    retrans:       int
    sent_bytes:    int
    recv_bytes:    int
    delivery_rate: int
    cwnd:          int
    unsent_bytes:  int
    cid:           str
    ts:            int
    x:             int

class NotCloudflare(Exception):
    pass

class SiteDown(Exception):
    pass

# https://stackoverflow.com/a/74844056
class NonRaisingHTTPErrorProcessor(request.HTTPErrorProcessor):
    http_response = https_response = lambda self, request, response: response

HTTP_OPENER = request.build_opener(NonRaisingHTTPErrorProcessor)

# Handling
def mkrequest(endpoint: str, headers: dict[str, str] = {}, **kwargs):
    try:
        return HTTP_OPENER.open(request.Request(
            f"{sys.argv[1].rstrip('/')}/v1{endpoint}",
            headers = headers | {"Authorization": sys.argv[2], "User-Agent": USER_AGENT},
            **kwargs
        ))

    except URLError:
        print(f"[API] Request to ${endpoint} failed...")
        exit(1)

def parse_timing(timing: str | None) -> TimingInformation:
    if not timing:
        raise NotCloudflare

    timing = (timing or "").split(" ")[-1]  # In the event of a duplicated header
    if timing[:4] != "cfL4":
        raise NotCloudflare

    return TimingInformation(**{
        name: int(value) if value.isnumeric() else value
        for name, value in [tuple(item.split("=")) for item in timing[12:-1].split("&")]
    })  # type: ignore

def calculate(url: str) -> tuple[list[dict[str, float]], int]:
    results, parsed = [], urlparse(url)
    for _ in range(2):
        payload = {"cpt": 0.0, "rwl": 0.0}

        # Establish request
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as outgoing:
            outgoing.settimeout(5)

            # Calculate TCP connection time
            start = time.perf_counter()
            outgoing.connect((parsed.netloc, 443))
            payload["tcp"] = time.perf_counter() - start

            # Calculate TLS handshake
            if parsed.scheme == "https":
                start = time.perf_counter()
                context = ssl.create_default_context()
                outgoing = context.wrap_socket(outgoing, server_hostname = parsed.netloc)
                payload["tls"] = time.perf_counter() - start

            start = time.perf_counter()
            outgoing.sendall(b"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n")
            outgoing.recv(1)
            payload["tfb"] = time.perf_counter() - start

        # Send actual HTTP request
        start = time.perf_counter()
        with HTTP_OPENER.open(request.Request(url, method = "GET", headers = {"User-Agent": USER_AGENT})) as response:
            payload["htc"] = response.getcode()
            payload["rwl"] = time.perf_counter() - start

            # Attempt to calculate the server side compute time from Cloudflare Server-Timing
            try:
                payload["cpt"] = parse_timing(response.getheader("Server-Timing")).rtt

            except NotCloudflare:
                pass

        # Forced sleep to prevent congestion on the target's side
        time.sleep(1)
        results.append(payload)

    return results, results[-1]["htc"]

# Utility tooling
def suffix(byte_count: float) -> str:
    if byte_count > 1000:
        return f"{round(byte_count / 1000, 1)} KiB"

    return f"{byte_count} B"

# Main loop
while True:

    # Calculate the next 5-minute interval
    now = datetime.now()
    target = now.replace(minute = 0, second = 0, microsecond = 0) + timedelta(minutes = (now.minute // 5 + 1) * 5)

    print(f"[Timing] Next target interval @ {target}")

    if not DEBUG_MODE:
        time.sleep((target - now).total_seconds())\

    # Fetch endpoints from upstream
    print("[API] Checking endpoint information...")
    with mkrequest("/private/endpoints") as response:
        endpoints = json.loads(response.read())["data"]
        print(f"    | {len(endpoints)} endpoint(s) were returned.")

        payload = {}
        for endpoint in endpoints:
            print("[Check]", endpoint["url"])
            results, status = calculate(endpoint["url"])

            # Convert and average results
            flattened = {}
            for result in results:
                for field, value in result.items():
                    if field == "code":
                        continue
                    
                    if field not in flattened:
                        flattened[field] = []

                    flattened[field].append(value if field == "cpt" else value * 1000)

            results = {k: round(sum(v) / len(v)) for k, v in flattened.items()}
            results["cpt"] = round(results["cpt"] / 1000)  # Micro -> milli

            # Save results to global payload
            payload[endpoint["name"]] = results | {"htc": status}

            print(f"     | RWL: {results['rwl']}ms | TCP: {results['tcp']}ms | TLS: {results['tls']}ms")
            print(f"     | Compute: {results['cpt']}ms | TTFB: {results['tfb']}ms | Code: HTTP {status}")

        # Send off to metric site
        with mkrequest("/private/metrics", headers = {"Content-Type": "application/json"}, data = json.dumps(payload).encode(), method = "POST") as response:
            print("[API]", "Metrics uploaded!" if response.getcode() == 200 else "Metric upload failed!")

        if DEBUG_MODE:
            exit()
