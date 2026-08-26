# 15 · arm_follow.py —— 人体腕部 3D → 机械臂 TCP 目标映射（协同控制核心）代码详解

> 本文档逐行级详解 `arm/arm_follow.py`（141 行，Windows 版"睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂 + L515 + MediaPipe Holistic 协同控制系统"的**人体腕部 3D → 机械臂 TCP 目标映射模块**，即"人动臂动"协同控制的核心坐标映射器）。
> 阅读本文档**不需要再读源码**即可完整理解该文件：坐标三段链、仿射近似公式、默认标定参数含义、每个方法的逐行逻辑、裁剪的安全意义、为什么不用完整手眼标定、现场标定方法、以及与 `holistic_pose.py` / `main_gui_holistic.py` 的接线方式。
> 建议搭配阅读：`docs/协同控制说明文档.md`（协同总说明，含标定流程）、`docs/代码详解/11_arm_controller.md`（机械臂控制器，含 TCP 坐标联动）、`docs/代码详解/14_holistic_pose.md` 之前的 `vision/holistic_pose.py`（腕部 3D 的来源）。

---

## 目录

1. [文件总览](#1-文件总览)
2. [模块 docstring 详解（坐标三段链 / 仿射近似 / 标定说明）](#2-模块-docstring-详解坐标三段链--仿射近似--标定说明)
3. [导入与日志](#3-导入与日志)
4. [DEFAULT_CALIB：默认标定参数逐个详解](#4-default_calib默认标定参数逐个详解)
5. [姿态常量：DEFAULT_GRASP_RPY 与"POSE 常量"说明](#5-姿态常量default_grasp_rpy-与pose-常量说明)
6. [类 ArmFollower 总览](#6-类-armfollower-总览)
7. [__init__ 构造方法逐行详解](#7-__init__-构造方法逐行详解)
8. [map_wrist_to_arm_pose：核心映射方法逐行详解（公式 + 裁剪）](#8-map_wrist_to_arm_pose核心映射方法逐行详解公式--裁剪)
9. [update_calib：运行时改标定参数（白名单机制）](#9-update_calib运行时改标定参数白名单机制)
10. [get_calib：读取当前标定参数](#10-get_calib读取当前标定参数)
11. [estimate_pose_from_arm：肩→肘方向估算姿态（可选）](#11-estimate_pose_from_arm肩肘方向估算姿态可选)
12. [坐标变换链与映射公式 ASCII 示意图](#12-坐标变换链与映射公式-ascii-示意图)
13. [为什么用仿射近似而不是完整手眼标定](#13-为什么用仿射近似而不是完整手眼标定)
14. [标定方法（两点 / 三点 / 手眼标定）](#14-标定方法两点--三点--手眼标定)
15. [与 holistic_pose / GUI 的接线](#15-与-holistic_pose--gui-的接线)
16. [自测 __main__ 详解（含数值演算）](#16-自测-__main__-详解含数值演算)
17. [常见问题（FAQ）](#17-常见问题faq)
18. [方法索引表与关键要点速查](#18-方法索引表与关键要点速查)

---

## 1. 文件总览

### 1.1 职责

本文件在整个协同控制链路中扮演**"坐标翻译官"**的角色：把"摄像头坐标系下的人体腕部 3D 位置（米）"，翻译成"机械臂基座坐标系下的 TCP 目标位姿 `[x, y, z, rx, ry, rz]`（米/弧度）"，交给机械臂控制器执行 `movel`，从而实现"人动臂动"。

```
        上游（视觉）                        本文件（映射）                    下游（执行）
 L515 深度反投影 → 腕部 3D  ────────►  ArmFollower.map_wrist_to_arm_pose  ────────►  arm.movel(pose)
 (vision/holistic_pose.py)           (arm/arm_follow.py，纯计算)               (arm/arm_controller.py)
```

**本模块的三个关键设计点**：

| 设计点 | 说明 |
|---|---|
| **纯计算、零硬件依赖** | 只做数值运算（加减乘除、裁剪、三角函数），不碰相机、不碰机械臂、不碰 SDK。因此可以脱离全部硬件单独验证（`python arm/arm_follow.py` 自测、`apps/test_holistic.py --selfcheck`）。 |
| **可现场标定** | 全部映射参数收敛在一个字典 `DEFAULT_CALIB` 里，GUI 可运行时修改（`update_calib`），支持现场逐步标定。 |
| **安全优先** | 映射结果强制裁剪到 `[min_xyz, max_xyz]` 安全框，防止深度异常/人快速移动导致机械臂越界猛动。 |

### 1.2 代码结构地图

| 行号区间 | 内容 |
|---|---|
| 1–27 | 模块 docstring：功能、坐标三段链、仿射近似说明、用法示例 |
| 29–35 | 导入（`__future__` / `logging` / `math` / `typing`）+ 模块日志器 |
| 37–49 | `DEFAULT_CALIB` 默认标定参数（offset / scale / add / fixed_rpy / min_xyz / max_xyz） |
| 51–52 | `DEFAULT_GRASP_RPY` 默认抓取姿态常量 |
| 55–74 | 类 `ArmFollower` 与 `__init__`（合并默认参数 + 防御性拷贝） |
| 76–91 | `map_wrist_to_arm_pose`：核心映射 + 安全裁剪 |
| 93–98 | `update_calib`：白名单式运行时改参 |
| 100–109 | `get_calib`：当前标定参数导出 |
| 111–128 | `estimate_pose_from_arm`：肩→肘方向估算姿态（可选） |
| 131–141 | `__main__` 自测：映射 + 越界裁剪验证 |

### 1.3 一句话总结

> **`target_i = (wrist_i − offset_i) × scale_i + add_i`，再裁剪进安全框，姿态固定为"朝下抓取"（或按肩→肘方向估算）——这就是本文件全部逻辑。**

---

## 2. 模块 docstring 详解（坐标三段链 / 仿射近似 / 标定说明）

docstring（第 2–27 行）是全文件的信息中心，包含四个层次的信息。

### 2.1 功能声明（第 3–7 行）

```
把"摄像头坐标系下的人体腕部 3D 位置"映射为"机械臂基座坐标系下的 TCP 目标位姿
[x, y, z, rx, ry, rz]"，实现"人动臂动"的协同控制。
```

- **输入**：腕部 3D 位置，单位**米**，坐标系为**相机系**（由 `holistic_pose.py` 的 `_pose_to_3d` 用 L515 深度 + 内参反投影得到）。
- **输出**：6 维位姿 `[x, y, z, rx, ry, rz]`：前 3 个是机械臂**基座坐标系**下的目标位置（米），后 3 个是**欧拉角 RPY**（弧度，绕固定轴 X→Y→Z 旋转），表示 TCP 的目标朝向。

### 2.2 坐标关系：三段链（第 9–11 行）

```
L515 相机系(米)  --外参 T_cam_base-->  机械臂基座系  --灵巧手安装偏移-->  TCP 系
                   (标定)                                    (setTcpOffset)
```

这是理解本模块最重要的概念，**整条坐标链分三段**：

1. **L515 相机系（米）**：原点在相机光学中心，x 向右、y 向下、z 向前（深度方向）。视觉模块输出的腕部 3D 就在这个坐标系里。
2. **机械臂基座系（米）**：原点在机械臂底座安装面中心，x 向前（作业方向）、y 向左、z 向上。机械臂的运动指令（`movel` 的目标位姿）以它为参考（再叠加 TCP 偏移）。
3. **TCP 系（米）**：原点在"工具中心点"——本项目即**灵巧手末端**。通过 `arm_controller.apply_tcp_offset()` 调用 SDK 的 `setTcpOffset` 写入"法兰偏移 + 灵巧手安装偏移"（`arm/arm_config.py` 的 `hand_mount_offset` 实测值），把 `movel` 的位姿基准从法兰盘挪到灵巧手 TCP。

**两段"跨坐标系"的翻译**：
- **相机系 → 基座系**：理想做法是标定一个完整 6DOF 外参 `T_cam_base`（旋转 + 平移，手眼标定）。**本文件用仿射近似代替**（见下一条）。
- **基座系 → TCP 系**：不是本文件的事，由机械臂控制器的 `setTcpOffset` 在 SDK 内部完成。本文件输出的 `[x,y,z]` 就是"TCP 系下的目标位置"（因为控制器已经设好偏移，`movel` 的坐标直接以灵巧手 TCP 为基准）。

### 2.3 当前实现：可现场标定的仿射近似（第 13–16 行）

```
* 平移映射：target = (wrist_3d - offset) * scale + add  （逐元素，米）
* 姿态固定：rx/ry/rz 取固定值（默认朝下抓取姿态）或按肩-肘方向估（可选）
* 缩放/偏移通过 CALIB 配置，GUI 可调，支持保存到 config/calibration.json
```

- **平移**：对 x/y/z 三轴**各自独立**地做 `(w − offset) × scale + add`。这是一个"对角阵 + 平移"的仿射变换：`offset` 吸收两坐标系原点的平移差，`scale` 吸收单位/尺度差，`add` 吸收残余平移。
- **姿态**：默认固定为"朝下抓取"（`[π, 0, 0]`），可选地按肩→肘方向估算（`estimate_pose_from_arm`）。
- **可标定**：参数集中在 `DEFAULT_CALIB`，GUI 的"映射标定"输入框可实时改 `offset/scale/add` 并生效（`update_calib`）。

### 2.4 为什么这么设计 + 用法示例（第 18–26 行）

- 相机↔机械臂外参最准确的做法是手眼标定；但本项目先以"缩放 + 平移"的仿射近似跑通闭环，现场按"人手移动到期望位置 → 记录机械臂实际目标"逐步校准 `offset/add`（详见第 13、14 节）。
- 映射函数纯计算，可单独验证。
- 用法示例：

```python
from arm.arm_follow import ArmFollower
f = ArmFollower()                                  # 用默认标定参数
pose6 = f.map_wrist_to_arm_pose([0.2, -0.3, 1.2])  # 腕部 3D(米) -> [x,y,z,rx,ry,rz]
```

---

## 3. 导入与日志

```python
from __future__ import annotations   # 第 29 行：延迟注解求值（字符串化类型注解，兼容旧 Python）
import logging                        # 第 31 行：日志
import math                           # 第 32 行：π、asin、atan2、sqrt（DEFAULT_CALIB 与姿态估算用）
from typing import List, Optional     # 第 33 行：类型注解
logger = logging.getLogger("arm_follow")   # 第 35 行：模块日志器（名字 "arm_follow"）
```

- `from __future__ import annotations`：让 `List[float]` 这类注解延迟求值，避免运行时开销与旧版本兼容问题——本文件实际只是"写类型给人看"，没有用运行时类型检查。
- `math` 的三处用途：① `DEFAULT_CALIB` 的 `fixed_rpy` 用 `math.pi`；② `DEFAULT_GRASP_RPY` 用 `math.pi`；③ `estimate_pose_from_arm` 用 `math.sqrt` / `math.asin` / `math.atan2`。
- 注意：本模块**不导入 numpy、不导入任何硬件库**——这是"纯计算、可单独验证"的根基。

---

## 4. DEFAULT_CALIB：默认标定参数逐个详解

```python
DEFAULT_CALIB = {
    "offset": [0.0, 0.0, 0.0],          # 相机系原点在机械臂基座系的位置（米）
    "scale": [1.0, 1.0, 1.0],           # 各轴缩放
    "add": [0.35, 0.0, 0.10],           # 目标附加平移（把"人前"映射到"臂前"）
    "fixed_rpy": [math.pi, 0.0, 0.0],   # TCP 姿态（弧度）
    "min_xyz": [0.15, -0.40, 0.10],     # 安全下限（米）
    "max_xyz": [0.90, 0.40, 0.80],      # 安全上限（米）
}
```

这是全文件**唯一需要现场关心的数据**。逐键解释：

### 4.1 `offset: [0.0, 0.0, 0.0]` —— 相机系原点在基座系的位置

- **含义**：相机坐标系原点相对机械臂基座原点的平移（米）。公式里 `wrist_i − offset_i` 的作用是"把腕部坐标从相机原点平移到基座原点"，即**先做原点对齐**。
- **默认 0 的原因**：起步阶段把两个原点近似视为重合（相机常装在机械臂附近、粗略安装），先不区分；真正差异由 `add` 粗调、两点标定精调。
- **现场标定后**：应当填"相机光心在基座系里的真实坐标"，例如 `[-0.1, 0.2, 0.3]`（相机在机械臂左后方、高 0.3m 之类）。

### 4.2 `scale: [1.0, 1.0, 1.0]` —— 各轴缩放

- **含义**：相机米 → 机械臂米的逐轴比例。单位都是米，理论上是 1.0；当两坐标系轴的**方向不一致**（相机斜着装）或存在镜头畸变未完全校正时，用缩放近似吸收"轴方向差异带来的投影伸缩"。
- **默认 1.0 的原因**：单位一致时最合理起步值。**反向问题的第一排查点也在这里**：如果人往右挥手臂往左走，说明该轴方向反了，应把对应 `scale[i]` 改为负数（如 `scale[0] = -1.0`）。

### 4.3 `add: [0.35, 0.0, 0.10]` —— 目标附加平移（"人前"→"臂前"）

- **含义**：映射结果再加一个固定平移（米）。
- **为什么是 `[0.35, 0.0, 0.10]`**：
  - 相机系里人站在相机前约 1~1.5 m，所以腕部 `z`（深度）≈ 1.0~1.4 m；而机械臂基座前的工作区约 0.3~0.8 m。直接把深度当作臂坐标会严重越界。
  - 注释"把'人前'映射到'臂前'"的含义：**补偿"相机前向（深度 z）"与"机械臂前向（x）"之间的位置折算**。`add[0] = 0.35` 把目标沿臂 x 方向前推 0.35 m，使目标落在机械臂正前方作业区；`add[2] = 0.10` 沿臂 z（竖直）上抬 0.10 m，粗略补偿相机与机械臂的安装高度差。
  - 强调：**这是经验初值，不是标定值**。它只保证"映射结果能落在安全框内、方向大致对"，精确对应必须现场标定（见第 14 节）。
- **注意**：因为本实现是逐元素映射（不做轴交换），"相机深度 → 臂前向"的严格对应其实要靠现场把 `scale/add` 调成近似值来逼近。这也正是第 13 节要解释的"仿射近似的局限"。

### 4.4 `fixed_rpy: [math.pi, 0.0, 0.0]` —— TCP 姿态（弧度）

- **含义**：映射输出的固定姿态 `[rx, ry, rz]`（欧拉角，弧度）。`rx = π` 表示**绕 X 轴旋转 180°**，把工具的 z 轴从"基座 +Z 向上"翻转为"朝下"——即手爪**垂直朝下抓取**的默认姿态（与 `DEFAULT_GRASP_RPY` 相同，见第 5 节）。
- **为什么不按人手姿态变**：抓取演示场景中"朝下"最通用、最安全；姿态跟踪需要完整手眼标定，属进阶。

### 4.5 `min_xyz` / `max_xyz` —— 安全裁剪框（最重要的安全机制）

| 轴 | 下限 | 上限 | 物理意义 |
|---|---|---|---|
| x（臂前向） | 0.15 | 0.90 | 太近会撞基座/立柱（<0.15 m 是死区）；太远超出 K5 工作半径或把人推得太远 |
| y（臂左右） | −0.40 | 0.40 | 横向摆幅限制，避免打到身体/周围物体，也避开奇异位形 |
| z（臂竖直） | 0.10 | 0.80 | 太低撞桌面/地面；太高超出关节范围或失去"朝下抓取"意义 |

- **为什么必须裁剪（防越界猛动）**：
  1. **深度噪声/离群点**：深度图在快速移动、遮挡、反光处会产生跳变的 3D 点，直接映射会让目标瞬间飞到几米外，机械臂会**猛甩**到极限甚至触发奇异保护；
  2. **工作空间约束**：目标超出机械臂可达范围时逆解失败或运动报错；裁剪保证目标始终在可达框内；
  3. **防碰撞**：目标太靠近基座/地面会撞本体或桌面；
  4. **平滑性**：把"突刺"压回边界，机械臂最多走到安全框边界，不会突然大幅动作。
- **裁剪实现**：`max(lo, min(hi, v))`——先取 `min(hi, v)`（封顶），再取 `max(lo, …)`（兜底），结果永远落在 `[lo, hi]` 闭区间内。

---

## 5. 姿态常量：DEFAULT_GRASP_RPY 与"POSE 常量"说明

```python
DEFAULT_GRASP_RPY = [math.pi, 0.0, 0.0]   # 绕 X 轴 180°（朝下）
```

### 5.1 DEFAULT_GRASP_RPY

- **含义**："人体腕部 → 机械臂"的默认抓取姿态：`rx = π`（绕 X 轴转 180°），`ry = rz = 0`。
- **几何理解**：机械臂基座系 z 轴默认朝上（工具直立）；绕 X 轴转 180° 后工具 z 轴指向**下方**，即手爪垂直朝下——这是"抓取/夹取"最常用的朝向。
- **与 DEFAULT_CALIB["fixed_rpy"] 的关系**：两者数值相同；`fixed_rpy` 是"可被标定覆盖的姿态"，`DEFAULT_GRASP_RPY` 是"缺省时的兜底姿态"。`__init__` 里 `c.get("fixed_rpy", list(DEFAULT_GRASP_RPY))` 用后者作为前者的默认值（第 72 行）。
- **为什么要拆成两个**：`DEFAULT_CALIB` 里的 `fixed_rpy` 允许用户通过标定字典覆盖成任意姿态（如侧抓、斜抓）；`DEFAULT_GRASP_RPY` 作为模块级常量单独命名，语义更清晰，也便于其他模块引用"标准朝下抓取姿态"。

### 5.2 "POSE 常量"说明（腕部索引从哪来）

`arm_follow.py` 本身**没有定义 `POSE_*` 索引常量**——腕部 3D 的"取点"发生在视觉模块 `vision/holistic_pose.py`（第 81–94 行）：

```python
POSE_LEFT_WRIST  = 15    # 人体左腕关键点索引（MediaPipe Pose 33 点）
POSE_RIGHT_WRIST = 16    # 人体右腕关键点索引
```

- `holistic_pose.process()` 第 296 行：`wrist_pose_idx = POSE_RIGHT_WRIST if side == "right" else POSE_LEFT_WRIST`，从 `pose_3d`（相机系米制 33 点）里取出对应腕部坐标作为 `r.wrist_3d`。
- 若人体未检测到，则回退用**手部 21 点的 WRIST 索引**（`hand_pose.WRIST`，即手部关键点 0）反投影出的 3D。
- 也就是说：**`arm_follow.py` 只负责"收到一个腕部 3D 就翻译"，不关心这个点来自人体 pose 还是手部 landmark**——这保持了映射器与视觉来源的解耦。

---

## 6. 类 ArmFollower 总览

```python
class ArmFollower:
    """
    人体腕部 3D → 机械臂 TCP 目标 映射器（可标定、可单独验证）。
    """
```

- **职责**：持有标定参数（`offset/scale/add/fixed_rpy/min_xyz/max_xyz` 六个实例属性），提供映射入口 `map_wrist_to_arm_pose`。
- **无状态设计**：除标定参数外不保存任何帧间状态——每帧调用、每帧独立，天然线程安全（GUI 主线程每帧调用）。
- **实例化成本**：零硬件、零 IO，构造只做几次数值拷贝，可以安全地在 GUI 里长期持有单个实例。
- **方法清单**：

| 方法 | 作用 | 调用方 |
|---|---|---|
| `__init__(calib=None)` | 初始化标定参数（合并默认 + 防御性拷贝） | GUI / 测试脚本 |
| `map_wrist_to_arm_pose(wrist_3d)` | **核心**：腕部 3D → 6 维 TCP 目标（含裁剪） | holistic_pose.process（经 arm_mapper）、GUI、自测 |
| `update_calib(**kwargs)` | 运行时更新白名单内的标定参数 | GUI"应用标定"按钮 |
| `get_calib()` | 导出当前标定参数（供显示/保存） | 预留（保存 calibration.json） |
| `estimate_pose_from_arm(shoulder_3d, elbow_3d)` | 可选：肩→肘方向估算姿态 | 当前代码中未启用（预留） |

---

## 7. `__init__` 构造方法逐行详解

```python
def __init__(self, calib: Optional[dict] = None):
    """
    Args:
        calib: 标定参数字典（含 offset/scale/add/fixed_rpy/min_xyz/max_xyz）；
               None 用 DEFAULT_CALIB。
    """
    c = dict(DEFAULT_CALIB)                       # 第 66 行
    if calib:                                     # 第 67 行
        c.update(calib)                           # 第 68 行
    self.offset = list(c.get("offset", [0.0, 0.0, 0.0]))      # 第 69 行
    self.scale = list(c.get("scale", [1.0, 1.0, 1.0]))        # 第 70 行
    self.add = list(c.get("add", [0.35, 0.0, 0.10]))          # 第 71 行
    self.fixed_rpy = list(c.get("fixed_rpy", list(DEFAULT_GRASP_RPY)))  # 第 72 行
    self.min_xyz = list(c.get("min_xyz", [0.15, -0.40, 0.10]))  # 第 73 行
    self.max_xyz = list(c.get("max_xyz", [0.90, 0.40, 0.80]))   # 第 74 行
```

逐行逻辑：

1. **第 66 行 `c = dict(DEFAULT_CALIB)`**：浅拷贝默认字典。**不直接改 `DEFAULT_CALIB` 本身**——保证多个 `ArmFollower` 实例、以及 GUI 里的默认值显示（`DEFAULT_CALIB["offset"][i]`）互不污染。
2. **第 67–68 行 `if calib: c.update(calib)`**：传入的自定义标定字典**按键覆盖**默认值。支持"只给一部分键"（例如只传 `{"add": [...]}`），其余键保持默认——这就是"部分标定/增量标定"的入口。`if calib` 同时过滤 `None` 和空字典。
3. **第 69–74 行**：六个参数统一模式 `self.xxx = list(c.get(key, default))`：
   - `c.get(key, default)`：键缺失时用默认值兜底，**永不 KeyError**；
   - `list(...)`：**防御性拷贝**——把传入的列表再复制一份。作用有二：① 防止外部修改传入列表导致实例内部参数被意外改掉；② 防止多个实例共享同一个列表对象（Python 列表是引用类型，直接赋值会共享内存）。
4. **第 72 行的特殊点**：`fixed_rpy` 的默认值是 `list(DEFAULT_GRASP_RPY)`（再次拷贝），而不是直接引用常量——同一个"防共享"动机。

> **设计意图**：整个 `__init__` 就是"**默认值 + 覆盖 + 拷贝**"三步，目的是让标定参数既灵活（可部分覆盖）又安全（不共享、不污染）。

---

## 8. `map_wrist_to_arm_pose`：核心映射方法逐行详解（公式 + 裁剪）

```python
def map_wrist_to_arm_pose(self, wrist_3d: List[float]) -> List[float]:
    """
    腕部 3D（相机系，米）→ 机械臂 TCP 目标位姿 [x,y,z,rx,ry,rz]（米/弧度）。

    公式：target_i = (wrist_i - offset_i) * scale_i + add_i，再裁剪到安全区间。
    """
    if wrist_3d is None or len(wrist_3d) < 3:            # 第 83 行
        raise ValueError("wrist_3d 需要至少 3 个分量")    # 第 84 行
    xyz = []                                             # 第 85 行
    for i in range(3):                                   # 第 86 行
        v = (float(wrist_3d[i]) - self.offset[i]) * self.scale[i] + self.add[i]  # 第 87 行
        lo, hi = self.min_xyz[i], self.max_xyz[i]        # 第 88 行
        xyz.append(max(lo, min(hi, v)))                  # 第 89 行
    pose = xyz + list(self.fixed_rpy)                    # 第 90 行
    return pose                                          # 第 91 行
```

### 8.1 逐行解释

- **第 83–84 行（输入校验）**：`wrist_3d` 为空或不足 3 个分量时**主动抛出 `ValueError`**。为什么主动抛而不是让它自然 `IndexError`：调用链上游（`holistic_pose.process`）会用 `try/except` 捕获映射异常并降级（只记 warning，不中断整帧处理），所以这里抛一个**语义明确的异常**，比"莫名 IndexError"好排查得多。
- **第 85–86 行**：`xyz` 收集三个轴的结果；`for i in range(3)` 只处理 x/y/z 三个轴（姿态轴单独处理）。
- **第 87 行（核心公式）**：
  ```
  v = (wrist_i - offset_i) * scale_i + add_i
  ```
  - `wrist_i − offset_i`：把腕部坐标从"相机原点"平移到"机械臂基座原点"（原点对齐）；
  - `× scale_i`：逐轴缩放（吸收方向/尺度差异，可负值实现镜像）；
  - `+ add_i`：附加平移（把目标推进机械臂前方作业区）。
  - `float(...)` 强转：容忍上游传入 numpy 标量（`np.float64`）或字符串，统一成 Python `float`。
- **第 88 行**：取该轴的安全下限 `lo`、上限 `hi`。
- **第 89 行（安全裁剪）**：`max(lo, min(hi, v))`——先封顶再兜底，结果 ∈ `[lo, hi]`。这正是第 4.5 节讲的"防越界猛动"的落地实现：**无论输入多离谱，输出都不可能超出安全框**。
- **第 90 行**：`xyz + list(self.fixed_rpy)`——位置（3 个）与姿态（3 个）拼成 6 维位姿。`list()` 再拷贝一次 `fixed_rpy`，防止调用方后续修改返回列表时污染内部参数。
- **第 91 行**：返回 `[x, y, z, rx, ry, rz]`，单位 米/弧度，可直接传给 `arm.movel(pose, block=False)`。

### 8.2 为什么裁剪能"防越界猛动"（展开）

机械臂跟随是**逐帧下发**的闭环：每帧 `wrist_3d → pose → movel`。如果某一帧的腕部 3D 因以下原因产生离群值：

| 异常来源 | 表现 | 不裁剪的后果 |
|---|---|---|
| 深度图噪声/反光 | z 瞬间跳到几米外 | 目标飞出工作空间 → 逆解失败或臂猛甩 |
| 人体快速移动/遮挡 | 关键点跳变 | 目标大幅突变 → 机械臂剧烈摆动 |
| 检测丢失后恢复 | 坐标从 0 跳回真实值 | 机械臂瞬间"飞"过整个行程 |

裁剪把每个轴的输出**钳制在安全框内**，于是机械臂最多移动到安全框边界，幅度变化被限制在"框内连续移动"——即使输入突变，臂的运动也保持可控。这是**"宁可位置不准，不可动作失控"**的安全设计哲学。

### 8.3 默认参数下的数值演算（直观理解公式）

默认标定下，输入 `wrist_3d = [0.2, -0.3, 1.2]`（人站在相机前约 1.2 m）：

| 轴 | 计算过程 | 结果 | 裁剪后 |
|---|---|---|---|
| x | (0.2 − 0) × 1 + 0.35 | 0.55 | 0.55（在 [0.15, 0.90] 内） |
| y | (−0.3 − 0) × 1 + 0 | −0.30 | −0.30（在 [−0.40, 0.40] 内） |
| z | (1.2 − 0) × 1 + 0.10 | 1.30 | **0.80（触发裁剪！超上限 0.80）** |

输出：`[0.55, −0.30, 0.80, π, 0, 0]`。

> **注意 z 轴真的触发了裁剪**：腕部深度 1.2 m 加 `add[2]=0.10` 后是 1.30 m，远超机械臂 z 上限 0.80 m，被压到 0.80。这说明默认参数下"远距离深度"本来就会被安全框兜住——**安全框在默认参数下就是活跃的**，不是摆设。

---

## 9. `update_calib`：运行时改标定参数（白名单机制）

```python
def update_calib(self, **kwargs):
    """运行时更新标定参数（GUI 用）。支持 offset/scale/add/fixed_rpy/min_xyz/max_xyz。"""
    for k, v in kwargs.items():
        if k in ("offset", "scale", "add", "fixed_rpy", "min_xyz", "max_xyz") and v:
            setattr(self, k, [float(x) for x in v])
```

### 9.1 逐行解释

- **`**kwargs`**：接受任意关键字参数（GUI 传 `offset=[...], scale=[...], add=[...]`）。
- **白名单判断 `k in ("offset", ..., "max_xyz")`**：只有这 6 个键**允许**被修改。这是本方法最关键的安全设计：
  - 防止**误改内部属性**：调用方笔误（如 `updat_calib(offsett=...)`）不会静默创建新属性（`setattr` 会真的给实例加属性）；
  - 防止**注入任意属性**：`**kwargs` 来源是 GUI 输入框，白名单保证任何"非标定键"都被忽略；
  - **可扩展性**：未来若加新参数（如平滑系数），只需往白名单元组里加一个名字。
- **`and v`**：值非空才更新——防止 `None`、`[]` 把参数清空成空列表（后续 `self.offset[i]` 会 IndexError）。
- **`[float(x) for x in v]`**：逐元素强转 `float`。GUI 输入框传的是**字符串**（如 `"0.35"`），这里统一转数字；若输入非数字会抛 `ValueError`——GUI 侧（`_holistic_apply_calib`）恰好 catch 它并弹窗"标定参数必须是数字"。**这层转换是 GUI 字符串输入能工作的关键**。

### 9.2 为什么叫"白名单"

对比"黑名单"（拒绝特定键）或"无限制 setattr"：白名单是**默认拒绝、显式放行**，语义最安全——即使调用方传了 100 个键，也只有 6 个被接受。这是防御式编程的典型写法，适合"参数来自外部输入"的场合。

---

## 10. `get_calib`：读取当前标定参数

```python
def get_calib(self) -> dict:
    """当前标定参数（供 GUI 显示/保存）。"""
    return {
        "offset": list(self.offset),
        "scale": list(self.scale),
        "add": list(self.add),
        "fixed_rpy": list(self.fixed_rpy),
        "min_xyz": list(self.min_xyz),
        "max_xyz": list(self.max_xyz),
    }
```

- **作用**：把 6 个实例属性打包成与 `DEFAULT_CALIB` 同构的字典。
- **每个值都 `list()` 拷贝**：返回的是"快照"，调用方改返回字典不会影响实例内部参数——与 `__init__`、`map_wrist_to_arm_pose` 第 90 行同一套"防共享"原则。
- **用途**：① GUI 显示当前标定值；② 序列化保存到 `config/calibration.json`（docstring 里提到的"支持保存"，本方法就是导出接口）；③ 现场标定后把结果回读、固化。

---

## 11. `estimate_pose_from_arm`：肩→肘方向估算姿态（可选）

```python
def estimate_pose_from_arm(self, shoulder_3d: List[float],
                           elbow_3d: List[float]) -> List[float]:
    """
    可选：由 肩→肘 方向估 TCP 姿态（近似朝目标方向）。
    返回 [rx, ry, rz]（弧度，欧拉近似）。未标定时返回 fixed_rpy 更稳。
    """
    try:
        v = [elbow_3d[i] - shoulder_3d[i] for i in range(3)]   # 第 119 行
        n = math.sqrt(sum(x * x for x in v))                    # 第 120 行
        if n < 1e-6:                                            # 第 121 行
            return list(self.fixed_rpy)                         # 第 122 行
        pitch = math.asin(max(-1.0, min(1.0, -v[1] / n)))       # 第 124 行
        yaw = math.atan2(v[0], v[2])                            # 第 125 行
        return [pitch, yaw, self.fixed_rpy[2]]                  # 第 126 行
    except Exception:                                           # 第 127 行
        return list(self.fixed_rpy)                             # 第 128 行
```

### 11.1 逐行解释

- **第 119 行 `v = elbow − shoulder`**：计算"肩 → 肘"方向向量（相机系，米）。手臂伸直时，肘的方向 ≈ 手臂指向的方向，用它近似 TCP 的朝向。
- **第 120 行 `n = |v|`**：向量模长（肩肘距离，约 0.2~0.5 m）。`sum(x*x for x in v)` 是平方和，再开方——**向量归一化的第一步**（后面除以 n）。
- **第 121–122 行 `n < 1e-6`**：肩肘几乎重合（检测异常/截断/数值错误）时无法确定方向，**回退固定姿态**。`1e-6` 是防止除零的阈值。
- **第 124 行 `pitch = asin(clamp(−v[1]/n))`**：
  - `v[1]/n` 是方向向量的 y 分量（归一化后），即"竖直方向的单位分量"；
  - 相机系 y 轴**向下**，而机械臂习惯 y 轴**向上**，所以取 `−v[1]/n` 把"向下"转成"向上为正"；
  - `asin` 得到俯仰角：肘明显低于肩 → `v[1] > 0` → `−v[1]/n < 0` → pitch 为负（TCP 朝下倾斜）；
  - **`max(-1.0, min(1.0, ...))` 先钳制到 [−1, 1]**：`asin` 的输入必须在此区间；`v[1]/n` 理论上必然在此区间，但浮点误差可能略超（如 1.0000000001），钳制后保证 `asin` 永不报 ValueError——这是**防御浮点边界**的经典写法。
- **第 125 行 `yaw = atan2(v[0], v[2])`**：
  - `atan2(y, x)` 形式：第一个参数是 x 分量（相机右向），第二个是 z 分量（相机前向）；
  - 结果是从"朝前（+z）"旋转到"朝肘方向（x,z 投影）"的**偏航角**：肘在右 → yaw > 0，肘在左 → yaw < 0；
  - `atan2` 比 `atan` 好在**自动处理四个象限**，不会出现方向判反。
- **第 126 行 `return [pitch, yaw, fixed_rpy[2]]`**：roll（绕 z 轴）沿用固定值——抓取场景手爪绕自身轴线旋转无实际意义，且未标定。
- **第 127–128 行 `except Exception`**：**整个姿态估算包在 try 里，任何异常（None 输入、非数值、除零、下标错误）都回退固定姿态**。设计哲学：姿态估算是"可选增强"，**绝不因它崩溃主流程**——最坏情况就是退化为固定朝下抓取。

### 11.2 重要局限（务必理解）

1. **坐标系不匹配**：该姿态是在**相机系**下算的角度，却直接作为**基座系**的 RPY 输出——只有在相机与机械臂坐标轴大致平行时才近似成立。因此注释明确写"未标定时返回 fixed_rpy 更稳"。
2. **当前代码中未启用**：全工程 grep 显示该方法**只定义、无调用**（`holistic_pose.process` 只接 `arm_mapper` 映射位置，姿态仍走 `fixed_rpy`）。它是为"未来按手臂方向控制手爪朝向"预留的接口。
3. **方向语义是近似**：肩→肘方向 ≠ 手爪应指向的方向（真实指向应由"肘→腕"或"手部平面法向"决定），这里只是低成本近似。

---

## 12. 坐标变换链与映射公式 ASCII 示意图

### 12.1 坐标三段链全景

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ① L515 相机系 C（米制）                                                        │
│    原点：相机光学中心         x 向右 · y 向下 · z 向前（深度）                   │
│    wrist_3d = (wx, wy, wz)   ← 深度反投影得到（holistic_pose._pose_to_3d）      │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    │  外参 T_cam_base（旋转 + 平移）
                                    │  理想：手眼标定（标定板 + calibrateHandEye）
                                    │  本项目：仿射近似
                                    │    target_i = (wrist_i - offset_i) * scale_i + add_i
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ② 机械臂基座系 B（米制）                                                       │
│    原点：机械臂底座安装面中心     x 向前 · y 向左 · z 向上                      │
│    target_xyz = (tx, ty, tz)     ← 本文件 map_wrist_to_arm_pose 输出（已裁剪）  │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    │  机械臂运动学（逆解 IK）+ setTcpOffset
                                    │  （arm_controller.apply_tcp_offset 已写入
                                    │    法兰偏移 + 灵巧手安装偏移）
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ③ TCP 系 T（米制，灵巧手末端）                                                 │
│    target = (tx, ty, tz, π, 0, 0)  ← 6 维目标位姿，movel 以它为准               │
│    "TCP 系下的目标" = "手爪应该到达的位置"（TCP 联动已生效）                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 wrist_3d → target 公式示意（逐元素流水线）

```
 wrist_3d (相机系, 米)
   wx ─┐
   wy ─┤
   wz ─┘
        │ ① 原点对齐：减去 offset（相机原点→基座原点）
        ▼
   (wx-off_x), (wy-off_y), (wz-off_z)
        │ ② 逐轴缩放：× scale（吸收轴方向/尺度差异，可为负=镜像）
        ▼
   (wx-off_x)*sx, (wy-off_y)*sy, (wz-off_z)*sz
        │ ③ 附加平移：+ add（把"人前"推到"臂前"作业区）
        ▼
   vx, vy, vz
        │ ④ 安全裁剪：clamp 到 [min_xyz, max_xyz]（防越界猛动）
        ▼
   x = clamp(vx, 0.15, 0.90)
   y = clamp(vy, -0.40, 0.40)
   z = clamp(vz, 0.10, 0.80)
        │ ⑤ 拼接固定姿态（或 estimate_pose_from_arm 估算值）
        ▼
   pose6 = [x, y, z, rx, ry, rz]   ──►  arm.movel(pose6, block=False)  人动臂动
```

### 12.3 一段话复述

> 相机看到的人手腕（相机系）→ 先减去相机与机械臂的原点差（offset）→ 按轴缩放（scale）→ 加一个把目标推进作业区的平移（add）→ 塞进机械臂安全作业框（min/max 裁剪）→ 姿态固定朝下（π,0,0）→ 得到一个可以直接发给 `movel` 的 6 维位姿。

---

## 13. 为什么用仿射近似而不是完整手眼标定

docstring 第 19–20 行明说："相机↔机械臂外参（旋转+平移）最准确做法是手眼标定；本项目先用'缩放+平移'仿射近似"。展开讲：

### 13.1 完整手眼标定是什么

- 用**标定板**（棋盘格/圆点阵列）和 OpenCV 的 `calibrateHandEye`（求解 AX=XB）标出相机与机械臂之间的**完整外参**：一个 3×3 旋转矩阵 R + 3 维平移向量 t，即 6DOF 的齐次变换 `T_cam_base`。
- 映射公式变为齐次变换：`target_h = T_cam_base · wrist_h`（把腕部 3D 齐次化后乘外参矩阵），姿态也从外参旋转部分 + 工具姿态得出。

### 13.2 为什么本项目先用仿射近似（设计权衡）

| 维度 | 完整手眼标定 | 仿射近似（本项目） |
|---|---|---|
| **标定成本** | 需要标定板、机械臂在多个姿态下拍摄、OpenCV 解算、误差评估——至少半天到一天 | 两点标定约 5~10 分钟，GUI 改参数即时生效 |
| **先跑通闭环** | 标定完成前机械臂完全动不了 | 默认参数 + 安全裁剪就能先让"人动臂动"闭环转起来 |
| **现场可调性** | 标定后参数固定，现场微调要重标 | GUI 输入框实时改 offset/scale/add，随改随验 |
| **姿态处理** | 需要完整 6DOF 姿态（标定板提供旋转信息） | 固定"朝下抓取"姿态，绕开姿态标定 |
| **精度** | 高（旋转 + 平移全建模） | 中（近似轴对齐，忽略旋转）；对"跟随演示/粗定位抓取"够用 |
| **对安装条件的要求** | 相机安装角度随意 | 相机与机械臂坐标轴大致平行时误差小；斜装误差大 |

**一句话**：**"先跑通、再标定、最后再决定要不要上完整外参"**——仿射近似是最低成本的可行性验证，手眼标定是它的最终升级路径。

### 13.3 仿射近似的数学本质与局限

- `target = (w − offset) × scale + add` 等价于**对角矩阵 D + 平移 b** 的仿射变换：`target = D·w + b`，其中 `D = diag(scale)`，`b = add − D·offset`。
- 它隐含假设：**相机系与基座系的三个坐标轴近似平行**（旋转部分 ≈ 单位阵）。若相机有明显俯仰/偏航安装角，真实外参的旋转矩阵有非对角元素，仿射近似会把它"摊"进 scale 和 add，导致**离原点越远误差越大**。
- **升级信号**：当"人在相机前不同距离/位置时，机械臂偏差明显不一致"（近处准、远处偏），就说明旋转成分不可忽略，应升级手眼标定，把公式换成 `target = R·w + t`（代码只需改 `map_wrist_to_arm_pose` 一行公式，接口不变）。

---

## 14. 标定方法（两点 / 三点 / 手眼标定）

> 标定对象：`offset` / `scale` / `add`（姿态一般保持固定 `[π,0,0]` 不动）。原则：**未标定前禁止开"机械臂跟随"**。

### 14.1 方法一：两点标定（推荐起步）

目标：求出"相机系腕部坐标"与"期望 TCP 位置"的对应关系。假设 `scale = [1,1,1]`，则公式简化为 `target = wrist − offset + add`，令 `b = add − offset`，即 `target = wrist + b`，**只需解一个 3 维平移向量 b**。

步骤：
```
① 人站在相机前约 1m，把手腕放在一个期望位置 P1
② 记下 GUI 显示的腕部 3D：w1 = (wx1, wy1, wz1)
③ 用示教器（freedrive 拖拽）把机械臂手动移到"希望手爪到达的位置"，记下 TCP：t1 = (tx1, ty1, tz1)
④ 求平移：b = w1 − t1（即 offset−add 的合并值）
⑤ 在 GUI 填入：offset = b 各分量，add 保持 0（或按第 2 点微调）
⑥ 换一个位置 P2 验证：手腕移到 P2，机械臂应大致跟随到对应位置；偏差用 add 微调
```

> 工程技巧：先让 `offset = b`、`add = [0,0,0]` 跑通，再逐步把部分平移挪进 `add` 以分离"原点差"与"作业区偏移"的语义（纯数值上两者合并等价，分开只为可读性）。

### 14.2 方法二：三点标定（更准）

用三个**不共线**的空间位置同时解出 `scale` 和 `offset`：

```
① 左 / 中 / 右（或近 / 中 / 远）三个位置，分别记录 (腕部 3D wi, 实际 TCP ti)，i=1,2,3
② 每轴独立列方程：ti = (wi − offset) * scale + add
   整理成线性形式：ti = scale * wi + b，其中 b = add − scale * offset
   对 x 轴：tx1 = sx*wx1 + bx；tx2 = sx*wx2 + bx  → 解出 sx, bx（两个点解两个未知数）
   三个点可做最小二乘冗余求解，更稳
③ 得到 scale 后：offset = (add − b) / scale（先定 add，或 add 归零）
```

- **为什么三点比两点准**：三点能同时约束"缩放"和"平移"，还能暴露"轴方向不对"（若某轴解出的 scale 为负，说明该轴方向镜像，需要反转）。
- **注意**：三个点应尽量拉开、不要共线，否则方程退化。

### 14.3 方法三：手眼标定（最准，进阶）

```
① 准备标定板（棋盘格或圆点阵），固定在相机视野内、机械臂可达处
② 机械臂在多个姿态下拍摄标定板，记录 (标定板角点检测, 机械臂 TCP 位姿) 多组数据
③ OpenCV calibrateHandEye 解出相机↔机械臂外参 T_cam_base（R, t）
④ 把 arm_follow 的公式升级为齐次变换：
      target_h = T_cam_base · [wx, wy, wz, 1]ᵀ
   姿态也可由外参旋转部分 + 期望工具姿态完整得出（不再固定朝下）
⑤ 重新验证：人移动手腕，机械臂应精确跟随（误差收敛到 cm 级以内）
```

- 适用：对定位精度要求高、相机安装角度大、需要非固定姿态抓取的场景。
- 成本：需要标定板 + 标定程序 + 半天的数据采集与误差分析。
- **代码改动量极小**：只改 `map_wrist_to_arm_pose` 内部的公式（或给 `ArmFollower` 增加一个 `T_cam_base` 矩阵参数），对外接口 `wrist_3d → pose6` 完全不变，`holistic_pose` / GUI 零改动。

### 14.4 标定验证清单

1. 标定后**先小速度（0.2）试跑**，人慢慢移动手腕，机械臂应平滑跟随、末端接近期望位置；
2. **反向检查**：人往右 → 臂往右；人往前 → 臂往前；反了查 `scale` 符号；
3. **幅度检查**：人动 10 cm，臂应动约 10 cm（误差 < 2~3 cm 可接受）；幅度不对调 `scale`；
4. **边界检查**：手腕移到安全框边缘，机械臂应停在边界而不是继续冲；
5. 标定完成后把 `get_calib()` 的返回值保存到 `config/calibration.json`，下次启动时读入传入 `ArmFollower(calib=...)`。

---

## 15. 与 holistic_pose / GUI 的接线

### 15.1 调用关系总览

```
gui/main_gui_holistic.py (MainGuiHolistic)
   │  self.follower = ArmFollower()                        # 构造映射器（默认标定）
   │  self.holistic  = HolisticPoseEstimator(...)          # 构造视觉估计器
   │
   │ 每帧（_holistic_step）：
   │  ┌──────────────────────────────────────────────────────────────────┐
   │  │ results = self.holistic.process(                                 │
   │  │     rgb, depth, intrinsics,                                      │
   │  │     map_to_arm=self.holistic_arm_follow_var.get(),   ← 勾选开关   │
   │  │     arm_mapper=self.follower.map_wrist_to_arm_pose,   ← 注入映射器 │
   │  │ )                                                                │
   │  └──────────────────────────────────────────────────────────────────┘
   │        │
   │        ▼  vision/holistic_pose.py 内部（process 第 311–315 行）
   │  if map_to_arm and arm_mapper is not None and r.wrist_3d is not None:
   │      r.arm_target_pose = arm_mapper(r.wrist_3d)      ← 调用映射（异常被捕获降级）
   │        │
   │        ▼  GUI 拿到结果
   │  if self.holistic_arm_follow_var.get() and r.arm_target_pose is not None:
   │      self.arm.movel(r.arm_target_pose, block=False, timeout_s=5)   ← 人动臂动
   │
   │ 用户点【应用标定】→ _holistic_apply_calib：
   │      self.follower.update_calib(offset=[...], scale=[...], add=[...])  ← 运行时改参
   │
   └─ 关闭窗口 → _holistic_stop() → holistic.close()
```

### 15.2 各接线点的细节

| 接线点 | 代码位置 | 说明 |
|---|---|---|
| **构造** | `main_gui_holistic.py` 第 62 行 `self.follower: ArmFollower = ArmFollower()` | GUI 持有单个实例，全程复用；`ArmFollower()` 不带参数即用 `DEFAULT_CALIB` |
| **注入映射器** | `main_gui_holistic.py` 第 188 行 `arm_mapper=self.follower.map_wrist_to_arm_pose` | 传的是**方法引用（callable）**，不是实例——`holistic_pose` 只要求"可调用：wrist_3d → pose6"（鸭子类型，松耦合） |
| **映射触发条件** | `holistic_pose.py` 第 311 行 `if map_to_arm and arm_mapper is not None and r.wrist_3d is not None` | 三个条件：GUI 勾选跟随、注入了映射器、本帧检测到有效腕部 3D；**任一不满足就不映射**，避免对 None 调用 |
| **异常降级** | `holistic_pose.py` 第 313–315 行 `try: ... except Exception: logger.warning("arm mapper 异常: %s", exc)` | 映射器抛异常（如腕部不足 3 分量）只记 warning，**不中断整帧**，`arm_target_pose` 保持 None |
| **执行跟随** | `main_gui_holistic.py` 第 216 行 `self.arm.movel(r.arm_target_pose, block=False, timeout_s=5)` | **非阻塞** movel：主线程每帧调用，机械臂忙则丢帧，下一帧继续跟（跟随模式的正确用法） |
| **运行时标定** | `main_gui_holistic.py` 第 168–172 行 `self.follower.update_calib(offset=[float(v.get()) for v in ...], ...)` | GUI 输入框（字符串）→ `update_calib` 白名单 + `float()` 转换 → 立即生效；非法输入抛 ValueError → GUI 弹窗 |
| **独立验证** | `apps/test_holistic.py` 第 88–96 行（`follower = ArmFollower()` + `--selfcheck` 直接调 `map_wrist_to_arm_pose`） | 无硬件验证映射方向与数值 |
| **数据流闭环** | `HolisticResult.wrist_3d`（相机系米制）→ `arm_target_pose`（基座系 6 维）→ 状态栏显示"腕3D=… 臂TCP=…" | GUI 第 202–207 行把两个量都显示出来，标定时对照观察 |

### 15.3 时序图（一帧）

```
 主线程每帧
   │
   ├─ _poll_video()（父类）：取帧 → 显示 → 原 mimic 逻辑
   ├─ _holistic_step(rgb, depth, intrinsics)
   │     ├─ holistic.process(map_to_arm=True, arm_mapper=follower.map_wrist_to_arm_pose)
   │     │     ├─ HolisticLandmarker.detect → 33 人体点 + 21 手部点
   │     │     ├─ _pose_to_3d：深度反投影 → wrist_3d（相机系，米）
   │     │     └─ arm_target_pose = arm_mapper(wrist_3d)   ← 本文件核心被调用
   │     ├─ 状态栏显示 腕3D / 臂TCP
   │     └─ 若勾选跟随：arm.movel(arm_target_pose, block=False)
   └─ draw_skeleton：人体 + 手部骨架叠加显示
```

---

## 16. 自测 `__main__` 详解（含数值演算）

```python
if __name__ == "__main__":
    # 自测：映射函数纯计算验证
    f = ArmFollower()                                          # 第 133 行
    pose = f.map_wrist_to_arm_pose([0.2, -0.3, 1.2])           # 第 134 行
    print(f"腕部(0.2,-0.3,1.2) -> TCP {[round(v,3) for v in pose]}")   # 第 135 行
    assert len(pose) == 6                                      # 第 136 行
    # 边界裁剪验证
    p2 = f.map_wrist_to_arm_pose([5.0, 5.0, 5.0])              # 第 138 行
    print(f"越界腕部 -> TCP {[round(v,3) for v in p2]}（应被裁剪）")      # 第 139 行
    assert p2[0] <= f.max_xyz[0] + 1e-6 and p2[1] <= f.max_xyz[1] + 1e-6  # 第 140 行
    print("ArmFollower 自测通过")                               # 第 141 行
```

- **第 133 行**：默认标定实例。
- **第 134–136 行**：正常腕部输入 → 断言输出 6 维。按第 8.3 节演算：`[0.55, −0.30, 0.80, π, 0, 0]`（z 被裁剪）。
- **第 138–139 行**：`[5,5,5]` 是极端越界输入（正常人手腕不可能到 5 m），验证裁剪：
  - x：`(5−0)×1+0.35 = 5.35` → 裁剪到 `0.90`；
  - y：`(5−0)×1+0 = 5.0` → 裁剪到 `0.40`；
  - z：`(5−0)×1+0.10 = 5.10` → 裁剪到 `0.80`；
  - 输出 `[0.90, 0.40, 0.80, π, 0, 0]`。
- **第 140 行**：断言裁剪生效——`p2[0] ≤ 0.90 + 1e-6`、`p2[1] ≤ 0.40 + 1e-6`（`1e-6` 容忍浮点误差）。**只断言了 x/y 上限**，因为断言目的是"验证裁剪机制在工作"，不必覆盖所有轴。
- **运行方式**：`python arm/arm_follow.py`。无需相机、无需机械臂、无需 SDK——这是该模块"可单独验证"的直接体现。

---

## 17. 常见问题（FAQ）

### 17.1 机械臂运动方向反了（人往右，臂往左）

| 排查项 | 说明 |
|---|---|
| **scale 符号** | 对应轴的 `scale[i]` 取反（如 `scale[0] = -1.0`）。相机 x 向右、臂 x 向前，若相机斜装/镜像，逐元素近似会方向相反 |
| **offset 符号** | 两点标定时 b = w − t 若算反，整体平移反向；重新按第 14.1 节步骤核对 |
| **相机安装方向** | 确认 L515 的 RGB 画面是否镜像（MediaPipe 关键点是画面坐标，镜像安装会整体反） |

### 17.2 幅度不对（人动 10cm，臂动 5cm 或 20cm）

- **人动臂动小**：`scale` 该轴调大（如 1.0 → 1.5）；
- **人动臂动大**：`scale` 调小；
- **近处准、远处偏**：这是旋转成分未被建模的典型表现（见 13.3），可先用三组远近点拟合 scale，仍不满意就上三点/手眼标定；
- **只有某个方向偏**：逐轴检查，只调对应轴的 scale/add。

### 17.3 越界裁剪频繁触发（目标一直顶在边界上，机械臂"卡住"）

- **表现**：状态栏"臂TCP"的某个分量长时间等于 0.90 / 0.80 / 0.40 等边界值；
- **原因**：① 腕部 3D 离群（深度噪声、人太远/太近）；② 默认 `min/max` 与现场工作区不匹配；
- **处理**：
  - 先看"腕3D"显示值是否合理（人站 1m 处手腕 z 应约 1.0~1.4）；
  - 深度不稳 → 用 L515 深度、减少反光、避免快速移动；
  - 工作区确实需要更大范围 → 谨慎放宽对应轴的 `min_xyz/max_xyz`（务必确认机械臂在放大的范围内可达且不碰撞）；
  - 不要为了"不裁剪"而把安全框开到极大——安全框是保命机制。

### 17.4 目标不可达（movel 报错 / 机械臂不动）

- **表现**：映射输出在安全框内，但 `movel` 返回错误码或臂不动作；
- **原因**：安全框只是"位置框"，未考虑**机械臂运动学可达性**——框内某些点可能超出臂长（如 x=0.9, y=0.4 同时取上限，对角线距离可能超工作半径）或接近奇异位形；
- **处理**：
  - 收紧 `max_xyz`（如 x 上限 0.90 → 0.75），让目标远离工作空间边缘；
  - 检查机械臂当前是否 Running 模式、是否急停、`arm.movel` 返回值（`arm_controller._ret_text` 会把错误码转中文）；
  - 速度比例过低时表现为"几乎不动"，调高 `speed_fraction`；
  - 每帧非阻塞 movel 若机械臂忙会丢帧，属正常，但若目标频繁大跳变会反复触发"目标不可达"——先解决 17.3 的输入稳定性。

### 17.5 手爪朝向不对（需要斜抓/侧抓，而不是垂直朝下）

- 默认 `fixed_rpy=[π,0,0]` 只支持垂直朝下；
- 需要其他朝向：① 改 `fixed_rpy`（需理解欧拉角约定，注意与机械臂姿态表示一致）；② 启用 `estimate_pose_from_arm`（当前未接线，需在 `holistic_pose.process` 的映射处把姿态替换为肩→肘估算结果）；③ 最彻底——手眼标定得到完整外参后由外参旋转部分 + 工具姿态给出。

### 17.6 改了标定参数没生效

- 确认 GUI 点的是【应用标定】（`_holistic_apply_calib`）而不是只改了输入框；
- 确认 `update_calib` 传的键名在白名单内（`offset/scale/add/fixed_rpy/min_xyz/max_xyz`），且值非空；
- 确认状态栏出现"标定参数已应用"（若弹"必须是数字"说明输入框有非数字字符，`float()` 转换失败）。

### 17.7 重启后参数丢失

- 当前 GUI 只支持运行时修改，**没有把 `get_calib()` 写回 `config/calibration.json` 的持久化逻辑**（docstring 提及"支持保存"是设计意图，落地需自行扩展）；
- 现场标定好后，把 `get_calib()` 的结果手动存文件，启动时 `ArmFollower(calib=json.load(...))` 读入即可。

---

## 18. 方法索引表与关键要点速查

### 18.1 方法索引

| 方法 | 签名 | 输入 → 输出 | 关键点 |
|---|---|---|---|
| `__init__` | `(self, calib=None)` | 标定字典 → 实例 | 默认 + 覆盖 + 防御性拷贝；键缺失兜底 |
| `map_wrist_to_arm_pose` | `(self, wrist_3d)` | `[wx,wy,wz]`(米) → `[x,y,z,rx,ry,rz]` | 仿射公式 + 安全裁剪；输入不足 3 分量抛 ValueError |
| `update_calib` | `(self, **kwargs)` | 白名单键 → 无 | 6 键白名单 + 值非空 + `float()` 转换 |
| `get_calib` | `(self)` | 无 → dict | 6 参数快照（list 拷贝） |
| `estimate_pose_from_arm` | `(self, shoulder_3d, elbow_3d)` | 肩/肘 3D → `[rx,ry,rz]` | 肩→肘向量归一化；pitch=asin(−vy/n)、yaw=atan2(vx,vz)；任何异常回退固定姿态 |

### 18.2 关键常量速查

| 常量 | 值 | 含义 |
|---|---|---|
| `DEFAULT_CALIB["offset"]` | `[0,0,0]` | 相机原点在基座系的位置（起步=0，现场标定） |
| `DEFAULT_CALIB["scale"]` | `[1,1,1]` | 逐轴缩放（反向就取负） |
| `DEFAULT_CALIB["add"]` | `[0.35,0,0.10]` | 目标附加平移（"人前"→"臂前"经验值） |
| `DEFAULT_CALIB["fixed_rpy"]` | `[π,0,0]` | TCP 姿态：绕 X 轴 180° 朝下 |
| `DEFAULT_CALIB["min_xyz"]` | `[0.15,−0.40,0.10]` | 安全框下限 |
| `DEFAULT_CALIB["max_xyz"]` | `[0.90,0.40,0.80]` | 安全框上限 |
| `DEFAULT_GRASP_RPY` | `[π,0,0]` | 默认抓取姿态（fixed_rpy 的兜底） |

### 18.3 核心公式速查

```
target_i = clamp( (wrist_i − offset_i) × scale_i + add_i , min_xyz[i], max_xyz[i] )   i = x,y,z
pose6    = [target_x, target_y, target_z, fixed_rpy[0], fixed_rpy[1], fixed_rpy[2]]
```

---

*本文档基于 `arm/arm_follow.py`（141 行）撰写；行号以撰写时源码版本为准，代码修改后以最新源码为准。*
