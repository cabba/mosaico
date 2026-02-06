import pyarrow as pa
from typing import Optional

from ..serializable import Serializable
from ..mixins import HeaderMixin
from .geometry import Vector2d


class ROI(Serializable, HeaderMixin):
    """
    Represents a rectangular Region of Interest (ROI) within a 2D coordinate system.

    This class is primarily used in imaging and computer vision pipelines to define
    sub-windows for processing or rectification.


    Attributes:
        offset: A [`Vector2d`][mosaicolabs.models.data.geometry.Vector2d] representing
            the top-left (leftmost, topmost) pixel coordinates of the ROI.
        height: The vertical extent of the ROI in pixels.
        width: The horizontal extent of the ROI in pixels.
        do_rectify: Optional flag; `True` if a sub-window is captured and requires
            rectification.
        header: Standard metadata header providing temporal and spatial context.
    """

    __msco_pyarrow_struct__ = pa.struct(
        [
            pa.field(
                "offset",
                Vector2d.__msco_pyarrow_struct__,
                nullable=False,
                metadata={"description": "(Leftmost, Rightmost) pixels of the ROI."},
            ),
            pa.field(
                "height",
                pa.uint32(),
                nullable=False,
                metadata={"description": "Height pixel of the ROI."},
            ),
            pa.field(
                "width",
                pa.uint32(),
                nullable=False,
                metadata={"description": "Width pixel of the ROI."},
            ),
            pa.field(
                "do_rectify",
                pa.bool_(),
                nullable=True,
                metadata={
                    "description": "False if the full image is captured (ROI not used)"
                    " and True if a subwindow is captured (ROI used) (optional). False if Null"
                },
            ),
        ]
    )

    offset: Vector2d
    """
    The top-left pixel coordinates of the ROI.

    ### Querying with the `.Q` Proxy
    Offset components are queryable through the `offset` field prefix.

    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `ROI.Q.offset.x` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |
    | `ROI.Q.offset.y` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for ROIs starting between the 10th and 350th pixel vertically
    query = QueryOntologyCatalog(ROI.Q.offset.x.gt(100))
            .with_expression(ROI.Q.offset.y.between(10, 350))
    ```
    """

    height: int
    """
    Height of the ROI in pixels.

    ### Querying with the `.Q` Proxy
    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `ROI.Q.height` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for ROIs with height beyond 100 pixels
    query = QueryOntologyCatalog(ROI.Q.height.gt(100))
    ```
    """

    width: int
    """
    Width of the ROI in pixels.

    ### Querying with the `.Q` Proxy
    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `ROI.Q.width` | `Numeric` | `.eq()`, `.neq()`, `.lt()`, `.gt()`, `.leq()`, `.geq()`, `.in_()`, `.between()` |

    **Example:**
    ```python
    # Filter for ROIs with width below (or equal to) 250 pixels
    query = QueryOntologyCatalog(ROI.Q.width.leq(250))
    ```
    """

    do_rectify: Optional[bool] = None
    """
    Flag indicating if the ROI requires rectification.

    ### Querying with the `.Q` Proxy
    | Field Access Path | Queryable Type | Supported Operators |
    | :--- | :--- | :--- |
    | `ROI.Q.do_rectify` | `Boolean` | `.eq()`, `.is_null()` |

    **Example:**
    ```python
    # Filter for explicitly non-rectified ROIs (not None)
    query = QueryOntologyCatalog(ROI.Q.do_rectify.eq(False))
    ```
    """
