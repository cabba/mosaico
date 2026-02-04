"""
Kinematics Data Structures.

This module defines structures for analyzing motion:
1.  **Velocity (Twist)**: Linear and angular speed.
2.  **Acceleration**: Linear and angular acceleration.
3.  **MotionState**: A complete snapshot of an object's kinematics (Pose + Velocity + Acceleration).

These can be assigned to Message.data field to send data to the platform.
"""

from typing import Optional
import pyarrow as pa
from pydantic import model_validator

from ..serializable import Serializable
from ..mixins import HeaderMixin, CovarianceMixin
from .geometry import Pose, Vector3d


class Velocity(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents 6-Degree-of-Freedom Velocity, commonly referred to as a Twist.

    The `Velocity` class describes the instantaneous motion of an object, split into
    linear and angular components.

    Attributes:
        linear: Optional [`Vector3d`][mosaicolabs.models.data.geometry.Vector3d] linear velocity vector.
        angular: Optional [`Vector3d`][mosaicolabs.models.data.geometry.Vector3d] angular velocity vector.
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 3x3 covariance matrix representing
            the uncertainty of the point measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    Note: Input Validation
        A valid `Velocity` object must contain at least a `linear` or an `angular`
        component; providing neither will raise a `ValueError`.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "linear",
                Vector3d.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "3D linear velocity vector"},
            ),
            pa.field(
                "angular",
                Vector3d.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "3D angular velocity vector"},
            ),
        ]
    )

    linear: Optional[Vector3d] = None
    """3D linear velocity vector"""

    angular: Optional[Vector3d] = None
    """3D angular velocity vector"""

    @model_validator(mode="after")
    def check_at_least_one_exists(self) -> "Velocity":
        """
        Ensures the velocity object is not empty.

        Raises:
            ValueError: If both `linear` and `angular` are None.
        """
        if self.linear is None and self.angular is None:
            raise ValueError("User must provide at least 'linear' or 'angular'.")
        return self


class Acceleration(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents 6-Degree-of-Freedom Acceleration.

    This class provides a standardized way to transmit linear and angular
    acceleration data to the platform.

    Attributes:
        linear: Optional 3D linear acceleration vector ($a_x, a_y, a_z$).
        angular: Optional 3D angular acceleration vector ($\alpha_x, \alpha_y, \alpha_z$).
        header: Optional metadata header providing acquisition context.
        covariance: Optional flattened 3x3 covariance matrix representing
            the uncertainty of the point measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    Note: Input Validation
        Similar to the [`Velocity`][mosaicolabs.models.data.kinematics.Velocity] class, an `Acceleration` instance requires
        at least one non-null component (`linear` or `angular`).
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "linear",
                Vector3d.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "3D linear acceleration vector"},
            ),
            pa.field(
                "angular",
                Vector3d.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "3D angular acceleration vector"},
            ),
        ]
    )

    linear: Optional[Vector3d] = None
    """3D linear acceleration vector"""

    angular: Optional[Vector3d] = None
    """3D angular acceleration vector"""

    @model_validator(mode="after")
    def check_at_least_one_exists(self) -> "Acceleration":
        """
        Ensures the acceleration object is not empty.

        Raises:
            ValueError: If both `linear` and `angular` are None.
        """
        if self.linear is None and self.angular is None:
            raise ValueError("User must provide at least 'linear' or 'angular'.")
        return self


class MotionState(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Aggregated Kinematic State.

    `MotionState` groups [`Pose`][mosaicolabs.models.data.geometry.Pose],
    [`Velocity`][mosaicolabs.models.data.kinematics.Velocity], and optional
    [`Acceleration`][mosaicolabs.models.data.kinematics.Acceleration] into a
    single atomic update.

    This is the preferred structure for:

    * **Trajectory Tracking**: Recording the high-fidelity path of a robot or vehicle.
    * **State Estimation**: Logging the output of Kalman filters or SLAM algorithms.
    * **Ground Truth**: Storing reference data from simulation environments.

    Attributes:
        pose: The 6D pose representing current position and orientation.
        velocity: The 6D velocity (Twist).
        target_frame_id: A string identifier for the target coordinate frame.
        acceleration: Optional 6D acceleration.
        header: Standard metadata header for temporal synchronization.
        covariance: Optional flattened NxN composed covariance matrix representing
            the uncertainty of the Pose+Velocity+[Acceleration] measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "pose",
                Pose.__msco_pyarrow_struct__,
                nullable=False,
                metadata={
                    "description": "6D pose with optional time and covariance info."
                },
            ),
            pa.field(
                "velocity",
                Velocity.__msco_pyarrow_struct__,
                nullable=False,
                metadata={
                    "description": "6D velocity with optional time and covariance info."
                },
            ),
            pa.field(
                "target_frame_id",
                pa.string(),
                nullable=False,
                metadata={"description": "Target frame identifier."},
            ),
            pa.field(
                "acceleration",
                Acceleration.__msco_pyarrow_struct__,
                nullable=True,
                metadata={
                    "description": "6D acceleration with optional time and covariance info."
                },
            ),
        ]
    )

    pose: Pose
    """6D pose with optional time and covariance info"""

    velocity: Velocity
    """6D velocity with optional time and covariance info"""

    target_frame_id: str
    """Target frame identifier"""

    acceleration: Optional[Acceleration] = None
    """6D acceleration with optional time and covariance info"""
