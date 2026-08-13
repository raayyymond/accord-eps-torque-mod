---
name: reference_accord_c64de_is_a_byte_oscillator_halfperiod
description: 0xC64DE -- the kit's longest-carried unmeasured cell (non-stock on all 89 images since V18) -- is a BYTE, not the halfword 25617/25627 the ledger records; and it is the half-period of a relaxation oscillator that sign-flips gp-0x6b2c, not the one-shot "re-engage ramp ceiling" the record describes. 17->27 moves it from 29.4 Hz to 18.5 Hz at 1 kHz. Probably dead (gated on gp-0x6809, zero writers) BUT 8 of its 16 read sites are in a region Ghidra never analyzed, so the null is a tool zero.
metadata:
  type: reference
---

# `0xC64DE` — a BYTE, and a relaxation oscillator — 2026-08-12, `fw-levers` task

## It is a BYTE. "25617 → 25627" is a type error. [EVIDENCE, three methods]

Stock `0xC64DE..DF` = `11 64`; V96 = `1B 64`. **Only the low byte moved: `0x11`=17 → `0x1B`=27.** The
high byte `0x64`=100 never moved and is a **separate cal**.
- Ghidra decompile of `FUN_00028ea6` renders it verbatim as **`*(byte *)(unaff_tp + 0x74de)`**, and loads
  `tp+0x74df` independently elsewhere ⇒ two distinct byte cals.
- Raw LE scan: **16** `ld.bu` sites → `0xC64DE`; **2** → `0xC64DF`. This is the documented **`ld.bu`
  parity trap**: `hw2 = 0x74df` in *both* cases, and the real displacement bit 0 lives in **hw1 bit 5**
  (opfield `0x3C` → `0xC64DE`, `0x3D` → `0xC64DF`). A scan keying on hw2 alone **merges the two cells**.
- `build_v18_tva.py` already annotated "(byte)". The halfword framing entered later via
  `ledger_v94_cells.py`'s `MATRIX_SCALARS` entry `(0xC64DE, 2, False, …)` — wrong width.

⇒ **Any doc, ledger row or handoff quoting `0xC64DE = 25617/25627` is reading two unrelated byte cals as
one halfword.** `docs/STATE.md`, `docs/HANDOFF-2026-08-12-*` and `ledger_v94_cells.py` all carry this.

## What it actually is: a relaxation oscillator's HALF-PERIOD [EVIDENCE, decompile]

`memory/reference_accord_eme_lever_semantics.md` calls it "the count ceiling of the re-engage/debounce SM
… increments by 1/cycle until it hits the ceiling". The increment half is right. **The record misses what
happens AT the ceiling** — `FUN_00028ea6` (`m_steer_torque_arbitration`), decompile lines 676-693:

```c
bVar6  = *(byte  *)(tp + 0x74de);                 // N = 17 stock / 27 every build since V18
bVar22 = *(byte  *)(gp - 0x6756);                 // counter
if (bVar22 < bVar6) {
    *(byte  *)(gp - 0x6756) = bVar22 + 1;
    iVar28  =  (int)*(short *)(gp - 0x6b2c);      // output = +A
} else {
    cVar29 = 1;
    if (*(ushort *)(tp + 0x728a) <= (ushort)(*(byte *)(tp+0x74de) + sVar27))
        cVar29 = (char)((uint)*(byte *)(tp + 0x74de) >> 1) + 1;   // re-arm at (N>>1)+1
    *(byte  *)(gp - 0x3d36) = 2;                  // state 1 -> 2
    *(char  *)(gp - 0x6756) = cVar29;             // counter RE-ARMS, does not latch
    iVar28  = (int)-*(short *)(gp - 0x6b2c);      // output = -A
    *(short *)(gp - 0x6b2c) = -*(short *)(gp - 0x6b2c);   // AMPLITUDE NEGATED
}
```

`gp-0x6b2c` is **sign-flipped** each time the counter reaches `N`, and the counter **re-arms** rather than
latching ⇒ a **square-wave dither / relaxation oscillator**, not a one-shot ramp. `N` is the **half-period
in ticks**. At 1 kHz (per [[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]],
which corrects the constellation's "4-of-16 phase gate"):

| | N | frequency |
|---|---|---|
| stock | 17 | **29.4 Hz** |
| every build since V18 | 27 | **18.5 Hz** |

`tp+0x728a` = `0xC628A` is a total-duration limit selecting between re-arm values 1 and `(N>>1)+1`.

## Liveness: BELIEF dead, but the null is a TOOL ZERO

The branch sits under `if (*(char *)(gp - 0x6809) == 1)`, and
`memory/eps-deliver-cut-gp6809-broken.md` establishes `gp-0x6809` has **zero writers — dead code** —
explicitly calling it "a dead gate protecting a permanently-zero term (`gp-0x6b2c`)". If so the oscillator
never runs, which would *explain* 89 images of no measurable effect.

🛑 **BUT 8 of the 16 read sites — `0x2B0AA, 0x2B17E, 0x2B192, 0x2B1A4, 0x2B1C4, 0x2B1D6, 0x2B1DE,
0x2B2BE` — lie OUTSIDE `FUN_00028ea6`** (body `0x28EA6`–`0x2A30D`). `get_function_by_address(0x2B0AA)`
returns **"No function found"** — Ghidra has never analyzed `0x2A30D`–`0x2B2BE`, so `search_instructions`
is structurally blind there and every prior census reporting "read 8×" counted only the arbitration copy.
It **is** code: `read_memory(0x2B0AA)` = `85 7f df 74` = `ld.bu 0x74de[tp], r15` inside a dense
instruction stream. **Unadjudicated by any session.** Next step: run Ghidra analysis over that region,
then decompile. Until then "`0xC64DE` is dead" is a tool zero, not a verified zero.

## Related
[[reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12]] — the same `ld.bu` parity trap,
second independent occurrence; here it merges `0xC64DE` with `0xC64DF`.
[[reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation]] — same session.
