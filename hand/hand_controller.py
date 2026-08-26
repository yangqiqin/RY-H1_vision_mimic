# -*- coding: utf-8 -*-
"""
hand_controller.py —— RY-H1(16) 灵巧手高层控制器（Windows 版）

职责：
  * 通过 ctypes 加载厂家 RyCAN SDK（RyhandLibx64.dll / libRyhand*.so）
  * 初始化总线（对齐官方 demo：hook=40、listen=33、32 个 AddListen）
  * 提供 16 关节弧度控制 / 单电机位置控制 / 状态读取 / 连接性自检

通信传输由 hand.transport.CanTransport 完成（PCAN / CANII / RS485）。

用法：
  from hand import RYH1HandController
  hand = RYH1HandController(method="pcan")     # "pcan" | "canii" | "rs485"
  hand.open()
  hand.check_connection()                       # 连接性自检
  hand.move_joints(angles_rad_16, speed=1000, current=75, hand_lr=1)
  hand.open_hand(); hand.close_hand()
  hand.close()
"""

from __future__ import annotations

import ctypes
import logging
import math
import os
import time
from typing import List, Optional

from .angles2motor import angles_to_motor_cmds
from .hand_config import HAND_CONFIG, JOINT_NUM, POS_MAX

logger = logging.getLogger("hand")

_DEFAULT_LIBS = [
    "RyhandLibx64.dll",      # Windows x64
    "RyhandLibx86.dll",      # Windows x86
    "libRyhand64_1.so",      # Linux x86_64
    "libRyhandArm64.so",     # Linux arm64
    "libRyhand.so",
]


# ---------------------------------------------------------------------------
# ctypes 结构体（与入门指南一致）
# ---------------------------------------------------------------------------
class CanMsgT(ctypes.Structure):
    _fields_ = [
        ("ulId", ctypes.c_uint32),
        ("ucLen", ctypes.c_uint8),
        ("pucDat", ctypes.c_uint8 * 64),
    ]


BusWriteT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(CanMsgT))
CallbackT = ctypes.CFUNCTYPE(None, ctypes.POINTER(CanMsgT), ctypes.c_void_p)


class MsgHookT(ctypes.Structure):
    _fields_ = [
        ("ucEn", ctypes.c_uint8),
        ("ucAlive", ctypes.c_uint8),
        ("pstuMsg", ctypes.POINTER(CanMsgT)),
        ("funCbk", CallbackT),
    ]


class ServoDataT(ctypes.Union):
    _fields_ = [("pucDat", ctypes.c_uint8 * 64)]


class MsgListenT(ctypes.Structure):
    _fields_ = [
        ("stuListen", MsgHookT),
        ("stuRet", ServoDataT),
        ("ucConfidence", ctypes.c_uint8),
    ]


class RyCanServoBusT(ctypes.Structure):
    _fields_ = [
        ("pusTicksMs", ctypes.POINTER(ctypes.c_uint16)),
        ("usTicksPeriod", ctypes.c_uint16),
        ("usHookNum", ctypes.c_uint16),
        ("usListenNum", ctypes.c_uint16),
        ("pstuHook", ctypes.POINTER(MsgHookT)),
        ("pstuListen", ctypes.POINTER(MsgListenT)),
        ("pfunWrite", BusWriteT),
    ]


# 故障状态码解释（手册 MFingerInfo_t status / enret_t）
SERVO_STATUS_TEXT = {
    0:  "正常",
    1:  "电机过温告警",
    2:  "电机过温保护",
    3:  "电机低压保护",
    4:  "电机过压保护",
    5:  "电机过流保护",
    6:  "电机力矩保护",
    7:  "电机熔丝位错保护",
    8:  "电机堵转保护",
    9:  "驱动器异常保护",
    10: "电机hall错保护",
    11: "电机找零告警（未完成回零，行程受限！需执行回零）",
}


def status_text(status: int) -> str:
    """故障码 -> 中文解释（未知码原样返回）。"""
    return SERVO_STATUS_TEXT.get(status, f"未知状态({status})")


class ServoInfo:
    """单电机状态回馈（MFingerInfo_t）。"""
    __slots__ = ("status", "position", "velocity", "current", "tactile")

    def __init__(self, status=0, position=0, velocity=0, current=0, tactile=0):
        self.status = status
        self.position = position
        self.velocity = velocity
        self.current = current
        self.tactile = tactile

    @property
    def status_text(self) -> str:
        return status_text(self.status)

    def __repr__(self):
        return (f"ServoInfo(status={self.status}[{self.status_text}], P={self.position}, "
                f"V={self.velocity}, I={self.current}, F={self.tactile})")


