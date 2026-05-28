#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from typing import List

from azurefunctions.extensions.connectors.office365 import (
    ClientReceiveMessage,
    GraphClientReceiveMessage,
    GraphCalendarEventListWithActionType,
    GraphCalendarEventClientReceive,
    ConnectorConverter
)


class TestConnectorConverter(unittest.TestCase):
    """Tests for the ConnectorConverter class."""

    def test_input_type_single(self):
        """Test that ClientReceiveMessage type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ClientReceiveMessage))

    def test_input_type_list(self):
        """Test that List[ClientReceiveMessage] type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(List[ClientReceiveMessage]))

    def test_input_type_invalid(self):
        """Test that invalid type annotations are rejected"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(dict))
        self.assertFalse(check_input_type(List[str]))

    def test_input_type_none(self):
        """Test that None type annotation is rejected"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertFalse(check_input_type(None))

    def test_input_none(self):
        """Test that None data returns None"""
        result = ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=ClientReceiveMessage
        )
        self.assertIsNone(result)

    def test_graph_input_type_single(self):
        """Test that GraphClientReceiveMessage type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphClientReceiveMessage))

    def test_graph_input_type_list(self):
        """Test that List[GraphClientReceiveMessage] type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(List[GraphClientReceiveMessage]))

    def test_graph_input_none(self):
        """Test that None data returns None for GraphClientReceiveMessage"""
        result = ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=GraphClientReceiveMessage
        )
        self.assertIsNone(result)

    def test_calendar_event_input_type_single(self):
        """Test that GraphCalendarEventListWithActionType annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphCalendarEventListWithActionType))

    def test_calendar_event_input_type_list(self):
        """Test that List[GraphCalendarEventListWithActionType] is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(
            check_input_type(List[GraphCalendarEventListWithActionType])
        )

    def test_calendar_event_input_none(self):
        """Test that None data returns None for GraphCalendarEventListWithActionType"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=GraphCalendarEventListWithActionType
        )
        self.assertIsNone(result)

    def test_calendar_event_client_receive_input_type_single(self):
        """Test that GraphCalendarEventClientReceive annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphCalendarEventClientReceive))

    def test_calendar_event_client_receive_input_type_list(self):
        """Test that List[GraphCalendarEventClientReceive] is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(
            check_input_type(List[GraphCalendarEventClientReceive])
        )

    def test_calendar_event_client_receive_input_none(self):
        """Test that None data returns None for GraphCalendarEventClientReceive"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=GraphCalendarEventClientReceive
        )
        self.assertIsNone(result)

    def test_decode_with_list_type_annotation(self):
        """Test that decode works with List[Type] annotations"""
        # Test List[ClientReceiveMessage]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[ClientReceiveMessage]
        )
        self.assertIsNone(result)

        # Test List[GraphClientReceiveMessage]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphClientReceiveMessage]
        )
        self.assertIsNone(result)

        # Test List[GraphCalendarEventListWithActionType]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphCalendarEventListWithActionType]
        )
        self.assertIsNone(result)

        # Test List[GraphCalendarEventClientReceive]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphCalendarEventClientReceive]
        )
        self.assertIsNone(result)

    def test_decode_unsupported_type_returns_none(self):
        """Test that decode returns None for unsupported types"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=str
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
