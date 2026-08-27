# HANDOFF 2026-07-29 — V56 drive: the mute is null, the few-Hz shake is a TYRE, and the probe under-ranges

**Route `24`** (`75604b0a432fdc89_00000024--bc45926e80--0..15`), 16 segments, **15:43**, mixed road
driving up to 21.8 m/s. **The kit's first road drive carrying a firmware telemetry probe** — every prior
vibration route was parking-lot creep.

🛑 **READ §8 FIRST.** Two deep analysis passes landed after §§1-7 were drafted and **overturned two of
them.** §8 is authoritative wherever it conflicts. The two big reversals: the ~8.7 Hz line is **wheel
order 1 (a tyre), not a V56-induced resonance**, and §5's retraction of the command-side amplitude figure
plus its downgrade of the `0xC646C` elimination were both **over-corrections that are withdrawn**.

**Headline: revert to V55.** The `0xC6AF0` mute **bought nothing** for the 20-25 Hz mode — and the null is
a real, hard-won result: it eliminates an entire lane, branch-agnostically, that three previous builds had
only nibbled at. Revert because it gained nothing and the operator reports degraded feel, not because
"it removed damping" is proven — the data does not support that claim, and cannot test it at road speed.

---

## 1. The four questions this session was asked

| # | question | verdict |
|---|---|---|
| 1 | is the vibration fixed? | 🛑 **No.** 786× engaged/disengaged, matched creep (V55 877×); replicated 1,878×/5,524× |
| 2 | did we remove damping / is there new few-Hz resonance? | ★★ **The few-Hz shake is WHEEL ORDER 1 — a tyre**, `f = 0.489·v − 0.186` through the origin, circumference **2.088 m** (§8.1). "V56 removed damping" is **unsupported by the data but not closable** — no prior build has road-speed data |
| 3 | why does openpilot beep to take over? | ✅ **`commIssue`+`selfdrivedLagging` softDisable under chronic device CPU load.** Clean CAN/EPS null |
| 4 | are we accounting for seeing only a few bits of the value? | 🛑 **No — it is a ~1.5-bit channel.** But the audit **upheld** the conclusions: quantisation is exonerated by construction; three restatements needed, not retractions (§8.3) |

---

## 2. The vibration — outcome (iii), the lane is eliminated

V56 = V55 + `0xC6AFC`/`0xC6AFE` 32768→0, which zeroes the output bound of `gp-0x6ad4` unconditionally.
Because the LERP result is a Q15 multiplier on the ceiling clamping the lane's **final combined value**,
the mute is **branch-agnostic** — unlike V43 (`0xC644A`→64), V46 (`0xC6450`→32) and V48A, which each
attenuated one branch and were each null.

Speed-matched creep (vEgo ≤ 1.6 m/s), engaged + hands-off, **full 16-bit** CAN `0x18F` bytes 0-1 BE
signed. Welch, NFFT=512, contiguous runs only:

| | P[15-26 Hz] engaged | disengaged | ratio |
|---|---|---|---|
| **V56 / route 24** | **1.28e8** | 1.63e5 | **786×** |
| V55 / route 1c | — | — | 877× (recorded) |

And the command side did not move either — probe field P[15-26] = **182** on V56 vs **22** on V55 at
matched creep (peak 23.24 Hz), transition rate 23.9/s vs 21.9/s.

⇒ **Pre-registered outcome (iii): neither the vibration nor the command's 21 Hz dropped.**
🛑 `gp-0x6ad4` / `FUN_0003a382` is **eliminated as the 21 Hz source.** The thread is closed.

### What that opens
The 21 Hz reaches `gp-0x6b98` through a **different summand**, and the aggregator's full lane list is now
confirmed — nine lanes, every one folded in by a plain `add` at `FUN_0003aa2c`:
`gp-0x6b62`, `-0x6b4c`, `-0x6ade`, ~~`-0x6ad4`~~, `-0x6b26` (friction), `-0x6bbe` (boost),
`-0x6bd0` (damping), `-0x6b86`, plus `FUN_00036682`'s return. **Rank these by attenuation at 21 Hz.**
That is the next workstream.

---

## 3. ★ The mute cost damping — GATE 2 resolved against it

`builds/v50_v79/build_v56_tva.py` recorded exactly one open risk: *"OPEN — the damping sign. If the lane is a DAMPING
term, muting it could make the vibration worse."* The car answered.

