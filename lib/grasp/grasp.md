# 现有项目代码参考文档 —— 手眼标定、坐标转换与安全运动策略


## 一、概述

你提供的三份代码（`nanning.py`、`jisuan_p_ab.py`、`myctrl_task10.py`）是一套**完整的“眼在手上”视觉抓取系统**，基于 Aubo i5 机械臂 + Intel RealSense L515 + YOLO 物体检测，实现了从**物体识别 → 手眼标定坐标转换 → 安全路径规划 → 抓取放置**的全链路闭环。

> 本文档说明：你的项目（基于 Holistic 识别手腕、实时跟随）可以**直接复用**这套代码中的哪些核心资产，以及**需要改造**哪些部分。

---

## 二、核心可复用资产

### 2.1 手眼标定变换矩阵（已标定好，直接复用）

代码中已给出 **相机→机械臂末端** 的旋转矩阵和平移向量，这是整套系统最核心的“坐标翻译官”：

```python
# nanning.py 第 130-133 行
R_cam2gripper = np.array([
    [-0.9997106, -0.01955281, 0.01401418],
    [0.01983786, -0.99959306, 0.02049808],
    [0.01360768, 0.02077016, 0.99969167]
])
t_cam2gripper = np.array([0.00050964, 0.13082029, 0.03207186])
```

**用途**：将相机坐标系下识别到的点（手腕/物体），转换到机械臂末端法兰坐标系。

**你的项目可以怎么做**：
- 直接复用这两个矩阵，无需重新做手眼标定（前提是你的相机安装位置与这套代码的物理安装一致）。
- 如果不一致，可以使用同样的标定流程（OpenCV `calibrateHandEye`）重新标定，替换这两个矩阵即可。


### 2.2 完整的坐标转换流水线（像素 → 基座坐标）

代码实现了标准的 4 层坐标转换链，这是**你项目中“手腕在基座系下的绝对坐标”的计算方法**：

```python
# nanning.py grasp_and_place_object_task1 核心片段

# 第 1 层：深度图 → 相机系 3D 坐标（针孔模型）
center = np.array([
    (center_pixel[0] - cam_intrinsics["cx"]) * depth_value / cam_intrinsics["fx"],
    (center_pixel[1] - cam_intrinsics["cy"]) * depth_value / cam_intrinsics["fy"],
    depth_value
])
P_cam = center

# 第 2 层：相机系 → 末端法兰系（手眼标定矩阵）
P_gripper = np.dot(R_cam2gripper, P_cam) + t_cam2gripper

# 第 3 层：读取当前机械臂法兰在基座系下的位姿
fk_result = aubo_robot.forward_kin(current_joint_angles)
end_effector_position = fk_result['pos']
R_gripper2base = R.from_quat(end_effector_quaternion).as_matrix()

# 第 4 层：末端法兰系 → 基座系
P_base = np.dot(R_gripper2base, P_gripper) + end_effector_position
```

**你的项目可以怎么做**：
- 将 `P_cam` 的输入从“YOLO 检测的物体中心”替换为“MediaPipe Holistic 检测的手腕中心”。
- 保留第 2~4 层的转换逻辑，这样你就能得到**手腕在机械臂基座坐标系下的绝对位置**。


### 2.3 安全运动策略（防止刮蹭的“走位法”）

这套代码在防止刮蹭上使用了一种**极其稳健的策略——先抬升，再平移，最后下降**：

```python
# nanning.py 第 290-310 行
# 1. 先走到物体正上方 0.4m 高处（高悬停位置）
result = aubo_robot.move_to_target_in_cartesian([target_pos[0], target_pos[1], 0.4], rpy_xyz)

# 2. 再垂直下降到抓取点上方 6cm 处
result = aubo_robot.move_to_target_in_cartesian(
    [target_pos[0], target_pos[1], target_pos[2] + 0.06], rpy_xyz
)

# 3. 最后垂直下降到抓取点
result = aubo_robot.move_to_target_in_cartesian(target_pos, rpy_xyz)
```

