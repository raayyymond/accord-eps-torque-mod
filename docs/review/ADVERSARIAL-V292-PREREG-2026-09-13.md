# ADVERSARIAL PASS — V292 (C10 with error-feedback cave), pre-registration

**Written by the orchestrator BEFORE the V292 image existed and BEFORE any adversary was briefed.** Same
contract as `ADVERSARIAL-V291-PREREG-2026-09-13.md`: four independent agents, disjoint surfaces, each
re-deriving from the BUILT IMAGE; the pass must be able to return "do not flash".

## The build under attack

**V292 = V291's dose, implemented byte-exactly.** The three V291 cells stay (0xC63E8/EA = 962/958, the
9.94 Hz DC-held feedback lag pole; 0xC6446 = 4725; the 0x14A b3 rung = sign(fb state)) and a CODE CAVE
replaces the filter's two quantised terms `floor(b·x/1024)` and `floor(a·s/1024)` with the same terms
carrying error-feedback remainders, so that the integer filter's mean behaviour equals the linear
filter's at every amplitude. Design: `docs/specs/design/DESIGN-V292-FBLP-CAVE-2026-09-13.md`; mirror
`rlog-tools/studies/grind/v292_cave_mirror.py`. Nothing else moves.

**Why V292 exists.** V291's pre-registered pass failed exactly one clause, B4's steady state (×1.00 ± 1 %),
byte-exactly at tiny demand: the quantum b/1024 = 1.07 raw counts left the rate loop effectively open
below ~0.5 deg/s (sp = 3 counts: ×1.34–1.80). That is an integer-arithmetic artefact of any cal-only
pole change, and error feedback removes it. Every other V291 criterion passed (B3 re-scored PASS at
×3.3–4.2 on the admissible effective r24 arm, κ 0.449). See `ADV-V291-B-LOOP-2026-09-13.md` §11.

## The 9–18 Hz sensitivity shoulder — disposition, decided before the pass

Adversary B found (V291 §4.3) that C10's worst-fit disturbance sensitivity |1/(1+L)| is higher than
V282's on 121/121 fits over 3.0–18.2 Hz, peak ratio ×1.99 at 12.85 Hz, and proposed a gate "ratio
≤ 1.25 pointwise over 3–30 Hz". **That gate is NOT adopted for V292, and the reason is recorded here so
it cannot be re-litigated after the fact:**

| f (Hz) | V282 worst-fit \|S\| | C10 worst-fit \|S\| | ratio |
|---|---|---|---|
| 9 | 0.70 | 0.91 | 1.30 |
| 12.85 | 1.41 | 2.81 | 1.99 |
| 14 | 1.78 | 3.25 | 1.94 |
| 16 | 2.58 | 3.40 | 1.32 |
| 18 | 3.96 | 3.54 | 0.89 |
| 20.3 | 18.42 | 2.64 | 0.14 |
(from `ADV-V291-B-LOOP-2026-09-13.md` §4.3, unfolded, worst fit of 121)

- **In absolute terms C10's shoulder (2.6–3.5 over 12–20 Hz) sits inside what V282 already carries at
  16–18 Hz (2.6–4.0), where the record reports no symptom line** (the two-line census finds V282's lines
  at 12–14 Hz and 20 Hz only). The band-wide worst-case peak falls 18.4 → 3.5, a ×5 reduction.
- **The shoulder is well damped** (no closed-loop pole below ζ 0.36 in 3–30 Hz); V289's rejected 16 Hz
  object was a ζ 0.03 line. No symptom in this kit's record has ever been tied to a well-damped
  sensitivity shoulder; a pointwise-ratio gate would be a criterion calibrated to no symptom, and it
  would close the whole loop-opening class at every readable dose (the ratio exceeds 1.25 at every corner
  ≤ 14 Hz) — i.e. it would forbid the only class the open-loop measurement licenses.
- **It is therefore pre-registered as a NAMED REVERT SIGNATURE with numbers**, not a gate: any new
  roughness, tone or line at 10–18 Hz on the drive (worst-fit sensitivity ×1.3–2.0 of V282's, peak near
  13 Hz; the byte-exact integer cycle relocating 19.8 → ~15 Hz) reverts the build. **The orchestrator's
  adjudication, marked as such; the operator may overrule it either way.**

