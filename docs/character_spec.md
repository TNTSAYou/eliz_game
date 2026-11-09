# 伊丽莎白 3D 角色规格书 v0.1（Windows 版）

> 状态：**v1 blockout 已生成（脚本可重跑），设计细节待确认**
> 日期：2026-11-09（Asia/Shanghai）
> 项目：`eliz_game` · 仓库：`D:\work\eliz_game`
> 平台基线：**Windows 11 IoT 企业版 LTSC 10.0.26100（24H2），x64**
> 工具链基线：**Blender 4.5.15 LTS（Windows x64，便携版优先）**
> 阶段：v1 blockout → 比例确认（pre-modeling spec 保持有效）
> 目标版本：**玩偶服版 v1**
> 参考图：`art/refs/`

---

## 0. 项目背景与角色简介

### 0.1 项目背景

`eliz_game` 是一个以《银魂》伊丽莎白为核心的角色项目。当前阶段不讨论游戏引擎、玩法和关卡，只聚焦一件事：

> 用 Blender（Tripo 仅作可选辅助）做出一个“玩偶服版”伊丽莎白 3D 资产，并验证“待机藏腿、奔跑露腿、壳腿分离绑定”的核心表演。

选择这个方向的原因：

- 伊丽莎白的剪影极强：白色长蛋形、黄嘴、鸭蹼，辨识度高。
- 几何结构简单，适合程序化建模和快速迭代。
- “可爱外壳 + 毛腿大叔”的反差本身就是记忆点。
- “奔跑时外壳上弹、露出毛腿”是天然的角色动画钩子。

第一版目标不是最终游戏资产，而是 blockout：比例正确、分件合理、能绑定、能跑、能导出 GLB。

**本版说明（Windows）**：本规格书按当前 Windows 11 工作机的真实工具链编写——路径是 Windows 路径，命令是 PowerShell 5.1+ 可直接执行的命令，Blender 的安装、调用与脚本约定集中在第 10.4、10.5 节。macOS 时代的路径（`/Users/wzh/...`、`/Applications/Blender.app`）与命令（Homebrew、`.app` 直接执行）已全部废弃，不要再沿用。

### 0.2 伊丽莎白是谁

伊丽莎白（エリザベス / Elizabeth）是空知英秋漫画《银魂》中的角色，桂小太郎的宠物兼攘夷伙伴，由坂本辰马送给桂。外表像一只巨大的白色企鹅/鸭子，实际是宇宙生物（天人）。

几个关键点：

- **交流方式**：日常举写字板；其实能说话，但偏用牌子。牌子也能当武器/盾牌。
- **官方设定**：生日 9 月 7 日，身高 180cm，体重 123kg。看起来呆萌，战斗力却很强，能踢回火箭炮、眼睛发激光、嘴里伸火炮/钻头，必要时还能当降落伞。
- **“中身”梗**：初登场就露出毛腿；嘴张开时里面是人形 + 发光眼。动画里中身常被玩成导演高松信司，片尾署名“旁边的大叔”；莲蓬篇说周一代班的是莲蓬族江莲；后期漫画还揭示它可能是央国星第一皇子多拉公尼亚。官方始终把它当梗，没有锁死一个答案。
- **性格与功能**：沉默、呆滞、忠诚，是桂身边最可靠的搭档之一；平时负责冷面吐槽和收拾残局，严肃篇章里又能扛事。它的喜剧节奏来自“站着不动，突然举牌”。

### 0.3 我们采用的版本

我们采用“玩偶服版”，而不是“实心生物版”：

- 白壳是一套连体玩偶服，不是它的身体。
- 黄色鸭蹼是套在人脚上的鞋。
- 壳里是毛腿大叔的腿和腰胯；不做完整上身。
- 待机时壳垂到鞋面，腿藏住；奔跑时壳上弹，露出毛腿。
- 壳、腿、鞋、嘴、牌子必须分件，壳和腿分开绑定。

这个版本更符合“奔跑时露毛腿”的想象，也更容易做出喜剧反差和动画表演。

### 0.4 一页结论

我们要做的不是“一只实心白鸭子”，而是：

```text
外层：白色长蛋形连体玩偶服（壳）
中层：深色内衬 + 底口
内层：毛腿大叔的腿 + 腰胯
配件：黄色鸭蹼鞋、空白牌子；伞和完整大叔脸暂不做
```

核心画面：

- 待机：壳垂到鞋面，**只看到白壳和鸭蹼鞋，看不到毛腿**。
- 奔跑：壳上弹约 **17cm**，露出 **15cm 以上**的毛腿。
- 大动作/彩蛋：壳抬到约 **0.50m**，露出膝盖，但不做完整大叔脸。

第一版目标不是“最终美术”，而是：

> **一个比例正确、壳腿分离、能跑起来露腿、能导出 GLB 的 blockout。**

第一版成功标准：

- [ ] 1.8m 高，正面/背面/3/4 剪影像伊丽莎白。
- [ ] 待机藏腿，跑步露腿 15cm 以上。
- [ ] 壳是空心的，有底口、有厚度、有深色内衬。
- [ ] 鸭蹼鞋跟脚，不跟壳焊死。
- [ ] 壳和腿分开绑定，壳抬起不拉扯腿。
- [ ] 8k–12k tris，能导出 GLB。

---

## 1. 项目目标与非目标

### 1.1 目标

1. 用 **Blender 为主** 建出“玩偶服版”伊丽莎白。
2. 结构上支持“壳上弹 → 露出毛腿”的核心表演。
3. 资产能继续绑定、动画、导出，为后续游戏做准备。
4. 第一版先做 **blockout + 简单骨骼 + 跑步测试**，不追求最终材质和毛发。

### 1.2 非目标（v1 不做）

- 不做完整大叔脸、嘴里发光眼、掀脸 hood。
- 不做伞。
- 不做牌子文字系统（只做空白板）。
- 不做攻击、受击、复杂战斗动画。
- 不做游戏引擎接入、关卡、UI。
- 不做 Tripo 最终外壳；Tripo 仅可选做比例参考或后期内里头部。

### 1.3 V1 交付范围

**必须（P0）：**

