# DESIGN V299-D4: smoothness-first (designer D4, judge-panel round, 2026-10-02)

**Status: DESIGN ONLY.** Nothing was built, flashed or sent, and the fork was not touched.

- Ghidra was used read-only: `disassemble_bytes dry_run`.
  - V298 was decoded from program `ADVIG_V298_177abf04.bin`.
  - The D4b bytes were decoded from a scratch import, `/d4scratch/D4B_DISASM_ONLY_NOT_AN_ARTIFACT_NO_CRC.bin`. That is V298 with the D4b edits and **no CRC fix**. It is not an artifact and not a flash candidate. Nothing was saved.
- Python is the `bin_decompile` environment. Every script finishes in under 30 s, and the wall times are given in section 3.

**Author:** designer D4, a SUBAGENT of the orchestrator.

**Labels:**
- **EVIDENCE** means measured on route 79, read from the image, or executed by a script. The method is given each time.
- **BELIEF** means modelled or inferred.
- These are band scores. **The operator scores the symptoms.**

Scripts are in `analysis-2020accord/studies/angle_loop/v299_design/D4-smoothness-first/`. Outputs are in `_scratch/v299_D4/`.

---

## 0. The answer in one page

**The target.** The drive read and its two refutations name the two ratchets behind note 4:

1. **The integrator-freeze relay.**
   - V298 freezes the I whenever the instantaneous torque word gp-0x4f60 crosses |300| against E′, or |512| at all.
   - Hands-off, the wheel's own reaction twist crosses those levels. The torque-word p90 is 607–681 below 8 m/s.
   - Stall-surges are enriched near those crossings: 80.7 against 30.3 /min at 5–10 m/s, and 47.4 against 8.4 at 0–5 m/s. V282 and V294, which have no freeze, show no enrichment (REFUTE-synthesis-inference V6).
2. **The small-correction stick.**
   - 87–91 % of the 0.25 deg/s dwells are a stuck wheel under a slowly drifting setpoint.
   - Catch-ups run 9× V282.

**The design.** D4 kills the relay with **one state word and a motion gate**, measures it from the first engaged second, and touches nothing in the linear loop.

| | **(a) cal + in-place** | **(b) cave term + state word: RECOMMENDED** |
|---|---|---|
| Firmware | GB-S13 table: 3 knot gains ×1.3 at 10 / 11.75 / 17.5 m/s and 4 slopes, which is 14 data bytes inside V298's cave. Version 'A16B'. CRC. | V298's 28-byte hand block is replaced by:<br>• an **LP-filtered hand word** h = gp-0x6a32 (τ 32 ms, engage-initialised);<br>• freeze if \|h\| > 512, or \|h\| > 300 opposing E′ **unless the wheel already moves toward the setpoint** (\|gp-0x6abe\| > 10 with the opposite sign of E′).<br>Plus `nop;nop` at 0x29D72 and the 0x14A b4.7 rung repointed to sign(h). The cave grows 260 → **312 B**. |
| New RAM | 0 | **1 halfword**, gp-0x6a32 |
| Fork | O1 ON debounce, 5 frames (code constant). Version tuple. | The same two |
| Ratchet 1 (freeze relay) | **not moved**. In-place thresholds cannot fix it without an N1 regression (EVIDENCE, §2a). | Hand-freeze toggles **325 → 79 /min** (route-79 replay). Duty 11.4 → 4.0 %. The integration the I keeps rises 0.69 → 0.81; effective Ki below 8 m/s goes 1.53 → 1.95 /s. Frozen share at \|α\| > 400 drops 0.62 → 0.26. |
| Ratchet 2 (stick) | Simulated stuck share −15 % at 12.5 m/s and −12 % at 19 m/s. Small-sine gain at 19 m/s 0.48 → 0.58. | Unchanged on its own (simulated). Grafting GB-S13 gives (a)'s numbers. |
| N1 (hand release) | Unchanged: Δlurch ≤ +0.07° in every scenario | Inward holds: Δ ≤ +0.30°. Firm outward hold: −0.4°. **Outward light hold (400–511 word): +1.7° worst**, at 3–5 m/s on a 10–12° baseline (declared, M3). |
| GATE 2 | Changes the loop, but **0 fails** on the core set at a = 0 / 1.5 / 2.5. PM falls by up to 17° at 10 m/s. | **Loop unchanged.** The PID and the I-frozen PD are byte-identical to V298's (0 fails). |
| Instrument | Small-signal slope and tap at 10–20 m/s (existing wire) | b4.7 = sign(h) against h reconstructed from the 0x18F word (comparator form), plus replay model selection on the 0x1AB tap |

**Rejected with evidence (§1, §3):**

| rejected option | reason | evidence |
|---|---|---|
| In-place opposing threshold 300 → 450 | Outward-hold release lurch rises from 3.45° to 13.5° at 8 m/s; co-steer droop rises from 0.36° to 2.0° | d4_sim |
| In-place "motion-corrected sign" rewrite of the 24-byte block | Toggles −5 % only, and hands pressed past steeringPressed are frozen on only 31 % of frames | d4_r79 A3 |
| **Setpoint-rate friction FF** (one state word) | The 0xE4 setpoint makes **275 one-quantum reversals per minute of hold**. The FF turns them into a ±FC buzz: 5–30 Hz torque ×3.5 in the creep sim, and FF ≥ FC/2 on 4.7–58 % of hold frames. It reaches FC/2 inside only 24–44 % of stuck-dwell frames. | d4_r79 C, d4_sim |
| Error-keyed friction FF (boundary layer) | **Hunting**: 14 reversals at 26 m/s on the nominal member. Jitter torque 2.3 → 4.3. | d4_sim |
| Dither | Not simulated. Rejected by construction for this car's vibrating and grinding record. | BELIEF |

