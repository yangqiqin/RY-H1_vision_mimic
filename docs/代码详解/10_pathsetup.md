# `lib/_pathsetup.py` 代码详解 —— 项目路径统一引导模块

> 所属项目：睿研 RY-H1(16) 灵巧手视觉动作模仿系统（Windows 版）
>
> 文件位置：`<根目录>/lib/_pathsetup.py`
>
> 本文件内容：`project_root()` / `ensure_root()` / `root_candidates()` 三个函数，外加一段说明问题的模块 docstring。
>
> 阅读本文后应能回答：**为什么直接运行 `python apps/test_hand.py` 会导入失败？内联两行引导是什么？`dirname(dirname(__file__))` 为什么恰好是项目根目录？本模块与入口脚本顶部的内联两行是什么关系？**

---

## 0. 文件元信息

| 项目 | 内容 |
|---|---|
| 绝对路径 | `<根目录>/lib/_pathsetup.py` |
| 模块性质 | 内部工具模块（下划线前缀 `_`，非公开 API，不参与业务逻辑） |
| 依赖 | 仅标准库：`os`、`sys`、`typing`（无任何第三方依赖） |
| 对外接口 | `project_root(anchor)`、`ensure_root(anchor)`、`root_candidates()` |
| 调用时机 | 入口脚本顶部（导入本项目任何模块**之前**）；hand 包内部加载 DLL/驱动时兜底 |
| 文件总行数 | 75 行（含注释） |

---

## 1. 这个模块解决什么问题（问题重述）

Python 运行一个脚本时，`sys.path` 里**默认只加入"脚本所在目录"**，而**不会**加入当前工作目录（CWD，即你敲 `python` 命令时所在的目录），更不会加入项目根目录。

以"在项目根目录执行 `python apps/test_hand.py`"为例，Python 的 `sys.path[0]` 是 `<根目录>/apps/`，此时：

1. **包导入失败**：`from hand import RYH1HandController` 中的 `hand` 包位于**根目录**下，而 `apps/` 里没有 `hand`，Python 在 `sys.path` 里找不到它 → `ModuleNotFoundError`；
2. **相对路径资源解析失败**：
   - `ctypes.CDLL("RyhandLibx64.dll")` 这种**裸文件名**加载，ctypes 会按"当前进程目录（= CWD）→ PATH → 系统目录"的顺序找 DLL。如果 CWD 是用户随便进的目录（比如 `C:\Users\xxx`），就找不到；
   - `from lib import PCANBasic`、`import ControlCAN` 这类驱动导入，同样依赖 `sys.path` 里存在根目录（或 `lib/`）；
   - 驱动 DLL（如 `ControlCAN.dll`）的加载依赖 CWD 或显式路径。

**解决思路**：每个入口脚本（`apps/*.py`、`gui/*.py`、`selfcheck.py` 等）在 import 本项目任何模块**之前**，先做两件事：

- ① 把**项目根目录**插入 `sys.path` 的最前面 → 让 `import hand / camera / vision / ...` 生效；
- ② `os.chdir(项目根目录)` → 把**当前工作目录**切到根目录 → 让 `RyhandLibx64.dll`、`ControlCAN.dll` 等相对路径查找生效。

本模块 `_pathsetup.py` 就是把"定位根目录 + 插 path + chdir"封装成三个小函数，并写成一份可复用的"路径引导"工具。

---

## 2. 模块 docstring 完整解读

docstring（第 1~29 行）是全文件最核心的"说明书"，逐段解读如下：

### 2.1 第一行：标题

```
_pathsetup.py —— 项目路径统一引导（解决"运行子目录单文件找不到根目录内容"）
```

说明模块定位：**路径统一引导**。"统一"体现在：所有入口脚本不再各自维护一套路径代码，而是遵循同一个模式（内联两行或调用本模块），把根目录定位逻辑收敛到一处。

### 2.2 "问题"段

```
问题：
  直接运行 `python apps/test_hand.py` 时，Python 只把脚本所在目录（apps/）
  加入 sys.path，导致：
    1) `from hand import ...` 等根目录包导入失败；
    2) ctypes.CDLL("RyhandLibx64.dll")、import PCANBasic / ControlCAN
       等相对路径资源（DLL、驱动文件）解析失败（依赖当前工作目录 CWD）。
```

要点：

