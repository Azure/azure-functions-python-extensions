import subprocess
import sys
import textwrap

import pytest


def test_framework_exports_supported_api():
    import azurefunctions.agents.extensions.agent_framework as framework

    assert framework.AgentFunctionApp is not None
    assert not hasattr(framework, "DurableAgentContext")
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


def test_non_durable_binding_runs_with_all_durable_imports_blocked(tmp_path):
    (tmp_path / "orders.agent.md").write_text("Handle orders.", encoding="utf-8")
    script = textwrap.dedent("""\
        import asyncio
        import importlib.abc
        import sys

        blocked = (
            'agent_framework_declarative',
            'yaml',
            'powerfx',
            'agent_framework_azurefunctions',
            'agent_framework_durabletask',
            'azure.durable_functions',
            'durabletask',
        )

        class BlockDurable(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == name or fullname.startswith(name + '.')
                       for name in blocked):
                    raise ModuleNotFoundError(name=fullname)

        sys.meta_path.insert(0, BlockDurable())
        import azure.functions as func
        from agent_framework import Agent, BaseChatClient
        from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp

        class LocalClient(BaseChatClient):
            def _inner_get_response(self, **kwargs):
                raise AssertionError('No model calls are expected')

        app = AgentFunctionApp(client_factory=LocalClient, app_root=sys.argv[1])

        @app.route(route='orders')
        @app.markdown_agent(arg_name='agent', agent_name='orders')
        async def orders(req: func.HttpRequest, agent: Agent):
            return func.HttpResponse(agent.name)

        indexed = app.get_functions()
        assert [f.get_function_name() for f in indexed] == ['orders']
        response = asyncio.run(indexed[0].get_user_function()(
            func.HttpRequest(method='GET', url='http://localhost/orders', body=b'')
        ))
        assert response.get_body() == b'orders'
        assert app._durable_app is None
        assert not any(module == name or module.startswith(name + '.')
                       for module in sys.modules for name in blocked)
    """)
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("missing", ["agent_framework_azurefunctions", "grpc"])
def test_dafx_import_errors_are_actionable_without_hiding_broken_installs(
    monkeypatch, tmp_path, missing
):
    import builtins
    from types import SimpleNamespace

    from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp

    app = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path)
    original_import = builtins.__import__

    def fail_dafx_import(name, *args, **kwargs):
        if name == "_hosting":
            raise ModuleNotFoundError(f"No module named {missing!r}", name=missing)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_dafx_import)
    app.add_durable_agent(SimpleNamespace(name="Orders"))
    assert set(app._durable_agents) == {"Orders"}
    assert app._durable_app is None
    with pytest.raises(ImportError) as caught:
        app.get_functions()
    if missing == "agent_framework_azurefunctions":
        assert "[durable]" in str(caught.value)
        assert isinstance(caught.value.__cause__, ModuleNotFoundError)
    else:
        assert isinstance(caught.value, ModuleNotFoundError)
        assert caught.value.name == "grpc"
    assert app._durable_app is None
