# Everything Claude Code (ECC) Capability Traceability Matrix

> **Document:** `docs/architecture/ECC_CAPABILITY_TRACEABILITY_MATRIX.md`  
> **Upstream Release Baseline:** ECC v2.2.3  
> **Authoritative Commit SHA:** `c05b2d6614f62f6db0047669aa4eefb223d478f9` (abbreviated `c05b2d6`)  
> **Release Tag Object SHA:** `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`  
> **License:** MIT (Affaan Mustafa)  
> **Status:** Ratified Traceability Baseline  

---

## 1. Executive Summary & Inventory Arithmetic

This document establishes the exhaustive machine-readable capability traceability matrix for all 962 evaluated upstream entries from Everything Claude Code (ECC) v2.2.3.

| Metric | Count | Percentage |
|---|---|---|
| **Total Upstream Files Evaluated** | 962 | 100.0% |
| **Included Physical Files** | 391 | 40.64% |
| **Deferred Entries (Cataloged as Inactive)** | 248 | 25.78% |
| **Rejected Entries (Build Artifacts / Node Modules)** | 323 | 33.58% |

### Decision Breakdown by Resource Type

| Resource Type | Total Evaluated | Included | Deferred | Rejected |
|---|---|---|---|---|
| `agent` | 68 | 68 | 0 | 0 |
| `command` | 94 | 24 | 70 | 0 |
| `context` | 3 | 3 | 0 | 0 |
| `hook` | 6 | 0 | 6 | 0 |
| `mcp_config` | 1 | 0 | 1 | 0 |
| `rule` | 122 | 122 | 0 | 0 |
| `skill` | 296 | 125 | 171 | 0 |
| `supporting` | 370 | 47 | 0 | 323 |
| `workflow` | 2 | 2 | 0 | 0 |

---

## 2. Six-Tier Classification Schema

Every discovered upstream asset is assigned exactly one classification:

1. **Directly Reusable (`directly_reusable`):** Markdown rules, contexts, and clean skills that execute natively via standard LLM text prompt injection.
2. **Requires Normalization (`requires_normalization`):** Items with non-standard YAML frontmatter or directory layouts normalized into typed `EngineeringResource` schemas.
3. **Requires an IDE/Provider Adapter (`requires_adapter`):** Interactive slash commands and agent persona templates requiring adapter translation for non-Claude hosts (e.g. Antigravity IDE, Cursor).
4. **Requires Unsupported Runtime Capability (`requires_unsupported_capability`):** Multi-agent JavaScript workflow scripts or background lifecycle hooks requiring deep IDE daemon hooks or Claude Code workflow runtimes.
5. **Documentation/Reference Only (`documentation_only`):** Passive reference scripts and auxiliary documentation assets governed by ADR-009 (ZERO runtime execution authorization).
6. **Excluded (`excluded`):** Unverified third-party binaries, vendor node_modules, and transient build artifacts.

---

## 3. Capability Traceability Matrix by Category

### 3.53 `RULE` Capabilities (122 items)

> **Purpose:** Coding standards, lint directives, and architectural invariants across 23 language/framework domains.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `rules/README.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/angular/coding-style.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/angular/hooks.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/angular/patterns.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/angular/security.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/angular/testing.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/arkts/coding-style.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/arkts/hooks.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/arkts/patterns.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/arkts/security.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/arkts/testing.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/agents.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/code-review.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/coding-style.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/development-workflow.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/git-workflow.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/hooks.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/patterns.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/performance.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/common/security.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| *... (97 additional `rule` items cataloged in inventory.json) ...* | — | — | — | — | — |
| `rules/web/hooks.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/web/patterns.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/web/performance.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/web/security.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `rules/web/testing.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |

### 3.86 `SKILL` Capabilities (296 items)

> **Purpose:** Procedural recipes, domain workflows, and actionable guidelines for complex development tasks.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `pi/core/skills/accessibility/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-architecture-audit/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-eval/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-harness-construction/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-introspection-debugging/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-self-evaluation/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agent-self-evaluation/templates/evaluation-report.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/agentic-engineering/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/ai-first-engineering/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/android-clean-architecture/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/angular-developer/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/api-connector-builder/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/api-design/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/architecture-decision-records/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/backend-patterns/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/benchmark/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/benchmark-optimization-loop/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/blueprint/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/bun-runtime/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| `pi/core/skills/click-path-audit/SKILL.md` | `include` | Directly Reusable | Native (Procedural MD) | **Connected** (`ECCBundledProvider`) | E2E Workflow Test |
| *... (271 additional `skill` items cataloged in inventory.json) ...* | — | — | — | — | — |
| `skills/videodb` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `skills/visa-doc-translate` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `skills/windows-desktop-e2e` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `skills/workspace-surface-audit` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `skills/x-api` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |

