# C++ 碰撞盒服务（collision_box_server）编译与使用

## 为什么需要它
- Python 版 `pyaubo-sdk` 的 RobotAlgorithm 无法调用 `addCollisionBox`（固件/绑定层报
  **32601 method not found**）。
- 方案：碰撞盒由 **C++ 程序直连遨博 C++ SDK** 调用，Python GUI 通过 **Socket(JSON)**
  下发 `add/remove` 命令。
- 链路：`GUI(main_gui_eye / main_gui_arm) → arm/collision_box_client.py → TCP → collision_box_server.exe → 遨博 C++ SDK → 机械臂`

## PyCharm 用户速览（您全程用 PyCharm）
1. **直接运行 GUI**：PyCharm 打开 `gui/main_gui_eye.py` → 右键 Run。
   程序会自动查找并拉起 `bin/collision_box_server.exe`，无需手动开服务。
2. **一键编译服务端**：PyCharm 打开 `cpp_src/build_collision_server.py` → 右键 Run
   （或 Terminal：`python cpp_src/build_collision_server.py`）。脚本会：
   - 自动定位 SDK 并尝试编译**真实版(mode=sdk)**；
   - 无论如何先编译一份**演示版(mode=mock)** 到 `bin/` 保底；
   - 结果写入 `bin/build_result.txt`。
3. **真实版编译**：本机 MinGW 对遨博 MSVC SDK 的导入库支持不完整（长 C++ 符号被
   dlltool 截断），真实版请在装有 MSVC 的环境运行
   `cpp_src/build_collision_server_msvc.bat`（或按下方 [编译 → 真实模式 MSVC] 手动执行）。
4. 状态栏会诚实显示当前是 `mode=sdk`（硬件级）还是 `mode=mock`（演示、软件链兜底）。

## 文件
| 文件 | 说明 |
|---|---|
| `cpp_src/collision_box_server.cpp` | C++ 服务端源码（真实 SDK 与演示两分支） |
| `cpp_src/build_collision_server.py` | PyCharm 一键编译脚本（演示保底 + 尝试真实版） |
| `cpp_src/build_collision_server_msvc.bat` | MSVC 真实版一键编译脚本 |
| `bin/collision_box_server.exe` | 当前版本 exe（演示 mock，待真实版替换） |
| `arm/collision_box_client.py` | Python Socket 客户端（自动启动服务端） |

## 运行模式与重要提醒
- **mode=sdk**：真实模式（编译时 `-DUSE_REAL_AUBO_SDK` 链接 SDK），GUI 显示"✅ C++ SDK 硬件级保护"。
- **mode=mock**：演示模式（当前 bin/ 版本），能完整跑通协议与 GUI 流程，但**不会真正在机器人上
  加碰撞盒**——GUI 会明确提示"演示模式(mock)，未真正启用 → 软件多层安全链兜底"，绝不谎报保护。
- ⚠️ **机器人固件限制（已实测确认）**：在 `aubo/1.py` 打印 `dir(ra)`，Python 绑定里
  **有** `addCollisionBox / removeCollisionObject`，但调用仍报 32601 method not found——
  说明方法在客户端存在、**控制器固件没有实现该 RPC**。C++ 走同一控制器 RPC，会返回
  **同样的 32601**（与语言无关）。
  因此：
  1. GUI 会自动尝试 **WorldZone 桌面危险腔**（`arm.enable_table_protect_zone`）；
     但实测本控制器固件 `setWorldZone` 同样 32601 → 无硬件级碰撞保护可用，
     最终由软件多层安全链兜底（GUI 会明确显示该结论并缓存，不再每次重试刷错）；
  2. 若必须使用 addCollisionBox / setWorldZone：需**升级控制器固件**
     （向遨博确认支持这些 API 的固件版本）；
  3. 升级前可先装 MSVC 编译真实版做一次实测复核（预期同为 32601）。