- 第 1 条问题本质是 **`sys.path` 不含根目录**；
- 第 2 条问题本质是 **CWD 不对**（裸文件名加载 DLL、驱动文件查找都依赖 CWD）。注意这里把两类"相对路径资源"并列：`ctypes.CDLL("RyhandLibx64.dll")` 是**动态库**，`import PCANBasic / ControlCAN` 是**驱动 Python 模块**（`PCANBasic.py` 在 `lib/` 下），它们的共同点是"路径解析依赖 sys.path / CWD 这两个全局状态"。

### 2.3 "解决"段

```
解决：
  每个入口脚本（apps/*.py、gui/*.py、selfcheck.py 等）在 import 本项目模块
  **之前**调用本模块，完成两件事：
    ① 把项目根目录插入 sys.path  —— 让 `import hand/camera/vision/...` 生效；
    ② os.chdir(项目根目录)       —— 让 DLL/驱动文件的相对路径查找生效。
```

两个动作与两类问题一一对应：**① 插 sys.path → 解决导入问题；② chdir → 解决资源查找问题**。关键约束是"**在 import 本项目模块之前**"——`sys.path` 的修改必须在 `from hand import ...` 执行之前完成，否则 import 语句在解释器求值时就已经失败，事后补插没有意义。

### 2.4 "用法"段

```
用法（入口脚本顶部，放在所有本项目 import 之前）：
    # ---- 路径引导（必须最先执行，放在本项目 import 之前） ----
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(sys.path[0])
```

这是**主用方案**（内联两行）。逐行拆解：

| 行 | 作用 |
|---|---|
| `import os, sys` | 只导入标准库，不依赖任何本项目模块（这是它能"最先执行"的前提） |
| `sys.path.insert(0, dirname(dirname(abspath(__file__))))` | 由入口脚本自己的文件位置反推根目录，插入 `sys.path[0]`（最高优先级） |
| `os.chdir(sys.path[0])` | 技巧：刚 `insert(0, ...)` 之后 `sys.path[0]` 就是根目录，直接 chdir 过去，省去再算一遍路径 |

关于 `__file__` 的说明：直接运行 `python apps/test_hand.py` 时 `__file__` 可能是相对路径 `apps/test_hand.py`，`os.path.abspath()` 会基于**命令被执行时的 CWD** 把它补全为绝对路径。由于 shell 能解析到该文件，这个绝对路径一定是正确的——所以无论用户从哪个目录执行，这一行都能定位到根目录。

### 2.5 "说明"段

```
说明：
  * 也可直接 `import _pathsetup; _pathsetup.ensure_root(__file__)`，
    但内联两行最稳妥（不依赖任何外部模块即可运行）。
  * 本模块同时供 hand 包内部使用：加载 DLL 时把根目录加入候选路径，
    避免"在子目录运行但忘了 chdir"导致的加载失败。
```

两个信息点：

1. 给出了**替代用法**：`import _pathsetup; _pathsetup.ensure_root(__file__)`。但注明内联两行"最稳妥"——因为内联两行是纯标准库、纯文件系统操作，**不依赖任何 import 机制**；而 `import _pathsetup` 本身要求 `lib/`（或根目录下的 `lib` 命名空间包）已经能被导入，存在"先有鸡还是先有蛋"的循环依赖风险，所以只作为备选。
2. 明确了**本模块的第二个职责**：供 `hand` 包内部做"兜底"。即使入口脚本忘了 chdir、或用户直接在 REPL 里 `import hand`，hand 包在加载 DLL/驱动时也会主动把根目录、`lib/` 加入候选路径，尽力避免加载失败（详见第 7、8 节）。

---

## 3. 目录结构与"为什么 `dirname(dirname(__file__))` 是根目录"

### 3.1 项目目录树（与本模块相关部分）

