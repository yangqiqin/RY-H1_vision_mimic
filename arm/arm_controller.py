# -*- coding: utf-8 -*-
"""
arm_controller.py —— Aubo（遨博）K5 机械臂高层控制器（Windows 版）

职责：
  * 通过 pyaubo_sdk（RPC）连接/登录机械臂控制柜
  * 电源管理：上电、启动（松刹车）、断电
  * 运动控制：关节运动 movej / 直线 movel / 圆弧 movec / 关节伺服 servoJoint（视觉跟随用）
  * 状态读取：模式、安全模式、关节角、TCP 位姿、是否停止、IO 等
  * 工具配置：setTcpOffset（TCP 坐标联动 = 写入灵巧手安装偏移）
  * 示教：freedrive 拖拽示教
  * 正逆解：forwardKinematics / inverseKinematics

API 依据官方示例（lib/aubo_sdk-.../share/example/python/）：
  * example_movej.py / example_movel.py / example_movec.py / example_startup.py
  * example_state.py / example_io.py / example_algorithm.py / example_servoj2.py
  * example_freedrive.py

用法：
  from arm import AuboK5ArmController
  arm = AuboK5ArmController()
  arm.open()                        # 连接 + 登录
  arm.poweron_and_startup()         # 上电 + 启动
  arm.movej([0, -0.26, 1.74, 0.44, 1.57, 0], block=True)   # 关节运动
  arm.movel([0.55, 0.0, 0.4, 3.14, 0, 1.57], block=True)   # 直线运动（TCP 系）
  arm.close()                       # 登出 + 断开
"""

from __future__ import annotations

import logging
import math
import time
from typing import List, Optional, Tuple

logger = logging.getLogger("arm")

try:
    import pyaubo_sdk
    _AUBO_OK = True
except ImportError:  # pragma: no cover
    pyaubo_sdk = None
    _AUBO_OK = False

from .arm_config import ARM_CONFIG, CONN_ERROR_TEXT, DOF


def _deg2rad_list(vals) -> List[float]:
    return [math.radians(v) for v in vals]


def _rad2deg_list(vals) -> List[float]:
    return [math.degrees(v) for v in vals]


