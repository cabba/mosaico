import pyarrow as pa
from mosaicolabs import HeaderMixin, Serializable


class EncoderTicks(Serializable, HeaderMixin):
    """
    Custom Mosaico model for NVIDIA Isaac Nova Encoder Ticks.

    This model represents raw wheel encoder counts and their hardware-specific
    timestamps, providing the base data for dead-reckoning and odometry calculations.

    ### Structural Integrity
    To pass Mosaico's strict schema alignment check, the names defined in the
    `__msco_pyarrow_struct__` must match the Pydantic field names one-to-one.

    Attributes:
        left_ticks: Cumulative tick count for the left wheel.
        right_ticks: Cumulative tick count for the right wheel.
    """

    # --- Wire Schema Definition ---
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "left_ticks",
                pa.uint32(),
                nullable=False,
                metadata={
                    "description": "Cumulative counts from the left wheel encoder."
                },
            ),
            pa.field(
                "right_ticks",
                pa.uint32(),
                nullable=False,
                metadata={
                    "description": "Cumulative counts from the right wheel encoder."
                },
            ),
        ],
    )

    # --- Pydantic Fields ---
    # names must match between pyarrow struct and model fields
    left_ticks: int
    """Cumulative tick count for the left wheel."""
    right_ticks: int
    """Cumulative tick count for the right wheel."""

    # ROS message defines a 'encoder_timestamp' field. We will use the `HeaderMixin.header` mixin, instead of
    # defining a new timestamp field in the pyarrow struct and pydantic model. This is because the HeaderMixin
    # already provides a timestamp field that is compatible with the Mosaico Ontology.
