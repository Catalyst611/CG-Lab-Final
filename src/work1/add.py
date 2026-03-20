import taichi as ti
import numpy as np
import math
from .main import get_view_matrix, get_projection_matrix

ti.init(arch=ti.cpu)
width, height = 700, 700

# 正方体 8 个顶点
vertices = np.array([
    [-1, -1, -1, 1],[ 1, -1, -1, 1],[ 1,  1, -1, 1], [-1,  1, -1, 1],[-1, -1,  1, 1], [ 1, -1,  1, 1],[ 1,  1,  1, 1], [-1,  1,  1, 1]
], dtype=np.float32)

# 正方体 12 条边
edges =[
    (0,1), (1,2), (2,3), (3,0), # 后
    (4,5), (5,6), (6,7), (7,4), # 前
    (0,4), (1,5), (2,6), (3,7)  # 侧
]

def get_model_matrix_3d(angle_x, angle_y):
    rad_x = angle_x * math.pi / 180.0
    rad_y = angle_y * math.pi / 180.0
    rot_x = np.array([
        [1, 0, 0, 0],[0, math.cos(rad_x), -math.sin(rad_x), 0],[0, math.sin(rad_x), math.cos(rad_x), 0],[0, 0, 0, 1]
    ], dtype=np.float32)
    rot_y = np.array([[math.cos(rad_y), 0, math.sin(rad_y), 0], [0, 1, 0, 0],[-math.sin(rad_y), 0, math.cos(rad_y), 0],[0, 0, 0, 1]
    ], dtype=np.float32)
    return rot_y @ rot_x

def run():
    gui = ti.GUI("Work1 Bonus: 3D Cube", res=(width, height))
    angle_x, angle_y = 0.0, 0.0
    eye_pos = [0.0, 0.0, 6.0]

    while gui.running:
        for e in gui.get_events(ti.GUI.PRESS):
            if e.key == 'w' or e.key == 'W': angle_x -= 5.0
            elif e.key == 's' or e.key == 'S': angle_x += 5.0
            elif e.key == 'a' or e.key == 'A': angle_y -= 5.0
            elif e.key == 'd' or e.key == 'D': angle_y += 5.0
            elif e.key == ti.GUI.ESCAPE: gui.running = False

        model = get_model_matrix_3d(angle_x, angle_y)
        view = get_view_matrix(eye_pos)
        proj = get_projection_matrix(45.0, width / height, 0.1, 50.0)
        mvp = proj @ view @ model

        screen_pos =[]
        for i in range(8):
            v_clip = mvp @ vertices[i]
            v_ndc = v_clip / v_clip[3]
            screen_pos.append([(v_ndc[0] + 1.0) / 2.0, (v_ndc[1] + 1.0) / 2.0])

        for edge in edges:
            gui.line(screen_pos[edge[0]], screen_pos[edge[1]], radius=1.5, color=0x00FF00)
            
        gui.text("Press W/S to rotate X, A/D to rotate Y", pos=(0.05, 0.95), color=0xFFFFFF)
        gui.show()

if __name__ == "__main__":
    run()