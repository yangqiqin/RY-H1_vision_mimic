# -*- coding: utf-8 -*-
"""
tools/calibrate_wrist_tcp.py —— 腕部(相机系)→机械臂 多点最小二乘标定器
=====================================================================
比"GUI 里单点 offset 填框"更准的标定：采多组对应点，对每个轴最小二乘拟合
    arm_i = scale_i * cam_i + add_i
（返回与 map_wrist_to_arm_pose 完全兼容的 scale/add；附每轴 RMSE 与 R² 评估）。

★ 采集原则（决定精度）：
  1) 把机械臂末端（法兰/TCP，须与你跟随用的目标一致）移到某个点，让手腕恰好处于
     该点上方/所在位置（目标：人手腕在相机看到的 3D = 该点）；
  2) 从 GUI"协同控制"面板复制"腕3D=(x,y,z)"（相机系米）→ 作为 cam；
  3) 记录此时机械臂 flange/TCP 位置（GUI 机械臂页读位姿填充，或本工具 --arm 自动读）
     → 作为 arm；
  4) 至少 8 组，覆盖桌面前后左右、不同高度；每组手腕保持 1~2 秒取平稳值再复制。

用法（PyCharm Terminal 或命令行）：
  python tools/calibrate_wrist_tcp.py -f samples.csv
  python tools/calibrate_wrist_tcp.py --interactive [--arm 192.168.1.100]
  samples.csv 每行 6 个数字(空格或逗号)：cam_x cam_y cam_z arm_x arm_y arm_z

输出：可直接贴进 GUI【协同控制 → 标定】：scale 填前 3 个，add 填后 3 个，offset 填 0。
RMSE(米) 告诉你平均偏差：>0.02 说明某组手抖/记录错位/相机系不稳定，应剔除重采。
"""
import argparse
import csv
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arm.arm_follow import ArmFollower  # noqa: E402


def load_csv(path: str) -> list:
    pairs = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            row = [r for r in row if r.strip() != ""]
            if not row:
                continue
            vals = []
            for cell in row:
                vals.extend(cell.replace(";", " ").split())
            if len(vals) < 6:
                print(f"[warn] 第{line_no}行字段不足6个，跳过: {row}")
                continue
            try:
                nums = [float(v) for v in vals[:6]]
            except ValueError:
                print(f"[warn] 第{line_no}行非数字，跳过")
                continue
            pairs.append((nums[:3], nums[3:6]))
    return pairs


def interactive_collect(arm_ip: str) -> list:
    arm = None
    if arm_ip:
        try:
            from arm.arm_controller import AuboK5ArmController
            arm = AuboK5ArmController(ip=arm_ip)
            if not arm.open():
                print("[warn] 机械臂连接失败，将改为手动输入 arm 坐标")
                arm = None
            else:
                arm.poweron_and_startup(wait_running=True, timeout_s=15)
                print(f"[info] 已连接机械臂 {arm_ip}（回车即读取当前法兰位置作为 arm）")
        except Exception as e:
            print(f"[warn] 机械臂初始化失败: {e}")
            arm = None

    print("\n交互采集：每次输入一行 'cam_x cam_y cam_z'（相机系腕部 3D，米）。")
    print("采集够后输入空行结束。")
    pairs = []
    while True:
        try:
            line = input("cam3D > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        try:
            cam = [float(x) for x in line.replace(",", " ").split()]
            if len(cam) < 3:
                raise ValueError
            cam = cam[:3]
        except ValueError:
            print("  格式错，示例: 0.12 -0.25 0.55")
            continue
        if arm is not None:
            try:
                input(f"  已记 cam={cam}。请把机械臂末端移到该点（键盘拖拽或命令），"
                      f"到位后回车读取法兰位置…")
                pose = arm.get_flange_pose()
                if pose is None:
                    print("  读取法兰位置失败，重试")
                    continue
                arm_xyz = list(pose[:3])
                print(f"  arm(法兰)= {[round(v, 4) for v in arm_xyz]}")
            except KeyboardInterrupt:
                break
        else:
            line2 = input("  arm3D(法兰/TCP x y z) > ").strip()
            try:
                arm_xyz = [float(x) for x in line2.replace(",", " ").split()][:3]
            except (ValueError, IndexError):
                print("  格式错")
                continue
        pairs.append((cam, arm_xyz))
        print(f"  → 已收集 {len(pairs)} 组")
    if arm is not None:
        arm.close()
    return pairs


def main():
    ap = argparse.ArgumentParser(description="腕部→机械臂 多点最小二乘标定")
    ap.add_argument("-f", "--file", help="samples 文件（每行 cam3 arm3，6 个数字）")
    ap.add_argument("--interactive", action="store_true", help="交互采集")
    ap.add_argument("--arm", default="", help="机械臂 IP（交互模式自动读法兰位置）")
    args = ap.parse_args()

    if args.file:
        pairs = load_csv(args.file)
    elif args.interactive:
        pairs = interactive_collect(args.arm)
    else:
        ap.print_help()
        return 1
    if len(pairs) < 3:
        print(f"有效样本仅 {len(pairs)} 组，至少 3 组，建议 ≥8 组。")
        return 1

    calib = ArmFollower.fit_calibration_from_pairs(pairs)
    fit = calib["_fit"]
    print("\n================= 标定结果 =================")
    print(f"样本数      : {fit['n_samples']}")
    for i, axis in enumerate("xyz"):
        print(f"轴 {axis}      : scale={calib['scale'][i]:.4f}  add={calib['add'][i]:.4f}  "
              f"RMSE={fit['rmse_m'][i]*1000:.1f}mm  R²={fit['r2'][i]:.3f}")
    print(f"\noffset = 0, 0, 0")
    print(f"scale  = {[round(v, 4) for v in calib['scale']]}")
    print(f"add    = {[round(v, 4) for v in calib['add']]}")
    print("\n把上面 scale/add 填入 GUI【协同控制 → 标定】，offset 填 0。")
    rmse = max(fit["rmse_m"])
    if rmse > 0.02:
        print(f"[警告] 最差轴 RMSE {rmse*1000:.0f}mm > 20mm：请剔除手抖/错位的样本后重采。")
    else:
        print(f"[OK] 最差轴 RMSE {rmse*1000:.0f}mm，精度可接受。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
