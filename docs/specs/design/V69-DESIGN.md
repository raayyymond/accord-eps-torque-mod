# V69 — DESIGN SPEC

🛑🛑 **SUPERSEDED 2026-08-04. THIS IS A HISTORICAL RECORD OF HOW V69 WAS CHOSEN — NOT CURRENT STATE.**
**V69 FLEW** (route `4f`) and so did V70 (route `50`). The analysis below is kept because it is the
honest record of the reasoning; **three of its load-bearing premises are now refuted.** Read
`docs/STATE.md` and `docs/handoffs/2026-08/HANDOFF-2026-08-04-both-confirmed-fixes-were-off-the-car.md` first.

1. 🛑 **THE `A_rk` FIGURE IS NOT A BURST MEASUREMENT.** `A_rk = 1927` traces to
   `studies/sessions/v70/v70_parametric_gain_collapse.py:132` — the top decile of the **whole-drive** `|rate|` distribution
   (hard manoeuvres), **not** the rate index during a grind. Measured directly over **424 grind-#1
   burst windows**: the oscillation's own 18–22 Hz rate swing is **p50 140 counts / p90 327**. The
   peak-velocity framing needs `A_rk ≳ 1400`, reached by **9.20% of windows on scale A and 0.00% on
   scale B** ⇒ **dead on scale B; alive on scale A only at the ~90th-percentile worst instant.**
