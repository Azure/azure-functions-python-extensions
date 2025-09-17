#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import grpc
import unittest

from unittest.mock import patch, MagicMock

from google.protobuf.timestamp_pb2 import Timestamp

from azurefunctions.extensions.bindings.servicebus import ServiceBusMessageActions
from azurefunctions.extensions.bindings.servicebus.serviceBusMessageActions import SettlementError  # noqa
from azurefunctions.extensions.bindings.protos import settlement_pb2 as pb2


class DummyMessage:
    def __init__(self, locktoken):
        self.lock_token = locktoken


class TestServiceBusMessageActions(unittest.TestCase):
    def setUp(self):
        ServiceBusMessageActions._instance = None
        # Patch create_client so we control what gets returned
        patcher = patch(
            "azurefunctions.extensions.bindings.servicebus.serviceBusMessageActions.GrpcClientFactory.create_client")  # noqa
        self.addCleanup(patcher.stop)
        self.mock_create_client = patcher.start()

        patcher_args = patch(
            "azurefunctions.extensions.bindings.servicebus.serviceBusMessageActions.parse_grpc_args")  # noqa
        self.addCleanup(patcher_args.stop)
        patcher_args.start()

        # Patch get_grpc_uri so we don't need CLI args
        patcher_uri = patch(
            "azurefunctions.extensions.bindings.servicebus.serviceBusMessageActions.get_grpc_uri",  # noqa
            return_value=("localhost:50051", 4 * 1024 * 1024))
        self.addCleanup(patcher_uri.stop)
        patcher_uri.start()

        patcher_message_length = patch(
            "azurefunctions.extensions.bindings.servicebus.serviceBusMessageActions.get_grpc_max_message_length")  # noqa
        self.addCleanup(patcher_message_length.stop)
        patcher_message_length.start()

        # The fake gRPC client returned by create_client
        self.mock_client = MagicMock()
        self.mock_client.Complete = MagicMock()
        self.mock_client.Abandon = MagicMock()
        self.mock_client.Deadletter = MagicMock()
        self.mock_client.Defer = MagicMock()
        self.mock_client.RenewMessageLock = MagicMock()
        self.mock_client.SetSessionState = MagicMock()
        self.mock_client.ReleaseSession = MagicMock()
        self.mock_client.RenewSessionLock = MagicMock()
        self.mock_create_client.return_value = self.mock_client

        # Now actions will use our patched client
        self.actions = ServiceBusMessageActions().get_instance()

    def tearDown(self):
        # Ensure singleton is cleared after each test too
        ServiceBusMessageActions._instance = None

    def test_complete_calls_grpc(self):
        msg = DummyMessage("lock123")
        self.actions.complete(msg)

        self.mock_client.Complete.assert_called_once()
        called_req = self.mock_client.Complete.call_args[0][0]
        self.assertIsInstance(called_req, pb2.CompleteRequest)
        self.assertEqual(called_req.locktoken, "lock123")

    def test_abandon_calls_grpc(self):
        msg = DummyMessage("lock123")
        self.actions.abandon(msg)

        self.mock_client.Abandon.assert_called_once()
        called_req = self.mock_client.Abandon.call_args[0][0]
        self.assertIsInstance(called_req, pb2.AbandonRequest)
        self.assertEqual(called_req.locktoken, "lock123")
        self.assertEqual(called_req.propertiesToModify, b"")

    def test_deadletter_with_reasons(self):
        msg = DummyMessage("lock123")
        self.actions.deadletter(
            msg,
            deadletter_reason="reason",
            deadletter_error_description="desc"
        )

        self.mock_client.Deadletter.assert_called_once()
        called_req = self.mock_client.Deadletter.call_args[0][0]
        self.assertIsInstance(called_req, pb2.DeadletterRequest)
        self.assertEqual(called_req.locktoken, "lock123")
        self.assertEqual(called_req.propertiesToModify, b"")
        self.assertEqual(called_req.deadletterReason.value, "reason")
        self.assertEqual(called_req.deadletterErrorDescription.value, "desc")

    def test_defer_calls_grpc(self):
        msg = DummyMessage("lock123")
        self.actions.defer(msg)

        self.mock_client.Defer.assert_called_once()
        called_req = self.mock_client.Defer.call_args[0][0]
        self.assertIsInstance(called_req, pb2.DeferRequest)
        self.assertEqual(called_req.locktoken, "lock123")
        self.assertEqual(called_req.propertiesToModify, b"")

    def test_renew_message_lock_calls_grpc(self):
        msg = DummyMessage("lock123")
        self.actions.renew_message_lock(msg)

        self.mock_client.RenewMessageLock.assert_called_once()
        called_req = self.mock_client.RenewMessageLock.call_args[0][0]
        self.assertIsInstance(called_req, pb2.RenewMessageLockRequest)
        self.assertEqual(called_req.locktoken, "lock123")

    def test_set_session_state(self):
        self.actions.set_session_state("sid", b"state")

        self.mock_client.SetSessionState.assert_called_once()
        called_req = self.mock_client.SetSessionState.call_args[0][0]
        self.assertIsInstance(called_req, pb2.SetSessionStateRequest)
        self.assertEqual(called_req.sessionId, "sid")
        self.assertEqual(called_req.sessionState, b"state")

    def test_release_session(self):
        self.actions.release_session("sid")

        self.mock_client.ReleaseSession.assert_called_once()
        called_req = self.mock_client.ReleaseSession.call_args[0][0]
        self.assertIsInstance(called_req, pb2.ReleaseSessionRequest)
        self.assertEqual(called_req.sessionId, "sid")

    def test_renew_session_lock_success(self):
        ts = Timestamp()
        ts.GetCurrentTime()
        # Mock gRPC response
        resp = pb2.RenewSessionLockResponse()
        resp.lockedUntil.CopyFrom(ts)
        self.mock_client.RenewSessionLock.return_value = resp

        result = self.actions.renew_session_lock("sid")

        self.mock_client.RenewSessionLock.assert_called_once()
        called_req = self.mock_client.RenewSessionLock.call_args[0][0]
        self.assertIsInstance(called_req, pb2.RenewSessionLockRequest)
        self.assertEqual(called_req.sessionId, "sid")
        self.assertIsInstance(result, Timestamp)
        self.assertEqual(result, ts)

    def test_renew_session_lock_failure(self):
        # No response
        self.mock_client.RenewSessionLock.return_value = None
        with self.assertRaises(RuntimeError):
            self.actions.renew_session_lock("sid")

    def test_validate_lock_token_raises(self):
        msg = DummyMessage(None)
        with self.assertRaises(ValueError):
            self.actions._validate_lock_token(msg)

    def test_complete_raises_SettlementError(self):
        msg = DummyMessage("lt1")
        self.mock_client.Complete.side_effect = grpc.RpcError("boom")

        with self.assertRaises(SettlementError) as cm:
            self.actions.complete(msg)

        self.assertIn("complete", str(cm.exception))
        self.assertIn("lt1", str(cm.exception))

    def test_abandon_raises_SettlementError(self):
        msg = DummyMessage("lt2")
        self.mock_client.Abandon.side_effect = grpc.RpcError("fail")

        with self.assertRaises(SettlementError) as cm:
            self.actions.abandon(msg)

        self.assertIn("abandon", str(cm.exception))
        self.assertIn("lt2", str(cm.exception))

    def test_deadletter_raises_SettlementError(self):
        msg = DummyMessage("lt3")
        self.mock_client.Deadletter.side_effect = grpc.RpcError("oops")

        with self.assertRaises(SettlementError) as cm:
            self.actions.deadletter(msg, deadletter_reason="reason")

        self.assertIn("deadletter", str(cm.exception))
        self.assertIn("lt3", str(cm.exception))

    def test_defer_raises_SettlementError(self):
        msg = DummyMessage("lt4")
        self.mock_client.Defer.side_effect = grpc.RpcError("bad")

        with self.assertRaises(SettlementError) as cm:
            self.actions.defer(msg)

        self.assertIn("defer", str(cm.exception))
        self.assertIn("lt4", str(cm.exception))

    def test_renew_message_lock_raises_SettlementError(self):
        msg = DummyMessage("lt5")
        self.mock_client.RenewMessageLock.side_effect = grpc.RpcError("err")

        with self.assertRaises(SettlementError) as cm:
            self.actions.renew_message_lock(msg)

        self.assertIn("renew_message_lock", str(cm.exception))
        self.assertIn("lt5", str(cm.exception))

    def test_set_session_state_raises_SettlementError(self):
        self.mock_client.SetSessionState.side_effect = grpc.RpcError("nope")

        with self.assertRaises(SettlementError) as cm:
            self.actions.set_session_state("sid1", b"state")

        self.assertIn("set_session_state", str(cm.exception))
        self.assertIn("sid1", str(cm.exception))

    def test_release_session_raises_SettlementError(self):
        self.mock_client.ReleaseSession.side_effect = grpc.RpcError("denied")

        with self.assertRaises(SettlementError) as cm:
            self.actions.release_session("sid2")

        self.assertIn("release_session", str(cm.exception))
        self.assertIn("sid2", str(cm.exception))

    def test_renew_session_lock_raises_SettlementError(self):
        self.mock_client.RenewSessionLock.side_effect = grpc.RpcError("boom")

        with self.assertRaises(SettlementError) as cm:
            self.actions.renew_session_lock("sid3")

        self.assertIn("renew_session_lock", str(cm.exception))
        self.assertIn("sid3", str(cm.exception))
