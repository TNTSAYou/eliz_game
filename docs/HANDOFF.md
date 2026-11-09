# 伊丽莎白项目 · 会话交接文档（Windows 版）

> 最后更新：2026-11-09（Asia/Shanghai）
> 项目目录：`D:\work\eliz_game`（原 macOS 路径 `/Users/wzh/work/eliz_game` 已废弃）
> 平台：**Windows 11 IoT 企业版 LTSC 10.0.26100（24H2），x64**
> 当前阶段：**v2 玩偶服改造已落地（一体化袖、下摆/鞋、嘴弧线、短毛绒材质），脚本 + GLB + 11 张渲染齐全**
> 阻塞点：**v2 已通过全部结构/遮挡/嘴型验收；剪影 IoU 0.909 < 0.93 门槛，待用户判断是收形还是接受"胖 3%"**

---

## 0. 快速状态

- 目标：用 **Blender（Tripo 仅作可选辅助）** 制作《银魂》伊丽莎白的 3D 角色，采用 **"玩偶服版"** 设定。
- 核心画面：平时是白色长蛋形玩偶服，只露出黄色鸭蹼鞋；**奔跑时外壳上弹，露出里面的毛腿大叔腿**。
- 已确定：外壳、底口、内衬、鸭蹼鞋、毛腿、绑定方案、尺寸和验收标准；外壳直接在 Blender 里建（Tripo 只做可选辅助）。
- 环境现状：Windows 11 x64；仓库 `D:\work\eliz_game`；Blender 4.5.15 LTS 便携版在 `D:\tools\blender-4.5.15-windows-x64\`。
- 当前进度：**v2**：17 个网格、29,346 tris、13 根骨骼、`idle`/`run`；`.blend` + `.glb`（2.67 MB，内嵌绒面贴图）+ 11 张渲染（含 4 张近景与参考图匹配图）；剪影 IoU 0.909。
- 下一步：用户看 `v2_front_match.png`、`v2_three_quarter.png` 与 4 张近景；确认"厚袖/大鞋"的观感，决定是否为了 IoU 再收形，或进入 v2.1（线迹、嘴部加密、鞋/嘴加绒）。
- 决策已定：D1 = 嘴缝两端下垂（∩）、D2 = 白色短毛绒；D3 = 24–30k + 1K 贴图；D4 = 服内人偶（待补）。

---

## 1. 项目背景

用户想做一个以伊丽莎白为主题的游戏，但当前阶段**先不考虑游戏引擎和玩法**，只考虑角色建模流程。

最初考虑的是“Tripo 生成草稿 → Blender 清理 → 进游戏引擎”。经过讨论后，目标收窄为：

1. 先做一个**玩偶服版**的伊丽莎白模型。
2. 外壳要能开底口，里面藏毛腿。
3. 跑步时外壳上弹，露出毛腿。
4. 使用 **Tripo + Blender**，但以 Blender 为主。
5. 当前只做到 Blender 资产和导出，不做游戏逻辑。

用户明确表示：

> “玩偶服版更符合我的想象，在奔跑运动时会露出毛腿之类的；我们先不考虑游戏，我们先考虑 Tripo + Blender 建模的流程。”

因此，后文所有设计都围绕“玩偶服 + 跑动露腿”展开，不再讨论“实心鸭子/生物版”。

项目最初在 **macOS** 上启动，文档全部按 macOS 写（`/Users/wzh/...`、Homebrew、`/Applications/Blender.app`）。工作机已切换到 **Windows 11**，因此本文件与 `docs/character_spec.md` 已整体改写为 Windows 版本：路径、安装方式、命令、验证步骤全部按本机实测重写，设计内容不变。

---

## 2. 环境与资产现状

### 2.1 环境（实测）

| 项 | 值 | 备注 |
|---|---|---|
| 操作系统 | Windows 11 IoT 企业版 LTSC，10.0.26100（24H2），x64 | 不是 macOS；所有 macOS 命令作废 |
| CPU | Intel Core i5-13500H，12 核 16 线程 | 后台渲染可吃满 |
| 内存 | 16 GB（可用约 15.7 GB） | 够跑 8k–12k tris 的 blockout |
| GPU | Intel Iris Xe Graphics（集显，共享显存约 2GB，驱动 32.0.101.6733） | 支持 OpenGL 4.6，可用 EEVEE Next；不要开高细分/4K 贴图 |
| 磁盘 | C: 剩余约 85 GB；D: 剩余约 287 GB | 仓库在 D:，Blender 便携版也放 D: |
| Shell | Windows PowerShell 5.1 | 命令按 PS 5.1 语法写，不用 bash 语法 |
| Git | 2.56.0.windows.4，`C:\Program Files\Git\cmd\git.exe` | **不在 PATH**，需全路径调用 |
| Git 身份 | **未配置**（system/local/global 都没有 `user.name`/`user.email`） | 提交前必须先设置 |
| Python（系统） | 3.14.7，`C:\Python314\python.exe` | 只用于辅助脚本；**不能 `import bpy`** |
| Python（Blender 内置） | 3.11（随 Blender 4.5） | 建模脚本在 Blender 内运行 |
| Chocolatey | 2.7.4 | 其 `blender` 包当前是 5.2.3，**不满足 4.5 LTS 基线**，不作为首选渠道 |
| Blender | **已安装** `D:\tools\blender-4.5.15-windows-x64\blender.exe` | 4.5.15 LTS（build 2026-10-22），SHA256 已校验，`--version` 通过 |
| Unity / Godot / Unreal | **未安装** | 当前阶段不需要 |
| Tripo | 尚未登录，无 API key | 助手无法直接操作其账号 |

### 2.2 本地参考图

参考图已入库，唯一权威副本是仓库内的 `art/refs/`（原 macOS 路径 `/Users/wzh/Downloads/eliz_pic` 在当前机器上不存在）：

| 文件 | 内容 | 用途 |
|---|---|---|
| [`eliz_front.jpg`](../art/refs/eliz_front.jpg) | 200×295，黑底，正面全身 | **主比例参考**；适合做正视图 |
| [`eliz_anime.jpg`](../art/refs/eliz_anime.jpg) | 491×407，动画截图，暖金背景 | 看鸭蹼、脚趾、暖光下的白壳颜色 |
| [`eliz_umbrella.png`](../art/refs/eliz_umbrella.png) | 425×470，3/4 撑红伞行走 | 看抓握、重心、动态；棋盘格是烘进画面的，无 alpha |
| [`eliz_sign.webp`](../art/refs/eliz_sign.webp) | 1000×749，举空白牌子半身 | 看牌子和手臂；白底，不适合直接做透明素材 |

### 2.3 工作区

```text
D:\work\eliz_game\
  .git\                 ← 已初始化，main 与 origin/main 同步
  .gitignore
  README.md
  docs\
    HANDOFF.md          ← 本文件（Windows 版）
    character_spec.md   ← 角色规格书 v0.1（Windows 版）
  art\
    refs\               ← 4 张参考图（已入库）
    blender\            ← eliz_costume_v1.blend（已生成）
    exports\            ← eliz_costume_v1.glb（已生成，313 KB）
    renders\            ← v1_front/side/back/three_quarter/run_reveal/sign_pose.png（已生成）
  scripts\              ← build_eliz_v1.py / render_views.py / verify_export.py / check_asset.py（已生成）
```

Git 现状（实测）：

- 远程：`git@github.com:TNTSAYou/eliz_game.git`（origin）。
- 分支：`main`，与 `origin/main` 同步。
- 提交：`d2fc2f2`（初始化规格书/README/参考图）、`692f4a5`（记录仓库初始化状态）。
- 未提交改动：v1 建模脚本、文档更新与 `art\` 产物尚未提交（本机未配置 Git 身份）。

---

## 3. 角色理解

### 3.1 原作中的伊丽莎白

- 桂小太郎的宠物兼攘夷伙伴，坂本辰马送给桂的宇宙生物。
- 外表像巨大的白色企鹅/鸭子；官方资料设定身高 **180cm**、体重 **123kg**、生日 **9 月 7 日**。
- 日常用**写字板**交流；其实能说话；牌子也能当武器/盾牌。
- 战斗力很强：踢回火箭炮、眼睛发激光、嘴里伸火炮/钻头、可当降落伞。
- “中身”是作品反复玩的梗，不是单一答案：
  1. 初登场就露过毛腿；嘴张开时里面是人形 + 发光眼。
  2. 动画里中身常被玩成导演**高松信司**，片尾署名“旁边的大叔”。
  3. 莲蓬篇：周一代班的是莲蓬族**江莲**，正牌伊丽莎白那阵子在休假。
  4. 后期漫画还给过“央国星第一皇子**多拉公尼亚**”的设定。
- 结论：**“毛腿大叔”是最深入人心的读法，但官方并没有把它锁死为唯一真相。**

### 3.2 我们采用的版本

**玩偶服版**：

```text
外层：白色连体玩偶服（长蛋形壳）
中层：深色内衬 + 底口
内层：毛腿大叔（腿 + 腰胯）
配件：黄色鸭蹼鞋、牌子、伞（伞第一版不做）
```

关键逻辑：

- 白壳是**衣服**，不是实心身体。
- 黄色鸭蹼是**套在人脚上的鞋**，不是长在壳上的脚。
- 毛腿一直在壳里，不是切换模型。
- 跑步时壳上弹，露出毛腿；待机时壳垂下来盖住腿。
- 壳和腿**分开绑定**，不能一起蒙皮。

**不要混用“生物版”和“玩偶服版”的逻辑**，否则会出现“鸭蹼和大叔腿怎么同时存在”的设定矛盾。

### 3.3 从图片得到的视觉结论

- 轮廓：长蛋形/胶囊形，**没有脖子、没有腰、没有可见的腿**；正面看，脚直接从身体下缘伸出来。
- 脸：眼睛是两个大圆，**瞳孔极小**，每只眼睛上方**三根短睫毛**，没有眉毛；嘴是宽扁黄色椭圆，中间一条闭合线，下嘴略深，没有鼻孔和牙齿。
- 身体：白色连体壳，没有拉链、没有接缝；表面哑光，只有浅灰阴影，没有布料纹理。
- 手臂：鳍状，没有手指；末端略尖，可以弯折夹住牌子/伞。
- 脚：三趾、趾间有蹼、黄色、趾尖略尖；不是人脚。
- 背面：参考图没有背面；第三人称游戏里背面是主视图，必须补设计。建议保持纯白，最多一个小尾巴凸起，不要加羽毛/拉链。
- 道具：牌子是白色长方形 + 细杆；牌子是“第二张脸”，也是天然 UI 载体。
- 颜色：身体约 `#E9E9E9` 暖灰白；嘴/蹼 `#FBC55B`；描线 `#2B2B2B`；眼白 `#FFFFFF`；红伞 `#A83D49`。

### 3.4 比例硬指标（按正面图估算）

- 身高 **1.8m**，躯干宽约 **0.85m**，展开手臂约 **1.1m**，体重感 **123kg**。
- 眼睛在总高 **20%**，嘴在 **22%–33%**，手臂从 **40%** 到 **65%**，脚只占底部 **10%–15%**。
- 躯干宽:高 ≈ **1:2.1**。
- 每只脚约体宽 **1/4**；嘴宽约体宽 **1/3**；牌子约体宽 **1/2–2/3**。
- 这些是“按图比例”的约束，不是官方绝对数值；官方只给了 180cm / 123kg / 9 月 7 日。

---

## 4. 已确定的玩偶服方案

### 4.1 尺寸关系

- 总高：**1.8m**。
- 壳宽：约 **0.85m**，壳深约 **0.70m**。
- 壳底口：待机时距地 **0.15m**，刚好盖到鞋面。
- 跑步时壳抬到 **0.32m**（抬升约 17cm），露出小腿；如果要露膝，可到 **0.50m** 左右。
- 底口：**0.50 × 0.38m** 的宽椭圆，必须能让两条腿和跑步动作通过。
- 壳厚：`Solidify` **2cm**；内衬 **1cm**。
- 鸭蹼鞋：高约 **0.15m**，长约 **0.36m**，宽约 **0.24m**。
- 腿关节：髋 **0.90m**、膝 **0.50m**、踝 **0.12m**。

### 4.2 分件

| 部件 | 说明 | 优先级 | 面数预算（v1） |
|---|---|---|---|
| `SUIT_Shell` | 白色长蛋形壳，开底口 | P0 | 2k–4k |
| `SUIT_Liner` | 深色内衬，防止看穿 | P0 | 300–600 |
| `SUIT_Bill_Upper` | 上嘴，固定到头部 | P0 | 300–500 |
| `SUIT_Bill_Lower` | 下嘴，挂到 `jaw` | P0 | 300–500 |
| `SUIT_Eye_L/R` | 眼白 + 瞳孔 | P0 | 150–250 each |
| `SUIT_Lash_L/R` | 三根睫毛 | P0 | 20–40 each |
| `SUIT_Arm_L/R` | 白色鳍状袖套 | P0 | 400–700 each |
| `DUCKSHOE_L/R` | 黄色鸭蹼鞋，三趾有蹼 | P0 | 500–800 each |
| `INNER_Leg_L/R` | 毛腿，髋到踝 | P0 | 800–1.2k each |
| `INNER_Pelvis` | 隐藏腰胯/短裤 | P1 | 200–400 |
| `INNER_Hair` | 风格化毛簇，不要毛发模拟 | P1 | 100–200 合计 |
| `PROP_Sign` | 空白板 + 细杆 | P1 | 30–60 |
| `PROP_Umbrella` | 红色低模伞 | P2 | 300–500 |
| `INNER_Head` | 大叔头/发光眼 | P2 | 1k–2k |

**v1 总预算：8k–12k tris。**

### 4.3 建模注意点

**外壳**

- 用 UV 球或圆柱做长蛋形，删掉底部，形成宽椭圆开口。
- 不要用布尔挖洞；直接建开口的壳更干净。
- 加 `Solidify` 2cm，再加一圈下摆卷边。
- 内衬用深灰/近黑；重点是“看进去是暗的”。
- 待机时下摆接近鞋面；跑步时壳骨上抬，露出内衬和腿。
- 背面保持干净，不要加羽毛、拉链、围巾、腰带。

**鸭蹼鞋**

- 必须独立，绑到脚骨，不要焊在壳上。
- 三趾、有蹼、黄色；脚踝处留开口/卷边，让毛腿能“插进去”。
- 鞋跟脚走；如果鞋焊在壳上，跑步会像壳在滑行。

**毛腿**

- 只做髋到踝，不需要完整人体。
- 腿型用圆柱/基础腿，膝盖和脚踝留环线。
- 毛发用 **12–16 簇**风格化毛片/几何毛簇，不要做毛发模拟。
- 大腿和小腿外侧多一点，内侧少一点；颜色深，和白色外壳形成反差。
- 待机时完全藏在壳里；跑步时至少露出 15cm。

**脸**

- 脸保持在壳上：上嘴固定，下嘴单独一件，挂 `jaw`。
- 眼睛独立做，小瞳孔、三根睫毛、无眉毛；眼白纯白，壳是暖灰白。
- 第一版不做完整大叔脸；嘴可以小幅开合，不做“嘴里钻出人脸”的复杂结构。
- 如果以后要做大叔脸，建议把“脸板”做成可掀开的 hood，而不是从嘴里钻出来。

**手臂/牌子**

- 手臂是白色鳍状袖套，一根骨头，不要做人手。
- 牌子挂在袖口末端；牌子先做空白板 + 细杆。
- 牌子文字不要烘焙，后续用引擎 UI/TextMesh 或 Label3D。
- 伞第一版不做，避免增加剪影和绑定复杂度。

### 4.4 绑定方案

推荐骨骼（v1，**13–15 根**）：

```text
root
  pelvis
    thigh_L
      shin_L
        foot_L
    thigh_R
      shin_R
        foot_R
    shell              ← 壳的主骨（刚体）
      jaw
      arm_L
      arm_R
        sign_socket
      umbrella_socket  ← v2，可选
```

要点：

- 壳 **100% 权重**给 `shell` 骨，不要给腿骨。
- 腿平滑权重到腿骨；鞋 100% 给脚骨。
- 动画 `shell` 的局部 Z 位移和旋转，实现壳上弹/后仰。
- 壳是刚体/半刚体，腿是独立动画；这样“壳弹起来露腿”非常容易调。
- **v1 不做 `spine`/`head`**；壳当刚体。以后要点头再加 head 骨并拆壳。
- 如果壳抬到最高时腿穿模，优先加宽底口，而不是把壳整体做大。
- 不要用 Rigify/完整人形骨架；手写 13–15 根骨头更干净。
- 牌子用 `Child Of` 或骨骼父子关系挂到 `sign_socket`，导出前烘焙。

### 4.5 动画清单

| 动画 | 帧数 @30fps | 要点 |
|---|---|---|
| `idle` | 60 | 壳垂到底，腿完全看不见；轻微呼吸、眨眼、偶尔翻牌 |
| `run` | 24 | 壳抬 17cm、后仰 8°；腿完整循环；毛腿明显露出 |
| `walk` | 30 | 壳轻微上下 3cm；腿偶尔露一点，不明显 |
| `jump` | 30 | 壳上弹，腿收起；落地壳压扁、腿露一下再盖住 |
| `sign_talk` | 45 | 举牌、翻牌 2–3 次；文字由引擎换 |
| `hit` | 15 | 壳左右晃，毛腿弹出来一点再缩回 |
| `reveal` | 60（可选） | 壳抬到 0.50m 露膝；第一版不做脸 |

动画原则：

- **静止是常态**：伊丽莎白的笑点来自“站着不动，突然举牌”，不要加过多 idle 弹跳。
- 举牌要快、硬切，停顿要够，文字才能读。
- 跑步要有 123kg 的重量感：身体左右倾 3–5°，脚抬 10cm，壳的弹跳和脚步错开半拍。
- “露腿”是跑步的自然结果，不是单独切换形态。

### 4.6 验收标准

- [ ] 待机时，从游戏镜头看不到毛腿，只看到白壳和鸭蹼鞋。
- [ ] 跑步时，壳抬起后至少露出 15cm 的毛腿。
- [ ] 壳抬到最高、腿摆到最大时，腿不穿出壳。
- [ ] 鸭蹼鞋始终跟着脚，不滑动、不脱离。
- [ ] 从底口能看出深色内衬，不像一个实心蛋。
- [ ] 正面、背面、3/4 视角剪影都像伊丽莎白。
- [ ] 跑步循环首尾接得上，脚不滑步。
- [ ] 壳和腿是分开绑定的，壳抬起来不会拉扯腿。

---

## 5. 技术路线结论

### 5.1 已决定：外壳用 Blender 直接建

对这个特定目标，推荐 **80% Blender + 20% Tripo**：

- **Blender 直接建**：外壳、底口、内衬、鸭蹼鞋、毛腿、牌子、绑定、动画。
- **Tripo 可选**：做 2–3 个比例参考；或做内里大叔的头部/有机细节。
- **不建议**：用 Tripo 生成最终外壳，再花时间切开、补面、重拓扑。