```
<根目录>/                                      ← 项目根目录（一个文件夹）
│
├── apps/                        # 一级子目录：命令行入口脚本
│   ├── test_hand.py             #   入口：python apps/test_hand.py
│   ├── test_camera.py
│   ├── test_all.py
│   ├── diag_camera.py
│   ├── diag_motor.py
│   └── mimic_demo.py
│
├── gui/                         # 一级子目录：图形界面入口
│   ├── main_gui.py
│   └── hand_gui.py
│
├── hand/                        # 根目录包：灵巧手控制
│   ├── __init__.py
│   ├── hand_controller.py       #   ctypes 加载 RyhandLibx64.dll
│   └── transport.py             #   PCANBasic / ControlCAN 驱动加载
│
├── camera/                      # 根目录包：相机
├── vision/                      # 根目录包：视觉
│
├── lib/                         # 一级子目录：资源统一存放处
│   ├── _pathsetup.py            #   ★ 本文件
│   ├── PCANBasic.py             #   PCAN 驱动模块
│   ├── PCAN_ruiyan16.py
│   ├── ControlCAN.py / .dll     #   CANalyst-II 驱动（示例）
│   └── RyhandLibx64.dll         #   厂家 SDK 动态库
│
├── selfcheck.py                 # 根目录直下的入口脚本（深度 0）
└── ...（其他文件）
```

### 3.2 为什么 `dirname(dirname(__file__))` 是根目录

`os.path.dirname(p)` 的作用是取路径 `p` 的**父目录**（去掉最后一级）。

本模块自身位于 `<根目录>/lib/_pathsetup.py`，逐级计算：

```
__file__                          = <根目录>/lib/_pathsetup.py
dirname(__file__)                 = <根目录>/lib        （第 1 次取父目录）
dirname(dirname(__file__))        = <根目录>            （第 2 次取父目录）
```

所以"**本文件所在目录（lib/）的父目录**"就是项目根目录。这正是模块 docstring 里强调的前提：**"用户已把资源统一移到 lib/，因此本文件固定位于 `<根目录>/lib/`，深度恒为 1"**——只要这个布局不变，`dirname(dirname(__file__))` 就是根目录，且**与 CWD 无关、与用户从哪个目录启动无关**。

同理，`anchor` 参数（第 4 节）的数学依据是：**入口脚本位于一级子目录中**，如 `<根目录>/apps/test_hand.py`：

```
abspath(anchor)                   = <根目录>/apps/test_hand.py
dirname(abspath(anchor))          = <根目录>/apps        （第 1 次取父目录）
dirname(dirname(abspath(anchor))) = <根目录>             （第 2 次取父目录）
```

一句话总结：**"父目录的父目录"只在"目标文件深度为 1（在根目录的一个直接子文件夹里）"时成立**。`lib/_pathsetup.py` 和 `apps/xxx.py`、`gui/xxx.py` 都满足这个条件；而 `selfcheck.py` 在根目录直下（深度 0），它的入口引导只用了一层 `dirname`（见第 7 节对照表）。

---

## 4. `project_root(anchor)` 详解

```python
def project_root(anchor: Optional[str] = None) -> str:
    """项目根目录。

    本文件位于 <根目录>/lib/_pathsetup.py（用户已把资源统一移到 lib/），
    因此默认取本文件所在目录的父目录作为根目录。

    Args:
        anchor: 可选，若传入某入口文件路径，则取其父目录的父目录
                （apps/xxx.py -> 根目录）作为根目录；默认取 lib/ 的父目录。
    """
    if anchor is not None:
        return os.path.dirname(os.path.dirname(os.path.abspath(anchor)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

### 4.1 职责

**纯函数**：只负责"算出一个绝对路径字符串（项目根目录）"，**不修改任何全局状态**（不动 `sys.path`、不动 CWD、不做 chdir）。这是它与 `ensure_root` 的本质区别。

### 4.2 `anchor` 参数的两种取值分支

**分支 A：`anchor is not None`（显式传入某个文件路径）**

```python
return os.path.dirname(os.path.dirname(os.path.abspath(anchor)))
```

- 对 `anchor` 先做 `os.path.abspath()` 规范化（把相对路径补成绝对路径）；
- 再连续取两次父目录：`xxx.py → 所在目录 → 所在目录的父目录`；
- 适用场景：入口脚本调用 `project_root(__file__)`，`__file__` 指向 `apps/test_hand.py` 这类"一级子目录中的文件"，两级上跳正好落在根目录。

> ⚠️ 隐含假设：`anchor` 必须是**一级子目录中的文件**。若传入根目录直下的文件（如 `selfcheck.py`），会多跳一级得到"根目录的父目录"，结果错误。这也是为什么默认分支更稳妥。

**分支 B：`anchor is None`（默认，不传参）**

```python
return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

