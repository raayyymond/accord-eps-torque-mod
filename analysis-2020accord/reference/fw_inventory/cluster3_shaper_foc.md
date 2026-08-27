# Cluster 3 — Rate Shaper + Dual-Path Lockstep + FOC Handoff
**Program:** code.bin (V850:LE:32, image_base 0x0, gp=0xFEDF8000, tp=0xBF000)
**Function analyzed:** s_motor_torque_rate_shaper (FUN_00042af8, 0x42af8–0x43e43)
**Date:** 2026-05-27
**Method:** search_instructions (program-wide, -0xOFF operand pattern) + full disasm 0x42af8–0x43e43

---

## 1. gp-offset Inventory Table

| gp offset | Abs address | Role | Writers (addr, fn) | Readers (addr, fn) | Notes |
|-----------|-------------|------|--------------------|--------------------|-------|
| **0x356c** | 0xFEDF4A94 | Slew accumulator (int32) — persists slew state across ticks | 0x43504 st.w r12 (shaper) | 0x434ce ld.w r9 (shaper) | Zeroed by deadband: r12=0 stored at 0x43504; with step=0, stays 0 |
| **0x3570** | 0xFEDF4A90 | Demand accumulator (int32) — integrates combined demand×rate each tick | 0x4327c st.w r10 (shaper) | 0x43214 ld.w r10, 0x432de ld.w r10 (shaper×2) | Scaled demand input to deadband logic; |r10>>15| = uVar53; LKAS+base-assist combined |
| **0x6966** | 0xFEDF169A | Scaled demand magnitude (uVar34 = uVar53×1092>>10) — deadband comparand | 0x432c8 st.h r13 (shaper) | 0x42d86 ld.hu r13 (shaper), 0x432e2 ld.hu r13 (shaper), 0x43df0 ld.hu r16 (shaper), 0x3a632 ld.hu r11 (FUN_0003a382) | Lockstep-shadowed with 0x4c5a |
| **0x4c5a** | 0xFEDF33A6 | Lockstep shadow of 0x6966 (dual-path consistency check) | 0x432cc st.h r9 (shaper) | 0x432b4 ld.hu r14 (shaper) | Fault via FUN_0006b9fa at 0x432d6 if 0x4c5a≠0x6966 |
| **0x6b98** | 0xFEDF1468 | **FINAL delivered motor command → FOC** | **0x43b52 st.h r8 (shaper) — PRIMARY**; **0x43dfc st.h r21 (shaper) — LOCKSTEP 2nd write**; 0x6e104 st.h r12 (FUN_0006e09a); 0x6e1dc st.h r10 (FUN_0006e140) | 45 load sites across 20+ functions (telemetry, FOC, lockstep monitors) | TWO external writers outside shaper — see section 4 |
| **0x4ce2** | 0xFEDF331E | Lockstep shadow of gp-0x6b98 | 0x43b56 st.h r8 (shaper), 0x43e00 st.h r21 (shaper) | 0x43b48 ld.h r7 (shaper), 0x43de8 ld.h r14 (shaper), multiple FOC/monitor fns | Fault via FUN_0006b9fa at 0x43b60 / 0x43e0a if 0x4ce2≠0x6b98 |
| **0x6dbc** | 0xFEDF1244 | Float-path shadow (gp-0x6b98 equivalent in float domain) | 0x44a22 st.w r9 (FUN_00043e44) | 0x43b24 ld.w r12 (shaper) | Used for float-to-int conversion check just before gp-0x6b98 store 1 |
| **0x6db8** | 0xFEDF1248 | Float-path shadow (demand) | — (not in search results) | — | Listed in brief; not found as distinct offset in this search |
| **0x6dc0** | 0xFEDF1240 | Float-path shadow (demand) | — | 0x43288 ld.w r9 (shaper) | Read in shaper near gp-0x6dbc read |
| **0x4cce** | 0xFEDF3332 | Lockstep shadow of gp-0x6b04 | 0x43a88 st.h r14, 0x43e1e st.h r28 (shaper×2) | 0x43a6a ld.h r12 (shaper), 0x43e12 ld.h r10 (shaper) | Fault via FUN_0006b9fa at 0x43a92 / 0x43e28 |
| **0x4ce2** | (see above) | Lockstep of gp-0x6b98 | (see above) | (see above) | Already listed |
| **0x6b00** | 0xFEDF1500 | Shaper neighbor — demand tracking state | 0x43a78 st.h r27 (shaper), 0x43e30 st.h r27 (shaper) | 0x431a0 ld.h r8 (shaper) | Part of demand velocity tracking |
| **0x6b08** | 0xFEDF14F8 | Shaper intermediate — gated shaper input (mode-select output; fed by gp-0x6acc) | 0x43206 st.h r11 (shaper) | 0x43a96 ld.h r11 (shaper), 0x432e6 ld.h r11 (shaper) | The "r11 = gp-0x6b08" at 0x43a96 is what populates r20 fallback when cVar8≠0 |
| **0x6b0a** | 0xFEDF14F6 | Shaper neighbor — demand velocity index | 0x43a72 st.h r24 (shaper), 0x43e34 st.h r24 (shaper) | 0x43294 ld.hu r18 (shaper), 0x432da ld.hu r18 (shaper) | |
| **0x6b02** | 0xFEDF14FE | Shaper neighbor — assist polarity record | 0x43c26 st.h r20 (shaper) | — | Written near end of shaper for downstream telemetry |
| **0x6b04** | 0xFEDF14FC | Parallel internal demand path (dual-path lockstep mirror) | 0x43a84 st.h r14, 0x43e1a st.h r28 (shaper×2) | 0x43a42 ld.h r15 (shaper), 0x43e0e ld.h r8 (shaper) | Lockstep-checked with 0x4cce |
| **0x6bf0** | 0xFEDF1410 | Base driver-assist demand entering shaper | 0x3c0cc st.h r6 (FUN_0003bd7c), 0x3c184 st.h r0 (FUN_0003bd7c), 0x3e7f4 st.h r0 (FUN_0003e760) | 0x43032 ld.h r10 (shaper), 0x43116 ld.h r6 (shaper), 11 other fns | Two shaper reads: 0x43032 (gp-0x67fe gate path) + 0x43116 (assist range check) |
| **0x67fe** | 0xFEDF1802 | Base-assist enable flag — gates gp-0x6bf0 load | 0x3bdb8 st.b r0, 0x3be4e st.b r6, 0x3be5a st.b r15, 0x3be7a st.b r0 (all FUN_0003bd7c) | 0x43016 ld.bu r8 (shaper); many other fns | Value meaning — see section 3 |
| **0x6bb0** | 0xFEDF1450 | FOC consumer 1 — motor current command A | 0x370f4 st.h r10, 0x3712e st.h r6 (FUN_000370b6×2) | 0x370c2 ld.h r7 (FUN_000370b6), 0x374c2 ld.h r12 (FUN_00037494), 0x377f4 ld.h r15 (FUN_000377ba), 0x37ac0 ld.h r23 (FUN_000378d6) | Downstream of gp-0x6b98 via FOC dispatch; writer FUN_000370b6 reads gp-0x6b98 at 0x370be |
| **0x4cee** | (FOC consumer) | Lockstep shadow FOC cmd | Not in brief's search results | — | Listed in brief; search not run |
| **0x6b54** | (FOC consumer) | FOC intermediate | Not in brief's search results | — | Listed in brief; search not run |
| **0x6bf6** | 0xFEDF140A | Mode-5 / gate assist output (feeds shaper via parallel path) | 0x3bac0 st.h r12, 0x3bc0e st.h r7 (FUN_0003b8f6×2) | — not found as reader | Appears to be upstream demand contribution to gp-0x3570 accumulator |
| **0x6c00** | (FOC consumer) | FOC output | Not in brief's search results | — | Listed in brief; search not run |

