# HANDOFF 2026-07-30 — the V57 drive: two symptoms, three broken conventions, and V58

**Session shape:** orchestrator + 4 subagents (route inventory, two spectral analyses, two firmware
traces). Two new routes on V57. One build (V58, unflashed). No flash, no CAN send.

---

## 1. What the operator asked, and what actually came back

> *"I did some drives on the V57 RWD… What do we see in the telemetry of these rlogs?"*

Routes `28` (street stop-and-go, segs 10-14, 5 min, to 20.33 m/s) and `29` (parking-lot grinding demo,
2 segs, 79 s). V57 fault-free on both — no `steerUnavailable`, `steerTempUnavailable`, `canError`, or
`controlsMismatch`.

**V57's own question is answered and closed.** The deadband/sign-relay gate is **inert where LKAS
applies**: 0.03% (route 28, 4/11,981) and 0.19% (route 29, 1/531) on LKAS-applying + hands-off. bit4 is
**identically zero across all 1,581 applying frames** ⇒ no chattering relay at any frequency. And the
**parity hole is closed**: all 9 bit6-vs-bus disagreements across both routes sit *exactly* on
`STEER_CONTROL_ACTIVE` transitions — 5 hole-class and 4 structurally-impossible, one per transition —
which is one-frame skew between two independent 100 Hz mailboxes, not `gp-0x6806 == 2`. The flag is
strictly {0,1} and the 2026-07-29 elimination now stands on exact equality.

**V57 was NULL for both symptoms**, as predicted.

---

## 2. 🛑 The session's biggest correction came from the operator, twice

Mid-session I concluded that the parking-lot "grinding" was a 7.4 Hz limit cycle carrying 33% of the
variance against the 20-25 Hz mode's 5.3%, and therefore that *"the kit has spent ~50 builds optimising
the 5.3% component."* That framing was wrong:

> **"grinding is not 7.4 Hz, that is the ratcheting."**
> **"steering angle excitation is just a correlation, only related by return to center"**
> **"grinding amplitude at 20 Hz was not halved in V57. perhaps your windows are too large."**

All three landed. The 7.4 Hz line is a **separate, already-named symptom**; the 20-25 Hz focus was correct
all along; and the third one was a **methodological catch the data confirmed only after he called it**:

| V57/V55, 18-26 Hz envelope | median | p90 | **p99** | **max** |
|---|---|---|---|---|
| ratio | 0.419 | 0.725 | **0.891** | **0.898** |

The "halving" lived entirely in the **median**, which is dominated by quiet time between bursts. At the
peak — what you feel — V57 is unchanged. **Mean Welch power is the wrong statistic for a bursty limit
cycle.** My earlier "21 Hz halved, three independent measurements" claim is withdrawn: two of the three
were unmatched comparisons and the third was retracted by its own author.

---

## 3. Three conventions this kit uses were producing wrong answers

Each flipped a headline. Full detail in
`memory/accord/instruments/accord-telemetry-conventions-that-produced-wrong-answers.md`.

1. **`cruiseState.enabled` is longitudinal+lateral.** It reads **0.00%** on V55 r1c, V56 r24 seg 0, and
   V57 r29 seg 1 — parking-lot routes where lateral was demonstrably applying. Using it flipped V57's
   deadband verdict from INERT (0.03%) to **NOT INERT (53.31%)**, because the gate is enabled precisely
   when lateral is off. It also inflates V56's creep baseline **28×**. Use `carControl.latActive` +
   `0x18F` byte4 bit3; they agree to 99.85-99.94%.
2. **Raw `|tq| <= 200` hands-off is self-contaminating.** The oscillation is ±1400 counts on that same
   channel. On genuinely quiet frames the raw test **keeps** 390 frames with oscillation rms 103.5 and
   **drops** 746 with rms **909.2** — **8.79× the amplitude**. It selects against the phenomenon.
3. **Envelope, not mean power** (above).

**Unsolved, and it reaches back through the whole record:** engagement and motion are **collinear** —
LKAS is active 1.7% below 0.5 m/s and ~100% above it, and **no speed bin on any route has ≥3 windows in
both arms**. So 877×, 786×, 14,750×, 27.7× are all moving-vs-stopped contrasts wearing an engagement
label. Quote absolute engaged powers until a deliberate A/B fixes it.

---

## 4. Cross-agent disputes, all resolved in bytes

Four subagents disagreed with each other or with me. Every one was settled by direct measurement rather
than by picking the more confident report.

