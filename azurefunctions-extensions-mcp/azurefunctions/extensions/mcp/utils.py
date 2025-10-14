#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
from typing import Any, Tuple, get_args, get_origin, Annotated


# Helper to extract actual type and description from Annotated types
def _extract_type_and_description(param_name: str, type_hint: Any) -> Tuple[Any, str]:
    if get_origin(type_hint) is Annotated:
        args = get_args(type_hint)
        actual_type = args[0]
        # Use first string annotation as description if present
        param_description = next((a for a in args[1:] if isinstance(a, str)), f"The {param_name} parameter.")
        return actual_type, param_description
    return type_hint, f"The {param_name} parameter."