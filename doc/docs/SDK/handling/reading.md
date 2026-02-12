---
title: The Reading Workflow
description: Handlers, Writers, and Streamers.
---

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
    if seq_handler:     
        print(f"Sequence: {seq_handler.name}")
        # Inspect the stored topics
        print(f"\t| Topics: {seq_handler.topics}")
        # Inspect the stored user metadata
        print(f"\t| Metadata: {seq_handler.user_metadata}")
        # Inspect the message timestamps spanned by the data-stream (without downloading data)
        print(f"\t| Timestamp span: {seq_handler.timestamp_ns_min} - {seq_handler.timestamp_ns_max}")
        # Inspect the system level info
        print(f"\t| Created {seq_handler.sequence_info.created_datetime}")
        print(f"\t| Size (MB) {seq_handler.sequence_info.total_size_bytes/(1024*1024)}")

        # Once done, close the reading channel (recommended)
        seq_handler.close()
```

#### Quick Reference
API Reference: [`mosaicolabs.handlers.SequenceHandler`][mosaicolabs.handlers.SequenceHandler].

| Properties | Type | Description |
| :--- | :--- | :--- |
| **[`name`][mosaicolabs.handlers.SequenceHandler.name]** | `str` | Returns the unique sequence identifier. |
| **[`topics`][mosaicolabs.handlers.SequenceHandler.topics]** | `List[str]` | List of all available topic names in the sequence. |
| **[`user_metadata`][mosaicolabs.handlers.SequenceHandler.user_metadata]** | `Dict[str, Any]` | Dictionary of tags attached during sequence creation. |
| **[`created_datetime`][mosaicolabs.handlers.SequenceHandler.created_datetime]** | `datetime` | The datetime when the sequence was created. |
| **[`is_locked`][mosaicolabs.handlers.SequenceHandler.is_locked]** | `bool` | Returns `True` if the sequence is locked (i.e. actively being written to), `False` otherwise. |
| **[`total_size_bytes`][mosaicolabs.handlers.SequenceHandler.total_size_bytes]** | `int` | The total physical storage footprint of the entity on the server in bytes. |
| **[`timestamp_ns_min`][mosaicolabs.handlers.SequenceHandler.timestamp_ns_min]** | `Optional[int]`  | Return the lowest timestamp in nanoseconds, among all the topics. |
| **[`timestamp_ns_max`][mosaicolabs.handlers.SequenceHandler.timestamp_ns_max]** | `Optional[int]` | Return the highest timestamp in nanoseconds, among all the topics. |

| Methods | Return Type | Description |
| :--- | :--- | :--- |
| **[`get_topic_handler(topic_name)`][mosaicolabs.handlers.SequenceHandler.get_topic_handler]** | `TopicHandler` | Returns a `TopicHandler` for a specific child topic. |
| **[`get_data_streamer(topics,start_timestamp_ns,end_timestamp_ns)`][mosaicolabs.handlers.SequenceHandler.get_data_streamer]**| `SequenceDataStreamer` | Creates a unified, time-synchronized data stream. The method takes optional arguments to filter the interested topics and time bounds for limiting the stream to a specific window. |
| **[`close()`][mosaicolabs.handlers.SequenceHandler.close]**| `None` | Closes the data streamer if active. |

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
    if top_handler:
        print(f"Sequence:Topic: {top_handler.sequence_name}:{top_handler.name}")
        # Inspect the stored user metadata
        print(f"\t| Metadata: {top_handler.user_metadata}")
        # Inspect the message timestamps spanned by the topic data-stream (without downloading data)
        print(f"\t| Timestamp span: {top_handler.timestamp_ns_min} - {top_handler.timestamp_ns_max}")
        # Inspect the system level info
        print(f"\t| Created {top_handler.topic_info.created_datetime}")
        print(f"\t| Size (MB) {top_handler.topic_info.total_size_bytes/(1024*1024)}")

        # Once done, close the reading channel (recommended)
        top_handler.close()
```
#### Quick Reference
API Reference: [`mosaicolabs.handlers.TopicHandler`][mosaicolabs.handlers.TopicHandler].

