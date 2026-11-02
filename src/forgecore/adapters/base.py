from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class InstallOpts:
    workspace_root: Path | None = None
    force: bool = False
    with_scaffold: bool = True


@dataclass
class InstallResult:
    success: bool
    message: str
    installed_files: list[str] = field(default_factory=list)


@dataclass
class Check:
    name: str
    passed: bool
    message: str
    hint: str | None = None


@runtime_checkable
class ClientAdapter(Protocol):
    """Protocol for AI coding client adapters (Antigravity, Cursor, etc.)."""

    @property
    def name(self) -> str:
        """Client name identifier."""
        ...

    def detect(self) -> bool:
        """Determines if the client is installed / available on this system."""
        ...

    def install(self, opts: InstallOpts) -> InstallResult:
        """Installs MCP config, global rules, and optional hooks for the client."""
        ...

    def uninstall(self) -> InstallResult:
        """Removes all installed configurations tracked in the manifest."""
        ...

    def doctor(self) -> list[Check]:
        """Runs diagnostics on the environment and client configuration."""
        ...
