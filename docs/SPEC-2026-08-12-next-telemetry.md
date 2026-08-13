# SPEC — LIVE TELEMETRY BUDGET FOR THE NEXT BUILD (2026-08-12)

**Written against the standing operator instruction issued today:**
> *"On every new firmware, be deliberate in thinking about what has already been observed in all prior
> builds (do not hallucinate this, there is a rich history which needs to be reviewed and cited). Then
> after this deliberate thinking, consider what data should be placed in the live telemetry. What data
> insight on live telemetry would provide us the most value at the present moment? Live telemetry is a
> CRUCIAL aspect of every single build."*

**Goal it serves: eliminate all grinding and ratcheting/stuttering.**
**Situation: V97 (`0xC63AC` 102 → 150) is on the car. Route `0x80`, a deliberate parking-lot creep with
LKAS engaged, provoking the grinding and micro-ratcheting. The operator felt ZERO difference and stopped
the drive.**

🛑 This is **SPEC ONLY**. No cave written, no bytes cut, no build proposed for flashing.
🛑 Every claim below is marked **[EVIDENCE]** or **[BELIEF]**. Every EVIDENCE claim names its method.

---

---

# 🛑🛑 RE-ISSUE, 2026-08-12 LATE — READ §R FIRST. IT SUPERSEDES §3.2, §3.11 AND §3.12.

Four things changed after the first draft and two of them are corrections to me:

1. **🛑 MY `≤ 9 %` SHARE BOUND IS WITHDRAWN.** `0x38238 subr r15,r6` (opcode 0x0C) makes the
   coefficient **exactly −1**, and `0xC6468` = 2639 scales **both** arms. `gp-0x6bfe` and
   `gp-0x374c>>4` are **two estimates of the same quantity, in the same units**, entering a
   **difference**. A difference of two correlated estimates is smaller than either, so the denominator
   is the **residual**, not the admitted range. **Comparing one arm's measured ceiling against the
   other's admitted range is unsound and I have struck it everywhere.** The correct statement is:
   **Path-2's share is UNRESOLVED.** ⊕ My own insert 2b is what makes this obvious — having shown these
   are the two arms of one observer residual, I then bounded one against the other's admitted range,
   which the structure forbids. **The conclusion is unaffected and arguably strengthened:
   *"we cannot even bound which arm is bigger"* is a sharper case for the instrument than a bound that
   does not hold.**
2. **🛑 THE OPERATOR OVERRODE THE EXPOSURE PREMISE.** *"the exposure really should not matter… if I
   observe micro-ratcheting or grinding, I am generally going to stop instantly."* ⇒ **my "≥5 min
   engaged" ask is WITHDRAWN.** Design for **~15–30 s of engaged symptomatic frames**. §R4 re-derives
   the requirement and shows **17 s is sufficient for the primary endpoint** — because it is a
   per-frame algebraic read, not a contrast.
3. **🛑 HARD GATE: *"It should not be uninterpretable is what I'm saying."*** "Uninterpretable" is a
   **design failure on our side**, not an outcome. §R5 applies it as pass/fail, bit by bit.
4. **⭐ NEW FIRST-CLASS REQUIREMENT: a BUILD-IDENTITY FIELD.** V97 cannot be separated from V96 by any
   single frame — the images differ by **5 bytes** (`0xC63AC` + its CRC trailer) and every CAN bit map
   is identical. §R6.

**§R below is the shipped spec. §3.2 / §3.11 / §3.12 are retained for provenance and are SUPERSEDED.**

---

## 0. THE ONE-PARAGRAPH VERSION

The decompile of `FUN_00038148` says V97's pole sits on **one of three summands** of the signal that
becomes the PID reference, and the other two bypass it completely. The three are **not independent**: two
of them are estimates of the same quantity entering a **difference** with coefficient exactly −1, both
scaled by the same cal — so **the relative size of the arms cannot be bounded by argument in either
direction, and has never been measured on any build.** That is a sufficient account of *"felt zero
difference"* which requires neither a wrong address nor a dead gate, **and it is unresolvable without an
instrument.** The next build should rank **all three arms of `iVar6` per frame** — with **comparator
rungs, not quantised magnitudes**, because a comparator is immune by construction to the over-range
failure that voided V96. It rides with a free closure of the **`sign(gp-0x6752)`** blocker (a single
4-byte load with 49 Honda twins, and a hard dependency of one of the other rungs), and it needs
**~17 seconds of engaged symptomatic driving** — which is what the operator's own drives deliver.

---

## PART 1 — WHAT LIVE TELEMETRY HAS ALREADY TOLD US

> 🛑 Sourcing rule for this section: every row is cited to a build script, `docs/BUILD-LINEAGE.md`, a
> `docs/HANDOFF-*.md`, `docs/STATE.md`, or a `memory/` file. Where the record does not say, the row
> reads **NOT ESTABLISHED** rather than a guess.

### 1.1 The arc of instrument classes, V53 → V97

| era | class of instrument | citation |
|---|---|---|
| V31P / V31T / V31U | first telemetry at all — gate-firing flags into `0x14A` spare bits; a `0x660` piggyback; UDS DID `0x4801` | `build_v31p_tva.py`, `build_v31t_tva.py`, `build_v31u_uds_telem_tva.py` docstrings |
| V53–V61 | telemetry probes + lane mutes | `build_v96_tva.py` arc summary; `docs/BUILD-LINEAGE.md` |
| V62–V73 | the rate lane (r24/r26) | same |
| V74–V83a | the base-assist damper | same |
| V84–V86B | damper reverts and phase | same |
| V87 | subtractive measurement, `0x14A` byte4 5 rungs + 427 → `gp-0x6b98` | `docs/BUILD-LINEAGE.md` V87 row |
| V88 | Lever B restored + the **sign** bit that made phase measurable | `docs/BUILD-LINEAGE.md` V88 row |
| V89 | the plant model (K1) + `gp-0x6ae2` probe | `docs/BUILD-LINEAGE.md` V89 row |
| V90 | **pure instrument**, cave 62 → 74 B, 5 rungs + 427 → `gp-0x6b26` | `docs/BUILD-LINEAGE.md` V90 row |
| V91/V92 | `0xCBE74` ×1.5 dose + the **first build ever to write `0x14A` byte 7**, cave 74 → 116 B | `docs/BUILD-LINEAGE.md` V92 row |
| V93/V94 | the `0xCBE74` CUT — **aborted on-car** | `docs/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md` |
| V96 | **the first build in the arc to telemeter a TRANSFER rather than a SIGNAL** — both ends of one nonlinearity, so the slope between them is the measurement | `build_v96_tva.py` docstring |
| V97 | V96's cave carried byte-for-byte; one calibration byte | `build_v97_tva.py` docstring, lines 99–101 |

### 1.1b THE PER-BUILD TELEMETRY LEDGER, V53 → V97

> Source discipline: the **instrument** column is read from each `analysis-2020accord/build_v<N>_tva.py`
> module docstring (design intent, verbatim); the **result** column is from `docs/BUILD-LINEAGE.md`,
> `docs/STATE.md`, the handoffs or `memory/`. Where I could not find a measured result I write
> **NOT FOUND IN THE RECORD** rather than guess.