---

## 1. Mechanisms: what each change must move, and the prediction

| # | mechanism (operator's words) | measured, route 79 (source) | D4 change | predicted (method) |
|---|---|---|---|---|
| M-i | "stuttery / ratchety" in turns: **the freeze relay** | Stall-surges near \|bar\| 300/512 crossings: 80.7 vs 30.3 /min (5–10 m/s), 47.4 vs 8.4 (0–5). References show none (refuter V6). Hands-off hand-freeze toggles **325 /min**, duty **11.4 %** (d4_r79 A, the M3 lane at 1 kHz). Kept integration **0.69** (M3: 0.69). Effective Ki below 8 m/s **1.53 /s** (refuter: 1.0–1.2; M3: 1.45–1.62). Frozen at \|α\| > 400: **0.62**. | (b): LP hand word, motion gate, thresholds on the LP word | Toggles **79 /min**. Duty **4.0 %**. Kept **0.81**. Effective Ki below 8 m/s **1.95 /s**. Frozen at \|α\| > 400: **0.26**. Hands with steeringPressed are still frozen on **0.999** of frames (V298 0.997). All EVIDENCE: the replay of the recorded inputs, using M3's validated lane and I recursion. The stall-surge enrichment near crossings should fall to ≤ 1.3×, the V282/V294 level of 0.4–1.1× (BELIEF: the sim does not reproduce the trains, §7). |
| M-i′ | The same relay **costs tracking** in hands-off manoeuvres | — | (b) | Sim slew with the twist model: lag p50 at 12.5 m/s **2.38° → 0.93°**, the V298 no-twist value (0.93); at 19 m/s 1.42° → 0.73° (no-twist 0.70). Peak T at 8 m/s 818 → 886. EVIDENCE: sim; the twist model is BELIEF. |
| M-ii | "micro-ratcheting" on small corrections: **stick** | Dwells /min 4.70 / 1.16 / 4.47 / 3.53 (0–5 / 5–10 / 10–20 / > 20 m/s). Catch-ups 1.08 /min (V282 0.12). Breakaway \|err\| median 0.8° (M4; d4_r79: 0.50 p50 / 1.20 p90). | (a): GB-S13 stiffness ×1.3 at 10–17.5 m/s | Sim creep, r79-friction member: stuck share **25.9 → 22.1 %** at 12.5 and **14.6 → 12.8 %** at 19 m/s. Lag max 1.48 → 1.28°. 10–20 m/s dwells **4.47 → ~3.8 /min** (BELIEF: proportional scaling). No change below 10 m/s. |
| M-iii | O1 snaps the setpoint to the wheel on the hands-off twist | 345 never-pressed O1 episodes, 13.8 s. Each steps the setpoint 3.6° (p50) toward the wheel. The 4–8 Hz modulation near O1 is 6.99 vs 3.06 deg/s away from it (refuter, causal direction undecided). | Fork: O1 ON debounce, 5 frames | **63 episodes, 2.2 s** left; **53 / 53** pressed episodes still caught, onset lag p50 0 ms (d4_r79 B, the O1 reconstruction re-run). |

---

## 2. The two implementations

### 2a. Implementation (a): cal + in-place

**Firmware: the GB-S13 table.** The table is the G(v) data at the end of V298's cave. Its rows are (X u16, G u16, S s16 Q12). The edit raises knots 2–4 by ×1.3 and recomputes every slope by rounding. The script `d4_gate2.scaled` reproduces GB-P exactly with factor 1 (control: True).

| addr | V298 (LE) | (a) | cell |
|---|---|---|---|
| 0xC4CE4 | `88 e7` (S1 −6264) | `72 ef` (−4238) | slope 8 → 10 m/s |
| 0xC4CE8 | `f8 02` (G2 760) | `dc 03` (988) | gain at 10.0 m/s, Kp_eff 332 → 432 |
| 0xC4CEA | `0f f8` (S2 −2033) | `ad f5` (−2643) | slope 10 → 11.75 m/s |
| 0xC4CEE | `30 02` (G3 560) | `d8 02` (728) | gain at 11.75 m/s, Kp_eff 245 → 318 |
| 0xC4CF0 | `22 06` (S3 1570) | `f8 07` (2040) | slope 11.75 → 17.5 m/s |
| 0xC4CF4 | `2c 04` (G4 1068) | `6c 05` (1388) | gain at 17.5 m/s, Kp_eff 467 → 607 |
| 0xC4CF6 | `46 08` (S4 2118) | `e9 05` (1513) | slope 17.5 → 26.9 m/s |
| 0x1310D | `41` 'A' | `42` 'B' | F181 → `39990-TVA,A16B` |
| 0xC4FFC | `f3d87c6b` | recomputed | main-block CRC; cal blocks untouched |

The delivered gain ratio against GB-P (EVIDENCE, `c3r1_model.walk_G`): ×1.10 at 9 m/s, ×1.30 at 10–17.5, ×1.22 at 19, ×1.10 at 22, ×1.01 at 26 m/s. Gains at ≤ 8 m/s are unchanged.

