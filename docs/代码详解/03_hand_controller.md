# 03 · hand_controller.py —— RY-H1(16) 灵巧手高层控制器 代码详解

> 本文档逐行级详解 `hand/hand_controller.py`（630 行，Windows 版"睿研 RY-H1(16) 灵巧手视觉动作模仿系统"的灵巧手高层控制器）。
> 阅读本文档**不需要再读源码**即可完整理解该文件的职责、数据结构、每个方法、线程模型与安全要点。
> 建议搭配阅读：`hand/hand_config.py`（配置）、`hand/transport.py`（传输层）、`hand/angles2motor.py`（角度↔电机指令换算）。

---

## 1. 文件总览

### 1.1 职责

本文件是灵巧手控制链路的**最高层**，向下只依赖三样东西：

| 依赖 | 作用 |
|---|---|
| `hand.transport.CanTransport` | 底层通信（PCAN / CANalyst-II / RS485 三种物理通道） |
| `hand.angles2motor` | 关节弧度 → 电机位置指令（0~4095）的换算 |
| `hand.hand_config` | 全部常量配置（关节数、行程上限、指令码、Hook/Listen 数量等） |

它本身通过 **ctypes** 直接加载厂家 RyCAN SDK（Windows 下为 `RyhandLibx64.dll`），完成：

1. **DLL 加载**与全部 C 函数签名声明（`_load_lib` / `_declare_api`）；
2. **总线初始化**——对齐官方 demo 的 `hook=40`、`listen=33`、32 个 `AddListen`（`_init_bus`）；
3. **收发桥接**——SDK 要发帧时回调 Python 写函数，硬件收帧时由传输层回调 `_on_frame` 喂给 SDK；
4. **1ms 节拍**——维护 SDK 需要的毫秒 tick 计数器（`_rx_loop`）；
5. **运动控制 API**——单电机 / 16 关节弧度 / 开合手 / 回零 / 复位 / 清故障 / 行程读写；
6. **自检与诊断**——连接性检查、行程检查、故障码解释。

### 1.2 模块间数据流

```
 GUI / 应用层（mimic_demo、hand_gui、test_hand ...）
        │  angles_rad_16（16 个弧度）
        ▼
┌───────────────────────────────────────────────┐
│ RYH1HandController（本文件）                   │
│  move_joints → angles_to_motor_cmds           │
│      → RyMotion_ServoMove_Mix / _Speed        │
│          │                                    │
│          ▼  SDK 内部组织成 0xAA/0xA1 指令帧      │
│   ┌─── 写回调 _write（SDK 同步调用）            │
│   │      ▼                                    │
│   │  CanTransport.send() → PCAN/CANII/RS485    │
│   │                                           │
│   │  硬件总线 → 伺服电机                       │
│   │                                           │
│   │  伺服应答（ID = 伺服ID+256）               │
│   │      ▼                                    │
│   │  CanTransport._rx_loop（传输接收线程）      │
│   │      ▼ _on_frame                          │
│   │  RyCanServoLibRcvMsg（喂给 SDK）            │
│   │      ▼ SDK 匹配 32 个 Listen               │
│   └─── _listen_cb（更新 _last_servo_info）      │
│                                               │
│  _rx_loop（1ms tick 线程）→ _ticks.value       │
└───────────────────────────────────────────────┘
```

### 1.3 模块级常量与导入

```python
from __future__ import annotations     # 延迟求值类型注解（Py3.7+）
import ctypes, logging, math, os, time
from typing import List, Optional
from .angles2motor import angles_to_motor_cmds
from .hand_config import HAND_CONFIG, JOINT_NUM, POS_MAX

logger = logging.getLogger("hand")
```

- `logger`：日志名 `"hand"`，全模块共用；
- `_DEFAULT_LIBS`：候选库名列表，**跨平台兜底**：
  - `RyhandLibx64.dll`（Windows x64，本系统实际使用）
  - `RyhandLibx86.dll`（Windows x86）
  - `libRyhand64_1.so` / `libRyhandArm64.so` / `libRyhand.so`（Linux 备用，方便同一套代码跨平台）

---

## 2. ctypes 结构体详解

### 2.1 为什么用 ctypes、为什么这样布局

- ctypes 是 Python 标准库中调用 C 动态库的机制：我们在 Python 里**复刻 C 头文件中的结构体定义**（`_fields_` 按字段顺序声明），ctypes 会按 C 的 ABI 规则自动计算内存布局（字段偏移、对齐、填充 padding）。
- 这些结构体直接与 SDK 头文件（`RyhandLib.h` 等）一一对应，SDK 的 C 函数通过**指针**读写这些内存，所以布局必须与 C 端完全一致，否则 SDK 会读到错位的字段。
- 关键布局规则：
  - 结构体按**最大对齐要求**的成员对齐（x64 下指针是 8 字节对齐）；
  - 字段顺序必须与 C 声明一致（`_fields_` 里列出的顺序就是内存顺序）；
  - 数组字段（`c_uint8 * 64`）是**内联数组**，直接嵌在结构体里，不是指针；
  - 需要 SDK 回填/引用的数据用**指针字段**（`POINTER(...)`），由 Python 端预先分配并保持存活。

### 2.2 CanMsgT —— CAN 帧

```python
class CanMsgT(ctypes.Structure):
    _fields_ = [
        ("ulId",   ctypes.c_uint32),          # CAN 帧 ID（标准帧 11bit，放大到 32bit 存储）
        ("ucLen",  ctypes.c_uint8),           # 数据长度（0~8，CAN 标准帧最多 8 字节）
        ("pucDat", ctypes.c_uint8 * 64),      # 数据缓冲区（64 字节，远超 8 字节）
    ]
```

| 字段 | C 类型 | 含义 |
|---|---|---|
| `ulId` | `uint32_t` | CAN 帧 ID。发送时就是目标伺服 ID（如 `0xAA` 指令发往 ID 1）；应答帧 ID = 伺服 ID + 256（见 2.7） |
| `ucLen` | `uint8_t` | 有效数据长度。写帧时 `bytes(msg.pucDat[:msg.ucLen])` 只发这么长 |
| `pucDat` | `uint8_t[64]` | 数据区。**为什么是 64 而不是 8？**——厂家 SDK 把这类结构体同时用作多种协议的缓冲（包括非 CAN 的扩展帧/诊断/固件升级等大 payload），头文件如此定义；Python 端照抄即可，发送时按 `ucLen` 截断 |

内存布局（x64）：`uint32`(4B) + `uint8`(1B) + `uint8[64]`(64B) = 69B，按 4 字节对齐补齐到 **72B**（结尾 padding 3B）。

### 2.3 回调类型 BusWriteT / CallbackT

```python
BusWriteT  = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(CanMsgT))
CallbackT  = ctypes.CFUNCTYPE(None, ctypes.POINTER(CanMsgT), ctypes.c_void_p)
```

| 类型 | 签名 | 用途 |
|---|---|---|
| `BusWriteT` | `int (*)(CanMsgT*)` | **总线写回调**：SDK 要发一帧时调用，返回 0 表示成功、-1 失败。Python 端实现为 `_write`，内部转调 `transport.send()` |
| `CallbackT` | `void (*)(CanMsgT*, void*)` | **Listen 回调**：SDK 收到匹配的应答帧时调用，`para` 是注册时传的用户参数（本文件未用，传 None 即可） |

> ⚠️ 见第 9 节：**CFUNCTYPE 回调对象必须被 Python 侧持有引用**（`self._write_cb` / `self._listen_cb`），否则会被垃圾回收，SDK 随后调用悬空函数指针导致崩溃。

### 2.4 MsgHookT —— 收发钩子（单个监听条目）

