"""
This module defines the fundamental building blocks for spatial representation, including vectors, points, quaternions, and rigid-body transforms.

The module follows a **Two-Tier Architecture** to optimize both internal efficiency and public usability:

* **Internal Structs (`_Struct`)**: Pure data containers that define the physical memory layout and the PyArrow schema. These are intended for embedding within larger composite objects (like a `Pose` or `Transform`) to avoid attaching redundant metadata headers or timestamps to every inner field.
* **Public Classes**: High-level models that combine spatial data with Mosaico's transport and serialization logic. These inherit from the internal structs and inject support for auto-registration ([`Serializable`][mosaicolabs.models.serializable.Serializable]), temporal/spatial context ([`HeaderMixin`][mosaicolabs.models.mixins.HeaderMixin]), and uncertainty tracking ([`CovarianceMixin`][mosaicolabs.models.mixins.CovarianceMixin]).
"""

from typing import Optional
import pyarrow as pa

from ..base_model import BaseModel
from ..serializable import Serializable
from ..mixins import HeaderMixin, CovarianceMixin


# ---------------------------------------------------------------------------
# Vector STRUCT classes
# ---------------------------------------------------------------------------


class _Vector2dStruct(BaseModel):
    """
    The internal data layout for 2D spatial vectors.

    This class serves as the schema definition for (x, y) coordinates.

    Note: Nullability Handling
        All fields are explicitly marked as `nullable=True` in the PyArrow schema.
        This ensures that empty fields are correctly deserialized as `None` rather than
        incorrectly being default-initialized to $0$ by Parquet readers.
    """

    # OPTIONALITY NOTE
    # All fields are explicitly set to `nullable=True`. This prevents Parquet V2
    # readers from incorrectly deserializing a `None` _Vector2dStruct field in a class
    # as a default-initialized object (e.g., getting _Vector2dStruct(0, ...) instead of None).
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "x",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector x component"},
            ),
            pa.field(
                "y",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector y component"},
            ),
        ]
    )

    x: float
    y: float

    @classmethod
    def from_list(cls, data: list[float]):
        """
        Creates a struct instance from a raw list.

        Args:
            data: A list containing exactly 2 float values: [x, y].

        Raises:
            ValueError: If the input list does not have a length of 2.
        """
        if len(data) != 2:
            raise ValueError("expected 2 values")
        return cls(x=data[0], y=data[1])


class _Vector3dStruct(BaseModel):
    """
    The internal data layout for 3D spatial vectors.

    This class serves as the schema definition for (x, y, z) coordinates.
    It is used as a nested component in composite models like [`Pose`][mosaicolabs.models.data.geometry.Pose]
    or [`Transform`][mosaicolabs.models.data.geometry.Transform].

    Note: Nullability Handling
        All fields are explicitly marked as `nullable=True` in the PyArrow schema.
        This ensures that empty fields are correctly deserialized as `None` rather than
        incorrectly being default-initialized to $0$ by Parquet readers.
    """

    # OPTIONALITY NOTE
    # All fields are explicitly set to `nullable=True`. This prevents Parquet V2
    # readers from incorrectly deserializing a `None` _Vector3dStruct field in a class
    # as a default-initialized object (e.g., getting _Vector3dStruct(0, ...) instead of None).
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "x",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector x component"},
            ),
            pa.field(
                "y",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector y component"},
            ),
            pa.field(
                "z",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector z component"},
            ),
        ]
    )

    x: float
    y: float
    z: float

    @classmethod
    def from_list(cls, data: list[float]):
        """
        Creates a struct instance from a raw list.

        Args:
            data: A list containing exactly 3 float values: [x, y, z].

        Raises:
            ValueError: If the input list does not have a length of 3.
        """
        if len(data) != 3:
            raise ValueError("expected 3 values")
        return cls(x=data[0], y=data[1], z=data[2])


class _Vector4dStruct(BaseModel):
    """
    The internal data layout for 4D spatial vectors.

    This class serves as the schema definition for (x, y, z, w) coordinates.
    It is used as a nested component in composite models like [`Pose`][mosaicolabs.models.data.geometry.Pose]
    or [`Transform`][mosaicolabs.models.data.geometry.Transform].

    Note: Nullability Handling
        All fields are explicitly marked as `nullable=True` in the PyArrow schema.
        This ensures that empty fields are correctly deserialized as `None` rather than
        incorrectly being default-initialized to $0$ by Parquet readers.
    """

    # OPTIONALITY NOTE
    # All fields are explicitly set to `nullable=True`. This prevents Parquet V2
    # readers from incorrectly deserializing a `None` _Vector4dStruct field in a class
    # as a default-initialized object (e.g., getting _Vector4dStruct(0, ...) instead of None).
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "x",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector x component"},
            ),
            pa.field(
                "y",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector y component"},
            ),
            pa.field(
                "z",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector z component"},
            ),
            pa.field(
                "w",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vector w component"},
            ),
        ]
    )

    x: float
    y: float
    z: float
    w: float

    @classmethod
    def from_list(cls, data: list[float]):
        """
        Creates a struct instance from a raw list.

        Args:
            data: A list containing exactly 4 float values: [x, y, z, w].

        Raises:
            ValueError: If the input list does not have a length of 4.
        """
        if len(data) != 4:
            raise ValueError("expected 4 values")
        return cls(x=data[0], y=data[1], z=data[2], w=data[3])