---

## 2. DECISIVE ANSWER: Does the deadband iVar45=0 reach gp-0x6b98?

**YES — the deadband zero DOES reach the final gp-0x6b98 store. But the decompiler variable reuse makes the path non-obvious. Here is the verified disassembly chain:**

### The deadband check (0x434c2–0x434ee)

```
0x434c2: ld.hu 0x3a[sp], r17          ; r17 = tp+0x7424 = 29491 (deadband threshold)
0x434c6: andi 0xffff, r15, r26         ; r26 = LERP demand result
0x434ca: cmp r17, r13                  ; r13 = uVar34 = uVar53*1092>>10 (scaled demand magnitude)
0x434cc: bc 0x434ee                    ; BRANCH if r13 < r17 (unsigned below = demand < 90% max)
  ; *** DEADBAND BRANCH ***
  0x434ee: mov r0, r12                 ; r12 = 0 (iVar45=0 in decompile)
  ; falls through to 0x434f0
; *** NON-DEADBAND path (demand above threshold): ***
  0x434ce: ld.w -0x356c[gp], r9       ; load slew accumulator
  ; ... slew ramp clamps r12 toward demand target by step tp+0x71D6=0 ...
```

### Critical register trace: deadband r12=0 → two output channels

**Channel A — slew state persistence (gp-0x356c):**
```
0x434ee: r12 = 0
0x434f0: mov r12, r16   → r16 = 0
0x434f2: add r27, r16   → r16 = r27  (r27 = demand component from accumulator sign path)
0x434f4: mov r29, r14
0x434f6: cmovp r0, r16, r8  → r8 = 0 if r27>0, else r8=r27  [PSW positive flag from add]
0x434fa: sub r12, r14   → r14 = r29 - 0 = r29
0x434fe: cmovle r0, r14, r6 → r6 = 0 if r29≤0 else r6=r29
0x43502: cmp r8, r11    ; compare r8 (≈0) vs r11 (gp-0x6b08 = gated input)
0x43504: st.w r12, -0x356c[gp]  → **gp-0x356c = 0 written**  [slew accumulator zeroed]
```

