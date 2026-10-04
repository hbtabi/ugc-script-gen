from types import SimpleNamespace

from ugc_script_gen.brief import Brief
from ugc_script_gen.scoring import find_claims, pacing_score, score_hook, score_script

BRIEF = Brief(brand="Acme", product="Widget", audience="cyclists", category="bike light",
              pain_points=["riding home in the dark"], benefits=["drivers see me from 200m", "it charges by USB"],
              proof=["4.9 stars"], cta="Tap the link", banned_claims=["unbreakable"])


def test_short_curious_hook_beats_long_flat_hook():
    good = score_hook("I tried this bike light for 7 days. Here's what happened.", BRIEF)
    bad = score_hook("Our company has been manufacturing lighting products of very high quality for many years now "
                     "and we think customers like them", BRIEF)
    assert good.total > bad.total + 30
    assert set(good.components) == {"brevity", "curiosity", "specificity", "direct_address", "relevance", "compliance"}


def test_banned_and_risky_claims_are_flagged():
    s = score_hook("This unbreakable light is guaranteed to work", BRIEF)
    assert s.components["compliance"] == 0
    assert any("unbreakable" in f for f in s.flags) and any("guaranteed" in f for f in s.flags)


def test_claims_match_whole_words_only():
    assert find_claims("procure the secure option") == []
    assert find_claims("It cures everything") == ["cures"]


def test_pacing_window():
    assert pacing_score(70, 30) == 100  # 70 / 78 words of capacity
    assert pacing_score(200, 30) == 0
    assert 0 < pacing_score(40, 30) < 100


def _script(vo_lines, last_on_screen="Tap the link"):
    beats = [SimpleNamespace(vo=v, on_screen="") for v in vo_lines]
    beats[-1].on_screen = last_on_screen
    return SimpleNamespace(beats=beats, hook=vo_lines[0], duration=15)


def test_script_score_components():
    s = score_script(_script(["Riding home in the dark? Watch this.", "Now drivers see me from 200m and it charges by USB.",
                              "4.9 stars. Tap the link."]), BRIEF)
    assert s.components["coverage"] == 100 and s.components["proof"] == 100 and s.components["cta"] == 100
    weak = score_script(_script(["Hello there.", "Nice product."], last_on_screen=""), BRIEF)
    assert weak.total < s.total and weak.components["cta"] < 100
