# 02 · `hand/angles2motor.py` —— 关节角度 ↔ 电机指令换算详解

> **源码**：`rycan_hand_windows/hand/angles2motor.py`（92 行）
> **配套**：[00_总览详解.md](00_总览详解.md)（系统全景）· [README.md](README.md)（文档索引）
> **一句话**：把"16 个关节角度（弧度）"换算成"16 个电机位置指令（0~4095）"，以及反向读回；公式与官方 demo `update_motor_positions` 完全一致，并内置左右手（镜像）处理。

---

## 1. 模块定位：数据流中的"翻译官"

```
摄像头 / L515
   ▼
MediaPipe 手部姿态（vision/hand_pose.py）→ 16 关节角度（弧度）
   ▼
★ 本模块 angles2motor.py（角度 ↔ 电机位置）★
   ▼
hand_controller.py（ctypes 调 RyhandLibx64.dll）
   ▼
RY-H1(16) 灵巧手（16 个伺服电机）
```

- 人的关节角度单位是"度/弧度"，电机只认"位置码 0~4095"（12 位 PWM 分辨率，`4095 = 2^12 − 1`）。
- 本模块就是两者之间的"翻译官"：**正变换**把角度翻译成电机指令（下发），**反变换**把电机位置翻译回角度（回读显示/校验）。
- 它是**纯计算模块**：不碰硬件、不碰总线、不依赖 SDK 库，只依赖 `hand_config.py` 的常量——所以可以脱离硬件单独自检（`selfcheck.py`、`apps/test_all.py` 第 4 步都用它做无硬件换算验证）。

---

## 2. 用到的常量（全部来自 `hand/hand_config.py`，本文件无魔法数）

| 常量 | 值 | 含义 |
|---|---|---|
| `FINGER_ORDER` | `["thumb","index","middle","ring","pinky"]` | 5 根手指顺序，决定关节索引的排布 |
| `ANGLE_RANGE_DEG` | 见下表 | 4 类关节的角度范围（度） |
| `K12` | `4095.0/90.0 = 45.5` | 近节/侧摆共用系数（每指电机 1、2） |
| `K3` | `4095.0/75.0 = 54.6` | 远节系数（电机 3） |
| `K16` | `4095.0/110.0 ≈ 37.2273` | 第16关节系数（电机 16） |
| `POS_MAX` | `4095` | 电机位置上限（下限为 0） |

`ANGLE_RANGE_DEG` 内容：

| 键 | 范围（度） | 适用关节 |
|---|---|---|
| `"swing"` | `(-20, 20)` | 侧摆：关节 1,4,7,10,13（每指第 1 个） |
| `"prox"` | `(0, 90)` | 近节：关节 2,5,8,11,14（每指第 2 个） |
| `"dist"` | `(0, 75)` | 远节：关节 3,6,9,12,15（每指第 3 个） |
| `"joint16"` | `(0, 110)` | 关节 16（拇指内外展，独立电机） |

### 2.1 关节索引 ↔ 手指/关节类型 的对应规则（本模块最关键的索引逻辑）

16 个关节按"手指连续排布"：每指固定 3 个关节，顺序 = [侧摆, 近节, 远节]。

```
索引 i:   0   1   2 |   3   4   5 |   6   7   8 |   9  10  11 |  12  13  14 |  15
关节ID:   1   2   3 |   4   5   6 |   7   8   9 |  10  11  12 |  13  14  15 |  16
手指:   拇指        |  食指        |  中指        |  无名指      |  小指        | (第16关节)
类型:   侧摆 近节 远节 | 侧摆 近节 远节 | ...（重复 5 次）...        |  内外展
```

- `i % 3` = 关节在手指内的位置：`0`=侧摆，`1`=近节，`2`=远节。
- `i // 3` = 手指序号（0~4，对应 `FINGER_ORDER` 的 5 根手指）。
- 每个手指的 3 个电机：`base = finger_idx * 3`，则电机1 ↔ `cmds[base]`，电机2 ↔ `cmds[base+1]`，电机3 ↔ `cmds[base+2]`。
- 下标 `i` 对应的**电机 ID = i + 1**（`hand_controller.move_joints` 里 `enumerate(cmds)` 后把 `i+1` 传给 SDK），与 `FINGER_MOTOR_IDS`（拇指 1-3、食指 4-6…）一致。

---

