# ECC Resource Inventory & Compatibility Evaluation

> **Document:** `docs/architecture/ECC_RESOURCE_INVENTORY.md`  
> **Status:** Baseline Resource Audit  
> **Target Baseline:** Everything Claude Code (ECC) v2.2.3  
> **Anchor Commit SHA:** `b38be6a`  
> **Upstream Repository:** `https://github.com/affaan-m/ECC`  
> **Upstream Author:** Affaan Mustafa  
> **License:** MIT License  

---

## 1. Executive Summary

This document establishes the comprehensive technical inventory and integration classification of resources in **Everything Claude Code (ECC) v2.2.3**.

ECC v2.2.3 represents a massive, community-driven collection of AI coding agent harnesses. However, **not all ECC resources can or should be integrated into Sarthi**. Sarthi's architectural mandate requires strict deterministic verification, offline bundling, and client safety. Therefore, every resource category in ECC is evaluated and assigned an explicit integration decision:

- **BUNDLE & DELIVER:** Bundled locally into `resources/ecc/` and exposed via MCP tools.
- **ADAPT:** Ingested and transformed to conform to Sarthi schemas and IDE constraints.
- **DEFER:** Excluded from Milestone 1; cataloged for future phased integration.
- **REJECT:** Excluded permanently due to security risks or architectural incompatibility.

---

## 2. Upstream Snapshot Provenance & Metadata

- **Upstream Repository:** `https://github.com/affaan-m/ECC` (formerly `affaan-m/everything-claude-code`)
- **Release Version:** `v2.2.3` (Release Date: October 1, 2026)
- **Authoritative Commit SHA:** `b38be6a` (anchored Git revision)
- **Upstream Release Focus:** Standardized project branding on ECC, hardened release CI/CD verification against npm registries, stabilized profile configurations, and unified skill metadata.
- **Total Catalog Size:** ~71 agent definitions, 311 skills (123 curated core skills), 14 domain rule packs, 97 command shims, and Hookify event rules.
- **License Terms:** MIT License (requires preservation of original copyright notice in all bundled distributions).

---

## 3. High-Level Category Evaluation Matrix

| Resource Category | Total Count (v2.2.3) | Primary Purpose | Initial Integration Decision | Host Target Support | Key Constraints & Dependencies |
|---|---|---|---|---|---|
| **Rules** | 14 rule packs | Domain and language coding standards | **BUNDLE & DELIVER** | IDE-Agnostic | Markdown/YAML frontmatter; mapped to Sarthi `RULE` type. |
| **Skills** | 311 total (123 core) | Procedural engineering guides & recipes | **BUNDLE & DELIVER** | IDE-Agnostic | Pure text instructions; requires token-budget capping (<3k tokens). |
| **Agents** | 71 definitions | Specialized sub-agent task personas | **ADAPT & DELIVER** | Antigravity / Claude Code | Ingested as persona prompt templates; execution delegated to host. |
| **Workflows** | 8 core workflows | Multi-stage task lifecycle processes | **ADAPT & DELIVER** | IDE-Agnostic | Replaces/augments Jinja2 templates; must fence project commands. |
| **Contexts** | 12 context briefs | Project & architectural knowledge briefs | **BUNDLE & DELIVER** | IDE-Agnostic | Delivered as reference resources (`sarthi://context/...`). |
| **Hooks (Hookify)** | 24 hook rules | Runtime event interception (bash, edits) | **DEFER (Phase 2)** | Host-Dependent (Node/CLI) | Requires active execution daemon; deferred to avoid premature automation. |
| **AgentShield** | 1 security suite | Agent configuration & permission auditor | **DEFER (Phase 2)** | External Tool / CI | Requires Node runtime; scheduled as verification runner in Phase 2. |
| **Scripts & Shims** | 97 command shims | Local CLI wrappers & package shims | **REJECT** | Host-Specific | Security hazard. Sarthi forbids executing untrusted third-party scripts. |
| **MCP Configs** | 16 server configs | External API connectors | **DEFER** | IDE-Dependent | Connects to external services; outside core engineering standards scope. |

---

## 4. Detailed Component Inventory & Curation

