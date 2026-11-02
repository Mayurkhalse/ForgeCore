from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from forgecore.adapters.base import Check, ClientAdapter, InstallOpts, InstallResult
from forgecore.core.config import ConfigLoader
from forgecore.mcp.tools import MCPToolHandlers

MANIFEST_FILE_NAME = "forgecore-manifest.json"


class AntigravityAdapter(ClientAdapter):
    """Client adapter for Google Antigravity (AGY)."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or (Path.home() / ".gemini" / "config")
        self.mcp_config_path = self.config_dir / "mcp_config.json"
        self.global_rule_path = self.config_dir / "GEMINI.md"
        self.manifest_path = self.config_dir / MANIFEST_FILE_NAME

    @property
    def name(self) -> str:
        return "antigravity"

    def detect(self) -> bool:
        """Checks if Antigravity's global directory ~/.gemini exists or if running inside AGY."""
        return (Path.home() / ".gemini").is_dir()

    def install(self, opts: InstallOpts) -> InstallResult:
        """Configures MCP server, writes global rule, and creates optional project scaffold."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            installed_files: list[str] = []

            # 1. Resolve Python executable path
            python_path = sys.executable

            # 2. Update mcp_config.json
            mcp_data = {"mcpServers": {}}
            mcp_backup_path: Path | None = None
            if self.mcp_config_path.is_file():
                mcp_backup_path = self.mcp_config_path.with_suffix(".json.bak")
                shutil.copy2(self.mcp_config_path, mcp_backup_path)
                try:
                    mcp_data = json.loads(self.mcp_config_path.read_text(encoding="utf-8"))
                    if not isinstance(mcp_data, dict):
                        mcp_data = {"mcpServers": {}}
                    if "mcpServers" not in mcp_data:
                        mcp_data["mcpServers"] = {}
                except Exception:
                    mcp_data = {"mcpServers": {}}

            mcp_data["mcpServers"]["forgecore"] = {
                "command": str(python_path),
                "args": ["-m", "forgecore.cli", "serve"],
                "env": {},
            }
            self.mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
            installed_files.append(str(self.mcp_config_path))

            # 3. Write Global Rule File (GEMINI.md)
            contract_path = Path(__file__).resolve().parent.parent.parent.parent / "standards" / "contract.md"
            if contract_path.is_file():
                contract_content = contract_path.read_text(encoding="utf-8")
            else:
                contract_content = "# FORGECORE CORE CONTRACT\nFollow standards and run verify_project before done."

            rule_wrapper = (
                "<!-- FORGECORE-MANAGED-START -->\n"
                f"{contract_content}\n"
                "<!-- FORGECORE-MANAGED-END -->\n"
            )

            # If GEMINI.md already exists, backup and append or replace the managed block
            rule_backup_path: Path | None = None
            if self.global_rule_path.is_file():
                rule_backup_path = self.global_rule_path.with_suffix(".md.bak")
                shutil.copy2(self.global_rule_path, rule_backup_path)
                existing = self.global_rule_path.read_text(encoding="utf-8")
                if "<!-- FORGECORE-MANAGED-START -->" in existing:
                    start_idx = existing.find("<!-- FORGECORE-MANAGED-START -->")
                    end_idx = existing.find("<!-- FORGECORE-MANAGED-END -->") + len("<!-- FORGECORE-MANAGED-END -->")
                    new_content = existing[:start_idx] + rule_wrapper + existing[end_idx:]
                else:
                    new_content = existing + "\n\n" + rule_wrapper
                self.global_rule_path.write_text(new_content, encoding="utf-8")
            else:
                self.global_rule_path.write_text(rule_wrapper, encoding="utf-8")

            installed_files.append(str(self.global_rule_path))

            # 4. Optional Project Scaffold
            if opts.workspace_root and opts.with_scaffold:
                loader = ConfigLoader(opts.workspace_root)
                if not loader.exists():
                    default_cfg = loader.create_default(project_name=opts.workspace_root.name)
                    scaffold_path = loader.save(default_cfg)
                    installed_files.append(str(scaffold_path))

            # 5. Write install manifest
            manifest_data = {
                "installed_by": "forgecore install antigravity",
                "python_path": str(python_path),
                "installed_files": installed_files,
                "added_mcp_server": "forgecore",
                "backups": {
                    "mcp_config": str(mcp_backup_path) if mcp_backup_path else None,
                    "global_rule": str(rule_backup_path) if rule_backup_path else None,
                },
            }
            self.manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

            # 6. Self-test
            handlers = MCPToolHandlers()
            test_res = handlers.initialize_project(str(opts.workspace_root or Path.cwd()))
            if "error" in test_res:
                return InstallResult(
                    success=False,
                    message=f"Installation succeeded but self-test failed: {test_res['error']['message']}",
                    installed_files=installed_files,
                )

            return InstallResult(
                success=True,
                message="Successfully installed ForgeCore for Antigravity! MCP server configured, global rule installed, and self-test passed.",
                installed_files=installed_files,
            )

        except Exception as e:
            return InstallResult(success=False, message=f"Failed to install for Antigravity: {e}")

    def uninstall(self) -> InstallResult:
        """Reverts all changes tracked in the install manifest."""
        try:
            removed: list[str] = []

            # 1. Clean MCP config
            if self.mcp_config_path.is_file():
                try:
                    mcp_data = json.loads(self.mcp_config_path.read_text(encoding="utf-8"))
                    if "mcpServers" in mcp_data and "forgecore" in mcp_data["mcpServers"]:
                        del mcp_data["mcpServers"]["forgecore"]
                        self.mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
                        removed.append("Removed 'forgecore' entry from mcp_config.json")
                except Exception:
                    pass

            # 2. Clean global rule file
            if self.global_rule_path.is_file():
                content = self.global_rule_path.read_text(encoding="utf-8")
                if "<!-- FORGECORE-MANAGED-START -->" in content:
                    start_idx = content.find("<!-- FORGECORE-MANAGED-START -->")
                    end_idx = content.find("<!-- FORGECORE-MANAGED-END -->") + len("<!-- FORGECORE-MANAGED-END -->")
                    cleaned = (content[:start_idx] + content[end_idx:]).strip()
                    if cleaned:
                        self.global_rule_path.write_text(cleaned + "\n", encoding="utf-8")
                    else:
                        self.global_rule_path.unlink()
                    removed.append("Removed Core Contract from global GEMINI.md")

            # 3. Clean up backup files if present
            mcp_backup = self.mcp_config_path.with_suffix(".json.bak")
            if mcp_backup.is_file():
                mcp_backup.unlink()
                removed.append("Cleaned up mcp_config.json.bak")

            rule_backup = self.global_rule_path.with_suffix(".md.bak")
            if rule_backup.is_file():
                rule_backup.unlink()
                removed.append("Cleaned up GEMINI.md.bak")

            # 4. Remove manifest
            if self.manifest_path.is_file():
                self.manifest_path.unlink()
                removed.append("Removed install manifest")

            return InstallResult(
                success=True,
                message="Successfully uninstalled ForgeCore from Antigravity.\n" + "\n".join(f"- {r}" for r in removed),
                installed_files=removed,
            )
        except Exception as e:
            return InstallResult(success=False, message=f"Uninstall failed: {e}")

    def doctor(self) -> list[Check]:
        checks: list[Check] = []

        # 1. Python version
        py_ver = sys.version_info
        py_ok = (py_ver.major == 3 and py_ver.minor >= 11) or py_ver.major > 3
        checks.append(
            Check(
                name="Python Version",
                passed=py_ok,
                message=f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
                hint="Python 3.11+ is required." if not py_ok else None,
            )
        )

        # 2. Antigravity Global Directory
        agy_detected = self.detect()
        checks.append(
            Check(
                name="Antigravity Global Directory",
                passed=agy_detected,
                message=f"Path '{self.config_dir}' {'exists' if agy_detected else 'not found'}",
                hint="Run 'forgecore install antigravity' to initialize.",
            )
        )

        # 3. MCP Config
        mcp_configured = False
        if self.mcp_config_path.is_file():
            try:
                data = json.loads(self.mcp_config_path.read_text(encoding="utf-8"))
                mcp_configured = "forgecore" in data.get("mcpServers", {})
            except Exception:
                pass
        checks.append(
            Check(
                name="MCP Server Registration",
                passed=mcp_configured,
                message="forgecore server registered in mcp_config.json" if mcp_configured else "forgecore not registered",
                hint="Run 'forgecore install antigravity' to register the server.",
            )
        )

        # 4. Global Core Contract
        rule_installed = False
        if self.global_rule_path.is_file():
            rule_installed = "FORGECORE-MANAGED" in self.global_rule_path.read_text(encoding="utf-8")
        checks.append(
            Check(
                name="Global Core Contract Rule",
                passed=rule_installed,
                message="Core contract active in GEMINI.md" if rule_installed else "Core contract not installed",
                hint="Run 'forgecore install antigravity' to install.",
            )
        )

        # 5. Git
        git_bin = shutil.which("git")
        checks.append(
            Check(
                name="Git CLI",
                passed=git_bin is not None,
                message=f"Found git at {git_bin}" if git_bin else "Git not found in PATH",
                hint="Install Git for accurate changed-file diffing.",
            )
        )

        # 6. Ruff
        ruff_bin = shutil.which("ruff")
        checks.append(
            Check(
                name="Ruff Linter",
                passed=ruff_bin is not None,
                message=f"Found ruff at {ruff_bin}" if ruff_bin else "Ruff not found in PATH",
                hint="Install ruff (pip install ruff) for fast Python linting.",
            )
        )

        # 7. Semgrep
        semgrep_bin = shutil.which("semgrep")
        checks.append(
            Check(
                name="Semgrep",
                passed=semgrep_bin is not None,
                message=f"Found semgrep at {semgrep_bin}" if semgrep_bin else "Semgrep not found (optional)",
                hint="Install semgrep (pip install semgrep) for deep AST security/architecture rules.",
            )
        )

        return checks
