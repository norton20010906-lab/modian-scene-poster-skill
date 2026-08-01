"""Compose internal poster candidates and a deterministic P1-P4 contact sheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw

try:
    from .compose_poster import PosterCompositionError, _fit_font, _font, _hex_color
    from .compose_reference_poster import (
        CANVAS_SIZE,
        SCENE_RECT,
        _cover_crop,
        _crop_box,
        _paste_rounded,
    )
    from .config_io import load_config
except ImportError:
    from compose_poster import PosterCompositionError, _fit_font, _font, _hex_color
    from compose_reference_poster import (
        CANVAS_SIZE,
        SCENE_RECT,
        _cover_crop,
        _crop_box,
        _paste_rounded,
    )
    from config_io import load_config


def load_template_library(path: str | Path) -> dict[str, Any]:
    library = load_config(path)
    templates = library.get("templates")
    strategy = library.get("candidate_strategy")
    if library.get("internal_only") is not True:
        raise ValueError("版式库必须标记为 internal_only")
    if not isinstance(templates, list) or not isinstance(strategy, dict):
        raise ValueError("版式库缺少 templates 或 candidate_strategy")
    if (
        strategy.get("library_slots") != ["P1", "P2", "P3"]
        or strategy.get("exploration_slot") != "P4"
        or strategy.get("library_pick_count") != 3
        or strategy.get("exploration_count") != 1
        or not strategy.get("user_guidance")
    ):
        raise ValueError("候选四宫格必须遵循三个模板位加一个探索位")
    for template in templates:
        if not isinstance(template, dict):
            raise ValueError("模板元数据必须为对象")
        target = template.get("product_width_target")
        if (
            not template.get("id")
            or not template.get("label")
            or not template.get("source")
            or not template.get("best_for")
            or not template.get("scene_asset")
            or template.get("status") != "approved"
            or not template.get("origin")
            or not template.get("renderer")
            or not isinstance(target, list)
            or len(target) != 2
            or not all(isinstance(value, (int, float)) for value in target)
            or not 0 < float(target[0]) < float(target[1]) <= 1
        ):
            raise ValueError("模板元数据缺少标签、来源、适用条件、主视觉或有效产品占比")
    ids = [template.get("id") for template in templates if isinstance(template, dict)]
    if len(ids) < 3 or len(ids) != len(set(ids)):
        raise ValueError("版式库必须包含至少三个 ID 唯一的成熟模板")
    return library


def _fit_full(image: Image.Image) -> Image.Image:
    source = image.convert("RGB")
    scale = max(CANVAS_SIZE[0] / source.width, CANVAS_SIZE[1] / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - CANVAS_SIZE[0]) // 2
    top = (resized.height - CANVAS_SIZE[1]) // 2
    return resized.crop((left, top, left + CANVAS_SIZE[0], top + CANVAS_SIZE[1]))


def _draw_brand_row(draw: ImageDraw.ImageDraw, brand: dict, content: dict, *, centered: bool = False) -> None:
    white = (250, 250, 252)
    muted = (171, 174, 183)
    brand_name = str(content.get("brand", "魔点门禁"))
    model = str(content.get("model", ""))
    if centered:
        label = f"{brand_name}  ·  {model}"
        font = _font(brand, 24, True)
        width = draw.textbbox((0, 0), label, font=font)[2]
        draw.text(((1080 - width) // 2, 58), label, font=font, fill=muted)
        return
    draw.text((70, 56), brand_name, font=_font(brand, 26, True), fill=white)
    model_font = _font(brand, 24, True)
    model_width = draw.textbbox((0, 0), model, font=model_font)[2]
    draw.text((1010 - model_width, 58), model, font=model_font, fill=muted)


def _draw_status(draw: ImageDraw.ImageDraw, brand: dict, label: str, position: tuple[int, int]) -> None:
    if not label:
        return
    color = _hex_color(brand.get("colors", {}).get("status", "#159BFF"), "#159BFF")
    font = _font(brand, 25, True)
    width = draw.textbbox((0, 0), label, font=font)[2] + 48
    x, y = position
    draw.rounded_rectangle((x, y, x + width, y + 54), radius=27, fill=color)
    draw.polygon([(x + width - 34, y + 53), (x + width - 15, y + 53), (x + width - 21, y + 67)], fill=color)
    draw.text((x + 24, y + 9), label, font=font, fill=(255, 255, 255))


def _save(canvas: Image.Image, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output.resolve()


def compose_centered_story(
    background_path: str | Path,
    content_path: str | Path,
    analysis_path: str | Path,
    brand_path: str | Path,
    output_path: str | Path,
) -> Path:
    content, analysis, brand = load_config(content_path), load_config(analysis_path), load_config(brand_path)
    points = content.get("selling_points", [])
    if len(points) != 3:
        raise PosterCompositionError("居中叙事模板固定使用 3 条卖点")
    canvas = Image.new("RGB", CANVAS_SIZE, (0, 0, 0))
    with Image.open(background_path) as source:
        scene = _cover_crop(source, _crop_box(source, analysis))
    _paste_rounded(canvas, scene)
    draw = ImageDraw.Draw(canvas)
    _draw_brand_row(draw, brand, content, centered=True)
    title = str(content.get("title", ""))
    title_font = _fit_font(draw, title, brand, 920, 78, 58, True)
    title_width = draw.textbbox((0, 0), title, font=title_font)[2]
    draw.text(((1080 - title_width) // 2, 126), title, font=title_font, fill=(255, 255, 255))
    second_title = str(points[1])
    second_font = _fit_font(draw, second_title, brand, 920, 66, 48, True)
    second_width = draw.textbbox((0, 0), second_title, font=second_font)[2]
    draw.text(((1080 - second_width) // 2, 226), second_title, font=second_font, fill=(255, 255, 255))
    subtitle = str(content.get("subtitle", ""))
    sub_font = _fit_font(draw, subtitle, brand, 900, 30, 22)
    sub_width = draw.textbbox((0, 0), subtitle, font=sub_font)[2]
    draw.text(((1080 - sub_width) // 2, 350), subtitle, font=sub_font, fill=(196, 197, 202))
    point_line = f"{points[0]}   ·   {points[2]}"
    point_font = _fit_font(draw, point_line, brand, 930, 25, 19)
    point_width = draw.textbbox((0, 0), point_line, font=point_font)[2]
    draw.text(((1080 - point_width) // 2, 480), point_line, font=point_font, fill=(245, 245, 247))
    _draw_status(draw, brand, str(content.get("status_badge", "")), (700, 718))
    return _save(canvas, output_path)


def compose_closeup_overlay(
    background_path: str | Path,
    content_path: str | Path,
    brand_path: str | Path,
    output_path: str | Path,
) -> Path:
    content, brand = load_config(content_path), load_config(brand_path)
    with Image.open(background_path) as source:
        canvas = _fit_full(source).convert("RGBA")
    overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, 1080, 250), fill=(8, 9, 14, 198))
    overlay_draw.rectangle((0, 1050, 1080, 1350), fill=(8, 9, 14, 220))
    canvas.alpha_composite(overlay)
    draw = ImageDraw.Draw(canvas)
    _draw_brand_row(draw, brand, content)
    title = str(content.get("title", ""))
    title_font = _fit_font(draw, title, brand, 850, 58, 44, True)
    draw.text((70, 132), title, font=title_font, fill=(255, 255, 255))
    points = content.get("selling_points", [])
    x_positions = (70, 382, 694)
    for index, point in enumerate(points):
        x = x_positions[index]
        draw.text((x, 1130), f"0{index + 1}", font=_font(brand, 34, True), fill=(19, 190, 201))
        font = _fit_font(draw, str(point), brand, 280, 24, 19, True)
        draw.text((x, 1185), str(point), font=font, fill=(250, 250, 252))
    _draw_status(draw, brand, str(content.get("status_badge", "")), (690, 510))
    return _save(canvas, output_path)


def compose_asymmetric_campaign(
    background_path: str | Path,
    content_path: str | Path,
    brand_path: str | Path,
    output_path: str | Path,
) -> Path:
    content, brand = load_config(content_path), load_config(brand_path)
    with Image.open(background_path) as source:
        canvas = _fit_full(source).convert("RGBA")
    overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    pixels = overlay.load()
    for x in range(760):
        alpha = round(225 * (1 - x / 760))
        for y in range(1350):
            pixels[x, y] = (2, 5, 10, alpha)
    canvas.alpha_composite(overlay)
    draw = ImageDraw.Draw(canvas)
    _draw_brand_row(draw, brand, content)
    title = str(content.get("title", ""))
    split = max(2, len(title) // 2)
    title_lines = f"{title[:split]}\n{title[split:]}"
    title_font = _fit_font(draw, title_lines, brand, 470, 88, 62, True)
    draw.multiline_text((70, 170), title_lines, font=title_font, fill=(255, 255, 255), spacing=3)
    draw.rectangle((70, 380, 128, 384), fill=(17, 157, 255))
    subtitle = str(content.get("subtitle", ""))
    sub_font = _fit_font(draw, subtitle, brand, 440, 27, 20)
    draw.multiline_text((70, 418), subtitle, font=sub_font, fill=(190, 197, 208), spacing=8)
    for index, point in enumerate(content.get("selling_points", [])):
        y = 1025 + index * 78
        draw.text((72, y), f"0{index + 1}", font=_font(brand, 24, True), fill=(21, 155, 255))
        draw.text((132, y), str(point), font=_font(brand, 24, True), fill=(250, 250, 252))
    _draw_status(draw, brand, str(content.get("status_badge", "")), (665, 735))
    return _save(canvas, output_path)


def build_contact_sheet(
    posters: Sequence[str | Path],
    output_path: str | Path,
    *,
    template_ids: Sequence[str] | None = None,
) -> Path:
    if len(posters) != 4:
        raise ValueError("四宫格必须且只能包含 4 张海报")
    sheet = Image.new("RGB", (2160, 2700), (6, 7, 10))
    label_font = None
    for index, poster_path in enumerate(posters):
        with Image.open(poster_path) as source:
            poster = source.convert("RGB")
            if poster.size != CANVAS_SIZE:
                raise ValueError(f"候选 P{index + 1} 尺寸必须为 1080×1350")
            x = (index % 2) * 1080
            y = (index // 2) * 1350
            poster = poster.resize((1056, 1320), Image.Resampling.LANCZOS)
            sheet.paste(poster, (x + 12, y + 30))
        label_draw = ImageDraw.Draw(sheet)
        label_font = label_font or _font({}, 20, True)
        label_draw.text((x + 14, y + 1), f"P{index + 1}", font=label_font, fill=(255, 255, 255))
    output = _save(sheet, output_path)
    template_order = list(template_ids or (
        "editorial-feature-grid",
        "centered-story-window",
        "product-closeup-overlay",
        "experimental:new-layout",
    ))
    if len(template_order) != 4 or len(set(template_order)) != 4:
        raise ValueError("四宫格必须记录 4 个不同的模板 ID")
    if any(template_id.startswith("experimental:") for template_id in template_order[:3]):
        raise ValueError("P1～P3 必须来自成熟模板库，不能标记为 experimental")
    if not template_order[3].startswith("experimental:"):
        raise ValueError("P4 必须使用 experimental:<id> 标记为本轮探索稿")
    manifest = {
        "schema_version": 2,
        "selection_status": "awaiting_user_selection",
        "contact_sheet": str(output),
        "user_guidance": "左上为 1、右上为 2、左下为 3、右下为 4；1、2、3 来自模板库，4 是本次新探索稿。回复编号选择；若 4 满意，可明确要求加入模板库。",
        "candidates": [
            {
                "selection_key": f"P{index + 1}",
                "template_id": template_order[index],
                "source_type": "library" if index < 3 else "exploration",
                "poster": str(Path(poster).resolve()),
            }
            for index, poster in enumerate(posters)
        ],
    }
    output.with_name("candidate_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="合成内部模板候选或四宫格联系表")
    subparsers = parser.add_subparsers(dest="action", required=True)

    for action in ("p2", "p3", "p4"):
        child = subparsers.add_parser(action)
        child.add_argument("--background", required=True)
        child.add_argument("--content", required=True)
        child.add_argument("--brand", required=True)
        child.add_argument("--output", required=True)
        if action == "p2":
            child.add_argument("--analysis", required=True)

    contact = subparsers.add_parser("contact")
    contact.add_argument("--poster", action="append", required=True)
    contact.add_argument("--template-id", action="append")
    contact.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.action == "p2":
        result = compose_centered_story(
            args.background, args.content, args.analysis, args.brand, args.output
        )
    elif args.action == "p3":
        result = compose_closeup_overlay(
            args.background, args.content, args.brand, args.output
        )
    elif args.action == "p4":
        result = compose_asymmetric_campaign(
            args.background, args.content, args.brand, args.output
        )
    else:
        result = build_contact_sheet(
            args.poster, args.output, template_ids=args.template_id
        )
    print(json.dumps({"output": str(result)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
