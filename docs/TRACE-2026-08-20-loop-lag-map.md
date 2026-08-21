# TRACE 2026-08-20 — the closed-loop lag map, and why no lag-only lever prices out for V104

**Task**: enumerate and quantify every phase-lag / delay element in the EPS closed loop, at 8/20/23/26 Hz,
and rank levers that could push `f0` (the `Re(Z)` zero-crossing) below the ~20-23 Hz mechanical mode
while V104 runs the 8x LKAS gain (`0xC6CD0`=7128). Program: `code.bin` (stock, GhidraMCP, read-only).
`gp=0xFEDF8000`, `tp=0xBF000`. All cal values below were read live this session
(`read_memory`/direct Python LE byte read of `stock_fw_dump/code.bin`) unless marked otherwise.

This is a SYNTHESIS session: most of the underlying facts already exist in this kit's memory,
scattered across ~15 files. Three items are NEW this session (marked EVIDENCE, fresh): the
`FUN_00041464` 1kHz rate correction, the `0xC6382`/`gp-0x381c` filter's structure, and the
100Hz-to-1kHz ZOH characterization on the damper/boost lanes.

## 0. Verified stock cal values (this session, `read_memory` + independent Python LE read, agree)

```
C63AC=102  C40D0=408  C40D4=573  C40D6=246  C40D8=3686  C63D2=6  C644A=1024  C6450=1024
C63EC=992  C63EE=507  C649B=0    C64FA=5    C6382=41    C6C42=4
C6ADC=4(hdr) C6AE6=2048(Kd Y0)   C6B08=4(hdr) C6B12=98(Ki Y0)   C6B1C=4(hdr) C6B26=256(Kp Y0)
C6200=8192  C6194=3   C6196=0   C63CC=0   C61B2=512  C61B4=512  C646C=891  C6CD0=65535(0xFFFF, stock-unused)
C6206=512   C6208=205  C520C=5(hdr)
biquad c1..c4 (0xC60A8/AC/B0/B4) = -1.5372, 0.63462, -1.8808, 0.81731
```

## 1. Execution model — confirmed, one correction made this session

- **Control task `FUN_0002214a` = 1 kHz** (OSTM0-confirmed, established prior sessions).
- **The `andi 0x830/0xc30/0xd30` blocks are STATE bitmasks (one-hot on `gp-0x67fa`), not phase
  dividers.** Reachable set is `{11}` alone in practice, and bit 11 (`0x800`) is set in all three
  masks ⇒ every gated block fires every tick. [EVIDENCE, prior session]
- 🛑 **NEW THIS SESSION**: `FUN_00041464` (the rate-estimator EMA producing `gp-0x6abe`/`gp-0x6ac0`)
  is called through a **third, earlier `andi 0xd30` gate** at `0x221f8`
  (`andi 0xd30,r25,r23` / `be 0x22204` / `jarl 0x41464`), fresh-disassembled this session
  (`disassemble_bytes 0x221e0-0x2223e`, dry_run). Same mask, same `{11}`-reachable conclusion ⇒
  **this function also runs unconditionally at 1 kHz.** This CORRECTS
  `reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain.md`, which computed this EMA's
  phase at `fs_eff=312.5 Hz` (a "5/16 phase-gating" reading) — that reading is the exact class of
  state-mask misparse that `reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md`
  already corrected for the neighbouring blocks, just not yet applied to this specific function.
  **Recomputed at the corrected 1 kHz rate the lag is much smaller** (see table).
- **FOC/PWM carrier = 4.000 kHz** (TSG20, PCLK=40MHz undivided, period 5000 ticks ×2). ADC-complete
  ISR and the resolver-angle differentiator (`FUN_00068f52`) sample at 4 kHz, not the older 8-16kHz
  belief. [EVIDENCE, prior session, `reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected.md`]
- **Task 5 (`FUN_00022ca0`) = 100 Hz**, independently confirmed via a live TCB-table read this
  kit's history (`reference_accord_task5_100hz_live_verified_full_producer_census.md`) — carries the
  base-assist damper (`FUN_00034350`→`gp-0x6bd0`) and boost (`FUN_00034a72`→`gp-0x6bbe`). These two
  lanes are summed into the 1kHz aggregator (`FUN_0003aa2c`) every tick but only UPDATE at 100Hz —
  **a genuine ZOH boundary** (see table, new this session).
- **One pure transport tick is proven from the call order inside `FUN_0002214a`**: `FUN_0003bc20`
  (MODEL) → `FUN_00026c80` (REQUEST/LKAS mixer) → `FUN_00038148` (reads all three, Path-2) →
  `FUN_00037fe6` (reference) → `FUN_0003a382` (PID) → ... → shaper writes `gp-0x6b98`, which
  `FUN_0003b8f6` reads back at the TOP of the NEXT tick. Every other hop is same-tick.
  [EVIDENCE, prior session, `reference_accord_ivar6_register_only_and_the_1khz_call_order.md`]
