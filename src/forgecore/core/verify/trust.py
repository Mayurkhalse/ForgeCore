from __future__ import annotations

import hashlib
import json
import shlex
import sys
from pathlib import Path
from typing import Any

# Allowed executable names (normalized lowercase, without Windows extensions)
ALLOWED_EXECUTABLES: set[str] = {
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
    "./gradlew",
    ".\\gradlew",
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


def parse_and_validate_command(command_str: str) -> list[str]:
    """Parses a command string into an argv list using shlex, rejecting shell

    metacharacters and executables outside the allowlist.

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

    # Check for ./gradlew or .\\gradlew
    if normalized_exe in {"./gradlew", "gradlew"}:
        return argv

    exe_path = Path(raw_exe)
    exe_name = exe_path.name.lower()

    # Strip Windows executable extensions
    for ext in (".exe", ".cmd", ".bat"):
        if exe_name.endswith(ext):
            exe_name = exe_name[: -len(ext)]
            break

    # Special handling for python -m pytest
    if exe_name in {"python", "python3"}:
        if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "pytest":
            return argv
        raise DisallowedExecutableError(
            f"Python executable is only allowed with '-m pytest', got: '{command_str}'"
        )

    # Check against allowlist
    if exe_name in ALLOWED_EXECUTABLES:
        return argv

    allowed_list = sorted(list(ALLOWED_EXECUTABLES) + ["python -m pytest"])
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
                parse_and_validate_command(cmd_str)
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
