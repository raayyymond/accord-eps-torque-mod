---
name: reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans
description: V850E2 `prepare` (function prologue) matches the Format-V jr/jarl opcode test ((hw1>>6)&0x1f)==0x1E, so a hand-rolled branch scanner reports FALSE branch targets out of every function prologue. The discriminator is target parity - a real jr/jarl target is halfword-aligned, and every prepare false positive produced an ODD target. This is the mirror of the documented jarl-opcode false-NEGATIVE trap. Found 2026-09-06 while proving the 0x2A508 duplicate block unreachable.
metadata:
  type: reference
---

# `prepare` collides with `jr`/`jarl` in a Format-V branch scan — a FALSE-POSITIVE trap

Found 2026-09-06 on the V282 image, during the GATE-1 reachability proof for the LKAS lag poles.

## The trap

A Format-V `jr`/`jarl disp22` is identified by `((hw1 >> 6) & 0x1f) == 0x1E`. **V850E2 `prepare`
matches that same test.** So a hand-rolled scanner emits a bogus branch out of **every function
prologue in the image**, with a garbage target computed from the register-list bitmap.

Concretely, the four that nearly broke a reachability verdict:

| site | my scanner said | Ghidra says |
|---|---|---|
| `0x22CA0` | `jr 0x2AC41` | `prepare { r20,r21,r22,r23,r25,r26,r27,r28,lp }, 0x0` — this is the **entry of FUN_00022ca0, the 100 Hz task** |
| `0x1B36A` | `jarl 0x2B3E9` | `prepare { r22,lp }, 0x4` (at 0x1B36E) |
| `0x20462` | `jr 0x2AC83` | `prepare` |
| `0x20F0A` | `jr 0x2B4AB` | `prepare` |

**All three of the apparent "entries into the unreachable duplicate block" were prologues.** Taken at
face value they would have flipped a GATE-1 verdict from PASS to FAIL and blocked a legitimate cal edit.

## 🛑 The discriminator: TARGET PARITY

**A real `jr`/`jarl` target is halfword-aligned, so the computed target must be EVEN.** Every `prepare`
false positive above produced an **ODD** target (0x2AC41, 0x2B3E9, 0x2AC83, 0x2B4AB) — structurally
impossible on V850, where all instructions are halfword-aligned.

```python
if ((hw1 >> 6) & 0x1f) == 0x1E:
    disp = sx(((hw1 & 0x3f) << 16) | hw2, 22)
    tgt  = a + disp
    if tgt & 1:            # <-- prepare (or data), NOT a branch
        continue
```
(Equivalently: `hw2 & 1` was set in all four. Parity of the target is the safer test to state, since it
is a property of the architecture rather than of `prepare`'s bitmap encoding.)

## ⊕ It is the MIRROR of the documented trap

The kit already records that using opcode field `0x1B` instead of `0x1E` for `jarl` gives **false
NEGATIVES** — 4,448 matches resolving zero real calls, a confident empty answer. This one is the
opposite failure of the same decoder: the correct field, but an **over-match producing false
POSITIVES**. Both are caught by the same discipline, and only by it:

> **Control the scanner on known cases, then adjudicate EVERY hit with a stated reason.**

In this instance 7/7 positive controls passed (`0x22522->0x28EA6`, `0x22530->0x2B422`,
`0x22572->0x2B57A`, `0x23276->0x34350`, `0x2291E->0x3AA2C` jarl; `0x2A1B4->0x2A1E6` Bcond;
`0x28F3C->0x290B0` jr) — **the controls passing did NOT protect against the over-match.** Controls
prove a scanner does not MISS; they say nothing about whether it INVENTS. Only per-hit adjudication
catches that half.

## Working Format III / Format V decoder (controlled, this image)

```python
# Format III, 2-byte conditional / br
if (hw1 & 0x0780) == 0x0580:
    disp = sx((((hw1 >> 11) & 0x1f) << 4) | (((hw1 >> 4) & 0x7) << 1), 9)
    cond = hw1 & 0xf            # 0x5 == br (always)
# Format V, 4-byte jr / jarl disp22   -- MUST filter on target parity, see above
if ((hw1 >> 6) & 0x1f) == 0x1E:
    disp = sx(((hw1 & 0x3f) << 16) | hw2, 22)
    reg2 = (hw1 >> 11) & 0x1f   # 0 => jr, else jarl
```
45,821 branches decoded image-wide with this.

## Related
[[reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader]] — the verdict this protected.
[[reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return]] — the GATE-1 result itself.
