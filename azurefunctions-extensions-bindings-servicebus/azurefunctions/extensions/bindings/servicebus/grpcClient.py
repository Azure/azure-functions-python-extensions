# Copyright (c) .NET Foundation. All rights reserved.
# Licensed under the MIT License.

import grpc
from typing import Any, Type


class GrpcClientFactory:
    """
    Factory class for creating gRPC clients from generated Python stubs.

    Python requires `.proto` files to be compiled into
    `_pb2.py` and `_pb2_grpc.py` modules before use. This factory assumes
    those files are already generated and importable.

    Example:
        from my_service_pb2_grpc import MyServiceStub

        client = GrpcClientFactory.create_client(
            service_stub=MyServiceStub,
            address="localhost:50051",
            grpc_max_message_length=4 * 1024 * 1024,  # 4 MB
            secure=False,
        )
    """

    @staticmethod
    def create_client(
        service_stub: Type[Any],
        address: str,
        grpc_max_message_length: int = 4 * 1024 * 1024,
        secure: bool = False,
        root_certificates: bytes | None = None,
    ) -> Any:
        """
        Creates and returns a gRPC client for the given service stub.

        Args:
            service_stub: The generated service stub class (e.g. `MyServiceStub`).
            address: The server address (e.g., "localhost:50051").
            grpc_max_message_length: Max message size for send/receive.
            secure: If True, use a secure channel; otherwise, insecure.
            root_certificates: Optional root certificates for TLS.

        Returns:
            An instance of the gRPC client stub.
        """

        options = [
            ("grpc.max_send_message_length", grpc_max_message_length),
            ("grpc.max_receive_message_length", grpc_max_message_length),
        ]

        if secure:
            credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
            channel = grpc.secure_channel(address, credentials, options=options)
        else:
            channel = grpc.insecure_channel(address, options=options)

        return service_stub(channel)
