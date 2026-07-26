---
name: reference-accord-gp4f60-carrier-surface
description: gp-0x4f60 has exactly 19 command-path carriers; V52C repoints ALL of them and passed every gate — the "broad and fragile, don't do it" verdict below is SUPERSEDED, and the 3 "self-filtering lanes" were mis-classified.
metadata:
  type: reference
---

> 🛑 **SUPERSEDED IN PART (2026-07-24, V52C).** The structural map below is sound and the 19-carrier
> count is CONFIRMED. **Three things in it are now WRONG — read this header before the body:**
>
> 1. **The strategic verdict ("broad and fragile ⇒ don't filter at the source") is REVERSED.** V52C
>    repoints ALL 19 carriers and passed every pre-flash gate. Filtering only *some* carriers is the
>    fragile option: a MIXED raw/filtered population is itself the hazard, because any
>    self-consistency / dual-path / lockstep check straddling the split sees a divergence that does
>    not exist today — **exactly how V27 bricked (ASYMMETRY, not magnitude).** GATE-2 agrees: margin
>    improves MONOTONICALLY with the filtered fraction, edge 4.66× (stock) → **21.19×** at 19/19.
> 2. **The "3 self-filtering lanes (cascade risk)" claim was WRONG ON ALL THREE** (measured vs V38):
>    - `0x36682` — TRUE, α=6/1024 → **fc 0.94 Hz** (−27 dB at 21 Hz; a real self-filter).
>    - `0x36846` — **NOT a filter at all.** Its `gp-0x6b44` write is a *cal-selected constant*; the
>      same load feeds a first-difference rate check raising DTC 0x23 (NOT hard-fault eligible).
>    - `0x3B908` — **nearly a PASSTHROUGH,** not "self-filters heavily": its float biquad stage is
>      DEGENERATE in stock cal (coeffs `0xC404C`/`0xC4050` = 0.0f), leaving poles at ~366 Hz.
>      ⚠ Its single `ld.h` is reused 4 instructions later by a `|x| ≤ 25600` validity gate.
>    ⚠ Cal provenance trap: those cals were first read from `code.bin` (**STOCK**, where `0xC646C`=891)
>    while the build is V38-based (`0xC646C`=3564, 4.00×). Re-read every cal against V38.
> 3. **"64 raw readers / 69 accesses" is an UNDERCOUNT.** That scan saw only the 4-byte disp16 form.
>    True total **76** (71 loads + 5 stores) including the 6-byte V850E2 extended-displacement form
>    (6 `ld.h` + 1 `ld.hu`, all diagnostic/CAN/self-test — **none a carrier**, so the 19-partition
>    holds). See [[accord-gp4f60-two-encodings-enumeration-trap]].
>
> Also confirmed since: the 2 "mode-gated" lanes are `gp-0x4e5f` (a shadowed sensor-fault flag, live
> in normal driving) and `0x3FCC6` (cal-DISABLED — `0xC64CF`=0x00). Both are repointed anyway, which
> is free: a dormant lane's repoint is a runtime no-op, and consistency is the governing criterion.
>
> Current build state: `docs/HANDOFF-2026-07-24-v52c-complete-broad-lowpass.md`.

**A definitive raw byte-scan (disp16 0xB0A0 = -0x4f60, gp-relative loads/stores over [0x13000,0xC4FFC))
found 64 raw `gp-0x4f60` readers image-wide — NOT the ~12 the V50/V52 model assumed.** V50's original
enumeration had already MISSED 3 (`FUN_0002eda8`), proving the prior `search_instructions`-based counts
undercount (kit correction #5). Classifying the ~23 command-region readers (2 firmware-codepath-tracer
agents) gives the real picture:

**~19 command-path CARRIERS of gp-0x4f60 (V52-as-built repoints only 10 of them):**
- Already in V52 (10): 0x2C480, 0x354D2, 0x35AA4, 0x3A6CA, 0x3A7CA, 0x3B4A8, 0x3B672 + the 3 FUN_0002eda8
  branches 0x2F318/0x2F330/0x2F33E (→ gp-0x6b6c → lane 9).
