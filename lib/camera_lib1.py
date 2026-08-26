# -*- coding: utf-8 -*-
"""
camera_lib1.py —— 摄像头模块（lib/ 转发入口）

用户已把 camera_lib1.py 原实现移到 lib/参考代码/ 子目录（与 L515_driver.py、
vision_hand_ctrl.py 一起作为参考代码归档）。为保持既有调用方式
  `from lib.camera_lib1 import CameraModule`
不变（gui/main_gui.py 等），本文件作为 **转发模块**：
  1. 先通过 lib._pathsetup.ensure_ref_code() 把 lib/参考代码/ 加入 sys.path；
  2. 再 `from 参考代码.camera_lib1 import *` 把真实实现的所有公开名转发过来。

注意：camera/camera_module.py（camera 包内版本）与本文件是**两套实现**，
不可互相替代（camera_lib1 带帧时间戳与 landmarks_to_3d 批量转换）。
"""

from __future__ import annotations

import os
import sys

# ---- 路径引导：lib/参考代码/ 加入 sys.path ----
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
try:
    from _pathsetup import ensure_ref_code
    ensure_ref_code()
except Exception:  # pragma: no cover
    _ref = os.path.join(_here, "参考代码")
    if os.path.isdir(_ref) and _ref not in sys.path:
        sys.path.insert(0, _ref)

# ---- 转发真实实现（lib/参考代码/camera_lib1.py）----
from 参考代码.camera_lib1 import *  # noqa: F401,F403,E402
from 参考代码.camera_lib1 import (  # noqa: F401,E402
    CameraModule,
    check_realsense_devices,
    L515_PYREALSENSE_VERSION,
    LAST_REALSENSE_ERROR,
)
