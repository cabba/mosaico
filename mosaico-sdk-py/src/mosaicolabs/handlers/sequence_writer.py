"""
Sequence Writing Module.

This module acts as the central controller for writing a sequence of data.
It manages the lifecycle of the sequence on the server (Create -> Write -> Finalize)
and distributes client resources (Connections, Executors) to individual Topics.
"""

from typing import Any, Optional
import pyarrow.flight as fl

from .config import WriterConfig
from .helpers import _validate_sequence_name
from ..comm.do_action import _do_action, _DoActionResponseKey
from ..comm.connection import _ConnectionPool
from ..comm.executor_pool import _ExecutorPool
from ..enum import FlightAction, SequenceStatus
from ..logging_config import get_logger
from .base_sequence_writer import BaseSequenceWriter

# Set the hierarchical logger
logger = get_logger(__name__)


class SequenceWriter(BaseSequenceWriter):
    """
    Orchestrates the creation and data ingestion lifecycle of a Mosaico Sequence.

    The `SequenceWriter` is the central controller for high-performance data writing.
    It manages the transition of a sequence through its lifecycle states: **Create** -> **Write** -> **Finalize**.

    ### Key Responsibilities
    * **Lifecycle Management**: Coordinates creation, finalization, or abort signals with the server.
    * **Resource Distribution**: Implements a "Multi-Lane" architecture by distributing network connections
        from a Connection Pool and thread executors from an Executor Pool to individual
        [`TopicWriter`][mosaicolabs.handlers.TopicWriter]
        instances. This ensures strict isolation and maximum parallelism between
        diverse data streams.


    Important: Usage Pattern
        This class **must** be used within a `with` statement (Context Manager).
        The context entry triggers sequence registration on the server, while the exit handles
        automatic finalization or error cleanup based on the configured `OnErrorPolicy`.

    Important: Obtaining a Writer
        Do not instantiate this class directly. Use the
        [`MosaicoClient.sequence_create()`][mosaicolabs.comm.MosaicoClient.sequence_create]
        factory method.
    """

    # -------------------- Constructor --------------------
    def __init__(
        self,
        *,
        sequence_name: str,
        client: fl.FlightClient,
        connection_pool: Optional[_ConnectionPool],
        executor_pool: Optional[_ExecutorPool],
        metadata: dict[str, Any],
        config: WriterConfig,
    ):
        """
        Internal constructor for SequenceWriter.

        **Do not call this directly.** Users must call
        [`MosaicoClient.sequence_create()`][mosaicolabs.comm.MosaicoClient.sequence_create]
        to obtain an initialized writer.

        Args:
            sequence_name: Unique name for the new sequence.
            client: The primary control FlightClient.
            connection_pool: Shared pool of data connections for parallel writing.
            executor_pool: Shared pool of thread executors for asynchronous I/O.
            metadata: User-defined metadata dictionary.
            config: Operational configuration (e.g., error policies, batch sizes).
        """
        _validate_sequence_name(sequence_name)
        self._metadata: dict[str, Any] = metadata
        """The metadata of the new sequence"""

        # Initialize base class
        super().__init__(
            sequence_name=sequence_name,
            client=client,
            config=config,
            connection_pool=connection_pool,
            executor_pool=executor_pool,
            logger=logger,
        )

    # -------------------- Base class abstract method override --------------------
    def _on_context_enter(self):
        """
        Performs the server-side handshake to create the new sequence.

        Triggers the `SEQUENCE_CREATE` action, transmitting the sequence name
        and initial metadata. Upon success, it captures the unique authorization
        key required for subsequent topic creation.

        Raises:
            Exception: If the server rejects the creation or returns an empty response.
        """
        ACTION = FlightAction.SEQUENCE_CREATE

        act_resp = _do_action(
            client=self._control_client,
            action=ACTION,
            payload={
                "name": self._name,
                "user_metadata": self._metadata,
            },
            expected_type=_DoActionResponseKey,
        )

        if act_resp is None:
            raise Exception(f"Action '{ACTION.value}' returned no response.")

        self._key = act_resp.key
        self._entered = True
        self._sequence_status = SequenceStatus.Pending

    # NOTE: No need of overriding `_on_context_exit` as default behavior is ok.