**策略解读**：
- **水平移动永远在最高处进行**（0.4m 高悬停），末端不会在水平移动时撞到桌沿、障碍物或人体。
- **垂直移动只在目标点正上方进行**，路径是纯粹的 Z 轴直线，没有侧向摆动。
- 这种“**水平抬升 → 水平平移 → 垂直下降**”的路径规划，是从物理上杜绝刮蹭的最有效手段。

**你的项目可以怎么做**：
- 在实时跟随模式下，如果检测到手腕位置超出安全范围（如 X > 0.7m），**强制让机械臂回到高悬停位置**，而不是继续跟随。
- 每次跟随的起点，先抬升到安全高度，再执行增量移动。


### 2.4 运动速度与加速度限制（防冲击）

代码中限制了关节速度和末端线速度：

```python
# nanning.py 第 16 行
limitspeed = 0.5

# 第 281-282 行
result = aubo_robot.set_joint_maxvelc((limitspeed, limitspeed, limitspeed, limitspeed, limitspeed, limitspeed))
result = aubo_robot.set_end_max_line_velc(limitspeed)
```

**你的项目可以怎么做**：
- 在开启实时跟随前，强制将速度设为 0.1~0.2（极低速），观察轨迹稳定后再逐步提高。
- 速度限制是“末端负载（摄像头+灵巧手）惯性刮蹭”的第一道防线。


### 2.5 物理安装偏移参数（`p_ab` 调试机制）

代码中的 `p_ab` 表示**抓取点相对于机械臂末端的偏移**，实际上就是**末端执行器（灵巧手/吸盘）的物理中心相对于法兰盘的偏移**：

```python
# myctrl_task10.py 第 116-118 行
p_ab = [[-0.005, -0.05, 0.13]]  # 可乐的抓取偏移
r_ab = [[40, 0, 0]]              # 抓取姿态偏移
```

更强大的是，`jisuan_p_ab.py` 提供了一个**交互式调试工具**：
- 按 `W/S/A/D/Q/E` 实时微调 `p_ab` 参数（±1mm 步进）
- 按 `I` 键**反算 `p_ab`**：输入目标抓取点坐标，自动计算出最优偏移
- 按空格键保存参数到 `debug_params.txt`

**你的项目可以怎么做**：
- 你的末端挂了“摄像头+灵巧手”组合体，同样需要测量并填入 `hand_mount_offset`（对应 `arm_config.py` 中的配置）。
- 可以参考 `jisuan_p_ab.py` 的调试方法，在 GUI 中增加“微调末端偏移”的交互功能，现场标定时逐毫米校正。


## 三、核心区别：你的项目需要改造的部分

### 3.1 控制模式：离散抓取 vs 实时跟随

| 维度 | 现有代码 | 你的目标 |
|---|---|---|
| 控制模式 | **单次绝对定位**：拍照→算坐标→移一次→停下 | **连续增量跟随**：每帧都算增量→累加→非阻塞下发 |
| 运动指令 | `move_to_target_in_cartesian(绝对坐标)` | `move_to_target_in_cartesian(当前位置 + 视觉增量)` |
| 目标来源 | YOLO 检测物体中心 | MediaPipe Holistic 检测手腕中心 |
| 运动节奏 | 停顿式（走一步，停一步） | 流式（连续平滑追踪） |

**改造方案**：

