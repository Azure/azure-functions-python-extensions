#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic callback tests for the eleven documented Teams trigger operations."""

import copy
import json
import unittest
from dataclasses import fields
from types import SimpleNamespace
from typing import List

import azure.connectors.teams as models
import azurefunctions.extensions.connectors.teams as teams
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.connectorConverter import ConnectorConverter


MODEL_BINDING_NAMES = (
    "ChatMessage",
    "ChatMessageWebhookResponseSchema",
    "DynamicNewMessageWebhookTriggerResponseSchema",
    "DynamicAtMentionWebhookTriggerResponseSchema",
    "DynamicKeywordWebhookTriggerResponseSchema",
    "MessageReactionWebhookResponseSchema",
    "RecordingWebhookResponseSchema",
    "TranscriptWebhookResponseSchema",
)
DYNAMIC_BINDING_NAMES = (
    "DynamicNewMessageWebhookTriggerResponseSchema",
    "DynamicAtMentionWebhookTriggerResponseSchema",
    "DynamicKeywordWebhookTriggerResponseSchema",
)


class TestTeamsBindings(unittest.TestCase):
    """Keep polling items, dynamic events, and webhook envelopes distinct."""

    def test_model_bindings_export_generated_models_and_annotations(self):
        """Expose each SDK model through a discoverable extension binding."""
        for name in MODEL_BINDING_NAMES:
            binding_type = getattr(teams, name)
            with self.subTest(name=name):
                self.assertIn(name, teams.__all__)
                self.assertTrue(issubclass(binding_type, getattr(models, name)))
                self.assertFalse(binding_type.supports_deferred_binding())
                for annotation in (
                    binding_type, List[binding_type], list[binding_type],
                ):
                    self.assertTrue(
                        ConnectorConverter.check_input_type_annotation(annotation),
                    )
                    self.assertIsNone(ConnectorConverter.decode(
                        data=None, trigger_metadata=None, pytype=annotation,
                    ))
                self.assertFalse(ConnectorConverter.check_input_type_annotation(
                    getattr(models, name),
                ))

    def test_channel_messages_preserve_all_fields_and_their_own_body(self):
        """Deserialize the SDK item while retaining nested JSON dictionaries."""
        record = {
            "id": "message-1", "body": {"content": "Hello", "contentType": "text"},
            "from": {"user": {"id": "user-1", "optional": None}},
            "attachments": [{"id": "attachment-1", "custom": False}],
            "createdDateTime": "2026-10-21T10:00:00Z", "deleted": False,
            "etag": "", "importance": "normal",
            "lastModifiedDateTime": "2026-10-21T11:00:00Z", "locale": "en-US",
            "mentions": [{"id": 0}], "messageType": "message",
            "reactions": [{"reactionType": "like"}], "replyToId": "parent-1",
            "subject": None, "summary": "Summary",
        }
        original = copy.deepcopy(record)
        for payload in (record, [record], {"body": record}, {"body": [record]},
                        {"value": [record]}, {"body": {"value": [record]}}):
            for value in (payload, json.dumps(payload), json.dumps(payload).encode()):
                with self.subTest(value=value):
                    result = teams.ChatMessage(data=Datum(
                        value=value, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    message = result[0]
                    self.assertIs(type(message), models.ChatMessage)
                    for model_field in fields(models.ChatMessage):
                        wire_name = model_field.metadata.get(
                            "wire_name", model_field.name,
                        )
                        self.assertEqual(
                            getattr(message, model_field.name), record[wire_name],
                        )
        self.assertEqual(record, original)

    def test_membership_binding_preserves_arbitrary_json_records(self):
        """The SDK membership alias has dictionaries, not a fixed item model."""
        record = {"id": "user-1", "body": {"enabled": False}, "value": [],
                  "count": 0, "optional": None, "roles": ["member"]}
        self.assertIn("OnGroupMemberChangeResponse", teams.__all__)
        self.assertFalse(teams.OnGroupMemberChangeResponse.supports_deferred_binding())
        for annotation in (teams.OnGroupMemberChangeResponse,
                           List[teams.OnGroupMemberChangeResponse]):
            self.assertTrue(ConnectorConverter.check_input_type_annotation(annotation))
            for payload in (record, [record], {"body": record}, {"value": [record]}):
                with self.subTest(annotation=annotation, payload=payload):
                    result = ConnectorConverter.decode(
                        data=Datum(value=payload, type="json"),
                        trigger_metadata=None, pytype=annotation,
                    )
                    self.assertEqual(result, [record])
                    self.assertIs(type(result[0]), dict)

    def test_chat_webhook_preserves_notification_envelope_boundaries(self):
        """Keep reference collections inside their generated SDK envelope."""
        references = [
            {"conversationId": "chat-1", "messageId": "message-1",
             "linkToMessage": "https://example.test/message", "optional": None},
            {"conversationId": "chat-2", "messageId": "message-2"},
        ]
        for notification_value in (references, [], None):
            for payload in ({"value": notification_value},
                            {"body": {"value": notification_value}}):
                for value in (payload, json.dumps(payload)):
                    with self.subTest(value=value):
                        result = teams.ChatMessageWebhookResponseSchema(data=Datum(
                            value=value, type="json",
                        )).get_sdk_type()
                        self.assertEqual(len(result), 1)
                        self.assertIs(
                            type(result[0]), models.ChatMessageWebhookResponseSchema,
                        )
                        self.assertEqual(result[0].value, notification_value)

    def test_chat_webhook_rejects_invalid_reference_collections(self):
        """Validate the envelope's own value array rather than dropping entries."""
        for value in ("invalid", [{"messageId": "valid"}, None], [False], {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    teams.ChatMessageWebhookResponseSchema(data=Datum(
                        value={"body": {"value": value}}, type="json",
                    )).get_sdk_type()

    def test_dynamic_webhooks_preserve_entire_notification_objects(self):
        """Do not interpret arbitrary value or additional_properties columns."""
        record = {"id": "message-1", "body": {"content": "Hello"},
                  "value": [{"id": "nested"}], "enabled": False, "count": 0,
                  "optional": None, "additional_properties": {"custom": True}}
        original = copy.deepcopy(record)
        for name in DYNAMIC_BINDING_NAMES:
            binding_type = getattr(teams, name)
            for payload in (record, {"body": record}, [record]):
                for value in (payload, json.dumps(payload)):
                    with self.subTest(name=name, value=value):
                        result = binding_type(data=Datum(
                            value=value, type="json",
                        )).get_sdk_type()
                        self.assertEqual(len(result), 1)
                        self.assertIs(type(result[0]), getattr(models, name))
                        self.assertEqual(result[0].additional_properties, record)
        self.assertEqual(record, original)

    def test_dynamic_webhook_value_only_notifications_are_not_batches(self):
        """Preserve empty and null value fields as notification data."""
        for name in DYNAMIC_BINDING_NAMES:
            for value in ([], None, [{"messageId": "nested"}]):
                with self.subTest(name=name, value=value):
                    result = getattr(teams, name)(data=Datum(
                        value={"value": value}, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].additional_properties, {"value": value})

    def test_reaction_webhook_maps_all_nine_fields(self):
        """Use the notification schema, not a subscription acknowledgement."""
        record = {"threadType": "chat", "chatId": "chat-1", "teamId": "",
                  "channelId": None, "messageId": "message-1", "replyToId": "parent",
                  "messageLink": "https://example.test/message", "userId": "user-1",
                  "messageReaction": "like"}
        result = teams.MessageReactionWebhookResponseSchema(data=Datum(
            value={"body": record}, type="json",
        )).get_sdk_type()
        self.assertEqual(len(result), 1)
        for model_field in fields(models.MessageReactionWebhookResponseSchema):
            self.assertEqual(
                getattr(result[0], model_field.name),
                record[model_field.metadata["wire_name"]],
            )

    def test_recording_and_transcript_preserve_ids_and_nested_identities(self):
        """Keep id and @odata.id separate, with a typed organizer model."""
        organizer = {"user": {"id": "user-1", "@odata.type": "identity",
                              "userPrincipalName": None},
                     "application": {"id": "app-1", "custom": False},
                     "device": {"id": "device-1"}}
        for name, content_field in (
            ("RecordingWebhookResponseSchema", "recordingContentUrl"),
            ("TranscriptWebhookResponseSchema", "transcriptContentUrl"),
        ):
            record = {"id": "resource-1", "@odata.id": "odata-resource-1",
                      "meetingId": "", "callId": "call-1",
                      "contentCorrelationId": "correlation-1",
                      "meetingOrganizer": organizer,
                      content_field: "https://example.test/content",
                      "createdDateTime": "2026-10-21T10:00:00Z", "endDateTime": None}
            for payload in (record, {"body": record}, [record]):
                with self.subTest(name=name, payload=payload):
                    result = getattr(teams, name)(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    item = result[0]
                    self.assertIs(type(item), getattr(models, name))
                    self.assertEqual(item.id, "resource-1")
                    self.assertEqual(item.id_2, "odata-resource-1")
                    self.assertEqual(item.meeting_id, "")
                    self.assertEqual(item.call_id, "call-1")
                    self.assertEqual(item.content_correlation_id, "correlation-1")
                    self.assertIs(type(item.meeting_organizer), models.TeamsIdentitySet)
                    self.assertEqual(item.meeting_organizer.user, organizer["user"])
                    self.assertEqual(
                        item.meeting_organizer.application, organizer["application"],
                    )
                    self.assertEqual(item.meeting_organizer.device, organizer["device"])
                    self.assertEqual(item.created_date_time, record["createdDateTime"])
                    self.assertIsNone(item.end_date_time)
                    self.assertEqual(
                        getattr(
                            item,
                            "recording_content_url" if name.startswith("Recording")
                            else "transcript_content_url",
                        ), record[content_field],
                    )

    def test_poll_many_keeps_webhook_boundaries_and_flattens_polling_batches(self):
        """Choose normalization by the selected binding, not the transport type."""
        cases = (
            (teams.ChatMessage, [{"body": {"id": "1"}}, [{"id": "2"}]], 2),
            (teams.OnGroupMemberChangeResponse,
             [[{"id": "1"}], {"value": [{"id": "2"}]}], 2),
            (teams.ChatMessageWebhookResponseSchema,
             [{"value": [{"messageId": "1"}, {"messageId": "2"}]}, {"value": []}], 2),
            (teams.DynamicNewMessageWebhookTriggerResponseSchema,
             [{"value": []}, {"value": [{"id": "2"}]}], 2),
        )
        for binding_type, events, expected_count in cases:
            strings = [json.dumps(event) for event in events]
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=strings)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[value.encode() for value in strings],
                )),
            ):
                with self.subTest(binding=binding_type, data_type=data_type):
                    result = binding_type(data=Datum(
                        value=collection, type=data_type,
                    )).get_sdk_type()
                    self.assertEqual(len(result), expected_count)
                    if binding_type is teams.ChatMessage:
                        self.assertEqual([item.id for item in result], ["1", "2"])
                    elif binding_type is teams.OnGroupMemberChangeResponse:
                        self.assertEqual(result, [{"id": "1"}, {"id": "2"}])
                    elif binding_type is teams.ChatMessageWebhookResponseSchema:
                        self.assertEqual(result[0].value, events[0]["value"])
                        self.assertEqual(result[1].value, [])
                    else:
                        self.assertEqual(
                            [item.additional_properties for item in result], events,
                        )

    def test_empty_and_malformed_payloads_for_all_bindings(self):
        """Reject bad members and preserve missing-data and no-work contracts."""
        for name in MODEL_BINDING_NAMES + ("OnGroupMemberChangeResponse",):
            binding_type = getattr(teams, name)
            for payload in ([], {"body": None}):
                with self.subTest(name=name, empty=payload):
                    self.assertEqual(binding_type(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type(), [])
            self.assertEqual(binding_type(data=Datum(
                value=SimpleNamespace(string=[]), type="collection_string",
            )).get_sdk_type(), [])
            for payload in ("not-json", b"\xff", None, 1, {"body": "bad"},
                            [{"id": "valid"}, None]):
                with self.subTest(name=name, invalid=payload):
                    with self.assertRaises(ValueError):
                        binding_type(data=Datum(
                            value=payload, type="json",
                        )).get_sdk_type()
            with self.assertRaisesRegex(ValueError, "No data provided"):
                binding_type(data=None).get_sdk_type()

    def test_polling_empty_and_invalid_value_batches(self):
        """Only polling bindings extract value as a source batch."""
        for binding_type in (teams.ChatMessage, teams.OnGroupMemberChangeResponse):
            for value in ([], None):
                self.assertEqual(binding_type(data=Datum(
                    value={"value": value}, type="json",
                )).get_sdk_type(), [])
            for value in ("bad", [{"id": "valid"}, False]):
                with self.assertRaises(ValueError):
                    binding_type(data=Datum(
                        value={"value": value}, type="json",
                    )).get_sdk_type()

    def test_registry_contains_core_operations_when_available(self):
        """Older SDK registries omit recording and transcript despite their models."""
        registry = getattr(models, "TRIGGER_OPERATIONS", None)
        if registry is None:
            self.skipTest("This SDK does not expose a Teams trigger registry.")
        for operation in (
            "OnNewChannelMessage", "OnNewChannelMessageMentioningMe",
            "OnGroupMembershipAdd", "OnGroupMembershipRemoval",
            "WebhookChatMessageTrigger", "WebhookNewMessageTrigger",
            "WebhookAtMentionTrigger", "WebhookKeywordTrigger",
            "WebhookMessageReactionTrigger",
        ):
            with self.subTest(operation=operation):
                self.assertIn(operation, registry)
