# -*- coding: utf-8 -*-
"""
calibrate_hand_eye.py —— 手眼标定工具（眼在手上，现场重标定）

参考：lib/grasp/Hand_eye_calibration_optimized.py（完整标定程序）。

用法：
  1. 把 8x5 棋盘格（方格 26mm）固定在机械臂工作空间外的固定位置；
  2. L515 固定在机械臂末端，末端在 20~25 个位姿下拍摄棋盘格；
     - 位置分散（前后左右上下），姿态 RX/RY/RZ 各 ±30° 内变化；
     - 每拍一张，记录机械臂当前末端位姿（工具：GUI 或机械臂 API getToolPose）；
     - 图像存 eye_in_hand/images/，位姿存 pose_vectors.npy；
  3. 运行本程序：自动检测角点 → 4 种手眼标定算法 → 选重投影误差最低者。

输出：打印可直接复制到 vision/hand_eye.py 的 R_cam2gripper / t_cam2gripper。

依赖：pip install opencv-python numpy scipy
"""

from __future__ import annotations
import os
import sys

# ---- 路径引导 ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import glob
import argparse

import cv2
import numpy as np

# 默认棋盘格参数（与 grasp 标定程序一致）
DEFAULT_PATTERN = (8, 5)
DEFAULT_SQUARE = 0.026  # 米


