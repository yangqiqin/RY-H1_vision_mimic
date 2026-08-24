import pyrealsense2 as rs
import numpy as np
import cv2
import sys

# ===== 改成你 Viewer 里显示的参数 =====
WIDTH = 1280          # 改成 Viewer 的彩色宽度
HEIGHT = 720          # 改成 Viewer 的彩色高度
DEPTH_WIDTH = 1024    # 改成 Viewer 的深度宽度
DEPTH_HEIGHT = 768    # 改成 Viewer 的深度高度
FPS = 30              # 改成 Viewer 的帧率
# ======================================

pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, FPS)

print(f"尝试用 Viewer 参数启动: {WIDTH}x{HEIGHT} / {DEPTH_WIDTH}x{DEPTH_HEIGHT} @ {FPS}FPS")

try:
    profile = pipeline.start(config)
    print("✅ L515 启动成功！")
except Exception as e:
    print(f"❌ 启动失败: {e}")
    sys.exit(1)

align = rs.align(rs.stream.color)

print("按 ESC 退出")

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        color = np.asanyarray(aligned.get_color_frame().get_data())
        depth = np.asanyarray(aligned.get_depth_frame().get_data())
        depth_cm = cv2.applyColorMap(cv2.convertScaleAbs(depth, alpha=0.03), cv2.COLORMAP_JET)
        cv2.imshow('Color', color)
        cv2.imshow('Depth', depth_cm)
        if cv2.waitKey(1) == 27:
            break
finally:
    pipeline.stop()
    cv2.destroyAllWindows()