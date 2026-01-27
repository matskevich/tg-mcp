# apps/vahue (placeholder)

this folder exists in the tree, but **vahue is not expected to have project-specific code**.

## rule
- do **not** add product logic here.
- keep reusable telegram/analytics code in `src/` and `packages/` so it can be shared across projects.

if we ever need a runnable entrypoint for a vahue workflow, we can add a thin wrapper here that calls shared code — but the logic stays shared.


