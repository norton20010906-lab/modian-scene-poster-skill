# 产品视觉分析结构

查看产品图后，将结果保存为以下结构。所有字段只描述可见事实。

```json
{
  "schema_version": 1,
  "input_image": "绝对路径",
  "image_type": "isolated_product | ecommerce_screenshot",
  "subject_bbox_normalized": [0.1, 0.1, 0.9, 0.9],
  "appearance": {
    "body_shape": "可见轮廓",
    "primary_colors": ["颜色"],
    "screen": "屏幕位置与比例",
    "camera": "摄像头可见位置",
    "frame": "边框与材质",
    "mounting_orientation": "竖直或其他可见朝向"
  },
  "identity_anchors": [
    "生成图必须保留的 3～5 个外观锚点"
  ],
  "background_interference": ["价格、店铺 UI 或其他干扰"],
  "occlusion": "none | partial | severe",
  "usable": true,
  "confidence": 0.0,
  "uncertainties": [],
  "fallback_used": false
}
```

当主体边界不清、遮挡严重、正面结构不可见或置信度低于 0.65 时，把 `usable` 设为 `false` 并请求更清晰图片。

不得出现的推断包括识别速度、容量、联网协议、考勤能力、防水等级、适用温度或准确率，除非只是说明这些内容无法从图片判断。
