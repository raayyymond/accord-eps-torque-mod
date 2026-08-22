---
name: reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed
description: "Operator's compensator hypothesis (a closed loop regulates out assist-lane edits) CONFIRMED STRUCTURALLY -- gp-0x6ad4 (PID output, FUN_0003a382) and EVERY hand-feel lane (gp-0x6b86 biquad, gp-0x6b26 friction, gp-0x6bbe boost, gp-0x6bd0 damper, AND r24/r26 via iVar21/iVar16->gp-0x6adc/gp-0x6ada) are literal sibling addends in FUN_0003aa2c's sum, decompiled fresh. The reference gp-0x6ad6 (FUN_00037fe6, also decompiled fresh) is built from 8 DIFFERENT (mostly LKAS-derived) signals, disjoint from every one of those lanes. BUT the mechanism at 6-9Hz specifically is NOT quiet rejection -- the 2026-08-21 on-car loop-ID (route 0x85/0x95) found 2.28x closed-loop AMPLIFICATION, gain margin 1.2-1.6x from instability. Ties together with a frequency-dependent lane:sum cancellation law (4:1 @6-9Hz -> 1.68:1 @21-22.5Hz) that retrodicts why V62/V88 worked and nothing at 6-9Hz ever has. ON-CAR CONFIRMED, ADDENDUM 3: V104 (c4 x1.85, an 85% DC raise on gp-0x6b86, delivered undiluted per fresh disassembly) flew route a4 and produced ZERO felt change and ZERO symptom change -- the structural mechanism now has a controlled on-car demonstration, not just code + an unrelated loop-ID. ALSO: Kp/Ki/Kd (0xC6B26/0xC6B12/0xC6AE6) identified as VIRGIN cal-only PID gains, Q10, LERP on gp-0x6ac0 -- Kp x2 buys only 1.13x (not-felt boundary), x4 rails 92%; the adjacent 0xC6450/0xC644A branch-smoothing poles were flown/falsified but scored on 15-26Hz so their nulls do NOT transfer to the gains themselves."
metadata:
  type: reference
---

# The compensator hypothesis — structural confirmation + why 6-9Hz specifically is amplification, not rejection

