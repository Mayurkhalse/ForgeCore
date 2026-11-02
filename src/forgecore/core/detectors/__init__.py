from __future__ import annotations

from forgecore.core.detectors.base import BaseDetector
from forgecore.core.detectors.fastapi import FastAPIDetector
from forgecore.core.detectors.node import NodeExpressDetector
from forgecore.core.detectors.python_ml import PythonMLDetector
from forgecore.core.detectors.react import ReactDetector
from forgecore.core.detectors.react_native import ReactNativeDetector
from forgecore.core.detectors.spring import SpringBootDetector

ALL_DETECTORS: list[type[BaseDetector]] = [
    ReactDetector,
    ReactNativeDetector,
    NodeExpressDetector,
    FastAPIDetector,
    SpringBootDetector,
    PythonMLDetector,
]

__all__ = [
    "BaseDetector",
    "ReactDetector",
    "ReactNativeDetector",
    "NodeExpressDetector",
    "FastAPIDetector",
    "SpringBootDetector",
    "PythonMLDetector",
    "ALL_DETECTORS",
]
