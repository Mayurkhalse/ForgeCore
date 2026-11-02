from __future__ import annotations

import json
from pathlib import Path

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.models import DetectedLayer


class ReactDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "react"

    def detect(self, root: Path) -> DetectedLayer | None:
        evidence: list[str] = []
        confidence = 0.0
        version: str | None = None

        # Look for package.json files
        files = self.scan_files(root, max_depth=3)
        package_jsons = [f for f in files if f.name == "package.json"]

        for pkg in package_jsons:
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))
                deps.update(data.get("peerDependencies", {}))

                if "react" in deps:
                    confidence = max(confidence, 0.85)
                    raw_ver = str(deps["react"]).lstrip("^~")
                    version = raw_ver
                    rel_pkg = str(pkg.relative_to(root)).replace("\\", "/")
                    evidence.append(f"package.json at '{rel_pkg}' declares dependency 'react': '{deps['react']}'")
            except Exception:
                pass

        # Look for jsx / tsx source files
        jsx_tsx_files = [f for f in files if f.suffix in {".jsx", ".tsx"}]
        if jsx_tsx_files:
            confidence = min(1.0, confidence + 0.25 if confidence > 0 else 0.6)
            sample = [str(f.relative_to(root)).replace("\\", "/") for f in jsx_tsx_files[:3]]
            evidence.append(f"Found {len(jsx_tsx_files)} JSX/TSX component files (e.g., {', '.join(sample)})")

        if confidence > 0.0:
            return DetectedLayer(
                name=self.layer_name,
                version=version,
                confidence=round(confidence, 2),
                evidence=evidence,
            )
        return None
