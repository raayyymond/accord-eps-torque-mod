# HANDOFF — 2026-06-02 (later) — 2020 Accord EPS (39990-TVA-A160) — V25 CLEAN

**Supersedes `HANDOFF-2026-06-02.md` (the V24 build).** Read with `memory/MEMORY_CONSTELLATION.md`
(Era 19) and `memory/reference_accord_corridor_vs_envelope.md` (the load-bearing model below).
This session was 100% on the **2020 Accord TVA** firmware (Renesas V850E2). Goal unchanged: ship a 2×
LKAS steering-torque build that does not EME.

---

## TL;DR

- **V25 was rebuilt CLEAN** and replaces the earlier V24/V25 (shl+B) approach. It is `GAIN + corridor ×2`,
  with the **entire integer-envelope (`shl`) thread dropped**.
- Build artifact (STUDY ARTIFACT — no flash until operator names file + bus):
  `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V25-LKAS-2x-V18gain-corridor2x-PNfix-0x13000-0x100000.rwd`
  Build: `analysis-2020accord/build_v25_tva.py` · plain image `../accord-firmware/analysis-2020accord/_v25_plain_image.bin` · plot
  `analysis-2020accord/plots/v25_corridor_before_after.png`.
- **19 bytes / 12 runs vs stock**, 49/49 CRC PASS, cipher round-trips, all readbacks held (asserted:
  corridor X-breakpoints/N counts unchanged, **zero code-section edits**, cave region all-`0xFF`).
- Unflashed. Not yet road-tested.

---

## The corrected causal model (this is the load-bearing part)

Full record: `memory/reference_accord_corridor_vs_envelope.md`. In brief — there are **three** distinct
"2×" levers, and V21–V24 spent four builds on the wrong one:

| Lever | Scales | Feeds | Verdict |
|---|---|---|---|
| **GAIN** `tp+0x746c` (`0xC646C`) | the LKAS command/torque | the motor | **The only real 2×.** Keep (V18). |
| **`shl` envelope** `gp-0x3574`/`gp-0x3578` | the IIR watchdog reference (`gp-0x6af6`/`gp-0x6b00`) | consistency monitors **only** | Touches no torque, no EME. Useless + harmful. **Dropped.** |
| **Direction corridor** `tp+0x7748`/`tp+0x7754` | `dir1`/`dir2` corridor bounds | the EME integrator `gp-0x3570` | The soft-EME headroom lever. **Scaled ×2 (V25).** |

Two **independent** faults:
1. **Soft EME** (V18: wonky ~10 s, recovers, **no DTC/dash**) = command exits the corridor `[dir2, dir1]`
   → integrator `gp-0x3570` wind-up → SM2/SM3 authority cutback. The GAIN doubled the command, so the
   stock ±1024 corridor is exceeded. **Fix = corridor ×2 → ±2048** (the 2× command fits inside).
2. **Hard fault** (V19–V24: startup / wheel-move, **DTC 0xF00049, dash**) = the `FUN_00043e44`
   consistency monitors desyncing because the `shl` doubled `gp-0x6af6`/`gp-0x6b00` but not their float
   twins / sibling shadows. **Self-inflicted by the `shl`.** V18 (gain, no `shl`) never had it. **Fix =
   don't do the `shl`** → the hard fault simply cannot occur, and all the V24 "B" cleanup (FP-twin caves,
   ±10 widen, weight-8 exclusion, inline-A neutralize) evaporates.

Instruction-verified anchors (bases `tp=0xBF000`, `gp=0xFEDF8000`):
- Delivered torque `gp-0x6b98` (store `@0x43b52`) = `clamp(min(lanes gp-0x6afe+r20, governor gp-0x4f64), ±0x2000)`;
  envelope **absent** on this path (read `0x43ae0–0x43b52`). → the IIR envelope is monitor-only.
