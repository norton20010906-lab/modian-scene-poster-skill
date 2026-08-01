---
name: modian-scene-poster
description: 为魔点门禁刷脸门禁机生成中文产品使用场景海报。只要用户提供产品图片或商品截图、产品型号，并要求门禁海报、刷脸门禁场景图、魔点产品宣传图或类似营销视觉，就应使用本 Skill；它会收集并分级核验产品证据、分析外观、从可信资料库提炼卖点、用内置图像生成能力制作无字场景，再以本地脚本确定性排版。不要用于其他品牌、视频、通用修图或未经核验的型号。
compatibility: Requires image viewing, built-in image generation, Python 3.10+, and Pillow. Read-only web search is recommended for evidence refresh; no external model API key.
---

# 魔点门禁产品场景海报

为一个已验证型号生成一张 1080×1350 中文使用场景海报。事实正确性优先于文案创意：产品能力只来自 `data/products.yaml`，图片观察只能描述外观。

## 输入

收集且只收集：

- 产品图片路径或对话中附件
- 产品型号
- 可选的一句话补充需求（最多 200 字）

如果缺少图片或型号，先请用户补齐。不要把补充需求解释为新增产品能力。

## 准备

把本文件所在目录记为 `SKILL_ROOT`。为本次运行创建 `output/<UTC时间戳>/`，后续中间文件都写入该目录，不覆盖旧结果。

先运行：

```text
python <SKILL_ROOT>/scripts/validate_input.py --image <图片> --model <型号> --requirement <补充需求>
python <SKILL_ROOT>/scripts/load_product_info.py --catalog <SKILL_ROOT>/data/products.yaml --model <型号>
```

任何命令失败都停止正式生成，并把错误原样解释给用户。特别是未收录或未启用型号，不做模糊匹配、不凭常识补全；可以进入资料收集流程，但在资料通过核验并写入目录前不生成正式海报。

## 执行流程

### 1. 检查输入图片

如果图片位于本地文件系统，先用 `view_image` 查看，使图片进入当前对话视觉上下文。按 `references/visual_analysis_schema.md` 生成 `analysis.json`。

只记录可见外观：机身形状、颜色、屏幕、摄像头、边框、安装朝向、遮挡和背景干扰。不要从外观推断识别速度、容量、协议、考勤或其他规格。

商品截图若无法可靠区分产品主体与页面 UI，停止并要求更清晰的单独产品图。

### 2. 收集与核验产品信息

读取 `references/product_research_workflow.md`，执行受控的证据收集：

1. 先从用户图片提取可见事实，再读取本地产品记录。
2. 使用品牌全称和精确型号做最多 3 次只读定向搜索，官方来源优先；不要进行开放式漫游搜索。
3. 把候选功能拆成逐条声明，标记来源类型、URL、核验日期和支持范围。
4. 只有被已验证来源直接支持的声明才能写入 `selling_points`；经销商或媒体来源只能作为线索，不能单独支撑高风险参数。
5. 每条卖点必须通过 `source_ids` 引用一个或多个已验证来源。若证据冲突、缺少 3 条卖点或仅有搜索摘要，停止正式生成。

对于已收录型号，本地资料库仍是生成时唯一事实输入；搜索用于刷新和审计资料库，而不是让文案模型临场自由发挥。把本次检索摘要、采用/拒绝的声明和来源写入运行目录 `research.json`。

### 3. 选择场景与文案

读取：

- `references/scene_and_copy_rules.md`
- 当前型号在 `data/products.yaml` 中的完整记录

从 `recommended_scenes` 中选择一个场景。没有明确补充要求时使用列表第一项。

生成 `scene_plan.json` 和初始 `copy.json`。`copy.json` 中的卖点只写 `selling_point_ids`，不要自行改写卖点正文。随后运行：

```text
python <SKILL_ROOT>/scripts/validate_content.py \
  --content <运行目录>/copy.json \
  --catalog <SKILL_ROOT>/data/products.yaml \
  --model <型号> \
  --output <运行目录>/copy.validated.json
```

后续仅使用 `copy.validated.json`。

### 4. 生成无字场景主视觉

读取 `references/product_prominence_rules.md` 和 `references/image_prompt_template.md`，将产品图片标记为产品参考或编辑目标。使用宿主内置 `image_gen`，不要调用 CLI、SDK 或要求 API Key。

生成要求：

- 真实企业入口、前台或办公门口环境
- 产品是场景主角而非背景道具：建议占画面宽度 20%～30%，低于 18% 必须重做
- 屏幕、传感器、边框和参考图中真实存在的品牌标识必须可辨
- 人物用半身或肩部视角明确朝向设备，形成正在刷脸的视觉关系，不能用全身远景稀释产品
- 竖版构图，为顶部标题和底部卖点留出低细节区域
- 无生成文字、无虚构 Logo、无水印、无功能图标；识别状态由排版脚本后加
- 保留 `analysis.json` 中列出的关键外观特征

把选中的场景图复制到运行目录 `scene.png`。项目资产不能只留在宿主默认生成目录。

### 5. 检查产品一致性

用 `view_image` 查看 `scene.png`，逐项比较 `analysis.json.identity_anchors`：轮廓、屏幕比例、摄像头位置、主色和安装朝向。同时在 `analysis.json.scene_product_bbox_normalized` 记录场景中产品框 `[x1, y1, x2, y2]`；宽度不足 18% 时，即使场景真实也判定不合格。

- 合格：在 `analysis.json` 中记录 `fallback_used: false`。
- 明显漂移：仅针对漂移项定向编辑一次，其他内容保持不变。
- 第二次仍不合格：按 `references/failure_recovery.md` 使用原产品裁切合成回退，并记录 `fallback_used: true`。

不要进行第三次生成。

### 6. 确定性排版

运行：

```text
python <SKILL_ROOT>/scripts/compose_poster.py \
  --background <运行目录>/scene.png \
  --content <运行目录>/copy.validated.json \
  --product <运行目录>/analysis.json \
  --brand <SKILL_ROOT>/data/brand_profile.yaml \
  --output <运行目录>/poster.png
```

图像模型不负责中文文字。`copy.json` 可选使用 `status_badge`，值只能为“识别成功”“打卡成功”或“欢迎通行”；脚本会根据产品框把状态标签放在产品附近。若排版脚本报告溢出，缩短标题或副标题后重新执行内容校验和排版；不要缩小到不可读字号。

### 7. 最终验收

运行：

```text
python <SKILL_ROOT>/scripts/verify_output.py \
  --poster <运行目录>/poster.png \
  --manifest <运行目录>/manifest.json \
  --catalog <SKILL_ROOT>/data/products.yaml
```

再用 `view_image` 检查最终海报，并逐项执行 `references/quality_checklist.md`。自动校验或人工视觉检查任一失败，都不要声称已完成。

## 输出

成功时向用户展示最终海报，并返回：

- `poster.png` 的绝对路径
- `manifest.json` 的绝对路径
- 使用的型号和场景
- 是否启用了产品裁切回退

不要只返回提示词或场景草图。不要把中间场景图误称为最终海报。

## 失败处理

读取 `references/failure_recovery.md` 处理未知型号、资料缺失、图片不可用、图像工具不可用、产品漂移与文字溢出。失败时保留已完成的结构化中间文件，说明最小补救动作，不自动切换到外部模型 API。
