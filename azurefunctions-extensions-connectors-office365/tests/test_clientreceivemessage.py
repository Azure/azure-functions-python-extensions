#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from typing import List

from azurefunctions.extensions.connectors.office365 import (
    ClientReceiveMessage,
    ClientReceiveMessageConverter
)


class TestClientReceiveMessageConverter(unittest.TestCase):
    def test_input_type_single(self):
        """Test that ClientReceiveMessage type annotation is accepted"""
        check_input_type = ClientReceiveMessageConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ClientReceiveMessage))

    def test_input_type_list(self):
        """Test that List[ClientReceiveMessage] type annotation is accepted"""
        check_input_type = ClientReceiveMessageConverter.check_input_type_annotation
        self.assertTrue(check_input_type(List[ClientReceiveMessage]))

    def test_input_type_invalid(self):
        """Test that invalid type annotations are rejected"""
        check_input_type = ClientReceiveMessageConverter.check_input_type_annotation
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(dict))
        self.assertFalse(check_input_type(List[str]))

    def test_input_none(self):
        """Test that None data returns None"""
        result = ClientReceiveMessageConverter.decode(
            data=None, trigger_metadata=None, pytype=ClientReceiveMessage
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
