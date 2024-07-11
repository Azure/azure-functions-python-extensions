#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import os
from pydantic import BaseModel, Field, field_validator


class ConnectionConfig(BaseModel):
    connection_string: str = Field(
        ..., description="Storage account connection string name"
    )

    @field_validator("connection_string")
    @classmethod
    def validate_connection_string(cls, cx_connection_string: str) -> str:
        """
        Validates the connection string. If the connection string is
        not an App Setting, an error will be thrown.
        """
        if cx_connection_string is "":
            raise ValueError(
                "Storage account connection string cannot be empty. "
                "Please provide a connection string."
            )
        elif str.isspace(cx_connection_string):
            raise ValueError(
                "Storage account connection string cannot contain only whitespace. "
                "Please provide a valid connection string."
            )
        elif not os.getenv(cx_connection_string):
            raise ValueError(
                "Storage account connection string %s does not exist. "
                "Please make sure that it is a defined App Setting.",
                cx_connection_string,
            )
        return os.getenv(cx_connection_string)