- `__file__` 是本模块自己的文件路径，即 `<根目录>/lib/_pathsetup.py`；
- 两级上跳：`lib/_pathsetup.py → lib/ → <根目录>`；
- **不依赖任何调用方信息**，只要本文件没被移动，任何地方调用都返回正确的根目录。

### 4.3 使用建议

- 需要"知道根目录在哪"但**不想改变** `sys.path` / CWD 时，用 `project_root()`；
- 典型用法：`root = project_root()`，然后基于 `root` 拼出 `<root>/lib/RyhandLibx64.dll` 之类的完整路径；
- 返回值总是绝对路径（因为内部经过了 `abspath`），可以放心与 `os.path.join` 拼接。

---

## 5. `ensure_root(anchor)` 详解

```python
def ensure_root(anchor: Optional[str] = None) -> str:
    """把项目根目录加入 sys.path 并切换到该目录。返回根目录绝对路径。

    在入口脚本顶部调用（放在本项目 import 之前）。
    """
    root = project_root(anchor)
    root = os.path.abspath(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        os.chdir(root)          # DLL / 驱动文件的相对路径查找依赖 CWD
    except OSError:
        pass
    return root
```

### 5.1 执行流程（4 步）

| 步骤 | 代码 | 作用 |
|---|---|---|
| 1 | `root = project_root(anchor)` | 复用第 4 节的定位逻辑，算出根目录 |
| 2 | `root = os.path.abspath(root)` | 再次规范化，确保 `root` 是绝对路径（`project_root` 虽已 abspath，这里显式再兜一次，保证后续 `in` / `insert` 比较的字符串形式一致） |
| 3 | `if root not in sys.path: sys.path.insert(0, root)` | **去重插入**：仅当根目录不在 `sys.path` 中才插入，且插到**最前面**（`index 0`，优先级最高） |
| 4 | `try: os.chdir(root) except OSError: pass` | 切换到根目录；chdir 失败只吞掉异常，不中断流程 |

### 5.2 `sys.path.insert(0, ...)` 的去重逻辑

```python
if root not in sys.path:
    sys.path.insert(0, root)
```

- **去重的意义**：`ensure_root` 可能被多次调用（入口引导调一次、hand 包内部兜底再调一次）。`sys.path` 中同一个路径出现多次虽不致命，但会造成冗余扫描、且后续 `sys.path[0]` 技巧（内联两行里 `os.chdir(sys.path[0])`）依赖"第一个元素就是根目录"，重复插入会破坏这一假设。因此先 `in` 判断再插入。
- **为什么 `insert(0)` 而不是 `append`**：`sys.path` 是**顺序查找**的，越靠前优先级越高。插到 0 号位可以保证：当系统里存在同名包（例如 pip 恰好装过一个叫 `hand` 的第三方包）时，**本项目根目录里的 `hand` 包优先被找到**，避免被同名包"顶掉"。
- **为什么不直接 `sys.path.insert(0, ...)` 无条件插入**：加上 `in` 判断后，重复调用是幂等的（idempotent），不会让 `sys.path` 越来越长。

### 5.3 `os.chdir(root)` 的目的

```python
try:
    os.chdir(root)          # DLL / 驱动文件的相对路径查找依赖 CWD
except OSError:
    pass
```

**为什么必须 chdir？** 因为存在三类"依赖 CWD 的相对路径查找"：

1. `ctypes.CDLL("RyhandLibx64.dll")` —— 传**裸文件名**时，ctypes 的查找顺序是：**当前进程工作目录（CWD）→ PATH 环境变量 → Windows 系统目录**。CWD 不对，裸名加载就失败；
2. `ctypes.CDLL("ControlCAN.dll")` / `windll.LoadLibrary(...)` 同理；
3. 某些驱动模块内部用相对路径打开自己的配置文件 / 附属 DLL（如 `PCANBasic` 加载 `PCANBasic.dll` 的逻辑），同样依赖 CWD。

`os.chdir(root)` 之后，进程的 CWD 变成根目录，而 DLL/驱动文件就在根目录或 `lib/` 下，裸名查找即可命中。

> 注意：**chdir 是进程级全局操作**，一旦执行，整个进程后续所有相对路径（包括用户传的相对参数、程序里打开的相对文件路径）都相对根目录解析——这是设计意图（统一基准），但也是使用上需要注意的副作用（见第 9 节 FAQ）。

