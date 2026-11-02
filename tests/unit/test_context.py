from pathlib import Path

from forgecore.core.context import ContextBuilder


def test_context_builder_fingerprint_and_caching(tmp_path: Path):
    manifest = tmp_path / "package.json"
    manifest.write_text('{"name": "demo"}', encoding="utf-8")

    builder = ContextBuilder(tmp_path)
    profile, config, version, refreshed = builder.build_context()
    assert version == 1
    assert refreshed is True

    # Second run without changes should read cache
    p2, c2, v2, refreshed2 = builder.build_context()
    assert v2 == 1
    assert refreshed2 is False

    # Modify manifest -> triggers auto-refresh and version bump
    manifest.write_text('{"name": "demo-updated"}', encoding="utf-8")
    p3, c3, v3, refreshed3 = builder.build_context()
    assert v3 == 2
    assert refreshed3 is True