class RYH1HandController:
    """RY-H1(16) 灵巧手控制器（Windows 版）。"""

    def __init__(
        self,
        method: str = "pcan",
        lib_path: Optional[str] = None,
        rs485_port: str = "COM3",
        rs485_baud: int = 5000000,
        default_speed: int = HAND_CONFIG["default_speed"],
        default_max_current: int = HAND_CONFIG["default_max_current"],
        hand_lr: int = 1,
    ):
        """
        Args:
            method: 通信方式 "pcan"（默认）| "canii" | "rs485"
            lib_path: 厂家 SDK 库路径（None 自动按平台找 RyhandLibx64.dll 等）
            rs485_port / rs485_baud: RS485 模式参数
            hand_lr: 1=右手（默认），0=左手（每指 M1/M2 交换）
        """
        self.method = method.lower()
        self.rs485_port = rs485_port
        self.rs485_baud = rs485_baud
        self.default_speed = default_speed
        self.default_max_current = default_max_current
        self.hand_lr = hand_lr

        self._lib = None
        self._tr = None
        self.bus = RyCanServoBusT()
        self._ticks = ctypes.c_uint16(0)
        self._rx_thread = None
        self._running = False
        self._last_servo_info = {}      # motor_id -> ServoInfo
        self._load_lib(lib_path)

    # ------------------------------------------------------------------
    def _load_lib(self, lib_path: Optional[str]):
        # 候选搜索目录：当前目录 + 项目根目录 + lib/（资源统一放 lib/）
        search_dirs = [os.getcwd()]
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
        for d in (here, os.path.join(here, "lib")):
            if d not in search_dirs:
                search_dirs.append(d)

        candidates = []
        if lib_path:
            candidates.append(lib_path)
        for d in search_dirs:
            for name in _DEFAULT_LIBS:
                candidates.append(os.path.join(d, name))
        # 保留裸名（依赖系统 PATH / CWD）
        candidates += _DEFAULT_LIBS

        last_err = None
        for name in candidates:
            if not name:
                continue
            try:
                self._lib = ctypes.CDLL(name)
                logger.info("[hand] 加载库成功: %s", name)
                break
            except OSError as exc:
                last_err = exc
                logger.warning("[hand] 加载 %s 失败: %s", name, exc)
        if self._lib is None:
            raise RuntimeError(
                f"无法加载厂家 SDK 库（{candidates}）。请把 RyhandLibx64.dll 放入本目录"
                f"或通过 lib_path 指定。原始错误: {last_err}")
        self._declare_api()

    def _declare_api(self):
        L = self._lib
        L.RyCanServoBusInit.restype = ctypes.c_uint8
        L.RyCanServoBusInit.argtypes = [
            ctypes.POINTER(RyCanServoBusT), BusWriteT,
            ctypes.POINTER(ctypes.c_uint16), ctypes.c_uint16,
        ]
        L.RyCanServoBusDeInit.restype = None
        L.RyCanServoBusDeInit.argtypes = [ctypes.POINTER(RyCanServoBusT)]
        L.RyCanServoLibRcvMsg.restype = ctypes.c_int8
        L.RyCanServoLibRcvMsg.argtypes = [ctypes.POINTER(RyCanServoBusT), CanMsgT]
        L.RyMotion_ServoMove_Mix.restype = ctypes.c_uint8
        L.RyMotion_ServoMove_Mix.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_int16,
            ctypes.c_uint16, ctypes.c_uint16, ctypes.POINTER(ServoDataT), ctypes.c_uint16]
        L.RyMotion_ServoMove_Speed.restype = ctypes.c_uint8
        L.RyMotion_ServoMove_Speed.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_int16,
            ctypes.c_uint16, ctypes.POINTER(ServoDataT), ctypes.c_uint16]
        L.RyFunc_GetServoInfo.restype = ctypes.c_uint8
        L.RyFunc_GetServoInfo.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8,
            ctypes.POINTER(ServoDataT), ctypes.c_uint16]
        L.AddListen.restype = ctypes.c_int16
        L.AddListen.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.POINTER(CanMsgT), CallbackT]
        L.GetServoUpdateInfo.restype = ctypes.c_int8
        L.GetServoUpdateInfo.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.POINTER(MsgListenT)]
        L.RyParam_SetUpateRate.restype = ctypes.c_uint8
        L.RyParam_SetUpateRate.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_uint16,
            ctypes.POINTER(ServoDataT), ctypes.c_uint16]
        L.RyParam_SetMotionMute.restype = ctypes.c_uint8
        L.RyParam_SetMotionMute.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16]
        L.RyFunc_Reset.restype = ctypes.c_uint8
        L.RyFunc_Reset.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_uint16]
        L.RyParam_ClearFault.restype = ctypes.c_uint8
        L.RyParam_ClearFault.argtypes = [
            ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8, ctypes.c_uint16]
        # 行程读取（排查第16关节/拇指横向旋转"幅度小"用，手册 RyParam_GetStroke）
        try:
            L.RyParam_GetStroke.restype = ctypes.c_uint8
            L.RyParam_GetStroke.argtypes = [
                ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8,
                ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint16]
            L.RyParam_SetStroke.restype = ctypes.c_uint8
            L.RyParam_SetStroke.argtypes = [
                ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8,
                ctypes.c_uint32, ctypes.c_uint16]
        except Exception:  # pragma: no cover
            pass
        # 回零/找零（故障码 11 = 电机找零告警；CMD 0xBE，demo set_home_mode）
        try:
            L.RyParam_SetHomeMode.restype = ctypes.c_uint8
            L.RyParam_SetHomeMode.argtypes = [
                ctypes.POINTER(RyCanServoBusT), ctypes.c_uint8,
                ctypes.c_uint8, ctypes.c_uint16]
        except Exception:  # pragma: no cover
            pass
        try:
            L.GetRyCanServoLibVersion.restype = None
            L.GetRyCanServoLibVersion.argtypes = [ctypes.c_uint8 * 30]
        except Exception:  # pragma: no cover
            pass

    # ------------------------------------------------------------------
    def open(self):
        """初始化总线（对齐官方 demo）。"""
        from .transport import CanTransport
        self._tr = CanTransport(method=self.method,
                                rs485_port=self.rs485_port,
                                rs485_baud=self.rs485_baud)
        self._tr.open()
        self._init_bus()

    def set_hand_lr(self, hand_lr: int):
        """运行时切换手型（0=左手，1=右手）。左手时每指 M1/M2 交换。

        注意：左右手硬件上电机 1、2 安装方向镜像，共模(近节)/差模(侧摆)
        的物理含义会互换。若"滑近节滑条实际是侧摆"，通常是手型选反了，
        调用本方法切换后立即生效（无需重连）。
        """
        self.hand_lr = 1 if hand_lr else 0
        logger.info("[hand] 手型切换为 %s", "右手(1)" if self.hand_lr else "左手(0)")

    def _init_bus(self):
        HookArr = MsgHookT * HAND_CONFIG["hook_num"]
        ListenArr = MsgListenT * HAND_CONFIG["listen_num"]
        hooks = HookArr()
        listens = ListenArr()
        ctypes.memset(ctypes.byref(hooks), 0, ctypes.sizeof(hooks))
        ctypes.memset(ctypes.byref(listens), 0, ctypes.sizeof(listens))

        ctypes.memset(ctypes.byref(self.bus), 0, ctypes.sizeof(self.bus))
        self.bus.usTicksPeriod = 1000
        self.bus.usHookNum = HAND_CONFIG["hook_num"]
        self.bus.usListenNum = HAND_CONFIG["listen_num"]
        self.bus.pusTicksMs = ctypes.pointer(self._ticks)
        self.bus.pstuHook = ctypes.cast(hooks, ctypes.POINTER(MsgHookT))
        self.bus.pstuListen = ctypes.cast(listens, ctypes.POINTER(MsgListenT))

        @BusWriteT
        def _write(msg_ptr) -> int:
            try:
                msg = msg_ptr.contents
                self._tr.send(msg.ulId, bytes(msg.pucDat[:msg.ucLen]))
                return 0
            except Exception as exc:  # pragma: no cover
                logger.error("bus write error: %s", exc)
                return -1

        self._write_cb = _write
        ret = self._lib.RyCanServoBusInit(
            ctypes.byref(self.bus), self._write_cb,
            ctypes.pointer(self._ticks), 1000)
        if ret != 0:
            raise RuntimeError(f"RyCanServoBusInit 失败: ret={ret}")

        # 32 个 Listen（16×0xA0 + 16×0xAA，ID = 伺服ID+256）
        @CallbackT
        def _listen_cb(msg_ptr, para):
            try:
                msg = msg_ptr.contents
                mid = msg.ulId & 0xFF
                if 1 <= mid <= 16 and msg.ucLen >= 8:
                    self._last_servo_info[mid] = parse_servo_info(bytes(msg.pucDat[:8]))
            except Exception:  # pragma: no cover
                pass

        self._listen_cb = _listen_cb
        stu = (CanMsgT * 32)()
        for i in range(16):
            stu[i].ulId = i + 1 + 256
            stu[i].ucLen = 1
            stu[i].pucDat[0] = 0xA0
            self._lib.AddListen(ctypes.byref(self.bus), ctypes.byref(stu[i]), self._listen_cb)
        for i in range(16, 32):
            stu[i].ulId = (i - 16) + 1 + 256
            stu[i].ucLen = 1
            stu[i].pucDat[0] = 0xAA
            self._lib.AddListen(ctypes.byref(self.bus), ctypes.byref(stu[i]), self._listen_cb)

        # 接收线程
        self._tr._on_frame = self._on_frame
        self._running = True
        import threading
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()
        logger.info("[hand] 总线初始化完成（%s）", self.method)

    def _on_frame(self, can_id: int, payload: bytes):
        msg = CanMsgT()
        msg.ulId = can_id
        msg.ucLen = len(payload)
        for i, b in enumerate(payload):
            msg.pucDat[i] = b
        self._lib.RyCanServoLibRcvMsg(ctypes.byref(self.bus), msg)

    def _rx_loop(self):
        while self._running:
            time.sleep(0.001)
            # 1ms 计数器
            self._ticks.value = int(time.time() * 1000) % 1000

    # ------------------------------------------------------------------
    def check_connection(self, timeout_s: float = 0.5) -> dict:
        """连接性自检：读取 16 个电机状态。返回 {ok, version, replies, status}。

        用于 GUI / test_hand 验证灵巧手是否连通：
          * replies = 有应答的电机数（>0 说明链路通）
          * status 非 0 的电机（故障）
        """
        result = {"ok": False, "version": "", "replies": 0, "faults": [], "servos": {}}
        try:
            buf = (ctypes.c_uint8 * 30)()
            self._lib.GetRyCanServoLibVersion(buf)
            result["version"] = bytes(buf).split(b"\x00")[0].decode("ascii", errors="ignore")
        except Exception:  # pragma: no cover
            pass

        replies = 0
        faults = []
        for mid in range(1, 17):
            info = self.get_servo_info(mid, timeout_ms=100)
            if info is not None:
                replies += 1
                result["servos"][mid] = info
                if info.status != 0:
                    faults.append((mid, info.status, status_text(info.status)))
        result["replies"] = replies
        result["faults"] = faults
        result["ok"] = replies > 0
        # 便捷：是否有"找零告警"电机（行程受限根因）
        result["need_homing"] = [mid for mid, st, _ in faults if st == 11]
        return result

    # ------------------------------------------------------------------
    def move_motor(self, motor_id: int, position: int,
                   speed: Optional[int] = None,
                   max_current: Optional[int] = None,
                   control_mode: int = 0) -> int:
        """单电机位置指令（用于单电机测试/排查，如中指远节电机9无响应）。

        Args:
            motor_id: 电机 ID 1~16
            position: 目标位置 0~4095
        """
        speed = self.default_speed if speed is None else speed
        cur = self.default_max_current if max_current is None else max_current
        pos = max(0, min(POS_MAX, int(position)))
        fdb = ServoDataT()
        if control_mode == 0:
            return self._lib.RyMotion_ServoMove_Mix(
                ctypes.byref(self.bus), motor_id, pos,
                speed, cur, ctypes.byref(fdb), 0)
        return self._lib.RyMotion_ServoMove_Speed(
            ctypes.byref(self.bus), motor_id, pos,
            speed, ctypes.byref(fdb), 0)

    def move_joints(self, angles_rad_16: List[float],
                    speed: Optional[int] = None,
                    max_current: Optional[int] = None,
                    hand_lr: Optional[int] = None,
                    control_mode: int = 0,
                    inter_sleep_s: float = 0.0001) -> List[int]:
        """16 关节弧度 -> 电机指令 -> 逐电机下发（0xAA 力位混合 / 0xA1 速度）。"""
        if len(angles_rad_16) != JOINT_NUM:
            raise ValueError(f"需要恰好 {JOINT_NUM} 个关节角度")
        speed = self.default_speed if speed is None else speed
        cur = self.default_max_current if max_current is None else max_current
        hlr = self.hand_lr if hand_lr is None else hand_lr

        cmds = angles_to_motor_cmds(list(angles_rad_16), hand_lr=hlr)
        fdb = ServoDataT()
        for i, pos in enumerate(cmds):
            if control_mode == 0:
                self._lib.RyMotion_ServoMove_Mix(
                    ctypes.byref(self.bus), i + 1, pos,
                    speed, cur, ctypes.byref(fdb), 0)
            else:
                self._lib.RyMotion_ServoMove_Speed(
                    ctypes.byref(self.bus), i + 1, pos,
                    speed, ctypes.byref(fdb), 0)
            if inter_sleep_s > 0:
                time.sleep(inter_sleep_s)
        return cmds

    # ------------------------------------------------------------------
    def get_servo_info(self, motor_id: int, timeout_ms: int = 100) -> Optional[ServoInfo]:
        """同步读取单电机信息（RyFunc_GetServoInfo）。"""
        data = ServoDataT()
        ret = self._lib.RyFunc_GetServoInfo(
            ctypes.byref(self.bus), motor_id, ctypes.byref(data),
            ctypes.c_uint16(timeout_ms))
        if ret != 0:
            return None
        return parse_servo_data(data)

    def read_joint_angles(self, hand_lr: Optional[int] = None) -> List[float]:
        """读取 16 关节角度（弧度）。"""
        from .angles2motor import motor_cmds_to_joint_angles
        hlr = self.hand_lr if hand_lr is None else hand_lr
        cmds = []
        for mid in range(1, 17):
            info = self.get_servo_info(mid, timeout_ms=100)
            cmds.append(info.position if info else 0)
        return motor_cmds_to_joint_angles(cmds, hand_lr=hlr)

    # ------------------------------------------------------------------
    def open_hand(self, speed=None, max_current=None):
        """手掌完全张开：全部关节 0°（侧摆 0、弯曲 0）。"""
        self.move_joints([0.0] * 16, speed, max_current)

    def close_hand(self, speed=None, max_current=None):
        """标准握拳（所有手指弯曲、侧摆为 0，符合手册关节角度范围）。

        每指 3 关节 = [侧摆, 近节, 远节]：
          侧摆 0°（握拳不侧摆）；近节 ~70°；远节 ~60°（在 0~90/0~75 范围内）。
        拇指近节 50°、远节 30°；四指近节 70°、远节 60°；第16关节 0°。
        注：官方 demo palm_bend 预设中食指远节=0（伸直）、且带侧摆，
            不符合"握拳"语义，此处按手册角度范围重设计。
        """
        angles = [
            # 拇指           食指           中指           无名指         小指          第16关节
            0, 50, 30,   0, 70, 60,   0, 70, 60,   0, 70, 60,   0, 70, 60,   0,
        ]
        self.move_joints([math.radians(a) for a in angles], speed, max_current)

    def relax(self, speed=None, max_current=None):
        """自然放松半握（所有手指半弯、侧摆 0）。"""
        angles = [
            0, 30, 15,   0, 35, 25,   0, 35, 25,   0, 35, 25,   0, 35, 25,   0,
        ]
        self.move_joints([math.radians(a) for a in angles], speed, max_current)

    def reset(self, motor_id: int) -> int:
        return self._lib.RyFunc_Reset(ctypes.byref(self.bus), motor_id, 100)

    def clear_fault(self, motor_id: int) -> int:
        return self._lib.RyParam_ClearFault(ctypes.byref(self.bus), motor_id, 100)

    def get_stroke(self, motor_id: int, timeout_ms: int = 100) -> Optional[int]:
        """读取电机行程（RyParam_GetStroke）。

        排查"16号电机（拇指横向旋转）幅度小"：若行程远小于 4095，
        说明该电机行程配置受限，需用 RyParam_SetStroke 恢复或上位机校准。
        """
        try:
            val = ctypes.c_uint32(0)
            ret = self._lib.RyParam_GetStroke(
                ctypes.byref(self.bus), motor_id, ctypes.byref(val),
                ctypes.c_uint16(timeout_ms))
            if ret != 0:
                return None
            return int(val.value)
        except Exception:  # pragma: no cover
            return None

    def set_stroke(self, motor_id: int, stroke: int, timeout_ms: int = 100) -> int:
        """设置电机行程（RyParam_SetStroke）。谨慎使用，先读当前值再改。"""
        try:
            return self._lib.RyParam_SetStroke(
                ctypes.byref(self.bus), motor_id, stroke,
                ctypes.c_uint16(timeout_ms))
        except Exception:  # pragma: no cover
            return 0xFF

    def check_joint16_stroke(self) -> dict:
        """检查第16关节（拇指横向旋转）行程与当前状态，用于排查"幅度小"。"""
        stroke = self.get_stroke(16)
        info = self.get_servo_info(16, timeout_ms=100)
        return {
            "stroke": stroke,           # 期望 ≈4095；过小 => 幅度小
            "servo": info,
            "suggest": ("行程正常" if (stroke or 0) >= 3000
                        else "行程偏小（<3000），16号电机幅度会很小。"
                             "请用上位机校准/设置行程 RyParam_SetStroke 为 4095"),
        }

    # ------------------------------------------------------------------
    def set_home_mode(self, motor_id: int, mode: int, timeout_ms: int = 1000) -> int:
        """设置/执行电机回零（RyParam_SetHomeMode，CMD 0xBE）。

        mode（demo 说明）：
          0 - 上电自执行归零（配置保存）
          1 - 上电不自动执行归零
          2 - 执行归零动作（立即执行一次）
        故障码 11（找零告警）即表示电机未完成回零、行程受限，
        用 mode=2 执行一次归零后行程恢复。
        """
        try:
            return self._lib.RyParam_SetHomeMode(
                ctypes.byref(self.bus), motor_id, mode,
                ctypes.c_uint16(timeout_ms))
        except Exception:  # pragma: no cover
            return 0xFF

    def homing(self, motor_ids=None, timeout_ms: int = 1000, sleep_s: float = 0.05) -> dict:
        """对指定电机执行回零（默认 1~16 全部）。返回 {id: ret}。

        解决"动作几乎看不见/行程太小"的常见根因：电机未找零（status=11）。
        """
        if motor_ids is None:
            motor_ids = list(range(1, 17))
        result = {}
        for mid in motor_ids:
            ret = self.set_home_mode(mid, 2, timeout_ms)
            result[mid] = ret
            if sleep_s > 0:
                time.sleep(sleep_s)
        return result

    def check_all_strokes(self) -> dict:
        """读取 1~16 全部电机行程 + 状态，返回 {mid: {stroke, info}}。

        用于"动作几乎看不见"排查：行程应≈4095；status=11 表示未回零。
        """
        out = {}
        for mid in range(1, 17):
            stroke = self.get_stroke(mid, timeout_ms=100)
            info = self.get_servo_info(mid, timeout_ms=100)
            out[mid] = {"stroke": stroke, "info": info}
        return out

    # ------------------------------------------------------------------
    def close(self):
        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=1.0)
        try:
            self._lib.RyCanServoBusDeInit(ctypes.byref(self.bus))
        except Exception:  # pragma: no cover
            pass
        if self._tr is not None:
            self._tr.close()


def parse_servo_data(data: ServoDataT) -> ServoInfo:
    raw = bytes(data.pucDat[:8])
    v = int.from_bytes(raw, "little")
    return ServoInfo(
        status=(v >> 8) & 0xFF,
        position=(v >> 16) & 0xFFF,
        velocity=_sign12((v >> 28) & 0xFFF),
        current=_sign12((v >> 40) & 0xFFF),
        tactile=(v >> 52) & 0xFFF,
    )


def parse_servo_info(raw8: bytes) -> ServoInfo:
    v = int.from_bytes(raw8[:8], "little")
    return ServoInfo(
        status=(v >> 8) & 0xFF,
        position=(v >> 16) & 0xFFF,
        velocity=_sign12((v >> 28) & 0xFFF),
        current=_sign12((v >> 40) & 0xFFF),
        tactile=(v >> 52) & 0xFFF,
    )


def _sign12(x: int) -> int:
    return x - 0x1000 if x & 0x800 else x
