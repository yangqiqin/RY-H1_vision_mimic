#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_camera.py —— 单项验证②：摄像头 / L515 连通性测试（不依赖灵巧手）

验证内容：
  1. 列出所有 Intel RealSense 设备（L515 连通性重点）
  2. 打开摄像头（USB 或 L515 RGB-D）
  3. 读取一帧并显示（可选）
  4. 打印相机内参 / 深度信息

L515 排查要点：
  * 必须 USB3.0 直连（勿经 USB2 集线器）；驱动装 Intel RealSense SDK 2.0；
  * `--list` 返回空 → 驱动/线缆/供电问题；可先用官方 RealSense Viewer 验证。

用法：
  python apps/test_camera.py --list              # 仅列出 RealSense 设备
  python apps/test_camera.py --camera 0          # USB 摄像头
  python apps/test_camera.py --realsense         # L515 RGB-D
  python apps/test_camera.py --realsense --show  # 弹窗显示画面（q 退出）

说明：
  本文件可直接运行，顶部路径引导自动定位项目根目录（导入 camera 包）。
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

import cv2
import numpy as np

from camera import CameraModule, check_realsense_devices

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    ap = argparse.ArgumentParser(description="摄像头 / L515 连通性测试")
    ap.add_argument("--list", action="store_true", help="仅列出 RealSense 设备")
    ap.add_argument("--camera", type=int, default=0, help="USB 摄像头索引")
    ap.add_argument("--realsense", action="store_true", help="使用 Intel RealSense")
    ap.add_argument("--serial", default=None, help="RealSense 序列号（多设备）")
    ap.add_argument("--show", action="store_true", help="弹窗显示画面")
    args = ap.parse_args()

    print("=" * 60)
    print("摄像头 / L515 连通性测试")
    print("=" * 60)

    devs = check_realsense_devices()
    print(f"[1] RealSense 设备数: {len(devs)}")
    for d in devs:
        print(f"    - {d['name']} serial={d['serial']} fw={d['fw']}")
    if args.list:
        return 0 if devs else 1

    try:
        cam = CameraModule(source=args.camera, use_realsense=args.realsense,
                           serial=args.serial,
                           width=1280 if args.realsense else 640,
                           height=720 if args.realsense else 480,
                           depth_width=1024, depth_height=768)
        print(f"[2] 摄像头打开成功: {'RealSense' if args.realsense else f'USB index={args.camera}'}")

        intr = cam.get_intrinsics()
        if intr:
            print(f"[3] 相机内参: fx={intr['fx']:.1f} fy={intr['fy']:.1f} "
                  f"ppx={intr['ppx']:.1f} ppy={intr['ppy']:.1f} {intr['width']}x{intr['height']}")

        rgb, depth = cam.read()
        if rgb is None:
            print("[4] ❌ 无法读取帧")
            return 1
        print(f"[4] RGB 帧: {rgb.shape} dtype={rgb.dtype}")
        if depth is not None:
            print(f"[5] 深度帧: {depth.shape} dtype={depth.dtype} "
                  f"范围=[{depth.min()}, {depth.max()}] mm")
            center = depth[depth.shape[0]//2, depth.shape[1]//2]
            print(f"    中心点深度: {center} mm")
        else:
            print("[5] 无深度（普通 USB 摄像头）")

        if args.show:
            print("[6] 按 q 退出画面")
            while True:
                rgb, depth = cam.read()
                if rgb is None:
                    continue
                disp = rgb.copy()
                if depth is not None:
                    # L515_driver.py 标准深度可视化：convertScaleAbs(alpha=0.03)
                    d8 = cv2.convertScaleAbs(depth, alpha=0.03)
                    disp = np.hstack([disp, cv2.applyColorMap(d8, cv2.COLORMAP_JET)])
                cv2.imshow("camera test", disp)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
            cv2.destroyAllWindows()

        print("\n✅ 摄像头连通性测试通过")
        return 0
    except Exception as exc:
        print(f"\n❌ 测试异常: {exc}")
        return 1
    finally:
        try:
            cam.release()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