**Why no hand-rule edit is in (a).** The in-place grid (d4_r79 A and A2, 48 rules) shows only two options, and both fail:
- Raising only the hard threshold (512 → 1229) keeps integration at **0.697** against 0.688 for V298. It changes nothing.
- Raising the opposing threshold to 450 does cut toggles to 127 /min and raise kept integration to 0.76. But the N1 outward light hold rises **+10.4°** and co-steer droop **+1.8°** (d4_sim C, B1). That is a hand-safety regression, so it is rejected.
- The 24-byte "motion-corrected sign" rewrite, which tests sign(hs − c·abe) with c = 1–8, leaves toggles at 306–313 /min. Pressed-frame freeze falls to 0.26–0.34 (A3).

So the freeze relay **cannot** be fixed in place. (a) is honest about that.

**Fork, code (`raayyymond-StarPilot`, Dom):**
- `values.py` `CarControllerParams`: add `ANGLE_OVERRIDE_DEBOUNCE = 5` (frames).
- `carcontroller.py` `_update_angle`: count consecutive frames with |steeringTorque| > ANGLE_OVERRIDE_ON while O1 is off. Turn O1 on only once the count reaches 5. The OFF hysteresis (500) is unchanged, and the counter resets whenever the torque drops to ON or below, or latActive is false.
- `values.py`: `HONDA_ACCORD_EPS_ANGLE_LOOP_FW` becomes a tuple `(b"39990-TVA,A16A", b"39990-TVA,A16B")`.
- `interface.py` `_get_params`: use `in` instead of `==`.
- **A toggle config cannot express these.** They are code constants. An optional `Params` override (`AccordAngleOverrideDebounce`) would make later tuning a toggle config.

**New RAM: none. Instrument:** the existing wire carries what is needed.
- The small-signal slope at 12–25 m/s should rise from 0.64–0.82.
- The 0x1AB tap at 10–20 m/s: open-loop replay p99 102 → 118 LSB (d4_r79 D).

### 2b. Implementation (b): the state-word cave (RECOMMENDED)

**Every byte that changes against V298 (sha 177abf04…):**

| id | addr | V298 bytes | (b) bytes | decoded (Ghidra dry-run on the scratch import) | loop term |
|---|---|---|---|---|---|
| N0 | 0x29D72 | `64 87 ce 95` `st.h r16,-0x6a32,gp` | `00 00 00 00` | `nop ; nop` | Removes Honda's dead setpoint publish, which would overwrite h every tick. This is V288 r2's flown edit site. |
| CAVE | 0xC4C00–0xC4D37 | 260 B, sha ef1861e1… | **312 B**, sha **59b90cbdf004** (full hash in §9) | listing below | the LP state word, the hand rules, the motion gate. Relinked: the table moves to **0xC4D0E**. |
| T7 | 0xC4B92 | `24 37 b4 94` `ld.h -0x6b4c,gp,r6` | `24 37 ce 95` | `ld.h -0x6a32,gp,r6` | the 0x14A b4.7 rung becomes **sign(h)** (1 = h < 0) |
| V1 | 0x1310D | `41` | `42` | F181 'A16B' | attribution |
| CRC | 0xC4FFC | `f3d87c6b` | recomputed | — | main block only |

**The cave listing, D4-new instructions only.** Everything else is V298's listing, relinked. CONTROL: d4_cave's listing reassembles V298's 260 B flight cave **byte for byte**, both against the frozen sha `ef1861e10421` and against the image bytes at 0xC4C00 (EVIDENCE, `d4_cave.main`). Every line below was decoded by Ghidra (dry-run, scratch import) exactly as listed.

```
0C4C54 APPLY mul r8,r16,r0 ; 0C4C58 sar 8,r16                                    (V298: E' = (E G) >> 8)
0C4C5A ld.w  -0x6cf8,gp,r8          24 47 09 93   [LP] Honda's first-tick sentinel word
0C4C5E mov   0x7fffffff,r13         2d 06 ff ff ff 7f
0C4C64 cmp   r13,r8                 ed 41         Z on the first PID tick after any skip
0C4C66 ld.h  -0x6a32,gp,r9          24 4f ce 95   h_prev (the state word)
0C4C6A cmove r0,r9,r9               e0 4f 24 4b   h_prev := 0 on that tick         (ENGAGE INIT)
0C4C6E ld.h  -0x4f60,gp,r8          24 47 a0 b0   hs = the signed hand word
0C4C72 sub r9,r8 ; sar 5,r8 ; add r8,r9           h = h_prev + ((hs - h_prev) >> 5)
0C4C78 st.h  r9,-0x6a32,gp          64 4f ce 95   the state word
0C4C7C cmp r0,r25 ; be CAM                        (V298 camera gate, relinked -> 0xC4CFC)
0C4C80 mov r9,r8 ; cmp r0,r8 ; bge HA ; subr r0,r8               |h|
0C4C88 HA movea 0x200,r0,r13 ; cmp r13,r8 ; bh FRZ(0xC4CF6)     [HARD] |h| > 512 -> freeze
0C4C90 movea 0x12c,r0,r13 ; cmp r13,r8 ; bnh N2(0xC4CAE)        [OPP] |h| <= 300 -> no hand
0C4C98 xor r16,r9 ; bge N2                                        same sign as E' -> not opposing
0C4C9C mov r26,r9 ; xor r16,r9 ; bge FRZ                          [GATE] abe has E's sign: NOT moving toward sp -> freeze
0C4CA2 addi 0xa,r26,r9 ; movea 0x14,r0,r13 ; cmp r13,r9 ; bnh FRZ  |abe| <= 10 (~static) -> freeze
0C4CAE N2: (V298's A3 bound, ramp test, FRZ / CAM / DONE exits, unchanged and relinked)
```

