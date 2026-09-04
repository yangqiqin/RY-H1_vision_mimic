# -*- coding: utf-8 -*-
"""
cpp_src/build_collision_server.py —— 一键编译 C++ 碰撞盒服务端（PyCharm 里直接运行）

流程：
  1) 定位遨博 C++ SDK（lib/aubo_sdk-*-Windows_AMD64*/，含 include 与 lib/*.dll/.lib）
  2) 若本机有 MinGW(g++/gendef/dlltool)：
       为 aubo_sdk.dll、robot_proxy.dll 生成导入库(.a) → 编译【真实 SDK 版】(mode=sdk)
       并把两个 dll 拷到 bin/（exe 运行时需要）
     g++ 不可用时提示用 MSVC（见 docs/cpp碰撞盒服务编译与使用.md）
  3) 无论真实版是否成功，都先编译【演示版】(mode=mock) 保底放到 bin/
     （无 SDK 环境也能跑通 GUI 流程；GUI 会提示 mock 未真正启用）
  4) 结果写入 bin/build_result.txt

用法：PyCharm 打开本文件 → 右键 Run；或在 PyCharm Terminal:
      python cpp_src/build_collision_server.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "cpp_src", "collision_box_server.cpp")
BIN_DIR = os.path.join(ROOT, "bin")
OUT = os.path.join(BIN_DIR, "collision_box_server.exe")
RESULT = os.path.join(BIN_DIR, "build_result.txt")


def find_sdk() -> str:
    lib_dir = os.path.join(ROOT, "lib")
    if not os.path.isdir(lib_dir):
        return ""
    hits = [os.path.join(lib_dir, d) for d in os.listdir(lib_dir)
            if d.startswith("aubo_sdk-") and "Windows_AMD64" in d]
    return hits[0] if hits else ""


def run(cmd, cwd=None) -> tuple:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError as e:
        return 127, f"找不到程序: {e}"


def which(name: str) -> bool:
    return shutil.which(name) is not None


def main():
    os.makedirs(BIN_DIR, exist_ok=True)
    notes = []
    ok_sdk = False
    sdk = find_sdk()
    if not sdk:
        notes.append("未找到遨博 C++ SDK 目录（lib/aubo_sdk-*-Windows_AMD64*）→ 仅编演示版。")
    elif not (which("g++") and which("gendef") and which("dlltool")):
        notes.append("本机无 MinGW(g++/gendef/dlltool)。演示版编译可能失败；真实版请用 "
                     "MSVC（见 docs/cpp碰撞盒服务编译与使用.md）。")
    else:
        notes.append(f"使用 SDK: {os.path.basename(sdk)}")

        # ---- 1) 为 MSVC 编译的 dll 生成 MinGW 导入库并编真实版 ----
        sdk_lib = os.path.join(sdk, "lib")
        imp_dir = os.path.join(BIN_DIR, "imp")
        os.makedirs(imp_dir, exist_ok=True)
        try:
            for dll in ("aubo_sdk.dll", "robot_proxy.dll"):
                dll_path = os.path.join(sdk_lib, dll)
                if not os.path.isfile(dll_path):
                    notes.append(f"缺少 {dll}（{sdk_lib}）")
                    continue
                def_name = dll.replace(".dll", ".def")
                a_name = "lib" + dll.replace(".dll", ".dll.a")
                rc, out = run(["gendef", dll_path], cwd=imp_dir)
                if rc != 0:
                    notes.append(f"gendef {dll} 失败: {out.strip()[:200]}")
                    continue
                rc, out = run(["dlltool", "-d", os.path.join(imp_dir, def_name),
                               "-l", os.path.join(imp_dir, a_name),
                               "-D", dll, "-k"], cwd=imp_dir)
                if rc != 0:
                    notes.append(f"dlltool {dll} 失败: {out.strip()[:200]}")
                    continue
                notes.append(f"导入库已生成: {a_name}")
            # 编译真实版
            cmd = ["g++", "-O2", "-std=c++17", "-DUSE_REAL_AUBO_SDK",
                   "-I", os.path.join(sdk, "include"),
                   SRC,
                   "-L", imp_dir, "-laubo_sdk", "-lrobot_proxy",
                   "-L", sdk_lib, "-lws2_32",
                   "-o", os.path.join(BIN_DIR, "collision_box_server_sdk.exe")]
            rc, out = run(cmd)
            if rc == 0:
                # 真实版就绪：拷贝 dll 到 bin/，并替换主 exe 为真实版
                for dll in ("aubo_sdk.dll", "robot_proxy.dll"):
                    src_dll = os.path.join(sdk_lib, dll)
                    if os.path.isfile(src_dll):
                        shutil.copy2(src_dll, os.path.join(BIN_DIR, dll))
                shutil.move(os.path.join(BIN_DIR, "collision_box_server_sdk.exe"), OUT)
                ok_sdk = True
                notes.append("✅ 真实 SDK 版编译成功（mode=sdk），已放入 bin/，并附带 dll。")
            else:
                notes.append(f"真实版链接失败（将保留演示版）:\n{out.strip()[-400:]}")
        except Exception as e:
            notes.append(f"真实版编译异常: {e}")

    # ---- 2) 演示版保底编译 ----
    if not ok_sdk:
        rc, out = run(["g++", "-O2", "-std=c++17", SRC, "-o", OUT, "-lws2_32"])
        if rc == 0:
            notes.append("✅ 演示版(mock)编译成功，已放入 bin/collision_box_server.exe")
        else:
            notes.append(f"演示版编译失败（请在装有 MSVC 的环境编译）:\n{out.strip()[-400:]}")

    text = "\n".join(notes)
    try:
        with open(RESULT, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    print("\n".join(notes))
    print(f"\n结果已写入: {RESULT}")


if __name__ == "__main__":
    main()
