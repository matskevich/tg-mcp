import pkgutil
import sys
from pathlib import Path


def test_tg_core_does_not_import_apps():
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
    assert offenders == [], f"tganalytics import must not pull project modules: {offenders}"


def test_project_code_has_no_direct_telethon_imports():
    repo = Path(__file__).resolve().parents[2]
    project_dirs = [repo / "apps", repo / "gconf", repo / "vahue"]
    offenders = []
    for base in project_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "import telethon" in text or "from telethon import" in text:
                offenders.append(str(path))
    assert offenders == [], f"project code must not import telethon directly: {offenders}"


def test_apps_do_not_import_each_other():
    apps_dir = Path(__file__).resolve().parents[2] / "apps"
    offenders = []
    for app_dir in [p for p in apps_dir.iterdir() if p.is_dir()]:
        app_name = app_dir.name
        for py in app_dir.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            # forbid imports like from apps.<other>.app ...
            if "from apps." in text and f"from apps.{app_name}." not in text:
                offenders.append(str(py))
    assert offenders == [], f"cross-app imports are forbidden: {offenders}"

def test_root_projects_do_not_import_each_other():
    repo = Path(__file__).resolve().parents[2]
    offenders = []

    checks = [
        ("gconf", {"apps.", "vahue."}),
        ("vahue", {"apps.", "gconf."}),
    ]

    for project_name, forbidden_prefixes in checks:
        base = repo / project_name
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for pref in forbidden_prefixes:
                if f"from {pref}" in text or f"import {pref}" in text:
                    offenders.append(str(py))
                    break

    assert offenders == [], f"cross-project imports are forbidden: {offenders}"


def test_no_sys_path_append_in_code():
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
    assert offenders == [], f"sys.path hacks forbidden in code: {offenders}"