**Byte count and registers.**
- The LP block is **34 B** and the new hand block **46 B**. Together they replace V298's 28-byte hand block, so the cave grows by **+52 B**.
- 0xC4D38 is well inside the free run, which ends at 0xC4FF0 (748 B of 0xFF, EVIDENCE, image read).
- Scratch registers: r8, r9 and r13 only, the same set V298 already uses. r10 (DB), r14 (ramp), r16 (E′), r26 (op) and r6 (link) are preserved. r25 is read only.

**The integer-exact mirror** (`d4_cave.d4b_ref`, the function to graft into `eps_chain_control.py` beside `_self_check_v298`):

```python
def d4b_hand(st, hs, Ep, op, eprev, s32=lambda x: ((x + 2**31) & 0xFFFFFFFF) - 2**31):
    """hs = s16 gp-0x4f60, Ep = E' (r16), op = validated gp-0x6abe (r26), eprev = gp-0x6cf8 (Honda's previous E' or
    the 0x7FFFFFFF skip sentinel).  st.h = gp-0x6a32 (s16).  -> True = freeze (exit 0x29D7E with e5 = 0)."""
    h_prev = 0 if eprev == 0x7FFFFFFF else st.h                    # 0xC4C5A..6A  engage init
    h = s32(h_prev + (s32(hs - h_prev) >> 5))                      # 0xC4C72..76  LP, tau 32 ticks
    st.h = ((h + 0x8000) & 0xFFFF) - 0x8000                        # 0xC4C78      st.h
    ah = abs(h)
    if ah > 512:                                   return True     # 0xC4C88      hard
    if ah <= 300 or (h ^ Ep) >= 0:                 return False    # 0xC4C90..9A  no opposing hand
    if (op ^ Ep) >= 0:                             return True     # 0xC4C9C..A0  not moving toward the setpoint
    return ((op + 10) & 0xFFFFFFFF) <= 20                          # 0xC4CA2..AC  |abe| <= 10 -> static -> freeze
    # False falls through to V298's A3 bound and ramp tests (unchanged)
```

Three checks tie the bytes, the mirror and the simulation together. All are EVIDENCE.
- **H1: the bytes match the mirror.** `d4_cave.h1` executes the D4b bytes in a V850E2 interpreter (`e2_asm.run_bytes` extended with `st.h`) and compares them with `d4b_ref`, including the state word. Over 20,000 random and edge inputs there are **0 mismatches**. The exits split RET 3299, FRZ 14555, op-skip 2146.
- **The simulation matches the mirror.** `d4_mirror_check`: the simulated lane `d4_sim.D4Lane` ('b8') against `d4b_ref` gives **0 / 4000** freeze-decision mismatches and **0 / 4000** state-word mismatches.
- **The simulation's V298 configuration matches the common scorer.** `d4_sim.selftest`: D4Lane in the V298 configuration against panel-2 `score_time.CandLane` (C3B-P, dir-2 ramp) differs on **0 of 36,000** T words.

**GATE 1: RAM ownership of gp-0x6a32 (0xFEDF15CE).**
- **Static census (EVIDENCE, `d4_gate1`).** Method: V289's `gp_accesses` scanner, which covers every width, the ld.bu parity form, bit-ops, the 6-byte ext form and addi/movea; the positive controls reproduce.
  - There are **2 writers and 0 readers**: `st.h` at 0x29D72 (removed by N0) and `st.h` at 0x2AC68. The second sits inside the duplicate PID span [0x2A30E, 0x2B422), which TRACE-2026-09-06 proved unreachable (inherited EVIDENCE).
  - No dword literal and no movhi pair.
  - Boot value 0 (.data, flash 0x8667E).
- **Nearby bases.** Two groups of addi/movea materialise a gp base within [−0x100, +0x40]. Neither reaches the word:
  - 0x41F12–0x41F22 (gp−0x6a1c / −0x6a20 / −0x6a1e / −0x6a1a) pass pointers to FUN_0004613e. Ghidra dry-run shows that function reads `0x0[r7]`, `0x0[r8]`, `0x0[r9]` and `*sp[0]` only: offset 0, no stores through the pointers.
  - 0x36D1C–0x36D30 are 242 B away.
- **On car (EVIDENCE of record).** V288 rev 2 used gp-0x6a32 as its filter state and flew (route 5e, cave LIVE, no anomaly).
- **New accessors.** The cave reads and writes the word. The 0x14A rung only reads it, and the halfword store is atomic.
- **Residual (BELIEF).** A fully register-indirect access from an unmaterialised base, the gp-0x1500 class, cannot be excluded statically.

**The wire instrument for the new state word: present with the dose, in the same build.**

1. **b4.7 = sign(h)** (the T7 repoint). The bit had been V282's sign(gp-0x6b4c), "never used in any analysis" (V289 note; its r79 duty was 0.29).
   - It is checked against h_rec, which is rebuilt offline from the 0x18F word: gp-0x4f60 = −bar, the +10-tick lead, and the same LP. That makes the check a comparator: no scale assumption, with the 0x18F torque as the magnitude channel.
   - Positive control: **P(b4.7 = [h_rec < 0] | \|h_rec\| ≥ 64) ≥ 0.95**.
2. **The dose: M3's replay model selection on the 0x1AB tap.** The tap is fitted twice, once with the D4b hand rules and once with V298's. On r79 the two rules differ by a replayed tap of **p99 70 LSB** hands-off, so one hands-off manoeuvre separates them.

   The sentence a null licenses: *if b4.7 tracks h_rec but the replay does not prefer the D4b rules, the cave is not deciding as designed; stop. If both pass and stall-surges are still enriched near \|bar\| 300/512, the freeze was not the ratchet's mechanism; the claim is falsified.*
