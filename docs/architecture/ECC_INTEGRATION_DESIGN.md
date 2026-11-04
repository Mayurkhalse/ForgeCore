# ECC Integration Architecture Design

> **Document:** `docs/architecture/ECC_INTEGRATION_DESIGN.md`  
> **Status:** Approved Architectural Specification  
> **Target Project:** Sarthi (evolving from ForgeCore)  
> **Baseline Snapshot:** Everything Claude Code (ECC) v2.2.3 (Commit `b38be6a`)  
> **Author:** Principal Software Architect & Senior Python Systems Engineer  

---

## 1. Executive Summary & Vision

The core mission of **Sarthi** is to provide AI coding agents with a deterministic engineering foundation that ensures generated code meets production-grade standards. 

In ForgeCore v0.1.0, engineering guidance was restricted to an initial, manually authored library of 85 YAML rules across 11 architectural layers. While effective for basic syntactic and structural verification, this handcrafted library created a severe limitation: **the breadth of engineering domain knowledge available to the AI agent was bounded by our internal authoring capacity.**

To resolve this limitation without sacrificing deterministic verification, Sarthi integrates **Everything Claude Code (ECC)** as its foundational engineering knowledge base. ECC represents the industry's most comprehensive open-source collection of production-ready agent skills, domain rules, specialized sub-agents, and procedural workflows.

### The Central Architectural Mandate
Sarthi does **not** simply dump hundreds of prompt files into the AI agent's context window. Sarthi treats ECC resources as an indexed, typed, offline-bundled knowledge catalog governed by:
1. **Deterministic Verification Over Aspirational Guidance:** Machine-enforced AST invariants, linters, and security checks always supersede natural-language guidelines.
2. **Strict Provider Isolation:** A clean provider abstraction decouples knowledge suppliers (ECC, Native Standards, Custom Extensions) from the core MCP server, security sandboxing, and verification engine.
3. **Budget-Capped Context Delivery:** Resources are dynamically discovered, filtered by stack and task, ranked by relevance, and capped within a 3,000-token envelope to prevent prompt drift and context saturation.
4. **Zero-Trust Fencing:** All project-derived inputs and bundled text are strictly sanitized and fence-neutralized before reaching the host agent.

---

## 2. High-Level Architecture

The integration introduces a modular **Provider Architecture** that sits between the MCP Tool Handlers and the underlying knowledge files.

```mermaid
flowchart TD
    subgraph HostEnvironment["IDE / Host Agent Environment"]
        User["Developer / Operator"]
        IDE["Antigravity IDE / Claude Code / Cursor"]
        Agent["Host AI Coding Agent"]
    end

    subgraph IntegrationLayer["MCP Server & Interface Layer (`src/forgecore/mcp/`)"]
        MCPServer["MCP Server (`server.py`)"]
        ToolHandlers["MCP Tool Handlers (`tools.py`)"]
        ResourceEndpoints["MCP Resources (`resources.py`)"]
    end

    subgraph ProviderLayer["Knowledge Provider Architecture (`src/forgecore/core/providers/`)"]
        ProviderRegistry["Provider Registry & Manager"]
        
        subgraph Providers["Concrete Providers"]
            NativeProv["Sarthi Native Provider<br/>(85 Core Standards, 16 Contract Rules)"]
            ECCProv["ECC Bundled Provider (v2.2.3)<br/>(Skills, Rules, Agent Prompts, Workflows)"]
            CustomProv["Third-Party / Workspace Provider<br/>(Future Extension)"]
        end
    end

    subgraph SelectionEngine["Selection & Synthesis Engine"]
        StackDetector["StackDetector (`core/stack_detector.py`)"]
        ResourceSelector["Unified Resource Selector (`core/resources/selector.py`)"]
        ConflictEngine["Precedence & Conflict Resolver"]
        BudgetManager["Token Budget Manager (`core/budget.py`)"]
    end

    subgraph VerificationSubsystem["Deterministic Verification Engine (`core/verify/`)"]
        Verifier["Verifier Orchestrator (`verifier.py`)"]
        Runners["Runners: Secrets, Ruff, Semgrep, ESLint, Tests"]
        Trust["CommandTrustManager (`trust.py`)"]
        PathGuard["PathGuard Sandbox (`pathguard.py`)"]
    end

    %% Interactions
    User -->|"Directs Task"| Agent
    Agent <-->|"JSON-RPC (stdio)"| MCPServer
    MCPServer --> ToolHandlers
    MCPServer --> ResourceEndpoints

    ToolHandlers -->|"Queries Active Resources"| ResourceSelector
    StackDetector -->|"Supplies Detected Layers"| ResourceSelector
    
    ResourceSelector -->|"Queries Catalog"| ProviderRegistry
    ProviderRegistry --> NativeProv
    ProviderRegistry --> ECCProv
    ProviderRegistry --> CustomProv

    ProviderRegistry -->|"Returns Raw Typed Resources"| ConflictEngine
    ConflictEngine -->|"Resolves Precedence"| BudgetManager
    BudgetManager -->|"Budget-Capped Payload (<3k tokens)"| ToolHandlers

    ToolHandlers -->|"Executes Verification"| Verifier
    Verifier --> PathGuard
    Verifier --> Trust
    Verifier --> Runners
```