2. 🛑 **THE rateKey / PEAK-VELOCITY DOSE FRAMING IS REFUTED — with the scope in (1) kept, not
   widened.** Grind #1 lives **97.8% (scale A) / 100% (scale B)** inside the flat `[0,400]` rate
   segment, over 19,378 burst samples on 11 routes. V70 delivered **exactly 2.000×** at grind #1's
   real operating point and did **not** reproduce V62's result.
   ⚠ **Say it as `STATE.md` says it: dead on scale B, alive on scale A only at the ~90th-percentile
   worst instant.** ⚠ **And record the adjudication, not just the verdict:** two analysts disagreed
   and the orchestrator ruled. The *outcome* data is sound (V70 excluded from V62's class at
   **P < 5 × 10⁻⁵**), but the rateKey axis is the **bus angle rate converted by an assumed scale**
   while `gp-0x6ac0` is the **motor/resolver rate** — **a proxy that cannot settle it either way.**
   The r26 explanation in (3) is preferred because it accounts for the same outcomes **with no
   rateKey claim at all**.
   ⚠ **The two `rateKey` mentions in the BODY of this file** (§0.1's fold row and §4's *"one accepted
   discontinuity"*) are about the **≥ 13001-count fold** — different arithmetic, still correct, and
   **not** the retracted framing. Left as written.
3. 🛑🛑 **EVERY MULTIPLIER IN THIS FILE IS r24-ONLY, COMPUTED AT `a = 0`.** r24 and r26 have
   **separate gain selectors** — r24 reads `gain_B` (the mode-10 surface this spec edits), r26 reads
   `gain_A` (fixed records at `0xC6A68/7C/90/A4`, **not** mode-indexed). **V69's and V70's surface
   edits could never reach r26.** And r26 is now **measured LIVE on-car** (V70's probe: `gp-0x6adc`
   strictly negative on 1,644/18,010 frames; a pinned-zero cell cannot clear a `>= 0` test).
   ⇒ **The dose axis this spec reasons on is the wrong lane.** A pure r24 series with r26 held at ×1
   — **stock → V70 → V69, ×1 → ×2 → ×4 — reads 879 / 729 / 746, all CIs overlapping**: r24 is
   near-inert for grind #1. Every build that *fixed* grind #1 changed **r26**.

⚠ **Also retired here:** the "non-monotone dose–response with a minimum near 2×" (it priced every
build on r24 alone), and *"Q is not measurable at NFFT 256"* (the ratchet's **Q ≈ 40 at f0 = 7.793 Hz**
is now measured, with a window-invariance test).

**Status: FLOWN.** `analysis-2020accord/builds/v50_v79/build_v69_tva.py`.

---

## 0. 🛑 REVISION 2026-08-04 — TWO OPERATOR INSTRUCTIONS, APPLIED IN PLACE

V69 was re-cut on the operator's explicit instruction. **The rest of this document still describes
the 2× design; §0 supersedes it wherever they disagree**, and each affected section is annotated.

### 0.1 The surface dose is 4×, not 2×

`0xD2A7E`/`0xD2A80` 3072 → **12288**, `0xD2ABA`/`0xD2ABC` 2561 → **10244**. The *shape* is unchanged
— exactly **4.000× to 10 km/h → 3.658 @15 → 3.307 @20 → 2.578 @30 → 1.808 @40 → EXACTLY 1.000× at
and above 50 km/h**, on both open axis scales, no hump anywhere, highway still structurally stock.
Only the dose moved. Three costs, each strictly worse than at 2×:

🛑 **IN-PLACE MARKER — see banner (3): every multiplier in this table is r24-only at `a = 0`, and
this edit could not reach r26 at all.** The **arithmetic** is correct and was confirmed on-car (the
dose was fully delivered); what is wrong is the premise that this axis is the one that moves grind #1.

| | 2× (as specced) | **4× (as built)** |
|---|---|---|
| max multiplier | 2.000× | **4.000×** |
| peak gain | 6144 | **12288** |
| r24 lane rails at \|dtorque\| | 1366 | **683** |
| margin vs repo max 839 | 1.63× | **0.81×** ⇒ *it can rail* |
| margin vs V68-route max 511 | 2.67× | **1.34×** |
| fold step at rateKey ≥ 13001, 0 km/h | 2.00 → 4.00× | 2.00 → **8.00×** |

1. 🛑 **The flown bracket is BROKEN.** At 2.000× §5.2's magnitude leg was an *interpolation* between
   stock (1.00×, shipped) and V62/V65 (2.00×, flown flight-clean). **4.000× is an extrapolation to
   twice the largest dose this kit has ever driven.** What still holds: phase is untouched (no
   filter, no pole, no delay, no `sar` moved), the lane is linear, V65 measured the aggregator never
   railing over 120,049 frames, and grind #1's dose–response was monotone through 2.00×.
   ⚠ **RETIRED 2026-08-04 — that last clause priced every build on r24 alone at `a = 0`.** With r26
   measured live, V62/V65's "2×" (**both** lanes, via `sar`) and V69's "4×" (gain_B only) were never
   the same quantity, so there was no single monotone curve to be on. **The broken-bracket warning
   itself was sound and is NOT retracted.**
2. 🛑 **Saturation crosses the record.** At 2× the lane could not rail in recorded driving; at 4× it
   can. During the largest low-speed transients the damping lane goes from linear to a hard rail —
   a describing-function regime the 2× design deliberately stayed out of. ⚠ And every `|dtorque|`
   figure here is a **LOWER BOUND** (CAN's 50 Hz Nyquist hides content the finite difference is
   still rising through), so the true margin is *worse* than 0.81×, not better.
   ★ **bit6 of the new probe measures exactly this on-car** (§0.2) — the cost is instrumented, not
   just disclosed.
   🛑 **OUTCOME: bit6 returned an UNINTERPRETABLE ZERO on BOTH drives** — **0/47,990** on V69's `4f`
   (at this ×4 dose, where the rung needed only **49 counts**) and **0/18,010** on V70's `50` (where a
   replay on the route's own data predicts **311** hits and stock predicts **52**). ⇒ **[BELIEF] the
   better-supported reading is an under-ranged or MIS-RECONSTRUCTED rung** — `dtorque` is a 4-sample
   1 kHz difference rebuilt from a 100 Hz bus copy of a different, filtered torque cell — **not arm
   selection, which cannot produce a dose-dependent miss.** ⇒ **the cost was instrumented but never
   measured.** The durable lesson is **GATE 4** in `docs/BUILD-LINEAGE.md`: **read the GAIN IN FORCE,
   not a lane output.**
3. ⚠ **Manual creep is 4.000×** on the pessimistic axis scale. Manual highway stays byte-identical
   to stock.

⇒ **This is the operator's call, made with the numbers above in front of him.** The build asserts
the dose it was told to deliver and prints the broken-bracket warning on every run rather than
silently passing a gate that no longer applies.

### 0.2 The probe is re-aimed at the RATCHET

Bits 6/5/4 no longer read Honda's oscillation detector. **Rationale: that instrument is exhausted** —
`gp-0x67df` has never been observed non-zero in this kit (0/53,991 on V68, 0/186,321 on V67,
straight through the captured 28 Hz burst), and with no positive control the null cannot separate
"no oscillation" from "detector disabled / input dead". **And the ratchet is the one symptom this
channel can resolve**: at ~7.4–7.6 Hz a 100 Hz probe gets ~13.5 samples/cycle, so each bit's own
time series carries the line. At 21 Hz and 43 Hz it never could.

The ratchet's signature — **symmetric waveform, amplitude-saturated, Q ≈ 36, creep, engaged,
hands-off, NOT the V42 state-4 governor** — is the describing-function signature of a **hard
nonlinearity inside the loop**. V65 already killed the obvious one (the aggregator SUM never rails).
What its null never covered is **each lane's own nonlinearity upstream of the sum**: eight ZERO-type
range gates (out-of-window contributes **0, not clipped** — a crossing is a *step*) and two
saturating lane clips. None has ever been measured.

| bit | cell | test | that lane's own hard nonlinearity | why it is a top candidate |
|---|---|---|---|---|
| 7 | — | constant 1 | — | LIVENESS; field == 0 ⇒ VOID |
| **6** | `gp-0x6ada` | ≥ +4096 | ±0x2000 **saturating clip** | r24's **lane output**, the damping/torque-rate lane the record points at and the lane V69 scales. Honda mirrors it to RAM at `0x3AD5A` every 1 kHz tick. 🛑 **0 readers / 1 writer image-wide** ⇒ the strongest GATE-1 statement available: nothing consumes it, so the probe cannot perturb anything even in principle. +4096 = half its rail ⇒ duty is a **rail-proximity meter**. |
| **5** | `gp-0x6b62` | ≥ +4096 | ±0x2000 **ZERO gate** | **The operator's own hypothesis, never probed in 69 builds.** Return-to-centre: `FUN_00036388`, a slow ±1/tick accumulator **with hysteresis**. |
| **4** | `gp-0x6ad4` | ≥ +4096 | 🛑 ~~±0x2800 **ZERO gate**~~ — **WRONG, CORRECTED 2026-08-04 AFTER THE FLIGHT** | The **unfiltered** residual/resonance lane (`FUN_0003a382`: two passthroughs + a **raw derivative** on the physical torque sensor, straight into the aggregator). Its gain is LERP-indexed by `gp-0x671a` — Honda's oscillation counter — so this lane **closes a loop from the detector back into assist**. Live hands-off, which the boost lane is not. 🛑🛑 **THIS RUNG WAS STRUCTURALLY VACUOUS AND COULD NEVER HAVE FIRED, ON ANY BUILD, ON ANY DRIVE.** `±0x2800` is the **ERR *input* clamp**, not the lane's output range. The **output** is clamped to ±CEILING = **MIN of three LERPs**; the binding one is `0xC67C2`/`0xC67C8`, indexed on **voted vehicle speed**, **max 1024**, and it **starts at ZERO** — at the four ratchet episodes' speeds (4.9/6.8/7.8/8.0 km/h) CEILING was **164–341**. A ≥ 4096 test is **12–25× above the lane's entire reachable range**. ★ It also explains why **V56's mute of this lane changed nothing.** ⇒ **the lesson: size a rung against the producing lane's own reachable output, never against a downstream gate width.** |
| 3 | — | constant **0** | — | V69 BUILD CLASS. V68 emits bit3 = 1 in **100.000%** of 53,991 frames ⇒ V68 excluded absolutely. |

**bit6 is freed from the LKAS gate** to buy the third rung. Justified, not assumed: `gp-0x6806`
agreed with `carControl.latActive` in **150,302/150,327 = 99.983%** of frames, `0x18F` b4 bit3 and
`0xE4` byte2 bit7 agree 99.94–100%, and **V69 reverts the gate** so `gp-0x6806` no longer steers
anything on this build — bit6 was a pure covariate and three external channels already carry it.

**Encoding, per rung (14 B):** `ld.h -disp[gp],r6` · `sar 0xc,r6` · `cmp 0x1,r6` · `blt +6` ·
`movea BIT,r7,r7`. All three lanes are **signed** halfwords (`ld.h`/`st.h` at every site).
`sar` is arithmetic and `blt` is signed, so a negative lane value fails the test — asserted by an
**exhaustive wire model over all 65,536 halfword patterns**, plus the explicit unsigned counter-case.

🛑🛑 **THE ONE-BIT TRAP, AND IT IS NOT HYPOTHETICAL HERE.** `ld.h` is opcode **0x39**; `st.h` is
**0x3B**. `gp-0x6ada`'s *only* real instance (`0x3AD5A`) **is** the `st.h` form and carries **the
same displacement halfword** we emit. One bit turns each read into a **write into a 1 kHz aggregator
lane**. Asserted by value in the builder *and* independently in `verify/verify_v69_image.py`.

**Encoder provenance:** `ld.h -0x6ad4[gp],r6` is **BYTE-IDENTICAL** to the aggregator's own read at
`0x3ACA8`; `gp-0x6b62` has **eight** real `ld.h -0x6b62[gp],rN` differing from ours **only in the
reg2 field**; `gp-0x6ada` has no real `ld.h`, but its hw2 is byte-identical to the real `st.h`
@`0x3AD5A` and every hw1 field is pinned by the two byte-identical `ld.h …,r6` donors. `sar 0xc,r6`
(`ac32` @`0x2C0BA`), `cmp 0x1,r6` (`6132` @`0x14D46`) and `blt +6` (`b605` @`0x1C006`) are all
byte-identical real instances.

**Cave: 66 of the proven 68 bytes, 2 spare. THE EXTENT IS NOT GROWN** (prologue 4 + 3×14 + epilogue
20). A fourth rung needs 14 more and does not fit — that arithmetic, not preference, is why there
are three. Caves are this kit's only bricking class (V24/V27/V48B).

**Decoder: `rlog-tools/probe/decode_v69_ratchet.py`**, linked mechanically — the build **fails** if its
`CAVE_HEX` is not byte-for-byte the built cave, if it omits any probed cell, or if it still
describes the retired grind-detector rungs as live.

🛑 **THREE RESIDUALS ON THIS PROBE, STATED.**
- **One-sided.** Each rung tests the positive side only (two-sided costs 8 B/rung and does not fit).
  For a symmetric limit cycle the positive half-cycles still put 7.4 Hz in the bit's spectrum — but
  **a null bounds only that lane's POSITIVE excursions.** Never quote it as two-sided.
- **No positive control on bit5/bit4.** Only bit6 is expected to fire on any real drive. If bit6
  also reads 0.000%, check bit7 and the `.rwd` name **before** interpreting bits 5/4 — the V64 lesson.
- **V69-vs-V66/V67 is not structural.** Those builds also emit bit3 = 0 and measured bits 5:4 = 0
  over 186,321 frames, so their payloads `{0x87, 0xC7}` are a **subset** of V69's. Discrimination
  rests on bit5/bit4 ever firing plus the filename. Two builds back; accepted and stated.

**What was considered and NOT taken** (so it is not re-proposed): `gp-0x6bbe` boost, ±0x800 — the
narrowest gate on a live lane, but indexed on **driver torque**, and the ratchet is hands-off ⇒ it
sits far from its gate exactly when the symptom occurs. `gp-0x6bd0` damping, ±0x800 — the record has
f5 = 0 at both operating points, so it likely reads 0; that is a **static** claim and probing it
would test a closed branch — **first cut if a rung ever frees up.** `gp-0x6b4c` LKAS lane — already
on CAN `0xE4`. `gp-0x4f62` dtorque (r24's input) — the "probe the input too" lesson; rung 4 if the
cave ever grows.

---

**Goal:** remove the engagement-conditional 24–30 Hz amplification at highway (the felt lane-change
vibration) **without losing grind #1's fix**, as a pure calibration + in-place-byte edit — no code cave.

Read with `docs/handoffs/2026-08/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md` (the measurement),
`docs/BUILD-LINEAGE.md` (what is already falsified) and `docs/STATE.md`.

---

## 1. 🛑 THE HONEST PREMISE, STATED FIRST

**The mechanism is SUGGESTIVE, NOT ESTABLISHED.** The evidence that the r24 rate lane causes the
28 Hz lane-change transient is a maneuver-conditioned dose ratio of **3.334 [1.201, 6.492]** at
26–30 Hz whose CI **does not clear its own split-half null of [0.33, 3.36]** — the Kd = 1 maneuver
arm holds only 39 windows / 17 blocks (~50 s). The operator was offered the drive that would settle
it (≈150–250 s more active LKAS-off highway maneuvering) and **declined it**; V69 is therefore built
on a suggestive mechanism by explicit decision. That is a reasonable call — the edit is cheap,
reversible, and self-testing — but it must not be written up later as though the mechanism had been
proven first.

**What IS established** and independent of the mechanism:
- The symptom is real and captured: `4e` seg 33 t = 51.3 s, ALC right lane change at 25.93 m/s,
  bar **1468 counts p-p**, 26–30 Hz envelope **614** (20× route median), lines at 28.12/28.51 Hz at
  prominence 100–107, **40–49 Hz reads 69 in the same window**. Not wheel order 2 (24.93 Hz) or 3
  (37.40), not engine order 1 (26.10) or 2 (52.20).
- "Only when engaged" is **REFUTED at 40–49 Hz** (maneuver/control 2.516 [1.561, 3.701] engaged vs
  2.558 [1.469, 3.747] manual) and the engagement-conditional part sits at **18–28 Hz**.
- V67/V68's arm delivers its **maximum** dose at highway (**2.4383×**, reproduced twice
  independently) because a flat scalar replaces a surface Honda rolls off with speed.

---

## 2. WHY THE DESIGN IS FORCED

`FUN_0003aa2c`'s r24 gain selection is a four-way priority ladder (addresses verified in the flown
image by hand-decoding the bytes, not only from Ghidra):

