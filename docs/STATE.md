# STATE — living current state of the kit

**Last updated: 2026-07-30.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed, falsified, or **rejected on
review** — check it before proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md`
(predecessor: `HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md`).

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it.

---

## 🛑🛑 THE TWO SYMPTOMS ARE DIFFERENT PHENOMENA — settled by the operator 2026-07-30

Everything before this date conflated them. Read this before any other section.

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz** (Q≈36, 2nd harmonic locked at 15.0 Hz) | **FIXED ~20.9 Hz** ⚠ see below |
| where it dominates | parking-lot creep at large steering angle | ⚠ **CREEP-ONLY on V58** — see below |
| variance share, r29 burst | **33.0%** (6–9 Hz) | **5.3%** (19–24 Hz) |
| vs command saturation | **rises 8.42×** with rail duty | falls to 0.74× |
| in openpilot's command? | **no** — command's 6–9 Hz peak is 6.26 Hz, 6.4 bins away | ⚠ **YES** — see below |

🛑 **Three entries in that table were corrected by the V58 drive (route `2b`, 2026-07-30).** They are
left visible above with pointers rather than silently overwritten:

1. **The frequency law `f = 0.177·v + 20.48` does NOT reproduce.** Strict 18–26 Hz band, sub-bin peak,
   speed stable within 1.5 m/s: slope `a = −0.005 … +0.031` at every prominence cut (n = 23–75, v span
   1.13–17.5 m/s). **`a = 0` fits within 0.12–1.48σ; `a = 0.177` is rejected at 3.2–7.1σ.** Model-free
   per bin: 20.65 / 20.83 / 21.90 / 21.50 / 21.61 / 20.46 Hz over 0–20 m/s vs a predicted 20.66 → 23.49.
   ⚠ **Do not rewrite the law off one route yet** — the recorded value came from a *pooled cross-route*
   fit whose own source warned "steering angle shifts it ±2 Hz", and on route `2b`
   `spearman(v,|ang|) = −0.728`. Re-run the strict-band test over V55/V56/V57 first (step 2 below).
   ⚠ **Search-band trap:** a 15–30 Hz or 17–28 Hz band catches the **ratchet's 2nd harmonic**
   (2×8.0–8.9 = 16–17.8 Hz) at road speed; the argmax then steps down to ~15 Hz and fakes a *negative*
   slope. A creep-only window fakes a *positive* one. Use 18–26 Hz **plus a presence test**.
2. **Creep-only, not road speed.** 18–26 Hz prominence by speed (engaged): 141× / 138× / 518× at
   1–2 / 2–3 / 3–4 m/s, collapsing to 29× / 11× / 8× / 7× at 4–6 / 6–10 / 10–14 / 14–18 m/s — and above
   6 m/s the peak-frequency scatter (sd 1.5–2.2 Hz) shows there is no coherent line at all.
3. **~21 Hz IS in openpilot's command.** Verified on the **native 0xE4 grid**, so not a held-last
   resampling artifact: 20.89 Hz at prominence 34.0×, `coherence(cmd, bar) = 0.917` at 20.96 Hz (K=4,
   95% null 0.632); co-located command peak in 8/21 strong-line windows vs 1/11 weak. The bar's line is
   6–7× sharper, which reads as an echo — but **direction is unresolved.** Carrier phase cannot settle it
   (one-sample mailbox skew = 75° at 21 Hz), and the skew-robust **envelope** cross-correlation was
   **inconclusive** (2/4 runs bar-leads, 2/4 command-leads, peak corr only 0.33–0.44). ⇒ openpilot is
   inside this loop; that is a constraint on any firmware fix, not an action.

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

**V58** = V57's calibration + the angle-rate/boost-lane probe in the cave. Flashed and driven 2026-07-30,
route `2b` (normal commute, 14 segments, ~14 min, 83,959 frames, creep → highway → parking).

```
0xC646C  shared sensor scale = 891 (stock)     <- was 3564 on V38..V56
0xC6CD0  private LKAS forward gain = 3564      <- V57's new cell
0xC62EA  low-speed lockout = 0                 <- V53, unchanged
0xC64DE  re-engage ramp = 27                   <- V18, carried forward correctly
_v58_plain_image.bin  SHA 431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48
V58 .rwd              SHA 7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7
```

**V58 is FLIGHT-CLEAN.** `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/
`immediateDisable`: **0 across all 14 segments** (raw `onroadEvents` scan, verified twice). The only
flags are `commIssue`×2 + `selfdrivedLagging`×1, all at seg 0 t≈8.5 s **in `wrongGear` before the drive
started** — a boot transient, unlike route 28's real mid-drive soft-disable. `STEER_STATUS == 0` in
**83,959/83,959** frames; **`ST==4`: 0**, extending V57's 0/37,922 to 121,881 combined clean frames.
Probe low bits `& 0x07 == 0b111`, zero exceptions. `0x14A`/`0x18F` at 100.00 Hz in every driving segment.