---

## 3. The Typed Resource Model

Rather than forcing every distinct ECC artifact into ForgeCore's legacy `Rule` model, Sarthi establishes an extensible, strongly typed hierarchy using Pydantic v2.

### 3.1 Resource Type Classification
An engineering resource serves a distinct behavioral role in the agent harness lifecycle:

```mermaid
classDiagram
    class ResourceType {
        <<enumeration>>
        RULE
        SKILL
        AGENT
        WORKFLOW
        CONTEXT
        HOOK
        MCP_CONFIG
        SUPPORTING
    }
```

- **`RULE`:** Directives, constraints, and invariants (e.g. `fastapi-no-db-in-routes`, `univ-no-hardcoded-secrets`). May carry machine verifier references.
- **`SKILL`:** Procedural instructions, domain patterns, and actionable recipes that teach an agent *how* to execute a complex task (e.g. `fastapi-tdd-flow`, `react-performance-optimization`).
- **`AGENT`:** Role personas, planning prompts, and sub-agent task definitions (e.g. `security-auditor`, `database-architect`, `planner`).
- **`WORKFLOW`:** Multi-phase execution lifecycles with gated phases (e.g. `feature-implementation`, `bug-investigation`).
- **`CONTEXT`:** Architectural references, stack summaries, and project background context.
- **`HOOK`:** Event-driven lifecycle interceptors (deferred from execution in Milestone 1; cataloged as metadata).
- **`MCP_CONFIG`:** Declarations of external tool services and server shims.
- **`SUPPORTING`:** Auxiliary templates, test fixtures, and scripts.

### 3.2 Strong Metadata Schema
Every resource is indexed with explicit provenance, licensing, and applicability metadata:

```python
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

class ResourceType(str, Enum):
    RULE = "rule"
    SKILL = "skill"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CONTEXT = "context"
    HOOK = "hook"
    MCP_CONFIG = "mcp_config"
    SUPPORTING = "supporting"

class CompatibilityStatus(str, Enum):
    NATIVE = "native"              # Runs natively across all IDEs via MCP text/prompt
    ADAPTED = "adapted"            # Adapted for Sarthi/Antigravity execution
    HOST_DEPENDENT = "host_dep"    # Requires specific host features (e.g., Claude Code subagents)
    DEFERRED = "deferred"          # Cataloged but inactive (e.g., shell hooks)

class TrustLevel(str, Enum):
    CORE_SECURITY = "core_sec"     # Immutable policy; cannot be overridden
    VERIFIED_NATIVE = "native"     # Native Sarthi rules and verifiers
    BUNDLED_ECC = "bundled_ecc"    # Pinned, audited ECC upstream resources
    WORKSPACE_LOCAL = "workspace"  # Untrusted local repository configurations

class EngineeringResource(BaseModel):
    """Universal typed model for all engineering intelligence artifacts."""
    id: str = Field(..., description="Unique canonical identifier, e.g. 'ecc.skill.tdd-flow'")
    provider_id: str = Field(..., description="Identifier of origin provider: 'ecc', 'native', 'workspace'")
    type: ResourceType = Field(..., description="Structural classification of the resource")
    name: str = Field(..., description="Human-readable title")
    description: str = Field(default="", description="Summary of capability or constraint")
    
    # Provenance and Versioning
    source_path: str = Field(..., description="Path relative to bundle root")
    source_version: str = Field(..., description="Version of origin upstream (e.g. '2.2.3')")
    source_commit: str = Field(..., description="Git commit SHA of origin snapshot")
    license: str = Field(default="MIT", description="Applicable license")
    
    # Selection and Target Matching
    applicable_stacks: list[str] = Field(default_factory=list, description="Target layers: ['fastapi', 'react', 'all']")
    applicable_tasks: list[str] = Field(default_factory=list, description="Task types: ['feature', 'bugfix', 'refactor']")
    tags: list[str] = Field(default_factory=list)
    
    # Execution & Safety Semantics
    compatibility: CompatibilityStatus = Field(default=CompatibilityStatus.NATIVE)
    trust_level: TrustLevel = Field(default=TrustLevel.BUNDLED_ECC)
    requires_tools: list[str] = Field(default_factory=list, description="Tools needed by the resource")
    
    # Content Handling
    content_ref: str | None = Field(default=None, description="Path to markdown body or raw content")
    content_inline: str | None = Field(default=None, description="Inline content if small")
    
    # Conflict & Precedence
    supersedes: list[str] = Field(default_factory=list, description="Resource IDs overridden by this resource")
```

