# 14 · holistic_pose.py 全身姿态估计模块详解（人体 → 机械臂 + 灵巧手协同）

> **所属系统**：睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂 + Intel RealSense L515 + MediaPipe Holistic 全身姿态协同控制系统（Windows 版）
> **模块定位**：视觉链路的"全身感知前端"——**一帧推理**同时检测 人体 33 关键点 + 左手/右手各 21 关键点，随后兵分两路：
> - **人体（肩/肘/腕）→ 机械臂 TCP 定位**（人动臂动）；
> - **手部 21 点 → 16 关节角 → 灵巧手**（手势模仿）。
>
> 本模块**不重新实现**手部角度解算，而是"组合"（composition）复用 `vision/hand_pose.py` 的成熟解算链，保证与纯手部模式角度完全一致。
> **源文件**：`RY-H1_vision_mimic/vision/holistic_pose.py`（共 428 行）
> **相关文档**：[07_hand_pose.md](07_hand_pose.md)（手部姿态模块，被本模块复用）、[13_main_gui_arm.md](13_main_gui_arm.md)（臂+手 GUI，本模块是其增强版的数据源）

---

## 0. 数据流总览（先建立全局画面）

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        holistic_pose.py 单帧流水线                           │
│                                                                            │
│  BGR 帧(H,W,3) + 深度图(mm) + 相机内参{fx,fy,ppx,ppy}                       │
│        │                                                                   │
│        ▼                                                                   │
│  bgr2rgb()  BGR→RGB  ──►  mp.Image(SRGB)  ──►  HolisticLandmarker.detect()  │
│        │                                        （holistic_landmarker.task  │
│        ▼                                         一帧一次推理）              │
│  HolisticLandmarkerResult：                                                 │
│    ├─ pose_landmarks(33 点, 归一化)          ← 人体                        │
│    ├─ left_hand_landmarks(21 点)             ← 左手                        │
│    └─ right_hand_landmarks(21 点)            ← 右手                        │
│        │                                                                   │
│        ▼                                                                   │
│  组装 HolisticResult：                                                      │
│    ├─ ① 人体：pose_landmarks ──► _pose_to_3d() ──► pose_3d(相机系,米)       │
│    ├─ ② 手部选边（hand_side 优先级）→ 21 点                                │
│    ├─ ③ 手部解算：组合的 HandPoseEstimator 裸实例                           │
│    │      _convert_landmarks_to_3d() ──► _landmarks_to_angles16()          │
│    │      ──► hand_angles_deg[16] / hand_lateral_dist                      │
│    │      _compute_fist_confidence() ──► hand_fist_confidence              │
│    ├─ ④ 腕部 3D：pose 15/16（或手部 WRIST 兜底）──► wrist_3d              │
│    └─ ⑤ 机械臂映射（可选）：arm_mapper(wrist_3d) ──► arm_target_pose        │
│              │                                                             │
│              ▼                                                             │
│  返回 List[HolisticResult]（0 或 1 个：holistic 最多检测一个人）              │
│        │                                                                   │
│        ▼                                                                   │
│  下游：GUI(main_gui_holistic.py) / test_holistic.py                        │
│    ├─ 腕部→ 机械臂 movel()（人动臂动）                                      │
│    └─ 手部→ 16 关节角→ 灵巧手 move_joints()（手势模仿）                      │
└────────────────────────────────────────────────────────────────────────────┘
```

**两条输出链（本模块最核心的分工）**：

```
                    ┌──────────────────────────────┐
                    │  HolisticLandmarker.detect()  │  ← 一帧一次推理
                    └──────────────────────────────┘
                          │              │
              pose_landmarks(33)   left/right_hand(21×2)
                          │              │
                          ▼              ▼
              ┌────────────────┐  ┌──────────────────────┐
              │  人体链路       │  │  手部链路（复用）     │
              │  _pose_to_3d   │  │  组合 hand_pose 裸实例│
              │  肩/肘/腕 3D   │  │  21点→16关节角        │
              └────────────────┘  └──────────────────────┘
                          │              │
                          ▼              ▼
               wrist_3d (pose 15/16)   hand_angles_deg[16]
                          │              │
                          ▼              ▼
              arm_follow.py         灵巧手 16 舵机
              map_wrist_to_arm_pose
              ──► arm_target_pose
```

---

## 1. 模块 docstring 与整体职责（第 1–33 行）

文件头部是一份完整的"模块说明书"，把它拆开读：

| 段落 | 内容 | 关键信息 |
|---|---|---|
| 功能 1 | MediaPipe HolisticLandmarker（最新 Tasks API + `holistic_landmarker.task`）同时检测 | 人体 33 点（含世界坐标 `pose_world_landmarks`）+ 左手/右手各 21 点 |
| 功能 2 | 人体关键点 → 机械臂 TCP 目标 | 取"右/左手腕"3D 位置 + 肩/肘方向，映射为 `[x,y,z,rx,ry,rz]`；映射逻辑在 `arm/arm_follow.py` 的 `map_wrist_to_arm_pose`（**可单独验证/标定**） |
| 功能 3 | 手部 21 点 → 16 关节角 | **复用** `vision/hand_pose.py` 的角度解算链（内部组合一个 HandPoseEstimator 实例），保证与灵巧手一致；但**检测**由本模块的 HolisticLandmarker 完成 |
| 功能 4 | 输出 HolisticResult | `pose_3d`（相机系米制，含腕部）、`hand_angles_deg[16]`、`hand_lateral_dist`、`hand_fist_confidence`、`arm_target_pose`（可选） |
| 功能 5 | 骨架绘制 | 人体 33 点连线 + 手部 21 点连线（复用 `HAND_CONNECTIONS` / `POSE_CONNECTIONS`） |

**设计说明（docstring 里明确写出的两条铁律）**：

1. **不修改 `vision/hand_pose.py`** —— 原文件保留，仅被"组合使用"（见第 15 节：为什么组合优于修改/复制）。
2. **HolisticLandmarker 是 mediapipe 1.x Tasks API 的新模型**（mediapipe 1.0.1 已验证支持），模型文件 `lib/holistic_landmarker.task` 由用户提供（最新版）。

**用法示例**（docstring 第 26–32 行）：

```python
from vision.holistic_pose import HolisticPoseEstimator, HolisticResult
est = HolisticPoseEstimator()                     # 需 lib/holistic_landmarker.task
results = est.process(rgb_bgr, depth, intrinsics) # 每帧调用
for r in results:
    print(r.hand_angles_deg, r.wrist_3d, r.arm_target_pose)
est.close()
```

> 注意：`process` 返回的是**列表**（与 hand_pose 保持一致），但 holistic 一次最多检测一个人，所以列表长度恒为 0 或 1。

---

## 2. 导入与 MediaPipe 可用性保护（第 35–57 行）

```python
from __future__ import annotations      # 延迟求值类型注解（Python 3.7+）

import logging
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

logger = logging.getLogger("holistic")  # 独立的 logger，便于按模块过滤日志

# 尝试导入 MediaPipe（1.x Tasks API）
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    _MP_OK = True
except ImportError:  # pragma: no cover
    mp = None
    mp_python = None
    mp_vision = None
    _MP_OK = False
```

要点：

- **导入级保护（`_MP_OK` 标志）**：用 `try/except ImportError` 包住 mediapipe 导入。作用与 `hand_pose.py` 完全相同——
  - 环境没装 mediapipe 时，**本模块仍可被 import**（不会一导入就崩），只是 `_MP_OK = False`；
  - 真正的"硬检查"推迟到 `HolisticPoseEstimator.__init__`（第 176–177 行），未安装时抛出带安装指引的 `RuntimeError`；
  - 好处：GUI / 文档 / 其它模块可以在没装库时导入本模块做展示、类型引用等。
- **用的是 MediaPipe 1.x Tasks API 的路径结构**：`mediapipe.tasks.python`（别名 `mp_python`）下取 `BaseOptions`，`mediapipe.tasks.python.vision`（别名 `mp_vision`）下取 `HolisticLandmarkerOptions` / `HolisticLandmarker` / `RunningMode`。
- **与旧版 API 的区别**：不是 `mediapipe.solutions.holistic`（旧版解决方案 API，模型文件是 `.tflite` 且接口完全不同）。Tasks API 用 `.task` 模型文件 + `BaseOptions(model_asset_path=...)` 加载。
- 第 45 行 `logger = logging.getLogger("holistic")`：本模块的日志独立命名空间，便于排查时只开 `holistic` 的日志。

---

## 3. 模型文件配置与搜索（第 59–77 行）

```python
DEFAULT_MODEL_NAME = "holistic_landmarker.task"
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/"
    "holistic_landmarker/float16/1/holistic_landmarker.task"
)
```

- `DEFAULT_MODEL_NAME`：默认模型文件名。与 hand_pose 的 `hand_landmarker.task` 不同，这里是 **`holistic_landmarker.task`**（Google 官方 float16 版）。
- `MODEL_DOWNLOAD_URL`：官方托管地址。模型找不到时，错误信息里会带这个链接提示下载（第 182–183 行）。

### `_find_model_file(model_path=None)`（第 67–77 行）

```python
def _find_model_file(model_path: Optional[str] = None) -> Optional[str]:
    """搜索模型：显式路径 → cwd → 根目录 → lib/ → 本文件目录。"""
    if model_path:
        return model_path if os.path.exists(model_path) else None
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    for d in (os.getcwd(), project_root, os.path.join(project_root, "lib"), here):
        p = os.path.join(d, DEFAULT_MODEL_NAME)
        if os.path.exists(p):
            return p
    return None
