# 魔点门禁产品场景海报生成 Skill

一个在 Codex 等支持视觉理解和内置图像生成的 Agent 环境中运行的 V1 Skill。它把产品图片、产品型号和可选补充需求转换成一张 1080×1350 中文使用场景海报。

## 当前状态

工作流、事实约束、海报合成、输出校验和测试已实现。为避免编造产品能力，`data/products.yaml` 中的首发型号目前处于禁用占位状态；填入用户提供的官方资料并启用后，才能生成正式海报。

V1 不包含独立 Web Demo、外部 API、联网搜索、多品牌、多型号模糊匹配或视频生成。

## 快速开始

1. 安装 Python 3.10+ 和 Pillow：

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. 用真实型号资料替换 `data/products.yaml` 中的占位记录。每条卖点需要稳定 ID、准确正文和 `verified: true`，并至少提供一个 `status: verified` 的来源。

3. 把产品图片附加到 Agent 对话或提供本地绝对路径，然后说：

   ```text
   请用魔点门禁海报 Skill，根据这张产品图为型号 <真实型号> 生成一张企业办公入口使用场景海报。补充要求：画面现代、克制。
   ```

4. Agent 将在 `output/<run-id>/` 中保留：

   ```text
   analysis.json
   scene_plan.json
   copy.json
   copy.validated.json
   scene.png
   poster.png
   manifest.json
   ```

## 设计原则

- 产品功能只来自内置资料库，视觉分析不推断规格。
- 场景图不生成中文，文字由 Pillow 确定性排版。
- 型号只能精确匹配或命中显式别名。
- 产品一致性编辑最多重试一次，随后采用可审计回退。
- 图像生成使用宿主内置能力，不需要 `OPENAI_API_KEY`。

## 本地验证

```powershell
python -m unittest discover -s tests -v
python -m compileall scripts tests
```

只有在补齐真实型号和产品图之后，才运行 `evals/evals.json` 中需要视觉生成的用例。未知型号、资料缺失和排版逻辑可以立即测试。

## 产品资料维护

V1 只允许一个启用型号。更新资料时：

1. 保留原始型号拼写，只把真实可接受的写法加入 `aliases`。
2. 每条卖点必须能对应到已提供资料。
3. 把夸大或未经确认的词句写入 `prohibited_claims`。
4. 在人工复核完成前保持 `enabled: false`。
5. 启用后运行完整测试和一个真实端到端样例。

## 目录说明

- `SKILL.md`：Agent 执行入口。
- `data/`：品牌和单型号可信资料。
- `references/`：按需加载的分析、场景、提示词和恢复规则。
- `scripts/`：确定性验证与排版程序。
- `evals/`：Skill 行为评测提示。
- `assets/`：字体说明、布局配置和待补充的真实示例。
