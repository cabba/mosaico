---
title: Reading & Writing Data
description: Handlers, Writers, and Streamers.
---

The SDK separates concerns into **Writers** (for ingestion) and **Handlers** (for retrieval), optimizing each for its specific traffic pattern.

## Writing Data

Ingestion is managed by the `SequenceWriter`. It enforces a strict lifecycle (Creation  Upload  Finalization) to maintain data consistency. You must create a `SequenceWriter` within a context block; exiting the block triggers the final commit that locks the sequence on the server.

```python
from mosaicolabs.models.sensors import GPS

# Start a new recording session
with client.sequence_create("drive_log_01") as seq_writer:
    
    # Register a topic for GPS data
    gps_writer = seq_writer.topic_create(
        topic_name="gps/front",
        metadata={"sensor_id": "A100"},
        ontology_type=GPS
    )
    
    # Push data points
    gps_writer.push(message=my_gps_message)

```

## Reading Data

The SDK offers two distinct strategies for consuming data, depending on whether you need a holistic view or targeted access.

### Unified Sequence Stream

The `SequenceHandler` provides a **Time-Synchronized** view of the entire recording. Its streamer performs a client-side **K-Way Merge Sort**, reading from all topics simultaneously and yielding messages in strict chronological order. This is essential for sensor fusion or system replay.

```python
handler = client.sequence_handler("drive_log_01")
streamer = handler.get_data_streamer()

for topic, message in streamer:
    # Process messages in order of occurrence
    print(f"[{message.timestamp}] {topic}: {message.ontology_type()}")

```

### Targeted Topic Stream

If you only need data from a single sensor (e.g., for training a model on just IMU data), use the `TopicHandler`. This bypasses the synchronization overhead and opens a direct, high-throughput channel to that specific resource.

```python
topic_h = client.topic_handler("drive_log_01", "gps/front")
# Stream only GPS data
for message in topic_h.get_data_streamer():
    print(message.get_data(GPS).position.x)

```