Traced 2026-08-22, task `compensator` (team-lead brief: operator proposed a closed-loop steering-feel
tracker regulates out assist-lane edits, retrodicting the kit's 60-build record of low-frequency nulls).
Full report sent to team-lead via SendMessage (2 messages: early crux answer, then full 6-item report).

## [EVIDENCE, fresh decompile this session] The summing junction — every hand-feel lever is a sibling addend

`FUN_0003aa2c` (aggregator, writes `gp-0x6b94`/`gp-0x4ce0` shadow pair), decompiled fresh:
```c
iVar19 = iVar9 + iVar19
  + gp_0x6ad4 * gated(<=0x2800)   // PID OUTPUT (FUN_0003a382)
  + gp_0x6b26 * gated(<=0x400)    // friction/inertia
  + gp_0x6bbe * gated(<=0x800)    // boost
  + gp_0x6bd0 * gated(<=0x800)    // damper
  + gp_0x6b86 * gated(<=0x3000)   // THE BIQUAD (V103/V104's lever, FUN_000352b4's output)
  + iVar21 + iVar16;               // <- r24/r26: function's OWN tail stores these to
                                   //    gp-0x6adc / gp-0x6ada respectively
iVar14 = FUN_00036682();  iVar14 += iVar19;
// clamped +-0x2800, stored gp-0x6b94 / gp-0x4ce0
```
**NEW, not previously stated this explicitly in the record: r24/r26 are literal siblings of gp-0x6ad4 and
gp-0x6b86 in the SAME expression** (previously r24/r26 were known to write gp-0x6ada/gp-0x6adc as a
"mirror," but this decompile shows those are the SAME `iVar21`/`iVar16` locals summed into the junction,
not a separate copy). ⇒ every hand-feel lever this kit has ever tried (r24/r26 V62/V65/V67/V68/V88/V71c,
damper V74-V83a, friction V89, boost, biquad V103/V104) sums at ONE junction, alongside the torque-tracking
PID's own corrective output.

`FUN_00037fe6` (reference producer, writes `gp-0x6ad6`), decompiled fresh:
```c
iVar4 = -gp_0x6b4a (gated +-0x6400, unconditional)
if (gp_0x67ab != 1):
  iVar4 += gp_0x6bc2*w + gp_0x6b60*w + gp_0x6b2a*w + gp_0x6bce*w + gp_0x6b6e*w + gp_0x6bbc*w
         + gp_0x6b70*w        // weights byte-confirmed =1 in prior sessions, not re-verified by me
uVar3 = speed-LERP(gp_0x69aa)  // flat 1024=unity at stock, per prior sessions
gp_0x6ad6 = clamp((iVar4*uVar3)>>10, +-0x6400)
```
None of these 8 terms is `gp-0x6b86`, `gp-0x6b94`, `gp-0x6b98`, `gp-0x6ad4`, `gp-0x6bbe`, `gp-0x6bd0`, or
`gp-0x6b26`. Matches prior tracers' claims exactly; this session independently re-derived the CONTENT via
fresh decompile rather than re-running their byte scans.

⇒ **Structural verdict: every hand-feel lane is a DISTURBANCE injected at the junction, not part of the
loop's REFERENCE.** The reference-forming function is architecturally blind to them; the loop only reacts
to their PHYSICAL effect via the torque sensor `gp-0x4f60`.

## [EVIDENCE, fresh disassembly this session] Call order and gating, `FUN_0002214a`

`disassemble_function(0x2214a)`, full function, confirms (addresses mine, this session):
```
0x22200  FUN_00041464   rate estimator -> gp-0x6abe/6ac0        [gate r23=0xd30]
0x22676  FUN_00038148   Path-2 mixer -> gp-0x374c, gp-0x6b70     [gate r28]
0x22696  FUN_00037fe6   REFERENCE PRODUCER -> gp-0x6ad6          [gate r28]
0x226a0  FUN_0003a382   THE PID -> gp-0x6ad4                     [gate r22=0xc30]
0x227b4  FUN_000352b4   THE BIQUAD -> gp-0x6b86                  [gate r26]
0x228cc  FUN_00036c12   friction/inertia -> gp-0x6b26            [gate r22]
0x2291e  FUN_0003aa2c   THE AGGREGATOR -> gp-0x6b94/gp-0x4ce0     [gate r22=0xc30, SAME r22]
0x2293a  FUN_0004503c   GOVERNOR -> gp-0x6ace                    [gate r23]
0x22984  FUN_000456a4   comp-add -> gp-0x6acc                    [gate r23]
0x229ce  FUN_00042af8   SHAPER -> gp-0x6b08                      [gate r23]
```
**Two new structural facts, confirmed directly (not relayed) this session:**
1. `FUN_0003a382` (PID) and `FUN_0003aa2c` (aggregator) test the LITERAL SAME register `r22`
   (`0x2269a: andi 0xc30,r25,r22`, reused unchanged at `0x22916`) — they cannot run independently; whenever
   one is gated off, so is the other.
2. The biquad (`0x227b4`) executes AFTER the PID (`0x226a0`) but BEFORE the aggregator (`0x2291e`) in the
   SAME tick — both `gp-0x6ad4` and `gp-0x6b86` are fresh, same-tick values when they meet at the junction.
   No cross-lane skew.

1kHz rate of `FUN_0002214a` itself is carried from project memory (`control-task-tick-confirmed-1khz.md`:
OSTM0 timer + STEER_STATUS=4 dwell) — NOT independently re-timed by me this session, only the call
STRUCTURE inside it.

## [BELIEF, structural] A genuine integrator sits at this junction — a second, lane-agnostic DC mechanism

Stage B of `FUN_0003a382` (from `reference_accord_fun3a382_pid_structure_...md`, prior session, not
re-derived by me): `I[n] = I[n-1] + (Ki*err)>>10`, Ki=98/1024 flat — a true non-leaky discrete integrator.
Textbook infinite DC loop gain before saturation ⇒ structural DC/slow rejection of ANY junction lane,
independent of and additional to any single lane's own coincidental H(0)≈1 (e.g. the biquad's 1.000034).
🛑 CAVEAT (evidence-grade from prior tracing, not re-verified by me): rejection is linear only while
UNSATURATED — `AUTH≈227ct at 6km/h` vs measured median override torque 2235ct means the loop is often AT
ITS RAILS in the exact hands-on regime used to judge feel, at which point anti-windup pins P+I and it
becomes a bang-bang relay, not a linear rejector.

## [RELAYED, high-confidence, NOT run by me] The on-car reframe — 6-9Hz is AMPLIFICATION, not rejection

