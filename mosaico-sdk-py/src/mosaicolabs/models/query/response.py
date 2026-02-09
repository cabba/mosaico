from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Any

from mosaicolabs.helpers import unpack_topic_full_path

from .builders import QuerySequence, QueryTopic
from .expressions import _QuerySequenceExpression, _QueryTopicExpression


@dataclass
class TimestampRange:
    """
    Represents a temporal window defined by a start and end timestamp.

    This utility class is used to define the bounds of sensor data or sequences
    within the Mosaico archive.

    Attributes:
        start (int): The beginning of the range (inclusive), typically in nanoseconds.
        end (int): The end of the range (inclusive), typically in nanoseconds.
    """

    start: int
    end: int


@dataclass
class QueryResponseItemSequence:
    """
    Metadata container for a single sequence discovered during a query.

    Attributes:
        name (str): The unique identifier of the sequence in the Mosaico database.
    """

    name: str

    @classmethod
    def _from_dict(cls, qdict: dict[str, str]) -> "QueryResponseItemSequence":
        return cls(name=qdict["sequence"])


@dataclass
class QueryResponseItemTopic:
    """
    Metadata for a specific topic (sensor stream) within a sequence.

    Contains information about the topic's identity and its available
    time range in the archive.

    Attributes:
        name (str): The name of the topic (e.g., 'front_camera/image_raw').
        timestamp_range (Optional[TimestampRange]): The availability window of the data
            for this specific topic.
    """

    name: str
    timestamp_range: Optional[TimestampRange]

    @classmethod
    def _from_dict(cls, tdict: dict[str, Any]) -> "QueryResponseItemTopic":
        seq_topic_tuple = unpack_topic_full_path(tdict["locator"])
        if not seq_topic_tuple:
            raise ValueError(f"Invalid topic name in response '{tdict['locator']}'")
        _, tname = seq_topic_tuple
        tsrange = tdict.get("timestamp_range")

        return cls(
            name=tname,
            timestamp_range=TimestampRange(start=int(tsrange[0]), end=int(tsrange[1]))
            if tsrange
            else None,
        )


@dataclass
class QueryResponseItem:
    """
    A unified result item representing a sequence and its associated topics.

    This serves as the primary unit of data returned when querying the
    Mosaico metadata catalog.

    Attributes:
        sequence (QueryResponseItemSequence): The parent sequence metadata.
        topics (List[QueryResponseItemTopic]): The list of topics available
            within this sequence that matched the query criteria.
    """

    sequence: QueryResponseItemSequence
    topics: List[QueryResponseItemTopic]

    @classmethod
    def _from_dict(cls, qdict: dict[str, Any]) -> "QueryResponseItem":
        return cls(
            sequence=QueryResponseItemSequence._from_dict(qdict),
            topics=[
                QueryResponseItemTopic._from_dict(tdict) for tdict in qdict["topics"]
            ],
        )


@dataclass
class QueryResponse:
    """
    An iterable collection of results returned by a Mosaico metadata query.

    This class provides convenience methods to transform search results back into
    query builders, enabling a fluid, multi-stage filtering workflow.

    Example:
        ```python
        response = sdk.query_sequences(...)
        # Refine the query to only look at topics within these specific sequences
        next_query = response.to_query_topic()
        ```

    Attributes:
        items (List[QueryResponseItem]): The list of items matching the query.
    """

    # Use field(default_factory=list) to handle cases where no items are passed
    items: List[QueryResponseItem] = field(default_factory=list)

    def to_query_sequence(self) -> QuerySequence:
        """
        Converts the current response into a QuerySequence builder.

        This allows for further filtering or operations on the specific set of
        sequences returned in this response.

        Returns:
            QuerySequence: A builder initialized with an '$in' filter on the sequence names.

        Raises:
            ValueError: If the response is empty.
        """
        if not self.items:
            raise ValueError(
                "Cannot create a 'QuerySequence' builder from an empty response"
            )
        return QuerySequence(
            _QuerySequenceExpression(
                "name",
                "$in",
                [it.sequence.name for it in self.items],
            )
        )

    def to_query_topic(self) -> QueryTopic:
        """
        Converts the current response into a QueryTopic builder.

        Useful for narrowing down a search to specific topics found within
        the retrieved sequences.

        Returns:
            QueryTopic: A builder initialized with an '$in' filter on the topic names.

        Raises:
            ValueError: If the response is empty.
        """
        if not self.items:
            raise ValueError(
                "Cannot create a 'QueryTopic' builder from an empty response"
            )
        return QueryTopic(
            _QueryTopicExpression(
                "name",
                "$in",
                [t.name for it in self.items for t in it.topics],
            )
        )

    def __len__(self) -> int:
        """Returns the number of items in the response."""
        return len(self.items)

    def __iter__(self) -> Iterator[QueryResponseItem]:
        """Iterates over the QueryResponseItem instances in the response."""
        return iter(self.items)

    def __getitem__(self, index: int) -> QueryResponseItem:
        """Retrieves a specific result item by its index."""
        return self.items[index]

    def is_empty(self) -> bool:
        """Returns True if the response contains no results."""
        return len(self.items) == 0
