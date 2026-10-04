import json

import pytest

from ugc_script_gen.brief import Brief, BriefError, load_brief

BASE = dict(brand="Acme", product="Widget", audience="busy parents",
            pain_points=["lost keys"], benefits=["I never lose my keys"])


def test_loads_toml_example():
    b = load_brief("examples/briefs/driftwell-sleep-mask.toml")
    assert b.brand == "Driftwell" and b.duration == 30 and b.platform == "tiktok"


def test_loads_json(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps(BASE))
    assert load_brief(p).product == "Widget"


def test_nested_brief_table(tmp_path):
    p = tmp_path / "b.toml"
    p.write_text('[brief]\nbrand="A"\nproduct="B"\naudience="C"\npain_points=["x"]\nbenefits=["y"]\n')
    assert load_brief(p).brand == "A"


@pytest.mark.parametrize("patch,msg", [
    ({"brand": " "}, "brand"),
    ({"pain_points": []}, "pain point"),
    ({"benefits": []}, "benefit"),
    ({"platform": "myspace"}, "platform"),
    ({"tone": "angry"}, "tone"),
    ({"duration": 300}, "duration"),
])
def test_validation(patch, msg):
    with pytest.raises(BriefError, match=msg):
        Brief(**{**BASE, **patch})


def test_unknown_and_missing_fields():
    with pytest.raises(BriefError, match="unknown"):
        Brief.from_dict({**BASE, "colour": "red"})
    with pytest.raises(BriefError, match="missing"):
        Brief.from_dict({"brand": "x"})
