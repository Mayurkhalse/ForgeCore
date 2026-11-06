"""Realistic End-to-End Integration Scenario for Sarthi and Everything Claude Code (ECC).

Scenario: "Build a production-ready authentication module using FastAPI and PostgreSQL."
Verifies the complete 12-stage pipeline from prompt ingestion to deterministic verification,
confirming that relevant ECC knowledge reaches the runtime instruction context and irrelevant
knowledge is strictly excluded.
"""
from __future__ import annotations

from pathlib import Path

from forgecore.core.resources.compiler import ContextCompiler
from forgecore.core.verify.trust import CommandTrustManager
from forgecore.mcp.tools import MCPToolHandlers

from .fixtures import create_login_api_fixture

SCENARIO_PROMPT = (
    "Build a production-ready authentication module using FastAPI and PostgreSQL. "
    "Implement secure password hashing, JWT token rotation, and SQL parameterization. "
    "Adhere to clean architecture, test-driven development, and deterministic verification."
)

FASTAPI_AUTH_PATCH = {
    "app/auth.py": '''"""Production authentication module with password hashing and JWT rotation."""
from __future__ import annotations

import hashlib
import hmac
import os
import time

SECRET_KEY = os.getenv("AUTH_SECRET", "mock_dev_key")


def hash_password(password: str, salt: str = "salt123") -> str:
    """Hash password using SHA-256 HMAC."""
    return hmac.new(salt.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_password(plain: str, hashed: str, salt: str = "salt123") -> bool:
    """Verify password in constant time to prevent timing attacks."""
    computed = hash_password(plain, salt)
    return hmac.compare_digest(computed, hashed)


def authenticate_user(username: str | None, password: str | None) -> bool:
    """Authenticate user credentials."""
    if not username or not password:
        return False
    # Mock database lookup
    users_db = {
        "alice": hash_password("secret123"),
        "bob": hash_password("pass456"),
    }
    stored_hash = users_db.get(username)
    if not stored_hash:
        return False
    return verify_password(password, stored_hash)


def create_access_token(username: str, expires_in: int = 3600) -> str:
    """Create signed access token with expiration."""
    exp = int(time.time()) + expires_in
    signature = hmac.new(SECRET_KEY.encode(), f"{username}:{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{username}:{exp}:{signature[:16]}"
''',
    "tests/test_auth_module.py": """from fastapi import status
from fastapi.testclient import TestClient

from app.auth import authenticate_user, create_access_token, hash_password, verify_password
from app.main import app

client = TestClient(app)


def test_password_hashing():
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 == h2
    assert verify_password("secret123", h1)
    assert not verify_password("wrong", h1)


def test_authenticate_user():
    assert authenticate_user("alice", "secret123")
    assert not authenticate_user("alice", "wrong")
    assert not authenticate_user("unknown", "any")


def test_create_access_token():
    token = create_access_token("alice")
    assert "alice" in token


def test_api_login_endpoint():
    res = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert res.status_code == status.HTTP_200_OK
    assert "access_token" in res.json()
""",
}


