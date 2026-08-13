---
name: accord-v88-flew-grinding-fixed-command-intact
description: "V88 flew as route 73 (2026-08-09). Operator: audible grinding FIXED, micro-ratcheting and ratcheting now the main issues. The 15-22 Hz delivered-command content halved while the 0.5-3 Hz LKAS command was untouched — the first time a fix has been shown not to cost steering authority. First route with real highway exposure."
metadata: 
  node_type: memory
  type: project
  originSessionId: d1d94665-4414-43cb-884d-1f27ae127561
  modified: 2026-08-10T00:47:29.308Z
---

**Route `73` = `75604b0a432fdc89_00000073--9380c74d52`, 11 segments, cache `_cache_r73/`.**

## IDENTITY — V88, three independent measurements [EVIDENCE]
Pre-registered parameter-free discriminator: on V88 the cave byte and the 427 packer read the same
cell, so `b6 == (wire >= 160)` must hold frame by frame; on V87 the cave read `gp-0x6b70`.

| | route 73 | route 71 (V87 control) |
|---|---|---|
| orchestrator, row-grid pairing | 0.9437 | 0.4033 |
| extraction agent, raw ts ±10 ms | **0.9654** | 0.4022 |
| scoring agent, ±20.1 ms | 0.9560 | 0.4035 |

**Chance level on route 73 is 0.6028** (the marginals are nearly equal, so chance is HIGH) and V87 sits
essentially *at* its own chance level of ~0.37. Duty match 0.27330 vs 0.27334. Away from the comparator
edge (|wire−160| > 40) agreement is **0.9901**. Lag sweep peaks at lag 0.

## ⭐ THE RESULT THAT MATTERS — the fix did NOT cost steering authority
Speed-matched 2–4 m/s, engaged, unclipped, episode-bootstrapped, V87's exact protocol:

| band | V88/V87 | CI excludes 1.00 |
|---|---|---|
| **0.5–3 Hz (the LKAS command)** | **1.192 [0.780, 1.812]** | **no — NULL** |
| 3–6 Hz | 1.165 [0.959, 1.375] | no |
| 6–9 Hz | 0.859 [0.503, 1.171] | no |
| 9–12 Hz | 0.604 [0.465, 0.943] | **FALL** |
| **15–22 Hz** | **0.549 [0.407, 0.844]** | **FALL** |

