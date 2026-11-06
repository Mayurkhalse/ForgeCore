from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def weight(self) -> int:
        levels = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
        }
        return levels[self]

    def __ge__(self, other: Severity | str) -> bool:
        if isinstance(other, str):
            other = Severity(other.lower())
        return self.weight() >= other.weight()

    def __gt__(self, other: Severity | str) -> bool:
        if isinstance(other, str):
            other = Severity(other.lower())
        return self.weight() > other.weight()

    def __le__(self, other: Severity | str) -> bool:
        if isinstance(other, str):
            other = Severity(other.lower())
        return self.weight() <= other.weight()

    def __lt__(self, other: Severity | str) -> bool:
        if isinstance(other, str):
            other = Severity(other.lower())
        return self.weight() < other.weight()


class Category(str, Enum):
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    TESTING = "testing"
    API = "api"
    DATA = "data"
    PERF = "perf"
    OPS = "ops"


class Tier(str, Enum):
    CORE = "core"
    STANDARD = "standard"
    REFERENCE = "reference"

    def rank(self) -> int:
        ranks = {Tier.CORE: 3, Tier.STANDARD: 2, Tier.REFERENCE: 1}
        return ranks[self]


class VerifierType(str, Enum):
    SEMGREP = "semgrep"
    RUFF = "ruff"
    ESLINT = "eslint"
    COMMAND = "command"
    PYTEST_MARKER = "pytest-marker"
    CHECKLIST = "checklist"
    SECRETS = "secrets"


class RuleVerifier(BaseModel):
    type: VerifierType
    ref: str | None = None
    command: str | None = None
    prompt: str | None = None


class RuleAppliesWhen(BaseModel):
    layers: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)


class Rule(BaseModel):
    id: str
    title: str
    layer: str
    category: Category
    severity: Severity
    tier: Tier = Tier.STANDARD
    applies_when: RuleAppliesWhen = Field(default_factory=RuleAppliesWhen)
    rule: str
    rationale: str = ""
    good: str = ""
    bad: str = ""
    verify: RuleVerifier | None = None
    supersedes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    since: str = "0.1.0"


class DetectedLayer(BaseModel):
    name: str
    version: str | None = None
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)


class StackProfile(BaseModel):
    root: Path
    layers: list[DetectedLayer] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    suggested_profile: str | None = None

    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]


class RuleOverride(BaseModel):
    id: str
    severity: Severity | None = None
    disabled: bool = False
    reason: str | None = None


class GenerationConfig(BaseModel):
    require_plan: bool = True
    require_tests: bool = True


class VerifyConfig(BaseModel):
    fail_on: Severity = Severity.HIGH
    commands: dict[str, str] = Field(default_factory=dict)


class LayersConfig(BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class RulesConfig(BaseModel):
    disable: list[str] = Field(default_factory=list)
    overrides: list[RuleOverride] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    version: int = 1
    project: dict[str, Any] = Field(default_factory=dict)
    profile: str | None = None
    layers: LayersConfig = Field(default_factory=LayersConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    file: str
    line: int = 0
    message: str
    recommendation: str = ""
    verifier: str = ""
    fix_hint: str = ""


class ChecklistItem(BaseModel):
    rule_id: str
    prompt: str


class SkippedCheck(BaseModel):
    check: str
    reason: str
    required: bool = True


class VerifyReport(BaseModel):
    status: Literal["passed", "failed", "incomplete"]
    context_version: int = 1
    summary: dict[str, int] = Field(default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0})
    findings: list[Finding] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    skipped: list[SkippedCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""


class RunContext(BaseModel):
    project_root: Path
    active_layers: list[str] = Field(default_factory=list)
    changed_files: list[Path] = Field(default_factory=list)
    config: ProjectConfig = Field(default_factory=ProjectConfig)
    deadline: float | None = None
