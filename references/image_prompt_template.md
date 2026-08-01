# 场景主视觉提示模板

使用宿主内置图像生成工具，分类为 `ads-marketing`。产品图片是产品参考或编辑目标，不是风格参考。

```text
Use case: ads-marketing
Asset type: 4:5 portrait access-control product poster background, text-free
Primary request: 将参考图中的刷脸门禁设备自然安装在真实的企业入口场景中，呈现员工从容刷脸通行的瞬间
Input images: Image 1 is the product identity reference/edit target
Scene/backdrop: <scene_plan.scene 与空间细节>
Subject: 魔点门禁刷脸门禁机；保留 <analysis.identity_anchors>
Style/medium: premium realistic architectural advertising photography
Composition/framing: portrait; product clearly visible around the middle-right; quiet negative space at top and lower area for later typography
Lighting/mood: clean daylight, restrained technology atmosphere, believable reflections and wall contact
Color palette: neutral architectural gray, deep charcoal, subtle cool green accent
Constraints: preserve product silhouette, screen ratio, camera position, primary colors, mounting orientation; realistic scale and perspective
Avoid: all text, letters, numbers, logos, watermarks, UI labels, feature icons, floating device, distorted hands, extra access-control devices, ecommerce page elements
```

若第一次结果只在一个外观锚点上漂移，第二次使用精确编辑指令：“只修正 `<漂移项>`；保持场景、人物、构图、照明及其他产品结构不变。”
