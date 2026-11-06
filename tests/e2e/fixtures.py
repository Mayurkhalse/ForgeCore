"""Test fixtures and code-change patches for Sarthi E2E workflow testing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forgecore.core.verify.trust import CommandTrustManager

FASTAPI_SHIM = '''"""Lightweight offline FastAPI compatibility shim over Starlette."""
from __future__ import annotations

from typing import Any, Callable

from starlette import status
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

__all__ = ["FastAPI", "HTTPException", "Request", "JSONResponse", "status"]


class FastAPI(Starlette):
    def get(self, path: str, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, methods=["GET"])
            return func
        return decorator

    def post(self, path: str, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, methods=["POST"])
            return func
        return decorator
'''

FASTAPI_TESTCLIENT_SHIM = '''"""Lightweight in-process ASGI test client shim avoiding external sockets and event loops."""
from __future__ import annotations

import inspect
import json
import urllib.parse
from typing import Any


class _TestResponse:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.content = body
        self.text = body.decode("utf-8", errors="replace")
        try:
            self._json_data = json.loads(self.text) if self.text else None
        except Exception:
            self._json_data = None

    def json(self) -> Any:
        return self._json_data


def _run_coro_sync(coro: Any) -> Any:
    stack = [coro]
    val = None
    while stack:
        top = stack[-1]
        try:
            nxt = top.send(val)
            if inspect.iscoroutine(nxt):
                stack.append(nxt)
                val = None
            else:
                val = nxt
        except StopIteration as e:
            stack.pop()
            val = e.value
    return val


class TestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, url: str, **kwargs: Any) -> _TestResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> _TestResponse:
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> _TestResponse:
        split = urllib.parse.urlsplit(url)
        path = split.path or "/"
        query = split.query or ""

        headers = kwargs.get("headers")
        req_headers: list[tuple[bytes, bytes]] = []
        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("latin-1"), str(v).encode("latin-1")))

        body_bytes = b""
        if "json" in kwargs and kwargs["json"] is not None:
            body_bytes = json.dumps(kwargs["json"]).encode("utf-8")
            req_headers.append((b"content-type", b"application/json"))
            req_headers.append((b"content-length", str(len(body_bytes)).encode("ascii")))
        elif "data" in kwargs and kwargs["data"] is not None:
            d = kwargs["data"]
            body_bytes = d if isinstance(d, bytes) else str(d).encode("utf-8")

        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query.encode("ascii"),
            "headers": req_headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }

        req_complete = False

        async def receive() -> dict[str, Any]:
            nonlocal req_complete
            if not req_complete:
                req_complete = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.disconnect"}

        status_code = 500
        resp_headers: dict[str, str] = {}
        resp_body = bytearray()

        async def send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                for k, v in message.get("headers", []):
                    resp_headers[k.decode("latin-1").lower()] = v.decode("latin-1")
            elif message["type"] == "http.response.body":
                resp_body.extend(message.get("body", b""))

        _run_coro_sync(self.app(scope, receive, send))
        return _TestResponse(status_code, resp_headers, bytes(resp_body))


__all__ = ["TestClient"]
'''

PYPROJECT_TOML = """[project]
name = "login-api"
version = "0.1.0"
description = "FastAPI authentication service"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.0.0",
]

[tool.pytest.ini_options]
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]

[tool.ruff]
line-length = 120
extend-exclude = ["fastapi"]

[tool.ruff.lint]
select = ["E", "F"]
ignore = ["E501"]
"""

PROJECT_YAML = """version: 1
project:
  name: "login-api"
  type: "service"
verify:
  fail_on: "high"
  commands:
    test: "pytest -q"
generation:
  require_plan: true
  require_tests: true
rules:
  profiles:
    - "standard"
"""

APP_MODELS = """from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
"""

APP_AUTH = '''"""Authentication and credential verification logic."""

from __future__ import annotations

USERS_DB = {
    "alice": "secret123",
    "bob": "securepass456",
}


def authenticate_user(username: str | None, password: str | None) -> bool:
    if not username or not password:
        return False
    return USERS_DB.get(username) == password
'''

APP_MAIN_INITIAL = '''"""Main FastAPI application for authentication service."""

from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

from app.auth import authenticate_user

app = FastAPI()


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/auth/login")
async def login(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        data = {}

    username = data.get("username")
    password = data.get("password")

    if not authenticate_user(username, password):
        return JSONResponse(
            {"detail": "Invalid credentials"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return JSONResponse({
        "access_token": f"token_for_{username}",
        "token_type": "bearer",
    })
'''

TESTS_LOGIN_INITIAL = """from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_login_success():
    response = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["access_token"] == "token_for_alice"
    assert payload["token_type"] == "bearer"


