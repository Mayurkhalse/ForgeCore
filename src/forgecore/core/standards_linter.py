from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from forgecore.core.models import Rule

KNOWN_LAYERS = {
    "universal",
    "security",
    "testing",
    "api-design",
    "observability",
    "react",
    "react-native",
    "node-express",
    "fastapi",
    "spring-boot",
    "python-ml",
}


class StandardsLintError:
    def __init__(self, file: str, message: str, rule_id: str | None = None) -> None:
        self.file = file
        self.message = message
        self.rule_id = rule_id

    def __str__(self) -> str:
        r = f"[{self.rule_id}] " if self.rule_id else ""
        return f"{self.file}: {r}{self.message}"


class StandardsLinter:
    """Validates the entire standards library against schemas and reference constraints."""

    def __init__(self, standards_dir: Path | str | None = None) -> None:
        if standards_dir:
            self.standards_dir = Path(standards_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.standards_dir = repo_root / "standards"

    def lint(self) -> list[StandardsLintError]:
        errors: list[StandardsLintError] = []
        rule_ids: dict[str, str] = {}  # id -> file

        if not self.standards_dir.is_dir():
            errors.append(StandardsLintError(str(self.standards_dir), "Standards directory not found"))
            return errors

        # 1. Validate contract.md
        contract_file = self.standards_dir / "contract.md"
        if not contract_file.is_file():
            errors.append(StandardsLintError("standards/contract.md", "Core Contract file missing"))

        # 2. Validate profiles
        profiles_dir = self.standards_dir / "profiles"
        if profiles_dir.is_dir():
            for p_file in profiles_dir.glob("*.yaml"):
                rel = str(p_file.relative_to(self.standards_dir.parent)).replace("\\", "/")
                try:
                    data = yaml.safe_load(p_file.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        errors.append(StandardsLintError(rel, "Profile YAML must be a mapping"))
                        continue
                    if "id" not in data or "layers" not in data:
                        errors.append(StandardsLintError(rel, "Profile must specify 'id' and 'layers'"))
                    for layer in data.get("layers", []):
                        if layer not in KNOWN_LAYERS:
                            errors.append(StandardsLintError(rel, f"Profile references unknown layer '{layer}'"))
                except Exception as e:
                    errors.append(StandardsLintError(rel, f"YAML parse error: {e}"))

        # 3. Validate workflows
        workflows_dir = self.standards_dir / "workflows"
        if workflows_dir.is_dir():
            for w_file in workflows_dir.glob("*.md"):
                rel = str(w_file.relative_to(self.standards_dir.parent)).replace("\\", "/")
                content = w_file.read_text(encoding="utf-8")
                if not content.startswith("---"):
                    errors.append(StandardsLintError(rel, "Workflow missing YAML frontmatter"))

        # 4. Validate rules
        for yaml_file in self.standards_dir.rglob("*.yaml"):
            rel_parts = yaml_file.relative_to(self.standards_dir).parts
            if "profiles" in rel_parts or "verifiers" in rel_parts:
                continue

            rel_path = str(yaml_file.relative_to(self.standards_dir.parent)).replace("\\", "/")
            try:
                content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(StandardsLintError(rel_path, f"YAML parse error: {e}"))
                continue

            items: list[Any] = content if isinstance(content, list) else [content]
            for item in items:
                if not isinstance(item, dict):
                    errors.append(StandardsLintError(rel_path, f"Rule entry must be a dictionary, got {type(item)}"))
                    continue

                r_id = item.get("id")
                if not r_id:
                    errors.append(StandardsLintError(rel_path, "Rule missing required field 'id'"))
                    continue

                # Check uniqueness
                if r_id in rule_ids:
                    errors.append(
                        StandardsLintError(
                            rel_path,
                            f"Duplicate rule ID '{r_id}', previously declared in {rule_ids[r_id]}",
                            rule_id=r_id,
                        )
                    )
                else:
                    rule_ids[r_id] = rel_path

                # Pydantic validation
                try:
                    rule = Rule.model_validate(item)
                except ValidationError as ve:
                    for err in ve.errors():
                        loc = ".".join(str(part) for part in err["loc"])
                        errors.append(
                            StandardsLintError(
                                rel_path,
                                f"Schema validation error on field '{loc}': {err['msg']}",
                                rule_id=r_id,
                            )
                        )
                    continue

                # Check layer
                if rule.layer not in KNOWN_LAYERS:
                    errors.append(
                        StandardsLintError(
                            rel_path,
                            f"Unknown layer '{rule.layer}' in rule definition",
                            rule_id=r_id,
                        )
                    )

                # Check verifier file reference if specified
                if rule.verify and rule.verify.ref:
                    repo_root = self.standards_dir.parent
                    ref_path = (repo_root / rule.verify.ref).resolve()
                    if not ref_path.is_file():
                        errors.append(
                            StandardsLintError(
                                rel_path,
                                f"Verifier reference file '{rule.verify.ref}' does not exist",
                                rule_id=r_id,
                            )
                        )

        return errors
