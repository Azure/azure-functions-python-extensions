#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import pytest
import unittest

from unittest.mock import patch, MagicMock

from google.protobuf.timestamp_pb2 import Timestamp

from azurefunctions.extensions.bindings.servicebus import ServiceBusMessageActions
from azurefunctions.extensions.bindings.protos import settlement_pb2 as pb2


@pytest.fixture
def mock_client():
    """Patch the GrpcClientFactory to return a mock SettlementStub."""
    with patch("azurefunctions.extensions.bindings.servicebus.GrpcClientFactory.create_client") as mock_factory: # noqa
        client = MagicMock()
        mock_factory.return_value = client
        yield client


@pytest.fixture
def actions(mock_client):
    """Return a fresh ServiceBusMessageActions instance with mocked gRPC client."""
    # Clear singleton
    ServiceBusMessageActions._instance = None
    return ServiceBusMessageActions.get_instance()


class DummyMessage:
    def __init__(self, lock_token=None):
        self.lock_token = lock_token


class TestServiceBusMessageActions(unittest.TestCase):
    def test_complete_calls_grpc(actions, mock_client):
        msg = DummyMessage("lock123")
        actions.complete(msg)
        # Check that gRPC method was called
        called_req = mock_client.Complete.call_args[0][0]
        assert isinstance(called_req, pb2.CompleteRequest)
        assert called_req.locktoken == "lock123"

    def test_abandon_calls_grpc(actions, mock_client):
        msg = DummyMessage("lock123")
        actions.abandon(msg, properties_to_modify=b"foo")
        called_req = mock_client.Abandon.call_args[0][0]
        assert isinstance(called_req, pb2.AbandonRequest)
        assert called_req.locktoken == "lock123"
        assert called_req.propertiesToModify == b"foo"

    def test_deadletter_with_reasons(actions, mock_client):
        msg = DummyMessage("lock123")
        actions.deadletter(
            msg,
            properties_to_modify=b"p",
            deadletter_reason="reason",
            deadletter_error_description="desc"
        )
        called_req = mock_client.Deadletter.call_args[0][0]
        assert isinstance(called_req, pb2.DeadletterRequest)
        assert called_req.locktoken == "lock123"
        assert called_req.propertiesToModify == b"p"
        assert called_req.deadletterReason.value == "reason"
        assert called_req.deadletterErrorDescription.value == "desc"

    def test_defer_calls_grpc(actions, mock_client):
        msg = DummyMessage("lock123")
        actions.defer(msg, properties_to_modify=b"defer")
        called_req = mock_client.Defer.call_args[0][0]
        assert isinstance(called_req, pb2.DeferRequest)
        assert called_req.locktoken == "lock123"
        assert called_req.propertiesToModify == b"defer"

    def test_renew_message_lock_calls_grpc(actions, mock_client):
        msg = DummyMessage("lock123")
        actions.renew_message_lock(msg)
        called_req = mock_client.RenewMessageLock.call_args[0][0]
        assert isinstance(called_req, pb2.RenewMessageLockRequest)
        assert called_req.locktoken == "lock123"

    def test_set_session_state(actions, mock_client):
        actions.set_session_state("sid", b"state")
        called_req = mock_client.SetSessionState.call_args[0][0]
        assert isinstance(called_req, pb2.SetSessionStateRequest)
        assert called_req.sessionId == "sid"
        assert called_req.sessionState == b"state"

    def test_release_session(actions, mock_client):
        actions.release_session("sid")
        called_req = mock_client.ReleaseSession.call_args[0][0]
        assert isinstance(called_req, pb2.ReleaseSessionRequest)
        assert called_req.sessionId == "sid"

    def test_renew_session_lock_success(actions, mock_client):
        ts = Timestamp()
        ts.GetCurrentTime()
        mock_client.RenewSessionLock.return_value.lockedUntil.CopyFrom(ts)

        result = actions.renew_session_lock("sid")

        called_req = mock_client.RenewSessionLock.call_args[0][0]
        assert isinstance(called_req, pb2.RenewSessionLockRequest)
        assert called_req.sessionId == "sid"
        assert isinstance(result, Timestamp)  # raw proto object returned
        assert result == ts

    def test_renew_session_lock_failure(actions, mock_client):
        # No response
        mock_client.RenewSessionLock.return_value = None
        with pytest.raises(RuntimeError):
            actions.renew_session_lock("sid")

        # Empty response
        empty_resp = pb2.RenewSessionLockResponse()
        mock_client.RenewSessionLock.return_value = empty_resp
        with pytest.raises(RuntimeError):
            actions.renew_session_lock("sid")

    def test_validate_lock_token_raises(actions):
        msg = DummyMessage(None)
        with pytest.raises(ValueError):
            actions._validate_lock_token(msg)
