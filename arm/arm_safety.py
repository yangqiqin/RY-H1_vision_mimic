# -*- coding: utf-8 -*-
"""
arm_safety.py —— 机械臂末端安全框模块（防剐蹭：相机 + 灵巧手安全保护）

背景（参考 lib/grasp 项目的安全策略）：
  * 机械臂末端挂着"L515 相机 + RY-H1 灵巧手"组合体；
  * 若机械臂随意运动，末端（相机/灵巧手）可能剐蹭桌面、机械臂本体或障碍物；
  * 本项目要求：机械臂运动必须被限制在【安全框】内（基座系下的 xyz 长方体区域），
    超出则裁剪或拒绝执行 → 从物理上杜绝相机/灵巧手碰撞。

安全框设计：
  * 以机械臂基座为原点（米），定义可运动长方体的下限/上限：
        min_xyz = [x_min, y_min, z_min]   （默认：工作台面之上、机械臂前方）
        max_xyz = [x_max, y_max, z_max]
  * clamp_pose()：把目标位置裁剪进安全框（超出部分拉回边界）；
  * check_pose()：判断目标是否在框内（供 GUI 显示/告警）；
  * 默认值参考 grasp 项目（SPACE_MIN_Z=0.18, SPACE_MAX_Z=0.68）与典型桌面高度，
    现场需按实际工作台/桌面高度修改。

用法：
  from arm.arm_safety import ArmSafetyBox
  safe = ArmSafetyBox()
  safe.set_box(min_xyz=[0.1, -0.4, 0.18], max_xyz=[0.9, 0.4, 0.68])
  clipped = safe.clamp_pose([0.5, -0.3, 0.05])   # z 被拉回 0.18
  ok, msg = safe.check_pose([0.5, -0.3, 0.5])    # (True, "OK")
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("arm_safety")

# 默认安全框（米，基座系）——参考 grasp 项目 + 典型桌面高度，现场按实际修改
DEFAULT_MIN_XYZ = [0.10, -0.40, 0.18]    # x 前、y 左右、z 高（桌面以上）
DEFAULT_MAX_XYZ = [0.90,  0.40, 0.68]    # 上限（防过高/过近机械臂本体）


class ArmSafetyBox:
    """机械臂末端安全框：限制末端位置，防相机/灵巧手剐蹭。"""

    def __init__(self,
                 min_xyz: Optional[List[float]] = None,
                 max_xyz: Optional[List[float]] = None):
        """
        Args:
            min_xyz: 安全框下限 [x,y,z]（米）
            max_xyz: 安全框上限 [x,y,z]（米）
        """
        self.min_xyz = np.array(min_xyz if min_xyz else DEFAULT_MIN_XYZ, dtype=np.float64)
        self.max_xyz = np.array(max_xyz if max_xyz else DEFAULT_MAX_XYZ, dtype=np.float64)

    # ------------------------------------------------------------------
    def set_box(self, min_xyz: Optional[List[float]] = None,
                max_xyz: Optional[List[float]] = None):
        """运行时设置安全框（GUI 可调）。"""
        if min_xyz is not None:
            self.min_xyz = np.array(min_xyz, dtype=np.float64)
        if max_xyz is not None:
            self.max_xyz = np.array(max_xyz, dtype=np.float64)
        logger.info("[safety] 安全框 = min%s max%s", self.min_xyz, self.max_xyz)

    def get_box(self) -> dict:
        return {"min_xyz": list(self.min_xyz), "max_xyz": list(self.max_xyz)}

    # ------------------------------------------------------------------
    def clamp_pose(self, pos: List[float]) -> List[float]:
        """把目标位置裁剪进安全框（超出部分拉回边界）。返回裁剪后的 [x,y,z]。"""
        p = np.array(pos[:3], dtype=np.float64)
        p = np.maximum(self.min_xyz, np.minimum(self.max_xyz, p))
        out = list(p) + list(pos[3:6]) if len(pos) >= 6 else list(p)
        return out

    def check_pose(self, pos: List[float],
                   margin: float = 0.0) -> Tuple[bool, str]:
        """判断目标是否在安全框内（可选留边距 margin）。返回 (ok, 说明)。"""
        p = np.array(pos[:3], dtype=np.float64)
        lo = self.min_xyz + margin
        hi = self.max_xyz - margin
        if np.all(p >= lo) and np.all(p <= hi):
            return True, "OK"
        outside = []
        for i, name in enumerate("xyz"):
            if p[i] < lo[i]:
                outside.append(f"{name}低于下限({p[i]:.3f}<{lo[i]:.3f})")
            elif p[i] > hi[i]:
                outside.append(f"{name}超上限({p[i]:.3f}>{hi[i]:.3f})")
        return False, ";".join(outside)

    def describe(self) -> str:
        return (f"安全框 x[{self.min_xyz[0]:.2f},{self.max_xyz[0]:.2f}] "
                f"y[{self.min_xyz[1]:.2f},{self.max_xyz[1]:.2f}] "
                f"z[{self.min_xyz[2]:.2f},{self.max_xyz[2]:.2f}] m")


if __name__ == "__main__":
    safe = ArmSafetyBox()
    print(safe.describe())
    # 越界裁剪
    clipped = safe.clamp_pose([0.5, -0.3, 0.05])
    print(f"z=0.05 越界 -> 裁剪为 {clipped}")
    assert clipped[2] >= safe.min_xyz[2] - 1e-9
    # 框内判定
    ok, msg = safe.check_pose([0.5, -0.3, 0.5])
    print(f"[0.5,-0.3,0.5] -> ok={ok} {msg}")
    ok2, msg2 = safe.check_pose([1.5, 0, 0.5])
    print(f"[1.5,0,0.5] -> ok={ok2} {msg2}")
    assert not ok2
    print("ArmSafetyBox 自测通过")
