# 代码注释文档索引

本目录对 `RY-H1_vision_mimic/` 工程的核心链路代码提供**逐函数、有逻辑**的中文注释详解
（灵巧手 + Aubo K5 机械臂）。

## 阅读顺序建议

1. **先读 [设备连接与成功运行总纲](../../docs/设备连接与成功运行总纲.md)** —— 器件连接/成功运行/运行逻辑/代码解释/术语表/全部注意事项（综合知识库+代码提炼）。
2. **再读 [00_总览详解.md](00_总览详解.md)** —— 系统架构、数据流、16 关节控制模型、模块关系、校准参数全景、常见问题速查。
3. **再按数据流顺序读各文件详解**：
   - 机械臂执行文档：[../../docs/机械臂控制执行文档.md](../../docs/机械臂控制执行文档.md)（环境/连接/验证/GUI/联动/排障）
   - 协同控制文档：[../../docs/协同控制说明文档.md](../../docs/协同控制说明文档.md)（Holistic 协同：映射/标定/使用）
   - 路径引导：[10_pathsetup.md](10_pathsetup.md)
   - 配置单点：[01_hand_config.md](01_hand_config.md)（灵巧手）/ [12_arm_config.md](12_arm_config.md)（机械臂）
   - 角度↔电机换算：[02_angles2motor.md](02_angles2motor.md)
   - 通信传输层：[04_transport.md](04_transport.md)
   - 灵巧手控制器：[03_hand_controller.md](03_hand_controller.md)
   - 机械臂控制器：[11_arm_controller.md](11_arm_controller.md)
   - 相机（标准版）：[05_camera_module.md](05_camera_module.md)
   - 相机（增强版，GUI 实际使用）：[06_camera_lib1.md](06_camera_lib1.md)
   - 姿态估计：[07_hand_pose.md](07_hand_pose.md)
   - 精度后处理：[08_postprocess.md](08_postprocess.md)
   - 主界面（灵巧手）：[09_main_gui.md](09_main_gui.md)
   - 主界面（臂+手）：[13_main_gui_arm.md](13_main_gui_arm.md)
   - Holistic 全身姿态（协同）：[14_holistic_pose.md](14_holistic_pose.md)
   - 腕部→TCP 映射（协同）：[15_arm_follow.md](15_arm_follow.md)
   - 协同总 GUI：[16_main_gui_holistic.md](16_main_gui_holistic.md)

## 文件对应关系

| 文档 | 源码文件 | 行数 |
|---|---|---|
| 01_hand_config.md | `hand/hand_config.py` | 67 |
| 02_angles2motor.md | `hand/angles2motor.py` | 92 |
| 03_hand_controller.md | `hand/hand_controller.py` | 630 |
| 04_transport.md | `hand/transport.py` | 243 |
| 05_camera_module.md | `camera/camera_module.py` | 339 |
| 06_camera_lib1.md | `lib/参考代码/camera_lib1.py`（转发入口 `lib/camera_lib1.py`） | 380 |
| 07_hand_pose.md | `vision/hand_pose.py` | 769 |
| 08_postprocess.md | `vision/postprocess.py` | 304 |
| 09_main_gui.md | `gui/main_gui.py` | 841 |
| 10_pathsetup.md | `lib/_pathsetup.py` | 96 |
| 11_arm_controller.md | `arm/arm_controller.py` | 新增 |
| 12_arm_config.md | `arm/arm_config.py` | 新增 |
| 13_main_gui_arm.md | `gui/main_gui_arm.py` | 新增 |
| 14_holistic_pose.md | `vision/holistic_pose.py` | 新增 |
| 15_arm_follow.md | `arm/arm_follow.py` | 新增 |
| 16_main_gui_holistic.md | `gui/main_gui_holistic.py` | 新增 |

> 注：文档中的行号基于撰写时的源码版本；后续代码若有修改，以最新源码为准。
