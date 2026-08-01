"""Audit a checked-out Skill repository for portability and release-scope leaks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "output"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".gitignore"}
ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:[\\/](?:Users|桌面|Desktop|Temp)[\\/]|/(?:Users|home|tmp)/)"
)
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _issue(code: str, path: str, detail: str) -> dict[str, str]:
    return {"code": code, "path": path, "detail": detail}


def _text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.casefold() in TEXT_SUFFIXES or path.name == ".gitignore":
            yield path


def audit_repository(root: str | Path, *, allowed_models: set[str]) -> dict[str, Any]:
    repo = Path(root).resolve()
    issues: list[dict[str, str]] = []
    if not (repo / "SKILL.md").is_file():
        issues.append(_issue("missing_skill", "SKILL.md", "仓库根目录缺少 SKILL.md"))

    for path in _text_files(repo):
        relative = path.relative_to(repo).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append(_issue("non_utf8_text", relative, "文本文件不是 UTF-8"))
            continue
        if ABSOLUTE_PATH_PATTERN.search(content):
            issues.append(_issue("absolute_path", relative, "包含不可移植的个人或临时绝对路径"))
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            issues.append(_issue("secret", relative, "疑似包含密钥或私钥"))

    catalog_path = repo / "data" / "products.yaml"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(_issue("invalid_catalog", "data/products.yaml", str(exc)))
        catalog = {"products": []}
    for product in catalog.get("products", []):
        model = str(product.get("model", ""))
        if model not in allowed_models:
            issues.append(_issue("unsupported_model", "data/products.yaml", f"首发范围不包含 {model}"))
        for source in product.get("sources", []):
            locator = source.get("path")
            if not locator:
                continue
            locator_text = str(locator)
            if Path(locator_text).is_absolute() or ABSOLUTE_PATH_PATTERN.search(locator_text):
                issues.append(_issue("absolute_path", "data/products.yaml", locator_text))
                continue
            if not (repo / locator_text).is_file():
                issues.append(_issue("missing_asset", locator_text, "资料库引用的相对资源不存在"))

    unique = []
    seen = set()
    for item in issues:
        key = (item["code"], item["path"], item["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return {"schema_version": 1, "ok": not unique, "root": str(repo), "issues": unique}


def main() -> None:
    parser = argparse.ArgumentParser(description="审计可公开传播的 Skill 仓库")
    parser.add_argument("--root", default=".")
    parser.add_argument("--allowed-model", action="append", required=True)
    args = parser.parse_args()
    result = audit_repository(args.root, allowed_models=set(args.allowed_model))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
