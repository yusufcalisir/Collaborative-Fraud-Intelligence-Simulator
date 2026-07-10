import asyncio
import contextlib
import logging
import time

import httpx
import websockets
from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.openapi.docs import get_swagger_ui_html

from app.config import get_settings
from app.infrastructure.redis_store import RedisStore

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

_rate_limiter = RedisStore("gateway_rate_limit")

# Downstream services mapping
SERVICES = {
    "fl-coordinator": {
        "http": "http://localhost:8001",
        "ws": "ws://localhost:8001",
    },
    "identity-graph": {
        "http": "http://localhost:8002",
        "ws": "ws://localhost:8002",
    },
    "fraud-alert": {
        "http": "http://localhost:8003",
        "ws": "ws://localhost:8003",
    },
}

if settings.app_env != "development":
    SERVICES = {
        "fl-coordinator": {
            "http": "http://fl-coordinator:8001",
            "ws": "ws://fl-coordinator:8001",
        },
        "identity-graph": {
            "http": "http://identity-graph:8002",
            "ws": "ws://identity-graph:8002",
        },
        "fraud-alert": {
            "http": "http://fraud-alert:8003",
            "ws": "ws://fraud-alert:8003",
        },
    }

PATH_ROUTING = {
    "/api/v1/simulations": "fl-coordinator",
    "/api/v1/banks": "fl-coordinator",
    "/api/v1/training": "fl-coordinator",
    "/api/v1/registry": "fl-coordinator",
    "/api/v1/entities": "identity-graph",
    "/api/v1/graph": "identity-graph",
    "/api/v1/alerts": "fraud-alert",
    "/api/v1/cases": "fraud-alert",
    "/api/v1/scenarios": "fraud-alert",
    "/api/v1/dashboard": "fraud-alert",
}

# ── Gateway Helpers ───────────────────────────────────────────


def get_api_keys() -> dict[str, tuple[str, str]]:
    keys_map = {}
    for item in settings.gateway_api_keys.split(","):
        if not item:
            continue
        parts = item.split(":")
        if len(parts) == 3:
            keys_map[parts[0]] = (parts[1], parts[2])
    return keys_map


def check_rate_limit(client_id: str) -> bool:
    minute_bucket = int(time.time() / 60)
    key = f"rl:{client_id}:{minute_bucket}"
    val = _rate_limiter.get(key)
    count = val.get("count", 0) if val else 0
    if count >= settings.gateway_rate_limit:
        return False
    _rate_limiter.set(key, {"count": count + 1}, ex=60)
    return True


def authenticate_request(request_or_websocket: Request | WebSocket) -> tuple[str, str, str | None]:
    """Authenticate request or websocket using API keys.

    Returns:
        tuple: (identity, role, api_key_used)
    """
    api_key = None
    if isinstance(request_or_websocket, Request):
        api_key = request_or_websocket.headers.get("X-API-Key")
        if not api_key:
            auth_header = request_or_websocket.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header.split(" ")[1]
    else:  # WebSocket
        api_key = request_or_websocket.query_params.get(
            "api_key"
        ) or request_or_websocket.headers.get("x-api-key")

    if api_key:
        keys_map = get_api_keys()
        if api_key in keys_map:
            identity, role = keys_map[api_key]
            return identity, role, api_key

    if settings.gateway_require_auth:
        return "", "", api_key

    return "analyst", "analyst", api_key


def check_authorization(
    identity: str, role: str, full_path: str, query_params: dict, method: str
) -> bool:
    if role == "analyst":
        return True

    if role == "bank":
        # Banks cannot trigger/run simulations, dashboards, or edit scenarios
        if full_path.startswith("/api/v1/simulations") and method != "GET":
            return False
        if full_path.startswith("/api/v1/scenarios"):
            return False
        if full_path.startswith("/api/v1/dashboard"):
            return False

        # Banks can only query metrics filtering by their own bank_id
        bank_id_param = query_params.get("bank_id")
        if bank_id_param and bank_id_param != identity:
            return False

    return True


def check_ws_authorization(identity: str, role: str, ws_path: str) -> bool:
    if role == "analyst":
        return True
    if role == "bank":
        # Banks are not permitted to see global training outputs
        return not ws_path.startswith("/ws/training")
    return False


# ── Swagger Docs Aggregation ──────────────────────────────────


