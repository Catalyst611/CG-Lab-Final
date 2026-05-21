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
indices = ti.field(dtype=ti.i32, shape=(N - 1) * (N - 1) * 6)

vertices = ti.Vector.field(3, dtype=ti.f32, shape=N * N)

sphere_pos = ti.Vector.field(3, dtype=ti.f32, shape=(1,))
sphere_r = 0.3

@ti.kernel
def init_mesh():
    for i, j in x:
        x[i, j] = ti.Vector([(i - N / 2) * l0, 0.6, (j - N / 2) * l0])
        v[i, j] = ti.Vector([0.0, 0.0, 0.0])
    sphere_pos[0] = ti.Vector([0.0, 0.0, 0.0])

@ti.kernel
def init_indices():
    for i, j in ti.ndrange(N - 1, N - 1):
        quad_id = i * (N - 1) + j
        idx = quad_id * 6
        indices[idx + 0] = i * N + j
        indices[idx + 1] = (i + 1) * N + j
        indices[idx + 2] = i * N + (j + 1)
        indices[idx + 3] = (i + 1) * N + j
        indices[idx + 4] = (i + 1) * N + (j + 1)
        indices[idx + 5] = i * N + (j + 1)

@ti.func
def compute_forces_on():
    for i, j in f:
        f[i, j] = ti.Vector([0.0, -9.8, 0.0]) * mass - damping[None] * v[i, j]
        
    for i, j in ti.ndrange(N, N):
        if i < N - 1:
            add_spring_force(i, j, i + 1, j, l0)
        if j < N - 1:
            add_spring_force(i, j, i, j + 1, l0)
            
        l_shear = l0 * 1.41421356
        if i < N - 1 and j < N - 1:
            add_spring_force(i, j, i + 1, j + 1, l_shear)
            add_spring_force(i + 1, j, i, j + 1, l_shear)
            
        l_bend = l0 * 2.0
        if i < N - 2:
            add_spring_force(i, j, i + 2, j, l_bend)
        if j < N - 2:
            add_spring_force(i, j, i, j + 2, l_bend)

@ti.func
def add_spring_force(i1, j1, i2, j2, rest_len):
    dir = x[i1, j1] - x[i2, j2]
    length = dir.norm()
    force = -stiffness[None] * (length - rest_len) * (dir / ti.max(length, 1e-4))
    ti.atomic_add(f[i1, j1], force)
    ti.atomic_add(f[i2, j2], -force)

@ti.func
def process_collision(i, j):
    dist_vec = x[i, j] - sphere_pos[0]
    dist = dist_vec.norm()
    if dist < sphere_r + 0.01:
        x[i, j] = sphere_pos[0] + dist_vec.normalized() * (sphere_r + 0.01)
        v[i, j] *= 0.3

@ti.kernel
def step_semi_implicit():
    compute_forces_on()
    for i, j in x:
        if not ((i == 0 or i == N - 1) and (j == 0 or j == N - 1)): 
            v[i, j] += (f[i, j] / mass) * dt
            vl = v[i, j].norm()
            if vl > max_vel[None]: v[i, j] = v[i, j] / vl * max_vel[None]
            x[i, j] += v[i, j] * dt
            process_collision(i, j)

@ti.kernel
def update_vertices():
    for i, j in x:
        vertices[i * N + j] = x[i, j]

def run():
    init_mesh()
    init_indices()
    stiffness[None], damping[None], max_vel[None] = 6000.0, 3.0, 80.0

    window = ti.ui.Window("Work6 Bonus: Complete Springs & Collision", (800, 800))
    canvas = window.get_canvas()
    scene = window.get_scene()
    camera = ti.ui.Camera()
    camera.position(0.0, 0.5, 2.0)
    camera.lookat(0.0, 0.0, 0.0)

    while window.running:
        for _ in range(substeps):
            step_semi_implicit()

        update_vertices()
        camera.track_user_inputs(window, movement_speed=0.03, hold_key=ti.ui.RMB)
        scene.set_camera(camera)
        scene.ambient_light((0.5, 0.5, 0.5))
        scene.point_light(pos=(0.5, 1.5, 1.5), color=(1, 1, 1))
        
        scene.mesh(vertices, indices=indices, color=(0.9, 0.3, 0.3), two_sided=True)
        scene.particles(sphere_pos, radius=sphere_r, color=(0.4, 0.8, 0.4))
        
        canvas.scene(scene)
        window.show()

if __name__ == "__main__":
    run()