```python
class MsgHookT(ctypes.Structure):
    _fields_ = [
        ("ucEn",    ctypes.c_uint8),          # 使能标志（1=启用）
        ("ucAlive", ctypes.c_uint8),          # 活跃计数：SDK 每次匹配到该钩子时递增，用于判活
        ("pstuMsg", ctypes.POINTER(CanMsgT)), # 指向"过滤模板"：匹配 ID 与首字节的 CAN 帧
        ("funCbk",  CallbackT),               # 命中时的回调函数指针
    ]
```

| 字段 | 含义 |
|---|---|
| `ucEn` | 使能位。初始化为 0（`memset`），`AddListen` 注册后 SDK 置 1 |
| `ucAlive` | 活跃/存活计数器。SDK 在内部 tick（1ms）里对长期无更新的钩子做超时/老化判断，`GetServoUpdateInfo` 可读 |
| `pstuMsg` | 指向模板帧 `CanMsgT`。匹配规则：**帧 ID 相同 且 数据首字节相同**（所以同一伺服 ID 可以注册两个 Listen，一个匹配 `0xA0` 应答、一个匹配 `0xAA` 应答，见 6.4） |
| `funCbk` | 回调。命中时 SDK 在**调用 `RyCanServoLibRcvMsg` 的那个线程**（即传输接收线程）上同步执行 |

内存布局（x64）：`uint8`+`uint8`（2B）→ 指针 8 字节对齐需要 **6B padding** → `pstuMsg`(8B) + `funCbk`(8B) = **24B**。这解释了"为什么两个 uint8 后面直接跟指针字段"——C 编译器自动插入填充，ctypes 同样处理。

### 2.5 ServoDataT —— 伺服数据联合体（Union）

```python
class ServoDataT(ctypes.Union):
    _fields_ = [("pucDat", ctypes.c_uint8 * 64)]
```

- 这是一个 **union**（联合体）：所有成员共享同一块内存。当前只有一个成员 `pucDat`（64 字节原始缓冲区）。
- 在 C 头文件中，该 union 通常还有**按字段解读的视图**（如 position/velocity/current 的结构体）；Python 端只保留原始字节视图，因为我们是**手动位域解析**（见第 4 节 `parse_servo_data`），不需要 C 视图。
- 用途：作为"出参缓冲"传给 `RyMotion_ServoMove_Mix`、`RyFunc_GetServoInfo` 等，SDK 把回读数据写进这块内存。

### 2.6 MsgListenT —— 完整监听槽（模板 + 回读缓冲 + 置信度）

```python
class MsgListenT(ctypes.Structure):
    _fields_ = [
        ("stuListen",     MsgHookT),      # 钩子本体：使能/存活/模板/回调
        ("stuRet",        ServoDataT),    # 回读缓冲：SDK 把最近一次应答的 64B 原始数据写这里
        ("ucConfidence",  ctypes.c_uint8),# 置信度/新鲜度：SDK 每收到一次新应答刷新它
    ]
```

| 字段 | 含义 |
|---|---|
| `stuListen` | 内嵌的 `MsgHookT`，即"监听谁、怎么回调" |
| `stuRet` | 内嵌的 `ServoDataT`（64B 联合体），SDK 把**最近一次命中该监听槽的应答载荷**拷进来；`GetServoUpdateInfo` 可把某个槽的内容取出来读 |
| `ucConfidence` | 置信度：新数据到达时 SDK 更新，可用于判断"这条数据是不是新的" |

> 注意：`_init_bus` 中 32 个 `AddListen` 用的回调是同一个 `_listen_cb`，它**直接解析并缓存到 `self._last_servo_info`**，所以本文件没有走 `GetServoUpdateInfo` 读 `stuRet` 的路径（该 API 只在 `_declare_api` 中声明，供扩展/排查用）。

### 2.7 RyCanServoBusT —— 总线上下文（最核心的结构体）

```python
class RyCanServoBusT(ctypes.Structure):
    _fields_ = [
        ("pusTicksMs",   ctypes.POINTER(ctypes.c_uint16)), # 毫秒 tick 计数器指针（外部维护）
        ("usTicksPeriod", ctypes.c_uint16),                # tick 周期：本实现 1000ms
        ("usHookNum",    ctypes.c_uint16),                 # 钩子数组长度：40
        ("usListenNum",  ctypes.c_uint16),                 # 监听数组长度：33
        ("pstuHook",     ctypes.POINTER(MsgHookT)),        # 指向 hook 数组首元素
        ("pstuListen",   ctypes.POINTER(MsgListenT)),      # 指向 listen 数组首元素
        ("pfunWrite",    BusWriteT),                       # 总线写回调
    ]
```

| 字段 | 值（本文件） | 含义 |
|---|---|---|
| `pusTicksMs` | `&self._ticks` | **指针**指向一个 16 位毫秒计数器。SDK 在 1ms 节拍里读它做超时判断与周期调度（如 `update_rate` 上报节奏）。**计数由 Python 的 tick 线程每 1ms 更新一次**（见 6.6） |
| `usTicksPeriod` | 1000 | tick 周期（ms）。与 `_rx_loop` 里 `int(time.time()*1000) % 1000` 的取模 1000 严格对应——SDK 期望计数器按 0~999 循环 |
| `usHookNum` | 40 | hook 数组元素个数（官方 demo 值） |
| `usListenNum` | 33 | listen 数组元素个数（官方 demo 值）。**32 个被 `AddListen` 占用，第 33 个是保留槽**（保持 0 初始化） |
| `pstuHook` | `cast(hooks, ...)` | 指向 `MsgHookT[40]` 数组首元素 |
| `pstuListen` | `cast(listens, ...)` | 指向 `MsgListenT[33]` 数组首元素 |
| `pfunWrite` | `self._write_cb` | SDK 发帧时调用的写回调 |

> **为什么用指针字段 + 外部数组？** SDK 初始化后会在**整个会话期间**持续读写这两个数组（钩子匹配、回读数据落槽）。若把数组内联进 `RyCanServoBusT`，结构体要随数组变大且 C 端不好按指针操作；用指针 + 独立数组是 C 的惯用设计，Python 端用 `ctypes.cast` 把数组对象转成指针塞进去（见 2.9 与第 9 节生命周期警告）。

### 2.8 应答 ID 规则（贯穿全文）

- 伺服电机应答帧的 **CAN ID = 伺服 ID + 256**。
- 例：对伺服 1 发指令，应答 ID = 257；伺服 16 应答 ID = 272。
- 因此 `_init_bus` 中 32 个 Listen 的模板 `ulId` 全部落在 **257~272**（`i+1+256`），同一 ID 注册两个 Listen（请求字节 `0xA0` / `0xAA`），SDK 用"ID + 首字节"双重匹配把应答路由到正确的槽位。
- 回调里 `mid = msg.ulId & 0xFF` 即从应答 ID 还原伺服号 1~16。

### 2.9 结构体定义小结表

| 结构体 | 对应 C 类型 | 关键作用 | 备注 |
|---|---|---|---|
| `CanMsgT` | `CAN_MSG_T` | CAN 帧 | 内联 64B 缓冲 |
| `BusWriteT` / `CallbackT` | 函数指针 | 写回调 / 监听回调 | CFUNCTYPE |
| `MsgHookT` | `MSG_HOOK_T` | 单条收发钩子 | 含模板指针与回调指针 |
| `ServoDataT` | `SERVO_DATA_T`(union) | 64B 原始回读缓冲 | 手动位域解析 |
| `MsgListenT` | `MSG_LISTEN_T` | 完整监听槽 | 钩子+回读+置信度 |
| `RyCanServoBusT` | `RYCAN_SERVO_BUS_T` | 总线上下文 | 全指针，跨会话存活 |

---

