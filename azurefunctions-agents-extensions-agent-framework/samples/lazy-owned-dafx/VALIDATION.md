# Historical durable markdown prototype verification

These results predate the rebase onto PR #185 at `2777aa3` and the separate
discovery/exposure API. They are historical totals, not validation of the current
revision. Current behavior is documented in [README.md](README.md).

Verified on Windows with Python 3.13.11 on 2026-09-09. This revision replaces
the explicit-registration example at `5d77570`. Branch base is extensions
PR #185 at `db2526586348513ff86ed2c61ffc685815a8d212`. Both DAFX packages remain
pinned to PR #72 at `aa9529ec489e16ac64b73bd68d5adbb8e4945258`.

## Historical results

| Configuration | Result |
| --- | --- |
| Functions 2.3.0, Durable 2.0.0rc1, core 1.16.0 | 135 passed |
| Functions 2.3.0, Durable 2.0.0b2, core 1.13.0 | 135 passed |
| Normal install without Durable/DAFX packages | 5 import tests passed |
| Strict mypy, both agent packages | Passed, 11 source files |
| Flake8, both package sources, framework tests and local samples | Passed |
| Both wheels and source distributions | Built |
| Wheel contents | New adapter included, removed base durable module absent |

The SDK emits one deprecation warning about `df_loads` without `expected_type`.
It is not suppressed. Tests exercise the SDK's real orchestration and entity
protobuf handlers, not a running Functions host or storage backend. Local clients
substitute for the model service; external MCP servers were not contacted.

## Historical change analysis

- Normal markdown binding construction/invocation remains import-safe without
  DAFX. Durable discovery is explicit and creates recipes, not clients. The old
  context wrapper, hidden activity, exports, and activity-specific tests are removed.
- The earlier revision published entity and HTTP functions for both discovery and
  bindings. That exposure behavior is superseded. Bindings are now private by
  default, and the inner DAFX host is deferred until indexing.
- Raw instructions are preserved. Discovery rejects duplicate names across both
  directories, case collisions, directories masquerading as files, and symlinks
  escaping the app root. Durable markdown names are restricted to safe ASCII
  route/entity identifiers. Colliding generated HTTP function names fail indexing.
- The binding validates generator shape, hides the injected parameter, forwards
  context and optional native input, and rejects mismatched context names and late
  declarations. Both one- and two-argument forms run through the real SDK dispatcher.
- A replay probe schedules the same entity, correlation ID, and input without
  constructing a client. Pinned DAFX supplies a wall-clock `created_at` on each
  request, so this is not a claim of byte-identical replay payloads. That upstream
  timestamp behavior is unchanged by this prototype.
- Endpoint and binding samples execute two turns through indexed entity handlers
  with serialized state carried between operations. Clients are newly created,
  entered, and closed for each turn. Session identity and history remain stable.
- Adapter tests cover finalization before cleanup, full response identity/value,
  fresh resources, stream/run failures, and cancellation during an active pull.
  An abandoned stream that is neither consumed nor cancelled is not covered.
- All sample apps are enumerated into index tests. Every SDK-owned function name
  is independently checked for collisions. A read-only adversarial review found
  no concrete additional defect; it is not a substitute for these runtime checks.
- Previous-commit probes fail on the new constructor/decorator APIs. In-memory
  mutations disabling discovery fail two tests, substituting a non-agent proxy
  fails three, and dropping the final response fails one. The unmodified adapter
  suite then passes all 40 tests. No source files were mutated by the probes.
- That revision's docs and samples used discovery or binding declarations, not the deleted
  custom activity API. `add_durable_agent()` remains a lower-level instance API but
  is not required by either markdown sample.

The Git-pinned SDK 2 migration is still an open PR. These dependencies and tests
support local exploration, not a PyPI release or deployed-host compatibility claim.
