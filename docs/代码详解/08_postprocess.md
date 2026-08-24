# `vision/postprocess.py` 代码详解 —— 关节角精度后处理（中值 + One Euro + 差分限速）

> 所属系统：睿研 RY-H1(16) 灵巧手视觉动作模仿系统（Windows 版）
> 模块角色：**关节角精度后处理**，位于视觉管线的最末端（`HandPoseEstimator` 输出 16 路关节角之后、下发灵巧手舵机之前）。
> 依据文档：《控制精度提升方案.md》**阶段 1**。
> 源文件：`rycan_hand_windows/vision/postprocess.py`（304 行，含 `__main__` 自测）。
> 读取本文前建议先读：《控制精度提升方案.md》阶段 1 部分。

---

## 0. 目录

1. [文件总览：解决什么、放在哪](#1-文件总览)
2. [设计背景：三大精度痛点与阶段 1 方案](#2-设计背景)
3. [关键演进（修改 8）：从"整帧丢弃"到"方向一致性 + 中值替代"](#3-关键演进修改-8)
4. [模块结构总览](#4-模块结构总览)
5. [`OneEuroFilter` 类详解](#5-oneeurofilter-类详解)
6. [`JointAnglePostProcess` 类详解](#6-jointanglepostprocess-类详解)
7. [方向一致性检测：数值示例](#7-方向一致性检测数值示例)
8. ["中值替代"与"整帧丢弃"的本质区别](#8-中值替代与整帧丢弃的本质区别)
9. [`update()` 数据流水线（ASCII 图）](#9-update-数据流水线ascii-图)
10. [自测部分（`__main__`）：5 个回归测试](#10-自测部分__main__)
11. [参数调优指南（GUI 滑条效果）](#11-参数调优指南)
12. [与 GUI 的接线（`PARAM_CONFIG` → `update_params`）](#12-与-gui-的接线)

---

## 1. 文件总览

本文件实现**单帧增量式**的关节角后处理链。`HandPoseEstimator` 通过 MediaPipe + 深度相机估计出每帧 16 个关节角（度），但原始角度存在三类问题：

| 痛点 | 表现 | 成因 | 本模块对策 |
|---|---|---|---|
| **抖动** | 静止时角度小幅高频抖动 | MediaPipe 关键点噪声 | ① 中值滤波（抗离群点）② One Euro 低速强平滑 |
| **幅度不稳** | 动作幅度忽大忽小 | 深度/关键点估计波动 | 中值滤波 + One Euro 速度自适应 |
| **突跳** | 单帧角度猛跳（如 +50°） | MediaPipe 偶发错检、手指交叉误判 | 方向一致性异常检测 + 中值替代 + 差分限幅 |

**对外接口只有一个核心类**：

```python
from vision.postprocess import JointAnglePostProcess

pp = JointAnglePostProcess(joint_num=16, median_n=5,
                           min_cutoff=0.5, beta=0.02,
                           max_delta_deg=8.0, abduct_max_delta_deg=3.0,
                           max_jump_deg=40.0, jump_ratio_threshold=3.0)
out_deg = pp.update(angles_deg)   # 每帧调用一次，返回后处理后的 16 路角度(度)
```

`JointAnglePostProcess` 内部为**每个关节**维护三样东西：

1. 一个**中值滤波窗口**（`collections.deque`，长度 `median_n`）；
2. 一个 **One Euro 滤波器实例**（`OneEuroFilter`，逐通道独立）；
3. 一个**上一帧输出值** `_prev_deg[i]`（用于差分限速与异常跳变检测）。

外加一套**稳定性统计指标**（`jitter_std` / `last_max_jump` / `dropped_frames` / `drop_rate_pct`），供 GUI 实时显示。

---

## 2. 设计背景

《控制精度提升方案.md》阶段 1 定了三件事，与本文件一一对应：

1. **中值滤波** —— 每通道维护长度为 `median_n` 的滑动窗口，取窗口**中位数**作为该帧代表值。相比均值滤波，中值对"偶发异常帧/离群点"几乎免疫：窗口 5 个样本里混进 1 个 +50° 的野值，中位数仍是正常值。
2. **One Euro 滤波** —— 速度自适应的指数平滑。慢速运动时截止频率低 → 强平滑压噪；快速运动时截止频率自动升高 → 低延迟跟手。解决"平滑 vs 跟手"这对矛盾。
3. **差分限幅** —— 每帧输出相对上一帧的角度变化不得超过上限（`max_delta_deg`），从**源头保证**任何一帧下发到舵机的角度变化是安全的，物理上不可能出现猛跳。

三者串成一条链：`异常检测 → 中值 → One Euro → 差分限速`。

---

## 3. 关键演进（修改 8）

> 这是理解本文件**最重要**的一段历史，也是自测部分存在的理由。

### 3.1 旧版方案：整帧跳变检测（有缺陷）

旧版逻辑：计算 16 个关节相对上一帧的最大跳变 `jump_max`，只要 `jump_max > 20°`，就认为"这一帧坏了"，**整帧丢弃** —— 直接返回上一帧的输出，16 个关节全部冻结。

**缺陷**：真实的快速握拳（0° → 70°，每帧 +5° 左右、四指同时变化）在某些帧里某一关节的瞬时跳变可能超过 20°。此时旧版把**真实运动误判为异常帧**，整帧丢弃 → 输出冻结在上一帧 → 灵巧手**卡住不动**，直到跳变变小才恢复。握拳越快，越容易卡。

### 3.2 新版方案：方向一致性 + 中值替代 + 深度辅助豁免

新版三处关键改动：

1. **方向一致性异常检测**：异常与否不由"跳变绝对值"单独决定，而由"跳变是否孤立"决定：
   - 取全部通道跳变的最大值 `jump_max` 与**中位数** `jump_med`；
   - 只有 **`jump_max > max_jump_deg` 且 `jump_max > jump_ratio_threshold × jump_med`** 才判异常。
   - 真实握拳时四指**协调变化**：所有通道跳变都大，`jump_med` 也大 → `jump_max / jump_med ≈ 1`，不满足比值条件 → **不判异常**。
   - 只有"孤立单指突变"（某关节跳变远大于其它关节）才判异常 → 正是 MediaPipe 偶发错检的形状。
2. **用中值替代，不整帧丢弃**：中值滤波对每个通道**无条件常开**（第 4 节会说明），异常通道的野值自然被窗口内其它正常样本的中位数"替代"掉；其它通道照常输出新值。因此即使某帧被判异常，**输出仍是新值、仍在运动**，不会冻结 → 不卡手。
3. **深度辅助豁免**：`update()` 新增可选参数 `fist_confidence`（来自深度相机的握拳置信度）。当 `fist_confidence ≥ 0.6` 时，**完全跳过异常判定**（不计数、不标记），因为深度相机已经确认真实握拳 —— 此时角度跳变大是事实，绝不卡住、绝不错杀。
4. **分通道限速**：拇指内外展（关节索引 15）运动范围大且极易被深度估错，单独使用更小的限速 `abduct_max_delta_deg`（默认 3.0°/帧），其它关节用 `max_delta_deg`（默认 8.0°/帧）。防内外展"啪"地跳变。

修改 8 的回归验证完全落在 `__main__` 的 5 个自测上（见第 10 节）：测 2 验证"孤立异常仍会被识别"，测 3 验证"真实握拳不冻结"，测 5 验证"深度确认后绝不误判"。这三个测试就是防止旧 bug 复活的守门员。

---

## 4. 模块结构总览

```
postprocess.py
├── 常量与导入（math / time / deque / List）
├── class OneEuroFilter          # 1€ 滤波器（逐通道实例）
│   ├── __init__(min_cutoff, beta, d_cutoff)
│   ├── @staticmethod _alpha(cutoff, dt)   # 离散低通系数推导
│   └── filter(x, t) → x_hat              # 速度估计 + 位置平滑
└── class JointAnglePostProcess  # 后处理链（核心）
    ├── ABDUCT_IDX = 15          # 拇指内外展关节索引
    ├── __init__(joint_num, median_n, min_cutoff, beta,
    │             max_delta_deg, abduct_max_delta_deg,
    │             max_jump_deg, jump_ratio_threshold)
    ├── reset()                  # 清空全部状态，保留滤波参数
    ├── update_params(...)       # 运行时热更新参数（GUI 滑条）
    ├── update(angles_deg, t, fist_confidence) → List[float]
    │     ├── 0) 方向一致性 + 深度辅助 异常检测
    │     └── 逐通道：中值 → One Euro → 分通道限速
    ├── get_stats() → dict       # 稳定性指标（GUI 显示）
    └── __main__ 自测（5 个回归测试）
```

---

## 5. `OneEuroFilter` 类详解

**来源**：Casiez, Roussel & Vogel, *"1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in Interactive Systems"*, UIST 2012。

### 5.1 构造参数

```python
def __init__(self, min_cutoff: float = 0.5, beta: float = 0.01,
             d_cutoff: float = 1.0):
```

| 参数 | 默认值 | 含义 |
|---|---|---|
| `min_cutoff` | 0.5 | 最小截止频率（Hz）。**越小越平滑**：静止/慢速时滤波越重。 |
| `beta` | 0.01 | 速度自适应系数。**越大越跟手**：速度越快，截止频率抬得越高。 |
| `d_cutoff` | 1.0 | 速度估计自身的平滑截止频率。控制"速度有多稳"，一般不动。 |

状态变量：`_x_prev`（上一帧平滑值）、`_dx_prev`（上一帧平滑速度）、`_t_prev`（上一帧时间戳）。三个初始为 `None`，首帧填充。

### 5.2 `_alpha` 静态方法：离散低通系数的推导

```python
@staticmethod
def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * 3.141592653589793 * max(cutoff, 1e-3))
    return 1.0 / (1.0 + tau / max(dt, 1e-6))
```

推导链条（一阶 RC 低通滤波的离散化）：

1. 一阶低通滤波器的**时间常数**与**截止频率**的关系：
   `τ = 1 / (2π · fc)`
   即代码第一行：`tau = 1 / (2π · cutoff)`。`max(cutoff, 1e-3)` 防止 cutoff=0 时除零。
2. 对连续一阶系统做**指数平滑离散化**（等价于一阶保持离散化），平滑系数为：
   `α = 1 / (1 + τ / Δt)`
   其中 `Δt` 是采样间隔（`dt`）。`max(dt, 1e-6)` 防除零。
3. 代入 τ 得完整公式：
   `α = 1 / (1 + 1 / (2π · fc · Δt))`

**物理直觉**：`fc` 越高（截止频率高）→ `τ` 越小 → `α` 越接近 1 → 新样本权重越大 → 越"跟手"（保留高频、延迟低）；`fc` 越低 → `α` 越小 → 输出越依赖历史 → 越"平滑"（滤掉高频噪声）。`dt` 越大（帧率越低）→ `α` 越小 → 平滑更强，因为每帧间隔长、变化量大。

### 5.3 `filter(x, t)`：速度估计 + 位置平滑的状态更新

```python
def filter(self, x: float, t: float) -> float:
    if self._x_prev is None:                 # 首帧：初始化并原样返回
        self._x_prev = x
        self._dx_prev = 0.0
        self._t_prev = t
        return x
    dt = max(t - self._t_prev, 1e-4)         # 采样间隔（下限 0.1ms）
    dx = (x - self._x_prev) / dt             # ① 原始速度估计（一阶差分）
    a_d = self._alpha(self.d_cutoff, dt)     # ② 速度低通系数
    dx_hat = a_d * dx + (1 - a_d) * self._dx_prev   # ③ 速度指数平滑
    cutoff = self.min_cutoff + self.beta * abs(dx_hat)  # ④ 自适应截止频率
    a = self._alpha(cutoff, dt)              # ⑤ 位置低通系数
    x_hat = a * x + (1 - a) * self._x_prev   # ⑥ 位置指数平滑
    self._x_prev = x_hat                     # ⑦ 状态推进
    self._dx_prev = dx_hat
    self._t_prev = t
    return x_hat
```

逐步解读：

- **① 原始速度** `dx`：当前帧观测与上一帧平滑值之差除以时间间隔，得到"这一帧到底动了多快"。注意用的是上一帧的**平滑值** `_x_prev` 而非原始值，避免把噪声当速度。
- **②③ 速度平滑** `dx_hat`：原始速度本身是噪声很大的差分信号，先用固定系数 `a_d`（由 `d_cutoff` 决定）做指数平滑：`dx_hat = a_d·dx + (1-a_d)·dx_hat_prev`。这是标准的 `新值 = α·当前观测 + (1-α)·历史` 递推。`d_cutoff` 越小 → `a_d` 越小 → 速度越"钝"，速度估计越稳定但反应越慢。
- **④ 自适应截止频率**：`cutoff = min_cutoff + beta·|dx_hat|`。这是 One Euro 的**核心思想**：速度越快（`|dx_hat|` 大），截止频率越高，滤波器放行更多高频成分 → 快速运动低延迟跟手；速度越慢（接近静止），截止频率趋近 `min_cutoff` → 强平滑压住抖动。
- **⑤⑥ 位置平滑**：用这个自适应 `cutoff` 算出系数 `a`，再做一次指数平滑得到 `x_hat`。
- **⑦ 状态推进**：把 `x_hat` 和 `dx_hat` 存回去，作为下一帧的"历史"。**指数平滑是无限冲激响应（IIR）滤波器**——每个历史样本的影响按 `(1-a)` 的幂指数衰减，永不彻底清零，所以没有"窗口长度"概念，输出是连续轨迹，不会像滑窗类滤波器那样出现台阶。

**一句话总结**：`filter` 就是"先估速、速度平滑、按速度调低通强度、再平滑位置"的四个递推步。

---

## 6. `JointAnglePostProcess` 类详解

### 6.1 类常量

```python
ABDUCT_IDX = 15   # 拇指内外展关节索引（16 关节模型中索引 15）
```

RY-H1(16) 的 16 路关节中，索引 15 是拇指**内收/外展**（abduct/adduct）关节。它运动范围大（0~110°）、深度估计易错，所以单独配更严的限速。

> 注意：`postprocess.py` 中注释写"关节16"，指的是"第 16 个关节"（1 起始编号），代码里索引是 `15`（0 起始）。两者指同一关节。

### 6.2 `__init__`：每个参数的含义与默认值

```python
def __init__(self, joint_num: int = 16, median_n: int = 5,
             min_cutoff: float = 0.5, beta: float = 0.02,
             max_delta_deg: float = 8.0,
             abduct_max_delta_deg: float = 3.0,
             max_jump_deg: float = 40.0,
             jump_ratio_threshold: float = 3.0):
```

| 参数 | 默认值 | 含义 | 归属环节 |
|---|---|---|---|
| `joint_num` | 16 | 关节数（RY-H1(16) 为 16）。决定所有逐通道容器长度。 | 配置 |
| `median_n` | 5 | 中值滤波窗口长度（帧）。窗口越大抗野值越强、滞后越大。 | 中值滤波 |
| `min_cutoff` | 0.5 | One Euro 最小截止频率（Hz）。越小越平滑。 | One Euro |
| `beta` | 0.02 | One Euro 速度自适应系数。越大越跟手。 | One Euro |
| `max_delta_deg` | 8.0 | 普通关节每帧最大角度变化（°/帧）。 | 差分限速 |
| `abduct_max_delta_deg` | 3.0 | 拇指内外展（索引 15）单独限速（°/帧）。 | 差分限速 |
| `max_jump_deg` | 40.0 | 判"异常"的**绝对**跳变阈值（°）。单帧跳变超过它才可能判异常。 | 异常检测 |
| `jump_ratio_threshold` | 3.0 | 判"异常"的**相对**比值阈值。最大跳变必须 > 该倍数 × 中位跳变。 | 异常检测 |

**初始化动作**：

```python
self.history = [deque(maxlen=self.median_n) for _ in range(self.n)]  # 每通道一个中值窗口
self.euro = [OneEuroFilter(min_cutoff, beta) for _ in range(self.n)]  # 每通道一个 1€ 滤波器
self._prev_deg = [0.0] * self.n    # 上一帧输出（限速 + 异常检测基准）
self._last_out = [0.0] * self.n    # 上一帧输出（抖动统计基准）
self._jitter_history = deque(maxlen=60)  # 近 60 帧的帧间最大变化（抖动样本）
self.jitter_std = 0.0              # 当前抖动标准差（度）
self.last_max_jump = 0.0           # 最近一帧的最大跳变（度）
self.dropped_frames = 0            # 被判为异常（被抑制）的帧计数
self.total_frames = 0              # 累计处理帧数（丢弃率分母）
```

细节：`deque(maxlen=median_n)` 是**定长环形缓冲**，满了自动挤掉最老样本 —— 天然实现滑动窗口，且 `append` 是 O(1)。`_prev_deg` 初始为 0，意味着第一帧的"跳变"是相对 0 算的，这也是异常检测需要 `total_frames > 3` 守卫的原因（见 6.5）。

### 6.3 `reset()`：复位全部状态

```python
def reset(self):
    self.history = [deque(maxlen=self.median_n) for _ in range(self.n)]
    self._prev_deg = [0.0] * self.n
    self._last_out = [0.0] * self.n
    mc = self.euro[0].min_cutoff if self.euro else 0.5
    bt = self.euro[0].beta if self.euro else 0.02
    self.euro = [OneEuroFilter(mc, bt) for _ in range(self.n)]
    self._jitter_history.clear()
    self.jitter_std = 0.0
    self.dropped_frames = 0
    self.total_frames = 0
```

- 清空所有**运行状态**（中值窗口、上一帧值、1€ 内部状态、统计量）。
- **保留滤波参数**：从旧 `euro[0]` 里取出当前 `min_cutoff` / `beta`，用它们重建新滤波器 —— 这样 GUI 调过参数后再 reset，参数不会丢。
- 典型调用时机：手部重新入画 / 重新连接灵巧手 / 用户点击"复位"。

### 6.4 `update_params()`：运行时热更新（GUI 滑条入口）

```python
def update_params(self, min_cutoff=None, beta=None,
                  max_delta_deg=None, abduct_max_delta_deg=None,
                  max_jump_deg=None, jump_ratio_threshold=None):
```

- 所有参数可选：传 `None` 表示"本次不改"。
- `min_cutoff` / `beta` 是**逐通道**的：遍历 `self.euro`，给**每个** One Euro 实例都改。因为它们是对象属性而非局部量，直接赋值即生效，下一帧就用新参数。
- 其余四个是**类级标量**，直接覆盖。
- 该函数**不 reset**：参数热更新不打断滤波状态，滑条拖动时不会闪跳。

### 6.5 `update()`：核心流水线

```python
def update(self, angles_deg: List[float],
           t: float | None = None,
           fist_confidence: float | None = None) -> List[float]:
```

**输入**：`angles_deg` 16 路原始关节角（度）；`t` 可选时间戳（默认 `time.time()`，自测里显式传入模拟时间保证确定性）；`fist_confidence` 可选深度辅助握拳置信度（0~1）。
**输出**：16 路后处理角度（度），长度与输入一致。

#### 第 0 步：方向一致性 + 深度辅助 异常检测

```python
jumps = [abs(float(angles_deg[i]) - self._prev_deg[i]) for i in range(self.n)]
jump_max = max(jumps) if jumps else 0.0
jump_sorted = sorted(jumps)
jump_med = jump_sorted[len(jump_sorted) // 2] if jump_sorted else 0.0
self.last_max_jump = jump_max

depth_confirms_fist = (fist_confidence is not None and fist_confidence >= 0.6)
abnormal = False
if not depth_confirms_fist:
    if (jump_max > self.max_jump and self.total_frames > 3
            and jump_max > self.jump_ratio * max(jump_med, 1e-3)):
        abnormal = True
        self.dropped_frames += 1
```

- **跳变向量**：每个关节相对"上一帧输出" `_prev_deg[i]` 的绝对差。注意基准是**输出**（已限速）而非上一帧原始输入，保证检测基于真实下发轨迹。
- **`jump_max`**：最大跳变；**`jump_med`**：跳变排序后的中位数（`len//2` 取下中位，16 通道时取第 9 小的值）。`jump_med` 刻画"大多数关节在动多快"。
- **判异常的三重条件（AND）**：
  1. `jump_max > max_jump`（40°）—— 绝对幅度确实夸张；
  2. `total_frames > 3` —— 前 3 帧不判（`_prev_deg` 从 0 起步，手刚入画的第一帧天然有"巨跳"，且中值窗口还没填满）；
  3. `jump_max > jump_ratio × max(jump_med, 1e-3)` —— **方向一致性**：最大跳变必须是中位跳变的 3 倍以上，即"孤立单指突变"，而不是全体协调运动。
- **深度辅助豁免**：`fist_confidence ≥ 0.6` 时整段跳过（`abnormal` 保持 False），握拳无论如何不计数。`max(jump_med, 1e-3)` 防 jump_med=0 时除零/误判。

> ⚠️ **实现细节（重要）**：当前代码里 `abnormal` 标志**只影响 `dropped_frames` 统计**，不改变下面的数据流分支 —— 中值滤波对每个通道**无条件执行**。也就是说，"中值替代"是**常开的机制**（任何一帧的野值都会被窗口内其它正常样本的中位数顶掉），异常检测负责的是"识别并记账"（供 `drop_rate_pct` 统计和 GUI 展示）。旧版"整帧丢弃→返回上一帧"的**分支逻辑已完全删除**，因此数据流上不存在"卡住"的可能（详见第 8 节）。

#### 逐通道：中值 → One Euro → 分通道限速

```python
out = []
for i in range(self.n):
    # 1) 中值滤波（去单通道毛刺）
    self.history[i].append(float(angles_deg[i]))
    vals = sorted(self.history[i])
    med = vals[len(vals) // 2]

    # 2) One Euro 平滑（异常通道同样走中值→平滑，保持运动趋势）
    sm = self.euro[i].filter(med, t)

    # 3) 分通道差分限速：内外展(关节16)单独更小限速，防跳变
    if i == self.ABDUCT_IDX:
        lim = self.abduct_max_delta
    else:
        lim = self.max_delta
    d = sm - self._prev_deg[i]
    if abs(d) > lim:
        sm = self._prev_deg[i] + lim * (1.0 if d > 0 else -1.0)
    self._prev_deg[i] = sm
    out.append(sm)
```

1. **中值滤波**：把当前帧原始值塞进该通道的窗口，排序后取 `vals[len//2]`（`median_n=5` 时取第 3 个，即正中间）。窗口里 1 个野值 + 4 个正常值时，中位数≈正常值 → 野值被"替代"。这是修改 8 里"用中值替代而非整帧丢弃"的落地点。
2. **One Euro 平滑**：对中值结果再过一遍速度自适应平滑。**注意异常通道也一样走这里** —— 被替代后的值接着被平滑，保持运动趋势连续，不会因为被"识别为异常"而冻结。
3. **分通道限速**：内外展（`i == ABDUCT_IDX`）用 `abduct_max_delta`，其它用 `max_delta`。若 One Euro 输出相对上一帧输出超限，则**钳制**到 `_prev_deg[i] ± lim`（保持符号方向）。这是**硬性安全网**：任何一帧下发到舵机的角度变化都不可能超过限速。
4. 更新 `_prev_deg[i] = sm`，为下一帧的限速与异常检测提供基准。

#### 稳定性指标（每帧更新）

```python
frame_jitter = max(abs(out[i] - self._last_out[i]) for i in range(self.n))
self._jitter_history.append(frame_jitter)
if len(self._jitter_history) >= 5:
    vals = list(self._jitter_history)
    m = sum(vals) / len(vals)
    self.jitter_std = math.sqrt(
        sum((x - m) ** 2 for x in vals) / len(vals))
self._last_out = out
return out
```

- `frame_jitter`：本帧输出与上一帧输出的**最大绝对差**（16 路取 max）——"这一帧整体动了多少"，静止时就是抖动幅度。
- 近 60 帧的 `frame_jitter` 存入环形缓冲，攒满 5 帧后计算**标准差** `jitter_std`。标准差衡量"帧间变化量的离散程度"：静止时理想为 0，越小越稳。
- `_last_out = out` 推进基准。最后返回 `out`。

### 6.6 `get_stats()`：稳定性指标

```python
drop_rate = (self.dropped_frames / self.total_frames * 100
             if self.total_frames else 0.0)
return {
    "jitter_std_deg": self.jitter_std,
    "last_max_jump_deg": self.last_max_jump,
    "dropped_frames": self.dropped_frames,
    "drop_rate_pct": drop_rate,
}
```

| 键 | 计算方式 | 含义 |
|---|---|---|
| `jitter_std_deg` | 近 60 帧 `frame_jitter` 的标准差 | 帧间抖动标准差，越小越稳（静止时≈0） |
| `last_max_jump_deg` | 最近一帧 `jump_max` | 最近一帧最大跳变，用于观察异常 |
| `dropped_frames` | 累计计数 | 被判异常（被抑制）的帧数 |
| `drop_rate_pct` | `dropped / total × 100`（total=0 时返回 0） | 异常帧占比，>1% 说明视觉估计不稳定 |

---

## 7. 方向一致性检测：数值示例

设 `max_jump_deg = 40.0`、`jump_ratio_threshold = 3.0`，4 通道模型。

### 示例 A：真实握拳（协调变化）→ 正常

四指同时 0°→70°，每帧每通道 **+5°**，叠加 ±2° 噪声：

```
跳变向量 jumps = [5, 5, 5, 5]   （±2° 噪声下约为 [5±2]×4，这里用理想值）
jump_max  = 5
排序后     = [5, 5, 5, 5]
jump_med  = 5          （4//2=2，取第 3 小的值）
比值      = 5 / max(5, 1e-3) = 1.0
```

判定：`jump_max(5) > max_jump(40)` **不成立** → 正常，不判异常。
即使瞬时跳变大（比如某一帧四指都 +45°，`jump_max=45 > 40` 成立），比值 `45/45 = 1 < 3` 也不成立 → 仍正常。**方向一致性兜住了协调快运动**。

### 示例 B：孤立单指突变 → 异常

静止 30°，某一帧仅第 3 通道被 MediaPipe 错检为 +50°（其余通道 ±2° 噪声）：

```
跳变向量 jumps = [2, 2, 52, 2]
jump_max  = 52
排序后     = [2, 2, 2, 52]
jump_med  = 2          （4//2=2，取第 3 小，即 2）
比值      = 52 / max(2, 1e-3) = 26.0
```

判定：`jump_max(52) > 40` ✅ 且 `52 > 3 × 2 = 6` ✅（且 `total_frames > 3`）→ **异常**，`dropped_frames += 1`。
该帧第 3 通道进入中值窗口后，窗口内其它 4 个正常值（≈30）把中位数顶在 ≈30 → 输出仍约 30°，其余通道照常输出。**不冻结、不猛跳**。

> 一句话：**比值 ≈ 1 是"大家都在动"（正常运动），比值 ≫ 1 是"只有它在动"（错检野值）**。这就是方向一致性检测的全部直觉。

---

## 8. "中值替代"与"整帧丢弃"的本质区别

| 维度 | 旧版：整帧丢弃 | 新版：中值替代 |
|---|---|---|
| 触发后做什么 | 16 路输出**全部**回退为上一帧值 | 每路照常走"中值→One Euro→限速"，野值通道的值被窗口**中位数**顶掉 |
| 其它关节 | 被连带冻结 | 不受影响，正常输出新值 |
| 运动连续性 | 输出出现"台阶/停顿"，握拳时表现为**卡死** | 输出始终是新鲜平滑轨迹，只是异常通道的值被"拉回正常水平" |
| 数据流分支 | 存在"返回上一帧"的旁路 | **无旁路**，中值滤波常开，异常检测只记账 |
| 卡手风险 | 高（握拳被误判 → 每帧都冻结） | 结构上不可能（永远输出新值） |

**为什么新版不卡手**：卡手的本质是"输出长时间不变"。新版里每一帧、每一路都必然产出新值（要么正常平滑、要么被中值替代），输出序列永远不会出现连续相同的冻结帧；即使最坏情况连续多帧被判异常，中值替代 + 限速也只会让异常通道"缓一缓"，其它手指继续运动，握拳轨迹照常推进。自测 3 正是用"冻结帧数 ≤ 3"来守住这条底线。

---

## 9. `update()` 数据流水线（ASCII 图）

```
                 ┌────────────────────────────────────────────────────────┐
                 │                    update(angles_deg,                   │
                 │                     t?, fist_confidence?)              │
                 └──────────────────────┬─────────────────────────────────┘
                                        │ 校验长度、取时间戳、total_frames++
                                        ▼
              ┌───────────────────────────────────────────────────┐
              │ 第0步 异常检测（方向一致性 + 深度辅助）             │
              │  jumps[i] = |angles[i] - _prev_deg[i]|            │
              │  jump_max = max(jumps)                            │
              │  jump_med = 中位数(jumps)                          │
              │  last_max_jump = jump_max                          │
              │                                                   │
              │  fist_confidence ≥ 0.6 ? ──是──▶ 不判异常（豁免）   │
              │        │否                                        │
              │        ▼                                          │
              │  jump_max > max_jump(40°)                         │
              │  且 total_frames > 3                              │
              │  且 jump_max > 3 × jump_med  ? ──是──▶ abnormal   │
              │        │否                              │         │
              │     正常帧                       dropped_frames++  │
              └───────────────────────┬───────────────────────────┘
                                      │  （abnormal 只记账，不分支数据流）
                                      ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  逐通道 for i in 0..15（每路独立，互不影响）                      │
        │                                                                 │
        │  ① 中值滤波：history[i].append(raw_i) → 排序 → 取中间值 med      │
        │        （孤立野值被窗口内其它正常样本的中位数“替代”）              │
        │              │                                                │
        │              ▼                                                │
        │  ② One Euro：sm = euro[i].filter(med, t)                      │
        │        （低速强平滑 / 高速自适应跟手）                            │
        │              │                                                │
        │              ▼                                                │
        │  ③ 分通道限速：                                                │
        │        i == 15(内外展) ? lim = abduct_max_delta(3.0°/帧)        │
        │                     : lim = max_delta(8.0°/帧)                  │
        │        d = sm - _prev_deg[i]                                   │
        │        |d| > lim ? sm = _prev_deg[i] + lim·sign(d)   ← 硬钳制  │
        │        _prev_deg[i] = sm                                       │
        └────────────────────────┬────────────────────────────────────────┘
                                 │  16 路输出汇合
                                 ▼
              ┌────────────────────────────────────────────┐
              │ 稳定性统计：                                │
              │  frame_jitter = max|out - _last_out|        │
              │  jitter_std  ← 近60帧 frame_jitter 的标准差  │
              │  _last_out = out                            │
              └──────────────────────┬─────────────────────┘
                                     ▼
                          return out（16 路后处理角度）
```

---

## 10. 自测部分（`__main__`）

> 运行方式：`python -m vision.postprocess`（在 `rycan_hand_windows/` 下）。全部通过打印 `JointAnglePostProcess 自测通过`；任一断言失败抛 `AssertionError`。

自测共 5 个，刻意用**小模型（4 通道）**或**全模型（16 通道）**验证不同层面：

### 测试 1：静止噪声抑制（`joint_num=4`）

- 场景：目标静止 30°，4 路叠加 ±3° 均匀噪声，跑 300 帧（模拟 50ms/帧）。
- 统计：取第 100 帧之后（跳过滤波器预热期）的原始 std 与后处理 std。
- 断言：`clean_std < raw_std × 0.5`（噪声至少抑制一半）。
- 验证点：**阶段 1 的"抖动"痛点** —— 中值 + One Euro 对静止目标的抑噪能力。

### 测试 2：孤立异常识别与抑制（`joint_num=4`）

- 场景：静止 30° ±2° 噪声，**每 20 帧的第 10 帧**给第 3 通道注入 +50° 孤立突变（`k % 20 == 10` 时 `noisy[2] += 50`），跑 300 帧。
- 断言：
  - `clean2_std < raw2_std × 0.5`：异常被中值+限速抑制；
  - `pp2.dropped_frames >= 10`：300 帧里约 15 次注入，至少 10 次被方向一致性检测识别（跳变 50 > 40 且比值大）。
- 验证点：**修改 8 第 1 点** —— "孤立单指突变"仍能被识别为异常（统计层），且不再整帧丢弃（数据层靠中值替代兜住）。

### 测试 3：真实握拳不冻结（`joint_num=4`，回归修改 8 的核心）

- 场景：四指同时 0°→70° 快速握拳，每帧 +5°，叠加 ±2° 噪声，跑 40 帧。
- 断言：
  - `frozen <= 3`：40 帧中输出与上一帧**完全相同**的帧数 ≤ 3（滤波收敛期允许极少冻结，但绝不能连续卡住）；
  - `out[0] > 40.0`：握拳应跟随到接近目标 70°（限速 8°/帧 × 40 帧足够到达）；
  - `pp3.dropped_frames <= 2`：协调运动**不应**被判异常。
- 验证点：**修改 8 的核心回归** —— 旧版整帧丢弃会让四指同时 +5°（跳变中位数也大）被误判，输出冻结、`frozen` 飙高、握拳跟不到目标。这个测试就是当年"握拳卡住" bug 的复活守卫。

### 测试 4：内外展分通道限速（`joint_num=16`）

- 场景：16 通道全 0，仅第 15 通道（内外展）0→110° 快速变化，每帧 +5°，跑 60 帧。
- 断言：
  - `max_step <= abduct_max_delta + 1e-6`（3.0°）：内外展单帧步进被限速硬性钳制在 3°/帧；
  - `|out[15] - 110| < 15`：限速只带来滞后，不阻碍到达目标（60 帧 × 3°/帧 = 180° 上限，足够追上 110°）。
- 验证点：**修改 8 第 2 点** —— 分通道限速对内外展跳变的压制。

### 测试 5：深度确认握拳 → 绝不误判（`joint_num=16`，回归修改 8）

- 场景：16 通道 0→70° 握拳（每帧 +6°，比测试 3 更快、噪声 ±3° 更大），内外展同步 0→60°，**每帧传 `fist_confidence=0.9`**，跑 40 帧。
- 断言：
  - `frozen5 <= 2`：输出不卡住；
  - `pp5.dropped_frames == 0`：深度确认握拳时**一帧都不判异常**。
- 验证点：**修改 8 第 3 点** —— 深度辅助豁免（≥0.6 跳过异常判定）。即使快速握拳出现大跳变，深度相机确认后绝不计数、绝不误伤。

**为什么这 5 个测试能回归验证修改 8**：修改 8 的全部行为变化（孤立才判异常、中值替代、分通道限速、深度豁免）分别被测试 2/3/4/5 覆盖；测试 1 守住阶段 1 的基础抑噪能力不被削弱。未来任何人改动异常判定或限速逻辑，只要有一个测试红掉，就说明修改 8 的某条保证被破坏了。

---

## 11. 参数调优指南

GUI 里对应滑条（详见第 12 节）。调参前先明确当前痛点，再对症下药，**每次只调一个参数**。

### 11.1 `min_cutoff`（平滑强度(1€)，0.1~2.0，默认 0.5）

| 方向 | 效果 | 代价 |
|---|---|---|
| **调小**（更平滑） | 静止抖动显著减小，轨迹丝滑 | 跟手延迟增大；快速动作被"削圆"、幅度可能不足 |
| **调大**（更跟手） | 延迟低，动作干脆 | 静止抖动变大，噪声直接透过 |

### 11.2 `beta`（跟手度(1€)，0.0~0.2，默认 0.02）

| 方向 | 效果 | 代价 |
|---|---|---|
| **调大** | 快速运动时截止频率抬得更高 → 猛挥/快速握拳更跟手、少拖尾 | 快速段的噪声也更难滤掉；过大会让快慢切换时出现"突然变锐"感 |
| **调小**（趋近 0） | 滤波器退化为固定截止（等于 min_cutoff），行为可预测 | 快速运动也保持强平滑 → 大动作明显滞后、幅度被压 |

### 11.3 `max_delta_deg`（限速°/帧，1.0~20.0，默认 8.0）

| 方向 | 效果 | 代价 |
|---|---|---|
| **调小** | 普通关节单帧变化更小 → 突跳物理上不可能，安全性最高 | 快速动作被削成斜坡 → 跟手变慢；握拳/张开需要更多帧到达 |
| **调大** | 快速运动几乎不限制，跟手 | 突跳防护变弱；瞬时大错检会直接透传为猛跳 |

### 11.4 `abduct_max_delta_deg`（内外展限速°/帧，0.5~8.0，默认 2.0~3.0）

| 方向 | 效果 | 代价 |
|---|---|---|
| **调小** | 内外展（拇指开合）动作极稳，杜绝"啪"地张开 | 内外展跟手明显变慢，快速拇指开合滞后 |
| **调大** | 拇指开合跟手 | 内外展跳变防护变弱（该关节深度估计最易错，谨慎调大） |

### 11.5 组合经验

- **静止抖动大、动作还算跟手** → 调小 `min_cutoff`（先 0.3 试）。
- **动作跟手性差（拖尾/滞后）** → 先调大 `beta`，再考虑调大 `max_delta_deg`。
- **握拳偶尔卡/被误判** → 确认 `fist_confidence` 已接通（≥0.6）；或调大 `max_jump_deg`、调大 `jump_ratio_threshold`（放宽异常判据）。
- **单指偶发猛跳但整体稳定** → 调小 `max_delta_deg`；若跳变来自拇指内外展，调小 `abduct_max_delta_deg`。
- **异常帧率（drop_rate_pct）> 1%** → 视觉估计本身不稳定，优先排查光照/深度，而不是一味加滤波。

---

## 12. 与 GUI 的接线

### 12.1 创建（`gui/main_gui.py` 第 157~162 行）

```python
self.post = JointAnglePostProcess(
    joint_num=JOINT_NUM, median_n=5,
    min_cutoff=0.5, beta=0.02,
    max_delta_deg=8.0, abduct_max_delta_deg=3.0,
    max_jump_deg=40.0, jump_ratio_threshold=3.0,
)
```

与 `postprocess.py` 的构造函数默认值完全一致（`JOINT_NUM` 即 16）。

### 12.2 `PARAM_CONFIG`（第 45 行起）与 `update_params` 的映射

GUI 的滑条定义在 `PARAM_CONFIG` 字典，`_apply_calib()`（第 645 行）在用户点击"应用校准"时把滑条值同步进后处理链：

```python
self.post.update_params(
    min_cutoff=self.param_vars["min_cutoff"].get(),
    beta=self.param_vars["beta"].get(),
    max_delta_deg=self.param_vars["max_delta"].get(),
    abduct_max_delta_deg=self.param_vars["abduct_max_delta"].get(),
)
```

映射表：

| GUI `PARAM_CONFIG` 键 | 滑条 label | 范围 (min, max, step) | GUI 默认 | 传入 `update_params` 的形参 | 后处理属性 |
|---|---|---|---|---|---|
| `min_cutoff` | 平滑强度(1€) | (0.1, 2.0, 0.05) | 0.5 | `min_cutoff` | 每个 `OneEuroFilter.min_cutoff` |
| `beta` | 跟手度(1€) | (0.0, 0.2, 0.005) | 0.02 | `beta` | 每个 `OneEuroFilter.beta` |
| `max_delta` | 限速°/帧 | (1.0, 20.0, 0.5) | 8.0 | `max_delta_deg` | `self.max_delta` |
| `abduct_max_delta` | 内外展限速°/帧 | (0.5, 8.0, 0.5) | 2.0 | `abduct_max_delta_deg` | `self.abduct_max_delta` |

要点：

- **`min_cutoff` / `beta` 是逐通道的**：`update_params` 遍历 `self.euro` 给 16 个 One Euro 实例逐一赋值，滑条一动、下一帧全部生效。
- **`max_jump_deg` / `jump_ratio_threshold` 没有滑条**：GUI 只暴露 4 个滑条，异常检测阈值保持构造值（40.0 / 3.0），需改动时改构造处或代码。
- **默认值差异提示**：GUI 的 `abduct_max_delta` 默认 2.0，而 `postprocess.py` 构造默认 3.0。`_apply_calib()` 一旦执行，GUI 值（2.0）会覆盖后处理默认值；未执行前按构造值 3.0 运行。实际生效值以最后一次 `_apply_calib()` 为准。
- **调用时机**：`_apply_calib()` 在"应用校准"按钮点击时触发（同时把参数存盘，`_save_calibration()`），属于**批量热更新**，不调用 `reset()`，滤波状态不中断。
- **`fist_confidence` 的接线**：`update()` 的第三个参数来自调用方的深度握拳置信度（`hand_pose` 深度辅助输出），GUI 主循环每帧把该值透传给 `self.post.update(angles, t, fist_confidence)`；若未接通，传 `None` 即退化为纯角度判断。

---

## 附：一句话速记

> **中值去野值、One Euro 自适应平滑、限速兜底安全，方向一致性只认"孤立突变"、深度确认真握拳就豁免 —— 这就是阶段 1 的关节角精度后处理。**