```

搜索策略（**优先级从高到低**）：

| 顺序 | 位置 | 说明 |
|---|---|---|
| 0 | `model_path`（显式传入） | 存在即返回，不存在返回 None（**不继续搜其它位置**） |
| 1 | `os.getcwd()`（当前工作目录） | 方便在项目根目录直接运行脚本 |
| 2 | `project_root`（本文件所在目录的上一级） | 即 `RY-H1_vision_mimic/` 根目录 |
| 3 | `project_root/lib/` | 官方推荐的存放目录（与 hand 模型一致） |
| 4 | `here`（本文件所在目录，即 `vision/`） | 最后兜底 |

返回**第一个**命中的路径；全部没找到返回 `None`，由 `__init__` 抛 `RuntimeError`。

> 设计意图：模型文件是"用户提供的外部资产"（几百 MB 级别不随代码分发），所以搜索策略尽量宽松——无论用户把模型放在根目录、lib/ 还是当前目录都能找到，同时允许显式指定任意路径。

---

## 4. 人体姿态关键点常量（第 80–94 行）

```python
# 人体姿态关键点索引（MediaPipe Pose 33 点）
POSE_NOSE = 0
POSE_LEFT_SHOULDER = 11
POSE_RIGHT_SHOULDER = 12
POSE_LEFT_ELBOW = 13
POSE_RIGHT_ELBOW = 14
POSE_LEFT_WRIST = 15
POSE_RIGHT_WRIST = 16
POSE_LEFT_PINKY = 17
POSE_RIGHT_PINKY = 18
POSE_LEFT_INDEX = 19
POSE_RIGHT_INDEX = 20
POSE_LEFT_THUMB = 21
POSE_RIGHT_THUMB = 22
```

MediaPipe Pose 完整 33 点编号见官方 `PoseLandmark` 枚举，本模块只定义**协同控制实际用到**的常量（后续代码用名字而不是魔法数字）：

| 常量 | 索引 | 用途（在本模块中） |
|---|---|---|
| `POSE_NOSE` | 0 | 鼻子（预留，常与肩部构成"朝向"参考） |
| `POSE_LEFT_SHOULDER` | 11 | 左肩：`_pose_to_3d` 参考深度候选点；机械臂姿态估计的可选输入 |
| `POSE_RIGHT_SHOULDER` | 12 | 右肩：同上 |
| `POSE_LEFT_ELBOW` | 13 | 左肘：肩-肘方向（机械臂姿态估计可选输入，见 arm_follow `estimate_pose_from_arm`） |
| `POSE_RIGHT_ELBOW` | 14 | 右肘：同上 |
| `POSE_LEFT_WRIST` | 15 | 左腕：**机械臂 TCP 定位的主用点**（左手控制时） |
| `POSE_RIGHT_WRIST` | 16 | 右腕：**机械臂 TCP 定位的主用点**（右手控制时） |
| `POSE_LEFT_PINKY` | 17 | 左小指（骨架绘制连线用） |
| `POSE_RIGHT_PINKY` | 18 | 右小指 |
| `POSE_LEFT_INDEX` | 19 | 左食指 |
| `POSE_RIGHT_INDEX` | 20 | 右食指 |
| `POSE_LEFT_THUMB` | 21 | 左拇指 |
| `POSE_RIGHT_THUMB` | 22 | 右拇指 |

> 注意：这些是**人体**姿态点（Pose 模型），与**手部** 21 点（Hand 模型）是两套编号体系，不要混淆。手部有自己的 `WRIST=0` 等常量（从 hand_pose 导入，见第 5 节）。

### POSE_CONNECTIONS 骨架连线（第 96–103 行）

```python
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),   # 肩-肘-腕
    (11, 23), (12, 24), (23, 24),                      # 肩-髋
    (15, 17), (15, 19), (15, 21),                      # 左腕-手指
    (16, 18), (16, 20), (16, 22),                      # 右腕-手指
    (23, 25), (25, 27), (24, 26), (26, 28),            # 髋-膝-踝
]
```

这是**简化版**人体骨架（未包含完整 33 点姿势的全部连线），分组含义：

| 组 | 连线 | 含义 |
|---|---|---|
| 肩-肘-腕 | `11-13-15`（左）、`12-14-16`（右） | 上肢主链，`11-12` 为肩部横线 |
| 肩-髋 | `11-23`、`12-24`（躯干侧线）、`23-24`（髋部横线） | 躯干框架 |
| 腕-手指 | `15→17/19/21`（左手）、`16→18/20/22`（右手） | 手腕连到小指/食指/拇指 |
| 髋-膝-踝 | `23-25-27`（左腿）、`24-26-28`（右腿） | 下肢主链 |

> 用途：仅供 `draw_skeleton` 画骨架使用（第 383–389 行）；角度解算完全不需要这些连线（角度由向量夹角法在 hand_pose 内完成）。

---

## 5. 复用 hand_pose 的常量与工具（第 105–110 行）

```python
from .hand_pose import (  # noqa: E402
    HAND_CONNECTIONS,
    INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP, WRIST,
    _angle_between,
)
```

从 `vision/hand_pose.py` 导入：

- `HAND_CONNECTIONS`：手部 21 点骨架连线（画骨架用）；
- `INDEX_TIP / MIDDLE_TIP / RING_TIP / PINKY_TIP / WRIST`：手部关键点索引（`WRIST=0` 用于腕部 3D 兜底，见第 10.7 节；指尖索引用于握拳置信度）；
- `_angle_between`：三维向量夹角（度）。本文件里它被**再导入但不直接调用**（`# noqa: E402` 表明放在 import 区之后是有意的）——真正的角度计算发生在组合的 hand_pose 裸实例内部；这里导入是为了保持与 hand_pose 的接口对齐/便于将来直接调用。

> `# noqa: E402` 是给 flake8 的注释：本 import 位于模块中部（常量定义之后），违反"import 必须放在文件顶部"的 E402 规则，用注释显式豁免。

---

## 6. HolisticResult 结果数据结构（第 113–147 行）

```python
@dataclass
class HolisticResult:
    pose_landmarks: Optional[np.ndarray] = None          # 人体 33 关键点（归一化 (33,3)）
    pose_3d: Optional[np.ndarray] = None                 # 人体 33 关键点（相机系米制 (33,3)，深度补全）
    wrist_3d: Optional[List[float]] = None               # 用于机械臂映射的腕部 3D 坐标（米）
    wrist_side: str = "none"                             # "right"/"left"/"none"
    hand_landmarks: Optional[np.ndarray] = None          # 手部 21 关键点（归一化 (21,3)）
    hand_angles_deg: List[float] = field(default_factory=lambda: [0.0] * 16)  # 16 关节角（度）
    hand_lateral_dist: float = 0.0                       # 拇指横向距离
    hand_fist_confidence: Optional[float] = None         # 深度辅助握拳置信度
    arm_target_pose: Optional[List[float]] = None        # 映射后的机械臂 TCP 目标 [x,y,z,rx,ry,rz]
    confidence: float = 0.0                              # 检测置信度
```

### 字段逐个详解

