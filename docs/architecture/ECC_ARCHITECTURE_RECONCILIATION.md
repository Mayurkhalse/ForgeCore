# ECC Architecture Reconciliation & Verification Report

> **Document:** `docs/architecture/ECC_ARCHITECTURE_RECONCILIATION.md`  
> **Status:** Ratified Reconciliation Report  
> **Target Project:** Sarthi (evolving from ForgeCore)  
> **Upstream Release Baseline:** Everything Claude Code (ECC) v2.2.3  
> **Authoritative Commit SHA:** `c05b2d6614f62f6db0047669aa4eefb223d478f9` (abbreviated `c05b2d6`)  
> **Release Tag Object SHA:** `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`  
> **Author:** Principal Software Architect & Senior Python Systems Engineer  

---

## 1. Executive Summary & Objective

Prior to commencing the physical acquisition and bundling of Everything Claude Code (ECC) resources, an independent architectural audit was conducted on the preliminary integration design documents:
- `docs/architecture/ECC_INTEGRATION_DESIGN.md`
- `docs/architecture/ECC_RESOURCE_INVENTORY.md`
- `docs/architecture/ECC_INTEGRATION_ROADMAP.md`
- `docs/architecture/ECC_ARCHITECTURE_DECISIONS.md`

The audit revealed critical factual inaccuracies, misinterpretations of the upstream ECC repository layout, supply-chain version ambiguities, and structural security weaknesses in the proposed precedence model.

This document formally records:
1. The specific discrepancies identified in the preliminary documents.
2. Verified factual evidence obtained directly from the official upstream repository (`https://github.com/affaan-m/ECC`).
3. Concrete architectural corrections applied across all design specifications.
4. The explicit boundary separating **verified facts** from **architectural recommendations**.
5. Mandatory sign-off gates that must be satisfied before Milestone 1 snapshot acquisition commences.

---

## 2. Identified Discrepancies in Preliminary Architecture

The independent review uncovered five major discrepancies and architectural risks in the preliminary documentation:

