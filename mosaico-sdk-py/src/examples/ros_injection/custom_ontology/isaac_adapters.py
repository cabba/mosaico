from typing import Any, Tuple, Type
from mosaicolabs.models import Message
from mosaicolabs.ros_bridge import ROSMessage, ROSAdapterBase, register_adapter
from mosaicolabs.ros_bridge.adapters.helpers import _make_header, _validate_msgdata

from .isaac import EncoderTicks


@register_adapter
class EncoderTicksAdapter(ROSAdapterBase[EncoderTicks]):
    """
    Adapter for translating NVIDIA Isaac EncoderTicks messages to Mosaico.

    This adapter bridges the `isaac_ros_nova_interfaces` ROS package into the
    custom Mosaico `EncoderTicks` model, handling hardware-to-platform mapping.

    **Supported ROS Type:**
    - `isaac_ros_nova_interfaces/msg/EncoderTicks`
    """

    ros_msgtype: str | Tuple[str, ...] = ("isaac_ros_nova_interfaces/msg/EncoderTicks",)
    __mosaico_ontology_type__: Type[EncoderTicks] = EncoderTicks

    # Validation keys used by _validate_msgdata
    _REQUIRED_KEYS = ("left_ticks", "right_ticks", "encoder_timestamp")

    @classmethod
    def translate(cls, ros_msg: ROSMessage, **kwargs: Any) -> Message:
        """
        Translates a ROS EncoderTicks message into a Mosaico Message container.

        Args:
            ros_msg: The raw container provided by the ROSLoader.
            **kwargs: Additional translation context.

        Returns:
            A Mosaico Message containing the translated EncoderTicks data.
        """
        if ros_msg.data is None:
            raise Exception(f"'data' attribute is None for topic {ros_msg.topic}")

        print(f"Mesg Header: {ros_msg.header}")

        try:
            return Message(
                timestamp_ns=ros_msg.bag_timestamp_ns,
                data=cls.from_dict(ros_msg.data),
                message_header=ros_msg.header.translate() if ros_msg.header else None,
            )
        except Exception as e:
            raise Exception(f"Translation failed for {ros_msg.topic}: {e}")

    @classmethod
    def from_dict(cls, ros_data: dict) -> EncoderTicks:
        """
        Maps the raw ROS dictionary to the EncoderTicks Pydantic model.

        This method performs field validation and header reconstruction.
        """
        _validate_msgdata(cls, ros_data)
        print(f"Type Header: {ros_data.get('header')}")
        print(f"Encoder Timestamp: {ros_data['encoder_timestamp']}")
        return EncoderTicks(
            header=_make_header(ros_data.get("header")),
            left_ticks=ros_data["left_ticks"],
            right_ticks=ros_data["right_ticks"],
        )
