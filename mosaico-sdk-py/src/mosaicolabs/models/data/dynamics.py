"""
This module defines specialized ontology structures for representing physical dynamics, specifically linear forces and rotational moments (torques).

The primary structure, [`ForceTorque`][mosaicolabs.models.data.dynamics.ForceTorque], implements a standard "Wrench" representation.
These models are designed to be assigned to the `data` field of a [`Message`][mosaicolabs.models.Message] for transmission to the platform.

**Key Features:**
* **Wrench Representation**: Combines 3D linear force and 3D rotational torque into a single, synchronized state.
* **Uncertainty Quantification**: Inherits from [`CovarianceMixin`][mosaicolabs.models.mixins.CovarianceMixin] to support $6 \times 6$ covariance matrices, allowing for the transmission of sensor noise characteristics or estimation confidence.
"""

import pyarrow as pa

from ..serializable import Serializable
from ..mixins import HeaderMixin, CovarianceMixin
from .geometry import Vector3d


class ForceTorque(
    Serializable,  # Adds Registry/Factory logic
    HeaderMixin,  # Adds Timestamp/Frame info
    CovarianceMixin,  # Adds Covariance matrix support
):
    """
    Represents a Wrench (Force and Torque) applied to a rigid body.

    The `ForceTorque` class is used to describe the total mechanical action (wrench)
    acting on a body at a specific reference point. By combining
    linear force and rotational torque, it provides a complete description of
    dynamics for simulation and telemetry.

    Attributes:
        force: A `Vector3d` representing the linear force vector in Newtons ($N$).
        torque: A `Vector3d` representing the rotational moment vector in Newton-meters (Nm).
        header: Optional metadata header providing temporal and spatial context.
        covariance: Optional flattened 6x6 composed covariance matrix representing
            the uncertainty of the force-torque measurement.
        covariance_type: Enum integer representing the parameterization of the
            covariance matrix.

    Note: Unit Standards
        To ensure platform-wide consistency, all force components should be
        specified in **Newtons** and torque in **Newton-meters**.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "force",
                Vector3d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "3D linear force vector"},
            ),
            pa.field(
                "torque",
                Vector3d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "3D torque vector"},
            ),
        ]
    )

    force: Vector3d
    """3D linear force vector"""

    torque: Vector3d
    """3D torque vector"""