| 字段 | 类型 | 含义 | 何时为 None / 默认值 |
|---|---|---|---|
| `pose_landmarks` | `(33,3) float64` | 人体 33 关键点，**归一化**坐标 `(x,y,z)`（x,y ∈ [0,1] 相对图像尺寸，z 为相对深度） | 未检测到人体 → None |
| `pose_3d` | `(33,3) float64` | 人体 33 关键点**相机系米制**坐标，由 `_pose_to_3d` 从归一化坐标 + 深度图反投影得到（缺深度用相对 z 补全） | 未检测到人体，或 `intrinsics` 为 None → None |
| `wrist_3d` | `List[float]`（长度 3） | **用于机械臂映射的腕部 3D**（米，相机系）。优先取 pose 15/16，兜底取手部 WRIST | 两者都不可用 → None |
| `wrist_side` | `str` | 当前腕部来自哪一侧：`"right"` / `"left"` / `"none"` | 默认 `"none"` |
| `hand_landmarks` | `(21,3) float64` | 所选手（按 hand_side 选边）的 21 关键点，归一化坐标 | 没有可用的手 → None |
| `hand_angles_deg` | `List[float]`（长度 16） | **16 关节角（度）**，复用 hand_pose 解算链输出，索引约定与 `07_hand_pose.md` 完全一致（0=拇指侧摆、1=拇指近端、2=拇指远端、3/6/9/12=四指侧摆、4/5…=四指近端/远端弯曲、15=拇指内外展） | 默认 `[0.0]*16`（手不可用时保持零角度） |
| `hand_lateral_dist` | `float` | 拇指横向距离（掌宽归一化的绝对投影距离，供 GUI/后处理参考） | 默认 0.0 |
| `hand_fist_confidence` | `float` | 握拳置信度 [0,1]（复用 `_compute_fist_confidence`，深度辅助） | 手不可用或 3D 坐标无效 → None |
| `arm_target_pose` | `List[float]`（长度 6） | **机械臂 TCP 目标** `[x,y,z,rx,ry,rz]`（米/弧度），由 `arm_mapper` 映射得到 | `map_to_arm=False` 或映射失败 → None |
| `confidence` | `float` | 检测置信度（本模块当前保留字段，未由检测结果填充，恒为默认 0.0） | 默认 0.0 |

### 属性（properties，第 141–147 行）

```python
@property
def pose_detected(self) -> bool:
    return self.pose_landmarks is not None

@property
def hand_detected(self) -> bool:
    return self.hand_landmarks is not None
```

两个只读属性，是 GUI/上层判断"人体在不在 / 手在不在"的便捷入口（`main_gui_holistic.py` 第 198–201 行就是用它们拼状态栏文字）。

> 设计要点：
> - 用 `field(default_factory=lambda: [0.0] * 16)` 而不是 `= []`——**避免可变默认值共享**（dataclass 陷阱）：每个实例得到独立的 16 长度列表。
> - 与 `HandResult`（hand_pose）的区别：HolisticResult **没有** `joint_angles_rad` 属性（需要弧度时上层自己 `math.radians` 转换，见 GUI 第 224 行）、**没有** handedness 字段（因为左右手由选边逻辑决定）、**多了** `wrist_3d / wrist_side / arm_target_pose`（机械臂链路专属）。

---

## 7. HolisticPoseEstimator 类总览（第 150–157 行）

```python
class HolisticPoseEstimator:
    """
    MediaPipe Holistic 全身姿态估计器（人体 → 机械臂 + 灵巧手协同）。

    - 用 HolisticLandmarker 检测人体 + 双手（一帧一次推理）；
    - 组合 HandPoseEstimator 复用其 3D 转换与 16 关节角解算（参数一致）；
    - 提供腕部 3D → 机械臂 TCP 映射入口（映射逻辑在 arm/arm_follow.py）。
    """
```

一句话概括类职责：**检测在本类（HolisticLandmarker），解算在组合的 hand_pose 裸实例，映射在 arm_follow**。三个关注点分离，各司其职。

类成员一览：

| 成员 | 类型 | 作用 |
|---|---|---|
| `__init__` | 方法 | 检查环境/模型 → 创建 HolisticLandmarker → 组合 hand_pose 裸实例 |
| `update_params(**kwargs)` | 方法 | 动态更新校准参数，转发给内部手部引擎 |
| `set_hand_side(side)` | 方法 | 切换用于控制灵巧手的手（right/left） |
| `process(...)` | 方法 | 单帧主流水线（检测→人体→手部→角度→腕部→映射） |
| `_pose_to_3d(...)` | 静态方法 | 人体 33 点 → 相机系米制 |
| `draw_skeleton(...)` | 方法 | 双色骨架绘制 |
| `close()` | 方法 | 释放模型资源 |
| 模块级 `bgr2rgb(...)` | 函数 | BGR→RGB 通道交换 |
| `model_path` | 属性 | 模型文件路径 |
| `hand_side` | 属性 | 当前选边（"right"/"left"） |
| `use_hand_pose` | 属性 | 是否启用组合手部引擎 |
| `_landmarker` | 属性 | HolisticLandmarker 实例 |
| `_hand_engine` | 属性 | 组合的 HandPoseEstimator **裸实例**（None=未启用） |

---

## 8. __init__：模型加载与"组合 hand_pose 裸实例"（第 159–215 行）

### 8.1 构造参数全表

```python
def __init__(
    self,
    use_hand_pose: bool = True,          # 是否组合手部引擎（False 则只做人体链路）
    hand_side: str = "right",            # 用哪只手控制灵巧手："right"/"left"
    model_path: Optional[str] = None,    # holistic 模型文件路径（None=自动搜索）
    bend_scale: float = 1.0,             # ↓ 以下全部是"手部 16 关节角"校准参数，
    bend_offset: float = 0.0,            #   与 hand_pose.HandPoseEstimator 同名参数
    bend_gain: float = 1.0,              #   一一对应，会被原样设置到组合的裸实例上
    deadzone_deg: float = 1.0,           #   保证两种模式角度输出一致
    bend_reverse: bool = False,
    per_finger_scale: Optional[dict] = None,
    per_finger_offset: Optional[dict] = None,
    thumb_abd_offset: float = 0.0,
    thumb_abd_gain: float = 0.8,
    thumb_abd_reverse: bool = False,
    swing_reverse: bool = False,
):
```

参数分三组理解：

| 组 | 参数 | 作用 |
|---|---|---|
| **运行开关** | `use_hand_pose` | 是否组合手部引擎。`False` 时本模块退化为"纯人体→机械臂"链路（省去手部解算开销），`_hand_engine` 保持 None |
| **选边** | `hand_side` | 用哪只手控制灵巧手：`"right"`（默认）/ `"left"`。**注意内部会 `.lower()` 归一化**（第 186 行） |
| **手部校准**（转发给裸实例） | `bend_scale / bend_offset / bend_gain / deadzone_deg / bend_reverse / per_finger_scale / per_finger_offset / thumb_abd_offset / thumb_abd_gain / thumb_abd_reverse / swing_reverse` | 与 `hand_pose.HandPoseEstimator.__init__` 同名的校准参数，语义 100% 一致（详见 07_hand_pose.md 第 5 节"完整校准链"）。传进来就是为了一帧初始化时直接把整套校准搬进裸实例 |

> 注意 `per_finger_swing_offset`（逐指侧摆偏移）：本构造器**不接收**它，裸实例上直接置为 `{}`（第 210 行）——如需侧摆校准请在运行期调 `update_params(per_finger_swing_offset={...})`。

### 8.2 前置检查（第 176–184 行）

```python
if not _MP_OK:
    raise RuntimeError("请安装 mediapipe>=0.10.14：pip install mediapipe")

model_file = _find_model_file(model_path)
if model_file is None:
    raise RuntimeError(
        f"未找到 holistic 模型文件 {DEFAULT_MODEL_NAME}。请放到项目根目录或 lib/：\n"
        f"  {MODEL_DOWNLOAD_URL}"
    )
self.model_path = model_file
self.hand_side = hand_side.lower()
self.use_hand_pose = use_hand_pose
```

两道硬检查：

1. **mediapipe 是否可导入**（`_MP_OK`）——否则报安装指引（注意这里提示 `>=0.10.14` 是兼容性下限，1.x Tasks API 在 0.10.14+ 均可，官方文档验证过 1.0.1）；
2. **模型文件是否存在**——`_find_model_file` 找不到就报错，并**直接给出官方下载 URL**，方便用户自助解决（这是最常见的启动失败原因，见第 16 节 FAQ）。

### 8.3 创建 HolisticLandmarker（Tasks API，第 189–195 行）

```python
# 创建 HolisticLandmarker（Tasks API）
base_options = mp_python.BaseOptions(model_asset_path=model_file)
options = mp_vision.HolisticLandmarkerOptions(
    base_options=base_options,
    running_mode=mp_vision.RunningMode.IMAGE,
)
self._landmarker = mp_vision.HolisticLandmarker.create_from_options(options)
```

