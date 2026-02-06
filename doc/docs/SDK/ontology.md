---
title: Data Models & Ontology
description: Strongly typed data structures.
sidebar:
    order: 3
---

The **Mosaico Data Ontology** is the semantic backbone of the SDK. 
It defines the structural "rules" that transform raw binary streams into meaningful physical data, such as GPS coordinates, 
inertial measurements, or camera frames.

By using a strongly-typed ontology, Mosaico ensures that your data remains consistent, validatable, 
and highly optimized for both high-throughput transport and complex queries.


## Core Philosophy

The ontology is designed to solve the "generic data" problem in robotics by ensuring every data object is:

1. **Validatable**: Uses Pydantic for strict runtime type checking of sensor fields.
2. **Serializable**: Automatically maps Python objects to efficient **PyArrow** schemas for high-speed binary transport.
3. **Queryable**: Injects a fluent API (`.Q`) into every class, allowing you to filter databases based on physical values (e.g., `IMU.Q.acceleration.x > 6.0`).
4. **Middleware-Agnostic**: Acts as an abstraction layer so that your analysis code doesn't care if the data originally came from ROS, a simulator, or a custom logger.

## The Building Blocks

The ontology architecture relies on three primary abstractions: the **Factory** (`Serializable`), the **Envelope** (`Message`) and the **Mixins**

### 1. `Serializable` (The Factory)

Every data payload in Mosaico inherits from the `Serializable` class. It manages the global registry of data types and ensures that the system knows exactly how to convert a string tag like `"imu"` back into a Python class with a specific binary schema.
`Serializable` uses the `__init_subclass__` hook, which is automatically called whenever a developer defines a new subclass.

```python
class MyCustomSensor(Serializable):  # <--- __init_subclass__ triggers here
    ...
```
When this happens, `Serializable` performs the following steps automatically:

1.  **Validates Schema:** Checks if the subclass defined the PyArrow struct schema (`__msco_pyarrow_struct__`). 
If missing, it raises an error at definition time (import time), preventing runtime failures later.
2.  **Generates Tag:** If the class doesn't define `__ontology_tag__`, it auto-generates one from the class name (e.g., `MyCustomSensor` -> `"my_custom_sensor"`).
3.  **Registers Class:** It adds the new class to the global types registry.
4.  **Injects Query Proxy:** It dynamically adds a `.Q` attribute to the class, enabling the fluent query syntax (e.g., `MyCustomSensor.Q.voltage > 12.0`).

#### Quick Reference
| Method | Return | Description |
| :--- | :--- | :--- |
| **`ontology_tag()`** | `str` | Returns the unique string identifier for a class or instance. |


### 2. `Message` (The Envelope)

The **`Message`** class is the universal transport envelope for all data within the Mosaico platform. 
It acts as a wrapper that combines specific sensor data (the payload) with middleware-level metadata.

