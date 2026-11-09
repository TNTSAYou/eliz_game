# eliz_game

以《银魂》伊丽莎白为核心的 3D 角色项目。

> **当前阶段：v4 软壳（布料动态）**（17 网格 / 31,074 tris / 30 骨骼 / idle + run / 正面对比剪影 IoU 0.914）。
> 平台：Windows 11 x64，仓库 `D:\work\eliz_game`；Blender 4.5.15 LTS 便携版在 `D:\tools\blender-4.5.15-windows-x64\`。
> 产物：`art\blender\eliz_costume_v2.blend`、`art\exports\eliz_costume_v2.glb`（2.72 MB，内嵌绒面贴图）、`art\renders\v2_*.png`（11 张）、`art\renders\v4_run*.gif/mp4`（3/4、侧面、v3 对比）。

## 项目概念

这不是"一只实心白鸭子"，而是**玩偶服版**伊丽莎白：

```text
外层：白色长蛋形连体玩偶服（壳 + 双袖，一张网格）
中层：深色内衬 + 底口
内层：毛腿大叔的腿 + 腰胯
配件：黄色鸭蹼鞋、空白牌子
```

核心表演：

- **待机**：壳垂到鞋面，只看到白壳和鸭蹼鞋，看不到毛腿。
- **奔跑**：壳上弹约 0.265m，露出约 0.18m 的毛腿。
- **大动作/彩蛋**：壳再抬高可露出膝盖，但暂不做完整大叔脸。

## 当前文档

- [角色规格书 v1](docs/character_spec.md) —— 尺寸、分件、材质、绑定、动画、验收标准、v1 产出记录。
- [v2 优化规格书](docs/character_spec_v2.md) —— 5 条 review 意见的改造方案 + 实施记录（§15：偏差、验收、已知限制）。
- [会话交接文档](docs/HANDOFF.md) —— 项目背景、讨论结论、当前进度与已知限制。

## 目录结构

```text
eliz_game/
  docs/
    character_spec.md
    character_spec_v2.md
    HANDOFF.md
  art/
    refs/          # 参考图（版权说明见 art/refs/README.md）
    blender/       # eliz_costume_v2.blend（v1 保留）
    exports/       # eliz_costume_v2.glb（v1 保留）
    renders/       # v2_*：四视图 / 跑动 / 举牌 / 匹配 / 4 张近景
    textures/      # fabric_albedo / rough / normal（1K 可平铺）
  scripts/
    build_eliz_v2.py        # 建模 + 材质 + 绑定 + 动画 + 渲染 + 导出
    make_fabric_textures.py # 生成可平铺绒面贴图（numpy）
    render_v2_views.py      # 只重渲 v2_* 图
    verify_export_v2.py     # 重导入 GLB 并校验
    check_asset_v2.py       # 验收检查（拓扑/权重/壳腿隔离/遮挡/嘴型）
    compare_ref.py          # 与参考图的剪影 IoU / 逐行宽度
  tools/           # 临时脚本与裁剪图（不入库）
```

## v2 产出

| 文件 | 说明 |
|---|---|
| [eliz_costume_v2.blend](art/blender/eliz_costume_v2.blend) | 场景 + 13 骨骼 + 渲染相机灯光 |
| [eliz_costume_v2.glb](art/exports/eliz_costume_v2.glb) | 17 网格 + 13 骨骼 + `idle` / `run` + 3 张绒面贴图 |
| [v2_front.png](art/renders/v2_front.png) · [v2_side.png](art/renders/v2_side.png) · [v2_back.png](art/renders/v2_back.png) · [v2_three_quarter.png](art/renders/v2_three_quarter.png) | 四视图（正交） |
| [v2_run_reveal.png](art/renders/v2_run_reveal.png) | 壳抬起、露出毛腿 |
| [v2_sign_pose.png](art/renders/v2_sign_pose.png) | 牌子 / 袖口姿态检查 |
| [v2_front_match.png](art/renders/v2_front_match.png) | 与参考图同构图（600×885、黑底）的正面图 |
| [v2_detail_hem.png](art/renders/v2_detail_hem.png) · [v2_detail_armhole.png](art/renders/v2_detail_armhole.png) · [v2_detail_mouth.png](art/renders/v2_detail_mouth.png) · [v2_detail_fabric.png](art/renders/v2_detail_fabric.png) | 近景：下摆 / 袖窿 / 嘴 / 绒面 |
| [v2_wearer_cutaway.png](art/renders/v2_wearer_cutaway.png) | 剖面：外套里隐藏的"服内人"（验证服比人大） |

## 复现

```powershell
Set-Location D:\work\eliz_game
$B = "D:\tools\blender-4.5.15-windows-x64\blender.exe"

# 建模 + 渲染 + 导出（需要 art/textures 下的贴图；改了贴图先跑下一行）
python scripts\make_fabric_textures.py
& $B --background --factory-startup --python-exit-code 1 --python "scripts\build_eliz_v2.py"

# 校验 GLB（重导入，检查高度/骨骼/动画/面数/贴图）
& $B --background --factory-startup --python-exit-code 1 --python "scripts\verify_export_v2.py"

# 验收检查（拓扑/权重/壳腿隔离/下颌/待机遮挡/嘴缝弧线）
& $B --background --factory-startup --python-exit-code 1 --python "scripts\check_asset_v2.py"

# 与参考图比剪影
python scripts\compare_ref.py
```

## 下一步

1. 看 `art\renders\` 的渲染，重点把 `v2_front_match.png` 和 `art/refs/eliz_front.jpg` 并排看，再看 4 张近景。
2. 如果"拖地下摆 + 扁脚"的方向 OK，进入 v3.1：脚趾改尖蹼、下摆堆叠厚度、跑动抬升重调、袖窿/下摆线迹、鞋与嘴加绒。
3. 如果更看重和参考图的相似度，可继续收窄袖宽/调整头顶弧度（当前 IoU 0.914）。
4. 之后再排 `walk`/`jump`/`hit` 动画与引擎接入。

## 参考图

4 张参考图已放在 [`art/refs/`](art/refs/)，包括正面全身、动画截图、撑伞行走、举牌半身。

这些图片仅用于本项目内部的视觉参考，版权归原作者/版权方所有；**不要在公开仓库中再分发，也不要用于商业用途**。如果仓库是公开的，建议删除图片或只保留原始来源链接。详见 [`art/refs/README.md`](art/refs/README.md)。

## 版权说明

伊丽莎白是空知英秋/集英社《银魂》的角色。本项目用于个人学习、同人原型和非商业开发；商业化发行需要版权授权。
