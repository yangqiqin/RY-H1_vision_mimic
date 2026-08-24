# -*- coding: utf-8 -*-
"""
camera_module.py —— 摄像头模块（Windows / Ubuntu 通用）

统一封装"图像采集"，对外只提供 RGB 帧（深度帧可选）：
  * 普通 USB 摄像头（UVC，OpenCV VideoCapture）
  * Intel RealSense L515 / D435 等 RGB-D 相机（pyrealsense2，RGB + 深度 + 内参）

针对 MediaPipe LIVE_STREAM 模式增强：
  * 提供严格递增的帧时间戳（毫秒），用于 detect_async()
  * 深度与 RGB 已对齐（L515 标准）
  * 提供 3D 坐标批量转换工具

依赖：
  pip install opencv-python
  # RGB-D 相机才需要（L515 必须固定版本）：
  pip install pyrealsense2==2.54.2.5684

用法：
  from camera import CameraModule
  cam = CameraModule(source=0)                     # USB 摄像头
  cam = CameraModule(use_realsense=True)           # Intel L515
  rgb, depth, ts = cam.read(return_timestamp=True) # 获取帧和时间戳
  # 批量将归一化关键点转为 3D 坐标
  points_3d = cam.landmarks_to_3d(norm_landmarks, rgb.shape, depth)
  cam.release()
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger("camera")

# README_1.md：L515 必须的 pyrealsense2 版本（librealsense 2.55+ 已移除 L515）
L515_PYREALSENSE_VERSION = "2.54.2.5684"
LAST_REALSENSE_ERROR = ""


def check_realsense_devices() -> List[dict]:
    """列出所有已连接的 Intel RealSense 设备，并校验 pyrealsense2 版本。"""
    try:
        import pyrealsense2 as rs
    except ImportError:
        logger.error("未安装 pyrealsense2：请执行 pip install pyrealsense2==%s",
                     L515_PYREALSENSE_VERSION)
        return []

    _warn_if_wrong_version()

    out = []
    try:
        ctx = rs.context()
        devs = list(ctx.query_devices())
    except Exception as exc:
        hint = ""
        if "0x80070005" in str(exc) or "Access denied" in str(exc) or "拒绝访问" in str(exc):
            hint = ("\n  ⚠️ Windows 拒绝访问（0x80070005）：请尝试【以管理员身份运行】终端/程序，"
                    "或检查摄像头隐私权限（设置→隐私→相机）。")
        logger.error("pyrealsense2 设备枚举失败: %s%s", exc, hint)
        global LAST_REALSENSE_ERROR
        LAST_REALSENSE_ERROR = f"设备枚举失败: {exc}{hint}"
        return []
    for dev in devs:
        try:
            out.append({
                "serial": dev.get_info(rs.camera_info.serial_number),
                "name": dev.get_info(rs.camera_info.name),
                "fw": dev.get_info(rs.camera_info.firmware_version),
            })
        except Exception as exc:
            logger.warning("读取设备信息失败: %s", exc)
    return out


def _get_pyrealsense_version() -> str:
    try:
        import importlib.metadata as md
        return md.version("pyrealsense2") or "unknown"
    except Exception:
        try:
            import pyrealsense2 as rs
            return getattr(rs, "__version__", "unknown")
        except Exception:
            return "unknown"


def _warn_if_wrong_version() -> bool:
    ver = _get_pyrealsense_version()
    ok = str(ver).startswith("2.54")
    if not ok:
        logger.error(
            "pyrealsense2 版本 %s 不兼容 L515：librealsense 2.55+ 已移除 L515 支持。"
            "请执行：pip install pyrealsense2==%s",
            ver, L515_PYREALSENSE_VERSION)
    return ok


class CameraModule:
    """摄像头采集模块，支持普通 USB 和 Intel RealSense RGB-D 相机。"""

    def __init__(
        self,
        source: int = 0,
        use_realsense: bool = False,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        serial: Optional[str] = None,
        depth_width: int = 1024,
        depth_height: int = 768,
        depth_fps: int = 30,
    ):
        """
        Args:
            source:        普通摄像头索引（OpenCV），默认 0
            use_realsense: 是否使用 Intel RealSense（L515/D435 等）
            width/height:  RGB 流分辨率。默认 1280x720（L515 常用）
            fps:           RGB 流帧率（默认 30）
            serial:        RealSense 设备序列号（多设备时指定；None=第一台）
            depth_width / depth_height / depth_fps: 深度流独立分辨率，默认 1024x768
        """
        self.use_realsense = use_realsense
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_width = depth_width
        self.depth_height = depth_height
        self.depth_fps = depth_fps
        self._align = None           # rs.align：深度对齐到彩色
        self._rs_pipeline = None
        self._rs_profile = None
        self._cap = None
        self._intrinsics = None

        # 帧时间戳计数器（用于 LIVE_STREAM 模式，严格递增）
        self._frame_timestamp = 0

        if use_realsense:
            self._open_realsense(serial)
        else:
            self._open_usb(source)

    # ------------------------------------------------------------------
    def _open_usb(self, source: int):
        self._cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(source)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 source={source}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        logger.info("USB 摄像头已打开 source=%s", source)

    def _open_realsense(self, serial: Optional[str]):
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError(
                f"使用 RGB-D 相机需先安装 pyrealsense2（L515 必须固定版本）："
                f"pip install pyrealsense2=={L515_PYREALSENSE_VERSION}") from exc

        if not _warn_if_wrong_version():
            raise RuntimeError(
                f"pyrealsense2 版本不兼容 L515：请执行 pip install pyrealsense2=={L515_PYREALSENSE_VERSION}")

        ctx = rs.context()
        try:
            devs = list(ctx.query_devices())
        except Exception as exc:
            hint = ("  ⚠️ Windows 拒绝访问（0x80070005）：请【以管理员身份运行】，"
                    "或检查设置→隐私→相机权限。") if "0x80070005" in str(exc) else ""
            raise RuntimeError(f"RealSense 设备枚举失败（权限/运行时）: {exc}\n{hint}") from exc
        if len(devs) == 0:
            raise RuntimeError(
                "未找到 RealSense 设备。请检查：\n"
                "  1. pyrealsense2 版本（必须 2.54.x）\n"
                "  2. USB3.0 直连\n"
                "  3. 安装 Intel RealSense SDK 2.0 运行时\n"
                "  4. 先用官方 RealSense Viewer 验证")
        if serial is None:
            serial = devs[0].get_info(rs.camera_info.serial_number)

        self._rs_pipeline = rs.pipeline()
        cfg = rs.config()
        cfg.enable_device(serial)
        cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        try:
            cfg.enable_stream(rs.stream.depth, self.depth_width, self.depth_height,
                              rs.format.z16, self.depth_fps)
        except Exception as exc:
            logger.warning("深度流配置失败（仅用 RGB）：%s", exc)

        try:
            self._rs_profile = self._rs_pipeline.start(cfg)
        except Exception as exc:
            self._rs_pipeline = None
            raise RuntimeError(
                f"RealSense 流启动失败：{exc}\n"
                f"  请检查分辨率组合（当前 RGB {self.width}x{self.height} + "
                f"深度 {self.depth_width}x{self.depth_height}）。\n"
                f"  L515 标准参数：depth 1024x768 + RGB 1280x720 @30FPS") from exc

        # 深度对齐到彩色（确保像素一一对应）
        try:
            self._align = rs.align(rs.stream.color)
        except Exception:
            self._align = None

        color_profile = self._rs_profile.get_stream(rs.stream.color)
        intr = color_profile.as_video_stream_profile().get_intrinsics()
        self._intrinsics = {
            "fx": intr.fx, "fy": intr.fy,
            "ppx": intr.ppx, "ppy": intr.ppy,
            "width": intr.width, "height": intr.height,
            "model": intr.model,
        }
        logger.info("RealSense %s 已打开（RGB %dx%d + 深度 %dx%d%s）",
                    serial, self.width, self.height,
                    self.depth_width, self.depth_height,
                    "，深度已对齐到彩色" if self._align else "")

    # ------------------------------------------------------------------
    def read(self, return_timestamp: bool = False, timeout_ms: int = 5000) -> Union[
        Tuple[Optional[np.ndarray], Optional[np.ndarray]],
        Tuple[Optional[np.ndarray], Optional[np.ndarray], int]
    ]:
        """
        读取一帧。

        Args:
            return_timestamp: 若为 True，额外返回一个严格递增的时间戳（毫秒），
                              用于 MediaPipe LIVE_STREAM 模式。
            timeout_ms: RealSense 等待超时时间（毫秒）。

        Returns:
            (rgb_bgr, depth) 或 (rgb_bgr, depth, timestamp_ms)。
            USB 摄像头：depth = None。
            RealSense：depth 为对齐到 RGB 的 uint16 深度图（单位 mm）。
            失败时返回 (None, None) 或 (None, None, 0)。
        """
        rgb = None
        depth = None
        ts = self._frame_timestamp  # 保留当前计数，若成功读取再递增

        if self.use_realsense:
            try:
                frames = self._rs_pipeline.wait_for_frames(timeout_ms=timeout_ms)
            except Exception as exc:
                logger.warning("read(): wait_for_frames 失败（%s）", exc)
                return (None, None, 0) if return_timestamp else (None, None)
            try:
                if self._align is not None:
                    frames = self._align.process(frames)
                color = frames.get_color_frame()
                depth = frames.get_depth_frame()
                if not color:
                    logger.warning("read(): 对齐后无彩色帧")
                    return (None, None, 0) if return_timestamp else (None, None)
                rgb = np.asanyarray(color.get_data())
                d = np.asanyarray(depth.get_data()) if depth else None
                if d is not None and rgb is not None and d.shape[:2] != rgb.shape[:2]:
                    logger.warning("read(): 深度(%s)与RGB(%s)尺寸不一致", d.shape, rgb.shape)
                # 成功读取，递增时间戳
                self._frame_timestamp += 1
                ts = self._frame_timestamp
                if return_timestamp:
                    return rgb, d, ts
                return rgb, d
            except Exception as exc:
                logger.warning("read(): 取帧/对齐异常（%s）", exc)
                return (None, None, 0) if return_timestamp else (None, None)

        # USB 摄像头
        ok, frame = self._cap.read()
        if ok:
            self._frame_timestamp += 1
            ts = self._frame_timestamp
            if return_timestamp:
                return frame, None, ts
            return frame, None
        return (None, None, 0) if return_timestamp else (None, None)

    def get_rgb(self) -> Optional[np.ndarray]:
        rgb, _ = self.read()
        return rgb

    def get_depth(self) -> Optional[np.ndarray]:
        _, depth = self.read()
        return depth

    def get_intrinsics(self) -> Optional[dict]:
        return self._intrinsics

    def get_timestamp_ms(self) -> int:
        """返回当前帧计数器（未递增），可用于需要时间戳但不读取帧的场景。"""
        return self._frame_timestamp

    # ------------------------------------------------------------------
    def pixel_to_point(self, u: float, v: float, depth_mm: Optional[float] = None) -> Optional[np.ndarray]:
        """像素 (u, v) + 深度 -> 相机系三维坐标 [x,y,z]（米）。仅 RGB-D 相机。"""
        if not self._intrinsics:
            logger.warning("无内参，无法换算三维坐标（仅 RGB-D 相机支持）")
            return None
        k = self._intrinsics
        if depth_mm is None:
            depth = self.get_depth()
            if depth is None:
                return None
            if 0 <= int(v) < depth.shape[0] and 0 <= int(u) < depth.shape[1]:
                depth_mm = float(depth[int(v), int(u)])
            else:
                return None
        z = depth_mm / 1000.0
        x = (u - k["ppx"]) / k["fx"] * z
        y = (v - k["ppy"]) / k["fy"] * z
        return np.array([x, y, z], dtype=np.float64)

    def landmarks_to_3d(self, landmarks: List[Tuple[float, float, float]],
                        rgb_shape: Tuple[int, int, int],
                        depth_image: np.ndarray,
                        depth_scale: float = 0.001) -> List[Tuple[float, float, float]]:
        """
        批量将归一化关键点转为相机系三维坐标（米）。

        Args:
            landmarks: 归一化坐标列表 [(x_norm, y_norm, z_mp), ...]  (z_mp 为 MediaPipe 相对深度，本方法不使用)
            rgb_shape: (height, width, channels) 用于将归一化转为像素
            depth_image: 对齐后的深度图 (uint16, 单位 mm)
            depth_scale: 深度图缩放因子（mm 转 m），通常为 0.001

        Returns:
            list of (x, y, z) 三维坐标，若某点深度无效则返回 (nan, nan, nan)
        """
        if self._intrinsics is None:
            raise RuntimeError("相机内参未获取，无法转换 3D 坐标（仅 RGB-D 相机支持）")
        h, w = rgb_shape[:2]
        k = self._intrinsics
        points_3d = []
        for (lx, ly, _) in landmarks:
            u = lx * w
            v = ly * h
            ui = int(round(u))
            vi = int(round(v))
            if 0 <= vi < depth_image.shape[0] and 0 <= ui < depth_image.shape[1]:
                depth_mm = float(depth_image[vi, ui])
            else:
                depth_mm = 0.0
            if depth_mm <= 0:
                points_3d.append((float('nan'), float('nan'), float('nan')))
                continue
            z = depth_mm * depth_scale  # 转为米
            x = (u - k["ppx"]) / k["fx"] * z
            y = (v - k["ppy"]) / k["fy"] * z
            points_3d.append((x, y, z))
        return points_3d

    # ------------------------------------------------------------------
    def release(self):
        if self._rs_pipeline is not None:
            try:
                self._rs_pipeline.stop()
            except Exception:
                pass
            self._rs_pipeline = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("摄像头已释放")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()