**V58's on-car result — see the handoff for the full numbers:**
- ★★ **The collinearity confound is BROKEN.** Seg 13 gives 60 s of *moving but disengaged* at
  0.5–4.8 m/s. Speed-matched grinding: **13.4×** [95% 3.9–19.8], **16.9×** speed+effort-matched, and
  **184×** on time-occupancy at matched creep. Better than any ratio — **the resonance is ABSENT
  disengaged**: prominence median 122.7× vs 3.6×, with the disengaged "peak" wandering 15–29.9 Hz
  (sd 2.49 Hz) i.e. the argmax of a floor. Confounds run *against* the engaged arm (disengaged has
  |ang| 167° vs 9°, effort 1638 vs 205). ⇒ **the grinding requires applied LKAS torque. Settled.**
- ✅ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED.** The lane never pins, so
  `K1` @`0xD200C` = 43 keeps its headroom.
- 🛑 **bit6 VOID BY CONSTRUCTION.** `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s; it is
  DC-dominated. **The damping sign is STILL OPEN.** ⚠ Pooling runs to force an answer manufactures a
  splice artifact (bit6 has 5/0/0/1 transitions *within* the four engaged runs, so a concatenated
  "coherence 0.5 at 25 Hz" is step discontinuities at the joins). **A sign comparator is a phase probe
  only for a signal that crosses zero at the frequency of interest.**
- ★★ **bit4 FIRED and is the lead.** `sign(gp-0x6b9a)` at 20.93 Hz, per-run coherence
  0.649/0.970/0.769/0.881, own-spectrum peak 10.8× median, `corr(envelope, toggle rate) = +0.834`.
  At matched creep: **13.69 toggles/s engaged vs 0.61 disengaged**, 20.93 Hz line present in one arm and
  absent in the other, duty cycle barely moving ⇒ it *oscillates*, it does not merely sit elsewhere.

🛑 **Hands-off could not be conditioned on anywhere on this route** — zero fully-hands-off windows in
either arm in any qualifying speed bin. Everything above is "any hands", matched on effort instead.

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **V59** | V58 + cave payload replaced by the **boost-index DEPTH probe** | ✅ **BUILT 2026-07-30, UNFLASHED.** `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense is "index < T", which is what lets the whole cave run on the two pinned condition codes). **19 bytes off V58** (cave + MAIN CRC only; **CAL CRC unchanged** = machine proof no calibration moved), 86 off V38. Same base `0xC4B34`/hook `0x55C0E`/68-byte extent as V55/V57/V58, all flown clean. **No new encoder, no new condition code.** 50/50 CRC, RWD round-trip, cave re-disassembled from the built image; the build also asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic rather than reporting on a surviving subset). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| **V55** | the pre-V56 revert target | ✅ built, driven, fault-free. SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~V56~~ | the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED.** Do not re-flash |
| ~~V57~~ | the `0xC646C` decoupling + deadband probe | ✅ flashed, fault-free; its calibration is carried by V58 |

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

