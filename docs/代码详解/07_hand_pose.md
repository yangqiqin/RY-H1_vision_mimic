# 07 · hand_pose.py 手部姿态估计模块详解

> **所属系统**：睿研 RY-H1(16) 灵巧手视觉动作模仿系统（Windows 版）
> **模块定位**：视觉链路的"感知前端"——把一帧 RGB 图像（可选 + 深度图）变成 16 个关节角度 + 一系列辅助量（深度、握拳置信度等），供下游 `postprocess.py`（滤波/防抖）与 GUI 使用。
> **源文件**：`rycan_hand_windows/vision/hand_pose.py`（共 769 行）

---

## 0. 数据流总览（先建立全局画面）

```
┌────────────────────────────────────────────────────────────────────┐
│                        hand_pose.py 单帧流水线                      │
│                                                                    │
│  RGB 图像 (BGR) + 深度图(mm) + 相机内参                              │
│        │                                                          │
│        ▼                                                          │
│  ┌──────────────────────────┐                                     │
│  │ bgr2rgb()  BGR→RGB 交换   │                                     │
│  └──────────────────────────┘                                     │
│        │                                                          │
│        ▼                                                          │
│  ┌──────────────────────────┐                                     │
│  │ mp.Image(SRGB) 封装       │                                     │
│  └──────────────────────────┘                                     │
│        │                                                          │
│        ▼                                                          │
│  ┌──────────────────────────┐                                     │
│  │ HandLandmarker.detect()  │  ← MediaPipe 1.x Tasks API          │
│  │ （hand_landmarker.task）  │     21 个关键点 / 手，归一化坐标      │
│  └──────────────────────────┘                                     │
│        │                                                          │
│        ▼                                                          │
│  对每只检测到的手：                                                  │
│   ├─ _convert_landmarks_to_3d() ──► 3D 坐标(米)（针孔反投影）        │
│   ├─ _landmarks_to_angles16()  ──► 16 关节角 + 拇指横向距离          │
│   ├─ _hand_depth()             ──► 手部深度(mm)                    │
│   └─ _compute_fist_confidence()──► 握拳置信度[0,1]                  │
│        │                                                          │
│        ▼                                                          │
│  HandResult 对象列表（每只手一个）                                    │
└────────────────────────────────────────────────────────────────────┘
        │
        ▼
  下游：postprocess.py（方向一致性 + 深度辅助防抖）
        │
        ▼
  GUI / 电机控制（16 关节角 → 舵机角度）
```

**坐标变换链**（本文件内部最核心的一条线）：

```
2D 像素坐标 (u,v) + 深度 Z(mm)            ← MediaPipe 关键点 + L515 深度图
        │  有效深度区间 (0, 3000)mm，超出置 NaN
        ▼
相机坐标系 3D 点 (X, Y, Z)，单位米          ← 针孔反投影
        │
        ▼
手掌局部坐标系（每帧实时构建）：
        normal    = normalize( (中指MCP−WRIST) × (小指MCP−WRIST) )  垂直掌面
        palm_axis = normalize( 中指MCP − WRIST )                   沿掌长方向
        perp      = normalize( normal × palm_axis )                沿掌宽方向
        │
        ▼
在局部坐标系下计算角度：
  侧摆(0/3/6/9/12)：向量投影到掌面 → 与 palm_axis 夹角，带 ± 号，|θ|≤20°
  内外展(15)     ：|TIP−掌心 在 perp 上的投影| ÷ 半掌宽 → 软饱和 → 0~110°
  弯曲(1,2,4,5,7,8,10,11,13,14)：相邻段向量夹角（或距离比率）→ 0~90° / 0~75°
```

---

## 1. 头部注释与 16 关节索引约定

文件头部（第 1–33 行）是一份完整的"模块说明书"，其中最重要的就是 **16 个关节角度的索引约定**（下游 `postprocess.py`、GUI、电机映射全部依赖这套索引，务必保持一致）：

| 索引 | 含义 | 范围（本模块输出） |
|------|------|--------------------|
| 0 | 拇指侧摆 (swing) | ±20° |
| 1 | 拇指近端弯曲 (proximal, CMC–MCP 折角) | 0~90° |
| 2 | 拇指远端弯曲 (distal, IP 折角) | 0~75° |
| 3 | 食指侧摆 (swing) | ±20° |
| 4 | 食指近端弯曲 (proximal) | 0~90° |
| 5 | 食指远端弯曲 (distal) | 0~75° |
| 6 | 中指侧摆 | ±20° |
| 7 | 中指近端弯曲 | 0~90° |
| 8 | 中指远端弯曲 | 0~75° |
| 9 | 无名指侧摆 | ±20° |
| 10 | 无名指近端弯曲 | 0~90° |
| 11 | 无名指远端弯曲 | 0~75° |
| 12 | 小指侧摆 | ±20° |
| 13 | 小指近端弯曲 | 0~90° |
| 14 | 小指远端弯曲 | 0~75° |
| 15 | 拇指内外展 (abduction/adduction) | 0~110° |

> 布局规律：每根手指占 3 个索引 = **侧摆 + 近端弯曲 + 远端弯曲**；食指从索引 3 开始，之后每指 +3（3/6/9/12 为侧摆，4/5、7/8、10/11、13/14 为近端/远端弯曲）。这个"每指 3 个"的规律在 `_landmarks_to_angles16()` 里用 `base = finger_idx * 3` 直接复用。

---

## 2. 导入与 MediaPipe 可用性检查（第 35–51 行）

```python
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence
import numpy as np

try:
    import mediapipe as mp
    _MP_OK = True
except ImportError:
    mp = None
    _MP_OK = False
```

- 使用 `try/except` 包住 `import mediapipe`：**如果环境里没装 mediapipe，模块仍可被 import**（不会一导入就崩），只是 `_MP_OK = False`。
- `_MP_OK` 这个标志在 `HandPoseEstimator.__init__` 里被检查，未安装时会抛出带安装指引的 `RuntimeError`。这样做的目的是让"文档/导入层"与"真正要用模型的功能层"解耦——即使没装库，GUI 也还能导入其余部分做展示。
- 注意：**本文件使用的是 MediaPipe 1.x 的 Tasks API**（`mediapipe.tasks.python.vision.HandLandmarker`），不是旧版 `mediapipe.solutions.hands`。两者的模型文件、API 形态完全不同，下文第 9 节会详述。

---

## 3. MediaPipe 21 关键点索引常量（第 53–60 行）

MediaPipe 手部模型输出 **21 个标准关键点**，编号 0~20。本文件为每个关键点定义了有意义的常量名：

```python
WRIST = 0                                  # 手腕
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4   # 拇指：腕掌/掌指/指间/指尖
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8  # 食指
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12  # 中指
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16  # 无名指
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20  # 小指
```

标准命名法（MediaPipe 官方约定）：

| 缩写 | 全称 | 含义 |
|------|------|------|
| CMC | Carpometacarpal | 腕掌关节（仅拇指有） |
| MCP | Metacarpophalangeal | 掌指关节（手指根部） |
| PIP | Proximal Interphalangeal | 近端指间关节 |
| DIP | Distal Interphalangeal | 远端指间关节 |
| IP | Interphalangeal | 指间关节（拇指只有一节，统称 IP） |
| TIP | Tip | 指尖 |

> 为什么用常量名而不是裸数字？因为后面 `_landmarks_to_angles16()` 里大量出现 `pts[THUMB_TIP]`、`pts[MIDDLE_MCP]` 这类访问，用名字可读性高、改索引只改一处。

---

## 4. FINGER_LANDMARKS 与 HAND_CONNECTIONS（第 62–80 行）

### 4.1 FINGER_LANDMARKS —— 手指关键点分组

```python
FINGER_LANDMARKS = {
    "thumb":  (THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP),   # (1,2,3,4)
    "index":  (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),  # (5,6,7,8)
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),  # (9,10,11,12)
    "ring":   (RING_MCP, RING_PIP, RING_DIP, RING_TIP),      # (13,14,15,16)
    "pinky":  (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),  # (17,18,19,20)
}
FINGER_ORDER = ["thumb", "index", "middle", "ring", "pinky"]
```

