"""Promote an explicitly approved P4 layout recipe into the internal template library."""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

try:
    from .compose_candidate_set import load_template_library
    from .config_io import load_config
except ImportError:
    from compose_candidate_set import load_template_library
    from config_io import load_config

RECIPE_FIELDS = ("composition", "text_hierarchy", "product_placement", "prompt_guidance")

def _validate_candidate(candidate: dict[str, Any]) -> None:
    evidence = candidate.get("promotion_evidence")
    if not isinstance(evidence, dict) or evidence.get("user_approved") is not True:
        raise ValueError("只有经过用户明确认可的 P4 才能加入模板库")
    if evidence.get("selection_key") != "P4":
        raise ValueError("晋升来源必须是本轮 P4 探索位")
    for field in ("run_id", "sample_path"):
        if not evidence.get(field):
            raise ValueError(f"晋升证据缺少 {field}")
    for field in ("id", "label", "source", "best_for", "product_width_target", "scene_asset", "renderer"):
        if not candidate.get(field):
            raise ValueError(f"候选模板缺少 {field}")
    recipe = candidate.get("layout_recipe")
    if not isinstance(recipe, dict) or any(not recipe.get(field) for field in RECIPE_FIELDS):
        raise ValueError("候选模板必须包含可复用的构图、文字层级、产品位置和提示词规则")

def promote_template(catalog_path: str | Path, candidate_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    library = deepcopy(load_template_library(catalog_path))
    candidate = load_config(candidate_path)
    _validate_candidate(candidate)
    if candidate["id"] in {item["id"] for item in library["templates"]}:
        raise ValueError(f"模板 ID 已存在：{candidate['id']}")
    promoted = deepcopy(candidate)
    promoted["status"] = "approved"
    promoted["origin"] = "experimental_promotion"
    promoted["promoted_at"] = date.today().isoformat()
    library["templates"].append(promoted)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_template_library(output)
    return library

def main() -> None:
    parser = argparse.ArgumentParser(description="将用户认可的 P4 版式晋升到内部模板库")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = promote_template(args.catalog, args.candidate, args.output)
    print(json.dumps({"output": str(Path(args.output).resolve()), "templates": len(result["templates"])}, ensure_ascii=False))

if __name__ == "__main__":
    main()