## 3. 公式速查（与官方 demo `update_motor_positions` 完全一致）

```
k  = K12 = 4095/90
M1 = k·( θ1/2 + θ2)      # 每指电机1：近节共模 + 侧摆差模的一半
M2 = k·(−θ1/2 + θ2)      # 每指电机2：近节共模 − 侧摆差模的一半
M3 = K3·θ3               # 远节独立电机
M16 = K16·θ16            # 第16关节独立电机
左手（hand_lr=0）：每指交换 M1 ↔ M2
```

反变换（用于回读）：

```
θ1 = (M1 − M2) / k       # 差模解出侧摆
θ2 = (M1 + M2) / (2k)    # 共模解出近节弯曲
θ3 = M3 / K3
θ16 = M16 / K16
```

> 以上公式中 θ 均为**度**；代码的输入/输出是**弧度**，内部互转见第 6 节。

---

## 4. 核心推导：为什么是 "θ1/2 + θ2" 与 "−θ1/2 + θ2"

### 4.1 两个电机 = 一个"共模 / 差模"变换（理解全文件的钥匙）

每根手指的近节弯曲和侧摆**不是两个独立电机各管一个**，而是由**两个电机（电机1、电机2）协作**完成：

- **共模（common mode）**：两个电机**同方向、同幅度**转动 → 手指只弯曲、不侧摆（对应近节弯曲 θ2）。
- **差模（differential mode）**：两个电机**反方向**转动（一增一减）→ 手指只侧摆、不弯曲（对应侧摆 θ1）。

数学上，看两个公式的**和与差**，θ1 与 θ2 被**完全解耦**：

```
M1 + M2 = k·(θ1/2 + θ2) + k·(−θ1/2 + θ2) = 2k·θ2      ← 只含 θ2（共模分量）
M1 − M2 = k·(θ1/2 + θ2) − k·(−θ1/2 + θ2) = k·θ1       ← 只含 θ1（差模分量）
```

- **和**（M1+M2）中 θ1 抵消 → 和的大小只由近节弯曲决定；
- **差**（M1−M2）中 θ2 抵消 → 差的大小只由侧摆决定。

写成矩阵就是（这是正反变换能"无损往返"的数学根本）：

```
[ M1 ]   [  1/2   1 ] [ θ1 ]
[ M2 ] = k·[ −1/2   1 ] [ θ2 ]
```

2×2 矩阵可逆（行列式 = k² ≠ 0），所以正变换是"乘矩阵"，反变换就是"解二元一次方程组"，没有信息损失。

### 4.2 为什么侧摆要除以 2（θ1/2、−θ1/2）

如果不除以 2，写成 `M1 = k·(θ1 + θ2)`、`M2 = k·θ2`，那么：

```
M1 + M2 = k·(θ1 + 2θ2)    ← 和里混进了 θ1 → 纯侧摆时也会解出弯曲！
M1 − M2 = k·θ1
```

**和**不再只依赖 θ2：当只想侧摆（θ2=0）时，M1 增加 k·θ1、M2 不动，共模分量 = k·θ1/2 ≠ 0，系统会误以为你在弯曲。所以必须把 θ1 **劈成两半**，一正一负分别加到两个电机上：

```
+θ1/2 给 M1，−θ1/2 给 M2  →  共模分量 (θ1/2) + (−θ1/2) = 0  →  纯侧摆不引入弯曲
```

**除以 2 的目的 = 保证"纯侧摆时弯曲分量为零"，让 θ1、θ2 正交（互不串扰）。**

### 4.3 为什么 K12 = 4095/90

近节弯曲 θ2 的范围是 0~90°。当 θ1=0、θ2=90°（近节弯到底）：

```
M1 = M2 = k·90 = (4095/90)·90 = 4095   ← 恰好是电机满行程
```

所以 **K12 的设计意图 = "近节弯满 90° ↔ 电机走满 0~4095"**，把 90° 均匀铺满 12 位分辨率。K3、K16 同理：远节 75°、第16关节 110° 各自铺满 4095（`54.6×75 = 4095`、`37.2273×110 = 4095`）。

### 4.4 具体数字演示（务必手算一遍）

**例 1：θ1 = 10°（侧摆 10°）、θ2 = 45°（近节弯曲 45°）**，k = 45.5