`docs/HANDOFF-2026-08-21-route9e-and-the-loop-is-the-cause.md`, routes `0x85`/`0x95` (4x/8x gain step):
```
|kG| = 0.630 [0.512,1.001]     gain margin ~1.2-1.6x from instability
A = 1+P = 0.440 @ +25.0deg     closed-loop 1/|A| = 2.28x AMPLIFICATION [1.51, 9.4]
Z0 = 2792 @ -92.45deg          near-lossless passive plant
```
⇒ 100% of measured `Re(Z)=-3761` at 6-9Hz is LOOP-GENERATED (near-instability), not a passive resonance
being excited, and NOT the loop quietly rejecting things — the OPPOSITE, it amplifies right there.
🛑 **Reconciling this with the compensator idea**: NOT a contradiction. The SAME session found the
junction is a **4:1 near-cancellation at 6-9Hz** (individual lanes larger than their sum, coh²(T,sum)=0.279
vs coh²(T,lane)=0.80-0.89), falling to **only 1.68:1 at 21-22.5Hz**. This is a waterbed pattern: strong
mutual lane cancellation (rejection-like, for single-lane edits) exactly where the aggregate loop sits
closest to instability. Both effects share a cause — several lanes (PID included) react to the SAME
sensed-torque feedback and partially cancel each other, while the aggregate is close to its stability
boundary at that exact frequency.

**Convergent check**: the code-side small-signal PID sign analysis (`gp-0x6752=-1` resolved 3 ways, prior
session) finds P+I net PUMPING (+0.122) at 6-9Hz, D the lone damper — directionally consistent with the
on-car amplification finding. Two independent methods agree on sign.

## Retrodiction — what this explains and what it doesn't

**Explains**: why NO junction-disturbance-class lever (r24/r26, damper, friction, boost, biquad) has ever
moved the 6-9Hz ratchet (4:1 cancellation + near-instability swamps any lane-sized dose) — AND why V62/V88
(the kit's only 2 measured wins, both in the 18-22/21-22.5Hz grind-#1 band) DID work: same junction, but
only 1.68:1 cancellation there, a materially more direct path.

**Does NOT explain (honestly unresolved)**: the ~42Hz (grind #2/#3) null specifically. CAN 427 samples at
~49.8Hz (Nyquist ~24.9Hz) ⇒ **42Hz content aliases/folds — this kit's primary telemetry channel is
STRUCTURALLY BLIND there** (`STATE.md` 2026-08-22 instrument-defect #4: fold ratio 0.23-2.57 at 20-24Hz).
Extrapolating the cancellation law's falling trend (4:1->1.68:1 from 6-9 to 21-22.5Hz) makes it MORE LIKELY
(belief, not measured — only 2 points exist) that cancellation is weaker still at 42Hz, arguing against
"loop quietly ate it" and toward a measurement gap or a non-firmware (mechanical/perceptual) explanation —
but this is an extrapolation past the two actually-measured points, not a third measurement.

V89 (friction K1 x2, structurally REFERENCE-side via gp-0x6bfe->gp-0x6b70->gp-0x6ad6, NULL) is the
interesting edge case: on a naive "edit the reference, escape rejection" theory it should have worked.
Likely explained by the SEPARATE, already-recorded `f'` compression mechanism (Stage-2 LERP slope falls
6.3x hands-on) rather than a refutation of the reference-side idea — but I did NOT re-trace whether K1's
specific contribution routes through the compressed stage this session; flagged as the concrete next step.

## Consequence for future levers
No new cal-only reference-side lever was identified this session with full address/blast-radius. The
gain-only V104->V105 plan already in motion (per STATE.md) is independently reinforced, not superseded:
gain is the one variable proven (same route 0x85/0x95 ID) to move |kG| itself, i.e. it acts on the
near-instability mechanism rather than fighting it from inside the junction.

## Related
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]] (project memory) — the downstream chain this
session's junction map sits upstream of. [[accord-friction-polarity-more-friction-is-more-assist]]
(project memory) — the gp-0x6ad6/reference framing this session confirmed structurally.
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]],
[[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]],
[[reference_accord_gp6ad6_eight_terms_and_the_reachability_budget]],
[[reference-accord-6to9hz-loop-is-pid-torque-tracker-phase-budget]],
[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]],
[[reference_accord_f0_dose_floor_and_common_path_structure_search]] — all prior-session material this
report leaned on without re-deriving; see them for the underlying frequency-response derivations.

---

## ADDENDUM 2026-08-22 (same session, round 2) — Kp/Ki/Kd identified+priced; the "gate2-pid" SQUEEZE citation
trail found (conclusions only, method NOT recoverable from disk); a −171.8° vs −17.2° phase puzzle