3. **Optional (doctrine: "prefer the inert tap").** A staged build, V299-pre = N0 + LP block + T7 with V298's hand rules, verifies the state word on one drive before the dose.
   - The dose was sized offline from r79's recorded word (d4_r79 A4), so D4 judges the stage optional.
   - The judge may require it.

**Fork:** the same two changes as (a): O1 debounce and the version tuple. **GB-S13** may be grafted onto (b) (as "b8+GBS13" in §3). It is not in (b) by default, because its smoothness costs are stated in §3.

---

## 3. GATE 2 and the time criteria (all run this session; wall times measured)

**GATE 2** (`d4_gate2.py`, **2.9 s**, 16 processes).
- Model: the independent C3-r1 stability model `c3r1_model` (exact sampled-data plant channels, 100 Hz hold, EMA, output lag, fade).
- Members: 12 core (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6, b_lo\*J_hi, b_lo\*tau6, J1.0, b_q, b_q\*J_hi). ms_free is reported separately.
- Frames: κ 1 / 0.83 / 1.155. Ages: 0 and 10.
- Curve-hold operating points a = 0 / 1.5 / 2.5 m/s², using rb_opbreak's tyre-softened spring.
- Bar: 45° for single members at age 0, 30° otherwise. Cell format: **min PM ° / min GM-up dB / max Ms**.
- **(b) = V298's loop.** The hand rules switch between the PID and the I-frozen PD, and both are byte-identical to V298's.

| v (m/s) | V298 = (b), PID a=0 | GB-S13 (a), PID a=0 | V298, PID a=2.5 | GB-S13, PID a=2.5 | V298, PD a=0 | GB-S13, PD a=0 |
|---|---|---|---|---|---|---|
| 3.1 | 46.0 / 15.4 / 1.47 | same | 36.2 / 15.5 / 1.63 | same | 58.3 / 15.4 / 1.48 | same |
| 8.0 | 45.6 / 15.1 / 1.61 | same | 33.4 / 15.2 / 1.87 | same | 54.1 / 15.0 / 1.52 | same |
| 10.0 | 80.2 / 17.1 / 1.32 | **62.8** / 16.8 / 1.34 | 42.9 / 17.2 / 1.39 | **38.8** / 16.9 / 1.55 | 82.1 | 68.5 |
| 11.75 | 75.5 / 18.2 / 1.26 | 75.3 / 17.9 / 1.27 | 45.8 / 18.3 / 1.30 | **41.7** / 18.0 / 1.43 | 96.0 | 87.5 |
| 15.0 | 79.3 / 20.8 / 1.28 | 67.3 / 20.5 / 1.36 | 52.6 / 21.0 / 1.28 | **46.8** / 20.7 / 1.49 | 77.6 | 68.3 |
| 17.5 | 84.4 / 22.3 / 1.24 | 79.1 / 21.9 / 1.35 | 60.1 / 22.4 / 1.27 | 55.6 / 22.1 / 1.46 | 89.5 | 77.3 |
| 22.0 | 75.2 / 22.4 / 1.36 | 71.8 / 22.1 / 1.44 | 64.0 / 22.5 / 1.41 | 57.3 / 22.2 / 1.51 | 82.7 | 74.7 |
| 26.9 | 60.2 / 22.3 / 1.55 | same | 54.6 / 22.4 / 1.59 | same | 67.4 | same |

- **Fails against the bar: 0** for both tables at every speed and every a, in the PID and PD loops alike (EVIDENCE).
- **ms_free family, report only** (BELIEF-disfavoured by the held-out identification): V298 at a = 2.5 has PM 20.4 (11.75 m/s); **GB-S13 has 15.4**. This is (a)'s one GATE 2 cost to declare.
- The full rows for a = 1.5 are in `_scratch/v299_D4/gate2.txt`.

**Time criteria.**
- Engine: `d4_sim.py`, the panel-2 common time scorer `score_time.run`, imported unchanged: Karnopp plant, 10 kHz substeps, frame map, slot-4 hold, EMA, fade, lag, rail.
- Lane: D4Lane.
- Members: nominal, F_hi, and **r79bk**, the nominal member with route 79's measured breakaway friction (156 / 93 / 47 / 51 / 29 / 28 T by band, Coulomb 0.8×; the instrument is single-method, so BELIEF).
- **TWIST** (scenarios marked *): the hands-off torque word = LP15 ms(−0.69α − 0.69ω − 163 sgn ω − 61) + N(0, 120), held at 100 Hz. The fit is M3's: its sign is EVIDENCE, its noise level BELIEF.
- Wall times: sets A1 / A2 / B1 / B2 / C took **12.8 / 10.8 / 8.4 / 7.4 / 8.3 s**; selftest 7.3 s; tables and summary 0.1 s.

