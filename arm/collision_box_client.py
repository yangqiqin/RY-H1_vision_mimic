# arm/collision_box_client.py
# Python 端 Socket 客户端，用于与 C++ 碰撞盒服务端（collision_box_server.exe）通信。
#
# 背景：Python 版 pyaubo-sdk 的 RobotAlgorithm 无法调用 addCollisionBox（固件报
# 32601 method not found），因此碰撞盒改为由 C++ 程序直接调用遨博 C++ SDK，
# Python GUI 通过本模块 + Socket 下发"add/remove"命令。
#
# 健壮性（本文件完善点）：
#   * recv 循环收包直到拿到完整 JSON（防 TCP 粘包/半包）；
#   * 断线自动重连一次再重发；
#   * exe 查找基于本文件路径推导的项目根，兼容根目录/bin/bin/Release 布局；
#   * 每个命令独立 short-timeout，GUI 线程不被长阻塞。

import json
import logging
import os
import socket
import subprocess
import sys
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("collision_box")

# 本项目根目录（arm/collision_box_client.py 的上上级）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_RECV_CHUNK = 65536
_MAX_RESP_BYTES = 1 << 20  # 1MB 上限，防异常服务端灌包


class CollisionBoxClient:
    """碰撞盒 Socket 客户端（每命令自动连接-发送-接收-可保持复用）。"""

    def __init__(self, server_ip: str = "127.0.0.1", server_port: int = 9999):
        self.server_ip = server_ip
        self.server_port = server_port
        self._connected = False
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    def connect(self, timeout: float = 2.0) -> bool:
        """建立连接（先清理旧 socket，避免半开连接堆积）。"""
        self.disconnect()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.server_ip, self.server_port))
            self._sock = sock
            self._connected = True
            return True
        except Exception as exc:
            logger.warning("[collision] 连接服务端 %s:%s 失败: %s",
                           self.server_ip, self.server_port, exc)
            self._connected = False
            return False

    def disconnect(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self._connected = False

    # ------------------------------------------------------------------
    @staticmethod
    def _recv_json(sock: socket.socket, timeout: float) -> Optional[dict]:
        """循环 recv 直到收到一个完整 JSON 对象（防粘包/半包）。超时/异常返回 None。"""
        sock.settimeout(timeout)
        buffer = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if len(buffer) > _MAX_RESP_BYTES:
                logger.error("[collision] 响应超长，丢弃")
                return None
            try:
                chunk = sock.recv(_RECV_CHUNK)
            except socket.timeout:
                break
            except Exception:
                break
            if not chunk:
                break
            buffer += chunk
            # 尝试解析：完整 JSON 必然能 parse；不完整则继续等下一段
            for _ in range(1):  # 尝试多次以防前缀残缺
                try:
                    obj = json.loads(buffer.decode("utf-8"))
                    return obj
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        return None

    def send_command(self, command: Dict[str, Any], timeout: float = 5.0) -> Optional[dict]:
        """发送命令并接收响应。

        ★ 每次命令用【独立连接】（服务端每连接处理一请求即关闭，维持长连接会产生
        反复"响应超时/自动重连"噪音且慢）；失败自动重试一次。
        """
        payload = json.dumps(command).encode("utf-8")
        for attempt in (1, 2):
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(min(timeout, 2.0))
                sock.connect((self.server_ip, self.server_port))
                sock.settimeout(timeout)
                sock.sendall(payload)
                resp = self._recv_json(sock, timeout)
                if resp is not None:
                    return resp
                if attempt == 1:
                    continue
                return {"status": "error", "msg": "服务端响应超时"}
            except socket.timeout:
                if attempt == 1:
                    continue
                return {"status": "error", "msg": "请求超时"}
            except Exception as exc:
                if attempt == 1:
                    continue
                return {"status": "error", "msg": str(exc)}
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass
        return {"status": "error", "msg": "未知错误"}

    # ------------------------------------------------------------------
    def add_collision_box(self, name: str, link: str,
                          sizes: list, poses: list, timeout: float = 8.0) -> dict:
        """添加碰撞盒。返回含 status/ret/mode 的响应（mode: sdk=真实 SDK, mock=演示）。"""
        result = self.send_command({
            "command": "add",
            "name": name,
            "link": link,
            "sizes": sizes,
            "poses": poses,
        }, timeout=timeout)
        return result if isinstance(result, dict) else {"status": "error", "msg": "无响应"}

    def remove_collision_box(self, name: str, timeout: float = 8.0) -> dict:
        """移除碰撞盒。"""
        result = self.send_command({"command": "remove", "name": name}, timeout=timeout)
        return result if isinstance(result, dict) else {"status": "error", "msg": "无响应"}

    def ping(self, timeout: float = 1.5) -> bool:
        """检测服务端是否存活（超时短，避免 GUI 卡顿）。"""
        result = self.send_command({"command": "ping"}, timeout=timeout)
        return result is not None and result.get("status") == "pong"


# ----------------------------------------------------------------------
# 全局单例 + 服务端子进程管理
# ----------------------------------------------------------------------
_collision_client: Optional[CollisionBoxClient] = None
_cpp_server_process: Optional[subprocess.Popen] = None
_server_log_path = os.path.join(_PROJECT_ROOT, "bin", "collision_server.log")
_last_start_error = ""


def get_collision_start_error() -> str:
    """最近一次启动失败的诊断信息（供 GUI 展示）。"""
    return _last_start_error


def _tail(path: str, n: int = 15) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:]).strip()
    except Exception:
        return ""


