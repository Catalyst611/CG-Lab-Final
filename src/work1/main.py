import taichi as ti
import numpy as np
import math

ti.init(arch=ti.cpu)

width = 700
height = 700
#第四位1表示一个点，0表示方向向量
vertices = np.array([
    [2.0, 0.0, -2.0, 1.0],
    [0.0, 2.0, -2.0, 1.0],
    [-2.0, 0.0, -2.0, 1.0]
], dtype=np.float32)

def get_model_matrix(angle):
    rad = angle * math.pi / 180.0
    #转换为弧度制
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return np.array([[cos_a, -sin_a, 0, 0],[sin_a, cos_a, 0, 0],
        [0, 0, 1, 0],[0, 0, 0, 1]
    ], dtype=np.float32)
    #前两行控制x和y

def get_view_matrix(eye_pos):
    ex, ey, ez = eye_pos
    #解包相机坐标
    return np.array([
        [1, 0, 0, -ex],[0, 1, 0, -ey],
        [0, 0, 1, -ez],[0, 0, 0, 1]
    ], dtype=np.float32)

def get_projection_matrix(eye_fov, aspect_ratio, zNear, zFar):
    fov_rad = eye_fov * math.pi / 180.0
    
    t = math.tan(fov_rad / 2.0) * abs(zNear)
    b = -t
    r = aspect_ratio * t
    l = -r

    n = -zNear
    f = -zFar

    M_p2o = np.array([[n, 0, 0, 0],
        [0, n, 0, 0],[0, 0, n + f, -n * f],
        [0, 0, 1, 0]
    ], dtype=np.float32)

    M_ortho = np.array([[2 / (r - l), 0, 0, 0],[0, 2 / (t - b), 0, 0],[0, 0, 2 / (n - f), -(n + f) / (n - f)],[0, 0, 0, 1]
    ], dtype=np.float32)

    return M_ortho @ M_p2o

def run():
    gui = ti.GUI("Work1: MVP Triangle", res=(width, height))
    angle = 0.0
    eye_pos =[0.0, 0.0, 5.0]

    while gui.running:
        for e in gui.get_events(ti.GUI.PRESS):
            if e.key == 'a' or e.key == 'A': angle += 5.0
            elif e.key == 'd' or e.key == 'D': angle -= 5.0
            elif e.key == ti.GUI.ESCAPE: gui.running = False

        model = get_model_matrix(angle)
        view = get_view_matrix(eye_pos)
        proj = get_projection_matrix(45.0, width / height, 0.1, 50.0)
        mvp = proj @ view @ model

        screen_pos = []
        for i in range(3):
            v = vertices[i]
            v_clip = mvp @ v
            w = v_clip[3]
            v_ndc = v_clip / w
            
            screen_x = (v_ndc[0] + 1.0) / 2.0
            screen_y = (v_ndc[1] + 1.0) / 2.0
            screen_pos.append([screen_x, screen_y])

        gui.line(screen_pos[0], screen_pos[1], radius=2, color=0x00BFFF)
        gui.line(screen_pos[1], screen_pos[2], radius=2, color=0x00BFFF)
        gui.line(screen_pos[2], screen_pos[0], radius=2, color=0x00BFFF)
        
        gui.text("Press A/D to rotate Z-axis", pos=(0.05, 0.95), color=0xFFFFFF)
        gui.show()

if __name__ == "__main__":
    run()