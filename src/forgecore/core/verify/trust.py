from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

# Allowed bare executable names (normalized lowercase, without Windows extensions)
ALLOWED_BARE_EXECUTABLES: set[str] = {
    "ruff",
    "semgrep",
    "pytest",
    "npm",
    "npx",
    "eslint",
    "tsc",
    "mvn",
    "gradle",
    "gradlew",
    "gradlew.bat",
}

# Dangerous shell metacharacters that enable command chaining, redirection, or expansion
SHELL_METACHARACTERS: set[str] = {
    ";",
    "&",
    "|",
    "<",
    ">",
    "$",
    "`",
    "\n",
    "\r",
    "(",
    ")",
}


class CommandTrustError(Exception):
    """Base exception for command security and trust validation."""


class ShellMetacharacterError(CommandTrustError):
    """Raised when shell metacharacters are detected in a command string."""


class DisallowedExecutableError(CommandTrustError):
    """Raised when an executable is not in the security allowlist."""


class UntrustedCommandError(CommandTrustError):
    """Raised when custom project commands have not been approved by the user."""


def _is_path_relative_to(child: Path, parent: Path) -> bool:
    """Checks whether child path is inside or identical to parent directory."""
    try:
        c_abs = child.absolute() if not child.is_absolute() else child
        p_abs = parent.absolute() if not parent.is_absolute() else parent
        if c_abs.is_relative_to(p_abs):
            return True
        if sys.platform == "win32":
            c_str = str(c_abs).lower()
            p_str = str(p_abs).lower()
            if c_str == p_str or c_str.startswith(p_str + "\\") or c_str.startswith(p_str + "/"):
                return True
        return False
    except Exception:
        return False


def _is_disallowed_project_executable(target: Path, root: Path) -> bool:
    """Checks whether target executable is located in an untrusted project directory.

    Binaries inside standard environment directories (.venv/Scripts, .venv/bin,
    and node_modules/.bin) are allowed, while bare executables in the project root
    (e.g. hijack pytest.bat, pytest.exe, pytest.cmd) or arbitrary repo subdirectories are rejected.
    """
    try:
        t_abs = target.absolute() if not target.is_absolute() else target
        r_abs = root.absolute() if not root.is_absolute() else root
        if not _is_path_relative_to(t_abs, r_abs):
            return False

        try:
            rel = t_abs.relative_to(r_abs)
        except ValueError:
            rel = Path(str(t_abs)[len(str(r_abs)) :].lstrip("\\/"))

        rel_parts = [p.lower() for p in rel.parts]
        if len(rel_parts) >= 2:
            if rel_parts[0] == ".venv" and rel_parts[1] in {"scripts", "bin"}:
                return False
            if rel_parts[0] == "node_modules" and rel_parts[1] == ".bin":
                return False

        return True
    except Exception:
        return False


def parse_and_validate_command(
    command_str: str,
    project_root: Path | str | None = None,
) -> list[str]:
    """Parses a command string into an argv list using shlex, rejecting shell

    metacharacters and executables outside the allowlist or untrusted in the project root.

    Allowed executables:
      - ruff
      - semgrep
      - pytest
      - python -m pytest (or python3 -m pytest)
      - npm
      - npx
      - eslint
      - tsc
      - mvn
      - gradle
      - ./gradlew (or gradlew / gradlew.bat)
    """
    if not command_str or not command_str.strip():
        raise CommandTrustError("Empty command string.")

    # 1. Reject any shell metacharacters
    for char in SHELL_METACHARACTERS:
        if char in command_str:
            raise ShellMetacharacterError(
                f"Command contains forbidden shell metacharacter '{char}': {command_str}"
            )

    # 2. Parse into argv
    try:
        argv = shlex.split(command_str)
    except ValueError as e:
        raise CommandTrustError(f"Failed to parse command with shlex: {e}") from e

    if not argv:
        raise CommandTrustError("Parsed command produced empty argv.")

    raw_exe = argv[0]
    normalized_exe = raw_exe.replace("\\", "/")

    # Check for ./gradlew or gradlew / gradlew.bat
    if normalized_exe in {"./gradlew", "gradlew", "gradlew.bat"}:
        return argv

    # Reject any relative or absolute paths (e.g. ./evil/pytest, ../pytest, bin/pytest, /usr/bin/pytest)
    if "/" in normalized_exe:
        raise DisallowedExecutableError(
            f"Path-based executable '{raw_exe}' is not permitted. "
            f"Only bare executable names from the allowlist or './gradlew' are allowed."
        )

    clean_exe = raw_exe.lower()
    for ext in (".exe", ".cmd", ".bat"):
        if clean_exe.endswith(ext):
            clean_exe = clean_exe[: -len(ext)]
            break

    search_path = None
    if project_root is not None:
        search_path = f"{Path(project_root).resolve()}{os.pathsep}{os.environ.get('PATH', '')}"

    # Special handling for python -m pytest
    if clean_exe in {"python", "python3"}:
        if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "pytest":
            resolved = (
                shutil.which(raw_exe, path=search_path)
                if search_path
                else shutil.which(raw_exe)
            ) or shutil.which(raw_exe)
            if resolved:
                unresolved_path = Path(resolved)
                resolved_path = unresolved_path.resolve()
                check_root = (
                    Path(project_root).resolve()
                    if project_root is not None
                    else Path.cwd().resolve()
                )
                if _is_disallowed_project_executable(unresolved_path, check_root) or _is_disallowed_project_executable(resolved_path, check_root):
                    raise DisallowedExecutableError(
                        f"Resolved executable '{resolved}' is located in an untrusted project directory ('{check_root}'). "
                        f"Executing bare repository-local binaries as trusted tools is forbidden."
                    )
                unresolved_base = unresolved_path.name.lower()
                for ext in (".exe", ".cmd", ".bat"):
                    if unresolved_base.endswith(ext):
                        unresolved_base = unresolved_base[: -len(ext)]
                        break
                if unresolved_base not in {"python", "python3"} and not (
                    unresolved_base.startswith("python3.") and unresolved_base[8:].isdigit()
                ):
                    raise DisallowedExecutableError(
                        f"Resolved executable '{resolved}' does not match python."
                    )
            return argv
        raise DisallowedExecutableError(
            f"Python executable is only allowed with '-m pytest', got: '{command_str}'"
        )

    # Check against allowlist
    if clean_exe in ALLOWED_BARE_EXECUTABLES:
        resolved = (
            shutil.which(raw_exe, path=search_path)
            if search_path
            else shutil.which(raw_exe)
        ) or shutil.which(raw_exe)
        if resolved:
            unresolved_path = Path(resolved)
            resolved_path = unresolved_path.resolve()
            check_root = (
                Path(project_root).resolve()
                if project_root is not None
                else Path.cwd().resolve()
            )
            if _is_disallowed_project_executable(unresolved_path, check_root) or _is_disallowed_project_executable(resolved_path, check_root):
                raise DisallowedExecutableError(
                    f"Resolved executable '{resolved}' is located in an untrusted project directory ('{check_root}'). "
                    f"Executing bare repository-local binaries as trusted tools is forbidden."
                )
            unresolved_base = unresolved_path.name.lower()
            for ext in (".exe", ".cmd", ".bat"):
                if unresolved_base.endswith(ext):
                    unresolved_base = unresolved_base[: -len(ext)]
                    break
            if unresolved_base != clean_exe and unresolved_base not in ALLOWED_BARE_EXECUTABLES:
                raise DisallowedExecutableError(
                    f"Resolved executable '{resolved}' is not on the allowlist."
                )
        return argv

    allowed_list = sorted(list(ALLOWED_BARE_EXECUTABLES) + ["python -m pytest", "./gradlew"])
    raise DisallowedExecutableError(
        f"Executable '{raw_exe}' is not on the ForgeCore allowlist: {allowed_list}"
    )


