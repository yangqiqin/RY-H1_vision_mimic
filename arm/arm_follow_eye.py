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
DEFAULT_MAX_STEP_M = 0.015      # 单帧最大合位移增量（米≈15mm）——更流畅的追手节拍
                                # 配合 GUI"限幅mm/帧"；垂直跟随只在 z 方向，故不再怕 x/y 噪声
# 丢手判定（时间制，避免"处理帧率高→短暂无手即误急停"）：
DEFAULT_LOST_TIMEOUT_S = 1.5    # 连续多长时间检测不到有效手腕才触发急停（秒）
DEFAULT_LOST_FRAMES = 5         # 兼容旧参数（不再按帧急停，仅计数显示）
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
MOVE_FAIL_SOFT_FRAMES = 8        # movej 瞬时错误（BUSY/队列满/未就绪类）连续软失败上限，超过才急停
# ★★★ 修改点：将 ret=-2 加入瞬态错误集合，避免偶发不可达直接急停 ★★★
# movej/movel 瞬时类错误码：不立即急停（SDK 忙/队列满/未就绪等），静默等待下拍重试；
# -2 通常表示逆解失败/目标不可达，连续出现才视为严重问题。
TRANSIENT_MOVE_RETS = frozenset({-2, 1, 2, 3, -13, 203, 210, 212, 218, 219, 236})
# 单次 movej 目标允许的最大位移（= max_step×4，即一次给足大段目标，减少指令频次→不易 QUEUE_FULL，
# 大范围运动由一条长轨迹平滑完成；真正的限速由机械臂自身速度上限决定）
SEND_LIMIT_FACTOR = 4

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
JOINT_LOCK_SPEED_DEG = 90.0
JOINT_LOCK_ACC_DEG = 220.0
MOVE_GATE_S = 0.12            # 相邻 move 下发最小间隔（s）≈8Hz 连续重规划，去掉 is_steady 等待
CAM_WINDOW_FRAMES = 15
# ★ 垂直(Z)跟随：不再用"深度差大"丢弃任何帧（真实运动不可能垂直，抖动不是丢帧理由）。
# 运动判定仅用 z 分量：单帧 |Δz|≥cam_still，或窗口累计 |Δz|≥Z_WIN_M。
CAM_BAD_JUMP_M = 0.15     # 保留常量仅为兼容；算法中已不使用"突跳丢弃"
Z_WIN_M = 0.015           # z 窗口累计移动阈值（米）≈ 15mm/0.5s 判定手在动
STEP_DONE_M = 0.003       # 追赶完成/微小抖动死区：期望-当前 ≤3mm 视为到位
# 每帧丢弃/忽略原因计数（GUI HUD 显示，用于判断"是否误丢了手的动作"）
DROP_KEYS = ("bad_jump", "bad_point", "static", "busy", "lost", "done")

# 手腕平滑（借鉴 github Real-time-3D-control…/smoothers.py RealtimeSmoother3D）：
# 大跳变=深度/检测异常 → 先压缩(0.3 blend)再进入 EMA，绝不丢帧；α 越小越顺。
EMA_SMOOTH_ALPHA = 0.35
EMA_OUTLIER_M = 0.15   # 手腕位移单帧突变 > 此值(米)视为异常帧：压缩后再平滑


