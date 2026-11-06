"""Benchmark Sarthi on a synthetic repository of 20,000 files.

Measures wall-clock time for:
1. Generation of 20,000 files across 20 modules.
2. `sarthi init <path>` (context build, fingerprinting, layer detection).
3. `sarthi verify <path>` without git (capped at 500 files, newest first).
4. `sarthi verify <path>` with git (incremental git diff + untracked detection).
5. `sarthi verify <path> --all` (full scan of all 20,000 files with wall-clock budget).

Reports all 4 timings and scan limit behaviors.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, float, str, str]:
    t0 = time.perf_counter()
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return res.returncode, dt, res.stdout, res.stderr


def main() -> int:
    print("=" * 75)
    print("Sarthi 20,000-File Synthetic Repository Benchmark")
    print("=" * 75)

    with tempfile.TemporaryDirectory(prefix="sarthi_20k_") as tmp_dir:
        repo_path = Path(tmp_dir).resolve()
        print(f"Synthetic repo root: {repo_path}")

        # 1. Generate 20,000 files
        t0 = time.perf_counter()
        pyproject = repo_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "synthetic-20k"\nversion = "0.1.0"\ndependencies = ["fastapi>=0.110.0"]\n',
            encoding="utf-8",
        )

        num_dirs = 20
        files_per_dir = 1000
        total_files = 0

        for d in range(num_dirs):
            dir_path = repo_path / f"module_{d:02d}"
            dir_path.mkdir(exist_ok=True)
            for f in range(files_per_dir):
                file_path = dir_path / f"service_{f:03d}.py"
                file_path.write_text(f"# synthetic file {d}_{f}\nx = {f}\n", encoding="utf-8")
                total_files += 1

        gen_time = time.perf_counter() - t0
        print(f"Generated {total_files} files across {num_dirs} directories in {gen_time:.2f}s.\n")

        # 2. Timing `sarthi init`
        print("--> 1/4 Timing `sarthi init`...")
        code_init, t_init, out_init, err_init = run_cmd(
            [sys.executable, "-m", "sarthi.cli", "init", str(repo_path)]
        )
        print(f"    sarthi init: exit code {code_init} in {t_init:.2f}s")

        # 3. Timing `sarthi verify` (no git) - incremental scope with non-git 500-file cap
        print("\n--> 2/4 Timing `sarthi verify` (no git)...")
        code_no_git, t_no_git, out_no_git, err_no_git = run_cmd(
            [sys.executable, "-m", "sarthi.cli", "verify", str(repo_path)]
        )
        print(f"    sarthi verify (no git): exit code {code_no_git} in {t_no_git:.2f}s")
        if "capped at 500" in out_no_git:
            print("    [Confirmed: non-git scan cap applied to 500 newest files]")

        # 4. Timing `sarthi verify` (with git) - initialize git repo and run incremental check
        print("\n--> 3/4 Setting up git repo and timing `sarthi verify` (git)...")
        run_cmd(["git", "init"], cwd=repo_path)
        run_cmd(["git", "config", "user.name", "Benchmark"], cwd=repo_path)
        run_cmd(["git", "config", "user.email", "bench@example.com"], cwd=repo_path)
        # Add and commit base files
        run_cmd(["git", "add", "pyproject.toml", ".sarthi/"], cwd=repo_path)
        run_cmd(["git", "commit", "-m", "Initial commit"], cwd=repo_path)
        # Touch 2 files to simulate real developer changes
        (repo_path / "module_00" / "service_000.py").write_text("# modified\nx = 999\n", encoding="utf-8")
        (repo_path / "module_00" / "service_new.py").write_text("# new file\nx = 1\n", encoding="utf-8")

        code_git, t_git, out_git, err_git = run_cmd(
            [sys.executable, "-m", "sarthi.cli", "verify", str(repo_path)]
        )
        print(f"    sarthi verify (git): exit code {code_git} in {t_git:.2f}s")

        # 5. Timing `sarthi verify --all` (full scan scope with 60s wall-clock timeout)
        print("\n--> 4/4 Timing `sarthi verify --all` (full scan scope)...")
        code_all, t_all, out_all, err_all = run_cmd(
            [sys.executable, "-m", "sarthi.cli", "verify", str(repo_path), "--all"]
        )
        print(f"    sarthi verify --all: exit code {code_all} in {t_all:.2f}s")

        print("\n" + "=" * 75)
        print("SUMMARY BENCHMARK RESULTS (20,000 files):")
        print(f"  Repo File Generation (20,000 files): {gen_time:.2f}s")
        print(f"  1. sarthi init:                   {t_init:.2f}s")
        print(f"  2. sarthi verify (no git, cap 500):{t_no_git:.2f}s")
        print(f"  3. sarthi verify (git, 2 files):  {t_git:.2f}s")
        print(f"  4. sarthi verify --all (20k scan):{t_all:.2f}s")
        print("=" * 75)

    return 0


if __name__ == "__main__":
    sys.exit(main())
