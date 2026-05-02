# Project Rules

- All code, identifiers, comments, commit messages, documentation, and user-facing strings in the repository must be written in English.
- After every project change, update `docs/` and `README.md` when the behavior, setup, deployment, or public API changes.
- After every completed change, create a git commit.
- Keep the legacy project snapshot in `old/`; it is intentionally ignored by git.
- Prefer Docker for server-side runtime changes. The home server runs other services, so do not install host-level services or change existing tunnel routing without explicit confirmation.
- Treat memory as scarce on the home server. Prefer small containers, bounded queues, and conservative defaults. Ask before choosing a higher-memory option.

