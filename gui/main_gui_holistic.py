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
        self._build_holistic_ui()
        self._holistic_poll_loop()

    # ==================================================================
    # 协同控制面板
    # ==================================================================
    def _build_holistic_ui(self):
        root = self.root
        # 第 5 行：协同控制面板
        root.grid_rowconfigure(5, weight=0)
        frame = ttk.LabelFrame(root, text="协同控制（MediaPipe Holistic：人体→机械臂 + 手→灵巧手）")
        frame.grid(row=5, column=0, sticky="ew", padx=5, pady=2)

        # 行 1：使能开关 + 检测状态
        r1 = ttk.Frame(frame)
        r1.pack(fill="x", padx=4, pady=2)
        self.holistic_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="启用 Holistic 检测", variable=self.holistic_enable_var,
                        command=self._holistic_toggle).pack(side="left", padx=2)
        self.holistic_arm_follow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="机械臂跟随(腕→TCP)", variable=self.holistic_arm_follow_var,
                        command=self._holistic_apply_flags).pack(side="left", padx=2)
        self.holistic_hand_follow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="灵巧手跟随(手→16角)", variable=self.holistic_hand_follow_var,
                        command=self._holistic_apply_flags).pack(side="left", padx=2)
        self.holistic_side_var = tk.StringVar(value="right")
        ttk.Label(r1, text="手:").pack(side="left", padx=(10, 2))
        ttk.Radiobutton(r1, text="右", value="right", variable=self.holistic_side_var,
                        command=self._holistic_apply_flags).pack(side="left")
        ttk.Radiobutton(r1, text="左", value="left", variable=self.holistic_side_var,
                        command=self._holistic_apply_flags).pack(side="left")
        ttk.Label(r1, textvariable=self.holistic_state_var, foreground="purple").pack(side="left", padx=8)

        # 行 2：映射标定参数（offset/scale/add 前3个）
        r2 = ttk.Frame(frame)
        r2.pack(fill="x", padx=4, pady=2)
        ttk.Label(r2, text="映射标定 offset(x,y,z):").pack(side="left")
        self.calib_offset_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["offset"][i]))
            self.calib_offset_vars.append(var)
            ttk.Entry(r2, textvariable=var, width=6).pack(side="left", padx=1)
        ttk.Label(r2, text="scale:").pack(side="left", padx=(8, 2))
        self.calib_scale_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["scale"][i]))
            self.calib_scale_vars.append(var)
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=1)
        ttk.Label(r2, text="add:").pack(side="left", padx=(8, 2))
        self.calib_add_vars = []
        for i in range(3):
            var = tk.StringVar(value=str(DEFAULT_CALIB["add"][i]))
            self.calib_add_vars.append(var)
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=1)
        ttk.Button(r2, text="应用标定", command=self._holistic_apply_calib).pack(side="left", padx=6)

        # 行 3：状态显示
        r3 = ttk.Frame(frame)
        r3.pack(fill="x", padx=4, pady=2)
        self.holistic_status_var = tk.StringVar(value="状态: -")
        ttk.Label(r3, textvariable=self.holistic_status_var, font=("Consolas", 8),
                  foreground="purple").pack(side="left")

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
                # 从队列取最新帧（非阻塞）
                rgb, depth = self.frame_q.get_nowait()
                intrinsics = None
                if hasattr(self.cam, 'get_intrinsics'):
                    intrinsics = self.cam.get_intrinsics()
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
