import json

from PIL import Image

from pressready.cli import main
from test_build import make_manuscript


def test_cli_build(tmp_path, capsys):
    ms = tmp_path / "ms"
    make_manuscript(ms)
    art = tmp_path / "front.png"
    Image.new("RGB", (800, 1200), (30, 90, 160)).save(art)
    out = tmp_path / "out"
    code = main(["build", str(ms), "--cover", str(art), "--out", str(out), "--trim", "5x8", "--paper", "cream"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert (out / "book.epub").is_file() and (out / "checklist.json").is_file()


def test_cli_mcp_subcommand_starts_server(monkeypatch):
    called = []
    monkeypatch.setattr("pressready.mcp_server.main", lambda: called.append(1))
    assert main(["mcp"]) == 0
    assert called == [1]


def test_server_json_launches_mcp_subcommand():
    from pathlib import Path
    server = json.loads((Path(__file__).resolve().parents[1] / "server.json").read_text(encoding="utf-8"))
    args = server["packages"][0]["packageArguments"]
    assert args == [{"type": "positional", "value": "mcp"}]


def test_cli_missing_cover(tmp_path, capsys):
    ms = tmp_path / "ms"
    make_manuscript(ms)
    code = main(["build", str(ms), "--cover", str(tmp_path / "nope.png"), "--out", str(tmp_path / "o")])
    assert code == 1
    assert json.loads(capsys.readouterr().err)["ok"] is False
