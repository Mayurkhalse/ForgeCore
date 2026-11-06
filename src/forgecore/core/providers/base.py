"""Protocol interface for knowledge providers."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from forgecore.core.resources.models import EngineeringResource, ResourceType


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Protocol implemented by all engineering knowledge providers."""

    @property
    def provider_id(self) -> str:
        """Unique identifier of the provider ('native', 'ecc', 'workspace')."""
        ...

    @property
    def version(self) -> str:
        """Catalog release version."""
        ...

    def initialize(self) -> None:
        """Loads manifests, indexes resources, and validates models."""
        ...

    def list_resources(
        self,
        resource_type: ResourceType | None = None,
    ) -> list[EngineeringResource]:
        """Returns all indexed resources, optionally filtered by ResourceType."""
        ...

    def get_resource(self, resource_id: str) -> EngineeringResource | None:
        """Retrieves a resource descriptor by its unique ID."""
        ...

    def get_content(self, resource: EngineeringResource) -> str:
        """Returns the full text/markdown content of a resource."""
        ...

