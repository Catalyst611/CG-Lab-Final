# src/Work3/main.py
import taichi as ti

ti.init(arch=ti.gpu)

RES = 800
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))

# UI 材质参数 (全局 Field 以供 Kernel 读取)
ka = ti.field(dtype=ti.f32, shape=())
kd = ti.field(dtype=ti.f32, shape=())
ks = ti.field(dtype=ti.f32, shape=())
shininess = ti.field(dtype=ti.f32, shape=())

@ti.func
def intersect_sphere(ro, rd, center, radius):
    """计算射线与球体的交点及法向量"""
    oc = ro - center
    b = 2.0 * oc.dot(rd)
    c = oc.dot(oc) - radius**2
    delta = b**2 - 4.0 * c
    
    t = 1e10
    normal = ti.Vector([0.0, 0.0, 0.0])
    if delta > 0:
        t_temp = (-b - ti.math.sqrt(delta)) / 2.0
        if t_temp > 0:
            t = t_temp
            p = ro + t * rd
            normal = (p - center).normalized()
    return t, normal

@ti.func
def intersect_cone(ro, rd, apex, y_base, radius):
    """计算射线与圆锥体的交点及法向量"""
    h = apex.y - y_base
    k = (radius / h)**2
    oc = ro - apex
    
    a = rd.x**2 + rd.z**2 - k * rd.y**2
    b = 2.0 * (rd.x * oc.x + rd.z * oc.z - k * rd.y * oc.y)
    c = oc.x**2 + oc.z**2 - k * oc.y**2
    delta = b**2 - 4.0 * a * c
    
    t = 1e10
    normal = ti.Vector([0.0, 0.0, 0.0])
    if delta > 0:
        t1 = (-b - ti.math.sqrt(delta)) / (2.0 * a)
        t2 = (-b + ti.math.sqrt(delta)) / (2.0 * a)
        
        # 寻找在高度范围内的最小正数 t
        t_cand = 1e10
        for t_val in ti.static([t1, t2]):
            if t_val > 1e-4:
                py = ro.y + t_val * rd.y
                if y_base <= py <= apex.y:
                    t_cand = ti.min(t_cand, t_val)
                    
        # 检测圆锥底面 (平面 y = y_base)
        if ti.abs(rd.y) > 1e-4:
            t_base = (y_base - ro.y) / rd.y
            if t_base > 1e-4:
                pb = ro + t_base * rd
                if (pb.x - apex.x)**2 + (pb.z - apex.z)**2 <= radius**2:
                    t_cand = ti.min(t_cand, t_base)
                    
        if t_cand < 1e10:
            t = t_cand
            p = ro + t * rd
            if ti.abs(p.y - y_base) < 1e-3:
                normal = ti.Vector([0.0, -1.0, 0.0])
            else:
                nx = p.x - apex.x
                nz = p.z - apex.z
                ny = -k * (p.y - apex.y)
                normal = ti.Vector([nx, ny, nz]).normalized()
    return t, normal

@ti.kernel
def render():
    for i, j in pixels:
        u = (i + 0.5) / RES * 2.0 - 1.0
        v = (j + 0.5) / RES * 2.0 - 1.0
        
        ro = ti.Vector([0.0, 0.0, 5.0]) 
        screen_p = ti.Vector([u * 2.0, v * 2.0, 3.0])
        rd = (screen_p - ro).normalized() 
        
        #定义场景参数
        sphere_c, sphere_r, sphere_col = ti.Vector([-1.2, -0.2, 0.0]), 1.2, ti.Vector([0.8, 0.1, 0.1])
        cone_apex, cone_base_y, cone_r, cone_col = ti.Vector([1.2, 1.2, 0.0]), -1.4, 1.2, ti.Vector([0.6, 0.2, 0.8])
        bg_col = ti.Vector([0.0, 0.15, 0.2]) 
        light_pos, light_col = ti.Vector([2.0, 3.0, 4.0]), ti.Vector([1.0, 1.0, 1.0])
        
        # 深度测试 
        t_min = 1e10
        hit_norm = ti.Vector([0.0, 0.0, 0.0])
        hit_col = ti.Vector([0.0, 0.0, 0.0])
        
        ts, ns = intersect_sphere(ro, rd, sphere_c, sphere_r)
        if ts < t_min:
            t_min, hit_norm, hit_col = ts, ns, sphere_col
            
        tc, nc = intersect_cone(ro, rd, cone_apex, cone_base_y, cone_r)
        if tc < t_min:
            t_min, hit_norm, hit_col = tc, nc, cone_col
            
        #Phong着色
        if t_min < 1e9:
            p = ro + t_min * rd 
            
            L = (light_pos - p).normalized()
            V = (ro - p).normalized()
            N = hit_norm.normalized()
            
            # (1) 环境光 Ambient
            ambient = ka[None] * light_col * hit_col
            
            # (2) 漫反射 Diffuse (截断负值，避免照亮背面)
            diff_factor = ti.max(0.0, N.dot(L))
            diffuse = kd[None] * diff_factor * light_col * hit_col
            
            # (3) 镜面高光 Specular (基于理想反射向量 R)
            R = (2.0 * N.dot(L) * N - L).normalized()
            spec_factor = ti.max(0.0, R.dot(V)) ** shininess[None]
            specular = ks[None] * spec_factor * light_col
            color = ambient + diffuse + specular
            pixels[i, j] = ti.math.clamp(color, 0.0, 1.0)
        else:
            pixels[i, j] = bg_col

def run():
    window = ti.ui.Window("Work3: Phong Illumination", (RES, RES))
    canvas = window.get_canvas()
    gui = window.get_gui()
    ka[None], kd[None], ks[None], shininess[None] = 0.2, 0.7, 0.5, 32.0
    
    while window.running:
        render()
        canvas.set_image(pixels)
        with gui.sub_window("Material Settings", 0.02, 0.02, 0.35, 0.25):
            ka[None] = gui.slider_float("Ka (Ambient)", ka[None], 0.0, 1.0)
            kd[None] = gui.slider_float("Kd (Diffuse)", kd[None], 0.0, 1.0)
            ks[None] = gui.slider_float("Ks (Specular)", ks[None], 0.0, 1.0)
            shininess[None] = gui.slider_float("Shininess", shininess[None], 1.0, 128.0)
            
        window.show()

if __name__ == '__main__':
    run()