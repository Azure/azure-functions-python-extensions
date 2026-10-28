#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Index and execute the Azure DevOps sample with synthetic callback records."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import azure.connectors.visualstudioteamservices as models
import azurefunctions.extensions.connectors.visualstudioteamservices as devops
from azurefunctions.extensions.base import Datum


class TestDevOpsSample(unittest.TestCase):
    """Keep the sample annotations, return contracts, and count-only logs usable."""

    @classmethod
    def setUpClass(cls):
        """Load only this sample and keep its indexed Functions handlers."""
        cls.sample_root = Path(__file__).resolve().parents[1] / "samples" / (
            "visualstudioteamservices_samples_polling"
        )
        specification = importlib.util.spec_from_file_location(
            "devops_polling_sample", cls.sample_root / "function_app.py",
        )
        cls.sample = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.sample)
        cls.functions = cls.sample.app.get_functions()

    def handler_contracts(self):
        """Map every sample to its binding, argument, and expected count log."""
        return {
            "devops_build_completed_single": (
                devops.BuildResult, "builds",
                "Received %d completed Azure DevOps builds.",
            ),
            "devops_build_completed_batch": (
                devops.BuildResult, "builds",
                "Received a batch of %d completed Azure DevOps builds.",
            ),
            "devops_git_push": (
                devops.GitPush, "pushes", "Received %d Azure DevOps Git pushes.",
            ),
            "devops_pull_request_created": (
                devops.GitPullRequest, "pull_requests",
                "Received %d created Azure DevOps pull requests.",
            ),
            "devops_pull_request_closed": (
                devops.GitPullRequest, "pull_requests",
                "Received %d closed Azure DevOps pull requests.",
            ),
            "devops_tfvc_check_in": (
                devops.TfvcChangeset, "changesets",
                "Received %d Azure DevOps TFVC changesets.",
            ),
            **{
                "devops_work_item_" + action: (
                    devops.TriggerWorkItemResponse, "work_items",
                    f"Received %d {action} Azure DevOps work items.",
                )
                for action in ("assigned", "closed", "created", "updated")
            },
        }

    def test_all_handlers_index_with_matching_binding_annotations(self):
        """Index ten examples covering nine operations and both build batch modes."""
        contracts = self.handler_contracts()
        self.assertEqual({function.get_function_name() for function in self.functions},
                         set(contracts))
        for function in self.functions:
            name = function.get_function_name()
            binding, argument, _ = contracts[name]
            with self.subTest(name=name):
                definition = json.loads(function.get_function_json())
                self.assertEqual(len(definition["bindings"]), 1)
                trigger = definition["bindings"][0]
                self.assertEqual(trigger["direction"].lower(), "in")
                self.assertEqual(trigger["type"], "connectorTrigger")
                self.assertEqual(trigger["name"], argument)
                annotation = function.get_user_function().__annotations__[argument]
                self.assertTrue(devops.ConnectorConverter
                                .check_input_type_annotation(annotation))
                self.assertEqual(annotation.__args__, (binding,))

    def test_handlers_log_counts_for_empty_and_populated_callbacks(self):
        """Run actual converted models, not raw dictionaries or wrapper instances."""
        contracts = self.handler_contracts()
        for function in self.functions:
            name = function.get_function_name()
            binding, _, message = contracts[name]
            for records in ([], [{
                "id": 0, "pushId": 0, "pullRequestId": 0, "changesetId": 0,
                "fields": {"Custom.Null": None, "Custom.Flag": False},
            }]):
                with self.subTest(name=name, records=records):
                    items = binding(data=Datum(value={"body": {"value": records}},
                                               type="json")).get_sdk_type()
                    self.assertTrue(all(type(item) is getattr(models, binding.__name__)
                                        for item in items))
                    with patch.object(self.sample.logging, "info") as log:
                        with patch.object(self.sample.logging, "error") as error_log:
                            self.assertIsNone(function.get_user_function()(items))
                        error_log.assert_not_called()
                    self.assertEqual(log.call_args_list[0].args,
                                     (message, len(records)))
                    if name == "devops_work_item_assigned":
                        self.assertEqual(
                            [call.args for call in log.call_args_list[1:]],
                            [("Azure DevOps work-item field count: %d.", 2)]
                            * len(records),
                        )
                    else:
                        self.assertEqual(log.call_count, 1)

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