def detect_corners(img, pattern_size):
    """检测棋盘格角点（亚像素精化）。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, pattern_size)
    if not ret:
        return None
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return corners


def main():
    ap = argparse.ArgumentParser(description="手眼标定（眼在手上）")
    ap.add_argument("--images", default="eye_in_hand/images",
                    help="棋盘格图像目录（rgb_*.jpg）")
    ap.add_argument("--poses", default="eye_in_hand/pose_vectors.npy",
                    help="末端位姿数据（.npy，形状 Nx6 [x,y,z,rx,ry,rz]）")
    ap.add_argument("--pattern", default="8x5", help="棋盘格内角点数（宽x高）")
    ap.add_argument("--square", type=float, default=DEFAULT_SQUARE, help="方格边长（米）")
    args = ap.parse_args()

    pw, ph = (int(x) for x in args.pattern.lower().split("x"))
    pattern = (pw, ph)
    square = args.square

    images = sorted(glob.glob(os.path.join(args.images, "*.jpg")))
    if not images:
        print(f"❌ 未找到图像: {args.images}/rgb_*.jpg")
        return
    if not os.path.exists(args.poses):
        print(f"❌ 未找到位姿数据: {args.poses}")
        return
    poses = np.load(args.poses)
    print(f"图像 {len(images)} 张，位姿 {len(poses)} 组")

    if len(images) != len(poses):
        print("⚠️ 图像与位姿数量不匹配，取较小值继续")

    # L515 内参（可改为实际标定值）
    K = np.array([[901.776, 0, 643.152],
                  [0, 902.146, 361.902],
                  [0, 0, 1]], dtype=np.float64)
    dist = np.array([0.1739, -0.5177, -0.00136, 0.000357, 0.0471], dtype=np.float64)

    objp = np.zeros((pw * ph, 3), np.float32)
    objp[:, :2] = np.mgrid[0:pw, 0:ph].T.reshape(-1, 2) * square

    R_ends, t_ends, R_boards, t_boards = [], [], [], []
    n = min(len(images), len(poses))
    for i in range(n):
        img = cv2.imread(images[i])
        if img is None:
            continue
        corners = detect_corners(img, pattern)
        if corners is None:
            print(f"  跳过 {os.path.basename(images[i])}（未检测到角点）")
            continue
        # 标定板在相机系
        ret, rvec, tvec = cv2.solvePnP(objp, corners, K, dist)
        R_board, _ = cv2.Rodrigues(rvec)
        # 末端在基座系
        p = poses[i]
        R_end = _rpy2R(p[3:6])
        R_ends.append(R_end)
        t_ends.append(p[:3].reshape(3, 1))
        R_boards.append(R_board)
        t_boards.append(tvec)

    if len(R_ends) < 5:
        print("❌ 有效图像太少（<5），请重新采集")
        return
    print(f"有效数据 {len(R_ends)} 组，开始标定...")

    methods = [cv2.CALIB_HAND_EYE_TSAI, cv2.CALIB_HAND_EYE_PARK,
               cv2.CALIB_HAND_EYE_HORAUD, cv2.CALIB_HAND_EYE_ANDREFF]
    names = ["TSAI", "PARK", "HORAUD", "ANDREFF"]
    best = None
    for name, m in zip(names, methods):
        try:
            R_c2e, t_c2e = cv2.calibrateHandEye(
                np.array(R_ends), np.array(t_ends),
                np.array(R_boards), np.array(t_boards), method=m)
            err = _reprojection_error(R_c2e, t_c2e, objp, R_boards, t_boards,
                                      R_ends, t_ends, K, dist)
            print(f"{name}: 重投影误差={err:.4f}px, |t|={np.linalg.norm(t_c2e):.4f}m")
            if best is None or err < best[0]:
                best = (err, name, R_c2e, t_c2e)
        except Exception as e:
            print(f"{name}: 失败 {e}")

    if best is None:
        print("❌ 全部标定方法失败")
        return
    err, name, R, t = best
    print(f"\n=== 最佳: {name}（误差 {err:.4f}px）===")
    print("R_cam2gripper = np.array([")
    for row in R:
        print(f"    [{row[0]:.8f}, {row[1]:.8f}, {row[2]:.8f}],")
    print("])")
    print(f"t_cam2gripper = np.array([{t[0,0]:.8f}, {t[1,0]:.8f}, {t[2,0]:.8f}])")
    print("\n请复制到 vision/hand_eye.py 的 CALIB 字典。")


def _rpy2R(rpy):
    """RPY 欧拉角（弧度，xyz）→ 旋转矩阵。"""
    from scipy.spatial.transform import Rotation as R
    return R.from_euler("xyz", rpy).as_matrix()


def _reprojection_error(R_c2e, t_c2e, objp, R_boards, t_boards,
                        R_ends, t_ends, K, dist):
    """重投影误差：把标定板角点经（末端系→基座系→相机系）投影回图像，与检测角点比差。"""
    T_c2e = np.eye(4)
    T_c2e[:3, :3] = R_c2e
    T_c2e[:3, 3] = t_c2e.ravel()
    T_e2c = np.linalg.inv(T_c2e)
    # 标定板在基座系（取所有位姿均值，稳定参考）
    T_b2bases = []
    for i in range(len(R_ends)):
        T_e2b = np.eye(4)
        T_e2b[:3, :3] = R_ends[i]
        T_e2b[:3, 3] = t_ends[i].ravel()
        T_b2c = np.eye(4)
        T_b2c[:3, :3] = R_boards[i]
        T_b2c[:3, 3] = t_boards[i].ravel()
        T_b2bases.append(T_e2b @ T_c2e @ T_b2c)
    positions = np.array([T[:3, 3] for T in T_b2bases])
    T_board2base = np.eye(4)
    T_board2base[:3, 3] = positions.mean(axis=0)

    total_err = 0.0
    total_pts = 0
    for i in range(len(R_ends)):
        T_e2b = np.eye(4)
        T_e2b[:3, :3] = R_ends[i]
        T_e2b[:3, 3] = t_ends[i].ravel()
        T_b2e = np.linalg.inv(T_e2b)
        T_b2c = T_e2c @ T_b2e @ T_board2base
        rvec, _ = cv2.Rodrigues(T_b2c[:3, :3])
        proj, _ = cv2.projectPoints(objp, rvec, T_b2c[:3, 3].reshape(3, 1), K, dist)
        proj = proj.reshape(-1, 2)
        actual = cv2.projectPoints(
            objp, cv2.Rodrigues(R_boards[i])[0], t_boards[i], K, dist)[0].reshape(-1, 2)
        total_err += float(np.linalg.norm(proj - actual, axis=1).sum())
        total_pts += len(proj)
    return total_err / max(total_pts, 1)


if __name__ == "__main__":
    main()
