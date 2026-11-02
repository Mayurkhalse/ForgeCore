from __future__ import annotations

import re
from pathlib import Path

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.models import DetectedLayer


class FastAPIDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "fastapi"

    def detect(self, root: Path) -> DetectedLayer | None:
        evidence: list[str] = []
        confidence = 0.0
        version: str | None = None

        files = self.scan_files(root, max_depth=3)

        # 1. Check pyproject.toml
        pyprojects = [f for f in files if f.name == "pyproject.toml"]
        for pyp in pyprojects:
            try:
                content = pyp.read_text(encoding="utf-8")
                # Exclude self-detection if looking at forgecore itself without real fastapi
                if re.search(r'["\']fastapi[>=<~^0-9\.]*["\']', content, re.IGNORECASE):
                    confidence = max(confidence, 0.9)
                    match = re.search(r'fastapi[>=<~^]*([0-9\.]+)', content, re.IGNORECASE)
                    if match:
                        version = match.group(1)
                    rel = str(pyp.relative_to(root)).replace("\\", "/")
                    evidence.append(f"pyproject.toml at '{rel}' lists 'fastapi'")
            except Exception:
                pass

        # 2. Check requirements*.txt
        req_files = [f for f in files if re.match(r"^requirements.*\.txt$", f.name, re.IGNORECASE)]
        for req in req_files:
            try:
                content = req.read_text(encoding="utf-8")
                match = re.search(r"^fastapi([>=<~^]*([0-9\.]+))?", content, re.MULTILINE | re.IGNORECASE)
                if match:
                    confidence = max(confidence, 0.9)
                    if match.group(2):
                        version = match.group(2)
                    rel = str(req.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Requirements file at '{rel}' lists 'fastapi'")
            except Exception:
                pass

        # 3. Check Pipfile
        pipfiles = [f for f in files if f.name == "Pipfile"]
        for pf in pipfiles:
            try:
                content = pf.read_text(encoding="utf-8")
                if "fastapi" in content.lower():
                    confidence = max(confidence, 0.85)
                    rel = str(pf.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Pipfile at '{rel}' contains 'fastapi'")
            except Exception:
                pass

        # 4. Check python files for FastAPI imports or instantiate
        py_files = [f for f in files if f.suffix == ".py"]
        for py in py_files[:10]:  # Check first 10 python files
            try:
                content = py.read_text(encoding="utf-8", errors="ignore")
                if "from fastapi import" in content or "import fastapi" in content or "FastAPI(" in content:
                    confidence = min(1.0, confidence + 0.3 if confidence > 0 else 0.7)
                    rel = str(py.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Source file '{rel}' contains FastAPI import/initialization")
                    break
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
