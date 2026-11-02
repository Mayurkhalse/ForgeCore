from __future__ import annotations

import json
from pathlib import Path

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.models import DetectedLayer


class ReactNativeDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "react-native"

    def detect(self, root: Path) -> DetectedLayer | None:
        evidence: list[str] = []
        confidence = 0.0
        version: str | None = None

        files = self.scan_files(root, max_depth=6)
        package_jsons = [f for f in files if f.name == "package.json"]

        for pkg in package_jsons:
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))

                if "react-native" in deps:
                    confidence = max(confidence, 0.9)
                    version = str(deps["react-native"]).lstrip("^~")
                    rel_pkg = str(pkg.relative_to(root)).replace("\\", "/")
                    evidence.append(f"package.json at '{rel_pkg}' declares 'react-native': '{deps['react-native']}'")
                if "expo" in deps:
                    confidence = max(confidence, 0.9)
                    if not version:
                        version = str(deps["expo"]).lstrip("^~")
                    rel_pkg = str(pkg.relative_to(root)).replace("\\", "/")
                    evidence.append(f"package.json at '{rel_pkg}' declares 'expo': '{deps['expo']}'")
            except Exception:
                pass

        # Look for metro config or mobile app config
        config_files = [f for f in files if f.name in {"metro.config.js", "metro.config.ts", "app.json"}]
        for cfg in config_files:
            rel = str(cfg.relative_to(root)).replace("\\", "/")
            if "metro.config" in cfg.name:
                confidence = min(1.0, confidence + 0.3 if confidence > 0 else 0.7)
                evidence.append(f"Found Metro configuration at '{rel}'")
            elif cfg.name == "app.json":
                try:
                    content = json.loads(cfg.read_text(encoding="utf-8"))
                    if "expo" in content or "react-native" in content:
                        confidence = min(1.0, confidence + 0.3 if confidence > 0 else 0.7)
                        evidence.append(f"Found mobile app config at '{rel}'")
                except Exception:
                    pass

        if confidence > 0.0:
            return DetectedLayer(
                name=self.layer_name,
                version=version,
                confidence=round(confidence, 2),
                evidence=evidence,
            )
        return None
