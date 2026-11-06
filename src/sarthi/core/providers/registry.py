"""Provider registry aggregating and managing multiple knowledge providers."""
from __future__ import annotations

from typing import Any

from sarthi.core.providers.base import KnowledgeProvider
from sarthi.core.providers.ecc import ECCBundledProvider
from sarthi.core.providers.native import SarthiNativeProvider
from sarthi.core.resources.models import EngineeringResource, ResourceType


class ProviderRegistry:
    """Central registry aggregating knowledge providers and providing catalog discovery."""

    def __init__(self) -> None:
        self._providers: dict[str, KnowledgeProvider] = {}
        self._initialized = False

    @classmethod
    def create_default(cls, project_root: str | None = None) -> ProviderRegistry:
        """Creates and initializes a ProviderRegistry with standard Native and ECC providers."""
        reg = cls()
        reg.register_provider(SarthiNativeProvider())
        reg.register_provider(ECCBundledProvider())
        if project_root:
            from sarthi.core.providers.workspace import WorkspaceProvider

            reg.register_provider(WorkspaceProvider(project_root))
        reg.initialize()
        return reg

    def register_provider(self, provider: KnowledgeProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> KnowledgeProvider | None:
        return self._providers.get(provider_id)

    def initialize(self) -> None:
        if self._initialized:
            return
        for provider in self._providers.values():
            provider.initialize()
        self._initialized = True

    def list_all_resources(
        self,
        resource_type: ResourceType | None = None,
    ) -> list[EngineeringResource]:
        self.initialize()
        resources: list[EngineeringResource] = []
        for provider in self._providers.values():
            resources.extend(provider.list_resources(resource_type=resource_type))
        return resources

    def get_resource(self, resource_id: str) -> EngineeringResource | None:
        self.initialize()
        for provider in self._providers.values():
            res = provider.get_resource(resource_id)
            if res is not None:
                return res
        return None

    def get_content(self, resource: EngineeringResource) -> str:
        provider = self.get_provider(resource.provider_id)
        if provider:
            return provider.get_content(resource)
        if resource.content_inline:
            return resource.content_inline
        return ""

    def get_inventory_summary(self) -> dict[str, Any]:
        """Returns statistical summary of catalog coverage across providers and types."""
        self.initialize()
        all_res = self.list_all_resources()

        counts_by_provider: dict[str, int] = {}
        counts_by_type: dict[str, int] = {}
        counts_by_classification: dict[str, int] = {}
        counts_by_compatibility: dict[str, int] = {}

        for r in all_res:
            counts_by_provider[r.provider_id] = counts_by_provider.get(r.provider_id, 0) + 1
            counts_by_type[r.type.value] = counts_by_type.get(r.type.value, 0) + 1
            counts_by_classification[r.classification.value] = (
                counts_by_classification.get(r.classification.value, 0) + 1
            )
            counts_by_compatibility[r.compatibility.value] = (
                counts_by_compatibility.get(r.compatibility.value, 0) + 1
            )

        return {
            "total_resources": len(all_res),
            "counts_by_provider": counts_by_provider,
            "counts_by_type": counts_by_type,
            "counts_by_classification": counts_by_classification,
            "counts_by_compatibility": counts_by_compatibility,
        }

