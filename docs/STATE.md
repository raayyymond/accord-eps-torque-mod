# STATE — living current state of the kit

**Last updated: 2026-07-30.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed, falsified, or **rejected on
review** — check it before proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md`.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it.

---

## 🛑🛑 THE TWO SYMPTOMS ARE DIFFERENT PHENOMENA — settled by the operator 2026-07-30

Everything before this date conflated them. Read this before any other section.

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz** (Q≈36, 2nd harmonic locked at 15.0 Hz) | **20–25 Hz** (`f ≈ 0.177·v + 20.48`) |
| where it dominates | parking-lot creep at large steering angle | road speed; present at creep too |
| variance share, r29 burst | **33.0%** (6–9 Hz) | **5.3%** (19–24 Hz) |
| vs command saturation | **rises 8.42×** with rail duty | falls to 0.74× |
| in openpilot's command? | **no** — command's 6–9 Hz peak is 6.26 Hz, 6.4 bins away | no |

⚠ **Operator correction, authoritative:** the 7.4 Hz line is the **ratcheting**, not the grinding. An
earlier pass this session called it "the grinding" and concluded the kit had been chasing the wrong mode
for 50 builds. **That conclusion is withdrawn** — the 20–25 Hz focus was correct all along.
⚠ **Steering-angle excitation of the 7.4 Hz mode is a CORRELATION only**, related through return-to-centre.
Do not treat angle as causal.

**The ratchet is not the V42 ratchet.** `STEER_STATUS == 4` fires in **0 of 37,922 frames** across both
V57 routes, so the state-4 governor (`0x454FE`, root-caused and fixed by V42) is not producing it.
Mechanism unknown. It is a plant limit cycle gated by applied LKAS torque, not commanded: over 0.21 s the
command drifts 510 counts while the torsion bar swings **2,791 counts through 3 sign changes**.

---

## On the car right now

**V57** = V55 + the `0xC646C` decoupling + the deadband-gate probe. Flashed and driven 2026-07-29–30,
routes `28` (street stop-and-go, 5 min, to 20.33 m/s) and `29` (parking-lot grinding demo, 79 s).
Fault-free. No `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch` on either route.

```
0xC646C  shared sensor scale = 891 (stock)     <- was 3564 on V38..V56
0xC6CD0  private LKAS forward gain = 3564      <- V57's new cell
0xC62EA  low-speed lockout = 0                 <- V53, unchanged
0xC64DE  re-engage ramp = 27                   <- V18, carried forward correctly
_v57_plain_image.bin  SHA 351735984aa0ec43572e94a0592b2fe8758d9a8e93c9844fcc226dd091179125
V57 .rwd              SHA 6263acf185a00849c4dd0556f15bd834faf63a9795c610228d83d64eadb5dd3b
```

**V57's on-car result:**
- ✅ **The deadband/sign-relay elimination is CLOSED, on exact equality.** Probe bit6 (`gp-0x6806 == 0`)
  on LKAS-applying + hands-off: **0.03%** (route 28, 4/11,981) and **0.19%** (route 29, 1/531). bit4
  (gate output == 0) is **identically zero across all 1,581 applying frames** ⇒ no chattering relay at any
  frequency. **No parity hole**: all 9 bit6-vs-bus disagreements across both routes sit *exactly* on
  `STEER_CONTROL_ACTIVE` transitions (5 hole-class + 4 structurally-impossible), i.e. one-frame skew
  between two independent 100 Hz mailboxes. `gp-0x6806` is strictly {0,1}.
- 🛑 **NULL for both symptoms**, as predicted. Burst-resolved envelope, V57/V55 at matched creep:
  grinding 18–26 Hz **p99 0.891 / max 0.898** (unchanged); ratchet 6–9 Hz 0.85–1.12 (unchanged).
  ⚠ The *median* ratio is 0.419, which earlier in the session was misreported as "the 21 Hz halved."
  **That was a windowing artifact** — see the methodology section.

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **V58** | V57 + cave payload replaced by the **angle-rate/boost-lane probe** | ✅ **BUILT 2026-07-30, UNFLASHED.** `0x14A` byte4: bit7 liveness, **bit6 = `gp-0x6bbe < 0` (the damping phase)**, bit5 = `gp-0x6bbe == +512` (pinned at ceiling), bit4 = `gp-0x6b9a < 0`, bit3 = `gp-0x6b9a == 0`. **59 bytes off V57** (cave + MAIN CRC only — the **CAL CRC is unchanged**, machine proof no calibration moved), 86 off V38. Same base `0xC4B34`/hook `0x55C0E`/68-byte extent as V55 and V57, both of which flew fault-free. 50/50 CRC, RWD round-trip, cave re-disassembled from the built image. Decoder `rlog-tools/decode_v58_boostlane.py`. RWD SHA `7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7`; image SHA `431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48` |
| **V55** | the pre-V56 revert target | ✅ built, driven, fault-free. SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~V56~~ | the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED.** Do not re-flash |

🛑 **Flash only on explicit operator instruction naming the file and the bus.** Kill openpilot/pandad first.

---

## 🛑 METHODOLOGY — three conventions that were producing wrong answers

These invalidate *reasoning* behind earlier conclusions. None changes a measured on-car outcome, but
every historical amplitude comparison needs rebuilding before it can be trusted.

1. **`carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG engagement proxy.**
   It reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot
   routes where lateral was demonstrably applying. On route 28 it reads 84.0% while lateral applied 49.9%.
   **Use `carControl.latActive`, corroborated by CAN `0x18F` byte4 bit3 (`STEER_CONTROL_ACTIVE`).** The
   three agree to **99.85–99.94%**. Using cruiseState flipped V57's headline verdict from INERT to
   NOT INERT, and inflates V56's creep baseline **28×** by sweeping in hands-on parking manoeuvres at
   |ang| 89.6°.
