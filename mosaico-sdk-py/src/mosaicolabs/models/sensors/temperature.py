"""
Temperature Ontology Module.

Defines the data structure for temperature sensors.
"""

from typing import Optional
import pyarrow as pa

from ..mixins import HeaderMixin, VarianceMixin
from ..serializable import Serializable
from ..header import Header


class Temperature(Serializable, HeaderMixin, VarianceMixin):
    """
    Represents a thermodynamic temperature. The internal representation is always stored in **Kelvin (K)**.

    Users are encouraged to use the `from_*` factory methods when initializing
    temperature values expressed in units other than Kelvin.

    Parameters:
        value (float): Temperature value in **Kelvin (K)**. When using the constructor directly,
            the value **must** be provided in Kelvin.
    """

    # --- Schema Definition ---
    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "value",
                pa.float64(),
                nullable=False,
                metadata={"description": "Temperature value in Kelvin."},
            ),
        ]
    )

    value: float
    """Temperature value in Kelvin."""

    @classmethod
    def from_celsius(
        cls,
        *,
        value: float,
        header: Optional[Header] = None,
        variance: Optional[float] = None,
        variance_type: Optional[int] = None,
    ) -> "Temperature":
        """
        Creates a `Temperature` instance using the value in Celsius and converting it in Kelvin using the formula
        `Kelvin = Celsius + 273.15`.

        Args:
            value (float): The temperature value in Celsius.
            header (Optional[Header]): The standard metadata header (optional).
            variance (Optional[float]): The variance of the data.
            variance_type (Optional[int]): Enum integer representing the variance parameterization.

        Returns:
            Temperature: A `Temperature` instance with value in Kelvin.
        """
        value_in_kelvin = value + 273.15
        return cls(
            value=value_in_kelvin,
            header=header,
            variance=variance,
            variance_type=variance_type,
        )

    @classmethod
    def from_fahrenheit(
        cls,
        *,
        value: float,
        header: Optional[Header] = None,
        variance: Optional[float] = None,
        variance_type: Optional[int] = None,
    ) -> "Temperature":
        """
        Creates a `Temperature` instance using the value in Fahrenheit and converting it in Kelvin using the formula
        `Kelvin = (Fahrenheit - 32) * 5 / 9 + 273.15`.

        Args:
            value (float): The temperature value in Celsius.
            header (Optional[Header]): The standard metadata header (optional).
            variance (Optional[float]): The variance of the data.
            variance_type (Optional[int]): Enum integer representing the variance parameterization.

        Returns:
            Temperature: A `Temperature` instance with value in Kelvin.
        """
        value_in_kelvin = (value - 32) * 5 / 9 + 273.15
        return cls(
            value=value_in_kelvin,
            header=header,
            variance=variance,
            variance_type=variance_type,
        )

    def to_celsius(self) -> float:
        """
        Converts and returns the `Temperature` value in Celsius using the formula
        `Celsius = Kelvin - 273.15`.

        Returns:
            float: The `Temperature` value in Celsius.
        """
        return self.value - 273.15

    def to_fahrenheit(self) -> float:
        """
        Converts and returns the `Temperature` value in Fahrenheit using the formula
        `Fahrenheit = (Kelvin - 273.15) * 9 / 5 + 32`.

        Returns:
            float: The `Temperature` value in Fahrenheit.
        """
        return (self.value - 273.15) * 9 / 5 + 32