- 每根手指用 **4 个连续关键点** 描述：拇指是 `(CMC, MCP, IP, TIP)`，四指是 `(MCP, PIP, DIP, TIP)`。
- `FINGER_ORDER` 是遍历顺序，且**顺序本身携带了索引信息**：第 0 位是 thumb、第 1 位是 index……因此 `_landmarks_to_angles16()` 里可以用 `base = finger_idx * 3` 直接推出该指的 3 个关节在 16 关节数组中的起始位置（thumb 跳过，index→3，middle→6，ring→9，pinky→12）。

### 4.2 HAND_CONNECTIONS —— 骨架连线表（仅用于绘制）

```python
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # 拇指链：WRIST→CMC→MCP→IP→TIP
    (0, 5), (5, 6), (6, 7), (7, 8),          # 食指链：WRIST→MCP→PIP→DIP→TIP
    (5, 9), (9, 10), (10, 11), (11, 12),     # 中指链（从食指 MCP 分叉）
    (9, 13), (13, 14), (14, 15), (15, 16),   # 无名指链（从中指 MCP 分叉）
    (13, 17), (17, 18), (18, 19), (19, 20),  # 小指链（从无名指 MCP 分叉）
    (0, 17),                                 # 手掌横跨线（WRIST→小指MCP）
]
```

- 这是**手部拓扑结构**的显式描述：四指从同一掌根出发、逐指分叉，加上一条腕到小指根的横跨线。
- 它**只服务于 `draw_skeleton()` 的可视化**，不参与任何角度计算（角度计算用的是"向量夹角"，与连线无关）。
- `draw_skeleton()` 用 `pts[a][0] * w`、`pts[a][1] * h` 把归一化坐标还原成像素坐标来画线/画点（见第 17 节）。

---

## 5. 模型文件配置（第 82–87 行）

```python
DEFAULT_MODEL_NAME = "hand_landmarker.task"
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
```

- 这是 **MediaPipe Tasks API 时代的模型文件**（`.task` 格式，内含 TFLite 图 + 元数据），与旧版 `solutions.hands` 的 `.tflite` 不通用。
- 默认文件名 `hand_landmarker.task` 会在 `_find_model_file()` 中被按固定顺序搜索。
- 官方下载 URL 直接写死在代码里，模型缺失时 `__init__` 抛出的错误信息会提示用户去这个地址下载。

---

## 6. 模块级函数一：`_find_model_file()`（第 90–115 行）

**作用**：在多个候选位置中定位模型文件，返回完整路径；找不到返回 `None`。

**实际搜索顺序**（按代码实现，注意与注释略有出入）：

```
1. model_path（用户显式指定）→ 存在则直接返回，不存在返回 None
2. os.getcwd()                  当前工作目录
3. project_root                 即"当前文件目录的上一级"= r y c a n _ h a n d _ w i n d o w s 包根
4. project_root/lib             lib/ 子目录
5. here                         当前文件所在目录（vision/）
```

代码关键点：

```python
if model_path:
    return model_path if os.path.exists(model_path) else None
here = os.path.dirname(os.path.abspath(__file__))   # .../rycan_hand_windows/vision
project_root = os.path.dirname(here)                # .../rycan_hand_windows
for d in (os.getcwd(), project_root,
          os.path.join(project_root, "lib"), here):
    p = os.path.join(d, DEFAULT_MODEL_NAME)
    if os.path.exists(p):
        return p
return None
```

- `here` 是**源文件所在目录**（`vision/`），`project_root` 是它往上一级（`rycan_hand_windows/` 包根）。注释写"上两级"，但代码实际是"上一级"——以代码为准。
- 四个候选目录按优先级依次探测：**工作目录 → 包根 → 包根/lib → vision 目录**，谁先命中返回谁。
- 设计意图：打包发布时模型可能放在 `lib/`（与 `L515_driver.py` 等第三方库同层）、运行时可能从任意 cwd 启动、开发时可能就在 `vision/` 旁边，多路径探测提高"模型放哪都能找到"的容错性。
- 若全没找到返回 `None`，`__init__` 会据此抛出"未找到模型文件"的 `RuntimeError`（见第 9 节）。

---

## 7. 模块级函数二：`_angle_between()`（第 118–135 行）

**作用**：计算两个三维向量的夹角（度），范围 [0, 180]。这是全模块最底层的"角度原语"，四指弯曲、拇指弯曲全部调用它。

```python
def _angle_between(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-6 or nb < 1e-6:
        return 0.0                      # 向量退化（长度≈0）→ 夹角无意义，返回 0
    cos = float(np.dot(a, b) / (na * nb))
    cos = max(-1.0, min(1.0, cos))      # 数值保护：防止浮点误差导致 acos 越界
    return math.degrees(math.acos(cos))
```

逐行解释：

1. **模长保护**：任一向量的模长 < `1e-6`（基本是零向量，例如两个关键点重合）时，夹角没有数学意义，直接返回 `0.0`，避免除零。
2. **余弦公式**：`cosθ = (a·b) / (|a|·|b|)`。
3. **数值裁剪**：浮点运算可能算出 `cos ≈ 1.0000000002` 之类的越界值，`acos` 的输入域是 [-1, 1]，不裁剪会得到 `nan`，所以先 `max(-1, min(1, cos))`。
4. **转角度**：`acos` 返回弧度，`math.degrees` 转成度。
5. **注意**：`acos` 结果天然在 [0, π]，所以 `_angle_between` **没有正负号**——它只回答"弯了多少"，不回答"往哪个方向弯"。方向性（正负）由调用处另行处理（侧摆用 `perp` 点积判号，内外展用 `abs()` 取无符号）。

---

## 8. 数据类 `HandResult`（第 138–169 行）

**作用**：单只手的完整检测结果容器，是 `process()` 的返回值元素。使用 `@dataclass` 声明，自动生成构造函数。

### 8.1 字段一览

| 字段 | 类型 | 含义 |
|------|------|------|
| `landmarks` | `np.ndarray` (21,3) | 21 个关键点的**归一化坐标**（x,y∈[0,1]，z 为 MediaPipe 相对深度），**无论有无深度图都会填充** |
| `handedness` | `str` | `"Left"` / `"Right"` / `"unknown"` |
| `joint_angles_deg` | `List[float]` (16,) | 16 个关节角度（度），默认全 0 |
| `confidence` | `float` | 检测置信度 [0,1]，取 `handedness[0].score`，无则默认 0.5 |
| `hand_depth_mm` | `Optional[float]` | 手腕处深度（毫米），来自深度图；无深度或越界为 `None` |
| `avg_depth_mm` | `Optional[float]` | 手掌 5 个关键点（WRIST + 四指 MCP）的平均深度（毫米） |
| `lateral_dist` | `Optional[float]` | 拇指横向距离（**米**，使用 3D 坐标时；归一化坐标时单位为"归一化单位"），直接存储供调试/展示 |
| `fist_confidence` | `Optional[float]` | 深度辅助握拳置信度 [0,1]；**无深度时为 `None`**（新功能，供后处理判断"真实握拳 vs 抖动"） |

```python
joint_angles_deg: List[float] = field(default_factory=lambda: [0.0] * 16)
```

- `field(default_factory=...)` 保证每个实例都拿到**独立**的 16 元素列表，而不是共享同一个可变默认值（Python 可变默认参数的经典坑）。

### 8.2 属性（property）

```python
@property
def joint_angles_rad(self) -> List[float]:
    """将关节角度从度转换为弧度"""
    return [math.radians(a) for a in self.joint_angles_deg]

@property
def visible(self) -> bool:
    """检查是否检测到手部"""
    return self.landmarks is not None
```

- `joint_angles_rad`：下游若需要弧度（某些电机控制库用弧度）可直接取，无需手写循环。
- `visible`：判断是否有手。注意一个细节——`process()` 构造 `HandResult` 时 `landmarks` 总是有值的，所以正常流程下 `visible` 恒为 `True`；它主要服务于"手工构造一个空结果"的容错场景（例如 GUI 用 `HandResult(landmarks=None)` 表示"无手"）。

---

## 9. 主类 `HandPoseEstimator.__init__`（第 172–271 行）

### 9.1 构造参数清单（全部有默认值，GUI 可实时覆盖）

