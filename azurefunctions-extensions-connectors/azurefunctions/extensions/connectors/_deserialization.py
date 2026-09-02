#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Shared deserialization helpers for connector trigger payloads."""

from __future__ import annotations

import json
import types
from dataclasses import Field, fields, is_dataclass
from typing import Any, Callable, TypeVar, Union, get_args, get_origin, get_type_hints

from azurefunctions.extensions.base import Datum

ModelT = TypeVar("ModelT")


def _snake_to_camel(name: str) -> str:
    """Convert a generated Python field name to its likely JSON wire name."""
    normalized_name = name[:-1] if name.endswith("_") else name
    first_part, *remaining_parts = normalized_name.split("_")
    return first_part + "".join(part.capitalize() for part in remaining_parts)


def _read_field_value(
    data: dict[str, Any],
    model_field: Field[Any],
    aliases: dict[str, str],
) -> Any:
    """Read a field using binding aliases, generated metadata, and conventions."""
    candidate_names = (
        aliases.get(model_field.name),
        _snake_to_camel(model_field.name),
        model_field.metadata.get("wire_name"),
        model_field.name,
    )
    for candidate_name in candidate_names:
        if candidate_name is not None and candidate_name in data:
            return data[candidate_name]
    return None


def _deserialize_value(annotation: Any, value: Any) -> Any:
    """Deserialize a value according to a generated model annotation."""
    if value is None:
        return None

    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        non_none_types = [
            item_type for item_type in get_args(annotation)
            if item_type is not type(None)
        ]
        if len(non_none_types) == 1:
            return _deserialize_value(non_none_types[0], value)

    if origin is list:
        item_types = get_args(annotation)
        item_type = item_types[0] if item_types else Any
        if not isinstance(value, list):
            return value
        return [_deserialize_value(item_type, item) for item in value]

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            return value
        return deserialize_model(annotation, value)

    return value


def deserialize_model(
    model_type: type[ModelT],
    data: dict[str, Any],
    *,
    aliases: dict[str, str] | None = None,
    converters: dict[str, Callable[[Any], Any]] | None = None,
) -> ModelT:
    """Deserialize a dictionary into a generated connector dataclass."""
    field_aliases = aliases or {}
    field_converters = converters or {}
    type_hints = get_type_hints(model_type)
    values: dict[str, Any] = {}

    for model_field in fields(model_type):
        value = _read_field_value(data, model_field, field_aliases)
        converter = field_converters.get(model_field.name)
        if converter is not None:
            value = converter(value)
        else:
            value = _deserialize_value(
                type_hints.get(model_field.name, Any),
                value,
            )
        values[model_field.name] = value

    return model_type(**values)


def parse_payload(data: Datum) -> list[dict[str, Any]]:
    """Normalize a connector callback into a list of item dictionaries."""
    payload: Any = data.value
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON payload: {error}.") from error

    if not isinstance(payload, dict):
        raise ValueError("Connector payload must contain a JSON object.")

    body = payload.get("body", payload)
    if body is None:
        return []
    if not isinstance(body, dict):
        raise ValueError("Connector payload body must contain a JSON object.")

    if set(body) == {"value"} and (
        body["value"] is None or isinstance(body["value"], list)
    ):
        raw_items = body["value"] or []
    else:
        raw_items = [body]

    return [item for item in raw_items if isinstance(item, dict)]
