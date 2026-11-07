"""Deterministic offline end-to-end integration test for the Sarthi Antigravity integration lifecycle.

Validates the complete 7-step lifecycle:
1. Installation into an isolated configuration directory with pre-existing user configs.
2. Staging a realistic FastAPI microservice with /items endpoint and PostgreSQL metadata.
3. Session initialization via MCP tool handlers detecting stack and layers.
4. Prompt-based standards retrieval confirming native rules and ECC postgres-patterns skill.
5. Negative verification blocking on an intentional flaw.
6. Remediation and verification unblocking the completion gate.
7. Uninstallation restoring original configs byte-for-byte while preserving backups.

Also validates lifecycle safety invariants:
- Installation idempotency (repeated install is safe and creates new timestamped backups).
- Uninstallation idempotency (repeated uninstall returns success without crashing).
- Corrupted configuration resilience (malformed JSON rejected safely without data loss).
- Isolated home directory protection (never writes outside the temporary test directory).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sarthi.adapters.antigravity.adapter import AntigravityAdapter
from sarthi.adapters.base import InstallOpts
from sarthi.core.verify.trust import CommandTrustManager
from sarthi.mcp.tools import MCPToolHandlers

from .fixtures import FASTAPI_SHIM, FASTAPI_TESTCLIENT_SHIM

RATE_LIMITING_TASK_PROMPT = "Add rate limiting to the /items endpoint using PostgreSQL-backed persistence."

ITEMS_PYPROJECT_TOML = """[project]
name = "items-service"
version = "0.1.0"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.0.0",
    "asyncpg>=0.29.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
extend-exclude = ["fastapi"]

[tool.ruff.lint]
select = ["E", "F"]
ignore = ["E501"]
"""

ITEMS_PROJECT_YAML = """version: 1
project:
  name: "items-service"
  type: "service"
layers:
  add:
    - "postgres"
    - "sql"
verify:
  fail_on: "high"
  commands:
    test: "pytest -q"
generation:
  require_plan: true
  require_tests: true
"""

ITEMS_README_INITIAL = """# Items Service

FastAPI-based item catalog microservice with PostgreSQL persistence.

## Endpoints
- `GET /health` - Health check
- `GET /items` - List catalog items
"""

ITEMS_APP_INITIAL = '''"""Main FastAPI application for items service."""
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

app = FastAPI()

ITEMS_DB = [
    {"id": 1, "name": "Hammer", "category": "tools"},
    {"id": 2, "name": "Nails", "category": "hardware"},
]


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/items")
async def get_items(request: Request) -> JSONResponse:
    return JSONResponse(ITEMS_DB)
'''

ITEMS_TESTS_INITIAL = """from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_get_items():
    response = client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Hammer"
"""

FLAWED_ITEMS_PATCH = {
    "app/main.py": '''"""Main FastAPI application with flawed rate limiting."""
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

app = FastAPI()

ITEMS_DB = [
    {"id": 1, "name": "Hammer", "category": "tools"},
    {"id": 2, "name": "Nails", "category": "hardware"},
]


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/items")
async def get_items(request: Request) -> JSONResponse:
    # Intentional flaw: rate limiting counter is never incremented,
    # so requests exceeding the rate limit are never blocked.
    return JSONResponse(ITEMS_DB)
''',
    "tests/test_items.py": """from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_get_items():
    response = client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


def test_items_rate_limiting_enforcement():
    for _ in range(5):
        resp = client.get("/items")
        assert resp.status_code == status.HTTP_200_OK
    # 6th request must trigger rate limit (429 Too Many Requests)
    resp = client.get("/items")
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
""",
}

REMEDIATED_ITEMS_PATCH = {
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
    "app/main.py": '''"""Main FastAPI application for items service with corrected rate limiting."""
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

from app.rate_limiter import limiter

app = FastAPI()

ITEMS_DB = [
    {"id": 1, "name": "Hammer", "category": "tools"},
    {"id": 2, "name": "Nails", "category": "hardware"},
]


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/items")
async def get_items(request: Request) -> JSONResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    if limiter.is_rate_limited(client_ip):
        return JSONResponse(
            {"detail": "Rate limit exceeded. Try again later."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    return JSONResponse(ITEMS_DB)
''',
    "tests/test_items.py": """from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limiter import limiter

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_get_items():
    limiter.reset()
    response = client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


