# ForgeCore Security Notes

## Command Execution Trust Boundary

ForgeCore enforces a strict security trust boundary for test suite execution:

1. **Allowlisted Executables:** ForgeCore only executes allowlisted binaries (`ruff`, `semgrep`, `pytest`, `python -m pytest`, `npm`, `npx`, `eslint`, `tsc`, `mvn`, `gradle`, `./gradlew`). Path-based relative executables (e.g. `./evil/pytest`) and shell metacharacters are strictly rejected.
2. **Approval as the Real Security Boundary:** Allowlisted test tools (`npm`, `mvn`, `gradle`, `pytest`) execute repository code by design (e.g., `conftest.py`, test setup hooks, package scripts). Therefore, binary allowlisting alone cannot prevent arbitrary code execution from malicious repository contents. **User approval is the real trust boundary.**
3. **Approval Coverage:** Approval covers **ANY** execution of project test commands, including auto-detected/default test suites, not only custom commands from `project.yaml`. Approval records are stored outside the repository in the user's configuration directory (`~/.forgecore/approvals.json`), keyed by project root and the cryptographic hash of the effective command set. Any change to project test commands invalidates approval and requires re-approval via `forgecore approve`.