- 外壳、底口、内衬。
- 上嘴/下嘴、眼睛、三根睫毛。
- 鳍状手臂、独立鸭蹼鞋。
- 毛腿 + 隐藏腰胯（不做完整上身）。
- 空白牌子 + `sign_socket`。
- 基础骨骼（壳腿分离）。
- `idle` + `run` 两个测试动画。
- 四视图 + 跑步露腿姿势渲染。
- `.blend` + `.glb`。

**可选（P1）：**

- `walk`、`jump`、`sign_talk`、`hit`。
- 毛腿细节、下摆卷边、简单布料质感。
- 眼睛眨眼形态键。

**下一版（V1.5 / V2）：**

- 完整大叔脸 / 掀脸 hood。
- 伞。
- 攻击、受击、复杂动作。
- 最终材质、描边、游戏引擎接入。

---

## 2. 设计支柱

1. **剪影第一**：长蛋形、无脖子、无腰、无可见腿；一眼认出是伊丽莎白。
2. **它是玩偶服，不是生物**：白壳是衣服，鸭蹼是鞋，毛腿在衣服里。
3. **反差，不是纯可爱**：小瞳孔、三根睫毛、无眉毛；呆滞、微诡异，不是大眼萌。
4. **露腿靠运动**：不是切换形态，而是壳的弹跳把腿露出来。
5. **绑定优先**：壳、腿、鞋、嘴、牌子必须分件；不要做成一个融合网格。

### 2.1 三个视觉方向（brainstorm）

| 方向 | 特征 | 优点 | 风险 | 建议 |
|---|---|---|---|---|
| A. 动画还原型 | 平涂、细描边、几乎无布料纹理 | 最像动画，剪影最干净 | 可能显得太“纸片” | **v1 主方向** |
| B. 玩偶服质感型 | 哑光布料、下摆卷边、轻微织纹、深色内衬 | 最能说明“这是衣服” | 纹理过多会脏，AI/贴图容易过度 | **v1.5 加入** |
| C. 黑色喜剧型 | 污渍、汗、胡茬、恐怖感 | 反差最强，游戏辨识度高 | 容易变恶心，偏离原作 | 暂不做，按游戏 tone 再定 |

**推荐：A 的形状 + B 的下摆/内衬细节。** 不要 C。

### 2.2 角色气质

- 表面：呆、静、无害、像个儿童节目吉祥物。
- 内里：沉、重、有点邋遢的大叔。
- 表演：**静止是常态**，突然举牌/突然露腿才是笑点。
- 不要做成活泼、弹跳、频繁卖萌的角色。

---

## 3. 角色分层与玩偶服逻辑

### 3.1 分层

```text
┌─────────────────────────────┐
│  SUIT_Shell  白色连体玩偶服  │
│  ┌───────────────────────┐  │
│  │ SUIT_Liner 深色内衬    │  │
│  │  ┌─────────────────┐  │  │
│  │  │ INNER_Legs 毛腿  │  │  │
│  │  │ INNER_Pelvis 腰胯│  │  │
│  │  └─────────────────┘  │  │
│  └───────────────────────┘  │
│  DUCKSHOE_L/R 鸭蹼鞋（独立）│
└─────────────────────────────┘
```

### 3.2 逻辑约定

- 白壳是**连体玩偶服**，不是实心身体。
- 黄色鸭蹼是**套在人脚上的鞋**，不是长在壳上的脚。
- 毛腿一直在壳内，不是切换模型。
- 待机时壳垂到鞋面，腿藏在阴影里。
- 跑步时壳上弹，露出毛腿；壳落下时重新盖住。
- 壳和腿**分开绑定**；壳不跟随腿蒙皮。
- 不做“壳是生物”和“壳是衣服”的混用，否则鸭蹼和大叔腿的逻辑会打架。

### 3.3 背面设计

参考图没有背面，但第三人称游戏里背面是主视图，必须先定：

- 背面保持纯白，**不加羽毛、拉链、围巾、腰带**。
- v1 不加尾巴；如果后期觉得太 blank，再加一个很小的尾凸。
- 下摆背面加一圈轻微卷边，和正面一致。
- 牌子背面为浅灰/白色，文字不能反透。
- 背面必须单独渲染检查，不能只做正面。

---

## 4. 第一版人物形象细节

### 4.1 轮廓

- 长蛋形/胶囊形，顶部圆，底部略收。
- **没有脖子、没有腰、没有可见的腿**。
- 正面看，脚直接从身体下缘伸出来。
- 最大宽度在身体中下部，约在总高 55%–60% 处。
- 手臂是短鳍状，自然下垂时贴近身体，不向外张。

### 4.2 脸

- 眼睛：两个大圆，眼白纯白，**瞳孔极小**。
- 睫毛：每只眼睛上方 **3 根短睫毛**，这是识别点。
- 眉毛：**没有**；不要加。
- 嘴：宽扁黄色椭圆，中间一条闭合线，下嘴略深。
- 没有鼻孔、没有牙齿、不要尖鸟喙。
- 表情：呆滞、冷眼旁观；不要大眼萌、不要微笑。
- v1 不做完整大叔脸；下嘴可小幅开合。

### 4.3 身体

- 白色连体壳，表面哑光，无拉链、无接缝、无花纹。
- 白色用暖灰白，不要纯白；眼睛才是纯白。
- 阴影用浅灰，不要脏灰。
- 不要羽毛、毛绒、围巾、腰带、口袋。
- 下摆有一圈卷边，暗示“这是衣服”。

### 4.4 手臂

- 白色鳍状袖套，没有手指。
- 长度到身体中下部，末端略尖，可以弯折夹住牌子。
- 一根骨头即可，不要做肘关节。
- 肩部用球窝重叠藏进壳里，不要焊出复杂腋下拓扑。
- 不要做人手/爪子。

### 4.5 鸭蹼鞋

- 黄色，三趾、趾间有蹼、趾尖略尖。
- 独立成鞋，不要和壳焊在一起。
- 脚踝处有开口/卷边，让毛腿“插进去”。
- 鞋跟脚走；待机时只看到鞋，跑步时鞋落地、腿露出。
- 不要做人脚、不要做真实鸭子脚。

### 4.6 毛腿与内里

