# -*- coding: utf-8 -*-
"""
test_holistic.py —— MediaPipe Holistic 全身姿态 单项验证（不接硬件也能跑）

验证内容：
  1. holistic 模型加载（lib/holistic_landmarker.task）
  2. 人体 + 手部检测（用相机/L515 或 静态图片）
  3. 手部 21 点 → 16 关节角（复用 hand_pose 解算链）
  4. 腕部 3D → 机械臂 TCP 映射（ArmFollower，纯计算）
  5. 骨架绘制（人体 + 手部）

用法：
  python apps/test_holistic.py                          # 仅自检（模型+映射）
  python apps/test_holistic.py --camera 0               # USB 摄像头实时验证
  python apps/test_holistic.py --realsense              # L515 实时验证（含深度）
  python apps/test_holistic.py --image xx.jpg           # 静态图片验证

说明：
  本脚本只做"视觉检测 + 角度解算 + 映射"，不发任何电机指令（安全）；
  需要控制时用 gui/main_gui_holistic.py。
"""

from __future__ import annotations
import os
import sys

# ---- 路径引导（必须最先执行） ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import math
import time

import cv2
import numpy as np

from vision.holistic_pose import HolisticPoseEstimator, HolisticResult
from arm.arm_follow import ArmFollower


def run_on_frame(est: HolisticPoseEstimator, follower: ArmFollower,
                 rgb: np.ndarray, depth=None, intrinsics=None, show: bool = False):
    """处理一帧并打印结果。"""
    results = est.process(rgb, depth, intrinsics, map_to_arm=True, arm_mapper=follower.map_wrist_to_arm_pose)
    if not results:
        return None
    r = results[0]
    info = []
    if r.pose_detected:
        info.append("人体: 检测到")
    if r.wrist_3d is not None:
        w = r.wrist_3d
        info.append(f"腕部3D: ({w[0]:.3f},{w[1]:.3f},{w[2]:.3f})m [{r.wrist_side}]")
    if r.arm_target_pose is not None:
        p = r.arm_target_pose
        info.append(f"臂TCP: ({p[0]:.3f},{p[1]:.3f},{p[2]:.3f})m")
    if r.hand_detected:
        ang = r.hand_angles_deg
        info.append(f"手: 16角 J1..J16 = " + " ".join(f"{a:.0f}" for a in ang))
    print(" | ".join(info))

    if show:
        disp = est.draw_skeleton(rgb, results)
        cv2.imshow("holistic", disp)
        if cv2.waitKey(1) & 0xFF == 27:
            return "quit"
    return r


def main():
    ap = argparse.ArgumentParser(description="Holistic 全身姿态单项验证")
    ap.add_argument("--camera", type=int, default=None, help="USB 摄像头索引")
    ap.add_argument("--realsense", action="store_true", help="用 L515")
    ap.add_argument("--image", default=None, help="静态图片路径")
    ap.add_argument("--hand-side", default="right", choices=["right", "left"])
    ap.add_argument("--show", action="store_true", help="显示骨架窗口")
    ap.add_argument("--selfcheck", action="store_true", help="仅模型+映射自检（默认）")
    args = ap.parse_args()

    print("加载 Holistic 模型（lib/holistic_landmarker.task）...")
    est = HolisticPoseEstimator(hand_side=args.hand_side)
    follower = ArmFollower()
    print("✅ 模型加载成功\n")

    # 映射纯计算自检
    test_wrist = [0.2, -0.3, 1.2]
    pose = follower.map_wrist_to_arm_pose(test_wrist)
    print(f"[自检] 腕部 {test_wrist} -> 机械臂TCP {[round(v,3) for v in pose]}")

    if args.selfcheck and not (args.camera is not None or args.realsense or args.image):
        print("\n仅自检模式完成（未打开相机）。")
        est.close()
        return

    cam = None
    try:
        if args.image:
            img = cv2.imread(args.image)
            if img is None:
                print("❌ 图片读取失败:", args.image)
                return
            run_on_frame(est, follower, img, show=args.show)
        else:
            from camera import CameraModule  # 与 test_camera.py 同源（camera 包），已验证可连 L515
            if args.realsense:
                cam = CameraModule(use_realsense=True)
            else:
                cam = CameraModule(source=args.camera or 0)
            intrinsics = cam.get_intrinsics()
            print("\n实时检测中（ESC 退出）...")
            while True:
                rgb, depth = cam.read()
                if rgb is None:
                    time.sleep(0.02)
                    continue
                ret = run_on_frame(est, follower, rgb, depth, intrinsics, show=args.show)
                if ret == "quit":
                    break
    finally:
        if cam is not None:
            cam.release()
        est.close()
        cv2.destroyAllWindows()
    print("\n✅ 完成")


if __name__ == "__main__":
    main()
