# HANDOFF 2026-08-09 (later) — V87 flew, the probe fired, and V88 restores Lever B

**Session shape:** orchestrator working directly (no subagents spawned this session).
**Deliverables:** route `71` extracted and scored · V87's blocking unknown CLOSED · the fork given a
first answer and an honest instrument limit · two of this session's own readings retracted by their
controls · one standing memory corrected from FALSIFIED-vs-untested · **V88 built, verified, unflashed.**

---

## 1. What the operator asked, and what came back

> *"I provided some rlogs from driving on V87. I observed grind #1, micro-ratcheting, and ratcheting.
> Work towards a V88, let's keep using our live telemetry to nail down the root cause."*

Route `71` = `75604b0a432fdc89_00000071--ac50da2a6a`, 4 segments, cache `_cache_r71/`.
**V87 flew fault-free** — 23,765 frames / 239.6 s, 52.4 % engaged, 0 sentinels, and no EPS event in
1,262 `onroadEvents` (the events are all `pedalPressed` / `steerOverride` / gear).

🛑 **The three symptoms are the PREDICTED result.** V87 is byte-stock at **all four** measured
grind-#1 addresses, read from its own image by `build_v88_tva.py` as a build gate:

```
0x3AB76 = aa    Lever A r26 `sar 0xa`   STOCK
0x3AC20 = aa    Lever A r24 `sar 0xa`   STOCK
0x3AA96 = c5    Lever B gate byte       STOCK
0xC6446 = 512   Lever B arm             STOCK
```

⚠ Unlike V81's, this absence was **not silent** — V87's own handoff says the V38 rebase dropped
Lever B. It was a known cost. V88 pays it back.

---

## 2. The probe fired — and this is the biggest instrument gain since the cave

V87's edit #6 repointed the 427 (`0x1AB`) transmit packer's source load, so `MOTOR_TORQUE` now carries
`clamp(|gp-0x6b98| * 5 >> 3, 0, 0x3FF)`. Both predecessor routes were re-tapped this session as
controls rather than quoting the record:

| route | build | non-zero | distinct | range | p95 | railed |
|---|---|---|---|---|---|---|
| `6f` | V86 | 56.45 % | 297 | [0, 345] | 137 | 0.000 % |
| `70` | V86B | 66.98 % | 240 | [0, 380] | 117 | 0.000 % |
| **`71`** | **V87** | **99.02 %** | **946** | **[0, 1023]** | **902** | **3.232 %** |

COUNTER increments 99.97 %, CHECKSUM spans 16/16, `CONFIG_VALID` duty 1.0000 on all three ⇒ the frame
is live and gateway-passed in every case; only the *payload* changed.

⊕ Note: `STATE.md` recorded 22.4 % / 20.2 % non-zero and 255 / 51 distinct for the V86/V86B 427 stream.
The numbers above are this session's own direct re-measurement over all four segments of each route
and should be used instead; the discrepancy was not chased.

### 2.1 🛑 THE BLOCKING UNKNOWN IS CLOSED

`STATE.md` §7 named `|gp-0x6b98|`'s real amplitude the thing that blocked every filter design, warned
the answer *"swings 5×"* across the plausible range, and recorded the working assumption as **~120
counts p-p**.

```
|gp-0x6b98|, counts (= wire × 8/5)          n       p50     p90      p99     railed≥1637
  ALL                                     11,883   137.6  1052.8   1636.8      3.23 %
  engaged                                  6,222   208.0   966.2   1636.8      2.35 %
  manual                                   5,661    14.4  1156.8   1636.8      4.20 %
  parked  v<0.2                            3,337     9.6    20.8   1636.8      3.75 %
  creep   0.2–2 m/s                        2,114   316.8  1498.7   1636.8      6.10 %
  2–6 m/s                                  6,432   217.6  1030.2   1636.8      2.02 %

band-limited, engaged / manual (rms counts)
  0.5–3 Hz   141.94 / 135.10      6–9 Hz    28.99 /  9.28      15–22 Hz  51.75 / 8.65
  3–6 Hz      28.88 /  18.96      9–15 Hz   29.18 /  9.10
```

⇒ **the 6–9 Hz ripple engaged is rms 29.0 counts, p-p 162 counts.** The assumption was low by
**1.35×**, not by 5×. Any future filter's phase budget can now be sized on a measurement.

