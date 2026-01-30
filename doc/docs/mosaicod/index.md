---
title: Backend Overview
description: Architecture and design of the mosaicod daemon.
sidebar: 
    order: 1
---

The **Mosaico Daemon**, a.k.a. `mosaicod`, acts as the authoritative kernel of the data platform. Developed in **Rust**, it is engineered to be the high-performance arbiter for all data interactions, guaranteeing that every byte of robotics data is strictly typed, atomically stored, and efficiently retrievable.

It functions on a standard client-server model, mediating between your high-level applications (via the SDKs) and the low-level storage infrastructure.

## Architectural Design

`mosaicod` is architected atop the **Apache Arrow Flight** protocol. Unlike traditional REST APIs which serialize data into text-based JSON, Flight is designed specifically for the transport of massive datasets over gRPC. This architectural choice provides Mosaico with three critical advantages:

**Zero-Copy Serialization.** Data is transmitted in the Apache Arrow columnar format, the exact same format used in-memory by modern analytics tools like pandas and Polars. This eliminates the CPU-heavy cost of serializing and deserializing data at every hop.

**Parallelized Transpor.** Operations are not bound to a single pipe; data transfer can be striped across multiple TCP connections to saturate available bandwidth.

**Snapshot-Based Schema Enforcement.** Data types are not guessed, nor are they forced into a rigid global model. Instead, the protocol enforces a rigorous schema handshake that validates data against a specific schema snapshot stored with the sequence.

### The Three Layers

To manage complexity and performance, the server segregates its operations into three distinct logical layers:

**Control Layer.** The administrative brain of the system. It handles metadata management, resource orchestration, and configuration via synchronous commands.

**Ingestion Layer.** A dedicated high-speed lane for writing data. It utilizes streaming endpoints to accept raw sensor data at wire speed.

**Retrieval Layer.** A dedicated high-speed lane for reading data. It streams requested data slices back to clients with minimal latency.

### Snapshot Schema

Robotics data is inherently dynamic; sensor configurations change, message definitions evolve rapidly, and experimental setups vary from run to run. Mosaico is designed to let teams focus on development rather than managing complex schema migrations or worrying about backward compatibility breaking old datasets.

To achieve this, Mosaico moves away from the concept of a rigid, global schema. Instead, it associates a specific **Schema Snapshot** with **each individual sequence**.

**Sequence-Scoped Definitions:** When a sequence is created, `mosaicod` captures and stores the exact schema blueprint used at that moment. This includes the precise structure of every topic and sensor message.

**Perfect Reconstruction:** Because the schema is immutable and attached directly to the data, the SDK can reconstruct the objects exactly as they were defined when the data was uploaded. This ensures that a recording from six months ago remains perfectly readable today, even if your current project's ontology has completely changed.

### Storage

`mosaicod` employs a hybrid storage strategy to balance speed and scalability:

**Hot State (Metadata).** Structural information—the catalog of sequences, topics, layer definitions, and validation schemas—is stored in a **PostgreSQL** database. This allows for complex, relational queries and transactional integrity for administrative actions.

**Cold State (Bulk Data).** The actual heavy sensor data (images, Lidar point clouds) is stored in an **Object Store**. By default, Mosaico uses the local filesystem for simplicity, but for production environments, it natively supports S3-compatible storage (AWS S3, MinIO, Google Cloud Storage).

This separation decouples compute from storage, allowing the platform to scale its data retention infinitely without degrading the performance of metadata operations.

Since we care about data,, the system is architected such that the *Hot State is completely reconstructible from the Cold State*. This means that if the database goes down or becomes corrupted, it is always possible to rebuild the entire metadata catalog by scanning the Cold State. Since the Cold State typically resides on an Object Store with extremely high durability and redundancy (like S3), this design ensures your data remains resilient and recoverable even in the face of catastrophic infrastructure failures.