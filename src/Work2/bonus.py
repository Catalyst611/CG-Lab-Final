# src/Work2/bonus.py
import taichi as ti
import numpy as np
from .main import de_casteljau

ti.init(arch=ti.gpu)

RES = 800
NUM_SEGMENTS = 1000
MAX_CONTROL_POINTS = 100
MAX_CURVE_POINTS = 20000

pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))
curve_points_field = ti.Vector.field(2, dtype=ti.f32, shape=MAX_CURVE_POINTS)
gui_points = ti.Vector.field(2, dtype=ti.f32, shape=MAX_CONTROL_POINTS)
gui_indices = ti.field(dtype=ti.i32, shape=(MAX_CONTROL_POINTS - 1) * 2)

# 三次均匀 B 样条基矩阵
M_B = np.array([[-1,  3, -3,  1],
    [ 3, -6,  3,  0],
    [-3,  0,  3,  0],[ 1,  4,  1,  0]
], dtype=np.float32) / 6.0

@ti.kernel
def clear_pixels():
    for i, j in pixels: pixels[i, j] =[0.0, 0.0, 0.0]

@ti.kernel
def draw_curve_aa_kernel(n: ti.i32, r: ti.f32, g: ti.f32, b: ti.f32):
    """反走样内核：点亮浮点坐标周围 5x5 的邻域，根据欧式距离计算颜色权重"""
    color = ti.Vector([r, g, b])
    for i in range(n):
        p = curve_points_field[i]
        px, py = p[0] * RES, p[1] * RES
        cx, cy = ti.cast(px, ti.i32), ti.cast(py, ti.i32)
        
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                x, y = cx + dx, cy + dy
                if 0 <= x < RES and 0 <= y < RES:
                    dist = ti.math.sqrt((x - px)**2 + (y - py)**2)
                    # 距离越近，权重越大。采用 max(0, 1 - dist * 0.5) 形成柔和边缘
                    intensity = ti.max(0.0, 1.0 - dist * 0.5)
                    
                    # 混合颜色，限制最大亮度防止过曝
                    cur_c = pixels[x, y]
                    pixels[x, y] = ti.math.clamp(cur_c + color * intensity, 0.0, 1.0)

def eval_bspline(points):
    """CPU 端：利用矩阵乘法分段计算均匀三次 B 样条坐标"""
    n = len(points)
    if n < 4: return np.zeros((0, 2), dtype=np.float32)
    
    total_points = (n - 3) * NUM_SEGMENTS + 1
    curve_np = np.zeros((total_points, 2), dtype=np.float32)
    
    idx = 0
    for i in range(n - 3):
        # 提取 4 个相邻控制点
        P = np.array(points[i:i+4], dtype=np.float32) 
        steps = NUM_SEGMENTS if i < n - 4 else NUM_SEGMENTS + 1
        for j in range(steps):
            t = j / NUM_SEGMENTS
            T = np.array([t**3, t**2, t, 1], dtype=np.float32)
            curve_np[idx] = T @ M_B @ P
            idx += 1
    return curve_np

def run():
    window = ti.ui.Window("Work2 Bonus: AA & B-Spline", (RES, RES))
    canvas = window.get_canvas()
    ctrl_points =[]
    mode = 'bezier'

    while window.running:
        for e in window.get_events(ti.ui.PRESS):
            if e.key == ti.ui.LMB and len(ctrl_points) < MAX_CONTROL_POINTS:
                pos = window.get_cursor_pos()
                ctrl_points.append([pos[0], pos[1]])
            elif e.key == 'c' or e.key == 'C':
                ctrl_points.clear()
            elif e.key == 'b' or e.key == 'B':
                mode = 'bspline' if mode == 'bezier' else 'bezier'
            elif e.key == ti.ui.ESCAPE:
                window.running = False

        clear_pixels()
        n_pts = len(ctrl_points)

        if mode == 'bezier' and n_pts >= 2:
            curve_np = np.zeros((NUM_SEGMENTS + 1, 2), dtype=np.float32)
            for i in range(NUM_SEGMENTS + 1):
                curve_np[i] = de_casteljau(ctrl_points, i / NUM_SEGMENTS)
            curve_points_field.from_numpy(curve_np)
            draw_curve_aa_kernel(NUM_SEGMENTS + 1, 0.0, 1.0, 0.0) # 绿色贝塞尔

        elif mode == 'bspline' and n_pts >= 4:
            curve_np = eval_bspline(ctrl_points)
            curve_points_field.from_numpy(curve_np)
            draw_curve_aa_kernel(len(curve_np), 0.0, 0.8, 1.0) # 青色 B样条

        canvas.set_image(pixels)

        if n_pts > 0:
            gui_pts_np = np.full((MAX_CONTROL_POINTS, 2), -10.0, dtype=np.float32)
            for i in range(n_pts): gui_pts_np[i] = ctrl_points[i]
            gui_points.from_numpy(gui_pts_np)

            if n_pts >= 2:
                idx_np = np.zeros((MAX_CONTROL_POINTS - 1) * 2, dtype=np.int32)
                for i in range(n_pts - 1):
                    idx_np[2*i], idx_np[2*i+1] = i, i+1
                gui_indices.from_numpy(idx_np)
                canvas.lines(gui_points, width=0.005, indices=gui_indices, color=(0.5, 0.5, 0.5))

            canvas.circles(gui_points, radius=0.008, color=(1.0, 0.0, 0.0))
            
        gui_text = "Mode: Bezier (Green) | Press 'B' to switch" if mode == 'bezier' else "Mode: B-Spline (Cyan) | Press 'B' to switch"
        window.GUI.begin("Controls", 0.02, 0.02, 0.4, 0.1)
        window.GUI.text(gui_text)
        window.GUI.text("Left Click: Add | 'C': Clear | ESC: Exit")
        window.GUI.end()
        window.show()

if __name__ == '__main__':
    run()