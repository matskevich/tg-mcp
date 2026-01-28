import pkgutil
import sys
from pathlib import Path


def test_tganalytics_does_not_import_external_projects():
    """Ensure tganalytics package doesn't pull in external project modules"""
    # make sure tganalytics is importable
    sys.path.append(str(Path(__file__).resolve().parents[2] / "tganalytics"))

    before = set(sys.modules.keys())
    import tganalytics  # noqa: F401
    after = set(sys.modules.keys())

    # modules loaded as a result of importing tganalytics
    newly_loaded = after - before
    offenders = [
        m
        for m in newly_loaded
        if m.startswith(("apps.", "gconf.", "vahue."))
    ]
    assert offenders == [], f"tganalytics import must not pull external modules: {offenders}"


def test_no_sys_path_append_in_library_code():
    """Ensure no sys.path hacks in library code (allowed in tests and scripts)"""
    repo = Path(__file__).resolve().parents[2]
    offenders = []
    for path in repo.rglob("*.py"):
        # skip tests, scripts, venv, and site-packages
        rel = path.relative_to(repo)
        rel_str = str(rel)
        if rel_str.startswith(("tests/", "scripts/", "venv/")) or "site-packages" in rel_str:
            continue
        text = path.read_text(encoding="utf-8")
        if "sys.path.append(" in text:
            offenders.append(rel_str)
    assert offenders == [], f"sys.path hacks forbidden in library code: {offenders}"
