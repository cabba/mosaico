---
title: Retrieval Layer
description: Streaming data via the Ticket mechanism.
sidebar:
    order: 4
---

Reading data is the responsibility of the **Retrieval Layer**, handled via the Flight `DoGet` endpoint. This layer allows clients to request specific slices of data, which are then streamed back as a sequence of Arrow batches.

## The Ticket Mechanism

Unlike standard REST APIs where parameters are embedded in the URL, Flight uses a binary token known as a **Ticket**. In Mosaico, this Ticket is a serialized request object containing:
* **Locator:** The precise path of the topic to read.
* **Time Range (Optional):** A specific start and end timestamp (in nanoseconds).

When the server receives a Ticket, it executes a three-step resolution process:
1.  **Index Lookup:** It consults the PostgreSQL metadata to identify which physical Chunks contain data overlapping the requested time range.
2.  **Pruning:** It filters out any chunks that fall strictly outside the requested window, avoiding unnecessary I/O.
3.  **Streaming:** It opens only the relevant chunk files and streams their content back to the client.

## Smart Batching

The server performs more than just a file dump; it implements **Smart Batching** to optimize network performance:
* It analyzes the schema structure and the compression ratio of the stored data.
* It dynamically computes an optimal `RecordBatch` size. This ensures that network packets are fully utilized while preventing Out-Of-Memory (OOM) errors on the client side, which can occur when deserializing massive, monolithic batches.

## Metadata Context Headers

To ensure the client has full context, the data stream is prefixed with a Schema message containing embedded custom metadata. Mosaico injects rich context into this header, allowing the client to reconstruct the full environment:
* **User Metadata:** The original JSON tags and configuration provided during creation.
* **Ontology Tag:** The specific data type version.
* **Serialization Format:** Details on how the binary data is structured.