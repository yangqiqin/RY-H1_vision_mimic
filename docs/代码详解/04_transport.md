# 04_transport.py —— 通信传输层 `CanTransport` 代码详解

> 本文档逐行解析 `hand/transport.py`，属于"睿研 RY-H1(16) 灵巧手视觉动作模仿系统（Windows 版）"代码详解系列。
> 目标：**不读源码即可完全理解本文件**——包括三种通信方式的初始化、帧构造、接收解析、线程模型与排障方法。

---

## 1. 文件定位与职责

`transport.py` 是系统的**通信传输层**，是整个"视觉动作模仿"链路中唯一直接接触物理总线的地方。它做两件相反的事：

1. **发送方向**：把 RyCAN SDK（`RyCanServoLib`，由 `hand_controller.py` 加载）通过**写回调**（`BusWriteT` 类型）下发的 `CanMsg`（ID + 数据字节），翻译成三种硬件之一能识别的帧格式，写进总线；
2. **接收方向**：在一个后台线程里轮询硬件，把硬件返回的应答帧解析回 `(can_id, payload)`，通过 `_on_frame` 回调喂回 SDK 的 `RyCanServoLibRcvMsg`，由 SDK 内部完成应答与消息监听的分发。

它本身**不实现任何协议逻辑**（电机指令、状态解析都在 SDK / 控制器层），只做"字节层面的搬运"。

支持的三种通信方式（Windows）：

| method 取值 | 硬件 | 速率 | 依赖 | 备注 |
|---|---|---|---|---|
| `"pcan"`（默认） | Peak PCAN-USB | 1 Mbps | `lib/PCANBasic.py` + PCAN 驱动 | 标准 CAN |
| `"canii"` | 周立功 CANalyst-II（USB-CAN） | 1 Mbps | `ControlCAN.py` + `ControlCAN.dll`（根目录） | 标准 CAN |
| `"rs485"` | RS485 串口（半双工） | 5 Mbps | `pyserial` | 私有封包协议，见 §10 |

实现参考：知识库官方 demo `RyHandLibCANII_rs485_pcan_16.py` 中的 `bus_write` / `bus_read` / `bus_read_callback`。

---

## 2. 整体数据流（ASCII 总览图）

```
┌────────────────────────────── SDK 侧（hand_controller.py）──────────────────────────────┐
│                                                                                          │
│   RyCanServoBusInit(&bus, 写回调 _write, &ticks, 1000)      ← 注册"写回调"+ 1ms 时钟     │
│        │                                                                                 │
│        │  SDK 内部需要发命令（如 0xA1 位置控制 / 0xA0 查询状态）                            │
│        ▼                                                                                 │
│   _write(msg_ptr)  ← BusWriteT 回调，SDK 每要发一帧就调一次                              │
│        │  msg.ulId（CAN ID）、msg.pucDat[0..ucLen-1]（负载）                              │
│        ▼                                                                                 │
│   tr.send(can_id, data)                                            ▲                      │
│                                                                     │                      │
└────────────────────────────────┼─────────────────────────────────────┼────────────────────┘
                                 │  发送                              │  收到帧（1ms 轮询）
                                 ▼                                    │
        ┌──────────────────────────────────────────────┐              │
        │              CanTransport（本文件）            │              │
        │   send(): 按 method 构造帧并写硬件             │              │
        │   _rx_loop(): 后台线程每 1ms 轮询一次          │              │
        └──────────────┬───────────────────────────────┘              │
                       │  ① TPCANMsg / ② VCI_CAN_OBJ / ③ 0xA5 封包     │
                       ▼                                              │
        ┌──────────────────────────────────────────────┐              │
        │  物理硬件：PCAN-USB / CANalyst-II / RS485 串口 │              │
        └──────────────┬───────────────────────────────┘              │
                       │                                              │
                       │  ② 硬件应答帧（电机状态、参数等）              │
                       ▼                                              │
        ┌──────────────────────────────────────────────┐              │
        │  _rx_loop（daemon 线程，见 §11）               │              │
        │   ├─ _rx_pcan():   dev.Read(PCAN_USBBUS1)     │              │
        │   ├─ _rx_canii():  VCI_Receive(批量 100 帧)   │              │
        │   └─ _rx_rs485():  0xA5 帧解析 + 和校验       │              │
        └──────────────┬───────────────────────────────┘              │
                       │  (can_id, payload)                            │
                       ▼                                              │
        _dispatch(can_id, payload)                                    │
                       │                                              │
                       ▼  tr._on_frame（由控制器注入的回调）────────────┘
                       │
                       ▼
        RyCanServoLibRcvMsg(&bus, msg)  →  SDK 内部钩子/监听分发
                                          （_listen_cb 解析 0xA0/0xAA 电机状态等）
```

一句话总结：**上行（发送）是"SDK 回调 → send() → 硬件"；下行（接收）是"硬件 → 接收线程 → dispatch → _on_frame → SDK RcvMsg"**，两条通路互相独立，靠后台线程衔接。

---

## 3. 模块级基础

### 3.1 文件头与导入（第 1~37 行）

```python
# -*- coding: utf-8 -*-
"""
transport.py —— Windows 通信传输层（PCAN / CANalyst-II / RS485）
...（模块 docstring，说明职责、三种方式、RS485 帧格式、依赖、用法）
"""
```

- **第 1 行**：声明 UTF-8 编码，保证中文字符串、注释在 Windows 下不乱码。
- **第 2~26 行**：模块 docstring，相当于"使用说明书"：三种方式、RS485 封包格式、依赖（`pip install pyserial`、PCANBasic/ControlCAN 驱动文件放同目录）、最小用法示例。
- **第 28 行** `from __future__ import annotations`：启用 PEP 563"注解延迟求值"，让 `Optional[threading.Thread]` 这类注解在低版本 Python 上也能写、且不求值，避免运行时开销与循环引用问题。
- **第 30~35 行** 导入：
  - `logging` —— 日志（模块级 logger，第 37 行 `logger = logging.getLogger("transport")`，logger 名 `"transport"`，便于 `logging.basicConfig` / 配置文件按名过滤）。
  - `os` / `sys` —— `_ensure_driver_path()` 里操作路径与 `sys.path`。
  - `threading` —— 接收线程。
  - `time` —— `_rx_loop` 的 1ms 休眠。
  - `typing.Callable / Optional` —— 类型注解：`_on_frame` 回调签名 `Callable[[int, bytes], None]`，`_rx_thread` 可为 `None`。

