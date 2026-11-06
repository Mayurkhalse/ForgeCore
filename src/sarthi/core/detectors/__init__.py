from __future__ import annotations

from sarthi.core.detectors.base import BaseDetector
from sarthi.core.detectors.fastapi import FastAPIDetector
from sarthi.core.detectors.node import NodeExpressDetector
from sarthi.core.detectors.python_ml import PythonMLDetector
from sarthi.core.detectors.react import ReactDetector
from sarthi.core.detectors.react_native import ReactNativeDetector
from sarthi.core.detectors.spring import SpringBootDetector

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
