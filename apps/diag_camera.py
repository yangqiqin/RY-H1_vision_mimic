#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_camera.py —— L515 摄像头深度诊断（精准定位"能打开但读不到帧"）

分步测试，每步独立判定，输出到哪一步失败：
  1. pyrealsense2 版本（L515 必须 2.54.x；2.55+ 已移除支持）
  2. 设备枚举（0x80070005 权限 / USB / 驱动 / 供电）
  3. 逐个尝试分辨率组合（标准 L515_driver.py 参数优先）
  4. 单独 RGB 流测试（不配深度，验证彩色是否正常）
  5. 单独深度流测试（验证深度是否正常）
  6. RGB+深度组合 + rs.align 对齐测试
  7. 连续取帧测试（10 帧，统计成功率）

用法：
  python apps/diag_camera.py
  python apps/diag_camera.py --quick      # 只测标准参数组合
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import cv2
import numpy as np

# ---- 路径引导 ----
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("diag_camera")


def step(n, title):
    print(f"\n[步骤{n}] {title}")
    print("-" * 60)


def main():
    ap = argparse.ArgumentParser(description="L515 深度诊断")
    ap.add_argument("--quick", action="store_true", help="只测标准参数组合")
    args = ap.parse_args()

    import pyrealsense2 as rs
    import importlib.metadata as md

    # 1) 版本
    step(1, "pyrealsense2 版本")
    try:
        ver = md.version("pyrealsense2")
    except Exception:
        ver = getattr(rs, "__version__", "unknown")
    print(f"  pyrealsense2 = {ver}")
    if str(ver).startswith("2.54"):
        print("  ✓ 版本兼容 L515（2.54.x）")
    else:
        print("  ✗ 版本不兼容：L515 在 librealsense 2.55+ 已被移除支持")
        print("    请执行: pip install pyrealsense2==2.54.2.5684")
        return 1

    # 2) 设备枚举
    step(2, "设备枚举")
    try:
        ctx = rs.context()
        devs = list(ctx.query_devices())
    except Exception as exc:
        msg = str(exc)
        if "0x80070005" in msg or "Access denied" in msg:
            print(f"  ✗ 拒绝访问({msg})：请【以管理员身份运行】，或检查 设置→隐私→相机")
        else:
            print(f"  ✗ 枚举失败: {msg}")
        return 1
    if len(devs) == 0:
        print("  ✗ 未发现 RealSense 设备")
        print("    检查: USB3.0 直连 / Intel RealSense SDK 2.0 驱动 / 供电")
        return 1
    for d in devs:
        print(f"  ✓ 设备: {d.get_info(rs.camera_info.name)} "
              f"serial={d.get_info(rs.camera_info.serial_number)} "
              f"fw={d.get_info(rs.camera_info.firmware_version)}")

    # 3) 分辨率组合
    combos = [
        ("L515_driver.py 标准", 1280, 720, 1024, 768),
        ("README_1 例2", 1920, 1080, 1024, 768),
        ("README_1 例1", 1280, 720, 640, 480),
        ("保守低分辨率", 640, 480, 640, 480),
    ]
    if args.quick:
        combos = combos[:1]

    # 4/5/6) 组合测试（含单独 RGB、单独深度）
    step(3, "流启动测试（分辨率组合）")
    for name, w, h, dw, dh in combos:
        print(f"\n  组合 [{name}]: RGB {w}x{h} + 深度 {dw}x{dh}")
        # 4a. 单独 RGB
        p1 = rs.pipeline()
        c1 = rs.config()
        c1.enable_stream(rs.stream.color, w, h, rs.format.bgr8, 30)
        try:
            p1.start(c1)
            f1 = p1.wait_for_frames(timeout_ms=3000)
            col1 = f1.get_color_frame()
            print(f"    单独RGB: {'✓ ' + str(col1.get_data().shape) if col1 else '✗ 无彩色帧'}")
        except Exception as exc:
            print(f"    ✗ 单独RGB启动/取帧失败: {exc}")
        finally:
            p1.stop()
        # 4b. 单独深度
        p2 = rs.pipeline()
        c2 = rs.config()
        c2.enable_stream(rs.stream.depth, dw, dh, rs.format.z16, 30)
        try:
            p2.start(c2)
            f2 = p2.wait_for_frames(timeout_ms=3000)
            dep2 = f2.get_depth_frame()
            print(f"    单独深度: {'✓ ' + str(dep2.get_data().shape) if dep2 else '✗ 无深度帧'}")
        except Exception as exc:
            print(f"    ✗ 单独深度启动/取帧失败: {exc}")
        finally:
            p2.stop()
        # 4c. 组合 + 对齐
        p3 = rs.pipeline()
        c3 = rs.config()
        c3.enable_stream(rs.stream.color, w, h, rs.format.bgr8, 30)
        c3.enable_stream(rs.stream.depth, dw, dh, rs.format.z16, 30)
        align = rs.align(rs.stream.color)
        try:
            p3.start(c3)
            frames = p3.wait_for_frames(timeout_ms=3000)
            aligned = align.process(frames)
            col3 = aligned.get_color_frame()
            dep3 = aligned.get_depth_frame()
            if col3 and dep3:
                rgb = np.asanyarray(col3.get_data())
                d = np.asanyarray(dep3.get_data())
                same = rgb.shape[:2] == d.shape[:2]
                print(f"    组合+对齐: ✓ RGB{rgb.shape} 深度{d.shape} 尺寸一致={same}")
            elif col3:
                print("    组合+对齐: ✓ 有彩色，✗ 无深度（深度流可能未启用）")
            else:
                print("    组合+对齐: ✗ 无彩色帧")
        except Exception as exc:
            print(f"    ✗ 组合启动/取帧失败: {exc}")
        finally:
            p3.stop()

    # 7) 连续取帧（用标准参数）
    step(4, "连续取帧测试（标准参数 1280x720+1024x768，10帧）")
    p = rs.pipeline()
    c = rs.config()
    c.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
    c.enable_stream(rs.stream.depth, 1024, 768, rs.format.z16, 30)
    align = rs.align(rs.stream.color)
    ok_cnt = 0
    try:
        p.start(c)
        for i in range(10):
            try:
                frames = p.wait_for_frames(timeout_ms=2000)
                aligned = align.process(frames)
                col = aligned.get_color_frame()
                if col:
                    ok_cnt += 1
                time.sleep(0.05)
            except Exception as exc:
                print(f"  帧{i}: 失败 {exc}")
        print(f"  取帧成功 {ok_cnt}/10")
    except Exception as exc:
        print(f"  ✗ 标准组合启动失败: {exc}")
    finally:
        p.stop()

    print("\n" + "=" * 60)
    if ok_cnt >= 8:
        print("诊断结论: 摄像头工作正常（连续取帧稳定）")
    else:
        print("诊断结论: 摄像头异常，按上面 ✗ 项逐条排查")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
