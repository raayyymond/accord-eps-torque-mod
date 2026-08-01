# HANDOFF 2026-08-01 — V62 FLEW AND THE GRINDING IS FIXED

**Route `00000037--6231e33f3d`, 15 segments, 86,278 frames, 862.65 s, 10:11:03–10:25:26.**
**Build on the car: V62** (`sar 0xa`→`sar 0x9` at `0x3AC20` and `0x3AB76` in `FUN_0003aa2c`).
Image SHA `80d9e1f7…9264c7`, RWD SHA `1e0806a1…5bff8e` — **both verified from the artifacts by the
orchestrator**, and the two edited bytes re-read from the image (`0x3AB76`=`a932`, `0x3AC20`=`a942`,
`0x3AB70` still `aa32`, all cals stock). What flew is exactly V62 as documented.

---

## ★★★ THE HEADLINE: the first measured FIX in the kit's history

Operator: *"Original grinding at 2–5 mph is gone!"* — **and the data agrees, by a large margin.**

Engaged creep, speed-standardised, episode-clustered bootstrap, order-track ceilings enforced:

| | V62 / V59 | |
|---|---|---|
| 18–22 Hz, creep | **0.124 [0.036, 0.387]** | 8× suppression, CI excludes 1 |
| 18–22 Hz, at \|rate\| 16–32 deg/s | **0.024 [0.016, 0.234]** | **42× suppression** |
| 30–40 Hz **negative control** | ~1.0 | ⇒ band-specific, not a route/gain offset |

And the whole transient distribution moved down. `|d(tq)|` per 10 ms, engaged, V62 vs V59:

| threshold | V62 rate/s | V59 rate/s | ratio |
|---|---|---|---|
| >200 | 15.77 | 19.88 | 0.793 [0.584, 1.100] |
| >500 | 3.85 | 7.92 | 0.486 [0.269, 0.850] |
| >1000 | 0.354 | 1.042 | 0.338 [0.135, 0.672] |

**V62 has the lowest p90, p99 and >1000/s of any build in the set**, and gets monotonically cleaner as
the threshold rises. Cleaner in **every** speed stratum below 16 m/s and at **every** motor rate.

★ **V61 is quantified here too, and it matches the operator's "significantly worse" exactly:**
p50 roughness **730** vs V59's 101; >1000 excursions **376.7/s vs 24.3/s** (15×); burst rate **72× V62's**.

---

## 🛑 THE NEW SYMPTOM IS NOT A REGRESSION — and the two remembered instants are different things

Operator: *"a new case where grinding occurred… turning manually, with LKAS engaged, at maybe 10–20 mph.
Timestamps 10:12:15 and 10:23:24."*

Wall clock is **measured, not assumed** (offset 1785517810.5370 s, sd 0.054 s, one continuous boot clock
across all 15 segments, ±0.05 s): **10:12:15 → seg 1 t=9.67 s**; **10:23:24 → seg 12 t=18.63 s**.
Both were **independently relocated without reference to the operator's memory**, by scanning
sample-to-sample `|d(tq)|` with no speed/engagement/effort criteria: the only burst >2000 counts/10 ms in
the entire route is seg 1 t=10.24–11.16 s, and the second largest at the 1000 threshold is
seg 12 t=17.76–19.09 s. Both methods converge to the second.

### They are two different phenomena, and only one is unusual

**Instant #2 (10:23:24, 16.3 mph)** — an ordinary roughness burst, n=33, max 1532, **never exceeded 2000**.
**V59 produces these at 1.042/s versus V62's 0.354/s — V59 has ~3× MORE of them.** Comfortably inside
V59's family. This is the unmasking: ordinary transient load dropped 2–3×, so what remains is salient.

**Instant #1 (10:12:15, 5.4 mph — NOT 10–20 mph)** — a **0.92 s singleton**, unique in the dataset,
max 3,694. Band decomposition vs 100 same-length engaged windows elsewhere in seg 1:

| band | vs median | percentile |
|---|---|---|
| 0.5–3 Hz (driver sweep) | 260× | 98th |
| 6–12 Hz (ratchet) | 12.0× | 64th |
| **18–22 Hz (GRINDING)** | **1.4×** | **52nd — ordinary** |
| **38–46 Hz** | **8,478×** | **100th ← this is the event** |
| 46–50 Hz | 2,401× | 100th |