## 3. 故障状态码 SERVO_STATUS_TEXT（0~11）

```python
SERVO_STATUS_TEXT = {
    0:  "正常",
    1:  "电机过温告警",
    2:  "电机过温保护",
    3:  "电机低压保护",
    4:  "电机过压保护",
    5:  "电机过流保护",
    6:  "电机力矩保护",
    7:  "电机熔丝位错保护",
    8:  "电机堵转保护",
    9:  "驱动器异常保护",
    10: "电机hall错保护",
    11: "电机找零告警（未完成回零，行程受限！需执行回零）",
}
```

该字典对应手册 `MFingerInfo_t.status` / `enret_t` 错误码。逐条含义与处置建议：

| 码 | 名称 | 含义 | 处置建议 |
|---|---|---|---|
| 0 | 正常 | 无故障 | — |
| 1 | 电机过温**告警** | 温度偏高但未到保护阈值 | 降载/降速继续观察；排查长时间堵转或大电流工况 |
| 2 | 电机过温**保护** | 温度越限，驱动器已停机 | 停止动作让电机散热；检查机械是否卡阻导致持续大电流 |
| 3 | 低压保护 | 供电电压低于阈值 | 检查电源电压/功率、线缆与接插件接触、USB-CAN 供电能力 |
| 4 | 过压保护 | 供电电压高于阈值 | 检查电源是否超压（尤其再生/回馈工况） |
| 5 | 过流保护 | 电流超过驱动器允许值 | 检查机械卡死、负载突变；适当降低电流限制参数；`clear_fault` 后重试 |
| 6 | 力矩保护 | 输出力矩超过保护值 | 检查外部负载/夹持物卡阻；减小目标力矩 |
| 7 | 熔丝位错保护 | 驱动器内部熔丝/配置位异常 | 多为硬件或固件问题，断电重启，仍复现需联系厂家 |
| 8 | 堵转保护 | 电机堵转（转不动） | 检查齿轮箱/丝杠是否卡死、有无异物；**先排除机械问题再上电动作** |
| 9 | 驱动器异常保护 | 驱动器自检异常 | 断电重启；仍复现需联系厂家 |
| 10 | Hall 错保护 | 霍尔传感器信号错误 | 检查电机线/编码器线是否松动；需厂家维修 |
| 11 | 找零告警 | **未完成回零，行程受限**（本系统最常见的坑） | 执行回零：`homing()`（`RyParam_SetHomeMode` mode=2，CMD 0xBE）。未回零时电机只会走受限行程，表现为"动作幅度小/几乎不动" |

辅助函数：

```python
def status_text(status: int) -> str:
    return SERVO_STATUS_TEXT.get(status, f"未知状态({status})")
```

未知码原样返回 `未知状态(N)`，保证 UI/日志不会因新码崩溃。

### 3.1 ServoInfo —— 单电机状态数据类

```python
class ServoInfo:
    __slots__ = ("status", "position", "velocity", "current", "tactile")
```

- 对应手册 `MFingerInfo_t` 的 5 个字段：故障码、位置、速度、电流、触觉/力。
- `__slots__` 限制实例只能有这 5 个属性，省内存且防拼写错误。
- `status_text` 属性把数值故障码转成中文（透传 `status_text()`）。
- `__repr__` 输出 `ServoInfo(status=0[正常], P=2048, V=0, I=0, F=0)`，方便日志/GUI 直接打印。

---

## 4. 位域解析：parse_servo_data / parse_servo_info / _sign12

伺服回读的应答帧**载荷 8 字节**，把一个 16 位/32 位字段压缩进 12 位位域。解析逻辑完全一致，两个函数只是入口不同：

- `parse_servo_data(data: ServoDataT)`：从 `RyFunc_GetServoInfo` 出参结构体里取 `pucDat[:8]`；
- `parse_servo_info(raw8: bytes)`：从 Listen 回调收到的原始 8 字节取。

### 4.1 位布局（64 位小端整数视角）

```python
v = int.from_bytes(raw, "little")     # 8 字节 → 64 位小端整数
status   = (v >> 8)  & 0xFF           # 位 8~15
position = (v >> 16) & 0xFFF          # 位 16~27
velocity = _sign12((v >> 28) & 0xFFF) # 位 28~39（有符号）
current  = _sign12((v >> 40) & 0xFFF) # 位 40~51（有符号）
tactile  = (v >> 52) & 0xFFF          # 位 52~63（无符号）
```

| 位区间（从低位起） | 字段 | 位数 | 有符号 | 取值范围 | 说明 |
|---|---|---|---|---|---|
| 0~7 | （保留） | 8 | — | — | 首字节未参与解析（帧计数/保留位） |
| 8~15 | status | 8 | 否 | 0~11（正常/故障） | 见第 3 节故障码表 |
| 16~27 | position | 12 | 否 | 0~4095 | 位置指令（与 `POS_MAX=4095` 对应） |
| 28~39 | velocity | 12 | **是** | -2048~2047 | 速度反馈（补码） |
| 40~51 | current | 12 | **是** | -2048~2047 | 电流反馈（补码，负号表示方向） |
| 52~63 | tactile | 12 | 否 | 0~4095 | 触觉/力反馈（协议按无符号幅值定义） |

### 4.2 字节 ↔ 位 映射（小端，方便对照抓包）

| 字节 | 位 | 内容 |
|---|---|---|
| byte0 | 0~7 | 保留 |
| byte1 | 8~15 | status |
| byte2 | 16~23 | position 低 8 位 |
| byte3 | 24~31 | position 高 4 位（24~27）+ velocity 低 4 位（28~31） |
| byte4 | 32~39 | velocity 高 8 位 |
| byte5 | 40~47 | current 低 8 位 |
| byte6 | 48~55 | current 高 4 位（48~51）+ tactile 低 4 位（52~55） |
| byte7 | 56~63 | tactile 高 8 位 |

**逐个移位解释**（以 `(v >> 16) & 0xFFF` 为例）：

1. `v >> 16`：把 64 位整数右移 16 位，让 position 字段落到最低 12 位；
2. `& 0xFFF`：掩码截取低 12 位，丢弃两侧无关位；
3. 其余字段同理：先右移到低位、再掩码取 12 位（status 取 8 位 `& 0xFF`）。

### 4.3 _sign12 —— 12 位二进制补码转有符号

```python
def _sign12(x: int) -> int:
    return x - 0x1000 if x & 0x800 else x
```

- 12 位无符号值范围 0~4095；其中最高位（bit11，掩码 `0x800`）是符号位；
- 若符号位为 1，说明是负数，减去 `0x1000`（4096）即得补码真值 → 范围 **-2048~2047**；
- 例如 `0xFFF`（4095）→ 4095 - 4096 = **-1**。
- 用途：velocity / current 可能为负（反向运动/反向电流），必须转有符号；position 与 tactile 按协议无符号，不做转换。

---

## 5. 类 RYH1HandController —— 构造函数与状态

```python
def __init__(self, method="pcan", lib_path=None,
             rs485_port="COM3", rs485_baud=5000000,
             default_speed=HAND_CONFIG["default_speed"],       # 1000
             default_max_current=HAND_CONFIG["default_max_current"],  # 75
             hand_lr=1):
```

| 参数 | 默认 | 含义 |
|---|---|---|
| `method` | `"pcan"` | 通信方式：`pcan` / `canii` / `rs485`（小写化后保存） |
| `lib_path` | None | 厂家 SDK 库路径；None 时按 6.1 策略自动搜索 |
| `rs485_port` / `rs485_baud` | `COM3` / `5000000` | RS485 模式参数（波特率 5Mbps 为灵巧手标配） |
| `default_speed` | 1000 | 默认运动速度（位置增量/时间相关，来自配置） |
| `default_max_current` | 75 | 默认最大电流限制（mA 量级，0xAA 力位混合模式生效） |
| `hand_lr` | 1 | 1=右手（默认），0=左手（每指 M1/M2 交换，见 6.3） |

