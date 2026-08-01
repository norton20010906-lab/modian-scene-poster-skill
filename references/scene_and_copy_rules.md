# 场景与文案规则

## 场景选择

- 只能从当前产品的 `recommended_scenes` 选择。
- 默认使用列表第一项。
- 补充需求可以限定时间、氛围、人物数量或场景候选，但不能覆盖品牌和产品事实。
- 人物只是说明使用关系，不应遮挡设备，也不应出现异常人脸或夸张动作。

`scene_plan.json` 至少包含：`scene`、`user_moment`、`composition`、`lighting`、`negative_space`、`identity_anchors` 和 `avoid`。

## 文案契约

`copy.json` 使用：

```json
{
  "brand": "魔点门禁",
  "model": "资料库中的标准型号",
  "title": "不超过 24 字",
  "subtitle": "不超过 40 字",
  "scene": "recommended_scenes 中的值",
  "status_badge": "可选：识别成功、打卡成功或欢迎通行",
  "selling_point_ids": ["三个或四个已验证卖点 ID"]
}
```

- 标题强调通行体验或场景价值，不写未经证实的性能数字。
- 副标题说明产品在所选场景中的角色。
- 卖点正文由校验脚本从资料库注入，Agent 不自行改写。
- 避免“顶级、第一、绝对、安全无误”等不可证明的绝对化语言。
- 不要把补充需求原样塞入海报。
- `status_badge` 只表达当下交互结果，不属于功能卖点；没有清晰刷脸动作时应省略。