🛑 **The probe's ceiling is the PROBE's**, not the command's: 1637 counts is where Honda's ×5/8 packer
hits 10 bits. What the command does above that is still unmeasured.

---

## 3. THE FORK — and the instrument limit that keeps it from closing

The question V87 existed to answer: is the ~7.8 Hz ratcheting **(A)** a passive mode being driven, or
**(B)** a closed-loop pole, i.e. is the delivered command itself oscillating at the line?

**Controls were run first**, at each window length (`feedback-run-the-control-before-the-measurement`).
White noise through the prominence estimator at nw = 256, fs = 49.81 Hz reads **p95 = 10.5**; a
synthetic 7.79 Hz line at line/noise 0.25 is detected in 82.5 % of draws, at 0.50 in 100 %.

**Rectification-transparent, unclipped, engaged windows** (screen: `min(0–3 Hz lowpass of |cmd|) >
3 × rms(6–9 Hz ripple)`, so the signal cannot change sign inside the window):

| signal | prominence, 6–9 Hz | above the p95 floor |
|---|---|---|
| column torque `0x18F` | **12.86 [5.73, 16.68]** | **50.0 %** |
| **delivered command `\|gp-0x6b98\|`** | **4.03 [3.54, 6.22]** | **7.1 %** — i.e. chance |
| openpilot's command `0x0E4` | 2.96 [2.36, 4.01] | 7.1 % |

⇒ **the ratcheting is not a tone the EPS is commanding.**

**But the link is real and frequency-selective:**

- pooled coherence `|gp-0x6b98|` ↔ column torque = **0.439 at 7.79 Hz**, against a **shuffled-pairs
  control of 0.178** (window *i*'s command against window *j*'s column, 60 permutations) and a
  background of 0.03–0.16 with a `1/n = 0.071` null;
- per-window **corr(column line prominence, command line prominence) = +0.62**, with the command's
  prominence rising to **12.67** in the top quartile of ratchet episodes and 4.93 in the bottom;
- the `|column/command|` ratio peaks at 7–8 Hz, but only **1.37–1.57× above its shuffled control** —
  most of the apparent "6× resonant peak" is the two signals' own spectra, and that part of the claim
  is **not** made.

⇒ **A lightly-damped mode driven by BROADBAND command content, not by a commanded oscillation.**
The lever class this implies is *"less broadband HF in the delivered command"* — **not a notch.**

### 3.1 🛑 THE INSTRUMENT LIMIT, stated rather than smoothed over

Rectification was transparent in **0 of 42** windows at 10.28 s and **14 of 37** at 5.14 s. `abs()` is
transparent only while the signal holds one sign, and at creep the command crosses zero constantly; a
7.79 Hz oscillation about zero folds to **15.58 Hz**. The 12–18 Hz image was also at the floor
(6.73 [5.18, 7.75]), which helps, but the null above rests on a screened subset of 14 windows.
**V88 fixes exactly this** (§5).

⚠ **Nyquist.** 427 runs at **49.81 Hz** ⇒ nothing above ~15 Hz is claimable from it; a 28 Hz object
aliases to 21.8 Hz. On the 100 Hz channels, engaged `tq` band rms is 337 (6–9 Hz), 254 (15–22),
**41 (24–32)**, 18 (32–40) — so the probe's 15–22 Hz shelf is *mostly* real, but not separably so.

### 3.2 ★ What engagement actually does to the delivered command — SPEED-MATCHED

`STATE.md` instrument defect #4 warns that an ENG/MAN column is usually MOVING-vs-PARKED. On this
route **59 % of manual frames are parked** and **0 % of engaged frames are**, so the raw ratio is
worthless. Matched to 2–4 m/s, per-window (nw = 256, unclipped), block-bootstrapped:

| band | engaged rms | manual rms | ratio |
|---|---|---|---|
| 0.5–3 Hz | 64.41 [40.43, 74.57] | 153.19 [29.02, 195.03] | **0.42×** |
| 3–6 Hz | 21.68 [19.72, 22.43] | 29.70 [8.59, 52.49] | 0.73× |
| 6–9 Hz | 24.17 [21.00, 37.74] | 13.98 [5.75, 27.31] | 1.73× |
| 9–12 Hz | 22.11 [15.12, 26.00] | 12.58 [5.82, 21.09] | 1.76× |
| 12–15 Hz | 16.29 [12.92, 23.25] | 9.08 [5.83, 16.21] | 1.79× |
| **15–22 Hz** | **47.57 [40.65, 59.91]** | **14.13 [7.12, 20.85]** | **3.37×  ← CIs DISJOINT** |