- **CAN transport (100 Hz TX base tick) is EXOGENOUS to this loop.** The resonance is measured
  hands-off under a roughly steady LKAS setpoint; the CAN-sourced command sets the PID's REFERENCE,
  not a term in the sensor-feedback path. `gp-0x6bfa` (REQUEST) does **not** echo the raw LKAS
  command (different struct field, confirmed by decompile — `reference_accord_v101_v102_resonance_mechanism_and_biquad_direction.md` §1). Excluded from the closed-loop lag budget on this basis.

## 2. The lag/phase table (Python mirror of the exact decompiled recursions, fs=1000Hz unless noted)

```python
def ema_response(alpha, f, fs=1000.0, extra_ticks=0):
    w = 2*math.pi*f/fs
    den_re = 1 - (1-alpha)*math.cos(w); den_im = (1-alpha)*math.sin(w)
    mag = alpha/math.hypot(den_re, den_im)
    phase = -math.degrees(math.atan2(den_im, den_re)) - 360.0*f/fs*extra_ticks
    return mag, phase
```
All values below computed with this exact function (verified: reproduces every pre-existing
cross-checked figure in this kit's memory to within 0.5° / 0.1dB — e.g. `0xC40D0` at 8Hz here
=-24.18°, memory's 7.79Hz figure=-23.63°; `0xC63D2` at 8Hz here=-81.89°, memory's 7.79Hz
figure=-81.8°; dead biquad at 20Hz here=-28.45°/-1.12dB, memory's 21Hz figure=-30.0°/-1.25dB).

| element | fn / addr | cal, value | 8 Hz \|H\|∠phase | 20 Hz | 23 Hz | 26 Hz | DC gain | editable? blast radius |
|---|---|---|---|---|---|---|---|---|
| resolver diff + 2-tap boxcar | `FUN_00068f52`, 4kHz ISR | none (structural) | 1.000∠+89.3° | 1.000∠+88.2° | 1.000∠+87.9° | 1.000∠+87.7° | 0 (pure diff) | NO — fixed hardware-rate structure |
| rate EMA `gp-0x6abe`/`6ac0` | `FUN_00041464`@`0x41464`, **1kHz (corrected this session)** | `0xC643C`=37, Q7 (α=0.2891) | 0.989∠−7.0° | 0.939∠−16.8° | 0.922∠−19.1° | 0.903∠−21.2° | 1.0 | cal, 1 reader-class but **15+ downstream common-mode consumers** — DO NOT EDIT casually |
| MODEL cmd branch (×2) | `FUN_0003b8f6`@`0x3b94e` | `0xC40D4`=573/4096 | 0.900∠−34.1° | 0.591∠−72.6° | 0.522∠−79.5° | 0.461∠−85.5° | 1.0 | cal, virgin, 1 reader |
| MODEL friction EMA | `FUN_0003b8f6`@`0x3bb22` | `0xC40D0`=408/4096 | 0.902∠−24.2° | 0.641∠−46.6° | 0.588∠−50.0° | 0.541∠−52.7° | 1.0 | cal, paired w/ `0xC63AC` (bit-identical α) |
| Path-2 accumulator (+1 tick, Path-2 stale-by-one) | `FUN_00038148`@`0x38202` | `0xC63AC`=102/1024 | 0.902∠−27.1° | 0.641∠−53.8° | 0.588∠−58.2° | 0.541∠−62.1° | 1.0 (pure lead/lag pole) | cal, virgin — **REFUTED as a lever, see §4** |
| `gp-0x6b46` filtered term | `FUN_00036682`@?, reader `0x38210` | `0xC63D2`=6/1024 | 0.116∠−81.9° | 0.047∠−83.7° | 0.041∠−83.5° | 0.036∠−83.3° | 1.0 | cal — but confirmed structurally negligible at this band (`reference_accord_v101_v102...` §9c) |
| PID D-branch alone | `FUN_0003a382`@`0x3a85c` | `0xC6AE6`(Kd Y0)=2048/1024, α-pole `0xC644A`=1024=unity(passthrough) | 0.101∠+88.6° | 0.251∠+86.4° | 0.289∠+85.9° | 0.326∠+85.3° | 0 (structural, DC=0 always) | cal, virgin — pure near-90° lead at every f 2-35Hz |
| PID P-branch alone | `FUN_0003a382`@`0x3a7f6` | `0xC6B26`(Kp Y0)=256/1024, pole `0xC6450`=1024=unity | flat 0.25∠0° at all f (unfiltered) | — | — | — | 0.25 | cal, virgin — 0° phase at every frequency (static gain) |
| `gp-0x381c` IIR, STATIC candidate | `FUN_000352b4`@`0x359d8-e8` | `0xC6382`=41/2048 (Q11) | 0.373∠−66.7° | 0.159∠−77.3° | 0.139∠−77.9° | 0.123∠−78.3° | 1.0 | cal — **near-inert in practice, see §3** |
| `gp-0x381c` IIR, LERP/clamp ceiling | same, α clamped to 204/2048 | (=0.0996, bit-identical to `0xC63AC`/`0xC40D0`) | 0.902∠−24.2° | 0.641∠−46.6° | 0.588∠−50.0° | 0.541∠−52.7° | 1.0 | LERP table not decoded this session |
| dead biquad | `FUN_000352b4`@`0x35a28-64` | `0xC649B`=0 (DISARMED, all builds) c1..c4 fixed floats | 0.982∠−10.9° | 0.879∠−28.5° | 0.837∠−33.2° | 0.786∠−38.1° | 1.0 | cal (1 byte), gated on `gp-0x671a≥cal(0xC64FA)=5` — VIRGIN, V103-speced |
| 100Hz→1kHz ZOH, damper/boost lanes | task5→task1 boundary | structural (100Hz update) | 0.990∠−14.4° | 0.936∠−36.0° | 0.915∠−41.4° | 0.893∠−46.8° | 1.0 | NOT editable without moving task5's own rate |
| 1-tick pure transport | call-order proof | structural (1kHz) | 1.000∠−2.9° | 1.000∠−7.2° | 1.000∠−8.3° | 1.000∠−9.4° | 1.0 | NOT editable — architectural |
| LKAS-branch IIR (**exogenous, excluded**) | `FUN_00028ea6`@`0x2a1a0` | `0xC63EC`=992/1024, `0xC63EE`=507/1024 | 0xC63EC/EE DC=0.990, fc≈4.97Hz | — | — | — | 0.990 | **CONFIRMED not in the sensor-feedback loop — see §5, excluded from f0 budget in either direction** |
| governor slew | `FUN_0004503c` | `0xC6206`=512/tick=512,000ct/s | not a linear filter — nonlinear, amplitude-dependent (see §6) | | | | n/a | NOT a tunable pole |
| comp-add | `FUN_000456a4` | static nested LERP | not a filter — memoryless, zero dynamics | | | | n/a | NOT a tunable pole |
| soft-EME integrator | `FUN_00042af8` | `gp-0x3570` | sits at 0 whenever \|command\| stays inside the 5120-12288ct corridor/boost bound — contributes ZERO linear dynamics at the observed small-signal amplitudes | | | | n/a | anti-windup structure, not a small-signal filter |
| FOC current-loop PI | `FUN_00071272`, 4kHz | Kp/Ki not located | **[OPEN]** assumed small phase at ≤26Hz (current loops typically run decades above mechanical bandwidth) — **not measured, flagged not assumed-safe** | | | | ? | UNCHARACTERIZED |

## 3. `0xC6382`/`gp-0x381c` — new structure this session, and why it's near-inert in practice

Fresh `disassemble_bytes(0x358a0-0x35b1c)` this session, cross-checked against
`search_instructions(operand_pattern="7382")` (exactly 1 real hit: `0x358cc ld.hu 0x7382,tp,r2`,
inside `FUN_000352b4`; the other 3 raw hits are branch-target coincidences or a different
tp-relative address — `-0x7382` is `0xB7C7E`, not `0xC6382`).

```
0x358cc  r2 = cal(0xC6382) = 41                       ; STATIC candidate, held in a register
0x3593e  r8 = gp-0x6b62                                ; return-centre / end-stop value
0x35942-4a  r12 = (|gp-0x6b62| > 8192) ? gp-0x6b62 : 0 ; zero-gate idiom
0x35950  r12 = (r12 != 0)                              ; = gate-fired flag
0x35954-5a  r15 = flagA AND r12                        ; flagA from an earlier gp-0x6b7a comparison
0x3595e-359ba  ...LERP over a small table at tp+0x78fc.. keyed on r1, producing r11...
0x359be  r15 = (r8!=0) ? cal(0xC6382)=41 : r11(LERP)   ; the actual selector
0x359c2-d4  K = clamp(r15, 2, 204)                     ; Q11 coefficient, floor 2/2048, ceiling 204/2048
0x359d8-e8  state(gp-0x381c, 32b) += ((target<<7 - state) * K) >> 11   ; single-pole IIR, ALWAYS RUNS
```
**This is a genuinely LIVE, unconditional (no branch skips it) single-pole IIR** — distinct from the
DISARMED biquad that follows it in the same function (confirmed same arm gate,
`cal(0xC649B)==1 AND gp-0x671a≥cal(0xC64FA)=5`, re-derived fresh this session, matches
`reference_accord_v101_v102_resonance_mechanism_and_biquad_direction.md` §4 exactly).

🛑 **[BELIEF, structural]**: the STATIC 41 candidate is selected only when `|gp-0x6b62| > 8192` AND
`flagA`. This kit's own measurement (`memory/accord-return-centre-and-detent-dead-engaged.md`,
corrected polarity per `reference_accord_dwell_relay_polarity_is_arm_on_LARGE_...md`) found
`gp-0x6b62 ≡ 0` over 75,227 engaged frames. **⇒ in real engaged driving the STATIC 41 branch almost
never fires; the LERP branch is what's actually live.** I did NOT decode the LERP's X/Y knots this
session (table at `tp+0x78fc..0x790c`) — **this is an open item**, not a closed one: the coefficient
this filter *actually* runs at in practice is unmeasured, only its reachable range (2-204/2048, i.e.
0.001 to 0.0996) is established. Downstream, `gp-0x381c`'s further consumer inside this same
function was not fully traced this session (it does NOT feed `r10`, the biquad's forcing input,
per the same `0x35a28` trace) — likely feeds the same friction/hold combinator that ultimately
reaches `gp-0x6b86` (the aggregator's widest lane), per the dead-biquad memory's prior finding, but
this specific link is BELIEF, not re-verified this session.

## 4. The tuner's mental model, tested — and it's backwards for this firmware's own "tracker"

The brief's cited fix ("push the resonance to higher frequencies by reducing filtering/speeding up
the tracker") was already TESTED on the one element that best matches "the tracker" — `0xC63AC`,
the Path-2 accumulator. **A full closed-loop Bode sum (not just the isolated stage) found raising it
makes `Q` WORSE at every dose 150-300 tested, never better** — because in this firmware EVERY lag
element identified above is a single-pole LOW-PASS, so removing its lag necessarily WIDENS its own
passband (more HF gain right at the resonance), and this kit's one full-loop-closed test showed that
gain cost dominates the phase-margin credit once the loop actually closes.
[EVIDENCE, prior session `reference_accord_c63ac_full_loop_bode_sum_net_negative.md`, reproduced:
`0.875 × 1.38(mag ratio @21Hz) = 1.208 > 1` from gain alone, before any phase-shift modelling.]
**⇒ Speeding up any of the low-pass elements in the table above (raising their α) is the WRONG
direction by this kit's own closed-loop evidence, not merely untested.**

## 5. `0xC63EC`/`0xC63EE` — confirmed exogenous, excluded in EITHER direction

Traced the live LKAS command path end-to-end this session against
`reference_accord_live_lkas_command_path_and_c63ec_lowpass.md`: `FUN_00028ea6`'s IIR
(`state=(state*0xC63EC + x*0xC63EE)>>10`) sits on the **CAN-sourced LKAS setpoint**, upstream of the
mixer (`gp-0x62b0`→`gp-0x3d88`→`gp-0x6b4c`), which then joins the aggregator as one SUMMAND. It never
reads a sensor/rate signal — its input is the openpilot command. Since the 20-26Hz resonance is
measured under a roughly steady (hands-off) LKAS setpoint, this filter is **not in the path that
closes the loop back to the sensor**, so **neither raising nor lowering its corner (currently
≈4.97 Hz) can move a closed-loop pole.** [EVIDENCE — confirms and extends the prior "DEAD ON
ARITHMETIC" finding; V85 precedent shows the WRONG-direction move (more filtering here) made a
DIFFERENT symptom (the ratchet) 2.89×→6.58× worse, consistent with it doing something to command
tracking speed, not loop damping.]

## 6. The f0 dose-floor — the load-bearing finding, already established, reconfirmed here

**This is the single most important constraint on any lever proposed below**, from
`reference_accord_f0_dose_floor_and_common_path_structure_search.md` (2026-08-20, same day as V103):

- `f0` is measured **linear in gain**: stock 21.90 Hz (1x) → V100 23.61 Hz (4x) → V102 24.90 Hz (6x),
  all CIs disjoint. Law: `f0 ≈ 21.3 + 0.60·m`. At 8x this retrodicts **≈26.1 Hz** — above the
  ~20-23 Hz mechanical mode, i.e. the mode would sit INSIDE the anti-damped region.
- **A lever needs to move `Re(Z)` by ~230 ct·s/rad at 22-26Hz to clear the ~1.5Hz detection floor.**
  The BEST characterized filter lever in this kit's whole record (the dead biquad, arming it) prices
  at **+2 to +13 ct·s/rad realistically, +50 at an extreme, unrealistic q=1.0** — **3-115× too small.**
- **The two "common path" (post-aggregator) candidates checked are NOT tunable filters**: the
  governor (`FUN_0004503c`) is a nonlinear slew-rate limiter (a describing-function test found its
  phase lag is **<0.3° at every measured amplitude**, and no unit rescaling can make its amplitude
  trajectory match `f0`'s monotone law — a **decisive, scale-invariant negative result**); comp-add
  (`FUN_000456a4`) is a static memoryless LERP with zero dynamics to retune.
- **A model-shape refit found the problem is not primarily about PHASE at all**: even a FULL ±180°
  phase rotation of the calibrated loop-gain model cannot supply the required `Re(Z)` swing — the
  loop-gain MAGNITUDE near 22-26Hz is too small in every model tried. This is a harder, more
  informative negative than the retrodiction's 5-8× magnitude miss.
- **Working synthesis** [BELIEF, prior session, not independently re-derived by me this session,
  but consistent with everything I traced]: gain's unique power is that `0xC6CD0` is the only
  variable that changes the PHYSICALLY DELIVERED TORQUE AMPLITUDE, which re-linearizes MULTIPLE
  amplitude-dependent nonlinearities simultaneously (the `f′` observer LERP — already shown to move
  ~2.9-15× locally over the amplitude range gain reaches — and plausibly the governor's own
  active-limiting duty). **A fixed linear filter on any ONE branch — including every element in the
  table above — touches only that branch's fixed dynamics and cannot replicate a system-wide,
  amplitude-driven effect.**

## 7. Ranked lever shortlist

| rank | lever | predicted Δf0 | sign | cost/risk | build class | verdict |
|---|---|---|---|---|---|---|
| 1 | Dead biquad arm (`0xC649B` 0→1) | **+0.01 to +0.3 Hz** (realistic to extreme-case) | favorable (toward stock, never adverse — checked both directions) | none identified — adds attenuation+lag to a branch (`gp-0x6b86`) with currently NO filtering; self-gates on the SAME `gp-0x671a≥5` reversal-counter used elsewhere for 18-21Hz ringing detection; doesn't touch dθ/dt or add low-freq friction | 1 cal byte, already V103-speced, GATE 1/2/3 previously worked | **Ships "free," but 5-150× below the ~1.5Hz action threshold. Do not present as a fix for the reported symptom — it is a free, safe, directionally-correct rider only.** |
| 2 | `0xC63AC` raise ("speed up the tracker") | predicted **worse** Q at every dose 150-300 | ADVERSE | full-loop Bode sum already computed and negative | cal edit | **REFUTED. Do not build.** |
| 3 | `0xC63EC`/`0xC63EE` (either direction) | **0 by construction** | n/a | n/a | n/a | **Excluded — exogenous to the loop, confirmed this session.** |
| 4 | `gp-0x381c`/`0xC6382` filter (favor the slower candidate) | **UNSIZED** — LERP table and branch attribution fraction `q` not resolved | plausibly favorable if the same "add lag where none currently binds" logic as the biquad applies (same downstream lane, `gp-0x6b86`) | unknown — need the LERP table decode + a `q` estimate before any GATE-2 judgment | not ready — needs one more tracing session | **New candidate, not a lever yet. Next step: decode `tp+0x78fc..0x790c`, then repeat the biquad's Re(Z)-sign-analysis treatment.** |
| 5 | New 2nd-order allpass cave (`fc≈21Hz, r=0.90`) | **explicitly un-priced** — the kit's own loop model was shown too unreliable at this magnitude (§6) to honestly convert phase to Hz | phase-only, `\|H\|=1` at every f by construction — dodges the "0xC63AC" gain-cost trap structurally | GATE 1 unresolved (4 new RAM states, not matched to specific free cells); GATE 2 needs the SAME magnitude-not-just-phase treatment that killed the naive retrodiction; command-band cost is low (-1.6 to -16.1° at 0.3-3Hz) | **a genuine NEW CAVE — this kit's only bricking class** | Most structurally promising IDEA in the record, but is design-stage only: no GATE-1 RAM claim, no priced Hz-of-f0, no build. |
| 6 | Lower `0xC6CD0` (give back some gain) | **the only lever with a MEASURED, monotone, linear effect on f0** | favorable | none — this is Honda's/this kit's own established relationship | cal edit, already flown 3x | **Contradicts the brief's stated constraint (hold 8x). Stated for completeness: this IS the lever that works; nothing else in this session's search reaches 1.5Hz.** |

## 8. What I could not resolve — and the exact next step

1. **The `gp-0x381c`/`0xC6382` filter's live-path coefficient (the LERP branch) is uncharacterized.**
   Next step: `decompile_function` or `disassemble_bytes` on `0x35962-0x359ba` to extract the
   `tp+0x78fc..0x790c` table's X/Y knots and the identity of `r1` (what it interpolates on).
2. **`gp-0x381c`'s downstream consumer is not fully traced.** Next step: `get_xrefs_to(gp-0x381c)`
   (as `-0x381c,gp` operand form) to find every reader, and confirm/refute that it feeds the same
   friction/hold combinator as the dead biquad's `r10` input.
3. **FOC current-loop Kp/Ki are not located.** Its phase contribution at 8-26Hz is assumed small by
   standard-practice reasoning (current loops usually run decades above mechanical bandwidth) but
   this is NOT measured. Next step: `decompile_function(0x71272)` (Park/Clarke + PI regulator).
4. **No composed, single total firmware-phase-at-20-26Hz figure exists** the way one does at 6-9Hz
   (`0.253∠−3.05° / 0.257∠+5.43° / 0.262∠+10.05°` at 6/7.79/9Hz, from
   `reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget.md`). Building the 20-26Hz
   equivalent needs the same "attribution fraction q per branch" the biquad and `0xC63AC` sessions
   both flagged as the recurring missing ingredient — not resolved by any session to date.
5. **The allpass cave's GATE-1 RAM claim is not matched to specific free cells**, and its Hz-of-f0
   effect is deliberately unpriced (§6). Both are prerequisites before it could be ranked above "idea."
6. I did **not** independently re-derive the governor describing-function simulation or the
   model-shape refit (§6) myself this session — I am relying on
   `reference_accord_f0_dose_floor_and_common_path_structure_search.md`'s reported numbers, which
   are internally well-documented (scripts named, method shown) but not re-run by me.

## 9. ADDENDUM — the re-centered 7.79Hz notch (orchestrator redirect, same day, `code.bin` unless noted)

The f0-based lever shortlist above (§6-7) is **SUPERSEDED for the ratchet symptom** by a mechanism
redirect: the operator's own two-inertia torsion-bar hypothesis sizes to 6-11Hz (physics) against a
measured 7.79Hz/Q14-29 ratchet, `f0`/22-26Hz is a **different, much smaller** signal on route `0x9e`
(`Re(Z)` −81 [−153,−42] vs **−3639 [−4324,−3114] at 6-9Hz, 45× larger**), and `f0`'s gain-tracking law
is in doubt (command-adjusted stock≈V102). This section prices the resulting lever: Honda's dormant
biquad in `FUN_000352b4`, re-centered from 55.2Hz onto 7.79Hz. §1-8 above (task rates, PID, ZOH,
`0xC6382`, `0xC63AC`, the f0 dose-floor) are UNCHANGED and still the reference for the 20-26Hz band.

### 9.1 §2 re-confirmed from a fresh decompile [EVIDENCE, `decompile_function(0x352b4)`]
`FUN_000352b4` (golden model's `magnitude_6b86` lane, NOT literally "base assist" — terminology
correction, substance unaffected): `gp-0x4f60` (raw torque) → clamp ±0x6400 → 10-point breakpoint
search/LERP over locally-staged `gp-0x37fc[]` (populated by an initial 10-iteration do-while calling
`FUN_000352a0` per knot) → `×sign×gp-0x6752` → shadow-locked into `gp-0x6b7a`/`gp-0x4cdc` → further
limit → `gp-0x6b82` → arm-gated biquad (`0xC649B==1 AND` arm condition) → shadow-locked into
`gp-0x6b86`/`gp-0x4cde` → (established prior session) `FUN_0003aa2c`, unweighted lane into `gp-0x6b94`.

### 9.2 Design verified byte-for-byte [EVIDENCE, independent Python re-derivation, not a relay]
`a1=-2r·cos(w0), a2=r², b1=-2cos(w0), g=(1+a1+a2)/(2+b1)` (DC-normalized), `w0=2π·7.79/1000`.
r=0.990 encodes to the exact bytes `0xC60A8=f0 22 fd bf, 0xC60AC=d5 e7 7a 3f, 0xC60B0=83 b1 ff bf,
0xC60B4=5f 10 84 3f`. Poles `r=0.990000 @ 7.7900Hz` exactly; DC gain 1.000000 exactly (pole/zero
cancellation confirmed, not assumed); peak `|H|` over 0.1-500Hz asymptotes AT Nyquist (500Hz),
**+0.3586dB for r=0.990** (confirmed no secondary peak anywhere by direct evaluation at 50/100/450/
499/500Hz, monotonic rise to the Nyquist asymptote).

### 9.3 Mistuning robustness — attenuation (dB), full grid
```
 f(Hz)   r=0.985  r=0.990  r=0.995
  6.00    -3.82    -2.25    -0.71
  6.50    -5.84    -3.74    -1.33
  7.00    -9.44    -6.77    -2.98
  7.79     null     null     null
  8.50   -10.26    -7.52    -3.47
  9.00    -6.24    -4.07    -1.49
 10.00    -2.68    -1.51    -0.45
```
-3dB half-bandwidth: r=0.985 ±2.07/2.09Hz · r=0.990 ±1.49/1.50Hz · r=0.995 ±0.81/0.79Hz. Peak|H|:
r=0.985 +0.79dB · r=0.990 +0.36dB · r=0.995 +0.09dB. **ADOPTED: r=0.990** — r=0.995's passband is
narrower than the physics-predicted mode range (6-11Hz) itself; r=0.985 pays more peak/20-28Hz cost
for little extra coverage.

### 9.4 6-9Hz Bode sum, `q` symbolic (r=0.990)
```
 f(Hz)     6.0     6.5     7.0     7.5    7.79    8.0     8.5     9.0
|H|dB    -2.25   -3.74   -6.77  -14.66   null  -17.40   -7.52   -4.07
phase   -35.2°  -44.7°  -57.6°  -73.8°     -    +88.3°  +71.7°  +58.3°
Re(H-1) -0.369  -0.538  -0.754  -0.948  -1.000  -0.996  -0.868  -0.671
```
`Re(H-1)` is negative and deepest (exactly −1.000) at 7.79Hz, staying negative through 6.0-7.79Hz
before flipping sign above resonance. [BELIEF, applying the orchestrator's own two-inertia mechanism
model — `L(jw)` transitions through positive-real/aligned territory above `wn`] a gain cut deepest
exactly there is the textbook-correct sign for reducing alignment where the loop is closest to
unstable. **No ct·s/rad number is derivable** without a branch-specific `L(f)` phase at 6-9Hz for
this lane — the same missing ingredient every prior session's Re(Z) pricing hit (§6 above), now also
missing here even with `q` supplied. The five-minute multiply once both land: `ΔRe(Z) ≈
q·C·Re(L_branch(f)·(H(f)-1))`, all filter-side terms above.

### 9.5 20-28Hz effect — a small regression versus what is already flashed [EVIDENCE, computed]
```
 f(Hz)         20      21      22      23      24      25      26      27      28
 r=0.990 dB  +0.27   +0.28   +0.29   +0.30   +0.31   +0.31   +0.32   +0.32   +0.32
 stock(55Hz) -1.12   -1.25   -1.39   -1.55   -1.72   -1.89   -2.09   -2.29   -2.52
```
V103's CURRENT 55Hz notch mildly ATTENUATES 20-28Hz; re-centering to 7.79Hz mildly AMPLIFIES it
instead — recentering **converts a small existing benefit into a small existing cost**, not a neutral
move. Both magnitudes are almost certainly below the ~1.5Hz/230ct·s/rad action threshold (§6), but
"does not disturb the vibration band" should read "costs an amount too small to matter, not zero."
This correction reached the operator; recorded here so the number, not just the correction, survives.

### 9.6 GATE 3 — clamps, and a genuine DROPOUT found this session [EVIDENCE, fresh decompile]
Two ordinary saturating clamps confirmed non-dropout: float `±12.0` (`0x35a54-78`, `maxf.s`/branch
pair) and integer `±0x3000`/12288 (`0x35a8c-a4`) — the SAME numeric bound in two domains
(12.0×1024=12288), a deliberate ceiling through the whole chain. **Separately, and NOT previously
documented as this class of thing**: if `|gp-0x4f60|` (raw torque) exceeds `±0x6400`/25600, the
function writes a **literal zero** to `gp-0x6b86`, bypassing the computed value outright (both paths
under their own shadow-lockstep check calling `FUN_0006b9fa` on mismatch). **A third member of this
firmware's latching-zero-output class**, alongside the `gp-0x6b30` sign-latch and the aggregator's
`0x3acc4 cmovc 0x0,r6,r13`. [BELIEF] Very likely a sensor-implausibility interlock, not a
normal-operating-range gate — 25600 sits well above every other torque-domain bound in this firmware
(PID error clamp ±10240, reference clamp ±8192) — but duty is NOT measured.
**Clamp-hit duty for the ±12.0/±0x3000 pair at r=0.990**: [BELIEF, structural] peak gain ≈1.036×,
input already clamped upstream to the identical ±12288 bound ⇒ output clamp can only bind within
~3.6% of the input's own ceiling — narrow by construction, not measured. **Answerable for free**: V103
already flew 406 engaged seconds with the 55Hz notch armed on the IDENTICAL state cells
(`gp-0x3814`/`gp-0x3818`) and IDENTICAL clamp structure — reading that already-collected telemetry
answers this empirically before any recentered coefficient is flashed. Assigned to a data agent
(needs the rlog cache, not Ghidra) as of this trace's close-out.

### 9.7 Engagement gate — KEEP, confirmed from the trace [EVIDENCE]
Nothing outside the arm-gated block reads `gp-0x6806` — when disarmed, `FUN_000352b4` falls straight
through to the raw pre-filter value, byte-identical to every build before V103. Manual feel is
**provably**, not merely believed, unchanged by this lever regardless of coefficient. Recommend
keeping engaged-only scope: the mechanism (operator's own two-inertia model) is specifically
LKAS-excitation-driven, and manual's own rate-dependence is flat (33→29 per route `0x9e`, relayed) —
engaged-only touches exactly the regime with evidence of a problem.

### 9.8 `gp-0x671a` correction — V103 does NOT share the r24/r26 starved gate [EVIDENCE, byte-verified]
Earlier this session flagged that the dead biquad's arm (`gp-0x671a>=cal(0xC64FA)=5`) might be
starved the same way `0xC6440`/`0xC643E` (r24/r26 "third arm") are — both read the identical cell
against the identical threshold in STOCK. **V103 repoints the SOURCE register**, confirmed by a direct
Python byte read of BOTH `stock_fw_dump/code.bin` and
`_v103_V102BASE-BIQUAD.ENGAGED-CAVE...plain_image.bin` (not a relay): `0x35A06` stock
`ld.bu -0x671a,gp,r9` → V103 `ld.bu -0x6806,gp,r9`; `0x35A12` `cmp r12,r9`→`cmp r0,r9`;
`0x35A18` `setfnc`→`setfne`; `0xC649B` `00`→`01`. Cross-checked three ways (raw byte diff;
displacement-delta arithmetic, `0x98E7-0x97FB=0xEC=236=0x6806-0x671A` exactly; full
instruction-semantic re-derivation giving `gp-0x6806!=0`, matching that cell's established identity
as the engagement flag). **V103's biquad is genuinely engaged-gated, not starved — the "f0 didn't
move as predicted" result is a real, if modest, magnitude confirmation, not a null-on-the-gate.**
The r24/r26 kill is UNAFFECTED (different gate, `FUN_0003aa2c`, not touched by V103's edit, which is
local to `FUN_000352b4`) and stands: `0xC6440`/`0xC643E` are not virgin (V42-V88 lineage) and remain
starved on every build to date including V103.

## 10. What is NOT written down elsewhere — for a successor, so nothing is re-run

- **My own scratch `biquad_H` derivation had two algebraically-different-looking forms** (an early
  one using `z + c1 + c2/z` for the pole polynomial and a hand-wavy `x2*z` stand-in for the
  numerator's `z^-2` tap, and a later, carefully re-derived one using the exact `1+b1z^-1+z^-2`
  numerator) that gave IDENTICAL numeric answers to 3-4dp, cross-validated against the
  orchestrator's independent number both times. **Never resolved WHY the two forms coincide** — did
  not chase it once triple-corroborated. A future session reusing scratch DSP code from this
  transcript should re-derive from the disassembly rather than trust either snippet's algebra by
  inspection; only the NUMBERS are load-bearing, not the derivation path.
- **`gp-0x671a` has readers this session did NOT characterize**: besides the two traced consumers
  (biquad arm, r24/r26 third arm), `search_instructions(operand_pattern="671a")` also found reads
  inside `FUN_00035b20`, `FUN_00036c12`, and — notably — **`FUN_0003a382`, the PID itself**
  (`0x3a4a6`). None of these three were opened this session. If `gp-0x671a` gates or modifies
  anything inside the PID directly, that is a live, unexplored thread adjacent to everything else in
  this trace. Next step: `decompile_function` on each, or at minimum `disassemble_bytes` around the
  three cited addresses.
- **`FUN_000428d4` (the `gp-0x671a`/`gp-0x67df` producer) has an un-traced early gate**: its very
  first action is `mov 0x5,r6 / jarl 0x46ea6,lp`, then an early-return (`jr 0x42a76`, skipping the
  entire FSM) if the call's result is nonzero. `FUN_00046ea6`'s semantics were not opened this
  session. If this gate is frequently true, it would ALSO suppress `gp-0x671a` updates on top of the
  wheel-rate-threshold mechanism already characterized — a possible SECOND reason the V67/V68
  zero-duty prior held, not yet distinguished from the primary mechanism.
- **`gp-0x381c`'s only-traced consumer is inside `FUN_000352b4` itself** (summed with the
  biquad/raw term before the shared `±0x3000` clamp, confirmed this session). Did not check for
  OTHER readers of `gp-0x381c` image-wide — plausible there are none (it reads as a private
  accumulator) but this was assumed from local context, not confirmed by a full xref sweep.
- **`gp-0x381c`'s LERP interpolation KEY (`r1` in the decompile) was never identified** — irrelevant
  to this session's conclusions because the LERP is flat (Y=[20,20,20,20] at all knots) so the key's
  identity cannot change the answer, but a future session raising any of those Y-values would need it.
- **The old repo-committed `eps_loop_gain_model.py` (V38-era) was read and explicitly NOT reused**:
  its single calibration anchor (`|L(4x)|=0.875`) extrapolates linearly to `|L(8x)|=1.75`, past the
  hard self-excitation edge — nonsense-past-validity for any 6-8x-gain-era question. Do not reach for
  this script for V101-V104-era pricing; it predates the gain era entirely and was calibrated on a
  single V38/4x data point.
- **Did NOT independently verify the two-inertia mechanism's physical parameter ranges**
  (k_tb 1.5-2.5 N·m/deg, J_wheel 0.03-0.06 kg·m²) that produce the claimed 6.0-11.0Hz mode range —
  treated as a plausible, cited engineering estimate, not something Ghidra or a byte read can confirm
  or deny. The ARITHMETIC connecting those parameters to a frequency was not independently re-run
  either (relied on the orchestrator's stated result).
- **Did NOT independently verify any route-`0x9e` telemetry claim** — IMU coherence figures, the
  24.29× engagement contrast, the wheel-rate scaling (16→60→369→490), the manual-flat citation
  (33→29), or the `Re(Z)` values themselves (−3639 at 6-9Hz, −81 at 22-26Hz, 895 at 31-35Hz control).
  These require the rlog cache (`analysis-2020accord/_cache_r9e/`), outside this agent's toolset
  (GhidraMCP + firmware bytes only). All treated as attributed, not re-derived.
- **FOC current-loop Kp/Ki are still not located** (`decompile_function(0x71272)` never run this
  session) — carried forward from §8 item 3, unchanged.
- **No single composed 20-26Hz (or now 6-9Hz) total-firmware-phase figure exists** the way one does
  for the OLD 6-9Hz PID-only budget cited in §8 item 4 — every session that has needed this,
  including this one, has hit the same missing per-branch attribution-fraction ingredient. This is a
  recurring, not novel, gap — flagging again so a successor does not treat it as newly discovered.

## Related memory
`reference_accord_f0_dose_floor_and_common_path_structure_search.md` ·
`reference_accord_c63ac_full_loop_bode_sum_net_negative.md` ·
`reference_accord_v101_v102_resonance_mechanism_and_biquad_direction.md` ·
`reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md` ·
`reference_accord_live_lkas_command_path_and_c63ec_lowpass.md` ·
`reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md` ·
`reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md` ·
`reference_accord_kd_pid_dterm_priced_and_manual_gate.md` ·
`reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md` ·
`reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26.md` ·
`reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction.md`
