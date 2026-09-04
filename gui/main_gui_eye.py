# -*- coding: utf-8 -*-
"""
main_gui_eye.py —— 眼在手上协同控制（全功能安全版）
功能：
  1. 读取当前末端姿态并固定。
  2. 安全框以【米】为单位设置（与机械臂末端读数同单位，直接对比无换算），越界即急停。
  3. 启用Aubo碰撞检测，遇阻立即停止。
  4. 丢失手腕跟踪自动急停。
  5. ★ J4/J5/J6 各关节独立硬限设置（GUI可调，最大90°）
  6. ★ 通过 Socket 调用 C++ 程序启用 SDK 碰撞盒（硬件级保护）
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import math
import time
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

from gui.main_gui_holistic import MainGuiHolistic
from vision.hand_eye import HandEyeCalibration, CALIB
from arm.arm_safety import ArmSafetyBox, DEFAULT_MIN_Z, DEFAULT_MAX_Z
from arm.arm_follow_eye import EyeInHandFollower

from typing import Optional, List, Dict


class MainGuiEye(MainGuiHolistic):
    def __init__(self, root: tk.Tk):
        super().__init__(root)
        self.hand_eye = HandEyeCalibration()
        self.safety_box = ArmSafetyBox()
        self.following = False
        self.follower: EyeInHandFollower | None = None  # 安全跟随控制器（含碰撞/停滞/姿态锁检测）
        self.max_step_m = 0.01  # 5mm/帧
        self.lost_frames_limit = 5
        self.lost_counter = 0
        self.prev_P_base = None
        self.fixed_rpy = [math.pi, 0.0, 0.0]  # 默认初始值，将被读取替换

        # ★ 各关节独立硬限默认值
        self.wrist_hard_j4_deg = 30.0
        self.wrist_hard_j5_deg = 30.0
        self.wrist_hard_j6_deg = 30.0
        self.wrist_tol_deg = 3.0

        self.eye_state_var = tk.StringVar(value="眼在手上未启动")
        self.rpy_labels = []
        self.safety_live_var = tk.StringVar(value="当前末端位置: --")
        self.follow3d_var = tk.StringVar(value="--")
        self._last_status_shown = ""      # 状态去重（避免每帧刷日志台）
        self._last_eye_t = 0.0            # 跟随 update 时间戳（算 HUD fps）
        self._eye_fps = 0.0
        self._table_zone_enabled = False  # 是否启用了 WorldZone 桌面危险腔
        self._table_zone_broken = False   # 固件不支持 WorldZone(32601) 缓存，避免每次重复失败调用
        self._build_eye_ui()
        self._eye_poll_loop()

    # ================== 界面构建 ==================
    def _build_eye_ui(self):
        tab_eye = ttk.Frame(self.arm_notebook)
        self.arm_notebook.add(tab_eye, text="  眼在手上控制  ")
        tab_eye.grid_columnconfigure(0, weight=1)

        # ---- 手眼标定 ----
        r1 = ttk.LabelFrame(tab_eye, text="手眼标定（相机系→末端法兰系）")
        r1.pack(fill="x", padx=4, pady=2)
        ttk.Button(r1, text="查看标定参数", command=self._eye_show_calib).pack(side="left", padx=2)
        ttk.Button(r1, text="切换备用标定", command=self._eye_switch_calib).pack(side="left", padx=2)

        # ---- 固定末端姿态 ----
        r_fixed = ttk.LabelFrame(tab_eye, text="固定末端姿态（读取当前并锁定）")
        r_fixed.pack(fill="x", padx=4, pady=2)
        sub_f = ttk.Frame(r_fixed)
        sub_f.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_f, text="Rx(rad):").pack(side="left")
        self.fixed_rx_var = tk.StringVar(value="3.1416")
        ttk.Entry(sub_f, textvariable=self.fixed_rx_var, width=8).pack(side="left", padx=2)
        ttk.Label(sub_f, text="Ry:").pack(side="left")
        self.fixed_ry_var = tk.StringVar(value="0.0")
        ttk.Entry(sub_f, textvariable=self.fixed_ry_var, width=8).pack(side="left", padx=2)
        ttk.Label(sub_f, text="Rz:").pack(side="left")
        self.fixed_rz_var = tk.StringVar(value="0.0")
        ttk.Entry(sub_f, textvariable=self.fixed_rz_var, width=8).pack(side="left", padx=2)
        ttk.Button(sub_f, text="读取当前末端姿态", command=self._eye_read_current_rpy).pack(side="left", padx=4)
        ttk.Button(sub_f, text="应用固定姿态", command=self._eye_apply_fixed_rpy).pack(side="left", padx=4)
        self.fixed_status_var = tk.StringVar(value="未锁定")
        ttk.Label(sub_f, textvariable=self.fixed_status_var, foreground="blue").pack(side="left", padx=6)

        # ---- 高度安全区（z 轴，单位米，基坐标系） ----
        r2 = ttk.LabelFrame(tab_eye, text="高度安全区（z轴·单位米·基坐标系：防碰桌面/防升太高）")
        r2.pack(fill="x", padx=4, pady=2)
        sub_b = ttk.Frame(r2)
        sub_b.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_b, text="min z (m):").pack(side="left")
        self.safe_min_vars = [tk.StringVar(value=f"{DEFAULT_MIN_Z:.2f}")]
        ttk.Entry(sub_b, textvariable=self.safe_min_vars[0], width=7).pack(side="left", padx=1)
        ttk.Label(sub_b, text="max z (m):").pack(side="left", padx=(8, 0))
        self.safe_max_vars = [tk.StringVar(value=f"{DEFAULT_MAX_Z:.2f}")]
        ttk.Entry(sub_b, textvariable=self.safe_max_vars[0], width=7).pack(side="left", padx=1)
        ttk.Button(sub_b, text="应用高度安全区", command=self._eye_apply_safety).pack(side="left", padx=6)
        self.safety_state_var = tk.StringVar(value="未设置")
        ttk.Label(sub_b, textvariable=self.safety_state_var, foreground="gray", font=("", 8)).pack(side="left", padx=6)

        # 实时"末端高度 vs 高度安全区"诊断行
        sub_b2 = ttk.Frame(r2)
        sub_b2.pack(fill="x", padx=2, pady=1)
        self.safety_live_var = tk.StringVar(value="当前末端高度: --（请连接机械臂后查看）")
        ttk.Label(sub_b2, textvariable=self.safety_live_var,
                  font=("Consolas", 8), foreground="blue").pack(side="left")

        # ---- 跟随控制（含各关节独立硬限设置） ----
        r3 = ttk.LabelFrame(tab_eye, text="跟随控制（自动碰撞检测）")
        r3.pack(fill="x", padx=4, pady=2)

        # 第一行：按钮和基本参数
        sub_c = ttk.Frame(r3)
        sub_c.pack(fill="x", padx=2, pady=1)
        ttk.Button(sub_c, text="▶ 开始跟随", command=self._eye_start_follow).pack(side="left", padx=2)
        ttk.Button(sub_c, text="⏹ 停止跟随(急停)", command=self._eye_stop_follow).pack(side="left", padx=2)
        ttk.Label(sub_c, text="垂向限幅mm/帧:").pack(side="left", padx=(14, 2))
        self.eye_step_var = tk.StringVar(value="10")
        ttk.Entry(sub_c, textvariable=self.eye_step_var, width=4).pack(side="left")
        ttk.Label(sub_c, text="丢手帧数:").pack(side="left", padx=(10, 2))
        self.eye_lost_var = tk.StringVar(value="5")
        ttk.Entry(sub_c, textvariable=self.eye_lost_var, width=4).pack(side="left")
        ttk.Label(sub_c, text="锁腕容差°:").pack(side="left", padx=(10, 2))
        self.eye_wrist_tol_var = tk.StringVar(value="3.0")
        ttk.Entry(sub_c, textvariable=self.eye_wrist_tol_var, width=4).pack(side="left")
        ttk.Label(sub_c, textvariable=self.eye_state_var, foreground="red").pack(side="left", padx=10)

        # ★ 第二行：各关节独立硬限（J4/J5/J6，最大值90°）
        sub_c2 = ttk.Frame(r3)
        sub_c2.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_c2, text="锁腕硬限(°):", font=("", 9, "bold")).pack(side="left", padx=(0, 6))

        ttk.Label(sub_c2, text="J4(俯仰):").pack(side="left")
        self.eye_hard_j4_var = tk.StringVar(value="30.0")
        ttk.Entry(sub_c2, textvariable=self.eye_hard_j4_var, width=4).pack(side="left", padx=(0, 10))

        ttk.Label(sub_c2, text="J5(偏航):").pack(side="left")
        self.eye_hard_j5_var = tk.StringVar(value="30.0")
        ttk.Entry(sub_c2, textvariable=self.eye_hard_j5_var, width=4).pack(side="left", padx=(0, 10))

        ttk.Label(sub_c2, text="J6(翻滚):").pack(side="left")
        self.eye_hard_j6_var = tk.StringVar(value="30.0")
        ttk.Entry(sub_c2, textvariable=self.eye_hard_j6_var, width=4).pack(side="left", padx=(0, 10))

        ttk.Label(sub_c2, text="(最大90°)", foreground="gray", font=("", 8)).pack(side="left")

        # 状态显示行
        sub_d = ttk.Frame(r3)
        sub_d.pack(fill="x", padx=2, pady=1)
        self.eye_status_var = tk.StringVar(value="状态: -")
        ttk.Label(sub_d, textvariable=self.eye_status_var, font=("Consolas", 8),
                  foreground="blue", justify="left", wraplength=900).pack(side="left")

        # ---- 3D 坐标跟随状态（末端/期望目标/剩余，基坐标系，单位米） ----
        sub_f3 = ttk.LabelFrame(tab_eye, text="3D 坐标跟随状态（基坐标系·米：手动多少末端跟多少）")
        sub_f3.pack(fill="x", padx=4, pady=2)
        self.follow3d_var = tk.StringVar(value="末端(x,y,z)=--  期望(x,y,z)=--  剩余=--（跟随中显示）")
        ttk.Label(sub_f3, textvariable=self.follow3d_var, font=("Consolas", 8),
                  foreground="darkgreen", justify="left").pack(side="left", padx=4, pady=1)

        # ---- 实时末端姿态 ----
        r4 = ttk.LabelFrame(tab_eye, text="实际末端姿态（应等于固定值）")
        r4.pack(fill="x", padx=4, pady=2)
        for idx, name in enumerate(["Rx", "Ry", "Rz"]):
            ttk.Label(r4, text=name + ":").grid(row=0, column=idx * 2, padx=5, pady=2, sticky="e")
            lbl = ttk.Label(r4, text="---", width=10, font=("Consolas", 10))
            lbl.grid(row=0, column=idx * 2 + 1, padx=5, pady=2, sticky="w")
            self.rpy_labels.append(lbl)

    # ================== 按钮回调 ==================
    def _eye_show_calib(self):
        cal = self.hand_eye.get_calibration()
        msg = f"R_cam2gripper =\n{cal['R_cam2gripper']}\n\nt_cam2gripper = {cal['t_cam2gripper']}"
        messagebox.showinfo("手眼标定参数", msg)

    def _eye_switch_calib(self):
        cur_t = self.hand_eye.get_calibration()["t_cam2gripper"]
        if np.allclose(cur_t, CALIB["t_cam2gripper"]):
            self.hand_eye.set_calibration(CALIB["R_cam2gripper_alt"], CALIB["t_cam2gripper_alt"])
            self.eye_state_var.set("已切换备用标定")
        else:
            self.hand_eye.set_calibration(CALIB["R_cam2gripper"], CALIB["t_cam2gripper"])
            self.eye_state_var.set("已切换默认标定")
        self._eye_show_calib()

    def _eye_read_current_rpy(self):
        """读取当前末端姿态并填入固定姿态输入框（用法兰位姿，与安全检测一致）"""
        if not self.arm_connected or self.arm is None:
            messagebox.showwarning("提示", "请先连接机械臂")
            return
        try:
            if hasattr(self.arm, "get_flange_pose"):
                pose = self.arm.get_flange_pose()
            else:
                pose = self.arm.get_tcp_pose()
            if pose is None or len(pose) < 6:
                messagebox.showwarning("提示", "无法读取当前姿态")
                return
            rx, ry, rz = pose[3], pose[4], pose[5]
            self.fixed_rx_var.set(f"{rx:.4f}")
            self.fixed_ry_var.set(f"{ry:.4f}")
            self.fixed_rz_var.set(f"{rz:.4f}")
            self.fixed_status_var.set("已读取，请点击'应用固定姿态'锁定")
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    def _eye_apply_fixed_rpy(self):
        try:
            rx = float(self.fixed_rx_var.get())
            ry = float(self.fixed_ry_var.get())
            rz = float(self.fixed_rz_var.get())
            self.fixed_rpy = [rx, ry, rz]
            self.fixed_status_var.set(f"已锁定: [{rx:.3f}, {ry:.3f}, {rz:.3f}] rad")
            self.eye_state_var.set("末端姿态已固定")
        except ValueError:
            messagebox.showerror("输入错误", "姿态必须是数字（弧度）")

    def _eye_apply_safety(self):
        try:
            min_z = float(self.safe_min_vars[0].get())
            max_z = float(self.safe_max_vars[0].get())
            if not self.safety_box.set_box(min_z=min_z, max_z=max_z):
                messagebox.showerror(
                    "高度安全区参数错误",
                    "数值异常被拒绝：单位为【米】（与末端读数一致），范围 [-1, 3]m 且 min_z≤max_z；\n"
                    "若你填的是 cm（如 50）请填 0.5。原区间保持不变。")
                return
            self.safety_state_var.set(f"✓ 已应用: z[{min_z:.2f}, {max_z:.2f}] m（基坐标系）")
            self.eye_state_var.set("高度安全区已更新")
            self._refresh_safety_live()
        except ValueError:
            messagebox.showerror("输入错误", "高度安全区参数必须是数字（米）")

    def _read_pose_once(self):
        """读一次当前末端位姿（供多个 UI 标签共用，减少机械臂 RPC——实时性优化）。"""
        if not getattr(self, "arm_connected", False) or self.arm is None:
            return None
        try:
            if hasattr(self.arm, "get_flange_pose"):
                return self.arm.get_flange_pose()
            return self.arm.get_tcp_pose()
        except Exception:
            return None

    def _refresh_safety_live(self, pose: Optional[list] = None):
        """实时刷新：末端 z 高度(m) + 高度安全区 + 判定（仅 z，基坐标系，xy 不计入）。"""
        if pose is None:
            pose = self._read_pose_once()
        if pose is None or len(pose) < 3:
            self.safety_live_var.set("当前末端高度: --（机械臂未连接/读取失败）")
            return
        try:
            z = float(pose[2])
            ok, msg = self.safety_box.check_pose([0.0, 0.0, z], margin=0.0)
            judge = "区内 ✓" if ok else f"区外 ✗ {msg}"
            self.safety_live_var.set(
                f"末端z={z:.3f}m 高度安全区z[{self.safety_box.min_z:.2f},"
                f"{self.safety_box.max_z:.2f}]m → {judge}（基坐标系，xy不计入）")
        except Exception as exc:
            self.safety_live_var.set(f"实时判定异常: {exc}")

    def _refresh_follow3d(self, pose: Optional[list] = None):
        """3D 坐标跟随状态：末端(x,y,z) / 期望目标(x,y,z) / 剩余追赶量（基坐标系·米）。"""
        if self.follower is None or not getattr(self.follower, "running", False):
            self.follow3d_var.set("末端(x,y,z)=-- 期望=-- 剩余=--（未在跟随）")
            return
        try:
            s = self.follower.get_stats()
            cur = None
            if pose is not None and len(pose) >= 3:
                cur = tuple(round(float(v), 3) for v in pose[:3])
            elif self.arm is not None:
                p = (self.arm.get_flange_pose()
                     if hasattr(self.arm, "get_flange_pose") else self.arm.get_tcp_pose())
                if p is not None and len(p) >= 3:
                    cur = tuple(round(float(v), 3) for v in p[:3])
            des = s.get("desired_xyz")
            des_txt = (f"({des[0]:.3f},{des[1]:.3f},{des[2]:.3f})"
                       if des else "--")
            mv = "手腕运动" if s.get("hand_moving") else "手腕静止"
            rem = s.get("step_remaining_mm", 0.0)
            cur_txt = (f"({cur[0]:.3f},{cur[1]:.3f},{cur[2]:.3f})" if cur else "--")
            # HUD：跟随帧率 / 总帧 / 丢弃统计（判断"手的动作是否被误丢"）
            drops = s.get("drops") or {}
            hud = (f" | {self._eye_fps:.0f}fps 帧{s.get('frames_total', 0)} "
                   f"丢:突跳{drops.get('bad_jump', 0)} 忙{drops.get('busy', 0)} "
                   f"到位{drops.get('done', 0)} 坏点{drops.get('bad_point', 0)}")
            self.follow3d_var.set(
                f"末端(x,y,z)=({cur_txt})  期望目标=({des_txt})  剩余Δ={rem:.0f}mm  "
                f"{mv}{hud}")
        except Exception as exc:
            self.follow3d_var.set(f"3D 状态异常: {exc}")

    # ================== 碰撞盒 / WorldZone 硬件保护 ==================
    def _enable_table_zone_fallback(self):
        """addCollisionBox 与 WorldZone 均为本控制器固件不支持(32601)时的兜底处理：
        尝试启用 WorldZone 桌面危险腔；失败(32601)后缓存结论，不再每次重复失败调用。"""
        if getattr(self, "_table_zone_broken", False):
            self.eye_state_var.set(
                "（控制器固件不支持 addCollisionBox/setWorldZone(32601) → 无硬件保护，"
                "软件安全链兜底）")
            return
        self._table_zone_enabled = False
        if self.arm is None or not hasattr(self.arm, "enable_table_protect_zone"):
            self._table_zone_broken = True
            self.eye_state_var.set(
                "（⚠️ 无 WorldZone 接口且固件不支持碰撞盒 → 软件安全链兜底）")
            return
        try:
            floor_z = max(0.05, self.safety_box.min_z - 0.10)   # 桌面下限下方留余量
            ret, note = self.arm.enable_table_protect_zone(floor_z=floor_z)
            if ret == 0:
                self._table_zone_enabled = True
                self.eye_state_var.set(f"（✅ 硬件保护已启用：{note}）")
            else:
                self._table_zone_broken = True
                self.eye_state_var.set(
                    f"（控制器固件不支持硬件碰撞盒/setWorldZone(32601) → 软件安全链兜底）")
        except Exception as exc:
            self._table_zone_broken = True
            self.eye_state_var.set(f"（⚠️ WorldZone 启用异常 {exc} → 软件安全链兜底）")

    def _disable_table_zone_if_enabled(self):
        """跟随停止/关窗时关闭本页启用的 WorldZone（避免残留硬件限制）。"""
        if getattr(self, "_table_zone_enabled", False) and self.arm is not None:
            try:
                if hasattr(self.arm, "disable_world_zone"):
                    self.arm.disable_world_zone()
            except Exception:
                pass
            self._table_zone_enabled = False

    def _start_collision_box_service(self) -> bool:
        """启动 C++ 碰撞盒服务端并通过 Socket 启用碰撞盒"""
        try:
            from arm.collision_box_client import (
                start_cpp_collision_server, get_collision_client
            )

            # 启动 C++ 服务端（如果未启动）；用当前机械臂 IP，避免服务端连错机器人
            rob_ip = getattr(self.arm, "ip", None) if self.arm is not None else None
            if not start_cpp_collision_server(robot_ip=rob_ip):
                from arm.collision_box_client import get_collision_start_error
                why = get_collision_start_error().replace("\n", " ")
                self.eye_state_var.set(
                    f"（⚠️ 碰撞盒服务启动失败: {why[:160]} → 软件安全链兜底）")
                return False

            # 获取碰撞盒参数
            if not hasattr(self, "tool_box_size_vars"):
                self.eye_state_var.set("（⚠️ 碰撞盒尺寸未配置 → 软件安全链兜底）")
                return False

            size_cm = [float(v.get()) for v in self.tool_box_size_vars]
            z_cm = float(self.tool_box_z_var.get())

            # 单位转换：cm → m
            sizes = [v / 100.0 for v in size_cm]
            poses = [0.0, 0.0, z_cm / 100.0, 0.0, 0.0, 0.0]

            # 通过 Socket 调用 C++ 程序添加碰撞盒
            client = get_collision_client()
            response = client.add_collision_box(
                name="tool_box",
                link="end_effector",
                sizes=sizes,
                poses=poses
            )

            if response.get("status") == "ok":
                mode = response.get("mode", "sdk")
                if mode == "sdk":
                    self.eye_state_var.set("（✅ 末端碰撞盒已启用，C++ SDK 硬件级保护）")
                else:
                    # mock/演示服务端：addCollisionBox 固件不支持(32601)，C++ 同 RPC 也一样。
                    # → 尝试真实可用的硬件级替代：WorldZone 桌面危险腔（腔内危险停机）
                    self._enable_table_zone_fallback()
                return True
            else:
                err_msg = response.get("msg", "未知错误")
                self.eye_state_var.set(f"（⚠️ 碰撞盒启用失败: {err_msg} → 软件安全链兜底）")
                return False

        except ImportError as e:
            self.eye_state_var.set(f"（⚠️ 碰撞盒模块导入失败: {e} → 软件安全链兜底）")
            return False
        except Exception as e:
            self.eye_state_var.set(f"（⚠️ 碰撞盒启用异常: {e} → 软件安全链兜底）")
            return False

    def _remove_collision_box(self):
        """移除碰撞盒"""
        try:
            from arm.collision_box_client import get_collision_client
            client = get_collision_client()
            response = client.remove_collision_box("tool_box")
            if response.get("status") == "ok":
                self.eye_state_var.set("已停止（碰撞盒已移除）")
            else:
                self.eye_state_var.set("已停止（碰撞盒移除失败）")
        except Exception:
            pass

    def _stop_collision_box_service(self):
        """停止 C++ 碰撞盒服务端"""
        try:
            from arm.collision_box_client import stop_cpp_collision_server
            stop_cpp_collision_server()
        except Exception:
            pass

    # ================== 跟随控制 ==================
    def _eye_start_follow(self):
        if not self.arm_connected or self.arm is None:
            messagebox.showwarning("提示", "请先连接机械臂")
            return
        if not self.holistic_running:
            messagebox.showwarning("提示", "请先启用 Holistic 检测")
            return

        # 姿态统一：若机械臂面板已锁定姿态，眼在手上跟随自动采用该锁定值
        if getattr(self, "_pose_locked", False) and hasattr(self, "_locked_rpy"):
            self.fixed_rpy = list(self._locked_rpy)
            try:
                self.fixed_rx_var.set(f"{self.fixed_rpy[0]:.4f}")
                self.fixed_ry_var.set(f"{self.fixed_rpy[1]:.4f}")
                self.fixed_rz_var.set(f"{self.fixed_rpy[2]:.4f}")
                self.fixed_status_var.set(f"已采用机械臂锁定姿态: [{self.fixed_rpy[0]:.3f}, "
                                          f"{self.fixed_rpy[1]:.3f}, {self.fixed_rpy[2]:.3f}] rad")
            except Exception:
                pass
        elif self.fixed_status_var.get().startswith("未锁定"):
            if not messagebox.askyesno("警告", "末端姿态尚未固定，继续？"):
                return

        try:
            self.max_step_m = float(self.eye_step_var.get()) / 1000.0
            self.lost_frames_limit = int(self.eye_lost_var.get())
            self.wrist_tol_deg = float(self.eye_wrist_tol_var.get())
            # ★ 读取各关节独立硬限（最大90°）
            self.wrist_hard_j4_deg = min(float(self.eye_hard_j4_var.get()), 90.0)
            self.wrist_hard_j5_deg = min(float(self.eye_hard_j5_var.get()), 90.0)
            self.wrist_hard_j6_deg = min(float(self.eye_hard_j6_var.get()), 90.0)
        except ValueError:
            messagebox.showerror("输入错误", "限幅/丢手/锁腕容差/硬限参数必须是数字")
            return

        # 启用 Aubo SDK 碰撞检测（软件级）
        if self.arm is not None:
            try:
                if hasattr(self.arm, '_robot_manage') and self.arm._robot_manage is not None:
                    self.arm._robot_manage.setCollisionLevel(3)
                    self.eye_state_var.set("碰撞检测已启用")
            except Exception as e:
                self.eye_state_var.set(f"碰撞检测启用失败: {e}")

        # 跟随期间清除 TCP 偏移
        try:
            if hasattr(self.arm, "apply_tcp_offset"):
                self.arm.apply_tcp_offset([0.0] * 6)
                self.eye_state_var.set("（跟随模式：TCP 偏移已清零，法兰=目标系）")
        except Exception:
            pass

        # 读取当前真实法兰姿态作为固定姿态
        try:
            if hasattr(self.arm, "get_flange_pose"):
                cur_pose = self.arm.get_flange_pose()
            else:
                cur_pose = self.arm.get_tcp_pose()
            if cur_pose is not None and len(cur_pose) >= 6:
                self.fixed_rpy = [float(v) for v in cur_pose[3:6]]
                try:
                    self.fixed_rx_var.set(f"{self.fixed_rpy[0]:.4f}")
                    self.fixed_ry_var.set(f"{self.fixed_rpy[1]:.4f}")
                    self.fixed_rz_var.set(f"{self.fixed_rpy[2]:.4f}")
                except Exception:
                    pass
        except Exception:
            pass

        # 启动前安全检查：当前末端 z 必须已在高度安全区内
        try:
            pose0 = (self.arm.get_flange_pose()
                     if hasattr(self.arm, "get_flange_pose") else self.arm.get_tcp_pose())
            if pose0 is not None and len(pose0) >= 3:
                ok0, msg0 = self.safety_box.check_pose(pose0[:3], margin=0.005)
                if not ok0:
                    z0 = float(pose0[2])
                    if not messagebox.askyesno(
                            "⚠️ 当前末端高度不在安全区",
                            f"当前末端 z={z0:.3f}m（基坐标系）\n"
                            f"判定: {msg0}\n高度安全区 z=[{self.safety_box.min_z:.2f},"
                            f"{self.safety_box.max_z:.2f}]m\n\n"
                            "末端当前高度已在安全区外：开始跟随后任何微小升降都会被拦截并急停。\n"
                            "建议先点【应用高度安全区】把区间调大覆盖当前高度，或先调整末端高度。\n\n"
                            "仍要继续吗？"):
                        return
        except Exception:
            pass

        # ★ 创建跟随器时传入各关节独立硬限
        # 注意：bound_stop_frames/rpy_tolerance_deg/torque_threshold 用 follower 默认
        # （越界6帧、姿态3°、力矩15N·m连续2帧——均为"降低误急停"校准值，见 arm_follow_eye.py 常量）
        self.follower = EyeInHandFollower(
            arm=self.arm, hand_eye=self.hand_eye, safety_box=self.safety_box,
            max_step_m=max(0.001, self.max_step_m),
            lost_frames=max(2, self.lost_frames_limit),
            fixed_rpy=self.fixed_rpy,
            max_speed=self.arm_fraction_var.get() if hasattr(self, "arm_fraction_var") else 0.15,
            motion_mode="wrist_lock",
            wrist_tol_deg=max(0.1, min(15.0, self.wrist_tol_deg)),
            wrist_hard_j4_deg=self.wrist_hard_j4_deg,  # ★ 传递J4硬限
            wrist_hard_j5_deg=self.wrist_hard_j5_deg,  # ★ 传递J5硬限
            wrist_hard_j6_deg=self.wrist_hard_j6_deg,  # ★ 传递J6硬限
        )
        self.follower.begin()

        # 锁腕初始化必须成功
        if hasattr(self.follower, "_wrist_lock_ok") and not self.follower._wrist_lock_ok:
            self.eye_state_var.set("⚠️ 锁腕初始化失败（读不到关节角），禁止跟随")
            self.follower.stop()
            self.follower = None
            return
        self.following = True
        self.lost_counter = 0
        self.prev_P_base = None

        # ★ 自动启用末端碰撞盒（通过 C++ Socket 服务）
        self._start_collision_box_service()

        lock_w = ""
        try:
            if hasattr(self.follower, "_locked_wrist") and self.follower._locked_wrist:
                lock_w = "腕锁J4-6=[" + ",".join(
                    f"{math.degrees(v):.1f}°" for v in self.follower._locked_wrist) + "]"
        except Exception:
            pass

        self.eye_state_var.set(
            f"跟随中（限幅{self.max_step_m * 1000:.0f}mm/帧，丢手{self.lost_frames_limit}帧急停，"
            f"姿态锁[{self.fixed_rpy[0]:.2f},{self.fixed_rpy[1]:.2f},{self.fixed_rpy[2]:.2f}]，"
            f"{lock_w} 容差{self.wrist_tol_deg:.1f}°，硬限J4={self.wrist_hard_j4_deg:.0f}° "
            f"J5={self.wrist_hard_j5_deg:.0f}° J6={self.wrist_hard_j6_deg:.0f}°，"
            f"碰撞/停滞/锁腕不可达自动急停）")
        self.eye_status_var.set("状态: 等待手腕检测...")

    def _eye_stop_follow(self):
        self.following = False
        if self.follower is not None:
            self.follower.stop(emergency=True, reason="GUI 手动急停")
            self.follower = None
        elif self.arm is not None:
            try:
                self.arm.stop_move()
            except Exception:
                pass

        # ★ 移除碰撞盒 / 关闭 WorldZone
        self._remove_collision_box()
        self._disable_table_zone_if_enabled()

        self.eye_state_var.set("已急停停止")
        self.eye_status_var.set("状态: 已停止")

    # ================== 核心跟随逻辑 ==================
    def _eye_step(self, wrist_3d_cam):
        """把手腕相机系坐标交给 EyeInHandFollower（含全部安全链）。

        状态文本去重：同样的消息不重复写状态栏（避免每帧刷屏日志台）；
        跟随 HUD 帧率在 _refresh_follow3d 展示。
        """
        now = time.time()
        if self._last_eye_t:
            dt = now - self._last_eye_t
            if dt > 1e-3:
                self._eye_fps = 0.8 * self._eye_fps + 0.2 / dt
        self._last_eye_t = now
        if self.follower is not None and self.follower.running:
            ok, msg = self.follower.update(wrist_3d_cam)
            if msg != self._last_status_shown:
                self.eye_status_var.set("状态: " + msg)
                self._last_status_shown = msg
            if not ok and ("急停" in msg or "碰撞" in msg or "安全框" in msg):
                self.eye_state_var.set("⚠️ " + msg)
                self.following = False
        elif self.following and self.arm is not None:
            self._eye_step_fallback(wrist_3d_cam)

    def _eye_step_fallback(self, wrist_3d_cam):
        """旧逻辑兜底（仅在 follower 未创建时使用）。"""
        if wrist_3d_cam is None:
            self.lost_counter += 1
            if self.lost_counter >= self.lost_frames_limit:
                try:
                    self.arm.stop_move()
                except Exception:
                    pass
                self.eye_state_var.set(f"⚠️ 丢手 {self.lost_counter} 帧，急停！")
                self.following = False
            return
        self.lost_counter = 0
        try:
            P_base = self.hand_eye.camera_to_base(np.array(wrist_3d_cam), self.arm)
        except Exception as e:
            self.eye_status_var.set(f"坐标转换失败: {e}")
            return
        if self.prev_P_base is None:
            self.prev_P_base = P_base.copy()
            return
        delta = P_base - self.prev_P_base
        self.prev_P_base = P_base.copy()
        norm = np.linalg.norm(delta)
        if norm > self.max_step_m:
            delta = delta / norm * self.max_step_m
        try:
            current_pose = self.arm.get_flange_pose() if hasattr(self.arm, "get_flange_pose") \
                else self.arm.get_tcp_pose()
            if current_pose is None:
                return
        except Exception:
            return
        target_pos = np.array(current_pose[:3]) + delta
        if self.safety_box is not None:
            ok, msg = self.safety_box.check_pose(target_pos, margin=0.005)
            if not ok:
                self.eye_status_var.set(f"⚠️ 安全框: {msg}")
                try:
                    self.arm.stop_move()
                except Exception:
                    pass
                self.following = False
                self.eye_state_var.set("安全框越界急停")
                return
        target = [float(target_pos[0]), float(target_pos[1]), float(target_pos[2]),
                  self.fixed_rpy[0], self.fixed_rpy[1], self.fixed_rpy[2]]
        try:
            self.arm.movel(target, speed=0.1, acc=0.08, block=False, timeout_s=5)
        except Exception as e:
            self.eye_status_var.set(f"运动指令异常: {e}")
            try:
                self.arm.stop_move()
            except Exception:
                pass
            self.following = False
            self.eye_state_var.set("运动指令失败，已急停")

    # ================== 轮询与钩子 ==================
    def _eye_poll_loop(self):
        try:
            # 只读一次位姿，同时刷新两个标签（跟随期间高频 RPC 是画面卡顿主因）
            pose = self._read_pose_once()
            self._refresh_safety_live(pose)
            self._refresh_follow3d(pose)
            if self.following and self.arm is not None:
                pose = self.arm.get_tcp_pose()
                if pose is not None and len(pose) >= 6:
                    for i, lbl in enumerate(self.rpy_labels):
                        lbl.config(text=f"{math.degrees(pose[3 + i]):+7.1f}°")
            else:
                for lbl in self.rpy_labels:
                    lbl.config(text="---")
        except Exception:
            pass
        self.root.after(300, self._eye_poll_loop)

    def _holistic_step(self, rgb, depth, intrinsics):
        if not self.holistic_running or self.holistic is None:
            return None
        try:
            results = self.holistic.process(
                rgb, depth, intrinsics,
                map_to_arm=False,
                arm_mapper=None,
            )
        except Exception as exc:
            self.holistic_status_var.set(f"检测异常: {exc}")
            if self.following:
                self._eye_step(None)
            return None
        if not results:
            self.holistic_status_var.set("状态: 未检测到人体/手")
            if self.following:
                self._eye_step(None)
            return None
        r = results[0]
        parts = []
        if r.pose_detected:
            parts.append("人体✓")
        if r.hand_detected:
            parts.append("手✓")
        if r.wrist_3d is not None:
            self._last_wrist_3d = r.wrist_3d
            parts.append(f"腕3D=({r.wrist_3d[0]:.2f},{r.wrist_3d[1]:.2f},{r.wrist_3d[2]:.2f})")
        if r.arm_target_pose is not None:
            p = r.arm_target_pose
            parts.append(f"臂TCP=({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})")
        if r.hand_fist_confidence is not None:
            parts.append(f"握拳={r.hand_fist_confidence:.2f}")
        self.holistic_status_var.set("状态: " + " | ".join(parts))

        # ---- 灵巧手跟随（带异常熔断，见基类 _send_hand_joints） ----
        if self.holistic_hand_follow_var.get() and r.hand_detected and self.hand is not None:
            if not self.checkbox_vars["mimic_on"].get():
                angles_rad = [math.radians(a) for a in r.hand_angles_deg]
                self._send_hand_joints(angles_rad)

        # ---- 眼在手上跟随 ----
        if self.following:
            self._eye_step(r.wrist_3d if r is not None else None)

        return r

    def _poll_video(self):
        super()._poll_video()
        if not self.holistic_running or self.cam is None:
            return
        if not hasattr(self, '_holistic_counter'):
            self._holistic_counter = 0
        self._holistic_counter += 1
        if self._holistic_counter % 3 != 0:
            return
        try:
            rgb, depth, intrinsics = getattr(self, "_last_frame", (None, None, None))
            if rgb is None:
                return
            h, w = rgb.shape[:2]
            if h < 200 or w < 200:
                return
            self._holistic_step(rgb, depth, intrinsics)
        except Exception:
            pass

    def _on_close(self):
        self.following = False
        if self.follower is not None:
            try:
                self.follower.stop(emergency=True, reason="GUI 关闭")
            except Exception:
                pass
            self.follower = None
        if self.arm is not None:
            try:
                self.arm.stop_move()
            except Exception:
                pass

        # ★ 移除碰撞盒并停止 C++ 服务端 / 关闭 WorldZone
        self._remove_collision_box()
        self._stop_collision_box_service()
        self._disable_table_zone_if_enabled()

        super()._on_close()


def main():
    root = tk.Tk()
    root.geometry("1680x1050")
    root.minsize(1200, 800)
    MainGuiEye(root)
    root.mainloop()


if __name__ == "__main__":
    main()
