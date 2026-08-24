# -*- coding: utf-8 -*-
"""
hand_pose.py —— 手部姿态估计模块（深度+3D几何）

功能概述：
1. 使用 MediaPipe 检测手部关键点（21个标准手部关键点）
2. 结合深度图（可选）将2D关键点转换为3D坐标
3. 计算16个手部关节角度（四指弯曲、拇指弯曲、手指侧摆、拇指外展）
4. 支持自定义参数调整（缩放、偏移、增益、死区等）
5. 提供手部骨架可视化功能

拇指内外展特殊处理：
- 直接使用横向距离（不归一化），外展→0°，内收→110°
- 通过 thumb_abd_offset 和 thumb_abd_gain 参数调节映射关系

关节角度索引说明（共16个）：
- 索引 0:  拇指侧摆 (swing)
- 索引 1:  拇指近端弯曲 (proximal)
- 索引 2:  拇指远端弯曲 (distal)
- 索引 3:  食指侧摆 (swing)
- 索引 4:  食指近端弯曲 (proximal)
- 索引 5:  食指远端弯曲 (distal)
- 索引 6:  中指侧摆 (swing)
- 索引 7:  中指近端弯曲 (proximal)
- 索引 8:  中指远端弯曲 (distal)
- 索引 9:  无名指侧摆 (swing)
- 索引 10: 无名指近端弯曲 (proximal)
- 索引 11: 无名指远端弯曲 (distal)
- 索引 12: 小指侧摆 (swing)
- 索引 13: 小指近端弯曲 (proximal)
- 索引 14: 小指远端弯曲 (distal)
- 索引 15: 拇指内外展 (abduction/adduction)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

# 尝试导入 MediaPipe，如果失败则设置标志位
try:
    import mediapipe as mp

    _MP_OK = True
except ImportError:
    mp = None
    _MP_OK = False

# ==================== MediaPipe 手部关键点索引定义 ====================
# 标准手部21个关键点编号（从0到20）
WRIST = 0  # 手腕
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4  # 拇指：腕掌、掌指、指间、指尖
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8  # 食指：掌指、近端、远端、指尖
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12  # 中指
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16  # 无名指
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20  # 小指

# 每根手指的关键点索引映射（用于遍历计算弯曲角度）
FINGER_LANDMARKS = {
    "thumb": (THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP),
    "index": (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
}
FINGER_ORDER = ["thumb", "index", "middle", "ring", "pinky"]  # 手指遍历顺序

# 手部骨架连接关系（用于绘制）
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),  # 拇指链
    (0, 5), (5, 6), (6, 7), (7, 8),  # 食指链
    (5, 9), (9, 10), (10, 11), (11, 12),  # 中指链（从食指MCP分叉）
    (9, 13), (13, 14), (14, 15), (15, 16),  # 无名指链（从中指MCP分叉）
    (13, 17), (17, 18), (18, 19), (19, 20),  # 小指链（从无名指MCP分叉）
    (0, 17),  # 手掌横跨（手腕到小指MCP）
]

# ==================== 模型文件配置 ====================
DEFAULT_MODEL_NAME = "hand_landmarker.task"  # 模型文件名
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)  # 官方模型下载地址


def _find_model_file(model_path: Optional[str] = None) -> Optional[str]:
    """
    查找手部模型文件

    搜索顺序：
    1. 用户指定的路径
    2. 当前工作目录
    3. 项目根目录（当前文件所在目录的上两级）
    4. lib/ 子目录
    5. 当前文件所在目录

    参数:
        model_path: 用户指定的模型路径（可选）

    返回:
        找到的模型文件完整路径，如果未找到则返回 None
    """
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
    计算两个三维向量之间的夹角（度）

    参数:
        a: 第一个向量 (3,)
        b: 第二个向量 (3,)

    返回:
        夹角（度），范围 [0, 180]
        如果任一向量模长接近0，返回0
    """
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-6 or nb < 1e-6:
        return 0.0
    cos = float(np.dot(a, b) / (na * nb))
    cos = max(-1.0, min(1.0, cos))  # 防止数值溢出
    return math.degrees(math.acos(cos))


