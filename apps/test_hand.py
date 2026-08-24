#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_hand.py —— 单项验证①：灵巧手连接性测试（不依赖摄像头）

验证内容：
  1. 加载厂家 SDK 库（RyhandLibx64.dll）
  2. 打开通信（PCAN / CANII / RS485）
  3. 读库版本
  4. 逐个读取 16 个电机状态（位置/速度/电流/故障）
  5. 安全动作测试：张开 → 握拳（默认关闭，需 --move 开启）

用法：
  python apps/test_hand.py --method pcan
  python apps/test_hand.py --method rs485 --port COM5
  python apps/test_hand.py --method pcan --move        # 附带动作测试

说明：
  本文件可直接运行（python apps/test_hand.py），顶部路径引导会
  自动定位项目根目录，确保能导入根目录的 hand 包、找到根目录的
  RyhandLibx64.dll / PCANBasic.py / ControlCAN.dll 等资源。
"""

from __future__ import annotations

# ---- 路径引导（必须最先执行：定位项目根目录，供包导入与 DLL 查找） ----
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
import time

from hand import RYH1HandController

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    ap = argparse.ArgumentParser(description="RY-H1 灵巧手连接性测试")
    ap.add_argument("--method", default="pcan", choices=["pcan", "canii", "rs485"])
    ap.add_argument("--port", default="COM3", help="RS485 串口号")
    ap.add_argument("--lib", default=None, help="SDK 库路径")
    ap.add_argument("--hand-lr", type=int, default=1, choices=[0, 1])
    ap.add_argument("--move", action="store_true", help="附带张开/握拳动作测试（默认只读）")
    args = ap.parse_args()

    print("=" * 60)
    print("RY-H1(16) 灵巧手连接性测试")
    print(f"  通信方式: {args.method}")
    print("=" * 60)

    hand = RYH1HandController(method=args.method, lib_path=args.lib,
                              rs485_port=args.port, hand_lr=args.hand_lr)
    try:
        hand.open()
        print(f"\n[1] 打开通信成功: {args.method}")

        res = hand.check_connection(timeout_s=0.6)
        print(f"[2] 库版本   : {res['version']!r}")
        print(f"[3] 电机应答 : {res['replies']}/16")
        if res["faults"]:
            print(f"[4] 故障电机 : {res['faults']}")
        else:
            print("[4] 无故障电机")

        if not res["ok"]:
            print("\n❌ 连接失败：0 个电机应答。")
            print("   排查：电源 24V/8A、CAN/RS485 线、波特率（CAN 1M / RS485 5M）、")
            print("         驱动（PCAN/ControlCAN）、串口号。")
            return 1

        print("\n[5] 各电机状态（位置 0~4095）：")
        for mid in range(1, 17):
            info = res["servos"].get(mid)
            if info:
                print(f"    电机{mid:2d}: P={info.position:4d} V={info.velocity:5d} "
                      f"I={info.current:5d} status={info.status}")
            else:
                print(f"    电机{mid:2d}: 无应答")

        if args.move:
            print("\n[6] 动作测试：张开 → 保持 → 握拳 → 保持 → 张开")
            hand.open_hand()
            time.sleep(2.0)
            hand.close_hand()
            time.sleep(2.0)
            hand.open_hand()
            time.sleep(1.0)
            print("    动作测试完成 ✓")

        print("\n✅ 灵巧手连接性测试通过")
        return 0
    except Exception as exc:
        print(f"\n❌ 测试异常: {exc}")
        return 1
    finally:
        try:
            hand.open_hand()
        except Exception:
            pass
        hand.close()


if __name__ == "__main__":
    raise SystemExit(main())
