import taichi as ti

ti.init(arch=ti.gpu)
RES = 800
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))

light_pos = ti.Vector.field(3, dtype=ti.f32, shape=())
max_bounces = ti.field(dtype=ti.i32, shape=())

@ti.func
def intersect_sphere(ro, rd, center, radius):
    oc = ro - center
    b = 2.0 * oc.dot(rd)
    c = oc.dot(oc) - radius**2
    delta = b**2 - 4.0 * c
    t = 1e10
    normal = ti.Vector([0.0, 0.0, 0.0])
    if delta > 0:
        t_temp = (-b - ti.math.sqrt(delta)) / 2.0
        if t_temp > 1e-4:
            t = t_temp
            p = ro + t * rd
            normal = (p - center).normalized()
    return t, normal

@ti.func
def intersect_plane(ro, rd, plane_y):
    t = 1e10
    normal = ti.Vector([0.0, 1.0, 0.0])
    if ti.abs(rd.y) > 1e-4:
        t_temp = (plane_y - ro.y) / rd.y
        if t_temp > 1e-4: t = t_temp
    return t, normal

@ti.func
def map_scene(ro, rd):
    t_min = 1e10
    hit_norm = ti.Vector([0.0, 0.0, 0.0])
    mat_id = 0  # 0:Background, 1:Ground(Diffuse), 2:Red Sphere(Diffuse), 3:Mirror Sphere
    hit_col = ti.Vector([0.0, 0.0, 0.0])

    #红色漫反射球
    ts1, ns1 = intersect_sphere(ro, rd, ti.Vector([-1.5, 0.0, 0.0]), 1.0)
    if ts1 < t_min:
        t_min, hit_norm, mat_id, hit_col = ts1, ns1, 2, ti.Vector([0.8, 0.2, 0.2])

    #银色镜面球
    ts2, ns2 = intersect_sphere(ro, rd, ti.Vector([1.5, 0.0, 0.0]), 1.0)
    if ts2 < t_min:
        t_min, hit_norm, mat_id, hit_col = ts2, ns2, 3, ti.Vector([0.9, 0.9, 0.9])

    tp, np = intersect_plane(ro, rd, -1.0)
    if tp < t_min:
        p = ro + tp * rd
        # 棋盘格纹理计算
        cx = ti.cast(ti.floor(p.x * 1.5), ti.i32)
        cz = ti.cast(ti.floor(p.z * 1.5), ti.i32)
        col = ti.Vector([0.8, 0.8, 0.8]) if (cx + cz) % 2 == 0 else ti.Vector([0.2, 0.2, 0.2])
        t_min, hit_norm, mat_id, hit_col = tp, np, 1, col

    return t_min, hit_norm, mat_id, hit_col

@ti.kernel
def render():
    for i, j in pixels:
        u = (i + 0.5) / RES * 2.0 - 1.0
        v = (j + 0.5) / RES * 2.0 - 1.0
        
        ro = ti.Vector([0.0, 1.0, 5.0])
        rd = (ti.Vector([u * 2.0, v * 2.0, 3.0]) - ro).normalized()
        
        throughput = ti.Vector([1.0, 1.0, 1.0])
        final_color = ti.Vector([0.0, 0.0, 0.0])
        
        # 迭代光线弹射
        for bounce in range(max_bounces[None]):
            t, N, mat_id, col = map_scene(ro, rd)
            
            if mat_id == 0: # 击中背景
                final_color += throughput * ti.Vector([0.1, 0.15, 0.2])
                break
                
            p = ro + t * rd
            
            if mat_id == 1 or mat_id == 2: # 漫反射材质 (地面或红球)
                L = (light_pos[None] - p).normalized()
                
                p_offset = p + N * 1e-4
                t_shadow, _, shadow_mat, _ = map_scene(p_offset, L)
                dist_to_light = (light_pos[None] - p).norm()
                in_shadow = t_shadow < dist_to_light
                
                ambient = 0.2 * col
                diffuse = ti.Vector([0.0, 0.0, 0.0])
                if not in_shadow:
                    diffuse = 0.8 * ti.max(0.0, N.dot(L)) * col
                
                final_color += throughput * (ambient + diffuse)
                break 
                
            elif mat_id == 3: 
                rd = (rd - 2.0 * rd.dot(N) * N).normalized()
                ro = p + N * 1e-4 
                throughput *= 0.8 
                
        pixels[i, j] = ti.math.clamp(final_color, 0.0, 1.0)

def run():
    window = ti.ui.Window("Work4: Ray Tracing", (RES, RES))
    canvas = window.get_canvas()
    gui = window.get_gui()
    
    light_pos[None] =[0.0, 5.0, 2.0]
    max_bounces[None] = 3
    
    while window.running:
        render()
        canvas.set_image(pixels)
        
        with gui.sub_window("Ray Tracing Settings", 0.02, 0.02, 0.35, 0.2):
            light_pos[None][0] = gui.slider_float("Light X", light_pos[None][0], -5.0, 5.0)
            light_pos[None][1] = gui.slider_float("Light Y", light_pos[None][1],  1.0, 10.0)
            light_pos[None][2] = gui.slider_float("Light Z", light_pos[None][2], -5.0, 5.0)
            max_bounces[None] = gui.slider_int("Max Bounces", max_bounces[None], 1, 5)
            
        window.show()

if __name__ == '__main__':
    run()