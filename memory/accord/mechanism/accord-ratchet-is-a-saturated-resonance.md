---
name: accord-ratchet-is-a-saturated-resonance
description: ★★ The ~7.3 Hz ratchet is LKAS-gated at p=1.09e-08 pooled over 5 builds, fixed in hertz, and its waveform is SYMMETRIC on every build -- an amplitude-saturated resonance, NOT a friction limit cycle. Damper lane and relay both eliminated.
metadata:
  type: reference
---

# ★★ THE RATCHET: LKAS-gated, fixed-frequency, SYMMETRIC ⇒ a saturated resonance

## It is strictly LKAS-gated, and this is now highly significant
Pooled across **all five builds**, each route contributing its OWN internal engaged-vs-manual contrast
(so no cross-route level comparison, and the exposure weakness does not apply). Creep 0.3–2.5 m/s, drive:

| arm | windows | episodes | prom ≥10× | RMS med |
|---|---|---|---|---|
| **ENGAGED** | 81 | 25 | **61/81 (75.3%)** | 322.5 |
| **MANUAL** | 48 | 23 | **1/48 (2.1%)** | 27.4 |

**Fisher exact on EPISODES: OR 115.5, p = 1.09e-08.** RMS ratio 11.8×. Present on **every** build
including V62 — **nothing escaped into manual.**
⚠ Within segs 13/14 alone the power ratio is 2,039× but that is 2 vs 3 episodes, **Fisher p = 0.10 — not
significant alone.** The pooled test is where the significance lives. Do not quote the single-route ratio
as the evidence.

## ★★ The waveform is SYMMETRIC on every build ⇒ NOT stick-slip
Dwell on the >4 Hz high-passed bar, against synthetic calibration:

| signal | dwell +/− | ratio | skew(dx/dt) |
|---|---|---|---|
| ratchet (all 5 builds) | 7.33 / 7.15 | 1.03 | **−0.16 … +0.06** |
| **SAWTOOTH calibration** | 6.80 / 6.69 | 1.02 | **−3.27** |

⇒ **An AMPLITUDE-SATURATED RESONANCE, not a friction limit cycle.** Points at **damping / loop gain**,
not friction compensation or a deadband. **Build-invariant** — V62 changed its amplitude, not its
mechanism.

⚠ **RE-FRAMED 2026-08-04 — the SATURATED half is now BELIEF, not measurement.** Route `4f` shows crest
factor **2.07–2.45** on a band-pass where a **steady sine gives 1.414**, and **no flat-topping on any
filter**. The symmetry above is unaffected (it kills stick-slip either way); what is not supported is
*"flat-topped / clipping"*, which is what justified V69's probe rung choice.
**Flag it for re-examination — do not treat the saturation model as dead, and do not quote it as
established.** ⚠ Separately, **Q is NOT measurable at NFFT 256** (main lobe caps it at ~13.3), so the
recorded **Q ≈ 36** is neither confirmed nor refuted by `4f`.
See [[accord-ratchet-characterised-on-route-4f]].

## Fixed in hertz, not a tyre order
Domain test 0.3–11 m/s: **CV(Hz) 0.211 vs CV(order) 0.829** on V62; fixed in hertz on all five builds.
🛑 **Order 1 (`0.489·v`) enters 6–9 Hz at v = 12.3 m/s and leaves at 18.4 m/s — every ratchet number
above ~11 m/s is tyre-contaminated.**

## What is ELIMINATED as its mechanism (all byte-verified)
- ❌ **The base-assist damper `gp-0x6bd0` is INERT at both symptoms' operating points.** The 4-factor
  chain is `mulu` throughout with **no additive term**, and two factors are zero here:
  **FactorC** (`0xD27BC`, mode 10) X = [2240,3840,5120,8960] = **35/60/80/140 km/h**, Y = [0,235,430,877]
  ⇒ **0 below 35 km/h**; **f5** (`0xD27F8`) X = [60,400,2500,4000], Y = [0,140,539,927] ⇒ **0 below
  12.7 deg/s**. Measured: **f5 = 0.0000 at the ratchet's 2.0 deg/s median, 0.0052 at the grinding's 15.5.**
  ⇒ **A THIRD independent reason V44/V47 were null**, beyond the FactorC speed gate and the task-5 lag.
  f1 (`0xD2738`) and f4 (`0xD2774`) are flat 1024 = **no-ops**.
- ❌ **The `FUN_00034350` relay** — a genuine Coulomb relay (sign forced to `−sign(gp-0x6abe)`
  @`0x3469e`–`0x346a2`, magnitude from four *independent* tables) — but dead here for the same reason.
- ❌ **Friction comp `FUN_00036c12`/`gp-0x6b26`** — continuous, `−K(speed) × motor rate`, viscous
  damping, reads no torque signal.
- ❌ **The motor-rate LERP as a discriminator.** Scale resolved: **4.7121 counts per deg/s**
  (`0xC613A` = 1159; chain `gp-0x4f50 → FUN_00041464 → gp-0x6abe → FUN_0003f776 → gp-0x6a56 →
  FUN_00040a50 → gp-0x69ea → 0x14A byte2:3`). Ratchet **9.4 counts**, grinding **73.0** — both inside
  gain_A's **flat first segment** (breakpoints 250/400). The stock curve cannot separate them.

## ✅ Still open, and the leading idea when the ratchet is worth attacking
The two modes **do** separate on motor rate (9.4 vs 73.0 counts) — **breakpoints are calibration.**
r24's gain_B (mode 10, `0xD2AEC`) has X = [0, **400**, 1500, 3000]. Moving them down to bracket the two
operating points — e.g. X = [0, 40, 100, 3000], Y = [2305, 2305, 4610, 4610] — gives **stock gain where
the ratchet lives and 2× where the grinding lives.** Arithmetic safe (5120 × 4610 = 23.6M vs 2³¹).
🛑 Not a build proposal: it would aim at an unmeasured effect. See [[accord-v62-flashed-grinding-is-fixed]].

See also [[accord-r26-is-structurally-inert]] (🛑 **its title claim is REVERSED as of 2026-08-04 —
r26 is LIVE**), [[accord-ratchet-characterised-on-route-4f]],
[[feedback-episodes-not-windows-and-the-noise-floor]].