| 参数 | 默认 | 含义 |
|------|------|------|
| `max_hands` | 1 | 最大检测手数 |
| `min_detection_confidence` | 0.5 | 检测阶段最小置信度 |
| `min_tracking_confidence` | 0.5 | 跟踪阶段最小置信度 |
| `bend_scale` | 1.0 | 弯曲角度**全局缩放**（乘法） |
| `bend_offset` | 0.0 | 弯曲角度**全局偏移**（加法，度） |
| `bend_gain` | 1.0 | 弯曲角度**全局增益**（乘法，与 scale 叠加） |
| `deadzone_deg` | 1.0 | 角度死区（度），小于它的弯曲角被置 0 |
| `bend_reverse` | False | 是否反转弯曲（`90−θ` / `75−θ`） |
| `use_distance_ratio` | False | 是否用**距离比率法**算弯曲（替代向量夹角法） |
| `per_finger_scale` | None | 每指独立缩放，如 `{"index": 0.8}` |
| `per_finger_offset` | None | 每指独立偏移，如 `{"index": 5.0}` |
| `model_path` | None | 模型文件路径，None 时走自动搜索 |
| `thumb_abd_offset` | 0.0 | 内外展死区（半掌宽倍数，GUI 范围 0~0.5） |
| `thumb_abd_gain` | 0.8 | 内外展有效区增益（GUI 范围 0.3~2.0） |
| `thumb_abd_reverse` | False | 内外展方向反转（True：外展→110°，内收→0°） |

### 9.2 初始化流程（第 229–271 行）

```python
if not _MP_OK:
    raise RuntimeError("请先安装 mediapipe>=0.10.14：pip install mediapipe")
```

**第 1 步：可用性检查**。mediapipe 没装上就直接报错，给出最小版本号（Tasks API 需要较新的 1.x）。

```python
model_file = _find_model_file(model_path)
if model_file is None:
    raise RuntimeError(
        f"未找到手部模型文件 {DEFAULT_MODEL_NAME}。请下载并放到项目根目录或 lib/：\n"
        f"  {MODEL_DOWNLOAD_URL}")
self.model_path = model_file
```

**第 2 步：定位模型**。找不到就抛错并附官方下载地址（"常见问题"第 1 条）。

**第 3 步：用 Tasks API 构建 HandLandmarker**（本文件与旧版 `solutions.hands` 的根本区别）：

```python
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

base_options = mp_python.BaseOptions(model_asset_path=model_file)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=max_hands,
    min_hand_detection_confidence=min_detection_confidence,
    min_hand_presence_confidence=min_tracking_confidence,
    min_tracking_confidence=min_tracking_confidence,
    running_mode=vision.RunningMode.IMAGE,   # 图像模式（单帧推理，非视频流）
)
self._landmarker = vision.HandLandmarker.create_from_options(options)
```

- `BaseOptions(model_asset_path=...)`：指定 `.task` 模型文件路径。
- `HandLandmarkerOptions`：配置检测数量与三档置信度阈值（检测、存在、跟踪）。`running_mode=IMAGE` 表示**逐帧独立推理**，不依赖时间上下文——适合模仿演示这种"来一帧处理一帧"的用法；`VIDEO` 模式则需要带时间戳的流式调用。
- `create_from_options` 返回可用的 landmarker 实例，保存在 `self._landmarker`。

**第 4 步：存参数并做防御性处理**：

```python
self.bend_gain = max(0.1, float(bend_gain))          # 增益下限 0.1，防 0/负
self.thumb_abd_gain = max(0.1, float(thumb_abd_gain)) # 同上
self._frame_scale = 1.0   # 预留的帧缩放因子（当前未参与计算）
```

- 两个 `gain` 都被钳制在 ≥0.1：防止用户把增益调到 0 或负值导致输出恒 0 或反向。
- `_frame_scale` 是预留字段，当前代码中没有任何地方使用它（保留是为了以后支持图像缩放加速）。

---

## 10. `update_params()` 动态调参（第 273–307 行）

**作用**：运行时热更新参数，供 GUI 滑块/复选框实时调用（`main_gui.py` 第 437–439、657–659 行就是这么用的）。

```python
def update_params(self, **kwargs):
    for k, v in kwargs.items():
        if k == "bend_scale": self.bend_scale = float(v)
        elif k == "bend_offset": self.bend_offset = float(v)
        elif k == "bend_gain": self.bend_gain = max(0.1, float(v))
        elif k == "deadzone_deg": self.deadzone_deg = float(v)
        elif k == "bend_reverse": self.bend_reverse = bool(v)
        elif k == "use_distance_ratio": self.use_distance_ratio = bool(v)
        elif k == "per_finger_scale" and isinstance(v, dict):
            self.per_finger_scale.update({str(x): float(y) for x, y in v.items()})
        elif k == "per_finger_offset" and isinstance(v, dict):
            self.per_finger_offset.update({str(x): float(y) for x, y in v.items()})
        elif k == "thumb_abd_offset": self.thumb_abd_offset = float(v)
        elif k == "thumb_abd_gain": self.thumb_abd_gain = max(0.1, float(v))
        elif k == "thumb_abd_reverse": self.thumb_abd_reverse = bool(v)
```

- 白名单式分发：未知参数名被静默忽略，不会误写。
- 所有数值都显式 `float()`/`bool()` 强转，防止 GUI 传字符串。
- 每指字典用 `update()` **合并**而非整体替换——允许只调某一根手指的参数而不影响其他手指。
- 全程无锁无重建：角度计算在 `_landmarks_to_angles16()` 里每次读取 `self.*`，所以参数修改**下一帧立即生效**。

---

## 11. `_convert_landmarks_to_3d()` 针孔反投影（第 309–352 行）

**作用**：把归一化 2D 关键点 + 深度图 → 相机坐标系 3D 点（米）。这是"深度辅助"一切功能（3D 优先角度、握拳置信度、真实手部深度）的基础。

**原理**（针孔相机模型）：

```
Z = depth[u, v] / 1000.0      # 深度图单位毫米 → 米
X = (u - ppx) * Z / fx        # 反投影：像素列 → 相机 x
Y = (v - ppy) * Z / fy        # 像素行 → 相机 y
```

**代码逐段**：

```python
h, w = depth.shape[:2]
fx = intrinsics['fx']; fy = intrinsics['fy']
ppx = intrinsics['ppx']; ppy = intrinsics['ppy']
pts_3d = np.zeros_like(landmarks_norm, dtype=np.float64)
```

- 取出深度图尺寸与内参（焦距 `fx/fy`、主点 `ppx/ppy`，单位像素）。内参由相机驱动（如 L515）标定给出。
- `pts_3d` 预分配为 float64（比 float32 精度高，避免角度计算误差累积）。

```python
for i, (nx, ny, _) in enumerate(landmarks_norm):
    u = int(nx * w)          # 归一化 x → 像素列
    v = int(ny * h)          # 归一化 y → 像素行
    if 0 <= v < h and 0 <= u < w:
        z_mm = float(depth[v, u])
        if z_mm > 0 and z_mm < 3000:      # 有效深度范围 0~3000mm
            z = z_mm / 1000.0
            x = (u - ppx) * z / fx
            y = (v - ppy) * z / fy
            pts_3d[i] = [x, y, z]
        else:
            pts_3d[i] = [nan, nan, nan]
    else:
        pts_3d[i] = [nan, nan, nan]
```

逐点处理，三个关键决策：

1. **像素取整**：`u = int(nx * w)` 直接把关键点落在**单像素**上取深度（不做邻域平均）。优点是快；缺点是关键点稍微偏一点深度就跳——这就是为什么后处理要配 One Euro 平滑。
2. **边界检查**：坐标越界（关键点被截断在画面外）→ NaN，不访问越界内存。
3. **有效深度区间 `(0, 3000)mm`**：
   - `>0`：滤掉深度为 0 的"黑洞"（传感器未测到、太近或太远都常给 0）。
   - `<3000`：滤掉 3 米外的噪声/背景。L515 的标称工作距离约 0.25~9m，但手部操作场景都在 1m 内，取 3000mm 上限足够且能挡掉远距离杂散深度。
   - **无效点统一置 NaN**——NaN 是"该点不可用"的统一信号，下游用 `np.isnan` 检查（`_landmarks_to_angles16` 用它决定是否回退到归一化坐标，`_compute_fist_confidence` 用它决定是否返回 None）。

