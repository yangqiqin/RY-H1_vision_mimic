# -*- coding: utf-8 -*-
"""
hand_eye.py —— 手眼标定模块（眼在手上：相机系 ↔ 机械臂基座系 坐标转换）

背景（参考 lib/grasp 项目，同一款 Aubo 机械臂 + RealSense L515）：
  * 相机固定在机械臂末端（"眼在手上" eye-in-hand），随末端一起运动；
  * 相机识别到的点（手腕/物体）在【相机坐标系】下，要转换为【机械臂基座系】下的坐标，
    才能驱动机械臂运动；
  * 转换需要"手眼标定矩阵"：相机系 → 末端法兰系 的旋转矩阵 R_cam2gripper 和平移向量
    t_cam2gripper（已由 grasp 项目标定，可直接复用；也可用本模块的标定流程现场重标定）。

坐标转换链（4 层，与 grasp 的 nanning.py / test_area_for_size.py 完全一致）：
  ① 像素(u,v) + 深度Z → 相机系 3D（针孔模型）：
        P_cam = [(u-cx)/fx·Z, (v-cy)/fy·Z, Z]
  ② 相机系 → 末端法兰系（手眼标定矩阵）：
        P_gripper = R_cam2gripper · P_cam + t_cam2gripper
  ③ 读取当前法兰位姿（正运动学）：末端位置 end_pos + 末端姿态 R_gripper2base
  ④ 末端法兰系 → 基座系：
        P_base = R_gripper2base · P_gripper + end_pos

用法：
  from vision.hand_eye import HandEyeCalibration, CALIB
  he = HandEyeCalibration(CALIB["R_cam2gripper"], CALIB["t_cam2gripper"])
  P_cam = he.pixel_to_camera(u, v, depth_mm, intrinsics)   # ①
  P_base = he.camera_to_base(P_cam, arm)                    # ①+②+③+④（需要机械臂实例）
  # 或直接一行：
  P_base = he.pixel_to_base(u, v, depth_mm, intrinsics, arm)
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional

import numpy as np

logger = logging.getLogger("hand_eye")

try:
    from scipy.spatial.transform import Rotation as _R
    _SCIPY_OK = True
except ImportError:  # pragma: no cover
    _SCIPY_OK = False


# ===========================================================================
# 手眼标定参数（复用 lib/grasp 项目标定结果）
# ===========================================================================
# 说明：grasp 项目里有两组标定矩阵（nanning.py 与 test_area_for_size.py），
# 物理安装位置不同会得到不同矩阵。默认用 test_area_for_size.py 当前启用的一组
# （与 grasp.md 记录的 nanning 版接近；现场若相机安装位置不变可直接用）。
# 若相机安装位置改变，请用 tools/calibrate_hand_eye.py 现场重标定后替换。
CALIB = {
    # 相机系 → 末端法兰系 旋转矩阵（3x3）
    "R_cam2gripper": np.array([
        [-0.02419637, -0.99950899,  0.01992146],
        [ 0.99955215, -0.02453875, -0.01714335],
        [ 0.01762429,  0.01949733,  0.99965460],
    ]),
    # 相机系 → 末端法兰系 平移向量（米）
    "t_cam2gripper": np.array([0.07802404, 0.00426695, 0.03737631]),
    # 备用（grasp.md 记录的 nanning 版本，供参考；如与你的安装匹配可切换）
    "R_cam2gripper_alt": np.array([
        [-0.9997106,  -0.01955281,  0.01401418],
        [ 0.01983786, -0.99959306,  0.02049808],
        [ 0.01360768,  0.02077016,  0.99969167],
    ]),
    "t_cam2gripper_alt": np.array([0.00050964, 0.13082029, 0.03207186]),
}

# 相机内参（L515 标准，参考 grasp 标定程序；现场可用 realsense 内参覆盖）
DEFAULT_INTRINSICS = {
    "fx": 901.7760620117188,
    "fy": 902.1463623046875,
    "ppx": 643.151611328125,
    "ppy": 361.9018249511719,
    "width": 1280,
    "height": 720,
}


class HandEyeCalibration:
    """
    手眼标定与坐标转换器（相机系 ↔ 机械臂基座系）。
    """

    def __init__(self,
                 R_cam2gripper: Optional[np.ndarray] = None,
                 t_cam2gripper: Optional[np.ndarray] = None):
        """
        Args:
            R_cam2gripper: 相机系→末端系旋转矩阵（3x3）；None 用 CALIB 默认
            t_cam2gripper: 相机系→末端系平移向量（3,）；None 用 CALIB 默认
        """
        self.R = np.array(R_cam2gripper if R_cam2gripper is not None
                          else CALIB["R_cam2gripper"], dtype=np.float64)
        self.t = np.array(t_cam2gripper if t_cam2gripper is not None
                          else CALIB["t_cam2gripper"], dtype=np.float64).reshape(3)

    # ------------------------------------------------------------------
    def set_calibration(self, R_cam2gripper: np.ndarray, t_cam2gripper: np.ndarray):
        """运行时更换标定矩阵（GUI 现场微调用）。"""
        self.R = np.array(R_cam2gripper, dtype=np.float64)
        self.t = np.array(t_cam2gripper, dtype=np.float64).reshape(3)
        logger.info("[hand_eye] 标定矩阵已更新")

    def get_calibration(self) -> dict:
        return {"R_cam2gripper": self.R.copy(), "t_cam2gripper": self.t.copy()}

    # ------------------------------------------------------------------
    @staticmethod
    def pixel_to_camera(u: float, v: float, depth_mm: float,
                        intrinsics: Optional[dict] = None) -> np.ndarray:
        """① 像素 (u,v) + 深度(mm) → 相机系 3D 坐标（米）。针孔模型。"""
        k = intrinsics or DEFAULT_INTRINSICS
        fx, fy = float(k["fx"]), float(k["fy"])
        ppx, ppy = float(k["ppx"]), float(k["ppy"])
        z = depth_mm / 1000.0
        x = (u - ppx) * z / fx
        y = (v - ppy) * z / fy
        return np.array([x, y, z], dtype=np.float64)

    # ------------------------------------------------------------------
    def cam_to_gripper(self, P_cam: np.ndarray) -> np.ndarray:
        """② 相机系 → 末端法兰系（手眼标定矩阵）。"""
        return np.dot(self.R, P_cam) + self.t

    @staticmethod
    def gripper_to_base(P_gripper: np.ndarray,
                        end_position: np.ndarray,
                        R_gripper2base: np.ndarray) -> np.ndarray:
        """④ 末端法兰系 → 基座系（需要当前法兰位姿）。"""
        return np.dot(R_gripper2base, P_gripper) + end_position

    # ------------------------------------------------------------------
    def camera_to_base(self, P_cam: np.ndarray, arm,
                       flange_pose: Optional[List[float]] = None) -> np.ndarray:
        """相机系点 → 基座系点（②+③+④）。

        Args:
            P_cam: 相机系 3D 坐标（米）
            arm: 机械臂控制器实例（仅在 flange_pose 未给时读取位姿）
            flange_pose: 可选——调用方已读到的当前【法兰】位姿 [x,y,z,rx,ry,rz]。
                         ★ 传入后不再重复 RPC 读位姿（眼在手上跟随每帧调用多次本方法，
                         复用一次读数可显著降低机械臂 RPC 开销、改善实时性）
        """
        P_gripper = self.cam_to_gripper(P_cam)
        # ③ 读取当前【法兰】位姿（手眼标定必须用法兰系：相机装在法兰盘上，
        #    不能用含 TCP 偏移的 getTcpPose，否则引入灵巧手安装偏移误差）
        pose = flange_pose
        if pose is None:
            if hasattr(arm, "get_flange_pose"):
                pose = arm.get_flange_pose()
            elif hasattr(arm, "get_tcp_pose"):
                pose = arm.get_tcp_pose()
        if pose is None:
            raise RuntimeError("无法读取机械臂当前法兰位姿（get_flange_pose 失败）")
        end_pos = np.array(pose[:3], dtype=np.float64)
        R_gripper2base = self._rpy_to_matrix(pose[3:6])
        return self.gripper_to_base(P_gripper, end_pos, R_gripper2base)

    # ------------------------------------------------------------------
    def pixel_to_base(self, u: float, v: float, depth_mm: float,
                      intrinsics: Optional[dict], arm) -> np.ndarray:
        """像素 + 深度 → 基座系坐标（①→④ 全链路，最常用）。"""
        P_cam = self.pixel_to_camera(u, v, depth_mm, intrinsics)
        return self.camera_to_base(P_cam, arm)

    # ------------------------------------------------------------------
    @staticmethod
    def _rpy_to_matrix(rpy: List[float]) -> np.ndarray:
        """RPY 欧拉角（弧度，xyz 顺序）→ 旋转矩阵。"""
        if _SCIPY_OK:
            return _R.from_euler("xyz", list(rpy)).as_matrix()
        # 无 scipy 时手写（XYZ 顺序）
        rx, ry, rz = rpy
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        return Rz @ Ry @ Rx


if __name__ == "__main__":
    # 自测：坐标转换链（无机械臂，用模拟末端位姿）
    he = HandEyeCalibration()
    # 模拟相机系点（像素中心 + 深度 500mm）
    P_cam = he.pixel_to_camera(643.0, 362.0, 500.0)
    print(f"P_cam = {P_cam}")
    # 模拟末端：位置(0.5, 0, 0.4)，姿态 RPY=[pi, 0, 0]
    class FakeArm:
        @staticmethod
        def get_tcp_pose():
            return [0.5, 0.0, 0.4, math.pi, 0.0, 0.0]
    P_base = he.camera_to_base(P_cam, FakeArm())
    print(f"P_base = {P_base}")
    assert P_base.shape == (3,)
    assert np.all(np.isfinite(P_base))
    print("HandEyeCalibration 自测通过")
