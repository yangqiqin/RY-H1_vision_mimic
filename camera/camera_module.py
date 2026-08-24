# -*- coding: utf-8 -*-
"""
camera_module.py —— 摄像头模块（Windows / Ubuntu 通用）

统一封装"图像采集"，对外只提供 RGB 帧（深度帧可选）：
  * 普通 USB 摄像头（UVC，OpenCV VideoCapture）
  * Intel RealSense L515 / D435 等 RGB-D 相机（pyrealsense2，RGB + 深度 + 内参）

L515 连通性（重点，依据知识库 README_1.md《L515 PyLive Toolkit》）：
  * ⚠️ L515 是 Intel 已停产的 LiDAR 设备：librealsense **2.55+ 已移除其支持**，
    必须安装 **pyrealsense2==2.54.2.5684**（README_1.md 指明 Just Stable）；
  * 必须 USB3.0 直连（勿经 USB2 集线器）+ 装 Intel RealSense SDK 2.0 运行时；
  * **深度流与 RGB 流必须分开设分辨率**（L515 彩色/深度分辨率不同）：
      例1 depth 640x480 + RGB 1280x720；例2 depth 1024x768 + RGB 1920x1080；
  * `check_realsense_devices()` 列出所有已连接 RealSense 设备并校验版本，
    若返回空列表/抛版本异常 → 先 `pip install pyrealsense2==2.54.2.5684`，
    再用官方 Intel RealSense Viewer 确认设备出图。

依赖：
  pip install opencv-python
  # RGB-D 相机才需要（L515 必须固定版本）：
  pip install pyrealsense2==2.54.2.5684

用法：
  from camera import CameraModule
  cam = CameraModule(source=0)           # USB 摄像头
  cam = CameraModule(use_realsense=True) # Intel L515
  rgb, depth = cam.read()                # depth 可为 None
  cam.release()
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("camera")

# README_1.md：L515 必须的 pyrealsense2 版本（librealsense 2.55+ 已移除 L515）
L515_PYREALSENSE_VERSION = "2.54.2.5684"

# 最近一次 RealSense 诊断信息（供 selfcheck/diag 显示具体失败原因）
LAST_REALSENSE_ERROR = ""


def check_realsense_devices() -> List[dict]:
    """列出所有已连接的 Intel RealSense 设备，并校验 pyrealsense2 版本。

    返回 [{serial, name, fw}]；无设备返回 []。若版本非 2.54.x 会记录 ERROR 级日志
    （L515 在 librealsense 2.55+ 已不被支持）。
    """
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
        devs = list(ctx.query_devices())   # 立即物化，避免延迟枚举抛异常
    except Exception as exc:  # pragma: no cover
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
        except Exception as exc:  # pragma: no cover
            logger.warning("读取设备信息失败: %s", exc)
    return out


def _get_pyrealsense_version() -> str:
    """获取 pyrealsense2 版本（优先 pip 元数据；pyrealsense2 2.54 无 __version__）。"""
    try:
        import importlib.metadata as md
        return md.version("pyrealsense2") or "unknown"
    except Exception:  # pragma: no cover
        try:
            import pyrealsense2 as rs
            return getattr(rs, "__version__", "unknown")
        except Exception:  # pragma: no cover
            return "unknown"


def _warn_if_wrong_version() -> bool:
    """检查 pyrealsense2 版本；非 2.54.x 时告警（L515 在 2.55+ 不被支持）。

    返回 True=版本兼容（2.54.x），False=版本不符。
    """
    ver = _get_pyrealsense_version()
    ok = str(ver).startswith("2.54")
    if not ok:
        logger.error(
            "pyrealsense2 版本 %s 不兼容 L515：librealsense 2.55+ 已移除 L515 支持。"
            "请执行：pip install pyrealsense2==%s",
            ver, L515_PYREALSENSE_VERSION)
    return ok


class CameraModule:
    """摄像头采集模块。"""

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
            width/height:  RGB 流分辨率。**默认 1280x720（L515_driver.py 标准参数，
                           README_1.md 例1）**
            fps:           RGB 流帧率（默认 30）
            serial:        RealSense 设备序列号（多设备时指定；None=第一台）
            depth_width / depth_height / depth_fps:
                           **深度流独立分辨率**。默认 **1024x768**（L515_driver.py
                           标准参数：depth 1024x768 + RGB 1280x720 @30FPS）。
        """
        self.use_realsense = use_realsense
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_width = depth_width
        self.depth_height = depth_height
        self.depth_fps = depth_fps
        self._align = None           # rs.align：深度对齐到彩色（L515_driver.py）

        self._rs_pipeline = None
        self._rs_profile = None
        self._cap = None
        self._intrinsics = None

        if use_realsense:
            self._open_realsense(serial)
        else:
            self._open_usb(source)

    # ------------------------------------------------------------------
    def _open_usb(self, source: int):
        self._cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)  # Windows 用 DirectShow
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(source)             # 回退默认后端
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 source={source}（/dev/video{source} 或 Windows 摄像头）")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        logger.info("USB 摄像头已打开 source=%s", source)

    def _open_realsense(self, serial: Optional[str]):
        try:
            import pyrealsense2 as rs
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                f"使用 RGB-D 相机需先安装 pyrealsense2（L515 必须固定版本）："
                f"pip install pyrealsense2=={L515_PYREALSENSE_VERSION}") from exc

        # 版本硬校验：librealsense 2.55+ 已移除 L515 支持（README_1.md）
        if not _warn_if_wrong_version():
            raise RuntimeError(
                f"pyrealsense2 版本不兼容 L515：请执行 pip install pyrealsense2=={L515_PYREALSENSE_VERSION}"
                f"（librealsense 2.55+ 已移除 L515 支持）")

        ctx = rs.context()
        try:
            devs = list(ctx.query_devices())
        except Exception as exc:  # pragma: no cover
            hint = ("  ⚠️ Windows 拒绝访问（0x80070005）：请【以管理员身份运行】，"
                    "或检查设置→隐私→相机权限。") if "0x80070005" in str(exc) else ""
            raise RuntimeError(f"RealSense 设备枚举失败（权限/运行时）: {exc}\n{hint}\n"
                               f"  请检查 pyrealsense2 版本（必须 2.54.x）与驱动") from exc
        if len(devs) == 0:
            raise RuntimeError(
                "未找到 RealSense 设备。请检查：\n"
                "  1. pyrealsense2 版本：pip show pyrealsense2（必须 2.54.x）\n"
                "  2. USB3.0 直连（勿经 USB2 集线器）\n"
                "  3. 驱动：安装 Intel RealSense SDK 2.0 运行时\n"
                "  4. 供电/线缆；可先用官方 RealSense Viewer 验证")
        if serial is None:
            serial = devs[0].get_info(rs.camera_info.serial_number)

        self._rs_pipeline = rs.pipeline()
        cfg = rs.config()
        cfg.enable_device(serial)
        # RGB 与深度分开配置：L515 深度流与彩色流分辨率不同（README_1.md 例1）
        cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        try:
            cfg.enable_stream(rs.stream.depth, self.depth_width, self.depth_height,
                              rs.format.z16, self.depth_fps)
        except Exception as exc:  # pragma: no cover
            logger.warning("深度流配置失败（仅用 RGB）：%s", exc)

        try:
            self._rs_profile = self._rs_pipeline.start(cfg)
        except Exception as exc:  # pragma: no cover
            self._rs_pipeline = None
            raise RuntimeError(
                f"RealSense 流启动失败：{exc}\n"
                f"  请检查分辨率组合（当前 RGB {self.width}x{self.height} + "
                f"深度 {self.depth_width}x{self.depth_height}）。\n"
                f"  L515 标准参数（L515_driver.py/README_1.md）："
                f"depth 1024x768 + RGB 1280x720 @30FPS") from exc

        # L515_driver.py 关键：深度对齐到彩色（保证深度与 RGB 像素对齐）
        try:
            self._align = rs.align(rs.stream.color)
        except Exception:  # pragma: no cover
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
    def read(self, timeout_ms: int = 5000) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """读取一帧。返回 (rgb_bgr, depth)。

        - USB 摄像头：depth = None
        - RealSense：rgb_bgr 为 BGR 帧，depth 为 uint16 深度帧（单位 mm）；
          深度流通过 rs.align 对齐到彩色（L515_driver.py 标准），
          保证 depth 与 rgb 像素一一对应（尺寸一致）。

        失败时返回 (None, None) 并记录具体原因（不抛异常）：
          * wait_for_frames 超时/异常 → 深度流可能未就绪/设备被占用
          * 对齐后取不到 color 帧 → 流配置问题
        """
        if self.use_realsense:
            try:
                frames = self._rs_pipeline.wait_for_frames(timeout_ms=timeout_ms)
            except Exception as exc:
                logger.warning("read(): wait_for_frames 失败（%s）。可能原因："
                               "设备被其他程序占用/深度流未就绪/USB带宽不足", exc)
                return None, None
            try:
                if self._align is not None:
                    frames = self._align.process(frames)   # 深度对齐到彩色
                color = frames.get_color_frame()
                depth = frames.get_depth_frame()
                if not color:
                    logger.warning("read(): 对齐后无彩色帧（可能只有深度流/流未对齐）")
                    return None, None
                rgb = np.asanyarray(color.get_data())
                d = np.asanyarray(depth.get_data()) if depth else None
                if d is not None and rgb is not None and d.shape[:2] != rgb.shape[:2]:
                    logger.warning("read(): 深度(%s)与RGB(%s)尺寸不一致，对齐可能失败",
                                   d.shape, rgb.shape)
                return rgb, d
            except Exception as exc:
                logger.warning("read(): 取帧/对齐异常（%s）", exc)
                return None, None

        ok, frame = self._cap.read()
        if not ok:
            return None, None
        return frame, None

    def get_rgb(self) -> Optional[np.ndarray]:
        rgb, _ = self.read()
        return rgb

    def get_depth(self) -> Optional[np.ndarray]:
        _, depth = self.read()
        return depth

    def get_intrinsics(self) -> Optional[dict]:
        return self._intrinsics

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

    # ------------------------------------------------------------------
    def release(self):
        if self._rs_pipeline is not None:
            try:
                self._rs_pipeline.stop()
            except Exception:  # pragma: no cover
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
