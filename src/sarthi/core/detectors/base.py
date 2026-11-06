from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from sarthi.core.models import DetectedLayer

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
}


class BaseDetector(ABC):
    """Abstract base class for layer detectors."""

    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Name of the layer detected (e.g., 'react', 'fastapi')."""
        pass

    @abstractmethod
    def detect(self, root: Path) -> DetectedLayer | None:
        """Inspect project files and return DetectedLayer with confidence and evidence, or None."""
        pass

    def scan_files(self, root: Path, max_depth: int = 6) -> list[Path]:
        """Yield files in root up to max_depth (default 6 for deep monorepos and Java layouts),

        ignoring common build and package directories.
        """
        found: list[Path] = []
        try:
            for item in root.iterdir():
                if item.name in SKIP_DIRS or item.name.startswith("."):
                    continue
                if item.is_file():
                    found.append(item)
                elif item.is_dir() and max_depth > 1:
                    found.extend(self.scan_files(item, max_depth - 1))
        except (PermissionError, FileNotFoundError):
            pass
        return found
