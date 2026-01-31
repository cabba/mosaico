---
title: Control Layer
description: Managing resources via synchronous actions.
sidebar:
    order: 2
---

The **Control Layer** serves as the administrative interface for Mosaico. It is accessed via the Arrow Flight `DoAction` RPC mechanism. Unlike the streaming layers which handle continuous flows of data, operations in the Control Layer are **synchronous** and **transactional**. This means every request is atomic: it either completes successfully, ensuring the system state is updated, or it fails entirely without side effects.

All actions in this layer follow a standardized pattern: they expect a JSON-serialized payload defining the request parameters and return a JSON-serialized response containing the result.

Here is the rewritten section using tables for better readability.

## Sequence Management

Sequences are the fundamental containers for data recordings in Mosaico. The Control Layer enforces a strict lifecycle state machine to guarantee data integrity.

| Action | Description |
| --- | --- |
| **`sequence_create`** | Initializes a new, empty sequence. It generates and returns a unique key (UUID). This key acts as a write token, authorizing subsequent data ingestion into this specific sequence. This avoids concurrent access and creation issues when multiple clients attempt to create sequences simultaneously. |
| **`sequence_finalize`** | Transitions a sequence from *uploading* to *archived*. This action locks the sequence, marking it as immutable. Once finalized, no further data can be added or modified, ensuring a perfect audit trail. |
| **`sequence_abort`** | A cleanup operation for failed uploads. It discards a sequence that is currently being uploaded, purging any partial data from the storage to prevent *zombie* records. |
| **`sequence_delete`** | Permanently removes a sequence from the platform. To protect data lineage, this is typically permitted only on unlocked (incomplete) sequences. |
| **`sequence_system_info`** | Provides low-level diagnostics, such as the total byte size, chunk count, and disk usage of a sequence. |

## Topic Management

Topics represent the individual sensor streams (e.g., `camera/front`, `gps`) contained within a sequence.

| Action | Description |
| --- | --- |
| **`topic_create`** | Registers a new topic. |
| **`topic_delete`** | Removes a specific topic from a sequence, permitted only if the parent sequence is still unlocked. |
| **`topic_system_info`** | Retrieves storage statistics specific to a single topic. |

## Notification System

The platform includes a tagging mechanism to attach alerts or informational messages to resources. For example, if an exception is raised during an upload, the notification system automatically registers the event, ensuring the failure is logged and visible for troubleshooting.

| Action | Description |
| --- | --- |
| **`*_notify_create`** | Attaches a notification to a Sequence or Topic. |
| **`*_notify_list`** | Retrieves the history of active notifications for a resource. |
| **`*_notify_purge`** | Clears the notification history. |

## Query Entrypoint

| Action | Description |
| --- | --- |
| **`query`** | This action serves as the gateway to the Query Engine. It accepts a complex filter object and returns a list of resources that match the criteria. |