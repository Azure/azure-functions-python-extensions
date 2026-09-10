# Discovery and binding verification

This revision rebases the prototype onto PR #185 at `2777aa3`. Its provider/MCP
fixes, renamed sample directories, malformed-input tests, and CI dependencies
are preserved. The rebased baseline passed 168 tests before the API revision.

## Current results

- 192 tests passed with YAML support installed, using Python 3.13.11, core 1.16.0,
  declarative 1.0.3, Functions 2.3.0, Durable 2.0.0rc1 and pinned DAFX PR #72.
- Without YAML dependencies, 179 passed and 13 YAML-specific cases skipped.
- Five isolated non-durable import tests passed.
- Strict mypy passed on 14 source files; scoped Flake8 and whitespace checks passed.
- Both wheels/source distributions built and local documentation links resolved.

## Change analysis

- Replaced the ambiguous `durable`/`workflows` switches with independent discovery
  flags and bulk endpoint controls. Bindings default private. Agent/workflow
  exposure matrices and registration-reuse tests cover every Boolean combination.
  Enabling exposure is monotonic and cannot be undone by a later private binding.
  A mutation forcing every agent endpoint on fails the three private combinations
  while the other five pass. Restored registration tests pass all 24 cases.
- One app-owned registry collects all declarations before the DAFX host is built.
  Workflow-only discovery does not expose standalone agents. Native factories and
  resource ownership remain unchanged, and a custom factory does not trigger
  irrelevant Markdown compilation unless agent discovery is requested.
- Selective loading validates the entry path and expected workflow identity before
  hosting. Unrelated YAML files remain unloaded. Binding stacking is validated at
  the outer orchestration trigger after injected parameters have been removed.
- Actual SDK protobuf parent execution schedules a child orchestration, the child
  runs through the existing real activity/replay harness, and parent replay receives
  the result. Task tests cover native and compatibility contexts, typed output
  reconstruction and child failure propagation.
- Independent review found reserved-envelope input forwarding and a collision
  between a workflow-internal agent and a standalone agent. Both were reproduced
  with safe failing tests and fixed. Forwarding now uses DAFX's own sanitizers;
  a standalone/internal collision fails before returning an indexed app.
- Native YAML behavior remains delegated to the public MAF factory. The narrow
  DAFX workflow-route override and input sanitizers rely on the pinned DAFX version,
  not on a custom workflow execution engine.

Tests use SDK handlers locally. No live Functions host/backend or external service
was exercised. The generic parent binding does not provide aggregated child HITL
management. Private means no generated HTTP routes, not a security principal.
