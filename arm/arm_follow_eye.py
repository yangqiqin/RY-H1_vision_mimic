# -*- coding: utf-8 -*-
"""
arm_follow_eye.py —— 眼在手上（eye-in-hand）跟随控制（增量跟随 + 安全 + 失手急停）

功能：
  实现"手腕识别 → 机械臂末端相对运动"的实时跟随：
  1. 相机（L515）检测手腕中心点（相机系 3D）
  2. 手眼标定（vision/hand_eye.py）把手腕转到【机械臂基座系】
  3. 与上一帧基座坐标做差 → 增量 ΔP（米）
  4. 单帧限幅（默认 5mm/帧，防视觉噪声猛冲）
  5. 目标 = 机械臂当前位置 + 限幅增量，姿态固定（锁死末端 RPY）
  6. 安全框裁剪（arm/arm_safety.py）：超出安全区 → 拉回/拒绝
  7. **丢失手 → 立即停止机械臂**（安全红线）

安全逻辑（用户硬性要求，务必保留）：
  * 如果连续 N 帧（默认 5）检测不到手 → 立即调用 stop_move() 强制停止机械臂；
  * 每次运动前先检查安全框，目标越界 → 不执行并告警；
  * 增量单帧限幅（默认 0.005m）+ 速度比例限制（0.2 起步）→ 防猛冲；
  * 姿态固定（默认 RPY=[π,0,0] 朝下）→ 末端退化为纯平移，路径可预测。

用法：
  from arm.arm_follow_eye import EyeInHandFollower
  f = EyeInHandFollower(arm, hand_eye, safety_box)
  f.begin()                            # 初始化基准（记录初始末端位姿）
  f.update(wrist_3d_cam)               # 每帧：输入手腕相机系坐标
      # 内部：转基座 → 增量 → 限幅 → 安全框 → movel
  f.stop()                             # 停止跟随（急停）
"""

from __future__ import annotations

import logging
import math
import time
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("arm_follow_eye")

# 默认参数
DEFAULT_MAX_STEP_M = 0.005     # 单帧最大位移增量（米）——防猛冲
DEFAULT_LOST_FRAMES = 5        # 连续丢手多少帧触发急停
DEFAULT_BOUND_STOP_FRAMES = 8  # 连续越界（安全框拦截）多少帧触发急停
DEFAULT_FIXED_RPY = [math.pi, 0.0, -0.436]   # 固定末端姿态（朝下）
DEFAULT_MOVE_TIMEOUT = 2.0     # 单次 movel 超时（秒，非阻塞等待）