```
0x3ABFA  cmp r0,r6              ; MASK   gp-0x671d != 0   -> cal 0xC6442 = 1024
0x3AC04  cmp r0,lp              ; GATE   (V67/V68: gp-0x6806) -> cal 0xC6446 = 5244
0x3AC0E  cmp r0,r2              ; 3rd    gp-0x671a >= 5    -> cal 0xC6440 = 2048
0x3AC16  (join)                 ; else   the mode-10 speed x rate LERP
```

The gate branch is `cmp` 2B + `be` 2B + `ld.hu` 4B + `br` 2B = **10 bytes, fully packed between two
other arms — zero slack.** So:

1. **The gated arm is a FLAT constant.** One scalar cannot serve both endpoints: stock LERP is
   **2621** at grind #1 and **2172** at highway, so 1.00× at highway needs 2172, which is **0.83×**
   at grind #1 (below stock — V61 territory, and V61 made grind #1 *worse*); while 2.00× at grind #1
   needs 5244, which is **2.4383×** at highway. **Structurally unsolvable as a flat arm.**
2. **Speed shaping exists only on the DEFAULT branch** (`FUN_0003ad74`'s cross-interpolation, outer
   axis = voted speed `gp-0x6a5e`). The gate *discards* that value.
3. ⇒ **The engaged path can only see speed shaping if it falls through to the LERP**, i.e. the gate
   must be off. Composing "gated AND shaped" requires inserting instructions into a zero-slack
   branch — a **code cave on the 1 kHz path**, this kit's only bricking class (V24, V27, V48B all
   bricked the ECU), also subject to DTC 0x18's per-task overrun budget. **Rejected.**

