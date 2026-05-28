#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.office365 import (
    GraphClientReceiveMessage
)


class TestGraphClientReceiveMessage(unittest.TestCase):
    """Tests for the GraphClientReceiveMessage SDK type wrapper."""

    def test_supports_deferred_binding_false(self):
        """Test that GraphClientReceiveMessage does not support deferred binding"""
        self.assertFalse(GraphClientReceiveMessage.supports_deferred_binding())

    def test_get_sdk_type_raises_on_none_data(self):
        """Test that get_sdk_type raises ValueError when data is None"""
        msg = GraphClientReceiveMessage(data=None)
        with self.assertRaises(ValueError) as context:
            msg.get_sdk_type()
        self.assertIn("No data provided", str(context.exception))

    def test_init_stores_json_payload(self):
        """Test that __init__ stores the data as _json_payload"""
        test_data = Datum(value='{"test": "data"}', type='json')
        msg = GraphClientReceiveMessage(data=test_data)
        self.assertEqual(msg._json_payload, test_data)


if __name__ == "__main__":
    unittest.main()