Peak 41.64 Hz ≈ 2 × 20.8 Hz. ⚠ **At fs ≈ 100.5 Hz this is indistinguishable from 58.86 Hz.**
Treat the PRESENCE as the result, never the number.

### 🛑🛑 IT IS ONE EVENT, AND THE CORRECT n IS 1
V62's 43 excursions >2000 are **all inside that single 0.92 s burst**. Any statistic treating them as
independent is wrong by ~43×. **By distinct bursts per engaged second:**

| build | bursts | engaged s | rate/s | 95% CI |
|---|---|---|---|---|
| **V62** | 1 | 702.4 | 0.00142 | **[0.00004, 0.00793]** |
| V59 | 0 | 374.2 | 0 | [0, 0.00986] |
| V61 | 4 | 39.2 | 0.10204 | [0.02780, 0.26127] |
| V64 | 0 | 79.2 | 0 | [0, 0.04658] |

⇒ **V62's CI is CONTAINED INSIDE V59's.** V59's upper bound is 7× V62's point estimate.

**Exposure-matched conditional test.** The burst is at v 2–4 m/s **and** |rate| ≥ 32 deg/s.
V62 spent **16.14 s** in that corner, V59 **15.75 s** — matched to 2.5% — and V59 saw 0 events.
With one event total, `p = 16.14/(16.14+15.75) = 0.51`. **A coin flip. No evidence of a regression,
and no evidence of absence.**

⚠ **The one thing that is genuinely out of family:** on 38–46 Hz max, V62's corner value is 6.30e5 vs
V59's 1.43e3 — **440×**. But through p90 the two are indistinguishable (438 vs 329). It is an ordinary
distribution with one extreme outlier, not a shifted distribution.

### Both instants are SYMMETRIC — not stick-slip
Dwell metrics on the >4 Hz high-passed bar, against synthetic calibration:

| signal | dwell +/− (samples) | ratio | skew(dx/dt) |
|---|---|---|---|
| instant 1 core | 1.50 / 1.50 | 1.00 | **−0.00** |
| instant 2 core | 1.24 / 1.07 | 1.16 | **−0.08** |
| seg13 RATCHET reference | 7.33 / 7.15 | 1.03 | −0.30 |
| **SAWTOOTH calibration** | 6.80 / 6.69 | 1.02 | **−3.27** |

⇒ **Neither instant is stick-slip** (a sawtooth gives −3.27; both give ≈0). And **dwell separates the
instants from the ratchet by 5–6×** — period 2.4–3.0 samples (≈33–42 Hz) vs 14.5 samples (≈6.9 Hz).
**95.7% / 77.6%** of the instants' >4 Hz energy is OUTSIDE both known bands; the ratchet puts 90–98%
INSIDE them. **Spectrally disjoint populations.**

---

## ★★★ r26 IS STRUCTURALLY INERT — every result on this lane is r24's

**`avg` (`gp-0x69a4`) multiplies r26 and only r26.** `FUN_00039702` shows the RAM array at
`gp-0x641E`…`gp-0x6444` is an **adjustment added in Q10 float to a fixed cal base at `tp+0x7564`**:
```
local_5c[2] = (float)*(short*)(tp+0x7564) * 0.0009765625 + (float)*(ushort*)(gp-0x6444) * 0.0009765625;
```
**`0xC6564`–`0xC658C` byte-reads as 40 bytes of EXACTLY ZERO** — orchestrator-verified, and the zero run
is **bounded by non-zero data on both sides**, so it is a deliberately-zeroed table, not sparse-region
filler. No writer was found for the RAM adjustment cells (10 of 18 checked individually, sign and
instruction context confirmed on every hit).

⇒ `stage1 = (dtorque × avg2) >> 10 ≈ 0` **regardless of dtorque** ⇒ **r26 contributes ~nothing, and
V62's `0x3AB76` edit was a NO-OP.**