⇒ **V69 reverts the gate and shapes the surface. The operator accepted the consequence** (§6).

---

## 3. THE EDIT

### 3.1 Byte table

🛑 **SUPERSEDED BY §0 — rows 3–6 are now ×4 and rows 7–8 are replaced by a full cave rewrite.**
The table below is kept because rows 1–2 are unchanged and because the ×2 values are what the rest
of this document's arithmetic is computed on. **As built:**

| # | address | before | **as built (×4)** | meaning | CRC block |
|---|---|---|---|---|---|
| 1 | `0x3AA96` | `fb` | `c5` | gate load reverts `ld.bu -0x6806[gp],r15` → `-0x683c` (stock's **dead** cell, 0 writers image-wide) | MAIN `[0x13000, 0xC4FFC)` |
| 2 | `0xC6446` | `7c 14` (5244) | `00 02` (512) | the now-unreachable arm returns to stock | CAL `[0xC6000, 0xC6FFC)` |
| 3 | `0xD2A7E` | `00 0c` (3072) | `00 30` (**12288**) | rec0 (**0 km/h**) Y[0] | `[0xD2000, 0xD2FFC)` |
| 4 | `0xD2A80` | `00 0c` (3072) | `00 30` (**12288**) | rec0 Y[1] | same |
| 5 | `0xD2ABA` | `01 0a` (2561) | `04 28` (**10244**) | rec1 (**10 km/h**) Y[0] | same |
| 6 | `0xD2ABC` | `01 0a` (2561) | `04 28` (**10244**) | rec1 Y[1] | same |
| 7 | `0xC4B34`–`0xC4B77` | V68's cave | **the ratchet probe** (§0.2) | 66 B of the proven 68 B extent, 2 spare | MAIN |

**7 edit sites / 70 changed bytes / 3 CRC blocks.** No cave *growth*, no new RAM cell.

~~Edits 3–6 are each an **exact doubling**~~ — each is an exact **×4** — of the low-rate end of the
two lowest-speed records.
Y lives at record+0x0A, X at +0x02, count at +0x00 — confirmed from the firmware's own accessor
arithmetic (`psVar11[i+5]` = Y[i]).

### 3.2 Which record is which — the trap that would have inverted this design

🛑 **`.claude/agent-memory/firmware-codepath-tracer/reference_accord_r24_gainb_table_structure_and_priority_gate.md`
assigns the four mode-10 records to the WRONG cross-axis speeds, rotated by one.** Under that
reading this edit would land on the **10 and 50 km/h** records and would *raise* the highway end —
the exact opposite of the goal. It is wrong. Verified three independent ways:

- **pointer arrays**: `0xCBF5C + 10×4 = 0xCBF84 → 0xD2A74`; `0xCC044 + 10×4 → 0xD2AB0`;
  `0xCC12C + 10×4 → 0xD2AEC`; `0xCC214 + 10×4 → 0xD2B28`. Slot *i* pairs with cross-axis `X[i]`.
- **cross axis** `0xC6010` = `[0, 640, 3200, 6400]` counts = `[0, 9.99, 49.95, 99.9]` km/h.
- **monotonicity**: Y[0] reads 3072 / 2561 / 2305 / 2151 in that order — a speed rolloff must be
  monotone, and the rotated reading makes it non-monotone.

⇒ **`0xD2A74` ↔ 0 km/h · `0xD2AB0` ↔ 10 km/h · `0xD2AEC` ↔ 50 km/h · `0xD2B28` ↔ 100 km/h.**
**Correct that memory before any subagent reads it again.**

### 3.3 Per-record inner axes differ

`rec0 X = [0, 400, **1400**, 3000]` but `rec1–3 X = [0, 400, **1500**, 3000]`. Applying one record's
axis to all four silently shifts every number — an error I made on my own first pass and corrected.

### 3.4 🛑 The neighbour trap — worse than a near-twin

The mode 10/11/12 records are interleaved at stride `0x14`, and the neighbours are not merely
similar:

| record | mode 10 (ours) | mode 11 | mode 12 |
|---|---|---|---|
| **0 km/h** Y | `[3072, 3072, 2322, 1536]` @`0xD2A74` | **IDENTICAL** @`0xD2A88` | **IDENTICAL** @`0xD2A9C` |
| **10 km/h** Y | `[2561, 2561, 2247, 1947]` @`0xD2AB0` | `[2560, 2560, 2246, 1946]` @`0xD2AC4` | same @`0xD2AD8` |

**Mode 11 and 12's 0 km/h records are BYTE-IDENTICAL to mode 10's**, and their 10 km/h records sit
one count below. So the byte pattern this edit targets occurs **three times within 40 bytes**.
🛑 **Address every cell by absolute address. Never search for a byte pattern.** A pattern-based
edit would silently rewrite another car variant's calibration, and `verify/diff_build_vs_stock.py` — being
span-based — would attribute it without complaint. **Assert the mode-11 and mode-12 records
byte-unchanged in both the builder and the verifier.**

---

## 4. WHAT IT DOES

### 4.1 Multiplier vs speed (low rate axis)

| km/h | 0 | 5 | 7.2 | 10 | 15 | 20 | 25 | 30 | 40 | **50** | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **V69 / stock** | 2.000 | 2.000 | 2.000 | **2.000** | 1.886 | 1.769 | 1.649 | 1.526 | 1.270 | **1.000** | **1.000** |

Flat 2× to 10 km/h, linear taper, **exactly 1.000× at and above 50 km/h — byte-identical to stock at
highway, in BOTH arms.** That is the fix.

★ **AND THE HIGHWAY 1.000× IS STRUCTURAL, NOT TUNED.** The lane-change point is 93.35 km/h = 5980
counts, which lies in the cross-axis `[3200, 6400]` segment — so the interpolation there reads
**only rec2 and rec3**. **Any edit confined to rec0 and rec1 is exactly 1.000× at every speed
≥ 50 km/h, at every rate, on every axis scale.** It cannot drift with a re-tune or a re-derived
scale; it is a property of which records the interpolation touches.

### 4.1b ★ SCALE-INVARIANCE — this design does not bet on an open question

🛑 The inner axis's counts-per-deg/s is **[OPEN]**: the repo runs 4.7121 (scale A), but the same
derivation chain has one wrong premise and the arithmetically-surviving alternative is 0.58901
(scale B). Every rate-axis figure in this kit is conditional on that.

**V69 doubles the whole flat `[0, 400]` segment rather than leaning on where a breakpoint falls**,
so its creep dose is **2.000× on BOTH scales**. Design A swings **2.00× (A) → 1.22× (B)** at grind
#1 — it is a bet on scale A.

⚠ **The price, stated honestly: the same property makes the manual-creep cost scale-dependent.**
grind #1 and manual creep share the same speed cells, so only the rate axis could separate them —
and on scale B they are both deep inside the flat segment and **nothing** separates them:

| | scale A (repo live) | scale B (chain-direct) |
|---|---|---|
| grind #1 region (2–5 mph × 16–128 deg/s) | min 1.75, median **2.00** | min 1.90, median **2.00** |
| creep grind #2 | **1.27×** | **2.00×** |
| manual creep | median 1.27, max 1.75 | median **2.00** |
| highway | **1.000×** | **1.000×** |

⇒ **Worst case (scale B), manual creep and creep grind #2 both sit at 2.00× — exactly the dose
V62/V65 flew.** That is bounded and known rather than speculative: the operator drove V62/V65 for
weeks. But if creep grind #2 returns, **this is the mechanism**, and P6 is the test.

### 4.2 The four operating points

| point | stock | V68 engaged | **V69** |
|---|---|---|---|
| grind #1 (7.2 km/h, \|dtq\| 603) | 1.000 | 2.001 | **1.835** |
| creep grind #2 (5.0 km/h, \|dtq\| 1206) | 1.000 | 2.185 | **1.267** |
| **highway lane change (93 km/h, \|dtq\| 164)** | 1.000 | **2.414** | **1.000** |
| manual creep | 1.000 | 1.000 | **1.835** ← the cost |

### 4.3 Why not "Design A" (`0xD2ABC` alone, 2561 → 7051)

**REJECTED, on its own hump.** Raising Y[1] alone makes a triangular spike `2561 → 7051 → 2247`
peaking exactly on the `X[1] = 400` breakpoint:

| | max multiplier | where | rate-axis slope | 2f depth | % of real driving > 2.00× |
|---|---|---|---|---|---|
| stock | 1.000 | — | 0.750 | 1.032 | — |
| **Design A** | **2.753** | 10 km/h, \|dtq\| 400 | **11.300** | **2.753** | **1.98%** |
| **V69** | **2.000** | ≤10 km/h | 3.850 | 1.122 | **0.00%** |

The record understates the hump as "~2.45×" — that is its value at grind #1's 128 deg/s only. The
true maximum is **2.753× at 10.0 km/h / 86 deg/s**, and it exceeds 2.5× across **9–16 km/h**, a band
cars drive through constantly. Reproduced independently, twice.

⭐ **AND A SECOND, INDEPENDENT REASON TO REJECT IT — Design A is sized for the wrong rate band.**
Its boost is a **ramp that only starts at the axis-400 breakpoint**, but V62's measured fix was
**largest at |rate| 16–32 deg/s** (42× suppression). Design A delivers only **1.1–1.5×** there:

| deg/s | 3.2 km/h | 5.0 | 7.2 | 10.0 | 14.4 |
|---|---|---|---|---|---|
| **16** | 1.09 | 1.15 | 1.22 | 1.33 | 1.30 |
| **32** | 1.18 | 1.30 | 1.45 | 1.66 | 1.59 |
| 128 | 1.41 | 1.67 | **2.00** | 2.46 | 2.31 |

**V69 delivers exactly 2.000× across that whole band** (16–32 deg/s sits inside the flat `[0, 400]`
segment on *either* scale), because it lifts the segment uniformly instead of tilting it. Region
scores: **V69 min 1.75 / median 2.00** vs **Design A min 1.09 / median 1.45** on scale A, and
**1.90 / 2.00** vs **1.01 / 1.05** on scale B.

⚠ 🛑 **CORRECTION TO MY OWN EARLIER REACHABILITY FIGURE.** I first reported "Design A exceeds 2.00×
in 1.99% of 318k frames" using a **torsion-bar torque rate** reconstructed from the `tq` channel.
**That is the wrong quantity for this axis** — the inner axis is a steering/motor *rate*, not a
torque rate. The *surface* properties above (max 2.753×, the region tables, the operating points)
are computed on the axis in its own counts and are unaffected; **the percentage-of-driving figure is
withdrawn.** The rejection does not depend on it: the hump's magnitude and the wrong-rate-band
argument each suffice on their own.

### 4.4 The Pareto front, and what was given up

Grid search over (rec0 Y[0..1] scale, rec1 Y[0..1] scale, shared Y[2] scale):
**≥ 1.90× at grind #1 and ≤ 1.35× at creep grind #2 are JOINTLY INFEASIBLE** with max ≤ 2.00× and
highway exactly 1.000×, because both points sit on the same linear segment between X[1]=400 and
X[2]=1500 and **the breakpoints cannot move** (§5.2). Relaxing to ≥ 1.80× leaves two:

| f0 | f1 | f2 | grind #1 | creep #2 | max | slope | 2f | halfwords |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 2.0 | 1.1 | 1.851 | 1.340 | 2.000 | 3.600 | 1.113 | 6 |
| **2.0** | **2.0** | **1.0** | **1.835** | **1.267** | **2.000** | 3.850 | 1.122 | **4** |

**Chosen: the second** — fewer halfwords, each an exact doubling, and more margin on creep grind #2,
which is the symptom currently at zero and the one V62's ungated 2× demonstrably reawakened.
⚠ **Cost: grind #1's dose falls 2.00× → 1.835×.** On the recorded dose–response (Kd = 1.00 → 1.00
ref; Kd = 2.00 → 0.39; V67 gated → 0.40 [0.27, 0.58]; null [0.88, 1.13]) that should still land near
0.42–0.45, far outside the null — but it **spends margin**, and if grind #1 returns, this is why.
🛑 **OUTCOME: grind #1 DID return — and this was NOT why.** The prediction failed because the
dose–response it leans on is an **r24-only** curve priced at `a = 0`, and **r24 is now measured
near-inert**: the clean r24 ladder reads **flat from ×1 to ×4 (879 / 729 / 746)**, while the two builds
that fixed grind #1 are the two that changed **r26**. See banner (3).