The operator reports damping removed and a new few-Hz resonance in some instances. It reproduces.
Welch, NFFT=1024 (0.0977 Hz), windows entirely engaged + hands-off + CAN-contiguous, split on
`steeringPressed` — which matters, because mixing hands-on and hands-off is the known trap that
manufactures a spurious 7.42 Hz peak:

| speed bin | n windows | top peak | vs next neighbour |
|---|---|---|---|
| 15-20 m/s | 82 | **8.69 Hz at 1.18e8** | **6.7×** (10.06 Hz @1.76e7) |
| 20-30 m/s | 15 | 9.67 Hz @4.72e7 | — |
| 10-15 m/s | 49 | 10.94 Hz @1.44e7 | no 8.69 line |
| 5-10 m/s | 2 | 7.42 Hz @2.53e7 | thin |

**Intermittent**, as reported — worst windows 09:23.21 and 09:21.94 (vEgo ~18 m/s, P[2-9] = 8.17e7 /
5.22e7); a handful dominate the average. No disengaged spectrum at any speed shows the line; disengaged
is dominated by 1.2-3.3 Hz driver input.

⚠ **Two control gaps, stated plainly.** There are **zero disengaged windows above 15 m/s**, so the
8.69 Hz bin has no matched-speed disengaged control. And **there is no pre-V56 road baseline in the
archive** — route `13` has only segments 12-15 on disk and they are creep (vEgo mean 1.12, max 2.73 m/s).
So the *newness* of the mode rests on the operator's felt comparison, not on archived data. Reverting to
V55 and re-driving is the clean test — and it is also the best available check that the mute was
genuinely live on the car.

### 🛑 A partial restore is not a candidate
The tracer proposed `Y = 16384` (50%) as a next step. **Rejected.** The lane at 100% (V55) and at 0%
(V56) produced the same 21 Hz, so intermediate authority is bounded between two measurements that already
agree; it can only deliver a fraction of an effect that was zero. It is a partial revert wearing a
candidate's clothes. Go straight back to V55.

---

## 4. `FUN_0003a382` is a genuine discrete PID — a real structural correction

Superseding the "three parallel lag stages" framing. All constants byte-verified two independent ways
(GhidraMCP `read_memory` and a raw little-endian Python read); identical in stock/V55/V56.

```python
ERR = clamp(gp_0x4f60 - bias, -0x2800, +0x2800)                  # 0x3a7ca-0x3a7e6
    # bias is a 2-STATE SELECTOR (+8192/-8192, cal 0xC6200 = 8192), NOT a continuous
    # subtraction of gp-0x6ad6 -> ERR's AC content IS gp-0x4f60's: unity gain, zero phase
P   = ((gainA * ERR) >> 10) * 32                                 # 0x3a7e8   gainA=LERP(0xC6B26)=[256,256,225,153]
I   = I_prev + ((98 * ERR) >> 10)                                # 0x3a7e6   cal 0xC6B12, anti-windup clamped
D   = clamp(((ERR - ERR_prev) * 2048) >> 10, -0x2800, 0x2800)*32 # 0x3a832   cal 0xC6AE6 = 2.0 in Q10, RAW diff
gp_0x6ad4 = clamp((((D + I + P) >> 5) * gainD) >> 10, -ceiling, +ceiling)
```

🛑 **The two `1024/1024` cals are each stage's *own extra* smoothing EMA and both collapse to identity.**
That does not mean "no derivative action" — it means the derivative's extra smoothing is defeated,
leaving the **raw** derivative in the sum. **V43 and V46 were re-introducing a defeated pole**, not
filtering the lane.

Frequency response at fs = 1000 Hz, cross-validated by closed-form z-transform and time-domain sim
(agreeing to 4 dp), gainA = 256 row:

| | 3 Hz | 5 Hz | 8 Hz | 21 Hz |
|---|---|---|---|---|
| magnitude | 0.279 | 0.255 | 0.257 | 0.361 |
| phase | −25.7° | −7.3° | +9.2° | +41.8° |

P/32 = 0.250 flat at every frequency; |I|/32 falls 0.159→0.023 and |D|/32 rises 0.038→0.264 over
3→21 Hz. **P-dominated in the few-Hz band; D rivals P by 21 Hz.**
⚠ This **contradicts** the recorded "net −3.3° to −5.4°, P dominates I+D by 8-10:1". The new figure is
cross-validated twice; re-derive before quoting the old one.

