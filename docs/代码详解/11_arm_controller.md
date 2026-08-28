# 11 · arm_controller.py —— Aubo K5 机械臂高层控制器（pyaubo_sdk RPC）代码详解

> 本文档逐行级详解 `arm/arm_controller.py`（607 行，Windows 版"睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂视觉动作模仿系统"的**机械臂高层控制器**）。
> 阅读本文档**不需要再读源码**即可完整理解该文件的职责、连接流程、每个方法、阻塞模型、TCP 坐标联动原理与安全要点。
> 建议搭配阅读：`arm/arm_config.py`（连接与运动默认参数）、`docs/机械臂控制执行文档.md`（整机执行流程）、官方 SDK 示例 `lib/aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170/share/example/python/`。

---

## 目录

1. [文件总览](#1-文件总览)
2. [模块 docstring 与导入（含 _AUBO_OK 保护机制）](#2-模块-docstring-与导入含-_aubo_ok-保护机制)
3. [类 AuboK5ArmController 与构造](#3-类-aubok5armcontroller-与构造)
4. [连接与断开：open / has_connected / has_logined / close](#4-连接与断开open--has_connected--has_logined--close)
5. [电源管理：poweron / startup / poweroff / poweron_and_startup](#5-电源管理poweron--startup--poweroff--poweron_and_startup)
6. [状态读取：模式 / 安全 / 位形 / 汇总 / 速度](#6-状态读取模式--安全--位形--汇总--速度)
7. [TCP 坐标联动：apply_tcp_offset](#7-tcp-坐标联动apply_tcp_offset)
8. [运动控制：_wait_arrival / movej / movel / movec / move_home / stop_move / servo](#8-运动控制_wait_arrival--movej--movel--movec--move_home--stop_move--servo)
9. [示教：freedrive](#9-示教freedrive)
10. [IO 控制](#10-io-控制)
11. [正逆解：forward_kinematics / inverse_kinematics](#11-正逆解forward_kinematics--inverse_kinematics)
12. [工具方法：_ret_text（返回码转中文）](#12-工具方法_ret_text返回码转中文)
13. [模块级函数：quick_check](#13-模块级函数quick_check)
14. [与官方示例对照表（汇总）](#14-与官方示例对照表汇总)
15. [线程与阻塞注意](#15-线程与阻塞注意)
16. [常见问题（FAQ）](#16-常见问题faq)
17. [典型调用时序](#17-典型调用时序)
18. [方法索引表](#18-方法索引表)

---

## 1. 文件总览

### 1.1 职责

本文件是机械臂控制链路的**最高层**，向下只依赖两样东西：

| 依赖 | 作用 |
|---|---|
| `pyaubo_sdk`（遨博官方 Python SDK，RPC） | 与机械臂控制柜通信的唯一通道（TCP，默认端口 30004） |
| `arm.arm_config.ARM_CONFIG` | 全部连接/运动默认参数（IP、端口、账号、速度、TCP 偏移等） |

它把 SDK 的**底层过程式调用**封装成**面向业务的高层语义**，具体做六件事：

1. **连接生命周期**：`open()` 一次性完成「连接 → 登录 → 取机器人名 → 取接口 → 缓存 6 个子接口 → 设速度 → 写 TCP 偏移」，`close()` 统一登出断开；
2. **电源管理**：上电 `poweron`、启动松刹车 `startup`、断电 `poweroff`，以及带 **Running 轮询**的 `poweron_and_startup`；
3. **运动控制**：关节运动 `movej`、直线 `movel`、圆弧 `movec`、急停 `stop_move`、视觉跟随用的关节伺服 `servo_joint`，全部带**单位换算**（度↔弧度）与**阻塞等待**（`_wait_arrival`）封装；
4. **TCP 坐标联动**：`apply_tcp_offset` 把「基础工具偏移 + 灵巧手安装偏移」相加后写入 `setTcpOffset`，使 `movel`/`movec` 的位姿直接以**灵巧手 TCP** 为基准；
5. **示教与状态**：`freedrive` 拖拽示教、模式/安全/关节角/TCP 位姿/IO 全量状态读取；
6. **算法辅助**：正解 `forward_kinematics`、逆解 `inverse_kinematics`（视觉坐标 → 关节角的关键桥梁）。

**使用场景**：GUI（`gui/main_gui_arm.py`）与命令行工具（`apps/test_arm.py`、`apps/diag_arm.py`）共用本控制器。

### 1.2 数据流总览（ASCII 图）

```
 调用方：GUI（main_gui_arm.py） / 命令行（test_arm.py / diag_arm.py）
   │    arm.movej([...], block=True) / arm.movel(pose) / arm.get_state_summary() ...
   ▼    高层语义：弧度、米、block 阻塞、中文错误信息
┌───────────────────────────────────────────────────────────────────────────────┐
│            AuboK5ArmController（本文件 arm/arm_controller.py）                   │
│                                                                                 │
│  缓存句柄（open() 时通过 getRobotInterface(name) 一次性取齐）                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ _robot_manage     ← RobotManage     │ 上电/启动/断电/自由驱动示教           │   │
│  │ _motion_control   ← MotionControl   │ moveJoint/moveLine/moveCircle/       │   │
│  │                                     │ servoJoint/setSpeedFraction/         │   │
│  │                                     │ getExecId/stopMove/servo模式         │   │
│  │ _robot_state      ← RobotState      │ 模式/安全模式/是否停稳/关节角/        │   │
│  │                                     │ TCP位姿/安全限位                     │   │
│  │ _robot_config     ← RobotConfig     │ setTcpOffset（TCP 坐标联动写入端）     │   │
│  │ _io_control       ← IoControl       │ 标准数字 IO / 工具端 IO 读写          │   │
│  │ _robot_algorithm  ← RobotAlgorithm  │ forwardKinematics/inverseKinematics  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  所有子接口的调用最终都汇到 _client（pyaubo_sdk.RpcClient）发出 RPC 请求           │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    ▼ TCP RPC（默认 30004 端口，登录 aubo/123456）
┌───────────────────────────────────────────────────────────────────────────────┐
│                pyaubo_sdk.RpcClient（遨博官方 Python SDK）                       │
│   connect / setRequestTimeout / login / logout / disconnect /                  │
│   hasConnected / hasLogined / getRobotNames / getRobotInterface                │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    ▼ RPC over TCP（局域网）
                          ┌─────────────────────────────────────┐
                          │       机械臂控制柜（Aubo 控制柜）      │
                          │   解析指令 → 运动规划 → 伺服控制       │
                          │   安全逻辑（限位/奇异点/急停）          │
                          └──────────────────┬──────────────────┘
                                             ▼ 动力线 / 编码器 / 抱闸
                          ┌─────────────────────────────────────┐
                          │        Aubo K5 六轴机械臂             │
                          │   （法兰盘下方挂 RY-H1(16) 灵巧手）    │
                          └─────────────────────────────────────┘
```

**6 个子接口的分工一句话总结**：
- **RobotManage** —— 管"电与状态机"（上电、启动、断电、自由驱动）；
- **MotionControl** —— 管"动"（各类运动指令、速度比例、运动 ID、停止、伺服）；
- **RobotState** —— 管"看"（当前模式、安全模式、关节角、TCP 位姿）；
- **RobotConfig** —— 管"标定"（TCP 工具偏移，决定 movel/movec 的坐标系基准）；
- **IoControl** —— 管"数字量"（标准端 + 工具端 IO，可联动外部传感器/夹爪供电）；
- **RobotAlgorithm** —— 管"算"（正解/逆解，纯算法，不触发运动）。

### 1.3 代码结构地图

| 行号区间 | 内容 |
|---|---|
| 1–27 | 模块 docstring（职责/API 依据/用法示例） |
| 29–45 | 导入 + `_AUBO_OK` 保护机制 |
| 48–53 | 模块级工具函数 `_deg2rad_list` / `_rad2deg_list` |
| 56–101 | 类 `AuboK5ArmController` 与 `__init__` |
| 103–193 | **连接/断开**：open / has_connected / has_logined / close |
| 195–239 | **电源管理**：poweron / startup / poweroff / poweron_and_startup |
| 241–314 | **状态读取**：模式/安全/停稳/关节角/TCP 位姿/汇总/速度 |
| 316–343 | **TCP 坐标联动**：apply_tcp_offset / get_hand_mount_offset |
| 345–489 | **运动控制**：_wait_arrival / movej / movel / movec / move_home / stop_move / servo 系列 |
| 491–512 | **示教**：freedrive |
| 514–555 | **IO 控制**：标准/工具数字 IO |
| 557–578 | **正逆解**：forward_kinematics / inverse_kinematics |
| 580–592 | **工具**：_ret_text（返回码转中文） |
| 595–607 | **模块级**：quick_check |

---

## 2. 模块 docstring 与导入（含 _AUBO_OK 保护机制）

### 2.1 docstring 逐句解读（第 1–27 行）

```python
"""
arm_controller.py —— Aubo（遨博）K5 机械臂高层控制器（Windows 版）

职责：
  * 通过 pyaubo_sdk（RPC）连接/登录机械臂控制柜
  * 电源管理：上电、启动（松刹车）、断电
  * 运动控制：关节运动 movej / 直线 movel / 圆弧 movec / 关节伺服 servoJoint（视觉跟随用）
  * 状态读取：模式、安全模式、关节角、TCP 位姿、是否停止、IO 等
  * 工具配置：setTcpOffset（TCP 坐标联动 = 写入灵巧手安装偏移）
  * 示教：freedrive 拖拽示教
  * 正逆解：forwardKinematics / inverseKinematics
"""
```

- 逐条职责与本文件 1.1 节一致，注意第 5 条把 `setTcpOffset` 明确定义为 **"TCP 坐标联动 = 写入灵巧手安装偏移"**——这是本系统把机械臂坐标系与灵巧手坐标系"打通"的关键设计（详见第 7 节）。
- docstring 中给出了**最小可用示例**（第 19–26 行）：`open()` → `poweron_and_startup()` → `movej/movel(block=True)` → `close()`，并注明 `movel` 的位姿是 **TCP 系**（以灵巧手 TCP 为基准，见第 7 节）。

### 2.2 导入与 `_AUBO_OK` 保护机制（第 29–45 行）—— 重点

```python
from __future__ import annotations   # 延迟求值类型注解（Py3.7+），避免运行时解析注解

import logging
import math
import time
from typing import List, Optional, Tuple

logger = logging.getLogger("arm")

try:
    import pyaubo_sdk
    _AUBO_OK = True
except ImportError:  # pragma: no cover
    pyaubo_sdk = None
    _AUBO_OK = False

from .arm_config import ARM_CONFIG, CONN_ERROR_TEXT, DOF
```

**`_AUBO_OK` 保护机制详解**（本文件最重要的防御性设计之一）：

1. **动机**：`pyaubo_sdk` 是第三方二进制扩展包（Windows 下需要装 `pyaubo-sdk==0.27.1rc4`）。如果直接 `import pyaubo_sdk` 失败，整个模块的 import 会抛 `ImportError`，导致**上层模块（GUI 等）在启动时就崩溃**，用户得不到任何友好提示。
2. **做法**：用 `try/except ImportError` 包裹导入。成功 → `_AUBO_OK = True`；失败 → `pyaubo_sdk = None`、`_AUBO_OK = False`，**模块照常导入成功**。
3. **后果**：任何依赖 `pyaubo_sdk` 的代码在运行前必须先查 `_AUBO_OK`。本文件在两处检查：
   - `__init__`（第 78–79 行）：抛 `RuntimeError("未安装 pyaubo_sdk：请执行 pip install pyaubo-sdk==0.27.1rc4")` —— 把"装依赖"的具体命令直接告诉用户；
   - `open()`（第 108–109 行）：抛 `RuntimeError("未安装 pyaubo_sdk")` —— 二次保险（正常情况下构造时已拦截）。
4. **为什么这样写**：
   - 让模块可以被安全 import（例如用于生成文档、类型检查、或 GUI 在未装 SDK 时仍能启动并弹出错误对话框）；
   - 把"缺依赖"从**导入期错误**推迟为**使用期错误**，且错误信息带安装指引；
   - `# pragma: no cover` 标注该分支不参与覆盖率统计（因为正常情况下不会执行）。

> ⚠️ **注意**：`CONN_ERROR_TEXT`（连接错误码中文解释）虽然被导入，但本文件中并未直接使用——它主要供上层 GUI/诊断工具（`diag_arm.py`）展示连接错误时查阅。这也说明 `arm_config.py` 是"配置中心"，各模块按需取用。

### 2.3 模块级工具函数（第 48–53 行）

```python
def _deg2rad_list(vals) -> List[float]:
    return [math.radians(v) for v in vals]

def _rad2deg_list(vals) -> List[float]:
    return [math.degrees(v) for v in vals]
```

- 纯数学工具：整列表的度↔弧度批量换算，列表推导式逐元素转换。
- 下划线前缀表示"模块私有"，不对外暴露。
- 本文件中只有 `_deg2rad_list` 被实际使用（`move_home` 把"度"写法的 home 点转成弧度）；`_rad2deg_list` 是配套提供的对称工具（供上层显示关节角时使用，如 GUI 里把弧度关节角显示成度）。

---

## 3. 类 AuboK5ArmController 与构造

### 3.1 类定位（第 56–57 行）

```python
class AuboK5ArmController:
    """Aubo K5 机械臂控制器（Windows，pyaubo_sdk RPC）。"""
```

- 一个实例 = **一条到机械臂控制柜的完整控制通道**。它把 SDK 的"全局 RpcClient + 每次现取子接口"的用法，收敛为"构造一次、`open()` 一次、之后所有方法直接用缓存的子接口句柄"。
- 对比官方示例：示例里每次操作都写 `robot_rpc_client.getRobotInterface(robot_name).getMotionControl()...` 一大串；本类在 `open()` 里取一次、缓存 7 个字段，后面所有方法一行 `self._motion_control.xxx()` 即可——这是高层封装的核心价值。

### 3.2 `__init__` 构造参数（第 59–91 行）

```python
def __init__(
    self,
    ip: Optional[str] = None,
    rpc_port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    speed_fraction: Optional[float] = None,
    tcp_offset: Optional[List[float]] = None,
    hand_mount_offset: Optional[List[float]] = None,
):
```

| 参数 | 默认来源 | 含义 |
|---|---|---|
| `ip` | `ARM_CONFIG["ip"]` = `"192.168.1.100"` | 机械臂控制柜 IP（实机按控制柜网口 IP；官方示例默认 127.0.0.1 是本机/模拟器） |
| `rpc_port` | `ARM_CONFIG["rpc_port"]` = `30004` | RPC 服务端口 |
| `username` / `password` | `"aubo"` / `"123456"` | 控制柜登录账号 |
| `speed_fraction` | `ARM_CONFIG["speed_fraction"]` = `0.3` | 全局速度比例 0~1（0.3 是安全起步值；官方示例用 0.75） |
| `tcp_offset` | `ARM_CONFIG["tcp_offset"]` = 全 0 | 基础工具中心点偏移 `[x,y,z,rx,ry,rz]`（米/弧度，相对法兰盘中心） |
| `hand_mount_offset` | `ARM_CONFIG["hand_mount_offset"]` = `[0,0,0.15,π,0,0]` | **灵巧手安装偏移**（TCP 坐标联动核心，见第 7 节）；`None` 表示不启用联动 |

构造逻辑逐段：

```python
if not _AUBO_OK:
    raise RuntimeError("未安装 pyaubo_sdk：请执行 pip install pyaubo-sdk==0.27.1rc4")
```

- 第 78–79 行：**第一道 `_AUBO_OK` 检查**（见 2.2 节）。在构造阶段就把缺依赖问题暴露出来，而不是等到 `open()`。

```python
self.ip = ip or ARM_CONFIG["ip"]
...
self.speed_fraction = (
    speed_fraction if speed_fraction is not None else ARM_CONFIG["speed_fraction"]
)
self._tcp_offset = list(tcp_offset) if tcp_offset else list(ARM_CONFIG["tcp_offset"])
self._hand_mount_offset = (
    list(hand_mount_offset) if hand_mount_offset is not None else None
)
```

- 显式传参优先，否则回落到 `ARM_CONFIG` 默认值——**"调用方可覆盖、不传有安全默认"** 的设计。
- 注意 `tcp_offset` 与 `hand_mount_offset` 都做了 `list(...)` 拷贝：防止外部列表后续被修改导致控制器内部状态被污染（防御性拷贝，避免别名共享 bug）。
- `hand_mount_offset` 的判定用 `is not None`（而不是 `if hand_mount_offset`），因为全零列表 `[0,0,0,0,0,0]` 是合法值（表示"安装偏移为零"），不能被当成"未提供"。

### 3.3 实例状态字段（第 93–101 行）

```python
self._client = None            # pyaubo_sdk.RpcClient —— 连接/登录/登出/断开的门面
self._robot_interface = None   # RobotInterface —— 各子接口的工厂
self._robot_name: Optional[str] = None
self._robot_manage = None      # RobotManage     —— 电源/示教
self._motion_control = None    # MotionControl   —— 运动
self._robot_state = None       # RobotState      —— 状态
self._robot_config = None      # RobotConfig     —— TCP 标定
self._io_control = None        # IoControl       —— 数字 IO
self._robot_algorithm = None   # RobotAlgorithm  —— 正逆解
```

- 全部初始化为 `None`，语义是"**尚未连接**"。`open()` 成功后才被填充，`close()` 时全部清回 `None`。
- 因此所有使用子接口的方法都隐含一个前提：**必须先 `open()` 成功**（`poweron` 等方法还显式检查 `has_logined()` 并抛 `RuntimeError("未登录，请先 open()")`，见 5.1 节）。

---

## 4. 连接与断开：open / has_connected / has_logined / close

### 4.1 `open()` —— 完整流程详解（第 106–165 行）—— 重点

```python
def open(self, timeout_ms: Optional[int] = None) -> bool:
    """连接 RPC 服务并登录。返回是否成功。"""
```

这是全文件最长的流程方法，把官方示例 `__main__` 里的"连接→登录→取接口"套路**固化**成一步。整个流程分 7 个阶段：

**阶段 0：前置守卫（第 108–112 行）**

```python
if not _AUBO_OK:
    raise RuntimeError("未安装 pyaubo_sdk")
if self._client is not None:
    logger.warning("[arm] 已连接，先 close 再 open")
    return self.has_connected()
```

- 第二道 `_AUBO_OK` 检查（见 2.2 节）。
- 幂等保护：如果已经 open 过（`_client` 非空），不重复建连，只告警并返回当前连接状态。这是**防御性编程**——防止 GUI 反复调用 `open()` 造成句柄泄漏。

**阶段 1：创建客户端 + 设置 RPC 超时（第 114–115 行）**

```python
client = pyaubo_sdk.RpcClient()
client.setRequestTimeout(timeout_ms or ARM_CONFIG["rpc_timeout_ms"])
```

- 与官方示例 `robot_rpc_client.setRequestTimeout(1000)` 对应（`ARM_CONFIG["rpc_timeout_ms"]` = 1000ms）。
- RPC 超时 = **单次请求的最长等待时间**，网络抖动时能快速失败，避免 GUI 卡死。

**阶段 2：TCP 连接（第 116–123 行）**

```python
try:
    client.connect(self.ip, self.rpc_port)
except Exception as exc:
    logger.error("[arm] 连接 %s:%d 失败: %s", self.ip, self.rpc_port, exc)
    return False
if not client.hasConnected():
    logger.error("[arm] hasConnected()=False（IP/端口/网络）")
    return False
```

- 双层判断：先捕获 `connect()` 抛出的**异常**（IP 写错、端口不通、目标机未开机等），再查 `hasConnected()` 的**返回值**（SDK 内部握手状态）。异常 + 状态双保险，任何一层失败都返回 `False`。
- 与官方示例 `if robot_rpc_client.hasConnected():` 对应。

**阶段 3：登录（第 124–133 行）**

```python
try:
    client.login(self.username, self.password)
except Exception as exc:
    logger.error("[arm] 登录失败: %s", exc)
    client.disconnect()
    return False
if not client.hasLogined():
    logger.error("[arm] hasLogined()=False（账号密码错误？）")
    client.disconnect()
    return False
```

- 同样异常 + 状态双保险。注意失败路径上都调用了 `client.disconnect()` —— **失败的连接也要回收**，不留半开连接占用控制柜会话。
- 错误信息直接提示"账号密码错误？"，指向最常见的登录失败原因。

**阶段 4：获取机器人名（第 135–146 行）**

```python
self._client = client
try:
    names = client.getRobotNames()
    self._robot_name = names[0] if names else None
except Exception as exc:
    logger.warning("[arm] getRobotNames 失败: %s", exc)
if self._robot_name is None:
    logger.error("[arm] 未获取到机器人名字")
    client.logout()
    client.disconnect()
    self._client = None
    return False
```

- **这里才把 `client` 挂到 `self._client`**——前面失败时 `self._client` 始终保持 `None`，保证"失败 = 未连接"的不变量成立。
- `getRobotNames()[0]`：取第一个机器人名（单臂系统只有一个）。与官方示例 `robot_name = rpc_client.getRobotNames()[0]` 完全一致。
- 失败路径：`logout()` → `disconnect()` → `_client = None`，**完整回滚**，不留任何残迹。
- 注意这里用的是 `logger.warning`（名字获取失败不致命，后面还有 None 检查兜底）——分层级日志的典型用法。

**阶段 5：取接口并缓存 6 个子接口（第 148–155 行）**

```python
ri = client.getRobotInterface(self._robot_name)
self._robot_interface = ri
self._robot_manage = ri.getRobotManage()
self._motion_control = ri.getMotionControl()
self._robot_state = ri.getRobotState()
self._robot_config = ri.getRobotConfig()
self._io_control = ri.getIoControl()
self._robot_algorithm = ri.getRobotAlgorithm()
```

- `getRobotInterface(name)` 返回一个 `RobotInterface` 对象，它本身是**子接口工厂**：`getXxx()` 返回各个功能子接口。
- **一次性取齐 6 个子接口并缓存**是本类高性能的关键——之后每次运动/状态调用都不再走 `getRobotInterface` 链式查找，直接命中缓存字段。
- 若后续某次调用需要"当前执行 ID、运动剩余时间"等，也全部经由缓存后的 `_motion_control` 完成。

**阶段 6：应用速度比例与 TCP 偏移（第 157–162 行）**

```python
try:
    self._motion_control.setSpeedFraction(self.speed_fraction)
except Exception as exc:
    logger.warning("[arm] setSpeedFraction 失败: %s", exc)
self.apply_tcp_offset()
```

- `setSpeedFraction(0.3)`：把构造时定的安全速度比例（0.3）下发给控制柜。失败只 `warning` 不中断（速度比例不是致命配置，且上层可随时用 `set_speed_fraction` 重设）。
- `apply_tcp_offset()`：写入 TCP 偏移（基础 + 安装，详见第 7 节）。这一步**不在 try 里**——因为 TCP 标定错误会直接导致后续 movel/movec 走错坐标系，属于必须暴露的致命错误（`apply_tcp_offset` 内部失败会 `raise`）。

**阶段 7：成功收尾（第 164–165 行）**

```python
logger.info("[arm] 已连接并登录: %s (%s:%d)", self._robot_name, self.ip, self.rpc_port)
return True
```

**open() 的异常处理总结**：

| 失败点 | 处理方式 | 残留清理 |
|---|---|---|
| 未装 SDK | 抛 RuntimeError | — |
| 已连接 | 告警 + 返回现状 | — |
| connect 异常 / hasConnected=False | 记 error，返回 False | — |
| login 异常 / hasLogined=False | 记 error，返回 False | `disconnect()` |
| getRobotNames 失败或空 | 记 error，返回 False | `logout()` + `disconnect()` + `_client=None` |

> **为什么这样写**：让 `open()` 成为"全有或全无"（all-or-nothing）操作——要么返回 True 且所有句柄就绪，要么返回 False 且不留任何半连接状态。上层（GUI/命令行）只需 `if not arm.open(): return` 即可安全退出。

### 4.2 `has_connected` / `has_logined`（第 167–171 行）

```python
def has_connected(self) -> bool:
    return bool(self._client is not None and self._client.hasConnected())

def has_logined(self) -> bool:
    return bool(self._client is not None and self._client.hasLogined())
```

- 组合判断：**先看本地缓存句柄是否存在，再看 SDK 底层状态**。`bool(...)` 确保返回纯 `bool`（SDK 可能返回其他可空类型）。
- 用途：`has_logined()` 是电源管理等方法的登录前置检查；`has_connected()` 供 GUI 状态栏轮询显示。

### 4.3 `close()`（第 173–193 行）

```python
def close(self):
    """登出并断开连接。"""
    if self._client is not None:
        try:
            self._client.logout()
        except Exception as exc:  # pragma: no cover
            logger.debug("[arm] logout: %s", exc)
        try:
            self._client.disconnect()
        except Exception as exc:  # pragma: no cover
            logger.debug("[arm] disconnect: %s", exc)
    self._client = None
    ...  # 其余 7 个字段全部置 None
    self._robot_name = None
    logger.info("[arm] 已断开")
```

- 与 open 对称：先 `logout()`（登出控制柜会话）再 `disconnect()`（断开 TCP），顺序不能反——先断 TCP 再登出会导致控制柜侧会话悬挂。
- 每个调用都套 try/except 且只记 `debug`：**close 是"尽力而为"的清理**，即使登出/断开本身失败（网络已断等），也不能让清理流程抛异常打断上层。
- 最后**无条件把 8 个字段全部置 None**，保证"close 之后一切回到未连接状态"，与 3.3 节的初始不变量一致。之后可安全地再次 `open()`。
- ⚠️ **注意**：`close()` **不会**调用 `poweroff()`。断电是显式动作（防止误触发）；程序正常退出只登出断开，机械臂保持上电待机状态，符合"机器停、电不断"的安全惯例。

---

## 5. 电源管理：poweron / startup / poweroff / poweron_and_startup

### 5.1 单个电源动作（第 198–220 行）

```python
def poweron(self) -> bool:
    if not self.has_logined():
        raise RuntimeError("未登录，请先 open()")
    ret = self._robot_manage.poweron()
    logger.info("[arm] poweron ret=%s", ret)
    return ret == 0
```

`startup()`（第 206–212 行）、`poweroff()`（第 214–220 行）结构完全相同，只是换成 `startup()` / `poweroff()`。统一解读：

- **前置检查**：`has_logined()` 为假则抛 `RuntimeError("未登录，请先 open()")`——**快速失败**，防止未连接时调用 SDK 得到晦涩错误。
- **调用**：`self._robot_manage.poweron()`（对应官方 `example_startup.py` 的 `getRobotManage().poweron()`）。
- **返回**：`ret == 0` 转成 bool。**SDK 约定：返回 0 表示成功**，非 0 是错误码（本文件统一用"0 成功"约定，`_ret_text` 负责把非 0 码翻译成中文，见第 12 节）。
- 日志记录 ret 原始值，便于排查。

三个动作的语义（K5 控制柜状态机）：
- `poweron`：给伺服系统**上电**（电机得电，但抱闸未松，机械臂不会动）；
- `startup`：**启动（松刹车）**——抱闸释放，机械臂进入可运动状态；
- `poweroff`：**断电**——电机失电，抱闸抱死。

> 官方示例中 `poweron()` 返回 0 时打印 "The robot is requesting power-on!"——注意是"**请求**上电"，真实状态切换需要时间，这正是 `poweron_and_startup` 里轮询的原因。

### 5.2 `poweron_and_startup`（第 222–239 行）—— Running 轮询逻辑

```python
def poweron_and_startup(self, wait_running: bool = True,
                        timeout_s: float = 15.0) -> bool:
    """上电 + 启动（松刹车），可选等待进入 Running 模式。返回是否成功。"""
    if not self.poweron():
        return False
    if not self.startup():
        return False
    if not wait_running:
        return True
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        mode = self.get_robot_mode()
        if mode is not None and "Running" in str(mode):
            logger.info("[arm] 机械臂进入 Running 模式")
            return True
        time.sleep(0.5)
    logger.warning("[arm] 等待 Running 超时（当前模式: %s）", self.get_robot_mode())
    return False
```

**逐段解读**：

1. **串行前置**：`poweron()` 失败直接返回 False（短路），成功才 `startup()`——**上电是启动的前提**，顺序不能颠倒。
2. **跳过等待**：`wait_running=False` 时只发指令不等结果，立即返回 True（用于"只上电不管"的快速脚本）。
3. **Running 轮询**（核心）：`t0 = time.time()` 记开始时间，循环里每次：
   - 调 `get_robot_mode()` 读当前模式（内部已带 try/except，失败返回 None）；
   - **`"Running" in str(mode)`**：把模式枚举转字符串后做**子串匹配**。为什么要这样而不是直接比枚举？——不同 SDK 版本中 `RobotModeType` 枚举名可能有细微差异（如 `Running` / `ROBOT_RUNNING`），字符串子串匹配更鲁棒；
   - `mode is not None` 防呆：读模式失败（网络抖动）时不误判为成功；
   - 每轮 `time.sleep(0.5)`：500ms 轮询间隔，兼顾响应速度与 RPC 负载。
4. **超时保护**：总时长超过 `timeout_s`（默认 15s）→ `warning` 并返回 False。超时日志里带上**当前模式**，方便诊断卡在哪个状态（如 PowerOn 但没到 Running = 启动失败/急停未复位）。

**与官方示例对比**（`example_startup.py` 第 32–38 行）：

```python
while 1:
    robot_mode = ...getRobotModeType()
    if robot_mode == pyaubo_sdk.RobotModeType.Running:
        break
    time.sleep(1)
```

- 官方版本是**死循环**（`while 1`，永不超时）且用**枚举精确比较**。本文件做了两点改进：① 加了 `timeout_s` 超时保护，避免控制柜卡死在非 Running 状态时程序永久挂起；② 用字符串子串匹配替代枚举比较，兼容 SDK 版本差异；③ 轮询间隔从 1s 缩短到 0.5s，加快就绪检测。

---

## 6. 状态读取：模式 / 安全 / 位形 / 汇总 / 速度

这一组方法（第 244–314 行）模式高度统一：**try 调 SDK → 成功返回数据 → 异常记 warning 返回 None/安全默认**。`None` 的语义是"读取失败"，上层（GUI 显示"--"、诊断脚本报错）据此区分"没读到"与"读到异常值"。

### 6.1 模式类（第 244–257 行）

```python
def get_robot_mode(self):
    """机器人模式类型（RobotModeType，如 PowerOff/PowerOn/Running/Error...）。"""
    try:
        return self._robot_state.getRobotModeType()
    except Exception as exc:
        logger.warning("[arm] getRobotModeType: %s", exc)
        return None
```

- `get_robot_mode`：机器人主状态机（PowerOff → PowerOn → Running → Error...），`poweron_and_startup` 轮询的就是它。
- `get_safety_mode`：安全模式（如 Normal/Reduced/ProtectiveStop/EmergencyStop...），排查急停、保护性停止时用。
- 都返回 SDK 枚举对象（可直接 `str()` 显示），异常返回 `None`。

### 6.2 状态类（第 259–272 行）

```python
def is_steady(self) -> Optional[bool]:
    """机器人是否已经停下来。"""
    ...
def is_within_safety_limits(self) -> Optional[bool]:
    ...
```

- `is_steady`：机械臂是否**完全停稳**（速度≈0）。用途：伺服运动收尾判定（官方 `example_servoj2.py` 的 `waitServoJointComplete` 第二步就是 `while not isSteady()`）、抓取动作前确认静止。
- `is_within_safety_limits`：当前位形是否在安全限位内（关节限位/软件限位）。用途：运动前安全检查、诊断。
- 返回 `Optional[bool]`：成功 `True/False`，失败 `None`。

### 6.3 位形类（第 274–288 行）

```python
def get_joint_positions(self) -> Optional[List[float]]:
    """当前关节角（弧度，6 维）。"""
    try:
        return list(self._robot_state.getJointPositions())
    ...
def get_tcp_pose(self) -> Optional[List[float]]:
    """当前 TCP 位姿 [x,y,z,rx,ry,rz]（米/弧度，含 TCP 偏移）。"""
    try:
        return list(self._robot_state.getTcpPose())
    ...
```

- **关节角**：6 维弧度列表（对应 `arm_config.DOF = 6`）。上层若想显示成度，用 `_rad2deg_list` 转。
- **TCP 位姿**：`[x,y,z,rx,ry,rz]`，位置米、姿态弧度，且**已包含 `setTcpOffset` 写入的偏移**（即返回的是"灵巧手 TCP"的位姿，而非法兰盘位姿——因为 `apply_tcp_offset` 已经把安装偏移写进控制柜）。
- `list(...)` 拷贝返回：防止外部修改污染 SDK 内部对象（与构造时的防御性拷贝同一思路）。

### 6.4 `get_state_summary`（第 290–300 行）

```python
def get_state_summary(self) -> dict:
    """状态汇总（GUI/诊断显示用）。"""
    return {
        "robot_mode": str(self.get_robot_mode()),
        "safety_mode": str(self.get_safety_mode()),
        "steady": self.is_steady(),
        "within_safety": self.is_within_safety_limits(),
        "joint_positions_rad": self.get_joint_positions(),
        "tcp_pose": self.get_tcp_pose(),
        "speed_fraction": self.get_speed_fraction(),
    }
```

- **一次性打包 7 项状态**成字典，供 GUI 状态面板、`diag_arm.py`、`quick_check` 直接展示。
- 枚举都先 `str()` 转字符串（方便 JSON 序列化/显示）；失败项自然携带 `None`，上层可分别处理。
- 这是典型的"**面向消费端聚合**"方法——把多个细粒度 getter 组合成一次可展示的快照。

### 6.5 速度（第 302–314 行）

```python
def get_speed_fraction(self) -> Optional[float]:
    try:
        return self._motion_control.getSpeedFraction()
    except Exception as exc:
        logger.warning("[arm] getSpeedFraction: %s", exc)
        return None

def set_speed_fraction(self, fraction: float):
    """设置全局速度比例 0~1。"""
    f = max(0.0, min(1.0, float(fraction)))
    self._motion_control.setSpeedFraction(f)
    self.speed_fraction = f
    logger.info("[arm] speed fraction = %.2f", f)
```

- `get_speed_fraction`：读回当前比例（可能与控制柜实际值不同步，读回为准）。
- `set_speed_fraction`：
  - **输入钳制**：`max(0.0, min(1.0, float(fraction)))` —— 把任意输入（含负数、>1、字符串）钳制到 `[0, 1]` 合法区间，防止用户误传 2.0 导致机械臂超速；
  - 下发后**同步更新本地 `self.speed_fraction`**（保持"本地值 = 实际下发值"的一致性，供 `get_state_summary` 等使用）；
  - 注意：运行中改速度比例对**已下发但未执行完**的运动不一定立即生效（取决于控制柜实现），主要影响后续指令。

---

## 7. TCP 坐标联动：apply_tcp_offset

### 7.1 概念：法兰 TCP vs 灵巧手 TCP（为什么需要"坐标联动"）

- 机械臂的 `movel`/`movec` 位姿是 **TCP（工具中心点）坐标**。默认（`tcp_offset` 全 0）时，TCP = **法兰盘中心**——指令里写 `[0.55, 0, 0.4, ...]` 指的是"法兰盘中心到该位置"。
- 但本系统在法兰盘下方挂了 **RY-H1(16) 灵巧手**，真正干活（抓取/模仿）的是**灵巧手掌心**。灵巧手相对法兰有一个固定的**安装偏移**（平移 + 旋转，如"法兰正下方 0.15m、绕 X 轴转 180°"，即 `ARM_CONFIG["hand_mount_offset"]`）。
- **如果不处理这个偏移**：视觉系统算出的"目标位置"（以灵巧手为基准）直接发给 movel，机械臂会把**法兰盘**移到那里，灵巧手整体低了 0.15m 且朝向错误——永远抓不准。
- **解决方案（TCP 坐标联动）**：把"基础 tcp_offset + 灵巧手安装偏移"相加，通过 `setTcpOffset` 写进控制柜。此后控制柜内部做坐标变换，**movel/movec 的位姿直接以灵巧手 TCP 为基准**——视觉算出的坐标可以原样下发，无需人工换算。

### 7.2 `apply_tcp_offset` 实现（第 319–340 行）—— 重点

```python
def apply_tcp_offset(self, hand_mount_offset: Optional[List[float]] = None):
    """把 TCP 偏移写入机械臂（setTcpOffset）。

    若传入 hand_mount_offset（灵巧手安装偏移），则最终 TCP 偏移 = 基础偏移 + 安装偏移
    （平移相加、旋转相加），使 moveLine/moveCircle 的位姿以"灵巧手 TCP"为基准。
    """
    if hand_mount_offset is not None:
        self._hand_mount_offset = list(hand_mount_offset)
    if self._hand_mount_offset is None:
        final = list(self._tcp_offset)
    else:
        final = [
            self._tcp_offset[i] + self._hand_mount_offset[i]
            for i in range(6)
        ]
    try:
        self._robot_config.setTcpOffset(final)
        logger.info("[arm] TCP offset = %s (hand mount %s)",
                    final, self._hand_mount_offset)
    except Exception as exc:
        logger.error("[arm] setTcpOffset 失败: %s", exc)
        raise
```

**逐段解读**：

1. **参数更新（第 325–326 行）**：显式传入 `hand_mount_offset` 时更新内部值（支持"安装灵巧手后重新标定"），否则沿用构造时/上次设置的值。
2. **合成最终偏移（第 327–333 行）**：
   - 无安装偏移 → 直接用基础 `_tcp_offset`（纯法兰工具偏移场景）；
   - 有安装偏移 → **逐元素相加**：`final[i] = 基础[i] + 安装[i]`，`i ∈ [0,6)`。前 3 维是 **xyz 平移相加**，后 3 维是 **rx,ry,rz 旋转角相加**（欧拉角近似叠加；安装偏移通常只有一个轴的大角度如 180°，此近似在工程上足够）。
   - **为什么旋转也直接加**：`setTcpOffset` 的旋转部分就是 TCP 相对法兰的姿态欧拉角。基础偏移全 0 时，最终偏移 = 安装偏移本身，控制柜据此把 TCP 系旋转到灵巧手姿态。
3. **下发（第 334–340 行）**：
   - `setTcpOffset(final)` 写入控制柜（对应官方 `example_movel.py` 的 `getRobotConfig().setTcpOffset(tcp_offset)`）；
   - **失败即 raise**（不吞异常）——TCP 标定是坐标正确性的根基，静默失败会让后续所有 movel/movec 走错坐标系且极难排查，所以必须让错误冒泡到上层（`open()` 阶段 6 也因此不在 try 里包它）。

**坐标联动后的效果链**：

```
视觉系统算出目标点（以灵巧手为基准）
        │ 直接作为 movel/movec 的 pose
        ▼
控制柜（已 setTcpOffset = 基础+安装偏移）
        │ 内部换算成"法兰盘系"目标
        ▼
K5 机械臂运动到目标 → 灵巧手掌心正好到达视觉目标点
```

### 7.3 `get_hand_mount_offset`（第 342–343 行）

```python
def get_hand_mount_offset(self) -> Optional[List[float]]:
    return list(self._hand_mount_offset) if self._hand_mount_offset else None
```

- 只读访问当前安装偏移（拷贝返回），供 GUI 显示/诊断确认联动是否启用。未启用（None）时返回 None。

---

## 8. 运动控制：_wait_arrival / movej / movel / movec / move_home / stop_move / servo

### 8.1 统一返回值约定

所有运动方法返回 `Tuple[int, Optional[str]]` = `(ret, err_msg)`：

| ret | err_msg | 含义 |
|---|---|---|
| `0` | `None` | 指令下发成功（且 block=True 时运动已完成） |
| 非 0 | 中文/字符串 | SDK 错误码（经 `_ret_text` 翻译）或参数校验失败信息 |
| `-1` | 字符串 | 异常（SDK 抛异常）或等待超时 |

上层只需 `ret, msg = arm.movej(...)`；`ret != 0` 时把 `msg` 展示给用户即可，无需关心底层错误码（翻译见第 12 节 `_ret_text`）。

### 8.2 `_wait_arrival` —— 阻塞等待实现（第 348–380 行）—— 核心

```python
def _wait_arrival(self, timeout_s: float = 30.0) -> int:
    """阻塞等待当前运动完成（官方 wait_arrival 逻辑 + 超时保护）。"""
    mc = self._motion_control
    t0 = time.time()
    exec_id = -1
    try:
        exec_id = mc.getExecId()
    except Exception:
        pass
    # 等待开始运动
    cnt = 0
    while exec_id == -1:
        cnt += 1
        if cnt > 5:
            return -1
        if time.time() - t0 > timeout_s:
            return -1
        time.sleep(0.05)
        try:
            exec_id = mc.getExecId()
        except Exception:
            exec_id = -1
    # 等待运动完成
    while True:
        if time.time() - t0 > timeout_s:
            logger.warning("[arm] 等待运动完成超时")
            return -1
        try:
            if mc.getExecId() == -1:
                return 0
        except Exception:
            pass
        time.sleep(0.05)
```

**核心语义：`getExecId()` 返回"当前正在执行的运动指令 ID"，`-1` 表示"当前没有运动在执行"**。

- 因此一次"等待运动完成"被拆成两个阶段：
  - **阶段 A（等待开始）**：`exec_id == -1` 说明运动还没被控制柜接住（指令刚下发、还没开始执行），持续轮询直到 `exec_id` 变成**非 -1**（运动开始）；
  - **阶段 B（等待完成）**：`exec_id` 非 -1 说明运动进行中，持续轮询直到它**回到 -1**（运动结束）。

**逐行细节**：

1. **初始读取**（第 352–356 行）：先读一次 `exec_id`，异常则保持 -1（按"没开始"处理，进入阶段 A 重试）。`except Exception: pass` 静默——这里读失败不代表运动失败，稍后还会重读。
2. **阶段 A**（第 358–369 行）：
   - `cnt > 5` 快速失败：最多重读 **5 次**（每次 50ms，约 250–300ms），与官方 `wait_arrival` 的 `max_retry_count = 5` 完全一致。超过说明运动**根本没开始**（指令被拒/控制柜忙），返回 -1；
   - `time.time() - t0 > timeout_s`：整体超时兜底（阶段 A + 阶段 B 共享同一个 `t0` 总预算，防止两阶段各算各的超时导致总时长失控）；
   - 每次 50ms 轮询 + try/except 重读（失败按 -1 继续等，不退出）。
3. **阶段 B**（第 371–380 行）：
   - 先查总超时（此时若超时会打 `warning("等待运动完成超时")`）；
   - `getExecId() == -1` → 运动完成，返回 `0`；
   - 读取异常 `pass`（视为"还没完成"，继续等）；
   - 50ms 轮询。

**与官方 `wait_arrival`（example_movej.py 第 22–41 行）对比**：

| 点 | 官方示例 | 本文件 |
|---|---|---|
| 阶段 A 快速失败 | `cnt > max_retry_count` 返回 -1 | 相同（cnt > 5） |
| 阶段 B | 死循环直到 -1 | 相同，但加了 `timeout_s` 总超时保护 |
| 超时保护 | **无**（可能永久阻塞） | **有**（30s 默认，超时返回 -1） |
| 读取异常 | 无处理（直接抛） | try/except 兜底（继续轮询） |

> 官方示例在"运动永远不结束"（如目标不可达但控制柜不报错、RPC 断连后 getExecId 恒返回 -1 之前）时会永久卡死；本文件的两处超时检查（阶段 A 开头、阶段 B 开头）是**防挂死的关键改进**——GUI 场景尤其重要，一个卡死的阻塞调用会冻住整个界面。

### 8.3 `movej` —— 关节运动（第 382–405 行）

```python
def movej(self, joint_rad: List[float],
          speed_deg: Optional[float] = None,
          acc_deg: Optional[float] = None,
          block: bool = True, timeout_s: float = 30.0) -> Tuple[int, Optional[str]]:
    """关节运动（moveJoint）。joint_rad: 6 维弧度。返回 (ret, err_msg)。"""
    if len(joint_rad) != DOF:
        return -1, f"需要 {DOF} 个关节角"
    spd = math.radians(speed_deg if speed_deg is not None
                       else ARM_CONFIG["joint_speed"])
    acc = math.radians(acc_deg if acc_deg is not None
                       else ARM_CONFIG["joint_acc"])
    try:
        ret = self._motion_control.moveJoint(
            list(joint_rad), spd, acc,
            ARM_CONFIG["blend_radius"], 0)
    except Exception as exc:
        logger.error("[arm] moveJoint 异常: %s", exc)
        return -1, str(exc)
    if ret != 0:
        return ret, self._ret_text(ret)
    if block:
        wr = self._wait_arrival(timeout_s)
        return (0, None) if wr == 0 else (-1, f"等待完成超时({timeout_s}s)")
    return 0, None
```

**参数**：

| 参数 | 单位 | 默认 | 说明 |
|---|---|---|---|
| `joint_rad` | 弧度 | 必填 | 6 维目标关节角 |
| `speed_deg` | **度/秒** | `ARM_CONFIG["joint_speed"]` = 40 | 关节速度上限 |
| `acc_deg` | **度/秒²** | `ARM_CONFIG["joint_acc"]` = 30 | 关节加速度上限 |
| `block` | — | `True` | True 阻塞到运动完成；False 只下发立即返回 |
| `timeout_s` | 秒 | 30 | block 模式下的等待超时 |

**逐段解读**：

1. **维度校验**（第 387–388 行）：`len(joint_rad) != DOF(6)` → 返回 `(-1, "需要 6 个关节角")`。把参数错误挡在 SDK 调用之前，错误信息对用户友好。
2. **单位换算（重点）**（第 389–392 行）：
   - `math.radians(...)`：**把"度"换算成"弧度"**。SDK 的 `moveJoint(q, vel, acc, ...)` 要求 vel/acc 单位是 **rad/s、rad/s²**（见 `arm_config.py` docstring 第 12 行），但业务层习惯用"度/秒"（40°/s 比 0.698 rad/s 直观得多）。**这就是封装层存在的意义之一**——对外暴露人友好的单位，对内自动换算。
   - 默认值来自 `ARM_CONFIG`：40°/s 速度、30°/s² 加速度（保守起步值，官方示例是 80°/s、60°/s²）。
3. **调用 SDK**（第 393–399 行）：
   - `moveJoint(list(joint_rad), spd, acc, ARM_CONFIG["blend_radius"], 0)`：5 个参数 = 目标关节角、速度、加速度、**过渡半径**（`blend_radius` = 0 表示精确到达、不圆滑衔接）、最后一个 `0` 是 SDK 的固定控制参数（官方示例同样传 `0`，见 `example_movej.py` 第 67 行 `moveJoint(q1, 80*(pi/180), 60*(pi/180), 0, 0)`）；
   - `list(...)` 拷贝传入，防外部篡改；
   - 异常 → 记 error，返回 `(-1, str(exc))`（把异常消息作为 err_msg 透出）。
4. **错误码翻译**（第 400–401 行）：`ret != 0` → `(ret, self._ret_text(ret))`，把 SDK 错误码转中文（第 12 节）。
5. **阻塞模式**（第 402–404 行）：`block=True` → `_wait_arrival(timeout_s)`；等待成功 `(0, None)`，超时 `(-1, "等待完成超时(30s)")`。**注意**：即使 `moveJoint` 返回 0，阻塞模式下也要等"运动真正完成"才算成功——0 只代表"指令被接收"。
6. **非阻塞模式**（第 405 行）：立即返回 `(0, None)`，运动在后台执行（可用于连续路点流水线，配合 `_wait_arrival` 或 `is_steady` 自行控制节奏）。

### 8.4 `movel` —— 直线运动（第 407–428 行）

```python
def movel(self, pose: List[float],
          speed: Optional[float] = None,
          acc: Optional[float] = None,
          block: bool = True, timeout_s: float = 30.0) -> Tuple[int, Optional[str]]:
    """直线运动（moveLine）。pose: [x,y,z,rx,ry,rz]，米/弧度（TCP 系）。"""
    if len(pose) != 6:
        return -1, "pose 需要 [x,y,z,rx,ry,rz]"
    spd = speed if speed is not None else ARM_CONFIG["line_speed"]
    acc = acc if acc is not None else ARM_CONFIG["line_acc"]
    try:
        ret = self._motion_control.moveLine(
            list(pose), spd, acc,
            ARM_CONFIG["blend_radius"], 0)
    except Exception as exc:
        logger.error("[arm] moveLine 异常: %s", exc)
        return -1, str(exc)
    if ret != 0:
        return ret, self._ret_text(ret)
    if block:
        wr = self._wait_arrival(timeout_s)
        return (0, None) if wr == 0 else (-1, f"等待完成超时({timeout_s}s)")
    return 0, None
```

**与 movej 的差异点**：

| 差异 | movej | movel |
|---|---|---|
| 目标描述 | 6 维关节角（弧度） | 6 维位姿 `[x,y,z,rx,ry,rz]`（米/弧度） |
| 速度/加速度单位 | 度/秒（内部转弧度） | **米/秒、米/秒²**（笛卡尔单位，直接传，无需换算） |
| 坐标系 | 关节空间（无坐标系概念） | **TCP 系**（受 `apply_tcp_offset` 影响，见第 7 节） |
| SDK 调用 | `moveJoint(q, vel, acc, blend, 0)` | `moveLine(pose, vel, acc, blend, 0)` |

- 维度校验消息直接提示正确格式 `"pose 需要 [x,y,z,rx,ry,rz]"`。
- 速度/加速度默认值：`line_speed = 0.4` m/s、`line_acc = 0.3` m/s²（`ARM_CONFIG`）。
- **TCP 坐标联动**：这里传的 `pose` 是"灵巧手 TCP 系"目标（前提是 `open()` 阶段 6 已 `apply_tcp_offset`）——视觉系统算出的抓取点可以直接用，这就是 7.1 节效果的落地。
- 阻塞/错误码逻辑与 movej 完全一致（复用同一套模式）。

### 8.5 `movec` —— 圆弧运动（第 430–445 行）

```python
def movec(self, mid_pose: List[float], end_pose: List[float],
          speed: Optional[float] = None,
          acc: Optional[float] = None) -> Tuple[int, Optional[str]]:
    """圆弧运动（moveCircle）：经中间点 mid_pose 到 end_pose（位姿，TCP 系）。"""
    spd = speed if speed is not None else ARM_CONFIG["line_speed"]
    acc = acc if acc is not None else ARM_CONFIG["line_acc"]
    try:
        ret = self._motion_control.moveCircle(
            list(mid_pose), list(end_pose), spd, acc,
            ARM_CONFIG["blend_radius"], 0)
    except Exception as exc:
        logger.error("[arm] moveCircle 异常: %s", exc)
        return -1, str(exc)
    if ret != 0:
        return ret, self._ret_text(ret)
    return 0, None
```

- **圆弧三点**：起点 = 当前位姿，中间点 = `mid_pose`，终点 = `end_pose`（三点定圆）。`mid_pose`/`end_pose` 均为 TCP 系位姿。
- 对应官方 `example_movec.py`：`moveCircle(waypoint2, waypoint3, 180*(pi/180), 1000000*(pi/180), 0, 0)`——注意官方示例里速度和加速度的单位是**弧度制**（`180*(pi/180)` 即 3.14 rad/s），本文件对 movec 直接使用 `line_speed`（m/s）/`line_acc`（m/s²），与 movel 的笛卡尔约定保持一致。
- **没有 `block` 参数**（与 movej/movel 不同）：movec 是"只下发、不等待"的语义。设计取舍：圆弧运动多用于连续轨迹段，调用方需要自行控制节奏；如需阻塞，可后续手动调 `_wait_arrival`（本类内部方法，外部可通过 `movej`/`movel` 的 block 模式或 `is_steady()` 轮询实现等价效果）。
- 错误码翻译逻辑与 movej/movel 相同。

### 8.6 `move_home`（第 447–450 行）

```python
def move_home(self, block: bool = True) -> Tuple[int, Optional[str]]:
    """回到初始关节角（示例 q 起点：J1=0, J2=-15°, J3=100°, J4=25°, J5=90°, J6=0）。"""
    home = [0.0, -15.0, 100.0, 25.0, 90.0, 0.0]
    return self.movej(_deg2rad_list(home), block=block)
```

- 定义**系统默认 home 点**：`[0°, -15°, 100°, 25°, 90°, 0°]`——与官方示例的起始点 `q1` 完全一致（`example_movej.py` 第 47–49 行、`example_movel.py` 第 47–48 行）。
- 用 `_deg2rad_list` 把"度"写法转成弧度后交给 `movej`——**示例代码风格 + 人类可读的度数书写**，一举两得。
- `block` 透传给 movej（默认阻塞）。

### 8.7 `stop_move`（第 452–458 行）

```python
def stop_move(self) -> int:
    """停止运动（stopMove）。"""
    try:
        return self._motion_control.stopMove()
    except Exception as exc:
        logger.warning("[arm] stopMove: %s", exc)
        return -1
```

- 紧急停止当前运动（对应 SDK `stopMove`；官方示例见 `example_motion_control.py` 的 stop 演示）。
- 返回 SDK ret（0 = 成功）；异常返回 -1 并记 warning（停止失败不致命，机械臂自身还有安全逻辑兜底）。
- **GUI 里的"急停"按钮应直接调它**——比 `poweroff` 轻量、比等待运动自然结束快。

### 8.8 `servo_mode_enable`（第 461–478 行）—— 视觉跟随模式开关

```python
def servo_mode_enable(self, enable: bool, mode: int = 1) -> int:
    """开关 servo 模式（mode: 1=旧接口等价, 2=新接口, 5=路点必达）。"""
    mc = self._motion_control
    try:
        if enable:
            mc.setServoModeSelect(mode)
            i = 0
            while mc.getServoModeSelect() != mode:
                i += 1
                if i > 20:
                    return -1
                time.sleep(0.007)
        else:
            mc.setServoModeSelect(0)
        return 0
    except Exception as exc:
        logger.error("[arm] servo mode: %s", exc)
        return -1
```

**背景**：`servoJoint`（8.9 节）只能在 **servo 模式**下工作。servo 模式由 `setServoModeSelect(mode)` 开启（`mode=0` 关闭）。本方法就是模式开关。

**mode 参数语义**（来自官方 `example_servoj2.py` docstring 第 7–11 行）：

| mode | 含义 | 特点 |
|---|---|---|
| `1` | 新接口，等价旧 `setServoMode` | 截断式：更新路点后**不保证经过**上一个路点（适合高速连续跟随） |
| `2` | 新接口 | 非截断，跟踪更平滑 |
| `5` | 新接口 | **路点必达式**：每个路点必须到达（适合轨迹精度要求高的场景） |

**逐段解读**：

1. **开启分支**（第 465–472 行）：`setServoModeSelect(mode)` 下发开启请求后，**轮询 `getServoModeSelect()` 直到确认模式生效**（最多 20 次 × 7ms ≈ 140ms，超限返回 -1）。为什么轮询？——模式切换是异步生效的，不确认就立刻发 `servoJoint` 可能被拒绝。这与官方 `switch_servoj_mode`（`example_servoj2.py` 第 69–82 行，同样 `i > 20` + `sleep(0.007)`）逐行对应。
2. **关闭分支**（第 473–474 行）：`setServoModeSelect(0)` 直接关闭（关闭无需轮询确认）。
3. **异常**：任何 SDK 异常 → error 日志 + 返回 -1。

**典型使用模式**（视觉跟随）：

```python
arm.servo_mode_enable(True, mode=1)     # 1. 开 servo 模式
while True:                              # 2. 高频循环（5ms 节拍）
    q = 视觉系统给出的目标关节角
    ret = arm.servo_joint(q)             #    下发一个目标点
    if ret != 0: break
arm.servo_mode_enable(False)             # 3. 关 servo 模式
```

### 8.9 `servo_joint`（第 480–489 行）—— 视觉跟随核心下发

```python
def servo_joint(self, joint_rad: List[float],
                t: float = 0.02, lookahead: float = 0.1,
                gain: float = 200) -> int:
    """关节伺服下发一个目标点（servoJoint），5ms 节拍连续调用可实现实时跟随。"""
    try:
        return self._motion_control.servoJoint(
            list(joint_rad), 0.1, 0.2, t, lookahead, gain)
    except Exception as exc:
        logger.error("[arm] servoJoint: %s", exc)
        return -1
```

**参数**（对应官方 `example_servoj2.py` 第 185 行 `mc.servoJoint(q, 0.1, 0.2, t, 0.1, 200)`）：

| 参数 | 值/默认 | 含义 |
|---|---|---|
| `joint_rad` | 必填 | 目标关节角（6 维弧度） |
| 第 2 个（固定 0.1） | 0.1 | 速度上限（rad/s） |
| 第 3 个（固定 0.2） | 0.2 | 加速度上限（rad/s²） |
| `t` | 0.02s | 控制周期（与官方一致） |
| `lookahead` | 0.1s | 前瞻时间（平滑滤波窗口） |
| `gain` | 200 | 伺服增益 |

- **调用方式**：每次调用下发**一个**目标点；在 **5ms 节拍**（官方注释"目标点下发时间间隔5ms"）下连续调用，机械臂就会实时追踪一串目标点——这就是"视觉跟随"的底层机制（视觉推理出轨迹 → 逐点喂给 servoJoint → 机械臂平滑跟随）。
- **返回值语义（重要）**：SDK 返回 `0` 成功；返回 **`2` = 缓冲区满（queue full）**——官方示例遇到 2 会 `sleep(0.005)` 后**重发同一目标点**直到成功（`example_servoj2.py` 第 186–189 行）。本方法**不自动重试**，把 `2` 原样返回给调用方自行处理（保持封装简单；调用方循环里 `if ret == 2: time.sleep(0.005); continue` 即可）。
- 异常 → error 日志 + 返回 -1。

> ⚠️ **安全提示**：servo 模式下机械臂按"最后一组参数"持续运动，**视觉线程崩溃时一定要在 finally 里 `servo_mode_enable(False)` + `stop_move()`**，否则机械臂可能继续沿最后轨迹运动。

---

## 9. 示教：freedrive

```python
def freedrive(self, enable: bool, duration_s: Optional[float] = None) -> bool:
    """拖拽示教：enable=True 进入自由驱动（可手动拖拽），False 退出。
    duration_s 非空时自动等待该秒数后退出。"""
    try:
        if enable:
            try:
                self._client.getRuntimeMachine().start()
            except Exception:
                pass
            self._robot_manage.freedrive(True)
            if duration_s is not None:
                time.sleep(duration_s)
                self._robot_manage.freedrive(False)
            return True
        self._robot_manage.freedrive(False)
        return True
    except Exception as exc:
        logger.error("[arm] freedrive: %s", exc)
        return False
```

**逐段解读**：

1. **开启分支**（第 498–507 行）：
   - **先 `getRuntimeMachine().start()`**：启动"运行时机器"。这是官方 `example_freedrive.py` 第 22 行的固定前置步骤（`cli.getRuntimeMachine().start()`）——某些 SDK 版本下不启动运行时机器，freedrive 请求会失败。包在 try/except 里静默（部分版本/固件不需要这步，失败不致命，真正能否示教由 `freedrive(True)` 的返回决定）；
   - `_robot_manage.freedrive(True)`：进入自由驱动模式——**伺服跟随人手拖拽**（抱闸释放 + 力矩补偿），人工把机械臂摆到目标姿态；
   - `duration_s` 非空：**阻塞等待该秒数后自动退出**（`freedrive(False)`）。这是对官方示例"sleep(25) 后退出"的封装（`example_freedrive.py` 第 25–27 行）。
2. **关闭分支**（第 508 行）：`freedrive(False)` 直接退出示教。
3. **异常**：error 日志 + 返回 False。

**典型用法**：

```python
arm.freedrive(True)          # 进入拖拽示教（不自动退出）
# ... 人工把机械臂摆到目标位姿 ...
arm.freedrive(False)         # 退出，读取当前关节角作为示教点
q = arm.get_joint_positions()   # 记录示教点
```

> GUI 场景建议用 `duration_s=None` + 按钮控制进出（阻塞 sleep 会卡 GUI，见第 15 节）；命令行脚本可用 `duration_s=25` 一条龙完成"进入→等待→退出"。

---

## 10. IO 控制

IO 子接口（`IoControl`）对应官方 `example_io.py`。全部方法遵循"try → 成功返回数据 / 异常记日志返回 None 或 -1"的统一模式。

### 10.1 标准数字输入（第 517–524 行）

```python
def get_standard_digital_inputs(self) -> Optional[List[int]]:
    """标准数字输入值列表。"""
    try:
        n = self._io_control.getStandardDigitalInputNum()
        return [self._io_control.getStandardDigitalInput(i) for i in range(n)]
    except Exception as exc:
        logger.warning("[arm] digital inputs: %s", exc)
        return None
```

- 先查**输入数量** `getStandardDigitalInputNum()`，再逐个 `getStandardDigitalInput(i)` 读值（0/1），返回**完整列表**。
- 与官方 `example_io.py` 第 42/70 行对应（`getStandardDigitalInputNum()` + 循环 `getStandardDigitalInput(i)`）。
- 用途：读外部传感器（光电/接近开关/按钮），例如"工件到位信号"。

### 10.2 标准数字输出（第 526–540 行）

```python
def get_standard_digital_outputs(self) -> Optional[List[int]]:
    try:
        n = self._io_control.getStandardDigitalOutputNum()
        return [self._io_control.getStandardDigitalOutput(i) for i in range(n)]
    except Exception as exc:
        logger.warning("[arm] digital outputs: %s", exc)
        return None

def set_standard_digital_output(self, index: int, value: bool) -> int:
    """设置标准数字输出。"""
    try:
        return self._io_control.setStandardDigitalOutput(int(index), bool(value))
    except Exception as exc:
        logger.error("[arm] set std DO: %s", exc)
        return -1
```

- 读：与 10.1 同构（`getStandardDigitalOutputNum` + 逐个 `getStandardDigitalOutput`）。
- 写：`setStandardDigitalOutput(int(index), bool(value))`——**显式 `int()`/`bool()` 强转**，防止调用方传入字符串 `"1"` 或整数 `1` 导致 SDK 类型错误。返回 SDK ret（0 = 成功），异常 -1。
- 用途：控制外部继电器/指示灯/气路电磁阀。

### 10.3 工具端 IO（第 542–555 行）

```python
def get_tool_digital_input(self, index: int = 1) -> Optional[int]:
    try:
        return self._io_control.getToolDigitalInput(int(index))
    except Exception as exc:
        logger.warning("[arm] tool DI: %s", exc)
        return None

def set_tool_digital_output(self, index: int, value: bool) -> int:
    """设置工具端数字输出（如控制末端夹爪/灵巧手供电信号）。"""
    try:
        return self._io_control.setToolDigitalOutput(int(index), bool(value))
    except Exception as exc:
        logger.error("[arm] set tool DO: %s", exc)
        return -1
```

- **工具端 = 法兰盘/末端执行器上的 IO**（经工具端连接器引出）。
- `get_tool_digital_input`：默认读第 1 路工具输入（`index=1`）。
- `set_tool_digital_output`：写工具端输出——docstring 点明本系统的用途：**控制末端夹爪/灵巧手供电信号**（例如先给灵巧手上电再开始手势，或触发夹爪开合）。对应官方 `example_io.py` 第 139 行 `setToolDigitalOutput(3, output)`。
- 同样带 `int()`/`bool()` 强转。

---

## 11. 正逆解：forward_kinematics / inverse_kinematics

```python
def forward_kinematics(self, joint_rad: List[float]) -> Tuple[Optional[List[float]], int]:
    """正解：关节角 -> TCP 位姿。返回 (pose, ret)。"""
    try:
        res = self._robot_algorithm.forwardKinematics(list(joint_rad))
        return list(res[0]), res[1]
    except Exception as exc:
        logger.error("[arm] forwardKinematics: %s", exc)
        return None, -1

def inverse_kinematics(self, ref_joint_rad: List[float],
                       target_pose: List[float]) -> Tuple[Optional[List[float]], int]:
    """逆解：位姿 -> 关节角（以 ref_joint_rad 为参考初值）。返回 (q, ret)。"""
    try:
        res = self._robot_algorithm.inverseKinematics(
            list(ref_joint_rad), list(target_pose))
        return list(res[0]), res[1]
    except Exception as exc:
        logger.error("[arm] inverseKinematics: %s", exc)
        return None, -1
```

**正解 `forwardKinematics(q)`**（对应官方 `example_algorithm.py` 第 44 行）：
- 输入 6 维关节角，输出 **TCP 位姿**（`res[0]`，注意：返回的位姿是**当前 TCP 标定下**的位姿，受 `setTcpOffset` 影响）。
- 返回值约定 `(pose, ret)`：`res` 是 SDK 返回的元组/对象，`res[0]` 是位姿列表、`res[1]` 是返回码（0 = 成功）。**成功返回 `(list(res[0]), res[1])`，异常返回 `(None, -1)`**。
- 用途：视觉系统需要知道"当前关节角对应的手在哪"时。

**逆解 `inverseKinematics(ref_q, pose)`**（对应官方 `example_algorithm.py` 第 32 行、`example_servo_cartesian.py` 第 79 行）：
- 输入**参考关节角**（作为初值/构型选择依据）+ **目标 TCP 位姿**，输出关节角。
- **为什么必须给参考关节角**：六轴机械臂逆解**多解**（同一 TCP 位姿对应多组关节角，如"肘上/肘下"两种构型）。以当前关节角为参考，SDK 会返回**最接近当前构型**的解，避免机械臂大幅翻转（抖动/碰撞风险）。
- 经典用法：视觉给出目标位姿 → 用当前关节角做参考逆解 → 得到目标关节角 → `movej` 过去。

> 📌 **进阶提示**：SDK 还提供 `inverseKinematics2`（按参考构型选同构型最近解，官方 `example_stable_ik.py` 专门演示了普通逆解 vs 稳定逆解的区别）。本文件只封装了普通版 `inverseKinematics`；若视觉模仿场景出现"翻转解"问题，可参考 `example_stable_ik.py` 扩展。

**两方法的共同点**：`list(...)` 拷贝保护、异常返回 `(None, -1)` 且 `ret` 位置统一——调用方可用 `q, ret = arm.inverse_kinematics(...); if ret != 0 or q is None: ...` 处理失败。

---

## 12. 工具方法：_ret_text（返回码转中文）

```python
@staticmethod
def _ret_text(ret: int) -> str:
    """返回码 -> 中文（尽量用 SDK 的 errorCode2Str）。"""
    try:
        s = pyaubo_sdk.errorCode2Str(ret)
        if s:
            return f"错误码{ret}: {s}"
    except Exception:
        pass
    return f"错误码{ret}"
```

**逐段解读**：

1. **`@staticmethod`**：不依赖实例状态，纯函数（可以 `AuboK5ArmController._ret_text(12)` 静态调用）。
2. **首选 SDK 翻译**：`pyaubo_sdk.errorCode2Str(ret)` 是 SDK 自带的"错误码 → 错误描述字符串"接口。如果返回非空字符串，拼成 `"错误码{ret}: {s}"`（如 `"错误码12: 目标位置超出工作空间"`）。
3. **兜底**：SDK 翻译失败（版本差异、未知错误码）→ 只返回 `"错误码{ret}"`，至少保留数字可查文档。
4. **为什么包 try/except**：`errorCode2Str` 本身也可能抛异常（比如 SDK 未初始化、ret 类型异常），不能让翻译环节掩盖真正的运动错误。

**返回码速查**（SDK 通用约定，详见官方文档）：`0` = 成功；负数 = 通用错误（如 `-1` 参数错误）；正数 = 运动相关错误（如 `2` = servo 缓冲满、`12` 类 = 路径规划失败）。具体数值含义以 `errorCode2Str` 输出为准。

---

## 13. 模块级函数：quick_check

```python
def quick_check(ip: Optional[str] = None) -> dict:
    """快速连通性检查（不登录也尝试连接并读状态），供 test_arm/diag_arm 使用。"""
    arm = AuboK5ArmController(ip=ip)
    ok = arm.open()
    out = {"connected": ok}
    if ok:
        try:
            out["robot_name"] = arm._robot_name
            out["summary"] = arm.get_state_summary()
        except Exception as exc:
            out["summary_error"] = str(exc)
        arm.close()
    return out
```

**功能**：一键连通性诊断——构造控制器 → `open()` → 读状态汇总 → 关闭 → 返回结果字典。

**逐段解读**：

1. **构造**：只覆盖 `ip`（其他参数走默认，方便快速指定 IP 测试）。
2. **open**：`ok = arm.open()` —— 连接+登录+取接口+设速度+写 TCP 偏移，全流程一次跑完。**失败时字典只有 `{"connected": False}`**（调用方据此判定"连不上"）。
3. **读状态**：成功连接后抓 `robot_name` + `get_state_summary()`（7 项状态，见 6.4 节）。整个读取包在 try/except 里——即使某项状态读取炸了，也返回 `summary_error` 字段而不是整体崩溃。**诊断工具的价值就在于"什么都别崩，把能查的查出来"**。
4. **清理**：最后 `arm.close()` 释放连接（诊断脚本通常连完就退，必须收尾）。
5. **返回值结构**：`{"connected": bool, "robot_name": str, "summary": dict} | {"connected": False} | {"connected": True, "summary_error": str}`——`diag_arm.py`/`test_arm.py` 直接打印/渲染。

> ⚠️ **小瑕疵说明**：第 602 行直接访问了私有字段 `arm._robot_name`（本应走公共 getter）。这是刻意简化（该类没有 `get_robot_name()` 公共方法），但破坏了封装；后续如新增公共 `get_robot_name()` 方法，这里应一并改掉。

---

## 14. 与官方示例对照表（汇总）

官方示例路径：`lib/aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170/share/example/python/`

| 本文件方法 | 调用的 SDK 接口 | 对应官方示例（文件 + 关键行） |
|---|---|---|
| `open()`（连接/登录段） | `RpcClient.connect/login/hasConnected/hasLogined/setRequestTimeout` | `example_movej.py` 第 100–107 行；`example_movel.py` 第 112–121 行 |
| `open()`（取名字/取接口段） | `getRobotNames/getRobotInterface` | `example_movej.py` 第 58–60 行 |
| `open()`（速度比例段） | `MotionControl.setSpeedFraction` | `example_movej.py` 第 63 行；`example_movel.py` 第 60 行 |
| `apply_tcp_offset()` | `RobotConfig.setTcpOffset` | `example_movel.py` 第 63–64 行 |
| `poweron()` / `startup()` / `poweroff()` | `RobotManage.poweron/startup/poweroff` | `example_startup.py` 第 26/29/44 行 |
| `poweron_and_startup()`（Running 轮询） | `RobotState.getRobotModeType` | `example_startup.py` 第 32–38 行（官方死循环，本文件加超时） |
| `_wait_arrival()` | `MotionControl.getExecId` | `example_movej.py` 第 22–41 行 `wait_arrival`（官方无超时，本文件加超时） |
| `movej()` | `MotionControl.moveJoint` | `example_movej.py` 第 66–67 行 |
| `movel()` | `MotionControl.moveLine` | `example_movel.py` 第 79–80 行 |
| `movec()` | `MotionControl.moveCircle` | `example_movec.py` 第 56 行 |
| `move_home()`（home 点） | （复用 movej） | `example_movej.py` 第 47–49 行 q1；`example_movel.py` 第 47–48 行 q |
| `stop_move()` | `MotionControl.stopMove` | `example_motion_control.py`（stop 演示段） |
| `servo_mode_enable()` | `MotionControl.setServoModeSelect/getServoModeSelect` | `example_servoj2.py` 第 69–82 行 `switch_servoj_mode`（逐行对应） |
| `servo_joint()` | `MotionControl.servoJoint` | `example_servoj2.py` 第 185 行 `mc.servoJoint(q, 0.1, 0.2, t, 0.1, 200)` |
| `freedrive()` | `RpcClient.getRuntimeMachine().start` + `RobotManage.freedrive` | `example_freedrive.py` 第 22–27 行 |
| `get_standard_digital_inputs/outputs` | `IoControl.getStandardDigitalInputNum/getStandardDigitalInput/...` | `example_io.py` 第 42/45/70/77 行 |
| `set_standard_digital_output` | `IoControl.setStandardDigitalOutput` | `example_io.py`（标准输出写入段） |
| `set_tool_digital_output` | `IoControl.setToolDigitalOutput` | `example_io.py` 第 139 行 |
| `forward_kinematics()` | `RobotAlgorithm.forwardKinematics` | `example_algorithm.py` 第 44 行；`example_force_control.py` 第 160–162 行 |
| `inverse_kinematics()` | `RobotAlgorithm.inverseKinematics` | `example_algorithm.py` 第 32 行；`example_servo_cartesian.py` 第 79 行 |
| `get_joint_positions()` / `get_tcp_pose()` | `RobotState.getJointPositions/getTcpPose` | `example_state.py` 第 36/75 行；`example_math.py` 第 71 行 |
| `is_steady()` | `RobotState.isSteady` | `example_servoj2.py` 第 64 行（waitServoJointComplete 第二步） |
| `_ret_text()` | `pyaubo_sdk.errorCode2Str` | 官方错误码处理惯例（各示例打印 ret 时） |

---

## 15. 线程与阻塞注意

### 15.1 阻塞模型总览

| 方法 | 是否阻塞 | 阻塞时长 | 说明 |
|---|---|---|---|
| `open()` | 是 | 最多 `rpc_timeout_ms`×几次 + 正常连接耗时 | 网络故障时可能多次超时 |
| `movej`/`movel`（`block=True`） | **是** | 运动全程（默认最多 30s 超时） | **阻塞调用线程直到运动完成** |
| `movej`/`movel`（`block=False`） | 否 | — | 立即返回，运动后台执行 |
| `movec` | 否 | — | 只下发不等（无 block 参数） |
| `poweron_and_startup()` | 是 | 最多 `timeout_s`（默认 15s） | 内部 0.5s 轮询 |
| `servo_joint()` | 否 | — | 单点下发，微秒级 |
| `freedrive(True, duration_s=25)` | 是 | `duration_s` 秒 | 内部 sleep |
| 其余 getter | 否 | 单次 RPC 往返（≤ 超时 1s） | — |

### 15.2 对 GUI 的关键约束（重要）

- **`block=True` 会阻塞调用它的线程**。GUI 主线程（tkinter 的 mainloop）一旦被 `movej(block=True)` 卡住，**整个窗口冻结、按钮失灵、状态不刷新**。
- 因此 GUI 场景的正确姿势（与 `gui/main_gui_arm.py` 的约定一致）：
  1. **运动一律 `block=False`**（只下发指令，立即返回）；
  2. 用 **`after()` 定时轮询**完成状态：每 100–200ms 调一次 `is_steady()` 或 `get_joint_positions()` 与目标对比，运动完成后更新 UI、解锁按钮；
  3. 需要"等待完成"的阻塞逻辑放在**后台工作线程**（`threading.Thread`），完成后再通过队列/`after` 通知主线程刷新。
- **多线程注意**：pyaubo_sdk 的 RpcClient 是**线程安全的吗？**——官方示例 `example_multi_thread.py` 表明 SDK 支持多线程访问，但同一时刻多个线程同时下发运动指令仍可能互相干扰。**推荐"单线程发指令"**：所有运动调用集中在一个控制线程，其他线程只读状态。
- **进程退出前**：务必 `arm.close()`（登出+断开）。`logout` 顺序在 close 内已保证；若直接 kill 进程，控制柜侧会话可能残留，需等待自动超时释放。

### 15.3 阻塞与中断

- `_wait_arrival` 的 30s 超时 + `poweron_and_startup` 的 15s 超时是**防挂死底线**；但若在 `time.sleep` 期间程序被要求退出，需等当前 sleep 结束。GUI 的"急停"应调 `stop_move()` 让 `_wait_arrival` 尽快观察到 `getExecId() == -1`（运动被中止后 ID 会复位）。

---

## 16. 常见问题（FAQ）

### Q1：`open()` 返回 False，日志显示"连接失败/超时"
**排查链**：
1. 控制柜是否开机、网线是否连通（`ping <ip>`，默认 192.168.1.100）；
2. 电脑网卡 IP 是否与控制柜同网段（如 192.168.1.x），Windows 防火墙是否放行 30004 端口；
3. `setRequestTimeout(1000)` 下超时 = 网络层不通；对照 `arm_config.CONN_ERROR_TEXT` 里的 `AUBO_TIMEOUT`（网络不通/防火墙）与 `AUBO_CONN_REFUSED`（IP/端口错或控制柜未开机）；
4. 若用模拟器/本机测试，把 `ARM_CONFIG["ip"]` 改为 `127.0.0.1`。

### Q2：连接成功但登录失败 / `hasLogined()=False`
- 账号密码写错（默认 `aubo` / `123456`，在 `arm_config.py` 或构造参数里核对）；
- 控制柜已满登录会话（其他程序/上次异常退出残留的会话未释放）——**重启控制柜或等会话超时**；检查是否有别的进程占着同一个机器人没 logout。

### Q3：运动指令返回非 0 错误码
- 先用 `_ret_text` 翻译（本类已自动翻译成 err_msg）；常见原因：
  - **目标超出工作空间/关节限位**（`JOINT_RANGE_DEG` 保守范围 ±175°，目标越界）；
  - **奇异点**（见 Q5）；
  - 运动参数非法（速度为 0、负值、NaN）；
  - 控制柜处于非 Running 状态（未上电/急停/错误模式）——先 `poweron_and_startup()`；
  - servo 模式下调用普通 movej/movel 被拒——先 `servo_mode_enable(False)`。

### Q4：指令返回 0 但机械臂不动 / block 后超时
- **机械臂未上电/未启动**：`moveJoint` 下发成功（0）只代表指令被接收，机器人不 Running 就不执行——必须 `poweron_and_startup()` 等到 Running；
- **安全模式异常**：急停按下、保护性停止未复位（查 `get_safety_mode()`）；
- **速度比例过低**：`speed_fraction` 太小（如 0.05）时运动极慢，30s 超时不够——调大或加大 `timeout_s`；
- **目标等于当前位置**：距离为 0 的运动瞬间"完成"，`_wait_arrival` 阶段 A 可能因 exec_id 未经历非 -1 而走 5 次重试 → 返回 -1（表现为"等待超时"假象）。

### Q5：movel 报奇异点（singularity）错误
- 直线运动在**关节奇异位形**（如腕部中心接近 J1 轴线、J4/J6 同轴对齐）附近无解或速度爆炸，控制柜拒绝轨迹；
- 处理：① 绕开奇异区域走多个中间点；② 改用 `movej`（关节空间无奇异问题）；③ 逆解时传好参考关节角选同构型解（见第 11 节，参考 `example_stable_ik.py`）。

### Q6：movel/movec 目标位姿"对不上"视觉坐标
- **TCP 偏移没写对**：`apply_tcp_offset` 未执行（open 失败）、`hand_mount_offset` 与实际安装不符（方向/距离），或安装灵巧手后没重新调用 `apply_tcp_offset(新偏移)`；
- 验证：读 `get_tcp_pose()` 与理论值对比；把 `hand_mount_offset` 清零做对照实验。

### Q7：servo 模式下机械臂行为异常（抖动/不跟手/超调）
- **模式选错**：跟随精度要求高用 mode 5（路点必达），高速连续用 mode 1；mode 1 是截断式，不保证过路点；
- **节拍不稳**：`servoJoint` 必须在稳定节拍（5ms 级别）下调用，中间有 >20ms 抖动会造成轨迹畸变——视觉推理循环别在 servo 循环里做重计算；
- **返回 2（缓冲满）**：按官方示例 `sleep(0.005)` 后重发同一点；
- **开 servo 前必须到位**：官方注释明确"当前位置要与轨迹第一个点一致，否则容易引起较大超调"（`example_servoj2.py` 第 108 行）——先用 movej 到起点再开 servo。

### Q8：freedrive 进入不了 / 一进就退
- 确认已 `poweron_and_startup()`（示教需要上电状态）；
- `getRuntimeMachine().start()` 被静默吞掉可能未生效——若 freedrive(True) 返回非 0，检查运行时机器状态；
- 部分固件要求先退出 servo 模式再进 freedrive。

### Q9：程序退出后再次连接失败
- 上次进程没 `close()`，控制柜会话残留——等待超时或重启控制柜；代码里用 `try/finally: arm.close()` 保证退出清理。

---

## 17. 典型调用时序

### 17.1 命令行脚本（阻塞式，简单直接）

```python
from arm import AuboK5ArmController

arm = AuboK5ArmController()            # 构造（默认 IP/端口/速度 0.3）
try:
    if not arm.open():
        print("连接失败"); return
    if not arm.poweron_and_startup():  # 上电+启动+等 Running（≤15s）
        print("上电/启动失败"); return
    arm.move_home(block=True)          # 回 home（阻塞至完成）
    ret, msg = arm.movel([0.55, 0.0, 0.4, 3.14, 0, 1.57], block=True)
    print("movel:", ret, msg)
    q, ret = arm.inverse_kinematics(
        arm.get_joint_positions(), [0.55, 0.0, 0.4, 3.14, 0, 1.57])
    print("逆解:", q, ret)
finally:
    arm.close()                        # 登出+断开（不自动断电）
```

### 17.2 GUI 场景（非阻塞 + after 轮询）

```python
# 按钮回调（主线程，绝不用 block=True）
def on_go_clicked():
    ret, msg = arm.movel(target_pose, block=False)
    if ret != 0:
        show_error(msg); return
    root.after(100, poll_arrival)      # 100ms 后轮询

def poll_arrival():
    if arm.is_steady():                # 停稳 = 运动完成
        set_status("到位"); enable_buttons()
    else:
        root.after(100, poll_arrival)  # 未完成，继续轮询
```

### 17.3 视觉跟随（servo 模式）

```python
arm.poweron_and_startup()
arm.movej(轨迹起点, block=True)        # 先到位，防超调
arm.servo_mode_enable(True, mode=1)
try:
    for q in 视觉轨迹点:                # 5ms 节拍
        ret = arm.servo_joint(q)
        if ret == 2:                    # 缓冲满 → 重发
            time.sleep(0.005); ret = arm.servo_joint(q)
        if ret != 0: break
finally:
    arm.servo_mode_enable(False)        # 视觉线程异常也要关闭
    arm.stop_move()
```

---

## 18. 方法索引表

| 方法 | 行号 | 一句话功能 |
|---|---|---|
| `__init__` | 59 | 构造：参数回落到 ARM_CONFIG，7 个句柄置 None |
| `open` | 106 | 连接→登录→取接口→设速度→写 TCP 偏移（全有或全无） |
| `has_connected` | 167 | 本地句柄 + SDK 双查连接状态 |
| `has_logined` | 170 | 本地句柄 + SDK 双查登录状态 |
| `close` | 173 | 登出→断开→8 字段清空（不自动断电） |
| `poweron` / `startup` / `poweroff` | 198/206/214 | 上电 / 启动松刹车 / 断电（ret==0 判成功） |
| `poweron_and_startup` | 222 | 上电+启动+等 Running（0.5s 轮询，15s 超时） |
| `get_robot_mode` / `get_safety_mode` | 244/252 | 读主模式 / 安全模式（失败返回 None） |
| `is_steady` / `is_within_safety_limits` | 259/267 | 是否停稳 / 是否在安全限位内 |
| `get_joint_positions` / `get_tcp_pose` | 274/282 | 当前关节角（弧度）/ TCP 位姿（含偏移） |
| `get_state_summary` | 290 | 7 项状态打包成字典（GUI/诊断用） |
| `get_speed_fraction` / `set_speed_fraction` | 302/309 | 读/写速度比例（写时钳制到 0~1） |
| `apply_tcp_offset` | 319 | 基础偏移+安装偏移 → setTcpOffset（TCP 坐标联动） |
| `get_hand_mount_offset` | 342 | 读安装偏移 |
| `_wait_arrival` | 348 | 阻塞等运动完成（getExecId 两阶段 + 30s 超时） |
| `movej` | 382 | 关节运动（度→弧度，可阻塞） |
| `movel` | 407 | 直线运动（TCP 系位姿，可阻塞） |
| `movec` | 430 | 圆弧运动（中间点+终点，不阻塞） |
| `move_home` | 447 | 回官方示例起点（度写法 → 弧度） |
| `stop_move` | 452 | 急停当前运动 |
| `servo_mode_enable` | 461 | servo 模式开关（mode 1/2/5，轮询确认生效） |
| `servo_joint` | 480 | 下发单个伺服目标点（视觉跟随节拍调用） |
| `freedrive` | 494 | 拖拽示教进出（可选自动计时退出） |
| `get_standard_digital_inputs/outputs` | 517/526 | 读全部标准数字 IO |
| `set_standard_digital_output` | 534 | 写标准数字输出 |
| `get_tool_digital_input` / `set_tool_digital_output` | 542/549 | 工具端 IO（夹爪/灵巧手信号） |
| `forward_kinematics` / `inverse_kinematics` | 560/569 | 正解 / 逆解（视觉坐标↔关节角桥梁） |
| `_ret_text` | 583 | SDK 错误码转中文（静态） |
| `quick_check` | 595 | 模块级快速连通性诊断（test_arm/diag_arm 用） |

---

*本文档依据 `arm/arm_controller.py`（607 行）与 `arm/arm_config.py` 撰写，SDK 调用签名已对照 `lib/aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170/share/example/python/` 下官方示例逐一核实。*
