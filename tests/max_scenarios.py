"""Compatibility entry point for the MAX browser checks."""
exec(compile((ROOT / "tests/max_share_scenarios.py").read_text(encoding="utf-8"), "max_share_scenarios.py", "exec"))
