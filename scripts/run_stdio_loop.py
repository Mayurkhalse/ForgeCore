from __future__ import annotations

import subprocess
import sys


def main() -> None:
    passes = 0
    failures = 0
    total = 20

    print(f"Starting stdio transport test loop ({total} iterations)...", flush=True)
    for i in range(1, total + 1):
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/integration/test_stdio_transport.py"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            passes += 1
            print(f"  Iteration {i:2d}/{total}: PASS", flush=True)
        else:
            failures += 1
            print(f"  Iteration {i:2d}/{total}: FAIL (exit code {res.returncode})", flush=True)
            print(res.stderr or res.stdout, flush=True)

    print("\n--- Stdio Loop Result ---", flush=True)
    print(f"Total Iterations: {total}", flush=True)
    print(f"Passed: {passes}", flush=True)
    print(f"Failed: {failures}", flush=True)


if __name__ == "__main__":
    main()