⇒ **engagement REMOVES low-frequency command motion and ADDS high-frequency motion, most of all in
grind #1's own band.** Only the 15–22 Hz row has disjoint CIs — [EVIDENCE]. The 6–15 Hz rows overlap
and are [BELIEF]. n = 6 manual windows; this wants repeating on a route with a real manual arm.

---

## 4. 🛑 TWO OF THIS SESSION'S OWN READINGS WERE RETRACTED BY THEIR CONTROLS

**1. The "differentiator" is an artefact.** A transfer `openpilot command → delivered command` rising
9× with frequency (|H| 0.064 → 0.580 from 1–3 Hz to 20–24 Hz) looked exactly like the r24/r26
derivative lane at its creep maximum. Coherence was **0.035–0.077** against a `1/n_avg = 0.043` null.
At zero coherence the estimator returns `sqrt(Pyy/Pxx)/sqrt(n_avg)`, and that formula reproduces the
measurement in **all seven bands**:

```
band      |H| measured   null prediction   ratio
1–3           0.0643            0.0645     1.00
3–6           0.0792            0.0867     0.91
6–9           0.2590            0.2557     1.01
9–12          0.2536            0.2433     1.04
12–15         0.2790            0.3122     0.89
15–20         0.3481            0.3442     1.01
20–24         0.5803            0.5393     1.08
```

**WITHDRAWN.** It would have been a very persuasive mechanism story for V88.

**2. The phase-randomised surrogate is a weak control here.** Phase randomisation **preserves
`|X(f)|`**, so for a single-window periodogram it preserves a line's power; only Hann leakage makes the
two differ. "real ≈ surrogate" is close to tautological and must not be read as "no line". The
load-bearing controls are the **white-noise floor at the same `nw`** and the **paired column-torque
comparison on the same windows**. Both survive; the surrogate is withdrawn from the argument.

⊕ **The in-route split-half null on 6–9 Hz power is [0.18, 5.51]** (14 clean windows in 10 blocks).
Any V88/V87 ratio inside that is a null, whatever it is. This route is too short to score a band.

---

## 5. V88 — built, verified, unflashed

```
image  96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8   1,048,576 B
.rwd   4955d80a763a364b30d82ba315e7f1a97873068399de1842f64864478130a2de     986,042 B
39990-TVA,A160-V88-V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256-0x13000-0x100000.rwd
base   _v87_..._plain_image.bin  27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034
```

| # | addr | w | from | to | what |
|---|---|---|---|---|---|
| 1 | `0x3AA96` | 1 | `c5` | `fb` | **LEVER B gate** — `ld.bu -0x683c[gp],r15` → `-0x6806[gp],r15` ("LKAS applying") |
| 2 | `0xC6446` | 2 | 512 | **5244** | **LEVER B arm** — r24's gain = flat 5244 while LKAS applies = **2.000×** the LERP |
| 3 | `0xC4B38` | 2 | `9094` | `6894` | cave probe source `gp-0x6b70` → **`gp-0x6b98`** ⇒ **b7 = SIGN of the delivered command, 100 Hz** |
| 4 | `0xC4B46` | 1 | `a6` | `a8` | cave `sar 0x6` → `sar 0x8`, magnitude rung **64 → 256 counts** |

**5 bytes actually change** (#3 writes two but only one differs: `-0x6b70` = `0x9490` and `-0x6b98` =
`0x9468` share the high byte), plus 8 CRC bytes in two blocks.

**Verification:** 6 runs / 15 bytes vs the flown V87, **zero unattributed**; restoring the attributed
set reproduces V87 bit-for-bit; CRC 50/50 on the built image, the readback and the shipped `.rwd`
re-read from disk; the whole build re-ran **bit-identically** after a docstring correction.

🛑 **No cave is created, moved, grown or shrunk.** Both instrument bytes are in-place edits inside the
62-byte payload that has flown three times (V86, V86B, V87). The only store is still
`st.b r6,-0x1514[gp]`, asserted unique.

