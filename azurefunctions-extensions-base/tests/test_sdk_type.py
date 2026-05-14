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

    def test_supports_deferred_binding_default_true(self):
        """Test that SdkType.supports_deferred_binding returns True by default."""
        self.assertTrue(sdkType.SdkType.supports_deferred_binding())

    def test_supports_deferred_binding_inherited(self):
        """Test that subclasses inherit the default True value."""
        class MockSdkType(sdkType.SdkType):
            def get_sdk_type(self):
                return None

        self.assertTrue(MockSdkType.supports_deferred_binding())
        # Also test on instance
        instance = MockSdkType()
        self.assertTrue(instance.supports_deferred_binding())

    def test_supports_deferred_binding_override_false(self):
        """Test that subclasses can override to return False."""
        class MockSdkTypeNoDeferred(sdkType.SdkType):
            @classmethod
            def supports_deferred_binding(cls) -> bool:
                return False

            def get_sdk_type(self):
                return None

        self.assertFalse(MockSdkTypeNoDeferred.supports_deferred_binding())
        # Also test on instance
        instance = MockSdkTypeNoDeferred()
        self.assertFalse(instance.supports_deferred_binding())
