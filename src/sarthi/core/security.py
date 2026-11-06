from __future__ import annotations

import re
from typing import Any

FENCE_TAG_PATTERN = re.compile(
    r"<\s*(/)?\s*untrusted[_\s]*project[_\s]*data\s*>",
    re.IGNORECASE,
)
FENCE_WRAPPED_PATTERN = re.compile(
    r"^<\s*untrusted[_\s]*project[_\s]*data\s*>(.*)<\s*/\s*untrusted[_\s]*project[_\s]*data\s*>$",
    re.IGNORECASE | re.DOTALL,
)


def neutralize_fence_tags(text: str) -> str:
    """Neutralizes raw fence tag occurrences within untrusted strings to prevent breakouts.

    Matches case-insensitively and tolerates arbitrary internal whitespace or casing variants.
    """

    def _replace(match: re.Match[str]) -> str:
        slash = match.group(1) or ""
        return f"[{slash}untrusted_project_data]"

    return FENCE_TAG_PATTERN.sub(_replace, text)


def fence_untrusted(text: Any) -> str:
    """Fences and labels strings sourced from project files as untrusted project data,

    neutralizing any internal fence breakout sequences.
    """
    if text is None:
        return ""
    val = str(text) if not isinstance(text, str) else text
    stripped = val.strip()
    match_wrap = FENCE_WRAPPED_PATTERN.match(stripped)
    if match_wrap:
        val = match_wrap.group(1)
    neutralized = neutralize_fence_tags(val)
    return f"<untrusted_project_data>{neutralized}</untrusted_project_data>"


def fence_nested_untrusted(data: Any) -> Any:
    """Recursively fences string data originating from project files/manifests."""
    if isinstance(data, str):
        return fence_untrusted(data)
    if isinstance(data, list):
        return [fence_nested_untrusted(item) for item in data]
    if isinstance(data, dict):
        return {k: fence_nested_untrusted(v) for k, v in data.items()}
    return data