**Sign proven, no inversion:** `ld.h` @`0x3aca8`, validity gate `cmovc` @`0x3acc4` (a gate, not a flip),
plain `add` @`0x3acd8`. All nine lanes add; not one `sub`. Polarity `gp-0x6752` is set to literal `1` at
boot in `FUN_000490ac` (`0x490b6`-`0x490c0`), shadow-checked against `gp-0x4c2d`.

**What firmware cannot settle:** whether a P-dominated few-Hz contribution nets out as damping once it
passes the real motor→rack→column plant. That needs the plant transfer function, which is not in the
binary. The on-car result is doing that work.

---

## 5. 🛑 The probe under-ranges — the operator's question was the important one

We built the probe guarding against **railing** on a road drive. The opposite happened.

```python
field = clamp((gp_0x6b98 >> 9) + 8, 1, 15)   # 4 bits of a signed 16-bit register, 1 LSB = 512 counts
```

Engaged + hands-off, n = 69,607: field **7 = 59.0%**, field **8 = 40.1%** ⇒ **99.2% in two adjacent
levels**, i.e. `gp-0x6b98` lives inside **±512** while one LSB *is* 512. Rail occupancy at field 1 and 15
is **0.0%** in every engaged condition. `bit7 = 1` in 94,369/94,369; bits 2:0 constant `7`.

⇒ **The probe is a ~1-bit sign comparator on the motor command.**

| claim | status |
|---|---|
| presence / frequency of a mode in the command | ✅ **survives** — a comparator preserves zero-crossing timing |
| transition rate as a statistic | ✅ **survives**, and is the robust one to quote |
| "120.5 counts at 21 Hz", "38× over openpilot's budget" | 🛑 **void** — under ¼ of one LSB, set by the quantiser step |
| "flat H1 0.192 → 0.216, coherence 0.93" | ⚠ **provisional** — few dof, through a 1-bit output |
| the `0xC646C` reader-set elimination that rested on it | ⚠ **downgraded to "not yet tested"** |

Recomputed H1(sensor→field), engaged + hands-off, NFFT=256:

| | 1.17 Hz | 3.12 | 5.08 | 7.81 | 21.09 Hz | windows |
|---|---|---|---|---|---|---|
| V55 / route 1c, vEgo≤1.98 | 0.058 | 0.480 | 0.335 | 0.389 | 0.132 | **3** |
| V56 / route 24, speed-matched | 0.540 | 1.153 | 1.020 | 0.463 | 0.584 | **5** |
| V56 / route 24, all speeds | 1.467 | 0.507 | 0.340 | 0.038 | 0.464 | 438 |

Not a like-for-like refutation (stricter windowing here), but it shows the recorded figure is
**method-sensitive on very few degrees of freedom**. Since it is what retired the `0xC646C` reader set,
that elimination is now provisional.

**Action for the next telemetry build:** `SHIFT = 9` is ~6 bits too coarse. Use **`SHIFT = 6`**
(64 counts/level, window ±448) or **`SHIFT = 7`** (128 counts/level, ±896). Keep the clamp to 1..15 and
the reserved 0. The full 16-bit CAN `0x18F` sensor figures are unaffected — keep sensor-side and
command-side numbers rigorously separate.

---

## 6. The take-over beep — closed, and not a firmware item

```
426.410s  commIssue/softDisable          "TAKE CONTROL IMMEDIATELY / Communication Issue Between Processes"
426.530s  selfdrivedLagging/softDisable  "TAKE CONTROL IMMEDIATELY / System Lagging"
427.450s  condition clears (1.040 s)
```

**Fired exactly once as a driver-visible banner in 15:43**, and **never escalated** — `latActive` and
`enabled` had zero transitions from 279 s to 588 s. A soft-disable that caught itself, which is why it
felt like nothing was wrong.

The car is a clean null: `STEER_STATUS = 0` continuously 193.1→588.0 s; `torqueState.saturated` False in
**94,241/94,241** samples route-wide; `pandaStates` health has **3 transitions all route**, all at
ignition; `can0`/`can1` error/TxLost/RxLost/coreReset flat zero with zero delta in [420,435] s; **zero
`steeringPressed` transitions** in the window.

Cause is **diffuse scheduling contention**: inter-arrival gaps for all seven candidate services peak far
from the event (466/471/437/481/506 s), zero camera frame skips, biggest per-process CPU mover
`starpilot.system` at +5.3 pp — against a standing condition of **5-6 of 8 cores near saturation**,
70-79% average, on a fork carrying `starpilot.system`, `starpilot.starp`, `mapd` on top of the stock
stack. Thermals green throughout. The lever is process load, not code; per the standing
no-openpilot-modifications instruction that is the operator's call.

### 🛑 Four rlog tooling traps this exposed
1. **`selfdriveState.alertSound` is unpopulated route-wide** — `none` in every frame, including a
   full-size `userPrompt`. **Absence of `alertSound` is not absence of a beep.**
2. **`onroadEvents` does exist** in this fork (top-level, edge-triggered, easy to miss in a `which()`
   histogram). Use its `softDisable`/`immediateDisable` booleans, not substring matching.
3. 🛑 **Anchor the route clock on each segment's first `carState`.** Every segment file's first entry is
   a re-embedded bootstrap message carrying the original boot timestamp (bit-identical `5786544129145`
   across segs 0/6/7/8), which biases a naive clock **+1.34 s**.
4. `0x33D` LKAS_HUD **byte 4 is counter+checksum** (`0x00/0x1f/0x2e/0x3d` every 10 ms), not a beep bit.

---

## 7. Next steps, in order

