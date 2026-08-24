# -*- coding: utf-8 -*-
"""
main_gui.py —— 综合控制界面（视频区域固定 16:9，无黑边）
"""
from __future__ import annotations

import json
import logging
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from collections import deque

# ---- 路径引导 ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import cv2
import numpy as np
from PIL import Image, ImageTk

from lib.camera_lib1 import CameraModule
from vision import HandPoseEstimator
from vision.postprocess import JointAnglePostProcess
from hand import RYH1HandController, JOINT_NAMES_CN, JOINT_NUM, status_text

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main_gui")

# ============================================================
# 参数配置字典
# ============================================================
PARAM_CONFIG = {
    "bend_gain": {
        "label": "弯曲增益",
        "range": (0.5, 2.5, 0.05),
        "default": 1.0,
        "desc": "放大/缩小弯曲幅度"
    },
    "bend_scale": {
        "label": "缩放",
        "range": (0.5, 1.5, 0.05),
        "default": 1.0,
        "desc": "整体弯曲比例"
    },
    "bend_offset": {
        "label": "偏置",
        "range": (-30, 30, 1),
        "default": 0,
        "desc": "固定偏移"
    },
    "deadzone": {
        "label": "死区",
        "range": (0, 10, 0.5),
        "default": 1.0,
        "desc": "消除微动"
    },
    "smooth": {
        "label": "平滑系数",
        "range": (0.1, 0.9, 0.05),
        "default": 0.35,
        "desc": "平滑强度"
    },
    "min_cutoff": {
        "label": "平滑强度(1€)",
        "range": (0.1, 2.0, 0.05),
        "default": 0.5,
        "desc": "One Euro 最小截止频率，越小越平滑"
    },
    "beta": {
        "label": "跟手度(1€)",
        "range": (0.0, 0.2, 0.005),
        "default": 0.02,
        "desc": "速度自适应系数，越大越跟手"
    },
    "max_delta": {
        "label": "限速°/帧",
        "range": (1.0, 20.0, 0.5),
        "default": 8.0,
        "desc": "每帧最大角度变化（防突跳）"
    },
    "thumb_abd_offset": {
        "label": "内外展死区",
        "range": (0.0, 0.5, 0.01),
        "default": 0.0,
        "desc": "手掌宽度倍数，切除并拢时底部无效区间"
    },
    "thumb_abd_gain": {
        "label": "内外展增益",
        "range": (0.3, 2.0, 0.05),
        "default": 0.8,
        "desc": "放大归一化横向距离（TIP/掌宽）"
    },
    "abduct_max_delta": {
        "label": "内外展限速°/帧",
        "range": (0.5, 8.0, 0.5),
        "default": 2.0,
        "desc": "内外展单帧最大变化（防跳变，越小越稳）"
    },
}

CHECKBOX_CONFIG = {
    "bend_reverse": {"label": "弯曲反转", "default": False},
    "thumb_abd_reverse": {"label": "内外展反转", "default": False},
    "use_dist_ratio": {"label": "距离比法", "default": False},
    "show_skeleton": {"label": "显示骨架", "default": True},
    "show_angles": {"label": "显示关节角", "default": True},
    "mimic_on": {"label": "动作模仿", "default": False},
}


def slider_range_for_joint(i: int) -> tuple:
    if i == 0:
        return (-20.0, 20.0)
    if i == 15:
        return (0.0, 110.0)
    m = i % 3
    if m == 0:
        return (-20.0, 20.0)
    if m == 1:
        return (0.0, 90.0)
    return (0.0, 75.0)


class MainGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("睿研 RY-H1(16) 灵巧手 · 视觉控制台")
        self.root.geometry("1600x900")

        self.cam: CameraModule | None = None
        self.est: HandPoseEstimator | None = None
        self.hand: RYH1HandController | None = None

        self.frame_q: queue.Queue = queue.Queue(maxsize=2)
        self._running = False
        self._smoother_state = [0.0] * JOINT_NUM
        self._capture_thread: threading.Thread | None = None
        self._stop_thread: threading.Thread | None = None
        self._after_id: str | None = None

        self.angle_history = deque(maxlen=5)

        # 精度后处理链（方向一致性异常检测 + 中值 + One Euro + 分通道限速）
        self.post = JointAnglePostProcess(
            joint_num=JOINT_NUM, median_n=5,
            min_cutoff=0.5, beta=0.02,
            max_delta_deg=8.0, abduct_max_delta_deg=3.0,
            max_jump_deg=40.0, jump_ratio_threshold=3.0,
        )

        # 参数变量
        self.param_vars = {}
        self.checkbox_vars = {}
        self.finger_vars = {}
        self.finger_offset_vars = {}

        self._build_ui()

        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "calibration.json")
        self._load_calibration()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # ---- 控制变量 ----
        self.cam_mode = tk.StringVar(value="usb")
        self.cam_idx = tk.IntVar(value=0)
        self.hand_method = tk.StringVar(value="pcan")
        self.hand_lr = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="未连接")
        self.state_var = tk.StringVar(value="相机未启动")
        self.info_var = tk.StringVar(value="等待相机...")

        # ---- 布局 ----
        self.root.grid_rowconfigure(0, weight=0)   # 顶部栏
        self.root.grid_rowconfigure(1, weight=1)   # 中部
        self.root.grid_rowconfigure(2, weight=0)   # 底部滑条
        self.root.grid_rowconfigure(3, weight=0)   # 底部按钮
        self.root.grid_columnconfigure(0, weight=1)

        # ---- 顶部控制栏 ----
        top = ttk.Frame(self.root)
        top.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        ttk.Label(top, text="相机:").pack(side="left")
        ttk.Radiobutton(top, text="USB", value="usb", variable=self.cam_mode).pack(side="left", padx=2)
        ttk.Radiobutton(top, text="L515", value="realsense", variable=self.cam_mode).pack(side="left", padx=2)
        ttk.Label(top, text="索引:").pack(side="left", padx=4)
        ttk.Spinbox(top, from_=0, to=9, textvariable=self.cam_idx, width=3).pack(side="left")
        ttk.Button(top, text="启动", command=self._start_camera).pack(side="left", padx=4)
        ttk.Button(top, text="停止", command=self._stop_camera).pack(side="left", padx=4)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(top, text="手通信:").pack(side="left")
        for method in ["PCAN", "CANII", "RS485"]:
            ttk.Radiobutton(top, text=method, value=method.lower(),
                            variable=self.hand_method).pack(side="left", padx=2)
        ttk.Radiobutton(top, text="右手", value=1, variable=self.hand_lr,
                        command=self._on_hand_lr).pack(side="left", padx=2)
        ttk.Radiobutton(top, text="左手", value=0, variable=self.hand_lr,
                        command=self._on_hand_lr).pack(side="left", padx=2)
        ttk.Button(top, text="连接", command=self._connect_hand).pack(side="left", padx=4)
        ttk.Button(top, text="自检", command=self._check_hand).pack(side="left", padx=4)
        ttk.Button(top, text="回零", command=self._homing).pack(side="left", padx=4)
        ttk.Button(top, text="断开", command=self._disconnect_hand).pack(side="left")

        ttk.Label(top, textvariable=self.status_var, foreground="blue").pack(side="left", padx=8)

        # ---- 中部：视频 + 参数 ----
        mid_frame = ttk.Frame(self.root)
        mid_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=2)
        mid_frame.grid_rowconfigure(0, weight=1)
        # 视频区 58%，参数区 42%（参数全部显示，无需滚动，接近方形）
        mid_frame.grid_columnconfigure(0, weight=58)
        mid_frame.grid_columnconfigure(1, weight=42)

        # ---- 左侧视频区域（自适应，保持原相机比例） ----
        left_frame = ttk.Frame(mid_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        vid_frame = ttk.LabelFrame(left_frame, text="实时画面（保持原相机比例，等比缩放居中）")
        vid_frame.pack(fill="both", expand=True, padx=2, pady=2)
        vid_frame.grid_rowconfigure(0, weight=1)
        vid_frame.grid_columnconfigure(0, weight=1)

        self.video_canvas = tk.Canvas(vid_frame, bg="black", highlightthickness=1)
        self.video_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.video_info_var = tk.StringVar(value="相机未启动")
        ttk.Label(vid_frame, textvariable=self.video_info_var,
                  foreground="gray").grid(row=1, column=0, sticky="w", padx=4)

        ttk.Label(vid_frame, textvariable=self.state_var,
                  foreground="green").grid(row=2, column=0, sticky="w", padx=4)

        # ---- 右侧参数面板（方形，全部显示，无需滚动） ----
        right_frame = ttk.Frame(mid_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # 参数区做成两列（每列两个分组），全部内容一次显示
        param_canvas_frame = ttk.Frame(right_frame)
        param_canvas_frame.grid(row=0, column=0, sticky="nsew")
        param_canvas_frame.grid_rowconfigure(0, weight=1)
        param_canvas_frame.grid_columnconfigure(0, weight=1)
        param_canvas_frame.grid_columnconfigure(1, weight=1)

        # 左列：全局校准 + 拇指内外展 + 控制开关
        col_left = ttk.Frame(param_canvas_frame)
        col_left.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        cal_frame = ttk.LabelFrame(col_left, text="全局校准")
        cal_frame.pack(fill="x", padx=2, pady=2)
        self._add_param_group(cal_frame, ["bend_gain", "bend_scale", "bend_offset",
                                          "deadzone", "smooth",
                                          "min_cutoff", "beta", "max_delta"])

        abd_frame = ttk.LabelFrame(col_left, text="拇指内外展校准")
        abd_frame.pack(fill="x", padx=2, pady=2)
        self._add_param_group(abd_frame, ["thumb_abd_offset", "thumb_abd_gain",
                                          "abduct_max_delta"])

        ctrl_frame = ttk.LabelFrame(col_left, text="控制开关")
        ctrl_frame.pack(fill="x", padx=2, pady=2)
        for idx, (key, cfg) in enumerate(CHECKBOX_CONFIG.items()):
            var = tk.BooleanVar(value=cfg["default"])
            self.checkbox_vars[key] = var
            if key == "mimic_on":
                chk = ttk.Checkbutton(ctrl_frame, text=cfg["label"], variable=var,
                                      command=self._toggle_mimic)
            else:
                chk = ttk.Checkbutton(ctrl_frame, text=cfg["label"], variable=var,
                                      command=self._apply_calib)
            chk.grid(row=idx//2, column=idx%2, sticky="w", padx=4, pady=1)

        # 右列：每指增益 + 每指偏移 + 实时参数
        col_right = ttk.Frame(param_canvas_frame)
        col_right.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        finger_frame = ttk.LabelFrame(col_right, text="每指增益")
        finger_frame.pack(fill="x", padx=2, pady=2)
        finger_names = ["thumb", "index", "middle", "ring", "pinky"]
        finger_display = ["拇指", "食指", "中指", "无名指", "小指"]
        self.finger_vars = {}
        for idx, (name, display) in enumerate(zip(finger_names, finger_display)):
            var = tk.DoubleVar(value=1.0)
            self.finger_vars[name] = var
            self._add_slider(finger_frame, display, var, 0.5, 2.0, 0.05)

        offset_frame = ttk.LabelFrame(col_right, text="每指偏移")
        offset_frame.pack(fill="x", padx=2, pady=2)
        self.finger_offset_vars = {}
        for idx, (name, display) in enumerate(zip(finger_names, finger_display)):
            var = tk.DoubleVar(value=0.0)
            self.finger_offset_vars[name] = var
            self._add_slider(offset_frame, display, var, -30, 30, 1)

        disp_frame = ttk.LabelFrame(col_right, text="实时参数")
        disp_frame.pack(fill="both", expand=True, padx=2, pady=2)
        ttk.Label(disp_frame, textvariable=self.info_var, justify="left",
                  font=("Consolas", 8)).pack(anchor="w", padx=4, fill="both", expand=True)

        # ---- 底部：关节滑条（长方形布局：16 列 × 2 行，横向长条） ----
        bot_frame = ttk.LabelFrame(self.root, text="16 关节手动控制（长方形布局）")
        bot_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        self.angle_vars = []
        self.sliders = []
        cols = 8                      # 8 列 × 2 行 = 长方形（更宽更扁）
        slider_len = 120
        for i in range(JOINT_NUM):
            row = (i // cols) * 2
            col = i % cols
            f = ttk.Frame(bot_frame)
            f.grid(row=row, column=col, sticky="nsew", padx=3, pady=1)
            var = tk.DoubleVar(value=0.0)
            self.angle_vars.append(var)
            lo, hi = slider_range_for_joint(i)
            label_text = f"{i+1}:{JOINT_NAMES_CN[i]}"
            ttk.Label(f, text=label_text, font=("", 7)).pack(anchor="w")
            s = tk.Scale(f, from_=lo, to=hi, resolution=0.5, orient=tk.HORIZONTAL,
                         variable=var, length=slider_len,
                         command=lambda _v, idx=i: self._slider_changed(idx))
            s.pack(fill="x")
            self.sliders.append(s)
        # 平均分配 8 列宽度（撑满横向）
        for c in range(cols):
            bot_frame.grid_columnconfigure(c, weight=1)

        # ---- 底部按钮 ----
        btns = ttk.Frame(self.root)
        btns.grid(row=3, column=0, sticky="ew", padx=5, pady=2)
        ttk.Button(btns, text="张开", command=self._preset_open).pack(side="left", padx=2)
        ttk.Button(btns, text="握拳", command=self._preset_close).pack(side="left", padx=2)
        ttk.Button(btns, text="放松", command=self._preset_relax).pack(side="left", padx=2)
        ttk.Button(btns, text="归零", command=self._preset_zero).pack(side="left", padx=2)
        ttk.Label(btns, text="单电机 ID:").pack(side="left", padx=(10, 2))
        self.motor_id = tk.IntVar(value=9)
        ttk.Spinbox(btns, from_=1, to=16, textvariable=self.motor_id, width=3).pack(side="left")
        ttk.Label(btns, text="位置:").pack(side="left", padx=4)
        self.motor_pos = tk.IntVar(value=2048)
        ttk.Spinbox(btns, from_=0, to=4095, textvariable=self.motor_pos, width=5).pack(side="left")
        ttk.Button(btns, text="测试", command=self._test_motor).pack(side="left", padx=4)

    def _add_slider(self, parent, label, var, from_, to, resolution):
        """添加单个滑条行（紧凑，适合方形面板全部显示）"""
        f = ttk.Frame(parent)
        f.pack(fill="x", padx=2, pady=0)
        ttk.Label(f, text=label, width=12, font=("", 8), anchor="w").pack(side="left")
        tk.Scale(f, from_=from_, to=to, resolution=resolution, orient=tk.HORIZONTAL,
                 variable=var, length=120, showvalue=False,
                 command=lambda _: self._apply_calib()).pack(side="left", fill="x", expand=True)
        ttk.Label(f, textvariable=var, width=5, font=("", 8), anchor="e").pack(side="left")

    def _add_param_group(self, parent, keys):
        """添加参数组（每个参数一个滑条）"""
        for key in keys:
            cfg = PARAM_CONFIG[key]
            var = tk.DoubleVar(value=cfg["default"])
            self.param_vars[key] = var
            self._add_slider(parent, cfg["label"], var, cfg["range"][0], cfg["range"][1], cfg["range"][2])

    # ==================================================================
    # 配置持久化
    # ==================================================================
    def _load_calibration(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for key in self.param_vars:
                if key in data:
                    self.param_vars[key].set(data[key])
            for key in self.checkbox_vars:
                if key in data:
                    self.checkbox_vars[key].set(data[key])
            if "per_finger_scale" in data:
                for name, val in data["per_finger_scale"].items():
                    if name in self.finger_vars:
                        self.finger_vars[name].set(val)
            if "per_finger_offset" in data:
                for name, val in data["per_finger_offset"].items():
                    if name in self.finger_offset_vars:
                        self.finger_offset_vars[name].set(val)
            logger.info("校准配置已加载")
        except Exception as e:
            logger.warning("加载校准配置失败: %s", e)

    def _save_calibration(self):
        data = {}
        for key, var in self.param_vars.items():
            data[key] = var.get()
        for key, var in self.checkbox_vars.items():
            data[key] = var.get()
        data["per_finger_scale"] = {name: var.get() for name, var in self.finger_vars.items()}
        data["per_finger_offset"] = {name: var.get() for name, var in self.finger_offset_vars.items()}
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("保存校准配置失败: %s", e)

    # ==================================================================
    # 相机
    # ==================================================================
    def _start_camera(self):
        if self.cam is not None:
            self._stop_camera()
        try:
            use_rs = self.cam_mode.get() == "realsense"
            self.cam = CameraModule(
                source=self.cam_idx.get(), use_realsense=use_rs,
                width=1280 if use_rs else 640,
                height=720 if use_rs else 480,
                depth_width=1024, depth_height=768)
            self.est = HandPoseEstimator(
                max_hands=1,
                use_distance_ratio=self.checkbox_vars["use_dist_ratio"].get(),
                thumb_abd_offset=self.param_vars["thumb_abd_offset"].get(),
                thumb_abd_gain=self.param_vars["thumb_abd_gain"].get(),
                thumb_abd_reverse=self.checkbox_vars["thumb_abd_reverse"].get(),
            )
            self._apply_calib()
            self._running = True
            self._after_id = None
            self._stop_thread = None
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            self.state_var.set("相机已启动")
            self._poll_video()
        except Exception as exc:
            messagebox.showerror("相机启动失败", str(exc))

    def _stop_camera(self):
        logger.info(">>> _stop_camera 开始")
        self._running = False

        if hasattr(self, '_after_id') and self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            except Exception:
                pass

        if hasattr(self, '_capture_thread') and self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=0.5)

        while not self.frame_q.empty():
            try:
                self.frame_q.get_nowait()
            except queue.Empty:
                break

        cam_to_release = self.cam
        est_to_close = self.est
        self.cam = None
        self.est = None

        def release_resources():
            if cam_to_release is not None:
                try:
                    cam_to_release.release()
                except Exception as e:
                    logger.warning("cam.release() 异常: %s", e)
            if est_to_close is not None:
                try:
                    est_to_close.close()
                except Exception as e:
                    logger.warning("est.close() 异常: %s", e)

        self._stop_thread = threading.Thread(target=release_resources, daemon=True)
        self._stop_thread.start()
        self.state_var.set("相机停止中...")
        logger.info(">>> _stop_camera 完成（主线程）")

    def _capture_loop(self):
        while self._running and self.cam is not None:
            try:
                rgb, depth = self.cam.read()
                if rgb is None:
                    time.sleep(0.005)
                    continue
                if self.frame_q.full():
                    try:
                        self.frame_q.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_q.put((rgb, depth), timeout=0.1)
            except queue.Full:
                pass
            except Exception as exc:
                logger.warning("capture: %s", exc)
            time.sleep(0.01)
        logger.info("_capture_loop 退出")

    def _poll_video(self):
        if not self._running:
            return

        try:
            rgb, depth = self.frame_q.get_nowait()
        except queue.Empty:
            if self._running:
                self._after_id = self.root.after(30, self._poll_video)
            return

        if not self._running:
            return

        intrinsics = None
        if self.cam is not None and hasattr(self.cam, 'get_intrinsics'):
            intrinsics = self.cam.get_intrinsics()

        results = []
        if self.est is not None:
            try:
                results = self.est.process(rgb, depth, intrinsics)
            except Exception as e:
                logger.warning("推理异常: %s", e)

        if results:
            results_right = [r for r in results if r.handedness.lower() == "right"]
            results = results_right if results_right else []

        disp = rgb.copy()
        if results and self.checkbox_vars["show_skeleton"].get():
            try:
                disp = self.est.draw_skeleton(disp, results)
            except Exception as e:
                logger.warning("绘制骨架异常: %s", e)

        angles_deg = None
        norm_dist = None
        fist_conf = None
        if results:
            try:
                r = results[0]
                angles_deg = r.joint_angles_deg
                norm_dist = getattr(r, "lateral_dist", None)   # 横向距离（原代码误用 norm_dist）
                fist_conf = getattr(r, "fist_confidence", None)  # 深度辅助握拳置信度
                if self.checkbox_vars["show_angles"].get():
                    y = 20
                    for i in range(JOINT_NUM):
                        cv2.putText(disp, f"J{i+1:2d} {angles_deg[i]:5.1f}", (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        y += 16
            except Exception as e:
                logger.warning("角度叠加异常: %s", e)

        if self.checkbox_vars["mimic_on"].get() and self.hand is not None and angles_deg is not None:
            try:
                self._mimic_apply(angles_deg, fist_conf)
            except Exception as e:
                logger.warning("动作模仿异常: %s", e)

        # ---- 信息展示 ----
        info = "未识别到手"
        if results and angles_deg is not None:
            r = results[0]
            dep = f" 深度={r.avg_depth_mm:.0f}mm" if r.avg_depth_mm else ""
            finger_names = ["拇指", "食指", "中指", "无名指", "小指"]
            start_idx = [0, 3, 6, 9, 12]
            lines = []
            for idx, name in enumerate(finger_names):
                base = start_idx[idx]
                line = f"{name}:  侧摆{angles_deg[base]:5.1f}  MCP{angles_deg[base+1]:5.1f}  PIP{angles_deg[base+2]:5.1f}"
                lines.append(line)
            lines.append(f"内外展: {angles_deg[15]:5.1f}")
            if norm_dist is not None:
                lines.append(f"横向距离: {norm_dist:.3f}")
            if fist_conf is not None:
                lines.append(f"握拳置信(深度): {fist_conf:.2f}")
            angle_str = "\n".join(lines)
            # 稳定性指标（后处理）
            if hasattr(self, "post"):
                st = self.post.get_stats()
                angle_str += (f"\n稳定性: 抖动std={st['jitter_std_deg']:.2f}° "
                              f"丢弃率={st['drop_rate_pct']:.1f}%")
            info = (f"手: {r.handedness} 置信={r.confidence:.2f}{dep}\n"
                    f"关节角:\n{angle_str}")
        self.info_var.set(info)

        # ---- 显示画面：保持原相机宽高比，等比缩放后居中（无变形、无黑边） ----
        try:
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            if canvas_w < 2 or canvas_h < 2:
                canvas_w, canvas_h = 800, 600

            src_h, src_w = disp.shape[:2]
            src_ratio = src_w / src_h          # 原相机宽高比

            # 以"填满"为原则等比缩放：scale = max(cw/sw, ch/sh)，
            # 缩放后裁掉超出 Canvas 的部分（保持比例 -> 无黑边、无变形）。
            scale = max(canvas_w / src_w, canvas_h / src_h)
            new_w = max(1, int(round(src_w * scale)))
            new_h = max(1, int(round(src_h * scale)))
            resized = cv2.resize(disp, (new_w, new_h))

            # 居中裁剪到 Canvas 尺寸
            x0 = max(0, (new_w - canvas_w) // 2)
            y0 = max(0, (new_h - canvas_h) // 2)
            crop = resized[y0:y0 + canvas_h, x0:x0 + canvas_w]

            resized_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(resized_rgb))
            self.video_canvas.delete("all")
            self.video_canvas.create_image(0, 0, anchor="nw", image=img)
            self.video_canvas.image = img

            # 显示相机比例信息（帮助理解"高度长度"）
            self.video_info_var.set(
                f"相机 {src_w}x{src_h} (比例 {src_ratio:.3f}) | "
                f"显示 {canvas_w}x{canvas_h} | 缩放 {scale:.2f}x"
            )
        except Exception as exc:
            logger.warning("显示画面异常: %s", exc)

        if self._running:
            self._after_id = self.root.after(30, self._poll_video)
        else:
            logger.info(">>> _poll_video 不再调度")

    # ==================================================================
    # 校准应用
    # ==================================================================
    def _apply_calib(self):
        if self.est is None:
            return
        self.est.update_params(
            bend_gain=self.param_vars["bend_gain"].get(),
            bend_scale=self.param_vars["bend_scale"].get(),
            bend_offset=self.param_vars["bend_offset"].get(),
            deadzone_deg=self.param_vars["deadzone"].get(),
            bend_reverse=self.checkbox_vars["bend_reverse"].get(),
            use_distance_ratio=self.checkbox_vars["use_dist_ratio"].get(),
            per_finger_scale={name: var.get() for name, var in self.finger_vars.items()},
            per_finger_offset={name: var.get() for name, var in self.finger_offset_vars.items()},
            thumb_abd_offset=self.param_vars["thumb_abd_offset"].get(),
            thumb_abd_gain=self.param_vars["thumb_abd_gain"].get(),
            thumb_abd_reverse=self.checkbox_vars["thumb_abd_reverse"].get(),
        )
        # 同步后处理参数
        if hasattr(self, "post"):
            self.post.update_params(
                min_cutoff=self.param_vars["min_cutoff"].get(),
                beta=self.param_vars["beta"].get(),
                max_delta_deg=self.param_vars["max_delta"].get(),
                abduct_max_delta_deg=self.param_vars["abduct_max_delta"].get(),
            )
        self._save_calibration()

    # ==================================================================
    # 灵巧手控制
    # ==================================================================
    def _connect_hand(self):
        try:
            if self.hand is not None:
                self._disconnect_hand()
            self.hand = RYH1HandController(method=self.hand_method.get(), hand_lr=self.hand_lr.get())
            self.hand.open()
            self.status_var.set(f"已连接（{self.hand_method.get()}）")
        except Exception as exc:
            messagebox.showerror("连接失败", str(exc))

    def _disconnect_hand(self):
        if self.hand is not None:
            try:
                self.hand.close()
            except Exception:
                pass
            self.hand = None
        self.status_var.set("未连接")

    def _on_hand_lr(self):
        if self.hand is not None:
            self.hand.set_hand_lr(self.hand_lr.get())

    def _check_hand(self):
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接手")
            return
        res = self.hand.check_connection()
        msg = f"库版本 {res['version']}，{res['replies']}/16 应答"
        if res["faults"]:
            msg += "\n故障:"
            for mid, st, txt in res["faults"]:
                msg += f"\n  电机{mid:2d}: {txt}"
        if res.get("need_homing"):
            msg += "\n⚠️ 有找零告警电机，点击【回零】"
        messagebox.showinfo("自检", msg)

    def _homing(self):
        if self.hand is None:
            return
        if not messagebox.askyesno("回零", "对全部电机执行回零？"):
            return
        self.hand.homing(timeout_ms=1500, sleep_s=0.3)
        time.sleep(1)
        messagebox.showinfo("回零", "回零完成")

    def _slider_changed(self, idx: int):
        if self.hand is None:
            return
        angles = [0.0] * JOINT_NUM
        for i, var in enumerate(self.angle_vars):
            angles[i] = math.radians(var.get())
        try:
            self.hand.move_joints(angles)
        except Exception as exc:
            logger.error("move_joints: %s", exc)

    def _preset_open(self):
        self._set_all(0.0)
        if self.hand:
            self.hand.open_hand()

    def _preset_close(self):
        vals = [0, 50, 30, 0, 70, 60, 0, 70, 60, 0, 70, 60, 0, 70, 60, 0]
        self._set_all_list(vals)
        if self.hand:
            self.hand.close_hand()

    def _preset_relax(self):
        vals = [0, 30, 15, 0, 35, 25, 0, 35, 25, 0, 35, 25, 0, 35, 25, 0]
        self._set_all_list(vals)
        if self.hand:
            self.hand.relax()

    def _preset_zero(self):
        self._set_all(0.0)
        if self.hand:
            self.hand.open_hand()

    def _set_all(self, val: float):
        for var in self.angle_vars:
            var.set(val)

    def _set_all_list(self, vals: list):
        for i, var in enumerate(self.angle_vars):
            if i < len(vals):
                var.set(vals[i])

    def _test_motor(self):
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接手")
            return
        mid = self.motor_id.get()
        pos = self.motor_pos.get()
        self.hand.move_motor(mid, pos)
        info = self.hand.get_servo_info(mid, timeout_ms=200)
        msg = f"电机{mid} 位置={pos}"
        if info:
            msg += f"\n回读 P={info.position} 状态={info.status}[{status_text(info.status)}]"
        else:
            msg += "\n无应答"
        messagebox.showinfo("单电机测试", msg)

    def _toggle_mimic(self):
        self._smoother_state = [0.0] * JOINT_NUM
        if hasattr(self, "post"):
            self.post.reset()
        self.state_var.set("动作模仿已开启" if self.checkbox_vars["mimic_on"].get() else "动作模仿已关闭")

    def _mimic_apply(self, angles_deg: List[float],
                     fist_confidence: float | None = None):
        """精度后处理链：均值 → deadzone → 异常检测(方向一致性+深度)/中值/One Euro/分通道限速 → 下发。"""
        deadzone_deg = self.param_vars["deadzone"].get()
        # 多帧均值（去单帧毛刺，配合 post 内部中值）
        self.angle_history.append(angles_deg.copy())
        if len(self.angle_history) >= 3:
            avg_deg = [0.0] * JOINT_NUM
            for i in range(JOINT_NUM):
                vals = [frame[i] for frame in self.angle_history]
                avg_deg[i] = sum(vals) / len(vals)
        else:
            avg_deg = angles_deg

        # deadzone（静态小角度归零，防微颤）
        for i in range(JOINT_NUM):
            if abs(avg_deg[i]) < deadzone_deg:
                avg_deg[i] = 0.0

        # 核心：方向一致性+深度辅助异常检测 → 中值 → One Euro → 分通道限速
        out_deg = self.post.update(avg_deg, fist_confidence=fist_confidence)

        angles_rad = [math.radians(v) for v in out_deg]
        try:
            self.hand.move_joints(angles_rad)
        except Exception as exc:
            logger.error("mimic_apply 异常: %s", exc)

    def _on_close(self):
        logger.info(">>> 窗口关闭开始")
        self._running = False
        if hasattr(self, '_after_id') and self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            except Exception:
                pass
        self._stop_camera()
        self._disconnect_hand()
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        logger.info(">>> 强制终止进程")
        os._exit(0)


def main():
    root = tk.Tk()
    MainGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()