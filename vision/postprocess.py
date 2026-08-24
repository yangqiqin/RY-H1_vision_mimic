# -*- coding: utf-8 -*-
"""
postprocess.py —— 关节角精度后处理（One Euro + 中值 + 限速）

依据《控制精度提升方案.md》阶段 1：
  解决"抖动 / 幅度不稳 / 突跳"三大精度痛点：
  1. 中值滤波    —— 去 MediaPipe 偶发异常帧（更抗离群点）
  2. One Euro    —— 速度自适应平滑（慢=强平滑抑噪，快=跟手低延迟）
  3. 差分限幅    —— 每帧角度变化限制，防止手指猛跳（安全）

用法：
  from vision.postprocess import JointAnglePostProcess
  pp = JointAnglePostProcess(joint_num=16, median_n=5, min_cutoff=0.5, beta=0.02, max_delta_deg=6.0)
  out_deg = pp.update(angles_deg)   # 每帧调用，返回后处理后的角度(度)
"""

from __future__ import annotations

import math
import time as _time
from collections import deque
from typing import List


class OneEuroFilter:
    """1€ 滤波器（Casiez et al., UIST 2012）。

    min_cutoff 越小越平滑；beta 越大越跟手；d_cutoff 控制速度估计平滑。
    """

    def __init__(self, min_cutoff: float = 0.5, beta: float = 0.01,
                 d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev: float | None = None
        self._dx_prev: float | None = None
        self._t_prev: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * 3.141592653589793 * max(cutoff, 1e-3))
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def filter(self, x: float, t: float) -> float:
        if self._x_prev is None:
            self._x_prev = x
            self._dx_prev = 0.0
            self._t_prev = t
            return x
        dt = max(t - self._t_prev, 1e-4)
        dx = (x - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self._dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self._x_prev
        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t
        return x_hat


class JointAnglePostProcess:
    """关节角后处理链：智能异常检测 → 中值 → One Euro → 分通道限速。

    改进（解决"握拳被误判异常导致卡住"与"内外展跳变"）：
      * 异常检测用"方向一致性"：真实握拳是所有手指协调变化（多通道同向大跳变
        是正常运动）；只有"孤立单指突变"（某关节跳变远大于其它关节）才判为异常，
        用中值替代而非整帧丢弃 → 握拳不再卡住
      * 分通道限速：拇指内外展(关节16)单独用更小 max_delta（防跳变），
        其它关节用常规限速
      * 可输出稳定性指标（抖动 std / 丢弃率）供 GUI 显示
    """

    # 拇指内外展关节索引（16 关节模型中索引 15）
    ABDUCT_IDX = 15

    def __init__(self, joint_num: int = 16, median_n: int = 5,
                 min_cutoff: float = 0.5, beta: float = 0.02,
                 max_delta_deg: float = 8.0,
                 abduct_max_delta_deg: float = 3.0,
                 max_jump_deg: float = 40.0,
                 jump_ratio_threshold: float = 3.0):
        self.n = int(joint_num)
        self.median_n = int(median_n)
        self.max_delta = float(max_delta_deg)
        self.abduct_max_delta = float(abduct_max_delta_deg)
        self.max_jump = float(max_jump_deg)
        self.jump_ratio = float(jump_ratio_threshold)
        self.history: List[deque] = [deque(maxlen=self.median_n)
                                     for _ in range(self.n)]
        self.euro: List[OneEuroFilter] = [OneEuroFilter(min_cutoff, beta)
                                          for _ in range(self.n)]
        self._prev_deg = [0.0] * self.n
        self._last_out = [0.0] * self.n
        # 稳定性指标
        self._jitter_history: deque = deque(maxlen=60)
        self.jitter_std = 0.0
        self.last_max_jump = 0.0
        self.dropped_frames = 0
        self.total_frames = 0

    def reset(self):
        self.history = [deque(maxlen=self.median_n) for _ in range(self.n)]
        self._prev_deg = [0.0] * self.n
        self._last_out = [0.0] * self.n
        mc = self.euro[0].min_cutoff if self.euro else 0.5
        bt = self.euro[0].beta if self.euro else 0.02
        self.euro = [OneEuroFilter(mc, bt) for _ in range(self.n)]
        self._jitter_history.clear()
        self.jitter_std = 0.0
        self.dropped_frames = 0
        self.total_frames = 0

    def update_params(self, min_cutoff=None, beta=None,
                      max_delta_deg=None, abduct_max_delta_deg=None,
                      max_jump_deg=None, jump_ratio_threshold=None):
        """运行时更新参数（GUI 实时调）。"""
        for f in self.euro:
            if min_cutoff is not None:
                f.min_cutoff = float(min_cutoff)
            if beta is not None:
                f.beta = float(beta)
        if max_delta_deg is not None:
            self.max_delta = float(max_delta_deg)
        if abduct_max_delta_deg is not None:
            self.abduct_max_delta = float(abduct_max_delta_deg)
        if max_jump_deg is not None:
            self.max_jump = float(max_jump_deg)
        if jump_ratio_threshold is not None:
            self.jump_ratio = float(jump_ratio_threshold)

    def update(self, angles_deg: List[float],
               t: float | None = None,
               fist_confidence: float | None = None) -> List[float]:
        """输入 16 关节角(度)，返回后处理结果(度)。

        异常判定（方向一致性 + 深度辅助）：
          * 计算每通道相对上一帧的跳变，取最大 jump_max 与中位 jump_med
          * 若 jump_max > max_jump 且 jump_max > jump_ratio × jump_med
            → 判定为"孤立单指突变"（异常）：该通道用中值替代，不整帧丢弃
          * 握拳等真实运动是协调变化（jump_med 也大），比值小 → 不丢弃
          * fist_confidence（来自深度相机）：当深度确认握拳（>=0.6）时，
            即使角度跳变大也视为真实运动 → 跳过异常判定，绝不卡住
        """
        if len(angles_deg) != self.n:
            raise ValueError(f"需要 {self.n} 个角度，收到 {len(angles_deg)}")
        if t is None:
            t = _time.time()
        self.total_frames += 1

        # ---- 0) 方向一致性 + 深度辅助 异常检测 ----
        jumps = [abs(float(angles_deg[i]) - self._prev_deg[i])
                 for i in range(self.n)]
        jump_max = max(jumps) if jumps else 0.0
        jump_sorted = sorted(jumps)
        jump_med = jump_sorted[len(jump_sorted) // 2] if jump_sorted else 0.0
        self.last_max_jump = jump_max

        depth_confirms_fist = (fist_confidence is not None
                               and fist_confidence >= 0.6)
        abnormal = False
        if not depth_confirms_fist:
            if (jump_max > self.max_jump and self.total_frames > 3
                    and jump_max > self.jump_ratio * max(jump_med, 1e-3)):
                abnormal = True
                self.dropped_frames += 1   # 记为"被抑制帧"（中值替代而非整帧丢弃）

        out = []
        for i in range(self.n):
            # 1) 中值滤波（去单通道毛刺）
            self.history[i].append(float(angles_deg[i]))
            vals = sorted(self.history[i])
            med = vals[len(vals) // 2]

            # 2) One Euro 平滑（异常通道同样走中值→平滑，保持运动趋势）
            sm = self.euro[i].filter(med, t)

            # 3) 分通道差分限速：内外展(关节16)单独更小限速，防跳变
            if i == self.ABDUCT_IDX:
                lim = self.abduct_max_delta
            else:
                lim = self.max_delta
            d = sm - self._prev_deg[i]
            if abs(d) > lim:
                sm = self._prev_deg[i] + lim * (1.0 if d > 0 else -1.0)
            self._prev_deg[i] = sm
            out.append(sm)

        # ---- 稳定性指标 ----
        frame_jitter = max(abs(out[i] - self._last_out[i]) for i in range(self.n))
        self._jitter_history.append(frame_jitter)
        if len(self._jitter_history) >= 5:
            vals = list(self._jitter_history)
            m = sum(vals) / len(vals)
            self.jitter_std = math.sqrt(
                sum((x - m) ** 2 for x in vals) / len(vals))
        self._last_out = out
        return out

    def get_stats(self) -> dict:
        """稳定性指标（GUI 显示用）。"""
        drop_rate = (self.dropped_frames / self.total_frames * 100
                     if self.total_frames else 0.0)
        return {
            "jitter_std_deg": self.jitter_std,     # 帧间抖动标准差
            "last_max_jump_deg": self.last_max_jump,
            "dropped_frames": self.dropped_frames,
            "drop_rate_pct": drop_rate,
        }


if __name__ == "__main__":
    # 自测1：纯噪声抑制（目标静止 30°，仅加噪声）
    import math
    import random
    random.seed(0)
    pp = JointAnglePostProcess(joint_num=4, median_n=5,
                               min_cutoff=0.5, beta=0.02, max_delta_deg=6.0)
    t0 = _time.time()
    raw, clean = [], []
    for k in range(300):
        noisy = [30.0 + random.uniform(-3, 3) for _ in range(4)]
        out = pp.update(noisy, t0 + k * 0.05)
        raw.append(noisy[0]); clean.append(out[0])

    def std(xs):
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

    raw_std = std(raw[100:]); clean_std = std(clean[100:])
    print(f"[静止+噪声] 原始抖动 std={raw_std:.3f}° -> 后处理 std={clean_std:.3f}°  抑制 {raw_std/max(clean_std,1e-9):.1f}x")
    assert clean_std < raw_std * 0.5, "静止目标噪声应被显著抑制"

    # 自测2：异常帧剔除（静止 30°，每 20 帧注入单通道 +50°）
    pp2 = JointAnglePostProcess(joint_num=4, median_n=5,
                                min_cutoff=0.5, beta=0.02, max_delta_deg=6.0)
    raw2, clean2 = [], []
    for k in range(300):
        noisy = [30.0 + random.uniform(-2, 2) for _ in range(4)]
        if k % 20 == 10:
            noisy[2] += 50.0   # 仅第 3 关节孤立突变
        out = pp2.update(noisy, t0 + k * 0.05)
        raw2.append(noisy[0]); clean2.append(out[0])
    raw2_std = std(raw2[50:]); clean2_std = std(clean2[50:])
    print(f"[孤立异常] 原始 std={raw2_std:.3f}° -> 后处理 std={clean2_std:.3f}°  抑制 {raw2_std/max(clean2_std,1e-9):.1f}x")
    assert clean2_std < raw2_std * 0.5, "孤立异常应被中值+限速抑制"
    assert pp2.dropped_frames >= 10, "孤立突变应被识别为异常帧"

    # 自测3：真实握拳（协调运动）不应被丢弃、不应卡住
    # 四指同时 0°→70° 快速握拳（每帧 +5°），叠加轻微抖动
    pp3 = JointAnglePostProcess(joint_num=4, median_n=5,
                                min_cutoff=0.5, beta=0.02, max_delta_deg=8.0,
                                max_jump_deg=40.0, jump_ratio_threshold=3.0)
    base = 0.0
    out_prev = None
    frozen = 0
    for k in range(40):
        base = min(base + 5.0, 70.0)
        noisy = [base + random.uniform(-2, 2) for _ in range(4)]
        out = pp3.update(noisy, t0 + k * 0.05)
        if out_prev is not None and out == out_prev:
            frozen += 1   # 输出完全不变 → 卡住
        out_prev = list(out)
    print(f"[握拳运动] 40帧握拳 -> 输出末值 {out[0]:.1f}° 冻结帧数 {frozen}")
    assert frozen <= 3, "真实握拳运动不应被误判丢弃导致卡住"
    assert out[0] > 40.0, "握拳应能跟随到接近目标"
    assert pp3.dropped_frames <= 2, "真实协调运动不应被判为异常帧"

    # 自测4：拇指内外展（0-110°）平滑性：快速张开不应超限速跳变
    pp4 = JointAnglePostProcess(joint_num=16, median_n=5,
                                min_cutoff=0.5, beta=0.02, max_delta_deg=8.0,
                                abduct_max_delta_deg=3.0, max_jump_deg=40.0)
    prev16 = 0.0
    max_step = 0.0
    for k in range(60):
        noisy = [0.0] * 16
        noisy[15] = min(k * 5.0, 110.0)   # 内外展 0→110° 快速变化
        out = pp4.update(noisy, t0 + k * 0.05)
        max_step = max(max_step, abs(out[15] - prev16))
        prev16 = out[15]
    print(f"[内外展] 0→110° 快速张开 -> 最大单帧步进 {max_step:.2f}° (限速 {pp4.abduct_max_delta}°)")
    assert max_step <= pp4.abduct_max_delta + 1e-6, "内外展单帧步进应被限速"
    assert abs(out[15] - 110.0) < 15.0, "内外展应能跟随到目标（允许限速滞后）"

    # 自测5：深度确认握拳 → 即使角度大跳变也绝不丢弃/卡住
    pp5 = JointAnglePostProcess(joint_num=16, median_n=5,
                                min_cutoff=0.5, beta=0.02, max_delta_deg=8.0,
                                abduct_max_delta_deg=3.0, max_jump_deg=40.0)
    out_prev5 = None
    frozen5 = 0
    for k in range(40):
        base = min(k * 6.0, 70.0)
        noisy = [base + random.uniform(-3, 3) for _ in range(16)]
        noisy[15] = min(k * 4.0, 60.0)   # 握拳时内外展同时变化
        out = pp5.update(noisy, t0 + k * 0.05, fist_confidence=0.9)  # 深度确认握拳
        if out_prev5 is not None and out == out_prev5:
            frozen5 += 1
        out_prev5 = list(out)
    print(f"[深度确认握拳] 40帧 -> 冻结帧数 {frozen5}, 丢弃帧 {pp5.dropped_frames}")
    assert frozen5 <= 2, "深度确认握拳时输出不应卡住"
    assert pp5.dropped_frames == 0, "深度确认握拳时不应判为异常帧"
    print("JointAnglePostProcess 自测通过")
