# -*- coding: utf-8 -*-
"""
main_gui_arm.py —— 综合控制界面（灵巧手 + Aubo K5 机械臂，TCP 坐标联动）

继承 MainGui，扩展机械臂控制，并重新布局视频/参数区。
主要改动：
  - 删除 16 个滑条行（保留按钮）
  - 视频区与参数区各占一半宽度
  - 16 关节角以 4 列网格显示，避免竖条
  - 参数区固定存在，无论相机是否启动
  - 机械臂 6 轴滑条范围根据 JOINT_RANGE_DEG 动态设置
"""

from __future__ import annotations

import os
import sys
import logging

# ---- 路径引导 ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import math
import tkinter as tk
from tkinter import ttk, messagebox

from gui.main_gui import MainGui, JOINT_NAMES_CN
from arm import AuboK5ArmController
from arm.arm_config import ARM_CONFIG, DOF, JOINT_RANGE_DEG, JOINT_STEP_DEG

logger = logging.getLogger("main_gui_arm")


class MainGuiArm(MainGui):
    def __init__(self, root: tk.Tk):
        # 1. 构建基类界面（相机、灵巧手、校准等）
        super().__init__(root)

        # 2. 删除 16 个滑条行（保留按钮）
        self._remove_joint_slider_rows()

        # 3. 重新布局视频与参数区（grid 列权重）
        self._reorganize_video_param_layout()

        # 4. 重写参数显示方法（将基类的 _update_video 替换为自定义版本）
        self._update_video = self._custom_update_video

        # 5. 机械臂相关状态
        self.arm: AuboK5ArmController | None = None
        self.arm_connected = False
        self.arm_state_var = tk.StringVar(value="机械臂未连接")
        self._pose_locked = False           # 姿态是否已锁定（movel 强制保持朝向）
        self._locked_rpy = [math.pi, 0.0, -0.436]   # 锁定姿态默认值（法兰 RPY）

        # 6. 创建机械臂面板（底部 Notebook）
        self._build_arm_ui()

        # 7. 初始化机械臂初始位显示
        self._arm_update_home_label()

        # 8. 启动机械臂状态轮询
        self._arm_poll_loop()

    # ==================================================================
    # 删除 16 个滑条行（但保留按钮行）
    # ==================================================================
    def _remove_joint_slider_rows(self):
        """查找包含 16 个滑条的容器，销毁所有包含 Scale 的子控件（每一行），保留按钮行。"""
        def find_slider_container(parent):
            for child in parent.winfo_children():
                if isinstance(child, ttk.LabelFrame) and "关节" in child.cget("text"):
                    return child
                res = find_slider_container(child)
                if res:
                    return res
            return None

        container = find_slider_container(self.root)
        if not container:
            return

        # 遍历子控件，销毁包含 Scale 的 Frame
        for child in container.winfo_children():
            if any(isinstance(c, tk.Scale) for c in child.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

    # ==================================================================
    # 重新布局视频与参数区（列权重调整）
    # ==================================================================
    def _reorganize_video_param_layout(self):
        """让视频和参数各占一半宽度，参数区不再狭小。"""
        root = self.root
        try:
            root.grid_columnconfigure(0, weight=2)  # 视频区
            root.grid_columnconfigure(1, weight=2)  # 参数区
        except Exception:
            pass
        # 确保 row1（视频/参数行）高度充足
        root.grid_rowconfigure(1, weight=4)

    # ==================================================================
    # 自定义参数显示（4 列网格）
    # ==================================================================
    def _custom_update_video(self):
        """
        重写基类的 _update_video，保留视频绘制（调用父类），
        但重新设置参数文本为 4 列网格。
        """
        # 1. 调用基类绘制视频（骨架等）
        try:
            super()._update_video()
        except Exception:
            pass

        # 2. 获取当前检测数据
        est = getattr(self, 'est', None)
        angles_deg = getattr(est, 'angles_deg', None) if est else None
        hand_lr = getattr(est, 'hand_lr', '右') if est else '右'
        fist_conf = getattr(est, 'fist_confidence', 0.0) if est else 0.0

        # 3. 构建显示文本
        lines = [f"手: {hand_lr}  握拳置信度: {fist_conf:.2f}"]

        if angles_deg is not None and len(angles_deg) == 16:
            # 4 列显示
            for row in range(4):
                row_str = ""
                for col in range(4):
                    idx = row * 4 + col
                    if idx < 16:
                        name = JOINT_NAMES_CN[idx] if idx < len(JOINT_NAMES_CN) else f"J{idx+1}"
                        val = angles_deg[idx]
                        row_str += f"{name}:{val:5.1f}°  "
                lines.append(row_str)
        else:
            lines.append("未识别到手")

        # 4. 查找参数标签并更新
        if hasattr(self, 'param_label') and self.param_label is not None:
            self.param_label.config(text="\n".join(lines))
        else:
            for child in self.root.winfo_children():
                if isinstance(child, ttk.Label) and "手:" in child.cget("text"):
                    child.config(text="\n".join(lines))
                    break

    # ==================================================================
    # 机械臂面板 UI（底部 Notebook，多标签页）
    # ==================================================================
    def _build_arm_ui(self):
        root = self.root
        try:
            root.geometry("1680x1080")
        except Exception:
            pass

        self.arm_notebook = ttk.Notebook(root)
        self.arm_notebook.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=2)

        tab_arm = ttk.Frame(self.arm_notebook)
        self.arm_notebook.add(tab_arm, text="  机械臂控制  ")
        self._build_arm_tab(tab_arm)

    def _build_arm_tab(self, parent: ttk.Frame):
        """机械臂控制标签页：多列布局，功能完整。"""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_columnconfigure(2, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # ---- 左列：连接 + 电源 + 状态 ----
        left = ttk.LabelFrame(parent, text="连接与电源")
        left.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)

        r1 = ttk.Frame(left)
        r1.pack(fill="x", padx=4, pady=2)
        ttk.Label(r1, text="IP:").pack(side="left")
        self.arm_ip_var = tk.StringVar(value=ARM_CONFIG["ip"])
        ttk.Entry(r1, textvariable=self.arm_ip_var, width=14).pack(side="left", padx=2)
        ttk.Label(r1, text="端口:").pack(side="left")
        self.arm_port_var = tk.StringVar(value=str(ARM_CONFIG["rpc_port"]))
        ttk.Entry(r1, textvariable=self.arm_port_var, width=6).pack(side="left", padx=2)
        ttk.Button(r1, text="连接", command=self._arm_connect).pack(side="left", padx=2)
        ttk.Button(r1, text="断开", command=self._arm_disconnect).pack(side="left", padx=2)

        r1b = ttk.Frame(left)
        r1b.pack(fill="x", padx=4, pady=2)
        ttk.Label(r1b, text="速度比例:").pack(side="left")
        self.arm_fraction_var = tk.DoubleVar(value=ARM_CONFIG["speed_fraction"])
        tk.Scale(r1b, from_=0.05, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                 variable=self.arm_fraction_var, length=220, showvalue=True,
                 command=lambda _v: self._arm_apply_fraction()).pack(side="left")
        ttk.Label(r1b, textvariable=self.arm_state_var, foreground="blue").pack(side="left", padx=8)

        r2 = ttk.Frame(left)
        r2.pack(fill="x", padx=4, pady=2)
        ttk.Button(r2, text="上电+启动", command=self._arm_poweron).pack(side="left", padx=2)
        ttk.Button(r2, text="断电", command=self._arm_poweroff).pack(side="left", padx=2)
        ttk.Button(r2, text="停止", command=self._arm_stop).pack(side="left", padx=2)
        ttk.Button(r2, text="拖拽示教开", command=lambda: self._arm_freedrive(True)).pack(side="left", padx=2)
        ttk.Button(r2, text="拖拽示教关", command=lambda: self._arm_freedrive(False)).pack(side="left", padx=2)

        # 初始位区（可调）
        r2b = ttk.Frame(left)
        r2b.pack(fill="x", padx=4, pady=2)
        ttk.Label(r2b, text="初始位(度):").pack(side="left")
        self.arm_home_label = tk.StringVar(value="0, -15, 100, 25, 90, 0")
        ttk.Label(r2b, textvariable=self.arm_home_label, font=("Consolas", 8)).pack(side="left", padx=2)
        ttk.Button(r2b, text="记录当前为初始位", command=self._arm_set_home_current).pack(side="left", padx=2)
        ttk.Button(r2b, text="回初始位", command=self._arm_home).pack(side="left", padx=2)

        # 状态显示（多行）
        self.arm_status_var = tk.StringVar(value="状态: -")
        ttk.Label(left, textvariable=self.arm_status_var, font=("Consolas", 8),
                  foreground="green", justify="left", wraplength=560).pack(
            fill="x", padx=4, pady=2)

        # ---- 中列：6 轴手动操控（滑条 + 微调） ----
        mid = ttk.LabelFrame(parent, text="手动操控（关节角，度）")
        mid.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)

        self.arm_joint_vars = []
        header = ttk.Frame(mid)
        header.pack(fill="x", padx=2)
        ttk.Label(header, text="轴", width=3).pack(side="left")
        ttk.Label(header, text="关节名", width=12).pack(side="left")
        ttk.Label(header, text="角度(°)", width=8).pack(side="left")
        ttk.Label(header, text="滑条", width=16).pack(side="left")
        ttk.Label(header, text="微调", width=14).pack(side="left")
        for i in range(DOF):
            row = ttk.Frame(mid)
            row.pack(fill="x", padx=2, pady=1)
            ttk.Label(row, text=f"J{i+1}", width=3).pack(side="left")
            ttk.Label(row, text=JOINT_NAMES_CN[i], width=12, font=("", 8)).pack(side="left")
            var = tk.DoubleVar(value=0.0)
            self.arm_joint_vars.append(var)
            ttk.Label(row, textvariable=var, width=8, font=("Consolas", 8)).pack(side="left")

            lo, hi = JOINT_RANGE_DEG[i]
            tk.Scale(row, from_=lo, to=hi, resolution=1, orient=tk.HORIZONTAL,
                     variable=var, length=180, showvalue=False).pack(side="left", padx=2)

            bf = ttk.Frame(row)
            bf.pack(side="left")
            ttk.Button(bf, text="-", width=2,
                       command=lambda idx=i: self._arm_joint_nudge(idx, -1)).pack(side="left")
            ttk.Button(bf, text="+", width=2,
                       command=lambda idx=i: self._arm_joint_nudge(idx, +1)).pack(side="left")

        btns = ttk.Frame(mid)
        btns.pack(fill="x", padx=2, pady=3)
        ttk.Button(btns, text="执行 movej（全部轴）", command=self._arm_movej_from_sliders).pack(side="left", padx=3)
        ttk.Button(btns, text="读取当前关节角", command=self._arm_read_joints).pack(side="left", padx=3)
        ttk.Button(btns, text="回初始位", command=self._arm_home).pack(side="left", padx=3)

        # ---- 右列：位姿 movel + TCP 联动 + 臂手联动 ----
        right = ttk.LabelFrame(parent, text="位姿运动（movel，TCP 系）与联动")
        right.grid(row=0, column=2, sticky="nsew", padx=4, pady=2)

        rp = ttk.Frame(right)
        rp.pack(fill="x", padx=4, pady=2)
        ttk.Label(rp, text="位姿 [x,y,z,rx,ry,rz] (m/rad):").pack(anchor="w")
        self.arm_pose_vars = []
        for i in range(6):
            var = tk.StringVar(value="0.0")
            self.arm_pose_vars.append(var)
            ttk.Entry(rp, textvariable=var, width=8).pack(side="left", padx=1)

        rpb = ttk.Frame(right)
        rpb.pack(fill="x", padx=4, pady=2)
        ttk.Button(rpb, text="执行 movel", command=self._arm_movel_from_entry).pack(side="left", padx=2)
        ttk.Button(rpb, text="读当前位姿填充", command=self._arm_read_pose_fill).pack(side="left", padx=2)

        # ★★★ 新增：锁定当前姿态按钮 ★★★
        lock_btn = tk.Button(
            rpb,
            text="锁定当前姿态",
            command=self._arm_lock_current_pose,
            bg="lightgreen",
            fg="black",
            font=("", 9, "bold")
        )
        lock_btn.pack(side="left", padx=4)
        unlock_btn = tk.Button(
            rpb, text="解除锁定", command=self._arm_unlock_pose,
            bg="lightcoral", fg="black", font=("", 9, "bold")
        )
        unlock_btn.pack(side="left", padx=2)

        # 位置微调（x/y/z 与姿态 ±）
        rpc = ttk.Frame(right)
        rpc.pack(fill="x", padx=4, pady=2)
        ttk.Label(rpc, text="微调:").pack(side="left")
        self._add_pose_nudge(rpc, 0, "X-", "X+", is_pos=True)
        self._add_pose_nudge(rpc, 1, "Y-", "Y+", is_pos=True)
        self._add_pose_nudge(rpc, 2, "Z-", "Z+", is_pos=True)
        ttk.Frame(rpc, width=6).pack(side="left")
        self._add_pose_nudge(rpc, 3, "Rx-", "Rx+", is_pos=False)
        self._add_pose_nudge(rpc, 4, "Ry-", "Ry+", is_pos=False)
        self._add_pose_nudge(rpc, 5, "Rz-", "Rz+", is_pos=False)

        rl = ttk.Frame(right)
        rl.pack(fill="x", padx=4, pady=2)
        self.arm_link_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(rl, text="TCP联动(灵巧手安装偏移)",
                        variable=self.arm_link_var,
                        command=self._arm_toggle_link).pack(side="left")

        rh = ttk.Frame(right)
        rh.pack(fill="x", padx=4, pady=2)
        ttk.Label(rh, text="臂手联动:").pack(side="left")
        ttk.Button(rh, text="到位后握拳", command=self._arm_hand_link_fist).pack(side="left", padx=2)
        ttk.Button(rh, text="到位后张开", command=self._arm_hand_link_open).pack(side="left", padx=2)
        ttk.Button(rh, text="到位后放松", command=self._arm_hand_link_relax).pack(side="left", padx=2)

        # ============================================================
        # ★★★ 末端安全碰撞盒（SDK 级保护：防相机/灵巧手剐蹭）★★★
        # 依据 lib/auboDocument/index-碰撞.pdf：
        #   addCollisionBox(name, "end_effector", [[长,宽,高]], [[x,y,z,rx,ry,rz]])
        #   → 在末端挂一个随动的长方体，机械臂其它连杆/环境进入 → SDK 碰撞保护
        # ============================================================
        rt = ttk.LabelFrame(right, text="末端安全碰撞盒（保护相机+灵巧手，单位 cm）")
        rt.pack(fill="x", padx=4, pady=2)
        sub_t1 = ttk.Frame(rt)
        sub_t1.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_t1, text="长×宽×高(cm):").pack(side="left")
        self.tool_box_size_vars = []
        # 默认：相机(~8cm) + 灵巧手(~15cm) + 手指摆动空间，稍放大留余量
        for default_cm in (20, 16, 25):
            var = tk.StringVar(value=str(default_cm))
            self.tool_box_size_vars.append(var)
            ttk.Entry(sub_t1, textvariable=var, width=5).pack(side="left", padx=1)
        ttk.Label(sub_t1, text=" 相对末端 z(cm):").pack(side="left", padx=(8, 0))
        self.tool_box_z_var = tk.StringVar(value="10")
        ttk.Entry(sub_t1, textvariable=self.tool_box_z_var, width=5).pack(side="left", padx=1)
        ttk.Button(sub_t1, text="启用碰撞盒", command=self._arm_enable_tool_box).pack(side="left", padx=4)
        ttk.Button(sub_t1, text="停用", command=self._arm_disable_tool_box).pack(side="left", padx=2)

    def _arm_enable_tool_box(self):
        """启用末端碰撞盒（addCollisionBox on end_effector，SDK 级防剐蹭）。"""
        if not self._require_arm():
            return
        try:
            size_cm = [float(v.get()) for v in self.tool_box_size_vars]
            z_cm = float(self.tool_box_z_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "尺寸必须是数字（厘米）")
            return
        size_m = [v / 100.0 for v in size_cm]
        z_m = z_cm / 100.0
        # 相对 end_effector 的位姿：盒子中心在末端前方 z_m 处
        pose = [0.0, 0.0, z_m, 0.0, 0.0, 0.0]

        # ★ 优先走 C++ Socket 服务（Python pyaubo-sdk 无法调用 addCollisionBox → 32601，
        #   由 C++ 服务端直连遨博 C++ SDK 调用）
        try:
            from arm.collision_box_client import (
                start_cpp_collision_server, get_collision_client)
            rob_ip = getattr(self.arm, "ip", None) if self.arm is not None else None
            if start_cpp_collision_server(timeout=2.0, robot_ip=rob_ip):
                resp = get_collision_client().add_collision_box(
                    "tool_box", "end_effector", size_m, pose)
                if resp.get("status") == "ok":
                    mode = resp.get("mode", "sdk")
                    if mode == "sdk":
                        self.arm_state_var.set(
                            f"✅ 末端碰撞盒已启用(C++ SDK): {size_cm[0]:.0f}×{size_cm[1]:.0f}"
                            f"×{size_cm[2]:.0f}cm (z+{z_cm:.0f}cm)")
                    else:
                        # addCollisionBox 固件不支持(32601，C++ 同 RPC 也一样) →
                        # 尝试真实硬件级替代：WorldZone 桌面危险腔
                        try:
                            if hasattr(self.arm, "enable_table_protect_zone"):
                                wret, wnote = self.arm.enable_table_protect_zone(floor_z=0.13)
                                if wret == 0:
                                    self.arm_state_var.set(
                                        f"（addCollisionBox 固件不支持 → ✅ {wnote}）")
                                else:
                                    self.arm_state_var.set(
                                        f"（碰撞盒固件不支持，WorldZone 失败：{wnote} "
                                        f"→ 软件安全链兜底）")
                            else:
                                self.arm_state_var.set(
                                    "（碰撞盒固件不支持且无 WorldZone 接口 → 软件安全链兜底）")
                        except Exception as wexc:
                            self.arm_state_var.set(f"（WorldZone 异常: {wexc} → 软件链兜底）")
                    return
        except Exception as e:
            print(f"Socket 碰撞盒失败，回退 Python SDK: {e}")

        ret = self.arm.add_tool_collision_box("tool_box", size_m, pose)
        if ret == 0:
            self.arm_state_var.set(
                f"✅ 末端碰撞盒已启用: {size_cm[0]:.0f}×{size_cm[1]:.0f}×{size_cm[2]:.0f}cm "
                f"(z+{z_cm:.0f}cm)，机械臂/环境进入即碰撞保护")
        else:
            # 读取具体错误（含异常详情）
            detail = f"addCollisionBox ret={ret}"
            if hasattr(self.arm, "get_last_collision_error"):
                err = self.arm.get_last_collision_error()
                if err:
                    detail = err
            # 若固件不支持 addCollisionBox(32601 method not found)，尝试 WorldZone 兜底
            fallback_note = ""
            if "32601" in detail or "method not found" in detail.lower():
                try:
                    # 用 WorldZone 保护基座前方工作区（桌面），software 层兜底
                    wret = self.arm.set_world_zone(
                        base_vertex=[0.0, -0.45, 0.0],
                        opposite_vertex=[1.0, 0.45, 0.20],
                        enabled=True, outside=True,
                        margin=0.01, tool_radius=0.05, brake_margin=0.02)
                    if wret == 0:
                        fallback_note = "\n\n已自动改用 WorldZone 保护工作台区域（防碰桌面）。\n" \
                                        "（本固件不支持末端随动碰撞盒 addCollisionBox）"
                        self.arm_state_var.set("WorldZone 桌面保护已启用（addCollisionBox 固件不支持）")
                except Exception as w_exc:
                    fallback_note = f"\n\nWorldZone 也失败: {w_exc}"
            messagebox.showerror(
                "启用失败",
                f"{detail}{fallback_note}\n\n"
                f"提示：\n"
                f"· 机械臂未进入 Running（先点【上电+启动】）\n"
                f"· 拖拽示教还开着（先关【拖拽示教】）\n"
                f"· 部分固件不支持 addCollisionBox（32601），已尝试 WorldZone 兜底")

    def _arm_disable_tool_box(self):
        """停用末端碰撞盒/WorldZone（优先走 C++ Socket 服务）。"""
        if not self._require_arm():
            return
        # ★ 优先走 C++ Socket 移除
        try:
            from arm.collision_box_client import get_collision_client
            resp = get_collision_client().remove_collision_box("tool_box")
            if resp.get("status") == "ok":
                self.arm_state_var.set(f"末端碰撞盒已停用(ret=0, mode={resp.get('mode')})")
                # 同时关闭可能启用的 WorldZone
                try:
                    if hasattr(self.arm, "disable_world_zone"):
                        self.arm.disable_world_zone()
                except Exception:
                    pass
                return
        except Exception:
            pass
        ret = self.arm.remove_tool_collision_box("tool_box")
        try:
            if hasattr(self.arm, "disable_world_zone"):
                self.arm.disable_world_zone()
        except Exception:
            pass
        self.arm_state_var.set(f"末端碰撞盒/WorldZone 已停用 ret={ret}")

    def _add_pose_nudge(self, parent, idx: int, minus_text: str, plus_text: str, is_pos: bool):
        """位姿微调按钮（位置步长 1cm / 姿态步长 0.05rad）。"""
        from arm.arm_config import POS_STEP_M, POS_STEP_RAD
        step = POS_STEP_M if is_pos else POS_STEP_RAD
        bf = ttk.Frame(parent)
        bf.pack(side="left", padx=1)
        ttk.Button(bf, text=minus_text, width=3,
                   command=lambda: self._arm_pose_nudge(idx, -step)).pack(side="left")
        ttk.Button(bf, text=plus_text, width=3,
                   command=lambda: self._arm_pose_nudge(idx, +step)).pack(side="left")

    # ==================================================================
    # 机械臂操作（连接/电源/运动/状态等）
    # ==================================================================
    def _require_arm(self) -> bool:
        if self.arm is None or not self.arm_connected:
            messagebox.showwarning("提示", "请先连接机械臂")
            return False
        return True

    def _arm_connect(self):
        if self.arm is not None:
            self._arm_disconnect()
        ip = self.arm_ip_var.get().strip() or ARM_CONFIG["ip"]
        try:
            port = int(self.arm_port_var.get().strip() or ARM_CONFIG["rpc_port"])
        except ValueError:
            port = ARM_CONFIG["rpc_port"]
        try:
            self.arm = AuboK5ArmController(ip=ip, rpc_port=port,
                                           speed_fraction=self.arm_fraction_var.get())
            if not self.arm.open():
                self.arm = None
                messagebox.showerror("机械臂连接失败", "连接/登录失败，检查 IP、网络、控制柜开机、账号密码")
                return
            self.arm_connected = True
            self.arm_state_var.set(f"已连接({ip})")
            self._arm_refresh_state()
        except Exception as exc:
            self.arm = None
            messagebox.showerror("机械臂连接失败", str(exc))

    def _arm_disconnect(self):
        if self.arm is not None:
            try:
                self.arm.close()
            except Exception:
                pass
        self.arm = None
        self.arm_connected = False
        self.arm_state_var.set("机械臂未连接")
        self.arm_status_var.set("状态: -")

    def _arm_apply_fraction(self):
        if self.arm_connected and self.arm is not None:
            try:
                self.arm.set_speed_fraction(self.arm_fraction_var.get())
            except Exception as exc:
                print(f"[WARN] set speed fraction: {exc}")

    def _arm_poweron(self):
        if not self._require_arm():
            return
        if not messagebox.askyesno("上电+启动", "确定对机械臂上电并松刹车？"):
            return
        try:
            ok = self.arm.poweron_and_startup(wait_running=True, timeout_s=15)
            self.arm_state_var.set("上电+启动成功(Running)" if ok else "上电/启动未达 Running")
        except Exception as exc:
            messagebox.showerror("上电失败", str(exc))

    def _arm_poweroff(self):
        if not self._require_arm():
            return
        if not messagebox.askyesno("断电", "确定对机械臂断电？"):
            return
        try:
            self.arm.poweroff()
            self.arm_state_var.set("已请求断电")
        except Exception as exc:
            messagebox.showerror("断电失败", str(exc))

    def _arm_stop(self):
        if not self._require_arm():
            return
        self.arm.stop_move()
        self.arm_state_var.set("已发送停止")

    def _arm_freedrive(self, enable: bool):
        if not self._require_arm():
            return
        try:
            self.arm.freedrive(enable)
            self.arm_state_var.set("拖拽示教: 开" if enable else "拖拽示教: 关")
        except Exception as exc:
            messagebox.showerror("示教失败", str(exc))

    def _arm_home(self):
        if not self._require_arm():
            return
        if not messagebox.askyesno("回初始位", "机械臂将回到初始关节角，确认？"):
            return
        ret, msg = self.arm.move_home(block=True)
        self.arm_state_var.set(f"回初始位 ret={ret} {msg or ''}")

    def _arm_lock_current_pose(self):
        """
        把当前【法兰】姿态锁定为协同跟随的固定姿态。
        读取机械臂当前位姿中的 [rx, ry, rz] 存入 self._locked_rpy 并置 _pose_locked=True，
        后续所有 movel 入口（_arm_movel_from_entry / _arm_hand_link）会强制替换姿态为锁定值，
        保证末端朝向（相机+灵巧手）始终不变。
        """
        if not self._require_arm():
            return

        # 用法兰位姿（不含 TCP 偏移，与手眼标定/安全检测一致）
        if hasattr(self.arm, "get_flange_pose"):
            pose = self.arm.get_flange_pose()
        else:
            pose = self.arm.get_tcp_pose()
        if pose is None:
            messagebox.showerror("读取失败", "无法获取当前位姿，请检查机械臂连接")
            return

        # 提取姿态部分 [rx, ry, rz] 并保存锁定状态
        locked_rpy = pose[3:6]
        self._locked_rpy = [float(v) for v in locked_rpy]
        self._pose_locked = True

        # 同步给 ArmFollower（若已启用协同）
        if hasattr(self, 'follower') and self.follower is not None:
            try:
                self.follower.update_calib(fixed_rpy=locked_rpy)
            except Exception:
                pass

        self.arm_state_var.set(
            f"✅ 姿态已锁定: [{self._locked_rpy[0]:.3f}, {self._locked_rpy[1]:.3f}, "
            f"{self._locked_rpy[2]:.3f}] rad（后续 movel 保持该朝向）"
        )
        logger.info("[arm] 锁定姿态: %s", [round(v, 4) for v in self._locked_rpy])

    def _arm_unlock_pose(self):
        """解除姿态锁定（movel 恢复使用输入框的姿态）。"""
        self._pose_locked = False
        self.arm_state_var.set("姿态锁定已解除（movel 用输入框姿态）")

    def _apply_locked_rpy(self, pose: list) -> list:
        """若已锁定姿态，把 pose 的旋转部分替换为锁定值（只移动 xyz）。"""
        if getattr(self, "_pose_locked", False) and hasattr(self, "_locked_rpy"):
            return list(pose[:3]) + list(self._locked_rpy)
        return list(pose)

    def _arm_movej_from_sliders(self):
        if not self._require_arm():
            return
        q = [math.radians(v.get()) for v in self.arm_joint_vars]
        ret, msg = self.arm.movej(q, block=True, timeout_s=30)
        self.arm_state_var.set(f"movej ret={ret} {msg or ''}")
        self._arm_refresh_state()

    def _arm_joint_nudge(self, idx: int, direction: int):
        if not self._require_arm():
            return
        cur = self.arm_joint_vars[idx].get()
        new = cur + direction * JOINT_STEP_DEG
        lo, hi = JOINT_RANGE_DEG[idx]
        new = max(lo, min(hi, new))
        self.arm_joint_vars[idx].set(round(new, 1))

    def _arm_read_joints(self):
        if not self._require_arm():
            return
        q = self.arm.get_joint_positions()
        if q is None:
            self.arm_state_var.set("读取关节角失败")
            return
        for i in range(DOF):
            self.arm_joint_vars[i].set(round(math.degrees(q[i]), 1))
        self.arm_state_var.set("已读取当前关节角并填充滑条")

    def _arm_read_pose_fill(self):
        if not self._require_arm():
            return
        pose = self.arm.get_tcp_pose()
        if pose is None:
            self.arm_state_var.set("读取位姿失败")
            return
        for i in range(6):
            self.arm_pose_vars[i].set(f"{pose[i]:.4f}")
        self.arm_state_var.set("已读取当前位姿并填充")

    def _arm_pose_nudge(self, idx: int, delta: float):
        if not self._require_arm():
            return
        try:
            vals = [float(v.get()) for v in self.arm_pose_vars]
        except ValueError:
            messagebox.showerror("输入错误", "位姿必须是数字")
            return
        vals[idx] = round(vals[idx] + delta, 4)
        for i in range(6):
            self.arm_pose_vars[i].set(f"{vals[i]:.4f}")
        ret, msg = self.arm.movel(vals, block=False, timeout_s=10)
        self.arm_state_var.set(f"movel 微调 ret={ret} {msg or ''}")

    def _arm_set_home_current(self):
        if not self._require_arm():
            return
        q = self.arm.get_joint_positions()
        if q is None:
            messagebox.showerror("失败", "读取当前关节角失败")
            return
        deg = [math.degrees(v) for v in q]
        self.arm.set_home(deg)
        self._arm_update_home_label()
        self.arm_state_var.set("已记录当前为初始位")

    def _arm_update_home_label(self):
        try:
            home = self.arm.get_home() if (self.arm is not None) else None
        except Exception:
            home = None
        from arm.arm_config import HOME_JOINT_DEG
        if home is None:
            home = HOME_JOINT_DEG
        self.arm_home_label.set(", ".join(f"{v:g}" for v in home))

    def _arm_movel_from_entry(self):
        if not self._require_arm():
            return
        try:
            pose = [float(v.get()) for v in self.arm_pose_vars]
        except ValueError:
            messagebox.showerror("输入错误", "位姿必须是数字 [x,y,z,rx,ry,rz]")
            return
        # 若已锁定姿态 → 强制替换旋转部分（末端朝向不变，只移动 xyz）
        pose = self._apply_locked_rpy(pose)
        ret, msg = self.arm.movel(pose, block=True, timeout_s=30)
        self.arm_state_var.set(f"movel ret={ret} {msg or ''}")
        self._arm_refresh_state()

    def _arm_toggle_link(self):
        if not self.arm_connected or self.arm is None:
            self.arm_link_var.set(False)
            messagebox.showwarning("提示", "请先连接机械臂")
            return
        try:
            if self.arm_link_var.get():
                off = self.arm.get_hand_mount_offset()
                if off is None:
                    off = ARM_CONFIG["hand_mount_offset"]
                self.arm.apply_tcp_offset(off)
                self.arm_state_var.set("TCP 联动已开启（位姿=灵巧手 TCP）")
            else:
                self.arm.apply_tcp_offset([0.0] * 6)
                self.arm_state_var.set("TCP 联动已关闭（位姿=法兰 TCP）")
        except Exception as exc:
            messagebox.showerror("TCP 联动失败", str(exc))

    def _arm_hand_link(self, hand_action: str):
        if not self._require_arm():
            return
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接灵巧手")
            return
        try:
            pose = [float(v.get()) for v in self.arm_pose_vars]
        except ValueError:
            messagebox.showerror("输入错误", "位姿必须是数字")
            return
        pose = self._apply_locked_rpy(pose)   # 若姿态已锁定则强制替换旋转部分
        if not messagebox.askyesno("臂手联动", f"机械臂 movel 到位后执行『{hand_action}』，确认？"):
            return
        ret, msg = self.arm.movel(pose, block=True, timeout_s=30)
        if ret != 0:
            messagebox.showerror("机械臂运动失败", f"movel ret={ret} {msg}")
            return
        try:
            if hand_action == "握拳":
                self.hand.close_hand()
            elif hand_action == "张开":
                self.hand.open_hand()
            else:
                self.hand.relax()
            self.arm_state_var.set(f"臂手联动完成（到位+{hand_action}）")
        except Exception as exc:
            messagebox.showerror("灵巧手动作失败", str(exc))

    def _arm_hand_link_fist(self):
        self._arm_hand_link("握拳")

    def _arm_hand_link_open(self):
        self._arm_hand_link("张开")

    def _arm_hand_link_relax(self):
        self._arm_hand_link("放松")

    # ==================================================================
    # 状态轮询
    # ==================================================================
    def _arm_refresh_state(self):
        if not self.arm_connected or self.arm is None:
            return
        try:
            s = self.arm.get_state_summary()
            q = s.get("joint_positions_rad")
            pose = s.get("tcp_pose")
            parts = [f"模式:{s['robot_mode']}", f"安全:{s['safety_mode']}"]
            if s.get("steady") is not None:
                parts.append("停止" if s["steady"] else "运动中")
            if q:
                deg = " ".join(f"{math.degrees(v):+5.1f}" for v in q)
                parts.append(f"J(deg): {deg}")
            if pose:
                parts.append(f"TCP: {', '.join(f'{v:.3f}' for v in pose)}")
            self.arm_status_var.set(" | ".join(parts))
        except Exception as exc:
            self.arm_status_var.set(f"状态读取失败: {exc}")

    def _arm_poll_loop(self):
        try:
            if self.arm_connected and self.arm is not None:
                self._arm_refresh_state()
        except Exception:
            pass
        self.root.after(800, self._arm_poll_loop)

    # ==================================================================
    # 关闭：先断开机械臂，再走原灵巧手关闭流程
    # ==================================================================
    def _on_close(self):
        try:
            if self.arm is not None:
                self.arm.close()
        except Exception:
            pass
        self.arm = None
        super()._on_close()


def main():
    root = tk.Tk()
    app = MainGuiArm(root)
    root.mainloop()


if __name__ == "__main__":
    main()