#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mimic_demo.py —— 动作模仿主程序（摄像头 + 灵巧手，无机械臂，Windows）

流程：
  摄像头采集（USB / L515）→ MediaPipe 手部姿态估计
  → 16 关节角度（弧度）→ 平滑 → RY-H1 灵巧手动作模仿

用法：
  python apps/mimic_demo.py --method pcan --camera 0 --scale 0.5
  python apps/mimic_demo.py --method rs485 --port COM5 --camera 0 --scale 0.3
  python apps/mimic_demo.py --method pcan --realsense --scale 0.5 --show

按键（--show 时）：
  q / Esc  退出；  o 张开；  c 握拳；  r 放松；  s 暂停/恢复

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
import logging
import math
import time

import cv2

from camera import CameraModule
from vision import HandPoseEstimator
from hand import RYH1HandController, JOINT_NUM

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mimic")


class MotionSmoother:
    """一阶低通 + 死区，防止抖动。"""

    def __init__(self, alpha: float = 0.35, deadzone: float = 0.03):
        self.alpha = alpha
        self.deadzone = deadzone
        self._state = [0.0] * JOINT_NUM

    def update(self, angles_rad: list) -> list:
        out = []
        for i in range(JOINT_NUM):
            v = self.alpha * angles_rad[i] + (1 - self.alpha) * self._state[i]
            if abs(v - self._state[i]) < self.deadzone:
                v = self._state[i]
            out.append(v)
        self._state = out
        return out


def main():
    ap = argparse.ArgumentParser(description="RY-H1 灵巧手视觉动作模仿（Windows）")
    ap.add_argument("--method", default="pcan", choices=["pcan", "canii", "rs485"],
                    help="灵巧手通信方式")
    ap.add_argument("--port", default="COM3", help="RS485 串口号")
    ap.add_argument("--lib", default=None, help="SDK 库路径")
    ap.add_argument("--hand-lr", type=int, default=1, choices=[0, 1], help="手型 1=右 0=左")
    ap.add_argument("--camera", type=int, default=0, help="USB 摄像头索引")
    ap.add_argument("--realsense", action="store_true", help="使用 Intel L515")
    ap.add_argument("--serial", default=None, help="RealSense 序列号")
    ap.add_argument("--hand-model", default=None,
                    help="MediaPipe 手部模型 hand_landmarker.task 路径（默认自动在根目录搜索）")
    ap.add_argument("--scale", type=float, default=0.5, help="关节角缩放（首次 0.3~0.5）")
    ap.add_argument("--speed", type=int, default=1000, help="速度 0.001行程/s")
    ap.add_argument("--max-current", type=int, default=75, help="最大电流 0.001A")
    ap.add_argument("--rate", type=float, default=15.0, help="控制频率 Hz")
    ap.add_argument("--smooth", type=float, default=0.35, help="平滑系数")
    ap.add_argument("--show", action="store_true", help="显示摄像头画面")
    args = ap.parse_args()

    # 1) 摄像头（L515 标准参数 L515_driver.py：RGB 1280x720 + 深度 1024x768）
    cam = CameraModule(source=args.camera, use_realsense=args.realsense,
                       serial=args.serial,
                       width=1280 if args.realsense else 640,
                       height=720 if args.realsense else 480,
                       depth_width=1024, depth_height=768)
    # 2) 姿态估计（MediaPipe Tasks：hand_landmarker.task）
    est = HandPoseEstimator(max_hands=1, model_path=args.hand_model)
    # 3) 灵巧手
    hand = RYH1HandController(method=args.method, lib_path=args.lib,
                              rs485_port=args.port,
                              default_speed=args.speed,
                              default_max_current=args.max_current,
                              hand_lr=args.hand_lr)
    hand.open()

    smoother = MotionSmoother(alpha=args.smooth)
    paused = False
    interval = 1.0 / max(1.0, args.rate)

    logger.info("动作模仿开始：scale=%.2f rate=%.1fHz method=%s hand_lr=%d",
                args.scale, args.rate, args.method, args.hand_lr)
    hand.open_hand()

    try:
        while True:
            t0 = time.time()
            rgb, _ = cam.read()
            if rgb is None:
                continue

            results = est.process(rgb)
            if results:
                angles_deg = [v * args.scale for v in results[0].joint_angles_deg]
                angles_rad = [math.radians(a) for a in angles_deg]
                angles_rad = smoother.update(angles_rad)
                if not paused:
                    hand.move_joints(angles_rad)
            else:
                angles_deg = None

            if args.show:
                frame = rgb.copy()
                if angles_deg is not None:
                    y = 20
                    for i in range(JOINT_NUM):
                        cv2.putText(frame, f"J{i+1}: {angles_deg[i]:5.1f}", (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                        y += 18
                cv2.imshow("mimic", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("o"):
                    hand.open_hand()
                if key == ord("c"):
                    hand.close_hand()
                if key == ord("r"):
                    hand.relax()
                if key == ord("s"):
                    paused = not paused

            dt = time.time() - t0
            if dt < interval:
                time.sleep(interval - dt)
    except KeyboardInterrupt:
        logger.info("用户中断")
    finally:
        hand.open_hand()
        hand.close()
        est.close()
        cam.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
