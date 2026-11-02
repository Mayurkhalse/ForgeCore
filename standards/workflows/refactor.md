---
id: refactor
requires_tools:
  - get_standards
  - verify_project
---
## 1. Baseline Verification
- Run existing tests to ensure clean green state prior to refactoring.
- Call `forgecore.get_standards(task=refactor_goal, task_type="refactor")`.

## 2. Plan Architecture
- Clarify domain boundaries, service layers, and contracts.
- Ensure backwards compatibility if public APIs are modified.

## 3. Incremental Refactor
- Refactor in small, test-backed increments.
- Keep business logic isolated from presentation and database layers.

## 4. Verify
- Call `forgecore.verify_project(scope="changed")`.
- Ensure all tests pass and static checks report zero violations.

## 5. Report
- Summarize structural improvements, maintainability gains, and test coverage.