| measure (max over the 3 members unless noted) | V298 | (a) GB-S13 | **(b) b8** | b8 + GB-S13 | b7 (LP 16 ms) | b2 (H1229) |
|---|---|---|---|---|---|---|
| *slew: hand-freeze toggles /s at 3 / 8 / 12.5 / 19 m/s | 21.5 / 13.0 / 16.3 / 16.7 | 25.5 / 13.3 / 21.3 / 17.0 | **2.7 / 1.3 / 0.0 / 6.7** | 4.3 / 2.0 / 0.7 / 1.3 | 5.3 / 2.7 / 1.7 / 5.0 | 4.3 / 2.3 / 1.7 / 3.3 |
| *slew lag p50 ° at 12.5 / 19 (V298 without twist: 0.93 / 0.70) | 2.38 / 1.42 | 1.62 / 0.95 | **0.93 / 0.73** | 0.42 / 0.46 | 0.94 / 0.72 | 0.94 / 0.73 |
| *slew 1.6–3 Hz wheel rate at 3 / 5 / 8 m/s | 7.28 / 3.85 / 8.07 | 7.13 / 3.82 / 7.97 | 5.49 / **5.49** / 8.85 | 5.35 / 5.52 / 8.75 | 5.40 / 5.32 / 8.45 | 7.55 / 5.71 / 10.52 |
| *creep (r79bk): stuck % at 12.5 / 19 | 25.9 / 14.6 | **22.1 / 12.8** | 25.9 / 14.5 | 22.3 / 12.6 | 25.9 / 14.0 | 26.1 / 14.6 |
| *creep: T 5–30 Hz rms, mean | 0.64 | 0.67 | 0.64 | 0.67 | 0.65 | 0.65 |
| *hold + measured setpoint jitter: T 2–30 Hz rms / reversals | 2.34 / 1 | 2.35 / 0 | 2.32 / 1 | 2.34 / 0 | 2.31 / 1 | 2.33 / 1 |
| hold + road noise 15 T: p2p ° | 1.02 | 0.89 | 0.90 | 0.85 | 0.75 | 0.88 |
| sine 0.3° 0.5 Hz gain, nominal, 19 / 26 m/s | 0.48 / 0.91 | **0.58** / 0.91 | 0.48 / 0.90 | 0.58 / 0.91 | 0.49 / 0.90 | 0.48 / 0.91 |
| N1 inward light holds ov_lt400 / ov_lt511 / ov3_lt511: worst lurch (Δ vs V298) | 4.03 | +0.02 / +0.03 / +0.03 | **+0.03 / +0.29 / +0.30** | — | +0.01 / +0.12 / +0.12 | +0.03 / +0.30 / +0.30 |
| N1 firm hold ov_fm2400 / co-steer cs droop (Δ) | 4.01 / 0.36 | +0.03 / +0.01 | +0.07 / +0.01 | — | +0.02 / +0.01 | +0.05 / +0.01 |
| **N1 OUTWARD** hold to 2·Ah, 3 s, word 400 / 511 / 1000: worst swing-back (Δ) | 11.9 / 10.4 / 8.1 | +0.07 / +0.04 / +0.02 | **+1.68 / +1.68 / −0.00** | — | +0.92 / +1.51 / 0.00 | +1.69 / +1.67 / +1.99 |

**Reading the table** (EVIDENCE that the sim does this; BELIEF that the car will):
- **(b) is the only family** that cuts the freeze toggling in the twist-laden slew **by ×3–20** and restores the designed tracking.
- It costs **+1.7° outward light-hold swing-back** at 3–5 m/s. The cause is the LP's ~45 ms onset delay.
- b7 (LP 16 ms) halves that cost (+0.9 / +1.5°) but keeps 133 /min of r79 toggles against b8's 79.
- **D4 chooses b8.** The judge may trade the two using these rows.
- The 1.6–3 Hz energy at 5 m/s **rises** 3.85 → 5.49. That is the designed no-twist loop's own value, 5.47 (declared, M2).

**Goal grid not re-run.** The common goal grid (rr / rrq r71b replays, th, tracking, 89 speeds) was not re-run, because it exceeds the 30 s budget. Without a torque word, (b) has arithmetic identical to V298: h = 0 ⇒ no hand freeze in either. So every scenario with no torque word inherits V298's published cells (EVIDENCE by the arithmetic). rrq, which replays r71b's own torque word, is not scored (declared).

---

## 4. Route-79 counterfactuals (`d4_r79.py`, **4.7 s**)

The script uses M3's lane (dir-2 ramp, +10-tick word timing, R² 0.928), with an exact event-driven integer I recursion that includes A3, ICL and the ramp. The V298 row reproduces M3's kept fraction of 0.69 (control).

| rule (hands-off = settled & not steeringPressed) | hand-freeze duty | toggles /min | kept, all | kept <5 / 5–8 / 8–12.5 / >12.5 | eff. Ki <8 m/s | pressed-frame freeze | replayed tap p99 (LSB) |
|---|---|---|---|---|---|---|---|
| V298 512 / 300 | 0.114 | 325 | 0.688 | 0.58 / 0.52 / 0.75 / 0.90 | 1.53 | 0.997 | 120 |
| in-place H1229 / T300 | 0.102 | 319 | 0.697 | 0.59 / 0.55 / 0.74 / 0.90 | 1.59 | 0.991 | 119 |
| in-place H1229 / T450 (N1 ✗) | 0.047 | 127 | 0.760 | 0.65 / 0.60 / 0.81 / 0.97 | 1.75 | 0.991 | 146 |
| motion gate only (b0) | 0.028 | 171 | 0.820 | 0.73 / 0.72 / 0.86 / 0.97 | 2.02 | 0.974 | 164 |
| **(b) b8: LP32 + gate, H512 / T300 on h** | **0.040** | **79** | **0.808** | 0.71 / 0.69 / 0.85 / 0.98 | **1.95** | **0.999** | 162 |
| b7: LP16 + gate | 0.051 | 133 | 0.774 | 0.66 / 0.63 / 0.83 / 0.97 | 1.80 | 0.999 | 157 |
| no hand freeze at all | — | 0 | 0.827 | 0.76 / 0.76 / 0.83 / 0.95 | 2.11 | — | 163 |

