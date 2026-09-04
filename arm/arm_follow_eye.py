# -*- coding: utf-8 -*-
"""
arm_follow_eye.py —— 眼在手上（eye-in-hand）跟随控制（增量跟随 + 硬安全 + 碰撞急停）

功能：
  实现"手腕识别 → 机械臂末端相对运动"的实时跟随（3D，幅度 1:1）：
  1. 相机（L515）检测手腕中心点（相机系 3D）
  2. 手眼标定（vision/hand_eye.py）把手腕转到【机械臂基座系】
  3. 【锚点追位】跟随开始建锚：期望目标 = 锚点末端 + (手腕当前 − 锚点手腕)（基座系 3D）
     —— 手移动多少末端追多少；手停后机械臂继续追赶直到 1:1 到位，位移不丢失
  4. 相机系窗口防抖：单帧跳变/窗口累计位移 ≥ 阈值才判"手在动"，微抖不跟、坏点忽略
  5. 每帧追赶步限幅（默认 5mm/帧，防猛冲；未追完的后续帧继续追）
  6. 高度安全区（基坐标系 z，xy 不计入）【强制生效】：期望点与路径 z 全程检查
  7. 碰撞/受阻检测：关节力矩超阈值 / 运动停滞 / 末端姿态偏离 → 立即急停

★★★ 末端三个关节锁腕机制（用户核心设计）★★★
  问题根源：moveLine 笛卡尔插值到达目标时，SDK 常"不自觉"调用末端三个关节（J4/J5/J6）来
  分摊位移 → 相机/灵巧手（装在末端）方向被带偏，"末端姿态固定"失败。
  本实现【默认不再用 moveLine】，改为关节级锁腕运动（motion_mode="wrist_lock"）：
    a. begin() 时读取当前关节角，锁定末端三个关节：locked_wrist = [J4, J5, J6]
    b. 每帧目标 = 当前位置 + 限幅增量（姿态仍是世界系固定 fixed_rpy）
    c. 逆解：以"当前关节角但腕钉在 locked_wrist"为参考角，对目标位姿做 IK
    d. 校验（两级容差）：IK 解出的 J4/5/6 与 locked_wrist 偏差 ≤ wrist_tol_deg
       （默认 3°，GUI 可调）→ 直接跟随；≤ wrist_hard_deg（默认 15°）→ 缩步软降级继续；
       > 硬限才判定不可达（奇异/边界）→ 计数急停；
       再正解 FK 校验该关节解的实际末端位置与目标偏差 ≤ 2mm
    e. 两者都过 → movej 下发（末端三关节几乎不动，方向由 IK 位姿保证绝对不变）

★★★ 安全红线 ★★★
  A. 末端姿态硬锁：每帧读取实际姿态，与固定姿态偏差 > 2° → 判定异常/碰撞 → 立即急停。
  B. 高度安全区强制生效（基坐标系，仅 z）：目标或路径 z 越界 → 立即 hard_stop 急停
  C. 碰撞检测（运动受阻）：同时监测力矩超阈值 / 位置停滞 / SDK 报错 → 立即急停。
  D. 失手急停：连续 lost_frames 帧检测不到手 → 立即急停。
  E. 锁腕保护：目标点需要转动末端三关节才能到达 → 连续 wrist_unreach_frames 帧 → 急停
"""

from __future__ import annotations

import logging
import math
import time
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("arm_follow_eye")

# 默认参数
DEFAULT_MAX_STEP_M = 0.01       # 单帧最大垂向位移增量（米=10mm/帧）——流畅第一，每帧走更大步
                                # 配合 GUI"限幅mm/帧"；垂直跟随只在 z 方向，故不再怕 x/y 噪声
DEFAULT_LOST_FRAMES = 5         # 连续丢手多少帧触发急停
DEFAULT_BOUND_STOP_FRAMES = 6   # 连续越界多少帧触发急停（3→6：降低误急停；越界仍持续拦截运动）
DEFAULT_RPY_TOLERANCE_DEG = 3.0  # 末端姿态允许偏差（度，按逐轴 wrap 后比较，防 ±π 翻转误报）
DEFAULT_TORQUE_THRESHOLD = 15.0  # 关节力矩阈值（N·m，8→15：K5 带负载加减速常超 8，需连续2帧才急停）
DEFAULT_STALL_FRAMES = 8         # 运动停滞帧数（需超过 STALL_MIN_ELAPSED_S 才计入）
DEFAULT_FIXED_RPY = [math.pi, 0.0, -0.436]   # 固定末端姿态（弧度）
DEFAULT_MOVE_TIMEOUT = 2.0       # 单次 movel 超时（秒）
DEFAULT_CAM_STILL_M = 0.008      # 相机系静止阈值（米）
TORQUE_PEAK_FRAMES = 2           # 力矩连续超阈值帧数（过滤单帧尖峰）
STALL_MIN_ELAPSED_S = 0.5        # stall 判定最短已下发时长（秒）：下发后不足此时间不算停滞
STALL_MOVED_M = 0.0003           # stall：实际位移 <0.3mm 才算几乎不动
MOVE_FAIL_SOFT_FRAMES = 8        # movej 瞬时错误（BUSY/未就绪类）连续软失败上限，超过才急停
# movej/movel 瞬时类错误码：跳过本帧不立即急停（SDK 忙/未就绪等），其它错误码才急停
TRANSIENT_MOVE_RETS = frozenset({1, 3, 203, 210, 212, 218, 219, 236})

# ---- 末端三关节锁腕 ----
MOTION_MODE_WRIST_LOCK = "wrist_lock"
MOTION_MODE_CARTESIAN = "cartesian"
DEFAULT_MOTION_MODE = MOTION_MODE_WRIST_LOCK

# ★ 软容差（默认3°）
DEFAULT_WRIST_TOL_DEG = 3.0

# ★ 各关节独立硬限（最大值可设为90°，GUI可调）
DEFAULT_WRIST_HARD_J4_DEG = 30.0   # J4 硬限（度）——腕部俯仰
DEFAULT_WRIST_HARD_J5_DEG = 30.0   # J5 硬限（度）——腕部旋转
DEFAULT_WRIST_HARD_J6_DEG = 30.0   # J6 硬限（度）——前臂旋转

DEFAULT_WRIST_UNREACH_FRAMES = 8
DEFAULT_IK_POS_ERR_M = 0.002
JOINT_LOCK_SCALES = (1.0, 0.5, 0.25, 0.125)
JOINT_LOCK_SPEED_DEG = 45.0
JOINT_LOCK_ACC_DEG = 90.0
CAM_WINDOW_FRAMES = 15
# ★ 垂直(Z)跟随：不再用"深度差大"丢弃任何帧（真实运动不可能垂直，抖动不是丢帧理由）。
# 运动判定仅用 z 分量：单帧 |Δz|≥cam_still，或窗口累计 |Δz|≥Z_WIN_M。
CAM_BAD_JUMP_M = 0.15     # 保留常量仅为兼容；算法中已不使用"突跳丢弃"
Z_WIN_M = 0.015           # z 窗口累计移动阈值（米）≈ 15mm/0.5s 判定手在动
STEP_DONE_M = 0.001
# 每帧丢弃/忽略原因计数（GUI HUD 显示，用于判断"是否误丢了手的动作"）
DROP_KEYS = ("bad_jump", "bad_point", "static", "busy", "lost", "done")


