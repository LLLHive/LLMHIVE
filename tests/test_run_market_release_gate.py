from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import run_market_release_gate as gate


def test_gate_defaults_to_static_checks_only(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_market_release_gate.py"])

    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0, "ok"

    monkeypatch.setattr(gate, "_run", fake_run)
    rc = gate.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert ["pytest", *gate.FOCUSED_TESTS, "-q"] in calls
    assert ["python", "scripts/verify_market_release_isolation.py"] in calls
    assert ["python", "scripts/verify_minimal_launch_release.py", "--json"] not in calls
    assert "MARKET RELEASE GATE" in out


def test_gate_includes_live_verifier_when_requested(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_market_release_gate.py", "--include-live", "--json"])

    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0, '{"passed": true}'

    monkeypatch.setattr(gate, "_run", fake_run)
    rc = gate.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert ["python", "scripts/verify_minimal_launch_release.py", "--json"] in calls
    assert '"passed": true' in out
