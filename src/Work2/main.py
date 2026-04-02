import taichi as ti
import numpy as np

# 初始化 GPU 环境
ti.init(arch=ti.gpu)

# --- 常量定义 ---
RES = 800
NUM_SEGMENTS = 1000
MAX_CONTROL_POINTS = 100

# --- 显存预分配 (Field) ---
# 1. 像素缓冲区，存储最终画面 RGB 值
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))
# 2. 接收 CPU 算好的曲线坐标
curve_points_field = ti.Vector.field(2, dtype=ti.f32, shape=NUM_SEGMENTS + 1)
# 3. UI 控制点对象池
gui_points = ti.Vector.field(2, dtype=ti.f32, shape=MAX_CONTROL_POINTS)
gui_indices = ti.field(dtype=ti.i32, shape=(MAX_CONTROL_POINTS - 1) * 2)

def de_casteljau(points, t):
    """CPU 端：使用递归线性插值实现 De Casteljau 算法"""
    if len(points) == 1:
        return points[0]
    new_points =[]
    for i in range(len(points) - 1):
        p0, p1 = points[i], points[i + 1]
        nx = p0[0] * (1 - t) + p1[0] * t
        ny = p0[1] * (1 - t) + p1[1] * t
        new_points.append([nx, ny])
    return de_casteljau(new_points, t)

@ti.kernel
def clear_pixels():
    """清理上一帧的像素"""
    for i, j in pixels:
        pixels[i, j] =[0.0, 0.0, 0.0]

@ti.kernel
def draw_curve_kernel(n: ti.i32):
    """GPU 端：光栅化绘制像素"""
    for i in range(n):
        p = curve_points_field[i]
        # 将 [0, 1] 浮点坐标映射为真实的屏幕整数索引
        x = ti.cast(p[0] * RES, ti.i32)
        y = ti.cast(p[1] * RES, ti.i32)
        
        # 越界检查与点亮像素 (绿色)
        if 0 <= x < RES and 0 <= y < RES:
            pixels[x, y] = [0.0, 1.0, 0.0]

def run():
    window = ti.ui.Window("Work2: Bezier Curve & Rasterization", (RES, RES))
    canvas = window.get_canvas()
    
    ctrl_points =[]

    while window.running:
        # 1. 处理鼠标和键盘交互事件
        for e in window.get_events(ti.ui.PRESS):
            if e.key == ti.ui.LMB:
                if len(ctrl_points) < MAX_CONTROL_POINTS:
                    pos = window.get_cursor_pos()
                    ctrl_points.append([pos[0], pos[1]])
            elif e.key == 'c' or e.key == 'C':
                ctrl_points.clear()
            elif e.key == ti.ui.ESCAPE:
                window.running = False

        clear_pixels()
        n_pts = len(ctrl_points)

        # 2. 计算曲线与绘制
        if n_pts >= 2:
            # CPU 批量计算
            curve_np = np.zeros((NUM_SEGMENTS + 1, 2), dtype=np.float32)
            for i in range(NUM_SEGMENTS + 1):
                t = i / NUM_SEGMENTS
                curve_np[i] = de_casteljau(ctrl_points, t)
            
            # 将数据一次性拷入 GPU，并在 GPU 上并行执行光栅化
            curve_points_field.from_numpy(curve_np)
            draw_curve_kernel(NUM_SEGMENTS + 1)

        # 3. 显示底层像素缓冲区
        canvas.set_image(pixels)

        # 4. 绘制上层 UI (控制多边形与红色控制点)
        if n_pts > 0:
            # 对象池技巧：将未使用的点隐藏在屏幕外(-10.0)
            gui_pts_np = np.full((MAX_CONTROL_POINTS, 2), -10.0, dtype=np.float32)
            for i in range(n_pts):
                gui_pts_np[i] = ctrl_points[i]
            gui_points.from_numpy(gui_pts_np)

            # 更新用于连线的索引数组
            if n_pts >= 2:
                idx_np = np.zeros((MAX_CONTROL_POINTS - 1) * 2, dtype=np.int32)
                for i in range(n_pts - 1):
                    idx_np[2*i] = i
                    idx_np[2*i+1] = i+1
                gui_indices.from_numpy(idx_np)
                canvas.lines(gui_points, width=0.005, indices=gui_indices, color=(0.5, 0.5, 0.5))

            canvas.circles(gui_points, radius=0.008, color=(1.0, 0.0, 0.0))

        window.show()

if __name__ == '__main__':
    run()