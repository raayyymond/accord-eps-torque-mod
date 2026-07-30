# STATE — living current state of the kit

**Last updated: 2026-07-29.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed and falsified — check it before
proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-29-v57-decouple-and-the-angle-rate-turn.md`.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it. See
`memory/feedback-explain-with-python-mirroring-decompiled-arithmetic.md`.

**Housekeeping, 2026-07-29 — no firmware change.** `analysis-2020accord/eps_lkas_chain_model.py` was
distilled 4,709→2,200 lines: its comments/docstrings had grown into dated changelogs and multi-hundred-
line findings essays. Cut to comments ≤1 sentence, docstrings ≤1 paragraph; addresses/Q-format/confidence
tags kept. Verified byte-identical arithmetic (AST diff) and byte-identical self-check output before/after.
No investigation conclusion below changed. See `memory/feedback-golden-model-distilled-keep-terse.md` and
`docs/HANDOFF-2026-07-29-golden-model-distillation.md`.

---

## On the car right now

**V56** = V55 + the `0xC6AF0` mute (`0xC6AFC`/`0xC6AFE` 32768→0). Flashed and driven 2026-07-29,
route `24` — **16 segments, 15:43, the kit's first ROAD drive with a firmware probe.** Fault-free.

🛑 **RECOMMENDED: flash V55 back.** The mute **bought nothing** for the vibration, and the operator reports
degraded steering feel. Reverting costs nothing (existing, already-driven artifact) and restores a
known-good state. Full numbers in
`memory/reference-accord-v56-flashed-mute-is-null-and-costs-damping.md`; narrative in
`docs/HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md`.

| | V56 route 24 | V55 route 1c |
|---|---|---|
| 15-26 Hz engaged/disengaged, speed-matched creep, full 16-bit CAN `0x18F` | **786×** (1.28e8 / 1.63e5) | 877× |
| — independent replication, 0.5-3.0 m/s, N=256 | 1,878× torque / 5,524× rate | 20,047× / 23,494× |
| absolute engaged 15-27 Hz power (counts²) | 7.66e4 | 1.94e5 · R13 6.59e4 |
| command's in-band content (probe field, matched creep) | 7.45e-2 level² | 3.94e-2 — **went UP ~1.9×** |
| command transition rate, matched creep | 23.9/s | 21.9/s |

⇒ pre-registered **outcome (iii)**, confirmed two independent ways. 🛑 **`gp-0x6ad4` / `FUN_0003a382` is
ELIMINATED as the driver of the 20-25 Hz mode** — V56 killed all three branches at once via the output
bound, where V43/V46/V48A each killed one. ⚠ Note the engaged/disengaged *ratio* spread across builds is
driven by the **disengaged** baseline (parking-lot idle), not the engaged level — quote the absolute
engaged power alongside it. And outcome (ii) is **not cleanly resolvable**: V56's command content rose,
but its windows are 0.5° steering vs V55's 26.9°, n=57 vs 19.

★★ **The few-Hz resonance is WHEEL ORDER 1 — a TYRE problem, not something V56 created.** Identified on
the independent `STEER_ANGLE_RATE` channel (`0x18F` bytes[2:4] BE signed × **−0.1** deg/s — the 10× finer
copy of the field openpilot reads at `0x14A[2:4]`, r = −0.9473):

```
f = 0.4890·v − 0.186 Hz      r = +0.9970    rms residual 0.037 Hz    intercept ≈ 0 (through the origin)
implied rolling circumference 2.088 m   (p10-p90 2.076-2.099)
# a 2020 Accord on 235/45R18 is 2.05-2.11 m  =>  ONE line per wheel revolution
```

| v (m/s) | n | f measured | v / 2.08 predicted | v/f (m) |
|---|---|---|---|---|
| 16.5-18.0 | 32 | 8.496 | 8.568 | 2.092 |
| 18.0-19.5 | 12 | 8.691 | 8.687 | 2.083 |
| 19.5-21.0 | 11 | 9.766 | 9.772 | 2.084 |

⇒ **tyre/wheel imbalance, non-uniformity or runout.** A road input, present regardless of firmware, and
invisible on every prior route because at 1.5 m/s wheel order 1 is 0.7 Hz, not 8.7. Burst-like:
worst window Q=55, **1608× the local floor**, 77× in power. ⇒ **Get a wheel balance / road-force check.**
The 2.088 m fit is specific enough to test physically.

★ **AND there is a separate genuine FIXED ~7-8 Hz resonance, on every build** — V56 7.81, V55 7.03,
V54 8.59, V53 7.03, R13 7.42 Hz at creep, where wheel order is only 0.3-0.8 Hz, so it cannot be wheel
order. Both are visible simultaneously in the seg-11 high-resolution spectrum (7.275/7.52/7.715 Hz **and**
the 9.766 Hz wheel-order line at 20.3 m/s). **At 15-20 m/s the wheel-order line sweeps UP THROUGH that
resonance** — the classic recipe for an intermittent low-frequency shake that only ever appears on the
road. That is the most likely thing the operator felt.

⚠ **"V56 removed damping" is NOT supported by the data — but it is NOT closable either.** Matched creep
(0.4-3.0 m/s), engaged + hands-off, torsion bar, 1-10 Hz band variance: **V56 9.75e3 vs V55 5.70e4
(0.17×), V53 9.68e4 (0.10×), R13 4.03e4 (0.24×), V54 7.38e3 (1.32×)**; angle-controlled (|ang|<5°, only
R13 survives) V56/R13 = 0.64×. Envelope-decay Q: V56 **3.6**, V55 7.4, V53 14.1, V54 4.8, R13 3.5 — V56 is
not the least damped. 🛑 **But all of that is at CREEP, and the operator felt it at ROAD speed, where no
prior build has any data at all.** Do not use the creep table to dismiss the report. GATE 2 stays open
exactly where it matters.

⚠ **Control gaps:** V56 has **zero disengaged windows above 3 m/s** — the whole road drive was engaged —
and **no pre-V56 road baseline exists** (route `13` has only segments 12-15 on disk, creep, vEgo max
2.73 m/s, 250 m total).

🛑 **A 50% partial restore (`Y = 16384`) is NOT a candidate.** The lane at 100% (V55) and 0% (V56)
produced the same 21 Hz, so intermediate authority is bounded between two agreeing measurements. It is a
partial revert wearing a candidate's clothes.

**V55** (the revert target) = V38 calibration + `0xC62EA` 320→0 + the dual probe on `0x14A` byte4
(bit7 = damper variant index ≥ 10; bits 6:3 = 4-bit `gp-0x6b98` motor command). Driven 2026-07-28
(route `1c`, 113 s parking lot), fault-free. `bit7 = 1` in 11,128/11,128 and again in 94,369/94,369 on
route `24`.

🛑 **THE PROBE UNDER-RANGES — it is a ~1.5-bit channel, and the record must say so next to every number.**
On the road drive, engaged + hands-off, **99.2% of frames sit in two adjacent levels** (field 7 = 59.0%,
field 8 = 40.1%); route-wide it is 94.0% (field 7 = 52.0%, 8 = 42.1%). ⇒ `gp-0x6b98` lives inside **±512**
while one LSB is **512 counts**. Rail occupancy **0.10% low / 0.00% high**; **field 15 never occurs in
943 s**; `field == 0` in **0** samples (liveness guard intact). We guarded against railing and got the
opposite. ⚠ **It is an amplitude comparator but a usable SPECTRAL probe** — that distinction is what makes
the partition answerable at all, and the sections below split the claims accordingly.

⚠ **Correction of record:** *"Probe live: 10 distinct field values, 100% interior, no rails"* is true of
the **whole drive** but **false of the analysed engaged subset**, which has **4 distinct values, 93.2% in
fields 7-8 — effective 1.5 bits.** Always state the subset.
- **Survives:** presence and frequency (a comparator preserves zero-crossing timing), and the transition
  rate as a robust statistic. Independent check: on V56 engaged+hands-off the **35-45 Hz control band sits
  BELOW the uniform-quantiser floor** (Δ²/12/50 Hz = 1.667e-3 level²/Hz) while **18-27 Hz sits 3.6× above
  it at creep** (peak 23.24 Hz, 61× floor). A control band below floor with the mode band well above it is
  a real detection, not quantiser noise.
- ⚠ **KEEP but RESTATE — `"120.5 counts at 21 Hz"` is a real detection, not an artifact.** Encoder gain is
  **1.006 (unbiased)**, and the quantisation false-positive floor at route 1c's actual dither (224-336
  counts rms) is **10-18 counts** ⇒ 120 counts is **7-12× above floor**. The "less than ¼ of one LSB"
  objection is **wrong**: averaging K segments over 512 bins recovers far below the step size when dither
  is present — the floor is set by the noise, not the LSB. Two required restatements: **(a) 120.5 is a
  bin-RMS, not an amplitude** (÷0.5766 → ≈209 counts amplitude); **(b) 🛑 if openpilot's "31.7 counts" was
  an amplitude and 120.5 a bin-RMS, the ratio is 66×, not 38×** — the record must state which estimator
  each used. **Unresolved.** Either way the correction runs *against* openpilot as the source.
  ⚠ The **railed** subset figure (105.8 counts) is 7.9 s non-contiguous ⇒ ≤1 segment, and its coherence
  0.66 is at/below its own threshold. **Do not lean on it.**
- ⚠ **UNCONFIRMED, not refuted:** *"flat H1 0.192 → 0.216."* **Quantisation is exonerated by
  construction** — the encoder preserves H1's *shape* to a few percent even for a true 0.93 Hz pole, and
  coherence bias is **downward**, so 0.93 is a lower bound. The real problem is dof: at ±19.6% a pole at
  fc=16.8 Hz and flat are statistically indistinguishable, and the 0.192→0.216 rise is **not
  significant**. ⇒ **The `0xC646C` elimination STANDS on its structural leg** (0 matches across all 468
  instructions of `FUN_0003a382`); the transfer argument is corroborating only. **No candidate returns to
  scope.**
- **Re-scale on any future build — and mind the sentinel trap:**
  🛑 **`SHIFT = 6` with `OFFSET = 8` COLLIDES WITH THE `field == 0` LIVENESS SENTINEL** — `(x>>6)+8 == 0`
  for x ∈ [−512,−449], which would silently destroy the guard that already saved this kit once (a V54
  image decoding as a plausible V55 reading). **Offset must go to 9 whenever shift goes to 6.**
  **Recommended: `SHIFT = 7`, `OFFSET = 8`** (128 counts/level, 4× finer) — the only option whose railing
  can be **bounded from data** (must-rail 0.13%, may-rail ≤0.83% on route 24 engaged+hands-off). It also
  preserves enough range to measure the tails, so `SHIFT = 6 / OFFSET = 9` can be chosen on data next time.
- The full 16-bit CAN `0x18F` sensor figures are **unaffected** — keep sensor-side and command-side
  numbers rigorously separate.
- 🛑 **`rlog-tools/decode_v55_motorcmd.py` has the wrong guard** — it warns only when rails exceed 50% and
  prescribes "rebuild with `CMD_SHIFT=10`", i.e. **the wrong direction**, guarding a failure that never
  occurs while silent on the one that always does. Its `band_power(nfft=256, hop=64)` is 75% overlap, so
  the printed `K` is ~4× the true dof. **Fixed 2026-07-29.**

**V54** (previous) = the 5-bit `gp-0x6966` authority probe. Its result stands: authority ≡ 0 by design on
V31+, so the `0xC6AF0` LERP selects unity in 100% of normal operation. **V53** before it = FOURFRAME2 cave
+ `0xC62EA` 320→0; steer-to-zero confirmed. Both superseded as flash candidates.

⚠ The `0x14A` byte4 bits 7:3 piggyback is now proven across **three** flashes (V54, V55, V56). Use it for all
future firmware telemetry; do not build another new-mailbox channel.

✅ **Steer-to-zero WORKS — confirmed from the rlog, not just by report.** Route `1a` segment 0:
`STEER_STATUS = 0` in **5,995/5,995** frames (ST=3 never fires anywhere) and **226 frames of
`STEER_CONTROL_ACTIVE = 1` below 5 km/h**, a cell that is structurally empty on V38. The §7 prediction
from the previous handoff held exactly.

🛑 **The four-frame telemetry (V53/FOURFRAME2) never arrived** — zero frames of `0x6A0`-`0x6A3` across
301,824 CAN frames. That null remains uninterpretable and the boxed rule in `BUILD-LINEAGE.md` Part 1
stands: **do not build another new-mailbox channel.** Use the `0x14A` piggyback, which now has an on-car
proof rather than an argument.

⚠ **V54 does NOT carry the V42 ratchet fix** (`0x454FE` is stock `0x65BA`). The state-4 governor
substitution block is live on the car.

⚠ An rlog **cannot** identify which build is flashed from the version string — every modified build
reports `fw='39990-TVA,A160'`. (It *can* now be identified behaviourally: ST=3 never firing ⇒ V53+.)

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **V55** | the **revert target** — probe intact, no mute | ✅ built, driven, fault-free. **Flash this to undo V56.** SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| **V57** | V55 + the **`0xC646C` decoupling** + the **DEADBAND-GATE PROBE** | ✅ **BUILT 2026-07-29, UNFLASHED.** (A) `0x2A1F0` disp `0x746C`→`0x7CD0`; `0xC6CD0`←3564 (private); `0xC646C`→891 (stock). (B) V55's cave payload REPLACED at the same base/hook/extent (68 B): `0x14A` byte4 **bit7=liveness, bit6=(gp-0x6806==0) EXACT gate test, bit5=(gp-0x69b0!=0), bit4=(gp-0x6b30==0), bit3=(gp-0x6b30<0)**. 58 bytes off V55, 88 off V38, 50/50 CRC, RWD round-trip gated, cave re-decoded from the built image. 🛑 (A) is a correctness fix, expected NULL for the grinding **and expected null for manual feel** (the operator has driven 891/1782/3564 and reports no difference; disengaged, only the feedback readers are live). (B) closes the **parity hole** in the deadband elimination. ⚠ code in the 1 kHz TX path — higher risk class than a cal-only build. RWD SHA `6263acf185a00849c4dd0556f15bd834faf63a9795c610228d83d64eadb5dd3b` |
| ~~**V56**~~ | V55 + the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED 2026-07-29.** Null for the 21 Hz, costs damping, adds an 8.69 Hz mode. Do not re-flash |
| `0x2a1ee` retarget → `0xC6CD0` | the `0xC646C` decoupling — correctness fix | verified safe + byte-minimal, **unbuilt**. Will NOT fix the vibration (see below) |
| `0xC6372` / `0xC636E` | the untested wideband assist EMAs | candidate #2, **needs its own GATE 2 pass** first |
| FOURFRAME2 | telemetry on IDs `0x6A0`-`0x6A3` | **retired** — the channel is unobservable |
| V49, V50, V51P, V52, VCANTX-TEST | superseded or blocked | see `docs/BUILD-LINEAGE.md` |

```
_v56_plain_image.bin  SHA 8c5c8a73425bf269c03b2e93144a7b8340983e5d873d70ea6009c0e68eacc7a0
V56 .rwd              SHA ffccf6e779498379e5d31326ba5bd7ed68da189d362b5f7ed925499df68343f4
_v55_plain_image.bin  SHA 9ed79e68e1d02362efff5262a9f142e6e1a6596104d800d5fd6a95cef86e576c  (ON THE CAR)
V55 .rwd              SHA 2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b
```

**V56 is exactly 6 bytes off V55** — and only **2** of them are calibration: `32768 = 00 80`
little-endian, so muting to 0 changes only the *high* byte of each halfword. 84 bytes off V38.
50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the readback. The
point-count word and the whole X row are asserted unchanged, `Y[2..4]` asserted stock, V55's cave and
hook byte-identical. Decoder unchanged: `rlog-tools/decode_v55_motorcmd.py`.

**`build_v56_tva.py` is a POST-PROCESSOR over `_v55_plain_image.bin`** — it transcribes nothing from V55,
not the cave, not the hook, not the encoders. Same principle V53 used with FOURFRAME2's cave.

⚠ **`V53.assert_stock_cals()` correctly refused this edit** ("the `0xC6AF0` LERP moved — its edit
direction is UNRESOLVED"). V54's drive resolved the direction. **Do not weaken that shared guard** —
five builders depend on it. V56 runs the *unmodified* guard against the pre-edit V55 source and
re-expands its other two components against the post-edit image.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## ★★ RESOLVED 2026-07-28 — authority `gp-0x6966` is ≡ 0 by design on V31+

**`gp-0x6966` is not a speed-scheduled "steering authority" gain.** It is the **soft-EME wind-up
integrator's magnitude**:

```
gp-0x3570 += (command − bound), clamped ±(cal 0xC61DC = 30720)   [anti-windup integrator]
gp-0x6966  = |gp-0x3570 >> 15| × (cal 0xC61DA = 1092) >> 10      [max (1092×30720)>>10 = 32760 ≈ Q15 1.0]
```

The bound is a 3-way gated MAX/MIN of corridor (driver-override), boost (angular rate) and an IIR on
column velocity. **No arm is vehicle road speed** — confirmed by a hit-count sweep of `FUN_00042af8` for
`gp-0x6a5e`/`0x6a62`/`0x6a64` and cal `0xC6316` (0 relevant hits).

**Why it reads zero on the flashed build — verified in `_v54_plain_image.bin`, not argued:**

```
boost LERP Y   stock: 0 / 1536 / 2048      V38 & V54: 5120 / 5120 / 5120
float twin     stock: 0.0 / 1.5 / 2.0      V54:       5.0 / 5.0 / 5.0
```

On **stock**, `Y[0] = 0`: at low angular rate the boost arm vanishes, the bound collapses, the integrator
winds — that is exactly the V30 hard-hands-off-turn EME event. On **V31+ (incl. V38/V54)** the boost arm
is floored and is ungated by driver input, so the bound cannot collapse, `(command − bound)` stays
negative, and the integrator sits pinned. **The V31 fixpoint is self-stable and attracting.**

⇒ **On-car measurement, route `1b`: `wire = 1` in 5,989/5,989 frames ⇒ `gp-0x6966` ∈ [0,127]**, zero
variation, i.e. **0.39% of saturation** — including 17% of requesting frames at openpilot's ±4096 rail.
Reaching the first LERP knee needs `|gp-0x3570>>15| ≥ 3073` against an observed **≤ 119**.

**This converts V31 from "argued, with a residual margin caveat" into on-car evidence under railed
command.** That is the real contribution of the V54 drive.

⚠ **One record clarification, and one genuine open item.**

*Clarification (NOT a correction to the V31 memory):* that memory's boost floor of **4096 is correct for
V31**. **V38 raised it to 5120**, and the golden model already carries both
(`Calibration.for_build("V31").boost_floor == 4096`, `("V38") == 5120`). The car runs V38+, so 5120 is
the live value. Do not "fix" the V31 memory.

*Genuine open item:* that memory's residual-margin arithmetic (*"COMP ceiling 2560 `0xC67D8` + governed
clamp 1024 `0xC61B4` = 3584 vs 4096"*) **does not reconcile with the image** — `0xC67D8` reads 512 and
`0xC61B4` reads 2048 in V54. Those may be LERP tables where a prose address names one element; the margin
must be **re-derived** before anyone quotes it again. It no longer blocks anything, because V54 measured
the margin directly on-car.

### Verified chain (Python byte reads, independent of Ghidra and of any subagent)

```
0x3a632  0x5fe4 0x969b   ld.hu -0x6966[gp], r11    <- the ONE command-path reader
0x3a636  0x7e25 0x7af0   movea 0x7af0, tp, r15     <- tp=0xBF000 -> 0xC6AF0, 4 bytes later
0x432c8  0x6f64 0x969a   st.h  r13, -0x6966[gp]    <- st.h => 16-bit; the probe's ld.hu width is correct
0xC6AF0  X = 0 / 3277 / 3604 / 19661 / 32768   Y = 32768 / 32768 / 0 / 0 / 0
```

**Channel audit (this session, against the fork on disk):**

| byte | DBC content | openpilot reads it? | free bits |
|---|---|---|---|
| `0x14A` byte4 | bits 2:0 = `STEER_SENSOR_STATUS_1/2/3` (live in firmware) | **no** (only bytes 0-3) | **5** @100 Hz |
| `0x18F` byte5 | bits 3:0 = `STEER_CONFIG_INDEX`; **bits 5:4 LIVE** (`gp-0x6880 & 3`, packer `0x55CAE`) | no | 2 safe; no hook located |
| `0x1AB` byte0 | bit7 `CONFIG_VALID`, bit3, bits 1:0 = `MOTOR_TORQUE[9:8]` | no (427 never parsed) | 4, non-contiguous, 48.7 Hz |

Panda Honda RX checks are `0x1A6`, `0x296`, `0x158`, `0x17C`, `0x326`, `0x1BE` — **none of the three**.
⚠ opendbc *does* verify Honda checksums (`opendbc/can/dbc.py`); a bad one drops `can_valid`, which is a
**disengage**. Any piggyback must be written before the checksum call.

---

## The two open workstreams

### A. The vibration — ★★ still open. Suspect moved to the **ANGLE-RATE** domain, 2026-07-29

★★ **THE TOP CANDIDATE IS NOW `gp-0x6bbe`'s ANGLE-RATE TRIBUTARY — the first ever outside the torque
domain.** `FUN_00034a72` (boost) reads the steering **angle rate** `gp-0x6a56` **unfiltered** at
`0x34AB8`/`0x34E8E` (byte-verified by the lead after two subagents disagreed) as one side of an FSM-result
subtraction, clamped ±12000, then scaled by **two speed-indexed LERPs** (`gp-0x6a5e` avg, `gp-0x6a62` max).

- `gp-0x6a56` is what the EPS **transmits** as `STEER_ANGLE_RATE` — `0x14A[2:3]` (via `gp-0x69ea`, `>>3`)
  and the 10× finer `0x18F[2:3]`. **opendbc ground truth, not inference** — the only control-path signal
  in this firmware with an external anchor.
- The mode measures **996× on `STEER_ANGLE_RATE`** vs **877× on the torsion bar** (route `1c`). *The rate
  channel carries it more strongly than torque does.*
- ⇒ **The rate path BYPASSES the torque EMA**, so the recorded −1.29 dB/−14.91 dB figures characterise
  only the torque tributary, and **the unresolved `FUN_00022ca0` task rate matters far less than it
  appeared** — an unfiltered path passes 21 Hz either way.

🛑🛑 **GATE 2 ANSWERED, AND IT ANSWERED *AGAINST* CUTTING THE LANE. THE LEVER INVERTS.**
An earlier pass this same session called `gp-0x6bbe` "same-signed, reinforcing" off the torque-EMA
framing. A full disassembly re-trace **corrects that**: the torque EMA is a **multiplicative amplitude
scale** (`term3 = (term2 * blendedMagnitude) >> 14` @`0x34ffa`), not an additive branch, and the core
signal is

```
0x34e96  sub r6,r28        rate_error = baseline - angle_rate_raw
```

All downstream multipliers are non-negative and polarity `gp-0x6752` = +1, so with `baseline` slow at
22 Hz this is `gp-0x6bbe ≈ −(gain)·angle_rate` — **viscous DAMPING on angle rate.**

⇒ **Cutting or muting this lane would REMOVE damping and would likely make the grinding WORSE.** That is
the V56 error exactly, one build later. **The interesting direction is RAISING the gain to ADD damping at
22 Hz** — cleanest single-point lever `K1` @ `0xD200C` = 43 (Q7, pointer base `0xCA324` has 1 hit
image-wide). Three more candidates in `accord-angle-rate-lane-gp6bbe-top-candidate.md`; none appears in
any build script, and all avoid V44/V47's specific bytes inside the shared `DAMP_BLOCK`.

⚠ **[INFERRED, moderate-high confidence, NOT time-domain simulated.]** The verdict rests on `baseline`
being slow at 22 Hz. 🛑 **Certify the sign by simulation before any build** — if `baseline` carries 22 Hz
content with the wrong phase, raising the gain makes it worse. Nothing gets built here until that runs.

⚠ Also corrected: **speedLERP2 (`0xD20C0`) is FLAT** — five entries of 512, a fixed ±512 clamp dressed as
a table. And **speedLERP1 (`0xD2834`) is a broad hump peaking at 40 km/h** (0.55-0.62 at creep, 0.61-0.55
on road), *not* a monotonic speed rise — so it does not by itself explain `f = 0.177·v + 20.48`.

⚠ **Task-rate status:** `FUN_00022ca0` is **not pinned**, bounds 100-1000 Hz, but weight shifted to 1 kHz —
the RTOS task table (base `0xBB858`, 7×48-byte records; `FUN_0002214a` @`0xBB928`, `FUN_00022ca0`
@`0xBB9E8`) encodes **no period or divisor field**, there is **no in-task divider**, and **`OSTM1` is
never configured anywhere in the image**. Three negatives, no positive evidence for a divider.

#### Historical framing — `gp-0x6ad4` ELIMINATED 2026-07-29

🛑 **STOP CALLING IT "21 Hz".** Presence-tested, steady-speed, pooled across builds:
`f = 0.177·v + 20.48` (r = +0.650) — **24.61 Hz at 19-21 m/s, 25.00 Hz at 21.3 m/s**, in the worst events a
cluster of extremely narrow lines (24.12/24.32/24.56/24.85/25.15 Hz, **Q = 160-228** at df = 0.0488 Hz).
The recorded 20.12 @1.0 m/s → 21.68 @4.0 now extends to 25.0 @21.3. It is a **20-25 Hz** mode.
⚠ It is **not** wheel order (the implied circumference would span 0.06-0.84 m).

🛑 **NEW CONFOUNDER — steering angle moves the mode ~2 Hz, within a single firmware.** V56, creep, engaged,
hands-off, speed held: |ang| 0-2° → **23.44 Hz** (n=18); 2-5° → 22.66 (n=9); 5-10° → 21.48 (n=17);
10-20° → 21.48 (n=13). V56's creep data is near-straight (0.5° median, road entry/exit) while **every**
prior build's creep data is wheel-turned (V55 26.9°, V53 42.2°, V54 17.6°, R13 12.6°). ⇒ the apparent
+2 Hz on V56 at matched *speed* is **fully confounded with angle** and cannot be attributed to firmware,
**and the historical speed curve is angle-contaminated too.** Condition on angle from now on.

🛑 **Read this before the 2026-07-28 material below.** V56's branch-agnostic mute of `gp-0x6ad4` changed
**neither** the vibration (786× vs V55's 877×) **nor** the command's 21 Hz. The prime suspect named
throughout the rest of this section is **dead**. What remains true: the mode is physical, hands-off,
engagement-dependent, moves with speed, and is internal to the EPS. What is now **provisional**: every
command-side *amplitude*, because the probe under-ranges to ~1 bit (see "On the car right now").

⇒ The search moves to the **other eight aggregator lanes**, all confirmed additive at `FUN_0003aa2c`.

★ **New symptom introduced by V56:** an intermittent, sharp **8.69 Hz** line at 15-20 m/s, engaged +
hands-off — 1.18e8, 6.7× its spectral neighbours, absent from every disengaged spectrum. Expected to
disappear on reverting to V55; **confirm that on the next drive**, because it is also the cleanest
available test that the mute was genuinely live on the car.

#### Historical framing from 2026-07-28 — the suspect it names is now eliminated

**The V55 drive (route `1c`) settled the two biggest open questions.** Full numbers in
`memory/reference-accord-v55-flashed-oscillation-is-internal.md`.

1. **The vibration is unambiguous and physical.** 20.90 Hz; **877×** engaged/disengaged on the torsion
   bar and **996×** on `STEER_ANGLE_RATE` — a *different physical quantity in the same CAN message*, so
   it is not a torque-sensor artifact. It is **hands-OFF**: on `1b`, engaged+hands-off carries **26×**
   the power of engaged+hands-on.
2. **The ~21 Hz IS in `gp-0x6b98`**, the final merged command, in the same 0.195 Hz bin as the sensor
   (coherence 0.93). **Route `1b` is a clean null control** — V54's constant field gives exactly zero
   command power, so the pipeline cannot manufacture the peak.
3. ★★ **openpilot is NOT the source.**
   ```python
   DC  = 4.0 * 3564 / 32768        # setpoint x(-4) then Q15 gain 0xC646C   = 0.4351
   IIR = 1/sqrt(1 + (21/4.97)**2)  # gp-0x3d3c pole 0.96875 @1kHz            = 0.2314
   31.7 * DC * IIR  ==   3.2       # what the LKAS lane can deliver from openpilot's 21 Hz
   31.7 * DC        ==  13.8       # even with the low-pass DELETED
   # MEASURED in gp-0x6b98:  120.5 counts   -> 38x over budget, 8.7x even unfiltered
   ```
   **And while openpilot is RAILED its own 21 Hz content is exactly 0.0, yet the command still carries
   105.8 counts at 21 Hz.** The loop closes inside the EPS, downstream of the LKAS lane's low-pass.
4. ★ **The carrier is UNFILTERED.** Sensor→command transfer (H1, 9 independent segments) is **flat:
   0.192 @1 Hz → 0.216 @21 Hz**, with only ~28° of phase rotation across the band. **A lane behind a
   pole cannot produce that** — which is what eliminates the entire `0xC646C` reader set.
5. **Damper bit7 = 1** in 11,128/11,128 ⇒ V44/V47 hit the LIVE tables ⇒ the missing-damping hypothesis
   is genuinely falsified. **Thread closed.**

🛑 **Direction is still not proven.** H1 in closed loop with no external excitation cannot separate
plant from controller, so the **damping sign remains open**. That is GATE 2 for V56.

#### Historical framing kept below for context

**What is established:**
- **The mode MOVES with speed** (route `1b` vs `1a`, Welch, 0.195 Hz resolution — 8 bins apart, resolved,
  not noise): **20.12 Hz at 1.0 m/s mean → 21.68 Hz at 4.0 m/s mean.** Q ≈ 34 and ≈ 22 respectively.
  ⇒ **Any openpilot notch must be wide or speed-scheduled; a fixed 21 Hz notch misses at creep.**
  ⇒ It also argues against a fixed digital artifact pinned at 21.09 Hz. It does **not** resolve the
  21.09-vs-78.91 aliasing question — both aliases shift together.
- **It requires the EPS to be ACTIVELY APPLYING LKAS torque.** Route 13 three-way split: openpilot off →
  nothing; commanding *harder* into low-speed lockout → nothing (1.33×); commanding **and applying** →
  **14,750×**. Reconfirmed on route `1b`: **771×** engaged/disengaged in the 15-26 Hz band.
- ★ **It reproduces at parking-lot creep** — route `1b` never exceeded **1.50 m/s (3.4 mph)**. This is the
  cell V53's `0xC62EA` unlock made reachable, previously structurally empty. Onset is sharp at engagement
  and collapses at disengagement.
- ★ **Saturating the command SUPPRESSES it, controlling for speed.** At 1.2-1.6 m/s: unsaturated
  `1.22e9` → railed(>50%) `8.6e6`, a **141× collapse**. At 0.8-1.2 m/s, 8.8×. Consistent with a loop that
  opens at the rail — **but a mechanical operating-point shift (backlash/stiction take-up under high
  torque) predicts the same observation, and this data cannot separate the two.**
- The mode **is** present in the openpilot command at the same peak bin, but at only **0.091%** of command
  power. Coherence is symmetric and still does not establish direction.

**Prime suspect:** the `FUN_0003a382` → `gp-0x6ad4` lane — an unfiltered, proportional-dominated feedback
of (sensor − reference model) straight into the actuator, with no band-limit at 20 Hz, whose output bound
is gated by authority `gp-0x6966` via the LERP at `0xC6AF0`.

#### ✅ The `0xC6AF0` direction is now MEASURED, not argued

Authority is ≡ 0 on this build (section above), and 0 sits inside the table's **first flat segment**:

- **`Y = 32768` (unity) is selected in 100% of normal operation.** The residual lane runs at its **full
  output bound** always — including throughout the vibration.
- The derate never engages, because engaging it needs an EME wind-up that V31's boost floor made
  unreachable.
- ⇒ **"keep-live" is a no-op** — the lane is already live. **Mute (`Y[0]`, `Y[1]` → 0) is the only
  meaningful edit**, and the measurement licenses it.
- A genuine safety point in the mute's favour: zeroing `Y[0]/Y[1]` **does not disable a live protection**,
  because the derate is currently never invoked — and in a hypothetical wind-up it would be *more*
  conservative, not less.

🛑 **STILL OPEN — GATE 2.** The measurement proves the lane is **live**; it does **not** prove it is the
**culprit**. The lane's damping-vs-anti-damping sign at 20 Hz remains undetermined ("proportional-dominated
8-10:1, net phase −3.3° to −5.4°… a plant-transfer-function question"). Muting a possibly-*damping* term
on the 1 kHz path is a real closed-loop risk. **Do not treat "unblocked" as "cleared to flash."**

### B. Low-speed steer lockout — ✅ CLOSED, flashed and confirmed 2026-07-27

`0xC62EA` = 320 ≈ 5 km/h is the LO half of a two-sided window against voted speed. Failing it sets
`STEER_STATUS=3`, which zeroes `STEER_CONTROL_ACTIVE` and kills the authority ramp. **V53 sets it to 0**
(operator instruction). One reader, no float mirror, in the cal block every build already touches.

**Why 0 rather than the previously-suggested 64:** stock *already* unlocks true standstill — `gp-0x68b3`
(the window bypass) is written only when `gp-0x6a62 == 0`, i.e. exactly 0. Stock therefore permits 0 km/h
and forbids 1–319 counts. Choosing 0 removes that discontinuity instead of moving it.

**Safety re-verified at build time**, in Python, independently of Ghidra:
- **Exactly one reader image-wide**, both V850E2 encodings swept over `[0x13000,0xC4FFC)`: the `disp|1`
  halfword `0x72EB` occurs once, at `0x28EBE` — the displacement of `ld.hu 0x72ea[tp],lp` @`0x28EBC`. The
  single bare-`0x72EA` hit is at **odd** address `0x21167`, so it cannot be an operand.
- **No LERP masquerade:** nearest `movea …,tp,rX` table base below the lever is `0x7010`, a 4-point record
  (X = 0/640/3200/6400) ending ≥ 0x2DA bytes short.
- **SNA detection intact** — the `0x7FFF` sentinel still fails the untouched HI bound `0xC62E8` = 12800.
- **`0xC62EE` left stock** (asserted). It is a permissive on a CAN-commanded assist-shutdown task, not a
  lockout, and must never be raised.

**On-car result 2026-07-27 (route `1a`, 58 s, 301,824 CAN frames):** ST=3 never fires; 226 frames of
`STEER_CONTROL_ACTIVE=1` below 5 km/h with `TORQUE_REQUEST=1` and `|torque|>50` in 224 of them. Carried
forward into V54 unchanged.

✅ **The engaged-at-low-speed cell has now been mined (2026-07-28).** Route `1b` is *entirely* inside it
(vEgo max 1.50 m/s, 49% engaged, 2,231 carState frames engaged below 5 km/h). **The vibration reproduces
there**, 771× engaged/disengaged — see workstream A. The collinearity break is claimed.

openpilot is not the obstacle (`CP.minSteerSpeed = 0.0`), but the StarPilot fork runs
`steerAtStandstill = False`, so at a dead stop openpilot still will not command. The real behaviour window
is roughly 0.1–3 mph: creep, parking lots, stop-and-go.

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction, 2026-07-28. The long-running
"openpilot-side 21 Hz notch" recommendation is **retired** — the fix must be firmware-side. openpilot
remains in scope as a *measurement instrument* (rlogs, CAN decode, correlation) only. See
`memory/feedback-no-openpilot-side-modifications.md`.

1. 🛑 **Flash V55 back.** V56 is falsified *and* it degraded the car. V55 is already built, already driven,
   fault-free, and keeps the probe. Straight revert, not a new experiment. **Do this before V57** — V57 is
   cut from V55, so flashing it would revert the mute *and* change feedback gains at once, confounding
   feel assessment and forfeiting the cleanest test that V56's mute was live (the 8.69 Hz line should
   vanish on V55).
2. ★★ **Characterise the `gp-0x6bbe` angle-rate tributary** (workstream A above) — end-to-end gain at
   20-25 Hz, the two speed-LERP tables byte-read at creep *and* road speed, and the **sign/phase at
   22 Hz**. That last one is GATE 2 and nothing gets built without it.
3. **The aggregator has ELEVEN summands, not 9.** Confirmed by full disassembly of `FUN_0003aa2c`
   (`0x3acc8`-`0x3ace6`), every one folded in by a plain `add`: `gp-0x6b62` (return-centre), `-0x6b4c`
   (LKAS), `-0x6ade` (feedforward, likely always 0), ~~`-0x6ad4`~~ (eliminated), `-0x6b26` (friction,
   driven by **motor** rate), `-0x6bbe` (boost), `-0x6bd0` (damping), `-0x6b86` (magnitude), **plus `r24`
   and `r26`** (the torque-RATE lanes, computed inline at `0x3aa9c`-`0x3ac58` — omitted from every prior
   list), plus `FUN_00036682`'s return. 🛑 **r24/r26 are already flashed and FALSIFIED** (V39, V42 ch.2) —
   a subagent re-proposed them as novel this session; check `BUILD-LINEAGE.md` first, every time.
3. **Re-scale the probe before the next telemetry build.** `SHIFT = 9` is ~6 bits too coarse for the
   observed ±512 range; use 6 or 7. Until then, treat every command-side amplitude in the record as void.
4. **Re-establish or retract the `0xC646C` elimination.** It rests on the flat-H1 result, which is now
   known to be a few-dof estimate through a 1-bit output. Either re-derive it on a re-scaled probe or
   demote it from "eliminated" to "not yet tested".
5. **`0xC6372`/`0xC636E`** — candidate #2, the only other lanes unattenuated at 21 Hz (−1.29 dB).
   🛑 **Needs its own GATE 2 pass first**: `gp-0x6bbe` is base power steering, and adding 60-73° of lag
   to the always-on assist loop is the **V48B brick class**. ⚠ V56 is now a cautionary precedent for
   muting a lane whose damping sign is unproven.
6. **The `0xC646C` decoupling** (`0x2a1ee` retarget → `0xC6CD0`) — build it as the **correctness fix** it
   is. ⚠ It will NOT fix the vibration: `FUN_0003a382` is not among the six readers.
7. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
8. **The take-over beep is closed and is not a firmware item** — `commIssue`/`selfdrivedLagging`
   softDisable under chronic device CPU load, with a clean CAN/EPS null. See
   `memory/accord-takeover-beep-is-openpilot-device-load.md`.

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** It will not — `gp-0x6966` is
wind-up-driven, not speed-driven, and V31's boost floor makes wind-up unreachable. Provoking it would
require the documented EME pattern (sustained hands-off hard turn), which V31 exists to prevent.

---

## Corrections of record still worth knowing

**New 2026-07-29 — the signal-identity audit. Several of these invalidate the *reasoning* behind flashed
builds; none of them change a measured on-car outcome.**
- 🛑★★ **`gp-0x6a5e`/`-0x6a62`/`-0x6a64` are VOTED VEHICLE SPEED.** Settled by fresh decompile of the voter
  `FUN_00041eec` (5 channels, validity window −6400..32000, closest-to-previous fallback; zero overlap
  with `gp-0x4f60`'s cluster). **Retire the "Sensor A" label — it was never a torque sensor.**
  ⇒ **The damper Factor C LERP indexes on it** (pointer chase byte-verified: `0xC9E9C+10*4` →
  `0x000D27BC`), X=(2240,3840,5120,8960) ≈ **35/60/80/140 km/h** ⇒ **`Y[0]=0` means "below ~35 km/h", not
  "hands-off"** ⇒ **V44 and V47 tested a mechanism that does not exist.** Results stand; rationale
  withdrawn. The "2240 counts driver torque" story is a **number collision** with the override curve's
  unrelated torque breakpoint. Invalid speed ⇒ the factor defaults to **unity**, not zero.
- ★★ **The driver-override curve is real and mapped** — `FUN_00028ea6` `0x29a74`, indexed by
  `gp-0x682f = |gp-0x4f60|>>5` with direction from `sign(gp-0x4f60)`; X=[70,72,78,80] Y=[254,234,12,0] ⇒
  **LKAS authority collapses 254→0 between raw torque 2240 and 3584.** This is the firmware behind the
  operator's *"significant driver torque in a direction kills the grinding"*. It explains the **kill, not
  the creation** — hands-off the curve is flat at 254. ⚠ The `0xC64B8` threshold branch is **dead** since
  V37 set it to `0xFF`.
- ⚠ **…but the bus carries PARITY, not the gate's test.** The packer does `andi 0x1, r15` (`0x55c7e`)
  while the gate tests **exact equality** (`cmp r0,r12 ; bne` @`0x2a1ba`/`0x2a1bc`). Four of the flag's
  eight live writers store a **register**, not a literal, so a value of 2 reads as bit0 = 0 while the gate
  is DISABLED — and a 0↔2 toggle at 22 Hz would be invisible (bit3 flat, zero transitions). Low
  probability, but the elimination rests on an argument at that last step. **V57's probe bit6 is the exact
  test and closes it.** Decoder: `rlog-tools/decode_v57_deadband.py`.
- 🛑 **`gp-0x6806` is ON THE BUS** — CAN `0x18F` byte4 bit3 = `STEER_CONTROL_ACTIVE` (packer
  `FUN_00055c42`, matches opendbc `BO_ 399`). Measured route 24: **==1 in 96.26%, TWO transitions in
  180 s** ⇒ the `0xC61B8` deadband + sign relay is **bypassed in steady engaged driving** and cannot be a
  20-25 Hz mechanism. **Before building against any internal flag, check whether it is already on the bus.**
- 🛑 **Split every `FUN_00028ea6` scan at `0x2a30d`.** `gp-0x6806` has **16 raw writers = 8 live + 8
  dead-echo**; `gp-0x6b30` has **4 refs = 2 live + 2 dead**. Everything above `0x2a30d` is the known-dead
  `FUN_0002a30e`/`FUN_0002a93a` copies. Two subagents drew wrong conclusions from unsplit scans.
- 🛑 **`gp-0x6ac0` is MOTOR resolver electrical rate, not steering-column rate.** Traced through CORDIC to
  the resolver sin/cos ADC channels; label earned, domain mislabelled. The **column** rate is `gp-0x6a56`,
  which is what both CAN frames actually carry.
- 🛑 **`STEER_WHEEL_ANGLE` is NOT a second angle** — `gp-0x69ec` and `gp-0x69ee` are written from the same
  register in every branch of their sole writer `FUN_00040a50`. Measured: bit-identical to `STEER_ANGLE`
  in **11,999/11,999** frames, twist exactly 0.00. There is **one** angle, transmitted twice.
- 🛑 **`reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md` is WRONG, not stale** — it
  searched for CAN ID `0x156`; this platform puts `STEERING_SENSORS` at `0x14A`. The EPS **does** own and
  transmit steering angle.
- **The real Main/Sub torque pair is INSIDE `gp-0x4f60`'s producer** — channel select `gp-0x4e3d ∈ {0,1}`
  (`FUN_0007f3f8` ch0, `FUN_00080a54` ch1), each with its own CORDIC and calibration, cross-channel drift
  integrator `gp-0x4f58`, DTC-gated failover. The firmware names them `KFC_STORQUE_0/1`. **Cannot chatter**
  — matured DTCs only, and recovery additionally gated on `gp-0x6b94 == 0`.
- ⚠ **`gp-0x6b86` is a PEAK-HOLD** ("keep unless bigger"), disasm-confirmed three ways. It converges to the
  envelope and does not reproduce instantaneous phase, so the recorded "−3.9 dB, #2 strongest carrier"
  ranking is invalid — that dB figure is the downstream IIR taken in isolation, applied to a waveform the
  hold has already destroyed. **Low priority as a 21 Hz carrier.**
- ⚠ **`FUN_0003a382`'s bias is a real continuous clamp**, not a 2-state ±8192 selector; and the
  authority-scale LERP indexed by `gp-0x69aa` is a **complete no-op** (every Y = 1024, fallback 1024).
  `gp-0x6ad6` has exactly **3 static references image-wide** — one write, two reads, both inside
  `FUN_0003a382` ⇒ the "hidden reference-model side-channel" hypothesis is **closed**, V56 tested the only
  exit door.



**New 2026-07-28 — four, all byte-verified:**
- 🛑 **`0xC63D2` is `6`, not `14`.** Read little-endian from `_v55_plain_image.bin` *and* stock `code.bin`
  (identical; no build touches it), confirmed three independent ways. `alpha = 6/1024` ⇒ **fc 0.933 Hz,
  −27.1 dB at 21 Hz**, not the recorded 2.18 Hz / −19.7 dB. The golden model had this right all along.
- 🛑 **LERP tables begin with a POINT-COUNT word.** `0xC6AF0` names the *table*; `Y[0]` is at
  **`0xC6AFC`** and `Y[1]` at **`0xC6AFE`**. Writing to `0xC6AF0` would clobber the count. Proved by the
  firmware's own `addi 0xc,r15,r13` / `addi 0x2,r15,ep` at `0x3a63a`/`0x3a63e`.
- 🛑 **`gp-0x67fe` is NOT an openpilot-engagement gate** — it is the EPS's own FOC/assist substate
  (`gp-0x6772 == 5 → 2`), measured by V31P at 1 in 100% of frames *including disengaged*. So
  `gp-0x6ad4` is live during manual driving, and muting it changes manual feel.
- 🛑 **V43/V46/V48A did not exonerate `FUN_0003a382`** — it has **three parallel branches** and each
  build attenuated exactly one (`0xC644A`→64 = −7.1 dB; `0xC6450`→32 = −12.6 dB; one carrier muted).
  Three nulls are precisely what you would predict. Only the `0xC6AF0` output-bound mute kills all three.
- ⚠ **V52C's null is weaker than it looks** — its EMA was `alpha = 74/1024` ⇒ **fc ≈ 12 Hz, only
  −6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the 21 Hz content; it did not remove it.

- **`0xC646C` is NOT "the LKAS authority gain."** It is the firmware's single shared Q15
  sensor-to-command-domain scale, with **6 readers across three subsystems**; two (`0x36686`, `0x3684a`)
  apply it to the **raw torsion-bar sensor** on a feedback path reaching the motor. Raising it for 4× LKAS
  authority silently raised those too. (Probably not the 21 Hz driver — that lane is low-passed at
  fc ≈ 2.2 Hz and clamped to 5% of aggregator range.)
- **The CAN-TX base tick is 100 Hz, not 62.5 Hz.**
- **The gateway per-ID whitelist is WEAKENED as an explanation.** `0x19F` is gated at its own request site
  (`0x5559E`), so it is not a clean control for "the gateway drops unknown IDs".
- **`gp-0x4f60` is Sensor-B (TAS) driver column torque** — not angular velocity, not vehicle speed.
- **The control task is ~1000 Hz** (confirmed two ways).
- **`FUN_00045608` is an authority-slot setter, not "motor off".** The governor **does** read vehicle
  speed (`0xC6316` = 640 ≈ 10 km/h, below which the slew limiter is bypassed).
- ⚠ **Flagged but NOT adopted:** two traces conclude `gp-0x6a5e`/`0x6a62`/`0x6a64` are voted **vehicle
  speed**, not voted torque. If true it reclassifies the V44/V47 damper result. Needs its own pass.