实例状态字段：

| 字段 | 初值 | 含义 |
|---|---|---|
| `self._lib` | None | 加载后的 ctypes CDLL 对象 |
| `self._tr` | None | `CanTransport` 实例（`open()` 时创建） |
| `self.bus` | `RyCanServoBusT()` | 总线上下文结构体（2.7） |
| `self._ticks` | `c_uint16(0)` | 1ms 计数器（tick 线程维护，SDK 通过 `pusTicksMs` 读取） |
| `self._rx_thread` | None | 本控制器的 tick 线程句柄 |
| `self._running` | False | 运行标志（tick 线程循环条件） |
| `self._last_servo_info` | `{}` | `motor_id(1~16) -> ServoInfo` 缓存，由 Listen 回调异步刷新 |

构造最后调用 `self._load_lib(lib_path)`（**注意：构造函数只加载 DLL，不打开总线**；总线初始化在 `open()`）。

---

## 6. 方法详解

### 6.1 `_load_lib(lib_path)` —— DLL 搜索策略

搜索目录（按优先级）：

1. `os.getcwd()` —— 当前工作目录（用户直接把 dll 放运行目录时生效）；
2. 项目根目录 `here`（`__file__` 上溯两级：`hand/` → 项目根）；
3. `here/lib/` —— **资源统一目录**（驱动/模型/参考文件都放 lib/，见 `transport._ensure_driver_path` 的同一约定）。

候选列表构造：

- 若显式给了 `lib_path`，先试它（最高优先级，绝对路径/相对路径均可）；
- 遍历 `search_dirs × _DEFAULT_LIBS` 拼出全部"目录+库名"组合；
- **最后追加裸库名**（`RyhandLibx64.dll` 等），依赖系统 PATH / 当前目录的默认搜索行为（`ctypes.CDLL` 裸名会走 Windows DLL 搜索顺序）。

加载循环：

```python
for name in candidates:
    try:
        self._lib = ctypes.CDLL(name)   # 成功即 break
    except OSError as exc:
        last_err = exc                   # 记录最后一次错误
        logger.warning(...)
if self._lib is None:
    raise RuntimeError(...)              # 全部失败：报错并列出全部候选
self._declare_api()                      # 加载成功后声明函数签名
```

要点：

- **失败不中断**，逐个候选尝试，直到第一个能加载的；
- 全部失败时抛 `RuntimeError`，错误信息包含全部候选路径与原始 OSError，方便用户定位（常见原因：dll 没放对位置、缺 VC 运行库、32/64 位不匹配）；
- 成功后立即 `_declare_api()`。

### 6.2 `_declare_api()` —— 每个 SDK 函数的签名声明

> ctypes 默认把函数当"返回 int、参数不校验"调用，**不声明会得到错误的返回值/崩溃**。此处逐一设置 `restype`（返回值类型）与 `argtypes`（参数类型列表，ctypes 据此做参数转换与类型检查）。

| SDK 函数 | restype | argtypes | 用途 / 对应指令 |
|---|---|---|---|
| `RyCanServoBusInit` | `uint8` | `(POINTER(RyCanServoBusT), BusWriteT, POINTER(c_uint16), c_uint16)` | 初始化总线。参数：总线、写回调、tick 指针、tick 周期(1000)。**返回 0 = 成功** |
| `RyCanServoBusDeInit` | `None` | `(POINTER(RyCanServoBusT))` | 反初始化（关闭时调用） |
| `RyCanServoLibRcvMsg` | `int8` | `(POINTER(RyCanServoBusT), CanMsgT)` | 把收到的 CAN 帧**按值**喂给 SDK（ctypes 自动拷贝，SDK 内部再拷贝，安全）。见 6.5 |
| `RyMotion_ServoMove_Mix` | `uint8` | `(bus, uint8 motor_id, int16 pos, uint16 speed, uint16 current, POINTER(ServoDataT), uint16 timeout)` | **0xAA 力位混合**：位置+速度+电流限制（带载推荐）。`pos` 是有符号 16 位，实际传 0~4095；最后参数 timeout（本文件传 0 = SDK 默认） |
| `RyMotion_ServoMove_Speed` | `uint8` | `(bus, uint8, int16, uint16, POINTER(ServoDataT), uint16)` | **0xA1 速度模式**：位置+速度，**无电流限制**（空载调试用） |
| `RyFunc_GetServoInfo` | `uint8` | `(bus, uint8 motor_id, POINTER(ServoDataT), uint16 timeout)` | **0xA0 同步读状态**：阻塞等待应答写入 `ServoDataT`，返回 0 成功 |
| `AddListen` | `int16` | `(bus, POINTER(CanMsgT), CallbackT)` | 注册监听：模板帧（ID+首字节）+ 回调。**返回监听槽索引** |
| `GetServoUpdateInfo` | `int8` | `(bus, uint8, POINTER(MsgListenT))` | 查询某监听槽的更新信息（alive/confidence/最新数据），本文件未使用（扩展排查用） |
| `RyParam_SetUpateRate` | `uint8` | `(bus, uint8, uint16 rate_ms, POINTER(ServoDataT), uint16)` | 设置状态**自动上报周期**（配置里 `update_rate_ms=20`；0xAA 应答可周期推送） |
| `RyParam_SetMotionMute` | `uint8` | `(bus, uint8, uint8 mute, uint16)` | 运动静音/使能（mute=1 禁动） |
| `RyFunc_Reset` | `uint8` | `(bus, uint8, uint16)` | 复位单个电机 |
| `RyParam_ClearFault` | `uint8` | `(bus, uint8, uint16)` | 清除电机故障 |
| `RyParam_GetStroke` | `uint8` | `(bus, uint8, POINTER(c_uint32), uint16)` | 读行程（0~4095）。**try/except 包裹：老 SDK 可能没有此函数** |
| `RyParam_SetStroke` | `uint8` | `(bus, uint8, uint32, uint16)` | 写行程（谨慎！） |
| `RyParam_SetHomeMode` | `uint8` | `(bus, uint8, uint8 mode, uint16)` | 回零配置/执行（CMD 0xBE，见 6.19） |
| `GetRyCanServoLibVersion` | `None` | `(c_uint8 * 30)` | 把版本字符串（ASCII，`\0` 结尾）写入 30 字节缓冲 |

**try/except 包裹的三个函数**（`RyParam_GetStroke` / `RyParam_SetStroke` / `RyParam_SetHomeMode` / `GetRyCanServoLibVersion`）说明：

- 这些是较新 SDK 才提供的 API；老版本 DLL 里没有对应导出符号，`L.xxx` 访问会抛 `AttributeError`；
- 包裹后**老 SDK 也能正常用其余功能**，只是行程/回零/版本功能不可用（调用处也都用 try/except 兜底，返回 None / 0xFF）。

### 6.3 `open()` 与 `set_hand_lr()`

```python
def open(self):
    from .transport import CanTransport       # 延迟导入，避免循环依赖
    self._tr = CanTransport(method=self.method, ...)
    self._tr.open()                           # 打开物理通道 + 启动传输接收线程
    self._init_bus()                          # 初始化 SDK 总线
```

- `open()` = 打开物理通道 + 初始化 SDK 总线，两步都必须成功；
- 传输层 `CanTransport.open()` 内部会启动自己的**接收线程**（读硬件帧 → `_dispatch` → 回调 `_on_frame`），见第 10 节线程模型。

```python
def set_hand_lr(self, hand_lr: int):
    self.hand_lr = 1 if hand_lr else 0
```