## 文件
| 文件 | 说明 |
|---|---|
| `cpp_src/collision_box_server.cpp` | C++ 服务端源码（含真实 SDK 与演示两分支） |
| `bin/collision_box_server.exe` | 已用 MinGW 编译的**演示(mock)版**（未链 SDK） |
| `arm/collision_box_client.py` | Python Socket 客户端（自动启动服务端） |

## 运行模式
- **mode=sdk**：真实模式（编译时 `-DUSE_REAL_AUBO_SDK` 链接 SDK），GUI 显示"✅ C++ SDK 硬件级保护"。
- **mode=mock**：演示模式（当前 bin/ 版本），能完整跑通协议与 GUI 流程，但**不会真正在机器人上
  加碰撞盒**——GUI 会明确提示"演示模式(mock)，未真正启用 → 软件多层安全链兜底"，绝不谎报保护。
- 真机使用前请用下面方式编译真实版替换 `bin/` 下的 exe。

## 编译
### 1) 演示模式（无 SDK 环境验证协议）
```
g++ -O2 -std=c++17 cpp_src/collision_box_server.cpp -o bin/collision_box_server.exe -lws2_32
```

### 2) 真实模式（MSVC / Visual Studio 开发人员命令行）
```
set SDK=E:\...\lib\aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170
cl /EHsc /O2 /DUSE_REAL_AUBO_SDK /I"%SDK%\include" cpp_src\collision_box_server.cpp ^
   /link /LIBPATH:"%SDK%\lib" aubo_sdk.lib robot_proxy.lib ws2_32.lib ^
   /OUT:bin\collision_box_server.exe
```
运行目录需能找到 `aubo_sdk.dll`、`robot_proxy.dll`（把 `%SDK%\lib` 下的 dll 拷到 exe 旁，
或加入 PATH）。

### 3) 真实模式（MinGW）
先生成导入库再编译：
```
gendef aubo_sdk.dll && dlltool -d aubo_sdk.def -l libaubo_sdk.dll.a
g++ -O2 -std=c++17 -DUSE_REAL_AUBO_SDK -I"<sdk>/include" cpp_src/collision_box_server.cpp ^
    -L. -laubo_sdk -lws2_32 -o bin/collision_box_server.exe
```

## 使用
- GUI 连接机械臂后：
  - 【机械臂控制】页 →"末端安全碰撞盒"→【启用碰撞盒】；
  - 【眼在手上控制】→ ▶ 开始跟随（自动启用）；⏹ 停止/关窗自动移除并停服务。
- 服务端参数：`collision_box_server.exe [port] [-r robot_ip]`（默认端口 9999，
  IP 默认 192.168.1.100；GUI 会自动传当前机械臂 IP）。
- **启动失败诊断**：服务进程日志写入 `bin/collision_server.log`（含启动时间戳与 C++ 端输出）；
  GUI 失败提示会附日志尾部。常见原因：端口被残留进程占用（任务管理器结束
  collision_box_server 后重试）、exe 依赖缺失（真实版需同目录放 aubo_sdk.dll/robot_proxy.dll）。
- 手动验证：命令行跑
  `python -c "from arm.collision_box_client import *; start_cpp_collision_server(); print(get_collision_client().ping())"`

## 协议（JSON，UTF-8，单请求单响应）
| 请求 | 响应 |
|---|---|
| `{"command":"ping"}` | `{"status":"pong"}` |
| `{"command":"add","name":"tool_box","link":"end_effector","sizes":[L,W,H],"poses":[x,y,z,rx,ry,rz]}` | `{"status":"ok","ret":0,"mode":"sdk"/"mock"}` |
| `{"command":"remove","name":"tool_box"}` | 同上 |
| 参数错误 / 未连接机器人 | `{"status":"error","msg":"...","mode":"..."}` |

> SDK 真实接口：`RobotAlgorithm::addCollisionBox(name, link_name, vector<vector> sizes,
> vector<vector> poses)` 与 `removeCollisionObject(name)`（见 lib/aubo_sdk.../include/aubo/robot/robot_algorithm.h）。
