# -*- coding: utf-8 -*-
"""
tools/recover_arm.py —— 机械臂控制器恢复/诊断工具（安全模式/程序节点未找到时用）

用法：
  python tools/recover_arm.py --status            # 仅打印模式/安全/运行状态，不动臂
  python tools/recover_arm.py                     # 上电+启动并确认 Running（臂会上电/断电）
  python tools/recover_arm.py --ip 192.168.1.100  # 指定机械臂 IP

说明：Aubo 的"程序节点未找到/安全模式"多为控制器侧异常；多数可通过
  ① 示教器复位 ② 控制柜断电重启 ③ SDK 上电+启动 恢复。
  详见 docs/控制器安全模式恢复.md
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arm.arm_controller import AuboK5ArmController  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="机械臂控制器恢复/诊断")
    ap.add_argument("--ip", default="", help="机械臂 IP（默认读配置 192.168.1.100）")
    ap.add_argument("--status", action="store_true", help="只诊断不动臂")
    ap.add_argument("--poweroff", action="store_true", help="恢复后执行断电(可选)")
    args = ap.parse_args()

    print("[1/3] 连接机械臂 ...")
    arm = AuboK5ArmController(ip=args.ip or None)
    if not arm.open():
        print("❌ 连接失败：请检查网线/IP/控制柜是否上电。")
        return 1

    def show_status(tag):
        print(f"--- {tag} ---")
        try:
            print("  robot_mode  :", arm.get_robot_mode())
        except Exception as e:
            print("  robot_mode  : 读取失败", e)
        try:
            print("  safety_mode :", arm.get_safety_mode())
        except Exception as e:
            print("  safety_mode : 读取失败", e)
        try:
            print("  steady      :", arm.is_steady())
        except Exception as e:
            print("  steady      : 读取失败", e)

    if args.status:
        show_status("当前状态（只读）")
        arm.close()
        return 0

    print("[2/3] 上电 + 启动（若处于安全模式/异常，此步可能失败，请先看示教器）")
    ok = arm.poweron_and_startup(wait_running=True, timeout_s=20)
    if not ok:
        print("❌ 未能进入 Running。")
        show_status("失败时状态")
        print("请按 docs/控制器安全模式恢复.md：示教器复位→控制柜断电重启→再试；")
        print("或直接咨询遨博技术支持（可能是固件/RTM 程序节点异常）。")
        arm.close()
        return 2

    print("✅ 已进入 Running。")
    show_status("启动后状态")

    if args.poweroff:
        print("[3/3] 断电 ...")
        try:
            arm.power_off()
            print("已断电。")
        except Exception as e:
            print("断电失败(可忽略，示教器操作)：", e)

    arm.close()
    print("恢复流程完成。接下来用 GUI 连接即可（先不要勾选伺服模式）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
