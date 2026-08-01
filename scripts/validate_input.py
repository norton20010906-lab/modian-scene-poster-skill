"""Validate the three public inputs before any model or image work begins."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_REQUIREMENT_LENGTH = 200


class InputValidationError(ValueError):
    """Raised when an invocation cannot safely enter the workflow."""


def validate_input(
    image_path: str | Path, model: str, requirement: str | None = None
) -> dict[str, str]:
    image = Path(image_path).expanduser().resolve()
    normalized_model = " ".join((model or "").split())
    normalized_requirement = " ".join((requirement or "").split())

    if not image.is_file():
        raise InputValidationError(f"产品图片不存在：{image}")
    if image.suffix.casefold() not in SUPPORTED_IMAGE_SUFFIXES:
        allowed = "、".join(sorted(SUPPORTED_IMAGE_SUFFIXES))
        raise InputValidationError(f"不支持的图片格式；仅支持 {allowed}")
    if not normalized_model:
        raise InputValidationError("产品型号不能为空")
    if len(normalized_model) > 80:
        raise InputValidationError("产品型号不能超过 80 个字符")
    if len(normalized_requirement) > MAX_REQUIREMENT_LENGTH:
        raise InputValidationError(
            f"补充需求不能超过 {MAX_REQUIREMENT_LENGTH} 个字符"
        )

    return {
        "image_path": str(image),
        "model": normalized_model,
        "requirement": normalized_requirement,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验魔点门禁海报 Skill 输入")
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--requirement", default="")
    args = parser.parse_args()
    print(
        json.dumps(
            validate_input(args.image, args.model, args.requirement),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

