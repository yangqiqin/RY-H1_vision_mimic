# 睿研 RY-H1(16) 灵巧手 · Windows 视觉动作模仿（不接机械臂，模块化可单项验证）

> **依据**：《睿研灵巧的SDK入门指南》V1.01（知识库）、官方 demo（`RyHandLibCANII_rs485_pcan_16.py`、`RyHandLibPCAN_windows16.cpp`、`RyHandLib.h`）、RY-H1(16) 手册。
>
> **目标**：Windows 上 **只通过摄像头 + 灵巧手** 实现视觉动作模仿，无需机械臂、无需 Ubuntu。每个模块可**单独验证**，另有综合验证脚本一次跑通。

```
USB摄像头 / Intel L515 ──▶ camera/ ──▶ vision/ (MediaPipe 16关节角)
                                          │
                                          ▼
                           hand/angles2motor (16关节弧度→电机指令)
                                          │
                                          ▼
                           hand/hand_controller (RyhandLibx64.dll + PCAN/CANII/RS485)
                                          │
                                          ▼
                                    RY-H1(16) 灵巧手
```

---

## 1. 目录结构与模块化验证入口

| 模块 | 文件 | 单项验证 | 说明 |
|---|---|---|---|
| 摄像头 | `camera/camera_module.py` | `apps/test_camera.py` | USB UVC / **L515 RGB-D**（含连通性检查） |
| 姿态估计 | `vision/hand_pose.py` | `test_all.py` 第 3 步 | MediaPipe → 16 关节弧度 |
| 关节换算 | `hand/angles2motor.py` | `test_all.py` 第 4 步 | demo 公式 + 左右手 |
| **灵巧手控制** | `hand/hand_controller.py` | **`apps/test_hand.py`** | 连接性自检 + 状态读取 + 动作 |
| 通信层 | `hand/transport.py` | （被控制器调用） | PCAN / CANalyst-II / RS485 |
| **GUI 控制** | **`gui/hand_gui.py`** | `python -m gui.hand_gui` | 连接测试 + 16 关节滑条 + 预设动作 |
| 动作模仿 | `apps/mimic_demo.py` | 直接运行 | 摄像头 → 姿态 → 灵巧手 |
| **综合验证** | **`apps/test_all.py`** | 直接运行 | 依赖+摄像头+姿态+换算+灵巧手一次跑通 |
| 环境自检 | `selfcheck.py` | 直接运行 | 不接硬件也能跑大部分 |

---

## 2. 安装（Windows，注意标注的包）

```bash
python -m pip install -r requirements.txt
# = 内容：
#   numpy, opencv-python, mediapipe>=0.10.14   # 视觉（必须；新版 MediaPipe Tasks）
#   pyrealsense2                               # L515 RGB-D（可选，必须 2.54.2.5684）
#   pyserial                                   # RS485 通信（可选）
```

**资源统一放在 `lib/` 目录**（模型 / 驱动 / SDK 库 / 参考文件；代码自动搜索 根目录 + lib/）：

| 文件（放 `lib/`） | 用途 | 缺了会怎样 |
|---|---|---|
| `RyhandLibx64.dll` | 睿研 SDK 库（Windows x64） | 控制器无法加载 |
| `PCANBasic.py` + PCAN 驱动 | PCAN-USB 通信（默认方式） | `--method pcan` 失败 |
| `ControlCAN.py` + `ControlCAN.dll` | 周立功 CANalyst-II | `--method canii` 失败 |
| `hand_landmarker.task` | MediaPipe 手部模型（新版 Tasks API 必需） | 姿态估计失败 |
| `_pathsetup.py` | 路径引导工具 | 代码自动用内联引导，可选 |
| `vision_hand_ctrl.py` | **参考实现**（距离比法/夹角法/CONFIG 参数规范） | 仅参考，非必需 |