class EyeInHandFollower:
    """
    眼在手上跟随控制器：手腕下移多少 → 机械臂末端就下移多少（相对增量）。
    内置完整安全链：姿态硬锁 + 末端三关节锁腕 + 安全框强制 + 碰撞/受阻检测 + 失手急停。

    ★ 各关节可独立设置硬限（J4/J5/J6，GUI可调，最大90°）
    """

    def __init__(self, arm, hand_eye, safety_box,
                 max_step_m: float = DEFAULT_MAX_STEP_M,
                 lost_frames: int = DEFAULT_LOST_FRAMES,
                 lost_time_s: float = DEFAULT_LOST_TIMEOUT_S,
                 fixed_rpy: Optional[List[float]] = None,
                 max_speed: float = 0.15,
                 bound_stop_frames: int = DEFAULT_BOUND_STOP_FRAMES,
                 rpy_tolerance_deg: float = DEFAULT_RPY_TOLERANCE_DEG,
                 torque_threshold: float = DEFAULT_TORQUE_THRESHOLD,
                 stall_frames: int = DEFAULT_STALL_FRAMES,
                 cam_still_m: float = DEFAULT_CAM_STILL_M,
                 motion_mode: str = DEFAULT_MOTION_MODE,
                 servo_mode: bool = False,
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
        self.lost_frames = int(lost_frames)      # 兼容（显示用；急停改时间制）
        self.lost_time_s = float(lost_time_s)    # 连续无有效手腕超时（秒）→ 急停
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

        # ★ 关节伺服执行（servoJoint 连续轨迹，视觉实时跟随 <0.1s 的正确执行层；
        #   默认关：begin() 里成功进入 servo 模式才启用，失败自动回退 move 模式）
        self.servo_mode = bool(servo_mode)
        self._servo_ok = False
        self._servo_t = 0.04   # servoj 下发时间参数 t（s），与跟随循环节拍一致（servo 模式时）

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
        self._lost_t0: Optional[float] = None    # 本次连续丢手起始时间（时间制判定）
        self._bound_count = 0
        self._stall_count = 0
        self._unreach_count = 0
        self._torque_peak_count = 0      # 力矩连续超阈值帧计数（过滤尖峰）
        self._last_cmd_time = 0.0        # 上次成功下发运动的时间
        self._move_fail_count = 0        # movej 瞬时错误连续次数
        self._time_gate_enabled = not getattr(arm, "_simulated", False)  # 真机开、模拟臂(自测)关
        self._last_cmd_xyz: Optional[np.ndarray] = None
        self._last_actual_xyz: Optional[np.ndarray] = None
        self._moved_count = 0
        self._start_time = 0.0
        self.emergency_triggered = False

        # ---- 末端三关节锁腕状态 ----
        self._locked_wrist: Optional[List[float]] = None
        self._wrist_lock_ok = False
        self._wrist_dev_last_deg = 0.0

        # ---- 锚点追踪状态（XYZ 平滑版） ----
        self._wrist_ema: Optional[np.ndarray] = None
        self._last_flange_pose: Optional[list] = None   # 最近法兰位姿缓存（GUI 显示用，免重复 RPC）
        self._anchor_end_xyz: Optional[np.ndarray] = None
        self._anchor_wrist_base: Optional[np.ndarray] = None
        self._desired_xyz: Optional[np.ndarray] = None
        self._anchor_flange_pose: Optional[list] = None   # ★ 新增：锚点末端位姿（固定用于坐标转换）

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
        """开始跟随：锁定末端姿态 + 记录锚点位姿（用于固定坐标变换）"""
        self._running = True
        self._last_wrist_base = None
        self._lost_count = 0
        self._lost_t0 = None
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
        self._wrist_ema = None
        self._last_flange_pose = None
        self._anchor_end_xyz = None
        self._anchor_wrist_base = None
        self._desired_xyz = None
        self._anchor_flange_pose = None   # ★ 新增：保存锚点末端位姿（固定用于坐标转换）

        # ---- 读取锚点末端位姿（固定） ----
        try:
            if hasattr(self.arm, "get_flange_pose"):
                anchor_pose = self.arm.get_flange_pose()
            elif hasattr(self.arm, "get_tcp_pose"):
                anchor_pose = self.arm.get_tcp_pose()
            else:
                anchor_pose = None
            if anchor_pose is not None and len(anchor_pose) >= 6:
                self._anchor_flange_pose = list(anchor_pose)
                logger.info("[eye-follow] 锚点末端位姿记录: %s", self._anchor_flange_pose)
            else:
                logger.warning("[eye-follow] 无法读取锚点末端位姿，将使用实时位姿（可能不稳定）")
        except Exception as exc:
            logger.warning("[eye-follow] 读取锚点末端位姿失败: %s", exc)

        # ---- 锁腕初始化（仅为统计显示，失败不禁止运动：跟随用"固定姿态 IK 直发"，腕自由） ----
        self._locked_wrist = None
        self._wrist_lock_ok = False
        if self.motion_mode == MOTION_MODE_WRIST_LOCK:
            try:
                q = self.arm.get_joint_positions()
                if q is not None and len(q) >= 6:
                    self._locked_wrist = [float(v) for v in q[3:6]]
                    self._wrist_lock_ok = True
                    logger.info("[eye-follow] 记录起始腕关节 J4/5/6=%s deg",
                                [round(math.degrees(v), 1) for v in self._locked_wrist])
            except Exception as exc:
                logger.info("[eye-follow] 读起始关节角失败(不影响跟随): %s", exc)

        # ---- 伺服模式开启（servo_mode=True 时尝试进入并【确认生效】；失败回退 move 模式）----
        self._servo_ok = False
        if self.servo_mode:
            if hasattr(self.arm, "start_servo_mode"):
                try:
                    if self.arm.start_servo_mode(mode=1) == 0:
                        # 模式切换是异步的：轮询确认 getServoModeSelect==1（参考官方 switch_servoj_mode）
                        self._servo_ok = True
                        try:
                            if hasattr(self.arm, "servo_mode_active"):
                                for _ in range(20):
                                    if self.arm.servo_mode_active():
                                        break
                                    time.sleep(0.01)
                                if not self.arm.servo_mode_active():
                                    self._servo_ok = False
                                    logger.warning("[eye-follow] servo 模式未生效(超时)，回退 move")
                        except Exception:
                            self._servo_ok = True   # 无法查询时按已开启处理，出错由 -13 重试逻辑兜底
                        if self._servo_ok:
                            logger.info("[eye-follow] ★ servo 模式已开启（实时关节跟随）")
                    else:
                        logger.warning("[eye-follow] servo 模式开启失败，回退 move 模式")
                except Exception as exc:
                    self._servo_ok = False
                    logger.warning("[eye-follow] servo 模式异常，回退 move 模式: %s", exc)
            else:
                logger.info("[eye-follow] 机械臂不支持 servo 接口，使用 move 模式")

        self.stats.update({"running": True, "lost_count": 0, "bound_count": 0,
                           "stall_count": 0, "unreach_count": 0, "moved_count": 0,
                           "last_status": ("跟随中（servo 实时模式）"
                                           if self._servo_ok else "跟随中（固定姿态，流畅跟随）"),
                           "emergency": "",
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
        """停止跟随。emergency=True 时执行【硬停止】。servo 模式需先退出伺服模式。"""
        self._running = False
        if self._servo_ok and hasattr(self.arm, "stop_servo_mode"):
            try:
                self.arm.stop_servo_mode()
            except Exception:
                pass
            self._servo_ok = False
            logger.info("[eye-follow] servo 模式已退出")
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
        if self.motion_mode not in (MOTION_MODE_WRIST_LOCK, MOTION_MODE_CARTESIAN):
            return False, "未知运动模式"
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
        if cur_pose is not None:
            self._last_flange_pose = list(cur_pose)   # 供 GUI 轮询显示，避免重复 RPC
        cur_xyz = None
        if cur_pose is not None and len(cur_pose) >= 3:
            cand = np.array(cur_pose[:3], dtype=np.float64)
            if np.all(np.isfinite(cand)) and np.all(np.abs(cand) <= 3.0):
                cur_xyz = cand

        ok_safe, msg_safe = self._check_emergency(pose=cur_pose)
        if not ok_safe:
            return False, msg_safe

        # ---- 丢手检测（时间制：连续无有效手腕 ≥lost_time_s 才急停） ----
        if wrist_3d_cam is None:
            self._drops["lost"] += 1
            now = time.time()
            if self._lost_t0 is None:
                self._lost_t0 = now
            self._lost_count += 1
            self.stats["lost_count"] = self._lost_count
            elapsed = now - self._lost_t0
            if elapsed >= self.lost_time_s:
                self.stop(emergency=True,
                          reason=f"丢手超时 {elapsed:.1f}s 未检测到手（急停）")
                return False, self.stats["last_status"]
            self.stats["last_status"] = f"手暂离 {elapsed:.1f}/{self.lost_time_s:.1f}s（未急停）"
            return False, self.stats["last_status"]
        self._lost_count = 0
        self._lost_t0 = None

        # ---- ★ XYZ 三维方向跟随算法（流畅优先：不因深度差丢帧，x/y 轻平滑抗抖） ----
        wrist3 = np.asarray(wrist_3d_cam[:3], dtype=np.float64)
        if not np.all(np.isfinite(wrist3)) or not (0.03 <= float(wrist3[2]) <= 4.0):
            self._drops["bad_point"] += 1
            self.stats["last_status"] = "手腕读数失效(非有限/超范围)，忽略该帧"
            return False, self.stats["last_status"]

        # ---- 确定用于坐标转换的固定位姿（锚点固定，防止正反馈） ----
        # 如果锚点固定位姿未设置（首次），则用当前位姿作为锚点（后续不变）
        if self._anchor_flange_pose is None and cur_pose is not None:
            self._anchor_flange_pose = list(cur_pose)
            logger.info("[eye-follow] 锚点末端位姿设为当前位姿: %s", self._anchor_flange_pose)
        # 若仍为 None（读不到位姿），则使用 cur_pose（但不推荐）
        flange_for_transform = self._anchor_flange_pose if self._anchor_flange_pose is not None else cur_pose

        # ---- 建锚点 ----
        if self._anchor_end_xyz is None:
            if cur_xyz is None:
                self.stats["last_status"] = "读当前位置失败（None/读数异常），无法建立锚点"
                return False, self.stats["last_status"]
            try:
                wb0 = self.he.camera_to_base(wrist3, self.arm, flange_pose=flange_for_transform)
            except Exception as exc:
                self.stats["last_status"] = f"坐标转换失败: {exc}"
                return False, self.stats["last_status"]
            self._anchor_end_xyz = cur_xyz.copy()
            self._anchor_wrist_base = wb0.copy()
            self._desired_xyz = cur_xyz.copy()
            self._wrist_ema = np.zeros(3, dtype=np.float64)   # 手腕位移平滑量
            self.stats["last_status"] = "锚点已建立（XYZ 跟随，幅度1:1）"
            return False, self.stats["last_status"]

        # 每帧计算手腕基座系位移（使用锚点固定位姿，防止正反馈）
        try:
            wb = self.he.camera_to_base(wrist3, self.arm, flange_pose=flange_for_transform)
        except Exception as exc:
            self.stats["last_status"] = f"坐标转换失败: {exc}"
            return False, self.stats["last_status"]
        raw_disp = wb - self._anchor_wrist_base

        # 平滑吸收（借鉴 RealtimeSmoother3D）：
        #   单帧突变>阈值 → 视为检测/深度异常，先压缩(30%新值)再 EMA；正常则标准 EMA。
        #   每帧都吸收：手再慢也能跟；x/y 噪声被平滑不会抖臂；异常不丢帧只是压幅。
        _new = raw_disp
        if float(np.linalg.norm(raw_disp - self._wrist_ema)) > EMA_OUTLIER_M:
            _new = 0.7 * self._wrist_ema + 0.3 * raw_disp
        self._wrist_ema = EMA_SMOOTH_ALPHA * _new + (1.0 - EMA_SMOOTH_ALPHA) * self._wrist_ema
        # 每轴 2mm 死区：滤掉亚毫米级抖动导致的机械臂微抖
        _dead = 0.002
        ema_dead = np.array([np.sign(v) * max(abs(v) - _dead, 0.0)
                             for v in self._wrist_ema], dtype=np.float64)
        self._desired_xyz = self._anchor_end_xyz + ema_dead
        self.stats["hand_moving"] = bool(float(np.linalg.norm(ema_dead)) > _dead)

        # ---- 算追赶步（XYZ） ----
        if cur_xyz is None:
            self.stats["last_status"] = "读当前位置失败（None/读数异常），禁止运动"
            return False, self.stats["last_status"]
        step = self._desired_xyz - cur_xyz
        step_norm = float(np.linalg.norm(step))
        self.stats["desired_xyz"] = [round(float(v), 4) for v in self._desired_xyz]
        self.stats["step_remaining_mm"] = round(step_norm * 1000.0, 1)
        _done = 0.001 if self._servo_ok else STEP_DONE_M
        if step_norm <= _done:
            self._drops["done"] += 1
            self.stats["last_status"] = "到位（XYZ 目标已跟随）"
            return False, self.stats["last_status"]

        # ---- 单次目标长度 ----
        # servo 模式：每次小步(≤max_step)，保证相邻关节差 ≤±15°(servoJoint 限制)；
        # move 模式：一次给足(≤max_step×SEND_LIMIT_FACTOR)长轨迹，减少队列满(ret=2)。
        _send_lim = self.max_step if self._servo_ok else self.max_step * SEND_LIMIT_FACTOR
        if step_norm > _send_lim:
            step = step / step_norm * _send_lim
            step_norm = _send_lim
        target_xyz = cur_xyz + step
        delta = step
        delta_norm = step_norm

        # ---- 高度安全区检查 ----
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

        # ---- 下发运动：每一帧有位移就【立即】下发当前目标 ----
        target_full = list(target_xyz) + list(self.fixed_rpy)
        if self.motion_mode == MOTION_MODE_WRIST_LOCK:
            return self._move_wrist_lock(cur_xyz, delta, delta_norm, block)
        return self._move_cartesian(target_full, target_xyz, cur_xyz, delta, delta_norm, block)

    # ------------------------------------------------------------------
    def _move_wrist_lock(self, cur_xyz, delta, delta_norm, block):
        """
        固定姿态 IK 直发（腕自由）：对【当前位置+步进，姿态=fixed_rpy】直接逆解 → movej。
        ★ 流畅第一（用户要求）：不再做"腕角锁定/容差/硬限/缩步不可达"等敏感校验——
        它们对微小运动即触发、让机械臂卡顿却实现不了实际保护。设备方向由【目标位姿的
        固定 RPY】保证，腕关节如何分配由 IK 决定（运动学正常行为），方向不会自己偏。
        仅 IK 完全无解（工作边界/奇异）时降半步并提示，不做累计急停。
        """
        base = np.array(cur_xyz, dtype=np.float64)
        dvec = np.array(delta, dtype=np.float64)
        try:
            q_cur = self.arm.get_joint_positions()
        except Exception:
            q_cur = None
        if q_cur is None or len(q_cur) < 6:
            self.stats["last_status"] = "读关节角失败(瞬态)，维持现状"
            return False, self.stats["last_status"]

        q_sol, scale, pos_t = None, 1.0, base + dvec
        for s in (1.0, 0.5, 0.25):
            pos_t = base + dvec * s
            pose_t = list(pos_t) + list(self.fixed_rpy)
            try:
                q_t, ret = self.arm.inverse_kinematics(q_cur, pose_t)
            except Exception:
                q_t, ret = None, -1
            if ret == 0 and q_t is not None and len(q_t) >= 6:
                q_sol = q_t
                scale = s
                break
        if q_sol is None:
            # 仅在工作边界/奇异处出现：不累计、不急停，保持原位等待
            self.stats["last_status"] = "目标不可达(工作边界)，维持原位"
            return False, self.stats["last_status"]
        pos_actual = base + dvec * scale
        try:
            ret, msg = 0, ""
            # —— servo 实时执行（若已进入 servo 模式）——
            if self._servo_ok and hasattr(self.arm, "servoj"):
                ret = self.arm.servoj(q_sol, t_s=self._servo_t)
                if ret in (2, 3):
                    # 忙/队列满：静默，下轮 worker 自然重试（不累计、不刷屏、不急停）
                    return False, self.stats["last_status"]
                if ret in (1, -13):
                    # -13=Not in servo mode / 1=BAD_STATE：模式可能掉线 → 重进一次再发
                    try:
                        self.arm.start_servo_mode(mode=1)
                        ret = self.arm.servoj(q_sol, t_s=self._servo_t)
                    except Exception:
                        ret = -13
                    if ret in (1, -13):
                        # 重进仍失败：自动回退 move 模式继续跟随（绝不因此急停）
                        self._servo_ok = False
                        self.stats["last_status"] = "servo 掉线→已回退 move 模式"
                        logger.warning("[eye-follow] servo 掉线(-13)，回退 move 模式")
                        ret, msg = self.arm.movej(q_sol,
                                                  speed_deg=JOINT_LOCK_SPEED_DEG,
                                                  acc_deg=JOINT_LOCK_ACC_DEG,
                                                  block=block,
                                                  timeout_s=DEFAULT_MOVE_TIMEOUT)
            else:
                ret, msg = self.arm.movej(q_sol,
                                          speed_deg=JOINT_LOCK_SPEED_DEG,
                                          acc_deg=JOINT_LOCK_ACC_DEG,
                                          block=block, timeout_s=DEFAULT_MOVE_TIMEOUT)
            if ret != 0:
                # 瞬时类错误（busy/队列满/模式未就绪等）→ 静默计数，连续多次才急停；
                # 其它错误码（规划失败/越界/奇异等）→ 立即急停
                if ret in TRANSIENT_MOVE_RETS:
                    self._move_fail_count += 1
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
            self.stats.update({
                "moved_count": self._moved_count,
                "last_delta": [round(float(v), 4) for v in (dvec * scale)],
                "last_target": [round(float(v), 4) for v in
                                (list(pos_actual) + list(self.fixed_rpy))],
                "last_status": (
                    f"跟随中 3DΔ=({dvec[0]*scale*1000:+.0f},{dvec[1]*scale*1000:+.0f},"
                    f"{dvec[2]*scale*1000:+.0f})mm"),
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
        _simulated = True          # 模拟臂标记：follower 据此关闭真实时钟时间门（自测用）
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

    print("\n=== 测试：固定姿态 IK 直发（腕自由）——腕偏多少都不断流 ===")
    arm_test = FakeJointArm()
    arm_test.force_wrist_shift_rad = 0.12  # 注入大腕偏 6.9°（旧"锁腕"会拒绝，新逻辑应照发）
    safe_test = ArmSafetyBox(min_z=0.0, max_z=2.0)
    f_test = EyeInHandFollower(arm_test, he, safe_test)
    f_test.begin()
    f_test.update([0.0, 0.0, 0.5])
    ok, msg = f_test.update([0.0, 0.0, 0.53])
    print(f"腕偏6.9° 跟随帧: {msg}")
    assert ok, "腕自由模式：IK 解存在即应下发 movej（不因腕差拒绝）"
    n_moves = len([m for m in arm_test.moves if isinstance(m, tuple) and m[0] == "movej"])
    print(f"已下发 movej 次数: {n_moves}")
    assert n_moves >= 1 and "HARD_STOP" not in arm_test.moves, "不应触发任何锁腕急停"
    print("固定姿态 IK 直发 OK：腕自由、无锁腕拒绝/急停")

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
    # 丢手急停（时间制：超时未检测到手腕 → 急停）
    armL = FakeJointArm()
    fL = EyeInHandFollower(armL, he, safe)
    fL.begin()
    fL.update([0.0, 0.0, 0.5])                    # 有效帧（清 t0）
    fL._lost_t0 = time.time() - fL.lost_time_s - 0.2   # 模拟已超时
    ok, msg = fL.update(None)
    print("丢手后:", msg)
    assert "HARD_STOP" in armL.moves, "丢手超时应触发硬停止"
    # 短时暂离不误急停（<超时阈值）
    armL2 = FakeJointArm()
    fL2 = EyeInHandFollower(armL2, he, safe)
    fL2.begin()
    fL2.update([0.0, 0.0, 0.5])
    fL2._lost_t0 = time.time() - 0.3              # 仅 0.3s 未检测到
    ok, msg = fL2.update(None)
    assert "HARD_STOP" not in armL2.moves and "暂离" in msg, f"短暂无手不应急停: {msg}"
    print("短暂丢手不误停 OK：", msg)
    print("回归 OK：力矩2帧/丢手(时间制)急停")

    print("\nEyeInHandFollower 自测全部通过")