class EyeInHandFollower:
    """
    眼在手上跟随控制器：手腕下移多少 → 机械臂末端就下移多少（相对增量）。
    内置完整安全链：姿态硬锁 + 末端三关节锁腕 + 安全框强制 + 碰撞/受阻检测 + 失手急停。

    ★ 各关节可独立设置硬限（J4/J5/J6，GUI可调，最大90°）
    """

    def __init__(self, arm, hand_eye, safety_box,
                 max_step_m: float = DEFAULT_MAX_STEP_M,
                 lost_frames: int = DEFAULT_LOST_FRAMES,
                 fixed_rpy: Optional[List[float]] = None,
                 max_speed: float = 0.15,
                 bound_stop_frames: int = DEFAULT_BOUND_STOP_FRAMES,
                 rpy_tolerance_deg: float = DEFAULT_RPY_TOLERANCE_DEG,
                 torque_threshold: float = DEFAULT_TORQUE_THRESHOLD,
                 stall_frames: int = DEFAULT_STALL_FRAMES,
                 cam_still_m: float = DEFAULT_CAM_STILL_M,
                 motion_mode: str = DEFAULT_MOTION_MODE,
                 wrist_tol_deg: float = DEFAULT_WRIST_TOL_DEG,
                 wrist_hard_j4_deg: float = DEFAULT_WRIST_HARD_J4_DEG,  # ★ J4 独立硬限
                 wrist_hard_j5_deg: float = DEFAULT_WRIST_HARD_J5_DEG,  # ★ J5 独立硬限
                 wrist_hard_j6_deg: float = DEFAULT_WRIST_HARD_J6_DEG,  # ★ J6 独立硬限
                 wrist_unreach_frames: int = DEFAULT_WRIST_UNREACH_FRAMES):
        """
        Args:
            arm: 机械臂控制器
            hand_eye: 手眼标定转换器
            safety_box: 安全框
            max_step_m: 单帧最大位移增量（米）
            lost_frames: 连续丢手帧数阈值
            fixed_rpy: 固定末端姿态（弧度）[rx,ry,rz]
            max_speed: 运动速度上限（米/秒，仅 cartesian 模式）
            bound_stop_frames: 连续越界帧数阈值
            rpy_tolerance_deg: 末端姿态允许偏差（度）
            torque_threshold: 关节力矩碰撞阈值（N·m）
            stall_frames: 运动停滞帧数阈值
            cam_still_m: 相机系静止阈值（米）
            motion_mode: "wrist_lock"（默认）| "cartesian"
            wrist_tol_deg: 锁腕软容差（度，默认3.0）
            wrist_hard_j4_deg: ★ J4 硬限（度，GUI可调，默认30°）
            wrist_hard_j5_deg: ★ J5 硬限（度，GUI可调，默认30°）
            wrist_hard_j6_deg: ★ J6 硬限（度，GUI可调，默认30°）
            wrist_unreach_frames: 连续"锁腕硬不可达"帧数阈值
        """
        self.arm = arm
        self.he = hand_eye
        self.safe = safety_box
        self.max_step = float(max_step_m)
        self.lost_frames = int(lost_frames)
        self.fixed_rpy = list(fixed_rpy) if fixed_rpy else list(DEFAULT_FIXED_RPY)
        self.max_speed = float(max_speed)
        self.bound_stop_frames = int(bound_stop_frames)
        self.rpy_tolerance = math.radians(float(rpy_tolerance_deg))
        self.torque_threshold = float(torque_threshold)
        self.stall_frames = int(stall_frames)
        self.cam_still = float(cam_still_m)
        self.motion_mode = motion_mode
        if self.motion_mode not in (MOTION_MODE_WRIST_LOCK, MOTION_MODE_CARTESIAN):
            logger.warning("[eye-follow] 未知 motion_mode=%r，回退 wrist_lock", motion_mode)
            self.motion_mode = MOTION_MODE_WRIST_LOCK

        # ★ 软容差（J4/J5/J6 共用）
        self.wrist_tol = math.radians(float(wrist_tol_deg))

        # ★ 各关节独立硬限（最大值限制为90°）
        hard_j4 = min(float(wrist_hard_j4_deg), 90.0)
        hard_j5 = min(float(wrist_hard_j5_deg), 90.0)
        hard_j6 = min(float(wrist_hard_j6_deg), 90.0)
        self.wrist_hard_j4 = math.radians(max(hard_j4, float(wrist_tol_deg)))
        self.wrist_hard_j5 = math.radians(max(hard_j5, float(wrist_tol_deg)))
        self.wrist_hard_j6 = math.radians(max(hard_j6, float(wrist_tol_deg)))

        self.wrist_unreach_frames = int(wrist_unreach_frames)

        self._running = False
        self._last_wrist_base: Optional[np.ndarray] = None
        self._lost_count = 0
        self._bound_count = 0
        self._stall_count = 0
        self._unreach_count = 0
        self._torque_peak_count = 0      # 力矩连续超阈值帧计数（过滤尖峰）
        self._last_cmd_time = 0.0        # 上次成功下发运动的时间
        self._move_fail_count = 0        # movej 瞬时错误连续次数
        self._last_cmd_xyz: Optional[np.ndarray] = None
        self._last_actual_xyz: Optional[np.ndarray] = None
        self._moved_count = 0
        self._start_time = 0.0
        self.emergency_triggered = False

        # ---- 末端三关节锁腕状态 ----
        self._locked_wrist: Optional[List[float]] = None
        self._wrist_lock_ok = False
        self._wrist_dev_last_deg = 0.0

        # ---- 垂直(Z)锚点追踪状态 ----
        self._z_win: List[float] = []        # 相机深度(z)窗口（运动判定，xy 不参与）
        self._last_cam_z: Optional[float] = None
        self._anchor_end_xyz: Optional[np.ndarray] = None
        self._anchor_wrist_base: Optional[np.ndarray] = None
        self._desired_xyz: Optional[np.ndarray] = None

        # ---- 帧统计（GUI HUD：总帧数 / 各类丢弃计数） ----
        self._frames_total = 0
        self._drops = {k: 0 for k in DROP_KEYS}

        # 状态统计
        self.stats = {
            "running": False,
            "lost_count": 0,
            "bound_count": 0,
            "stall_count": 0,
            "unreach_count": 0,
            "moved_count": 0,
            "last_delta": [0.0, 0.0, 0.0],
            "last_target": None,
            "last_status": "未启动",
            "emergency": "",
            "motion_mode": self.motion_mode,
            "locked_wrist_deg": None,
            "wrist_dev_deg": 0.0,
            "hand_moving": False,
            "desired_xyz": None,
            "step_remaining_mm": 0.0,
            # ★ 新增：显示各关节硬限值
            "wrist_hard_j4_deg": round(math.degrees(self.wrist_hard_j4), 1),
            "wrist_hard_j5_deg": round(math.degrees(self.wrist_hard_j5), 1),
            "wrist_hard_j6_deg": round(math.degrees(self.wrist_hard_j6), 1),
            # ★ 新增：显示各关节当前偏差
            "dev_j4_deg": 0.0,
            "dev_j5_deg": 0.0,
            "dev_j6_deg": 0.0,
        }

    # ------------------------------------------------------------------
    def begin(self):
        """开始跟随：锁定末端姿态 + 锁定末端三个关节(J4/J5/J6)。"""
        self._running = True
        self._last_wrist_base = None
        self._lost_count = 0
        self._bound_count = 0
        self._stall_count = 0
        self._unreach_count = 0
        self._torque_peak_count = 0
        self._last_cmd_time = 0.0
        self._move_fail_count = 0
        self._last_cmd_xyz = None
        self._last_actual_xyz = None
        self._moved_count = 0
        self.emergency_triggered = False
        self._start_time = time.time()
        self._z_win = []
        self._last_cam_z = None
        self._anchor_end_xyz = None
        self._anchor_wrist_base = None
        self._desired_xyz = None

        # ---- 末端三关节锁腕初始化 ----
        self._locked_wrist = None
        self._wrist_lock_ok = False
        if self.motion_mode == MOTION_MODE_WRIST_LOCK:
            try:
                q = self.arm.get_joint_positions()
                if q is not None and len(q) >= 6:
                    self._locked_wrist = [float(v) for v in q[3:6]]
                    self._wrist_lock_ok = True
                else:
                    logger.error("[eye-follow] 锁腕初始化失败：读关节角返回 %s", q)
            except Exception as exc:
                logger.error("[eye-follow] 锁腕初始化异常: %s", exc)
            if self._wrist_lock_ok:
                logger.info("[eye-follow] 末端三关节已锁定 J4/5/6=%s deg",
                            [round(math.degrees(v), 1) for v in self._locked_wrist])
            else:
                self.stats.update({
                    "running": True, "moved_count": 0,
                    "last_status": "锁腕模式初始化失败（读关节角失败），禁止运动",
                    "emergency": ""})
                return

        self.stats.update({"running": True, "lost_count": 0, "bound_count": 0,
                           "stall_count": 0, "unreach_count": 0, "moved_count": 0,
                           "last_status": "跟随中（姿态已硬锁，腕关节已锁）", "emergency": "",
                           "motion_mode": self.motion_mode,
                           "locked_wrist_deg": ([round(math.degrees(v), 2)
                                                for v in self._locked_wrist]
                                               if self._locked_wrist else None),
                           "wrist_hard_j4_deg": round(math.degrees(self.wrist_hard_j4), 1),
                           "wrist_hard_j5_deg": round(math.degrees(self.wrist_hard_j5), 1),
                           "wrist_hard_j6_deg": round(math.degrees(self.wrist_hard_j6), 1)})
        logger.info("[eye-follow] 开始跟随（mode=%s），固定姿态 RPY=%s",
                    self.motion_mode,
                    [round(math.degrees(v), 1) for v in self.fixed_rpy])
        logger.info("[eye-follow] 锁腕硬限: J4=%.1f°, J5=%.1f°, J6=%.1f°",
                    math.degrees(self.wrist_hard_j4),
                    math.degrees(self.wrist_hard_j5),
                    math.degrees(self.wrist_hard_j6))

    def stop(self, emergency: bool = False, reason: str = ""):
        """停止跟随。emergency=True 时执行【硬停止】。"""
        self._running = False
        if emergency:
            self._hard_stop(reason)
        self.stats.update({"running": False,
                           "last_status": f"急停: {reason}" if emergency else "已停止",
                           "emergency": reason if emergency else ""})
        logger.warning("[eye-follow] 停止跟随%s%s",
                       "（急停）" if emergency else "", f" 原因: {reason}" if reason else "")

    def _hard_stop(self, reason: str):
        """硬停止：优先用 arm.hard_stop，失败回退 stop_move。"""
        if self.emergency_triggered:
            return
        self.emergency_triggered = True
        try:
            if hasattr(self.arm, "hard_stop"):
                ok = self.arm.hard_stop(retries=5, delay_s=0.05)
                if not ok:
                    logger.error("[eye-follow] ⚠️ hard_stop 未能确认停止！原因: %s", reason)
            else:
                self.arm.stop_move()
            logger.warning("[eye-follow] ⚠️ 急停已触发: %s", reason)
        except Exception as exc:
            logger.error("[eye-follow] 急停失败: %s", exc)

    @property
    def running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    def _check_emergency(self, pose: Optional[list] = None) -> Tuple[bool, str]:
        """碰撞/异常检测：力矩超阈值(连续2帧) / 运动停滞(带时间窗) / 姿态偏离(wrap) → 急停。

        Args:
            pose: 本帧已读到的法兰位姿（复用之，避免这里再 RPC 读一次——实时性优化）。
                  None 时才自行读取。
        """
        # 0) 准备位姿（一次读取，姿态/停滞共用）
        cur = pose
        if cur is None:
            try:
                if hasattr(self.arm, "get_flange_pose"):
                    cur = self.arm.get_flange_pose()
                elif hasattr(self.arm, "get_tcp_pose"):
                    cur = self.arm.get_tcp_pose()
            except Exception:
                cur = None

        # 1) 关节力矩碰撞检测（连续 TORQUE_PEAK_FRAMES 帧超阈值才急停，过滤加减速单帧尖峰）
        if hasattr(self.arm, "get_joint_torques"):
            try:
                torques = self.arm.get_joint_torques()
                if torques is not None:
                    max_t = max(abs(float(t)) for t in torques)
                    if max_t > self.torque_threshold:
                        self._torque_peak_count += 1
                        if self._torque_peak_count >= TORQUE_PEAK_FRAMES:
                            self.stop(emergency=True,
                                      reason=f"碰撞/受阻: 关节力矩 {max_t:.1f}N·m 连续"
                                             f"{self._torque_peak_count}帧超阈值 {self.torque_threshold}")
                            return False, self.stats["last_status"]
                    else:
                        self._torque_peak_count = 0
            except Exception:
                pass

        # 2) 运动停滞检测（时间窗：下发后 <STALL_MIN_ELAPSED_S 不判停滞，避免慢轮询误报）
        if self._last_cmd_xyz is not None and self._last_actual_xyz is not None and cur is not None:
            try:
                since_cmd = time.time() - self._last_cmd_time
                if since_cmd >= STALL_MIN_ELAPSED_S:
                    cmd_moved = float(np.linalg.norm(self._last_cmd_xyz - self._last_actual_xyz))
                    if cmd_moved > 0.001:
                        cur_xyz = np.array(cur[:3])
                        moved = float(np.linalg.norm(cur_xyz - self._last_actual_xyz))
                        if moved < STALL_MOVED_M:
                            self._stall_count += 1
                            self.stats["stall_count"] = self._stall_count
                            if self._stall_count >= self.stall_frames:
                                self.stop(emergency=True,
                                          reason=f"运动受阻/停滞: 下发{since_cmd:.1f}s后"
                                                 f"连续{self._stall_count}帧位置几乎不动")
                                return False, self.stats["last_status"]
                        else:
                            self._stall_count = 0
                else:
                    self._stall_count = 0
            except Exception:
                pass

        # 3) 末端姿态硬锁检测（逐分量 wrap 到 ±π 后比范数：
        #    朝下位姿 rx≈π 时 SDK RPY 可能在 π/−π 间跳号，直接求差会误报 360°）
        if cur is not None:
            try:
                cur_rpy = np.array(cur[3:6])
                diff = cur_rpy - np.array(self.fixed_rpy)
                diff = (diff + math.pi) % (2.0 * math.pi) - math.pi   # wrap → [-π, π]
                dev = float(np.linalg.norm(diff))
                if dev > self.rpy_tolerance:
                    self.stop(emergency=True,
                              reason=f"末端姿态偏离: 偏差 {math.degrees(dev):.1f}° > 阈值 "
                                     f"{math.degrees(self.rpy_tolerance):.1f}°（姿态未锁定！）")
                    return False, self.stats["last_status"]
            except Exception:
                pass
        return True, ""

    # ------------------------------------------------------------------
    def _read_end_xyz(self) -> Optional[np.ndarray]:
        """读当前【法兰】位置（基座系，米，3D）。"""
        try:
            if hasattr(self.arm, "get_flange_pose"):
                cur = self.arm.get_flange_pose()
            else:
                cur = self.arm.get_tcp_pose()
        except Exception as exc:
            logger.error("[eye-follow] 读当前位置失败: %s", exc)
            return None
        if cur is None or len(cur) < 3:
            return None
        xyz = np.array(cur[:3], dtype=np.float64)
        if not np.all(np.isfinite(xyz)) or np.any(np.abs(xyz) > 3.0):
            logger.error("[eye-follow] 末端位置读数异常: %s", xyz)
            return None
        return xyz

    # ------------------------------------------------------------------
    def update(self, wrist_3d_cam: Optional[List[float]],
               block: bool = False) -> Tuple[bool, str]:
        """每帧调用：输入手腕在【相机系】的 3D 坐标。"""
        self._frames_total += 1
        if not self._running:
            return False, "未在跟随状态"
        if self.motion_mode == MOTION_MODE_WRIST_LOCK and not self._wrist_lock_ok:
            return False, "锁腕模式未就绪（读关节角失败），禁止运动"
        if not hasattr(self.arm, "get_flange_pose") and not hasattr(self.arm, "get_tcp_pose"):
            return False, "机械臂未连接/不支持读位姿"

        # ---- 0. 读当前法兰位姿【一次】，全流程复用（实时性关键：每帧只 1 次位姿 RPC） ----
        cur_pose = None
        try:
            if hasattr(self.arm, "get_flange_pose"):
                cur_pose = self.arm.get_flange_pose()
            elif hasattr(self.arm, "get_tcp_pose"):
                cur_pose = self.arm.get_tcp_pose()
        except Exception:
            cur_pose = None
        cur_xyz = None
        if cur_pose is not None and len(cur_pose) >= 3:
            cand = np.array(cur_pose[:3], dtype=np.float64)
            if np.all(np.isfinite(cand)) and np.all(np.abs(cand) <= 3.0):
                cur_xyz = cand

        ok_safe, msg_safe = self._check_emergency(pose=cur_pose)
        if not ok_safe:
            return False, msg_safe

        # ---- 丢手检测 ----
        if wrist_3d_cam is None:
            self._lost_count += 1
            self._drops["lost"] += 1
            self.stats["lost_count"] = self._lost_count
            if self._lost_count >= self.lost_frames:
                self.stop(emergency=True, reason=f"连续 {self._lost_count} 帧未检测到手")
                return False, self.stats["last_status"]
            self.stats["last_status"] = f"丢手 {self._lost_count}/{self.lost_frames}（即将急停）"
            return False, self.stats["last_status"]
        self._lost_count = 0

        # ---- ★ 垂直(Z)方向跟随算法 ----
        # 只用手腕相机系 3D 中的【垂直/深度方向】(z≈光轴深度, 相机朝下时≈高度)。
        # 设计（用户要求，流畅第一）：
        #   * 只用 z 分量做"手是否在动"判定与跟随量；x/y（水平抖动/深度噪声）一律不参与；
        #   * 深度差大【绝不丢弃帧】——视为一次较大的垂直移动，由"追逐步长限幅"平滑逼近；
        #   * 仅当坐标物理失效(非有限/超范围)才忽略该帧（sensor 坏点）。
        wrist3 = np.asarray(wrist_3d_cam[:3], dtype=np.float64)
        z_cam = float(wrist3[2])
        if not np.isfinite(z_cam) or not (0.03 <= z_cam <= 4.0):
            self._drops["bad_point"] += 1
            self.stats["last_status"] = "手腕深度失效(非有限/超范围)，忽略该帧"
            return False, self.stats["last_status"]

        jump_z = 0.0
        if self._last_cam_z is not None:
            jump_z = abs(z_cam - self._last_cam_z)
        self._z_win.append(z_cam)
        if len(self._z_win) > CAM_WINDOW_FRAMES:
            self._z_win.pop(0)
        win_z = abs(z_cam - self._z_win[0]) if len(self._z_win) >= 2 else 0.0
        hand_moving = (jump_z >= self.cam_still) or (win_z >= Z_WIN_M)
        self.stats["hand_moving"] = bool(hand_moving)

        # ---- 建锚 / 刷新期望（垂直目标） ----
        if self._anchor_end_xyz is None:
            if cur_xyz is None:
                self.stats["last_status"] = "读当前位置失败（None/读数异常），无法建立锚点"
                return False, self.stats["last_status"]
            try:
                wb0 = self.he.camera_to_base(wrist3, self.arm, flange_pose=cur_pose)
            except Exception as exc:
                self.stats["last_status"] = f"坐标转换失败: {exc}"
                return False, self.stats["last_status"]
            self._anchor_end_xyz = cur_xyz.copy()
            self._anchor_wrist_base = wb0.copy()          # 全 3D（内部只取 z 用）
            self._desired_xyz = cur_xyz.copy()
            self._last_cam_z = z_cam
            self.stats["last_status"] = "锚点已建立（垂直 Z 跟随，幅度1:1）"
            return False, self.stats["last_status"]

        if hand_moving:
            try:
                wb = self.he.camera_to_base(wrist3, self.arm, flange_pose=cur_pose)
            except Exception as exc:
                self.stats["last_status"] = f"坐标转换失败: {exc}"
                return False, self.stats["last_status"]
            d_z = float(wb[2] - self._anchor_wrist_base[2])   # 手腕垂直位移（基座系 z）
            # 期望末端：x/y 保持锚点（水平不跟随），z = 锚点 z + 手腕垂直位移（幅度 1:1）
            self._desired_xyz = np.array(
                [self._anchor_end_xyz[0], self._anchor_end_xyz[1],
                 self._anchor_end_xyz[2] + d_z], dtype=np.float64)
        self._last_cam_z = z_cam

        # ---- 算追赶步（仅 z 方向） ----
        if cur_xyz is None:
            self.stats["last_status"] = "读当前位置失败（None/读数异常），禁止运动"
            return False, self.stats["last_status"]
        diff_z = float(self._desired_xyz[2] - cur_xyz[2])
        self.stats["desired_xyz"] = [round(float(v), 4) for v in self._desired_xyz]
        self.stats["step_remaining_mm"] = round(abs(diff_z) * 1000.0, 1)
        if abs(diff_z) <= STEP_DONE_M:
            self._drops["done"] += 1
            self.stats["last_status"] = "到位（垂直目标已 1:1 跟随）"
            return False, self.stats["last_status"]

        # ---- 追逐步长限幅（深度大差也在此被平滑，绝不丢帧） ----
        step_z = max(-self.max_step, min(self.max_step, diff_z))
        target_xyz = np.array([cur_xyz[0], cur_xyz[1], cur_xyz[2] + step_z])
        delta = np.array([0.0, 0.0, step_z])
        delta_norm = abs(step_z)

        # ---- 高度安全区检查 ----
        target_full = list(target_xyz) + list(self.fixed_rpy)
        ok_des, des_msg = self.safe.check_pose(list(self._desired_xyz), margin=0.005)
        ok_path, path_msg = self.safe.check_path(list(cur_xyz), list(target_xyz), margin=0.005)
        if not (ok_des and ok_path):
            self._bound_count += 1
            self.stats["bound_count"] = self._bound_count
            why = des_msg if not ok_des else path_msg
            try:
                b = self.safe.get_box()
                diag = (f"末端z={cur_xyz[2]:.3f}m 期望z={self._desired_xyz[2]:.3f}m "
                        f"高度安全区z[{b.get('min_z', b.get('min_xyz',[0,0,0])[2]):.2f},"
                        f"{b.get('max_z', b.get('max_xyz',[0,0,1])[2]):.2f}]m")
            except Exception:
                diag = ""
            self.stats["last_status"] = f"⚠️ 高度安全区拦截: {why}"
            if diag:
                self.stats["last_status"] += f" ｜ {diag}"
            logger.warning("[eye-follow] 高度安全区拦截: %s %s", why, diag)
            if self._bound_count >= self.bound_stop_frames:
                self.stop(emergency=True,
                          reason=f"连续越界 {self._bound_count} 帧（高度安全区）: {why}")
            return False, self.stats["last_status"]
        self._bound_count = 0

        # ---- 下发运动 ----
        if hasattr(self.arm, "is_steady"):
            try:
                steady = self.arm.is_steady()
                if steady is False:
                    self._drops["busy"] += 1
                    self.stats["last_status"] = "上一帧运动中，跳过本帧"
                    return False, self.stats["last_status"]
            except Exception:
                pass
        if self.motion_mode == MOTION_MODE_WRIST_LOCK:
            return self._move_wrist_lock(cur_xyz, delta, delta_norm, block)
        return self._move_cartesian(target_full, target_xyz, cur_xyz,
                                    delta, delta_norm, block)

    # ------------------------------------------------------------------
    def _move_wrist_lock(self, cur_xyz, delta, delta_norm, block):
        """
        末端三关节锁腕运动。

        ★ 各关节独立硬限判断：
           J4 <= wrist_hard_j4, J5 <= wrist_hard_j5, J6 <= wrist_hard_j6
           任一超过则视为不可达
        """
        if not self._wrist_lock_ok or self._locked_wrist is None:
            self.stats["last_status"] = "锁腕模式未就绪，禁止运动"
            return False, self.stats["last_status"]
        try:
            q_cur = self.arm.get_joint_positions()
            if q_cur is None or len(q_cur) < 6:
                self.stats["last_status"] = "读关节角失败，跳过本帧"
                return False, self.stats["last_status"]
        except Exception as exc:
            self.stats["last_status"] = f"读关节角失败: {exc}"
            return False, self.stats["last_status"]

        ref = [float(v) for v in q_cur]
        ref[3], ref[4], ref[5] = self._locked_wrist[0], self._locked_wrist[1], self._locked_wrist[2]

        q_sol, scale, wrist_dev_deg, soft = None, 1.0, 0.0, False
        best_small_q, best_small_scale, best_small_dev = None, 1.0, None
        # ★ 各关节独立偏差和硬限
        best_small_dev_j4 = None
        best_small_dev_j5 = None
        best_small_dev_j6 = None

        base = np.array(cur_xyz, dtype=np.float64)
        dvec = np.array(delta, dtype=np.float64)
        try:
            for s in JOINT_LOCK_SCALES:
                pos_t = base + dvec * s
                pose_t = list(pos_t) + list(self.fixed_rpy)
                q_t, ret = self.arm.inverse_kinematics(ref, pose_t)
                if ret != 0 or q_t is None or len(q_t) < 6:
                    continue

                # ★ 分别计算各关节偏差
                dev_j4 = abs(q_t[3] - self._locked_wrist[0])
                dev_j5 = abs(q_t[4] - self._locked_wrist[1])
                dev_j6 = abs(q_t[5] - self._locked_wrist[2])
                dev = max(dev_j4, dev_j5, dev_j6)

                # FK 正解校验
                fk_pose, fk_ret = self.arm.forward_kinematics(q_t)
                if fk_ret != 0 or fk_pose is None:
                    continue
                fk_err = float(np.linalg.norm(np.array(fk_pose[:3]) - pos_t))
                if fk_err > DEFAULT_IK_POS_ERR_M:
                    continue

                # ★ 软容差检查（3°以内直接执行）
                if dev <= self.wrist_tol:
                    q_sol, scale, wrist_dev_deg = q_t, s, math.degrees(dev)
                    break

                # ★ 记录最小偏差解（用于软降级）
                if best_small_dev is None or dev < best_small_dev:
                    best_small_q, best_small_scale, best_small_dev = q_t, s, dev
                    best_small_dev_j4 = dev_j4
                    best_small_dev_j5 = dev_j5
                    best_small_dev_j6 = dev_j6

            # ★ 全级超软容差 → 检查是否各关节都≤各自硬限
            if q_sol is None and best_small_q is not None:
                j4_ok = best_small_dev_j4 <= self.wrist_hard_j4
                j5_ok = best_small_dev_j5 <= self.wrist_hard_j5
                j6_ok = best_small_dev_j6 <= self.wrist_hard_j6
                if j4_ok and j5_ok and j6_ok:
                    q_sol, scale = best_small_q, best_small_scale
                    wrist_dev_deg = math.degrees(best_small_dev)
                    soft = True

        except Exception as exc:
            self.stats["last_status"] = f"锁腕 IK/FK 异常: {exc}"
            return False, self.stats["last_status"]

        # ★ 不可达判定：任一关节超过其独立硬限
        if q_sol is None:
            self._unreach_count += 1
            self.stats["unreach_count"] = self._unreach_count
            self.stats["last_status"] = (
                f"⚠️ 锁腕硬不可达：需转动末端关节超硬限 "
                f"(J4>{math.degrees(self.wrist_hard_j4):.0f}° / "
                f"J5>{math.degrees(self.wrist_hard_j5):.0f}° / "
                f"J6>{math.degrees(self.wrist_hard_j6):.0f}°) "
                f"{self._unreach_count}/{self.wrist_unreach_frames}")
            logger.warning("[eye-follow] %s", self.stats["last_status"])
            if self._unreach_count >= self.wrist_unreach_frames:
                self.stop(emergency=True,
                          reason=f"连续{self._unreach_count}帧需大幅转动末端关节才可达"
                                 f"（锁腕保护急停）")
            return False, self.stats["last_status"]
        self._unreach_count = 0
        self._wrist_dev_last_deg = wrist_dev_deg

        # ★ 记录各关节当前偏差到统计（供GUI显示）
        if q_sol is not None:
            dev_j4_cur = abs(q_sol[3] - self._locked_wrist[0])
            dev_j5_cur = abs(q_sol[4] - self._locked_wrist[1])
            dev_j6_cur = abs(q_sol[5] - self._locked_wrist[2])
            self.stats["dev_j4_deg"] = round(math.degrees(dev_j4_cur), 1)
            self.stats["dev_j5_deg"] = round(math.degrees(dev_j5_cur), 1)
            self.stats["dev_j6_deg"] = round(math.degrees(dev_j6_cur), 1)

        pos_actual = base + dvec * scale
        eff_norm = delta_norm * scale
        try:
            ret, msg = self.arm.movej(q_sol,
                                      speed_deg=JOINT_LOCK_SPEED_DEG,
                                      acc_deg=JOINT_LOCK_ACC_DEG,
                                      block=block, timeout_s=DEFAULT_MOVE_TIMEOUT)
            if ret != 0:
                # 瞬时类错误（SDK 忙/未就绪等）→ 软跳过本帧，连续多次才急停；
                # 其它错误码（路径规划失败/力矩过载等）→ 立即急停
                if ret in TRANSIENT_MOVE_RETS:
                    self._move_fail_count += 1
                    self.stats["last_status"] = (
                        f"movej 瞬时错误 ret={ret}({msg or ''}) 软跳过 "
                        f"{self._move_fail_count}/{MOVE_FAIL_SOFT_FRAMES}")
                    if self._move_fail_count >= MOVE_FAIL_SOFT_FRAMES:
                        self.stop(emergency=True,
                                  reason=f"movej 连续失败 ret={ret} {msg}")
                    return False, self.stats["last_status"]
                self.stop(emergency=True, reason=f"movej 指令异常 ret={ret} {msg}")
                return False, self.stats["last_status"]
            self._move_fail_count = 0
            self._last_cmd_time = time.time()
            self._moved_count += 1
            self._last_cmd_xyz = np.array(pos_actual)
            self._last_actual_xyz = np.array(base)
            if soft:
                lock_txt = (f"腕补偿 {wrist_dev_deg:.1f}°(J4≤{math.degrees(self.wrist_hard_j4):.0f}°,"
                            f"J5≤{math.degrees(self.wrist_hard_j5):.0f}°,"
                            f"J6≤{math.degrees(self.wrist_hard_j6):.0f}°)姿态仍锁")
            else:
                lock_txt = (f"腕偏差 {wrist_dev_deg:.2f}° ≤ "
                            f"{math.degrees(self.wrist_tol):.0f}° 已锁腕")
            self.stats.update({
                "moved_count": self._moved_count,
                "last_delta": [round(float(v), 4) for v in (dvec * scale)],
                "last_target": [round(float(v), 4) for v in
                                (list(pos_actual) + list(self.fixed_rpy))],
                "wrist_dev_deg": round(wrist_dev_deg, 3),
                "last_status": (
                    f"跟随中 3DΔ=({dvec[0]*scale*1000:+.0f},{dvec[1]*scale*1000:+.0f},"
                    f"{dvec[2]*scale*1000:+.0f})mm {lock_txt}"),
            })
            return True, self.stats["last_status"]
        except Exception as exc:
            self.stop(emergency=True, reason=f"movej 异常: {exc}")
            return False, self.stats["last_status"]

    # ------------------------------------------------------------------
    def _move_cartesian(self, target_full, target_xyz, cur_xyz, delta, delta_norm, block):
        """旧实现：moveLine 笛卡尔直线 + 姿态硬锁（对照/调试用）。"""
        try:
            ret, msg = self.arm.movel(target_full, speed=self.max_speed,
                                      acc=self.max_speed * 0.8,
                                      block=block, timeout_s=DEFAULT_MOVE_TIMEOUT)
            if ret != 0:
                if ret in TRANSIENT_MOVE_RETS:
                    self._move_fail_count += 1
                    self.stats["last_status"] = (
                        f"movel 瞬时错误 ret={ret} 软跳过 "
                        f"{self._move_fail_count}/{MOVE_FAIL_SOFT_FRAMES}")
                    if self._move_fail_count >= MOVE_FAIL_SOFT_FRAMES:
                        self.stop(emergency=True,
                                  reason=f"movel 连续失败 ret={ret} {msg}")
                    return False, self.stats["last_status"]
                self.stop(emergency=True, reason=f"movel 指令异常 ret={ret} {msg}")
                return False, self.stats["last_status"]
            self._move_fail_count = 0
            self._last_cmd_time = time.time()
            self._moved_count += 1
            self._last_cmd_xyz = np.array(target_xyz)
            self._last_actual_xyz = np.array(cur_xyz)
            self.stats.update({
                "moved_count": self._moved_count,
                "last_delta": [round(float(v), 4) for v in delta],
                "last_target": [round(float(v), 4) for v in target_full],
                "last_status": f"跟随中 Δ={delta_norm*1000:.1f}mm 姿态已锁(cartesian)",
            })
            return True, self.stats["last_status"]
        except Exception as exc:
            self.stop(emergency=True, reason=f"movel 异常: {exc}")
            return False, self.stats["last_status"]

    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        s = dict(self.stats)
        # 帧统计动态附加（避免每次 update 到处同步）
        s["frames_total"] = self._frames_total
        s["drops"] = dict(self._drops)
        return s