### 5.4 异常处理：`except OSError: pass`

`os.chdir` 在目录不存在、无权限等情况下会抛 `OSError`。这里**故意吞掉**，原因：

- chdir 只是"优化"——让裸文件名能通过 CWD 命中 DLL；
- 即使 chdir 失败，第 3 步 `sys.path` 已经插好了，且 hand 包的 DLL 加载逻辑（`hand_controller._load_lib`）会**显式构造完整路径**候选（`<root>/lib/RyhandLibx64.dll`），不依赖 CWD 也能加载；
- 因此 chdir 失败不应把整个初始化流程搞挂（例如在只读目录、或特殊环境里运行自检脚本时，程序仍应能继续）。

### 5.5 返回值

返回 `root`（根目录的绝对路径字符串）。调用方拿到返回值后可以直接基于它拼资源路径，不必再调用 `project_root()` 算一次。

---

## 6. `root_candidates()` 详解

```python
def root_candidates() -> list:
    """返回应搜索 DLL/驱动文件的目录候选列表（根目录优先）。"""
    roots = [os.getcwd()]
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in roots:
        roots.append(here)
    return roots
```

### 6.1 职责

**查询型工具**：返回"应该去哪里找 DLL / 驱动文件"的**候选目录列表**。与 `ensure_root` 不同，它**不修改任何全局状态**（不动 `sys.path`、不 chdir），只是给出建议搜索目录。

### 6.2 返回的候选列表

```
[当前工作目录 CWD, 本文件所在目录（lib/）]   ← 若两者相同则只有 1 个元素
```

构造过程：

1. `roots = [os.getcwd()]` —— 第一个候选是**当前工作目录**。在正常流程下（入口已做引导），CWD 已被 `os.chdir` 到根目录，所以此时 CWD == 根目录 → **根目录排在第一位**，这正对应 docstring 说的"根目录优先"；
2. `here = os.path.dirname(os.path.abspath(__file__))` —— 第二个候选是**本模块所在目录**，即 `lib/`（资源统一存放处，DLL/驱动文件大多在这里）；
3. `if here not in roots: roots.append(here)` —— **去重追加**：如果 CWD 恰好就是 `lib/`（例如用户 `cd lib` 后运行），就不再重复添加。

### 6.3 设计意图与使用方式

- 它回答的问题是："给一个 DLL 裸名，应该到哪几个目录去拼完整路径逐个尝试？"
- 与 `hand_controller._load_lib()` 中的候选搜索逻辑（`CWD → 根目录 → 根/lib/`）**功能等价**——hand 包目前在自己内部内联实现了这份逻辑（见第 8 节），本函数是把它抽成通用工具的版本，供后续需要"搜索 DLL 目录"的代码复用；
- 返回值可以直接这样用：

```python
for d in root_candidates():
    p = os.path.join(d, "RyhandLibx64.dll")
    if os.path.isfile(p):
        self._lib = ctypes.CDLL(p)
        break
```

---

## 7. 与入口脚本"内联两行引导"的关系（主用 vs 兜底）

### 7.1 两层机制的分工总览

| 层次 | 位置 | 内容 | 角色 |
|---|---|---|---|
| **主用方案** | 每个入口脚本顶部 | 内联两行：`sys.path.insert(0, ...)` + `os.chdir(sys.path[0])` | 负责"一启动就把环境摆正"，**保证 import 成功** |
| **兜底方案** | 本模块 `ensure_root()` | 封装同款逻辑的函数 | 供 hand 包内部在加载 DLL / 驱动时再兜一次底 |
| **兜底方案 2** | `hand/transport.py::_ensure_driver_path()` | 把根目录 + `lib/` 插入 `sys.path` | 保证 `from lib import PCANBasic` / `import ControlCAN` 一定可导入 |

### 7.2 为什么"内联两行"是主用方案，而不是 `ensure_root()`

docstring 的原话：**"内联两行最稳妥（不依赖任何外部模块即可运行）"**。深层原因：