- 只做髋到踝，不需要完整人体。
- 大腿和小腿有基本腿型；膝盖、脚踝留环线。
- 毛发用 **12–16 簇风格化毛片/几何毛簇**，不要毛发模拟。
- 毛色深，和白色外壳形成强反差；大腿外侧多一些，内侧少一些。
- 腰胯藏在壳内，穿深色短裤/内衬；不要做完整上身。
- 待机完全藏住；跑步至少露出 15cm。

### 4.7 牌子

- 白色长方形板 + 细杆，v1 留空白。
- 板约 0.60m × 0.40m × 0.02m；杆约 0.40m。
- 挂在右手袖口末端，牌面朝向镜头时文字可读。
- 不烘焙文字；以后用引擎 UI / TextMesh / Label3D。
- 牌子也是武器/盾牌，但 v1 不做攻击动画。

### 4.8 伞（v2）

- 红色，低模，8–12 段伞面。
- 第一版不做，避免增加剪影和绑定复杂度。
- 做的时候挂在左手，注意不要挡住牌子和镜头。

---

## 5. 尺寸与比例

> 官方只给了 180cm / 123kg / 9 月 7 日；其余是按正面图比例估算，建模后可微调。

| 项目 | 数值 | 备注 |
|---|---:|---|
| 总高 | **1.80m** | 从头顶到地面 |
| 壳最大宽度 | **0.85m** | 中下部最宽 |
| 壳最大深度 | **0.70m** | 估算，需侧视图确认 |
| 底口 | **0.50m × 0.38m** | 宽椭圆，能过两条腿 |
| 底口待机高度 | **0.15m** | 刚好到鞋面 |
| 跑步壳高度 | **0.32m** | 抬升约 17cm |
| 大动作壳高度 | **0.50m** | 露膝，用于 jump/reveal |
| 壳厚 | **0.02m** | Solidify |
| 内衬厚 | **0.01m** | 深色，防看穿 |
| 眼线高度 | **1.44m** | 从地面算，约总高 20% 下方 |
| 眼睛直径 | **0.13m** | 眼白圆片 |
| 眼睛中心间距 | **0.18m** | 左右各 ±0.09m |
| 瞳孔直径 | **0.025m** | 极小 |
| 睫毛长度 | **0.04m** | 每眼 3 根 |
| 嘴宽 | **0.28m** | 约壳宽 1/3 |
| 嘴高 | **0.13m** | 上下嘴合计 |
| 嘴中心高度 | **1.31m** | 紧贴眼睛下方 |
| 手臂根高度 | **1.08m** | 总高 40% 处 |
| 手臂末端高度 | **0.63m** | 自然下垂 |
| 手臂长度 | **0.45m** | 鳍状 |
| 手臂宽度 | **0.16m** | 最宽处 |
| 鞋长 | **0.36m** | 鸭蹼鞋 |
| 鞋宽 | **0.24m** | 单只 |
| 鞋高 | **0.15m** | 含鞋底 |
| 鞋踝口直径 | **0.14m** | 毛腿插入 |
| 髋高度 | **0.90m** | 腿根 |
| 膝高度 | **0.50m** | 腿弯 |
| 踝高度 | **0.12m** | 进鞋 |
| 大腿直径 | **0.18m** | 毛腿 |
| 小腿直径 | **0.14m** | 毛腿 |
| 腰胯高度 | **0.85–1.00m** | 藏在壳内 |
| 牌子 | **0.60 × 0.40 × 0.02m** | 空白板 |
| 牌杆 | **0.40m** | 细杆 |
| 体重感 | **123kg** | 动画重量感，不做物理 |

---

## 6. 颜色与材质

### 6.1 色板

| 部位 | 基色 | 阴影 | 高光 | 备注 |
|---|---|---|---|---|
| 壳 | `#E9E9E9` | `#CFCFCF` | `#FAFAFA` | 暖灰白，不纯白 |
| 嘴/鸭蹼 | `#FBC55B` | `#D99A2B` | `#FFD77A` | 暖黄 |
| 描边 | `#2B2B2B` | — | — | 深灰近黑 |
| 眼白 | `#FFFFFF` | — | — | 比壳更白 |
| 瞳孔 | `#111111` | — | — | 小圆点 |
| 睫毛 | `#2B2B2B` | — | — | 3 根/眼 |
| 内衬 | `#262626` | — | — | 深色，防看穿 |
| 皮肤 | `#C98E6B` | `#A86F50` | — | 毛腿 |
| 毛发 | `#2A211C` | — | `#4A3A30` | 深棕黑 |
| 短裤/腰胯 | `#3A3A3A` | — | — | 藏在壳内 |
| 牌子 | `#F7F5EE` | `#D8D4C8` | — | 空白 |
| 伞（v2） | `#A83D49` | — | `#D1908B` | 红色点缀 |

### 6.2 材质

| 材质 | 粗糙度 | 金属度 | 说明 |
|---|---:|---:|---|
| 壳布料 | 0.85 | 0 | 哑光；v1.5 可加轻微织纹 |
| 嘴/鸭蹼 | 0.55 | 0 | 微哑光，不要塑料感 |
| 眼睛 | 0.20 | 0 | 亮一点，但不写实 |
| 内衬 | 0.95 | 0 | 深色，不反光 |
| 皮肤 | 0.65 | 0 | 风格化，不做次表面 |
| 毛发 | 0.70 | 0 | 几何毛簇，不做发丝 |
| 牌子 | 0.80 | 0 | 空白、不反光 |
| 伞（v2） | 0.80 | 0 | 布料 |

### 6.3 渲染风格

- 赛璐璐/平涂为主，细描边；v1 可以用 Workbench/MatCap 快速看形。
- 白壳靠描边、边缘光和接触阴影和背景分开。
- 不要用 Tripo 的 PBR 纹理；不要烘焙光照。
- 最终引擎里再做 toon shader；Blender 里先保证色块和剪影。

---

## 7. 3D 构造方案

### 7.1 分件与面数预算