---

## 12. `process()` 主流水线（第 354–425 行）

**签名**：

```python
def process(self, rgb_bgr: np.ndarray,            # BGR 格式图像 (H,W,3) uint8
            depth: Optional[np.ndarray] = None,   # 深度图 (H,W) 毫米
            intrinsics: Optional[dict] = None) -> List[HandResult]:  # 内参
```

> ⚠️ 命名注意：参数名叫 `rgb_bgr`，实际接收的是 **BGR 顺序**（OpenCV 惯例），函数内部第 1 步就把它转成真正的 RGB 给 MediaPipe。传图时务必给 BGR 格式，否则颜色通道错乱会显著影响检测效果。

**完整流水线（对应第 0 节的图）**：

```python
if rgb_bgr is None:
    return []
rgb = bgr2rgb(rgb_bgr)                          # ① BGR→RGB
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(rgb))   # ② 封装 MediaPipe 图像
res = self._landmarker.detect(mp_image)          # ③ 推理
out = []
if not res.hand_landmarks:
    return out                                   # ④ 没检测到手 → 空列表
```

- `np.ascontiguousarray`：保证内存连续，MediaPipe 对非连续数组可能报错。
- 无手时返回**空列表**（不是 None），调用方用 `if results:` 即可判断。

```python
handedness = []
for hh in res.handedness:
    if hh:
        cat = hh[0]
        handedness.append(cat.category_name or cat.display_name or "unknown")
```

- 提取左右手标签：Tasks API 的 `handedness` 是每个手的分类列表，取置信度最高的第 0 个分类，`category_name` 为空时回退到 `display_name`，再不行给 `"unknown"`。

```python
for i, lm in enumerate(res.hand_landmarks):
    pts_norm = np.array([(p.x, p.y, p.z) for p in lm], dtype=np.float64)
    label = handedness[i] if i < len(handedness) else "unknown"
    conf = 0.5
    if res.handedness and i < len(res.handedness) and res.handedness[i]:
        conf = float(res.handedness[i][0].score)
```

- 每只手的 21 个关键点组装成 `(21,3)` 数组（float64）。注意 `p.z` 是 MediaPipe 输出的**相对深度**（以手腕为基准的归一化值，不是真实深度），只有和深度图结合才能得到真实 3D。
- 置信度取分类分数，异常情况下兜底 0.5。

```python
    real_pts = None
    if depth is not None and intrinsics is not None:
        real_pts = self._convert_landmarks_to_3d(pts_norm, depth, intrinsics)

    angles, lateral_dist = self._landmarks_to_angles16(pts_norm, real_pts)

    hand_d, avg_d = None, None
    if depth is not None:
        hand_d, avg_d = self._hand_depth(depth, pts_norm)

    fist_conf = self._compute_fist_confidence(pts_norm, real_pts)

    out.append(HandResult(
        landmarks=pts_norm, handedness=label,
        joint_angles_deg=angles, confidence=conf,
        hand_depth_mm=hand_d, avg_depth_mm=avg_d,
        lateral_dist=lateral_dist, fist_confidence=fist_conf,
    ))
return out
```

- **3D 坐标可选**：`depth` 和 `intrinsics` 必须同时给出才做反投影；缺一则 `real_pts=None`，角度计算自动退回纯 2D 归一化坐标（第 13 节会讲这个回退）。
- **16 个角度永远计算**：无论有无深度。
- 深度辅助量（`hand_depth_mm` / `avg_depth_mm` / `fist_confidence`）只在有深度图时才有值，否则为 `None`。
- `lateral_dist` 透传出来，主要供 GUI 调试显示（`main_gui.py` 第 557 行读取它）。

---

## 13. `_compute_fist_confidence()` 深度辅助握拳置信度（第 427–459 行）

> 这是**新功能**，也是后处理"真实握拳 vs 抖动"判定的关键输入（`postprocess.py` 第 161–162 行：`fist_confidence >= 0.6` 时跳过异常判定，避免真实握拳被当作抖动抑制）。

**为什么需要它？** MediaPipe 在握拳时（指尖遮挡多）关键点抖动很大，纯角度跳变检测容易把"真实握拳"误判成"孤立突变"而抑制掉。但 L515 深度图给出的是**真实的 3D 位置**——握拳时四指指尖明显靠近掌心，这是深度相机才能可靠看到的几何事实，用它来背书"这是真握拳"。

**算法推导（详细）**：

```python
if real_pts is None or np.any(np.isnan(real_pts)):
    return None      # 无深度 → 无法用深度确认，交给方向一致性检测兜底
```

**前置条件**：必须有完整无 NaN 的 3D 坐标（任一关键点无效都放弃，避免用残缺点算距离）。

```python
pts = real_pts                       # 单位米
palm_center = (pts[WRIST] + pts[MIDDLE_MCP]) / 2.0     # 掌心 ≈ 腕与中指根的中点
palm_w = float(np.linalg.norm(pts[MIDDLE_MCP] - palm_center))  # 半掌宽
if palm_w < 1e-6:
    palm_w = 0.02                    # 退化保护：防止除零
tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
dists = [np.linalg.norm(pts[t] - palm_center) for t in tips]
ratio = float(np.mean(dists)) / palm_w
```

- **掌心中心**：取 `(WRIST + 中指MCP)/2`。用这两点是因为它们在最稳定的掌根结构上（指尖再怎么动，掌根不太动），且不依赖拇指（拇指姿势不影响掌心）。
- **半掌宽 `palm_w`**：`中指MCP → 掌心` 的距离，作为**长度标尺**。用标尺归一化后，`ratio` 与手的绝对大小、与相机距离无关（近大远小被消掉）——这是它能跨距离工作的关键。
- **四指指尖到掌心的平均距离** ÷ 半掌宽 = `ratio`。

**标定数据**（代码注释里的实测值，`palm_w≈0.04~0.05m`）：

| 手型 | 指尖–掌心距离 | ratio |
|------|--------------|-------|
| 张开手 | ≈0.10~0.12 m | ≈2.0~3.0 |
| 握拳 | ≈0.03~0.05 m | ≈0.7~1.1 |

```python
conf = (1.6 - ratio) / (1.6 - 0.9)      # 线性映射到 [0,1]
return float(np.clip(conf, 0.0, 1.0))
```

- 映射区间 `[0.9, 1.6]`（代码注释与需求文档一致）：
  - `ratio ≤ 0.9` → `conf = 1.0`（确定握拳，深度证实指尖已贴掌心）
  - `ratio ≥ 1.6` → `conf = 0.0`（确定张开）
  - 中间线性过渡：`conf = (1.6 − ratio) / 0.7`
- 两个区间端点的物理含义：0.9 与 1.6 之间正是"半握拳/手型过渡"的模糊带，线性插值给出连续置信度，便于后处理用阈值（0.6）做软判定。

**置信度与"握拳"的关系**：**ratio 越小 → 指尖越贴掌心 → 越像握拳 → conf 越大**，单调映射。

---

## 14. `_hand_depth()` 手部深度提取（第 461–494 行）

**作用**：从深度图里抠出手部的两个深度参考值（毫米）。

```python
try:
    h, w = depth.shape[:2]
    u = int(pts[WRIST][0] * w); v = int(pts[WRIST][1] * h)
    hand_d = None
    if 0 <= v < h and 0 <= u < w:
        z = float(depth[v, u])
        if 0 < z < 3000:
            hand_d = z                      # ① 手腕单点深度

    vals = []
    for k in (0, 5, 9, 13, 17):             # WRIST + 四指 MCP
        u2 = int(pts[k][0] * w); v2 = int(pts[k][1] * h)
        if 0 <= v2 < h and 0 <= u2 < w:
            z2 = float(depth[v2, u2])
            if 0 < z2 < 3000:
                vals.append(z2)
    avg_d = float(np.mean(vals)) if vals else None   # ② 5 点平均深度
    return hand_d, avg_d
except Exception:
    return None, None                       # 任何异常都不让流水线崩
```

