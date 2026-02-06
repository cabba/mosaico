"""
GNSS/GPS Ontology Module.

This module defines data structures for Global Navigation Satellite Systems.
It includes Status flags, processed Fixes (Position/Velocity), and raw NMEA strings.

"""

from typing import Optional
import pyarrow as pa

from ..data import Point3d, Vector3d
from ..mixins import HeaderMixin
from ..serializable import Serializable


class GPSStatus(Serializable, HeaderMixin):
    """
    Status of the GNSS receiver and satellite fix.

    This class encapsulates quality metrics and operational state of the GNSS receiver,
    including fix type, satellite usage, and precision dilution factors.

    Attributes:
        status: Fix status indicator (e.g., No Fix, 2D, 3D).
        service: Service used for the fix (e.g., GPS, GLONASS, Galileo).
        satellites: Number of satellites currently visible or used in the solution.
        hdop: Horizontal Dilution of Precision (lower is better).
        vdop: Vertical Dilution of Precision (lower is better).
        header: Standard metadata providing temporal and spatial reference.

    ### Querying with the `.Q` Proxy
    This class is fully queryable via the **`.Q` proxy**. You can filter status data based
    on fix quality or precision metrics within a [`QueryOntologyCatalog`][mosaicolabs.models.query.builders.QueryOntologyCatalog].

    **Example:**
    ```python
    # Filter for high-quality fixes (low HDOP)
    query = QueryOntologyCatalog(GPSStatus.Q.hdop.lt(2.0))
    ```
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "status",
                pa.int8(),
                nullable=False,
                metadata={"description": "Fix status."},
            ),
            pa.field(
                "service",
                pa.uint16(),
                nullable=False,
                metadata={"description": "Service used (GPS, GLONASS, etc)."},
            ),
            pa.field(
                "satellites",
                pa.int8(),
                nullable=True,
                metadata={"description": "Satellites visible/used."},
            ),
            pa.field(
                "hdop",
                pa.float64(),
                nullable=True,
                metadata={"description": "Horizontal Dilution of Precision."},
            ),
            pa.field(
                "vdop",
                pa.float64(),
                nullable=True,
                metadata={"description": "Vertical Dilution of Precision."},
            ),
        ]
    )

    status: int
    """
    Fix status.

    ### Querying with the `.Q` Proxy
    The fix status is queryable via the `status` field.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPSStatus.Q.status` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for valid fixes
    query = QueryOntologyCatalog(GPSStatus.Q.status.gt(0))
    ```
    """

    service: int
    """
    Service used (GPS, GLONASS, etc).

    ### Querying with the `.Q` Proxy
    The service identifier is queryable via the `service` field.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPSStatus.Q.service` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for specific service ID
    query = QueryOntologyCatalog(GPSStatus.Q.service.eq(1))
    ```
    """

    satellites: Optional[int] = None
    """
    Satellites visible/used.

    ### Querying with the `.Q` Proxy
    Satellite count is queryable via the `satellites` field.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPSStatus.Q.satellites` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for fixes with at least 6 satellites
    query = QueryOntologyCatalog(GPSStatus.Q.satellites.geq(6))
    ```
    """

    hdop: Optional[float] = None
    """
    Horizontal Dilution of Precision.

    ### Querying with the `.Q` Proxy
    HDOP values are queryable via the `hdop` field.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPSStatus.Q.hdop` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for excellent horizontal precision
    query = QueryOntologyCatalog(GPSStatus.Q.hdop.lt(1.5))
    ```
    """

    vdop: Optional[float] = None
    """
    Vertical Dilution of Precision.

    ### Querying with the `.Q` Proxy
    VDOP values are queryable via the `vdop` field.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPSStatus.Q.vdop` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for good vertical precision
    query = QueryOntologyCatalog(GPSStatus.Q.vdop.lt(2.0))
    ```
    """


class GPS(Serializable, HeaderMixin):
    """
    Processed GNSS fix containing Position, Velocity, and Status.

    This class serves as the primary container for geodetic location data (WGS 84)
    and receiver state information.

    Attributes:
        position: Lat/Lon/Alt (WGS 84) represented as a [`Point3d`][mosaicolabs.models.data.geometry.Point3d].
        velocity: Velocity vector [North, East, Alt] in $m/s$.
        status: Receiver status info including fix type and satellite count.
        header: Standard metadata providing temporal and spatial reference.

    ### Querying with the `.Q` Proxy
    This class is fully queryable via the **`.Q` proxy**. You can filter GPS data based
    on geodetic coordinates or signal quality within a [`QueryOntologyCatalog`][mosaicolabs.models.query.builders.QueryOntologyCatalog].

    **Example:**
    ```python
    # Find data collected above 1000m altitude
    query = QueryOntologyCatalog(GPS.Q.position.z.gt(1000.0))
    ```
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "position",
                Point3d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "Lat/Lon/Alt (WGS 84)."},
            ),
            pa.field(
                "velocity",
                Vector3d.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "Velocity vector [North, East, Alt] m/s."},
            ),
            pa.field(
                "status",
                GPSStatus.__msco_pyarrow_struct__,
                nullable=True,
                metadata={"description": "Receiver status info."},
            ),
        ]
    )

    position: Point3d
    """
    Lat/Lon/Alt (WGS 84).

    ### Querying with the `.Q` Proxy
    Position components are queryable through the `position` field prefix.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPS.Q.position.x` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.position.y` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.position.z` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for a specific latitude range
    query = QueryOntologyCatalog(GPS.Q.position.x.between([45.0, 46.0]))
    ```
    """

    velocity: Optional[Vector3d] = None
    """
    Velocity vector [North, East, Alt] m/s.

    ### Querying with the `.Q` Proxy
    Velocity components are queryable through the `velocity` field prefix.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPS.Q.velocity.x` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.velocity.y` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.velocity.z` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for high vertical velocity
    query = QueryOntologyCatalog(GPS.Q.velocity.z.gt(5.0))
    ```
    """

    status: Optional[GPSStatus] = None
    """
    Receiver status information.

    ### Querying with the `.Q` Proxy
    Status components are queryable through the `status` field prefix.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `GPS.Q.status.satellites` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.status.hdop` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.status.vdop` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.status.status` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `GPS.Q.status.service` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for high-precision fixes with at least 8 satellites
    query = QueryOntologyCatalog(GPS.Q.status.satellites.geq(8))
    ```
    """


class NMEASentence(Serializable, HeaderMixin):
    """
    Raw NMEA 0183 sentence string.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "sentence",
                pa.string(),
                nullable=False,
                metadata={"description": "Raw ASCII sentence."},
            ),
        ]
    )

    sentence: str
    """Raw ASCII sentence."""