| 对象名 | 内容 | 优先级 | 面数预算（v1） |
|---|---|---|---:|
| `SUIT_Shell` | 白色长蛋形壳，开底口 | P0 | 2k–4k |
| `SUIT_Liner` | 深色内衬 | P0 | 300–600 |
| `SUIT_Bill_Upper` | 上嘴 | P0 | 300–500 |
| `SUIT_Bill_Lower` | 下嘴 | P0 | 300–500 |
| `SUIT_Eye_L/R` | 眼白 + 瞳孔 | P0 | 150–250 each |
| `SUIT_Lash_L/R` | 三根睫毛 | P0 | 20–40 each |
| `SUIT_Arm_L/R` | 白色鳍状袖套 | P0 | 400–700 each |
| `DUCKSHOE_L/R` | 黄色鸭蹼鞋 | P0 | 500–800 each |
| `INNER_Leg_L/R` | 毛腿 | P0 | 800–1.2k each |
| `INNER_Hair` | 风格化毛簇 | P1 | 100–200 total |
| `INNER_Pelvis` | 隐藏腰胯/短裤 | P1 | 200–400 |
| `PROP_Sign` | 空白板 + 杆 | P1 | 30–60 |
| `PROP_Umbrella` | 红伞 | P2 | 300–500 |
| `INNER_Head` | 大叔头/发光眼 | P2 | 1k–2k |

**v1 总预算：8k–12k tris。**

### 7.2 外壳构造

1. UV 球或圆柱起形，32 段 × 16–20 环。
2. 拉成 1.8m 长蛋形，最大宽度 0.85m，深度 0.70m。
3. 删掉底部 2–3 圈面，形成 0.50m × 0.38m 的宽椭圆底口。
4. 选中边界，向下挤出一点，做下摆卷边。
5. `Solidify` 2cm，应用。
6. 内层复制一份，法线翻转，深色内衬；或用单独的低模内衬。
7. 检查底口：从下往上看，必须是暗的、有厚度的，不是纸片。
8. 背面保持干净；不要加羽毛/拉链。

**不要用布尔挖洞。** 直接建开口的壳更干净。

> **v1 实现修订（2026-11-09）**：外壳改成“参数化闭合剖面旋转”——外壁 + 2cm 内壁 + 底口内折裙摆，**不再用 Solidify**。原因：底口要同时满足“外轮廓约 0.87m 宽”和“可见开口 0.50×0.38m”，Solidify 只能等厚偏移，没法把 0.87m 的裙摆收到 0.50m；内折剖面一次成型，开口尺寸精确可控。
>
> 外形轮廓改为按 `art/refs/eliz_front.jpg` 逐行量宽拟合：身躯是近直筒的胶囊（最大宽 0.85m 一直延续到 z≈1.03），顶部是“椭球顶”（`DOME_C=1.03`、`DOME_H=0.77`、剖面指数 0.5），比原先“整颗蛋”的中间粗两头细更接近参考图。壳深按 0.70/0.85 的比例联动。


### 7.3 嘴与眼睛

- 上嘴：压扁的球/椭球，固定到壳。
- 下嘴：单独一件，铰链在嘴角后方，挂 `jaw` 骨。
- 嘴中间留一条闭合线；下嘴颜色略深。
- 内腔：深色，张嘴时不能看穿。
- 眼睛：独立圆片/半球，眼白纯白；瞳孔小圆片；睫毛用曲线转网格。
- v1 眼睛固定；眨眼用形态键或眼睑片，v1.5 再加。

### 7.4 手臂

- 单独鳍状胶囊，一根骨头。
- 肩部伸进壳内 5cm，用球窝重叠遮住接缝。
- 不做手指；末端可以稍微弯，夹住牌杆。
- 手臂不焊进壳；权重 100% 给手臂骨。

### 7.5 鸭蹼鞋

- 单独做鞋，不要从壳上切。
- 三趾、趾间有蹼；鞋底略平，能落地。
- 脚踝开口/卷边，毛腿从里面伸进去。
- 鞋 100% 权重给脚骨。
- 鞋和腿之间允许有轻微穿插，但跑步时不能脱节。

### 7.6 毛腿

- 髋到踝：大腿、膝盖、小腿、脚踝。
- 8–12 边圆柱起形，膝盖/脚踝留环线。
- 毛簇：12–16 簇/腿，几何毛片或低模毛簇；不要粒子毛发。
- 皮肤和毛发分开材质；毛发深色，边缘稍微不规则。
- 腰胯用深色短裤/内衬遮住；不要做完整上身。

### 7.7 牌子

- 平板 + 细杆；板 0.60 × 0.40 × 0.02m。
- 杆 0.40m，挂在右手袖口末端。
- v1 空白；文字以后用引擎 UI。
- 牌面朝向镜头时，文字区域要平整，不要有厚边框。

### 7.8 命名与集合

```text
SUIT_*
INNER_*
DUCKSHOE_*
PROP_*
RIG_Eliz
REF_*
```

集合：

```text
SUIT
INNER
PROPS
RIG
REF
```

单位：米；角色朝 `-Y`；脚底在 `Z=0`；所有变换应用；不要负缩放。

- 场景单位保持 `Metric / Scale 1.0`；不要用 `Scale 0.01` 之类的“假单位”。
- Blender 里以 **-Y 为角色正面**；导出 glTF/GLB 时由导出器自动转成 +Y up，角色正面落在 **+Z**。**不要**在导出前手动旋转模型。
- 导出前检查：`Scale = 1`、`Rotation = 0`、脚底 `Z = 0`、身高 `1.8m`。

### 7.9 落盘与坐标约定（Windows）

- 文件名全小写、下划线分隔（`build_eliz_v1.py`、`eliz_costume_v1.blend`）；对象名按 7.8 节前缀大写。
- 产物一律写到仓库内（`art\renders\`、`art\exports\`、`art\blender\`），**不要**写到 `%TEMP%` 或桌面，否则脚本重跑不可复现。
- 脚本内路径用 `pathlib.Path` 拼接，避免手写反斜杠；日志里的路径打印用 `str(path)`。

---

## 8. 绑定方案

### 8.1 骨骼层级（v1，约 13–15 根）

```text
root
  pelvis
    thigh_L
      shin_L
        foot_L
    thigh_R
      shin_R
        foot_R
    shell
      jaw
      arm_L
      arm_R
        sign_socket
      umbrella_socket（v2，可选）
