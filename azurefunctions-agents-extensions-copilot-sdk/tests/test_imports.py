import subprocess
import sys


def test_copilot_sdk_exports_supported_api():
    import azurefunctions.agents.extensions.copilot_sdk as copilot_sdk
    from azurefunctions.agents.extensions.base.durable import DurableAgentContext

    assert copilot_sdk.AgentFunctionApp is not None
    assert not hasattr(copilot_sdk, "CopilotSessionOptions")
    assert copilot_sdk.DurableAgentContext is DurableAgentContext
    assert copilot_sdk.COPILOT_SDK_PROVIDER_ID == "copilot_sdk"
    assert not hasattr(copilot_sdk, "markdown_agent")


def test_copilot_sdk_import_does_not_import_durable():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.abc\n"
                "import sys\n"
                "class BlockDurable(importlib.abc.MetaPathFinder):\n"
                " def find_spec(self, fullname, path, target=None):\n"
                "  if fullname == 'azure.durable_functions' or "
                "fullname.startswith('azure.durable_functions.'):\n"
                "   raise ModuleNotFoundError(name=fullname)\n"
                "sys.meta_path.insert(0, BlockDurable())\n"
                "import azurefunctions.agents.extensions.copilot_sdk\n"
                "assert 'azure.durable_functions' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