★ **The new load is not hand-encoded.** `24376894` is **byte-identical to the 427 packer's own
`ld.h -0x6b98[gp],r6` at `0x55DF0`** on this base — an instruction already proven on-car reading
exactly that cell. Both halfwords asserted from the image.

★ **The `TVCA4` hazard, checked and cleared.** `v66_v67_explained` derives the arm from **mode-10**
records; this car reads **24/26**, and that mismatch has already produced three byte-stock builds
(`reference-accord-car-is-tvca4-mode-24-26`, RULE 7). Re-derived from the image's own pointer arrays:

```
mode 24: LERP = 2622   5244/LERP = 2.0000x   (the car)
mode 26: LERP = 2622   5244/LERP = 2.0000x   (the car)
mode 10: LERP = 2622   5244/LERP = 2.0000x   (the helper's hard-coded table)
mode 24 == mode 26 byte-identical in all 4 gain_B arrays
```

⚠ a SCALAR arm against a CURVE: **1.77×–2.55×** across the LKAS-on regime.

**GATE 1 — RAM ownership: nothing new is written.** #1 and #3 change a load's *displacement*, #4 an
immediate, #2 a calibration halfword.
**GATE 2 — closed-loop stability:** #3/#4 are read-only telemetry. #1+#2 raise r24's *derivative*
feedback 2.000× while LKAS applies — phase LEAD, i.e. damping — and have flown twice at exactly this
dose on a build carrying exactly this 4.000× forward LKAS gain. Linearity re-derived, not quoted: the
lane's ±8192 clamp needs `|dtorque| ≥ 1601` counts against V65's measured 123–839 over 120,049 frames.

### 5.1 🛑🛑 RECORD CORRECTION — `0xC6444` is FALSIFIED, not untested

`accord-rate-lane-builds-were-never-single-variable` names `0xC6444` as the decoupler for Lever B's
known residual (the repoint also puts r26's arm on the gate, cutting it ~6×) and calls raising it
*"UNTESTED: a candidate, NOT a recommendation"*. **A cross-image matrix built for this session's
close-out shows `0xC6444` = 3072 has FLOWN — it is V71c**, which is exactly
`V67 + 0xC6444 512→3072 + 0x454FE` and nothing else. `LEDGER-V38-TO-V84.md:236`:

- grind #1 `e_18-22` = **223** vs V67/V68's **109** — below stock, but **excluded HIGHER than V67
  (P = 0.0215)**;
- **grind #2 came back**: 7 bursts at 44.31 Hz, p99 = **12.2×** the max of any non-bursting build,
  against V67/V68's **zero** at creep;
- **the ratchet hit 8,521 counts p-p — the corpus RECORD.**

⇒ **the 6× r26 cut is LOAD-BEARING in Lever B, not a defect in it.** `0xC6444` stays at Honda's 512
here and is **not** a V89 candidate. FALSIFIED ≠ untested.

### 5.2 🛑 HONEST LABEL — this is not "V88 fixes the grinding"

Lever B has flown **seven times** (V67, V68, V71c, V84, V85, V86, V86B). The record calls it
*"CONFIRMED-FIX, AT ITS CEILING … tops out at V67's level, which the operator still calls grinding"*,
and on V84 it read 1.10× V81 after negative-control correction, i.e. it only undid a regression.
**V88 does not beat that ceiling and does not claim to.** What it does:

1. **puts the car back to the best state the kit has measured**, which V87's rebase deliberately gave up;
2. **makes Lever B's mechanism observable for the first time.** Every prior Lever B flight was scored
   on the column torque — an OUTPUT. V87's probe exposes the delivered command, so V88-vs-V87 is a
   single-variable A/B on the thing Lever B actually changes.

**It is NOT a ratcheting lever.** Nothing in it targets the ~7.8 Hz mode, whose firmware search the
record marks CLOSED by a shape argument. **If the ratcheting is unchanged, that is the prediction.**

---

## 6. PRE-REGISTRATION for the V88 flight — write the result in the pass that scores it

**Identity, parameter-free, control already measured.** On V88 the cave and the 427 packer read the
same cell, so per frame `b6 == (MOTOR_TORQUE ≥ 160)` (= `(256·5)>>3`) must hold. On route `71` (V87,
cave on `gp-0x6b70`) that predicate agrees **0.402** of the time.
⇒ **≈1.00 means V88 flew · ≈0.40 means V87 did.**

**H1 — THE MECHANISM TEST, and the one that matters.** Lever B doubles the r24 derivative arm while
LKAS applies, so it must change the **delivered command's** HF content. Measured on V87 at 2–4 m/s,
speed-matched: 15–22 Hz engaged rms **47.6 [40.7, 59.9]**, 6–9 Hz **24.2 [21.0, 37.7]**.
- **CONFIRMED** if V88's engaged 15–22 Hz band rms of `|gp-0x6b98|` falls with a CI excluding 1.00.
- 🛑 **REFUTED** if it is unchanged or rises — and that refutes the *"broadband HF in the delivered
  command drives a lightly-damped plant mode"* reading, which is worth more than another attenuation
  point. Say so plainly if it happens.
- ⚠ **AMBIGUOUS, not a null**, if the route has < 5 engaged minutes or no manual arm above 0.5 m/s.

**H2 — the fork, now closable.** With `b7` giving sign at 100 Hz, reconstruct the **signed** delivered
command and re-run §3's paired test with **no transparency screen**. The V87 answer (line in the
column, not in the command) either survives on the full window set or it does not.

