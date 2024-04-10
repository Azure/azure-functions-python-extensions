# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import unittest

from azurefunctions.extensions.base import sdkType


class TestSdkType(unittest.TestCase):

    def test_init(self):
        data_populated = sdkType.SdkType(data={"key": "value"})
        self.assertEqual(data_populated._data, {"key": "value"})

        data_empty = sdkType.SdkType()
        self.assertEqual(data_empty._data, {})

    def test_get_sdk_type(self):
        class MockSdkType(sdkType.SdkType):
            _sample = ""

        mock_type = MockSdkType()
        self.assertIsNone(mock_type.get_sdk_type())
