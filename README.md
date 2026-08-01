# 魔点门禁产品场景海报 Skill

[![validate-skill](https://github.com/OWNER/modian-scene-poster-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/modian-scene-poster-skill/actions/workflows/ci.yml)

把产品图片和型号交给 WorkBuddy、Codex 等具备视觉理解、图片生成和本地脚本能力的 Agent，生成四张 1080×1350 中文门禁使用场景海报候选：前三张来自成熟模板库，第四张探索一种新排版。

V1 只支持品牌“魔点门禁”和型号 `D5 Ultra`，不对未知型号做模糊匹配，不根据产品外观猜测功能。

![D5 Ultra 四候选](assets/sample_output/d5-ultra-four-candidate-sheet.png)

## 从 GitHub 安装到 WorkBuddy

把仓库地址发送给 WorkBuddy：

```text
请安装并启用这个 Skill：
https://github.com/OWNER/modian-scene-poster-skill
```

如果当前版本无法直接从地址安装，手动克隆到用户 Skill 目录：

```bash
git clone https://github.com/OWNER/modian-scene-poster-skill.git ~/.workbuddy/skills/modian-scene-poster
```

重载 WorkBuddy Skills 后，在对话中上传产品图片并输入：

```text
使用 modian-scene-poster Skill，根据我上传的产品图，
为 D5 Ultra 生成企业入口使用场景海报。
```

也可以使用 `/modian-scene-poster` 主动调用。WorkBuddy 需要选择支持图片理解的模型，并启用内置图片生成工具。

## 首次运行

Skill 会先检查 Python、Pillow、中文字体、工作空间写权限、D5 Ultra 资料库、模板库以及宿主视觉能力：

```bash
python scripts/preflight.py \
  --workspace . \
  --catalog data/products.yaml \
  --templates data/layout_templates.yaml \
  --model "D5 Ultra" \
  --host-capability vision \
  --host-capability image-generation
```

如果缺少 Pillow，WorkBuddy 会先征得许可，再安装唯一的 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

不需要外部模型 API Key。图片生成消耗由使用者自己的 Agent/WorkBuddy 账号承担。

## 输入与输出

输入：

- 一张产品图或商品截图
- 产品型号 `D5 Ultra`
- 可选的一句话补充需求，最多 200 字

每次运行写入当前工作空间的 `output/<run-id>/`：

```text
analysis.json
research.json
scene_plan.json
copy.validated.json
scenes/
p1/poster.png
p2/poster.png
p3/poster.png
p4/poster.png
contact-sheet.png
candidate_manifest.json
```

位置固定为：左上 1、右上 2、左下 3、右下 4。1～3 是模板库方案，4 是当次探索稿。回复编号即可查看单张成品。

## 稳定性约束

- 产品能力只来自 `data/products.yaml` 中有来源 ID 的已验证资料。
- 商品截图只用于识别产品主体，不把价格、店铺和页面 UI 带入海报。
- 图片生成只负责无字场景；中文标题、型号、卖点和状态由 Pillow 排版。
- 产品宽度低于画面 18% 时拒绝成品。
- 产品结构明显漂移时只重试一次，之后使用原产品图合成回退。
- 输出不会写入 Skill 安装目录，也不会静默修改共享模板库。

## 模板库协作

P4 被明确认可后，Skill 在用户工作空间生成去产品化的 `template_candidate.json`。共享新模板通过 GitHub 的“新模板提案”Issue 或 Pull Request 提交，审核通过后才进入未来 P1～P3 的轮换池。

模板提案必须包含：

- 适用场景与产品展示目标
- 构图、文字层级、产品位置和占比
- 无字主视觉提示规则
- 用户认可证据和样例
- 短、长文案的排版验证结果

## 本地验证

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/audit_repository.py --root . --allowed-model "D5 Ultra"
```

CI 会在 Windows 和 macOS、Python 3.10 与 3.12 上重复这些检查。

## 常见问题

**图片无法识别**：切换到支持视觉理解的模型，并使用更清晰的单独产品图。

**无法生成场景图**：确认 WorkBuddy 图片生成工具已启用；不可用时 Skill 会停止，不会把草图冒充正式海报。

**中文显示异常**：安装微软雅黑、Noto Sans CJK 或苹方后重试。

**提示未知型号**：V1 仅发布 D5 Ultra，其他型号不会临场补写资料。

**安装后找不到 Skill**：确认目录为 `~/.workbuddy/skills/modian-scene-poster/SKILL.md`，然后重载 Skills。

## 数据与授权

- 产品功能资料来自仓库中逐条登记的来源；用户图片是外观证据，不自动成为功能证据。
- 用户上传的运行时产品图保存在其当前 WorkBuddy 工作空间，是否由宿主上传处理取决于用户的 WorkBuddy 配置。
- 仓库代码、模板规则和示例素材使用 [MIT License](LICENSE)。
