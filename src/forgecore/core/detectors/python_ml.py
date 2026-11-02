from __future__ import annotations

import re
from pathlib import Path

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.models import DetectedLayer

ML_LIBRARIES = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "keras",
    "scikit-learn",
    "sklearn",
    "transformers",
    "datasets",
    "mlflow",
    "xgboost",
    "lightgbm",
    "optuna",
    "wandb",
    "pandas",
    "numpy",
]


class PythonMLDetector(BaseDetector):
    @property
    def layer_name(self) -> str:
        return "python-ml"

    def detect(self, root: Path) -> DetectedLayer | None:
        evidence: list[str] = []
        confidence = 0.0
        version: str | None = None
        matched_libs: list[str] = []

        files = self.scan_files(root, max_depth=3)

        # 1. Check requirements / pyproject / conda environment
        dep_files = [
            f for f in files
            if f.name in {"pyproject.toml", "Pipfile", "environment.yml", "environment.yaml"}
            or re.match(r"^requirements.*\.txt$", f.name, re.IGNORECASE)
        ]

        for df in dep_files:
            try:
                content = df.read_text(encoding="utf-8", errors="ignore")
                for lib in ML_LIBRARIES:
                    if re.search(rf"\b{lib}\b", content, re.IGNORECASE):
                        if lib not in matched_libs:
                            matched_libs.append(lib)
                if matched_libs:
                    confidence = max(confidence, 0.85)
                    rel = str(df.relative_to(root)).replace("\\", "/")
                    evidence.append(f"Dependency manifest '{rel}' includes ML libraries: {', '.join(matched_libs[:5])}")
            except Exception:
                pass

        # 2. Check for Jupyter Notebooks
        notebooks = [f for f in files if f.suffix == ".ipynb"]
        if notebooks:
            confidence = min(1.0, confidence + 0.3 if confidence > 0 else 0.6)
            evidence.append(f"Found {len(notebooks)} Jupyter Notebook files (.ipynb)")

        if confidence > 0.0:
            return DetectedLayer(
                name=self.layer_name,
                version=version,
                confidence=round(confidence, 2),
                evidence=evidence,
            )
        return None