```python
# 原有逻辑（绝对定位）
target_pos = (P_base[0], P_base[1], object_height)
aubo_robot.move_to_target_in_cartesian(target_pos, rpy_xyz)

# 改造为增量逻辑（实时跟随）
# 1. 读取机械臂当前真实位置（防止累积误差）
current_pose = aubo_robot.get_current_waypoint()['pos']

# 2. 计算视觉增量（当前帧手腕 - 上一帧手腕，在基座系下）
delta = P_base_now - P_base_last

# 3. 单步限幅（防猛冲，最大 5mm/帧）
max_step = 0.005
delta = np.clip(delta, -max_step, max_step)

# 4. 目标 = 当前位置 + 限幅后的增量
target_pos = current_pose + delta

# 5. 非阻塞下发（不等走完）
aubo_robot.move_to_target_in_cartesian(target_pos, 固定姿态, block=False)
```


### 3.2 末端姿态：动态变化 vs 固定锁死

| 维度 | 现有代码 | 你的目标 |
|---|---|---|
| 末端姿态（Rx/Ry/Rz） | 随物体姿态变化（如 `rpy_xyz`） | **固定不变**（锁死 J5/J6） |
| 姿态来源 | `pose_vectors_to_end2base_transforms` 计算 | 写死为固定值（如 `[π, 0, 0]`） |

**为什么你的项目必须固定姿态**：
- 如果姿态随视觉变化，机械臂的 J5/J6 会不断旋转，末端负载（摄像头+灵巧手）会画弧线，极大增加刮蹭风险。
- 固定姿态后，运动退化为纯平移（`moveL` 直线），路径可预测、安全可控。


### 3.3 识别对象：YOLO 物体 vs Holistic 手腕

| 维度 | 现有代码 | 你的目标 |
|---|---|---|
| 识别目标 | 物体（苹果/可乐/工件） | **人体手腕** |
| 识别模型 | YOLOv8（需训练） | MediaPipe Holistic（开箱即用） |
| 输出信息 | 物体掩膜 + 中心点 | 手腕 3D 关键点（归一化坐标+深度） |

**改造方案**：
- 将 `results = model(rgb, conf=0.3)` 替换为 `results = holistic_estimator.process(rgb, depth, intrinsics)`。
- 从 Holistic 结果中取 `r.wrist_3d`（已在相机系下，单位米），替代原来的 `P_cam`。


## 四、关键代码示例：集成参考方案

以下是你项目中**可以直接借鉴的代码片段**：

### 4.1 从相机坐标到基座坐标（复用现有代码）

```python
import numpy as np
from scipy.spatial.transform import Rotation as R

# 复用现有手眼标定矩阵
R_cam2gripper = np.array([
    [-0.9997106, -0.01955281, 0.01401418],
    [0.01983786, -0.99959306, 0.02049808],
    [0.01360768, 0.02077016, 0.99969167]
])
t_cam2gripper = np.array([0.00050964, 0.13082029, 0.03207186])

def camera_to_base(P_cam, aubo_robot):
    """
    将相机系下的点 (P_cam) 转换到机械臂基座系。
    参数:
        P_cam: 相机系下的 3D 坐标 [x, y, z]，单位米
        aubo_robot: 机械臂控制器实例
    返回:
        P_base: 基座系下的 3D 坐标 [x, y, z]，单位米
    """
    # 1. 相机系 → 末端法兰系
    P_gripper = np.dot(R_cam2gripper, P_cam) + t_cam2gripper
    
    # 2. 读取当前法兰在基座系下的位姿
    current_joint_angles = aubo_robot.get_current_waypoint()['joint']
    fk_result = aubo_robot.forward_kin(current_joint_angles)
    end_effector_position = fk_result['pos']
    
    # 3. 四元数 → 旋转矩阵
    q = fk_result['ori']  # [w, x, y, z]
    end_effector_quat = [q[1], q[2], q[3], q[0]]  # 转 [x, y, z, w]
    R_gripper2base = R.from_quat(end_effector_quat).as_matrix()
    
    # 4. 末端法兰系 → 基座系
    P_base = np.dot(R_gripper2base, P_gripper) + end_effector_position
    return P_base
```

### 4.2 安全运动封装（复用“先抬升再平移”策略）

