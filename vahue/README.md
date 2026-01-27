# vahue (analytics workspace)

this top-level `vahue/` directory contains **no code**. it’s a workspace for:
- analytics artifacts (exports, joins, segment tables)
- campaign folders (notes, worklogs)
- small reference files (lists of ids, mappings, assumptions)
- positioning docs (one-pagers, copy drafts)

## repo rule of thumb
- **shared code only** lives in `src/` and `packages/` and is reused across all projects.
- project workspaces like `vahue/` (and `vahue/satia/`) are **data + notes**, not executable logic.

## campaigns
- `vahue/satia/` — satia campaign workspace (exports + notes). raw/processed exports are intentionally git-ignored inside that folder.