---

## 5. THE TWO GATES

### 5.1 GATE 1 — RAM ownership: **VACUOUS**
No cave growth, no new instruction, no new RAM cell. Edits 1, 2, 7 are in-place byte changes to
existing instructions/cals; 3–6 are ROM table constants. Nothing is claimed.

### 5.2 GATE 2 — closed-loop stability: magnitude AND phase

**PHASE: unchanged everywhere.** V69 edits no filter, no pole, no delay, no `sar`. The finite-
difference delay cal `0xC6C42` stays 4. A pure gain change contributes no phase.
🛑 The record already closed the filter route: a differentiator (+20 dB/dec) against one real pole
(−20 dB/dec) is flat above the corner, and two poles low enough to bite by 42 Hz cost −92° at
20.9 Hz and destroy the damping. **Do not re-propose. Raising `0xC6C42` fails identically.**

🛑🛑 **THE MAGNITUDE LEG BELOW IS SUPERSEDED BY §0.1 AND NO LONGER HOLDS AS WRITTEN.** At the
as-built **4.000×** the bracket is *broken*: it is an extrapolation to twice the largest dose ever
driven, and the saturation margin falls to **0.81×** of the repo-recorded max `|dtorque|` — the lane
can rail. The **phase** leg above is unaffected and still holds in full. Read the paragraph below as
the argument for the 2× design it was written for, and §0.1 for what is actually on the artifact.

