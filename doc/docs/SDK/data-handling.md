---
title: Writing & Reading Data
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

1. The metadata fields will be queryable via the [`Query` mechanism](./query.md). The mechanism allows creating queries like: `Sequence.Q.user_metadata["vehicle.software_stack.planning"].match("plan-4.")`

#### Quick Reference
| Method | Return | Description |
| :--- | :--- | :--- |
| **`topic_create(topic_name,metadata,ontology_type)`** | `Optional[TopicWriter]` | Registers a new topic and returns a `TopicWriter`. |
| **`get_topic(topic_name)`** | `Optional[TopicWriter]` | Returns a `TopicWriter` instance, if it exists. |
| **`topic_exists(topic_name)`** | `bool` | Checks if a local `TopicWriter` exists for that topic. |
| **`close()`** | `None` | Finalizes the sequence and marks it as immutable on the server. |
| **`sequence_status()`** | `SequenceStatus` | Returns the current state (e.g., `Pending`, `Finalized`). |
| **`list_topics()`** | `List[str]` | Returns all active topics currently being managed. |

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


## The Reading Workflow

The **Reading Workflow** in Mosaico is architected to separate resource discovery from high-volume data transmission. This is achieved through two distinct layers: **Handlers**, which serve as metadata proxies, and **Streamers**, which act as the high-performance data engines.

### Handlers: The Catalog Layer

Handlers are lightweight objects that represent a server-side resource. Their primary role is to provide immediate access to system information and user-defined metadata **without downloading the actual sensor data**. They act as the "Catalog" layer of the SDK, allowing you to inspect the contents of the platform before committing to a high-bandwidth data stream.

Mosaico provides two specialized handler types: `SequenceHandler` and `TopicHandler`.

#### `SequenceHandler`
Represents a complete recording session. It provides a holistic view, allowing you to inspect all available topic names, global sequence metadata, and the overall temporal bounds (earliest and latest timestamps) of the session.

This example demonstrates how to use a Sequence handler to inspect metadata.

```python
import sys
from mosaicolabs import MosaicoClient

with MosaicoClient.connect("localhost", 6726) as client:
    # Use a Handler to inspect the catalog
    seq_handler = client.sequence_handler("mission_alpha")
    if not seq_handler:
        print("Sequence not found.")
        sys.exit(1)  # early exit 
        
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
```

#### Quick Reference

| Attribute/Method | Type/Return | Description |
| :--- | :--- | :--- |
| **`name`** | `str` | Returns the unique sequence identifier. |
| **`topics`** | `List[str]` | List of all available topic names in the sequence. |
| **`user_metadata`** | `Dict[str, Any]` | Dictionary of tags attached during sequence creation. |
| **`sequence_info`** | `Sequence` | System model containing size, date, and storage stats. |
| **`timestamp_ns_min`** | `Optional[int]`  | Return the lowest timestamp in nanoseconds, among all the topics. |
| **`timestamp_ns_max`** | `Optional[int]` | Return the highest timestamp in nanoseconds, among all the topics. |
| **`get_topic_handler()`** | `TopicHandler` | Returns a `TopicHandler` for a specific child topic. |
| **`get_data_streamer(topics,start_timestamp_ns,end_timestamp_ns)`**| `SequenceDataStreamer` | Creates a unified, time-synchronized data stream. The method takes optional arguments to filter the interested topics and time bounds for limiting the stream to a specific window. |
| **`close()`**| `None` | Closes the data streamer if active. |

#### `TopicHandler`
Represents a specific data channel within a sequence (e.g., a single IMU or Camera). It provides granular system info, such as the specific ontology model used and the data volume of that individual stream.

This example demonstrates how to use a Topic handler to inspect metadata.

```python
import sys
from mosaicolabs import MosaicoClient

with MosaicoClient.connect("localhost", 6726) as client:
    # Use a Handler to inspect the catalog
    top_handler = client.topic_handler("mission_alpha", "/front/imu")
    # Note that the same handler can be retrieve via the SequenceHandler of the parent sequence:
    # seq_handler = client.sequence_handler("mission_alpha")
    # top_handler = seq_handler.get_topic_handler("/front/imu")
    if not top_handler:
        print("Sequence or Topic not found.")
        sys.exit(1)  # early exit 

    print(f"Sequence:Topic: {top_handler.sequence_name}:{top_handler.name}")
    # Inspect the stored user metadata
    print(f"\t| Metadata: {top_handler.user_metadata}")
    # Inspect the timestamps spanned by the topic data-stream (without downloading data)
    print(f"\t| Timestamp span: {top_handler.timestamp_ns_min} - {top_handler.timestamp_ns_max}")
    # Inspect the system level info
    print(f"\t| Created {top_handler.topic_info.created_datetime}")
    print(f"\t| Size (MB) {top_handler.topic_info.total_size_bytes/(1024*1024)}")
```
#### Quick Reference

