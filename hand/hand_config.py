# -*- coding: utf-8 -*-
"""
hand_config.py —— RY-H1(16) 灵巧手配置（Windows 版）

依据《RY-H1(16)灵巧手用户使用手册》+ 官方 demo（知识库）：
  * 关节角度 ID 1~16（控制接口用"关节 ID"）
  * 每指 3 电机（电机 ID = 关节内电机编号）
  * 换算系数与左右手规则（demo update_motor_positions）

关节角度 ID（1~16）：
    1 拇指侧摆 | 2 拇指近节 | 3 拇指远节
    4 食指侧摆 | 5 食指近节 | 6 食指远节
    7 中指侧摆 | 8 中指近节 | 9 中指远节
    10 无名指侧摆 | 11 无名指近节 | 12 无名指远节
    13 小指侧摆 | 14 小指近节 | 15 小指远节
    16 第16关节（0~110°）
"""

# 手指 -> 电机 ID（每指 3 个电机，顺序 [电机1, 电机2, 电机3]）
FINGER_MOTOR_IDS = {
    "thumb":   [1, 2, 3],
    "index":   [4, 5, 6],
    "middle":  [7, 8, 9],
    "ring":    [10, 11, 12],
    "pinky":   [13, 14, 15],
}
MOTOR_NUM = 16
JOINT_NUM = 16
FINGER_ORDER = ["thumb", "index", "middle", "ring", "pinky"]

# 关节角度范围（度，伸直=0°）
ANGLE_RANGE_DEG = {
    "swing":   (-20.0, 20.0),
    "prox":    (  0.0, 90.0),
    "dist":    (  0.0, 75.0),
    "joint16": (  0.0, 110.0),
}

# 中文关节名（GUI/日志显示用）
JOINT_NAMES_CN = [
    "拇指侧摆", "拇指MCP", "拇指PIP",
    "食指侧摆", "食指MCP", "食指PIP",
    "中指侧摆", "中指MCP", "中指PIP",
    "无名指侧摆", "无名指MCP", "无名指PIP",
    "小指侧摆", "小指MCP", "小指PIP",
    "拇指内外展"
]

K12 = 4095.0 / 90.0
K3 = 4095.0 / 75.0
K16 = 4095.0 / 110.0
POS_MAX = 4095

HAND_CONFIG = {
    "position_max": POS_MAX,
    "k12": K12, "k3": K3, "k16": K16,
    "angle_range_deg": ANGLE_RANGE_DEG,
    "default_speed": 1000,
    "default_max_current": 75,
    "cmd_pos_vel_cur": 0xAA,
    "cmd_pos_vel":     0xA1,
    "cmd_get_status":  0xA0,
    "hook_num": 40,
    "listen_num": 33,
    "update_rate_ms": 20,
    "timeout_ms": 10,
}
