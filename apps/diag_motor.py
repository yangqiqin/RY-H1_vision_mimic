#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_motor.py —— 灵巧手电机深度诊断（精准定位"动作几乎看不见/行程太小"）

分步测试：
  1. 连接 + 库版本
  2. 连接性自检（16 电机应答 + 故障码中文解释）
  3. 全电机行程读取（行程应≈4095；过小 => 动作看不见）
  4. 故障码 11（找零告警）处理：执行回零（homing），再复检行程
  5. 单电机动作测试（对指定电机直接发位置指令，验证是否响应）
  6. 全手张开/握拳动作测试（确认幅度）

用法：
  python apps/diag_motor.py --method pcan
  python apps/diag_motor.py --method pcan --fix-homing     # 自动执行回零修复
  python apps/diag_motor.py --method pcan --motor 9        # 只诊断电机9
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

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
logger = logging.getLogger("diag_motor")

from hand import RYH1HandController, status_text, JOINT_NAMES_CN


def step(n, title):
    print(f"\n[步骤{n}] {title}")
    print("-" * 60)


def main():
    ap = argparse.ArgumentParser(description="灵巧手电机诊断")
    ap.add_argument("--method", default="pcan", choices=["pcan", "canii", "rs485"])
    ap.add_argument("--port", default="COM3")
    ap.add_argument("--lib", default=None)
    ap.add_argument("--hand-lr", type=int, default=1, choices=[0, 1])
    ap.add_argument("--fix-homing", action="store_true",
                    help="检测到找零告警(11)时自动执行回零")
    ap.add_argument("--motor", type=int, default=0, help="只诊断指定电机(1-16)，0=全部")
    args = ap.parse_args()

    hand = RYH1HandController(method=args.method, lib_path=args.lib,
                              rs485_port=args.port, hand_lr=args.hand_lr)
    try:
        hand.open()
        print(f"库版本: {hand.version()}")

        # 2) 连接性自检
        step(2, "连接性自检（16 电机应答 + 故障码）")
        res = hand.check_connection()
        print(f"  应答: {res['replies']}/16  库版本: {res['version']!r}")
        if res["faults"]:
            for mid, st, txt in res["faults"]:
                print(f"  ✗ 电机{mid:2d} 状态={st} [{txt}]")
        else:
            print("  ✓ 无故障电机")

        # 3) 行程读取
        step(3, "行程读取（应≈4095）")
        strokes = hand.check_all_strokes()
        low = []
        for mid in range(1, 17):
            if args.motor and mid != args.motor:
                continue
            s = strokes[mid]["stroke"]
            info = strokes[mid]["info"]
            mark = "✓" if (s or 0) >= 3000 else "⚠️ 偏小"
            print(f"  电机{mid:2d}: 行程={s} {mark}"
                  + (f"  状态={info.status}[{status_text(info.status)}]" if info else "  无应答"))
            if (s or 0) < 3000:
                low.append(mid)

        # 4) 找零告警处理
        need = res.get("need_homing", [])
        if need:
            step(4, "找零告警(11)电机：" + ",".join(str(m) for m in need))
            print("  这些电机未完成回零，位置基准未建立 → 行程受限 → 动作几乎看不见")
            if args.fix_homing:
                print("  执行回零（mode=2 立即归零）...")
                r = hand.homing(need, timeout_ms=1500, sleep_s=0.3)
                print(f"  回零返回: {r}")
                time.sleep(1.0)
                # 复检
                for mid in need:
                    info = hand.get_servo_info(mid, timeout_ms=200)
                    st = hand.get_stroke(mid, timeout_ms=200)
                    if info:
                        print(f"  电机{mid:2d} 复检: 状态={info.status}"
                              f"[{status_text(info.status)}] 行程={st}")
            else:
                print("  ➡ 加 --fix-homing 自动执行回零修复")
                print("    或 GUI 连接性自检后点【回零】按钮")

        # 5) 单电机动作测试
        if args.motor:
            mid = args.motor
            step(5, f"单电机{mid}动作测试（位置 0→2048→4095）")
            for pos in (2048, 4095):
                ret = hand.move_motor(mid, pos)
                time.sleep(0.8)
                info = hand.get_servo_info(mid, timeout_ms=200)
                print(f"  位置={pos} 返回={ret}" +
                      (f" 回读P={info.position}" if info else " 无应答"))
            hand.move_motor(mid, 0)
            return 0

        # 6) 全手动作测试
        step(6, "全手动作测试（张开→握拳→张开）")
        hand.open_hand()
        time.sleep(1.5)
        hand.close_hand()
        time.sleep(1.5)
        hand.open_hand()
        time.sleep(1.0)
        print("  动作完成 ✓（若幅度仍小，检查行程与回零）")

        print("\n" + "=" * 60)
        if low or need:
            print("结论: 存在行程受限/找零告警电机，按上面处理（回零→复检→动作）")
        else:
            print("结论: 电机行程正常、无故障")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\n✗ 诊断异常: {exc}")
        return 1
    finally:
        try:
            hand.open_hand()
        except Exception:
            pass
        hand.close()


if __name__ == "__main__":
    sys.exit(main())