| Attribute/Method | Type/Return | Description |
| :--- | :--- | :--- |
| **`name`** | `str` | Returns the unique topic identifier. |
| **`sequence_name`** | `str` | Returns the unique parent sequence identifier. |
| **`user_metadata`** | `Dict[str,Any]` | Dictionary of tags specific to this single topic. |
| **`topic_info`** | `Topic` | System model containing the ontology type and volume size. |
| **`timestamp_ns_min`** | `Optional[int]` | Return the lowest timestamp in nanoseconds of this topic. |
| **`timestamp_ns_max`** | `Optional[int]` | Return the highest timestamp in nanoseconds of this topic. |
| **`get_data_streamer(start_timestamp_ns,ebd_timestamp_ns)`**| `TopicDataStreamer` | Creates a direct stream for this topic's data. The method takes optional time bounds for limiting the stream to a specific window.|
| **`close()`**| `None` | Closes the data streamer if active. |


### Streamers: The Data Engines
Both handlers serve as **factories**; once you have identified the resource you need, the handler is used to spawn the appropriate Streamer to begin data consumption.
Streamers are the active components that manage the physical data exchange between the server and your application. They handle the complexities of network buffering, batch management, and the de-serialization of raw bytes into Mosaico `Message` objects.

#### `SequenceDataStreamer` (Unified Replay)

The **`SequenceDataStreamer`** is a unified engine designed specifically for sensor fusion and full-system replay. It allows you to consume multiple data streams as if they were a single, coherent timeline.

To achieve this, the streamer employs the following technical mechanisms:

* **K-Way Merge Sorting**: The streamer monitors the timestamps across all requested topics simultaneously. On every iteration, it "peeks" at the next available message from each topic and yields the one with the lowest timestamp.
* **Strict Chronological Order**: This sorting ensures that messages are delivered in exact acquisition order, effectively normalizing topics that may operate at vastly different frequencies (e.g., high-rate IMU vs. low-rate GPS).
* **Temporal Slicing**: You can request a "windowed" extraction by specifying `start_timestamp_ns` and `end_timestamp_ns`. This is highly efficient as it avoids downloading the entire sequence, focusing only on the specific event or time range of interest.
* **Smart Buffering**: To maintain memory efficiency, the streamer retrieves data in memory-limited batches. As you iterate, processed batches are discarded and replaced with new data from the server, allowing you to stream sequences that exceed your available RAM.

This example demonstrates how to initiate and use the Sequence data stream.

```python
import sys
from mosaicolabs import MosaicoClient 

with MosaicoClient.connect("localhost", 6726) as client:
    # Use a Handler to inspect the catalog
    seq_handler = client.sequence_handler("mission_alpha")
    if not seq_handler:
        print("Sequence not found.")
        sys.exit(1)  # early exit 

    # Start a Unified Stream (K-Way Merge) for multi-sensor replay
    # We only want GPS and IMU data for this synchronized analysis
    streamer = seq_handler.get_data_streamer(
        topics=["/gps", "/imu"], # Optionally filter topics
        # Optionally set the time window to extract
        start_timestamp_ns=1738508778000000000,
        end_timestamp_ns=1738509618000000000
    )

    # Peek at the start time
    print(f"Recording starts at: {streamer.next_timestamp()}")

    for topic, msg in streamer:
        # Processes GPS and IMU in perfect chronological order
        print(f"[{topic}] at {msg.timestamp_ns}: {type(msg.data).__name__}")
```

#### Quick Reference
| Method | Return | Description |
| :--- | :--- | :--- |
| **`next()`** | `(topic, Message)` | Retrieves the next time-ordered record across all topics. |
| **`next_timestamp()`** | `float` | **Look-ahead**: Peeks at the next available time without consuming it. |
| **`close()`** | `None` | Shuts down the underlying network connections for all topics. |

#### A more advanced pattern

When consuming unified streams via the `SequenceDataStreamer`, messages from diverse sensors arrive in a single chronological timeline.
Because the specific data type of the next message is polymorphic, relying on extensive `if/elif` chains to inspect every incoming packet is brittle and difficult to maintain.