# ---------------------------------------------------------------------------
# Public vector classes
# ---------------------------------------------------------------------------


class Vector2d(
    _Vector2dStruct,  # Inherits fields (x, y)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    A public 2D Vector for platform-wide transmission.

    This class combines the [x, y] coordinates with full Mosaico transport logic.
    It is used to represent quantities such as velocity, acceleration, or directional forces.

    Attributes:
        x: Vector X component.
        y: Vector Y component.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 2x2 covariance matrix representing
            the uncertainty of the vector measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    """

    pass


class Vector3d(
    _Vector3dStruct,  # Inherits fields (x, y, z)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    A public 3D Vector for platform-wide transmission.

    This class combines the [x, y, z] coordinates with full Mosaico transport logic.
    It is used to represent quantities such as velocity, acceleration, or directional forces.

    Attributes:
        x: Vector X component.
        y: Vector Y component.
        z: Vector Z component.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 3x3 covariance matrix representing
            the uncertainty of the vector measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    """

    pass


class Vector4d(
    _Vector4dStruct,  # Inherits fields (x, y, z, w)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    A public 4D Vector for platform-wide transmission.

    This class combines the [x, y, z, w] coordinates with full Mosaico transport logic.
    It is used to represent quantities such as velocity, acceleration, or directional forces.

    Attributes:
        x: Vector X component.
        y: Vector Y component.
        z: Vector Z component.
        w: Vector W component.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 4x4 covariance matrix representing
            the uncertainty of the vector measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.
    """

    pass


class Point2d(
    _Vector2dStruct,  # Inherits fields (x, y)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Semantically represents a specific location (Point) in 2D space.

    Structurally identical to a 2D Vector, but distinguished within the Mosaico API
    to clarify intent in spatial operations. Use this class for
    2D coordinate data that requires Mosaico transport logic.

    Attributes:
        x: Point X coordinate.
        y: Point Y coordinate.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 2x2 covariance matrix representing
            the uncertainty of the point measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    """

    pass


class Point3d(
    _Vector3dStruct,  # Inherits fields (x, y, z)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Semantically represents a specific location (Point) in 3D space.

    The `Point3d` class is used to instantiate a 3D coordinate message for
    transmission over the platform. It is structurally identical
    to a 3D Vector but is used to denote state rather than direction.

    Attributes:
        x: Point X coordinate.
        y: Point Y coordinate.
        z: Point Z coordinate.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 3x3 covariance matrix representing
            the uncertainty of the point measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    """

    pass


class Quaternion(
    _Vector4dStruct,  # Inherits fields (x, y, z, w)
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents a rotation in 3D space using normalized quaternions.

    Structurally identical to a 4D vector [x, y, z, w], but semantically denotes
    an orientation. This representation avoids the gimbal lock
    issues associated with Euler angles.

    Attributes:
        x: Vector X component.
        y: Vector Y component.
        z: Vector Z component.
        w: Vector W component.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 4x4 covariance matrix representing
            the uncertainty of the quaternion measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.
    """

    pass


# ---------------------------------------------------------------------------
# Composite Structures
# ---------------------------------------------------------------------------


class Transform(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents a rigid-body transformation between two coordinate frames.

    A transform consists of a translation followed by a rotation. It is
    typically used to describe the kinematic relationship between components
    (e.g., "Camera to Robot Base").

    Attributes:
        translation: A `Vector3d` describing the linear shift.
        rotation: A `Quaternion` describing the rotational shift.
        target_frame_id: The identifier of the destination coordinate frame.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 7x7 composed covariance matrix representing
            the uncertainty of the Translation+Rotation.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "translation",
                Vector3d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "3D translation vector"},
            ),
            pa.field(
                "rotation",
                Quaternion.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "Quaternion representing rotation."},
            ),
            pa.field(
                "target_frame_id",
                pa.string(),
                nullable=True,
                metadata={"description": "Target frame identifier."},
            ),
        ]
    )

    translation: Vector3d
    """3D translation vector."""

    rotation: Quaternion
    """Quaternion representing rotation."""

    target_frame_id: Optional[str] = None
    """Target frame identifier."""


class Pose(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents the position and orientation of an object in a global or local frame.

    While similar to a [`Transform`][mosaicolabs.models.data.geometry.Transform], a
    `Pose` semantically denotes the **state** of an object (its current location
    and heading) rather than the mathematical shift between two frames.

    Attributes:
        position: A `Point3d` representing the object's coordinates.
        orientation: A `Quaternion` representing the object's heading.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 7x7 composed covariance matrix representing
            the uncertainty of the Translation+Rotation.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "position",
                Point3d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "3D translation vector"},
            ),
            pa.field(
                "orientation",
                Quaternion.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "Quaternion representing rotation."},
            ),
        ]
    )

    position: Point3d
    """3D translation vector"""

    orientation: Quaternion
    """Quaternion representing rotation."""
