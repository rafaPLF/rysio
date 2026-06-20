from __future__ import annotations

import json
from pathlib import Path


class OwnerService:
    def __init__(self) -> None:
        self._state_path = Path(__file__).resolve().parent.parent / "data" / "owner_state.json"
        self._disabled_bypass_user_ids: set[int] = set()

    async def load(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._state_path.exists():
            return

        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        values = data.get("disabled_bypass_user_ids", [])
        self._disabled_bypass_user_ids = {int(value) for value in values}

    def is_bypass_enabled(self, user_id: int) -> bool:
        return user_id not in self._disabled_bypass_user_ids

    def set_bypass_enabled(self, user_id: int, enabled: bool) -> None:
        if enabled:
            self._disabled_bypass_user_ids.discard(user_id)
        else:
            self._disabled_bypass_user_ids.add(user_id)
        self._save()

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "disabled_bypass_user_ids": sorted(self._disabled_bypass_user_ids),
        }
        self._state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