def test_items_rate_limiting_enforcement():
    limiter.reset()
    for _ in range(5):
        resp = client.get("/items")
        assert resp.status_code == status.HTTP_200_OK
    resp = client.get("/items")
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert resp.json() == {"detail": "Rate limit exceeded. Try again later."}
""",
}


def _create_items_fixture(base_dir: Path, trust_mgr: CommandTrustManager | None = None) -> Path:
    """Creates an isolated, complete FastAPI items microservice fixture with Git initialized."""
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1. FastAPI offline compatibility shim
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
    (app_dir / "main.py").write_text(ITEMS_APP_INITIAL, encoding="utf-8")

    # 3. Tests
    tests_dir = base_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_items.py").write_text(ITEMS_TESTS_INITIAL, encoding="utf-8")

    # 4. Manifests and config
    (base_dir / "pyproject.toml").write_text(ITEMS_PYPROJECT_TOML, encoding="utf-8")
    (base_dir / "README.md").write_text(ITEMS_README_INITIAL, encoding="utf-8")

    sarthi_dir = base_dir / ".sarthi"
    sarthi_dir.mkdir(exist_ok=True)
    (sarthi_dir / "project.yaml").write_text(ITEMS_PROJECT_YAML, encoding="utf-8")

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
        ["git", "commit", "-m", "chore: initial items service commit"],
        cwd=str(base_dir),
        check=True,
        capture_output=True,
    )

    # 6. Pre-approve test command in trust manager
    if trust_mgr is not None:
        trust_mgr.approve(base_dir, {"test": "pytest -q"})

    return base_dir


def test_antigravity_complete_offline_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates the complete 7-step Sarthi Antigravity integration lifecycle."""
    # -------------------------------------------------------------------------
    # Setup isolated environment
    # -------------------------------------------------------------------------
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    config_dir = fake_home / ".gemini" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    adapter = AntigravityAdapter(config_dir=config_dir)

    # Stage realistic pre-existing user configurations
    orig_mcp_bytes = (
        b"{\n"
        b'  "mcpServers": {\n'
        b'    "github": {\n'
        b'      "command": "npx",\n'
        b'      "args": ["-y", "@modelcontextprotocol/server-github"]\n'
        b"    }\n"
        b"  }\n"
        b"}\n"
    )
    orig_rule_bytes = (
        b"# Custom Engineering Directives\n\n"
        b"- Always write clean, well-tested Python code.\n"
        b"- Enforce ruff linting before committing.\n\n"
        b"<!-- Persona: Strict Pair Programmer -->\n"
    )

    adapter.mcp_config_path.write_bytes(orig_mcp_bytes)
    adapter.global_rule_path.write_bytes(orig_rule_bytes)

    # -------------------------------------------------------------------------
    # Step 1: Installation
    # -------------------------------------------------------------------------
    workspace_root = tmp_path / "items_service"
    trust_dir = tmp_path / "trust_store"
    trust_mgr = CommandTrustManager(trust_dir)

    install_result = adapter.install(InstallOpts(workspace_root=workspace_root, with_scaffold=False))
    assert install_result.success is True, f"Install failed: {install_result.message}"

    # Verify MCP server configuration
    assert adapter.mcp_config_path.is_file()
    active_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "sarthi" in active_mcp["mcpServers"]
    assert "github" in active_mcp["mcpServers"]  # Existing server entry preserved
    sarthi_cfg = active_mcp["mcpServers"]["sarthi"]
    assert sarthi_cfg["args"] == ["-m", "sarthi.cli", "serve"]

    # Verify Sarthi Core Contract injected into GEMINI.md
    assert adapter.global_rule_path.is_file()
    active_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "<!-- SARTHI-MANAGED-START -->" in active_rule
    assert "<!-- SARTHI-MANAGED-END -->" in active_rule
    assert "# Custom Engineering Directives" in active_rule  # Existing instructions preserved
    assert "Strict Pair Programmer" in active_rule

    # Verify backups created
    mcp_baks = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks) == 1
    assert len(rule_baks) == 1
    assert mcp_baks[0].read_bytes() == orig_mcp_bytes
    assert rule_baks[0].read_bytes() == orig_rule_bytes

    # -------------------------------------------------------------------------
    # Step 2: Realistic project workspace
    # -------------------------------------------------------------------------
    _create_items_fixture(workspace_root, trust_mgr=trust_mgr)
    assert (workspace_root / "app" / "main.py").is_file()
    assert (workspace_root / "tests" / "test_items.py").is_file()
    assert (workspace_root / ".sarthi" / "project.yaml").is_file()

    # -------------------------------------------------------------------------
    # Step 3: Session initialization
    # -------------------------------------------------------------------------
    mcp = MCPToolHandlers()
    init_res = mcp.initialize_project(root=str(workspace_root))
    assert init_res["status"] == "initialized"
    assert "items-service" in init_res["project_name"]

    detected_stack = init_res["detected_stack"]
    assert "python" in detected_stack["languages"]
    assert "pytest" in detected_stack["test_frameworks"]

    active_layers = init_res["active_layers"]
    assert "fastapi" in active_layers
    assert "security" in active_layers
    assert "postgres" in active_layers
    assert "sql" in active_layers

    assert "ecc" in init_res["knowledge_providers"]
    assert init_res["total_available_resources"] > 500

    # -------------------------------------------------------------------------
    # Step 4: Prompt and standards retrieval
    # -------------------------------------------------------------------------
    standards_res = mcp.get_standards(
        root=str(workspace_root),
        task=RATE_LIMITING_TASK_PROMPT,
        task_type="feature",
        layers=active_layers,
        max_rules=15,
    )
    assert "error" not in standards_res

    # Verify native FastAPI and security rules
    rules = standards_res.get("rules", [])
    rule_ids = [r["id"] for r in rules]
    assert any("FAPI" in rid for rid in rule_ids), f"Expected FAPI rules, got {rule_ids}"
    assert any("SEC" in rid for rid in rule_ids), f"Expected SEC rules, got {rule_ids}"

    # Verify ECC postgres-patterns skill retrieved
    skills = standards_res.get("skills", [])
    skill_ids = [s["id"] for s in skills]
    assert any("postgres-patterns" in sid for sid in skill_ids), f"Expected postgres-patterns, got {skill_ids}"

    # Verify instructions markdown compiled
    inst_md = standards_res.get("instructions_markdown", "")
    assert "Mandatory Security Invariants" in inst_md
    assert "Mandatory Core Engineering Contract" in inst_md
    assert "Upstream ECC Engineering Guidance" in inst_md

    # Verify irrelevant skills are strictly excluded
    assert not any("react" in sid for sid in skill_ids)
    assert not any("flutter" in sid for sid in skill_ids)
    assert not any("spring" in sid for sid in skill_ids)
    assert not any("laravel" in sid for sid in skill_ids)

    # Verify ECC provenance trace
    provenance = standards_res.get("provenance", [])
    assert any(p.get("provider") == "ecc" for p in provenance)
    assert any(p.get("commit") == "c05b2d6614f62f6db0047669aa4eefb223d478f9" for p in provenance)

    # -------------------------------------------------------------------------
    # Step 5: Negative verification (Agent introduces deliberate flaw)
    # -------------------------------------------------------------------------
    for rel_path, content in FLAWED_ITEMS_PATCH.items():
        dest = workspace_root / rel_path
        dest.write_text(content, encoding="utf-8")

    neg_verify_res = mcp.verify_project(root=str(workspace_root), scope="all", trust_mgr=trust_mgr)
    assert neg_verify_res["status"] == "failed", f"Expected verification failure, got: {neg_verify_res}"
    assert neg_verify_res["summary"]["high"] >= 1, "Expected at least 1 high severity finding"

    # Completion gate must remain BLOCKED
    blocking_findings = [f for f in neg_verify_res.get("findings", []) if f.get("severity") in {"critical", "high"}]
    assert len(blocking_findings) >= 1
    assert "Fix" in neg_verify_res.get("next_action", "")
    assert "Ready for review" not in neg_verify_res.get("next_action", "")

    # Useful diagnostic information must be reported
    finding_messages = [f.get("message", "") for f in neg_verify_res.get("findings", [])]
    assert any("Test suite failed" in m for m in finding_messages)

    # -------------------------------------------------------------------------
    # Step 6: Remediation and successful verification
    # -------------------------------------------------------------------------
    for rel_path, content in REMEDIATED_ITEMS_PATCH.items():
        dest = workspace_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    pos_verify_res = mcp.verify_project(root=str(workspace_root), scope="all", trust_mgr=trust_mgr)
    assert pos_verify_res["status"] == "passed", f"Expected verification pass, got: {pos_verify_res}"
    assert pos_verify_res["summary"]["critical"] == 0
    assert pos_verify_res["summary"]["high"] == 0

    # Completion gate is now RELEASED
    pos_blocking = [f for f in pos_verify_res.get("findings", []) if f.get("severity") in {"critical", "high"}]
    assert len(pos_blocking) == 0
    assert "Ready for review" in pos_verify_res.get("next_action", "")

    # -------------------------------------------------------------------------
    # Step 7: Uninstallation
    # -------------------------------------------------------------------------
    uninstall_res = adapter.uninstall()
    assert uninstall_res.success is True, f"Uninstall failed: {uninstall_res.message}"

    # Asserts pre-existing configurations restored byte-for-byte
    assert adapter.mcp_config_path.read_bytes() == orig_mcp_bytes
    assert adapter.global_rule_path.read_bytes() == orig_rule_bytes

    # Manifest removed
    assert not adapter.manifest_path.exists()

    # Backups preserved
    final_mcp_baks = list(config_dir.glob("mcp_config.json.*.bak"))
    final_rule_baks = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(final_mcp_baks) >= 1
    assert len(final_rule_baks) >= 1


