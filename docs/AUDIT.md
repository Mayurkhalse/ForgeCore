# ForgeCore Repository Audit Report

**Date:** 2026-11-03  
**Auditor:** Antigravity Coding Assistant  
**Repository:** `ForgeCore` (commit `526ec1629518577fe7102ffc571d17da855a377b`)  
**Scope:** Thorough audit against specifications in `README.md`. No new code built.

---

## Executive Summary Table

| Area | Status | Evidence Label | One-Line Summary Reason |
|---|---|---|---|
| **Test Suite Execution** | **PASS** | `[RAN]` | All 23 unit and integration tests passed cleanly in 3.43s. |
| **Code Linting** | **PASS** | `[RAN]` | Ruff check reported 0 errors with pyproject.toml configuration. |
| **Standards Schema Validation** | **PASS** | `[RAN]` | `forgecore lint-standards` passed with 0 schema or reference errors. |
| **Environment Diagnostics** | **PASS** | `[RAN]` | `forgecore doctor` correctly identifies Python 3.13, AGY directory, Git, and Ruff. |
| **Test Alterations Audit** | **PASS** | `[READ]` | No test was weakened; test assertions accurately reflect line numbers and statuses. |
| **Standards Quality Bar** | **FAIL** | `[RAN]` / `[READ]` | Only `react` meets the bar (≥5 machine verifiers); 5 stacks fail and are not labeled experimental. |
| **Semgrep Live Verification** | **UNVERIFIED** | `[RAN]` | Semgrep CLI is not installed in the Windows environment, so live rule triggering was unverified. |
| **Stack Detection** | **PARTIAL** | `[RAN]` | Monorepo and dual-manifest detected cleanly, but `max_depth=3` misses standard Java package paths. |
| **PathGuard Security** | **PASS** | `[RAN]` / `[READ]` | Traversal (`..\..\x`), absolute paths, and secrets (`.env`, `id_rsa`) are strictly blocked. |
| **Subprocess Execution Safety** | **PARTIAL** | `[READ]` | All calls use argv lists, timeouts, and pinned cwd, but project.yaml test command lacks a binary allowlist. |
| **Verify Loop Degradation** | **PASS** | `[RAN]` | Clean project with missing tools reports `incomplete` and never `passed`. |
| **Token Budget Compliance** | **PASS** | `[RAN]` | Contract (652 tokens) and get_standards (1,736 tokens) stay within budgets (2,000 & 3,000). |
| **Prompt Injection Fencing** | **FAIL** | `[RAN]` / `[READ]` | Project-derived strings are not fenced with `<untrusted_project_data>` as claimed in README 8.4. |
| **MCP stdio Integration** | **PARTIAL** | `[RAN]` / `[READ]` | All 6 tools work with structured outputs via direct manager; raw stdio pipes block on Windows anyio. |
| **Antigravity Instructions Field**| **UNVERIFIED** | `[READ]` | Official AGY docs only specify tool discovery; whether MCP `instructions` reaches model is unverified. |
| **Installer Safety & Reversibility**| **PARTIAL** | `[RAN]` / `[READ]` | Install/uninstall is completely reversible and preserves user data, but makes no backup copies. |
| **README Specification Parity** | **FAIL** | `[RAN]` / `[READ]` | 15 expected files/directories (including `evals/`, `docs/`, `scripts/`) are missing from the repo. |

---

## PART 1: Baseline Verification

### 1. Baseline Test and Linter Execution

The baseline verification commands were executed in the project virtual environment:

- **`uv run pytest -q`** `[RAN]`
  - Command: `uv run pytest -q; echo "EXIT_CODE: $LASTEXITCODE"`
  - Exit code: `0`
  - Output:
    ```
    .......................                                                  [100%]
    23 passed in 3.43s
    EXIT_CODE: 0
    ```
- **`uv run ruff check .`** `[RAN]`
  - Command: `uv run ruff check .; echo "EXIT_CODE: $LASTEXITCODE"`
  - Exit code: `0`
  - Output:
    ```
    All checks passed!
    EXIT_CODE: 0
    ```
- **`uv run forgecore lint-standards`** `[RAN]`
  - Command: `uv run forgecore lint-standards; echo "EXIT_CODE: $LASTEXITCODE"`
  - Exit code: `0`
  - Output:
    ```
    Linting ForgeCore Standards Library...
    All standards, profiles, and verifiers passed schema validation!
    EXIT_CODE: 0
    ```
- **`uv run forgecore doctor`** `[RAN]`
  - Command: `uv run forgecore doctor; echo "EXIT_CODE: $LASTEXITCODE"`
  - Exit code: `0`
  - Output:
    ```
    Running ForgeCore Environment Diagnostics...

    +-----------------------------------------------------------------------------+
    | Status   | Check                          | Details                         |
    |----------+--------------------------------+---------------------------------|
    | PASS     | Python Version                 | Python 3.13.5                   |
    | PASS     | Antigravity Global Directory   | Path 'C:\Users\Rajendra\.gemini\config' exists |
    | WARN     | MCP Server Registration        | forgecore not registered (Hint: Run forgecore install antigravity) |
    | WARN     | Global Core Contract Rule      | Core contract not installed (Hint: Run forgecore install antigravity) |
    | PASS     | Git CLI                        | Found git at C:\Program Files\Git\cmd\git.EXE |
    | PASS     | Ruff Linter                    | Found ruff at C:\Users\Rajendra\Desktop\Projects\ForgeCore\.venv\Scripts\ruff.exe |
    | WARN     | Semgrep                        | Semgrep not found (optional)    |
    +-----------------------------------------------------------------------------+
    EXIT_CODE: 0
    ```

### 2. Git History and Test Alterations Audit

- **`git log --stat`** `[RAN]` shows a single unified commit: `526ec1629518577fe7102ffc571d17da855a377b` (`feat: implement ForgeCore architecture, core, standards, MCP server, verify loop, and CLI`).
- **Internal modification audit during development** `[READ]`:
  1. In `src/forgecore/core/verify/runners/secrets.py:72`, `SecretsRunner` initially skipped any line containing the substring `"example"`. In `tests/fixtures/violations_app/auth.py`, the seeded key was `AKIAIOSFODNN7EXAMPLE`. The runner skipped the line due to the overly broad `"example"` substring check. The code was fixed in `secrets.py` (`lines 70-73`) to only skip lines starting with comment delimiters (`#`, `//`, `/*`), and the test fixture was updated to `AKIA1234567890ABCDEF`. **Verdict: Fixed the code bug; did not loosen the check.**
  2. In `tests/unit/test_verify.py:21`, `secret_findings[0].line` was initially asserted to be `line == 4`. When Ruff removed an unused `import os` statement from `auth.py`, the secret shifted to line 2. The test assertion was adjusted to `line == 2` to match exact file coordinates. **Verdict: Correct line synchronization; did not weaken the check.**
  3. In `tests/unit/test_verify.py:33`, `test_verifier_clean_fixture` asserts `assert report.status in ("passed", "incomplete")`. This was intentionally written to reflect Section 9.2 of `README.md`: on machines without Semgrep installed, verification cannot report `"passed"`; it must report `"incomplete"`. **Verdict: Complies with README contract.**

---

## PART 2: Standards Library Quality

### 3. Layer Breakdown Table

README Section 6.2 specifies:
> "Quality bar per stack layer for v0.1: at least 12 rules, of which at least 5 are machine-verifiable. A stack that does not meet the bar ships labeled experimental in the docs."

The following breakdown was calculated directly from all YAML files in `standards/` `[RAN]`:

| Layer | Total Rules | Real Machine Verifiers | Checklist / Guidance | Missing Verifier Refs | Quality Bar Status |
|---|---|---|---|---|---|
| `universal` (cross-cutting) | 4 | 2 (secrets, ruff) | 2 | 0 | N/A (Cross-cutting) |
| `security` (cross-cutting) | 3 | 1 (semgrep) | 2 | 0 | N/A (Cross-cutting) |
| `testing` (cross-cutting) | 2 | 0 | 2 | 0 | N/A (Cross-cutting) |
| `api-design` (cross-cutting) | 2 | 0 | 2 | 0 | N/A (Cross-cutting) |
| `observability` (cross-cutting) | 1 | 0 | 1 | 0 | N/A (Cross-cutting) |
| **`react`** | **12** | **6 (eslint)** | **6** | **0** | **MEETS BAR** |
| **`fastapi`** | **13** | **3 (1 semgrep, 2 ruff)** | **10** | **0** | **FAILS BAR** (3 < 5) |
| **`node-express`** | **12** | **2 (eslint)** | **10** | **0** | **FAILS BAR** (2 < 5) |
| **`react-native`** | **12** | **2 (eslint)** | **10** | **0** | **FAILS BAR** (2 < 5) |
| **`python-ml`** | **12** | **1 (ruff)** | **11** | **0** | **FAILS BAR** (1 < 5) |
| **`spring-boot`** | **12** | **0** | **12** | **0** | **FAILS BAR** (0 < 5) |

### 4. Stack Layers Missing Quality Bar

Five out of the six stack layers miss the quality bar of at least 5 machine-verifiable rules:
1. `fastapi` (3 machine verifiers) — Deficit: 2 rules.
2. `node-express` (2 machine verifiers) — Deficit: 3 rules.
3. `react-native` (2 machine verifiers) — Deficit: 3 rules.
4. `python-ml` (1 machine verifier) — Deficit: 4 rules.
5. `spring-boot` (0 machine verifiers) — Deficit: 5 rules.

**Recommendation:** As mandated by README Section 6.2, `fastapi`, `node-express`, `react-native`, `python-ml`, and `spring-boot` must be labeled **`experimental`** in documentation until additional Semgrep, Ruff, or ESLint rules are authored to reach 5 machine verifiers per layer.

### 5. Sample of 10 Rules Evaluated

Ten rules were sampled deterministically using `random.Random(42).sample(all_rules, 10)` `[RAN]`:

1. **`UNI-ARCH-001` (`universal`)**
   - *Rule:* "Route handlers, controllers, and UI views must never execute raw database queries or business computations directly. Delegate all domain operations to isolated services."
   - *Judgment:* **Generic / Advisory.** While foundational, "separate concerns" is standard advice any LLM recites. Verified via checklist only.
2. **`FAPI-TEST-001` (`fastapi`)**
   - *Rule:* "Write automated tests for FastAPI routes using `starlette.testclient.TestClient` or `httpx.AsyncClient`. Override database and auth dependencies via `app.dependency_overrides`."
   - *Judgment:* **Specific & Actionable.** Explicitly mandates FastAPI's `dependency_overrides` idiom instead of arbitrary monkeypatching.
3. **`FAPI-ARCH-002` (`fastapi`)**
   - *Rule:* "Define modular endpoints within separate routers using `APIRouter(prefix=..., tags=...)` and mount them on the root application using `app.include_router(router)`."
   - *Judgment:* **Specific & Checkable.** Concrete requirement preventing monolithic `app = FastAPI()` endpoint accumulation.
4. **`ML-CHK-001` (`python-ml`)**
   - *Rule:* "Save best model weights based on validation loss and halt training if validation metric stops improving."
   - *Judgment:* **Generic Advice.** Standard ML best practice without strict implementation constraint.
5. **`ML-MEM-001` (`python-ml`)**
   - *Rule:* "Wrap evaluation and inference loops in `with torch.no_grad():` or use `@torch.inference_mode()`."
   - *Judgment:* **Specific & Checkable.** Enforces a concrete syntax pattern preventing VRAM exhaustion during PyTorch inference.
6. **`ML-REP-001` (`python-ml`)**
   - *Rule:* "Explicitly set seeds for standard library `random`, `numpy.random`, and deep learning frameworks (`torch.manual_seed`, `torch.cuda.manual_seed_all`, `tf.random.set_seed`)."
   - *Judgment:* **Specific & Actionable.** Names exact seeding functions required across libraries.
