# 实时视觉臂跟随架构（<0.1s）与 servo 执行层

## 目标
眼在手上：手(相机系3D) → 手眼标定 → 机械臂末端 **顺滑、实时(<0.1s 延迟)、精确** 跟随。

## 为什么之前"卡/不跟手"
本项目早期执行层全部用 `moveJoint/moveLine`：这是**路径执行**接口——指令进 SDK 规划队列、
按"一段一段执行完再接受下一段"工作；队列满返回 2(QUEUE_FULL)。视觉误差 100~200ms 才进一条
指令，机械臂自然顿挫、滞后、且曾误报急停。结论：**<0.1s 的实时跟随必须换执行层，不能靠 move 队列**。

## 关键发现（来自 SDK 官方示例与头文件）
- SDK 提供关节伺服：`MotionControl.setServoModeSelect(mode)` / `servoJoint(q, a, v, t,
  lookahead_time, gain)`（Python 可用，见 lib/aubo_sdk.../share/example/python/
  example_servoj2.py、example_servoj3.py）。
- 语义（motion_control.h）：
  - servoJoint 按**固定周期**(如 5~20ms)连续下发关节目标，截断式连续轨迹；
  - `t`≈相邻两次调用间隔（与实际下发节拍一致最好）；
  - `lookahead_time` 建议一个控制周期量级 [0.03,0.2]，用于平滑（太小超调大）；
  - `gain` [100,200]，越大越稳但到位越慢；
  - 相邻两点的关节角差须 ≤±15°（超出返回 -5 → 说明步长过大，需缩小每步位移）；
  - 队列满 ret=2 时按示例"sleep≈5ms 后重发"即可（实时流的正常现象，非故障）。
- RTDE/state 可读高速关节状态（example_rtde.py），用于后续状态反馈闭环。

## 本项目的取舍（position-based visual servoing, PBVS）
采用**位置基视觉伺服**流水线（最稳妥、可逐步调试），不用直接图像雅可比：
```
捕获(30fps) → [worker] 手眼3D(≈mm) → EMA平滑+死区 → 期望末端(x,y,z,固定姿态)
→ IK(固定RPY) → 关节目标 → 执行层 servoJoint(move) 每 ~40ms
```
- 平滑/死区防抖；每帧目标 = 期望终点（限步长 ≤ max_step 或 4×max_step 防跳变）；
- **执行层二选一**：
  - 常规 move 模式（默认）：大位移一条 movej 长轨迹；
  - **伺服实时模式（新）**：begin() 进入 servo → 每 40ms 下发 `servoJoint` → stop() 退出 servo。
- 全部在后台 worker 线程：主线程只管显示，延迟不受 GUI 阻塞影响。

## 使用（实机）
1. 机械臂：连接 → 上电+启动(Running)；**不要**开启拖拽示教；安全模式 Normal。
2. GUI【眼在手上】勾选 **"★ 伺服实时模式"** → 设置安全高度区 → ▶ 开始跟随。
3. 手从慢速小幅开始；确认方向、幅度、稳定后逐步加大移动幅度。
4. 停止：⏹ 停止跟随（自动退出 servo）或关窗。

> ⚠️ 首次真机务必低速、人手随时按急停。servo 会连续驱动机器人，出现异常应停止跟随退出 servo。

## 各段延迟预算（目标端到端 <0.1s）
| 环节 | 预算 | 手段 |
|---|---|---|
| 捕获/对齐 | ≤10ms | L515 队列最新帧(丢旧帧，只处理最新) |
| 手部/手腕检测 | 20~40ms | holistic 原分辨率；后续可做手腕 ROI 轻量跟踪 |
| 3D+手眼换算+平滑 | <1ms | 纯 numpy |
| 期望位姿+IK | 3~8ms | SDK 逆解 RPC（网络~1-3ms） |
| 执行 servoJoint | 与节拍同 | 40ms 周期（t 同设 0.04） |
合 计（检测→执行）≈ 60~90ms，接近/达到 <0.1s；**实际延迟请用 HUD 的 fps 与状态判断**。

## 参数调优表（GUI/常量）
| 参数 | 默认 | 建议范围 | 说明 |
|---|---|---|---|
| 每帧步长 max_step（限幅mm/帧） | 15 | 5~30 | 跟随速度上限≈step/节拍；伺服时保持≤max_step 以免邻点 >±15° |
| servoJoint t | 0.04s | 与下发节拍一致 | GUI 伺服模式已把 worker 节拍设 0.04 |
| lookahead | 0.1s | 0.03~0.2 | 顺滑度 |
| gain | 200 | 100~200 | 跟踪平滑/精度折中 |
| 丢手超时 | 1.5s | 0.5~3s | 时间制，短暂遮挡不误停 |
| EMA 权重 | 0.45 | 0.2~0.6 | 越小越平滑但滞后略大 |

## 后续改进（按实测数据选择）
1. **延迟测量**：在 worker 记录 capture→detect→send 时间戳，GUI HUD 显示"总延迟ms"，再针对性优化；
2. 若检测是大头：做**手腕 ROI 跟踪**（上帧腕部周围小窗只跑手模型）或切轻量模型；
3. 若 RPC 是瓶颈：IK 移到本地(带 DH 自算)或缓存最近解+小增量解析，进一步降到 <5ms；
4. 状态闭环：用 RTDE 高频读实际关节，误差>阈值时微调（视觉伺服收敛）；
5. 末端碰撞/桌面保护：沿用软件安全链 + 高度安全区（控制器 addCollisionBox/setWorldZone 在本固件 32601 不可用，见 cpp 文档）。

## 参考（来源）
- SDK：lib/aubo_sdk-.../share/example/python/example_servoj2.py、example_servoj3.py、
  example_rtde.py；include/aubo/robot/motion_control.h 的 servoJoint 注释。
- 视觉伺服通用方法：位置基视觉伺服(PBVS) 误差=目标3D-当前 → 运动命令（本项目实现取舍）。
- 论文/项目参考：视觉预测/动作识别人机协同（动作意图估计→响应）可作为"预判+平滑"扩展方向，
  不在当前 0.1s 实时主链必须范围内。