✅ **A fourth problem, SOLVED 2026-07-30 by route `2b`:** engagement and motion used to be collinear —
no speed bin on any route had ≥3 windows in both arms, so the recorded ratios (877×, 786×, 14,750×,
27.7×) were moving-vs-stopped contrasts wearing an engagement label. **Route `2b` breaks it**: seg 13 is
60 s of *moving but disengaged* at 0.5–4.8 m/s against engaged creep at overlapping speeds, giving 3 of
9 speed bins with windows in both arms (18 v 18 windows, but only ~10 independent episodes per arm —
treat n as episodes, not windows). ⇒ **13.4× amplitude [95% 3.9–19.8], 16.9× speed+effort-matched.**
🛑 The old ratios stay retired; **do not resurrect 877×/786×/14,750×** — they were never engagement
contrasts. Quote the route-`2b` numbers, or absolute engaged powers.

⚠ **A fifth convention, learned the hard way this session: use a STRICT 18–26 Hz band plus a presence
test, never a wider search band.** A 15–30 Hz or 17–28 Hz argmax catches the ratchet's 2nd harmonic
(2×8.0–8.9 Hz = 16–17.8 Hz) at road speed and steps down to ~15 Hz, manufacturing a *negative* frequency
slope out of a mode switch. Two independent analysts produced two contradictory "frequency laws" this way
before the band was tightened.

⚠ **A sixth: prominence, not envelope amplitude, is what separates a mode from broadband.** The
disengaged arm's loudest 18–26 Hz moments are single-digit prominence at |ang| up to 295° — a driver
cranking a wheel. An envelope-ratio headline divides one broadband spike by another; the prominence
contrast (34× grinding vs 6.1× ratchet) and the presence/absence are the defensible statistics.

---

## Signal-identity corrections of record

