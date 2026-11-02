from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgecore.core.context import ContextBuilder
from forgecore.core.pathguard import PathGuard, PathGuardError
from forgecore.core.rules import RuleLoader, RuleSelector
from forgecore.core.verify.verifier import Verifier
from forgecore.core.workflows import WorkflowEngine


def fence_untrusted_data(data: Any) -> str:
    """Wraps untrusted project strings in security boundaries."""
    serialized = json.dumps(data, indent=2, default=str)
    return f"<untrusted_project_data>\n{serialized}\n</untrusted_project_data>"


class MCPToolHandlers:
    """Implementations for the six core ForgeCore MCP tools."""

    def __init__(self, standards_dir: Path | str | None = None) -> None:
        self.rule_loader = RuleLoader(standards_dir)
        self.workflow_engine = WorkflowEngine(
            Path(standards_dir) / "workflows" if standards_dir else None
        )
        self.all_rules = self.rule_loader.load_all_rules()
        self.profiles = self.rule_loader.load_profiles()
        self.selector = RuleSelector(self.all_rules, self.profiles)

    def initialize_project(self, root: str, force: bool = False) -> dict[str, Any]:
        """
        Inspects the project, detects stack and layers, registers configuration,
        and initializes context caching.
        """
        try:
            root_path = Path(root).resolve()
            PathGuard(root_path)
            builder = ContextBuilder(root_path)

            profile, config, version, refreshed = builder.build_context(force=force)
            active_layers = self.selector.resolve_active_layers(
                detected_layers=profile.layer_names(),
                config=config,
            )

            # Contract snippet
            contract_path = Path(__file__).resolve().parent.parent.parent.parent / "standards" / "contract.md"
            contract_summary = "Follow ForgeCore standards: Plan, Retrieve Standards, Test, and Verify before declaring complete."
            if contract_path.is_file():
                contract_summary = contract_path.read_text(encoding="utf-8")[:1200]

            return {
                "status": "initialized",
                "project_name": config.project.get("name", root_path.name),
                "context_version": version,
                "refreshed": refreshed,
                "detected_stack": {
                    "languages": profile.languages,
                    "package_managers": profile.package_managers,
                    "test_frameworks": profile.test_frameworks,
                    "suggested_profile": profile.suggested_profile,
                },
                "active_layers": active_layers,
                "evidence": json.loads(fence_untrusted_data(profile.evidence).replace("<untrusted_project_data>\n", "").replace("\n</untrusted_project_data>", "")),
                "core_contract_summary": contract_summary,
                "next_step": "Call forgecore.get_workflow(task_type) or forgecore.get_standards(task, layers) before writing code.",
            }
        except PathGuardError as pge:
            return {"error": {"code": "PATH_GUARD_ERROR", "message": str(pge), "hint": "Ensure root points to an existing directory."}}
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e), "hint": "Check project configuration and file permissions."}}

    def get_project_context(self, root: str) -> dict[str, Any]:
        """
        Retrieves cached project context, auto-refreshing if manifests or config changed.
        """
        try:
            root_path = Path(root).resolve()
            builder = ContextBuilder(root_path)
            profile, config, version, refreshed = builder.build_context(force=False)
            active_layers = self.selector.resolve_active_layers(
                detected_layers=profile.layer_names(),
                config=config,
            )

            return {
                "context_version": version,
                "refreshed": refreshed,
                "active_layers": active_layers,
                "languages": profile.languages,
                "test_frameworks": profile.test_frameworks,
                "fail_on": config.verify.fail_on.value,
                "require_plan": config.generation.require_plan,
                "require_tests": config.generation.require_tests,
            }
        except Exception as e:
            return {"error": {"code": "CONTEXT_ERROR", "message": str(e), "hint": "Run initialize_project first."}}

    def get_standards(
        self,
        root: str,
        task: str,
        task_type: str = "feature",
        layers: list[str] | None = None,
        max_rules: int = 15,
    ) -> dict[str, Any]:
        """
        Retrieves ranked and token-budgeted engineering standards for the active task.
        """
        try:
            root_path = Path(root).resolve()
            builder = ContextBuilder(root_path)
            profile, config, _, _ = builder.build_context(force=False)

            active_layers = self.selector.resolve_active_layers(
                detected_layers=profile.layer_names(),
                config=config,
                explicit_layers=layers,
            )

            selected_rules, truncated, hint = self.selector.select_rules(
                active_layers=active_layers,
                task=task,
                task_type=task_type,
                config=config,
                max_rules=max_rules,
            )

            rules_data = []
            for r in selected_rules:
                rules_data.append({
                    "id": r.id,
                    "title": r.title,
                    "layer": r.layer,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "rule": r.rule.strip(),
                    "good": r.good.strip() if r.good else "",
                    "bad": r.bad.strip() if r.bad else "",
                    "verify_ref": r.verify.ref if r.verify else None,
                })

            return {
                "task": task,
                "active_layers": active_layers,
                "total_returned": len(rules_data),
                "truncated": truncated,
                "rules": rules_data,
                "hint": hint or "Follow these standards carefully while implementing.",
            }
        except Exception as e:
            return {"error": {"code": "STANDARDS_ERROR", "message": str(e), "hint": "Check parameters and root path."}}

    def get_workflow(self, root: str, task_type: str = "feature") -> dict[str, Any]:
        """
        Returns the procedural workflow rendered with project-specific verification commands.
        """
        try:
            root_path = Path(root).resolve()
            builder = ContextBuilder(root_path)
            profile, config, _, _ = builder.build_context(force=False)
            active_layers = self.selector.resolve_active_layers(
                detected_layers=profile.layer_names(),
                config=config,
            )

            rendered = self.workflow_engine.render_workflow(
                task_type=task_type,
                active_layers=active_layers,
                config=config,
            )

            return {
                "task_type": task_type,
                "workflow_markdown": rendered,
                "active_layers": active_layers,
            }
        except Exception as e:
            return {"error": {"code": "WORKFLOW_ERROR", "message": str(e), "hint": "Ensure task_type is feature, bugfix, refactor, or new-project."}}

    def get_rule(self, rule_id: str) -> dict[str, Any]:
        """
        Fetches full details, rationale, and examples for a single rule ID.
        """
        rule = self.selector.get_rule(rule_id)
        if not rule:
            return {"error": {"code": "RULE_NOT_FOUND", "message": f"Rule '{rule_id}' does not exist", "hint": "Check rule ID spelling."}}

        return rule.model_dump(mode="json")

    def verify_project(
        self,
        root: str,
        scope: str = "changed",
        checks: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Executes deterministic verifiers (ruff, semgrep, tests, secrets) and returns structured report.
        """
        try:
            root_path = Path(root).resolve()
            verifier = Verifier(root_path)
            report = verifier.verify(scope=scope, checks=checks)
            return report.model_dump(mode="json")
        except Exception as e:
            return {"error": {"code": "VERIFICATION_ERROR", "message": str(e), "hint": "Check verifier configurations."}}
