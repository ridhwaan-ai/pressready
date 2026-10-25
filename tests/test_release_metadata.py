import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_server_json_matches_pyproject():
    proj = _pyproject()["project"]
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert server["version"] == proj["version"]
    pkg = server["packages"][0]
    assert pkg["identifier"] == proj["name"]
    assert pkg["version"] == proj["version"]
    assert len(server["description"]) <= 100


def test_readme_has_mcp_name_line():
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"mcp-name: {server['name']}" in readme


def test_fonts_are_packaged():
    data = _pyproject()["tool"]["setuptools"]["package-data"]["pressready"]
    assert any(p.startswith("fonts/") and p.endswith(".ttf") for p in data)
    fonts = list((ROOT / "src" / "pressready" / "fonts").glob("*.ttf"))
    assert len(fonts) >= 4
    assert (ROOT / "LICENSE").exists()


def test_console_scripts_declared():
    scripts = _pyproject()["project"]["scripts"]
    assert "pressready" in scripts and "pressready-mcp" in scripts
