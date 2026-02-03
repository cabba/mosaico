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

The Query Proxy is the cornerstone of Mosaico's type-safe data discovery. Every data model in the Mosaico Ontology (e.g., `IMU`, `GPS`, `Image`) is automatically injected with a static `.Q` attribute during class initialization. This mechanism transforms static data structures into dynamic, fluent interfaces for constructing complex filters.

The proxy follows a three-step lifecycle to ensure that your queries are both semantically correct and high-performance:

1. **Intelligent Mapping**: During system initialization, the proxy inspects the sensor's schema recursively. It maps every nested field path (e.g., `"acceleration.x"`) to a dedicated *queryable* object, i.e. an object providing comparison operators and expression generation methods.
2. **Type-Aware Operators**: The proxy identifies the data type of each field (numeric, string, or boolean) and exposes only the operators valid for that type. This prevents logical errors, such as attempting a substring `.match()` on a numeric acceleration value.
3. **Intent Generation**: When you invoke an operator (e.g., `.gt(15.0)`), the proxy generates a `QueryExpression`. This object encapsulates your search intent and is serialized into an optimized JSON format for the platform to execute.

To understand how the proxy handles nested structures, inherited attributes, and data types, consider the `IMU` ontology class:

```python
class IMU(Serializable, HeaderMixin):
    acceleration: Vector3d      # Composed type: contains x, y, z
    angular_velocity: Vector3d  # Composed type: contains x, y, z
    orientation: Optional[Quaternion] = None # Composed type: contains x, y, z, w

```

The `.Q` proxy enables you to navigate the data exactly as it is defined in the model. By following the `IMU.Q` instruction, you can drill down through nested fields and inherited mixins using standard dot notation until you reach a base queryable type.

The proxy automatically flattens the hierarchy, including fields inherited from `HeaderMixin` (like `frame_id` and `stamp`), assigning the correct queryable type and operators to each leaf node:

| Proxy Field Path | Queryable Type | Supported Operators (Examples) |
| --- | --- | --- |
| **`IMU.Q.acceleration.x/y/z`** | **Numeric** | `.gt()`, `.lt()`, `.geq()`, `.leq()`, `.eq()`, `.between()`, `.in_()` |
| **`IMU.Q.angular_velocity.x/y/z`** | **Numeric** | *same as above* |
| **`IMU.Q.orientation.x/y/z/w`** | **Numeric** | *same as above* |
| **`IMU.Q.header.frame_id`** | **String** | `.eq()`, `.match()` |
| **`IMU.Q.header.stamp.sec`** | **Numeric** | `.gt()`, `.lt()`, `.geq()`, ... |
| **`IMU.Q.header.stamp.nanosec`** | **Numeric** | `.gt()`, `.lt()`, `.geq()`, ... |


### Supported vs. Unsupported Types

While the `.Q` proxy is highly versatile, it enforces specific rules on which data structures can be queried:

* **Supported Types**: The proxy resolves all simple (int, float, str, bool) or composed types (like `Vector3d` or `Quaternion`). It will continue to expose nested fields as long as they lead to a primitive base type.
* **Dictionaries**: Dynamic fields, such as the `user_metadata` found in the **`Topic`** and **`Sequence`** platform models (from `mosaicolabs.models.platform`), are fully queryable through the proxy using bracket notation (e.g., `Topic.Q.user_metadata["key"]`). This approach provides the flexibility to search across custom tags and dynamic properties that aren't part of a fixed schema. This dictionary-based querying logic is not restricted to platform models; it applies to any **custom ontology model** created by the user that contains a `dict` field.
    * **Syntax**: Instead of the standard dot notation used for fixed fields, you must use square brackets `["key"]` to target specific dictionary entries.
    * **Nested Access**: For dictionaries containing nested structures, you can use **dot notation within the key string** (e.g., `["environment.visibility"]`) to traverse sub-fields.
    * **Operator Support**: Because dictionary values are dynamic, these fields are "promiscuous," meaning they support all available numeric, string, and boolean operators without strict SDK-level type checking.

* **Unsupported Types (Lists and Tuples)**: Any field defined as a container, such as a **List** or **Tuple** (e.g., `covariance: List[float]`), is currently skipped by the proxy generator. These fields will not appear in autocomplete and cannot be used in a query expression.