2. **Hands-off must be SUSTAINED effort `|lowpass(tq, 3 Hz)| ≤ 200`, never raw `|tq| ≤ 200`.**
   The oscillation is ±1400 counts *on the torsion-bar channel itself*, so it trips the raw test by
   itself: 68.3% of frames scored "hands-on" have the driver doing nothing sustained. On genuinely quiet
   frames the raw test **keeps** 390 frames with oscillation rms 103.5 and **drops** 746 with rms 909.2 —
   **8.79× the amplitude.** It selects *against* the phenomenon. Switching recovers 2.5× more usable
   frames and turns subsets that had no contiguous run into computable numbers.
3. **Mean Welch power is the wrong statistic for a bursty limit cycle — use peak/p99 envelope.**
   V57/V55 grinding: median 0.419 but **p99 0.891, max 0.898**. The "halving" lived entirely in the
   median, which is dominated by quiet time between bursts. Operator called this before the data did.

⚠ **A fourth problem, not yet solvable:** **engagement and motion are collinear.** LKAS is active 1.7%
below 0.5 m/s and ~100% above it (corr = +0.627); **no speed bin on any route has ≥3 windows in both
arms.** So the recorded engaged/disengaged ratios (877×, 786×, 14,750×, 27.7×) are moving-vs-stopped
contrasts wearing an engagement label. **Quote absolute engaged powers instead.** Breaking this needs a
deliberate LKAS-on/off A/B at matched speed and angle.

---

## Signal-identity corrections of record

- 🛑★★ **`gp-0x6a56` is NOT independently sensed.** `FUN_0003f776` (sole producer, 4 `st.h`, all inside it):
  `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)` — a fixed Q15 scale of
  the **motor/resolver electrical rate**. The ±12000 is a magnitude clamp recomputed fresh each tick, not a
  rate limit; `gp-0x6a60` merely mirrors its magnitude. ⇒ **`STEER_ANGLE_RATE` is opendbc-named but is not
  an independent angle sensor**, so "996× on rate vs 877× on torque" is two EPS-internal derivations, not
  independent corroboration. And since `gp-0x6bbe`'s `baseline` is **also** `gp-0x6abe`-derived,
  `rate_error = baseline − angle_rate` may partially cancel ⇒ **the damping sign is UNRESOLVED.**
