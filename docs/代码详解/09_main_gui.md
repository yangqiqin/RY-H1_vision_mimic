# 09 · `gui/main_gui.py` 代码详解

> 本文档对应源文件：`rycan_hand_windows/gui/main_gui.py`（共 841 行）
> 入口方式：`python -m gui.main_gui`（在 `rycan_hand_windows` 目录下执行）
>
> 本文件是整个「睿研 RY-H1(16) 灵巧手视觉动作模仿系统（Windows 版）」的**主综合 GUI**：它把相机采集、MediaPipe 手部姿态估计、16 关节角度计算、精度后处理、灵巧手 CAN/串口下发全部集成到一个 Tkinter 窗口里，是人机交互的唯一入口。

---

## 目录

1. [文件职责总览](#1-文件职责总览)
2. [ASCII 架构图：线程 / 回调 / 队列关系](#2-ascii-架构图线程--回调--队列关系)
3. [模块头部：导入与路径引导（L1–L40）](#3-模块头部导入与路径引导l1l40)
4. [参数配置体系（L42–L121）](#4-参数配置体系l42l121)
5. [`slider_range_for_joint`：关节范围映射（L124–L134）](#5-slider_range_for_joint关节范围映射l124l134)
6. [类 `MainGui` 总览与 `__init__`（L137–L177）](#6-类-maingui-总览与-initl137l177)
7. [`_build_ui`：完整布局逻辑（L179–L360）](#7-_build_ui完整布局逻辑l179l360)
8. [`_add_slider` / `_add_param_group`（L362–L378）](#8-_add_slider--_add_param_groupl362l378)
9. [配置持久化：`_load_calibration` / `_save_calibration`（L383–L419）](#9-配置持久化_load_calibration--_save_calibrationl383l419)
10. [相机：启动 / 停止 / 采集线程 / 视频轮询（L421–L640）](#10-相机启动--停止--采集线程--视频轮询l421l640)
11. [视频显示算法：等比缩放 + 居中裁剪（L601–L635）](#11-视频显示算法等比缩放--居中裁剪l601l635)
12. [`_apply_calib`：校准参数下发（L645–L669）](#12-_apply_calib校准参数下发l645l669)
13. [灵巧手控制（L671–L775）](#13-灵巧手控制l671l775)
14. [动作模仿：`_toggle_mimic` / `_mimic_apply`（L777–L809）](#14-动作模仿_toggle_mimic--_mimic_applyl777l809)
15. [`_on_close`：关闭清理与强制退出（L811–L831）](#15-_on_close关闭清理与强制退出l811l831)
16. [`main()` 入口（L834–L841）](#16-main-入口l834l841)
17. [操作流程：从零开始连接](#17-操作流程从零开始连接)
18. [布局设计决策](#18-布局设计决策)
19. [常见问题（FAQ）](#19-常见问题faq)
20. [参数速查表](#20-参数速查表)

---

## 1. 文件职责总览

`main_gui.py` 是系统的**前端总控**，职责可以归纳为四层：

| 层 | 职责 | 涉及对象 / 方法 |
|---|---|---|
| **UI 层** | 用 Tkinter 搭出顶部控制栏、中部视频+参数、底部 16 关节滑条 | `_build_ui`、`_add_slider`、`_add_param_group` |
| **采集层** | 独立线程从相机读帧，放入有界队列，避免阻塞 UI | `_capture_loop`、`_poll_video` |
| **算法层** | MediaPipe 手部姿态 → 16 关节角度；精度后处理链（方向一致性异常检测 + 中值 + One Euro + 分通道限速） | `HandPoseEstimator`、`JointAnglePostProcess` |
| **执行层** | 把 16 关节弧度下发到灵巧手（PCAN / CANII / RS485），并支持自检、回零、预设手型、单电机测试 | `RYH1HandController` |

数据流向一句话概括：

```
相机帧 → 姿态估计(est) → 16关节角度(度) → 精度后处理(post) → 弧度 → 灵巧手(hand)
```

整个文件**不包含任何底层算法实现**，只负责：创建底层对象、转发参数、调度线程与 Tk 回调、展示信息。因此本文件是理解整个系统「如何被拼起来」的最佳入口。

---

## 2. ASCII 架构图：线程 / 回调 / 队列关系

```
┌────────────────────────────────────────── 主线程（Tk mainloop，事件驱动）──────────────────────────────────────────┐
│                                                                                                                  │
│   ┌──────────────┐   创建     ┌──────────────────┐   创建     ┌─────────────────────┐    创建    ┌──────────────┐   │
│   │ CameraModule │◄──────────┤    MainGui       │──────────► │ HandPoseEstimator   │            │ RYH1Hand     │   │
│   │ (lib版)      │            │   (本文件)        │            │ (vision 包, est)     │            │ Controller   │   │
│   └──────┬───────┘            └────────┬─────────┘            └──────────┬──────────┘            └──────┬───────┘   │
│          │ read()                       │ 线程调度                          │ process()                   │          │
│          ▼                              ▼                                  ▼                             │ move_joints│
│   ┌──────────────────┐        ┌───────────────────┐            ┌─────────────────────┐                    │          │
│   │  _capture_loop   │  put   │   frame_q         │   get      │  _poll_video (Tk    │                    │          │
│   │  (后台线程,       │───────►│   (queue, max=2)  │◄───────────│  after 30ms 定时回调)│                    │          │
│   │   生产者)         │        └───────────────────┘            │   (消费者+推理+绘制) │                    │          │
│   └──────────────────┘                                          └─────────┬───────────┘                    │          │
│          ▲                                                               │ 推理 results                      │          │
│          │ daemon 线程                                                 ▼                                  │          │
│          │                                                     ┌─────────────────────┐                    │          │
│          │                                                     │  _mimic_apply        │  (mimic_on 开启时)   │          │
│          └────────────────────────────────────────────────────►│  多帧均值→deadzone→  │───────────────────►│          │
│                                                                 │  post.update → 弧度  │   hand.move_joints  │          │
│                                                                 └─────────────────────┘                    │          │
│                                                                                                             │          │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │  手动控制路径（不经过模仿链路）：底部滑条 → _slider_changed → hand.move_joints(弧度)                     │   │
│   └──────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

数据链路（详细）：
[相机帧 rgb/depth]
    │  _capture_loop（后台线程，~100fps 尽力读帧，最多缓存 2 帧，满了丢最旧）
    ▼
frame_q（有界队列 maxsize=2，天然"只保留最新帧"，缓解 UI 卡顿）
    │  _poll_video（Tk after(30ms) 定时回调，主线程执行，~33fps 上限）
    ▼
est.process(rgb, depth, intrinsics)  →  results（含 handedness / confidence / joint_angles_deg /
                                        lateral_dist / fist_confidence / avg_depth_mm）
    │  只保留"右手"结果（过滤）
    ▼
角度叠加 / 骨架绘制 → Canvas 显示（等比缩放+居中裁剪，无黑边无变形）
    │  （若 mimic_on 勾选 且 手已连接 且 有角度）
    ▼
_mimic_apply(angles_deg, fist_conf)
    │  ① 5 帧均值（angle_history deque(maxlen=5)） ② deadzone 归零 ③ post.update(度)
    │  ④ 度→弧度 ⑤ hand.move_joints(弧度)
    ▼
RYH1HandController → PCAN / CANII / RS485 → 灵巧手 16 电机
```

关键点：

- **两条并行度完全不同的链路**：采集线程以相机帧率尽力产帧；`_poll_video` 是 Tk 定时回调，每 30ms 最多跑一次（约 33fps），两者用有界队列解耦——采集快、消费慢时，旧帧被直接丢弃，界面永不堆积延迟。
- **Tk 不是线程安全的**：所有对 UI 的修改（Canvas 绘制、变量 set、`after` 调度）都发生在主线程的 `_poll_video` 里；采集线程只碰 `frame_q` 和 `self.cam.read()`，绝不碰 UI。
- **后处理链的吞吐位置**：`post.update()` 只在 `_mimic_apply` 中被调用（即动作模仿开启时才走完整后处理），而 `est` 每帧都会推理。

---

## 3. 模块头部：导入与路径引导（L1–L40）

```python
# -*- coding: utf-8 -*-
"""
main_gui.py —— 综合控制界面（视频区域固定 16:9，无黑边）
"""
from __future__ import annotations
```

- `# -*- coding: utf-8 -*-`：声明源码为 UTF-8，保证中文注释/字符串正确。
- `from __future__ import annotations`：让类型注解（如 `CameraModule | None`）延迟求值为字符串，Python 3.9 以下也能用 `|` 语法，同时避免运行时求值开销。

### 3.1 路径引导（L20–L27）—— 最关键的一步

```python
# ---- 路径引导 ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
```

逐行解读：

| 行 | 代码 | 作用 |
|---|---|---|
| L21 | `os.path.abspath(__file__)` | 取本文件绝对路径，如 `...\rycan_hand_windows\gui\main_gui.py` |
| L21 | 外层 `os.path.dirname` | 去掉文件名 → `...\rycan_hand_windows\gui` |
| L21 | 内层 `os.path.dirname` | 再去一层 → `...\rycan_hand_windows`（项目根目录） |
| L21 | `sys.path.insert(0, ...)` | 把项目根目录插入 `sys.path` **最前面**，保证 `import lib.camera_lib1`、`import vision`、`import hand` 一定从本项目解析（即使当前工作目录不对也能找到） |
| L22 | `os.chdir(sys.path[0])` | **把进程工作目录切到项目根目录**。这保证后续相对路径操作（如读取 `config/calibration.json`）与模型文件加载都以项目根为基准 |
| L23–L27 | `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")` | Windows 控制台默认 GBK，遇到中文日志会抛 `UnicodeEncodeError`；这里强制 UTF-8 输出并把无法编码的字符替换为 `?`，保证中文日志不崩溃 |

> ⚠️ **为什么必须有两层 dirname？**
> 因为 `__file__` 指向 `gui/` 子目录内的文件，需要向上跳两级才回到根目录。
> ⚠️ **为什么先插 path 再 chdir？** 因为 `sys.path[0]` 在 `insert(0, ...)` 之后就是项目根目录，`os.chdir(sys.path[0])` 直接引用它，两行共用同一个值，不会写错。

### 3.2 依赖导入（L29–L36）

```python
import cv2
import numpy as np
from PIL import Image, ImageTk

from lib.camera_lib1 import CameraModule          # lib 版相机模块（支持时间戳 / landmarks_to_3d）
from vision import HandPoseEstimator              # MediaPipe 手部姿态估计器
from vision.postprocess import JointAnglePostProcess  # 精度后处理链
from hand import RYH1HandController, JOINT_NAMES_CN, JOINT_NUM, status_text
```

- `CameraModule` 特意从 `lib.camera_lib1` 导入（而不是 `camera` 包），因为 **lib 版支持时间戳与 `landmarks_to_3d`**，能配合深度相机输出 3D 关键点，这是拇指内外展与握拳置信度计算的输入基础。
- `JOINT_NUM = 16`（见 `hand/hand_config.py` L28），全文件都用它而非魔法数。
- `JOINT_NAMES_CN`：16 个关节的中文名，用于滑条标签与信息面板。
- `status_text`：电机状态码转中文文本，用于单电机测试回读显示。

### 3.3 日志配置（L38–L40）

```python
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main_gui")
```

- 根日志级别 INFO，格式含时间/级别/模块名。
- `logger` 是"main_gui"命名空间的句柄，`_start_camera`/`_stop_camera`/`_capture_loop`/`_poll_video` 等处的运行轨迹都靠它输出（`>>>` 前缀的日志是作者留下的流程跟踪标记）。

---

## 4. 参数配置体系（L42–L121）

整个系统的可调参数被收敛成两个字典，**全部由 UI 滑条/复选框驱动**，是理解"参数从哪来、到哪去"的核心。

### 4.1 `PARAM_CONFIG`（L45–L112）—— 连续型参数（滑条）

字典结构：`key → {"label": 中文名, "range": (min, max, step), "default": 默认值, "desc": 说明}`。

| key | label | range (min,max,step) | 默认 | 作用 | 下发目标 |
|---|---|---|---|---|---|
| `bend_gain` | 弯曲增益 | (0.5, 2.5, 0.05) | 1.0 | 放大/缩小弯曲幅度（整体增益） | `est.update_params(bend_gain=...)` |
| `bend_scale` | 缩放 | (0.5, 1.5, 0.05) | 1.0 | 整体弯曲比例（二次缩放，与 gain 叠加使用） | `est.update_params(bend_scale=...)` |
| `bend_offset` | 偏置 | (-30, 30, 1) | 0 | 固定角度偏置（度），补偿机械零位偏差 | `est.update_params(bend_offset=...)` |
| `deadzone` | 死区 | (0, 10, 0.5) | 1.0 | 消除微动：|角度|<deadzone 时归零（度） | `est.update_params(deadzone_deg=...)` **且** `_mimic_apply` 中做静态 deadzone |
| `smooth` | 平滑系数 | (0.1, 0.9, 0.05) | 0.35 | 平滑强度（滑条保留，但**未在 `_apply_calib` 中下发**——注意：它只被 `est.update_params` 的 `**kwargs` 忽略，属于"占位/历史遗留"参数） | 无实际下发（详见下方注意） |
| `min_cutoff` | 平滑强度(1€) | (0.1, 2.0, 0.05) | 0.5 | One Euro 滤波器最小截止频率，**越小越平滑**（也越迟钝） | `post.update_params(min_cutoff=...)` |
| `beta` | 跟手度(1€) | (0.0, 0.2, 0.005) | 0.02 | One Euro 速度自适应系数，**越大越跟手**（对快速运动响应越快） | `post.update_params(beta=...)` |
| `max_delta` | 限速°/帧 | (1.0, 20.0, 0.5) | 8.0 | 弯曲通道每帧最大角度变化（防突跳） | `post.update_params(max_delta_deg=...)` |
| `thumb_abd_offset` | 内外展死区 | (0.0, 0.5, 0.01) | 0.0 | 以"手掌宽度倍数"为单位的死区：切除并拢时底部无效区间 | `est.update_params(thumb_abd_offset=...)`（构造函数同参） |
| `thumb_abd_gain` | 内外展增益 | (0.3, 2.0, 0.05) | 0.8 | 放大归一化横向距离（TIP 到掌根的水平距离 / 掌宽） | `est.update_params(thumb_abd_gain=...)`（构造函数同参） |
| `abduct_max_delta` | 内外展限速°/帧 | (0.5, 8.0, 0.5) | 2.0 | 内外展通道单帧最大变化（越小越稳，防止外展轴抖动） | `post.update_params(abduct_max_delta_deg=...)` |

> 📌 **关于 `smooth` 的注意点**：`_apply_calib`（L645–L669）下发参数时**没有把 `smooth` 传给 est 或 post**——`est.update_params` 使用 `**kwargs` 白名单匹配，未知 key 会被静默忽略。即：GUI 上拖动"平滑系数"滑条**不会产生任何实际效果**，它是早期版本遗留（当时的平滑逻辑已被 One Euro 的 `min_cutoff`/`beta` 取代）。滑条仍保留是为了 UI 兼容与调试。
>
> 📌 **deadzone 双通道生效**：一方面通过 `est.update_params(deadzone_deg=...)` 在**估计器内部**对角度做死区；另一方面 `_mimic_apply`（L798–L800）在**模仿链路上再次**做静态死区。两处叠加，保证"手微微颤动"时输出为 0。

### 4.2 `CHECKBOX_CONFIG`（L114–L121）—— 开关型参数（复选框）

| key | label | 默认 | 作用 | 下发目标 |
|---|---|---|---|---|
| `bend_reverse` | 弯曲反转 | False | 弯曲角度方向取反（针对镜像安装/左右手差异） | `est.update_params(bend_reverse=...)` |
| `thumb_abd_reverse` | 内外展反转 | False | 拇指外展方向取反 | `est.update_params(thumb_abd_reverse=...)` |
| `use_dist_ratio` | 距离比法 | False | 是否用"距离比"法计算关节角（替代默认角度法） | `est` 构造函数 + `est.update_params(use_distance_ratio=...)` |
| `show_skeleton` | 显示骨架 | True | 在画面上叠加 21 点骨架连线 | 仅 UI（`est.draw_skeleton`） |
| `show_angles` | 显示关节角 | True | 在画面上叠加 16 个关节角度文本 | 仅 UI（cv2.putText） |
| `mimic_on` | 动作模仿 | False | 是否把识别角度实时下发到手（总开关） | 触发 `_toggle_mimic`，控制 `_poll_video` 中的模仿分支 |

> 复选框的 UI 行为分两种（L282–L291）：
> - `mimic_on` → 回调 `self._toggle_mimic`（需要重置后处理状态）；
> - 其余 5 个 → 回调 `self._apply_calib`（即时把开关值同步进底层模块）。

---

## 5. `slider_range_for_joint`：关节范围映射（L124–L134）

```python
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
```

输入是 0~15 的关节索引，输出该关节滑条的 `(下限, 上限)`（单位：度）。这个函数与 `hand/hand_config.py` 里的 `ANGLE_RANGE_DEG` **一一对应**：

| 关节分组 | 索引规律 | 物理含义 | 范围 | 对应 `ANGLE_RANGE_DEG` |
|---|---|---|---|---|
| 拇指侧摆 | `i == 0` | 拇指根部左右摆动（可负，伸到负方向） | ±20.0 | `swing: (-20, 20)` |
| 其余指的侧摆 | `i % 3 == 0`（i=3,6,9,12） | 食指~小指的侧摆轴 | ±20.0 | `swing: (-20, 20)` |
| 近端关节 MCP | `i % 3 == 1`（i=1,4,7,10,13） | 手指根部弯曲 | 0~90.0 | `prox: (0, 90)` |
| 远端关节 PIP | `i % 3 == 2`（i=2,5,8,11,14） | 手指第二指节弯曲 | 0~75.0 | `dist: (0, 75)` |
| 拇指内外展 | `i == 15` | 第 16 关节：拇指整体外展/内收 | 0~110.0 | `joint16: (0, 110)` |

### 5.1 为什么是这个规律？

关节编号是按手指顺序连续排布的（见 `JOINT_NAMES_CN`，L40–L47）：

```
索引:  0       1       2      |  3       4       5      |  6       7       8      | ...
关节: 拇指侧摆 拇指MCP 拇指PIP | 食指侧摆 食指MCP 食指PIP | 中指侧摆 中指MCP 中指PIP | ...
索引: 15 = 拇指内外展
```

- 除拇指外，每根手指占 3 个连续索引，**每组的第 1 个是侧摆（i%3==0）**，第 2 个是 MCP（i%3==1），第 3 个是 PIP（i%3==2）。
- 侧摆轴物理上能双向摆动 → 允许负值（±20°）；弯曲轴只能向掌心方向弯 → 0 起。
- 拇指只有 2 个弯曲关节（MCP、PIP），它的"侧摆"（i=0）规则与其它指一致（±20）；而 i=1、i=2 走 `i%3==1/2` 分支，恰好命中 MCP(0~90)/PIP(0~75)。
- **i==15（拇指内外展）** 是唯一的特例：它是第 16 个电机、独立轴，范围 0~110°（`K16 = 4095/110`，见 hand_config L51）。
- 该函数只影响**手动滑条**的 UI 范围；模仿链路中 `post` 输出的角度理论上受 `est` 内部钳制，滑条范围与 `ANGLE_RANGE_DEG` 一致是为了手动控制不越界（底层 `move_motor` 也会做 0~4095 位置钳制，双保险）。

---

## 6. 类 `MainGui` 总览与 `__init__`（L137–L177）

### 6.1 类的状态一览

| 属性 | 类型 | 含义 |
|---|---|---|
| `self.cam` | `CameraModule \| None` | 相机模块（lib 版），启动后非 None |
| `self.est` | `HandPoseEstimator \| None` | MediaPipe 姿态估计器 |
| `self.hand` | `RYH1HandController \| None` | 灵巧手控制器 |
| `self.frame_q` | `queue.Queue(maxsize=2)` | 采集线程→UI 的有界帧队列 |
| `self._running` | `bool` | 采集/轮询运行标志（False 即停止一切） |
| `self._smoother_state` | `list[16]` | 平滑器历史状态（仅在开关模仿时重置） |
| `self._capture_thread` | `Thread \| None` | 采集线程 |
| `self._stop_thread` | `Thread \| None` | 释放相机资源的后台线程 |
| `self._after_id` | `str \| None` | Tk `after` 回调 id（用于取消调度） |
| `self.angle_history` | `deque(maxlen=5)` | 最近 5 帧关节角（模仿链路多帧均值用） |
| `self.post` | `JointAnglePostProcess` | 精度后处理链实例 |
| `self.param_vars` | `dict` | PARAM_CONFIG 每个 key → `DoubleVar` |
| `self.checkbox_vars` | `dict` | CHECKBOX_CONFIG 每个 key → `BooleanVar` |
| `self.finger_vars` | `dict` | 5 指增益 → `DoubleVar` |
| `self.finger_offset_vars` | `dict` | 5 指偏移 → `DoubleVar` |
| `self.angle_vars` / `self.sliders` | `list` | 16 个手动滑条变量 / 控件 |
| `self.config_dir` / `self.config_path` | `str` | `config/` 目录与 `calibration.json` 路径 |

### 6.2 `__init__` 执行顺序（L138–L177）

```python
def __init__(self, root: tk.Tk):
    self.root = root
    self.root.title("睿研 RY-H1(16) 灵巧手 · 视觉控制台")
    self.root.geometry("1600x900")
```

1. **窗口基础**：标题 + 初始尺寸 1600×900。
2. **置空三大对象**（L143–L145）：`cam` / `est` / `hand` 先置 None，后续按需创建，保证"未启动也能打开界面"。
3. **线程与队列初始化**（L147–L152）：
   - `frame_q = queue.Queue(maxsize=2)`：有界队列，容量 2。这是**生产者-消费者解耦**的核心——采集线程永不阻塞等待 UI，UI 慢时旧帧自动被挤掉（见 `_capture_loop` L501–L506 的"满则丢最旧"逻辑）。
   - `_smoother_state = [0.0] * JOINT_NUM`：16 维平滑状态。
   - `_capture_thread` / `_stop_thread` / `_after_id` 置 None。
4. **角度历史队列**（L154）：`angle_history = deque(maxlen=5)` —— 模仿链路的多帧均值窗口。
5. **创建精度后处理链**（L156–L162）：

   ```python
   self.post = JointAnglePostProcess(
       joint_num=JOINT_NUM, median_n=5,
       min_cutoff=0.5, beta=0.02,
       max_delta_deg=8.0, abduct_max_delta_deg=3.0,
       max_jump_deg=40.0, jump_ratio_threshold=3.0,
   )
   ```

   一次性配置好整条后处理链：
   - `median_n=5`：中值滤波窗口 5 帧（去孤立毛刺）；
   - `min_cutoff=0.5 / beta=0.02`：One Euro 滤波初始参数（后续被滑条覆盖）；
   - `max_delta_deg=8.0`：弯曲通道每帧限速 8°/帧；
   - `abduct_max_delta_deg=3.0`：内外展通道限速 3°/帧（**初始值 3.0 与 GUI 默认 2.0 不同**，一旦拖动滑条即以 GUI 值为准）；
   - `max_jump_deg=40.0 / jump_ratio_threshold=3.0`：方向一致性异常检测阈值（单通道跳变 >40° 且 >3 倍中位跳变 → 判定为孤立突变，用中值替代）。
6. **参数变量字典**（L164–L168）：四个空 dict 待 `_build_ui` 填充。
7. **构建 UI**（L170）：`self._build_ui()` —— 注意它在加载校准**之前**执行，因为校准加载要往已创建的 `param_vars` / `checkbox_vars` / `finger_vars` 里写值。
8. **校准配置持久化准备**（L172–L175）：

   ```python
   self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
   os.makedirs(self.config_dir, exist_ok=True)
   self.config_path = os.path.join(self.config_dir, "calibration.json")
   self._load_calibration()
   ```

   - 配置文件位置：`rycan_hand_windows/config/calibration.json`（与 `__file__` 相对，向上两级 + `config` 子目录）。
   - `makedirs(exist_ok=True)` 保证目录存在（首次运行自动创建）。
   - 随后立即 `_load_calibration()` 把上次保存的参数回填到 UI 变量。
9. **关闭挂钩**（L177）：

   ```python
   self.root.protocol("WM_DELETE_WINDOW", self._on_close)
   ```

   拦截窗口右上角 ✕，改为走 `_on_close`（先清理资源再 `os._exit(0)`，见 §15）。

> 💡 **设计要点**：`post` 在 `__init__` 就创建，而 `est` 在 `_start_camera` 才创建。原因是 `post` 是纯数值模块（无相机依赖），需要常驻以统计稳定性指标；`est` 依赖 MediaPipe 与相机分辨率，跟随相机生命周期。

---

## 7. `_build_ui`：完整布局逻辑（L179–L360）

### 7.1 控制变量（L180–L187）

| 变量 | 类型 | 默认 | 用途 |
|---|---|---|---|
| `cam_mode` | `StringVar` | `"usb"` | 相机类型：`"usb"` / `"realsense"` |
| `cam_idx` | `IntVar` | 0 | USB 设备索引 / L515 序号 |
| `hand_method` | `StringVar` | `"pcan"` | 通信方式：`pcan` / `canii` / `rs485` |
| `hand_lr` | `IntVar` | 1 | 1=右手，0=左手 |
| `status_var` | `StringVar` | `"未连接"` | 顶部蓝色状态文字（手连接状态） |
| `state_var` | `StringVar` | `"相机未启动"` | 视频区绿色状态文字（相机状态） |
| `info_var` | `StringVar` | `"等待相机..."` | 右侧"实时参数"面板文字 |

### 7.2 根窗口网格（L190–L194）

```
row 0  weight=0  顶部控制栏（固定高）
row 1  weight=1  中部（视频+参数，占所有剩余空间）
row 2  weight=0  底部 16 关节滑条区
row 3  weight=0  底部按钮区
column 0 weight=1 （单列撑满）
```

只有中部行可伸缩 → 窗口拉大时视频/参数区变大，顶部和底部条保持原高。

### 7.3 顶部控制栏（L196–L223）

自左向右用 `pack(side="left")` 依次排布：

1. **相机组**：`相机:` 标签 → `USB`/`L515` 单选（绑定 `cam_mode`）→ `索引:` 标签 → 0~9 Spinbox（`cam_idx`）→ `启动` 按钮（`_start_camera`）→ `停止` 按钮（`_stop_camera`）。
2. **竖分隔线**：`ttk.Separator(orient="vertical")` 视觉分组。
3. **手通信组**：`手通信:` 标签 → `PCAN`/`CANII`/`RS485` 单选（value 为小写，绑定 `hand_method`）→ `右手`/`左手` 单选（绑定 `hand_lr`，**带 `command=self._on_hand_lr`**，切换立即生效）→ `连接`（`_connect_hand`）→ `自检`（`_check_hand`）→ `回零`（`_homing`）→ `断开`（`_disconnect_hand`）。
4. **状态文字**：蓝色 `status_var`（如"已连接（pcan）"）。

### 7.4 中部：视频 + 参数（L225–L318）

```
mid_frame  (row=1, sticky=nsew)
 ├── 列 0  weight=58  ← 左：视频区
 └── 列 1  weight=42  ← 右：参数面板
```

**左侧视频区（L233–L250）**：

- `ttk.LabelFrame` 标题"实时画面（保持原相机比例，等比缩放居中）"，内部 `grid_rowconfigure(0, weight=1)` + `grid_columnconfigure(0, weight=1)`，让 Canvas 撑满。
- `self.video_canvas = tk.Canvas(vid_frame, bg="black", ...)`：黑色底（裁剪溢出时不露白）。
- Canvas 下方两行状态文字：`video_info_var`（灰色，显示相机分辨率/缩放倍数）和 `state_var`（绿色，相机运行状态）。

**右侧参数面板（L252–L318）**：

- 外层 `right_frame`，内部 `param_canvas_frame` 用 `grid_columnconfigure(0/1, weight=1)` 均分两列。
- **左列 `col_left`**（自上而下三个分组）：
  1. `全局校准`（LabelFrame）：`_add_param_group(cal_frame, ["bend_gain", "bend_scale", "bend_offset", "deadzone", "smooth", "min_cutoff", "beta", "max_delta"])` —— 8 个滑条。
  2. `拇指内外展校准`：`["thumb_abd_offset", "thumb_abd_gain", "abduct_max_delta"]` —— 3 个滑条。
  3. `控制开关`：遍历 `CHECKBOX_CONFIG`，每项一个 Checkbutton；**`mimic_on` 走 `_toggle_mimic` 回调，其余走 `_apply_calib` 回调**；用 `grid(row=idx//2, column=idx%2)` 排成 **3 行 × 2 列**。
- **右列 `col_right`**（自上而下三个分组）：
  1. `每指增益`：`finger_names = ["thumb","index","middle","ring","pinky"]`，显示名"拇指/食指/中指/无名指/小指"，每个 `DoubleVar(value=1.0)`，滑条范围 (0.5, 2.0, 0.05)，存入 `finger_vars`。
  2. `每指偏移`：同样 5 指，`DoubleVar(value=0.0)`，范围 (-30, 30, 1)，存入 `finger_offset_vars`。
  3. `实时参数`：`pack(fill="both", expand=True)` 吃掉剩余空间，内部一个等宽字体（Consolas 8）的 Label 绑定 `info_var`，显示手部置信度/深度/16 关节角/稳定性统计。

### 7.5 底部：16 关节手动滑条（L320–L345）

```python
bot_frame = ttk.LabelFrame(self.root, text="16 关节手动控制（长方形布局）")
bot_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

self.angle_vars = []
self.sliders = []
cols = 8                      # 8 列 × 2 行 = 长方形（更宽更扁）
slider_len = 120
for i in range(JOINT_NUM):
    row = (i // cols) * 2
    col = i % cols
    ...
```

- **8 列 × 2 行**：`row = (i // 8) * 2`（每行占 2 个 grid 行：标签行 + 滑条行），`col = i % 8`。
- 每格是一个 `ttk.Frame`，内含：`标签（如 "1:拇指侧摆"，字号 7）` + `tk.Scale(水平, from_=lo, to=hi, resolution=0.5, length=120, command=...)`。
- 滑条 `command=lambda _v, idx=i: self._slider_changed(idx)` —— **注意用 `idx=i` 默认参数闭包捕获**，否则 lambda 全部捕获同一个循环尾值 i=15。
- `resolution=0.5`：步进 0.5°。
- 循环结束后 `for c in range(cols): bot_frame.grid_columnconfigure(c, weight=1)` —— 8 列均分宽度，滑条区横向撑满窗口。

### 7.6 底部按钮区（L347–L360）

自左向右：`张开`（`_preset_open`）、`握拳`（`_preset_close`）、`放松`（`_preset_relax`）、`归零`（`_preset_zero`）、`单电机 ID:` Spinbox(1~16, 默认 9)、`位置:` Spinbox(0~4095, 默认 2048)、`测试`（`_test_motor`）。

---

## 8. `_add_slider` / `_add_param_group`（L362–L378）

### 8.1 `_add_slider`（L362–L370）

```python
def _add_slider(self, parent, label, var, from_, to, resolution):
    """添加单个滑条行（紧凑，适合方形面板全部显示）"""
    f = ttk.Frame(parent)
    f.pack(fill="x", padx=2, pady=0)
    ttk.Label(f, text=label, width=6, font=("", 8)).pack(side="left")
    tk.Scale(f, from_=from_, to=to, resolution=resolution, orient=tk.HORIZONTAL,
             variable=var, length=110, showvalue=False,
             command=lambda _: self._apply_calib()).pack(side="left", fill="x", expand=True)
    ttk.Label(f, textvariable=var, width=5, font=("", 8)).pack(side="left")
```

- 一行三件套：**左标签（固定宽 6 字符）→ 中滑条（固定长 110px，`showvalue=False` 隐藏 Tk 自带数值）→ 右数值（`textvariable=var` 实时回显）**。
- **每个滑条拖动都触发 `_apply_calib()`**：即"松手前每动一格就同步一次底层 + 保存一次 json"。这是为了让用户能看到实时效果；代价是拖动时频繁写盘（见 §12 的讨论）。
- `width=6` 标签 + `width=5` 数值，保证所有参数行对齐成整齐的列（方形面板观感）。

### 8.2 `_add_param_group`（L372–L378）

```python
def _add_param_group(self, parent, keys):
    """添加参数组（每个参数一个滑条）"""
    for key in keys:
        cfg = PARAM_CONFIG[key]
        var = tk.DoubleVar(value=cfg["default"])
        self.param_vars[key] = var
        self._add_slider(parent, cfg["label"], var, cfg["range"][0], cfg["range"][1], cfg["range"][2])
```

- 给定一组 key，从 `PARAM_CONFIG` 取配置，创建 `DoubleVar(default)`，注册进 `param_vars`，再调用 `_add_slider` 生成滑条行。
- 滑条范围/步进直接取自 `cfg["range"]` 三元组 `(min, max, step)`。
- 这是"配置字典驱动 UI"的典型写法：**加一个新参数只需在 `PARAM_CONFIG` 加一条 + 在 `_build_ui` 的 group 列表里加 key**，UI 代码零改动。

---

## 9. 配置持久化：`_load_calibration` / `_save_calibration`（L383–L419）

配置文件：`rycan_hand_windows/config/calibration.json`。

### 9.1 `_load_calibration`（L383–L405）

1. **文件不存在直接返回**（L384–L385）——首次运行无配置，全部用默认值。
2. 读 JSON 到 `data` dict。
3. **回填三类变量**（容错：只回填存在的 key）：
   - `param_vars`：全局校准滑条值；
   - `checkbox_vars`：开关状态；
   - `data["per_finger_scale"]` → `finger_vars`（每指增益）；
   - `data["per_finger_offset"]` → `finger_offset_vars`（每指偏移）。
4. 成功日志 `"校准配置已加载"`；任何异常（如 JSON 损坏）只 `logger.warning`，**不弹窗不崩溃**——让界面用默认参数继续跑。

> ⚠️ **注意**：加载只写 UI 变量，**不会**立即同步进 `est`/`post`（因为此时 `est` 可能还没创建）。真正的同步发生在 `_start_camera` 创建 `est` 后调用 `_apply_calib()`（L441），以及用户首次拖动任意滑条时。

### 9.2 `_save_calibration`（L407–L419)

1. 收集全部变量当前值：`param_vars` + `checkbox_vars` + `per_finger_scale` + `per_finger_offset`。
2. `json.dump(data, f, indent=2, ensure_ascii=False)` —— **`ensure_ascii=False` 保证中文 label 无关紧要，但数值以 UTF-8 明文保存，方便手工编辑校准文件**；`indent=2` 保证人类可读。
3. 失败只告警不崩溃。

> 触发时机：`_apply_calib` 末尾（每次滑条/复选框变化）→ 相当于"自动保存"，用户不需要点任何保存按钮。

---

## 10. 相机：启动 / 停止 / 采集线程 / 视频轮询（L421–L640）

### 10.1 `_start_camera`（L424–L450）

```python
def _start_camera(self):
    if self.cam is not None:
        self._stop_camera()          # 已启动则先停（支持热切换相机）
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
        self._apply_calib()          # 把加载的校准参数一次性同步进 est/post
        self._running = True
        self._after_id = None
        self._stop_thread = None
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self.state_var.set("相机已启动")
        self._poll_video()           # 手动触发第一帧轮询（启动 after 链）
    except Exception as exc:
        messagebox.showerror("相机启动失败", str(exc))
```

关键点：

- **分辨率选择**：L515 用 1280×720（深度 1024×768），USB 用 640×480。深度分辨率只在 realsense 模式生效。
- **`est` 在这里才创建**：构造参数直接读取当前 UI 变量（距离比法/拇指外展三参数），之后用 `_apply_calib()` 一次性同步剩余全部参数——保证"加载的校准"与"UI 当前值"一致。
- **线程启动顺序**：先 `_running=True`，再启动采集线程，最后**手动调用一次 `_poll_video()`** 让 after 回调链"自举"起来（之后 `_poll_video` 自己会调度自己）。
- 任何异常（相机被占用、无设备等）弹 `messagebox.showerror`，界面不崩。

### 10.2 `_stop_camera`（L452–L492）—— 三步停止 + 后台释放

```python
def _stop_camera(self):
    logger.info(">>> _stop_camera 开始")
    self._running = False                              # ① 停标志：采集线程与轮询链立刻退出

    if hasattr(self, '_after_id') and self._after_id is not None:
        try:
            self.root.after_cancel(self._after_id)     # ② 取消挂起的 after 回调
            self._after_id = None
        except Exception:
            pass

    if hasattr(self, '_capture_thread') and self._capture_thread and self._capture_thread.is_alive():
        self._capture_thread.join(timeout=0.5)         # ③ 等采集线程退出（最多 0.5s）

    while not self.frame_q.empty():                    # ④ 清空队列，防止残留帧被下一轮消费
        try:
            self.frame_q.get_nowait()
        except queue.Empty:
            break

    cam_to_release = self.cam
    est_to_close = self.est
    self.cam = None                                    # ⑤ 先置空引用，防止轮询期间再用到
    self.est = None

    def release_resources():                           # ⑥ 后台线程慢慢释放（release/close 可能卡）
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
    self._stop_thread.start()                          # ⑦ 立即返回，不阻塞 UI
    self.state_var.set("相机停止中...")
    logger.info(">>> _stop_camera 完成（主线程）")
```

设计要点：

- **三步停止**：`_running=False`（逻辑停）→ `after_cancel`（停 UI 回调）→ `join(0.5)`（停采集线程）。
- **为什么释放资源要丢给后台线程？** `cam.release()` / `est.close()` 在某些驱动（尤其 realsense）下可能阻塞数百毫秒甚至更久。若在 UI 线程同步执行，用户点"停止"窗口会卡死。用 daemon 线程异步释放，UI 立即恢复响应。
- **先置 None 再释放**：防止 `_poll_video` 在释放过程中访问到半释放对象。
- **清空队列**：防止"停止→快速启动"后，旧帧被新轮询链消费导致首帧是残影。

### 10.3 `_capture_loop`（L494–L512）—— 生产者

```python
def _capture_loop(self):
    while self._running and self.cam is not None:
        try:
            rgb, depth = self.cam.read()
            if rgb is None:
                time.sleep(0.005)          # 读帧失败（如相机还在初始化）短暂退避
                continue
            if self.frame_q.full():
                try:
                    self.frame_q.get_nowait()   # 队列满 → 丢最旧帧
                except queue.Empty:
                    pass
            self.frame_q.put((rgb, depth), timeout=0.1)
        except queue.Full:
            pass
        except Exception as exc:
            logger.warning("capture: %s", exc)
        time.sleep(0.01)                   # 限速 ~100Hz 轮询，避免空转烧 CPU
    logger.info("_capture_loop 退出")
```

- **有界队列 + 满则丢旧**：`frame_q` 容量 2，满时先 `get_nowait()` 丢掉最旧帧再 `put` 新帧。**效果 = 队列里永远是最新 1~2 帧**，天然解决"UI 卡顿时画面越来越滞后"的问题（视觉上会丢帧，但不会延迟累积）。
- `read()` 返回 `(rgb, depth)` 二元组：lib 版相机把深度图一起返回（USB 模式 depth 可能为 None，`est.process` 内部兼容）。
- 退出条件：`_running` 变 False 或 `cam` 被置 None。

### 10.4 `_poll_video`（L514–L640）—— 消费者 + 推理 + 绘制 + 显示 + 模仿

这是**整个 UI 的心脏**，每 30ms（约 33fps）由 Tk `after` 调度执行一次，完整流程：

```
① 取帧（非阻塞）
② 获取相机内参（intrinsics，用于 2D→3D）
③ est.process(rgb, depth, intrinsics) 推理
④ 过滤：只保留"右手"结果
⑤ 可选：draw_skeleton 绘制骨架
⑥ 可选：cv2.putText 叠加 16 关节角
⑦ 可选（mimic_on）：_mimic_apply(angles_deg, fist_conf) 下发到手
⑧ 更新右侧"实时参数"文字（含稳定性统计）
⑨ 等比缩放 + 居中裁剪 → Canvas 显示
⑩ 调度下一帧：root.after(30, self._poll_video)
```

**① 取帧（L518–L523）**：

```python
try:
    rgb, depth = self.frame_q.get_nowait()
except queue.Empty:
    if self._running:
        self._after_id = self.root.after(30, self._poll_video)  # 没帧也继续轮询
    return
```

- 队列空则**不做事**，直接调度 30ms 后再来（保持画面连续，不闪烁）。

**② 内参（L528–L530）**：`self.cam.get_intrinsics()` 返回 `{fx, fy, ppx, ppy}`，供 `est.process` 把归一化 2D 关键点转成 3D（深度辅助功能）。

**③ 推理（L532–L537）**：`results = self.est.process(rgb, depth, intrinsics)`。返回结果列表（`max_hands=1` 时最多 1 个）。

**④ 右手过滤（L539–L541）**：

```python
if results:
    results_right = [r for r in results if r.handedness.lower() == "right"]
    results = results_right if results_right else []
```

- **系统只响应右手**（左手结果被丢弃，画面也不会显示左手骨架）。这是产品决策：RY-H1 灵巧手默认模拟右手动作。

**⑤ 骨架绘制（L543–L548）**：勾选 `show_skeleton` 时 `est.draw_skeleton(disp, results)` 在帧上画 21 点连线。

**⑥ 角度叠加（L550–L566）**：

```python
angles_deg = None
norm_dist = None
fist_conf = None
if results:
    try:
        r = results[0]
        angles_deg = r.joint_angles_deg
        norm_dist = getattr(r, "lateral_dist", None)      # 横向距离（原代码误用 norm_dist）
        fist_conf = getattr(r, "fist_confidence", None)   # 深度辅助握拳置信度
        if self.checkbox_vars["show_angles"].get():
            y = 20
            for i in range(JOINT_NUM):
                cv2.putText(disp, f"J{i+1:2d} {angles_deg[i]:5.1f}", (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                y += 16
```

- 从结果对象取出：16 关节角（度）、横向距离、**握拳置信度**（来自深度相机的辅助信号，用于后处理异常判定时"确认握拳是真实运动"）。
- `getattr(..., None)` 容错：老版本结果对象没有该属性时返回 None 而不崩。
- 画面左上角绿色小字显示 `J1~J16` 的实时角度（L562 用 `J{i+1:2d}` 格式：索引 0 → "J 1"，方便对照滑条编号）。

**⑦ 动作模仿（L568–L572）**：

```python
if self.checkbox_vars["mimic_on"].get() and self.hand is not None and angles_deg is not None:
    try:
        self._mimic_apply(angles_deg, fist_conf)
    except Exception as e:
        logger.warning("动作模仿异常: %s", e)
```

三个条件缺一不可：模仿开关开 + 手已连接 + 本帧识别到角度。

**⑧ 信息面板（L574–L599）**：构建多行文本：
- 手部信息：`手: {handedness} 置信={confidence:.2f}` + 深度 `深度={avg_depth_mm:.0f}mm`；
- 五根手指各一行：`侧摆 MCP PIP` 三个角度（按 `start_idx = [0,3,6,9,12]` 分组取索引）；
- 拇指内外展角度 `内外展: {angles_deg[15]}`；
- 横向距离、握拳置信度（若有）；
- **稳定性统计**：`self.post.get_stats()` 返回 `jitter_std_deg`（抖动标准差）与 `drop_rate_pct`（丢弃率），帮助用户判断后处理效果。
- 未识别到手时显示 `"未识别到手"`。

**⑨ 显示（L601–L635）**：见 §11。

**⑩ 自调度（L637–L640）**：

```python
if self._running:
    self._after_id = self.root.after(30, self._poll_video)
else:
    logger.info(">>> _poll_video 不再调度")
```

> 💡 **为什么用 `after` 而不是线程 + `queue.get()` 阻塞？**
> 因为**Tk 不是线程安全的**——所有 Canvas/变量操作必须在主线程。`after` 让消费逻辑在主线程事件循环里跑，天然安全；代价是吞吐上限约 33fps（30ms 周期），对灵巧手模仿（要求平滑、低延迟）已经足够，配合后处理链的平滑效果，实际体验流畅。

---

## 11. 视频显示算法：等比缩放 + 居中裁剪（L601–L635）

这是"无黑边、无变形"的核心，数学如下：

```python
src_h, src_w = disp.shape[:2]
src_ratio = src_w / src_h                     # 原相机宽高比（如 640/480 = 4:3）

scale = max(canvas_w / src_w, canvas_h / src_h)   # ① 以"填满"为原则
new_w = max(1, int(round(src_w * scale)))
new_h = max(1, int(round(src_h * scale)))
resized = cv2.resize(disp, (new_w, new_h))        # ② 等比放大到至少盖满画布

x0 = max(0, (new_w - canvas_w) // 2)              # ③ 居中裁剪
y0 = max(0, (new_h - canvas_h) // 2)
crop = resized[y0:y0 + canvas_h, x0:x0 + canvas_w]
```

### 11.1 逐步推导

1. **求等比缩放系数**：`scale = max(cw/sw, ch/sh)`。
   - 若只按宽度缩放（`cw/sw`），高度可能不足；只按高度缩放（`ch/sh`），宽度可能不足。
   - 取**两者较大值** → 缩放后的图像**至少在一个方向上完全盖住画布**，另一方向必然超出（溢出部分被裁掉）。
   - 因为是等比缩放（`new_w/new_h = src_w/src_h`），**图像内容不会变形**。
2. **缩放**：`new_w = src_w × scale`，`new_h = src_h × scale`。由于 `scale` 保证 `new_w ≥ canvas_w` 且 `new_h ≥ canvas_h`（至少一个严格大于），所以：
   - 画布较"扁"（如 16:9 画布装 4:3 视频）→ 高度方向被裁；
   - 画布较"高" → 宽度方向被裁。
3. **居中裁剪**：`x0 = (new_w - canvas_w)//2`，`y0 = (new_h - canvas_h)//2`，从缩放图正中心裁出 `canvas_w × canvas_h` 的子图。
   - `max(0, ...)` 防御：当某方向恰好相等（`new_w == canvas_w`）时偏移为 0。

### 11.2 效果对比

| 方案 | 黑边 | 变形 | 本文件 |
|---|---|---|---|
| `scale = min(cw/sw, ch/sh)`（contain） | ✅ 有黑边 | ❌ 无 | ✗ 不用 |
| 直接 `resize` 到画布（stretch） | ❌ 无 | ✅ 有 | ✗ 不用 |
| **`scale = max(cw/sw, ch/sh)` + 居中裁剪（cover）** | ❌ **无** | ❌ **无** | ✅ **采用** |

代价是画面**四周会被裁掉一部分**（信息损失），但换来"全屏无黑边、比例不变"，这正是作者在文件头注释里强调的"视频区域固定比例，无黑边"。

### 11.3 其它细节

- `canvas_w < 2 or canvas_h < 2` 时（Canvas 尚未完成布局，尺寸为 1×1）回退到 800×600 计算（L605–L606）。
- `ImageTk.PhotoImage(Image.fromarray(resized_rgb))`：BGR→RGB 转换后用 PIL 转 Tk 图像。
- **必须保存引用**：`self.video_canvas.image = img`（L627）——Tk 的 PhotoImage 若被垃圾回收会白屏，这是 Tkinter 经典坑。
- `create_image(0, 0, anchor="nw", ...)`：从左上角放置，因为裁剪图尺寸已经等于画布尺寸。
- 底部灰色信息条（L630–L633）：`相机 640x480 (比例 1.333) | 显示 900x600 | 缩放 1.41x`，方便用户理解"裁了多少"。

---

## 12. `_apply_calib`：校准参数下发（L645–L669）

```python
def _apply_calib(self):
    if self.est is None:
        return                                  # est 未创建（相机未启动）→ 直接跳过
    self.est.update_params(
        bend_gain=..., bend_scale=..., bend_offset=...,
        deadzone_deg=..., bend_reverse=...,
        use_distance_ratio=...,
        per_finger_scale={...}, per_finger_offset={...},
        thumb_abd_offset=..., thumb_abd_gain=..., thumb_abd_reverse=...,
    )
    if hasattr(self, "post"):
        self.post.update_params(
            min_cutoff=..., beta=...,
            max_delta_deg=..., abduct_max_delta_deg=...,
        )
    self._save_calibration()
```

职责一句话：**把 GUI 当前所有参数值"灌"进底层两个模块，并自动保存**。

| 参数组 | 去向 | 说明 |
|---|---|---|
| bend_gain / bend_scale / bend_offset / deadzone / bend_reverse / use_distance_ratio / per_finger_scale / per_finger_offset / thumb_abd_* | `est.update_params` | 影响**角度计算**（MediaPipe 关键点 → 16 关节角） |
| min_cutoff / beta / max_delta / abduct_max_delta | `post.update_params` | 影响**后处理**（One Euro 平滑 + 限速） |

触发时机（三重）：
1. 每个参数滑条拖动（`_add_slider` 的 `command`）；
2. 除 mimic 外的每个复选框点击（`_build_ui` L289–L290）；
3. `_start_camera` 创建完 `est` 后的一次性全量同步（L441）。

> 💡 `_apply_calib` 末尾必调 `_save_calibration()`，所以校准是**无感自动保存**的。频繁拖动滑条会高频写 json（几十次/秒），但文件很小，现代 SSD 无压力；若担心磨损可改为"松开滑条才保存"，当前实现是简单优先。

---

## 13. 灵巧手控制（L671–L775）

### 13.1 `_connect_hand`（L674–L682）

```python
def _connect_hand(self):
    try:
        if self.hand is not None:
            self._disconnect_hand()                       # 已连接则先断开（防重复连接）
        self.hand = RYH1HandController(method=self.hand_method.get(), hand_lr=self.hand_lr.get())
        self.hand.open()                                  # 打开通信（PCAN 初始化 / 串口打开）
        self.status_var.set(f"已连接（{self.hand_method.get()}）")
    except Exception as exc:
        messagebox.showerror("连接失败", str(exc))
```

- `method` 直接取 UI 单选值（`pcan`/`canii`/`rs485`），`hand_lr` 取左右手单选值。
- `open()` 失败（如 PCAN 设备不存在、串口被占用）→ 弹错误框，`hand` 保持 None。

### 13.2 `_disconnect_hand`（L684–L691）

```python
def _disconnect_hand(self):
    if self.hand is not None:
        try:
            self.hand.close()
        except Exception:
            pass
        self.hand = None
    self.status_var.set("未连接")
```

- 关闭通信并置 None；`close()` 异常被吞掉（断开失败也不能阻止 UI 状态更新）。

### 13.3 `_on_hand_lr`（L693–L695）

```python
def _on_hand_lr(self):
    if self.hand is not None:
        self.hand.set_hand_lr(self.hand_lr.get())
```

- 左右手单选按钮的 `command`：**已连接时热切换左右手**，无需断开重连。

### 13.4 `_check_hand`（L697–L709）—— 自检

```python
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
```

- 返回字典含：`version`（库版本）、`replies`（应答电机数/16）、`faults`（故障电机列表 `(电机ID, 状态码, 文本)`）、`need_homing`（是否有电机处于"找零"告警状态）。
- 弹窗汇总所有信息，`need_homing=True` 时提示用户点【回零】。

### 13.5 `_homing`（L711–L718）—— 回零

```python
def _homing(self):
    if self.hand is None:
        return
    if not messagebox.askyesno("回零", "对全部电机执行回零？"):
        return
    self.hand.homing(timeout_ms=1500, sleep_s=0.3)
    time.sleep(1)
    messagebox.showinfo("回零", "回零完成")
```

- 先 `askyesno` 二次确认（回零会让机械臂动作，需防误触）。
- `homing(timeout_ms=1500, sleep_s=0.3)`：逐电机回零，每电机等待最多 1.5s、间隔 0.3s。
- 完成后 `time.sleep(1)`（让机械动作稳定）再弹窗确认。

### 13.6 `_slider_changed`（L720–L729）—— 手动滑条下发

```python
def _slider_changed(self, idx: int):
    if self.hand is None:
        return
    angles = [0.0] * JOINT_NUM
    for i, var in enumerate(self.angle_vars):
        angles[i] = math.radians(var.get())       # 度 → 弧度
    try:
        self.hand.move_joints(angles)
    except Exception as exc:
        logger.error("move_joints: %s", exc)
```

- 任何一根滑条变化 → 读**全部 16 根**滑条 → 转弧度 → `move_joints` 整体下发（保证关节间同步，不是只动被拖的那根）。
- `idx` 参数当前未被使用（仅为闭包签名保留，未来可做单关节增量下发优化）。
- `math.radians` 是度→弧度转换：底层控制器按弧度接口（`hand_controller.py` 内再转 PWM 位置）。

### 13.7 预设手型（L731–L751）

| 方法 | 逻辑 | 底层调用 |
|---|---|---|
| `_preset_open`（张开） | `_set_all(0.0)` 滑条全归零 | `hand.open_hand()` |
| `_preset_close`（握拳） | `_set_all_list([0,50,30, 0,70,60, 0,70,60, 0,70,60, 0,70,60, 0])` 设置各指弯曲 | `hand.close_hand()` |
| `_preset_relax`（放松） | `_set_all_list([0,30,15, 0,35,25, 0,35,25, 0,35,25, 0,35,25, 0])` 半握状态 | `hand.relax()` |
| `_preset_zero`（归零） | `_set_all(0.0)` | `hand.open_hand()` |

- 预设数组按关节索引排布：`[侧摆, MCP, PIP] × 5 指 + [内外展]`。如握拳：拇指 `[0,50,30]`，其余四指 `[0,70,60]`（MCP 70°、PIP 60° 的强弯曲），内外展 0。
- `_set_all*` 只改 UI 滑条变量；实际下发靠底层 `open_hand()`/`close_hand()`/`relax()` 的库调用（它们内部按配置好的手型直接驱动电机）。
- 注意：**预设按钮修改滑条变量后，滑条 `command` 不会被触发**（Tk 编程式 set 不触发 command），所以不会重复下发；动作完全由底层库方法完成。

### 13.8 `_set_all` / `_set_all_list`（L753–L760）

```python
def _set_all(self, val: float):
    for var in self.angle_vars:
        var.set(val)

def _set_all_list(self, vals: list):
    for i, var in enumerate(self.angle_vars):
        if i < len(vals):
            var.set(vals[i])
```

- `_set_all`：16 个滑条统一设一个值（张开/归零用）。
- `_set_all_list`：按列表逐位设置（越界忽略），供握拳/放松预设使用。

### 13.9 `_test_motor`（L762–L775）—— 单电机测试

```python
def _test_motor(self):
    if self.hand is None:
        messagebox.showwarning("提示", "请先连接手")
        return
    mid = self.motor_id.get()
    pos = self.motor_pos.get()
    self.hand.move_motor(mid, pos)                       # 指定电机转到指定位置(0~4095)
    info = self.hand.get_servo_info(mid, timeout_ms=200) # 回读伺服状态
    msg = f"电机{mid} 位置={pos}"
    if info:
        msg += f"\n回读 P={info.position} 状态={info.status}[{status_text(info.status)}]"
    else:
        msg += "\n无应答"
    messagebox.showinfo("单电机测试", msg)
```

- 用于**逐电机排查**：设置 ID（1~16）和位置（0~4095，PWM 码值），下发后回读该电机位置与状态码（`status_text` 翻译成中文）。
- 位置 2048 是中位（约 90°），0/4095 是两端。
- 回读超时 200ms，无应答显示"无应答"（电机可能掉线/线序问题）。

---

## 14. 动作模仿：`_toggle_mimic` / `_mimic_apply`（L777–L809）

### 14.1 `_toggle_mimic`（L777–L781）

```python
def _toggle_mimic(self):
    self._smoother_state = [0.0] * JOINT_NUM       # 清空平滑状态
    if hasattr(self, "post"):
        self.post.reset()                          # 重置后处理链内部状态（历史/滤波/统计）
    self.state_var.set("动作模仿已开启" if self.checkbox_vars["mimic_on"].get() else "动作模仿已关闭")
```

- 勾选/取消"动作模仿"时执行：**清空所有滤波历史**，避免开关切换瞬间带着旧状态输出跳变角度。
- `post.reset()` 重置：中值历史、上一帧值、One Euro 滤波器、抖动统计（见 postprocess L104–L114）。
- 状态栏同步显示开关结果。

### 14.2 `_mimic_apply`（L783–L809）—— 模仿链路核心

```python
def _mimic_apply(self, angles_deg: List[float], fist_confidence: float | None = None):
    """精度后处理链：均值 → deadzone → 异常检测(方向一致性+深度)/中值/One Euro/分通道限速 → 下发。"""
    deadzone_deg = self.param_vars["deadzone"].get()
    # ① 多帧均值（去单帧毛刺，配合 post 内部中值）
    self.angle_history.append(angles_deg.copy())
    if len(self.angle_history) >= 3:
        avg_deg = [0.0] * JOINT_NUM
        for i in range(JOINT_NUM):
            vals = [frame[i] for frame in self.angle_history]
            avg_deg[i] = sum(vals) / len(vals)
    else:
        avg_deg = angles_deg

    # ② deadzone（静态小角度归零，防微颤）
    for i in range(JOINT_NUM):
        if abs(avg_deg[i]) < deadzone_deg:
            avg_deg[i] = 0.0

    # ③ 核心：方向一致性+深度辅助异常检测 → 中值 → One Euro → 分通道限速
    out_deg = self.post.update(avg_deg, fist_confidence=fist_confidence)

    # ④ 度 → 弧度
    angles_rad = [math.radians(v) for v in out_deg]
    try:
        self.hand.move_joints(angles_rad)           # ⑤ 下发
    except Exception as exc:
        logger.error("mimic_apply 异常: %s", exc)
```

**数据流五段式**：

| 阶段 | 代码 | 作用 | 数据形态 |
|---|---|---|---|
| ① 多帧均值 | `angle_history`（deque maxlen=5，≥3 帧才均值） | 平滑单帧抖动（MediaPipe 偶尔单帧跳变）；**取均值时 `angles_deg.copy()` 防止共享引用被后续修改** | 16×float（度） |
| ② 静态死区 | `|avg|<deadzone → 0` | 消除"手其实没动但识别出小角度"的微颤 | 16×float（度） |
| ③ 后处理链 | `post.update(avg_deg, fist_confidence)` | 方向一致性异常检测（孤立突变用中值替代）→ 5 帧中值 → One Euro → 弯曲/外展分通道限速 | 16×float（度） |
| ④ 单位转换 | `math.radians` | 度 → 弧度（底层控制器接口要求） | 16×float（弧度） |
| ⑤ 下发 | `hand.move_joints(angles_rad)` | 一次性下发 16 关节，控制器内部换算 PWM 位置 | CAN/串口帧 |

**`fist_confidence` 的作用（重要）**：

- 它来自深度相机的辅助信号（`r.fist_confidence`，L558）。
- 传递给 `post.update(..., fist_confidence=...)` 后，后处理在异常判定时**会用深度信息区分"真实握拳"与"误识别跳变"**：
  - 正常握拳时，5 指角度同时大幅变化 → `jump_max` 大且 `jump_med` 也大，比值小 → 不被判为异常；
  - 单指孤立突跳（如手指快速划过镜头被误识别）→ `jump_max` 远大于 `jump_med` → 判异常，该通道用中值替代；
  - 当 `fist_confidence >= 0.6`（深度确认确实在握拳）时，**跳过异常判定**，绝不因为角度变化大而卡住动作（见 postprocess.py L139–L146 注释）。
- 一句话：**深度置信度是异常检测的"安全阀"**，防止真实快速动作被误杀。

> ⚠️ 注意死区用了**静态**判断（仅当前帧），`post` 内部的 One Euro 才是动态滤波；两者叠加后，手慢速移动时输出平滑、手停住时输出归零，这是"不抖"体验的关键。

---

## 15. `_on_close`：关闭清理与强制退出（L811–L831）

```python
def _on_close(self):
    logger.info(">>> 窗口关闭开始")
    self._running = False                          # ① 停运行标志
    if hasattr(self, '_after_id') and self._after_id is not None:
        try:
            self.root.after_cancel(self._after_id) # ② 取消 after 链
            self._after_id = None
        except Exception:
            pass
    self._stop_camera()                            # ③ 停相机（内部已处理线程/队列/释放）
    self._disconnect_hand()                        # ④ 断手（关 CAN/串口）
    try:
        self.root.quit()
    except Exception:
        pass
    try:
        self.root.destroy()
    except Exception:
        pass
    logger.info(">>> 强制终止进程")
    os._exit(0)                                    # ⑤ 兜底强杀
```

- 顺序清理：停标志 → 取消回调 → 停相机 → 断手 → 正常退出 Tk → **`os._exit(0)` 兜底**。
- **为什么最后还要 `os._exit(0)`？** 因为某些后台线程（daemon 采集线程、释放资源的 `_stop_thread`、以及可能的第三方驱动线程）可能在 `root.destroy()` 后仍存活；Tk 销毁后残留线程访问已销毁的 Tcl 解释器会抛异常或挂死。`os._exit(0)` 不做任何清理直接终止进程，保证**窗口一定能关掉**。代价是跳过 Python 的 `atexit` 等清理，但所有资源（相机/手）已在上一步显式释放，这是可接受的取舍。

---

## 16. `main()` 入口（L834–L841）

```python
def main():
    root = tk.Tk()
    MainGui(root)
    root.mainloop()

if __name__ == "__main__":
    main()
```

- 创建 `Tk` 根窗口 → 实例化 `MainGui`（构造里完成 UI 构建与校准加载）→ 进入 `mainloop()` 事件循环。
- `mainloop` 返回后进程退出（`_on_close` 已保证在此之前被调用）。
- 入口命令：`python -m gui.main_gui`（在 `rycan_hand_windows` 目录下），`-m` 方式让 `gui` 成为包、模块内相对路径与 `sys.path` 引导都能正确工作。

---

## 17. 操作流程：从零开始连接

### 场景 A：完整视觉动作模仿（推荐路径）

```
① 硬件准备
   相机（USB 或 L515 接入）→ 灵巧手控制器（PCAN/CANII/RS485 接入并上电）
② 启动程序
   cd ryan_hand_windows  （实际为 r y c a n_hand_windows）
   python -m gui.main_gui
   （窗口出现后确认：标题"睿研 RY-H1(16) 灵巧手 · 视觉控制台"，底部无报错）
③ 启动相机
   顶部：相机类型选 USB 或 L515 → 索引保持 0（多相机时调整）→ 点【启动】
   确认：视频区出现画面，"相机已启动"绿色文字；若黑屏 → 看"常见问题 §19.2"
④ 连接手
   顶部：手通信选 PCAN / CANII / RS485（与硬件一致）→ 左右手按实际安装选 → 点【连接】
   确认：顶部蓝色文字变为"已连接（pcan）"
⑤ 自检（可选但建议）
   点【自检】→ 弹窗显示"xx/16 应答"与故障列表
   - 若提示"⚠️ 有找零告警电机，点击【回零】" → 继续第 ⑥ 步
   - 若应答数 < 16 → 检查总线接线 / 电机供电 / ID 配置
⑥ 回零
   点【回零】→ 确认弹窗 → 等待全部电机回零（听到/看到机械回位）
⑦ 开启动作模仿
   右侧参数面板 → 控制开关 → 勾选【动作模仿】
   确认：视频区状态变为"动作模仿已开启"
⑧ 验证
   在相机前伸出右手 → 画面出现骨架 + 左上角 J1~J16 角度 → 灵巧手跟随手部动作
   - 若跟随过快/抖动：调低 min_cutoff、调高 smooth 相关项、加大 deadzone
   - 若跟不上：调高 beta（跟手度）
   - 若反向：勾选 弯曲反转 / 内外展反转
⑨ 结束
   直接关窗口（自动停相机/断手）或依次点【停止】【断开】再关
```

### 场景 B：手动控制测试（不依赖视觉）

```
启动 → 连接手 → 回零 →
底部滑条区拖动任一滑条（如 "4:食指侧摆"）→ 食指轴转动 →
点【张开】/【握拳】/【放松】/【归零】验证预设手型 →
点【单电机测试】输入 ID=9 位置=2048 → 点【测试】→ 弹窗回读电机 9 状态
```

### 场景 C：参数校准（让动作更准）

```
连接相机 + 手 → 勾选模仿 →
① 手势对照：手张开，看 info 面板各指角度是否接近 0
   不接近 → 调 bend_offset（固定偏置补偿）或勾选 bend_reverse（方向反了）
② 幅度对照：手全握，看角度是否够大
   不够 → 调高 bend_gain / bend_scale；过大 → 调低
③ 抖动治理：手保持不动，看稳定性 std
   std 大 → 加大 deadzone、调低 min_cutoff
④ 拇指专项：手并拢，调 thumb_abd_offset（死区）；手张开，调 thumb_abd_gain（幅度）
⑤ 保存：所有调节自动写入 config/calibration.json，下次启动自动恢复
```

---

## 18. 布局设计决策

### 18.1 为什么视频区 58% / 参数区 42%？

- 视频需要足够大才能看清骨架与关节角叠加；参数区需要容纳 11 个全局滑条 + 6 个复选框 + 5 指增益 + 5 指偏移 + 实时信息，内容很多。
- 58/42 的权重（`grid_columnconfigure(0, weight=58)` / `(1, weight=42)`，L230–L231）是在"视频够大"与"参数放得下"之间取的平衡点；窗口默认 1600×900 时，视频区约 900px 宽、参数区约 650px 宽。
- 权重制（而非固定像素）保证**窗口任意缩放时两区按比例伸缩**，不会挤爆。

### 18.2 为什么参数面板不用滚动条？

- 参数面板设计成**接近方形**（两列 × 三个分组），所有内容**一次性全部显示**（注释 L252、L258 明确写了"全部显示，无需滚动"）。
- 理由：
  1. **可见性**：所有参数同时可见，用户调节时不需要"滚上去看效果、滚下来调参数"；
  2. **实时性**：每个滑条拖动即生效（`_apply_calib`），全部可见才能边看视频边调；
  3. **实现简单**：Tk 滚动区域（Canvas + Scrollbar + 绑定事件）是经典复杂点（鼠标滚轮在 Windows 上需额外绑定），方形布局直接规避。
- 代价：窗口高度不足时（如 900 高度下）参数区被压扁——用紧凑控件（字号 8、滑条 110px、`pady=0`）缓解。

### 18.3 为什么滑条 8 列 × 2 行？

- 窗口默认 1600×900 **宽 > 高**，横向空间充足、纵向紧张。
- 16 个关节若排成 2 列 × 8 行会很高（超出可用高度）；8 列 × 2 行把滑条区变成**横向长条**（"长方形布局"——这正是 L320 注释和 LabelFrame 标题的意思），与窗口形状匹配。
- 每格内部还是"标签在上、滑条在下"的纵向堆叠，因此每个 grid 单元占 2 行（`row = (i//8)*2`）。
- 8 列均分宽度（L344–L345 `weight=1`），滑条横向撑满、整齐对齐。

### 18.4 为什么视频用"居中裁剪"而不是"等比缩放完整显示"？

- 两种候选方案：
  - **contain（`scale = min(cw/sw, ch/sh)`）**：完整显示画面，但上下/左右留黑边——与文件头"无黑边"的要求冲突；
  - **cover（`scale = max(...)` + 居中裁剪）**：画面填满画布、比例不变、无黑边——但四周被裁掉一部分。
- 本项目选 **cover**，理由：
  1. **视觉干净**：黑边会让人误以为相机/程序有问题；
  2. **比例保真**：手部形状不变形，关节角计算**不依赖显示画面**（推理在原始帧上做，`disp` 只是展示副本），所以裁剪不影响识别精度；
  3. **信息损失可控**：手通常位于画面中心区域，居中裁剪恰好保住最重要的部分；相机分辨率（640×480 / 1280×720）也高于画布显示尺寸，裁剪不损失有效信息。
- 一句话：**推理用原图、显示用 cover 裁剪图**，两全其美。

---

## 19. 常见问题（FAQ）

### 19.1 启动报错 `ModuleNotFoundError`（路径引导失败）

```
现象：python -m gui.main_gui 报 "No module named 'lib' / 'vision' / 'hand'"
```

- **原因**：不在项目根目录执行，且 `sys.path` 引导没生效（例如 `__file__` 路径含特殊字符，或目录结构被移动）。
- **排查**：
  1. 确认在 `rycan_hand_windows` 目录下执行（`cd ryan_hand_windows && python -m gui.main_gui`，实际目录名 `rycan_hand_windows`）；
  2. 确认目录结构完整：`rycan_hand_windows/{gui, lib, vision, hand, camera, config}` 都在；
  3. 手工验证：`python -c "import sys; sys.path.insert(0,'.'); import lib.camera_lib1; print('ok')"`；
  4. 检查 L21 的 `os.path.dirname` 层数是否正确（`gui/main_gui.py` 需要向上两级）。
- **避免**：不要用双击 .py 的方式运行（工作目录变成桌面/资源管理器路径）；务必用 `-m` 模块方式。

### 19.2 点【启动】相机报"相机启动失败"

- **USB 相机**：设备被其它软件占用（摄像头 App、微信、OBS）→ 关闭占用程序；索引不对（`cam_idx` 不是 0）→ 逐个试 0~9；驱动问题 → 换 UVC 驱动或换接口。
- **L515**：`realsense` 模式需要 Intel RealSense SDK 且设备已插好；SDK 未安装 → 装 `pyrealsense2` 及 SDK；USB 3.0 供电不足 → 换口/加供电。
- 注意 `_start_camera` 失败会弹 `messagebox.showerror` 但**界面不崩**，可改参数重试。

### 19.3 点【连接】手报"连接失败"

- **PCAN**：PCAN-USB 设备未插入、驱动未装、被其它进程占用（如 PCAN-View）。
- **CANII / RS485**：串口号不对（代码可能按默认端口枚举）、波特率/接线错误、控制器未上电。
- 检查顺序：控制器电源 → 总线接线（CANH/CANL 或 A/B）→ 终端电阻（CAN 总线两端 120Ω）→ 上位机软件占用。
- 连接成功后顶部蓝色文字应为"已连接（xxx）"。

### 19.4 自检显示"找零告警"或应答数不足

- `need_homing=True`：电机上电后未找到零点 → 点【回零】执行 `homing()`。
- `replies < 16`：部分电机没应答 → 检查对应电机供电、ID 配置（1~16）、总线拓扑（菊花链中断）。
- 有 `faults` 列表时逐条看 `status_text` 中文含义（过流/过温/堵转等），处理后再自检。

### 19.5 勾选动作模仿后手不跟随（或只显示角度不动）

按 `_poll_video` 模仿分支的三个条件（L568）逐项排查：

```
if mimic_on 勾选 且 hand 已连接 且 angles_deg 不是 None:
```

1. **没识别到手**：info 面板显示"未识别到手"→ 调整手的位置/光照/距离，让骨架稳定出现；
2. **识别到但手不动**：确认右手是否在画面中（系统**只响应右手**，L539–L541 过滤了左手！）→ 换右手或勾选角度反转类参数；
3. **手已连接但 mimic 没触发**：确认顶部状态是"已连接"（不是"未连接"）；
4. **动一下又立刻回弹/抖动**：后处理在起作用——检查稳定性 std、适当加大 deadzone、调低 min_cutoff；
5. **动作方向相反**：勾选 `弯曲反转` / `内外展反转`。

### 19.6 画面抖动/跟不上

| 症状 | 调节 | 原理 |
|---|---|---|
| 抖动、微颤 | 增大 `deadzone`；调低 `min_cutoff`（更平滑） | 死区吃掉小角度；One Euro 截止频率越低越平滑 |
| 动作滞后、跟不上快速动作 | 调高 `beta`（跟手度）；调低 min_cutoff 不要过低 | beta 越大速度自适应越快 |
| 突然跳变/抽搐 | 调低 `max_delta`（限速）与 `abduct_max_delta` | 每帧角度变化上限收紧 |
| 单指偶发乱动 | 保持 `max_jump_deg=40`、`jump_ratio=3`（异常检测兜底） | 孤立突变用中值替代 |

### 19.7 关窗口卡住 / 无法退出

- 正常流程：`_on_close` → 停相机 → 断手 → `os._exit(0)`。若卡住：
  1. 检查是否卡在 `_stop_camera` 的 `join(timeout=0.5)`（采集线程 `cam.read()` 阻塞）——0.5s 超时后强制继续；
  2. `os._exit(0)` 兜底后进程必然终止；若任务管理器仍见进程，多半是驱动 DLL 的线程未释放（daemon 线程特性），手动结束即可；
  3. 避免在模仿开启时直接拔相机（驱动可能挂起），先点【停止】。

### 19.8 calibration.json 被改坏 / 想恢复默认

- 删除 `rycan_hand_windows/config/calibration.json` 后重启程序 → `_load_calibration` 发现文件不存在直接跳过，全部参数回到 `PARAM_CONFIG`/`CHECKBOX_CONFIG` 的默认值。
- 文件是 `ensure_ascii=False` 明文 JSON，也可手工编辑后重启生效（注意范围：bend_gain 应在 0.5~2.5 等）。

---

## 20. 参数速查表

### 全局校准（左列）→ `est.update_params` / `post.update_params`

| 滑条 | 范围 | 默认 | 单位 | 目标模块 | 一句话 |
|---|---|---|---|---|---|
| 弯曲增益 bend_gain | 0.5~2.5 | 1.0 | 倍 | est | 弯曲幅度放大/缩小 |
| 缩放 bend_scale | 0.5~1.5 | 1.0 | 倍 | est | 整体弯曲比例 |
| 偏置 bend_offset | -30~30 | 0 | 度 | est | 固定角度补偿 |
| 死区 deadzone | 0~10 | 1.0 | 度 | est + mimic | 小角度归零 |
| 平滑系数 smooth | 0.1~0.9 | 0.35 | — | （无实际下发） | 历史遗留占位 |
| 平滑强度(1€) min_cutoff | 0.1~2.0 | 0.5 | Hz | post | 越小越平滑 |
| 跟手度(1€) beta | 0~0.2 | 0.02 | — | post | 越大越跟手 |
| 限速°/帧 max_delta | 1~20 | 8.0 | 度/帧 | post | 弯曲通道防突跳 |

### 拇指内外展校准（左列）→ `est`

| 滑条 | 范围 | 默认 | 单位 | 一句话 |
|---|---|---|---|---|
| 内外展死区 thumb_abd_offset | 0~0.5 | 0.0 | 掌宽倍数 | 切除并拢无效区间 |
| 内外展增益 thumb_abd_gain | 0.3~2.0 | 0.8 | 倍 | 放大横向距离 |
| 内外展限速°/帧 abduct_max_delta | 0.5~8.0 | 2.0 | 度/帧 | 外展轴防抖 |

### 控制开关（左列）→ 混合

| 复选框 | 默认 | 目标 |
|---|---|---|
| 弯曲反转 | ✗ | est（bend_reverse） |
| 内外展反转 | ✗ | est（thumb_abd_reverse） |
| 距离比法 | ✗ | est（use_distance_ratio） |
| 显示骨架 | ✓ | 仅 UI |
| 显示关节角 | ✓ | 仅 UI |
| 动作模仿 | ✗ | 触发 _toggle_mimic → _poll_video 模仿分支 |

### 每指增益 / 每指偏移（右列）→ `est`

| 组 | 范围 | 默认 | 键（finger_vars / finger_offset_vars） |
|---|---|---|---|
| 每指增益 | 0.5~2.0 | 1.0 | thumb / index / middle / ring / pinky |
| 每指偏移 | -30~30 | 0 | thumb / index / middle / ring / pinky |

### 16 关节滑条（底部）→ `hand.move_joints`

| 索引 | 关节 | 范围(度) | 说明 |
|---|---|---|---|
| 0 | 拇指侧摆 | ±20 | swing |
| 1 | 拇指MCP | 0~90 | prox |
| 2 | 拇指PIP | 0~75 | dist |
| 3,6,9,12 | 食/中/无名/小指侧摆 | ±20 | swing |
| 4,7,10,13 | 食/中/无名/小指MCP | 0~90 | prox |
| 5,8,11,14 | 食/中/无名/小指PIP | 0~75 | dist |
| 15 | 拇指内外展 | 0~110 | joint16 |

### 后处理链初始硬编码（`__init__` 创建 post 时）

| 参数 | 初始值 | GUI 覆盖项 |
|---|---|---|
| median_n | 5 | 不可调 |
| min_cutoff / beta | 0.5 / 0.02 | min_cutoff / beta 滑条 |
| max_delta_deg | 8.0 | max_delta 滑条 |
| abduct_max_delta_deg | 3.0 | abduct_max_delta 滑条（默认 2.0，拖动后生效） |
| max_jump_deg / jump_ratio_threshold | 40.0 / 3.0 | 不可调（异常检测兜底） |

---

## 附：文件行号索引（便于对照源码）

| 功能 | 行号 |
|---|---|
| 路径引导 / 导入 / 日志 | L20–L40 |
| PARAM_CONFIG | L45–L112 |
| CHECKBOX_CONFIG | L114–L121 |
| slider_range_for_joint | L124–L134 |
| `__init__` | L138–L177 |
| `_build_ui`（顶/中/底布局） | L179–L360 |
| `_add_slider` / `_add_param_group` | L362–L378 |
| `_load_calibration` / `_save_calibration` | L383–L419 |
| `_start_camera` / `_stop_camera` | L424–L492 |
| `_capture_loop` | L494–L512 |
| `_poll_video` | L514–L640 |
| 视频显示（cover 算法） | L601–L635 |
| `_apply_calib` | L645–L669 |
| `_connect_hand` / `_disconnect_hand` / `_on_hand_lr` | L674–L695 |
| `_check_hand` / `_homing` | L697–L718 |
| `_slider_changed` | L720–L729 |
| 预设手型 / `_set_all` / `_set_all_list` | L731–L760 |
| `_test_motor` | L762–L775 |
| `_toggle_mimic` / `_mimic_apply` | L777–L809 |
| `_on_close` | L811–L831 |
| `main()` | L834–L841 |
