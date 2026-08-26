# 13 · `gui/main_gui_arm.py` 代码详解

> 本文档对应源文件：`RY-H1_vision_mimic/gui/main_gui_arm.py`（共 365 行）
> 入口方式：`python -m gui.main_gui_arm`（在 `RY-H1_vision_mimic` 目录下执行）
>
> 本文件是「睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂视觉动作模仿系统（Windows 版）」的**扩展版综合控制界面**：它在不修改原 `gui/main_gui.py` 的前提下，通过**继承**完整复用灵巧手侧全部功能（相机 / MediaPipe 姿态 / 精度后处理 / 16 关节控制），并在窗口底部**新增第 4 行"Aubo K5 机械臂控制"面板**，实现机械臂的连接、上电、运动控制、TCP 坐标联动与"臂手联动"（机械臂到位后自动做手部动作）。

---

## 目录

1. [文件职责总览](#1-文件职责总览)
2. [ASCII 架构图（一）：MainGuiArm 界面整体布局](#2-ascii-架构图一mainguiarm-界面整体布局)
3. [ASCII 架构图（二）：臂手联动数据流](#3-ascii-架构图二臂手联动数据流)
4. [模块头部：导入与路径引导（L24–L46）](#4-模块头部导入与路径引导l24l46)
5. [类 `MainGuiArm` 总览与 `__init__`（L49–L60）](#5-类-mainguiarm-总览与-initl49l60)
6. [`_build_arm_ui`：机械臂面板完整布局（L65–L136）](#6-_build_arm_ui机械臂面板完整布局l65l136)
7. [`_require_arm`：统一守卫（L141–L145）](#7-_require_arm统一守卫l141l145)
8. [连接与断开：`_arm_connect` / `_arm_disconnect`（L147–L178）](#8-连接与断开_arm_connect--_arm_disconnectl147l178)
9. [速度比例实时下发：`_arm_apply_fraction`（L180–L185）](#9-速度比例实时下发_arm_apply_fractionl180l185)
10. [电源与动作：上电 / 断电 / 停止 / 拖拽示教 / 回初始位（L187–L230）](#10-电源与动作上电--断电--停止--拖拽示教--回初始位l187l230)
11. [关节滑条执行 movej（L232–L238）](#11-关节滑条执行-movejl232l238)
12. [位姿输入执行 movel（L240–L250）](#12-位姿输入执行-movell240l250)
13. [TCP 坐标联动：`_arm_toggle_link`（L252–L269）](#13-tcp-坐标联动_arm_toggle_linkl252l269)
14. [臂手联动：`_arm_hand_link` 与三个包装按钮（L271–L307）](#14-臂手联动_arm_hand_link-与三个包装按钮l271l307)
15. [状态刷新：`_arm_refresh_state`（L312–L329）](#15-状态刷新_arm_refresh_statel312l329)
16. [常驻轮询：`_arm_poll_loop`——为什么用 `after(800)` 而非线程（L331–L338）](#16-常驻轮询_arm_poll_loop为什么用-after800-而非线程l331l338)
17. [关闭流程：`_on_close` 覆写（L343–L350）](#17-关闭流程_on_close-覆写l343l350)
18. [工具函数与入口：`logger_warn` / `main`（L353–L365）](#18-工具函数与入口logger_warn--mainl353l365)
19. [与 `main_gui.py` 的差异对比表](#19-与-maingui-py-的差异对比表)
20. [安全设计](#20-安全设计)
21. [常见问题（FAQ）](#21-常见问题faq)
22. [方法速查表](#22-方法速查表)

---

## 1. 文件职责总览

`main_gui_arm.py` 的架构核心是一个词：**继承扩展，零侵入**。

| 层 | 内容 | 来源 |
|---|---|---|
| **复用层** | 相机(USB/L515)、MediaPipe 姿态、精度后处理、灵巧手连接/校准/动作模仿/16 关节滑条、原界面 0~3 行布局 | `class MainGuiArm(MainGui)`，`super().__init__()` 全盘继承 |
| **新增层** | 底部第 4 行"Aubo K5 机械臂控制"面板（连接/电源/关节滑条/位姿/TCP 联动/臂手联动） | 本文件 `_build_arm_ui()` |
| **新增调度** | 每 800ms 常驻刷新机械臂状态 | 本文件 `_arm_poll_loop()` |
| **新增收尾** | 关窗前先断开机械臂，再走原关闭流程 | 本文件覆写 `_on_close()` |

数据流一句话概括：

```
GUI 输入(滑条/位姿框/勾选) ──► AuboK5ArmController ──► 机械臂 SDK ──► 机械臂运动
                                                            │
GUI 状态区 ◄── _arm_poll_loop(800ms) ◄── get_state_summary() ─┘
```

本文件**不实现任何机械臂底层通信**（那在 `arm/arm_controller.py`），它只负责：创建控制器、把面板输入翻译成控制器调用、把控制器返回的状态翻译成人话显示。

---

## 2. ASCII 架构图（一）：MainGuiArm 界面整体布局

```
┌─────────────────────────────── 主窗口 (tk.Tk root) ────────────────────────────────────────────┐
│                                                                                                │
│  row 0  ┌────────────────────────────────────────────────────────────────────────────────┐      │
│         │ 顶部控制栏（原 MainGui._build_ui）：相机选择/启动/停止、姿态、后处理参数、灵巧手    │      │
│         │ 连接方式(PCAN/CANII/RS485)、左右手选择、连接/断开/校准/回零/预设手型/动作模仿开关   │      │
│         └────────────────────────────────────────────────────────────────────────────────┘      │
│  row 1  ┌────────────────────────────────────────────────────────────────────────────────┐      │
│         │ 中部：视频显示区（相机帧 + MediaPipe 骨骼叠加） + 参数区（后处理参数滑条）         │      │
│         └────────────────────────────────────────────────────────────────────────────────┘      │
│  row 2  ┌────────────────────────────────────────────────────────────────────────────────┐      │
│         │ 中部/下部：16 关节滑条区（灵巧手 16 关节角度，J1~J16）                            │      │
│         └────────────────────────────────────────────────────────────────────────────────┘      │
│  row 3  ┌────────────────────────────────────────────────────────────────────────────────┐      │
│         │ 原状态栏 / 原界面其余控件（super().__init__ 已建好，本文件不动）                    │      │
│         └────────────────────────────────────────────────────────────────────────────────┘      │
│  row 4  ┌─────────────────────────── LabelFrame: Aubo K5 机械臂控制（TCP 坐标联动）──────────┐   │
│         │                                                                                  │   │
│  r1     │ [IP:____][端口:___][连接][断开] 速度比例: [───●─────]  (机械臂状态: 已连接/未连接) │   │
│  r2     │ [上电+启动][断电][停止][拖拽示教(开)][拖拽示教(关)][回初始位]                        │   │
│  r3     │ [J1滑条][J2滑条][J3滑条][J4滑条][J5滑条][J6滑条] [执行 movej] (状态: 模式/安全/…)  │   │
│  r4     │ movel位姿 [x][y][z][rx][ry][rz] [执行 movel]  ☑TCP联动 [臂手联动:到位后握拳/张开/放松]│   │
│         └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                │
│  说明：row 0~3 由 super().__init__() 构建（继承自 MainGui，代码不变）；                           │
│        row 4 由本文件 _build_arm_ui() 追加，且 root.grid_rowconfigure(4, weight=0) 不拉伸。       │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

要点：
- **第 4 行是"贴"在原界面下面的**，原界面行号 0~3 一个都不动，所以原文件零修改；
- 面板内部又用 4 个水平子行（r1~r4）组织，r1=连接+速度、r2=电源/动作、r3=6 轴关节、r4=位姿+联动；
- r3 的 6 个滑条标签直接复用 `JOINT_NAMES_CN`（J1~J6 中文名）。

---

## 3. ASCII 架构图（二）：臂手联动数据流

"臂手联动"是本文件最有特色的功能：一次点击 = 机械臂先 movel 到位 + 灵巧手再执行手势。数据流如下（以"到位后握拳"为例）：

```
用户点击 [臂手联动:到位后握拳]
        │
        ▼
_arm_hand_link("握拳")                              （L271）
  1. _require_arm()  → 未连接则弹窗拦截
  2. self.hand is None? → 未连灵巧手则弹窗拦截        （L275-277）
  3. 解析 6 个位姿输入框 → [x,y,z,rx,ry,rz]           （L279-282，非数字弹错）
  4. askyesno 确认弹窗（"机械臂 movel 到位后执行『握拳』"） （L283）
        │
        ▼
  self.arm.movel(pose, block=True, timeout_s=30)     （L285）  ──► AuboK5ArmController.movel
        │                                                   ──► SDK moveLineP(位姿, 速度, 加速度, 过渡半径)
        │                                                       （若 TCP 联动已开，位姿基准=灵巧手 TCP）
        ▼
  ret != 0 ? ──是──► 弹窗"机械臂运动失败"，流程终止        （L286-288）
        │否
        ▼
  hand_action == "握拳" ? ──► self.hand.close_hand()    （L291）  ──► 灵巧手 16 指全部握紧
       │ "张开"            ──► self.hand.open_hand()     （L293）  ──► 灵巧手全部张开
       │ 其他("放松")       ──► self.hand.relax()         （L295）  ──► 灵巧手放松(断电保持)
        │
        ▼
  arm_state_var 显示 "臂手联动完成（到位+握拳）"            （L296）
```

设计要点：
- **严格串行**：movel 用 `block=True` 等机械臂**真正到位**后才发手部指令，杜绝"臂没到位手先动"的时序错乱；
- **失败即止**：movel 返回非 0 直接中断，不会在手没就位的情况下乱抓手势；
- **复用现有手部 API**：三个动作直接调 `RYH1HandController` 已有的 `close_hand / open_hand / relax`（与主界面"预设手型"按钮同一套实现，行为一致）。

---

## 4. 模块头部：导入与路径引导（L24–L46）

```python
L24  from __future__ import annotations
L25
L26  import os
L27  import sys
L28
L29  # ---- 路径引导（必须最先执行） ----
L30  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L31  os.chdir(sys.path[0])
L32  try:
L33      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L34      sys.stderr.reconfigure(encoding="utf-8", errors="replace")
L35  except Exception:
L36      pass
L37
L38  import math
L39  import threading
L40  import time
L41  import tkinter as tk
L42  from tkinter import ttk, messagebox
L43
L44  from gui.main_gui import MainGui, JOINT_NAMES_CN
L45  from arm import AuboK5ArmController
L46  from arm.arm_config import ARM_CONFIG, DOF
```

- **L24**：`from __future__ import annotations`——把类型注解变成字符串延迟求值，允许 `self.arm: AuboK5ArmController | None = None` 这种"联合类型写法"在旧版 Python 也能跑，且避免运行时计算注解。
- **L30–L31 路径引导（关键）**：
  - `os.path.abspath(__file__)` 得到本文件绝对路径，`dirname` 两次 = 项目根目录 `RY-H1_vision_mimic/`；
  - `sys.path.insert(0, ...)` 把项目根插到模块搜索路径最前面，这样无论从哪里启动，`import gui.main_gui`、`import arm` 都能命中本项目包；
  - `os.chdir(sys.path[0])` 把**当前工作目录**切到项目根——保证后续相对路径（相机配置、模型文件、日志目录等）全部以项目根为基准。这一行必须放在任何"依赖 cwd 的代码"之前。
- **L32–L36**：Windows 控制台默认 GBK 编码，强制把 stdout/stderr 重配成 UTF-8（`errors="replace"` 防止个别字符解码崩溃）；失败就静默跳过（例如在无控制台的 GUI 环境下）。
- **L38–L42**：标准库导入。`math`（度→弧度转换）、`threading`/`time`（备用，本文件主要用 Tk 定时器）、`tkinter`/`ttk`/`messagebox`（界面与弹窗）。
- **L44**：`from gui.main_gui import MainGui, JOINT_NAMES_CN`——**继承的父类**从这里来；`JOINT_NAMES_CN` 是原界面 16 关节名，这里再导入用于第 3 行 6 个机械臂关节滑条标签（注意：原 `main_gui.py` 的 `JOINT_NAMES_CN` 来自 `hand` 模块的灵巧手关节名，而机械臂关节名在 `arm/arm_config.py`——两个 `JOINT_NAMES_CN` 是**不同集合**，这里复用父类导出的名字只用于一致性展示，机械臂 6 轴标签实际用的是 `arm/__init__.py` 导出的那份，见下）。
- **L45**：`from arm import AuboK5ArmController`——机械臂控制器的门面类（`arm/__init__.py` 再导出），所有机械臂操作都通过它。
- **L46**：`from arm.arm_config import ARM_CONFIG, DOF`——配置单点：面板默认 IP/端口/速度比例、6 个滑条的循环次数都取自这里。

> 🔑 注意 `import math` 在 `sys.path` 引导**之后**才出现——路径引导必须在任何项目内 import 之前执行，这是 L29 注释"必须最先执行"的含义。

---

## 5. 类 `MainGuiArm` 总览与 `__init__`（L49–L60）

```python
L49  class MainGuiArm(MainGui):
L50      """扩展版主界面：灵巧手（继承 MainGui）+ Aubo K5 机械臂。"""
L51
L52      def __init__(self, root: tk.Tk):
L53          # 先构建原灵巧手界面（相机/姿态/后处理/手控/布局）
L54          super().__init__(root)
L55          # 机械臂相关状态
L56          self.arm: AuboK5ArmController | None = None
L57          self.arm_connected = False
L58          self.arm_state_var = tk.StringVar(value="机械臂未连接")
L59          self._build_arm_ui()
L60          self._arm_poll_loop()
```

**继承关系**：`MainGuiArm` 是 `MainGui` 的直接子类。`MainGui`（`gui/main_gui.py` L143）已经包含：相机采集线程、姿态估计、后处理、灵巧手控制器（`self.hand`）、全部 UI 构建（`_build_ui`）、动作模仿、关闭流程等。子类**只做加法，不做减法**。

`__init__` 四步走：

| 步骤 | 代码 | 作用 |
|---|---|---|
| ① 先建原界面 | `super().__init__(root)` (L54) | 完整执行父类构造：构建 0~3 行全部控件、初始化 `self.hand`、启动相机线程、注册关闭回调等。**必须最先执行**，因为后面新增的机械臂面板要"挂"在已经存在的 root 布局上 |
| ② 初始化机械臂状态 | L56–L58 | `self.arm=None`（控制器对象，未创建）、`self.arm_connected=False`（连接标志）、`arm_state_var="机械臂未连接"`（顶部状态文字，蓝色标签绑定） |
| ③ 搭机械臂面板 | `self._build_arm_ui()` (L59) | 见下一节，把第 4 行面板及其全部控件、变量、回调建好 |
| ④ 启动轮询 | `self._arm_poll_loop()` (L60) | 注册第一个 `after(800)` 定时器，从此每 800ms 刷新机械臂状态，直到关窗 |

两个状态对象的分工：
- `self.arm`：**真正的控制器实例**（与机械臂的 TCP 连接、所有 SDK 调用的门面）。未连接时为 `None`。
- `self.arm_connected`：布尔标志，标记"是否已成功连接"。之所以要单独一个标志，是因为连接成功与否不能只靠 `arm is not None` 判断（连接失败时代码也会先把 `arm=None` 清理，见 L159/L166），标志更明确。
- `arm_state_var`：给 r1 行蓝色标签绑定的字符串变量，显示"机械臂未连接 / 已连接(IP) / 上电成功 / 运动 ret=..."等**人话状态**。

---

## 6. `_build_arm_ui`：机械臂面板完整布局（L65–L136）

```python
L65  def _build_arm_ui(self):
L66      root = self.root
L67      # 机械臂面板占第 4 行（原界面 0~3 行不动）
L68      root.grid_rowconfigure(4, weight=0)
L69      frame = ttk.LabelFrame(root, text="Aubo K5 机械臂控制（TCP 坐标联动）")
L70      frame.grid(row=4, column=0, sticky="ew", padx=5, pady=2)
```

- **L68**：`grid_rowconfigure(4, weight=0)` 声明第 4 行的拉伸权重为 0——窗口缩放时机械臂面板**不跟着变高**，保持紧凑（原界面 0~3 行的权重是父类设的，这里不动）。
- **L69–L70**：面板主体是一个带标题框的 `ttk.LabelFrame`，标题"**Aubo K5 机械臂控制（TCP 坐标联动）**"点明两大主题：机械臂控制 + TCP 联动。`sticky="ew"` 让面板横向铺满、纵向不拉伸。

### 行 1（L73–L88）：连接 + 速度

```
r1: [IP: 192.168.1.200][端口: 30004][连接][断开]  速度比例: [====●====] 0.3   (机械臂未连接/已连接…)
```

| 控件 | 绑定变量/命令 | 说明 |
|---|---|---|
| `ttk.Label "IP:"` + `Entry` | `self.arm_ip_var`（默认 `ARM_CONFIG["ip"]`） | IP 输入框，宽度 14 |
| `ttk.Label "端口:"` + `Entry` | `self.arm_port_var`（默认 `str(ARM_CONFIG["rpc_port"])`） | 端口输入框，宽度 6 |
| `Button "连接"` | `command=self._arm_connect` | 建控制器并连机械臂 |
| `Button "断开"` | `command=self._arm_disconnect` | 关连接、清状态 |
| `tk.Scale 速度比例` | `self.arm_fraction_var`（默认 `ARM_CONFIG["speed_fraction"]`=0.3），`from_=0.05, to=1.0, resolution=0.05`，`command=lambda _v: self._arm_apply_fraction()` | 水平滑条，**拖动松手即实时下发**速度比例；范围 5%~100%，步进 5%（与 `arm_config` 的 max/min_speed_fraction 一致） |
| `Label`（蓝色） | `textvariable=self.arm_state_var` | 机械臂连接/运行状态的人话显示 |

### 行 2（L91–L98）：电源与动作

```
r2: [上电+启动][断电][停止][拖拽示教(开)][拖拽示教(关)][回初始位]
```

| 按钮 | 命令 | 语义 |
|---|---|---|
| 上电+启动 | `self._arm_poweron` | 上电并松刹车，等机械臂进入 Running |
| 断电 | `self._arm_poweroff` | 下电 |
| 停止 | `self._arm_stop` | 立即停止当前运动 |
| 拖拽示教(开) | `lambda: self._arm_freedrive(True)` | 进入拖拽示教模式（可手推机械臂） |
| 拖拽示教(关) | `lambda: self._arm_freedrive(False)` | 退出拖拽示教 |
| 回初始位 | `self._arm_home` | 回到初始关节角 |

用 `lambda` 包一层是为了把 `True/False` 参数塞进 `command`（Tk 的 command 回调不接受参数）。

### 行 3（L100–L116）：6 轴关节滑条 + movej 执行 + 状态区

```
r3: [J1基座旋转][J2肩部][J3肘部][J4前臂旋转][J5腕部俯仰][J6腕部旋转]  [执行 movej]  (状态: 模式:… 安全:… 停止 J(deg): … TCP: …)
```

- **L103–L112 循环生成 6 个滑条**：`for i in range(DOF)`（DOF=6 来自 `arm_config`）。每个关节一列（`ttk.Frame`），包含：
  - 顶部标签：`JOINT_NAMES_CN[i]`（如"基座旋转(J1)"），小字号字体；
  - `tk.Scale`：`from_=-175, to=175, resolution=1`（**单位：度**，范围与 `JOINT_RANGE_DEG` 保守值一致），不显示数值（`showvalue=False`）；
  - 底部数值标签：绑定同一个 `var`，实时显示当前角度值。
  - 每个 `var`（`tk.DoubleVar`）存入 `self.arm_joint_vars` 列表，供"执行 movej"读取。
- **L113**：`Button "执行 movej"` → `self._arm_movej_from_sliders`：把 6 个滑条当前角度（度）转弧度后下发关节运动。
- **L114–L116**：`self.arm_status_var`（默认"状态: -"），等宽字体绿色标签，显示轮询得到的详细状态（模式/安全/停止/关节角/TCP 位姿）。

### 行 4（L119–L136）：movel 位姿输入 + TCP 联动 + 臂手联动

```
r4: movel位姿 [x][y][z][rx][ry][rz] [执行 movel]  ☐TCP联动(灵巧手安装偏移) [到位后握拳][到位后张开][到位后放松]
```

- **L121–L127**：6 个 `Entry`（默认 `"0.0"`）对应 `[x,y,z,rx,ry,rz]`，单位 **米/弧度**；每个 Entry 绑定一个 `StringVar` 存入 `self.arm_pose_vars`；`Button "执行 movel"` → `_arm_movel_from_entry`。
- **L130–L133 TCP 联动**：`self.arm_link_var = tk.BooleanVar(False)` + `ttk.Checkbutton "TCP联动(灵巧手安装偏移)"`，勾选变化触发 `_arm_toggle_link`——把灵巧手安装偏移写入机械臂 `setTcpOffset`（详见 §13）。
- **L134–L136 臂手联动三按钮**：`到位后握拳`→`_arm_hand_link_fist`、`到位后张开`→`_arm_hand_link_open`、`到位后放松`→`_arm_hand_link_relax`，三者都汇聚到统一的 `_arm_hand_link(动作名)`（详见 §14）。

---

## 7. `_require_arm`：统一守卫（L141–L145）

```python
L141  def _require_arm(self) -> bool:
L142      if self.arm is None or not self.arm_connected:
L143          messagebox.showwarning("提示", "请先连接机械臂")
L144          return False
L145      return True
```

- **作用**：几乎所有机械臂操作（上电/断电/停止/示教/回初始/movej/movel/臂手联动）的第一步都是"检查是否已连接"。
- **写法**：`self.arm is None or not self.arm_connected` 双重判断——对象不存在（没建过/已清理）或标志为假（连接失败）都算未连接。
- **失败时**：弹出黄色警告框"请先连接机械臂"，返回 `False`；调用方 `if not self._require_arm(): return` 直接短路返回。
- **为什么用统一函数**：避免每个方法各写一套判断；将来要加"连接状态更细粒度"的判断（比如还要求已上电）只需改这一处。

---

## 8. 连接与断开：`_arm_connect` / `_arm_disconnect`（L147–L178）

### `_arm_connect`（L147–L167）

```python
L147  def _arm_connect(self):
L148      if self.arm is not None:
L149          self._arm_disconnect()
L150      ip = self.arm_ip_var.get().strip() or ARM_CONFIG["ip"]
L151      try:
L152          port = int(self.arm_port_var.get().strip() or ARM_CONFIG["rpc_port"])
L153      except ValueError:
L154          port = ARM_CONFIG["rpc_port"]
L155      try:
L156          self.arm = AuboK5ArmController(ip=ip, rpc_port=port,
L157                                         speed_fraction=self.arm_fraction_var.get())
L158          if not self.arm.open():
L159              self.arm = None
L160              messagebox.showerror("机械臂连接失败", "连接/登录失败，检查 IP、网络、控制柜开机、账号密码")
L161              return
L162          self.arm_connected = True
L163          self.arm_state_var.set(f"已连接({ip})")
L164          self._arm_refresh_state()
L165      except Exception as exc:
L166          self.arm = None
L167          messagebox.showerror("机械臂连接失败", str(exc))
```

逐段解释：

| 行 | 逻辑 | 说明 |
|---|---|---|
| L148–L149 | **重连前先断开** | 若已存在控制器（比如换 IP 重连），先走一遍 `_arm_disconnect` 清理旧连接，避免 TCP 句柄泄漏 |
| L150 | **取 IP** | 从输入框取，`strip()` 去空格；空字符串回退到配置默认值 `ARM_CONFIG["ip"]` |
| L151–L154 | **取端口** | 转 `int`；`ValueError`（输入非数字或为空）时静默回退默认端口 30004——容错但不打扰用户 |
| L156–L157 | **创建控制器** | 把面板上的 IP/端口/**当前速度比例滑条值**传进构造函数（`arm_controller` 内部默认也读 `ARM_CONFIG`，但这里显式传，保证滑条上的实时比例生效） |
| L158–L161 | **open() 失败分支** | `open()` 返回 False（连不上/登录失败）：清掉 `self.arm`，弹红色错误框给出排查提示 |
| L162–L164 | **成功分支** | 置 `arm_connected=True`；状态文字显示"已连接(IP)"；立刻刷一次状态（不等 800ms 轮询） |
| L165–L167 | **异常兜底** | 构造函数或 open 抛异常（如网络异常对象）：同样清 `self.arm` 并弹错，保证任何失败路径都不会留下"半连接"状态 |

**设计要点**：所有失败路径都做 `self.arm = None` 清理 + 弹窗，保证"连接失败后界面仍处于干净的可重试状态"。

### `_arm_disconnect`（L169–L178）

```python
L169  def _arm_disconnect(self):
L170      if self.arm is not None:
L171          try:
L172              self.arm.close()
L173          except Exception:
L174              pass
L175      self.arm = None
L176      self.arm_connected = False
L177      self.arm_state_var.set("机械臂未连接")
L178      self.arm_status_var.set("状态: -")
```

- L170–L174：有控制器就调 `close()`（内部会注销 RTDE、关 TCP）；**异常吞掉**——断开是"尽力而为"的操作，网络已经断了也要能正常继续清理。
- L175–L178：无论成败，统一复位四个状态：控制器置 None、连接标志置 False、顶部状态字"机械臂未连接"、状态区"状态: -"。**幂等**：重复点"断开"也安全。

---

## 9. 速度比例实时下发：`_arm_apply_fraction`（L180–L185）

```python
L180  def _arm_apply_fraction(self):
L181      if self.arm_connected and self.arm is not None:
L182          try:
L183              self.arm.set_speed_fraction(self.arm_fraction_var.get())
L184          except Exception as exc:
L185              logger_warn(f"set speed fraction: {exc}")
```

- **触发时机**：r1 行滑条**每动一格**（`command` 回调，松手/拖动过程中都会触发）。
- **逻辑**：只在已连接时下发 `set_speed_fraction`；未连接时静默跳过（滑条先调好，连接时 L157 会把这个值带进构造函数）。
- **异常处理**：失败只记 warning 日志，不弹窗——速度调节属于高频低危操作，弹窗会打断操作。
- **设计意图**：**"调速度不需要断开重连"**——运动中、上电前都能实时改速度比例，这是安全演示的关键手段（发现太快立刻拉低）。

---

## 10. 电源与动作：上电 / 断电 / 停止 / 拖拽示教 / 回初始位（L187–L230）

五个方法结构高度一致：`_require_arm()` 守卫 → （危险操作）确认弹窗 → 调控制器 → 更新状态字。逐一说明：

### `_arm_poweron`（L187–L196）
```python
L187  def _arm_poweron(self):
L188      if not self._require_arm():
L189          return
L190      if not messagebox.askyesno("上电+启动", "确定对机械臂上电并松刹车？"):
L191          return
L192      try:
L193          ok = self.arm.poweron_and_startup(wait_running=True, timeout_s=15)
L194          self.arm_state_var.set("上电+启动成功(Running)" if ok else "上电/启动未达 Running")
L195      except Exception as exc:
L196          messagebox.showerror("上电失败", str(exc))
```
- 确认弹窗文案明确告知后果（"上电并松刹车"——松刹车后臂会失去保持力，可能下垂/坠落）；
- `poweron_and_startup(wait_running=True, timeout_s=15)`：阻塞等最多 15 秒直到机械臂进入 Running 状态，返回布尔；
- 结果写入状态字；异常弹错。

### `_arm_poweroff`（L198–L207）
- 确认弹窗"确定对机械臂断电？"后调 `poweroff()`；成功显示"已请求断电"。
- **注意**：断电前应确认机械臂已停止运动且无人靠近。

### `_arm_stop`（L209–L213）
- **无确认弹窗**（停止是安全操作，越快越好）；`self.arm.stop_move()` 立即停止当前运动；状态字"已发送停止"。
- 语义上是"急停级"的软停止，运动指令（movej/movel）未结束时按下即打断。

### `_arm_freedrive(enable)`（L215–L222）
- 带参版本，由 r2 行两个按钮分别以 `True/False` 调用；
- `self.arm.freedrive(enable)` 进入/退出拖拽示教模式；
- 状态字显示"拖拽示教: 开/关"；异常弹"示教失败"。
- **使用场景**：人工把机械臂掰到某个姿态（配合关节滑条回读当前角度），是示教式编程的入口。

### `_arm_home`（L224–L230）
```python
L224  def _arm_home(self):
L225      if not self._require_arm():
L226          return
L227      if not messagebox.askyesno("回初始位", "机械臂将回到初始关节角，确认？"):
L228          return
L229      ret, msg = self.arm.move_home(block=True)
L230      self.arm_state_var.set(f"回初始位 ret={ret} {msg or ''}")
```
- 确认弹窗（回初始位也是一次大范围运动，需确认周围无障碍）；
- `move_home(block=True)` 阻塞直到回到初始位，返回 `(ret, msg)` 二元组；
- 状态字直接显示 `ret` 与消息——**把控制器的返回原样暴露给用户**，便于排障。

---

## 11. 关节滑条执行 movej（L232–L238）

```python
L232  def _arm_movej_from_sliders(self):
L233      if not self._require_arm():
L234          return
L235      q = [math.radians(v.get()) for v in self.arm_joint_vars]
L236      ret, msg = self.arm.movej(q, block=True, timeout_s=30)
L237      self.arm_state_var.set(f"movej ret={ret} {msg or ''}")
L238      self._arm_refresh_state()
```

| 行 | 说明 |
|---|---|
| L235 | **度→弧度**：滑条单位是度（给人看），SDK 要弧度（机械臂用），`math.radians` 逐个转换，得到 6 元列表 `q` |
| L236 | `movej(q, block=True, timeout_s=30)`：关节空间运动，**阻塞等待到位**，最多等 30 秒；超时/失败返回非 0 `ret` |
| L237 | 状态字显示返回值与消息（如 `ret=0` 成功） |
| L238 | 运动完立刻刷新一次详细状态（关节角/TCP 位姿都会变），不必等下一次 800ms 轮询 |

**设计要点**：`block=True` 保证"点执行 → 动完 → 刷新"，语义上是同步的，避免用户连续点按钮造成指令堆叠。

---

## 12. 位姿输入执行 movel（L240–L250）

```python
L240  def _arm_movel_from_entry(self):
L241      if not self._require_arm():
L242          return
L243      try:
L244          pose = [float(v.get()) for v in self.arm_pose_vars]
L245      except ValueError:
L246          messagebox.showerror("输入错误", "位姿必须是数字 [x,y,z,rx,ry,rz]")
L247          return
L248      ret, msg = self.arm.movel(pose, block=True, timeout_s=30)
L249      self.arm_state_var.set(f"movel ret={ret} {msg or ''}")
L250      self._arm_refresh_state()
```

- **L243–L247**：把 6 个字符串输入框转成 `float`；任何一个不是数字就弹"输入错误"并**直接返回**——数值校验放在调用 SDK 之前，防止把垃圾数据发给机械臂。
- **L248**：`movel(pose, block=True, timeout_s=30)`——笛卡尔空间直线运动到 `[x,y,z,rx,ry,rz]`（米/弧度）。
- **坐标系语义**（关键）：这里的位姿是**当前 TCP 坐标系**下的目标。若 TCP 联动已开启（§13），TCP 已被设为"灵巧手 TCP"，那么输入的位姿直接是**灵巧手手指尖**要到的位置——这就是"TCP 坐标联动"名字的由来。
- **L249–L250**：同 movej，显示 ret 并立即刷新状态。

---

## 13. TCP 坐标联动：`_arm_toggle_link`（L252–L269）

```python
L252  def _arm_toggle_link(self):
L253      """TCP 坐标联动：勾选后把灵巧手安装偏移写入机械臂 setTcpOffset。"""
L254      if not self.arm_connected or self.arm is None:
L255          self.arm_link_var.set(False)
L256          messagebox.showwarning("提示", "请先连接机械臂")
L257          return
L258      try:
L259          if self.arm_link_var.get():
L260              off = self.arm.get_hand_mount_offset()
L261              if off is None:
L262                  off = ARM_CONFIG["hand_mount_offset"]
L263              self.arm.apply_tcp_offset(off)
L264              self.arm_state_var.set("TCP 联动已开启（位姿=灵巧手 TCP）")
L265          else:
L266              self.arm.apply_tcp_offset([0.0] * 6)   # 关联动 = 基础 TCP
L267              self.arm_state_var.set("TCP 联动已关闭（位姿=法兰 TCP）")
L268      except Exception as exc:
L269          messagebox.showerror("TCP 联动失败", str(exc))
```

**这个勾选框在做什么**：机械臂 SDK 的 `setTcpOffset` 决定"moveLine/moveCircle 的位姿以哪个点为基准"。勾选 = 把**灵巧手安装偏移**（`arm_config.py` 的 `hand_mount_offset`，如 `[0,0,0.15,π,0,0]`）叠加进 TCP；取消 = 写全 0，回到法兰盘基准。

逐段逻辑：

| 行 | 逻辑 | 说明 |
|---|---|---|
| L254–L257 | **未连接拦截** | 未连接时勾选无效，并**把勾选框强制弹回 False**（`set(False)`），同时警告"请先连接机械臂"——防止用户以为已经生效 |
| L259–L264 | **开启分支** | 优先用控制器里已存的安装偏移（`get_hand_mount_offset()`，连接时/此前设置过则非 None）；控制器没存过就回退到配置默认 `ARM_CONFIG["hand_mount_offset"]`；然后 `apply_tcp_offset(off)` 写入机械臂；状态字提示"位姿=灵巧手 TCP" |
| L265–L267 | **关闭分支** | `apply_tcp_offset([0.0]*6)`——**注意**：这里传的是全 0，控制器内部逻辑是"基础偏移 + 传入偏移"，全 0 意味着最终 TCP = 基础 `tcp_offset`（默认也是 0）= 法兰 TCP；状态字提示"位姿=法兰 TCP" |
| L268–L269 | **异常兜底** | 写入失败弹"TCP 联动失败" |

**设计意图**：
1. **把"坐标系切换"做成一个可视化开关**，而不是让用户去改配置文件——勾一下，movel 的坐标系就在"法兰"与"灵巧手"之间切换，直观且可逆；
2. **联动与运动解耦**：TCP 联动只管"坐标系基准"，臂手联动（§14）管"运动完做手势"，两者可独立开关，组合出四种行为模式；
3. 联动开启后，配合 `hand_mount_offset`，用户可以"看着灵巧手手指尖编程"，而不是心算法兰偏移。

---

## 14. 臂手联动：`_arm_hand_link` 与三个包装按钮（L271–L307）

```python
L271  def _arm_hand_link(self, hand_action: str):
L272      """臂手联动：先机械臂 movel 到面板输入的位姿，再执行灵巧手动作。"""
L273      if not self._require_arm():
L274          return
L275      if self.hand is None:
L276          messagebox.showwarning("提示", "请先连接灵巧手")
L277          return
L278      try:
L279          pose = [float(v.get()) for v in self.arm_pose_vars]
L280      except ValueError:
L281          messagebox.showerror("输入错误", "位姿必须是数字")
L282          return
L283      if not messagebox.askyesno("臂手联动", f"机械臂 movel 到位后执行『{hand_action}』，确认？"):
L284          return
L285      ret, msg = self.arm.movel(pose, block=True, timeout_s=30)
L286      if ret != 0:
L287          messagebox.showerror("机械臂运动失败", f"movel ret={ret} {msg}")
L288          return
L289      try:
L290          if hand_action == "握拳":
L291              self.hand.close_hand()
L292          elif hand_action == "张开":
L293              self.hand.open_hand()
L294          else:
L295              self.hand.relax()
L296          self.arm_state_var.set(f"臂手联动完成（到位+{hand_action}）")
L297      except Exception as exc:
L298          messagebox.showerror("灵巧手动作失败", str(exc))
```

**五道关卡（按顺序）**：

| 关卡 | 行 | 作用 |
|---|---|---|
| ① 机械臂已连 | L273–L274 | `_require_arm()`，未连弹"请先连接机械臂" |
| ② 灵巧手已连 | L275–L277 | `self.hand is None` 检查——**联动是"臂+手"两个设备的事，手没连就白跑** |
| ③ 位姿数字校验 | L278–L282 | 6 个输入框转 float，非数字弹错返回 |
| ④ 用户确认 | L283–L284 | 弹窗明示"机械臂 movel 到位后执行『握拳』"——这是一次会**真实移动机械臂**的操作，必须确认 |
| ⑤ movel 结果校验 | L285–L288 | **movel 成功（ret==0）才继续**；失败弹"机械臂运动失败"并终止，绝不会在未到位时做手势 |

**手部动作分发**（L289–L296）：按 `hand_action` 字符串分发——`"握拳"→close_hand()`（全部握紧）、`"张开"→open_hand()`（全部张开）、**其他任意值（"放松"）→`relax()`**（放松/断电保持）。用 `else` 兜底而非第三个 `elif`，代码更稳。完成后状态字"臂手联动完成（到位+握拳）"。

**三个包装按钮**（L300–L307）：
```python
L300  def _arm_hand_link_fist(self):   self._arm_hand_link("握拳")
L303  def _arm_hand_link_open(self):   self._arm_hand_link("张开")
L306  def _arm_hand_link_relax(self):  self._arm_hand_link("放松")
```
Tk 按钮 `command` 不能传参，所以用三个零参包装函数把动作名传给统一实现——与 r2 行拖拽示教两个按钮用 `lambda` 是同一思路（这里拆成命名函数更可读）。

**设计意图**：把"移动到某位姿"+"做手势"这两个高频组合动作**封装成单次点击**，消除用户"先点 movel、等到位、再点手型"的繁琐与出错可能；且通过 `block=True` 保证严格时序——**先到位、后动手**，这是"动作模仿/演示"类任务的刚需。

---

## 15. 状态刷新：`_arm_refresh_state`（L312–L329）

```python
L312  def _arm_refresh_state(self):
L313      if not self.arm_connected or self.arm is None:
L314          return
L315      try:
L316          s = self.arm.get_state_summary()
L317          q = s.get("joint_positions_rad")
L318          pose = s.get("tcp_pose")
L319          parts = [f"模式:{s['robot_mode']}", f"安全:{s['safety_mode']}"]
L320          if s.get("steady") is not None:
L321              parts.append("停止" if s["steady"] else "运动中")
L322          if q:
L323              deg = " ".join(f"{math.degrees(v):+5.1f}" for v in q)
L324              parts.append(f"J(deg): {deg}")
L325          if pose:
L326              parts.append(f"TCP: {', '.join(f'{v:.3f}' for v in pose)}")
L327          self.arm_status_var.set(" | ".join(parts))
L328      except Exception as exc:
L329          self.arm_status_var.set(f"状态读取失败: {exc}")
```

- **L313–L314**：未连接直接返回（轮询循环里每 800ms 调用一次，未连接时这是个廉价空操作）。
- **L316**：一次 `get_state_summary()` 拿回整个状态字典（`arm_controller.py` L290 定义：robot_mode、safety_mode、steady、within_safety、joint_positions_rad、tcp_pose、speed_fraction）。
- **L319**：基础片段 = 机器人模式 + 安全模式（`s['robot_mode']`/`s['safety_mode']` 是必现键，直接下标取）。
- **L320–L321**：`steady` 存在时显示"停止/运动中"——让操作者一眼看出臂有没有在动。
- **L322–L324**：6 关节角**弧度转度**（`math.degrees`），格式 `+5.1f`（带符号、5 位宽、1 位小数），如 `+12.3 -45.6 ...`，紧凑一行显示。
- **L325–L326**：TCP 位姿 6 个数各保留 3 位小数，逗号分隔。
- **L327**：所有片段用 `" | "` 拼接成一行（如 `模式:2 | 安全:0 | 停止 | J(deg): +0.0 ... | TCP: 0.100, ...`），塞进绿色状态标签。
- **L328–L329**：**读状态失败不崩溃**，把异常文本显示在状态区（"状态读取失败: ..."）——网络抖动时用户能看到原因而不是黑屏。

---

## 16. 常驻轮询：`_arm_poll_loop`——为什么用 `after(800)` 而非线程（L331–L338）

```python
L331  def _arm_poll_loop(self):
L332      """每 800ms 刷新机械臂状态（Tk after 常驻调度，非阻塞）。"""
L333      try:
L334          if self.arm_connected and self.arm is not None:
L335              self._arm_refresh_state()
L336      except Exception:
L337          pass
L338      self.root.after(800, self._arm_poll_loop)
```

**执行机制**：这不是循环也不是线程——`root.after(800, self._arm_poll_loop)` 是**向 Tk 事件循环注册一个 800ms 后的回调**；回调执行完又注册下一个，形成"自我续约"的常驻定时器。整个轮询**跑在 Tk 主线程**里。

**为什么用 `after` 而不是线程**：

| 方案 | 问题 |
|---|---|
| 独立线程轮询 | 线程里读到的状态要**跨线程更新 Tk 控件**，而 Tk 不是线程安全的，必须用 `queue` + 主线程定时取（原界面相机就是这样做的，复杂）；且线程生命周期要在关窗时妥善回收，容易出僵尸线程 |
| `root.after` 轮询 | 回调天然在主线程执行，**更新控件零同步成本**；无需线程管理；800ms 间隔内回调体（一次 `get_state_summary`）耗时远小于间隔，不会卡 UI |

**为什么是 800ms 而不是更短**：
- 机械臂状态（模式/安全/关节角/TCP）是**慢变量**，几百毫秒级刷新完全够用；
- 每次刷新都是一次 RTDE 网络读取，间隔太短会白白增加控制柜负担，也可能与运动指令争抢连接；
- 800ms 与人眼感知匹配——用户不会觉得"卡"，也不会觉得"跳"。

**异常吞掉（L333–L337）**：单次刷新失败不影响后续轮询——`after(800, ...)` 在 try 之外（L338），**无论如何都会注册下一次**，所以轮询永不中断；这是"常驻"语义的保证。

> ⚠️ 一个值得注意的细节：`_arm_poll_loop` 在 `__init__` 末尾（L60）启动后**永不显式停止**——但回调链在窗口销毁时随主线程一起结束，且 `_on_close` 会先断开机械臂（L345–L348），断开后 L334 的条件为假，后续轮询自动变为空转，不会访问已释放的对象。

---

## 17. 关闭流程：`_on_close` 覆写（L343–L350）

```python
L343  def _on_close(self):
L344      try:
L345          if self.arm is not None:
L346              self.arm.close()
L347      except Exception:
L348          pass
L349      self.arm = None
L350      super()._on_close()
```

- **L344–L348**：关窗前先**断开机械臂**（`self.arm.close()`：注销 RTDE、关 TCP 连接）；异常吞掉（网络已断也要能继续）。
- **L349**：清空控制器引用。
- **L350**：**然后才调用父类的 `_on_close`**——父类实现（`main_gui.py` L802–L822）负责：停相机线程、断开灵巧手、`root.quit()` + `root.destroy()`，最后 `os._exit(0)` **强制终止进程**。

**为什么顺序如此重要**：父类 `_on_close` 末尾是 `os._exit(0)`——**进程会立即终止，不再执行任何后续 Python 代码**。所以"断开机械臂"必须放在 `super()._on_close()` **之前**，否则机械臂连接永远不会被优雅关闭（TCP 会被操作系统强杀，控制柜侧可能残留会话）。这是继承体系下"覆写关闭流程"最关键的坑，本文件处理得正确。

---

## 18. 工具函数与入口：`logger_warn` / `main`（L353–L365）

```python
L353  def logger_warn(msg: str):
L354      import logging
L355      logging.getLogger("main_gui_arm").warning(msg)
L356
L357
L358  def main():
L359      root = tk.Tk()
L360      MainGuiArm(root)
L361      root.mainloop()
L362
L363
L364  if __name__ == "__main__":
L365      main()
```

- **L353–L355 `logger_warn`**：模块级小工具，把消息记到名为 `"main_gui_arm"` 的 logger 的 warning 级别（用于 `_arm_apply_fraction` 的异常记录）。`import logging` 放在函数内是**延迟导入**，避免模块加载时多一层依赖；整个模块没有 `logger = logging.getLogger(...)` 的全局实例，这是本文件刻意的轻量做法。
- **L358–L361 `main()`**：创建 `tk.Tk` 根窗口 → `MainGuiArm(root)`（构造即建全部界面并启动轮询）→ `root.mainloop()` 进入事件循环。
- **L364–L365**：`python -m gui.main_gui_arm` 时执行 `main()`。

---

## 19. 与 `main_gui.py` 的差异对比表

| 维度 | `gui/main_gui.py`（原） | `gui/main_gui_arm.py`（本文件） | 说明 |
|---|---|---|---|
| 类 | `class MainGui` | `class MainGuiArm(MainGui)` | 继承扩展，不改原类 |
| 界面行数 | 0~3 行 | 0~4 行（追加第 4 行机械臂面板） | `_build_arm_ui` 追加 |
| 相机/姿态/后处理 | ✅ 完整 | ✅ **复用**（继承） | 零重复代码 |
| 灵巧手控制（连接/校准/回零/预设手型/16 滑条/动作模仿） | ✅ 完整 | ✅ **复用**（继承） | 通过 `self.hand` 直接可用 |
| 机械臂连接 | ❌ 无 | ✅ 新增 `_arm_connect`/`_arm_disconnect` | |
| 机械臂电源/示教/回初始 | ❌ 无 | ✅ 新增 5 个按钮方法 | |
| 关节滑条 movej | ❌ 无 | ✅ 新增 6 轴滑条 + `_arm_movej_from_sliders` | 滑条范围 ±175° 保守值 |
| 位姿 movel | ❌ 无 | ✅ 新增 6 输入框 + `_arm_movel_from_entry` | |
| TCP 坐标联动 | ❌ 无 | ✅ 新增勾选框 `_arm_toggle_link` | 写入 `setTcpOffset` |
| 臂手联动 | ❌ 无 | ✅ 新增三按钮 `_arm_hand_link*` | movel 到位后再动手 |
| 状态轮询 | 视频用 `after(30)` | 机械臂状态新增 `after(800)` 常驻轮询 | 两条定时器互不干扰 |
| 关闭流程 | `_on_close` → 停相机/断手/`os._exit(0)` | 覆写：**先断机械臂**，再 `super()._on_close()` | 顺序是硬要求（见 §17） |
| 入口 | `python -m gui.main_gui` | `python -m gui.main_gui_arm` | 两个程序可独立运行 |

**为何不修改原文件**（设计决策）：
1. **隔离风险**：原 `main_gui.py` 是经过验证的灵巧手主界面，改动它可能影响相机/姿态/手控的既有行为；继承方式让机械臂功能"长在外面"，互不干扰；
2. **便于升级**：原文件有 bug 修复或功能增强时，直接替换文件即可，扩展版自动继承新行为，无需同步改两处；
3. **职责单一**：原文件保持"纯灵巧手系统"，机械臂相关代码集中在本文件，符合单一职责；
4. **代价**：继承意味着原界面的布局顺序固定（机械臂面板只能在底部第 4 行），且若父类 API 变化（如 `_on_close` 改名），子类需同步跟进——这是继承方案唯一需要留意的维护点。

---

## 20. 安全设计

机械臂是**高动能危险设备**，本文件的安全措施可以归纳为五层：

| 层级 | 措施 | 代码位置 |
|---|---|---|
| ① 速度限制 | 速度比例默认 0.3（保守起步），滑条范围 5%~100%，**实时可调**（运动中拉低即生效） | L84–L87、L180–L185；默认值来自 `arm_config.speed_fraction` |
| ② 连接守卫 | 所有机械臂操作前 `_require_arm()`，未连接直接拦截并提示 | L141–L145，被 9 个方法调用 |
| ③ 危险操作确认弹窗 | 上电/断电/回初始位/臂手联动均有 `askyesno` 二次确认，弹窗明示后果 | L190、L201、L227、L283 |
| ④ 运动失败即止 | movel/movej 返回非 0 就弹错并终止，臂手联动**绝不在未到位时做手势** | L236、L248、L285–L288 |
| ⑤ 优雅关闭 | 关窗前先断机械臂，避免 TCP 会话残留；轮询异常吞掉不崩溃 | L343–L350、L333–L337 |

补充要点：
- **急停路径**：随时可点 r2 行"停止"（`_arm_stop`）中断运动；也可直接把速度比例拉到 5% 让后续运动变慢；
- **操作纪律**（写在模块 docstring L19–L21）：首次连接建议速度比例 0.2~0.3；运动前确认机械臂周围无人、无障碍物；
- **确认弹窗的取舍**：停止/速度调节**不弹窗**（紧急场景要零延迟），上电/断电/回初始/臂手联动**弹窗**（不可逆或大范围运动场景）。

---

## 21. 常见问题（FAQ）

### Q1：机械臂面板的状态区一直不刷新 / 显示"状态: -"
- **原因**：未连接成功（`_arm_connected=False`），`_arm_refresh_state` L313 直接返回；或连接失败被 L160 拦截。
- **排查**：① 先点"连接"，看顶部蓝色状态字是否为"已连接(IP)"；② 检查 IP/端口与控制柜实际配置是否一致、网线连通、控制柜已开机；③ 若连接弹错，按 `arm_config.CONN_ERROR_TEXT` 的提示排查（被拒=IP/端口/未开机；超时=网络；重置=控制柜重启过）。

### Q2：未连接机械臂时点了"上电/停止/movej"等按钮
- **现象**：弹出黄色警告框"请先连接机械臂"，操作被拒绝——这是 `_require_arm` 守卫在起作用，**不是 bug**。
- **正确顺序**：先"连接"→ 再"上电+启动"→ 等状态字显示 Running → 再运动/联动。

### Q3：勾了"TCP联动"却感觉 movel 目标不对 / 联动失效
- **可能原因**：
  1. 未连接机械臂时勾选会被**强制弹回 False**（L254–L257），你以为开了其实没开——先连接再勾；
  2. `hand_mount_offset` 是示例值（z=0.15m、绕X轴180°），**没有按实际安装测量**，导致 TCP 基准偏差——实测后改 `arm_config.py`；
  3. 联动只影响**后续** movel 的坐标系，已经执行过的运动不会回改。
- **验证方法**：勾选后顶部状态字应显示"TCP 联动已开启（位姿=灵巧手 TCP）"；r3 状态区的 TCP 位姿读数会随偏移变化。

### Q4：点了"臂手联动"却没看到手部动作
- **排查链路**（对应 §14 五道关卡）：① 机械臂连了吗？② 灵巧手连了吗（`self.hand is None` 会提示）？③ 位姿输入是不是数字？④ 确认弹窗点"是"了吗？⑤ movel 是否成功（`ret != 0` 会弹"机械臂运动失败"且**不会做手势**——这是设计如此，防止没到位就抓手）。
- 若 movel 失败，检查目标位姿是否超出工作空间/关节限位，或把速度比例拉低重试。

### Q5：拖动速度比例滑条没反应
- **原因**：未连接时 `_arm_apply_fraction` 直接跳过（L181 条件不满足）；或已连接但被控制器钳制（`set_speed_fraction` 内部会 `max(0, min(1, ...))`）。
- **说明**：滑条值会在**下次连接时**作为构造参数生效（L157），所以可以先调好速度再连接。

### Q6：程序关闭时会不会有残留？
- 不会：`_on_close` 先 `self.arm.close()` 断机械臂，再走父类流程停相机、断灵巧手、`os._exit(0)` 强制退出，确保 TCP/RTDE 会话被主动释放。

### Q7：机械臂面板能放在别的位置吗？
- 当前固定在底部第 4 行（`grid(row=4)` L70）。若想调整，改 L68–L70 的行号与布局参数即可；但**不要动父类的 0~3 行**，否则破坏继承的界面。

---

## 22. 方法速查表

| 方法 | 行号 | 触发方式 | 一句话职责 |
|---|---|---|---|
| `__init__` | L52 | 构造 | super 建原界面 → 初始化机械臂状态 → 建面板 → 启动轮询 |
| `_build_arm_ui` | L65 | `__init__` | 搭建第 4 行机械臂面板（r1~r4 全部控件） |
| `_require_arm` | L141 | 各操作前调用 | 守卫：未连接则警告并返回 False |
| `_arm_connect` | L147 | 按钮"连接" | 建控制器、open()、失败清理弹错、成功刷新状态 |
| `_arm_disconnect` | L169 | 按钮"断开" | close() 后复位全部状态（幂等） |
| `_arm_apply_fraction` | L180 | 速度滑条拖动 | 已连接时实时下发 `set_speed_fraction` |
| `_arm_poweron` | L187 | 按钮"上电+启动" | 确认后上电松刹车，等 Running（15s 超时） |
| `_arm_poweroff` | L198 | 按钮"断电" | 确认后下电 |
| `_arm_stop` | L209 | 按钮"停止" | 立即停止运动（无确认，紧急用） |
| `_arm_freedrive` | L215 | 示教开/关按钮 | 进入/退出拖拽示教模式 |
| `_arm_home` | L224 | 按钮"回初始位" | 确认后回初始关节角 |
| `_arm_movej_from_sliders` | L232 | 按钮"执行 movej" | 滑条角度(度)→弧度→movej(block) |
| `_arm_movel_from_entry` | L240 | 按钮"执行 movel" | 输入位姿→float 校验→movel(block) |
| `_arm_toggle_link` | L252 | TCP联动勾选框 | 开：写灵巧手安装偏移；关：写全 0（法兰 TCP） |
| `_arm_hand_link` | L271 | 三个包装按钮 | 臂手联动主逻辑：movel 成功后才做手势 |
| `_arm_hand_link_fist/open/relax` | L300/L303/L306 | 三个联动按钮 | 分别以"握拳/张开/放松"调用 `_arm_hand_link` |
| `_arm_refresh_state` | L312 | 轮询/运动后 | 读状态汇总并格式化显示（模式/安全/停止/关节角/TCP） |
| `_arm_poll_loop` | L331 | `__init__` 启动 | 每 800ms 自续约刷新状态，永不中断 |
| `_on_close` | L343 | 关窗 | 先断机械臂，再 super()._on_close()（内含 os._exit(0)） |
| `logger_warn` | L353 | 内部 | 记 warning 日志（延迟 import logging） |
| `main` | L358 | `__main__` | 建 root → MainGuiArm → mainloop |

---

*（本文档完）*