**MAGNITUDE: bracketed by two flown-stable configurations, with zero exceedance.**
Stock = 1.000× is the shipped configuration; V62/V65 flew a flat **2.000×** and were flight-clean
(`ST == 4` = 0). V69's maximum is **exactly 2.000×**, reached only at ≤10 km/h, and over 318,144
frames of real driving it exceeds 2.00× in **0.00%** of samples. **The bracket holds unconditionally.**

**Parametric pump (the criterion `studies/sessions/v68/v68_design_math.py` pre-commits to).** `gp-0x6ac0` is *rectified*,
so the rate axis sweeps at 2× the mode frequency; the pump cares about gain modulation depth over a
half-cycle. Stock **1.032**, V69 **1.122**, Design A **2.753**. V69 sits ~9% above stock.

**Saturation margin** — r24 clamps at `|dtorque| ≥ 8192·1024/gain`; measured max `|dtorque|` = 839:

🛑 **Corrected from my first draft, which quoted the gain at grind #1's point rather than the
design's PEAK gain — the peak is what sets the margin.**

| | **peak** gain | saturates at \|dtorque\| | margin vs 839 |
|---|---|---|---|
| stock | 3072 | 2731 | 3.25× |
| V67/V68 arm | 5244 | 1599 | **1.91×** |
| **V69** | **6144** | **1366** | **1.63×** |
| Design A | 7051 | 1191 | 1.42× |

✅ **SETTLED ON-CAR — the concern below did NOT bite.** Route `4f` measured transfer-corrected
`|dtorque|` max **633.9**, with **0.0000%** of engaged time at or above V69's **683** rail ⇒ **the full
4.000× was delivered**, and V69's result cannot be explained as clipping. The pre-flight reasoning is
kept as written because it was the right thing to worry about.

⚠ **V69's saturation margin is 1.63×, WORSE than the 1.91× on the car today** (better than Design
A's 1.42×). Quoted against the repo's recorded max `|dtorque|` of **839**; against the 511 measured
directly on the two V68 routes it is 2.67×, and the 28 Hz burst itself is only **254** counts.
🛑 Every `|dtorque|` figure in this kit is a **LOWER BOUND** — CAN's 50 Hz Nyquist hides content
whose contribution to the real `gp-0x4f62` is *rising* through that band. **This is the one metric
on which V69 is worse than V68, and it is disclosed rather than buried.**

**⚠ One accepted discontinuity, stated because it is real.** `rateKey` folds to 0 at ≥ 13001 counts
(`0x3AAC8`/`0x3AACC`), i.e. **2759 deg/s** — fault-level, not reachable in ordinary driving. Raising
Y[0] enlarges the step across that fold: at 0 km/h stock steps 1536 → 3072 (**2.00×**), V69 steps
1536 → 6144 (**4.00×**); at 10 km/h 1.32× → 2.63×. Bounded, unreachable, and recorded rather than
hidden.

**Blast radius.** rec0 and rec1 are reached by **exactly one pointer each** (`0xCBF84`, `0xCC06C`),
both mode-10 slots ⇒ **the edit touches one car variant.** Their interpolated output lands in
`gp-0x6e40`/`gp-0x6e38`, read at only four addresses, **all inside `FUN_0003aa2c`** — zero other
consumers, by a three-method scan (disp16, disp23 extended form, LE32 literal).
✅ **NO FLOAT MIRROR.** Four encodings × every rec0/rec1 X and Y value, unaligned over all 1,048,576
bytes: **zero hits on any Y value.** The clinching argument is that a mirror must carry *all* the
values, and 2561 / 2247 / 1947 / 2322 / 1400 / 3000 are absent in every encoding. The known
precedent `FUN_00043e44` is the float twin of a *different* table and contains zero literals for
these records. ⇒ **the V22/V27 int–float desync class does not bind V69.**
🛑 **This is why V69 edits Y values ONLY and never an X breakpoint** — X = 400 and X = 1500 *do*
have single f32 hits (`0xC661C`, `0x55B5A`), so moving a breakpoint would reopen the question.

**Safety anchors, re-verified across stock and all 11 archived images:** role table `0xC4124` =
`[0,0,5,0,5,5,0,0,0,5,0]` — **no slot ever 6 or 7**, so `gp-0x67ac` stays 0 and the rate lanes cannot
silently drop out; `0xC6564` = **40 zero bytes**, so ~~r26 is structurally inert and r24 carries the
whole lane~~ 🛑🛑 **REFUTED ON-CAR — NOT merely downgraded.** V70's probe read `gp-0x6adc` (r26's
post-clamp mirror) **strictly negative on 1,644 of 18,010 frames**, and **a pinned-zero cell cannot
clear a `>= 0` test** ⇒ **r26 is LIVE.** What follows is the pre-flight *downgrade*, kept for its
reasoning; **the verdict is now settled against it.**
🛑 **DOWNGRADED 2026-08-04 to BELIEF.** `0xC6564` really is 40 zero bytes with no writer
found for the RAM adjustment (10 of 18 cells) — but **its link to `gp-0x69a4` was NEVER VERIFIED**, and
`gp-0x69a4`'s real producer is a **live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`**.
⇒ ~~*"r24 carries the whole lane"* may still be right (the dose–response argues it is), but it is an
inference, not a byte fact.~~ 🛑 **It is not right — see the on-car refutation above.** And the
dose–response that *"argues it is"* has itself been retired, for pricing every build on r24 alone. **`0xC6564` remains a valid *byte* anchor** — it is simply not evidence
about r26's liveness. ⚠ Separately, the **GATE** leg of the same claim **is** reversed: the gate kills
r26 only at `|gp-0x6bda| ≥ 384`, and hands-off `gp-0x6bda` ≈ 9262 = 24× that.

---

## 6. THE COST, AND THAT IT WAS THE OPERATOR'S CALL

Reverting the gate makes the shaped surface apply in **both** arms. Manual steering below ~50 km/h
gains the rate damping that today applies only when LKAS is engaged; **manual highway is
byte-identical to stock.** Over the pooled 318k frames, **50.7%** of samples see > 1.5× (that set is
creep-heavy and over-represents low speed). This is close to what V62/V65 already delivered and the
operator drove for weeks. **He was shown this trade explicitly, with the cave alternative priced,
and chose it.**