### 3.119 `AGENT` Capabilities (68 items)

> **Purpose:** Role persona prompts and specialized sub-agent task definitions.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `agents/a11y-architect.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/agent-evaluator.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/architect.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/build-error-resolver.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/chief-of-staff.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/code-architect.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/code-explorer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/code-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/code-simplifier.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/comment-analyzer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/conversation-analyzer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/cpp-build-resolver.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/cpp-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/csharp-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/dart-build-resolver.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/database-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/django-build-resolver.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/django-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/doc-updater.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/docs-lookup.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| *... (43 additional `agent` items cataloged in inventory.json) ...* | — | — | — | — | — |
| `agents/swift-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/tdd-guide.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/type-design-analyzer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/typescript-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `agents/vue-reviewer.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |

### 3.152 `COMMAND` Capabilities (94 items)

> **Purpose:** Slash command prompt templates and instruction macros.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `pi/core/commands/aside.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/build-fix.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/code-review.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/cpp-test.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/fastapi-review.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/feature-dev.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/flutter-test.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/go-test.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/gradle-build.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/kotlin-test.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/plan-prd.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/plan.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/pr.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/prp-commit.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/prp-implement.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/prp-plan.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/prp-pr.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/prp-prd.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/react-test.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| `pi/core/commands/refactor-clean.md` | `include` | Requires Adapter | Adapted (Sarthi Prompt Adapter) | **Connected** (`ECCBundledProvider`) | Host Adapter Test |
| *... (69 additional `command` items cataloged in inventory.json) ...* | — | — | — | — | — |
| `commands/sessions.md` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `commands/setup-pm.md` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `commands/skill-create.md` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `commands/skill-health.md` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |
| `commands/vue-review.md` | `defer` | Requires Adapter | Non-Core Upstream | Cataloged (Deferred Index) | Inventory Trace Test |

### 3.185 `WORKFLOW` Capabilities (2 items)

> **Purpose:** Multi-phase execution lifecycles and background multi-agent orchestrations.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `workflows/README.md` | `include` | Requires Adapter | Adapted | **Cataloged** (Metadata Only) | Lifecycle Validation |
| `workflows/orch-review.workflow.js` | `include` | Requires Unsupported Capability | Host Dependent (Claude Workflow) | **Cataloged** (Metadata Only) | Lifecycle Validation |

### 3.194 `CONTEXT` Capabilities (3 items)

> **Purpose:** Architectural summaries, domain glossaries, and project background briefs.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `contexts/dev.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `contexts/research.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |
| `contexts/review.md` | `include` | Directly Reusable | Native (Markdown) | **Connected** (`ECCBundledProvider`) | Unit / Selection Test |

### 3.204 `HOOK` Capabilities (6 items)

> **Purpose:** Event-driven lifecycle interceptors (e.g. PostToolUse hooks).

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `hooks/codex-hooks.json` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |
| `hooks/hooks.json` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |
| `hooks/hooks.metadata.json` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |
| `hooks/README.md` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |
| `hooks/memory-persistence/hooks.json` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |
| `hooks/memory-persistence/README.md` | `defer` | Requires Unsupported Capability | Host Dependent (Shell Hooks) | Deferred to Phase 2 (ADR-005) | Deferred Catalog Test |

