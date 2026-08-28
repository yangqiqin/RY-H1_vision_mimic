#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selfcheck.py —— Windows 环境自检（不接硬件也能跑大部分）

检查：
  1. Python 依赖（numpy/opencv/mediapipe/pyserial/pyrealsense2）
  2. 厂家 SDK 库文件是否存在（RyhandLibx64.dll 等）
  3. Windows 通信驱动文件（PCANBasic.py / ControlCAN.py/.dll）
  4. Intel RealSense 设备（L515 连通性）
  5. 摄像头可打开
  6. 16 关节 -> 电机指令换算（对照官方 demo）

用法：
  python selfcheck.py          # 在项目根目录运行（推荐）
  python 任意路径/selfcheck.py # 顶部路径引导会自动定位根目录
"""

from __future__ import annotations

# ---- 路径引导（必须最先执行：定位项目根目录 + 控制台 UTF-8） ----
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import importlib
import math


def check(ok: bool, msg: str):
    print(("[PASS] " if ok else "[FAIL] ") + msg)
    return ok


def main():
    ok_all = True

    print("== 1. Python 依赖 ==")
    for mod in ("numpy", "cv2", "mediapipe", "serial"):
        try:
            importlib.import_module(mod)
            ok_all &= check(True, f"{mod} 已安装")
        except ImportError:
            ok_all &= check(False, f"{mod} 未安装：pip install {mod}")
    try:
        import pyrealsense2 as _rs
        try:
            import importlib.metadata as _md
            ver = _md.version("pyrealsense2") or "unknown"
        except Exception:  # pragma: no cover
            ver = getattr(_rs, "__version__", "unknown")
        ok_v = str(ver).startswith("2.54")
        if ok_v:
            check(True, f"pyrealsense2 已安装（{ver}，符合 L515 要求 2.54.x）")
        else:
            ok_all &= check(False, f"pyrealsense2 版本 {ver} 非 2.54.x；"
                                   f"L515 请固定 pyrealsense2==2.54.2.5684（README_1.md）")
    except ImportError:
        ok_all &= check(False, "pyrealsense2 未安装（L515 需要）：pip install pyrealsense2==2.54.2.5684")

    # 1b. MediaPipe 手部模型（新版 Tasks：hand_landmarker.task）
    print("\n== 1b. MediaPipe 手部模型（hand_landmarker.task）==")
    try:
        from vision.hand_pose import _find_model_file, MODEL_DOWNLOAD_URL
        mf = _find_model_file()
        if mf:
            ok_all &= check(True, f"找到手部模型: {mf}")
        else:
            ok_all &= check(False, "未找到 hand_landmarker.task。请下载到项目根目录：")
            print(f"         {MODEL_DOWNLOAD_URL}")
    except Exception as exc:
        ok_all &= check(False, f"模型检查异常: {exc}")

    print("\n== 2. 厂家 SDK 库文件 ==")
    found_lib = False
    _root = os.getcwd()
    _dirs = [_root, os.path.join(_root, "lib")]
    for d in _dirs:
        for name in ("RyhandLibx64.dll", "RyhandLibx86.dll",
                     "libRyhand64_1.so", "libRyhandArm64.so", "libRyhand.so"):
            if os.path.exists(os.path.join(d, name)):
                found_lib = True
                ok_all &= check(True, f"找到 SDK 库: {os.path.join(d, name)}")
    if not found_lib:
        ok_all &= check(False, "未找到 SDK 库（RyhandLibx64.dll）。请放到项目根目录或 lib/")

    print("\n== 3. 通信驱动文件 ==")
    _dirs = [_root, os.path.join(_root, "lib"), os.path.join(_root, "lib", "pcan")]
    for name in ("PCANBasic.py", "ControlCAN.py", "ControlCAN.dll"):
        p = next((os.path.join(d, name) for d in _dirs if os.path.exists(os.path.join(d, name))), None)
        if p:
            check(True, f"找到 {p}")
        else:
            check(False, f"未找到 {name}（放到 lib/pcan/ 或根目录/lib/，按需从官方 demo 拷贝）")

    print("\n== 4. Intel RealSense（L515 连通性）==")
    try:
        from camera import check_realsense_devices
        from camera import camera_module as _cm
        devs = check_realsense_devices()
        if devs:
            for d in devs:
                ok_all &= check(True, f"L515 已连接: {d['name']} serial={d['serial']}")
        else:
            ok_all &= check(False, "未检测到 RealSense 设备")
            if _cm.LAST_REALSENSE_ERROR:
                print(f"        诊断: {_cm.LAST_REALSENSE_ERROR}")
                print("        提示: python apps/diag_camera.py 逐步定位")
    except Exception as exc:
        ok_all &= check(False, f"RealSense 检查异常: {exc}")

    print("\n== 5. 摄像头 ==")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        opened = cap.isOpened()
        cap.release()
        ok_all &= check(opened, "USB 摄像头 index=0 可打开")
    except Exception as exc:
        ok_all &= check(False, f"摄像头检查异常: {exc}")

    print("\n== 6. 16 关节换算（对照官方 demo）==")
    try:
        from hand import angles_to_motor_cmds
        cmds_open = angles_to_motor_cmds([0.0] * 16, hand_lr=1)
        ok1 = cmds_open == [0] * 16
        ok_all &= check(ok1, f"张开(全0°)->{cmds_open} 期望全0")
        demo = [0, 20, 0, 10, 10, 0, 0, 20, 75, 0, 20, 75, 0, 20, 75, 55]
        cmds = angles_to_motor_cmds([math.radians(a) for a in demo], hand_lr=1)
        ok2 = cmds[0] == 910 and cmds[8] == 4095 and cmds[15] == 2047
        ok_all &= check(ok2, f"demo 握拳预设->{cmds[:3]}...{cmds[15]}（期望 910...2047）")
        # 左手交换：θ1=20°,θ2=0 -> M1=455,M2=0；左手后 M1/M2 互换
        ang = [math.radians(20)] + [0.0] * 15
        cmds_r = angles_to_motor_cmds(ang, hand_lr=1)
        cmds_l = angles_to_motor_cmds(ang, hand_lr=0)
        ok3 = cmds_l[0] == cmds_r[1] and cmds_l[1] == cmds_r[0]
        ok_all &= check(ok3, f"左手 M1/M2 交换：右手({cmds_r[0]},{cmds_r[1]}) -> 左手({cmds_l[0]},{cmds_l[1]})")
    except Exception as exc:
        ok_all &= check(False, f"换算检查异常: {exc}")

    print()
    print("结论:", "全部通过" if ok_all else "有失败项（见上，无硬件时部分项预期 FAIL）")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