def get_collision_client() -> CollisionBoxClient:
    global _collision_client
    if _collision_client is None:
        _collision_client = CollisionBoxClient()
    return _collision_client


def _find_server_exe() -> Optional[str]:
    """查找服务端可执行文件（基于本模块所在项目根目录，兼容多种布局）。"""
    candidates = [
        os.path.join(_PROJECT_ROOT, "bin", "collision_box_server.exe"),
        os.path.join(_PROJECT_ROOT, "bin", "Release", "collision_box_server.exe"),
        os.path.join(_PROJECT_ROOT, "collision_box_server.exe"),
        os.path.join(_PROJECT_ROOT, "cpp_src", "bin", "collision_box_server.exe"),
        "./bin/collision_box_server.exe",
        "./collision_box_server.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def start_cpp_collision_server(port: int = 9999, timeout: float = 3.0,
                               robot_ip: Optional[str] = None) -> bool:
    """启动 C++ 碰撞盒服务端子进程并等待就绪。

    Args:
        port: 本机 Socket 端口
        timeout: 等待服务就绪时间（秒）
        robot_ip: 机械臂 IP；None 则读环境变量 AUBO_ROBOT_IP，再默认 192.168.1.100
    """
    import os
    global _cpp_server_process

    client = get_collision_client()
    # 保证客户端端口与将要启动的服务端端口一致（默认 9999；传其它端口时同步）
    if client.server_port != port:
        client.disconnect()
        client.server_port = port

    if _cpp_server_process is not None and _cpp_server_process.poll() is None:
        if client.ping():
            logger.info("[collision] 碰撞盒服务端已在运行")
            return True

    exe_path = _find_server_exe()
    if exe_path is None:
        _last_start_error = ("找不到 collision_box_server.exe。请先编译："
                             "PyCharm 运行 cpp_src/build_collision_server.py（见 "
                             "docs/cpp碰撞盒服务编译与使用.md）")
        logger.error("[collision] %s", _last_start_error)
        return False

    rob_ip = robot_ip or os.environ.get("AUBO_ROBOT_IP", "192.168.1.100")
    cmd = [exe_path, str(port), "-r", rob_ip]
    logger.info("[collision] 启动服务端: %s", " ".join(cmd))
    # 子进程日志落盘（避免 PIPE 不消费导致卡死/无日志可查）
    log_f = open(_server_log_path, "a", encoding="utf-8", errors="replace")
    log_f.write("\n===== start %s =====\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    log_f.flush()
    try:
        _cpp_server_process = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        log_f.close()
    except Exception as exc:
        log_f.close()
        _last_start_error = f"启动服务端失败: {exc}"
        logger.error("[collision] %s", _last_start_error)
        return False

    # 等待服务就绪
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.ping():
            logger.info("[collision] 碰撞盒服务端就绪")
            return True
        time.sleep(0.15)
    # 启动超时：给出可读诊断
    tail = _tail(_server_log_path)
    _last_start_error = (f"启动超时({timeout}s)。日志: {_server_log_path}\n"
                         f"{tail}\n\n排查：端口被占用？删掉 bin/ 旧日志后重试；"
                         f"或用任务管理器结束残留 collision_box_server 进程。")
    logger.error("[collision] %s", _last_start_error)
    return False


def stop_cpp_collision_server():
    """停止 C++ 碰撞盒服务端子进程。"""
    global _cpp_server_process, _collision_client
    if _cpp_server_process is not None:
        try:
            _cpp_server_process.terminate()
            _cpp_server_process.wait(timeout=2)
        except Exception:
            try:
                _cpp_server_process.kill()
            except Exception:
                pass
        _cpp_server_process = None
        logger.info("[collision] 碰撞盒服务端已停止")
    if _collision_client is not None:
        _collision_client.disconnect()
        _collision_client = None


if __name__ == "__main__":
    # 简易自测：Ping 正在运行的服务端
    logging.basicConfig(level=logging.INFO)
    c = get_collision_client()
    print("ping =", c.ping())