### 4.1 Selected Resources: Rules (Core Coding Standards)
ECC rules provide clean, domain-specific coding guidelines that directly augment Sarthi's declarative standards:

| Resource ID | Origin Path in ECC | Target Domain | Integration Strategy | Technical Justification |
|---|---|---|---|---|
| `ecc.rule.typescript` | `rules/typescript.md` | TypeScript / Node | **Bundle** | Standardizes strict typing, error handling, and modern ES syntax. |
| `ecc.rule.python` | `rules/python.md` | Python Ecosystem | **Bundle** | Enforces PEP 8, typing annotations, and async discipline. |
| `ecc.rule.react` | `rules/react.md` | React / Next.js | **Bundle** | Enforces component isolation, hook discipline, and SSR safety. |
| `ecc.rule.fastapi` | `rules/fastapi.md` | FastAPI Web APIs | **Bundle** | Complements Sarthi's `fastapi` layer with dependency injection patterns. |
| `ecc.rule.security` | `rules/security.md` | OWASP / Security | **Bundle** | Reinforces input sanitization, CSRF, and secret handling. |
| `ecc.rule.git` | `rules/git.md` | Version Control | **Bundle** | Standardizes Conventional Commits and clean PR discipline. |
| `ecc.rule.testing` | `rules/testing.md` | Automated Testing | **Bundle** | Mandates unit, integration, and property-based test patterns. |
| `ecc.rule.database` | `rules/database.md` | SQL / Migrations | **Bundle** | Enforces schema migration discipline and indexing rules. |

### 4.2 Selected Resources: Skills (Procedural Engineering Guides)
Skills represent the highest-value component of ECC. In Milestone 1, Sarthi bundles the **123 curated core skills** (`ecc-pi-core` profile):

| Domain Cluster | Key Skills Included | Delivery Mechanism | Token Impact & Budgeting |
|---|---|---|---|
| **Test-Driven Development (TDD)** | `tdd-workflow`, `pytest-patterns`, `jest-vitest-recipes`, `mocking-strategies` | `get_standards()` / `get_workflow()` | Ingested on demand; truncated if combined size exceeds 3,000 tokens. |
| **API Architecture** | `rest-api-design`, `fastapi-advanced`, `pydantic-v2-patterns`, `graphql-schema` | `get_standards()` | Selected when `api-design` or `fastapi` layers are active. |
| **Frontend Engineering** | `react-state-management`, `react-performance`, `tailwind-styling`, `a11y-audit` | `get_standards()` | Selected when `react` or `react-native` layers are active. |
| **Backend & Cloud** | `docker-best-practices`, `postgresql-optimization`, `redis-caching`, `jwt-auth` | `get_standards()` | Selected based on task keyword matching. |
| **Refactoring & Clean Code** | `legacy-refactoring`, `code-smells-remediation`, `solid-principles` | `get_workflow(task_type="refactor")` | Automatically attached to refactoring task lifecycles. |

### 4.3 Selected Resources: Specialized Agent Personas
ECC includes 71 specialized agent definitions. Sarthi indexes and delivers these definitions as **role-based planning templates**:

| Agent ID | Role / Specialization | Antigravity Host Mapping | Delivery Mechanism |
|---|---|---|---|
| `ecc.agent.planner` | Architecture & Feature Planning | Maps to Session Planning Phase | Delivered via `get_workflow(task_type="feature")` |
| `ecc.agent.code-reviewer` | Code Review & Audit | Maps to Pre-Verification Phase | Delivered via `get_workflow()` check phase |
| `ecc.agent.security-auditor` | Vulnerability & Permission Audit | Maps to Security Layer | Delivered when security-critical tasks are active |
| `ecc.agent.test-lead` | Test Suite Design & Edge Cases | Maps to Testing Layer | Delivered when test generation is requested |
| `ecc.agent.build-repair` | Diagnostic & Error Recovery | Maps to Verification Remediation | Delivered when `verify_project` reports failures |

*Architectural Caveat:* Sarthi **cannot** autonomously spawn child processes or subagents inside Antigravity unless the host IDE supports subagent delegation. These agent definitions are delivered as **system prompts and structured instructions** for the host agent to execute.

