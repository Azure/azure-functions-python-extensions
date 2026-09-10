# YAML discovery verification

## Results

Native factory delegation was verified on Windows/Python 3.13.11 with core 1.16.0,
declarative 1.0.3, Functions 2.3.0, Durable 2.0.0rc1 and DAFX PR #72 at `aa9529ec`.

- Both agent-package suites passed 158 tests with workflow dependencies installed.
- Without YAML dependencies, 151 passed and seven YAML-only cases skipped.
- The clean non-durable installation passed five isolated import tests.
- Strict mypy passed on 12 source files. Flake8, whitespace, dependency consistency,
  documentation links, and both package wheel/source builds passed.
- The original nine YAML replay scenarios still pass. Thirteen additional native
  cases cover previously blocked MAF configuration, plus the configured sample.

An upstream `df_loads` deprecation warning remains visible. The tests do not hide
it. Python 3.14 execution is unverified rather than blocked by this extension.

## Current integration contract

- Discovery is limited to the two workflow suffixes directly in the app root or
  `workflows/`, with entry-file containment checks. Loaded results must be MAF
  `Workflow` objects with stable, valid names unique ignoring case.
- Loading calls public `create_workflow_from_yaml_path()`. MAF owns YAML parsing,
  action handling, native warnings/errors, and nested file resolution. References
  inside YAML are not sandboxed by the extension. Deploy only trusted files.
- The default factory receives all discovered Markdown adapters. A supplied
  factory is used unchanged, with no automatic Markdown registry merge. DAFX
  still validates and hosts the resulting graphs, and all discovered Markdown
  agents still get standalone endpoints.
- Markdown adapters create fresh resources per execution. Inline and
  custom-factory agents follow MAF's or the factory's lifecycle and may construct
  agents and clients during app initialization/indexing.
- The workflows extra accepts declarative `>=1.0.3,<2`. There is no private action
  registry dependency or extension-level Python 3.14 rejection. Python support
  follows MAF's dependencies. Expression execution is verified on 3.13 only,
  since declarative 1.0.3 excludes its PowerFx dependency on 3.14.

## Verification scope

The replay probes reconstruct the app and YAML graphs before orchestration
activations and activities. They execute the actual SDK protobuf orchestration
handler and registered DAFX activities with in-memory storage/dispatch history.
Native-feature probes cover inline and relative-file agents, dynamic agent
selection with default and custom factories, sync/async function tools, local
HTTP/MCP handlers, configuration-only and environment-fallback expressions, and
the absence of automatic Markdown merging into a custom factory. This is not an
exhaustive claim of MAF feature parity.

## Change analysis

- Removed custom parsing, action traversal/allowlists, the internal action registry
  import, and the inline/file/dynamic/tool/Python version gates. Tests now compare
  duplicate-key, unknown-action, root-precedence and trigger-name behavior with
  the public MAF factory instead of enforcing a second YAML dialect.
- Discovery boundaries and returned Workflow/name checks remain. The exact supplied
  factory instance receives both file paths without extra method calls or mutation.
  Its exceptions propagate; it need not import the default declarative loader.
- Default factories receive all markdown adapters, allowing runtime selection.
  Supplied factories receive no implicit merge. The negative missing-agent case
  verifies a same-named discovered Markdown file cannot override a custom registry.
- Native agent creation is intentionally permitted during loading. Real AgentFactory
  public methods parse/build inline and relative-file agents using a local client.
  Local HTTP/MCP handlers and registered sync/async tools execute once across replay,
  with complete expected arguments/state checked. No external network is involved.
- Review found a stale mutation stub after adding the factory keyword. Its signature
  is corrected: removing workflow loading fails on missing `dafx-Simple`, not a
  keyword error. Ignoring the supplied factory also fails the native construction
  assertion. Restored workflow tests pass all 21 collected cases.
- The sample index enumerates every sample app. The configured factory sample uses
  its actual `format_order` implementation and configuration through SDK replay.
  Documentation and sample-index claims were checked together.

The documented sample outputs are `["User turn 1: Review order 42."]` for
`OrderReview` and `["approved"]` after responding to `Approval`. The
[configured factory sample](../configured-workflow-factory/README.md) expects
`["Local order 42."]` for `ConfiguredTools`.

No live Functions host, storage backend, external model, or external HTTP/MCP
service is part of these checks. Retries, parallel execution, and nested
workflows are not claimed as verified. The subprocess helpers exit after all
assertions to isolate embedded PowerFx/CLR shutdown from pytest reporting, not
to bypass application logic or assertions.