- **Hand-frozen share by \|α\|** (0–25 / 25–100 / 100–400 / > 400 deg/s²): V298 0.034 / 0.149 / 0.379 / **0.622**; b8 0.013 / 0.038 / 0.151 / **0.255**.
- **Replayed tap.** The replayed tap is OPEN LOOP: the recorded errors are fed through the new rules. With the I unfrozen in manoeuvres, p99 rises 120 → 162 LSB and the maximum 245 LSB = 80 % of the 307.6 rail. Closed loop the error shrinks, so this is an upper bound (BELIEF). It is the authority note 2 asked for, delivered by the same term.
- **O1 (fork)**, with 600/500 debounced over 5 frames: episodes 415 → 99; never-pressed episodes 345 / 13.8 s → **63 / 2.2 s**; pressed episodes caught **53 / 53**. 1200/1000 would remove all 345 twist episodes but stop following hands between 600 and 1200, so it is not chosen.
- **Setpoint-rate FF census.**
  - **369 one-quantum reversals in 80.5 s of holds (275 /min)**.
  - Five FF parameterisations reach FC/2 in only 24–79 % of stuck-dwell frames, and push the right way on 72–84 %. In holds they fire on 4.7–58 % of frames, with 223–577 sign flips /min.
  - **Rejected.**
- **GB-S13, open loop on the recorded errors:**
  - tap p99 at 10–20 m/s 102 → 118 LSB;
  - small-error tap per degree at 10–20 m/s 34 → 40;
  - unchanged below 10 m/s.

---

## 5. Hazards and fail-safe paths

| event | what happens to h, the freeze and the lane | traced or measured |
|---|---|---|
| Engage, re-engage, the first PID tick after any A2/B2 skip, the op-skip (invalid rate, jr 0x2A164) or a request drop | Honda's epilogue at 0x2A164 sets gp-0x6cf8 = 0x7FFFFFFF. The next hook tick sees Z and sets **h_prev := 0**. h then rebuilds over ~32 ms (a 1229 hand passes 512 in about 17 ms). | EVIDENCE: Ghidra on the epilogue (judge, C3-rev2 §2) and H1's 0x7FFFFFFF cases. This is V288 rev 2's flown init. |
| 0xE4 timeout (frames stop) | During the 510 ms hold the request is still 1, the hook runs and h tracks the hand normally. Then Honda's fault path skips the hook, and init happens on the next engage. The sentinel P-rail of V298 is unchanged by D4. | BELIEF on the timeout ordering (score_time `tmo` covers it for V298; D4's arithmetic is identical when \|h\| ≤ 300) |
| Camera frame (r25 = 0) | The LP updates before the camera gate, so h stays current. The CAM path is V298's: inert lane, I ×0.125/tick. | EVIDENCE (H1 r25 = 0 cases) |
| A real hand, firm (\|bar\| ≥ 1229) | \|h\| > 512 within ~17 ms → freeze. Pressed frames frozen 0.999 (r79 replay). Fade, O1 and Honda's override path are untouched. **The driver always overrides**: the lane is ≤ 2461 T and faded ×0.30 at \|bar\| 2289, as in V298. | EVIDENCE (replay); the override path is unchanged code |
| A light opposing hand (300–511) that holds the wheel still or drags it away | Freezes once \|h\| > 300 (~45 ms delay). Inward holds Δ ≤ +0.30°; **outward Δ +1.7°** at 3–5 m/s. | EVIDENCE: sim (§3) |
| A light hand resisting while the wheel still moves toward the setpoint | Not frozen. The I integrates the shrinking error and A3 bounds it; release goes toward the setpoint, not past it. | BELIEF from the arithmetic, covered by the cs and ov sims |
| Hands-off reaction twist | Rejected by the LP and the gate. Toggles −76 %. | EVIDENCE (r79) |
| Integer ranges | hs and h are s16. hs − h ≤ ±65535 in 32 bits, and h is stored as s16 (\|h\| ≤ max\|hs\|). (abe + 10) is checked as unsigned against 20. | EVIDENCE (H1 edge inputs ±32768) |
| Telemetry task reading gp-0x6a32 | Halfword read of an atomic st.h; read-only | EVIDENCE (decode) |
| The fork on an old firmware | The version tuple accepts A16A or A16B only, so another EPS stays in the existing permanent-fault path. | code read (`interface.py`) |

---

## 6. Pre-registered FAIL criteria for one short drive (any one → do not fly again)

The drive is 15–30 s of engaged turning at 3–10 m/s hands-off, plus one deliberate light-hand hold and release.

| id | FAIL if | instrument |
|---|---|---|
| F1 instrument | P(b4.7 = [h_rec < 0] \| \|h_rec\| ≥ 64) < 0.95 over ≥ 10 s engaged | 0x14A b4 cache + 0x18F |
| F2 identity | (b): the tap replay R² with the D4b rules does not beat V298's rules by ≥ 0.02 on hands-off frames with \|α\| ≥ 100 deg/s². (a): carFw is not A16B, or the 10–20 m/s small-signal slope does not rise. | M3 replay; carFw |
| F3 hand safety | Any release from a hand (steeringPressed falling edge, or \|bar\| > 300 lasting ≥ 0.5 s) followed within 1.5 s by a swing past the setpoint > 8° at ≤ 10 m/s or > 3° above 10 m/s; or the operator reports a lurch at release | wire θ, θsp, bar |
| F4 the mechanism claim | Stall-surges per minute near \|bar\| 300/512 crossings (±0.25 s) against away from them, at 3–10 m/s, are still ≥ 2.0× (route 79: 2.66× and 5.6×), with ≥ 20 turning-seconds. The claim "the freeze relay is the ratchet" is then FALSIFIED: do not iterate this class. | refute_inference's split (unchanged detector) |
| F5 new oscillation | Ring presence > 0.5 %, F7 > 0, or a new 5–30 Hz line (R4) | drive_read instrument |
| F6 hands held | Replayed pressed-frame freeze < 0.95 | replay |
| F7 (a) only | 13–17 Hz engaged/disengaged > 3.5 (r79 2.94), or a 2–6 Hz line at 10–20 m/s | instrument |
| R9 | The operator's words ("stuttery / ratchety" in turns unchanged). F4 is the band reading beside them; he scores the symptom. | operator |

