from __future__ import annotations

from types import SimpleNamespace

import pytest

from azurefunctions.extensions.agents_base import providers


class _Provider:
    provider_id = "agent_framework"
    distribution_name = "azurefunctions-extensions-agents-framework"

    def compile_binding(self, **kwargs):
        return kwargs


class _EntryPoint:
    def __init__(self, name, value, factory, distribution):
        self.name = name
        self.value = value
        self._factory = factory
        self.dist = SimpleNamespace(name=distribution)

    def load(self):
        return self._factory


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    providers._provider_entry_points.cache_clear()
    providers.load_provider.cache_clear()
    yield
    providers.load_provider.cache_clear()
    providers._provider_entry_points.cache_clear()


def test_load_provider_uses_matching_entry_point(monkeypatch):
    entry_point = _EntryPoint(
        "agent_framework",
        "test:provider",
        _Provider,
        "azurefunctions-extensions-agents-framework",
    )
    monkeypatch.setattr(
        providers.metadata,
        "entry_points",
        lambda **kwargs: [entry_point],
    )

    provider = providers.load_provider("agent_framework")

    assert provider.provider_id == "agent_framework"
    assert providers.load_provider("agent_framework") is provider


def test_provider_entry_points_are_enumerated_once_for_multiple_ids(monkeypatch):
    class OtherProvider(_Provider):
        provider_id = "other"
        distribution_name = "other-provider"

    entry_points = [
        _EntryPoint(
            "agent_framework",
            "test:provider",
            _Provider,
            "azurefunctions-extensions-agents-framework",
        ),
        _EntryPoint("other", "test:other", OtherProvider, "other-provider"),
    ]
    calls = 0

    def enumerate_entry_points(**kwargs):
        nonlocal calls
        calls += 1
        return entry_points

    monkeypatch.setattr(providers.metadata, "entry_points", enumerate_entry_points)

    assert providers.load_provider("agent_framework").provider_id == "agent_framework"
    assert providers.load_provider("other").provider_id == "other"
    assert calls == 1


def test_load_provider_reports_installable_distribution(monkeypatch):
    monkeypatch.setattr(providers.metadata, "entry_points", lambda **kwargs: [])

    with pytest.raises(LookupError, match="azurefunctions-extensions-agents-framework"):
        providers.load_provider("agent_framework")


def test_load_provider_rejects_duplicate_provider_ids(monkeypatch):
    entry_points = [
        _EntryPoint("agent_framework", "one:provider", _Provider, "provider-one"),
        _EntryPoint("agent_framework", "two:provider", _Provider, "provider-two"),
    ]
    monkeypatch.setattr(
        providers.metadata,
        "entry_points",
        lambda **kwargs: entry_points,
    )

    with pytest.raises(RuntimeError, match="provider-one, provider-two"):
        providers.load_provider("agent_framework")


def test_load_provider_does_not_rewrite_factory_error(monkeypatch):
    def fail():
        raise RuntimeError("provider initialization failed")

    entry_point = _EntryPoint("agent_framework", "test:fail", fail, "provider")
    monkeypatch.setattr(
        providers.metadata,
        "entry_points",
        lambda **kwargs: [entry_point],
    )

    with pytest.raises(RuntimeError, match="provider initialization failed"):
        providers.load_provider("agent_framework")


def test_load_provider_validates_returned_provider_id(monkeypatch):
    class WrongProvider(_Provider):
        provider_id = "wrong"

    entry_point = _EntryPoint(
        "agent_framework",
        "test:wrong",
        WrongProvider,
        "provider",
    )
    monkeypatch.setattr(
        providers.metadata,
        "entry_points",
        lambda **kwargs: [entry_point],
    )

    with pytest.raises(ValueError, match="returned provider 'wrong'"):
        providers.load_provider("agent_framework")
