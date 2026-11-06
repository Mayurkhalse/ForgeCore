---
id: feature
requires_tools:
  - get_standards
  - verify_project
---
## 1. Plan
- State the desired behavior change and break down the necessary steps.
- Identify the affected layers (e.g. {{ layers | join(', ') }}).
- Call `sarthi.get_standards(task=task_description, layers=affected_layers)`.

## 2. Design Check
- Validate that the proposed architecture aligns with the retrieved standards.
- Confirm separation of concerns (no business logic in controllers/views).

## 3. Implement
- Apply the smallest coherent set of changes.
- Add or update automated unit/integration tests alongside the implementation.
- Avoid modifying unneeded files or introducing unused dependencies.

## 4. Verify
- Call `sarthi.verify_project(scope="changed")`.
- If failures at severity >= {{ fail_on }} are reported, fix them and rerun verification until clean.

## 5. Report
- Summarize what was implemented, files changed, and verification status.
