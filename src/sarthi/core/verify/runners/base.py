from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from sarthi.core.models import Finding, RunContext


@runtime_checkable
class Runner(Protocol):
    """Protocol for verification check runners."""

    @property
    def name(self) -> str:
        """Identifier for the runner (e.g. 'ruff', 'secrets', 'semgrep')."""
        ...

    @property
    def required(self) -> bool:
        """Whether the runner is required (True) or optional (False) for verification completion."""
        ...

    def available(self, ctx: RunContext) -> bool:
        """Determines if the runner is available and can execute in the given context."""
        ...

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        """Executes the runner against the target files and returns normalized findings."""
        ...
