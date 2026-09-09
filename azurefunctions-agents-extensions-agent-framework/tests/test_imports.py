import subprocess
import sys


def test_framework_exports_only_app_api():
    import azurefunctions.agents.extensions.agent_framework as framework

    assert framework.AgentFunctionApp is not None
    assert not hasattr(framework, "AgentDFApp")
    assert not hasattr(framework, "markdown_agent")


def test_framework_import_does_not_import_durable():
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
                "import azurefunctions.agents.extensions.agent_framework\n"
                "assert 'azure.durable_functions' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


