"""Verify final raster and manifest invariants after composition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from .config_io import load_config
    from .load_product_info import ProductCatalogError, load_product
except ImportError:
    from config_io import load_config
    from load_product_info import ProductCatalogError, load_product


class OutputVerificationError(ValueError):
    """Raised when a generated deliverable is incomplete or malformed."""


def verify_output(
    poster_path: str | Path,
    manifest_path: str | Path,
    catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    poster = Path(poster_path)
    manifest_file = Path(manifest_path)
    if not poster.is_file():
        raise OutputVerificationError(f"海报不存在：{poster}")
    if poster.suffix.casefold() != ".png":
        raise OutputVerificationError("海报格式必须为 PNG")
    try:
        with Image.open(poster) as image:
            if image.size != (1080, 1350):
                raise OutputVerificationError(
                    f"海报尺寸必须为 1080×1350，当前为 {image.width}×{image.height}"
                )
            if image.mode != "RGB":
                raise OutputVerificationError("最终海报必须为 RGB/sRGB 兼容图像")
            image.verify()
    except OSError as exc:
        raise OutputVerificationError("海报文件不是有效图片") from exc

    manifest = load_config(manifest_file)
    required = ("brand", "model", "scene", "fallback_used", "selling_point_ids", "layout")
    missing = [field for field in required if field not in manifest]
    if missing:
        raise OutputVerificationError("生成清单缺少字段：" + "、".join(missing))
    if manifest.get("status") != "complete":
        raise OutputVerificationError("生成清单状态不是 complete")
    if manifest.get("brand") != "魔点门禁":
        raise OutputVerificationError("生成清单品牌名不正确")
    point_ids = manifest.get("selling_point_ids")
    if not isinstance(point_ids, list) or not 3 <= len(point_ids) <= 4:
        raise OutputVerificationError("生成清单必须记录 3～4 条卖点")
    if manifest.get("layout", {}).get("text_overflow") is not False:
        raise OutputVerificationError("生成清单报告文本溢出")
    if catalog_path is not None:
        try:
            product = load_product(catalog_path, str(manifest["model"]))
        except ProductCatalogError as exc:
            raise OutputVerificationError(f"无法用资料库验证输出：{exc}") from exc
        verified_ids = {
            point["id"]
            for point in product.get("selling_points", [])
            if isinstance(point, dict) and point.get("verified") is True
        }
        unverified = [point_id for point_id in point_ids if point_id not in verified_ids]
        if unverified:
            raise OutputVerificationError(
                "生成清单包含资料库外卖点：" + "、".join(map(str, unverified))
            )

    return {
        "valid": True,
        "poster": str(poster.resolve()),
        "manifest": str(manifest_file.resolve()),
        "model": manifest["model"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验魔点门禁海报输出")
    parser.add_argument("--poster", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--catalog", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            verify_output(args.poster, args.manifest, args.catalog),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