```
M1 = 45.5 × (10/2 + 45) = 45.5 × 50 = 2275
M2 = 45.5 × (−10/2 + 45) = 45.5 × 40 = 1820
```

验证（用"和/差"解耦）：

```
共模: (M1+M2)/2 = (2275+1820)/2 = 2047.5 → 2047.5/45.5 = 45° = θ2 ✓
差模: M1−M2 = 455 → 455/45.5 = 10° = θ1 ✓
```

物理含义：以"弯曲 45° 的基准位置（两电机各 2047.5）"为参照，电机1 多转了 227.5 码（2275 vs 2047.5），电机2 少转了 227.5 码（1820 vs 2047.5）——**一推一拉**，手指在弯曲 45° 的基础上再向一侧摆 10°。

**例 2：θ1 = 0°（纯弯曲 45°）**

```
M1 = 45.5 × 45 = 2047.5 → int() 截断 → 2047
M2 = 45.5 × 45 = 2047.5 → int() 截断 → 2047
```

两电机完全相同 → 差模为 0 → 侧摆 0° ✓；读回 θ2 = (2047+2047)/(2×45.5) = 4094/91 ≈ **44.99°**（int 截断带来的 <0.01° 量化误差，可忽略）。

**例 3：θ1 = 10°（纯侧摆）、θ2 = 0°** —— 展示 clamp 的必要性

```
M1 = 45.5 × 5 = 227.5 → int → 227
M2 = 45.5 × (−5) = −227.5 → int → −227 → 被 _clamp 截到 0
```

M2 算出了**负位置**——12 位 PWM 根本表达不了负数。clamp 到 0 后读回：

```
θ1 = (227 − 0)/45.5 ≈ 4.99°（≠ 10°）
θ2 = (227 + 0)/91 ≈ 2.49°（≠ 0°）
```

**注意**：该模型隐含假设"θ1=θ2=0 时两电机位置都为 0"。当 θ2 < |θ1|/2 时，必有一个电机需要负位置 → 被 clamp → 侧摆/弯曲都失真。**有效工作区是 θ2 ≥ |θ1|/2**（例：10° 侧摆至少要配 5° 弯曲）。这也是为什么 GUI 侧摆滑条范围只有 ±20°、且所有预设动作都"侧摆=0"。

**例 4：极限组合 θ1 = 20°、θ2 = 90°**（同时满摆 + 满弯）

```
M1 = 45.5 × (10 + 90) = 4550 → 超上限 → clamp 到 4095（饱和）
M2 = 45.5 × (−10 + 90) = 3640（正常）
```

M1 饱和：同时"弯到底 + 摆到底"超出单电机行程，clamp 把 4550 截到 4095，电机停在物理极限而不是目标位置。

### 4.5 反变换：怎么从 (M1, M2) 解回 (θ1, θ2)

正变换是二元一次方程组：

```
M1 = k·(θ1/2 + θ2)
M2 = k·(−θ1/2 + θ2)
```

两式**相加**消去 θ1：

```
M1 + M2 = 2k·θ2  →  θ2 = (M1 + M2) / (2k)
```

两式**相减**消去 θ2：

```
M1 − M2 = k·θ1  →  θ1 = (M1 − M2) / k
```

（这正是 `motor_cmds_to_joint_angles` 第 86 / 88 行做的事。）因为正变换是"和/差解耦"的，反变换也只需"和、差"两步，不需要矩阵求逆。

### 4.6 为什么 M2 带负号（−θ1/2）—— 电机安装方向镜像

- 物理上，电机1 和电机2 安装在近节关节的**两侧**（左右各一个，像两根肌腱）。要让手指**摆向一侧**，必须"一侧电机收紧、另一侧放松"——即一增一减。
- 公式里 `M1` 带 `+θ1/2`、`M2` 带 `−θ1/2`，正是这个"一推一拉"的代数表达。**负号不是数学巧合，而是电机2 的安装方向与电机1 相反**：对电机2 而言"正转"对应的物理方向与电机1 相反，所以同样的 θ1 必须取反。
- **左右手镜像**：左手是右手的镜像。右手时"电机1 收紧 = 正侧摆"，镜像到左手就变成"电机2 收紧 = 正侧摆"。等价的操作就是**交换 M1、M2**（`hand_lr=0` 时）。交换之后，"共模对应弯曲 / 差模对应侧摆"的物理含义会互换——这就是"手型选反时滑近节实际在侧摆"的根源（见第 10 节）。