> 注意：模块**顶层不导入 ctypes**。这正是 `ctypes_byref` 辅助函数存在的原因（见 §5.1）：ctypes 只在 CANalyst-II 分支真正用到时才惰性导入，让只跑 PCAN/RS485 的进程少加载一个模块。

---

## 4. 类 `CanTransport` 总览

```python
class CanTransport:
    """Windows CAN/RS485 传输层。send() 由 SDK 写回调调用；recv 线程喂给 SDK。"""
```

核心成员变量（都在 `__init__` 中初始化）：

| 成员 | 类型 | 含义 |
|---|---|---|
| `method` | str | 小写化后的通信方式：`"pcan"` / `"canii"` / `"rs485"` |
| `rs485_port` / `rs485_baud` | str / int | RS485 模式参数（默认 `COM3` / `5000000`） |
| `_pcan` | tuple \| None | `(PCANBasic 模块, PCANBasic 实例)`，PCAN 模式打开成功后赋值 |
| `_canii` | module \| None | `ControlCAN` 模块（内含 `dll` 句柄与常量），CANII 模式赋值 |
| `_ser` | serial.Serial \| None | RS485 串口对象 |
| `_rx_thread` | Thread \| None | 接收轮询线程 |
| `_running` | bool | 线程运行开关（`open()` 置 True，`close()` 置 False） |
| `_on_frame` | Callable \| None | 接收分发回调，**由上层控制器注入**（`hand_controller` 把它指向 `self._on_frame`） |

---

### 4.1 `__init__`（第 43~59 行）—— 构造：只存参数、不碰硬件

```python
def __init__(self, method: str = "pcan", rs485_port: str = "COM3",
             rs485_baud: int = 5000000):
    self.method = method.lower()          # 50
    self.rs485_port = rs485_port          # 51
    self.rs485_baud = rs485_baud          # 52
    self._pcan = None                     # 54
    self._canii = None                    # 55
    self._ser = None                      # 56
    self._rx_thread: Optional[threading.Thread] = None   # 57
    self._running = False                 # 58
    self._on_frame: Optional[Callable[[int, bytes], None]] = None   # 59
```

逐行解读：

- **第 50 行** `self.method = method.lower()`：把入参转小写，保证用户传 `"PCAN"`、`"Pcan"` 也能匹配分支（宽容设计）。
- **第 51~52 行**：保存 RS485 参数。默认 `COM3` / `5_000_000`（5 Mbps）。注意这些参数只在 `method == "rs485"` 时才会被真正使用。
- **第 54~56 行**：三个"硬件句柄"槽位预置为 `None`。用 `_pcan`/`_canii`/`_ser` 区分"当前到底开了哪种硬件"，后续 `send`/`close` 都靠它们判断。
- **第 57 行**：接收线程槽位，构造时为空。
- **第 58 行** `_running = False`：线程运行标志，**构造阶段必须为 False**，否则线程未启动、标志却为真，逻辑上不一致。
- **第 59 行** `_on_frame = None`：接收回调。构造时不赋值，由 `hand_controller._init_bus()` 在总线初始化完成后注入（见 §12）。这是本类与上层唯一的数据耦合点。

> 设计要点：`__init__` **不做任何硬件操作**（不打开串口、不初始化 PCAN）。打开动作推迟到 `open()`，这样构造对象是廉价的、可失败的构造只发生在显式 `open()` 时。

---

## 5. 模块级辅助函数

### 5.1 `ctypes_byref(obj)`（第 240~243 行）—— 为什么存在？

```python
def ctypes_byref(obj):
    """ctypes.byref 便捷封装（保持 import 轻量）。"""
    import ctypes
    return ctypes.byref(obj)
```

**为什么存在**：这是"惰性导入"的经典手法。

- `ctypes.byref` 只在 **CANalyst-II 分支**被需要（`_open_canii` 的 `VCI_InitCAN`、`send` 的 `VCI_Transmit`）。
- 如果模块顶层写 `import ctypes`，那么即使用户只用 PCAN 或 RS485，Python 也会加载 ctypes（以及它背后的一堆 C 扩展初始化）。
- 把 `import ctypes` 挪进函数体后，**只有真正走到 CANII 分支的那一帧**才会触发导入；对 PCAN/RS485 用户而言，本模块完全不依赖 ctypes。

附带收益：
- 调用点代码更短：`ctypes_byref(cfg)` 比 `ctypes.byref(cfg)` 少一个全局名依赖；
- 与 `from lib import PCANBasic` / `import ControlCAN` 的"按需 import"风格一致（驱动模块同样只在使用时导入）。

> 注：函数每调用一次就重新执行一次 `import ctypes`。Python 的模块缓存保证这只是查字典，开销可忽略——这是标准写法，不是 bug。

---

## 6. 打开流程（`open()` 与三个 `_open_xxx`）

### 6.1 `_ensure_driver_path`（第 62~71 行）—— 路径兜底

```python
def _ensure_driver_path(self):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
    for d in (here, os.path.join(here, "lib")):
        if d not in sys.path:
            sys.path.insert(0, d)
```

