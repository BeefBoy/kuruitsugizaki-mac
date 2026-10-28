Read `docs/INDEX.md` first. It is the only index.

Never edit an `.flp` in place. Build with the writer, read back with `project_read`. The byte-identical round trip
(`docs/ARCHITECTURE.md`) is the invariant; `scripts/selftest.py` checks it.