- **MISSING from V52 (9):**
  - 0x29A90 (r12, `FUN_00028ea6`, 1kHz control task) — arbitration LERP curve → gp-0x6a32/gp-0x6b2c cluster.
  - 0x2B69E (r?, `FUN_0002b62c`, ~100Hz assist task) → gp-0x6aea → FUN_0004e96a.
  - 0x2DF32 (r?, `FUN_0002db94`, ~100Hz) → gp-0x6b1a → FUN_0002e52e.
  - 0x33D2A (r?, `FUN_00033d10`, ~100Hz) — a float PID controller → gp-0x6b78 → FUN_0003405a.
  - 0x36682 (r11, `FUN_00036682`, control task) — **self-filters (internal IIR)** → gp-0x6b46 → FUN_00038148.
  - 0x36846 (r14, `FUN_00036828`, ~100Hz) — **self-filters (EMA)** → gp-0x6b44.
  - 0x3B908 (r9, `FUN_0003b8f6`, control task) — **self-filters heavily (float IIR chain)** → gp-0x6bfc.
  - 0x3F8E2 (r11, `FUN_0003f884`) — mode-gated (gp-0x4e5f, believed fallback; liveness UNCONFIRMED) → angle
    integrator → gp-0x6a0a.
  - 0x3FCC6 (r7, `FUN_0003fc16`, control task) — mode-gated (cal tp+0x74cf + gp-0x4ebc speed-like) → gp-0x6a0a.
- Chains A (→FUN_00038148→gp-0x6b70) and B (→FUN_0003b338→gp-0x6b6e) converge in **`FUN_00037fe6`** (a
  7-lane grand sum → gp-0x6ad6 → `FUN_0003a382`, the governor-slew-feeding lane —
  [[reference-accord-fun3a382-unfiltered-residual-lane]]).

**No monitor hazards.** Every gp-0x4f60 monitor read compares raw vs a LITERAL constant, not a
filtered/command value: M1 `FUN_00042af8`@0x42C20 (±25600 counts → gp-0x6af8), M2 `FUN_00043e44`@0x43EDA
(IEEE double 25.0), the FUN_00028ea6 gate @0x28F26 (±25600). So the broad filter would NOT brick via a
V27-class raw-vs-filtered lockstep — the risk is EFFICACY/FEEL, not a brick. Benign readers: producer
region 0x7Exxx-0x81xxx, CAN packers (0x1Cxxx broadcast, 0x55xxx CAN-399, 0x4D8xx, UDS 0x4E4xx/0x4E8xx),
diagnostic loggers FUN_0004fbde/FUN_0002ec52, angle-cal SM 0x69C12. Dead: FUN_0002a93a (0x2A992), orphan
0x2d5fe-0x2db93 (0x2D9A2/0x2DAE6).

**Consequence (load-bearing for strategy):** filtering gp-0x4f60 "at the source + repoint consumers"
requires repointing ~19 lanes across TWO control tasks, 3 of which already self-filter (repointing →
CASCADED IIR → over-attenuation, changing legitimate assist feel) and 2 of which are mode-gated. GATE-2
was closed for a 7-lane insertion; a 19-lane insertion (with cascades) does NOT inherit that verdict and
needs full re-analysis. **This is the concrete empirical case for the operator's diagnose-then-filter
reframe** ([[reference-accord-vibration-levers-falsified-vs-untested]]): FFT the FOURFRAME backward-chain
signals, find the ONE carrier lane, filter it narrowly at a convergence point (e.g. gp-0x6ad6/gp-0x6b70),
NOT the 19-consumer root. **V52-as-built (10 repoints) is INCOMPLETE → not a valid efficacy test as-is**
(half the resonance still passes). See [[reference-accord-v51p-gate1-both-cells-clean]] for the clean cell.
