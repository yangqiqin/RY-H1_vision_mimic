# -*- coding: utf-8 -*-
"""
diag_arm.py —— Aubo K5 机械臂深度诊断（连接 / 电源 / 状态 / 正逆解 / IO / 示教 / 复位）

用法：
  python apps/diag_arm.py                    # 连接 + 全量状态
  python apps/diag_arm.py --ip 192.168.1.100   # 指定 IP（实测可用）
  python apps/diag_arm.py --poweron          # 上电+启动
  python apps/diag_arm.py --freedrive 10     # 进入拖拽示教 10 秒后退出
  python apps/diag_arm.py --fk                # 正解自检
  python apps/diag_arm.py --ik                # 逆解自检
  python apps/diag_arm.py --stop              # 停止运动
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


def main():
    ap = argparse.ArgumentParser(description="Aubo K5 机械臂深度诊断")
    ap.add_argument("--ip", default=ARM_CONFIG["ip"])
    ap.add_argument("--port", type=int, default=ARM_CONFIG["rpc_port"])
    ap.add_argument("--poweron", action="store_true", help="上电+启动")
    ap.add_argument("--freedrive", type=float, default=0,
                    help="进入拖拽示教 N 秒（0=不进入）")
    ap.add_argument("--fk", action="store_true", help="正解自检")
    ap.add_argument("--ik", action="store_true", help="逆解自检")
    ap.add_argument("--stop", action="store_true", help="停止运动")
    ap.add_argument("--fraction", type=float, default=ARM_CONFIG["speed_fraction"])
    args = ap.parse_args()

    arm = AuboK5ArmController(ip=args.ip, rpc_port=args.port,
                              speed_fraction=args.fraction)
    print(f"[1] 连接 {args.ip}:{args.port} ...")
    if not arm.open():
        print("❌ 连接/登录失败")
        sys.exit(1)
    print("✅ 已连接并登录")

    print("\n[2] 基本信息")
    s = arm.get_state_summary()
    for k, v in s.items():
        print(f"    {k}: {v}")

    if args.stop:
        print("\n[3] 停止运动")
        print("    stopMove ret =", arm.stop_move())

    if args.poweron:
        print("\n[3] 上电 + 启动（松刹车）")
        if arm.poweron_and_startup(wait_running=True, timeout_s=15):
            print("    ✅ Running")
        else:
            print("    ⚠️ 未达 Running，当前模式:", arm.get_robot_mode())
        time.sleep(1)
        s = arm.get_state_summary()
        print("    模式:", s["robot_mode"], "| 安全:", s["safety_mode"],
              "| 已停止:", s["steady"])

    if args.fk:
        print("\n[4] 正解自检（给定关节角 -> 位姿）")
        q = [0.0, -0.26, 1.74, 0.44, 1.57, 0.0]
        pose, ret = arm.forward_kinematics(q)
        print(f"    q(deg) = {[round(math.degrees(v), 1) for v in q]}")
        print(f"    ret = {ret}")
        if pose:
            print(f"    pose = {[round(v, 4) for v in pose]}")

    if args.ik:
        print("\n[5] 逆解自检（位姿 -> 关节角）")
        pose = [0.549, -0.121, 0.465, 3.138, 0.001, 1.571]
        ref_q = [0.0, -0.26, 1.74, 0.44, 1.57, 0.0]
        q, ret = arm.inverse_kinematics(ref_q, pose)
        print(f"    pose = {pose}")
        print(f"    ret = {ret}")
        if q:
            print(f"    q(deg) = {[round(math.degrees(v), 2) for v in q]}")

    print("\n[6] IO 快速检查")
    di = arm.get_standard_digital_inputs()
    do = arm.get_standard_digital_outputs()
    if di is not None:
        print(f"    标准数字输入: {di}")
    if do is not None:
        print(f"    标准数字输出: {do}")

    if args.freedrive > 0:
        print(f"\n[7] 进入拖拽示教 {args.freedrive} 秒（可手动拖动机臂）...")
        ok = arm.freedrive(True, duration_s=args.freedrive)
        print(f"    freedrive ret = {ok}")

    print("\n断开连接 ...")
    arm.close()
    print("✅ 完成")


if __name__ == "__main__":
    main()
