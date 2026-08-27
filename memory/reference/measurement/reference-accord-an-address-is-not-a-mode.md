---
name: reference-accord-an-address-is-not-a-mode
description: "NAMED TRAP, three instances in one session — a raw address standing in for a mode. Byte-verified friction-record mode map for 0xCBE74, and the rule: dereference 0xCBE74 + mode*4 and print the mode number beside every address in a spec. Y is at record base + 8, not base + 2."
metadata:
  type: reference
---

🛑 **NAMED TRAP, 2026-08-10 — AN ADDRESS IS NOT A MODE.** Three instances in a single session:
1. **V69 wrote another variant's rows** — `gain_B` at mode 10 on a car that runs 24/26 ⇒ byte-stock, and
   the r24 dose ladder derived from it **never existed** ([[reference-accord-car-is-tvca4-mode-24-26]]).
2. **An agent asserted "mode 24 is dosed" from a table that was showing stock** — it had matched the
   address, not the mode.
3. **The orchestrator named `0xD6A5C` as mode 24.** It is **mode 23** — another variant's engaged column.

## Byte-verified mode map — friction-comp LERP (`FUN_00036c12`, `gp-0x6b26`), pointer table `0xCBE74`

```
mode 10  record 0xD2A44  X 0xD2A46  Y 0xD2A4C   DISENGAGED (another variant)
mode 23  record 0xD6A54  X 0xD6A56  Y 0xD6A5C   another variant's ENGAGED column
mode 24  record 0xD6A64  X 0xD6A66  Y 0xD6A6C   ★ THIS CAR, MANUAL   — never dosed, ever
mode 25  record 0xD7A44  X 0xD7A46  Y 0xD7A4C   row-11 B branch
mode 26  record 0xD7A54  X 0xD7A56  Y 0xD7A5C   ★ THIS CAR, ENGAGED
mode 27  record 0xD7A64  X 0xD7A66  Y 0xD7A6C   row-11 B branch
```

```python
# [EVIDENCE] reproduced on the images, little-endian, V850 LE
PT = 0xCBE74
rec = int.from_bytes(img[PT + mode*4 : PT + mode*4 + 4], "little")
X   = rec + 2      # breakpoint array
Y   = rec + 8      # value array   <-- NOT rec + 2
```

## 🛑 Why `base + 8` is not a detail: writing Y at `base + 2` fails SILENTLY and PLAUSIBLY

The LERP compares the X breakpoints **UNSIGNED**. Y values are negative, so landing them in X poisons the
search rather than erroring:

```python
# a Y value of -29490 written into the X array:
(-29490) & 0xFFFF          # -> 36046, larger than any speed count the car ever produces
# => every speed falls below X[0]  => the LERP returns a FLAT Y[0] at ALL speeds
```

⇒ **a silent, plausible-looking ~5× increase at highway speed**, with a build that byte-verifies, CRCs
clean and drives. **Assert the X arrays unchanged in any builder that touches this row.**

## The rule

> **Dereference `0xCBE74 + mode*4` and print the mode number beside every address in a spec.**
> Never let a raw address stand in for a mode; never inherit a mode label from a previous spec, a
> remembered list, or a build script comment.

This car is **`TVCA4`, row 11** — manual **24/25**, engaged **26/27**. Engaged and disengaged column sets
are disjoint across all 16 rows, so a wrong mode is **not a weak lever, it is NO lever** — and it looks
flashed, verified and driven. See [[feedback-rule7-mode-proof-or-a-bet]],
[[accord-damper-is-mode-table-selected]], [[accord-mode-27-is-a-second-engaged-column]],
[[reference-accord-cbe74-friction-row-zero-clean-flights]], [[accord-lerp-tables-count-word-first]].
