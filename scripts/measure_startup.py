from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time


def measure_one_run(cmd: list[str]) -> float:
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    start = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        init_req = (
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "benchmark", "version": "1.0"},
                },
            })
            + "\n"
        )
        assert proc.stdin is not None
        proc.stdin.write(init_req)
        proc.stdin.flush()

        assert proc.stdout is not None
        line = proc.stdout.readline()
        elapsed = time.perf_counter() - start
        data = json.loads(line)
        assert data.get("id") == 1
        return elapsed
    finally:
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            proc.kill()


def main() -> None:
    # Measure 'forgecore serve' via CLI entrypoint
    cmd = [sys.executable, "-u", "-m", "forgecore.cli", "serve"]
    runs = 10
    times: list[float] = []

    print(f"Measuring cold startup time for: {' '.join(cmd)}", flush=True)
    for i in range(1, runs + 1):
        elapsed = measure_one_run(cmd)
        times.append(elapsed)
        print(f"  Run {i:2d}: {elapsed * 1000:6.1f} ms ({elapsed:.3f} s)", flush=True)

    mean_t = statistics.mean(times)
    stdev_t = statistics.stdev(times) if len(times) > 1 else 0.0
    min_t = min(times)
    max_t = max(times)

    print("\n--- Summary ---")
    print(f"Mean:   {mean_t * 1000:6.1f} ms ({mean_t:.3f} s)")
    print(f"StdDev: {stdev_t * 1000:6.1f} ms")
    print(f"Min:    {min_t * 1000:6.1f} ms")
    print(f"Max:    {max_t * 1000:6.1f} ms")


if __name__ == "__main__":
    main()
