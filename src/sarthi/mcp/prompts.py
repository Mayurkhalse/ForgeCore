from __future__ import annotations

PROMPT_TEMPLATES = {
    "new-feature": (
        "Implement a new feature: {task}\n\n"
        "Guidelines:\n"
        "1. Call sarthi.get_standards(task='{task}', task_type='feature') to retrieve active engineering rules.\n"
        "2. Break down the plan into concrete steps.\n"
        "3. Write tests alongside the implementation.\n"
        "4. Call sarthi.verify_project(scope='changed') and fix all failures.\n"
    ),
    "fix-bug": (
        "Fix a bug: {description}\n\n"
        "Guidelines:\n"
        "1. Write a failing regression test replicating the issue.\n"
        "2. Call sarthi.get_standards(task='{description}', task_type='bugfix') for boundary guidance.\n"
        "3. Fix the root cause cleanly.\n"
        "4. Run sarthi.verify_project(scope='changed') to confirm all tests pass and no regressions occur.\n"
    ),
    "refactor": (
        "Refactor codebase: {scope}\n\n"
        "Guidelines:\n"
        "1. Verify baseline test suite passes.\n"
        "2. Call sarthi.get_standards(task='{scope}', task_type='refactor').\n"
        "3. Decouple layers and eliminate code duplication.\n"
        "4. Call sarthi.verify_project(scope='changed') to ensure behavioral preservation.\n"
    ),
    "new-project": (
        "Scaffold new project: {name}\n\n"
        "Guidelines:\n"
        "1. Scaffold clean modular directory layout.\n"
        "2. Call sarthi.initialize_project() to register stack profile.\n"
        "3. Add continuous test and verification configuration.\n"
        "4. Run sarthi.verify_project(scope='all').\n"
    ),
}
