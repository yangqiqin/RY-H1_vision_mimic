# -*- coding: utf-8 -*-
"""
arm_follow.py —— 人体腕部 3D → 机械臂 TCP 目标映射（协同控制核心）

功能：
  把"摄像头坐标系下的人体腕部 3D 位置"映射为"机械臂基座坐标系下的 TCP 目标位姿
  [x, y, z, rx, ry, rz]"，实现"人动臂动"的协同控制。

坐标关系（三段链）：
  L515 相机系(米)  --外参 T_cam_base-->  机械臂基座系  --灵巧手安装偏移-->  TCP 系
                     (标定)                                    (setTcpOffset)

当前实现（可现场标定）：
  * 平移映射：target = (wrist_3d - offset) * scale + add  （逐元素，米）
  * 姿态固定：rx/ry/rz 取固定值（默认朝下抓取姿态）或按肩-肘方向估（可选）
  * 缩放/偏移通过 CALIB 配置，GUI 可调，支持保存到 config/calibration.json

说明：
  * 相机↔机械臂外参（旋转+平移）最准确做法是手眼标定；本项目先用"缩放+平移"仿射近似，
    现场按"人手移动到期望位置 → 记录机械臂实际目标"逐步校准 offset/add；
  * 映射函数纯计算、无硬件依赖，可单独验证（apps/test_arm_follow.py）。

用法：
  from arm.arm_follow import ArmFollower
  f = ArmFollower()                     # 用默认标定参数
  pose6 = f.map_wrist_to_arm_pose([0.2, -0.3, 1.2])   # 腕部 3D(米) -> [x,y,z,rx,ry,rz]
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional

logger = logging.getLogger("arm_follow")

# 默认标定参数（经验值，需现场标定）：
#   offset：相机系原点相对机械臂基座的平移（米）
#   scale ：相机米 → 机械臂米 的比例（通常 ≈1，若有缩放差异再调）
#   add   ：目标平移附加量（米）
#   fixed_pose：TCP 姿态（弧度，默认"朝下抓取"方向）
DEFAULT_CALIB = {
    "offset": [0.0, 0.0, 0.0],          # 相机系原点在机械臂基座系的位置（米）
    "scale": [1.0, 1.0, 1.0],           # 各轴缩放
    "add": [0.35, 0.0, 0.10],           # 目标附加平移（把"人前"映射到"臂前"）
    "fixed_rpy": [math.pi, 0.0, 0.0],   # TCP 姿态（弧度）
    "min_xyz": [0.15, -0.40, 0.10],     # 安全下限（米）
    "max_xyz": [0.90, 0.40, 0.80],      # 安全上限（米）
}

# 人体腕部到机械臂的常见方向（默认右手腕 → 机械臂"朝下"抓取）
DEFAULT_GRASP_RPY = [math.pi, 0.0, 0.0]   # 绕 X 轴 180°（朝下）


class ArmFollower:
    """
    人体腕部 3D → 机械臂 TCP 目标 映射器（可标定、可单独验证）。
    """

    def __init__(self, calib: Optional[dict] = None):
        """
        Args:
            calib: 标定参数字典（含 offset/scale/add/fixed_rpy/min_xyz/max_xyz）；
                   None 用 DEFAULT_CALIB。
        """
        c = dict(DEFAULT_CALIB)
        if calib:
            c.update(calib)
        self.offset = list(c.get("offset", [0.0, 0.0, 0.0]))
        self.scale = list(c.get("scale", [1.0, 1.0, 1.0]))
        self.add = list(c.get("add", [0.35, 0.0, 0.10]))
        self.fixed_rpy = list(c.get("fixed_rpy", list(DEFAULT_GRASP_RPY)))
        self.min_xyz = list(c.get("min_xyz", [0.15, -0.40, 0.10]))
        self.max_xyz = list(c.get("max_xyz", [0.90, 0.40, 0.80]))

    # ------------------------------------------------------------------
    def map_wrist_to_arm_pose(self, wrist_3d: List[float]) -> List[float]:
        """
        腕部 3D（相机系，米）→ 机械臂 TCP 目标位姿 [x,y,z,rx,ry,rz]（米/弧度）。

        公式：target_i = (wrist_i - offset_i) * scale_i + add_i，再裁剪到安全区间。
        """
        if wrist_3d is None or len(wrist_3d) < 3:
            raise ValueError("wrist_3d 需要至少 3 个分量")
        xyz = []
        for i in range(3):
            v = (float(wrist_3d[i]) - self.offset[i]) * self.scale[i] + self.add[i]
            lo, hi = self.min_xyz[i], self.max_xyz[i]
            xyz.append(max(lo, min(hi, v)))
        pose = xyz + list(self.fixed_rpy)
        return pose

    # ------------------------------------------------------------------
    def update_calib(self, **kwargs):
        """运行时更新标定参数（GUI 用）。支持 offset/scale/add/fixed_rpy/min_xyz/max_xyz。"""
        for k, v in kwargs.items():
            if k in ("offset", "scale", "add", "fixed_rpy", "min_xyz", "max_xyz") and v:
                setattr(self, k, [float(x) for x in v])

    def get_calib(self) -> dict:
        """当前标定参数（供 GUI 显示/保存）。"""
        return {
            "offset": list(self.offset),
            "scale": list(self.scale),
            "add": list(self.add),
            "fixed_rpy": list(self.fixed_rpy),
            "min_xyz": list(self.min_xyz),
            "max_xyz": list(self.max_xyz),
        }

    # ------------------------------------------------------------------
    def estimate_pose_from_arm(self, shoulder_3d: List[float],
                               elbow_3d: List[float]) -> List[float]:
        """
        可选：由 肩→肘 方向估 TCP 姿态（近似朝目标方向）。
        返回 [rx, ry, rz]（弧度，欧拉近似）。未标定时返回 fixed_rpy 更稳。
        """
        try:
            v = [elbow_3d[i] - shoulder_3d[i] for i in range(3)]
            n = math.sqrt(sum(x * x for x in v))
            if n < 1e-6:
                return list(self.fixed_rpy)
            # 简化为绕 X/Y 的俯仰（Z 朝前 → 朝目标）
            pitch = math.asin(max(-1.0, min(1.0, -v[1] / n)))
            yaw = math.atan2(v[0], v[2])
            return [pitch, yaw, self.fixed_rpy[2]]
        except Exception:
            return list(self.fixed_rpy)


if __name__ == "__main__":
    # 自测：映射函数纯计算验证
    f = ArmFollower()
    pose = f.map_wrist_to_arm_pose([0.2, -0.3, 1.2])
    print(f"腕部(0.2,-0.3,1.2) -> TCP {[round(v,3) for v in pose]}")
    assert len(pose) == 6
    # 边界裁剪验证
    p2 = f.map_wrist_to_arm_pose([5.0, 5.0, 5.0])
    print(f"越界腕部 -> TCP {[round(v,3) for v in p2]}（应被裁剪）")
    assert p2[0] <= f.max_xyz[0] + 1e-6 and p2[1] <= f.max_xyz[1] + 1e-6
    print("ArmFollower 自测通过")