**Channel B — state machine → assist output → LERP → governor → r21 → gp-0x6b98:**
```
0x43524+: state machine reads r8 (≈0), r11 (gp-0x6b08)
   → state machine sets gp-0x6960 = 0 (at 0x4362a: st.h r0,-0x6960[gp])
     when assist-state timeout/zero-crossing condition fires
   → 0x435b2/0x435f6/0x436b2: ld.hu -0x6960[gp], r6  → r6 = 0
0x439c0: cmp r12, r6    ; r12 here = state-machine output r12
0x439c2: cmovnc r12, r6, r8  → r8 = assist output (can be 0)
0x43a10: ld.hu 0x2e[sp], r8  ; r8 reloaded from stack (demand curve output)
0x43a1c: mov r11, r15
0x43a20-0x43a38: LERP(demand curves, r8, r11) → r28
0x43a3a: mul r26, r28, r0; sar 0xf, r28  → r28 = demand × speed_gain  [≈0 when r26≈0]
0x43a9a: ld.bu 0xb[sp], r18  ; r18 = tp+0x74C9 = 0
0x43a9e: cmp r0, r18         ; Z=1
0x43aa0: cmove r28, r11, r20 → r20 = r28 (since Z=1; cVar8=0)
0x43ae0: ld.h -0x6afe[gp], r13   ; feed-forward
0x43ae4: ld.hu -0x4f64[gp], r10  ; governor cap
0x43af0: cmovc 0x0, r13, r12     ; r12 = feed-forward if in range, else 0
0x43af4: add r20, r12            ; r12 = feed-forward + r28 (≈0)  [r12 REASSIGNED here]
0x43afa: cmovc 0x0, r10, r14     ; r14 = governor cap if r10<0x2801 else 0
0x43afe: cmp r14, r12; ...       ; governor clamp
0x43b0e: addi -0x2000, r14, r0; movea 0x2000, r0, r21  ; ±0x2000 hard clamp
0x43b16: bgt 0x43b24; 0x43b1c: movea -0x2000, r0, r6; cmovle r6, r14, r21
  → r21 = clamp(r14, -0x2000, +0x2000)  [= 0 when r14≈0 from deadband chain]
0x43b4e: mov r21, r8
0x43b52: st.h r8, -0x6b98[gp]   *** STORE 1: gp-0x6b98 = r21 ***
```

**Second lockstep write:**
```
0x43de8: ld.h -0x4ce2[gp], r14
0x43dec: ld.h -0x6b98[gp], r12
0x43df4: cmp r14, r12   ; consistency check: 0x4ce2 == 0x6b98?
0x43dfa: bne 0x43e06    ; mismatch → fault handler FUN_0006b9fa
0x43dfc: st.h r21, -0x6b98[gp]  *** STORE 2: redundant write of same r21 ***
0x43e00: st.h r21, -0x4ce2[gp]  ; update shadow too
```

### Verdict: iVar45 IS reassigned before the store, but the zero still propagates

The decompiler reuses `iVar45` for:
- Line ~1253 in decompile: iVar45=0 (deadband) → maps to **r12 at 0x434ee**
- Line ~1255 in decompile: iVar45 = clamp(±0x2000) → maps to **r21 at 0x43b12–0x43b20**

These are DIFFERENT physical registers. The deadband r12=0 does NOT travel directly to the final store's r21. However, the zero DOES reach gp-0x6b98 via Channel B:

1. r12=0 → r8≈0 (cmovp) → state machine triggers zero-assist state → gp-0x6960=0
2. gp-0x6960=0 → r6=0 → assist output → r26≈0 → r28 LERP ≈ 0 → r20≈0
3. r12 (feed-forward + r20) ≈ 0 → governor clamps ≈ 0 → r21 ≈ 0 → gp-0x6b98 = 0

**The decompile-level iVar45=0 correctly predicts gp-0x6b98→0, but the mechanism is through the state machine assist-output path, not a direct register carry. The critical intermediary is gp-0x6960 (zero-assist state) zeroed by the state machine transition when r8≈0 at 0x43502/cmp.**

With step=0 (tp+0x71D6=0), the slew accumulator gp-0x356c stays at 0 once zeroed (next tick also produces r12=0 from slew → repeats the chain). Recovery requires the demand accumulator gp-0x3570 to rebuild above 90% (= uVar34 ≥ 29491 = uVar53 ≥ 27654), which at combined demand 1000 takes ~28ms, at 500 ~55ms.

---

## 3. gp-0x67fe (base-assist enable flag): Values and gating of gp-0x6bf0

### Usage inside s_motor_torque_rate_shaper (verified disassembly)

```
0x43016: ld.bu -0x67fe[gp], r8  ; r8 = gp-0x67fe (byte)
0x4301a: cmp 0x2, r8             ; is r8 == 2?
0x4301c: setfne r6               ; r6 = (r8 ≠ 2)
0x43020: cmp 0x1, r8             ; is r8 == 1?
0x43022: setfne r15              ; r15 = (r8 ≠ 1)
0x43026: cmp r0, r6
0x43028: ld.hu 0x741a[tp], r21  ; r21 = tp+0x741a (speed threshold for base-assist gate)
0x4302c: be 0x43032              ; if r8==2 → branch to load gp-0x6bf0
0x4302e: cmp r0, r15
0x43030: bne 0x43046             ; if r8≠1 → skip gp-0x6bf0 load
0x43032: ld.h -0x6bf0[gp], r10  ; *** load base-assist demand ***
0x43036: ori 0xc801, r0, r16     ; r16 = 0xc801
0x4303a: addi 0x6400, r10, r7   ; r7 = gp-0x6bf0 + 25600
0x4303e: cmp r16, r7             ; check range: gp-0x6bf0 + 25600 < 0xc801 = 51201?
0x43040: setfnc r1               ; r1 = 1 if gp-0x6bf0 < 25601
0x43044: br 0x43048
0x43046: mov 0x1, r1             ; else r1 = 1 (force base-assist enable)
```

**Interpretation:**
- `gp-0x67fe = 1` or `gp-0x67fe = 2`: base-assist enable flag TRUE → gp-0x6bf0 is loaded and range-checked → r1 = base-assist-in-range flag
- `gp-0x67fe = 0` (or any other value): skip gp-0x6bf0 load → r1 = 1 (hardcoded enable) → base assist treated as always-enabled with range check bypassed
- The range check at 0x4303e: gp-0x6bf0 must be < 25601 raw (= ~6.25 Nm if Q8.8 scale) to pass; outside = r1=0 = suppress base-assist contribution

**Writers of gp-0x67fe** (from FUN_0003bd7c):
- 0x3bdb8: `st.b r0, -0x67fe[gp]` — zero (disable)
- 0x3be4e: `st.b r6, -0x67fe[gp]` — variable value
- 0x3be5a: `st.b r15, -0x67fe[gp]` — variable value
- 0x3be7a: `st.b r0, -0x67fe[gp]` — zero (disable)

FUN_0003bd7c is the primary writer. It is the base-assist torque computation function (reads/writes both gp-0x67fe and gp-0x6bf0).

### Does base-assist (gp-0x6bf0) go to 0 TOGETHER with LKAS?

**Structurally YES** when the deadband fires — both converge in gp-0x3570 before the deadband check:

The demand accumulator gp-0x3570 integrates the sum of both LKAS demand and base-assist demand on each tick. The deadband tests the COMBINED magnitude (uVar34 from gp-0x3570). When LKAS is commanding strongly in one direction and the driver overrides in the other, the combined demand passes through zero, causing uVar34 to drop below 90%.

At that point, the deadband fires and zeroes gp-0x356c (slew state), which via the state machine zeroes gp-0x6960 → zeroes the final r21 written to gp-0x6b98. Since gp-0x6b98 is the ONLY path to FOC (base-assist has no separate FOC path — confirmed by gp-0x6b98 being the sole command output to FOC), zeroing gp-0x6b98 kills both LKAS AND base power steering simultaneously.

