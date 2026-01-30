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
with MosaicoClient.connect("localhost", 6726) as client:
    # Logic goes here
    pass
# Pools and connections are closed automatically

```

## Quick reference
<!-- TODO: fix and add links. -->
| Method | Description |
| --- | --- |
| `connect()` | Establishes the connection to the server and initializes all data and processing pools. |
| `close()` | Manually shuts down all pools and connections. Called automatically by the context manager (if the instance was created in a `with` block). |
| `sequence_create()` | Creates a [new writer](handlers.md#writing-data) for uploading data. |
| `sequence_handler()` | Retrieves a [handler](handlers.md#reading--handling-data) for an existing sequence. The method does not actually download the sequence data-stream. |
| `topic_handler()` | Retrieves a [handler](handlers.md#reading--handling-data) for a specific topic within a sequence. The method does not actually download the topic data-stream. |
| `query()` | Executes [queries](queries.md) against the data catalogs, i.e. Platform entities (i.e. Sequence or Topic) or Ontology catalog.|
| `sequence_delete()` | Permanently removes a sequence and all its associated data from the server. |
| `list_sequences()` | Retrieves the list of all sequences available on the server. |
| `sequence_system_info()` | Retrieves system-level metadata for a specific sequence. The method queries the server for the physical state of the sequence, including its total storage footprint and creation history. |
| `topic_system_info()` | Retrieves system-level metadata for a specific topic within a sequence. The method queries the server for the physical state of the sequence, including its total storage footprint and creation history. |