- **`STEER_STATUS` bits.** route-health reported "100% == 0, no regression" from bits 2:0 — which the
  firmware **never writes anywhere** (boot-zeroed, spare, reads 0 forever). Real field is bits 7:4
  (`gp-0x6807`, store `0x55ca2`). Raw byte4 on route 29: `0x30 ×120` ⇒ **ST==3 fires**, 109 in seg 0
  alone. All at `vEgo == 0.000` exactly, never with LKAS applying; `0xC62EA` byte-identical across
  V55/V56/V57 ⇒ **not a V57 regression**, but it amends "ST=3 never fires on V53+". It took two rounds to
  land.
- **The "biquad".** tributary-trace found a 2-pole structure at `0xC4018/1C/20`; damping-census had
  reported "no biquad anywhere". Both half-right: I byte-read the coefficients — **floats (1.0, 0.0,
  0.0)**, an identity configuration — so a *structure* exists and is *disabled by calibration*. Then
  damping-census proved it is a **3-tap FIR, not an IIR** (no y[n−1]/y[n−2] feedback), i.e.
  unconditionally stable. **Then I killed it on arithmetic:** at 1 kHz a 21 Hz notch needs
  `b = [1, −1.9826, 1]`, costing **−35.2 dB at DC** (21 Hz is 2.1% of Nyquist, so the zeros sit at DC);
  normalising needs `b ≈ (57.5, −114.0, 57.5)` with **229× peak gain**. Dead as a lever, before a build.
- **The `0xC61D6` "fresh" rate limiter.** Surfaced as the ratchet's cause. It is **REJECTED** — an
  11-round 4-analyst review found slew=0 *freezes* a dormant 2D shaping lane and 0→14 **activates an
  uncalibrated map onto the live command**; *"highest-risk lever; last/never."* Two process failures let
  it resurface: `0xC61D6` appears nowhere in `BUILD-LINEAGE.md` (which covers V9→V58, and V16 is a
  pre-V18 `archive/old_tools/` build), and an agent-memory still closed with *"FIX = set 0xC61D6 to 14."* Both
  fixed.
- **`0xC6372`/`0xC636E`.** damping-census retracted its own GATE-2 analysis: `tp+0x7498 = tp+0x7499 = 1`
  routes **both** boost and damping past the torque EMA to read `gp-0x6ba6` directly. It is a **dead
  branch** — the arithmetic was right, its relevance was nil.

---

## 5. The two symptoms, as they now stand

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz**, Q≈36, 2nd harmonic locked at 15.0 Hz | **20-25 Hz** |
| variance share (r29 burst) | **33.0%** | **5.3%** |
| vs rail duty | **8.42×** up (partial r = +0.810 vs angle) | 0.74× |
| commanded? | no — command's 6-9 Hz peak is 6.26 Hz, 6.4 bins away | no |
| cal lever | **none** — all closed | **none** with a certified sign |

The ratchet is **not** the V42 state-4 ratchet (`ST==4` fires 0/37,922). Over 0.21 s the command drifts
510 counts while the bar swings **2,791 counts through 3 sign changes**. Present on V55 too ⇒ not new.

**Grinding levers, all closed this session:** no usable notch (above) · `0xC6372`/`0xC636E` dead branch ·
damping's own table `0xD2738` is flat unity, a no-op · Factor E `Y[3]` is a ~10% bump on a mechanism V47
already opened far wider and had falsified · `gp-0x6bbe`'s sign unresolved.

**Why unresolved:** `gp-0x6a56` — what the EPS transmits as `STEER_ANGLE_RATE` — is **not independently
sensed**. `FUN_0003f776` computes it as `clamp(polarity × ((gp-0x6abe × 48 × cal) >> 15), ±12000)`, a
fixed scale of the **motor resolver rate**. And `baseline` is *also* `gp-0x6abe`-derived, so
`rate_error = baseline − angle_rate` may partially cancel. The sign flip-flopped four times; the golden
model can't settle it (`base_driver_assist_lane` is flagged `[SIMPLIFIED]` at exactly that point).

---

## 6. V58 — measure it instead

`39990-TVA,A160-V58-…-boostlaneprobe-can330byte4-…rwd`, SHA `7b3cfff0…`, **BUILT, UNFLASHED**.

V57 with **only** the cave payload replaced — same base `0xC4B34`, hook `0x55C0E`, 68-byte extent, an
envelope that has flown fault-free twice. **59 bytes off V57**, and the **CAL CRC is unchanged**: machine
proof that no calibration byte moved.