Team-lead escalated to: are `Kp`/`Ki`/`Kd` themselves cal-only loop-side levers (as opposed to the
disturbance-side lanes covered above)? Full answer sent to team-lead; durable facts below.

### [EVIDENCE, 3 methods this session] Kp/Ki/Kd are tp-relative cal cells, Q10, LERP-Y[0] on `gp-0x6ac0`
```
Kp: header 0xC6B1C, X=[0,300,2000,4000], Y@0xC6B26=[256,256,225,153]   (stock 256, NOT flat)
Ki: header 0xC6B08, X=[0,400,1500,3000], Y@0xC6B12=[98,98,98,98]       (stock 98, flat)
Kd: header 0xC6ADC, X=[50,400,1500,3000], Y@0xC6AE6=[2048,2048,2048,2048] (stock 2048, flat)
```
Confirmed via fresh `decompile_function(0x3a382)` (whole PID, all 3 LERP walkers present, byte-exact
addresses) + fresh `read_memory` on all 3 headers (raw bytes match the `{count,X[],Y[]}` layout exactly)
+ `grep build_v*_tva.py` (V100-V104 all carry these as `FROZEN` cells commented "VIRGIN").

🛑 **`get_xrefs_to(0xC6B26)` returned "No references found" — a LIVE reproduction of the documented
Ghidra tp-relative misleading-zero trap.** My own decompile shows the LERP read once, matching a prior
tracer's 2-method census (1 reader each, all inside `FUN_0003a382`, 0 writers — flash constants).

### [EVIDENCE] Flight history — the GAINS are virgin; two DIFFERENT adjacent cells were flown and nulled
`Kp`/`Ki`/`Kd` themselves: **byte-identical to stock on every image V43→V104. Never tried.**
Adjacent-but-different cells (each gain's OWN per-branch smoothing EMA pole, not the gain): `0xC6450`
(P-branch pole, V46 1024→32, FALSIFIED on 21Hz vibration) and `0xC644A` (D-branch pole, V43/V49
1024→32/64, FALSIFIED on 15-26Hz) — **both scored on bands other than 6-9Hz, so neither null transfers**
to a 6-9Hz question about the gains themselves.

### [RELAYED — method NOT recoverable] The "SQUEEZE" (Kp x2=1.130x on the not-felt bound; x4=1.720x but
92% rail duty hands-on; Kd sign flips on only 53.4° of an unmeasured plant phase) traces to a cited
sub-analysis `gate2-pid`, referenced in `docs/BUILD-LINEAGE.md` and `docs/_v101_arc_map.md` §5.2g-§5.2k
(2026-08-14, V100 session). **Searched `docs/GATE2-*.md` and every HANDOFF — the full derivation is NOT
on disk, only its conclusions survive, quoted verbatim in the arc_map.** Predates the 2026-08-21 route
0x85/0x95 loop identification by a week.

### [EVIDENCE, independently reproduced from scratch] The P-branch saturation arithmetic checks out
```python
P_state = ((Kp * ERR) >> 10) * 32     # Kp=256 stock, straight from my own fresh decompile
# ERR=2000 -> P_state=16000   <- MATCHES arc_map's cited "16,000 at e=2000" EXACTLY
# solving P_state=7264 (the cited anti-windup bound) => ERR ~= 908 counts
```
P alone saturates the internal ceiling at ERR≈908, well under the measured median override torque
(2235) — independent, first-principles corroboration of "92% rail duty hands-on" even though gate2-pid's
own script could not be found.

### [EVIDENCE] `H_PID(f)` computed fresh, cross-validated exactly against the existing record
```python
H_P(f)=Kp/1024;  H_I(f)=(Ki/1024)/(32*(1-z^-1));  H_D(f)= cross-validated closed form (kd_pid memory)
H_PID(f) = (H_P+H_I+H_D) * gp_0x6752   # gp_0x6752=-1
```
Pre-polarity at stock Kp=256 reproduces `reference-accord-6to9hz-loop-is-pid-torque-tracker-phase-budget`'s
table to 2 decimals exactly (6/7.79/9 Hz: 0.2529∠−0.89° / 0.2565∠+8.24° / 0.2617∠+13.29°) — the mirror
is correct. With polarity: **`H_PID(7.79Hz) = 0.257∠−171.8°`** — only 8.2° from the classic relay/
limit-cycle −180° condition.