if __name__ == "__main__":
    # 自测代码（略，与原文件保持一致）
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from vision.hand_eye import HandEyeCalibration
    from arm.arm_safety import ArmSafetyBox

    he = HandEyeCalibration()
    safe = ArmSafetyBox()

    class FakeJointArm:
        Q0 = [0.2, -0.5, 1.0, 0.5, 1.0, 0.0]
        POS0 = [0.5, 0.0, 0.4]
        K = 0.1

        def __init__(self):
            self.q = list(self.Q0)
            self.moves = []
            self.torques = [2.0] * 6
            self.stall = False
            self.force_wrist_shift_rad = 0.0

        def _fk_pos(self, q):
            return [self.POS0[i] + self.K * (q[i] - self.Q0[i]) for i in range(3)]

        def get_joint_positions(self):
            return list(self.q)

        def get_flange_pose(self):
            return self._fk_pos(self.q) + [math.pi, 0.0, -0.436]

        def get_tcp_pose(self):
            return self.get_flange_pose()

        def get_joint_torques(self):
            return list(self.torques)

        def is_steady(self):
            return True

        def hard_stop(self, retries=5, delay_s=0.05):
            self.moves.append("HARD_STOP")
            return True

        def stop_move(self):
            self.moves.append("STOP")

        def inverse_kinematics(self, ref, pose):
            q = [self.Q0[i] + (pose[i] - self.POS0[i]) / self.K for i in range(3)]
            q += [ref[3], ref[4], ref[5]]
            if self.force_wrist_shift_rad:
                q[3] += self.force_wrist_shift_rad
            return q, 0

        def forward_kinematics(self, q):
            return self._fk_pos(q) + [math.pi, 0.0, -0.436], 0

        def movej(self, q, speed_deg=None, acc_deg=None, block=False, timeout_s=None):
            self.moves.append(("movej", list(q)))
            if not self.stall:
                self.q = list(q)
            return 0, None

        def movel(self, pose, speed=None, acc=None, block=False, timeout_s=None):
            self.moves.append(list(pose))
            return 0, None

    print("\n=== 测试：各关节独立硬限 ===")
    arm_test = FakeJointArm()
    arm_test.force_wrist_shift_rad = 0.08  # J4 约 4.6°
    safe_test = ArmSafetyBox(min_z=0.0, max_z=2.0)

    f_test = EyeInHandFollower(
        arm_test, he, safe_test,
        wrist_hard_j4_deg=5.0,   # J4 硬限 5°
        wrist_hard_j5_deg=30.0,  # J5 硬限 30°
        wrist_hard_j6_deg=30.0,  # J6 硬限 30°
        wrist_unreach_frames=3
    )
    f_test.begin()
    f_test.update([0.0, 0.0, 0.5])
    ok, msg = f_test.update([0.0, 0.0, 0.53])
    print(f"J4偏差4.6°(硬限5°): {msg}")
    stats = f_test.get_stats()
    print(f"各关节硬限: J4={stats.get('wrist_hard_j4_deg')}°, J5={stats.get('wrist_hard_j5_deg')}°, J6={stats.get('wrist_hard_j6_deg')}°")

    print("\n=== 测试：J4超硬限触发急停 ===")
    arm_test2 = FakeJointArm()
    arm_test2.force_wrist_shift_rad = 0.12  # J4 约 6.9°
    f_test2 = EyeInHandFollower(
        arm_test2, he, safe_test,
        wrist_hard_j4_deg=5.0,
        wrist_hard_j5_deg=30.0,
        wrist_hard_j6_deg=30.0,
        wrist_unreach_frames=3
    )
    f_test2.begin()
    f_test2.update([0.0, 0.0, 0.5])
    got_stop = False
    for i in range(4):
        ok, msg = f_test2.update([0.0, 0.0, 0.5 + 0.012 * (i + 1)])
        if "急停" in msg or "锁腕保护" in msg:
            got_stop = True
            break
    print(f"J4偏差6.9°(硬限5°)→ {msg}")
    assert got_stop, "J4 超硬限应触发急停"

    # ================= 回归：RPY ±π 跳变不应误急停 =================
    class FakeWrapArm(FakeJointArm):
        """模拟法兰 rx 在 -π 附近（等价 fixed π，仅数值跳号）"""
        def get_flange_pose(self):
            return self._fk_pos(self.q) + [-math.pi + 0.02, 0.0, -0.436]
    armw = FakeWrapArm()
    fw = EyeInHandFollower(armw, he, safe)   # fixed_rpy 默认 [π,0,-0.436]
    fw.begin()
    okw, msgw = fw._check_emergency()
    assert okw, f"±π 跳号不应误报姿态偏离: {msgw}"
    print("\n回归 OK：RPY 在 ±π 跳号不误急停")

    # ================= 回归：力矩连续2帧急停 / 丢手急停 =================
    armt = FakeJointArm()
    ft = EyeInHandFollower(armt, he, safe)
    ft.begin()
    ft.update([0.0, 0.0, 0.5])
    armt.torques = [16.0] * 6                 # > 默认阈值 15
    ok, msg = ft.update([0.0, 0.0, 0.53])     # 第1帧：计数1，不立即停
    print("力矩第1帧:", msg)
    ok, msg = ft.update([0.0, 0.0, 0.53])     # 第2帧连续超阈值 → 急停
    print("力矩第2帧:", msg)
    assert "急停" in msg or "碰撞" in msg, "力矩连续2帧超阈值应急停"
    # 丢手急停
    for _ in range(8):
        ok, msg = ft.update(None)
    print("丢手后:", msg)
    assert "HARD_STOP" in armt.moves, "丢手应触发硬停止"
    print("回归 OK：力矩2帧/丢手急停")

    print("\nEyeInHandFollower 自测全部通过")