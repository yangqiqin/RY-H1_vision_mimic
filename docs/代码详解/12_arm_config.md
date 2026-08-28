# 12 · `arm/arm_config.py` 代码详解

> 本文档对应源文件：`RY-H1_vision_mimic/arm/arm_config.py`（共 78 行）
>
> 本文件是整个「睿研 RY-H1(16) 灵巧手 + Aubo K5 机械臂视觉动作模仿系统（Windows 版）」中**机械臂侧的"配置单点"**：它不包含任何执行逻辑，只声明一组全局常量（连接参数、运动参数、TCP 偏移、关节范围、错误码文案）。所有机械臂相关模块（`arm_controller.py`、`main_gui_arm.py`、`apps/diag_arm.py`、`apps/test_arm.py`）都从这里取值，**改机械臂配置只需改这一个文件**。

---

## 目录

1. [文件职责总览](#1-文件职责总览)
2. [模块头部 docstring：设计依据（L1–L14）](#2-模块头部-docstring设计依据l1l14)
3. [`ARM_CONFIG` 字典总览](#3-arm_config-字典总览)
4. [连接配置组（L19–L26）](#4-连接配置组l19l26)
5. [运动默认参数组（L28–L34）](#5-运动默认参数组l28l34)
6. [TCP / 工具组（L36–L39）](#6-tcp--工具组l36l39)
7. [灵巧手安装偏移（L41–L46）——TCP 坐标联动核心](#7-灵巧手安装偏移l41l46tcp-坐标联动核心)
8. [安全组（L48–L50）](#8-安全组l48l50)
9. [常量速查表：全键一览](#9-常量速查表全键一览)
10. [`DOF`：自由度（L53–L54）](#10-dof自由度l53l54)
11. [`JOINT_NAMES_CN`：关节中文名（L56–L60）](#11-joint_names_cn关节中文名l56l60)
12. [`JOINT_RANGE_DEG`：关节角安全范围（L62–L71）——为什么取"保守值"](#12-joint_range_deg关节角安全范围l62l71为什么取保守值)
13. [`CONN_ERROR_TEXT`：连接错误码中文解释（L73–L78）](#13-conn_error_text连接错误码中文解释l73l78)
14. [被谁引用：模块依赖关系图](#14-被谁引用模块依赖关系图)
15. [修改配置的注意事项](#15-修改配置的注意事项)

---

## 1. 文件职责总览

`arm_config.py` 在整个机械臂子系统中的定位可以用一句话概括：

> **它是机械臂的"出厂设置单"，所有机械臂代码都向它要默认值，而不是自己写死参数。**

| 职责 | 说明 |
|---|---|
| **连接参数** | 控制柜 IP、RPC 端口、RTDE 端口、账号密码、RPC 超时 |
| **运动参数** | 全局速度比例、moveJoint / moveLine 的速度加速度上限、过渡半径 |
| **工具参数** | 法兰中心 TCP 偏移、灵巧手安装偏移（联动核心） |
| **安全参数** | 速度比例滑条的上下限 |
| **命名与范围** | 自由度、关节中文名、关节角安全范围 |
| **错误码文案** | 连接失败时给用户看的错误码中文解释 |

设计上刻意做到：**配置与逻辑分离**。控制器与 GUI 只负责"使用"这些值，不负责"决定"这些值，这样：
- 换一台机械臂 / 换一种安装方式，只改一个文件；
- GUI 面板上的默认 IP、端口、速度比例直接来自这里；
- 安全相关参数（速度比例、关节范围）集中在同一处，方便审计。

---

## 2. 模块头部 docstring：设计依据（L1–L14）

```
L1   # -*- coding: utf-8 -*-
L2   """
L3   arm_config.py —— Aubo（遨博）K5 机械臂配置（Windows 版）
...
L14  """
```

- **L1**：声明源文件为 UTF-8 编码，保证中文注释在 Windows 控制台/IDE 下不乱码。
- **L3–L6**：说明参数来源——`lib/auboDocument/` 下的三份官方 PDF（通信搭建 / SDK 功能模块 / Python SDK）以及 SDK 自带的 Python 示例（`lib/aubo_sdk-.../share/example/python/`）。也就是说，**这里的所有默认值都不是拍脑袋定的，而是对照官方文档与官方示例抄录的**。
- **L8–L13**：四条"关键事实"，是整个文件数值的推导依据：
  1. **通信方式**：TCP RPC，默认端口 30004；RTDE 数据端口 30010；登录账号 `aubo` / 密码 `123456`；
  2. **机器人 IP**：官方示例默认 `127.0.0.1`（本机模拟器）；实机要填控制柜网口 IP（如 `192.168.1.100`）；
  3. **单位制**：关节角用**弧度**；位姿 `[x,y,z,rx,ry,rz]` 中位置单位是**米**、姿态单位是**弧度**；moveJoint 的速度/加速度单位是 rad/s，moveLine 是 m/s 与 m/s²（GUI 里显示给用户的是度，转换在 GUI 层做）；
  4. **安全**：`setSpeedFraction(0~1)` 是全局速度比例；**首次运行建议 0.2~0.3**——这就是 `speed_fraction` 默认 0.3 的出处。

> ⚠️ 理解单位制是读懂后面所有配置的关键：`arm_config.py` 里**关节角范围用"度"**（给人看），而**控制器内部运动用"弧度"**（给 SDK 用），两者之间的换算发生在 `main_gui_arm.py`（`math.radians`）与 `arm_controller.py` 内部。

---

## 3. `ARM_CONFIG` 字典总览

`ARM_CONFIG`（L19–L51）是一个普通 Python 字典，按功能分为 5 组，每组前有注释分隔：

| 分组 | 键 | 行号 |
|---|---|---|
| RPC 连接 | `ip` / `rpc_port` / `rtde_port` / `username` / `password` / `rpc_timeout_ms` | L20–L26 |
| 运动默认参数 | `speed_fraction` / `joint_speed` / `joint_acc` / `line_speed` / `line_acc` / `blend_radius` | L28–L34 |
| TCP / 工具 | `tcp_offset` | L36–L39 |
| 灵巧手安装偏移 | `hand_mount_offset` | L41–L46 |
| 安全 | `max_speed_fraction` / `min_speed_fraction` | L48–L50 |

下面逐组、逐键详解。

---

## 4. 连接配置组（L19–L26）

```python
L19  ARM_CONFIG = {
L20      # ---- RPC 连接 ----
L21      "ip": "192.168.1.100",      # 机械臂控制柜 IP（示例默认 127.0.0.1 为模拟器/本机）
L22      "rpc_port": 30004,          # RPC 服务端口（官方示例）
L23      "rtde_port": 30010,         # RTDE 数据端口（官方示例，非阻塞/状态用）
L24      "username": "aubo",         # 登录账号（官方示例）
L25      "password": "123456",       # 登录密码（官方示例）
L26      "rpc_timeout_ms": 1000,     # RPC 请求超时（毫秒）
```

| 键 | 默认值 | 类型 | 含义 / 单位 | 被谁使用 | 为什么这样设 |
|---|---|---|---|---|---|
| `ip` | `"192.168.1.100"` | str | 机械臂控制柜的 IP 地址 | `arm_controller.py` L81（构造器默认）、`main_gui_arm.py` L76/L150（GUI 输入框默认值）、`apps/diag_arm.py` L38、`apps/test_arm.py` L61（命令行默认值） | 实机控制柜网口 IP 示例；官方示例默认 `127.0.0.1` 是模拟器/本机。现场若网段不同需在此改 |
| `rpc_port` | `30004` | int | RPC 服务端口（控制指令走这里） | `arm_controller.py` L82/L115、`main_gui_arm.py` L79/L152/L154、两个 apps | 官方示例端口，一般无需改动 |
| `rtde_port` | `30010` | int | RTDE 数据端口（状态/非阻塞数据读取） | 由 `arm_controller.py` 内部 RTDE 连接使用 | 官方示例端口，与 RPC 端口成对出现 |
| `username` | `"aubo"` | str | 登录账号 | `arm_controller.py` L83 | 官方示例账号 |
| `password` | `"123456"` | str | 登录密码 | `arm_controller.py` L84 | 官方示例密码；实机出厂默认 |
| `rpc_timeout_ms` | `1000` | int | RPC 请求超时（毫秒） | `arm_controller.py` L115：`client.setRequestTimeout(timeout_ms or ARM_CONFIG["rpc_timeout_ms"])` | 1 秒对本地网段足够；太短会导致慢响应被误判失败，太长会让 GUI 按钮"卡死"感明显 |

**设计意图**：GUI 的 IP/端口输入框（`main_gui_arm.py` L76/L79）直接用这两个值当默认显示，用户现场只需在面板上改 IP，无需改代码。

---

## 5. 运动默认参数组（L28–L34）

```python
L28      # ---- 运动默认参数 ----
L29      "speed_fraction": 0.3,      # 全局速度比例 0~1（安全起步，官方示例用 0.75）
L30      "joint_speed": 40.0,        # moveJoint 关节速度上限（度/秒，内部转弧度）
L31      "joint_acc": 30.0,          # moveJoint 关节加速度上限（度/秒²）
L32      "line_speed": 0.4,          # moveLine 末端线速度（米/秒）
L33      "line_acc": 0.3,            # moveLine 末端线加速度（米/秒²）
L34      "blend_radius": 0.0,        # 过渡半径（0 = 精确到达，>0 平滑过渡）
```

| 键 | 默认值 | 单位 | 含义 | 被谁使用 | 为什么这样设 |
|---|---|---|---|---|---|
| `speed_fraction` | `0.3` | 无（比例 0~1） | 全局速度比例，对一切运动生效（相当于"油门"） | `arm_controller.py` L86（控制器默认）、`main_gui_arm.py` L84（滑条初始值）L157（连接时传入） | **安全起步**：首次联调推荐 0.2~0.3；官方示例用 0.75 对新手太快、风险高（源码注释已注明） |
| `joint_speed` | `40.0` | 度/秒（内部转 rad/s） | moveJoint 关节速度上限 | `arm_controller.py` L390（`movej` 未显式传速度时的默认） | 40°/s 是较保守的关节速度，便于观察与急停 |
| `joint_acc` | `30.0` | 度/秒² | moveJoint 关节加速度上限 | `arm_controller.py` L392（`movej` 默认加速度） | 加速度比速度更影响冲击力，取低值降低机械冲击 |
| `line_speed` | `0.4` | 米/秒 | moveLine 末端直线运动速度 | `arm_controller.py` L414/L434（`movel`/`movec` 默认速度） | 0.4 m/s 兼顾效率与安全，适合桌面级演示 |
| `line_acc` | `0.3` | 米/秒² | moveLine 末端直线加速度 | `arm_controller.py` L415/L435 | 与 line_speed 匹配，起停平缓 |
| `blend_radius` | `0.0` | 米 | 运动段间过渡半径 | `arm_controller.py` L396/L419/L439（传入 SDK 的 blend radius 参数） | **0 = 精确到达**目标点再执行下一段；>0 会在到达前提前转弯（平滑但会"抄近路"）。默认精确，避免"以为到位了其实没到"的联动错位 |

> 🔑 **speed_fraction 与 joint_speed 的区别**：`joint_speed` 是"这条指令允许的最大速度"，`speed_fraction` 是"把一切速度再统一乘一个比例"。两者是乘法关系，例如 joint_speed=40、fraction=0.3 时实际关节速度上限约为 12°/s。

---

## 6. TCP / 工具组（L36–L39）

```python
L36      # ---- TCP / 工具 ----
L37      # 默认工具中心点偏移（相对法兰盘中心，[x,y,z,rx,ry,rz]，米/弧度）。
L38      # 若不挂灵巧手，保持全 0；挂载灵巧手时把"安装偏移"填到 HAND_MOUNT_OFFSET。
L39      "tcp_offset": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
```

- **默认值**：6 元全 0 列表 `[x,y,z,rx,ry,rz]`，位置单位米、姿态单位弧度。
- **含义**：机械臂**基础**工具中心点（TCP）相对法兰盘中心的偏移。TCP 是机器人运动学计算"末端到底在哪"的基准点。
- **被谁使用**：`arm_controller.py` L88（构造器把默认 TCP 偏移存进 `self._tcp_offset`），随后 `apply_tcp_offset()`（L319–L340）把"基础偏移 + 安装偏移"合并后调用 SDK `setTcpOffset` 写入机械臂。
- **为什么默认全 0**：不挂任何工具时，TCP 就是法兰盘中心本身。若挂载了其他刚性工具（如吸盘、夹爪），应把该工具的偏移填在这里；**灵巧手的偏移不要填这里**，而是填下一节的 `hand_mount_offset`——因为灵巧手需要被"联动开关"动态启停。

---

## 7. 灵巧手安装偏移（L41–L46）——TCP 坐标联动核心

```python
L41      # ---- 灵巧手安装偏移（TCP 坐标联动核心）----
L42      # RY-H1(16) 灵巧手安装在机械臂法兰下时，相对法兰的平移/旋转偏移（米/弧度）。
L43      # 设置后 setTcpOffset 会把该偏移写入机械臂，moveLine/moveCircle 的位姿
L44      # 即直接以"灵巧手 TCP"为基准（先动臂到目标，再做手势）。
L45      # 实测值需按实际安装测量填写；默认给出示例值（法兰下方 0.15m、绕X轴180°）。
L46      "hand_mount_offset": [0.0, 0.0, 0.15, 3.141592653589793, 0.0, 0.0],
```

| 项 | 值 | 说明 |
|---|---|---|
| 默认值 | `[0.0, 0.0, 0.15, π, 0.0, 0.0]` | z=+0.15 m（法兰正下方 15 cm）、rx=π（绕 X 轴翻转 180°），其余为 0 |
| 单位 | 米 / 弧度 | 与 SDK 位姿约定一致 |
| 被谁使用 | `main_gui_arm.py` L262（TCP 联动开启时若控制器没存偏移，取此值兜底）、`arm_controller.py` L319–L343（`apply_tcp_offset` / `get_hand_mount_offset`） | |
| 为什么这样设 | 这是**示例值**：灵巧手装在法兰下方 15 cm，且通常需要翻转 180° 让手指朝下/朝前。**实机必须按实际安装尺寸重新测量填写**（源码注释 L45 明确说明） | |

**设计意图（联动核心）**：
1. 机械臂 SDK 的 `setTcpOffset` 一旦设置了偏移，后续 `moveLine/moveCircle` 的目标位姿就**以新的 TCP 为基准**；
2. 把灵巧手安装偏移写进去后，用户在 GUI 里输入的 movel 位姿"指向的是灵巧手手指尖"而不是"法兰中心"，坐标系语义与人的直觉一致；
3. 勾选"TCP 联动"= 写入该偏移；取消勾选 = 写入全 0（回到法兰 TCP）。这就是 `main_gui_arm.py` 中 `_arm_toggle_link` 的底层依据。

> ⚠️ 两个偏移的分工：`tcp_offset`（L39）= 法兰上的固定工具；`hand_mount_offset`（L46）= 灵巧手，**由 GUI 勾选动态启停**。控制器合并规则见 `arm_controller.apply_tcp_offset`：最终偏移 = `tcp_offset` 逐元素 + `hand_mount_offset`（平移相加、旋转相加）。

---

## 8. 安全组（L48–L50）

```python
L48      # ---- 安全 ----
L49      "max_speed_fraction": 1.0,  # 速度比例上限（GUI 滑条范围用）
L50      "min_speed_fraction": 0.05,  # 速度比例下限
```

- `max_speed_fraction = 1.0`：速度比例滑条上限，即最大允许 100% 全速。
- `min_speed_fraction = 0.05`：下限，即最小 5%，**永远不允许滑到 0**——防止用户误以为"0 = 停止"而实际是"速度比例非法"。
- **被谁使用**：`main_gui_arm.py` L85 的 `tk.Scale(from_=0.05, to=1.0, ...)` 滑条范围就是抄的这两个值（当前是字面量写死，与配置一致）。`arm_controller.set_speed_fraction`（L311）也会把传入值钳制在 0~1。
- **为什么这样设**：上限 1.0 表示"允许全速"（实测/熟练后可用），下限 0.05 防止 0 值歧义；安全实践上建议日常演示把滑条拉到 0.3 以下。

---

## 9. 常量速查表：全键一览

| 键 | 默认值 | 单位 | 一句话说明 |
|---|---|---|---|
| `ip` | `192.168.1.100` | — | 控制柜 IP |
| `rpc_port` | `30004` | — | RPC 指令端口 |
| `rtde_port` | `30010` | — | RTDE 状态端口 |
| `username` / `password` | `aubo` / `123456` | — | SDK 登录凭据 |
| `rpc_timeout_ms` | `1000` | ms | RPC 请求超时 |
| `speed_fraction` | `0.3` | 比例 | 全局速度油门（官方示例 0.75，这里保守起步） |
| `joint_speed` | `40.0` | °/s | moveJoint 速度上限 |
| `joint_acc` | `30.0` | °/s² | moveJoint 加速度上限 |
| `line_speed` | `0.4` | m/s | moveLine 线速度 |
| `line_acc` | `0.3` | m/s² | moveLine 线加速度 |
| `blend_radius` | `0.0` | m | 段间过渡半径（0=精确） |
| `tcp_offset` | 全 0 | m/rad | 法兰工具基础 TCP 偏移 |
| `hand_mount_offset` | `[0,0,0.15,π,0,0]` | m/rad | 灵巧手安装偏移（联动核心，需实测） |
| `max_speed_fraction` / `min_speed_fraction` | `1.0` / `0.05` | 比例 | 速度滑条上下限 |

---

## 10. `DOF`：自由度（L53–L54）

```python
L53  # 机械臂自由度（Aubo K5 为 6 轴）
L54  DOF = 6
```

- **含义**：Aubo K5 是 6 自由度串联机械臂，`DOF = 6`。
- **被谁使用**：`main_gui_arm.py` L104——`for i in range(DOF)` 决定 GUI 第 3 行要生成**几个**关节滑条。如果将来换 7 轴臂，改这里 GUI 会自动多出一个滑条。
- **为什么单独提出来**：把"轴数"从"关节名列表长度"中独立出来，语义更清晰，也便于程序化遍历。

---

## 11. `JOINT_NAMES_CN`：关节中文名（L56–L60）

```python
L56  # 关节中文名（GUI/日志显示用，按关节 1~6）
L57  JOINT_NAMES_CN = [
L58      "基座旋转(J1)", "肩部(J2)", "肘部(J3)",
L59      "前臂旋转(J4)", "腕部俯仰(J5)", "腕部旋转(J6)",
L60  ]
```

- **含义**：6 个关节的**中文名 + 英文代号**，从基座到末端依次为 J1~J6：基座旋转、肩部、肘部、前臂旋转、腕部俯仰、腕部旋转——这是 K5 这类 6 轴臂的典型构型命名。
- **被谁使用**：`main_gui_arm.py` L44/L109——先经 `arm/__init__.py`（L22）导出，再被 `main_gui_arm.py` 从 `gui.main_gui` 或 `arm` 导入，用作 6 个关节滑条上方的标签文字。
- **为什么这样设**：给每个滑条一个"人话"名字，操作者不用背 J1~J6 的含义；同时保留 `J1`~`J6` 代号便于与示教器对照。

---

## 12. `JOINT_RANGE_DEG`：关节角安全范围（L62–L71）——为什么取"保守值"

```python
L62  # 关节角安全范围（度，保守值；实机以示教器/文档为准）
L63  # K5 各轴范围参考官方文档，这里取常用保守区间
L64  JOINT_RANGE_DEG = [
L65      (-175.0, 175.0),   # J1
L66      (-175.0, 175.0),   # J2
L67      (-175.0, 175.0),   # J3
L68      (-175.0, 175.0),   # J4
L69      (-175.0, 175.0),   # J5
L70      (-175.0, 175.0),   # J6
L71  ]
```

- **含义**：每个关节允许的运动范围（单位：**度**），以 `(下限, 上限)` 元组表示。当前 6 个轴全部是 ±175°。
- **为什么是"保守值"**（源码注释 L62 明说）：
  1. K5 不同轴的真实机械限位并不相同（有的轴 ±360°，有的轴 ±120°），而这里**统一取了 ±175°**，是为了保证"任何一个轴都不会撞机械限位"的最安全交集；
  2. 源代码只参考了官方文档，**未在实机上逐轴实测**——官方标称范围 vs 实际安装（线缆走线、法兰上挂的灵巧手会不会自撞）可能存在出入；
  3. 因此注释明确要求：**实机以示教器/文档为准**，联调时若发现某个轴实际到不了 ±175°，应在此收窄。
- **被谁使用**：`main_gui_arm.py` L110——6 个关节滑条的范围 `from_=-175, to=175`（当前是字面量，与配置一致）。它同时也是后续"关节角合法性校验"（如 `arm_controller` 的 `is_within_safety_limits`）的数据源。
- **⚠️ 单位提醒**：这里存的是**度**（给人看、给滑条用）；真正下发 SDK 前要在 GUI 里 `math.radians` 转成弧度（见 `main_gui_arm.py` L235）。

---

## 13. `CONN_ERROR_TEXT`：连接错误码中文解释（L73–L78）

```python
L73  # 登录/连接错误码解释（pyaubo_sdk 常量）
L74  CONN_ERROR_TEXT = {
L75      "AUBO_CONN_REFUSED": "连接被拒绝（IP/端口错误或控制柜未开机）",
L76      "AUBO_TIMEOUT": "连接超时（网络不通，检查网线/防火墙）",
L77      "AUBO_CONN_RESET": "连接被重置（控制柜重启或网络中断）",
L78  }
```

- **含义**：把 pyaubo_sdk 抛出的三个典型连接异常常量，映射成**给操作者看的中文排查提示**：
  | 错误码 | 含义 | 排查方向 |
  |---|---|---|
  | `AUBO_CONN_REFUSED` | 连接被拒绝 | IP/端口填错，或控制柜没开机 |
  | `AUBO_TIMEOUT` | 连接超时 | 网络不通，查网线、防火墙、网段 |
  | `AUBO_CONN_RESET` | 连接被重置 | 控制柜重启、掉电或网络中断 |
- **被谁使用**：`arm_controller.py` L45 导入（`from .arm_config import ARM_CONFIG, CONN_ERROR_TEXT, DOF`），在 `open()` 的异常处理中把 SDK 异常翻译成可读文案，再抛给 GUI 弹窗展示（`main_gui_arm.py` L160/L167 的 `messagebox.showerror`）。
- **为什么这样设**：SDK 的原始异常名是英文、对现场操作者不友好；集中维护这份映射，出现新的错误码只需在此追加。

---

## 14. 被谁引用：模块依赖关系图

```
                        ┌──────────────────────────┐
                        │  arm/arm_config.py       │
                        │  （本文件，纯配置）        │
                        └────────────┬─────────────┘
                                     │  import
        ┌──────────────┬─────────────┼──────────────┬──────────────┐
        ▼              ▼             ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│arm/__init__.py│ │arm/          │ │gui/          │ │apps/         │ │apps/         │
│再导出         │ │arm_controller│ │main_gui_arm  │ │diag_arm.py   │ │test_arm.py   │
│ARM_CONFIG,   │ │.py           │ │.py           │ │(--ip/--port/ │ │(--ip/--port/ │
│DOF,          │ │(连接/运动/    │ │(面板默认值/    │ │ --fraction)  │ │ --fraction)  │
│JOINT_NAMES_CN│ │TCP偏移/错误码)│ │TCP联动兜底值)  │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

具体引用点（已核对源码）：

| 引用方 | 使用的配置项 | 行号 |
|---|---|---|
| `arm/__init__.py` | 再导出 `ARM_CONFIG`、`DOF`、`JOINT_NAMES_CN` | L22 |
| `arm/arm_controller.py` | `ARM_CONFIG`（ip/port/账号/超时/速度/TCP 偏移/运动参数）、`CONN_ERROR_TEXT`、`DOF` | L45、L81–L88、L115、L390–L439 |
| `gui/main_gui_arm.py` | `ARM_CONFIG["ip"/"rpc_port"/"speed_fraction"/"hand_mount_offset"]`、`DOF` | L46、L76、L79、L84、L150–L157、L262 |
| `apps/diag_arm.py` | `ARM_CONFIG["ip"/"rpc_port"/"speed_fraction"]` 作为命令行默认值 | L38–L46 |
| `apps/test_arm.py` | `ARM_CONFIG["ip"/"rpc_port"/"speed_fraction"]` 作为命令行默认值 | L61–L66 |

---

## 15. 修改配置的注意事项

1. **改完必须重启程序**：本文件是模块级常量，运行时不会热更新；GUI/诊断程序启动时读取一次。
2. **单位别搞混**：`JOINT_RANGE_DEG` 与 `joint_speed/joint_acc` 的单位是**度**；`hand_mount_offset`/`tcp_offset` 的单位是**米/弧度**；SDK 内部运动接口一律用**弧度**。改范围时不要直接拿 SDK 文档里的弧度值填进 `JOINT_RANGE_DEG`。
3. **`hand_mount_offset` 必须实测**：默认 `[0,0,0.15,π,0,0]` 只是示例。量好灵巧手相对法兰的平移与旋转后填写；填错会导致 movel 目标点与手指实际位置系统性偏差。
4. **`JOINT_RANGE_DEG` 先保守后实测**：出厂统一 ±175° 只是安全交集，联调时逐步按示教器实测值收窄/放宽，并确保 GUI 滑条范围（`main_gui_arm.py` L110）与其保持一致（目前是两处字面量，改配置时记得同步）。
5. **速度比例优先用 GUI 滑条**：`speed_fraction` 只是默认值，现场以 `main_gui_arm.py` 第 1 行的滑条实时调节为准；首次联调务必把滑条拉到 0.3 以下。
6. **错误码文案可扩展**：遇到新连接异常，在 `CONN_ERROR_TEXT` 里追加键值即可，控制器会自动使用。

---

*（本文档完，下一篇：`13_main_gui_arm.md`——扩展版综合控制界面详解）*
