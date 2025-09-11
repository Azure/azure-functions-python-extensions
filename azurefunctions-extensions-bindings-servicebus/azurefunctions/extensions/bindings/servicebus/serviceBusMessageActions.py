# Copyright (c) .NET Foundation. All rights reserved.
# Licensed under the MIT License.

from typing import Optional

from azurefunctions.extensions.base import GrpcClientType
from google.protobuf.wrappers_pb2 import StringValue

from ..protos.settlement_pb2 import (
    AbandonRequest,
    CompleteRequest,
    DeadletterRequest,
    DeferRequest,
    ReleaseSessionRequest,
    RenewMessageLockRequest,
    RenewSessionLockRequest,
    SetSessionStateRequest,
)
from ..protos.settlement_pb2_grpc import SettlementStub

from .grpcClient import GrpcClientFactory
from .grpc_utils import build_grpc_uri


class ServiceBusMessageActions(GrpcClientType):
    """
    ServiceBusMessageActions class.
    Provides async methods for message settlement over gRPC.
    Implements a singleton pattern.
    """

    _instance: Optional["ServiceBusMessageActions"] = None

    def __init__(self) -> None:
        self._uri, self._grpc_max_message_length = build_grpc_uri()

        self._client: SettlementStub = GrpcClientFactory.create_client(
            service_stub=SettlementStub,
            address=self._uri,
            grpc_max_message_length=self._grpc_max_message_length,
            secure=False,
        )

    @classmethod
    def get_instance(cls) -> "ServiceBusMessageActions":
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

    def complete(self,
                 message
                 ) -> None:
        locktoken = self._validate_lock_token(message)
        request = CompleteRequest()
        request.locktoken = str(locktoken)
        self._client.Complete(request)

    def abandon(self,
                message,
                properties_to_modify: bytes = b""
                ) -> None:
        locktoken = self._validate_lock_token(message)
        request = AbandonRequest()
        request.locktoken = str(locktoken)
        request.propertiesToModify = properties_to_modify
        self._client.Abandon(request)

    def deadletter(self,
                   message,
                   properties_to_modify: bytes = b"",
                   deadletter_reason: Optional[str] = None,
                   deadletter_error_description: Optional[str] = None,
                   ) -> None:
        locktoken = self._validate_lock_token(message)
        request = DeadletterRequest()
        request.locktoken = str(locktoken)
        request.propertiesToModify = properties_to_modify

        if deadletter_reason:
            request.deadletterReason.CopyFrom(StringValue(value=deadletter_reason))

        if deadletter_error_description:
            request.deadletterErrorDescription.CopyFrom(
                StringValue(value=deadletter_error_description))
        self._client.Deadletter(request)

    def defer(self,
              message,
              properties_to_modify: bytes = b""
              ) -> None:
        locktoken = self._validate_lock_token(message)
        request = DeferRequest()
        request.locktoken = str(locktoken)
        request.propertiesToModify = properties_to_modify
        self._client.Defer(request)

    def renew_message_lock(self,
                           message
                           ) -> None:
        locktoken = self._validate_lock_token(message)
        request = RenewMessageLockRequest()
        request.locktoken = str(locktoken)
        self._client.RenewMessageLock(request)

    def set_session_state(self,
                          session_id: str,
                          session_state: bytes
                          ) -> None:
        request = SetSessionStateRequest()
        request.sessionId = session_id
        request.sessionState = session_state
        self._client.SetSessionState(request)

    def release_session(self,
                        session_id: str
                        ) -> None:
        request = ReleaseSessionRequest()
        request.sessionId = session_id
        self._client.ReleaseSession(request)

    def renew_session_lock(self,
                           session_id: str):
        request = RenewSessionLockRequest()
        request.sessionId = session_id
        response = self._client.RenewSessionLock(request)

        if not response or not response.lockedUntil:
            raise RuntimeError("No response or lockedUntil "
                               "returned from renewSessionLock")

        return response.lockedUntil
