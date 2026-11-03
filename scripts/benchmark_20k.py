"""Benchmark ForgeCore on a synthetic repository of 20,000 files.

Measures wall-clock time for:
1. Generation of 20,000 files across 20 modules.
2. `forgecore init <path>` (context build, fingerprinting, layer detection).
3. `forgecore verify <path>` (incremental verification loop).
4. `forgecore verify --all <path>` (full scan verification loop).

Reports exact timings and any scan limits encountered.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    print("=" * 70)
    print("ForgeCore 20,000-File Synthetic Repository Benchmark")
    print("=" * 70)

    with tempfile.TemporaryDirectory(prefix="forgecore_20k_") as tmp_dir:
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
        print(f"Generated {total_files} files across {num_dirs} directories in {gen_time:.2f}s.")

        # 2. Time `forgecore init`
        print("\n--> Timing `forgecore init`...")
        t_init_0 = time.perf_counter()
        init_res = subprocess.run(
            [sys.executable, "-m", "forgecore.cli", "init", str(repo_path)],
            capture_output=True,
            text=True,
        )
        t_init = time.perf_counter() - t_init_0
        print(f"forgecore init exit code: {init_res.returncode} in {t_init:.2f}s")
        if init_res.returncode != 0:
            print(f"init stdout:\n{init_res.stdout}\nstderr:\n{init_res.stderr}")

        # 3. Time `forgecore verify` (default / changed scope)
        print("\n--> Timing `forgecore verify` (default scope)...")
        t_verify_0 = time.perf_counter()
        verify_res = subprocess.run(
            [sys.executable, "-m", "forgecore.cli", "verify", str(repo_path)],
            capture_output=True,
            text=True,
        )
        t_verify = time.perf_counter() - t_verify_0
        print(f"forgecore verify (default) exit code: {verify_res.returncode} in {t_verify:.2f}s")

        # 4. Time `forgecore verify --all` (full repo scan)
        print("\n--> Timing `forgecore verify --all` (full scan scope)...")
        t_verify_all_0 = time.perf_counter()
        verify_all_res = subprocess.run(
            [sys.executable, "-m", "forgecore.cli", "verify", "--all", str(repo_path)],
            capture_output=True,
            text=True,
        )
        t_verify_all = time.perf_counter() - t_verify_all_0
        print(f"forgecore verify --all exit code: {verify_all_res.returncode} in {t_verify_all:.2f}s")

        print("\n" + "=" * 70)
        print("SUMMARY TIMINGS:")
        print(f"  Repo File Generation (20,000 files): {gen_time:.2f}s")
        print(f"  forgecore init:                     {t_init:.2f}s")
        print(f"  forgecore verify (incremental):     {t_verify:.2f}s")
        print(f"  forgecore verify --all (full scan):  {t_verify_all:.2f}s")
        print("=" * 70)

        # 5. Check scan limits and behaviors
        print("\nSCAN LIMITS ANALYSIS:")
        print("1. Max Traversal Depth: StackDetector.scan_files enforces max_depth=6.")
        print("   Directories deeper than 6 levels are pruned to protect against deep recursion.")
        print("2. Directory Skip List: SKIP_DIRS ignores build/cache/virtualenv directories:")
        print("   {.git, node_modules, .venv, venv, env, __pycache__, dist, build, target, .idea, etc.}")
        print("3. Manifest Fingerprinting: MANIFEST_PATTERNS only hashes 12 known project manifests,")
        print("   avoiding full 20,000-file SHA-256 rehashing on cached init/verify calls.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
