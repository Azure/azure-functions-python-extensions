#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from unittest.mock import patch, MagicMock

from azurefunctions.extensions.bindings.servicebus.grpcClient import (GrpcClientFactory,
                                                                      GrpcChannelError)
from azurefunctions.extensions.bindings.servicebus.grpc_utils import (
    get_grpc_uri,
    get_grpc_max_message_length,
    parse_grpc_args,
    ArgumentError)


class DummyStub:
    def __init__(self, channel):
        self._channel = channel


class TestGrpcClient(unittest.TestCase):
    def test_create_client_insecure_channel(self):
        with patch("azurefunctions.extensions.bindings.servicebus.grpcClient.grpc.insecure_channel") as mock_insecure: # noqa
            fake_channel = MagicMock()
            mock_insecure.return_value = fake_channel

            client = GrpcClientFactory.create_client(
                service_stub=DummyStub,
                address="localhost:1234",
                grpc_max_message_length=1024,
            )

            mock_insecure.assert_called_once()
            args, kwargs = mock_insecure.call_args
            assert args[0] == "localhost:1234"
            assert ("grpc.max_send_message_length", 1024) in kwargs["options"]
            assert ("grpc.max_receive_message_length", 1024) in kwargs["options"]

            assert isinstance(client, DummyStub)
            assert client._channel == fake_channel

    @patch("azurefunctions.extensions.bindings.servicebus.grpcClient."
           "grpc.insecure_channel")
    def test_create_client_raises_on_insecure_channel_failure(self,
                                                              mock_insecure_channel):
        # Arrange: force grpc.insecure_channel to throw
        mock_insecure_channel.side_effect = RuntimeError("connection failed")

        # Act + Assert
        with self.assertRaises(GrpcChannelError) as ctx:
            GrpcClientFactory.create_client(DummyStub, "localhost:1234")

        # Ensure exception contains useful context
        self.assertIn("Failed to create gRPC channel", str(ctx.exception))
        self.assertIn("localhost:1234", str(ctx.exception))


class TestGrpcUtils(unittest.TestCase):
    def test_get_grpc_uri_and_max_message_length_valid_args(self):
        argv = [
            "--host", "localhost",
            "--port", "50051",
            "--functions-grpc-max-message-length", "4096"
        ]
        args = parse_grpc_args(argv)
        uri = get_grpc_uri(args)
        max_len = get_grpc_max_message_length(args)
        assert uri == "localhost:50051"
        assert max_len == 4096

    def test_get_grpc_uri_missing_host(self):
        argv = [
            "--port", "50051",
            "--functions-grpc-max-message-length", "4096"
        ]
        with self.assertRaises(ArgumentError) as excinfo:
            parse_grpc_args(argv)
        self.assertIn("host", str(excinfo.exception))

    def test_get_grpc_uri_missing_port(self):
        argv = [
            "--host", "localhost",
            "--functions-grpc-max-message-length", "4096"
        ]
        with self.assertRaises(ArgumentError) as excinfo:
            parse_grpc_args(argv)
        self.assertIn("port", str(excinfo.exception))

    def test_get_grpc_max_message_length_missing(self):
        argv = [
            "--host", "localhost",
            "--port", "50051",
        ]
        with self.assertRaises(ArgumentError) as excinfo:
            parse_grpc_args(argv)
        self.assertIn("functions-grpc-max-message-length", str(excinfo.exception))

    def test_get_grpc_uri_and_max_message_length_multiple_missing(self):
        argv = []
        with self.assertRaises(ArgumentError) as excinfo:
            parse_grpc_args(argv)
        msg = str(excinfo.exception)
        self.assertIn("host", msg)
        self.assertIn("port", msg)
        self.assertIn("functions-grpc-max-message-length", msg)
