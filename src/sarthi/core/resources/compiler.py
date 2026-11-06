"""Runtime context compiler assembling and formatting engineering intelligence payloads."""
from __future__ import annotations

from typing import Any

from sarthi.core.models import ProjectConfig
from sarthi.core.resources.models import (
    CompiledContext,
    PrecedenceTier,
    ResourceType,
)
from sarthi.core.resources.selector import UnifiedResourceSelector
from sarthi.core.security import neutralize_fence_tags


class ContextCompiler:
    """Assembles selected multi-provider knowledge into a structured, explainable context payload."""

    def __init__(self, selector: UnifiedResourceSelector | None = None) -> None:
        self.selector = selector or UnifiedResourceSelector()

    def compile_context(
        self,
        active_layers: list[str],
        task: str,
        task_type: str = "feature",
        config: ProjectConfig | None = None,
        max_tokens: int = 3000,
    ) -> CompiledContext:
        """Executes selection and compiles the complete structured engineering context."""
        resources, trace, conflict_report = self.selector.select_resources(
            active_layers=active_layers,
            task=task,
            task_type=task_type,
            config=config,
            max_tokens=max_tokens,
        )

        # Inviolable Security Invariants (Tier 1)
        security_invariants = [
            "PathGuard: All file reads and writes must remain strictly contained within the project root directory.",
            "Credential Denylist: Access to .env, private keys (*.pem, *.key, id_*), and credentials is permanently blocked.",
            "Command Allowlist: Only verified, allowlisted binaries (pytest, ruff, eslint, npm) may be executed.",
            "Interactive TTY Approval: Any unapproved test command requires explicit user approval before execution.",
            "Untrusted XML Fence Sanitization: All untrusted project data and prompts are neutralized with [untrusted_project_data].",
        ]

        # Core Contract Rules (Tier 3)
        core_contract_rules: list[str] = []
        native_standards: list[dict[str, Any]] = []
        ecc_skills: list[dict[str, Any]] = []
        ecc_commands: list[dict[str, Any]] = []
        ecc_agents: list[dict[str, Any]] = []
        provenance_records: list[dict[str, Any]] = []

        for r in resources:
            prov_record = {
                "id": r.id,
                "provider": r.provider_id,
                "source_path": r.source_path,
                "source_commit": r.source_commit,
                "source_version": r.source_version,
                "license": r.license,
                "tier": r.precedence_tier,
            }
            provenance_records.append(prov_record)

            if r.precedence_tier <= int(PrecedenceTier.TIER_3_CORE_CONTRACT):
                core_contract_rules.append(r.description or r.name)
            elif r.type == ResourceType.RULE and r.provider_id == "native":
                native_standards.append({
                    "id": r.id,
                    "title": r.name,
                    "category": r.category,
                    "description": r.description,
                    "rule": r.content_inline or "",
                    "required_tools": r.required_tools,
                })
            elif r.type == ResourceType.SKILL:
                content = self.selector.registry.get_content(r)
                ecc_skills.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "stacks": r.applicable_stacks,
                    "guidance": content[:1200] if content else "",
                    "source_path": r.source_path,
                })
            elif r.type == ResourceType.COMMAND:
                ecc_commands.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "source_path": r.source_path,
                })
            elif r.type == ResourceType.AGENT:
                ecc_agents.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "tools": r.required_tools,
                    "source_path": r.source_path,
                })

        # Deterministic Verification Requirements (Tier 2)
        verification_requirements = [
            "Execute secrets scan (UNI-SEC-001) to verify zero credentials in code.",
            "Execute Ruff / ESLint linter to verify syntax and undefined symbols.",
            "Execute Semgrep AST check for SQL injection (sec-sql-string-concat).",
            "Execute project test suite (pytest) with 100% pass rate before completion.",
        ]

        return CompiledContext(
            task_understanding=task,
            active_layers=active_layers,
            security_invariants=security_invariants,
            core_contract_rules=core_contract_rules,
            native_standards=native_standards,
            ecc_skills=ecc_skills,
            ecc_commands=ecc_commands,
            ecc_agents=ecc_agents,
            verification_requirements=verification_requirements,
            provenance_records=provenance_records,
            selection_trace=trace,
        )

    def render_markdown_instructions(self, context: CompiledContext) -> str:
        """Renders the compiled context as clear, Markdown-formatted instructions for an AI coding agent."""
        md = "# Sarthi Engineering Intelligence Instructions\n\n"
        md += f"**Task:** {neutralize_fence_tags(context.task_understanding)}\n"
        md += f"**Active Layers:** {', '.join(context.active_layers)}\n\n"

        md += "## 1. Mandatory Security Invariants (Tier 1 - Inviolable)\n"
        for inv in context.security_invariants:
            md += f"- **[SECURITY]** {inv}\n"
        md += "\n"

        if context.core_contract_rules:
            md += "## 2. Mandatory Core Engineering Contract (Tier 3)\n"
            for rule in context.core_contract_rules:
                md += f"- **[CONTRACT]** {rule}\n"
            md += "\n"

        if context.native_standards:
            md += "## 3. Verified Architectural Standards (Tier 5)\n"
            for std in context.native_standards:
                md += f"### {std['id']}: {std['title']}\n"
                md += f"{std['rule']}\n\n"

        if context.ecc_skills:
            md += "## 4. Upstream ECC Engineering Guidance & Skills (Tier 6)\n"
            for sk in context.ecc_skills:
                md += f"### Skill: {sk['name']} (`{sk['id']}`)\n"
                md += f"> {sk['description']}\n\n"
                if sk.get("guidance"):
                    md += f"```text\n{sk['guidance'][:800]}...\n```\n\n"

        md += "## 5. Mandatory Verification Gates (Tier 2)\n"
        for req in context.verification_requirements:
            md += f"- **[VERIFY]** {req}\n"
        md += "\n"

        md += "## 6. Knowledge Provenance Trace\n"
        md += f"- Total resources evaluated: {context.selection_trace.total_evaluated}\n"
        md += f"- Selected resources: {context.selection_trace.total_selected}\n"
        md += f"- Context token count: {context.selection_trace.token_count} / {context.selection_trace.token_limit}\n"
        md += "- Upstream ECC commit: `c05b2d6` (v2.2.3, MIT License, Affaan Mustafa)\n"

        return md
