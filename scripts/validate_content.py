"""Enforce that poster copy contains only catalog-backed product claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .config_io import load_config
    from .load_product_info import load_product
except ImportError:
    from config_io import load_config
    from load_product_info import load_product


BRAND_NAME = "魔点门禁"
TITLE_MAX = 24
SUBTITLE_MAX = 40


class ContentValidationError(ValueError):
    """Raised when generated copy violates the factual or layout contract."""


def validate_content(
    content: dict[str, Any], product: dict[str, Any]
) -> dict[str, Any]:
    if content.get("brand") != BRAND_NAME:
        raise ContentValidationError(f"品牌名必须严格为“{BRAND_NAME}”")
    if content.get("model") != product.get("model"):
        raise ContentValidationError("文案中的型号与资料库型号不一致")

    title = " ".join(str(content.get("title", "")).split())
    subtitle = " ".join(str(content.get("subtitle", "")).split())
    if not title or len(title) > TITLE_MAX:
        raise ContentValidationError(f"标题必须为 1～{TITLE_MAX} 个字符")
    if not subtitle or len(subtitle) > SUBTITLE_MAX:
        raise ContentValidationError(f"副标题必须为 1～{SUBTITLE_MAX} 个字符")

    ids = content.get("selling_point_ids")
    if not isinstance(ids, list) or not 3 <= len(ids) <= 4:
        raise ContentValidationError("卖点必须为 3～4 条")
    if len(set(ids)) != len(ids):
        raise ContentValidationError("卖点不能重复")

    verified = {
        item["id"]: item["text"]
        for item in product.get("selling_points", [])
        if isinstance(item, dict) and item.get("verified") is True
    }
    unknown = [item_id for item_id in ids if item_id not in verified]
    if unknown:
        raise ContentValidationError(
            "包含未经验证的卖点：" + "、".join(map(str, unknown))
        )

    full_copy = " ".join(
        [title, subtitle, *[verified[item_id] for item_id in ids]]
    )
    prohibited = [
        claim
        for claim in product.get("prohibited_claims", [])
        if claim and claim in full_copy
    ]
    if prohibited:
        raise ContentValidationError(
            "文案包含禁用表述：" + "、".join(prohibited)
        )

    return {
        "brand": BRAND_NAME,
        "model": product["model"],
        "title": title,
        "subtitle": subtitle,
        "selling_point_ids": ids,
        "selling_points": [verified[item_id] for item_id in ids],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验海报文案的事实与长度")
    parser.add_argument("--content", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    content = load_config(args.content)
    product = load_product(args.catalog, args.model)
    result = validate_content(content, product)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