- `BaseOptions(model_asset_path=...)`：Tasks API 的统一"模型资产"入口（指定 `.task` 文件路径）。
- `HolisticLandmarkerOptions`：只显式配置了两项——
  - `base_options`：模型资产；
  - `running_mode=RunningMode.IMAGE`：**同步单帧模式**（每次调用 `detect()` 独立推理一帧，无跨帧跟踪）。
- **没有配置的参数**（全部用官方默认值）：`min_face_detection_confidence`、`min_face_presence_confidence`、`min_pose_detection_confidence`、`min_pose_presence_confidence`、`min_hand_landmarks_confidence`、`output_face_blendshapes`（默认 False）、`output_segmentation_mask`（默认 False）、`result_callback`（仅 VIDEO/LIVE_STREAM 模式需要）。
- **关键差异：HolisticLandmarkerOptions 没有 `num_hands` 参数**（那是 `HandLandmarkerOptions` 专属的）。Holistic 模型固定输出"左/右两个手部通道"（`left_hand_landmarks` / `right_hand_landmarks`），不会出现"检测到 N 只手"的概念——这也是为什么本模块的选边逻辑（第 10.5 节）是在**两个固定通道里选一个**，而不是像 hand_pose 那样遍历手列表。

### 8.4 组合 hand_pose 裸实例（第 197–215 行）——本模块最精妙的设计

```python
# 组合 HandPoseEstimator 复用角度解算（懒创建，避免加载手部模型）
self._hand_engine = None
if use_hand_pose:
    from .hand_pose import HandPoseEstimator
    # 通过 __new__ 创建"裸实例"：不加载 hand 模型，只复用其角度解算方法
    self._hand_engine = object.__new__(HandPoseEstimator)
    self._hand_engine.bend_scale = bend_scale
    self._hand_engine.bend_offset = bend_offset
    self._hand_engine.bend_gain = max(0.1, float(bend_gain))
    self._hand_engine.deadzone_deg = float(deadzone_deg)
    self._hand_engine.bend_reverse = bool(bend_reverse)
    self._hand_engine.per_finger_scale = dict(per_finger_scale or {})
    self._hand_engine.per_finger_offset = dict(per_finger_offset or {})
    self._hand_engine.per_finger_swing_offset = {}
    self._hand_engine.swing_reverse = bool(swing_reverse)
    self._hand_engine.thumb_abd_offset = float(thumb_abd_offset)
    self._hand_engine.thumb_abd_gain = max(0.1, float(thumb_abd_gain))
    self._hand_engine.thumb_abd_reverse = bool(thumb_abd_reverse)
    self._hand_engine._frame_scale = 1.0
```

#### 为什么 `object.__new__(HandPoseEstimator)` 能绕过模型加载？

Python 的对象创建分两步：

1. `__new__(cls)` —— 分配内存、返回一个"空壳实例"；
2. `__init__(self, ...)` —— 初始化实例状态。

`HandPoseEstimator.__init__`（见 hand_pose.py 第 122–178 行）里做的事包括：检查 `_MP_OK` → `_find_model_file` 找 `hand_landmarker.task` → **`HandLandmarker.create_from_options` 加载手部模型** → 设置一堆校准属性。

**`object.__new__(HandPoseEstimator)` 只做第 1 步**：得到一个"裸实例"，`__init__` 完全没执行，所以：

- ❌ 不会去找 `hand_landmarker.task`；
- ❌ 不会加载第二份模型（**省内存、省启动时间**）；
- ✅ 但方法（`_landmarks_to_angles16`、`_convert_landmarks_to_3d`、`_compute_fist_confidence`）作为类的一部分**天然存在**，不需要实例化也能调用。

这就是"组合（composition）而非重复实现"的落地手段：**检测模型只需要 holistic 一份，手部解算只是"借用方法"**。

#### 为什么这样是安全的？——裸实例需要哪些属性

手部解算的三个方法对实例属性的依赖各不相同：

| 方法 | 是否静态 | 依赖的实例属性 | 说明 |
|---|---|---|---|
| `_convert_landmarks_to_3d` | ✅ 静态方法 | **无** | 只用入参 `landmarks_norm / depth / intrinsics`，裸实例直接可调 |
| `_compute_fist_confidence` | ✅ 静态方法 | **无** | 只用入参 |
| `_landmarks_to_angles16` | ❌ 实例方法 | **全部校准属性** | 见下 |

`_landmarks_to_angles16`（hand_pose.py 第 358–540 行）内部读取的属性清单（逐行核对过）：

| 属性 | 用途（在角度解算中） |
|---|---|
| `self.bend_scale` | 全局弯曲缩放（第 476/520 行：`theta = theta_raw * bend_scale + bend_offset`） |
| `self.bend_offset` | 全局弯曲偏移 |
| `self.bend_gain` | 全局弯曲增益（乘积） |
| `self.deadzone_deg` | 死区：小于该角度的弯曲直接置 0（滤除微颤） |
| `self.bend_reverse` | 弯曲反向（90−θ / 75−θ） |
| `self.per_finger_scale` | 每指独立缩放（键："thumb"/"index"/…） |
| `self.per_finger_offset` | 每指独立偏移 |
| `self.per_finger_swing_offset` | 每指侧摆偏移（第 433 行 `swing = angle_deg - offset`） |
| `self.swing_reverse` | 侧摆反向 |
| `self.thumb_abd_offset` | 拇指内外展偏移 |
| `self.thumb_abd_gain` | 拇指内外展增益 |
| `self.thumb_abd_reverse` | 拇指内外展反向 |

所以 `__init__` 第 203–215 行**精确地**把这 12 个属性 + 兼容属性 `_frame_scale`（预留字段，当前任何解算都不读它，保留是为了与 hand_pose 实例的属性面完全一致）都设置好了。只要这些属性在，`_landmarks_to_angles16` 就能正常跑完整个校准链——**与模型加载完全无关**。

> 一句话总结机制：**裸实例 = "跳过模型加载的 __init__ + 手工补齐解算所需属性"**。因为解算方法是纯数学（向量夹角法），不依赖任何模型/检测状态，所以这套"借壳"方案是安全且高效的。

#### 与直接实例化的区别（对比表）

| 维度 | `object.__new__(HandPoseEstimator)`（本模块采用） | `HandPoseEstimator(...)`（直接实例化） |
|---|---|---|
| 模型加载 | **不加载**任何手部模型 | 加载 `hand_landmarker.task`（第二份模型） |
| 对 hand 模型文件的要求 | **不需要** hand 模型存在 | 必须存在，否则 `RuntimeError` |
| 内存/启动开销 | 仅几个浮点属性 | 一份完整模型（数 MB~数十 MB）+ 推理图 |
| 检测职责 | 本模块 HolisticLandmarker 负责 | 自己还要能 detect（本模块用不上） |
| 校准参数 | 构造器显式传入并逐个赋值 | `__init__` 参数自带 |
| 风险 | 若 hand_pose 未来在方法里新增依赖属性，可能缺属性（AttributeError）——这是"借用"方案的耦合点 | 无此风险 |

> **取舍**：直接实例化更"正规"但白白多加载一份模型；裸实例省资源但隐式耦合了 hand_pose 方法的内部属性面。注释里已写明"懒创建，避免加载手部模型"，这是经过权衡的刻意选择。为降低裸实例耦合风险，建议保持 `hand_pose.py` 的 `_landmarks_to_angles16` 只依赖校准属性、不新增依赖（详见第 15 节"设计约束"）。

#### 8.5 参数保险（第 205/213 行的 `max(0.1, ...)`）

```python
self._hand_engine.bend_gain = max(0.1, float(bend_gain))
...
self._hand_engine.thumb_abd_gain = max(0.1, float(thumb_abd_gain))
```

两个"增益"参数被强制下限 0.1——与 `hand_pose.py` 的 `__init__`（第 167/177 行）行为完全一致。原因：**增益为 0 会把所有角度乘以 0 变成恒 0°**（误配置时看似"死机"），0.1 下限保证即使输入 0 也保留最小响应，属于防御性编程。

---

## 9. update_params 与 set_hand_side（第 217–228 行）

```python
def update_params(self, **kwargs):
    """动态更新参数（同步给内部手部引擎）。"""
    if self._hand_engine is not None:
        self._hand_engine.update_params(**kwargs)
    for k, v in kwargs.items():
        if k == "hand_side":
            self.hand_side = str(v).lower()

def set_hand_side(self, side: str):
    """切换用于控制灵巧手的手（right/left）。"""
    self.hand_side = str(side).lower()
```

