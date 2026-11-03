from __future__ import annotations

from pathlib import Path

from forgecore.core.standards_linter import StandardsLinter


def generate_rules_table(standards_dir: Path | str | None = None) -> str:
    linter = StandardsLinter(standards_dir)
    return linter.generate_summary_table()


def main() -> None:
    print(generate_rules_table())


if __name__ == "__main__":
    main()