```

说明：

- `shell` 是壳的主骨，壳和内衬 100% 权重给它。
- `shell` 直接挂在 `pelvis` 下；跑步时动画 `shell` 的局部 Z 位移和旋转。
- `jaw` 控制下嘴；上嘴跟壳。
- `arm_L/R` 控制鳍状袖套；牌子挂 `sign_socket`。
- 腿骨只影响毛腿，不影响壳。
- 不做 `spine/head` 骨；壳是刚体。若后期要点头，再加 head 骨并拆壳，v1 不做。

### 8.2 权重

| 对象 | 权重 |
|---|---|
| `SUIT_Shell` | 100% `shell` |
| `SUIT_Liner` | 100% `shell` |
| `SUIT_Bill_Upper` | 100% `shell` |
| `SUIT_Bill_Lower` | 100% `jaw` |
| `SUIT_Eye/Lash` | 100% `shell` |
| `SUIT_Arm_L/R` | 100% `arm_L/R` |
| `DUCKSHOE_L/R` | 100% `foot_L/R` |
| `INNER_Leg_L/R` | 平滑权重到 thigh/shin/foot |
| `INNER_Pelvis` | 100% `pelvis` |
| `PROP_Sign` | 100% `sign_socket` |

### 8.3 壳抬升参数

- 待机：壳底口 `Z=0.15m`。
- 走路：`Z=0.15–0.18m`，轻微上下。
- 跑步：`Z=0.32m`，后仰 8°。
- 跳跃/大动作：`Z=0.45–0.50m`，露膝。
- 壳抬到最高时，腿不能穿出壳；如果穿，先加宽底口。

### 8.4 约束与导出

- 牌子用骨骼父子或 `Child Of`；导出前烘焙。
- 不要用引擎不支持的复杂约束。
- 所有修改器应用，Armature 修改器保留。
- 导出 GLB/FBX 前检查：缩放 1、朝向、骨骼命名、动画片段。

---

## 9. 动画清单与优先级

| 动画 | 优先级 | 帧数 @30fps | 内容 | 验收 |
|---|---|---|---:|---|
| `idle` | P0 | 60 | 壳垂到底，轻微呼吸，眨眼可选 | 看不到毛腿 |
| `run` | P0 | 24 | 壳抬 17cm、后仰 8°，腿循环 | 毛腿露出 ≥15cm |
| `walk` | P1 | 30 | 壳轻微上下 3cm，鸭步 | 腿基本藏住 |
| `jump` | P1 | 30 | 壳上弹、腿收起、落地压扁 | 不穿模 |
| `sign_talk` | P1 | 45 | 举空白牌，翻牌 2 次 | 牌不穿头 |
| `hit` | P2 | 15 | 壳晃，毛腿弹一下 | 喜剧感 |
| `reveal` | P2 | 60 | 壳抬 0.50m，露膝 | 可选，不做脸 |

动画原则：

- 静止是常态；不要加过多 idle 弹跳。
- 举牌要快、硬切，停 0.5–1 秒。
- 跑步有 123kg 重量感：身体左右倾 3–5°，脚抬 10cm。
- 壳的弹跳和脚步错开半拍，才有“衣服在晃”的感觉。
- “露腿”是跑步的自然结果，不是切换形态。

---

## 10. 制作管线

### 10.1 推荐路线

```text
参考图/规格冻结
→ Blender blockout（壳/底口/内衬/嘴眼/手脚/腿）
→ 比例确认（四视图 + 跑步姿势）
→ 细化（鞋/毛/牌子/材质）
→ 绑定（壳腿分离）
→ 动画测试（P0：idle/run）
→ 导出 GLB/FBX
```

### 10.2 Tripo 的角色

- **v1 外壳不用 Tripo**：它是简单几何，Blender 直接建更快、更可控。
- Tripo 可选：
  1. 生成 2–3 个比例参考，只看剪影；
  2. 后期做内里大叔头部/有机细节；
  3. 给朋友看立体草稿。
- 不要把 Tripo 的封闭壳直接当最终资产；不要用它的自动绑定和 PBR 纹理。

### 10.3 文件结构（Windows）

```text
D:\work\eliz_game\
  .git\                       ← 已初始化
  .gitignore
  README.md
  docs\
    character_spec.md         ← 本文件
    HANDOFF.md
  art\
    refs\                     ← 4 张参考图（已入库）
      README.md
      eliz_front.jpg
      eliz_anime.jpg
      eliz_umbrella.png
      eliz_sign.webp
    blender\                  ← 脚本生成：.blend
      eliz_costume_v1.blend
    exports\                  ← 脚本生成：.glb / .fbx
      eliz_costume_v1.glb
    renders\                  ← 脚本生成：预览 PNG
      v1_front.png
      v1_side.png
      v1_back.png
      v1_three_quarter.png
      v1_run_reveal.png
      v1_sign_pose.png        ← 牌子/袖口姿态检查（加宽画幅）
  scripts\                    ← bpy 脚本
    build_eliz_v1.py          ← 建模 + 渲染 + 导出（v1 主入口）
    render_views.py           ← 只重渲 v1_* 图，不重建
    verify_export.py          ← 重导入 GLB，校验尺寸/骨骼/动画/面数
    check_asset.py            ← 验收检查：拓扑/权重/变换/壳腿隔离/鞋跟脚/下颌/遮挡
  tools\                      ← 可选、不入库：Blender 便携版解压目录
