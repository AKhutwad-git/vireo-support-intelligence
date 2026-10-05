"""Hash-keyed JSONL cache; raw ticket inputs are never persisted."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def cache_key(request_text: str, model: str, prompt_version: str) -> str:
    return hashlib.sha256((prompt_version + "\0" + model + "\0" + request_text).encode("utf-8")).hexdigest()


class ResultCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line); self.data[item["key"]] = item["value"]
                except (json.JSONDecodeError, KeyError):
                    continue

    def get(self, key): return self.data.get(key)

    @staticmethod
    def make_key(request_text: str, model: str, prompt_version: str) -> str:
        return cache_key(request_text, model, prompt_version)

    def set(self, key, value):
        self.data[key] = value
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")
