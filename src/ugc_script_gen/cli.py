"""Command-line interface: ``ugc-script-gen hooks|generate|formats``."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import __version__
from .brief import BriefError, load_brief
from .generator import generate_hooks, generate_scripts
from .llm import get_llm
from .render import hooks_table, summary, to_json, to_markdown
from .templates import FORMATS


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ugc-script-gen", description="Shot-ready UGC ad scripts from a product brief.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hooks", help="rank scroll-stopping hooks for a brief")
    h.add_argument("brief")
    h.add_argument("-n", type=int, default=10)
    h.add_argument("--json", action="store_true")
    h.add_argument("--offline", action="store_true", help="never call an LLM, even if OPENAI_API_KEY is set")

    g = sub.add_parser("generate", help="generate ranked, timed scripts")
    g.add_argument("brief")
    g.add_argument("-n", type=int, default=3, help="number of scripts to keep")
    g.add_argument("-f", "--format", action="append", choices=list(FORMATS), help="restrict to format(s)")
    g.add_argument("-d", "--duration", type=int, help="override brief duration (seconds)")
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("-o", "--out", help="write Markdown + JSON files to this directory")
    g.add_argument("--json", action="store_true", help="print JSON instead of a summary")
    g.add_argument("--offline", action="store_true")

    sub.add_parser("formats", help="list script formats")
    a = p.parse_args(argv)

    if a.cmd == "formats":
        for f in FORMATS.values():
            print(f"{f.key:<17} {f.title:<28} {f.description}")
        return 0
    try:
        brief = load_brief(a.brief)
        if getattr(a, "duration", None):
            brief.duration = a.duration
            brief.__post_init__()
    except (OSError, BriefError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    llm = get_llm(a.offline)

    if a.cmd == "hooks":
        hooks = generate_hooks(brief, a.n, llm)
        print(to_json(hooks) if a.json else hooks_table(hooks))
        return 0

    scripts = generate_scripts(brief, a.n, a.format, a.seed, llm=llm)
    if a.json:
        print(to_json(scripts))
    else:
        print(f"{brief.brand} · {brief.product} · {brief.platform} · {brief.duration}s · backend: {llm.name}\n")
        print(summary(scripts))
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        base = _slug(f"{brief.brand}-{brief.product}")
        for i, s in enumerate(scripts, 1):
            (out / f"{base}-{i}-{s.format}.md").write_text(to_markdown(s, i), encoding="utf-8")
        (out / f"{base}.json").write_text(to_json(scripts), encoding="utf-8")
        if not a.json:
            print(f"\nwrote {len(scripts)} scripts to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