---

## 5. 逐函数逐行详解

### 5.0 文件头与导入（第 1~21 行）

```python
# -*- coding: utf-8 -*-
"""
angles2motor.py —— RY-H1(16) 关节角度 <-> 电机指令换算
...（模块 docstring：公式速查，与官方 demo 一致）
"""
from __future__ import annotations
import math
from typing import List
from .hand_config import (ANGLE_RANGE_DEG, FINGER_ORDER, K12, K3, K16, POS_MAX)
```

| 行 | 内容 | 说明 |
|---|---|---|
| 1 | `# -*- coding: utf-8 -*-` | 声明 UTF-8 源码编码（Windows 下避免中文注释乱码） |
| 2~12 | 模块 docstring | 记录公式来源（官方 demo）与四行核心公式，相当于"需求规格" |
| 14 | `from __future__ import annotations` | 让类型注解延迟求值（PEP 563），低版本 Python 也兼容 |
| 16 | `import math` | 弧度/度互转（`math.radians` / `math.degrees`） |
| 17 | `from typing import List` | 类型提示 |
| 19~21 | 从 `hand_config` 导入常量 | 全部常量来自配置单点，**本文件没有任何魔法数** |

---

### 5.1 `_clamp(v, lo=0.0, hi=POS_MAX) -> int`（第 24~25 行）

```python
def _clamp(v: float, lo: float = 0.0, hi: float = POS_MAX) -> int:
    return int(round(max(lo, min(hi, v))))
```

**用途**：把任意数值限幅到 `[lo, hi]` 并取整，**保证返回的电机指令永远落在合法区间**。

逐行：

| 表达式 | 含义 |
|---|---|
| `min(hi, v)` | 先压上限：v 超过 hi 就取 hi |
| `max(lo, ...)` | 再抬下限：低于 lo 就取 lo |
| `round(...)` | 四舍五入到最近整数。注意：Python 内置 round 是**银行家舍入**（`.5` 取偶数），对电机指令影响至多 ±1 码，可忽略 |
| `int(...)` | 确保返回 `int` 类型（round 单参本已返回 int，这里是显式保证） |
| 默认参数 | `lo=0.0`、`hi=POS_MAX=4095` → 默认行为就是"电机位置合法区间" |

**关键点**：clamp 是"**截断**"不是"缩放"——超出部分被直接砍掉，电机停在边界，绝不会收到非法指令。

---

### 5.2 `_clamp_angle_rad(v, lo_deg, hi_deg) -> float`（第 28~29 行）

```python
def _clamp_angle_rad(v: float, lo_deg: float, hi_deg: float) -> float:
    return max(math.radians(lo_deg), min(math.radians(hi_deg), v))
```

**用途**：角度**输入**限幅。输入 `v` 是弧度，范围参数是度（来自 `ANGLE_RANGE_DEG`），先把边界转成弧度再限幅。

逐行：

| 表达式 | 含义 |
|---|---|
| `math.radians(lo_deg)` / `math.radians(hi_deg)` | 边界从"度"转"弧度"（例：±20° → ±0.3491 rad） |
| `min(hi_rad, v)` / `max(lo_rad, ...)` | 与 `_clamp` 相同的限幅嵌套结构 |

**与 `_clamp` 的区别**：
- 这里是**角度域**限幅（把 MediaPipe 解算出的异常角度挡在换算之外），`_clamp` 是**位置域**限幅（保证电机指令合法）。
- 这里**不取整**，保留浮点精度——四舍五入推迟到最终生成电机指令时（`_clamp`）才做，避免中间精度损失。

---

### 5.3 `angles_to_motor_cmds(angles_rad_16, hand_lr=1) -> List[int]`（第 32~68 行）