7. **`NODE-ASYNC-001` (`node-express`)**
   - *Rule:* "In Express 4, wrap asynchronous route handlers with `try/catch (err) { next(err); }` or use a wrapper helper / `express-async-errors`."
   - *Judgment:* **Highly Specific & Opinionated.** Directly targets Express 4's unhandled promise bug where unhandled rejections hang HTTP requests.
8. **`FAPI-LIFESPAN-001` (`fastapi`)**
   - *Rule:* "Use `@asynccontextmanager async def lifespan(app: FastAPI)` instead of the deprecated `@app.on_event('startup')` and `@app.on_event('shutdown')`."
   - *Judgment:* **Highly Specific & Checkable.** Modernizes FastAPI app initialization away from deprecated events.
9. **`SB-DATA-001` (`spring-boot`)**
   - *Rule:* "When querying entities with `@OneToMany` or `@ManyToMany` relationships, use `JOIN FETCH` in JPQL or declare `@EntityGraph` to load relations eagerly in a single SQL query."
   - *Judgment:* **Highly Specific & Checkable.** Targets the classic JPA N+1 select performance antipattern.
10. **`FAPI-ERR-001` (`fastapi`)**
    - *Rule:* "When handling domain errors, raise `HTTPException(status_code=..., detail=...)` or map custom domain exceptions via `@app.exception_handler`."
    - *Judgment:* **Specific.** Dictates structured exception throwing over generic runtime exceptions.

### 6. Semgrep Verifiers Good/Bad Evaluation

- Executed `uv run python -c "import shutil; print(shutil.which('semgrep'))"` `[RAN]`.
- Output: `None`.
- **Finding:** Semgrep is not installed in the Windows environment (`doctor` also emitted `WARN: Semgrep not found (optional)`).
- **Status:** **`[UNVERIFIED]`**. Because the semgrep CLI binary was absent, live execution of the Semgrep rules against their respective good and bad code snippets could not be run.
- **Static Inspection of Rules `[READ]`:**
  - `standards/verifiers/semgrep/fastapi-rules.yaml`: Matches `$DB: Session = Depends(...)` followed by `$DB.add(...)` or `$DB.query(...)` inside route handlers.
  - `standards/verifiers/semgrep/security-rules.yaml`: Matches `$DB.execute("..." + $VAR)` and f-string formatted queries.

---

## PART 3: Core Correctness

### 7. Stack Detection Verification

#### Execution on Fixtures `[RAN]`
- `tests/fixtures/fastapi_app`: Detected `fastapi` (conf: 1.0, version: 0.110.0), profile: `react-fastapi`.
- `tests/fixtures/ml_app`: Detected `python-ml` (conf: 0.85), profile: `python-ml`.
- `tests/fixtures/node_app`: Detected `node-express` (conf: 1.0, version: 4.19.2), profile: `react-node`.
- `tests/fixtures/react_app`: Detected `react` (conf: 1.0, version: 18.2.0), profile: `react-node`.
- `tests/fixtures/spring_app`: Detected `spring-boot` (conf: 0.95, version: 3.2.4), profile: `java-springboot`.
- `tests/fixtures/violations_app`: Detected `python` language; no framework layers detected.

#### Defect Found: Java Directory Depth `[RAN]` / `[READ]`
In `spring_app`, `sp.languages` was detected as `[]` (empty list). Inspection of `StackDetector.scan_files` (`src/forgecore/core/stack_detector.py:38`) revealed `max_depth = 3`. Standard Java packages like `src/main/java/com/example/Application.java` are 6 directories deep and were skipped by `scan_files()`.

#### Adversarial Cases `[RAN]`
1. **Empty folder:**
   - Layers: `[]`, Suggested Profile: `None`, Confidence: `{}`. Handled cleanly without errors.
2. **Monorepo with `frontend/` (React) and `backend/` (FastAPI):**
   - Layers: `['react', 'fastapi']`.
   - Suggested Profile: `react-fastapi`.
   - Evidence correctly preserved relative paths: `frontend/package.json` and `backend/pyproject.toml`.
