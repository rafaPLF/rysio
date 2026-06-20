from __future__ import annotations

import json
from pathlib import Path


class LocalizationService:
    def __init__(self, default_language: str = "de") -> None:
        self.default_language = default_language
        self._locale_dir = Path(__file__).resolve().parent.parent / "locales"
        self._cache: dict[str, dict[str, str]] = {}

    def translate(self, key: str, language: str | None = None, **kwargs: object) -> str:
        active_language = language or self.default_language
        locale = self._load_locale(active_language)
        template = locale.get(key) or self._load_locale(self.default_language).get(key) or key
        return template.format(**kwargs)

    def _load_locale(self, language: str) -> dict[str, str]:
        if language in self._cache:
            return self._cache[language]

        locale_path = self._locale_dir / f"{language}.json"
        if not locale_path.exists():
            if language != self.default_language:
                return self._load_locale(self.default_language)
            return {}

        self._cache[language] = json.loads(locale_path.read_text(encoding="utf-8"))
        return self._cache[language]
