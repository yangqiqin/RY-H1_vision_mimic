# -*- coding: utf-8 -*-
"""
install_realsense_driver.py —— L515 驱动一键诊断与安装引导（解决 0x80070005）

背景（根因）：
  L515 若使用微软通用 UVC 驱动（usbvideo.inf），librealsense 在 Windows 上走
  MediaFoundation 后端枚举 RGB 流，会被系统拒绝（MFCreateDeviceSource 0x80070005）——
  表现为"设备能连电脑，但 Python/GUI 打开相机报拒绝访问"。
  安装 Intel RealSense 专属驱动后，librealsense 改用 WinUSB 后端，不再报错。

用法：
  python tools/install_realsense_driver.py          # 诊断 + 引导（推荐）
  python tools/install_realsense_driver.py --check  # 仅检测当前驱动
  python tools/install_realsense_driver.py --open   # 打开官方下载页

说明：
  驱动安装需要管理员权限 + 官方安装包，本脚本负责"检测 → 引导 → 验证"，
  无法自动替你安装（需下载 exe 并手动运行）。
"""

from __future__ import annotations
import os
import subprocess
import sys

# ---- 路径引导 ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse

REALSENSE_RELEASES_URL = "https://github.com/IntelRealSense/librealsense/releases"
# 适配 L515 的推荐版本（librealsense 2.55+ 移除 L515，必须 2.54 及以前）
RECOMMENDED_URL = ("https://github.com/IntelRealSense/librealsense/releases/tag/v2.54.2")


def check_driver() -> dict:
    """检测 L515 当前使用的驱动类型。返回 {has_l515, driver, detail}。"""
    out = {"has_l515": False, "driver": "unknown", "detail": ""}
    try:
        r = subprocess.run(["pnputil", "/enum-devices", "/class", "Camera"],
                           capture_output=True, text=True, timeout=20)
        text = r.stdout or ""
        # 定位 L515 段落（Intel RealSense 515 的 Device Description）
        l515_block = ""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "RealSense" in line and ("515" in line or "L515" in line):
                # 收集该设备段（到下一个 Instance ID 为止）
                block = [line]
                for nl in lines[i + 1:]:
                    if nl.strip().startswith("Instance ID"):
                        break
                    block.append(nl)
                l515_block = "\n".join(block)
                break
        if not l515_block:
            # 兜底：整段搜索
            if "RealSense" in text and ("515" in text or "L515" in text):
                l515_block = text
            else:
                out["has_l515"] = False
                return out
        out["has_l515"] = True
        if "usbvideo.inf" in l515_block:
            out["driver"] = "微软通用UVC(usbvideo.inf) ← 根因"
        else:
            out["driver"] = "Intel专属驱动 ✅"
        out["detail"] = l515_block[:500]
    except Exception as exc:
        out["detail"] = f"检测异常: {exc}"
    return out


def main():
    ap = argparse.ArgumentParser(description="L515 驱动诊断与安装引导")
    ap.add_argument("--check", action="store_true", help="仅检测驱动")
    ap.add_argument("--open", action="store_true", help="打开官方下载页")
    args = ap.parse_args()

    print("=" * 60)
    print("L515 驱动诊断（解决 0x80070005 拒绝访问）")
    print("=" * 60)

    if args.open:
        import webbrowser
        print(f"打开下载页: {RECOMMENDED_URL}")
        webbrowser.open(RECOMMENDED_URL)
        return

    info = check_driver()
    if not info["has_l515"]:
        print("⚠️  未在 Camera 类设备中找到 L515（RealSense 515）。")
        print("    请检查：USB3.0 直连 / 线缆 / 供电。")
        return
    print(f"✅ 找到 L515 设备")
    print(f"当前驱动: {info['driver']}")

    if info["driver"] == "Intel专属":
        print("\n✅ 已使用 Intel 专属驱动，理论上不会出现 0x80070005。")
        print("   若仍报错，请检查：管理员运行 / 设置→隐私→相机→允许桌面应用访问相机。")
    else:
        print("\n⚠️  L515 使用微软通用 UVC 驱动 → 这是 0x80070005 的根因！")
        print("\n★ 彻底解决方案（安装 Intel RealSense SDK 2.0 运行时）：")
        print("  ① 下载（推荐 2.54.2 版本，L515 最后支持版）：")
        print(f"     {RECOMMENDED_URL}")
        print("     或全部版本：")
        print(f"     {REALSENSE_RELEASES_URL}")
        print("     （选择 Windows 安装包，如 Intel.RealSense.SDK-WIN10-2.54.2.5684.exe）")
        print("  ② 以管理员身份运行安装程序，勾选安装设备驱动；")
        print("  ③ 安装完成后重新插拔 L515；")
        print("  ④ 用 Intel RealSense Viewer 确认能出图；")
        print("  ⑤ 重开本程序，运行:")
        print("     python tools/install_realsense_driver.py --check")
        print("     应显示『Intel专属』，GUI 打开相机即成功。")

    if args.check:
        return
    # 交互式引导
    try:
        ans = input("\n是否现在打开官方下载页？[y/N]: ").strip().lower()
        if ans == "y":
            import webbrowser
            webbrowser.open(RECOMMENDED_URL)
            print("已打开下载页。")
    except Exception:
        pass


if __name__ == "__main__":
    main()