1. **无导入依赖**：内联两行只用 `os`、`sys` 两个标准库，且不 import 本项目任何模块。而 `import _pathsetup` 本身需要"`lib/` 或根目录已在 `sys.path` 里"才能成功——但引导的目的恰恰是**把根目录加进 `sys.path`**，形成循环依赖。用内联两行就完全绕开了这个问题；
2. **文件系统定位，与 import 机制解耦**：内联两行靠 `__file__` 的绝对路径反推根目录，纯文件系统操作，即使 `sys.path` 一团糟也能正确执行；
3. **入口脚本内聚**：每个入口脚本自带头部引导，单文件拷贝到任何位置都能独立运行，不依赖别的模块存在。

### 7.3 各入口脚本的引导对照表

| 入口脚本 | 文件深度 | 内联两行的 `dirname` 层数 | 结果 |
|---|---|---|---|
| `apps/test_hand.py` 等 `apps/*.py` | 1（在 `apps/` 内） | 2 层：`dirname(dirname(abspath(__file__)))` | `apps/ → 根目录` ✅ |
| `gui/main_gui.py`、`gui/hand_gui.py` | 1（在 `gui/` 内） | 2 层 | `gui/ → 根目录` ✅ |
| `selfcheck.py` | 0（根目录直下） | 1 层：`dirname(abspath(__file__))` | `根目录` ✅ |

注意 `selfcheck.py` 的差异：它在根目录直下，所以只用**一层** `dirname`。这印证了第 3 节的结论——**"上跳层数 = 文件深度"**，两层 `dirname` 只对一级子目录中的文件成立。

### 7.4 两条路径的等价性

内联两行与 `ensure_root()` 做的事情**完全等价**（都是"插根目录进 `sys.path` + chdir 到根目录"），只是实现细节略有不同：

| 步骤 | 内联两行 | `ensure_root(anchor)` |
|---|---|---|
| 算根目录 | `dirname(dirname(abspath(__file__)))` | `project_root(anchor)`（内部同款算法） |
| 插 path | 无条件 `insert(0, ...)` | 先 `in` 去重再 `insert(0, ...)` |
| chdir | `os.chdir(sys.path[0])`（利用刚插入的元素） | `os.chdir(root)`，且 `except OSError: pass` 容错 |
| 返回值 | 无 | 返回根目录绝对路径 |

---

## 8. hand 包内部如何使用（兜底场景实例）

`_pathsetup.py` 的第二个职责是"供 hand 包内部兜底"。虽然 hand 包目前没有直接 `import _pathsetup`，但它的两处内部逻辑与本模块是**同一思想**的落地，理解它们就理解了本模块的价值：

### 8.1 `hand/transport.py::_ensure_driver_path()` —— sys.path 兜底

```python
def _ensure_driver_path(self):
    """确保项目根目录与 lib/ 在 sys.path 中（驱动文件 PCANBasic.py / ControlCAN.py）。
    资源统一放在 lib/（模型/驱动/参考），同时保留根目录兼容旧布局。
    即使入口脚本已做路径引导，这里再兜底一次。
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
    for d in (here, os.path.join(here, "lib")):
        if d not in sys.path:
            sys.path.insert(0, d)
```