@dataclass
class HandResult:
    """
    单只手部检测结果数据类

    属性:
        landmarks: 21个关键点的归一化坐标 (21, 3)，范围 [0,1]
        handedness: 左右手标识，"Left" / "Right" / "unknown"
        joint_angles_deg: 16个关节角度（度）
        confidence: 检测置信度 [0, 1]
        hand_depth_mm: 手腕处深度值（毫米），来自深度图
        avg_depth_mm: 手掌关键点平均深度（毫米），来自深度图
        lateral_dist: 拇指横向距离（米），用于拇指外展计算
    """
    landmarks: np.ndarray
    handedness: str = "unknown"
    joint_angles_deg: List[float] = field(default_factory=lambda: [0.0] * 16)
    confidence: float = 0.0
    hand_depth_mm: Optional[float] = None
    avg_depth_mm: Optional[float] = None
    lateral_dist: Optional[float] = None  # 直接存储横向距离，用于调试
    fist_confidence: Optional[float] = None  # 深度辅助握拳置信度 [0,1]，None=无深度

    @property
    def joint_angles_rad(self) -> List[float]:
        """将关节角度从度转换为弧度"""
        return [math.radians(a) for a in self.joint_angles_deg]

    @property
    def visible(self) -> bool:
        """检查是否检测到手部"""
        return self.landmarks is not None


