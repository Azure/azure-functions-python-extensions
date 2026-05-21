# Kafka Record Trigger Sample

This sample demonstrates how to use the `azurefunctions-extensions-bindings-kafka` extension to bind to raw Apache Kafka records with full metadata access.

## Overview

- Access raw key/value as `bytes` (user controls deserialization)
- Read record metadata: topic, partition, offset, timestamp, leader epoch
- Iterate over Kafka headers
- Supports single and batch (cardinality=MANY) modes

## Prerequisites

- Python 3.9+
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4
- A Kafka broker (Confluent Cloud, Azure Event Hubs with Kafka endpoint, or local Docker broker)

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure local settings

Edit `local.settings.json` and set `BrokerList` to your Kafka broker:

```json
{
  "Values": {
    "BrokerList": "localhost:9092"
  }
}
```

### 4. Run

```bash
func start
```

### 5. Produce messages

Send messages to `my-topic` using any Kafka producer.

## KafkaRecord Properties

| Property | Type | Description |
|----------|------|-------------|
| `topic` | `str` | Topic name |
| `partition` | `int` | Partition number |
| `offset` | `int` | Offset within partition |
| `key` | `bytes \| None` | Raw key bytes |
| `value` | `bytes \| None` | Raw value bytes |
| `timestamp` | `KafkaTimestamp` | Timestamp with `unix_timestamp_ms`, `type`, `datetime` |
| `headers` | `list[KafkaHeader]` | Headers with `key` (str) and `value` (bytes) |
| `leader_epoch` | `int \| None` | Leader epoch |

## Related

- [Azure Functions Kafka Extension](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-kafka)
- [Parent issue: Azure/azure-functions-kafka-extension#612](https://github.com/Azure/azure-functions-kafka-extension/issues/612)
