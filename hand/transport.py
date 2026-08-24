# -*- coding: utf-8 -*-
"""
transport.py —— Windows 通信传输层（PCAN / CANalyst-II / RS485）

负责把 RyCAN SDK 的回调 CanMsg -> 底层硬件发送，以及接收硬件帧 -> CanMsg。
参考知识库官方 demo `RyHandLibCANII_rs485_pcan_16.py` 的 bus_write/bus_read 实现。

支持三种通信方式（Windows）：
  1. PCAN（Peak PCAN-USB，1Mbps）       —— 需要 PCANBasic.py + PCAN 驱动
  2. CANalyst-II（周立功 USB-CAN，1Mbps）—— 需要 ControlCAN.py + ControlCAN.dll
  3. RS485（5Mbps 串口，半双工）         —— 需要 pyserial，帧格式见下

RS485 封包格式（demo）：
  | 0xA5 | id_lo | id_hi | len | data[0..len-1] | check(和校验) |

依赖：
  pip install pyserial
  # PCAN / CANII 还需把官方驱动文件（PCANBasic.py / ControlCAN.py/.dll）放同目录

用法：
  from hand.transport import CanTransport
  tr = CanTransport(method="pcan")     # "pcan" | "canii" | "rs485"
  tr.open()
  tr.send(can_id, data_bytes)
  tr.close()
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("transport")


class CanTransport:
    """Windows CAN/RS485 传输层。send() 由 SDK 写回调调用；recv 线程喂给 SDK。"""

    def __init__(self, method: str = "pcan", rs485_port: str = "COM3",
                 rs485_baud: int = 5000000):
        """
        Args:
            method: "pcan"（默认）| "canii" | "rs485"
            rs485_port / rs485_baud: RS485 模式参数
        """
        self.method = method.lower()
        self.rs485_port = rs485_port
        self.rs485_baud = rs485_baud

        self._pcan = None
        self._canii = None
        self._ser = None
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_frame: Optional[Callable[[int, bytes], None]] = None

    # ------------------------------------------------------------------
    def _ensure_driver_path(self):
        """确保项目根目录与 lib/ 在 sys.path 中（驱动文件 PCANBasic.py / ControlCAN.py）。

        资源统一放在 lib/（模型/驱动/参考），同时保留根目录兼容旧布局。
        即使入口脚本已做路径引导，这里再兜底一次。
        """
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
        for d in (here, os.path.join(here, "lib")):
            if d not in sys.path:
                sys.path.insert(0, d)

    # ------------------------------------------------------------------
    def open(self):
        if self.method == "pcan":
            self._open_pcan()
        elif self.method == "canii":
            self._open_canii()
        elif self.method == "rs485":
            self._open_rs485()
        else:
            raise ValueError(f"未知通信方式: {self.method}")
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()
        logger.info("[transport] %s 已打开", self.method)

    # ---- PCAN ----
    def _open_pcan(self):
        self._ensure_driver_path()
        from lib import PCANBasic as pcan
        dev = pcan.PCANBasic()
        res = dev.Initialize(pcan.PCAN_USBBUS1, pcan.PCAN_BAUD_1M)
        if res != pcan.PCAN_ERROR_OK:
            raise RuntimeError(f"PCAN 初始化失败，错误码 {res}（请确认 PCAN-USB 已插入、驱动已装）")
        self._pcan = (pcan, dev)
        logger.info("PCAN 初始化成功（1Mbps）")

    # ---- CANalyst-II ----
    def _open_canii(self):
        self._ensure_driver_path()
        import ControlCAN as cc
        if cc.dll.VCI_OpenDevice(cc.VCI_USBCAN2, 0, 0) != 1:
            raise RuntimeError("CANalyst-II 打开设备失败（请确认 USB-CAN 已插入、ControlCAN.dll 同目录）")
        cfg = cc.VCI_INIT_CONFIG()
        cfg.AccCode = 0x00000000
        cfg.AccMask = 0xFFFFFFFF
        cfg.Filter = 0
        cfg.Timing0 = 0x00          # 1Mbps
        cfg.Timing1 = 0x14
        cfg.Mode = 0
        if cc.dll.VCI_InitCAN(cc.VCI_USBCAN2, 0, 0, ctypes_byref(cfg)) != 1:
            cc.dll.VCI_CloseDevice(cc.VCI_USBCAN2, 0)
            raise RuntimeError("CANalyst-II 初始化失败")
        if cc.dll.VCI_StartCAN(cc.VCI_USBCAN2, 0, 0) != 1:
            cc.dll.VCI_CloseDevice(cc.VCI_USBCAN2, 0)
            raise RuntimeError("CANalyst-II 启动失败")
        self._canii = cc
        logger.info("CANalyst-II 初始化成功（1Mbps, dev0/can0）")

    # ---- RS485 ----
    def _open_rs485(self):
        import serial
        try:
            self._ser = serial.Serial(self.rs485_port, self.rs485_baud, timeout=1)
        except Exception as exc:
            raise RuntimeError(f"RS485 串口 {self.rs485_port} 打开失败: {exc}（请确认串口号与 5Mbps 支持）")
        logger.info("RS485 串口 %s @ %d 打开成功", self.rs485_port, self.rs485_baud)

    # ------------------------------------------------------------------
    def send(self, can_id: int, data: bytes):
        """发送一帧（SDK 写回调调用）。"""
        if self.method == "pcan":
            from lib import PCANBasic as pcan
            _, dev = self._pcan
            msg = pcan.TPCANMsg()
            msg.ID = can_id
            msg.MSGTYPE = pcan.PCAN_MESSAGE_STANDARD
            msg.LEN = len(data)
            for i in range(min(len(data), 8)):
                msg.DATA[i] = data[i]
            res = dev.Write(pcan.PCAN_USBBUS1, msg)
            if res != pcan.PCAN_ERROR_OK:
                logger.warning("PCAN 发送失败: %s", res)

        elif self.method == "canii":
            cc = self._canii
            frame = cc.VCI_CAN_OBJ()
            frame.ID = can_id
            frame.SendType = 1
            frame.RemoteFlag = 0
            frame.ExternFlag = 0
            frame.DataLen = len(data)
            for i in range(min(len(data), 8)):
                frame.Data[i] = data[i]
            cc.dll.VCI_Transmit(cc.VCI_USBCAN2, 0, 0, ctypes_byref(frame), 1)

        elif self.method == "rs485":
            frame = bytearray([0xA5, can_id & 0xFF, (can_id >> 8) & 0xFF, len(data)])
            frame.extend(data)
            check = sum(frame) & 0xFF
            frame.append(check)
            self._ser.write(bytes(frame))

    # ------------------------------------------------------------------
    def _rx_loop(self):
        while self._running:
            try:
                if self.method == "pcan":
                    self._rx_pcan()
                elif self.method == "canii":
                    self._rx_canii()
                elif self.method == "rs485":
                    self._rx_rs485()
            except Exception as exc:  # pragma: no cover
                logger.debug("rx loop: %s", exc)
            time.sleep(0.001)

    def _rx_pcan(self):
        from lib import PCANBasic as pcan
        _, dev = self._pcan
        res, msg, _ts = dev.Read(pcan.PCAN_USBBUS1)
        if res == pcan.PCAN_ERROR_OK and msg.LEN > 0:
            self._dispatch(msg.ID, bytes(msg.DATA[:msg.LEN]))

    def _rx_canii(self):
        cc = self._canii
        buf = (cc.VCI_CAN_OBJ * 100)()
        num = cc.dll.VCI_Receive(cc.VCI_USBCAN2, 0, 0, buf, 100, 0)
        if num > 0 and num < 0xFFFFFFFF:
            for i in range(num):
                f = buf[i]
                self._dispatch(f.ID, bytes(f.Data[:f.DataLen]))

    def _rx_rs485(self):
        if self._ser is None or self._ser.in_waiting <= 0:
            return
        data = self._ser.read(self._ser.in_waiting)
        # 解析 0xA5 帧（与 demo bus_read_callback 一致）
        i = 0
        while i < len(data):
            if data[i] != 0xA5:
                i += 1
                continue
            if i + 4 > len(data):
                break
            can_id = data[i + 1] | (data[i + 2] << 8)
            dlen = data[i + 3]
            if i + 4 + dlen + 1 > len(data):
                break
            payload = bytes(data[i + 4:i + 4 + dlen])
            check = sum(data[i:i + 4 + dlen]) & 0xFF
            if check == data[i + 4 + dlen]:
                self._dispatch(can_id, payload)
            i += 4 + dlen + 1

    def _dispatch(self, can_id: int, payload: bytes):
        if self._on_frame is not None:
            self._on_frame(can_id, payload)

    # ------------------------------------------------------------------
    def close(self):
        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=1.0)
        try:
            if self.method == "pcan" and self._pcan:
                from lib import PCANBasic as pcan
                _, dev = self._pcan
                dev.Uninitialize(pcan.PCAN_USBBUS1)
            elif self.method == "canii" and self._canii:
                self._canii.dll.VCI_CloseDevice(self._canii.VCI_USBCAN2, 0)
            elif self._ser is not None:
                self._ser.close()
        except Exception as exc:  # pragma: no cover
            logger.debug("close: %s", exc)
        logger.info("[transport] 已关闭")


def ctypes_byref(obj):
    """ctypes.byref 便捷封装（保持 import 轻量）。"""
    import ctypes
    return ctypes.byref(obj)