class AuboK5ArmController:
    """Aubo K5 机械臂控制器（Windows，pyaubo_sdk RPC）。"""

    def __init__(
        self,
        ip: Optional[str] = None,
        rpc_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        speed_fraction: Optional[float] = None,
        tcp_offset: Optional[List[float]] = None,
        hand_mount_offset: Optional[List[float]] = None,
    ):
        """
        Args:
            ip: 机械臂控制柜 IP（默认取 ARM_CONFIG["ip"]）
            rpc_port: RPC 端口（默认 30004）
            username / password: 登录账号（默认 aubo / 123456）
            speed_fraction: 全局速度比例 0~1（默认 0.3，安全起步）
            tcp_offset: 工具中心点偏移（默认 ARM_CONFIG["tcp_offset"]）
            hand_mount_offset: 灵巧手安装偏移（TCP 坐标联动；None 则不启用）
        """
        if not _AUBO_OK:
            raise RuntimeError("未安装 pyaubo_sdk：请执行 pip install pyaubo-sdk==0.27.1rc4")

        self.ip = ip or ARM_CONFIG["ip"]
        self.rpc_port = rpc_port or ARM_CONFIG["rpc_port"]
        self.username = username or ARM_CONFIG["username"]
        self.password = password or ARM_CONFIG["password"]
        self.speed_fraction = (
            speed_fraction if speed_fraction is not None else ARM_CONFIG["speed_fraction"]
        )
        self._tcp_offset = list(tcp_offset) if tcp_offset else list(ARM_CONFIG["tcp_offset"])
        self._hand_mount_offset = (
            list(hand_mount_offset) if hand_mount_offset is not None else None
        )

        self._client = None
        self._robot_interface = None
        self._robot_name: Optional[str] = None
        self._robot_manage = None
        self._motion_control = None
        self._robot_state = None
        self._robot_config = None
        self._io_control = None
        self._robot_algorithm = None

    # ==================================================================
    # 连接 / 断开
    # ==================================================================
    def open(self, timeout_ms: Optional[int] = None) -> bool:
        """连接 RPC 服务并登录。返回是否成功。"""
        if not _AUBO_OK:
            raise RuntimeError("未安装 pyaubo_sdk")
        if self._client is not None:
            logger.warning("[arm] 已连接，先 close 再 open")
            return self.has_connected()

        client = pyaubo_sdk.RpcClient()
        client.setRequestTimeout(timeout_ms or ARM_CONFIG["rpc_timeout_ms"])
        try:
            client.connect(self.ip, self.rpc_port)
        except Exception as exc:
            logger.error("[arm] 连接 %s:%d 失败: %s", self.ip, self.rpc_port, exc)
            return False
        if not client.hasConnected():
            logger.error("[arm] hasConnected()=False（IP/端口/网络）")
            return False
        try:
            client.login(self.username, self.password)
        except Exception as exc:
            logger.error("[arm] 登录失败: %s", exc)
            client.disconnect()
            return False
        if not client.hasLogined():
            logger.error("[arm] hasLogined()=False（账号密码错误？）")
            client.disconnect()
            return False

        self._client = client
        try:
            names = client.getRobotNames()
            self._robot_name = names[0] if names else None
        except Exception as exc:
            logger.warning("[arm] getRobotNames 失败: %s", exc)
        if self._robot_name is None:
            logger.error("[arm] 未获取到机器人名字")
            client.logout()
            client.disconnect()
            self._client = None
            return False

        ri = client.getRobotInterface(self._robot_name)
        self._robot_interface = ri
        self._robot_manage = ri.getRobotManage()
        self._motion_control = ri.getMotionControl()
        self._robot_state = ri.getRobotState()
        self._robot_config = ri.getRobotConfig()
        self._io_control = ri.getIoControl()
        self._robot_algorithm = ri.getRobotAlgorithm()

        # 应用速度比例与 TCP 偏移
        try:
            self._motion_control.setSpeedFraction(self.speed_fraction)
        except Exception as exc:
            logger.warning("[arm] setSpeedFraction 失败: %s", exc)
        self.apply_tcp_offset()

        logger.info("[arm] 已连接并登录: %s (%s:%d)", self._robot_name, self.ip, self.rpc_port)
        return True

    def has_connected(self) -> bool:
        return bool(self._client is not None and self._client.hasConnected())

    def has_logined(self) -> bool:
        return bool(self._client is not None and self._client.hasLogined())

    def close(self):
        """登出并断开连接。"""
        if self._client is not None:
            try:
                self._client.logout()
            except Exception as exc:  # pragma: no cover
                logger.debug("[arm] logout: %s", exc)
            try:
                self._client.disconnect()
            except Exception as exc:  # pragma: no cover
                logger.debug("[arm] disconnect: %s", exc)
        self._client = None
        self._robot_interface = None
        self._robot_manage = None
        self._motion_control = None
        self._robot_state = None
        self._robot_config = None
        self._io_control = None
        self._robot_algorithm = None
        self._robot_name = None
        logger.info("[arm] 已断开")

    # ==================================================================
    # 电源管理
    # ==================================================================
    def poweron(self) -> bool:
        """上电（请求机器人上电）。返回是否成功。"""
        if not self.has_logined():
            raise RuntimeError("未登录，请先 open()")
        ret = self._robot_manage.poweron()
        logger.info("[arm] poweron ret=%s", ret)
        return ret == 0

    def startup(self) -> bool:
        """启动（松刹车）。返回是否成功。"""
        if not self.has_logined():
            raise RuntimeError("未登录，请先 open()")
        ret = self._robot_manage.startup()
        logger.info("[arm] startup ret=%s", ret)
        return ret == 0

    def poweroff(self) -> bool:
        """断电。返回是否成功。"""
        if not self.has_logined():
            raise RuntimeError("未登录，请先 open()")
        ret = self._robot_manage.poweroff()
        logger.info("[arm] poweroff ret=%s", ret)
        return ret == 0

    def poweron_and_startup(self, wait_running: bool = True,
                            timeout_s: float = 15.0) -> bool:
        """上电 + 启动（松刹车），可选等待进入 Running 模式。返回是否成功。"""
        if not self.poweron():
            return False
        if not self.startup():
            return False
        if not wait_running:
            return True
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            mode = self.get_robot_mode()
            if mode is not None and "Running" in str(mode):
                logger.info("[arm] 机械臂进入 Running 模式")
                return True
            time.sleep(0.5)
        logger.warning("[arm] 等待 Running 超时（当前模式: %s）", self.get_robot_mode())
        return False

    # ==================================================================
    # 状态读取
    # ==================================================================
    def get_robot_mode(self):
        """机器人模式类型（RobotModeType，如 PowerOff/PowerOn/Running/Error...）。"""
        try:
            return self._robot_state.getRobotModeType()
        except Exception as exc:
            logger.warning("[arm] getRobotModeType: %s", exc)
            return None

    def get_safety_mode(self):
        try:
            return self._robot_state.getSafetyModeType()
        except Exception as exc:
            logger.warning("[arm] getSafetyModeType: %s", exc)
            return None

    def is_steady(self) -> Optional[bool]:
        """机器人是否已经停下来。"""
        try:
            return self._robot_state.isSteady()
        except Exception as exc:
            logger.warning("[arm] isSteady: %s", exc)
            return None

    def is_within_safety_limits(self) -> Optional[bool]:
        try:
            return self._robot_state.isWithinSafetyLimits()
        except Exception as exc:
            logger.warning("[arm] isWithinSafetyLimits: %s", exc)
            return None

    def get_joint_positions(self) -> Optional[List[float]]:
        """当前关节角（弧度，6 维）。"""
        try:
            return list(self._robot_state.getJointPositions())
        except Exception as exc:
            logger.warning("[arm] getJointPositions: %s", exc)
            return None

    def get_tcp_pose(self) -> Optional[List[float]]:
        """当前 TCP 位姿 [x,y,z,rx,ry,rz]（米/弧度，含 TCP 偏移）。"""
        try:
            return list(self._robot_state.getTcpPose())
        except Exception as exc:
            logger.warning("[arm] getTcpPose: %s", exc)
            return None

    def get_state_summary(self) -> dict:
        """状态汇总（GUI/诊断显示用）。"""
        return {
            "robot_mode": str(self.get_robot_mode()),
            "safety_mode": str(self.get_safety_mode()),
            "steady": self.is_steady(),
            "within_safety": self.is_within_safety_limits(),
            "joint_positions_rad": self.get_joint_positions(),
            "tcp_pose": self.get_tcp_pose(),
            "speed_fraction": self.get_speed_fraction(),
        }

    def get_speed_fraction(self) -> Optional[float]:
        try:
            return self._motion_control.getSpeedFraction()
        except Exception as exc:
            logger.warning("[arm] getSpeedFraction: %s", exc)
            return None

    def set_speed_fraction(self, fraction: float):
        """设置全局速度比例 0~1。"""
        f = max(0.0, min(1.0, float(fraction)))
        self._motion_control.setSpeedFraction(f)
        self.speed_fraction = f
        logger.info("[arm] speed fraction = %.2f", f)

    # ==================================================================
    # TCP 坐标联动
    # ==================================================================
    def apply_tcp_offset(self, hand_mount_offset: Optional[List[float]] = None):
        """把 TCP 偏移写入机械臂（setTcpOffset）。

        若传入 hand_mount_offset（灵巧手安装偏移），则最终 TCP 偏移 = 基础偏移 + 安装偏移
        （平移相加、旋转相加），使 moveLine/moveCircle 的位姿以"灵巧手 TCP"为基准。
        """
        if hand_mount_offset is not None:
            self._hand_mount_offset = list(hand_mount_offset)
        if self._hand_mount_offset is None:
            final = list(self._tcp_offset)
        else:
            final = [
                self._tcp_offset[i] + self._hand_mount_offset[i]
                for i in range(6)
            ]
        try:
            self._robot_config.setTcpOffset(final)
            logger.info("[arm] TCP offset = %s (hand mount %s)",
                        final, self._hand_mount_offset)
        except Exception as exc:
            logger.error("[arm] setTcpOffset 失败: %s", exc)
            raise

    def get_hand_mount_offset(self) -> Optional[List[float]]:
        return list(self._hand_mount_offset) if self._hand_mount_offset else None

    # ==================================================================
    # 运动控制
    # ==================================================================
    def _wait_arrival(self, timeout_s: float = 30.0) -> int:
        """阻塞等待当前运动完成（官方 wait_arrival 逻辑 + 超时保护）。"""
        mc = self._motion_control
        t0 = time.time()
        exec_id = -1
        try:
            exec_id = mc.getExecId()
        except Exception:
            pass
        # 等待开始运动
        cnt = 0
        while exec_id == -1:
            cnt += 1
            if cnt > 5:
                return -1
            if time.time() - t0 > timeout_s:
                return -1
            time.sleep(0.05)
            try:
                exec_id = mc.getExecId()
            except Exception:
                exec_id = -1
        # 等待运动完成
        while True:
            if time.time() - t0 > timeout_s:
                logger.warning("[arm] 等待运动完成超时")
                return -1
            try:
                if mc.getExecId() == -1:
                    return 0
            except Exception:
                pass
            time.sleep(0.05)

    def movej(self, joint_rad: List[float],
              speed_deg: Optional[float] = None,
              acc_deg: Optional[float] = None,
              block: bool = True, timeout_s: float = 30.0) -> Tuple[int, Optional[str]]:
        """关节运动（moveJoint）。joint_rad: 6 维弧度。返回 (ret, err_msg)。"""
        if len(joint_rad) != DOF:
            return -1, f"需要 {DOF} 个关节角"
        spd = math.radians(speed_deg if speed_deg is not None
                           else ARM_CONFIG["joint_speed"])
        acc = math.radians(acc_deg if acc_deg is not None
                           else ARM_CONFIG["joint_acc"])
        try:
            ret = self._motion_control.moveJoint(
                list(joint_rad), spd, acc,
                ARM_CONFIG["blend_radius"], 0)
        except Exception as exc:
            logger.error("[arm] moveJoint 异常: %s", exc)
            return -1, str(exc)
        if ret != 0:
            return ret, self._ret_text(ret)
        if block:
            wr = self._wait_arrival(timeout_s)
            return (0, None) if wr == 0 else (-1, f"等待完成超时({timeout_s}s)")
        return 0, None

    def movel(self, pose: List[float],
              speed: Optional[float] = None,
              acc: Optional[float] = None,
              block: bool = True, timeout_s: float = 30.0) -> Tuple[int, Optional[str]]:
        """直线运动（moveLine）。pose: [x,y,z,rx,ry,rz]，米/弧度（TCP 系）。"""
        if len(pose) != 6:
            return -1, "pose 需要 [x,y,z,rx,ry,rz]"
        spd = speed if speed is not None else ARM_CONFIG["line_speed"]
        acc = acc if acc is not None else ARM_CONFIG["line_acc"]
        try:
            ret = self._motion_control.moveLine(
                list(pose), spd, acc,
                ARM_CONFIG["blend_radius"], 0)
        except Exception as exc:
            logger.error("[arm] moveLine 异常: %s", exc)
            return -1, str(exc)
        if ret != 0:
            return ret, self._ret_text(ret)
        if block:
            wr = self._wait_arrival(timeout_s)
            return (0, None) if wr == 0 else (-1, f"等待完成超时({timeout_s}s)")
        return 0, None

    def movec(self, mid_pose: List[float], end_pose: List[float],
              speed: Optional[float] = None,
              acc: Optional[float] = None) -> Tuple[int, Optional[str]]:
        """圆弧运动（moveCircle）：经中间点 mid_pose 到 end_pose（位姿，TCP 系）。"""
        spd = speed if speed is not None else ARM_CONFIG["line_speed"]
        acc = acc if acc is not None else ARM_CONFIG["line_acc"]
        try:
            ret = self._motion_control.moveCircle(
                list(mid_pose), list(end_pose), spd, acc,
                ARM_CONFIG["blend_radius"], 0)
        except Exception as exc:
            logger.error("[arm] moveCircle 异常: %s", exc)
            return -1, str(exc)
        if ret != 0:
            return ret, self._ret_text(ret)
        return 0, None

    def move_home(self, block: bool = True) -> Tuple[int, Optional[str]]:
        """回到初始关节角（示例 q 起点：J1=0, J2=-15°, J3=100°, J4=25°, J5=90°, J6=0）。"""
        home = [0.0, -15.0, 100.0, 25.0, 90.0, 0.0]
        return self.movej(_deg2rad_list(home), block=block)

    def stop_move(self) -> int:
        """停止运动（stopMove）。"""
        try:
            return self._motion_control.stopMove()
        except Exception as exc:
            logger.warning("[arm] stopMove: %s", exc)
            return -1

    # ---- 关节伺服（视觉跟随/连续轨迹用） ----
    def servo_mode_enable(self, enable: bool, mode: int = 1) -> int:
        """开关 servo 模式（mode: 1=旧接口等价, 2=新接口, 5=路点必达）。"""
        mc = self._motion_control
        try:
            if enable:
                mc.setServoModeSelect(mode)
                i = 0
                while mc.getServoModeSelect() != mode:
                    i += 1
                    if i > 20:
                        return -1
                    time.sleep(0.007)
            else:
                mc.setServoModeSelect(0)
            return 0
        except Exception as exc:
            logger.error("[arm] servo mode: %s", exc)
            return -1

    def servo_joint(self, joint_rad: List[float],
                    t: float = 0.02, lookahead: float = 0.1,
                    gain: float = 200) -> int:
        """关节伺服下发一个目标点（servoJoint），5ms 节拍连续调用可实现实时跟随。"""
        try:
            return self._motion_control.servoJoint(
                list(joint_rad), 0.1, 0.2, t, lookahead, gain)
        except Exception as exc:
            logger.error("[arm] servoJoint: %s", exc)
            return -1

    # ==================================================================
    # 示教
    # ==================================================================
    def freedrive(self, enable: bool, duration_s: Optional[float] = None) -> bool:
        """拖拽示教：enable=True 进入自由驱动（可手动拖拽），False 退出。
        duration_s 非空时自动等待该秒数后退出。"""
        try:
            if enable:
                try:
                    self._client.getRuntimeMachine().start()
                except Exception:
                    pass
                self._robot_manage.freedrive(True)
                if duration_s is not None:
                    time.sleep(duration_s)
                    self._robot_manage.freedrive(False)
                return True
            self._robot_manage.freedrive(False)
            return True
        except Exception as exc:
            logger.error("[arm] freedrive: %s", exc)
            return False

    # ==================================================================
    # IO
    # ==================================================================
    def get_standard_digital_inputs(self) -> Optional[List[int]]:
        """标准数字输入值列表。"""
        try:
            n = self._io_control.getStandardDigitalInputNum()
            return [self._io_control.getStandardDigitalInput(i) for i in range(n)]
        except Exception as exc:
            logger.warning("[arm] digital inputs: %s", exc)
            return None

    def get_standard_digital_outputs(self) -> Optional[List[int]]:
        try:
            n = self._io_control.getStandardDigitalOutputNum()
            return [self._io_control.getStandardDigitalOutput(i) for i in range(n)]
        except Exception as exc:
            logger.warning("[arm] digital outputs: %s", exc)
            return None

    def set_standard_digital_output(self, index: int, value: bool) -> int:
        """设置标准数字输出。"""
        try:
            return self._io_control.setStandardDigitalOutput(int(index), bool(value))
        except Exception as exc:
            logger.error("[arm] set std DO: %s", exc)
            return -1

    def get_tool_digital_input(self, index: int = 1) -> Optional[int]:
        try:
            return self._io_control.getToolDigitalInput(int(index))
        except Exception as exc:
            logger.warning("[arm] tool DI: %s", exc)
            return None

    def set_tool_digital_output(self, index: int, value: bool) -> int:
        """设置工具端数字输出（如控制末端夹爪/灵巧手供电信号）。"""
        try:
            return self._io_control.setToolDigitalOutput(int(index), bool(value))
        except Exception as exc:
            logger.error("[arm] set tool DO: %s", exc)
            return -1

    # ==================================================================
    # 正逆解
    # ==================================================================
    def forward_kinematics(self, joint_rad: List[float]) -> Tuple[Optional[List[float]], int]:
        """正解：关节角 -> TCP 位姿。返回 (pose, ret)。"""
        try:
            res = self._robot_algorithm.forwardKinematics(list(joint_rad))
            return list(res[0]), res[1]
        except Exception as exc:
            logger.error("[arm] forwardKinematics: %s", exc)
            return None, -1

    def inverse_kinematics(self, ref_joint_rad: List[float],
                           target_pose: List[float]) -> Tuple[Optional[List[float]], int]:
        """逆解：位姿 -> 关节角（以 ref_joint_rad 为参考初值）。返回 (q, ret)。"""
        try:
            res = self._robot_algorithm.inverseKinematics(
                list(ref_joint_rad), list(target_pose))
            return list(res[0]), res[1]
        except Exception as exc:
            logger.error("[arm] inverseKinematics: %s", exc)
            return None, -1

    # ==================================================================
    # 工具
    # ==================================================================
    @staticmethod
    def _ret_text(ret: int) -> str:
        """返回码 -> 中文（尽量用 SDK 的 errorCode2Str）。"""
        try:
            s = pyaubo_sdk.errorCode2Str(ret)
            if s:
                return f"错误码{ret}: {s}"
        except Exception:
            pass
        return f"错误码{ret}"


def quick_check(ip: Optional[str] = None) -> dict:
    """快速连通性检查（不登录也尝试连接并读状态），供 test_arm/diag_arm 使用。"""
    arm = AuboK5ArmController(ip=ip)
    ok = arm.open()
    out = {"connected": ok}
    if ok:
        try:
            out["robot_name"] = arm._robot_name
            out["summary"] = arm.get_state_summary()
        except Exception as exc:
            out["summary_error"] = str(exc)
        arm.close()
    return out
