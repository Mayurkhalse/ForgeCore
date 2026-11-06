"""Engineering resource models, catalog, conflict resolution, and selection engine."""
from __future__ import annotations

from .compiler import ContextCompiler
from .conflict import ConflictResolver
from .models import (
    Classification,
    CompatibilityStatus,
    CompiledContext,
    ConflictResolutionReport,
    EngineeringResource,
    KnowledgeConflict,
    PrecedenceTier,
    ResourceType,
    SelectionTrace,
    TrustLevel,
)
from .selector import UnifiedResourceSelector

__all__ = [
    "Classification",
    "CompatibilityStatus",
    "CompiledContext",
    "ConflictResolutionReport",
    "ConflictResolver",
    "ContextCompiler",
    "EngineeringResource",
    "KnowledgeConflict",
    "PrecedenceTier",
    "ResourceType",
    "SelectionTrace",
    "TrustLevel",
    "UnifiedResourceSelector",
]
