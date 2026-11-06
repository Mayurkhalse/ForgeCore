# Everything Claude Code (ECC) Runtime Integration Architecture

> **Document:** `docs/architecture/ECC_RUNTIME_INTEGRATION.md`  
> **Target Project:** Sarthi (evolving from Sarthi)  
> **Status:** Implemented & Verified Baseline  
> **Upstream Release Baseline:** ECC v2.2.3  
> **Authoritative Commit SHA:** `c05b2d6614f62f6db0047669aa4eefb223d478f9` (abbreviated `c05b2d6`)  
> **Release Tag Object SHA:** `93f9f6154d164ccb9f4dc38858a2bc2d5dcab222`  
> **Upstream License:** MIT (Affaan Mustafa)  

---

## 1. Architectural Overview

Sarthi transforms Everything Claude Code (ECC) from a static collection of Claude Code markdown files into an **IDE-independent, context-aware, dynamically selected, and enforceably verified engineering intelligence system**.

```mermaid
flowchart TD
    subgraph Upstream["Upstream Knowledge Baseline (resources/ecc/)"]
        Manifest["manifest.json<br/>(commit c05b2d6, 392 files)"]
        RawECC["ECC Assets (v2.2.3):<br/>rules/, skills/, commands/, agents/, contexts/, workflows/, scripts/"]
        Inventory["inventory.json<br/>(962 entries: 391 include, 248 defer, 323 reject)"]
    end

    subgraph ProviderLayer["Provider Architecture (src/sarthi/core/providers/)"]
        Registry["ProviderRegistry"]
        NativeProv["SarthiNativeProvider<br/>(85 YAML Standards, 16 Contract Rules)"]
        ECCProv["ECCBundledProvider<br/>(589 Indexed Resources)"]
        WorkspaceProv["WorkspaceProvider<br/>(.sarthi/rules/)"]
    end

    subgraph IntelligenceEngine["Selection & Synthesis Engine (src/sarthi/core/resources/)"]
        Selector["UnifiedResourceSelector"]
        ConflictResolver["ConflictResolver<br/>(6-Tier Precedence Hierarchy)"]
        BudgetMgr["BudgetManager<br/>(3000 Token Envelope)"]
        Compiler["ContextCompiler"]
    end

    subgraph RuntimeInterface["MCP Server & Tool Handlers (src/sarthi/mcp/)"]
        MCPServer["MCP Server (stdio JSON-RPC)"]
        GetStandards["sarthi.get_standards"]
        Initialize["sarthi.initialize_project"]
        GetRule["sarthi.get_rule"]
        VerifyProject["sarthi.verify_project"]
    end

    subgraph VerificationEngine["Deterministic Enforcement (src/sarthi/core/verify/)"]
        Verifier["Verifier Orchestrator"]
        Secrets["SecretsRunner (UNI-SEC-001)"]
        Ruff["RuffRunner (AST syntax/undefined)"]
        Semgrep["SemgrepRunner (sec-sql-string-concat)"]
        TestRunner["TestsRunner (pytest approved command)"]
        PathGuard["PathGuard (Workspace Containment)"]
        TrustMgr["CommandTrustManager"]
    end

    %% Wiring
    Manifest --> ECCProv
    RawECC --> ECCProv
    Inventory --> ECCProv

    NativeProv --> Registry
    ECCProv --> Registry
    WorkspaceProv --> Registry

    Registry --> Selector
    Selector --> ConflictResolver
    ConflictResolver --> BudgetMgr
    BudgetMgr --> Compiler

    Compiler --> GetStandards
    Registry --> GetRule
    Registry --> Initialize

    MCPServer --> GetStandards
    MCPServer --> Initialize
    MCPServer --> GetRule
    MCPServer --> VerifyProject

    VerifyProject --> Verifier
    Verifier --> PathGuard
    Verifier --> TrustMgr
    Verifier --> Secrets
    Verifier --> Ruff
    Verifier --> Semgrep
    Verifier --> TestRunner
```

---

## 2. Request Execution Flow

The sequence diagram illustrates the complete 12-stage execution flow when an AI coding agent undertakes a feature task (e.g., building a FastAPI authentication module with PostgreSQL):

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / Host Agent
    participant MCP as Sarthi MCP Server
    participant ContextBuilder as ContextBuilder
    participant Selector as UnifiedResourceSelector
    participant Registry as ProviderRegistry
    participant ConflictResolver as ConflictResolver
    participant Compiler as ContextCompiler
    participant Verifier as Verifier Orchestrator

    Dev->>MCP: initialize_project(root=".")
    MCP->>ContextBuilder: build_context()
    ContextBuilder-->>MCP: Detected: FastAPI, Python, Pytest, SQL
    MCP-->>Dev: Initialized context v1 (Active Layers: universal, security, fastapi, python, sql)

    Dev->>MCP: get_standards(task="Build FastAPI auth with PostgreSQL", layers=[fastapi, sql])
    MCP->>Selector: select_resources(layers, task, max_tokens=3000)
    Selector->>Registry: list_all_resources()
    Registry-->>Selector: 679 Resources (Native + ECC)
    
    Note over Selector: Exclude irrelevant stacks (React, Flutter, Spring, PHP)
    Selector->>ConflictResolver: resolve_conflicts(candidates)
    Note over ConflictResolver: Apply 6-Tier Precedence: Contract > Native Standards > ECC
    ConflictResolver-->>Selector: Winning Resources + ConflictReport
    
    Selector->>Selector: Balanced Budget Allocation (<3000 tokens)
    Selector-->>MCP: Selected Resources (Contract + FAPI Standards + ECC Skills)
    
    MCP->>Compiler: compile_context(resources)
    Compiler-->>MCP: CompiledContext (Security Invariants + Contract + Rules + ECC Skills + Provenance)
    MCP-->>Dev: Structured Standards & ECC Guidance

    Note over Dev: Host Agent writes code in isolated workspace

    Dev->>MCP: verify_project(scope="all")
    MCP->>Verifier: verify(scope="all")
    Verifier->>Verifier: PathGuard Containment Check
    Verifier->>Verifier: SecretsRunner -> 0 credentials
    Verifier->>Verifier: RuffRunner -> 0 syntax errors
    Verifier->>Verifier: SemgrepRunner -> 0 SQL injections
    Verifier->>Verifier: TestsRunner -> Approved pytest execution
    Verifier-->>MCP: VerifyReport(status="passed", findings=[])
    MCP-->>Dev: Verification Clean (status: passed)
