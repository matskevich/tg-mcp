#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_FILE = ROOT / "packages" / "tg_core" / "tg_core" / "__init__.py"
PYP_FILE = ROOT / "packages" / "tg_core" / "pyproject.toml"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(s: str):
    m = SEMVER_RE.match(s.strip())
    if not m:
        raise SystemExit(f"Invalid version format: {s}")
    return tuple(int(x) for x in m.groups())


def bump(v: str, kind: str) -> str:
    major, minor, patch = parse_version(v)
    if kind == "patch":
        patch += 1
    elif kind == "minor":
        minor += 1
        patch = 0
    elif kind == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise SystemExit("Usage: bump_version.py [patch|minor|major]")
    return f"{major}.{minor}.{patch}"


def read_init_version() -> str:
    text = INIT_FILE.read_text(encoding="utf-8")
    m = re.search(r"__version__\s*=\s*\"(.*?)\"", text)
    if not m:
        raise SystemExit("__version__ not found in __init__.py")
    return m.group(1)


def write_init_version(new: str):
    text = INIT_FILE.read_text(encoding="utf-8")
    text = re.sub(r"__version__\s*=\s*\".*?\"", f"__version__ = \"{new}\"", text)
    INIT_FILE.write_text(text, encoding="utf-8")


def write_pyproject_version(new: str):
    text = PYP_FILE.read_text(encoding="utf-8")
    text = re.sub(r"^version\s*=\s*\".*?\"$", f"version = \"{new}\"", text, flags=re.MULTILINE)
    PYP_FILE.write_text(text, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/bump_version.py [patch|minor|major]")
    kind = sys.argv[1]
    current = read_init_version()
    new = bump(current, kind)
    write_init_version(new)
    write_pyproject_version(new)
    print(f"Bumped tg_core version: {current} -> {new}")


if __name__ == "__main__":
    main()
