# 将优秀 P4 制成可复用模板

仅在用户明确认可本轮 P4 并要求以后复用时执行。目标不是保存一张成品图，而是提炼一个可用于其他型号、其他文案长度和相近场景的版式配方。

## 晋升步骤

1. 记录证据：运行 ID、`selection_key: P4`、样例路径和 `user_approved: true`。
2. 拆解成功因素：构图轴、标题层级、产品位置与宽度区间、人物关系、留白、安全边距、状态标签位置、色彩角色。
3. 去产品化：删除具体型号、标题、卖点、人名、时间和屏幕文字，只保留槽位、长度约束和排版关系。
4. 写入候选 JSON：必须含 `id`、`label`、`best_for`、`product_width_target`、`scene_asset`、`renderer`、`layout_recipe` 与 `promotion_evidence`。
5. 用短标题和长标题各验证一次；检查 1080×1350、缩略图可读、产品占比、中文溢出和事实字段。
6. 与现有模板比较。若差异只有颜色、背景或微小位移，不晋升。
7. 运行：

```text
python <SKILL_ROOT>/scripts/promote_layout_template.py \
  --catalog <SKILL_ROOT>/data/layout_templates.yaml \
  --candidate <运行目录>/p4/template_candidate.json \
  --output <运行目录>/layout_templates.promoted.yaml
```

8. 校验输出后，再用审核后的文件替换正式注册表，运行测试、更新样例和重新打包 Skill。不要让脚本在未经复核时直接覆盖正式库。

## `layout_recipe` 必填字段

- `composition`：构图分区与视觉动线。
- `text_hierarchy`：品牌、型号、标题、副标题、卖点的顺序与长度规则。
- `product_placement`：产品锚点、宽度区间、裁切和不可遮挡区域。
- `prompt_guidance`：生成该版式所需无字主视觉的可复用提示规则。

不得把具体产品功能写死在配方中；所有功能仍由 `products.yaml` 和本轮验证文案注入。

## 不得晋升

- 用户没有明确授权。
- 产品漂移、结构畸变或缩略图不可识别。
- 中文溢出、错字、伪 Logo 或生成水印。
- 只对已有模板换色或挪动几个像素。
- 只能适配当前一句文案，无法抽象成槽位和约束。
