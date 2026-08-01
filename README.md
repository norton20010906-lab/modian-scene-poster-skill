# 魔点门禁产品场景海报生成 Skill

一个在 Codex 等支持视觉理解和内置图像生成的 Agent 环境中运行的 V1 Skill。它把产品图片、产品型号和可选补充需求转换成四张 1080×1350 中文使用场景海报候选和一张四宫格联系表；用户选择 P1～P4 后再交付单张成品。

## 当前状态

工作流、证据收集、事实约束、海报合成、输出校验和测试已实现。首发型号已录入为 D5 Ultra；当前可宣传的能力由魔点官网产品目录与用户提供图片共同支持，并逐条绑定来源 ID。

V1 不包含独立 Web Demo、外部模型 API、多品牌、多型号模糊匹配或视频生成。允许最多 3 次官方优先的只读定向搜索，用于刷新证据；生成时仍只读取本地已核验资料库。

## 快速开始

1. 安装 Python 3.10+ 和 Pillow：

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. 按 `references/product_research_workflow.md` 维护 `data/products.yaml`。每条卖点需要稳定 ID、准确正文、`verified: true` 和可解析的 `source_ids`。

3. 把产品图片附加到 Agent 对话或提供本地绝对路径，然后说：

   ```text
   请用魔点门禁海报 Skill，根据这张产品图为型号 <真实型号> 生成一张企业办公入口使用场景海报。补充要求：画面现代、克制。
   ```

4. Agent 将在 `output/<run-id>/` 中保留：

   ```text
   analysis.json
   research.json
   scene_plan.json
   copy.json
   copy.validated.json
   scene.png
   poster.png
   manifest.json
   ```

## 设计原则

- 产品功能只来自内置资料库，视觉分析不推断规格。
- 新输入先经过图片事实提取、官方优先检索和声明级核验，再进入文案与生图。
- 每条卖点必须引用已验证来源；搜索摘要、相邻型号和用户场景偏好不能成为功能证据。
- 场景图不生成中文，文字由 Pillow 确定性排版。
- 型号只能精确匹配或命中显式别名。
- 产品一致性编辑最多重试一次，随后采用可审计回退。
- 图像生成使用宿主内置能力，不需要 `OPENAI_API_KEY`。
- 产品建议占画面宽度 20%～30%，小于 18% 会被排版流程拒绝。
- 刷脸动作由人物朝向和屏幕取景关系表达；中文识别状态由本地脚本稳定叠加。
- 版式来自内部积累库，用户不在生成前选择模板；Skill 根据内容生成四个结果候选。
- 四宫格只用于比较，用户选择 P1～P4 后展示对应的全尺寸海报。

## 已验证样例

- 输入：[D5 Ultra 商品主图](assets/sample_input/d5-ultra-product.webp)
- 输出：[D5 Ultra 企业入口海报 V2](assets/sample_output/d5-ultra-enterprise-entry-poster-v2.png)
- 四候选：[D5 Ultra P1～P4 四宫格](assets/sample_output/d5-ultra-four-candidate-sheet.png)

该样例只宣传官网产品目录与用户图片直接支持的内容；经销商和媒体页面仅作发现线索，未用于支撑参数型声明。

## 本地验证

```powershell
python -m unittest discover -s tests -v
python -m compileall scripts tests
```

只有在补齐真实型号和产品图之后，才运行 `evals/evals.json` 中需要视觉生成的用例。未知型号、资料缺失和排版逻辑可以立即测试。

## 产品资料维护

V1 只允许一个启用型号。更新资料时：

1. 保留原始型号拼写，只把真实可接受的写法加入 `aliases`。
2. 每条卖点必须通过 `source_ids` 对应到已验证资料。
3. 把夸大或未经确认的词句写入 `prohibited_claims`。
4. 在人工复核完成前保持 `enabled: false`。
5. 启用后运行完整测试和一个真实端到端样例。

## 目录说明

- `SKILL.md`：Agent 执行入口。
- `data/`：品牌和单型号可信资料。
- `data/layout_templates.yaml`：内部版式积累库与默认四候选注册表。
- `references/`：按需加载的分析、场景、提示词和恢复规则。
- `scripts/`：确定性验证与排版程序。
- `evals/`：Skill 行为评测提示。
- `assets/`：字体说明、布局配置和待补充的真实示例。