### 4.4 Selected Resources: Workflows
ECC multi-stage workflows are adapted to replace Sarthi's static Jinja2 templates:
- **`feature-flow`:** Plan -> Interface Contract -> Test Scaffold -> Implement -> Verify -> Document.
- **`bugfix-flow`:** Failing Reproduction Test -> Root Cause Analysis -> Atomic Patch -> Regression Verification.
- **`refactor-flow`:** Invariant Test Baseline -> Incremental Decoupling -> Verification Loop.

---

## 5. Deferred & Rejected Resources

### 5.1 Deferred to Phase 2 (Runtime & Tooling Dependencies)
1. **Hookify Lifecycle Hooks (`hooks/`):**
   - *Reason for Deferral:* Hooks require a continuously running Node runtime or native IDE interception hook (e.g. Antigravity `hooks.json` or Claude Code shell shims). Sarthi Milestone 1 focuses strictly on deterministic verification and resource delivery over MCP. Hooks will be integrated in Phase 2 once IDE lifecycle events are validated.
2. **AgentShield Security Scanner:**
   - *Reason for Deferral:* AgentShield is an external TypeScript/Node CLI (`npx ecc-agentshield`). Sarthi's core verification engine is Python-native. In Phase 2, AgentShield will be evaluated as an optional runner alongside ESLint and Ruff.
3. **External MCP Configurations (`mcp/`):**
   - *Reason for Deferral:* ECC's MCP configs connect to external SaaS APIs (Linear, GitHub, Figma, PostgreSQL). Sarthi's primary purpose is local codebase guardrails. External MCP connectors are outside the core standards scope.

### 5.2 Rejected Resources (Permanent Security Exclusion)
1. **Shell Scripts & Shims (`bin/`, `scripts/`):**
   - *Reason for Rejection:* ECC contains 97 shell shims and Node utility scripts. Executing unverified third-party shell scripts inside the user's project violates Sarthi's core security model (`PathGuard` and executable allowlist). All automation within Sarthi must execute verified native binaries (`ruff`, `pytest`, `eslint`, `semgrep`).
2. **Unsandboxed Memory State (`.claude/memory/`):**
   - *Reason for Rejection:* Dynamic prompt memory files are treated as untrusted project data. They are never ingested as executable policy or allowed to bypass verification gates.

---

## 6. Licensing & Attribution Strategy

ECC is licensed under the **MIT License** by Affaan Mustafa. Because Sarthi bundles a snapshot of ECC resources, strict compliance with the MIT License is mandatory.

### 6.1 Licensing Implementation Plan
1. **Bundled License Preservation:** The upstream `LICENSE` file is copied verbatim to `resources/ecc/LICENSE`.
2. **Attribution in `NOTICE`:** The repository's root `NOTICE` file is updated with explicit attribution:
   ```
   This product includes software developed as part of Everything Claude Code (ECC)
   by Affaan Mustafa (https://github.com/affaan-m/ECC).
   Licensed under the MIT License.
   Bundled Snapshot: v2.2.3 (Commit b38be6a)
   ```
3. **Header Preservation:** Any ECC rule, skill, or workflow containing original author attribution or copyright comments retains those comments without modification.
4. **Independent Authorship Distinction:** All Sarthi core code (`src/forgecore/`), verification runners, `PathGuard`, and native standards (`standards/`) remain independently authored by the Sarthi / ForgeCore development team.

---

## 7. Resource Ingestion Summary

```
+-----------------------------------------------------------------------------------------+
|                              ECC SNAPSHOT INGESTION SUMMARY                             |
+-----------------------------------------------------------------------------------------+
| Total ECC Resources Evaluated:                           436 artifacts                  |
| --------------------------------------------------------------------------------------- |
| - Bundled & Delivered (Core Skills, Rules, Workflows):    158 artifacts (36%)            |
| - Adapted for MCP Delivery (Agent Persona Prompts):       24 artifacts (5%)             |
| - Deferred to Phase 2 (Hooks, AgentShield, MCP configs):  48 artifacts (11%)            |
| - Rejected (Scripts, Shims, Memory State):               206 artifacts (48%)            |
+-----------------------------------------------------------------------------------------+
```

