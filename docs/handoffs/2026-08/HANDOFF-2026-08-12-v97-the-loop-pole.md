# HANDOFF 2026-08-12 (late) — V96 flew, the crux became a trajectory, and V97 moves a loop pole

**Read after:** `docs/handoffs/2026-08/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md`.
**Agent outputs:** `analysis-2020accord/sessions/v97/` (7 files, ~190 KB) · figures in
`analysis-2020accord/figures/r7e_r7f/` (22) and `sessions/v97/plots_rtc/` (20+).

---

## 0. WHAT CHANGED, IN FIVE LINES

1. **V96 is on the car** — routes `7e`/`7f`, both fault-free, identity proven single-frame. The record
   said V94 for the whole session and **that cost an hour of the best analysis in it.**
2. **The operator renamed the target**: not a band, but **the LKAS return-to-centre trajectory** —
   as smooth as the manual return **and faster**.
3. **Seven candidate levers died**, each before a build was cut, including the pre-declared V97.
4. **Two multi-session blockers closed** — `f′ ≥ 0` (enforced in code) and the `L` coefficients.
5. **V97 cut: `0xC63AC` 102 → 150. One byte.** The first loop-pole lever in the arc.

---

## 1. THE OPERATOR'S OWN FRAMING — three inputs, each of which redirected the session

> *"there is ringing in the driver torque, and a wiggle in the steering angle as it returns to center.
> Normally, without LKAS engaged, there is no ringing and no wiggle. The 2nd case is how the LKAS
> return to center should look, AND it should be faster than with LKAS disengaged."*

> *"take the derivative — the wiggles should look like **wiggles/spikes on top of a raised flat section**."*

> *"it feels like effectively a **steer angle rate limit for LKAS engaged**."*

And, in answer to direct questions: **hands OFF during the return** · **no left/right difference** ·
**he does not feel the ~0.5–1 Hz surge.**

🛑 **The hands-off answer invalidated the kit's own mask.** Every 6–9 Hz number produced before this
session used `|tq| > 1200`, which selects the **wind** phase and excludes the **return** almost by
construction. The orchestrator's own 7.2× headline was about the wind phase and was corrected to the
operator mid-session.

---

## 2. WHAT IS MEASURED, WITH ITS CONTROLS

| statistic | engaged vs off | placebo floor | verdict |
|---|---|---|---|
| **ring** (torque, 4–12 Hz) | **3.5 – 6.5×** across all detector settings | ~2.0 | ✅ robust |
| **wiggle** (angle) | 1.94 – 2.76× | 1.70 – 1.88 | ⚠ marginal |
| **return duration / rate** | 0.65 – 1.20, **flips with the detector** | 1.88 | ❌ **not established** |

🛑 **An earlier "engaged return is 2.25× slower" report was RETRACTED** on these controls. Raw medians
do differ (24.8 vs 67.0 °/s) but `p_placebo` = 0.459, and at 11 engaged / 7 LKAS-off episodes the CI
fold-width on duration is **3.27×** against an observed ~2.7× — **underpowered, not refuted.**

⭐ **The ring persists hands-off** (138/265 ct vs 33/28) ⇒ not a driver-arm artefact.
⭐ **The LKAS command is a DC constant for 52–70 % of the return and rings at full amplitude anyway**
⇒ **the excitation is SENSOR-FED**, and every command-side lever is excluded.

---

## 3. THE SEVEN DEATHS

| lever | how it died |
|---|---|
| **pre-declared V97** (`gp-0x6b4c`/`gp-0x6b4e`) | `gp-0x6b4e` **provably ≡ 0**. §A5 priced gate WIDTH; the failure mode is the signal never being non-zero — that **IS** the V64 null. Array is `gp-0x62c8[]`, not `gp-0x62f8[]`; they are **two different arrays 0x18 apart** |
| **the return-to-centre lane** | It is a **RACK END-STOP CUSHION**: arms on `\|gp-0x6b98\|>4096` **AND** motor rate `<200` — a **stall detector** — splits by sign into left/right stop enums, has **no angle term anywhere**, gate needs `\|gp-0x6bf0\|>8878`. **~99.3 % dead in MANUAL too**, so its absence cannot explain the engaged/manual difference. Arming it would inject end-stop pushback where there is no end stop |
| `0xC520C` governor ceiling | `gp-0x6ac0` scale reconstructed at **4.7121 ct per column °/s** ⇒ first knot **222.8 °/s**. Measured hands-off returns max **528 ct against a 1050 knot — 0.00 %** reach it |
| `0xC6194` LKAS slew limiter | **Real and calibrated** — 3 ct/tick = 1.37 s full scale, exactly the shape the operator described — but its input partition `0xC4118` is **all-1**, so 100 % of the request bypasses it. 🛑 The record's *"output ×0"* reason is **wrong** (that is `0xC6196`). **Arming it goes the wrong way** |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]**, CI excludes the predicted +1 — **and** `gp-0x6b4c` is a **second LKAS route that never sees AUTH** (lane mode 0 at `0xC4124`; `REQ_B` written at runtime `@0x26496`). ⊕ `0xC6CD0`, our own 4× gain, sits on that lane. ⚠ **The table header is `0xC67BE`; `0xC67C8` is its `Y[0]`** |
| PID Ki `0xC6B12` | **INERT** — at 6–10 km/h the P term alone (16,000 at e=2000) already exceeds the anti-windup bound (7,264); the integrator is pinned and Ki is marginally irrelevant |
| `0xC63A6` / `0xC63A4` | `0xC63A6` is **a cliff edge, not a lever** — V91/V92's ×1.5 null and V94's ×0.25 catastrophe fit closed-loop invariance, not a dose-response. `0xC63A4`'s lane carries **~1.1 ct of a 342 ct signal** |

