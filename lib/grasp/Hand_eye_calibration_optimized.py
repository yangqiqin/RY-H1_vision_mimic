'''
眼在手上标定
安装位置：
✓ 将12×9标定板固定在机械臂工作空间外的固定位置
✓ 标定板高度：0.8-1.2米
✓ 标定板角度：垂直或略微倾斜(5-10度)
✓ 标定板朝向：面向机械臂工作空间

安装位置：
✓ 将L515相机安装在机械臂末端法兰盘上
✓ 相机朝向：面向标定板方向
✓ 相机角度：与法兰盘垂直或略微倾斜

建议20-25个位姿，分布如下：
- 位置分散：围绕工作空间移动末端（前/后/左/右/上/下）
- 旋转分散：末端姿态变化，RX/RY/RZ各±30度以内范围
- 确保标定板始终在相机视野内
- 避免极端角度和几乎相同的位姿
'''

import cv2
import numpy as np
import glob
import os
import json
from datetime import datetime
from scipy.spatial.transform import Rotation as R


def pose_vectors_to_end2base_transforms(pose_vectors):
    """将位姿向量转换为变换矩阵
    注意：getToolPose()返回的是[x,y,z,rx,ry,rz]，其中(rx,ry,rz)是RPY欧拉角(弧度), xyz顺序
    """
    R_end2bases = []
    t_end2bases = []

    for pose_vector in pose_vectors:
        R_end2base = R.from_euler('xyz', pose_vector[3:6]).as_matrix()
        t_end2base = pose_vector[:3].reshape(3, 1)

        R_end2bases.append(R_end2base)
        t_end2bases.append(t_end2base)

    return np.array(R_end2bases), np.array(t_end2bases)


def detect_chessboard_corners(image_path, pattern_size, square_size):
    """检测棋盘格角点，返回精化后的角点"""
    img = cv2.imread(image_path)
    if img is None:
        return None, None, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, pattern_size)

    if ret:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        objp = np.zeros((np.prod(pattern_size), 3), dtype=np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2) * square_size
        objp[:, 2] = 0.0

        return corners_refined, objp, img
    else:
        return None, None, None


def compute_reprojection_error(R_cam2end, t_cam2end, obj_points, img_points,
                                R_end2bases, t_end2bases, R_board2cameras, t_board2cameras,
                                K, dist_coeffs):

    T_cam2end = np.eye(4)
    T_cam2end[:3, :3] = R_cam2end
    T_cam2end[:3, 3] = t_cam2end.ravel()
    T_end2cam = np.linalg.inv(T_cam2end)

    T_board2bases = []
    for i in range(len(obj_points)):
        T_end2base = np.eye(4)
        T_end2base[:3, :3] = R_end2bases[i]
        T_end2base[:3, 3] = t_end2bases[i].ravel()

        T_board2cam = np.eye(4)
        T_board2cam[:3, :3] = R_board2cameras[i]
        T_board2cam[:3, 3] = t_board2cameras[i].ravel()

        T_board2base_i = T_end2base @ T_cam2end @ T_board2cam
        T_board2bases.append(T_board2base_i)

    positions = np.array([T[:3, 3] for T in T_board2bases])
    avg_position = np.mean(positions, axis=0)

    rotations = np.array([R.from_matrix(T[:3, :3]).as_rotvec() for T in T_board2bases])
    avg_rotvec = np.mean(rotations, axis=0)
    avg_rotation = R.from_rotvec(avg_rotvec).as_matrix()

    T_board2base = np.eye(4)
    T_board2base[:3, :3] = avg_rotation
    T_board2base[:3, 3] = avg_position

    total_error = 0.0
    total_points = 0

    for i in range(len(obj_points)):
        T_end2base = np.eye(4)
        T_end2base[:3, :3] = R_end2bases[i]
        T_end2base[:3, 3] = t_end2bases[i].ravel()
        T_base2end = np.linalg.inv(T_end2base)

        T_board2cam = T_end2cam @ T_base2end @ T_board2base

        rvec, _ = cv2.Rodrigues(T_board2cam[:3, :3])
        tvec = T_board2cam[:3, 3].reshape(3, 1)

        projected, _ = cv2.projectPoints(obj_points[i], rvec, tvec, K, dist_coeffs)
        projected = projected.reshape(-1, 2)
        actual = img_points[i].reshape(-1, 2)

        errors = np.linalg.norm(projected - actual, axis=1)
        total_error += np.sum(errors)
        total_points += len(errors)

    if total_points == 0:
        return float('inf')
    return total_error / total_points


def evaluate_calibration_quality(R_camera2end, t_camera2end, det_success_num, total_images):
    """评估标定质量"""
    quality_metrics = {}
    quality_metrics['detection_rate'] = det_success_num / total_images
    quality_metrics['orthogonality_error'] = np.linalg.norm(np.dot(R_camera2end.T, R_camera2end) - np.eye(3))
    quality_metrics['determinant'] = np.linalg.det(R_camera2end)
    quality_metrics['translation_norm'] = np.linalg.norm(t_camera2end)
    return quality_metrics


