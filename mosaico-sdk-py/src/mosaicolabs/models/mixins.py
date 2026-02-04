"""
Header Mixin Module.

This module provides `HeaderMixin`, a helper class used to inject standard
header fields into ontology models via composition.
"""

from typing import List, Optional
import pyarrow as pa

from .base_model import BaseModel
from .header import Header

# ---- HeaderMixin ----


class HeaderMixin(BaseModel):
    """
    A mixin that injects a standard `header` field into any inheriting ontology model.

    The `HeaderMixin` is used to add standard metadata (such as acquisition timestamps
    or frame IDs) to a sensor model through composition. It ensures that the
    underlying PyArrow schema remains synchronized with the Pydantic data model.

    ### Dynamic Schema Injection
    This mixin uses the `__init_subclass__` hook to perform a **Schema Append** operation:

    1. It inspects the child class's existing `__msco_pyarrow_struct__`.
    2. It appends a `header` field of type [`Header`][mosaicolabs.models.Header].
    3. It reconstructs the final `pa.struct` for the class.

    Attributes:
        header: An optional [`Header`][mosaicolabs.models.Header] object containing standard metadata.

    Important: Collision Safety
        The mixin performs a collision check during class definition. If the child
        class already defines a `header` field in its PyArrow struct, a `ValueError`
        will be raised to prevent schema corruption.
    """

    header: Optional[Header] = None
    """optional Header object containing standard metadata."""

    def __init_subclass__(cls, **kwargs):
        """
        Automatically updates the child class's PyArrow schema to include 'header'.

        This method is triggered at class definition time.

        Raises:
            ValueError: If a field named 'header' already exists in the child's schema.
        """
        super().__init_subclass__(**kwargs)

        # Define the PyArrow field definition for the header
        _HEADER_FIELD = pa.field(
            "header",
            Header.__msco_pyarrow_struct__,
            nullable=True,
            metadata={"description": "The standard metadata header (optional)."},
        )

        # Retrieve existing schema fields from the child class
        current_pa_fields = []
        if hasattr(cls, "__msco_pyarrow_struct__") and isinstance(
            cls.__msco_pyarrow_struct__, pa.StructType
        ):
            current_pa_fields = list(cls.__msco_pyarrow_struct__)

        # Collision Check
        existing_pa_names = [f.name for f in current_pa_fields]
        if "header" in existing_pa_names:
            raise ValueError(
                f"Class '{cls.__name__}' has conflicting 'header' schema key."
            )

        # Append and Update
        new_fields = current_pa_fields + [_HEADER_FIELD]
        cls.__msco_pyarrow_struct__ = pa.struct(new_fields)


# ---- CovarianceMixin ----


class CovarianceMixin(BaseModel):
    """
    A mixin that adds uncertainty fields (`covariance` and `covariance_type`) to data models.

    This is particularly useful for complex sensors like IMUs, Odometry, or GNSS
    receivers that provide multidimensional uncertainty matrices along with
    their primary measurements.

    ### Injected Fields
    * **`covariance`**: A flattened list of floats representing the covariance matrix.
    * **`covariance_type`**: An integer enum representing the specific parameterization
        used (e.g., fixed, diagonal, full).

    Attributes:
        covariance: Optional list of 64-bit floats representing the flattened matrix.
        covariance_type: Optional 16-bit integer representing the covariance enum.
    """

    covariance: Optional[List[float]] = None
    """Optional list of 64-bit floats representing the flattened matrix."""

    covariance_type: Optional[int] = None
    """Optional 16-bit integer representing the covariance enum."""

    def __init_subclass__(cls, **kwargs):
        """
        Dynamically appends covariance-related fields to the child class's PyArrow struct.

        Raises:
            ValueError: If 'covariance' or 'covariance_type' keys collide with existing fields.
        """
        super().__init_subclass__(**kwargs)

        # Define the fields to inject
        _FIELDS = [
            pa.field(
                "covariance",
                pa.list_(value_type=pa.float64()),
                nullable=True,
                metadata={
                    "description": "The covariance matrix (flattened) of the data."
                },
            ),
            pa.field(
                "covariance_type",
                pa.int16(),
                nullable=True,
                metadata={
                    "description": "Enum integer representing the covariance parameterization."
                },
            ),
        ]

        # Retrieve existing schema fields
        current_pa_fields = []
        if hasattr(cls, "__msco_pyarrow_struct__") and isinstance(
            cls.__msco_pyarrow_struct__, pa.StructType
        ):
            current_pa_fields = list(cls.__msco_pyarrow_struct__)

        # Collision Check
        existing_pa_names = [f.name for f in current_pa_fields]
        if "covariance" in existing_pa_names or "covariance_type" in existing_pa_names:
            raise ValueError(
                f"Class '{cls.__name__}' has conflicting 'covariance' or 'covariance_type' schema keys."
            )

        # Append and Update
        new_fields = current_pa_fields + _FIELDS
        cls.__msco_pyarrow_struct__ = pa.struct(new_fields)


# ---- VarianceMixin ----


class VarianceMixin(BaseModel):
    """
    A mixin that adds 1-dimensional uncertainty fields (`variance` and `variance_type`).

    Recommended for sensors with scalar uncertain outputs, such as ultrasonic
    rangefinders, temperature sensors, or individual encoders.

    ### Injected Fields
    * **`variance`**: Optional 64-bit float representing the variance of the data.
    * **`variance_type`**: Optional 16-bit integer representing the variance parameterization.

    Attributes:
        variance: Optional 64-bit float representing the variance of the data.
        variance_type: Optional 16-bit integer representing the variance parameterization.
    """

    variance: Optional[float] = None
    """Optional 64-bit float representing the variance of the data."""

    variance_type: Optional[int] = None
    """Optional 16-bit integer representing the variance parameterization."""

    def __init_subclass__(cls, **kwargs):
        """
        Dynamically appends variance-related fields to the child class's PyArrow struct.

        Raises:
            ValueError: If 'variance' or 'variance_type' keys collide with existing fields.
        """
        super().__init_subclass__(**kwargs)

        # Define the fields to inject
        _FIELDS = [
            pa.field(
                "variance",
                pa.float64(),
                nullable=True,
                metadata={"description": "The variance of the data."},
            ),
            pa.field(
                "variance_type",
                pa.int16(),
                nullable=True,
                metadata={
                    "description": "Enum integer representing the variance parameterization."
                },
            ),
        ]

        # Retrieve existing schema fields
        current_pa_fields = []
        if hasattr(cls, "__msco_pyarrow_struct__") and isinstance(
            cls.__msco_pyarrow_struct__, pa.StructType
        ):
            current_pa_fields = list(cls.__msco_pyarrow_struct__)

        # Collision Check
        existing_pa_names = [f.name for f in current_pa_fields]
        if "variance" in existing_pa_names or "variance_type" in existing_pa_names:
            raise ValueError(
                f"Class '{cls.__name__}' has conflicting 'variance' or 'variance_type' schema keys."
            )

        # Append and Update
        new_fields = current_pa_fields + _FIELDS
        cls.__msco_pyarrow_struct__ = pa.struct(new_fields)