### 🛑🛑 [OPEN, IMPORTANT] −171.8° (isolated PID) vs −17.2° (measured aggregate loop) — unreconciled
Re-deriving team-lead's own `A=1+P=0.440∠+25°` gives `L_total(7.79Hz)=1−A=0.630∠−17.2°` (matches
`|κG|=0.630` to 3 decimals — confirms I have the convention right). **This is nowhere near −180°.** The
isolated PID sits close to the relay condition; the measured AGGREGATE loop does not. Two live
explanations, NEITHER checked this session: (a) the other ≥4 sensed-quantity-dependent lanes at the same
junction (`gp-0x6bbe`∝−K1·col.rate, `gp-0x6b26`∝motor-rate sign, r24/r26∝d(torque)/dt, the biquad)
dominate the aggregate phase and rotate it away from the PID's own character; (b) the −17.2° identification
was measured in a regime where the PID was NOT railed (routes 0x85/0x95's hands-on fraction is unknown to
me), and the picture changes once it rails. **Do not treat a PID-isolated S(f) as reproducing or refuting
the measured 2.28x loop amplification — the attribution-fraction ("q") problem is unresolved, same class
as the kit's prior `0xC63AC`/`gp-0x6b26` isolated-stage failures.**

### Sensitivities at 7.79Hz (isolated PID, NOT full-loop d|A|/dK — see caveat above)
```
d|H_PID|/dKp ~= +0.000966/count   (P dominates ~7:1 over I+D combined at this operating point)
d|H_PID|/dKi ~= -0.000074/count   (negligible even before saturation -- Ki's own AC role here is small)
d|H_PID|/dKd ~= +0.000008/count   (small on magnitude; LARGE on phase/sign: Kd sign-flip swings arg -172->+147)
```

### Open items
1. Hands-on/override fraction of routes `0x85`/`0x95` — decides whether the −17.2° identification is even
   the right regime to reason from.
2. Per-lane attribution (`q`) — unmeasured; the sign(gp-0x6ad4) vs other-lane comparator proposed above
   would help, a magnitude-ratio channel would help more.
3. `FUN_0003a382`'s full anti-windup/AUTH topology — my fresh decompile shows 3 MORE LERPs beyond
   Kp/Ki/Kd (indexed on `gp-0x6bda`, `gp-0x6a5e`, `gp-0x6966`) feeding a ceiling/ANTI-WINDOW chain,
   matching the AUTH formula already on record but not fully hand-decoded this session — needed for any
   real describing-function/relay analysis in the railed regime.

---

## 🛑🛑 ADDENDUM 3 (same session, round 3+) — ON-CAR CONFIRMATION: V104 flew, and the junction-rejection
mechanism now has a controlled demonstration, not just structure