| Properties | Type | Description |
| :--- | :--- | :--- |
| **[`name`][mosaicolabs.handlers.TopicHandler.name]** | `str` | Returns the unique topic identifier. |
| **[`sequence_name`][mosaicolabs.handlers.TopicHandler.sequence_name]** | `str` | Returns the unique parent sequence identifier. |
| **[`user_metadata`][mosaicolabs.handlers.TopicHandler.user_metadata]** | `Dict[str,Any]` | Dictionary of tags specific to this single topic. |
| **[`created_datetime`][mosaicolabs.handlers.TopicHandler.created_datetime]** | `datetime` | The datetime when the topic was created. |
| **[`is_locked`][mosaicolabs.handlers.TopicHandler.is_locked]** | `bool` | Returns `True` if the resource is currently locked, `False` otherwise. |
| **[`chunks_number`][mosaicolabs.handlers.TopicHandler.chunks_number]** | `int` | The number of physical data chunks stored for this topic. |
| **[`ontology_tag`][mosaicolabs.handlers.TopicHandler.ontology_tag]** | `str` | The ontology type identifier. |
| **[`serialization_format`][mosaicolabs.handlers.TopicHandler.serialization_format]** | `str` | The format used to serialize the topic data. |
| **[`total_size_bytes`][mosaicolabs.handlers.TopicHandler.total_size_bytes]** | `int` | The total physical storage footprint of the entity on the server in bytes. |
| **[`timestamp_ns_min`][mosaicolabs.handlers.TopicHandler.timestamp_ns_min]** | `Optional[int]` | Return the lowest timestamp in nanoseconds of this topic. |
| **[`timestamp_ns_max`][mosaicolabs.handlers.TopicHandler.timestamp_ns_max]** | `Optional[int]` | Return the highest timestamp in nanoseconds of this topic. |

| Methods | Return Type | Description |
| :--- | :--- | :--- |
| **[`get_data_streamer(start_timestamp_ns,ebd_timestamp_ns)`][mosaicolabs.handlers.TopicHandler.get_data_streamer]**| `TopicDataStreamer` | Creates a direct stream for this topic's data. The method takes optional time bounds for limiting the stream to a specific window.|
| **[`close()`][mosaicolabs.handlers.TopicHandler.close]**| `None` | Closes the data streamer if active. |


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
    if seq_handler:
        # Start a Unified Stream (K-Way Merge) for multi-sensor replay
        # We only want GPS and IMU data for this synchronized analysis
        streamer = seq_handler.get_data_streamer(
            topics=["/gps", "/imu"], # Optionally filter topics
            # Optionally set the time window to extract
            start_timestamp_ns=1738508778000000000,
            end_timestamp_ns=1738509618000000000
        )

        # Check the start message timestamp
        print(f"Recording starts at: {streamer.next_timestamp()}")

        for topic, msg in streamer:
            # Processes GPS and IMU in perfect chronological order
            print(f"[{topic}] at {msg.timestamp_ns}: {type(msg.data).__name__}")

        # Once done, close the reading channel (recommended)
        seq_handler.close()
```

#### Quick Reference
API Reference: [`mosaicolabs.handlers.SequenceDataStreamer`][mosaicolabs.handlers.SequenceDataStreamer].

| Method | Return | Description |
| :--- | :--- | :--- |
| **[`next_timestamp()`][mosaicolabs.handlers.SequenceDataStreamer.next_timestamp]** | `Optional[int]` | **Look-ahead**: Peeks at the next available time without consuming it. |
| **[`close()`][mosaicolabs.handlers.SequenceDataStreamer.close]** | `None` | Shuts down the underlying network connections for all topics. |

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
seq_handler = client.sequence_handler("drive_session_01")
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

# Once done, close the reading channel (recommended)
seq_handler.close()
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
    if top_handler:
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
API Reference: [`mosaicolabs.handlers.TopicDataStreamer`][mosaicolabs.handlers.TopicDataStreamer].

| Method | Return | Description |
| :--- | :--- | :--- |
| **[`next_timestamp()`][mosaicolabs.handlers.TopicDataStreamer.next_timestamp]** | `Optional[int]` | **Look-ahead**: Peeks at the next message's time. |
| **[`name()`][mosaicolabs.handlers.TopicDataStreamer.name]** | `str` | Returns the canonical name of the stream (e.g., `/sensors/imu`). |
| **[`ontology_tag()`][mosaicolabs.handlers.TopicDataStreamer.ontology_tag]** | `str` | Returns the ontology tag associated with this streamer. |
| **[`close()`][mosaicolabs.handlers.TopicDataStreamer.close]** | `None` | Shuts down the underlying network connections for all topics. |

