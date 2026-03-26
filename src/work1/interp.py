# src/Work1/interp.py
import taichi as ti
import numpy as np
import math
import time
from .main import get_view_matrix, get_projection_matrix

ti.init(arch=ti.cpu)
width, height = 800, 600

# 顶点与边定义
vertices = np.array([
    [-1, -1, -1, 1],[1, -1, -1, 1], [1, 1, -1, 1],[-1, 1, -1, 1],
    [-1, -1, 1, 1],[1, -1, 1, 1],  [1, 1, 1, 1],[-1, 1, 1, 1]
], dtype=np.float32)

edges =[
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7)
]

def get_model_matrix_3d(angle_x, angle_y, tx=0.0):
    """支持平移与旋转的复合模型矩阵"""
    rad_x = angle_x * math.pi / 180.0
    rad_y = angle_y * math.pi / 180.0
    
    rot_x = np.array([[1, 0, 0, 0],[0, math.cos(rad_x), -math.sin(rad_x), 0],[0, math.sin(rad_x), math.cos(rad_x), 0], [0, 0, 0, 1]], dtype=np.float32)
    rot_y = np.array([[math.cos(rad_y), 0, math.sin(rad_y), 0], [0, 1, 0, 0],[-math.sin(rad_y), 0, math.cos(rad_y), 0],[0, 0, 0, 1]], dtype=np.float32)
    trans = np.array([[1, 0, 0, tx], [0, 1, 0, 0],[0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32)
    
    return trans @ rot_y @ rot_x

def draw_cube(gui, mvp, color):
    """根据 MVP 矩阵绘制单个立方体"""
    screen_pos = []
    for i in range(8):
        v_clip = mvp @ vertices[i]
        v_ndc = v_clip / v_clip[3]
        screen_pos.append([(v_ndc[0] + 1.0) / 2.0, (v_ndc[1] + 1.0) / 2.0])
    for edge in edges:
        gui.line(screen_pos[edge[0]], screen_pos[edge[1]], radius=1.5, color=color)

def run():
    gui = ti.GUI("Work1 Bonus: Rotation Interpolation", res=(width, height))
    eye_pos =[0.0, 0.0, 9.0] # 相机拉远，以便容纳3个立方体

    # 定义起始姿态 (R0) 和 结束姿态 (R1)
    pose0 = {'x': 0.0, 'y': 0.0, 'tx': -3.5}
    pose1 = {'x': 90.0, 'y': 180.0, 'tx': 3.5}

    while gui.running:
        for e in gui.get_events(ti.GUI.PRESS):
            if e.key == ti.GUI.ESCAPE: gui.running = False

        # 生成随时间振荡的插值系数 t，范围 [0, 1]
        t = (math.sin(time.time() * 2.0) + 1.0) / 2.0 

        view = get_view_matrix(eye_pos)
        proj = get_projection_matrix(45.0, width / height, 0.1, 50.0)

        # 1. 绘制静止的 R0 (深灰色)
        m0 = get_model_matrix_3d(pose0['x'], pose0['y'], pose0['tx'])
        draw_cube(gui, proj @ view @ m0, color=0x444444)

        # 2. 绘制静止的 R1 (深灰色)
        m1 = get_model_matrix_3d(pose1['x'], pose1['y'], pose1['tx'])
        draw_cube(gui, proj @ view @ m1, color=0x444444)

        # 3. 计算插值姿态 Rt 并绘制 (天蓝色)
        cur_x = pose0['x'] * (1 - t) + pose1['x'] * t
        cur_y = pose0['y'] * (1 - t) + pose1['y'] * t
        cur_tx = pose0['tx'] * (1 - t) + pose1['tx'] * t
        
        mt = get_model_matrix_3d(cur_x, cur_y, cur_tx)
        draw_cube(gui, proj @ view @ mt, color=0x00BFFF)

        # UI 提示
        gui.text("R0", pos=(0.15, 0.85), color=0xFFFFFF)
        gui.text("R1", pos=(0.82, 0.85), color=0xFFFFFF)
        gui.text(f"Rt (t={t:.2f})", pos=(0.45, 0.90), color=0x00BFFF)
        gui.show()

if __name__ == "__main__":
    run()