```python
def angles_to_motor_cmds(angles_rad_16: List[float],
                         hand_lr: int = 1) -> List[int]:
    """16 关节角度（弧度，顺序 = 关节 ID 1~16）-> 16 个电机指令（0~4095）。"""
    if len(angles_rad_16) != 16:
        raise ValueError("angles_rad_16 必须包含恰好 16 个元素（关节 ID 1~16）")

    lim = list(angles_rad_16)
    for i in range(15):
        joint_in_finger = i % 3
        if joint_in_finger == 0:
            lo, hi = ANGLE_RANGE_DEG["swing"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
        elif joint_in_finger == 1:
            lo, hi = ANGLE_RANGE_DEG["prox"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
        else:
            lo, hi = ANGLE_RANGE_DEG["dist"]
            lim[i] = _clamp_angle_rad(lim[i], lo, hi)
    lo16, hi16 = ANGLE_RANGE_DEG["joint16"]
    lim[15] = _clamp_angle_rad(lim[15], lo16, hi16)

    cmds = [0] * 16
    for finger_idx, finger in enumerate(FINGER_ORDER):
        base = finger_idx * 3
        t1_deg = math.degrees(lim[base])
        t2_deg = math.degrees(lim[base + 1])
        t3_deg = math.degrees(lim[base + 2])
        cmds[base] = _clamp(int(K12 * (t1_deg / 2.0 + t2_deg)))
        cmds[base + 1] = _clamp(int(K12 * (-t1_deg / 2.0 + t2_deg)))
        cmds[base + 2] = _clamp(int(K3 * t3_deg))
    cmds[15] = _clamp(int(K16 * math.degrees(lim[15])))

    if hand_lr == 0:
        for finger_idx in range(5):
            base = finger_idx * 3
            cmds[base], cmds[base + 1] = cmds[base + 1], cmds[base]
    return cmds
```

**整体流程**：长度校验 → 角度限幅 → 逐指换算 → 左右手交换 → 返回。分五步：

**① 长度校验（35~36 行）**
- `len != 16` 直接抛 `ValueError`。防止调用方传错长度导致后续索引错位/越界；宁可快速失败，也不静默算错。

**② 角度限幅（38~51 行）**
- `lim = list(angles_rad_16)`：**拷贝**输入，后续在 `lim` 上原地替换限幅结果——**不修改调用方传入的列表**（纯函数、无副作用）。
- `for i in range(15)`：只处理前 15 个关节（索引 0~14，即关节 ID 1~15）。`joint_in_finger = i % 3` 判断关节类型：
  - `0` → 侧摆，范围 `(-20°, 20°)`
  - `1` → 近节，范围 `(0°, 90°)`
  - 其他（`2`）→ 远节，范围 `(0°, 75°)`
- 索引 15（第 16 关节）单独处理（50~51 行），范围 `(0°, 110°)`。
- 限幅之后，任何越界输入（比如视觉解算的毛刺）在进入公式前就被截回手册范围。

**③ 逐指换算（53~62 行）**
- `cmds = [0] * 16`：预分配结果列表。
- `for finger_idx, finger in enumerate(FINGER_ORDER)`：按"拇指→食指→中指→无名指→小指"遍历 5 根手指。（小细节：`finger` 变量本身没被用到，遍历只是为了拿到 `finger_idx` 序号。）
- `base = finger_idx * 3`：该指 3 个关节的起始下标（0, 3, 6, 9, 12）。
- `t1_deg / t2_deg / t3_deg`：把该指 3 个关节的弧度转成度（`math.degrees`）——因为**系数 K12/K3/K16 是按"度"标定的**。
- 三条公式逐行对应：
  - `cmds[base]   = _clamp(int(K12 * ( t1_deg/2.0 + t2_deg)))` —— 电机1：共模弯曲 + 差模侧摆的一半
  - `cmds[base+1] = _clamp(int(K12 * (−t1_deg/2.0 + t2_deg)))` —— 电机2：共模弯曲 − 差模侧摆的一半
  - `cmds[base+2] = _clamp(int(K3 * t3_deg))` —— 电机3：远节独立
- `cmds[15] = _clamp(int(K16 * math.degrees(lim[15])))`（62 行）：第 16 关节独立电机。

> **取整细节**：`int(...)` 先**截断**（向零取整，与官方 demo 一致），`_clamp` 再限幅。由于 `int()` 在 clamp **之前**执行、而 `_clamp` 内部 `round` 对整数是恒等，最终值是"截断后限幅"，与"限幅后取整"在正常范围内差异至多 ±1 码。

**④ 左右手交换（64~67 行）**
- `hand_lr == 0`（左手）时，每指交换 `cmds[base] ↔ cmds[base+1]`（电机1、电机2 的指令互换）。注意判定条件是"`== 0` 才是左手"，其他任何值都按右手处理。
- 交换发生在**全部换算完成之后**，一次性处理，逻辑清晰。
- 语法：`cmds[base], cmds[base+1] = cmds[base+1], cmds[base]` 是 Python 元组解包的原地交换。