3. **Dual Manifest at Root (`package.json` + `pyproject.toml`):**
   - Layers: `['node-express', 'python-ml']`.
   - Suggested Profile: Arbitrarily selected `python-ml` due to linear `if/elif` cascade in `_infer_profile()`.

### 8. PathGuard Adversarial Verification

Executed against `src/forgecore/core/pathguard.py` `[RAN]`:

- `..\..\x`: **BLOCKED** with `PathTraversalError: Access denied: '..\..\x' resolves outside project root`.
- Absolute path outside root (`C:\...\outside.txt`): **BLOCKED** with `PathTraversalError`.
- Reading `.env`: **BLOCKED** with `SecretFileAccessError: Access denied: '.env' is flagged as a sensitive secret file`.
- Reading `id_rsa`: **BLOCKED** with `SecretFileAccessError: Access denied: 'id_rsa' is flagged as a sensitive secret file`.
- Windows case insensitivity (`.ENV`, `id_RSA`): **BLOCKED** with `SecretFileAccessError` (case-normalized pattern matching).
- Trailing dots/spaces on Windows (`normal.txt.`, `normal.txt `): Successfully normalized by Windows OS path layer to `normal.txt` (not secret).
- Directory junctions pointing outside root `[READ]`: `PathGuard.safe_path()` calls `Path(target).resolve()`. On POSIX and Windows, `.resolve()` resolves the target path; `p.relative_to(self.root)` fails with `ValueError` and raises `PathTraversalError`.

### 9. Subprocess Command Execution Audit

Parsed via Python AST across all source files in `src/` `[RAN]`:

| File & Line | Command Executed | `shell=True`? | Has Timeout? | `cwd` Pinned to Root? | Allowlist Checked? |
|---|---|---|---|---|---|
| `verifier.py:43` | `['git', 'diff', '--name-only', 'HEAD']` | No | Yes (5s) | Yes (`self.root`) | Hardcoded Git |
| `verifier.py:58` | `['git', 'status', '--porcelain']` | No | Yes (5s) | Yes (`self.root`) | Hardcoded Git |
| `eslint.py:47` | `[*cmd_prefix, "--format=json", *files]` | No | Yes (45s) | Yes (`ctx.project_root`) | Hardcoded ESLint binary |
| `ruff.py:48` | `[bin_path, "check", "--output-format=json", *files]` | No | Yes (30s) | Yes (`ctx.project_root`) | Hardcoded Ruff binary |
| `semgrep.py:53` | `["semgrep", "--config=...", "--json", *files]` | No | Yes (45s) | Yes (`ctx.project_root`) | Hardcoded Semgrep binary |
| `tests.py:54` | `cmd = self._resolve_command(ctx)` | No | Yes (60s) | Yes (`ctx.project_root`) | **PARTIAL** |

**Security Defect Found in `tests.py:21-23` `[READ]`:**
```python
custom_cmd = ctx.config.verify.commands.get("test")
if custom_cmd:
    return shlex.split(custom_cmd)
```
If a project `.forgecore/project.yaml` specifies `commands.test`, it is tokenized with `shlex.split` and executed without verifying that the command binary is an allowlisted test runner (e.g. `pytest`, `npm`, `mvn`, `gradle`, `cargo`).

### 10. Verify Loop Missing Tool Degradation

- Executed `uv run forgecore verify tests/fixtures/fastapi_app --all --json` `[RAN]`.
- Output:
  ```json
  {
    "status": "incomplete",
    "findings": [],
    "skipped": [
      {"check": "semgrep", "reason": "not installed or not configured in environment"},
      {"check": "tests", "reason": "not installed or not configured in environment"}
    ],
    "next_action": "No failures found, but 2 check(s) were skipped (semgrep, tests). Install missing tools for complete verification."
  }
  ```
- **Finding:** Correctly returns status `"incomplete"` when checks are skipped, fulfilling the requirement that skipped tools never report `"passed"`.

### 11. Context Budget Compliance

Measured token sizes (`chars // 4`) against README Section 7.4 budgets `[RAN]`:

- **Core Contract (`standards/contract.md`):**
  - Characters: 2,605
  - Measured Tokens: ~652
  - Budget: ≤ 2,000 tokens (**Passes**, 32.6% of budget)
- **`initialize_project` response:**
  - Characters: 1,825
  - Measured Tokens: ~457
  - Budget: ≤ 1,500 tokens (**Passes**, 30.5% of budget)
- **`get_standards` worst-case response (all layers, max_rules=50):**
  - Characters: 6,942
  - Measured Tokens: ~1,736 (12 rules returned, truncated flag: `True`)
  - Budget: ≤ 3,000 tokens (**Passes**, 57.8% of budget)
- **`get_workflow` response:**
  - Characters: 883 to 1,140
  - Measured Tokens: ~221 to ~285
  - Budget: ≤ 1,200 tokens (**Passes**, ~23.7% of budget)

### 12. Prompt-Injection Hygiene

Tested against a fixture with a package name and file containing `"IGNORE ALL PREVIOUS INSTRUCTIONS"` `[RAN]`:
- In `src/forgecore/mcp/tools.py:64` `[READ]`:
  ```python
  "evidence": json.loads(fence_untrusted_data(profile.evidence).replace("<untrusted_project_data>\n", "").replace("\n</untrusted_project_data>", ""))
  ```
  The code explicitly stripped the fencing tags!
- In `initialize_project`: `project_name` is output as a raw string without fencing.
- In `verify_project`: Findings containing file names with injection payloads are returned as raw string fields (`file: "..."`) without fencing tags.
- **Finding:** **Fails README 8.4.** README claims: "strings from the project are fenced and labeled `untrusted_project_data`". The implementation does not wrap project strings with `<untrusted_project_data>` tags.

---

## PART 4: MCP and Antigravity Integration

### 13. MCP Tools Execution

All six MCP tools were invoked via `MCPServer._tool_manager.get_tool(...)` `[RAN]`:

| Tool | Response Payload Size | Error / Status | Notes |
|---|---|---|---|
| `initialize_project` | 1,932 bytes | `status: "initialized"` | Clean stack profile and contract summary |
| `get_project_context` | 305 bytes | `status: "ok"` | Returns cached context and version |
| `get_standards` | 7,954 bytes | `status: "ok"` | Returns 12 budgeted rules |
| `get_workflow` | 1,176 bytes | `status: "ok"` | Renders Markdown with project commands |
| `get_rule` | 1,188 bytes | `status: "ok"` | Full rule with good/bad examples |
| `verify_project` | 3,176 bytes | `status: "incomplete"` | Verification report with findings and checklist |

**Stdio Transport Defect on Windows `[RAN]` / `[READ]`:**
When spawning `python -m forgecore.cli serve` through `mcp.client.stdio.stdio_client`, the client process hung indefinitely. Inspection of `mcp.server.stdio._claim_fd` (`mcp/server/stdio.py:53`) revealed that `mcp 2.3.0` redirects `stdin` with `os.dup2(diversion_fd, 0)` and wraps it with `anyio.wrap_file(stdin)`. In Windows sandboxes, `anyio.wrap_file(sys.stdin)` deadlocks in worker threads on blocking `ReadFile` calls.

### 14. Verification of `docs/antigravity-notes.md`

Audited against official Antigravity documentation in `~/.gemini/antigravity/builtin/skills/` `[READ]`:

1. **MCP Config Path (`~/.gemini/config/mcp_config.json`)**:
   - `[READ]` `agy-customizations/docs/mcp_servers.md:19-20`. Verified.
2. **MCP Schema (`mcpServers: { ... }`)**:
   - `[READ]` `agy-customizations/docs/mcp_servers.md:31-45`. Verified.
3. **Global Rule Locations (`GEMINI.md` / `AGENTS.md`)**:
   - `[READ]` `agy-customizations/docs/rules.md:11-16` & `agy-customizations/SKILL.md:52-54`. Verified.
4. **Lifecycle Hooks (`hooks.json` events)**:
   - `[READ]` `agy-customizations/docs/hooks.md:85-106`. Verified.
