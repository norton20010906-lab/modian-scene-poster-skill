"""Load one verified product by exact model or explicit alias."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .config_io import ConfigError, load_config
except ImportError:  # Allows direct `python scripts/...py` execution.
    from config_io import ConfigError, load_config


class ProductCatalogError(ValueError):
    """Raised when the requested model is not safely usable."""


def _match_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _validate_product(product: dict[str, Any]) -> None:
    required = (
        "model",
        "category",
        "verified_features",
        "selling_points",
        "recommended_scenes",
        "prohibited_claims",
        "sources",
    )
    missing = [name for name in required if not product.get(name)]
    if missing:
        raise ProductCatalogError(
            "型号资料不完整，缺少：" + "、".join(missing)
        )

    verified_points = [
        item
        for item in product["selling_points"]
        if isinstance(item, dict)
        and item.get("id")
        and item.get("text")
        and item.get("verified") is True
    ]
    if len(verified_points) < 3:
        raise ProductCatalogError("型号至少需要 3 条已验证卖点")
    if not any(
        isinstance(source, dict) and source.get("status") == "verified"
        for source in product["sources"]
    ):
        raise ProductCatalogError("型号缺少已验证的资料来源")


def load_product(catalog_path: str | Path, requested_model: str) -> dict[str, Any]:
    try:
        catalog = load_config(catalog_path)
    except ConfigError as exc:
        raise ProductCatalogError(str(exc)) from exc

    requested_key = _match_key(requested_model)
    if not requested_key:
        raise ProductCatalogError("产品型号不能为空")

    for product in catalog.get("products", []):
        if not isinstance(product, dict):
            continue
        names = [product.get("model", ""), *product.get("aliases", [])]
        if requested_key not in {_match_key(str(name)) for name in names}:
            continue
        if product.get("enabled") is not True:
            raise ProductCatalogError(
                f"型号 {product.get('model', requested_model)} 尚未启用，请先补齐可信资料"
            )
        _validate_product(product)
        return product

    raise ProductCatalogError(f"未收录型号：{requested_model}；V1 不进行模糊匹配")


def main() -> None:
    parser = argparse.ArgumentParser(description="精确读取魔点门禁产品资料")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            load_product(args.catalog, args.model), ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    main()

