<div align="right">
<picture>
<source media="(prefers-color-scheme: light)" srcset="../../logo/mono_black.svg">
<source media="(prefers-color-scheme: dark)" srcset="../../logo/mono_white.svg">
<img alt="Mosaico logo" src="../../logo/color_white.svg" height="30">
</picture>
</div>

# Data Handling

This guide details the core components for reading and writing data within the Mosaico library. The architecture is divided into two distinct workflows: [**Writing**](#writing-data) (creating new sequences and pushing data) and [**Handling/Reading**](#reading--handling-data) (inspecting existing sequences and streaming data back).

All interactions start from the `MosaicoClient` (see [Client Architecture](./communication.md) documentation), which acts as the factory for these components.

-----

## Architecture Overview

The library uses a hierarchical object model to manage data streams (see also [Core Concepts](../../CORE_CONCEPTS.md#topics-and-sequences)):

  * **Sequence:** The top-level container. It represents a recording session or a logical grouping of data streams.
  * **Topic:** A specific stream within a sequence (e.g., "gps\_sensor", "video\_front"). Each topic carries data of a specific **Ontology** type.

### Design Pattern

  * **Writers (`SequenceWriter`, `TopicWriter`):** Designed for high-throughput data ingestion. They utilize buffering, batching, and background threading to ensure the client application is not blocked by network I/O.
  * **Handlers (`SequenceHandler`, `TopicHandler`):** Lightweight proxies for server-side resources. They provide access to metadata and allow you to spawn "Streamers".
  * **Streamers (`SequenceDataStreamer`, `TopicDataStreamer`):** Iterators that pull data from the server. The `SequenceDataStreamer` performs a **K-Way Merge**, combining multiple topic streams into a single, time-ordered timeline.

-----

## Writing Data

Writing is performed inside a strict lifecycle managed by the `SequenceWriter`.

### Class: `SequenceWriter`

The `SequenceWriter` acts as the orchestrator. It handles the sequence lifecycle on the server (Pending $\rightarrow$ Finalized/Error), and creates child `TopicWriter`s.

#### Key Features

  * **Instantiation:** Is made by calling the method [`sequence_create(...)`](communication.md#api-reference) of a `MosaicoClient` instance.
  * **Context Manager Support:** Users **must** use the writer within a `with` statement. This guarantees that `finalize()` (or `abort()` on error) is called, ensuring data integrity. Instantiating a `SequenceWriter` outside a `with` block will result in a runtime error.
  * **Error Policies:** Configured via `WriterConfig`, the writer can either delete the entire sequence upon an error (`OnErrorPolicy.Delete`) or save the valid partial data (`OnErrorPolicy.Report`). In this latter case, the sequence and its resources will be kept on the data platform storage and databases, however the sequence will be marked as *unlocked*, meaning that it can be still removed in a second time.

#### API Reference

**Lifecycle & Topic Management**

  * **`topic_create(topic_name: str, metadata: dict[str, Any], ontology_type: Type[Serializable]) -> Optional[TopicWriter]`**
    Registers a new topic on the server and initializes a local writer for it. This method assigns resources (network connections and thread executors) from the client's pools to ensure parallel writing.

      * **`topic_name`**: The unique name for the topic within this sequence.
      * **`metadata`**: A dictionary of user-defined tags specific to this topic.
      * **`ontology_type`**: The class type of the data model (must be a subclass of `Serializable`).

  * **`close() -> None`**
    Explicitly finalizes the sequence. It sends the `SEQUENCE_FINALIZE` signal to the server, marking the data as immutable.

      * *Note*: This is automatically called when exiting the `with` block context.

  * **`sequence_status() -> SequenceStatus`**
    Returns the current state of the sequence (e.g., `Pending`, `Finalized`, `Error`).

  * **`topic_exists(topic_name: str) -> bool`**
    Checks if a local `TopicWriter` has already been created for the given name.

  * **`list_topics() -> list[str]`**
    Returns a list of names for all active topics currently managed by this writer.

  * **`get_topic(topic_name: str) -> Optional[TopicWriter]`**
    Retrieves the `TopicWriter` instance for a specific topic, if it exists.

-----

### Class: `TopicWriter`

The `TopicWriter` handles the actual data transmission for a single stream. It abstracts the underlying PyArrow Flight `DoPut` stream, handling buffering (batching) and serialization.

#### API Reference

**Data Ingestion**

  * **`push(message: Optional[Message] = None, message_timestamp_ns: Optional[int] = None, ontology_obj: Optional[Serializable] = None, ...) -> None`**
    Adds a new record to the internal write buffer. If the buffer exceeds the configured limits (`max_batch_size_bytes` or `max_batch_size_records`), it triggers a flush to the server.

    *Usage Mode A (Recommended):*

      * **`message`**: A complete `Message` object containing the data and timestamp.

    *Usage Mode B (Components):*

      * **`ontology_obj`**: The payload object (must match the topic's ontology type).
      * **`message_timestamp_ns`**: The timestamp of the record in nanoseconds.
      * **`message_header`** *(Optional)*: Additional header information.

**State Management**

  * **`finalize(with_error: bool = False) -> None`**
    Flushes any pending data in the buffer and closes the underlying Flight stream.
      * **`with_error`**: If `True`, indicates the stream is closing due to an exception. This may alter flushing behavior (e.g., to avoid sending corrupted partial batches).

      * *Note*: This is automatically called from the `SequenceWriter` instance when exiting the `with` block context.

#### Example Usage

```python
from mosaicolabs.models import Message
from mosaicolabs.models.data import Point3d # Standard ontologies
from mosaicolabs.models.sensors import GPS # Standard ontologies
from my_ontologies import Temperature # User defined ontologies

# Start the Sequence Context using the client factory method
with client.sequence_create("drive_session_01") as seq_writer:

    # Create Topic Writers
    gps_writer = seq_writer.topic_create(
        topic_name="gps/front",
        metadata={"sensor_id": "A100"},
        ontology_type=GPS
    )
    
    temp_writer = seq_writer.topic_create(
        topic_name="/cabin/temp", # The platform handles leading slashes automatically
        metadata={"unit": "celsius"},
        ontology_type=Temperature
    )

    # Push Data - Option A (Components)
    gps_writer.push(
        ontology_obj=GPS(position=Point3d(x=45.0, y=9.0, z=0)),
        message_timestamp_ns=1620000000000
    )

    # Push Data - Option B (Full Message)
    msg = Message(timestamp_ns=1620000000100, data=Temperature(value=22.5))
    temp_writer.push(message=msg)

# Exiting the block automatically finalizes and closes the sequence.
```

> [!NOTE] 
> **Topic Name Normalization**
>
> The Data Platform automatically sanitizes topic names. A leading slash (`/`) is optional during topic creation. However, to ensure consistency, the SDK normalizes all names to include a leading slash when retrieving data (e.g., both `gps/front` and `/gps/front` will be retrieved as `/gps/front`).


## Reading & Handling Data

To interact with data that has already been written, users can use *Handlers*, primarily obtained via the `MosaicoClient`.

### Class: `SequenceHandler`

This is the handler to an existing sequence. It allows you to inspect what topics exist, view metadata, and start reading the data.

#### API Reference

**Properties**

  * **`topics`**
    Returns a list of strings representing the names of all topics available in this sequence (names are normalized with leading `/`)
  * **`user_metadata`**
    Returns the dictionary of metadata attached to the sequence during creation.
  * **`name`**
    Returns the unique name of the sequence.
  * **`sequence_info`**
    Returns the full `Sequence` model object containing system info (size, creation date, etc.).

**Streamer Factories**

  * **`get_data_streamer(force_new_instance: bool = False) -> SequenceDataStreamer`**
    Creates and returns a `SequenceDataStreamer` initialized to read the **entire** sequence. By default, it caches the streamer instance.

      * **`force_new_instance`**: If `True`, closes any existing streamer and creates a fresh one (useful for restarting iteration).

  * **`get_topic_handler(topic_name: str, force_new_instance: bool = False) -> Optional[TopicHandler]`**
    Returns a `TopicHandler` for a specific child topic.

      * **`topic_name`**: The name of the topic to retrieve.
      * **`force_new_instance`**: If `True`, recreates the handler connection.

  * **`close() -> None`**
    Closes all cached topic handlers and active data streamers associated with this handler.

-----

### Class: `SequenceDataStreamer`

This is a unified iterator that connects to *all* topics in the sequence simultaneously, using a **K-Way Merge algorithm**. It actively maintains a connection to every topic, "peeking" at the next available timestamp for each. On every iteration, it yields the record with the lowest timestamp across all topics. This ensures a chronologically correct stream, regardless of the recording frequency of individual sensors.

#### API Reference

**Iteration**

  * **`next() -> Optional[tuple[str, Message]]`**
    Retrieves the next time-ordered record from the merged stream.

      * **Returns**: A tuple `(topic_name, message)` or `None` if the stream is exhausted.

  * **`next_timestamp() -> Optional[float]`**
    Peeks at the timestamp of the very next record in the merged timeline without consuming it. Useful for synchronizing external loops or checking stream progress.

  * **`close() -> None`**
    Closes the underlying Flight streams for all topics.

#### Example Usage

```python
# 1. Get the handler
seq_handler = client.sequence_handler("drive_session_01")
print(f"Reading sequence with topics: {seq_handler.topics}")

# 2. Get the unified streamer
streamer = seq_handler.get_data_streamer()

# 3. Iterate (chronological merge)
for topic_name, message in streamer:
    if topic_name == "gps":
        print(f"Position: {message.data.position.x}, {message.data.position.y}")
    elif topic_name == "cabin_temp":
        print(f"Temp: {message.data.value}")

# 4. Clean up
seq_handler.close()
```


### Recommended Pattern: Type-Based Dispatching

When consuming unified data streams, using the `SequenceDataStreamer`, messages from various topics arrive in chronological order, meaning the specific data type of the next message is not known in advance. Relying on extensive `if/elif` chains to inspect each message is often brittle and hard to maintain.

Instead, we recommend implementing a **Registry Pattern** (or Type-Based Dispatcher). This approach involves registering specific processing functions to handle distinct **Ontology classes**. When a message arrives, the system uses `message.ontology_type()` to dynamically dispatch the data to the correct handler. This efficiently decouples stream consumption from data processing, ensuring your application remains modular and easy to extend as new sensor types are introduced.

```python
from typing import Callable, Dict, Type
from mosaicolabs.models import Serializable, Message
from mosaicolabs.models.sensors import GPS
from my_ontologies import Temperature

# --- 1. Registry Setup ---

# A dictionary mapping Ontology Classes to their handler functions
_processor_registry: Dict[Type[Serializable], Callable] = {}

def register_processor(ontology_class: Type[Serializable]):
    """
    Decorator to register a function as the processor for a specific Ontology Class.
    """
    def decorator(func: Callable):
        _processor_registry[ontology_class] = func
        return func
    return decorator


# --- 2. Define Handlers for Specific Ontology Types ---

@register_processor(Temperature)
def process_temperature(message: Message, topic_name: str):
    """
    Business logic for Temperature data.
    """
    # ... processing logic here ...
    pass

@register_processor(GPS)
def process_gps(message: Message, topic_name: str):
    """
    Business logic for GPS data.
    """
    # ... processing logic here ...
    pass


# --- 3. Stream Consumption Loop ---

# Initialize the handler and streamer
seq_handler = client.sequence_handler("drive_session_01")
streamer = seq_handler.get_data_streamer()

print(f"Streaming sequence with topics: {seq_handler.topics}")

# Iterate through the chronological stream
for topic_name, message in streamer:
    # Dynamically look up the registered processor based on the message type
    processor = _processor_registry.get(message.ontology_type())
    
    # Dispatch or log missing handler
    if processor:
        processor(message, topic_name)
    else:
        # Optional: Handle unknown types silently or log a warning
        pass
```

### Class: `TopicHandler` & `TopicDataStreamer`

If data from a single specific topic is needed (and its timing relative to other topics is not important), then the `TopicHandler` can be used.

#### TopicHandler API Reference

  * **`user_metadata`**
    Returns the user dictionary associated with the topic.
  * **`topic_info`**
    Returns the full `Topic` data model (system info, schema, etc.).
  * **`get_data_streamer(force_new_instance: bool = False) -> Optional[TopicDataStreamer]`**
    Creates a `TopicDataStreamer` to read data strictly from this single topic endpoint.

#### TopicDataStreamer API Reference

  * **`next() -> Optional[Message]`**
    Returns the next `Message` object from the stream, or `None` if finished.
  * **`next_timestamp() -> Optional[float]`**
    Peeks at the timestamp of the next record without consuming it.
  * **`name() -> str`**
    Returns the topic name associated with this stream.
