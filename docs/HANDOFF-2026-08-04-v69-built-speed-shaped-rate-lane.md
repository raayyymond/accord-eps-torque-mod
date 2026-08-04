# HANDOFF 2026-08-04 — V69 built: revert the gate, shape Honda's own speed schedule

**★★★ THE RESULT: V69 is built and unflashed. It removes the engagement-conditional 24–30 Hz
amplification at highway by deleting the mechanism that causes it — a FLAT rate-lane arm whose
delivered multiplier *rises* with speed and peaks exactly where the symptom is — and replaces it by
shaping Honda's own speed-scheduled surface, which rolls off to stock by 50 km/h.**

Spec `docs/V69-DESIGN.md` · builder `analysis-2020accord/build_v69_tva.py` · verifier
`analysis-2020accord/verify_v69_image.py`. Predecessor:
`HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`.

---

## 1. WHY THIS BUILD EXISTS

Routes `4c`/`4e` captured the operator's symptom. Route `4e` seg 33, t = 51.3 s — openpilot fires
`preLaneChangeRight` and executes an ALC right lane change at **25.93 m/s**:

| quantity | value |
|---|---|
| torsion bar peak-to-peak | **1468 counts** |
| 26–30 Hz envelope | **614** (route median 31 ⇒ **20×**) |
| spectral lines | 27.73 / **28.12** / **28.51** Hz, prominence **100–107** |
| **40–49 Hz, same window** | **69** |
| wheel order 2 / 3 · engine order 1 / 2 | 24.93 / 37.40 · 26.10 / 52.20 Hz — **none of them** |

✅ The estimator's own control fires in that window: lines at **37.10/37.49 Hz** *are* wheel order 3.

And V67/V68's arm is the mechanism's shape: it is a **flat scalar** taken whenever the LKAS gate is
open, while Honda's stock surface **rolls off with speed** (3072 → 2151). So the delivered multiplier
climbs with speed and **maxes out at highway — 2.4383×** — which is precisely where the symptom lives.

---

## 2. THE DESIGN IS FORCED, NOT CHOSEN

The r24 gain selection is a four-way priority ladder, verified by hand-decoding the flown bytes:

```
0x3ABFA  cmp r0,r6   ; MASK  gp-0x671d != 0  -> cal 0xC6442 = 1024
0x3AC04  cmp r0,lp   ; GATE  gp-0x6806       -> cal 0xC6446 = 5244
0x3AC0E  cmp r0,r2   ; 3rd   gp-0x671a >= 5  -> cal 0xC6440 = 2048
0x3AC16  (join)      ; else  the mode-10 speed x rate LERP
```

Three facts close the design space:

1. **One scalar cannot serve both endpoints.** Stock LERP is **2621** at grind #1 and **2172** at
   highway. 1.00× at highway needs 2172 — which is **0.83×** at grind #1, *below stock*, i.e. V61
   territory, and **V61 made grind #1 worse**. 2.00× at grind #1 needs 5244 — which is **2.4383×** at
   highway, reproducing the measured 2.44× exactly.
2. **Speed shaping lives only on the DEFAULT branch**, and the gate **replaces** that value rather
   than scaling it.
3. **The gate branch is 10 bytes with zero slack** (`cmp` 2 + `be` 2 + `ld.hu` 4 + `br` 2), packed
   between two other arms.

⇒ *Gated AND speed-shaped* requires inserting instructions on the **1 kHz path** — a code cave, this
kit's **only bricking class** (V24, V27, V48B all bricked the ECU), also subject to DTC 0x18's
per-task overrun budget. **Rejected.** V69 reverts the gate and shapes the surface; the operator was
shown that trade with the cave alternative priced and **chose it**.

---

## 3. THE EDIT — 8 edits / 11 changed bytes / 3 CRC blocks

| # | addr | before → after | what | block |
|---|---|---|---|---|
| 1 | `0x3AA96` | `fb` → `c5` | gate reverts to the dead `gp-0x683c` (0 writers image-wide) | MAIN |
| 2 | `0xC6446` | 5244 → 512 | now-unreachable arm back to stock | CAL |
| 3–4 | `0xD2A7E`/`0xD2A80` | 3072 → **6144** | mode-10 gain_B **0 km/h** Y[0..1] | `0xD2000` |
| 5–6 | `0xD2ABA`/`0xD2ABC` | 2561 → **5122** | mode-10 gain_B **10 km/h** Y[0..1] | `0xD2000` |
| 7 | `0xC4B36` | `88` → `80` | probe: bit3 **CLEAR** | MAIN |
| 8 | `0xC4B54` | `61` → `60` | probe: `cmp 0x0,r6` ⇒ bit4 **CONSTANT 1** | MAIN |

