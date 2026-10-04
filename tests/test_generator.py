import random

import pytest

from ugc_script_gen import generate_hooks, generate_scripts, load_brief
from ugc_script_gen.generator import build_script, polish
from ugc_script_gen.llm import LLMError, MockLLM
from ugc_script_gen.templates import FORMATS

BRIEF = load_brief("examples/briefs/driftwell-sleep-mask.toml")


def test_hooks_are_ranked_unique_and_filled():
    hooks = generate_hooks(BRIEF, n=15)
    assert len(hooks) == 15
    scores = [h.score.total for h in hooks]
    assert scores == sorted(scores, reverse=True)
    assert len({h.text.lower() for h in hooks}) == 15
    assert all("{" not in h.text for h in hooks)


def test_social_proof_hooks_need_proof():
    BRIEF2 = load_brief("examples/briefs/driftwell-sleep-mask.toml")
    BRIEF2.proof = []
    assert all(h.angle != "social_proof" for h in generate_hooks(BRIEF2, n=100))


def test_generate_is_deterministic_and_diverse():
    a = generate_scripts(BRIEF, n=3, seed=1)
    b = generate_scripts(BRIEF, n=3, seed=1)
    assert [s.as_dict() for s in a] == [s.as_dict() for s in b]
    assert len({s.format for s in a}) == 3
    assert [s.score.total for s in a] == sorted([s.score.total for s in a], reverse=True)


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_every_format_builds_contiguous_timeline(fmt):
    s = build_script(BRIEF, fmt, "Hook line here.", random.Random(0))
    assert s.beats[0].start == 0 and s.beats[-1].end == BRIEF.duration
    for prev, nxt in zip(s.beats, s.beats[1:]):
        assert prev.end == nxt.start and prev.start < prev.end
    assert all("{" not in b.vo + b.on_screen for b in s.beats)
    assert BRIEF.cta.lower() in s.beats[-1].vo.lower()


def test_short_duration_tightens_or_drops_beats():
    brief = load_brief("examples/briefs/driftwell-sleep-mask.toml")
    brief.duration = 12
    s = build_script(brief, "problem_solution", "Hook.", random.Random(0))
    assert len(s.beats) < len(FORMATS["problem_solution"].beats)
    assert any("Dropped" in n for n in s.notes)


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        generate_scripts(BRIEF, formats=["nope"])


class FakeLLM:
    name = "fake"

    def __init__(self, hooks=None, fail=False, lines=None):
        self.hooks, self.fail, self.lines = hooks or [], fail, lines

    def propose_hooks(self, brief, n=5):
        if self.fail:
            raise LLMError("down")
        return self.hooks

    def polish_lines(self, lines, brief):
        if self.fail:
            raise LLMError("down")
        return self.lines(lines) if self.lines else lines


def test_llm_hooks_join_the_scored_pool():
    hooks = generate_hooks(BRIEF, n=200, llm=FakeLLM(hooks=["Your 5am wake-up call ends tonight?"]))
    assert any(h.angle == "llm" for h in hooks)


def test_llm_failure_falls_back_silently():
    assert generate_hooks(BRIEF, n=5, llm=FakeLLM(fail=True))
    assert generate_scripts(BRIEF, n=2, llm=FakeLLM(fail=True))


def test_polish_rejects_worse_rewrites():
    s = generate_scripts(BRIEF, n=1)[0]
    worse = polish(s, BRIEF, FakeLLM(lines=lambda ls: ["This is a guaranteed miracle cure."] * len(ls)))
    assert worse is s
    assert polish(s, BRIEF, MockLLM()) is s