- **第 68 行**：`__file__` 是本文件绝对路径 → `dirname` 一次得到 `hand/` → `dirname` 第二次得到**项目根目录**（`rycan_hand_windows/`）。
- **第 69~71 行**：把**根目录**和**根目录/lib/** 依次插入 `sys.path` 最前面（`insert(0, ...)`）。
  - 根目录放的是 `ControlCAN.py`（`_open_canii` 用 `import ControlCAN` 直接找它）；
  - `lib/` 放的是 `PCANBasic.py`（`_open_pcan` 用 `from lib import PCANBasic`）。
  - `if d not in sys.path` 防止重复插入；`insert(0)` 保证优先于其他路径。
- 注释说明：即使入口脚本（`apps/*.py`、`selfcheck.py`）已经做过路径引导，这里**再兜底一次**，保证本模块被任何入口 import 时都能找到驱动文件，从而把"驱动放哪"这个易错点收敛到根目录/lib 两个固定位置。

### 6.2 `open()`（第 74~86 行）—— 统一入口：开硬件 + 启线程

```python
def open(self):
    if self.method == "pcan":
        self._open_pcan()            # 75~76
    elif self.method == "canii":
        self._open_canii()           # 77~78
    elif self.method == "rs485":
        self._open_rs485()           # 79~80
    else:
        raise ValueError(f"未知通信方式: {self.method}")   # 82
    self._running = True             # 83
    self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)  # 84
    self._rx_thread.start()          # 85
    logger.info("[transport] %s 已打开", self.method)     # 86
```

- **第 75~82 行**：按 `method` 分发到对应 `_open_xxx`。未知方式直接抛 `ValueError`（防御性校验，防止静默"什么都没开"）。
- **第 83 行** `_running = True`：**先**置运行标志，**再**启动线程（第 84~85 行）——顺序不能反，否则线程一启动就发现标志为 False 直接退出。
- **第 84~85 行**：创建接收线程，`target=self._rx_loop`，`daemon=True`（守护线程，含义见 §11），立即 `start()`。
- **第 86 行**：成功日志（如 `[transport] pcan 已打开`）。

> 失败语义：任一 `_open_xxx` 抛异常时，`_running` 不会置 True、线程不会启动，异常向上抛给调用者（`hand_controller.open()`），由上层决定如何处理（GUI 弹窗/测试脚本打印）。

### 6.3 `_open_pcan`（第 89~97 行）—— PCAN-USB 初始化

```python
def _open_pcan(self):
    self._ensure_driver_path()
    from lib import PCANBasic as pcan
    dev = pcan.PCANBasic()
    res = dev.Initialize(pcan.PCAN_USBBUS1, pcan.PCAN_BAUD_1M)
    if res != pcan.PCAN_ERROR_OK:
        raise RuntimeError(f"PCAN 初始化失败，错误码 {res}（请确认 PCAN-USB 已插入、驱动已装）")
    self._pcan = (pcan, dev)
    logger.info("PCAN 初始化成功（1Mbps）")
```

- **第 90 行**：先确保 `lib/` 在 `sys.path`（PCANBasic.py 在 `lib/` 下）。
- **第 91 行** `from lib import PCANBasic as pcan`：函数内 import（惰性），只在使用 PCAN 时加载驱动封装。
- **第 92 行** `dev = pcan.PCANBasic()`：创建 PCANBasic API 实例（PCANBasic.py 内部封装了 `PCANBasic.dll`，Windows 下安装 PCAN 驱动后系统路径里就有这个 DLL）。
- **第 93 行** `res = dev.Initialize(pcan.PCAN_USBBUS1, pcan.PCAN_BAUD_1M)`：
  - `PCAN_USBBUS1`（= 0x51）：PCAN-USB 的第一个通道；
  - `PCAN_BAUD_1M`（= 0x00000400）：波特率 1 Mbps；
  - 返回值 `res` 是错误码，`PCAN_ERROR_OK`（= 0x00）表示成功。
- **第 94~95 行**：非 0 即失败，抛 `RuntimeError`，错误码直接拼进消息（方便对照 §13.1 排障表）。
- **第 96 行** `self._pcan = (pcan, dev)`：把**模块和实例打包成元组**存起来。为什么存两个？
  - `dev` 是操作句柄，`send`/`_rx_pcan`/`close` 要用它调用 `Write`/`Read`/`Uninitialize`；
  - `pcan` 模块提供常量（`PCAN_USBBUS1`、`PCAN_MESSAGE_STANDARD`、`PCAN_ERROR_OK` 等），后续方法也要用，所以一并保存。省去每次 `from lib import PCANBasic` 的重复导入。

### 6.4 `_open_canii`（第 100~119 行）—— CANalyst-II 初始化（三步曲）

```python
def _open_canii(self):
    self._ensure_driver_path()
    import ControlCAN as cc
    if cc.dll.VCI_OpenDevice(cc.VCI_USBCAN2, 0, 0) != 1:
        raise RuntimeError("CANalyst-II 打开设备失败（请确认 USB-CAN 已插入、ControlCAN.dll 同目录）")
    cfg = cc.VCI_INIT_CONFIG()
    cfg.AccCode = 0x00000000
    cfg.AccMask = 0xFFFFFFFF
    cfg.Filter = 0
    cfg.Timing0 = 0x00          # 1Mbps
    cfg.Timing1 = 0x14
    cfg.Mode = 0
    if cc.dll.VCI_InitCAN(cc.VCI_USBCAN2, 0, 0, ctypes_byref(cfg)) != 1:
        cc.dll.VCI_CloseDevice(cc.VCI_USBCAN2, 0)
        raise RuntimeError("CANalyst-II 初始化失败")
    if cc.dll.VCI_StartCAN(cc.VCI_USBCAN2, 0, 0) != 1:
        cc.dll.VCI_CloseDevice(cc.VCI_USBCAN2, 0)
        raise RuntimeError("CANalyst-II 启动失败")
    self._canii = cc
    logger.info("CANalyst-II 初始化成功（1Mbps, dev0/can0）")
```

**第 102 行**：`import ControlCAN as cc` —— ControlCAN.py 是周立功官方驱动封装（C 结构体定义 + `ctypes` 加载 `ControlCAN.dll`）。注意它**不是** `from lib import`，而是普通 import，所以文件必须放在根目录（这正是 `_ensure_driver_path` 把根目录加进 `sys.path` 的原因）。

**第 103~104 行：打开设备**：
- `cc.dll.VCI_OpenDevice(设备类型, 设备索引, 保留参数)`；
- `VCI_USBCAN2` = 4，表示"USBCAN-II / CANalyst-II"这类双通道设备；
- 参数 `0, 0` = 第 0 号设备、保留位；
- 返回 `1` 成功、`0` 失败。失败时抛 `RuntimeError`（常见原因见 §13.2）。

**第 105~111 行：构造初始化配置 `VCI_INIT_CONFIG`**：
| 字段 | 值 | 含义 |
|---|---|---|
| `AccCode` | `0x00000000` | 验收码（接收过滤器用） |
| `AccMask` | `0xFFFFFFFF` | 验收屏蔽码，全 1 = 所有位都"不关心" = **接收所有帧** |
| `Filter` | `0` | 0 = 单滤波方式（配合上面的全通掩码，等效于不过滤） |
| `Timing0` | `0x00` | 波特率分频寄存器高字节 |
| `Timing1` | `0x14` | 波特率分频寄存器低字节 |
| `Mode` | `0` | 0 = 正常模式（收发都开；1 是只听模式） |

- **Timing0=0x00 / Timing1=0x14 对应 1 Mbps**（周立功官方波特率表：500K=0x00/0x1C，250K=0x01/0x1C，125K=0x03/0x1C，100K=0x04/0x1C，1M=0x00/0x14）。必须与对端（灵巧手）一致，否则收不到任何应答。

**第 112~114 行：初始化 CAN 通道**：
- `VCI_InitCAN(VCI_USBCAN2, 设备0, 通道0, ctypes_byref(cfg))` —— 第四个参数需要**指针**，所以用 §5.1 的 `ctypes_byref(cfg)` 取地址；
- 返回 `1` 成功、`0` 失败。失败时**先 `VCI_CloseDevice` 关掉已打开的设备**再抛异常——这是资源清理习惯：打开成功但初始化失败，必须把设备还回去，否则设备一直被占用。

**第 115~117 行：启动 CAN 通道**：
- `VCI_StartCAN(VCI_USBCAN2, 0, 0)`，返回 `1` 成功、`0` 失败；失败同样先关设备再抛异常。

**第 118 行** `self._canii = cc`：保存模块引用（里面有 `dll` 和全部常量、结构体）。与 PCAN 不同，CANII 不需要持有一个"实例"——直接通过模块级 `cc.dll` 调 DLL 函数。

> 小结：CANalyst-II 的初始化是"**打开 → 配置 → 启动**"三步，任一步失败都会回滚（关设备）并抛异常，避免留下半初始化状态。

### 6.5 `_open_rs485`（第 122~128 行）—— 串口打开

```python
def _open_rs485(self):
    import serial
    try:
        self._ser = serial.Serial(self.rs485_port, self.rs485_baud, timeout=1)
    except Exception as exc:
        raise RuntimeError(f"RS485 串口 {self.rs485_port} 打开失败: {exc}（请确认串口号与 5Mbps 支持）")
    logger.info("RS485 串口 %s @ %d 打开成功", self.rs485_port, self.rs485_baud)
```

- **第 123 行**：惰性 `import serial`（pyserial），不装依赖时只有 RS485 模式才报错，PCAN/CANII 不受影响。
- **第 124~127 行**：`serial.Serial(端口, 波特率, timeout=1)`：
  - 打开失败（端口不存在 / 被占用 / 波特率不被驱动支持）会抛异常，这里**捕获后包一层 `RuntimeError`**，把原始错误 `exc` 拼进消息，方便排障（§13.3）；
  - `timeout=1`：读超时 1 秒——`_rx_rs485` 里 `read()` 最多阻塞 1s（线程模型相关，见 §11）。
- **第 128 行**：成功日志。

> 注意：串口对象一旦创建，`close()` 里对应 `self._ser.close()`；另外 pyserial 的 `Serial` 构造时可能已在内部打开端口，若后续 `open()` 流程里出现异常，`close()` 兜底逻辑（§9）也会尝试关闭它。

---

## 7. 发送：`send(can_id, data)`（第 131~163 行）

```python
def send(self, can_id: int, data: bytes):
    """发送一帧（SDK 写回调调用）。"""
```

**入参**：`can_id`（CAN 标识符，标准帧 11 位，如 0x101、0x1A1）、`data`（负载字节串）。
**调用者**：`hand_controller.py` 的 `_write` 回调（`msg.ulId` → `can_id`，`msg.pucDat[:msg.ucLen]` → `data`），也就是 SDK 每次要发命令都会走到这里。

### 7.1 PCAN 分支（第 133~144 行）

```python
from lib import PCANBasic as pcan
_, dev = self._pcan
msg = pcan.TPCANMsg()
msg.ID = can_id
msg.MSGTYPE = pcan.PCAN_MESSAGE_STANDARD
msg.LEN = len(data)
for i in range(min(len(data), 8)):
    msg.DATA[i] = data[i]
res = dev.Write(pcan.PCAN_USBBUS1, msg)
if res != pcan.PCAN_ERROR_OK:
    logger.warning("PCAN 发送失败: %s", res)
```

- `_, dev = self._pcan`：元组解包，只需要实例 `dev`（模块 `pcan` 在函数内重新 import，保证可用）。
- `TPCANMsg()`：构造 PCAN 消息结构体，逐字段填充：
  - `ID = can_id`：帧 ID；
  - `MSGTYPE = PCAN_MESSAGE_STANDARD`（= 0x00）：**标准帧**（11 位 ID，非扩展帧）；
  - `LEN = len(data)`：数据长度；
  - `DATA[i] = data[i]`：拷贝负载，**最多 8 字节**（`min(len(data), 8)`）——标准 CAN 一帧最多 8 字节负载，超长部分被截断（调用方保证命令帧 ≤ 8 字节，这是硬性约束）。
- `dev.Write(PCAN_USBBUS1, msg)`：写通道 1。返回错误码，非 `PCAN_ERROR_OK` 时只打 `warning` **不抛异常**——发送失败不应中断 SDK 的控制流（比如总线被拔掉时，控制循环还能继续跑、由上层超时机制发现）。

### 7.2 CANalyst-II 分支（第 146~156 行）

```python
cc = self._canii
frame = cc.VCI_CAN_OBJ()
frame.ID = can_id
frame.SendType = 1
frame.RemoteFlag = 0
frame.ExternFlag = 0
frame.DataLen = len(data)
for i in range(min(len(data), 8)):
    frame.Data[i] = data[i]
cc.dll.VCI_Transmit(cc.VCI_USBCAN2, 0, 0, ctypes_byref(frame), 1)
```

- `VCI_CAN_OBJ()`：周立功的 CAN 帧结构体，字段语义：
  | 字段 | 值 | 含义 |
  |---|---|---|
  | `ID` | can_id | 帧 ID |
  | `SendType` | `1` | 1 = **单次发送**（发一次不重发；0 是正常发送，失败会自动重试） |
  | `RemoteFlag` | `0` | 0 = 数据帧（1 是远程帧，无数据） |
  | `ExternFlag` | `0` | 0 = 标准帧 11 位 ID（1 是扩展帧 29 位） |
  | `DataLen` | len(data) | 数据长度 |
  | `Data[0..7]` | data | 负载，同样按 8 字节上限截断 |
- `cc.dll.VCI_Transmit(设备类型, 设备0, 通道0, ctypes_byref(frame), 1)`：最后参数 `1` 表示"发送 1 帧"（buffer 长度）。返回实际发送帧数，**这里不检查返回值**——与 PCAN 分支相比略糙，但失败场景（设备未插）会在 `open` 阶段被挡住，运行期发送失败一般由上层超时兜底。

### 7.3 RS485 分支（第 158~163 行）

```python
frame = bytearray([0xA5, can_id & 0xFF, (can_id >> 8) & 0xFF, len(data)])
frame.extend(data)
check = sum(frame) & 0xFF
frame.append(check)
self._ser.write(bytes(frame))
```

这是私有封包协议（对齐 demo 的 `bus_write`）：

```
| 0xA5 | id_lo | id_hi | len | data[0..len-1] | check |
   1B      1B     1B     1B        len B           1B
```

- **第 159 行**：构造帧头 4 字节——
  - `0xA5`：固定帧头（同步字/魔数），接收端靠它找帧起点；
  - `can_id & 0xFF`：ID 低字节；
  - `(can_id >> 8) & 0xFF`：ID 高字节（**小端序**：低字节在前）；
  - `len(data)`：负载长度（1 字节，最大 255）。
  - 注意：RS485 的负载长度**不受 8 字节限制**（`len(data)` 全量装入），这是 RS485 相比标准 CAN 的优势。
- **第 160 行**：追加负载字节。
- **第 161 行**：`check = sum(frame) & 0xFF` —— **和校验**：对**从 0xA5 到最后一个数据字节**（即除 check 本身外的所有字节）求和，`& 0xFF` 只取低 8 位（等价于 `sum % 256`）。这是一个 8 位校验和，能发现单字节翻转等常见错误（不能保证检测所有错误，但对本系统足够，且实现最简）。
- **第 162 行**：把校验字节追加到帧尾。
- **第 163 行**：`self._ser.write(bytes(frame))` 一次性写出整帧。半双工总线上，发送后硬件/适配器负责方向切换（见 §13.4 关于自动方向控制的说明）。

> 校验和的接收端验证逻辑见 §10.2，两处公式完全对称：发送端 `sum(除check外全部字节) & 0xFF`，接收端同样求和后与 check 字节比对。

---

## 8. 接收流程

### 8.1 `_rx_loop`（第 166~177 行）—— 1ms 轮询主循环

```python
def _rx_loop(self):
    while self._running:
        try:
            if self.method == "pcan":
                self._rx_pcan()
            elif self.method == "canii":
                self._rx_canii()
            elif self.method == "rs485":
                self._rx_rs485()
        except Exception as exc:  # pragma: no cover
            logger.debug("rx loop: %s", exc)
        time.sleep(0.001)
```

- **第 167 行**：`while self._running` —— 靠标志位退出；`close()` 把它置 False 后，循环在下一轮条件判断处自然结束。
- **第 168~176 行**：按 `method` 调用对应 `_rx_xxx`，并用 `try/except Exception` 包住——**接收线程绝不允许因单个异常死掉**。任何解析/驱动异常只记 `debug` 日志（`# pragma: no cover` 表示该分支通常不触发，测试覆盖率工具忽略）。
- **第 177 行** `time.sleep(0.001)`：**1ms 轮询节拍**（≈1000 次/秒）。为什么轮询而不是阻塞等待？
  - PCAN `Read` 是非阻塞的（无帧时立即返回 `PCAN_ERROR_QRCVEMPTY`）；
  - CANII `VCI_Receive` 传了 `WaitTime=0` 也是非阻塞；
  - RS485 `read(in_waiting)` 只读"已有字节"。
  - 因此统一用一个 1ms 的轮询循环来"刷"三种硬件，实现简单、退出及时（最迟 1ms 响应 `_running=False`）。

### 8.2 `_rx_pcan`（第 179~184 行）

```python
def _rx_pcan(self):
    from lib import PCANBasic as pcan
    _, dev = self._pcan
    res, msg, _ts = dev.Read(pcan.PCAN_USBBUS1)
    if res == pcan.PCAN_ERROR_OK and msg.LEN > 0:
        self._dispatch(msg.ID, bytes(msg.DATA[:msg.LEN]))
```

- `dev.Read(PCAN_USBBUS1)`：PCANBasic 的 `Read` 一次返回三元组 `(结果码, TPCANMsg, 时间戳)`。时间戳 `_ts` 本系统不用，故用下划线命名丢弃。
- 无帧时返回 `PCAN_ERROR_QRCVEMPTY`（0x20），此时 `res != PCAN_ERROR_OK`，直接跳过。
- 有帧时：`msg.LEN > 0` 过滤空帧；`bytes(msg.DATA[:msg.LEN])` 把 ctypes 定长数组按实际长度切片转成 Python `bytes`；然后 `_dispatch(msg.ID, payload)` 交给分发。

### 8.3 `_rx_canii`（第 186~193 行）—— 批量接收 100 帧

```python
def _rx_canii(self):
    cc = self._canii
    buf = (cc.VCI_CAN_OBJ * 100)()
    num = cc.dll.VCI_Receive(cc.VCI_USBCAN2, 0, 0, buf, 100, 0)
    if num > 0 and num < 0xFFFFFFFF:
        for i in range(num):
            f = buf[i]
            self._dispatch(f.ID, bytes(f.Data[:f.DataLen]))
```

- **第 188 行**：`(cc.VCI_CAN_OBJ * 100)()` —— 一次性分配**100 个 CAN 帧结构体的定长数组**（ctypes 数组乘法语法），作为接收缓冲区。每次轮询最多取 100 帧，灵巧手 16 电机的状态应答远小于这个量，基本不会丢帧。
- **第 189 行**：`VCI_Receive(设备, 设备0, 通道0, buf, 100, 0)` —— 参数依次是：接收缓冲区、缓冲区长度 100、**等待时间 0ms（非阻塞）**。返回值 `num` 是实际收到的帧数。
- **第 190 行** `if num > 0 and num < 0xFFFFFFFF`：两个边界——
  - `num > 0`：无帧（0）直接跳过；
  - `num < 0xFFFFFFFF`：**`VCI_Receive` 出错时返回 `0xFFFFFFFF`（4294967295）**（例如设备拔出、缓冲区错误），这个哨兵值必须排除，否则 `range(0xFFFFFFFF)` 会把线程卡死/爆内存。这是典型的"DLL 返回值用 UINT 表示错误"的防御写法。
- **第 191~193 行**：逐帧取出 `f.ID` 与 `bytes(f.Data[:f.DataLen])`，交给 `_dispatch`。

### 8.4 `_rx_rs485`（第 195~215 行）—— 0xA5 帧解析（核心逻辑）

```python
def _rx_rs485(self):
    if self._ser is None or self._ser.in_waiting <= 0:
        return
    data = self._ser.read(self._ser.in_waiting)
    # 解析 0xA5 帧（与 demo bus_read_callback 一致）
    i = 0
    while i < len(data):
        if data[i] != 0xA5:
            i += 1
            continue
        if i + 4 > len(data):
            break
        can_id = data[i + 1] | (data[i + 2] << 8)
        dlen = data[i + 3]
        if i + 4 + dlen + 1 > len(data):
            break
        payload = bytes(data[i + 4:i + 4 + dlen])
        check = sum(data[i:i + 4 + dlen]) & 0xFF
        if check == data[i + 4 + dlen]:
            self._dispatch(can_id, payload)
        i += 4 + dlen + 1
```

**第 196~197 行（快速通道）**：串口未开或接收缓冲区无数据（`in_waiting <= 0`）直接返回——避免无谓的 `read` 调用。

**第 198 行**：`data = self._ser.read(self._ser.in_waiting)` —— 把当前缓冲区里**所有**可用字节一次读出来（`read(n)` 在 `timeout=1` 内返回，实际数据通常已在缓冲区，立即返回）。

**第 200 行起：缓冲区扫描循环**（`i` 是当前解析位置）。串口是字节流，没有"帧边界"，所以必须**自己找帧头**：

| 行 | 逻辑 | 说明 |
|---|---|---|
| 202~204 | `if data[i] != 0xA5: i += 1; continue` | **找帧头**：不是 0xA5 就跳过 1 字节继续扫（容错：噪声/半帧残留都被跳过，实现"再同步"） |
| 205~206 | `if i + 4 > len(data): break` | **帧头不完整**：至少还要 4 字节（0xA5+id_lo+id_hi+len）才够，缓冲区里不足则退出等下一轮 |
| 207 | `can_id = data[i+1] \| (data[i+2] << 8)` | **拆 ID**：低字节 `data[i+1]`、高字节 `data[i+2]` 左移 8 位后按位或，还原小端序 ID（与发送端 `can_id & 0xFF` / `(can_id>>8)&0xFF` 互逆） |
| 208 | `dlen = data[i+3]` | **拆长度**：负载字节数 |
| 209~210 | `if i + 4 + dlen + 1 > len(data): break` | **整帧不完整**：需要 `4(帧头) + dlen(负载) + 1(校验)` 字节；不够则退出等下一轮（防止越界/解析半帧） |
| 211 | `payload = bytes(data[i+4 : i+4+dlen])` | **拆负载**：切片取出 `dlen` 字节 |
| 212 | `check = sum(data[i : i+4+dlen]) & 0xFF` | **计算校验和**：对 `0xA5 + id_lo + id_hi + len + data[...]`（4+dlen 字节）求和取低 8 位——与发送端公式完全一致 |
| 213~214 | `if check == data[i+4+dlen]: self._dispatch(...)` | **校验比对**：算出的校验和与帧尾校验字节相等 → 帧合法，分发 `(can_id, payload)`；不相等 → 静默丢弃（视为坏帧），不抛异常 |
| 215 | `i += 4 + dlen + 1` | 跳到下一帧起点（无论校验成败都要前进，否则死循环） |

**关于"帧被拆到两次轮询"的行为**（重要理解）：每次轮询读到的字节是**全新的本地 `data`**，解析中若因"帧不完整"而 `break`，这些半帧字节并不会被保留到下一轮——下一次轮询从零开始扫新读到的字节。在 5 Mbps 下，一帧（13 字节左右）传输只需 ~26µs，远小于 1ms 轮询间隔，正常情况整帧在一次 `read` 内到齐；只有极端的"恰好读到一半"竞态才会丢帧。这是 demo 同款实现的取舍：**实现简单、以轮询高频弥补**，上层有超时/重试机制兜底。

### 8.5 `_dispatch`（第 217~219 行）

```python
def _dispatch(self, can_id: int, payload: bytes):
    if self._on_frame is not None:
        self._on_frame(can_id, payload)
```

- 所有 `_rx_xxx` 解析出的帧最终都汇聚到这里——**统一出口**，三种方式共用。
- 若上层已注入回调（`_on_frame is not None`），就调用 `self._on_frame(can_id, payload)`；否则静默丢弃（例如只发送不接收的场景）。
- 回调运行在**接收线程**里，因此回调里的工作要尽量快、不能阻塞（SDK 的 `RyCanServoLibRcvMsg` 是内存操作，很快）。

---

## 9. 关闭：`close()`（第 222~237 行）

```python
def close(self):
    self._running = False
    if self._rx_thread is not None:
        self._rx_thread.join(timeout=1.0)
    try:
        if self.method == "pcan" and self._pcan:
            from lib import PCANBasic as pcan
            _, dev = self._pcan
            dev.Uninitialize(pcan.PCAN_USBBUS1)
        elif self.method == "canii" and self._canii:
            self._canii.dll.VCI_CloseDevice(self._canii.VCI_USBCAN2, 0)
        elif self._ser is not None:
            self._ser.close()
    except Exception as exc:  # pragma: no cover
        logger.debug("close: %s", exc)
    logger.info("[transport] 已关闭")
```

- **第 223 行**：先停线程（`_running = False`，接收循环最迟 1ms 后退出）。
- **第 224~225 行**：`self._rx_thread.join(timeout=1.0)` —— 等线程退出，**最多等 1 秒**。为什么设超时？因为 RS485 的 `read()` 可能阻塞最长 1s（`timeout=1`），`join` 等不到就超时返回，不无限挂起。线程是 daemon 的（§11），即使没来得及退出，进程退出时也不会被它挡住。
- **第 226~236 行**：按方式释放硬件，全部包在 `try/except` 里（关闭阶段的异常不值得冒泡，记 `debug` 即可）：
  - **PCAN**：`dev.Uninitialize(PCAN_USBBUS1)` 释放通道（必须先判断 `self._pcan` 非空，防止从未 open 就 close）；
  - **CANII**：`cc.dll.VCI_CloseDevice(VCI_USBCAN2, 0)` 关闭设备（与 `_open_canii` 失败回滚是同一函数）；
  - **RS485**：`self._ser.close()` 关串口（注意这里用的是 `elif self._ser is not None`，没有重复判断 method，逻辑等价：非 pcan/canii 且串口开过就关）。
- **第 237 行**：关闭日志。

> 幂等性：`close()` 可以安全地在"从未 open"或"重复 close"时调用（各分支都判空、异常被吞），适合放在 `finally` 里。

---

## 10. RS485 封包协议专题

### 10.1 帧格式与字节序

```
偏移:   0        1        2        3        4 .. 4+dlen-1     4+dlen
        ┌────────┬────────┬────────┬────────┬─────────────────┬────────┐
        │  0xA5  │ id_lo  │ id_hi  │  len   │ data[0..len-1]  │ check  │
        └────────┴────────┴────────┴────────┴─────────────────┴────────┘
          帧头       ID 低8位  ID 高8位  负载长度   负载（≤255B）   校验和
```

- **帧头 0xA5**：固定的"魔数"，接收端扫描同步用；理论上可能出现在负载里，但因为接收端从帧头开始按长度切帧，误同步只会导致该帧校验失败被丢弃，不会崩溃。
- **ID 小端序**：发送 `can_id & 0xFF`（低字节在前）→ `(can_id >> 8) & 0xFF`；接收 `data[i+1] | (data[i+2] << 8)` 还原。2 字节可表示 0~65535 的 ID。
- **len 单字节**：负载最长 255 字节（实际用途 ≤ 8 字节）。

### 10.2 校验和（check）的计算与验证

**发送端（§7.3）**：

```python
frame = bytearray([0xA5, id_lo, id_hi, len])
frame.extend(data)
check = sum(frame) & 0xFF     # 对 0xA5 + id + len + data 求和，取低 8 位
frame.append(check)
```

**接收端（§8.4）**：

```python
check = sum(data[i : i + 4 + dlen]) & 0xFF   # 同样的 4+dlen 字节求和取低 8 位
if check == data[i + 4 + dlen]:              # 与帧尾校验字节比对
    self._dispatch(can_id, payload)
```

- 数学上：`sum(全部字节) mod 256`，`& 0xFF` 与 `% 256` 等价（取低 8 位）。
- **覆盖范围**：帧头 + ID + 长度 + 负载（**不含 check 自身**）。发送端"先求和再 append"，接收端"求和后与尾字节比"，两段代码覆盖的字节集合完全一致，保证对称。
- **能力边界**：8 位和校验能检出**任意奇数个字节翻转**和大多数偶发错误，但"两个字节同时翻转且增量抵消"这类错误检不出——对本系统（短帧、低噪声环境）足够，且是 demo 同款算法。
- **校验失败的处置**：静默丢弃（不进 `_dispatch`），同时 `i` 照常前进，继续解析后面的字节——坏帧不影响后续好帧。

---

## 11. 线程模型

本文件只有一个线程，加上控制器侧共两个后台线程：

```
主线程（调用方，如 GUI / 测试脚本）
 ├─ open()  ──► 启动 [传输接收线程]  CanTransport._rx_loop   daemon=True
 │                 └─ 每 1ms：读硬件 → _dispatch → _on_frame（→ SDK RcvMsg）
 ├─ send() 由 SDK 写回调触发（运行在主线程/调用线程里，非传输线程）
 └─ close() ──► _running=False → join(timeout=1.0) 回收线程
```

| 问题 | 答案 |
|---|---|
| 什么时候启动？ | `open()` 成功打开硬件后（第 84~85 行） |
| 什么时候退出？ | `close()` 置 `_running=False`，循环最迟 1ms 内自行结束（第 167 行条件判断） |
| 为什么 `daemon=True`？ | 守护线程不阻止解释器退出。若用户不调 `close()` 就关程序，或 `join` 超时线程还活着，进程也能正常退出，不会挂死。这是"后台轮询线程"的标准做法 |
| `close()` 的 `join(timeout=1.0)` 是什么？ | 最多等 1 秒让线程干净退出。RS485 `read(timeout=1)` 最坏阻塞 1s，超时 join 保证 close 不会卡死；等不到就放弃，靠 daemon 兜底 |
| 线程安全吗？ | 传输线程只读 `self._pcan/_canii/_ser/_method/_running/_on_frame`，主线程只在 `open()`/`close()` 时改 `_running` 与句柄——**句柄在 open 完成后不再变更**，`_running` 是 int 读写，CPython 下无 GIL 竞争问题，实际安全 |
| 回调在哪个线程执行？ | `_on_frame`（即控制器把帧喂给 SDK 的函数）运行在**传输接收线程**里，所以它必须快速返回，不能做阻塞 IO |

---

## 12. 与上层 `hand_controller.py` 的协作

`transport.py` 不直接 import 控制器，控制器也不 import 传输层的 SDK 细节，两者通过"回调注入 + 方法调用"解耦：

```python
# hand_controller.py（节选）
def open(self):
    from .transport import CanTransport
    self._tr = CanTransport(method=self.method, rs485_port=..., rs485_baud=...)
    self._tr.open()                       # ① 开硬件 + 启接收线程

def _init_bus(self):
    ...
    @BusWriteT
    def _write(msg_ptr) -> int:           # ② SDK 写回调
        msg = msg_ptr.contents
        self._tr.send(msg.ulId, bytes(msg.pucDat[:msg.ucLen]))   # ③ 下行
        return 0
    ret = self._lib.RyCanServoBusInit(ctypes.byref(self.bus), self._write_cb, ...)
    ...
    self._tr._on_frame = self._on_frame   # ④ 注入接收回调（访问"私有"成员，属约定耦合）
    # 控制器另起一个线程更新 1ms ticks（bus.pusTicksMs）供 SDK 计时

def _on_frame(self, can_id, payload):     # ⑤ 传输线程 → SDK
    msg = CanMsgT(); msg.ulId = can_id; msg.ucLen = len(payload); ...
    self._lib.RyCanServoLibRcvMsg(ctypes.byref(self.bus), msg)   # ⑥ 上行喂回 SDK
```

完整闭环（对应 §2 图）：

1. `hand_controller.open()` → `CanTransport.open()`（开硬件、启动传输接收线程）；
2. `_init_bus()` → `RyCanServoBusInit(&bus, 写回调, &ticks, 1000)` 注册 SDK 的写回调；
3. SDK 想发命令 → 调写回调 `_write` → `tr.send(can_id, data)` → 硬件（三种方式之一）；
4. 硬件应答 → 传输接收线程 1ms 轮询 → `_dispatch` → `tr._on_frame`（即控制器的 `_on_frame`）→ 组装 `CanMsgT` → `RyCanServoLibRcvMsg(&bus, msg)` → SDK 内部把应答匹配给对应命令的钩子/监听（例如 0xA0 状态帧进 `_listen_cb` 更新 16 电机状态）。

**为什么 `_on_frame` 是"注入"而不是构造参数？** 因为 `CanTransport` 是纯传输层，不依赖 SDK 类型（`CanMsgT`、`RyCanServoLibRcvMsg` 都是控制器/库的）。传输层只负责把帧"递出去"，由谁消化、怎么消化是上层的事——所以用"属性赋值回调"保持传输层与 SDK 完全解耦。

---

## 13. 排障指南

### 13.1 PCAN 初始化失败（`_open_pcan` 抛 `RuntimeError: PCAN 初始化失败，错误码 X`）

`Initialize` 返回的错误码是 **32 位位掩码**，可能多值叠加。常见值：

| 错误码 | 十进制 | 含义 | 处理 |
|---|---|---|---|
| `PCAN_ERROR_OK` (0x00) | 0 | 成功 | — |
| `PCAN_ERROR_XMTFULL` (0x01) | 1 | 发送缓冲区满 | 发送太频繁，降速 |
| `PCAN_ERROR_OVERRUN` (0x02) | 2 | 接收溢出 | 轮询太慢，检查线程是否卡死 |
| `PCAN_ERROR_BUSLIGHT` (0x04) / `BUSHEAVY` (0x08) | 4/8 | 总线负载告警 | 检查总线终端电阻、对端是否在线 |
| `PCAN_ERROR_BUSOFF` (0x10) | 16 | **总线关闭**（严重错误） | 检查 CAN_H/CAN_L 接线、120Ω 终端、波特率 |
| `PCAN_ERROR_QRCVEMPTY` (0x20) | 32 | 接收队列空 | 正常现象（非错误，轮询时常见） |
| `PCAN_ERROR_NODRIVER` (0x200) | 512 | **未装 PCAN 驱动** | 安装 PEAK PCAN 官方驱动（PCANBasic.dll） |
| `PCAN_ERROR_HWINUSE` (0x400) | 1024 | **硬件已被其他程序占用** | 关闭 PCAN-View 等其他占用通道的程序 |
| `PCAN_ERROR_NETINUSE` (0x800) | 2048 | 网络被占用 | 同上 |
| `PCAN_ERROR_ILLHW` (0x1400) | 5120 | 硬件句柄无效 | 设备未插入/被拔出，重新插拔 USB |

**排查步骤**：① 插好 PCAN-USB，看设备管理器是否识别；② 确认已装 PEAK 驱动；③ 关闭 PCAN-View 等调试软件再重试；④ 换 USB 口/换设备验证硬件。

### 13.2 CANalyst-II 打开失败

三个失败点对应三条错误消息：

1. **`CANalyst-II 打开设备失败`**（`VCI_OpenDevice` 返回 0）：
   - `ControlCAN.dll` 不在根目录（`_ensure_driver_path` 只加了根目录和 `lib/`）；
   - USB-CAN 没插 / 驱动（USBCAN 驱动）没装 / 设备被其他程序（如 ZCANPRO、CANTest）占用；
   - 确认 `VCI_USBCAN2` 设备类型与硬件匹配（CANalyst-II 是 USBCAN-II 兼容）。
2. **`CANalyst-II 初始化失败`**（`VCI_InitCAN` 返回 0）：多半是配置参数问题（但本代码参数是固定标准值），或设备处于异常状态——**先拔插设备再试**。
3. **`CANalyst-II 启动失败`**（`VCI_StartCAN` 返回 0）：同上，设备异常或已被占用。这两条失败路径都已先 `VCI_CloseDevice` 回滚，可直接重试。

### 13.3 RS485 串口打不开（`RS485 串口 COM3 打开失败: ...`）

- **`could not open port 'COM3'` / `FileNotFoundError`**：串口号不对。到设备管理器"端口(COM 和 LPT)"里查实际 COM 号，改 `rs485_port`。
- **`Access is denied` / 端口被占用**：串口被其他软件（串口助手、上一轮没退干净的程序）占用，关掉再试。
- **`ValueError: Unsupported baudrate`**：**5 Mbps 需要硬件与驱动支持**。常见 USB 转串口芯片：FTDI 高端型号（FT2232H/FT4232H 等）可支持，部分 CH340/CP210x 上限只有 1~2 Mbps。确认适配器规格；必要时降低 `rs485_baud` 并与灵巧手侧保持一致。
- **接线**：A/B 线交叉（对端 A 接我方 B），半双工共地。

### 13.4 收不到应答（能发不能收 / 完全无响应）

按"物理 → 配置 → 时序"三层排查：

1. **物理层**：
   - CAN 总线需要**两端 120Ω 终端电阻**（尤其线长 >1m 时）；缺终端表现为"偶发丢帧"或完全无应答；
   - 检查 CAN_H/CAN_L 是否接反、线缆是否断路；RS485 检查 A/B 是否交叉；
   - 灵巧手是否上电（手部供电指示灯）。
2. **配置层**：
   - **波特率一致性**：PCAN 1M / CANII Timing0=0x00,Timing1=0x14（1M）/ RS485 5M，都必须与灵巧手固件配置一致；
   - **ID 过滤**：本代码 CANII 用 `AccCode=0 / AccMask=0xFFFFFFFF` 接收所有帧、PCAN 无过滤，若改了过滤参数，确认没把应答 ID 滤掉；
   - **RS485 半双工方向控制**：发送后必须释放总线才能收。本代码不手动翻转 RTS/DE，依赖适配器**自动方向控制**（多数 USB-RS485 自动完成）；若用的是需要软件控制方向的适配器，会"发得出去收不回来"——换自动方向适配器，或硬件上把 DE 接高电平配合收发切换芯片。
3. **时序/软件层**：
   - 接收线程是否在跑（日志 `[transport] xxx 已打开` 后线程即启动；`close()` 后不再收）；
   - 上层 `check_connection()` 的 `replies > 0` 是链路是否打通的最快判据（有应答=链路通）；
   - 偶发丢帧属正常（轮询/校验丢弃），上层有超时重试；若**持续**无应答，重点查波特率与终端电阻；
   - PCAN 模式可开 PCAN-View 挂同一通道抓总线流量，确认硬件层面有没有帧（区分"没发出去"和"没收到"）；
   - CANII 模式可用 ZCANPRO/CANTest 抓包验证。

---

## 14. 设计要点小结（一句话版）

- **解耦**：传输层只认 `(can_id, payload)`，不认识 SDK 结构体；上行靠 `send()` 方法、下行靠 `_on_frame` 回调注入。
- **惰性加载**：`ctypes`、`PCANBasic`、`ControlCAN`、`serial` 全部用时才 import，任何单一通信方式都不需要其他方式的依赖。
- **线程安全退出**：`daemon=True` + `_running` 标志 + `join(timeout=1.0)` 三件套，保证收尾干净且永不挂死。
- **防御式解析**：RS485 找帧头 + 长度边界检查 + 8 位和校验；CANII 排除 `0xFFFFFFFF` 错误哨兵；接收线程异常不致死。
- **失败可诊断**：每个失败点都带上下文信息的 `RuntimeError`，直接对应本文档 §13 排障表。
