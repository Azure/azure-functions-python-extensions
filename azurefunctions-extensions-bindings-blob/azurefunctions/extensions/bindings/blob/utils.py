#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import os

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient


def validate_connection_name(connection_name: str) -> str:
    """
    Validates and returns the connection name. The setting must
    not be None - if it is, a ValueError will be raised.
    """
    if connection_name is None:
        raise ValueError(
            "Storage account connection name cannot be None. "
            "Please provide a connection setting."
        )
    else:
        return connection_name


def get_connection_string(connection_name: str) -> str:
    """
    Returns the connection string.

    When using managed identity, the connection string variable name is formatted
    like so:
    Input: <CONNECTION_NAME_PREFIX>__serviceUri
    Trigger: <CONNECTION_NAME_PREFIX>__blobServiceUri
    The variable received will be <CONNECTION_NAME_PREFIX>. Therefore, we need to append
    the suffix to obtain the storage URI and create the client.

    There are four cases:
    1. Not using managed identity: the environment variable exists as is
    2. Using managed identity for blob input: __serviceUri must be appended
    3. Using managed identity for blob trigger: __blobServiceUri must be appended
    4. None of these cases existed, so the connection variable is invalid.
    """
    if connection_name in os.environ:
        return os.getenv(connection_name)
    elif connection_name + "__serviceUri" in os.environ:
        return os.getenv(connection_name + "__serviceUri")
    elif connection_name + "__blobServiceUri" in os.environ:
        return os.getenv(connection_name + "__blobServiceUri")
    else:
        raise ValueError(
            f"Storage account connection name {connection_name} does not exist. "
            f"Please make sure that it is a defined App Setting."
        )


def using_system_managed_identity(connection_name: str) -> bool:
    """
    To determine if system-assigned managed identity is being used, we check if
    the provided connection string has either of the two suffixes:
    __serviceUri or __blobServiceUri.
    """
    return (os.getenv(connection_name + "__serviceUri") is not None) or (
        os.getenv(connection_name + "__blobServiceUri") is not None
    )


def using_user_managed_identity(connection_name: str) -> bool:
    """
    To determine if user-assigned managed identity is being used, we check if
    the provided connection string has the following suffixes:
    __credential AND __clientId
    """
    return (os.getenv(connection_name + "__credential") is not None) and (
        os.getenv(connection_name + "__clientId") is not None
    )


def service_client_factory(connection: str):
    """
    Returns the BlobServiceClient.

    How the BlobServiceClient is created depends on the authentication
    strategy of the customer.

    There are 3 cases:
    1. The customer is using user-assigned managed identity -> the BlobServiceClient
    must be created using a ManagedIdentityCredential.
    2. The customer is using system based managed identity -> the BlobServiceClient
    must be created using a DefaultAzureCredential.
    3. The customer is not using managed identity -> the BlobServiceClient must
    be created using a connection string.
    """
    connection_string = get_connection_string(connection)
    if using_user_managed_identity(connection):
        return BlobServiceClient(account_url=connection_string,
                                 credential=ManagedIdentityCredential(
                                     client_id=os.getenv(connection + "__clientId")))
    elif using_system_managed_identity(connection):
        return BlobServiceClient(account_url=connection_string,
                                 credential=DefaultAzureCredential())
    else:
        return BlobServiceClient.from_connection_string(connection_string)