| build | channel + what was instrumented | result | class |
|---|---|---|---|
| **V53** | the **four-frame** cave on new IDs `0x6A0–0x6A3` (not `0x14A`) | 🛑 **0 frames across 301,824** — never transmitted | **CHANNEL-NEVER-TRANSMITTED.** Our own STRB/SSAM defect, not the gateway. ⇒ every later cave uses `0x14A` |
| **V54** | **first `0x14A` byte4[7:3] cave.** `gp-0x6966`, the `FUN_0003a382` authority index. Explicitly reserved *"wire == 0 = THE CAVE DID NOT FIRE — a live probe can never emit 0"* | ✅ **authority is 0 BY DESIGN** — held there by V31's boost floor on every V31+ build | ⭐ **SUCCESS.** Also the origin of the kit's did-not-fire discipline |
| **V55** | DUAL probe, 4 bits on `gp-0x6b98`. Route `24`, **69,607 engaged frames / 943 s** | baseline for everything after | — |
| **V56** | V55's probe **carried unchanged**, + the `0xC6AF0` authority-LERP mute | mute **NULL**; the few-Hz shake is a **tyre** (wheel order 1) | probe fine; the *lever* was the null |
| **V57** | probe **replaced**: `b7` = LIVENESS, `b6` = `(gp-0x6806 == 0)` — the deadband gate | closed a hole in the kit's own elimination; `0xC646C` decoupled onto `0xC6CD0` | ⭐ |
| **V58** | probe replaced: the **angle-rate lane** | *"nothing is buildable with a certified sign"* — the probe measured the two things that would settle it | — |
| **V59** | probe replaced: **boost-index depth** (`gp-0x6ba6`) | the parametric pump is real but **MARGINAL** (eps 0.013–0.169 vs threshold 0.147) | — |
| **V60** | V59's probe **unchanged, deliberately as a CONTROL** (reads `gp-0x6ba6`, upstream of the blend) | `bit5` never toggles once in 61.2 s disengaged | ⭐ the kit's first deliberate probe-as-control |
| **V61** | V59's probe unchanged — 🛑 docstring notes it is **NOT a pure control here** | *"worse — the rate lane IS the damper"* | honest scoping, recorded at cut time |
| **V62** | V59's probe unchanged, secondary readout | ★★★★ **V62 FIXED THE GRINDING** (18–22 Hz down 8–42×) | the lever succeeded; the probe was incidental |
| **V64** | 🛑 probe **still** on `gp-0x6ba6`, which V60 had **already falsified** — the docstring itself calls it *"dead weight"* | **the detector never armed** ⇒ the cal edits were never in force | 🛑 **GATE-NEVER-ARMED**, and a wasted rung on top |
| **V66** | GATE PROBE cave, 4 rungs, 60 of 68 bytes | — | — |
| **V67** | a **different** probe, explicitly *"the V64 lesson applied: probe the gate, not just the output"* | Lever B (LKAS-gated r24 arm) — **best in kit at the time** | ⭐ the rule enters the kit here |
| **V68** | probe re-aimed at `gp-0x67df`, a **second detector stage** (`>= 1`, not V67's `>= 5`) | 🛑 **the detector STILL reads zero** — the cell **has never been non-zero on any build** | 🛑 **NO-POSITIVE-CONTROL** |
| **V69** | probe re-aimed at the **RATCHET** (operator instruction 2026-08-04) | 🛑 **all three rungs failed** | 🛑 **SIZED-AGAINST-THE-WRONG-THING** — rungs sized against a downstream gate's width |
| **V70** | a **REPAIRED** 4-bit SIGN probe: `b6` ratchet size · `b5` the state gate · `b4` r26 sign · `b3` r24 sign. Docstring: *"read bit4 as an AGREEMENT [test]"*, explicitly to avoid *"the uninterpretable-zero class that wasted V64's and V69's probes"* | — 🛑 **no SHAs: V70 was RE-CUT** | ⭐ design improved; ⚠ the re-cut destroyed its predecessor's image |
| **V72** | 5 rungs in 68 bytes | `b5` (`gp-0x67fa == 4`) = **0 / 123,277 frames** (route 54); `b4` (`\|gp-0x6bd0\| ≥ 64`) = **0 / 87,940** | 🛑 **RAILED-DEAD ×2** |
| **V73** | 🛑 **ONE rung, by design** — the damper's **MODE BYTE**, because *"V72 spent five rungs and the decisive one returned an uninterpretable [zero]"* | mode read settled which cal records were live | ⭐ the correct response to V72 |
| **V75** (route `5e`) | MAGNITUDE probe **redesigned**, 68 of 68 B. Docstring: 🛑 *"THIS IS NOT OPTIONAL: V74's PROBE CANNOT DISTINGUISH V75 FROM V74"* | **hard-FAULTED** at t = 284.79 s. The damper-ceiling rung (`\|gp-0x6bd0\| ≥ 448`) read **0 / 28,317** pre-fault frames | ⭐ identity-blindness caught **before** the flight. ✅ **NOT an uninterpretable null** — the 0/28,317 is a real *negative* measurement that **ruled the damper out as the fault cause**. Failure class: N/A (a safety fault, not an instrumentation failure) |
| **V80** (route `66`) | probe **byte-identical to V79/V78**. Docstring: 🛑 *"The probe CANNOT discriminate V80 from V79 below 80 km/h"* | **WORST GRINDING EVER**, no fault. `\|damper\| ≥ 448` engaged **19.4 %** vs V75's 0.000 %; relay index **3.27×** measured directly | ✅ **NOT a null at all — a POSITIVE relay confirmation**, fully interpretable. ⚠ The identity-blindness below 80 km/h is still a real limitation, stated at cut time and flown anyway |
| **V84** (route `6d`) | cave **repointed, no new extent**: `b7` `gp-0x6ada ≥ +1024` · `b6` `≤ −1024` · `b5` `gp-0x67fe ∈ {1,2}` (FactorD liveness — *"if this reads 0, every FactorD number in the kit is void"*) · `b4` `gp-0x6a10 ≥ 8` · `b3` fingerprint | byte4 alphabet exactly `{0x2F, 0x3F}`; the r24 ±1024 rungs `b7`/`b6` read **0 / 68,236**. Operator: **"None of these have been fully fixed"** | ⭐ the two-level ± pair design starts here — but 🛑 **the ±1024 pair is a genuine UNDER-RANGED null**: the rung was set higher than r24 actually delivers |
| **V85** | cave repointed: rate `gp-0x6abc`, friction `gp-0x6ae2` (`b5` `≥ 8`, `b4` `≥ 2` = the liveness anchor) | identity with **no free parameter** (`b3` 1.00000, `b7` 0.39481 vs V84's **0/68,236**); relay saturation delivered | ⭐⭐ **the cleanest flight in the modern lineage** |
| **V86** | `b4` = `gp-0x67ab < 2` — *"the aggregator's optional-term GATE — probe the gate, not just the output"*. 🛑 Docstring states outright: *"THE PROBE CANNOT SCORE `0xC40D4` IN FORCE"* | `0xC40D4` 286 **falsified** | ⭐ a build that names its own instrument's limit in its header |
| **V87** | `0x55DF2` `e893`→`6894`: **427 `MOTOR_TORQUE` ← `gp-0x6b98`**, `sar 3`; + V86B's 62-byte cave verbatim | ✅ **the probe FIRED** — 427 went to 240–297 distinct values; `gp-0x6b98` is **BROADBAND** | ⚠ but **RECTIFIED**, so it could not close its fork |
| **V88** | `0xC4B38` `9094`→`6894` (cave source → `gp-0x6b98`, giving **`b7` = SIGN at 100 Hz**) + `0xC4B46` `a6`→`a8` (rung 64→256 ct) | **the fork CLOSED**: signed ≈ rectified ⇒ V87's null was CORRECT; `\|tq/cmd\|` 6.24 at 7.79 Hz, coh² 0.009→0.343 | ⭐⭐⭐ **the single best telemetry design in the kit** |
| **V89** | `0xC4B38` `6894`→`1e95` (cave source → `gp-0x6ae2` = friction × 1024) + rung `sar 8`→`sar 6` (±64) | H1 PASS (probe fired), **H2 FAIL** — and the probe **explained its own null**: `\|friction\| ≥ 0.0625` on **0.009** of micro-ratchet frames | ⭐ a probe that killed its own build's thesis, correctly |
| **V90** | cave 62 → **74 B**, four independent rungs; `0x55DF2` `6894`→`da94` (**427 ← `gp-0x6b26`**), `sar 3` | `b7` 0.524 · `b6` 0.254 · `b5` 0.675 — all live. 🛑 **`b4` (`gp-0x6c00 < 0`) = 0 / 62,180 — RAILED DEAD** | ⭐ 3 of 4; the 4th is **RAILED-DEAD** |
| **V91/V92** (route `79`) | V92: cave 74 → **116 B**, **SEVEN rungs, the FIRST build ever to write `0x14A` byte 7**; `0x55DF2` `da94`→`4294` (**427 ← `gp-0x6bbe`**), `0x55E10` `a332`→`a432` (`sar 3`→`4`, the no-clip fix) | dose ratio **0.99 [0.91, 1.26]** vs a pre-registered 1.50, duty 0.167/0.161/0.165 vs a needed 0.204. byte7 `b6` (dwell-snap) **0.0000 / 87,317**; return-centre `gp-0x6b62` and detent `gp-0x6bda` both **0.0000 / 75,227** engaged | ⚠ **SPLIT, and the record is precise about it:** the ×1.5 **dose measurement is a real, well-controlled null — NOT uninterpretable** (it is the **CANNOT-MEASURE-ITS-OWN-DOSE** finding, which is itself the result). The **uninterpretable** piece is the companion byte7 dwell-relay rung and the return-centre/detent gates = 🛑 **GATE-NEVER-ARMED** |
| **V93/V94** | 427 source `gp-0x6b26`; V93 `sar 3`, **V94 `sar 1`** | V94 **ABORTED on-car**; the packer byte was **EXONERATED** | the instrument was fine; the calibration was backwards |
| **V96** | cave 116 → **112 B (no growth)**; `0x55DF2` `4294`→`9094` (**427 ← `gp-0x6b70`**), `0x55E10` `a432`→`a632` (`sar 4`→`6`). **The first build in the arc to telemeter a TRANSFER** | ✅ sign bits settled **V97's direction** (`arg(V)−arg(B′)` = −178.1° on both routes). 🛑 the **regressor** was **34× over-range** (M pinned at 0) ⇒ **S1 and S2 both VOID** | ⭐ **and** 🛑 **OVER-RANGED** — one channel decisive, one void |
| **V97** | V96's cave and 427 pointing carried **byte-for-byte**; one calibration byte | route `80`: **17.5 s engaged** (§3.12). `M ≡ 0`, `b3 ≡ 1`, byte7 `b6 ≡ 1` — all as V96 | 🛑 **UNINTERPRETABLE BY EXPOSURE** |

**Answers to the four questions asked:**

- **(a) Who wrote `0x14A` byte 7?** **V92 (first ever), V96, V97 — and nobody else.** Every cave from
  V53/V54 through V91 wrote **byte4[7:3] and nothing else** (`build_v92_tva.py`: *"It is the FIRST build
  ever to write CAN `0x14A` byte 7. Every cave from V53 to V90 wrote byte 4 bits 7:3 and nothing else."*)
- **(b) 427 `MOTOR_TORQUE` repointing, V87 →:** `gp-0x6c18` (stock) → **V87** `gp-0x6b98` (`6894`,
  `sar 3`) → V88/V89 unchanged → **V90/V91** `gp-0x6b26` (`da94`, `sar 3`) → **V92** `gp-0x6bbe`
  (`4294`, `sar 4`) → **V93** `gp-0x6b26`, `sar 3` → **V94** `gp-0x6b26`, **`sar 1`** → **V96/V97**
  `gp-0x6b70` (`9094`, **`sar 6`**). ⚠ `BUILD-LINEAGE`'s V94 row reads *"`a3` → `a1`"*, which is right
  against V90 and **wrong against V92** — `build_v96_tva.py` flags this explicitly.
- **(c) Probed cells that have NEVER read non-zero on any flight** (reconciled against an independent
  V53→V97 survey run this session; where the two disagreed I took the survey's route/frame counts):
  `gp-0x67df`, **Honda's own oscillation-FSM neutral flag — 0 across V64, V67 AND V68, every route**
  (the clearest NO-POSITIVE-CONTROL case in the kit) · `gp-0x671a ≥ 5` and `gp-0x671d ≠ 0`
  (**0 / 14,980**, V64/route `35`, byte4 constant `0x87`) · V72's Lever-B/C in-force bit
  (**0 / 87,940**, incl. **0 / 34,275** above 35 km/h) · `\|gp-0x6bd0\| ≥ 448` (**0 / 28,317**, V75/route
  `5e`) · `gp-0x6c00 < 0` (**0 / 124,362**, V90 — ⚠ my earlier 62,180 was the single-route figure) ·
  the V92 byte7 dwell-relay rung (**0.0000 / 87,317**) · `gp-0x6b62 ≠ 0` and the `gp-0x6bda` gate (both
  **0.0000 / 75,227** engaged) · V84's r24 ±1024 rungs `b7`/`b6` (**0 / 68,236**).
- **(d) The probes that decided something:** **V54** (authority is 0 by design) · **V60** (the first
  deliberate probe-as-control) · **V85** (identity with no free parameter) · **V88** (the sign bit ⇒ a
  transfer function ⇒ the fork closed) · **V89** (the probe explained its own build's null) · **V90**
  (three live rungs + the (b6,b5) 2×2) · **V96** (settled V97's direction).

🛑 **The pattern across 45 builds, and it is the argument for this spec's shape:** *every probe that
decided something was a **sign bit paired with a magnitude channel, or a deliberately-designed control**.
Every uninterpretable null was a **single threshold rung on a quantity with no measured distribution and
no positive control**.*

### 1.2 The probe results that DECIDED something — the kit's telemetry successes

| build | instrument | what it measured | what it settled |
|---|---|---|---|
| **V88** | `0x14A` byte4 `b7` = **sign** of `gp-0x6b98`, at 100 Hz, paired with the 427 magnitude | signed `cmd`↔column: `\|tq/cmd\|` **6.24** at 7.79 Hz, phase **−30.9°**, coherence² **0.009 (rectified) → 0.343 (signed)** | **The sign bit turned a yes/no probe into a transfer-function measurement.** It closed the fork: signed ≈ rectified ⇒ *"rectification was NEVER hiding a line; V87's null was CORRECT"* ⇒ **the ratcheting is NOT a tone the EPS commands** — no notch, no phase lever at 7.79 Hz. Cited: `docs/STATE.md` §2 (V88 block); ⚠ **auto-memory root**: `…/memory/accord-v88-flew-grinding-fixed-command-intact.md` |
| **V88** | same, as an identity check | `b6 == (427 wire ≥ 160)` = **0.9654** vs V87 control **0.4022**, chance 0.6028 | Parameter-free single-build identity — the design every later build copies |
| **V90** | `b7` `gp-0x6b26<0` (duty 0.524) · `b6` `\|gp-0x6bf6\|≥512` (0.254) · `b5` `gp-0x6ae2≠0` (0.675) | duties as listed | Three live rungs, all interpretable. Also produced the **(b6,b5) 2×2 below 1 °/s** = the sixth independent confirmation that the K1 term is Coulomb friction. Cited: `docs/SPEC-2026-08-11-telemetry-budget.md` T2; `docs/STATE.md` §6/§7 |
| **V89** | `gp-0x6ae2` = friction × 1024 | `\|friction\| ≥ 0.0625` on **0.000** of frames below 1 °/s and **0.009** of the micro-ratcheting regime | **The probe explained its own build's null** — arithmetic saying the lever was pointed away from the target. Cited: `docs/BUILD-LINEAGE.md` V89 correction block |
| **V96** | `b7` sign(`gp-0x6b70`) + `b6` sign(`gp-0x374c>>4`), Welch on the full engaged set | `arg(V) − arg(B′)` = **−178.1°** on BOTH routes; `arg(V)` just below −90° | **Settled V97's DIRECTION** — anti-damping seen on a firmware-internal signal for the first time, agreeing with the independent `Q` estimator to <7°. Cited: `build_v97_tva.py` lines 36–50; `docs/STATE.md` §A8 |

⇒ **The single highest-yield design element in the kit's telemetry history is the SIGN BIT paired with a
rectified magnitude channel.** It has produced a decisive result on V88, V90 and V96. Any new allocation
should keep that shape rather than invent a new instrument class.

### 1.3 🛑 THE UNINTERPRETABLE NULLS, BY FAILURE CLASS

These are the rows that matter most, because the next build must not add a seventh instance.

| build | probe | reading | failure class | citation |
|---|---|---|---|---|
| **V64** | the dwell/ratchet detector's own cells | the cal edits were never in force | **GATE-NEVER-ARMED** — *"the null is on the GATE, not the hypothesis"*; the detector never armed | `memory/accord-v64-null-is-on-the-gate.md`; `docs/HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md` |
| **V68** | the detector cell | reads zero | **NO-POSITIVE-CONTROL** — *"the cell has NEVER been non-zero on any build ⇒ its writer and enable gate are OPEN"* | `memory/accord-v68-detector-still-zero-no-positive-control.md` |
| **V69** | three probe rungs | all three failed | **SIZED-AGAINST-THE-WRONG-THING** — rungs sized against a downstream gate's width, not the lane's own reachable output. *"V69 spent all three rungs for nothing."* | `memory/feedback-size-probe-rungs-against-lane-reachable-output.md`; `docs/BUILD-LINEAGE.md` GATE 3 |
| **V69 / V70** | the r24 dose ladder | byte-stock | **WRONG-MODE / RULE 7** — the builds wrote mode-10 `gain_B`; the car is TVCA4 (modes 24/26) ⇒ *"the r24 dose ladder NEVER EXISTED"* | `memory/reference-accord-car-is-tvca4-mode-24-26.md` |
| **V87 (and V90's `b4`)** | `gp-0x6b98` magnitude / `gp-0x6c00<0` | under-ranges to ~1.5 bits / duty **0.000000 railed** | **UNDER-RANGED** and **RAILED-DEAD**. *"a usable SPECTRAL probe, but amplitude claims do NOT travel."* A duty-0 or duty-1 rung carries zero information | `memory/accord-probe-underranges-to-one-bit-comparator.md`; `docs/SPEC-2026-08-11-telemetry-budget.md` T2 |
| **V91 / V92** | 427 ← `gp-0x6b26` as the dose-in-force channel for the `0xCBE74` ×1.5 dose | engaged stratified ratio **0.99 [0.91, 1.26]** against a pre-registered **1.50** | **INSTRUMENT-CANNOT-MEASURE-ITS-OWN-DOSE** — `gp-0x6b26 = K·α` and α is *what K damps*, so in a stable closed loop the **product is invariant to K**. *"Nobody asked whether the instrument could measure the thing it was pointed at."* | `memory/accord-cbe74-dose-measured-inert-wrong-mode-record.md`; `docs/HANDOFF-2026-08-12-v94...` §1.5 |
| **V92 / V93** | — | V93's flight was wasted because **V93's own instrument could not see V93's edit** | same class, restated as a build rule | `build_v96_tva.py` SIZING section |
| **V96** | `0x14A` byte4/byte7 ← `gp-0x374c>>4`, LSB **2048**, saturating at 12288 | magnitude code **M pinned at 0** on 99.90 % / 99.97 % of frames and **100 %** of route 7f's engaged elicitation | **OVER-RANGED, 34×.** *"S1 AND S2 ARE BOTH VOID; `f′` is NOT RESOLVED by this flight."* Next regressor LSB should be **128–256** | `docs/STATE.md` §A5 |
| **all 427 magnitude probes** | rectified `\|x\|` on `0x1AB` at 50 Hz | — | **ALIASED** — a rectified channel folds on `2f` and the law is `\|2f − 50·round(2f/50)\|`, **not** `f mod 25`. 26/29/31 Hz fold to **2/8/12 Hz** ⇒ a rectified 427 magnitude probe exposes **2–12 Hz, not 19–24**, and cannot separate a genuine 2–12 Hz line from a 26–31 Hz image | `memory/reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz.md` |

### 1.4 The channel facts, as they stand (inherited EVIDENCE, re-verified where noted)

| fact | status |
|---|---|
| The CAN TX gateway is a **WHITELIST** — only `0x14A`, `0x18F`, `0x1AB` cross. **A new CAN ID can NEVER reach openpilot.** | `memory/accord-can-tx-gateway-whitelist-and-20-free-bits.md` — inherited, not re-derived here |
| `0x14A` byte4[7:3] = 5 bits @ 100 Hz — in use since ~V53, ~50 flown builds | `docs/SPEC-2026-08-11-telemetry-budget.md` T1 |
| `0x14A` byte7[7:6] = 2 bits @ 100 Hz — **first written by V92**; V96/V97 use both | `docs/BUILD-LINEAGE.md` V92 row; `build_v96_tva.py` |
| `0x1AB`/427 `MOTOR_TORQUE` = 10-bit unsigned magnitude @ **50 Hz** (Nyquist 24.91 Hz), source at `0x55DF2`, scale at `0x55E10` | `build_v96_tva.py`; `docs/HANDOFF-2026-08-12-v94...` §6b |
| `0x18F` has **6 clean spare bits** (byte4[2:0] + byte5[7:6] + byte6[6]) with zero DBC overlap — but **ZERO FLIGHTS**; a second builder hook is a first-flight risk class | `docs/SPEC-2026-08-11-telemetry-budget.md` T1 + ADDENDUM 3 |
| The checksum (`FUN_00057b24`) is the **last** step in every builder ⇒ spare bits are auto-covered | `docs/SPEC-2026-08-11-telemetry-budget.md` T1 |
| CAN-TX base tick **100 Hz** (not 62.5); control task **~1000 Hz** | `memory/accord-can-tx-100hz-base-tick-and-gateway.md`; `memory/control-task-tick-confirmed-1khz.md` |
| The `0x18F`-vs-`0x14A` skew is **~9.15 ms and is a MIXTURE, not a pure delay**: `H(f) = 0.9128·e^{−j2πf·0.01} + 0.0872` | `docs/STATE.md` skew section |
| **`rate_f` (`0x18F`) for PHASE, `rate_c` (`0x14A`) for MAGNITUDE** — getting it wrong INVERTS a build decision | `docs/STATE.md` trap 1 |
| `raw14` off-by-one in **every** cache — safe pairs are `(t, probe)` or `(raw14_t, raw14_b4)`, never crossed | ⚠ **auto-memory root**, not `memory/`: `~/.claude/projects/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/memory/accord-raw14-offbyone-in-every-cache.md` |

### 1.5 🛑 A CONSTRAINT THE PARENT BRIEF GOT SLIGHTLY WRONG, AND IT MATTERS FOR SIZING

> *"Any probe on a fast signal is therefore **aliased** unless it accumulates/peak-holds in the cave."*

**[EVIDENCE] Accumulation and peak-hold are NOT available to this cave.** The cave hangs off the
**100 Hz CAN-TX builder** (`FUN_00055a98` / the hook at `0x55C0E`), not off the 1 kHz control task
(`FUN_0002214a`) — `build_v96_tva.py` GATE 2 (2): *"the cave hangs off the 100 Hz CAN-TX builder, not
the 1 kHz control task."* A peak-hold or accumulator over the 1 kHz signal would require a **second hook
inside the control task**, i.e. a new cave in the code path that bricked V24, V27 and V48B.

⇒ **Every cave bit in this kit is a 100 Hz POINT SAMPLE of a 1 kHz signal, with no anti-alias filter.**
1 kHz content at 92 Hz folds to 8 Hz — straight into the micro-ratchet band. This is irreducible without
a control-task cave and it should be stated in every scoring plan, not designed around. The only real
mitigations are (a) probe signals whose producers are already low-passed, and (b) cross-check every
6–9 Hz claim against the independent 100 Hz `tq` (`0x18F`) and `rate_c` (`0x14A`) channels — which is
what V96's scoring plan already required.

---

## PART 2 — WHAT IS CURRENTLY BLIND, RANKED

Ranked by *"what decision does this unblock, and can only telemetry settle it?"* — in the operator's
regime: **parking-lot creep, LKAS engaged, hands on, deliberately provoking the symptom.**

### 🥇 BLIND SPOT 1 — the three-way decomposition of `iVar6`. THIS IS THE ONE.

**[EVIDENCE]** Method: `decompile_function(0x38148)` on stock `code.bin` (GhidraMCP, fully analysed,
2086 functions), then `disassemble_function(0x38148)` to pin the instructions. Decompile first, then
assembly, and both agree.

```
00038236  sar   0x4,r6      # r6 = gp-0x374c >> 4    <- the SIX-LANE sum, low-passed by 0xC63AC (= V97)
00038238  subr  r15,r6      # r6 = gp-0x6bfe - r6    <- gp-0x6bfe enters UNFILTERED
0003823a  add   r9,r6       # r6 = ... + gp-0x6bfa   <- gp-0x6bfa enters UNFILTERED
```

Mirrored in integer Python exactly as the firmware computes it, each line annotated with its address:

```python
# FUN_00038148, 1 kHz, sole caller FUN_0002214a.  All shifts are integer >>.  V850 is LE.
def stage(gp, tp):
    # --- the six weighted, individually gated lanes -------------------- 0x38148..0x381EC
    s  = (gp.i16(-0x6bd0) * (abs(gp.i16(-0x6bd0)) <= 2048)  * tp.u16(0x73a0)) >> 10  # w0 damping
    s += (gp.i16(-0x6bbe) * (abs(gp.i16(-0x6bbe)) <= 2048)  * tp.u16(0x73a2)) >> 10  # w1 viscous
    s += (gp.i16(-0x6b46) * (abs(gp.i16(-0x6b46)) <= 1024)  * tp.u16(0x73a4)) >> 10  # w2
    s += (gp.i16(-0x6b26) * (abs(gp.i16(-0x6b26)) <= 1024)  * tp.u16(0x73a6)) >> 10  # w3 friction/inertia
    s += (gp.i16(-0x6b4e) * (abs(gp.i16(-0x6b4e)) <= 10240) * tp.u16(0x73a8)) >> 10  # w4  (lane == 0)
    s += (gp.i16(-0x6b4c) * (abs(gp.i16(-0x6b4c)) <= 10240) * tp.u16(0x73aa)) >> 10  # w5 LKAS
    # --- the POLARITY CONSTANT multiplies the WHOLE sum ---------------- 0x381EE / 0x381F6
    s  = s * gp.i8(-0x6752)                       # ld.b -0x6752,gp,r8 ; mul r8,r14,r0
    s  = (s * tp.u16(0x7468)) >> 10               # 0xC6468 = 2639          0x381F2/0x38206
    target = s << 4                               # shl 0x4,r14             0x3820C
    # --- V97's ENTIRE REACH: a one-pole IIR on this ONE summand -------- 0x38202 / 0x38210..0x38230
    A = tp.u16(0x73ac)                            # 0xC63AC  stock 102  ->  V97 150
    gp.acc  += ((target - gp.acc) * A) >> 10       # gp-0x374c
    # --- the THREE-WAY SUM.  Two terms NEVER see A. ------------------- 0x38236..0x3823A
    if not (-20000 <= gp.i16(-0x6bfe) <= 20000):  # bnc 0x382ce           0x3822E/0x38234
        gp.w16(-0x6b70, 0x7fff)                   # movea 0x7fff  <- CLAMP BYPASSED   0x382CE
        return
    iVar6 = ( gp.i16(-0x6bfe)                     #   MODEL   -- unfiltered
            + gp.i16(-0x6bfa)                     #   REQUEST -- unfiltered  (gate is dead, see below)
            - (gp.acc >> 4) )                     #   SIX-LANE SUM -- the only term A touches
    # --- sign x LERP(|.|), then the +-8192 clamp ---------------------- 0x3823C..0x382D2
    y = sign(iVar6) * RAM_LERP(abs(iVar6) * tp.u16(0x73ae) >> 10)   # 0xC63AE = 1024 => index == |iVar6|
    gp.w16(-0x6b70, clamp(y, -tp.u16(0x7200), +tp.u16(0x7200)))     # 0xC6200 = 8192
```

**The three terms and their provenance [EVIDENCE, `search_instructions` + decompile of each writer]:**

| term | writer | access sites image-wide | admitted range | filtered by `0xC63AC`? | ever telemetered? |
|---|---|---|---|---|---|
| `gp-0x6bfe` — the **MODEL** (disturbance-observer output) | `FUN_0003bc20` @`0x3bc3e`, sole writer | **2** (1 reader @`0x38218`, 1 writer) | ±20000, **or exactly 32767** | **NO** | **NEVER, on any build** |
| `gp-0x6bfa` — the **REQUEST** (LKAS side) | `FUN_00026c80` (the 11-slot request aggregator that also writes `gp-0x6b4c` / `gp-0x6b4e` / `gp-0x6b4a`) | **5** (1 reader @`0x38208`, 1 `ld.h` + 3 `st.h` in the writer) | ±20000 (writer clamps) | **NO** | **NEVER, on any build** |
| `gp-0x374c >> 4` — the **SIX-LANE SUM** | `FUN_00038148` itself @`0x38230` | **2**, both inside `FUN_00038148` | measured **< 2048** on ≥99.90 % of frames | **YES — this is all of V97** | V96 only, **34× over-range** |

⚠ **Naming discipline on `gp-0x6bfa`.** What is **EVIDENCE** is its provenance: sole writer
`FUN_00026c80`, the 11-slot request aggregator (`gp-0x6bfa = clamp(Σ gp-0x6324[i], ±20000)`, lockstep
shadow at `gp-0x4cfa`), which is the same function that writes `gp-0x6b4c`, `gp-0x6b4e` and
`gp-0x6b4a`. Calling it *"the LKAS REQUEST term"* is **BELIEF** — a reasonable reading of that
provenance, not a traced physical identity. **The build does not depend on the name; it depends on the
magnitude.**

**⭐ WHERE THIS SITS IN THE CHAIN — and it reframes the whole arc.**
[EVIDENCE] `search_instructions("-0x6bfc")`: **2 sites image-wide.** `gp-0x6bfc` is written **only** by
`FUN_0003b8f6` @`0x3bc1a` and read **only** by `FUN_0003bc20` @`0x3bc20`, which plausibility-gates it
into `gp-0x6bfe`. `FUN_0003b8f6` is the **1 kHz plant-model / disturbance observer** — the function that
holds K0 `0xC4080`, **K1 `0xC40D2`**, the Coulomb-relay gate `0xC40BC`, and the EMAs `0xC40D4` /
`0xC40D6`. This is exactly link 2 of the V89 sign chain already on record
(*"`FUN_0003bc20` plausibility ±20000 → `gp-0x6bfe`"*).

⇒ **`gp-0x6bfe` IS the MODEL side of the observer's residual, and `gp-0x374c>>4` is the ACTUAL side.**
The chain the record calls *"a DISTURBANCE OBSERVER (`residual = MODEL − ACTUAL`)"* is literally this
subtraction at `0x38238`:

```
FUN_0003b8f6  (1 kHz plant model; K0 0xC4080, K1 0xC40D2=204, 0xC40BC=600, 0xC40D4=573, 0xC40D6=246)
      |  gp-0x6bfc
      v
FUN_0003bc20  (plausibility +-20000; else force 0x7fff)
      |  gp-0x6bfe  ------------------- MODEL  ---------+   <-- UNFILTERED.  V89's K1 lives HERE
                                                        |
FUN_00026c80  (11-slot LKAS request aggregator)         |
      |  gp-0x6bfa  ------------------- REQUEST --------+   <-- UNFILTERED
                                                        |
six lanes -> sum6 -> x sign(gp-0x6752) -> x2639 -> <<4  |
      |  IIR pole 0xC63AC  (102 -> 150 = ALL OF V97)    |
      |  gp-0x374c >> 4  ---------------- ACTUAL -------+   <-- the ONLY filtered term, measured < 2048
                                                        |
                                              iVar6 ----+
                                                        v
                        gp-0x6b70 = sign(iVar6) x LERP(|iVar6|), clamp +-8192   [0xC6200]
                                                        v
                        FUN_00037fe6 -> gp-0x6ad6 = the PID REFERENCE
                                                        v
                        FUN_0003a382:  error = measured driver torque - reference
                                                        v
                        PID -> gp-0x6ad4 -> aggregator -> gp-0x6b94 -> governor -> ... -> motor
```

🛑 **V89's K1 (`0xC40D2` 102 → 204, on the car since V89 = 8 builds, measured FLAT) acts on the MODEL
term, unfiltered. V97's pole acts on the ACTUAL term. The two levers sit on OPPOSITE SIDES of the same
subtraction — coefficient exactly −1, both arms scaled by the same cal `0xC6468` = 2639 — and nobody has
ever measured their relative size.** ⚠ **Do NOT bound one arm against the other's admitted range** — see
the withdrawn-bound correction above; the denominator is the residual, not the range.
That is the arc's most consequential unmeasured quantity, and one instrument settles it.
⊕ It also pre-positions the next lever hunt honestly: if the MODEL side dominates, the live cells are
inside `FUN_0003b8f6` — where `0xC40BC` = 6000 measured **2.3× WORSE** (V85), `0xC40D4` = 286 was
**falsified** (V86), K1 measured **FLAT** (V89), and `0xC40D6` is **VIRGIN 92/92** and explicitly frozen
in `build_v97_tva.py`'s `FROZEN` table. A measured share tells you whether that is a live field or a
spent one.

**Why its absence is blocking:**

🛑🛑 **CORRECTION, 2026-08-12 late — MY EARLIER "≤ 9 % SHARE" BOUND IS WITHDRAWN.** An earlier draft of
this section argued that `|gp-0x374c>>4| < 2048` (measured) against two summands *admitted* to ±20000
bounded the ACTUAL arm's share at ≤ ~9 %. **That comparison is unsound and must not be quoted.**

```
0x38238  8f31  subr r15,r6    opcode 0x0C = SUBR  =>  r6 = r15 - r6   coefficient -1 EXACT
0x3823A  c931  add  r9,r6     opcode 0x0E = ADD   =>                  coefficient +1 EXACT
cal 0xC6468 = 2639 (raw 4f0a) -- the SAME cal scales BOTH arms
```
`gp-0x6bfe` and `gp-0x374c>>4` are **two estimates of the same quantity, in the same units, scaled by
the same calibration**, entering a **difference**. A difference of two correlated estimates is **smaller
than either**, so the denominator is the **residual**, not the admitted range — comparing one arm's
measured ceiling against the other's admitted range **systematically understates** the ACTUAL arm's
share. Over the plausible `f′ ∈ [0.1, 10]`, `|resid|` p50 lands in **[32, 3200] ct**, i.e. the Path-2
term is **comparable to or larger than the residual it enters, and is capable of dominating.**

⊕ **My own §"WHERE THIS SITS IN THE CHAIN" is what makes the error obvious** — having shown these are
the two arms of one observer residual, I then bounded one against the other's admitted range, which the
structure forbids.

⇒ **THE CORRECT STATEMENT, AND THE ONLY ONE: Path-2's share is UNRESOLVED. No number is carried in
either direction.** The case for the instrument is **stronger** this way, not weaker: *"we cannot even
bound which arm is bigger"* is a sharper argument than a bound that does not hold. The build is not
*"check whether the class is dead by magnitude"* — it is **"price a lane the code says is well-levered
and that nobody has ever measured."**

- 🛑 This does **not** displace `GhidraLiveness`'s question — a shut `gp-0x67fa` gate would produce the
  same null — but the two are separable on the wire, and neither can be settled by argument.

**What it unblocks:** `0xC63A0`–`0xC63AE` is **seven cells**; six of them (`A2`/`A4`/`A6`/`A8`/`AA`/`AC`)
are **VIRGIN across every image in the kit** (`docs/HANDOFF-2026-08-12-v94...` cross-build matrix, "85 —
VIRGIN"). The whole class is currently blocked because *"a lever whose SIGN is unresolved is not a
lever"* (`docs/STATE.md` §A6b). This measurement answers a prior question — **whether the class is big
enough to be felt at all** — and it answers it in **both** directions:
- six-lane share **large** ⇒ the class is live, and `f′ ≥ 0` (closed structurally, §A10) plus a measured
  share makes a weight lever priceable for the first time;
- six-lane share **small** ⇒ **the entire Path-2 weight/pole class is dead by magnitude**, V97 is
  explained, and the arc pivots off it instead of spending a fifth build there.

### 🥈 BLIND SPOT 2 — `sign(gp-0x6752)`. A standing multi-session blocker that is one 4-byte load away.

The brief calls this *"a ±1 EEPROM constant, not in flash, not readable from any existing log"*
(`docs/HANDOFF-2026-08-12-v97-the-loop-pole.md` §8.6). The first half is right; **the conclusion is not.**

**[EVIDENCE]** `search_instructions(operand_pattern="-0x6752")` on stock `code.bin`: **55 matches,
183,570 instructions scanned, `truncated:false`.** **49 readers across ~40 functions; 6 writers** —
`FUN_00048a40` (`0x48E68`, `0x48E88`), `FUN_000490ac` (`0x490C0`), `FUN_000497e6` (`0x49838`,
`0x49844`). It is a **live RAM signed byte**, not an unreachable EEPROM word, and
`ld.b -0x6752,gp,r6` = `0437ae98` exists as a **whole 4-byte Honda twin at `0x28F22`**.

⊕ And it is not only a Path-1 gate: at `0x381EE`/`0x381F6` it **multiplies the entire Path-2 six-lane
sum**, so it is on the critical path of Blind Spot 1 as well. If it is 0, `gp-0x374c → 0` and V97 is a
guaranteed null.
⚠ [BELIEF] that its magnitude is exactly 1 — the record says ±1 but 6 writers exist and the read is
`ld.b` (sign-extending), so ±2 or 0 are not excluded by structure. The rung must be readable in both
directions (see Part 3, `b3`).

### 🥉 BLIND SPOT 3 — which of the eleven aggregator lanes carries the 6–9 Hz energy in the MICRO regime

`Re(Z) < 0` is replicated on three drives and is **strongest in the micro 1–13 °/s regime** (−3480,
coh² 0.804) — the regime the operator says is unfixed (`memory/accord-rez-antidamping-replicated-three-drives.md`).
And the lanes we keep editing are demonstrably **absent there**:
- the base-assist damper is **exactly zero on 100.0 %** of the micro regime (`docs/STATE.md` §4);
- V89's friction term has `|friction| ≥ 0.0625` on **0.009** of micro-ratcheting frames
  (`docs/BUILD-LINEAGE.md` V89 correction).

**Nobody has ever put the aggregator's lane decomposition on the wire in the micro regime.** The
11-lane table (`docs/SPEC-2026-08-11-telemetry-budget.md` ADDENDUM) ranks r24/r26 and `gp-0x6bbe` as the
unresolved ones — but `gp-0x6bbe` has since been **downgraded** (rate-derived, dead as a lever,
`memory/`… `reference-accord-gp6bbe-is-rate-derived-not-base-assist`), and r24/r26 mirrors
(`gp-0x6ada` / `gp-0x6adc`) are **1 writer / 0 readers = free, zero-blast-radius telemetry**
(`memory/accord-aggregator-lane-mirrors-6ada-6adc.md`).

🛑 **This does not fit the current budget** — a 6-lane decomposition needs more than 7 bits — and it is
a Path-1 question while Blind Spot 1 is a Path-2 question. **Recommendation: this is the build AFTER,
and it is the natural use for the `0x18F` spare bits once a second hook has one clean flight.**

### 4 — PLANT vs FIRMWARE. Evaluated seriously, as instructed, and the verdict is: NOT a telemetry problem.

The brief flags *"hands-off coast still ~0 s ⇒ plant-vs-firmware unrun"* and asks whether it is the
highest-value unrun experiment. **It is high value, and no channel on any whitelisted frame can settle
it**, because every observable is inside a closed loop the firmware is part of. Options, priced:

| option | what it would settle | cost / risk | verdict |
|---|---|---|---|
| **Ignition-off / unpowered hand-turning of the wheel** | Is a 7.8 Hz notchy resonance present with the EPS not driving at all? | **ZERO.** 60 seconds in a driveway. No firmware, no build, no CAN | ⭐ **Run this first.** ⚠ Its limitation is real and must be stated: an unpowered column has far higher friction, which can mask the mode ⇒ **a negative is weak, a positive is strong** |
| **Manual (LKAS off) hands-on creep at matched wheel rate** | Is the mode present with the LKAS lane absent? | ZERO — needs no build, only a drive arm | ✅ Already partly done: engaged/manual is **2.2× on 10 of 10 routes** (`docs/STATE.md` §A2). But base assist still closes a loop ⇒ **partial** |
| **Restore the low-speed lockout `0xC62EA` 0 → 320 (Honda's value)** for one drive | The plant with LKAS authority genuinely killed below ~5 km/h, same car/driver/route, and `STEER_STATUS = 3` marks the arm in the log automatically | One halfword, a **revert to stock**, cal-only, `memory/accord-low-speed-lockout-window-c62ea.md` | ⚠ **Defensible but it removes the operator's elicitation regime**, and it violates the single-purpose rule V96 was built to re-establish. **Not the next build.** Keep as a named option |
| A dither/system-ID injection in the control path | Definitive open-loop plant identification | 🛑 **A 1 kHz control-task cave = the exact class that bricked V24, V27 and V48B** | ❌ **Do not propose.** The information is not worth the bricking class |

⇒ **Verdict: the plant-vs-firmware question should be advanced by a free operator test and a drive arm,
not by a telemetry channel, and certainly not by a cave.** It should not compete for bits on this build.

### 5 — Firmware-driven vs structural resonance. Already answerable from data on disk; costs no bits.

The ratchet is a lightly-damped resonance, **Q 14–29**, ζ 0.017–0.036, motor/rack-side, limit cycle
EXCLUDED. ⚠ **Two memories cover this and they live in DIFFERENT ROOTS with different names** —
`memory/accord-ratchet-is-a-saturated-resonance.md` (the repo: LKAS-gating at p = 1.09e-08, symmetric
waveform ⇒ not stick-slip, **and the "saturated" half re-framed to BELIEF on 2026-08-04**) and
`~/.claude/projects/…/memory/accord-ratchet-is-a-lightly-damped-resonance.md` (auto-memory: the
ring-down ζ). **They are complementary, not contradictory — but an agent that finds one will not find
the other**, and the repo copy explicitly says *"do not quote the saturation model as established."*
The discriminator on the live
channel is: **does `f0` move when a firmware pole moves?** A structural resonance's frequency is set by
inertia and stiffness and is invariant to a loop pole; a firmware-closed-loop mode's is not.

🛑 **V97 IS that experiment and it has already flown.** `0xC63AC` 102 → 150 shifts Path 2's phase by
**+7.82° at 7.79 Hz** (`build_v97_tva.py` line 21). ⇒ **Compare `f0` and the ring-down ζ on route `80`
against routes `7e`/`7f` (V96, same firmware but for the one byte).** If `f0` is unmoved, that is
evidence for structural — and it is an analysis on data already on disk, needing **no new telemetry at
all**. ⊕ Caveat, stated: if Blind Spot 1 resolves the six-lane share as tiny, the phase actually
delivered is a fraction of 7.82° and the test is underpowered — **so the two results must be read
together, and the decomposition must come first.**

### 6 — Clause 2 (the return-to-centre speed). Telemetry cannot manufacture a mechanism.

Three candidates died and *"the field is empty"* (`docs/HANDOFF-2026-08-12-v97-the-loop-pole.md` §8.1).
What telemetry **can** do is narrow it: the operator's own framing is that the LKAS command is a **DC
constant for 52–70 % of the return** while the ring is at full amplitude ⇒ *"the excitation is
SENSOR-FED, and every command-side lever is excluded."* The `iVar6` decomposition **is** a sensor-side
decomposition, measured during hands-off returns, and it says which of the three terms drives the return
trajectory. ⇒ **Blind Spot 1's instrument serves clause 2 as a secondary endpoint at zero extra cost**,
which is one more reason to prefer it. 🛑 It is **not** a mechanism and must not be reported as one.

### 7 — Two free readings nobody had taken, already on the wire — ✅ BOTH NOW EXECUTED AND CLOSED

🛑 **UPDATE: item 1 was run and the answer is ZERO.** `duty(427 == 1023) = 0` on **87,423 frames**
across routes `80`/`7e`/`7f`, and the scoring was **strengthened beyond my flag** — the plausible
ceiling `8192·5>>6 = 640` was derived and `> 640` scored as well: **also zero.**
⇒ **[EVIDENCE] `FUN_0003bc20`'s plausibility latch has NEVER fired on any drive**, including straight
through the operator's own elicitation. `gp-0x6b70` is never written as 32767 and the ±8192 clamp is
never bypassed. **The structural reading below was right; the branch is simply not reachable in
practice.** Kept as a standing check, not as an open question.

1. **🛑 `gp-0x6b70` is NOT always clamped to ±8192.** [EVIDENCE, `disassemble_function(0x38148)`]
   `0x38234 bnc 0x382ce` → `0x382CE movea 0x7fff,r0,r11` → `0x382D2 st.h r11,-0x6b70[gp]`. When
   `|gp-0x6bfe| > 20000`, `gp-0x6b70 = 32767` and the ±8192 clamp at `0x382AC–0x382CC` is **bypassed**.
   `build_v96_tva.py`'s no-clip argument (*"the cell is HARD-CLAMPED to ±8192 by `0xC6200`"*) holds only
   for the plausible branch. ⊕ **This is free and already flying:** on V96/V97's packer
   (`×5 >> 6`, clamp 0..1023), 32767·5>>6 = 2560 ⇒ **a 427 wire reading of exactly 1023 ⟺ the
   observer's plausibility test failed.** Its duty on routes `7e`, `7f` and `80` has never been scored.
   **`TelemetryDecode` can read it off route 80 today, at zero cost.**
2. **The `±20000` gate on `gp-0x6bfa` inside `FUN_00038148` is DEAD.** [EVIDENCE, decompile of
   `FUN_00026c80`] Its sole writer already clamps to exactly `[−20000, +20000]` (stores of `20000` and
   `0xb1e0` = −20000), so `gate(x) = x + 20000u < 0x9c41` can never fail ⇒ `gated(gp-0x6bfa) ≡
   gp-0x6bfa`. Saves cave bytes and removes a term from the model.

---

## PART 3 — THE SPEC (⊕ §3.1 and §3.3–§3.10 are LIVE. 🛑 §3.2, §3.11 and §3.12 are **SUPERSEDED BY §R** — retained for provenance only. Do not build from them.)

### 3.1 Class of build, stated against the whole arc since V38

V38–V52 authority/filters/poles/caves · V53–V61 telemetry + lane mutes · V62–V73 the rate lane ·
V74–V83a the base-assist damper · V84–V86B damper reverts + phase · V87 subtractive · V88 Lever B ·
V89 the plant model · V90 pure instrument · V91/V92 the `0xCBE74` ×1.5 dose · V93/V94 the `0xCBE74`
CUT (**aborted on-car**) · V96 the first TRANSFER probe · **V97 the first LOOP-POLE lever**.

**This build is a POST-MORTEM INSTRUMENT: the first build in the arc to telemeter a SUM'S
DECOMPOSITION.** V53–V94 put single cells on the wire and asked *how big / what sign*. V96 put both ends
of one nonlinearity on the wire and asked *what is the slope between them*. This one puts **all three
addends of one sum** on the wire and asks *which of them is the signal*. Nothing in the kit has done
that.

🛑 **RE-RUN vs NEW, plainly:**
- `gp-0x6bfe` and `gp-0x6bfa` have **never been on any wire on any build** — genuinely new.
- `gp-0x374c` is a **re-run of V96's rung with the LSB corrected 8×**, which is the explicit
  instruction the V96 flight left behind (`docs/STATE.md` §A5: *"Next regressor LSB should be 128–256,
  not 2048"*). It is a re-run **because the previous attempt was over-ranged**, not because the
  question changed — and that is a legitimate reason, stated.
- `gp-0x6752` is new.
- The 427 repoint + rescale is the same CLASS as V87/V88/V90/V92/V94/V96 — a 2-byte source halfword and
  a 1-byte shift, pointed at a cell no build has telemetered.
- **ZERO calibration bytes.** This is not a fix and must not be built as one.

### 3.2 The payload — 🛑🛑 SUPERSEDED BY §R2. PROVENANCE ONLY.
> Why it was superseded, in one line: it repointed 427 to `gp-0x6bfe` (unnecessary — 427 is already the
> best channel in the build and its LERP inversion gives `|resid|` and `f′` for free), it spent bits on
> quantised magnitudes (the failure class §R1 removes), and it carried no build-identity field.

| channel | signal | rate | sizing, against **its own lane's reachable range** | role |
|---|---|---|---|---|
| **`0x1AB`/427** | `clamp(\|gp-0x6bfe\|·5 >> 7, 0, 1023)` | 50 Hz | range ±20000 (writer-enforced) ⇒ `20000·5>>7 = 781 ≤ 1023` **no clip**. LSB = 128/5 = **25.6 ct** = 0.128 % of range, **~9.6 effective bits**. `32767·5>>7 = 1280 → 1023` ⇒ **a rail at 1023 is the plausibility-fail branch**, a free diagnostic | full magnitude of the **never-observed** MODEL term |
| **byte4 `b7`** | `gp-0x6bfe < 0` | 100 Hz | 1 bit | **signed reconstruction** with 427 — the only channel reaching 26–31 Hz for this term (427's Nyquist is 24.91 Hz). The V88/V90/V96 shape |
| **byte4 `b6`** | `\|gp-0x6bfa\| ≥ 512` | 100 Hz | thermometer level 1 | REQUEST-term magnitude, low bracket |
| **byte4 `b5`** | `\|gp-0x6bfa\| ≥ 4096` | 100 Hz | thermometer level 2 | REQUEST-term magnitude, high bracket. Thresholds chosen to **bracket 2048 on both sides**, i.e. the measured bound on the term V97 filters — so the comparison the build exists to make is legible whichever way it falls |
| **byte4 `b4`** | `gp-0x6bfa < 0` | 100 Hz | 1 bit | signed series for the REQUEST term at 100 Hz |
| **byte4 `b3`** | `gp-0x6752 ≥ 0` | 100 Hz | 1 bit | **closes the standing blocker.** Expected CONSTANT for the whole drive |
| **byte7 `b7`** | **hard-wired `1`** | 100 Hz | constant | **LIVENESS / positive control / identity.** `mov 0x1,rN` — a constant, not a signal |
| **byte7 `b6`** | `\|gp-0x374c >> 4\| ≥ 256` | 100 Hz | **re-sized 8× from V96's LSB of 2048**, per `STATE.md` §A5's own instruction | SIX-LANE term — the one V97 filters |

**Bit budget: 7 of 7 used; `0x18F` untouched; one builder hook (`0x14A`'s own, already proven).**

#### 🛑 SIZING HONESTY — I am making the same GATE-3 mistake V96 made, deliberately, and here is the fix

**[EVIDENCE]** Route `0x80`'s 427 channel, read from `_cache_r80/r80.npz` `ab_mt`, 5,375 frames
(⚠ *assuming route 80 is V97, which `ImageVerify` / `TelemetryDecode` are confirming independently*).
V96/V97 point 427 at `|gp-0x6b70|·5 >> 6`, clamp 0..1023:

| statistic | wire code | implied `\|gp-0x6b70\|` |
|---|---|---|
| p50 | 25 | **320** |
| p90 | 198 | 2,534 |
| p99 | 239 | 3,059 |
| **max** | **249** | **3,187** |
| distinct codes | **250** | — |
| duty(wire == 0) | **0.0171** | non-zero ~98.3 % of the time |
| **duty(wire == 1023)** | **0.000000** | — |
| duty(at the ±8192 clamp, wire ≥ 640) | **0.000000** | — |

Three things fall straight out, all new:
1. **The `|gp-0x6bfe| > 20000` plausibility branch NEVER fires on route 80** (duty of the 1023 rail is
   exactly 0 over 5,375 frames) ⇒ **the observer stays in range, and the 32767/clamp-bypass path is NOT
   the explanation for anything on this drive.** A clean negative, available today.
2. **`gp-0x6b70` never approaches its own ±8192 clamp** (max 3,187 = 39 % of it, duty at the rail 0).
   Since the LERP is monotone with **`f′ ≥ 0` enforced in code** (`docs/STATE.md` §A10), the stage is
   operating on the **interior** of its map, not on a rail. The Stage-2 nonlinearity is live.
3. 🛑 **V96's own primary channel is under-used by ~4×.** It was sized against `gp-0x6b70`'s **clamp**
   (`0xC6200` = 8192) rather than against the lane's reachable output — which is precisely what
   `docs/BUILD-LINEAGE.md` **GATE 3** forbids: *"size a rung against the LANE's own reachable output,
   not a downstream gate's width."* A clamp **is** a downstream gate. `sar 4` would have given 4× the
   resolution with no clip (`3187·5>>4 = 996 ≤ 1023`). ⊕ **In fairness this was not avoidable at the
   time** — no distribution for `gp-0x6b70` existed. It is avoidable now.

**⇒ And that indicts MY sizing too, so I am stating it rather than repeating it.** `|gp-0x6bfe|` on 427
at `sar 7` is sized against **±20000, the writer's clamp** — the same class of choice, for the same
reason (no distribution exists for a cell no build has ever telemetered). Two responses:

- **Accepted default:** keep `sar 7`. It cannot clip, the resolution cost is stated (25.6 ct LSB,
  ~9.6 effective bits), and **the flight's own percentiles are a first-class reported output so the next
  build sizes off data instead of off a bound.** That is V96's stated philosophy applied in the safe
  direction, and it is the right call for a *first* observation.
- **⭐ The better fix — DONE, not deferred.** The Stage-2 LERP is **100 % flash-derived**
  (`FUN_000382d8` sole writer → `FUN_000389ec` rescale → `FUN_00038148`) and
  `analysis-2020accord/_v97/read_ram_lerp_provenance.py` already reads it. See §3.2b below: I ran it and
  inverted route 80's measured distribution. The sizing below is now **data-driven, not bound-driven.**

#### 3.2b ⭐ THE SIZING, DONE PROPERLY — the LERP inverted against route 80's own data

**[EVIDENCE] Step 1 — the cave field on route `0x80`, read from `_cache_r80/r80.npz`
(`raw14_b4`, `raw14_b7`):**

| observation | value | meaning |
|---|---|---|
| `byte4[7:3]` takes exactly **4** values | `{1, 9, 17, 25}` = `{00001, 01001, 10001, 11001}` | `b7` and `b6` (the two signs) vary; **`b5 = b4 = 0` always** |
| ⇒ `Mhi` | **≡ 0** on every frame | `\|gp-0x374c>>4\| < 4096` |
| `byte7` range | **64 … 127** (bit 7 never set, bit 6 always set) | ⇒ **`Mlo ≡ 0`**, and the fingerprint holds |
| ⇒ `M = 2·Mhi + Mlo` | **≡ 0 on 100 % of route 80** | 🛑 **`\|gp-0x374c>>4\| < 2048` on EVERY FRAME of the V97 drive** — V96's 7e/7f bound reproduces on V97 |
| `byte4 b3` | **≡ 1** on every frame | ⇒ **`gp-0x674e < 28`. RULE 7 is SETTLED for the authority curve** — the `Y[last] = 0` records are the live ones, and modes 28–39 (`Y[last] = 51`) are excluded. **V96's b3 rung has done its job and is now SPENT** — which is what makes this spec's reallocation of `b3` to `gp-0x6752` safe |

**[EVIDENCE] Step 2 — the LERP's actual knots**, from `_v97/read_ram_lerp_provenance.py` on stock
`code.bin` (anchors verified: `0xC6468` = 2639 ✓, `0xC40BC` = 600 ✓, `tp+0x8b40` = `0xC7B40` ✓).
Mode **26** (ENGAGED), speed breakpoints `[0, 15, 40, 80, 120, 160, 200]` km/h; route 80's engaged
median is **5.13 km/h**, `v_max` **6.6 km/h**, so `rec[0]` (0 km/h) and `rec[1]` (15 km/h) bracket it:

```
mode 26 rec[0]  X = [0, 200, 400, 800, 1200, 1800, 3000, 5000, 12000]
                Y = [0, 471, 880, 1408, 1689, 1953, 2376, 2844,  4114]
mode 26 rec[1]  X = [0, 150, 300, 618, 1200, 1800, 3000, 5000, 10000]
                Y = [0, 429, 788, 1350, 2029, 2358, 2763, 3297,  4625]
```
⚠ `FUN_000389ec` rescales these (`X[i] = (Xsrc[i−1]<<10)/K1`, `Y[i] = (Ysrc[i−1]·K2)>>10`, with
`X[0] = Y[0] = 0` and `Y` capped at `0xC6200` = 8192). **`K1`/`K2` were not identified by me**, so the
inversion below is quoted as a range covering `K1 ∈ {1024, 1159}` and `K2 = 1024`.

**[BELIEF — arithmetic shown, three assumptions flagged] Step 3 — invert route 80's `|gp-0x6b70|`:**

| percentile | measured `\|gp-0x6b70\|` | lands between knots | ⇒ inferred `\|iVar6\|` |
|---|---|---|---|
| p50 | 320 | `Y[1]=0 … Y[2]=471` | **≈ 120 – 140** |
| p90 | 2,534 | `Y[7]=2376 … Y[8]=2844` | **≈ 3,200 – 3,700** |
| max | 3,187 | `Y[8]=2844 … Y[9]=4114` | **≈ 5,000 – 10,000** |

**⇒ WHAT THIS DOES AND DOES NOT LICENSE.**

🛑🛑 **AN EARLIER DRAFT DERIVED A "SHARE CEILING" HERE. IT IS WITHDRAWN — see the correction in Part 2
Blind Spot 1.** `|resid|` is the **difference of two correlated estimates of the same quantity** (`subr`,
coefficient exactly −1, both arms scaled by `0xC6468` = 2639), so **`|gp-0x374c>>4|` may legitimately be
LARGER than the residual it enters.** Bounding the ACTUAL arm against `|resid|` — or against the other
arm's admitted range — is unsound in both directions. **Path-2's share is UNRESOLVED and no number is
carried.**

**What the inversion DOES license, and it is still worth having:**
- `|resid|` p50 ≈ **120–140**, p90 ≈ **3,200–3,700**, max ≈ **5,000–10,000** — the residual's own scale,
  measured on the operator's own drive, **never previously known**. [BELIEF: `K1`/`K2` unidentified; the
  5–6.6 km/h record selection is bracketed, not pinned. `LerpKnots` is resolving both.]
- The operating point is on the **interior** of the LERP, so `f′` is well-defined and non-degenerate
  there, and **`f′` is derivable from the flash table at that point** — which is what makes §R1's
  verdict possible (S1 needs no regression and no bits).
- ⊕ The p50 of ~130 is small in absolute terms, which is **suggestive of strong cancellation between the
  arms** — a live hypothesis the comparator bits in §R2 test directly, and one that a share bound would
  have obscured rather than revealed.

**⇒ Step 4 — and this DECIDES the 427 scale, on physics rather than on a bound.**
The obvious move from Step 3 would be `sar 6` (2× the resolution, no clip up to `|x| = 13,094`, which
covers the inferred `|iVar6|` peak). 🛑 **Reject it.** The LERP inversion bounds `|iVar6|`, **not
`|gp-0x6bfe|`** — and one of the live hypotheses this build exists to test is that **the terms are
individually large and largely CANCEL** (an observer residual is exactly the kind of quantity where
`|MODEL| ≫ |MODEL − ACTUAL|`; the route-80 median `|iVar6| ≈ 130` against a six-lane term admitted to
2048 already hints at cancellation). **A `sar 6` channel would clip precisely when the finding is most
interesting.**

⇒ **`sar 7` stands, and now for a stated physical reason rather than for want of a distribution:
the channel must survive `|gp-0x6bfe| ≫ |iVar6|`.** LSB 25.6 ct, ~9.6 effective bits, no clip anywhere
in the writer's full ±20000 range. **Report the measured percentiles as a first-class output so the
build after this one can tighten it.**

#### 🛑 The one rung that could rail dead, and why it is still worth its bit

byte7 `b6` is a **single** threshold on a signal whose distribution is known only as `< 2048`. A rung
that rails is worthless (V90's `b4`, duty **0.000000**) — so the threshold must be chosen such that
**both rails are decisive**, which is the criterion `SPEC-2026-08-11` set for spending a bit on an
unpredictable duty:

| reading | what it means | actionable? |
|---|---|---|
| **rails at 0** | `\|gp-0x374c>>4\| < 256` throughout, against summands admitted to ±20000 ⇒ six-lane share **< 1.3 %** | ✅ **The whole `FUN_00038148` weight/pole class is DEAD BY MAGNITUDE.** V97 is explained; the arc pivots. A decisive negative |
| mixed duty | inverts to an RMS the same way V90's `b6` (`\|gp-0x6bf6\|≥512`, duty 0.254) was read | ✅ the share is measured |
| **rails at 1** | `256 ≤ \|gp-0x374c>>4\| < 2048` throughout (upper bound from V96) — bracketed to a factor of 8 | ✅ the class is live and the share is bracketed |

⇒ **256 is chosen because a rail at 0 is itself the decisive result**, not because a non-degenerate duty
is expected. State this in the build; do not let a scorer read a 0-rail as a broken probe.

⊕ **And the threshold translates cleanly back to the lanes themselves**, which is what makes it
defensible rather than arbitrary. In steady state `gp-0x374c → target`, so
```
gp-0x374c >> 4  ->  (sum6 * sign(gp-0x6752) * 2639) >> 10   =   sum6 x 2.577
```
⇒ the **measured** bound `|gp-0x374c>>4| < 2048` is exactly **`|sum6| < 795`**, and the proposed
threshold of 256 is **`|sum6| ≈ 99`**. Against six lanes individually gated at ±2048 / ±1024 / ±10240
and all six weights at unity (`0xC63A0..0xC63AA` = 1024, VIRGIN on every image), *the six lanes are
summing to under 795 counts in the operator's own regime* — either individually small or cancelling.
**A split at ~99 counts of `sum6` is right in the middle of that story**, and the duty is the number
that says which of the two it is.

#### VARIANT — leave 427 on `gp-0x6b70` (zero 427 edits) and recover the six-lane term by difference

Considered and **not recommended**, recorded so it is not re-derived. Keeping 427 = `|gp-0x6b70|`
(V96/V97's current pointing, **no `0x55DF2`/`0x55E10` edit at all**) would let the six-lane term be
solved for by inverting the LERP — legitimate now that `f′ ≥ 0` is closed structurally and the table is
**100 % flash-derived** (`docs/STATE.md` §A10). **Rejected because:** (a) `gp-0x6b70` is clamped at
**±8192**, which destroys the information exactly when `iVar6` is large; (b) inverting a saturating
monotone map near its rails is ill-conditioned; (c) it substitutes a **modelling step** for a direct
read, and this kit's expensive errors have consistently come from pricing a lane by arithmetic rather
than measuring the delivered lane (V94, twice, four days apart). ⊕ Its one real advantage — **two fewer
edited bytes** — is not worth a modelled endpoint on a build whose entire purpose is to stop modelling
this stage.

### 3.3 The gate and the input for every probed lane — so a zero is interpretable

The kit's most common wasted build is a probe that reads zero and cannot distinguish *"gate never
armed"* from *"hypothesis wrong"* (V64, V68, V92). Addressed term by term:

| term | its INPUT | its GATE | how a zero is disambiguated |
|---|---|---|---|
| `gp-0x6bfe` | `gp-0x6bfc`, via `FUN_0003bc20` | the ±20000 plausibility test at `0x3822E` | **The gate is directly observable on the wire**: failing it forces `gp-0x6bfe = 32767` ⇒ 427 rails at **exactly 1023**. A 427 zero with 1023-duty zero means the model really is small; a 427 zero with 1023-duty high means the observer is out of plausibility. **Fully separable.** |
| `gp-0x6bfa` | Σ over the 11 request slots of `gp-0x6324[i]`, in `FUN_00026c80` | 🛑 **its `FUN_00038148` gate is DEAD** — the writer already clamps to ±20000 (§Part 2.7) | A zero on `(b6,b5)` means `\|gp-0x6bfa\| < 512` and nothing else. **No gate to confound it.** |
| `gp-0x374c >> 4` | `target = ((sum6 · gp-0x6752 · 2639) >> 10) << 4` | ⚠ **`FUN_00038148` itself is called only when `gp-0x67fa & 0xF ∈ {4,5,11}`** (`0x22672 cmp r0,r28 / be`) | **NOT closed by this build — see 3.4.** |
| `gp-0x6752` | a config/EEPROM shadow written by 3 functions | none — an unconditional `ld.b` | `b3` constant ⇒ read is valid; `b3` varying ⇒ the offset or the staticness assumption is wrong |

### 3.4 🛑 THE ONE GAP, STATED RATHER THAN PAPERED OVER — and a correction to V96's reasoning

`build_v96_tva.py` rejected a `gp-0x67fa` state-gate rung on **buildability**, arguing it would need to
recompute `1 << s` and mask `0x830`, i.e. a **Format IX `shl reg,reg,reg`** — *"the hand-encoding class
that bricked V24/V27/V48B"* — and that the affordable `4 ≤ s ≤ 11` approximation is a **superset**, so
*"a bit that can silently say 'live' while the pair is frozen is worse than no bit."*

**That verdict is right about the approximation and wrong about the necessity of the shift.** You do not
need `1 << s`; you need the **predicate**, and `s ∈ {4,5,11}` over a 4-bit value is exactly **two
unsigned range tests** — `4 ≤ s ≤ 5` and `11 ≤ s ≤ 11` — each of which is V96's own already-proven
`addi -imm,r6,r0` + `bnh` idiom. **No Format IX, no new branch condition, ~16–20 cave bytes, 2 bits.**

⚠ **I am not spending bits on it here**, for two reasons, both stated so the trade is visible:
1. It costs 2 of 7 bits, and the only candidates to drop are `sign(gp-0x6bfa)` and the second
   `gp-0x6bfa` thermometer level — i.e. it would buy a yes/no at the cost of the decomposition this
   build exists to make.
2. **`GhidraLiveness` is settling the same question analytically, this session, for free.** If it comes
   back with *"the gate is open throughout the creep regime"*, the rung is redundant.

🛑 **This build's freeze detector is WEAKER than V96's, and that is a real regression I am not hiding.**
V96's freeze exclusion worked because the gate shutting held **both** members of its pair, so a
common-mode bit-exact hold across two channels was a strong detector. Here, `gp-0x6bfe` and `gp-0x6bfa`
are written **outside** `FUN_00038148` and keep moving when the gate shuts; only byte7 `b6` freezes.
⊕ Mitigating, and it is a genuine improvement in kind: the gate shutting now produces a
**distinctive asymmetric signature** — byte7 `b6` frozen while 427 and byte4 keep moving — rather than a
common-mode hold. **Pre-registered rule: report the duty of `(byte7 b6 constant for ≥ 20 consecutive
frames) AND (427 code changing over the same span)` as a first-class output.** It is a weaker detector
than V96's and it is labelled as one.

### 3.5 Positive controls and validators — what proves the probe itself is alive

V68's cell *"had never been non-zero on any build"*; that must not recur.

| # | check | why it cannot fail silently |
|---|---|---|
| **POS-1** | **byte7 `b7` == 1 on ≥ 99.9 % of frames.** A hard-wired constant (`mov 0x1,rN`), not a measurand | **If this fails, NOTHING in the readout is interpretable and nothing may be reported.** V96's proven pattern — it read 1 on **100.0000 % of 164,096 frames** across routes `7e`/`7f` |
| **POS-2** | 427 non-degenerate: ≥ 20 distinct codes and p99 ≥ 8 | V96's own POS-2, reused unchanged |
| **POS-3** | byte4 `b3` **constant** across the drive | `gp-0x6752` is a config byte; frame-to-frame variation indicts the bit offset or the staticness assumption |
| **VAL-1** | 🛑 **`(b6, b5) = (0, 1)` in byte4 is STRUCTURALLY IMPOSSIBLE** — both read `\|gp-0x6bfa\|` and 4096 > 512 | A genuine never-occurs validator (the class `SPEC-2026-08-11` correctly identified as the real one), not a duty argument |
| **VAL-2** | byte7`[7:6]` ∈ {2, 3} on **every** frame; 0 or 1 proves a byte7 offset error | `b7` is a constant 1 |
| ⚠ **NOT a validator** | byte4 parity. 🛑 **The ~50-build "byte4[7:3] is always ODD" convention DOES NOT HOLD on this build** — `b3` is a measurand now, so byte4 goes EVEN if `gp-0x6752 < 0`, and **that is the finding, not a fault.** Liveness moves from byte4 `b3` to byte7 `b7`. **This must be pre-registered or a scorer will pull a working build** — exactly the failure `SPEC-2026-08-11`'s `(0,0)` correction was written to prevent |

### 3.6 Identity — single-frame, and its residual stated

**Primary: `0x14A` byte7[7:6] == 2 on any single frame.**
- Builds ≤ V91 never write byte 7 at all ⇒ byte7[7:6] ≡ 0. **Excluded.**
- **V96 and V97 — the builds actually on the car** — hard-wire byte7 `b6` ≡ 1 (`build_v96_tva.py`
  IDENTITY; measured **1 on 100.0000 % of 164,096 frames**) ⇒ they can only produce {1, 3}.
  **Excluded, structurally.**
- ⚠ **Residual, stated honestly: V92 also writes byte7 and CAN produce 2** (its `b7` was the
  `|gp-0x6b26| ≥ 15` dose-in-force rung with a predicted duty ~0.24–0.34, `b6` the dwell-snap rung
  measured 0.0000). **V92 is a shelf artefact that is not a flash candidate**, and the flash decision
  names one file, so the residual is bookkeeping, not physics. **Do not claim a structural separation
  from V92.**
- Firing probability: byte7[7:6] == 2 ⟺ `|gp-0x374c>>4| < 256`. V96 measured the same quantity
  **< 2048 essentially always**, and its sign spectrum is coherent at 6–9 Hz ⇒ it crosses zero
  repeatedly ⇒ **P(fires) ≈ 1.0**, but this is a **measured duty, not an impossibility.** Labelled.
- **Secondary, independent:** the 427 source and scale both change (`0x55DF2` → `gp-0x6bfe`,
  `0x55E10` `a632` → `a732`), so the 427 code distribution is a second discriminator.

### 3.7 Aliasing, explicitly

| channel | rate | Nyquist | fold law | what it can and cannot see |
|---|---|---|---|---|
| 427 magnitude **alone** (rectified) | 50 Hz | 24.91 Hz | 🛑 `\|2f − 50·round(2f/50)\|` — rectification folds on **2f** | Exposes **2–12 Hz** and **cannot** separate a genuine 2–12 Hz line from a 26–31 Hz image (`memory/reference-accord-427-is-rectified…`) |
| 427 **+ byte4 `b7` sign** (signed series) | 50 Hz | 24.91 Hz | `\|f − 50k\|` | 26–31 Hz → **19–24 Hz**, outside the scored bands. 🛑 **The sign bit is not optional; without it the channel is unusable for band work** |
| byte4 / byte7 cave bits | 100 Hz | 50 Hz | `\|f − 100k\|` | Reach **6–9 Hz**, **18–22 Hz** and **26–31 Hz** directly — the only channels that do |
| 🛑 all cave bits | — | — | — | **No anti-alias filter exists and none can be built** (§Part 1.5). 1 kHz content at 92 Hz folds to 8 Hz. **Cross-check every 6–9 Hz claim on the independent 100 Hz `tq` (`0x18F`) and `rate_c` (`0x14A`) channels** |

### 3.8 GATE 1 — RAM ownership

**Every new access is a pure LOAD. Zero new RAM. The store set is unchanged from V96's flown cave:
`{gp-0x1514 bits 7:3, gp-0x1511 bits 7:6}`.**

| cell | writer(s) | readers | this build adds | verdict |
|---|---|---|---|---|
| `gp-0x6bfe` | `FUN_0003bc20` @`0x3bc3e`, **sole** | 1 (`FUN_00038148` @`0x38218`) | 1 reader | **2 sites image-wide** — the same profile as `gp-0x374c`, which V96 flew fault-free |
| `gp-0x6bfa` | `FUN_00026c80` (3 `st.h`) | 1 (`FUN_00038148` @`0x38208`) + 1 `ld.h` in the writer | 1 reader | 5 sites image-wide |
| `gp-0x374c` | `FUN_00038148` @`0x38230` | 1 (`FUN_00038148` @`0x381FE`) | 1 reader | Already read by V96's **flown** cave |
| `gp-0x6752` | 6 (`FUN_00048a40` ×2, `FUN_000490ac`, `FUN_000497e6` ×2) | 49 | a 50th reader | Widely-read config byte; one more load is the same class |

🛑 **MANDATORY, and it is the method gap V96 itself found:** a scan keyed on `st.b`/`st.h` whose `hw2`
equals the exact displacement is **structurally blind to a 32-bit access at a different displacement
covering the same byte** (V96 found `ld.w`/`st.w -0x1514[gp]` this way — benign, but invisible to the
narrow method). **Repeat the WIDER scan for all four cells, by GhidraMCP AND an independent whole-image
Python LE byte scan of every store encoding, and set-difference the two.** A count from one tool is not
a count.

### 3.9 GATE 2 — closed-loop stability

**Magnitude and phase, in every loop the signal is in — demonstrated, not asserted.**

1. **ZERO calibration bytes.** Not one. Asserted cell by cell against the base image and by a
   zero-unattributed whole-image diff restricted to `[0x13000, 0x100000)`.
2. **No control signal is modified at all** ⇒ **phase added to every control loop is exactly 0°.**
   🛑 This is *not* the sentence that shipped V94 (*"a scalar on an existing term adds ZERO phase"* —
   true, irrelevant, and about an edit that **did** alter a control signal). Here nothing in the control
   path changes: the cave's stores are `{gp-0x1514, gp-0x1511}` and **no control-path instruction reads
   either byte** — that is the demonstration, and it is read back from the built image's own
   re-disassembly.
3. The cave hangs off the **100 Hz** CAN-TX builder, not the 1 kHz control task. V92 flew 43
   instructions at this site (route 79) and V96 flew 43 at the identical site (routes `7e`/`7f`), all
   fault-free.
4. The two 427 edits change **what a CAN field reports, not what the ECU does**: `0x55DF2` selects which
   cell loads into `r6` for `jarl FUN_00049a5a`; `0x55E10` scales it; the result reaches only
   `FUN_00049a90(v, 0, 0x3ff)` → the `0x1AB` payload. Nothing feeds back. ⊕ Independently established
   on V94, whose packer byte was **exonerated** by an instruction-level walk (`r6` is consumed only by
   the `jarl` two instructions later) and by `steeringTorqueEps` dead-ending in `carstate.py`.
5. Untouched and asserted: `0xC4080` (K0, the NEVER-RAISE relay hazard), `0xC407E` (Honda's 511, the
   hard-fault interlock), the shaper, and all four authority-curve records (`0xE547C` / `0xE5404` /
   `0xE52FC` / `0xE5284`, virgin on all 99 images).
6. 🛑 **`0xC63AC` stays at V97's 150.** This build measures what V97 did; it does not move it.

### 3.10 Cave discipline and size

- Base `0xC4B34`; extent `CAVE_BASE .. CAVE_FREE_END = 0xC4B34 .. 0xC4FF0` = **1212 B free**
  (`build_v96_tva.py`). V96's payload is **112 B / 43 instructions**.
- Estimated new payload: 4 loads (16 B) + 2 abs sequences (12 B) + 1 `sar 0x4` (2 B) + 5 threshold/sign
  rungs (~40 B) + the two existing RMW epilogues (~28 B) ≈ **110–135 B**. That is **0 to +23 B over
  V96**, i.e. up to ~11 % of the extent. **State the exact figure in the build; do not claim NO-GROWTH
  unless it is achieved.** (V90 → V92 already grew 74 → 116 B and flew fault-free.)
- 🛑 **SCRATCH REGISTERS: `r6` and `r7` ONLY**, as V96 (asserted mechanically from the built image's own
  decode). That is enough — every rung is `load → set flags → branch → OR into the accumulator`, and the
  abs is done **in place** (`subr r0,r6` = `8031`, present in V96's own payload). ⚠ Note a `mov` and a
  `ld` do **not** set flags on V850; each abs needs an explicit flag-setter (`cmp r0,r6`) before its
  `bp`. The firmware's own abs at `0x3823C–0x38240` gets its flags from the preceding `add` and is
  therefore **not** a drop-in twin for a standalone abs — twin the two instructions, not the pattern.
- 🛑 **NO NEW BRANCH CONDITION.** All rungs are signs and magnitude thresholds on non-negative values —
  V96's proven `{bge, bnh}` set plus its `addi -imm,r6,r0` + `bnh` unsigned-range idiom. Avoid `be`/`bne`
  and the recorded `ba05`/`b205` inversion hazard.
- **Every non-trivial byte sequence must be copied from a Ghidra-verified twin in the base image**, and
  the built image re-disassembled and each instruction's class re-checked. Twins located this session:

| needed | twin | note |
|---|---|---|
| `ld.h -0x6bfe[gp],r6` | hw2 `0294` whole from `0x38218` (`247f0294`); hw1 `2437` from `0x55DF0` (`2437e893`, a real `ld.h …,gp,r6`) | 🛑 `ld.h` and `ld.w` **share hw1**; only hw2 bit 0 separates them. `0294` has bit 0 clear ⇒ `ld.h`. Twin hw1 from an `ld.h`, never from an `ld.w` |
| `ld.h -0x6bfa[gp],r6` | hw2 `0694` from `0x38208` (`243f0694`); hw1 as above | same rule |
| `ld.b -0x6752[gp],r6` | **whole 4 bytes** `0437ae98` @`0x28F22` | 49 readers exist; pick a whole twin |
| `ld.w -0x374c[gp],r6` | **whole 4 bytes** `2437b5c8` @`0x381FE` | already used by V96 |
| `sar 0x4,r6` | `a432` @`0x38236` | the firmware's **own** `gp-0x374c >> 4` |
| **`sar 0x7,r6`** (the new 427 shift) | **whole 2 bytes `a732` @`0x55C58`** (also `0x558CE`) | `0x55C58` is inside `FUN_00055c42`, **16 bytes from the cave hook** |
| abs | `mov rX,rY / bp +4 / subr r0,rY` @`0x3823C–0x38240` | 🛑 `subr r0,rN` is `8031`. The hand-derived `3080` is **`satsubr`**, which SATURATES instead of negating and corrupts `\|v\|` on negatives only — **a defect that survives a flight** |

### 3.11 Pre-registered scoring plan — 🛑🛑 SUPERSEDED BY §R5 AND §R10. PROVENANCE ONLY.
> Superseded because its SECONDARY and TERTIARY endpoints require exposure the operator will not
> produce, and because it did not write out the sentence each null licenses.

**PRIMARY ENDPOINT — the decomposition. Three numbers, never merged.**
For engaged frames in the creep/override regime, report:
- `D1` = median and p95 of `|gp-0x6bfe|` (from 427, de-rectified with `b7`),
- `D2` = the inverted RMS of `|gp-0x6bfa|` from the `(b6,b5)` thermometer duties,
- `D3` = the inverted RMS of `|gp-0x374c>>4|` from byte7 `b6`'s duty, combined with V96's `< 2048` bound,
and the **share** `D3 / (D1 + D2 + D3)`.
🛑 **Report the three separately as well as the ratio.** A ratio hides which term moved.

**SECONDARY — the same decomposition restricted to 6–9 Hz band power**, i.e. which term carries the
micro-ratchet. Signed series only (427 + `b7` for the model; `b4` + thermometer for the request; byte7
`b6` for the six-lane term).

**TERTIARY — hands-off returns.** The same decomposition during the return trajectory, which is the
operator's own named crux (`docs/HANDOFF-2026-08-12-v97-the-loop-pole.md` §1). 🛑 **Not a mechanism.**

**CONTROLS — run the control BEFORE the measurement** (four 6–9 Hz stories died to their own controls in
one session):
- **NEG-1** band 32–38 Hz, same windows, **SYMMETRIC** wheel-order veto over orders 1–6 on **all** scored
  bands at once — never per-band vetoes, which build different window sets per band.
- **NEG-2** the same estimator on MANUAL hands-on windows matched on wheel rate.
- **NEG-3** shuffled-pairs control on every cross-channel statistic.
- **FLOOR** 🛑 **no ratio below 2× may be claimed in either direction.** Same-firmware placebo spread:
  6–9 Hz **1.37×**, 18–22 **1.31×**, 26–31 **1.99×**, 32–38 control **1.54×** (`docs/STATE.md`).
- **BOOTSTRAP OVER EPISODES, never over windows** (`memory/feedback-episodes-not-windows.md`).

**NULL INTERPRETABILITY BUDGET — decided in advance:**
- `D3` share **large** ⇒ Path 2's weight/pole class is live; V97 was correctly aimed and its dose or
  direction is the question. **Actionable.**
- `D3` share **small** ⇒ **the whole `FUN_00038148` weight/pole class is dead by magnitude**, V97's null
  is explained without invoking a gate, and the arc should stop spending builds there. **Actionable.**
- 427 pinned at **1023** with high duty ⇒ the observer is out of plausibility much of the time, and
  `gp-0x6b70` is being written as 32767 with the ±8192 clamp bypassed. **A new and separate finding.**
- byte4 `b3` reading **0** for the whole drive ⇒ `gp-0x6752 < 0`; the standing blocker is closed and the
  byte4 parity convention is broken **by design**, not by fault.
- 🛑 If POS-1 fails, **nothing is reported.**

### 3.12 🛑🛑 SUPERSEDED BY §R4 AND §R9 — AND THIS SECTION'S CENTRAL ASK WAS WRONG. PROVENANCE ONLY.
> **It asked for 5–17× more engaged driving. The operator has ruled that out** — *"if I observe
> micro-ratcheting or grinding, I am generally going to stop instantly."* The correct response to a
> 17 s budget is to **redesign the endpoint to fit 17 s**, which §R4 does and shows is sufficient.
> The **exposure measurements in this section are correct and are retained**; only the conclusion drawn
> from them is withdrawn.

### 3.12 (retained) WHAT DRIVE THE OPERATOR WOULD NEED, AND HOW MUCH

The record is blunt that **exposure, not analysis, is the binding constraint** — but that verdict was
reached for *symptom contrasts*, and this build's primary endpoint is not one.

**⭐ The primary endpoint is a WITHIN-FRAME decomposition, so it needs FRAMES IN THE REGIME, not matched
episodes.** That is a large and genuine reduction in what is asked of the operator:

### 🛑🛑 FIRST — ROUTE `0x80` IS 17.5 SECONDS OF ENGAGED TIME. MEASURE IT BEFORE REASONING FROM IT.

**[EVIDENCE]** Read directly from `analysis-2020accord/_cache_r80/r80.npz` (10,749 rows, `cc_lat` for
engagement, `cs_v` for speed):

| quantity | route `0x80` |
|---|---|
| total duration | **109.2 s** |
| **engaged** | **1,720 frames = 17.5 s (16.0 %)** |
| engaged **and** below 15 km/h | 1,720 frames = **17.5 s** (all of it — `v_max` is 6.6 km/h) |
| engaged **and** hands-on (`\|tq\| > 1200`) | **336 frames = 3.4 s** |
| median engaged speed | **5.13 km/h** |

🛑 **The operator stopped the drive after 17.5 seconds of engaged exposure.** His *"felt zero
difference"* is a primary symptom report and stands on its own — **but no INSTRUMENT claim of any kind
can be made from route `0x80`.** For scale: the corpus's own placebo floor says no ratio below **2×** is
supportable even on full-length routes; 17.5 s engaged gives roughly **140 effective samples** at the
~8 Hz correlation time, and 3.4 s of override supports on the order of **13** 1.28 s windows.
⇒ **Any agent scoring route `0x80` must report the exposure alongside every number, and a null there is
UNINTERPRETABLE by exposure — a seventh failure class, and the cheapest one to avoid.**

| endpoint | protocol | how much | vs route `0x80` | scoreable? |
|---|---|---|---|---|
| **PRIMARY — the DC decomposition** | **Route `0x80`'s protocol again**: parking-lot creep, LKAS engaged, hands on, deliberately provoking the grinding and micro-ratcheting | **≥ 90–120 s ENGAGED** below ~15 km/h | **5–7×** | ✅ **Yes — one ~10 min parking-lot session** |
| PRIMARY control arm | the same creep with **LKAS disengaged**, hands on, matched wheel rate | ≥ 60 s engaged-equivalent | — | ✅ |
| SECONDARY — the 6–9 Hz share | as PRIMARY, with **sustained deliberate override**. 🛑 Override supports **only 1.28 s onset-triggered windows** — 5013 contiguous runs corpus-wide, median **0.02 s**, p90 **0.55 s**, only **SEVEN** reach 5.12 s. **Point-process / onset-triggered methods, declared before the drive** | **≥ 300 s engaged** with **≥ 60 s of override** | **~17×** engaged, **~18×** override | ⚠ **Needs a deliberate, longer session** |
| TERTIARY — hands-off returns | **matched engaged/disengaged hands-off returns from similar starting angles**, disengage with the **cancel button** — never by grabbing the wheel or braking | 🛑 **≥ 25 episodes per arm.** 11 vs 7 could not resolve a 2.7× effect (fold-width **3.27×**). Config: `analysis-2020accord/_v97/rtc_measure.json` → `config`; scorer `rlog-tools/v97_return_to_centre.py` | ⚠ **Not on a short drive. Do not promise it** |
| **FREE, no build, run it anyway** | **Turn the wheel by hand with the car off.** Is there a notchy ~8 Hz resonance with the EPS not driving? | 60 seconds in a driveway | ⚠ A **positive is strong; a negative is weak** (unpowered friction can mask the mode) |

🛑 **State plainly to the operator: the primary endpoint is scoreable on a short repeat of route 80. The
symptom endpoint is not, and must not be promised.**

---

# §R — THE RE-ISSUED SPEC (SHIPPED). Supersedes §3.2, §3.11, §3.12.

## R0. The design principle, restated after the operator's re-aim

> *"if I observe micro-ratcheting or grinding, I am generally going to stop instantly… it should be very
> clear what the issue is by observing steering angle, driver-side torque, and LKAS demand and other
> telemetry."* · *"It should not be uninterpretable is what I'm saying."*

**⇒ The build is no longer an instrument to SCORE A LEVER across drives. It is an instrument to
DIAGNOSE THE SYMPTOM from ONE short symptomatic episode.** Everything that needs episode counts, matched
arms, or a cross-build ratio is **out**, not demoted.

The record supports this over my earlier framing: **nothing has moved micro-ratcheting or ratcheting in
sixty builds**, and the kit's genuine telemetry successes were nearly all **single-drive, within-episode
reads** — V54, V55, V57, V58→V59, V65, V73. None needed matched episodes or a cross-build contrast.

**The question this build must answer, in one sentence:** *during the ~15–30 s in which the operator can
feel the grinding, which arm of the observer residual is the large one, and does its sign move with the
symptom?* Steering angle, driver torque and the LKAS demand are **already free on `0x18F`/`0x14A`/`0xE4`
and must not be duplicated** — the cave's job is exactly the part those three cannot show.

## R1. 🛑 THE BIT-BUDGET ADJUDICATION — `f′` does NOT need a regression, and S1 is OBSOLETE

**Question put to me:** *"Can S1 — the slope of `gp-0x6b70` on `gp-0x374c>>4` — be recovered from a
1-bit comparator, or does it need genuine magnitude resolution?"*

**Answer: neither. Do not spend bits on S1 at all. Here is the arithmetic.**

**(a) A 1-bit comparator cannot give `f′`'s magnitude, and cannot give its sign either — because the
sign is already known.** Regressing `y` on a binary `b = 1[x ≥ T]`:
```
E[y | b=1] - E[y | b=0]  =  f' * ( E[x | x>=T] - E[x | x<T] )  +  (other terms)
                                  \_______________________/
                                   the conditional-mean GAP of x -- UNOBSERVED
```
The gap is a property of `x`'s distribution, which is exactly what we do not know. **So a 1-bit
regressor yields `f′` only up to an unknown positive scale ⇒ the SIGN, and nothing else.** And
**`f′ ≥ 0` is already ENFORCED IN CODE** at three ungated sites, with flash agreeing 14/14 records
strictly increasing (`docs/STATE.md` §A10). ⇒ **a 1-bit regressor buys literally nothing.**

**(b) But magnitude bits are not the answer either, because `f′` is DERIVABLE from a channel we already
have.** `f′` is a property of a **flash table**, evaluated at the operating point:
```
427  ->  |gp-0x6b70|  --LERP^-1-->  |resid|  --LERP'-->  f'(|resid|)
```
Every step is available: the LERP is **100 % flash-derived** (`FUN_000382d8` → `FUN_000389ec`,
`docs/STATE.md` §A10, and `_v97/read_ram_lerp_provenance.py` already reads it); `0xC63AE` = 1024 so the
index is exactly `|resid|`; and the inversion is well-posed **because the flight measured
`gp-0x6b70` never reaching its clamp** (max 3,187 of ±8,192, rail duty **0.000000**) and `Y` strictly
increasing. ⚠ One real limit: mode-26 `rec[0]` has `Y[0] = Y[1] = 0`, so **near zero the inversion is
degenerate and `|resid|` is not recoverable** — but route 80's median `|gp-0x6b70|` = 320 sits above
that flat region.

**⇒ V96 needed the PAIR only because it believed the LERP was unreadable. That premise was retracted.
S1 is obsolete as a design goal, and the bits it would have cost are freed.**

**(c) What is genuinely NOT derivable is the SPLIT.** `resid` is one number produced by three terms;
no table inverts that. **That — and only that — is what the cave must buy.**

### ⭐ And the way to buy it is a COMPARATOR, not a quantiser

**🛑 The general lesson, and it is the structural fix for V96's failure class:**
> **When you do not know a signal's scale, do not MEASURE it — COMPARE it.** A comparator rung is
> **immune to UNDER-RANGED and OVER-RANGED by construction**: it has no LSB, no ceiling, and no
> assumed distribution. It compares two 32-bit values at full precision **inside the cave**, before any
> quantisation exists.

V96 lost a channel to a 34× over-range guess about `gp-0x374c`'s distribution. **A comparator could not
have failed that way.** This is the first build in the kit to use one, and it is the direct answer to
*"we could not see it."*

### R1b. ⇒ The explicit answer to *"the regressor reads zero magnitude — what would give it leverage?"*

**Nothing needs to, and that is the point.** `Mhi ≡ 0` on all 10,750 route-80 frames means
`|gp-0x374c>>4| < 2048` — but the correct response is **not** a rescale, a different exponent, or a
speed-gated instrument. Those all re-run the same bet: *guess a scale for a distribution you do not
know.* Three reasons the comparator supersedes all of them:

1. **A comparator has no scale.** `b6`/`b5` compare `|gp-0x6bfe|` and `|gp-0x6bfa|` against
   `|gp-0x374c>>4|` **at full 16/32-bit precision inside the cave, before any quantisation exists.**
   `gp-0x374c` being small is then not a problem — it is *the measurement*.
2. **A rescale would still not answer the question asked.** Knowing `|gp-0x374c>>4|` to 128-count
   resolution tells you its size; it does **not** tell you its size *relative to the other two arms*,
   which is the decomposition. The comparator answers that directly.
3. **`f′` — the thing the regressor existed to serve — needs no regressor at all** (R1(b)). So the
   channel's whole purpose is discharged elsewhere.

⊕ **Conditional re-size, if `LerpKnots` returns a collapsed `f′` range.** The tracer is resolving the
Stage-2 knots as a function of the two runtime `FUN_0003897a` factors, and tracing `gp-0x6982`/
`gp-0x6984` to say where they sit at ≤ 6.6 km/h. **If they pin at creep, `f′` collapses and the LERP
inversion of 427 tightens from a bracket to a number** — which sharpens R10's outputs 2 and 3 but
**changes no bit and no byte of this spec.** If they do not pin, the bracket stands and the comparator
bits are unaffected either way. 🛑 **This build must not block on that result**, and it does not.

## R2. THE PAYLOAD

| slot | signal | rate | role |
|---|---|---|---|
| **`0x1AB`/427** | 🛑 **UNCHANGED — `clamp(\|gp-0x6b70\|·5>>6, 0, 1023)`. ZERO 427 edits.** No `0x55DF2`, no `0x55E10` | 50 Hz | `\|resid\|` via LERP⁻¹, and `f′` from the same table. **Measured healthy on this exact firmware**: 250 distinct codes, **0.000 % saturation**, 98.29 % non-zero, p99 3,059 ct against a ±8,192 clamp |
| **byte4 `b7`** | `gp-0x6b70 < 0` — **UNCHANGED from V96/V97** | 100 Hz | **de-rectifies 427.** Mandatory: rectified, 427 folds on `2f` and 26–31 Hz aliases into 2–12 Hz. Zero risk — this exact rung has flown three routes |
| **byte4 `b6`** | ⭐ `\|gp-0x6bfe\| ≥ \|gp-0x374c>>4\|` | 100 Hz | **THE SHARE BIT.** Its duty *is* the fraction of frames on which the MODEL arm exceeds the ACTUAL arm |
| **byte4 `b5`** | ⭐ `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` | 100 Hz | the same for the REQUEST arm. **(b6, b5) ranks all three arms, per frame, with no scale assumption** |
| **byte4 `b4`** | `(gp-0x374c>>4) < 0` — **V96's own b6 rung** | 100 Hz | the ACTUAL arm's sign, so V96's measured +78° vs wheel rate reproduces = the converse positive control (R5) |
| **byte4 `b3`** | `gp-0x6752 ≥ 0` | 100 Hz | 🛑 **makes `b4` interpretable at all** — see R3 — and closes a standing blocker. STATIC |
| **byte7 `[7:6]`** | **hard-wired `10`b = 2** | 100 Hz | **BUILD-IDENTITY + liveness (POS-1).** R6 |

**One builder hook (`0x14A`'s own, proven). ZERO calibration bytes. ZERO 427 bytes. Cave only.**

## R3. 🛑 WHY `b3` IS NOT OPTIONAL — a dependency, not a nicety

`gp-0x6752` is a **signed char that multiplies the entire six-lane sum** at `0x381EE`/`0x381F6`:
```
gp-0x374c  ->  target = ((sum6 * gp-0x6752 * 2639) >> 10) << 4
⇒  sign(gp-0x374c>>4)  =  sign(gp-0x6752) · sign(sum6)
```
**⇒ `b4` measures a product, and without `b3` its physical meaning is ambiguous by a global sign flip.**
That is precisely *"probe the gate and the input, not just the output"*, and it converts `b3` from an
opportunistic rider into a **required companion**. ⊕ It also closes the standing blocker permanently:
`ld.b -0x6752,gp,r6` = `0437ae98` has a **whole 4-byte Honda twin at `0x28F22`** (49 readers exist).
⚠ [BELIEF] that `|gp-0x6752|` = 1 — the record says ±1, but 6 writers exist and the read sign-extends.
`b3` gives the **sign**, which is what `b4` needs; the magnitude stays an assumption and is flagged.

## R4. 🛑 THE ENDPOINT RE-DERIVED FOR A ~17 s DRIVE — the arithmetic, as asked

**The primary endpoint is a per-frame comparator duty. It is not a contrast, so the placebo floor, the
1.28 s onset windows and the episode bootstrap do not bind** — those govern band-power ratios and
cross-build comparisons. Here there is no second arm to compare against.

```
p        = duty of a comparator bit over engaged symptomatic frames
n_eff    = T / tau                      tau = the bit's correlation time
SE(p)    = sqrt( p(1-p) / n_eff )
```

| `tau` | rationale | `n_eff` at **T = 17.2 s** | SE at p = 0.5 | SE at p = 0.9 |
|---|---|---|---|---|
| 0.125 s | the 8 Hz symptom band | **138** | **0.043** | 0.026 |
| 0.5 s | mid | 34 | 0.086 | 0.051 |
| **1.0 s** | **pessimistic** — the LKAS command is 88–95 % inside 0.5–3 Hz | **17** | **0.121** | 0.073 |

**⇒ VERDICT: 17 s IS SUFFICIENT for the primary endpoint.** Even at the pessimistic 1 s correlation
time, a duty of 0.9 / 0.5 / 0.1 is separated by ~3σ. **What 17 s resolves is the ORDERING of the three
arms — which is the endpoint. What it does not resolve is a duty to better than ~±12 %, which is not
the endpoint and is not claimed.** ⊕ 60 s would halve the error; **nothing here needs minutes, and
my earlier "≥5 min" ask was wrong for the reason the operator gave and for this arithmetic too.**

### The endpoints, after cutting

| endpoint | status |
|---|---|
| **PRIMARY — the three-arm ordering** from `(b6, b5)` duties, plus `\|resid\|` and `f′` from 427 | ✅ **scoreable on ~17 s.** This is the build |
| **SECONDARY — the 6–9 Hz band share** from the sign bits' coherence with `\|resid\|` and with column torque | ⚠ **kept only as a bonus, explicitly NOT an acceptance criterion.** At 17 s it is ~13 windows; it may or may not resolve. **Reported with its exposure, never as a verdict** |
| ~~TERTIARY — hands-off returns, ≥25 episodes/arm~~ | ❌ **DROPPED. Unbuildable under how the operator drives.** Not carried, not listed as future work |
| ~~any cross-build band ratio~~ | ❌ **DROPPED.** 60 builds of track record say it does not decide anything |

## R5. 🛑 THE HARD GATE — every bit, and the sentence a null on it licenses

> **If the operator provokes the symptom for ~15–30 s and it is still there, this build's telemetry must
> tell us WHY — it must distinguish "the lever did nothing" from "we could not see it."**

| bit | reading | the sentence it licenses — **written before the drive** |
|---|---|---|
| **byte7[7:6]** | == 2 | *"This build is on the car."* Hard constant. **≠ 2 ⇒ NOTHING is reported.** |
| | ≠ 2 | *"The cave did not run, or the byte7 offset is wrong."* |
| **`b6`** | duty → 1 | *"The MODEL arm exceeds the ACTUAL arm on essentially every frame ⇒ `0xC63AC` and the six lane weights move a minor arm; the Path-2 weight class is weakly levered and the search should move to `FUN_0003b8f6`."* |
| | duty → 0 | *"The ACTUAL arm dominates ⇒ Path-2 is WELL levered, V97 was correctly aimed, and its null is about dose or direction, not reach."* |
| | duty ≈ 0.5 | *"The arms are comparable ⇒ both are live and the residual is a genuine difference of two similar numbers — the cancellation regime."* |
| **`b5`** | any | the same three sentences for the REQUEST arm. **(b6,b5) = (1,1)/(0,0)/(1,0)/(0,1) each name a different ordering; all four are real answers** |
| **`b4`** | varies, 6–9 Hz phase vs wheel rate ≈ **+78°** | ⭐ *"The ACTUAL lane is live and the bit map is right"* — **this is the converse positive control**, and it is only obtainable if the mechanism is real (R5b) |
| | railed | *"The six-lane sum does not change sign during the symptom ⇒ it is a DC bias, not a dynamic participant."* A real finding |
| **`b3`** | ≡ 1 | *"`gp-0x6752 ≥ 0`; `b4` reads `sign(sum6)` directly."* |
| | ≡ 0 | *"`gp-0x6752 < 0`; every `b4` sign flips, and the standing blocker is closed."* **byte4 goes EVEN — by design, see R7** |
| | varies | *"`gp-0x6752` is not static, or the bit offset is wrong."* Indicts the map |
| **427** | non-degenerate | `\|resid\|` and `f′` at the operating point. **Already measured healthy on this firmware** |
| | pinned | *"POS-2 failed; the analogue half is void and the cave half stands."* The two fail independently, on purpose |

**🛑 THERE IS NO COMBINATION OF READINGS THAT LICENSES "UNINTERPRETABLE".** Every bit is either a hard
constant (so its failure is diagnostic), a comparator (whose every duty is a statement about an
ordering), or a rung with a **prior measurement on the same firmware** to check it against. **The gate
passes.**

### R5b. The converse positive control — a reading only possible if the mechanism is real

POS-1 proves the *instrument* is alive. The operator asked for the other direction, and this build has
it: **`b4` is V96's own `b6` rung, unchanged, and V96 measured it at `arg(B′) − arg(rate) = +78.6°` /
`+78.0°` on two independent routes** (`build_v97_tva.py` lines 36–43). **Reproducing +78° ± a sensible
tolerance is a reading that a broken bit map, a wrong offset or a dead lane cannot produce.** It is a
prior-registered, mechanism-specific positive control — the thing V64 and V68 lacked.

## R6. ⭐ THE BUILD-IDENTITY FIELD — treated as first-class, and priced honestly

**The problem, confirmed:** V97 vs V96 is **5 bytes** (`0xC63AC` + its CRC trailer). Cave, 427 repoint,
packer scale and every bit map identical ⇒ **the only thing distinguishing them on the wire is the
physical effect of the lever under test, which is circular.**

**This build: `0x14A` byte7[7:6] = hard-wired `2`.**
- **Cost: ZERO extra cave bytes.** It is V96's existing `mov 0x1,r7` with a different immediate.
- **Single-frame and structural:** builds ≤ V91 mask byte7 off (≡ 0); **V96/V97 hard-wire `b6` ≡ 1** so
  they can only produce {1, 3}. ⇒ **byte7[7:6] == 2 on any single frame proves this build.**
- ⚠ **Residual, stated: V92 can also produce 2.** A shelf artefact, not a flash candidate. **I am not
  claiming a structural separation from V92.**

**🛑 AND THE HONEST ANSWER TO "HOW MANY BITS DOES IT NEED": TWO IS NOT ENOUGH TO BE DURABLE.**
`0x14A` byte7 has 4 codes and **V96/V97 already burn {1,3}**. This scheme gives **exactly one clean
generation**. The next build after this one has only `{1,3}` left, both ambiguous. There is no other
free capacity on `0x14A`: byte4[7:3] is fully spent on measurands.

⇒ **A durable field needs ≥3 bits, and the only places with ≥3 free bits are `0x18F` (6 spare) and
`0x1AB` (3 spare) — both of which need a SECOND BUILDER HOOK, first flight.**

**My recommendation, and it is the one thing I would spend a first-flight hook on:**
> **Pay the `0x18F` hook ONCE, for a 3–4 bit BUILD ID and nothing else.** The hook risk is paid a single
> time; **every future build then gets an identity field for free, forever**, and it can never be
> dropped under budget pressure because it does not compete with measurands. `0x18F`'s 6 spare bits are
> already GATE-1-clean and have zero DBC overlap on either side
> (`docs/SPEC-2026-08-11-telemetry-budget.md` T1), and the hook is structurally identical to `0x14A`'s
> proven one. **The alternative is exactly what just happened: a session that could not tell which of
> two builds was on the car.**
> 🛑 **But do it as its own build, not bolted onto this one.** A first-flight hook and a new measurement
> class in one cut is how V24/V27/V48B happened. **This build ships the 2-bit interim.**

⊕ **A free improvement for the build after next:** once `gp-0x6752`'s sign is known, `b3` is spent and
**frees a byte4 bit permanently.** Combined with `b4` (whose phase V96 already banked), that is 2 bits
recoverable on `0x14A` without any new hook.
⊕ **Not a substitute, recorded so nobody leans on it:** the 427 `sar` immediate has differed per build
(stock 3 · V92 4 · V93 3 · V94 1 · V96/V97 6). That is a *statistical* fingerprint of the wire's scale,
**not a single-frame code.** Weak. Do not rely on it.

## R7. Validators, and the one that will trip a scorer if it is not pre-registered

- **POS-1** byte7[7:6] == 2 on ≥ 99.9 % of frames. **If it fails, nothing is reported.**
- **POS-2** 427 non-degenerate: ≥ 20 distinct codes, p99 ≥ 8. (Measured on route 80: **250 codes,
  p99 = 239.** Passes on this firmware already.)
- **POS-3** `b3` constant across the drive.
- **R5b** `b4`'s 6–9 Hz phase vs wheel rate reproduces V96's **+78°**.
- 🛑 **VAL — THE CONVENTION-BREAK WARNING, AND IT MUST BE PRE-REGISTERED.** The ~50-build
  *"byte4[7:3] is always ODD"* convention **DOES NOT HOLD on this build.** `b3` is a measurand, so
  **byte4 goes EVEN whenever `gp-0x6752 < 0` — and that is the finding, not a fault.** Liveness moved
  to byte7. **Without this pre-registration a scorer sees even values and pulls a working build** —
  the same failure the 2026-08-11 spec's `(0,0)` correction was written to prevent.
- ⚠ **No structural never-occurs pair exists in this allocation.** `(b6, b5)` read *different*
  numerators against a *shared* denominator, so all four codes are reachable and none is a validator.
  **Stated rather than invented** — the 2026-08-11 spec's own lesson about tempting-but-wrong
  validators.

## R8. GATE 1 / GATE 2 / cave discipline — deltas from §3.8–3.10 only

**GATE 1 is UNCHANGED and now smaller**, because 427 is untouched: the store set is still
`{gp-0x1514[7:3], gp-0x1511[7:6]}`, and the new reads are `gp-0x6bfe` (**2 sites image-wide**, 1r/1w),
`gp-0x6bfa` (5 sites), `gp-0x6752` (a 50th reader), `gp-0x374c` (already read by V96's flown cave).
🛑 **The WIDER 32-bit-access scan is still mandatory for all four** — the method gap V96 itself found.

**GATE 2 is STRONGER than §3.9**, because this build changes **fewer bytes than V96 did**: zero
calibration, **zero 427**, cave only. No control signal is modified ⇒ 0° added phase; the cave's stores
are read by no control-path instruction, re-verified from the built image's own re-disassembly.

**🛑 ONE GENUINE BUILDABILITY OPEN ITEM, HANDED OVER RATHER THAN HAND-WAVED.** V96's cave used
**`r6` and `r7` as its only scratch**, and every one of its rungs was **single-operand**. A comparator
is **two-operand**: `b6` and `b5` each need `|gp-0x6bfe|` (or `|gp-0x6bfa|`) and `|gp-0x374c>>4|` live
at once, against an accumulator already occupying one register. Two paths, both priced:

| path | cost | risk |
|---|---|---|
| **Recompute `\|gp-0x374c>>4\|` inside each comparator rung** (load, `sar 0x4`, abs) | **+~10 B per rung, ~+20 B total** ⇒ cave ≈ **125–135 B** vs V96's 112 | **None new.** Keeps V96's proven `r6`/`r7` discipline exactly |
| **Prove a third scratch register dead at the hook** and hold `\|gp-0x374c>>4\|` across both rungs | cave ≈ **105–115 B**, i.e. **no growth over V96** | A new liveness claim at the hook. V96 asserted `r6`/`r7` **mechanically from the built image's decode** — the same method must clear the third, and if it does not, **take path 1** |

**Default to path 1.** ~135 B against **1,212 B free** in the extent. **State the exact figure in the
build; do not claim NO-GROWTH unless it is achieved.**
🛑 **NO NEW BRANCH CONDITION**: signs and unsigned magnitude compares only — V96's proven `{bge, bnh}`
set plus its `addi -imm,r6,r0` + `bnh` idiom. Every non-trivial byte from a Ghidra-verified twin; the
abs is `subr r0,r6` = `8031` (**not** `3080`, which is `satsubr` and corrupts negatives only — a defect
that survives a flight).

## R9. What the operator is asked to do

**One parking-lot creep, LKAS engaged, hands on, exactly as he already drives it — and he should stop
the moment he feels the symptom, as he said he would.**

- **~15–30 s of engaged symptomatic frames is enough** (R4). Route 80 delivered 17.2 s and that
  suffices for the primary endpoint.
- **No matched arms. No episode counts. No second drive. No highway.**
- ⊕ If it is free: a few seconds of the same creep with **LKAS off** strengthens the reading, but the
  primary endpoint **does not depend on it**.
- ⭐ **Separately, and worth 60 seconds of his time with no build at all:** turn the wheel by hand with
  the car off, and say whether the notchy ~8 Hz feel is there. **A positive is strong; a negative is
  weak** (an unpowered column's friction can mask it). It is the cheapest plant-vs-firmware evidence
  available and it needs no firmware.

⊕ **Context he should have when interpreting any behaviour at that speed:** route 80's median engaged
speed is **5.13 km/h**, which sits **right on the knee of `0xC62EA` = 320 ≈ 5 km/h — Honda's low-speed
steer lockout, which this kit has held at 0 since V53/V81.** Anyone attributing behaviour there to a
lever needs to know the stock lockout is disabled underneath them.

## R10. What this build CONCLUDES from ~17 s — written out, as required

1. **The ordering of the three arms of the observer residual**, per frame, with no scale assumption —
   from `(b6, b5)` duties. *Never measured on any build.*
2. **`|resid|` and `f′` at the real operating point** — from 427 through the flash LERP. *This is what
   V96 was built to get and failed to get; it comes free here, from a channel already flying.*
3. **Whether `0xC63AC` (V97) and the six virgin lane weights sit on the major or the minor arm** ⇒
   whether that class is worth another build, or the search moves to `FUN_0003b8f6`.
4. **`sign(gp-0x6752)`** — a standing multi-session blocker, closed permanently.
5. **Whether the ACTUAL arm is a dynamic participant or a DC bias** during the symptom — from `b4`.
6. **Which build is on the car** — single-frame, structural, for the first time since V96.

**None of the six needs a second drive, a matched arm, or a cross-build ratio.**

---

## 4. OPTION B — the `0x18F` hook, priced but NOT recommended for this build

`0x18F` has **6 clean spare bits** (byte4[2:0] + byte5[7:6] + byte6[6]) with zero DBC overlap on either
side, and `opendbc/safety/modes/honda.h` references neither `0x14A` nor `0x18F` at all
(`docs/SPEC-2026-08-11-telemetry-budget.md` T1). With them, this build could carry, additionally:
- the **exact** `gp-0x67fa ∈ {4,5,11}` state gate as two unsigned range tests (§3.4) — 2 bits;
- `sign(gp-0x374c>>4)`, restoring V96's phase channel — 1 bit;
- a second thermometer level on `|gp-0x374c>>4|` — 1 bit;
- `|gp-0x6752|` magnitude, closing the ±1 assumption outright — 2 bits.

**Recommended AGAINST for this build, and the argument is the kit's own:** `0x18F`'s hook is
structurally identical to `0x14A`'s proven one but has **ZERO flights**. A first-time insertion point is
a genuine incremental risk class, not merely more bytes — and it is exactly the class (novel cave/hook
combinations) this kit's **three bricks** came from (V24, V27, V48B). **One hook, fewer bits, all
decisive.** ⊕ If the orchestrator overrules this, the exact state gate is the first thing the new
capacity should buy.

---

## 5. DEFECTS AND CORRECTIONS FOUND WHILE WRITING THIS SPEC — reported, not fixed

1. 🛑 **`build_v96_tva.py`'s 427 no-clip argument is incomplete.** *"The cell is HARD-CLAMPED to ±8192 by
   `0xC6200`, read from the image"* holds only for the plausible branch; `gp-0x6b70 = 32767` when
   `|gp-0x6bfe| > 20000` (`0x38234 bnc 0x382ce` → `0x382CE movea 0x7fff`). The consequence is benign
   (the wire rails at 1023) and is in fact a **free diagnostic nobody has scored**.
2. 🛑 **`docs/HANDOFF-2026-08-12-v97-the-loop-pole.md` §8.6 — `sign(gp-0x6752)` is described as not
   readable.** It is a live RAM byte with 49 readers and 6 writers and a whole 4-byte twin at `0x28F22`.
   The blocker is real for *logs*; it is one rung for a *build*.
3. 🛑 **`build_v96_tva.py`'s rejection of the `gp-0x67fa` rung over-states the buildability problem.**
   The predicate `s ∈ {4,5,11}` needs two unsigned range tests, not a Format IX variable shift.
4. **The `±20000` gate on `gp-0x6bfa` in `FUN_00038148` is dead** — its writer already clamps to exactly
   that range.
5. ⚠ **A live instance of a recorded tool trap, hit by me this session.**
   `search_instructions(mnemonic="sar", operand_pattern="0x7,r6")` returned **0 matches /
   `truncated:false`**. The true count is ≥ 2 (`0x558CE`, `0x55C58`) — Ghidra renders the operand as
   `0x7, r6`, **with a space**. Same class as `STATE.md` §A11's *"a filtered zero is not a fact"*.
   **A zero from `operand_pattern` is never evidence until the rendering has been checked.**
6. ⚠ **Citation-root hazard, checked mechanically while writing this spec.** I verified all 18
   `memory/` files I cite. **Three of them do not exist in the repo's `memory/` at all** —
   `accord-raw14-offbyone-in-every-cache`, `accord-v88-flew-grinding-fixed-command-intact`, and
   `accord-ratchet-is-a-lightly-damped-resonance` live **only in the auto-memory root**
   (`~/.claude/projects/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/memory/`). This is the
   *"four resolve only into the auto-memory directory, which is a separate root"* defect the V94 handoff
   already flagged as OPEN, and it is worse than a broken link: **`memory/MEMORY.md` lists them with
   bare names, so an agent told to "read the memory it points to" gets a file-not-found and moves on.**
   🛑 **Sharper instance: the ratchet has TWO memories under DIFFERENT NAMES in DIFFERENT ROOTS** —
   `memory/accord-ratchet-is-a-saturated-resonance.md` and the auto-memory
   `accord-ratchet-is-a-lightly-damped-resonance.md`. They are complementary, but the repo copy carries
   a **2026-08-04 re-framing that downgrades the "saturated" claim to BELIEF** and says *"do not quote
   the saturation model as established"* — a correction an agent reading only the auto-memory copy will
   never see. Same failure mode as the recorded `accord-factord-is-the-angle-error-lever` incident,
   where a stale auto-memory copy *"sent a subagent down a dead thread."*
   ⇒ **When a `reference_*` fact is corrected, correct BOTH copies** — the rule is already on record and
   it is still being violated.
7. ⚠ **Not verified by me, flagged for the record**: `docs/SPEC-2026-08-11-telemetry-budget.md` ADDENDUM
   ranks `gp-0x6bbe` as the top anti-damping candidate and allocates 427 + a sign bit to it. That was
   **superseded on 2026-08-12** — `gp-0x6bbe` is rate-derived and dead as a lever
   (`docs/STATE.md` §A4). Anyone reading that spec fresh will re-propose a dead lever.

---

## 6. WHAT THIS SPEC DELIBERATELY DOES NOT DO

- It proposes **no calibration change**. Not one byte. V97 stays on the car and stays at 150.
- It does **not** claim V97 is dead. It claims V97's reach is **bounded and unmeasured**, and it
  measures it.
- It does **not** claim to address the return-to-centre **speed**. Clause 2 has no mechanism
  (`docs/STATE.md` §A9); nothing here changes that.
- It does **not** re-open `0xC63A6` or any `FUN_00038148` weight. *"A lever whose sign is unresolved is
  not a lever. That is exactly how V94 reached the car."*
- It does **not** call anything fixed. **The operator scores symptoms; this instrument scores bands and
  magnitudes, and those are different objects.**