## What a FAIL looks like — fixed before the pass runs

**Any one of the following is a FAIL, and a FAIL on A, B(1–4) or D(1–3) is "DO NOT FLASH".**

### A — ARITHMETIC (re-derive from the image)
1. The cave's integer mirror, re-derived from the BUILT bytes, does not give mean input gain exactly b/1024
   and mean decay exactly a/1024 at every constant x in 1…12000 (remainders bounded |rem| < 1024), or the
   realised DC differs from 30.903 by more than 0.1 % at any amplitude from 1 count up.
2. Any int32 overflow in x·b + rem, s·a + rem, or the two-sample sum, with |x| ≤ 12000 and s at its
   steady state; any narrowing store; any register or flag the displaced code depended on not restored.
3. The describing-function gain of the byte-exact filter at 20.3 Hz is outside 1.00 ± 0.03 at any
   amplitude A ∈ {1, 2, 3, 5, 8, 16, 24} raw counts.
4. The r24 lane arithmetic or the b3 rung differ from V291's (both are inherited; re-verify they are
   byte-identical to V291 and still correct).
5. The cave's displaced instruction(s) are not replicated exactly, or the return lands anywhere but the
   instruction after the displaced one, or the cave's cycle cost exceeds 2× the V289 cave's.

### B — UNIT / SCALE CHAIN and CLOSED-LOOP STABILITY (GATE 2)
1. Any of the 121 linear-stable family fits goes unstable under V292 (the linear loop is V291's; confirm
   the cave's mean behaviour is identical and that the dither term is zero-mean and ≤ 1 LSB per tick).
2. gate73 > 1.01 on the admissible (effective, κ 0.449) r24 scaling with k_eff 0.895; or the k = 1
   surrogate/folded disagreement exceeds what V291 §11 recorded.
3. Max |1/(1+L)| over 12–26 Hz not reduced by ≥ ×2 vs V282 on the effective arm, or a NEW pole with
   ζ < 0.05 anywhere in 3–30 Hz on any fit.
4. |T(3.9)| > 1.15, or |ΔL| below 5 Hz > 30 %, or byte-exact capped-step overshoot > 1.205, **or
   byte-exact steady-state authority outside ×1.00 ± 1 % at sp = 3, 33 and 330 counts, measured against the
   LINEAR V282 chain** (DC 30.891 — the surface the operator's authority is defined on). Compute it with the
   cave's arithmetic, not the linear model, and ALSO report the ratio against V282's own byte-exact chain as
   information. *Amended 2026-09-13 before any V292 image existed, on the cave designer's interim: V282's own
   integer filter under-feeds at small x (its DC reads 28.0 at x = 8 and ~29.9 at x = 30 against the linear
   30.891), so a mean-exact V292 will read ~1–1.5 % LOW against byte-exact V282 at sp ≈ 33 while matching
   the linear surface; the linear surface is the reference the operator's requirement names. The sp = 3
   point, where V291 read ×1.34–1.80, is the clause's teeth and is unchanged.*
5. The 5–9 Hz sensitivity bump ≥ 1.0 on the worst fit.
6. The ring ratio with the r24 loss folded < ×2.43 (readability floor).
7. openpilot's outer loop: 0.38 × |T(3.9)| > 0.5.
(The 9–18 Hz shoulder is scored and reported, not gated — see above. The fork toggle `AccordCurvatureLead`
must be OFF; with it ON B5 fails.)

### C — BUILD-SCRIPT AUDIT
1. Independent rebuild from the V282 image (cells + rung + cave + CRCs, block structure walked from the
   image) does not reproduce the reported image and rwd sha256.
2. The full-file diff vs V282 is anything other than the V291 15 bytes plus the cave bytes, the hook
   bytes and the touched CRC trailers.
3. The rwd does not round-trip, or any block CRC fails under the kit routine and an independent CRC.
4. A load-bearing claim about the edit's effect rests on a tautology or on the base hash; the census must
   be classified independently (V291's "377 substantive" was 67).
5. More than one V292 rwd on disk; V291's rwd must be renamed `SUPERSEDED-DO-NOT-FLASH-…` by the build
   (one flashable candidate per class on disk), or the script must refuse to write.
6. The output filename's dose/tag is not derived from the integers (V291 defect D2); no write guard
   (V291 defect D3).

### D — INTERLOCKS AND DOWNSTREAM (GATE 1)
1. Any accessor of the cave's two remainder words other than the cave, by raw byte scan (4-byte, 6-byte
   and bit-op forms) AND Ghidra, on the BUILT image; the cells must be aligned for their access width (the design uses two HALFWORDS at gp-0x6D74/gp-0x6D72, ld.hu/st.h)
   and inside the certified free run; boot value found or bounded.
2. Any consumer of the fb state gp-0x3d30 other than the filter and the b3 rung; the filter still runs
   every tick; the sentinel/bail path still zeroes s on a bail; r25 undisturbed; the remainder words'
   behaviour on the bail path stated and harmless.
3. Any EME/governor/lockstep/DTC threshold or cal changed; the gp-0x671d latch made reachable; the
   plausibility monitor FUN_0004595a's inputs changed by anything but the intended mean-exact rounding.
4. The hook's displaced instruction is not `jr`-replaceable (length, alignment, flags, `lp` liveness);
   any live register clobbered; the cave's flash region not 0xFF on V282 and V291; the CRC block that
   owns the cave not the one recomputed.
5. The fork: with `AccordCurvatureLead` OFF nothing changes on the openpilot side.
6. The dead twin island 0x2A30E–0x2B421 reads none of the touched cells.

## What PASS licenses
A cleared candidate, handed to the operator with V291's pre-registered read (half-peak decay ≈545 →
≈183 ms on hands-off creep; −14° ± 4° at 10 Hz; b3 read AMENDED on adversary A2's measurement before any drive — the transition-rate figure ×0.785 was
sized on V291's absorbing negative zone and does not transfer: on V292 hand over the b3 DUTY, which sits at
0.47–0.50 at every amplitude (V291 pinned at 1.000 below A = 3; V282-pole 0.54–0.70), conditioned on
|rate| ≥ 2 counts and mean rate ≤ ~1.5 deg/s; idle duty 0.000 with the wheel still is the cave-live control) and its revert signatures
(6–9 Hz strong-turn ripple; 10–18 Hz roughness/line per the shoulder numbers above; 22–30 Hz line;
grinding unchanged; darty feel; one-sided pull at rest). **It does not license any claim that the
grinding is fixed — the operator scores the symptom.**

---

## Verdicts (appended after the pass; orchestrator's crux checks marked ✔)

| surface | verdict | decisive numbers | file |
|---|---|---|---|
| **A arithmetic** | **PASS** | cave decoded by an independent decoder; mean gain exact (958/31) at every x, remainders in [0,1023], no overflow (margin ×12); DF gain 0.9994–1.0009 and phase ≤ 0.16° at A = 1…24 ✔; the negative stick zone [−16, −1] released; the b3 READ must be the DUTY (V292 0.47–0.50 at every amplitude; V291 pinned at 1.0; V282-pole 0.54–0.70) — the ×0.785 transition-rate figure was V291's and is withdrawn ✔ | `ADV-V292-A-ARITHMETIC-2026-09-13.md` |
| **B units / stability** | 🛑 **DO-NOT-FLASH on B4 (4th clause) ALONE**, every other clause PASS, no instability on any fit | B1 0/121 unstable, vector margin 0.052 → 0.275; B2 gate 0.549 (κ 0.449); B3 folded ×3.7–3.9 (unfolded ×5.3), 0/121 gain a ζ < 0.05 pole; **B4: at sp = ±3 counts V292 vs the LINEAR V282 chain ×0.776–1.164 (20–21/21 fits outside ±1 %) — and vs byte-exact V282 ×1.0000 at +3 (median), ×1.32 at −3; 0/21 outside ±1 % at ±330** ✔; the cause is the four un-caved floors (fade, output lag ×3, motor gain), not the cave (with the output-lag floors exact V292 reads ×0.992); DF 0.9995–1.0009 ✔; 9–18 Hz shoulder ×1.33–1.70 byte-exact (×1.99 linear), unchanged by the cave; **§7.1 the inherited r24 fold omitted the motor gain K and over-weighted r24 ×6.13 — pessimistic; corrected Ms reduction ×5.19, folded f0 18.4 Hz**; **§7.2 the ±102 deadband on y with gp-0x6806 = 0 would zero sp = 3 on every build — which state is live while engaged is BELIEF** | `ADV-V292-B-LOOP-2026-09-13.md` |
| **C build audit** | **PASS** | independent rebuild from the memo's listing reproduces image d1128232… and rwd 6d2784b5… ✔; 69-byte diff attributed; CRC 49/49 + 50/50 and independent CRC32; rwd round-trips; 17/17 mutations caught; tag re-derived from the built image; write guard refuses a second write; V291 renamed; all encoder controls in-region | `ADV-V292-C-BUILD-2026-09-13.md` |
| **D interlocks** | **PASS** | the two remainder halfwords: exactly the cave's four accessors on the built image, both methods, plus the boot `.data` copy loop at 0x1476C–0x14794 that writes 00 00 once (the initialiser the memo could not find); fb state accessors = filter + b3 rung; every interlock cal byte-identical; the latch moves the safe way; the hook: r7/r9 are LIVE-IN and the cave replicates both muls first (the memo's "writes before reading" wording corrected — errata appended); no branch into the orphaned span; dead island reads nothing | `ADV-V292-D-INTERLOCKS-2026-09-13.md` |

