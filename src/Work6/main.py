# src/Work6/main.py
import taichi as ti

ti.init(arch=ti.gpu)

N = 20           
mass = 1.0       
l0 = 0.05        
dt = 2e-3        
substeps = 10    

stiffness = ti.field(dtype=ti.f32, shape=())
damping = ti.field(dtype=ti.f32, shape=())
max_vel = ti.field(dtype=ti.f32, shape=())

x = ti.Vector.field(3, dtype=ti.f32, shape=(N, N))
v = ti.Vector.field(3, dtype=ti.f32, shape=(N, N))
f = ti.Vector.field(3, dtype=ti.f32, shape=(N, N))
x_old = ti.Vector.field(3, dtype=ti.f32, shape=(N, N))
v_old = ti.Vector.field(3, dtype=ti.f32, shape=(N, N))

# 渲染专用的一维数组
vertices = ti.Vector.field(3, dtype=ti.f32, shape=N * N)
# 用于画线的弹簧边缘索引 (水平 + 垂直弹簧)
num_edges = 2 * N * (N - 1)
edge_indices = ti.field(dtype=ti.i32, shape=num_edges * 2)

@ti.kernel
def init_mesh():
    for i, j in x:
        x[i, j] = ti.Vector([(i - N / 2) * l0, 0.5, (j - N / 2) * l0])
        v[i, j] = ti.Vector([0.0, 0.0, 0.0])

@ti.kernel
def init_edge_indices():
    """提取质点之间的连线索引，用于渲染白色的弹簧线"""
    for i, j in ti.ndrange(N, N):
        if i < N - 1:
            eid = i * N + j
            edge_indices[eid * 2] = i * N + j
            edge_indices[eid * 2 + 1] = (i + 1) * N + j
        if j < N - 1:
            eid = N * (N - 1) + j * N + i
            edge_indices[eid * 2] = i * N + j
            edge_indices[eid * 2 + 1] = i * N + (j + 1)

@ti.func
def compute_forces_on():
    for i, j in f:
        f[i, j] = ti.Vector([0.0, -9.8, 0.0]) * mass - damping[None] * v[i, j]
        
    for i, j in ti.ndrange(N, N):
        if i < N - 1:
            dir = x[i, j] - x[i + 1, j]
            length = dir.norm()
            force = -stiffness[None] * (length - l0) * (dir / ti.max(length, 1e-4))
            ti.atomic_add(f[i, j], force)
            ti.atomic_add(f[i + 1, j], -force)
        if j < N - 1:
            dir = x[i, j] - x[i, j + 1]
            length = dir.norm()
            force = -stiffness[None] * (length - l0) * (dir / ti.max(length, 1e-4))
            ti.atomic_add(f[i, j], force)
            ti.atomic_add(f[i, j + 1], -force)

@ti.func
def clamp_velocity(i, j):
    vl = v[i, j].norm()
    if vl > max_vel[None]:
        v[i, j] = v[i, j] / vl * max_vel[None]

@ti.kernel
def step_explicit():
    compute_forces_on() 
    for i, j in x:
        if not (i == 0 and (j == 0 or j == N - 1)): # 挂住顶部的两个角
            x[i, j] += v[i, j] * dt
            v[i, j] += (f[i, j] / mass) * dt
            clamp_velocity(i, j)

@ti.kernel
def step_semi_implicit():
    compute_forces_on()
    for i, j in x:
        if not (i == 0 and (j == 0 or j == N - 1)):
            v[i, j] += (f[i, j] / mass) * dt
            clamp_velocity(i, j)
            x[i, j] += v[i, j] * dt

@ti.kernel
def backup_state():
    for i, j in x:
        x_old[i, j] = x[i, j]
        v_old[i, j] = v[i, j]

@ti.kernel
def step_implicit_iter():
    compute_forces_on()
    for i, j in x:
        if not (i == 0 and (j == 0 or j == N - 1)):
            v[i, j] = v_old[i, j] + (f[i, j] / mass) * dt
            clamp_velocity(i, j)
            x[i, j] = x_old[i, j] + v[i, j] * dt

@ti.kernel
def update_vertices():
    """将二维坐标展平"""
    for i, j in x:
        vertices[i * N + j] = x[i, j]

def run():
    init_mesh()
    init_edge_indices()
    
    stiffness[None], damping[None], max_vel[None] = 5000.0, 2.0, 100.0
    solver_mode = 1 
    paused = False

    window = ti.ui.Window("Games101 - Mass Spring System", (800, 800))
    canvas = window.get_canvas()
    scene = window.get_scene() 
    camera = ti.ui.Camera()
    camera.position(0.5, 0.0, 1.5)
    camera.lookat(0.0, 0.0, 0.0)

    while window.running:
        gui = window.get_gui()
        with gui.sub_window("Control Panel", 0.02, 0.02, 0.4, 0.35):
            gui.text("Integration Method:")
            # 复刻老师的单选框逻辑
            if gui.checkbox("Explicit Euler (Explosive)", solver_mode == 0): solver_mode = 0
            if gui.checkbox("Semi-Implicit Euler (Stable)", solver_mode == 1): solver_mode = 1
            if gui.checkbox("Implicit Euler (Damped)", solver_mode == 2): solver_mode = 2
            
            gui.text("") # 空行
            paused = gui.checkbox("Pause Simulation", paused)
            if gui.button("Reset Cloth"):
                init_mesh()

            gui.text("") 
            stiffness[None] = gui.slider_float("Stiffness", stiffness[None], 1000.0, 10000.0)
            damping[None] = gui.slider_float("Damping", damping[None], 0.0, 10.0)

        if not paused:
            for _ in range(substeps):
                if solver_mode == 0:
                    step_explicit()
                elif solver_mode == 1:
                    step_semi_implicit()
                elif solver_mode == 2:
                    backup_state()
                    for _iter in range(3): 
                        step_implicit_iter()

        update_vertices()
        camera.track_user_inputs(window, movement_speed=0.03, hold_key=ti.ui.RMB)
        scene.set_camera(camera)
        scene.ambient_light((0.5, 0.5, 0.5))
        scene.point_light(pos=(0.5, 1.5, 1.5), color=(1, 1, 1))
        
        # 1. 渲染弹簧白线
        scene.lines(vertices, width=0.002, indices=edge_indices, color=(0.8, 0.8, 0.8))
        # 2. 渲染蓝色的质点
        scene.particles(vertices, radius=0.015, color=(0.2, 0.7, 1.0))
        
        canvas.scene(scene)
        window.show()

if __name__ == "__main__":
    run()