### 5.2 为什么

- 需要的是“有底口、有厚度、有内衬、分件、能绑定的玩偶服结构”，不是“一个封闭的鸭子模型”。
- Tripo 看到正面图，大概率生成**封闭实体**；它不知道衣服里面是空的，也不知道底口要开。
- 它会把鸭蹼、身体、甚至手臂粘成一个网格；后面还是要切开、加厚、加内衬、重做鞋。
- 它的拓扑不会为底口、下颌、肩部留环线；绑定前还是要重拓扑。
- 伊丽莎白外壳太简单，AI 的“生成细节”优势发挥不出来；手工建壳 1–3 小时（熟手），反而更可控。
- 对新手，修 AI 网格比建一个胶囊更难；手工步骤是线性的，AI 清理是开盲盒。

### 5.3 如果仍想用 Tripo

只把它当“比例参考生成器”：

1. 打开 [Tripo Studio](https://studio.tripo3d.com/)。
2. 选 `Image to 3D`；第二轮可用 `Smart Mesh`（四边面）。
3. 上传干净正面图，去掉牌子、伞、背景。
4. 参数：Draft/Standard；对称开；纹理关或 1K；自动绑定关；草稿面数 3k–8k 四边面。
5. 提示词：`long white egg-shaped mascot costume, yellow duck bill, short flipper sleeves, clean silhouette, symmetrical, front view, no props, no text, no human legs`。
6. 负面提示词：`sign, umbrella, human legs, hands, fingers, feathers, text, extra limbs, realistic details`。
7. 生成 4–6 版，只看剪影，不看纹理。
8. 选最像的，导出 GLB；导入 Blender，缩放成 1.8m。
9. 把它放进 `REF_Tripo` 集合，锁定、半透明，只当 `Shrinkwrap` 目标；重拓扑完就删掉。

**不要**在提示词里写“里面有大叔”“毛腿”“玩偶服里的人”；Tripo 会把腿和壳生成在一起，后面很难拆。

### 5.4 助手使用 Blender 的能力边界（Windows）

助手可以：

- 用 Blender 的 Python API（`bpy`）在**后台/无界面**模式下建模。
- 生成网格、材质、UV、骨骼、权重、基础动画。
- 用 Workbench / EEVEE Next 渲染正面/侧面/背面/姿势预览 PNG，并读取图片检查。
- 导出 GLB/FBX，生成 `.blend`。
- 根据反馈改参数、重新生成，版本可复现。

助手不能：

- 像人一样在 Blender 视口里用鼠标实时拖点、雕刻。
- 做很细的有机雕刻（大叔脸皱纹、真实毛发走向、布料褶皱）。
- 登录用户的 Tripo 账号点网页；需要用户操作或提供 API key。
- 在没有安装 Blender 的机器上直接生成 `.blend`。
- 用系统 Python（3.14）跑 `bpy`——`bpy` 只在 Blender 自带的 Python 3.11 里存在。

Windows 特有的约束：

- 必须用全路径调用 `blender.exe`（`& "D:\tools\...\blender.exe"`），否则依赖 PATH。
- 命令用 PowerShell 语法；续行用反引号，不能用 bash 的 `\`。
- 后台模式要带 `--background`；`--python-exit-code 1` 才能让失败被 PowerShell 捕获。

---

## 6. 当前进度

### 6.1 已完成

- **2026-11-09：v2 玩偶服改造完成**——`scripts\build_eliz_v2.py` 重做造型：身体+双袖布尔合并（单连通、0 边界边、16 mm 袖根倒角）、下摆 0.18 m + 24 mm 厚边、鞋 0.26 m 高（上部藏进摆内）、嘴缝弧线凹槽（中–端 0.028 m）、眼片包边；`make_fabric_textures.py` 生成 1K 可平铺绒面贴图，材质加 sheen；11 张渲染（含 4 张近景）；`check_asset_v2.py` → CHECK_OK、`verify_export_v2.py` → VERIFY_OK。含隐藏服内人偶（9 件，0 顶点露在服外，头顶余量 0.165 m）与剖面图 `v2_wearer_cutaway.png`。
- **2026-11-09：v1 blockout 完成**——安装 Blender 4.5.15 LTS 便携版、写 `scripts\build_eliz_v1.py`，生成壳/底口/内衬/嘴眼/鳍臂/鸭蹼/毛腿/腰胯/牌子 + 13 根骨骼 + `idle`/`run`，渲 6 张图，导出 `.blend` 与 `.glb`；`verify_export.py` 与 `check_asset.py` 均通过（高 1.800 m、13 骨、9,204 tris、2 个动作、待机 0 露腿、跑步露 0.184 m）。
- 阅读并分析 4 张参考图。
- 查证伊丽莎白原作设定与“中身”多层梗。
- 确定采用“玩偶服版”，而不是“生物版”。
- 确定“鸭蹼是鞋、毛腿在壳内、壳上弹露腿”的结构。
- 确定尺寸、分件、材质、绑定、动画和验收标准。
- 比较 Tripo 与 Blender 直接建模，结论：外壳用 Blender，Tripo 只做可选辅助。
- 说明助手可以用 `bpy` 脚本建模，但需要先安装 Blender。
- 建立 `docs/character_spec.md`（v0.1），固化尺寸、分件、材质、绑定、动画、验收和待决策项。
- 建立 `art/`、`art/refs/`，复制 4 张参考图入库。
- 初始化独立 Git 仓库 `main` 分支，配置 GitHub 远程并同步到 `origin/main`（`d2fc2f2`、`692f4a5`）。
- **2026-11-09：文档从 macOS 版整体改写为 Windows 版**（环境、安装命令、路径、Git 状态按本机实测；绑定方案与规格书对齐为 13–15 根、去掉 `spine`/`head`；毛簇统一为 12–16；面数预算统一）。

### 6.2 未完成

- 未使用 Tripo（仍为可选）。
- 未配置 Git 身份（`user.name`/`user.email`），本机提交需临时 `-c`。
- v2.1 待做：袖窿/下摆线迹、嘴部网格加密（消除近景台阶）、鞋与嘴加绒、眼睑/眨眼。
- 未做 walk / jump / hit / sign_talk 动画（只有 `idle` + `run`）。
- 未选择游戏引擎，未开始游戏玩法。

### 6.3 最后的待确认

v2 已通过结构 / 遮挡 / 嘴型 / 导出验收，剩下的是观感与相似度的取舍：

1. **厚袖 + 大鞋**是否符合你对"玩偶服"的预期（`v2_three_quarter.png`、`v2_front_match.png`）。
2. 剪影 IoU 从 v1 的 0.925 降到 0.909（整体胖约 3%）；是为了相似度收窄鞋/袖，还是保持现在的"玩偶体积"。
3. 布料近景（`v2_detail_fabric.png`）的绒面颗粒感是否够；全身尺度偏"砂纸"，可再加一层低频褶皱。
4. 嘴部近景（`v2_detail_mouth.png`）的弧线方向与深浅是否满意。

---

## 7. 下一步执行清单

### P0：确认规格 + 让 Blender 可用

- [x] 规格书第 12 节决策：v1 先按推荐默认值实现，验收时一并确认。
- [x] Blender 安装方案：便携版 `D:\tools\blender-4.5.15-windows-x64\`。
- [x] 下载并安装 Blender **4.5.15 LTS（windows-x64）**（SHA256 校验通过）：
  - 便携版：<https://download.blender.org/release/Blender4.5/blender-4.5.15-windows-x64.zip> → 解压到 `D:\tools\blender-4.5.15-windows-x64\`。
  - 安装版：<https://download.blender.org/release/Blender4.5/blender-4.5.15-windows-x64.msi>。
  - 校验：同目录 `blender-4.5.15.sha256`。
- [x] 验证：`Blender 4.5.15 LTS` 已正常输出版本（`--version`）。
- [ ] 配置 Git 身份（仍未配置，提交前必做）：
  ```powershell
  & "C:\Program Files\Git\cmd\git.exe" config --global user.name "你的名字"
  & "C:\Program Files\Git\cmd\git.exe" config --global user.email "you@example.com"
  ```
- [x] 创建 `scripts\`（3 个脚本已就位）；`art\blender\`、`art\exports\`、`art\renders\` 由脚本自动生成。

### P1：第一版 blockout

- [ ] 可选：把正面图抠底、放大成 1024 PNG，保存到 `art\refs\eliz_front_clean.png`。
- [x] 写 `scripts\build_eliz_v1.py`（壳厚用双层建模替代 Solidify，底口尺寸更可控）：
  - 1.8m 长蛋形壳；
  - 底口 0.50 × 0.38m；
  - `Solidify` 2cm；
  - 深色内衬；
  - 上嘴/下嘴；
  - 眼睛 + 三根睫毛；
  - 鳍状手臂；
  - 独立鸭蹼鞋；
  - 毛腿 + 隐藏腰胯；
  - 简单骨骼：`root/pelvis/thigh/shin/foot/shell/jaw/arm/sign_socket`（13–15 根）。
- [x] 用 PowerShell 跑（已跑通）：
  ```powershell
  & "D:\tools\blender-4.5.15-windows-x64\blender.exe" --background --factory-startup `
      --python-exit-code 1 --python "D:\work\eliz_game\scripts\build_eliz_v1.py"
  ```
- [x] 渲染四视图：front / side / back / 3/4（PNG 到 `art\renders\`）。
- [x] 渲染一个“壳抬起、腿露出”的跑步姿势（v1_run_reveal.png），另加 v1_sign_pose.png。
- [x] 保存 `art\blender\eliz_costume_v1.blend`。
- [x] 导出 `art\exports\eliz_costume_v1.glb`（重导入校验通过）。
- [ ] 把渲染图给用户确认比例 ← **当前卡在这一步**。

### P2：确认后再做

- [ ] 根据反馈调比例、底口、腿长、壳抬高度。
- [ ] 绑定权重，测试跑步循环。
- [ ] 做 idle / walk / run / jump / hit。
- [ ] 做牌子 + `sign_socket`。
- [ ] 可选：Tripo 生成内里大叔头，导入 Blender 细化。
- [ ] 可选：伞。
- [ ] 最终导出 GLB/FBX。

---

## 8. 待决策

| 决策 | 当前建议 | 状态 |
|---|---|---|
| 规格书关键决策 | 见 `docs/character_spec.md` 第 12 节；v1 已按推荐值实现，待验收 | 待用户确认 |
| 安装 Blender | 4.5.15 LTS 便携版已装到 `D:\tools\blender-4.5.15-windows-x64\` | 已完成 |
| 第一版范围 | 只做外壳/底口/内衬/嘴眼/鸭蹼/毛腿/简单骨骼 | 待用户确认 |
| 大叔脸 | 第一版不做；以后用 Tripo 或手工做 hood 掀开 | 暂缓 |
| 伞 | 第一版不做 | 暂缓 |
| 牌子文字 | 模型留空白板，文字以后用引擎 UI | 暂缓 |
| 游戏引擎 | 暂不选；先完成 Blender 资产 | 暂缓 |
| 风格 | 赛璐璐/平涂 + 深灰描边；白壳暖灰白 | 默认 |

---

## 9. 风险与注意事项

**设计风险**

- **不要混用生物版和玩偶服版逻辑。** 鸭蹼是鞋，毛腿是内里；否则设定会打架。
- **不要把壳和腿一起蒙皮。** 壳必须是独立骨骼，腿才能自由跑。
- **不要把鸭蹼焊在壳上。** 鞋必须跟脚，否则跑步像滑行。
- **底口不能太窄。** 跑步时大腿会穿出壳；优先加宽底口。
- **待机不能露腿。** 壳要垂到鞋面附近；跑起来才露。
- **内衬不能省。** 壳一抬，没内衬会直接看穿。
- **毛发不要做太真实。** 风格化毛簇，不要毛发模拟。
- **不要用 Tripo 纹理做最终材质。** 它带烘焙光照，和赛璐璐冲突。
- **不要用 Tripo 自动绑定。** 非标准体型，权重大概率崩。
- **不要忽略背面。** 第三人称游戏里背面是主视图；参考图没有背面，需要补设计。

**Windows 环境风险**

- `git` 和 `blender` 都**不在 PATH**：脚本、文档一律写全路径，或先手动加 PATH。
- Git **没有配置身份**：直接 `git commit` 会失败或产生错误作者信息。
- PowerShell 里路径含空格必须加引号；调用 exe 用 `&`，否则拿不到 `$LASTEXITCODE`。
- PowerShell 续行是反引号，且**反引号后不能有空格**，否则参数会被拆开。
- 控制台中文可能乱码；脚本日志优先英文，或先 `chcp 65001`。
- 系统 Python 是 3.14，**不能**替代 Blender 内置 Python 3.11 跑 `bpy`。
- Intel Iris Xe 是集显、共享显存：不要开高细分/4K 贴图/体积雾，否则渲染会爆显存或极慢。
- 首次运行 `blender.exe` 可能被 SmartScreen/杀软拦；必要时给 `D:\tools\blender-4.5.15-windows-x64\` 加白名单。
- 仓库和 Blender 都放在纯 ASCII 路径（不要放中文目录、不要放 OneDrive 同步目录）。
- 需要干净复现时用 `--factory-startup`；用户配置在 `%APPDATA%\Blender Foundation\Blender\4.5\`。

**IP 风险**

- 伊丽莎白是空知英秋/集英社的角色；个人同人和学习可以，商业化发行需要授权。Tripo 生成物的商用权也要看套餐。

---

## 10. 参考资料

### 本地图片

- [正面全身图](../art/refs/eliz_front.jpg)
- [动画截图](../art/refs/eliz_anime.jpg)
- [撑伞行走图](../art/refs/eliz_umbrella.png)
- [举牌半身图](../art/refs/eliz_sign.webp)

> 原始下载目录是原 macOS 机器上的 `/Users/wzh/Downloads/eliz_pic`，当前 Windows 机器没有该路径；仓库内 `art/refs/` 为唯一权威副本。

### 网络资料

- [中文维基：银魂角色列表](https://zh.wikipedia.org/wiki/%E9%93%B6%E9%AD%82%E8%A7%92%E8%89%B2%E5%88%97%E8%A1%A8)
- [アニ図鑑：エリザベス](https://anizukan.com/characters/12237/elizabeth)
- [RENOTE：エリザベス考察](https://renote.net/articles/10712/page/2)
- [English Wikipedia: List of Gintama characters](https://en.wikipedia.org/wiki/List_of_Gintama_characters)
- [Blender 4.5 LTS 下载目录](https://download.blender.org/release/Blender4.5/)
- [Blender 4.5 手册](https://docs.blender.org/manual/en/4.5/)
- [Tripo 图像转 3D](https://www.tripo3d.com/features/image-to-3d-model)
- [Tripo 智能网格](https://www.tripo3d.com/features/smart-mesh)
- [Tripo 新手教程](https://www.tripo3d.com/blog/first-3d-model-ai-tutorial)

---

## 11. 新会话启动提示词

把下面这段直接贴给新会话：

```text
请先阅读 D:\work\eliz_game\docs\HANDOFF.md，理解项目背景、角色设定、已确定的设计方案和当前进度。

当前目标：用 Blender 脚本建模“玩偶服版”伊丽莎白（Windows 11 x64，仓库 D:\work\eliz_game）。
核心结构：白色长蛋形外壳 + 底口 + 深色内衬 + 独立鸭蹼鞋 + 壳内毛腿；跑步时外壳上弹，露出毛腿。
已决定：外壳用 Blender 直接建，不用 Tripo 生成最终外壳；Tripo 仅作为比例参考或内里大叔头部的可选辅助。
当前进度：v1 blockout 已生成并按参考图重调（22 网格 / 9,204 tris / 13 骨骼 / idle+run），Blender 4.5.15 已装在 D:\tools\blender-4.5.15-windows-x64；7 张渲染与 .blend/.glb 已产出，verify_export.py + check_asset.py 均通过，正面对比剪影 IoU 0.92。
最后待确认：用户对 7 张渲染的比例确认；规格书第 12 节决策（v1 已按参考图实测值实现）。

请先看 art\renders\v1_*.png 和 docs\character_spec.md 第 17 节（v1 产出记录 + 已知简化）；再决定是调比例还是进 v1.5 细化（鸭蹼脚型 / 牌子握持 / 描边与布料 / walk+jump+hit）。
复现：& "D:\tools\blender-4.5.15-windows-x64\blender.exe" --background --factory-startup --python-exit-code 1 --python "scripts\build_eliz_v1.py"
命令一律用 PowerShell，Blender 用全路径调用，并带 --background --factory-startup --python-exit-code 1。
不要重新讨论 Tripo vs Blender；外壳已决定用 Blender 直接建。
```

---

## 12. 一句话交接

**项目目前停在“规格书 v0.1（Windows 版）已建立、关键决策待确认、Blender 未安装、模型未建”的阶段；下一步是先确认规格书，再把 Blender 4.5.15 LTS 便携版装到 `D:\tools\`，写 `scripts\build_eliz_v1.py` 做玩偶服 blockout，重点验证“待机藏腿、跑步露腿、壳腿分离绑定”这三件事。**

---

## 13. 文档变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-09 | 建立 `docs/character_spec.md` v0.1 与本文档（macOS 版）。 |
| 2026-11-09 | Git 仓库初始化并推送 GitHub；记录 commit `d2fc2f2`。 |
| 2026-11-09 | **整体改写为 Windows 版**：环境表、安装与验证命令、路径、Git 状态、参考图链接全部按本机实测重写；绑定方案对齐规格书（13–15 根，去掉 `spine`/`head`）；毛簇统一为 12–16；面数预算与规格书统一；新增 Windows 环境风险一节。 |
| 2026-11-09 | **v1 blockout 完成**：装 Blender 4.5.15 便携版，写 `build_eliz_v1.py` / `render_views.py` / `verify_export.py`；产出 6 张渲染、`.blend`、`.glb`；GLB 重导入校验通过（1.800 m / 13 骨 / idle+run）。 |
| 2026-11-09 | **v1 验收加固**：外壳加密 + 加裙摆卷边（→ 8,364 tris）、修牌杆端 n-gon、脚踝开口居中、跑步壳抬 0.19 m；新增 `check_asset.py`：待机漏腿 0、跑步露出 0.184 m、壳腿隔离 Δ=0、鞋跟脚、下颌只动下嘴，全部 `CHECK_OK`。 |
| 2026-11-09 | **按参考图重调（v1.1）**：逐像素量 `eliz_front.jpg` 反推尺寸（壳宽 0.894、眼 0.16/±0.165/1.535、嘴 0.452×0.29、脚扇面 0.5），壳形改为“直筒 + 椭球顶”，鸭嘴合并为单网格（上/下材质 + 下颌 `jaw` 权重），加 Freestyle 描边、加黑底同构图渲染 `v1_front_match.png`；剪影 IoU 0.92、同高度行宽基本一致。`CHECK_OK` / `VERIFY_OK` 仍通过。 |
