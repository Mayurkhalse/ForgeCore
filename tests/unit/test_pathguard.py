from pathlib import Path

import pytest

from forgecore.core.pathguard import (
    FileTooLargeError,
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