class EyeInHandFollower:
    """
    眼在手上跟随控制器：手腕下移多少 → 机械臂末端就下移多少（相对增量）。
    """

    def __init__(self, arm, hand_eye, safety_box,
                 max_step_m: float = DEFAULT_MAX_STEP_M,
                 lost_frames: int = DEFAULT_LOST_FRAMES,
                 fixed_rpy: Optional[List[float]] = None,
                 max_speed: float = 0.15,
                 bound_stop_frames: int = DEFAULT_BOUND_STOP_FRAMES):
        """
        Args:
            arm: 机械臂控制器（AuboK5ArmController，需 movej/movel/stop_move/get_tcp_pose）
            hand_eye: 手眼标定转换器（HandEyeCalibration）
            safety_box: 安全框（ArmSafetyBox）
            max_step_m: 单帧最大位移增量（米）
            lost_frames: 连续丢手帧数阈值（触发急停）
            fixed_rpy: 固定末端姿态（弧度）[rx,ry,rz]
            max_speed: 运动速度上限（米/秒）
            bound_stop_frames: 连续越界（安全框拦截）帧数阈值（触发急停，防贴边）
        """
        self.arm = arm
        self.he = hand_eye
        self.safe = safety_box
        self.max_step = float(max_step_m)
        self.lost_frames = int(lost_frames)
        self.fixed_rpy = list(fixed_rpy) if fixed_rpy else list(DEFAULT_FIXED_RPY)
        self.max_speed = float(max_speed)
        self.bound_stop_frames = int(bound_stop_frames)

        self._running = False
        self._last_wrist_base: Optional[np.ndarray] = None
        self._lost_count = 0
        self._bound_count = 0
        self._moved_count = 0
        self._start_time = 0.0

        # 状态统计（GUI 显示）
        self.stats = {
            "running": False,
            "lost_count": 0,
            "moved_count": 0,
            "last_delta": [0.0, 0.0, 0.0],
            "last_target": None,
            "last_status": "未启动",
        }

    # ------------------------------------------------------------------
    def begin(self):
        """开始跟随：记录当前末端位姿为基准，清零丢手计数。"""
        self._running = True
        self._last_wrist_base = None
        self._lost_count = 0
        self._moved_count = 0
        self._start_time = time.time()
        self.stats.update({"running": True, "lost_count": 0, "moved_count": 0,
                           "last_status": "跟随中"})
        logger.info("[eye-follow] 开始跟随")

    def stop(self, emergency: bool = False):
        """停止跟随。emergency=True 时先强制停止机械臂（失手急停/用户急停）。"""
        self._running = False
        if emergency:
            try:
                self.arm.stop_move()
                logger.warning("[eye-follow] ⚠️ 急停：已强制停止机械臂")
            except Exception as exc:
                logger.error("[eye-follow] 急停失败: %s", exc)
        self.stats.update({"running": False, "last_status": "急停" if emergency else "已停止"})
        logger.info("[eye-follow] 停止跟随%s", "（急停）" if emergency else "")

    @property
    def running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    def update(self, wrist_3d_cam: Optional[List[float]],
               block: bool = False) -> Tuple[bool, str]:
        """
        每帧调用：输入手腕在【相机系】的 3D 坐标（米，可为 None=未检测到手）。

        返回 (执行了运动?, 状态说明)。
        """
        if not self._running:
            return False, "未在跟随状态"
        if not hasattr(self.arm, "get_tcp_pose"):
            return False, "机械臂未连接/不支持读位姿"

        # ---- 1. 丢手检测（安全红线） ----
        if wrist_3d_cam is None:
            self._lost_count += 1
            self.stats["lost_count"] = self._lost_count
            if self._lost_count >= self.lost_frames:
                self.stop(emergency=True)
                return False, f"⚠️ 连续 {self._lost_count} 帧未检测到手 → 已急停"
            self.stats["last_status"] = f"丢手 {self._lost_count}/{self.lost_frames}（即将急停）"
            return False, self.stats["last_status"]
        self._lost_count = 0

        # ---- 2. 手腕 相机系 → 基座系 ----
        try:
            wrist_base = self.he.camera_to_base(np.array(wrist_3d_cam[:3]), self.arm)
        except Exception as exc:
            self.stats["last_status"] = f"坐标转换失败: {exc}"
            return False, self.stats["last_status"]

        # ---- 3. 增量（相对上一帧） ----
        if self._last_wrist_base is None:
            self._last_wrist_base = wrist_base
            self.stats["last_status"] = "基准建立（首帧）"
            return False, self.stats["last_status"]
        delta = wrist_base - self._last_wrist_base
        self._last_wrist_base = wrist_base

        # ---- 4. 单帧限幅（防猛冲） ----
        delta_norm = float(np.linalg.norm(delta))
        if delta_norm > self.max_step:
            delta = delta / delta_norm * self.max_step
            delta_norm = self.max_step
        if delta_norm < 1e-5:
            self.stats["last_status"] = "手腕静止"
            return False, "手腕静止"

        # ---- 5. 目标 = 当前位置 + 增量（基座系，法兰位姿） ----
        try:
            # 用法兰位姿（与 hand_eye 坐标转换一致：手腕基座坐标基于法兰系）
            if hasattr(self.arm, "get_flange_pose"):
                cur = self.arm.get_flange_pose()
            else:
                cur = self.arm.get_tcp_pose()
        except Exception as exc:
            self.stats["last_status"] = f"读当前位置失败: {exc}"
            return False, self.stats["last_status"]
        target_xyz = np.array(cur[:3]) + delta

        # ---- 6. 安全框检查（防剐蹭，安全红线） ----
        # 目标越界 → 拒绝本次运动并告警（绝不 clamp 后继续运动，避免顶在边界反复碰撞）
        target_full = list(target_xyz) + list(self.fixed_rpy)
        ok_box, box_msg = self.safe.check_pose(target_xyz, margin=0.005)
        if not ok_box:
            self._bound_count += 1
            self.stats["bound_count"] = self._bound_count
            self.stats["last_status"] = f"⚠️ 安全框拦截: {box_msg}"
            logger.warning("[eye-follow] 安全框拦截: %s", box_msg)
            # 连续越界达到阈值 → 急停（防止一直贴边）
            if self._bound_count >= self.bound_stop_frames:
                self.stop(emergency=True)
                self.stats["last_status"] = f"⚠️ 连续越界 {self._bound_count} 帧 → 已急停"
            return False, self.stats["last_status"]
        self._bound_count = 0

        # ---- 7. 下发运动（非阻塞） ----
        try:
            self.arm.movel(target_full, speed=self.max_speed, acc=self.max_speed * 0.8,
                           block=block, timeout_s=DEFAULT_MOVE_TIMEOUT)
            self._moved_count += 1
            self.stats.update({
                "moved_count": self._moved_count,
                "last_delta": [round(float(v), 4) for v in delta],
                "last_target": [round(float(v), 4) for v in target_full],
                "last_status": f"跟随中 Δ={delta_norm*1000:.1f}mm",
            })
            return True, self.stats["last_status"]
        except Exception as exc:
            self.stats["last_status"] = f"movel 失败: {exc}"
            logger.error("[eye-follow] movel 失败: %s", exc)
            return False, self.stats["last_status"]

    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        return dict(self.stats)


if __name__ == "__main__":
    # 自测：纯逻辑验证（无硬件，模拟机械臂）
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    class FakeArm:
        def __init__(self):
            self.pos = [0.5, 0.0, 0.4, math.pi, 0.0, 0.0]
            self.moves = []

        def get_flange_pose(self):
            return list(self.pos)

        def get_tcp_pose(self):
            return list(self.pos)

        def movel(self, pose, speed=None, acc=None, block=False, timeout_s=None):
            self.moves.append(list(pose))
            return 0, None

        def stop_move(self):
            self.moves.append("STOP")

    from vision.hand_eye import HandEyeCalibration
    from arm.arm_safety import ArmSafetyBox

    arm = FakeArm()
    he = HandEyeCalibration()
    safe = ArmSafetyBox()
    f = EyeInHandFollower(arm, he, safe)
    f.begin()
    # 首帧（建基准）
    ok, msg = f.update([0.0, 0.0, 0.5])
    print(f"首帧: {msg}")
    # 手腕下移 2cm（相机系 z 增 0.02 → 基座系应下移）
    ok, msg = f.update([0.0, 0.0, 0.52])
    print(f"第二帧: ok={ok} {msg} moves={len(arm.moves)}")
    # 丢手 → 急停
    for i in range(6):
        ok, msg = f.update(None)
    print(f"丢手后: {msg}")
    assert "STOP" in arm.moves, "丢手应触发急停"
    print("EyeInHandFollower 自测通过（丢手急停 OK）")