```python
from mosaicolabs import Message, Time, Header, Temperature
# Use Case: Create a Temperature timestamped message with uncertainty
meas_time = Time.now()
temp_msg = Message(
    timestamp_ns=msg_time.to_nanoseconds(), # here the message timestamp is the same as the measurement, but it can be different
    data=Temperature.from_celsius(
        value=57,
        header=Header(stamp=meas_time, frame_id="comp_case"),
        variance=0.03
    )
)
```
#### Quick Reference
| Field/Method | Type/Return | Description |
| :--- | :--- | :--- |
| **`timestamp_ns`** | `int` | Middleware processing timestamp in nanoseconds (different from sensor acquisition time). |
| **`data`** | `Serializable` | The polymorphic payload (e.g., an IMU object). |
| **`message_header`** | `Optional[Header]` | Middleware-level header. |
| **`get_data()`** | `Serializable` | A type-safe accessor that returns the payload bound to the specified ontology model. |
| **`ontology_type()`** | `Type[Serializable]` | Retrieves the Python class type of the payload stored in the `data` field. |
| **`ontology_tag()`** | `str` | Returns the unique string identifier (tag) for the payload (e.g., `"imu"`). |
| **`from_dataframe_row()`** | `Message` | **(Static)** Reconstructs a full `Message` object from a flattened row produced by the [`DataFrameExtractor`](./bridges/ml.md#from-sequences-to-dataframes).

While logically a `Message` contains a `data` object (e.g., an instance of an Ontology type), physically on the wire (PyArrow/Parquet), the fields are **flattened**.

  * **Logical:** `Message(timestamp_ns=123, data=IMU(acceleration=Vector3d(x=1.0,...)))`
  * **Physical:** `Struct(timestamp_ns=123, acceleration, ...)`

This flattening is handled automatically by the class internal methods.
This ensures zero-overhead access to nested data during queries while maintaining a clean object-oriented API in Python.


### 3. Mixins: Headers & Uncertainty

Mosaico uses **Mixins** to inject standard fields across different data types, ensuring a consistent interface.
Almost every class in the ontology, from high-level sensors down to elementary data primitives like `Vector3d` or `Float32`, 
inherits from two Mixin classes, which inject standard fields into data models via composition, ensuring consistency across different sensor types:

* **`HeaderMixin`**: Injects a standard (Optional) `header` containing a sequence ID, a frame ID (e.g., `"base_link"`), and a high-precision acquisition timestamp (`stamp`).

    | Field | Type | Description |
    | :--- | :--- | :--- |
    | **`stamp`** | `Time` | Time of data acquisition. |
    | **`frame_id`** | `str` | Coordinate frame ID. |
    | **`seq`** | `Optional[int]` | Sequence ID. Legacy field. |

* **`CovarianceMixin`**: Injects multidimensional uncertainty fields, typically used for flattened covariance matrices in sensor fusion applications.

    | Field | Type | Description |
    | :--- | :--- | :--- |
    | **`covariance`** | `Optional[List[float]]` | The covariance matrix (flattened) of the data. |
    | **`covariance_type`** | `Optional[int]` | Enum integer representing the covariance parameterization. |

* **`VarianceMixin`**: Injects monodimensional uncertainty fields, useful for sensors with 1-dimensional uncertain data (like `Temperature` or `Pressure`).

    | Field | Type | Description |
    | :--- | :--- | :--- |
    | **`variance`** | `Optional[List[float]]` | The covariance matrix (flattened) of the data. |
    | **`variance_type`** | `Optional[int]` | Enum integer representing the covariance parameterization. |

The integration of **`HeaderMixin`** and **`Covariance/VarianceMixin`** into the Mosaico Data Ontology enables a flexible dual-usage pattern: **Standalone Messages** and **Embedded Fields**. 
This design ensures that base geometric types can serve as either independent data streams or granular components of complex sensor models.

#### Standalone Usage

Because elementary types (such as `Vector3d`, `String`, or `Float32`) inherit directly from these mixins, they are "first-class" members of the ontology. 
You can treat them as independent, timestamped messages without needing to wrap them in a more complex container.

This is ideal for pushing processed signals, debug values, or simple sensor readings that require their own metadata and uncertainty context.

```python
# Use Case: Sending a raw 3D vector as a timestamped message with uncertainty
accel_msg = Vector3d(
    x=0.0, 
    y=0.0, 
    z=9.81,
    header=Header(stamp=Time.now(), frame_id="base_link"),
    covariance=[0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]  # 3x3 Diagonal matrix
)

# `acc_writer` is a TopicWriter associated to the new sequence that is being uploaded.
acc_writer.push(message=Message(timestamp_ns=ts, data=accel_msg)) # (1)!

# Use Case: Sending a timestamped diagnostic error
error_msg = String(
    data="Waypoint-miss in navigation detected!",
    header=Header(stamp=Time.now(), frame_id="base_link")
)

# `log_writer` is another TopicWriter associated to the new sequence that is being uploaded.
log_writer.push(message=Message(timestamp_ns=ts, data=error_msg))
```

1. The `push` command will be covered in the documentation of the Writers 

#### Embedded Usage

When these base types are used as internal fields within a larger structure (e.g., an `IMU` or `MotionState` model), the mixins allow you to attach metadata to specific *parts* of a message.

In this context, while the parent object (the `IMU`) carries a global timestamp, the individual fields (like `acceleration`) can carry their own specific **covariance** matrices.
To avoid data redundancy, the internal `header` of the embedded field is typically left as `None`, as it inherits the temporal context from the parent message.

```python
# Use Case: Embedding Vector3d inside a complex IMU message
imu_msg = IMU(
    # Parent Header: Defines the time and frame for the entire sensor packet
    header=Header(stamp=Time.now(), frame_id="imu_link"),
    
    # Embedded Field 1: Acceleration
    # Inherits global time, but specifies its own unique uncertainty
    acceleration=Vector3d(
        x=0.5, y=-0.2, z=9.8,
        covariance=[0.1, 0, 0, 0, 0.1, 0, 0, 0, 0.1] # Specific to acceleration
    ),
    
    # Embedded Field 2: Angular Velocity
    # Carries a distinct covariance matrix independent of the acceleration
    angular_velocity=Vector3d(
        x=0.01, y=0.0, z=-0.01,
        covariance=[0.05, 0, 0, 0, 0.05, 0, 0, 0, 0.05] # Specific to velocity
    )
)

# as above, `imu_writer` is another TopicWriter associated to the new sequence that is being uploaded.
imu_writer.push(imu_msg)

```
## Customizing the Ontology

The Mosaico SDK is built for extensibility, allowing you to define domain-specific data structures that can be registered to the platform and live alongside standard types.
Custom types are automatically validatable, serializable, and queryable once registered in the platform.

Follow these three steps to implement a compatible custom data type:

### 1. Inheritance and Mixins

Your custom class **must** inherit from `Serializable` to enable auto-registration, factory creation, and the queryability of the model. 
To align with the Mosaico ecosystem, use the following mixins:

* **`HeaderMixin`**: Required for timestamped data or sensor readings. It injects a standard `header` (stamp, frame_id, seq), ensuring your data remains compatible with time-synchronization and coordinate frame logic.
* **`CovarianceMixin`**: Used for data including measurement uncertainty, standardizing the storage of covariance matrices.


### 2. Define the Wire Schema (`__msco_pyarrow_struct__`)

You must define a class-level `__msco_pyarrow_struct__` using `pyarrow.struct`. This explicitly dictates how your Python object is serialized into high-performance Apache Arrow/Parquet buffers for network transmission and storage.

#### 2.1 Serialization Format Optimization

You can optimize remote server performance by overriding the `__serialization_format__` attribute. This controls how the server compresses and organizes your data.

| Format | Identifier | Use Case Recommendation |
| --- | --- | --- |
| **Default** | `"default"` | **Standard Table**: Fixed-width data with a constant number of fields. |
| **Ragged** | `"ragged"` | **Variable Length**: Best for lists, sequences, or point clouds. |
| **Image** | `"image"` | **Blobs**: Raw or compressed images requiring specialized codec handling. |

If not explicitly set, the system defaults to `Default` format.

### 3. Define Class Fields

Define the Python attributes for your class using standard type hints. 
Note that the names of your Python class fields **must match exactly** the field names defined in your `__msco_pyarrow_struct__` schema.


### Customization Example: `EnvironmentSensor`

This example demonstrates a custom sensor for environmental monitoring that tracks temperature, humidity, and pressure.

```python
# file: custom_ontology.py

from typing import Optional
import pyarrow as pa
from mosaicolabs.models import Serializable, HeaderMixin

class EnvironmentSensor(Serializable, HeaderMixin):
    """
    Custom sensor reading for Temperature, Humidity, and Pressure.
    """

    # --- 1. Define the Wire Schema (PyArrow Layout) ---
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field("temperature", pa.float32(), nullable=False),
            pa.field("humidity", pa.float32(), nullable=True),
            pa.field("pressure", pa.float32(), nullable=True),
        ]
    )

    # --- 2. Define Python Fields (Must match schema exactly) ---
    temperature: float
    humidity: Optional[float] = None
    pressure: Optional[float] = None


# --- Usage Example ---
from mosaicolabs.models import Message, Header, Time

# Initialize with standard metadata
meas = EnvironmentSensor(
    header=Header(stamp=Time.now(), frame_id="lab_sensor_1"),
    temperature=23.5,
    humidity=0.45
)

# Ready for streaming or querying
# writer.push(Message(timestamp_ns=ts, data=meas))

```
<figure markdown="span">
  ![Ontology customization example](../assets/ontology_customization.png)
  <figcaption>Schema for defining a custom ontology model.</figcaption>
</figure>



### Available Ontology Classes

The following classes are categorized into base geometric building blocks and high-level sensor types:

#### Base & Geometric Types

| Module | Classes | Purpose |
| --- | --- | --- |
| **Base Types** | `String`, `LargeString`, `Boolean`, `Integer8/16/32/64`, `Unsigned8/16/32/64`, `Floating16/32/64` | Timestamped wrappers for Python primitives. |
| **Geometry** | `Vector2d/3d/4d`, `Point2d/3d`, `Quaternion` | Fundamental spatial components. |
| **Spatial** | `Transform`, `Pose` | Spatial relationships and object positions. |
| **Vision** | `ROI` | Region of Interest in image coordinates. |

#### Sensor & Kinematic Types

| Module | Classes | Purpose |
| --- | --- | --- |
| **Kinematics** | `Velocity`, `Acceleration`, `MotionState` | Movement snapshots (linear and angular). |
| **Inertial** | `IMU` | Linear acceleration () and angular velocity (). |
| **Navigation** | `GPS`, `GPSStatus`, `NMEASentence` | Satellite positioning and raw receiver strings. |
| **Environment** | `Temperature`, `Pressure`, `Range` | Environmental and distances.|
| **Vision** | `Image`, `CompressedImage`, `CameraInfo` | Raw pixels, compressed blobs (JPEG/PNG), and calibration info. |
| **Dynamics** | `ForceTorque` | 3D force () and torque () vectors. |
| **Robotics** | `RobotJoint` | Names, positions, and efforts of robot joints. |
| **Magnetic** | `Magnetometer` | Magnetic field vectors in microTesla (). |

