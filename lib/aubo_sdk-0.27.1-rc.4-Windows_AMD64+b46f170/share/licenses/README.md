# AUBO SDK 许可说明 / AUBO SDK License Notes

本目录包含 AUBO SDK 的全部许可文件。就下列组件，AUBO（遨博（北京）智能科技股份有限公司）提供**二选一**许可：你可在《AUBO SDK 使用许可协议》与 `BSD 2-Clause License` 之间，任选其一适用。

## 双许可选择 / Dual-License Choice

**适用组件**：发布包中明确标注适用 `BSD-2-Clause` 的组件，包括 AUBO SDK 客户端动态链接库及配套二进制文件、配套的公有 API 头文件，以及发布包、组件清单或文件许可标识中明确指定适用 `BSD-2-Clause` 的其他文件。该范围与 `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE` 列明的一致。

**如何选择**：
- 选择 BSD 2-Clause：上述组件按 `BSD-2-Clause` 提供，只需遵守 `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE`；SDK 许可协议对该等组件的再分发等限制不适用。
- 选择 SDK 许可协议：上述组件按 `AUBO_SDK_LICENSE` 提供。

两种选择互斥，择一即可，**无需同时接受两份协议**。未被上述范围覆盖的 SDK 组件（控制器软件、服务端软件、固件、算法实现、内部工具及未明确标注的文件）仅适用 `AUBO_SDK_LICENSE`，不提供 BSD 选项。第三方软件继续适用其各自许可证（见 `third_party/`）。

---

This directory contains all AUBO SDK license files. For the components below, AUBO offers a choose-one-of-two license: you may apply either the AUBO SDK License Agreement or the BSD 2-Clause License, at your option.

**Covered components**: those explicitly marked `BSD-2-Clause` in the release package — the AUBO SDK client shared library and accompanying binaries, the accompanying public API headers, and any other files explicitly designated `BSD-2-Clause` in the package, component manifest, or file markings (same scope as `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE`).

**How to choose**:
- Choose BSD 2-Clause: covered components are provided under BSD-2-Clause; comply only with `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE`, and the SDK License's redistribution restrictions do not bind you for those components.
- Choose the SDK License: covered components are provided under `AUBO_SDK_LICENSE`.

The two choices are mutually exclusive: pick one to apply, and **no need to accept both agreements**. Components outside that scope (controller/server software, firmware, algorithm implementations, internal tools, unmarked files) are provided solely under `AUBO_SDK_LICENSE` and are not offered under BSD. Third-party software keeps its own licenses (see `third_party/`).

## 文件清单 / Files

- `AUBO_SDK_LICENSE.zh-CN.md` / `AUBO_SDK_LICENSE.en.md` — AUBO SDK 使用许可协议（EULA）
- `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE.zh-CN.md` / `AUBO_SDK_BSD_2_CLAUSE_LICENSE_NOTICE.en.md` — BSD 2-Clause 许可声明
- `third_party/` — 第三方软件许可证
