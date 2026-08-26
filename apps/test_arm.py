# -*- coding: utf-8 -*-
"""
test_arm.py —— Aubo K5 机械臂单项验证（连接 / 上电 / 状态 / 关节运动 / 复位）

用法：
  python apps/test_arm.py                     # 仅连接 + 读状态
  python apps/test_arm.py --ip 192.168.1.200  # 指定 IP
  python apps/test_arm.py --move              # 附带安全小幅度关节运动 + 复位
  python apps/test_arm.py --startup           # 上电 + 启动（松刹车）后测试
  python apps/test_arm.py --movel             # 直线运动测试（需先确认 TCP 安全位姿）

安全提示：
  * 首次运行建议 --move 用默认小角度（见下方 SAFE_MOVE_DEG）；
  * 确认机械臂周围无人、无障碍物；急停按钮随时可按。
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

from arm import AuboK5ArmController
from arm.arm_config import ARM_CONFIG

# 安全测试运动（度）：仅动 J2/J3 小幅，默认 5°，验证链路即可
SAFE_MOVE_DEG = [0.0, -15.0, 100.0, 25.0, 90.0, 0.0]      # 起始位
SAFE_MOVE_DEG2 = [0.0, -12.0, 95.0, 25.0, 90.0, 0.0]     # 小幅偏移


def show_state(arm, title="状态"):
    print(f"\n===== {title} =====")
    s = arm.get_state_summary()
    print(f"  模式:        {s['robot_mode']}")
    print(f"  安全模式:    {s['safety_mode']}")
    print(f"  已停止:      {s['steady']}")
    print(f"  安全限制内:  {s['within_safety']}")
    print(f"  速度比例:    {s['speed_fraction']}")
    q = s['joint_positions_rad']
    if q:
        print("  关节角(rad): " + "  ".join(f"{v:+.3f}" for v in q))
        print("  关节角(deg): " + "  ".join(f"{math.degrees(v):+7.1f}" for v in q))
    if s['tcp_pose']:
        p = s['tcp_pose']
        print("  TCP位姿:    " + "  ".join(f"{v:+.4f}" for v in p))


def main():
    ap = argparse.ArgumentParser(description="Aubo K5 机械臂单项验证")
    ap.add_argument("--ip", default=ARM_CONFIG["ip"], help="机械臂 IP")
    ap.add_argument("--port", type=int, default=ARM_CONFIG["rpc_port"], help="RPC 端口")
    ap.add_argument("--move", action="store_true", help="附带安全关节运动测试")
    ap.add_argument("--movel", action="store_true", help="直线运动测试（慎用，需确认 TCP）")
    ap.add_argument("--startup", action="store_true", help="上电 + 启动（松刹车）")
    ap.add_argument("--fraction", type=float, default=ARM_CONFIG["speed_fraction"],
                    help="速度比例 0~1")
    args = ap.parse_args()

    arm = AuboK5ArmController(ip=args.ip, rpc_port=args.port,
                              speed_fraction=args.fraction)
    print(f"连接 {args.ip}:{args.port} ...")
    if not arm.open():
        print("❌ 连接/登录失败（检查 IP、网络、控制柜开机、账号密码）")
        sys.exit(1)
    print("✅ 已连接并登录")

    show_state(arm, "连接后状态")

    if args.startup:
        print("\n上电 + 启动 ...")
        if arm.poweron_and_startup(wait_running=True):
            print("✅ 上电/启动成功（Running）")
        else:
            print("⚠️ 上电/启动未达 Running（可能已运行或需要人工确认）")
        time.sleep(1)
        show_state(arm, "上电后状态")

    if args.move:
        print(f"\n关节运动测试（速度比例 {args.fraction}）...")
        q1 = [math.radians(d) for d in SAFE_MOVE_DEG]
        q2 = [math.radians(d) for d in SAFE_MOVE_DEG2]
        ret, msg = arm.movej(q1, speed_deg=20, acc_deg=15, block=True)
        print(f"  movej -> 起始位: ret={ret} {msg or ''}")
        ret, msg = arm.movej(q2, speed_deg=20, acc_deg=15, block=True)
        print(f"  movej -> 偏移位: ret={ret} {msg or ''}")
        ret, msg = arm.movej(q1, speed_deg=20, acc_deg=15, block=True)
        print(f"  movej -> 回起始: ret={ret} {msg or ''}")
        show_state(arm, "运动后状态")

    if args.movel:
        print("\n直线运动测试（TCP 系，需确认当前 TCP 安全）...")
        cur = arm.get_tcp_pose()
        if cur is None:
            print("❌ 读不到当前 TCP，取消 movel")
        else:
            target = list(cur)
            target[2] -= 0.05   # 沿 TCP Z 下降 5cm（安全方向由用户确认）
            print(f"  目标位姿: {[round(v, 4) for v in target]}")
            ret, msg = arm.movel(target, speed=0.1, acc=0.1, block=True)
            print(f"  movel ret={ret} {msg or ''}")
            show_state(arm, "movel 后状态")

    print("\n断开连接 ...")
    arm.close()
    print("✅ 完成")


if __name__ == "__main__":
    main()