def test_login_invalid_credentials():
    response = client.post("/auth/login", json={"username": "alice", "password": "wrongpassword"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_unknown_user():
    response = client.post("/auth/login", json={"username": "unknown", "password": "any"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
"""

README_INITIAL = """# Login API Service

FastAPI-based authentication microservice.

## Endpoints
- `GET /health` - Health check endpoint
- `POST /auth/login` - User login with username and password
"""

# Patches for Stage G code change simulation

VALID_RATE_LIMIT_PATCH = {
    "app/rate_limiter.py": '''"""In-memory rate limiter with sliding window tracking."""

import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = [t for t in self.attempts[key] if t > cutoff]
        self.attempts[key] = timestamps

        if len(timestamps) >= self.max_attempts:
            return True

        self.attempts[key].append(now)
        return False

    def reset(self) -> None:
        self.attempts.clear()


limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=60)
''',
    "app/main.py": '''"""Main FastAPI application for authentication service with rate limiting."""

from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

from app.auth import authenticate_user
from app.rate_limiter import limiter

app = FastAPI()


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/auth/login")
async def login(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        data = {}

    username = data.get("username", "anonymous")
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{username}"

    if limiter.is_rate_limited(rate_key):
        return JSONResponse(
            {"detail": "Rate limit exceeded. Try again later."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    password = data.get("password")
    if not authenticate_user(username, password):
        return JSONResponse(
            {"detail": "Invalid credentials"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return JSONResponse({
        "access_token": f"token_for_{username}",
        "token_type": "bearer",
    })
''',
    "tests/test_login.py": """from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limiter import limiter

client = TestClient(app)


def setup_function():
    limiter.reset()


def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_login_success():
    response = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["access_token"] == "token_for_alice"
    assert payload["token_type"] == "bearer"


def test_login_invalid_credentials():
    response = client.post("/auth/login", json={"username": "alice", "password": "wrongpassword"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_unknown_user():
    response = client.post("/auth/login", json={"username": "unknown", "password": "any"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_rate_limiting():
    # Execute 5 invalid attempts (allowed by rate limiter)
    for _ in range(5):
        resp = client.post("/auth/login", json={"username": "attacker", "password": "bad"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 6th attempt must be rejected with 429 Too Many Requests
    blocked_resp = client.post("/auth/login", json={"username": "attacker", "password": "bad"})
    assert blocked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert blocked_resp.json()["detail"] == "Rate limit exceeded. Try again later."
""",
    "README.md": """# Login API Service

FastAPI-based authentication microservice.

## Endpoints
- `GET /health` - Health check endpoint
- `POST /auth/login` - User login with username and password

## Security & Rate Limiting
- Login endpoint is protected with a rate limiter allowing a maximum of 5 requests per 60 seconds per client IP/user.
- Exceeding the threshold returns `429 Too Many Requests`.
""",
}

FAILING_TEST_PATCH = {
    "tests/test_failing.py": """def test_forced_failure():
    assert False, "Forced failure for adversarial scenario 8"
"""
}

MALFORMED_PATCH = {
    "app/main.py": "def broken_syntax(\n    incomplete python code with missing closing parenthesis"
}


def create_login_api_fixture(
    base_dir: Path,
    trust_mgr: CommandTrustManager | None = None,
) -> Path:
    """Creates an isolated, complete FastAPI login microservice fixture with Git initialized."""
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1. FastAPI compatibility shim
    fastapi_dir = base_dir / "fastapi"
    fastapi_dir.mkdir(exist_ok=True)
    (fastapi_dir / "__init__.py").write_text(FASTAPI_SHIM, encoding="utf-8")
    testclient_dir = fastapi_dir / "testclient"
    testclient_dir.mkdir(exist_ok=True)
    (testclient_dir / "__init__.py").write_text(FASTAPI_TESTCLIENT_SHIM, encoding="utf-8")

    # 2. Application sources
    app_dir = base_dir / "app"
    app_dir.mkdir(exist_ok=True)
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "models.py").write_text(APP_MODELS, encoding="utf-8")
    (app_dir / "auth.py").write_text(APP_AUTH, encoding="utf-8")
    (app_dir / "main.py").write_text(APP_MAIN_INITIAL, encoding="utf-8")

    # 3. Tests
    tests_dir = base_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_login.py").write_text(TESTS_LOGIN_INITIAL, encoding="utf-8")

    # 4. Manifests and config
    (base_dir / "pyproject.toml").write_text(PYPROJECT_TOML, encoding="utf-8")
    (base_dir / "README.md").write_text(README_INITIAL, encoding="utf-8")

    forgecore_dir = base_dir / ".forgecore"
    forgecore_dir.mkdir(exist_ok=True)
    (forgecore_dir / "project.yaml").write_text(PROJECT_YAML, encoding="utf-8")

    # 5. Git repository initialization
    subprocess.run(["git", "init"], cwd=str(base_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Sarthi CI"],
        cwd=str(base_dir),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "ci@sarthi.dev"],
        cwd=str(base_dir),
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=str(base_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial login service commit"],
        cwd=str(base_dir),
        check=True,
        capture_output=True,
    )

    # 6. Approve command in trust manager if supplied
    if trust_mgr is not None:
        trust_mgr.approve(base_dir, {"test": "pytest -q"})

    return base_dir