- **左右手硬件镜像**：左手/右手电机的 M1/M2 安装方向相反，导致"共模（近节弯曲）/差模（侧摆）"的物理含义互换；
- 症状：**"滑近节滑条，实际动的是侧摆"** → 大概率手型选反了，调用 `set_hand_lr` 立即生效，**无需重连**；
- 换算层（`angles_to_motor_cmds`）在 `hand_lr=0` 时交换每指 M1↔M2 指令，读回时（`motor_cmds_to_joint_angles`）同样交换，保证正/逆变换一致。

### 6.4 `_init_bus()` —— 总线初始化（核心，对齐官方 demo）

分五个步骤：

**① 分配并清零数组**

```python
HookArr   = MsgHookT * HAND_CONFIG["hook_num"]     # MsgHookT[40]
ListenArr = MsgListenT * HAND_CONFIG["listen_num"] # MsgListenT[33]
hooks   = HookArr()
listens = ListenArr()
ctypes.memset(ctypes.byref(hooks),   0, ctypes.sizeof(hooks))
ctypes.memset(ctypes.byref(listens), 0, ctypes.sizeof(listens))
```

- `T * N` 是 ctypes 的**数组类型**，`()` 实例化出零初始化数组；
- `memset` 把**包括指针字段在内的所有字节清零**——否则 SDK 读到的 `pstuMsg`/`funCbk` 是未定义垃圾值，会崩溃或误匹配；
- hook=40 / listen=33 与官方 demo 完全一致。

**② 填充总线上下文**

```python
ctypes.memset(ctypes.byref(self.bus), 0, ctypes.sizeof(self.bus))
self.bus.usTicksPeriod = 1000
self.bus.usHookNum     = HAND_CONFIG["hook_num"]    # 40
self.bus.usListenNum   = HAND_CONFIG["listen_num"]  # 33
self.bus.pusTicksMs    = ctypes.pointer(self._ticks)   # tick 指针
self.bus.pstuHook      = ctypes.cast(hooks,  ctypes.POINTER(MsgHookT))    # 数组→指针
self.bus.pstuListen    = ctypes.cast(listens, ctypes.POINTER(MsgListenT)) # 数组→指针
```

- `usTicksPeriod=1000` 与 `_rx_loop` 的取模 1000 配套（计数器 0~999 循环）；
- `ctypes.cast(数组, POINTER(类型))`：把数组对象**原地**当作指向首元素的指针（ctypes 数组本身就是连续内存，cast 只是类型转换，不拷贝），见第 9 节；
- `ctypes.pointer(self._ticks)`：取 `c_uint16` 对象的地址。

**③ 写回调 `_write`**

```python
@BusWriteT
def _write(msg_ptr) -> int:
    msg = msg_ptr.contents            # 解引用：指针 → CanMsgT
    self._tr.send(msg.ulId, bytes(msg.pucDat[:msg.ucLen]))
    return 0
self._write_cb = _write               # ★ 持有引用，防止 GC
```

- SDK 要发帧时**同步**调用此函数；`msg_ptr.contents` 取出帧内容；
- 只发送 `pucDat[:ucLen]` 有效字节；
- 返回 0 表示发送成功；异常时记日志并返回 -1（SDK 据此知道发送失败）；
- **`self._write_cb = _write` 必须保留引用**（见第 9 节）。

**④ 调用 RyCanServoBusInit + 32 个 AddListen**

```python
ret = self._lib.RyCanServoBusInit(ctypes.byref(self.bus), self._write_cb,
                                  ctypes.pointer(self._ticks), 1000)
if ret != 0:
    raise RuntimeError(f"RyCanServoBusInit 失败: ret={ret}")
```

- 注意 tick 指针传了两遍（结构体字段 + 第 3 个参数），与 demo 一致，SDK 以参数为准；
- **ret != 0 直接抛异常**——初始化失败必须显式暴露，不能静默继续。

```python
stu = (CanMsgT * 32)()               # 32 个监听模板帧
for i in range(16):                  # 前 16 个：0xA0 状态查询
    stu[i].ulId = i + 1 + 256        # ID = 伺服ID+256 → 257~272
    stu[i].ucLen = 1
    stu[i].pucDat[0] = 0xA0
    self._lib.AddListen(byref(self.bus), byref(stu[i]), self._listen_cb)
for i in range(16, 32):              # 后 16 个：0xAA 位置速度电流
    stu[i].ulId = (i-16) + 1 + 256   # 同样 257~272
    stu[i].ucLen = 1
    stu[i].pucDat[0] = 0xAA
    self._lib.AddListen(...)
```

- **为什么同一 ID 注册两次？** 伺服对同一 ID 会根据请求内容回不同数据：`0xA0` 回状态、`0xAA` 回位置/速度/电流。SDK 的监听匹配规则是"**ID + 数据首字节**"，所以每个伺服 ID 注册 2 个模板（`0xA0` 一个、`0xAA` 一个）共 32 个，正好对应 `listen_num=33`（第 33 槽保留）；
- 应答载荷统一由 `_listen_cb` 解析（两者位布局相同，见第 4 节）。

**⑤ 启动 tick 线程**

```python
self._tr._on_frame = self._on_frame   # 传输层收帧 → 本控制器
self._running = True
self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
self._rx_thread.start()
```

### 6.5 `_on_frame(can_id, payload)` —— 收帧入口

```python
def _on_frame(self, can_id, payload):
    msg = CanMsgT()
    msg.ulId = can_id
    msg.ucLen = len(payload)
    for i, b in enumerate(payload):
        msg.pucDat[i] = b
    self._lib.RyCanServoLibRcvMsg(ctypes.byref(self.bus), msg)
```

- 被传输层接收线程调用（`transport._dispatch` → `_on_frame`）；
- 把 `(can_id, bytes)` 组装回 `CanMsgT` 后**按值**传给 `RyCanServoLibRcvMsg`；
- SDK 内部匹配 32 个 Listen → 命中 → 同步执行 `_listen_cb`（见 6.4 ④）→ 更新 `_last_servo_info`；
- **注意线程**：本函数运行在传输接收线程上，回调也在这条线程执行（见第 10 节）。

### 6.6 `_rx_loop()` —— 1ms 节拍

```python
while self._running:
    time.sleep(0.001)
    self._ticks.value = int(time.time() * 1000) % 1000
```

- 每 1ms 把 16 位 tick 计数器更新为"当前毫秒数对 1000 取模"（0~999 循环，与 `usTicksPeriod=1000` 配套）；
- SDK 内部定时/超时逻辑全部依赖这个计数器（例如 `update_rate` 上报节奏、监听超时老化）；
- `% 1000` 而不是单调递增：保证与 SDK 期望的周期语义一致，且 16 位 `c_uint16` 不会溢出。

### 6.7 `check_connection(timeout_s=0.5)` —— 连接性自检

返回字典 `{"ok", "version", "replies", "faults", "servos", "need_homing"}`：

| 键 | 含义 |
|---|---|
| `ok` | `replies > 0`，即至少一个电机有应答 → 链路通 |
| `version` | SDK 版本字符串（`GetRyCanServoLibVersion` 写入 30 字节缓冲，按 `\0` 截断、ASCII 解码；老 SDK 无此函数则空） |
| `replies` | 有应答的电机数（1~16，逐个 `get_servo_info(mid, 100ms)`） |
| `faults` | `[(mid, status, 中文说明), ...]` 所有故障电机 |
| `servos` | `{mid: ServoInfo}` 全部回读 |
| `need_homing` | **status==11（找零告警）的电机列表**，是"行程受限/动作幅度小"的快捷根因提示 |

