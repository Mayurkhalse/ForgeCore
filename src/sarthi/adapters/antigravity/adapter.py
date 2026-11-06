from __future__ import annotations

import datetime
import json
import shutil
import sys
from pathlib import Path

from sarthi.adapters.base import Check, ClientAdapter, InstallOpts, InstallResult
from sarthi.core.config import ConfigLoader
from sarthi.mcp.tools import MCPToolHandlers

MANIFEST_FILE_NAME = "sarthi-manifest.json"


def _create_timestamped_backup(file_path: Path) -> Path:
    """Creates a unique timestamped backup copy that is never overwritten."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidate = file_path.with_name(f"{file_path.name}.{now_str}.bak")
    counter = 1
    while candidate.exists():
        candidate = file_path.with_name(f"{file_path.name}.{now_str}_{counter}.bak")
        counter += 1
    shutil.copy2(file_path, candidate)
    return candidate


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
            # 1. Validate existing mcp_config.json if present
            mcp_data = {"mcpServers": {}}
            if self.mcp_config_path.is_file():
                raw_mcp = self.mcp_config_path.read_text(encoding="utf-8")
                try:
                    loaded = json.loads(raw_mcp)
                    if not isinstance(loaded, dict):
                        return InstallResult(
                            success=False,
                            message=f"Existing MCP config file '{self.mcp_config_path}' must contain a valid JSON object.",
                        )
                    mcp_data = loaded
                except Exception as e:
                    return InstallResult(
                        success=False,
                        message=f"Existing MCP config file '{self.mcp_config_path}' contains invalid JSON: {e}. Refusing to proceed.",
                    )
                if "mcpServers" not in mcp_data:
                    mcp_data["mcpServers"] = {}

            # 2. Check for dry-run (after validating config)
            if opts.dry_run:
                preview_files = [str(self.mcp_config_path), str(self.global_rule_path)]
                if opts.workspace_root and opts.with_scaffold:
                    preview_files.append(str(opts.workspace_root / ".sarthi" / "project.yaml"))
                return InstallResult(
                    success=True,
                    message="[Dry Run] Validated configuration. No files written to disk.",
                    installed_files=preview_files,
                )

            self.config_dir.mkdir(parents=True, exist_ok=True)
            installed_files: list[str] = []

            # 3. Resolve Python executable path
            python_path = sys.executable

            # 4. Create timestamped backup and update mcp_config.json
            mcp_backup_path: Path | None = None
            if self.mcp_config_path.is_file():
                mcp_backup_path = _create_timestamped_backup(self.mcp_config_path)

            mcp_data["mcpServers"]["sarthi"] = {
                "command": str(python_path),
                "args": ["-m", "sarthi.cli", "serve"],
                "env": {},
            }
            self.mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
            installed_files.append(str(self.mcp_config_path))

            # 3. Write Global Rule File (GEMINI.md)
            contract_path = Path(__file__).resolve().parent.parent.parent.parent / "standards" / "contract.md"
            if contract_path.is_file():
                contract_content = contract_path.read_text(encoding="utf-8")
            else:
                contract_content = "# SARTHI CORE CONTRACT\nFollow standards and run verify_project before done."

            rule_wrapper = (
                "<!-- SARTHI-MANAGED-START -->\n"
                f"{contract_content}\n"
                "<!-- SARTHI-MANAGED-END -->\n"
            )

            # If GEMINI.md already exists, backup with unique timestamp and append or replace the managed block
            rule_backup_path: Path | None = None
            if self.global_rule_path.is_file():
                rule_backup_path = _create_timestamped_backup(self.global_rule_path)
                existing = self.global_rule_path.read_text(encoding="utf-8")
                if "<!-- SARTHI-MANAGED-START -->" in existing:
                    start_idx = existing.find("<!-- SARTHI-MANAGED-START -->")
                    end_idx = existing.find("<!-- SARTHI-MANAGED-END -->") + len("<!-- SARTHI-MANAGED-END -->")
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
                "installed_by": "sarthi install antigravity",
                "python_path": str(python_path),
                "installed_files": installed_files,
                "added_mcp_server": "sarthi",
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
                message="Successfully installed Sarthi for Antigravity! MCP server configured, global rule installed, and self-test passed.",
                installed_files=installed_files,
            )

        except Exception as e:
            return InstallResult(success=False, message=f"Failed to install for Antigravity: {e}")

    def uninstall(self) -> InstallResult:
        """Reverts all changes tracked in the install manifest."""
        try:
            removed: list[str] = []

            manifest_data: dict = {}
            if self.manifest_path.is_file():
                try:
                    manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            backups = manifest_data.get("backups", {}) if isinstance(manifest_data, dict) else {}
            mcp_backup = backups.get("mcp_config")
            rule_backup = backups.get("global_rule")

            # 1. Clean or restore MCP config
            if mcp_backup and Path(mcp_backup).is_file():
                shutil.copy2(mcp_backup, self.mcp_config_path)
                removed.append("Restored original mcp_config.json from backup")
            elif self.mcp_config_path.is_file():
                if "backups" in manifest_data and mcp_backup is None:
                    self.mcp_config_path.unlink()
                    removed.append("Removed created mcp_config.json")
                else:
                    try:
                        mcp_data = json.loads(self.mcp_config_path.read_text(encoding="utf-8"))
                        if "mcpServers" in mcp_data and "sarthi" in mcp_data["mcpServers"]:
                            del mcp_data["mcpServers"]["sarthi"]
                            self.mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
                            removed.append("Removed 'sarthi' entry from mcp_config.json")
                    except Exception:
                        pass

            # 2. Clean or restore global rule file
            if rule_backup and Path(rule_backup).is_file():
                shutil.copy2(rule_backup, self.global_rule_path)
                removed.append("Restored original GEMINI.md from backup")
            elif self.global_rule_path.is_file():
                if "backups" in manifest_data and rule_backup is None:
                    self.global_rule_path.unlink()
                    removed.append("Removed created global GEMINI.md")
                else:
                    content = self.global_rule_path.read_text(encoding="utf-8")
                    if "<!-- SARTHI-MANAGED-START -->" in content:
                        start_idx = content.find("<!-- SARTHI-MANAGED-START -->")
                        end_idx = content.find("<!-- SARTHI-MANAGED-END -->") + len("<!-- SARTHI-MANAGED-END -->")
                        cleaned = (content[:start_idx] + content[end_idx:]).strip()
                        if cleaned:
                            self.global_rule_path.write_text(cleaned + "\n", encoding="utf-8")
                        else:
                            self.global_rule_path.unlink()
                        removed.append("Removed Core Contract from global GEMINI.md")

            # 3. Remove manifest (timestamped backups are preserved for safety)
            if self.manifest_path.is_file():
                self.manifest_path.unlink()
                removed.append("Removed install manifest")

            return InstallResult(
                success=True,
                message="Successfully uninstalled Sarthi from Antigravity.\n" + "\n".join(f"- {r}" for r in removed),
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
                hint="Run 'sarthi install antigravity' to initialize.",
            )
        )

        # 3. MCP Config
        mcp_configured = False
        if self.mcp_config_path.is_file():
            try:
                data = json.loads(self.mcp_config_path.read_text(encoding="utf-8"))
                mcp_configured = "sarthi" in data.get("mcpServers", {})
            except Exception:
                pass
        checks.append(
            Check(
                name="MCP Server Registration",
                passed=mcp_configured,
                message="sarthi server registered in mcp_config.json" if mcp_configured else "sarthi not registered",
                hint="Run 'sarthi install antigravity' to register the server.",
            )
        )

        # 4. Global Core Contract
        rule_installed = False
        if self.global_rule_path.is_file():
            rule_installed = "SARTHI-MANAGED" in self.global_rule_path.read_text(encoding="utf-8")
        checks.append(
            Check(
                name="Global Core Contract Rule",
                passed=rule_installed,
                message="Core contract active in GEMINI.md" if rule_installed else "Core contract not installed",
                hint="Run 'sarthi install antigravity' to install.",
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
