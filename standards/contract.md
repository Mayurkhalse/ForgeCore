# FORGECORE CORE CONTRACT v1

You are operating under ForgeCore engineering standards. Follow this contract strictly:

1. **Session Start:** At the beginning of a coding session, call `forgecore.initialize_project` once to detect the stack and active engineering constraints.
2. **Workflows:** Before non-trivial work, call `forgecore.get_workflow(task_type)` and follow its plan-implement-verify lifecycle.
3. **Retrieve Standards:** Before writing code in any architectural layer, call `forgecore.get_standards(task, layers)` to load specific rules.
4. **No Hardcoded Secrets:** Never hardcode API keys, tokens, or credentials. Read configuration strictly from environment variables or secure stores.
5. **Boundary Validation:** Validate and sanitize all external inputs (HTTP queries, body payloads, CLI arguments) at the network/system boundary using strict schemas (e.g., Pydantic, Zod).
6. **Separation of Concerns:** Keep business logic out of controllers, route handlers, and UI components. Route handlers only parse, authorize, delegate to services, and format responses.
7. **Test Discipline:** Every behavior change must ship with accompanying automated unit or integration tests. Never delete or skip tests to make builds green.
8. **Deterministic Verification:** Before declaring any task complete, call `forgecore.verify_project(scope="changed")` and resolve all findings at severity >= high.
9. **Error Handling:** Never swallow exceptions or use empty catch/except blocks. Always log errors with contextual metadata and return structured, safe error messages to clients.
10. **Secure Database Queries:** Never concatenate user input into SQL queries. Always use parameterized queries or type-safe ORM query builders.
11. **Minimal Surface Area:** Expose only required APIs, types, and exports. Mark internal functions and helpers as private or internal.
12. **Idempotency & Resilience:** Design mutating operations with idempotency in mind. Implement proper timeouts on all external HTTP and RPC calls.
13. **Strict Typing:** Avoid `any` in TypeScript or untyped signatures in Python/Java. Explicitly type all public parameters and return values.
14. **No Dead Code:** Remove commented-out code blocks, unused imports, and unreferenced functions before completion.
15. **Resource Management:** Ensure file handles, database connections, and network streams are always closed using context managers (`with` / `try-finally` / `using`).
16. **Deterministic Builds:** Maintain reproducible dependency manifests. Never use unpinned floating wildcard versions for core production dependencies.
