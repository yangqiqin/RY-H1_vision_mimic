# -*- coding: utf-8 -*-
import asyncio
import math
import threading
from flask import Flask, Response
import logging
import time
from time import sleep
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import open3d as o3d
import yaml
import sys
from scipy.spatial.transform import Rotation as R
from PCAN_ruiyan16 import send_predefined_action, send_clean
from adaptive_grasp import adaptive_open_apple, adaptive_close_apple

# ══════════════════════════════════════════════════
#  pyaubo_sdk 适配层
#  
# ══════════════════════════════════════════════════
try:
    from pyaubo_sdk import RpcClient
    _SDK_OK = True
except ImportError:
    _SDK_OK = False
    print("[警告] pyaubo_sdk 未找到")


class RobotErrorType:
    RobotError_SUCC         = 0
    RobotError_NoLink       = 2003
    RobotError_Move         = 2004
    RobotError_LOGIN_FAILED = 2005


class RobotToolPowerType:
    OUT_0V  = 0
    OUT_12V = 1
    OUT_24V = 2


class Auboi5Robot:
    """用 pyaubo_sdk.RpcClient 实现与原 auboi5_ctrl 相同的接口"""

    def __init__(self):
        self.connected   = False
        self._cli        = None
        self._robot_name = None
        self._ri         = None
        self._mc         = None

    @staticmethod
    def initialize():
        return RobotErrorType.RobotError_SUCC

    @staticmethod
    def uninitialize():
        pass

    def create_context(self):
        if not _SDK_OK:
            return 0
        self._cli = RpcClient()
        self._cli.setRequestTimeout(2000)
        return 0  # ≥0 = 成功

    def connect(self, ip='192.168.1.100', port=8899):
        """
        连接机械臂。
        固定用 30004 端口（新版固件），忽略传入的 port 参数。
        """
        if not _SDK_OK:
            self.connected = True
            return RobotErrorType.RobotError_SUCC
        AUBO_PORT = 30004
        try:
            print(f"[臂] 连接 {ip}:{AUBO_PORT} ...")
            self._cli.connect(ip, AUBO_PORT)
            self._cli.login("aubo", "123456")
            self._robot_name = self._cli.getRobotNames()[0]
            self._ri         = self._cli.getRobotInterface(self._robot_name)
            self._mc         = self._ri.getMotionControl()
            self._cli.getRuntimeMachine().start()
            time.sleep(1)
            self._mc.setSpeedFraction(1.0)
            self.connected = True
            print(f"[臂] 连接成功: {self._robot_name}")
            return RobotErrorType.RobotError_SUCC
        except Exception as e:
            print(f"[臂] connect 异常: {e}")
            return RobotErrorType.RobotError_LOGIN_FAILED

    def disconnect(self):
        try:
            if self._cli and self.connected:
                self._cli.getRuntimeMachine().abort()
                self._cli.logout()
                self._cli.disconnect()
        except Exception:
            pass
        self.connected = False
        return RobotErrorType.RobotError_SUCC

    def robot_startup(self, collision=6, tool_dynamics=None):
        return RobotErrorType.RobotError_SUCC

    def set_tool_power_type(self, power_type):
        return RobotErrorType.RobotError_SUCC

    def set_joint_maxvelc(self, velc_tuple):
        try:
            self._mc.setSpeedFraction(min(1.0, float(velc_tuple[0])))
        except Exception:
            pass
        return RobotErrorType.RobotError_SUCC

    def set_end_max_line_velc(self, velc):
        return RobotErrorType.RobotError_SUCC

    def move_to_target_in_cartesian(self, position, rpy):
        """
        笛卡尔运动（阻塞，1s轮询等到位）
        position : (x, y, z)  单位：米
        rpy      : (roll, pitch, yaw) 单位：度
        """
        if not _SDK_OK:
            time.sleep(1.0)
            return RobotErrorType.RobotError_SUCC
        try:
            rx = math.radians(rpy[0])
            ry = math.radians(rpy[1])
            rz = math.radians(rpy[2])
            self._mc.moveLine(
                list(position) + [rx, ry, rz],
                0.13,   # 线速度 m/s（慢速）0.15
                0.2,    # 加速度 m/s²0.3
                0.0,
                0       # 阻塞模式
            )
            self._wait_done()
            return RobotErrorType.RobotError_SUCC
        except Exception as e:
            print(f"[臂] move_to_target_in_cartesian 异常: {e}")
            return RobotErrorType.RobotError_Move

    def _wait_done(self, timeout=60):
        """1s 轮询，等机械臂停止运动"""
        time.sleep(1.0)                          # 先等运动开始
        start = time.time()
        while time.time() - start < timeout:
            try:
                state = self._ri.getRobotState()
                if hasattr(state, 'isMoving') and not state.isMoving():
                    break
                if hasattr(state, 'isSteady') and state.isSteady():
                    break
            except Exception:
                time.sleep(1.0)
                break
            time.sleep(1.0)                      # 1s 轮询间隔

    def get_current_waypoint(self):
        """返回 {'joint': [j1..j6]}，单位弧度"""
        if not _SDK_OK:
            return {'joint': [0.0, -0.5, 1.2, 0.3, 1.57, 0.0]}
        try:
            joints = self._ri.getRobotState().getJointPositions()
            return {'joint': list(joints)}
        except Exception as e:
            print(f"[臂] get_current_waypoint 异常: {e}")
            return {'joint': [0.0, -0.5, 1.2, 0.3, 1.57, 0.0]}

    def forward_kin(self, joint_angles):
        """返回 {'pos':(x,y,z), 'ori':(w,x,y,z)}"""
        if not _SDK_OK:
            return {'pos': (0.0, -0.47, 0.4), 'ori': (1.0, 0.0, 0.0, 0.0)}
        try:
            pose = self._ri.getRobotState().getToolPose()
            pos  = (pose[0], pose[1], pose[2])
            rot  = R.from_euler('xyz', [pose[3], pose[4], pose[5]])
            q    = rot.as_quat()            # x,y,z,w
            ori  = (q[3], q[0], q[1], q[2])  # w,x,y,z
            return {'pos': pos, 'ori': ori}
        except Exception as e:
            print(f"[臂] forward_kin 异常: {e}")
            return None


# ══════════════════════════════════════════════════
#  全局配置
# ══════════════════════════════════════════════════

limitspeed = 0.3          # tree fruit grasp: slow and stable


offsetx = 0
offsety = -0.1
offsetz = 0

want_obj_num = 1   # 每次扫描只要找到1个就开始抓，抓完再扫下一个

image_width  = 1280
image_height = 720
chang_color  = False

# 高悬停位（扫描）
#high_hover_pos = (-0.125483, -0.4 + offsety, 0.45)
#high_hover_pos = (-0.122483, -0.31 + offsety, 0.45)
high_hover_pos = (-0.122483, -0.14, 0.53)
#high_hover_pos = (-0.00833483,-0.488453, 0.38577)
high_hover_rpy = (180,-90, -88)

