"""Turn a brief into ranked hooks and timed, shot-ready scripts."""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field

from .brief import Brief
from .llm import LLMError, MockLLM
from .scoring import WORDS_PER_SECOND, Score, score_hook, score_script, words
from .templates import FORMATS, HOOKS, TONE_SIGNOFFS


class _Safe(dict):
    def __missing__(self, key):
        return ""


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _sentence(s: str) -> str:
    s = s.strip()
    return s if not s or s[-1] in ".!?" else s + "."


def _tidy(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([.,!?])", r"\1", s)
    s = re.sub(r"\.\.+", ".", s)
    return s


def _short(text: str, max_words: int = 7) -> str:
    first = re.split(r"(?<=[.?!:])\s", text.strip())[0].rstrip(".!")
    w = first.split()
    return " ".join(w[:max_words]) + ("…" if len(w) > max_words else "")


def build_context(brief: Brief, pain: str | None = None) -> dict:
    pain = pain or brief.pain_points[0]
    b = (brief.benefits * 3)[:3]
    usp = _sentence(brief.usp) if brief.usp else f"It's made for {brief.audience}."
    proof = brief.proof[0] if brief.proof else ""
    return _Safe(
        brand=brief.brand, product=brief.product, category=brief.category, audience=brief.audience,
        pain=pain, Pain=_cap(pain),
        benefit_1=b[0], benefit_2=b[1], benefit_3=b[2], Benefit_1=_cap(b[0]),
        usp_sentence=usp, usp_sentence_lower=usp[:1].lower() + usp[1:],
        proof=proof, proof_lower=proof[:1].lower() + proof[1:],
        proof_sentence=f"{_cap(proof)}, so it's not just me." if proof else "And I'm clearly not the only one obsessed.",
        offer_sentence=_sentence(brief.offer) + " " if brief.offer else "",
        cta=brief.cta.rstrip("."), cta_short=_short(brief.cta, 7) + " ↓",
    )


@dataclass
class Hook:
    text: str
    angle: str
    score: Score

    def as_dict(self) -> dict:
        return {"text": self.text, "angle": self.angle, "score": self.score.as_dict()}


def generate_hooks(brief: Brief, n: int = 10, llm=None) -> list[Hook]:
    """Fill every hook template for every pain point, score, de-duplicate and rank."""
    seen: set[str] = set()
    pool: list[Hook] = []
    for pain in brief.pain_points:
        ctx = build_context(brief, pain)
        for angle, templates in HOOKS.items():
            if angle == "social_proof" and not brief.proof:
                continue
            for t in templates:
                text = _tidy(t.format_map(ctx))
                if text.lower() not in seen:
                    seen.add(text.lower())
                    pool.append(Hook(text, angle, score_hook(text, brief)))
    llm = llm or MockLLM()
    try:
        for text in llm.propose_hooks(brief, 5):
            text = _tidy(text)
            if text and text.lower() not in seen:
                seen.add(text.lower())
                pool.append(Hook(text, "llm", score_hook(text, brief)))
    except LLMError:
        pass
    pool.sort(key=lambda h: (-h.score.total, h.text))
    return pool[:n]


@dataclass
class ScriptBeat:
    name: str
    start: float
    end: float
    shot: str
    vo: str
    on_screen: str
    broll: str = ""


@dataclass
class Script:
    brand: str
    product: str
    format: str
    format_title: str
    platform: str
    duration: int
    hook: str
    beats: list[ScriptBeat]
    score: Score | None = None
    llm: str = "mock"
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["score"] = self.score.as_dict() if self.score else None
        return d


def _timings(weights: list[float], duration: int) -> list[tuple[float, float]]:
    total = sum(weights)
    out, t = [], 0.0
    for i, w in enumerate(weights):
        end = float(duration) if i == len(weights) - 1 else round((t + duration * w / total) * 2) / 2
        out.append((t, end))
        t = end
    return out


def _hook_for(fmt_key: str, ranked: list[Hook], ctx: dict, rng: random.Random) -> str:
    angle = {"three_reasons": "listicle", "before_after": "before_after"}.get(fmt_key)
    if angle:
        return _tidy(rng.choice(HOOKS[angle]).format_map(ctx))
    top = [h.text for h in ranked if h.angle not in ("listicle", "before_after")][:6]
    return rng.choice(top)


def _assemble(brief: Brief, fmt, beats_src, ctx: dict, rng: random.Random, tight: bool) -> list[ScriptBeat]:
    beats = []
    for beat, (start, end) in zip(beats_src, _timings([b.weight for b in beats_src], brief.duration)):
        option = min(beat.vo, key=len) if tight else rng.choice(beat.vo)
        vo = _tidy(option.format_map(ctx))
        on_screen = " · ".join(_tidy(o.format_map(ctx)) for o in beat.on_screen)
        beats.append(ScriptBeat(beat.name, start, end, beat.shot, vo, on_screen, beat.broll))
    return beats


def _overruns(beats: list[ScriptBeat], duration: int) -> bool:
    return len(words(" ".join(b.vo for b in beats))) > duration * WORDS_PER_SECOND


def build_script(brief: Brief, fmt_key: str, hook: str, rng: random.Random, pain: str | None = None) -> Script:
    """Fill a format for the brief. If the VO overruns the runtime, tighten lines, then drop optional beats."""
    fmt = FORMATS[fmt_key]
    ctx = build_context(brief, pain)
    ctx["hook"] = hook
    ctx["hook_short"] = _short(hook).lower()
    ctx["hook_listicle"] = ctx["hook_before_after"] = hook
    ctx["signoff"] = rng.choice(TONE_SIGNOFFS[brief.tone])
    src = list(fmt.beats)
    beats = _assemble(brief, fmt, src, ctx, rng, tight=False)
    notes = []
    if _overruns(beats, brief.duration):
        ctx["signoff"] = ""
        beats = _assemble(brief, fmt, src, ctx, rng, tight=True)
        notes.append("Tightened: shortest line variants used and sign-off removed to fit the runtime.")
        for victim in sorted((b for b in src if b.drop), key=lambda b: -b.drop):
            if not _overruns(beats, brief.duration):
                break
            src.remove(victim)
            beats = _assemble(brief, fmt, src, ctx, rng, tight=True)
            notes.append(f"Dropped optional '{victim.name}' beat to fit {brief.duration}s.")
    notes += [f"Aspect 9:16 for {brief.platform}; keep captions inside the centre safe zone.",
              "Burn in captions: most short-form views start muted.",
              "Hook must land in the first 1.5s; cut any lead-in breath."]
    return Script(brief.brand, brief.product, fmt.key, fmt.title, brief.platform, brief.duration, hook, beats, notes=notes)


def polish(script: Script, brief: Brief, llm) -> Script:
    """Ask the LLM to polish VO lines; keep the original if it errors or scores worse."""
    if isinstance(llm, MockLLM):
        return script
    try:
        lines = llm.polish_lines([b.vo for b in script.beats], brief)
    except LLMError:
        return script
    beats = [ScriptBeat(**{**b.__dict__, "vo": _tidy(line)}) for b, line in zip(script.beats, lines)]
    candidate = Script(**{**script.__dict__, "beats": beats})
    candidate.hook = candidate.beats[0].vo
    candidate.score = score_script(candidate, brief)
    candidate.llm = llm.name
    return candidate if candidate.score.total >= script.score.total else script


def generate_scripts(brief: Brief, n: int = 3, formats: list[str] | None = None, seed: int = 7,
                     variants: int = 6, llm=None) -> list[Script]:
    """Generate ``variants`` candidates per format, score them, return the top ``n`` (one per format first)."""
    llm = llm or MockLLM()
    rng = random.Random(seed)
    keys = formats or list(FORMATS)
    for k in keys:
        if k not in FORMATS:
            raise ValueError(f"unknown format '{k}'. Choose from: {', '.join(FORMATS)}")
    ranked = generate_hooks(brief, n=30, llm=llm)
    candidates: list[Script] = []
    for k in keys:
        for _ in range(variants):
            pain = rng.choice(brief.pain_points)
            ctx = build_context(brief, pain)
            s = build_script(brief, k, _hook_for(k, ranked, ctx, rng), rng, pain)
            s.score = score_script(s, brief)
            candidates.append(s)
    candidates.sort(key=lambda s: -s.score.total)
    picked, used, hooks = [], set(), set()
    for strict in (True, False):  # diversity pass: best of each format, preferring unused hooks
        for s in candidates:
            if s.format not in used and (not strict or s.hook not in hooks):
                picked.append(s)
                used.add(s.format)
                hooks.add(s.hook)
    picked.sort(key=lambda s: -s.score.total)
    picked = picked[:n]
    for s in candidates:
        if len(picked) >= n:
            break
        if s not in picked:
            picked.append(s)
    return [polish(s, brief, llm) for s in picked]
