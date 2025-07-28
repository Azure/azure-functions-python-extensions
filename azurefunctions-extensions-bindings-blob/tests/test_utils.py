#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import os
import unittest

from unittest.mock import patch

from azurefunctions.extensions.bindings.blob.utils import (
    validate_connection_name,
    get_connection_string,
    using_system_managed_identity,
    using_user_managed_identity)


class TestUtils(unittest.TestCase):

    def test_valid_connection_string(self):
        # Test that a valid connection string is returned unchanged
        conn_setting = "MyStorageConnection"
        result = validate_connection_name(conn_setting)
        self.assertEqual(result, conn_setting)

    def test_none_connection_string_raises_value_error(self):
        # Test that passing None raises a ValueError
        with self.assertRaises(ValueError) as context:
            validate_connection_name(None)
        self.assertIn("Storage account connection name cannot be None",
                      str(context.exception))

    def test_connection_string_exists_directly(self):
        with patch.dict(os.environ, {"MY_CONNECTION": "direct_connection_string"}):
            result = get_connection_string("MY_CONNECTION")
            self.assertEqual(result, "direct_connection_string")

    def test_service_uri_exists(self):
        with patch.dict(os.environ, {"MY_CONNECTION__serviceUri":
                        "service_uri_string"}):
            result = get_connection_string("MY_CONNECTION")
            self.assertEqual(result, "service_uri_string")

    def test_blob_service_uri_exists(self):
        with patch.dict(os.environ, {"MY_CONNECTION__blobServiceUri":
                        "blob_service_uri_string"}):
            result = get_connection_string("MY_CONNECTION")
            self.assertEqual(result, "blob_service_uri_string")

    def test_connection_string_missing_raises_value_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                get_connection_string("MISSING_CONNECTION")
            self.assertIn("Storage account connection name "
                          "MISSING_CONNECTION does not exist",
                          str(context.exception))

    def test_service_uri_present(self):
        with patch.dict(os.environ, {"MY_CONNECTION__serviceUri":
                        "https://example.service.core.windows.net/"}):
            result = using_system_managed_identity("MY_CONNECTION")
            self.assertTrue(result)

    def test_blob_service_uri_present(self):
        with patch.dict(os.environ, {"MY_CONNECTION__blobServiceUri":
                        "https://example.blob.core.windows.net/"}):
            result = using_system_managed_identity("MY_CONNECTION")
            self.assertTrue(result)

    def test_both_uris_present(self):
        with patch.dict(os.environ, {
            "MY_CONNECTION__serviceUri": "https://example.service.core.windows.net/",
            "MY_CONNECTION__blobServiceUri": "https://example.blob.core.windows.net/"
        }):
            result = using_system_managed_identity("MY_CONNECTION")
            self.assertTrue(result)

    def test_no_uris_present(self):
        with patch.dict(os.environ, {}, clear=True):
            result = using_system_managed_identity("MY_CONNECTION")
            self.assertFalse(result)

    def test_both_credential_and_clientid_present(self):
        with patch.dict(os.environ, {
            "MY_CONNECTION__credential": "some-credential",
            "MY_CONNECTION__clientId": "some-client-id"
        }):
            result = using_user_managed_identity("MY_CONNECTION")
            self.assertTrue(result)

    def test_only_credential_present(self):
        with patch.dict(os.environ, {
            "MY_CONNECTION__credential": "some-credential"
        }):
            result = using_user_managed_identity("MY_CONNECTION")
            self.assertFalse(result)

    def test_only_clientid_present(self):
        with patch.dict(os.environ, {
            "MY_CONNECTION__clientId": "some-client-id"
        }):
            result = using_user_managed_identity("MY_CONNECTION")
            self.assertFalse(result)

    def test_neither_credential_nor_clientid_present(self):
        with patch.dict(os.environ, {}, clear=True):
            result = using_user_managed_identity("MY_CONNECTION")
            self.assertFalse(result)