- `update_params`：**透传给内部手部引擎**（`_hand_engine.update_params(**kwargs)`）。hand_pose 的 `update_params` 支持 `bend_scale / bend_offset / bend_gain / deadzone_deg / bend_reverse / per_finger_scale / per_finger_offset / thumb_abd_* / per_finger_swing_offset / swing_reverse`（并显式忽略 `use_distance_ratio`，见 hand_pose.py 第 193–195 行）。**这正是 GUI 校准联动的基础**：上层把校准滑条的值调进来，内部引擎与 hand_pose 模式收到**完全相同的参数**，输出角度自然一致。
- 额外拦截 `hand_side` 键：校准参数之外，本模块独有的"选边"参数也走同一个入口。
- `set_hand_side`：专门给 GUI 的"左手/右手"下拉框用（`main_gui_holistic.py` 第 162 行 `self.holistic.set_hand_side(self.holistic_side_var.get())`），运行中随时换手，无需重建估计器。

---

## 10. process：单帧七步流水线（第 230–318 行）

### 10.1 签名与参数

```python
def process(
    self,
    rgb_bgr: np.ndarray,                 # BGR 帧 (H,W,3)
    depth: Optional[np.ndarray] = None,  # 深度帧（可选，mm）
    intrinsics: Optional[dict] = None,   # 相机内参 {fx,fy,ppx,ppy}（可选）
    map_to_arm: bool = False,            # 是否把腕部 3D 映射为机械臂 TCP（需 arm_mapper）
    arm_mapper=None,                     # arm/arm_follow.py 的映射器（callable: wrist_3d -> pose6）
) -> List[HolisticResult]:
```

- `rgb_bgr`：**BGR** 顺序（OpenCV 惯例），函数内部转 RGB 交给 MediaPipe。
- `depth`：毫米深度图，与 RGB 同尺寸。可选——不传时 3D 恢复退化为"相对深度补全"（精度下降，但角度解算仍可用）。
- `intrinsics`：针孔内参 `{fx, fy, ppx, ppy}`。**手部链路缺它仍能算**（hand_pose 的 `_convert_landmarks_to_3d` 用默认 640×480 反投影，见 hand_pose.py 第 222 行）；但**人体链路缺它则 `_pose_to_3d` 直接返回 None**（见第 11 节）。
- `map_to_arm` / `arm_mapper`：机械臂映射开关与映射器。`arm_mapper` 是**鸭子类型 callable**（`wrist_3d -> pose6`），GUI 里传的就是 `self.follower.map_wrist_to_arm_pose`（`main_gui_holistic.py` 第 188 行）。不强制类型、不强依赖 ArmFollower 类，**任何"腕部 3D → 6 位姿"的可调用对象都能接进来**（便于单独测试/替换映射器）。

### 10.2 第 0 步：空帧检查 + 预处理（第 249–254 行）

```python
if rgb_bgr is None:
    return []
rgb = bgr2rgb(rgb_bgr)
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(rgb))
res = self._landmarker.detect(mp_image)
```

- `rgb_bgr is None` → 直接返回空列表（安全边界）。
- `bgr2rgb`：通道交换（BGR→RGB），因为 MediaPipe 期望 RGB。
- `np.ascontiguousarray`：**强制 C 连续内存布局**——MediaPipe 的 `Image` 对 numpy 数组的内存布局有要求，非连续视图（如切片）会报错。
- `mp.Image(SRGB, data=...)`：封装成 MediaPipe 图像对象。
- `self._landmarker.detect(mp_image)`：**执行检测**，返回 `HolisticLandmarkerResult`（字段：`face_landmarks`、`pose_landmarks`、`pose_world_landmarks`、`left_hand_landmarks`、`left_hand_world_landmarks`、`right_hand_landmarks`、`right_hand_world_landmarks`、`face_blendshapes`、`segmentation_mask`）。本模块只用 `pose_landmarks` 与 `left/right_hand_landmarks` 三个归一化坐标通道；`pose_world_landmarks` 虽然检测出来了但**不用**——本模块的 3D 恢复走自己的深度反投影（第 11 节），因为世界坐标是模型估算值、不如 L515 深度真实。

### 10.3 第 1 步：人体关键点（第 262–267 行）

```python
# ---- 1. 人体关键点 ----
if res.pose_landmarks:
    pts_norm = np.array([(p.x, p.y, p.z) for p in res.pose_landmarks],
                        dtype=np.float64)
    r.pose_landmarks = pts_norm
    r.pose_3d = self._pose_to_3d(pts_norm, depth, intrinsics)
```

- `res.pose_landmarks` 存在（检测到人体）→ 把 33 个 `NormalizedLandmark` 转成 `(33,3) float64` 数组存入 `pose_landmarks`；
- 立即调用 `_pose_to_3d` 生成相机系米制 `pose_3d`（深度补全细节见第 11 节）；
- 注意 `pts_norm` 的 z 分量是 MediaPipe 的**相对深度**（相对髋部中心，单位约为米），不是真实距离。

### 10.4 第 2 步：手部选边（第 269–283 行）——优先级逻辑详解

```python
# ---- 2. 手部关键点（选一只手控制灵巧手） ----
hand_pts_norm = None
side = "none"
if self.hand_side == "left" and res.left_hand_landmarks:
    hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.left_hand_landmarks],
                             dtype=np.float64)
    side = "left"
elif self.hand_side == "right" and res.right_hand_landmarks:
    hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.right_hand_landmarks],
                             dtype=np.float64)
    side = "right"
elif res.right_hand_landmarks:  # 兜底：默认优先右手
    hand_pts_norm = np.array([(p.x, p.y, p.z) for p in res.right_hand_landmarks],
                             dtype=np.float64)
    side = "right"
```

**判定优先级（自上而下，命中即停）**：

| 优先级 | 条件 | 结果 |
|---|---|---|
| 1 | `hand_side == "left"` **且** 检测到左手 | 用**左手**，`side="left"` |
| 2 | `hand_side == "right"` **且** 检测到右手 | 用**右手**，`side="right"` |
| 3（兜底） | 只要检测到右手 | 用**右手**，`side="right"`（即使配置是 left 且左手没检测到） |

几个**容易踩坑的行为**要讲清楚：

1. **兜底只朝右**：如果配置 `hand_side="left"` 但左手没检测到、右手检测到了 → 走第 3 分支**用右手**（`side="right"`，腕部也会跟着变右侧）。这是刻意的"默认优先右手"（与灵巧手默认为右手习惯一致）。
2. **左手永远不会兜底**：配置 `hand_side="right"` 但右手没检测到、左手检测到了 → 前两个分支都不中，第 3 分支 `res.right_hand_landmarks` 为假 → `hand_pts_norm` 保持 None，**本帧手部链路为空**（宁可不用左手，也不违背用户"用右手"的显式配置）。
3. **左右手标签是 MediaPipe 按"图像视角"给出的**：`left_hand_landmarks` 是"画面中的人体左手"。如果操作者**正对相机**，画面中的左手对应**操作者自己的右手**（镜像问题）——所以 GUI 里的 hand_side 下拉要按实际镜像关系配置（见第 16 节 FAQ 之四）。

### 10.5 第 3 步：手部角度解算（第 285–293 行）

```python
r.hand_landmarks = hand_pts_norm
if hand_pts_norm is not None and self._hand_engine is not None:
    real_pts = self._hand_engine._convert_landmarks_to_3d(
        hand_pts_norm, depth, intrinsics)
    angles, lateral = self._hand_engine._landmarks_to_angles16(real_pts)
    r.hand_angles_deg = angles
    r.hand_lateral_dist = lateral
    r.hand_fist_confidence = self._hand_engine._compute_fist_confidence(
        hand_pts_norm, real_pts)
```

- 条件：选到手（`hand_pts_norm` 非 None）**且**组合引擎存在（`use_hand_pose=True`）。
- 复用链（全部来自 hand_pose 裸实例）：
  1. `_convert_landmarks_to_3d`：归一化 21 点 → 相机系米制（手腕深度锚定 + 相对深度补全，详见 07_hand_pose.md 第 6 节）；
  2. `_landmarks_to_angles16`：3D 坐标 → **16 关节角 + 拇指横向距离**（向量夹角法 + 完整校准链）；
  3. `_compute_fist_confidence`：握拳置信度 [0,1]。
- 输出写入 `hand_angles_deg / hand_lateral_dist / hand_fist_confidence`。
- **这就是第 0 节数据流图里"手部→hand_pose 解算"分支的落地点**：检测是 holistic 的，解算是 hand_pose 的。