# 递可乐给客人
#high_hover_pos_kele = (-0.098, -0.525113 + offsety, 0.4)
#high_hover_rpy_kele = (86.72, 0, 0)

# 放水果到右边纸箱
high_hover_pos_shuiguo = (-0.49, -0.32 + offsety , 0.52)
high_hover_rpy_shuiguo = (150,-40, -88)

# 托盘位置（保留原版，备用）
place_pos_htpA = (-0.3,  -0.15 + offsety, 0.3)
place_rpy_htpA = (180, 0, 0)
place_pos_ltpB = ( 0.30, -0.15 + offsety, 0.3)
place_rpy_ltpB = (180, 0, 0)
place_pos_txm  = ( 0.00, -0.05 + offsety, 0.3)
place_rpy_txm  = (180, 0, -90)
place_position = [
    [place_pos_htpA, place_rpy_htpA],
    [place_pos_ltpB, place_rpy_ltpB],
    [place_pos_txm,  place_rpy_txm],
]

'''
R_cam2gripper = np.array([
    [0, -0.05819466,  0.48942417],
    [-0.08278096,  0.96164373,  0.26151223],
    [-0.4858703,  -0.2680573,   0.83191065]
])
t_cam2gripper = np.array([0.09326227, -0.28075383, 0.01818273])'''
R_cam2gripper = np.array([
    [-0.02419637, -0.99950899, 0.01992146],
    [0.99955215, -0.02453875, -0.01714335],
    [0.01762429, 0.01949733, 0.99965460]
])
t_cam2gripper = np.array([0.07802404, 0.00426695, 0.03737631])

# ══════════════════════════════════════════════════
#  物体配置 —— 五种水果
#  苹果、香蕉、橘子、芒果、梨子
#  
# ══════════════════════════════════════════════════

# YOLO模型里对应的类别名称（需与训练时一致）,"pear"orange
all_objects    = ["apple","apple"]

# 本次任务抓取顺序（可按需调整）,"pear"
take_order     = ["apple","apple"]

# 需要计算坐标的物体（与all_objects一致）,"pear"
target_objects = ["apple","apple"]

grasp_objects  = []

# 分类：全部放同一托盘（递给观众），无需分A/B,"pear"
task0_objA     = []
task0_objB     = ["apple","apple"]
task1_objA     = []
task1_objB     = []

# 水果高度约0.012m（距桌面抓取点高度）
#   苹果    橘子0.055   芒果  梨子
target_heigh = [0.065,0.065,0.065]

table_height = 0   # 桌面在机械臂基坐标系的z值

# 灵巧手动作编号
# 水果体积比可乐小，用同一套张手/抓握动作
# 如需单独调整各水果的抓取力度，在PCAN_ruiyan16.py里修改对应ActionTab3行
#   苹果  梨子  香蕉  橘子  芒果
action_release = [1,1]   # apple open hand action 3
action_grab    = [0,0]   # apple grasp action 2

# p_ab：物体相对末端的偏移（xyz，单位米）
# r_ab：抓取姿态角补偿（roll,pitch,yaw，单位度）
# 水果较矮，z偏移比可乐小（0.14→0.10）
p_ab = [
    [-0.069, -0.006, 0.175],   # 苹果 -0.069, -0.006, 0.175-0.067, -0.008, 0.1735
    [-0.069, -0.006, 0.175],   # 苹果
    #[-0.069, -0.006, 0.175],   # 苹果
    #[-0.052, 0.006, 0.170],   # orange
    # [-0.060, 0.008, 0.15],    # mango
]
#[-0.065, 0.008, 0.132],   # 梨子
r_ab = [
    [60, -30, 10],  # 苹果[60, -30, 10], # 苹果[60, -30, 10],
    [60, -30, 10],  # 苹果
    #[60, -30, 10],  # 苹果
    #[60, -30, 10],  # orange
    # [40, 0, -88],   # mango
   
]
 #[40, 0,-88],   # 梨子
SPACE_GRASP_Z_OFFSET = 0.00
SPACE_PRE_GRASP_Z_OFFSET = 0.08
SPACE_RETRACT_Z_OFFSET = 0.10
SPACE_MIN_Z = 0.18
SPACE_MAX_Z = 0.68
text_depth = ""
gx = 0
gy = 0


# ══════════════════════════════════════════════════
#  Flask Web推流系统（替换原显示线程）
#  浏览器访问（本机，不需要网络）：
#    http://localhost:5000       → 扫描识别画面
#    http://localhost:5000/grasp → 抓取过程画面
#
#  原显示线程完全去掉，彻底解决Wayland/Qt段错误问题
# ══════════════════════════════════════════════════

_display_stop = False

# 录制配置（新增）
import os
SAVE_VIDEO         = True
VIDEO_DIR          = "grasp_videos"
_video_writer      = None
_video_writer_lock = threading.Lock()

# 两路推流帧缓冲
_web_scan_frame  = None   # 扫描识别画面（YOLO标注）
_web_grasp_frame = None   # 抓取过程画面（原始相机）
_web_lock        = threading.Lock()

_flask_app = Flask(__name__)


