# -*- coding: utf-8 -*-
"""
camera_lib1.py —— 摄像头模块（lib/ 转发入口）

用户已把 camera_lib1.py 原实现移到 lib/参考代码/ 子目录（与 L515_driver.py、
vision_hand_ctrl.py 一起作为参考代码归档）。为保持既有调用方式
  `from lib.camera_lib1 import CameraModule`
不变（gui/main_gui.py 等），本文件作为 **转发模块**：
  1. 先通过 lib._pathsetup.ensure_ref_code() 把 lib/参考代码/ 加入 sys.path；
  2. 再 `from 参考代码.camera_lib1 import *` 把真实实现的所有公开名转发过来。

注意：camera/camera_module.py（camera 包内版本）与本文件是**两套实现**，
不可互相替代（camera_lib1 带帧时间戳与 landmarks_to_3d 批量转换）。
"""

from __future__ import annotations

import os
import sys

# ---- 路径引导：lib/参考代码/ 加入 sys.path ----
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
try:
    from _pathsetup import ensure_ref_code
    ensure_ref_code()
except Exception:  # pragma: no cover
    _ref = os.path.join(_here, "参考代码")
    if os.path.isdir(_ref) and _ref not in sys.path:
        sys.path.insert(0, _ref)

# ---- 转发真实实现（lib/参考代码/camera_lib1.py）----
from 参考代码.camera_lib1 import *  # noqa: F401,F403,E402
from 参考代码.camera_lib1 import (  # noqa: F401,E402
    CameraModule,
    check_realsense_devices,
    L515_PYREALSENSE_VERSION,
    LAST_REALSENSE_ERROR,
)


def diagnose_realsense() -> dict:
    """L515 启动失败一键诊断：返回 {ok, reasons[], hints[]}。

    用于 GUI 相机启动失败时给用户精准指引（区分"权限问题/设备问题/版本问题/驱动问题"）。
    """
    import ctypes
    import importlib.metadata as md
    import subprocess

    out = {"ok": False, "reasons": [], "hints": []}

    # 1) pyrealsense2 版本
    try:
        ver = md.version("pyrealsense2")
        if str(ver).startswith("2.54"):
            out["reasons"].append(f"版本 OK: {ver}")
        else:
            out["reasons"].append(f"版本不符: {ver}（需 2.54.2.5684）")
            out["hints"].append(f"请执行: pip install pyrealsense2=={L515_PYREALSENSE_VERSION}")
    except Exception:
        out["reasons"].append("未安装 pyrealsense2")
        out["hints"].append(f"请执行: pip install pyrealsense2=={L515_PYREALSENSE_VERSION}")

    # 2) 管理员权限
    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        out["reasons"].append(f"以管理员运行: {'是' if is_admin else '否'}")
        if not is_admin:
            out["hints"].append("建议【以管理员身份运行】终端/程序（很多 0x80070005 由此解决）")
    except Exception:
        pass

    # 3) L515 驱动检测（核心）：是否装了 Intel 专属驱动（WinUSB）而非微软通用 UVC
    try:
        r = subprocess.run(["pnputil", "/enum-devices", "/class", "Camera"],
                           capture_output=True, text=True, timeout=20)
        text = r.stdout or ""
        # 定位 L515 设备段（Intel RealSense 515）
        l515_block = ""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "RealSense" in line and ("515" in line or "L515" in line):
                block = [line]
                for nl in lines[i + 1:]:
                    if nl.strip().startswith("Instance ID"):
                        break
                    block.append(nl)
                l515_block = "\n".join(block)
                break
        if l515_block:
            if "usbvideo.inf" in l515_block:
                out["reasons"].append("L515 驱动: 微软通用UVC(usbvideo.inf) ⚠️ ← 根因")
                out["hints"].append(
                    "★ 根因：L515 用的是微软通用 UVC 驱动，librealsense 走 MediaFoundation 被系统拒绝(0x80070005)。\n"
                    "  ★ 彻底解决：安装 Intel RealSense SDK 2.0 运行时（含专属驱动，装后走 WinUSB 不再报错）：\n"
                    "    ① 下载：https://github.com/IntelRealSense/librealsense/releases/tag/v2.54.2\n"
                    "       （L515 最后支持版 2.54.x，文件名如 Intel.RealSense.SDK-WIN10-2.54.2.5684.exe）\n"
                    "    ② 以管理员运行安装，勾选安装驱动；\n"
                    "    ③ 装完重插 L515，用 Intel RealSense Viewer 确认出图；\n"
                    "    ④ 重开本程序即可（诊断会显示『Intel 专属驱动 ✅』）。\n"
                    "    快捷引导：python tools/install_realsense_driver.py")
            else:
                out["reasons"].append("L515 驱动: Intel 专属驱动 ✅")
        else:
            out["reasons"].append("未在 Camera 类设备中找到 L515")
            out["hints"].append("检查：USB3.0 直连 / Intel RealSense SDK 2.0 运行时 / 换线换口")
    except Exception as exc:
        out["reasons"].append(f"驱动检测跳过: {str(exc)[:60]}")

    # 4) 设备枚举（绕过 RGB 后端尝试）
    try:
        import pyrealsense2 as rs
        ctx = rs.context()
        devs = list(ctx.query_devices())
        if devs:
            out["ok"] = True
            for d in devs:
                out["reasons"].append(
                    f"设备: {d.get_info(rs.camera_info.name)} serial={d.get_info(rs.camera_info.serial_number)}")
        else:
            out["reasons"].append("设备枚举: 0 台（硬件/驱动/供电问题）")
    except Exception as exc:
        if "0x80070005" in str(exc) or "拒绝访问" in str(exc):
            out["reasons"].append("设备枚举失败: 0x80070005 拒绝访问（MediaFoundation 被系统拦截）")
            out["hints"].append("→ 安装 Intel RealSense 专属驱动后即走 WinUSB 后端，可彻底解决（见上方驱动检测）")
            out["hints"].append("→ 临时缓解：以管理员身份运行；或 设置→隐私→相机→允许桌面应用访问相机")
        else:
            out["reasons"].append(f"设备枚举异常: {str(exc)[:120]}")
    return out
