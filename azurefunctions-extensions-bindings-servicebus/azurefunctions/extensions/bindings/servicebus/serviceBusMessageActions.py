# Copyright (c) .NET Foundation. All rights reserved.
# Licensed under the MIT License.
import threading

from typing import Optional

from azurefunctions.extensions.base import GrpcClientType
from google.protobuf.wrappers_pb2 import StringValue

from ..protos.settlement_pb2 import (
    AbandonRequest,
    CompleteRequest,
    DeadletterRequest,
    DeferRequest,
    GetSessionStateRequest,
    ReleaseSessionRequest,
    RenewMessageLockRequest,
    RenewSessionLockRequest,
    SetSessionStateRequest,
)
from ..protos.settlement_pb2_grpc import SettlementStub

from .grpcClient import GrpcClientFactory
from .grpc_utils import get_grpc_uri, get_grpc_max_message_length, parse_grpc_args
from .utils import convert_to_bytestring


class SettlementError(Exception):
    """Custom exception for ServiceBusMessageActions errors."""
    def __init__(self, method: str, details: str, original: Exception):
        super().__init__(f"[{method}] {details}. Underlying error: {original}")
        self.method = method
        self.details = details
        self.original = original


class ServiceBusMessageActions(GrpcClientType):
    """
    ServiceBusMessageActions class.
    Provides async methods for message settlement over gRPC.
    Implements a singleton pattern.
    """

    _instance: Optional["ServiceBusMessageActions"] = None
    _lock = threading.Lock()  # class-level lock

    def __init__(self) -> None:
        args = parse_grpc_args()
        self._uri = get_grpc_uri(args)
        self._grpc_max_message_length = get_grpc_max_message_length(args)

        self._client: SettlementStub = GrpcClientFactory.create_client(
            service_stub=SettlementStub,
            address=self._uri,
            grpc_max_message_length=self._grpc_max_message_length,
        )

    @classmethod
    def get_instance(cls) -> "ServiceBusMessageActions":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ServiceBusMessageActions()
        return cls._instance

    def _validate_lock_token(self, message) -> str:
        locktoken = message.lock_token
        if not locktoken:
            raise ValueError("lockToken is required in ServiceBusReceivedMessage.")
        return locktoken

    # -------------------------------
    # Settlement methods
    # -------------------------------

    def complete(self, message) -> None:
        try:
            locktoken = self._validate_lock_token(message)
            request = CompleteRequest()
            request.locktoken = str(locktoken)
            self._client.Complete(request)
        except Exception as e:
            raise SettlementError("complete",
                                  f"Failed to complete message {locktoken}", e)

    def abandon(self, message, properties_to_modify: Optional[dict] = {}) -> None:
        try:
            locktoken = self._validate_lock_token(message)
            request = AbandonRequest()
            request.locktoken = str(locktoken)
            request.propertiesToModify = convert_to_bytestring(properties_to_modify)
            self._client.Abandon(request)
        except Exception as e:
            raise SettlementError("abandon",
                                  f"Failed to abandon message {locktoken}", e)

    def deadletter(
            self,
            message,
            deadletter_reason: Optional[str] = None,
            deadletter_error_description: Optional[str] = None,
            properties_to_modify: Optional[dict] = {}) -> None:
        try:
            locktoken = self._validate_lock_token(message)
            request = DeadletterRequest()
            request.locktoken = str(locktoken)
            request.propertiesToModify = convert_to_bytestring(properties_to_modify)

            if deadletter_reason:
                request.deadletterReason.CopyFrom(StringValue(value=deadletter_reason))
            if deadletter_error_description:
                request.deadletterErrorDescription.CopyFrom(
                    StringValue(value=deadletter_error_description))

            self._client.Deadletter(request)
        except Exception as e:
            raise SettlementError("deadletter",
                                  f"Failed to deadletter message {locktoken}", e)

    def defer(self, message, properties_to_modify: Optional[dict] = {}) -> None:
        try:
            locktoken = self._validate_lock_token(message)
            request = DeferRequest()
            request.locktoken = str(locktoken)
            request.propertiesToModify = convert_to_bytestring(properties_to_modify)

            self._client.Defer(request)
        except Exception as e:
            raise SettlementError("defer", f"Failed to defer message {locktoken}", e)

    def renew_message_lock(self, message) -> None:
        try:
            locktoken = self._validate_lock_token(message)
            request = RenewMessageLockRequest()
            request.locktoken = str(locktoken)
            self._client.RenewMessageLock(request)
        except Exception as e:
            raise SettlementError("renew_message_lock",
                                  f"Failed to renew lock for {locktoken}", e)
        
    def get_session_state(self, session_id: str) -> bytes:
        try:
            request = GetSessionStateRequest()
            request.sessionId = session_id
            response = self._client.GetSessionState(request)
            return response.sessionState
        except Exception as e:
            raise SettlementError("get_session_state",
                                  f"Failed to get state for session {session_id}", e)

    def set_session_state(self, session_id: str, session_state: bytes) -> None:
        try:
            request = SetSessionStateRequest()
            request.sessionId = session_id
            request.sessionState = session_state
            self._client.SetSessionState(request)
        except Exception as e:
            raise SettlementError("set_session_state",
                                  f"Failed to set state for session {session_id}", e)

    def release_session(self, session_id: str) -> None:
        try:
            request = ReleaseSessionRequest()
            request.sessionId = session_id
            self._client.ReleaseSession(request)
        except Exception as e:
            raise SettlementError("release_session",
                                  f"Failed to release session {session_id}", e)

    def renew_session_lock(self, session_id: str):
        try:
            request = RenewSessionLockRequest()
            request.sessionId = session_id
            response = self._client.RenewSessionLock(request)
        except Exception as e:
            raise SettlementError("renew_session_lock", f"Failed to renew "
                                  f"lock for session {session_id}", e)

        if not response or not response.lockedUntil:
            raise RuntimeError("No response or lockedUntil returned "
                               "from renewSessionLock")

        return response.lockedUntil
