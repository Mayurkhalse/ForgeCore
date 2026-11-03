"""Clean clone and install verification script.

In a temporary directory:
1. Copies the repository source tree (excluding .venv, .git, and cache directories).
2. Creates an isolated virtual environment with `sys.executable -m venv`.
3. Installs ForgeCore in editable mode via pip.
4. Runs `forgecore doctor` and asserts exit code 0.
5. Runs `forgecore init` on a clean copy of the FastAPI fixture and asserts exit code 0.
6. Asserts that .forgecore/project.yaml and .forgecore/cache/context.md were generated.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print(f"--> Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"STDOUT:\n{res.stdout}")
        print(f"STDERR:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Command failed with exit code {res.returncode}: {' '.join(cmd)}")
    return res


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    print(f"[clean_install_check] Source repo: {repo_root}")

    with tempfile.TemporaryDirectory(prefix="forgecore_clean_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        clean_repo = tmp_path / "repo"
        clean_venv = tmp_path / "venv"
        clean_fixture = tmp_path / "fastapi_app"

        # 1. Copy repository tree
        print(f"[clean_install_check] Copying repo to {clean_repo}...")
        ignore_patterns = shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "*.egg-info",
            "dist",
            "build",
            ".forgecore",
        )
        shutil.copytree(repo_root, clean_repo, ignore=ignore_patterns)

        # Copy fixture to a separate clean directory
        src_fixture = repo_root / "tests" / "fixtures" / "fastapi_app"
        shutil.copytree(src_fixture, clean_fixture, ignore=ignore_patterns)

        # 2. Create virtual environment
        print(f"[clean_install_check] Creating virtual environment at {clean_venv}...")
        run_cmd([sys.executable, "-m", "venv", str(clean_venv)])

        # Locate binaries
        if sys.platform == "win32":
            venv_python = clean_venv / "Scripts" / "python.exe"
            venv_forgecore = clean_venv / "Scripts" / "forgecore.exe"
        else:
            venv_python = clean_venv / "bin" / "python"
            venv_forgecore = clean_venv / "bin" / "forgecore"

        assert venv_python.exists(), f"Virtualenv Python not found at {venv_python}"

        # 3. Install repo into virtualenv
        print("[clean_install_check] Installing ForgeCore into clean venv...")
        run_cmd([str(venv_python), "-m", "pip", "install", "-e", str(clean_repo)])

        assert venv_forgecore.exists(), f"forgecore console script not found at {venv_forgecore}"

        # 4. Run forgecore doctor
        print("[clean_install_check] Running forgecore doctor...")
        doc_res = run_cmd([str(venv_forgecore), "doctor"])
        print(f"[clean_install_check] forgecore doctor output:\n{doc_res.stdout.strip()}")

        # 5. Run forgecore init on clean fixture
        print("[clean_install_check] Running forgecore init on fixture...")
        init_res = run_cmd([str(venv_forgecore), "init", str(clean_fixture)])
        print(f"[clean_install_check] forgecore init output:\n{init_res.stdout.strip()}")

        # 6. Verify generated files
        project_yaml = clean_fixture / ".forgecore" / "project.yaml"
        context_md = clean_fixture / ".forgecore" / "cache" / "context.md"

        assert project_yaml.is_file(), f"Expected project.yaml at {project_yaml}"
        assert context_md.is_file(), f"Expected context.md at {context_md}"
        print(f"[clean_install_check] Verified .forgecore/project.yaml ({project_yaml.stat().st_size} bytes)")
        print(f"[clean_install_check] Verified .forgecore/cache/context.md ({context_md.stat().st_size} bytes)")

    print("[clean_install_check] SUCCESS: All clean install and execution checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