**⑤ 返回（68 行）**
- 返回 16 个 `int`，每个都在 `[0, 4095]`，可直接交给 `hand_controller.move_joints` 逐电机下发。

---

### 5.4 `motor_cmds_to_joint_angles(cmds, hand_lr=1) -> List[float]`（第 71~92 行）

```python
def motor_cmds_to_joint_angles(cmds: List[int], hand_lr: int = 1) -> List[float]:
    """16 电机指令 -> 16 关节角度（弧度）。"""
    if len(cmds) != 16:
        raise ValueError("cmds 必须包含恰好 16 个元素")
    if hand_lr == 0:
        cmds = list(cmds)
        for finger_idx in range(5):
            base = finger_idx * 3
            cmds[base], cmds[base + 1] = cmds[base + 1], cmds[base]

    angles = [0.0] * 16
    for i in range(15):
        joint_in_finger = i % 3
        finger_base = (i // 3) * 3
        if joint_in_finger == 0:
            angles[i] = (cmds[finger_base] - cmds[finger_base + 1]) / K12
        elif joint_in_finger == 1:
            angles[i] = (cmds[finger_base] + cmds[finger_base + 1]) / (2.0 * K12)
        else:
            angles[i] = cmds[i] / K3
    angles[15] = cmds[15] / K16
    return [math.radians(a) for a in angles]
```

**用途**：正变换的逆——从 16 个电机位置（0~4095）解回 16 个关节角度（弧度）。用于 `read_joint_angles` 回读当前姿态。

**① 长度校验（73~74 行）**：同正变换，快速失败。

**② 左手先交换回来（75~79 行）**
- `if hand_lr == 0`：左手时**先把 M1/M2 换回"右手约定"**再解算。
- `cmds = list(cmds)`：**拷贝**！交换是原地修改，不拷贝会直接改写调用方传入的列表（例如 `_last_servo_info` 里收集的原始数据）。这是与正变换不同的关键细节。
- 为什么必须"先换回来"：正变换左手 = `swap(右手公式)`；反变换就必须先做 `swap⁻¹ = swap`（交换是自身的逆），再套右手解算公式——**顺序不能反**（数学证明见第 7 节）。

**③ 逐关节解算（81~91 行）**
- `for i in range(15)`：前 15 个关节。`finger_base = (i // 3) * 3` 是该指起始下标。
- 按 `i % 3` 分流：
  - `0`（侧摆）：`θ1 = (M1 − M2) / K12` —— 差模（86 行）
  - `1`（近节）：`θ2 = (M1 + M2) / (2.0 * K12)` —— 共模（88 行）
  - `2`（远节）：`θ3 = M3 / K3`（90 行）
- `angles[15] = cmds[15] / K16`（91 行）：第 16 关节。
- 注意：侧摆和近节都用该指电机1、2（`cmds[finger_base]`、`cmds[finger_base+1]`）；远节用 `cmds[i]`，即 `cmds[finger_base+2]`（该指电机3），写法不同但含义一致。

**④ 转弧度（92 行）**
- `[math.radians(a) for a in angles]`：把度转回弧度，与 `angles_to_motor_cmds` 的输入单位对齐，方便上层直接比较/显示。
- 反变换**不再 clamp**：它如实反映电机的物理位置（包括饱和后的值），让上层看到真实状态，而不是被修饰过的理想值。

---

## 6. 弧度 ↔ 度 转换一览

| 位置 | 单位 | 转换 |
|---|---|---|
| `angles_to_motor_cmds` **输入** | 弧度 | 内部 `math.degrees` 转度再套公式 |
| `angles_to_motor_cmds` **输出** | 电机码 0~4095 | 无需转换 |
| `motor_cmds_to_joint_angles` **输入** | 电机码 | 内部解算得到度 |
| `motor_cmds_to_joint_angles` **输出** | 弧度 | `math.radians` |

- 系数量纲：`K12 = 45.5 码/度`、`K3 = 54.6 码/度`、`K16 ≈ 37.23 码/度`。
- 反过来看分辨率：1 码 ≈ 0.022°（近节）、0.018°（远节）、0.027°（关节16）——远小于人手与机械误差，量化不是精度瓶颈。

---

## 7. 左右手交换的对称性（为什么反变换要"先交换再解算"）

