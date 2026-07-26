---
name: reference-accord-corridor-vs-envelope
description: "2026-06-02 (V24→V25 CLEAN) load-bearing causal model for the 2020 Accord (39990-TVA-A160, V850E2). THREE distinct '2×' levers, do NOT conflate: (1) GAIN tp+0x746c=0xC646C 891→1782 — the ONLY real torque 2× (LKAS command); (2) shl-envelope (gp-0x3574/gp-0x3578 IIR → int16 shadows gp-0x6af6/gp-0x6b00) — a WATCHDOG REFERENCE ONLY, gates NEITHER delivered torque NOR the EME; doubling it (V21–V24 shl 0x8→0x9) only DESYNCS the int-vs-float consistency monitors = the SELF-INFLICTED hard fault; (3) DIRECTION CORRIDOR tp+0x7748 (dir1 UPPER, Y@0xC674E/0xC6750) / tp+0x7754 (dir2 LOWER, Y@0xC675A/0xC675C) — the soft-EME command-integrator reference. TWO faults: SOFT EME (recoverable ~10s, NO DTC) = command exits corridor → integrator gp-0x3570 wind-up → SM2/SM3 cutback; HARD fault (DTC 0xF00049, dash) = consistency-monitor desync, exists ONLY because of the shl. Delivered torque gp-0x6b98 = clamp(min(lanes gp-0x6afe+r20, governor gp-0x4f64), ±0x2000) — envelope ABSENT (instruction-verified 0x43ae0–0x43b52). V25 CLEAN = GAIN + corridor ×2 (±1024→±2048), drop the entire shl/envelope/consistency-monitor thread. tp=0xBF000, gp=0xFEDF8000."
metadata:
  node_type: memory
  type: reference
---

# Accord EME: the corridor (real lever) vs the IIR envelope (watchdog only)

> **⚠ CORRECTED 2026-06-02 (later, V25 road-test → V26):** the claim below that the corridor is a clean
> lever and that "the entire consistency-monitor thread can be dropped — nothing on the monitor side needs
> touching" is **WRONG**. V25 (corridor ×2, monitor untouched) was road-tested and **HARD-FAULTED** (DTC
> 0xF00049, EPS shutdown) at full RIGHT lock. The **direction corridor IS lockstep-monitored**: it is
> computed in both integer (walls `gp-0x6af6`/`gp-0x6b00` from cal `0xC674E`/`0xC675A`) and float (a
> velocity-LERP over cal `0xC6664`), and a monitor cross-checks them (inline check A @0x43172 + FUN_00043e44).
> V25 doubled only the integer side → 1024-LSB desync → DTC. **V26 tried to fix it by doubling cal
> `0xC6664` 1.0→2.0 — and that was a SECOND mistake: `0xC6664` is LERP_B (a velocity ENVELOPE multiplier),
> NOT the float corridor twin.** V26 was FLASHED and HARD-FAULTED *immediately at rest* (worse than V25):
> at rest `lerp_a=2.0`, so doubling `lerp_b` added a constant +2.0 envelope offset → watchdog desync from
> t=0. **The REAL float twins are RAM `lp`/`r20` (→`gp-0x6db0`/`gp-0x6db8`) computed in `FUN_00043e44`; the
> working fix is V27 = int corridor ×2 + a CODE TRAMPOLINE at `0xC4E00` doubling `lp`/`r20`.** The
> three-lever framing + "shl is the only thing that desyncs the monitor" + the "double 0xC6664" claim are
> all superseded by **[[reference-accord-corridor-lockstep]]** (read that for the live V27 model;
> `0xC6664`=LERP_B is [[reference-c6664-lerp-b-envelope]]). (The GAIN lever and the
> delivered-torque-excludes-envelope facts below remain correct.)

Established 2026-06-02 across the V24→V25 session (multiple `firmware-codepath-tracer`
subagents + operator-directed instruction-level Ghidra reads). This is the causal model that
resolved four builds (V21–V24) of confusion. Bases `tp=0xBF000`, `gp=0xFEDF8000`. All [V] claims
are instruction-grounded in `s_motor_torque_rate_shaper` (`FUN_00042af8`) and the float monitor
`FUN_00043e44`. Supersedes the loose "double the integer envelope to give 2× headroom" framing that
drove V21–V24.

