"""Render scripts as shot-ready Markdown, JSON or a coloured terminal summary."""

from __future__ import annotations

import json
import os
import sys

from .generator import Hook, Script


def _fmt_t(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def to_markdown(script: Script, rank: int | None = None) -> str:
    title = f"{script.brand}: {script.product}"
    lines = [f"# {'#' + str(rank) + ' ' if rank else ''}{title}", "",
             f"**Format:** {script.format_title} · **Platform:** {script.platform} · **Length:** {script.duration}s · "
             f"**Score:** {script.score.total:.0f}/100", "",
             f"> **Hook:** {script.hook}", "",
             "| # | Time | Shot | On-screen text | Voice-over |", "|---|------|------|----------------|------------|"]
    for i, b in enumerate(script.beats, 1):
        cell = lambda s: s.replace("|", "\\|")
        shot = cell(b.shot) + (f"<br>_B-roll: {cell(b.broll)}_" if b.broll else "")
        lines.append(f"| {i} | {_fmt_t(b.start)}–{_fmt_t(b.end)} | {shot} | {cell(b.on_screen)} | {cell(b.vo)} |")
    lines += ["", "## Score breakdown", ""]
    for k, v in script.score.components.items():
        lines.append(f"- **{k}**: {v:.0f}")
    if script.score.flags:
        lines += ["", "**Flags:** " + "; ".join(script.score.flags)]
    lines += ["", "## Production notes", ""] + [f"- {n}" for n in script.notes]
    return "\n".join(lines) + "\n"


def to_json(items) -> str:
    return json.dumps([i.as_dict() for i in items], indent=2, ensure_ascii=False)


def _color() -> bool:
    return os.environ.get("FORCE_COLOR", "") not in ("", "0") or (sys.stdout.isatty() and not os.environ.get("NO_COLOR"))


def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if _color() else s


def _bar(v: float, width: int = 20) -> str:
    n = round(v / 100 * width)
    code = "32" if v >= 80 else "33" if v >= 60 else "31"
    return _c(code, "█" * n) + _c("90", "░" * (width - n))


def summary(scripts: list[Script]) -> str:
    out = []
    for i, s in enumerate(scripts, 1):
        out.append(f"{_c('1;36', f'#{i}')} {_c('1', s.format_title)}  {_bar(s.score.total)} "
                   f"{_c('1', f'{s.score.total:.0f}')}/100  {_c('90', f'{s.duration}s · {len(s.beats)} beats · {s.llm}')}")
        out.append(f"   {_c('33', 'hook')}  “{s.hook}”")
        comps = "  ".join(f"{k} {v:.0f}" for k, v in s.score.components.items())
        out.append(f"   {_c('90', comps)}")
        for f in s.score.flags:
            out.append(f"   {_c('31', '! ' + f)}")
    return "\n".join(out)


def hooks_table(hooks: list[Hook]) -> str:
    out = []
    for i, h in enumerate(hooks, 1):
        out.append(f"{_c('90', f'{i:>2}.')} {_bar(h.score.total, 10)} {_c('1', f'{h.score.total:>3.0f}')}  "
                   f"{_c('35', f'{h.angle:<13}')} {h.text}")
    return "\n".join(out)
