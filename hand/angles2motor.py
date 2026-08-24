# -*- coding: utf-8 -*-
"""
angles2motor.py —— RY-H1(16) 关节角度 <-> 电机指令换算

与官方 demo `update_motor_positions` 完全一致：
    k = 4095/90
    M1 = k·(θ1/2 + θ2)          （θ1 侧摆、θ2 近节，单位度）
    M2 = k·(−θ1/2 + θ2)
    M3 = (4095/75)·θ3
    M16 = (4095/110)·θ16
    左手（hand_lr=0）时每指 M1↔M2 交换
"""

from __future__ import annotations

import math
from typing import List

from .hand_config import (
    ANGLE_RANGE_DEG, FINGER_ORDER, K12, K3, K16, POS_MAX,
)


def _clamp(v: float, lo: float = 0.0, hi: float = POS_MAX) -> int:
    return int(round(max(lo, min(hi, v))))


def _clamp_angle_rad(v: float, lo_deg: float, hi_deg: float) -> float:
    return max(math.radians(lo_deg), min(math.radians(hi_deg), v))


def angles_to_motor_cmds(angles_rad_16: List[float],
                         hand_lr: int = 1) -> List[int]:
    """16 关节角度（弧度，顺序 = 关节 ID 1~16）-> 16 个电机指令（0~4095）。"""
    if len(angles_rad_16) != 16:
        raise ValueError("angles_rad_16 必须包含恰好 16 个元素（关节 ID 1~16）")

    lim = list(angles_rad_16)
    for i in range(15):
        joint_in_finger = i % 3
        if joint_in_finger == 0:
            lo, hi = ANGLE_RANGE_DEG["swing"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
        elif joint_in_finger == 1:
            lo, hi = ANGLE_RANGE_DEG["prox"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
        else:
            lo, hi = ANGLE_RANGE_DEG["dist"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
    lo16, hi16 = ANGLE_RANGE_DEG["joint16"]
    lim[15] = _clamp_angle_rad(lim[15], lo16, hi16)

    cmds = [0] * 16
    for finger_idx, finger in enumerate(FINGER_ORDER):
        base = finger_idx * 3
        t1_deg = math.degrees(lim[base])
        t2_deg = math.degrees(lim[base + 1])
        t3_deg = math.degrees(lim[base + 2])
        cmds[base] = _clamp(int(K12 * (t1_deg / 2.0 + t2_deg)))
        cmds[base + 1] = _clamp(int(K12 * (-t1_deg / 2.0 + t2_deg)))
        cmds[base + 2] = _clamp(int(K3 * t3_deg))
    cmds[15] = _clamp(int(K16 * math.degrees(lim[15])))

    if hand_lr == 0:
        for finger_idx in range(5):
            base = finger_idx * 3
            cmds[base], cmds[base + 1] = cmds[base + 1], cmds[base]
    return cmds


def motor_cmds_to_joint_angles(cmds: List[int], hand_lr: int = 1) -> List[float]:
    """16 电机指令 -> 16 关节角度（弧度）。"""
    if len(cmds) != 16:
        raise ValueError("cmds 必须包含恰好 16 个元素")
    if hand_lr == 0:
        cmds = list(cmds)
        for finger_idx in range(5):
            base = finger_idx * 3
            cmds[base], cmds[base + 1] = cmds[base + 1], cmds[base]

    angles = [0.0] * 16
    for i in range(15):
        joint_in_finger = i % 3
        finger_base = (i // 3) * 3
        if joint_in_finger == 0:
            angles[i] = (cmds[finger_base] - cmds[finger_base + 1]) / K12
        elif joint_in_finger == 1:
            angles[i] = (cmds[finger_base] + cmds[finger_base + 1]) / (2.0 * K12)
        else:
            angles[i] = cmds[i] / K3
    angles[15] = cmds[15] / K16
    return [math.radians(a) for a in angles]