### 10.6 第 4 步：腕部 3D（第 295–308 行）

```python
# ---- 3. 腕部 3D（机械臂映射用） ----
wrist_pose_idx = POSE_RIGHT_WRIST if side == "right" else POSE_LEFT_WRIST
# 优先用所选手的腕部（pose 15/16），若人体未检测到则回退手部 WRIST
if r.pose_3d is not None and wrist_pose_idx < len(r.pose_3d):
    w3d = r.pose_3d[wrist_pose_idx]
    if np.all(np.isfinite(w3d)):
        r.wrist_3d = [float(v) for v in w3d]
        r.wrist_side = side
if r.wrist_3d is None and hand_pts_norm is not None and self._hand_engine is not None:
    real_pts = self._hand_engine._convert_landmarks_to_3d(
        hand_pts_norm, depth, intrinsics)
    if real_pts is not None and np.all(np.isfinite(real_pts[WRIST])):
        r.wrist_3d = [float(v) for v in real_pts[WRIST]]
        r.wrist_side = side
```

两层兜底逻辑：

1. **主用：人体 pose 腕部**。`wrist_pose_idx = 16`（右手控制）或 `15`（左手控制；**注意 `side=="none"` 时也走 15=左腕**，因为条件只看 `side=="right"`）。从 `pose_3d` 取该点，要求**所有分量有限**（`np.isfinite` 全真）才采用——防止深度补全产生的 NaN/Inf 污染机械臂目标。
2. **兜底：手部 WRIST 关键点**。人体链路不可用（`pose_3d` 为 None 或该点非有限）时，用所选手的 21 点里的 `WRIST`（索引 0）的 3D 坐标——手部 `_convert_landmarks_to_3d` 同样做深度反投影，结果同为相机系米制。

> 为什么要有这一层？因为"人体检测"和"手部检测"在 Holistic 里可能不同时成功（手更靠近/更大，有时手检测到了但人体姿态质量差）。用 pose 腕部优先是因为它**属于完整人体骨架**（与肩/肘同坐标系、同一次 `_pose_to_3d` 补全），一致性更好；手部 WRIST 兜底保证"只有手也能联动机械臂"。

### 10.7 第 5 步：机械臂 TCP 映射（第 310–315 行）

```python
# ---- 4. 机械臂 TCP 映射 ----
if map_to_arm and arm_mapper is not None and r.wrist_3d is not None:
    try:
        r.arm_target_pose = arm_mapper(r.wrist_3d)
    except Exception as exc:
        logger.warning("arm mapper 异常: %s", exc)
```

- 三个条件缺一不可：开关打开、映射器存在、腕部 3D 可用。
- `arm_mapper(r.wrist_3d)` 返回 6 元位姿 `[x,y,z,rx,ry,rz]` 存入 `arm_target_pose`。
- **异常隔离**：映射器抛任何异常只记 `logger.warning`，不影响整帧结果（`arm_target_pose` 保持 None）——视觉链路不能因为映射配置错误而崩掉。
- 实际映射器即 `ArmFollower.map_wrist_to_arm_pose`（arm_follow.py 第 77–91 行）：`target_i = (wrist_i − offset_i) × scale_i + add_i`，再裁剪到 `[min_xyz, max_xyz]` 安全区间，姿态取 `fixed_rpy`（默认"朝下抓取"）。offset/scale/add 由 GUI 标定（`main_gui_holistic.py` 第 166–175 行 `follower.update_calib(...)`）。

### 10.8 收尾与边界情况（第 256–260、317–318 行）

```python
out: List[HolisticResult] = []
# holistic 最多检测一个人体；构造单结果
r = HolisticResult()
if not res.pose_landmarks and not (res.left_hand_landmarks or res.right_hand_landmarks):
    return out
...
out.append(r)
return out
```

- **早退**：人体和双手都没检测到 → 直接返回空列表 `[]`（不浪费后续计算）。
- 恒返回 **0 或 1 个**结果（holistic 单人体语义）；调用方取 `results[0]` 前应判空（GUI 第 193–196 行就是先判空再取）。

---

## 11. _pose_to_3d：人体 33 点 → 相机系米制（第 320–364 行）

```python
@staticmethod
def _pose_to_3d(
    pts_norm: np.ndarray,
    depth: Optional[np.ndarray],
    intrinsics: Optional[dict],
) -> Optional[np.ndarray]:
    """人体 33 关键点 → 相机系米制 3D（深度优先，缺深度用相对 z 补全）。"""
```

### 11.1 输入与默认值（第 328–334 行）

```python
n = len(pts_norm)
if intrinsics is None:
    return None
fx, fy = intrinsics.get("fx", 640.0), intrinsics.get("fy", 640.0)
ppx, ppy = intrinsics.get("ppx", 320.0), intrinsics.get("ppy", 240.0)
h = depth.shape[0] if depth is not None else 480
w = depth.shape[1] if depth is not None else 640
```

- **`intrinsics` 缺失直接返回 None**（人体链路硬依赖内参；与手部链路"缺内参仍可用默认值"的策略不同——人体用于机械臂定位，精度要求更高，宁可报 None 也不给错误坐标）。
- 内参用 `.get(key, 默认)` 容错：缺哪个键用 640×480 视场的默认值。
- 图像尺寸：优先取深度图尺寸，否则 480×640（与 L515 输出一致）。

### 11.2 参考深度：髋部或肩部（第 337–348 行）

```python
# 参考深度：髋部中点（pose 23/24 平均）或肩部
ref_z = 800.0
if depth is not None:
    for idx in (23, 24, 11, 12):
        if idx < n:
            u = int(pts_norm[idx][0] * w)
            v = int(pts_norm[idx][1] * h)
            if 0 <= v < h and 0 <= u < w:
                zz = float(depth[v, u])
                if 0 < zz < 3000:
                    ref_z = zz
                    break
```

- `ref_z` 默认 800mm（经验值），**深度图可用时**按顺序探测候选点：`23`（左髋）、`24`（右髋）、`11`（左肩）、`12`（右肩）——**躯干中心区域**最不容易被手/手臂遮挡，深度可信度最高。
- 命中条件：像素在图像内、深度值在 `(0, 3000)mm` 有效区间（L515 有效量程）→ 取第一个命中即 `break`。
- `ref_z` 的用途：当某个关键点没有有效深度时，用它 + 相对深度推算出补全深度（见下）。

### 11.3 逐点反投影 + 深度补全（第 349–363 行）

```python
for i, (nx, ny, rel_z) in enumerate(pts_norm):
    u, v = nx * w, ny * h
    z_mm = 0.0
    if depth is not None:
        ui, vi = int(round(u)), int(round(v))
        if 0 <= vi < h and 0 <= ui < w:
            z_mm = float(depth[vi, ui])
    if not (0 < z_mm < 3000):
        z_mm = ref_z + float(rel_z) * 300.0  # 相对深度粗补全
        if z_mm < 100:
            z_mm = 100.0
    z = z_mm / 1000.0
    x = (u - ppx) * z / fx
    y = (v - ppy) * z / fy
    pts_3d[i] = [x, y, z]
```

**核心逻辑（深度优先 + 补全）**：

1. **深度优先**：每个关键点先到深度图上采样真实深度 `z_mm`（就近取整到像素，越界/无效跳过）；
2. **有效性判据**：`0 < z_mm < 3000`（毫米）。无效（0、越界、≥3000 即超出 L515 量程）→ 进入补全分支；
3. **相对深度补全**：`z_mm = ref_z + rel_z × 300.0`
   - `rel_z` 是 MediaPipe Pose 输出的**相对深度**（相对髋部中心，方向：负值=更靠近相机/更前）；
   - `×300.0` 是经验缩放系数（把模型相对深度放大到毫米量级，与真实人体前后位移量级匹配）；
   - 下限 `100mm`：防止补全出负深度/过近深度。
4. **针孔反投影**（毫米→米）：
   - `z = z_mm / 1000.0`（毫米转米）；
   - `x = (u − ppx) × z / fx`（像素横坐标 → 相机系 X）；
   - `y = (v − ppy) × z / fy`（像素纵坐标 → 相机系 Y）。
   - 这是标准的针孔相机模型：`X = (u−cx)·Z/fx`，`Y = (v−cy)·Z/fy`，Z 为深度。

> **与 hand_pose 的 `_convert_landmarks_to_3d` 对比**：两者都是"深度优先 + 相对深度补全 + 针孔反投影"，但锚定策略不同——手部以**手腕深度**为锚（`wrist_z_mm`，默认 600mm，缩放系数 0.5），人体以**髋/肩深度**为锚（`ref_z`，默认 800mm，缩放系数 300）。系数差异是因为 Pose 与 Hand 两套模型的 `rel_z` 尺度不同，各自按其模型特性标定，**不要互相套用**。

