import os
import urllib.request
import torch
import imageio
import numpy as np
from tqdm import tqdm

# PyTorch3D 导入
from pytorch3d.io import load_objs_as_meshes
from pytorch3d.utils import ico_sphere
from pytorch3d.loss import mesh_edge_loss, mesh_laplacian_smoothing, mesh_normal_consistency
from pytorch3d.renderer import (
    look_at_view_transform, FoVPerspectiveCameras, 
    RasterizationSettings, MeshRenderer, MeshRasterizer, 
    SoftSilhouetteShader, BlendParams
)

def download_data():
    os.makedirs("src/Work5/data", exist_ok=True)
    urls = {
        "cow.obj": "https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/docs/tutorials/data/cow_mesh/cow.obj",
    }
    for filename, url in urls.items():
        filepath = os.path.join("src/Work5/data", filename)
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, filepath)

def run():
    download_data()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    target_mesh = load_objs_as_meshes(["src/Work5/data/cow.obj"], device=device)

    num_views = 20
    elev = torch.linspace(0, 0, num_views)
    azim = torch.linspace(-180, 180, num_views)
    R, T = look_at_view_transform(dist=2.7, elev=elev, azim=azim)
    cameras = FoVPerspectiveCameras(device=device, R=R, T=T)

    blend_params = BlendParams(sigma=1e-4, gamma=1e-4)
    raster_settings = RasterizationSettings(
        image_size=256, blur_radius=np.log(1. / 1e-4 - 1.) * blend_params.sigma, faces_per_pixel=50
    )
    renderer_silhouette = MeshRenderer(
        rasterizer=MeshRasterizer(cameras=cameras, raster_settings=raster_settings),
        shader=SoftSilhouetteShader(blend_params=blend_params)
    )

    target_silhouette = renderer_silhouette(meshes_world=target_mesh.extend(num_views))
    target_silhouette = target_silhouette[..., 3]  

    src_mesh = ico_sphere(4, device)
    src_verts, src_faces = src_mesh.get_mesh_verts_faces(0)


    deform_verts = torch.full(src_verts.shape, 0.0, device=device, requires_grad=True)
    optimizer = torch.optim.SGD([deform_verts], lr=1.0, momentum=0.9)

    w_silhouette = 1.0
    w_edge = 1.0
    w_normal = 0.01
    w_laplacian = 0.1

    loop = tqdm(range(500))
    frames = []

    for i in loop:
        optimizer.zero_grad()
       
        new_src_mesh = src_mesh.offset_verts(deform_verts)

        rendered_silhouette = renderer_silhouette(meshes_world=new_src_mesh.extend(num_views))
        rendered_silhouette = rendered_silhouette[..., 3]

        loss_silhouette = ((rendered_silhouette - target_silhouette) ** 2).mean()
        loss_edge = mesh_edge_loss(new_src_mesh)
        loss_normal = mesh_normal_consistency(new_src_mesh)
        loss_laplacian = mesh_laplacian_smoothing(new_src_mesh, method="uniform")
        
        loss = (loss_silhouette * w_silhouette + 
                loss_edge * w_edge + 
                loss_normal * w_normal + 
                loss_laplacian * w_laplacian)
        
        loss.backward()
        optimizer.step()
        
        loop.set_description(f"Loss: {loss.item():.4f}")

        if i % 20 == 0 or i == 499:
            with torch.no_grad():
                demo_mesh = new_src_mesh.extend(1)
                img = renderer_silhouette(meshes_world=demo_mesh, cameras=FoVPerspectiveCameras(device=device, R=R[0:1], T=T[0:1]))
                img = img[0, ..., 3].cpu().numpy()
                img = (img * 255).astype(np.uint8)
                frames.append(img)

    os.makedirs("src/Work5/assets", exist_ok=True)
    imageio.mimsave("src/Work5/assets/silhouette_opt.gif", frames, fps=10)
    print("Optimization finished! GIF saved to src/Work5/assets/silhouette_opt.gif")

if __name__ == '__main__':
    run()