Every surface halfword is an **exact doubling**. Multiplier: **2.000× to 10 km/h** → 1.886 @15 →
1.769 @20 → 1.526 @30 → 1.270 @40 → **exactly 1.000× at and above 50 km/h**, in both arms.

★ **THE HIGHWAY 1.000× IS STRUCTURAL.** The lane-change point (93.35 km/h = 5980 counts) lies in the
cross-axis `[3200, 6400]` segment, so the interpolation there reads **only rec2 and rec3** — which
this edit does not touch. **Proven by a 12,221-point sweep in the builder**, not argued. It cannot
drift with a re-tune.

★ **AND IT DOES NOT BET ON THE OPEN AXIS SCALE.** The inner axis's counts-per-deg/s is **[OPEN]**
(repo runs 4.7121; the chain-direct alternative is 0.58901). V69 doubles the *whole flat `[0,400]`
segment* rather than leaning on where a breakpoint falls, so its creep dose is **2.000× on both
scales**.

---

## 4. WHY "DESIGN A" WAS REJECTED — three independent counts

The pre-existing one-halfword candidate (`0xD2ABC` 2561 → 7051):

1. **Its hump is 2.753×, not the recorded ~2.45×** — that figure is only its value at 128 deg/s. The
   true maximum is at 10.0 km/h / 86 deg/s, and it exceeds 2.5× across **9–16 km/h**.
2. **It swings 2.00× → 1.22×** at grind #1 across the two axis scales — a bet on scale A.
3. ⭐ **It is sized for the wrong rate band.** Its boost is a ramp starting at the axis-400
   breakpoint, but **V62's measured fix was largest at |rate| 16–32 deg/s (42× suppression)**, where
   Design A delivers only **1.1–1.5×**. V69 delivers exactly **2.000×** across that band on either
   scale. Region min/median: **V69 1.75/2.00** vs **Design A 1.09/1.45**.

An independent directed search over 8 edit families converged on **V69's exact four addresses and
four values**.

---

## 5. THE COSTS, STATED RATHER THAN BURIED

1. **Manual steering below ~50 km/h now gets the rate damping.** Manual highway is byte-identical to
   stock. Close to what V62/V65 already delivered and the operator drove for weeks.
2. ⚠ **Saturation margin drops 1.91× → 1.63×** (peak gain 6144 saturates at `|dtorque|` 1366 against
   the recorded max 839; against the 511 measured on the V68 routes it is 2.67×, and the 28 Hz burst
   itself is only **254**). **This is the one metric on which V69 is worse than what is on the car.**
3. ⚠ **On the pessimistic axis scale, manual creep and creep grind #2 are both 2.000×** — exactly the
   dose V62/V65 flew. Bounded and known, not speculative.

---

## 6. 🛑 TWO TRAPS THE BUILDER ASSERTS AGAINST

**(a) THE EDIT-ORDER INVARIANT — this one can make the car WORSE THAN STOCK.** Edits 1 and 2 are
jointly safe and individually dangerous in one direction: writing `0xC6446 = 512` while the gate
stays repointed leaves the arm **LIVE at 512, ~5× BELOW the stock LERP**, degrading engaged steering
everywhere. Asserted as `arm == 512 ⟹ gate byte == 0xc5`; the builder refuses to emit otherwise.

**(b) THE NEIGHBOUR TRAP.** Modes 10/11/12 interleave at stride `0x14`, and **mode 11's and mode 12's
0 km/h records are BYTE-IDENTICAL to mode 10's**, with their 10 km/h records one count below — the
target pattern occurs **three times within 40 bytes**. Every cell is addressed absolutely and all
eight neighbours are asserted in both builder and verifier, because
**`diff_build_vs_stock.py` is span-based and would not catch a stray hit.**

---

## 7. GATES AND VERIFICATION

**GATE 1 — RAM ownership: VACUOUS.** No cave growth (60 B of the proven 68 B), no new instruction, no
new RAM cell; the cave's sole store is still the existing CAN-330 payload byte with bits 2:0 preserved.

**GATE 2 — closed-loop stability.** **Phase unchanged everywhere**: no filter, pole, delay or `sar`
edited. **Magnitude bracketed**: max = exactly **2.000×**, inside `[stock 1.00×, V62/V65 2.00×]`,
both flown flight-clean. **2f parametric-pump depth 1.122** vs stock 1.032 (Design A 2.753).
⚠ Accepted, bounded: raising Y[0] enlarges the step across the `rateKey` fold at 2759 deg/s
(fault-level, unreachable) from 2.00× to 4.00× at 0 km/h.

