# 计算机图形学实验 (CG-Lab) 代码仓库

本仓库用于存放计算机图形学课程的所有实验作业代码，采用单一仓库多子目录 (Mono-repo) 结构进行管理。所有代码基于 Python 3.12+ 与 Taichi 框架编写。

## 🗂️ 项目文件结构

```text
CG_LAB/
├── pyproject.toml     <-- uv 项目配置文件
├── README.md          <-- 本说明文档
└── src/
    ├── Work0/         <-- 实验零：万有引力粒子群
    └── Work1/         <-- 实验一：3D空间坐标变换 (含旋转插值)
```

## 📚 作业目录

- [Work0: 万有引力粒子群仿真](./src/Work0)
-[Work1: 3D 空间坐标变换 (MVP)](./src/Work1)

## ⚙️ 全局运行环境

```bash
# 初始化并安装依赖
uv sync
```