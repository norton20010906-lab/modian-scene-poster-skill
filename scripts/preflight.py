"""Check whether a host can run the poster Skill before generation starts."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

try:
    from .config_io import load_config
    from .load_product_info import ProductCatalogError, load_product
except ImportError:
    from config_io import load_config
    from load_product_info import ProductCatalogError, load_product


REQUIRED_CAPABILITIES = {"vision", "image-generation"}


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for item in value.split("."):
        digits = "".join(character for character in item if character.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _font_candidates(root: Path) -> list[Path]:
    candidates = list((root / "assets" / "fonts").glob("*.ttf"))
    candidates.extend((root / "assets" / "fonts").glob("*.otf"))
    windows_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates.extend([
        windows_dir / "Fonts" / "msyh.ttc",
        windows_dir / "Fonts" / "simhei.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ])
    return candidates


def _workspace_is_writable(workspace: Path) -> bool:
    if not workspace.is_dir():
        return False
    try:
        with tempfile.NamedTemporaryFile(prefix="modian-preflight-", dir=workspace, delete=True):
            return True
    except OSError:
        return False


def run_preflight(
    *,
    workspace: str | Path,
    catalog_path: str | Path,
    templates_path: str | Path,
    model: str,
    host_capabilities: Iterable[str],
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    workspace_path = Path(workspace).resolve()
    capabilities = {str(item).strip().casefold() for item in host_capabilities}
    checks: dict[str, dict[str, Any]] = {}

    python_ok = sys.version_info >= (3, 10)
    checks["python"] = {
        "ok": python_ok,
        "detected": ".".join(map(str, sys.version_info[:3])),
        "remediation": "在 WorkBuddy 设置中安装 Python 3.10 或更高版本。",
    }

    try:
        pillow = importlib.import_module("PIL")
        pillow_version = str(getattr(pillow, "__version__", "0"))
        pillow_ok = (10,) <= _version_tuple(pillow_version) < (13,)
    except ImportError:
        pillow_version, pillow_ok = "missing", False
    checks["pillow"] = {
        "ok": pillow_ok,
        "detected": pillow_version,
        "remediation": "经用户授权后运行：python -m pip install -r requirements.txt",
    }

    font = next((path for path in _font_candidates(root) if path.is_file()), None)
    checks["chinese_font"] = {
        "ok": font is not None,
        "detected": str(font) if font else None,
        "remediation": "安装微软雅黑、Noto Sans CJK 或苹方中文字体后重试。",
    }

    writable = _workspace_is_writable(workspace_path)
    checks["workspace_writable"] = {
        "ok": writable,
        "detected": str(workspace_path),
        "remediation": "在 WorkBuddy 中选择一个允许写入的工作空间。",
    }

    try:
        product = load_product(catalog_path, model)
        product_ok = product.get("model") == "D5 Ultra"
        product_message = product.get("model")
    except ProductCatalogError as exc:
        product_ok, product_message = False, str(exc)
    checks["product_catalog"] = {
        "ok": product_ok,
        "detected": product_message,
        "remediation": "首发版本仅支持资料完整的 D5 Ultra。",
    }

    try:
        templates = load_config(templates_path)
        approved = [
            item for item in templates.get("templates", [])
            if isinstance(item, dict) and item.get("status") == "approved"
        ]
        strategy = templates.get("candidate_strategy", {})
        templates_ok = (
            len(approved) >= 3
            and strategy.get("library_pick_count") == 3
            and strategy.get("exploration_count") == 1
        )
        template_message = f"approved={len(approved)}"
    except (OSError, ValueError) as exc:
        templates_ok, template_message = False, str(exc)
    checks["template_library"] = {
        "ok": templates_ok,
        "detected": template_message,
        "remediation": "恢复完整的 3+1 模板注册表。",
    }

    checks["vision"] = {
        "ok": "vision" in capabilities,
        "detected": "vision" in capabilities,
        "remediation": "在 WorkBuddy 中切换到支持图片理解的模型。",
    }
    checks["image_generation"] = {
        "ok": "image-generation" in capabilities,
        "detected": "image-generation" in capabilities,
        "remediation": "启用 WorkBuddy 图片生成工具；不可用时停止正式海报生成。",
    }

    return {
        "schema_version": 1,
        "ready": all(item["ok"] for item in checks.values()),
        "model": model,
        "workspace": str(workspace_path),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查魔点门禁海报 Skill 的运行条件")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--templates", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--host-capability", action="append", default=[])
    args = parser.parse_args()
    result = run_preflight(
        workspace=args.workspace,
        catalog_path=args.catalog,
        templates_path=args.templates,
        model=args.model,
        host_capabilities=args.host_capability,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
