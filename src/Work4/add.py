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
    t, normal = 1e10, ti.Vector([0.0, 0.0, 0.0])
    if delta > 0:
        t_temp = (-b - ti.math.sqrt(delta)) / 2.0
        if t_temp > 1e-4:
            t = t_temp
            normal = (ro + t * rd - center).normalized()
        else:
            t_temp = (-b + ti.math.sqrt(delta)) / 2.0
            if t_temp > 1e-4:
                t = t_temp
                normal = (ro + t * rd - center).normalized()
    return t, normal

@ti.func
def intersect_plane(ro, rd, plane_y):
    t, normal = 1e10, ti.Vector([0.0, 1.0, 0.0])
    if ti.abs(rd.y) > 1e-4:
        t_temp = (plane_y - ro.y) / rd.y
        if t_temp > 1e-4: t = t_temp
    return t, normal

@ti.func
def map_scene(ro, rd):
    t_min = 1e10
    hit_norm, hit_col = ti.Vector([0.0,0.0,0.0]), ti.Vector([0.0,0.0,0.0])
    mat_id = 0 # 0:Bg, 1:Ground, 2:Glass, 3:Mirror
    
    ts1, ns1 = intersect_sphere(ro, rd, ti.Vector([-1.5, 0.0, 0.0]), 1.0)
    if ts1 < t_min: t_min, hit_norm, mat_id, hit_col = ts1, ns1, 2, ti.Vector([1.0, 1.0, 1.0])
        
    ts2, ns2 = intersect_sphere(ro, rd, ti.Vector([1.5, 0.0, 0.0]), 1.0)
    if ts2 < t_min: t_min, hit_norm, mat_id, hit_col = ts2, ns2, 3, ti.Vector([0.9, 0.9, 0.9])
        
    tp, np = intersect_plane(ro, rd, -1.0)
    if tp < t_min:
        p = ro + tp * rd
        cx, cz = ti.cast(ti.floor(p.x * 1.5), ti.i32), ti.cast(ti.floor(p.z * 1.5), ti.i32)
        col = ti.Vector([0.8, 0.8, 0.8]) if (cx + cz) % 2 == 0 else ti.Vector([0.2, 0.2, 0.2])
        t_min, hit_norm, mat_id, hit_col = tp, np, 1, col
    return t_min, hit_norm, mat_id, hit_col

@ti.kernel
def render():
    SAMPLES = 4
    for i, j in pixels:
        color_sum = ti.Vector([0.0, 0.0, 0.0])
        for _ in range(SAMPLES):
            u = (i + ti.random()) / RES * 2.0 - 1.0
            v = (j + ti.random()) / RES * 2.0 - 1.0
            
            ro = ti.Vector([0.0, 1.0, 5.0])
            rd = (ti.Vector([u * 2.0, v * 2.0, 3.0]) - ro).normalized()
            
            throughput = ti.Vector([1.0, 1.0, 1.0])
            cur_color = ti.Vector([0.0, 0.0, 0.0])
            
            for bounce in range(max_bounces[None]):
                t, N, mat_id, col = map_scene(ro, rd)
                if mat_id == 0:
                    cur_color += throughput * ti.Vector([0.1, 0.15, 0.2])
                    break
                p = ro + t * rd
                
                if mat_id == 1:
                    L = (light_pos[None] - p).normalized()
                    # 修复处：使用不同的变量名代替连续使用 _
                    t_shad, norm_dummy, mat_dummy, col_dummy = map_scene(p + N * 1e-4, L)
                    in_shadow = t_shad < (light_pos[None] - p).norm()
                    ambient = 0.2 * col
                    diffuse = ti.Vector([0.0, 0.0, 0.0])
                    if not in_shadow: diffuse = 0.8 * ti.max(0.0, N.dot(L)) * col
                    cur_color += throughput * (ambient + diffuse)
                    break
                    
                elif mat_id == 3:
                    rd = (rd - 2.0 * rd.dot(N) * N).normalized()
                    ro = p + N * 1e-4
                    throughput *= 0.8
                    
                elif mat_id == 2:
                    cosi = rd.dot(N)
                    etai, etat = 1.0, 1.5
                    n = N
                    if cosi < 0:
                        cosi = -cosi
                    else:
                        etai, etat = etat, etai
                        n = -N
                        
                    eta = etai / etat
                    k = 1.0 - eta**2 * (1.0 - cosi**2)
                    if k < 0.0:
                        rd = (rd - 2.0 * rd.dot(n) * n).normalized()
                        ro = p + n * 1e-4
                    else:
                        rd = (eta * rd + (eta * cosi - ti.math.sqrt(k)) * n).normalized()
                        ro = p - n * 1e-4
                        throughput *= 0.9
                        
            color_sum += cur_color
        pixels[i, j] = ti.math.clamp(color_sum / SAMPLES, 0.0, 1.0)

def run():
    window = ti.ui.Window("Work4 Bonus: Refraction & MSAA", (RES, RES))
    canvas = window.get_canvas()
    gui = window.get_gui()
    light_pos[None] =[0.0, 5.0, 2.0]
    max_bounces[None] = 4
    
    while window.running:
        render()
        canvas.set_image(pixels)
        with gui.sub_window("Settings", 0.02, 0.02, 0.35, 0.2):
            light_pos[None][0] = gui.slider_float("Light X", light_pos[None][0], -5.0, 5.0)
            light_pos[None][1] = gui.slider_float("Light Y", light_pos[None][1],  1.0, 10.0)
            light_pos[None][2] = gui.slider_float("Light Z", light_pos[None][2], -5.0, 5.0)
            max_bounces[None] = gui.slider_int("Max Bounces", max_bounces[None], 1, 5)
        window.show()

if __name__ == '__main__':
    run()