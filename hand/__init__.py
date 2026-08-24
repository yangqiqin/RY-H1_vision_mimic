# -*- coding: utf-8 -*-
"""hand package —— RY-H1(16) 灵巧手控制模块（Windows 版）。"""

from .hand_config import (
    HAND_CONFIG, FINGER_MOTOR_IDS, FINGER_ORDER,
    ANGLE_RANGE_DEG, JOINT_NUM, MOTOR_NUM, POS_MAX,
    JOINT_NAMES_CN,
)
from .angles2motor import (
    angles_to_motor_cmds, motor_cmds_to_joint_angles,
)
from .hand_controller import (
    RYH1HandController, ServoInfo, status_text, SERVO_STATUS_TEXT,
)

__all__ = [
    "HAND_CONFIG", "FINGER_MOTOR_IDS", "FINGER_ORDER",
    "ANGLE_RANGE_DEG", "JOINT_NUM", "MOTOR_NUM", "POS_MAX", "JOINT_NAMES_CN",
    "angles_to_motor_cmds", "motor_cmds_to_joint_angles",
    "RYH1HandController", "ServoInfo", "status_text", "SERVO_STATUS_TEXT",
]
