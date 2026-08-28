# -*- coding: utf-8 -*-
"""
arm —— Aubo（遨博）K5 机械臂控制模块（Windows 版）

模块构成：
  * arm_config.py      —— 机械臂配置（IP/端口/登录/运动参数/TCP 偏移/灵巧手安装偏移）
  * arm_controller.py  —— AuboK5ArmController（pyaubo_sdk RPC 封装）
  * arm_follow.py      —— ArmFollower（人体腕部 3D → 机械臂 TCP 目标映射，协同控制）
  * arm_safety.py      —— ArmSafetyBox（末端安全框，防相机/灵巧手剐蹭）
  * arm_follow_eye.py  —— EyeInHandFollower（眼在手上增量跟随 + 失手急停）

与灵巧手模块（hand/）平行：机械臂只负责"把末端（+挂载的灵巧手）移动到目标位姿"，
手势本身仍由 RY-H1(16) 灵巧手完成；TCP 坐标联动 = 灵巧手安装偏移（相对法兰）写入
机械臂 setTcpOffset，使 moveLine 的位姿直接以"灵巧手 TCP"为基准。

用法：
  from arm import AuboK5ArmController, ArmFollower, ArmSafetyBox, EyeInHandFollower
  arm = AuboK5ArmController()
  arm.open()                       # 连接 + 登录
  arm.poweron_and_startup()        # 上电 + 启动（松刹车）
  arm.movej([0, -0.26, 1.74, 0.44, 1.57, 0])   # 关节运动（弧度）
  arm.close()                      # 登出 + 断开
  f = ArmFollower()                # 腕部→TCP 映射（协同控制）
  pose = f.map_wrist_to_arm_pose([0.2, -0.3, 1.2])
"""

from .arm_config import ARM_CONFIG, DOF, JOINT_NAMES_CN
from .arm_controller import AuboK5ArmController
from .arm_follow import ArmFollower
from .arm_safety import ArmSafetyBox
from .arm_follow_eye import EyeInHandFollower

__all__ = [
    "ARM_CONFIG", "DOF", "JOINT_NAMES_CN",
    "AuboK5ArmController",
    "ArmFollower",
    "ArmSafetyBox",
    "EyeInHandFollower",
]
