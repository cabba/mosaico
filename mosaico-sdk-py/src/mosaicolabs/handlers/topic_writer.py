"""
Topic Writing Module.

This module handles the buffered writing of data to a specific topic.
It abstracts the PyArrow Flight `DoPut` stream, handling batching,
serialization, and connection management.
"""

from concurrent.futures import ThreadPoolExecutor
import json
from typing import Any, Type, Optional
from mosaicolabs.models.header import Header
from mosaicolabs.models.message import Message
import pyarrow.flight as fl

from mosaicolabs.models import Serializable
from .internal.topic_write_state import _TopicWriteState
from .helpers import _make_exception
from ..helpers import pack_topic_resource_name
from ..comm.do_action import _do_action
from ..enum import FlightAction, OnErrorPolicy
from .config import WriterConfig
from ..logging_config import get_logger

# Set the hierarchical logger
logger = get_logger(__name__)


class TopicWriter:
    """
    Manages a high-performance data stream for a single Mosaico topic.

    The `TopicWriter` abstracts the complexity of the PyArrow Flight `DoPut` protocol,
    handling internal buffering, serialization, and network transmission.
    It accumulates records in memory and automatically flushes them to the server when
    configured batch limits—defined by either byte size or record count—are exceeded.

    ### Performance & Parallelism
    If an executor pool is provided by the parent client, the `TopicWriter` performs
    data serialization on background threads, preventing I/O operations from blocking
    the main application logic.

    Important: Obtaining a Writer
        End-users should not instantiate this class directly. Use the
        [`SequenceWriter.topic_create()`][mosaicolabs.handlers.SequenceWriter.topic_create]
        factory method to obtain an active writer.
    """

    def __init__(
        self,
        *,
        topic_name: str,
        sequence_name: str,
        client: fl.FlightClient,
        state: _TopicWriteState,
        config: WriterConfig,
    ):
        """
        Internal constructor for TopicWriter.

        **Do not call this directly.** Internal library modules should use the
        [`create()`][mosaicolabs.handlers.TopicWriter.create] factory.
        Users must call
        [`SequenceWriter.topic_create()`][mosaicolabs.handlers.SequenceWriter.topic_create]
        to obtain an initialized writer.

        Args:
            topic_name: The name of the specific topic.
            sequence_name: The name of the parent sequence.
            client: The FlightClient used for data transmission.
            state: The internal state object managing buffers and streams.
            config: Operational configuration for batching and error handling.
        """
        self._fl_client: fl.FlightClient = client
        """The FlightClient used for writing operations."""
        self._sequence_name: str = sequence_name
        """The name of the created sequence"""
        self._name: str = topic_name
        """The name of the new topic"""
        self._config: WriterConfig = config
        """The config of the writer"""
        self._wrstate: _TopicWriteState = state
        """The actual writer object"""

    @classmethod
    def create(
        cls,
        sequence_name: str,
        topic_name: str,
        topic_key: str,
        client: fl.FlightClient,
        executor: Optional[ThreadPoolExecutor],
        ontology_type: Type[Serializable],
        config: WriterConfig,
    ) -> "TopicWriter":
        """
        Internal Factory method to initialize an active TopicWriter.

        This method performs the underlying handshake with the Mosaico server to
        open a `DoPut` stream and initializes the memory buffers based on the
        provided ontology type.

        Important: **Do not call this directly**
            Users must call
            [`SequenceWriter.topic_create()`][mosaicolabs.handlers.SequenceWriter.topic_create]
            to obtain an initialized writer.

        Args:
            sequence_name: Name of the parent sequence.
            topic_name: Unique name for this topic stream.
            topic_key: authorization key provided by the server during creation.
            client: The connection to use for the data stream.
            executor: Optional thread pool for background serialization.
            ontology_type: The data model class defining the record schema.
            config: Batching limits and error policies.

        Returns:
            An active `TopicWriter` instance ready for data ingestion.

        Raises:
            ValueError: If the ontology type is not a valid `Serializable` subclass.
            Exception: If the Flight stream fails to open on the server.
        """
        # Validate Ontology Class requirements (must have tags and serialization format)
        cls._validate_ontology_type(ontology_type)

        # Create Flight Descriptor: Tells server where to route the data
        descriptor = fl.FlightDescriptor.for_command(
            json.dumps(
                {
                    "resource_locator": pack_topic_resource_name(
                        sequence_name, topic_name
                    ),
                    "key": topic_key,
                }
            )
        )

        # Open Flight Stream (DoPut)
        try:
            writer, _ = client.do_put(descriptor, Message._get_schema(ontology_type))
        except Exception as e:
            raise _make_exception(
                f"Failed to open Flight stream for topic '{topic_name}'", e
            )

        assert ontology_type.__ontology_tag__ is not None

        # Initialize Internal Write State (manages the buffer and flushing logic)
        wrstate = _TopicWriteState(
            topic_name=topic_name,
            ontology_tag=ontology_type.__ontology_tag__,
            writer=writer,
            executor=executor,
            max_batch_size_bytes=config.max_batch_size_bytes,
            max_batch_size_records=config.max_batch_size_records,
        )

        return cls(
            topic_name=topic_name,
            sequence_name=sequence_name,
            client=client,
            state=wrstate,
            config=config,
        )

    # --- Context Manager ---
    def __enter__(self) -> "TopicWriter":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Context manager exit.

        Guarantees cleanup of the Flight stream. If an exception occurred within
        the block, it triggers the configured `OnErrorPolicy` (e.g., reporting the error).
        Exceptions from the with-block are always propagated.
        """
        error_occurred = exc_type is not None

        try:
            # Attempt to flush remaining data and close stream
            self.finalize(with_error=error_occurred)
        except Exception as e:
            # FINALIZE FAILED: treat this as an error condition
            logger.exception(f"Failed to finalize topic '{self._name}': '{e}'")
            error_occurred = True
            if not exc_type:
                exc_type, exc_val = type(e), e

        if error_occurred:
            # Exit due to an error (original, cleanup, or finalize failure)
            try:
                if self._config.on_error == OnErrorPolicy.Report:
                    self._error_report(str(exc_val))
            except Exception as e:
                logger.exception(
                    f"Error handling topic '{self._name}' after exception: '{e}'"
                )

    def __del__(self):
        """Destructor check to ensure `finalize()` was called."""
        name = getattr(self, "_name", "__not_initialized__")
        if hasattr(self, "finalized") and not self.finalized():
            logger.warning(
                f"TopicWriter '{name}' destroyed without calling finalize(). "
                "Resources may not have been released properly."
            )

    def _handle_exception_and_raise(self, err: Exception, msg: str):
        """Helper to cleanup resources and re-raise exceptions with context."""
        try:
            if self._config.on_error == OnErrorPolicy.Report:
                self._error_report(str(err))
        except Exception as report_err:
            logger.error(f"Failed to report error: '{report_err}'")
        finally:
            # Always attempt to close local resources
            if hasattr(self, "_wrstate") and self._wrstate:
                self._wrstate.close(with_error=True)

        raise _make_exception(f"Topic '{self._name}' operation failed: '{msg}'", err)

    @classmethod
    def _validate_ontology_type(cls, ontology_type: Type[Serializable]) -> None:
        if not issubclass(ontology_type, Serializable):
            raise ValueError(
                f"Ontology class '{ontology_type.__name__}' is not serializable."
            )

    def _error_report(self, err: str):
        """Sends an 'error' notification to the server regarding this topic."""
        try:
            _do_action(
                client=self._fl_client,
                action=FlightAction.TOPIC_NOTIFY_CREATE,
                payload={
                    "name": pack_topic_resource_name(self._sequence_name, self._name),
                    "notify_type": "error",
                    "msg": str(err),
                },
                expected_type=None,
            )
            logger.info(f"TopicWriter '{self._name}' reported error.")
        except Exception as e:
            raise _make_exception(
                f"Error sending 'topic_report_error' action for sequence '{self._name}'.",
                e,
            )

    # --- Writing Logic ---
    def push(
        self,
        message: Optional[Message] = None,
        message_timestamp_ns: Optional[int] = None,
        message_header: Optional[Header] = None,
        ontology_obj: Optional[Serializable] = None,
    ) -> None:
        """
        Adds a new record to the internal write buffer.

        Records are accumulated in memory. If a push triggers a batch limit,
        the buffer is automatically serialized and transmitted to the server.

        Note: Input Modes
            You can provide a single [`Message`][mosaicolabs.models.Message] object
            **OR** provide the discrete components (`ontology_obj`, `message_timestamp_ns`
            and `message_header`).

        Args:
            message: A pre-constructed Message object.
            message_timestamp_ns: Absolute timestamp in **nanoseconds**.
            message_header: Optional metadata header for the record.
            ontology_obj: The actual data payload instance (e.g., a GPS or IMU object).

        Raises:
            ValueError: If neither a Message nor the required discrete components are provided.
            Exception: If a buffer flush fails during the operation.
        """
        msg = message
        if not msg:
            if message_timestamp_ns is not None and ontology_obj is not None:
                msg = Message(
                    timestamp_ns=message_timestamp_ns,
                    data=ontology_obj,
                    message_header=message_header,
                )
            else:
                raise ValueError(
                    "Expected a valid message or the couple 'message_timestamp_ns' + 'ontology_obj'."
                )

        try:
            self._wrstate.push_record(msg)
        except Exception as e:
            self._handle_exception_and_raise(e, "Error during TopicWriter.push")

    def finalized(self) -> bool:
        """
        Returns `True` if the data stream has been finalized and the writer is closed.
        """
        return self._wrstate.writer is None

    def finalize(self, with_error: bool = False) -> None:
        """
        Flushes all remaining buffered data and closes the remote Flight stream.

        This method ensures that any data residing in the local memory buffer is sent to the
        server before the connection is severed.

        Note: Automatic Finalization
            In typical workflows, you do not need to call this manually. It is
            **automatically invoked** by the `__exit__` method of the parent
            [`SequenceWriter`][mosaicolabs.handlers.SequenceWriter] when the `with` block scope is closed.

        Args:
            with_error: If `True`, the writer closes without attempting to flush
                incomplete buffers. This is typically used by the
                [`SequenceWriter`][mosaicolabs.handlers.SequenceWriter] during error cleanup
                to avoid sending potentially corrupted data.

        Raises:
            Exception: If the server fails to acknowledge the stream closure or a
                final buffer flush fails.
        """
        try:
            self._wrstate.close(with_error=with_error)
        except Exception:
            raise

        logger.info(
            f"TopicWriter '{self._name}' finalized {'WITH ERROR' if with_error else ''} successfully."
        )
