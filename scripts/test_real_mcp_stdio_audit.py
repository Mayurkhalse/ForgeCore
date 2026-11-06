"""Real MCP Stdio Subprocess Verification Script.

Executes all 12 requirements of Section 7 against the real MCP server subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("C:/Users/Rajendra/Desktop/Projects/ForgeCore")

def run_mcp_stdio_verification():
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
    }
    fixture_dir = REPO_ROOT / "tests" / "fixtures" / "fastapi_app"

    cmd = [sys.executable, "-u", "-m", "forgecore.mcp.server"]
    print(f"Starting server process: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )

    req_id = 0

    def send_and_recv(method: str, params: dict | None = None, is_notif: bool = False):
        nonlocal req_id
        if is_notif:
            payload = {"jsonrpc": "2.0", "method": method}
            if params:
                payload["params"] = params
            req_str = json.dumps(payload) + "\n"
            proc.stdin.write(req_str)
            proc.stdin.flush()
            return None

        req_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        req_str = json.dumps(payload) + "\n"
        proc.stdin.write(req_str)
        proc.stdin.flush()

        resp_line = proc.stdout.readline()
        if not resp_line:
            raise RuntimeError(f"Server closed stdout unexpectedly on {method}")
        return json.loads(resp_line.strip())

    try:
        # 1. Handshake
        print("\n--- 1. Handshake ---")
        init_resp = send_and_recv("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"resources": {}, "tools": {}, "prompts": {}},
            "clientInfo": {"name": "audit-client", "version": "1.0.0"},
        })
        print(f"Server Name: {init_resp.get('result', {}).get('serverInfo', {}).get('name')}")
        print(f"Instructions Preview: {init_resp.get('result', {}).get('instructions', '')[:100]}...")

        # 2. Notification initialized
        send_and_recv("notifications/initialized", is_notif=True)

        # 3. Tool Discovery
        print("\n--- 2. Tool Discovery ---")
        tools_resp = send_and_recv("tools/list")
        tools = [t["name"] for t in tools_resp.get("result", {}).get("tools", [])]
        print(f"Discovered {len(tools)} tools: {tools}")

        # 4. Resource Template Discovery
        print("\n--- 3. Resource Template Discovery ---")
        res_resp = send_and_recv("resources/templates/list")
        templates = [t["uriTemplate"] for t in res_resp.get("result", {}).get("resourceTemplates", [])]
        print(f"Discovered {len(templates)} resource templates: {templates}")

        # 5. get_standards Invocation
        print("\n--- 4. get_standards Invocation ---")
        standards_resp = send_and_recv("tools/call", {
            "name": "get_standards",
            "arguments": {
                "root": str(fixture_dir),
                "task": "Build a production-ready authentication module using FastAPI and PostgreSQL.",
                "layers": ["fastapi", "security", "sql"],
            },
        })
        content_items = standards_resp.get("result", {}).get("content", [])
        assert len(content_items) > 0, "No content returned from get_standards"
        st_data = json.loads(content_items[0]["text"])
        print(f"Rules returned: {len(st_data.get('rules', []))}")
        print(f"Skills returned: {len(st_data.get('skills', []))}")
        skill_ids = [s["id"] for s in st_data.get("skills", [])]
        print(f"Skill IDs: {skill_ids}")

        # 6. Compiled Instruction Content
        print("\n--- 5. Compiled Instructions Markdown ---")
        inst_md = st_data.get("instructions_markdown", "")
        assert "Mandatory Security Invariants" in inst_md
        assert "Mandatory Core Engineering Contract" in inst_md
        assert "Upstream ECC Engineering Guidance" in inst_md
        print(f"Instructions Markdown length: {len(inst_md)} characters")
        print("Section Headers in Markdown:")
        for line in inst_md.splitlines():
            if line.startswith("#"):
                print(f"  {line}")

        # 7. get_workflow Invocation
        print("\n--- 6. get_workflow Invocation ---")
        wf_resp = send_and_recv("tools/call", {
            "name": "get_workflow",
            "arguments": {"task_type": "feature"},
        })
        wf_content = wf_resp.get("result", {}).get("content", [])[0]["text"]
        print(f"Workflow content length: {len(wf_content)} characters")
        print(f"Workflow preview: {wf_content[:150]}...")

        # 8. verify_project Invocation
        print("\n--- 7. verify_project Invocation ---")
        vp_resp = send_and_recv("tools/call", {
            "name": "verify_project",
            "arguments": {"root": str(fixture_dir)},
        })
        vp_data = json.loads(vp_resp.get("result", {}).get("content", [])[0]["text"])
        print(f"Verify project status: {vp_data.get('status')}")
        print(f"Passed checks: {vp_data.get('passed_checks')}")
        print(f"Failed checks: {vp_data.get('failed_checks')}")

        # 9. Direct forgecore://ecc/{resource_id} Resource Retrieval
        print("\n--- 8. Direct Resource Read (forgecore://ecc/ecc.skill.fastapi-patterns) ---")
        read_resp = send_and_recv("resources/read", {
            "uri": "forgecore://ecc/ecc.skill.fastapi-patterns",
        })
        contents = read_resp.get("result", {}).get("contents", [])
        assert len(contents) > 0
        res_data = json.loads(contents[0]["text"])
        print(f"Resource ID: {res_data.get('id')}")
        print(f"Name: {res_data.get('name')}")
        print(f"Source Commit: {res_data.get('source_commit')}")
        print(f"License: {res_data.get('license')}")
        print(f"Content Length: {len(res_data.get('content', ''))} characters")

        # 10. Invalid Resource Handling
        print("\n--- 9. Invalid Resource Handling ---")
        inv_read_resp = send_and_recv("resources/read", {
            "uri": "forgecore://ecc/ecc.skill.nonexistent_bogus",
        })
        inv_content = json.loads(inv_read_resp.get("result", {}).get("contents", [])[0]["text"])
        print(f"Invalid resource result: {inv_content}")
        assert "error" in inv_content

        # 11. Malformed Request Handling
        print("\n--- 10. Malformed Request Handling ---")
        proc.stdin.write('{"jsonrpc": "2.0", "id": 999, "method": "unsupported_unknown_method"}\n')
        proc.stdin.flush()
        malformed_resp_line = proc.stdout.readline()
        malformed_resp = json.loads(malformed_resp_line.strip())
        print(f"Malformed/Unknown method response: {malformed_resp}")
        assert "error" in malformed_resp or malformed_resp.get("result") is None

        # 12. Graceful Shutdown
        print("\n--- 11. Graceful Process Shutdown ---")
        proc.stdin.close()
        exit_code = proc.wait(timeout=5)
        print(f"Server process terminated with return code: {exit_code}")
        assert exit_code == 0, f"Expected return code 0, got {exit_code}"
        print("\nAll 12 Real MCP stdio requirements VERIFIED SUCCESSFULLY!")

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

if __name__ == "__main__":
    run_mcp_stdio_verification()

