# -*- coding: utf-8 -*-
"""
hand_pose.py —— 手部姿态估计模块（强制3D向量夹角法）

设计核心原则：
1. 所有弯曲角度（MCP和PIP）严格独立计算，采用三维向量夹角法（acos）。
2. 绝对禁止使用距离比率法，因为它会耦合MCP和PIP，且对近端弯曲不敏感。
3. 始终使用带Z轴的3D坐标（通过补全确保无NaN），绝不回退到纯2D。
4. Z轴补全的物理尺度必须真实（缩放因子0.5），否则向量方向畸变导致角度错误。
5. ★★★ 拇指弯曲（索引1和2）已纳入完整校准链，与四指完全一致。 ★★★

关节索引说明：
- 索引 0: 拇指侧摆
- 索引 1: 拇指近端弯曲 (MCP) —— 已纳入校准链
- 索引 2: 拇指远端弯曲 (PIP) —— 已纳入校准链
- 索引 3,6,9,12: 食/中/无/小指侧摆
- 索引 4,7,10,13: 食/中/无/小指近端弯曲 (MCP)
- 索引 5,8,11,14: 食/中/无/小指远端弯曲 (PIP)
- 索引 15: 拇指内外展
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

try:
    import mediapipe as mp
    _MP_OK = True
except ImportError:
    mp = None
    _MP_OK = False

# ==================== MediaPipe 手部关键点索引定义 ====================
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_LANDMARKS = {
    "thumb": (THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP),
    "index": (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
}
FINGER_ORDER = ["thumb", "index", "middle", "ring", "pinky"]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

DEFAULT_MODEL_NAME = "hand_landmarker.task"
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def _find_model_file(model_path: Optional[str] = None) -> Optional[str]:
    if model_path:
        return model_path if os.path.exists(model_path) else None
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    for d in (os.getcwd(), project_root, os.path.join(project_root, "lib"), here):
        p = os.path.join(d, DEFAULT_MODEL_NAME)
        if os.path.exists(p):
            return p
    return None


def _angle_between(a: np.ndarray, b: np.ndarray) -> float:
    """
    计算两个三维向量的夹角（度），范围 [0, 180]。
    设计原因：这是所有弯曲角度（MCP/PIP）的计算基础，直接反映关节的旋转弧度。
    """
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-6 or nb < 1e-6:
        return 0.0
    cos = float(np.dot(a, b) / (na * nb))
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


@dataclass
class HandResult:
    landmarks: np.ndarray
    handedness: str = "unknown"
    joint_angles_deg: List[float] = field(default_factory=lambda: [0.0] * 16)
    confidence: float = 0.0
    hand_depth_mm: Optional[float] = None
    avg_depth_mm: Optional[float] = None
    lateral_dist: Optional[float] = None
    fist_confidence: Optional[float] = None

    @property
    def joint_angles_rad(self) -> List[float]:
        return [math.radians(a) for a in self.joint_angles_deg]

    @property
    def visible(self) -> bool:
        return self.landmarks is not None


class HandPoseEstimator:
    """
    手部姿态估计器，强制使用3D向量夹角法计算弯曲角度。
    所有弯曲角度（包括拇指）都经过完整的校准链。
    """

    def __init__(
            self,
            max_hands: int = 1,
            min_detection_confidence: float = 0.5,
            min_tracking_confidence: float = 0.5,
            bend_scale: float = 1.0,
            bend_offset: float = 0.0,
            bend_gain: float = 1.0,
            deadzone_deg: float = 1.0,
            bend_reverse: bool = False,
            per_finger_scale: Optional[dict] = None,
            per_finger_offset: Optional[dict] = None,
            per_finger_swing_offset: Optional[dict] = None,
            model_path: Optional[str] = None,
            thumb_abd_offset: float = 0.0,
            thumb_abd_gain: float = 0.8,
            thumb_abd_reverse: bool = False,
            swing_reverse: bool = False,
    ):
        if not _MP_OK:
            raise RuntimeError("请安装 mediapipe>=0.10.14")

        model_file = _find_model_file(model_path)
        if model_file is None:
            raise RuntimeError(
                f"未找到模型文件 {DEFAULT_MODEL_NAME}，请下载：{MODEL_DOWNLOAD_URL}"
            )
        self.model_path = model_file

        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        base_options = mp_python.BaseOptions(model_asset_path=model_file)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
            running_mode=vision.RunningMode.IMAGE,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

        self.bend_scale = bend_scale
        self.bend_offset = bend_offset
        self.bend_gain = max(0.1, float(bend_gain))
        self.deadzone_deg = float(deadzone_deg)
        self.bend_reverse = bool(bend_reverse)
        self.per_finger_scale = dict(per_finger_scale or {})
        self.per_finger_offset = dict(per_finger_offset or {})
        self.per_finger_swing_offset = dict(per_finger_swing_offset or {})
        self.swing_reverse = bool(swing_reverse)
        self._frame_scale = 1.0

        self.thumb_abd_offset = float(thumb_abd_offset)
        self.thumb_abd_gain = max(0.1, float(thumb_abd_gain))
        self.thumb_abd_reverse = bool(thumb_abd_reverse)

    def update_params(self, **kwargs):
        """动态更新参数，忽略 use_distance_ratio"""
        for k, v in kwargs.items():
            if k == "bend_scale":
                self.bend_scale = float(v)
            elif k == "bend_offset":
                self.bend_offset = float(v)
            elif k == "bend_gain":
                self.bend_gain = max(0.1, float(v))
            elif k == "deadzone_deg":
                self.deadzone_deg = float(v)
            elif k == "bend_reverse":
                self.bend_reverse = bool(v)
            elif k == "use_distance_ratio":
                # 强制忽略，永远使用向量夹角法
                pass
            elif k == "per_finger_scale" and isinstance(v, dict):
                self.per_finger_scale.update({str(x): float(y) for x, y in v.items()})
            elif k == "per_finger_offset" and isinstance(v, dict):
                self.per_finger_offset.update({str(x): float(y) for x, y in v.items()})
            elif k == "thumb_abd_offset":
                self.thumb_abd_offset = float(v)
            elif k == "thumb_abd_gain":
                self.thumb_abd_gain = max(0.1, float(v))
            elif k == "thumb_abd_reverse":
                self.thumb_abd_reverse = bool(v)
            elif k == "per_finger_swing_offset" and isinstance(v, dict):
                self.per_finger_swing_offset.update({str(x): float(y) for x, y in v.items()})
            elif k == "swing_reverse":
                self.swing_reverse = bool(v)

    @staticmethod
    def _convert_landmarks_to_3d(
            landmarks_norm: np.ndarray,
            depth: Optional[np.ndarray],
            intrinsics: dict
    ) -> np.ndarray:
        """
        强制生成物理尺度统一的3D米制坐标。
        当深度无效时，利用MediaPipe相对深度补全Z轴，缩放因子0.5确保位移真实。
        设计原因：只有保证Z轴变化范围（约5~10cm）与真实握拳匹配，向量夹角才能正确反映MCP弯曲。
        """
        h, w = depth.shape[:2] if depth is not None else (480, 640)
        fx, fy = intrinsics['fx'], intrinsics['fy']
        ppx, ppy = intrinsics['ppx'], intrinsics['ppy']

        pts_3d = np.zeros_like(landmarks_norm, dtype=np.float64)

        wrist_z_mm = 600.0
        if depth is not None:
            wrist_u = int(landmarks_norm[WRIST][0] * w)
            wrist_v = int(landmarks_norm[WRIST][1] * h)
            if 0 <= wrist_v < h and 0 <= wrist_u < w:
                z_val = float(depth[wrist_v, wrist_u])
                if 0 < z_val < 3000:
                    wrist_z_mm = z_val

        for i, (nx, ny, rel_z) in enumerate(landmarks_norm):
            u = nx * w
            v = ny * h

            z_mm = 0.0
            if depth is not None:
                ui, vi = int(round(u)), int(round(v))
                if 0 <= vi < h and 0 <= ui < w:
                    z_mm = float(depth[vi, ui])

            if not (0 < z_mm < 3000):
                offset_m = float(rel_z) * 0.5  # 关键修正：0.5倍，使Z轴变化达5~10cm
                z_mm = wrist_z_mm + offset_m * 1000.0
                if z_mm < 50:
                    z_mm = 50.0

            z = z_mm / 1000.0
            x = (u - ppx) * z / fx
            y = (v - ppy) * z / fy
            pts_3d[i] = [x, y, z]

        return pts_3d

    def process(
            self,
            rgb_bgr: np.ndarray,
            depth: Optional[np.ndarray] = None,
            intrinsics: Optional[dict] = None
    ) -> List[HandResult]:
        if rgb_bgr is None:
            return []
        rgb = bgr2rgb(rgb_bgr)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._landmarker.detect(mp_image)

        out: List[HandResult] = []
        if not res.hand_landmarks:
            return out

        handedness = []
        for hh in res.handedness:
            if hh:
                cat = hh[0]
                handedness.append(cat.category_name or cat.display_name or "unknown")

        for i, lm in enumerate(res.hand_landmarks):
            pts_norm = np.array([(p.x, p.y, p.z) for p in lm], dtype=np.float64)
            label = handedness[i] if i < len(handedness) else "unknown"
            conf = 0.5
            if res.handedness and i < len(res.handedness) and res.handedness[i]:
                conf = float(res.handedness[i][0].score)

            # 强制生成3D坐标（即使内参缺失也尝试补全）
            if intrinsics is not None:
                real_pts = self._convert_landmarks_to_3d(pts_norm, depth, intrinsics)
            else:
                real_pts = pts_norm.copy()  # 保留z轴

            angles, lateral_dist = self._landmarks_to_angles16(real_pts)

            hand_d, avg_d = None, None
            if depth is not None:
                hand_d, avg_d = self._hand_depth(depth, pts_norm)

            fist_conf = self._compute_fist_confidence(pts_norm, real_pts)

            out.append(HandResult(
                landmarks=pts_norm,
                handedness=label,
                joint_angles_deg=angles,
                confidence=conf,
                hand_depth_mm=hand_d,
                avg_depth_mm=avg_d,
                lateral_dist=lateral_dist,
                fist_confidence=fist_conf,
            ))
        return out

    @staticmethod
    def _compute_fist_confidence(
            pts_norm: np.ndarray,
            real_pts: Optional[np.ndarray] = None
    ) -> Optional[float]:
        if real_pts is None or np.any(np.isnan(real_pts)):
            return None
        pts = real_pts
        palm_center = (pts[WRIST] + pts[MIDDLE_MCP]) / 2.0
        palm_w = float(np.linalg.norm(pts[MIDDLE_MCP] - palm_center))
        if palm_w < 1e-6:
            palm_w = 0.02
        tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
        dists = [np.linalg.norm(pts[t] - palm_center) for t in tips]
        ratio = float(np.mean(dists)) / palm_w
        conf = (1.6 - ratio) / (1.6 - 0.9)
        return float(np.clip(conf, 0.0, 1.0))

    def _hand_depth(self, depth: np.ndarray, pts: np.ndarray):
        try:
            h, w = depth.shape[:2]
            u = int(pts[WRIST][0] * w)
            v = int(pts[WRIST][1] * h)
            hand_d = None
            if 0 <= v < h and 0 <= u < w:
                z = float(depth[v, u])
                if 0 < z < 3000:
                    hand_d = z

            vals = []
            for k in (0, 5, 9, 13, 17):
                u2 = int(pts[k][0] * w)
                v2 = int(pts[k][1] * h)
                if 0 <= v2 < h and 0 <= u2 < w:
                    z2 = float(depth[v2, u2])
                    if 0 < z2 < 3000:
                        vals.append(z2)
            avg_d = float(np.mean(vals)) if vals else None
            return hand_d, avg_d
        except Exception:
            return None, None

    def _landmarks_to_angles16(self, pts: np.ndarray) -> tuple[List[float], float]:
        """
        核心角度计算。
        设计强制规则：
        1. 始终使用 pts（3D坐标）。
        2. 弯曲角度（MCP和PIP）使用独立向量夹角法，绝不使用距离比率。
        3. 侧摆和内外展使用投影法。
        4. ★★★ 所有弯曲角度（包括拇指）都经过完整的校准链。 ★★★
        """
        angles = [0.0] * 16
        lateral_dist = 0.0

        # ========== 1. 构建手掌局部坐标系 ==========
        wrist = pts[WRIST]
        mcp_mid = pts[MIDDLE_MCP]
        mcp_pinky = pts[PINKY_MCP]

        v1 = mcp_mid - wrist
        v2 = mcp_pinky - wrist
        normal = np.cross(v1, v2)
        norm_n = np.linalg.norm(normal)
        if norm_n > 1e-8:
            normal = normal / norm_n
        else:
            normal = np.array([0, 0, 1])

        palm_axis = mcp_mid - wrist
        palm_len = np.linalg.norm(palm_axis)
        if palm_len > 1e-8:
            palm_axis = palm_axis / palm_len
        else:
            palm_axis = np.array([1, 0, 0])

        perp = np.cross(normal, palm_axis)
        perp_norm = np.linalg.norm(perp)
        if perp_norm > 1e-8:
            perp = perp / perp_norm
        else:
            perp = np.array([0, 1, 0])

        # ========== 2. 拇指侧摆 ==========
        v_thumb = pts[THUMB_CMC] - wrist
        proj_thumb = v_thumb - np.dot(v_thumb, normal) * normal
        if np.linalg.norm(proj_thumb) > 1e-8 and palm_len > 1e-8:
            cos_angle = np.dot(proj_thumb, palm_axis) / (np.linalg.norm(proj_thumb) * palm_len)
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = math.degrees(math.acos(cos_angle))
            sign = 1 if np.dot(proj_thumb, perp) > 0 else -1
            thumb_swing = sign * min(angle, 20)
            if self.swing_reverse:
                thumb_swing = -thumb_swing
            angles[0] = thumb_swing
        else:
            angles[0] = 0

        # ========== 3. 四指侧摆 ==========
        finger_pip_map = {
            "index": (INDEX_MCP, INDEX_PIP),
            "middle": (MIDDLE_MCP, MIDDLE_PIP),
            "ring": (RING_MCP, RING_PIP),
            "pinky": (PINKY_MCP, PINKY_PIP),
        }
        swing_idx_map = {
            "index": 3,
            "middle": 6,
            "ring": 9,
            "pinky": 12,
        }
        for fname, (mcp_idx, pip_idx) in finger_pip_map.items():
            v_finger = pts[pip_idx] - pts[mcp_idx]
            proj = v_finger - np.dot(v_finger, normal) * normal
            proj_norm = np.linalg.norm(proj)
            if proj_norm > 1e-8 and palm_len > 1e-8:
                angle_rad = math.atan2(np.dot(proj, perp), np.dot(proj, palm_axis))
                angle_deg = math.degrees(angle_rad)
                offset = self.per_finger_swing_offset.get(fname, 0.0)
                swing = angle_deg - offset
                if self.swing_reverse:
                    swing = -swing
                swing = np.clip(swing, -20.0, 20.0)
                angles[swing_idx_map[fname]] = float(swing)
            else:
                angles[swing_idx_map[fname]] = 0.0

        # ========== 4. 拇指内外展 ==========
        palm_center = (wrist + mcp_mid) / 2.0
        v_tip_to_center = pts[THUMB_TIP] - palm_center
        lateral_dist = abs(float(np.dot(v_tip_to_center, perp)))
        palm_w = float(np.linalg.norm(mcp_mid - palm_center))
        if palm_w < 1e-6:
            palm_w = 0.01
        ratio = lateral_dist / palm_w
        abd_ratio = (ratio - self.thumb_abd_offset) * self.thumb_abd_gain
        abd_ratio = np.clip(abd_ratio, 0.0, 1.0)
        abd_ratio = 3.0 * abd_ratio * abd_ratio - 2.0 * abd_ratio * abd_ratio * abd_ratio
        abd_ratio = float(np.clip(abd_ratio, 0.0, 1.0))
        if self.thumb_abd_reverse:
            abduction = abd_ratio * 110.0
        else:
            abduction = (1.0 - abd_ratio) * 110.0
        angles[15] = np.clip(abduction, 0, 110)

        # ========== 5. 拇指弯曲（索引 1, 2） ==========
        # ★★★ 修复：拇指现在走完整的校准链，与四指完全一致 ★★★
        # 设计原因：原代码中拇指弯曲（索引1和2）未经过 bend_scale/bend_offset/bend_gain/
        # per_finger_scale/per_finger_offset/bend_reverse/deadzone_deg 等校准参数，
        # 导致 GUI 滑条（拇指增益、偏移、反转等）对拇指完全无效。
        # 修改后，拇指与四指使用完全相同的校准逻辑。
        v_cmc_to_mcp = pts[THUMB_MCP] - pts[THUMB_CMC]
        v_mcp_to_ip = pts[THUMB_IP] - pts[THUMB_MCP]
        v_ip_to_tip = pts[THUMB_TIP] - pts[THUMB_IP]

        # ---- 原始几何角度（0~90°, 0~75°） ----
        theta_prox_raw = np.clip(_angle_between(v_cmc_to_mcp, v_mcp_to_ip), 0, 90)
        theta_dist_raw = np.clip(_angle_between(v_mcp_to_ip, v_ip_to_tip), 0, 75)

        # ---- ★★★ 完整校准链 ★★★ ----
        # ① 全局校准 (scale → offset → gain)
        theta_prox = (theta_prox_raw * self.bend_scale + self.bend_offset) * self.bend_gain
        theta_dist = (theta_dist_raw * self.bend_scale + self.bend_offset) * self.bend_gain

        # ② 每指独立校准（从 per_finger_scale/offset 读取 "thumb" 键值）
        s = self.per_finger_scale.get("thumb", 1.0)
        o = self.per_finger_offset.get("thumb", 0.0)
        theta_prox = theta_prox * s + o
        theta_dist = theta_dist * s + o

        # ③ 可选反转（适用全局 bend_reverse）
        if self.bend_reverse:
            theta_prox = 90.0 - theta_prox
            theta_dist = 75.0 - theta_dist

        # ④ 死区（滤除微颤）
        if theta_prox < self.deadzone_deg:
            theta_prox = 0.0
        if theta_dist < self.deadzone_deg:
            theta_dist = 0.0

        # ⑤ 最终裁剪到硬件行程
        angles[1] = np.clip(theta_prox, 0, 90)
        angles[2] = np.clip(theta_dist, 0, 75)

        # ========== 6. 四指弯曲（强制独立向量夹角法） ==========
        # 设计原因：MCP 和 PIP 是解剖独立关节，必须使用各自的向量对。
        for finger_idx, finger in enumerate(FINGER_ORDER):
            if finger == "thumb":
                continue
            base = finger_idx * 3
            mcp, pip, dip, tip = FINGER_LANDMARKS[finger]

            # ---- 近端（MCP） ----
            v_wrist_to_mcp = pts[mcp] - wrist
            v_mcp_to_pip = pts[pip] - pts[mcp]
            angle_prox = _angle_between(v_wrist_to_mcp, v_mcp_to_pip)
            theta_prox = np.clip(angle_prox, 0, 90)

            # ---- 远端（PIP） ----
            v_pip_to_dip = pts[dip] - pts[pip]
            angle_dist = _angle_between(v_mcp_to_pip, v_pip_to_dip)
            theta_dist = np.clip(angle_dist, 0, 75)

            # ---- 校准链（与拇指完全一致） ----
            theta_prox = (theta_prox * self.bend_scale + self.bend_offset) * self.bend_gain
            theta_dist = (theta_dist * self.bend_scale + self.bend_offset) * self.bend_gain

            s = self.per_finger_scale.get(finger, 1.0)
            o = self.per_finger_offset.get(finger, 0.0)
            theta_prox = theta_prox * s + o
            theta_dist = theta_dist * s + o

            if self.bend_reverse:
                theta_prox = 90.0 - theta_prox
                theta_dist = 75.0 - theta_dist

            if theta_prox < self.deadzone_deg:
                theta_prox = 0.0
            if theta_dist < self.deadzone_deg:
                theta_dist = 0.0

            angles[base + 1] = np.clip(theta_prox, 0, 90)
            angles[base + 2] = np.clip(theta_dist, 0, 75)

        return angles, lateral_dist

    def draw_skeleton(self, frame: np.ndarray,
                      results: Sequence[HandResult],
                      color=(0, 255, 0), line_px: int = 2) -> np.ndarray:
        import cv2
        out = frame.copy()
        if not results:
            return out
        h, w = out.shape[:2]
        for r in results:
            pts = r.landmarks
            for a, b in HAND_CONNECTIONS:
                p1 = (int(pts[a][0] * w), int(pts[a][1] * h))
                p2 = (int(pts[b][0] * w), int(pts[b][1] * h))
                cv2.line(out, p1, p2, color, line_px, cv2.LINE_AA)
            for p in pts:
                cv2.circle(out, (int(p[0] * w), int(p[1] * h)),
                           4, (0, 0, 255), -1, cv2.LINE_AA)
        return out

    def close(self):
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass


def bgr2rgb(bgr: np.ndarray) -> np.ndarray:
    return bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr