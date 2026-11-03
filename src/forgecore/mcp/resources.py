from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forgecore.core.rules import RuleLoader
    from forgecore.core.workflows import WorkflowEngine


class MCPResources:
    """Provides read-only MCP resources for standards, contracts, and workflows."""

    def __init__(self, standards_dir: Path | str | None = None) -> None:
        if standards_dir:
            self.standards_dir = Path(standards_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.standards_dir = repo_root / "standards"
        self._rule_loader: RuleLoader | None = None
        self._workflow_engine: WorkflowEngine | None = None

    @property
    def rule_loader(self) -> RuleLoader:
        if self._rule_loader is None:
            from forgecore.core.rules import RuleLoader

            self._rule_loader = RuleLoader(self.standards_dir)
        return self._rule_loader

    @property
    def workflow_engine(self) -> WorkflowEngine:
        if self._workflow_engine is None:
            from forgecore.core.workflows import WorkflowEngine

            self._workflow_engine = WorkflowEngine(self.standards_dir / "workflows")
        return self._workflow_engine

    def get_contract(self) -> str:
        contract_path = self.standards_dir / "contract.md"
        if contract_path.is_file():
            return contract_path.read_text(encoding="utf-8")
        return "# FORGECORE CORE CONTRACT\nAlways follow standards and verify before completion."

    def get_layer_standards(self, layer: str) -> str:
        all_rules = self.rule_loader.load_all_rules()
        layer_rules = [r for r in all_rules if r.layer == layer]
        return json.dumps([r.model_dump(mode="json") for r in layer_rules], indent=2)

    def get_workflow_template(self, task_type: str) -> str:
        _, body = self.workflow_engine.get_raw_workflow(task_type)
        return body
