from __future__ import annotations

import hashlib
import json
from pathlib import Path

from forgecore.core.config import ConfigLoader
from forgecore.core.models import ProjectConfig, StackProfile
from forgecore.core.pathguard import PathGuard
from forgecore.core.stack_detector import StackDetector

MANIFEST_PATTERNS = [
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements*.txt",
    "Pipfile",
    "Pipfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    ".forgecore/project.yaml",
]


class ContextBuilder:
    """Manages project fingerprinting, cached context state, and auto-refresh."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.pathguard = PathGuard(self.root)
        self.forgecore_dir = self.root / ".forgecore"
        self.cache_dir = self.forgecore_dir / "cache"
        self.config_loader = ConfigLoader(self.root)
        self.stack_detector = StackDetector(self.root)

    def _ensure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Ensure .forgecore/.gitignore exists ignoring cache/
        gitignore_path = self.forgecore_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("cache/\n", encoding="utf-8")

    def compute_manifest_fingerprints(self) -> dict[str, str]:
        """Calculates SHA256 hashes of all manifest files in the project."""
        fingerprints: dict[str, str] = {}
        for pattern in MANIFEST_PATTERNS:
            if "/" in pattern:
                p = self.root / pattern
                if p.is_file():
                    rel = str(p.relative_to(self.root)).replace("\\", "/")
                    h = hashlib.sha256(p.read_bytes()).hexdigest()
                    fingerprints[rel] = h
            else:
                for match in self.root.glob(pattern):
                    if match.is_file():
                        rel = str(match.relative_to(self.root)).replace("\\", "/")
                        h = hashlib.sha256(match.read_bytes()).hexdigest()
                        fingerprints[rel] = h
        return fingerprints

    def is_stale(self, current_fingerprints: dict[str, str]) -> bool:
        fingerprint_file = self.cache_dir / "fingerprint.json"
        if not fingerprint_file.is_file():
            return True

        try:
            cached = json.loads(fingerprint_file.read_text(encoding="utf-8"))
            cached_fps = cached.get("fingerprints", {})
            return cached_fps != current_fingerprints
        except Exception:
            return True

    def build_context(self, force: bool = False) -> tuple[StackProfile, ProjectConfig, int, bool]:
        """
        Builds or loads cached context.
        Returns: (StackProfile, ProjectConfig, context_version, was_refreshed).
        """
        self._ensure_cache_dir()
        current_fps = self.compute_manifest_fingerprints()
        fingerprint_file = self.cache_dir / "fingerprint.json"
        stack_file = self.cache_dir / "stack.json"

        version = 1
        stale = force or self.is_stale(current_fps)

        if not stale and stack_file.is_file() and fingerprint_file.is_file():
            try:
                cached_meta = json.loads(fingerprint_file.read_text(encoding="utf-8"))
                version = cached_meta.get("version", 1)
                stack_data = json.loads(stack_file.read_text(encoding="utf-8"))
                profile = StackProfile.model_validate(stack_data)
                config = self.config_loader.load()
                return profile, config, version, False
            except Exception:
                pass  # Recompute on corruption

        # Re-detect stack
        if fingerprint_file.is_file():
            try:
                prev_meta = json.loads(fingerprint_file.read_text(encoding="utf-8"))
                version = prev_meta.get("version", 0) + 1
            except Exception:
                version = 1

        profile = self.stack_detector.detect_stack()
        config = self.config_loader.load()

        # Update cache files
        stack_dump = profile.model_dump(mode="json")
        stack_file.write_text(json.dumps(stack_dump, indent=2), encoding="utf-8")

        meta = {
            "version": version,
            "fingerprints": current_fps,
        }
        fingerprint_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # Generate human-readable context.md
        context_md = self._render_context_md(profile, config, version)
        (self.cache_dir / "context.md").write_text(context_md, encoding="utf-8")

        return profile, config, version, True

    def _render_context_md(self, profile: StackProfile, config: ProjectConfig, version: int) -> str:
        lines = [
            f"# ForgeCore Project Context (v{version})",
            "",
            f"**Project Name:** {config.project.get('name', profile.root.name)}",
            f"**Root Directory:** `{profile.root}`",
            f"**Detected Languages:** {', '.join(profile.languages) or 'None'}",
            f"**Package Managers:** {', '.join(profile.package_managers) or 'None'}",
            f"**Test Frameworks:** {', '.join(profile.test_frameworks) or 'None'}",
            f"**Suggested Profile:** `{profile.suggested_profile or 'None'}`",
            "",
            "## Active Layers",
        ]
        for layer in profile.layers:
            ver = f" ({layer.version})" if layer.version else ""
            lines.append(f"- **{layer.name}**{ver} - Confidence: {int(layer.confidence * 100)}%")
            for ev in layer.evidence:
                lines.append(f"  - {ev}")

        lines.extend([
            "",
            "## Quality & Verification Gates",
            f"- **Fail on severity:** `{config.verify.fail_on.value}`",
            f"- **Require plan:** `{config.generation.require_plan}`",
            f"- **Require tests:** `{config.generation.require_tests}`",
        ])
        return "\n".join(lines) + "\n"
