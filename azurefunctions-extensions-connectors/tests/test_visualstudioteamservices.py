#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic Azure DevOps polling callbacks against the generated SDK models."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from dataclasses import fields
from types import SimpleNamespace
from typing import List

from azurefunctions.extensions.base import Datum

SDK_AVAILABLE = importlib.util.find_spec(
    "azure.connectors.visualstudioteamservices"
) is not None
if SDK_AVAILABLE:
    import azure.connectors.visualstudioteamservices as models
    import azurefunctions.extensions.connectors.visualstudioteamservices as devops


class TestDevOpsSdkAvailability(unittest.TestCase):
    """Keep old connectors usable when the optional new SDK module is absent."""

    def test_missing_devops_sdk_has_actionable_error(self):
        """Fail only the new namespace import, with its SDK prerequisite named."""
        result = subprocess.run(
            [sys.executable, "-c", """
import sys
sys.modules['azure.connectors.visualstudioteamservices'] = None
import azurefunctions.extensions.connectors.salesforce
try:
    import azurefunctions.extensions.connectors.visualstudioteamservices
except ImportError as error:
    assert 'Azure DevOps bindings require' in str(error), str(error)
    assert 'azure.connectors.visualstudioteamservices' in str(error), str(error)
    assert 'SDK main' in str(error), str(error)
else:
    raise AssertionError('Expected a missing SDK module error.')
import azurefunctions.extensions.connectors.planner
"""],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(
    SDK_AVAILABLE,
    "Azure DevOps requires SDK main with visualstudioteamservices (see samples).",
)
class TestDevOpsBindings(unittest.TestCase):
    """Verify item identity, nested types, custom fields, and source batches."""

    def binding_types(self):
        """Return the five binding names shared by the nine polling triggers."""
        return (devops.BuildResult, devops.GitPush, devops.GitPullRequest,
                devops.TfvcChangeset, devops.TriggerWorkItemResponse)

    def decode(self, binding, payload):
        """Send a decoded callback through the Functions converter."""
        return devops.ConnectorConverter.decode(
            data=Datum(value=payload, type="json"), trigger_metadata=None,
            pytype=List[binding],
        )

    def test_exports_annotations_and_exact_sdk_item_types(self):
        """Accept direct and list annotations without returning response envelopes."""
        for binding in self.binding_types():
            model = getattr(models, binding.__name__)
            self.assertIn(binding.__name__, devops.__all__)
            self.assertTrue(issubclass(binding, model))
            self.assertFalse(binding.supports_deferred_binding())
            for annotation in (binding, List[binding], list[binding]):
                with self.subTest(binding=binding, annotation=annotation):
                    self.assertTrue(devops.ConnectorConverter
                                    .check_input_type_annotation(annotation))
                    result = devops.ConnectorConverter.decode(
                        data=Datum(value={}, type="json"), trigger_metadata=None,
                        pytype=annotation,
                    )
                    self.assertEqual(len(result), 1)
                    self.assertIs(type(result[0]), model)
            self.assertFalse(devops.ConnectorConverter
                             .check_input_type_annotation(model))

    def test_nine_polling_operations_match_generated_registry(self):
        """Use current item contracts, not webhook or action-response classes."""
        operations = {
            "OnBuildCompleted": (devops.BuildResult, "VstsListBuildResult"),
            "OnGitPush": (devops.GitPush, "VstsListGitPush"),
            "OnGitPullCreated": (devops.GitPullRequest, "VstsListGitPullRequest"),
            "OnGitPullClosed": (devops.GitPullRequest, "VstsListGitPullRequest"),
            "OnTfvcCheckIn": (devops.TfvcChangeset, "VstsListTfvcChangeset"),
            **{operation: (devops.TriggerWorkItemResponse,
                           "VstsListTriggerWorkItemResponse") for operation in (
                "OnWorkItemAssignedV2", "OnWorkItemClosedV2",
                "OnWorkItemCreatedV2", "OnWorkItemUpdatedV2",
            )},
        }
        self.assertEqual(set(models.TRIGGER_OPERATIONS), set(operations))
        for operation, (binding, envelope) in operations.items():
            with self.subTest(operation=operation):
                entry = models.TRIGGER_OPERATIONS[operation]
                self.assertEqual(entry["method"], "get")
                self.assertEqual(entry["callback_payload_type"], envelope)
                required = ["account", "project"]
                if operation.startswith("OnGit"):
                    required += ["repository"]
                elif operation == "OnWorkItemAssignedV2":
                    required += ["team", "wiql__System_AssignedTo"]
                self.assertEqual(entry["required_parameters"], required)
                result = self.decode(binding, {"value": [{}]})
                self.assertIs(type(result[0]), getattr(models, binding.__name__))
                self.assertNotIsInstance(result[0], getattr(models, envelope))

    def test_build_fields_links_and_nested_sdk_models(self):
        """Map _links and convert generated user, definition, and web-link models."""
        record = {
            "id": 0, "buildNumber": "", "sourceBranch": "refs/heads/main",
            "sourceVersion": "commit", "status": "completed", "priority": "normal",
            "queueTime": "2026-10-28T01:00:00Z", "startTime": None,
            "finishTime": "2026-10-28T01:01:00Z", "reason": "manual",
            "result": "succeeded", "requestedFor": {"uniqueName": "synthetic"},
            "parameters": '{"flag":false}', "definition": {"id": 0, "name": ""},
            "_links": {"web": {"href": "https://example.test/build"}},
            "links": {"web": {"href": "wrong-fallback"}},
            "tags": [], "templateParameters": {"flag": "false"},
        }
        build = self.decode(devops.BuildResult, record)[0]
        self.assertEqual(build.id, 0)
        for name in ("build_number", "source_branch", "source_version", "status",
                     "priority", "queue_time", "start_time", "finish_time",
                     "reason", "result", "parameters", "tags", "template_parameters"):
            field = next(field for field in fields(models.BuildResult)
                         if field.name == name)
            self.assertEqual(getattr(build, name), record[field.metadata.get(
                "wire_name", name,
            )])
        self.assertIs(type(build.requested_for), models.BuildRequestUser)
        self.assertEqual(build.requested_for.unique_name, "synthetic")
        self.assertIs(type(build.definition), models.BuildResultDefinition)
        self.assertEqual((build.definition.id, build.definition.name), (0, ""))
        self.assertIs(type(build.links), models.Links)
        self.assertIs(type(build.links.web), models.WebLinks)
        self.assertEqual(build.links.web.href, "https://example.test/build")

    def test_git_push_nested_models_and_zero_identifier(self):
        """Build typed repository, identity, and ref-update SDK objects."""
        record = {
            "repository": {"id": "repository", "name": "", "url": "api",
                           "remoteUrl": "remote"},
            "pushedBy": {"id": "user", "displayName": "", "uniqueName": "name",
                         "imageUrl": None},
            "refUpdates": [{"name": "refs/heads/main", "repositoryId": "repo",
                            "oldObjectId": "old", "newObjectId": "new"}],
            "pushId": 0, "date": "2026-10-28T01:00:00Z",
        }
        push = self.decode(devops.GitPush, record)[0]
        self.assertIs(type(push.repository), models.GitRepository)
        self.assertEqual(push.repository.remote_url, "remote")
        self.assertEqual(push.repository.name, "")
        self.assertIs(type(push.pushed_by), models.GitPushUser)
        self.assertEqual(push.pushed_by.unique_name, "name")
        self.assertIsNone(push.pushed_by.image_url)
        self.assertIs(type(push.ref_updates[0]), models.GitRefUpdate)
        self.assertEqual(push.ref_updates[0].repository_id, "repo")
        self.assertEqual(push.ref_updates[0].old_object_id, "old")
        self.assertEqual(push.ref_updates[0].new_object_id, "new")
        self.assertEqual((push.push_id, push.date), (0, record["date"]))

    def test_pull_request_recursive_reviewers_commits_and_options(self):
        """Preserve false options, zero votes, and nested reviewer collections."""
        record = {
            "repository": {"id": "repo"}, "pullRequestId": 0,
            "createdBy": {"id": "creator"}, "closedBy": {"id": "closer"},
            "autoCompleteSetBy": {"id": "auto"}, "creationDate": "created",
            "closedDate": None, "title": "", "description": None,
            "sourceRefName": "refs/heads/feature", "targetRefName": "refs/heads/main",
            "isDraft": False, "reviewers": [{
                "id": "reviewer", "vote": 0, "hasDeclined": False,
                "isFlagged": False, "isRequired": False,
                "votedFor": [{"id": "team", "votedFor": []}],
            }],
            "commits": [{"commitId": "commit", "comment": ""}],
            "completionOptions": {"deleteSourceBranch": False},
            "mergeOptions": {"noFastForward": "false", "rebase": "false",
                             "rebaseMerge": "false", "squash": "false"},
            "mergeFailureMessage": "", "reviewerList": "", "requiredReviewerList": "",
            "url": "api", "remoteUrl": "remote", "artifactId": "artifact",
            "mergeId": "merge", "codeReviewId": 0, "completionQueueTime": "queued",
            "supportsIterations": False,
        }
        pull = self.decode(devops.GitPullRequest, record)[0]
        self.assertEqual((pull.pull_request_id, pull.is_draft, pull.code_review_id),
                         (0, False, 0))
        self.assertFalse(pull.supports_iterations)
        for name, model in (
            ("repository", models.GitRepository),
            ("created_by", models.PullRequestCreatedBy),
            ("closed_by", models.PullRequestClosedBy),
            ("auto_complete_set_by", models.PullRequestAutoCompleteSetBy),
        ):
            self.assertIs(type(getattr(pull, name)), model)
        for field in fields(models.GitPullRequest):
            wire_name = field.metadata.get("wire_name", field.name)
            if not isinstance(record[wire_name], (dict, list)):
                self.assertEqual(getattr(pull, field.name), record[wire_name])
        self.assertIs(type(pull.reviewers[0]), models.PullRequestReviewer)
        self.assertEqual(pull.reviewers[0].vote, 0)
        self.assertFalse(pull.reviewers[0].has_declined)
        self.assertFalse(pull.reviewers[0].is_flagged)
        self.assertFalse(pull.reviewers[0].is_required)
        self.assertIs(type(pull.reviewers[0].voted_for[0]), models.PullRequestReviewer)
        self.assertEqual(pull.reviewers[0].voted_for[0].id, "team")
        self.assertEqual(pull.reviewers[0].voted_for[0].voted_for, [])
        self.assertIs(type(pull.commits[0]), models.GitCommitRef)
        self.assertEqual(pull.commits[0].commit_id, "commit")
        self.assertIs(
            type(pull.completion_options), models.PullRequestCompletionOptions,
        )
        self.assertFalse(pull.completion_options.delete_source_branch)
        self.assertIs(type(pull.merge_options), models.PullRequestMergeOptions)
        self.assertEqual(pull.merge_options.no_fast_forward, "false")
        self.assertEqual(pull.merge_options.rebase, "false")
        self.assertEqual(pull.merge_options.rebase_merge, "false")
        self.assertEqual(pull.merge_options.squash, "false")

    def test_tfvc_fields_and_typed_author_identities(self):
        """Use changeset models rather than a Git commit or push model."""
        record = {"changesetId": 0, "author": {"displayName": "", "uniqueName": "a"},
                  "checkedInBy": {"displayName": "checker", "uniqueName": "b"},
                  "createdDate": "2026-10-28T01:00:00Z", "comment": ""}
        changeset = self.decode(devops.TfvcChangeset, record)[0]
        self.assertEqual((changeset.changeset_id, changeset.comment), (0, ""))
        self.assertEqual(changeset.created_date, record["createdDate"])
        self.assertIs(type(changeset.author), models.ChangesetAuthor)
        self.assertIs(type(changeset.checked_in_by), models.ChangesetCheckedInBy)
        self.assertEqual(changeset.author.display_name, "")
        self.assertEqual(changeset.checked_in_by.unique_name, "b")

    def test_custom_work_item_fields_keep_exact_json_and_names(self):
        """Preserve dotted custom columns, nested JSON, nulls, and falsy values."""
        record = {"id": 0, "rev": 0, "url": "api", "fields": {
            "System.Title": "\u00e9quipe", "Custom.Flag": False, "Custom.Count": 0,
            "Custom.Null": None, "Custom.Empty": "", "Custom.Array": [None, False],
            "Custom.Object": {"Id": "upper", "id": "lower", "value": [],
                              "body": {"dynamicProperties": None}},
            "additional_properties": {"not": "an envelope"},
        }}
        original = copy.deepcopy(record)
        item = self.decode(devops.TriggerWorkItemResponse, record)[0]
        self.assertEqual((item.id, item.rev, item.url), (0, 0, "api"))
        self.assertIsInstance(item.fields, dict)
        self.assertEqual(item.fields, original["fields"])
        self.assertEqual(record, original)

    def test_work_item_fields_empty_null_and_invalid_shapes(self):
        """Only a dictionary or null can represent the generated fields bag."""
        for value in ({}, None):
            self.assertEqual(
                self.decode(
                    devops.TriggerWorkItemResponse, {"fields": value},
                )[0].fields,
                value,
            )
        for value in ([], "bad", 0, False):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "fields"):
                    self.decode(devops.TriggerWorkItemResponse, {"fields": value})

    def test_record_and_batch_encodings_for_each_binding(self):
        """Accept object, array, callback body, and OData batch in JSON or bytes."""
        for binding in self.binding_types():
            identity = {
                devops.GitPush: "pushId", devops.GitPullRequest: "pullRequestId",
                devops.TfvcChangeset: "changesetId",
            }.get(binding, "id")
            record = {identity: 42}
            for payload in (
                record, [record], {"body": record}, {"body": [record]},
                {"value": [record]}, {"body": {
                    "value": [record], "@odata.nextLink": "not-fetched",
                    "odata.context": "items",
                }},
            ):
                text = json.dumps(payload)
                for value in (payload, text, text.encode(), bytearray(text.encode())):
                    with self.subTest(binding=binding, value=value):
                        result = self.decode(binding, value)
                        self.assertEqual(len(result), 1)
                        self.assertIs(type(result[0]),
                                      getattr(models, binding.__name__))
                        field = next(field for field in fields(type(result[0]))
                                     if field.metadata.get("wire_name", field.name)
                                     == identity)
                        self.assertEqual(getattr(result[0], field.name), 42)

    def test_transport_collections_preserve_source_order(self):
        """Flatten Poll MANY event and source batches without dropping records."""
        for binding in self.binding_types():
            events = [json.dumps({"body": {"value": [{}, {}]}}), json.dumps({}),
                      json.dumps([])]
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=events)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[event.encode() for event in events],
                )),
            ):
                with self.subTest(binding=binding, data_type=data_type):
                    result = binding(data=Datum(
                        value=collection, type=data_type,
                    )).get_sdk_type()
                    self.assertEqual(len(result), 3)
                    self.assertTrue(all(type(item) is getattr(models, binding.__name__)
                                        for item in result))
        events = [json.dumps({"id": 1}), json.dumps({"value": [{"id": 2}, {"id": 3}]})]
        result = devops.BuildResult(data=Datum(
            value=SimpleNamespace(string=events), type="collection_string",
        )).get_sdk_type()
        self.assertEqual([item.id for item in result], [1, 2, 3])

    def test_record_body_and_value_do_not_mask_typed_fields(self):
        """Only unwrap sole-body and OData-only value envelope dictionaries."""
        for value in ([], None, "custom", False):
            item = self.decode(devops.TriggerWorkItemResponse, {
                "id": 42, "fields": {"Custom.Column": value},
                "value": value, "body": {"id": "wrong"},
            })[0]
            self.assertEqual(item.id, 42)
            self.assertEqual(item.fields, {"Custom.Column": value})

    def test_empty_callbacks_and_optional_sdk_fields(self):
        """Distinguish no-work batches from a record with absent optional fields."""
        for binding in self.binding_types():
            for payload in ([], {"body": None}, {"body": []}, {"value": None},
                            {"value": [], "@odata.context": "items"}):
                with self.subTest(binding=binding, payload=payload):
                    self.assertEqual(self.decode(binding, payload), [])
            item = self.decode(binding, {})[0]
            self.assertTrue(all(getattr(item, field.name) is None
                                for field in fields(type(item))))
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=[])),
                ("collection_bytes", SimpleNamespace(bytes=[])),
            ):
                self.assertEqual(binding(data=Datum(
                    value=collection, type=data_type,
                )).get_sdk_type(), [])

    def test_invalid_source_and_batch_members_raise(self):
        """Reject malformed data instead of returning partial or empty SDK items."""
        for binding in self.binding_types():
            for payload in ("invalid", b"\xff", None, False, 0, {"body": "bad"},
                            {"value": {}}, {"value": "bad"}, {"value": [{}, None]},
                            [{}, False], {"body": [1]}):
                with self.subTest(binding=binding, payload=payload):
                    with self.assertRaises(ValueError):
                        self.decode(binding, payload)

    def test_missing_data_follows_existing_converter_contract(self):
        """Return None through the converter but reject missing direct input."""
        for binding in self.binding_types():
            self.assertIsNone(devops.ConnectorConverter.decode(
                data=None, trigger_metadata=None, pytype=binding,
            ))
            with self.assertRaisesRegex(ValueError, "No data provided"):
                binding(data=None).get_sdk_type()