### 11.4 返回值

- 成功：`(n,3) float64` 相机系米制坐标（与 `pose_landmarks` 逐点对应）；
- `intrinsics is None`：返回 `None`（调用方据此走手部 WRIST 兜底）。

---

## 12. draw_skeleton：人体 + 手部双色骨架（第 366–403 行）

```python
def draw_skeleton(
    self,
    frame: np.ndarray,
    results: Sequence[HolisticResult],
    pose_color=(0, 255, 0),     # 人体：绿色
    hand_color=(0, 255, 255),   # 手部：黄色
    line_px: int = 2,
) -> np.ndarray:
```

绘制逻辑（注意 BGR 颜色顺序）：

| 对象 | 连线 | 颜色 | 关节圆点 | 半径 |
|---|---|---|---|---|
| 人体 | `POSE_CONNECTIONS`（11 条） | 绿 `(0,255,0)` | 红 `(0,0,255)` | 3px |
| 手部 | `HAND_CONNECTIONS`（21 条） | 黄 `(0,255,255)` | 品红 `(255,0,255)` | 3px |

细节：

- **只画 `results[0]`**（第 381 行 `r = results[0]`）——与"单人体"语义一致；
- 归一化坐标 → 像素：`x*w`、`y*h` 取整；
- 连线用抗锯齿 `cv2.LINE_AA`；
- 返回**拷贝**（`frame.copy()`），不污染原帧；
- `import cv2` 放在方法内部（延迟导入）：本模块主链路不依赖 OpenCV，只有画图时才需要，避免无谓的导入开销。

---

## 13. close 与 bgr2rgb（第 405–417 行）

```python
def close(self):
    """释放模型资源。"""
    if self._landmarker is not None:
        try:
            self._landmarker.close()
        except Exception:
            pass
    self._landmarker = None
```

- 调用 Tasks API 的 `close()` 释放底层推理资源，`try/except` 吞异常保证幂等（重复 close 不炸）；
- 置 `None` 标记已释放；
- GUI 停止按钮（`main_gui_holistic.py` 第 149–155 行 `_holistic_stop`）和自测都会调用。

```python
def bgr2rgb(bgr: np.ndarray) -> np.ndarray:
    """BGR → RGB。"""
    return bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr
```

- `[:, :, ::-1]` 反转第三维（通道序），`.copy()` 保证返回**连续新数组**（防止负步长视图传入 MediaPipe 出问题）；
- 非 3 通道（灰度/异常输入）原样返回——防御性。

---

## 14. __main__ 自测入口（第 420–428 行）

```python
if __name__ == "__main__":
    # 自测：模型加载 + 空帧处理（不接摄像头）
    est = HolisticPoseEstimator()
    print("HolisticPoseEstimator loaded OK")
    empty = np.zeros((480, 640, 3), dtype=np.uint8)
    res = est.process(empty)
    print(f"空帧结果数: {len(res)}（应为 0）")
    est.close()
    print("自测通过")
```

自测内容（纯软件，不接硬件）：

1. **模型加载**：`HolisticPoseEstimator()` 成功 → 说明 mediapipe 可导入 + `holistic_landmarker.task` 找到了；
2. **空帧处理**：全黑帧 → `process` 返回 `[]`（检测不到人体/手 → 早退路径）——验证空输入不会崩；
3. 释放资源、打印"自测通过"。

> 运行方式：`python vision/holistic_pose.py`（需先保证模型文件就位）。更完整的单项验证见 `apps/test_holistic.py`（支持相机/图片/实时骨架显示）。

---

## 15. 与 hand_pose.py 的关系：复用 vs 重复，为什么这样设计

### 15.1 复用清单（本模块从 hand_pose 拿来什么）

| hand_pose 资产 | 类型 | 本模块用途 |
|---|---|---|
| `HAND_CONNECTIONS` | 常量 | 手部骨架绘制 |
| `INDEX_TIP/MIDDLE_TIP/RING_TIP/PINKY_TIP/WRIST` | 常量 | 握拳置信度、腕部兜底 |
| `_angle_between` | 函数 | 再导入（内部解算在裸实例里用） |
| `HandPoseEstimator._convert_landmarks_to_3d` | 静态方法 | 手部 21 点 → 相机系米制 |
| `HandPoseEstimator._landmarks_to_angles16` | 实例方法 | 3D → 16 关节角 + 横向距离 |
| `HandPoseEstimator._compute_fist_confidence` | 静态方法 | 握拳置信度 |
| `HandPoseEstimator.update_params` | 实例方法 | 校准参数动态更新转发 |

**没有重复实现**的东西：16 关节角的向量夹角法、校准链、3D 反投影、握拳置信度——全部是"借"的。

### 15.2 为什么用"组合裸实例"而不是其它方案？

| 备选方案 | 问题 | 结论 |
|---|---|---|
| **复制一份角度代码到本模块** | 两套代码漂移：改 hand_pose 的校准链，holistic 模式角度就对不上，排查成本翻倍 | ❌ 不采用 |
| **直接 `HandPoseEstimator()` 实例化** | 白白加载第二份 `hand_landmarker.task` 模型（内存、启动时间翻倍），且要求 hand 模型文件也必须存在——而 holistic 场景本不需要它 | ❌ 不采用 |
| **继承 `HandPoseEstimator`** | 继承会带入 `__init__` 的模型加载逻辑（除非重写 __init__，绕一大圈）；语义上也说不过去——HolisticPoseEstimator **不是**一种 HandPoseEstimator | ❌ 不采用 |
| **组合裸实例（`object.__new__` + 手工赋值）** | 只复用"纯数学方法"，模型只加载 holistic 一份；校准参数构造期注入，运行期 `update_params` 同步 | ✅ **采用** |

核心原则一句话：**角度解算的唯一事实来源（single source of truth）是 `hand_pose.py`；holistic 模式只是换了一个"检测器"（HolisticLandmarker），解算完全复用，因此两种模式的 16 关节角在任何校准参数下都严格一致。**

### 15.3 设计约束（使用裸实例的代价）

裸实例与 hand_pose 的 `_landmarks_to_angles16` 形成**隐式契约**：该方法读取的属性集合（`bend_scale` 等 12 个，见第 8.4 节表格）必须全部存在。因此：

- **修改 hand_pose 时**：若给 `_landmarks_to_angles16` 增加新的属性依赖，必须同步在 `holistic_pose.__init__` 里补赋值，否则 holistic 模式会 `AttributeError`；
- 这是"组合复用"的固有耦合点，属于可接受的设计债（换来的是零重复代码 + 双模式一致）。

### 15.4 与 GUI 的联动（校准如何传导）

`gui/main_gui_holistic.py` 的联动点（已核对源码）：

| GUI 操作 | 调用 | 作用 |
|---|---|---|
| 启动协同（第 139 行） | `HolisticPoseEstimator(hand_side=self.holistic_side_var.get())` | 按当前"左手/右手"下拉创建估计器 |
| 切换左右手（第 162 行） | `self.holistic.set_hand_side(...)` | 运行中换手，无需重建 |
| 机械臂标定（第 166–175 行） | `self.follower.update_calib(offset/scale/add=...)` | 更新 `ArmFollower` 的映射标定（offset/scale/add），下次 `process(map_to_arm=True)` 立即生效 |
| 每帧处理（第 185–189 行） | `self.holistic.process(rgb, depth, intrinsics, map_to_arm=..., arm_mapper=self.follower.map_wrist_to_arm_pose)` | 检测+解算+映射一步到位 |
| 机械臂跟随（第 213–217 行） | `self.arm.movel(r.arm_target_pose, block=False)` | 腕部 → TCP → 机械臂运动 |
| 灵巧手跟随（第 221–226 行） | `angles_rad = [math.radians(a) for a in r.hand_angles_deg]; self.hand.move_joints(angles_rad)` | 16 关节角（度→弧度）→ 灵巧手 |

> **手部 16 关节角的校准**（bend_scale/per_finger_* 等）在 holistic 模式下与纯手部模式走**同一套参数**（构造器注入 + `update_params` 转发）。GUI 若复用纯手部模式的校准滑条，调 `self.holistic.update_params(**滑条值)` 即可让两种模式得到完全相同的角度响应——这就是"复用 vs 重复"设计带来的实际好处。

---

## 16. 常见问题（FAQ）

