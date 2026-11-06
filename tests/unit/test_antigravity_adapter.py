from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sarthi.adapters.antigravity.adapter import AntigravityAdapter
from sarthi.adapters.base import InstallOpts
from sarthi.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolates HOME and USERPROFILE to a temporary directory so real user files are never touched."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home


def test_default_config_dir_uses_isolated_home(isolate_home: Path) -> None:
    """Verifies AntigravityAdapter default constructor uses the isolated HOME path."""
    adapter = AntigravityAdapter()
    expected = isolate_home / ".gemini" / "config"
    assert adapter.config_dir == expected
    assert adapter.mcp_config_path == expected / "mcp_config.json"
    assert adapter.global_rule_path == expected / "GEMINI.md"


def test_install_clean(tmp_path: Path) -> None:
    """Clean install creates mcp_config.json, GEMINI.md, and manifest."""
    config_dir = tmp_path / ".gemini" / "config"
    adapter = AntigravityAdapter(config_dir=config_dir)

    result = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert result.success is True

    assert adapter.mcp_config_path.is_file()
    assert adapter.global_rule_path.is_file()
    assert adapter.manifest_path.is_file()

    # mcp_config contains sarthi
    mcp_data = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "sarthi" in mcp_data["mcpServers"]

    # GEMINI.md contains core contract
    content = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "<!-- SARTHI-MANAGED-START -->" in content
    assert "<!-- SARTHI-MANAGED-END -->" in content


def test_install_creates_timestamped_backups_and_never_overwrites(tmp_path: Path) -> None:
    """Existing mcp_config.json and GEMINI.md are backed up to timestamped .bak files

    which are never overwritten even across multiple installs.
    """
    config_dir = tmp_path / ".gemini" / "config"
    config_dir.mkdir(parents=True)

    # Pre-existing user mcp_config
    orig_mcp = {
        "mcpServers": {
            "my-custom-tool": {
                "command": "node",
                "args": ["server.js"],
            }
        }
    }
    adapter = AntigravityAdapter(config_dir=config_dir)
    adapter.mcp_config_path.write_text(json.dumps(orig_mcp, indent=2), encoding="utf-8")

    # Pre-existing user GEMINI.md
    orig_rule = "# User Instructions\nAlways be helpful and concise.\n"
    adapter.global_rule_path.write_text(orig_rule, encoding="utf-8")

    # First Install
    res1 = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert res1.success is True

    # Check that timestamped backups were created
    mcp_baks = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks) == 1
    assert len(rule_baks) == 1
    assert json.loads(mcp_baks[0].read_text(encoding="utf-8")) == orig_mcp
    assert rule_baks[0].read_text(encoding="utf-8") == orig_rule

    # Second Install: must create a new backup, never overwriting the first
    res2 = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert res2.success is True

    mcp_baks2 = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks2 = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks2) == 2
    assert len(rule_baks2) == 2

    # User content preserved in active files
    active_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "my-custom-tool" in active_mcp["mcpServers"]
    assert "sarthi" in active_mcp["mcpServers"]

    active_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "# User Instructions" in active_rule
    assert "Always be helpful and concise." in active_rule
    assert "<!-- SARTHI-MANAGED-START -->" in active_rule


def test_uninstall_restores_user_content_and_preserves_backups(tmp_path: Path) -> None:
    """Uninstall restores original user configuration and never deletes backup files."""
    config_dir = tmp_path / ".gemini" / "config"
    config_dir.mkdir(parents=True)

    adapter = AntigravityAdapter(config_dir=config_dir)
    orig_mcp_text = json.dumps({"mcpServers": {"existing": {"command": "test"}}}, indent=2)
    orig_rule_text = "# Custom Persona\nYou are an expert assistant.\n"

    adapter.mcp_config_path.write_text(orig_mcp_text, encoding="utf-8")
    adapter.global_rule_path.write_text(orig_rule_text, encoding="utf-8")

    # Install then uninstall
    adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    un_res = adapter.uninstall()
    assert un_res.success is True

    # Backups are PRESERVED (never deleted by uninstall)
    mcp_baks = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_baks = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_baks) >= 1
    assert len(rule_baks) >= 1
    assert not adapter.manifest_path.exists()

    # Active files restored
    restored_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "existing" in restored_mcp["mcpServers"]
    assert "sarthi" not in restored_mcp["mcpServers"]

    restored_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "# Custom Persona" in restored_rule
    assert "<!-- SARTHI-MANAGED-START -->" not in restored_rule