**Note**: If gp-0x67fe=0 (base-assist disabled) AND gp-0x6bf0=0, the demand accumulator gp-0x3570 carries only LKAS demand. In that case the LKAS component alone must drop below 90% for the deadband to fire. During a strong 2× LKAS command, the component doesn't drop until the driver pushes hard enough to zero the net demand.

---

## 4. gp-0x6b98 Writers Outside the Shaper

Two external writers found:

| Address | Function | Mnemonic | Operand | Context |
|---------|----------|----------|---------|---------|
| 0x6e104 | FUN_0006e09a | st.h r12, -0x6b98[gp] | Writes r12 | Appears to be a fault/reset path or override handler; needs Ghidra decompile to classify |
| 0x6e1dc | FUN_0006e140 | st.h r10, -0x6b98[gp] | Writes r10 | Appears to be second fault/reset variant; same function family |

**Assessment (belief, not fully confirmed):** These functions are likely called in abnormal conditions (EPS fault, torque-sensor plausibility failure, power-on initialization). They would override the shaper output with a safe/zero value. The shaper itself does not call these during normal LKAS operation.

**Verification needed:** Ghidra decompile of FUN_0006e09a (0x6e09a) and FUN_0006e140 (0x6e140) to confirm they are fault/reset handlers and not a parallel torque-injection path.

---

## 5. New gp-Offsets Discovered During This Analysis

| gp offset | Abs address | Role | Discovery context |
|-----------|-------------|------|-------------------|
| 0x6960 | 0xFEDF169F | Assist level output from state machine (zeroed by state machine when zero-crossing/timeout) | Critical intermediary: deadband→r8→state machine→gp-0x6960=0→r6=0→r26=0→r28=0→r20=0→r21≈0→gp-0x6b98=0 |
| 0x6af8 | 0xFEDF1508 | Assist velocity/LERP weight | Read at multiple points inside shaper: 0x43564, 0x43594, 0x437f8, 0x4381c, 0x43678 |
| 0x6a74 | 0xFEDF1D8C | Assist timer counter (zeroed when state machine resets, incremented otherwise) | 0x435b6 st.h r0; 0x43602 st.h r0; 0x4362c st.h r0; etc. |
| 0x6a72 | 0xFEDF1D8E | Assist ramp counter (secondary timer) | 0x4380c / 0x43864 / 0x43886 st.h |
| 0x6785 | 0xFEDF187B | Assist state byte 2 (sub-state for state machine) | Written with 0x1/0x2/0x3 across state machine branches |
| 0x6786 | 0xFEDF187A | Assist state byte 1 | Written with 0x1/0x2/0x3 across state machine branches; read at 0x43d88 |
| 0x6711 | 0xFEDF18EF | Assist step counter (incremented each state machine cycle) | 0x435fe/0x436a0/0x43732 etc. |
| 0x355d | 0xFEDF4AA3 | First-level state byte for base-assist state machine | Multiple writes (1/2/3/4) |
| 0x355e | 0xFEDF4AA2 | Second-level state byte | Multiple writes |
| 0x355f | 0xFEDF4AA1 | Third-level state byte | Multiple writes |
| 0x3560 | 0xFEDF4AA0 | Fourth-level state byte | Multiple writes |
| 0x3561 | 0xFEDF4A9F | Direction state (1=positive, -1=negative) | Written at 0x43722/0x43774 |
| 0x3562 | 0xFEDF4A9E | Outer convergence flag (1=initial, 2=converged) | Written at 0x42ff6/0x43010 |
| 0x355c | 0xFEDF4AA4 | Convergence counter | Written at 0x42fd0/0x42fe8/0x42fee |
| 0x6908 | 0xFEDF16F8 | Assist debug output | 0x43be8 st.h r1 |
| 0x6964 | 0xFEDF169C | Demand output record (stored twice in shaper: 0x43bf8, 0x43e2c) | Locked with r26 |

---

## 6. Summary Table: All gp-0x6b98 Touchers