#### Supported Operators by Type

| Data Type | Operators |
| --- | --- |
| **Numeric** | `.eq()`, `.neq()`, `.lt()`, `.leq()`, `.gt()`, `.geq()`, `.between()`, `.in_()` |
| **String** | `.eq()`, `.neq()`, `.match()` (substring), `.in_()` |
| **Boolean** | `.eq(True/False)` |


## Query Layers

Mosaico organizes data into three distinct architectural layers, each with its own specialized Query Builder:

1. **Sequence Layer (`QuerySequence`)**: Filters recordings based on high-level session metadata, such as the sequence name or the time it was created.

    | Methods | Return | Target Resource |
    | :--- | :--- | :--- |
    | `__init__(*expressions)` | `None` | Initializes the query with an optional set of initial expressions (via the `.Q` proxy). |
    | `with_name(name)` | `QuerySequence` | Add a filter for the sequence exact 'name' field. |
    | `with_name_match(name)` | `QuerySequence`| Add a filter for the partial sequence 'name' field (subsring). |
    | `with_created_timestamp(time_start, time_end)` | `QuerySequence`| Add a filter for the 'creation_unix_timestamp' field. |
    | `with_expression(expr)` | `QuerySequence` | Adds a new expression to the query (via the `.Q` proxy). |

2. **Topic Layer (`QueryTopic`)**: Targets specific data channels within a sequence. You can search for topics by name pattern or by their specific Ontology type (e.g., "Find all GPS topics").

    | Methods | Return | Target Resource |
    | :--- | :--- | :--- |
    | `__init__(*expressions)` | `None` | Initializes the query with an optional set of initial expressions. |
    | `with_name(name)` | `QueryTopic` | Add a filter for the topic exact 'name' field. |
    | `with_name_match(name)` | `QueryTopic`| Add a filter for the partial topic 'name' field (subsring). |
    | `with_ontology_tag(tag)` | `QueryTopic`| Add a filter for the 'ontology_tag' supported by the topic. |
    | `with_created_timestamp(time_start, time_end)` | `QueryTopic`| Add a filter for the 'creation_unix_timestamp' field. |
    | `with_expression(expr)` | `QueryTopic` | Adds a new expression to the query (via the `.Q` proxy). |

3. **Ontology Catalog Layer (`QueryOntologyCatalog`)**: The deepest layer of discovery. It allows you to search the **actual time-series content** of the sensors (e.g., "Find events where `acceleration.z` exceeded a specific value").

    | Methods |  Return | Target Resource |
    | :--- | :--- | :--- |
    | `__init__(*expressions,include_timestamp_range)` | `None`| Initializes the query with an optional set of initial expressions. If `include_timestamp_range==True`, the server returns the start and end timestamps of the queried condition.|
    | `with_expression(expr)` | `QueryOntologyCatalog` | Adds a new expression to the query (via the `.Q` proxy). |


The Mosaico Query Module offers two distinct paths for defining filters,  **Convenience Methods** and **Generic Expression Method**, both of which support **method chaining** to compose multiple criteria into a single query using a logical **AND**.

#### Convenience Methods

The query layers provide high-level helpers (`with_<attribute>`), built directly into the query builder classes and designed for ease of use.
They allow you to filter data without deep knowledge of the internal model schema. 
The builder automatically selects the appropriate field and operator (such as exact match vs. substring pattern) based on the method used.

```python
from mosaicolabs import QuerySequence, QueryTopic, RobotJoint

# Build a filter with name pattern
qbuilder = QuerySequence()
    .with_name_match("test_drive")

# Build a filter with ontology tag AND a specific creation time window
qbuilder = QueryTopic()
    .with_ontology_tag(RobotJoint.ontology_tag())
    .with_created_timestamp(start=t1, end=t2)

```

* **Best For**: Standard system-level fields like Names and Timestamps.

#### Generic Expression Method

The `with_expression()` method accepts raw **Query Expressions** generated through the `.Q` proxy. 
This provides full access to every supported operator (`.gt()`, `.lt()`, `.between()`, etc.) for specific fields.