用于 GUI / `test_hand` 的连通性验证：`ok=True` 表示可通信，`faults` 不为空表示有故障电机需处理。

### 6.8 `move_motor(motor_id, position, speed, max_current, control_mode=0)` —— 单电机位置指令

```python
pos = max(0, min(POS_MAX, int(position)))   # 位置钳位到 [0, 4095]
if control_mode == 0:
    return RyMotion_ServoMove_Mix(bus, motor_id, pos, speed, cur, fdb, 0)   # 0xAA 力位混合（带电流限制）
return RyMotion_ServoMove_Speed(bus, motor_id, pos, speed, fdb, 0)          # 0xA1 速度模式
```

- 用于**单电机测试/排查**（如"中指远节电机 9 无响应"时单独驱动它验证）；
- speed / max_current 缺省时用 `default_speed=1000` / `default_max_current=75`；
- `control_mode=0` → 力位混合（0xAA，**带电流限制，带载安全**）；非 0 → 速度模式（0xA1，**无电流限制，仅空载调试**）；
- 返回 SDK 返回值（0 = 成功）。

### 6.9 `move_joints(angles_rad_16, speed, max_current, hand_lr, control_mode=0, inter_sleep_s=0.0005)` —— 16 关节弧度控制

```python
if len(angles_rad_16) != JOINT_NUM: raise ValueError(...)   # 必须恰好 16 个
cmds = angles_to_motor_cmds(list(angles_rad_16), hand_lr=hlr)  # 弧度 → 0~4095 指令
for i, pos in enumerate(cmds):
    # 电机 ID = 关节索引 + 1（关节 1~16 ↔ 电机 1~16）
    RyMotion_ServoMove_Mix / _Speed(bus, i + 1, pos, speed, cur, fdb, 0)
    if inter_sleep_s > 0: time.sleep(inter_sleep_s)          # 500µs 间隔，避免总线风暴
return cmds
```

- 输入是 **16 个关节的弧度**（顺序 = 关节 ID 1~16：拇指侧摆/近节/远节、食指…、第 16 关节）；
- 换算规则（`angles2motor`，与官方 demo `update_motor_positions` 一致）：
  - `M1 = K12·(θ侧摆/2 + θ近节)`，`M2 = K12·(−θ侧摆/2 + θ近节)`（`K12=4095/90`）
  - `M3 = K3·θ远节`（`K3=4095/75`），`M16 = K16·θ16`（`K16=4095/110`）
  - 左手时每指 M1↔M2 交换；
- 每个角度先按手册范围钳位（侧摆 ±20°、近节 0~90°、远节 0~75°、第16关节 0~110°）；
- `inter_sleep_s=0.5ms`：16 帧连续下发间隔，防止瞬时总线拥塞导致丢帧（0xAA 指令逐帧确认，间隔过短可能丢应答）；
- 返回下发用的 `cmds`（16 个 0~4095 指令），便于调用方记录/校验。

### 6.10 `get_servo_info(motor_id, timeout_ms=100)` —— 同步读单电机状态

```python
data = ServoDataT()
ret = self._lib.RyFunc_GetServoInfo(bus, motor_id, byref(data), c_uint16(timeout_ms))
if ret != 0: return None
return parse_servo_data(data)
```

- `RyFunc_GetServoInfo` 是**同步阻塞**调用：内部发 0xA0 请求 → 等应答（超时 `timeout_ms`）→ 写入 `data`；
- 返回 0 成功 → `parse_servo_data` 解析出 `ServoInfo`；非 0（超时/无应答）→ `None`；
- `check_connection` / `read_joint_angles` / `check_all_strokes` 都基于它。

### 6.11 `read_joint_angles(hand_lr=None)` —— 读取 16 关节角度（弧度）

```python
for mid in range(1, 17):
    info = self.get_servo_info(mid, timeout_ms=100)
    cmds.append(info.position if info else 0)     # 无应答的电机按 0 处理
return motor_cmds_to_joint_angles(cmds, hand_lr=hlr)
```

- 逐电机读位置（0~4095）→ 逆换算回 16 个关节弧度（`motor_cmds_to_joint_angles`：`θ侧摆=(M1−M2)/K12`、`θ近节=(M1+M2)/(2·K12)`、`θ远节=M3/K3`、`θ16=M16/K16`，左手先交换）；
- **注意**：读不到应答的电机位置按 0 参与换算，可能使读回角度失真——排查时先确认 `replies` 是否满 16。

### 6.12 `open_hand()` / `close_hand()` / `relax()` —— 预设手势

```python
def open_hand(self, ...):
    self.move_joints([0.0] * 16, ...)   # 全关节 0°：完全张开（侧摆 0、弯曲 0）

def close_hand(self, ...):
    angles = [0,50,30,  0,70,60,  0,70,60,  0,70,60,  0,70,60,  0]   # 度
    self.move_joints([math.radians(a) for a in angles], ...)

def relax(self, ...):
    angles = [0,30,15,  0,35,25,  0,35,25,  0,35,25,  0,35,25,  0]   # 度
    self.move_joints(...)
```

**标准握拳角度表设计说明**（每指 3 关节 = [侧摆, 近节, 远节]，第 16 关节单独）：

| 手指 | 侧摆 | 近节 | 远节 | 理由 |
|---|---|---|---|---|
| 拇指 | 0° | 50° | 30° | 拇指近节/远节关节物理行程与结构较短，且握拳时过度弯曲会顶到掌心，取 50/30 既能握实又不自锁 |
| 食指/中指/无名指/小指 | 0° | 70° | 60° | 落在手册范围（近节 0~90°、远节 0~75°）内偏大值，形成"握实但不僵死"的拳；侧摆 0° 避免握拳时产生横向力矩 |
| 第 16 关节 | — | — | 0° | 拇指横向旋转（内外展）在握拳时保持中立 |

- **为什么这样设计**：官方 demo 的 `palm_bend` 预设里食指远节=0（伸直）、且带侧摆，那更像"伸掌/半握"而不是"握拳"；本实现按手册角度范围重新设计了符合"握拳"语义的角度表；
- `relax` 是"自然放松半握"：手指半弯（近节 35°、远节 25°），侧摆 0，适合长时间待机演示。

### 6.13 `reset(motor_id)` / `clear_fault(motor_id)`

```python
def reset(self, motor_id):        # 复位电机（断电重启等效）
    return self._lib.RyFunc_Reset(bus, motor_id, 100)          # 超时 100ms
def clear_fault(self, motor_id):  # 清除故障码
    return self._lib.RyParam_ClearFault(bus, motor_id, 100)
```

- 时序建议：电机报故障（status≠0）时先 `clear_fault`；仍异常再 `reset`；**再不行检查机械/供电**（见第 12 节排查表）。

### 6.14 `get_stroke(motor_id, timeout_ms=100)` —— 读行程

```python
val = ctypes.c_uint32(0)
ret = self._lib.RyParam_GetStroke(bus, motor_id, byref(val), timeout_ms)
if ret != 0: return None
return int(val.value)
```

- 行程 = 电机可运动的全量程（0~4095 为满行程）；
- **排查"第 16 关节（拇指横向旋转）幅度小"**：若行程远小于 4095，说明该电机行程配置被限制（可能被上位机/参数误设），需用 `set_stroke` 恢复或上位机校准；
- 老 SDK 无此函数时 try/except 兜底返回 None。

### 6.15 `set_stroke(motor_id, stroke, timeout_ms=100)` —— 写行程（谨慎）

- **必须先 `get_stroke` 读当前值再改**，避免误设导致电机行程越界撞机械限位；
- 恢复满行程传 4095；
- 失败返回 `0xFF`（老 SDK 无此函数/执行失败）。

### 6.16 `check_joint16_stroke()` —— 第 16 关节专项排查