## The three "2×" levers — do not conflate them [V]

| Lever | What it scales | Feeds | Effect |
|---|---|---|---|
| **GAIN** `tp+0x746c` (`0xC646C`) 891→1782 | the LKAS **command/torque** itself | the motor | **The only real 2×.** This is what makes the command exceed everything downstream. (V18.) |
| **`shl 0x8→0x9`** on `gp-0x3574`/`gp-0x3578` IIR | the **IIR envelope** (→ shadows `gp-0x6af6`/`gp-0x6b00`) | **consistency monitors only** | Watchdog reference. Touches NEITHER torque NOR the EME accumulator. (V21–V24; useless + harmful.) |
| **Direction corridor** `tp+0x7748` (`dir1`) / `tp+0x7754` (`dir2`) | the corridor the command is compared against | the **EME command-integrator** `gp-0x3570` | The soft-EME headroom lever. (V25.) |

## Two independent LERP chains [V]

1. **IIR-envelope chain** → `gp-0x3574`/`gp-0x3578` (IIR) → `sar 0x8` → int16 shadows
   `gp-0x6af6` (0xFEDF150A) / `gp-0x6b00` (0xFEDF1500). These are read ONLY at monitor sites:
   inline check A (`0x43182`), inline check B (`0x43a48`, routes to dead-end `gp-0x6908`), and the
   float monitor `FUN_00043e44` (`0x4462a`). **They never reach delivered torque or the integrator.**
   The `shl` doubling lives here (sites `0x42dae`/`0x42dca`/`0x42f16`).
2. **Direction-corridor chain** → LERP(`tp+0x7748`) = `dir1` (UPPER), LERP(`tp+0x7754`) = `dir2`
   (LOWER), indexed by `gp-0x4f60` — ⚠ **CORRECTED 2026-07-18: that is SENSOR-B DRIVER COLUMN TORQUE,
   not column angular velocity** (CAN-399 packer `FUN_00055c42`); the "Q10, 1024 = 1.0 rad/s" scale note
   below is therefore also suspect and should be re-derived in torque units. See
   [[reference-accord-gp4f60-is-sensor-b-column-torque]]. (The tables are flat in stock, so the error
   changed no stock behaviour — but it would matter to anyone reshaping these corridor tables.) Base loads
   `movea 0x7748,tp,r6 @0x4304c` and `movea 0x7754,tp,r15 @0x430b2`. Format per table:
   `[N][X0..X_{N-1}][Y0..Y_{N-1}]` s16, N=2; X = velocity breakpoints (Q10), Y = corridor bound
   (command-domain counts, full-scale ±8192 = ±0x2000). **Both tables flat in stock** (Y[0]=Y[1]),
   so the corridor is a velocity-independent ±1024.

## Delivered torque does NOT use the envelope [V]