---

## 4. Provider Architecture

### 4.1 The Provider Protocol
A knowledge provider is a decoupled component responsible for cataloging, filtering, and rendering resources under its ownership.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class KnowledgeProvider(Protocol):
    """Protocol implemented by all resource providers."""
    
    @property
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'native', 'ecc', 'workspace')."""
        ...
        
    @property
    def version(self) -> str:
        """Provider catalog release version."""
        ...

    def initialize(self) -> None:
        """Loads manifests, indexes resources, and validates schemas."""
        ...

    def list_resources(self, resource_type: ResourceType | None = None) -> list[EngineeringResource]:
        """Returns all indexed resources matching optional type filter."""
        ...

    def get_resource(self, resource_id: str) -> EngineeringResource | None:
        """Fetches resource descriptor by unique canonical ID."""
        ...

    def get_content(self, resource: EngineeringResource) -> str:
        """Reads and returns the raw content string (Markdown, YAML, or text)."""
        ...
```

### 4.2 The Concrete Providers
1. **`SarthiNativeProvider` (`src/forgecore/core/providers/native.py`):**
   - Wraps the existing 85 YAML standards in `standards/` and the Core Contract in `standards/contract.md`.
   - Maps each legacy `Rule` into an `EngineeringResource` of type `RULE`.
   - Maintains full backward compatibility with existing tests and schema expectations.
   - Assigned `TrustLevel.VERIFIED_NATIVE`.
2. **`ECCBundledProvider` (`src/forgecore/core/providers/ecc.py`):**
   - Reads the local bundled catalog located at `resources/ecc/`.
   - Governed by `resources/ecc/manifest.json`.
   - Parses markdown frontmatter for ECC skills, agent prompts, and workflows.
   - Assigned `TrustLevel.BUNDLED_ECC`.
3. **`WorkspaceProvider` (Planned for Milestone 5):**
   - Discovers project-specific rules from `.forgecore/rules/` or `.sarthi/rules/`.
   - Assigned `TrustLevel.WORKSPACE_LOCAL` (strictly fenced and sandboxed).

---

## 5. Local Bundling & Offline Isolation Strategy

To satisfy **Decision 1 (Version-Pinned Baseline)** and guarantee reliable offline operation, ECC resources are bundled directly into the distribution package.

### 5.1 Proposed Directory Structure
```
resources/
|-- native/
|   |-- contract.md               # 16-point Core Contract
|   |-- standards/                # 85 YAML rules across 11 layers
|   `-- workflows/                # feature.md, bugfix.md, refactor.md, new-project.md
`-- ecc/
    |-- manifest.json             # Pinned catalog metadata, commit SHA, resource index
    |-- LICENSE                   # Upstream MIT License (Affaan Mustafa)
    |-- NOTICE                    # Attribution and modification history
    |-- rules/                    # Selected coding standards and domain rules
    |-- skills/                   # Curated procedural engineering skills
    |-- agents/                   # Agent persona prompts and planning guides
    |-- workflows/                # Multi-stage task processes
    `-- contexts/                 # Stack and architectural reference briefs
```

### 5.2 The Bundle Manifest (`resources/ecc/manifest.json`)
The bundle manifest is an immutable record anchoring the ECC snapshot:

```json
{
  "schema_version": "1.0.0",
  "upstream": {
    "repository": "https://github.com/affaan-m/ECC",
    "release_tag": "v2.2.3",
    "commit_sha": "b38be6a",
    "snapshot_date": "2026-10-01",
    "license": "MIT",
    "author": "Affaan Mustafa"
  },
  "curation": {
    "total_resources": 158,
    "skills_count": 112,
    "agents_count": 24,
    "rules_count": 14,
    "workflows_count": 8
  },
  "resources": [
    {
      "id": "ecc.skill.tdd-workflow",
      "type": "skill",
      "name": "Test-Driven Development Workflow",
      "path": "skills/tdd-workflow/SKILL.md",
      "applicable_stacks": ["all"],
      "applicable_tasks": ["feature", "bugfix"],
      "compatibility": "native"
    }
  ]
}
```

### 5.3 Offline and Installation Guarantees
- **Zero Runtime Network Calls:** The provider indexes resources from the local disk using `importlib.resources` or local path resolution. No Git binary or internet access is required during runtime.
- **Package Ingestion:** `pyproject.toml` packages the `resources/` directory within package data, ensuring `pip install` or `uv sync` installs the complete bundled intelligence.

---

## 6. Coexistence, Precedence & Conflict Resolution

A critical challenge of the hybrid architecture is preventing contradictions between broad ECC natural-language guidelines and Sarthi's deterministic rules.

### 6.1 The Strict Precedence Hierarchy

```
+-----------------------------------------------------------------------------------------+
|                         SARTHI STRICT PRECEDENCE HIERARCHY                              |
+-----------------------------------------------------------------------------------------+
| Tier 1: Core Security & Sandbox Policy (Inviolable)                                     |
|         - PathGuard jail checks, credential denylist (`.env`, `id_rsa`)                 |
|         - Command allowlist, shell metacharacter blocking, interactive TTY approvals    |
|         - Cannot be overridden by any rule, skill, prompt, or config override           |
+-----------------------------------------------------------------------------------------+
| Tier 2: Deterministic Machine Verifier Failures (Hard Gate)                             |
|         - Semgrep SQL injection AST patterns (`sec-sql-string-concat`)                  |
|         - SecretsRunner regex & entropy hits (`UNI-SEC-001`)                            |
|         - Ruff syntax & undefined name errors (`RUFF-E9`, `RUFF-F821`)                  |
|         - Project test suite execution failures (`UNI-TEST-001`)                        |
+-----------------------------------------------------------------------------------------+
| Tier 3: Core Governance Contract (Inviolable Standard)                                  |
|         - 16 Core Contract rules (`standards/contract.md`)                              |
|         - Separation of concerns, parameterization, no swallowed exceptions            |
+-----------------------------------------------------------------------------------------+
| Tier 4: Explicit Project Configuration Overrides                                        |
|         - User-configured overrides in `.forgecore/project.yaml`                        |
|         - Explicit layer additions/removals, rule severity adjustments                  |
+-----------------------------------------------------------------------------------------+
| Tier 5: Sarthi Native Standards Library                                                 |
|         - 85 curated architectural standards (`standards/*`)                            |
+-----------------------------------------------------------------------------------------+
| Tier 6: Bundled ECC Skills & Procedural Guidance                                        |
|         - ECC skills, workflows, agent prompts, architectural patterns                  |
|         - Active only when conforming to higher tiers                                    |
+-----------------------------------------------------------------------------------------+
```

### 6.2 Conflict Resolution Mechanics
When a candidate resource from ECC overlaps with a Sarthi native rule:
1. **Rule Supersession (`supersedes`):** If an ECC rule explicitly conflicts with a native rule, the native rule takes precedence unless the native rule is marked as superseded in configuration.
2. **Deterministic Precedence:** If an ECC skill recommends a pattern (e.g. quick mock query in an endpoint) that triggers a deterministic AST verifier (e.g. `FAPI-ARCH-001: no direct DB access in route handlers`), the verifier failure halts the workflow. Natural language advice **never** overrides a static analysis check.
3. **Additive Complementarity:** In practice, 90% of ECC skills are *procedural* (explaining how to structure TDD, design React component trees, or vectorize ML pipelines), whereas Sarthi standards are *declarative gates* (forbidding SQL concatenation, unhandled rejections, or hardcoded secrets). They operate in harmony: **ECC teaches the agent how to build; Sarthi verifies that the agent built safely.**

---

## 7. The End-to-End Request Lifecycle

The unified lifecycle traces an agent interaction from task initiation to final deterministic verification:

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (User)
    participant IDE as Host IDE / Agent
    participant MCP as Sarthi MCP Server
    participant Intel as Project Intelligence
    participant Registry as Provider Registry
    participant Engine as Selection & Budget Engine
    participant Verifier as Verification Engine

    Dev->>IDE: "Implement JWT refresh token rotation in FastAPI"
    
    %% Phase 1: Stack & Layer Discovery
    IDE->>MCP: initialize_project(root=".")
    MCP->>Intel: ContextBuilder.build_context()
    Intel-->>MCP: Detected: FastAPI, Python 3.13, Pytest (Active Layers: universal, security, fastapi)
    MCP-->>IDE: Initialized context v1

    %% Phase 2: Workflow & Resource Selection
    IDE->>MCP: get_workflow(task_type="feature")
    MCP->>Registry: Query workflows for "feature"
    Registry-->>MCP: ECC Feature Workflow + Project Verification Commands
    MCP-->>IDE: Markdown Workflow (Plan, Design, Implement, Verify, Report)

    %% Phase 3: Targeted Knowledge Retrieval
    IDE->>MCP: get_standards(task="JWT refresh rotation", layers=["fastapi", "security"])
    MCP->>Engine: Select applicable resources(layers, task, max_rules=15)
    Engine->>Registry: Fetch Native Rules + ECC Skills + ECC Agent Guides
    Registry-->>Engine: 3 Native Rules, 2 ECC Skills, 1 Security Checklist
    Engine->>Engine: Apply Precedence & Conflict Rules
    Engine->>Engine: BudgetManager.enforce_budget(cap=3000 tokens)
    Engine-->>MCP: Budget-Capped Knowledge Payload
    MCP-->>IDE: Structured Rules, Good/Bad Examples, and ECC Procedural Guidance

    %% Phase 4: Implementation
    Note over IDE: Agent writes route handler in `src/auth.py` and test in `tests/test_auth.py`

    %% Phase 5: Deterministic Verification
    IDE->>MCP: verify_project(scope="changed")
    MCP->>Verifier: Verifier.verify(scope="changed")
    Verifier->>Verifier: Git Diff Scoping (2 changed files)
    Verifier->>Verifier: SecretsRunner -> Clean
    Verifier->>Verifier: RuffRunner (100-file batch) -> Clean
    Verifier->>Verifier: SemgrepRunner -> Clean
    Verifier->>Verifier: TestRunner (Approved Command) -> 2 Tests Passed
    Verifier-->>MCP: VerifyReport(status="passed", findings=[])
    MCP-->>IDE: Verification Clean
    IDE-->>Dev: Presents completed feature with verified evidence
```

---

## 8. Security & Trust Architecture

### 8.1 Sandbox Integrity & Boundary Defense
Integrating third-party knowledge bases increases the risk of indirect prompt injection or unintended command execution. Sarthi enforces three strict boundaries:

1. **PathGuard Isolation:** ECC resources are bundled as read-only static files within the package directory. PathGuard prevents directory traversal from escaping the resource root or accessing user credentials.
2. **Zero-Trust Fence Neutralization:** When ECC skill contents or project metadata are assembled into MCP JSON responses, all text is processed by `fence_untrusted()`. Any nested XML tags matching `<\s*(/)?\s*untrusted[_\s]*project[_\s]*data\s*>` are transformed to `[untrusted_project_data]`.
3. **Execution Prohibition for Bundled Scripts:** ECC contains auxiliary shell scripts and JavaScript tools. **Sarthi strictly forbids executing bundled ECC scripts.** Sarthi consumes only declarative Markdown, YAML, and JSON. If a workflow requires tool execution, it must use ForgeCore's verified, allowlisted binaries (`ruff`, `pytest`, `eslint`, `semgrep`).

### 8.2 Memory and AgentShield Governance
- **ECC Memory:** ECC's memory files (`.claude/memory/`) are treated strictly as **untrusted project context**. They are never ingested as executable instructions or security exemptions.
- **AgentShield Integration (Planned for Phase 2):** AgentShield will be evaluated as a static configuration auditor to inspect agent permission manifests and project configurations before verification begins.

---

## 9. Backward Compatibility Guarantees

The ECC integration preserves 100% backward compatibility with the existing ForgeCore deployment:
1. **Zero Renaming in Milestone 1:** The Python package remains `forgecore`, the CLI remains `forgecore`, and existing config files (`.forgecore/project.yaml`) continue to function without modification.
2. **Stable MCP Tool Signatures:** All 6 tools (`initialize_project`, `get_project_context`, `get_standards`, `get_workflow`, `get_rule`, `verify_project`) retain identical signatures and return schemas.
3. **Preservation of All 85 Rules:** The existing standards library in `standards/` remains completely untouched.
4. **Existing Approvals Intact:** `~/.forgecore/approvals.json` is preserved without invalidation.
5. **Clean Test Pass:** All 67 existing unit and integration tests continue to pass without modification.