- `hand_depth_mm`：手腕点深度，代表"手离相机多远"。
- `avg_depth_mm`：手腕 + 四指 MCP 共 5 个掌根点的平均，比单点更抗噪（单点跳了平均不跳）。
- 同样做边界与 `(0, 3000)` 有效性过滤。
- 整个函数包在 `try/except` 里兜底返回 `(None, None)`——深度图偶尔形状异常（比如相机没起好）不能让整个 process 崩掉。

---

## 15. `_bend_ratio_by_distance()` 距离比率法（第 496–516 行）

**作用**：用"三段距离的比例"估计弯曲程度，替代向量夹角法。供 `use_distance_ratio=True` 时使用。

**原理**：

```
手指伸直时：|p1-p3| ≈ |p1-p2| + |p2-p3|          → ratio ≈ 0
手指完全弯曲时：|p1-p3| 远小于两段之和             → ratio → 1

ratio = 1 - |p1-p3| / (|p1-p2| + |p2-p3|)
```

```python
d13 = np.linalg.norm(p1 - p3)
d12 = np.linalg.norm(p1 - p2)
d23 = np.linalg.norm(p2 - p3)
denom = d12 + d23
if denom < 1e-6:
    return 0.0                 # 两段都退化 → 视为伸直
ratio = 1.0 - d13 / denom
return float(np.clip(ratio, 0.0, 1.0))
```

**直觉解释**：骨节长度在弯曲时几乎不变，所以 `|p1-p2|+|p2-p3|`（折线总长）基本恒定；变化的是弦长 `|p1-p3|`（指尖到指根直线距离）。弯曲越狠，弦越短，`d13/denom` 越小，`ratio` 越大。

**与向量夹角法的差异**：
- 向量夹角法对"哪个方向弯"更敏感、物理上更接近真实关节角，但对 2D 投影下的遮挡/形变敏感；
- 距离比率法只依赖长度，对平面内旋转不敏感、更稳，但会混淆"手指弯曲"与"手指向掌心收缩"（比如四指并拢但没弯，`d13` 也会变小一点点）。
- 两者是**可切换策略**（GUI 里有"距离比法"复选框），默认关，用向量夹角法。

---

## 16. `_landmarks_to_angles16()` —— 全模块核心（第 518–715 行）

**签名**：输入归一化坐标 + 可选真实 3D 坐标，输出 `(angles[16], lateral_dist)`。

### 16.0 坐标选择与回退策略

```python
if real_pts is not None and not np.any(np.isnan(real_pts)):
    pts = real_pts      # 3D 优先：几何最真实
    is_real = True
else:
    pts = pts_norm      # 无深度/深度有缺 → 退回归一化坐标
    is_real = False
```

- **只要深度给出的 3D 坐标完整有效，一律用 3D**。因为：
  1. 3D 坐标不受"手离相机远近"影响，角度在不同距离下保持一致（归一化 2D 坐标在近距离时侧摆/弯曲角会被透视放大）；
  2. 3D 能区分"手在画面里旋转但形状没变"和"形状真的变了"，2D 投影做不到；
  3. 深度值本身来自 L515 真实测量，比 MediaPipe 的模型推断（z 是网络估计的相对深度）可信。
- 只要**任何一个**关键点是 NaN（比如指尖被遮挡超出深度有效范围），就整体回退到归一化坐标——绝不混用两种坐标系（混用会导致手掌坐标系方向错乱）。回退后 `is_real=False`，只影响手掌法线退化时的兜底值（其实两分支相同，见下）。

### 16.1 构建手掌局部坐标系（第 550–579 行）—— 用叉积搭出"掌面"

```python
wrist = pts[WRIST]
mcp_mid = pts[MIDDLE_MCP]      # 中指 MCP
mcp_pinky = pts[PINKY_MCP]     # 小指 MCP

v1 = mcp_mid - wrist
v2 = mcp_pinky - wrist
normal = np.cross(v1, v2)              # ① 法线
norm_n = np.linalg.norm(normal)
if norm_n > 1e-8:
    normal = normal / norm_n
else:
    normal = np.array([0, 0, 1])

palm_axis = mcp_mid - wrist            # ② 主轴
palm_len = np.linalg.norm(palm_axis)
if palm_len > 1e-8:
    palm_axis = palm_axis / palm_len
else:
    palm_axis = np.array([1, 0, 0])

perp = np.cross(normal, palm_axis)     # ③ 横向轴
perp_norm = np.linalg.norm(perp)
if perp_norm > 1e-8:
    perp = perp / perp_norm
else:
    perp = np.array([0, 1, 0])
```

**三个轴怎么来的（数学）**：

- **`normal`（掌面法线）**：取掌根平面上两条不共线向量 `v1`（中指MCP→腕）与 `v2`（小指MCP→腕），**叉积** `v1 × v2` 垂直于两者张成的平面，即**垂直掌面**。归一化后就是掌面单位法线。
- **`palm_axis`（掌长方向）**：直接取"腕 → 中指MCP"方向并归一化。中指是手掌的中线，这个方向近似手掌纵向主轴。
- **`perp`（掌宽方向）**：`normal × palm_axis` 再归一化。因为 `normal ⊥ palm_axis`，叉积结果同时垂直于两者，落在掌面内且沿掌宽方向。三个轴两两正交，构成一个**随每帧手部姿态实时旋转的局部坐标系**——不管手怎么翻、怎么转，角度计算都在"掌面参考系"里做，天然对手腕整体旋转不敏感。

**退化兜底**：若 `norm_n ≤ 1e-8`（手侧对相机，两个向量几乎共线，叉积≈0），法线方向无定义，给固定 `[0,0,1]`。`palm_axis`、`perp` 同理各有兜底。注意 `normal` 的两分支其实是同一个值（代码如此），兜底目的只是保证后续叉积不会再用零向量。

### 16.2 拇指侧摆（索引 0，第 581–592 行）

```python
v_thumb = pts[THUMB_CMC] - wrist
proj_thumb = v_thumb - np.dot(v_thumb, normal) * normal   # 投影到掌面
if np.linalg.norm(proj_thumb) > 1e-8 and palm_len > 1e-8:
    cos_angle = np.dot(proj_thumb, palm_axis) / (np.linalg.norm(proj_thumb) * palm_len)
    cos_angle = np.clip(cos_angle, -1, 1)
    angle = math.degrees(math.acos(cos_angle))
    sign = 1 if np.dot(proj_thumb, perp) > 0 else -1     # 侧摆方向
    angles[0] = sign * min(angle, 20)                     # ±20 封顶
else:
    angles[0] = 0
```

**为什么先投影再算夹角**：
- 拇指 CMC 相对手腕的向量 `v_thumb` 是 3D 的，它既包含"在掌面内的摆动"也包含"垂直掌面的抬起"。侧摆（swing）定义在**掌面内**，所以要先把 `v_thumb` 投影到掌面：`proj = v − (v·normal)·normal`（减去法线方向分量，剩下就是掌面内分量）。
- 投影后与 `palm_axis` 的夹角就是"拇指在掌面上偏离掌长方向多少度"。

**正负号怎么定**：`dot(proj_thumb, perp)` 的符号决定拇指偏向掌宽方向的哪一侧——`perp` 指向哪一侧取决于叉积顺序（左手/右手、左掌/右掌），所以对左右手这个符号物理意义相反。这里用**点积符号直接判向**，配合 GUI 的"弯曲反转/内外展反转"开关做全局补偿。注意 `acos` 给出的是 [0,180] 的无符号角，`sign` 把它变成有符号的侧摆。

**为什么 ±20 封顶**：灵巧手（RY-H1(16)）侧摆舵机行程有限（索引 0 的 GUI 滑杆范围就是 `(-20, 20)`，见 `main_gui.py` 第 126 行）。真实人手拇指侧摆可以很大（>40°），但硬件只支持 ±20°，超出部分饱和即可——既保护舵机，也避免大幅侧摆被当成弯曲干扰。

### 16.3 四指侧摆（索引 3/6/9/12，第 594–617 行）

