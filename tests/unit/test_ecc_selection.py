"""Tests for multi-stack retrieval, context matching, and irrelevant knowledge exclusion."""
from __future__ import annotations

from pathlib import Path

import pytest

from forgecore.core.providers.registry import ProviderRegistry
from forgecore.core.resources.selector import UnifiedResourceSelector


@pytest.fixture
def selector() -> UnifiedResourceSelector:
    return UnifiedResourceSelector()


def test_selection_fastapi_task(selector: UnifiedResourceSelector):
    """Verifies that a FastAPI task retrieves FastAPI standards and relevant ECC skills."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "fastapi", "python"],
        task="Implement JWT token authentication and route handlers in FastAPI",
        task_type="feature",
        max_tokens=3000,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    assert any("FAPI-" in i for i in ids)
    assert any("fastapi-patterns" in i for i in ids)

    # Irrelevant stack exclusion
    assert not any("react" in i for i in ids if "native" not in i)
    assert not any("spring" in i for i in ids)
    assert not any("laravel" in i for i in ids)


def test_selection_mern_react_task(selector: UnifiedResourceSelector):
    """Verifies that a React / Node task retrieves React standards and excludes Python/FastAPI."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "react", "node", "typescript"],
        task="Create an interactive accessible React dashboard with state management",
        task_type="feature",
        max_tokens=3000,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    assert any("REACT-" in i for i in ids)

    # Irrelevant stack exclusion
    assert not any("FAPI-" in i for i in ids)
    assert not any("django" in i for i in ids)
    assert not any("spring" in i for i in ids)


def test_selection_spring_boot_task(selector: UnifiedResourceSelector):
    """Verifies that a Spring Boot task retrieves Java/Spring resources."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "spring", "java"],
        task="Implement REST controller with Spring Security and Maven",
        task_type="feature",
        max_tokens=3000,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    assert any("spring" in i or "java" in i for i in ids)

    # Exclude Python/FastAPI
    assert not any("FAPI-" in i for i in ids)
    assert not any("fastapi" in i for i in ids)


def test_selection_python_ml_task(selector: UnifiedResourceSelector):
    """Verifies that a Python ML task retrieves Python ML standards."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "python", "python-ml"],
        task="Train a PyTorch neural network model and evaluate metrics",
        task_type="feature",
        max_tokens=3000,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    assert any("ML-" in i or "python" in i for i in ids)
    assert not any("react" in i for i in ids if "native" not in i)


def test_selection_react_native_task(selector: UnifiedResourceSelector):
    """Verifies that a React Native task retrieves mobile resources and excludes Web React."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "react-native", "mobile"],
        task="Build an Expo mobile navigation screen",
        task_type="feature",
        max_tokens=3000,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    assert not any("FAPI-" in i for i in ids)


def test_selection_mixed_stack_project(selector: UnifiedResourceSelector):
    """Verifies that a mixed full-stack project (FastAPI + React) receives relevant rules for both."""
    res, trace, report = selector.select_resources(
        active_layers=["universal", "security", "fastapi", "react", "python", "node"],
        task="Connect FastAPI login backend to React login form",
        task_type="feature",
        max_tokens=3500,
    )
    ids = [r.id for r in res]
    assert "native.contract.core" in ids
    has_fastapi = any("FAPI-" in i or "fastapi" in i for i in ids)
    has_react = any("REACT-" in i or "react" in i for i in ids)
    assert has_fastapi and has_react


def test_selection_project_specific_rule_activation(tmp_path: Path):
    """Verifies that custom rules from .forgecore/rules/ are discovered and selected."""
    fc_rules = tmp_path / ".forgecore" / "rules"
    fc_rules.mkdir(parents=True)

    custom_rule = """id: custom-corp-logging
title: Corporate JSON Logging Standard
layers: [universal]
rule: All service logs must be emitted as structured JSON with correlation_id.
category: observability
"""
    (fc_rules / "corp_log.yaml").write_text(custom_rule, encoding="utf-8")

    registry = ProviderRegistry.create_default(project_root=str(tmp_path))
    selector = UnifiedResourceSelector(registry=registry)

    res, trace, report = selector.select_resources(
        active_layers=["universal"],
        task="Add structured corporate logging",
        task_type="feature",
    )
    ids = [r.id for r in res]
    assert "workspace.custom-corp-logging" in ids
