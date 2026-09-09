# Prototype verification

Verified on Windows with Python 3.13.11 on 2026-09-09. Branch base is extensions
PR #185 at `db2526586348513ff86ed2c61ffc685815a8d212`. DAFX dependencies are pinned
to PR #72 at `aa9529ec489e16ac64b73bd68d5adbb8e4945258`.

## Results

| Configuration | Result |
| --- | --- |
| Original PR, Functions 2.3.0, Durable 2.0.0rc1, core 1.16.0 | 69 passed |
| Prototype, same SDK/core versions, DAFX PR #72 | 96 passed |
| Prototype, Durable 2.0.0b2, core 1.16.0 | 96 passed |
| Prototype, Durable 2.0.0b2, core 1.13.0 | 96 passed |
| Fresh normal install without Durable/DAFX packages | 5 import tests passed |
| Strict mypy, both agent packages | Passed, 11 source files |
| Flake8, framework source, tests, and new sample | Passed |
| Both package wheels and source distributions | Built |
| Dependency consistency, plain and durable environments | Passed |

The SDK emits one deprecation warning during entity deserialization about calling
`df_loads` without `expected_type`. Build tooling emits existing license-metadata
deprecation warnings. Neither warning was suppressed.

No deployed Functions host, external model, or storage service was exercised.
The execution test uses the real indexed SDK entity handler, protobuf transport,
DAFX execution and tasks, and serialized entity state between turns. Only its
model and orchestration scheduler are test substitutes.

## Change analysis

- Initialization and provider configuration still happen before binding decoration.
  Existing constructor/decorator contract tests and both original suites pass.
- The old activity-based `call_agent()` remains unchanged. Its decoration/indexing
  path does not construct the inner app. Explicit registration is a separate API.
- Both function registries are included, including SDK built-ins. HTTP auth is
  preserved. Duplicate names, repeated indexing, and retry after correcting a
  collision are tested. The SDK name-validation state is reset on each pass.
- Agent lookup does not import or create DAFX. Explicit registration after indexing
  is rejected. Re-registering the same instance is idempotent, but a different
  instance with the same case-insensitive name is rejected.
- Missing, empty, whitespace-only, and non-string names are rejected before DAFX
  creation. Missing DAFX produces installation guidance; a broken transitive
  import preserves its original error. Different apps own separate registries.
- SDK built-in names are derived from the real inner registry for collision tests.
  The sample index test separately pins the expected complete function list.
- The initial 20 new DAFX tests fail against the untouched PR head because the
  new API/state is absent, then pass with the implementation present. In-memory
  mutations removing inner functions and removing the inner validation reset
  each fail three targeted tests for the expected behavior. No source file was
  mutated by those probes.
- An independent read-only review prompted additional app-isolation and
  indexing-recovery tests. Its proposed blanket guard against adding any decorator
  after indexing was not adopted: the original SDK and PR already allow that;
  this prototype guards only its new durable-agent registration API.
- Documentation and dependency declarations were checked together. Both DAFX Git
  pins occur only in the optional extra; CI explicitly installs that extra for
  framework tests. These prototype Git dependencies are not a PyPI release plan.

See the adjacent README for installation and test commands. Full suites cover
the two agent packages, not unrelated extensions elsewhere in the repository.
