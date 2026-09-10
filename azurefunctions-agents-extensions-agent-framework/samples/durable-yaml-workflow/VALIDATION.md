# YAML discovery verification

Verified on Windows, Python 3.13.11, core 1.16.0, declarative 1.0.3,
Functions 2.3.0, Durable 2.0.0rc1 and DAFX PR #72 at `aa9529ec`.

- Both agent-package suites passed 152 tests with the optional workflows package.
- Without YAML dependencies, 148 tests passed and four YAML-only tests skipped.
- The fresh non-durable environment passed five import tests with YAML, PowerFx,
  DAFX and Durable imports blocked.
- Strict mypy passed on 12 source files. Flake8, whitespace, dependency consistency,
  and both package wheel/source builds passed.

The YAML subprocess suite contains nine replay cases: simple output, shared state,
ConditionGroup true/else branches, Foreach, an agent call, Question pause/resume,
and agent calls inside both If branches. Each reconstructs the outer app and YAML
graph before every orchestration activation and activity. The actual SDK protobuf
orchestration handler and registered DAFX activities execute; only storage and
dispatch are represented by in-memory history. Agent calls open/close a fresh
client and do not repeat during orchestration replay.

The sample's real local client and documented order input produce
`["User turn 1: Review order 42."]`; Approval resumes with `["approved"]`.
Its complete 20-function index and generated endpoint metadata are checked.

## Change analysis

- Workflow loading precedes construction of the one owned DAFX app. Plain and
  markdown-only paths do not import the declarative package. Existing binding
  registration, HTTP auth and repeated indexing tests remain green.
- Discovery handles both suffixes and locations, validates explicit stable names,
  duplicate keys/names, YAML cycles, malformed definitions, directories and
  escaping symlinks. Arbitrary YAML elsewhere is not discovered.
- Registration keeps live resources out of indexing. Inline/file-based YAML agent
  definitions and dynamic agent names fail rather than constructing hidden clients.
- The action walker follows the pinned loader's If and ConditionGroup structures,
  not arbitrary literal dictionaries. Unknown actions fail instead of being skipped.
  Conflicting root/trigger or If branch definitions are rejected. Workflow-level
  tools without registered handlers fail; agent-level tools are unaffected.
- A read-only review found missing If branch discovery. A real replay reproduced
  `Agent 'writer' invocation failed: not found in registry`; both branches pass
  after correction. It also identified shadowed action lists and unconfigured
  function tools, now covered by rejection tests.
- Removing workflow loading in an in-memory mutation makes the replay test fail
  on missing `dafx-Simple`; restoring the implementation passes all workflow tests.
  The earlier shared-state-loss mutation also failed the expected output assertion.
- Action registry knowledge comes from the pinned declarative loader. Structural
  action traversal is tested with root/trigger forms, nested If, ConditionGroup,
  Foreach, and literal data containing keys named `actions`.

No live Functions host, storage backend, external model or MCP service was run.
Retries, parallel execution and nested workflows are not claimed as verified.
The subprocess helper exits after all assertions to isolate embedded PowerFx/CLR
shutdown behavior from pytest. It does not bypass application logic or assertions.
YAML support is limited to Python 3.13 until the PowerFx dependency supports 3.14.