```python
finger_mcp_map = {"index": INDEX_MCP, "middle": MIDDLE_MCP,
                  "ring": RING_MCP, "pinky": PINKY_MCP}
swing_idx_map = {"index": 3, "middle": 6, "ring": 9, "pinky": 12}
for fname, mcp_idx in finger_mcp_map.items():
    v_finger = pts[mcp_idx] - wrist
    proj = v_finger - np.dot(v_finger, normal) * normal    # 同样投影到掌面
    if np.linalg.norm(proj) > 1e-8 and palm_len > 1e-8:
        cos_angle = np.dot(proj, palm_axis) / (np.linalg.norm(proj) * palm_len)
        cos_angle = np.clip(cos_angle, -1, 1)
        angle = math.degrees(math.acos(cos_angle))
        sign = 1 if np.dot(proj, perp) > 0 else -1
        angles[swing_idx_map[fname]] = sign * min(angle, 20)
    else:
        angles[swing_idx_map[fname]] = 0
```

- 与拇指侧摆**完全相同**的套路：每根手指取 `MCP − WRIST` 向量 → 投影到掌面 → 与 `palm_axis` 求夹角 → 用 `perp` 点积定号 → ±20° 封顶。
- 因为四指的 MCP 都大致沿掌宽方向排开，`proj` 与 `palm_axis` 的夹角天然能反映"这根手指往左/右撇了多少"。

### 16.4 拇指内外展（索引 15）—— 算法 v3（第 619–652 行）

> **这是全模块修复次数最多的算法**。v3 的核心决策：**用无符号绝对值，不用方向锚定符号判断**。

```python
# ① 掌心中心
palm_center = (wrist + mcp_mid) / 2.0
# ② 拇指 TIP 相对掌心、在 perp 方向上的投影（取绝对值！）
v_tip_to_center = pts[THUMB_TIP] - palm_center
lateral_dist = abs(float(np.dot(v_tip_to_center, perp)))
```

**为什么用 TIP 而不是 MCP**：外展/内收动作中，拇指 MCP 几乎贴着食指根部不动，真正的横向位移全在**指尖**——用 TIP 才能在几何上"看到"外展。用 MCP 的话，外展前后向量几乎不变，输出恒不变。

**为什么取绝对值（关键修复）**：`dot(v_tip_to_center, perp)` 的符号取决于拇指尖落在 `perp` 的正侧还是负侧，而 `perp` 的方向由叉积顺序和手型决定——**翻掌时 `perp` 会反向**，符号判断就会翻转。若用符号做方向判定（"正=外展"），翻掌瞬间输出会跳变或恒锁死。v3 只取**无符号的横向距离大小**，方向问题完全交给 GUI 上的 `thumb_abd_reverse` 开关人工设定，从根源上消灭了"符号锚定失效"这一类 bug（详见"常见问题"第 2、3 条）。

```python
# ③ 标尺：半掌宽
palm_w = float(np.linalg.norm(mcp_mid - palm_center))
if palm_w < 1e-6:
    palm_w = 0.01
ratio = lateral_dist / palm_w
```

**为什么用"半掌宽"做标尺**：手掌宽度（中指MCP→掌心）是手的固有尺度，不随拇指姿势变化（拇指长度会随弯曲投影变化），也不随相机距离变化（距离归一化）。`ratio` = "拇指尖横向偏出掌心几个掌宽"，是一个尺度无关的量。

```python
# ④ 死区切除 + 增益放大（线性）
abd_ratio = (ratio - self.thumb_abd_offset) * self.thumb_abd_gain
abd_ratio = np.clip(abd_ratio, 0.0, 1.0)

# ⑤ 软饱和：3x² − 2x³
abd_ratio = 3.0 * abd_ratio * abd_ratio - 2.0 * abd_ratio * abd_ratio * abd_ratio
abd_ratio = float(np.clip(abd_ratio, 0.0, 1.0))
```

**软饱和函数 `s(x) = 3x² − 2x³` 的形状与作用**：

```
s(0)=0, s(1)=1, s(0.5)=0.5（过对称中点）
s'(0)=0, s'(1)=0          ← 两端导数为 0：平滑压扁
s'(0.5)=1.5               ← 中段斜率 1.5：比线性更灵敏
```

- 这是一条 **S 形单调曲线**（smoothstep，图形学常用）：**两端导数为 0**，意味着小位移时输出从 0 平滑起步、大位移时输出趋近 1 时不会"啪"地截断，避免**过早饱和失去区分度**——即"稍微外展一点就有反应（中段放大了 1.5 倍灵敏度），但展到很开时输出不再猛增，留出余量"。
- 相比硬 clip（`min(max(x,0),1)`），软饱和在 0 和 1 附近都是连续可导的，**输出曲线更平滑，抖动更小**。

```python
# ⑥ 方向映射：由开关决定
if self.thumb_abd_reverse:
    abduction = abd_ratio * 110.0          # 外展 → 110°
else:
    abduction = (1.0 - abd_ratio) * 110.0  # 外展 → 0°
angles[15] = np.clip(abduction, 0, 110)
```

- `abd_ratio ∈ [0,1]` 只有"大小"没有"方向"；方向由 `thumb_abd_reverse` 决定映射极性：
  - `reverse=False`（默认）：外展（ratio 大）→ `0°`，内收（ratio 小，并拢）→ `110°`；
  - `reverse=True`：外展 → `110°`，内收 → `0°`。
- 语义对齐：灵巧手角度约定"0°=完全伸展、110°=内收到底"还是反过来，由机械结构决定，所以做成 GUI 可切的开关。
- 最终裁剪到 [0, 110]（索引 15 的 GUI 滑杆范围 `(0, 110)`，`main_gui.py` 第 127 行）。

**完整公式链（v3 一览）**：

```
lateral_dist = | (TIP − 掌心) · perp |                    [米或归一化单位]
palm_w       = | 中指MCP − 掌心 |                          [同一单位]
ratio        = lateral_dist / palm_w                       [尺度无关]
abd_ratio    = clip((ratio − offset) × gain, 0, 1)         [死区+增益]
abd_ratio    = clip(3·abd_ratio² − 2·abd_ratio³, 0, 1)     [软饱和]
angle        = reverse ? abd_ratio×110 : (1−abd_ratio)×110 [方向开关]
angles[15]   = clip(angle, 0, 110)
```

### 16.5 拇指弯曲（索引 1、2，第 654–664 行）

```python
v_cmc_to_mcp = pts[THUMB_MCP] - pts[THUMB_CMC]
v_mcp_to_ip  = pts[THUMB_IP]  - pts[THUMB_MCP]
v_ip_to_tip  = pts[THUMB_TIP] - pts[THUMB_IP]

theta_prox = _angle_between(v_cmc_to_mcp, v_mcp_to_ip)   # 近端弯曲（CMC-MCP 折角）
theta_dist = _angle_between(v_mcp_to_ip,  v_ip_to_tip)   # 远端弯曲（IP 折角）
theta_prox = np.clip(theta_prox, 0, 90)
theta_dist = np.clip(theta_dist, 0, 75)
angles[1] = theta_prox
angles[2] = theta_dist
```

- 拇指用 **CMC→MCP、MCP→IP、IP→TIP 三段向量**，相邻两段求夹角：`CMC-MCP` 段与 `MCP-IP` 段的夹角 = 近端弯曲；`MCP-IP` 与 `IP-TIP` 的夹角 = 远端弯曲。
- 裁剪范围与四指一致：近端 ≤90°、远端 ≤75°。
- **注意**：拇指弯曲**不经过** `bend_scale/bend_offset/bend_gain/deadzone/bend_reverse/per_finger_*` 校准链（与四指不同，见 16.6）——代码对拇指弯曲是"裸算 + 裁剪"，这是刻意的简化（拇指关节少、行程大，GUI 主要靠整体参数调四指）。

### 16.6 四指弯曲（索引 4/5、7/8、10/11、13/14，第 666–713 行）

```python
for finger_idx, finger in enumerate(FINGER_ORDER):
    if finger == "thumb":
        continue
    base = finger_idx * 3          # index→3, middle→6, ring→9, pinky→12
    mcp, pip, dip, tip = FINGER_LANDMARKS[finger]

    if self.use_distance_ratio:
        ratio = self._bend_ratio_by_distance(pts[mcp], pts[pip], pts[tip])
        theta_prox = ratio * 90.0
        theta_dist = ratio * 75.0
    else:
        v_wrist_to_mcp = pts[mcp] - wrist
        v_mcp_to_pip   = pts[pip] - pts[mcp]
        v_pip_to_dip   = pts[dip] - pts[pip]
        angle_prox = _angle_between(v_wrist_to_mcp, v_mcp_to_pip)
        angle_dist = _angle_between(v_mcp_to_pip, v_pip_to_dip)
        theta_prox = np.clip(angle_prox, 0, 90)
        theta_dist = np.clip(angle_dist, 0, 75)
```