设右手正变换为 `f`，交换操作为 `S`（`S(a,b) = (b,a)`，且 `S∘S = id`，即交换是自身的逆）：

```
右手：  M = f(θ)
左手：  M = S(f(θ))          ← 正变换：先按右手公式算，再交换
左手反：θ = f⁻¹(S(M))        ← 反变换：先交换回来，再解右手方程
```

- 正变换（64~67 行）：**先算后换**——换算完 5 指 16 码，再统一交换。
- 反变换（75~79 行）：**先换后算**——交换回右手约定，再解方程组。
- 两者互为镜像，所以正反变换天然可逆：`angles_to_motor_cmds` 的输出喂给 `motor_cmds_to_joint_angles`（同一 `hand_lr`），能还原出近似相等的角度，误差仅来自 int 截断与 clamp 饱和。
- **对称性被破坏的唯一来源是 clamp 饱和**（见第 9 节）——目标超出物理行程时信息被截断，读回必然偏离。

---

## 8. 与 `hand_controller` 的调用关系

### 8.1 下发链路：`move_joints` → `angles_to_motor_cmds` → SDK

`hand_controller.py`（428~454 行）核心片段：

```python
def move_joints(self, angles_rad_16, speed=None, max_current=None,
                hand_lr=None, control_mode=0, inter_sleep_s=0.0005):
    ...
    hlr = self.hand_lr if hand_lr is None else hand_lr              # 优先级：显式参数 > 实例属性
    cmds = angles_to_motor_cmds(list(angles_rad_16), hand_lr=hlr)   # ← 本模块正变换
    fdb = ServoDataT()
    for i, pos in enumerate(cmds):
        if control_mode == 0:
            self._lib.RyMotion_ServoMove_Mix(self.bus, i + 1, pos, speed, cur, ...)   # 0xAA 力位混合
        else:
            self._lib.RyMotion_ServoMove_Speed(self.bus, i + 1, pos, speed, cur, ...) # 0xA1 速度
        ...
```

- **电机 ID = 列表下标 + 1**：`cmds[0]` → 电机 1，`cmds[15]` → 电机 16，与 `FINGER_MOTOR_IDS`（拇指 1-3、食指 4-6…）一一对应。
- `hand_lr` 三态：调用方不传（`None`）→ 用控制器实例属性 `self.hand_lr`（`__init__` 默认 1，`set_hand_lr(0/1)` 运行时可切换）。
- 上层调用方：`open_hand()`（全 0°）、`close_hand()`（握拳预设）、`relax()`（放松预设）都通过 `move_joints` 走这条链路；GUI 滑条手动控制与动作模仿模式最终也汇聚到这里。

### 8.2 回读链路：`read_joint_angles` → `motor_cmds_to_joint_angles`

`hand_controller.py`（467~475 行）：

```python
def read_joint_angles(self, hand_lr=None):
    hlr = self.hand_lr if hand_lr is None else hand_lr
    cmds = []
    for mid in range(1, 17):
        info = self.get_servo_info(mid, timeout_ms=100)   # SDK 同步读电机位置（12 位，0~4095）
        cmds.append(info.position if info else 0)         # 无应答的电机按 0 处理
    return motor_cmds_to_joint_angles(cmds, hand_lr=hlr)  # ← 本模块反变换
```

- 电机位置来自 `get_servo_info` 解析出的 `position` 字段；返回弧度列表，可与下发前的目标角度对比（显示当前姿态/校验）。

### 8.3 其他调用点

- `hand/__init__.py`：导出 `angles_to_motor_cmds` / `motor_cmds_to_joint_angles`，支持 `from hand import angles_to_motor_cmds`。
- `selfcheck.py`（129~140 行）、`apps/test_all.py`（125~128 行）：**不接硬件**做换算自检——张开/握拳/左右手各算一遍，检查输出是否落在 0~4095。

---

## 9. 数值安全（为什么 clamp 能保护电机）

### 9.1 三道防线

| 防线 | 位置 | 作用 |
|---|---|---|
| ① 角度限幅 | `_clamp_angle_rad`（本文件） | 输入角度先截回手册范围（±20° / 0~90° / 0~75° / 0~110°），把视觉毛刺挡在换算之外 |
| ② 位置限幅 | `_clamp`（本文件） | 每个电机指令强制落在 [0, 4095] |
| ③ 控制器兜底 | `hand_controller.move_motor`（418 行 `max(0, min(POS_MAX, int(position)))`） | 单电机接口再 clamp 一次，双保险 |

