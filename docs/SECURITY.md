# Sarthi Security Notes

## Command Execution Trust Boundary

Sarthi enforces a strict security trust boundary for test suite execution:

1. **Allowlisted Executables:** Sarthi only executes allowlisted binaries (`ruff`, `semgrep`, `pytest`, `python -m pytest`, `npm`, `npx`, `eslint`, `tsc`, `mvn`, `gradle`, `./gradlew`). Path-based relative executables (e.g. `./evil/pytest`) and shell metacharacters are strictly rejected.
2. **Approval as the Real Security Boundary:** Allowlisted test tools (`npm`, `mvn`, `gradle`, `pytest`) execute repository code by design (e.g., `conftest.py`, test setup hooks, package scripts). Therefore, binary allowlisting alone cannot prevent arbitrary code execution from malicious repository contents. **User approval is the real trust boundary.**
3. **Approval Coverage:** Approval covers **ANY** execution of project test commands, including auto-detected/default test suites, not only custom commands from `project.yaml`. Approval records are stored outside the repository in the user's configuration directory (`~/.sarthi/approvals.json`), keyed by project root and the cryptographic hash of the effective command set. Any change to project test commands invalidates approval and requires re-approval via `sarthi approve`.
4. **Approval Covers the Command Set, Not Repo Contents:** Approval records and locks the cryptographic hash of the *command set* (`verify.commands`), not repository contents. Because allowlisted build and test runners execute repository code by design (e.g. `conftest.py`, `package.json` test scripts, build hooks), approving a command set authorizes those tools to run against repo files. To prevent automated scripts or AI agents running in a subshell from self-approving via pipes, `sarthi approve` strictly requires an interactive terminal (real TTY) and refuses execution with a non-zero exit code if stdin is piped or non-interactive.
5. **Accident Protection vs. Adversarial Agents:** The interactive TTY check and the user approvals file are **accident protection**, not a security boundary against a determined agent. If an agent already has shell access or local filesystem write permissions outside the sandbox, it could allocate a pseudo-terminal (PTY) or write directly to `~/.sarthi/approvals.json`. These mechanisms prevent casual, piped, or accidental self-approval during automated workflows; true host containment against hostile agents requires containerization, virtualization, or OS-level sandboxing.

## Verification Runners: Required vs. Optional Checks

Sarthi verification distinguishes between **required** checks and **optional** checks:

| Runner | Name | Classification | Behavior When Missing / Unconfigured |
| :--- | :--- | :--- | :--- |
| `SecretsRunner` | `secrets` | **Required** | Deterministic in-process regex scanner for credentials and tokens. Failure to run marks verification `incomplete`. |
| `RuffRunner` | `ruff` | **Required** | Static lint and security analyzer for Python. Required whenever Python files or layers exist. If `ruff` is not installed, verification status is `incomplete`. |
| `ESLintRunner` | `eslint` | **Required** | Static analyzer for JavaScript / TypeScript. Required whenever JS/TS files or layers exist. If `eslint` is not installed, verification status is `incomplete`. |
| `TestRunner` | `tests` | **Required** | Automated project test suite runner. Required whenever a test suite or command is configured. Missing test runner binary or unapproved commands mark verification status as `incomplete`. |
| `SemgrepRunner` | `semgrep` | **Optional** | Semantic AST/rule verifier. Missing `semgrep` (common on Windows environments) produces a diagnostic warning in the report and `report.warnings`, but does **not** mark verification status as `incomplete`. |
| `ChecklistRunner` | `checklist` | **Optional** | Advisory checklist for agent or developer confirmation. Checklist items do not block or fail deterministic verification status. |

