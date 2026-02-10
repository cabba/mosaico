---
title: The Writing Workflow
description: Data Writers.
---

The **Writing Workflow** in Mosaico is designed for high-throughput data ingestion, ensuring that your application remains responsive even when streaming high-bandwidth sensor data like 4K video or high-frequency IMU telemetry.

The architecture is built around a **"Multi-Lane"** approach, where each sensor stream operates in its own isolated lane with dedicated system resources.

### The Orchestrator: `SequenceWriter`

The `SequenceWriter` acts as the central controller for a recording session. It manages the high-level lifecycle of the data on the server and serves as the factory for individual sensor streams.

**Key Roles:**

* **Lifecycle Management**: It handles the lifecycle of a new sequence and ensures that it is either successfully committed as immutable data or, in the event of a failure, cleaned up according to your configured `OnErrorPolicy`.
* **Resource Distribution**: The writer pulls network connections from the **Connection Pool** and background threads from the **Executor Pool**, assigning them to individual topics. This isolation prevents a slow network connection on one topic from bottlenecking others.
* **Context Safety**: To ensure data integrity, the `SequenceWriter` must be used within a Python `with` block. This guarantees that all buffers are flushed and the sequence is closed properly, even if your application crashes.

```python
from mosaicolabs import MosaicoClient, OnErrorPolicy

# Open the connection with the Mosaico Client
with MosaicoClient.connect("localhost", 6726) as client:
    # Start the Sequence Orchestrator
    with client.sequence_create(
        sequence_name="mission_log_042", 
        # Custom metadata for this data sequence.
        metadata={ # (1)!
            "vehicle": {
                "vehicle_id": "veh_sim_042",
                "powertrain": "EV",
                "sensor_rig_version": "v3.2.1",
                "software_stack": {
                    "perception": "perception-5.14.0",
                    "localization": "loc-2.9.3",
                    "planning": "plan-4.1.7",
                },
            },
            "driver": {
                "driver_id": "drv_sim_017",
                "role": "validation",
                "experience_level": "senior",
            },
            "location": {
                "city": "Milan",
                "country": "IT",
                "facility": "Downtown",
                "gps": {
                    "lat": 45.46481,
                    "lon": 9.19201,
                },
            },
        }
        on_error = OnErrorPolicy.Delete # Default
        ) as seq_writer:

        # `seq_writer` is the writing handler of the new 'mission_log_042' sequence
        # Data will be uploaded by spawning topic writers that will manage the actual data stream 
        # remote push... See below.

```

1. The metadata fields will be queryable via the [`Query` mechanism](../query.md). The mechanism allows creating queries like: `Sequence.Q.user_metadata["vehicle.software_stack.planning"].match("plan-4.")`

#### Quick Reference

API Reference: [`mosaicolabs.handlers.SequenceWriter`][mosaicolabs.handlers.SequenceWriter].

| Method | Return | Description |
| :--- | :--- | :--- |
| **`topic_create(topic_name, metadata, ontology_type)`** | [`Optional[TopicWriter]`][mosaicolabs.handlers.TopicWriter] | Registers a new topic and returns a `TopicWriter`. |
| **`get_topic_writer(topic_name)`** | [`Optional[TopicWriter]`][mosaicolabs.handlers.TopicWriter] | Returns a `TopicWriter` instance, if it exists. |
| **`topic_writer_exists(topic_name)`** | `bool` | Checks if a local `TopicWriter` exists for that topic. |
| **`sequence_status()`** | [`SequenceStatus`][mosaicolabs.enum.SequenceStatus] | Returns the current state (e.g., `Pending`, `Finalized`). |
| **`list_topic_writers()`** | `List[str]` | Returns all active topics currently being managed. |

### The Data Engine: `TopicWriter`

Once a topic is created, a `TopicWriter` is spawned to handle the actual transmission of data for that specific stream. It abstracts the underlying networking protocols, allowing you to simply "push" Python objects while it handles the heavy lifting.

**Key Roles:**

* **Smart Buffering**: Instead of sending every single message over the network—which would be highly inefficient—the `TopicWriter` accumulates records in a memory buffer.
* **Automated Flushing**: The writer automatically triggers a "flush" to the server whenever the internal buffer exceeds your configured limits, such as a maximum byte size or a specific number of records.
* **Asynchronous Serialization**: For CPU-intensive data (like encoding images), the writer can offload the serialization process to background threads, ensuring your main application loop stays fast.

```python
# Continues from the code above...

    # 👉 with client.sequence_create(...) as seq_writer:
        # Create individual Topic Writers
        # Each writer gets its own assigned resources from the pools
        imu_writer = seq_writer.topic_create(
            topic_name="sensors/imu", # The univocal topic name
            metadata={ # The topic/sensor custom metadata
                "vendor": "inertix-dynamics",
                "model": "ixd-f100",
                "firmware_version": "1.2.0",
                "serial_number": "IMUF-9A31D72X",
                "calibrated":"false",
            },
            ontology_type=IMU, # The ontology type stored in this topic
        )

        # Another individual topic writer for the GPS device
        gps_writer = seq_writer.topic_create(
            topic_name="sensors/gps", # The univocal topic name
            metadata={ # The topic/sensor custom metadata
                "role": "primary_gps",
                "vendor": "satnavics",
                "model": "snx-g500",
                "firmware_version": "3.2.0",
                "serial_number": "GPS-7C1F4A9B",            
                "interface": { # (1)!
                    "type": "UART",
                    "baudrate": 115200,
                    "protocol": "NMEA",
                },
            }, # The topic/sensor custom metadata
            ontology_type=GPS, # The ontology type stored in this topic
        )

        # Push data - The SDK handles batching and background I/O
        # Usage Mode A: Component-based
        imu_writer.push(
            ontology_obj=IMU(acceleration=Vector3d(x=0, y=0, z=9.81), ...),
            message_timestamp_ns=1700000000000
        )

        # Usage Mode B: Full Message-based
        gps_msg = Message(timestamp_ns=1700000000100, data=GPS(...))
        gps_writer.push(message=gps_msg)

# Exiting the block automatically flushes all topic buffers, finalizes the sequence on the server 
# and closes all connections and pools
```

1. The metadata fields will be queryable via the [`Query` mechanism](./query.md). The mechanism allows creating query expressions like: `Topic.Q.user_metadata["interface.type"].eq("UART")`.
    See also:
    * [`mosaicolabs.models.platform.Topic`][mosaicolabs.models.platform.Topic]
    * [`mosaicolabs.models.query.builders.QueryTopic`][mosaicolabs.models.query.builders.QueryTopic].

#### Quick Reference

API Reference: [`mosaicolabs.handlers.TopicWriter`][mosaicolabs.handlers.TopicWriter].

| Method | Description |
| --- | --- |
| **`push(message,message_timestamp_ns,message_header,ontology_obj)`** | Adds a new record to the internal buffer for transmission. The method can be called passing a pre-built `Message` object or passing distinct components (`ontology_obj`, `message_timestamp_ns`, `message_header`).|
| **`finalize()`** | Flushes remaining data and closes the specific data stream. |
| **`finalized()`** | Returns True if the writer stream has been closed. |


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

API Reference:[`mosaicolabs.enum.OnErrorPolicy`][mosaicolabs.enum.OnErrorPolicy]
