#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.office365 import (
    GraphCalendarEventClientReceive
)


class TestGraphCalendarEventClientReceive(unittest.TestCase):
    """Tests for the GraphCalendarEventClientReceive SDK type wrapper."""

    def test_supports_deferred_binding_false(self):
        """Test that GraphCalendarEventClientReceive does not support
        deferred binding"""
        self.assertFalse(
            GraphCalendarEventClientReceive.supports_deferred_binding()
        )

    def test_get_sdk_type_raises_on_none_data(self):
        """Test that get_sdk_type raises ValueError when data is None"""
        event = GraphCalendarEventClientReceive(data=None)
        with self.assertRaises(ValueError) as context:
            event.get_sdk_type()
        self.assertIn("No data provided", str(context.exception))

    def test_init_stores_json_payload(self):
        """Test that __init__ stores the data as _json_payload"""
        test_data = Datum(value='{"test": "data"}', type='json')
        event = GraphCalendarEventClientReceive(data=test_data)
        self.assertEqual(event._json_payload, test_data)

    def test_get_sdk_type_deserializes_calendar_events(self):
        """Test calendar event fields are mapped by the extension."""
        data = Datum(
            value={
                "body": {
                    "value": [
                        {
                            "id": "event-1",
                            "subject": "Planning",
                            "startWithTimeZone": "2026-09-02T10:00:00Z",
                            "isAllDay": False,
                        }
                    ]
                }
            },
            type="json",
        )

        events = GraphCalendarEventClientReceive(data=data).get_sdk_type()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].subject, "Planning")
        self.assertEqual(
            events[0].start_with_time_zone,
            "2026-09-02T10:00:00Z",
        )
        self.assertFalse(events[0].is_all_day)


if __name__ == "__main__":
    unittest.main()
