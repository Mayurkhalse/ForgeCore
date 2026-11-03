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

    def generate_summary_table(self) -> str:
        """Generates a Markdown table summarizing total rules and machine verifiers per layer."""
        from collections import defaultdict

        from forgecore.core.models import VerifierType
        from forgecore.core.rules import RuleLoader

        loader = RuleLoader(self.standards_dir)
        rules = loader.load_all_rules()

        layer_rules: dict[str, list[Rule]] = defaultdict(list)
        for r in rules:
            layer_rules[r.layer].append(r)

        cross_cutting = ["universal", "security", "testing", "api-design", "observability"]
        stack_layers = ["react", "fastapi", "node-express", "react-native", "spring-boot", "python-ml"]
        all_layers = cross_cutting + [lyr for lyr in stack_layers if lyr not in cross_cutting]
        for lyr in sorted(layer_rules.keys()):
            if lyr not in all_layers:
                all_layers.append(lyr)

        lines = [
            "| Layer / Stack | Total Rules | Machine Verifiers | Status in v0.1 |",
            "|---|---|---|---|",
        ]

        for layer in all_layers:
            r_list = layer_rules.get(layer, [])
            total = len(r_list)

            # Count machine verifiers
            machine_counts: dict[str, int] = defaultdict(int)
            for r in r_list:
                if r.verify and r.verify.type in (
                    VerifierType.SEMGREP,
                    VerifierType.RUFF,
                    VerifierType.ESLINT,
                    VerifierType.SECRETS,
                    VerifierType.PYTEST_MARKER,
                    VerifierType.COMMAND,
                ):
                    v_type = r.verify.type.value
                    if v_type == "semgrep":
                        machine_counts["Semgrep"] += 1
                    elif v_type == "ruff":
                        machine_counts["Ruff"] += 1
                    elif v_type == "eslint":
                        machine_counts["ESLint"] += 1
                    elif v_type == "secrets":
                        machine_counts["Secrets"] += 1
                    else:
                        machine_counts[v_type.capitalize()] += 1

            total_machine = sum(machine_counts.values())

            if total_machine > 0:
                details = ", ".join(
                    f"{count} {name}" if len(machine_counts) > 1 else name
                    for name, count in machine_counts.items()
                )
                verifiers_str = f"{total_machine} ({details})"
            else:
                verifiers_str = "0 (guidance / checklist)"

            if layer in cross_cutting:
                status_str = "**Cross-cutting**"
            else:
                if total >= 12 and total_machine >= 5:
                    status_str = "**Stable**"
                else:
                    missing = max(0, 5 - total_machine)
                    status_str = f"**Experimental** (missing {missing} verifier{'s' if missing != 1 else ''})"

            lines.append(f"| `{layer}` | {total} | {verifiers_str} | {status_str} |")

        return "\n".join(lines)
