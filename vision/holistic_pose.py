# -*- coding: utf-8 -*-
"""
holistic_pose.py —— MediaPipe Holistic 全身姿态估计（人体 → 机械臂 + 灵巧手协同）

功能：
  1. 用 MediaPipe HolisticLandmarker（最新 Tasks API + holistic_landmarker.task）同时检测：
       - 人体姿态 33 个关键点（pose_landmarks，含世界坐标 pose_world_landmarks）
       - 左手/右手各 21 个手部关键点（left/right_hand_landmarks）
  2. 人体关键点 → 机械臂 TCP 目标（协同控制：人动臂动）
       - 取"右/左手腕"3D 位置 + 肩/肘方向，映射为机械臂末端位姿 [x,y,z,rx,ry,rz]
       - 映射由 arm/arm_follow.py 的 map_wrist_to_arm_pose 完成（可单独验证/标定）
  3. 手部 21 点 → 16 关节角（复用 vision/hand_pose.py 的角度解算链，保证与灵巧手一致）
       - 内部组合一个 HandPoseEstimator 实例（用其 _convert_landmarks_to_3d / _landmarks_to_angles16
         / 全部校准参数），但检测由本模块的 HolisticLandmarker 完成
  4. 输出 HolisticResult：
       - pose 3D 关键点（相机系米制，含腕部）
       - hand_angles_deg[16]、hand_lateral_dist、hand_fist_confidence
       - arm_target_pose（映射后的机械臂 TCP 目标，可选）
  5. 骨架绘制：人体 33 点连线 + 手部 21 点连线（复用 HAND_CONNECTIONS / POSE_CONNECTIONS）

设计说明：
  * 不修改 vision/hand_pose.py（原文件保留，仅被组合使用）；
  * HolisticLandmarker 是 mediapipe 1.x Tasks API 新模型（mediapipe 1.0.1 已验证支持）；
  * 模型文件：lib/holistic_landmarker.task（用户提供，最新版）。

用法：
  from vision.holistic_pose import HolisticPoseEstimator, HolisticResult
  est = HolisticPoseEstimator()                     # 需 lib/holistic_landmarker.task
  results = est.process(rgb_bgr, depth, intrinsics) # 每帧调用
  for r in results:
      print(r.hand_angles_deg, r.wrist_3d, r.arm_target_pose)
  est.close()
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

logger = logging.getLogger("holistic")

# 尝试导入 MediaPipe（1.x Tasks API）
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    _MP_OK = True
except ImportError:  # pragma: no cover
    mp = None
    mp_python = None
    mp_vision = None
    _MP_OK = False

# ==================== 模型文件配置 ====================
DEFAULT_MODEL_NAME = "holistic_landmarker.task"
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/"
    "holistic_landmarker/float16/1/holistic_landmarker.task"
)


def _find_model_file(model_path: Optional[str] = None) -> Optional[str]:
    """搜索模型：显式路径 → cwd → 根目录 → lib/ → 本文件目录。"""
    if model_path:
        return model_path if os.path.exists(model_path) else None
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    for d in (os.getcwd(), project_root, os.path.join(project_root, "lib"), here):
        p = os.path.join(d, DEFAULT_MODEL_NAME)
        if os.path.exists(p):
            return p
    return None


# ==================== 人体姿态关键点索引（MediaPipe Pose 33 点） ====================
# 常用索引（完整 33 点见 mediapipe PoseLandmark 枚举）
POSE_NOSE = 0
POSE_LEFT_SHOULDER = 11
POSE_RIGHT_SHOULDER = 12
POSE_LEFT_ELBOW = 13
POSE_RIGHT_ELBOW = 14
POSE_LEFT_WRIST = 15
POSE_RIGHT_WRIST = 16
POSE_LEFT_PINKY = 17
POSE_RIGHT_PINKY = 18
POSE_LEFT_INDEX = 19
POSE_RIGHT_INDEX = 20
POSE_LEFT_THUMB = 21
POSE_RIGHT_THUMB = 22

# 人体骨架连线（简化版，用于绘制）
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),   # 肩-肘-腕
    (11, 23), (12, 24), (23, 24),                      # 肩-髋
    (15, 17), (15, 19), (15, 21),                      # 左腕-手指
    (16, 18), (16, 20), (16, 22),                      # 右腕-手指
    (23, 25), (25, 27), (24, 26), (26, 28),            # 髋-膝-踝
]

# 复用 hand_pose 的手部关键点索引与连线（保证与灵巧手角度解算一致）
from .hand_pose import (  # noqa: E402
    HAND_CONNECTIONS,
    INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP, WRIST,
    _angle_between,
)


@dataclass
class HolisticResult:
    """
    单帧 holistic 检测结果。

    Attributes:
        pose_landmarks: 人体 33 关键点（归一化 (33,3)，未检测到为 None）
        pose_3d: 人体 33 关键点（相机系米制 (33,3)，深度补全）
        wrist_3d: 用于机械臂映射的腕部 3D 坐标（米，None=未检测）
        wrist_side: "right"/"left"/None
        hand_landmarks: 手部 21 关键点（归一化 (21,3)，None=未检测到手）
        hand_angles_deg: 16 关节角（度，复用 hand_pose 解算）
        hand_lateral_dist: 拇指横向距离
        hand_fist_confidence: 深度辅助握拳置信度
        arm_target_pose: 映射后的机械臂 TCP 目标 [x,y,z,rx,ry,rz]（可选）
        confidence: 检测置信度
    """
    pose_landmarks: Optional[np.ndarray] = None
    pose_3d: Optional[np.ndarray] = None
    wrist_3d: Optional[List[float]] = None
    wrist_side: str = "none"
    hand_landmarks: Optional[np.ndarray] = None
    hand_angles_deg: List[float] = field(default_factory=lambda: [0.0] * 16)
    hand_lateral_dist: float = 0.0
    hand_fist_confidence: Optional[float] = None
    arm_target_pose: Optional[List[float]] = None
    confidence: float = 0.0

    @property
    def pose_detected(self) -> bool:
        return self.pose_landmarks is not None

    @property
    def hand_detected(self) -> bool:
        return self.hand_landmarks is not None


class HolisticPoseEstimator:
    """
    MediaPipe Holistic 全身姿态估计器（人体 → 机械臂 + 灵巧手协同）。

    - 用 HolisticLandmarker 检测人体 + 双手（一帧一次推理）；
    - 组合 HandPoseEstimator 复用其 3D 转换与 16 关节角解算（参数一致）；
    - 提供腕部 3D → 机械臂 TCP 映射入口（映射逻辑在 arm/arm_follow.py）。
    """

    def __init__(
        self,
        use_hand_pose: bool = True,
        hand_side: str = "right",          # 用哪只手控制灵巧手："right"/"left"
        model_path: Optional[str] = None,
        bend_scale: float = 1.0,
        bend_offset: float = 0.0,
        bend_gain: float = 1.0,
        deadzone_deg: float = 1.0,
        bend_reverse: bool = False,
        per_finger_scale: Optional[dict] = None,
        per_finger_offset: Optional[dict] = None,
        thumb_abd_offset: float = 0.0,
        thumb_abd_gain: float = 0.8,
        thumb_abd_reverse: bool = False,
        swing_reverse: bool = False,
    ):
        if not _MP_OK:
            raise RuntimeError("请安装 mediapipe>=0.10.14：pip install mediapipe")

        model_file = _find_model_file(model_path)
        if model_file is None:
            raise RuntimeError(
                f"未找到 holistic 模型文件 {DEFAULT_MODEL_NAME}。请放到项目根目录或 lib/：\n"
                f"  {MODEL_DOWNLOAD_URL}"
            )
        self.model_path = model_file
        self.hand_side = hand_side.lower()
        self.use_hand_pose = use_hand_pose

        # 创建 HolisticLandmarker（Tasks API）
        base_options = mp_python.BaseOptions(model_asset_path=model_file)
        options = mp_vision.HolisticLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
        )
        self._landmarker = mp_vision.HolisticLandmarker.create_from_options(options)

        # 组合 HandPoseEstimator 复用角度解算（懒创建，避免加载手部模型）
        self._hand_engine = None
        if use_hand_pose:
            from .hand_pose import HandPoseEstimator
            # 通过 __new__ 创建"裸实例"：不加载 hand 模型，只复用其角度解算方法
            self._hand_engine = object.__new__(HandPoseEstimator)
            self._hand_engine.bend_scale = bend_scale
            self._hand_engine.bend_offset = bend_offset
            self._hand_engine.bend_gain = max(0.1, float(bend_gain))
            self._hand_engine.deadzone_deg = float(deadzone_deg)
            self._hand_engine.bend_reverse = bool(bend_reverse)
            self._hand_engine.per_finger_scale = dict(per_finger_scale or {})
            self._hand_engine.per_finger_offset = dict(per_finger_offset or {})
            self._hand_engine.per_finger_swing_offset = {}
            self._hand_engine.swing_reverse = bool(swing_reverse)
            self._hand_engine.thumb_abd_offset = float(thumb_abd_offset)
            self._hand_engine.thumb_abd_gain = max(0.1, float(thumb_abd_gain))
            self._hand_engine.thumb_abd_reverse = bool(thumb_abd_reverse)
            self._hand_engine._frame_scale = 1.0

    # ------------------------------------------------------------------
    def update_params(self, **kwargs):
        """动态更新参数（同步给内部手部引擎）。"""
        if self._hand_engine is not None:
            self._hand_engine.update_params(**kwargs)
        for k, v in kwargs.items():
            if k == "hand_side":
                self.hand_side = str(v).lower()

    def set_hand_side(self, side: str):
        """切换用于控制灵巧手的手（right/left）。"""
        self.hand_side = str(side).lower()

    # ------------------------------------------------------------------
    def process(
        self,
        rgb_bgr: np.ndarray,
        depth: Optional[np.ndarray] = None,
        intrinsics: Optional[dict] = None,
        map_to_arm: bool = False,
        arm_mapper=None,
    ) -> List[HolisticResult]:
        """
        处理一帧：检测人体 + 双手，解算手部 16 关节角，可选映射机械臂 TCP。

        Args:
            rgb_bgr: BGR 帧 (H,W,3)
            depth: 深度帧（可选，mm）
            intrinsics: 相机内参 {fx,fy,ppx,ppy}（可选）
            map_to_arm: 是否把腕部 3D 映射为机械臂 TCP（需 arm_mapper）
            arm_mapper: arm/arm_follow.py 的映射器（callable: wrist_3d -> pose6）
        """
        if rgb_bgr is None:
            return []
        rgb = bgr2rgb(rgb_bgr)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=np.ascontiguousarray(rgb))
        res = self._landmarker.detect(mp_image)

        out: List[HolisticResult] = []
        # holistic 最多检测一个人体；构造单结果
        r = HolisticResult()
        if not res.pose_landmarks and not (res.left_hand_landmarks or res.right_hand_landmarks):
            return out

        # ---- 1. 人体关键点 ----
        if res.pose_landmarks:
            pts_norm = np.array([(p.x, p.y, p.z) for p in res.pose_landmarks],
                                dtype=np.float64)
            r.pose_landmarks = pts_norm
            r.pose_3d = self._pose_to_3d(pts_norm, depth, intrinsics)

        # ---- 2. 手部关键点（选一只手控制灵巧手） ----
        hand_pts_norm = None
        side = "none"
        if self.hand_side == "left" and res.left_hand_landmarks:
            hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.left_hand_landmarks],
                                     dtype=np.float64)
            side = "left"
        elif self.hand_side == "right" and res.right_hand_landmarks:
            hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.right_hand_landmarks],
                                     dtype=np.float64)
            side = "right"
        elif res.right_hand_landmarks:  # 兜底：默认优先右手
            hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.right_hand_landmarks],
                                     dtype=np.float64)
            side = "right"

        r.hand_landmarks = hand_pts_norm
        if hand_pts_norm is not None and self._hand_engine is not None:
            real_pts = self._hand_engine._convert_landmarks_to_3d(
                hand_pts_norm, depth, intrinsics)
            angles, lateral = self._hand_engine._landmarks_to_angles16(real_pts)
            r.hand_angles_deg = angles
            r.hand_lateral_dist = lateral
            r.hand_fist_confidence = self._hand_engine._compute_fist_confidence(
                hand_pts_norm, real_pts)

        # ---- 3. 腕部 3D（机械臂映射用） ----
        wrist_pose_idx = POSE_RIGHT_WRIST if side == "right" else POSE_LEFT_WRIST
        # 优先用所选手的腕部（pose 15/16），若人体未检测到则回退手部 WRIST
        if r.pose_3d is not None and wrist_pose_idx < len(r.pose_3d):
            w3d = r.pose_3d[wrist_pose_idx]
            if np.all(np.isfinite(w3d)):
                r.wrist_3d = [float(v) for v in w3d]
                r.wrist_side = side
        if r.wrist_3d is None and hand_pts_norm is not None and self._hand_engine is not None:
            real_pts = self._hand_engine._convert_landmarks_to_3d(
                hand_pts_norm, depth, intrinsics)
            if real_pts is not None and np.all(np.isfinite(real_pts[WRIST])):
                r.wrist_3d = [float(v) for v in real_pts[WRIST]]
                r.wrist_side = side

        # ---- 4. 机械臂 TCP 映射 ----
        if map_to_arm and arm_mapper is not None and r.wrist_3d is not None:
            try:
                r.arm_target_pose = arm_mapper(r.wrist_3d)
            except Exception as exc:
                logger.warning("arm mapper 异常: %s", exc)

        out.append(r)
        return out

    # ------------------------------------------------------------------
    @staticmethod
    def _pose_to_3d(
        pts_norm: np.ndarray,
        depth: Optional[np.ndarray],
        intrinsics: Optional[dict],
    ) -> Optional[np.ndarray]:
        """人体 33 关键点 → 相机系米制 3D（深度优先，缺深度用相对 z 补全）。"""
        n = len(pts_norm)
        if intrinsics is None:
            return None
        fx, fy = intrinsics.get("fx", 640.0), intrinsics.get("fy", 640.0)
        ppx, ppy = intrinsics.get("ppx", 320.0), intrinsics.get("ppy", 240.0)
        h = depth.shape[0] if depth is not None else 480
        w = depth.shape[1] if depth is not None else 640

        pts_3d = np.zeros((n, 3), dtype=np.float64)
        # 参考深度：髋部中点（pose 23/24 平均）或肩部
        ref_z = 800.0
        if depth is not None:
            for idx in (23, 24, 11, 12):
                if idx < n:
                    u = int(pts_norm[idx][0] * w)
                    v = int(pts_norm[idx][1] * h)
                    if 0 <= v < h and 0 <= u < w:
                        zz = float(depth[v, u])
                        if 0 < zz < 3000:
                            ref_z = zz
                            break
        for i, (nx, ny, rel_z) in enumerate(pts_norm):
            u, v = nx * w, ny * h
            z_mm = 0.0
            if depth is not None:
                ui, vi = int(round(u)), int(round(v))
                if 0 <= vi < h and 0 <= ui < w:
                    z_mm = float(depth[vi, ui])
            if not (0 < z_mm < 3000):
                z_mm = ref_z + float(rel_z) * 300.0  # 相对深度粗补全
                if z_mm < 100:
                    z_mm = 100.0
            z = z_mm / 1000.0
            x = (u - ppx) * z / fx
            y = (v - ppy) * z / fy
            pts_3d[i] = [x, y, z]
        return pts_3d

    # ------------------------------------------------------------------
    def draw_skeleton(
        self,
        frame: np.ndarray,
        results: Sequence[HolisticResult],
        pose_color=(0, 255, 0),
        hand_color=(0, 255, 255),
        line_px: int = 2,
    ) -> np.ndarray:
        """绘制人体 + 手部骨架。"""
        import cv2
        out = frame.copy()
        if not results:
            return out
        h, w = out.shape[:2]
        r = results[0]
        # 人体
        if r.pose_landmarks is not None:
            pts = r.pose_landmarks
            for a, b in POSE_CONNECTIONS:
                if a < len(pts) and b < len(pts):
                    p1 = (int(pts[a][0] * w), int(pts[a][1] * h))
                    p2 = (int(pts[b][0] * w), int(pts[b][1] * h))
                    cv2.line(out, p1, p2, pose_color, line_px, cv2.LINE_AA)
            for p in pts:
                cv2.circle(out, (int(p[0] * w), int(p[1] * h)),
                           3, (0, 0, 255), -1, cv2.LINE_AA)
        # 手部
        if r.hand_landmarks is not None:
            pts = r.hand_landmarks
            for a, b in HAND_CONNECTIONS:
                p1 = (int(pts[a][0] * w), int(pts[a][1] * h))
                p2 = (int(pts[b][0] * w), int(pts[b][1] * h))
                cv2.line(out, p1, p2, hand_color, line_px, cv2.LINE_AA)
            for p in pts:
                cv2.circle(out, (int(p[0] * w), int(p[1] * h)),
                           3, (255, 0, 255), -1, cv2.LINE_AA)
        return out

    def close(self):
        """释放模型资源。"""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
        self._landmarker = None


def bgr2rgb(bgr: np.ndarray) -> np.ndarray:
    """BGR → RGB。"""
    return bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr


if __name__ == "__main__":
    # 自测：模型加载 + 空帧处理（不接摄像头）
    est = HolisticPoseEstimator()
    print("HolisticPoseEstimator loaded OK")
    empty = np.zeros((480, 640, 3), dtype=np.uint8)
    res = est.process(empty)
    print(f"空帧结果数: {len(res)}（应为 0）")
    est.close()
    print("自测通过")