✅ **NO FLOAT MIRROR** on any Y value — four encodings, unaligned, over all 1,048,576 bytes. The
clinching argument: a mirror must carry **all** the values, and 2561 / 2247 / 1947 / 2322 / 1400 /
3000 are absent in every encoding. ⚠ **X values DO have f32 hits** (`0xC661C`, `0x55B5A`), which is
exactly why **V69 edits Y only and never a breakpoint**.

✅ 50/50 CRC across 3 blocks · x31 checksum PASS · **the RWD decodes exactly back to the image and
every gate re-runs on the readback** · `verify_v69_image.py` **all anchors PASS** ·
`diff_build_vs_stock.py v69` **0 unattributed**, V68 unregressed, self-test still fails informatively.

★ **`verify_v69_image.py` caught its own author.** Its first run failed two anchors — I had assumed
mode 12's records matched mode 11's; they do not (`0xD2B14` is 2303/2303/2151/1947, not
2304/2304/2150/1946). **That is a value-anchored verifier doing precisely the job a span-based differ
cannot.** The image was correct; my expectations were not.

---

## 8. 🛑 THE PREMISE, AND WHAT WOULD FALSIFY IT

**The mechanism is SUGGESTIVE, NOT ESTABLISHED.** The 26–30 Hz maneuver-conditioned dose ratio is
**3.334 [1.201, 6.492]** against a split-half null of **[0.33, 3.36]** — it does **not** clear its own
floor, because the Kd = 1 maneuver arm holds only 39 windows / 17 blocks (~50 s). The operator was
offered the drive that would settle it (~150–250 s more active LKAS-off highway maneuvering) and
**declined**; V69 is built on it by explicit decision. That must not be written up later as though
the mechanism had been proven first.

**Pre-registered, before the build existed:**

| | prediction |
|---|---|
| **P1** | engaged-highway maneuver **26–30 Hz falls ~3.3× [1.33, 6.78]** toward the Kd = 1 level |
| **P2** | engaged-creep 18–22 Hz (grind #1) stays fixed, ~0.42–0.45 vs the Kd = 1 pool |
| **P3** *(neg. control)* | 40–49 Hz at highway **does not move** |
| **P4** *(neg. control)* | 1–4 Hz driver band **does not move** |
| **P5** | `ST == 4` stays 0 |
| **P6** | creep grind #2 stays at **zero bursts** in both arms |

**P3 and P4 are what catch this being wrong.** No scripted drive is needed — route `4e` gave 18
maneuver windows in ~4 min at speed, so an ordinary 20–30 min engaged highway commute yields 5–7×.

---

## 9. OPEN / NOT CLOSED

- **BELIEF: "mode = 10 on this car."** `gp+0x63fd` is RAM with 6 runtime writers. The PN-key chain
  plus V55's on-car damper-variant bit corroborate transitively — strong, not a fresh measurement.
  **Every number here is mode-10-specific.**
- **The inner axis's counts-per-deg/s — [OPEN]** (4.7121 vs 0.58901). V69 is deliberately invariant
  to it; the *manual-creep cost* is not.
- **`gp-0x4f50`'s physical units — [OPEN]**, deliberately. Do not close by borrowing `gp-0x6ac0`'s
  4.7121; composing those chains produced the retracted "bus = 8 × deg/s".
- **The DTC↔bit5 mapping** behind the detector's entry gate (the detector itself is now proven live).
- **The `gp-0x6c2c` amplitude ladder** — designed and costed at **58 B** against the 68 B extent
  (smaller than V68's 60 B), within the r6/r7-only one-store discipline. **Deferred to V70**: it
  rewrites ~34 bytes of cave body, and the rule that has held since V29 is cal-only or single
  in-place edits. Its bytes are hand-derived and have **not** been through the kit's encoder
  pipeline — do not treat §7.1 of the spec as build-ready.

---

## 🛑 METHOD NOTES

1. **A value-anchored verifier catches what a span-based differ cannot.** `diff_build_vs_stock.py`
   attributes by RANGE, so a wrong *value* inside an existing edit span passes silently. Ship both.
2. **When two edits are jointly safe and individually dangerous, assert the implication in the
   builder.** Not in a comment — in code that refuses to emit.
3. **Check whether the neighbours are byte-identical before trusting any pattern-shaped reasoning.**
   Here three variants share a record's bytes within 40 bytes of each other.
4. **A repo memory can be rotated.** A tracer memory assigned the four records to the wrong speeds,
   which would have put this edit on the 10 and 50 km/h records and *raised* the highway end. Three
   independent checks (pointer arrays, cross-axis, Y[0] monotonicity) were needed to settle it.