---

## 7. Declared misses

| # | miss | size | why |
|---|---|---|---|
| M1 | The small-correction stick below 10 m/s | Dwells 4.70 / 1.16 /min (0–5 / 5–10) predicted unchanged by both implementations. Sim stuck share 35 % / 28 % unchanged. | Every stick term that would reach it fails on this car's setpoint (jitter, hunting; §3, §4). Stiffness is GATE-2-bound at low speed. Fix path: §8. |
| M2 | Hard-turn 1.6–3 Hz wheel rate (goal FAIL 8.48 vs V282 3.45–4.02) | (b) raises the sim value at 5 m/s 3.85 → 5.49 = the no-twist design value. The route-79 FAIL is predicted to stay or worsen (BELIEF). | The energy is carried by the setpoint, and D4 restores tracking of it. Only a fork-side setpoint filter fixes it. |
| M3 | Outward light-hold release (300–511 word) | +1.7° worst, at 3–5 m/s on a 10–12° baseline | The LP onset delay. b7 halves it at the cost of ×1.7 toggles. |
| M4 | The stall-surge trains are not reproduced by the sim | V298 + twist gives 0 trains in the sim | The ratchet claim rests on r79's enrichment statistic and on the toggle counterfactual (EVIDENCE for the toggles; BELIEF for the felt result). F4 tests it. |
| M5 | Note 2 authority beyond the I: the 120 deg/s cap, the error clip, O1 under real hands | Not moved, apart from the I unfreezing (replayed tap p99 +35 %, open loop) | Out of D4's angle |
| M6 | Note 3 indicator | Not addressed | §8 |
| M7 | O1 debounce delays the setpoint following a real grab by 50 ms | 53 / 53 pressed episodes still caught on r79 | Accepted. The firmware freeze and the fade act within 17 ms. |
| M8 | The rrq goal scenarios were not scored (r71b's torque word) | — | Over the 30 s budget |
| M9 | (a)'s ms_free op-point PM | 20.4 → 15.4 at a = 2.5 | Report-only family |

---

## 8. What I would graft from the other angles

- **From the fork-first angle (D2), and needed for M1 and M2:**
  - A **hysteretic setpoint quantiser**: send a new raw only when the plan has moved ≥ 1 quantum beyond the last sent value. That alone removes all 275 /min one-quantum reversals by construction (§4).
  - A **0.5–1 Hz-limited setpoint path in hard turns** for the 1.6–3 Hz energy.
  - With the setpoint de-jittered, a setpoint-rate friction FF becomes worth re-scoring, and D4's state-word scaffold carries it.
  - **Better: the fork sends the friction direction explicitly** in spare 0xE4 byte-2 bits. That is open until a tracer confirms that Honda's RX handler stores those bits in RAM.
- **From authority (D3):** the O1-release re-slew from the plan rather than the wheel (73 % of cap binding), and the cap / clip sizing. D4's unfrozen I already raises the hands-off tap.
- **From the indicator work:** show the lane torque (parse 0x1AB in the fork) instead of the a_lat request / 0.3247.
- **From the architect (D5):** if the judge raises the low-speed authority envelope (the A3 cap at 4096), re-run D4's N1 outward table, because the outward swing-back scales with the I bound.
- **An in-place LP for free:** if a tracer finds a Honda-maintained low-passed torque word, the LP state word becomes an operand repoint and (b) drops to 0 new RAM.

---

## 9. Files and wall times

| file | wall | what |
|---|---|---|
| `D4-smoothness-first/d4_r79.py` | 4.7 s | route-79 counterfactuals: freeze grid, exact I recursion, O1, FF census, GB-S13 |
| `d4_sim.py` (selftest; run A1 / A2 / B1 / B2 / C) | 7.3; 12.8 / 10.8 / 8.4 / 7.4 / 8.3 s | the nonlinear 1 kHz sim (panel-2 engine + D4Lane, twist, r79 friction member) |
| `d4_tab.py`, `d4_summary.py` | 0.1 s | tables |
| `d4_gate2.py` | 2.9 s | GATE 2 per operating point |
| `d4_gate1.py` | 2.2 s | GATE 1 census of gp-0x6a32 |
| `d4_cave.py` | 5.2 s | (b) listing → bytes, control vs V298, H1 0 / 20000 |
| `d4_mirror_check.py` | 0.7 s | sim lane against the mirror, 0 / 4000 |
| `_scratch/v299_D4/` | — | `d4_r79.txt`, `sim_summary.txt`, `sim_tables.txt`, `gate2.txt`, `gate1.txt`, `d4b_cave.hex`, `D4B_DISASM_ONLY_NOT_AN_ARTIFACT_NO_CRC.bin` (decode only, no CRC) |

**D4b cave** (312 B at 0xC4C00, sha256 `59b90cbdf00422ef4278985b6da483eb579968485fc0dfe14e1ecf772eef83c1`). The builder must relink from `d4_cave.listing_d4b`, not splice this hex, and re-run H1 and the Ghidra decode on the BUILT image.
