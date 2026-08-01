"""Compose the black editorial poster layout learned from user references."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .compose_poster import (
        ComposeResult,
        PosterCompositionError,
        _fit_font,
        _font,
        _hex_color,
    )
    from .config_io import load_config
except ImportError:
    from compose_poster import (
        ComposeResult,
        PosterCompositionError,
        _fit_font,
        _font,
        _hex_color,
    )
    from config_io import load_config


CANVAS_SIZE = (1080, 1350)
SCENE_RECT = (48, 690, 1032, 1298)
MIN_PRODUCT_WIDTH_RATIO = 0.18


def _crop_box(image: Image.Image, analysis: dict) -> tuple[int, int, int, int]:
    raw = analysis.get("scene_crop_normalized", [0, 0, 1, 1])
    if (
        not isinstance(raw, list)
        or len(raw) != 4
        or not all(isinstance(value, (int, float)) for value in raw)
    ):
        raise PosterCompositionError("scene_crop_normalized 必须包含 4 个数字")
    x1, y1, x2, y2 = (float(value) for value in raw)
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise PosterCompositionError("场景裁切坐标必须位于 0～1 范围内")
    return (
        round(x1 * image.width),
        round(y1 * image.height),
        round(x2 * image.width),
        round(y2 * image.height),
    )


def _cover_crop(image: Image.Image, crop: tuple[int, int, int, int]) -> Image.Image:
    target_width = SCENE_RECT[2] - SCENE_RECT[0]
    target_height = SCENE_RECT[3] - SCENE_RECT[1]
    source = image.convert("RGB").crop(crop)
    scale = max(target_width / source.width, target_height / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - target_width) // 2
    top = (resized.height - target_height) // 2
    return resized.crop((left, top, left + target_width, top + target_height))


def _paste_rounded(canvas: Image.Image, scene: Image.Image) -> None:
    mask = Image.new("L", scene.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, scene.width - 1, scene.height - 1), radius=28, fill=255)
    canvas.paste(scene, SCENE_RECT[:2], mask)


def _draw_status(draw: ImageDraw.ImageDraw, brand: dict, label: str) -> None:
    if not label:
        return
    blue = _hex_color(brand.get("colors", {}).get("status", "#159BFF"), "#159BFF")
    font = _font(brand, 26, True)
    text_box = draw.textbbox((0, 0), label, font=font)
    width = text_box[2] - text_box[0] + 52
    height = 54
    x1, y1 = 700, 718
    x2, y2 = x1 + width, y1 + height
    draw.rounded_rectangle((x1, y1, x2, y2), radius=27, fill=blue)
    draw.polygon([(x2 - 38, y2 - 1), (x2 - 18, y2 - 1), (x2 - 24, y2 + 14)], fill=blue)
    draw.text((x1 + 26, y1 + 9), label, font=font, fill=(255, 255, 255))


def compose_reference_poster(
    background_path: str | Path,
    content_path: str | Path,
    product_analysis_path: str | Path,
    brand_path: str | Path,
    output_path: str | Path,
) -> ComposeResult:
    background = Path(background_path)
    output = Path(output_path)
    if not background.is_file():
        raise PosterCompositionError(f"场景图不存在：{background}")

    content = load_config(content_path)
    analysis = load_config(product_analysis_path)
    brand = load_config(brand_path)
    product_width_ratio = analysis.get("scene_product_width_ratio")
    if (
        not isinstance(product_width_ratio, (int, float))
        or float(product_width_ratio) < MIN_PRODUCT_WIDTH_RATIO
    ):
        raise PosterCompositionError(
            f"产品主体宽度必须至少占场景窗口 {MIN_PRODUCT_WIDTH_RATIO:.0%}"
        )
    selling_points = content.get("selling_points", [])
    if not isinstance(selling_points, list) or len(selling_points) != 3:
        raise PosterCompositionError("参考版式当前固定使用 3 条卖点")

    canvas = Image.new("RGB", CANVAS_SIZE, (14, 14, 20))
    with Image.open(background) as source:
        scene = _cover_crop(source, _crop_box(source, analysis))
    _paste_rounded(canvas, scene)
    draw = ImageDraw.Draw(canvas)

    colors = brand.get("colors", {})
    text = _hex_color(colors.get("text", "#FFFFFF"), "#FFFFFF")
    accent = (19, 190, 201)
    muted = (177, 179, 187)
    left, right = 72, 1008

    brand_name = str(content.get("brand", "魔点门禁"))
    draw.text((left, 56), brand_name, font=_font(brand, 27, True), fill=text)
    draw.rectangle((left, 105, left + 46, 108), fill=accent)
    model = str(content.get("model", ""))
    model_font = _font(brand, 25, True)
    model_width = draw.textbbox((0, 0), model, font=model_font)[2]
    draw.text((right - model_width, 58), model, font=model_font, fill=muted)

    title = str(content.get("title", ""))
    title_font = _fit_font(draw, title, brand, right - left, 82, 62, True)
    draw.multiline_text((left, 144), title, font=title_font, fill=text, spacing=5)
    title_box = draw.multiline_textbbox((left, 144), title, font=title_font, spacing=5)
    subtitle = str(content.get("subtitle", ""))
    subtitle_font = _fit_font(draw, subtitle, brand, right - left, 29, 22)
    draw.text((left, title_box[3] + 22), subtitle, font=subtitle_font, fill=muted)

    column_width = 312
    feature_top = 470
    for index, point in enumerate(selling_points):
        x = left + index * column_width
        if index:
            divider_x = x - 24
            draw.line((divider_x, feature_top, divider_x, feature_top + 122), fill=(52, 53, 61), width=1)
        draw.text((x, feature_top), f"0{index + 1}", font=_font(brand, 48, True), fill=accent)
        point_font = _fit_font(draw, str(point), brand, column_width - 34, 27, 22, True)
        draw.text((x, feature_top + 70), str(point), font=point_font, fill=text)

    _draw_status(draw, brand, str(content.get("status_badge", "")).strip())

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    manifest_path = output.with_name("manifest.json")
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "brand": brand_name,
        "model": model,
        "scene": content.get("scene"),
        "selling_point_ids": content.get("selling_point_ids", []),
        "status_badge": content.get("status_badge"),
        "fallback_used": bool(analysis.get("fallback_used", False)),
        "assets": {"background": str(background.resolve()), "poster": str(output.resolve())},
        "layout": {
            "template": "reference-editorial-black-v1",
            "width": CANVAS_SIZE[0],
            "height": CANVAS_SIZE[1],
            "text_overflow": False,
            "status_badge_drawn": bool(content.get("status_badge")),
            "product_width_ratio": float(product_width_ratio),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ComposeResult(output.resolve(), manifest_path.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="合成参考图风格的黑底编辑式海报")
    parser.add_argument("--background", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compose_reference_poster(
        args.background, args.content, args.product, args.brand, args.output
    )
    print(json.dumps({"poster": str(result.poster_path), "manifest": str(result.manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
