# 16 · `gui/main_gui_holistic.py` 代码详解

> 本文档对应源文件：`RY-H1_vision_mimic/gui/main_gui_holistic.py`（共 303 行）
> 入口方式：`python -m gui.main_gui_holistic`（在 `RY-H1_vision_mimic` 目录下执行）
>
> 本文件是「睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂 + Intel RealSense L515 + MediaPipe Holistic **协同控制**系统（Windows 版）」的**协同总 GUI**：它在**不修改**原 `gui/main_gui.py`（灵巧手版）的前提下，通过三级继承 `MainGui → MainGuiArm → MainGuiHolistic`，把"灵巧手控制"、"机械臂控制"、"人体姿态协同"三层能力叠进同一个窗口，最终实现 **人动臂动、手动手动的实时协同**。

---

## 目录

1. [文件职责总览](#1-文件职责总览)
2. [ASCII 架构图（一）：MainGuiHolistic 界面层次（3 层）](#2-ascii-架构图一mainguiholistic-界面层次3层)
3. [ASCII 架构图（二）：协同数据流（相机 → Holistic → 臂 / 手）](#3-ascii-架构图二协同数据流相机--holistic--臂--手)
4. [模块头部：docstring、导入与路径引导（L1–L52）](#4-模块头部docstring导入与路径引导l1l52)
5. [类 `MainGuiHolistic` 总览与 `__init__`（L55–L66）](#5-类-mainguiholistic-总览与-initl55l66)
6. [`_build_holistic_ui`：协同面板完整布局（L71–L126）](#6-_build_holistic_ui协同面板完整布局l71l126)
7. [`_holistic_toggle`：启用/停止检测（L131–L147）](#7-_holistic_toggle启用停止检测l131l147)
8. [`_holistic_stop`：释放检测器（L149–L157）](#8-_holistic_stop释放检测器l149l157)
9. [`_holistic_apply_flags`：开关/手型同步（L159–L164）](#9-_holistic_apply_flags开关手型同步l159l164)
10. [`_holistic_apply_calib`：标定参数校验与应用（L166–L175）](#10-_holistic_apply_calib标定参数校验与应用l166l175)
11. [`_holistic_step`：每帧协同核心（L180–L228）](#11-_holistic_step每帧协同核心l180l228)
12. [深挖一：灵巧手跟随为何独立于 mimic 开关 + 防双重下发](#12-深挖一灵巧手跟随为何独立于-mimic-开关--防双重下发)
13. [深挖二：机械臂跟随为什么用 `block=False` 非阻塞](#13-深挖二机械臂跟随为什么用-blockfalse-非阻塞)
14. [`_holistic_poll_loop`：常驻调度心跳（L230–L237）](#14-_holistic_poll_loop常驻调度心跳l230l237)
15. [`_poll_video` 覆写：super 之后追加协同处理（L242–L262）](#15-_poll_video-覆写super-之后追加协同处理l242l262)
16. [`_draw_holistic_to_canvas`：骨架帧 cover 缩放显示（L264–L286）](#16-_draw_holistic_to_canvas骨架帧-cover-缩放显示l264l286)
17. [`_on_close`：先停协同再走父类收尾（L291–L293）](#17-_on_close先停协同再走父类收尾l291l293)
18. [`main` 与程序入口（L296–L303）](#18-main-与程序入口l296l303)
19. [与 `main_gui_arm.py` 的差异对比表](#19-与-main_gui_armpy-的差异对比表)
20. [安全设计](#20-安全设计)
21. [常见问题（FAQ）](#21-常见问题faq)
22. [方法速查表](#22-方法速查表)

---

## 1. 文件职责总览

`main_gui_holistic.py` 的架构核心是一个词：**继承叠加，协同编排**。

| 层 | 内容 | 来源 |
|---|---|---|
| **复用层 ①** | 相机(USB/L515)、MediaPipe 手部姿态、精度后处理、灵巧手连接/校准/动作模仿/16 关节滑条、原界面 row 0~3 | `MainGui`（`gui/main_gui.py`），`super().__init__()` 全盘继承 |
| **复用层 ②** | 机械臂连接/上电/关节滑条/位姿 movel/TCP 联动/臂手联动、row 4 面板 | `MainGuiArm`（`gui/main_gui_arm.py`） |
| **新增层 ③** | 底部第 5 行"协同控制（MediaPipe Holistic）"面板：启用开关、机械臂跟随(腕→TCP)、灵巧手跟随(手→16角)、左右手选择、标定 offset/scale/add、状态显示 | 本文件 `_build_holistic_ui()` |
| **新增编排** | 每帧在 `_poll_video` 尾部追加：Holistic 检测 → 状态显示 → 臂跟随 → 手跟随 → 骨架绘制 | 本文件覆写 `_poll_video()` + `_holistic_step()` |
| **新增心跳** | 200ms 常驻 `after` 调度，保证 after 链不中断 | 本文件 `_holistic_poll_loop()` |
| **新增收尾** | 关窗前先 `_holistic_stop()`，再走父类关闭流程 | 本文件覆写 `_on_close()` |

协同数据流一句话概括：

```
L515 相机帧 ──► frame_q ──► _poll_video ──► HolisticPoseEstimator.process()
                                                ├─ 腕部 3D ──► ArmFollower 映射 ──► 机械臂 movel(block=False)
                                                └─ 手部 21 点 ──► 16 关节角 ──► 灵巧手 move_joints(rad)
```

本文件**不实现任何视觉算法与硬件通信**：
- 检测/角度解算在 `vision/holistic_pose.py`（`HolisticPoseEstimator`，内部组合复用 `vision/hand_pose.py` 的角度解算链）；
- 腕部→机械臂 TCP 映射在 `arm/arm_follow.py`（`ArmFollower`，纯计算、可独立标定验证）；
- 机械臂运动在 `arm/arm_controller.py`（`AuboK5ArmController`），灵巧手运动在 `hand/hand_controller.py`。

本文件只负责：**把三层 UI 拼起来、把开关翻译成每帧调用、把结果翻译成人话显示、并守住安全边界**。

---

## 2. ASCII 架构图（一）：MainGuiHolistic 界面层次（3 层）

整个窗口是**三层面板纵向堆叠**：第 1 层灵巧手（row 0~3，父类），第 2 层机械臂（row 4，父类），第 3 层协同（row 5，本文件）。三层各自独立、互不覆盖：

```
┌──────────────────────────────── 主窗口 (tk.Tk root, 1600x900) ────────────────────────────────────┐
│                                                                                                    │
│ ╔══════════════ 第 1 层：灵巧手控制（row 0~3，来自 MainGui，本文件一行不改）══════════════════════╗ │
│ ║ row 0 │ 顶部控制栏：相机(USB/L515)+启动/停止、手通信(PCAN/CANII/RS485)、左右手、连接/断开/    ║ │
│ ║       │ 校准/回零/预设手型/动作模仿开关(checkbox_vars["mimic_on"])/显示骨架/显示关节角          ║ │
│ ║ row 1 │ 中部：视频显示区(video_canvas，显示相机帧+手部骨架) + 后处理参数区                      ║ │
│ ║ row 2 │ 16 关节滑条区（J1~J16，灵巧手 16 关节角度）                                             ║ │
│ ║ row 3 │ 原状态栏 / 其余控件                                                                     ║ │
│ ╚══════════════════════════════════════════════════════════════════════════════════════════════╝ │
│ ╔══════════════ 第 2 层：机械臂控制（row 4，来自 MainGuiArm）═══════════════════════════════════╗ │
│ ║ r1 │ [IP][端口][连接][断开]  速度比例: [───●────]  (机械臂状态)                                   ║ │
│ ║ r2 │ [上电+启动][断电][停止][拖拽示教(开)][拖拽示教(关)][回初始位]                                ║ │
│ ║ r3 │ [J1~J6 关节滑条] [执行 movej]  (关节角/TCP 状态)                                            ║ │
│ ║ r4 │ movel位姿 [x][y][z][rx][ry][rz] [执行 movel] ☑TCP联动 [臂手联动:握拳/张开/放松]             ║ │
│ ╚══════════════════════════════════════════════════════════════════════════════════════════════╝ │
│ ╔══════════════ 第 3 层：协同控制（row 5，本文件 _build_holistic_ui）════════════════════════════╗ │
│ ║ r1 │ ☐启用Holistic检测  ☐机械臂跟随(腕→TCP)  ☐灵巧手跟随(手→16角)  手:(•)右 ( )左  (状态文字)   ║ │
│ ║ r2 │ 映射标定 offset(x,y,z):[0][0][0]  scale:[1][1][1]  add:[.35][0][.10]  [应用标定]             ║ │
│ ║ r3 │ (状态: 人体✓ | 手✓ | 腕3D=(..) | 臂TCP=(..) | 握拳=0.87 | 检测异常:...)                      ║ │
│ ╚══════════════════════════════════════════════════════════════════════════════════════════════╝ │
│                                                                                                    │
│  说明：row 0~4 全部由 super().__init__() 构建（继承自 MainGuiArm → MainGui，代码零改动）；            │
│        row 5 由本文件追加，root.grid_rowconfigure(5, weight=0) 固定高度不拉伸；                       │
│        三层 GUI 与三级继承一一对应：MainGui(灵巧手) → MainGuiArm(+机械臂) → MainGuiHolistic(+协同)。 │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**协同面板内部三行（r1/r2/r3）的职责划分**：

| 子行 | 内容 | 作用 |
|---|---|---|
| **r1** | 启用检测、机械臂跟随、灵巧手跟随 3 个开关 + 左右手单选 + 紫色状态文字 | **使能与模式选择**——协同的"总闸"和"两路跟随的分闸" |
| **r2** | offset(x,y,z) / scale(x,y,z) / add(x,y,z) 共 9 个输入框 + `应用标定`按钮 | **臂跟随的映射参数标定**（写给 `ArmFollower`） |
| **r3** | Consolas 等宽字体状态行 | **每帧实时反馈**：人体/手是否检出、腕部 3D、臂 TCP 目标、握拳置信度、异常信息 |

---

## 3. ASCII 架构图（二）：协同数据流（相机 → Holistic → 臂 / 手）

```
                        ┌──────────────────────────────────────────────────────────────────┐
                        │                     L515 / USB 相机 (CameraModule)               │
                        │            采集线程 _capture_loop 持续 read() 出 (rgb, depth)      │
                        └───────────────────────────────┬──────────────────────────────────┘
                                                        │ frame_q.put((rgb, depth))   （队列 maxsize=2，满则丢旧帧）
                                                        ▼
                        ┌──────────────────────────────────────────────────────────────────┐
                        │  Tk 主线程 _poll_video()（每 ~30ms 一轮，本文件覆写）            │
                        │                                                                │
                        │  ① super()._poll_video()   ← 父类原逻辑：取帧→手部姿态(hand_pose) │
                        │     ├─ 显示原画面(手部骨架) ──► video_canvas                    │
                        │     └─ mimic_on 勾选时：手部角度 → 灵巧手（父类 mimic 路）        │
                        │                                                                │
                        │  ② if holistic_running and cam：                               │
                        │     rgb, depth = frame_q.get_nowait()   ← 取最新帧（尽力而为）    │
                        │     intrinsics = cam.get_intrinsics()                          │
                        │     r = _holistic_step(rgb, depth, intrinsics)  ────────────┐  │
                        │     if show_skeleton: 骨架绘制 → video_canvas（覆盖显示）      │  │
                        └────────────────────────────────────────────────────────────┼──┘
                                                                                     │
    _holistic_step 内部（L180-228）                                                   │
    ┌────────────────────────────────────────────────────────────────────────────────┼───┐
    │ holistic.process(rgb, depth, intrinsics,                                      │   │
    │                  map_to_arm=机械臂跟随开关,                                     │   │
    │                  arm_mapper=follower.map_wrist_to_arm_pose)                   │   │
    │      │  （HolisticLandmarker 一次性检出：人体 33 点 + 双手 21 点）               │   │
    │      ▼                                                                        │   │
    │  HolisticResult：pose_landmarks / hand_landmarks / wrist_3d /                 │   │
    │                   hand_angles_deg[16] / hand_fist_confidence /                │   │
    │                   arm_target_pose[6]（仅 map_to_arm=True 时计算）               │   │
    │      │                                                                        │   │
    │      ├─► 状态行拼接：人体✓ | 手✓ | 腕3D=(..) | 臂TCP=(..) | 握拳=0.87          │   │
    │      │                                                                        │   │
    │      ├─► 【臂跟随】arm_follow_var 且 arm_target_pose 存在 且 臂已连接           │   │
    │      │      └─► self.arm.movel(pose, block=False, timeout_s=5)                │   │
    │      │              └─► AuboK5ArmController ──► SDK moveLineP ──► 机械臂 TCP 运动│   │
    │      │                                                                        │   │
    │      └─► 【手跟随】hand_follow_var 且 手检出 且 hand 存在 且 未勾选 mimic_on     │   │
    │             └─► angles_rad = radians(hand_angles_deg)                          │   │
    │                   └─► self.hand.move_joints(angles_rad) ──► RY-H1 16 关节电机  │   │
    └────────────────────────────────────────────────────────────────────────────────┘
```

关键点：
- **一条数据源，两路消费**：相机采集线程只管把帧塞进 `frame_q`；主线程 `_poll_video` 里父类先消费一帧做手部识别，本文件再 `get_nowait()` 消费一帧做 Holistic 识别——两条视觉链路**共享同一相机、互不阻塞**。
- **两条执行通道**：腕→臂走 `movel`（运动学轨迹），手→灵巧手走 `move_joints`（16 关节角直发），**并行互不干扰**。
- **两套"骨架绘制"分层**：父类画的是 `hand_pose` 手部骨架；协同开启且勾选"显示骨架"时，本文件用 Holistic 骨架（人体 33 点 + 手 21 点）**覆盖重绘**到同一 canvas。

---

## 4. 模块头部：docstring、导入与路径引导（L1–L52）

### 4.1 模块 docstring（L2–L25）

```python
main_gui_holistic.py —— 协同总控制界面（L515 + Holistic 全身姿态 → 灵巧手 + 机械臂）
```

docstring 用三块讲清了本文件定位：
1. **继承方式**（L5–L6）：在 `gui/main_gui_arm.py`（臂+手扩展版）基础上"再叠加"协同面板；明确写出继承链 `MainGui（灵巧手）→ MainGuiArm（+机械臂）→ MainGuiHolistic（+协同控制）`。这是理解全文件的钥匙：**每一级只做"增量"**，父级代码原封不动。
2. **功能清单**（L8–L17）：完整保留相机/灵巧手/机械臂全部能力；新增协同面板的 5 件事——检测启停、手→16 角跟随、腕→TCP 跟随、骨架显示、实时状态、标定参数；第 3 条点出**安全基调**（使能需显式勾选、臂跟随默认关、速度比例共用）。
3. **用法与安全提示**（L19–L24）：`python -m gui.main_gui_holistic`；强调"协同会移动机械臂"，先跑 `apps/test_holistic.py --selfcheck` 手动验证映射，再小速度试跑，随时可停或急停。

### 4.2 路径引导（L32–L39）

```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
```

与 `main_gui.py` / `main_gui_arm.py` 完全相同的三行套路（详见 `10_pathsetup.md`）：
- 把**项目根目录**（`__file__` 的上两级，即 `RY-H1_vision_mimic/`）插到 `sys.path` 最前，保证 `from gui.xxx import ...`、`from vision.xxx import ...` 能直接命中；
- `os.chdir(sys.path[0])` 把工作目录切到项目根，保证相对路径资源（模型文件、config 目录）可找到；
- 重配 stdout/stderr 为 UTF-8（L36–L37），避免 Windows 控制台打印中文报 `UnicodeEncodeError`。

### 4.3 关键导入（L41–L52）

```python
import math            # 角度换算：hand_angles_deg(度) → move_joints(弧度)
import threading       # 由父类使用（采集线程）；本文件不直接建线程
import time
import tkinter as tk
from tkinter import ttk, messagebox   # ttk=皮肤控件；messagebox=弹窗（提示/错误）

import cv2             # 图像缩放/通道转换（_draw_holistic_to_canvas）
import numpy as np

from gui.main_gui_arm import MainGuiArm      # 父类：臂+手界面
from vision.holistic_pose import HolisticPoseEstimator   # 协同检测器
from arm.arm_follow import ArmFollower, DEFAULT_CALIB    # 腕→TCP 映射器 + 默认标定参数
```

注意导入顺序：`MainGuiArm` 在最前且**只导入父类**——`MainGui`（祖父类）由 `main_gui_arm` 内部导入，本文件不需要直接引用。

---

## 5. 类 `MainGuiHolistic` 总览与 `__init__`（L55–L66）

```python
class MainGuiHolistic(MainGuiArm):
    """协同总控制界面：灵巧手 + 机械臂 + Holistic 全身姿态协同。"""
```

### 5.1 类的地位

`MainGuiHolistic` 是三级继承链的**终端类**，承担"总装配"角色：

```
MainGui（gui/main_gui.py）           相机 / hand_pose 姿态 / 后处理 / 灵巧手 / row0~3 / mimic / _poll_video / _on_close(os._exit)
   └─► MainGuiArm（gui/main_gui_arm.py）    +机械臂 arm / arm_connected / row4 面板 / _arm_poll_loop / 覆写 _on_close
        └─► MainGuiHolistic（本文件）        +holistic 检测器 / follower / row5 协同面板 / _holistic_poll_loop / 覆写 _poll_video、_on_close
```

### 5.2 `__init__` 逐段（L58–L66）

```python
def __init__(self, root: tk.Tk):
    super().__init__(root)          # MainGuiArm → MainGui 全部界面
```

**第 1 步（L59）：`super().__init__(root)` 复用全部。**

这一行调用的是 `MainGuiArm.__init__`，而它内部又调用 `MainGui.__init__`，因此一次调用连锁完成：
- 创建并布局 row 0~3（顶部控制栏 / 视频区 / 16 关节滑条 / 状态栏），以及 row 4 机械臂面板；
- 初始化全部父类状态：`self.cam`（相机，初始 None）、`self.est`（手部姿态器）、`self.hand`（灵巧手控制器）、`self.arm`（机械臂控制器）、`self.arm_connected`（机械臂连接标志）、`self.frame_q`（帧队列 maxsize=2）、`self.checkbox_vars`（含 `mimic_on`、`show_skeleton` 等开关）、`self.video_canvas`（视频画布）；
- 装载校准配置、注册 `WM_DELETE_WINDOW → _on_close`。

> 本文件之后的所有代码都**假设这些成员已存在**——这正是继承带来的"契约"。

```python
    # Holistic 状态
    self.holistic: HolisticPoseEstimator | None = None
    self.follower: ArmFollower = ArmFollower()
    self.holistic_running = False
    self.holistic_state_var = tk.StringVar(value="协同未启动")
    self._build_holistic_ui()
    self._holistic_poll_loop()
```

**第 2 步（L61–L64）：初始化协同专属状态。**

| 成员 | 类型/初值 | 含义 |
|---|---|---|
| `self.holistic` | `HolisticPoseEstimator \| None`，初值 None | 协同检测器实例。**惰性创建**：只有用户勾选"启用"时才 `new`，因为要加载 `holistic_landmarker.task` 模型，失败时不能影响主界面启动 |
| `self.follower` | `ArmFollower()`（用 `DEFAULT_CALIB`） | 腕部 3D → 机械臂 TCP 目标 的映射器，纯计算无硬件依赖，启动即创建 |
| `self.holistic_running` | bool，初值 False | 协同运行总标志：`_holistic_toggle` 置 True/False；`_poll_video`、`_holistic_step` 都先看它 |
| `self.holistic_state_var` | `tk.StringVar("协同未启动")` | 协同面板 r1 的紫色状态文字（启停级状态） |

**第 3 步（L65）：`self._build_holistic_ui()`**——追加第 5 行协同面板（详见第 6 节）。

**第 4 步（L66）：`self._holistic_poll_loop()`**——启动 200ms 常驻心跳（详见第 14 节）。

> **设计要点**：`holistic` 惰性创建而 `follower` 立即创建。原因：`HolisticPoseEstimator` 构造函数会查找并加载 `lib/holistic_landmarker.task` 模型文件（找不到直接 `raise RuntimeError`），若在 `__init__` 里就创建，模型缺失会导致**整个 GUI 起不来**；而 `ArmFollower` 只是几个数字的封装，随时可建。

---

## 6. `_build_holistic_ui`：协同面板完整布局（L71–L126）

### 6.1 面板挂载（L72–L76）

```python
def _build_holistic_ui(self):
    root = self.root
    # 第 5 行：协同控制面板
    root.grid_rowconfigure(5, weight=0)
    frame = ttk.LabelFrame(root, text="协同控制（MediaPipe Holistic：人体→机械臂 + 手→灵巧手）")
    frame.grid(row=5, column=0, sticky="ew", padx=5, pady=2)
```

- `root.grid_rowconfigure(5, weight=0)`：**固定第 5 行高度**，不随窗口拉伸（与父类 row 4 的写法一致），保证三层面板各自规整；
- `ttk.LabelFrame`：带标题边框的面板，标题本身就把本面板的用途讲清楚了——**"人体→机械臂 + 手→灵巧手"**；
- `frame.grid(row=5, column=0, sticky="ew")`：贴满整行宽度。

### 6.2 行 r1：使能开关 + 检测状态（L78–L96）

```python
r1 = ttk.Frame(frame)
r1.pack(fill="x", padx=4, pady=2)
```

**① 启用检测总开关（L81–L83）**：

```python
self.holistic_enable_var = tk.BooleanVar(value=False)
ttk.Checkbutton(r1, text="启用 Holistic 检测", variable=self.holistic_enable_var,
                command=self._holistic_toggle).pack(side="left", padx=2)
```

- 初值 **False（默认关闭）**——安全设计：协同检测默认不运行；
- `command=self._holistic_toggle`：**勾选/取消的瞬间**触发启停逻辑（创建/释放检测器），不是等到下一帧；
- 这是协同的"总闸"：勾选后才会创建 `HolisticPoseEstimator` 并置 `holistic_running=True`。

**② 机械臂跟随开关（L84–L86）**：

```python
self.holistic_arm_follow_var = tk.BooleanVar(value=False)
ttk.Checkbutton(r1, text="机械臂跟随(腕→TCP)", variable=self.holistic_arm_follow_var,
                command=self._holistic_apply_flags).pack(side="left", padx=2)
```

- 初值 **False（默认关闭）**——安全设计：**机械臂跟随默认不动作**，必须显式勾选；
- 勾选后，`_holistic_step` 每帧把腕部 3D 映射成 TCP 目标并 `movel` 下发（见第 11 节）；
- `command=self._holistic_apply_flags`：切换时同步状态（当前实现里实际只同步手型，见第 9 节）。

**③ 灵巧手跟随开关（L87–L89）**：

```python
self.holistic_hand_follow_var = tk.BooleanVar(value=False)
ttk.Checkbutton(r1, text="灵巧手跟随(手→16角)", variable=self.holistic_hand_follow_var,
                command=self._holistic_apply_flags).pack(side="left", padx=2)
```

- 勾选后，`_holistic_step` 每帧把 Holistic 手部 21 点解算出的 16 关节角换算成弧度发给灵巧手；
- 与父类 `mimic_on` 的互斥关系见第 12 节（这是全文件最微妙的安全逻辑）。

**④ 左右手选择（L90–L95）**：

```python
self.holistic_side_var = tk.StringVar(value="right")
ttk.Label(r1, text="手:").pack(side="left", padx=(10, 2))
ttk.Radiobutton(r1, text="右", value="right", variable=self.holistic_side_var,
                command=self._holistic_apply_flags).pack(side="left")
ttk.Radiobutton(r1, text="左", value="left", variable=self.holistic_side_var,
                command=self._holistic_apply_flags).pack(side="left")
```

- 默认 `"right"`（右手）；
- 作用：**告诉 Holistic 用哪只手的 21 点来解算 16 关节角**（`HolisticPoseEstimator.set_hand_side`）以及用哪侧腕部做臂映射；
- 切换即 `command=_holistic_apply_flags` 实时同步给检测器，**无需重启协同**；
- 注意 MediaPipe 的 left/right 是**镜像语义**（画面中人的左右手），实际使用若发现"反手"就在这里切换（见 FAQ）。

**⑤ 启停状态文字（L96）**：

```python
ttk.Label(r1, textvariable=self.holistic_state_var, foreground="purple").pack(side="left", padx=8)
```

紫色文字，显示"协同未启动 / 协同运行中（检测人体+手）"，反映**启停级**状态（与 r3 的每帧级状态区分）。

### 6.3 行 r2：映射标定参数（L98–L119）

```python
r2 = ttk.Frame(frame)
r2.pack(fill="x", padx=4, pady=2)
```

**① offset(x,y,z)（L101–L106）**：

```python
ttk.Label(r2, text="映射标定 offset(x,y,z):").pack(side="left")
self.calib_offset_vars = []
for i in range(3):
    var = tk.StringVar(value=str(DEFAULT_CALIB["offset"][i]))
    self.calib_offset_vars.append(var)
    ttk.Entry(r2, textvariable=var, width=6).pack(side="left", padx=1)
```

- 三个 `StringVar` 的初值直接取自 `arm/arm_follow.py` 的 `DEFAULT_CALIB["offset"]`（`[0.0, 0.0, 0.0]`），保证 GUI 显示与映射器内部一致；
- 语义：**相机坐标系原点相对机械臂基座系的平移（米）**——现场标定时，把"人手移到期望位置，记录机械臂实际目标"逐步调整。

**② scale(x,y,z)（L107–L112）**：初值 `DEFAULT_CALIB["scale"]`（`[1.0, 1.0, 1.0]`），**相机米→机械臂米的比例**，通常 ≈1，有缩放差异再调。

**③ add(x,y,z)（L113–L118）**：初值 `DEFAULT_CALIB["add"]`（`[0.35, 0.0, 0.10]`），**目标附加平移**，默认把"人前"映射到"臂前"的工作距离。

**④ 应用按钮（L119）**：

```python
ttk.Button(r2, text="应用标定", command=self._holistic_apply_calib).pack(side="left", padx=6)
```

点击后把 9 个输入框解析成 `float` 并写入 `self.follower`（`ArmFollower.update_calib`），供下一帧映射生效（详见第 10 节）。

### 6.4 行 r3：状态显示（L121–L126）

```python
r3 = ttk.Frame(frame)
r3.pack(fill="x", padx=4, pady=2)
self.holistic_status_var = tk.StringVar(value="状态: -")
ttk.Label(r3, textvariable=self.holistic_status_var, font=("Consolas", 8),
          foreground="purple").pack(side="left")
```

- 等宽字体（Consolas）保证 `腕3D=(0.12,-0.30,1.20)` 这类数值串对齐、不跳动；
- 内容由 `_holistic_step` 每帧覆盖更新（见第 11 节）。

> **布局小结**：r1 = 三开关 + 手型 + 启停状态；r2 = 9 个标定输入框 + 应用按钮；r3 = 每帧状态。整个面板**不引入任何新线程**——所有协同工作都挂在 Tk 主线程的事件循环上。

---

## 7. `_holistic_toggle`：启用/停止检测（L131–L147）

```python
def _holistic_toggle(self):
    if self.holistic_enable_var.get():
        # 启动
        if self.cam is None:
            messagebox.showwarning("提示", "请先启动相机（L515 效果最佳）")
            self.holistic_enable_var.set(False)
            return
        try:
            self.holistic = HolisticPoseEstimator(hand_side=self.holistic_side_var.get())
            self.holistic_running = True
            self.holistic_state_var.set("协同运行中（检测人体+手）")
        except Exception as exc:
            messagebox.showerror("Holistic 启动失败", str(exc))
            self.holistic = None
            self.holistic_enable_var.set(False)
    else:
        self._holistic_stop()
```

### 7.1 启动分支（勾选）

按顺序执行**三道关卡**：

1. **依赖相机检查（L134–L137）**：`self.cam is None` → 弹警告"请先启动相机（L515 效果最佳）"，**并把勾选复位为 False**。
   - 原因：Holistic 检测需要 RGB 帧（+深度做 3D），没有相机就没有输入源；
   - 注意：**只查了 cam 是否启动，不查帧率/分辨率**——L515 只是建议（RGB+深度一体、带内参），USB 摄像头也能跑（深度缺失时 `_pose_to_3d` 会用相对深度粗补全）。
2. **创建检测器（L139）**：`HolisticPoseEstimator(hand_side=...)`。构造过程会：
   - 检查 `mediapipe` 是否安装（否则 `RuntimeError: 请安装 mediapipe>=0.10.14`）；
   - 搜索模型文件 `holistic_landmarker.task`（cwd → 项目根 → `lib/` → 本文件目录，见 `vision/holistic_pose.py` 的 `_find_model_file`），找不到直接抛 `RuntimeError` 并给出下载 URL；
   - 创建 `HolisticLandmarker`（Tasks API）+ 用 `object.__new__` 组合一个"裸" `HandPoseEstimator` 复用 16 关节角解算链。
   - 所以**模型加载失败只会发生在这一步**，且被 `try/except` 兜住（见第 3 关）。
3. **置运行标志（L140–L141）**：`holistic_running=True` + 状态文字"协同运行中（检测人体+手）"。此后 `_poll_video` 每帧都会走协同处理。

### 7.2 启动失败兜底（L142–L145）

```python
except Exception as exc:
    messagebox.showerror("Holistic 启动失败", str(exc))
    self.holistic = None
    self.holistic_enable_var.set(False)
```

- 弹错误框展示异常原文（最常见是模型文件缺失）；
- **三连复位**：`holistic=None`（释放半成品）、`holistic_running` 保持 False、勾选复位为 False——保证 GUI 状态与真实运行状态永远一致，不会出现"勾着却不在跑"的假象。

### 7.3 停止分支（取消勾选，L146–L147）

直接调 `self._holistic_stop()`（下一节）。**注意：取消勾选不会自动关闭两个跟随开关**——如果用户只取消"启用"而忘了关"机械臂跟随"，`holistic_running` 变 False 后 `_holistic_step` 直接短路返回，跟随自然失效，无安全隐患；但重启协同后跟随开关仍处于勾选状态，会立即开始跟随，操作上需留意。

---

## 8. `_holistic_stop`：释放检测器（L149–L157）

```python
def _holistic_stop(self):
    if self.holistic is not None:
        try:
            self.holistic.close()
        except Exception:
            pass
    self.holistic = None
    self.holistic_running = False
    self.holistic_state_var.set("协同未启动")
```

- **释放模型资源**：`self.holistic.close()` 内部调 `HolisticLandmarker.close()`（释放底层推理资源），异常静默吞掉（`except: pass`），因为释放失败不影响后续状态复位；
- **状态三连复位**：`holistic=None`（后续 `_poll_video` 的 `self.holistic_running` 判断会先短路，不会触碰 None）、`holistic_running=False`、状态文字"协同未启动"；
- **调用点有三处**：① 用户取消"启用"勾选；② 关窗时 `_on_close` 最先调用；③ 启动失败兜底（间接，靠复位勾选触发）。
- 注意：**不停止机械臂/灵巧手的当前运动**——协同停止只意味着"不再下发新目标"，正在执行的轨迹由各自控制器的既有机制处理。

---

## 9. `_holistic_apply_flags`：开关/手型同步（L159–L164）

```python
def _holistic_apply_flags(self):
    """同步手型/跟随开关。"""
    if self.holistic is not None:
        self.holistic.set_hand_side(self.holistic_side_var.get())
    if not self.holistic_arm_follow_var.get() and self.holistic_arm_follow_var.get() is False:
        pass
```

### 9.1 实际生效的部分：手型同步

```python
if self.holistic is not None:
    self.holistic.set_hand_side(self.holistic_side_var.get())
```

- 把 r1 的"右/左"单选值实时写入检测器（`HolisticPoseEstimator.set_hand_side`），**切换手型无需重启协同**；
- 只在 `holistic` 已创建（非 None）时执行，避免空引用。

### 9.2 两个跟随开关为什么"什么都不用做"？

`holistic_arm_follow_var` / `holistic_hand_follow_var` 的当前值在 `_holistic_step` 里**每帧实时 `.get()`**（L187、L213、L221），所以开关一勾选/取消，**下一帧就生效**——不需要在这里做任何搬运，`_holistic_apply_flags` 挂到它们的 `command` 上，真正目的只是"顺路同步一下手型"。

### 9.3 遗留死代码（L163–L164）

```python
if not self.holistic_arm_follow_var.get() and self.holistic_arm_follow_var.get() is False:
    pass
```

这是一个**恒真且无操作的条件**（`not False and False is False` 恒为 True，然后 `pass`），是开发过程中留下的冗余代码，**没有任何实际作用**，可安全删除。阅读时直接忽略即可——本方法的功能只有 `set_hand_side` 一行。

---

## 10. `_holistic_apply_calib`：标定参数校验与应用（L166–L175）

```python
def _holistic_apply_calib(self):
    try:
        self.follower.update_calib(
            offset=[float(v.get()) for v in self.calib_offset_vars],
            scale=[float(v.get()) for v in self.calib_scale_vars],
            add=[float(v.get()) for v in self.calib_add_vars],
        )
        self.holistic_status_var.set("标定参数已应用")
    except ValueError:
        messagebox.showerror("输入错误", "标定参数必须是数字")
```

### 10.1 参数解析（L167–L172）

- 从 9 个输入框（`calib_offset_vars`×3、`calib_scale_vars`×3、`calib_add_vars`×3）逐个 `v.get()` 取字符串再 `float()` 转数字；
- 组成三个三元列表，一次性传给 `ArmFollower.update_calib(offset=..., scale=..., add=...)`；
- `update_calib` 内部（`arm/arm_follow.py` L94–L98）只接受白名单键 `offset/scale/add/fixed_rpy/min_xyz/max_xyz`，非空即 `setattr` 覆盖——所以**应用后立即生效**，下一帧 `map_wrist_to_arm_pose` 就用新参数。

### 10.2 校验兜底（L174–L175）

- `float()` 对任意一个输入框解析失败（空串、非数字）都会抛 `ValueError`，被 `except ValueError` 捕获 → 弹错误框"标定参数必须是数字"；
- **只捕获 ValueError**：其他异常（理论上 `update_calib` 不太会抛）不在这里处理，保持简单；
- 参数合法性（如负的 scale、越界 offset）**不做数值校验**——交给 `ArmFollower.map_wrist_to_arm_pose` 内部的 `min_xyz/max_xyz` 安全区间裁剪兜底（见第 13 节），这正是"参数可现场乱调、结果不会出安全区"的设计。

---

## 11. `_holistic_step`：每帧协同核心（L180–L228）

```python
def _holistic_step(self, rgb, depth, intrinsics):
    """在 _poll_video 取到帧后调用：检测 + 映射 + 可选跟随。"""
```

这是全文件**最核心的方法**，每帧依次完成：**检测 → 状态显示 → 臂跟随 → 手跟随**。下面分段拆解。

### 11.1 守卫：未运行直接短路（L182–L183）

```python
if not self.holistic_running or self.holistic is None:
    return None
```

双条件保险：总开关没开、或检测器不存在（启动失败/已停止），直接返回 None，**一行都不往下走**。这也是"取消启用后跟随立即失效"的机制保证。

### 11.2 检测：一次推理拿全部结果（L184–L192）

```python
try:
    results = self.holistic.process(
        rgb, depth, intrinsics,
        map_to_arm=self.holistic_arm_follow_var.get(),
        arm_mapper=self.follower.map_wrist_to_arm_pose,
    )
except Exception as exc:
    self.holistic_status_var.set(f"检测异常: {exc}")
    return None
```

- `process` 是 `HolisticPoseEstimator.process`（`vision/holistic_pose.py` L231）：一次 `HolisticLandmarker.detect` 同时拿到**人体 33 点 + 双手各 21 点**，再组合内部 hand_pose 引擎解算出 `hand_angles_deg[16]`、`hand_fist_confidence`、`wrist_3d`；
- `map_to_arm=机械臂跟随开关`：**只有勾选时才做腕→TCP 映射**，省掉无谓计算；
- `arm_mapper=self.follower.map_wrist_to_arm_pose`：传入映射函数引用（`ArmFollower` 的映射公式 `(wrist - offset) * scale + add` + 安全裁剪，见第 13 节）——**标定参数在此生效**；
- 任何异常（如分辨率异常、内参缺失）→ 状态行显示"检测异常: …"，返回 None，**不崩溃主循环**。

### 11.3 无结果分支（L193–L195）

```python
if not results:
    self.holistic_status_var.set("状态: 未检测到人体/手")
    return None
```

- `process` 在"既没有人也没有手"时返回空列表；
- 状态行提示"未检测到人体/手"——告诉用户"人在画面里站远一点/露出手"；
- 返回 None：**不进入跟随与绘制**。

### 11.4 状态显示：把结果翻译成人话（L196–L210）

```python
r = results[0]
parts = []
if r.pose_detected:
    parts.append("人体✓")
if r.hand_detected:
    parts.append("手✓")
if r.wrist_3d is not None:
    w = r.wrist_3d
    parts.append(f"腕3D=({w[0]:.2f},{w[1]:.2f},{w[2]:.2f})")
if r.arm_target_pose is not None:
    p = r.arm_target_pose
    parts.append(f"臂TCP=({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})")
if r.hand_fist_confidence is not None:
    parts.append(f"握拳={r.hand_fist_confidence:.2f}")
self.holistic_status_var.set("状态: " + " | ".join(parts))
```

- `HolisticResult` 的四个可选字段，**有什么显示什么**：
  - `pose_detected`：人体 33 点是否检出（属性由 `pose_landmarks is not None` 推导）；
  - `hand_detected`：所选手的 21 点是否检出；
  - `wrist_3d`：用于臂映射的腕部 3D 坐标（米，`.2f` 两位小数）；
  - `arm_target_pose`：映射后的机械臂 TCP 目标 `[x,y,z,rx,ry,rz]`——**只有勾选机械臂跟随才会有**（`map_to_arm=True` 才计算）；
  - `hand_fist_confidence`：深度辅助握拳置信度（0~1，越大越像握拳）。
- 拼成 `状态: 人体✓ | 手✓ | 腕3D=(0.12,-0.30,1.20) | 臂TCP=(0.35,0.00,0.10) | 握拳=0.87` 一行写进 r3——**这一步不产生任何动作，纯观察**，方便现场先"看"再"跟"。

### 11.5 机械臂跟随（腕→TCP）（L212–L218）

```python
# ---- 机械臂跟随（腕→TCP）----
if self.holistic_arm_follow_var.get() and r.arm_target_pose is not None:
    if self.arm_connected and self.arm is not None:
        try:
            self.arm.movel(r.arm_target_pose, block=False, timeout_s=5)
        except Exception as exc:
            self.holistic_status_var.set(f"臂跟随异常: {exc}")
```

执行条件（**三重闸门，缺一不可**）：
1. **跟随开关开着**（`holistic_arm_follow_var.get()`）——用户明确授权才动臂；
2. **本帧有目标**（`arm_target_pose is not None`）——需要 `map_to_arm=True` 且腕部 3D 有效且映射成功；
3. **臂已连接**（`arm_connected and arm is not None`）——未连臂时静默跳过，不弹窗（避免每帧弹窗轰炸）。

动作：`self.arm.movel(target, block=False, timeout_s=5)` 把 TCP 目标**非阻塞**下发给 Aubo K5（为什么非阻塞见第 13 节）。异常 → 状态行"臂跟随异常: …"。

### 11.6 灵巧手跟随（手→16角）（L220–L227）

```python
# ---- 灵巧手跟随（手→16角，独立于父类 mimic 开关，避免双重下发）----
if self.holistic_hand_follow_var.get() and r.hand_detected:
    if self.hand is not None and not self.checkbox_vars["mimic_on"].get():
        try:
            angles_rad = [math.radians(a) for a in r.hand_angles_deg]
            self.hand.move_joints(angles_rad)
        except Exception as exc:
            self.holistic_status_var.set(f"手跟随异常: {exc}")
```

执行条件（四重闸门）：
1. **跟随开关开着**（`holistic_hand_follow_var.get()`）；
2. **本帧检出所选手**（`r.hand_detected`）；
3. **灵巧手已连接**（`self.hand is not None`）；
4. **父类 mimic 模仿未开**（`not self.checkbox_vars["mimic_on"].get()`）——防双重下发，详见第 12 节。

动作：`hand_angles_deg`（度）→ `math.radians` 逐个转弧度 → `hand.move_joints(angles_rad)` 直发 16 关节。异常 → 状态行"手跟随异常: …"。

### 11.7 返回值（L228）

```python
return r
```

把 `HolisticResult` 返回给 `_poll_video`，供骨架绘制使用（`draw_skeleton(rgb, [r])`）。无结果/异常路径统一返回 None。

---

## 12. 深挖一：灵巧手跟随为何独立于 mimic 开关 + 防双重下发

这是全文件**最需要讲透**的安全逻辑，涉及两条"手→灵巧手"通道的竞争。

### 12.1 两条通道都会发 `move_joints`

**通道 A：父类 mimic（动作模仿）**，在 `MainGui._poll_video`（`gui/main_gui.py` L578–L582）：

```python
if self.checkbox_vars["mimic_on"].get() and self.hand is not None and angles_deg is not None:
    self._mimic_apply(angles_deg, fist_conf)   # 内部最终 hand.move_joints(angles_rad)
```

**通道 B：本文件 Holistic 手跟随**，即上面 11.6 的 `hand.move_joints(angles_rad)`。

两条通道的输入源不同：
- 通道 A 的 `angles_deg` 来自 `hand_pose` 检测器（`self.est`，独立 MediaPipe 手部模型，仅手部）；
- 通道 B 的 `hand_angles_deg` 来自 Holistic 检测器（人体+手一体模型，同一帧的另一路推理）。

### 12.2 同时开启会怎样（"打架"）

如果两个开关同时打开，**同一帧里**可能出现：

```
_poll_video 主循环（~30ms/帧）
  ① super()._poll_video()
       └─ mimic_on=True → 通道A：move_joints(A帧角度)   ← 基于 hand_pose 解算
  ② 本文件协同处理
       └─ hand_follow=True → 通道B：move_joints(B帧角度) ← 基于 Holistic 解算
```

- 两个解算链的参数、死区、平滑策略不同，**同一帧算出的 16 个角度数值不一致**；
- 两次 `move_joints` 紧挨着发到同一个 RY-H1 控制器，**后发覆盖先发**——电机在两套目标间来回拉扯，表现为：手指高频抖动、动作混乱、甚至电机电流异常；
- 这是典型的"双主控写同一外设"竞争，**必须互斥**。

### 12.3 防双重下发条件（L222 的关键一行）

```python
if self.hand is not None and not self.checkbox_vars["mimic_on"].get():
```

- **`not mimic_on` 作为通道 B 的前置闸门**：只要父类模仿还开着，Holistic 手跟随就**整帧静默跳过**（不报错、不弹窗，只不动作）；
- 用户想用 Holistic 手跟随，**必须先关掉父类的"动作模仿"开关**；
- 反之，Holistic 手跟随开着时用户又勾了 mimic，mimic 通道照常工作，Holistic 通道被闸门挡下——**任何时刻最多一条通道在发关节指令**。

### 12.4 为什么叫"独立于 mimic 开关"

- **独立启动**：Holistic 手跟随**不需要** mimic_on 为 True 才能工作（普通直觉会以为"跟随=模仿的升级版"，其实两者毫无依赖）——它自己有一套检测源（Holistic）和开关（`holistic_hand_follow_var`）；
- **独立受控**：两者开关完全分离，用户可只开 Holistic 跟随、只开 mimic、或都关；
- **互斥执行**：唯一交集是"同一时刻不能同时下发"，由 `not mimic_on` 闸门保证。

一句话总结：**开关各自独立（能分别打开），执行互斥（不能同时下发）**。

---

## 13. 深挖二：机械臂跟随为什么用 `block=False` 非阻塞

### 13.1 调用发生的线程与节奏

`_holistic_step` 是在 `_poll_video` 里被调的，而 `_poll_video` 是 **Tk 主线程**上由 `root.after(30, ...)` 驱动的轮询（约 30ms 一帧）。这意味着：**跟随的每次 movel 都发生在 GUI 主线程内**。

### 13.2 如果用 `block=True` 会怎样

```python
self.arm.movel(target, block=True, timeout_s=30)   # 反面教材
```

- `block=True` 会**等待整段轨迹执行完毕才返回**：Aubo K5 走一小段可能要 0.5~2 秒（取决于距离和速度比例）；
- 主线程被卡住期间：**Tk 事件循环停摆** → 窗口"假死"（点停止没反应、状态不刷新）、`after` 链中断、后续帧无人消费（`frame_q` 满后采集线程开始丢帧）；
- 更要命的是：每帧跟随时若都阻塞到轨迹走完，跟随周期就退化成"机械臂一动、GUI 一停"，**完全丧失实时性**。

### 13.3 `block=False` 的语义与"忙则丢帧下帧再跟"

```python
self.arm.movel(r.arm_target_pose, block=False, timeout_s=5)
```

- **立即返回**：`block=False` 只是把"目标位姿"投递给机械臂 SDK（底层 `moveLineP`），不等轨迹完成；
- 主线程继续下一帧：**每帧（30ms）都计算新腕部位置、下发新目标**，机械臂在一条连续的目标流里"追"人手——这就是跟随的本质；
- `timeout_s=5`：给底层 RPC 一个超时上限，防止网络/控制器异常时主线程被挂死；
- **忙则丢帧下帧再跟**：如果某一帧机械臂 SDK 正忙（上一帧指令还在排队），这一帧的 movel 要么排队要么被控制器按新目标处理；主线程**绝不会等它**，直接进入下一帧。视觉侧同理——`frame_q.get_nowait()` 是**非阻塞取帧**，取不到就跳过本帧协同，下一帧再跟。整个跟随是"尽力而为的离散采样"，任何一环忙，丢掉的只是"这一帧的目标"，实时性由高频重试保证。

### 13.4 配套的安全裁剪（`ArmFollower` 内部）

`map_wrist_to_arm_pose`（`arm/arm_follow.py` L77–L91）在映射公式之外还做了**逐轴安全区间裁剪**：

```python
v = (wrist_3d[i] - offset[i]) * scale[i] + add[i]
lo, hi = min_xyz[i], max_xyz[i]
xyz.append(max(lo, min(hi, v)))     # 裁剪到 [min_xyz, max_xyz]
```

默认 `min_xyz=[0.15,-0.40,0.10]`、`max_xyz=[0.90,0.40,0.80]`（米），保证**无论人手怎么挥、标定参数怎么调，下发到机械臂的目标 xyz 都落在安全工作区间内**。姿态 `rx/ry/rz` 取固定 `fixed_rpy=[π,0,0]`（默认"朝下抓取"），不随人体姿态乱变。这是"非阻塞高频跟随"能安全成立的最后一道保险。

---

## 14. `_holistic_poll_loop`：常驻调度心跳（L230–L237）

```python
def _holistic_poll_loop(self):
    """常驻调度（防止 after 链因异常中断）。"""
    try:
        if self.holistic_running:
            pass
    except Exception:
        pass
    self.root.after(200, self._holistic_poll_loop)
```

### 14.1 行为拆解

- 函数体里的 `try/if/pass` 是**占位/保活壳**：当前版本没有真正要周期做的事（协同的每帧工作在 `_poll_video` 路径完成），这段代码等于"检查一下运行标志，无操作"；
- **真正的关键在最后一行**：`self.root.after(200, self._holistic_poll_loop)` 无条件地**每 200ms 把自己再调度一次**——一个永远不死的 after 链。

### 14.2 为什么需要"防 after 链中断"

Tk 的 `after` 是**单次定时器**：`after(ms, f)` 只会触发一次，持续轮询必须靠回调内部"再调一次自己"。这类链式调度有两个脆弱点：

1. **父类的 `_poll_video` 链依赖相机运行**：`MainGui._poll_video` 末尾 `if self._running: after(30, ...)` ——相机一停，`_running=False`，**整条视频轮询链就断了**；
2. **异常会掐断整条链**：链上任意一次回调抛异常且未被捕获，`after` 链不会自动续接（取决于异常是否冒泡出 Tk 主循环）。

`_holistic_poll_loop` 用**完全独立的一条 200ms 心跳**（自己 try/except 包住、自己无条件续接）保证：即使视频链断了、即使某次处理异常，**这条心跳永远在跳**。它既是"协同模块的保活锚点"，也为将来把周期性任务（如定期刷新、看门狗）挂进来预留了位置。

### 14.3 与 `_arm_poll_loop`（800ms）的关系

| 轮询 | 周期 | 目的 | 依赖 |
|---|---|---|---|
| `_arm_poll_loop`（父类） | 800ms | 刷新机械臂状态显示 | 机械臂已连接 |
| `_holistic_poll_loop`（本文件） | 200ms | 常驻心跳，保活 after 链 | 无（无条件续接） |

两者互不干扰、各自独立调度。

---

## 15. `_poll_video` 覆写：super 之后追加协同处理（L242–L262）

```python
def _poll_video(self):
    # 调用父类原逻辑（取帧/推理/显示/模仿）
    super()._poll_video()
    # 若 holistic 运行且相机在，追加协同处理
    if self.holistic_running and self.cam is not None:
        try:
            # 从队列取最新帧（非阻塞）
            rgb, depth = self.frame_q.get_nowait()
            intrinsics = None
            if hasattr(self.cam, 'get_intrinsics'):
                intrinsics = self.cam.get_intrinsics()
            r = self._holistic_step(rgb, depth, intrinsics)
            # 绘制骨架叠加到画面（在原视频 canvas 上再画一层）
            if r is not None and self.checkbox_vars["show_skeleton"].get():
                try:
                    disp = self.holistic.draw_skeleton(rgb, [r])
                    self._draw_holistic_to_canvas(disp)
                except Exception:
                    pass
        except Exception:
            pass
```

### 15.1 先 super：父类逻辑一条不少

`super()._poll_video()` 完整执行父类的取帧、手部推理、mimic、关节角叠加、原画面显示、`after(30)` 续接（见 `gui/main_gui.py` L522–L640）。**父类行为完全保留**——协同层只是"追加"，不是"替换"。

### 15.2 再追加：协同处理（L246–L262）

前置条件 `self.holistic_running and self.cam is not None`：总开关开着且相机在（相机停则没帧可取，直接跳过）。

**① 取最新帧（L249）**：

```python
rgb, depth = self.frame_q.get_nowait()
```

- **非阻塞取帧**：队列空（父类刚消费完最后一帧）时抛 `queue.Empty`，被最外层 `except Exception: pass` 兜住——**本帧协同处理被跳过，下一帧再来**；
- 语义：父类先消费了一帧（可能在队列有 2 帧时还剩 1 帧），这里拿的是**队列里的最新帧**，与父类处理的那帧最多差 1 帧，可接受；
- 注意这里**没有 while 清空队列**，只取一次，保证不拖慢主循环。

**② 取相机内参（L250–L252）**：`cam.get_intrinsics()`（存在才取，USB 相机可能没有）→ 传给 Holistic 用于像素→米制的 3D 反投影。

**③ 执行协同核心（L253）**：`r = self._holistic_step(rgb, depth, intrinsics)` —— 第 11 节的全部逻辑（检测/状态/臂跟/手跟）。

**④ 骨架绘制（L255–L260）**：

```python
if r is not None and self.checkbox_vars["show_skeleton"].get():
    disp = self.holistic.draw_skeleton(rgb, [r])
    self._draw_holistic_to_canvas(disp)
```

- 条件：本帧有检测结果 **且** 父类"显示骨架"开关开着（复用父类 checkbox，**共用同一个开关**）；
- `draw_skeleton`（`vision/holistic_pose.py` L367）在原始帧上画人体 33 点连线 + 手 21 点连线；
- `_draw_holistic_to_canvas` 把画好的帧**覆盖**到 `video_canvas`——此时画面上是 Holistic 骨架（覆盖了父类刚画的手部骨架，两套骨架不会同时残留）；
- 若本帧无结果或开关关着：**父类已经画好的画面原样保留**，不会闪黑。

### 15.3 双 try/except 的层次

- 内层 try（L257–L260）：只管**骨架绘制**，异常静默（绘制失败不影响协同主逻辑）；
- 外层 try（L247–L262）：管**取帧+协同**，异常静默（取帧空、内参异常、任何意外都吞掉，**主循环绝不因协同崩溃**）。

---

## 16. `_draw_holistic_to_canvas`：骨架帧 cover 缩放显示（L264–L286）

```python
def _draw_holistic_to_canvas(self, frame: np.ndarray):
    """把 holistic 骨架帧显示到视频画布（等比缩放+居中裁剪，与原逻辑一致）。"""
```

这段的缩放算法与父类 `MainGui._poll_video` 的显示段（`gui/main_gui.py` L611–L629）**完全同款**，保证两种画面的观感一致。

### 16.1 逐段

```python
from PIL import Image, ImageTk
canvas_w = self.video_canvas.winfo_width()
canvas_h = self.video_canvas.winfo_height()
if canvas_w < 2 or canvas_h < 2:
    canvas_w, canvas_h = 800, 600
```

- 每次调用临时 `import PIL`（懒加载，避免模块级引入开销）；
- 取画布实际尺寸；窗口未完成布局时 `winfo_width()` 可能返回 1，兜底 800×600。

```python
src_h, src_w = frame.shape[:2]
scale = max(canvas_w / src_w, canvas_h / src_h)   # cover：取较大缩放比
new_w = max(1, int(round(src_w * scale)))
new_h = max(1, int(round(src_h * scale)))
resized = cv2.resize(frame, (new_w, new_h))
```

- **cover 缩放**：`scale = max(画布宽/源宽, 画布高/源高)` —— 放大到**至少一边填满画布**（另一边必然超出）；
- 与"contain（整体放进画布，留黑边）"不同，cover 保证**画面无黑边、铺满画布**，代价是边缘被裁掉。

```python
x0 = max(0, (new_w - canvas_w) // 2)
y0 = max(0, (new_h - canvas_h) // 2)
crop = resized[y0:y0 + canvas_h, x0:x0 + canvas_w]
```

- **居中裁剪**：从放大图的正中心切出画布大小的窗口，`max(0, …)` 防止尺寸反超时出现负索引。

```python
rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
img = ImageTk.PhotoImage(Image.fromarray(rgb))
self.video_canvas.delete("all")
self.video_canvas.create_image(0, 0, anchor="nw", image=img)
self.video_canvas.image = img
```

- BGR→RGB → PIL Image → `PhotoImage`；
- **`delete("all")` 清掉画布旧内容**（父类刚画的那帧），再贴新图；
- `self.video_canvas.image = img` 保留引用——**否则 PhotoImage 被 GC 回收，画面立即消失**（Tk 经典坑）。

### 16.2 与父类显示的关系

| 时刻 | canvas 上的内容 |
|---|---|
| 父类 `_poll_video` 执行完 | 父类手部骨架帧（hand_pose 绘制） |
| 协同开启 + 有结果 + show_skeleton | **被 Holistic 骨架帧覆盖**（人体+手） |
| 协同开启但无结果 / show_skeleton 关 | 保留父类画面不动 |

---

## 17. `_on_close`：先停协同再走父类收尾（L291–L293）

```python
def _on_close(self):
    self._holistic_stop()
    super()._on_close()
```

### 17.1 执行顺序链

```
用户点窗口 ✕
   └─► MainGuiHolistic._on_close
         ① _holistic_stop()      ← 释放 HolisticLandmarker、holistic_running=False
         ② super()._on_close()   ← MainGuiArm._on_close（arm.close() 断机械臂）
              └─► MainGui._on_close
                     ├─ _running=False + after_cancel  ← 停视频轮询链
                     ├─ _stop_camera()                  ← 停采集线程、释放相机
                     ├─ _disconnect_hand()              ← 断灵巧手
                     ├─ root.quit() / root.destroy()
                     └─ os._exit(0)                     ← 最终强杀进程
```

### 17.2 为什么必须先 `_holistic_stop()`

- 父类 `MainGui._on_close` 最后是 **`os._exit(0)` 强杀进程**（`gui/main_gui.py` L822）——一旦执行到那里，**后面所有代码都不会再跑**；
- 所以在调用 `super()._on_close()` **之前**，必须把协同模块自己的资源（HolisticLandmarker 底层推理资源）释放掉，否则直接 `os._exit` 会跳过 `close()`，模型资源来不及回收；
- 同理，`MainGuiArm` 也是这个套路：先 `arm.close()` 再 super——**每一级都在调用父类收尾前先清理自己新增的资源**，形成"从子到父"的逆序释放链。

### 17.3 协同停止 ≠ 停止硬件运动

`_holistic_stop()` 只停"协同下发"，机械臂正在执行的轨迹由 `MainGuiArm` 的 `arm.close()` 处理、灵巧手由 `_disconnect_hand()` 处理——**各层各自负责自己那摊硬件**，职责清晰。

---

## 18. `main` 与程序入口（L296–L303）

```python
def main():
    root = tk.Tk()
    MainGuiHolistic(root)
    root.mainloop()

if __name__ == "__main__":
    main()
```

- 标准 Tk 入口：建根窗口 → 实例化 `MainGuiHolistic`（构造期间即完成三层 UI 与所有轮询启动）→ 进入 `mainloop()` 事件循环；
- `MainGuiHolistic` 构造里 `_holistic_poll_loop()` 已经启动了第一条 after 心跳，配合 `MainGui.__init__` 里注册的 `WM_DELETE_WINDOW → _on_close`，整个生命周期闭环：**启动即就绪、关闭即清理**。

---

## 19. 与 `main_gui_arm.py` 的差异对比表

| 维度 | `main_gui_arm.py`（父类） | `main_gui_holistic.py`（本文件） |
|---|---|---|
| 继承 | `MainGuiArm(MainGui)` | `MainGuiHolistic(MainGuiArm)` |
| 新增面板 | 第 4 行：机械臂控制（连接/电源/关节/位姿/联动） | 第 5 行：协同控制（检测开关/两路跟随/标定/状态） |
| 新增对象 | `arm`、`arm_connected`、`arm_state_var` | `holistic`（惰性）、`follower`、`holistic_running`、两个 state_var |
| 轮询 | `_arm_poll_loop`（800ms，刷机械臂状态） | `_holistic_poll_loop`（200ms，常驻心跳保活） |
| 覆写方法 | `_on_close`（先断臂再 super） | `_poll_video`（super 后追加协同）、`_on_close`（先停 holistic 再 super） |
| 机械臂运动来源 | 手动按钮（movej/movel，`block=True`） | 协同跟随（每帧 `movel(block=False)`） |
| 灵巧手运动来源 | mimic 开关（`_mimic_apply`） | Holistic 手跟随（`move_joints`），与 mimic 互斥 |
| 标定参数 | 手部角度校准（`_apply_calib` → `self.est`） | 臂映射标定（`_holistic_apply_calib` → `self.follower`） |
| 骨架来源 | `hand_pose` 手部骨架 | Holistic 人体 33 点 + 手 21 点骨架（覆盖显示） |

---

## 20. 安全设计

协同控制是**会动机械臂**的功能，本文件围绕"默认不动作、显式才使能、随时可停"设计了一整套安全护栏：

### 20.1 跟随默认关闭（默认不动作）

- `holistic_enable_var` / `holistic_arm_follow_var` / `holistic_hand_follow_var` **三个开关初值全部 False**（L81/L84/L87）：程序启动后，即使相机、机械臂、灵巧手全部就绪，**系统也不会自己动**，必须用户显式勾选；
- 尤其"机械臂跟随"独立于"启用检测"单独勾选——可以先开检测**只观察状态行**（人体✓/腕3D/臂TCP），确认映射合理后再开跟随。

### 20.2 机械臂侧多重保险

- **非阻塞高频跟随 + 超时**：`movel(block=False, timeout_s=5)`（L216），主线程永不等待；
- **目标安全区间裁剪**：`ArmFollower` 内部 `min_xyz/max_xyz`（默认 `[0.15,-0.40,0.10]`~`[0.90,0.40,0.80]`）把每帧目标 xyz 裁进安全区（`arm/arm_follow.py` L87–L89）；
- **姿态固定**：`rx/ry/rz` 取固定"朝下抓取"姿态 `[π,0,0]`，不随人体晃动；
- **速度比例共用**：机械臂所有运动（含跟随）都走父类 `arm_fraction_var` 速度比例滑条（默认低值，可现场调 0.05~1.0），跟随也不例外——**用低速试跑是文档明确要求的流程**；
- **未连臂不动作**：三重闸门之一（L214），没连上机械臂时跟随静默跳过。

### 20.3 防双重下发（手侧互斥）

- Holistic 手跟随与父类 mimic 通道**互斥执行**：`not self.checkbox_vars["mimic_on"].get()` 闸门（L222）保证同一时刻只有一条通道在向灵巧手发关节指令，杜绝"两套角度打架"导致的抖动与异常电流（详见第 12 节）。

### 20.4 状态可视化（看得见才安全）

- r3 每帧显示：人体✓ / 手✓ / 腕3D / 臂TCP 目标 / 握拳置信度——**动作发生前先在状态行看到"将要发生什么"**；
- 异常（检测异常/臂跟随异常/手跟随异常）也实时显示在状态行，便于第一时间发现并停止；
- r1 启停状态文字区分"协同未启动/运行中"。

### 20.5 一键停止与关闭顺序

- 停止路径多样：取消"启用"勾选（`_holistic_stop`）、机械臂面板的"停止"按钮、窗口 ✕（逐级逆序释放）；
- 窗口关闭顺序：`_holistic_stop()` → `arm.close()` → 停相机/断手 → `os._exit(0)`——每级先清自己再交棒父类，资源不泄漏、硬件不残留。

### 20.6 使用流程建议（来自模块 docstring）

```
1. 先手动验证映射：python apps/test_holistic.py --selfcheck（或 test_arm_follow.py）
2. 启动相机（L515 最佳）→ 连接灵巧手 → 连接并上电机械臂
3. 勾选"启用 Holistic 检测"，先观察 r3 状态行
4. 速度比例调低（0.2~0.3）→ 勾选"机械臂跟随"试跑
5. 确认手型（右/左）→ 关掉父类"动作模仿" → 勾选"灵巧手跟随"
6. 随时可：取消勾选停止 / 机械臂面板"停止" / 急停
```

---

## 21. 常见问题（FAQ）

### Q1：勾选"启用 Holistic 检测"报"Holistic 启动失败"

**现象**：弹窗显示 `未找到 holistic 模型文件 holistic_landmarker.task…` 或 `请安装 mediapipe>=0.10.14…`。

**原因与解决**：
- **模型缺失**（最常见）：`HolisticPoseEstimator` 构造时会在 cwd → 项目根 → `lib/` → 本文件目录搜索 `holistic_landmarker.task`，找不到即抛错。解决：从官方下载 URL（`vision/holistic_pose.py` L61–L64 的 `MODEL_DOWNLOAD_URL`，Google 存储桶）下载该文件，放到**项目根目录或 `lib/`**；
- **mediapipe 未装/版本旧**：`pip install mediapipe`（需 ≥0.10.14，Tasks API 需要 1.x，作者验证 mediapipe 1.0.1 可用）；
- 此异常被 `try/except` 兜住，**不会影响主界面**，修好资源后重新勾选即可。

### Q2：勾选"机械臂跟随"后机械臂乱跑/动作吓人

**现象**：机械臂大幅摆动、冲向某个方向、或与预期位置不符。

**原因与解决**：
- **标定参数不对**：offset/scale/add 是现场经验值，默认值只保证"能映射"不保证"映射准"。先**取消跟随**，只看 r3 状态行的"腕3D / 臂TCP"，移动人手观察目标数值是否合理，再用 r2 输入框 + "应用标定"逐步校正（把"人手移到期望位置 → 记录臂目标"的偏差折算进 offset/add）；
- **速度太快**：把机械臂面板的"速度比例"调到 0.2~0.3 再试；
- **误开了跟随**：确认 `机械臂跟随(腕→TCP)` 是否真的是自己勾的——它默认关闭，勾选才动作；
- **画面中人手与机械臂工作区不匹配**：检查人站的位置是否在相机可视范围、深度是否有效（腕3D 数值是否在合理范围，如 z≈0.5~1.5m）。
- 最后防线：`min_xyz/max_xyz` 安全裁剪保证目标 xyz 不越界，但**姿态/标定错误导致的"方向不对"仍需人工标定解决**。

### Q3：勾选"灵巧手跟随"但手不动 / 偶尔动

按四重闸门逐条排查（L221–L222）：
1. **开关没开**：`holistic_hand_follow_var` 是否勾选；
2. **手没检出**：r3 状态行是否显示"手✓"——手要完整露出、光照充足、距离合适（L515 效果最好）；没检出则状态行会显示"未检测到人体/手"或缺少"手✓"；
3. **灵巧手没连接**：`self.hand is None` → 先去父类面板连接手（PCAN/CANII/RS485）；
4. **父类 mimic 还开着**：`mimic_on` 勾选会**屏蔽** Holistic 手跟随（防双重下发）——**去顶部控制栏取消"动作模仿"勾选**。这是最常被忽略的一条。

### Q4：帧率低 / 画面卡顿

**原因**：Holistic 推理（人体+双手一体模型）比单纯手部模型重，且在 **Tk 主线程**里每帧执行（`_poll_video` 30ms 一轮 + `_holistic_step`）。

**缓解**：
- 接受"尽力而为"：`frame_q.get_nowait()` 非阻塞，忙时**丢帧**——卡顿表现为"跟随时有跳变"，但不会死锁；
- 确认走的是 L515（RGB+深度一体），USB 摄像头无深度会导致 `_pose_to_3d` 用相对深度补全，既慢又不准；
- 降低输入分辨率（相机侧配置）、关闭不需要的显示（如父类"显示关节角"）；
- 机械臂跟随与手跟随**按需单独开**，不要无谓同时开。

### Q5：左右手搞反（镜像问题）

**现象**：右手动，灵巧手跟的是左手（或反之）。

**原因**：MediaPipe 的 `left/right_hand` 是**画面中的左右**（相当于照镜子），与你面对摄像头时的真实左右相反；且本文件默认 `hand_side="right"`。

**解决**：在协同面板 r1 直接切换"手: 右/左"单选——**实时生效无需重启**（`_holistic_apply_flags` → `set_hand_side`）。若切换后仍不对，再检查 Holistic 检测器选的是哪只手（状态行"手✓"来自所选手）。

### Q6：协同检测完全没反应 / 状态行一直是"-"

- 确认**先启动相机再勾选"启用"**：`_holistic_toggle` 里 `cam is None` 会被拦截并弹警告；
- 确认 `holistic_running=True`（r1 状态文字应显示"协同运行中"）；
- 确认人在画面里、画面有内容（可先看父类视频区是否有画面）；
- 若 r3 显示"检测异常: …"，把异常原文记下来排查（多为内参/分辨率/模型问题）。

### Q7：关窗后进程还在 / 资源没释放

本文件 `_on_close` 先 `_holistic_stop()` 再 `super()._on_close()`，最终 `os._exit(0)` 强杀——正常不会残留。若异常（如卡在消息框），可手动结束进程；日常关窗请用窗口 ✕ 而不是杀进程。

---

## 22. 方法速查表

| 方法 | 行号 | 触发 | 作用 |
|---|---|---|---|
| `__init__(root)` | L58–L66 | 构造 | super 复用全部 → 建 holistic/follower 状态 → 建面板 → 启心跳 |
| `_build_holistic_ui()` | L71–L126 | `__init__` | 第 5 行协同面板：r1 开关+手型 / r2 标定参数 / r3 状态 |
| `_holistic_toggle()` | L131–L147 | r1 启用勾选 | 检查相机 → 创建检测器 → 置 running；失败复位；取消则 stop |
| `_holistic_stop()` | L149–L157 | 取消勾选 / 关窗 | 释放检测器、running=False、状态复位 |
| `_holistic_apply_flags()` | L159–L164 | r1 各开关/手型 | 同步手型给检测器（含一行无操作死代码） |
| `_holistic_apply_calib()` | L166–L175 | "应用标定"按钮 | 解析 9 个输入框 → `follower.update_calib`；非数字弹错 |
| `_holistic_step()` | L180–L228 | `_poll_video` 每帧 | 检测 → 状态显示 → 臂跟随(block=False) → 手跟随(防双重) |
| `_holistic_poll_loop()` | L230–L237 | `__init__` 启动 | 200ms 常驻心跳，保活 after 链 |
| `_poll_video()` | L242–L262 | Tk after 链 | super 原逻辑 + 追加取帧/协同/骨架覆盖绘制 |
| `_draw_holistic_to_canvas()` | L264–L286 | `_poll_video` | 骨架帧 cover 缩放 + 居中裁剪 + 贴到 video_canvas |
| `_on_close()` | L291–L293 | 窗口 ✕ | `_holistic_stop()` → `super()._on_close()`（最终 os._exit(0)） |
| `main()` | L296–L299 | `__main__` | 建 root、实例化、mainloop |

---

### 附：关键协作模块速查

| 模块 | 路径 | 本文件用到 |
|---|---|---|
| `MainGui` | `gui/main_gui.py` | 祖父类：cam/frame_q/hand/checkbox_vars/video_canvas/_poll_video/_on_close/mimic |
| `MainGuiArm` | `gui/main_gui_arm.py` | 父类：arm/arm_connected/速度比例/机械臂面板 |
| `HolisticPoseEstimator` | `vision/holistic_pose.py` | `process()` 检测+解算+映射；`draw_skeleton()` 画骨架；`set_hand_side()`；`close()` |
| `ArmFollower` | `arm/arm_follow.py` | `map_wrist_to_arm_pose()` 腕→TCP；`update_calib()`；`DEFAULT_CALIB` 初值 |
| `AuboK5ArmController` | `arm/arm_controller.py` | `movel(pose, block=False)` 非阻塞下发 |
| `RYH1HandController` | `hand/hand_controller.py` | `move_joints(rad)` 16 关节直发 |

> 注：本文档行号基于撰写时的源码版本（`main_gui_holistic.py` 共 303 行）；后续代码若有修改，以最新源码为准。
