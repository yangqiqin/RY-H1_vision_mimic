# 代码注释文档索引

本目录对 `rycan_hand_windows/` 工程的核心链路代码提供**逐函数、有逻辑**的中文注释详解。

## 阅读顺序建议

1. **先读 [00_总览详解.md](00_总览详解.md)** —— 系统架构、数据流、16 关节控制模型、模块关系、校准参数全景、常见问题速查。
2. **再按数据流顺序读各文件详解**：
   - 路径引导：[10_pathsetup.md](10_pathsetup.md)
   - 配置单点：[01_hand_config.md](01_hand_config.md)
   - 角度↔电机换算：[02_angles2motor.md](02_angles2motor.md)
   - 通信传输层：[04_transport.md](04_transport.md)
   - 灵巧手控制器：[03_hand_controller.md](03_hand_controller.md)
   - 相机（标准版）：[05_camera_module.md](05_camera_module.md)
   - 相机（增强版，GUI 实际使用）：[06_camera_lib1.md](06_camera_lib1.md)
   - 姿态估计：[07_hand_pose.md](07_hand_pose.md)
   - 精度后处理：[08_postprocess.md](08_postprocess.md)
   - 主界面：[09_main_gui.md](09_main_gui.md)

## 文件对应关系

| 文档 | 源码文件 | 行数 |
|---|---|---|
| 01_hand_config.md | `hand/hand_config.py` | 67 |
| 02_angles2motor.md | `hand/angles2motor.py` | 92 |
| 03_hand_controller.md | `hand/hand_controller.py` | 630 |
| 04_transport.md | `hand/transport.py` | 243 |
| 05_camera_module.md | `camera/camera_module.py` | 339 |
| 06_camera_lib1.md | `lib/camera_lib1.py` | 380 |
| 07_hand_pose.md | `vision/hand_pose.py` | 769 |
| 08_postprocess.md | `vision/postprocess.py` | 304 |
| 09_main_gui.md | `gui/main_gui.py` | 841 |
| 10_pathsetup.md | `lib/_pathsetup.py` | 75 |

> 注：文档中的行号基于撰写时的源码版本；后续代码若有修改，以最新源码为准。