`gp-0x6b98` (0xFEDF1468, the FOC input) store at `0x43b52`:
`gp-0x6b98 = clamp(min(lanes gp-0x6afe + r20, governor gp-0x4f64), ±0x2000)`.
Read directly at `0x43ae0–0x43b52`: the envelope (`gp-0x6af6`/`gp-0x3574`) appears **nowhere** on
this path. So the `shl` envelope-doubling changes no torque. (This closed the long-open "is the
envelope used to clamp the command?" question → **no**.)

## The soft EME = corridor → integrator → SM2/SM3 [V]

The command-integrator `gp-0x3570` (update block `0x43214–0x4327c`) accumulates per 1 kHz tick:
`delta = (command − dir_boundary) << 13`, winding up ONLY when the command exits `[dir2, dir1]`.
MODE 0 for A160 (`tp+0x74c8 = 0x00`, read `@0x431cc`): `command = clamp(gp-0x6acc, ±0x2000)`. The
integrator is clamped to `±(tp+0x71dc<<15)` (`0x43268`/`0x43270`); SM2 arms when its magnitude
crosses `tp+0x7422` (`0xC6422` = 16384, read `@0x436f4`/`0x43746`); SM3 clamp = `tp+0x71dc`
(`0xC61DC` = 30720). When armed, SM2/SM3 cut steering authority → V18's wonky-for-~10s,
self-recovering EME (**no DTC, no dash light**). See [[reference-accord-override-snap-state-machines]].
The **GAIN** (lever 1) doubled the command, so the stock ±1024 corridor is exceeded → wind-up → EME.

## The hard fault = consistency-monitor desync, self-inflicted by the `shl` [V]

The V19–V24 hard fault (DTC 0xF00049, startup or on wheel movement, dash light) is the
`FUN_00043e44` accumulator crossing 128.0 (`@0x44a2e`) because the `shl` doubled `gp-0x6af6`/
`gp-0x6b00` but not their float twins / sibling shadows (`gp-0x6b04` = f(`gp-0x6acc`), `gp-0x6b0a`
= ABS(`gp-0x3570`>>15) — both STOCK under the doubling). The weight-8 window bit
(`gp-0x6b04` ∈ [`gp-0x6b00/1024`−5/1024, `gp-0x6af6/1024`+5/1024]) is a PROPORTIONAL mismatch
that no fixed-LSB widen can cover — it was the V24 manual-turn fault. **V18 (gain, no `shl`) never
had a hard fault** — proof the hard fault is manufactured by lever 2, not by the gain.

## Two "mode" systems (the recurring byte-offset trap) [V]

- `tp+0x74c8` (`0xC64C8`) = **command mode selector** = `0x00` for A160 → MODE 0. (`tp+0x74ca`=0x01
  is a DIFFERENT byte, a direction-ref scale; reading it instead is the byte-offset error that
  flipped mode=0↔mode=1 in past sessions.)
- `gp-0x674e` = **variant mode** (LERP-curve-set selector) = 1 for A160 (TVAA1, Era 13). Distinct
  system; do not conflate with the command-mode selector.

## V25 CLEAN build (current)

`build_v25_tva.py` = **GAIN** (V18: `0xC646C` 891→1782, clamps `0xC61B4`/`0xC61B2` 512→1024, ramp
`0xC64DE` 0x11→0x1B) + **corridor ×2** (`dir1` Y `0xC674E`/`0xC6750` +1024→+2048; `dir2` Y
`0xC675A`/`0xC675C` −1024→−2048) + PN. **NO `shl`, NO caves, NO consistency-monitor edits** → no hard
fault to fix (it was only ever the `shl`'s side-effect). X breakpoints + N counts asserted unchanged.
19 bytes / 12 runs vs stock; 49/49 CRC; cipher round-trips; before/after plot at
`analysis-2020accord/plots/v25_corridor_before_after.png`. STUDY ARTIFACT — unflashed.
**Expected:** 2× LKAS like V18, no V19–V24 hard fault, soft-EME headroom raised.

## Safety

The corridor is the anti-fight / anti-oscillation authority gate. Widening it ×2 lets a LKAS command
persist up to twice as far from the column-motion direction before SM2/SM3 arms — a proportional
loosening of override-snap responsiveness, matched to the 2× gain. Operator weighed and accepted.

## Contested neighbor (do not over-trust)

`.claude/agent-memory/firmware-codepath-tracer/reference_accord_eme_bit32_float_monitor.md` claims
"bit32 = V18 EME root cause." That conclusion rests on a mis-primed brief and is **likely wrong**:
V18 produced **no DTC** (the soft EME is the corridor/SM path), and bit32's `cmd_final` is almost
certainly gain-aware (derived from `gp-0x6acc`, the already-gained command) so it does not diverge
under V18. Treat the bit32 file as evidence of the float-monitor structure, not as the V18 cause.

## Related

[[reference-accord-override-snap-state-machines]] · [[reference-accord-lkas-delivery-and-governor]] ·
[[reference-accord-lerp3-gp3574-chain]] · [[project-accord-torque-mod-v0]] ·
[[feedback-operator-lived-experience-overrides-analyst-recs]] · [[feedback-rigorous-validation]]
