---
name: bambu-pause-check
description: Audit the manual pause heights or layers in a sliced Bambu Studio project before a print that requires embedded inserts. Report extra, missing or unverified stops for a specific plate.
---

Ask for the intended plate number and the full list of expected heights or one-based layer numbers, including explicit confirmation if zero pauses are intended. Use the final sliced archive or its text G-code. Run `python scripts/check_pauses.py FILE --plate N --height MM` from this skill directory. Repeat the height flag for multiple stops, use repeated `--layer` instead for layer numbers, or use `--expect-none`.

Report matched, missing and unexpected locations with G-code lines. Treat custom or conditional pause behavior as inconclusive. For one missing and one unexpected event, give their signed height or layer difference. Keep the source untouched. See [the tutorial](TUTORIAL.md) for supported Bambu markers and file selection.
