# ★★ The grinding is a positive-feedback loop through the torque sensor — and it is UNCOMPENSATED

**Operator's hypothesis, 2026-07-30. Traced and measured the same day. Now the leading explanation for
the ~20.9 Hz grinding, displacing the parametric-pump story that V58/V59/V60 were built around.**

## The mechanism
The torque sensor sits between the steering wheel and the road. When LKAS commands motor torque the
column twists — **and the sensor reads that twist as though it were driver input.** Base assist boosts
it → more motor torque → more twist. A closed loop. Unlike the parametric pump this is a plain
**linear** instability: loop gain > 1 with the wrong phase at ~21 Hz gives a sustained oscillation.

## The three findings that converged
1. **MEASURED — the command→torsion-bar transfer function peaks at 21.09 Hz, the GLOBAL maximum over
   3–46 Hz.** 15.6× baseline engaged+creep+hands-off (K=5, coherence 0.654 vs K-appropriate null
   0.527); **25.7× at 20.70 Hz** any-hands (K=53, null 0.056). Cross-spectra accumulated across
   disjoint runs, never spliced. That is a loop resonance, not a broadband response.
2. **TRACED — no motor-command feedforward compensation exists anywhere** in the
   torque → boost-shaper → damper → aggregator chain. The delivered command `gp-0x6b98` appears
   exactly twice: as a **sign input** to the `gp-0x6ac2` counter-torque detector (a **ceiling** in all
   4 real consumers, never a correction), and in `FUN_00043e44`, whose output `gp-0x6906` has **zero
   readers program-wide**. `FUN_00034a72`, `FUN_00034350` and `FUN_0003aa2c` contain **zero**
   references to it. Byte-scan corroborated.
3. **BYTE-VERIFIED — the only motor-reaction-aware term is switched off where it matters.** The
   velocity-proportional damper `gp-0x6bd0` (sign forced to `-sign(gp-0x6abe)`) is **arithmetically
   zero below 35 km/h in all 34 mode tables** (FactorC `Y[0]=0`, multiplicative, LERP clamps to Y0).

⇒ **At creep the assist loop has no motor-reaction compensation AND no damping.**

## Why it beats the parametric-pump story
- The pump kept measuring **marginal** against every threshold available (eps 0.013–0.169), and the
  threshold `2/Q` cannot be pinned because the **passive Q is not measurable while the mode is active**
  — there is **no ring-down at all** (66 candidates, longest **0.63 cycles**). A linear loop at unity
  gain sustains indefinitely and never rings down. That is what the data looks like.
- ★ **V52C retrodiction.** V52C lowpassed the **torque sensor** `gp-0x4f60` (cave, α = 74/1024,
  fc ≈ 12 Hz, only −6.1 dB at 21 Hz, +61° lag) and **halved the mode** — the largest single effect any
  build has had, and the **only** lever on the **feedback** path; every falsified one sat on the
  command path. The loop predicts this; nothing else does.

## 🛑 What is NOT established
- **The transfer-function peak shows the bar responds resonantly to command — it does not prove the
  assist feedback CREATES the resonance.** A mechanical plant resonance excited by command looks
  similar in magnitude. What tips it is engagement-gating: road input would ring a passive mode with
  LKAS off, and V59 shows it does not (absent disengaged, 61 s control). Strong but circumstantial.
- **V52C's "halved" was never re-derived under the corrected statistics** (lateral engagement +
  sustained-effort hands-off + envelope/prominence). This kit's halvings have been **median artifacts**
  before. **Re-derive it before building on it** — it either promotes the loop or removes its best
  evidence.
- **Loop phase margin is unobtainable from the bus.** One 100 Hz mailbox sample is **~76° at 21 Hz**.
  Sizing a fix needs a firmware-side probe, not more rlog analysis.

## Consequence for levers
Damping is **closed** (V44 FactorC + V47 Factor E, both flashed, both null). The second aggregator path
`gp-0x6b70` is **closed** (terminates at V56's falsified `0xC6AF0`; all its weights are unity/stock).
What remains is **base-assist loop gain** — `0xCA154[mode]`→`0xD2834` (speed-keyed), the amplitude
curves, `0xC63BA` — all on the base-assist path, **no LKAS-only decoupling point exists in this chain**
(traced; unlike V57's `0xC646C` there is no fork). That makes it a **direct trade against steering
weight, i.e. an operator decision.**

Related: [[accord-check-build-lineage-before-proposing-lever]],
[[accord-ratchet-and-grinding-are-two-symptoms]], [[accord-gp6ba6-is-the-boost-amplitude-index]],
[[accord-sign-probe-needs-zero-crossings]].
