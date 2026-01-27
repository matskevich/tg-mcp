import csv
import json
from pathlib import Path
from typing import Dict, Optional, Set, Tuple


class Blacklist:
    def __init__(self, base_dir: Optional[str] = None):
        gconf_root = Path(__file__).resolve().parents[2]
        self.base = Path(base_dir) if base_dir else (gconf_root / "data")
        self.global_path = self.base / "blacklist.global.csv"
        self.per_event_path = self.base / "blacklist.per_event.csv"
        self.keymap_path = self.base / "events_keymap.json"
        self.exclude_all_ids: Set[int] = set()
        self.per_event: Dict[Tuple[int, str], str] = {}
        self.event_keys_by_id: Dict[str, str] = {}
        self._load()

    def _load(self):
        if self.keymap_path.exists():
            self.event_keys_by_id = json.loads(self.keymap_path.read_text(encoding="utf-8"))
        # global
        if self.global_path.exists():
            with self.global_path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    s = (row.get("id") or "").strip()
                    pol = (row.get("policy") or "").strip().lower()
                    if s.isdigit() and pol == "exclude_all":
                        self.exclude_all_ids.add(int(s))
        # per-event
        if self.per_event_path.exists():
            with self.per_event_path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    sid = (row.get("id") or "").strip()
                    ev = (row.get("event_key") or "").strip()
                    pol = (row.get("policy") or "").strip().lower()
                    if sid.isdigit() and ev and pol:
                        self.per_event[(int(sid), ev)] = pol

    def _event_variants(self, event_key: str):
        # allow both raw id and label
        return {event_key, self.event_keys_by_id.get(event_key, "")}

    def apply_attendance(self, user_id: int, event_key: str) -> bool:
        if user_id in self.exclude_all_ids:
            return False
        # per-event override: exclude_all wins
        for ek in self._event_variants(event_key):
            pol = self.per_event.get((user_id, ek))
            # политика: все "бесплатные/ролевые" статусы исключаются из любых метрик по ивенту
            if pol in {"exclude_all", "invited_free", "volunteer", "protagonist"}:
                return False
        return True

    def exclude_from_paid(self, user_id: int, event_key: str) -> bool:
        if user_id in self.exclude_all_ids:
            return True
        for ek in self._event_variants(event_key):
            pol = self.per_event.get((user_id, ek))
            if pol in {"exclude_all", "invited_free", "volunteer", "protagonist", "exclude_conversion_only"}:
                return True
        return False