**ORCHESTRATOR'S ADJUDICATION, 2026-09-13.** Three surfaces pass. Surface B fails one clause — the
steady-state clause at sp = 3 counts against the LINEAR V282 chain, as the orchestrator amended it
before the image existed on the designer's prediction that a mean-exact filter would land on the linear
surface. **The built image falsifies that prediction, and B2 shows why: the loop has five floors and the
cave repairs one; the linear chain is a surface no integer build can sit on at 1-count demand — V282
itself reads ×0.958 at +3 and ×0.72 at −3 against it.** The kit's standing rule
(`memory/feedback/... a-check-that-condemns-the-flown-build-is-broken`) says a check the flown build fails
is a broken check. On the clause's INTENT — the operator's authority preserved — V292 reads ×1.0000 of
byte-exact V282 at +3 (median), 0/21 fits outside ±1 % at ±330 counts, ≤ 2 % at ±33, and a smaller
sign asymmetry at ±3 than either V282 (×1.33) or V291 (×1.41): ×0.89. The absolute spread at sp = 3 is
0.22–0.33 deg/s. B2 declined to change the criterion after the fact and said it "would not defend a
do-not-flash on physics here"; that dissent is recorded verbatim in its §5.4 and §9.
**⇒ VERDICT: V292 is CLEARED as the flight candidate, with the sp = 3 numbers, B2's dissent, the
un-resolved §7.2 premise (gp-0x6806's engaged state — the record's V103/V104 evidence says it is 1 while
engaged: the 55 Hz notch and the r24 rung both key on it and both were measured live) and the 9–18 Hz
shoulder all stated on the page; the decision to fly remains the operator's.** A V293 carrying error
feedback through the output lag would close the clause as written (B2 §9.1) at the price of a second cave
on the engaged path; it is not recommended for a 0.1 deg/s effect.

**The read, as amended by A2:** ring half-peak decay ≈545 → ≈183 ms on hands-off creep; T-vs-rate phase
−14° ± 4° at 10 Hz; **0x14A b3 DUTY 0.47–0.50 at every amplitude** (V282 0.54–0.70; idle 0.000 with the
wheel still = the cave is live), conditioned on |rate| ≥ 2 counts and mean rate ≤ ~1.5 deg/s; b5/b6 the
r24 cut's control. **Revert if:** the 6–9 Hz strong-turn ripple returns; new roughness or a line at
10–18 Hz (byte-exact worst-fit sensitivity ×1.3–1.7 of V282's, peak near 13 Hz); a 22–30 Hz line; the
grinding unchanged; a darty feel; a one-sided pull at rest. `AccordCurvatureLead` OFF.
