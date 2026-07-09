from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def file_sha256(path: str | Path) -> str:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_config(root: Path, firm: str) -> dict[str, Any]:
    config_path = root / "configs" / f"{firm}.yml"
    chunks_path = root / "configs" / "source_chunks.yml"
    cfg = load_yaml(config_path)
    chunks = load_yaml(chunks_path)
    cfg["source_chunks"] = chunks["chunks"]
    cfg["_config_path"] = str(config_path.relative_to(root))
    cfg["_config_sha256"] = file_sha256(config_path)
    cfg["_source_chunks_path"] = str(chunks_path.relative_to(root))
    cfg["_source_chunks_sha256"] = file_sha256(chunks_path)
    return cfg