5. **Does Antigravity pass MCP `instructions` to the model?**:
   - In `agy-customizations/docs/mcp_servers.md:74-84`, the document specifies "1. Tool Discovery", "2. Tool Injection" (tools added to toolset), and "3. Execution". It contains **no mention** of passing the MCP `instructions` field from server initialization into the system prompt.
   - **Verdict:** **`[UNVERIFIED]`**. There is currently no evidence that Antigravity surfaces the MCP `instructions` field to the LLM context.

### 15. Installer Safety and Idempotency Audit

Tested via `AntigravityAdapter.install()` and `AntigravityAdapter.uninstall()` against an isolated temporary directory `[RAN]`:

- **Preservation of User Content:** Pre-existing entries in `mcp_config.json` (`existing-tool`) and `GEMINI.md` (`# My Custom User Rules`) were preserved intact.
- **Clean Uninstall:** `adapter.uninstall()` removed the `forgecore` server entry, stripped the managed comment block from `GEMINI.md`, and deleted the tracking manifest.
- **File Diff Before vs. After Uninstall:** Byte-for-byte identical (`True` for both `mcp_config.json` and `GEMINI.md`).
- **Shortcoming Identified `[READ]`:** The installer does NOT create backup files (e.g. `mcp_config.json.bak` or `GEMINI.md.bak`) prior to modification. If an unhandled exception or process termination occurs during disk write, user configuration could be corrupted.

---

## PART 5: README versus Reality

### 16. Exhaustive Discrepancy List

The following files, features, and behaviors described in `README.md` are missing or diverge from the codebase:

#### Missing Files & Directories (from README Section 12) `[RAN]`
1. `src/forgecore/adapters/antigravity/templates` — Directory does not exist (templates are inlined as python strings).
2. `standards/verifiers/eslint` — Directory for shared ESLint rules does not exist.
3. `evals/` — Entire evaluation directory is missing:
   - `evals/prompts/`
   - `evals/rubric.yaml`
   - `evals/run_eval.py`
   - `evals/results/`
4. `docs/ARCHITECTURE.md` — Missing.
5. `docs/RULE_AUTHORING.md` — Missing (partially covered in `CONTRIBUTING.md`).
6. `docs/ADAPTERS.md` — Missing.
7. `docs/ROADMAP.md` — Missing.
8. `.github/ISSUE_TEMPLATE/` — Missing.
9. `.github/PULL_REQUEST_TEMPLATE.md` — Missing.
10. `scripts/setup.ps1` — Missing.
11. `scripts/setup.sh` — Missing.

#### Behavioral & Architectural Discrepancies
12. **Prompt-Injection Fencing (README 8.4):** Fencing with `<untrusted_project_data>` is not applied to project strings in MCP tool outputs.
13. **Command Allowlist (README 13):** Test commands from `.forgecore/project.yaml` are executed via `shlex.split` without validating against an allowed binary list.
14. **Scan Depth in Monorepos & Java (README 7.1):** Hardcoded `max_depth = 3` in `StackDetector.scan_files()` fails to discover Java source files located in standard `src/main/java/...` package paths.
15. **CI Workflow Discrepancy (README 12):** `.github/workflows/ci.yml` runs `ruff check`, `lint-standards`, and `pytest`, but omits `forgecore verify`.
16. **Lack of Installer Backups (README 10):** Adapter modifies `mcp_config.json` and `GEMINI.md` in place without creating `.bak` copies.
17. **Experimental Labels Missing (README 6.2):** `fastapi`, `node-express`, `react-native`, `python-ml`, and `spring-boot` fail the quality bar (≥5 machine verifiers) but are not labeled experimental in docs or profiles.

---

## Prioritised Fix List

### P0: Blocking a Trustworthy v0.1 (Integrity & Security)

1. **Implement Prompt-Injection Fencing (README 8.4)**
   - *Issue:* Project names, evidence paths, and file paths are not wrapped in `<untrusted_project_data>` boundaries.
   - *Fix:* Ensure all data sourced from files or directories is wrapped with `<untrusted_project_data>` tags in MCP outputs.
   - *Effort Estimate:* 2 hours.