@router.get("/docs/{service_name}", include_in_schema=False)
async def service_docs(service_name: str):
    """Serve Swagger UI page for a specific downstream microservice."""
    if service_name not in SERVICES:
        return Response(content="Service docs not found", status_code=404)
    return get_swagger_ui_html(
        openapi_url=f"/openapi/{service_name}.json",
        title=f"{service_name.replace('-', ' ').title()} API Docs",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@router.get("/openapi/{service_name}.json", include_in_schema=False)
async def service_openapi(service_name: str):
    """Fetch and return the OpenAPI JSON schema for a specific downstream microservice."""
    if service_name not in SERVICES:
        return Response(content="Service not found", status_code=404)

    target_host = SERVICES[service_name]["http"]
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{target_host}/openapi.json")
            data = resp.json()
            return data
        except Exception as e:
            logger.error(f"Failed to fetch OpenAPI for {service_name}: {e}")
            return Response(content=f"Error loading docs: {e}", status_code=502)


# ── Dynamic HTTP Proxying ───────────────────────────────────


@router.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
)
async def http_proxy(request: Request, path: str):
    """Proxy HTTP requests to the corresponding downstream microservice."""
    start_time = time.time()
    full_path = f"/ {path}".replace(" ", "")
    if not full_path.startswith("/"):
        full_path = "/" + full_path

    # Versioning Check
    if full_path.startswith("/api/") and not full_path.startswith("/api/v1/"):
        return Response(content="Gateway Error: Unsupported API Version", status_code=400)

    client_ip = request.client.host if request.client else "unknown"

    # Authenticate Request
    identity, role, api_key = authenticate_request(request)
    if not identity:
        return Response(content="Gateway Error: Unauthorized key", status_code=401)

    # Rate Limiting
    client_id = api_key or client_ip
    if not check_rate_limit(client_id):
        return Response(content="Gateway Error: Too Many Requests", status_code=429)

    # Determine downstream target service
    target_service = None
    for prefix, service_name in PATH_ROUTING.items():
        if full_path.startswith(prefix):
            target_service = service_name
            break

    if not target_service:
        if full_path in ("/health", "/api/health", "/api/v1/health"):
            return {"status": "ok", "service": "gateway"}
        return Response(content="Gateway: Path not mapped to any microservice", status_code=404)

    # Extract headers and body
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    body = await request.body()
    query_params = dict(request.query_params)

    # Authorization Check & Parameter Injection
    if not check_authorization(identity, role, full_path, query_params, request.method):
        return Response(content="Gateway Error: Forbidden", status_code=403)

    if role == "bank" and "bank_id" not in query_params:
        query_params["bank_id"] = identity

    target_host = SERVICES[target_service]["http"]
    target_url = f"{target_host}{full_path}"

    status_code = 502
    try:
        async with httpx.AsyncClient() as client:
            downstream_resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
                timeout=30.0,
            )

            resp_headers = dict(downstream_resp.headers)
            resp_headers.pop("content-encoding", None)
            resp_headers.pop("content-length", None)

            status_code = downstream_resp.status_code
            return Response(
                content=downstream_resp.content,
                status_code=downstream_resp.status_code,
                headers=resp_headers,
            )
    except Exception as e:
        logger.error(f"Gateway proxy error to {target_url}: {e}")
        return Response(content=f"Gateway Error: {str(e)}", status_code=502)
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "GATEWAY: %s - %s %s - Auth: %s (%s) - Status: %s - Time: %dms",
            client_ip,
            request.method,
            full_path,
            identity,
            role,
            status_code,
            duration_ms,
        )


# ── Dynamic WebSocket Proxying ────────────────────────────────


@router.websocket("/ws/{path:path}")
async def ws_proxy(websocket: WebSocket, path: str):
    """Proxy WebSocket connections to the corresponding downstream microservice."""
    start_time = time.time()
    ws_path = f"/ws/{path}"
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Authenticate WS
    identity, role, api_key = authenticate_request(websocket)
    if not identity:
        await websocket.accept()
        await websocket.close(code=3000, reason="Gateway Error: Unauthorized key")
        return

    # Rate Limiting
    client_id = api_key or client_ip
    if not check_rate_limit(client_id):
        await websocket.accept()
        await websocket.close(code=1013, reason="Gateway Error: Too Many Requests")
        return

    # Authorization Check
    if not check_ws_authorization(identity, role, ws_path):
        await websocket.accept()
        await websocket.close(code=3000, reason="Gateway Error: Forbidden")
        return

    await websocket.accept()

    target_service = None
    if ws_path.startswith("/ws/training"):
        target_service = "fl-coordinator"
    elif ws_path.startswith("/ws/streaming"):
        target_service = "fraud-alert"

    if not target_service:
        await websocket.close(code=4004, reason="Gateway: WS path not mapped")
        return

    target_host = SERVICES[target_service]["ws"]
    target_url = f"{target_host}{ws_path}"

    status_code = 1011
    try:
        async with websockets.connect(target_url) as downstream_ws:
            status_code = 1000

            async def forward_to_client():
                try:
                    async for message in downstream_ws:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    pass

            async def forward_to_server():
                try:
                    async for message in websocket.iter_text():
                        await downstream_ws.send(message)
                except Exception:
                    pass

            await asyncio.gather(forward_to_client(), forward_to_server())

    except WebSocketDisconnect:
        status_code = 1000
        logger.debug(f"Client disconnected from gateway websocket proxy for {ws_path}")
    except Exception as e:
        logger.error(f"Gateway WebSocket proxy error for {ws_path}: {e}")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "GATEWAY_WS: %s - %s - Auth: %s (%s) - Closed: %s - Time: %dms",
            client_ip,
            ws_path,
            identity,
            role,
            status_code,
            duration_ms,
        )
