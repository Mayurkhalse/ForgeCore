from pathlib import Path

import pytest

from sarthi.core.pathguard import (
    FileTooLargeError,
    GitDirectoryAccessError,
    PathGuard,
    PathTraversalError,
    SecretFileAccessError,
)


def test_pathguard_safe_resolution(tmp_path: Path):
    sub = tmp_path / "src"
    sub.mkdir()
    target_file = sub / "app.py"
    target_file.write_text("print('safe')", encoding="utf-8")

    guard = PathGuard(tmp_path)
    safe = guard.safe_path("src/app.py")
    assert safe == target_file
    assert guard.read_text("src/app.py") == "print('safe')"


def test_pathguard_prevents_directory_traversal(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret outside", encoding="utf-8")

    guard = PathGuard(root)
    with pytest.raises(PathTraversalError):
        guard.safe_path("../outside.txt")


def test_pathguard_blocks_secret_files(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=123", encoding="utf-8")

    guard = PathGuard(tmp_path)
    assert guard.is_secret_file(".env") is True
    assert guard.is_secret_file("id_rsa") is True
    assert guard.is_secret_file("server.key") is True
    assert guard.is_secret_file("main.py") is False

    with pytest.raises(SecretFileAccessError):
        guard.safe_path(".env")


def test_pathguard_file_size_limit(tmp_path: Path):
    big_file = tmp_path / "big.txt"
    big_file.write_bytes(b"A" * 200)

    guard = PathGuard(tmp_path, max_read_bytes=100)
    with pytest.raises(FileTooLargeError):
        guard.read_text("big.txt")


def test_pathguard_blocks_git_directory(tmp_path: Path):
    """Verifies that PathGuard strictly blocks all direct, nested, and case-variant .git accesses."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")
    hooks = git_dir / "hooks"
    hooks.mkdir()
    (hooks / "pre-commit").write_text("#!/bin/sh\n", encoding="utf-8")

    sub_repo = tmp_path / "sub" / ".git"
    sub_repo.mkdir(parents=True)
    (sub_repo / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    guard = PathGuard(tmp_path)

    # 1. Direct .git paths
    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path(".git")

    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path(".git/config")

    with pytest.raises(GitDirectoryAccessError):
        guard.read_text(".git/config")

    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path(".git/hooks/pre-commit")

    # 2. Case variations (especially critical on Windows)
    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path(".GIT/config")

    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path(".Git/hooks/pre-commit")

    # 3. Subdirectory nested .git
    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path("sub/.git/HEAD")

    # 4. Traversal resolution landing on .git
    with pytest.raises(GitDirectoryAccessError):
        guard.safe_path("sub/../.git/config")

    # 5. Traversal escaping root targeting .git
    with pytest.raises(PathTraversalError):
        guard.safe_path("../../.git")

