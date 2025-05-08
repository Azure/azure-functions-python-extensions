#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import os

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient


def get_connection_string(connection_string: str) -> str:
    """
    Validates and returns the connection string. If the connection string is
    not an App Setting, an error will be thrown.

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
    if connection_string is None:
        raise ValueError(
            "Storage account connection string cannot be None. "
            "Please provide a connection string."
        )
    elif connection_string in os.environ:
        return os.getenv(connection_string)
    elif connection_string + "__serviceUri" in os.environ:
        return os.getenv(connection_string + "__serviceUri")
    elif connection_string + "__blobServiceUri" in os.environ:
        return os.getenv(connection_string + "__blobServiceUri")
    else:
        raise ValueError(
            f"Storage account connection string {connection_string} does not exist. "
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
    __serviceUri and __credential, AND either __managedIdentityResourceId
    or __clientID.

    We are not verifying that the customer only has __managedIdentityResourceId
    or __clientID. That check is handled by the (???).
    """
    return ((os.getenv(connection_name + "__serviceUri") is not None)
            and (os.getenv(connection_name + "__credential") is not None)
            and ((os.getenv(connection_name + "__managedIdentityResourceId")
                  is not None)
                 or (os.getenv(connection_name + "__clientID") is not None
                     )))


def get_blob_service_client(system_managed_identity: bool,
                            user_managed_identity: bool,
                            connection: str):
    connection_string = get_connection_string(connection)
    if user_managed_identity:
        return BlobServiceClient(account_url=connection_string,
                                 credential=ManagedIdentityCredential(
                                     client_id=os.getenv(connection + "__clientID")))
    elif system_managed_identity:
        return BlobServiceClient(account_url=connection_string,
                                 credential=DefaultAzureCredential())
    else:
        return BlobServiceClient.from_connection_string(connection_string)
