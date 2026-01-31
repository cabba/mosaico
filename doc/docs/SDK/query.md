---
title: Query Catalogs
description: The Query mechanism
---

The **Query Module** provides a high-performance, fluent interface for discovering and filtering data within the Mosaico Data Platform. 
It is designed to move beyond simple keyword searches, allowing you to perform deep, semantic queries across metadata, system catalogs, and the physical content of sensor streams.

## The Query Philosophy

Traditional data filtering often suffers from the "stringly-typed" problem, where developers must manually type complex dictionary keys that are prone to errors.
Mosaico replaces this with a **Fluent Interface** powered by a unique **Query Proxy (`.Q`)** mechanism.

### The `.Q` Proxy Mechanism

Every data model in the Mosaico Ontology is automatically injected with a static `.Q` attribute during class initialization.

* **Intelligent Mapping**: During initialization, the system inspects the sensor's schema and generates a dictionary mapping specific field paths to composed *queryable* objects.
* **Type-Aware Operators**: The proxy understands the data type of each field and only exposes valid operators. For example, it provides `.gt()` (greater than) for numeric fields but `.match()` for string-based fields.
* **Intent Generation**: Invoking an operator method (e.g., `.gt(15.0)`) generates a `QueryExpression` object. This object encapsulates your search intent, which is subsequently serialized into the JSON format required by the platform.

## Query Layers

Mosaico organizes data into three distinct architectural layers, each with its own specialized Query Builder:

1. **Sequence Layer (`QuerySequence`)**: Filters recordings based on high-level session metadata, such as the sequence name or the time it was created.
2. **Topic Layer (`QueryTopic`)**: Targets specific data channels within a sequence. You can search for topics by name pattern or by their specific Ontology type (e.g., "Find all GPS topics").
3. **Ontology Catalog Layer (`QueryOntologyCatalog`)**: The deepest layer of discovery. It allows you to search the **actual time-series content** of the sensors (e.g., "Find events where `acceleration.z` exceeded a specific value").

The Mosaico Query Module offers two distinct paths for defining filters, both of which support **method chaining** to compose multiple criteria into a single query using a logical **AND**.

### A. Convenience Methods

The query layers provide high-level helpers (`with_<attribute>`), built directly into the query builder classes and designed for ease of use.
They allow you to filter data without deep knowledge of the internal model schema. 
The builder automatically selects the appropriate field and operator (such as exact match vs. substring pattern) based on the method used.

```python
from mosaicolabs import QuerySequence

# Filter by name pattern AND a specific creation time window
QuerySequence()
    .with_name_match("test_drive")
    .with_created_timestamp(start=t1, end=t2)

```
* **Best For**: Standard system-level fields like Names and Timestamps.

### B. The Generic Expression Method

The `with_expression()` method accepts raw **Query Expressions** generated through the `.Q` proxy. 
This provides full access to every supported operator (`.gt()`, `.lt()`, `.between()`, etc.) for specific fields.

```python
from mosaicolabs import QueryOntologyCatalog, IMU

# Constructor Initialization: Compact and readable
QueryOntologyCatalog(
    IMU.Q.acceleration.x.gt(5.0),
    IMU.Q.header.stamp.sec.gt(1700134567),
    IMU.Q.header.stamp.nanosec.between([123456, 789123])
)

```

* **Best For**: Accessing specific Ontology data fields (e.g., acceleration, position, etc.) and custom `user_metadata`.
* **Metadata Querying**: For `Sequence` and `Topic` layers, `with_expression()` is used specifically (**and only**) for the `user_metadata` field via the `.Q` proxy.
    Metadata querying is made via bracket notation (`[]`) for keys and dot notation (`.`) to traverse nested dictionaries;
    being a generic JSON-like data struct, the `user_metadata` field supports all available operators. 

    ```python
    from mosaicolabs import Sequence, Topic

    Sequence.Q.user_metadata['driver'].match('Mark')
    # Dot notation for nested fields
    Sequence.Q.user_metadata['environment.visibility'].lt(50)

    Topic.Q.user_metadata['firmware_version'].eq("v0.1.4")
    ```

## Query Execution & The Response Model

Queries are executed via the `MosaicoClient.query()` method. When multiple builders are provided, they are combined with a logical **AND**.

### The Response Hierarchy

Execution returns a `QueryResponse` object, which behaves like a standard Python list containing `QueryResponseItem` objects.

| Class | Description |
| --- | --- |
| **`QueryResponseItem`** | Groups all matches belonging to the same **Sequence**. |
| **`QueryResponseItemTopic`** | Represents a specific **Topic** where matches were found. It includes the normalized topic path and the optional `timestamp_range` (the first and last occurrence of the condition). |

