"""
Хранилище записей о паролях.

Все зашифрованные пароли лежат в одном JSON-файле. Каждая запись — это словарь
с сервисом, логином, зашифрованными данными и меткой времени. Открытых паролей
в файле нет, поэтому его можно спокойно хранить и даже коммитить (в отличие от
private_key.pem).

Формат файла:
{
    "entries": [
        {
            "id": "8f3c...",
            "service": "gmail",
            "username": "user@gmail.com",
            "encrypted_key": "ab12...",
            "token": "cd34...",
            "created_at": "2026-07-14T10:00:00+00:00"
        }
    ]
}
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any


class Storage:
    def __init__(self, path: str) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            self.entries = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.entries = data.get("entries", [])

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"entries": self.entries}, f, indent=2, ensure_ascii=False)

    def add(
        self,
        service: str,
        username: str,
        encrypted_key: str,
        token: str,
    ) -> dict[str, Any]:
        """Добавляет новую запись и сохраняет файл."""
        entry = {
            "id": uuid.uuid4().hex,
            "service": service,
            "username": username,
            "encrypted_key": encrypted_key,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        self._save()
        return entry

    def all(self) -> list[dict[str, Any]]:
        """Возвращает все записи."""
        return self.entries

    def find(self, entry_id: str) -> dict[str, Any] | None:
        """Ищет запись по её id."""
        for entry in self.entries:
            if entry["id"] == entry_id:
                return entry
        return None

    def delete(self, entry_id: str) -> bool:
        """Удаляет запись по id. Возвращает True, если что-то удалено."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        if len(self.entries) != before:
            self._save()
            return True
        return False
