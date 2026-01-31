---
title: Reading & Writing Data
description: Handlers, Writers, and Streamers.
---

The **Data Handling** module is the operational core of the Mosaico SDK, providing the necessary tools to move multi-modal sensor data between your application and the Mosaico Data Platform. 
It is designed for high-throughput ingestion and chronologically accurate retrieval, abstracting away the complexities of network I/O, buffering, and time-synchronization.
The SDK separates concerns into **Writers** (for ingestion) and **Handlers** (for retrieval), optimizing each for its specific traffic pattern.

### Memory-Efficient Data Flow

The Mosaico SDK is engineered to handle the massive data volumes characteristic of robotics and autonomous systems without exhausting local system resources. Whether you are ingesting new streams or retrieving existing ones, the SDK implements a consistent **Smart Batching & Buffering** strategy to ensure high performance and stability.

* **Resource Optimization**: Both reading and writing operations are executed in **memory-limited batches** rather than loading or sending entire sequences at once.
* **Background Processing**: The SDK utilizes the asynchronous **Data and Processing Layers** of the `MosaicoClient` to manage data serialization and network I/O.
* **Automatic Lifecycle**: In reading workflows, processed batches are automatically discarded and replaced with new data fetched from the server. In writing workflows, the SDK automatically flushes local buffers once they exceed configured size or record limits.
* **Constant Footprint**: This strategy allows developers to process or record datasets that are significantly larger than the available workstation RAM (spanning terabytes of data) while maintaining a minimal and predictable memory footprint.

## The Writing Workflow

The **Writing Workflow** in Mosaico is designed for high-throughput data ingestion, ensuring that your application remains responsive even when streaming high-bandwidth sensor data like 4K video or high-frequency IMU telemetry.

The architecture is built around a **"Multi-Lane"** approach, where each sensor stream operates in its own isolated lane with dedicated system resources.

### The Orchestrator: `SequenceWriter`

The `SequenceWriter` acts as the central controller for a recording session. It manages the high-level lifecycle of the data on the server and serves as the factory for individual sensor streams.

**Key Roles:**

* **Lifecycle Management**: It handles the transition of a sequence from `Pending` to `Finalized`. It ensures that a sequence is either successfully committed as immutable data or, in the event of a failure, cleaned up according to your configured `OnErrorPolicy`.
* **Resource Distribution**: The writer pulls network connections from the **Connection Pool** and background threads from the **Executor Pool**, assigning them to individual topics. This isolation prevents a slow network connection on one topic from bottlenecking others.
* **Context Safety**: To ensure data integrity, the `SequenceWriter` must be used within a Python `with` block. This guarantees that all buffers are flushed and the sequence is closed properly, even if your application crashes.

### The Data Engine: `TopicWriter`

Once a topic is created, a `TopicWriter` is spawned to handle the actual transmission of data for that specific stream. It abstracts the underlying networking protocols, allowing you to simply "push" Python objects while it handles the heavy lifting.

**Key Roles:**

* **Smart Buffering**: Instead of sending every single message over the network—which would be highly inefficient—the `TopicWriter` accumulates records in a memory buffer.
* **Automated Flushing**: The writer automatically triggers a "flush" to the server whenever the internal buffer exceeds your configured limits, such as a maximum byte size or a specific number of records.
* **Asynchronous Serialization**: For CPU-intensive data (like encoding images), the writer can offload the serialization process to background threads, ensuring your main application loop stays fast.

### Error Management

When recording data, the Mosaico SDK provides two distinct **Error Policies** to manage the lifecycle of a sequence if an exception occurs during the writing process. These policies are configured via the `WriterConfig` and determine whether Mosaico prioritizes **data integrity (clean state)** or **data recovery (partial state)**.

#### 1. `OnErrorPolicy.Delete` (The "Clean Slate" Policy)

This is the strictest policy, designed to prevent the platform from becoming cluttered with incomplete or corrupted datasets.

* **Behavior**: If an error occurs within the `SequenceWriter` context, the SDK sends an `ABORT` signal to the server.
* **Result**: The server immediately deletes the entire sequence and all associated topic data from storage.
* **Best For**: Automated testing, CI/CD pipelines, or scenarios where a partial log is useless for analysis.

#### 2. `OnErrorPolicy.Report` (The "Recovery" Policy)

This policy is designed for mission-critical recordings where even partial data is valuable for debugging or forensics.