### 问题 1：启动报"未找到 holistic 模型文件 holistic_landmarker.task"

**现象**：`RuntimeError: 未找到 holistic 模型文件 holistic_landmarker.task。请放到项目根目录或 lib/：https://storage.googleapis.com/...`

**原因与解决**：

1. 模型文件不存在或放错位置。`_find_model_file` 的搜索顺序是：显式路径 → **当前目录 → 项目根目录 → 项目根/lib/ → vision/**（第 8 节）。把下载的 `holistic_landmarker.task` 放到 `RY-H1_vision_mimic/lib/` 或项目根目录即可；
2. 下载地址：`MODEL_DOWNLOAD_URL`（Google 官方 float16 版）。若网络受限，可从 mediapipe-models 的 GitHub releases / 镜像获取同名文件；
3. **路径大小写/后缀**：必须精确叫 `holistic_landmarker.task`（不是 `.tflite`——Tasks API 用 `.task` 打包格式，与旧版 solutions API 的 `.tflite` 不通用）；
4. 版本匹配：建议 mediapipe ≥ 0.10.14（官方验证 1.0.1 支持 HolisticLandmarker），模型用**最新版**。

### 问题 2：为什么 HolisticLandmarkerOptions 没有 `num_hands` 参数？

**这是设计差异，不是遗漏**：

- `HandLandmarkerOptions.num_hands` 属于"单手模型"，需要告诉它最多找几只手；
- Holistic 是**全身模型**，左右手是**两个固定输出通道**：`left_hand_landmarks`（左手）和 `right_hand_landmarks`（右手）——不存在"第 N 只手"的概念；
- 因此本模块的"限制手数"逻辑是**选边**（`hand_side`），而不是 num_hands；
- HolisticLandmarkerOptions 实际支持的置信度参数是：`min_pose_detection_confidence`、`min_pose_presence_confidence`、`min_hand_landmarks_confidence`、`min_face_*`（本模块未显式配置，用默认值；如需更灵敏/更严格的检测可自行添加）。

### 问题 3：检测不到人体 / 手

排查顺序：

1. **mediapipe 版本**：确认 `_MP_OK` 为 True（`pip show mediapipe`，建议 ≥0.10.14）；1.x Tasks API 与旧版 solutions API 混装会行为怪异；
2. **图像内容**：人体要**完整入镜**（头部+躯干+至少部分四肢）、光线充足、无明显运动模糊；手不要与脸/身体大面积重叠；
3. **分辨率**：L515 输出 640×480 时，人太远（<30% 画面高度）检测率骤降——靠近相机或提高输入分辨率；
4. **运行模式**：`RunningMode.IMAGE` 是每帧独立检测（无跟踪），检测不到就返回空列表 `[]`，属正常行为；如需跨帧跟踪/回调模式可用 `VIDEO` + `result_callback`（本模块未启用）；
5. **确认早退逻辑**：人体和双手都无结果时 `process` 返回 `[]`——GUI 会显示"未检测到人体/手"（main_gui_holistic.py 第 194 行），先看状态栏。

### 问题 4：左右手"反了"（镜像问题）

**现象**：操作者明明动右手，灵巧手却像左手在动。

**原因**：MediaPipe 的 `left/right_hand_landmarks` 是**图像视角**的左右。操作者**正对相机**时，画面中的"左手"实际是操作者自己的右手（镜子效应）。

**解决**：在 GUI 的"左手/右手"下拉里**按实际观察结果切换** `hand_side`（`set_hand_side` 即时生效，无需重启）：

- 若操作者正对相机、习惯右手控制 → 通常应选 `"left"`（画面左手 = 操作者右手）；
- 若侧身/背对相机 → 按实际匹配调整；
- 建议在测试时同时显示 `r.wrist_side`（GUI 状态栏会打印"腕3D=... [side]"）来核对当前选边。

> 附带注意：**腕部跟随（机械臂）也受选边影响**——`wrist_pose_idx` 跟随 `side`（右侧→pose 16，其余→pose 15），所以换手时机械臂跟随的目标腕也会一起换，属预期行为。

### 问题 5：帧率低 / 卡顿

**原因分析**：

1. Holistic 一次推理同时跑 **人体 Pose + 双手 Hand + 人脸** 三个子网络（即使没用脸，模型仍会算），比单独 `hand_landmarker` 慢得多；
2. `RunningMode.IMAGE` 每帧独立推理，**无跨帧跟踪加速**；
3. 输入分辨率直接决定推理耗时（640×480 明显慢于 320×240）。

**优化建议**：

| 手段 | 说明 |
|---|---|
| 降低处理分辨率 | 推理前把帧缩到 320×240 或 480×270（视觉角度精度影响可控） |
| 限制处理频率 | GUI 轮询里隔帧处理（如每 2–3 帧跑一次 holistic，其余帧复用上次结果） |
| 换 VIDEO 模式 | `RunningMode.VIDEO` + `result_callback` 启用跨帧跟踪（需改造 process 为异步回调风格，本模块当前未采用） |
| 关闭人脸输出 | 本模块已不请求 `output_face_blendshapes/segmentation_mask`（默认 False），无需再改 |
| 硬件 | 有 NVIDIA GPU 时 mediapipe 自动用 GPU delegate，显著提速（Windows 版需确认 CUDA 环境） |

### 问题 6：腕部 3D 跳动 / 机械臂抖

- 腕部优先取 `pose_3d[15/16]`，其深度来自**深度图采样**，边缘/遮挡处易跳变；`np.isfinite` 只挡 NaN 不挡抖动；
- 可配合 `vision/postprocess.py`（方向一致性 + 深度辅助防抖）做后处理，或在机械臂侧限制速度/加滤波；
- 深度缺失时走"相对深度补全"（`ref_z + rel_z×300`），精度低于真深度——尽量保持躯干（髋/肩）在深度有效量程 (0,3000)mm 内，因为 `ref_z` 的可靠性决定补全质量。

---

## 17. 全文件成员索引（速查表）

| 行号 | 成员 | 一句话作用 |
|---|---|---|
| 45 | `logger` | 模块日志（命名空间 "holistic"） |
| 48–57 | `mp / mp_python / mp_vision / _MP_OK` | mediapipe 导入与可用性标志 |
| 60 | `DEFAULT_MODEL_NAME` | 默认模型文件名 `holistic_landmarker.task` |
| 61–64 | `MODEL_DOWNLOAD_URL` | 官方模型下载地址 |
| 67–77 | `_find_model_file()` | 按优先级搜索模型文件 |
| 82–94 | `POSE_*` | 人体 33 点常用索引常量 |
| 97–103 | `POSE_CONNECTIONS` | 人体骨架连线（简化版） |
| 106–110 | `from .hand_pose import ...` | 复用 hand_pose 常量与工具 |
| 113–147 | `HolisticResult` | 单帧结果 dataclass（10 字段 + 2 属性） |
| 150–157 | `HolisticPoseEstimator` | 主类（检测 + 组合解算 + 映射） |
| 159–215 | `__init__` | 环境/模型检查、创建 Landmarker、组合裸实例 |
| 217–224 | `update_params()` | 校准参数动态更新（转发给手部引擎） |
| 226–228 | `set_hand_side()` | 切换控制手 |
| 230–318 | `process()` | 单帧七步流水线 |
| 320–364 | `_pose_to_3d()` | 人体 33 点 → 相机系米制（深度优先+补全） |
| 366–403 | `draw_skeleton()` | 人体(绿)+手部(黄)双色骨架 |
| 405–412 | `close()` | 释放模型资源 |
| 415–417 | `bgr2rgb()` | BGR→RGB 通道交换 |
| 420–428 | `__main__` | 自测：模型加载 + 空帧处理 |

---

## 附：与相关文件的接口关系

```
vision/holistic_pose.py
   │ 复用（组合裸实例）
   ├──► vision/hand_pose.py        # HAND_CONNECTIONS、WRIST/指尖常量、_angle_between、
   │                               #   HandPoseEstimator 的 3D 转换/16 角/握拳方法
   │ 映射（process 的 arm_mapper 参数）
   └──► arm/arm_follow.py          # ArmFollower.map_wrist_to_arm_pose：腕部3D→TCP [x,y,z,rx,ry,rz]
   │ 调用方
   ├──► gui/main_gui_holistic.py   # 构造估计器、set_hand_side、process+ArmFollower、movel/move_joints
   ├──► apps/test_holistic.py      # 单项验证（模型/检测/角度/映射/骨架）
   └──► vision/postprocess.py      # （可选）角度后处理防抖
```
