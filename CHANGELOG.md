# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added
- Core models with Pydantic validation (Rule, StackProfile, Finding, VerifyReport).
- Multi-layer stack detection across 5 primary stacks (`react`, `react-native`, `node-express`, `fastapi`, `spring-boot`, `python-ml`).
- Sandboxed PathGuard preventing path traversal and secret file exfiltration.
- Dynamic manifest fingerprinting and cache auto-refresh.
- Rule selector with priority ranking (severity, tier, specificity) and context budget management.
- Complete standards library across universal, security, testing, api-design, observability, and all 5 framework stacks.
- Deterministic verification loop supporting Ruff, Semgrep, ESLint, test runners, and secret scanning.
- MCP Server implementing 6 core tools, resources, and reusable prompt templates.
- Antigravity adapter supporting one-command idempotent installation, uninstallation, and health diagnostics.
- Typer-based CLI (`init`, `context`, `standards`, `verify`, `doctor`, `lint-standards`, `serve`, `install`, `uninstall`).