```
bit7 liveness · bit6 = sign(gp-0x6bbe) THE DAMPING PHASE · bit5 = gp-0x6bbe == +512
bit4 = sign(gp-0x6b9a) · bit3 = gp-0x6b9a == 0
```

`STEER_ANGLE_RATE` is already on the bus, so the cross-spectrum phase of bit6 against it at 20-25 Hz gives
the damping sign directly. **The method was validated before the build, not assumed:** V57's bit3 — also a
1-bit sign channel — returned **coherence 0.958 at 21.31 Hz**. bit5 decides whether `K1` is a lever at
all, since the ±512 ceiling is a *saturating* clamp and a pinned lane has zero damping derivative exactly
at the peaks.

Verification: 50/50 CRC on the built image *and* readback · RWD round-trips byte-identically · cave
re-disassembled **from the built image** instruction-by-instruction · diff restricted to
`[0x13000,0x100000)` · encoders' operand fields decoded out of the encoding rather than trusted · only
condition codes pinned to real instances (`BGE`, `BNE`; `BLT` pinned at `b6 05` @`0x1c006` but designed
around).

⚠ **The decoder had a silent-null bug I caught only because I knew the answer.** One `0x14A` frame arrives
before the first `0x18F`, leaving torque `NaN`; a single NaN propagates through the FFT and makes every
sustained-effort value NaN — reading out as *"0 hands-off frames"*, a plausible finding rather than an
error. Fixed at source, `sustained()` made NaN-safe with an assert.

---

## 7. Also settled

- ✅ **The tyre line is confirmed and firmware-independent.** Order tracking (rescale each window by its
  own wheel frequency before pooling) puts **both** V57 and V56 at **order 1.000**, circumference
  **2.088 m**, with the estimator calibrated on V56 first where the answer was known. Per-window on V57's
  road episode: 2.056-2.105 m, 715× prominence burst at 19.5 m/s. ⇒ **get a wheel balance / road-force
  check.**
- 🛑 **The "8.69 Hz line V56 introduced" never existed** — it is wheel order 1 at the ~18 m/s V56 happened
  to drive (`0.489·v − 0.186`). Its absence on V57 is **not** evidence the `0xC6AF0` mute was live; that
  "cleanest liveness proof" was never a test.
- 🛑 **`FUN_0004613e` is not a rate limiter** — a fault logger; `0x3638` is a diagnostic tag. The
  `gp-0x6bb2/4/6/8` cluster is a cross-tick integrity watchdog with no forward path. Golden model
  corrected; self-check output verified **byte-identical** before/after.
- ⚠ The two `STEER_ANGLE_RATE` copies disagree by a **constant 1.25×** — one DBC scale factor is wrong.
  Frequencies/Q/ratios unaffected; absolute deg/s figures are not.

---

## 8. Next session

1. **Flash V58** and drive the A/B below. It answers on-car what four rounds of static analysis could not.
2. **The route spec — this is the deliverable, not a detail.** Parking-lot creep, LKAS applying, wheel
   held at a **fixed 20-30°**, hands light enough that **sustained effort stays under 200 counts for ≥3 s
   at a stretch**, **openpilot not railed** (command near 1,800 to match route 1c), repeated ≥5 times,
   with deliberate LKAS-on/off passes at matched speed and angle, plus a slow driver-torque ramp
   0 → 2240 → 3000 → 0 (≥3 s per ramp, ≥5 times). *Why:* V57 r29 has only 437 qualifying frames in 6
   fragments — **no 2.56 s window exists** — and its command sat at 3,851 vs V55's 1,801, so the
   `0xC646C` A/B could not be computed and the driver-torque-knee test could not be resolved (its pooled
   7× collapse is carried by 1 of 3 excursions, one of which shows an *increase*).
3. **Rebuild the historical baselines** on lateral engagement + sustained-effort hands-off + envelope
   statistics before trusting any amplitude comparison.
4. **The ratchet needs a mechanism.** No cal lever exists. `gp-0x6b62` (return-centre, ZERO-gated
   ±0x2000) has never been probed and matches the operator's own return-to-centre framing.

## Housekeeping

Removed the stale duplicate V57 RWD (`…v55probe-plus-0xC646C-decouple…`, SHA `816d2255…`) — an earlier
iteration superseded before flashing. The one on the car is `…mss0-decouple0xC646C-deadbandprobe…`,
SHA `6263acf1…`, which matches `STATE.md`.
