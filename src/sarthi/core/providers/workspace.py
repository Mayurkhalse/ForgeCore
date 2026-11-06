"""Workspace knowledge provider discovering project-specific local rules and custom guidance."""
from __future__ import annotations

from pathlib import Path

import yaml

from sarthi.core.resources.models import (
    Classification,
    CompatibilityStatus,
    EngineeringResource,
    PrecedenceTier,
    ResourceType,
    TrustLevel,
)


class WorkspaceProvider:
    """Knowledge provider for project-specific rules in .sarthi/rules/ or .sarthi/rules/."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).resolve()
        self._resources: dict[str, EngineeringResource] = {}
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "workspace"

    @property
    def version(self) -> str:
        return "workspace-local"

    def initialize(self) -> None:
        if self._initialized:
            return

        rule_dirs = [
            self.project_root / ".sarthi" / "rules",
            self.project_root / ".sarthi" / "rules",
            self.project_root / ".sarthi" / "skills",
            self.project_root / ".sarthi" / "skills",
        ]

        for r_dir in rule_dirs:
            if not r_dir.is_dir():
                continue

            for file_path in r_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                if file_path.suffix in [".yaml", ".yml"]:
                    try:
                        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
                        if isinstance(data, dict) and "id" in data:
                            r_id = f"workspace.{data['id']}"
                            res = EngineeringResource(
                                id=r_id,
                                provider_id="workspace",
                                type=ResourceType.RULE,
                                classification=Classification.DIRECTLY_REUSABLE,
                                name=data.get("title", file_path.stem),
                                description=data.get("rationale", data.get("rule", "")),
                                category=data.get("category", "project_standard"),
                                source_path=file_path.relative_to(self.project_root).as_posix(),
                                source_version="workspace",
                                source_commit="local",
                                license="Project Internal",
                                applicable_stacks=data.get("layers", ["all"]),
                                applicable_tasks=data.get("tasks", ["all"]),
                                tags=data.get("tags", ["workspace"]),
                                compatibility=CompatibilityStatus.NATIVE,
                                trust_level=TrustLevel.WORKSPACE_LOCAL,
                                precedence_tier=int(PrecedenceTier.TIER_4_PROJECT_CONFIG),
                                priority=40,
                                content_inline=str(data.get("rule", "")),
                                supersedes=data.get("supersedes", []),
                            )
                            self._resources[r_id] = res
                    except Exception:
                        pass
                elif file_path.suffix == ".md":
                    try:
                        raw_text = file_path.read_text(encoding="utf-8")
                        r_id = f"workspace.{file_path.stem}"
                        res = EngineeringResource(
                            id=r_id,
                            provider_id="workspace",
                            type=ResourceType.SKILL if "skill" in str(file_path) else ResourceType.RULE,
                            classification=Classification.DIRECTLY_REUSABLE,
                            name=file_path.stem.replace("-", " ").title(),
                            description=f"Workspace custom guidance from {file_path.name}",
                            category="project_custom",
                            source_path=file_path.relative_to(self.project_root).as_posix(),
                            source_version="workspace",
                            source_commit="local",
                            license="Project Internal",
                            applicable_stacks=["all"],
                            applicable_tasks=["all"],
                            tags=["workspace", "custom"],
                            compatibility=CompatibilityStatus.NATIVE,
                            trust_level=TrustLevel.WORKSPACE_LOCAL,
                            precedence_tier=int(PrecedenceTier.TIER_4_PROJECT_CONFIG),
                            priority=40,
                            content_inline=raw_text,
                        )
                        self._resources[r_id] = res
                    except Exception:
                        pass

        self._initialized = True

    def list_resources(
        self,
        resource_type: ResourceType | None = None,
    ) -> list[EngineeringResource]:
        self.initialize()
        if resource_type is None:
            return list(self._resources.values())
        return [r for r in self._resources.values() if r.type == resource_type]

    def get_resource(self, resource_id: str) -> EngineeringResource | None:
        self.initialize()
        return self._resources.get(resource_id)

    def get_content(self, resource: EngineeringResource) -> str:
        self.initialize()
        if resource.content_inline:
            return resource.content_inline
        if resource.content_ref and Path(resource.content_ref).is_file():
            return Path(resource.content_ref).read_text(encoding="utf-8")
        return ""