class HandPoseEstimator:
    """
    手部姿态估计器主类

    功能：
    1. 加载 MediaPipe 手部关键点检测模型
    2. 处理 RGB 图像，检测手部关键点
    3. 可选：结合深度图生成3D坐标
    4. 计算16个关节角度
    5. 支持实时参数调整

    使用示例:
        estimator = HandPoseEstimator()
        results = estimator.process(rgb_image, depth_image, intrinsics)
        angles = results[0].joint_angles_deg
    """

    def __init__(
            self,
            max_hands: int = 1,  # 最大检测手数
            min_detection_confidence: float = 0.5,  # 检测置信度阈值
            min_tracking_confidence: float = 0.5,  # 跟踪置信度阈值
            bend_scale: float = 1.0,  # 弯曲角度全局缩放
            bend_offset: float = 0.0,  # 弯曲角度全局偏移
            bend_gain: float = 1.0,  # 弯曲角度全局增益
            deadzone_deg: float = 1.0,  # 角度死区（小于此值置0）
            bend_reverse: bool = False,  # 是否反转弯曲角度
            use_distance_ratio: bool = False,  # 是否使用距离比率法计算弯曲
            per_finger_scale: Optional[dict] = None,  # 每指缩放
            per_finger_offset: Optional[dict] = None,  # 每指偏移
            model_path: Optional[str] = None,  # 模型文件路径
            # 拇指内外展直接映射参数（不归一化）
            thumb_abd_offset: float = 0.0,  # 死区（手掌宽度倍数，0~0.3）
            thumb_abd_gain: float = 0.8,   # 有效区增益（放大归一化横向距离）
            thumb_abd_reverse: bool = False,  # 是否反转映射方向
    ):
        """
        初始化手部姿态估计器

        参数:
            max_hands: 最大检测手部数量
            min_detection_confidence: 检测阶段的最小置信度
            min_tracking_confidence: 跟踪阶段的最小置信度
            bend_scale: 所有手指弯曲角度的全局缩放系数
            bend_offset: 所有手指弯曲角度的全局偏移量（度）
            bend_gain: 所有手指弯曲角度的全局增益（乘法因子）
            deadzone_deg: 死区阈值（度），小于此值的角度将被置为0
            bend_reverse: 是否反转弯曲角度（用于特殊映射需求）
            use_distance_ratio: 使用距离比率法计算弯曲（基于三点距离比）
            per_finger_scale: 每根手指的独立缩放系数，如 {"index": 0.8}
            per_finger_offset: 每根手指的独立偏移量，如 {"index": 5.0}
            model_path: 手部模型文件的路径
            thumb_abd_offset: 拇指内收死区（拇指长度倍数，默认0；手指并拢时若输出
                               非0，增大此值切除底部无效区间）
            thumb_abd_gain: 有效区增益（归一化横向距离的放大系数，默认2.0）
            thumb_abd_reverse: 是否反转拇指外展映射（True: 外展→110°, 内收→0°）
        """
        # 检查 MediaPipe 是否可用
        if not _MP_OK:
            raise RuntimeError("请先安装 mediapipe>=0.10.14：pip install mediapipe")

        # 查找模型文件
        model_file = _find_model_file(model_path)
        if model_file is None:
            raise RuntimeError(
                f"未找到手部模型文件 {DEFAULT_MODEL_NAME}。请下载并放到项目根目录或 lib/：\n"
                f"  {MODEL_DOWNLOAD_URL}"
            )
        self.model_path = model_file

        # 创建 MediaPipe HandLandmarker
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        base_options = mp_python.BaseOptions(model_asset_path=model_file)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
            running_mode=vision.RunningMode.IMAGE,  # 图像模式（非视频流）
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

        # 存储弯曲参数
        self.bend_scale = bend_scale
        self.bend_offset = bend_offset
        self.bend_gain = max(0.1, float(bend_gain))
        self.deadzone_deg = float(deadzone_deg)
        self.bend_reverse = bool(bend_reverse)
        self.use_distance_ratio = bool(use_distance_ratio)
        self.per_finger_scale = dict(per_finger_scale or {})
        self.per_finger_offset = dict(per_finger_offset or {})
        self._frame_scale = 1.0

        # 存储拇指外展参数
        self.thumb_abd_offset = float(thumb_abd_offset)
        self.thumb_abd_gain = max(0.1, float(thumb_abd_gain))
        self.thumb_abd_reverse = bool(thumb_abd_reverse)

    def update_params(self, **kwargs):
        """
        动态更新估计器参数

        支持的参数:
            bend_scale, bend_offset, bend_gain, deadzone_deg, bend_reverse,
            use_distance_ratio, per_finger_scale, per_finger_offset,
            thumb_abd_offset, thumb_abd_gain, thumb_abd_reverse

        示例:
            estimator.update_params(bend_scale=0.8, deadzone_deg=2.0)
        """
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
                self.use_distance_ratio = bool(v)
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

    @staticmethod
    def _convert_landmarks_to_3d(
            landmarks_norm: np.ndarray,  # 归一化2D坐标 (21, 3)
            depth: np.ndarray,  # 深度图 (H, W)
            intrinsics: dict  # 相机内参 {fx, fy, ppx, ppy}
    ) -> np.ndarray:
        """
        将归一化的2D关键点转换为相机坐标系下的3D坐标

        转换原理：使用针孔相机模型
            X = (u - cx) * Z / fx
            Y = (v - cy) * Z / fy
            Z = depth[u, v] / 1000.0  (转换为米)

        参数:
            landmarks_norm: 归一化坐标 (21, 3)，x,y范围[0,1]
            depth: 深度图 (H, W)，单位毫米
            intrinsics: 相机内参，包含 fx, fy, ppx, ppy

        返回:
            3D坐标数组 (21, 3)，单位米，无效点设为 NaN
        """
        h, w = depth.shape[:2]
        fx = intrinsics['fx']
        fy = intrinsics['fy']
        ppx = intrinsics['ppx']
        ppy = intrinsics['ppy']
        pts_3d = np.zeros_like(landmarks_norm, dtype=np.float64)

        for i, (nx, ny, _) in enumerate(landmarks_norm):
            u = int(nx * w)
            v = int(ny * h)
            if 0 <= v < h and 0 <= u < w:
                z_mm = float(depth[v, u])
                if z_mm > 0 and z_mm < 3000:  # 有效深度范围 0-3000mm
                    z = z_mm / 1000.0  # 转换为米
                    x = (u - ppx) * z / fx
                    y = (v - ppy) * z / fy
                    pts_3d[i] = [x, y, z]
                else:
                    pts_3d[i] = [float('nan'), float('nan'), float('nan')]
            else:
                pts_3d[i] = [float('nan'), float('nan'), float('nan')]
        return pts_3d

    def process(
            self,
            rgb_bgr: np.ndarray,  # BGR 格式的 RGB 图像
            depth: Optional[np.ndarray] = None,  # 深度图（可选）
            intrinsics: Optional[dict] = None  # 相机内参（可选）
    ) -> List[HandResult]:
        """
        处理单张图像，检测手部并计算关节角度

        参数:
            rgb_bgr: BGR格式图像 (H, W, 3)，uint8
            depth: 深度图 (H, W)，单位毫米，float32
            intrinsics: 相机内参字典，包含 fx, fy, ppx, ppy

        返回:
            HandResult 列表，每个元素对应一只检测到的手
        """
        if rgb_bgr is None:
            return []
        rgb = bgr2rgb(rgb_bgr)  # BGR -> RGB

        # 转换为 MediaPipe 图像格式
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._landmarker.detect(mp_image)

        out: List[HandResult] = []
        if not res.hand_landmarks:
            return out

        # 提取左右手标签
        handedness = []
        for hh in res.handedness:
            if hh:
                cat = hh[0]
                handedness.append(cat.category_name or cat.display_name or "unknown")

        # 遍历每只手
        for i, lm in enumerate(res.hand_landmarks):
            # 提取归一化坐标 (21, 3)
            pts_norm = np.array([(p.x, p.y, p.z) for p in lm], dtype=np.float64)
            label = handedness[i] if i < len(handedness) else "unknown"
            conf = 0.5
            if res.handedness and i < len(res.handedness) and res.handedness[i]:
                conf = float(res.handedness[i][0].score)

            # 如果有深度图，生成3D坐标
            real_pts = None
            if depth is not None and intrinsics is not None:
                real_pts = self._convert_landmarks_to_3d(pts_norm, depth, intrinsics)

            # 计算关节角度
            angles, lateral_dist = self._landmarks_to_angles16(pts_norm, real_pts)

            # 获取手部深度信息
            hand_d, avg_d = None, None
            if depth is not None:
                hand_d, avg_d = self._hand_depth(depth, pts_norm)

            # 深度辅助握拳置信度：指尖到掌心的3D距离越小 → 越像握拳
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
        """
        深度辅助握拳置信度（核心：结合深度相机判别"真实握拳"）

        原理：MediaPipe 在握拳时指尖抖动大，但深度图（L515 RGB对齐）
        给出的指尖 3D 位置是真实的。用 4 指指尖到掌心中心的 3D 距离
        除以手掌宽度得到归一化"指尖到掌心距离比"：
            ratio = mean(||tip_i - palm_center||) / palm_w
        张开手 ratio≈1.5+，握拳 ratio≈0.4~0.7。
        映射到 [0,1]：ratio 越小置信度越高（越像握拳）。

        返回: [0,1] 置信度；无深度(real_pts 无效)时返回 None。
        """
        if real_pts is None or np.any(np.isnan(real_pts)):
            return None   # 无深度 → 无法用深度确认，交由方向一致性检测兜底
        pts = real_pts  # 单位米
        palm_center = (pts[WRIST] + pts[MIDDLE_MCP]) / 2.0
        palm_w = float(np.linalg.norm(pts[MIDDLE_MCP] - palm_center))
        if palm_w < 1e-6:
            palm_w = 0.02
        tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
        dists = [np.linalg.norm(pts[t] - palm_center) for t in tips]
        ratio = float(np.mean(dists)) / palm_w
        # 标定（实测半掌宽 palm_w≈0.04~0.05m）：
        #   张开手  指尖-掌心距离≈0.10~0.12m → ratio≈2.0~3.0
        #   握拳    指尖-掌心距离≈0.03~0.05m → ratio≈0.7~1.1
        # 线性映射：ratio<=0.9 → 1.0（确认握拳），ratio>=1.6 → 0.0（张开）
        conf = (1.6 - ratio) / (1.6 - 0.9)
        return float(np.clip(conf, 0.0, 1.0))

    def _hand_depth(self, depth: np.ndarray, pts: np.ndarray):
        """
        从深度图中提取手部深度值

        参数:
            depth: 深度图
            pts: 归一化关键点坐标

        返回:
            (手腕处深度, 手掌关键点平均深度)，单位毫米
        """
        try:
            h, w = depth.shape[:2]
            u = int(pts[WRIST][0] * w)
            v = int(pts[WRIST][1] * h)
            hand_d = None
            if 0 <= v < h and 0 <= u < w:
                z = float(depth[v, u])
                if 0 < z < 3000:
                    hand_d = z

            # 计算手掌关键点平均深度（手腕+五指的MCP）
            vals = []
            for k in (0, 5, 9, 13, 17):  # WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP
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

    def _bend_ratio_by_distance(self, p1, p2, p3) -> float:
        """
        使用距离比率法计算弯曲程度

        原理：当手指弯曲时，p1-p3 距离变小，而 p1-p2 + p2-p3 基本不变
            ratio = 1 - |p1-p3| / (|p1-p2| + |p2-p3|)

        参数:
            p1, p2, p3: 三个连续关键点坐标

        返回:
            弯曲比率 [0, 1]，0表示伸直，1表示完全弯曲
        """
        d13 = np.linalg.norm(p1 - p3)
        d12 = np.linalg.norm(p1 - p2)
        d23 = np.linalg.norm(p2 - p3)
        denom = d12 + d23
        if denom < 1e-6:
            return 0.0
        ratio = 1.0 - d13 / denom
        return float(np.clip(ratio, 0.0, 1.0))

    def _landmarks_to_angles16(
            self,
            pts_norm: np.ndarray,  # 归一化坐标 (21, 3)
            real_pts: Optional[np.ndarray] = None  # 真实3D坐标 (21, 3)
    ) -> tuple[List[float], float]:
        """
        从关键点计算16个关节角度和拇指横向距离

        算法概述：
        1. 构建手掌局部坐标系（normal, palm_axis, perp）
        2. 计算手指侧摆角度（投影到手掌平面）
        3. 计算拇指外展（使用横向距离直接映射）
        4. 计算各手指弯曲角度（使用向量夹角或距离比率）

        参数:
            pts_norm: 归一化坐标
            real_pts: 真实3D坐标（如果有）

        返回:
            (16个角度列表, 拇指横向距离)
        """
        # 优先使用真实3D坐标，否则使用归一化坐标
        if real_pts is not None and not np.any(np.isnan(real_pts)):
            pts = real_pts
            is_real = True
        else:
            pts = pts_norm
            is_real = False

        angles = [0.0] * 16
        lateral_dist = 0.0

        # ========== 构建手掌局部坐标系 ==========
        wrist = pts[WRIST]
        mcp_mid = pts[MIDDLE_MCP]  # 中指MCP
        mcp_pinky = pts[PINKY_MCP]  # 小指MCP

        # 手掌法线：通过中指MCP到手腕向量 和 小指MCP到手腕向量的叉积
        v1 = mcp_mid - wrist
        v2 = mcp_pinky - wrist
        normal = np.cross(v1, v2)
        norm_n = np.linalg.norm(normal)
        if norm_n > 1e-8:
            normal = normal / norm_n
        else:
            normal = np.array([0, 0, 1]) if not is_real else np.array([0, 0, 1])

        # 手掌主轴：从中指MCP到手腕方向
        palm_axis = mcp_mid - wrist
        palm_len = np.linalg.norm(palm_axis)
        if palm_len > 1e-8:
            palm_axis = palm_axis / palm_len
        else:
            palm_axis = np.array([1, 0, 0])

        # 手掌横向轴：垂直于法线和主轴
        perp = np.cross(normal, palm_axis)
        perp_norm = np.linalg.norm(perp)
        if perp_norm > 1e-8:
            perp = perp / perp_norm
        else:
            perp = np.array([0, 1, 0])

        # ========== 1. 拇指侧摆（关节索引 0） ==========
        # 计算拇指CMC在手掌平面上的投影与主轴的夹角
        v_thumb = pts[THUMB_CMC] - wrist
        proj_thumb = v_thumb - np.dot(v_thumb, normal) * normal  # 投影到手掌平面
        if np.linalg.norm(proj_thumb) > 1e-8 and palm_len > 1e-8:
            cos_angle = np.dot(proj_thumb, palm_axis) / (np.linalg.norm(proj_thumb) * palm_len)
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = math.degrees(math.acos(cos_angle))
            sign = 1 if np.dot(proj_thumb, perp) > 0 else -1  # 侧摆方向
            angles[0] = sign * min(angle, 20)  # 限制最大20度
        else:
            angles[0] = 0

        # ========== 2. 四指侧摆（关节索引 3, 6, 9, 12） ==========
        finger_mcp_map = {
            "index": INDEX_MCP,
            "middle": MIDDLE_MCP,
            "ring": RING_MCP,
            "pinky": PINKY_MCP,
        }
        swing_idx_map = {
            "index": 3,
            "middle": 6,
            "ring": 9,
            "pinky": 12,
        }
        for fname, mcp_idx in finger_mcp_map.items():
            v_finger = pts[mcp_idx] - wrist
            proj = v_finger - np.dot(v_finger, normal) * normal
            if np.linalg.norm(proj) > 1e-8 and palm_len > 1e-8:
                cos_angle = np.dot(proj, palm_axis) / (np.linalg.norm(proj) * palm_len)
                cos_angle = np.clip(cos_angle, -1, 1)
                angle = math.degrees(math.acos(cos_angle))
                sign = 1 if np.dot(proj, perp) > 0 else -1
                angles[swing_idx_map[fname]] = sign * min(angle, 20)
            else:
                angles[swing_idx_map[fname]] = 0

        # ========== 3. 拇指内外展（关节索引 15） ==========
        # 无符号归一化距离比法（参考 vision_hand_ctrl.py）：
        #   1) lateral_dist = 拇指 TIP 到手掌中心 在 perp 方向的横向距离（绝对值）
        #      —— 用 TIP 而非 MCP：外展时指尖位移最明显、MCP 基本不动
        #   2) 标尺用"掌心→中指MCP"距离（手掌宽度），比拇指长度更稳定
        #   3) 死区(offset) + 增益(gain) -> 0~1
        #   4) 方向由 thumb_abd_reverse 开关控制（GUI 可切），映射到 0~110°
        # 注意：不用自动符号判断（翻掌/手型变化下会失效导致输出恒不变）
        palm_center = (wrist + mcp_mid) / 2.0
        v_tip_to_center = pts[THUMB_TIP] - palm_center
        lateral_dist = abs(float(np.dot(v_tip_to_center, perp)))

        # 标尺：手掌宽度（掌心→中指MCP），尺度不变、对距离鲁棒
        palm_w = float(np.linalg.norm(mcp_mid - palm_center))
        if palm_w < 1e-6:
            palm_w = 0.01

        ratio = lateral_dist / palm_w

        # 死区切除 + 有效区放大（线性）
        abd_ratio = (ratio - self.thumb_abd_offset) * self.thumb_abd_gain
        abd_ratio = np.clip(abd_ratio, 0.0, 1.0)

        # 软饱和（sigmoid 类）：小位移敏感、大位移渐缓，避免过早饱和失去区分度
        # 映射 x in [0,1] -> 0~1，中段线性、两端压缩
        abd_ratio = 3.0 * abd_ratio * abd_ratio - 2.0 * abd_ratio * abd_ratio * abd_ratio
        abd_ratio = float(np.clip(abd_ratio, 0.0, 1.0))

        # 方向：由开关决定 内收↔110° / 外展↔0°
        if self.thumb_abd_reverse:
            abduction = abd_ratio * 110.0
        else:
            abduction = (1.0 - abd_ratio) * 110.0
        angles[15] = np.clip(abduction, 0, 110)

        # ========== 4. 拇指弯曲（关节索引 1, 2） ==========
        v_cmc_to_mcp = pts[THUMB_MCP] - pts[THUMB_CMC]
        v_mcp_to_ip = pts[THUMB_IP] - pts[THUMB_MCP]
        v_ip_to_tip = pts[THUMB_TIP] - pts[THUMB_IP]

        theta_prox = _angle_between(v_cmc_to_mcp, v_mcp_to_ip)  # 近端弯曲（MCP）
        theta_dist = _angle_between(v_mcp_to_ip, v_ip_to_tip)  # 远端弯曲（IP）
        theta_prox = np.clip(theta_prox, 0, 90)
        theta_dist = np.clip(theta_dist, 0, 75)
        angles[1] = theta_prox
        angles[2] = theta_dist

        # ========== 5. 四指弯曲（关节索引 4,5, 7,8, 10,11, 13,14） ==========
        for finger_idx, finger in enumerate(FINGER_ORDER):
            if finger == "thumb":
                continue
            base = finger_idx * 3  # 每个手指占3个关节（侧摆+近端+远端）
            mcp, pip, dip, tip = FINGER_LANDMARKS[finger]

            if self.use_distance_ratio:
                # 使用距离比率法计算弯曲
                ratio = self._bend_ratio_by_distance(pts[mcp], pts[pip], pts[tip])
                theta_prox = ratio * 90.0
                theta_dist = ratio * 75.0
            else:
                # 使用向量夹角法计算弯曲
                v_wrist_to_mcp = pts[mcp] - wrist
                v_mcp_to_pip = pts[pip] - pts[mcp]
                v_pip_to_dip = pts[dip] - pts[pip]

                angle_prox = _angle_between(v_wrist_to_mcp, v_mcp_to_pip)
                angle_dist = _angle_between(v_mcp_to_pip, v_pip_to_dip)
                theta_prox = np.clip(angle_prox, 0, 90)
                theta_dist = np.clip(angle_dist, 0, 75)

            # 应用全局和每指校准参数
            theta_prox = (theta_prox * self.bend_scale + self.bend_offset) * self.bend_gain
            theta_dist = (theta_dist * self.bend_scale + self.bend_offset) * self.bend_gain
            s = self.per_finger_scale.get(finger, 1.0)
            o = self.per_finger_offset.get(finger, 0.0)
            theta_prox = theta_prox * s + o
            theta_dist = theta_dist * s + o

            # 可选反转
            if self.bend_reverse:
                theta_prox = 90.0 - theta_prox
                theta_dist = 75.0 - theta_dist

            # 死区处理
            if theta_prox < self.deadzone_deg:
                theta_prox = 0.0
            if theta_dist < self.deadzone_deg:
                theta_dist = 0.0

            # 裁剪到有效范围
            theta_prox = np.clip(theta_prox, 0, 90)
            theta_dist = np.clip(theta_dist, 0, 75)

            angles[base + 1] = theta_prox  # 近端弯曲
            angles[base + 2] = theta_dist  # 远端弯曲

        return angles, lateral_dist

    def draw_skeleton(self, frame: np.ndarray,
                      results: Sequence[HandResult],
                      color=(0, 255, 0), line_px: int = 2) -> np.ndarray:
        """
        在图像上绘制手部骨架

        参数:
            frame: 输入图像 (H, W, 3)
            results: HandResult 列表
            color: 线条颜色 (B, G, R)
            line_px: 线条粗细（像素）

        返回:
            绘制了骨架的图像
        """
        import cv2
        out = frame.copy()
        if not results:
            return out
        h, w = out.shape[:2]
        for r in results:
            pts = r.landmarks
            # 绘制连接线
            for a, b in HAND_CONNECTIONS:
                p1 = (int(pts[a][0] * w), int(pts[a][1] * h))
                p2 = (int(pts[b][0] * w), int(pts[b][1] * h))
                cv2.line(out, p1, p2, color, line_px, cv2.LINE_AA)
            # 绘制关键点
            for p in pts:
                cv2.circle(out, (int(p[0] * w), int(p[1] * h)),
                           4, (0, 0, 255), -1, cv2.LINE_AA)
        return out

    def close(self):
        """释放 MediaPipe 资源"""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass


def bgr2rgb(bgr: np.ndarray) -> np.ndarray:
    """
    将 BGR 图像转换为 RGB 格式

    参数:
        bgr: BGR 图像 (H, W, 3)

    返回:
        RGB 图像 (H, W, 3)
    """
    return bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr