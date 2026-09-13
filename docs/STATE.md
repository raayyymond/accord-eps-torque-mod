# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Everything you need to make a decision is in this box. The superseded decision
> boxes and the 84 finding/correction blocks that used to follow it are ARCHIVED under `docs/archive/` (pointers
> at the end of this file). They are a record, not a briefing; nothing was retracted by the moves.

## ✈ THE DECISION, IN ONE PLACE — updated 2026-09-13 late (**V292 FLEW AND IS A REVERT. V293 — TORQUE MODE — IS BUILT AND CLEARED AS THE FLIGHT CANDIDATE OVER ONE DISSENT. Nothing flashed, nothing sent.**)

**ON THE CAR: V292** — routes `75604b0a432fdc89_0000006d--5e7b4d2ceb`, `…6e--64b4a5fef4`,
`…6f--d876c761bc` (2026-09-13, 54 segments, 1,723 s engaged-lateral), attributed **from the tap, not the
label**: `0x14A` b3 tracks `sign(0x18F rate)` at lag **+1 frame** (split 0.642–0.764) against four
reference builds flat at every lag. 🛑 **The dongle counter was RESET — these are NOT August's r6d/r6e/r6f.**
🛑 **V292 IS A REVERT BY ITS OWN PRE-REGISTRATION. THE FALLBACK IS V282** (rwd sha256 `618365154e3f…`),
which is what the operator should be on unless he chooses to fly V293.
**BUILT, NOT FLOWN, 🛑 CLEARED AS THE FLIGHT CANDIDATE OVER ONE DISSENT: V293** — torque mode, cal-only
on V282. **image**
`f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17` · **rwd**
`ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba`
(`…-V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-…rwd`, **exactly one on
disk**; both hashes re-verified from the files at close-out, and **378 diff bytes over 6 CRC blocks**
re-derived independently from the two images — 1 fb clamp + 1 D clamp + 2 r24 + 112 Kd knots + 240 Kp
knots = 356 payload, + 22 trailer). **242 assertions** (census 64 substantive / 172 vacuous / 6 tautological, post-`scriptfix`),
**16/16 mutations caught**, and the build-audit adversary's independent rebuild lands on the same two
hashes. **378 diff bytes, and ZERO of them below `0xC0000`** — the cal-only claim is a byte fact, not a
docstring claim.

> 🛑 **THE VERDICT: V293 is CLEARED as the flight candidate over ONE DISSENT (B2 as written), with V282
> the fallback, the fork preset (`AccordEpsTorqueMode` ON: LAF 6.0 / friction 0.00 / Kp 0.3 / Ki 0.15,
> rate-plant FF OFF) MANDATORY, the first drive an IDENTIFICATION drive, and the low-speed 1–4 Hz
> signature the first revert trigger. The decision to fly is the operator's. Nothing licenses any claim
> that the grinding or the stutter is fixed — he scores the symptom; the pre-registered read and the
> terminal null sentence stand.**

**Page:** https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565 (v2 — the A/C/D1 verdicts,
the taper split, and the authority callout).

**THE PASS, COMPLETE — `advA3` PASS (A1–A4) · `advC3` PASS (C1–C5) · `advD3` PASS (D1–D5) · `advB3`/`advB3b`:
B1, B3, B4, B5, B7 PASS, B8 reported, and 🛑 TWO CLAUSES FAIL AS WRITTEN (B2, B6), BOTH ADJUDICATED.**
Full table and reasoning: `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`.

- **A — ARITHMETIC PASS.** Clamp block simulated from its own decoded bytes over **4,023 int32 states: 0
  non-zero operands** (V282 at 46080: **4,012** — the null is capable); **D ≡ 0 by EACH cell alone**; Ki 0;
  `0x2A0C6` unreachable by three methods incl. **zero LE32 hits of `0xFEDF17F6`**; **rail 2461 = 2461** on
  matched cold-start trajectories, **P first rails at idx 239**, linear fit **10.336·idx − 1.89** (2.19-count
  max residual, accounted for by the map lerp plus three floors); all 28 Kp = [120]×5, all 28 Kd = [0]×4;
  **code region `[0x13000, 0xC0000)` byte-identical** ✔ (378 diff bytes, lowest `0xC61B7`).
- 🛑🛑 **A's CARRIED FINDING — NOT GATED, AND IT GOVERNS THE LANGUAGE: V293's sub-rail slope is 10.34
  counts/idx against V282's 21.35 at fb = 0.** Below idx 116 V293 delivers **0.47–0.49 of V282's
  STALLED-WHEEL torque** (idx 58: **598 vs 1236**), meeting it only at idx 239–240 — *"the peak is identical
  and needs twice the demand to reach."* ⇒ 🛑 **NEVER WRITE "AUTHORITY UNCHANGED" ABOUT V293, AND NEVER SHOW
  ONLY THE RAIL.** ⚠ Against a *moving* wheel V282 delivers less and can go negative while V293 holds, so
  the deficit is the **stalled** regime only; openpilot's LAF identification absorbs the slope (actuator
  fraction ~12 % → ~24 %), which is why the first drive identifies before it tunes.
- **B1 PASS at 2048** — unstable fits in torque mode, V282-pole-only family: **5244 → 7/2** (κ 0.45/1.45),
  **4451 → 5/0**, **2048 → 0/0**; both-poles family at κ 0.45 (n = 12, control matches) **0 unstable at every
  arm**, worst-plant ζ **+0.161** vs V282's **−0.005**. ⚠ The literal `ζ < 0.05` clause **condemns flown V282
  on 250/250 and 12/12 — broken**, scored as *"no unstable fit and no worse than V282"*; **the both-poles
  family at κ 1.45 is EMPTY, so the κ dispute is sidestepped at one end, not settled.**
  ⭐ **HAD 4451 BEEN BUILT, B1 WOULD HAVE FAILED.**
- **B3 PASS** — rail **×1.000000**, P rails at idx 239, slope **0.641212** counts per CAN count.
- **B4 PASS, and it is the THINNEST margin in the pass.** Ripple/level on loaded turns **0.028 / 0.034 /
  0.048** against the 0.25 gate (V282 0.019 / 0.013 / 0.099; **stock 0.044 / 0.033 / 0.087 — V293 sits
  between the two**); predicted F7 **≈ 1.24 /100 s** against 2, a margin of only **×1.6** through a
  nonlinear mapping.
