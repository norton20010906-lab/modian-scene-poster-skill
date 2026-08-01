"""Read the JSON-compatible YAML used by this dependency-light skill."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a bundled configuration file is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"配置文件不存在：{config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"配置文件必须使用 JSON 兼容的 YAML 格式：{config_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"配置文件顶层必须是对象：{config_path}")
    return payload