`c4` (`0xC60B4`, the biquad's overall gain, `FUN_000352b4`) was raised 0.81731→1.51202 (×1.850) in V104.
[RELAYED from team-lead/`feel-impact`, not independently re-derived by me this session] Fresh disassembly
established this is an **85% DC gain raise on `gp-0x6b86` (the driver-torque-to-assist feedforward)
delivered UNDILUTED** — the `gp-0x6b7e` pedestal is added *after* the biquad and is never scaled by `c4`,
so in steady driving ~100% of the lane is the `c4`-scaled term.

**V104 flew route `a4`. Operator's verbatim report:** *"I did not feel any [change in] normal, manual,
LKAS-disengaged OR LKAS-engaged steering feel."* / *"just as bad as any other 6x before it, I don't think
I could tell the difference."*

⇒ **An 85% raise on a major assist lane, delivered and verified undiluted, produced NO perceptible change
in steering weight and NO change in either symptom (grinding, ratcheting).** This is exactly what the
junction topology above predicts: `gp-0x6b86` is a disturbance at the summing junction; the reference
`gp-0x6ad6` is architecturally blind to it; the loop measures the physical column torque `gp-0x4f60` and
regulates the difference back out. **The structural claim ("junction-level lanes are rejected") now has a
controlled on-car demonstration on THIS EXACT mechanism, not just the unrelated route 0x85/0x95 loop-ID.**

🛑 **Scope of what this proves — do not over-extend it.** This confirms rejection for a **DC/broadband,
undiluted, lane-level** perturbation. It does NOT by itself confirm rejection at 6-9Hz specifically (that
band is separately established as AMPLIFICATION, not rejection — see ADDENDUM 1 above) — the two are
compatible (waterbed pattern) but are different frequency regions of the same `S(f)`-like curve. It also
does not bear on **sensor-path** contamination (upstream of the junction) — see
[[reference_accord_gp6b4a_is_speed_derived_and_c616c_is_a_fault_monitor_not_decoupler]] for that
architecturally-distinct question (no decoupler found; both candidate mechanisms refuted this session).

**Practical consequence, reinforced**: any future lever proposal that sums INTO this same junction
(`gp-0x6b94` via `FUN_0003aa2c`) — a new damper term, a new friction term, a rescaled existing lane — should
be treated as presumptively REJECTED at DC/broadband, on both structural grounds (this file) AND now a
direct on-car result (V104), unless it specifically targets the 6-9Hz near-instability band or acts on the
reference/sensor path instead of the junction.

---

## ADDENDUM 4 — `Kd` priced at 26 Hz (the OTHER loud mode: 26.0-26.8Hz, 17-32x stock, dominant band,
closed-loop, the ONE band V104 didn't move), independent second derivation per team-lead's request

Team-lead identified a SECOND, louder, previously-untouched mode at 26.0-26.8Hz and asked for an
independent (not-reconciled-with-`ceiling-trace`) pricing of `Kd` there, building on this file's own
`H_PID(f)` model and the −171.8°-vs−17.2° puzzle. Full numbers sent to team-lead; durable facts below.

### [EVIDENCE, same validated `H_PID(f)` model as ADDENDUM 2] D dominates ~79% of `|H_PID|` at 26Hz
```
f(Hz)   |P|     |I|     |D|     |sum|    D-fraction
7.79    0.2500  0.0611  0.0979  0.2565   38.2%
26.40   0.2500  0.0181  0.3314  0.4187   79.1%
```
`d|H_PID|/dKd` is **16x larger at 26.4Hz (0.000129/ct) than at 7.79Hz (0.000008/ct)**. A `Kd` dose sized
to move 26Hz meaningfully (×1.5-2.0) moves 7.79Hz proportionally **5.5-7.8x less** — favorable ratio IF
D's established 6-9Hz damping classification (from the `gp_0x6752`-corrected analysis) transfers to 26Hz,
which is UNVERIFIED (that classification depends on the plant's own phase, which is frequency-dependent).

### [EVIDENCE] Isolated-PID phase moves AWAY from the -180° relay condition as frequency rises, not toward it
`7.79Hz: -171.76° (8.2° from -180°) → 21.7Hz: -137.21° → 26.0Hz: -132.17° → 26.8Hz: -131.39° (48.6° from
-180°) → 42Hz: -122.14° (57.9° from -180°)`. Answers "does the relay condition get closer at 26Hz" — NO,
for the ISOLATED PID specifically. Does not resolve the AGGREGATE loop's phase there (unmeasured; the
same `q`-attribution gap as ADDENDUM 2, now at a different frequency).

### 🛑 [EVIDENCE, computed fresh — a real data point AGAINST the Kd hypothesis, not just silent on it]
`0xC644A` (D's OWN smoothing EMA pole, stock=1024=unity) at V43's flown dose (1024→32):
`|H_EMA(26.4Hz)| = 0.188` (**-14.5dB, an 81% CUT to D's content at exactly this band**) — flown and
FALSIFIED (moved nothing at 15-26Hz). A pole and a gain act differently in principle (frequency-selective
attenuation vs uniform multiply), so this is not a clean proof a `Kd` RAISE would also fail — but cutting
D's 26Hz content 81% and seeing nothing is a real, on-topic prior result, not a formally-adjacent one.

### 🛑 Standing caveat that applies to ANY 21-26Hz phase claim, mine included
The 2026-08-22 `H(s)` handoff's own open item #1: `|Z|` rolls off un-modelled above ~13Hz — *"if `tq` is
internally low-passed there, every kit `|Z|` above ~10Hz inherits it — including the 21-24Hz work."*
Treat any 26Hz loop-phase number as provisional until that's closed.

### Verdict: structurally interesting, NOT cleared for safety
D genuinely dominates at 26Hz and the dose-sizing cross-check is favorable IF the mechanism works at all —
but the railed/relay safety question (ADDENDUM 2's `AUTH≈227ct` vs override 2235ct finding) is unresolved,
and the `0xC644A` null is real evidence against, not merely uninformative. Would need `L_total(26Hz)` (a
route-0x85/0x95-style system-ID centered on this band, or the mechanical plant's own phase there) and the
anti-windup/relay describing-function analysis before this is buildable.
