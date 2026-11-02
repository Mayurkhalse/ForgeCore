---
id: bugfix
requires_tools:
  - get_standards
  - verify_project
---
## 1. Reproduce
- Write a reproducing unit or integration test exposing the bug.
- Verify the test fails before applying any fix.

## 2. Identify Root Cause & Plan
- Call `forgecore.get_standards(task=bug_description, task_type="bugfix")`.
- Analyze boundary conditions, null/empty states, and unexpected inputs.

## 3. Implement Fix
- Address the root cause with minimal side-effects.
- Confirm the reproduction test now passes.

## 4. Verify
- Call `forgecore.verify_project(scope="changed")`.
- Fix any security or lint regressions immediately.

## 5. Report
- Explain why the bug occurred, how it was resolved, and the test proving the fix.
