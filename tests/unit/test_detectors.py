from pathlib import Path

from forgecore.core.stack_detector import StackDetector

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_detect_fastapi():
    root = FIXTURES_DIR / "fastapi_app"
    detector = StackDetector(root)
    profile = detector.detect_stack()

    assert "fastapi" in profile.layer_names()
    assert "python" in profile.languages
    assert profile.confidence["fastapi"] >= 0.8
    assert len(profile.evidence["fastapi"]) > 0
    assert profile.suggested_profile == "react-fastapi"


def test_detect_react():
    root = FIXTURES_DIR / "react_app"
    detector = StackDetector(root)
    profile = detector.detect_stack()

    assert "react" in profile.layer_names()
    assert profile.confidence["react"] >= 0.8
    assert profile.suggested_profile == "react-node"


def test_detect_node_express():
    root = FIXTURES_DIR / "node_app"
    detector = StackDetector(root)
    profile = detector.detect_stack()

    assert "node-express" in profile.layer_names()
    assert "javascript" in profile.languages
    assert profile.confidence["node-express"] >= 0.8


def test_detect_spring_boot():
    root = FIXTURES_DIR / "spring_app"
    detector = StackDetector(root)
    profile = detector.detect_stack()

    assert "spring-boot" in profile.layer_names()
    assert "java" in profile.languages
    assert "maven" in profile.package_managers
    assert profile.suggested_profile == "java-springboot"
    assert any("Application.java" in e for e in profile.evidence["spring-boot"])


def test_detect_python_ml():
    root = FIXTURES_DIR / "ml_app"
    detector = StackDetector(root)
    profile = detector.detect_stack()

    assert "python-ml" in profile.layer_names()
    assert profile.suggested_profile == "python-ml"