```python
from mosaicolabs import MosaicoClient, QueryOntologyCatalog, IMU

with MosaicoClient.connect("localhost", 6726) as client:
    # Find specific events where the robot experienced a hard impact (z-axis acceleration > 15 m/s^2)
    impact_query = QueryOntologyCatalog(
        IMU.Q.acceleration.z.gt(15.0),
        include_timestamp_range=True
    )

    results = client.query(impact_query)

    for item in results:
        print(f"Sequence: {item.sequence.name}")
        for topic in item.topics:
            print(f"  - Match in: {topic.name} starting at {topic.timestamp_range.start}")
```

### Restricted Queries (Chaining)
The `QueryResponse` class enables a powerful mechanism for **iterative search refinement** by allowing you to convert your current results back into a new query builder.
This approach is essential for resolving complex, multi-modal dependencies where a single monolithic query would be logically ambiguous or technically impossible.

| Method | Return Type | Description |
| --- | --- | --- |
| **`to_query_sequence()`** | `QuerySequence` | Returns a query builder pre-filtered to include only the **sequences** present in the response. |
| **`to_query_topic()`** | `QueryTopic` | Returns a query builder pre-filtered to include only the specific **topics** identified in the response. |

When you invoke these factory methods, the SDK generates a new query expression containing an explicit `$in` filter populated with the identifiers held in the current response. This effectively **"locks" the search domain**, allowing you to apply new criteria to a restricted subset of your data without re-scanning the entire platform catalog.


#### When Chaining is Necessary

In the Mosaico Data Platform, a single `client.query()` call uses logical **AND** to find individual *data streams* (topics) that satisfy **all conditions simultaneously**. 
Since a single topic cannot physically be two different sensor types at once (e.g., both a `GPS` and a `String` log), a monolithic query searching for both would yield zero results.

```python
# AMBIGUOUS: This looks for ONE topic that is BOTH GPS and String
response = client.query(
    QueryOntologyCatalog(GPS.Q.status.status.eq(DGPS_FIX)),
    QueryOntologyCatalog(String.Q.data.match("[ERR]")),
    QueryTopic().with_name("/localization/log_string")
)

```
Instead, by chaining, you decouple the criteria into logical stages:

1. **Broad Search:** Identify sequences containing a high-precision GPS fix.
2. **Locked Refinement:** Within *only* those valid sequences, search for a specific error pattern in the localization logs.

```python
# 1. Initial Query: Find sequences where GPS reached a high-precision state
initial_response = client.query(
    QueryOntologyCatalog(GPS.Q.status.status.eq(DGPS_FIX))
)

# 2. Refinement: "Lock" the scope to the sequences identified above
if not initial_response.is_empty():
    refined_query = initial_response.to_query_sequence()

    # 3. Final Query: Search for specific error patterns within that restricted scope
    final_response = client.query(
        refined_query,                                         # The restricted domain
        QueryTopic().with_name("/localization/log_string"),    # Target topic
        QueryOntologyCatalog(String.Q.data.match("[ERR]"))     # Data content filter
    )

```

## Constraints & Limitations

While fully functional, the current implementation (v0.x) has a **Single Occurrence Constraint**.

* **Constraint**: A specific data field path may appear **only once** within a single query builder instance. You cannot chain two separate conditions on the same field (e.g., `.gt(0.5)` and `.lt(1.0)`).
    ```python
    # INVALID: The same field (acceleration.x) is used twice in the constructor
    QueryOntologyCatalog() \
        .with_expression(IMU.Q.acceleration.x.gt(0.5))
        .with_expression(IMU.Q.acceleration.x.lt(1.0)) # <- Duplicate field path

    ```
* **Solution**: Use the built-in **`.between([min, max])`** operator to perform range filtering on a single field path.
* **Note**: You can still query multiple *different* fields from the same sensor model (e.g., `acceleration.x` and `acceleration.y`) in one builder.
    ```python
    # VALID: Each expression targets a unique field path
    QueryOntologyCatalog(
        IMU.Q.acceleration.x.gt(0.5),              # Unique field
        IMU.Q.acceleration.y.lt(1.0),              # Unique field
        IMU.Q.angular_velocity.x.between([0, 1]),   # Correct way to do ranges
        include_timestamp_range=True
    )

    ```

## Quick Reference

### Builder Methods

| Class | Methods | Target Resource |
| --- | --- | --- |
| **`QuerySequence`** | `with_name()`, `with_name_match()`, `with_created_timestamp()`, `with_expression()` | Session Metadata |
| **`QueryTopic`** | `with_name()`, `with_name_match()`, `with_ontology_tag()`, `with_created_timestamp()`, `with_expression()` | Topic Metadata |
| **`QueryOntologyCatalog`** | `with_data_timestamp()`, `with_message_timestamp()`, `with_expression()` | In-stream Sensor Data |

### Supported Operators by Type

| Data Type | Operators |
| --- | --- |
| **Numeric** | `.eq()`, `.neq()`, `.lt()`, `.leq()`, `.gt()`, `.geq()`, `.between()`, `.in_()` |
| **String** | `.eq()`, `.neq()`, `.match()` (substring), `.in_()` |
| **Boolean** | `.eq(True/False)` |
