# HANDOFF 2026-07-29 — V56 drive: the mute is null, it costs damping, and the probe under-ranges

**Route `24`** (`75604b0a432fdc89_00000024--bc45926e80--0..15`), 16 segments, **15:43**, mixed road
driving up to 21.8 m/s. **The kit's first road drive carrying a firmware telemetry probe** — every prior
vibration route was parking-lot creep.

**Headline: revert to V55.** V56's `0xC6AF0` mute answered its question in the worst possible way — it
did **nothing** for the 21 Hz and it **removed damping**. But the null is a real, hard-won result: it
eliminates an entire lane, branch-agnostically, that three previous builds had only nibbled at.

---

## 1. The four questions this session was asked

| # | question | verdict |
|---|---|---|
| 1 | is the vibration fixed? | 🛑 **No.** 786× engaged/disengaged, matched creep — V55 was 877× |
| 2 | did we remove damping / is there new few-Hz resonance? | ★ **Yes, both.** Sharp intermittent **8.69 Hz**, 6.7× above its neighbours |
| 3 | why does openpilot beep to take over? | ✅ **`commIssue`+`selfdrivedLagging` softDisable under chronic device CPU load.** Clean CAN/EPS null |
| 4 | are we accounting for seeing only a few bits of the value? | 🛑 **No, and it matters more than expected** — the probe is a ~1-bit comparator |

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

`build_v56_tva.py` recorded exactly one open risk: *"OPEN — the damping sign. If the lane is a DAMPING
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
