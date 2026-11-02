from __future__ import annotations

import re
from pathlib import Path

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.models import DetectedLayer


class SpringBootDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "spring-boot"

    def detect(self, root: Path) -> DetectedLayer | None:
        evidence: list[str] = []
        confidence = 0.0
        version: str | None = None

        files = self.scan_files(root, max_depth=6)

        # Check pom.xml
        pom_files = [f for f in files if f.name == "pom.xml"]
        for pom in pom_files:
            try:
                content = pom.read_text(encoding="utf-8")
                if "spring-boot" in content:
                    confidence = max(confidence, 0.95)
                    ver_match = re.search(r"<spring-boot\.version>([^<]+)</spring-boot\.version>", content)
                    if ver_match:
                        version = ver_match.group(1)
                    rel = str(pom.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Maven configuration at '{rel}' includes Spring Boot dependencies")
            except Exception:
                pass

        # Check Gradle files
        gradle_files = [f for f in files if f.name in {"build.gradle", "build.gradle.kts"}]
        for gr in gradle_files:
            try:
                content = gr.read_text(encoding="utf-8")
                if "org.springframework.boot" in content or "spring-boot" in content:
                    confidence = max(confidence, 0.95)
                    ver_match = re.search(r'id\s*\(?["\']org\.springframework\.boot["\']\)?\s*version\s*["\']([^"\']+)["\']', content)
                    if ver_match:
                        version = ver_match.group(1)
                    rel = str(gr.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Gradle build script at '{rel}' includes Spring Boot plugin/starter")
            except Exception:
                pass

        # Check Java/Kotlin source annotations
        source_files = [f for f in files if f.suffix in {".java", ".kt"}]
        for src in source_files[:10]:
            try:
                content = src.read_text(encoding="utf-8", errors="ignore")
                if "@SpringBootApplication" in content or "import org.springframework." in content:
                    confidence = min(1.0, confidence + 0.2 if confidence > 0 else 0.7)
                    rel = str(src.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Source file '{rel}' contains Spring annotations")
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