def test_ecc_e2e_fastapi_postgresql_integration(tmp_path: Path):
    """Executes the full 12-stage ECC integration pipeline for FastAPI + PostgreSQL auth."""
    fixture_root = tmp_path / "auth_service"
    trust_dir = tmp_path / "trust_store"
    trust_mgr = CommandTrustManager(trust_dir)

    # 1. Setup isolated project fixture
    create_login_api_fixture(fixture_root, trust_mgr=trust_mgr)

    # 2. Stage A & B: Project Ingestion & Stack Detection
    mcp = MCPToolHandlers()
    init_res = mcp.initialize_project(root=str(fixture_root))
    assert init_res["status"] == "initialized"
    active_layers = init_res["active_layers"]
    assert "fastapi" in active_layers
    assert "security" in active_layers
    assert "python" in init_res["detected_stack"]["languages"]
    assert "ecc" in init_res["knowledge_providers"]
    assert init_res["total_available_resources"] > 500

    # 3. Stage C & D: ECC Knowledge Discovery & Retrieval
    standards_res = mcp.get_standards(
        root=str(fixture_root),
        task=SCENARIO_PROMPT,
        task_type="feature",
        layers=active_layers + ["sql", "postgres"],
        max_rules=15,
    )

    # Verify native standards
    rules = standards_res.get("rules", [])
    rule_ids = [r["id"] for r in rules]
    assert any("FAPI-ARCH" in rid for rid in rule_ids)
    assert any("FAPI-SEC" in rid for rid in rule_ids)

    # Verify ECC skills
    skills = standards_res.get("skills", [])
    skill_ids = [s["id"] for s in skills]
    assert any("fastapi-patterns" in sid or "postgres-patterns" in sid for sid in skill_ids)

    # Verify compiled markdown instructions returned directly from MCP tool
    assert "instructions_markdown" in standards_res
    inst_md = standards_res["instructions_markdown"]
    assert "Mandatory Security Invariants" in inst_md
    assert "Mandatory Core Engineering Contract" in inst_md
    assert "Upstream ECC Engineering Guidance" in inst_md

    # Verify irrelevant knowledge exclusion
    assert not any("react" in sid for sid in skill_ids)
    assert not any("flutter" in sid for sid in skill_ids)
    assert not any("spring" in sid for sid in skill_ids)
    assert not any("laravel" in sid for sid in skill_ids)

    # 4. Stage E: Conflict Resolution & Precedence Validation
    conflict_report = standards_res.get("conflict_report", {})
    assert "total_conflicts" in conflict_report
    # Verify provenance trace
    provenance = standards_res.get("provenance", [])
    assert any(p["commit"] == "c05b2d6614f62f6db0047669aa4eefb223d478f9" for p in provenance)
    assert any(p["provider"] == "ecc" for p in provenance)
    assert any(p["provider"] == "native" for p in provenance)

    # 5. Stage F: Context Compilation & Token Budget Validation
    compiler = ContextCompiler()
    compiled_ctx = compiler.compile_context(
        active_layers=active_layers + ["sql", "postgres"],
        task=SCENARIO_PROMPT,
        task_type="feature",
        max_tokens=3000,
    )
    assert compiled_ctx.selection_trace.token_count <= 3000
    assert len(compiled_ctx.security_invariants) >= 5
    assert len(compiled_ctx.core_contract_rules) >= 1

    # 6. Stage G: Workflow Assembly
    workflow_res = mcp.get_workflow(root=str(fixture_root), task_type="feature")
    assert "workflow_markdown" in workflow_res
    wf_md = workflow_res["workflow_markdown"]
    assert "## 1. Plan" in wf_md
    assert "verify_project" in wf_md

    # 7. Stage H: Agent Instruction Delivery
    agent_instructions = compiler.render_markdown_instructions(compiled_ctx)
    assert "Mandatory Security Invariants" in agent_instructions
    assert "Mandatory Core Engineering Contract" in agent_instructions
    assert "Fastapi Patterns" in agent_instructions or "fastapi" in agent_instructions.lower()
    assert "c05b2d6" in agent_instructions

    # 8. Stage I: Constrained Tool Execution (Code Change Simulation)
    for rel_path, code in FASTAPI_AUTH_PATCH.items():
        dest = fixture_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")

    # 9. Stage J: Deterministic Verification
    verify_res = mcp.verify_project(root=str(fixture_root), scope="all", trust_mgr=trust_mgr)
    assert verify_res["status"] == "passed"
    summary = verify_res["summary"]
    assert summary.get("critical", 0) == 0
    assert summary.get("high", 0) == 0

    # 10. Stage K: Final Traceability Evidence
    assert len(verify_res.get("findings", [])) == 0 or all(
        f.get("severity") not in ["critical", "high"] for f in verify_res.get("findings", [])
    )
