#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from unittest.mock import patch, MagicMock

from azurefunctions.extensions.bindings.servicebus.grpcClient import GrpcClientFactory
from azurefunctions.extensions.bindings.servicebus.grpc_utils import (build_grpc_uri,
                                                                      ArgumentError)
import pytest


class TestGrpcClient(unittest.TestCase):
    def test_create_client_insecure_channel(self):
        # Dummy stub class to verify it receives a channel
        class DummyStub:
            def __init__(self, channel):
                self._channel = channel

        with patch("azurefunctions.extensions.bindings.servicebus.grpcClient.grpc.insecure_channel") as mock_insecure: # noqa
            fake_channel = MagicMock()
            mock_insecure.return_value = fake_channel

            client = GrpcClientFactory.create_client(
                service_stub=DummyStub,
                address="localhost:1234",
                grpc_max_message_length=1024,
                secure=False,
            )

            mock_insecure.assert_called_once()
            args, kwargs = mock_insecure.call_args
            assert args[0] == "localhost:1234"
            assert ("grpc.max_send_message_length", 1024) in kwargs["options"]
            assert ("grpc.max_receive_message_length", 1024) in kwargs["options"]

            assert isinstance(client, DummyStub)
            assert client._channel == fake_channel

    def test_create_client_secure_channel_with_root_certs(self):
        class DummyStub:
            def __init__(self, channel):
                self._channel = channel

        with (patch("azurefunctions.extensions.bindings.servicebus.grpcClient.grpc.secure_channel") as mock_secure,  # noqa
              patch("azurefunctions.extensions.bindings.servicebus.grpcClient.grpc.ssl_channel_credentials") as mock_creds):  # noqa
            fake_channel = MagicMock()
            fake_creds = MagicMock()
            mock_secure.return_value = fake_channel
            mock_creds.return_value = fake_creds

            client = GrpcClientFactory.create_client(
                service_stub=DummyStub,
                address="securehost:9999",
                grpc_max_message_length=2048,
                secure=True,
                root_certificates=b"fakecerts",
            )

            mock_creds.assert_called_once_with(root_certificates=b"fakecerts")
            mock_secure.assert_called_once()
            args, kwargs = mock_secure.call_args
            assert args[0] == "securehost:9999"
            assert args[1] == fake_creds
            assert ("grpc.max_send_message_length", 2048) in kwargs["options"]
            assert ("grpc.max_receive_message_length", 2048) in kwargs["options"]

            assert isinstance(client, DummyStub)
            assert client._channel == fake_channel


class TestGrpcUtils(unittest.TestCase):
    def test_build_grpc_uri_valid_args(self):
        argv = [
            "--host", "localhost",
            "--port", "50051",
            "--functions-grpc-max-message-length", "4096"
        ]
        uri, max_len = build_grpc_uri(argv)
        assert uri == "localhost:50051"
        assert max_len == 4096

    def test_build_grpc_uri_missing_host(self):
        argv = [
            "--port", "50051",
            "--functions-grpc-max-message-length", "4096"
        ]
        with pytest.raises(ArgumentError) as excinfo:
            build_grpc_uri(argv)
        assert "host" in str(excinfo.value)

    def test_build_grpc_uri_missing_port(self):
        argv = [
            "--host", "localhost",
            "--functions-grpc-max-message-length", "4096"
        ]
        with pytest.raises(ArgumentError) as excinfo:
            build_grpc_uri(argv)
        assert "port" in str(excinfo.value)

    def test_build_grpc_uri_missing_message_length(self):
        argv = [
            "--host", "localhost",
            "--port", "50051",
        ]
        with pytest.raises(ArgumentError) as excinfo:
            build_grpc_uri(argv)
        assert "functions-grpc-max-message-length" in str(excinfo.value)

    def test_build_grpc_uri_multiple_missing(self):
        argv = []
        with pytest.raises(ArgumentError) as excinfo:
            build_grpc_uri(argv)
        msg = str(excinfo.value)
        assert ("host" in msg and "port" in msg
                and "functions-grpc-max-message-length" in msg)
