"""
This module provides specialized wrapper classes for standard Python primitive types, including Integers, Floating-point numbers, Booleans, and Strings.

In the Mosaico ecosystem, raw primitives cannot be transmitted directly because the platform requires structured metadata and explicit serialization schemas.
These wrappers elevate basic data types to "first-class citizens" of the messaging system by inheriting from [`Serializable`][mosaicolabs.models.serializable.Serializable]
and [`HeaderMixin`][mosaicolabs.models.mixins.HeaderMixin].

**Key Features:**
* **Standardized Metadata**: Every wrapped value includes a standard [`Header`][mosaicolabs.models.header.Header], enabling full traceability and temporal context (timestamps) for even the simplest data points.
* **Explicit Serialization**: Each class defines a precise `pyarrow.StructType` schema, ensuring consistent bit-width (e.g., 8-bit vs 64-bit) across the entire data platform.
* **Registry Integration**: Wrapped types are automatically registered in the Mosaico ontology, allowing them to be used in platform-side [Queries][mosaicolabs.comm.MosaicoClient.query].
"""

from typing import Any
import pyarrow as pa

from ..serializable import Serializable
from ..mixins import HeaderMixin


class Integer8(Serializable, HeaderMixin):
    """
    A wrapper for a signed 8-bit integer.

    Attributes:
        data: The underlying 8-bit integer value.
        header: An optional metadata header injected by `HeaderMixin`.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.int8(),
                nullable=False,
                metadata={"description": "8-bit Integer data"},
            ),
        ]
    )
    data: int


class Integer16(Serializable, HeaderMixin):
    """
    A wrapper for a signed 16-bit integer.

    Attributes:
        data: The underlying 16-bit integer value.
        header: An optional metadata header injected by `HeaderMixin`.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.int16(),
                nullable=False,
                metadata={"description": "16-bit Integer data"},
            ),
        ]
    )
    data: int


class Integer32(Serializable, HeaderMixin):
    """
    A wrapper for a signed 32-bit integer.

    Attributes:
        data: The underlying 32-bit integer value.
        header: An optional metadata header injected by `HeaderMixin`.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.int32(),
                nullable=False,
                metadata={"description": "32-bit Integer data"},
            ),
        ]
    )
    data: int


class Integer64(Serializable, HeaderMixin):
    """
    A wrapper for a signed 64-bit integer.

    Attributes:
        data: The underlying 64-bit integer value.
        header: An optional metadata header injected by `HeaderMixin`.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.int64(),
                nullable=False,
                metadata={"description": "64-bit Integer data"},
            ),
        ]
    )
    data: int


class Unsigned8(Serializable, HeaderMixin):
    """
    A wrapper for an unsigned 8-bit integer.

    Attributes:
        data: The underlying unsigned 8-bit integer value.

    Raises:
        ValueError: If `data` is initialized with a negative value.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.uint8(),
                nullable=False,
                metadata={"description": "8-bit Unsigned data"},
            ),
        ]
    )
    data: int

    def model_post_init(self, context: Any) -> None:
        """
        Validates that the input data is non-negative.

        Raises:
            ValueError: If data < 0.
        """
        super().model_post_init(context)
        if self.data < 0:
            raise ValueError("Integer must be unsigned")


class Unsigned16(Serializable, HeaderMixin):
    """
    A wrapper for an unsigned 16-bit integer.

    Attributes:
        data: The underlying unsigned 16-bit integer value.

    Raises:
        ValueError: If `data` is initialized with a negative value.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.uint16(),
                nullable=False,
                metadata={"description": "16-bit Unsigned data"},
            ),
        ]
    )
    data: int

    def model_post_init(self, context: Any) -> None:
        """
        Validates that the input data is non-negative.

        Raises:
            ValueError: If data < 0.
        """
        super().model_post_init(context)
        if self.data < 0:
            raise ValueError("Integer must be unsigned")


class Unsigned32(Serializable, HeaderMixin):
    """
    A wrapper for an unsigned 32-bit integer.

    Attributes:
        data: The underlying unsigned 32-bit integer value.

    Raises:
        ValueError: If `data` is initialized with a negative value.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.uint32(),
                nullable=False,
                metadata={"description": "32-bit Unsigned data"},
            ),
        ]
    )
    data: int

    def model_post_init(self, context: Any) -> None:
        """
        Validates that the input data is non-negative.

        Raises:
            ValueError: If data < 0.
        """
        super().model_post_init(context)
        if self.data < 0:
            raise ValueError("Integer must be unsigned")


class Unsigned64(Serializable, HeaderMixin):
    """
    A wrapper for an unsigned 64-bit integer.

    Attributes:
        data: The underlying unsigned 64-bit integer value.

    Raises:
        ValueError: If `data` is initialized with a negative value.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.uint64(),
                nullable=False,
                metadata={"description": "64-bit Unsigned data"},
            ),
        ]
    )
    data: int

    def model_post_init(self, context: Any) -> None:
        """
        Validates that the input data is non-negative.

        Raises:
            ValueError: If data < 0.
        """
        super().model_post_init(context)
        if self.data < 0:
            raise ValueError("Integer must be unsigned")


class Floating16(Serializable, HeaderMixin):
    """
    A wrapper for a 16-bit single-precision floating-point number.

    Attributes:
        data: The underlying single-precision float.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.float16(),
                nullable=False,
                metadata={"description": "16-bit Floating-point data"},
            ),
        ]
    )
    data: float


class Floating32(Serializable, HeaderMixin):
    """
    A wrapper for a 32-bit single-precision floating-point number.

    Attributes:
        data: The underlying single-precision float.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.float32(),
                nullable=False,
                metadata={"description": "32-bit Floating-point data"},
            ),
        ]
    )
    data: float


class Floating64(Serializable, HeaderMixin):
    """
    A wrapper for a 64-bit single-precision floating-point number.

    Attributes:
        data: The underlying single-precision float.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.float64(),
                nullable=False,
                metadata={"description": "64-bit Floating-point data"},
            ),
        ]
    )
    data: float


class Boolean(Serializable, HeaderMixin):
    """
    A wrapper for a standard boolean value.

    Attributes:
        data: The underlying boolean value.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.bool_(),
                nullable=False,
                metadata={"description": "Boolean data"},
            ),
        ]
    )
    data: bool


class String(Serializable, HeaderMixin):
    """
    A wrapper for a standard UTF-8 encoded string.

    Attributes:
        data: The underlying string data.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.string(),
                nullable=False,
                metadata={"description": "String data"},
            ),
        ]
    )
    data: str


class LargeString(Serializable, HeaderMixin):
    """
    A wrapper for a Large UTF-8 encoded string.

    Use this class when string data is expected to exceed 2GB in size, necessitating
    the use of 64-bit offsets in the underlying PyArrow implementation.

    Attributes:
        data: The underlying large string data.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "data",
                pa.large_string(),
                nullable=False,
                metadata={"description": "Large string data"},
            ),
        ]
    )
    data: str
