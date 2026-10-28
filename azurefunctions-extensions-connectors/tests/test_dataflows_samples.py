#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Index and execute the Dataflows sample with synthetic refresh callbacks."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import azure.connectors.dataflows as models
import azurefunctions.extensions.connectors.dataflows as dataflows
from azurefunctions.extensions.base import Datum


class TestDataflowsSample(unittest.TestCase):
    """Exercise the actual sample handler with generated refresh objects."""

    @classmethod
    def setUpClass(cls):
        """Load only the Dataflows sample and index its Functions handler."""
        cls.sample_root = Path(__file__).resolve().parents[1] / "samples" / (
            "dataflows_samples_refresh_completed"
        )
        specification = importlib.util.spec_from_file_location(
            "dataflows_refresh_sample", cls.sample_root / "function_app.py",
        )
        cls.sample = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.sample)
        cls.functions = cls.sample.app.get_functions()

    def test_handler_indexes_with_refresh_model_annotation(self):
        """The function receives SDK items, not the action's DataflowModel."""
        self.assertEqual(len(self.functions), 1)
        function = self.functions[0]
        self.assertEqual(function.get_function_name(), "dataflows_refresh_completed")
        definition = json.loads(function.get_function_json())
        self.assertEqual(len(definition["bindings"]), 1)
        binding = definition["bindings"][0]
        self.assertEqual(binding["type"], "connectorTrigger")
        self.assertEqual(binding["name"], "refreshes")
        self.assertEqual(binding["direction"].lower(), "in")
        annotation = function.get_user_function().__annotations__["refreshes"]
        self.assertTrue(dataflows.ConnectorConverter
                        .check_input_type_annotation(annotation))
        self.assertEqual(annotation.__args__, (dataflows.RefreshModel,))

    def test_handler_logs_counts_for_empty_success_failed_and_cancelled(self):
        """A failed refresh reaches the handler as data, not a conversion error."""
        self.assertEqual(len(self.functions), 1)
        for payload, expected_count, expected_failed in (
            ({"body": []}, 0, 0),
            ({"body": {"dataflowId": "synthetic-id", "status": "Success"}}, 1, 0),
            ({"body": {"dataflowId": "synthetic-id", "status": "Failed"}}, 1, 1),
            ({"body": {"dataflowId": "synthetic-id", "status": "Cancelled"}}, 1, 0),
        ):
            with self.subTest(payload=payload):
                items = dataflows.ConnectorConverter.decode(
                    data=Datum(value=payload, type="json"), trigger_metadata=None,
                    pytype=list[dataflows.RefreshModel],
                )
                self.assertEqual(len(items), expected_count)
                self.assertTrue(all(type(item) is models.RefreshModel
                                    for item in items))
                with patch.object(self.sample.logging, "info") as log:
                    with patch.object(self.sample.logging, "error") as error_log:
                        self.assertIsNone(self.functions[0].get_user_function()(items))
                    error_log.assert_not_called()
                self.assertEqual([call.args for call in log.call_args_list], [
                    ("Received %d Dataflows refresh completions.", expected_count),
                    ("Failed Dataflows refresh count: %d.", expected_failed),
                ])
                self.assertNotIn("synthetic-id", str(log.call_args_list))

    def test_configuration_uses_sdk_package_and_local_runtime_settings(self):
        """Use the SDK package with the experimental bundle and local storage."""
        requirements = (self.sample_root / "requirements.txt").read_text()
        self.assertIn("azure-connectors", requirements.splitlines())
        host = json.loads((self.sample_root / "host.json").read_text())
        self.assertEqual(host["extensionBundle"]["id"],
                         "Microsoft.Azure.Functions.ExtensionBundle.Experimental")
        settings = json.loads((self.sample_root / "local.settings.json").read_text())
        self.assertEqual(settings["Values"]["AzureWebJobsStorage"],
                         "UseDevelopmentStorage=true")
