---
title: SDK Overview
description: A high-level introduction to the Mosaico Python SDK for beginners.
sidebar:
    order: 1
---

The **Mosaico SDK** serves as the primary bridge between your application code and the **Mosaico Data Platform**. It is designed to abstract away the complexities of high-performance network communication and binary serialization, providing a clean, Python-native interface for managing multi-modal robotics data.

It acts as a bridge, allowing you to ingest data directly from [ROS](https://www.ros.org/) and export it into Pandas or PyTorch for Machine Learning.

This guide introduces the fundamental concepts and mechanisms you will encounter when using the SDK.

## Core Mechanisms

The Mosaico SDK is engineered to handle the high-throughput demands of robotics data natively in Python. Its architecture is built upon several core mechanisms that ensure performance, type safety, and ease of use without requiring the user to manage low-level network complexity.

### High-Performance Client Architecture

At the heart of the SDK is the client, which acts as a resource manager to orchestrate operations across three distinct layers. This design prevents heavy data processing from blocking the main application thread, ensuring that control operations remain responsive even during intensive workloads.

### Structured Data Handling

Data interaction within the SDK is strictly typed and managed through specialized components designed for specific stages of the data lifecycle.

**Writing Data** is managed by dedicated Writers that enforce a strict lifecycle protocol. A sequence must be explicitly created, populated, and then finalized. This process ensures data immutability and integrity; once a sequence is finalized on the server, it becomes a permanent record that cannot be altered, preserving the lineage of the data.

**Reading Data** is handled by Handlers, which provide access to existing datasets. The SDK offers two distinct strategies for consuming this data:
*  **Unified Streaming:** Ideally suited for sensor fusion or system replay, this mode performs a client-side merge sort to combine multiple sensor topics into a single stream. Messages are yielded in strict chronological order, regardless of the source sensor's frequency.
*  **Targeted Streaming:** For applications that require high-speed access to a single sensor, such as training a model solely on IMU data, this mode bypasses the synchronization overhead and opens a direct, high-throughput channel to the specific topic.

### Strongly-Typed Ontology

Unlike generic key-value stores that rely on unstructured dictionaries, the Mosaico SDK enforces a strict schema using a Python-native Ontology. Data types such as IMUs, Images, or Poses are defined as classes that inherit from a common serializable base.

This approach ensures that all data is validated at runtime before it leaves the client. It also allows the SDK to automatically map these Python objects to efficient Apache Arrow schemas for binary transport. This eliminates the ambiguity of loose JSON blobs and ensures that the data stored in the platform is always structurally consistent and queryable.
## Core Mechanisms

The SDK is engineered to handle the specific demands of robotics and IoT data, which often involve high-throughput streams (like video or Lidar) and complex, nested structures. Its core philosophy is built on:

* **Performance:** It utilizes a layered architecture to ensure that heavy data processing does not block your application's control logic.
* **Type Safety:** Unlike generic databases that store unstructured blobs, the SDK enforces a strict schema for all data, ensuring validity and consistency.
* **Ease of Use:** It provides high-level abstractions for complex tasks like time-synchronization and data ingestion, allowing you to focus on your logic rather than data plumbing.

## Client Architecture

The `MosaicoClient` is your entry point to the platform. It acts as a resource manager that orchestrates the connection to the server and manages the lifecycle of your data operations.

Through the client, users perform the following main operations:

* **Connection Management:** Establishing and maintaining the link to the Mosaico server. The client automatically manages pools of connections and background threads to maximize throughput.
* **Resource Creation:** Initializing new recording sessions (Sequences) to upload data.
* **Resource Retrieval:** Obtaining "Handlers" for existing data. These handlers allow you to inspect metadata and access data streams for specific sequences or topics.
* **Querying:** searching the catalog to find specific data based on metadata tags or deep content inspection.
* **Cleanup:** Deleting incomplete or malformed sequences to maintain a clean repository.

## Data Handling

Interaction with data streams is divided into two distinct roles: **Writing** (ingestion) and **Reading** (retrieval).

### Writing Data
Writing is managed by **Writers**, which enforce a strict lifecycle to ensure data integrity.
* **Sequence Creation:** Users start by creating a sequence writer.
* **Topic Registration:** Within a sequence, users define specific topics (streams) and assign them a data type.
* **Pushing Data:** Data is pushed to these topics. The writer handles buffering and batching automatically.
* **Finalization:** Once writing is complete, the sequence is finalized and "locked," becoming immutable.

### Reading Data
Reading is managed by **Handlers**, `SequenceHandler` and `TopicHandler`, which provide access to stored data.
* **Unified Streaming:** Ideally suited for system replay or sensor fusion, this mode combines multiple topics into a single stream. The SDK performs a "k-way merge sort" to yield messages from all sensors in strict chronological order.
* **Targeted Streaming:** For applications needing only specific data (e.g., training a model solely on IMU data), users can open a direct stream to a single topic, bypassing synchronization overhead for maximum speed.

## Ontology

Mosaico employs a **Strongly-Typed Ontology** to define the "shape" of data. Instead of treating files as raw bytes or using loose dictionaries, every data point is an instance of a specific class (e.g., `Image`, `IMU`, `GPS`).

* **Validation:** Data objects are validated at runtime, preventing invalid data from entering the system.
* **Serialization:** These Python objects are automatically mapped to efficient binary schemas (Apache Arrow) for high-performance storage and transport.
* **Extensibility:** Users can define their own custom ontology models to represent domain-specific data types.

## Machine Learning Module

The **ML Module** acts as a bridge between the raw, asynchronous world of robotics and the synchronous, tabular world of Machine Learning.

It allows users to perform two critical operations:

1.  **Flattening (Extraction):** The module can convert complex, nested sensor streams into flat, columnar DataFrames (like those used in Pandas). It handles the recursive unpacking of data structures into simple columns.
2.  **Synchronization:** Robotics sensors often operate at different frequencies (e.g., 100Hz IMU vs. 30Hz Camera). The ML module provides tools to resample and align these heterogeneous streams onto a uniform time grid, making them ready for training deep learning models.
i
The **Mosaico SDK** is the primary interface for interacting with the **Mosaico Data Platform**, a high-performance system designed for the ingestion, storage, and retrieval of multi-modal sensor data (Robotics, IoT).

Unlike generic time-series databases, Mosaico understands the semantics of complex sensor data types—from LIDAR point clouds and high-res images to telemetry and transformations. This SDK provides Python-native bindings to define data using a strongly-typed Ontology, ingest streams with automatic batching, and retrieve synchronized sequences for analysis.
