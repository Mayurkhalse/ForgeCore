from __future__ import annotations

from pathlib import Path

from forgecore.core.detectors import ALL_DETECTORS
from forgecore.core.detectors.base import SKIP_DIRS
from forgecore.core.models import DetectedLayer, StackProfile
from forgecore.core.pathguard import PathGuard

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".html": "html",
    ".css": "css",
}

PACKAGE_MANAGERS = {
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lockb": "bun",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "Cargo.lock": "cargo",
    "go.sum": "go-modules",
}

TEST_FRAMEWORKS_INDICATORS = {
    "pytest": ["pytest.ini", "conftest.py", "test_*.py", "*_test.py"],
    "jest": ["jest.config.js", "jest.config.ts"],
    "vitest": ["vitest.config.ts", "vitest.config.js"],
    "junit": ["*Test.java", "*Tests.java", "*Test.kt"],
}


class StackDetector:
    """Discovers project languages, package managers, test frameworks, and framework layers."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.pathguard = PathGuard(self.root)

    def scan_files(self, max_depth: int = 6) -> list[Path]:
        found: list[Path] = []

        def _walk(curr: Path, depth: int):
            try:
                for item in curr.iterdir():
                    if item.name in SKIP_DIRS or item.name.startswith("."):
                        continue
                    if item.is_file():
                        found.append(item)
                    elif item.is_dir() and depth > 1:
                        _walk(item, depth - 1)
            except (PermissionError, FileNotFoundError):
                pass

        _walk(self.root, max_depth)
        return found

    def detect_languages(self, files: list[Path]) -> list[str]:
        langs = set()
        for f in files:
            ext = f.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                langs.add(LANGUAGE_EXTENSIONS[ext])
        return sorted(list(langs))

    def detect_package_managers(self, files: list[Path]) -> list[str]:
        pms = set()
        file_names = {f.name for f in files}
        for manifest, pm in PACKAGE_MANAGERS.items():
            if manifest in file_names:
                pms.add(pm)
        # Default python pip check if requirements.txt exists and no lockfile
        if not pms and any(f.name.startswith("requirements") for f in files):
            pms.add("pip")
        return sorted(list(pms))

    def detect_test_frameworks(self, files: list[Path]) -> list[str]:
        frameworks = set()
        file_names = [f.name for f in files]
        for tf, indicators in TEST_FRAMEWORKS_INDICATORS.items():
            for pattern in indicators:
                if any(Path(fn).match(pattern) for fn in file_names):
                    frameworks.add(tf)
                    break
        return sorted(list(frameworks))

    def detect_stack(self) -> StackProfile:
        files = self.scan_files(max_depth=6)
        languages = self.detect_languages(files)
        package_managers = self.detect_package_managers(files)
        test_frameworks = self.detect_test_frameworks(files)

        detected_layers: list[DetectedLayer] = []
        confidences: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}

        for detector_cls in ALL_DETECTORS:
            detector = detector_cls()
            layer = detector.detect(self.root)
            if layer:
                detected_layers.append(layer)
                confidences[layer.name] = layer.confidence
                evidence[layer.name] = layer.evidence

        suggested_profile = self._infer_profile([layer.name for layer in detected_layers])

        return StackProfile(
            root=self.root,
            layers=detected_layers,
            languages=languages,
            package_managers=package_managers,
            test_frameworks=test_frameworks,
            confidence=confidences,
            evidence=evidence,
            suggested_profile=suggested_profile,
        )

    def _infer_profile(self, layers: list[str]) -> str | None:
        layer_set = set(layers)
        if "react" in layer_set and "fastapi" in layer_set:
            return "react-fastapi"
        if "react" in layer_set and "node-express" in layer_set:
            return "react-node"
        if "react-native" in layer_set:
            return "react-native"
        if "spring-boot" in layer_set:
            return "java-springboot"
        if "python-ml" in layer_set:
            return "python-ml"
        if "fastapi" in layer_set:
            return "react-fastapi"  # closest default profile
        if "node-express" in layer_set:
            return "react-node"
        if "react" in layer_set:
            return "react-node"
        return None
