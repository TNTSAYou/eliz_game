# eliz_game

以《银魂》伊丽莎白为核心的 3D 角色项目。

> **当前阶段：v1 blockout 已生成**（22 个网格对象 / 9,204 tris / 13 骨骼 / idle + run 两个动作 / 正面对比剪影 IoU 0.92）。
> 平台：Windows 11 x64，仓库 `D:\work\eliz_game`；Blender 4.5.15 LTS 便携版在 `D:\tools\blender-4.5.15-windows-x64\`。
> 产物：`art\blender\eliz_costume_v1.blend`、`art\exports\eliz_costume_v1.glb`、`art\renders\v1_*.png`（7 张，含对齐参考图的 `v1_front_match.png`）。

## 项目概念

这不是“一只实心白鸭子”，而是**玩偶服版**伊丽莎白：

```text
外层：白色长蛋形连体玩偶服（壳）
中层：深色内衬 + 底口
内层：毛腿大叔的腿 + 腰胯
配件：黄色鸭蹼鞋、空白牌子
```

核心表演：

- **待机**：壳垂到鞋面，只看到白壳和鸭蹼鞋，看不到毛腿。
- **奔跑**：壳上弹约 17cm，露出 15cm 以上的毛腿。
- **大动作/彩蛋**：壳抬到约 0.50m，露出膝盖，但暂不做完整大叔脸。

## 当前文档

- [角色规格书 v0.1](docs/character_spec.md) —— 尺寸、分件、材质、绑定、动画、验收标准、待决策项与 v1 产出记录。
- [会话交接文档](docs/HANDOFF.md) —— 项目背景、讨论结论、当前进度与已知限制。

## 目录结构

```text
eliz_game/
  docs/
    character_spec.md
    HANDOFF.md
  art/
    refs/          # 参考图（版权说明见 art/refs/README.md）
    blender/       # eliz_costume_v1.blend
    exports/       # eliz_costume_v1.glb
    renders/       # v1_front / side / back / three_quarter / run_reveal / sign_pose
  scripts/
    build_eliz_v1.py   # 建模 + 渲染 + 导出
    render_views.py    # 只重渲 v1_* 图
    verify_export.py   # 重导入 GLB 并校验
    check_asset.py     # 验收检查（拓扑/权重/壳腿隔离/遮挡）
  tools/           # Blender 便携版解压目录（不入库）
```

## v1 产出

| 文件 | 说明 |
|---|---|
| [eliz_costume_v1.blend](art/blender/eliz_costume_v1.blend) | 场景 + 13 骨骼 + 渲染相机灯光 |
| [eliz_costume_v1.glb](art/exports/eliz_costume_v1.glb) | 22 网格 + 13 骨骼 + `idle` / `run` 动画 |
| [v1_front.png](art/renders/v1_front.png) · [v1_side.png](art/renders/v1_side.png) · [v1_back.png](art/renders/v1_back.png) · [v1_three_quarter.png](art/renders/v1_three_quarter.png) | 四视图（正交） |
| [v1_run_reveal.png](art/renders/v1_run_reveal.png) | 壳抬起、露出毛腿 |
| [v1_sign_pose.png](art/renders/v1_sign_pose.png) | 牌子 / 袖口姿态检查 |
| [v1_front_match.png](art/renders/v1_front_match.png) | 与参考图同构图（600×885、黑底）的正面图 |

## 复现

```powershell
Set-Location D:\work\eliz_game
$B = "D:\tools\blender-4.5.15-windows-x64\blender.exe"

# 建模 + 渲染 + 导出
& $B --background --factory-startup --python-exit-code 1 --python "scripts\build_eliz_v1.py"

# 校验 GLB（重导入，检查高度/骨骼/动画/面数）
& $B --background --factory-startup --python-exit-code 1 --python "scripts\verify_export.py"

# 验收检查（拓扑/权重/壳腿隔离/下颌/待机遮挡）
& $B --background --factory-startup --python-exit-code 1 --python "scripts\check_asset.py"

# 只重渲，不重建
& $B --background --factory-startup --python-exit-code 1 --python "scripts\render_views.py"
```

## 下一步

1. 看 `art\renders\` 的 7 张图，重点把 `v1_front_match.png` 和 `art/refs/eliz_front.jpg` 并排看。
2. 按反馈改 `scripts\build_eliz_v1.py` 顶部的尺寸常量，重跑即可复现。
3. v1.5：鸭蹼脚型、牌子握持、眼睑/眨眼、赛璐璐描边与布料质感、`walk`/`jump`/`hit` 动画。

## 参考图

4 张参考图已放在 [`art/refs/`](art/refs/)，包括正面全身、动画截图、撑伞行走、举牌半身。

这些图片仅用于本项目内部的视觉参考，版权归原作者/版权方所有；**不要在公开仓库中再分发，也不要用于商业用途**。如果仓库是公开的，建议删除图片或只保留原始来源链接。详见 [`art/refs/README.md`](art/refs/README.md)。

## 版权说明

伊丽莎白是空知英秋/集英社《银魂》的角色。本项目用于个人学习、同人原型和非商业开发；商业化发行需要版权授权。
