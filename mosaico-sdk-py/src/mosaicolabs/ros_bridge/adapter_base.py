from abc import ABC, abstractmethod
from typing import Generic, Optional, Tuple, Type, Any, TypeVar

from mosaicolabs.models.message import Message

from .ros_message import ROSMessage
from ..models import Serializable

T = TypeVar("T", bound=Serializable)


class ROSAdapterBase(ABC, Generic[T]):
    """
    Abstract Base Class for converting ROS messages to Mosaico Ontology types.

    The Adaptation Layer is the semantic core of the ROS Bridge. Rather than
    performing simple parsing, adapters actively translate raw ROS data into standardized,
    strongly-typed Mosaico Ontology objects.

    Attributes:
        ros_msgtype: The ROS message type string (e.g., 'sensor_msgs/msg/Imu') or a tuple
            of supported types.
        __mosaico_ontology_type__: The target Mosaico class (e.g., IMU).
        _REQUIRED_KEYS: Internal validation list for mandatory ROS message fields.
    """

    ros_msgtype: str | Tuple[str, ...]
    __mosaico_ontology_type__: Type[T]
    _REQUIRED_KEYS: Tuple[str, ...]
    _REQUIRED_KEYS_CASE_INSENSITIVE: Tuple[str, ...] = ()

    @classmethod
    @abstractmethod
    def ros_msg_type(cls) -> str | Tuple[str, ...]:
        """Returns the specific ROS message type handled by this adapter."""
        return cls.ros_msgtype

    @classmethod
    @abstractmethod
    def translate(cls, ros_msg: ROSMessage, **kwargs: Any) -> Message:
        """
        Translates a ROS message instance into a Mosaico Message.

        Implementation should handle recursive unwrapping, unit conversion, and
        validation.

        Args:
            ros_msg: The source container yielded by the ROSLoader.
            **kwargs: Contextual data such as calibration parameters or frame overrides.

        Returns:
            A Mosaico Message object containing the instantiated ontology data.
        """
        pass

    @classmethod
    @abstractmethod
    def schema_metadata(cls, ros_data: dict, **kwargs: Any) -> Optional[dict]:
        """
        Extracts ROS-specific schema metadata for the Mosaico platform.

        This allows preserving original ROS attributes that may not fit directly
        into the physical ontology fields.
        """
        pass

    @classmethod
    def ontology_data_type(cls) -> Type[T]:
        """Returns the Ontology class type associated with this adapter."""
        return cls.__mosaico_ontology_type__
