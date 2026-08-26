#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
vision_hand_ctrl.py – 基于 MediaPipe 手部关键点的灵巧手视觉控制程序
================================================================================
"""

# =============================================================================
# 1. 模块导入（每个函数/类的功能说明）
# =============================================================================

import cv2
# cv2.VideoCapture(0) —— 打开系统默认摄像头（索引0），返回 VideoCapture 对象。
#   - 参数：设备索引或视频文件路径。
#   - 返回值：VideoCapture 实例，用于后续 read() 获取帧。
# cv2.flip(frame, 1) —— 水平翻转图像（镜像）。
#   - 参数1：输入图像；参数2：1 表示绕Y轴翻转（水平镜像）。
#   - 返回值：翻转后的图像。
# cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) —— 颜色空间转换。
#   - 参数：输入BGR图像，转换码。
#   - 返回值：转换后的RGB图像（MediaPipe 要求）。
# cv2.imshow('win', frame) —— 在指定窗口显示图像。
# cv2.waitKey(1) —— 等待键盘事件，参数为等待毫秒数（1表示非阻塞）。
#   - 返回值：按键的ASCII码，若超时返回 -1。
# cv2.rectangle() —— 绘制矩形；cv2.putText() —— 绘制文字；
# cv2.line() —— 绘制线段；cv2.circle() —— 绘制圆点。
# cv2.FONT_HERSHEY_SIMPLEX —— OpenCV 内置字体。

import mediapipe as mp
# MediaPipe 主库。mp.Image 用于封装图像数据。

from mediapipe import tasks
# tasks.BaseOptions(model_asset_path=路径) —— 指定加载的模型文件路径。

from mediapipe.tasks.python import vision
# vision.HandLandmarkerOptions —— 配置检测器参数（运行模式、置信度等）。
# vision.HandLandmarker.create_from_options(options) —— 根据选项创建检测器实例。

from mediapipe.tasks.python.vision import RunningMode
# RunningMode.LIVE_STREAM —— 枚举值，表示异步实时流模式。
#   - 此模式下调用 detect_async() 立即返回，结果由回调函数接收。

import os
# os.path.dirname(__file__) —— 获取当前脚本所在的目录路径（__file__ 是当前文件路径）。
# os.path.join(dir, name) —— 拼接目录和文件名，返回完整路径（自动处理 / 或 \）。
# os.path.exists(path) —— 检查路径是否存在，返回 True/False。

import numpy as np
# np.array([x, y, z]) —— 将列表转换为 NumPy 数组（向量），支持向量运算。
# np.linalg.norm(vector) —— 计算向量的欧几里得范数（即长度/模）。
#   - 公式：sqrt(x^2 + y^2 + z^2)，用于获取骨骼长度。
# np.dot(v1, v2) —— 计算两个向量的点积（内积）。
#   - 公式：x1*x2 + y1*y2 + z1*z2，用于求夹角余弦值。
# np.clip(value, min, max) —— 将数值限幅在 [min, max] 区间。
#   - 若 value < min，返回 min；若 value > max，返回 max；否则返回原值。

import time
# time.time() —— 返回当前时间戳（浮点数，单位：秒）。
#   - 用法：获取当前时刻，用于计算时间间隔（限频）和异步检测的时间戳。

import math
# math.acos(x) —— 反余弦函数（Arc Cosine）。
#   - 参数 x 必须在 [-1.0, 1.0] 范围内。
#   - 返回值：对应的弧度值（0 ~ π）。
# math.degrees(rad) —— 将弧度转换为角度（°）。
#   - 公式：角度 = 弧度 × (180 / π)。

import struct
# struct.pack(format, v1, v2, ...) —— 将 Python 值打包为二进制字节串。
#   - format 字符串定义字节序和类型，如 "<2B7H"：
#        "<" 表示小端字节序（Little-Endian）。
#        "2B" 表示两个 unsigned char（1字节），"7H" 表示七个 unsigned short（2字节）。
#   - 返回值：打包后的 bytes 对象，用于串口发送。

import serial
# serial.Serial(port, baudrate, timeout) —— 创建串口对象。
#   - port：端口名（如 'COM3' 或 '/dev/ttyUSB0'）。
#   - baudrate：波特率（灵巧手通常为 921600）。
#   - timeout：读取超时时间（秒）。
#   - 方法：write(bytes) 发送数据，read(n) 读取 n 字节，flush() 等待发送完成，close() 关闭。

from serial.tools import list_ports
# list_ports.comports() —— 扫描系统所有可用串口，返回 List[SerialPortInfo]。
#   - 每个元素有 device（端口名）、description（描述字符串）等属性。

from aero_open_sdk.aero_hand import AeroHand, GET_POS
# AeroHand(port=port) —— 创建灵巧手对象，自动连接指定串口。
#   - 方法：set_joint_positions([angle1..angle7]) —— 发送7个舵机角度（度）。
# GET_POS —— 常量，值为 0x22，是获取位置指令的操作码。

# =============================================================================
# 2. 全局配置字典（原注释全部保留，未作任何改动）
# =============================================================================

CONFIG = {

    # ---------------------------- 摄像头 ----------------------------
    "mirror": True,
    # 作用：水平镜像画面。摄像头若放在用户对面（自拍视角），开启后画面如同照镜子，
    # 用户伸出右手，画面显示为右手，机械手跟随右手。
    # 若摄像头从背后拍摄（后置视角），设为 False。

    # ====================== 拇指外展（根部横向张开） ======================
    # 对应舵机索引 0，输出范围 0~90°

    "abd_scale": 1.2,
    # 物理意义：将“拇指 MCP 相对手掌中心的横向距离”除以“拇指自身长度”后，
    # 再乘以此系数。拇指外展的原始比例通常偏小（因为手部骨骼限制），
    # 此系数用于放大原始比例，使轻度外展也能产生可观的舵机角度。
    # 增大 → 更灵敏，小幅张开即产生大角度；减小 → 更迟钝。

    "abd_offset": 0.0,
    # 物理意义：在最终外展角度上直接叠加的偏移量（单位：度）。
    # 用于机械零点校正。若舵机在拇指完全并拢时仍显示正角度，设负值抵消。
    # 建议范围：-20 ~ 20 度。

    "abd_reverse": True,
    # 物理意义：控制外展方向的逻辑。
    # True  → 拇指张开（远离食指）时，角度值减小；并拢时角度值增大。
    # False → 张开时角度值增大，并拢时减小。
    # 当摄像头镜像导致左右手互换时，通过此开关反转映射曲线。

    "thumb_abd_gain": 2.2,
    # 物理意义：外展比例（0~1）映射到角度时的总增益。
    # 最终角度 = 外展比例 × 90° × 此增益。
    # 人体外展最大幅度对应视觉比例可能只有 0.4~0.6，通过增益将其拉伸到接近 90°。

    "abd_ratio_offset": 0.0,
    # 物理意义：从归一化横向距离中减去的底噪偏移量。
    # 人体拇指完全并拢时，由于骨骼宽度，横向距离不为 0（存在生理死区）。
    # 此参数切除底部无效区间，避免“微张”时舵机微颤。
    # 增大 → 需要更大幅度的外展才产生角度，抑制抖动。

    "abd_ratio_gain": 1.2,
    # 物理意义：对切除底噪后的比例进行放大，将有效区间拉伸至满量程。
    # 配合 abd_ratio_offset 使用，实现“死区切除 + 有效区放大”的非线性映射。

    # ====================== 拇指屈曲（根部弯曲） ======================
    # 对应舵机索引 1，输出范围 0~55°

    "thumb_flex_gain": 5.0,
    # 物理意义：拇指屈曲角度增益。使用空间夹角法测量 CMC-MCP-IP 夹角，
    # 原始夹角范围为 0~180°，除以 180 得到 0~1 比例。
    # 此增益将比例映射到舵机行程。默认 5.0 是因为人类拇指握拳时夹角接近 150°，
    # 比例约 0.83，乘以 5.0 后达到 4.15，再乘 90° 会严重超限，但后续会被钳位。
    # 实际上，增益 > 3 时就会饱和，这里设 5.0 是为了确保小幅度弯曲也能快速达到 90°。

    # ====================== 拇指指尖（末端弯曲） ======================
    # 对应舵机索引 2，输出范围 0~90°

    "thumb_tip_gain": 2.0,
    # 物理意义：拇指 IP 关节弯曲增益。逻辑同 thumb_flex_gain，但 MCP-IP-TIP
    # 的夹角范围通常更小（人类指尖弯曲度有限），因此增益稍低。

    # ====================== 四指（食中无小） ======================
    # 对应舵机索引 3~6，输出范围 0~90°

    "finger_gain": 1.8,
    # 物理意义：四指统一增益。使用距离比法（1 - d13/(d12+d23)）测量弯曲度。
    # 人类握拳时，该比例通常可达 0.7~0.9。乘以 90° 和 1.8 后，接近或达到 90°。
    # 若手指无法完全握拳（比例不足），增大此增益。

    # ====================== 信号后处理 ======================

    "alpha": 0.3,
    # 物理意义：一阶指数平滑系数（0~1）。公式：y[k] = α·x[k] + (1-α)·y[k-1]。
    # 这是一个单极点低通滤波器，极点位于 z = 1-α = 0.7。
    # 摄像头帧率 30Hz 时，截止频率约 5Hz，能有效滤除 MediaPipe 的高频亚像素抖动。
    # 增大 α（如 0.5）→ 响应快但残留噪声；减小 α（如 0.15）→ 更平滑但有延迟。

    "dead_zone": 0.5,
    # 物理意义：死区阈值（单位：度）。当任一角度变化小于此值时，不触发串口发送。
    # 舵机机械背隙通常 0.3~0.5°，小于该阈值的指令舵机无法执行，只会发热。
    # 此参数从源头抑制极限环振荡，延长舵机寿命。

    "send_interval": 0.05,
    # 物理意义：串口发送最小间隔（秒）。限制最大发送频率为 20Hz。
    # 避免串口拥塞，同时保证舵机指令平滑。若需更流畅的动作，可降至 0.03（33Hz）。

    "verbose": True,
    # 控制台调试打印开关。True 时每 10 帧打印一次原始比例和最终角度。

    # ================== 拇指过伸抑制参数（新增） ==================
    "thumb_flex_hyperextension_z_threshold": 0.015,
    # 物理意义：拇指屈曲过伸检测的深度阈值（归一化坐标）。
    # 当 IP 点相对 MCP 点的 z 值变化超过此阈值，且夹角较大时，判定为过伸，强制伸直。
    # 该值基于 MediaPipe 的归一化深度（0~1），需根据实际手距微调。
    # 增大 → 抑制触发更不敏感；减小 → 更敏感。

    "thumb_tip_hyperextension_z_threshold": 0.015,
    # 物理意义：拇指指尖过伸检测的深度阈值，逻辑同上，针对 TIP 点相对 IP 点。

    "hyperextension_angle_threshold": 10.0,
    # 物理意义：过伸判断时的夹角阈值（度）。
    # 当原始夹角大于此值且深度变化超过阈值时，才触发抑制。
    # 避免在伸直小角度时误触发。
}

# =============================================================================
# 3. 主控制器类
# =============================================================================

class HandController:
    """
    手部识别与灵巧手控制总调度类。
    """

    def __init__(self, port=None, config=None):
        """
        构造方法：初始化配置、MediaPipe 检测器、Aero Hand 连接。

        参数：
            port (str): 串口号，如 'COM3'。None 时自动扫描。
            config (dict): 配置字典，None 时使用全局 CONFIG。
        """
        # ---------- 第1步：加载配置 ----------
        if config is None:
            config = CONFIG  # 若未传入配置，使用全局默认配置
        self.config = config  # 保存配置引用（便于外部访问）

        # 从配置字典中提取参数到实例属性（self.xxx），目的是减少后续频繁的字典查找开销
        self.mirror = config["mirror"]
        self.abd_scale = config["abd_scale"]
        self.abd_offset_deg = config["abd_offset"]
        self.abd_reverse = config["abd_reverse"]
        self.thumb_abd_gain = config["thumb_abd_gain"]
        self.thumb_flex_gain = config["thumb_flex_gain"]
        self.thumb_tip_gain = config["thumb_tip_gain"]
        self.finger_gain = config["finger_gain"]
        self.alpha = config["alpha"]
        self.dead_zone_deg = config["dead_zone"]
        self.send_interval = config["send_interval"]
        self.verbose = config["verbose"]
        self.abd_ratio_offset = config["abd_ratio_offset"]
        self.abd_ratio_gain = config["abd_ratio_gain"]

        # 过伸抑制相关参数
        self.flex_hyperext_z_thresh = config["thumb_flex_hyperextension_z_threshold"]
        self.tip_hyperext_z_thresh = config["thumb_tip_hyperextension_z_threshold"]
        self.hyperext_angle_thresh = config["hyperextension_angle_threshold"]

        # ---------- 第2步：初始化运行时状态变量 ----------
        # latest_result: MediaPipe 异步回调线程会写入最新检测结果，主线程读取
        self.latest_result = None
        # smooth_angles_deg: 保存上一帧滤波后的7个角度（度），用于指数平滑递推
        self.smooth_angles_deg = None
        # last_send_time: 上次串口发送的时间戳（秒），用于限频控制（send_interval）
        self.last_send_time = 0.0
        # frame_count: 帧计数器，每处理一帧加1，用于控制调试打印频率（每10帧打印一次）
        self.frame_count = 0

        # ---------- 第3步：初始化 MediaPipe 检测器 ----------
        print("正在初始化 MediaPipe ...")
        model_name = 'hand_landmarker.task'  # 模型文件名

        # 获取当前脚本所在的绝对目录路径
        current_dir = os.path.dirname(__file__)
        # 向上跳三级目录，定位到项目根目录（假设项目结构：根目录/子目录1/子目录2/当前脚本）
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

        # os.path.join() —— 拼接路径；os.path.exists() —— 检查路径是否存在
        if os.path.exists(os.path.join(current_dir, model_name)):
            model_path = os.path.join(current_dir, model_name)  # 优先从当前目录加载
        elif os.path.exists(os.path.join(root_dir, model_name)):
            model_path = os.path.join(root_dir, model_name)    # 其次从根目录加载
        else:
            # 如果找不到模型文件，抛出异常终止程序
            raise FileNotFoundError(f"找不到模型文件 {model_name}")

        # 定义回调函数（由 MediaPipe 后台线程在推理完成后调用）
        def save_result(result, _output_image, _timestamp_ms):
            # result: HandLandmarkerResult 对象，包含手部关键点等
            # _output_image, _timestamp_ms: 参数固定，但此处用不到，加下划线避免 lint 警告
            self.latest_result = result  # 将结果存入实例变量，供主线程使用

        # tasks.BaseOptions —— 指定模型文件路径
        base_options = tasks.BaseOptions(model_asset_path=model_path)

        # vision.HandLandmarkerOptions —— 构造检测器配置项
        options = vision.HandLandmarkerOptions(
            base_options=base_options,                      # 基础选项（模型路径）
            running_mode=RunningMode.LIVE_STREAM,           # 异步实时流模式
            num_hands=2,                                    # 最多检测双手（取第一只用于控制）
            min_hand_detection_confidence=0.5,              # 手部检测置信度阈值
            min_tracking_confidence=0.5,                    # 跟踪置信度阈值
            result_callback=save_result                     # 绑定回调函数
        )
        # vision.HandLandmarker.create_from_options(options) —— 根据配置创建检测器实例
        self.detector = vision.HandLandmarker.create_from_options(options)
        print("MediaPipe 初始化成功！")

        # ---------- 第4步：连接 Aero Hand 灵巧手 ----------
        print("正在连接 Aero Hand ...")
        self.hand = None  # 初始化为 None，表示未连接

        if port is not None:
            # 分支1：用户指定了串口号，直接尝试连接
            try:
                # AeroHand(port=port) —— 创建灵巧手对象，内部执行串口连接
                self.hand = AeroHand(port=port)
                print(f"Aero Hand 连接成功 (指定端口 {port})")
            except Exception as e:
                # 若连接失败（如端口不存在、权限不足），捕获异常并打印，程序继续运行
                print(f"指定端口 {port} 连接失败: {e}")
        else:
            # 分支2：未指定端口，尝试自动检测
            try:
                # AeroHand() 无参构造 —— 在 Linux 下内置自动检测，遍历 /dev/tty* 并握手
                self.hand = AeroHand()
                print("Aero Hand 连接成功 (自动检测)")
            except Exception:
                # 若内置检测失败（比如在 Windows 下），进入手动串口扫描
                print("自动检测失败，开始扫描所有串口 ...")
                # 调用自定义方法 _find_aero_hand_port()，返回找到的端口名或 None
                found_port = self._find_aero_hand_port()
                if found_port:
                    try:
                        self.hand = AeroHand(port=found_port)
                        print(f"Aero Hand 连接成功 (扫描找到 {found_port})")
                    except Exception as e2:
                        print(f"连接 {found_port} 失败: {e2}")
        # 若 self.hand 仍为 None，说明所有连接尝试均失败，打印提示但不终止程序
        if self.hand is None:
            print("Aero Hand 未连接，仅显示跟踪（不发送指令）。")

    # ------------------------------------------------------------------------
    # 自定义方法：手动扫描串口（握手协议识别）
    # ------------------------------------------------------------------------
    def _find_aero_hand_port(self):
        """
        扫描所有可用串口，发送 GET_POS（0x22）协议帧，若收到预期应答则确认设备。

        返回值：str —— 找到的端口名；若未找到返回 None。
        """
        # list_ports.comports() —— 返回系统所有可用串口列表
        ports = list_ports.comports()
        if not ports:
            return None

        candidates = []  # 优先候选端口（包含 ESP/JTAG/USB 关键字）
        others = []      # 其他端口
        for p in ports:
            desc = p.description  # 获取端口描述字符串（如 "USB Serial Port"）
            if "ESP" in desc or "JTAG" in desc or "USB" in desc:
                candidates.append(p.device)   # p.device 是端口名（如 'COM3'）
            else:
                others.append(p.device)

        # 先尝试候选端口，再尝试其他端口
        for port_name in candidates + others:
            try:
                # serial.Serial() —— 打开串口，设置波特率 921600，超时 0.2 秒
                ser = serial.Serial(port_name, 921600, timeout=0.2)

                # 构造 GET_POS 协议帧
                payload = [0] * 7  # 7 个负载数据，均为 0
                # struct.pack("<2B7H", ...) —— 打包为二进制
                #   "<" 小端字节序；"2B" 两个 unsigned char（操作码 0x22 和 0x00）
                #   "7H" 七个 unsigned short（payload 的 7 个 0）
                # GET_POS & 0xFF 确保取低字节（0x22）
                msg = struct.pack("<2B7H", GET_POS & 0xFF, 0x00, *payload)
                ser.write(msg)   # 发送数据
                ser.flush()      # 等待发送缓冲区清空
                resp = ser.read(16)  # 读取 16 字节应答数据

                # 判断应答：长度必须为 16 字节，且首字节必须为操作码 0x22
                if len(resp) == 16 and resp[0] == GET_POS:
                    ser.close()  # 关闭串口
                    return port_name  # 返回找到的端口
                ser.close()
            except:
                # 若打开失败或通信异常，跳过该端口继续尝试
                continue
        return None  # 未找到任何设备

    # ========================================================================
    # 核心算法1：三维空间夹角（用于拇指屈曲与指尖）
    # ========================================================================
    def _compute_angle_between_vectors(self, point_proximal, point_middle, point_distal):
        """
        计算三个空间点形成的关节夹角（度）。

        参数：
            point_proximal : numpy array (3,) —— 近端关键点坐标
            point_middle   : numpy array (3,) —— 中间关键点坐标
            point_distal   : numpy array (3,) —— 远端关键点坐标

        返回值：float —— 夹角（度），范围 0~180
        """
        # 计算两条骨骼的方向向量
        vector_forward = point_middle - point_proximal   # 骨骼1：近端 → 中间
        vector_backward = point_distal - point_middle    # 骨骼2：中间 → 远端

        # np.linalg.norm() —— 计算向量的欧几里得长度（模）
        norm_forward = np.linalg.norm(vector_forward)
        norm_backward = np.linalg.norm(vector_backward)

        # 若任一骨骼长度接近于0（关键点重叠），防止除零，直接返回0°
        if norm_forward < 1e-6 or norm_backward < 1e-6:
            return 0.0

        # np.dot() —— 计算两个向量的点积
        # 点积公式：v1·v2 = |v1| * |v2| * cos(θ)
        # 所以 cos(θ) = (v1·v2) / (|v1| * |v2|)
        cos_theta = np.dot(vector_forward, vector_backward) / (norm_forward * norm_backward)

        # np.clip() —— 将余弦值限幅到 [-1.0, 1.0]，防止浮点误差导致 acos 报错
        cos_theta = np.clip(cos_theta, -1.0, 1.0)

        # math.acos() —— 反余弦，返回弧度值（0 ~ π）
        # math.degrees() —— 将弧度转换为角度（°）
        return math.degrees(math.acos(cos_theta))

    # ========================================================================
    # 核心算法2：弯曲比例（距离比法）—— 用于四指
    # ========================================================================
    def _compute_bend_ratio_by_distance(self, point_proximal, point_middle, point_distal):
        """
        使用三点欧氏距离计算弯曲比例（0~1）。

        参数：
            point_proximal : numpy array (3,) —— 近端（指根）
            point_middle   : numpy array (3,) —— 中间（指中）
            point_distal   : numpy array (3,) —— 远端（指尖）

        返回值：float —— 弯曲比例，0=伸直，1=握拳
        """
        # np.linalg.norm(A - B) —— 计算 A、B 两点的欧氏距离
        distance_proximal_distal = np.linalg.norm(point_proximal - point_distal)  # 弦长（指根到指尖直线距离）
        distance_proximal_middle = np.linalg.norm(point_proximal - point_middle)  # 近节骨骼长度
        distance_middle_distal = np.linalg.norm(point_middle - point_distal)      # 中/远节骨骼长度之和

        denominator = distance_proximal_middle + distance_middle_distal  # 手指伸直时的理论最大弦长

        if denominator < 1e-6:  # 防止除零（骨骼长度近似为0）
            return 0.0

        # 核心归一化公式：
        #   伸直时：弦长 ≈ 分母 → 比例 = 1 - 1 = 0
        #   握拳时：弦长 ≈ 0   → 比例 = 1 - 0 = 1
        ratio = 1.0 - (distance_proximal_distal / denominator)

        # np.clip() 确保返回值在 [0, 1] 范围内（防止微小误差越界）
        return np.clip(ratio, 0.0, 1.0)

    # ========================================================================
    # 主映射函数：21个关键点 → 7个关节角度（度）
    # ========================================================================
    def landmarks_to_joint_angles(self, landmarks):
        """
        将 MediaPipe 检测到的 21 个手部关键点转换为 7 个舵机角度。

        输入：landmarks —— MediaPipe 的关键点列表，每个元素有 x, y, z 属性（归一化坐标 0~1）。
        输出：list[float] —— 7个角度（度），顺序：
              [拇指外展, 拇指屈曲, 拇指指尖, 食指, 中指, 无名指, 小指]
        """
        # ===================== 第1步：计算四指（食中无小）角度 =====================
        # MediaPipe 标准索引：食指(5,6,8)，中指(9,10,12)，无名指(13,14,16)，小指(17,18,20)
        finger_indices = [
            (5, 6, 8),
            (9, 10, 12),
            (13, 14, 16),
            (17, 18, 20)
        ]
        finger_angles_deg = []   # 存储四个手指的角度结果
        finger_ratios = []       # 存储原始比例（仅用于调试打印）

        for mcp_idx, pip_idx, tip_idx in finger_indices:
            # 从 landmarks 中提取坐标，转为 numpy 数组
            point_mcp = np.array([
                landmarks[mcp_idx].x,
                landmarks[mcp_idx].y,
                landmarks[mcp_idx].z
            ])
            point_pip = np.array([
                landmarks[pip_idx].x,
                landmarks[pip_idx].y,
                landmarks[pip_idx].z
            ])
            point_tip = np.array([
                landmarks[tip_idx].x,
                landmarks[tip_idx].y,
                landmarks[tip_idx].z
            ])

            # 调用距离比法，得到 0~1 的弯曲比例
            bend_ratio = self._compute_bend_ratio_by_distance(point_mcp, point_pip, point_tip)
            # 映射到角度：比例 × 90° × 增益，然后钳位到 0~90°
            angle_deg = bend_ratio * 90.0 * self.finger_gain
            angle_deg = np.clip(angle_deg, 0.0, 90.0)

            finger_angles_deg.append(angle_deg)
            finger_ratios.append(bend_ratio)

        # ===================== 第2步：计算拇指屈曲与指尖（空间夹角法） =====================
        # MediaPipe 拇指索引：1=CMC(腕掌), 2=MCP(掌指), 3=IP(指间), 4=TIP(指尖)
        point_cmc = np.array([
            landmarks[1].x, landmarks[1].y, landmarks[1].z
        ])
        point_mcp = np.array([
            landmarks[2].x, landmarks[2].y, landmarks[2].z
        ])
        point_ip = np.array([
            landmarks[3].x, landmarks[3].y, landmarks[3].z
        ])
        point_tip = np.array([
            landmarks[4].x, landmarks[4].y, landmarks[4].z
        ])

        # 2.1 拇指屈曲（根部弯曲）：CMC-MCP-IP 三点夹角
        flex_angle_raw_deg = self._compute_angle_between_vectors(point_cmc, point_mcp, point_ip)
        flex_ratio = flex_angle_raw_deg / 180.0   # 将 0~180° 归一化为 0~1
        flex_angle_deg = flex_ratio * 90.0 * self.thumb_flex_gain  # 映射到舵机行程
        flex_angle_deg = np.clip(flex_angle_deg, 0.0, 55.0)  # 硬件限位 55°

        # ---- 过伸抑制（屈曲） ----
        # 计算 IP 相对 MCP 在 Z 轴（深度）的变化量
        z_depth_change_flex = point_ip[2] - point_mcp[2]
        # 若深度变化超过阈值 且 原始夹角大于阈值，判定为过伸，强制置 0°
        if (z_depth_change_flex > self.flex_hyperext_z_thresh and
            flex_angle_raw_deg > self.hyperext_angle_thresh):
            flex_angle_deg = 0.0

        # 2.2 拇指指尖（末端弯曲）：MCP-IP-TIP 三点夹角
        tip_angle_raw_deg = self._compute_angle_between_vectors(point_mcp, point_ip, point_tip)
        tip_ratio = tip_angle_raw_deg / 180.0
        tip_angle_deg = tip_ratio * 90.0 * self.thumb_tip_gain
        tip_angle_deg = np.clip(tip_angle_deg, 0.0, 90.0)

        # ---- 过伸抑制（指尖） ----
        z_depth_change_tip = point_tip[2] - point_ip[2]
        if (z_depth_change_tip > self.tip_hyperext_z_thresh and
            tip_angle_raw_deg > self.hyperext_angle_thresh):
            tip_angle_deg = 0.0

        # ===================== 第3步：计算拇指外展（归一化横向距离） =====================
        # 动态标尺：拇指自身长度（MCP 到 TIP），用于消除摄像头远近缩放影响
        thumb_length = np.linalg.norm(point_mcp - point_tip)
        if thumb_length < 1e-6:   # 防除零
            thumb_length = 0.01

        # 动态手掌中心：取手腕 (0) 与中指 MCP (9) 的中点（忽略 Z 轴）
        wrist = np.array([landmarks[0].x, landmarks[0].y, 0])
        middle_mcp = np.array([landmarks[9].x, landmarks[9].y, 0])
        palm_center = (wrist + middle_mcp) / 2.0

        # 横向偏移：拇指 MCP 到手掌中心在 X 方向的距离（取绝对值）
        lateral_distance = abs(point_mcp[0] - palm_center[0])

        # 第1步归一化：横向距离 / 拇指长度 × 缩放系数
        abd_ratio_raw = (lateral_distance / thumb_length) * self.abd_scale
        abd_ratio_raw = np.clip(abd_ratio_raw, 0.0, 1.0)

        # 第2步非线性拉伸：切除生理死区（offset）+ 放大有效区（gain）
        abd_ratio = (abd_ratio_raw - self.abd_ratio_offset) * self.abd_ratio_gain
        abd_ratio = np.clip(abd_ratio, 0.0, 1.0)

        # 方向反转（用于摄像头镜像补偿）
        if self.abd_reverse:
            abd_ratio = 1.0 - abd_ratio

        # 最终映射到角度：比例 × 90° × 增益 + 偏移
        abd_angle_deg = abd_ratio * 90.0 * self.thumb_abd_gain + self.abd_offset_deg
        abd_angle_deg = np.clip(abd_angle_deg, 0.0, 90.0)

        # ===================== 第4步：组装最终输出列表 =====================
        angles_deg = [abd_angle_deg, flex_angle_deg, tip_angle_deg] + finger_angles_deg

        # 调试打印（每10帧打印一次）
        if self.verbose and (self.frame_count % 10 == 0):
            print(f"[帧 {self.frame_count}] 拇指外展: 横向距离={lateral_distance:.3f} → "
                  f"比例={abd_ratio:.2f} → 角度={abd_angle_deg:.1f}°")
            print(f"  屈曲: 原始夹角={flex_angle_raw_deg:.1f}° → {flex_angle_deg:.1f}°, "
                  f"指尖: 原始夹角={tip_angle_raw_deg:.1f}° → {tip_angle_deg:.1f}°")
            print(f"  四指比例: {[round(r, 2) for r in finger_ratios]}")
            print(f"  输出角度: {[round(a, 1) for a in angles_deg]}")
        self.frame_count += 1  # 帧计数器递增

        return angles_deg

    # ========================================================================
    # 信号后处理：指数平滑 + 死区判决
    # ========================================================================
    def smooth_and_apply_deadzone(self, raw_angles_deg):
        """
        对原始角度进行一阶低通滤波，并判断变化是否超过死区。

        参数：
            raw_angles_deg (list[float]) —— 当前帧原始 7 个角度（度）

        返回值：
            smoothed_angles (list[float]) —— 滤波后的角度
            changed (bool) —— 是否有任一角度变化超过 dead_zone
        """
        if self.smooth_angles_deg is None:
            # 首帧：无历史数据，直接保存当前值作为初始滤波值
            self.smooth_angles_deg = raw_angles_deg[:]  # [:] 创建副本，避免引用
            return raw_angles_deg, True   # 首帧默认发送

        smoothed = []  # 存储滤波后的角度
        for i in range(len(raw_angles_deg)):
            # 一阶指数平滑公式：y[k] = α·x[k] + (1-α)·y[k-1]
            val = self.alpha * raw_angles_deg[i] + (1.0 - self.alpha) * self.smooth_angles_deg[i]
            smoothed.append(val)

        # 计算每个角度相对于上一帧滤波值的变化量（绝对值）
        differences = [
            abs(smoothed[i] - self.smooth_angles_deg[i])
            for i in range(len(smoothed))
        ]
        # any() —— 判断可迭代对象中是否有任何一个元素为 True
        # 只要有一个角度的变化超过死区阈值，就置 changed = True
        changed = any(diff > self.dead_zone_deg for diff in differences)

        # 更新历史滤波值
        self.smooth_angles_deg = smoothed[:]
        return smoothed, changed

    # ========================================================================
    # 辅助函数：绘制文字（带背景）
    # ========================================================================
    def _put_text_with_bg(self, img, text, pos, font_scale, color,
                          bg_color=(0, 0, 0), thickness=1, padding=2):
        """
        在图像上绘制带黑色背景的文字，提高可读性。

        参数：
            img —— 图像（会被修改）
            text —— 要绘制的字符串
            pos —— 左上角坐标 (x, y)
            font_scale —— 字体缩放比例
            color —— 文字颜色 (B, G, R)
            bg_color —— 背景颜色，默认黑色
            thickness —— 线条粗细
            padding —— 背景内边距
        """
        font = cv2.FONT_HERSHEY_SIMPLEX  # OpenCV 内置字体
        # cv2.getTextSize() —— 获取文字占据的宽度和高度
        #   参数：text, font, font_scale, thickness
        #   返回值：(width, height), baseline
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        x, y = pos

        # cv2.rectangle() —— 绘制矩形填充背景
        #   参数：img, 左上角坐标, 右下角坐标, 颜色, thickness=-1（填充）
        cv2.rectangle(img,
                      (x - padding, y - text_h - padding),                     # 左上角（留出 padding）
                      (x + text_w + padding, y + baseline + padding),          # 右下角
                      bg_color, -1)                                            # -1 表示填充

        # cv2.putText() —— 在背景上绘制文字
        #   参数：img, text, 左下角坐标, font, font_scale, color, thickness, 线型
        cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

    # ========================================================================
    # 辅助函数：绘制手部骨架
    # ========================================================================
    def _draw_hand_skeleton(self, image, landmarks):
        """
        绘制手部 21 个关键点和连接线（骨架）。

        参数：
            image —— 图像（会被修改）
            landmarks —— MediaPipe 检测到的关键点列表
        """
        h, w, _ = image.shape  # 获取图像高度和宽度
        # MediaPipe 标准连接拓扑（关键点索引对）
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # 拇指
            (0, 5), (5, 6), (6, 7), (7, 8),  # 食指
            (0, 9), (9, 10), (10, 11), (11, 12),  # 中指
            (0, 13), (13, 14), (14, 15), (15, 16),  # 无名指
            (0, 17), (17, 18), (18, 19), (19, 20),  # 小指
            (5, 9), (9, 13), (13, 17)  # 手掌横弓
        ]
        for start, end in connections:
            # 将归一化坐标 (0~1) 转换为像素坐标
            pt1 = (int(landmarks[start].x * w), int(landmarks[start].y * h))
            pt2 = (int(landmarks[end].x * w), int(landmarks[end].y * h))
            # cv2.line() —— 绘制线段，颜色绿色 (0,255,0)，粗细 2
            cv2.line(image, pt1, pt2, (0, 255, 0), 2)

        # 绘制每个关键点为红色圆点
        for lm in landmarks:
            cx = int(lm.x * w)
            cy = int(lm.y * h)
            # cv2.circle() —— 绘制圆，半径5，红色 (0,0,255)，-1 表示填充
            cv2.circle(image, (cx, cy), 5, (0, 0, 255), -1)

    # ========================================================================
    # 主循环
    # ========================================================================
    def run(self):
        """
        程序主循环：摄像头采集 → 异步检测 → 计算角度 → 平滑滤波 → 串口发送。
        按 'q' 键退出。
        """
        # cv2.VideoCapture(0) —— 打开默认摄像头（索引0）
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():  # isOpened() 检查摄像头是否成功打开
            print("无法打开摄像头，请检查连接。")
            return

        print("按 'q' 键退出程序。")

        while True:
            # cap.read() —— 从摄像头读取一帧
            #   返回值：ret (bool) 是否成功，frame (ndarray) 图像数据
            ret, frame = cap.read()
            if not ret:
                break  # 读取失败则退出循环

            # 若配置启用了镜像，执行水平翻转
            if self.mirror:
                # cv2.flip(frame, 1) —— 1 表示绕 Y 轴翻转（水平镜像）
                frame = cv2.flip(frame, 1)

            # MediaPipe 要求输入为 RGB 格式，而 OpenCV 默认是 BGR
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # mp.Image —— 构造 MediaPipe 图像对象
            #   image_format=mp.ImageFormat.SRGB 指定为 RGB 格式
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # self.detector.detect_async() —— 发起异步检测（非阻塞）
            #   参数1：图像对象；参数2：时间戳（毫秒），用于跟踪帧
            #   该方法立即返回，推理在后台线程进行，完成后调用 save_result 回调
            self.detector.detect_async(mp_image, int(time.time() * 1000))

            # 检查是否已收到检测结果（latest_result 由回调线程写入）
            if self.latest_result and self.latest_result.hand_landmarks:
                # 取第一只手（索引0）的关键点列表
                hand_landmarks = self.latest_result.hand_landmarks[0]

                # 调用主映射函数，得到 7 个原始角度（度）
                raw_angles = self.landmarks_to_joint_angles(hand_landmarks)

                # 调用后处理：指数平滑 + 死区判决
                #   smoothed_angles: 滤波后的角度
                #   changed: 是否有角度变化超过死区
                smoothed_angles, changed = self.smooth_and_apply_deadzone(raw_angles)

                # 若灵巧手已连接，且 (变化超过死区 且 距上次发送已超过间隔)
                if self.hand is not None:
                    now = time.time()  # 当前时间戳（秒）
                    if (now - self.last_send_time >= self.send_interval) and changed:
                        try:
                            # AeroHand.set_joint_positions() —— 发送7个角度到灵巧手
                            self.hand.set_joint_positions(smoothed_angles)
                            self.last_send_time = now  # 更新上次发送时间
                        except Exception as e:
                            print(f"[发送错误] {e}")

                # ---- 可视化绘制 ----
                # 绘制手部骨架
                self._draw_hand_skeleton(frame, hand_landmarks)
                # 在画面左上角显示角度信息
                self._put_text_with_bg(
                    frame,
                    f"Thumb: {smoothed_angles[0]:.1f}°(abd) {smoothed_angles[1]:.1f}°(flex) {smoothed_angles[2]:.1f}°(tip)",
                    (10, 30), 0.5, (0, 255, 255)
                )
                self._put_text_with_bg(
                    frame,
                    f"Fingers: {smoothed_angles[3]:.1f} {smoothed_angles[4]:.1f} {smoothed_angles[5]:.1f} {smoothed_angles[6]:.1f}",
                    (10, 55), 0.5, (255, 255, 255)
                )
                # 显示连接状态（Connected / Disconnected）
                self._put_text_with_bg(
                    frame,
                    "Connected" if self.hand else "Disconnected",
                    (10, 80), 0.5,
                    (0, 255, 0) if self.hand else (0, 0, 255)
                )
            else:
                # 未检测到手部时，在画面显示提示
                self._put_text_with_bg(frame, "No hand detected", (10, 30), 0.7, (0, 0, 255))

            # cv2.imshow() —— 在窗口中显示图像
            cv2.imshow('Hand Control - Aero Hand', frame)

            # cv2.waitKey(1) —— 等待1ms键盘事件，返回按键ASCII码
            #   若按下 'q' 键（ASCII 113），则跳出循环
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ---------- 释放资源 ----------
        cap.release()         # 释放摄像头
        cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
        self.detector.close()    # 关闭 MediaPipe 检测器（释放模型资源）
        if self.hand:
            self.hand.close()    # 关闭串口连接
        print("程序退出。")


# =============================================================================
# 4. 主程序入口
# =============================================================================
if __name__ == "__main__":
    # 创建控制器实例，port=None 表示自动扫描串口，config=CONFIG 使用默认配置
    controller = HandController(port=None, config=CONFIG)
    controller.run()  # 启动主循环