```python
def safe_move_to_target(aubo_robot, target_pos, rpy, hover_height=0.4, approach_height=0.06):
    """
    安全路径规划：先抬升 → 水平平移 → 垂直下降。
    参数:
        target_pos: 目标位置 [x, y, z]
        rpy: 目标姿态 [rx, ry, rz]（度）
        hover_height: 高悬停高度（默认 0.4m）
        approach_height: 接近高度（默认 0.06m）
    """
    # 1. 先走到目标正上方悬停高度
    aubo_robot.move_to_target_in_cartesian(
        [target_pos[0], target_pos[1], hover_height], rpy
    )
    
    # 2. 垂直下降到目标上方 approach_height 处
    aubo_robot.move_to_target_in_cartesian(
        [target_pos[0], target_pos[1], target_pos[2] + approach_height], rpy
    )
    
    # 3. 垂直下降到目标点
    aubo_robot.move_to_target_in_cartesian(target_pos, rpy)
```

### 4.3 单步限幅（防视觉跳变导致猛冲）

```python
def apply_step_limit(delta, max_step=0.005):
    """
    限制单帧位移增量，防止视觉深度噪声导致机械臂猛冲。
    参数:
        delta: 本帧位移增量 [dx, dy, dz]
        max_step: 单帧最大位移（默认 5mm）
    返回:
        delta: 限幅后的位移增量
    """
    norm = np.linalg.norm(delta)
    if norm > max_step:
        delta = delta / norm * max_step
    return delta
```


## 五、实施步骤建议

| 步骤 | 内容 | 参考代码位置 |
|---|---|---|
| 1 | 直接复用 `R_cam2gripper` 和 `t_cam2gripper` 手眼标定矩阵 | `nanning.py` L130-133 |
| 2 | 复用坐标转换函数 `camera_to_base()` | 参考上述 4.1 节 |
| 3 | 将目标识别从 YOLO 物体替换为 MediaPipe Holistic 手腕 | 替换 `results = model(...)` |
| 4 | 将控制模式从“绝对定位”改为“增量累加” | 改造 `move_to_target_in_cartesian` 调用逻辑 |
| 5 | 套用“先抬升→平移→下降”安全路径策略 | `nanning.py` L290-310 |
| 6 | 限制单帧最大位移（5mm/帧） | 上述 4.3 节 |
| 7 | 固定末端姿态（锁死 J5/J6） | 将 RPY 写死为 `[180, 0, 0]` |
| 8 | 参照 `jisuan_p_ab.py` 的交互调试方法，微调末端偏移参数 | `jisuan_p_ab.py` 调试功能 |


## 六、总结

| 模块 | 可复用程度 | 说明 |
|---|---|---|
| 手眼标定矩阵 `R_cam2gripper` / `t_cam2gripper` | ✅ **直接复用** | 已标定好，无需重新计算 |
| 相机→基座坐标转换流水线 | ✅ **直接复用** | 代码完整，替换输入即可 |
| 安全路径策略（先抬升再平移） | ✅ **直接复用** | 防刮蹭的核心手段 |
| 速度/加速度限制 | ✅ **直接复用** | 防惯性冲击 |
| `p_ab` 交互调试工具 | ✅ **可参考** | 现场标定末端偏移的方法 |
| 物体识别（YOLO） | ❌ **需替换** | 你的目标是识别手腕，用 Holistic |
| 控制模式（绝对定位） | ❌ **需改造** | 你的目标是连续增量跟随 |
| 末端姿态（动态变化） | ❌ **需固定** | 锁死姿态，退化为纯平移 |

> **一句话总结**：这套代码提供了你项目中**“坐标怎么统一”**（手眼标定矩阵）和**“安全怎么保证”**（高悬停走位法）的完整解决方案。你需要改造的只是**控制模式**（从“点到点”改成“增量累加”）和**识别目标**（从“YOLO 物体”改成“Holistic 手腕”）。