```

约定：

- `art\blender\`、`art\exports\`、`art\renders\` 由脚本自己 `mkdir(parents=True, exist_ok=True)` 创建，**不要手工建空目录**（Git 也不跟踪空目录）。
- 产物一律落在仓库内，不要写到桌面或 `%TEMP%`，否则无法复现、也无法和文档对账。
- `tools\`（Blender 便携版）加入 `.gitignore`，**不要**把 Blender 本体提交进仓库。
- `.gitignore` 已忽略 `*.blend1`、`*.blend2`、`*.tmp`、`__pycache__/`；GLB/PNG 变多以后，再决定是入库还是忽略。

### 10.4 环境与工具链（Windows 基线）

本规格书以如下机器为基线；换机器时只替换路径，设计数值不变。

| 项 | 实测值 | 说明 |
|---|---|---|
| 操作系统 | Windows 11 IoT 企业版 LTSC，10.0.26100（24H2），x64 | 不是 macOS；不要用 `/Applications`、Homebrew 命令 |
| CPU | Intel Core i5-13500H，12 核 16 线程 | 后台渲染可吃满 |
| 内存 | 16 GB（可用约 15.7 GB） | 够跑 8k–12k tris 的 blockout |
| GPU | Intel Iris Xe Graphics（集显，共享显存约 2GB，驱动 32.0.101.6733） | 支持 OpenGL 4.6，可用 EEVEE Next |
| 磁盘 | C: 剩余约 85 GB；D: 剩余约 287 GB | 仓库在 D:，Blender 便携版也建议放 D: |
| Shell | Windows PowerShell 5.1 | 命令按 PS 5.1 语法；不用 bash 语法 |
| Git | 2.56.0.windows.4，`C:\Program Files\Git\cmd\git.exe` | **不在 PATH**，需全路径调用或手动加 PATH |
| Git 身份 | **未配置**（system/local/global 均无 `user.name`/`user.email`） | 提交前必须先设置 |
| Python（系统） | 3.14.7，`C:\Python314\python.exe` | 只用于辅助脚本；**不能 `import bpy`** |
| Python（Blender 内置） | 3.11（随 Blender 4.5） | 所有建模脚本在 Blender 内运行 |
| Chocolatey | 2.7.4 | 其 `blender` 包当前是 5.2.3，**不满足 4.5 LTS 基线**，不作首选 |
| Blender | **未安装** | 基线：Blender 4.5.15 LTS（2026-10-22 发布） |

#### 10.4.1 安装 Blender 4.5 LTS（windows-x64）

两个方案二选一；**推荐 A（便携版）**：无需管理员权限、路径固定、可多版本并存、删目录即卸载。

**A. 便携版 zip（推荐）**

1. 下载 <https://download.blender.org/release/Blender4.5/blender-4.5.15-windows-x64.zip>（约 399 MB），连同同目录的 `blender-4.5.15.sha256` 一起放到下载目录。
2. 校验 SHA256（`-match` 默认忽略大小写，能直接命中 `.sha256` 文件里的那一行）：
   ```powershell
   $zip  = ".\blender-4.5.15-windows-x64.zip"
   $hash = (Get-FileHash $zip -Algorithm SHA256).Hash
   if ((Get-Content .\blender-4.5.15.sha256) -match $hash) { "sha256 OK" }
   else { throw "sha256 mismatch" }
   ```
3. 解压到 `D:\tools\`：
   ```powershell
   New-Item -ItemType Directory -Force D:\tools | Out-Null
   Expand-Archive .\blender-4.5.15-windows-x64.zip -DestinationPath D:\tools
   ```
   得到 `D:\tools\blender-4.5.15-windows-x64\blender.exe`。
4. 验证：
   ```powershell
   & "D:\tools\blender-4.5.15-windows-x64\blender.exe" --version
   ```

**B. MSI 安装包**

- <https://download.blender.org/release/Blender4.5/blender-4.5.15-windows-x64.msi>（约 360 MB）。
- 默认装到 `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`。

**加入 PATH（可选，图省事才做）**

```powershell
$dir = "D:\tools\blender-4.5.15-windows-x64"
[Environment]::SetEnvironmentVariable(
  "Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$dir", "User")
```

改完要**新开终端**才生效；脚本里不要依赖 PATH，一律写全路径。

#### 10.4.2 Git 与仓库

- `git` 不在 PATH：用 `& "C:\Program Files\Git\cmd\git.exe" ...`，或把 `C:\Program Files\Git\cmd` 加进 PATH。
- 远程已配置：`git@github.com:TNTSAYou/eliz_game.git`；分支 `main`，与 `origin/main` 同步。
- 本机**没有 Git 身份**，提交前先设置：
  ```powershell
  & "C:\Program Files\Git\cmd\git.exe" config --global user.name "你的名字"
  & "C:\Program Files\Git\cmd\git.exe" config --global user.email "you@example.com"
  ```
- 系统级 `core.autocrlf=true`：仓库内 `.md`/`.py` 以 LF 存储、检出为 CRLF。Blender 不受影响，但脚本不要依赖行尾。

#### 10.4.3 渲染与 GPU

- 引擎 ID：EEVEE = `BLENDER_EEVEE_NEXT`，Workbench = `BLENDER_WORKBENCH`，Cycles = `CYCLES`。
- Iris Xe 是集显、共享内存：blockout 阶段用 **Workbench**（最快、剪影最干净）或 **EEVEE Next @ 800px**；不要开 4K 贴图、高细分、体积雾。
- Cycles 用 CPU（i5-13500H）做对照即可，不作默认；显存不足会回退或报 `Out of memory`。
- 渲染输出写绝对路径到 `art\renders\`，PNG；色彩管理（Standard 或 AgX）**固定一种**，保证多版本可比。

#### 10.4.4 脚本约定（bpy + PowerShell）

- 脚本保存为 **UTF-8（无 BOM）**；控制台中文可能乱码，日志优先英文（或先 `chcp 65001`）。
- 不要用 bash 语法（`export`、`$VAR`、反斜杠续行）；PowerShell 续行用反引号，且**反引号后不能有空格**。
- 调外部程序用 `&`，并检查 `$LASTEXITCODE`；不要用 `Start-Process`（拿不到退出码）。
- Python 里 Windows 路径用 `pathlib.Path` 或原始字符串 `r"D:\work\eliz_game\art\renders"`；不要写未转义的 `"D:\work\..."`。
- 用 `PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]` 定位仓库根，其余路径都从它拼。
- 后台模式无 GUI 上下文：批量操作优先用 `bpy.data` API；必须用 `bpy.ops` 时用 `bpy.context.temp_override(...)`。
- 渲染前显式设置 `scene.render.filepath`、`image_settings.file_format = 'PNG'`、`resolution_percentage`，再 `bpy.ops.wm.save_as_mainfile`。
- 导出 GLB：`bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', export_apply=True)`；确认没有残留 `Solidify`/`Mirror` 修改器。
- 需要干净复现时用 `--factory-startup`；用户配置在 `%APPDATA%\Blender Foundation\Blender\4.5\`。
- 仓库与 Blender 都放纯 ASCII 路径（当前 `D:\work\eliz_game` 已满足），不要放中文目录或 OneDrive。

### 10.5 常用命令（PowerShell）

```powershell
# 0) 进入仓库
Set-Location D:\work\eliz_game