### Discrepancy 1: Incorrect Upstream Git Commit SHA for v2.2.3
- **Preliminary Claim:** The preliminary architecture documents (ADR-001, Design, Inventory, Roadmap) anchored the integration to ECC `v2.2.3` at Git commit `b38be6a`.
- **Factual Reality:** The official release tag `v2.2.3` does **not** point to `b38be6a`. Commit `b38be6a` is a post-release commit on `main` merged on October 29/30, 2026 (PR #3809), nearly a month after release `v2.2.3` was tagged. The true release commit tagged as `v2.2.3` is `c05b2d6614f62f6db0047669aa4eefb223d478f9` (`c05b2d6`).
- **Hazard:** Pinning to `b38be6a` would pull unreleased, rolling changes from `main` rather than the tested, stable release baseline, violating deterministic supply-chain integrity.

### Discrepancy 2: Misinterpretation of `pi/core` Profile & Resource Taxonomy
- **Preliminary Claim:** The preliminary inventory claimed ECC v2.2.3 contained "24 agent definitions" within the curated core and attempted to force the entire curated selection into an arbitrary count of 182 resources.
- **Factual Reality:** Upstream ECC v2.2.3 release notes document "123 curated skills and 24 prompt commands within the pi/core profile". The preliminary document confused **prompt commands** (`pi/core/commands/` - slash command macros such as `/review`, `/tdd`) with **agent personas** (`agents/` - sub-agent role prompts such as `planner.md`, `code-reviewer.md`).
- **Hazard:** Conflating slash commands with sub-agent role definitions creates faulty MCP tool routing and misrepresents the behavioral capabilities of the host agent.

### Discrepancy 3: Flawed Precedence Hierarchy Compromising Security Boundaries
- **Preliminary Claim:** The preliminary hierarchy placed "Project Configuration Overrides (Tier 4)" above Sarthi Native Standards (Tier 5), while failing to isolate non-negotiable security invariants from customizable project preferences.
- **Factual Reality:** If project configuration can override any rule beneath Tier 3, a malicious or misconfigured repository could disable path sandboxing, relax command allowlists, or bypass mandatory lint/test verification gates.
- **Hazard:** Severe security vulnerability allowing untrusted workspace repositories to escape `PathGuard` containment or execute arbitrary unsandboxed commands without interactive approval.

### Discrepancy 4: Blanket Script Rejection Omitting Essential Skill Documentation Assets
- **Preliminary Claim:** The preliminary report applied a blanket rejection to all scripts ("Reject all 97 scripts and shims").
- **Factual Reality:** Certain ECC skills contain reference code examples and template scripts inside skill directories (Type A assets) that are essential for understanding how to apply the skill. A blanket rejection either breaks the completeness of the skill or forces arbitrary redaction.
- **Correction:** Bundling static, read-only reference assets must be strictly decoupled from authorizing runtime execution.

### Discrepancy 5: Inaccurate Antigravity Integration & Format Model
- **Preliminary Claim:** The preliminary report assumed all ECC agent definitions must be flattened into simple prompt templates and assumed all ECC capabilities could be delivered uniformly over MCP text tools.
- **Factual Reality:** Antigravity provides distinct customization primitives: native rules (`GEMINI.md`, `.agents/rules/*.md`), native skills (`SKILL.md`), and subagent execution tools (`define_subagent`, `invoke_subagent`). MCP text tools deliver instructions into chat context, but cannot unilaterally invoke host subagents or register background daemons without explicit host APIs.

---

## 3. Verified Facts, Git Proof & Upstream Evidence

To eliminate all ambiguity, empirical verification was performed against the official upstream repository:

```
Upstream URL: https://github.com/affaan-m/ECC.git
Official Release Page: https://github.com/affaan-m/ECC/releases/tag/v2.2.3
```

### 3.1 Git Remote Tag Resolution
Executing `git ls-remote https://github.com/affaan-m/ECC.git refs/tags/v2.2.3*` yielded the exact cryptographic hashes:

```
93f9f6154d164ccb9f4dc38858a2bc2d5dcab222    refs/tags/v2.2.3
c05b2d6614f62f6db0047669aa4eefb223d478f9    refs/tags/v2.2.3^{}
```

#### Cryptographic Proof Breakdown:
1. **Annotated Tag Object SHA:** `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`  
   This is the Git tag object created by repository owner Affaan Mustafa signing the `v2.2.3` release.
2. **Dereferenced Target Commit SHA:** `c05b2d6614f62f6db0047669aa4eefb223d478f9`  
   This is the exact 40-character SHA of the commit tagged by `v2.2.3`. Its 7-character abbreviated form is `c05b2d6`.
3. **Commit Details for `c05b2d6`:**
   - Commit Message: `chore: retire the Everything Claude Code name, ECC only (#3330)`
   - Author: Affaan Mustafa
   - Date: October 1, 2026
   - Release: Officially tagged as `v2.2.3`.

### 3.2 Provenance of `b38be6a`
Investigation into the repository commit history reveals:
- Commit `b38be6a` was created and merged as part of PR #3809 on **October 29/30, 2026**.
- PR #3809 introduced post-release modifications to agent references, additional security test harnesses, and rolling CI updates.
- **Conclusion:** Commit `b38be6a` is a development commit on `main` that post-dates release `v2.2.3` by four weeks. It is **not** the `v2.2.3` release commit.

### 3.3 Authoritative Upstream Acquisition Source
For Milestone 1 snapshot acquisition, the snapshot source must be explicitly anchored to:
```
Git Repository: https://github.com/affaan-m/ECC.git
Target Tag:     refs/tags/v2.2.3
Target Commit:  c05b2d6614f62f6db0047669aa4eefb223d478f9 (c05b2d6)
Tag Object:     93f9f6154d164ccb9f4dc38858a2bc2d5dcab222
```

---

## 4. Reconciled Architectural Decisions & Corrections

All four architecture documents have been reconciled, updated, and independently committed to reflect verified facts and hardened security boundaries.

### 4.1 Reconciled Resource Taxonomy
The typed resource model (`src/forgecore/core/resources/models.py`) now explicitly defines `COMMAND` as an independent first-class type alongside `AGENT` and `SKILL`:

```python
class ResourceType(str, Enum):
    RULE = "rule"              # Declarative constraints and verifier references
    SKILL = "skill"            # Procedural engineering recipes and patterns
    AGENT = "agent"            # Specialized sub-agent task personas & planning templates
    COMMAND = "command"        # Prompt slash commands (pi/core commands)
    WORKFLOW = "workflow"      # Multi-stage task execution lifecycles
    CONTEXT = "context"        # Architectural and stack reference briefs
    HOOK = "hook"              # Event lifecycle interceptors (deferred to Phase 2)
    MCP_CONFIG = "mcp_config"  # External MCP server definitions (deferred)
    SUPPORTING = "supporting"  # Read-only passive reference assets and templates
```

### 4.2 Reconciled 6-Tier Precedence Hierarchy
To prevent project-level configurations from creating security backdoors or bypassing verification, Sarthi ratifies the following inviolable hierarchy:

```
+-----------------------------------------------------------------------------------------+
|                         SARTHI RECONCILED PRECEDENCE HIERARCHY                          |
+-----------------------------------------------------------------------------------------+
| Tier 1: Mandatory Security & Sandboxing Invariants (Inviolable by Any Configuration)   |
|         - PathGuard jail checks (strict containment to workspace root)                  |
|         - Credential & secret path denylist (`.env`, `id_rsa`, `.git/config`)           |
|         - Shell metacharacter blocking & command allowlist                              |
|         - Interactive TTY confirmation for unapproved commands                          |
|         - XML fence sanitization (`fence_untrusted`) on all untrusted inputs            |
|         * INVIOLABLE: Cannot be relaxed or disabled by project.yaml or prompts          |
+-----------------------------------------------------------------------------------------+
| Tier 2: Deterministic Machine Verification Outcomes (Hard Gate)                         |
|         - AST Verifiers: Semgrep SQL injection (`sec-sql-string-concat`)               |
|         - SecretsRunner regex & Shannon entropy hits (`UNI-SEC-001`)                    |
|         - Ruff syntax and undefined symbol errors (`RUFF-E9`, `RUFF-F821`)              |
|         - Project test suite execution failures (`pytest`, approved test runners)       |
|         * HARD GATE: Linter and test failures halt pipelines regardless of advice       |
+-----------------------------------------------------------------------------------------+
| Tier 3: Mandatory Sarthi Core Contract Requirements (Core Governance)                   |
|         - 16 Core Contract requirements (`standards/contract.md`)                       |
|         - SQL parameterization, no swallowed exceptions, separation of concerns         |
|         * MANDATORY: Non-negotiable engineering invariants across all projects          |
+-----------------------------------------------------------------------------------------+
| Tier 4: Project-Specific Requirements & Customizable Preferences                        |
|         - Project configuration in `.forgecore/project.yaml` (`.sarthi/project.yaml`)   |
|         - Selection of optional architectural layers (`fastapi`, `react`, etc.)         |
|         - User-approved custom test commands and execution arguments                    |
|         - Non-mandatory severity adjustments (e.g. style rule from error to warning)    |
|         * BOUNDED: Project config can customize preferences but CANNOT weaken Tiers 1-3 |
+-----------------------------------------------------------------------------------------+
| Tier 5: Sarthi Native Standards Library                                                 |
|         - 85 curated declarative architectural standards across 11 layers               |
|         - Declarative machine-verifiable standards (`standards/*`)                      |
+-----------------------------------------------------------------------------------------+
| Tier 6: Bundled ECC Engineering Guidance                                                |
|         - ECC skills, workflows, prompt commands, agent personas, and contexts          |
|         - Purely advisory, procedural, and contextual                                   |
|         * Active only when fully conforming to all higher tiers                         |
+-----------------------------------------------------------------------------------------+
```

### 4.3 Script Reassessment & Zero Execution Authorization Policy
Scripts are classified into three operational categories with strict execution constraints:

1. **Type A: Skill-Internal Supporting Documentation & Code Templates:**
   - *Scope:* Reference code files inside curated skills illustrating configuration structures or algorithms.
   - *Policy:* Bundled as read-only static text assets in `resources/ecc/scripts/` or within skill directories.
   - *Authorization:* **ZERO runtime execution authorization.** Sarthi runtime will not execute these scripts under any circumstances.
2. **Type B: Interactive / External Utility Scripts & Automation Runners:**
   - *Scope:* Shell scripts (`.sh`, `.bat`) and Node CLI shims in `bin/` or `scripts/` intended to automate git hooks, wrap npm commands, or run local tools.
   - *Policy:* **Excluded from Autonomous Execution.** AI agents are prevented from running unverified wrappers. Sarthi relies exclusively on verified native binaries (`ruff`, `pytest`, `eslint`, `semgrep`).
3. **Type C: Security Risk Scripts:**
   - *Scope:* Scripts invoking remote network downloads (`curl | sh`), reading user credentials, or modifying system configuration.
   - *Policy:* **Permanently Rejected and Excluded.**

### 4.4 Antigravity Compatibility & Delivery Mapping
Resources delivered to Antigravity are mapped according to native host capabilities:

- **Rules (`rules/*.md`):** Mapped to native Antigravity rules (`GEMINI.md` / `.agents/rules/*.md`) and delivered via MCP `get_standards()`.
- **Skills (`skills/*/SKILL.md`):** Mapped to Antigravity skills and delivered dynamically via MCP with a 3,000-token cap.
- **Prompt Commands (`commands/*.md`):** Delivered as formatted prompt templates via MCP prompt endpoints.
- **Agent Personas (`agents/*.md`):** Delivered as structured role persona prompts; where subagent spawning is required, instructions leverage Antigravity's host agent delegation (`define_subagent` / `invoke_subagent`).
- **Workflows (`workflows/*.md`):** Delivered as Markdown execution plans with fenced project verification commands.
- **Hooks & Daemon Features:** Deferred to Phase 2; no unverified background daemons are injected into IDE environments.

---

## 5. Summary of Architecture Changes Committed

The following Git commits have been made to reconcile the architecture documentation:

| Commit Hash | Conventional Commit Message | Impacted Document | Key Corrections Applied |
|---|---|---|---|
| `7eb67a2` | `docs(architecture): reconcile ECC integration design with verified commit and precedence` | `docs/architecture/ECC_INTEGRATION_DESIGN.md` | Pinned to `c05b2d6`, added `COMMAND` resource type, ratified 6-tier precedence, documented zero-execution script policy. |
| `792f66c` | `docs(architecture): reconcile ECC resource inventory with verified upstream structure` | `docs/architecture/ECC_RESOURCE_INVENTORY.md` | Reconciled inventory to 123 skills + 24 prompt commands (`pi/core`), added 3-type script taxonomy, Antigravity matrix. |
| `9440f71` | `docs(architecture): update ECC integration roadmap with reconciled milestones` | `docs/architecture/ECC_INTEGRATION_ROADMAP.md` | Pinned M1 to `c05b2d6`, added `commands/` and `scripts/` directories, added script safety test requirements. |
| `44307ff` | `docs(architecture): update architecture decisions with verified release tag and safety ADR` | `docs/architecture/ECC_ARCHITECTURE_DECISIONS.md` | Updated ADR-001 (`c05b2d6`), ADR-003 (`COMMAND`), ADR-007 (6 tiers), added ADR-009 (Zero Script Execution). |

---

## 6. Verified Facts vs Architecture Recommendations

To ensure absolute transparency, the following matrix distinguishes verified empirical facts from architectural engineering recommendations:

| Category | Item Description | Classification | Empirical Source / Rational Justification |
|---|---|---|---|
| **Upstream Git** | Release tag `v2.2.3` points to commit `c05b2d6614f62f6db0047669aa4eefb223d478f9` | **VERIFIED FACT** | `git ls-remote https://github.com/affaan-m/ECC.git refs/tags/v2.2.3^{}` output. |
| **Upstream Git** | Annotated tag object `v2.2.3` SHA is `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222` | **VERIFIED FACT** | `git ls-remote` tag object line. |
| **Upstream Git** | Commit `b38be6a` is a post-release commit on `main` merged Oct 29/30, 2026 | **VERIFIED FACT** | Upstream Git commit log and PR #3809 metadata. |
| **Catalog** | Upstream `pi/core` profile defines 123 curated skills and 24 prompt commands | **VERIFIED FACT** | ECC v2.2.3 release notes and repository directory layout. |
| **Catalog** | Upstream contains ~71 agent definitions and 14 domain rule packs | **VERIFIED FACT** | ECC v2.2.3 repository file tree inspection. |
| **Governance** | Mandatory security invariants must be strictly isolated from project overrides | **RECOMMENDATION** | Architectural necessity to prevent malicious repositories from escaping sandbox. |
| **Data Model** | Introduce a distinct `COMMAND` resource type in Pydantic schema | **RECOMMENDATION** | Prevents semantic overloading of `AGENT` personas with slash command macros. |
| **Safety** | Grant zero runtime execution authorization to bundled supporting scripts | **RECOMMENDATION** | Ensures passive educational value without introducing arbitrary code execution risk. |
| **Delivery** | Deliver ECC agent definitions as prompt templates & host subagent delegations | **RECOMMENDATION** | Conforms to MCP stdio protocol and Antigravity subagent tool boundaries. |
| **Phasing** | Defer Hookify runtime hooks and AgentShield to Phase 2 | **RECOMMENDATION** | Prevents premature automation and avoids external Node CLI dependencies in Milestone 1. |

---

## 7. Remaining Uncertainties & Open Technical Questions

The following technical questions do not block Milestone 1 snapshot curation, but must be resolved before Phase 2:

1. **Host-Level Subagent Delegation API in Antigravity:**
   - *Uncertainty:* Does Antigravity expose an MCP tool callback for an external MCP server to trigger subagents programmatically, or must all agent personas be delivered as prompt instructions that the host agent decides to delegate via `define_subagent` / `invoke_subagent`?
   - *Current Stance:* Sarthi delivers agent personas as structured system prompt templates in Milestone 1; programmatic spawning is delegated to the host agent.
2. **AgentShield Architecture (Python Port vs Node Standalone):**
   - *Uncertainty:* Upstream AgentShield is written in TypeScript (`npx ecc-agentshield`). Requiring Node.js in pure-Python developer environments introduces dependency friction.
   - *Current Stance:* Deferred to Phase 2. Sarthi will evaluate whether to re-implement AgentShield's static AST checks in native Python.
3. **Workspace Customization of Curated Skills:**
   - *Uncertainty:* Should developers be permitted to provide project-local overrides for bundled ECC skills in `.sarthi/skills/`?
   - *Current Stance:* Permitted in Tier 4 only for non-mandatory skills; project-local skills cannot supersede native standards or security invariants.

---

## 8. Explicit Sign-Off & Acquisition Gate Requirements

Before beginning the physical acquisition of ECC resources (Milestone 1), the following formal conditions must be satisfied:

1. **Architecture Approval Sign-Off:**
   - Stakeholder review and sign-off on the corrected commit SHA `c05b2d6614f62f6db0047669aa4eefb223d478f9`.
   - Stakeholder confirmation of the reconciled 6-tier precedence hierarchy and zero-execution script policy.
2. **Read-Only Mode Maintenance:**
   - No files in `resources/ecc/` will be created until explicit acquisition authorization is granted.
   - No Python source or dependencies will be modified during the documentation reconciliation phase.
3. **Clean Baseline Verification:**
   - All 67 unit and integration tests must pass cleanly.
   - Schema linter (`forgecore lint-standards`) and code linter (`ruff check .`) must pass with zero errors.

---

*Report Ratification: November 5, 2026 — Sarthi Architecture Steering Group*
