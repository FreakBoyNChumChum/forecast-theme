"""potree: the shared bridge/launch logic every app in the family used to duplicate by hand.

Headless like the rest of the suite -- no Qt, no real PotreeDesktop install needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forecast_theme import potree


def test_find_cloud_file_none_when_absent(tmp_path):
    assert potree.find_cloud_file(tmp_path) is None


@pytest.mark.parametrize("marker", potree.CLOUD_MARKERS)
def test_find_cloud_file_finds_marker(tmp_path, marker):
    nested = tmp_path / "run_potree"
    nested.mkdir()
    cloud_file = nested / marker
    cloud_file.write_text("{}")
    assert potree.find_cloud_file(tmp_path) == cloud_file


def test_setup_potree_bridge_false_without_index_html(tmp_path):
    assert potree.setup_potree_bridge(str(tmp_path), tmp_path / "cloud.js") is False


def test_setup_potree_bridge_injects_script_tag_once(tmp_path):
    index = tmp_path / "index.html"
    index.write_text("<html><body></body></html>", encoding="utf-8")
    cloud_file = tmp_path / "run_potree" / "cloud.js"

    assert potree.setup_potree_bridge(str(tmp_path), cloud_file) is True
    content = index.read_text(encoding="utf-8")
    assert content.count('<script src="autoload.js"></script>') == 1

    # A second run must not duplicate the tag.
    assert potree.setup_potree_bridge(str(tmp_path), cloud_file) is True
    assert index.read_text(encoding="utf-8").count('<script src="autoload.js"></script>') == 1


def test_setup_potree_bridge_writes_autoload_js_pointing_at_the_cloud(tmp_path):
    index = tmp_path / "index.html"
    index.write_text("<html><body></body></html>", encoding="utf-8")
    cloud_file = tmp_path / "run_potree" / "cloud.js"

    potree.setup_potree_bridge(str(tmp_path), cloud_file)
    autoload = (tmp_path / "autoload.js").read_text(encoding="utf-8")
    assert cloud_file.as_posix() in autoload


def test_launch_potree_raises_without_any_known_exe(tmp_path):
    with pytest.raises(FileNotFoundError):
        potree.launch_potree(str(tmp_path))


def test_launch_potree_prefers_the_desktop_exe(tmp_path, monkeypatch):
    exe = tmp_path / "PotreeDesktop.exe"
    exe.write_text("")

    calls = []
    monkeypatch.setattr(potree.subprocess, "Popen", lambda cmd, cwd: calls.append((cmd, cwd)))

    potree.launch_potree(str(tmp_path))
    assert calls == [([str(exe)], str(tmp_path))]


def test_launch_potree_falls_back_to_electron(tmp_path, monkeypatch):
    electron = tmp_path / "node_modules" / "electron" / "dist" / "electron.exe"
    electron.parent.mkdir(parents=True)
    electron.write_text("")

    calls = []
    monkeypatch.setattr(potree.subprocess, "Popen", lambda cmd, cwd: calls.append((cmd, cwd)))

    potree.launch_potree(str(tmp_path))
    assert calls == [([str(electron), str(tmp_path / "main.js")], str(tmp_path))]