⇒ **Lever B halved the delivered command's 15–22 Hz broadband content while leaving the peak effective
LKAS steer command intact.** That is the operator's own stated constraint, met and measured.
**Aliasing cleared**: on the 100 Hz channels (which the 427's 24.9 Hz Nyquist cannot resolve), 15–22 Hz
is 0.33×/0.31× while **28–35 Hz is flat at 1.13×/0.94×** ⇒ the fall is real, not a fold.

## 🛑 A HYPOTHESIS OF MINE THAT WAS REFUTED, AND WHY
I predicted 15–22 Hz would **RISE**, reasoning that r24 is a differentiator and Lever B doubles its gain.
**Wrong: r24 is rate FEEDBACK inside the loop, and `gp-0x6b98` is the loop's OUTPUT, not its input.**
More derivative feedback = more damping = **less** HF motion everywhere inside the loop. V87's
engaged-spectrum rise with frequency (29 / 29 / 52 counts rms) against a flat manual arm (~9) is the
signature of an **under-damped closed loop at stock derivative gain**, not of a feedforward differentiator.

## 🛑 WHAT THIS ROUTE CAN AND CANNOT RESOLVE
- **7.41 engaged minutes; 120 s engaged ≥50 km/h, 80 s ≥80 km/h, v_max 116.6 km/h** — the first route in
  five with any highway at all (the previous four had **0.0 s**). Highway = segments 4–5.
- 🛑 **ZERO manual frames above 20 km/h** ⇒ no engaged-vs-manual contrast is constructible at speed.
- 🛑 58.7 % of manual frames are PARKED (route 71: 58.9 %) ⇒ raw engaged/manual ratios stay worthless.
- Split-half nulls are ~3× tighter than route 71's, **but the cross-build 6–9 Hz comparison inherits route
  71's [0.18, 5.51]** ⇒ it cannot resolve a ratchet change under ~3–5×. **"The ratchet was unchanged" is
  NOT supported by this route pair — "cannot resolve" is.**
- Clean flight: 0 sentinels, DTC duty 0.000000, CONFIG_VALID 1.0, no EPS event in 1,786 `onroadEvents`.
  `steerSaturated` ×5 is new — expected on first engagement above 100 km/h.

## THE THREE SYMPTOMS — the instrument agrees with the operator on all three
- **Grinding (he says FIXED).** `e_18-22` engaged creep: **V88 150.5 [118.5, 183.8]** against **V67's
  110.7** (which reproduces the record's ~109, so the ruler is calibrated). **V88/V67 = 1.101
  [0.424, 2.206] — a clean null ⇒ indistinguishable from the kit's best-ever result.** V87 was 400.2.
  Negative control 32–38 Hz inside its null ⇒ band-specific. 🛑 The V88/V87 *ratio* (0.549) does not
  clear route 71's own [0.30, 3.40] null — **the load-bearing statement is the absolute level vs V67.**
- **Grind #2 (hints, could not elicit).** **ZERO events** in the strict creep-cornering regime, same as
  V67/V68. 🛑 Exposure 47.4 s = **29 % of the 166 s interpretability floor ⇒ formally uninterpretable.**
- **Ratcheting — UNCHANGED, back to V67.** `e_6-9` V88/V67 = **1.040 [0.759, 1.260]** over 14 matched
  cells. **Exactly V88's pre-registration.** ⇒ it did not get worse; the grinding above it came down.
🛑 The data do **not** separate "micro-ratcheting" from "ratcheting" — the apparent 9–10.5 / 10.5–12 Hz
clusters are **wheel order 2** at speed. That is a statement about the instrument, not the car.

## ★★★★★ THE HIGHWAY — speed-invariance PROVEN, and a real 29.02 Hz ring
First route that could test it. **`f0 = +0.0102·v + 7.998 Hz` against wheel order 1's 0.4807 — 47×
flatter**, corr(f0, v) = +0.106. f0 by stratum: 8.01 (creep) · 8.08 · 8.31 · **8.36 Hz (>80 km/h)**.
★ **The >80 km/h stratum is INTRINSICALLY order-clean** — at 30 m/s order 1 has climbed to 14.5 Hz,
above the band, so **no order 1–6 can reach 6–9 Hz** ⇒ the cleanest ratchet measurement in the corpus.
★ **Amplitude decays 4.8× from creep to highway (402 → 83.5 ct)** ⇒ **the ratchet is a LOW-SPEED
phenomenon in AMPLITUDE while FIXED in FREQUENCY.**
★ **26–31 Hz is real at 29.02 Hz** and survives the order veto (49/115 windows, `e` 121.4 [77.6, 176.5]);
above 80 km/h it is the dominant non-order band on every channel. **Grind #1 falls away at highway**
(`e_18-22` 161 → 43.0).

## 🛑 THE CO-MOVEMENT DID NOT SURVIVE ITS DOSE TEST
Within V88, corr(log 15–22 Hz command rms, log 6–9 Hz column prominence) = **+0.364** (p = 0.016), which
looked like a lever. **The dose test kills it.** Speed-partialled elasticity **b = 1.082 [0.814, 1.329]**
⇒ V88's 0.549× cut predicts a ratchet ratio of **0.5225**, well outside the resolvable floor of
[0.759, 1.260] ⇒ it **should have been detectable. The measured ratio was 1.040 — no change.**
⊕ And the **32–38 Hz negative control responds too** (`negctrl_as_response` = 0.664 [0.441, 0.827]) — a
negative control is not supposed to respond at all. ⇒ **common cause (road input / effort driving every
band at once), not the command driving the ratchet.**
🛑 **So "cut more HF command content to fix the ratchet" is NOT supported.** Combined with the clamp
result — the `0xC6446` dose window is nearly closed, 2.5× sits at the rail at the hot end of the
scalar-vs-curve spread and 3× pins into V80's relay class — **V89 should be a MEASUREMENT, not a dose.**

## 🛑 THE NEXT STEPS ARE ANALYSIS ON EXISTING LOGS — the orchestrator was corrected
He recommended a dedicated ring-down driving session. **The operator: *"We're just diagnosing
micro-ratcheting and ratcheting at this point, at parking lot speeds. This is done in a drive/log we
already have on V88."* He is right** — route 73's segments 0/8/9 give ~118 s engaged below ~15 km/h,
exactly where the ratchet is largest (402 ct vs 83.5 at highway).

★ **The session under-used its own instrument.** Ring-down *was* the only ζ estimator that had passed a
control, so "we cannot measure Q" had collapsed into "we need more disengagement edges" — carried forward
without re-checking. **V88 broke that**: H2 gives `|tq/cmd|` = **6.24 at 7.79 Hz, phase −30.9°**, coherence²
**0.009 (rectified = the shuffled control) → 0.343 (signed)**. **That is a transfer function, and Q falls
out of its peak shape and phase roll-through with no disengagement at all.** V87 could not do it —
rectification destroyed the phase, which is why that session fell back on ring-down.

⇒ **three analyses, no car needed:** (1) fit `cmd → column` 4–15 Hz on route 73's creep segments, Q from
peak + phase slope; (2) **pool ring-down edges across all 13 caches** (only `r71`/`r73` were ever screened)
— ⚠ screen by damper state, V87/V88 are stock on FactorC and pool cleanly, **V74–V86B do not**;
(3) **partial coherence vs the IMU**, run alongside (1) because it can undercut it — **if the mode is
road-excited rather than command-excited, `cmd→column` is the wrong transfer and its Q is biased, and
that answer decides whether ANY command-side lever could work.**
🛑 **The only thing that needs new driving is a BUILD comparison — and that needs a new build, not a
new drive.** ⊕ `gp-0x6ada` (r24's post-clamp mirror, 1 writer / 0 readers) should ride along on whatever
build is next, so the clamp margin stops resting on V65's `|dtorque|` distribution.

## 🛑 THE r24 CLAMP IS AN IMMEDIATE, AND RAISING IT IS THE ONE CHANGE THAT COULD COST LKAS AUTHORITY
`±0x2000` at `0x3ac42`–`0x3ac54` is **four 16-bit immediates in `addi`/`movea`**, not a cal — orchestrator-
disassembled. So the edit is trivial and in the safe in-place class (V42/V57/V87). **But `gp-0x6b94`, the
TEN-LANE aggregator sum that leaves the function, is hard-clipped to ±10240** (`movea 0x2800` @`0x3acf6`
/ `-0x2800` @`0x3ad0e`) ⇒ **r24 alone is already allowed 80 % of the whole output budget.** The record
lists the LKAS term `gp-0x6b4c` among the lanes in that same sum ⇒ **raising r24's ceiling lets a
derivative lane eat the headroom the LKAS command needs — the one change in this path that could reduce
the peak effective LKAS steering.** ⚠ That last step is from the record, not from a fresh decompile —
verify it first if the clamp is ever pursued.

Related: [[accord-v88-lever-b-restored]] · [[accord-v87-flew-the-probe-fired-and-6b98-is-broadband]] ·
[[accord-ratchet-is-a-lightly-damped-resonance]] · [[accord-v81-carries-neither-grind1-fix]] ·
[[feedback-episodes-not-windows]] · [[accord-averaged-spectrum-needs-matched-speed-distributions]]
