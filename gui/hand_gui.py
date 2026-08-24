# -*- coding: utf-8 -*-
"""
hand_gui.py —— 灵巧手控制 GUI（tkinter，零额外依赖）

功能（用于独立验证灵巧手连接性与手动控制）：
  * 通信方式选择：PCAN / CANalyst-II / RS485
  * 连接 / 断开 / 连接性自检（读库版本 + 16 电机应答 + 故障提示）
  * 16 关节滑条控制（角度实时下发）+ 手型选择（左/右手）
  * 预设动作：张开 / 握拳 / 放松
  * 状态监视：定时读取 16 电机 位置/速度/电流

运行：
  python -m gui.hand_gui      # 从项目根目录运行（推荐）
  python gui/hand_gui.py      # 直接运行（顶部路径引导自动定位根目录）

依赖：仅标准库 tkinter（Python 自带）+ 本项目 hand 包。
"""

from __future__ import annotations

# ---- 路径引导（必须最先执行：定位项目根目录 + 控制台 UTF-8） ----
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import logging
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox

from hand import RYH1HandController, JOINT_NAMES_CN, JOINT_NUM


def slider_range_for_joint(i: int) -> tuple:
    """按关节类型返回滑条角度范围（度），依据 RY-H1 手册角度范围。

    侧摆(关节 1/4/7/10/13) -20°~+20°；近节(2/5/8/11/14) 0~90°；
    远节(3/6/9/12/15) 0~75°；第16关节(16) 0~110°。
    """
    if i == 15:
        return (0.0, 110.0)      # 第16关节（拇指横向旋转 0~110°）
    m = i % 3
    if m == 0:
        return (-20.0, 20.0)     # 侧摆（对称，可双向）
    if m == 1:
        return (0.0, 90.0)       # 近节弯曲
    return (0.0, 75.0)           # 远节弯曲

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gui")


class HandGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("睿研 RY-H1(16) 灵巧手控制面板")
        self.root.geometry("980x720")

        self.hand: RYH1HandController | None = None
        self.sliders = []
        self.angle_vars = []
        self._monitor_job = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _build_ui(self):
        top = ttk.LabelFrame(self.root, text="连接设置")
        top.pack(fill="x", padx=8, pady=4)

        ttk.Label(top, text="通信方式:").pack(side="left", padx=4)
        self.method_var = tk.StringVar(value="pcan")
        for text, val in [("PCAN", "pcan"), ("CANalyst-II", "canii"), ("RS485", "rs485")]:
            ttk.Radiobutton(top, text=text, value=val,
                            variable=self.method_var).pack(side="left", padx=4)

        ttk.Label(top, text="串口(RS485):").pack(side="left", padx=8)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(top, textvariable=self.port_var, width=8).pack(side="left")

        ttk.Label(top, text="手型:").pack(side="left", padx=8)
        self.hand_lr_var = tk.IntVar(value=1)
        ttk.Radiobutton(top, text="右手", value=1, variable=self.hand_lr_var,
                        command=self._on_hand_lr_change).pack(side="left")
        ttk.Radiobutton(top, text="左手", value=0, variable=self.hand_lr_var,
                        command=self._on_hand_lr_change).pack(side="left")
        ttk.Label(top, text="（近节/侧摆错乱时切换手型）",
                  foreground="gray").pack(side="left", padx=4)

        ttk.Button(top, text="连接", command=self._connect).pack(side="left", padx=6)
        ttk.Button(top, text="断开", command=self._disconnect).pack(side="left")
        ttk.Button(top, text="连接性自检", command=self._check).pack(side="left", padx=6)
        ttk.Button(top, text="回零(homing)", command=self._homing).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(top, textvariable=self.status_var, foreground="blue").pack(side="left", padx=12)

        # 中间：16 关节滑条
        mid = ttk.LabelFrame(self.root, text="16 关节角度控制（弧度换算为电机指令，0xAA 力位混合）")
        mid.pack(fill="both", expand=True, padx=8, pady=4)

        cols = 4
        for i in range(JOINT_NUM):
            frame = ttk.Frame(mid)
            frame.grid(row=(i // cols) * 3, column=i % cols, sticky="nsew",
                       padx=6, pady=2)
            var = tk.DoubleVar(value=0.0)
            self.angle_vars.append(var)

            # 滑条范围按关节类型设置（手册角度范围，防侧摆超限/单向）：
            #   侧摆(关节 1,4,7,10,13) -20°~+20°；近节(2,5,8,11,14) 0~90°；
            #   远节(3,6,9,12,15) 0~75°；第16关节 0~110°
            lo, hi = slider_range_for_joint(i)
            ttk.Label(frame, text=f"{i+1:2d} {JOINT_NAMES_CN[i]}").pack(anchor="w")
            s = ttk.Scale(frame, from_=lo, to=hi, orient="horizontal",
                          variable=var, length=180,
                          command=lambda _v, idx=i: self._slider_changed(idx))
            s.pack(fill="x")
            self.sliders.append(s)
            ttk.Label(frame, textvariable=var).pack(anchor="e")

        # 底部：预设动作 + 单电机测试 + 状态
        bot = ttk.Frame(self.root)
        bot.pack(fill="x", padx=8, pady=4)
        ttk.Button(bot, text="张开 (open)", command=self._preset_open).pack(side="left", padx=4)
        ttk.Button(bot, text="握拳 (close)", command=self._preset_close).pack(side="left", padx=4)
        ttk.Button(bot, text="放松 (relax)", command=self._preset_relax).pack(side="left", padx=4)
        ttk.Button(bot, text="全部回零", command=self._preset_zero).pack(side="left", padx=4)
        ttk.Button(bot, text="开始/停止状态监视", command=self._toggle_monitor).pack(side="left", padx=12)

        # 单电机测试（排查"某电机无响应"，如中指远节电机9）
        ttk.Label(bot, text="单电机测试 ID:").pack(side="left", padx=(16, 2))
        self.motor_id_var = tk.IntVar(value=9)
        ttk.Spinbox(bot, from_=1, to=16, textvariable=self.motor_id_var,
                    width=4).pack(side="left")
        ttk.Label(bot, text="位置:").pack(side="left", padx=4)
        self.motor_pos_var = tk.IntVar(value=2048)
        ttk.Spinbox(bot, from_=0, to=4095, textvariable=self.motor_pos_var,
                    width=6).pack(side="left")
        ttk.Button(bot, text="测试电机", command=self._test_motor).pack(side="left", padx=6)
        ttk.Button(bot, text="查行程", command=self._check_motor_stroke).pack(side="left")

        self.monitor_var = tk.StringVar(value="状态: -")
        ttk.Label(bot, textvariable=self.monitor_var, foreground="green").pack(side="left", padx=8)

    # ------------------------------------------------------------------
    def _connect(self):
        try:
            if self.hand is not None:
                self._disconnect()
            self.hand = RYH1HandController(
                method=self.method_var.get(),
                rs485_port=self.port_var.get(),
                hand_lr=self.hand_lr_var.get(),
            )
            self.hand.open()
            self.status_var.set(f"已连接（{self.method_var.get()}）")
            logger.info("连接成功")
        except Exception as exc:
            messagebox.showerror("连接失败", str(exc))
            self.status_var.set("连接失败")

    def _disconnect(self):
        if self.hand is not None:
            self.hand.close()
            self.hand = None
        self.status_var.set("未连接")
        self._stop_monitor()

    def _on_hand_lr_change(self):
        """手型切换：已连接时立即生效（无需重连）。"""
        if self.hand is not None:
            self.hand.set_hand_lr(self.hand_lr_var.get())
            logger.info("手型切换为 %s", "右手" if self.hand_lr_var.get() else "左手")
            self.status_var.set(
                f"已连接（{self.method_var.get()}，手型={'右' if self.hand_lr_var.get() else '左'}手）")

    def _check(self):
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接")
            return
        try:
            res = self.hand.check_connection()
            if res["ok"]:
                msg = (f"连接正常：库版本 {res['version']}，{res['replies']}/16 电机有应答")
                if res["faults"]:
                    msg += "\n故障电机："
                    for mid, st, txt in res["faults"]:
                        msg += f"\n  电机{mid:2d}: 状态{st} [{txt}]"
                if res.get("need_homing"):
                    msg += ("\n\n⚠️ 存在【找零告警】电机：未完成回零 → 行程受限 → 动作几乎看不见。"
                            "\n点击【回零】按钮或运行 apps/diag_motor.py --fix-homing 修复")
                messagebox.showinfo("连接性自检", msg)
                self.status_var.set(f"OK：{res['replies']}/16 电机应答")
            else:
                messagebox.showwarning("连接性自检",
                                       f"0/16 电机应答。请检查：电源(24V/8A)、CAN/485 线、波特率 1M/5M")
                self.status_var.set("无应答")
        except Exception as exc:
            messagebox.showerror("自检异常", str(exc))

    def _homing(self):
        """执行回零（修复找零告警 status=11 导致的行程受限/动作看不见）。"""
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接")
            return
        if not messagebox.askyesno("回零", "将对 1~16 全部电机执行回零（归位动作），确认？"):
            return
        try:
            r = self.hand.homing(timeout_ms=1500, sleep_s=0.3)
            time.sleep(1.0)
            res = self.hand.check_connection()
            bad = [(m, st, t) for m, st, t in res["faults"] if st == 11]
            if bad:
                messagebox.showwarning("回零", f"仍有找零告警电机: {[m for m,_,_ in bad]}。"
                                               f"请检查机械是否卡住/电源是否足够")
            else:
                messagebox.showinfo("回零", "回零完成，无找零告警电机。请重新测试动作幅度。")
        except Exception as exc:
            messagebox.showerror("回零异常", str(exc))

    # ------------------------------------------------------------------
    def _slider_changed(self, idx: int):
        if self.hand is None:
            return
        angles = [0.0] * JOINT_NUM
        for i, var in enumerate(self.angle_vars):
            angles[i] = math.radians(var.get())
        try:
            self.hand.move_joints(angles)
        except Exception as exc:  # pragma: no cover
            logger.error("move_joints: %s", exc)

    def _test_motor(self):
        """单电机测试：给指定电机发位置指令（排查无响应，如电机9中指远节）。"""
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接")
            return
        mid = self.motor_id_var.get()
        pos = self.motor_pos_var.get()
        try:
            ret = self.hand.move_motor(mid, pos)
            # 回读状态确认响应
            info = self.hand.get_servo_info(mid, timeout_ms=200)
            msg = f"电机{mid} 指令位置={pos} 返回码={ret}"
            if info is not None:
                msg += f"\n回读: P={info.position} status={info.status}"
            else:
                msg += "\n⚠️ 无应答（该电机可能无响应/行程受限）"
            messagebox.showinfo("单电机测试", msg)
        except Exception as exc:
            messagebox.showerror("单电机测试异常", str(exc))

    def _check_motor_stroke(self):
        """读取电机行程（排查"幅度小/无响应"：行程应≈4095）。"""
        if self.hand is None:
            messagebox.showwarning("提示", "请先连接")
            return
        mid = self.motor_id_var.get()
        stroke = self.hand.get_stroke(mid)
        info = self.hand.get_servo_info(mid, timeout_ms=200)
        if stroke is None:
            messagebox.showwarning("行程", f"电机{mid} 行程读取失败（无应答）")
            return
        tip = "正常" if stroke >= 3000 else "⚠️ 行程偏小（<3000），该电机幅度会很小或无响应"
        msg = f"电机{mid} 行程 = {stroke}（应≈4095）\n{tip}"
        if info is not None:
            msg += f"\n当前位置 P={info.position} status={info.status}"
        messagebox.showinfo("电机行程", msg)

    def _preset_open(self):
        self._set_all(0.0); self._slider_changed_all()
        if self.hand: self.hand.open_hand()

    def _preset_close(self):
        # 标准握拳：侧摆全 0，所有手指近节+远节弯曲（与 hand.close_hand 一致）
        vals = [0, 50, 30,   0, 70, 60,   0, 70, 60,   0, 70, 60,   0, 70, 60,   0]
        self._set_all_list(vals)
        if self.hand: self.hand.close_hand()

    def _preset_relax(self):
        vals = [0, 30, 15,   0, 35, 25,   0, 35, 25,   0, 35, 25,   0, 35, 25,   0]
        self._set_all_list(vals)
        if self.hand: self.hand.relax()

    def _preset_zero(self):
        self._set_all(0.0)
        if self.hand: self.hand.open_hand()

    def _set_all(self, val: float):
        for var in self.angle_vars:
            var.set(val)

    def _set_all_list(self, vals: list):
        for i, var in enumerate(self.angle_vars):
            if i < len(vals):
                var.set(vals[i])

    def _slider_changed_all(self):
        for i in range(JOINT_NUM):
            self._slider_changed(i)

    # ------------------------------------------------------------------
    def _toggle_monitor(self):
        if self._monitor_job is not None:
            self._stop_monitor()
        else:
            self._monitor()

    def _monitor(self):
        if self.hand is None:
            self._stop_monitor()
            return
        try:
            angles = self.hand.read_joint_angles()
            deg = [math.degrees(a) for a in angles]
            self.monitor_var.set("状态: " + " ".join(f"{d:.0f}" for d in deg))
        except Exception as exc:  # pragma: no cover
            self.monitor_var.set(f"状态读取失败: {exc}")
        self._monitor_job = self.root.after(500, self._monitor)

    def _stop_monitor(self):
        if self._monitor_job is not None:
            self.root.after_cancel(self._monitor_job)
            self._monitor_job = None
        self.monitor_var.set("状态: -")

    # ------------------------------------------------------------------
    def _on_close(self):
        self._disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    HandGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