2. **Fix `scan_files` Depth for Java and Deep Monorepos**
   - *Issue:* `max_depth = 3` causes `spring_app` to detect `Languages: []`.
   - *Fix:* Increase default scan depth to 6, while maintaining skip logic for `node_modules`, `.venv`, `.git`, `target`, `build`.
   - *Effort Estimate:* 1 hour.

3. **Label Stacks Failing Quality Bar as "Experimental"**
   - *Issue:* 5 of 6 stack layers have fewer than 5 machine verifiers.
   - *Fix:* Update documentation and `profile.yaml` metadata to mark `fastapi`, `node-express`, `react-native`, `python-ml`, and `spring-boot` as experimental, or author additional Semgrep/Ruff verifiers.
   - *Effort Estimate:* 2 hours (doc labeling) / 1.5 days (authoring 15+ missing verifier rules).

4. **Add Binary Allowlist for Configured Test Commands (README 13)**
   - *Issue:* `tests.py` executes arbitrary commands from `project.yaml`.
   - *Fix:* Enforce an allowlist of permitted test binaries (`pytest`, `npm`, `npx`, `pnpm`, `yarn`, `mvn`, `gradle`, `cargo`, `go`, `dotnet`).
   - *Effort Estimate:* 1.5 hours.

5. **Installer Backups**
   - *Issue:* `mcp_config.json` and `GEMINI.md` are updated without backups.
   - *Fix:* Create `.bak` timestamped copies prior to writing, and clean up backup references in uninstall.
   - *Effort Estimate:* 1 hour.

### P1: Important for Full Developer Workflow

6. **Add Missing Documentation Files**
   - *Issue:* `docs/ARCHITECTURE.md`, `docs/RULE_AUTHORING.md`, `docs/ADAPTERS.md`, `docs/ROADMAP.md` do not exist.
   - *Fix:* Author the missing documentation files referenced in Section 12.
   - *Effort Estimate:* 4 hours.

7. **Add Verification Step to CI Workflow**
   - *Issue:* `.github/workflows/ci.yml` omits `forgecore verify`.
   - *Fix:* Add a `run: uv run forgecore verify . --all` step to CI.
   - *Effort Estimate:* 30 minutes.

8. **Add Setup Scripts & Issue Templates**
   - *Issue:* `scripts/setup.ps1`, `scripts/setup.sh`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` do not exist.
   - *Fix:* Scaffold cross-platform bootstrap scripts and standard GitHub templates.
   - *Effort Estimate:* 2 hours.

### P2: Evaluation & Benchmark Infrastructure (Milestone 6)

9. **Build `evals/` Harness & Benchmark Suite**
   - *Issue:* `evals/` folder with 10+ standard tasks, rubric, and runner does not exist.
   - *Fix:* Build out `evals/prompts/`, `evals/rubric.yaml`, `evals/run_eval.py`, and initial baseline results.
   - *Effort Estimate:* 2-3 days.

---

## What I Could Not Verify and Why

1. **Semgrep Live Rule Execution Against Good/Bad Examples `[UNVERIFIED]`:**
   - *Reason:* The `semgrep` binary is not installed in the local Windows Python 3.13 development environment. Per the read-only rules of this audit, no new external packages were installed.
2. **Antigravity Passing MCP `instructions` to Agent System Context `[UNVERIFIED]`:**
   - *Reason:* The official Antigravity documentation in `~/.gemini/antigravity/builtin/skills/agy-customizations/docs/mcp_servers.md` describes tool discovery and execution, but makes no statement regarding the handling or surfacing of MCP server `instructions`. Determining whether the instructions reach the model requires a live token-inspection hook inside Antigravity's internal planner, which is not externally observable.
3. **Windows Junction Escape in PathGuard `[UNVERIFIED]`:**
   - *Reason:* Creating Windows directory junctions (`mklink /J` or `_winapi.CreateJunction`) in the unprivileged sandbox environment fails with `PermissionError: [WinError 5] Access is denied`. Path containment behavior was verified via code inspection of `Path.resolve()`.