class CommandTrustManager:
    """Manages approval records for custom commands from .forgecore/project.yaml.

    Approvals are stored in the user's configuration directory (outside the
    project), keyed by normalized project root path and sha256 hash of the
    command set. Any changes to the command set invalidate approval.
    """

    def __init__(self, config_dir: Path | str | None = None) -> None:
        if config_dir is not None:
            self.config_dir = Path(config_dir).resolve()
        else:
            self.config_dir = Path.home() / ".forgecore"
        self.approvals_file = self.config_dir / "approvals.json"

    def _normalize_project_path(self, project_root: Path | str) -> str:
        resolved = Path(project_root).resolve()
        # Case-fold path on Windows to avoid case mismatch
        path_str = str(resolved)
        return path_str.lower() if sys.platform == "win32" else path_str

    @staticmethod
    def compute_commands_hash(commands: dict[str, str]) -> str:
        """Computes a deterministic SHA-256 hash over the sorted command dictionary."""
        canonical = json.dumps(
            {k: commands[k] for k in sorted(commands.keys())},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _read_approvals(self) -> dict[str, Any]:
        if not self.approvals_file.is_file():
            return {}
        try:
            with open(self.approvals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_approvals(self, data: dict[str, Any]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # Write atomically
        temp_file = self.approvals_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        temp_file.replace(self.approvals_file)

    def is_approved(self, project_root: Path | str, commands: dict[str, str]) -> bool:
        """Checks whether the exact command set for the project has been approved."""
        if not commands:
            return True

        project_key = self._normalize_project_path(project_root)
        approvals = self._read_approvals()

        stored = approvals.get(project_key)
        if not stored:
            return False

        expected_hash = self.compute_commands_hash(commands)

        # Stored can be a string hash or a dict with {"hash": ...}
        if isinstance(stored, dict):
            stored_hash = stored.get("hash")
        elif isinstance(stored, str):
            stored_hash = stored
        else:
            stored_hash = None

        return stored_hash == expected_hash

    def approve(self, project_root: Path | str, commands: dict[str, str]) -> str:
        """Validates all commands and records user approval in user config directory.

        Returns the computed approval hash.
        Raises CommandTrustError if any command fails allowlist or metacharacter checks.
        """
        if not commands:
            raise CommandTrustError("No commands to approve.")

        # Validate every command before approving
        for name, cmd_str in commands.items():
            try:
                parse_and_validate_command(cmd_str, project_root=project_root)
            except CommandTrustError as e:
                raise CommandTrustError(
                    f"Cannot approve command for '{name}': {e}"
                ) from e

        project_key = self._normalize_project_path(project_root)
        cmd_hash = self.compute_commands_hash(commands)

        approvals = self._read_approvals()
        approvals[project_key] = {
            "hash": cmd_hash,
            "commands": commands,
        }
        self._write_approvals(approvals)
        return cmd_hash

    def revoke(self, project_root: Path | str) -> bool:
        """Revokes approval for a project."""
        project_key = self._normalize_project_path(project_root)
        approvals = self._read_approvals()
        if project_key in approvals:
            del approvals[project_key]
            self._write_approvals(approvals)
            return True
        return False
