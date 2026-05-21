# 计算机图形学实验 (CG-Lab) 代码仓库

本仓库用于存放计算机图形学课程的所有实验作业代码，采用单一仓库多子目录 (Mono-repo) 结构进行管理。代码主要基于 Python 3.12+ 与 Taichi 框架编写（部分逆向渲染作业基于 PyTorch3D）。

## 🗂️ 项目文件结构
```text
CG_LAB/
├── pyproject.toml
├── README.md
└── src/
    ├── Work0/         <-- 实验零：万有引力粒子群
    ├── Work1/         <-- 实验一：3D空间坐标变换 (MVP)
    ├── Work2/         <-- 实验二：贝塞尔曲线与光栅化基础
    ├── Work3/         <-- 实验三：局部光照模型与交互式渲染
    ├── Work4/         <-- 实验四：光线追踪 (Ray Tracing)
    ├── Work5/         <-- 实验五：可微光栅化与网格优化
    └── Work6/         <-- 实验六：质点弹簧模型与数值积分
```

## 📚 作业直达链接
- [Work0: 万有引力粒子群仿真](./src/Work0)
- [Work1: 3D 空间坐标变换 (MVP)](./src/Work1)
- [Work2: 贝塞尔曲线与光栅化基础](./src/Work2)
- [Work3: 局部光照模型与交互式渲染](./src/Work3)
- [Work4: 光线追踪 (Ray Tracing)](./src/Work4)
- [Work5: 可微光栅化与网格优化](./src/Work5)
- [Work6: 质点弹簧模型与数值求解器](./src/Work6)