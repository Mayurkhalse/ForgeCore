"""Test fixtures and code-change patches for Sarthi E2E workflow testing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forgecore.core.verify.trust import CommandTrustManager

FASTAPI_SHIM = '''"""Lightweight offline FastAPI compatibility shim over Starlette."""
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

FASTAPI_TESTCLIENT_SHIM = '''"""Lightweight test client shim over Starlette."""
from starlette.testclient import TestClient

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
line-length = 100
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

from typing import Optional

USERS_DB = {
    "alice": "secret123",
    "bob": "securepass456",
}


def authenticate_user(username: Optional[str], password: Optional[str]) -> bool:
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