**H3 — symptoms.** 🛑 **The operator scores grinding, micro-ratcheting and ratcheting, in his words.**
Bands are the instrument, never the verdict. An absence of complaint is not a report of improvement.

**Exposure requirements, from `STATE.md` instrument defect #6, and route `71` failed all three:**
- **≥ 5 engaged minutes** (route `71` had 2.1) for a ~1.7× band ratio; ~40 min for 1.2×.
- **a real MANUAL arm above 0.5 m/s** — 59 % of `71`'s manual frames were parked, which is what makes
  the raw engaged/manual ratio meaningless.
- **highway** if any 26–31 Hz or grind-#1-at-speed claim is wanted: `71` had **0.0 s engaged ≥ 50 km/h**,
  the fourth consecutive route with none.

---

## 7. Where this leaves the root cause

```
openpilot 0x0E4  ──►  4.000× forward LKAS gain (FROZEN on every build; do NOT lower)
                          │
                          ▼
        aggregator + the r24/r26 DERIVATIVE lane  ◄── LEVER B doubles r24 here, engaged only
                          │                            (r24 = 4-tick finite difference of BAR torque)
                          ▼
        governor ─► comp-add ─► shaper ─► gp-0x6b98   ◄── V87's 427 probe reads |this|, 50 Hz
                          │                                V88 adds its SIGN at 100 Hz
                          ▼
                    FOC ─► PWM ─► motor ─► rack ─► column
                                    └── the ~7.8 Hz mode lives HERE, Q 14–29,
                                        and NO channel on this bus observes it
```

**What is now EVIDENCE:** the delivered command carries **broadband** 6–9 Hz content (rms 29 counts
engaged) and no detectable tone there; the column carries the tone; the two are coherent at 0.44 at
7.79 Hz against a 0.18 shuffled control. **What is BELIEF:** that reducing the command's broadband HF
reduces the symptom proportionally. **H1 tests exactly that belief**, for the first time, on the
delivered signal rather than on the column.

⊕ `gp-0x6b70` (the Coulomb friction compensator), measured on route `71` before V88 repoints away from
it: non-zero **99.80 %**, `|v| ≥ 64` in **93.84 %**, negative **67.19 %**, and the aggregator's
optional-term gate **open 100 %** of 23,766 frames.

---

## 8. Files

| path | what |
|---|---|
| `rlog-tools/extract_r71.py` | route `71` via the shared extractor **verbatim**, plus a pass-through tap that records all three `0x1AB` bytes during the extractor's own single pass |
| `rlog-tools/v87_probe_6b98.py` | stages 0–6: controls first, amplitude census, rectification transparency, the fork, coherence, split-half null, headroom |
| `rlog-tools/v87_probe_fork.py` | stages 7–10: the fork on transparent windows at three window lengths, aliasing, the (retracted) transfer, episode-conditional |
| `rlog-tools/v87_probe_ctrl.py` | stages 11–13: speed-matched engaged/manual, the coherence null **computed**, shuffled-pairs control — and both retractions |
| `analysis-2020accord/build_v88_tva.py` | the build. Self-checking; `ACCORD_V88_WRITE=rwd` to cut |
| `_cache_r71/` | `r71.npz` (+ `ab_*` probe columns), per-segment `r71s*.npz`, `*_1ab.json`, three result JSONs |
