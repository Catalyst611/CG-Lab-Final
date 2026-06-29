# Work0: 万有引力粒子群仿真

## 1. 项目简介
本项目基于 GPU 加速实现了一个万有引力粒子群交互系统。包含 10,000 个粒子，支持鼠标引力交互与物理边界碰撞反弹效果。

## 2. 文件结构

```text
Work0/
├── __init__.py
├── config.py      # 参数配置中心
├── physics.py     # GPU 核心物理逻辑
├── main.py        # 程序入口与视图层
├── README.md      # 本文档
└── assets/        # 演示动图文件夹
    └── demo.gif
```

## 3. 运行方式
在项目**根目录**下（外层 `CG_LAB` 目录），执行以下命令以模块方式运行：

```bash
uv run python -m src.Work0.main
```

## 4. 效果展示
![Gravity Swarm Demo](./assets/demo.gif)

学号：202411998324
姓名：李佳澍
人工智能专业
