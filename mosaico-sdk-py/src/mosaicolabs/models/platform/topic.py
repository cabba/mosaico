"""
Topic Catalog Entity.

This module defines the `Topic` class, which represents a read-only view of a
Topic's metadata in the platform catalog. It is used primarily for inspection
(listing topics) and query construction.
"""

from typing import Any, Optional

from pydantic import PrivateAttr
from ..query.generation.api import queryable
from ..query.generation.pydantic_mapper import PydanticFieldMapper
from ..query.expressions import _QueryTopicExpression

from .platform_base import PlatformBase


@queryable(
    mapper_type=PydanticFieldMapper,
    prefix="",
    query_expression_type=_QueryTopicExpression,
)
class Topic(PlatformBase):
    """
    Represents a read-only view of a server-side Topic platform resource.

    The `Topic` class provides access to topic-specific system metadata, such as the ontology tag (e.g., 'imu', 'camera') and the serialization format.
    It serves as a metadata-rich view of an individual data stream within the platform catalog.

    Important: Data Retrieval
        This class provides a **metadata-only** view of the topic.
        To retrieve the actual time-series messages contained within the topic, you must
        use the [`TopicHandler.get_data_streamer()`][mosaicolabs.handlers.TopicHandler.get_data_streamer]
        method from a [`TopicHandler`][mosaicolabs.handlers.TopicHandler]
        instance.

    ### Querying with the `.Q` Proxy
    The `user_metadata` field of this class is queryable when constructing a [`QueryTopic`][mosaicolabs.models.query.QueryTopic]
    via the **`.Q` proxy**. Check the fields documentation for detailed description.

    Example:
        ```python
        # Filter for a specific data value (using constructor)
        qbuilder = QueryTopic(
            Topic.Q.user_metadata["update_rate_hz"].eq(100), # Access the keys using the [] operator
            Topic.Q.user_metadata["interface.type"].eq("canbus"), # Navigate the nested dicts using the dot notation
        )

        # The same builder using `with_expression`
        qbuilder = (
            QueryTopic()
            .with_expression(Topic.Q.user_metadata["update_rate_hz"].eq(100))
            .with_expression(
                Topic.Q.user_metadata["interface.type"].match("canbus")
            )
        )
        ```
    """

    # --- Private Fields (Internal State) ---
    _sequence_name: str = PrivateAttr()
    _ontology_tag: str = PrivateAttr()
    _serialization_format: str = PrivateAttr()
    _chunks_number: Optional[int] = PrivateAttr(default=None)

    # --- Factory Method ---
    @classmethod
    def from_flight_info(
        cls, sequence_name: str, name: str, metadata: Any, sys_info: Any
    ) -> "Topic":
        """
        Internal factory method to construct a Topic model from Flight protocol objects.

        This method adapts low-level protocol responses into the high-level
        Catalog model.

        Args:
            sequence_name: The parent sequence identifier.
            name: The full resource name of the topic.
            metadata: Decoded topic metadata (properties and user metadata).
            sys_info: System diagnostic information.

        Returns:
            An initialized, read-only `Topic` model.
        """
        # Create the instance with public fields.
        # Note: metadata.user_metadata comes flat from the server; we unflatten it
        # to restore nested dictionary structures for the user.
        instance = cls(
            user_metadata=metadata.user_metadata,
        )

        # Set private attributes explicitly via the base helper
        instance._init_base_private(
            name=name,
            created_datetime=sys_info.created_datetime,
            is_locked=sys_info.is_locked,
            total_size_bytes=sys_info.total_size_bytes,
        )

        # Set local private attributes
        instance._sequence_name = sequence_name
        instance._ontology_tag = metadata.properties.ontology_tag
        instance._serialization_format = metadata.properties.serialization_format
        instance._chunks_number = sys_info.chunks_number

        return instance

    # --- Properties ---
    @property
    def ontology_tag(self) -> str:
        """
        The ontology type identifier (e.g., 'imu', 'gnss').

        This corresponds to the `__ontology_tag__` defined in the
        [`Serializable`][mosaicolabs.models.Serializable] class registry.
        """
        return self._ontology_tag

    @property
    def sequence_name(self) -> str:
        """The name of the parent sequence containing this topic."""
        return self._sequence_name

    @property
    def chunks_number(self) -> Optional[int]:
        """
        The number of physical data chunks stored for this topic.

        May be `None` if the server did not provide detailed storage statistics.
        """
        return self._chunks_number

    @property
    def serialization_format(self) -> str:
        """
        The format used to serialize the topic data (e.g., 'arrow', 'image').

        This corresponds to the [`SerializationFormat`][mosaicolabs.enum.SerializationFormat] enum.
        """
        return self._serialization_format
