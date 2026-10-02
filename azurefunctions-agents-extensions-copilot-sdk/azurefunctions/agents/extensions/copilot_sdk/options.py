from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from copilot import ToolSet
from copilot.canvas import (
    CanvasDeclaration,
    CanvasHandler,
    CanvasProviderIdentity,
    ExtensionInfo,
)
from copilot.client import (
    AskUserVariant,
    CapiSessionOptions,
    CloudSessionOptions,
    CopilotExpAssignmentResponse,
    GitHubTokenProvider,
    ManagedSettings,
)
from copilot.generated.rpc import RemoteSessionMode
from copilot.generated.session_events import SessionEvent
from copilot.session import (
    AutoModeSwitchHandler,
    CommandDefinition,
    ContextTier,
    CreateSessionFsHandler,
    CustomAgentConfig,
    DefaultAgentConfig,
    ElicitationHandler,
    ExitPlanModeHandler,
    GitHubMcpToolConfig,
    InfiniteSessionConfig,
    LargeToolOutputConfig,
    McpAuthHandler,
    MCPServerConfig,
    MemoryConfiguration,
    ModelCapabilitiesOverride,
    NamedProviderConfig,
    ProviderModelConfig,
    ReasoningEffort,
    ReasoningSummary,
    SessionHooks,
    SessionLimitsConfig,
    SystemMessageConfig,
    ToolSearchConfig,
    UserInputHandler,
)
from typing_extensions import TypedDict


class CopilotSessionOptions(  # type: ignore[call-arg]  # mypy lacks PEP 728
    TypedDict,
    total=False,
    extra_items=object,
):
    """Optional arguments forwarded to ``CopilotClient.create_session``."""

    session_id: str | None
    client_name: str | None
    reasoning_effort: ReasoningEffort | None
    reasoning_summary: ReasoningSummary | None
    enable_experimental_mode: bool | None
    context_tier: ContextTier | None
    system_message: SystemMessageConfig | None
    tool_search: ToolSearchConfig | None
    available_tools: list[str] | ToolSet | None
    excluded_tools: list[str] | ToolSet | None
    on_user_input_request: UserInputHandler | None
    ask_user_variant: AskUserVariant | None
    hooks: SessionHooks | None
    working_directory: str | None
    additional_directories: list[str] | None
    capi: CapiSessionOptions | None
    providers: list[NamedProviderConfig] | None
    models: list[ProviderModelConfig] | None
    enable_session_telemetry: bool | None
    enable_citations: bool | None
    enable_file_change_tracking: bool | None
    excluded_builtin_agents: list[str] | None
    session_limits: SessionLimitsConfig | None
    skip_custom_instructions: bool | None
    custom_agents_local_only: bool | None
    coauthor_enabled: bool | None
    manage_schedule_enabled: bool | None
    model_capabilities: ModelCapabilitiesOverride | None
    streaming: bool | None
    include_sub_agent_streaming_events: bool | None
    mcp_servers: dict[str, MCPServerConfig] | None
    mcp_oauth_token_storage: Literal["persistent", "in-memory"] | None
    auth_client_id_metadata_url: str | None
    embedding_cache_storage: Literal["persistent", "in-memory"] | None
    custom_agents: list[CustomAgentConfig] | None
    default_agent: DefaultAgentConfig | dict[str, Any] | None
    agent: str | None
    config_directory: str | None
    enable_config_discovery: bool | None
    skip_embedding_retrieval: bool | None
    organization_custom_instructions: str | None
    enable_on_demand_instruction_discovery: bool | None
    enable_file_hooks: bool | None
    enable_host_git_operations: bool | None
    enable_session_store: bool | None
    enable_skills: bool | None
    included_builtin_skills: list[str] | None
    skill_directories: list[str] | None
    plugin_directories: list[str] | None
    instruction_directories: list[str] | None
    disabled_skills: list[str] | None
    disabled_mcp_servers: list[str] | None
    infinite_sessions: InfiniteSessionConfig | None
    large_output: LargeToolOutputConfig | None
    memory: MemoryConfiguration | None
    on_event: Callable[[SessionEvent], None] | None
    commands: list[CommandDefinition] | None
    on_elicitation_request: ElicitationHandler | None
    on_mcp_auth_request: McpAuthHandler | None
    enable_mcp_apps: bool
    on_exit_plan_mode_request: ExitPlanModeHandler | None
    on_auto_mode_switch_request: AutoModeSwitchHandler | None
    create_session_fs_handler: CreateSessionFsHandler | None
    github_token: str | None
    github_token_provider: GitHubTokenProvider | None
    remote_session: RemoteSessionMode | None
    cloud: CloudSessionOptions | None
    canvases: list[CanvasDeclaration] | None
    request_canvas_renderer: bool | None
    request_extensions: bool | None
    extension_sdk_path: str | None
    extension_info: ExtensionInfo | None
    canvas_provider: CanvasProviderIdentity | None
    canvas_handler: CanvasHandler | None
    feature_flags: dict[str, bool] | None
    exp_assignments: CopilotExpAssignmentResponse | None
    enable_managed_settings: bool | None
    github_mcp_tool_config: GitHubMcpToolConfig | None
    managed_settings: ManagedSettings | None