- Integrator `gp-0x3570` (`0x43214–0x4327c`) delta = `(command − dir)<<13`; MODE 0 for A160
  (`tp+0x74c8=0` `@0x431cc`) → `command = clamp(gp-0x6acc, ±0x2000)`; clamp `±(tp+0x71dc<<15)`; SM2 arms
  vs `tp+0x7422`=16384 (`@0x436f4`/`0x43746`). Corridor LERP indexed by velocity `gp-0x4f60` (Q10).
- Corridor tables: `[N][X velocity Q10][Y command-counts]`, N=2, flat in stock (±1024). dir1=`tp+0x7748`
  (Y `0xC674E`/`0xC6750`), dir2=`tp+0x7754` (Y `0xC675A`/`0xC675C`).

---

## V25 CLEAN exact edit set (in `build_v25_tva.py`)

Cal block #48 + PN only; **no code-section patches**:
- GAIN `0xC646C` 891→1782 ; CLAMP `0xC61B4`/`0xC61B2` 512→1024 ; RAMP `0xC64DE` 0x11→0x1B (V18 lineage).
- Corridor dir1 Y `0xC674E`/`0xC6750` +1024→+2048 ; dir2 Y `0xC675A`/`0xC675C` −1024→−2048 (×2).
- PN `0x13109`/`0x14120` `'-'→','`.
- Asserted UNCHANGED: corridor X breakpoints `0xC674A`/`0xC674C`/`0xC6756`/`0xC6758` + N counts
  `0xC6748`/`0xC6754`; all code sites (shl/caves/monitor bytes) byte-identical to stock; cave region all-`0xFF`.
- CRC: block #48 `@0xC6FFC`, main `@0xC4FFC`.

---

## Expected behavior / open items

- **Expected:** 2× LKAS like V18; **no** V19–V24 hard fault (no `shl` → no monitor desync); soft-EME
  headroom raised proportional to the gain. Manual driving byte-identical to V18 (only cal touched).
- **Not verified on-car.** The corridor ×2 is the predicted fix; only a road test confirms the soft EME
  is gone. Operator seat-of-pants is the arbiter ([[feedback-operator-lived-experience]]).
- **Safety (operator weighed):** corridor ×2 proportionally loosens the anti-fight / anti-oscillation
  gate — a LKAS command can oppose column motion ~2× longer before the cutback arms.
- **If bit-perfect tuning later wanted:** the corridor is velocity-INDEPENDENT in stock (flat Y). The
  table format supports per-velocity Y values, so a velocity-shaped corridor is a future option.

---

## Contested prior conclusion (corrected this session)

The earlier "bit32 (weight 32) in `FUN_00043e44` = the V18 EME" claim
(`.claude/agent-memory/firmware-codepath-tracer/reference_accord_eme_bit32_float_monitor.md`) rested on a
mis-primed brief (I asserted "V18 throws DTC 0xF00049", which the operator's account contradicts — V18 had
no dash light, recoverable). V18's EME is the **corridor/SM2-SM3** mechanism; `bit32`'s `cmd_final` is
almost certainly gain-aware (from `gp-0x6acc`) so it doesn't diverge under V18. Treat that file as
float-monitor structure evidence, not as the V18 cause. (A caveat header was added to it.)

---

## Safety (kit iron rules — unchanged)

- No flash, no CAN/UDS send, without the operator explicitly naming the **file + bus**; repeat back first.
  All `.rwd` here are study artifacts by default.
- `flashing-2020accord/eps-read-dtcs.py` is read-only; prior on-car fault-register reads returned NRC 0x11.
- Before any flash on a comma device, openpilot/pandad must be killed.

## Suggested first actions next session

1. Re-read this + `memory/reference_accord_corridor_vs_envelope.md` + constellation Era 19.
2. If flashing V25: operator names file + bus; capture CAN `0x427` + steering through a held-2× event to
   confirm the soft EME is gone (and to pin the command full-scale, still the one residual ambiguity).
3. If V25 still soft-EMEs: the corridor scale factor or a velocity-shaped corridor is the next knob; the
   SM arming cals (`tp+0x7422` SM2) remain the alternative lever (do NOT raise `tp+0x71dc` — V20 showed
   raising the integrator clamp backfires).
