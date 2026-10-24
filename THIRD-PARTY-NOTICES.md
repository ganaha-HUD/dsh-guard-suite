# Third-party notices

This package VENDORS the following third-party code. It is not a dependency
that is installed at runtime — the source is copied into `vendor/` and executed
from there.

## dsh-guard-repeat-output 2.1.7

- Copyright (c) 2026 mcd0luo
- License: MIT (full text in [`vendor/repeat/LICENSE`](./vendor/repeat/LICENSE))
- Upstream: https://github.com/Mcd0LUO/dsh-guard-repeat-output
- Location in this package: `vendor/repeat/`
- **Modified.** Four audit patches were applied. Each patch site is marked with a
  `PATCH #n (guard-suite)` comment in `vendor/repeat/index.js`. The unmodified
  upstream file is kept alongside it as `vendor/repeat/index.js.orig` so the
  diff is auditable without network access.
- See [`PATCHES.md`](./PATCHES.md) for what each patch fixes and why.

The MIT license permits redistribution and modification provided the copyright
notice and permission notice are retained. Both are retained: the upstream
LICENSE ships unmodified in `vendor/repeat/LICENSE`.

## dsh-guard-collapse 0.1.0

First-party code, same MIT license as this repository.