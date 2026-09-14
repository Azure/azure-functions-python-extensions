#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.office365 import (
    ClientReceiveMessage
)


class TestClientReceiveMessage(unittest.TestCase):
    """Tests for the ClientReceiveMessage SDK type wrapper."""

    def test_supports_deferred_binding_false(self):
        """Test that ClientReceiveMessage does not support deferred binding"""
        self.assertFalse(ClientReceiveMessage.supports_deferred_binding())

    def test_get_sdk_type_raises_on_none_data(self):
        """Test that get_sdk_type raises ValueError when data is None"""
        msg = ClientReceiveMessage(data=None)
        with self.assertRaises(ValueError) as context:
            msg.get_sdk_type()
        self.assertIn("No data provided", str(context.exception))

    def test_init_stores_json_payload(self):
        """Test that __init__ stores the data as _json_payload"""
        test_data = Datum(value='{"test": "data"}', type='json')
        msg = ClientReceiveMessage(data=test_data)
        self.assertEqual(msg._json_payload, test_data)

    def test_get_sdk_type_deserializes_batch_and_nested_attachment(self):
        """Test extension-owned email and attachment deserialization."""
        data = Datum(
            value=(
                '{"body":{"value":[{"id":"message-1",'
                '"toRecipients":"recipient@example.com",'
                '"importance":"high","hasAttachments":true,'
                '"attachments":[{"id":"attachment-1",'
                '"contentType":"text/plain"}]}]}}'
            ),
            type="json",
        )

        messages = ClientReceiveMessage(data=data).get_sdk_type()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, "message-1")
        self.assertEqual(messages[0].to, "recipient@example.com")
        self.assertEqual(messages[0].importance, 2)
        self.assertTrue(messages[0].has_attachment)
        self.assertEqual(messages[0].attachments[0].id, "attachment-1")
        self.assertEqual(
            messages[0].attachments[0].content_type,
            "text/plain",
        )

    def test_get_sdk_type_deserializes_single_item(self):
        """Test single-item callbacks are normalized to a list."""
        data = Datum(
            value={"body": {"id": "message-1", "subject": "Hello"}},
            type="json",
        )

        messages = ClientReceiveMessage(data=data).get_sdk_type()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].subject, "Hello")


if __name__ == "__main__":
    unittest.main()