- **B5 PASS at 2048** — 5–9 Hz **×1.59 / 1.50 / 1.53 vs V282** and **×1.13 / 1.07 / 1.05 vs STOCK** (the
  stock leg run at **both** readings of its r24 arm); **neither leg trips**, where **4451 trips leg 1 on
  r39 (1.654)**. ⭐ **The rise is BROADBAND — peakiness unchanged**, structurally unlike V292's resonant
  7 Hz re-arm.
- **B7 PASS** — **0 of 250** plants with ζ < 0.10 in 10–18 Hz; 13–17 Hz **×1.058** max vs V282 against a
  ×1.5 gate (V292's rejected number was ×1.9–2.1).
- **B8 reported** — the command-driven 18–22 Hz torque is **×0.055–0.137 of V282's ring and has no pole:
  it cannot ring.**
- 🛑 **B6 FAIL AS WRITTEN AT THE MEASURED τ — and it is a BROKEN CHECK that fires cleanly.** At each speed's
  own measured τ, V293 at the **repaired** preset (friction 0.00) breaks **3 of 10** controller-loop cells
  (worst **PM 33.2°**, k30 1.09, kU 1.80 at 5 m/s / τ 0.25) — and **V282 at the tune it is actually flown
  with breaks 3 of 10 too** (worst **PM 35.6°**, k30 1.12, kU 1.74 at 28.5 m/s / τ 0.22). On the
  path-following channel **both** go unstable inside [0.5×, 2×] (kU 1.31 vs 1.27). The friction repair is
  worth **×1.58 on k30**. ⇒ **Scored on its INTENT — V293's outer loop no worse than the build on the car —
  B6 PASSES.** ⚠ **Residual, named not closed: the creep margin at 5 m/s is only ~10–20 % of plant gain on
  BOTH builds, and the failure mode there is the V276 1–4 Hz signature. That is the FIRST THING TO WATCH,
  at low speed.**
- 🛑 **B2 FAIL AS WRITTEN — ADJUDICATED PASS ON INTENT, AND THE DISSENT STANDS.** Uncalibrated ring
  **×0.285** (r39) / **×0.403** (r6c); the mandated V292 calibration (**×1.90–3.64**) ⇒ **×0.54–1.04 /
  ×0.77–1.47** against the ≤ ×0.50 gate; the open-loop calibration (×1.64) ⇒ 0.47 / 0.66; **the on-car
  anchor, no predictor, re-derived independently: ×0.237 / ×0.285 / ×0.265.**
  **Why it was adjudicated rather than left to the broken-check rule:** B2 does **not** condemn a flown
  build, so that rule does not reach it. The calibration factor was measured on **V292, a build that did
  NOT open the loop** — the fit family's error there is in how a feedback pole reshapes the return ratio at
  20 Hz, **an error that has no channel when the operand is identically zero** (`|S| ≡ 1` is an identity the
  code region's bytes prove, not a fit). Transferred to the one fully-open-loop configuration the car has
  been measured in, **that calibration over-predicts the measured ring by ×1.3–2.0 — the calibrated
  predictor fails a measured case.** On the clause's intent (the ring at least halved) the direct on-car
  measurement reads ×0.24–0.29 and the command-driven residual ×0.06–0.14, **both EVIDENCE rather than
  model.** 🛑 **The V292 precedent is stated, not hidden: V292 was also cleared over one dissent and then
  failed on the wire on clauses the model had passed — which is exactly why this candidate's ring claim
  rests on the car's own open-loop measurement and NOT on the replay.**
- **C — BUILD AUDIT PASS.** Independent rebuild from the V282 image plus the prereg edit list, **hashes
  PREDICTED BEFORE THE WRITE**, reproduced byte for byte; 378 bytes / **0 unattributed / 0 below
  `0xC0000`**; round-trip byte-equal, 50/50 CRCs by two routines; the write guard refuses before touching
  the filesystem. **Five defects in the script's self-verification and prose, NONE in the artifact** — the
  census overstated by 23; **seven single-knot mutations (one Kp knot at 121, one Kd knot at 1) pass all
  241 assertions** because the byte counter cannot see a wrong *level* and the rail check samples only
  Y[−1] (bounded at +9 counts at one idx, closed for V293 by C1's independent knot derivation); the tag
  ignores the D-clamp integer; the "87 % of peak" D-kick sentence is a **×6.13 unit error** (14.5 %); "Kd
  128 on every record" is true on **8 of 28** (64 on 20). `scriptfix` applied the four fixes with the image
  hash held.
- **D — INTERLOCKS PASS (D1–D5), and D1 found the mechanism rather than failing to find one.** The
  integrate-and-trip **exists**: the soft-EME command integrator `gp-0x3570` in the shaper `FUN_00042af8`
  (`0x43214–0x4327C`), `I += (cmd − bound) << 15` at 1 kHz, authority `(|I>>15|·1092)>>10`, **SM2 arms at
  `|I>>15| ≥ 15361`** (a 100-count excess arms in 154 ms), `bound = max(corridor, IIR, boost floor 5120)`.
  ⭐ **The LKAS lane is clamped at 3072 so it cannot drive wind-up alone**; the aggregate ceiling 5325 is
  unchanged; the governor, `FUN_0004595a` and `FUN_000456a4` carry **no accumulator**; the energy budget
  `FUN_0007b022` is **unreachable** (it needs > 5325 strictly, and the cap table's max IS 5325).
  ⚠ **Residual named, not closed:** the 205-count band **`5120 < |cmd| ≤ 5325` needs 75 ms continuous
  residency**, it exists on V282 too, and SM2/SM3 self-clear. **D5 is false as worded** (the island does
  read `0xC61B6`) but **PASS in effect** — 239 island-internal targets, **zero external sources, zero
  `jarl` in**.

---

### 🛑🛑 V292 FLEW — THE VERDICT IN ONE PARAGRAPH

**The operator: grinding still present, stuttering WORSE — "most visible as an oscillation when holding
the wheel at a high angle."** Two of V292's own pre-registered revert signatures **FIRED**: the 6–9 Hz
strong-turn ripple returned (**F7 4.17 /100 s** pooled [1.68, 8.59] against V282's 0.51 and V281 rev 3's
0.00, ×8.1, p = 0.022; tap ripple/level **0.214 / 0.327 / 0.339** against a 0.25 trip and V282's
0.104–0.166), and the 9–18 Hz shoulder landed at **×1.8–2.1** where ×1.3–1.7 was predicted, carrying a new
**14.84 Hz line at +6.3 dB** on r6d where V282 reads +2.8. **The 18–22 Hz ring did NOT fall: by the
drive-controlled measure (engaged ÷ the SAME route's lateral-disengaged amplitude) the loop's own
contribution went UP ×1.20–2.00**, present-window amplitude ×1.07–1.38, the pre-registered creep stratum
×1.10 [0.68, 1.56] — against a predicted ×0.55 pooled / ×0.71 vs r6c. **f0 sat at 19.92–20.02 Hz on every
route and did not move.** The phase moved **+15.5 to +38.4° at 10 Hz** where −14 ± 4° was predicted —
consistently, on three routes against two references, **opposite in sign**. Mechanism: **P is not railed
on any of the seven F7 episodes** (duty ≤ 0.20), so this is not the V278 rev 3 stalled-wheel class; the
seven sit at 6.64–7.47 Hz, exactly the **7.3 Hz gate `DESIGN-V291-FBLP` predicted every dose at a ≥ 927
would pay** (V292 carries a = 962) — the linear 7 Hz mode V281 rev 3 damped out, **re-armed by the fb
pole's phase lag** [EVIDENCE for the numbers, BELIEF for the causal attribution]. Exposure, excitation
(`0xE4` content ≤ ×1.3 while the response moved ×2) and route-normalisation controls all pass; the one
standing confound is the driving model change `tsfdo` → `gyhu3`, which is why controls (2) and (3) exist.
**The wiped `Accord*` params are RESOLVED and NOT a confound** — each code default equals the 2026-09-10
backup value, so the effective outer loop was unchanged, and `AccordCurvatureLead` was absent both sides
⇒ default OFF, the prereg requirement met. Full read: `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md`;
lineage entry and verdict in `docs/BUILD-LINEAGE.md`.

### 🛑🛑 V293 — WHAT IT IS, WHAT IT COSTS, AND WHAT IT CANNOT PROMISE

**V293 = V282 + cal-only edits, not one code byte:** `0xC62E6` 46080 → **0** (the LKAS rate-PID feedback
saturation clamp; zero forces the feedback operand to exactly 0 on all three branches ⇒ **`E = 32·setpoint`,
the loop is OPEN at every frequency**), the Kd bank `0xCB7D4` → **0** and `0xC61B6` → **0** (**D ≡ 0 twice
over, by two independent cells** — the prereg's A1 clause FAILs unless either alone suffices), the Kp bank
`0xCB994` **all 28 records → 120 flat** (at fb = 0, V282's Kp 248 would rail from idx 116, i.e. peak torque
from 48 % of demand; 120 keeps the surface **linear to full command into V282's own 15360 P-rail**; all 28
because the fb clamp is **one global cell** while Kp is per-slot), and `0xC6446` 5244 → **2048** (the r24
engaged arm). **Class: V279 rev 2's structure (built 2026-09-02, never flown) rebased onto V282** — the
LKAS lane becomes a linear **torque map**, `T = f(cmd)·taper`. Not a new lever; new are the base, the r24
dose and the fork preset. 🛑 **Peak authority is ×1.000: the delivered rail reads 2461 on the V293 image
AND on the V282 image.** Three numbers have been called "the rail" and only one is delivered — **2461**
is the byte-exact steady state through the fade and the output lag (the residue is the output lag's
integer fixed-point interval); **2462** is the same chain's LINEAR DC; **2505** is the structural ceiling
`min((15360·5346)>>15, 3072)`, the `T_ceil` convention the older docstrings print. **Never quote 2505 as
delivered — neither build reaches it at fade 254.** (This supersedes the design doc's ×0.9992 "2461 vs
2463", which compared the two builds by two different methods, and refines correction 3(d) below.)

**🛑 THE PRICE, and it is on the symptom he has just called worse.** V282's loop is a **disturbance-
rejecting servo below ~13 Hz**, and opening it removes that rejection: the predicted **5–9 Hz wheel band
rises ×1.74–1.85 broadband** across the r24 arms, and **×2.10 (r39) / ×1.45 (r35)** on loaded high-angle
windows — consistent with `|1 + L_V282(7.3 Hz)| = 2.04`. That is the same band V292's flight just measured
rising ×1.6–2.2 raw / ×2.9–4.3 route-normalised. **In exchange**, the ring is predicted **×0.285** on r39's
loudest windows and **×0.40** on r6c, with an **on-car anchor** — the reciprocal of V282's own measured
engaged ÷ disengaged ratio — of **×0.24–0.29**. 🛑 **The one out-of-sample test of that predictor FAILED
on V292** (predicted ×0.535, the wire read the loop contribution UP ×1.20–2.00), and the failure is the
**method's**, not an implementation difference. **The r24 cut to 2048** is the orchestrator's ruling
against the design's 4451, taken before any image existed: a criterion-exact arm carries no margin when
the same model under-predicted V292's 5–9 Hz cost three-fold, 2048 is the record's own priced lever, and
**in torque mode the cut is free at 20 Hz** — with the servo gone, removing r24 **raises** ζ (+0.036 /
+0.097 / +0.183 at κ 0.10/0.20/0.45, 96–100 % of plants) where with the servo present it costs it.
**The outer loop is NOT the risk** (Ms 1.09–1.38 vs V282's 1.04–1.35, PM 64° vs 66°; no grid cell
reproduces V276's 2–4 Hz signature that V282 does not also reproduce) — **V276's shape returns as a
feedforward mis-scaling ×3.17 at 5 m/s**, which is what the fork preset exists to prevent.
⭐ **The decomposition the operator is entitled to before he decides:** sweeping `0xC62E6` 46080 → 0 with
Kp 120 / Kd 0 held moves the ring only ×0.299 → ×0.272 — **~90 % of the ring benefit is Kd = 0 and the Kp
re-level; the clamp is what changes the delivered QUANTITY** and is nearly free on the ring. 🛑 **There is
no intermediate dose**: `0xC62E6` is a clamp, not a gain, and any non-zero value is a **Coulomb relay on
sign(rate)** — worse than 0 on every column, and it *adds* 18–22 Hz motion with the command frozen.
**🛑 THE FIRST DRIVE IS AN IDENTIFICATION DRIVE, NOT A SYMPTOM DRIVE:** hands-off, laterally engaged,
≥ 400 frame pairs per |τ| bucket in ≥ 4 buckets to |τ| 0.5, both signs, fitted by instrumental variables
against `modelV2.action.desiredCurvature·v²` — **not** from `torqued`. Then the tune. Then the symptom drive.
Detail: prereg `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` · design
`docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md` · lineage entry
`docs/BUILD-LINEAGE-PART6-V291-ONWARD.md` · builder `analysis-2020accord/builds/v108_plus/build_v293_tva.py`.

**READ IT BY:** the within-frame identity `T_tap = f(cmd)·taper` on every engaged frame, with
`sign(T) = −sign(cmd)` ≈ 1.00 proving the feedback is dead (T saturating below the map top means the map
is not the live source); the ring by the **drive-controlled** measure only — engaged 18–22 Hz ÷ the same
route's lateral-disengaged (V282 3.4–3.9, V292 4.1–6.8) plus present-window amplitude vs r6c — **never the
driven half-peak decay**; F7 and tap ripple/level at |angle| ≥ 30°; a 1–4 Hz line in command and angle;
b4–b7 duties as the r24 control. **REVERT IF:** grinding unchanged (his word); the 6–9 Hz ripple returns
(F7 ≥ 2/100 s or ripple/level ≥ 0.25); **a 1–4 Hz oscillation of command and angle — the V276 signature;
the fix is the fork preset, not the firmware, but the drive stops**; a 10–18 Hz line; a darty or loose
feel; a one-sided pull at rest; any EME or DTC.

### 🛑🛑 THE DESIGN LAW, AS OF 2026-09-13 LATE — the in-loop null sentence has FIRED

> **V292's pre-registered null sentence — *decay not below 1.23× V282's while the phase HAS moved ⇒ the
> object's damping is not set by the rate loop's return ratio* — FIRED on the wire.** Either the fit
> family mis-sizes what a feedback pole does at 20 Hz (the opposite-sign phase is the tell), or the
> engaged-only de-damping is not the LKAS loop's return ratio at all. **Torque mode is the
> MODEL-INDEPENDENT test of that disjunction: with `fb ≡ 0` there is no loop at any frequency, so no fit
> family stands between the edit and the answer.**
>
> **THE TERMINAL NULL SENTENCE, written before the drive:** *if the 18–22 Hz ring's amplitude and
> ring-down are unchanged with the LKAS loop open on every frame — the edit-live identity holding — then
> the 20 Hz object is not the LKAS loop's, and the whole in-loop class, V38 → V293, is closed.*

- **The measurement that set the direction still stands** (`OPENLOOP-RING-DAMPING-2026-09-13.md`, 35
  routes, 4,759 s lateral-disengaged): with the loop OPEN there is **no resonance in 16–26 Hz**; a
  synthetic mode of ζ ≤ 0.03 at the same energy WOULD have been found ⇒ **ζ_open ≥ 0.05 or non-modal**;
  engaged ζ 0.034–0.036, **V282 alone 0.0164** [0.0126, 0.0222] at 20.01 Hz; load-matched amplitude
  OFF/engaged 0.21 (×4.5). Limit: opening the loop also removes the LKAS excitation, so "no object" has
  two readings and both say the same thing for a build.
- **Scoring rules the V292 flight forced, binding on every later build.** (a) **Score the ring by the
  DRIVE-CONTROLLED measure** — engaged ÷ same-route lateral-disengaged, plus present-window amplitude vs
  r6c — **never** by the driven half-peak decay, which is confounded. (b) **Pre-register MARGINS, not
  points**: the operator's revert threshold on the 7 Hz ripple (0.25) and V292's own prediction (0.22)
  were 13 % apart. (c) **A duty read is not an attribution** — design the identity read on the bit's
  *meaning* (a lagged-sign correlation, with a lag profile and reference builds), not on a duty that
  overlaps the reference.
- **The r24 lane** (`TRACE-2026-09-13-r24-lane-transfer.md`): a lag-4 backward difference of torsion-bar
  torque, unit-weight sibling of the LKAS lane at `gp-0x6b94` ⇒ **1 : 1 at the motor**; pure PUMP at
  3–7 Hz, near-pure DAMPER at 18–22 Hz (73–86 % of the electronic 20 Hz damping) — **but that damping is
  a partial cancellation of the servo's de-damping, and it evaporates when the servo goes.** κ dispute
  still open (0.10–0.20 / 0.45 / 1.45); 10–14 Hz unidentified; the `gp-0x671d` fault latch UNARMED.
- **The LKAS lane's true path** (`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`): T @`0x2A23C`
  → gated copy @`0x2A2EA` → `gp-0x6b3c` → clamp ±`0xC61B2` → request array → **`gp-0x6b4c`** (unit weight)
  → aggregator → governor → comp → shaper → `gp-0x6b98`. **`gp-0x6ad4` is a driver-torque tracking PID**,
  not the LKAS output. `0x2A508–0x2B421` is an uncalled TWIN of the LKAS output path, analysed and SAVED.

### THE SESSION'S GOAL AND THE SESSION'S ANSWER

**The operator's goal, in substance:** a new firmware plus StarPilot changes that keep **V282's authority**
(×6 torque, ×6 rate setpoint, no EMEs) with **no grinding and no stutter**; **either** the LKAS PID tracks
**angular acceleration** (≈ torque, which is what openpilot expects) **or** StarPilot outputs a **rate
target**; and the StarPilot tuning updated to match.

| reading of the goal | what it would be | disposition |
|---|---|---|
| **"torque"** | **Torque mode** — V279's structure on V282: fb clamp 0, Kd 0, Kp re-levelled | ⭐ **BUILT as V293.** Cal-only, no cave, and the model-independent test of the in-loop class |
| **"angular acceleration tracking"** | the PID tracks `d(rate)/dt` instead of rate | 🛑 **DOMINATED — recorded, not built.** It **CONTAINS torque mode** and adds electronic inertia on top, and the inertia term **needs a cave** (the kit's only bricking class). Reasoning: `TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §4 |
| **"StarPilot outputs a rate target"** (fork Design B) | shape the reference on the openpilot side | 🛑 **CANNOT REMOVE THE GRINDING — recorded, not built.** V288 rev 2 flew exactly this class: the cave was live, the D-bind duty fell ×0.03 as designed, **and the grinding was unchanged** (19.99 vs 19.93 Hz, KS p 0.18). Nothing on the fork's reference side reaches the 20 Hz ring |
| **"the tuning updated"** | four toggles the operator had to keep consistent by hand | ⭐ **ONE switch instead**: `AccordEpsTorqueMode`, uncommitted in the fork, OFF by default |

### ⏱ τ, MEASURED — and "τ = 0.20 s" was never a measurement

`rlog-tools/studies/grind/TAU-ACTUATOR-DELAY-2026-09-13.md` [EVIDENCE]. The LKAS lateral delay, measured
`controlsState.desiredCurvature` → steering-angle curvature on **six routes**, zero-lag and 200 ms controls
both passing. ⚠ **The `0xE4` → rate pair is UNUSABLE for this** — the rate-plant feedforward makes the
wheel **LEAD** the command by one round trip.

| speed | correlation-peak lag, current tune (r6c / V282) |
|---|---|
| 3–8 m/s | **258 ms** [251, 264] |
| 8–15 m/s | **232 ms** [219, 247] |
| 15–25 m/s | **211 ms** [197, 231] |
| 25+ m/s | **182 ms** [175, 191] |

⭐ **V292's routes sit INSIDE that scatter — V292 changed nothing here; the TUNE did.** r39's older tune
was **20–55 ms faster**, and the LAF 6.0 tune cut P/I authority.
🛑 **The path is NOT a pure delay, so "τ = 0.20 s" is neither measured nor a single number.** Three
estimators differ by **up to 100 ms on the same data**, and the fitted lag pole is **1.4–4.3 Hz — the
torque controller's own bandwidth plus plant, NOT the EPS servo.** ⇒ **use `tau_eq(f)` at the crossover,
not a scalar.** The **dead-time / servo-lag split is NOT identified** (r39 puts the speed dependence in
dead time, 80 → 180 ms; r6c puts it in the pole) — **quote totals only.** At 3–8 m/s the wheel realises
only **0.57–0.69 of commanded curvature at 1 Hz**, and small-signal is **30–50 ms slower** (friction and
deadband, **not** rate limiting).
⇒ **What this does to B6:** its FAIL was conditional on **τ ≥ 0.18 s**, and the measured totals are
**0.182–0.258 s at every speed band** — met, and met with margin (**258 ms**) at the 5 m/s point where the
FAIL sits. ⚠ **Not a clean substitution**, because the report's own finding is that a total is not
`tau_eq` at the crossover. **B6's condition is satisfied on the best evidence available; the re-score at
the repaired preset is still what settles it.** [EVIDENCE for the totals; this inference is mine.]

### 🛑🛑 A STANDING FORK DEFECT — LIVE ON THE CAR TODAY, ×6.6, AND IT IS NOT A V293 PROBLEM

Found by `advB3`'s B6 surface, **crux verified in the fork source by the orchestrator.** StarPilot feeds
**`error_with_lsf`** (= `error·(1 + lsf/kp)`) into **`get_friction`**, where upstream openpilot feeds the
**raw** error. The friction compensator's gain is therefore **`(friction/0.30)·(1 + lsf/kp)`**:

| configuration | friction-compensator gain | outer-loop PM at 5 m/s, κ 1.00, τ 0.20 s |
|---|---|---|
| **the operator's LIVE tune today (Kp 0.9, on V282)** | **×6.6** | — |
| the V293 preset as shipped (Kp 0.3, friction 0.01) | **×17.9** | **22.8°** (Ms 4.32) |
| the repair: preset friction **0.01 → 0.00** | — | **42.2°** (Ms 2.06, GM ×1.40) |

⭐ **A LOWER Kp MAKES IT WORSE, NOT SAFER** — the loop gain is minimised near **Kp ≈ 1.0**, so *"Kp 0.3 is
the conservative third of today's 0.9"* is **backwards as a stability argument.** ⚠ The whole B6 verdict is
conditional on **τ ≥ 0.18 s**, and **τ = 0.20 s is the operator's `SteerDelay` toggle ECHOED BACK, not
identified** (the Honda port's prior is 0.10 s) — being measured from the rlogs now. **This is a fork fact,
not a firmware fact: it is live on V282 today and it does not depend on which image is in the ECU.**

### FORK (`raayyymond-StarPilot` @ `Dom`) — one switch, and the mismatch is NOT symmetric
**`AccordEpsTorqueMode`** (Galaxy → *Custom Patches*), **uncommitted, ships OFF**, card
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`. **The one rule: it may be ON only while a
torque-map image (V293 or later) is in the ECU.** Going TO V293 — **flash first, toggle second**;
reverting — **toggle first, flash second**. 🛑 **Mode ON + rate-servo image = OVER-DELIVERY, feedforward
×2.55 at 15 m/s / 0.9 m/s², and NOTHING downstream catches it** (`opendbc/safety/modes/honda.h` applies no
magnitude, rate, driver-torque or RT-window limit to `0xE4`) — **never create that state, not even for the
drive to the flashing spot.** Mode OFF + torque-map image = under-delivery, recoverable, and the state
Safe Mode forces. Provisional first-drive tune, all four in `latcontrol_vehicle_tunes.py`'s
`HONDA_ACCORD_TORQUE_MODE_*` block and **all PROVISIONAL**: LAF **6.0** (carried over so the first flight
is not also a gain change — **not an identification**; on a torque actuator the DC gain is finite and
should come out lower), friction **0.01**, Kp **0.3**, Ki **0.15**. Net command at 15 m/s / 0.9 m/s² is
**×0.955** of today's — a coincidence at one operating point, **not a safety margin**. `SteerRatio` stays
**16.88** through identification (its second consumer is gone in torque mode, so the level's sensitivity
roughly halves) [BELIEF, from the structure]. 🛑 **If the toggle appears inert, `params_pyx.so` was not
rebuilt** — the new keys live in the compiled `common/params_keys.h`, and an older `.so` silently falls
through to the default (which is OFF, so the failure is in the safe direction, but it is silent).
- 🛑 **THE PARAMS-WIPE TRAP, measured on the V292 routes:** every `Accord*` key was **ABSENT** from
  `initData.params`, i.e. running its **code default** — which is invisible in a route read unless you
  have the checkout. It was benign this time (each default equalled the 2026-09-10 backup value), but
  **an `Accord*` param at its default is absent from `initData.params` by construction**, which is why
  `starpilotLateralState.epsTorqueMode` exists as a cereal field. **Verify the mode from the cereal
  field, not from the params blob.**
- **`torqued` UPDATED, and it is a report, not a licence to edit the memories:** on route 6f
  `liveTorqueParameters` reads `useParams` 1, **`liveValid` 1**, `latAccelFactorRaw` **6.24** (p5–p95
  5.86–6.67) — within 4 % of the toggle. The record's *"torqued cannot validate on the modded EPS"* was
  measured on r31/r32/r33 at the **port defaults**, where `liveValid` was 0 on every tick. The toggle
  ceilings quoted there are also stale (`LAT_ACCEL_FACTOR_MAX_MULT` now 10.0, `STEER_KP_MAX_MULT` 5.0).
  **Still do not identify LAF from `torqued`** — its buckets do not fill on this car.
- **`ModelCurvatureLead`** (`AccordCurvatureLead`, uncommitted, OFF) is unchanged and **inert under torque
  mode**; set it explicitly OFF so the rlog reads unambiguously. `AccordTurnFFTaper`, `AccordEpsGainScale`,
  `AccordEpsSpringScale`, `AccordFFRateGain` are all held inert in torque mode. 🛑 **Do NOT flip
  `AccordRatePlantFF` by hand** — that single flip on a rate-servo image *is* the over-delivery hazard.

### CORRECTIONS OF RECORD, 2026-09-13 (late)
1. **The V292 prereg's b3 DUTY read did not discriminate** — V292 0.418–0.453 against V282's 0.467,
   overlapping, and the idle control read backwards (0.035–0.049 vs r6c 0.000). A **design defect in the
   read**, caught only because the flight agent refused to force it. Attribution came from the bit's
   *meaning* instead. Carry (c) of the scoring rules above.
2. **The byte-exact replay's V292 prediction FAILED out of sample** (×0.55 predicted, the loop's
   contribution measured UP ×1.20–2.00). The failure is the **method's** — the V293 design agent
   reproduced the published number with its own implementation. **Every replay-based ring prediction in
   the record now carries that caveat, V293's included.**
3. **Tracer corrections, four, each from the bytes** (`TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §7):
   (a) **`0x29F18 sar 0x7,r2` is the I ACCUMULATOR, not P — the registers were swapped in the record.**
   P is `(E·Kp) >> 8` formed at `0x29E36 mul` / `0x29E3E sar 0x8`, clamped to ±`[0xC61BC]`; `r8` is D.
   (b) **`0x2A0C6` is NOT a reset route ("SKIP 3") — it is a second delivery MODE**, a feedback-only
   viscous damper `−sign(fb)·LERP(|fb>>5|)` over `0xC6710–0xC6730`, gated on `gp-0x680a`, **unreachable**
   (zero writers; `.data` boot value `00`), which is why the mislabel has cost nothing.
   (c) **The cold-boot values of `gp-0x3d30` / `gp-0x3d2c` are now EVIDENCE, not BELIEF: both boot to 0**,
   from the `.data` copy loop `0x1476C–0x14794` (flash `0x89380` / `0x89384`), with `gp-0x6AB0` ← `0x86600`
   = `88 02 88 02` as the non-zero positive control.
   (d) **The delivered rail is NOT 2481 and NOT 2505.** An always-on override taper
   `((255·255)&0xFFFF)>>8 = 254`, i.e. **×254/256**, sits between the sum and the sum clamp; 2481 omits it.
   ▸ **Refined at the V293 build from BOTH built images: the DELIVERED rail is 2461** (the byte-exact
   steady state; the residue is the output lag's integer fixed-point interval), **2462 is the LINEAR DC**
   of the same chain, and **2505 is the structural ceiling.** The tracer's 2462 was the linear reading.
4. **THE TAPER — SPLIT THE CLOSURE. The SELECTOR is CLOSED; the AXIS UNIT is OPEN.**
   ✅ **CLOSED, and the kit memory was right about D:** the taper is **ONE stage, not two** — the bytes at
   `0x2A13x` carry `factor = ((tapAB · tapCD) & 0xFFFF) >> 8; S = (factor · S) >> 8`, at-rest 254/256 only
   because **both halves return 255 at rest**, and **`gp-0x6803` picks B × D (`0xCBBC4`)**. The tracer's
   `bVar1 = true` → A×C reading is **wrong**.
   🛑 **STILL OPEN — what the C/D half's X AXIS IS IN.** Adversary A read it as **speed and assumed km/h**
   (**BELIEF**, and A says so), which would put the rail at **2151 at 10 m/s and 736 at ≥ 20 m/s**. The
   record's own on-car tap numbers point the other way — V278 rev 3's `T_meas/T_sim` **0.42–0.51 at
   3–9 m/s**, and the tap's 310 rail on faster routes. **Do not treat the derated rails as established.**
   ⭐ **What is safe either way: the table is IDENTICAL on both builds, so the V282 : V293 ratio holds at
   every speed** — the trade does not depend on resolving the axis. But **2461 is an AT-REST number**, so
   condition every on-car rail read on speed rather than quoting it flat.
5. 🛑🛑 **THE B ADVERSARY'S DEFECT LIST (its §9) — SIX ITEMS, ALL IN MACHINERY OTHER RESULTS REST ON, NONE
   IN THE ARTIFACT.** Every one is a tool or a document, not the image.
   (a) **The module-default `B(f)` fit is BAD.** At `nb = 1, nd = 4` it returns rms `ln|B|` **0.54**,
   phase error **38°**, and **a spurious UNSTABLE 4.5 Hz root**. **Use the design's `nb = 1, nd = 3`**, and
   re-check anything fitted with the module default.
   (b) 🛑 **`r24_plant_refit.py` CANNOT REGENERATE `r24_plant_refit.json`** — its `fit_B(nb=4, nd=2)`
   now raises on the properness guard. **The pre-registration names that family as B1's reference and it
   is not reproducible from its own script.** The JSON on disk is an artifact with **no working producer**.
   (c) **`v293_s3_gate7`'s unbanded `unst` column is MEANINGLESS** — do not quote it.
   (d) **The design scripts modelled Kp 119; the image carries 120.** Every design-script number that
   depends on Kp is off by that one count until re-run.
   (e) **`v293_s4` never ran the stock leg or F7** — its stock comparison and its F7 figure do not exist.
   (f) **`v293_s2` TASK 2C's V293 command leg reads ×2.5 BELOW the second method** — unreconciled.
   (g) **The pre-registration's own anchor caveat (1) is VOID**, and **the r26 sibling arm was omitted**
   from it.
6. 🛑🛑 **r24 ARM CORRECTION — `0xC6440` = 2048 IS THE DISENGAGED ARM, and it reads 2048 on EVERY image
   INCLUDING STOCK.** Honda's stock **engaged** arm is `0xC6446` = **512**. ⇒ **V293's 2048 sets the
   ENGAGED arm equal to the DISENGAGED one**, which is a different and much more interpretable statement
   than "a number between 512 and 5244".
   ✅ **RESOLVED by `advB3b`: the lane is SWITCHED, not gated off.** The selector rungs read
   `g = 1024 if gp-0x671d else 0xC6446 if lateral else 0xC6440` (`0x3ABFE` / `0x3AC08` / `0x3AC12`).
   ⇒ **on V293 the r24 lane is BIT-IDENTICAL engaged and disengaged**, and the on-car anchor's reciprocal
   (**×0.24–0.29**) is therefore **an ESTIMATE of V293's ring, not a lower bound.** ⚠ **Three residuals
   keep it an estimate:** V293 still injects `f(cmd)` (the replay sizes the forced ring at **3.49** against
   V282's **10.30** counts); the disengaged reference is **mostly stationary**; and **the r26 base-assist
   arm `0xC6444` also moves with the `0x3AA96` gate** — unresolved.
7. **Refinement to `TRACE-2026-09-13-fb-lag-filter-bytes`, from `goldenmodel`'s independent march:**
   with **`b = 0` the filter state's absorbing set is `[−10, −1]`, not `{0}`**, so the two-sample feedback
   operand would rest in **`[−20, −2]`** rather than at zero. It does not touch V293 (whose clamp forces
   the *operand* to 0 regardless of the state) and it does not touch V292 (whose cave releases the
   absorbing state at its own `b`), but **any future argument that "the state rests at exactly 0" must
   name its `b`.**
8. 🛑🛑 **NOTHING IN THE FORK MEASURES τ — three separate fields look like identifications and none is.**
   (a) **`liveDelay.lateralDelay = 0.2` is the operator's `SteerDelay` toggle ECHOED BACK.**
   (b) **`lateralDelayEstimate` (0.2479) is ~99 % SEED from previous routes** — 50 blocks, all seeded;
   r39 sat **frozen at 0.2272 for 948 s**. It is gated to **≥ 15 m/s** and reads **livePose yaw, which
   lags the gyro by 73–90 ms.** **Not an identification.**
   (c) ⚠ **A FORK DEFECT, reported not fixed:** `full_lateral_delay(x) = x + 0.2`, and **the toggle branch
   in `lagd` SKIPS that wrapper**, so the field **mixes two conventions** depending on which branch wrote it.
   (d) **The operator's `SteerDelay` 0.2 is a FULL delay**, implying a **vehicle part of 0.0** against
   stock Honda's **0.1 / 0.3**. ⇒ **Quote the measured totals (182–258 ms by speed) and `tau_eq(f)` at the
   crossover. Never quote 0.20 s as measured.**
9. Still standing from earlier today: `DESIGN-V290B` §A.2's per-build free-decay ζ are **not**
   measurements; the ring is **~16 LSB on the 0x18F RATE channel** (0.17–0.28 LSB was the ANGLE channel);
   r24 is a **lag-4 backward difference on `gp-0x4f62`**, not a 4-tap FIR on `gp-0x6ada`; the record's
   "×33–72 engagement gating" is a presence RATE and the amplitude ratio is ×4.5.

### ✈ NEXT — in order
1. ⭐ **THE OPERATOR DECIDES.** The pass is complete and V293 is cleared over one dissent. Put in front of
   him, before he decides: the **×0.25-ring-for-×1.5-stutter** trade; the decomposition (**~90 % of the
   ring benefit is Kd = 0 + Kp 120, not the clamp** — the two goals are separable); **A's authority
   finding** (the peak is identical and needs twice the demand to reach; 0.47–0.49 of V282's stalled-wheel
   torque below idx 116); and **the dissent on B2** in its own words.
2. **If he flies it, the ORDER is not optional.** Toggle checklist: **flash first, toggle second**; the
   fork preset is **mandatory**; **the first drive is an IDENTIFICATION drive**, then the tune, then the
   symptom drive. **Watch the low-speed 1–4 Hz signature first** — it is the first revert trigger and the
   creep margin is only ~10–20 % of plant gain on **both** builds. Score the bands; **he scores the symptom.**
3. **The EME / governor dwell residual is NAMED, not closed:** the 205-count band
   **`5120 < |cmd| ≤ 5325` needs 75 ms continuous residency** to arm SM2. It exists on V282 too and
   SM2/SM3 self-clear, but nothing has ever measured the dwell on the wire.
5. **The IMU stays the top missing instrument** (road vs rack vs motor). No drive so far separates them.
6. **Two open premises other builds have already leaned on:** `gp-0x6806`'s engaged state, and **the
   taper's X-AXIS UNIT** (the selector is closed — D — but whether the axis is km/h is BELIEF, and it
   decides whether the rail derates to 2151/736 or not; see correction 4). Because the taper is one
   speed-derated stage, **condition any on-car rail read on speed** rather than quoting 2461 flat.
7. Standing: golden model **94 symbols** — 🛑 **90 → 94 this close-out, when the LKAS RATE PID ITSELF was
   added** (`lkas_rate_pid_tick`, `lkas_rate_pid_surface`, `lkas_rate_lerp`, `lkas_output_lag`, SECTION 5D
   of `eps_chain_control.py`), closing the gap that had left V288's and V289's mirrors with no caller;
   a fifth new def, `_self_check_v293`, is deliberately NOT re-exported. `_self_check()`+`_demo()` sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` (2,512 B) — **unchanged**, because
   every `_self_check_v2xx()` asserts and prints nothing. **Contract re-verified independently at close-out:
   94 / 2,512 B / `740f4bcd…`, and `_golden_contract_syms.json` carries the four new names.**
   `CLAUDE.md`'s contract line is already at 94;
   🛑 **the lineage SPLIT happened this close-out** — `docs/BUILD-LINEAGE.md` is the entry point,
   **new per-build entries from V293 onward go in `docs/BUILD-LINEAGE-PART6-V291-ONWARD.md`** (⚠ PART**6**;
   `PART5-V122-ONWARD-MEASURED` already exists and is a different thing). `BUILD-LINEAGE-PART1-LEVER-INDEX.md`
   is over the 150 KB soft target — split it at the next close-out; `0xC61C0/C2/C4` still has no lineage entry.

**Session reports:** `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md` (+ `v292_flight_*.py`,
`extract_v292_routes.py`) · `docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md`,
`ADVERSARIAL-V293-PREREG-2026-09-13.md` · `docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md`
(+ `v293_s1`…`s10`, `v293_lib.py`) · `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` ·
`docs/research/ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md` and
`FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md` (each now carries a **Reconciliation**
note pointing at the other and at the prereg's dispositions) · `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` ·
`analysis-2020accord/builds/v108_plus/build_v293_tva.py` · handoff
`docs/handoffs/2026-09/HANDOFF-2026-09-13-V292-FLEW-REVERT-V293-TORQUE-MODE-BUILT.md`.
**The superseded 2026-09-13 V292 decision box is archived in
`docs/archive/STATE-ARCHIVE-2026-09-13-v292-decision-box.md`**, and the 09-09/09-10 boxes in
`docs/archive/STATE-ARCHIVE-2026-09-13-decision-boxes-0909-0910.md` — records, not instructions. Nothing
was retracted by either move; every still-decision-bearing correction is in the paragraphs above.

---


## 📁 **THE V279-ERA REFERENCE AND 84 FINDING BLOCKS (2026-08-30 → 2026-09-11) ARCHIVED 2026-09-13**

Moved to `docs/archive/STATE-ARCHIVE-2026-09-13-v279-to-v290-blocks.md` at the V291 close-out to keep this file
under its working target. **A record, not an instruction.** Nothing was retracted by the move; the decision box
above carries every correction that was still decision-bearing.

## 📁 **EARLIER BLOCKS (24) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 🗂 INDEX TO THE BLOCKS BELOW

| what you want | look for the block titled |
|---|---|
| the flight order | *FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD* |
| why V222’s ratchet is a risk | *THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET* |
| what V228 is | *V228 BUILT — V222 WITHOUT THE 8×* |
| the audible side effect | *"V228 CANNOT MAKE ANYTHING WORSE" IS FALSE* · *THE 40–49 Hz LIFT IS UNAVOIDABLE* |
| **my own withdrawn claims** | *SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED* · *CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR* · *CORRECTION: "V62’s lever CREATED grind #2" is NOT settled* |
| what measurement can and cannot do | *THE RATCHET BAND CANNOT BE SCORED BY BAND POWER* · *RING-DOWN COMPUTED* · *CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION* |
| what is closed and will not be re-proposed | *THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION* · *THE NOTCH IS NOW CLOSED* · *EXACTLY ONE BIQUAD* · *FOC CURRENT LOOP IS TRANSPARENT* · *LEVER A r26-HALF ONLY* · *r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING* |
| what is still open | *THE TWO REMAINING QUESTIONS BOTH NEED A CAVE* · *OPEN OBSERVATION — an 11.4× residual* · *THE FRAME TEST IS INCONCLUSIVE* |
| the session narrative | *SESSION HANDOFF* (last block) |

---



## 📁 **EARLIER BLOCKS (22) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 📁 **EARLIER STATE (V204 → V208) IS ARCHIVED — with its closures kept here**

Split out 2026-08-30 at **138.6 KB**, against the ~150 KB soft target. The narrative, the numbers
and the retractions now live in `docs/archive/STATE-ARCHIVE-2026-08-30-v204-v208.md` — **a record,
not an instruction.** What that era CLOSED is kept below, because a closure is what stops a lever
being re-proposed:

| closed | verdict |
|---|---|
| the notch shelf | was cutting a **real 6–9 Hz damper 7.15× below the car**; fixed V214–V217 |
| the saturation census | **closed** — the last gate cannot fire; V207 retired **before** flight |
| `gp-0x6b70` saturation | **does not saturate**; V206’s best argument retracted |
| the command-gated-saturation model | **no mechanism exists** in this path — no gate rejects either |
| the 8 Hz ratchet notch | **stays rejected**; the friction lane is NOT "reverted to Honda" |
| two authority levers | **checked and closed**; a latent 18.52 Hz injector found silent |
| `0xC63AA` sensitivity | **41× understated** in the old record |
| the relay | a **SOFT** relay, curve **built at runtime** — unreadable from the image |
| `0xC63AE` sign | established **without a drive**; V206 built and priced |

🛑 **Tooling gotcha kept live, because it still bites:** `stock_fw_dump/code.bin` reads `0xFFFF`
at `0xC6CD0` because **V57 created that cell**. Do not use the stock dump as a stock reference for
post-V57 migrated cals — it hands you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and
`0xC64DE` read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