---

## 7. PROBE — 🛑 SUPERSEDED BY §0.2

**This section describes the ×2 revision's probe: two in-place immediates that spent bits 5 and 4 on
Honda's oscillation detector and made bit4 a constant. As built, all three rungs read RATCHET
candidates and the cave is rewritten (66 B of the proven 68). The one claim below that SURVIVES is
the bit3 build-class argument — V69 still emits `movea 0x80` and V68 still emits `0x88`, so
V68-vs-V69 remains structurally disjoint.** Kept for that argument and for the V70 note in §7.1.

### 7.0 (superseded) build identity for **two in-place immediate bytes**

V68 and V69 would otherwise emit **identical payloads** and be indistinguishable from a log: bit6
reads `gp-0x6806` in the *cave*, independent of the control-path gate at `0x3AA94`. That is
unacceptable — V68 is what is on the car, so V68-vs-V69 is exactly the confusion that matters.

**Edit 7 — the structural half.** V68's bit3 is **not derived from any signal**: it is baked into the
liveness `movea 0x88,r0,r7`'s immediate. V69 emits `movea 0x80` instead — **one byte at `0xC4B36`,
the same instruction, no new bytes.** V68 therefore sets bit3 in *every* frame and V69 clears it in
*every* frame. **The two payload sets are structurally disjoint; no measurement can make them
overlap.**

**Edit 8 — the practical half, because bit3 alone is not enough.** ⚠ **V67 already emits
`movea 0x80`** (verified: `0xC4B34` = `20 3e 80 00` on V67), so Tier 0 alone makes V69's payload set
*identical to V66/V67's*. Edit 8 changes `cmp 0x1,r6` → `cmp 0x0,r6` at `0xC4B54`: `ld.bu`
zero-extends, so `r6 ∈ [0,255]` and a signed `blt` against 0 is **never** taken ⇒ **bit4 is set in
every frame.**

| bit | V69 |
|---|---|
| 7 | liveness |
| 6 | `gp-0x6806 != 0` — the LKAS gate (still a useful arm split for analysis) |
| 5 | `gp-0x67df != 0` — the 1 kHz detector's crossing stage. **Kept: now proven live** (§8) |
| **4** | **constant 1** |
| **3** | **constant 0** |

**Legal payload sets, and the decision rule:**

| build | byte4 set |
|---|---|
| V66 / V67 | `{0x87, 0x97, 0xA7, 0xB7, 0xC7, 0xD7, 0xE7, 0xF7}` — in practice only `0x87`/`0xC7` |
| V68 | `{0x8F, 0x9F, 0xAF, 0xBF, 0xCF, 0xDF, 0xEF, 0xFF}` (bit3 = 1 always) |
| **V69** | **`{0x97, 0xB7, 0xD7, 0xF7}`** (bit3 = 0, bit4 = 1) |

⇒ *"bit3 clear in every frame"* excludes V68 **structurally**. *"bit4 set in every frame"* excludes
V66/V67 **practically** — their bit4 (`gp-0x671a ≥ 5`) read **0 in 186,321 frames**. A 5-bit field
cannot make three classes structurally disjoint; this is the best available and its limit is stated.
Burning bit4 costs nothing: it is redundant with bit5 (a reversal implies a crossing) and has never
fired in any build.

### 7.1 ⚠ The `gp-0x6c2c` ladder — designed and costed, DEFERRED TO V70

`gp-0x6c2c`'s *production* (`FUN_00041464`) contains **zero calls to `FUN_00046EA6`** — confirmed
from its decompile, not merely cited — so it bypasses the detector's DTC gate entirely, and reading
it directly also sidesteps the `T` = 12800 / `CEIL` = 5 quantisation. It would give this kit the
**positive control the FSM flags have never once provided**.

It has been fully designed and it *fits*: a 2-rung monotone ladder at T/4 = 3200 and T/2 = 6400,
sharing one absolute-value prefix (`ld.h` / `cmp r0,r6` / `bge +4` / `subr r0,r6`) and subtracting
the **incremental** 3200 in place, so both rungs are the byte-identical `movea -0xc80,r6,r6`.
Cost **58 B** against the proven 68 B extent — *smaller than V68's 60 B* — staying within the
r6/r7-only, exactly-one-store discipline every flown cave has met. A 3rd rung at T/8 needs 46 B
against a 44 B ceiling: **2 bytes over.**

🛑 **Not taken for V69, and the reason is the standing rule, not the byte count.** *"Every success
since V29 has been cal-only or a single in-place branch/displacement edit."* Edits 1–8 are all in
that class. The ladder **rewrites ~34 bytes of cave body** with instructions (`subr`, `bge`, signed
`ld.h`, negative-immediate `movea`) that this cave has never carried — and code caves are this kit's
**only bricking class** (V24, V27, V48B). V69's job is the fix; **P1 needs no probe at all.** Fly
V69, learn whether P1 held, then spend risk on the instrument in V70.
⚠ Two caveats to carry forward: the hook fires at **100 Hz (task 5)** while `gp-0x6c2c` refreshes at
1 kHz, so the ladder is a **decimated snapshot, not a peak-hold** — it can show "≥ threshold at this
sample", never "never crossed between samples". And the proposed bytes are **hand-derived**,
cross-validated against three real reference points but **not yet run through the kit's own encoder
and self-check pipeline**, which must be the final gate.

---

## 8. WHAT V69 INHERITS AS SETTLED

**Honda's 1 kHz detector is LIVE — V68's zero is a QUIET BAND, not a dead instrument.** Verified this
session: the entry gate at `0x428D8`–`0x428E2` (`mov 0x5,r6` / `jarl FUN_00046ea6` / `cmp r0,r10` /
`be 0x428E6` / `jr 0x42A76`) runs the body when the active-DTC mask bit is **clear**; the flights
were fault-clean. `gp-0x67df` has exactly 2 firmware accesses (read `0x428E6`, write `0x4299C`) plus
our cave read; zero extended-form hits, zero address literals. The input `gp-0x4f50` has one writer
fed from the live resolver chain, refreshed every task-1 tick. Every detector cal is live and sane
(T = 12800, CEIL = 5, dwell = 50, release = 5000, K1 = 37, K2 = 22).
⚠ **Residual:** the exact DTC↔bit5 mapping is not pinned, so "mask was clear" rests on flight-clean
telemetry rather than exhaustive proof.
★ **And it corroborates the lever from an unexpected direction:** the 28 Hz event ran 1468 counts p-p
on the *torsion bar* yet never tripped a detector watching *resolver-derived motor rate*. The mode
lives on the bar/column side — exactly the channel `gp-0x4f62` differentiates and r24 amplifies.

