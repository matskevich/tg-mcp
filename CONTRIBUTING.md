# Contributing

Thanks for contributing to `tg-mcp`.

## Project Model

- License: MIT (`LICENSE`)
- Development model: open source
- Governance rule: commits to `main` are maintainer-only

External contributions are welcome through Issues and Pull Requests.

## How to Contribute

1. Open an issue describing bug, risk, or feature proposal.
2. Fork the repository and create a focused branch.
3. Add tests/docs for behavior changes.
4. Run local checks:
   - `make test`
   - `make anti-spam-check`
   - `make security-check`
5. Open a pull request with a clear summary and risk notes.

## Safety Requirements

- Keep Telegram write operations ActionMCP-only (`tgmcp-actions`).
- Do not bypass write guard with direct Telethon write calls.
- Preserve safe defaults for allowlist, confirmation, approval code, and idempotency.

For operational details, see:

- `docs/AGENT_PLAYBOOK.md`
- `docs/ACTION_POLICY_TOGGLES.md`
- `docs/ANTISPAM_SECURITY.md`
