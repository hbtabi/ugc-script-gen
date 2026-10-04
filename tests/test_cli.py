import json

from ugc_script_gen.cli import main

B = "examples/briefs/driftwell-sleep-mask.toml"


def test_generate_writes_files(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["generate", B, "-n", "2", "-o", str(tmp_path)]) == 0
    md = sorted(tmp_path.glob("*.md"))
    assert len(md) == 2 and "| # | Time | Shot |" in md[0].read_text()
    data = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert len(data) == 2 and data[0]["beats"]
    assert "backend: mock" in capsys.readouterr().out


def test_hooks_json(capsys):
    assert main(["hooks", B, "-n", "3", "--json", "--offline"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 3


def test_duration_override_and_bad_brief(tmp_path, capsys):
    assert main(["generate", B, "-d", "15", "--json", "--offline", "-n", "1"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["duration"] == 15
    bad = tmp_path / "bad.toml"
    bad.write_text('brand="x"')
    assert main(["generate", str(bad)]) == 2


def test_formats(capsys):
    assert main(["formats"]) == 0
    assert "problem_solution" in capsys.readouterr().out
