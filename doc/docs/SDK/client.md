---
title: Client Architecture
description: Description of the MosaicoClient class
sidebar:
    order: 2
---

The `MosaicoClient` is a resource manager designed to orchestrate three distinct **Layers** of communication and processing. 
This layered architecture ensures that high-throughput sensor data does not block critical control operations or application logic.

## Control Layer

A single, dedicated connection is maintained for metadata operations. 
This layer handles lightweight tasks such as creating sequences, querying the catalog, and managing schema definitions. 
By isolating control traffic, the client ensures that critical commands (like `sequence_finalize`) are never queued behind heavy data transfers.

## Data Layer

For high-bandwidth data ingestion (e.g., uploading 4x 1080p cameras simultaneously), the client maintains a **Connection Pool** of multiple Flight clients. 
The SDK automatically stripes writes across these connections in a round-robin fashion, allowing the application to saturate the available network bandwidth.

## Processing Layer

Serialization of complex sensor data (like compressing images or encoding LIDAR point clouds) is CPU-intensive. 
The SDK uses an **Executor Pool** of background threads to offload these tasks. 
This ensures that while one thread is serializing the *next* batch of data, another thread is already transmitting the *previous* batch over the network.

**Best Practice:** It is recomended to always use the client inside a `with` context to ensure resources in all layers are cleanly released.

```python
from mosaicolabs import MosaicoClient

with MosaicoClient.connect("localhost", 6726) as client:
    # Logic goes here
    pass
# Pools and connections are closed automatically

```

## Quick reference
<!-- TODO: fix and add links. -->
| Method | Return | Description |
| :--- | :--- | :--- |
| `connect(host, port, timeout)` | `MosaicoClient` | Establishes the connection to the server and initializes all data and processing pools. |
| `close()` | `None` | Manually shuts down all pools and connections. Called automatically by the context manager (if the instance was created in a `with` block). |
| `sequence_create(sequence_name, metadata, on_error, ...)` | `SequenceWriter` | Creates a [new writer](data-handling.md#writing-data) for uploading data. |
| `sequence_handler(sequence_name)` | `Optional[SequenceHandler]` | Retrieves a [handler](data-handling.md#the-reading-workflow) for an existing sequence. The method does not actually download the sequence data-stream. |
| `topic_handler(sequence_name, topic_name)` | `Optional[TopicHandler]` | Retrieves a [handler](data-handling.md#the-reading-workflow) for a specific topic within a sequence. The method does not actually download the topic data-stream. |
| `query(*queries, query)` | `Optional[QueryResponse]` | Executes [queries](query.md) against the platform catalogs. The provided queries are joined in AND condition. The method accepts a variable arguments of query builder objects or a pre-constructed *Query* object.|
| `sequence_delete(sequence_name)` | `None` | Permanently removes a sequence and all its associated data from the server. The operation is allowed only on [unlocked sequences](../index.md#data-lifetime-and-integrity) |
| `list_sequences()` | `List[str]` | Retrieves the list of all sequences available on the server. |
| `sequence_system_info(sequence_name)` | `Optional[SystemInfo]` | Retrieves system-level metadata for a specific sequence. The method queries the server for the physical state of the sequence, including its total storage footprint and creation history. |
| `topic_system_info(sequence_name, topic_name)` | `Optional[SystemInfo]` | Retrieves system-level metadata for a specific topic within a sequence. The method queries the server for the physical state of the sequence, including its total storage footprint and creation history. |