```python
from mosaicolabs import QueryOntologyCatalog, QuerySequence, IMU

# Build a filter with name pattern and metadata-related expression
qbuilder = QuerySequence()
    .with_expression(
        # Use query proxy for generating a QueryExpression
        Sequence.Q.user_metadata['environment.visibility'].lt(50)
    )
    # Can be AND-chained with convenience methods
    .with_name_match("test_drive")

# Build a filter with deep time-series data discovery and measurement time windowing
qbuilder = QueryOntologyCatalog()
    .with_expression(IMU.Q.acceleration.x.gt(5.0))
    .with_expression(IMU.Q.header.stamp.sec.gt(1700134567))
    .with_expression(IMU.Q.header.stamp.nanosec.between([123456, 789123]))
```

* **Best For**: Accessing specific Ontology data fields (e.g., acceleration, position, etc.) and custom `user_metadata` in `Sequence` and `Topic` data models.

## Query Execution & The Response Model

Queries are executed via the `query()` method exposed by the `MosaicoClient` class. When multiple builders are provided, they are combined with a logical **AND**.

| Method | Return | Description |
| :--- | :--- | :--- |
| `query(*queries, query)` | `Optional[QueryResponse]` | Executes one or more queries against the platform catalogs. The provided queries are joined in AND condition. The method accepts a variable arguments of query builder objects or a pre-constructed *Query* object.|


### The Response Hierarchy

Execution returns a `QueryResponse` object, which behaves like a standard Python list containing `QueryResponseItem` objects.

| Class | Description |
| --- | --- |
| **`QueryResponseItem`** | Groups all matches belonging to the same **Sequence**. Constains a `QueryResponseItemSequence` and a list of related `QueryResponseItemTopic`.|
| **`QueryResponseItemSequence`** | Represents a specific **Sequence** where matches were found. It includes the sequence name. |
| **`QueryResponseItemTopic`** | Represents a specific **Topic** where matches were found. It includes the normalized topic path and the optional `timestamp_range` (the first and last occurrence of the condition). |

This example demonstrates a complete query execution and the inspection of the query response. By enabling the `include_timestamp_range` flag, the platform identifies the exact temporal windows where the physical conditions were met.

```python
import sys
from mosaicolabs import MosaicoClient, QueryOntologyCatalog
from mosaicolabs.models.sensors import IMU

# Establish a connection to the Mosaico Data Platform
with MosaicoClient.connect("localhost", 6726) as client:
    
    # 1. Define a Deep Data Filter using the .Q Query Proxy
    # We are searching for vertical impact events where acceleration.z > 15.0 m/s^2
    impact_qbuilder = QueryOntologyCatalog(
        IMU.Q.acceleration.z.gt(15.0),
        # include_timestamp_range returns the precise start/end of the matching event
        include_timestamp_range=True
    )

    # 2. Execute the query via the client
    results = client.query(impact_qbuilder)
    
    # Handle potential server-side execution errors
    if results is None:
        print("Query returned an internal error.")
        sys.exit(1)

    # 3. Parse the structured QueryResponse object
    # Results are automatically grouped by Sequence for easier data management
    for item in results:
        print(f"Sequence: {item.sequence.name}")
        
        # Iterate through matching topics within the sequence
        for topic in item.topics:
            # Topic names are normalized (sequence prefix is stripped) for direct use
            print(f"  - Match in: {topic.name}")
            
            # Extract the temporal bounds of the event
            if topic.timestamp_range:
                start = topic.timestamp_range.start
                end = topic.timestamp_range.end
                print(f"    Occurrence: {start} ns to {end} ns")

```

### Technical Highlights

* **Type-Safe Discovery**: By using `IMU.Q.acceleration.z`, the SDK ensures you are querying a numeric field that physically exists in the IMU ontology.
* **Temporal Windows**: The `timestamp_range` provides the first and last occurrence of the queried condition within a topic, allowing you to slice data accurately for further analysis.
* **Result Normalization**: `topic.name` returns the relative topic path (e.g., `/sensors/imu`), making it immediately compatible with other SDK methods like `get_topic_handler()`.


### Restricted Queries (Chaining)
The `QueryResponse` class enables a powerful mechanism for **iterative search refinement** by allowing you to convert your current results back into a new query builder.
This approach is essential for resolving complex, multi-modal dependencies where a single monolithic query would be logically ambiguous or technically impossible.