* **Behavior**: If an error occurs, the SDK finalizes whatever data has successfully reached the server and sends a `NOTIFY_CREATE` signal with the error details.
* **Result**: The sequence is preserved on the platform but remains in an **"unlocked" state**. This state allows the data to be read but also permits manual deletion later, which is otherwise forbidden for finalized, healthy sequences.
* **Best For**: Field tests, long-running mission logs, or hardware-in-the-loop simulations where the root cause of a failure needs to be investigated using the data leading up to the crash.

### Example: Writing Data

This example demonstrates the standard workflow: creating a sequence, initializing topic writers for different sensors, and pushing data.

```python
from mosaicolabs.models import Message
from mosaicolabs.models.sensors import IMU, GPS

# 1. Start the Sequence Orchestrator
with client.sequence_create("mission_log_042") as seq_writer:

    # 2. Create individual Topic Writers
    # Each writer gets its own assigned resources from the pools
    imu_writer = seq_writer.topic_create("sensors/imu", {}, IMU)
    gps_writer = seq_writer.topic_create("sensors/gps", {}, GPS)

    # 3. Push data - The SDK handles batching and background I/O
    # Usage Mode A: Component-based
    imu_writer.push(
        ontology_obj=IMU(acceleration=Vector3d(x=0, y=0, z=9.81)),
        message_timestamp_ns=1700000000000
    )

    # Usage Mode B: Full Message-based
    gps_msg = Message(timestamp_ns=1700000000100, data=GPS(...))
    gps_writer.push(message=gps_msg)

# Exiting the block automatically flushes all topic buffers 
# and finalizes the sequence on the server.

```

## The Reading Workflow

The **Reading Workflow** in Mosaico is architected to separate resource discovery from high-volume data transmission. This is achieved through two distinct layers: **Handlers**, which serve as metadata proxies, and **Streamers**, which act as the high-performance data engines.

### Handlers: The Catalog Layer

Handlers are lightweight objects that represent a server-side resource. Their primary role is to provide immediate access to system information and user-defined metadata **without downloading the actual sensor data**. They act as the "Catalog" layer of the SDK, allowing you to inspect the contents of the platform before committing to a high-bandwidth data stream.

Mosaico provides two specialized handler types:

* **`SequenceHandler`**: Represents a complete recording session. It provides a holistic view, allowing you to inspect all available topic names, global sequence metadata, and the overall temporal bounds (earliest and latest timestamps) of the session.
* **`TopicHandler`**: Represents a specific data channel within a sequence (e.g., a single IMU or Camera). It provides granular system info, such as the specific ontology model used and the data volume of that individual stream.

Both handlers serve as **factories**; once you have identified the resource you need, the handler is used to spawn the appropriate Streamer to begin data consumption.

### Streamers: The Data Engines

Streamers are the active components that manage the physical data exchange between the server and your application. They handle the complexities of network buffering, batch management, and the de-serialization of raw bytes into Mosaico `Message` objects.

#### `SequenceDataStreamer` (Unified Replay)

The `SequenceDataStreamer` is designed for sensor fusion and full-system replay. It performs a **K-Way Merge Sort** by monitoring the timestamps across multiple requested topics simultaneously. This ensures that as you iterate, messages are yielded in strict chronological order, regardless of the differing frequencies of individual sensors.

#### `TopicDataStreamer` (Targeted Access)

The `TopicDataStreamer` provides a direct, high-throughput channel to a single data resource. By bypassing the synchronization logic required for merging multiple topics, it offers the lowest possible overhead for tasks that only require a single data stream, such as training a model on isolated camera frames or IMU logs.

### Example: Unified Reading Workflow

This example demonstrates how to use a Sequence handler to inspect metadata before initiating the data stream.

```python
from mosaicolabs import MosaicoClient
from mosaicolabs.models.sensors import GPS

client = MosaicoClient.connect("localhost", 6726)

# Use a Handler to inspect the catalog
seq_handler = client.sequence_handler("mission_alpha")
print(f"Sequence: {seq_handler.name}")
# Inspect the stored topics
print(f"\t| Topics: {seq_handler.topics}")
# Inspect the stored user metadata
print(f"\t| Metadata: {seq_handler.user_metadata}")
# Inspect the timestamps spanned by the data-stream (without downloading data)
print(f"\t| Timestamp span: {seq_handler.timestamp_ns_min} - {seq_handler.timestamp_ns_max}")
# Inspect the system level info
print(f"\t| Created {seq_handler.sequence_info.created_datetime}")
print(f"\t| Size (MB) {seq_handler.sequence_info.total_size_bytes/(1024*1024)}")


# Start a Unified Stream (K-Way Merge) for multi-sensor replay
# We only want GPS and IMU data for this synchronized analysis
streamer = seq_handler.get_data_streamer(topics=["/gps", "/imu"])

# Peek at the start time
print(f"Recording starts at: {streamer.next_timestamp()}")

for topic, msg in streamer:
    # Processes GPS and IMU in perfect chronological order
    print(f"[{topic}] at {msg.timestamp_ns}: {type(msg.data).__name__}")
```

