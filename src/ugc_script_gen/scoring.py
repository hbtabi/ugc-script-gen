"""Transparent, rule-based scoring for hooks and full scripts.

Each score is a weighted sum of named components so you can see *why* a script
ranked where it did. Weights are deliberately simple and live in this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

WORDS_PER_SECOND = 2.6  # comfortable conversational VO pace

RISKY_CLAIMS = [
    "cure", "cures", "guaranteed", "guarantee", "miracle", "100%", "instantly", "overnight",
    "clinically proven", "doctor recommended", "risk-free", "permanent", "no side effects",
]
CURIOSITY_CUES = ["this", "here's", "until", "watch", "didn't expect", "wish", "secret", "nobody",
                  "stop", "what happened", "wrong", "gatekeeping", "vs"]
DIRECT_ADDRESS = re.compile(r"\b(you|your|you're|pov|me|my|i)\b", re.I)
WORD = re.compile(r"[A-Za-z0-9'’]+")


def words(text: str) -> list[str]:
    return WORD.findall(text)


@dataclass
class Score:
    total: float
    components: dict[str, float]
    flags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"total": round(self.total, 1), "components": {k: round(v, 1) for k, v in self.components.items()},
                "flags": list(self.flags)}


def find_claims(text: str, banned: list[str] | None = None) -> list[str]:
    lower = text.lower()
    hits = []
    for claim in [*(banned or []), *RISKY_CLAIMS]:
        c = claim.lower().strip()
        if c and re.search(r"(?<![a-z])" + re.escape(c) + r"(?![a-z])", lower) and c not in hits:
            hits.append(c)
    return hits


def _keywords(phrases: list[str]) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "my", "your", "i", "you", "it", "is", "at"}
    return {w.lower() for p in phrases for w in words(p) if len(w) > 2 and w.lower() not in stop}


def score_hook(hook: str, brief=None) -> Score:
    """Score a hook out of 100 on brevity, curiosity, specificity, address, relevance and compliance."""
    n = len(words(hook))
    lower = hook.lower()
    comp: dict[str, float] = {}
    comp["brevity"] = 25.0 if n <= 10 else max(0.0, 25.0 * (22 - n) / 12)
    comp["curiosity"] = 20.0 if (any(c in lower for c in CURIOSITY_CUES) or hook.strip().endswith("?")) else 6.0
    comp["specificity"] = 15.0 if re.search(r"\d", hook) else 5.0
    comp["direct_address"] = 15.0 if DIRECT_ADDRESS.search(hook) else 4.0
    relevance = 7.0
    if brief is not None:
        kws = _keywords([*brief.pain_points, *brief.benefits, brief.product, brief.category])
        if kws & {w.lower() for w in words(hook)}:
            relevance = 15.0
    comp["relevance"] = relevance
    flags = find_claims(hook, getattr(brief, "banned_claims", None))
    comp["compliance"] = 0.0 if flags else 10.0
    return Score(sum(comp.values()), comp, [f"risky claim: '{f}'" for f in flags])


WEIGHTS = {"hook": 0.30, "pacing": 0.20, "coverage": 0.20, "proof": 0.10, "cta": 0.10, "compliance": 0.10}


def pacing_score(vo_words: int, duration: float) -> float:
    capacity = duration * WORDS_PER_SECOND
    ratio = vo_words / capacity if capacity else 0
    if 0.7 <= ratio <= 1.0:
        return 100.0
    if ratio < 0.7:
        return max(0.0, 100 - (0.7 - ratio) * 200)
    return max(0.0, 100 - (ratio - 1.0) * 250)


def score_script(script, brief) -> Score:
    """Score a full script (an object with ``.beats``, ``.hook`` and ``.duration``)."""
    vo = " ".join(b.vo for b in script.beats)
    full = vo + " " + " ".join(b.on_screen for b in script.beats)
    lower = full.lower()
    hook = score_hook(script.hook, brief)
    comp = {"hook": hook.total}
    comp["pacing"] = pacing_score(len(words(vo)), script.duration)
    wanted = brief.benefits[:3]
    covered = sum(1 for b in wanted if b.lower() in lower)
    comp["coverage"] = 100.0 * covered / len(wanted)
    if brief.proof:
        comp["proof"] = 100.0 if any(p.lower() in lower for p in brief.proof) else 40.0
    else:
        comp["proof"] = 60.0
    last = script.beats[-1]
    comp["cta"] = 100.0 if brief.cta.lower() in (last.vo + " " + last.on_screen).lower() else 30.0
    claims = find_claims(full, brief.banned_claims)
    comp["compliance"] = max(0.0, 100.0 - 50.0 * len(claims))
    total = sum(comp[k] * w for k, w in WEIGHTS.items())
    flags = [f"risky claim: '{c}'" for c in claims]
    if comp["pacing"] < 70:
        flags.append(f"pacing: {len(words(vo))} VO words for {script.duration}s")
    return Score(total, comp, flags)
