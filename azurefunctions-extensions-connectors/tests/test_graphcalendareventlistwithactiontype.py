#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.office365 import (
    GraphCalendarEventListWithActionType
)


class TestGraphCalendarEventListWithActionType(unittest.TestCase):
    """Tests for the GraphCalendarEventListWithActionType SDK type wrapper."""

    def test_supports_deferred_binding_false(self):
        """Test that GraphCalendarEventListWithActionType does not support
        deferred binding"""
        self.assertFalse(
            GraphCalendarEventListWithActionType.supports_deferred_binding()
        )

    def test_get_sdk_type_raises_on_none_data(self):
        """Test that get_sdk_type raises ValueError when data is None"""
        event = GraphCalendarEventListWithActionType(data=None)
        with self.assertRaises(ValueError) as context:
            event.get_sdk_type()
        self.assertIn("No data provided", str(context.exception))

    def test_init_stores_json_payload(self):
        """Test that __init__ stores the data as _json_payload"""
        test_data = Datum(value='{"test": "data"}', type='json')
        event = GraphCalendarEventListWithActionType(data=test_data)
        self.assertEqual(event._json_payload, test_data)

    def test_get_sdk_type_deserializes_action_type_wrapper(self):
        """Test changed events are returned in the generated wrapper."""
        data = Datum(
            value={
                "body": {
                    "id": "event-1",
                    "actionType": "updated",
                    "isUpdated": True,
                    "subject": "Updated planning",
                }
            },
            type="json",
        )

        event_list = GraphCalendarEventListWithActionType(
            data=data
        ).get_sdk_type()

        self.assertEqual(len(event_list.value), 1)
        self.assertEqual(event_list.value[0].id, "event-1")
        self.assertEqual(event_list.value[0].action_type, "updated")
        self.assertTrue(event_list.value[0].is_updated)


if __name__ == "__main__":
    unittest.main()
