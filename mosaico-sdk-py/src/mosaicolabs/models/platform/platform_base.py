"""
Platform Entity Base Module.

This module defines `PlatformBase`, the foundational class for the main catalog entities,
Sequences and Topics, within the SDK. It consolidates shared system attributes
(like creation time, locks, and size) and integrates with the Pydantic validation
system and the internal Query API.
"""

import datetime
from typing import Any, Dict

from pydantic import PrivateAttr
import pydantic
from ..query.generation.api import _QueryableModel


class PlatformBase(pydantic.BaseModel, _QueryableModel):
    """
    Base class for Mosaico Sequence and Topic entities.

    The `PlatformBase` serves as a read-only view of a server-side resource.
    It is designed to hold system-level metadata and enable fluid querying of
    user-defined properties.


    ### Core Functionality
    1.  **System Metadata**: Consolidates attributes like storage size and locking
        status that are common across the catalog.
    2.  **Query Interface**: Inherits from `_QueryableModel` to support expressive
        syntax for filtering resources (e.g., `Sequence.Q.user_metadata["env"] == "prod"`).

    Note: Read-Only Entities
        Instances of this class are factory-generated from server responses.
        Users should not instantiate this class directly.

    Attributes:
        user_metadata: A dictionary of custom key-value pairs assigned by the user.
    """

    user_metadata: Dict[str, Any]
    """Custom user-defined key-value pairs associated with the entity."""

    # --- Private Attributes ---
    # These fields are managed internally and populated via _init_base_private.
    # They are excluded from the standard Pydantic __init__ to prevent users
    # from manually setting system-controlled values.
    _is_locked: bool = PrivateAttr(default=False)
    _total_size_bytes: int = PrivateAttr()
    _created_datetime: datetime.datetime = PrivateAttr()
    _name: str = PrivateAttr()

    def _init_base_private(
        self,
        *,
        name: str,
        total_size_bytes: int,
        created_datetime: datetime.datetime,
        is_locked: bool = False,
    ) -> None:
        """
        Internal helper to populate system-controlled private attributes.

        This is used by factory methods (`from_flight_info`) to set attributes
        that are strictly read-only for the user.

        Args:
            name: The unique resource name.
            total_size_bytes: The storage size on the server.
            created_datetime: The UTC timestamp of creation.
            is_locked: Whether the resource is currently locked (e.g., during writing).
        """
        self._is_locked = is_locked
        self._total_size_bytes = total_size_bytes
        self._created_datetime = created_datetime or datetime.datetime.utcnow()
        self._name = name or ""

    # --- Shared Properties ---
    @property
    def name(self) -> str:
        """The unique identifier or resource name of the entity."""
        return self._name

    @property
    def created_datetime(self) -> datetime.datetime:
        """The UTC timestamp indicating when the entity was created on the server."""
        return self._created_datetime

    @property
    def is_locked(self) -> bool:
        """
        Indicates if the resource is currently locked.

        A locked state typically occurs during active writing or maintenance operations,
        preventing deletion or structural modifications.
        """
        return self._is_locked

    @property
    def total_size_bytes(self) -> int:
        """The total physical storage footprint of the entity on the server in bytes."""
        return self._total_size_bytes
