---
name: accord-the-8x-gain-is-the-carrier
description: The 8x LKAS gain 0xC6CD0 is the SOLE measured cause of the ~23 Hz vibration; nine other levers died on evidence; vibration scales m^1.74 vs authority m^0.88
metadata:
  type: project
---

🛑🛑 **`0xC6CD0` — THE LKAS FORWARD GAIN — IS THE MEASURED CAUSE OF THE ~23 Hz VIBRATION.**
V101 flew it at 8× (7128) as route `0x95`, 2026-08-19. Operator: *"grinding/vibration now exists at
all speeds… only occurs during LKAS command… I can get it to go away if I apply some torque… as soon
as I let go, the grinding returns and grows into a steady state."*

**EVIDENCE — de-confounded 2×2 against route `71` (V87 = 4×, Lever B already dead), in SHAPE units
(band ÷ 32–38 Hz control) against a MEASURED placebo floor of 1.45× (r75 vs r76, byte-identical V89):**
- **gain G = 2.7–3.9×** at 22–26 Hz · **Lever B = 0.84–1.30× (INSIDE the floor)** · **`0xCBE74`
  k = 0.86–0.90 (inert)**. A×B reproduces C on all three channels. Insensitive to `k` across its CI.
- **The peak MOVED: 20.3 Hz on THREE separate 4× routes (r7e, r7f, r85) → 23.0 Hz on V101** ⇒ a
  **POLE moved**, not an amplitude scaled.
- **The line is in the FIRMWARE'S OWN DEMAND** — `gp-0x6b94` 21–24 Hz shape **1.71× [1.33, 2.29]**
  above its own broadband dose, every other band flat at 1.3–1.6×.
- ⭐ **The aggregator's SIGN reverses 25–37 /s at wire codes 16–64 (205–820 ct) where V100 reverses
  0.7–3.2.** Re-weighted onto V100's magnitude distribution: **34.19 vs 11.17 = 3.06×** ⇒ **NOT a
  quantisation artefact.** Internal control `b4` (PID reference sign) flat at 1.24×.

**🛑 NO FIRMWARE CLAMP BINDS ANYWHERE.** `b6` (`|gp-0x6b4c| ≥ 4096`) duty **0.000000** over 17,614
engaged frames, zero transitions, all 10 command deciles — with **all four positive controls passing**
(not a V64/V68 gate null). Structurally: the setpoint is LERP-clipped to **15360 upstream of the
gain** ⇒ `0xC61B2`/`0xC61B4` sit at **81.5 % of rail on every build since V14**. The only saturating
element is **openpilot's own ±4096 rail, ~12 % duty on BOTH builds**.

**🛑 NOT A LIMIT CYCLE.** Growth σ inside a phase-randomised surrogate null (1.13/0.91); kurtosis
3.85/3.38 (3.0 = narrowband Gaussian). A **very lightly damped resonance** — consistent with there
being no amplitude-setting saturation inside the ECU. *"Grows into a steady state"* is the **release
transient**: σ ≈ 2.5–5 s⁻¹, plateau in ~0.5 s.

**DOSE-RESPONSE — vibration m^1.74 [1.43,1.96], authority m^0.88 [0.75,1.04].** 🛑 **TWO POINTS, NO
THIRD RUNG — `p` is EMPIRICAL, not a law.** At 6×: 22–26 Hz **0.61× [0.57–0.66] of V101**, wheel rate
under hard command **0.78× of V101 but still 1.43× of V100**. **Benefit:cost 1.76:1.**
🛑 **The naive mechanism is REFUTED**: within either route the band does **not** scale with command
amplitude (slope **+0.01 [−0.36,+0.31]** across a >10× range) ⇒ **the gain acts on the LOOP, not the
drive.** ⭐ **Structural cap: the build ABORTS at 10×** (`0xC674E`=5120 must exceed the tracking clamp).

**⇒ V102 = `0xC6CD0` 7128→5346 (6×) + clamps 4096→3072, chosen by the OPERATOR from this curve.**

🛑 **NINE LEVERS KILLED ON EVIDENCE, NONE ON THE ROAD** — see [[accord-nine-levers-killed-2026-08-20]]
and `docs/BUILD-LINEAGE.md`. Related: [[accord-band-envelope-is-rectified-not-analytic]],
[[accord-gp6b4c-is-an-11-slot-assist-sum]], [[accord-4x-lkas-gain-is-the-frozen-variable]] (its
*"raising is free"* leg does **not** survive), [[accord-v88-flew-grinding-fixed-command-intact]].