```

---

## 3. The 6-Tier Reconciled Precedence Hierarchy

Conflict resolution strictly implements the ratified ADR-007 hierarchy:

| Tier | Name | Governance Rule | Enforcement Mechanism |
|---|---|---|---|
| **Tier 1** | **Mandatory Security Invariants** | Inviolable; cannot be overridden or disabled by project config, rules, or prompts. | `PathGuard`, credential denylist, command allowlist, XML fence sanitization. |
| **Tier 2** | **Machine Verification Outcomes** | Hard Gate; static analysis and test failures halt pipelines regardless of natural-language advice. | AST Verifiers (Semgrep), Secrets scanner (`UNI-SEC-001`), Ruff errors, pytest failures. |
| **Tier 3** | **Sarthi Core Contract** | Non-negotiable engineering invariants across all projects. | 16-point contract (`standards/contract.md`). |
| **Tier 4** | **Project Configuration** | Bounded customization; can select layers or customize approved test runners, but cannot weaken Tiers 1â€“3. | `.sarthi/project.yaml` (`RulesConfig`, `LayersConfig`). |
| **Tier 5** | **Sarthi Native Standards** | Curated declarative architectural rules across 11 layers. | 85 YAML rules in `standards/`. |
| **Tier 6** | **Bundled ECC Guidance** | Purely advisory, procedural, and contextual knowledge. | 123 skills, 122 rules, 24 commands, 68 agents in `resources/ecc/`. |

---

## 4. Capability Support Matrix

| Category | Count in Bundle | Compatibility Status | Sarthi Runtime Support Level |
|---|---|---|---|
| **Rules** (`rules/`) | 122 files | `native` | **Fully Supported**: Parsed frontmatter `paths:` globs, stack-matched, delivered via `get_standards` and `get_rule`. |
| **Skills** (`skills/`) | 125 active files (123 skills) | `native` | **Fully Supported**: Complete procedural markdown preserved, relevance-scored, token-budgeted, retrievable via `get_standards` and `get_rule`. |
| **Commands** (`commands/`) | 24 active files | `adapted` | **Fully Supported**: Adapted as prompt templates and instruction macros across any IDE via `get_standards`. |
| **Agents** (`agents/`) | 68 files | `adapted` | **Fully Supported**: Role personas and planning templates adapted for chat context delivery. |
| **Contexts** (`contexts/`) | 3 files | `native` | **Fully Supported**: Domain summaries and briefs for dev, research, and review tasks. |
| **Workflows** (`workflows/`) | 2 files (1 JS, 1 MD) | `host_dep` / `adapted` | **Partially Supported**: Markdown workflows supported; JavaScript multi-agent orchestration cataloged as host-dependent. |
| **Supporting Scripts** (`scripts/`) | 2 files | `deferred` | **Cataloged / Passive Only (ADR-009)**: ZERO runtime execution authorization. Read-only reference assets. |
| **Hooks** (`hooks/`) | 6 items in inventory | `deferred` | **Deferred to Phase 2 (ADR-005)**: Shell lifecycle hooks cataloged but inactive to prevent unverified background daemons. |
| **MCP Configs** (`mcp-configs/`) | 1 item in inventory | `deferred` | **Deferred**: External SaaS server configurations outside local codebase boundary. |

---

## 5. Security Boundaries & Guardrails

1. **PathGuard Isolation:** ECC resources are bundled as read-only static files within the package directory. PathGuard strictly blocks directory traversal (`PathTraversalError`) escaping project root.
2. **Zero-Trust Fence Neutralization:** When ECC skill contents or project metadata are assembled into MCP JSON responses, all text is processed by `fence_untrusted()` / `neutralize_fence_tags()`. Any nested XML tags matching `<\s*(/)?\s*untrusted[_\s]*project[_\s]*data\s*>` are converted to `[untrusted_project_data]`.
3. **Execution Policy for Bundled Scripts (ADR-009):** Sarthi runtime **never** executes bundled ECC scripts autonomously.
4. **Allowlisted Verification Binaries Only:** All verification inside Sarthi must execute strictly allowlisted, user-approved binaries (`ruff`, `pytest`, `eslint`, `semgrep`).