def test_refuse_on_invalid_json(tmp_path: Path) -> None:
    """Installer refuses to proceed if existing mcp_config.json contains invalid JSON."""
    config_dir = tmp_path / ".gemini" / "config"
    config_dir.mkdir(parents=True)

    adapter = AntigravityAdapter(config_dir=config_dir)
    corrupted_content = "{ this is not valid json : [ 123"
    adapter.mcp_config_path.write_text(corrupted_content, encoding="utf-8")

    res = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert res.success is False
    assert "contains invalid JSON" in res.message
    # File was not overwritten or corrupted further
    assert adapter.mcp_config_path.read_text(encoding="utf-8") == corrupted_content
    # No backups were created for broken file
    assert list(config_dir.glob("mcp_config.json.*.bak")) == []


def test_dry_run_does_not_modify_disk(tmp_path: Path) -> None:
    """Dry run validates configuration without modifying or creating files on disk."""
    config_dir = tmp_path / ".gemini" / "config"
    adapter = AntigravityAdapter(config_dir=config_dir)

    res = adapter.install(InstallOpts(workspace_root=tmp_path, dry_run=True, with_scaffold=True))
    assert res.success is True
    assert "[Dry Run]" in res.message
    assert not config_dir.exists()
    assert not (tmp_path / ".sarthi" / "project.yaml").exists()


def test_dry_run_refuses_invalid_json(tmp_path: Path) -> None:
    """Dry run validates existing configuration and flags invalid JSON."""
    config_dir = tmp_path / ".gemini" / "config"
    config_dir.mkdir(parents=True)
    adapter = AntigravityAdapter(config_dir=config_dir)
    adapter.mcp_config_path.write_text("invalid json", encoding="utf-8")

    res = adapter.install(InstallOpts(workspace_root=tmp_path, dry_run=True))
    assert res.success is False
    assert "contains invalid JSON" in res.message


def test_cli_dry_run(isolate_home: Path) -> None:
    """Tests the CLI --dry-run option for install antigravity."""
    result = runner.invoke(app, ["install", "antigravity", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry Run" in result.stdout
    # Verify no files were created in isolated home
    assert not (isolate_home / ".gemini").exists()


def test_install_uninstall_roundtrip_byte_identical(isolate_home: Path, tmp_path: Path) -> None:
    """Round-trip: install then uninstall against pre-existing files restores exact bytes.

    Asserts that mcp_config.json and GEMINI.md are byte-identical afterward,
    and timestamped backups are preserved.
    """
    config_dir = isolate_home / ".gemini" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    adapter = AntigravityAdapter(config_dir=config_dir)

    # Realistic pre-existing mcp_config.json with custom indentation and ordering
    orig_mcp_bytes = (
        b'{\n'
        b'    "mcpServers": {\n'
        b'        "github": {\n'
        b'            "command": "npx",\n'
        b'            "args": [\n'
        b'                "-y",\n'
        b'                "@modelcontextprotocol/server-github"\n'
        b'            ],\n'
        b'            "env": {\n'
        b'                "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_secret123"\n'
        b'            }\n'
        b'        }\n'
        b'    }\n'
        b'}\n'
    )
    # Realistic pre-existing GEMINI.md with custom formatting and spacing
    orig_rule_bytes = (
        b"# Custom Engineering Directives\n\n"
        b"- Always write clean, well-tested Python code.\n"
        b"- Enforce ruff linting before committing.\n\n"
        b"<!-- Persona: Strict Pair Programmer -->\n"
    )

    adapter.mcp_config_path.write_bytes(orig_mcp_bytes)
    adapter.global_rule_path.write_bytes(orig_rule_bytes)

    # 1. Install
    install_res = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert install_res.success is True
    # Verify files were modified during install
    assert adapter.mcp_config_path.read_bytes() != orig_mcp_bytes
    assert adapter.global_rule_path.read_bytes() != orig_rule_bytes

    # 2. Uninstall
    uninstall_res = adapter.uninstall()
    assert uninstall_res.success is True

    # 3. Assert byte-identical restoration
    assert adapter.mcp_config_path.read_bytes() == orig_mcp_bytes
    assert adapter.global_rule_path.read_bytes() == orig_rule_bytes

    # 4. Verify backups are preserved on disk and manifest removed
    assert not adapter.manifest_path.exists()
    mcp_backups = list(config_dir.glob("mcp_config.json.*.bak"))
    rule_backups = list(config_dir.glob("GEMINI.md.*.bak"))
    assert len(mcp_backups) == 1
    assert len(rule_backups) == 1
    assert mcp_backups[0].read_bytes() == orig_mcp_bytes
    assert rule_backups[0].read_bytes() == orig_rule_bytes