### 9.2 为什么超出 0~4095 会损坏电机

- 位置指令是 **12 位 PWM 值**：0 = 行程一端，4095 = 另一端，**硬件上不存在负数或 >4095 的位置**。
- 若把越界值直接下发（绕过 clamp），SDK/驱动对非法行程的解释不确定：轻则指令无效，重则电机朝极限硬顶、堵转、触发过流/堵转保护（故障码 5/8），长期可能损伤减速箱。
- 常见越界场景（都被 clamp 挡住）：
  1. 视觉解算瞬间毛刺（如 θ2=95°）；
  2. 组合角度超行程（θ2=90° + θ1=20° → M1=4550）；
  3. 负数（θ2 < |θ1|/2 → M2 < 0）。

### 9.3 clamp 的代价：饱和失真（读回 ≠ 目标）

clamp 是**截断**：一旦饱和，目标信息丢失。表现：
- 指令停在 4095/0，电机停在物理极限；
- `read_joint_angles` 读回的 θ 与目标不一致（例 4：想"弯 90° + 摆 20°"，读回只有弯满，侧摆被吞掉一部分）。
- 这是**物理极限**，不是 bug：正确做法是让上层（GUI 滑条范围、`bend_gain/bend_scale`、`postprocess` 限速）把角度控制在手册范围内。

---

## 10. 常见问题（现象 → 根因 → 处理）

| 现象 | 根因 | 处理 |
|---|---|---|
| **滑"近节"滑条，实际动的是"侧摆"** | **手型选反**：左右手电机 1/2 镜像安装，交换 M1/M2 后"共模=弯曲 / 差模=侧摆"的物理含义互换——你发的共模指令被硬件当成差模执行 | GUI 切"左手/右手"（或 `hand.set_hand_lr(0/1)`），**已连接也立即生效**，无需重启 |
| 侧摆只有单边能动 / 一摆就弯 | θ2 < \|θ1\|/2 时 M1 或 M2 需要负位置 → 被 clamp 截断 | 侧摆幅度不要超过近节弯曲的一半；或先弯曲再侧摆 |
| 读回角度与设定差 1° 以内 | int 截断的量化误差（例：45° → 2047 而非 2048） | 正常现象，无需处理 |
| 读回角度明显不对（差很多） | clamp 饱和失真（目标超出物理行程） | 减小幅度；检查输入角度是否越界 |
| 16 号电机"幅度小" | 不是本模块问题：电机**行程**配置偏小或未回零（status=11） | `hand.check_joint16_stroke()`；`hand.set_stroke(16, 4095)` 或执行回零 |
| `angles_to_motor_cmds` 抛 ValueError | 传入长度 ≠ 16 | 检查上游是否补齐 16 个关节角（无手势时可能缺数据） |
| 全部电机指令都是 0 | 输入角度全为 0（手势未识别/未启动模仿） | 先确认姿态估计有输出 |

---

## 11. 附：30 秒自测（不接硬件）

```python
import math
from hand import angles_to_motor_cmds, motor_cmds_to_joint_angles

# 例1：拇指 侧摆 10°、近节 45°，其余 0
angles = [math.radians(10), math.radians(45)] + [0.0] * 14
cmds = angles_to_motor_cmds(angles, hand_lr=1)
print(cmds[:3])                        # 期望 ≈ [2275, 1820, 0]

# 左右手对称性：左手 = 右手交换 M1/M2
cmds_l = angles_to_motor_cmds(angles, hand_lr=0)
print(cmds_l[:2] == [cmds[1], cmds[0]])  # True

# 正反变换互逆（未饱和时）
back = motor_cmds_to_joint_angles(cmds, hand_lr=1)
print([round(math.degrees(a), 3) for a in back[:2]])   # ≈ [10.0, 45.0]

# 越界保护：任何输入都不会产生负数或 >4095 的指令
bad = angles_to_motor_cmds([math.radians(200)] * 16)
print(min(bad) >= 0 and max(bad) <= 4095)   # True
```

---

*本文与 `docs/代码详解/00_总览详解.md` 配套阅读；公式与官方 demo `update_motor_positions` 一致，如厂家资料更新以厂家最新文档为准。*