---

## 4. THE TWO BLOCKERS THAT FELL

**`f′` — closed, structurally.** The "RAM-resident, unreadable" LERP is **100 % flash-derived**
(`FUN_000382d8` sole writer → `FUN_000389ec` rescale → `FUN_00038148`), and **`f′ ≥ 0` is enforced in
code at three ungated sites**, so it holds for any cal, any mode, any build. Flash data agrees
**14/14 records strictly increasing** (orchestrator-verified from the V96 image, all four anchors exact).
🛑 **`STATE.md` §A6b's "the transfer cannot be read from the image" is FALSE.**

**`L` — the premise was wrong.** Not 8 floats: **3 floats + 6 halfword Q-format cals**, and two of the
three floats are **hard zero**, so the FIR is an **identity**. The handover also omitted `0xC4048`, the
only nonzero tap.

---

## 5. V97 — ONE BYTE, AND THE DIRECTION IS MEASURED

```
39990-TVA,A160-V97-V96BASE-C63AC.102to150-0x13000-0x100000.rwd
  .rwd  78c674a899971a6a9763c2d7c89bf4c9169f35dfba3fbe4ce62d9bc445a17372
  image 7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3
  builder analysis-2020accord/builds/v80_v107/build_v97_tva.py   131/131   BASE = V96
```

`gp-0x374c += ((target − gp-0x374c) × A) >> 10`, sole reader `@0x38202`, **1 reader / 0 writers**
established five ways, **virgin across all 99 images**. 102 = `0x0066`, 150 = `0x0096` ⇒ **one byte**
plus its CRC trailer at `0xC6FFC`. **DC gain 1.000000 at any A — a POLE, not a GAIN.**

**Direction, two independent instruments agreeing to <7°:**
- **`|Q| = 1.233` on both routes**, coherence 0.974/0.978. The criterion is *inversion iff `|Q| < 1`
  and `cos(arg Q) < −|Q|`* ⇒ **`|Q| > 1` excludes inversion at any phase**; the ±28° CAN-join
  uncertainty is moot.
- **`arg(V) − arg(B′) = −178.1°`** on both routes (reproduced independently at +179.8°/+178.6°).
  `arg(V)` sits just below −90° ⇒ **anti-damping**; lead rotates it toward the damping axis.

🛑 **Cost: +2 %…+13 % at 21 Hz** on the total command, where V62's and V88's grinding fix lives.
Worst case 1.13 × 0.549 = 0.620, inside V88's CI — **but that dilution is a model.** Exchange rate is
**flat at 0.33°/%; there is no sweet spot.** **A = 150 was the operator's choice with the trade stated.**

🛑 **V97 IS NOT A RETURN-SPEED FIX.** Clause 2 has **no mechanism**; three candidates died and nothing
replaced them. **Do not score V97 as if it addressed the return speed.**

---

## 6. 🛑 THE PROCESS FINDING — the direction was inverted once, and only disagreement caught it

`scipy.signal.csd(x, y)` returns `arg(Y) − arg(X)`. An agent labelled every cross-spectrum backwards
and **recommended lowering `0xC63AC`**, which would have made the car worse. The tell was a
**replicated ~90°** disagreement with the independent `Q` estimator — a bug signature, not physics.
The agent retracted unprompted and corrected the record.

**Four tool-zeros in one session**, one of them a new class:
**`ep`-relative short-format aliasing** — an array based once via `movea <off>,gp,ep`, then accessed by
`sld`/`sst` with **no offset in the operand text**. `-0x62f8` → **15 hits, 14 base setups, ZERO actual
accesses.** 🛑 *Worse than a zero: a healthy-looking count that misses 100 % of accesses.*
🛑 `0xC63AC`'s census was **re-tested against this trap and is clean.**

---

## 7. WHAT THE NEXT DRIVE NEEDS

To make clause 2 scoreable: **matched engaged/disengaged hands-off returns from similar starting
angles, many more of them.** 11 vs 7 episodes cannot resolve a 2.7× effect. The scoring config is
machine-readable at `analysis-2020accord/sessions/v97/rtc_measure.json` → `config`; the scorer is
`rlog-tools/studies/ratchet/v97_return_to_centre.py`.

## 8. OPEN

1. **Clause 2 has no mechanism.** Three died; the field is empty.
2. **`BUILD-LINEAGE-PART1` is fifteen builds behind** the by-address grep `CLAUDE.md` makes mandatory.
3. **`model/eps_lkas_chain_model.py` is 309 KB** — past the 256 KB `Read` cap, so an agent told to "read the
   golden model" silently gets a truncated tail.
4. **`studies/ledger/ledger_v94_cells.py` ignores `LEDGER_TARGET=V96`** in `grid` (silently) and `KeyError`s in `matrix`.
5. **The `_v95_*` images are gone from disk** while Ghidra still holds two V95 programs pointing at them.
6. **`sign(gp-0x6752)`** — a ±1 EEPROM constant, not in flash, not readable from existing logs. It
   gates the Path-1 weight family (but **not** V97, where polarity cancels).
