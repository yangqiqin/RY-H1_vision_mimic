#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_all.py —— 综合验证：把「摄像头/L515 + 姿态估计 + 灵巧手」串起来跑一遍

验证顺序：
  1. 依赖检查（numpy/opencv/mediapipe）
  2. L515 / 摄像头连通性（读帧、内参）
  3. MediaPipe 姿态估计（对一帧做推理，输出 16 关节角）
  4. 16 关节 -> 电机指令换算（对照 demo 公式）
  5. 灵巧手连接 + 连接性自检 + 安全动作（可选 --move）

用法：
  python apps/test_all.py --method pcan          # 全套（不动作）
  python apps/test_all.py --method pcan --move   # 附带张开/握拳
  python apps/test_all.py --no-camera            # 跳过摄像头，只验手
  python apps/test_all.py --no-hand              # 跳过灵巧手，只验视觉

说明：
  本文件可直接运行，顶部路径引导自动定位项目根目录。
"""

from __future__ import annotations

# ---- 路径引导（必须最先执行：定位项目根目录 + 控制台 UTF-8） ----
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import importlib
import logging
import math
import time

import numpy as np

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test_all")


def step(title: str):
    print(f"\n--- {title} ---")


def main():
    ap = argparse.ArgumentParser(description="RY-H1 综合验证（摄像头+姿态+灵巧手）")
    ap.add_argument("--method", default="pcan", choices=["pcan", "canii", "rs485"])
    ap.add_argument("--port", default="COM3")
    ap.add_argument("--lib", default=None)
    ap.add_argument("--hand-lr", type=int, default=1, choices=[0, 1])
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--realsense", action="store_true")
    ap.add_argument("--serial", default=None)
    ap.add_argument("--hand-model", default=None,
                    help="MediaPipe 手部模型 hand_landmarker.task 路径（默认自动搜索根目录）")
    ap.add_argument("--move", action="store_true", help="附带动作测试")
    ap.add_argument("--no-camera", action="store_true", help="跳过摄像头")
    ap.add_argument("--no-hand", action="store_true", help="跳过灵巧手")
    args = ap.parse_args()

    ok_all = True

    # 1) 依赖
    step("1. 依赖检查")
    for mod in ("numpy", "cv2", "mediapipe"):
        try:
            importlib.import_module(mod)
            print(f"  [OK] {mod}")
        except ImportError:
            print(f"  [FAIL] {mod} 未安装（pip install -r requirements.txt）")
            ok_all = False
    try:
        importlib.import_module("pyrealsense2")
        print("  [OK] pyrealsense2")
    except ImportError:
        print("  . pyrealsense2 未装（仅 L515 需要）")

    # 2) 摄像头
    if not args.no_camera:
        step("2. 摄像头/L515 连通性")
        try:
            from camera import CameraModule, check_realsense_devices
            devs = check_realsense_devices()
            print(f"  RealSense 设备: {[d['name'] for d in devs] or '无'}")
            cam = CameraModule(source=args.camera, use_realsense=args.realsense,
                               serial=args.serial,
                               width=1280 if args.realsense else 640,
                               height=720 if args.realsense else 480,
                               depth_width=1024, depth_height=768)
            rgb, depth = cam.read()
            assert rgb is not None, "无法读取帧"
            print(f"  RGB: {rgb.shape}, 深度: {depth.shape if depth is not None else 'N/A'}")
            intr = cam.get_intrinsics()
            if intr:
                print(f"  内参: fx={intr['fx']:.1f} ppx={intr['ppx']:.1f}")
            cam.release()
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            ok_all = False

    # 3) MediaPipe 姿态
    step("3. MediaPipe 姿态估计（hand_landmarker.task）")
    try:
        from vision import HandPoseEstimator
        est = HandPoseEstimator(max_hands=1, model_path=args.hand_model)
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        res = est.process(dummy)
        print(f"  空帧推理正常（无手 -> {len(res)} 个结果）")
        est.close()
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        ok_all = False

    # 4) 16 关节换算
    step("4. 16 关节 -> 电机指令（对照 demo 公式）")
    try:
        from hand import angles_to_motor_cmds
        cmds_open = angles_to_motor_cmds([0.0] * 16, hand_lr=1)
        demo = [0, 20, 0, 10, 10, 0, 0, 20, 75, 0, 20, 75, 0, 20, 75, 55]
        cmds_demo = angles_to_motor_cmds([math.radians(a) for a in demo], hand_lr=1)
        assert cmds_open == [0] * 16, cmds_open
        assert cmds_demo[0] == 910 and cmds_demo[8] == 4095 and cmds_demo[15] == 2047
        print(f"  张开->{cmds_open[:3]}... 握拳->{cmds_demo[:3]}... 第16->{cmds_demo[15]} [OK]")
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        ok_all = False

    # 5) 灵巧手
    if not args.no_hand:
        step("5. 灵巧手连接 + 自检")
        from hand import RYH1HandController
        hand = RYH1HandController(method=args.method, lib_path=args.lib,
                                  rs485_port=args.port, hand_lr=args.hand_lr)
        try:
            hand.open()
            res = hand.check_connection()
            print(f"  库版本: {res['version']!r}")
            print(f"  电机应答: {res['replies']}/16  故障: {res['faults'] or '无'}")
            if not res["ok"]:
                print("  [FAIL] 灵巧手无应答")
                ok_all = False
            elif args.move:
                print("  动作测试：张开→握拳→张开")
                hand.open_hand(); time.sleep(2)
                hand.close_hand(); time.sleep(2)
                hand.open_hand(); time.sleep(1)
                print("  [OK] 动作完成")
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            ok_all = False
        finally:
            try:
                hand.open_hand()
            except Exception:
                pass
            hand.close()

    print("\n" + "=" * 60)
    print("综合验证结论:", "[OK] 全部通过" if ok_all else "[FAIL] 有失败项")
    print("=" * 60)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