### This rewrites the lane's history
| build | edit | result | what actually happened |
|---|---|---|---|
| V42 | zeroed r26's gain | NULL | r26 was already zero |
| V61 | killed **both** taps | **WORSE** | this was killing **r24** |
| V62 | doubled **both** | grinding fixed 8–42× | this was doubling **r24** |

🛑 **SUPERSEDES a standing claim.** The record said *"r24 and r26 are not independent — killing either
alone leaves the other transmitting, so each null is uninformative about the lane."* **r26 was never
transmitting.** That sentence shaped several builds.
🛑 **A one-byte revert of `0x3AB76` would therefore change NOTHING.** It was the orchestrator's leading
candidate mid-session and is now dead. (`r37-extract`'s closing note recommending it as "the right next
build for the ratchet question" was written before this result and is superseded.)

⚠ **BELIEF, not proof:** `avg2 ≈ 0` rests on a zero cal base + no writer found in 10 of 18 cells.
`read_memory` on the live RAM fails, as it does for every RAM table in this kit. A diagnostic or
adaptive-learning write path via the 8 unchecked cells or a register-indirect method would overturn it.

---

## ✅ Three structural eliminations, all byte-verified

1. **Saturation / clamps are NOT the mechanism.** Per-lane clamps confirmed **±8192** at `0x3AB82`/
   `0x3AC42`; aggregate sum clamp **±10240**, a hard clip, at `0x3ACE8`. But `dtorque` never gets near
   the range where they bite: the kit's own measured amplitudes give dtorque **123–839**, and even the
   route's most violent transient implies **739** — r24 = 3,326 against a lane clamp of 8,192. Reaching
   the ±10240 sum clamp would need `avg2` ≥ 1,598, and `avg2 ≈ 0`. **Two independent reasons.**
2. **The `FUN_00034350` relay is dead in the symptom band.** It is a genuine Coulomb relay — sign forced
   to `−sign(gp-0x6abe)` @`0x3469e`–`0x346a2` with magnitude built from four *independent* tables, so
   every motor reversal flips a nonzero quantity. But the chain is **`mulu` throughout with no additive
   term**, and two multiplicative factors are zero here:
   - **FactorC** (`0xD27BC`, mode 10): X = [2240, 3840, 5120, 8960] = **35/60/80/140 km/h**, Y = [0, 235,
     430, 877] ⇒ **exactly 0 below 35 km/h**.
   - **f5** (`0xD27F8`): X = [60, 400, 2500, 4000], Y = [0, 140, 539, 927] ⇒ **0 below 12.7 deg/s**, and
     only 0.137 by 85 deg/s.
3. **⇒ The base-assist damper lane is inert at BOTH symptoms' operating points**, at any speed:

   | | motor rate | f5 |
   |---|---|---|
   | ratchet p50 | 2.0 deg/s | **0.0000** |
   | grinding p50 | 15.5 deg/s | **0.0052** |

   **A third independent reason V44 and V47 were null**, beyond the FactorC speed gate and the task-5 lag.
   f1 (`0xD2738`) and f4 (`0xD2774`) are **flat 1024 = no-ops** (f4's 5th Y is 1024, closing an open item).

---

## ★★ THE RATCHET — best characterisation this kit has ever had

**It is strictly LKAS-gated, and this is now highly significant.** Pooled across all five builds, each
route contributing its OWN internal engaged-vs-manual contrast (so no cross-route level comparison):

| arm | windows | episodes | prom ≥10× | episodes with hit | RMS med |
|---|---|---|---|---|---|
| **ENGAGED** | 81 | 25 | **61/81 (75.3%)** | 21/25 | 322.5 |
| **MANUAL** | 48 | 23 | **1/48 (2.1%)** | 1/23 | 27.4 |

**Fisher exact on EPISODES: OR 115.5, p = 1.09e-08.** RMS ratio 11.8×. Present on **every** build
including V62 — **nothing escaped into manual.** (Within segs 13/14 alone the power ratio is 2,039×, but
that is 2 vs 3 episodes, Fisher p = 0.10 — **not significant alone**; the pooled test is where the
significance lives.)

★★ **THE RATCHET WAVEFORM IS SYMMETRIC ON EVERY BUILD** (skew(dx/dt) −0.16…+0.06 across all five, against
a −3.27 sawtooth calibration). ⇒ **It is an AMPLITUDE-SATURATED RESONANCE, not a friction limit cycle.**
Points at **damping / loop gain**, not friction compensation or a deadband — and it is **build-invariant**,
so V62 changed its amplitude, not its mechanism.

**Fixed in hertz, not a tyre order:** domain test at 0.3–11 m/s gives CV(Hz) 0.211 vs CV(order) 0.829.
🛑 **Order 1 (`0.489·v`) enters 6–9 Hz at v = 12.3 m/s and leaves at 18.4 m/s — every ratchet number above
~11 m/s is tyre-contaminated.**

---

## 🛑 RETRACTIONS — claims made and withdrawn in this session

1. **"V62 amplified the ratchet 2–3×, gated on driver effort."** ❌ **RETRACTED.** A split-half-by-episode
   null puts the **resolution floor at 2.2×**; every ratchet CI covers 1. The effort profile is
   monotone-decreasing (2.03 → 1.22 → 0.93), not peaked at 200–1000 with a reversal above 2500 — that came
   from unclustered window medians, which shrink CIs by ~√28 and manufacture significance.
   `spec-newgrind` independently concurs (its own creep figures, 1.3–1.8×, are inside the floor).
2. **"Band power tracks driver effort."** ❌ **WRONG — it tracks MOTOR RATE.** Partial Spearman of
   log band power, each axis residualised on the other, replicating across both builds:

   | | partial ρ(effort \| rate) | partial ρ(rate \| effort) |
   |---|---|---|
   | grinding V62 / V59 | −0.130 / −0.247 | **+0.573 / +0.701** |
   | ratchet V62 / V59 | −0.393 / −0.306 | **+0.613 / +0.590** |

   Effort's partial association is **negative** everywhere. It was only ever a proxy for rate.
3. **"The ratchet's f0 moved 8.18 → 7.71 Hz."** ❌ **Simpson's paradox.** Speed-matched V62/V59:
   7.41/7.39, 8.25/7.73, 8.80/9.60, 8.01/10.53, 9.02/8.87 — **no consistent shift**. f0 rises with speed
   on every build (ρ +0.36…+0.59) and V59's windows sit higher in the pooled range. **V61 IS genuinely
   down** (6.51–6.75, sd 0.25–0.58).
4. **A 41–48 Hz "line" as a V62-specific mode.** ❌ Does not survive a per-window presence test (V62 prom
   p50 **7.0** vs V59 **9.5**, f0 wandering sd 1.2–3.1 Hz). It was an artifact of averaging overlapping
   window spectra near Nyquist. The **burst's** 38–46 Hz content is real and separate; the routine
   high-band "line" was not.
5. **"Segment 0 is a stale boot from 07:05."** ❌ Only its `clocks` **messages** carry a pre-NTP RTC (349
   of 351, wrong by 34,052,791 s). **Seg 0 is real driving, 10:11:03–10:12:05** — park→drive, mostly
   manual at large angle, so it matters for the manual arm. 🛑 Never use seg 0's own `wall_t0` scalar.
6. **A "2.0043 ± 0.076 harmonic lock over 121 windows."** ❌ Withdrawn by its own author — 120 of those
   windows have both bands at floor. **Exactly one window in 15 segments** has 36–48 Hz RMS > 150 counts
   (instant 1), and in it `f_hi/f_grind = 2.000` exactly. Suggestive, n=1, **not established**.
7. **The `avg` gate is `gp-0x4f60 < 9217`.** ❌ It is the symmetric window **|gp-0x4f60| ≤ 25600**
   (`addi 0x6400` / `ori 0xc801` / `cmovnc` @`0x355b0`–`0x355c6`) — the biased-unsigned idiom. Corrected
   twice, finally at instruction level, and it matches an independent earlier session.

---

## 🛑 A DECODE TRAP THAT SILENTLY INVERTS A CONCLUSION

**`0x14A` byte4 = `0x87` means the OPPOSITE thing on V62 and V64.**
- Under **V59's thermometer** (which V62 carries): *live, boost index ≥ 2048* — the **deepest** reading.
- Under **V64's detector**: *live, detector unarmed* — **the V64 null**.

`0x87` is **9.24% of route 37**. The V64 handoff primes every reader to see it as a null. `extract_r37_cache.py`
decodes it as V59's probe and exposes `field/live/fault/lt512/lt1024/lt2048/therm/thermviol` with **no V64
detector fields**. Route-37 probe health: liveness 86,278/86,278, fault sentinel 0, thermviol 0, stock low
bits `&0x07` = 7 on every frame.

---

## FLIGHT HEALTH — CLEAN

- **`ST==4` = 0 / 86,278** and `ST==5` = 0. ⚠ ST==4 is the **fault** value (`no_torque_alert_2`, the gentle
  EME) — zero is the clean result. **The zero-EME streak extends past 229,278 frames.**
- `ST==3` = 119, **all at vEgo 0.000** (seg 0 t=0.37–1.48 s; seg 14 t=21.15–21.21 s) — the low-speed
  lockout, expected.
- `0x14A` / `0x18F` at 100.00–100.06 Hz in every segment, frame counts matched to ±1, no dropouts.
- Six watched events: **all 0** except `steerSaturated` ×2 (seg 1, t=49.20 and 49.68 — **not** at either
  instant). 123 softDisable, all benign (`wrongGear` 115, `seatbeltNotLatched` 5, plus the known seg-0
  boot/device-load transient).

---

## ⇒ RECOMMENDED NEXT STEP: **NO NEW BUILD. FLY V62 AGAIN.**

**There is nothing established to fix.** The grinding is fixed by a large margin. The one candidate event
is a 0.92 s singleton at **p = 0.51** against an exposure-matched control, and V62's burst-rate CI sits
inside V59's. **A fix would be aimed at a coin flip.**

The open question is *the RATE of a rare event*, and that needs **exposure, not firmware**. Two more V62
routes make the rate estimable: if it never recurs it was a one-off; if it recurs at ~1/700 s there will be
three events and a real CI. **Zero risk, no new build, no new probe.**

**Route for the repeat:** ordinary driving plus deliberate creep passes, and specifically **revisit the
corner the burst lived in — v 2–4 m/s with high steering rate (≥32 deg/s) under LKAS.** Log from before
first engagement.

### When a build does come, the target is the RATCHET, and the search space just shrank
- ❌ **NOT** the r26 revert — structurally inert.
- ❌ **NOT** the base-assist damper (`gp-0x6bd0`) — f5 = 0 at both operating points.
- ❌ **NOT** friction compensation or a deadband — the waveform is **symmetric**, so it is a saturated
  resonance, not stick-slip. (`FUN_00036c12` is separately confirmed continuous, `−K(speed) × motor rate`,
  viscous damping, reads no torque signal.)
- ❌ **NOT** the motor-rate LERP as a discriminator — **scale resolved this session at 4.7121 counts per
  deg/s** (`0xC613A` = 1159, chain `gp-0x4f50 → FUN_00041464 → gp-0x6abe → FUN_0003f776 → gp-0x6a56 →
  FUN_00040a50 → gp-0x69ea → 0x14A byte2:3`). Ratchet 9.4 counts, grinding 73.0 — **both inside gain_A's
  flat first segment** (breakpoints 250/400), so the stock curve cannot separate them.
- ✅ **STILL OPEN and now the leading idea:** the two modes *do* separate on motor rate (9.4 vs 73.0
  counts). **Breakpoints are calibration.** r24's gain_B (mode 10, `0xD2AEC`) has X = [0, **400**, 1500,
  3000], Y = [2305, 2304, 2149, 1948]. Moving the breakpoints down to bracket the two operating points —
  e.g. X = [0, 40, 100, 3000], Y = [2305, 2305, 4610, 4610] — would give **stock gain where the ratchet
  lives and 2× where the grinding lives**. Arithmetic is safe (5120 × 4610 = 23.6M against 2³¹).
  🛑 Not proposed as a build: it would be aimed at an unmeasured effect. Hold until the ratchet is worth
  attacking on its own terms.
- 🛑 **`gp-0x61a0` → `gp-0x67ac` remains OPEN.** `gp-0x67ac == 1` excludes **nine** aggregator lanes
  including r24/r26 from the sum. Single writer `FUN_00026c80`, sticky latch over an 11-slot state table
  whose own writer was not located. If it is ever 1 at road speed, the lead-compensator framing needs
  revisiting. Circumstantial evidence says the lanes are live (V62 differs from V59 at 4–9 m/s) —
  **probable, not proven.**

### ⚠ AND THE TRIGGER IS OUTSIDE THE FIRMWARE
Instant #1 occurs while **openpilot's command is railed at ±4096** (0.64 s continuous) with the driver
turning against it. Engaged-creep rail duty: **V62 42.38% vs V59 25.25%** — 1.7× the exposure, which is
itself a confound for the burst comparison. The record already noted the ratchet *"rises 8.42× with rail
duty."* 🛑 **NO openpilot-side modifications** is a standing operator instruction and was honoured; this
is recorded as a factual observation about the trigger, and the constraint is the operator's call.

---

## ★ NEW STRUCTURAL FACTS OF RECORD

- **The rate lane is TWO-LEVEL scheduled.** Inner (per tick, `FUN_0003aa2c`): 4-point LERP on **motor rate**
  `gp-0x6ac0`. Outer (periodic rebuild, `FUN_0003ad74`): selects among **speed-class** records via voted
  speed `gp-0x6a5e`, breakpoints `0xC6010` = [0, 640, 3200, 6400] = **0/10/50/100 km/h**.
- **gain_A (r26) is NOT mode-indexed** — fixed cals `0xC6A68`/`0xC6A7C`/`0xC6A90`/`0xC6AA4` for every mode.
  **gain_B (r24) IS mode-indexed** via `gp+0x63fd`. Byte-read, mode 10 / class 0:

  | | X | Y |
  |---|---|---|
  | gain_A 0 km/h | [0, 400, 1600, 3000] | [3072, 3072, 2434, 2048] |
  | gain_A 10 km/h | [0, 250, 1200, 3000] | [3072, 3072, 2488, 1536] |
  | gain_A 50 km/h | [0, 400, 1250, 3000] | [2664, 2664, 2243, 1436] |
  | gain_A 100 km/h | [0, 400, 1250, 3000] | [2560, 2560, 2145, 1331] |
  | **gain_B `0xD2AEC`** | [0, 400, 1500, 3000] | **[2305, 2304, 2149, 1948]** — nearly flat |
- 🛑 **LERP record layout is `count` as u16 at +0, then X[n], then Y[n]** — a u32 read shifts every field
  by 2 bytes and yields absurd counts. Caught in-session on the damper factor tables.
- ★ **8 of the 10 aggregator lanes are ZERO-GATES, not clamps.** Idiom at e.g. `0x3ACB0`–`0x3ACB8`:
  `value × (bool: in_range)` — full pass-through in range, **hard zero out of range**. A clamp keeps
  authority at the ceiling; a zero-gate **deletes the lane exactly when the signal is largest**. Only
  r24 and r26 use true saturating clamps.
- ★ **The transient statistic `|d(tq)|` is far more robust to cross-route confounds than band power.**
  V59/V64 as a true cross-route null: **0.87–0.92** (within 13% of 1.0) for transients, versus 0.63–1.23
  for band power. Prefer it for cross-route comparison. ⚠ But it is a high-pass of `tq`, so it is
  **partly the same measurement** as 18–22 Hz band power — do not double-count "cleaner everywhere" as an
  independent win.
- ⚠ **V64 CANNOT serve as a control** for stratified work: 3 episodes, CIs [0.14, 61], and it drove a very
  different profile (|rate| p50 17.8 vs 2.9). Usable only as a cross-route null for the rate statistic.

---

## FILES

**Cache/extraction:** `extract_r37_cache.py`, `r37_wallclock.py`, `r37_inventory.py` · cache
`_cache_r37/r37s0..14.npz`, `r37s*_events.json`, `r37_candidate_windows.json`.
**Analysis:** `r37_load_scaling.py`, `r37_transients.py`, `analyze_r37_final3.py`, `_r37_ratchet_lib.py`,
and the `analyze_r37_*.py` set.

**Predecessor:** `HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md`.