- 它在 `open()` 时被调用，把**根目录**和**根/lib/**都插入 `sys.path`；
- 之后 `from lib import PCANBasic`（PCAN 模式）才能成功——因为 `PCANBasic.py` 在 `lib/` 下；
- 注释明确写了"**即使入口脚本已做路径引导，这里再兜底一次**"——这正是本模块 docstring 里"避免在子目录运行但忘了 chdir 导致的加载失败"的落地。

### 8.2 `hand/hand_controller.py::_load_lib()` —— DLL 候选路径兜底

```python
search_dirs = [os.getcwd()]
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
for d in (here, os.path.join(here, "lib")):
    if d not in search_dirs:
        search_dirs.append(d)
...
for d in search_dirs:
    for name in _DEFAULT_LIBS:          # _DEFAULT_LIBS = ["RyhandLibx64.dll", ...]
        candidates.append(os.path.join(d, name))
# 保留裸名（依赖系统 PATH / CWD）
candidates += _DEFAULT_LIBS
```

- 它把 `RyhandLibx64.dll` 的查找范围扩展为：**CWD → 根目录 → 根/lib/** 的完整路径，外加裸名兜底；
- 也就是说：**即使 CWD 不在 DLL 所在目录**（忘了 chdir、或 REPL 里直接 import），只要 DLL 在根目录或 `lib/` 下，用完整路径也能加载成功——这就是"兜底"的含义；
- `root_candidates()`（第 6 节）就是把这个 `search_dirs` 逻辑抽成通用函数的版本。

---

## 9. 常见问题（FAQ）

### 9.1 为什么在子目录运行（或从别的目录启动）仍可能找不到 DLL？

DLL 加载失败通常有以下几个原因，按可能性排序：

1. **CWD 不是 DLL 所在目录**：`ctypes.CDLL("RyhandLibx64.dll")` 裸名加载依赖 CWD。入口脚本的 `os.chdir(sys.path[0])` 只在入口脚本运行时生效；如果你在 REPL 里 `import hand`、或自己写脚本时忘了引导、或引导代码被放在了 import 之后，CWD 就是启动时的任意目录 → 裸名找不到。**对策**：用完整路径（`root_candidates()` 拼路径逐个试），这正是 hand 包 `_load_lib` 做的事；
2. **DLL 在 `lib/` 而 CWD 是根目录**：裸名查找只查 CWD（根目录），不查 `lib/`，所以 `RyhandLibx64.dll` 只放在 `lib/` 时裸名依然失败。**对策**：`os.path.join(root, "lib", "RyhandLibx64.dll")` 完整路径，或把 DLL 也复制一份到根目录（不推荐，资源已统一到 `lib/`）；
3. **驱动 DLL 依赖链**：`PCANBasic.py` / `ControlCAN.py` 内部还要加载自己的 `PCANBasic.dll` / `ControlCAN.dll`，这些 DLL 的查找同样依赖 CWD 或它们所在目录被加入 `os.add_dll_directory()`（较新 Windows 的安全机制）。若入口已 chdir 到根目录、且驱动 DLL 在根目录或 `lib/`，一般能命中；若还不行，需要确认驱动 DLL 确实存在且位数（x64/x86）匹配 Python 解释器位数。

### 9.2 `os.chdir` 会带来哪些影响（副作用）？

`os.chdir` 是**进程级全局操作**，一旦执行，进程内**所有**相对路径都相对新 CWD（根目录）解析：

| 影响面 | 具体表现 |
|---|---|
| **相对文件读写** | 程序里 `open("config.yaml")`、`np.load("model.npy")`、`cv2.imwrite("out.jpg")` 等，都会读写**根目录**下的同名文件，而不是脚本所在目录或用户启动目录下的文件 |
| **日志文件位置** | `logging.FileHandler("logs/app.log")` 的日志会写到**根目录/logs/**。若用户在别的目录期望看到日志，位置会"不对"——但这是设计意图：无论从哪启动，日志位置都统一 |
| **用户传入的相对参数** | 如 `python apps/test_hand.py --lib lib/x.dll` 里的相对路径 `lib/x.dll`，也会相对根目录解析 |
| **好处** | 全进程路径基准统一：同一份代码从任何目录启动，资源定位结果一致，避免"换个目录跑就崩" |

> 提示：如果某个模块需要在"用户原目录"下读写文件，应在 chdir **之前**先 `os.path.abspath` 保存原路径，或用绝对路径打开。

### 9.3 为什么内联两行必须放在所有本项目 import 之前？

- `from hand import ...` 在**解释器执行到这一行时**就立即查找并导入，如果那时根目录还没进 `sys.path`，直接 `ModuleNotFoundError`，之后再补插已经来不及；
- `ctypes.CDLL("RyhandLibx64.dll")` 在 hand 包**模块级或 `__init__` 时**就可能执行，同理需要在之前完成 chdir；
- 因此引导必须位于入口文件**最顶部**、且只依赖标准库（`os`/`sys`）。

### 9.4 为什么用 `sys.path.insert(0, ...)` 而不是 `append(...)`？

`sys.path` 是顺序查找：**先出现的路径优先**。`insert(0)` 把根目录放到最前面，保证：

- 根目录下的 `hand` / `camera` / `vision` / `lib` 包优先命中；
- 即便环境中存在同名第三方包（pip 装过 `hand` 之类的），也不会覆盖本项目的包。

### 9.5 `project_root(anchor)` 传什么参数才不会出错？

- 传**一级子目录中的文件**（如 `__file__` 位于 `apps/`、`gui/`）：两级上跳 = 根目录，正确；
- 传**根目录直下的文件**（如 `selfcheck.py`）：两级上跳 = 根目录的父目录，**错误**（会多跳一级）；
- **最稳妥**：不传参（默认用 `lib/_pathsetup.py` 自己的位置推导），只要本文件没有被移动，任何调用都返回正确根目录。

### 9.6 `ensure_root` 里 chdir 失败为什么被吞掉（`except OSError: pass`）？

- chdir 只是"优化裸名查找"的辅助手段，不是必需品；
- 即使失败，`sys.path` 已插好，且 hand 包的 DLL 加载用**完整路径候选**兜底，仍可工作；
- 若 chdir 失败直接抛异常，会打断整个初始化流程，让"只读目录 / 特殊环境下的自检"这类场景无法运行。

### 9.7 `root_candidates()` 和 `ensure_root()` 有什么区别？

| | `ensure_root()` | `root_candidates()` |
|---|---|---|
| 修改 `sys.path` | ✅ 会（插入根目录） | ❌ 不会 |
| 修改 CWD | ✅ 会（chdir 根目录） | ❌ 不会 |
| 返回值 | 根目录绝对路径 | `[CWD, lib/]` 候选目录列表 |
| 用途 | 入口引导（改环境） | 查询（只读，供 DLL 搜索拼路径） |

---

## 10. 附：源码全文（75 行）

```python
# -*- coding: utf-8 -*-
"""
_pathsetup.py —— 项目路径统一引导（解决"运行子目录单文件找不到根目录内容"）

问题：
  直接运行 `python apps/test_hand.py` 时，Python 只把脚本所在目录（apps/）
  加入 sys.path，导致：
    1) `from hand import ...` 等根目录包导入失败；
    2) ctypes.CDLL("RyhandLibx64.dll")、import PCANBasic / ControlCAN
       等相对路径资源（DLL、驱动文件）解析失败（依赖当前工作目录 CWD）。

解决：
  每个入口脚本（apps/*.py、gui/*.py、selfcheck.py 等）在 import 本项目模块
  **之前**调用本模块，完成两件事：
    ① 把项目根目录插入 sys.path  —— 让 `import hand/camera/vision/...` 生效；
    ② os.chdir(项目根目录)       —— 让 DLL/驱动文件的相对路径查找生效。

用法（入口脚本顶部，放在所有本项目 import 之前）：
    # ---- 路径引导（必须最先执行，放在本项目 import 之前） ----
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(sys.path[0])

说明：
  * 也可直接 `import _pathsetup; _pathsetup.ensure_root(__file__)`，
    但内联两行最稳妥（不依赖任何外部模块即可运行）。
  * 本模块同时供 hand 包内部使用：加载 DLL 时把根目录加入候选路径，
    避免"在子目录运行但忘了 chdir"导致的加载失败。
"""

from __future__ import annotations

import os
import sys
from typing import Optional


def project_root(anchor: Optional[str] = None) -> str:
    """项目根目录。

    本文件位于 <根目录>/lib/_pathsetup.py（用户已把资源统一移到 lib/），
    因此默认取本文件所在目录的父目录作为根目录。

    Args:
        anchor: 可选，若传入某入口文件路径，则取其父目录的父目录
                （apps/xxx.py -> 根目录）作为根目录；默认取 lib/ 的父目录。
    """
    if anchor is not None:
        return os.path.dirname(os.path.dirname(os.path.abspath(anchor)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_root(anchor: Optional[str] = None) -> str:
    """把项目根目录加入 sys.path 并切换到该目录。返回根目录绝对路径。

    在入口脚本顶部调用（放在本项目 import 之前）。
    """
    root = project_root(anchor)
    root = os.path.abspath(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        os.chdir(root)          # DLL / 驱动文件的相对路径查找依赖 CWD
    except OSError:
        pass
    return root


def root_candidates() -> list:
    """返回应搜索 DLL/驱动文件的目录候选列表（根目录优先）。"""
    roots = [os.getcwd()]
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in roots:
        roots.append(here)
    return roots
```

---

## 附：一句话总结

> **入口脚本顶部用"内联两行"把根目录插进 `sys.path` 并 chdir 过去（主用方案，纯标准库、零依赖、最先执行）；本模块把同一套逻辑封装成 `project_root` / `ensure_root` / `root_candidates` 三个函数（备用方案），并作为 hand 包内部加载 DLL / 驱动时的兜底，确保"忘了 chdir、在子目录运行"也不会加载失败。**