For sophisticated applications, we recommend the **Registry Pattern** (or Type-Based Dispatcher).
This architecture decouples the stream consumption loop from specific business logic by registering dedicated processing functions for distinct **Ontology classes**.

* **Decoupled Logic**: Your main loop focuses exclusively on data movement and orchestration, while specific handler functions focus on data interpretation.
* **Modular Extensibility**: Adding support for a new sensor type (e.g., Lidar) simply requires defining a new decorated function; the core consumption loop remains unchanged.
* **Dynamic Resolution**: The system utilizes `message.ontology_type()` to resolve the correct processing logic at runtime, ensuring type safety and highly maintainable code.


```python
from typing import Callable, Dict, Type
from mosaicolabs.models import Serializable, Message
from mosaicolabs.models.sensors import GPS
# Example of a user-defined ontology
from my_project.ontology import Temperature 

# --- Registry Setup ---
# Maps Ontology Classes to their respective handler functions
_processor_registry: Dict[Type[Serializable], Callable] = {}

def register_processor(ontology_class: Type[Serializable]):
    """Decorator to register a function as the processor for an Ontology Class."""
    def decorator(func: Callable):
        _processor_registry[ontology_class] = func
        return func
    return decorator

# --- Define Granular Handlers ---

@register_processor(Temperature)
def process_temperature(message: Message, topic_name: str):
    """Business logic for Temperature data."""
    temp_data = message.get_data(Temperature)
    print(f"[{topic_name}] Temperature: {temp_data.value}°C")
    # Do something with this data

@register_processor(GPS)
def process_gps(message: Message, topic_name: str):
    """Business logic for GPS data."""
    gps_data = message.get_data(GPS)
    print(f"[{topic_name}] Fix: {gps_data.position.x}, {gps_data.position.y}")
    # Do something with this data

# --- The Consumption Loop ---
with client.sequence_handler("drive_session_01") as seq_handler:
    # SequenceDataStreamer handles the K-Way Merge Sort automatically
    streamer = seq_handler.get_data_streamer()

    for topic_name, message in streamer:
        # Dynamically dispatch based on the ontology type
        processor = _processor_registry.get(message.ontology_type())
        
        if processor:
            processor(message, topic_name)
        else:
            # Handle unknown types or log warnings for unregistered ontologies
            pass
```


#### `TopicDataStreamer` (Targeted Access)

The **`TopicDataStreamer`** provides a dedicated, high-throughput channel for interacting with a single data resource. By bypassing the complex synchronization logic required for merging multiple topics, it offers the lowest possible overhead for tasks requiring isolated data streams, such as training models on specific camera frames or IMU logs.

To ensure efficiency, the streamer supports the following features:

* **Temporal Slicing**: Much like the `SequenceDataStreamer`, you can extract data in a time-windowed fashion by specifying `start_timestamp_ns` and `end_timestamp_ns`. This ensures that only the relevant portion of the stream is retrieved rather than the entire dataset.
* **Smart Buffering**: Data is not downloaded all at once; instead, the SDK retrieves information in memory-limited batches, substituting old data with new batches as you iterate to maintain a constant, minimal memory footprint.

This example demonstrates how to initiate and use the Topic data stream.

```python
import sys
from mosaicolabs import MosaicoClient, IMU

with MosaicoClient.connect("localhost", 6726) as client:
    # Retrieve the topic handler using (e.g.) MosaicoClient
    top_handler = client.topic_handler("mission_alpha", "/front/imu")
    if not top_handler:
        print("Sequence or Topic not found.")
        sys.exit(1)  # early exit 

    # Start a Targeted Stream for single-sensor replay
    imu_stream = top_handler.get_data_streamer(
        # Optionally set the time window to extract
        start_timestamp_ns=1738508778000000000,
        end_timestamp_ns=1738509618000000000
    )

    # Peek at the start time
    print(f"Recording starts at: {streamer.next_timestamp()}")

    # Direct, low-overhead loop
    for imu_msg in imu_stream:
        process_sample(imu_msg.get_data(IMU)) # Some custom process function

    # Once done, close the reading channel (recommended)
    top_handler.close()
```

#### Quick Reference
| Method | Return | Description |
| :--- | :--- | :--- |
| **`next()`** | `Message` | Advances the stream and returns the next data object. |
| **`next_timestamp()`** | `float` | **Look-ahead**: Peeks at the next message's time. |
| **`name()`** | `str` | Returns the canonical name of the stream (e.g., `/sensors/imu`). |
