from __future__ import annotations

import fnmatch
from pathlib import Path


class PathGuardError(Exception):
    """Base exception for PathGuard errors."""
    pass


class PathTraversalError(PathGuardError):
    """Raised when an access attempts to escape the project root."""
    pass


class SecretFileAccessError(PathGuardError):
    """Raised when an access targets a known secret or sensitive credential file."""
    pass


class GitDirectoryAccessError(PathGuardError):
    """Raised when an access targets a .git directory or files within it."""
    pass


class FileTooLargeError(PathGuardError):
    """Raised when reading a file that exceeds the size limit."""
    pass


DEFAULT_SECRET_PATTERNS = [
    ".git",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.pkcs12",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_rsa.*",
    "id_dsa",
    "id_dsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "id_ecdsa",
    "id_ecdsa.*",
    "*.keystore",
    "*.jks",
    "credentials.json",
    "service-account*.json",
    "*_rsa",
]


class PathGuard:
    """Enforces sandbox path safety, preventing traversal escapes and secret exfiltration."""

    def __init__(
        self,
        root: Path | str,
        secret_patterns: list[str] | None = None,
        max_read_bytes: int = 5 * 1024 * 1024,  # 5MB default cap
    ) -> None:
        self.root = Path(root).resolve()
        self.secret_patterns = secret_patterns or DEFAULT_SECRET_PATTERNS
        self.max_read_bytes = max_read_bytes

    def is_secret_file(self, path: Path | str) -> bool:
        """Check if filename matches any known sensitive credential patterns."""
        p = Path(path)
        name = p.name.lower()
        for pattern in self.secret_patterns:
            if fnmatch.fnmatch(name, pattern.lower()):
                return True
        return False

    def safe_path(self, target: Path | str, allow_secret: bool = False, allow_git: bool = False) -> Path:
        """
        Resolves the target path and verifies it strictly resides within project root.
        Denies path escapes, symlinks leaving root, internal VCS (.git) access, and sensitive secret files.
        """
        p = Path(target)
        if not p.is_absolute():
            p = (self.root / p).resolve()
        else:
            p = p.resolve()

        # Check containment within root
        try:
            rel = p.relative_to(self.root)
        except ValueError:
            raise PathTraversalError(f"Access denied: '{target}' resolves outside project root '{self.root}'")

        # Block internal VCS (.git) directory and any components within it
        if not allow_git and any(part.lower() == ".git" for part in rel.parts):
            raise GitDirectoryAccessError(f"Access denied: '.git' directory access is forbidden: '{target}'")

        if not allow_secret and self.is_secret_file(p):
            raise SecretFileAccessError(f"Access denied: '{p.name}' is flagged as a sensitive secret file")

        return p

    def read_text(self, target: Path | str, allow_secret: bool = False, encoding: str = "utf-8") -> str:
        """Safely read text file with path validation and size cap."""
        path = self.safe_path(target, allow_secret=allow_secret)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        file_size = path.stat().st_size
        if file_size > self.max_read_bytes:
            raise FileTooLargeError(
                f"File '{path.name}' size ({file_size} bytes) exceeds limit ({self.max_read_bytes} bytes)"
            )

        return path.read_text(encoding=encoding, errors="replace")

    def safe_relative(self, target: Path | str) -> str:
        """Returns relative path string normalized with forward slashes."""
        path = self.safe_path(target, allow_secret=True)
        return str(path.relative_to(self.root)).replace("\\", "/")
