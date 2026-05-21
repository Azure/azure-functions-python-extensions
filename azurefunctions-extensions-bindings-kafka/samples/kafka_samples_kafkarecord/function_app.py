# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# --------------------------------------------------------------------------

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.bindings.kafka as kafka

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

"""
FOLDER: kafka_samples_kafkarecord
DESCRIPTION:
    These samples demonstrate how to obtain a KafkaRecord from a Kafka Trigger.
USAGE:
    Configure your Kafka broker connection in local.settings.json.
    The BrokerList setting should point to your Kafka bootstrap server(s).
"""


@app.kafka_trigger(
    arg_name="record",
    topic="my-topic",
    broker_list="%BrokerList%",
    consumer_group="$Default",
)
def kafka_trigger(record: kafka.KafkaRecord):
    logging.info(
        "Python Kafka trigger processed a record on topic %s "
        "partition %d offset %d",
        record.topic,
        record.partition,
        record.offset,
    )

    if record.key:
        logging.info("Key: %s", record.key.decode("utf-8"))
    if record.value:
        logging.info("Value: %s", record.value.decode("utf-8"))

    logging.info(
        "Timestamp: %s (type=%s)",
        record.timestamp.datetime.isoformat(),
        record.timestamp.type.name,
    )

    if record.leader_epoch is not None:
        logging.info("Leader Epoch: %d", record.leader_epoch)

    for header in record.headers:
        value_str = header.get_value_as_string() or "(null)"
        logging.info("Header: %s = %s", header.key, value_str)


@app.kafka_trigger(
    arg_name="records",
    topic="my-topic",
    broker_list="%BrokerList%",
    consumer_group="$Default",
    cardinality=func.Cardinality.MANY,
)
def kafka_batch_trigger(records: List[kafka.KafkaRecord]):
    for record in records:
        logging.info(
            "Batch: %s:%d:%d value=%s",
            record.topic,
            record.partition,
            record.offset,
            record.value.decode("utf-8") if record.value else "(null)",
        )
