"""Bundled ECC knowledge provider managing Everything Claude Code (v2.2.3 @ c05b2d6) catalog."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forgecore.core.resources.models import (
    Classification,
    CompatibilityStatus,
    EngineeringResource,
    PrecedenceTier,
    ResourceType,
    TrustLevel,
)

STACK_KEYWORDS = {
    "fastapi": ["fastapi", "uvicorn", "starlette", "pydantic"],
    "django": ["django", "django-rest-framework", "drf"],
    "flask": ["flask", "werkzeug"],
    "spring": ["spring", "spring boot", "java", "maven", "gradle"],
    "node": ["node", "nodejs", "npm", "pnpm", "yarn", "express"],
    "php": ["php", "laravel", "symfony", "composer"],
    "ruby": ["ruby", "rails", "gem", "bundler"],
    "react": ["react", "jsx", "tsx", "frontend", "components"],
    "react-native": ["react-native", "react native", "expo"],
    "mobile": ["android", "ios", "flutter", "kotlin", "swift", "kmp"],
    "python": ["python", "pytest", "ruff", "pip", "uv", "poetry"],
    "python-ml": ["machine learning", "pytorch", "tensorflow", "scikit-learn", "numpy", "pandas"],
    "typescript": ["typescript", "ts"],
    "golang": ["golang", "go"],
    "rust": ["rust", "cargo"],
    "postgres": ["postgres", "postgresql", "psycopg", "pg"],
    "mysql": ["mysql", "mariadb"],
    "sql": ["sql", "database", "orm", "alembic", "db"],
    "docker": ["docker", "container", "dockerfile"],
    "universal": ["universal", "clean-code", "refactoring", "tdd-workflow"],
}


def _detect_stacks(name: str, desc: str, tags: list[str]) -> list[str]:
    import re
    text = f"{name} {desc} {' '.join(tags)}".lower()
    detected = set()
    for stack, keywords in STACK_KEYWORDS.items():
        for kw in keywords:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text):
                detected.add(stack)
                break
    return sorted(list(detected)) if detected else ["all"]


def _detect_tasks(name: str, desc: str) -> list[str]:
    text = f"{name} {desc}".lower()
    tasks = set()
    if any(w in text for w in ["tdd", "test", "testing", "spec"]):
        tasks.update(["feature", "bugfix", "refactor"])
    if any(w in text for w in ["bug", "fix", "troubleshoot", "debug", "error"]):
        tasks.add("bugfix")
    if any(w in text for w in ["refactor", "cleanup", "moderniz", "optimize"]):
        tasks.add("refactor")
    if any(w in text for w in ["review", "audit", "inspect"]):
        tasks.add("review")
    if any(w in text for w in ["plan", "architecture", "feature", "build", "create", "implement"]):
        tasks.add("feature")
    return sorted(list(tasks)) if tasks else ["all"]


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "resources" / "ecc").is_dir() or (parent / "standards").is_dir():
            return parent
    return current.parent.parent.parent.parent


class ECCBundledProvider:
    """Knowledge provider for the locally bundled Everything Claude Code (ECC) snapshot."""

    def __init__(self, ecc_dir: Path | str | None = None) -> None:
        if ecc_dir:
            self.ecc_dir = Path(ecc_dir).resolve()
        else:
            repo_root = _find_repo_root()
            self.ecc_dir = repo_root / "resources" / "ecc"

        self._resources: dict[str, EngineeringResource] = {}
        self._inventory_entries: list[dict[str, Any]] = []
        self._manifest_data: dict[str, Any] = {}
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "ecc"

    @property
    def version(self) -> str:
        return "2.2.3"

    @property
    def commit(self) -> str:
        return "c05b2d6614f62f6db0047669aa4eefb223d478f9"

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    data = yaml.safe_load(parts[1])
                    return data if isinstance(data, dict) else {}, parts[2].strip()
                except Exception:
                    pass
        return {}, text.strip()

    def initialize(self) -> None:
        if self._initialized:
            return

        manifest_path = self.ecc_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                self._manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                self._manifest_data = {}

        inv_path = self.ecc_dir / "inventory.json"
        if inv_path.is_file():
            try:
                self._inventory_entries = json.loads(inv_path.read_text(encoding="utf-8"))
            except Exception:
                self._inventory_entries = []

        # 1. Index Skills
        skills_dir = self.ecc_dir / "skills"
        if skills_dir.is_dir():
            for s_dir in skills_dir.iterdir():
                if not s_dir.is_dir():
                    continue
                skill_file = s_dir / "SKILL.md"
                if not skill_file.is_file():
                    continue

                raw_text = skill_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(raw_text)
                name = fm.get("name", s_dir.name)
                desc = fm.get("description", "")
                skill_id = f"ecc.skill.{name}"
                stacks = _detect_stacks(name, desc, [])
                tasks = _detect_tasks(name, desc)

                # Check for associated scripts
                scripts = []
                for sc in s_dir.rglob("*"):
                    if sc.is_file() and sc.suffix in [".py", ".sh", ".js"]:
                        scripts.append(sc.relative_to(self.ecc_dir).as_posix())

                self._resources[skill_id] = EngineeringResource(
                    id=skill_id,
                    provider_id="ecc",
                    type=ResourceType.SKILL,
                    classification=Classification.DIRECTLY_REUSABLE,
                    name=name.replace("-", " ").title(),
                    description=desc,
                    category="procedural_skill",
                    source_path=f"skills/{s_dir.name}/SKILL.md",
                    source_version=self.version,
                    source_commit=self.commit,
                    license="MIT",
                    applicable_stacks=stacks,
                    applicable_tasks=tasks,
                    tags=["ecc", "skill", s_dir.name],
                    dependencies=scripts,
                    compatibility=CompatibilityStatus.NATIVE,
                    trust_level=TrustLevel.BUNDLED_ECC,
                    precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                    priority=25,
                    content_ref=str(skill_file),
                    content_inline=raw_text,
                )

        # 2. Index Rules
        rules_dir = self.ecc_dir / "rules"
        if rules_dir.is_dir():
            for r_file in rules_dir.rglob("*.md"):
                rel = r_file.relative_to(rules_dir)
                parts = rel.parts
                lang = parts[0] if len(parts) > 1 else "universal"
                stem = r_file.stem
                if stem == "README":
                    continue

                rule_id = f"ecc.rule.{lang}.{stem}"
                raw_text = r_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(raw_text)
                paths = fm.get("paths", [])

                stacks = [lang] if lang != "common" else ["all"]
                if stem in STACK_KEYWORDS:
                    stacks.append(stem)

                self._resources[rule_id] = EngineeringResource(
                    id=rule_id,
                    provider_id="ecc",
                    type=ResourceType.RULE,
                    classification=Classification.DIRECTLY_REUSABLE,
                    name=f"ECC {lang.capitalize()} {stem.capitalize()} Rules",
                    description=f"ECC coding standards and domain guidance for {lang} ({stem}).",
                    category="coding_standard",
                    source_path=f"rules/{rel.as_posix()}",
                    source_version=self.version,
                    source_commit=self.commit,
                    license="MIT",
                    applicable_stacks=stacks,
                    applicable_tasks=["all"],
                    tags=["ecc", "rule", lang, stem],
                    compatibility=CompatibilityStatus.NATIVE,
                    trust_level=TrustLevel.BUNDLED_ECC,
                    precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                    priority=15,
                    content_ref=str(r_file),
                    content_inline=raw_text,
                    activation_conditions={"paths": paths} if paths else {},
                )

        # 3. Index Commands
        commands_dir = self.ecc_dir / "commands"
        if commands_dir.is_dir():
            for c_file in commands_dir.glob("*.md"):
                cmd_id = f"ecc.command.{c_file.stem}"
                raw_text = c_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(raw_text)
                desc = fm.get("description", "")
                stacks = _detect_stacks(c_file.stem, desc, [])
                tasks = _detect_tasks(c_file.stem, desc)

                self._resources[cmd_id] = EngineeringResource(
                    id=cmd_id,
                    provider_id="ecc",
                    type=ResourceType.COMMAND,
                    classification=Classification.REQUIRES_ADAPTER,
                    name=f"/{c_file.stem}",
                    description=desc,
                    category="command_template",
                    source_path=f"commands/{c_file.name}",
                    source_version=self.version,
                    source_commit=self.commit,
                    license="MIT",
                    applicable_stacks=stacks,
                    applicable_tasks=tasks,
                    tags=["ecc", "command", c_file.stem],
                    compatibility=CompatibilityStatus.ADAPTED,
                    trust_level=TrustLevel.BUNDLED_ECC,
                    precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                    priority=20,
                    content_ref=str(c_file),
                    content_inline=raw_text,
                )

        # 4. Index Agents
        agents_dir = self.ecc_dir / "agents"
        if agents_dir.is_dir():
            for a_file in agents_dir.glob("*.md"):
                agent_id = f"ecc.agent.{a_file.stem}"
                raw_text = a_file.read_text(encoding="utf-8")
                fm, body = self._parse_frontmatter(raw_text)
                desc = fm.get("description", "")
                tools_req = fm.get("tools", "")
                tools_list = [t.strip() for t in tools_req.split(",") if t.strip()] if tools_req else []
                stacks = _detect_stacks(a_file.stem, desc, [])
                tasks = _detect_tasks(a_file.stem, desc)

                self._resources[agent_id] = EngineeringResource(
                    id=agent_id,
                    provider_id="ecc",
                    type=ResourceType.AGENT,
                    classification=Classification.REQUIRES_ADAPTER,
                    name=fm.get("name", a_file.stem).replace("-", " ").title(),
                    description=desc,
                    category="agent_persona",
                    source_path=f"agents/{a_file.name}",
                    source_version=self.version,
                    source_commit=self.commit,
                    license="MIT",
                    applicable_stacks=stacks,
                    applicable_tasks=tasks,
                    tags=["ecc", "agent", a_file.stem],
                    required_tools=tools_list,
                    compatibility=CompatibilityStatus.ADAPTED,
                    trust_level=TrustLevel.BUNDLED_ECC,
                    precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                    priority=20,
                    content_ref=str(a_file),
                    content_inline=raw_text,
                )

        # 5. Index Contexts
        ctx_dir = self.ecc_dir / "contexts"
        if ctx_dir.is_dir():
            for ctx_file in ctx_dir.glob("*.md"):
                ctx_id = f"ecc.context.{ctx_file.stem}"
                raw_text = ctx_file.read_text(encoding="utf-8")
                self._resources[ctx_id] = EngineeringResource(
                    id=ctx_id,
                    provider_id="ecc",
                    type=ResourceType.CONTEXT,
                    classification=Classification.DIRECTLY_REUSABLE,
                    name=f"Context: {ctx_file.stem.capitalize()}",
                    description=f"ECC engineering reference context for {ctx_file.stem} workflows.",
                    category="reference_context",
                    source_path=f"contexts/{ctx_file.name}",
                    source_version=self.version,
                    source_commit=self.commit,
                    license="MIT",
                    applicable_stacks=["all"],
                    applicable_tasks=["all"],
                    tags=["ecc", "context", ctx_file.stem],
                    compatibility=CompatibilityStatus.NATIVE,
                    trust_level=TrustLevel.BUNDLED_ECC,
                    precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                    priority=10,
                    content_ref=str(ctx_file),
                    content_inline=raw_text,
                )

        # 6. Index Workflows
        wf_dir = self.ecc_dir / "workflows"
        if wf_dir.is_dir():
            for wf_file in wf_dir.iterdir():
                if wf_file.is_file() and wf_file.name != "README.md":
                    wf_id = f"ecc.workflow.{wf_file.stem}"
                    raw_text = wf_file.read_text(encoding="utf-8")
                    self._resources[wf_id] = EngineeringResource(
                        id=wf_id,
                        provider_id="ecc",
                        type=ResourceType.WORKFLOW,
                        classification=Classification.REQUIRES_UNSUPPORTED_CAPABILITY
                        if wf_file.suffix == ".js"
                        else Classification.REQUIRES_ADAPTER,
                        name=f"Workflow: {wf_file.stem.replace('.', ' ').capitalize()}",
                        description="ECC native workflow orchestration script.",
                        category="orchestration_workflow",
                        source_path=f"workflows/{wf_file.name}",
                        source_version=self.version,
                        source_commit=self.commit,
                        license="MIT",
                        applicable_stacks=["all"],
                        applicable_tasks=["all"],
                        tags=["ecc", "workflow", wf_file.stem],
                        compatibility=CompatibilityStatus.HOST_DEPENDENT
                        if wf_file.suffix == ".js"
                        else CompatibilityStatus.ADAPTED,
                        trust_level=TrustLevel.BUNDLED_ECC,
                        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                        priority=15,
                        content_ref=str(wf_file),
                        content_inline=raw_text,
                    )

        # 7. Index Passive Scripts (ADR-009)
        sc_dir = self.ecc_dir / "scripts"
        if sc_dir.is_dir():
            for sc_file in sc_dir.iterdir():
                if sc_file.is_file() and sc_file.name != "README.md":
                    sc_id = f"ecc.script.{sc_file.stem}"
                    raw_text = sc_file.read_text(encoding="utf-8")
                    self._resources[sc_id] = EngineeringResource(
                        id=sc_id,
                        provider_id="ecc",
                        type=ResourceType.SUPPORTING,
                        classification=Classification.DOCUMENTATION_ONLY,
                        name=f"Script: {sc_file.name}",
                        description="Passive reference script asset. ZERO RUNTIME EXECUTION AUTHORIZATION (ADR-009).",
                        category="reference_script",
                        source_path=f"scripts/{sc_file.name}",
                        source_version=self.version,
                        source_commit=self.commit,
                        license="MIT",
                        applicable_stacks=["all"],
                        applicable_tasks=["all"],
                        tags=["ecc", "script", "passive"],
                        compatibility=CompatibilityStatus.DEFERRED,
                        trust_level=TrustLevel.BUNDLED_ECC,
                        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                        priority=5,
                        content_ref=str(sc_file),
                        content_inline=raw_text,
                    )

        # 8. Index Deferred Upstream Inventory Items (No silent omissions!)
        for entry in self._inventory_entries:
            if entry.get("decision") == "defer":
                up_path = entry.get("upstream_path", "")
                res_type_str = entry.get("resource_type", "supporting")
                res_type = ResourceType(res_type_str) if res_type_str in [r.value for r in ResourceType] else ResourceType.SUPPORTING
                entry_id = f"ecc.deferred.{up_path.replace('/', '.').replace('-', '_')}"
                if entry_id not in self._resources:
                    self._resources[entry_id] = EngineeringResource(
                        id=entry_id,
                        provider_id="ecc",
                        type=res_type,
                        classification=Classification.REQUIRES_UNSUPPORTED_CAPABILITY
                        if res_type == ResourceType.HOOK
                        else Classification.REQUIRES_ADAPTER,
                        name=f"Deferred: {Path(up_path).name}",
                        description=entry.get("reason", "Deferred from active bundle."),
                        category="deferred_upstream",
                        source_path=up_path,
                        source_version=self.version,
                        source_commit=self.commit,
                        license="MIT",
                        applicable_stacks=["all"],
                        applicable_tasks=["all"],
                        tags=["ecc", "deferred", res_type_str],
                        compatibility=CompatibilityStatus.DEFERRED,
                        trust_level=TrustLevel.BUNDLED_ECC,
                        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
                        priority=0,
                        content_inline="",
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
