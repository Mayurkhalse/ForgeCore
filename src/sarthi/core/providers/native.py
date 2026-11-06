"""Native knowledge provider managing Sarthi's 85 verified YAML standards and Core Contract."""
from __future__ import annotations

from pathlib import Path

from sarthi.core.models import Rule
from sarthi.core.resources.models import (
    Classification,
    CompatibilityStatus,
    EngineeringResource,
    PrecedenceTier,
    ResourceType,
    TrustLevel,
)
from sarthi.core.rules import RuleLoader


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "standards").is_dir() or (parent / "resources" / "ecc").is_dir():
            return parent
    return current.parent.parent.parent.parent


class SarthiNativeProvider:
    """Knowledge provider for Sarthi native standards library, Core Contract, and workflows."""

    def __init__(self, standards_dir: Path | str | None = None) -> None:
        if standards_dir:
            self.standards_dir = Path(standards_dir).resolve()
        else:
            repo_root = _find_repo_root()
            self.standards_dir = repo_root / "standards"

        self._resources: dict[str, EngineeringResource] = {}
        self._raw_rules: dict[str, Rule] = {}
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "native"

    @property
    def version(self) -> str:
        return "0.1.0"

    def initialize(self) -> None:
        if self._initialized:
            return

        loader = RuleLoader(self.standards_dir)
        raw_rules = loader.load_all_rules()

        # 1. Index Core Contract (Tier 3)
        contract_path = self.standards_dir / "contract.md"
        if contract_path.is_file():
            contract_content = contract_path.read_text(encoding="utf-8")
            self._resources["native.contract.core"] = EngineeringResource(
                id="native.contract.core",
                provider_id="native",
                type=ResourceType.RULE,
                classification=Classification.DIRECTLY_REUSABLE,
                name="Sarthi 16-Point Core Engineering Contract",
                description="Non-negotiable core engineering standards for all AI agent code generation.",
                category="architecture",
                source_path="standards/contract.md",
                source_version=self.version,
                source_commit="native",
                license="Proprietary / Sarthi Native",
                applicable_stacks=["all"],
                applicable_tasks=["all"],
                tags=["contract", "mandatory", "core"],
                compatibility=CompatibilityStatus.NATIVE,
                trust_level=TrustLevel.CORE_SECURITY,
                precedence_tier=int(PrecedenceTier.TIER_3_CORE_CONTRACT),
                priority=100,
                content_ref=str(contract_path),
                content_inline=contract_content,
            )

        # 2. Index 85 YAML Standards (Tier 5)
        for r in raw_rules:
            self._raw_rules[r.id] = r
            applicable_stacks = list(set([r.layer] + (r.applies_when.layers or [])))
            applicable_tasks = r.applies_when.tasks if r.applies_when.tasks else ["all"]
            required_tools = [r.verify.type.value] if r.verify else []

            content_text = (
                f"# {r.title} ({r.id})\n\n"
                f"**Layer:** {r.layer} | **Severity:** {r.severity.value} | **Category:** {r.category.value}\n\n"
                f"## Rule\n{r.rule.strip()}\n\n"
            )
            if r.rationale:
                content_text += f"## Rationale\n{r.rationale.strip()}\n\n"
            if r.good:
                content_text += f"## Good Example\n```\n{r.good.strip()}\n```\n\n"
            if r.bad:
                content_text += f"## Bad Example\n```\n{r.bad.strip()}\n```\n"

            res = EngineeringResource(
                id=r.id,
                provider_id="native",
                type=ResourceType.RULE,
                classification=Classification.DIRECTLY_REUSABLE,
                name=r.title,
                description=r.rationale or r.rule,
                category=r.category.value,
                source_path=f"standards/{r.layer}/{r.id}.yaml",
                source_version=r.since,
                source_commit="native",
                license="Proprietary / Sarthi Native",
                applicable_stacks=applicable_stacks,
                applicable_tasks=applicable_tasks,
                tags=r.tags,
                required_tools=required_tools,
                compatibility=CompatibilityStatus.NATIVE,
                trust_level=TrustLevel.VERIFIED_NATIVE,
                precedence_tier=int(PrecedenceTier.TIER_5_NATIVE_STANDARDS),
                priority=50 + (10 if r.layer not in ["universal", "security"] else 0),
                content_inline=content_text,
                supersedes=r.supersedes,
            )
            self._resources[r.id] = res

        # 3. Index Native Workflows
        wf_dir = self.standards_dir / "workflows"
        if wf_dir.is_dir():
            for wf_file in wf_dir.glob("*.md"):
                wf_id = f"native.workflow.{wf_file.stem}"
                wf_text = wf_file.read_text(encoding="utf-8")
                self._resources[wf_id] = EngineeringResource(
                    id=wf_id,
                    provider_id="native",
                    type=ResourceType.WORKFLOW,
                    classification=Classification.DIRECTLY_REUSABLE,
                    name=f"Workflow: {wf_file.stem.capitalize()}",
                    description=f"Standard Sarthi development lifecycle workflow for {wf_file.stem} tasks.",
                    category="workflow",
                    source_path=f"standards/workflows/{wf_file.name}",
                    source_version=self.version,
                    source_commit="native",
                    license="Proprietary / Sarthi Native",
                    applicable_stacks=["all"],
                    applicable_tasks=[wf_file.stem],
                    tags=["workflow", wf_file.stem],
                    compatibility=CompatibilityStatus.NATIVE,
                    trust_level=TrustLevel.VERIFIED_NATIVE,
                    precedence_tier=int(PrecedenceTier.TIER_5_NATIVE_STANDARDS),
                    priority=20,
                    content_ref=str(wf_file),
                    content_inline=wf_text,
                )

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
