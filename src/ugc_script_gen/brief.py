"""Product brief model and loaders (TOML or JSON)."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

PLATFORMS = {"tiktok": 9 / 16, "reels": 9 / 16, "shorts": 9 / 16}
TONES = {"casual", "premium", "playful", "clinical"}


class BriefError(ValueError):
    """Raised when a brief is missing required fields or has invalid values."""


@dataclass
class Brief:
    brand: str
    product: str
    audience: str
    pain_points: list[str]
    benefits: list[str]
    category: str = "product"
    usp: str = ""
    proof: list[str] = field(default_factory=list)
    offer: str = ""
    cta: str = "Tap the link to try it"
    tone: str = "casual"
    platform: str = "tiktok"
    duration: int = 30
    banned_claims: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("brand", "product", "audience"):
            if not str(getattr(self, name)).strip():
                raise BriefError(f"brief field '{name}' must not be empty")
        if not self.pain_points:
            raise BriefError("brief needs at least one pain point")
        if not self.benefits:
            raise BriefError("brief needs at least one benefit")
        self.platform = self.platform.lower()
        if self.platform not in PLATFORMS:
            raise BriefError(f"platform must be one of {sorted(PLATFORMS)}")
        self.tone = self.tone.lower()
        if self.tone not in TONES:
            raise BriefError(f"tone must be one of {sorted(TONES)}")
        if not 10 <= int(self.duration) <= 90:
            raise BriefError("duration must be between 10 and 90 seconds")
        self.duration = int(self.duration)

    @classmethod
    def from_dict(cls, data: dict) -> Brief:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise BriefError(f"unknown brief field(s): {', '.join(sorted(unknown))}")
        missing = [n for n in ("brand", "product", "audience", "pain_points", "benefits") if n not in data]
        if missing:
            raise BriefError(f"missing required field(s): {', '.join(missing)}")
        return cls(**data)


def load_brief(path: str | Path) -> Brief:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = tomllib.loads(text)
    return Brief.from_dict(data.get("brief", data))
