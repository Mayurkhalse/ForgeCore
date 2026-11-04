# Sarthi Architecture Decision Records (ADRs)

> **Document:** `docs/architecture/ECC_ARCHITECTURE_DECISIONS.md`  
> **Status:** Ratified Baseline Architecture (Reconciled)  
> **Target Project:** Sarthi (evolving from ForgeCore)  
> **Upstream Release Baseline:** ECC v2.2.3  
> **Authoritative Commit SHA:** `c05b2d6614f62f6db0047669aa4eefb223d478f9` (abbreviated `c05b2d6`)  
> **Release Tag Object SHA:** `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`  
> **Author:** Principal Software Architect & Senior Python Systems Engineer  

---

## 1. Architecture Decision Records Index

| ADR ID | Decision Title | Status | Impact Area |
|---|---|---|---|
| **ADR-001** | Version-Pinned ECC Snapshot (`v2.2.3` @ `c05b2d6`) over Dynamic Remote Fetch | **Accepted** | Supply Chain & Reliability |
| **ADR-002** | Dual Provider Abstraction (ECC + Sarthi Native) over Monolithic Knowledge Storage | **Accepted** | Knowledge Architecture |
| **ADR-003** | Strongly Typed Polymorphic Resource Model (including `COMMAND`) over Universal Rule Model Overload | **Accepted** | Data Modeling |
| **ADR-004** | Preservation of Existing 85 YAML Standards & 16-Point Core Contract | **Accepted** | Standards Governance |
| **ADR-005** | Deferral of Runtime Lifecycle Hooks & Automatic Tool Interception to Phase 2 | **Accepted** | Execution Safety |
| **ADR-006** | Preservation of `forgecore` Package Name and CLI During Milestone 1 | **Accepted** | Backward Compatibility |
| **ADR-007** | Reconciled 6-Tier Precedence Hierarchy: Security Invariants > Verifier > Contract > Config > Standards > ECC | **Accepted** | Conflict Resolution |
| **ADR-008** | Offline Local Bundling in Wheel Package Data over Network Installation | **Accepted** | Air-Gapped Operation |
| **ADR-009** | Read-Only Script Asset Bundling with Zero Execution Authorization | **Accepted** | Execution Safety & Sandboxing |

---

## 2. Detailed Decision Records

---

### ADR-001: Version-Pinned ECC Snapshot (`v2.2.3` @ `c05b2d6`) over Dynamic Remote Fetch

#### Context
Everything Claude Code (ECC) is a rapidly evolving community project hosted on GitHub (`affaan-m/ECC`). AI coding agent environments require absolute determinism and reproducibility. If Sarthi pulled the latest ECC resources from GitHub at runtime or installation time, behavior could drift between runs, upstream breaking changes could destabilize verification, and air-gapped environments would fail.

