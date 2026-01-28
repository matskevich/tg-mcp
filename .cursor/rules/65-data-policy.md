# scope: project

## data policy (per-project folders)

- code vs data
  - code in `packages/tg_core`, `gconf/`, `vahue/`, and `apps/*` must not contain real pii or working exports.
  - `tg_core` never reads from `data/*`; only from its own public api.
  - app logic and sample configs live under each project folder (`gconf/app/*`, `vahue/app/*`, ...).

- storage locations
  - `gconf/data/` (local, .gitignored): runtime artifacts and private lists
    - `blacklist_ids.txt` — one numeric telegram user id per line
    - `blacklist_handles.txt` — one handle per line; `@` optional
    - other working csv/json exports used only locally
  - `gconf/export/` (outputs): analytics reports; avoid pii where possible
  - `gconf/app/` (repo): code, loaders, and samples
    - `blacklist.sample.txt` or `blacklist.sample.yaml` — public, non-sensitive examples
    - loader precedence: first `gconf/data/*`, then samples under `gconf/app/*`
  - `vahue/data/` (local, .gitignored): runtime artifacts and private lists
  - `vahue/export/` (outputs): analytics reports; avoid pii where possible
  - `vahue/app/` (repo): code, loaders, and samples

- agent rules
  - never commit files from `gconf/data/` or real exports with pii [[ref: privacy]]
  - write analytics outputs to `gconf/export/` by default (or `<project>/export/`)
  - when a blacklist is needed, read `gconf/data/*` if present; otherwise fall back to samples in `gconf/app/*`
  - do not wire `tg_core` to any `data/*` paths

- references
  - see `60-arch-current.md` (data locations) and `70-telegram-invariants.md` (pii handling)

## blacklist model (gconf)
- global: `gconf/data/blacklist.global.csv` — columns: `id,reason,policy`; use `policy=exclude_all` to fully exclude id from all metrics
- per event: `gconf/data/blacklist.per_event.csv` — columns: `id,event_key,policy,reason`
  - event_key: raw gid like `-1002621978258` or label like `gconf #7` (see `gconf/data/events_keymap.json`)
  - policies: `invited_free`, `volunteer`, `protagonist`, `exclude_all`
  - precedence: per-event overrides global (most restrictive wins)
- application:
  - per-event policies `invited_free/volunteer/protagonist` — исключать из всех метрик по соответствующему ивенту
  - global `exclude_all` — исключать из всех метрик везде