@_flask_app.route('/')
def _page_scan():
    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>扫描识别</title>
  <style>
    body{background:#111;margin:0;display:flex;flex-direction:column;
         align-items:center;font-family:sans-serif;color:#fff}
    h2{margin:12px 0;font-size:22px}
    img{width:95vw;max-width:1280px;border:2px solid #0f0;border-radius:4px}
    a{color:#0af;margin:10px;font-size:16px;text-decoration:none}
    a:hover{text-decoration:underline}
  </style>
</head>
<body>
  <h2>扫描识别结果画面</h2>
  <img src="/stream/scan">
  <a href="/grasp">→ 切换到抓取过程画面</a>
</body>
</html>'''


@_flask_app.route('/grasp')
def _page_grasp():
    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>抓取过程</title>
  <style>
    body{background:#111;margin:0;display:flex;flex-direction:column;
         align-items:center;font-family:sans-serif;color:#fff}
    h2{margin:12px 0;font-size:22px}
    img{width:95vw;max-width:1280px;border:2px solid #f80;border-radius:4px}
    a{color:#0af;margin:10px;font-size:16px;text-decoration:none}
    a:hover{text-decoration:underline}
  </style>
</head>
<body>
  <h2>实时抓取过程画面</h2>
  <img src="/stream/grasp">
  <a href="/">→ 切换到扫描识别画面</a>
</body>
</html>'''


def _gen_mjpeg(key):
    """生成MJPEG流，浏览器img标签直接显示"""
    while True:
        with _web_lock:
            frame = _web_scan_frame if key == 'scan' else _web_grasp_frame
        if frame is not None:
            ok, buf = cv2.imencode('.jpg', frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n'
                       + buf.tobytes() + b'\r\n')
        time.sleep(0.04)   # 约25fps


@_flask_app.route('/stream/scan')
def _stream_scan():
    return Response(_gen_mjpeg('scan'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@_flask_app.route('/stream/grasp')
def _stream_grasp():
    return Response(_gen_mjpeg('grasp'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def _update_display(frame):
    """更新扫描识别推流帧（保留原函数名，方便兼容）"""
    global _web_scan_frame
    with _web_lock:
        _web_scan_frame = frame.copy()


def _update_grasp_stream(frame):
    """更新抓取过程推流帧"""
    global _web_grasp_frame
    with _web_lock:
        _web_grasp_frame = frame.copy()


def _start_flask():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    _flask_app.run(host='0.0.0.0', port=5000,
                   threaded=True, use_reloader=False)


# 相机占用标志：主循环读帧时为True，子线程不抢
_pipeline_busy = False
_pipeline_busy_lock = threading.Lock()


def _grasp_cam_reader(pipeline_ref, align_ref):
    """
    独立线程：专门持续读相机帧推给抓取过程画面。
    主循环空闲时（扫描阶段）用主循环的帧。
    主循环阻塞时（机械臂运动中），这个线程接管读帧，保持画面实时。
    """
    global _display_stop
    while not _display_stop:
        with _pipeline_busy_lock:
            busy = _pipeline_busy
        if busy:
            # 主循环正在读帧，子线程等待不抢
            time.sleep(0.03)
            continue
        try:
            frames = pipeline_ref.wait_for_frames(timeout_ms=200)
            af     = align_ref.process(frames)
            cf     = af.get_color_frame()
            if cf:
                img = np.asanyarray(cf.get_data()).copy()
                _update_grasp_stream(img)
                # 写入视频文件（新增）
                with _video_writer_lock:
                    if _video_writer is not None:
                        _video_writer.write(
                            cv2.resize(img, (image_width, image_height)))
        except Exception:
            pass
        time.sleep(0.03)


# ══════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def get_cursor_position():
    # Ubuntu 下不使用 msvcrt，主流程未调用此函数
    return 0, 0


def calculate_grasp_angle(mask):
    """从分割mask计算物体旋转角，与原版完全一致"""
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8)

    if len(stats) > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    else:
        largest_label = 0

    largest_mask = np.zeros_like(mask)
    largest_mask[labels == largest_label] = 255

    contours, _ = cv2.findContours(
        largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        raise Exception("未找到物体轮廓")

    contour = contours[0]
    rect    = cv2.minAreaRect(contour)
    box     = cv2.boxPoints(rect)
    box     = np.intp(box)
    center, size, angle = rect

    def _angle_between(p1, p2):
        dy = p2[1] - p1[1]
        dx = p2[0] - p1[0]
        a  = np.degrees(np.arctan2(dy, dx))
        if a < -90: a += 180
        elif a > 90: a -= 180
        return a

    max_distance = 0
    min_distance = 10000
    point1 = point2 = None
    for i in range(len(box)):
        for j in range(len(box)):
            if i == j:
                continue
            d = np.linalg.norm(box[i] - box[j])
            cp = np.mean([box[i], box[j]], axis=0)
            if np.allclose(center, cp, atol=5):
                continue
            if d < min_distance:
                min_distance = d
            if d > max_distance:
                max_distance = d
                if box[i][1] > box[j][1]:
                    point1, point2 = box[i], box[j]
                else:
                    point1, point2 = box[j], box[i]

    angle1 = 0
    if point1 is not None and point2 is not None:
        angle1 = _angle_between(point1, point2)

    ratio = max_distance / (min_distance + 1e-6)
    if ratio < 1.2:
        angle1 = 0

    return -angle1, box, point1, point2, largest_mask, ratio


def pose_vectors_to_end2base_transforms(
        position_AB, euler_angles_AB,
        position_A_base, euler_angles_A_base):
    """坐标变换：物体位置 → 末端目标位姿（与原版完全一致）"""

    print("物体在端坐标系中的位置:", np.round(position_AB, 2))
    print("物体在端坐标系中的姿态角:", np.round(euler_angles_AB, 2))

    rotation_AB = R.from_euler('xyz', euler_angles_AB, degrees=True).as_matrix()
    T_AB        = np.eye(4)
    T_AB[:3, :3] = rotation_AB
    T_AB[:3, 3]  = position_AB
    T_BA         = np.linalg.inv(T_AB)

    position_BA     = T_BA[:3, 3]
    euler_angles_BA = R.from_matrix(T_BA[:3, :3]).as_euler('xyz', degrees=True)

    print("端坐标系在物体坐标系中的位置:", np.round(position_BA, 2))
    print("端坐标系在物体坐标系中的姿态角:", np.round(euler_angles_BA, 2))
    print("物体坐标系在基坐标系中的位置:", np.round(position_A_base, 2))
    print("物体坐标系在基坐标系中的姿态角:", np.round(euler_angles_A_base, 2))

    rotation_A_base = R.from_euler('xyz', euler_angles_A_base, degrees=True).as_matrix()
    rotation_B_A    = R.from_euler('xyz', euler_angles_BA,     degrees=True).as_matrix()

    T_A_base        = np.eye(4)
    T_A_base[:3, :3] = rotation_A_base
    T_A_base[:3, 3]  = position_A_base

    T_B_A           = np.eye(4)
    T_B_A[:3, :3]   = rotation_B_A
    T_B_A[:3, 3]    = position_BA

    T_B_base            = T_A_base @ T_B_A
    position_B_base     = T_B_base[:3, 3]
    euler_angles_B_base = R.from_matrix(T_B_base[:3, :3]).as_euler('xyz', degrees=True)

    print("端坐标系在基坐标系中的位置:", np.round(position_B_base, 2))
    print("端坐标系在基坐标系中的姿态角:", np.round(euler_angles_B_base, 2))

    return position_B_base, euler_angles_B_base


# ══════════════════════════════════════════════════
#  主抓取流程
# ══════════════════════════════════════════════════

async def grasp_and_place_object_task10(
        model, cam_intrinsics, pipeline, align,
        depth_scale, model_size, aubo_robot):

    global grasp_objects, target_objects, take_order, _display_stop,_video_writer

    scan_posx = [[] for _ in range(4)]
    num1 = num2 = num3 = num4 = num5 = num6 = num7 = 0
    k    = 0.8

    #num7是否移动到高度扫描位
    #if num7 == 0:
    #    aubo_robot.move_to_target_in_cartesian(high_hover_pos, high_hover_rpy)
    #    num7 = 1

    processed_objects = []
    _no_apple_count = 0    # 连续未检测到apple的次数，达到3次则结束
    _skip_grasp_decision = False  # 稳定帧/扫描偏移期间跳过抓取决策
    start_time  = time.time()

    # 开始录制全程（新增）
    if SAVE_VIDEO:
        os.makedirs(VIDEO_DIR, exist_ok=True)
        fname  = f"{VIDEO_DIR}/grasp_all_{int(time.time())}.avi"
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        with _video_writer_lock:
            _video_writer = cv2.VideoWriter(
                fname, fourcc, 15, (image_width, image_height))
        print(f"[录制] 开始录制全程: {fname}")

    while _no_apple_count < 3:

        # 读一帧（主循环占用相机，子线程等待）
        with _pipeline_busy_lock:
            _pipeline_busy = True
        frames         = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        color_frame    = aligned_frames.get_color_frame()
        depth_frame    = aligned_frames.get_depth_frame()
        with _pipeline_busy_lock:
            _pipeline_busy = False
        if not depth_frame or not color_frame:
            print("[Info] No L515 data.")
            continue

        rgb = np.asanyarray(color_frame.get_data())
        if chang_color:
            rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        depth          = np.asanyarray(depth_frame.get_data())
        print("[Debug]depth:",depth)
        depth_in_meters = depth * depth_scale

        # YOLO推理
        results        = model(rgb, conf=0.75)
        annotated_frame = results[0].plot()
        print("[Debug]YOLO推理captured image shape:",annotated_frame.shape)
        
        #if len(results)>0:
           #print("[Debug]results[0]:",results[0])
           #print("[Debug]results[0].names:",results[0].names)

        # 深度文字（用上一帧坐标）
        if 0 <= gy < depth_in_meters.shape[0] and 0 <= gx < depth_in_meters.shape[1]:
            text_depth = f"Depth ({gx},{gy}): {depth_in_meters[gy,gx]:.2f}m"
        cv2.putText(annotated_frame, text_depth,
                    (gx, gy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        model_info = f"imgsz:{model_size}  Speed:{results[0].speed['inference']:.1f}ms"
        print("[Debug]mouse_callback YOLOv8 Inference imgsz")
        cv2.putText(annotated_frame, model_info,
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)

        # 扫描识别画面推流（每帧都更新YOLO标注图）
        _update_display(annotated_frame)

        # 注：抓取过程画面由 _grasp_cam_reader 子线程持续推流，不在此更新

        if _display_stop:
            break

        # ── 动态检测：检查是否检测到apple ──
        if results[0].masks is None or len(results[0].boxes) == 0:
            _no_apple_count += 1
            print(f"[检测] 未检测到apple ({_no_apple_count}/3)")
            if _no_apple_count >= 3:
                print("[结束] 连续3次未检测到apple，任务结束")
                break
            print("[等待] 10秒后重新检测...")
            await asyncio.sleep(10)
            continue

        # 检测到apple，重置连续未检测计数
        _no_apple_count = 0
        _skip_grasp_decision = False

        # 确认YOLO是否检测到了对象
        if results[0].masks is not None:
            
            # 获取检测到的对象的掩码和类别
            masks = results[0].masks.data.cpu().numpy()
            
            # 获取检测到的对象的类别
            cls = [results[0].names[int(box.cls)] for box in results[0].boxes]
            print("[Debug] Detected classes:", cls)  # 调试信息，打印检测到的类名

            # 获取移动前当前机械臂的关节状态
            current_joint_angles = aubo_robot.get_current_waypoint()['joint']
            print(f"当前关节角度: ",current_joint_angles)

            # 获取正向运动学结果
            fk_result = aubo_robot.forward_kin(current_joint_angles)
            if fk_result is None:
                raise Exception("正向运动学计算失败")
            
            # 提取旋转矩阵和平移向量
            end_effector_position = fk_result['pos']

            # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
            end_effector_quaternion = fk_result['ori']
            end_effector_quaternion = [
                end_effector_quaternion[1],
                end_effector_quaternion[2],
                end_effector_quaternion[3],
                end_effector_quaternion[0]
            ]
            print(f"当前移动前初始所在位置: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
             # 将四元数转换为旋转矩阵
            R_gripper2base = R.from_quat(end_effector_quaternion).as_matrix()

            for obj in cls:

                # 获取目标对象的索引
                cls_idx = cls.index(obj)

                # 获取目标对象的像素掩码 大小是 384*640
                mask = masks[cls_idx]
                print(f"[Debug] Mask shape: {mask.shape}")

                # 把mask 等比例缩放到深度图大小 768 * 1280 
                mask = cv2.resize(mask, (1280, 768), interpolation=cv2.INTER_NEAREST)
                print(f"[Debug] Mask shape after resize: {mask.shape}") 
                # 裁切图像到1280x720
                start_x = (mask.shape[1] - 1280) // 2
                start_y = (mask.shape[0] - 720) // 2
                mask = mask[start_y:start_y + 720, start_x:start_x + 1280]
                print(f"[Debug] Mask shape after resize mask : {mask.shape}")    

                # 将mask 转成 CV_8UC1 格式图片
                mask_img = (mask * 255).astype(np.uint8)
                print(f"[Debug] mask 转成 CV_8UC1 格式图片: {mask_img.shape}") 


                # 计算抓取角度和最小外接矩形
                angle, box, p1,p2,largest_mask,ratio = calculate_grasp_angle(mask_img)
                print(f"[Debug] largest_mask: {largest_mask.shape}")
                print(f"[Debug] 计算抓取角度: {angle}")

                # 在原图像上绘制最小外接矩形
                cv2.drawContours(annotated_frame, [box], 0, (0, 255, 0), 2)


                # 在图像中标注P1和P2

                if p1[0] != 0 and p1[1] != 0 and p2[0] != 0 and p2[1] != 0:
                    cv2.circle(annotated_frame, tuple(p1), 4, (255, 0, 0), -1)  # 红色小点
                    cv2.circle(annotated_frame, tuple(p2), 4, (255, 0, 0), -1)  # 红色小点


                # 计算mask区域的x和y的平均值
                mask_indices = np.where(largest_mask > 0)
                avg_x = np.mean(mask_indices[1])
                avg_y = np.mean(mask_indices[0])
                center_pixel = (int(avg_x), int(avg_y))
                print(f"mask区域的x和y的平均值center_pixel: {center_pixel,(avg_x,avg_y)}")

                # 获取 largest_mask 中深度非零的最小值
                non_zero_depth_values = depth_in_meters[largest_mask > 0]
                non_zero_depth_values = non_zero_depth_values[non_zero_depth_values > 0]
                if non_zero_depth_values.size > 0:
                    min_depth_value = np.min(non_zero_depth_values)
                else:
                    min_depth_value = 0.4


                ys, xs = np.where(largest_mask > 0)
                depths = depth_in_meters[ys, xs]
                valid = depths > 0
                if np.sum(valid) < 20:
                    print("[Warn] fruit mask has too few valid depth pixels, skip this detection.")
                    continue

                xs_valid = xs[valid]
                ys_valid = ys[valid]
                depths_valid = depths[valid]
                depth_value = float(np.median(depths_valid))
                center = np.array([
                    float(np.median((xs_valid - cam_intrinsics["cx"]) * depths_valid / cam_intrinsics["fx"])),
                    float(np.median((ys_valid - cam_intrinsics["cy"]) * depths_valid / cam_intrinsics["fy"])),
                    depth_value
                ])
                center_pixel = (int(np.median(xs_valid)), int(np.median(ys_valid)))
                area = np.sum(valid) * (depth_value / cam_intrinsics["fx"]) * (depth_value / cam_intrinsics["fy"]) * 1e4
                print(f"[Debug] area : {area}")
                print(f"[Space] P_cam from mask median: {np.round(center, 4)}, center_pixel:{center_pixel}")

                P_cam = center
                print(f"[Debug] P_cam : {center}")

                # object_height = table_height+target_heigh[all_objects.index(obj)]

                # 将点从相机坐标系转换到末端执行器坐标系中
                # P_gripper = np.dot(R_cam2gripper, P_cam) + t_cam2gripper
                P_gripper = np.dot(R_cam2gripper, P_cam) + t_cam2gripper
                print(f"[Debug] P_gripper: {P_gripper}")
                print(f"[Debug] R_cam2gripper: {R_cam2gripper}")
                print(f"[Debug] t_cam2gripper: {t_cam2gripper}")
                print(f"[Debug] np.dot(R_cam2gripper, P_cam) : {np.dot(R_cam2gripper, P_cam) }")

                # 将点从末端执行器坐标系转换到基坐标系中
                P_base = np.dot(R_gripper2base, P_gripper) + end_effector_position
                print(f"[Debug] R_gripper2base: ",R_gripper2base)
                print(f"[Debug] np.dot(R_gripper2base, P_gripper) : ",np.dot(R_gripper2base, P_gripper) ) 
                print(f"[Debug] end_effector_position: ",end_effector_position)
                print(P_base)



                # 根据物品名找到物体高度值
                # object_height = table_height + object_height
                object_height = float(np.clip(P_base[2] + SPACE_GRASP_Z_OFFSET, SPACE_MIN_Z, SPACE_MAX_Z))

                # 计算目标对象的目标位置
                target_pos = ( P_base[0], P_base[1], object_height )
                print(f"[Debug] 目标对象的目标位置: {target_pos}")   
                 # 计算目标位置的模长
                target_pos_magnitude = np.linalg.norm(target_pos)
                
                print(P_cam)
                print(P_gripper)
                print(P_base)
                print(target_pos)
                print("+++++++++++++++++++++")
                #aubo_robot.move_to_target_in_cartesian(target_pos,high_hover_rpy)
               # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                   raise Exception("正向运动学计算失败")
            
               # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

               # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                 end_effector_quaternion[1],
                 end_effector_quaternion[2],
                 end_effector_quaternion[3],
                 end_effector_quaternion[0]
                ]
                print(f"当前移动前初始所在位置test: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                                             
                
                if obj in target_objects:
                    # 将物体及及x,y,z,和target_pos_magnitude保存到grasp_objects列表中，
                    # 检查 grasp_objects 是否已经包含该对象
                    existing_object = next((item for item in grasp_objects if item[0] == obj), None)
                    if existing_object:
                        # 替换已有对象并进行加权平均
                        grasp_objects = [item if item[0] != obj else (
                            obj,
                            item[1] * k + P_base[0] * (1-k),
                            item[2] * k + P_base[1] * (1-k),
                            item[3] * k + P_base[2] * (1-k),
                            item[4] * k + target_pos_magnitude * (1-k),
                            item[5] * k + angle * (1-k),
                            item[6] * k + area * (1-k),
                            item[7] * k + ratio * (1-k),
                            item[8] * k + min_depth_value * (1-k)
                        ) for item in grasp_objects]
                    else:
                        # 新加入对象
                        grasp_objects.append((obj, P_base[0], P_base[1], P_base[2], target_pos_magnitude, angle , area , ratio, min_depth_value ))
                

                print(f"[Debug] grasp_objects: ",grasp_objects)  
                # 在图像中标注物体中心点
                cv2.circle(annotated_frame, center_pixel, 5, (0, 0, 255), -1)  # 红色小点

                # 显示具体的 x, y, z 坐标值
                text_inof = f"A:{angle:.2f}, S:{area:.2f}, R:{ratio:.2f},min_dep:{min_depth_value:.2f})"
                text_cam = f"Cam: ({P_cam[0]:.2f}, {P_cam[1]:.2f}, {P_cam[2]:.2f},)"
                text_gripper = f"grip: ({P_gripper[0]:.2f}, {P_gripper[1]:.2f},{P_gripper[2]:.2f}) flange: ({end_effector_position[0]:.2f}, {end_effector_position[1]:.2f},{end_effector_position[2]:.2f})"
                text_base = f"base: ({P_base[0]:.2f}, {P_base[1]:.2f},{P_base[2]:.2f})"
                text_distance = f"distance: ({target_pos_magnitude:.2f})"

                cv2.putText(annotated_frame, text_inof, (center_pixel[0] + 10, center_pixel[1] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)  # 蓝色
                cv2.putText(annotated_frame, text_cam, (center_pixel[0] + 10, center_pixel[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)  # 蓝色
                cv2.putText(annotated_frame, text_gripper, (center_pixel[0] + 10, center_pixel[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)  # 绿色
                cv2.putText(annotated_frame, text_base, (center_pixel[0] + 10, center_pixel[1] + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)  # 红色
                cv2.putText(annotated_frame, text_distance, (center_pixel[0] + 10, center_pixel[1] + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)  # 红色
    

                # 输出图像已经抓取的特体名字在图像上
                text = "Processed: " + ", ".join(processed_objects)
                cv2.putText(annotated_frame, text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 1)                

            grasp_objects.sort( key=lambda obj: obj[4] )
            for obj in grasp_objects:
                print( obj )
            

            # 得到的数量#num4扫描方向索引#检测到的物体数
            num1 = len(grasp_objects)
            print( "num1:", num1, "num5:", num5  )
            # 获取正向运动学结果
            fk_result = aubo_robot.forward_kin(current_joint_angles)
            if fk_result is None:
                raise Exception("正向运动学计算失败")
            
            # 提取旋转矩阵和平移向量
            end_effector_position = fk_result['pos']

            # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
            end_effector_quaternion = fk_result['ori']
            end_effector_quaternion = [
                end_effector_quaternion[1],
                end_effector_quaternion[2],
                end_effector_quaternion[3],
                end_effector_quaternion[0]
            ]
            print(f"当前移动前初始所在位置3: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")

            if not _skip_grasp_decision:
                if num1 < want_obj_num : 
                    scan_pos = high_hover_pos
                    scan_posx[0] = (scan_pos[0], scan_pos[1] - 0.05, scan_pos[2]) 
                    scan_posx[1] = (scan_pos[0], scan_pos[1] + 0.05, scan_pos[2]) 
                    scan_posx[2] = (scan_pos[0] + 0.1, scan_pos[1], scan_pos[2]) 
                    scan_posx[3] = (scan_pos[0] - 0.1, scan_pos[1], scan_pos[2]) 

                    result = aubo_robot.set_joint_maxvelc(  (0.2, 0.2, 0.2, 0.2, 0.2, 0.2) )
                    result = aubo_robot.set_end_max_line_velc(0.2)
                    aubo_robot.move_to_target_in_cartesian( scan_posx[num4], high_hover_rpy)
                    num4 = num4 + 1 
                    if num4 == 4:
                        num4 = 0
                    continue

                # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                    raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                    end_effector_quaternion[1],
                    end_effector_quaternion[2],
                    end_effector_quaternion[3],
                    end_effector_quaternion[0]
                ]
                print(f"当前移动前初始所在位置4: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                #num5计算5帧
                if num1 >= want_obj_num and num5 <= 5:
                    num5 = num5 + 1
                    _skip_grasp_decision = True
                    continue
            
            num5 = 0
            # ── 动态选取第一个检测到的apple ──
            if len(grasp_objects) == 0:
                continue
            take_obj = grasp_objects[0][0]
            print("take_obj (动态检测):", take_obj)
            num6=1  
            # 先走到要抓取的物品的位置正上方重定位
            #预接近标志位num6
            if num6 == 0:
                # 找到 take_obj 在 grasp_objects 中的位置
                grasp_obj_index = next((index for index, obj in enumerate(grasp_objects) if obj[0] == take_obj), None)
                if grasp_obj_index is None:
                    print(f"[Error] Target object {take_obj} not found in grasp_objects.")
                    continue
                num6 = 1
                scan_pos = [ grasp_objects[grasp_obj_index][1], grasp_objects[grasp_obj_index][2] + 0.12, 0.4 ]
                aubo_robot.move_to_target_in_cartesian( scan_pos, high_hover_rpy)
                print(f"go to object above position: {scan_pos}")
                print(f"scan_pos近标志位: ",grasp_objects[grasp_obj_index][1], grasp_objects[grasp_obj_index][2] + 0.12, 0.4)
                continue
            if take_obj in all_objects:
                    
                print(f"[Debug] Target object {num3} detected and processing: {take_obj}")
                
                #得到物品名在all_objects中的索引号
                grasp_idx = all_objects.index(take_obj)

                # 判断target_object是task0_objA还是task0_objB
                if take_obj in task0_objA:
                    task_idx = 0
                elif take_obj in task0_objB:
                    task_idx = 1
                elif take_obj in task1_objA:
                    task_idx = 2

                print( "task_idx:", task_idx , "grasp_idx:", grasp_idx ) 

                # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                    raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                   end_effector_quaternion[1],
                   end_effector_quaternion[2],
                   end_effector_quaternion[3],
                   end_effector_quaternion[0]
                ]
                print(f"当前移动前初始所在位置42: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                # 找到 take_obj 在 grasp_objects 中的位置
                grasp_obj_index = next((index for index, obj in enumerate(grasp_objects) if obj[0] == take_obj), None)
                if grasp_obj_index is None:
                    print(f"[Error] Target object {take_obj} not found in grasp_objects.")
                    continue

                # 根据物品名找到物体高度值
                object_height = table_height + target_heigh[grasp_idx]  
                # 计算目标对象的位置
                pos = ( grasp_objects[grasp_obj_index][1] , grasp_objects[grasp_obj_index][2] ,  object_height )
                fruit_center = np.array([
                    grasp_objects[grasp_obj_index][1],
                    grasp_objects[grasp_obj_index][2],
                    grasp_objects[grasp_obj_index][3],
                ], dtype=float)
                fruit_center[2] = np.clip(fruit_center[2] + SPACE_GRASP_Z_OFFSET, SPACE_MIN_Z, SPACE_MAX_Z)
                pos = tuple(fruit_center)
                object_height = float(pos[2])
                print(f"[Space] use fruit 3D position: {np.round(fruit_center, 4)}")
                print(f"[Space] object_height: {np.round(object_height, 4)}")
                print(f"[Debug] 计算目标对象的位置:",pos)  # 调试信息
                # 计算目标对物体的z轴角度
                angle = grasp_objects[grasp_obj_index][5]
                print(f"[Debug] 计算目标对物体的z轴角度:",angle)  # 调试信息
                # 水果抓取姿态角：香蕉、芒果需要对齐旋转角，其他固定0度
                # Apple-only test: use fixed object yaw.
                angle = 0
                xyz = [180, 0.0, -25]
                target_pos,rpy_xyz = pose_vectors_to_end2base_transforms( np.array(p_ab[grasp_idx]), np.array(r_ab[grasp_idx]), np.array(pos), np.array(xyz) )
                print(f"[Debug] p_ab[grasp_idx]:",p_ab[grasp_idx],r_ab[grasp_idx],pos,xyz)  # 调试信息
                print(f"[Debug] object_height:{object_height:.2f} Moving to position: {np.round(target_pos,4)}, RPY: { np.round(rpy_xyz, 4) }")  # 调试信息
                
                # 尝试移动机械臂到指定位置
                result = aubo_robot.set_joint_maxvelc(  (limitspeed, limitspeed, limitspeed, limitspeed, limitspeed, limitspeed) )
                result = aubo_robot.set_end_max_line_velc(limitspeed)
                grasp_pos = np.array(target_pos, dtype=float)
                pre_grasp_pos = grasp_pos.copy()
                retract_pos = grasp_pos.copy()
                pre_grasp_pos[2] = np.clip(grasp_pos[2] + SPACE_PRE_GRASP_Z_OFFSET, SPACE_MIN_Z, SPACE_MAX_Z)
                retract_pos[2] = np.clip(grasp_pos[2] + SPACE_RETRACT_Z_OFFSET, SPACE_MIN_Z, SPACE_MAX_Z)
                print(f"[Space] pre:{np.round(pre_grasp_pos, 4)}, grasp:{np.round(grasp_pos, 4)}, retract:{np.round(retract_pos, 4)}, rpy:{rpy_xyz}")
                # 步骤1：移到正上方
                print("[步骤1] 移到可乐正上方...")
                await send_clean()
                await send_predefined_action(1)
                result = aubo_robot.move_to_target_in_cartesian( pre_grasp_pos.tolist() , rpy_xyz)
                if result != RobotErrorType.RobotError_SUCC:
                    print(f"[Error] pre-grasp pose is unreachable or singular: {np.round(pre_grasp_pos, 4)}, rpy:{rpy_xyz}")
                    grasp_objects = []
                    continue
                await asyncio.sleep(0.3)
                # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                    raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                   end_effector_quaternion[1],
                   end_effector_quaternion[2],
                   end_effector_quaternion[3],
                   end_effector_quaternion[0]
                ]
                print(f"当前移到可乐正上方末端步骤1位置: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                
                # 步骤2：张手
                print("[步骤2] 张手...")
                await send_clean()
                apple_area = grasp_objects[grasp_obj_index][6]
                await adaptive_open_apple(apple_area)
                
                 # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                    raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                   end_effector_quaternion[1],
                   end_effector_quaternion[2],
                   end_effector_quaternion[3],
                   end_effector_quaternion[0]
                ]
                print(f"当前移到可乐正上方末端步骤2位置: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                
                
                await asyncio.sleep(0.5)
                # 移到目标位置
                # 步骤3：下降到抓取点-0.014  +0.017    -0.017   +0.0145
                print("[步骤3] 下降到可乐...")
                #grasp_pos[1]=grasp_pos[1]-0.014
                #grasp_pos[2]=grasp_pos[2]+0.017
                result = aubo_robot.move_to_target_in_cartesian(grasp_pos.tolist(), rpy_xyz)
                if result != RobotErrorType.RobotError_SUCC:
                    print(f"[Error] grasp pose is unreachable or singular: {np.round(grasp_pos, 4)}, rpy:{rpy_xyz}")
                    grasp_objects = []
                    continue
                
                 # 获取正向运动学结果
                fk_result = aubo_robot.forward_kin(current_joint_angles)
                if fk_result is None:
                    raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                end_effector_quaternion = fk_result['ori']
                end_effector_quaternion = [
                   end_effector_quaternion[1],
                   end_effector_quaternion[2],
                   end_effector_quaternion[3],
                   end_effector_quaternion[0]
                ]
                print(f"当前移到可乐正上方末端步骤3位置: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                
                
                await asyncio.sleep(0.5)
                
                if result == RobotErrorType.RobotError_SUCC and task_idx <= 1:
                    print("[Debug] aubo_robot reached target position, attempting to grasp object...")  # 抓取对象
                    
                    print("[步骤4] 抓握...")
                    await send_clean()
                    apple_area = grasp_objects[grasp_obj_index][6]
                    await adaptive_close_apple(apple_area)
                    
                     # 获取正向运动学结果
                    fk_result = aubo_robot.forward_kin(current_joint_angles)
                    if fk_result is None:
                           raise Exception("正向运动学计算失败")
            
                # 提取旋转矩阵和平移向量
                    end_effector_position = fk_result['pos']

                # 四元素，返回的是w,x,y,z，要转换成x,y,z,w
                    end_effector_quaternion = fk_result['ori']
                    end_effector_quaternion = [
                        end_effector_quaternion[1],
                        end_effector_quaternion[2],
                        end_effector_quaternion[3],
                        end_effector_quaternion[0]
                    ]
                    print(f"当前移到可乐正上方末端步骤2位置: {np.round(end_effector_position, 2)}, 姿态: {np.round(end_effector_quaternion, 2)}")
                    
                    
                    await asyncio.sleep(0.5)
                #     if take_obj == "sj" or take_obj == "baoguo2" or take_obj == "pcb":
                #         aubo_robot.set_joint_maxvelc(  (0.2,0.2,0.2,0.2,0.2,0.2) )
                #         aubo_robot.set_end_max_line_velc(0.15)

                    #return
                    # 移动机械臂到高悬停位置（+具体物品的Z）
                    # 步骤5：提起到正上方
                    print("[步骤5] 提起...")
                    #target_pos = (target_pos[0], target_pos[1], 0.55 )
                    print("[Debug] Moving to high hover position.")
                    #aubo_robot.move_to_target_in_cartesian(target_pos, rpy_xyz)
                    #await asyncio.sleep(0.5)

		    # 步骤6：回高悬停位（过渡点）
                    print("[步骤6] 回高悬停位...")
                    retract_pos[1]=retract_pos[1]+0.20
                    retract_pos[2]=retract_pos[2]+0.05
                    aubo_robot.move_to_target_in_cartesian(retract_pos.tolist(), rpy_xyz)
                    await asyncio.sleep(0.2)
                                      
                    # 步骤7：移到递可乐位置
                    '''print("[步骤7] 移到右边纸箱放置...")
                    aubo_robot.move_to_target_in_cartesian(high_hover_pos_shuiguo, high_hover_rpy_shuiguo)
                    await asyncio.sleep(0.5)'''
                    
                    # 步骤8：降低高度在纸箱放置
                    target_pos = (high_hover_pos_shuiguo[0], high_hover_pos_shuiguo[1], 0.33 )
                    target_high_pos = (high_hover_pos_shuiguo[0], high_hover_pos_shuiguo[1], 0.47 )
                    if(num3>=1):
                        
                        target_pos = (high_hover_pos_shuiguo[0]-0.08*(num3//2),high_hover_pos_shuiguo[1]+0.12*(num3%2), 0.33 )
                        target_high_pos = (high_hover_pos_shuiguo[0]-0.08*(num3//2),high_hover_pos_shuiguo[1]+0.12*(num3%2), 0.47 )
                    print('[步骤7] 移动到放置高位')
                    aubo_robot.move_to_target_in_cartesian(target_high_pos, high_hover_rpy_shuiguo)
                    await asyncio.sleep(1.0)
                    print('[步骤8] 在放置高位下降放置')
                    aubo_robot.move_to_target_in_cartesian(target_pos, high_hover_rpy_shuiguo)
                    
                    # 步骤9：等待观众取走（2s）
                    print("[步骤9] 等待观众取走可乐...")
                    await asyncio.sleep(1.5)
                  
                    # 步骤10：松手
                    print("[步骤10] 松手...")
                    await send_clean()
                    await send_predefined_action(1)
                    await asyncio.sleep(1)
                    
                    aubo_robot.move_to_target_in_cartesian([high_hover_pos_shuiguo[0], high_hover_pos_shuiguo[1], 0.50], high_hover_rpy_shuiguo)
                    await asyncio.sleep(0.3)


                #     await send_clean()
                #     await send_predefined_action(18)
                #     await asyncio.sleep(1)

                #     if take_obj == "sj"or take_obj == "baoguo2" or take_obj == "pcb":
                #         aubo_robot.set_joint_maxvelc(  (limitspeed, limitspeed, limitspeed, limitspeed, limitspeed, limitspeed) )
                #         aubo_robot.set_end_max_line_velc(limitspeed)

                #     # 调整姿态角度          
                #     if abs(angle) > 45 and take_obj != "scq":
                #         aubo_robot.move_to_target_in_cartesian(target_pos, high_hover_rpy)

                    
                #     if target_pos[0] * place_position[task_idx][0][0] < 0 :  # and target_pos[1] > (high_hover_pos[1] - 0.05)
                #         result = aubo_robot.move_to_target_in_cartesian( [high_hover_pos[0],high_hover_pos[1]-0.1,high_hover_pos[2]], rpy_mapping[take_obj])               
                #     # 移动机械臂到放置位置
                #     aubo_robot.move_to_target_in_cartesian( position_mapping[take_obj], rpy_mapping[take_obj] )
                #     # 松开对象
                #     print("[Debug] Releasing object.")
                #     await send_clean()
                #     await send_predefined_action(action_release[grasp_idx] )
                #     await asyncio.sleep(0.8)                    
                #     # z轴上升0.05
                #     print("[Debug] moveing up.")
                #     aubo_robot.move_to_target_in_cartesian( [position_mapping[take_obj][0], position_mapping[take_obj][1], position_mapping[take_obj][2]+0.05], rpy_mapping[take_obj] )

                        

                    # 将目标对象添加到已处理对象列表中
                    processed_objects.append(take_obj)
                    num3 += 1  # 累计已抓取数量（用于放置偏移判断）

                    # ── 重置扫描状态，准备抓下一个水果 ──
                    grasp_objects = []   # 清空坐标库，重新扫描
                    num5 = 0             # 重置稳定帧计数
                    num6 = 0             # 重置预接近标志

                    # 移回高悬停位置，开始扫描下一个
                    # 步骤11：回高悬停位
                    print("[步骤11] 回高悬停初始位...")
                    print("[Debug] Returning to high hover position.")
                    aubo_robot.move_to_target_in_cartesian(high_hover_pos, high_hover_rpy)
                    print("[步骤11] 回到张手初始状态...")
                    await asyncio.sleep(0.5)
                    await send_clean()
                    await send_predefined_action(9)

                #     if num3 < num2 :
                #         # 找到 take_obj 在 grasp_objects 中的位置
                #         grasp_obj_index = next((index for index, obj in enumerate(grasp_objects) if obj[0] == take_order1[num3]), None)
                #         if grasp_obj_index is None:
                #             aubo_robot.move_to_target_in_cartesian(high_hover_pos, high_hover_rpy)
                #         else:
                #             pos = ( grasp_objects[grasp_obj_index][1] , grasp_objects[grasp_obj_index][2] + 0.12 ,  0.4 ) 
                            
                #             if grasp_objects[grasp_obj_index][1] * position_mapping[take_obj][0] < 0 :
                #                 result = aubo_robot.move_to_target_in_cartesian( [high_hover_pos[0],high_hover_pos[1]-0.1,high_hover_pos[2]], high_hover_rpy)

                #             aubo_robot.move_to_target_in_cartesian(pos, high_hover_rpy)
                #     else:
                #         aubo_robot.move_to_target_in_cartesian(high_hover_pos, high_hover_rpy)

                    


                                
                    
        # # 输出图像已经抓取的特体名字在图像上
        text = "Processed: " + ", ".join(processed_objects)
        cv2.putText(annotated_frame, text, (10,90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 1)
        _update_display(annotated_frame)

    # 统计耗时
    elapsed = time.time() - start_time
    m, s    = divmod(elapsed, 60)
    print(f"Total time taken: {int(m)} minutes {s:.2f} seconds")

    # 所有水果抓完，关闭录制（新增）
    with _video_writer_lock:
        if _video_writer is not None:
            _video_writer.release()
            _video_writer = None
            print("[录制] 全程视频已保存")

    cv2.destroyAllWindows()  


# ══════════════════════════════════════════════════
#  程序入口
# ══════════════════════════════════════════════════

if __name__ == '__main__':

    clear_screen()

    # 加载YOLO模型
    model_path = "train/weights/"
    model      = YOLO(model_path + "best.pt")
    model_size = 640
    with open(model_path + "../args.yaml", "r") as f:
        args       = yaml.safe_load(f)
        model_size = args.get("imgsz", 640)

    # 初始化RealSense相机
    context = rs.context()
    if len(context.devices) == 0:
        print("No device connected")
        sys.exit()

    devices         = context.query_devices()
    selected_device = devices[0]
    print("连接的设备数量:", len(devices))
    for i, device in enumerate(devices):
        name = device.get_info(rs.camera_info.name)
        print(f"设备 {i}: {name}")
        if name == "Intel RealSense L515":
            selected_device = devices[i]

    print(f"连接设备: {selected_device.get_info(rs.camera_info.name)}")

    pipeline = rs.pipeline(context)
    config   = rs.config()
    config.enable_device(selected_device.get_info(rs.camera_info.serial_number))

    if selected_device.get_info(rs.camera_info.name) == "Intel RealSense L515":
        config.enable_stream(rs.stream.depth, 640,         480,          rs.format.z16,  30)
        config.enable_stream(rs.stream.color, image_width, image_height, rs.format.bgr8, 30)
    else:
        config.enable_stream(rs.stream.depth, image_width, image_height, rs.format.z16,  30)
        config.enable_stream(rs.stream.color, image_width, image_height, rs.format.bgr8, 30)

    profile      = pipeline.start(config)
    align        = rs.align(rs.stream.color)
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale  = depth_sensor.get_depth_scale()
    print(f"Depth Scale is: {depth_scale}")

    if selected_device.get_info(rs.camera_info.name) == "Intel RealSense L515":
        depth_sensor.set_option(rs.option.visual_preset, 5)   # 短距模式

    intrinsics = profile.get_stream(
        rs.stream.color).as_video_stream_profile().get_intrinsics()
    color_intrinsics = {
        "fx": intrinsics.fx, "fy": intrinsics.fy,
        "cx": intrinsics.ppx, "cy": intrinsics.ppy,
        "height": intrinsics.height, "width": intrinsics.width, "scale": 1.0
    }
    print("color 内参:", intrinsics.fx,intrinsics.fy,intrinsics.ppx,intrinsics.ppy)

    robot = Auboi5Robot()

    try:
        Auboi5Robot.initialize()
        handle = robot.create_context()
        if handle < 0:
            raise Exception("上下文句柄创建失败")
        print(f"上下文句柄创建成功: {handle}")

        # IP已确认，端口内部固定30004
        ip   = '192.168.1.100'
        port = 8899
        result = robot.connect(ip, port)
        if result != RobotErrorType.RobotError_SUCC:
            raise Exception(f"连接机械臂失败")
        print(f"成功连接到机械臂")

        result = robot.robot_startup()
        if result != RobotErrorType.RobotError_SUCC:
            raise Exception("机械臂启动失败")
        print("机械臂启动成功")

        robot.set_tool_power_type(RobotToolPowerType.OUT_24V)
        print("[Debug] robot.set_tool_power_type")
        robot.set_joint_maxvelc((limitspeed,)*6)
        print("[Debug] robot.set_joint_maxvelc")
        robot.set_end_max_line_velc(limitspeed)
        print("[Debug] robot.set_end_max_line_velc")

        result = robot.move_to_target_in_cartesian(high_hover_pos, high_hover_rpy)
        print("[Debug] robot.move_to_target_in_cartesian")
        print("[Debug] init move result:{result}")
        


        if result == RobotErrorType.RobotError_SUCC:
            print("[Debug] Starting asyncio event loop for grasp_and_place_object.")

            # 启动Flask推流服务器
            flask_thread = threading.Thread(target=_start_flask, daemon=True)
            flask_thread.start()

            # 启动抓取画面读帧线程（机械臂运动时也持续推流）
            cam_reader_thread = threading.Thread(
                target=_grasp_cam_reader,
                args=(pipeline, align),
                daemon=True)
            cam_reader_thread.start()

            print("=" * 50)
            print("[推流] 浏览器打开以下地址查看实时画面：")
            print("  扫描识别：http://localhost:5000")
            print("  抓取过程：http://localhost:5000/grasp")
            print("=" * 50)

            # 启动主抓取流程
            asyncio.run(grasp_and_place_object_task10(
                model, color_intrinsics, pipeline, align,
                depth_scale, model_size, robot
            ))

    except Exception as e:
        print(f"发生异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        _display_stop = True
        # 确保录制被关闭（新增）
        with _video_writer_lock:
            if _video_writer is not None:
                _video_writer.release()
                _video_writer = None
                print("[录制] 已强制保存")
        if robot.connected:
            print("机械臂关闭")
            robot.disconnect()
        Auboi5Robot.uninitialize()
        pipeline.stop()
        print("机械臂已关闭并断开连接")

