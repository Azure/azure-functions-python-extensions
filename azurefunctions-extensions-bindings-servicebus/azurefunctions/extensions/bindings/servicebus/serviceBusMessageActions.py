# Copyright (c) .NET Foundation. All rights reserved.
# Licensed under the MIT License.

from typing import Optional
from protos.settlement_pb2 import (
    AbandonRequest,
    CompleteRequest,
    DeadletterRequest,
    DeferRequest,
    ReleaseSessionRequest,
    RenewMessageLockRequest,
    RenewSessionLockRequest,
    SetSessionStateRequest,
)
from protos.settlement_pb2_grpc import SettlementStub

from .grpcClient import GrpcClientFactory
from .grpc_utils import build_grpc_uri


class ServiceBusMessageActions:
    """
    ServiceBusMessageActions class.
    Provides async methods for message settlement over gRPC.
    Implements a singleton pattern.
    """

    _instance: Optional["ServiceBusMessageActions"] = None

    def __init__(self) -> None:
        uri, grpc_max_message_length = build_grpc_uri()

        self._client: SettlementStub = GrpcClientFactory.create_client(
            service_stub=SettlementStub,
            address=uri,
            grpc_max_message_length=grpc_max_message_length,
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

    async def complete(self, message) -> None:
        locktoken = self._validate_lock_token(message)
        request = CompleteRequest(locktoken=locktoken)
        await self._client.Complete(request)

    async def abandon(self, message, properties_to_modify: bytes = b"") -> None:
        locktoken = self._validate_lock_token(message)
        request = AbandonRequest(locktoken=locktoken, propertiesToModify=properties_to_modify)
        await self._client.Abandon(request)

    async def deadletter(
        self,
        message,
        properties_to_modify: bytes = b"",
        deadletter_reason: Optional[str] = None,
        deadletter_error_description: Optional[str] = None,
    ) -> None:
        locktoken = self._validate_lock_token(message)
        request = DeadletterRequest(
            locktoken=locktoken,
            propertiesToModify=properties_to_modify,
            deadletterReason=deadletter_reason or "",
            deadletterErrorDescription=deadletter_error_description or "",
        )
        await self._client.Deadletter(request)

    async def defer(self, message, properties_to_modify: bytes = b"") -> None:
        locktoken = self._validate_lock_token(message)
        request = DeferRequest(locktoken=locktoken, propertiesToModify=properties_to_modify)
        await self._client.Defer(request)

    async def renew_message_lock(self, message) -> None:
        locktoken = self._validate_lock_token(message)
        request = RenewMessageLockRequest(locktoken=locktoken)
        await self._client.RenewMessageLock(request)

    async def set_session_state(self, session_id: str, session_state: bytes) -> None:
        request = SetSessionStateRequest(sessionId=session_id, sessionState=session_state)
        await self._client.SetSessionState(request)

    async def release_session(self, session_id: str) -> None:
        request = ReleaseSessionRequest(sessionId=session_id)
        await self._client.ReleaseSession(request)

    async def renew_session_lock(self, session_id: str) -> str:
        request = RenewSessionLockRequest(sessionId=session_id)
        response = await self._client.RenewSessionLock(request)
        if not response or not response.lockedUntil:
            raise RuntimeError("No response or lockedUntil returned from renewSessionLock")
        return response.lockedUntil
