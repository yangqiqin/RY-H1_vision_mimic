# -*- coding: utf-8 -*-
"""
main_gui_holistic.py —— 协同总控制界面（L515 + Holistic 全身姿态 → 灵巧手 + 机械臂）

在原 gui/main_gui_arm.py（臂+手扩展版）基础上**再叠加** Holistic 协同控制面板，
继承链：MainGui（灵巧手）→ MainGuiArm（+机械臂）→ MainGuiHolistic（+协同控制）。

功能：
  1. 完整保留：相机(USB/L515)、灵巧手控制/校准/动作模仿、机械臂控制/TCP联动/臂手联动；
  2. 新增"协同控制（Holistic）"面板：
       - 启动/停止 holistic 检测（L515 RGB+深度 → 人体+手部关键点）
       - 手部 21 点 → 16 关节角 → 灵巧手跟随（可选）
       - 人体腕部 3D → 机械臂 TCP（ArmFollower 映射）→ 机械臂跟随（可选）
       - 骨架显示（人体 33 点 + 手部 21 点）
       - 实时显示：腕部 3D / 臂 TCP 目标 / 16 关节角 / 握拳置信度
       - 映射标定参数：offset / scale / add（可调，保存到 calibration.json）
  3. 安全：协同使能需显式勾选；机械臂跟随默认关闭；速度比例滑条共用。

用法：
  python -m gui.main_gui_holistic

安全提示：
  * 协同控制会移动机械臂！先手动验证映射（apps/test_holistic.py --selfcheck），
    再小速度（0.2~0.3）试跑，随时可点【停止】或按急停。
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
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
import numpy as np

from gui.main_gui_arm import MainGuiArm
from vision.holistic_pose import HolisticPoseEstimator
from arm.arm_follow import ArmFollower, DEFAULT_CALIB


class MainGuiHolistic(MainGuiArm):
    """协同总控制界面：灵巧手 + 机械臂 + Holistic 全身姿态协同。"""

    def __init__(self, root: tk.Tk):
        super().__init__(root)          # MainGuiArm → MainGui 全部界面
        # Holistic 状态
        self.holistic: HolisticPoseEstimator | None = None
        self.follower: ArmFollower = ArmFollower()
        self.holistic_running = False
        self.holistic_state_var = tk.StringVar(value="协同未启动")
        self._last_wrist_3d = None           # 最近一帧腕部 3D（标定辅助）
        self._build_holistic_ui()
        self._holistic_poll_loop()

    # ==================================================================
    # 协同控制面板（加入机械臂 Notebook 的第二个标签页）
    # ==================================================================
    def _build_holistic_ui(self):
        # 复用父类创建的 Notebook（机械臂控制 tab0），协同加为 tab1
        tab_hol = ttk.Frame(self.arm_notebook)
        self.arm_notebook.add(tab_hol, text="  协同控制(Holistic)  ")
        tab_hol.grid_columnconfigure(0, weight=1)
        tab_hol.grid_columnconfigure(1, weight=1)
        tab_hol.grid_columnconfigure(2, weight=1)
        tab_hol.grid_rowconfigure(0, weight=1)

        # ---- 左列：使能与跟随 ----
        left = ttk.LabelFrame(tab_hol, text="协同控制开关")
        left.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)

        r1 = ttk.Frame(left)
        r1.pack(fill="x", padx=4, pady=2)
        self.holistic_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="启用 Holistic 检测", variable=self.holistic_enable_var,
                        command=self._holistic_toggle).pack(anchor="w", pady=1)
        self.holistic_arm_follow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="机械臂跟随(腕→TCP movel)",
                        variable=self.holistic_arm_follow_var,
                        command=self._holistic_apply_flags).pack(anchor="w", pady=1)
        self.holistic_hand_follow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="灵巧手跟随(手→16关节角)",
                        variable=self.holistic_hand_follow_var,
                        command=self._holistic_apply_flags).pack(anchor="w", pady=1)

        r1b = ttk.Frame(left)
        r1b.pack(fill="x", padx=4, pady=2)
        ttk.Label(r1b, text="控制手:").pack(side="left")
        self.holistic_side_var = tk.StringVar(value="right")
        ttk.Radiobutton(r1b, text="右", value="right", variable=self.holistic_side_var,
                        command=self._holistic_apply_flags).pack(side="left")
        ttk.Radiobutton(r1b, text="左", value="left", variable=self.holistic_side_var,
                        command=self._holistic_apply_flags).pack(side="left")
        self.holistic_state_var = tk.StringVar(value="协同未启动")
        ttk.Label(left, textvariable=self.holistic_state_var, foreground="purple").pack(
            anchor="w", padx=4, pady=2)

        # ---- 中列：映射标定 ----
        mid = ttk.LabelFrame(tab_hol, text="腕→TCP 映射标定（先标定再跟随！）")
        mid.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)

        r2 = ttk.Frame(mid)
        r2.pack(fill="x", padx=4, pady=2)
        ttk.Label(r2, text="offset(x,y,z):").pack(side="left")
        self.calib_offset_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["offset"][i]))
            self.calib_offset_vars.append(var)
            ttk.Entry(r2, textvariable=var, width=6).pack(side="left", padx=1)
        r2b = ttk.Frame(mid)
        r2b.pack(fill="x", padx=4, pady=2)
        ttk.Label(r2b, text="scale(x,y,z):").pack(side="left")
        self.calib_scale_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["scale"][i]))
            self.calib_scale_vars.append(var)
            ttk.Entry(r2b, textvariable=var, width=6).pack(side="left", padx=1)
        r2c = ttk.Frame(mid)
        r2c.pack(fill="x", padx=4, pady=2)
        ttk.Label(r2c, text="add(x,y,z):  ").pack(side="left")
        self.calib_add_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["add"][i]))
            self.calib_add_vars.append(var)
            ttk.Entry(r2c, textvariable=var, width=6).pack(side="left", padx=1)
        r2d = ttk.Frame(mid)
        r2d.pack(fill="x", padx=4, pady=2)
        ttk.Button(r2d, text="应用标定", command=self._holistic_apply_calib).pack(side="left", padx=2)
        ttk.Button(r2d, text="读当前腕部填充offset", command=self._holistic_fill_offset).pack(side="left", padx=2)
        ttk.Label(r2d, text="（人体腕部3D − 期望TCP ≈ offset）", font=("", 7)).pack(side="left", padx=4)

        # ---- 右列：状态显示 ----
        right = ttk.LabelFrame(tab_hol, text="实时状态")
        right.grid(row=0, column=2, sticky="nsew", padx=4, pady=2)
        self.holistic_status_var = tk.StringVar(value="状态: -")
        ttk.Label(right, textvariable=self.holistic_status_var, font=("Consolas", 8),
                  foreground="purple", justify="left", wraplength=420).pack(
            fill="x", padx=4, pady=2)

    # ==================================================================
    # Holistic 控制
    # ==================================================================
    def _holistic_toggle(self):
        if self.holistic_enable_var.get():
            # 启动
            if self.cam is None:
                messagebox.showwarning("提示", "请先启动相机（L515 效果最佳）")
                self.holistic_enable_var.set(False)
                return
            try:
                self.holistic = HolisticPoseEstimator(hand_side=self.holistic_side_var.get())
                self.holistic_running = True
                self.holistic_state_var.set("协同运行中（检测人体+手）")
            except Exception as exc:
                messagebox.showerror("Holistic 启动失败", str(exc))
                self.holistic = None
                self.holistic_enable_var.set(False)
        else:
            self._holistic_stop()

    def _holistic_stop(self):
        if self.holistic is not None:
            try:
                self.holistic.close()
            except Exception:
                pass
        self.holistic = None
        self.holistic_running = False
        self.holistic_state_var.set("协同未启动")

    def _holistic_apply_flags(self):
        """同步手型/跟随开关。"""
        if self.holistic is not None:
            self.holistic.set_hand_side(self.holistic_side_var.get())
        if not self.holistic_arm_follow_var.get() and self.holistic_arm_follow_var.get() is False:
            pass

    def _holistic_apply_calib(self):
        try:
            self.follower.update_calib(
                offset=[float(v.get()) for v in self.calib_offset_vars],
                scale=[float(v.get()) for v in self.calib_scale_vars],
                add=[float(v.get()) for v in self.calib_add_vars],
            )
            self.holistic_status_var.set("标定参数已应用")
        except ValueError:
            messagebox.showerror("输入错误", "标定参数必须是数字")

    def _holistic_fill_offset(self):
        """辅助标定：读取当前检测到的腕部 3D，作为 offset 参考（需人体在画面中）。

        标定技巧：人把腕部放到"希望机械臂 TCP 到达的位置"（以机械臂基座系看是期望 TCP），
        相机系下该腕部 3D ≈ offset（当 scale=1、add=0 时）。读取后填入 offset 输入框。
        """
        if not self.holistic_running or self.holistic is None:
            messagebox.showwarning("提示", "请先启用 Holistic 检测并确保检测到人体")
            return
        # 用最近一帧的腕部（通过 _holistic_step 的缓存）
        wrist = getattr(self, "_last_wrist_3d", None)
        if wrist is None:
            messagebox.showwarning("提示", "未检测到腕部 3D，请确认人体在画面中")
            return
        for i in range(3):
            self.calib_offset_vars[i].set(f"{wrist[i]:.4f}")
        self.holistic_status_var.set("已用当前腕部 3D 填充 offset（再按实际偏差微调）")

    # ==================================================================
    # 每帧协同处理（挂到主轮询）
    # ==================================================================
    def _holistic_step(self, rgb, depth, intrinsics):
        """在 _poll_video 取到帧后调用：检测 + 映射 + 可选跟随。"""
        if not self.holistic_running or self.holistic is None:
            return None
        try:
            results = self.holistic.process(
                rgb, depth, intrinsics,
                map_to_arm=self.holistic_arm_follow_var.get(),
                arm_mapper=self.follower.map_wrist_to_arm_pose,
            )
        except Exception as exc:
            self.holistic_status_var.set(f"检测异常: {exc}")
            return None
        if not results:
            self.holistic_status_var.set("状态: 未检测到人体/手")
            return None
        r = results[0]
        parts = []
        if r.pose_detected:
            parts.append("人体✓")
        if r.hand_detected:
            parts.append("手✓")
        if r.wrist_3d is not None:
            w = r.wrist_3d
            self._last_wrist_3d = w          # 供"填充 offset"标定辅助
            parts.append(f"腕3D=({w[0]:.2f},{w[1]:.2f},{w[2]:.2f})")
        if r.arm_target_pose is not None:
            p = r.arm_target_pose
            parts.append(f"臂TCP=({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})")
        if r.hand_fist_confidence is not None:
            parts.append(f"握拳={r.hand_fist_confidence:.2f}")
        self.holistic_status_var.set("状态: " + " | ".join(parts))

        # ---- 机械臂跟随（腕→TCP）----
        if self.holistic_arm_follow_var.get() and r.arm_target_pose is not None:
            if self.arm_connected and self.arm is not None:
                try:
                    self.arm.movel(r.arm_target_pose, block=False, timeout_s=5)
                except Exception as exc:
                    self.holistic_status_var.set(f"臂跟随异常: {exc}")

        # ---- 灵巧手跟随（手→16角，独立于父类 mimic 开关，避免双重下发）----
        if self.holistic_hand_follow_var.get() and r.hand_detected:
            if self.hand is not None and not self.checkbox_vars["mimic_on"].get():
                try:
                    angles_rad = [math.radians(a) for a in r.hand_angles_deg]
                    self.hand.move_joints(angles_rad)
                except Exception as exc:
                    self.holistic_status_var.set(f"手跟随异常: {exc}")
        return r

    def _holistic_poll_loop(self):
        """常驻调度（防止 after 链因异常中断）。"""
        try:
            if self.holistic_running:
                pass
        except Exception:
            pass
        self.root.after(200, self._holistic_poll_loop)

    # ==================================================================
    # 覆写 _poll_video：在原有显示后追加 holistic 处理与骨架绘制
    # ==================================================================
    def _poll_video(self):
        # 调用父类原逻辑（取帧/推理/显示/模仿）
        super()._poll_video()
        # 若 holistic 运行且相机在，追加协同处理
        if self.holistic_running and self.cam is not None:
            try:
                # 复用父类已处理的当前帧（父类 _poll_video 已把帧存入 self._last_frame，
                # 不能再用 frame_q.get_nowait()——队列已被父类消费，再取会空队列）
                rgb, depth, intrinsics = getattr(self, "_last_frame", (None, None, None))
                if rgb is None:
                    return
                r = self._holistic_step(rgb, depth, intrinsics)
                # 绘制骨架叠加到画面（在原视频 canvas 上再画一层）
                if r is not None and self.checkbox_vars["show_skeleton"].get():
                    try:
                        disp = self.holistic.draw_skeleton(rgb, [r])
                        self._draw_holistic_to_canvas(disp)
                    except Exception:
                        pass
            except Exception:
                pass

    def _draw_holistic_to_canvas(self, frame: np.ndarray):
        """把 holistic 骨架帧显示到视频画布（等比缩放+居中裁剪，与原逻辑一致）。"""
        try:
            from PIL import Image, ImageTk
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            if canvas_w < 2 or canvas_h < 2:
                canvas_w, canvas_h = 800, 600
            src_h, src_w = frame.shape[:2]
            scale = max(canvas_w / src_w, canvas_h / src_h)
            new_w = max(1, int(round(src_w * scale)))
            new_h = max(1, int(round(src_h * scale)))
            resized = cv2.resize(frame, (new_w, new_h))
            x0 = max(0, (new_w - canvas_w) // 2)
            y0 = max(0, (new_h - canvas_h) // 2)
            crop = resized[y0:y0 + canvas_h, x0:x0 + canvas_w]
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.video_canvas.delete("all")
            self.video_canvas.create_image(0, 0, anchor="nw", image=img)
            self.video_canvas.image = img
        except Exception:
            pass

    # ==================================================================
    # 关闭：先停 holistic
    # ==================================================================
    def _on_close(self):
        self._holistic_stop()
        super()._on_close()


def main():
    root = tk.Tk()
    MainGuiHolistic(root)
    root.mainloop()


if __name__ == "__main__":
    main()
