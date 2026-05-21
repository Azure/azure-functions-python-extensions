# azurefunctions-extensions-bindings-kafka

Kafka Python worker extension for Azure Functions — raw `KafkaRecord` binding with full metadata access.

## Installation

```bash
pip install azurefunctions-extensions-bindings-kafka
```

## Usage

```python
import logging
import azure.functions as func
import azurefunctions.extensions.bindings.kafka as kafka

app = func.FunctionApp()

@app.kafka_trigger(
    arg_name="record",
    topic="my-topic",
    broker_list="%BrokerList%",
    consumer_group="$Default")
def kafka_trigger(record: kafka.KafkaRecord):
    logging.info(f"Topic: {record.topic}, Partition: {record.partition}")
    logging.info(f"Value: {record.value.decode('utf-8')}")

    for header in record.headers:
        logging.info(f"Header: {header.key} = {header.get_value_as_string()}")
```

## KafkaRecord Properties

| Property | Type | Description |
|----------|------|-------------|
| `topic` | `str` | Topic name |
| `partition` | `int` | Partition number |
| `offset` | `int` | Offset within partition |
| `key` | `bytes \| None` | Raw key bytes |
| `value` | `bytes \| None` | Raw value bytes |
| `timestamp` | `KafkaTimestamp` | Timestamp with `unix_timestamp_ms`, `type`, `datetime` |
| `headers` | `list[KafkaHeader]` | Headers with `key` (str) and `value` (bytes \| None) |
| `leader_epoch` | `int \| None` | Leader epoch |

## Samples

See [`samples/kafka_samples_kafkarecord/`](./samples/kafka_samples_kafkarecord/) for a complete working example.

## Related

- [Azure Functions Kafka Extension](https://github.com/Azure/azure-functions-kafka-extension)
- [Kafka bindings documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-kafka)
