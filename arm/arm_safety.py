# -*- coding: utf-8 -*-
"""
arm_safety.py —— 机械臂末端【高度安全区】(z 轴单向保护) 模块

设计原则（用户明确决定，务必遵守）：
  ★ 坐标系基准：无意外情况一律使用【基底（基座）坐标系】；
  ★ 安全框只取 Z（高度）轴判定：xy 是相对基座的水平面坐标，机械臂末端跟随手/转向到
    不同方位时，基坐标系下的 xy 数值会大范围变化——把 xy 的固定区间当作"安全框"，
    会在"末端明明安全"时报越界，非常荒谬 → **xy 不计入安全框**；
  ★ 基坐标系的 z 与"离地面/桌面高度"方向一致，用 z 高度区间做单向保护：
      - z 低于下限 → 防末端/工具撞桌面；
      - z 高于上限 → 防末端升太高（防超出工作范围/碰撞上方物体）；
  ★ 末端碰撞盒（SDK addCollisionBox）与基座系 WorldZone 是另一套保护机制，
    以各自坐标系（末端/基座）为准，不受本模块影响。

用法：
  from arm.arm_safety import ArmSafetyBox
  safe = ArmSafetyBox(min_z=0.18, max_z=0.68)   # 基坐标系高度区间（米）
  ok, msg = safe.check_pose([0.5, -0.3, 0.45])  # 只看 pos[2]（z）
  safe.set_box(min_z=0.15, max_z=0.80)
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("arm_safety")

# 默认高度安全区（米，基坐标系）——z 下限防碰桌面，z 上限防升太高
DEFAULT_MIN_Z = 0.18
DEFAULT_MAX_Z = 0.68

# 兼容别名（旧代码可能引用 DEFAULT_MIN_XYZ / DEFAULT_MAX_XYZ 的 z 分量）
DEFAULT_MIN_XYZ = [0.0, 0.0, DEFAULT_MIN_Z]
DEFAULT_MAX_XYZ = [0.0, 0.0, DEFAULT_MAX_Z]

# z 合理物理范围（米）：正常正装机械臂 z≥0；允许 -1m（倒装/下沉安装）~ 3m
_Z_LIMIT_LO, _Z_LIMIT_HI = -1.0, 3.0


class ArmSafetyBox:
    """末端【高度安全区】：只按基坐标系 z 判定，防碰桌面 / 防升太高。

    说明：名称保留"Box"仅为兼容旧调用点；内部**仅比较 z 轴**，
    传入点坐标（pos=[x,y,z,...]）时 x/y 分量被忽略，绝不做 xy 平面框判定。
    """

    def __init__(self,
                 min_z: Optional[float] = None,
                 max_z: Optional[float] = None):
        """
        Args:
            min_z: 高度下限（米，基坐标系）；None 用默认
            max_z: 高度上限（米，基坐标系）；None 用默认
        """
        self.min_z = float(min_z if min_z is not None else DEFAULT_MIN_Z)
        self.max_z = float(max_z if max_z is not None else DEFAULT_MAX_Z)
        # 合法性防御：值非有限 / 超物理范围（疑似 cm 误用）/ 上下限颠倒 → 复位默认并告警
        if not self._values_sane(self.min_z, self.max_z):
            logger.error("[safety] 高度安全区参数异常(疑似单位错误/上下限颠倒)，已复位默认！"
                         " 传入 min_z=%s max_z=%s", min_z, max_z)
            self.min_z = DEFAULT_MIN_Z
            self.max_z = DEFAULT_MAX_Z

    @staticmethod
    def _values_sane(lo: float, hi: float) -> bool:
        """高度区间数值自检：单位米（[-1, 3]m），min_z ≤ max_z。"""
        try:
            lo_f, hi_f = float(lo), float(hi)
        except (TypeError, ValueError):
            return False
        if not (np.isfinite(lo_f) and np.isfinite(hi_f)):
            return False
        if lo_f < _Z_LIMIT_LO or hi_f > _Z_LIMIT_HI or hi_f < lo_f:
            return False
        return True

    # ------------------------------------------------------------------
    def set_box(self, min_z: Optional[float] = None,
                max_z: Optional[float] = None) -> bool:
        """运行时设置高度安全区（单位【米】，基坐标系）。返回是否设置成功。

        数值自检：非有限值 / |z| 超物理范围（疑 cm 当 m）/ min_z>max_z
        → 拒绝本次设置返回 False（保持原区间），绝不带病运行。
        """
        lo = float(min_z if min_z is not None else self.min_z)
        hi = float(max_z if max_z is not None else self.max_z)
        if not self._values_sane(lo, hi):
            logger.error("[safety] set_box 拒绝异常参数(单位/cm混淆或上下限颠倒): "
                         "min_z=%s max_z=%s（原区间保持不变）", min_z, max_z)
            return False
        self.min_z = lo
        self.max_z = hi
        logger.info("[safety] 高度安全区 = z[%.3f, %.3f] m（基坐标系）", lo, hi)
        return True

    def get_box(self) -> dict:
        return {"min_z": self.min_z, "max_z": self.max_z}

    def get_zone(self) -> Tuple[float, float]:
        return self.min_z, self.max_z

    # ------------------------------------------------------------------
    def clamp_pose(self, pos: List[float]) -> List[float]:
        """把目标位置的 z 裁剪进高度安全区（xy 保持不变——xy 不计入安全框）。"""
        if pos is None or len(pos) < 3:
            return list(pos) if pos else []
        z = float(np.clip(float(pos[2]), self.min_z, self.max_z))
        out = list(pos)
        out[2] = z
        return out

    def check_pose(self, pos: List[float],
                   margin: float = 0.0) -> Tuple[bool, str]:
        """判断点坐标是否在【高度安全区】内（只看 z，margin 单位米）。返回 (ok, 说明)。

        坐标系：z 为基坐标系下的高度（米）。x/y 分量被忽略，不做 xy 判定。
        读数异常（无 z / NaN / |z| 超物理范围）→ (False, "读数异常…")，
        避免把"读数错误"误报成"越界"误导排查。
        """
        if pos is None or len(pos) < 3:
            return False, "位置读数异常（长度不足，无法取 z），视为越界"
        try:
            z = float(pos[2])
        except (TypeError, ValueError):
            return False, "位置读数异常（z 无法解析为数值），视为越界"
        if not np.isfinite(z):
            return False, "位置读数异常（z 含 NaN/Inf），视为越界"
        if z < _Z_LIMIT_LO or z > _Z_LIMIT_HI:
            return False, f"z 读数异常({z:.3f}m 超物理范围 {_Z_LIMIT_LO}~{_Z_LIMIT_HI}m)，视为越界"
        lo = self.min_z + margin
        hi = self.max_z - margin
        if lo <= z <= hi:
            return True, "OK"
        if z < lo:
            return False, f"z低于下限({z:.3f}m<{lo:.3f}m)（防碰桌面）"
        return False, f"z超上限({z:.3f}m>{hi:.3f}m)（防升太高）"

    def check_path(self, start_pos: List[float], end_pos: List[float],
                   margin: float = 0.0, steps: int = 10) -> Tuple[bool, str]:
        """【路径级安全】检查从 start 到 end 的直线路径 z 是否全程在高度安全区内。

        直线段上 z 单调，等效检查各采样点 z；保留 steps 分段以兼容调用。
        单位：米（z 为基坐标系高度）。
        """
        if start_pos is None or end_pos is None or len(start_pos) < 3 or len(end_pos) < 3:
            return False, "路径读数异常（长度不足，无法取 z），视为越界"
        try:
            zs = float(start_pos[2])
            ze = float(end_pos[2])
        except (TypeError, ValueError):
            return False, "路径读数异常（z 无法解析为数值），视为越界"
        if not (np.isfinite(zs) and np.isfinite(ze)):
            return False, "路径读数异常（z 含 NaN/Inf），视为越界"
        for i in range(steps + 1):
            t = i / steps
            z = zs + (ze - zs) * t
            ok, msg = self.check_pose([0.0, 0.0, z], margin=margin)
            if not ok:
                return False, f"路径第{i}段越界: {msg}"
        return True, "OK"

    def describe(self) -> str:
        return f"高度安全区 z[{self.min_z:.2f},{self.max_z:.2f}] m（基坐标系，仅 z 轴）"


if __name__ == "__main__":
    safe = ArmSafetyBox()
    print(safe.describe())
    # z 越界裁剪（xy 保持不变）
    clipped = safe.clamp_pose([0.5, -0.3, 0.05])
    print(f"z=0.05 越界 -> 裁剪为 {clipped}（xy 不变）")
    assert clipped[2] >= safe.min_z - 1e-9 and clipped[0] == 0.5
    # 框内判定（只看 z；xy 随意变化不影响判定）
    ok, msg = safe.check_pose([0.5, -0.3, 0.45])
    print(f"[0.5,-0.3,0.45] -> ok={ok} {msg}")
    assert ok
    # ★ xy 完全不影响判定：只要 z 在区间内，任意 x/y 都算框内
    ok_side, _ = safe.check_pose([-0.8, 1.2, 0.45])
    print(f"[z=0.45, x/y任意] -> ok={ok_side}（应 True：xy 不计入安全框）")
    assert ok_side, "xy 不得参与安全框判定"
    # z 越界
    ok2, msg2 = safe.check_pose([0.5, 0, 0.05])
    print(f"[z=0.05] -> ok={ok2} {msg2}")
    assert not ok2 and "m" in msg2, "越界提示应带米单位"
    # ★ 单位防线：cm 值误用（min_z=18/max_z=68 → 疑 cm 当 m）→ 拒绝
    ok3 = safe.set_box(min_z=18.0, max_z=68.0)
    print(f"cm 值误用 set_box -> ok={ok3}（应为 False）")
    assert not ok3, "cm 量级参数必须被拒绝（单位防线）"
    # ★ 读数异常：NaN z → 报"读数异常"而非普通越界
    ok4, msg4 = safe.check_pose([0.5, 0.0, float("nan")])
    print(f"NaN z -> ok={ok4} {msg4}")
    assert (not ok4) and "读数异常" in msg4, "NaN z 应报读数异常"
    # 异常构造 → 自动复位默认
    ArmSafetyBox(min_z=0.3, max_z=0.1)
    print("ArmSafetyBox 自测通过（z-only + xy忽略 + 单位防线 + 读数异常防御 OK）")