> 代码搜索顺序：显式路径 → 当前目录 → 项目根目录 → **lib/** → vision/。兼容"资源放根目录或 lib/"两种布局。
>
> MediaPipe 模型下载（放到 lib/）：
> ```bash
> curl -L -o lib/hand_landmarker.task ^
>   https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
> ```

> PCAN / ControlCAN 驱动文件在官方 `ryhand_windows_python_canii_rs485_pcan_16.zip` demo 中，知识库已保存源码。

---

## 3. 硬件连接与 L515 连通性

### 灵巧手
- 电源 **24V（推荐 8A+）**，先接线无误再插航插，禁止带电插拔；
- M9 航插 → PCAN 模块 → USB 接电脑（或 USB-CAN / RS485 转接）；
- CAN 波特率 **1Mbps**；RS485 **5Mbps**。

### L515（重点，依据知识库 README_1.md《L515 PyLive Toolkit》）
1. **必须 USB3.0 直连**（勿经 USB2 集线器），装 [Intel RealSense SDK 2.0](https://github.com/IntelRealSense/librealsense/releases)；
2. **必须安装 `pyrealsense2==2.54.2.5684`**（README_1.md 指明 L515 只用此稳定版；
   ⚠️ **librealsense 2.55+ 已移除 L515 支持**，装新版本会"识别不到"）：
   ```bash
   pip install pyrealsense2==2.54.2.5684
   ```
3. **深度流与 RGB 流分开设分辨率**（L515 彩色/深度分辨率不同，README_1.md 例1/例2）：
   本工程已按 **RGB 1280×720 + 深度 1040×768** 配置（`camera_module.py` 的 `width/height` 与 `depth_width/depth_height` 分开）；
4. 先跑 `python apps/test_camera.py --list`：能看到设备即连通；返回空 = 驱动/线缆/供电问题；
5. 再跑 `python apps/test_camera.py --realsense --show` 看 RGB+深度画面；
6. 也可以先用官方 Intel RealSense Viewer 确认出图。

**L515 仍识别不到时的排查顺序（`python apps/test_camera.py --list`）：**
| 现象/日志 | 根因 | 处理 |
|---|---|---|
| `pyrealsense2 版本 xx 不兼容 L515` | 装了 2.55+（L515 已被移除支持） | `pip install pyrealsense2==2.54.2.5684` |
| `0x80070005 拒绝访问 / Access denied` | **Windows 权限**：相机隐私权限或非管理员 | **以管理员身份运行**；设置→隐私→相机→允许 |
| `未找到 RealSense 设备` | USB/驱动/供电 | USB3 直连、装 SDK 2.0 运行时、换线/换口、RealSense Viewer 验证 |
| `RealSense 流启动失败` | 分辨率组合不支持 | 按 README_1.md 例1/例2 调整（depth 640×480+RGB 1280×720） |

### 关节角度范围（RY-H1 手册，GUI 滑条已按此限幅）
| 关节类型 | 角度范围 | 关节 ID |
|---|---|---|
| 侧摆 | **-20° ~ +20°**（对称，可双向） | 1,4,7,10,13 |
| 近节弯曲 | 0° ~ 90° | 2,5,8,11,14 |
| 远节弯曲 | 0° ~ 75° | 3,6,9,12,15 |
| 第16关节（拇指横向旋转） | 0° ~ 110° | 16 |

> ⚠️ 安全：GUI 滑条范围已按上表设置（侧摆不再只能单向/可拉 90°）。运动前建议先跑
> `python apps/test_hand.py --method pcan` 确认方向与幅度，scale 从 0.3 起步。

---

## 4. 使用步骤

```bash
# ① 环境自检（不接硬件也能验证依赖/换算）
python selfcheck.py

# ② 单项验证·灵巧手连接性（推荐先做）
python apps/test_hand.py --method pcan
python apps/test_hand.py --method rs485 --port COM5
python apps/test_hand.py --method pcan --move        # 附带张开/握拳

# ③ 单项验证·摄像头/L515
python apps/test_camera.py --list
python apps/test_camera.py --camera 0
python apps/test_camera.py --realsense --show

# ④ 简单 GUI 控制面板（连接测试 + 滑条 + 预设动作）
python -m gui.hand_gui

# ⑤ ★ 综合控制界面（推荐：实时画面 + 骨架 + 校准 + 手控）
python -m gui.main_gui

# ⑥ 动作模仿（命令行版）
python apps/mimic_demo.py --method pcan --camera 0 --scale 0.5
python apps/mimic_demo.py --method pcan --realsense --scale 0.5 --show

# ⑦ 综合验证（依赖+摄像头+姿态+换算+灵巧手 一次跑通）
python apps/test_all.py --method pcan
python apps/test_all.py --method pcan --move
```

### 综合控制界面 `gui/main_gui.py` 使用步骤（推荐主入口）

```bash
python -m gui.main_gui
```

1. **启动相机**：选 `USB摄像头` 或 `L515` → 点【启动相机】；
   右侧实时画面出现（有手时绘制绿色骨架 + 关节角叠加，无手显示"未识别到手"）；
2. **连接灵巧手**：选手通信 `PCAN/CANII/RS485` + 手型（左/右）→ 点【连接手】；
   （若 9/11 号等电机"动作看不见"，先【自检】看是否 `找零告警`，再点【回零】）
3. **精细校准**（右侧面板实时生效）：
   - `bend_gain`：**动作幅度偏小时调大**（1.0→1.5~2.0）；**幅度过大时调小**（→0.5~0.8）；
   - `bend_scale/bend_offset`：整体缩放/偏置；
   - `deadzone`：抖动过滤（越大越不灵敏）；
   - **弯曲方向反转**：勾选后"该伸直时弯曲/该弯曲时伸直"互换（90°-θ）；
   - **距离比法**：四指默认用距离比法（更稳），取消则用三维夹角法；
   - `每指增益`：各指弯曲灵敏度单独调（如拇指 1.2）；
   - 观察"实时参数"里的 16 关节角，边看边调；
4. **动作模仿**：勾选【动作模仿】→ 摄像头前做手势，灵巧手跟随
   （平滑系数可调，首次建议 bend_gain 从 1.0 试起，确认方向再加大）；
5. **手动控制**：底部 16 关节滑条逐个调试；预设按钮（张开/握拳/放松）；
   单电机测试（ID+位置）排查无响应电机；
6. 退出：关闭窗口自动释放相机/断开手。

> 综合界面同时调用 **RGB + 深度**（L515）：深度帧用于手部距离显示，
> 姿态估计用 3D 关键点（x,y,z）计算夹角，比纯 2D 精度更高、动作幅度更真实。

---

## 5. 预设动作（标准握拳，已修正 demo palm_bend 缺陷）

官方 demo `palm_bend` 预设存在两个问题（用户实测发现）：
1. **食指远节=0°（食指一直伸直）**、且各指弯曲幅度不齐；
2. **握拳时带侧摆**（demo 给食指侧摆 10°），不符合"握拳"语义。

本工程 `hand_controller.close_hand()` 已重设计为**标准握拳**：

| 手指 | 侧摆 | 近节 | 远节 |
|---|---|---|---|
| 拇指 | 0° | 50° | 30° |
| 食指/中指/无名指/小指 | 0° | 70° | 60° |

- 所有手指**近节+远节都弯曲**（不再有手指伸直），**侧摆全 0**（握拳不侧摆）；
- 角度均在手册范围内（近节 ≤90°、远节 ≤75°）；
- `relax()`（放松半握）同理：近节 30~35°、远节 15~25°、侧摆 0。

### 第16关节（拇指横向旋转）"幅度小"排查
- 手册标准版参数：**大拇指横向旋转范围 0~125°（含大侧摆与小侧摆）**，demo 换算用 0~110°；
- 若实测 16 号电机幅度很小，用 `test_hand.py` 或以下命令检查**行程（Stroke）**：
  ```python
  from hand import RYH1HandController
  hand = RYH1HandController(method="pcan"); hand.open()
  print(hand.check_joint16_stroke())   # 行程应 ≈4095；过小则幅度小
  hand.close()
  ```
- 行程偏小（<3000）时，用上位机校准或 `hand.set_stroke(16, 4095)` 恢复（谨慎，先读当前值）。

---

## 5. 控制模型（与官方 demo 对齐）

- **16 关节 ID 1~16**（弧度输入）：拇指侧摆/近节/远节、食指…、小指远节、第16关节(0~110°)；
- **换算**（demo `update_motor_positions`）：`M1=k(θ1/2+θ2)`、`M2=k(−θ1/2+θ2)`、`M3=θ3·(4095/75)`、`M16=θ16·(4095/110)`，k=4095/90；
- **左右手**：`hand_lr=1` 右手；`0` 左手每指 M1↔M2 交换；
- **初始化**（demo）：`hook=40`、`listen=33`、32 个 AddListen（16×0xA0 + 16×0xAA，ID=伺服ID+256）；
- **指令**：0xAA 位置速度电流（带载推荐）/ 0xA1 位置速度 / 0xA0 读状态；应答 ID = 发送 ID + 0x100。

---

## 6. 路径引导说明（重要：解决"运行子目录文件找不到根目录资源"）

**问题**：直接运行 `python apps/test_hand.py` 时，Python 只把 `apps/` 加入 `sys.path`，
导致找不到根目录的 `hand/camera/vision` 包；同时 `RyhandLibx64.dll`、
`lib/PCANBasic.py`、`ControlCAN.dll` 是相对路径/依赖 sys.path，也解析不到根目录。

**解决**：每个入口文件（`apps/*.py`、`gui/hand_gui.py`、`selfcheck.py`）顶部都有
**统一路径引导**（在导入本项目模块之前）：

```python
from __future__ import annotations
# ---- 路径引导（必须最先执行） ----
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:                                    # Windows 控制台 UTF-8，避免中文/符号乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
```

引导效果：
1. **`sys.path` 注入项目根目录** → `from hand import ...` / `import camera` 等根目录包可用；
2. **`os.chdir(根目录)`** → `ctypes.CDLL("RyhandLibx64.dll")`、`import PCANBasic`、
   `ControlCAN.dll` 等相对路径资源可在根目录找到；
3. **UTF-8 重配置** → Windows GBK 控制台不会因 `✓/✗/中文` 报 UnicodeEncodeError。

另外，`hand/hand_controller.py` 加载 DLL 时会把「当前目录 + 项目根目录」都加入搜索候选，
`hand/transport.py` 导入 PCAN/ControlCAN 驱动前也会确保根目录在 sys.path —— **双保险**，
即使忘了在入口做引导，从任何目录以任何方式运行都能找到根目录内容。

因此：**DLL、PCANBasic.py、ControlCAN.py/.dll 等资源统一放项目根目录即可**，
所有入口（根目录 / apps/ / gui/ 下的单文件、`python -m` 模块方式）都能正确识别。

---

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| `test_hand` 0/16 电机应答 | 电源 24V/8A；波特率 1M/5M；PCAN 驱动/ControlCAN.dll；串口号 |
| `selfcheck` 找不到 SDK 库 | 把 `RyhandLibx64.dll` 放工程根目录 |
| **滑"近节"滑条实际是侧摆** | **手型选反了**：左右手电机 1/2 镜像，共模(近节)/差模(侧摆)互换。GUI 点"左手/右手"切换（已连接也立即生效） |
| L515 `--list` 为空 | ① pyrealsense2 必须 2.54.2.5684（2.55+ 移除 L515）② USB3 直连 ③ 管理员运行（0x80070005 拒绝访问）④ 官方 Viewer 验证 |
| MediaPipe 卡 | 降 `--rate`；低分辨率；用 GPU 机型 |
| 手方向反/幅度大 | `--hand-lr` 与手型一致；`--scale 0.3` 起步；调 `hand_pose.py` 阈值 |
| GUI 滑条不动 | 先点"连接"；确认 `test_hand` 通过 |

---

*依据《睿研灵巧的SDK入门指南》V1.01 与官方 demo 编写；如与厂家最新库不一致，以厂家最新资料为准。*