- `base = finger_idx * 3`：FINGER_ORDER 的序号直接映射到 16 关节数组（thumb=0 跳过，index=1→base=3，…），`base+1` 是近端、`base+2` 是远端。
- **两种弯曲算法**（由 `use_distance_ratio` 切换）：
  - **向量夹角法（默认）**：近端弯曲 = `(腕→MCP)` 与 `(MCP→PIP)` 的夹角；远端 = `(MCP→PIP)` 与 `(PIP→DIP)` 的夹角。注意近端用的是**腕作参考点**——手指根部抬起时 `腕→MCP` 方向变化，能反映"整指抬起"。
  - **距离比率法**：`_bend_ratio_by_distance(mcp, pip, tip)` 给出 [0,1] 弯曲比，再分别乘 90/75 得到近端/远端角（见第 15 节）。

**校准参数应用链（逐行）**：

```python
# ① 全局：scale（乘）→ offset（加）→ gain（乘）
theta_prox = (theta_prox * self.bend_scale + self.bend_offset) * self.bend_gain
theta_dist = (theta_dist * self.bend_scale + self.bend_offset) * self.bend_gain

# ② 每指：scale（乘）→ offset（加）
s = self.per_finger_scale.get(finger, 1.0)
o = self.per_finger_offset.get(finger, 0.0)
theta_prox = theta_prox * s + o
theta_dist = theta_dist * s + o

# ③ 可选反转
if self.bend_reverse:
    theta_prox = 90.0 - theta_prox
    theta_dist = 75.0 - theta_dist

# ④ 死区
if theta_prox < self.deadzone_deg:
    theta_prox = 0.0
if theta_dist < self.deadzone_deg:
    theta_dist = 0.0

# ⑤ 最终裁剪
theta_prox = np.clip(theta_prox, 0, 90)
theta_dist = np.clip(theta_dist, 0, 75)

angles[base + 1] = theta_prox
angles[base + 2] = theta_dist
```

完整公式：

```
θ_raw → (θ_raw·bend_scale + bend_offset)·bend_gain       全局校准
      → ×per_finger_scale[finger] + per_finger_offset[finger]   每指校准
      → (可选) 90/75 − θ                                   反转
      → θ < deadzone_deg ? 0 : θ                           死区
      → clip(θ, 0, 90/75)                                  行程裁剪
```

- **scale 与 gain 的区别**：二者都是乘法，历史遗留的双参数——scale 是"原始几何角的缩放"，gain 是"输出级增益"，分开调便于在 GUI 上分别补偿"手型比例差异"与"舵机行程差异"。实际效果叠加。
- **每指参数**：不同手指的固有灵敏度不同（小指最飘、食指最稳），`per_finger_scale/offset` 用于单指微调；默认 1.0/0.0 = 不干预。
- **反转**：`90−θ` / `75−θ`，适配"0°=弯曲、90°=伸直"这类相反约定的下游。
- **死区**：消除传感器噪声导致的微小假弯曲（默认 1°）。
- **裁剪**：与侧摆 ±20° 同理，保护硬件行程。

### 16.7 返回值

```python
return angles, lateral_dist
```

- `angles`：16 元素 list（浮点度）。
- `lateral_dist`：拇指横向距离（**绝对值**，未除标尺的原始量），供 GUI 调试显示。

---

## 17. `draw_skeleton()` 骨架可视化（第 717–748 行）

```python
def draw_skeleton(self, frame, results, color=(0, 255, 0), line_px=2):
    import cv2                      # 延迟导入：不画骨架就不依赖 cv2
    out = frame.copy()
    if not results:
        return out
    h, w = out.shape[:2]
    for r in results:
        pts = r.landmarks           # 归一化坐标
        for a, b in HAND_CONNECTIONS:
            p1 = (int(pts[a][0] * w), int(pts[a][1] * h))
            p2 = (int(pts[b][0] * w), int(pts[b][1] * h))
            cv2.line(out, p1, p2, color, line_px, cv2.LINE_AA)   # 连线（绿色，抗锯齿）
        for p in pts:
            cv2.circle(out, (int(p[0] * w), int(p[1] * h)),
                       4, (0, 0, 255), -1, cv2.LINE_AA)          # 关键点（红色实心圆）
    return out
```

- `import cv2` 放在函数内**延迟导入**：让不画图的使用路径（如纯控制端）无需 OpenCV。
- 用 `HAND_CONNECTIONS` 画骨架线（默认绿色 BGR `(0,255,0)`），21 个关键点画红点（BGR `(0,0,255)`）。
- 归一化坐标 × 图像宽高还原像素位置，与 `_convert_landmarks_to_3d` 的取像素逻辑一致。

---

## 18. `close()` 与 `bgr2rgb()`（第 750–769 行）

```python
def close(self):
    """释放 MediaPipe 资源"""
    if self._landmarker is not None:
        try:
            self._landmarker.close()
        except Exception:
            pass
```

- 释放 Tasks API 底层的推理资源；异常吞掉（close 失败不致命）。GUI 退出时调用。

```python
def bgr2rgb(bgr: np.ndarray) -> np.ndarray:
    return bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr
```

- `[:, :, ::-1]` 反转通道顺序（BGR→RGB），`.copy()` 保证内存连续（`::-1` 会产生非连续视图，MediaPipe 不接受）。
- 不是 3 通道的输入原样返回（容错）。

---

## 19. 参数校准说明（调参速查表）

所有参数最终都作用于 `_landmarks_to_angles16()`。下表说明**每个参数改大/改小会发生什么**，以及何时该动它：

### 19.1 四指/拇指弯曲类

| 参数 | 公式位置 | 改大的效果 | 何时调整 |
|------|----------|-----------|----------|
| `bend_scale` | `θ×scale` | 所有弯曲角按比例放大，动作更"夸张" | 手大/手小导致整体弯曲偏小或偏大时 |
| `bend_offset` | `θ+offset` | 所有弯曲角整体抬高（加性） | 手指伸直时输出仍有底噪/偏置 |
| `bend_gain` | `(…)×gain` | 输出级整体放大（≥0.1 保护） | 舵机行程与视觉角换算不匹配时做末级补偿 |
| `deadzone_deg` | `θ<deadzone→0` | 死区变大，小弯曲被吞掉 | 静止时手指轻微抖动不停输出小角度 |
| `bend_reverse` | `90−θ / 75−θ` | 弯曲方向整体取反 | 下游约定是"0=弯、90=直"时 |
| `use_distance_ratio` | 切换算法 | 弯曲计算从夹角法换成长度比率法 | 夹角法在特定手型下不稳定时试试它 |
| `per_finger_scale` | `θ×s` | 只放大某根手指 | 单指灵敏度异常（如小指偏大） |
| `per_finger_offset` | `θ+o` | 只抬升某根手指 | 单指伸直不归零 |

> 调节顺序建议：先 `bend_scale` 对齐整体幅度 → `bend_offset` 对齐伸直零位 → `deadzone` 压噪 → 最后用 per_finger 修单指。

### 19.2 拇指内外展类（v3 公式：`clip((ratio−offset)·gain)` → 软饱和 → 方向映射）

| 参数 | 公式位置 | 改大的效果 | 何时调整 |
|------|----------|-----------|----------|
| `thumb_abd_offset` | `ratio−offset` | 死区变大：拇指并拢（小 ratio）时输出**更早被压到 0 方向**，切除底部无效区间 | 手指并拢时内外展输出不为 0（抖动），加大它 |
| `thumb_abd_gain` | `(…)×gain` | 有效区放大：同样的横向位移产生更大的 ratio 变化 → 输出对位移更敏感、更快到饱和 | 外展动作幅度偏小、区分度不足时加大 |
| `thumb_abd_reverse` | 极性开关 | 切换"外展↔0°/110°"的对应关系 | 机械/电气接法导致内外展方向反了时（GUI 一键切换） |