def save_calibration_results(T_camera2end, quality_metrics, method_name, output_dir='./calibration_results'):
    """保存标定结果"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    np.savetxt(f'{output_dir}/T_camera2end_{method_name}_{timestamp}.txt',
               T_camera2end, fmt='%.8f')

    with open(f'{output_dir}/quality_metrics_{method_name}_{timestamp}.json', 'w') as f:
        json.dump(quality_metrics, f, indent=2)

    print(f"标定结果已保存到: {output_dir}")


def main():
    print("=== 优化版手眼标定程序 ===")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    pose_files = glob.glob(os.path.join(script_dir, 'pose_vectors_*.npy'))
    if not pose_files:
        print("错误: 未找到位姿数据文件 (pose_vectors_*.npy)")
        return

    latest_pose_file = max(pose_files, key=os.path.getctime)
    print(f"使用位姿数据文件: {os.path.basename(latest_pose_file)}")

    pose_vectors = np.load(latest_pose_file)
    print(f"加载了 {len(pose_vectors)} 个位姿")

    square_size = 0.026
    pattern_size = (8, 5)

    fx, fy, cx, cy = 901.7760620117188, 902.1463623046875, 643.151611328125, 361.9018249511719
    k1, k2 = 0.17391179502010345, -0.5176779627799988
    k3, k4, k5 = -0.00135987, 0.000356587, 0.0471074

    K = np.array([[fx, 0, cx],
                  [0, fy, cy],
                  [0, 0, 1]], dtype=np.float64)

    dist_coeffs = np.array([k1, k2, k3, k4, k5], dtype=np.float64)

    # 关键修复：按文件名排序，确保图像和位姿一一对应
    images = sorted(glob.glob(os.path.join(script_dir, 'eye_in_hand/images18', 'rgb_*.jpg')))
    depths = sorted(glob.glob(os.path.join(script_dir, 'eye_in_hand/depths18', 'depth_*.png')))

    print(f"找到 {len(images)} 张图像")
    print(f"位姿数据: {len(pose_vectors)} 个")
    print(f"图像排序后前3个: {[os.path.basename(f) for f in images[:3]]}")

    if len(images) != len(pose_vectors):
        print(f"警告: 图像数量({len(images)})与位姿数量({len(pose_vectors)})不匹配!")
        print("请确认 images18 目录中的图像与最新采集的位姿数据一一对应")
        print("如果目录中有旧图像，请清空后重新采集")

    obj_points = []
    img_points = []
    det_success_num = 0
    det_success_indices = []

    print("开始检测棋盘格角点...")
    for i, image_path in enumerate(images):
        corners, objp, img = detect_chessboard_corners(image_path, pattern_size, square_size)

        if corners is not None:
            obj_points.append(objp)
            img_points.append(corners)
            det_success_num += 1
            det_success_indices.append(i)

            cv2.drawChessboardCorners(img, pattern_size, corners, True)
            cv2.imshow(f'Detection {i+1}', img)
            cv2.waitKey(100)
        else:
            print(f"无法检测角点: {os.path.basename(image_path)}")

    cv2.destroyAllWindows()

    if det_success_num < 5:
        print("错误: 检测成功的图像数量太少，无法进行标定")
        return

    print(f"成功检测 {det_success_num} 张图像")

    R_board2cameras = []
    t_board2cameras = []

    for i in range(det_success_num):
        ret, rvec, t_board2camera = cv2.solvePnP(obj_points[i], img_points[i], K, dist_coeffs)
        R_board2camera, _ = cv2.Rodrigues(rvec)

        R_board2cameras.append(R_board2camera)
        t_board2cameras.append(t_board2camera)

    # 只使用检测成功对应的位姿
    R_end2bases_all, t_end2bases_all = pose_vectors_to_end2base_transforms(pose_vectors)

    R_end2bases = []
    t_end2bases = []
    for idx in det_success_indices:
        if idx < len(R_end2bases_all):
            R_end2bases.append(R_end2bases_all[idx])
            t_end2bases.append(t_end2bases_all[idx])
        else:
            print(f"警告: 图像索引 {idx} 超出位姿数据范围，跳过")

    min_count = min(len(R_end2bases), len(R_board2cameras))
    print(f"有效位姿数据: {len(R_end2bases)}, 检测成功图像: {len(R_board2cameras)}")
    print(f"使用 {min_count} 组位姿数据进行标定")

    if len(R_end2bases) != len(R_board2cameras):
        print(f"警告: 有效位姿数据({len(R_end2bases)})与检测成功图像({len(R_board2cameras)})不匹配")
        R_end2bases = R_end2bases[:min_count]
        t_end2bases = t_end2bases[:min_count]
        R_board2cameras = R_board2cameras[:min_count]
        t_board2cameras = t_board2cameras[:min_count]
        obj_points = obj_points[:min_count]
        img_points = img_points[:min_count]

    R_end2bases = np.array(R_end2bases)
    t_end2bases = np.array(t_end2bases)
    R_board2cameras = np.array(R_board2cameras)
    t_board2cameras = np.array(t_board2cameras)

    methods = [cv2.CALIB_HAND_EYE_TSAI, cv2.CALIB_HAND_EYE_PARK,
               cv2.CALIB_HAND_EYE_HORAUD, cv2.CALIB_HAND_EYE_ANDREFF]
    method_names = ['TSAI', 'PARK', 'HORAUD', 'ANDREFF']

    all_results = []

    print("\n尝试不同的手眼标定方法:")
    for method, name in zip(methods, method_names):
        try:
            R_cam2end, t_cam2end = cv2.calibrateHandEye(
                R_end2bases, t_end2bases, R_board2cameras, t_board2cameras, method=method)

            rep_error = compute_reprojection_error(
                R_cam2end, t_cam2end, obj_points, img_points,
                R_end2bases, t_end2bases, R_board2cameras, t_board2cameras,
                K, dist_coeffs)

            t_norm = np.linalg.norm(t_cam2end)

            print(f"{name}方法: 重投影误差 = {rep_error:.4f} px, 平移向量模长 = {t_norm:.4f} m ({t_norm*100:.1f} cm)")
            print(f"  R_cam2end = ")
            print(f"    [{R_cam2end[0,0]:.6f}, {R_cam2end[0,1]:.6f}, {R_cam2end[0,2]:.6f}]")
            print(f"    [{R_cam2end[1,0]:.6f}, {R_cam2end[1,1]:.6f}, {R_cam2end[1,2]:.6f}]")
            print(f"    [{R_cam2end[2,0]:.6f}, {R_cam2end[2,1]:.6f}, {R_cam2end[2,2]:.6f}]")
            print(f"  t_cam2end = [{t_cam2end[0,0]:.6f}, {t_cam2end[1,0]:.6f}, {t_cam2end[2,0]:.6f}]")

            all_results.append((name, method, R_cam2end, t_cam2end, rep_error, t_norm))

        except Exception as e:
            print(f"{name}方法: 失败 - {e}")

    if not all_results:
        print("错误: 所有标定方法都失败了")
        return

    # 按重投影误差排序，选择最佳方法
    all_results.sort(key=lambda x: x[4])

    best_name, best_method, best_R, best_t, best_error, best_t_norm = all_results[0]

    R_camera2end = best_R
    t_camera2end = best_t

    T_camera2end = np.eye(4)
    T_camera2end[:3, :3] = R_camera2end
    T_camera2end[:3, 3] = t_camera2end.reshape(3)

    quality_metrics = evaluate_calibration_quality(R_camera2end, t_camera2end, det_success_num, len(images))

    print(f"\n=== 标定结果 ({best_name}方法，重投影误差最低) ===")
    print("相机到机械臂末端的变换矩阵:")
    np.set_printoptions(suppress=True)
    print(T_camera2end)

    print(f"\n=== 所有方法结果 ===")
    print(f"{'方法':<10} {'重投影误差(px)':<18} {'平移模长(m)':<15} {'平移模长(cm)':<15}")
    for name, _, _, _, rep_err, t_norm in all_results:
        print(f"{name:<10} {rep_err:<18.4f} {t_norm:<15.4f} {t_norm*100:<15.1f}")

    print(f"\n=== 质量评估 ===")
    print(f"检测成功率: {quality_metrics['detection_rate']*100:.1f}%")
    print(f"旋转矩阵正交性误差: {quality_metrics['orthogonality_error']:.6f}")
    print(f"旋转矩阵行列式: {quality_metrics['determinant']:.6f}")
    print(f"平移向量模长: {quality_metrics['translation_norm']:.4f} 米 ({quality_metrics['translation_norm']*100:.1f} 厘米)")
    print(f"重投影误差: {best_error:.4f} px")

    # 输出可直接复制到task_kele.py的参数
    print(f"\n=== 可直接复制到 task_kele.py 的参数 ===")
    print("R_cam2gripper = np.array([")
    print(f"    [{R_camera2end[0,0]:.8f}, {R_camera2end[0,1]:.8f}, {R_camera2end[0,2]:.8f}],")
    print(f"    [{R_camera2end[1,0]:.8f}, {R_camera2end[1,1]:.8f}, {R_camera2end[1,2]:.8f}],")
    print(f"    [{R_camera2end[2,0]:.8f}, {R_camera2end[2,1]:.8f}, {R_camera2end[2,2]:.8f}]")
    print("])")
    print(f"t_cam2gripper = np.array([{t_camera2end[0,0]:.8f}, {t_camera2end[1,0]:.8f}, {t_camera2end[2,0]:.8f}])")

    save_calibration_results(T_camera2end, quality_metrics, best_name)

    print("\n标定完成！")


if __name__ == '__main__':
    main()