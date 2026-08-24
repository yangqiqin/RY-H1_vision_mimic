# 05 · camera_module.py 代码详解

> **文件**：`rycan_hand_windows/camera/camera_module.py`（Windows / Ubuntu 通用）
>
> **模块职责**：统一封装"图像采集"。对外只提供 **RGB 帧**（深度帧可选），隐藏两类底层来源的差异：
>
> 1. 普通 USB 摄像头（UVC 协议，走 OpenCV `VideoCapture`）；
> 2. Intel RealSense **L515 / D435** 等 RGB-D 相机（走 `pyrealsense2`，同时给出 RGB + 深度 + 相机内参）。
>
> **文档目标**：不读源码，仅凭本文即可完全理解本文件的每个函数、每条分支、每个设计决策，以及常见的 L515 排障方法。
>
> **相关参考**：`lib/L515_driver.py`（L515 标准驱动参数）、知识库 `README_1.md`《L515 PyLive Toolkit》。

---

## 目录

1. [模块在系统中的位置（架构图）](#一模块在系统中的位置架构图)
2. [模块级常量与全局状态](#二模块级常量与全局状态)
3. [模块级函数详解](#三模块级函数详解)
4. [CameraModule 类总览](#四cameramodule-类总览)
5. [`__init__`：构造函数](#五__init__构造函数)
6. [`_open_usb`：打开 USB 摄像头](#六_open_usb打开-usb-摄像头)
7. [`_open_realsense`：打开 RealSense RGB-D 相机](#七_open_realsense打开-realsense-rgb-d-相机)
8. [`read`：读取一帧（核心方法）](#八read读取一帧核心方法)
9. [`get_rgb` / `get_depth` / `get_intrinsics`：便捷取值](#九get_rgb--get_depth--get_intrinsics便捷取值)
10. [`pixel_to_point`：像素反投影三维坐标（针孔模型推导）](#十pixel_to_point像素反投影三维坐标针孔模型推导)
11. [`release` 与上下文管理器 `__enter__` / `__exit__`](#十一release-与上下文管理器-__enter__--__exit__)
12. [L515 专项排障指南](#十二l515-专项排障指南)
13. [与上层 GUI / hand_pose 的接口约定](#十三与上层-gui--hand_pose-的接口约定)

---

## 一、模块在系统中的位置（架构图）

CameraModule 位于"采集层"，是视觉动作模仿系统数据链路的**第一环**：它只负责把"相机硬件"变成"内存里的帧"，不关心手势识别、3D 坐标换算等上层逻辑；上层（GUI / 测试脚本 / hand_pose）通过统一接口消费它。

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         上层调用方（GUI / 测试脚本）                    │
│   cam.read()            cam.get_intrinsics()        cam.release()     │
└───────────────┬──────────────────────────┬───────────────────────────┘
                │ 统一接口                  │
                ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CameraModule（本文件：camera_module.py）            │
│                                                                      │
│   ┌──────────────┐          ┌─────────────────────────────┐          │
│   │ _open_usb()  │          │ _open_realsense()           │          │
│   │ OpenCV       │          │ pyrealsense2 (L515/D435)    │          │
│   │ VideoCapture │          │  版本硬校验 → 枚举设备        │          │
│   └──────┬───────┘          │  配置双流 → rs.align → 内参   │          │
│          │                  └──────────────┬──────────────┘          │
│          └─────────────┬───────────────────┘                         │
│                        ▼                                             │
│                 read()：取一帧                                       │
│            ┌──────────┼───────────┐                                  │
│            ▼          ▼           ▼                                  │
│         RGB(BGR)    Depth(mm)   内参{fx,fy,ppx,ppy}                  │
└────────────┼──────────┼───────────┼──────────────────────────────────┘
             │          │           │
             ▼          ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       hand_pose（3D 手部姿态）                         │
│   对 RGB 帧做手部关键点检测 → 得到像素 (u, v)                           │
│   用 pixel_to_point(u, v) 反投影 → 相机系 3D 坐标 [x, y, z]（米）       │
│   → 关节角度 / 动作模仿 / 遥操作                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**关键点**：`read()` 是唯一的数据出口——一次调用同时带回 RGB 帧、深度帧、以及（从 RealSense 内参反投影）3D 计算所需的一切。深度帧对 USB 摄像头恒为 `None`，上层据此分支即可，无需感知底层是哪种相机。

---

## 二、模块级常量与全局状态

```python
logger = logging.getLogger("camera")          # 模块级日志器，统一日志命名空间
L515_PYREALSENSE_VERSION = "2.54.2.5684"      # L515 必须固定的 pyrealsense2 版本
LAST_REALSENSE_ERROR = ""                     # 最近一次 RealSense 诊断信息（全局字符串）
```

| 名字 | 类型 | 含义 |
|---|---|---|
| `logger` | `logging.Logger` | 模块所有日志统一走 `camera` 这个名字空间，便于在配置中单独过滤/调整级别。 |
| `L515_PYREALSENSE_VERSION` | `str` | 依据 README_1.md：**L515 是 Intel 已停产的 LiDAR 设备，librealsense 2.55+ 已移除其支持**，因此必须安装 `pyrealsense2==2.54.2.5684`（即捆绑 librealsense 2.54.x）。这个常量在多处被引用：报错提示、安装指引、版本校验。 |
| `LAST_REALSENSE_ERROR` | `str` | **全局**变量（模块级而非类级），记录最近一次 RealSense 诊断失败的完整原因（含提示语），供上层 `selfcheck` / `diag` 界面直接展示"具体为什么失败"，避免用户只看一个笼统的异常。注意：`check_realsense_devices()` 内部用 `global LAST_REALSENSE_ERROR` 声明后写入。 |

> 💡 **为什么版本要"硬钉死"？** librealsense 2.55.0 起移除了对 L515（LiDAR 深度传感器）的固件支持。若装了更新版本，L515 会表现为"设备能枚举到但流起不来"或直接枚举不到，极易误判为硬件故障。所以本模块把版本校验做成**硬门槛**：版本不对，直接拒绝打开并给出安装命令。

---

## 三、模块级函数详解

三个函数构成一个"自检小工具链"，专门服务于 L515 这类"版本敏感 + 权限敏感"的设备：

```text
check_realsense_devices()
        │
        ├─ 1. import pyrealsense2（没有 → 报错提示安装，返回 []）
        │
        ├─ 2. _warn_if_wrong_version()  ──►  _get_pyrealsense_version()
        │       版本不是 2.54.x → ERROR 日志          │
        │                                          ▼
        │                                   1. importlib.metadata 查 pip 元数据
        │                                   2. 失败则退回 rs.__version__
        │                                   3. 再失败则 "unknown"
        │
        └─ 3. rs.context().query_devices() 枚举设备（失败 → 记 LAST_REALSENSE_ERROR，返回 []）
                 ▼
        逐台读取 serial / name / firmware，返回 [{"serial","name","fw"}, ...]
```

### 3.1 `check_realsense_devices() -> List[dict]`

**作用**：列出所有已连接的 Intel RealSense 设备，并顺带校验 pyrealsense2 版本。供 GUI 的"设备检测"功能与诊断页使用。

**返回**：`[{"serial": ..., "name": ..., "fw": ...}, ...]`；**无设备返回 `[]`**（空列表，不是异常）。

**逻辑分四步**：

1. **懒加载检测**：`try: import pyrealsense2 as rs`，若 `ImportError` → 记 ERROR 日志"未安装 pyrealsense2：请执行 pip install pyrealsense2==2.54.2.5684"，返回 `[]`。这一步保证：普通 USB 用户即使没装 pyrealsense2，调用此函数也**不会崩溃**。
2. **版本告警**：调 `_warn_if_wrong_version()`（见 3.3），版本非 2.54.x 时记 ERROR 日志。注意这里是"告警不阻断"——枚举照常进行，因为即使版本不对，也可能有别的 RealSense 设备（如 D435）可用。
3. **枚举设备**：
   - `ctx = rs.context()` 创建 librealsense 上下文（相当于与运行时握手）；
   - `devs = list(ctx.query_devices())` —— **立即物化**成列表是关键：librealsense 的 `query_devices()` 返回的是**惰性枚举器**，如果不立刻 `list()`，真正的硬件访问会推迟到遍历时才发生，异常发生点难以定位；物化后任何枚举异常都在这里抛出。
   - 枚举异常处理（`except Exception`）：提取错误字符串，**若包含 `0x80070005` / `Access denied` / `拒绝访问`**，拼接管理员权限提示（Windows 权限问题），记 ERROR 日志 + 写入全局 `LAST_REALSENSE_ERROR`，返回 `[]`。
4. **逐台取信息**：对每台设备用 `dev.get_info(...)` 读取 `serial_number`、`name`、`firmware_version`；单台失败仅 WARNING 并跳过（不因一台设备损坏而放弃整批）。

> 💡 **0x80070005 是什么**：Windows 的 `ERROR_ACCESS_DENIED`（拒绝访问）。USB 设备在 Windows 上被其它进程占用、或以非管理员身份访问受保护设备接口时常见。提示语建议"以管理员身份运行终端/程序"，或检查"设置 → 隐私 → 相机"权限开关。

### 3.2 `_get_pyrealsense_version() -> str`

**作用**：取 pyrealsense2 的版本字符串。**为什么绕这么大一圈**：`pyrealsense2` 2.54 的 Python 包**没有 `__version__` 属性**（README_1.md 的已知坑），所以先走 pip 元数据。

**逻辑（两级回退）**：

1. `importlib.metadata.version("pyrealsense2")` —— 从已安装包的发行元数据（`*.dist-info/METADATA`）读版本。返回空字符串时兜底为 `"unknown"`。
2. 若元数据读取抛异常（如包损坏/未装），回退 `import pyrealsense2 as rs`，取 `getattr(rs, "__version__", "unknown")`（万一未来版本补上了该属性）。
3. 全部失败 → `"unknown"`。

> 该函数**永不抛异常**，任何情况下都返回一个可打印的字符串，保证后续版本校验不会因"查版本本身出错"而连锁崩溃。

### 3.3 `_warn_if_wrong_version() -> bool`

**作用**：版本兼容性检查。**返回 `True` = 兼容（2.54.x），`False` = 不兼容**。

**逻辑**：

```python
ver = _get_pyrealsense_version()
ok = str(ver).startswith("2.54")
```

- 判定标准是**前缀匹配 `"2.54"`**（涵盖 2.54.0 ~ 2.54.2.x 等所有 2.54 小版本）；
- 不兼容时记 ERROR 日志，明确告知"librealsense 2.55+ 已移除 L515 支持"，并给出安装命令 `pip install pyrealsense2==2.54.2.5684`。

**两种调用场景的行为差异**：

| 调用方 | 行为 |
|---|---|
| `check_realsense_devices()` | 只告警（记日志），**继续枚举**——因为可能连接的是 D435 等其他设备 |
| `_open_realsense()` | 硬校验：返回 `False` 直接 `raise RuntimeError`，**拒绝打开**——因为打开路径默认目标就是 L515 |

---

## 四、CameraModule 类总览

```python
class CameraModule:
    """摄像头采集模块。"""
```

**一句话定位**：一个"双后端"的相机对象——构造时按 `use_realsense` 决定走哪条打开路径，之后所有调用方只面对统一方法（`read` / `get_rgb` / `get_depth` / `get_intrinsics` / `pixel_to_point` / `release`），无需关心后端差异。

**内部状态一览**（全部在 `__init__` 初始化）：

| 属性 | 初始值 | 含义 |
|---|---|---|
| `use_realsense` | 参数 | 是否走 RealSense 后端（构造后不再可变） |
| `width / height / fps` | 1280 / 720 / 30 | RGB 流参数（L515_driver.py 标准参数） |
| `depth_width / depth_height / depth_fps` | 1024 / 768 / 30 | **深度流独立**分辨率参数 |
| `_align` | `None` | `rs.align` 对象：深度对齐到彩色（仅 RealSense） |
| `_rs_pipeline` | `None` | RealSense 管线（`rs.pipeline`），未打开时为 `None` |
| `_rs_profile` | `None` | 管线启动后返回的流配置档案（取内参用） |
| `_cap` | `None` | OpenCV `VideoCapture`（USB 后端），未打开时为 `None` |
| `_intrinsics` | `None` | 相机内参 dict：`{fx, fy, ppx, ppy, width, height, model}` |

> ⚠️ **两条后端路径互斥**：USB 后端只用 `_cap`，RealSense 后端只用 `_rs_pipeline` / `_rs_profile` / `_align`。`release()` 会**同时**检查并清理两者，保证即使状态异常也不漏资源。

---

## 五、`__init__`：构造函数

**签名**：

```python
def __init__(
    self,
    source: int = 0,               # 普通摄像头索引（OpenCV），默认 0
    use_realsense: bool = False,   # 是否使用 Intel RealSense（L515/D435 等）
    width: int = 1280,             # RGB 流宽度
    height: int = 720,             # RGB 流高度
    fps: int = 30,                 # RGB 流帧率
    serial: Optional[str] = None,  # RealSense 序列号（多设备时指定；None=第一台）
    depth_width: int = 1024,       # 深度流宽度（独立于 RGB！）
    depth_height: int = 768,       # 深度流高度
    depth_fps: int = 30,           # 深度流帧率
):
```

**要点**：

1. **默认值就是 L515 标准参数**（与 `lib/L515_driver.py` 一致、README_1.md 例 1 同款）：`RGB 1280x720 @30FPS + depth 1024x768 @30FPS`。调用方不传参即可直接跑通 L515。
2. **深度流必须独立设分辨率**：L515 的彩色与深度传感器分辨率不同，RGB 与深度**不能共用一个分辨率参数**——这是 L515 连接成功的关键之一（README_1.md 明确要求"深度流与 RGB 流必须分开设分辨率"）。因此构造函数拆成 `width/height` 与 `depth_width/depth_height` 两组。
3. **分支打开**：
   - `use_realsense=True` → `self._open_realsense(serial)`（打开失败会抛 `RuntimeError`，构造即失败）；
   - 否则 → `self._open_usb(source)`。
4. **失败语义**：构造函数可能抛异常（打不开摄像头 / RealSense 版本不对 / 设备枚举失败）。调用方应把构造放在 `try/except` 里，或在 GUI 中提前用 `check_realsense_devices()` 预检。

---

## 六、`_open_usb`：打开 USB 摄像头

```python
def _open_usb(self, source: int):
    self._cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)  # Windows 用 DirectShow
    if not self._cap.isOpened():
        self._cap = cv2.VideoCapture(source)             # 回退默认后端
    if not self._cap.isOpened():
        raise RuntimeError(...)
    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
    self._cap.set(cv2.CAP_PROP_FPS, self.fps)
```

**为什么优先 `CAP_DSHOW`（Windows DirectShow）**：

- OpenCV 的 `VideoCapture` 在 Windows 上可以选多种后端：MSMF（Media Foundation）、DSHOW（DirectShow）、VFW 等，默认后端因版本/编译而异。
- **DirectShow 在 Windows 上是事实上的稳定选择**：对 UVC 摄像头兼容性好、延迟可控、分辨率/帧率设置行为可预期；MSMF 后端在部分摄像头上存在分辨率设置无效、花屏、偶发打不开的问题。
- 注意：`cv2.CAP_DSHOW` 是 **Windows 专属**的常量。Linux 上此路径用不到——Ubuntu 走的是 V4L2，OpenCV 默认后端即可。因此代码对"Windows 用 DSHOW、其它平台默认"做了统一处理：**先试 DSHOW，失败回退默认**，两全其美。

**回退逻辑（双保险）**：

1. 第一次用 `CAP_DSHOW` 打开；若 `isOpened()` 为假（例如该摄像头在 DSHOW 下不可用），
2. 用 `cv2.VideoCapture(source)`（不指定后端 → 系统默认后端）重试；
3. 仍失败才抛 `RuntimeError`：`无法打开摄像头 source=...`（提示 `/dev/videoN` 或 Windows 摄像头）。

**参数设置**：用 `set(CAP_PROP_FRAME_WIDTH/HEIGHT/FPS)` 请求 `width/height/fps`。

> ⚠️ **注意**：UVC 摄像头对分辨率的支持有限（只支持它固件里预设的几种），`set` 是"尽力而为"——请求 1280x720 但设备只支持 640x480 时，OpenCV 会静默用 640x480，`get` 才能读到实际值。本文件没有强制校验实际分辨率，属有意简化（对演示/采集场景足够）。

---

## 七、`_open_realsense`：打开 RealSense RGB-D 相机

这是本文件**最复杂、注释最重**的方法，完整流程如下：

```text
_open_realsense(serial)
  │
  ├─ ① import pyrealsense2  ── 失败 → RuntimeError（提示 pip install pyrealsense2==2.54.2.5684）
  │
  ├─ ② 版本硬校验 _warn_if_wrong_version()
  │      False → RuntimeError（版本不兼容 L515，拒绝打开）        ← 硬门槛
  │
  ├─ ③ 枚举设备 rs.context().query_devices()
  │      ├─ 枚举异常（0x80070005 → 附管理员权限提示）→ RuntimeError
  │      └─ 0 台设备 → RuntimeError（USB3.0 / 驱动 / Viewer 验证 4 条排查建议）
  │
  ├─ ④ serial 归一化：None → 取第一台设备的序列号
  │
  ├─ ⑤ 创建 pipeline + config
  │      cfg.enable_device(serial)                        ← 锁定目标设备
  │      cfg.enable_stream(color, W, H, bgr8, fps)        ← RGB 流
  │      cfg.enable_stream(depth, DW, DH, z16, dfps)      ← 深度流（独立分辨率，失败仅告警）
  │
  ├─ ⑥ pipeline.start(cfg)  ── 失败 → RuntimeError（提示分辨率组合 + L515 标准参数）
  │
  ├─ ⑦ rs.align(rs.stream.color)  ── 失败则 _align=None（降级为不强制对齐）
  │
  ├─ ⑧ 从 profile 取彩色流内参 → self._intrinsics = {fx, fy, ppx, ppy, width, height, model}
  │
  └─ ⑨ INFO 日志确认打开（RGB + 深度 + 是否已对齐）
```

### ① import 与版本硬校验

```python
try:
    import pyrealsense2 as rs
except ImportError as exc:
    raise RuntimeError(f"使用 RGB-D 相机需先安装 pyrealsense2（L515 必须固定版本）："
                       f"pip install pyrealsense2=={L515_PYREALSENSE_VERSION}") from exc

if not _warn_if_wrong_version():
    raise RuntimeError(f"pyrealsense2 版本不兼容 L515：请执行 pip install pyrealsense2=={L515_PYREALSENSE_VERSION}"
                       f"（librealsense 2.55+ 已移除 L515 支持）")
```

- `from exc` 保留原始异常链，调试时可回溯根因。
- 版本校验在这里是**硬门槛**（区别于 `check_realsense_devices` 的软告警）：既然用户显式选择了 RGB-D 后端，而默认目标设备就是 L515，版本不对直接拒绝打开，把问题暴露在**构造阶段**而不是第一帧读取时。

### ③ 枚举设备与 0x80070005 处理

```python
ctx = rs.context()
devs = list(ctx.query_devices())   # 立即物化，异常在这里集中爆发
```

- 枚举异常时：若错误信息含 `0x80070005`，追加"以管理员身份运行 / 检查设置→隐私→相机权限"提示；
- `len(devs) == 0` 时给出**四条排查建议**（即"找不到设备"标准动作）：
  1. `pip show pyrealsense2` 确认版本是 2.54.x；
  2. **USB3.0 直连**（L515 必须 USB3.0 带宽，经 USB2 集线器必失败）；
  3. 安装 **Intel RealSense SDK 2.0 运行时**（驱动层）；
  4. 供电/线缆问题——先用官方 **Intel RealSense Viewer** 验证设备能否出图。

### ⑤⑥ 双流配置与启动

```python
cfg.enable_device(serial)   # 多设备时锁定目标；None 时上面已归一化为第一台
cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
try:
    cfg.enable_stream(rs.stream.depth, self.depth_width, self.depth_height,
                      rs.format.z16, self.depth_fps)
except Exception as exc:
    logger.warning("深度流配置失败（仅用 RGB）：%s", exc)
```

- **颜色格式选 `bgr8`**：与 OpenCV 的 BGR 约定一致，取出的帧可直接给 OpenCV 处理，无需转换。
- **深度格式 `z16`**：16 位无符号整数，**单位是毫米（mm）**，这是后面 `pixel_to_point` 除以 1000 的依据。
- 深度流配置失败**只告警不致命**（降级为"仅 RGB"模式）——某些分辨率组合不被固件支持时，RGB 仍可用。
- `pipeline.start(cfg)` 失败 → `self._rs_pipeline = None` 置空（避免半初始化状态残留），抛 `RuntimeError`，提示**分辨率组合可能不被支持**，并给出 L515 标准参数 `depth 1024x768 + RGB 1280x720 @30FPS` 作为对照。

### ⑦ 深度对齐 `rs.align(rs.stream.color)`

```python
try:
    self._align = rs.align(rs.stream.color)
except Exception:
    self._align = None
```

`rs.align(rs.stream.color)` 创建一个"**把深度帧重投影到彩色相机坐标系**"的对齐器。因为 L515 的深度传感器与彩色传感器**物理位置不同**（视差基线），同一物体在两个传感器图像上的像素位置有偏移；对齐后，**深度图和 RGB 图逐像素一一对应**（同一 `(u, v)` 处，RGB 是某点的颜色，深度就是同一点的毫米距离）。这正是 `pixel_to_point` 能"拿 RGB 上的关键点像素 → 直接查深度图取该点深度"的前提。创建失败仅置 `None`，`read()` 里会自动跳过对齐步骤（降级）。

### ⑧ 取内参

```python
color_profile = self._rs_profile.get_stream(rs.stream.color)
intr = color_profile.as_video_stream_profile().get_intrinsics()
self._intrinsics = {
    "fx": intr.fx, "fy": intr.fy,
    "ppx": intr.ppx, "ppy": intr.ppy,
    "width": intr.width, "height": intr.height,
    "model": intr.model,
}
```

- `get_stream(rs.stream.color)` 从启动档案里拿到**实际生效**的彩色流（注意：实际分辨率可能与请求不同）；
- `as_video_stream_profile()` 转成视频流档案后才能取内参；
- `get_intrinsics()` 返回 librealsense 内参结构：`fx`（x 方向焦距，像素）、`fy`（y 方向焦距，像素）、`ppx`（主点 x，像素）、`ppy`（主点 y，像素），另有实际宽高与畸变模型。
- 存成 **dict** 而不是裸结构体：上层（GUI/hand_pose）只依赖 `{fx, fy, ppx, ppy}` 四个键，与后端解耦，且便于 JSON 序列化展示。

> ⚠️ **内参为什么重要**：内参是"像素坐标 ↔ 相机系 3D 坐标"换算的唯一桥梁，没有它，`pixel_to_point` 无从计算。普通 USB 摄像头没有官方内参，所以 `_intrinsics` 恒为 `None`，`pixel_to_point` 也据此拒绝工作。

---

## 八、`read`：读取一帧（核心方法）

**签名与返回**：

```python
def read(self, timeout_ms: int = 5000) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
```

返回 `(rgb_bgr, depth)`：

| 后端 | `rgb_bgr` | `depth` |
|---|---|---|
| USB 摄像头 | BGR 帧 `np.ndarray` | 恒为 `None` |
| RealSense | BGR 帧 `np.ndarray`（uint8） | uint16 深度帧，**单位毫米**，已对齐到彩色 |
| 任何失败 | `None` | `None` |

**设计原则：失败不抛异常，返回 `(None, None)` 并记 WARNING 日志**。理由：视频流是高频调用（每帧一次），中途断流/丢帧是常态而非意外；让上层以"空帧"分支处理，比每帧 try/except 更干净，也避免 GUI 主循环被异常打断。

### 8.1 RealSense 分支

```python
try:
    frames = self._rs_pipeline.wait_for_frames(timeout_ms=timeout_ms)
except Exception as exc:
    logger.warning("read(): wait_for_frames 失败（%s）。可能原因：设备被其他程序占用/深度流未就绪/USB带宽不足", exc)
    return None, None
```

- **`wait_for_frames(timeout_ms)`**：阻塞等待直到**所有已配置流**同步就绪一整组帧（RGB + 深度配对），超时（默认 5000ms）抛异常。
- 常见失败原因已写进日志提示：设备被其它程序占用（如 RealSense Viewer 还开着）、深度流未就绪、**USB 带宽不足**（USB2 直连 L515 常见）。

```python
try:
    if self._align is not None:
        frames = self._align.process(frames)   # 深度对齐到彩色
    color = frames.get_color_frame()
    depth = frames.get_depth_frame()
    if not color:
        logger.warning("read(): 对齐后无彩色帧（可能只有深度流/流未对齐）")
        return None, None
    rgb = np.asanyarray(color.get_data())
    d = np.asanyarray(depth.get_data()) if depth else None
    if d is not None and rgb is not None and d.shape[:2] != rgb.shape[:2]:
        logger.warning("read(): 深度(%s)与RGB(%s)尺寸不一致，对齐可能失败", d.shape, rgb.shape)
    return rgb, d
except Exception as exc:
    logger.warning("read(): 取帧/对齐异常（%s）", exc)
    return None, None
```

逐步拆解：

1. **对齐**：`self._align.process(frames)` 把深度帧重投影到彩色坐标系（见 7 ⑦）。
2. **取流**：`get_color_frame()` / `get_depth_frame()`；**彩色帧缺失直接判失败**（深度缺失则容忍，`d=None`）。
3. **转数组**：`np.asanyarray(...get_data())`——零拷贝视图方式包装 pyrealsense 的帧缓冲区，避免整帧拷贝的开销（高频路径的性能细节）。
4. **对齐后尺寸校验（重要）**：
   ```python
   if d is not None and d.shape[:2] != rgb.shape[:2]:
       logger.warning("深度(%s)与RGB(%s)尺寸不一致，对齐可能失败", d.shape, rgb.shape)
   ```
   对齐成功时，深度图与 RGB 图**宽高必须完全一致**（同一 `(u,v)` 一一对应）。若不一致，说明对齐没生效（例如 `_align` 创建失败、或流配置异常），此时"用 RGB 像素查深度"会错位。虽然这里只 WARNING 不阻断，但**上层必须在收到尺寸不一致时不要做逐像素融合**，这也是"对齐后尺寸校验"的意义——把"数据是否可信"这个判断显式暴露出来。

### 8.2 USB 分支

```python
ok, frame = self._cap.read()
if not ok:
    return None, None
return frame, None
```

OpenCV 惯例：`read()` 返回 `(ok, frame)`，`ok=False` 表示取帧失败（设备拔出/断流），此时返回 `(None, None)`；成功则 `depth` 恒为 `None`。

---

## 九、`get_rgb` / `get_depth` / `get_intrinsics`：便捷取值

```python
def get_rgb(self) -> Optional[np.ndarray]:
    rgb, _ = self.read()
    return rgb

def get_depth(self) -> Optional[np.ndarray]:
    _, depth = self.read()
    return depth

def get_intrinsics(self) -> Optional[dict]:
    return self._intrinsics
```

- `get_rgb` / `get_depth` 是 `read()` 的语法糖：各取一帧的一半。注意**每次调用都会真正读一帧**（两次调用是两帧，不是同一帧），需要 RGB 与深度**配对**时必须用 `read()` 一次拿全。
- `get_intrinsics` 是纯内存访问（不读帧），返回构造时缓存的内参 dict；USB 摄像头返回 `None`。

---

## 十、`pixel_to_point`：像素反投影三维坐标（针孔模型推导）

**签名**：

```python
def pixel_to_point(self, u: float, v: float,
                   depth_mm: Optional[float] = None) -> Optional[np.ndarray]:
    """像素 (u, v) + 深度 -> 相机系三维坐标 [x,y,z]（米）。仅 RGB-D 相机。"""
```

**输入语义**：`(u, v)` 是 RGB 图上的像素坐标（`u` 列坐标 / x 方向，`v` 行坐标 / y 方向，均从 0 开始）；`depth_mm` 可选——不传则自动从深度图 `(v, u)` 处取该像素的深度。

**返回**：`np.array([x, y, z], dtype=np.float64)`，**单位米**，坐标系为**相机坐标系**（z 轴沿光轴向前、x 向右、y 向下，OpenCV 惯例）。失败返回 `None`。

### 10.1 针孔相机模型推导

针孔模型描述"现实三维点 → 图像像素"的正向投影：

```text
                      图像平面
                    ┌──────────┐
       光心 (0,0,0) │  (u,v)   │
          ●────────►│──────────│────► z 轴（光轴，向前）
        /           │          │
       / 焦距 f     └──────────┘
    三维点 P(X,Y,Z)
```

由相似三角形（Z 是点在相机系下的深度，f 是焦距）：

```text
u = fx * (X / Z) + ppx
v = fy * (Y / Z) + ppy
```

- `fx` / `fy`：x / y 方向的焦距，单位是**像素**（= 物理焦距 / 像元尺寸）；
- `ppx` / `ppy`：主点（光轴与像平面交点）的像素坐标，一般接近图像中心，但受装配误差影响略有偏移，所以必须用标定/出厂值而非图像中心。

**反推（反投影）**：已知像素 `(u, v)` 与深度 `Z`，解出 `(X, Y)`：

```text
X = (u − ppx) × Z / fx
Y = (v − ppy) × Z / fy
Z = z   （深度值本身）
```

这就是代码第 317–319 行的公式：

```python
z = depth_mm / 1000.0
x = (u - k["ppx"]) / k["fx"] * z
y = (v - k["ppy"]) / k["fy"] * z
```

**直觉解释**：`(u − ppx)` 是像素偏离主点的距离（像素单位），除以焦距 `fx` 得到"该像素相对光轴方向的单位方向向量 x 分量"，再乘深度 `Z` 得到实际三维偏移 `X`。y 方向同理。

### 10.2 单位换算：Z = depth_mm / 1000

- 深度图（z16 格式）的**原始单位是毫米（mm）**；
- `pixel_to_point` 的输出约定是**米（m）**（注释明确写"（米）"）；
- 因此 `z = depth_mm / 1000.0`，随后 x、y 也用这个 `z` 参与乘法，三个分量**同单位（米）**，保证输出向量各轴一致。

> ⚠️ **数值精度**：z16 深度按毫米量化，1m 处精度 ±0.5mm；对 3D 手势坐标（厘米级误差可接受）足够。不要用浮点深度流（会大幅增加带宽），这是选 z16 的原因之一。

### 10.3 深度来源的两条路径

```python
if depth_mm is None:
    depth = self.get_depth()
    if depth is None:
        return None
    if 0 <= int(v) < depth.shape[0] and 0 <= int(u) < depth.shape[1]:
        depth_mm = float(depth[int(v), int(u)])
    else:
        return None
```

- 调用方**显式传入** `depth_mm`（例如 hand_pose 已缓存了深度帧，避免二次读帧）→ 直接用；
- 否则**自动读一帧深度图**，取 `depth[int(v), int(u)]` 处的毫米值；
- **越界保护**：`(u, v)` 超出深度图范围（关键点落在图像外）→ 返回 `None`，防止 IndexError 崩溃；
- **无内参**（USB 摄像头）→ WARNING + `None`：USB 相机没有官方内参，反投影物理上不可行，这是"仅 RGB-D 相机支持"的原因。

---

## 十一、`release` 与上下文管理器 `__enter__` / `__exit__`

```python
def release(self):
    if self._rs_pipeline is not None:
        try:
            self._rs_pipeline.stop()
        except Exception:
            pass
        self._rs_pipeline = None
    if self._cap is not None:
        self._cap.release()
        self._cap = None
    logger.info("摄像头已释放")

def __enter__(self):
    return self

def __exit__(self, *exc):
    self.release()
```

- **`release()`**：按"哪个后端在用就释放哪个"的原则清理——RealSense 管线 `stop()`（异常吞掉，因为释放阶段不应再抛错），OpenCV 捕获器 `release()`；释放后**置 `None`**，使重复调用幂等（二次 release 是安全空操作）。
- **上下文管理器**：`__enter__` 返回自身，`__exit__` 调 `release()`。支持 `with CameraModule(use_realsense=True) as cam:` 写法，**离开 with 块自动释放硬件资源**，杜绝忘记 `release()` 导致的"摄像头被占用"（这正是 `read()` 里 wait_for_frames 失败的最常见原因之一）。
- 推荐的两种生命周期写法：

```python
# 写法 A：手动管理
cam = CameraModule(use_realsense=True)
try:
    rgb, depth = cam.read()
finally:
    cam.release()

# 写法 B：上下文管理器（推荐，异常也安全）
with CameraModule(source=0) as cam:
    rgb, _ = cam.read()
```

---

## 十二、L515 专项排障指南

按"症状 → 原因 → 解决"组织，覆盖 README_1.md 的已知坑与本模块内置的检查点。

### 12.1 症状：版本不对（构造即抛 RuntimeError）

| 项目 | 内容 |
|---|---|
| 报错 | `pyrealsense2 版本不兼容 L515：请执行 pip install pyrealsense2==2.54.2.5684（librealsense 2.55+ 已移除 L515 支持）` |
| 原因 | **L515 已被 Intel 停产**；librealsense **2.55+ 移除了对 L515 的支持**。任何 2.55+ / 2.56.x 的 pyrealsense2 都无法驱动 L515 |
| 解决 | `pip install pyrealsense2==2.54.2.5684`；验证：`pip show pyrealsense2` 应显示 `Version: 2.54.2.5684`。**不要**升级 pyrealsense2，也不要让它被别的依赖连带升级（必要时用虚拟环境） |

### 12.2 症状：0x80070005 拒绝访问（Windows）

| 项目 | 内容 |
|---|---|
| 报错 | `设备枚举失败: ... 0x80070005 ...`，日志带提示 `⚙️ Windows 拒绝访问（0x80070005）：请尝试【以管理员身份运行】终端/程序，或检查摄像头隐私权限（设置→隐私→相机）` |
| 原因 | Windows 的 `ERROR_ACCESS_DENIED`：USB 设备接口被占用，或当前进程无访问权限（管理员权限 / 隐私设置） |
| 解决 | ① **以管理员身份运行**终端 / GUI 程序；② 检查 `设置 → 隐私 → 相机`，允许"桌面应用访问相机"；③ 关闭其它占用设备的程序（RealSense Viewer、其它采集软件）后重试 |
| 代码对应 | `check_realsense_devices()` 和 `_open_realsense()` 都对错误字符串做 `0x80070005` / `Access denied` / `拒绝访问` 匹配并附加此提示 |

### 12.3 症状：找不到设备（枚举为空）

| 项目 | 内容 |
|---|---|
| 报错 | `未找到 RealSense 设备。请检查：1. pyrealsense2 版本… 2. USB3.0 直连… 3. 驱动… 4. 供电/线缆…` |
| 原因 | 枚举不到硬件，常见：版本不对（见 12.1）、**USB2.0 连接**、缺驱动、供电不足/线缆坏 |
| 解决 | ① `pip show pyrealsense2` 确认 2.54.x；② **USB3.0 直连主板/扩展卡**，禁用 USB2 集线器（L515 的 USB3 带宽是硬性要求）；③ 安装 **Intel RealSense SDK 2.0 运行时**（提供驱动）；④ 换线/换口，用官方 **Intel RealSense Viewer** 确认设备能出图后再回本模块 |

### 12.4 症状：深度与 RGB 尺寸不一致（read() 告警）

| 项目 | 内容 |
|---|---|
| 报错 | WARNING 日志：`read(): 深度(1024,768)与RGB(1280,720)尺寸不一致，对齐可能失败` |
| 原因 | L515 彩色与深度传感器分辨率本来就不同（这是**正常的**：配置阶段就分开设了 1280x720 与 1024x768）；只有经过 `rs.align` 后二者才应该一致。出现此告警说明**对齐未生效**（`_align` 创建失败被降级为 `None`，或流配置异常） |
| 影响 | 深度与 RGB 像素**错位**，此时"用 RGB 关键点查深度图取深度"会取到错误位置的深度值 → 3D 坐标错误 |
| 解决 | ① 检查 `_open_realsense` 第 ⑦ 步是否成功（日志是否含"深度已对齐到彩色"）；② 确认没有私自改分辨率组合；③ 用 `lib/L515_driver.py` 的标准参数（depth 1024x768 + RGB 1280x720 @30FPS）验证；④ 更新/重装 `pyrealsense2==2.54.2.5684` |
| 上层应对 | 收到此告警时**不要**做 RGB↔深度逐像素融合；等告警消失再启用 3D 功能 |

### 12.5 症状：read() 一直返回 (None, None)

按 `wait_for_frames` 失败日志排查：设备被其它程序占用（关掉 Viewer）→ 深度流未就绪（重启程序/重插 USB）→ USB 带宽不足（确认 USB3.0 直连）→ 实在不行重启设备电源（L515 是 LiDAR，冷启动偶尔需要重新上电）。

---

## 十三、与上层 GUI / hand_pose 的接口约定

上层代码**只需要**依赖以下四个稳定接口，后端差异被完全封装：

| 接口 | 返回 | 上层用法 |
|---|---|---|
| `cam.read()` | `(rgb_bgr, depth)` | GUI 主循环每帧调用；`rgb_bgr` 给显示/检测，`depth`（可为 `None`）给 3D 计算 |
| `cam.get_intrinsics()` | `{fx, fy, ppx, ppy, width, height, model}` 或 `None` | hand_pose 做 3D 坐标换算时取内参；`None` 表示无 3D 能力 |
| `cam.pixel_to_point(u, v)` | `[x, y, z]`（米）或 `None` | 手部关键点像素 → 相机系 3D 坐标 → 关节角度/动作模仿 |
| `cam.release()` / `with cam` | — | 释放硬件；用 `with` 语句保证异常安全 |

**hand_pose 典型数据流**：

```text
read() ──► rgb_bgr ──► 手部关键点检测 ──► (u, v) 像素
                    └─► depth (mm, 已对齐) ─┐
                                            ├─► pixel_to_point(u, v) ──► [x,y,z] 米
                    get_intrinsics() ───────┘
```

**调用方注意事项汇总**：

1. `get_rgb()` 与 `get_depth()` 各读**一帧**；需要 RGB/深度配对时用 `read()` 一次取齐；
2. 深度值单位是**毫米**，`pixel_to_point` 输出单位是**米**，跨层传递时别混；
3. 构造可能抛 `RuntimeError`（版本/枚举/分辨率），GUI 启动时应预检（`check_realsense_devices()`）并展示 `LAST_REALSENSE_ERROR`；
4. 看到"深度与 RGB 尺寸不一致"告警时，先修对齐问题再启用 3D 功能；
5. 用 `with CameraModule(...)` 管理生命周期，避免"摄像头被占用"类故障。

---

*文档结束 · 对应源码 `rycan_hand_windows/camera/camera_module.py`（339 行）*
