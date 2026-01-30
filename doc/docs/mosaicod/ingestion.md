---
title: Ingestion Layer
description: High-throughput writing via data streams.
sidebar:
    order: 3
---

Data ingestion in Mosaico is handled by a dedicated **Ingestion Layer**, implemented via the Flight `DoPut` streaming endpoint. This layer is optimized specifically for write-heavy workloads, allowing clients to push high-bandwidth sensor data, such as 4K video streams or high-frequency Lidar.

## The Ingestion Protocol

Uploading a stream involves a rigorous handshake protocol designed to ensure type safety before any data is committed to storage:

**Command Descriptor.** The client initiates the stream by sending a Flight Descriptor containing a JSON command identifying the target topic (e.g., `run_01/sensors/cam_front`) and providing the authorization key generated during topic creation.

**Schema Negotiation.** The very first message sent on the stream **must** be the Apache Arrow Schema definition.
    * The server intercepts this schema and validates it against the registered ontology for that topic.
    * If there is a mismatch (e.g., a client attempts to write an `Image` payload to a topic registered as `IMU`), the server immediately rejects the stream with a validation error, preventing data corruption.

**Data Transmission.** Once the schema is negotiated and accepted, the client streams a sequence of `RecordBatch` payloads. The server buffers these batches in memory and writes them efficiently to the underlying storage.

**Commit Phase.** Closing the stream signals the server that the upload is complete. The server then flushes all buffers, calculates necessary indices, and atomically commits the data chunks to the repository.

## Chunking & Indexing Strategy

To manage massive datasets efficiently, the backend automatically handles *Chunking*. As data flows in, `mosaicod` splits the continuous stream into optimal storage units called *Chunks*.

For every chunk written, the server computes and stores *skip indices* in the metadata database contaning ontology statistics i.e. type-specific metadata (e.g., coordinate bounding boxes for GPS, value ranges for sensors) that enables the Query Engine to perform content-based filtering without reading the bulk data.