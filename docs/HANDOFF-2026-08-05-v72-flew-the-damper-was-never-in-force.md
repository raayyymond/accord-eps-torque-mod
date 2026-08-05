# HANDOFF 2026-08-05 — V72 FLEW; THE DAMPER WAS NEVER IN FORCE

**Session type:** operator-directed. He supplied the **V72 flight (route `59`)** and asked for root causes
for grind #1 and a newly-reported "micro-ratcheting", whether the two are equivalent, why grind #2 is
resolved, and a V73 that keeps V72's wins without repeating *"every previous fix for grind #1 introduced
grind #2."*

**Fleet:** 9 agents — 5 firmware (GhidraMCP), 4 data, 1 builder.
**Spec:** `docs/V73-DESIGN.md`. **V73 is BUILT, VERIFIED and UNFLASHED.**

---

## ★★★★★ THE HEADLINE — V72's DAMPING LEVERS WERE NEVER IN FORCE, AND IT IS PROVABLE ARITHMETICALLY

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`, where `mode = *(byte)(gp + 0x63fd)`. **13 mode variants exist. V72 edited
modes 10 and 11 only.**

On V72, mode 10/11 carry `FactorC = [430,430,430,877]` (`C >= 430` at every speed — below `X[0]=2240` it
clamps to `Y[0]`) and `FactorE = [927,927,927,927]` (`E = 927` at every rate), so:
```
|gp-0x6bd0| = 1024 * (430/1024) * (927/1024) = 389 MINIMUM, unconditionally
```
⇒ **in mode 10/11, V72's `bit4` (`|gp-0x6bd0| >= 64`) would fire on 100% of frames. It fired on 0 of
87,940, including 0 of 34,275 above 35 km/h.**

> **[EVIDENCE] The car is NOT in mode 10 or 11. Levers B and C were INERT BY TABLE SELECTION — not a
> broken probe, not a vacuous seed, not a missing factor. All three were independently eliminated first.
> The damping approach to the ratchet has NEVER been tested.**

★ **Why it hid for a dozen builds:** the mode comes from `FUN_00057f8e`, a config lookup matching a
5-byte ASCII key at `gp+0x6408..0x640C` against 16 records at `0xCD000`. Row 2 is `'TVAA1'`, and
`39990-TVA-A160` *reads as* `TVA`+`A1` ⇒ index 2 ⇒ modes 10/11. **That mapping is an assumption in
`BUILD-LINEAGE.md`, never a measurement**, and `build_v44_tva.py` has patched modes 10 **and** 11 since
V44 *because of it*.

⚠ **Which mode IS live is unresolved.** Graded against route 59's own telemetry using each mode's exact
trip threshold: **modes 4/5 and 12 are fully consistent** (highway `gp-0x6ac0` peaked at **329.8 counts**
against their 330-335 thresholds — never reached); **modes 0-3 marginally disfavoured** (11 of 34,277
frames exceeded their 270-count threshold, within 100 Hz sampling slop); **10/11 excluded.** V73's probe
settles it.

---

## 1. THE FLIGHT — one fix real, one not, and a naming correction from the operator

| symptom | verdict |
|---|---|
| **creep grind #2** | ✅ **ESTABLISHED.** Routes 58/59 have **identical 691.2 s** exposure, r59 has *more* in every burst-producing cell, **7 bursts vs 0**, exact Poisson **p = 0.0078**; vs V62/V65 **p = 0.00009**; pooled two-lane row **0 in 2,656 s vs 31, p = 6e-5** |
| **highway grind #2** | ❌ **NOT SUPPORTED — struck.** 0 bursts in 253.4 s ⇒ **P(0) = 0.456**; no build has *ever* produced a highway burst. Real result is a **non-regression** (0.448 vs V71C, outside null, at an inaudible 91 counts) |
| **micro ratchet (7.79 Hz)** | ❌ **NOT FIXED. Attenuation factor 1.0**, three independent instruments. Column moves **2.1-2.5x FURTHER** than V71B/V71C |
| **macro ratchet** | ⚠ **fixed per operator, UNMEASURABLE.** Two purpose-built instruments, **64/65 comparisons inside their own nulls — and both FAIL their own positive control** (cannot separate V71B/V71C from V72, the arms he separates). Uninterpretable in **both** directions |
| **grind #1** | ❌ **614 [311, 1187] — the STOCK band.** Consistent with stock **P = 0.985**; excluded HIGHER than V62/V65/V67/V68/V71C at **P < 0.0001** |

🛑 **THE OPERATOR SETTLED THE NAMING: there are TWO ratchets.** **MACRO** = the large-scale symptom he
reports fixed. **MICRO == the 7.79 Hz line.** His *"not audible, only felt in the column"* is exactly
right — **7.7 Hz is below the ~20 Hz hearing threshold.** All three data agents measured MICRO; nobody
measured MACRO, because nobody knew to look separately.

★★ **THE CRUX:** at <= 10 km/h V72's delivered gain is **bit-identical** to V67/V68's (same absolute
5244/512 at every rate index) **and V72 scored stock's grind.** In that dose-matched stratum V72 is
consistent with stock (**P = 0.874**) and excluded higher than V67+V68 (**P < 0.0001**); effort-matching
runs against V72 twice. ⇒ **the creep rate-lane gain is not what separated them.**

---

## 2. ROOT CAUSE — GRIND #1 IS A LIMIT CYCLE

**[EVIDENCE, 8 routes]** decomposing each build's median into duty x in-burst amplitude:
**duty spans 0.015 -> 0.958 (64x); in-burst amplitude spans 1232 -> 1533 (1.24x)** against a **5.62x**
dose ladder. Amplitude is tight within build (CV 0.17-0.26), and `log10 e_18-22` is **two-moded on
exactly the arms that have the cycle, one-moded on the arms that suppress it**, high mode at 1073-1353 on
three independent arms.
> **Successful builds stop the cycle STARTING. None makes it smaller.**

Excess over its own in-window 24-28 Hz control: V61 **12.42** · stock **8.77** · V72 **6.40** · V71C
**4.17** · V62+V65 **2.82** · V67+V68 **2.21**. **Nothing reaches 1.0 on any build.**
⊕ Corroborated from the opposite direction: sweeping `a` (`gp-0x69a4`) 0 -> 32.0 in summed **and**
differential models, **no value makes the ladder monotone** (best |tau| = 0.429). **Not a scalar-gain
phenomenon.**

### The two symptoms share a driver but are DISTINCT MODES
- **Shared:** partial `r(6-9, 18-22 | 24-28)` = **0.460**, circular-shift null [-0.102,+0.023],
  **p = 0.0002**, build-independent. ⚠ The raw correlation would have fooled us — the control band
  tracks nearly as hard.
- **Distinct:** **opposite-signed dependence on steering position** (window-level Spearman **+0.23/+0.32**
  for the ratchet vs **+0.05/+0.06** for grind #1, two pipelines, n = 117/437; ratio of ratios ~2.0-2.3
  for any split 3-20 deg; robust to leaving out any route or block). **Two amplitudes of one oscillation
  cannot do that.**
⇒ **Score BOTH bands on every future build.**

⚠ The angle result is **diagnostic, not a lever** — no firmware structure of adequate magnitude was found
(best candidate `0xC6B64` moves 3.8% over 0-45 deg against a 3.2x effect, and is indexed by tracking
*error*, not absolute position), and **nothing in the corpus separates firmware from plant.**

---

## 3. ⇒ V73 — BUILT, VERIFIED, UNFLASHED

| | |
|---|---|
| image SHA256 | `918a37151876a1a321103fbd7252684d944773109ff454a08a41fe2c191ee63a` |
| rwd SHA256 | `d15e848f86f11245db16822bb06dadde39d5112aa6ce0444d3219aa5dee7c7d5` |
| rwd | `39990-TVA,A160-V73-V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE-…rwd` |

**Verified:** 50/50 CRC PASS · exactly 6 trailers moved · **nothing in `[0xC5000,0xC5FFC)`** · 89
functional bytes, all attributable (cave 61, ratchet 20, friction 6, clamp 2) · V72's levers byte-identical.

- **LEVER A** — the rate lanes, **carried byte-identically.** Owns the one established fix. 🛑 Untouched.
- **LEVER D (grind #1)** — `0xD2A44` Y x1.5 + `0xC407E` 511 -> 850. `gp-0x6b26` is 1 kHz, well-phased
  (**cos -0.63 at 20.9 Hz, -0.96 at 45 Hz**), and **not the rate lane**, so it cannot reopen the grind-#2
  trap. 📋 **FALSIFIABLE: it must suppress 40-49 Hz at least as hard as 18-22 Hz (1.5-2.9x at every
  amplitude tested) and must NOT reproduce V62's regression.** Lineage: **0 of 67 images** — virgin.
- **LEVER E (micro ratchet)** — modes 0,1,2,3,4,5,12,14: `FactorC Y[0] := Y[1]`, `FactorE Y[0] := Y[1]`.
  Largest value keeping the curve **monotone**, and it **preserves rate proportionality**. 🛑 It
  deliberately does **not** flatten the row: **V72 set mode 10's FactorE `Y[0..2] -> 927`, converting a
  rate-proportional damper into a near-BANG-BANG RELAY — a limit-cycle generator. Had Lever B been
  delivered, it could have made the ratchet WORSE.** Not repeated.
- **PROBE** — `bit7` liveness, **`bits 6:3 = mode & 0xF`**. **Read the GATE, not the lane output** —
  the lesson from six uninterpretable nulls (V64/V67/V68/V69/V70/V72).

★ **The cave is the safest this kit has built:** 16 bytes of new payload + **V72's flown 20-byte tail,
byte-identical**, extent unchanged at 68. Three of five payload instructions appear in V72's own flown
cave; the mode read is byte-identical to a real one in stock at `0x346B4`; **the only novel element is an
immediate** (`andi 0x000f` vs V72's `andi 0x0007`).

⚠ **The ratchet dose differs sharply by family: 106 counts for modes 0-3, but only 33 for 4/5 and 31 for
12/14. If the probe reads 4/5 or 12, Lever E is WEAK and V74 must raise it against the live mode.**

---

## 4. SIX REVERSALS UNDER INDEPENDENT CHECKING — two of them the orchestrator's own

1. **"The return-centre relay is a bang-bang limit-cycle driver"** — the mechanism is real but its Y-table
   is `[0,2560,2560,717,0]` over `X=[-397,-192,140,294,384]`, and `gp-0x6bda` runs **~24x** the 384
   threshold hands-off ⇒ **the lane contributes exactly ZERO in the symptom regime.** Closed.
2. **"`X_lo == X_hi == 14`, the sign flips brake<->pump"** — an **off-by-0x1000** tp error (the trap's
   **fifth** recorded occurrence, by an agent who had already hit and fixed it once the same session).
   The orchestrator relayed it to the operator before catching it.
3. **The base damper's phase, THREE times** — 81.8/119.4 deg (built on an EMA later shown inert) ->
   "undetermined, cos spans [-1,+1]" (a broken estimator whose `mean 0, stdev 0.707` is the fingerprint of
   `cos(Uniform(0,2pi))`) -> **cos ~0.5 at 20.9 Hz, ~0.92 at 7.79 Hz**, after the sample rate was
   corrected 312.5 Hz -> **1 kHz** (`andi 0xd30,r25` is a **state mask**, not a phase counter).
4. **"The friction lane is already saturated at the resonance"** — the clamp crossing moved **2.4x** on
   the corrected rate; only the p99 tail clips. The lever survives; the framing did not.
5. **Orchestrator's own: "the ID-string marker breaks the config match"** — refuted. **Nothing parses that
   string into the key**; its only writer is a UDS service taking bytes from a diagnostic payload.
6. **Orchestrator's own: a raw LE displacement scan produced 5 phantom readers** — V850 Format I opcode
   `0b001100` is **SUBR**, colliding byte-for-byte with the `tp+0x718a` displacement. **Confirm every hit
   on an instruction boundary.**

⊕ Also corrected: **V61's lever is not in the gain surface at all** — two register-field edits
(`0x3AB6C e137->e037`, `0x3AC16 0140->0040`) zero the shared `dtorque` tap; V61 is the only image with
them, and its gain records and all five arm cals are byte-stock.

---

## 5. OPEN
1. 🛑 **Which mode is live.** The probe settles it. **If it reads 10/11 we are out of hypotheses** for the
   `bit4` null — seed pinned at 1024 (two derivations + the `.data` boot image at flash `0x86E80`),
   FactorB/D flat unity, no external writer (3 stores, all in `FUN_00034350`), ceiling >= 512 everywhere,
   probe encoding hand-verified.
2. ⚠ **Whether the HW-ID key is ever populated on a running vehicle.** `gp+0x6408` is `.bss`,
   zero-cleared at boot, outside the `.data` restore range; only writer is a UDS service; **no boot-time
   NVM reload found by two agents.** ⚠ But the boot loops use `sst.w` with a **computed `ep`**, invisible
   to all four search methods used — a restore path could exist unfound, and a production ECU would
   normally retain identity in NVM.
3. ⚠ **The macro ratchet is unattributed** and its instruments fail their positive control. ⇒ V73 **adds
   only**; nothing in Levers A/B/C moved.
4. ⚠ **V42's confirmed hard-turn fix vs `gp-0x67fa == 4` never occurring while driving.** Unresolved.

---

## 6. FLIGHT INSTRUCTION
The **mode reads out within seconds of first engagement** — ordinary driving suffices for the probe.
For the levers: **creep with openpilot engaged, wheel working through moderate excursions (25-75 deg p-p),
near and away from centre**, plus **quick low-speed hand-over-hand inputs** to feel Lever D's named cost
(*a momentary extra resistance at the onset of a fast parking-speed input — not a general heaviness*).
⚠ **Score BOTH bands** — 18-22 Hz and 6-9 Hz share a driver.