> 标定手感：先调 `offset` 让"完全并拢"时输出稳定在 0（或 110，取决于 reverse），再调 `gain` 让"完全外展"时输出恰好饱和到另一端，避免中段过于灵敏或迟钝。

### 19.3 检测类（不参与角度公式）

| 参数 | 作用 |
|------|------|
| `max_hands` | 同时检测的手数（模仿演示通常 1） |
| `min_detection_confidence` / `min_tracking_confidence` | 越高越严格、漏检越多，越低越容易误检；环境光差时适当调低 |

---

## 20. 常见问题（FAQ）

### Q1：报错"未找到手部模型文件 hand_landmarker.task"

```
RuntimeError: 未找到手部模型文件 hand_landmarker.task。请下载并放到项目根目录或 lib/：…
```

**原因**：`_find_model_file()` 按 `cwd → 包根 → 包根/lib → vision/` 四个位置都找不到模型。

**排查**：
1. 确认模型是否真的下载了（文件大小约 7~8 MB，别用 0 字节的占位文件）。
2. 确认文件名**完全一致**：`hand_landmarker.task`（Tasks API 的 `.task` 格式，不是旧版 `.tflite`）。
3. 确认放置位置命中搜索列表：放在**项目根目录**（`rycan_hand_windows/` 同级的 `hand_landmarker.task`）、`rycan_hand_windows/lib/`、或**运行时的 cwd** 下都可以。
4. 用 `model_path=` 参数显式指定路径可绕过搜索。
5. 从报错信息里的官方 URL 重新下载：`https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`。

### Q2：握拳时拇指内外展（索引 15）输出跳变/乱跳

**现象**：明明握拳过程中手没动，内外展角度却大幅抖动。

**原因分析**（结合 v3 公式逐环节看）：
1. **握拳时拇指 TIP 被遮挡**，MediaPipe 的 2D 关键点抖动大 → 归一化坐标下 `lateral_dist` 抖动。
2. 若有深度：`_convert_landmarks_to_3d` 取 TIP 单像素深度，遮挡边缘深度跳变 → 3D 下 `lateral_dist` 抖动更大。
3. 抖动经过 `gain` 放大 → `abd_ratio` 在 0~1 之间来回 → 软饱和区斜率 1.5 又放大中段 → 输出剧烈抖动。

**对策（按优先级）**：
- 让**后处理兜底**：`fist_confidence`（深度确认握拳 ≥0.6）会让 `postprocess.py` 跳过异常判定，同时 `abduct_max_delta`（内外展限速，GUI 默认 2°/帧）直接限制单帧变化——这是设计好的主防线。
- 调小 `thumb_abd_gain`（例如 0.8 → 0.5），降低对抖动的放大。
- 适当加大 `thumb_abd_offset`，把并拢状态的底部区间切除，让抖动落在死区里。
- 保证光照/距离合适，减少 MediaPipe 关键点本身的抖动（治本）。

### Q3：翻掌（手心朝下/朝上切换）后内外展失效，输出恒不变

**现象**：把手翻过来，拇指内外展怎么动输出都不变，或者突然反了。

**根因（v3 之前的设计缺陷，已修复）**：旧算法用**方向锚定符号判断**——例如"`dot(TIP−掌心, perp) > 0` 判为外展方向"。但 `perp` 的方向由 `normal = (中指MCP−腕) × (小指MCP−腕)` 的叉积决定，**翻掌时 `v1`、`v2` 的相对方位翻转，`perp` 整体反向**，于是：
- 符号判断与真实外展方向失去固定对应关系 → 输出被锁死在某一侧（恒不变）；
- 手型变化（比如握拳时掌根形变）也会让 `normal` 轻微翻转 → 符号偶然翻转 → 输出跳变。

**v3 的修复**（本文件第 619–652 行）：
1. **只用无符号绝对值** `lateral_dist = |dot(TIP−掌心, perp)|` —— 不管 `perp` 朝哪，横向距离大小不变，彻底消灭"符号锚定失效"这类 bug；
2. 方向问题**从算法里拿走**，交给 GUI 上的 `thumb_abd_reverse` 开关人工设定（安装时按机械结构定一次即可）。
3. 配套：用"半掌宽"做标尺（尺度无关）＋ 软饱和（防饱和抖动）＋ 死区（防并拢抖动）。

> 结论：**内外展方向永远不要用算法自动判断正负号**——3D 几何在翻掌/遮挡下不可靠，人工开关 + 无符号距离才是稳的。

### Q4：为什么有时候角度计算回退到"归一化坐标"？有没有影响？

当深度图缺失、或 3D 坐标里有 NaN（关键点越界/深度超出 0~3000mm/深度为 0）时，`_landmarks_to_angles16` 整体回退用 `pts_norm` 计算。

- **影响**：角度数值仍是"合理的"，因为 MediaPipe 的归一化坐标本身包含手部相对几何（z 是相对深度）；但**绝对尺度与旋转不变性会变差**——手离相机近时角度偏大、远时偏小，翻掌时 2D 投影的侧摆会失真。
- **建议**：生产环境务必保证深度图与内参同时传入；演示环境可以接受 2D 回退，但握拳置信度会变成 `None`，后处理的"深度辅助防抖"失效（只剩方向一致性判定）。

### Q5：为什么四指弯曲近端用"腕→MCP"而不是"MCP→掌根"作参考？

`angle_prox = _angle_between(腕→MCP, MCP→PIP)`。以腕为参考的好处：手指从掌根"抬起"（MCP 相对手腕移动）也会被计入近端弯曲，接近真实"掌指关节"的解剖学意义；若用 `(MCP 自身方向)` 作参考则只能看到 PIP 的折叠。代价是**整手平移/旋转时**腕参考会引入少量耦合——这正是一帧一帧独立推理、且靠后处理平滑来吸收的原因。

### Q6：为什么侧摆要"投影到手掌平面"再算夹角？

不投影直接算 3D 夹角，会把"手指垂直掌面抬起"（这属于弯曲/整指抬起，不是侧摆）也混进侧摆角度。投影到掌面后只剩掌面内分量，侧摆与弯曲**正交解耦**：侧摆只看掌面内摆动，弯曲只看段间折角，两者互不污染。

### Q7：`fist_confidence` 为 None 是什么情况？

只有"深度图缺失"或"3D 坐标存在 NaN"两种可能（`_compute_fist_confidence` 第一行就返回 None）。`None` 语义是"无法用深度确认"，后处理会退回纯方向一致性判定（`postprocess.py` 里 `depth_confirms_fist = fist_confidence is not None and >= 0.6`，None 时该分支不生效）。

---

## 21. 与上下游模块的衔接（跨文件速览）

| 模块 | 方向 | 关系 |
|------|------|------|
| `camera/camera_module.py`、`lib/L515_driver.py` | 上游 | 提供 RGB（BGR）帧、深度图（毫米）、相机内参 `{fx, fy, ppx, ppy}` |
| `vision/postprocess.py` | 下游 | 消费 `joint_angles_deg`（16 角）与 `fist_confidence`（握拳背书，≥0.6 跳过异常抑制） |
| `hand/angles2motor.py`、`hand/hand_controller.py` | 下游 | 把 16 关节角度映射为 16 舵机角度并下发 |
| `gui/main_gui.py` | 交互 | 通过 `update_params()` 热调参（滑块范围与本文参数对应，如内外展滑杆 `(0,110)`）；读取 `lateral_dist`、`fist_confidence` 做调试显示；`process()` 输出经 `postprocess.update()` 后再用 |
| `lib/vision_hand_ctrl.py` | 参考实现 | 旧版纯 2D 手控算法的参考（v3 注释里引用了它的"横向距离/拇指长度"归一化思路，但本文件改为"半掌宽标尺 + 软饱和 + 开关定方向"的稳定版本） |

---

*文档结束。本文档覆盖 hand_pose.py 全部 769 行：常量定义、模块级函数、HandResult 数据结构、HandPoseEstimator 全生命周期（构造→检测→角度计算→绘制→释放），并对核心算法 `_landmarks_to_angles16`（含内外展 v3）做了逐公式推导。*
