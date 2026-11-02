# Contributing to ForgeCore

Thank you for your interest in contributing to ForgeCore!

ForgeCore is built on the principle: **Standards are data, not code.**
Most contributions will be adding or refining engineering standards in `standards/`.

---

## Adding a New Rule (10-minute guide)

1. Find the appropriate layer folder under `standards/<layer>/` (or propose a new layer).
2. Open or create `rules.yaml`.
3. Follow the schema:
   ```yaml
   - id: MYLAYER-CAT-001
     title: Imperative title of rule
     layer: mylayer
     category: architecture  # architecture|security|testing|api|data|perf|ops
     severity: high          # critical|high|medium|low
     tier: standard          # core|standard|reference
     applies_when:
       layers: [mylayer]
       tasks: [feature, refactor]
     rule: Precise explanation of requirement.
     rationale: Why this standard exists.
     good: |
       // good code example
     bad: |
       // bad code example
     verify:
       type: checklist       # semgrep|ruff|eslint|command|pytest-marker|checklist|secrets
     tags: [topic]
     since: "0.1.0"
   ```
4. Run `uv run forgecore lint-standards` to validate your changes.
5. Submit a pull request.

---

## Local Development & Testing

1. Install `uv`: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
2. Clone repository:
   ```bash
   git clone https://github.com/forgecore/forgecore.git
   cd forgecore
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Run linter and tests:
   ```bash
   uv run ruff check .
   uv run pytest
   uv run forgecore lint-standards
   ```
