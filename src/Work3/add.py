import taichi as ti
from .main import intersect_sphere, intersect_cone

ti.init(arch=ti.gpu)

RES = 800
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))

ka = ti.field(dtype=ti.f32, shape=())
kd = ti.field(dtype=ti.f32, shape=())
ks = ti.field(dtype=ti.f32, shape=())
shininess = ti.field(dtype=ti.f32, shape=())

@ti.kernel
def render_bonus():
    for i, j in pixels:
        u = (i + 0.5) / RES * 2.0 - 1.0
        v = (j + 0.5) / RES * 2.0 - 1.0
        ro = ti.Vector([0.0, 0.0, 5.0])
        screen_p = ti.Vector([u * 2.0, v * 2.0, 3.0])
        rd = (screen_p - ro).normalized()
        
        sphere_c, sphere_r, sphere_col = ti.Vector([-1.2, -0.2, 0.0]), 1.2, ti.Vector([0.8, 0.1, 0.1])
        cone_apex, cone_base_y, cone_r, cone_col = ti.Vector([1.2, 1.2, 0.0]), -1.4, 1.2, ti.Vector([0.6, 0.2, 0.8])
        bg_col = ti.Vector([0.0, 0.15, 0.2])
        light_pos, light_col = ti.Vector([2.0, 3.0, 4.0]), ti.Vector([1.0, 1.0, 1.0])
        
        t_min = 1e10
        hit_norm = ti.Vector([0.0, 0.0, 0.0])
        hit_col = ti.Vector([0.0, 0.0, 0.0])
        
        ts, ns = intersect_sphere(ro, rd, sphere_c, sphere_r)
        if ts < t_min: t_min, hit_norm, hit_col = ts, ns, sphere_col
            
        tc, nc = intersect_cone(ro, rd, cone_apex, cone_base_y, cone_r)
        if tc < t_min: t_min, hit_norm, hit_col = tc, nc, cone_col
            
        if t_min < 1e9:
            p = ro + t_min * rd
            L = (light_pos - p).normalized()
            V = (ro - p).normalized()
            N = hit_norm.normalized()
            ro_shadow = p + N * 1e-3
            dist_to_light = (light_pos - p).norm()
            in_shadow = False
            
            t_s, _ = intersect_sphere(ro_shadow, L, sphere_c, sphere_r)
            if t_s < dist_to_light: in_shadow = True
            
            t_c, _ = intersect_cone(ro_shadow, L, cone_apex, cone_base_y, cone_r)
            if t_c < dist_to_light: in_shadow = True
            ambient = ka[None] * light_col * hit_col
            diffuse = ti.Vector([0.0, 0.0, 0.0])
            specular = ti.Vector([0.0, 0.0, 0.0])
            
            if not in_shadow:
                diff_factor = ti.max(0.0, N.dot(L))
                diffuse = kd[None] * diff_factor * light_col * hit_col
                H = (L + V).normalized()
                spec_factor = ti.max(0.0, N.dot(H)) ** shininess[None]
                specular = ks[None] * spec_factor * light_col
                
            color = ambient + diffuse + specular
            pixels[i, j] = ti.math.clamp(color, 0.0, 1.0)
        else:
            pixels[i, j] = bg_col

def run():
    window = ti.ui.Window("Work3 Bonus: Blinn-Phong & Hard Shadow", (RES, RES))
    canvas = window.get_canvas()
    gui = window.get_gui()
    ka[None], kd[None], ks[None], shininess[None] = 0.2, 0.7, 0.5, 32.0
    
    while window.running:
        render_bonus()
        canvas.set_image(pixels)
        with gui.sub_window("Material Settings", 0.02, 0.02, 0.35, 0.25):
            ka[None] = gui.slider_float("Ka (Ambient)", ka[None], 0.0, 1.0)
            kd[None] = gui.slider_float("Kd (Diffuse)", kd[None], 0.0, 1.0)
            ks[None] = gui.slider_float("Ks (Specular)", ks[None], 0.0, 1.0)
            shininess[None] = gui.slider_float("Shininess", shininess[None], 1.0, 128.0)
        window.show()

if __name__ == '__main__':
    run()