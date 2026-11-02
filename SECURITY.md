# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in ForgeCore:

1. **Do not** disclose the issue publicly in GitHub Issues or Discussions.
2. Email security concerns privately to security@forgecore.dev or open a Private Security Advisory on GitHub.
3. Include clear reproduction steps or proof-of-concept scripts.

We take security seriously and will acknowledge receipt within 48 hours and work with you on a timely patch.

---

## Command Execution Trust Boundary

ForgeCore enforces a strict security trust boundary for test suite execution:

1. **Allowlisted Executables:** ForgeCore only executes allowlisted binaries (`ruff`, `semgrep`, `pytest`, `python -m pytest`, `npm`, `npx`, `eslint`, `tsc`, `mvn`, `gradle`, `./gradlew`). Path-based relative executables (e.g. `./evil/pytest`) and shell metacharacters are strictly rejected.
2. **Approval as the Real Security Boundary:** Allowlisted test tools (`npm`, `mvn`, `gradle`, `pytest`) execute repository code by design (e.g., `conftest.py`, test setup hooks, package scripts). Therefore, binary allowlisting alone cannot prevent arbitrary code execution from malicious repository contents. **User approval is the real trust boundary.**
3. **Approval Coverage:** Approval covers **ANY** execution of project test commands, including auto-detected/default test suites, not only custom commands from `project.yaml`. Approval records are stored outside the repository in the user's configuration directory (`~/.forgecore/approvals.json`), keyed by project root and the cryptographic hash of the effective command set. Any change to project test commands invalidates approval and requires re-approval via `forgecore approve`.