```python
stroke = self.get_stroke(16)
info   = self.get_servo_info(16, timeout_ms=100)
return {"stroke": stroke, "servo": info,
        "suggest": "行程正常" if stroke >= 3000 else
                   "行程偏小（<3000），16号电机幅度会很小。请用上位机校准/设置行程 RyParam_SetStroke 为 4095"}
```

- 一站式回答"**拇指横向旋转为什么幅度小**"：行程阈值 3000 经验值，低于即提示；
- 同时带上 `servo`（含 status，若为 11 则还需回零）。

### 6.17 `set_home_mode(motor_id, mode, timeout_ms=1000)` —— 回零设置/执行（CMD 0xBE）

mode（官方 demo 语义）：

| mode | 含义 |
|---|---|
| 0 | **上电自执行归零**（配置保存到驱动器，下次上电自动找零） |
| 1 | 上电**不**自动归零 |
| 2 | **立即执行一次归零动作** |

- **status=11（找零告警）就是"没回零、行程受限"**；执行 `mode=2` 归零后行程恢复；
- 老 SDK 无此函数时返回 `0xFF`。

### 6.18 `homing(motor_ids=None, timeout_ms=1000, sleep_s=0.05)` —— 批量回零

```python
if motor_ids is None: motor_ids = list(range(1, 17))   # 默认全部电机
for mid in motor_ids:
    ret = self.set_home_mode(mid, 2, timeout_ms)       # 立即执行归零
    result[mid] = ret
    time.sleep(sleep_s)                                 # 50ms 间隔，避免总线拥塞
return result                                           # {mid: ret}
```

- **解决"动作几乎看不见/行程太小"的最常见根因**（status=11）；
- 返回值 `{电机ID: SDK返回码}`，可用于统计成功数。

### 6.19 `check_all_strokes()` —— 全电机行程体检

```python
for mid in range(1, 17):
    stroke = self.get_stroke(mid, timeout_ms=100)
    info   = self.get_servo_info(mid, timeout_ms=100)
    out[mid] = {"stroke": stroke, "info": info}
```

- 用于"动作几乎看不见"排查：正常应 `stroke≈4095` 且 `info.status==0`；
- 行程 < 4095 → 行程受限（`set_stroke` 恢复）；status=11 → 未回零（`homing()`）。

### 6.20 `close()` —— 资源释放（顺序很重要）

```python
self._running = False                    # ① 停 tick 线程
if self._rx_thread is not None:
    self._rx_thread.join(timeout=1.0)    # ② 等 tick 线程退出（最多 1s）
try:
    self._lib.RyCanServoBusDeInit(byref(self.bus))   # ③ SDK 反初始化（先于物理关闭）
except Exception: pass
if self._tr is not None:
    self._tr.close()                     # ④ 关闭物理通道 + 停传输接收线程
```

- 顺序逻辑：**先停软件层（tick）→ 再 SDK 反初始化 → 最后关物理通道**。若先关物理通道，SDK 反初始化时可能尝试发帧而失败；
- `daemon=True` 的线程即使 join 超时也不会阻塞进程退出。

---

## 7. ctypes 关键点（必读）

### 7.1 CFUNCTYPE 回调必须持有引用，防止被 GC

```python
self._write_cb  = _write     # SDK 内部长期保存这个函数指针
self._listen_cb = _listen_cb # SDK 匹配到帧时调用
```

- `ctypes.CFUNCTYPE` 包装出的回调对象是普通 Python 对象，**SDK 只保存 C 函数指针，不持有 Python 引用**；
- 如果回调对象被垃圾回收，其底层 C 函数指针变成悬垂指针，SDK 下次调用直接**崩溃（访问违例）**；
- 因此必须把回调存为实例属性（`self._xxx_cb`）——本文件两个回调都这么做了，这是 ctypes 回调的**标准铁律**。

### 7.2 ctypes.cast —— 数组转指针

```python
self.bus.pstuHook   = ctypes.cast(hooks,   ctypes.POINTER(MsgHookT))
self.bus.pstuListen = ctypes.cast(listens, ctypes.POINTER(MsgListenT))
```

- ctypes 数组对象本身就是一段连续内存，`cast(数组, POINTER(T))` 只是**类型层面**把它当作 `T*`，不复制数据；
- 用途：C 结构体需要 `MsgHookT*` / `MsgListenT*` 指针，而 Python 侧持有的是数组对象；
- **生命周期陷阱**：`hooks`/`listens` 是 `_init_bus` 的局部变量。若 SDK 在 `RyCanServoBusInit` 时**只保存指针而不拷贝**，函数返回后数组可能被 GC，`self.bus` 里的指针悬垂 → 后续访问崩溃或数据错乱。**加固建议**：把数组存为实例属性（如 `self._hooks` / `self._listens`）保持存活，与回调保持引用同理。当前实现依赖 SDK 在 Init 时拷贝进内部缓冲（多数厂家 SDK 如此），但显式持有引用是最稳妥的。

### 7.3 byref vs pointer

| 用法 | 特点 | 适用 |
|---|---|---|
| `ctypes.byref(obj)` | 轻量、不创建新对象，只生成"地址引用"，**不能用来长期保存** | 绝大多数函数传参（`RyCanServoBusInit`、`RyFunc_GetServoInfo`、`AddListen` 等） |
| `ctypes.pointer(obj)` | 创建真正的指针对象，可长期持有 | 需要存进结构体字段（`bus.pusTicksMs = ctypes.pointer(self._ticks)`）、或需要后续解引用 |

本文件两处都用得恰当：函数调用一律 `byref`（快），需要 SDK 跨会话引用的用 `pointer`/`cast`。

### 7.4 结构体按值传参（RyCanServoLibRcvMsg）

```python
L.RyCanServoLibRcvMsg.argtypes = [POINTER(RyCanServoBusT), CanMsgT]  # 第二个参数是按值
self._lib.RyCanServoLibRcvMsg(byref(self.bus), msg)                  # 直接传结构体对象
```

- ctypes 允许把结构体**按值**传给 C 函数（自动在调用栈上拷贝一份）；
- 本函数声明为按值接收，SDK 内部再把内容拷到自己的缓冲——所以调用后局部 `msg` 可以安全销毁；
- 对比：`AddListen` 的模板参数是 `POINTER(CanMsgT)`（按指针），SDK 需要**引用**模板做匹配，所以模板数组 `stu` 必须存活（它是 `_init_bus` 局部变量——同上生命周期注意，建议持引用）。

### 7.5 restype / argtypes 的意义

- 不声明 `restype` 时 ctypes 假定返回 `int`（32 位截断），声明为 `c_uint8`/`None` 才能正确取回返回值；
- `argtypes` 让 ctypes 做**参数类型检查与自动转换**（如 `ctypes.c_uint16(timeout_ms)` 的显式转换其实可省略，argtypes 会自动转；显式写出是为了自文档化）；
- 三个 try/except 包裹的声明：老 SDK 缺导出符号时，`L.xxx` 属性访问抛 `AttributeError`，包裹后降级可用。

---

## 8. 线程模型

系统中共有 **3 条活跃线程**（外加调用方主线程）：

| 线程 | 创建处 | 职责 | 终止方式 |
|---|---|---|---|
| **传输接收线程** | `CanTransport.open()`（daemon） | 读硬件帧（PCAN `Read` / CANII `VCI_Receive` / RS485 串口）→ `_dispatch` → `_on_frame` → `RyCanServoLibRcvMsg` → **同步执行 `_listen_cb`** → 更新 `_last_servo_info` | `close()` 置 `_running=False` + `join(1s)` |
| **tick 线程** | `RYH1HandController._init_bus()`（daemon） | 每 1ms 更新 `_ticks.value = ms % 1000`，供 SDK 计时 | `close()` 置 `_running=False` + `join(1s)` |
| **写回调**（无独立线程） | — | SDK 在**调用运动 API 的线程**（通常是主线程/GUI 线程）内同步回调 `_write` → `transport.send()` | 随调用线程结束 |
| 主线程/调用线程 | 应用 | 调 `move_joints`、`get_servo_info`、`check_connection` 等 | — |