- 🛑 **`FUN_0004613e` is not a rate limiter.** It snapshots params into log cells and calls
  `FUN_00016de6(0x1c,…)`, a fault logger; **`0x3638` (13880) is a diagnostic TAG** (the same callee takes
  `0x38c7` elsewhere). The `gp-0x6bb2/4/6/8` cluster is a cross-tick **integrity watchdog** re-deriving the
  same ±512 ceiling in float, with **no forward path into any control signal**. Golden model corrected.
  ⚠ Its fault path calls `FUN_000462e6(0x39e9,…)` **ungated** — Monitor 2's hard-shutdown chain. Any edit
  to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table `0xD2018` to match, or it may trip.
- 🛑 **`0xC6372`/`0xC636E` is a DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every
  build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. Any
  GATE-2 analysis of those two cals is analysing a lever with zero effect on this firmware.
- **The FIR slots are real but cannot notch.** `FUN_0003b66a` implements a genuine **3-tap transversal FIR**
  (`y[n] = b0·x[n] + b1·x[n−1] + b2·x[n−2]`, two persisted delay states `gp-0x365c`/`gp-0x3658`) — **not a
  2-pole IIR biquad**, so it is unconditionally stable. Coefficients `0xC4018/1C/20` = floats
  **(1.0, 0.0, 0.0)** = identity; a second instance `0xC4048/4C/50` (`FUN_0003b8f6`) is also identity.
  Exactly **one consumer each**. See "closed levers" for why enabling them fails.
- 🛑 **The ±565/cycle slew in `FUN_0003b66a` is a CODE IMMEDIATE** (`mov 0x440d4000,r6` = 565.0f), not a
  calibration. Editing it is a code-patch-class change. The halfword 565 in the cal region
  (`[0,191,402,565,686,804,878]` at `0xCE43C` etc.) is an unrelated LERP entry — numeric coincidence.
- ⚠ **The two `STEER_ANGLE_RATE` copies disagree by a constant 1.25×** (`0x18F[2:4]×−0.1` reads 0.799–0.800
  of `0x14A[2:4]×−1.0`, corr +0.9997). One DBC scale factor is wrong. Frequencies, Q, prominence and ratios
  are unaffected; **absolute deg/s figures are not.**
- 🛑 **`STEER_STATUS` is `0x18F` byte4 bits 7:4**, not bits 2:0 (which are SPARE — never written anywhere in
  the image, boot-zeroed, read 0 forever). Reading bits 2:0 yields a tautological "always 0". Route 29 shows
  `ST==3` in **120 frames**, all at `vEgo == 0.000` exactly, never with LKAS applying, in two episodes
  (1.08 s at log start, 0.10 s at t=77.8 s). **Not a V57 regression** — `0xC62EA` is byte-identical across
  V55/V56/V57. Amends the record's "ST=3 never fires on V53+".
- 🛑 **The "8.69 Hz line V56 introduced" never existed — it is wheel order 1.** V56's 35 windows sat at
  v ≈ 18 m/s where `0.489·v − 0.186 = 8.69`; its own edge windows move to 7.03 and 9.77 Hz, and V57 tracks
  identically (7.03 → 8.98 → 9.38). **Its absence on V57 is NOT evidence the `0xC6AF0` mute was live** — a
  different liveness proof is needed.
- ⚠ **The recorded V56 baseline `7.66e4` is suspect** — within 5% of route 24 seg 0's *all-frames* power,
  and that segment contains **zero** LKAS-applying frames.

---

## ✅ The tyre line — CONFIRMED, firmware-independent, and actionable

