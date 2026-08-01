"""Compose a deterministic 1080x1350 poster from a text-free scene image."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from .config_io import load_config
except ImportError:
    from config_io import load_config


@dataclass(frozen=True)
class ComposeResult:
    poster_path: Path
    manifest_path: Path


class PosterCompositionError(ValueError):
    """Raised when the supplied assets cannot fit the V1 poster contract."""


MIN_PRODUCT_WIDTH_RATIO = 0.18


def _hex_color(value: str, fallback: str) -> tuple[int, int, int]:
    candidate = (value or fallback).lstrip("#")
    if len(candidate) != 6:
        candidate = fallback.lstrip("#")
    try:
        return tuple(int(candidate[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return _hex_color(fallback, fallback)


def _font_paths(brand: dict[str, Any]) -> list[Path]:
    configured = [Path(item) for item in brand.get("font_candidates", [])]
    bundled = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    system = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyhbd.ttc",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    return configured + list(bundled.glob("*.ttf")) + list(bundled.glob("*.otf")) + system


def _font(brand: dict[str, Any], size: int, bold: bool = False) -> ImageFont.ImageFont:
    paths = _font_paths(brand)
    if bold:
        paths = sorted(paths, key=lambda path: "bold" not in path.name.casefold())
    for path in paths:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    source = image.convert("RGB")
    scale = max(size[0] / source.width, size[1] / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def _add_readability_overlay(canvas: Image.Image) -> None:
    width, height = canvas.size
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(height):
        top_alpha = max(0, round(185 * (1 - y / 540))) if y < 540 else 0
        bottom_alpha = max(0, round(220 * ((y - 830) / (height - 830)))) if y > 830 else 0
        alpha = max(top_alpha, bottom_alpha)
        for x in range(width):
            pixels[x, y] = (7, 18, 25, alpha)
    canvas.alpha_composite(overlay)


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    brand: dict[str, Any],
    max_width: int,
    start: int,
    minimum: int,
    bold: bool = False,
) -> ImageFont.ImageFont:
    for size in range(start, minimum - 1, -2):
        font = _font(brand, size, bold=bold)
        lines = text.splitlines() or [text]
        if all(draw.textbbox((0, 0), line, font=font)[2] <= max_width for line in lines):
            return font
    raise PosterCompositionError(f"文案无法放入版面，请缩短：{text}")


def _scene_product_box(
    analysis: dict[str, Any], size: tuple[int, int]
) -> tuple[tuple[int, int, int, int] | None, float | None]:
    raw_box = analysis.get("scene_product_bbox_normalized")
    if raw_box is None:
        return None, None
    if (
        not isinstance(raw_box, list)
        or len(raw_box) != 4
        or not all(isinstance(value, (int, float)) for value in raw_box)
    ):
        raise PosterCompositionError("scene_product_bbox_normalized 必须包含 4 个数字")
    x1, y1, x2, y2 = (float(value) for value in raw_box)
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise PosterCompositionError("产品主体坐标必须位于 0～1 范围内")
    width_ratio = x2 - x1
    if width_ratio < MIN_PRODUCT_WIDTH_RATIO:
        raise PosterCompositionError(
            f"产品主体宽度仅占画面 {width_ratio:.0%}，必须至少占 {MIN_PRODUCT_WIDTH_RATIO:.0%}"
        )
    return (
        (
            round(x1 * size[0]),
            round(y1 * size[1]),
            round(x2 * size[0]),
            round(y2 * size[1]),
        ),
        width_ratio,
    )


def _draw_status_badge(
    draw: ImageDraw.ImageDraw,
    label: str,
    product_box: tuple[int, int, int, int],
    brand: dict[str, Any],
    color: tuple[int, int, int],
    canvas_size: tuple[int, int],
) -> None:
    font = _font(brand, 28, True)
    text_box = draw.textbbox((0, 0), label, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    badge_width = text_width + 52
    badge_height = text_height + 28
    center_x = (product_box[0] + product_box[2]) // 2
    x1 = max(54, min(center_x - badge_width // 2, canvas_size[0] - badge_width - 54))
    y1 = max(430, product_box[1] - badge_height - 30)
    x2 = x1 + badge_width
    y2 = y1 + badge_height
    draw.rounded_rectangle((x1, y1, x2, y2), radius=badge_height // 2, fill=(*color, 245))
    pointer_x = max(x1 + 30, min(center_x, x2 - 30))
    draw.polygon(
        [(pointer_x - 10, y2 - 1), (pointer_x + 12, y2 - 1), (pointer_x + 6, y2 + 14)],
        fill=(*color, 245),
    )
    draw.text(
        (x1 + 26, y1 + (badge_height - text_height) // 2 - text_box[1]),
        label,
        font=font,
        fill=(255, 255, 255),
    )


def compose_poster(
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
    expected_brand = brand.get("brand_name", "魔点门禁")
    if content.get("brand") != expected_brand:
        raise PosterCompositionError("文案品牌与品牌配置不一致")

    canvas_config = brand.get("canvas", {})
    size = (int(canvas_config.get("width", 1080)), int(canvas_config.get("height", 1350)))
    if size != (1080, 1350):
        raise PosterCompositionError("V1 画布必须为 1080×1350")
    selling_points = content.get("selling_points", [])
    if not isinstance(selling_points, list) or not 3 <= len(selling_points) <= 4:
        raise PosterCompositionError("最终文案必须包含 3～4 条卖点")
    product_box, product_width_ratio = _scene_product_box(analysis, size)

    with Image.open(background) as source:
        canvas = _cover(source, size).convert("RGBA")
    _add_readability_overlay(canvas)
    draw = ImageDraw.Draw(canvas)
    colors = brand.get("colors", {})
    accent = _hex_color(colors.get("accent", "#58E6C0"), "#58E6C0")
    text_color = _hex_color(colors.get("text", "#FFFFFF"), "#FFFFFF")

    left = 72
    right = size[0] - 72
    draw.rounded_rectangle((left, 54, left + 184, 102), radius=24, fill=(*accent, 238))
    draw.text((left + 22, 63), expected_brand, font=_font(brand, 25, True), fill=(8, 28, 34))
    model = str(content.get("model", ""))
    model_font = _fit_font(draw, model, brand, 300, 28, 22, True)
    model_box = draw.textbbox((0, 0), model, font=model_font)
    model_width = model_box[2] - model_box[0]
    draw.text((right - model_width, 64), model, font=model_font, fill=text_color)

    title = str(content.get("title", ""))
    title_font = _fit_font(draw, title, brand, right - left, 76, 52, True)
    title_y = 145
    draw.multiline_text(
        (left, title_y), title, font=title_font, fill=text_color, spacing=8, stroke_width=1
    )
    title_box = draw.multiline_textbbox((left, title_y), title, font=title_font, spacing=8)
    subtitle_y = title_box[3] + 24
    subtitle = str(content.get("subtitle", ""))
    subtitle_font = _fit_font(draw, subtitle, brand, right - left, 30, 22)
    draw.text((left, subtitle_y), subtitle, font=subtitle_font, fill=(*text_color, 220))

    status_badge = str(content.get("status_badge", "")).strip()
    status_badge_drawn = bool(status_badge and product_box)
    if status_badge and product_box is None:
        raise PosterCompositionError("绘制状态标签前必须提供场景中的产品主体坐标")
    if status_badge_drawn:
        status_color = _hex_color(colors.get("status", "#159BFF"), "#159BFF")
        _draw_status_badge(draw, status_badge, product_box, brand, status_color, size)

    panel_top = 1012 if len(selling_points) == 3 else 968
    draw.rounded_rectangle(
        (44, panel_top, size[0] - 44, size[1] - 46),
        radius=28,
        fill=(5, 17, 24, 205),
        outline=(255, 255, 255, 42),
        width=1,
    )
    point_font = _font(brand, 28)
    y = panel_top + 35
    for index, point in enumerate(selling_points, start=1):
        point_text = str(point)
        point_font = _fit_font(draw, point_text, brand, 800, 28, 22)
        draw.ellipse((76, y + 8, 88, y + 20), fill=accent)
        draw.text((110, y), point_text, font=point_font, fill=text_color)
        y += 70

    text_overflow = y > size[1] - 54
    if text_overflow:
        raise PosterCompositionError("卖点区域发生文本溢出，请缩短卖点")

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    manifest_path = output.with_name("manifest.json")
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "brand": expected_brand,
        "model": model,
        "scene": content.get("scene", "企业办公入口"),
        "selling_point_ids": content.get("selling_point_ids", []),
        "fallback_used": bool(analysis.get("fallback_used", False)),
        "status_badge": status_badge or None,
        "product_analysis_confidence": analysis.get("confidence"),
        "assets": {
            "background": str(background.resolve()),
            "poster": str(output.resolve()),
        },
        "layout": {
            "width": size[0],
            "height": size[1],
            "text_overflow": False,
            "status_badge_drawn": status_badge_drawn,
            "product_width_ratio": product_width_ratio,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ComposeResult(output.resolve(), manifest_path.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="合成魔点门禁 4:5 场景海报")
    parser.add_argument("--background", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compose_poster(
        args.background, args.content, args.product, args.brand, args.output
    )
    print(json.dumps({"poster": str(result.poster_path), "manifest": str(result.manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