1. 🛑 **Flash V55 back.** Already built, already driven, fault-free, keeps the probe.
   `39990-TVA,A160-V55-...rwd`, SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf`.
   On the next drive, confirm the 8.69 Hz line disappears — that is both the fix and the liveness proof.
2. **Enumerate and rank the other eight aggregator lanes** by attenuation at 21 Hz.
3. **Re-scale the probe** to `SHIFT = 6..7` before the next telemetry build.
4. **Re-establish or retract the `0xC646C` elimination.**
5. `0xC6372`/`0xC636E` remains candidate #2, still needing its own GATE 2 pass. ⚠ V56 is now a
   cautionary precedent for muting a lane whose damping sign is unproven.

## Artifacts
Analysis scripts left in the session scratchpad: `steerreq.py`, `xcheck_21hz.py`, `lowfreq_hunt.py`,
`spectrum_shape.py`, `probe_rails.py`, `field_v55_vs_v56.py`, `h1_v55_v56.py`, plus the subagents'
`stageA`-`stageD` reports. `probe_rails.py` writes `route24_cache.npz`, which makes re-analysis of this
route fast.

---

## 8. 🛑 CORRECTIONS — late-arriving analysis overturned two sections above

Two deep passes landed after §§1-7 were written. **Read this section as authoritative where it conflicts.**

### 8.1 The 8.69 Hz line is WHEEL ORDER 1, not a V56-induced resonance

§3 above called it a new resonance. **It is a tyre.** Identified on the independent `STEER_ANGLE_RATE`
channel — `0x18F` bytes[2:4] BE signed × **−0.1** deg/s, which is the **10× finer** copy of the field
openpilot itself reads at `0x14A[2:4]` (r = −0.9473 vs `carState.steeringRateDeg`; and `carState`'s value
is quantised to **1 deg/s**, a crippling quantiser for a ~1.5 deg/s rms line — use the CAN field):

```
f = 0.4890·v − 0.186 Hz    r = +0.9970    rms residual 0.037 Hz    intercept ~ 0 (THROUGH THE ORIGIN)
implied rolling circumference 2.088 m  (p10-p90 2.076-2.099)   vs 2.05-2.11 m for 235/45R18
```

⇒ **one line per wheel revolution: tyre/wheel imbalance, non-uniformity or runout.** Firmware-independent.
Invisible on every prior route because at 1.5 m/s wheel order 1 is 0.7 Hz, not 8.7. Burst-like — worst
window Q=55 at **1608× the local floor**, while pooled envelope Q is only 3-4.
⇒ **ACTION: wheel balance / road-force check.** The 2.088 m fit is specific enough to test physically.

**My non-monotonic speed bins in §3 are explained:** the bins were too coarse (15-20 m/s spans 7.2-9.6 Hz
of true wheel order, so the bin argmax lands wherever the most windows were) and in weak bins the argmax
is noise. Restricted to present-and-steady windows it is monotonic and linear.

**There is ALSO a genuine FIXED ~7-8 Hz resonance, on every build** — V56 7.81, V55 7.03, V54 8.59,
V53 7.03, R13 7.42 Hz at creep, where wheel order is only 0.3-0.8 Hz, so it cannot be wheel order. Both
appear together in the seg-11 high-resolution spectrum (7.275/7.52/7.715 Hz **and** the 9.766 Hz
wheel-order line at 20.3 m/s). **At 15-20 m/s the wheel-order line sweeps UP THROUGH that resonance** —
the classic recipe for an intermittent low-frequency shake that only ever appears on the road. That is
most likely what was felt.

**And "V56 removed damping" is not supported by the data.** Matched creep, 1-10 Hz band variance:
V56 **9.75e3** vs V55 5.70e4 (**0.17×**), V53 9.68e4 (0.10×), R13 4.03e4 (0.24×), V54 7.38e3 (1.32×);
angle-controlled (|ang|<5°, only R13 survives) V56/R13 = 0.64×. Envelope-decay Q: V56 **3.6**, V55 7.4,
V53 14.1, V54 4.8, R13 3.5 — V56 is not the least damped.
🛑 **But every one of those numbers is CREEP data, and the report was at ROAD speed where no prior build
has any data at all.** The creep table does not test the claim. **GATE 2 stays open where it matters.**

### 8.2 The mode is 20-25 Hz, and steering angle confounds every cross-route comparison

**Stop calling it "21 Hz."** Presence-tested, steady-speed, pooled: `f = 0.177·v + 20.48` (r = +0.650) —
**24.61 Hz at 19-21 m/s, 25.00 at 21.3 m/s**, in the worst events a cluster of very narrow lines
(24.12/24.32/24.56/24.85/25.15 Hz, **Q = 160-228** at df = 0.0488 Hz). Not wheel order (implied
circumference would span 0.06-0.84 m).

🛑 **NEW CONFOUNDER: steering angle moves the mode ~2 Hz within one firmware.** |ang| 0-2° → 23.44 Hz
(n=18); 2-5° → 22.66; 5-10° → 21.48; 10-20° → 21.48. V56's creep is near-straight (0.5° median, road
entry/exit) while **every** prior build's creep is wheel-turned (V55 26.9°, V53 42.2°, V54 17.6°,
R13 12.6°). ⇒ V56's apparent +2 Hz at matched *speed* is fully confounded with *angle*, **and the
historical 20.12 → 21.68 Hz speed curve is angle-contaminated too.** Condition on angle from now on.

### 8.3 §5 over-corrected: the amplitude figure and the `0xC646C` elimination both survive

**"120.5 counts at 21 Hz" is a REAL detection — keep it, restate it.** My "under ¼ of one LSB ⇒ void"
reasoning was wrong: averaging K segments over 512 bins recovers far below the step size when dither is
present, so the floor is set by the noise, not the LSB. Encoder gain is **1.006 (unbiased)**; the
false-positive floor at route 1c's actual dither (224-336 counts rms) is **10-18 counts** ⇒ **120 counts is
7-12× above floor.** Required restatements: it is a **bin-RMS, not an amplitude** (÷0.5766 → ≈209 counts),
and 🛑 **38× vs 66× depends on whether openpilot's "31.7 counts" was an amplitude or a bin-RMS — the record
must say which. Unresolved.** Either way the correction runs *against* openpilot as the source.
⚠ The railed-subset figure (105.8 counts) is 7.9 s non-contiguous with coherence 0.66 at/below its own
threshold — **do not lean on it.**

**"flat H1" is UNCONFIRMED, not refuted — and quantisation is EXONERATED by construction.** Ground-truth
lanes through the exact encoder (Monte Carlo K=30 × 60 trials) reproduce H1's **shape** to a few percent,
including a true 0.93 Hz pole (true ratio @21/@1 = 0.069, measured 0.071 ± 0.022). A memoryless
nonlinearity applies one describing-function gain at every frequency — **it cannot flatten a pole.**
Coherence bias is **downward** (0.963-0.976 for a true 1.000), so the recorded 0.93 is a **lower bound**.
The real problem is dof: at ±19.6% a pole at fc = 16.8 Hz (rel-sse 0.215) and flat (0.245) are
**statistically indistinguishable**, and the 0.192 → 0.216 rise is **not significant**.

🛑 **Therefore the `0xC646C` elimination STANDS — my downgrade to "not yet tested" is withdrawn.** Rest it
on the **structural** leg, which is a byte fact untouched by any of this: **`0xC646C` has 0 matches across
all 468 instructions of `FUN_0003a382`.** The transfer argument is corroborating only.
**No candidate cause returns to scope.**

### 8.4 Further corrections of record

- 🛑 **"9 independent segments, coherence significance 0.312" is WRONG.** Route 1c engaged is **2
  contiguous runs** (998 + 1359 = 2,357 samples = **23.6 s**) ⇒ **K = 3** non-overlapping 512-pt segments,
  **significance 0.776** (K=6 at 50% overlap → 0.451). Nine would need 46 s. **The quoted coherences
  (0.672, 0.687) sit near or below their own threshold.** Root cause: `band_power(nfft=256, hop=64)` is
  75% overlap, overstating dof ~4×.
- ⚠ **"Probe live: 10 distinct field values, 100% interior, no rails"** is true of the whole drive but
  **false of the analysed engaged subset** — 4 distinct values, 93.2% in fields 7-8, **effective 1.5 bits.**
- **Route 24 structural checks all pass:** bit7 = 1 in 94,348/94,348; bits 2:0 = 7 in 94,348/94,348;
  `field == 0` in **0** samples; **field 15 never occurs in 943 s**; rails 0.10% low / 0.00% high.
- **Disengaged control is thinner than §3 said:** V56 has **zero** disengaged windows above **3 m/s**, not
  15 — the entire road drive was engaged.
- ⚠ **The level-spread is NOT a V55-vs-V56 discriminator**, with a mechanism: at low true sd, **a half-LSB
  DC shift alone swings the 15-26 Hz statistic 1.45×** (83.6 → 121.4 counts with the true signal held
  constant), and the two drives' DC differs by exactly that (mode at field 8 on 1c vs field 7 on 24). It
  measures threshold placement, not the command.
- ⚠ **A tempting discriminator, tested and KILLED** (so nobody re-runs it): pooled at 1.0-3.0 m/s the peak
  appears to move 21.09 → 23.44 Hz at matched speed. **Per-segment it dissolves** — route 1c is locked
  (21.09/21.09/21.09 Hz) while route 24 wanders (20.31/22.66/22.66/21.88/14.06/19.53/23.44/17.19/21.09/
  20.31) over speeds spanning only 1.17-1.81 m/s. **On route 24 the mode is intermittent, not shifted;**
  the pooled peak was one strong 5.4 s episode.
- 🛑 **`SHIFT = 6` with `OFFSET = 8` collides with the `field == 0` sentinel** — `(x>>6)+8 == 0` for
  x ∈ [−512,−449]. §5's "use 6 or 7" was unsafe as written. **Offset must go to 9 whenever shift goes to
  6**; recommended is **`SHIFT = 7 / OFFSET = 8`**, the only option whose railing can be bounded from data
  (must-rail 0.13%, may-rail ≤0.83% on route 24 engaged+hands-off).
- 🛑 **A ~1.5-bit quantiser folds the mode's 5th harmonic into the few-Hz band** at fs = 100 Hz (25-79
  counts, +5.1 to +7.1 dB over the local floor). It moves **5× faster with speed** than the mode — that is
  the test **any** new few-Hz claim from this probe must clear. No evidence of it in existing data (route
  1c's 5.47 Hz bin carries 3.07 counts, field/sensor ratio 0.059, lowest in the band).
- **`rlog-tools/probe/decode_v55_motorcmd.py` FIXED**: its railing guard fired only above 50% and prescribed
  `CMD_SHIFT=10` — the wrong direction, guarding a failure that never occurs while silent on the one that
  always does. It now flags >80% occupancy in ≤2 adjacent levels, prescribes `CMD_SHIFT=7`, warns about the
  offset-9 sentinel collision, and documents the 4× dof overstatement. Re-validated on route 1c (fires at
  90.7%).

### 8.5 The recommendation is unchanged, and gains a non-firmware item

**Revert to V55** — not because "V56 removed damping" is proven (it is not), but because **V56 bought
nothing** for the mode and the operator reports degraded feel. Lived experience governs, the data cannot
contradict it at road speed, and reverting is free.

**Plus: get the wheels balanced / road-force checked.** That is a genuine, testable, non-firmware finding
and the first mechanical lead this project has produced.

**The test that would settle GATE 2 properly:** a hands-off drive on the **same road** at 17-21 m/s with
the lane restored, **including a deliberate disengaged stretch at 18-20 m/s as the control** — the one
condition no route in the archive contains.