def test_antigravity_lifecycle_safety_invariants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates installation idempotency, uninstallation idempotency, and corruption resilience."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    config_dir = fake_home / ".gemini" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    adapter = AntigravityAdapter(config_dir=config_dir)

    # 1. Temporary HOME isolation
    default_adapter = AntigravityAdapter()
    assert default_adapter.config_dir == fake_home / ".gemini" / "config"
    assert default_adapter.mcp_config_path == fake_home / ".gemini" / "config" / "mcp_config.json"
    assert default_adapter.global_rule_path == fake_home / ".gemini" / "config" / "GEMINI.md"

    # Pre-existing user config
    orig_mcp = {"mcpServers": {"existing-tool": {"command": "node", "args": ["app.js"]}}}
    orig_rule = "# Custom Instructions\nBe concise and accurate.\n"
    adapter.mcp_config_path.write_text(json.dumps(orig_mcp, indent=2), encoding="utf-8")
    adapter.global_rule_path.write_text(orig_rule, encoding="utf-8")

    # 2. Installation Idempotency: first install
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    res1 = adapter.install(InstallOpts(workspace_root=workspace, with_scaffold=False))
    assert res1.success is True

    mcp_baks1 = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks1 = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks1) == 1
    assert len(rule_baks1) == 1

    # Installation Idempotency: second install must not duplicate entries and must make a new backup
    res2 = adapter.install(InstallOpts(workspace_root=workspace, with_scaffold=False))
    assert res2.success is True

    mcp_baks2 = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks2 = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks2) == 2
    assert len(rule_baks2) == 2

    active_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "existing-tool" in active_mcp["mcpServers"]
    assert "sarthi" in active_mcp["mcpServers"]

    active_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert active_rule.count("<!-- SARTHI-MANAGED-START -->") == 1
    assert active_rule.count("<!-- SARTHI-MANAGED-END -->") == 1
    assert "# Custom Instructions" in active_rule

    # 3. Uninstallation Idempotency: first uninstall
    un1 = adapter.uninstall()
    assert un1.success is True
    assert not adapter.manifest_path.exists()

    # Second uninstall must not crash or fail even though manifest is gone
    un2 = adapter.uninstall()
    assert un2.success is True

    # 4. Corrupted Config Resilience: installer refuses malformed JSON
    corrupted_json = '{\n  "mcpServers": {\n    unclosed string syntax... \n'
    adapter.mcp_config_path.write_text(corrupted_json, encoding="utf-8")

    corrupt_res = adapter.install(InstallOpts(workspace_root=workspace, with_scaffold=False))
    assert corrupt_res.success is False
    assert "invalid JSON" in corrupt_res.message
    # File was not overwritten or destroyed
    assert adapter.mcp_config_path.read_text(encoding="utf-8") == corrupted_json
