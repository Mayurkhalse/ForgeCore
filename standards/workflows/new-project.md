---
id: new-project
requires_tools:
  - initialize_project
  - get_standards
  - verify_project
---
## 1. Initialize
- Scaffold the project layout following standard directory conventions for the chosen stack.
- Create dependency manifest (`package.json`, `pyproject.toml`, or `pom.xml`).
- Call `sarthi.initialize_project()` to detect layers and register configuration.

## 2. Standards Review
- Call `sarthi.get_standards(task="initial architecture setup", task_type="new-project")`.
- Structure application layers: entrypoints, business services, data repositories, schemas.

## 3. Implement Core Skeleton
- Implement minimal viable health-check endpoint or main entrypoint.
- Setup test harness and continuous verification.

## 4. Verify
- Run `sarthi.verify_project(scope="all")`.
- Fix any configuration, lint, or security issues.