Order tracking (rescale each window's frequency axis by its own wheel frequency before pooling) puts
**both** builds at **order 1.000**:

| build | K | v range | order peak | prom | implied circumference |
|---|---|---|---|---|---|
| **V57 / r28** | 9 | 4.2–20.1 m/s | **1.000** | 11.7 | **2.088 m** |
| V56 / r24 | 59 | 9.5–20.5 m/s | **1.000** | 6.2 | **2.088 m** |

Estimator calibrated on V56 first, where the answer was known. Decoys at order 0.70/1.40/1.80/2.00 all
score far below. Per-window on V57's road episode: 2.056–2.105 m, with a 715× prominence burst at
19.5 m/s. A 235/45R18 is 2.05–2.11 m ⇒ **one line per wheel revolution**.

⇒ 🛑 **Get a wheel balance / road-force check.** Firmware cannot move a road input, and it didn't.

★ Separately, a **fixed ~7.4 Hz resonance** is present on V57 (Q 36.2 at nfft=1024, prominence 40–136×) at
1.2 m/s where wheel order is only 0.59 Hz ⇒ **not the tyre**. It is the ratchet. Route 28's creep misses it
because that creep is |ang| 5.8° — **excitation, not absence** (r29 creep is 26.5°, matching the historical
set's 12.6–42.2°).

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction. openpilot remains a *measurement
instrument* only.

1. ★★ **Flash V58 and drive the A/B route below.** V58 answers, on-car, what three rounds of static
   analysis could not: the `gp-0x6bbe` damping sign (bit6 phase vs the bus's rate copy at 20–25 Hz) and
   whether the lane pins at its ±512 ceiling (bit5), which decides whether `K1` is a lever at all.
   **Method pre-validated:** V57's bit3 — also a 1-bit sign channel — returned **coherence 0.958 at
   21.31 Hz** against `STEER_ANGLE_RATE` on route 29's burst.
2. ★★ **The route to drive, which fixes the collinearity problem:** parking-lot creep, LKAS applying,
   wheel held at a **fixed 20–30°**, hands resting **lightly enough that sustained effort stays under 200
   counts for ≥3 s at a stretch**, and **openpilot not railed** (command near 1,800, matching route 1c).
   Repeat ≥5 times, with deliberate LKAS-on/off passes at matched speed and angle. Add a slow driver-torque
   ramp 0 → 2240 → 3000 → 0, ≥3 s per ramp, ≥5 times, to settle the override-knee question.
   *Why this spec:* V57 r29 has only 437 qualifying frames in 6 fragments — no 2.56 s window exists — and
   its command sat at 3,851 vs V55's 1,801, so the `0xC646C` A/B could not be computed.
3. **Re-derive every historical amplitude baseline** on sustained-effort hands-off + lateral engagement +
   envelope statistics. Until then treat 877× / 786× / 14,750× / 7.66e4 as provisional.
4. **The ratchet has no cal lever and no mechanism.** All rate-limit candidates are closed (see
   `BUILD-LINEAGE.md`). Next step is measurement, not a build. The return-centre lane `gp-0x6b62`
   (aggregator, ZERO-gated ±0x2000) has never been probed and is the operator's own hypothesis.
5. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
6. **The take-over beep is closed** — `commIssue`/`selfdrivedLagging` under device CPU load, clean CAN/EPS
   null. Seen again on both V57 routes (route 28's at t=126.5 s produced a real soft-disable).

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** `gp-0x6966` is wind-up-driven, not
speed-driven, and V31's boost floor makes wind-up unreachable (V54 measured this on-car under railed
command).

---

## Still-standing results worth not re-deriving

- **`gp-0x6966` authority ≡ 0 by design on V31+** — soft-EME wind-up magnitude, pinned by V31's boost
  floor; `0xC6AF0` selects unity in 100% of normal operation. Measured on-car, route `1b`, 5,989/5,989.
- **Steer-to-zero works** — `0xC62EA` = 0, `ST=3` never fires while moving, 226 frames of
  `STEER_CONTROL_ACTIVE=1` below 5 km/h on route `1a`.
- **The `0x14A` byte4 bits 7:3 piggyback is proven across FOUR flashes** (V54, V55, V56, V57). Use it for
  all future firmware telemetry; **do not build another new-mailbox channel** (FOURFRAME2 was never
  transmitted — that null remains uninterpretable).
- **No notch/biquad exists anywhere** on the arb, aggregator, r24/r26, comp-add, boost/damping/friction,
  shaper, or governor paths, nor in the three non-aggregator consumers of `gp-0x6b94`
  (`FUN_0004503c` governor, `FUN_0004595a` redundancy monitor, `FUN_0007ff08` boot interlock). Two regions
  remain unswept: the raw CAN → `gp-0x4f60` producer, and the FOC current loop below `gp-0x6b98`.
- **An rlog cannot identify the flashed build from the version string** — every build reports
  `fw='39990-TVA,A160'`. Behaviourally: `ST=3` never firing while moving ⇒ V53+; probe field semantics
  identify V54/V55/V56/V57/V58 exactly.
