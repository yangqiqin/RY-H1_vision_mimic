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


# ---------------------------------------------------------------------------
# 限流日志：同一 tag 的错误/警告每 period 秒至多打印一次（防"32601 不支持"类
# 高频 RPC 失败把日志台刷爆）
# ---------------------------------------------------------------------------
_RL_LAST: dict = {}


def _rl_warn(logger_: logging.Logger, tag: str, msg: str, period: float = 30.0,
             first_error: bool = True):
    import time as _t
    now = _t.time()
    if _RL_LAST.get(tag, 0.0) + period >= now:
        return
    _RL_LAST[tag] = now
    (logger_.error if first_error else logger_.warning)("%s: %s", tag, msg)



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
        self._runtime_machine = None
        self._last_collision_error = ""    # 最近一次碰撞盒操作错误详情
        # 能力熔断：固件不支持的 RPC（如 getJointTorques 32601）连续失败后自动禁用，
        # 避免每帧重试刷屏/拖慢
        self._torque_ok = True
        self._torque_fail = 0

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
        # 运行时机器（碰撞盒/非阻塞运动等需要 RTM 已启动）
        try:
            self._runtime_machine = client.getRuntimeMachine()
        except Exception as exc:
            logger.warning("[arm] getRuntimeMachine: %s", exc)
            self._runtime_machine = None

        # 应用速度比例与 TCP 偏移
        try:
            self._motion_control.setSpeedFraction(self.speed_fraction)
        except Exception as exc:
            _rl_warn(logger, "setSpeedFraction", str(exc))
        self.apply_tcp_offset()

        self._torque_ok = True
        self._torque_fail = 0
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
        self._runtime_machine = None
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
            _rl_warn(logger, "isSteady", str(exc))
            return None

    def is_within_safety_limits(self) -> Optional[bool]:
        try:
            return self._robot_state.isWithinSafetyLimits()
        except Exception as exc:
            _rl_warn(logger, "isWithinSafetyLimits", str(exc))
            return None

    def _sane_joints(self, q) -> Optional[List[float]]:
        """关节角合理性校验（弧度，6 维）。异常返回 None（调用方按"读不到"处理）。"""
        if q is None or len(q) < 6:
            return None
        try:
            vals = [float(v) for v in q[:6]]
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(v) for v in vals):
            return None
        if any(abs(v) > 2 * math.pi + 0.5 for v in vals):
            logger.warning("[arm] 关节角读数异常(超出±2π): %s", vals)
            return None
        return vals

    def _sane_pose(self, pose) -> Optional[List[float]]:
        """位姿合理性校验（位置米/旋转弧度，6 维）。

        位置分量 |·| > 3m 即疑似"厘米被当米/单位错误/读数异常" → 返回 None，
        防止把荒谬读数喂给安全框/手眼标定导致误判或危险动作。
        """
        if pose is None or len(pose) < 6:
            return None
        try:
            vals = [float(v) for v in pose[:6]]
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(v) for v in vals):
            return None
        if any(abs(v) > 3.0 for v in vals[:3]):
            logger.warning("[arm] 位姿位置读数异常(疑似单位错误/cm被当m): %s", vals[:3])
            return None
        if any(abs(v) > 2 * math.pi + 0.5 for v in vals[3:6]):
            logger.warning("[arm] 位姿旋转读数异常(超出±2π): %s", vals[3:6])
            return None
        return vals

    def get_joint_positions(self) -> Optional[List[float]]:
        """当前关节角（弧度，6 维）。"""
        try:
            return self._sane_joints(self._robot_state.getJointPositions())
        except Exception as exc:
            _rl_warn(logger, "getJointPositions", str(exc))
            return None

    def get_tcp_pose(self) -> Optional[List[float]]:
        """当前 TCP 位姿 [x,y,z,rx,ry,rz]（米/弧度，含 TCP 偏移）。"""
        try:
            return self._sane_pose(self._robot_state.getTcpPose())
        except Exception as exc:
            _rl_warn(logger, "getTcpPose", str(exc))
            return None

    def get_flange_pose(self) -> Optional[List[float]]:
        """当前【法兰】位姿 [x,y,z,rx,ry,rz]（米/弧度，不含 TCP 偏移）。

        手眼标定坐标转换必须用【法兰位姿】（相机装在法兰上），
        而不是含 TCP 偏移的 getTcpPose（那是灵巧手 TCP 位置，会引入偏移误差）。
        """
        try:
            return self._sane_pose(self._robot_state.getToolPose())
        except Exception as exc:
            _rl_warn(logger, "getToolPose", str(exc))
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

    # ---- 碰撞/受阻检测数据（眼在手上安全用） ----
    def get_joint_torques(self) -> Optional[List[float]]:
        """关节力矩（N·m，6 维）。碰撞时力矩会异常增大。

        ★ 固件不支持(32601)时熔断：连续失败 3 次后本连接期内不再重试（返回 None），
        只打一次错误，避免跟随每帧重试把日志台刷爆。
        """
        if not self._torque_ok:
            return None
        try:
            return list(self._robot_state.getJointTorques())
        except Exception as exc:
            self._torque_fail += 1
            if self._torque_fail == 1:
                _rl_warn(logger, "getJointTorques(固件不支持?)", str(exc))
            if self._torque_fail >= 3:
                self._torque_ok = False
                logger.warning("[arm] 力矩读取连续失败，已在本连接内禁用（返回 None）")
            return None

    def get_joint_currents(self) -> Optional[List[float]]:
        """关节电流（A，6 维）。受阻时电流增大。"""
        try:
            return list(self._robot_state.getJointCurrents())
        except Exception as exc:
            _rl_warn(logger, "getJointCurrents", str(exc))
            return None

    def hard_stop(self, retries: int = 5, delay_s: float = 0.05) -> bool:
        """【硬停止】多次调用 stopMove 直到确认停止（安全关键）。

        碰撞/异常/急停时用：SDK 忙或运动队列未清空时单次 stopMove 可能失败，
        重试直到 is_steady() 为 True 或达到重试上限。
        """
        for i in range(max(1, retries)):
            try:
                self._motion_control.stopMove()
            except Exception as exc:
                logger.error("[arm] hard_stop 第%d次 stopMove 异常: %s", i + 1, exc)
            time.sleep(delay_s)
            try:
                steady = self._robot_state.isSteady()
                if steady:
                    logger.warning("[arm] hard_stop 已确认停止（第%d次）", i + 1)
                    return True
            except Exception:
                pass
        logger.error("[arm] hard_stop 未能确认停止（仍可能运动中！）")
        return False

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
        """回到初始关节角（取 arm_config.HOME_JOINT_DEG，GUI 可调可保存）。

        默认：J1=0, J2=-15°, J3=100°, J4=25°, J5=90°, J6=0（官方示例起始位）。
        用户可在 GUI 点【记录当前为初始位】把当前位置设为新的 HOME，随后"回初始位"即回该处。
        """
        from .arm_config import HOME_JOINT_DEG
        return self.movej(_deg2rad_list(list(HOME_JOINT_DEG)), block=block)

    def set_home(self, joint_deg: List[float]) -> None:
        """设置新的初始位置（度，6 维）——GUI【记录当前为初始位】调用。"""
        from .arm_config import HOME_JOINT_DEG
        if len(joint_deg) != DOF:
            raise ValueError(f"需要 {DOF} 个角度")
        HOME_JOINT_DEG[:] = [float(v) for v in joint_deg]
        logger.info("[arm] HOME 已更新为 %s", [round(v, 1) for v in HOME_JOINT_DEG])

    def get_home(self) -> List[float]:
        """读取当前初始位置（度，6 维）。"""
        from .arm_config import HOME_JOINT_DEG
        return list(HOME_JOINT_DEG)

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
    # 末端碰撞盒 / 安全包围盒（防相机·灵巧手剐蹭，SDK 硬件级碰撞保护）
    # 依据 lib/auboDocument/index-碰撞.pdf：addCollisionBox(name, link_name, sizes, poses)
    #   * link_name="end_effector" → 碰撞盒挂在末端，随末端运动
    #   * 机械臂其它连杆/环境物体进入该盒 → SDK 碰撞保护（停止）
    #   * sizes = [[长, 宽, 高]]（米）；poses = [[x,y,z,rx,ry,rz]] 相对末端位姿
    # ==================================================================
    def add_tool_collision_box(self, name: str = "tool_box",
                               size: Optional[List[float]] = None,
                               pose: Optional[List[float]] = None) -> int:
        """在末端挂一个立方体碰撞盒（工具包络），随末端运动。

        前置条件（addCollisionBox 是算法接口，需 RTM 运行）：
          1. 确保 RuntimeMachine 已启动（203 AUBO_BADSTATE_RTM_NOT_STARTED）；
          2. 确保机械臂 Running（212 AUBO_BADSTATE_ROBOT_NOT_RUNNING）；
          3. 同名碰撞盒先删除（防重名冲突）。

        Args:
            name: 碰撞盒名（addCollisionBox 的 name）
            size: [长, 宽, 高]（米）——包含相机 + 灵巧手 + 手指摆动空间
            pose: [x,y,z,rx,ry,rz] 相对 end_effector 的位姿（米/弧度）

        Returns:
            0=成功；>0=AUBO 错误码；-1=异常
        """
        if self._robot_algorithm is None:
            logger.warning("[arm] 算法接口未就绪（未连接）")
            return -1

        # 0) 先删除同名旧碰撞盒（防重名冲突，忽略删除失败）
        try:
            self._robot_algorithm.removeCollisionObject(name)
        except Exception:
            pass

        # 1) 确保 RuntimeMachine 已启动（addCollisionBox 需要 RTM）
        if getattr(self, "_runtime_machine", None) is not None:
            try:
                rt_state = self._runtime_machine.getRuntimeState()
                # 若未启动则 start()
                if not rt_state:
                    self._runtime_machine.start()
                    time.sleep(0.1)
            except Exception as exc:
                logger.warning("[arm] RTM 启动检查/启动: %s", exc)

        # 2) 若机械臂未 Running（仅上电未启动），提示先 poweron_and_startup
        try:
            mode = str(self.get_robot_mode())
            if mode and "Running" not in mode and "Idle" in mode:
                logger.warning("[arm] 机械臂未进入 Running（当前 %s），碰撞盒可能添加失败。"
                               "请先执行 上电+启动", mode)
        except Exception:
            pass

        sz = [list(size)] if size else [[0.15, 0.12, 0.20]]
        ps = [list(pose)] if pose else [[0.0, 0.0, 0.10, 0.0, 0.0, 0.0]]
        try:
            ret = self._robot_algorithm.addCollisionBox(name, "end_effector", sz, ps)
            if ret == 0:
                logger.info("[arm] ✅ 末端碰撞盒 %s 已添加（size=%s, pose=%s）", name, sz, ps)
                self._last_collision_error = ""
            else:
                # AUBO 错误码中文提示（对照 dir(pyaubo_sdk) 的 AUBO_ 常量）
                self._last_collision_error = self._aubo_error_text(ret)
                logger.error("[arm] ❌ addCollisionBox ret=%d %s", ret,
                             self._last_collision_error)
            return ret
        except Exception as exc:
            # 记录详细异常（GUI 读取显示），返回 -1 表示异常
            self._last_collision_error = f"调用异常: {type(exc).__name__}: {exc}"
            logger.error("[arm] addCollisionBox 调用异常: %s", exc)
            return -1

    def get_last_collision_error(self) -> str:
        """最近一次碰撞盒操作的具体错误（供 GUI 弹窗显示）。"""
        return getattr(self, "_last_collision_error", "")

    @staticmethod
    def _aubo_error_text(ret: int) -> str:
        """AUBO 返回码 → 中文解释（对照 pyaubo_sdk.AUBO_* 常量）。"""
        import pyaubo_sdk as _s
        mapping = {
            0: "成功", 1: "状态错误(BAD_STATE)", 2: "队列已满(QUEUE_FULL)",
            3: "忙(BUSY)", 4: "超时(TIMEOUT)", 5: "参数非法(INVL_ARGUMENT)",
            6: "未实现", 7: "无权限(NO_ACCESS)", 8: "连接拒绝", 9: "连接重置",
            10: "进行中(INPROGRESS)", 11: "IO错误", 12: "无缓冲", 13: "请求被忽略",
            14: "算法规划失败", 15: "版本不兼容", 16: "维度错误", 17: "奇异点",
            18: "位置越界", 19: "初始位置错误", 21: "轨迹生成失败",
            22: "轨迹自碰撞(SELF_COLLISION)", 23: "逆解不收敛",
            203: "运行时未启动(RTM_NOT_STARTED)——请先执行上电+启动",
            210: "机器人模式无效(INVALID_ROBOT_MODE)",
            212: "机器人未运行(ROBOT_NOT_RUNNING)——请先执行上电+启动",
            213: "机器人未断电完成", 218: "机器人未停稳",
            219: "拖拽示教激活中(FREE_DRIVE_ACTIVE)——请先关闭拖拽",
            221: "仿真模式激活(SIMULATION_MODE_ACTIVE)",
        }
        if ret in mapping:
            return mapping[ret]
        try:
            return str(_s.errorCode2Str(ret))
        except Exception:
            return f"未知错误码 {ret}"

    def remove_tool_collision_box(self, name: str = "tool_box") -> int:
        """删除末端碰撞盒。"""
        if self._robot_algorithm is None:
            return -1
        try:
            ret = self._robot_algorithm.removeCollisionObject(name)
            logger.info("[arm] 碰撞盒 %s 已删除 ret=%s", name, ret)
            return ret
        except Exception as exc:
            logger.error("[arm] removeCollisionObject 失败: %s", exc)
            return -1

    # ==================================================================
    # 基座坐标系安全长方体（WorldZone，固定区域：保护桌面/障碍物）
    # ==================================================================
    def set_world_zone(self, base_vertex: List[float], opposite_vertex: List[float],
                       enabled: bool = True, outside: bool = True,
                       margin: float = 0.01, tool_radius: float = 0.05,
                       brake_margin: float = 0.02, zone_id: int = 1) -> int:
        """设置基座系安全长方体（WorldZone）。

        Args:
            base_vertex: 长方体一角 [x,y,z]（基座系，米）
            opposite_vertex: 对角 [x,y,z]
            enabled: 是否启用
            outside: False=腔内危险(TCP进入→停), True=腔外危险(内缩成禁区保护桌面)
            margin: 工艺余量（米）
            tool_radius: 工具包络半径（米）
            brake_margin: 制动距离余量（米），启用时必须>0
        """
        if self._io_control is None:
            logger.warning("[arm] IO 接口未就绪")
            return -1
        try:
            import pyaubo_sdk
            wz = pyaubo_sdk.WorldZone()
            wz.id = int(zone_id)
            wz.enabled = bool(enabled)
            wz.outside = bool(outside)
            wz.base_vertex = [float(v) for v in base_vertex]
            wz.opposite_vertex = [float(v) for v in opposite_vertex]
            wz.margin = float(margin)
            wz.tool_radius = float(tool_radius)
            wz.brake_margin = float(brake_margin)
            ret = self._io_control.setWorldZone(wz)
            logger.info("[arm] WorldZone%d 设置: base%s opp%s outside=%s ret=%s",
                        zone_id, base_vertex, opposite_vertex, outside, ret)
            return ret
        except Exception as exc:
            _rl_warn(logger, "setWorldZone", str(exc))
            return -1

    def get_world_zone_state(self) -> dict:
        """读取 WorldZone 运行状态（TCP 是否进入/阻塞）。"""
        if self._io_control is None:
            return {}
        try:
            st = self._io_control.getWorldZoneState()
            return {
                "any_occupied": bool(getattr(st, "any_occupied", False)),
                "holding": bool(getattr(st, "holding", False)),
                "blocking": bool(getattr(st, "blocking", False)),
                "blocking_ids": list(getattr(st, "blocking_ids", [])),
            }
        except Exception as exc:
            logger.warning("[arm] getWorldZoneState: %s", exc)
            return {}

    def enable_table_protect_zone(self, floor_z: float = 0.13,
                                  zone_id: int = 1) -> Tuple[int, str]:
        """启用【桌面/地面危险腔】WorldZone（腔内危险：末端 z<floor_z 即 SDK 停机）。

        用途：作为 addCollisionBox 固件不支持(32601)时的硬件级替代——
        把"桌面以下空间"定义为危险腔，末端一旦下沉超过 floor_z（基座系米）即保护停机。
        xy 不限制（不误伤转向/平移）；上方不限制。
        """
        try:
            ret = self.set_world_zone(
                base_vertex=[-10.0, -10.0, -10.0],
                opposite_vertex=[10.0, 10.0, max(0.02, floor_z)],
                enabled=True, outside=False,      # 腔内危险：进入 z<floor_z 区域即触发
                margin=0.0, tool_radius=0.03, brake_margin=0.02,
                zone_id=zone_id)
            if ret == 0:
                return 0, f"WorldZone 桌面危险腔已启用（z<{floor_z:.2f}m 停机保护）"
            return ret, f"WorldZone 设置失败 ret={ret}（见日志）"
        except Exception as exc:
            logger.error("[arm] enable_table_protect_zone 异常: %s", exc)
            return -1, f"WorldZone 异常: {exc}"

    def disable_world_zone(self, zone_id: int = 1) -> int:
        """停用指定 WorldZone。"""
        return self.set_world_zone(
            base_vertex=[0.0, 0.0, 0.0],
            opposite_vertex=[1.0, 1.0, 1.0],
            enabled=False, outside=False, margin=0.0,
            tool_radius=0.03, brake_margin=0.02, zone_id=zone_id)

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