# 1) 选择 Blender（便携版 / 安装版二选一）
$Blender = "D:\tools\blender-4.5.15-windows-x64\blender.exe"
# $Blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# 2) 版本检查
& $Blender --version

# 3) 冒烟测试：确认 bpy 可用
& $Blender --background --factory-startup --python-expr "import bpy; print('BPY', bpy.app.version_string)"

# 4) 建模 + 渲染 + 导出（正式入口）
& $Blender --background --factory-startup --python-exit-code 1 `
    --python "D:\work\eliz_game\scripts\build_eliz_v1.py"
if ($LASTEXITCODE -ne 0) { throw "build_eliz_v1.py failed: $LASTEXITCODE" }

# 5) 只重渲视图，不重建模型
& $Blender --background "D:\work\eliz_game\art\blender\eliz_costume_v1.blend" `
    --python-exit-code 1 --python "D:\work\eliz_game\scripts\render_views.py"

# 6) 检查产物
Get-ChildItem .\art\renders, .\art\exports, .\art\blender |
    Select-Object Name, Length, LastWriteTime
```

要点：

- 必须带 `--background`（无界面）；带 GUI 启动会挂着等操作，脚本里会“假死”。
- `--python-exit-code 1` 让脚本异常时返回非 0，PowerShell 才能 `throw`。
- `--factory-startup` 屏蔽用户插件和启动文件，保证可复现。
- 长命令换行用反引号，**反引号后不能有空格**；不确定就直接写一行。
- 首次运行若被 SmartScreen / 杀软拦，给 Blender 目录加白名单。
- 若需要中文日志，先 `chcp 65001`，并把控制台字体换成支持中文的字体。

---

## 11. 验收标准

### 11.1 造型

- [ ] 2m 距离看，正面/背面/3/4 都能认出是伊丽莎白。
- [ ] 长蛋形、无脖子、无腰、无可见腿。
- [ ] 眼睛小瞳孔、三根睫毛、无眉毛。
- [ ] 嘴宽扁、黄色、不是尖鸟喙。
- [ ] 手臂是鳍状，不是人手。
- [ ] 鸭蹼鞋三趾有蹼，不是人脚。
- [ ] 背面干净，没有多余羽毛/拉链。

### 11.2 结构

- [ ] 壳是空心，有 2cm 厚度和深色内衬。
- [ ] 底口 0.50 × 0.38m，能过两条腿。
- [ ] 待机壳底口在 0.15m，看不到毛腿。
- [ ] 跑步壳抬到 0.32m，毛腿露出 ≥15cm。
- [ ] 壳抬到最高时，腿不穿出壳。
- [ ] 鸭蹼鞋跟脚，不滑动、不脱离。
- [ ] 牌子挂在袖口，不穿头。

### 11.3 绑定与动画

- [ ] 壳 100% 权重给 `shell`，腿不影响壳。
- [ ] 腿平滑权重，膝盖/脚踝弯曲不破面。
- [ ] 下嘴能开 25°（说话）/55°（彩蛋）。
- [ ] `idle/walk/run/jump` 循环接得上。
- [ ] 跑步脚不滑步。
- [ ] 30fps 下动作不抖。

### 11.4 资产

- [ ] 8k–12k tris；四边面为主；无多余 n-gon。
- [ ] 对象/集合命名规范；无隐藏垃圾。
- [ ] 所有变换应用；脚底 Z=0；身高 1.8m。
- [ ] GLB 导入 Blender 后比例、材质、动画正常。
- [ ] `.blend` 可复现；脚本可重跑。
- [ ] 在 Windows 本机按 10.5 节命令重跑，能从零生成 `.blend`、`.glb` 和 5 张渲染图，且退出码为 0。
- [ ] 产物路径与 10.3 节一致（`art\blender\`、`art\exports\`、`art\renders\`），文件名不改。

---

## 12. 待确认决策

| # | 决策 | 推荐 | 备选 | 状态 |
|---|---|---|---|---|
| 1 | 视觉方向 | A 动画还原 + B 下摆质感 | 纯 A / C 黑色喜剧 | 待确认 |
| 2 | 跑步壳抬升 | 0.32m（露小腿） | 0.45m（露膝，更夸张） | 待确认 |
| 3 | 毛腿密度 | 中等偏多，2m 可见 | 少量 / 很浓密 | 待确认 |
| 4 | 牌子 | v1 做空白牌 | v1 不做，v2 再加 | 待确认 |
| 5 | 内里服装 | 深色短裤 + 裸毛腿 | 全裸腿 / 加袜子 | 待确认 |
| 6 | 脸 | 固定壳脸 + 可动下嘴 | 可掀 hood（v2） | 待确认 |
| 7 | 伞 | v2 再做 | v1 一起做 | 待确认 |
| 8 | 背面 | 纯白，无尾巴 | 加小尾巴 | 待确认 |
| 9 | Tripo | 外壳不用；后期可选内里头 | 先生成比例参考 | 待确认 |
| 10 | 最终用途 | 先做 Blender 资产，不接引擎 | 同时做引擎测试 | 待确认 |

---

## 13. 风险与规避

| 风险 | 表现 | 规避 |
|---|---|---|
| 壳太窄 | 跑步大腿穿出壳 | 底口加到 0.50m 以上；先做抬腿测试 |
| 壳太短 | 待机就露腿 | 下摆压到 0.15m；鞋面遮住 |
| 鞋焊在壳上 | 跑步像滑行 | 鞋独立，绑脚骨 |
| 壳腿一起蒙皮 | 腿动壳变形 | 壳 100% 给 shell，腿独立 |
| 没内衬 | 壳一抬就看穿 | 深色内衬 + 内腔 |
| 毛太真实 | 变成毛茸茸的腿 | 几何毛簇，12–16 簇/腿 |
| 眼太大/有眉毛 | 变成可爱企鹅 | 小瞳孔、三睫毛、无眉 |
| 身体纯白 | 亮场景过曝 | 暖灰白 + 描边 + 边缘光 |
| 背面没做 | 第三人称主视图难看 | 必须渲染背面 |
| Tripo 融合 | 壳/脚/腿粘一起 | 外壳不用 Tripo；只做参考 |
| 范围膨胀 | 先做脸/伞/攻击 | v1 只做壳/腿/鞋/牌/跑 |

---

## 14. 下一步

1. 用户确认第 12 节的 10 个决策（至少确认 1–5）。
2. 安装 Blender **4.5.15 LTS（windows-x64）**：推荐便携版解压到 `D:\tools\blender-4.5.15-windows-x64\`，或用 MSI 装到 `C:\Program Files\Blender Foundation\Blender 4.5\`；详见 10.4.1。
3. 在 PowerShell 里验证：`& "D:\tools\blender-4.5.15-windows-x64\blender.exe" --version`。
4. 写 `scripts\build_eliz_v1.py`，生成 blockout；用 10.5 节的命令跑。
5. 渲染四视图 + 跑步露腿姿势到 `art\renders\`。
6. 用户确认比例后，再做材质、毛腿细化、绑定和动画。

---

## 15. 参考

### 本地图片

- [正面全身图](../art/refs/eliz_front.jpg)
- [动画截图](../art/refs/eliz_anime.jpg)
- [撑伞行走图](../art/refs/eliz_umbrella.png)
- [举牌半身图](../art/refs/eliz_sign.webp)

> 说明：参考图原先放在旧 macOS 机器的 `/Users/wzh/Downloads/eliz_pic`，该路径在当前 Windows 机器上不存在；仓库内 `art/refs/` 是唯一权威副本。

### 网络资料

- [中文维基：银魂角色列表](https://zh.wikipedia.org/wiki/%E9%93%B6%E9%AD%82%E8%A7%92%E8%89%B2%E5%88%97%E8%A1%A8)
- [アニ図鑑：エリザベス](https://anizukan.com/characters/12237/elizabeth)
- [RENOTE：エリザベス考察](https://renote.net/articles/10712/page/2)
- [English Wikipedia: List of Gintama characters](https://en.wikipedia.org/wiki/List_of_Gintama_characters)

### 工具

- [Blender 4.5 LTS 下载目录](https://download.blender.org/release/Blender4.5/)
- [Blender 4.5 手册](https://docs.blender.org/manual/en/4.5/)
- [Tripo 图像转 3D](https://www.tripo3d.com/features/image-to-3d-model)
- [Tripo 智能网格](https://www.tripo3d.com/features/smart-mesh)
- [Tripo 新手教程](https://www.tripo3d.com/blog/first-3d-model-ai-tutorial)

---

## 16. IP 说明

伊丽莎白是空知英秋/集英社《银魂》的角色。个人同人、学习、非商业原型通常没问题；商业化发行需要版权授权。Tripo 生成物的商用权取决于套餐条款，使用前需确认。

---

## 17. v1 产出记录（2026-11-09）

### 17.1 产物

| 文件 | 说明 |
|---|---|
| `art\blender\eliz_costume_v1.blend` | 场景：SUIT / INNER / PROPS / RIG / RENDER 集合，含渲染相机与三盏灯 |
| `art\exports\eliz_costume_v1.glb` | 约 287 KB；23 个网格对象 + 1 个骨架（13 骨）；2 个动画 |
| `art\renders\v1_*.png` | 6 张：front / side / back / three_quarter / run_reveal / sign_pose |

### 17.2 实测数据

- 总高 **1.800 m**（脚底 Z=0，头顶 Z=1.800）；壳宽 0.850 m、壳深 0.700 m。
- 总面数 **8,364 tris**：壳 3,600 / 裙摆卷边 432 / 鞋 1,024 / 腿 784 / 头发 360 / 其余见脚本 `STATS:` 输出。
- 骨骼 **13 根**：`root, pelvis, thigh/shin/foot L/R, shell, jaw, arm L/R, sign_socket`。
- 动作：`idle` 60 帧（2.0 s）、`run` 24 帧（0.8 s）@30fps，随 GLB 导出。
- 底口：外沿约 0.87 × 0.71 m，**内开口 0.50 × 0.38 m**（靠裙摆内折收口，见 §7.2 的实现修订）。
- 待机壳底 0.15 m；跑步壳抬 **0.19 m**（底口 0.34 m），实测可见小腿 **0.184 m**。

### 17.3 校验

- `scripts\verify_export.py` 重新导入 GLB：height=1.800、min_z=0.000、bones=13、actions=[idle, run]、tris=8,364、11 个材质 → `VERIFY_OK`。
- `scripts\check_asset.py` 逐项验收：n-gon=0、权重和=1、变换已应用、壳动腿不动（Δ=0）、鞋跟脚（Δ=0.55 m）、下颌只带动下嘴（上嘴 Δ=0）、待机可见皮肤/毛=0 条射线、跑步可见 39 条、露出 **0.184 m**、run 循环首尾一致（f1==f25）→ `CHECK_OK`。
- 六张渲染人工目视：待机只见白壳 + 鸭蹼，看不到皮肤/毛腿；跑步图可见小腿与毛簇。

### 17.4 已知简化（v1.5 再改）

- 鸭蹼鞋是“三趾 + 蹼”的简化块面，正面看偏低矮，趾缝不够锐利。
- 牌子挂在袖口末端，但静态渲染里连接杆被板面挡住，看起来像“浮在身侧”；需要抬手姿态或专门的握持约束。
- 眼睛是贴合壳面的贴片 + 深色描边环，没有眼睑 / 眨眼形态键。
- 材质只有基础 Principled 色块，没有赛璐璐描边与织纹（§6.3 的 v1.5 目标）。
- 头发是四边锥毛簇，边缘偏硬。

### 17.5 复现命令

```powershell
Set-Location D:\work\eliz_game
$B = "D:\tools\blender-4.5.15-windows-x64\blender.exe"
& $B --background --factory-startup --python-exit-code 1 --python "scripts\build_eliz_v1.py"
& $B --background --factory-startup --python-exit-code 1 --python "scripts\verify_export.py"
& $B --background --factory-startup --python-exit-code 1 --python "scripts\check_asset.py"
& $B --background --factory-startup --python-exit-code 1 --python "scripts\render_views.py"
```
