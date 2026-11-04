# Sarthi Architecture Decision Records (ADRs)

> **Document:** `docs/architecture/ECC_ARCHITECTURE_DECISIONS.md`  
> **Status:** Ratified Baseline Architecture  
> **Target Project:** Sarthi (evolving from ForgeCore)  
> **Author:** Principal Software Architect & Senior Python Systems Engineer  

---

## 1. Architecture Decision Records Index

| ADR ID | Decision Title | Status | Impact Area |
|---|---|---|---|
| **ADR-001** | Version-Pinned ECC Snapshot (`v2.2.3` @ `b38be6a`) over Dynamic Remote Fetch | **Accepted** | Supply Chain & Reliability |
| **ADR-002** | Dual Provider Abstraction (ECC + Sarthi Native) over Monolithic Knowledge Storage | **Accepted** | Knowledge Architecture |
| **ADR-003** | Strongly Typed Polymorphic Resource Model over Universal Rule Model Overload | **Accepted** | Data Modeling |
| **ADR-004** | Preservation of Existing 85 YAML Standards & 16-Point Core Contract | **Accepted** | Standards Governance |
| **ADR-005** | Deferral of Runtime Lifecycle Hooks & Automatic Tool Interception to Phase 2 | **Accepted** | Execution Safety |
| **ADR-006** | Preservation of `forgecore` Package Name and CLI During Milestone 1 | **Accepted** | Backward Compatibility |
| **ADR-007** | Strict Precedence Hierarchy: Security Policy > Linter Invariant > ECC Guidance | **Accepted** | Conflict Resolution |
| **ADR-008** | Offline Local Bundling in Wheel Package Data over Network Installation | **Accepted** | Air-Gapped Operation |

---

## 2. Detailed Decision Records

---

### ADR-001: Version-Pinned ECC Snapshot (`v2.2.3` @ `b38be6a`) over Dynamic Remote Fetch

#### Context
Everything Claude Code (ECC) is a rapidly evolving community project hosted on GitHub (`affaan-m/ECC`). AI coding agent environments require absolute determinism and reproducibility. If Sarthi pulled the latest ECC resources from GitHub at runtime or installation time, behavior could drift between runs, upstream breaking changes could destabilize verification, and air-gapped environments would fail.

#### Decision
We will pin our baseline to a curated local snapshot of **ECC v2.2.3**, anchored to Git commit SHA **`b38be6a`**. Resources will be bundled locally under `resources/ecc/`. Upstream updates will be incorporated only through deliberate, tested Sarthi minor releases.

#### Alternatives Considered
1. *Git Submodule:* Rejected because it requires users to have `git` installed, causes recursive clone overhead, and complicates PyPI/wheel packaging.
2. *Dynamic Runtime Download (curl/npm):* Rejected because it violates offline operation, introduces supply-chain vulnerabilities, and creates non-deterministic agent behavior.

#### Consequences
- **Positive:** Guaranteed reproducible builds; zero network dependency; complete auditability of bundled content.
- **Negative:** Upstream bug fixes and new community skills require a Sarthi release to propagate.
- **Compliance:** Full preservation of upstream MIT License and author attribution (Affaan Mustafa).

---

### ADR-002: Dual Provider Abstraction (ECC + Sarthi Native) over Monolithic Storage

#### Context
ForgeCore already possesses an established standards library (`standards/`) and workflow engine. ECC introduces over 150 skills and rules. Merging ECC directly into the existing `standards/` directory would destroy provenance, complicate future ECC snapshot upgrades, and blur the distinction between verified native rules and third-party guidance.

#### Decision
Introduce a `KnowledgeProvider` Protocol and implement two distinct providers:
1. `SarthiNativeProvider`: Owns the 85 native YAML rules, 16-point Core Contract, and deterministic verification references.
2. `ECCBundledProvider`: Owns the curated snapshot of ECC skills, rules, agent definitions, and workflows.

#### Alternatives Considered
1. *Monolithic Conversion:* Convert all ECC skills into ForgeCore YAML files in `standards/`. Rejected because skills are procedural Markdown documents, not declarative rule definitions.
2. *Complete Replacement:* Delete ForgeCore rules and use ECC exclusively. Rejected because ECC lacks Sarthi's deterministic AST verifier bindings (Ruff, Semgrep, ESLint).

#### Consequences
- **Positive:** Clean architectural decoupling; independent versioning; trivial addition of future workspace or enterprise providers.
- **Negative:** Requires an intermediate `ResourceSelector` to query and merge multiple provider catalogs.

---

### ADR-003: Strongly Typed Polymorphic Resource Model over Universal Rule Model Overload

#### Context
ForgeCore models all knowledge using `forgecore.core.models.Rule`. While suitable for single-line assertions (`id`, `rule`, `good`, `bad`), forcing procedural skills, multi-stage agent workflows, and sub-agent personas into `Rule` would require abusing optional fields or serializing complex structures into string blobs.

#### Decision
Create a typed `EngineeringResource` model with an explicit `ResourceType` enum: `RULE`, `SKILL`, `AGENT`, `WORKFLOW`, `CONTEXT`, `HOOK`, `MCP_CONFIG`, `SUPPORTING`. Legacy `Rule` instances are mapped cleanly into `EngineeringResource(type=ResourceType.RULE)` by the native provider.

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

### ADR-007: Strict Precedence Hierarchy: Security Policy > Linter Invariant > ECC Guidance

#### Context
When an AI agent receives both strict AST rules and flexible conversational skills, contradictions can arise. For example, an ECC skill might suggest an inline database query for rapid prototyping, while Sarthi native rule `FAPI-ARCH-001` forbids direct database queries in route handlers.

#### Decision
Enforce an inviolable precedence hierarchy:
1. **Core Security & Sandboxing** (`PathGuard`, allowlist, approvals) cannot be overridden by any resource.
2. **Deterministic Verifier Failures** (`Semgrep`, `Ruff`, `ESLint`, `TestRunner`) hard-fail builds regardless of natural-language guidance.
3. **Core Contract & Native Rules** supersede ECC conversational skills in the event of direct conflict.
4. **ECC Skills** provide implementation guidance *within* the boundary established by higher tiers.

#### Consequences
- **Positive:** Unambiguous resolution of conflicting instructions; safety invariants are strictly maintained.
- **Negative:** Agents cannot use certain shortcut patterns suggested in community skills if they violate native gates.

---

### ADR-008: Offline Local Bundling in Package Distribution over Network Installation

#### Context
Enterprise and secure developer environments frequently operate in air-gapped or restricted-network setups where accessing GitHub or external npm registries is forbidden or monitored.

#### Decision
Selected ECC resources (rules, skills, agent templates, workflows) will be packaged directly within the Python distribution package under `resources/ecc/`. `pyproject.toml` will include these files in package data.

#### Consequences
- **Positive:** Complete offline capability; instantaneous resource discovery without HTTP latency.
- **Negative:** Distribution wheel size increases by approximately 1.5MB to 2.5MB.

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

