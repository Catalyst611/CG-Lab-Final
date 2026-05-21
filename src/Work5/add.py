import os
import urllib.request
import torch
import imageio
import numpy as np
from tqdm import tqdm

from pytorch3d.io import load_objs_as_meshes
from pytorch3d.utils import ico_sphere
from pytorch3d.loss import mesh_edge_loss, mesh_laplacian_smoothing, mesh_normal_consistency
from pytorch3d.renderer import (
    look_at_view_transform, FoVPerspectiveCameras, PointLights, 
    RasterizationSettings, MeshRenderer, MeshRasterizer, 
    SoftPhongShader, SoftSilhouetteShader, BlendParams
)
from pytorch3d.structures import Meshes
from pytorch3d.renderer.mesh.textures import TexturesVertex

def download_textured_data():
    os.makedirs("src/Work5/data", exist_ok=True)
    urls = {
        "cow.obj": "https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/docs/tutorials/data/cow_mesh/cow.obj",
        "cow.mtl": "https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/docs/tutorials/data/cow_mesh/cow.mtl",
        "cow_texture.png": "https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/docs/tutorials/data/cow_mesh/cow_texture.png"
    }
    for filename, url in urls.items():
        filepath = os.path.join("src/Work5/data", filename)
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, filepath)

def run():
    download_textured_data()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    target_mesh = load_objs_as_meshes(["src/Work5/data/cow.obj"], device=device)

    num_views = 20
    R, T = look_at_view_transform(dist=2.7, elev=0, azim=torch.linspace(-180, 180, num_views))
    cameras = FoVPerspectiveCameras(device=device, R=R, T=T)
    lights = PointLights(device=device, location=[[0.0, 0.0, -3.0]])

    raster_settings = RasterizationSettings(image_size=256, blur_radius=0.0, faces_per_pixel=1)
    raster_settings_soft = RasterizationSettings(image_size=256, blur_radius=1e-4, faces_per_pixel=50)

    renderer_rgb = MeshRenderer(
        rasterizer=MeshRasterizer(cameras=cameras, raster_settings=raster_settings),
        shader=SoftPhongShader(device=device, cameras=cameras, lights=lights)
    )
    renderer_silhouette = MeshRenderer(
        rasterizer=MeshRasterizer(cameras=cameras, raster_settings=raster_settings_soft),
        shader=SoftSilhouetteShader()
    )

    target_meshes = target_mesh.extend(num_views)
    target_rgb = renderer_rgb(meshes_world=target_meshes)[..., :3]
    target_sil = renderer_silhouette(meshes_world=target_meshes)[..., 3]

    src_mesh = ico_sphere(4, device)
    src_verts, src_faces = src_mesh.get_mesh_verts_faces(0)
    
    deform_verts = torch.full(src_verts.shape, 0.0, device=device, requires_grad=True)
    sphere_verts_rgb = torch.full(src_verts.shape, 0.5, device=device, requires_grad=True) # 初始灰色
    
    optimizer = torch.optim.SGD([deform_verts, sphere_verts_rgb], lr=1.0, momentum=0.9)

    loop = tqdm(range(500))
    frames = []

    for i in loop:
        optimizer.zero_grad()

        new_src_mesh = src_mesh.offset_verts(deform_verts)
        new_src_mesh.textures = TexturesVertex(verts_features=[sphere_verts_rgb])

        pred_meshes = new_src_mesh.extend(num_views)
        pred_rgb = renderer_rgb(meshes_world=pred_meshes)[..., :3]
        pred_sil = renderer_silhouette(meshes_world=pred_meshes)[..., 3]

        loss_rgb = ((pred_rgb - target_rgb) ** 2).mean()
        loss_sil = ((pred_sil - target_sil) ** 2).mean()
        loss_edge = mesh_edge_loss(new_src_mesh)
        loss_normal = mesh_normal_consistency(new_src_mesh)
        loss_laplacian = mesh_laplacian_smoothing(new_src_mesh, method="uniform")
        
        loss = loss_rgb * 1.0 + loss_sil * 1.0 + loss_edge * 1.0 + loss_normal * 0.01 + loss_laplacian * 0.1
        
        loss.backward()
        optimizer.step()

        with torch.no_grad():
            sphere_verts_rgb.clamp_(0.0, 1.0)
            
        loop.set_description(f"Loss: {loss.item():.4f}")

        if i % 20 == 0 or i == 499:
            with torch.no_grad():
                img = renderer_rgb(meshes_world=new_src_mesh.extend(1), cameras=FoVPerspectiveCameras(device=device, R=R[0:1], T=T[0:1]))
                img = img[0, ..., :3].cpu().numpy()
                frames.append((img * 255).astype(np.uint8))

    os.makedirs("src/Work5/assets", exist_ok=True)
    imageio.mimsave("src/Work5/assets/rgb_opt.gif", frames, fps=10)
    print("Bonus Optimization finished! GIF saved to src/Work5/assets/rgb_opt.gif")

if __name__ == '__main__':
    run()