**数据流向与时序**：

1. 主线程调 `move_joints` → 每个电机调 `RyMotion_ServoMove_Mix`（0xAA）→ SDK 同步回调 `_write` 发帧 → 返回；
2. 伺服应答帧被传输接收线程读到 → `_on_frame` → `RyCanServoLibRcvMsg`（运行在接收线程）→ SDK 匹配 Listen → 同线程执行 `_listen_cb` → 写 `_last_servo_info[mid]`；
3. 同步 API（`get_servo_info`）在**主线程**阻塞等待应答：SDK 内部"发请求 → 等接收线程喂进来的应答"完成同步往返（SDK 内部有等待机制，超时由 tick 计数驱动）；
4. tick 线程独立推进 1ms 计数器，SDK 的所有超时/调度都基于它。

**线程安全要点**：

- `_last_servo_info`：接收线程写、主线程读——dict 的读写受 GIL 保护，单条赋值原子，无锁可用（可能读到旧值，但不会崩溃；对状态监控场景可接受）；
- `_running` 标志：bool 读写原子，用于优雅停止；
- `_ticks.value`：tick 线程独占写，SDK 在别的线程读——16 位读写原子，无竞争问题；
- 回调 `_listen_cb` / `_write` 内**不能做耗时操作**（如阻塞 IO、sleep），否则会拖慢接收线程或调用线程。

---

## 9. 安全注意（操作灵巧手前必读）

1. **带载必须用 0xAA 力位混合**（`control_mode=0`，带 `max_current` 电流限制）；0xA1 速度模式无电流限制，**仅限空载调试**，带载使用可能过流损坏电机。
2. **上电后先 `check_connection()`**：确认 16 个电机都有应答、`faults` 为空再动作。
3. **status=11（找零告警）必须先回零**：`homing()`（mode=2）后再运动，否则行程受限、动作幅度小，强行大幅运动可能撞限位。
4. **回零/动作时手指会运动**：确保手周围无人员、无易损物品、无夹持物。
5. **行程检查**：`check_all_strokes()` / `check_joint16_stroke()`，行程应 ≈4095；异常时先 `set_stroke` 恢复，**不要盲目加大速度/电流来"补偿"幅度**。
6. **不要热插拔**：先 `hand.close()`（SDK 反初始化 + 关物理通道）再拔 USB-CAN / 串口线；带电拔插可能损坏接口或让 SDK 处于不一致状态。
7. **清故障顺序**：`clear_fault` → 仍异常 → `reset` → 仍异常 → **断电检查机械与供电**（堵转/过流多数是机械卡阻，不是软件问题）。
8. **参数谨慎**：`default_speed` / `default_max_current` 不要随意调大；`set_stroke` 前务必先 `get_stroke` 读当前值。
9. **左右手不要搞反**：症状"滑近节实际动侧摆"时用 `set_hand_lr` 切换（无需重连）。
10. **RS485 半双工**：一主一从拓扑，波特率 5Mbps，线材尽量短；`move_joints` 的 `inter_sleep_s` 不要设 0（避免总线风暴丢帧）。

---

## 10. 常见问题排查（FAQ）

### 10.1 某电机 status=11（找零告警）

- **现象**：`check_connection()` 的 `need_homing` 列表包含该电机；动作幅度小或不动。
- **原因**：电机断电后失去零点，或上电未执行归零。
- **处理**：`hand.homing([mid])` 立即归零；或 `hand.set_home_mode(mid, 0)` 配置"上电自归零"一劳永逸。

### 10.2 某电机无响应（get_servo_info 返回 None）

排查顺序：

1. `check_connection()` 看 `replies`：<16 说明有电机掉线；
2. 对目标电机 `clear_fault(mid)` → `reset(mid)` → 再 `get_servo_info(mid)`；
3. 用 `move_motor(mid, 2000)` 单独驱动，观察是否动作、`replies` 是否恢复；
4. 硬件排查：接线/接插件（尤其该电机对应连接器）、供电、电机本身损坏（项目里曾出现"中指远节电机 9 无响应"，多为硬件问题）；
5. 仍无应答：换一根 CAN/串口线，或换一块 USB-CAN 排除总线问题。

### 10.3 动作幅度小 / 几乎看不见

按概率排序的根因与对策：

| 根因 | 判据 | 对策 |
|---|---|---|
| 未回零（status=11） | `check_all_strokes()` 里 `info.status==11` | `homing()`（mode=2） |
| 行程被限制 | `get_stroke(mid) < 3000` | `set_stroke(mid, 4095)` 或上位机校准 |
| 第 16 关节幅度小 | `check_joint16_stroke()` 的 `suggest` | 同上，专查 16 号 |
| 左右手选反 | 滑近节滑条实际动侧摆 | `set_hand_lr(0/1)` 切换 |
| 角度表本身偏小 | 预设 `relax` 只有 35° | 用 `move_joints` 传大角度验证行程 |

### 10.4 版本读不到 / 行程接口报错

- `GetRyCanServoLibVersion` / `RyParam_GetStroke` 等是较新 SDK 才有的 API；老 DLL 下 `check_connection()["version"]` 为空、`get_stroke` 返回 None——**属正常降级**，不影响运动控制；如需行程/回零功能请升级厂家 SDK。

### 10.5 PCAN / CANalyst-II 打不开

- PCAN：确认 PCAN-USB 已插入、驱动已装、无其他软件占用；波特率固定 1Mbps；
- CANalyst-II：确认 `ControlCAN.dll` / `ControlCAN.py` 在 lib/ 或根目录、设备未被占用；
- RS485：确认串口号（默认 COM3）与 5Mbps 支持（部分 USB 转串口芯片不支持高速率）。

### 10.6 回读数据全是 0 / 状态异常

- 检查回调过滤条件：`mid = msg.ulId & 0xFF`（1~16）且 `ucLen >= 8`；若应答被截断（`ucLen<8`）会被丢弃——先看 `replies` 是否正常；
- 检查位解析：`parse_servo_info` 只取前 8 字节小端解析，抓包核对 byte1=status、byte2-3=position 是否符合 4.2 的字节表。

---

## 11. 附录：与官方 demo 的对齐点速查

| 项 | 本实现 | 官方 demo |
|---|---|---|
| hook 数量 | 40（`hand_config`） | 40 |
| listen 数量 | 33（32 个 AddListen + 1 保留） | 33 |
| 监听模板 | 16×0xA0 + 16×0xAA，ID=伺服ID+256 | 同 |
| tick | 1ms 计数器 `% 1000`，`usTicksPeriod=1000` | 同 |
| 换算 | `M1=k(θ1/2+θ2)`、`M2=k(−θ1/2+θ2)`、`M3=k·θ3`、`M16=k·θ16`（k=4095/90、4095/75、4095/110） | `update_motor_positions` 同 |
| 左右手 | `hand_lr=0` 时 M1↔M2 交换 | 同 |
| 回零 | `RyParam_SetHomeMode` mode=2（CMD 0xBE） | `set_home_mode` 同 |
| 握拳 | 拇指 50/30、四指 70/60、侧摆 0、第16关节 0（按手册范围重设计） | demo `palm_bend`（食指远节=0 且带侧摆，不符合握拳语义，已改进） |

---

*文档结束。对应源码：`hand/hand_controller.py`（630 行）。*
