from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template

from sarthi.core.models import ProjectConfig
from sarthi.core.security import fence_untrusted


class WorkflowEngine:
    """Loads, validates, and renders task workflows with active layers and project settings."""

    def __init__(self, workflows_dir: Path | str | None = None) -> None:
        if workflows_dir:
            self.workflows_dir = Path(workflows_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.workflows_dir = repo_root / "standards" / "workflows"

    def get_raw_workflow(self, task_type: str) -> tuple[dict[str, Any], str]:
        """Reads workflow frontmatter and markdown body for a task type."""
        file_path = self.workflows_dir / f"{task_type}.md"
        if not file_path.is_file():
            # Fallback to feature workflow if requested not found
            fallback_path = self.workflows_dir / "feature.md"
            if fallback_path.is_file():
                file_path = fallback_path
            else:
                return {"id": task_type, "requires_tools": ["get_standards", "verify_project"]}, (
                    "## 1. Plan\nCall get_standards(task, layers).\n"
                    "## 2. Implement\nApply standards.\n"
                    "## 3. Verify\nCall verify_project().\n"
                )

        content = file_path.read_text(encoding="utf-8")
        frontmatter: dict[str, Any] = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except Exception:
                    pass

        return frontmatter, body

    def render_workflow(
        self,
        task_type: str,
        active_layers: list[str],
        config: ProjectConfig | None = None,
    ) -> str:
        frontmatter, body = self.get_raw_workflow(task_type)

        # Context for rendering (project-derived commands are strictly fenced)
        verify_commands = config.verify.commands if config and config.verify.commands else {}
        fenced_commands = {k: fence_untrusted(v) for k, v in verify_commands.items()}
        context = {
            "task_type": task_type,
            "layers": active_layers,
            "commands": fenced_commands,
            "fail_on": config.verify.fail_on.value if config else "high",
        }

        try:
            rendered_body = Template(body).render(**context)
        except Exception:
            rendered_body = body

        output = f"# Workflow: {task_type.capitalize()}\n"
        if "requires_tools" in frontmatter:
            output += f"**Required Tools:** {', '.join(frontmatter['requires_tools'])}\n\n"
        output += rendered_body
        return output
