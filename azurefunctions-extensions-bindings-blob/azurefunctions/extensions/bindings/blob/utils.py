#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import os


def validate_connection_string(connection_string: str) -> str:
    """
    Validates the connection string. If the connection string is
    not an App Setting, an error will be thrown.
    """
    if connection_string == None:
        raise ValueError(
            "Storage account connection string cannot be none. "
            "Please provide a connection string."
        )
    elif connection_string == "":
        raise ValueError(
            "Storage account connection string cannot be empty. "
            "Please provide a connection string."
        )
    elif str.isspace(connection_string):
        raise ValueError(
            "Storage account connection string cannot contain only whitespace. "
            "Please provide a valid connection string."
        )
    elif not os.getenv(connection_string):
        raise ValueError(
            f"Storage account connection string {connection_string} does not exist. "
            f"Please make sure that it is a defined App Setting."
        )
    return os.getenv(connection_string)