- 🛑★★ **`gp-0x6ba6 == |gp-0x6b9a|`, and `gp-0x6ba6` — not `gp-0x6b9a` — is the boost amplitude index.**
  Byte-verified 2026-07-30; **`build_v58_tva.py`'s docstring was wrong on both counts** and is corrected
  in place. `FUN_0003b66a` writes both from the same r28 (`cmp r0,r28 / mov r28,r13 / bge / subr r0,r13`
  @`0x3b874-87c`, then `st.h` @`0x3b892` and `@0x3b8b0`; byte-scanned for **both** gp-relative encodings:
  exactly one writer each). `gp-0x6b9a`'s only live consumer in `FUN_00034a72` is a **five-input
  plausibility gate** (`|x| ≤ 25600` @`0x34c9c-cb4`, ANDed with `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/
  `gp-0x6c2e` into r21, which zeroes r24 @`0x34fc8`) — **its sign has no effect on the output**, and two
  of its three reads there (`0x34b5e`, `0x34b68`) are **dead** (`tp+0x7499 = 1` takes the branch
  @`0x34b3c`). **`0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`** (which resolves to
  `0xD2888`); resolved from image bytes across all 34 modes.
  ⇒ **THE MECHANISM:** V58 measured the *signed* sibling crossing zero at 20.93 Hz only when LKAS
  applies, so the index is that signal **full-wave rectified** — a minimum at every zero crossing,
  sweeping the boost amplitude curve (`0xD28DC` Y = 16384→8187, `0xD2888` Y = 16384→8176) at **~2× the
  mode frequency on the BASE ASSIST path**. ⚠ **INFERENCE, depth unmeasured**: a sign bit carries no
  amplitude, and the delivered swing depends on how far up the curve the index climbs —
  `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert"
  below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero.
  **V59 measures which regime. Do not move `0xD28DC`/`0xD2888` until it has flown.**
- ⚠ **`FUN_0003b66a` branch A is NOT a biquad** — a subagent claimed "a genuine floating-point 2-pole
  biquad, IIR by definition"; it is not. `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** It is the identity 3-tap FIR already on record, so **"no biquad
  anywhere" survives and there is no new notch candidate.** Also new: `tp+0x74be = 0` (`0xC64BE`) makes
  `0x3b736–0x3b758` (the `divf.s` block) dead code.
- ⚠ **`search_instructions` undercounted again** — 8 access sites for `gp-0x6b9a` where a Python byte
  scan finds **9** (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). The sole-writer
  conclusion held, but only because it was re-derived. **Never let a writer/reader set rest on it alone.**

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

1. ★★ **Flash V59 and drive the creep route below.** The whole question is **depth**: how far up the
   amplitude curve does the index climb during the bursts? Read the thermometer to bracket the swept
   Y range and hence the delivered gain swing (`<512 ⇒ ≤1.12×` … `≥5120 ⇒ 2.00×`). ⚠ A "stays below
   512" result is **weak, not inert** — the curve interpolates from X = 0 — so the decision is whether
   the swing justifies a GATE-2 review of a base-assist lever, not a clean yes/no.
2. ★★ **The route to drive:** parking-lot / low-speed creep, **v ≤ 5 m/s** (the mode is creep-only —
   route `2b` wasted most of 14 minutes on highway where there is no line at all), LKAS applying, wheel
   held at a **fixed 20–30°**, and — the thing route `2b` could not give — **sustained hands-off
   stretches ≥ 3 s** (`|lowpass(tq,3Hz)| ≤ 200`). Repeat ≥5 times with deliberate LKAS-on/off passes at
   matched speed and angle. Add a slow driver-torque ramp 0 → 2240 → 3000 → 0, ≥3 s per ramp, ≥5 times,
   for the override knee. *Why:* route `2b` had **zero** fully-hands-off windows in either arm, so every
   V58 number is "any hands"; and its knee table shows the real transition between 200–500 and
   500–1000 counts, with no feature at 2240 — but that measures openpilot's `e4tq` response, **not** the
   firmware-internal knee, which is not on CAN.
3. **Re-run the strict-band (18–26 Hz + presence test) analysis over the V55/V56/V57 routes** before
   rewriting the frequency law. One route cannot kill a cross-route fit, but the cross-route fit is now
   suspect (pooled, and speed/angle are anti-correlated at ρ = −0.728 here). Same pass should re-derive
   the historical amplitude baselines on lateral engagement + sustained-effort hands-off + envelope
   statistics; until then treat 7.66e4 as provisional.
4. **The ratchet has no cal lever and no mechanism.** All rate-limit candidates are closed (see
   `BUILD-LINEAGE.md`). Next step is measurement, not a build. The return-centre lane `gp-0x6b62`
   (aggregator, ZERO-gated ±0x2000) has never been probed and is the operator's own hypothesis.
   🛑 **Route `2b` cannot speak to the ratchet in either direction, and the operator said so before the
   data did.** Hands-off + engaged + `|e4tq| ≥ 3500` + v ≤ 3.0 m/s yields **9 runs / 139 frames (~1.4 s)**,
   all inside one 8 s window in seg 1 that overlaps a hands-on manoeuvre sweeping −24° → +302° — i.e.
   transient zero-crossings of the lowpassed effort signal *during* hands-on driving. **Zero clean
   episodes.** The driver-applied sharp turns don't show it either: 6–9 Hz sits at or below a strict
   quiet baseline in 8 of 11 long episodes, with the 5–10 Hz peak wandering 5.3–9.9 Hz rather than
   locking at 7.4 Hz with Q≈36. **A dedicated comma-commanded route is required.**
5. 🛑 **Do NOT move `0xD28DC`, `0xD2888`, or `tp+0x73ba` (`0xC63BA` = 512) yet.** All three sit on the
   **base assist** path, so they change manual feel, not just the LKAS lane, and all need GATE 2.
   `tp+0x73ba` is the cascaded EMA alpha (0.5 at 1 kHz ⇒ corner ≈120 Hz for the pair, i.e. **wide open at
   21 Hz**) and is the *upstream* candidate — attenuate there and the index stops carrying 21 Hz at all.
   Gate all three on V59's depth answer.
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
