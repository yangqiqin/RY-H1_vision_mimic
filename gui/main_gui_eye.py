# -*- coding: utf-8 -*-
"""
main_gui_eye.py —— 眼在手上（eye-in-hand）协同总控制界面

在 gui/main_gui_holistic.py（灵巧手 + 机械臂 + Holistic 协同）基础上，实现
**眼在手上**完整闭环：相机固定在机械臂末端 → 识别手腕 → 手眼标定转换到基座系 →
驱动机械臂末端跟随（增量+安全框+失手急停）+ 手部手势驱动灵巧手。

继承链：MainGui → MainGuiArm → MainGuiHolistic → MainGuiEye

眼在手上控制面板（加入父类 arm_notebook 的第三页）：
  1. 手眼标定：查看/切换 R_cam2gripper/t_cam2gripper（复用 lib/grasp 标定值）；
  2. 初始化姿态：定义机械臂初始位（回初始位 / 记录当前为初始位）；
  3. 安全框：min_xyz / max_xyz 参数（GUI 可调），实时显示当前末端是否在框内；
  4. 跟随控制：【开始跟随】/【停止跟随（急停）】；
     手腕下移 → 机械臂末端下移（增量限幅 5mm/帧 + 姿态固定 + 安全框）；
  5. 安全红线：**连续丢手 N 帧 → 立即 stop_move 强制停止**；
  6. 实时状态：手腕基座坐标 / 增量 / 目标位姿 / 丢手计数 / 安全框判定；
  7. 末端姿态欧拉角（Rx/Ry/Rz）实时显示（确认末端姿态已固定）。

用法：
  python -m gui.main_gui_eye

安全提示（务必阅读 docs/眼在手上协同控制文档.md）：
  * 跟随会移动机械臂！首次速度比例 0.2、周围无人、急停可触及；
  * 开始跟随前必须：机械臂已连接上电、Holistic 已启动、安全框已设置合理；
  * 丢手自动急停是最后防线，不要依赖它代替人工注意。
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

import math
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from gui.main_gui_holistic import MainGuiHolistic
from vision.hand_eye import HandEyeCalibration, CALIB
from arm.arm_safety import ArmSafetyBox, DEFAULT_MIN_XYZ, DEFAULT_MAX_XYZ
from arm.arm_follow_eye import EyeInHandFollower


class MainGuiEye(MainGuiHolistic):
    """眼在手上协同总界面：灵巧手 + 机械臂 + Holistic + 手眼标定 + 安全框 + 跟随。"""

    def __init__(self, root: tk.Tk):
        # 先让父类构建所有原始界面（含 arm_notebook）
        super().__init__(root)
        # 眼在手上状态
        self.hand_eye: HandEyeCalibration = HandEyeCalibration()
        self.safety_box: ArmSafetyBox = ArmSafetyBox()
        self.follower: EyeInHandFollower | None = None
        self.eye_state_var = tk.StringVar(value="眼在手上未启动")
        self.rpy_labels = []                 # 末端姿态欧拉角显示标签
        self._build_eye_ui()
        self._eye_poll_loop()

    # ==================================================================
    # 眼在手上控制面板（arm_notebook 第三页）
    # ==================================================================
    def _build_eye_ui(self):
        # 加入父类创建的 Notebook 第三页（机械臂控制 tab0 / 协同控制 tab1）
        tab_eye = ttk.Frame(self.arm_notebook)
        self.arm_notebook.add(tab_eye, text="  眼在手上控制  ")
        tab_eye.grid_columnconfigure(0, weight=1)

        # ---- 行 1：手眼标定 ----
        r1 = ttk.LabelFrame(tab_eye, text="手眼标定（相机系→末端法兰系，来自 lib/grasp）")
        r1.pack(fill="x", padx=4, pady=2)
        ttk.Button(r1, text="查看标定参数", command=self._eye_show_calib).pack(side="left", padx=2)
        ttk.Button(r1, text="切换备用标定", command=self._eye_switch_calib).pack(side="left", padx=2)

        # ---- 行 2：初始化姿态 + 安全框 ----
        r2 = ttk.LabelFrame(tab_eye, text="初始化姿态 + 安全框")
        r2.pack(fill="x", padx=4, pady=2)

        sub_a = ttk.Frame(r2)
        sub_a.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_a, text="初始化姿态:").pack(side="left")
        ttk.Button(sub_a, text="回初始位", command=self._arm_home).pack(side="left", padx=2)
        ttk.Button(sub_a, text="记录当前为初始位", command=self._arm_set_home_current).pack(side="left", padx=2)

        sub_b = ttk.Frame(r2)
        sub_b.pack(fill="x", padx=2, pady=1)
        ttk.Label(sub_b, text="安全框 min(x,y,z):").pack(side="left")
        self.safe_min_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_MIN_XYZ[i]))
            self.safe_min_vars.append(var)
            ttk.Entry(sub_b, textvariable=var, width=6).pack(side="left", padx=1)
        ttk.Label(sub_b, text="max:").pack(side="left", padx=(8, 0))
        self.safe_max_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_MAX_XYZ[i]))
            self.safe_max_vars.append(var)
            ttk.Entry(sub_b, textvariable=var, width=6).pack(side="left", padx=1)
        ttk.Button(sub_b, text="应用安全框", command=self._eye_apply_safety).pack(side="left", padx=6)
        self.safety_state_var = tk.StringVar(value="（默认参考值，请按桌面高度调整）")
        ttk.Label(sub_b, textvariable=self.safety_state_var, foreground="gray",
                  font=("", 8)).pack(side="left", padx=6)

        # ---- 行 3：跟随控制 ----
        r3 = ttk.LabelFrame(tab_eye, text="眼在手上跟随控制（手腕下移→末端下移）")
        r3.pack(fill="x", padx=4, pady=2)

        sub_c = ttk.Frame(r3)
        sub_c.pack(fill="x", padx=2, pady=1)
        ttk.Button(sub_c, text="▶ 开始跟随", command=self._eye_start_follow).pack(side="left", padx=2)
        ttk.Button(sub_c, text="⏹ 停止跟随(急停)", command=self._eye_stop_follow).pack(side="left", padx=2)
        ttk.Label(sub_c, text="限幅mm/帧:").pack(side="left", padx=(14, 2))
        self.eye_step_var = tk.StringVar(value="5")
        ttk.Entry(sub_c, textvariable=self.eye_step_var, width=4).pack(side="left")
        ttk.Label(sub_c, text="丢手急停帧数:").pack(side="left", padx=(10, 2))
        self.eye_lost_var = tk.StringVar(value="5")
        ttk.Entry(sub_c, textvariable=self.eye_lost_var, width=4).pack(side="left")
        ttk.Label(sub_c, textvariable=self.eye_state_var, foreground="red").pack(side="left", padx=10)

        sub_d = ttk.Frame(r3)
        sub_d.pack(fill="x", padx=2, pady=1)
        self.eye_status_var = tk.StringVar(value="状态: -")
        ttk.Label(sub_d, textvariable=self.eye_status_var, font=("Consolas", 8),
                  foreground="blue", justify="left", wraplength=900).pack(side="left")

        # ---- 行 4：末端姿态欧拉角（RPY）实时显示 ----
        r4 = ttk.LabelFrame(tab_eye, text="末端姿态欧拉角（RPY，应保持固定）")
        r4.pack(fill="x", padx=4, pady=2)
        rpy_names = ["Rx", "Ry", "Rz"]
        for idx, name in enumerate(rpy_names):
            ttk.Label(r4, text=name + ":").grid(row=0, column=idx * 2, padx=5, pady=2, sticky="e")
            lbl = ttk.Label(r4, text="---", width=10, font=("Consolas", 10))
            lbl.grid(row=0, column=idx * 2 + 1, padx=5, pady=2, sticky="w")
            self.rpy_labels.append(lbl)

    # ==================================================================
    # 手眼标定
    # ==================================================================
    def _eye_show_calib(self):
        cal = self.hand_eye.get_calibration()
        R = cal["R_cam2gripper"]
        t = cal["t_cam2gripper"]
        msg = (
            "R_cam2gripper =\n" + "\n".join(
                "  [" + ", ".join(f"{v:.6f}" for v in row) + "]" for row in R) +
            f"\n\nt_cam2gripper = [{', '.join(f'{v:.6f}' for v in t)}]"
            "\n\n（来源：lib/grasp 项目标定结果，相机系→末端法兰系）"
        )
        messagebox.showinfo("手眼标定参数", msg)

    def _eye_switch_calib(self):
        """切换主/备用标定矩阵（grasp 两组，物理安装可能不同）。"""
        cur_t = self.hand_eye.get_calibration()["t_cam2gripper"]
        if np.allclose(cur_t, CALIB["t_cam2gripper"]):
            self.hand_eye.set_calibration(CALIB["R_cam2gripper_alt"], CALIB["t_cam2gripper_alt"])
            self.eye_state_var.set("已切换备用标定（alt）")
        else:
            self.hand_eye.set_calibration(CALIB["R_cam2gripper"], CALIB["t_cam2gripper"])
            self.eye_state_var.set("已切换默认标定")
        self._eye_show_calib()

    # ==================================================================
    # 安全框
    # ==================================================================
    def _eye_apply_safety(self):
        """应用安全框参数（min/max xyz）。"""
        try:
            self.safety_box.set_box(
                min_xyz=[float(v.get()) for v in self.safe_min_vars],
                max_xyz=[float(v.get()) for v in self.safe_max_vars],
            )
            self.safety_state_var.set("✓ 已应用: " + self.safety_box.describe())
            self.eye_state_var.set("安全框已应用")
        except ValueError:
            messagebox.showerror("输入错误", "安全框参数必须是数字")
            self.safety_state_var.set("✗ 参数格式错误（需数字）")

    # ==================================================================
    # 跟随控制
    # ==================================================================
    def _eye_start_follow(self):
        # 前置检查
        if not self.arm_connected or self.arm is None:
            messagebox.showwarning("提示", "请先连接机械臂")
            return
        if not self.holistic_running:
            messagebox.showwarning("提示", "请先启用 Holistic 检测（协同控制页）")
            return
        try:
            step_mm = float(self.eye_step_var.get()) / 1000.0
            lost = int(self.eye_lost_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "限幅/丢手参数必须是数字")
            return
        self.follower = EyeInHandFollower(
            arm=self.arm, hand_eye=self.hand_eye, safety_box=self.safety_box,
            max_step_m=max(0.001, step_mm), lost_frames=max(2, lost),
            fixed_rpy=[math.pi, 0.0, 0.0],
            max_speed=self.arm_fraction_var.get() if hasattr(self, "arm_fraction_var") else 0.2,
        )
        self.follower.begin()
        self.eye_state_var.set(
            f"跟随中（限幅{step_mm*1000:.0f}mm/帧，丢手{lost}帧急停）")
        self.eye_status_var.set("状态: 等待手腕检测...")

    def _eye_stop_follow(self):
        if self.follower is not None:
            self.follower.stop(emergency=True)
            self.follower = None
        self.eye_state_var.set("已急停停止")
        self.eye_status_var.set("状态: 已停止")

    # ==================================================================
    # 每帧：眼在手上处理
    # ==================================================================
    def _eye_step(self, wrist_3d_cam):
        """输入手腕相机系坐标（或 None=未检测到手），驱动机械臂跟随。"""
        if self.follower is None or not self.follower.running:
            return
        try:
            ok, msg = self.follower.update(wrist_3d_cam)
            self.eye_status_var.set("状态: " + msg)
            if not ok and "急停" in msg:
                self.eye_state_var.set("⚠️ " + msg)
        except Exception as exc:
            self.eye_status_var.set(f"状态: 跟随异常 {exc}")

    def _eye_poll_loop(self):
        """常驻调度：刷新眼在手上状态 + 末端 RPY 显示。"""
        try:
            if self.follower is not None and self.follower.running:
                st = self.follower.get_stats()
                txt = "状态: " + st["last_status"] + f" | 已移动 {st['moved_count']} 次"
                if st.get("last_delta"):
                    txt += f" | Δ={[round(x, 4) for x in st['last_delta']]}"
                if st.get("last_target"):
                    txt += f" | 目标={[round(x, 3) for x in st['last_target']]}"
                self.eye_status_var.set(txt)
            # 末端 RPY 实时显示（确认姿态固定）
            if self.arm_connected and self.arm is not None:
                pose = self.arm.get_tcp_pose()
                if pose is not None and len(pose) >= 6:
                    for i, lbl in enumerate(self.rpy_labels):
                        lbl.config(text=f"{math.degrees(pose[3+i]):+7.1f}°")
        except Exception:
            pass
        self.root.after(300, self._eye_poll_loop)

    # ==================================================================
    # 覆写 _holistic_step：把手腕 3D 传给眼在手上跟随（丢手→急停）
    # 注意：眼在手上模式下，holistic 的"机械臂跟随"会被自动禁用（防双重下发 movel）
    # ==================================================================
    def _holistic_step(self, rgb, depth, intrinsics):
        """
        覆写父类方法：完全由眼在手上模块控制，禁用父类的机械臂跟随。
        """
        if not self.holistic_running or self.holistic is None:
            return None

        try:
            # 直接调用 Holistic 检测，不启用臂映射（由 eye 跟随处理）
            results = self.holistic.process(
                rgb, depth, intrinsics,
                map_to_arm=False,  # 关键：禁用父类的臂跟随
                arm_mapper=None,
            )
        except Exception as exc:
            self.holistic_status_var.set(f"检测异常: {exc}")
            return None

        if not results:
            self.holistic_status_var.set("状态: 未检测到人体/手")
            return None

        r = results[0]

        # ---- 更新状态显示（与父类保持一致） ----
        parts = []
        if r.pose_detected:
            parts.append("人体✓")
        if r.hand_detected:
            parts.append("手✓")
        if r.wrist_3d is not None:
            parts.append(f"腕3D=({r.wrist_3d[0]:.2f},{r.wrist_3d[1]:.2f},{r.wrist_3d[2]:.2f})")
        if r.arm_target_pose is not None:
            p = r.arm_target_pose
            parts.append(f"臂TCP=({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})")
        if r.hand_fist_confidence is not None:
            parts.append(f"握拳={r.hand_fist_confidence:.2f}")
        self.holistic_status_var.set("状态: " + " | ".join(parts))

        # ---- 灵巧手跟随（若开启） ----
        if self.holistic_hand_follow_var.get() and r.hand_detected and self.hand is not None:
            if not self.checkbox_vars["mimic_on"].get():
                try:
                    angles_rad = [math.radians(a) for a in r.hand_angles_deg]
                    self.hand.move_joints(angles_rad)
                except Exception as exc:
                    self.holistic_status_var.set(f"手跟随异常: {exc}")

        # ---- 眼在手上跟随（丢手→急停） ----
        if self.follower is not None and self.follower.running:
            wrist = r.wrist_3d if r is not None else None
            self._eye_step(wrist)

        return r

    # ==================================================================
    # 关闭
    # ==================================================================
    def _on_close(self):
        if self.follower is not None:
            try:
                self.follower.stop(emergency=True)
            except Exception:
                pass
        super()._on_close()


def main():
    root = tk.Tk()
    root.geometry("1680x1050")
    root.minsize(1200, 800)
    MainGuiEye(root)
    root.mainloop()


if __name__ == "__main__":
    main()
