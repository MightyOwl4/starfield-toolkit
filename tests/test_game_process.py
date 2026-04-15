import subprocess
from types import SimpleNamespace

from starfield_tool import game_process


def _fake_run(stdouts_by_image):
    """Return a fake subprocess.run that dispatches by IMAGENAME filter."""
    def _run(cmd, capture_output, text, timeout):
        # cmd: ["tasklist", "/FI", f"IMAGENAME eq X", "/NH"]
        image = cmd[2].split("IMAGENAME eq ", 1)[1]
        stdout = stdouts_by_image.get(image, "")
        return SimpleNamespace(stdout=stdout, returncode=0)
    return _run


def test_all_absent_returns_false(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run({}))
    assert game_process.is_starfield_running() is False
    assert game_process.is_launcher_running() is False
    assert game_process.is_starfield_or_launcher_running() is False


def test_starfield_running(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run({
        "Starfield.exe": "Starfield.exe 1234 Console 1 100,000 K",
    }))
    assert game_process.is_starfield_running() is True
    assert game_process.is_launcher_running() is False
    assert game_process.is_starfield_or_launcher_running() is True


def test_launcher_running_without_game(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run({
        "BethesdaNetLauncher.exe": "BethesdaNetLauncher.exe 5678 Console 1 50,000 K",
    }))
    assert game_process.is_starfield_running() is False
    assert game_process.is_launcher_running() is True
    assert game_process.is_starfield_or_launcher_running() is True


def test_timeout_returns_false(monkeypatch):
    def _raise(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd="tasklist", timeout=5)
    monkeypatch.setattr(subprocess, "run", _raise)
    assert game_process.is_starfield_running() is False
    assert game_process.is_launcher_running() is False
    assert game_process.is_starfield_or_launcher_running() is False