A preliminary report proposed commit `b38be6a` as the v2.2.3 anchor. Investigation into the Git history revealed that `b38be6a` is a post-release commit on `main` (PR #3809, merged October 29/30, 2026), whereas the official release tag `v2.2.3` resolves definitively to commit `c05b2d6614f62f6db0047669aa4eefb223d478f9` (tag object `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`, commit message: `chore: retire the Everything Claude Code name, ECC only (#3330)`).

#### Decision
We will pin our baseline strictly to the verified official release commit of **ECC v2.2.3**, anchored to Git commit SHA **`c05b2d6614f62f6db0047669aa4eefb223d478f9`** (abbreviated `c05b2d6`). Resources will be bundled locally under `resources/ecc/`. Upstream updates will be incorporated only through deliberate, tested Sarthi minor releases.

#### Alternatives Considered
1. *Git Submodule:* Rejected because it requires users to have `git` installed, causes recursive clone overhead, and complicates PyPI/wheel packaging.
2. *Dynamic Runtime Download (curl/npm):* Rejected because it violates offline operation, introduces supply-chain vulnerabilities, and creates non-deterministic agent behavior.
3. *Ad-Hoc Commit `b38be6a`:* Rejected because it does not correspond to an official release tag and incorporates unverified rolling changes from late October 2026.

#### Consequences
- **Positive:** Guaranteed reproducible builds; zero network dependency; complete auditability of bundled content anchored to the official release.
- **Negative:** Upstream bug fixes and new community skills require a Sarthi release to propagate.
- **Compliance:** Full preservation of upstream MIT License and author attribution (Affaan Mustafa).

---

### ADR-002: Dual Provider Abstraction (ECC + Sarthi Native) over Monolithic Storage

#### Context
ForgeCore already possesses an established standards library (`standards/`) and workflow engine. ECC introduces over 150 skills and rules. Merging ECC directly into the existing `standards/` directory would destroy provenance, complicate future ECC snapshot upgrades, and blur the distinction between verified native rules and third-party guidance.

#### Decision
Introduce a `KnowledgeProvider` Protocol and implement two distinct providers:
1. `SarthiNativeProvider`: Owns the 85 native YAML rules, 16-point Core Contract, and deterministic verification references.
2. `ECCBundledProvider`: Owns the curated snapshot of ECC skills, rules, prompt commands, agent definitions, and workflows.

#### Alternatives Considered
1. *Monolithic Conversion:* Convert all ECC skills into ForgeCore YAML files in `standards/`. Rejected because skills are procedural Markdown documents, not declarative rule definitions.
2. *Complete Replacement:* Delete ForgeCore rules and use ECC exclusively. Rejected because ECC lacks Sarthi's deterministic AST verifier bindings (Ruff, Semgrep, ESLint).

#### Consequences
- **Positive:** Clean architectural decoupling; independent versioning; trivial addition of future workspace or enterprise providers.
- **Negative:** Requires an intermediate `ResourceSelector` to query and merge multiple provider catalogs.

---

### ADR-003: Strongly Typed Polymorphic Resource Model (including `COMMAND`) over Universal Rule Model Overload

#### Context
ForgeCore models all knowledge using `forgecore.core.models.Rule`. While suitable for single-line assertions (`id`, `rule`, `good`, `bad`), forcing procedural skills, prompt commands, multi-stage agent workflows, and sub-agent personas into `Rule` would require abusing optional fields or serializing complex structures into string blobs. Furthermore, the preliminary architecture conflated prompt commands with agent definitions.

#### Decision
Create a typed `EngineeringResource` model with an explicit `ResourceType` enum: `RULE`, `SKILL`, `AGENT`, `COMMAND`, `WORKFLOW`, `CONTEXT`, `HOOK`, `MCP_CONFIG`, `SUPPORTING`.
- `COMMAND`: Represents prompt slash command templates (e.g. `pi/core/commands/review.md`).
- `AGENT`: Represents specialized role personas and planning templates (e.g. `agents/planner.md`).
Legacy `Rule` instances are mapped cleanly into `EngineeringResource(type=ResourceType.RULE)` by the native provider.

#### Alternatives Considered
1. *Keep `Rule` Unchanged:* Overload `Rule.rule` with 10KB of Markdown skill text. Rejected due to token budgeting inaccuracies and schema pollution.
2. *Multiple Unrelated Classes:* Create completely separate classes for every type without a common base. Rejected because unified indexing, filtering, and budgeting require common metadata (ID, provider, applicable stacks).

#### Consequences
- **Positive:** Type-safe resource manipulation; accurate metadata indexing; clear semantics for agents.
- **Negative:** New schemas in `src/forgecore/core/resources/models.py` must be maintained alongside legacy models during transition.

---

### ADR-004: Preservation of Existing 85 YAML Standards & 16-Point Core Contract

#### Context
ForgeCore's 85 standards have been rigorously verified through schema linting (`lint-standards`), test suites (67 passing tests), and AST verifier bindings. Discarding them in favor of unverified ECC markdown would cause an immediate regression in verification rigor.

#### Decision
The 85 standards and the 16-point Core Contract remain completely intact in their original locations (`standards/`). They form the foundational baseline of Sarthi's `NativeProvider`.

#### Consequences
- **Positive:** Zero regressions; 100% test pass rate preserved; machine verifiers remain fully functional.
- **Neutral:** Sarthi carries both native standards and ECC skills in parallel, requiring conflict resolution.

---

### ADR-005: Deferral of Runtime Lifecycle Hooks & Automatic Tool Interception to Phase 2

#### Context
ECC provides "Hookify" rules that intercept command execution (e.g. bash commands, file modifications). While attractive, implementing lifecycle hooks requires deep hooks into IDE processes or background daemons. Antigravity's lifecycle hook integration (`hooks.json`) has not been validated in code, and Claude Code hooks require external shell shims.

#### Decision
Defer all automated lifecycle hooks, tool interception, and background daemon execution to Phase 2. Milestone 1 will focus strictly on resource discovery, selection, token budgeting, and MCP tool delivery.

#### Alternatives Considered
1. *Immediate Antigravity Hook Scaffolding:* Attempt to write `~/.gemini/config/hooks.json` in Milestone 1. Rejected because unverified hooks can hijack user terminal sessions or cause tool deadlocks.

#### Consequences
- **Positive:** Safe, non-invasive integration; zero risk of corrupting IDE workflows.
- **Negative:** Agents must continue calling `verify_project` explicitly rather than having verification triggered automatically on tool exit.

---

### ADR-006: Preservation of `forgecore` Package Name and CLI During Milestone 1

#### Context
Renaming the package from `forgecore` to `sarthi` touches 74 files, 612 identifiers, persistent config directories (`.forgecore/`), and approvals (`~/.forgecore/approvals.json`). Attempting to rename the package simultaneously with the ECC integration would create an unmaintainable diff and high risk of regressions.

#### Decision
All changes in Milestone 1 will retain the package name `forgecore`, CLI command `forgecore`, and existing config paths. The formal namespace rename to `sarthi` is scheduled as a dedicated, independent milestone.

#### Consequences
- **Positive:** Isolates knowledge integration from namespace refactoring; existing approval records remain valid.
- **Negative:** Codebase temporarily bears the legacy name while implementing Sarthi architecture.

---

### ADR-007: Reconciled 6-Tier Precedence Hierarchy: Security Invariants > Verifier > Contract > Config > Standards > ECC

#### Context
The preliminary precedence model placed project configuration above native standards, creating a potential loophole where project configuration could relax security sandboxing or skip mandatory verifications. Furthermore, clear boundaries were needed between mandatory invariants and customizable preferences.

#### Decision
Ratify the reconciled 6-tier precedence hierarchy:
1. **Tier 1: Mandatory Security & Sandboxing Invariants (Inviolable):** `PathGuard` workspace containment, credential denylist, command allowlist, mandatory interactive TTY approval for command trust, and untrusted XML fence sanitization. CANNOT be overridden or disabled by project config, rules, or prompts.
2. **Tier 2: Deterministic Machine Verification Outcomes (Hard Gate):** AST verifiers (Semgrep SQL injection), secret scanners, Ruff errors, and test suite execution failures halt workflows unconditionally. Natural language advice never supersedes static checks.
3. **Tier 3: Mandatory Sarthi Core Contract Requirements:** 16 non-negotiable core engineering rules in `standards/contract.md`.
4. **Tier 4: Project-Specific Requirements & Customizable Preferences:** Workspace configuration in `.forgecore/project.yaml` (optional layer activation, approved test runners, non-mandatory severity customization). Strictly bounded: project config cannot weaken Tiers 1-3.
5. **Tier 5: Sarthi Native Standards Library:** 85 declarative architectural standards across 11 layers.
6. **Tier 6: Bundled ECC Engineering Guidance:** Procedural skills, workflows, prompt commands, agent personas, and contexts. Advisory only.

#### Consequences
- **Positive:** Inviolable security boundary; project configuration cannot introduce vulnerabilities; unambiguous resolution of conflicting instructions.
- **Negative:** Project owners cannot suppress Tier 1 security checks or Tier 3 contract invariants.

---

### ADR-008: Offline Local Bundling in Wheel Package Data over Network Installation

#### Context
Enterprise and secure developer environments frequently operate in air-gapped or restricted-network setups where accessing GitHub or external npm registries is forbidden or monitored.

#### Decision
Selected ECC resources (rules, skills, prompt commands, agent templates, workflows, contexts) will be packaged directly within the Python distribution package under `resources/ecc/`. `pyproject.toml` will include these files in package data.

#### Consequences
- **Positive:** Complete offline capability; instantaneous resource discovery without HTTP latency.
- **Negative:** Distribution wheel size increases by approximately 1.5MB to 2.5MB.

---

### ADR-009: Read-Only Script Asset Bundling with Zero Execution Authorization

#### Context
ECC includes auxiliary scripts within skills and utility directories. A preliminary recommendation advocated for a blanket rejection of all scripts. However, certain skills rely on reference code templates (e.g. Python algorithm examples or configuration templates) to be fully comprehensible. Conversely, allowing an AI agent or MCP server to autonomously execute third-party shell scripts or shims represents an unacceptable security risk.

#### Decision
Adopt a strict tripartite classification:
1. **Type A (Skill-Internal Reference Code & Documentation Assets):** Bundled into `resources/ecc/scripts/` or skill directories strictly as passive, read-only text files. **Sarthi runtime grants ZERO execution authorization to these assets.**
2. **Type B (Executable Utilities & CLI Shims):** Standalone shell scripts and shims in `bin/` or `scripts/` are excluded from autonomous execution. Verification relies exclusively on verified, allowlisted native binaries (`ruff`, `pytest`, `eslint`, `semgrep`).
3. **Type C (Security Risk Scripts):** Any script that performs remote downloads, accesses credentials, or modifies system state is permanently rejected and excluded.

#### Consequences
- **Positive:** Preserves the educational and illustrative value of skills while maintaining absolute runtime execution safety.
- **Negative:** Developers must manually review reference code examples rather than executing them via one-click automation.

---

## 3. Unresolved Architecture Questions (Requiring Stakeholder Input)

The following architectural questions are cataloged for resolution prior to Phase 2:

1. **Host-Level Subagent Delegation:**
   - *Question:* Does Antigravity expose a native API for MCP servers to trigger subagents directly, or must ECC agent personas be delivered exclusively as prompt templates in chat context?
2. **Approvals Storage Path Migration:**
   - *Question:* When the formal rename occurs, should Sarthi automatically copy existing approval hashes from `~/.forgecore/approvals.json` to `~/.sarthi/approvals.json`, or prompt the user once for bulk re-approval?
3. **AgentShield Integration Runtime:**
   - *Question:* Should AgentShield be bundled as a compiled Node standalone executable, or should its static checks be re-implemented in native Python to avoid requiring Node.js in pure-Python environments?
4. **User-Customized ECC Skills:**
   - *Question:* Should developers be allowed to override bundled ECC skills by placing modified markdown files in `.sarthi/skills/` within their project workspace?