| Method | Return Type | Description |
| --- | --- | --- |
| **`to_query_sequence()`** | `QuerySequence` | Returns a query builder pre-filtered to include only the **sequences** present in the response. |
| **`to_query_topic()`** | `QueryTopic` | Returns a query builder pre-filtered to include only the specific **topics** identified in the response. |

When you invoke these factory methods, the SDK generates a new query expression containing an explicit `$in` filter populated with the identifiers held in the current response. This effectively **"locks" the search domain**, allowing you to apply new criteria to a restricted subset of your data without re-scanning the entire platform catalog.

```python
# 1. Broad Search: Find all sequences where a GPS sensor reached a high-precision state (status=2)
initial_response = client.query(
    QueryOntologyCatalog(GPS.Q.status.status.eq(2))
)
# 'initial_response' now acts as a filtered container of matching sequences.

# 2. Domain Locking: Restrict the search scope to the results of the initial query
if not initial_response.is_empty():
    # .to_query_sequence() generates a QuerySequence pre-filled with the matching sequence names.
    refined_query = initial_response.to_query_sequence()

    # 3. Targeted Refinement: Search for error patterns ONLY within the restricted domain
    # This ensures the platform only scans for '[ERR]' strings within sequences already validated for GPS precision.
    final_response = client.query(
        refined_query,                                         # The "locked" sequence domain
        QueryTopic().with_name("/localization/log_string"),    # Target a specific log topic
        QueryOntologyCatalog(String.Q.data.match("[ERR]"))     # Filter by exact data content pattern
    )

```

When a specific set of topics has been identified through a data-driven query (e.g., finding every camera topic that recorded a specific event), you can use `to_query_topic()` to "lock" your next search to those specific data channels. This is particularly useful when you need to verify a condition on a very specific subset of sensors across many sequences, bypassing the need to re-identify those topics in the next step.

In the next example, we first find all topics that are tagged as "High-Resolution" in their metadata and then search specifically within *those* topics for any instances where the sensor acquisition time indicates a lag.

```python
from mosaicolabs.models.platform import Topic
from mosaicolabs.models.query import QueryTopic, QueryOntologyCatalog
from mosaicolabs.models.sensors import Image

# 1. Initial Query: Find all topics that have a specific user_metadata tag
# We look for topics tagged with a 'quality' level of 'high-res'
initial_response = client.query(
    QueryTopic().with_expression(Topic.Q.user_metadata["quality"].eq("high-res"))
)

# 2. Topic-Level Domain Locking
if not initial_response.is_empty():
    # .to_query_topic() generates a QueryTopic pre-filled with the specific 
    # topic paths identified in the first step.
    restricted_topic_scope = initial_response.to_query_topic()

    # 3. Targeted Refinement: Search for data events within those exact topics
    # We now look for frames within those high-res topics where the 
    # internal sensor stamp exceeds a certain epoch.
    final_results = client.query(
        restricted_topic_scope,                            # The "locked" topic paths
        QueryOntologyCatalog(
            Image.Q.header.stamp.sec.gt(1704067200),       # Filter by data content
            include_timestamp_range=True                   # pinpoint the exact time range
        )
    )
    
    # Process results as usual
    for item in final_results:
        print(f"Verified high-res data in sequence: {item.sequence.name}")

```

#### When Chaining is Necessary

The previous example of the GPS query and the subsequent `/localization/log_string` topic search highlight exactly when *query chaining* becomes a technical necessity rather than just a recommendation. In the Mosaico Data Platform, a single `client.query()` call applies a logical **AND** across all provided builders to locate individual **data streams (topics)** that satisfy every condition simultaneously.
Because a single topic cannot physically represent two different sensor types at once, such as being both a `GPS` sensor and a `String` log, a monolithic query attempting to filter for both on the same stream will inherently return zero results. Chaining resolves this by allowing you to find the correct **Sequence** context in step one, then "locking" that domain to find a different **Topic** within that same context in step two.

```python
# AMBIGUOUS: This looks for ONE topic that is BOTH GPS and String
response = client.query(
    QueryOntologyCatalog(GPS.Q.status.status.eq(DGPS_FIX)),
    QueryOntologyCatalog(String.Q.data.match("[ERR]")),
    QueryTopic().with_name("/localization/log_string")
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
