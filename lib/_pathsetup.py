# -*- coding: utf-8 -*-
"""
_pathsetup.py —— 项目路径统一引导（解决"运行子目录单文件找不到根目录内容"）

问题：
  直接运行 `python apps/test_hand.py` 时，Python 只把脚本所在目录（apps/）
  加入 sys.path，导致：
    1) `from hand import ...` 等根目录包导入失败；
    2) ctypes.CDLL("RyhandLibx64.dll")、import PCANBasic / ControlCAN
       等相对路径资源（DLL、驱动文件）解析失败（依赖当前工作目录 CWD）。

解决：
  每个入口脚本（apps/*.py、gui/*.py、selfcheck.py 等）在 import 本项目模块
  **之前**调用本模块，完成两件事：
    ① 把项目根目录插入 sys.path  —— 让 `import hand/camera/vision/...` 生效；
    ② os.chdir(项目根目录)       —— 让 DLL/驱动文件的相对路径查找生效。

用法（入口脚本顶部，放在所有本项目 import 之前）：
    # ---- 路径引导（必须最先执行，放在本项目 import 之前） ----
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(sys.path[0])

说明：
  * 也可直接 `import _pathsetup; _pathsetup.ensure_root(__file__)`，
    但内联两行最稳妥（不依赖任何外部模块即可运行）。
  * 本模块同时供 hand 包内部使用：加载 DLL 时把根目录加入候选路径，
    避免"在子目录运行但忘了 chdir"导致的加载失败。
"""

from __future__ import annotations

import os
import sys
from typing import Optional


def project_root(anchor: Optional[str] = None) -> str:
    """项目根目录。

    本文件位于 <根目录>/lib/_pathsetup.py（用户已把资源统一移到 lib/），
    因此默认取本文件所在目录的父目录作为根目录。

    Args:
        anchor: 可选，若传入某入口文件路径，则取其父目录的父目录
                （apps/xxx.py -> 根目录）作为根目录；默认取 lib/ 的父目录。
    """
    if anchor is not None:
        return os.path.dirname(os.path.dirname(os.path.abspath(anchor)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_root(anchor: Optional[str] = None) -> str:
    """把项目根目录加入 sys.path 并切换到该目录。返回根目录绝对路径。

    在入口脚本顶部调用（放在本项目 import 之前）。
    """
    root = project_root(anchor)
    root = os.path.abspath(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        os.chdir(root)          # DLL / 驱动文件的相对路径查找依赖 CWD
    except OSError:
        pass
    return root


def root_candidates() -> list:
    """返回应搜索 DLL/驱动文件的目录候选列表（根目录优先）。"""
    roots = [os.getcwd()]
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in roots:
        roots.append(here)
    return roots
