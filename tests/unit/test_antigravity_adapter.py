from __future__ import annotations

import json
from pathlib import Path

from forgecore.adapters.antigravity.adapter import AntigravityAdapter
from forgecore.adapters.base import InstallOpts


def test_install_clean(tmp_path: Path) -> None:
    """Clean install creates mcp_config.json, GEMINI.md, and manifest."""
    config_dir = tmp_path / ".gemini" / "config"
    adapter = AntigravityAdapter(config_dir=config_dir)

    result = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert result.success is True

    assert adapter.mcp_config_path.is_file()
    assert adapter.global_rule_path.is_file()
    assert adapter.manifest_path.is_file()

    # mcp_config contains forgecore
    mcp_data = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "forgecore" in mcp_data["mcpServers"]

    # GEMINI.md contains core contract
    content = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "<!-- FORGECORE-MANAGED-START -->" in content
    assert "<!-- FORGECORE-MANAGED-END -->" in content


def test_install_creates_backups_and_preserves_user_content(tmp_path: Path) -> None:
    """Existing mcp_config.json and GEMINI.md are backed up to .bak files

    and user configurations are preserved.
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

    # Install
    result = adapter.install(InstallOpts(workspace_root=tmp_path, with_scaffold=False))
    assert result.success is True

    # 1. Backups created
    mcp_bak = adapter.mcp_config_path.with_suffix(".json.bak")
    rule_bak = adapter.global_rule_path.with_suffix(".md.bak")
    assert mcp_bak.is_file()
    assert rule_bak.is_file()
    assert json.loads(mcp_bak.read_text(encoding="utf-8")) == orig_mcp
    assert rule_bak.read_text(encoding="utf-8") == orig_rule

    # 2. User content preserved in active files
    active_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "my-custom-tool" in active_mcp["mcpServers"]
    assert "forgecore" in active_mcp["mcpServers"]

    active_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "# User Instructions" in active_rule
    assert "Always be helpful and concise." in active_rule
    assert "<!-- FORGECORE-MANAGED-START -->" in active_rule


def test_uninstall_restores_user_content_and_removes_backups(tmp_path: Path) -> None:
    """Uninstall removes ForgeCore additions and cleans up backup files."""
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

    # Backups cleaned up
    assert not adapter.mcp_config_path.with_suffix(".json.bak").exists()
    assert not adapter.global_rule_path.with_suffix(".md.bak").exists()
    assert not adapter.manifest_path.exists()

    # Active files restored
    restored_mcp = json.loads(adapter.mcp_config_path.read_text(encoding="utf-8"))
    assert "existing" in restored_mcp["mcpServers"]
    assert "forgecore" not in restored_mcp["mcpServers"]

    restored_rule = adapter.global_rule_path.read_text(encoding="utf-8")
    assert "# Custom Persona" in restored_rule
    assert "<!-- FORGECORE-MANAGED-START -->" not in restored_rule
