from __future__ import annotations

import json
from pathlib import Path

from sarthi.core.detectors.base import BaseDetector
from sarthi.core.models import DetectedLayer

FRAMEWORKS = ["express", "fastify", "@nestjs/core", "koa", "hapi"]


class NodeExpressDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "node-express"

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

                for fw in FRAMEWORKS:
                    if fw in deps:
                        confidence = max(confidence, 0.9)
                        version = str(deps[fw]).lstrip("^~")
                        rel_pkg = str(pkg.relative_to(root)).replace("\\", "/")
                        evidence.append(f"package.json at '{rel_pkg}' declares backend framework '{fw}': '{deps[fw]}'")
            except Exception:
                pass

        # Look for entry points
        entry_candidates = ["server.js", "server.ts", "app.js", "app.ts", "main.ts"]
        entry_files = [f for f in files if f.name in entry_candidates]
        for ef in entry_files:
            rel = str(ef.relative_to(root)).replace("\\", "/")
            confidence = min(1.0, confidence + 0.15 if confidence > 0 else 0.5)
            evidence.append(f"Found server entrypoint file at '{rel}'")

        if confidence > 0.0:
            return DetectedLayer(
                name=self.layer_name,
                version=version,
                confidence=round(confidence, 2),
                evidence=evidence,
            )
        return None