---

## 9. PRE-REGISTERED PREDICTIONS — written before the build exists

⚠ **P1/P2/P6 were sized for the ×2 dose and are NOT re-derived for ×4** — the dose–response is only
measured out to 2.00×, so extrapolating them would be inventing precision. Read them as *directions*
at ×4, not as intervals. **P3, P4 and P5 are dose-independent and stand exactly as written.**
**New at ×4, and pre-registered here:**

| | prediction (×4) |
|---|---|
| **P7** *(new)* | probe **bit6** (r24 lane ≥ +4096) fires on any real drive. If it reads 0.000%, the cave is not the one documented — check bit7 and the `.rwd` name **before** interpreting bits 5/4 |
| **P8** *(new, the 4× cost)* | bit6's duty at engaged creep is **materially higher than at highway**, because the 4× surface applies only below 50 km/h. A flat duty across speed would mean the surface edit is not reaching the lane |
| **P9** *(new, the ratchet)* | if the ratchet is a lane-level hard nonlinearity, at least one of bits 6/5/4 carries a **6–9 Hz line above its own split-half null** during engaged-creep hands-off episodes. 🛑 **A null here is NOT a refutation** — the rungs are one-sided and bits 5/4 have no positive control |

| | prediction (as specced, ×2) |
|---|---|
| **P1** | engaged-highway maneuver **26–30 Hz falls ~3.3× [1.33, 6.78]** toward the Kd = 1 level |
| **P2** | engaged-creep 18–22 Hz (grind #1) stays fixed, **~0.42–0.45** vs the Kd = 1 pool (null [0.88, 1.13]) — slightly weaker than V68's 0.40 |
| **P3** *(negative control)* | 40–49 Hz at highway **does not move** (1.36 [0.95, 1.79] — no dose response) |
| **P4** *(negative control)* | 1–4 Hz driver band **does not move** |
| **P5** | `ST == 4` stays 0; the zero-EME streak continues |
| **P6** *(new)* | creep grind #2 stays at **zero bursts** in both arms — V69 runs 1.267× where V62's 6-burst manual arm ran ~2× |

**P3 and P4 are what catch me being wrong**: if they move, the edit did something other than intended.
**No scripted drive is needed** — route `4e` yielded 18 maneuver windows in ~4 min at speed, so an
ordinary 20–30 min engaged highway commute gives ~5–7× that, enough to test P1.

---

## 10. BUILD REQUIREMENTS (for `builds/v50_v79/build_v69_tva.py`)

1. **Three CRC blocks.** `builds/v50_v79/build_v68_tva.py` recomputes only `sorted({MAIN, CAL})` **and asserts the
   CAL CRC did not move** — that assert fires on edit 2. Use **`builds/v50_v79/build_v60_tva.py:202-216`'s generic
   template**, which calls `V53.owning_block(code, addr)` and recomputes the union.
2. **Relax** `builds/v50_v79/build_v68_tva.py:1378-1381` (`for rec in GAIN_B_RECORDS` byte-identity) and
   `V66.assert_gain_b_surface(...)` at line 1398 — they assert the surface is stock.
3. **Keep** `D2000_BLOCK = (0xD2000, 0xD2010)`'s identity assertion: it is the machine proof that
   V60's falsified cells stay put, and it is untouched by this edit.
4. **Assert the neighbours**: mode-11 (`0xD2AC4`…) and mode-12 records byte-unchanged (§3.4).
5. **Ship `verify/verify_v69_image.py` with EXACT-VALUE anchors.** 🛑 `verify/diff_build_vs_stock.py` is
   **span-based, not value-based** — a wrong value inside an existing `EDITS` span is silently
   attributed and the gate passes. Anchor every one of the 7 bytes, plus `0xC4124` **and `0xC6564`**
   (which `verify/verify_v68_image.py` does *not* check).
6. **Add `EDITS` rows** for `0xD2A7E-0xD2A81`, `0xD2ABA-0xD2ABD`, `0x3AA96`, `0xC4B36`, `0xC4B54`, and change
   the `0xC6446` row to 512.
7. **Re-read `0xC4124` every build and STOP if any slot carries 6 or 7** (inherited from V68).
8. 🛑🛑 **ASSERT THE EDIT-ORDER INVARIANT — this one can make the car worse than stock.**
   Edits 1 and 2 are **jointly** safe and **individually** dangerous in one direction: writing
   `0xC6446 = 512` while the gate at `0x3AA96` stays repointed to `gp-0x6806` leaves the arm LIVE at
   **512, which is ~5× BELOW the stock LERP**, degrading engaged steering everywhere. The builder
   must assert **`0xC6446 == 512` ⟹ `0x3AA96 == 0xc5`** and refuse to emit otherwise.
   (Reverting the gate alone is harmless: nothing then reaches `0xC6446`.)
9. Verify with a fresh Ghidra import — 🛑 a stale import defeats hash-checking.

---

## 11. DOCUMENTATION DRIFT FOUND WHILE SPECCING THIS — fix before the next session

1. 🛑 **The tracer memory's record→speed rotation** (§3.2). Highest priority; it would invert a design.
2. 🛑 **`docs/BUILD-LINEAGE.md` line 38**: "`0xC644A` … V43 … 1024→64" is **wrong**. **V43 shipped 32**
   (`builds/v18_v49/build_v43_tva.py:195 POLE_NEW = 32`, confirmed in `_v43_plain_image.bin`); **64 was V49**, and
   the −7.1 dB figure belongs to V49.
3. ⚠ **`memory/accord/calibration/accord-r24-gain-b-four-pointer-arrays.md`**: "the 10 km/h record uses 1400" — **1400 is
   rec0, the 0 km/h record**; rec1 (10 km/h) uses 1500.

---

## 12. OPEN / NOT CLOSED

- **BELIEF: "mode = 10 on this car."** `gp+0x63fd` is RAM with 6 runtime writers, not statically
  readable. The PN-key chain plus V55's on-car damper-variant bit (same cell, `0x34502`) corroborate
  transitively — strong, but not a fresh measurement. **Every number here is mode-10-specific.**
- **`gp-0x4f50`'s physical units — [OPEN]**, deliberately. Do not close by borrowing `gp-0x6ac0`'s
  4.7121 counts/deg-s; composing those chains produced the retracted "bus = 8 × deg/s".
- **The DTC↔bit5 mapping** behind the detector gate (§8).
- **r26's inertness** rests on a zero cal base plus no writer found across 10 of 18 cells.
- **The mechanism itself** (§1) — P1 is the test.
