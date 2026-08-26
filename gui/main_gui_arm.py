# -*- coding: utf-8 -*-
"""
main_gui_arm.py —— 综合控制界面（灵巧手 + Aubo K5 机械臂，TCP 坐标联动）

在原 gui/main_gui.py（仅灵巧手）基础上扩展，**不修改原文件**：
  * 继承 MainGui，完整保留：相机(USB/L515)、MediaPipe 姿态、精度后处理、
    灵巧手连接/校准/动作模仿/16 关节滑条；
  * 新增底部"机械臂控制"面板：
      - 连接（IP/端口/登录） + 上电/启动/断电 + 停止 + 拖拽示教 + 回初始位
      - 6 轴关节滑条（movej）与实时状态/关节角/TCP 位姿显示
      - 位姿输入 movel（TCP 系）
      - TCP 坐标联动：勾选后把"灵巧手安装偏移"写入机械臂 setTcpOffset，
        movel 的目标位姿即以灵巧手 TCP 为基准
      - "臂手联动"：机械臂 movel 到位后自动执行灵巧手预设动作（握拳/张开/放松）

用法：
  python -m gui.main_gui_arm

安全提示：
  * 首次连接建议速度比例 0.2~0.3（面板滑条可调）；
  * 运动前确认机械臂周围无人、无障碍物。
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

from gui.main_gui import MainGui, JOINT_NAMES_CN
from arm import AuboK5ArmController
from arm.arm_config import ARM_CONFIG, DOF


class MainGuiArm(MainGui):
    """扩展版主界面：灵巧手（继承 MainGui）+ Aubo K5 机械臂。"""

    def __init__(self, root: tk.Tk):
        # 先构建原灵巧手界面（相机/姿态/后处理/手控/布局）
        super().__init__(root)
        # 机械臂相关状态
        self.arm: AuboK5ArmController | None = None
        self.arm_connected = False
        self.arm_state_var = tk.StringVar(value="机械臂未连接")
        self._build_arm_ui()
        self._arm_poll_loop()

    # ==================================================================
    # 机械臂面板 UI
    # ==================================================================
    def _build_arm_ui(self):
        root = self.root
        # 机械臂面板占第 4 行（原界面 0~3 行不动）
        root.grid_rowconfigure(4, weight=0)
        frame = ttk.LabelFrame(root, text="Aubo K5 机械臂控制（TCP 坐标联动）")
        frame.grid(row=4, column=0, sticky="ew", padx=5, pady=2)

        # ---- 行 1：连接 + 速度 ----
        r1 = ttk.Frame(frame)
        r1.pack(fill="x", padx=4, pady=2)
        ttk.Label(r1, text="IP:").pack(side="left")
        self.arm_ip_var = tk.StringVar(value=ARM_CONFIG["ip"])
        ttk.Entry(r1, textvariable=self.arm_ip_var, width=14).pack(side="left", padx=2)
        ttk.Label(r1, text="端口:").pack(side="left")
        self.arm_port_var = tk.StringVar(value=str(ARM_CONFIG["rpc_port"]))
        ttk.Entry(r1, textvariable=self.arm_port_var, width=6).pack(side="left", padx=2)
        ttk.Button(r1, text="连接", command=self._arm_connect).pack(side="left", padx=4)
        ttk.Button(r1, text="断开", command=self._arm_disconnect).pack(side="left", padx=2)
        ttk.Label(r1, text="速度比例:").pack(side="left", padx=(14, 2))
        self.arm_fraction_var = tk.DoubleVar(value=ARM_CONFIG["speed_fraction"])
        tk.Scale(r1, from_=0.05, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                 variable=self.arm_fraction_var, length=160, showvalue=True,
                 command=lambda _v: self._arm_apply_fraction()).pack(side="left")
        ttk.Label(r1, textvariable=self.arm_state_var, foreground="blue").pack(side="left", padx=8)

        # ---- 行 2：电源/动作 ----
        r2 = ttk.Frame(frame)
        r2.pack(fill="x", padx=4, pady=2)
        ttk.Button(r2, text="上电+启动", command=self._arm_poweron).pack(side="left", padx=2)
        ttk.Button(r2, text="断电", command=self._arm_poweroff).pack(side="left", padx=2)
        ttk.Button(r2, text="停止", command=self._arm_stop).pack(side="left", padx=2)
        ttk.Button(r2, text="拖拽示教(开)", command=lambda: self._arm_freedrive(True)).pack(side="left", padx=2)
        ttk.Button(r2, text="拖拽示教(关)", command=lambda: self._arm_freedrive(False)).pack(side="left", padx=2)
        ttk.Button(r2, text="回初始位", command=self._arm_home).pack(side="left", padx=2)

        # ---- 行 3：6 轴关节滑条 + 状态 ----
        r3 = ttk.Frame(frame)
        r3.pack(fill="x", padx=4, pady=2)
        self.arm_joint_vars = []
        for i in range(DOF):
            f = ttk.Frame(r3)
            f.pack(side="left", padx=2)
            var = tk.DoubleVar(value=0.0)
            self.arm_joint_vars.append(var)
            ttk.Label(f, text=JOINT_NAMES_CN[i], font=("", 7)).pack(anchor="w")
            tk.Scale(f, from_=-175, to=175, resolution=1, orient=tk.HORIZONTAL,
                     variable=var, length=90, showvalue=False).pack()
            ttk.Label(f, textvariable=var, width=5, font=("", 7)).pack()
        ttk.Button(r3, text="执行 movej", command=self._arm_movej_from_sliders).pack(side="left", padx=4)
        self.arm_status_var = tk.StringVar(value="状态: -")
        ttk.Label(r3, textvariable=self.arm_status_var, font=("Consolas", 8),
                  foreground="green").pack(side="left", padx=8)

        # ---- 行 4：位姿输入 movel + TCP 联动 ----
        r4 = ttk.Frame(frame)
        r4.pack(fill="x", padx=4, pady=2)
        ttk.Label(r4, text="movel 位姿 [x,y,z,rx,ry,rz] (m/rad):").pack(side="left")
        self.arm_pose_vars = []
        for i in range(6):
            var = tk.StringVar(value="0.0")
            self.arm_pose_vars.append(var)
            ttk.Entry(r4, textvariable=var, width=7).pack(side="left", padx=1)
        ttk.Button(r4, text="执行 movel", command=self._arm_movel_from_entry).pack(side="left", padx=4)

        # TCP 联动区
        self.arm_link_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r4, text="TCP联动(灵巧手安装偏移)",
                        variable=self.arm_link_var,
                        command=self._arm_toggle_link).pack(side="left", padx=(14, 2))
        ttk.Button(r4, text="臂手联动:到位后握拳", command=self._arm_hand_link_fist).pack(side="left", padx=2)
        ttk.Button(r4, text="臂手联动:到位后张开", command=self._arm_hand_link_open).pack(side="left", padx=2)
        ttk.Button(r4, text="臂手联动:到位后放松", command=self._arm_hand_link_relax).pack(side="left", padx=2)

    # ==================================================================
    # 机械臂操作
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
                logger_warn(f"set speed fraction: {exc}")

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

    def _arm_movej_from_sliders(self):
        if not self._require_arm():
            return
        q = [math.radians(v.get()) for v in self.arm_joint_vars]
        ret, msg = self.arm.movej(q, block=True, timeout_s=30)
        self.arm_state_var.set(f"movej ret={ret} {msg or ''}")
        self._arm_refresh_state()

    def _arm_movel_from_entry(self):
        if not self._require_arm():
            return
        try:
            pose = [float(v.get()) for v in self.arm_pose_vars]
        except ValueError:
            messagebox.showerror("输入错误", "位姿必须是数字 [x,y,z,rx,ry,rz]")
            return
        ret, msg = self.arm.movel(pose, block=True, timeout_s=30)
        self.arm_state_var.set(f"movel ret={ret} {msg or ''}")
        self._arm_refresh_state()

    def _arm_toggle_link(self):
        """TCP 坐标联动：勾选后把灵巧手安装偏移写入机械臂 setTcpOffset。"""
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
                self.arm.apply_tcp_offset([0.0] * 6)   # 关联动 = 基础 TCP
                self.arm_state_var.set("TCP 联动已关闭（位姿=法兰 TCP）")
        except Exception as exc:
            messagebox.showerror("TCP 联动失败", str(exc))

    def _arm_hand_link(self, hand_action: str):
        """臂手联动：先机械臂 movel 到面板输入的位姿，再执行灵巧手动作。"""
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
        """每 800ms 刷新机械臂状态（Tk after 常驻调度，非阻塞）。"""
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


def logger_warn(msg: str):
    import logging
    logging.getLogger("main_gui_arm").warning(msg)


def main():
    root = tk.Tk()
    MainGuiArm(root)
    root.mainloop()


if __name__ == "__main__":
    main()