### Example: Targeted Reading Workflow

This example demonstrates how to use a Topic handler to inspect metadata before initiating the targeted data stream.

```python
# Alternatively, get a TopicHandler for a high-speed targeted task
client = MosaicoClient.connect("localhost", 6726)
# (e.g. training a model on just the front camera)
cam_handler = client.get_topic_handler("mission_alpha", "/cam_front")
# You can retrieve a topic handler from the parent SequenceHandler also:
# cam_handler = seq_handler.get_topic_handler("/cam_front")

print(f"Topic: {cam_handler.name}")
# Inspect the stored user metadata
print(f"\t| Camera metadata: {cam_handler.user_metadata}")
# Inspect the timestamps spanned by the data-stream (without downloading data)
print(f"\t| Timestamp span: {cam_handler.timestamp_ns_min} - {cam_handler.timestamp_ns_max}")
# Inspect the system level info
print(f"\t| Created {cam_handler.topic_info.created_datetime}")
print(f"\t| Size (MB) {seq_handler.topic_info.total_size_bytes/(1024*1024)}")

cam_stream = cam_handler.get_data_streamer()
# Direct, low-overhead loop
for frame_msg in cam_stream:
    process_frame(frame_msg.get_data(Image))

client.close()
```

## Quick Reference

### Class `SequenceWriter`

| Method | Description |
| --- | --- |
| **`topic_create()`** | Registers a new topic and returns a `TopicWriter`. |
| **`close()`** | Finalizes the sequence and marks it as immutable on the server. |
| **`sequence_status()`** | Returns the current state (e.g., `Pending`, `Finalized`). |
| **`list_topics()`** | Returns all active topics currently being managed. |
| **`get_topic()`** | Returns a `TopicWriter` instance, if it exists. |
| **`topic_exists()`** | Checks if a local `TopicWriter` exists for that topic. |

### Class `TopicWriter`

| Method | Description |
| --- | --- |
| **`push()`** | Adds a new record to the internal buffer for transmission. |
| **`finalize()`** | Flushes remaining data and closes the specific data stream. |
| **`finalized()`** | Returns True if the writer stream has been closed. |

### Class: `SequenceHandler`

| Attribute/Method | Type | Description |
| :--- | :--- | :--- |
| **`name`** | Property | Returns the unique sequence identifier. |
| **`topics`** | Property | List of all available topic names in the sequence. |
| **`user_metadata`** | Property | Dictionary of tags attached during sequence creation. |
| **`sequence_info`** | Property | System model containing size, date, and storage stats. |
| **`timestamp_ns_min`** | Property | Return the lowest timestamp in nanoseconds, among all the topics. |
| **`timestamp_ns_max`** | Property | Return the highest timestamp in nanoseconds, among all the topics. |
| **`get_data_streamer()`**| Method | Creates a unified, time-synchronized data stream. |
| **`get_topic_handler()`** | Method | Returns a `TopicHandler` for a specific child topic. |

### Class: `TopicHandler`

| Attribute/Method | Type | Description |
| :--- | :--- | :--- |
| **`name`** | Property | Returns the unique topic identifier. |
| **`user_metadata`** | Property | Dictionary of tags specific to this single topic. |
| **`topic_info`** | Property | System model containing the ontology type and volume size. |
| **`timestamp_ns_min`** | Property | Return the lowest timestamp in nanoseconds, among all the topics. |
| **`timestamp_ns_max`** | Property | Return the highest timestamp in nanoseconds, among all the topics. |
| **`get_data_streamer()`**| Method | Creates a direct stream for this topic's data. |
| **`close()`**| Method | Closes the data streamer if active. |

### Class `SequenceDataStreamer`

| Method | Returns | Description |
| :--- | :--- | :--- |
| **`next()`** | `(topic, Message)` | Retrieves the next time-ordered record across all topics. |
| **`next_timestamp()`** | `float` | **Look-ahead**: Peeks at the next available time without consuming it. |
| **`close()`** | `None` | Shuts down the underlying network connections for all topics. |

### Class `TopicDataStreamer`

| Method | Returns | Description |
| :--- | :--- | :--- |
| **`next()`** | `Message` | Advances the stream and returns the next data object. |
| **`next_timestamp()`** | `float` | **Look-ahead**: Peeks at the next message's time. |
| **`name()`** | `str` | Returns the canonical name of the stream (e.g., `/sensors/imu`). |

