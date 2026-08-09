---
name: reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram
description: "Invert the cave-RAM search: a cell with ONE dedicated gp-relative writer and ZERO readers is stronger evidence of ownership than virgin RAM, because a dedicated `st.w disp16[gp]` PROVES named-scalar allocation (which a buffer slot can never show) and 0 readers closes the V48B failure direction by construction. Five contiguous 32-bit such cells live in FUN_0003b66a. Also: 'dead feature' does NOT mean free RAM here."
metadata:
  type: reference
---

# The best cave RAM in this firmware is WRITE-ONLY, not virgin (2026-08-09, GATE-1 survey)

## The inversion

The kit has always hunted RAM that *nothing* touches. That is the **weakest** evidence available, because
"no displacement hit" is exactly what a pointer-walked buffer looks like — gp-0x1500 is the proof, and
[[reference_accord_gate1_gp683c_ram_ownership_audit]] already recorded the inverted heuristic (a long free
run is a RED flag).

**Better class: exactly one known writer, zero readers.**
- A dedicated `st.w -0xNNNN[gp]` is **POSITIVE evidence that the compiler allocated a named scalar
  object** at that address. A registry-listed buffer slot can never show that — it has no dedicated
  gp-relative access at all. This is the discriminator gp-0x1500 lacked.
- **0 readers closes the V48B failure DIRECTION by construction** (cave writes → firmware reads →
  firmware misbehaves). The residual runs the other way — firmware writes → our state glitches — which
  degrades only our own filter. Same asymmetry argument the gp-0x683c audit made, but for a whole class.
- It also proves the address is **real, writable RAM** (the firmware writes it 1000×/s) — not a hole in
  the address map, not read-only, not a peripheral window.
- Cost to own: neutralise the single writer. One **4-byte in-place** edit (`st.w` → two 2-byte `nop`s, or
  repoint the displacement). Same class as V62/V67 — the class that has never bricked this ECU. It
  *removes* an instruction, so there is no cycle cost.

Image-wide census (stock, contamination-filtered): **771 cells** in class W1R0 (≥1 writer, 0 readers).

## ★ The recommended set — five 32-bit cells, all in FUN_0003b66a (0x3b66a-0x3b8f5, 1 kHz, Path 2)

| cell | abs | writer | readers | section / boot init |
|---|---|---|---|---|
| gp-0x6d08 | 0xFEDF12F8 | `st.w r11,-0x6d08[gp]` @0x3b768 | 0 | .data / 00000000 |
| gp-0x6d04 | 0xFEDF12FC | `st.w r13,-0x6d04[gp]` @0x3b730 | 0 | .data / 00000000 |
| gp-0x6d00 | 0xFEDF1300 | `st.w r11,-0x6d00[gp]` @0x3b7de | 0 | .data / 00000000 |
| gp-0x6de8 | 0xFEDF1218 | `st.w r28,-0x6de8[gp]` @0x3b866 | 0 | .data / 00000000 |
| gp-0x6de4 | 0xFEDF121C | `st.w r14,-0x6de4[gp]` @0x3b846 | 0 | .data / 00000000 |

`0xFEDF12F8..0xFEDF1303` (3 cells) and `0xFEDF1218..0xFEDF121F` (2 cells) are **contiguous and exactly
tiled** by dedicated `st.w`s — no gaps, no overlaps, no reads. That tiling *is* the evidence: it is what a
run of named 32-bit scalar globals looks like and is not what a buffer looks like.
Write-only confirmed by reading the decompile, e.g. `*(int *)(unaff_gp + -0x6de8) = (int)(fVar6 * 1024.0);`.
All clear on: register-indirect reach, `movea`-gp base, LE32 registry literal (±64 B), stack reach
(+6 KB above `sp`), and the array-shadow test. **Identical on stock and V86B.**
Not lockstep partners — FUN_0003b66a's own lockstep pairs are gp-0x6ba6↔gp-0x4ce8 and gp-0x6b9a↔gp-0x4ce4.

**16-bit siblings, same class** (prefer 32-bit for an 8 Hz biquad at 1 kHz — pole radius ~0.95, and V50's
−7-count floor-bias ratchet was exactly this quantisation failure): `gp-0x6c00` @0x3bc16, `gp-0x6bf6`
(2 writers @0x3bac0/0x3bc0e), `gp-0x6ae0` @0x3bc00, `gp-0x6ae2` @0x3bc04, `gp-0x695c` @0x3bc42 — all
corroborating [[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] §9. Ghidra
`search_instructions` independently returns exactly 1 hit for gp-0x6ae0 and gp-0x6ae2.

## 🛑 Do NOT use

- **gp-0x1300** — V51P flight-clean but structurally bad; see
  [[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]] §2. Use **gp-0x1100** instead.
- **gp-0x6bce / gp-0x6bbc** ("dead lanes", 0 writers). Their single reader IS a live summand in
  `FUN_00037fe6`, and the gate is a **MULTIPLIER** whose cal byte is **1, not 0**, on stock AND V86B
  (`0xC64AD`=1, `0xC64AF`=1, bytes read directly). Writing state there injects it into
  gp-0x6ad6 → PID bias → aggregator → motor. Usable only if the gate byte is also zeroed, and whether
  those cals are shared was NOT checked. ⚠ This CORRECTS the natural reading of
  [[reference_accord_fun38148_fun37fe6_channel_census_and_dead_lanes]] — "0 writers" made them look free;
  they are not. gp-0x6bbc additionally has a `movea` struct base 8 bytes below at `0xFEDF143C`.
- **gp-0x363c / gp-0x3638** (the dead FIR's x[n-1]/x[n-2]) — a trap. They are **floats** read by `ld.w`
  and multiplied by 0.0f coefficients. `0.0f × NaN = NaN` ⇒ an arbitrary 32-bit state pattern very likely
  propagates **NaN into Path 2's output**, and the V850E2 FPU may trap. They are also written every tick.

## 🛑 "Dead feature" does NOT mean free RAM in this firmware — negative result

Both named dead features are dead **by coefficient, not by execution**:
- `0xC6194`'s LKAS rate limiter — dead by output ×0.
- `FUN_0003b8f6`'s 3-tap FIR — dead by `(c1,c2,c0)=(1.0,0.0,0.0)` on every build.
Their code still runs and still writes their state cells every tick ⇒ **no persistent RAM there.** Dead
means "harmless if corrupted", which is not what a filter needs. The useful sense of dead is
**"nothing consumes it"** — i.e. the write-only taps above.

## Geometry worth remembering
gp disp16 reach = `0xFEDF0000..0xFEDFFFFF`; app RAM = `0xFEDEC000..0xFEDFFFFF`; the 16 KB disp16 cannot
reach is exactly the stack. ⇒ **every byte of non-stack RAM is disp16-reachable; a cave never needs
disp23 for state.** [BELIEF, not datasheet-confirmed] that 80 KB is the whole physical RAM, so there is no
virgin pool outside the app's window to inherit.

Related: [[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]] ·
[[reference_accord_gate1_gp683c_ram_ownership_audit]] ·
[[reference_accord_app_ram_layout_and_boot_init_loops]]