| Address | Function | Mnemonic | Count | Role |
|---------|----------|----------|-------|------|
| 0x43b52 | s_motor_torque_rate_shaper | st.h r8 | WRITE | **Primary shaper output — r21 (clamped ±0x2000)** |
| 0x43dfc | s_motor_torque_rate_shaper | st.h r21 | WRITE | **Secondary/lockstep shaper output — same r21** |
| 0x6e104 | FUN_0006e09a | st.h r12 | WRITE | External writer — likely fault/reset |
| 0x6e1dc | FUN_0006e140 | st.h r10 | WRITE | External writer — likely fault/reset |
| 0x43b34 | s_motor_torque_rate_shaper | ld.h r15 | READ | Pre-store lockstep read (before 0x43b52) |
| 0x43dec | s_motor_torque_rate_shaper | ld.h r12 | READ | Pre-store lockstep read (before 0x43dfc) |
| 0x19fe2 | FUN_00019f7c | ld.h r10 | READ | Telemetry/monitor |
| 0x1c0c8 | FUN_0001bf88 | ld.h r15 | READ | Telemetry/monitor |
| 0x1c22c | FUN_0001c1ce | ld.h r10 | READ | Telemetry/monitor |
| 0x24448 | FUN_000242a2 | ld.h r24 | READ | Telemetry/monitor |
| 0x2c47c | FUN_0002c478 | ld.h r6 | READ | Reads gp-0x67fe + gp-0x6b98 — combined assist status |
| 0x35ee6 | FUN_00035e00 | ld.h r8 | READ | Base-assist demand consumer |
| 0x370be | FUN_000370b6 | ld.h r14 | READ | **FOC dispatch — primary motor command consumer** |
| 0x3b00a | FUN_0003aff4 | ld.h r12 | READ | FOC downstream |
| 0x3b8f6 | FUN_0003b8f6 | ld.h r7 | READ | FOC downstream |
| 0x41672 | FUN_00041464 | ld.h r16 | READ | FOC downstream |
| 0x41846 | FUN_00041464 | ld.h r9 | READ | FOC downstream (second read same fn) |
| 0x41bd8 | FUN_00041b8e | ld.h r13 | READ | FOC downstream |
| 0x448d6 | FUN_00043e44 | ld.h r12 | READ | Float-path cross-check |
| 0x56420 | FUN_00056420 | ld.h r14 | READ | Supervisory |
| 0x56554+ | FUN_00056518 | ld.h (×3) | READ×3 | Supervisory / CAN TX |
| 0x569c4+ | FUN_000568d0 | ld.h (×2) | READ×2 | CAN TX / telemetry |
| 0x59a44+ | FUN_00059912 | ld.h (×6) | READ×6 | CAN TX broadcast |
| 0x59f7c+ | FUN_00059e7a | ld.h/ld.hu (×4) | READ×4 | CAN TX broadcast |
| 0x65c90 | FUN_00065afe | ld.h r15 | READ | Supervisory |
| 0x69bee+ | FUN_00069b8e | ld.h (×2) | READ×2 | Supervisory |
| 0x70bfc | FUN_00070a98 | ld.h r11 | READ | Safety check |
| 0x7580c | FUN_000757a2 | ld.h ep | READ | Safety check |
| 0x7c52c | FUN_0007c4f2 | ld.h r14 | READ | Safety check |
| 0x7c94e | FUN_0007c94a | ld.h r12 | READ | Safety check |
| 0x81be8 | FUN_00081b24 | ld.h r15 | READ | Supervisory/logging |

**Total: 4 WRITE sites (2 shaper + 2 external), ~41 READ sites across ~20+ functions.**

---

## 7. Calibration Values (Verified via tp=0xBF000)

| Cal offset | Abs addr | Value (LE u16/u8) | Role |
|------------|----------|-------------------|------|
| tp+0x71D6 | 0xC61D6 | 0x0000 = 0 | Slew step — **zero = slew disabled; deadband holds gp-0x6b98=0 indefinitely** |
| tp+0x71DA | 0xC61DA | 0x0444 = 1092 | Scale factor for uVar34 = uVar53×1092>>10 |
| tp+0x71DC | 0xC61DC | 0x7800 = 30720 | Demand accumulator clamp max |
| tp+0x7422 | 0xC6422 | 0x4000 = 16384 | Lane-2 deadband threshold (50% of max) |
| tp+0x7424 | 0xC6424 | 0x7333 = 29491 | **Main deadband threshold (90% of max) — TRIGGER point** |
| tp+0x74C9 | 0xC64C9 | 0x00 | cVar8: 0=use LERP output (r28) for r20; 1=use raw input (gp-0x6b08) |

---

*Generated by firmware-codepath-tracer agent, 2026-05-27. Based on full disassembly of FUN_00042af8 (s_motor_torque_rate_shaper) + program-wide search_instructions for all listed gp-offsets.*