### 3.217 `MCP_CONFIG` Capabilities (1 items)

> **Purpose:** Declarations of external tool services and server shims.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `mcp-configs/mcp-servers.json` | `defer` | Requires Unsupported Capability | External SaaS MCP | Deferred (Out of Boundary) | Security Policy Test |

### 3.225 `SUPPORTING` Capabilities (370 items)

> **Purpose:** Auxiliary templates, passive reference scripts, and license notices.

| Original Source Path | Decision | Classification | Portability / Adapter | Connected to SARTHI? | Verification Strategy |
|---|---|---|---|---|---|
| `pi/core/skills/agent-self-evaluation/examples/high-score-example.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/agent-self-evaluation/examples/low-score-example.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/agent-self-evaluation/references/evaluation-criteria.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/agent-self-evaluation/references/hook-integration.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/agent-self-evaluation/scripts/evaluate.py` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/angular-animations.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/angular-aria.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/cli.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/component-harnesses.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/component-styling.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/components.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/creating-services.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/data-resolvers.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/define-routes.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/defining-providers.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/di-fundamentals.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/e2e-testing.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/effects.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/hierarchical-injectors.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| `pi/core/skills/angular-developer/references/host-elements.md` | `include` | Documentation Only | Passive Text (ADR-009) | **Passive** (No Execution) | Static Hash Verifier |
| *... (345 additional `supporting` items cataloged in inventory.json) ...* | — | — | — | — | — |
| `scripts/lib/worktree-lifecycle/git.js` | `reject` | Excluded | Untrusted / Vendor Artifact | Excluded (ADR-009) | Exclusion Gate Check |
| `scripts/lib/worktree-lifecycle/lifecycle.js` | `reject` | Excluded | Untrusted / Vendor Artifact | Excluded (ADR-009) | Exclusion Gate Check |
| `install.sh` | `reject` | Excluded | Untrusted / Vendor Artifact | Excluded (ADR-009) | Exclusion Gate Check |
| `install.ps1` | `reject` | Excluded | Untrusted / Vendor Artifact | Excluded (ADR-009) | Exclusion Gate Check |
| `ecc_dashboard.py` | `reject` | Excluded | Untrusted / Vendor Artifact | Excluded (ADR-009) | Exclusion Gate Check |

---

## 4. Source-to-Runtime Traceability Metrics

| Dimension | Metric | Formula | Score | Acceptance Status |
|---|---|---|---|---|
| **Source Discovery** | Evaluated Assets | Total Upstream Tracked Files Evaluated / Total Known | 962 / 962 (**100.0%**) | **PASSED** |
| **Disposition Coverage** | Categorized Entries | (Included + Deferred + Rejected) / Total Upstream | 962 / 962 (**100.0%**) | **PASSED** |
| **Knowledge Preservation** | Preserved Upstream Assets | Upstream Knowledge Assets Preserved / Required Preserved | 391 / 391 (**100.0%**) | **PASSED** |
| **Manifest Integrity** | Physical Snapshot Files | Manifest Checksum Verified Files (391 Upstream + 1 Generated Inventory) | 392 / 392 (**100.0%**) | **PASSED** |
| **Logical Resource Indexing** | Provider-Indexed Catalog | Logical Resources Indexed / Intended to be Indexed | 589 / 589 (**100.0%**) | **PASSED** |
| **Runtime Accessibility** | Content-Retrievable Assets | Active Retrievable Resources / Active Bundled Resources | 341 / 341 (**100.0%**) | **PASSED** |
| **Execution Safety** | Script Execution Block | Unauthorized Executable Scripts Permitted | **0 scripts (100% Blocked)** | **PASSED (ADR-009)** |

---

## 5. Non-Negotiable Acceptance Certification

All 962 upstream assets are accounted for with zero silent omissions. All 391 included upstream files (plus 1 generated inventory metadata file, 392 files total in manifest) are checksum-verified against commit `c05b2d6614f62f6db0047669aa4eefb223d478f9`. Execution safety invariants under ADR-005 and ADR-009 are strictly enforced.
