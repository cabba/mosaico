---
title: Data Models & Ontology
description: Strongly typed data structures.
---

Mosaico enforces a strong schema using the `Serializable` factory. Every data object—from a simple `Vector3d` to a complex `CameraInfo`—is validatable via Pydantic and serializable to Apache Arrow. This eliminates "stringly-typed" dictionaries and ensures data integrity.

## The Message Envelope

All data on the platform is wrapped in a generic `Message` container. This separates middleware metadata (like reception time) from the actual sensor payload.

* **`timestamp_ns`**: The reception timestamp (Unix nanoseconds).
* **`data`**: The polymorphic payload (e.g., `IMU`, `Image`).

## Built-in Ontology Types

The SDK includes a comprehensive library of standard robotics types:

* **Sensors**: `IMU`, `GPS` (with `GPSStatus`), `Image` (Raw), `CompressedImage`, `Magnetometer`.
* **Geometry**: `Vector3d`, `Point3d`, `Quaternion`, `Pose`, `Transform`.
* **Kinematics**: `Velocity` (Twist), `Acceleration`, `MotionState` (Odometry).
* **Dynamics**: `ForceTorque` (Wrench).

## Defining Custom Types

You can extend the platform by defining your own classes. Simply inherit from `Serializable` and define the PyArrow structure.

```python
import pyarrow as pa
from mosaicolabs.models import Serializable, HeaderMixin

class BatteryStatus(Serializable, HeaderMixin):
    # Define the wire format for storage efficiency
    __msco_pyarrow_struct__ = pa.struct([
        pa.field("voltage", pa.float32()),
        pa.field("current", pa.float32())
    ])
    
    # Define Python fields for usage
    voltage: float
    current: float

```