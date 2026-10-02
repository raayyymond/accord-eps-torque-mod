# DESIGN V299 — D1 (firmware-first, minimal): replace the hand-word integrator freeze with a sign-referenced integral bound

**Status: DESIGN ONLY.** Nothing was built, flashed or sent. The fork, the firmware images, the golden model and the
kit's STATE/lineage were not touched. Ghidra was used read-only (`disassemble_bytes dry_run:true` on
`ADVIG_V298_177abf04.bin`). Author: designer **D1-firmware-minimal**, a SUBAGENT in the V299 judge-panel round.
**Labels.** EVIDENCE = measured on the wire or rlog, read from the V298 image, executed by an interpreter, or produced by an
unchanged kit scorer (the method is named). BELIEF = modelled or inferred. The operator scores symptoms; this page scores bands.

**Scripts** (all under `analysis-2020accord/studies/angle_loop/v299_design/D1-firmware-minimal/`, outputs in `out/`; wall
times measured): `d1_cells.py` 0.04 s · `d1_427_check.py` 6.0 s · `d1_r79.py` 3.3 s · `d1_gate2.py` 20.4 s (`kd` mode
17.7 s) · `d1_gate2_report.py` 1.0 s · `d1_gate2_table.py` 3.2 s · `d1_n1.py` 29.1 s · `d1_time.py` 22.9 s
(`control` mode ≈ 10 s) · `d1_cave.py` 13.9 s · `d1c_mirror.py` 0.3 s · `d1_bar_cells.py` 0.05 s.
⚠ The first `d1_time.py` run took 113.9 s (one batch per member). It broke the < 30 s rule; the script was restructured
to one batch per scenario. Its output is kept as `out/d1_time_run1_capC8k.txt` because it holds the cap-8192 rows (§3.3).
The big GATE-2 row arrays are in `_scratch/v299_D1/`.

---

## 0. The answer in one page

**Recommended: implementation (b) "D1c".** It is three edits inside V298's existing cave. Nothing else in the firmware moves.

| # | edit | bytes | loop term |
|---|---|---|---|
| 1 | hard-hand freeze threshold `movea 512` → `movea 1229` (= 1200 raw × 1.024, Honda's stock steeringPressed level) | imm16 | I freeze only under a pressed-level hand |
| 2 | the opposing-hand freeze clause (`movea 300 … xor r16,r9 ; blt FRZ`) **removed** | −16 B | the reaction-twist freeze is gone |
| 3 | an **asymmetric A3 bound**: `mov r9,r13 ; xor r16,r13 ; bge AS ; mov 0,r9` after `ld.h -0x6a00[gp],r9` | +8 B | when sign(θ) ≠ sign(E′), the I may wind toward centre only to B = 1250 S (≈ 200 T, the friction allowance) |

- **Cave size:** 260 → **252 B** (210 code + 42 table), relinked. **RAM written: 0.** **New state words: 0.**
- **Fixed:** E1/E2/B2/A2/E4/HOOK/OPH, every cal cell, the G table, Kp/Ki/Kd, the camera gate, the op-skip and the fade
  are all byte-identical to V298. The small-signal loop is V298's, so GATE 2 is V298's (EVIDENCE §3.1).
- **Fork:** one change, the torque bar (§2.3). It now shows the EPS's own 0x1AB lane-torque tap as a fraction of the rail.

**Why.** Two refuters ranked the integrator freeze as the ratchet's measured mechanism, and route 79 shows it.

- **Stall-surges cluster at the freeze thresholds.** They are enriched near |bar| crossings of 300/512:
  80.7 vs 30.3 /min at 5–10 m/s, and 47.4 vs 8.4 /min at 0–5 m/s. V282 and V294, which have no freeze, show no such
  enrichment (REFUTE-inference §3).
- **The freeze discards integration hands-off,** because the wheel's own reaction twist trips it:
  - the hands-off torque word has p90 607–681 below 8 m/s;
  - V298's rule discards **28 %** of commanded integration hands-off, and **38–42 %** below 8 m/s;
  - it toggles **325 /min** (EVIDENCE: `d1_r79` A, replay validated R² 0.928).
- **Under D1c the same wire gives:** 0.8 % discarded, 13 toggles/min, and stall-surge events near a toggle 9/27 and
  26/68, against V298's 22/27 and 56/68 (`d1_r79` A, B).

**Why the cave, and not cal.** No threshold separates a light opposing hand from the reaction twist; both live at
300–1200 words.

- **Cal-only (a)** raises both immediates to 1229. That fixes the freeze, but it **fails the N1 light-hand release lens**:
  - outward 2× hold at 12.5–22 m/s: **15.9°** lurch vs V298 4.7°;
  - 5° straight nudge: 8.0° vs 0.8° (EVIDENCE `d1_n1`).
- **D1c's sign-referenced bound restores N1 to the judge's form:**
  - outward ≥ 12.5 m/s: 5.05°;
  - inward partial drag: 7.13°;
  - nudge: 3.64° (all < 8°).
  - The costs are declared in §7.
- The structure, not the cal, limits this loop. So D1 designs the cave, per the 2026-09-30 ruling.

**Rejected by this round's own evidence** (do not re-propose without new data):

| lever | evidence against |
|---|---|
| A3 low-speed cap 4096 → 8192 (the authority ceiling) | Sim: hands-off hard turn-in overshoot **11.8°** vs 1.0° at 3.1 m/s, and 7.3° vs 2.2° at 5 m/s |
| Kp(\|θsp\|) schedule ×1.5 / ×2 (cal, Kp knots keyed on the demand index = 0.618·\|θsp\|) | GATE 2: 122 / 940 PM fails, worst −9.9° / −20°, at physical low-speed op-points |
| Kd(\|θsp\|) lowered at \|θsp\| ≥ 36° (to stop D braking unwinds) | GATE 2: Kd 36 gives 44 fails, worst −6.3° at 8 m/s; Kd 24 gives 579 |
| highway G ×1.25 (for the small-correction stick at speed) | GATE 2: 30 fails, −6.4° at 26.9 m/s on the a 1.0 op-point |
| motion-gated opposing freeze "D1b" (+14 B) | Keeps N1, but keeps 171 toggles/min and the toggles near the 0–5 m/s stalls (22/27) |

**What D1 cannot fix** (§7):
- the O1 relay and its re-slew (the fork's);
- the 120 deg/s cap and the error clip;
- the hand-on yield in AOL intersection turns (by design);
- the low-speed authority ceiling (A3 cap; GATE 2 / overshoot-bound);
- the small-correction stick (needs feed-forward, not gain);
- D braking in unwinds;
- the 1.6–3 Hz criterion, which D1c makes slightly worse by tracking the setpoint better.

---

## 1. The mechanisms D1 addresses: the number each must move, and the prediction

### 1a. Route-79 replay numbers (EVIDENCE)

These are open-loop replays with each rule applied to the recorded wire (`d1_r79`).

| mechanism (r79, EVIDENCE) | measured | D1c predicted |
|---|---|---|
| hand-freeze duty, hands-off, all speeds | 11.4 % (26.2 % below 5 m/s, 26.2 % at 5–8 m/s) | **0.4 %** (0.7 / 1.2 %) |
| integration discarded hands-off (\|inc\|-weighted) | 28.3 % (37.7 / 41.5 % below 8 m/s; refuter's \|E·G\| form: 26 / 37 %) | **0.8 %** (0.7 / 2.0 %) |
| freeze toggles, hands-off | 325 /min (409 / 555 below 8 m/s) | **13 /min** (19 / 46) |
| real hand (steeringPressed) still frozen | 99.7 % of pressed ticks | **97.3 %** |
| stall-surge events with a freeze toggle within ±0.25 s (M4 detector; wire rule) | 0–5 m/s 22 of 27 · 5–10 m/s 56 of 68 | **9 · 26** |
| turning time within ±0.25 s of a toggle | 49 % / 65 % | **24 % / 34 %** |

### 1b. Predictions that need the closed loop or a model (BELIEF)

| mechanism | measured | D1c predicted |
|---|---|---|
| effective integral below 8 m/s | 1.0–1.2 /s (refuter); 1.45–1.62 /s (M3); design 2.79 | ≈ 2.7 /s |
| stall-surge rate near vs away from \|bar\| 300/512 crossings, 5–10 m/s | 80.7 vs 30.3 /min | no enrichment (≤ 1.5×), toward the free 30 /min |
| ratchet trains per minute of turning (0–5 / 5–10 / 10–20 m/s) | 3.1 / 4.7 / 4.2 (V282 0–2.2) | toward V282, below 2.5 at 5–10 |
| lane tap in hands-off manoeuvres | hard-frame p99 135 LSB, peak 183 (59 % of rail) | open-loop replay: p99 149 → **194**, max 199 → 245. The closed-loop rise is smaller. |
| hard turn-in response with the reaction twist, 3.1 / 5 / 8 m/s (sim, hardT) | V298 hard_ratio 0.60 / 0.64 / 0.73; overshoot 0.6 / 0.3 / 0.0° | **0.78 / 0.90 / 1.00**; overshoot 0.7 / 2.2 / 3.1° (= the design's no-twist value) |

The open-loop tap replay feeds V298's own errors, which grew while V298 froze. That is why its rise overstates the
closed-loop rise.

### 1c. The bar (EVIDENCE, `d1_bar_cells`)

| quantity | measured | predicted |
|---|---|---|
| \|corr\| between the bar and the delivered torque | 0.135; pinned at full on 59.7 % of engaged time | the bar **is** the 0x1AB tap |
| bar distribution on r79, replayed | — | p50 0.05, p90 0.17, p99 0.35, max 0.60 |
| pinned (≥ 0.9) | 59.7 % | **0 %** |

---

## 2. Implementations

### 2.1 (a) Cal-only: immediates inside V298's cave, no relink

**Verdict: NOT FOR FLIGHT.** It is listed to prove that the structure, not the cal space, limits this loop.

**The cells** (EVIDENCE: bytes read from the V298 image by `d1_bar_cells`; forms decoded by Ghidra dry-run at
`0xC4C62`/`0xC4C6A`):

| cell | addr | stock | V298 bytes | (a) bytes | term |
|---|---|---|---|---|---|
| hard freeze THR | `0xC4C62` | — (cave) | `20 6e 00 02` = movea 512 | `20 6e cd 04` = movea 1229 | I frozen iff \|gp-0x4f68\| > THR |
| opposing THR | `0xC4C6A` | — (cave) | `20 6e 2c 01` = movea 300 | `20 6e cd 04` = movea 1229 | The clause becomes unreachable: it is reached only when \|tq\| ≤ 1229 and needs \|tq\| > 1229 |
| *(a2, optional)* GB-P knot 0 G | `0xC4CDC` | — | `9a 04` = 1178 | `78 05` = 1400 | low-speed stiffness ×1.19 at ≤ 3.1 m/s, fading to ×1 at 8 m/s |
| *(a2)* GB-P knot 0 S (Q12) | `0xC4CDE` | — | `11 04` = 1041 | `ec 00` = 236 | keeps segment 0 linear to knot 1 (1843, 1465) |

- **Bytes changed:** 4 (a) / 8 (a2), plus the main-block CRC.
- **What it does:** the freeze rule becomes D1a. Every row of §1 moves as D1c does (`d1_r79` A: D1a and D1c share the
  hand rule).
- **What it breaks (EVIDENCE `d1_n1`):** with no opposing clause and a symmetric bound, an outward light hand lets the I
  swing from +hold to −(16|θ|+B), or −(64|θ|+B) above 12.5 m/s.

  | N1 scenario | (a) lurch | V298 lurch |
  |---|---|---|
  | out_2_511 at 12.5–22 m/s | 15.9° | 4.7° |
  | out_1.5 at 8–12.5 m/s | 16.0° | 7.2° |
  | nudge_5 at 12.5–22 m/s | 8.0° | 0.8° |

- **What it cannot do:** no cal cell references the bound to sign(E′). Every threshold that clears the twist (p90
  607–681, p99 1103–1206 below 8 m/s) also stops catching the 300–600-word light hands that O1 (614) does not catch.
- **(a2) G0-1400** is GATE-2 clean (worst +2.4°, the same point as V298). Its time effect is mixed.
  - Better: ±1° 0.2 Hz tracking at 3.1 m/s rises from 0.18 to 0.50.
  - Worse at 3.1 m/s: hard turn-in overshoot 3.2° vs 1.0°, step overshoot 19.7 % vs 15.9 %, ov_lt511 lurch 9.5° vs 7.7°.
  - **It is offered as a separate dose, not carried in D1c**, so that one drive can interpret one edit.

### 2.2 (b) D1c: the cave edit

**Base and size**
- Base: V298 (`177abf04…`). Cave at `0xC4C00`.
- Flight cave 252 B, sha256 `80dd2052edc08cd3948a8d065e16af7c234ab4f0dec69961b4cb3ed92863950b`.
- Score cave (cmovh op-validity, for H1) 250 B, sha256 `a35e4fa5…7e65257f`.
- The trailing 8 bytes `0xC4CFC..0xC4D03` return to `0xFF` (the free region's erased value).
- **152 of the 260 cave-region bytes differ from V298.** The relink moves the tail. The first difference is the table
  pointer at `0xC4C1E`: `0xC4CDA` → `0xC4CD2`.
- Everything outside the cave is V298 (E1 E2 B2 A2 E4 HOOK OPH V1, the cal cells, the Kp/Kd/fade records).
- Main-block CRC `[0x13000, 0xC4FFC)` must be recomputed (builder).

**Changed code in the flight listing** (`out/d1_cave.txt` prints all 85 lines; each new instruction's term is named).

| addr | bytes | instruction | term |
|---|---|---|---|
| `0xC4C1C` | `29 06 d2 4c 0c 00` | mov 0xC4CD2,r9 | table pointer (relinked; V298 `…da 4c…`) |
| `0xC4C5E` | `e4 47 99 b0` | ld.hu -0x4f68[gp],r8 | \|hand word\| (unchanged) |
| `0xC4C62` | `20 6e cd 04` | movea 1229,r0,r13 | **[1] hard THR = Honda pressed level** |
| `0xC4C66` | `ed 41` | cmp r13,r8 | |
| `0xC4C68` | `9b 2d` | bh FRZ (→ `0xC4CBA`) | freeze iff \|tq\| > 1229 |
| — | — | *(V298's 16-byte opposing block `0xC4C6A..0xC4C79` is absent)* | **[2] removed** |
| `0xC4C6A` | `24 4f 00 96` | ld.h -0x6a00[gp],r9 | θ (0.1° counts) |
| `0xC4C6E` | `09 68` | mov r9,r13 | **[3] r13 = θ** |
| `0xC4C70` | `30 69` | xor r16,r13 | **[3] θ ^ E′** |
| `0xC4C72` | `ae 05` | bge AS (→ `0xC4C76`) | **[3] same sign: the I winds outward; use the θ-referenced bound** |
| `0xC4C74` | `00 4a` | mov 0,r9 | **[3] toward centre: \|θ\| term := 0, so bound = B** |
| `0xC4C76` | `e0 49` | AS: cmp r0,r9 | (V298's A3 block from here on, shifted −8 B) |

- **Unchanged order.** The rest is V298's order: the |θ| shift by 4 or 6 at VTH 2880, `addi 1250`, the cap 4096 at
  VCAP 1382, `ld.w gp-0x6dd0 ; sar 10`, the sign of E′, `bge FRZ`, the ramp test, `FRZ: mov 0,r6 ; jr 0x29D7E`, the
  CAM handler, `DONE: jmp [r6]`, and the GB-P table at `0xC4CD2`.
- **Re-encoded targets:** `bh FRZ`, `bge FRZ`, `bne DONE`, `be CAM`, the two `jr 0x29D7E`, and the op-skip
  `jr 0x2A164` are all re-encoded by the same two-pass linker `build_v298_tva.reassemble_caves` uses.
- **Full hex:** `out/d1c_flight.hex`.

**Verification done here (EVIDENCE)**

- **C1:** the same pipeline (`e2_asm.listing` + the op-skip injection + the two-pass relink), given V298's policy,
  re-derives `build_v298_tva.FLIGHT` and `SCORE` byte for byte (sha `ef1861e10421`).
- **H1:** `score_time.h1`'s V850E2 interpreter executed the D1c score-cave **bytes** against D1's mirror
  (`d1_time.D1Lane.cave_stage`), with random and edge cases. A case passes only if every check holds:
  - E′, the exit address, r6 and r26 match;
  - gp-0x6dd0 matches;
  - preserved registers are unchanged;
  - every read-only cell is unchanged.

  | run | result |
  |---|---|
  | D1c | **0 / 8000** |
  | control: V298's bytes vs the V298-switch mirror | 0 / 3000 |
  | negative control: no asymmetric bound | 29 / 1500 fail |
  | negative control: THR 512 | 159 / 1500 fail |

  So the asymmetric bound and the threshold are both really in the bytes.
- **Instruction forms:** all are forms V298 already executes, re-decoded by Ghidra (dry run, V298 program):
  - `xor r16,r9` (`30 49`) at `0xC4C76`;
  - `bge` (`ae 05`) at `0xC4C80`;
  - `movea 0x200,r0,r13` (`20 6e 00 02`);
  - `mov r26,r8` (`1a 40`) at `0x29EE0`;
  - `mov 0,r6` (`00 32`, the FRZ head).

  D1c changes only the register fields of these forms. The builder's H5 still decodes the BUILT image.

**Integer-exact mirror** (`d1c_mirror.py`; 0 / 20000 mismatches vs `D1Lane.cave_stage`, both freeze and normal exits
exercised). This is the core of what the golden model would carry.

```python
def d1c_cave(sp, r26, r14_ramp, r25, g6abe, g6a5e, g4f68, g6a00, g6dd0, flight=True, rows=GBP, THR=1229):
    r16 = s32(s32(sp << 2) - r26)                       # 0xC4C00 shl 2 ; 0xC4C02 sub r26,r16    E = 16(th_sp - th)
    r26 = s16(g6abe)                                    # 0xC4C04 ld.h -0x6abe   D operand (fresh motor rate)
    if ((r26 + 13000) & 0xFFFFFFFF) > 26000:            # 0xC4C08..0xC4C12 validity
        if flight: return ('SKIP', 0x2A164)             # 0xC4C14 jr 0x2A164 (Honda epilogue: I8:=0, sentinel)
        r26 = 0
    G = walk(rows, g6a5e & 0xFFFF)                      # 0xC4C18..0xC4C52 the GB-P walk (unchanged)
    r16 = s32(r16 * G) >> 8                             # 0xC4C54 mul ; 0xC4C58 sar 8          E' = (E G) >> 8
    if r25 == 0: return ('FRZ', E'=0, r6=-(I8 >> 6), op=0)   # 0xC4C5A/5C camera gate -> CAM (unchanged)
    if (g4f68 & 0xFFFF) > THR: return ('FRZ', r6=0)     # 0xC4C5E..0xC4C68 [1] hard freeze at 1229
    r9 = s16(g6a00)                                     # 0xC4C6A theta
    if s32(r9 ^ r16) < 0: r9 = 0                        # 0xC4C6E..0xC4C74 [3] toward centre -> bound = B
    r9 = abs(r9)                                        # 0xC4C76..0xC4C7A
    v = g6a5e & 0xFFFF
    r9 = s32(r9 << (6 if v > 2880 else 4)) + 1250       # 0xC4C7C..0xC4C8E slope, + B
    if v <= 1382 and (r9 & 0xFFFFFFFF) > 4096: r9 = 4096    # 0xC4C92..0xC4CA0 low-speed cap (unchanged)
    t = s32(g6dd0) >> 10                                # 0xC4CA4/A8 I >> 7
    if r16 < 0: t = -t                                  # 0xC4CAA..AE  t = sgn(E') I
    if t >= r9: return ('FRZ', r6=0)                    # 0xC4CB0/B2 winding past the bound
    if (r14_ramp & 0x8000) == 0: return ('FRZ', r6=0)   # 0xC4CB4/B8 ramp-in freeze (unchanged)
    return ('DONE', 0x29D7A)                            # 0xC4CD0 jmp [r6] -> Honda's I: inc = ((E'>>5)*40)>>3
```

**The loop it implements** (downstream unchanged from V298 design §1.4):

```
I8 += ((E′>>5)·40)>>3   only when not frozen
bound = B                       if sign(θ) ≠ sign(E′)
bound = (|θ|<<4|6) + B          otherwise (capped at 4096 when v ≤ 6 m/s)
frozen  ⇔  |hand| > 1229  ∨  sgn(E′)·(I8>>10) ≥ bound  ∨  ramp < 0x8000
```

**GATE 1 (RAM ownership).**
- The cave writes **no RAM** (EVIDENCE: no `st.*` in the listing; H1 checks every read cell unchanged).
- It reads gp-0x6abe, -0x6a5e, -0x4f68, -0x6a00, -0x6dd0 and r25. All are read by V298 already.
- It no longer reads gp-0x4f60 (the signed hand word).
- No new state word exists, so no engage/disengage/bail initialisation is needed. gp-0x6dd0 stays Honda's, zeroed by
  the `0x2A164` epilogue on every skip.

**The wire instrument for the edit** (no new state word, so no new bit; prefer the inert test):

1. **Rule-identity replay (zero bytes).** Run `d1_r79`'s replay with the V298 rule and with the D1c rule on the new
   drive. The rule that ran must win R² against the 0x1AB tap.
   - Power, on r79 where V298 is true: V298 beats D1c in **18 / 18** 30-s settled windows (dR² p50 +0.605, p10 +0.229),
     and in 10 / 10 windows with ≥ 2 s of hands-off manoeuvre (EVIDENCE `d1_r79` D).
   - The next drive runs the same test reversed.
2. **The refuters' near-crossing split** (`refute_inference.py` D4/D6), re-run on the new route with V282/V294 as
   controls. The prediction is that the excess near |bar| 300/512 crossings disappears.
3. **The bar itself** (§2.3) shows the tap live, so the operator can see the delivered lane torque.

A direct freeze bit on 0x14A b4.3 is possible. It would need the 0x14A telemetry cave edited, a second cave, so it is not
proposed.

### 2.3 Fork change (with either implementation): the torque bar

| file / function | the diff in words | toggle config? | param |
|---|---|---|---|
| `opendbc_repo/opendbc/car/honda/carstate.py` · `CarState.get_can_parsers` and `update` | When the EPS is the angle-loop firmware, parse 427 `STEER_MOTOR_TORQUE` on the pt bus. Use the same predicate the fork already uses for the 0xE4 angle interface (fw A16A / `AccordEpsAngleLoop`). Add it as `("STEER_MOTOR_TORQUE", float("nan"))` so it carries no frequency gate. Decode `raw = MOTOR_TORQUE` (10 bits, DBC `1\|10@0+`, present in `honda_civic_hatchback_ex_2017_can_generated`, the Accord's pt DBC) as `tap_T = (-1 if raw & 0x200 else 1) * (raw & 0x1FF) * 8`, and set `ret.steeringTorqueEps = tap_T`. | no (code) | gate on the existing `AccordEpsAngleLoop` |
| `selfdrive/ui/onroad/starpilot/torque_bar.py` · `TorqueBar._update_state` (angle branch) | On the angle-loop Accord, replace `(a_lat + accel_diff)/CP.maxLateralAccel` with `clip(carState.steeringTorqueEps / 2461, -1, 1)`. 2461 T = the lane rail (SCL 15360 × 5346/32768 ≈ 307.6 LSB × 8). Keep the 0.1 s filter. The old formula stays for every other car. | no (code) | same |

**EVIDENCE**
- `d1_427_check.py` decoded all 21 r79 segments. On bus 1 there are 61113 0x1AB frames at 49.9 Hz.
  - Honda nibble checksum valid on **100 %**.
  - COUNTER step 1 on 99.997 % (2 skips).
  - CONFIG_VALID 100 %.

  So the V298 cave keeps 0x1AB a valid frame (closes C12's open item). Parsing it cannot break `canValid` through its
  checksum.
- The kit's T decode has the same sign as the current bar (M5: 14 / 14 sign agreement, r +0.72).

**BELIEF**
- The opendbc `float("nan")` no-timeout convention on this fork's CANParser. The fork-side reviewer must confirm it.
- **The bar shows the lane's torque only,** not Honda's base assist. That is the automation's effort, the thing note 3
  asks about.

---

## 3. GATE 2 and the time criteria (kit scorers, run here)

### 3.1 GATE 2

**Model.** The C3-r1 stability refuter's independent model (`refute_stability/c3r1/c3r1_model.py`, unchanged).
- Bars: tier A 45° (aged 30°), tier B 30°, GM ≥ 6 dB, 5–30 Hz |T| ≤ +3 dB.
- Exact periodic ρ is computed wherever PM < 32°.
- D1c changes no linear cell (Kp 112, Ki 40, Kd 48, GB-P, the operands). **Its PID and I-frozen PD loops are V298's**
  (EVIDENCE by construction plus H1).
- The integral policy only switches between those two loops. **BELIEF:** switching between two stable loops at the
  bound does not destabilise; the sim shows no hunting (`d1_time`).

**Summary table** (EVIDENCE, `d1_gate2` + `d1_gate2_report`, physical envelope θ ≤ θ(v, 3 m/s²)):

| set | loop | n (credible) | PM < bar | GM < 6 | pk > 3 dB | ρ ≥ 1 | worst PM − bar |
|---|---|---|---|---|---|---|---|
| D1c = V298, θ = 0, 1–35 m/s, frames nom/FA.83/FA1.155/FB.83/FB1.155, e −1/0/5/10 | PID | 4160 | **0** | 0 | 0 | 0 | +9.8 (b_q×J1.0, 30 m/s, e10) |
| same | PD | 4160 | **0** | 0 | 0 | 0 | +17.1 |
| D1c = V298, low-speed op-points 110–360° (k·sech²(θ/sat)), 2–10 m/s | PID | 4560 | **0** | 0 | 0 | 0 | **+2.4** (b_lo×J_hi, 8 m/s, 110°, e10) |
| same | PD | 4560 | 0 | 0 | 0 | 0 | +11.7 |
| D1c = V298, curve-hold a 1.0–2.5, 15–30 m/s | PID | 7200 | 0 | 0 | 0 | 0 | +5.6 |
| (a2) G0-1400 | PID | 4800 | 0 | 0 | 0 | 0 | +2.4 (per-speed +3…+5 at 2–7 m/s; V298 +5…+9) |
| rejected: G0-1600 / Kp168 / Kp224 / Kd36 / Kd24 / Ghi1.25 | PID | — | 7 / 122 / 940 / 44 / 579 / 30 | | | 0 | −1.2 / −9.9 / −20.3 / −6.3 / −15.4 / −6.4 |

The J≈2 ms_free products are reported apart, as V298's design declared them. V298 = D1c there: θ=0 0 fails; curve-hold
25 PM fails, ρ < 1.

**Per operating point** (EVIDENCE, `d1_gate2_table`: nominal member, frame nom, e 0; worst credible member in brackets).

| v (m/s) | θop | PID PM / GMup / Ms / fc (Hz) | PD PM / GMup / Ms |
|---|---|---|---|
| 3.1 | 0 | 83.7 / 23.2 / 1.24 / 1.81 (J_hi 66.5) | 88.1 / 23.2 / 1.24 (b_lo 70.4) |
| 3.1 | 360° | 78.6 / 23.2 / 1.24 / 1.72 (J_hi 58.6) | 84.9 / 23.2 / 1.24 |
| 5.0 | 208° | 76.4 / 23.2 / 1.24 / 1.81 (J_hi 57.2) | 82.6 / 23.0 / 1.25 |
| 8.0 | 81° | 74.6 / 23.1 / 1.25 / 1.95 (J_hi 56.2) | 80.3 / 22.9 / 1.26 |
| 11.75 | 38° | 68.7 / 27.7 / 1.10 / 0.44 (ms_free **36.3**, the declared V298 residual) | 122.3 / 27.7 / 1.10 |
| 17.5 | 17° | 81.4 / 33.2 / 1.04 / 0.37 (b_q×ms_free 41.5) | 159.9 / 33.2 / 1.04 |
| 26.9 | 7° | 76.8 / 34.9 / 1.04 / 0.60 (b_q×J1.0 48.1) | 120.3 / 34.9 / 1.04 |

**Other loops are unchanged:** the outer fork loop (τ_o), the hands-on fade floors and the rate-invalid op-skip are all
V298's.

### 3.2 Time criteria

**Scorers.** `panel2/score_time.py` imported unchanged, extended by `D1Lane`.
- **Control:** `D1Lane` with V298's switches equals `CandLane` bit for bit (`python d1_time.py control`; |dθ| 0,
  |dT| 0).
- **Speeds:** 3.1 / 5 / 8 / 11.9 / 17 / 26.9 m/s.
- **Members:** nominal, bc, F_hi, b_lo×J_hi. Each cell below is the worst over the members.
- **Twist scenarios** (`hardT`, `stT`, `thT`) add the r79 reaction model to the torque word: −0.69·α − 0.69·ω −
  163·tanh(ω/2) − 0.13·θ − 61, plus AR(1) noise of std 206 words and lag-1 autocorrelation 0.89 at 100 Hz. This is
  BELIEF: a fitted model with R² 0.31.
- **N1 lens:** `refute_c3_nonlinear` via `rb_n1.Lane2`, extended to `Lane3`. Control: `Lane3(V298)` = `Lane2('theta', 40,
  300)` bit for bit.

**Results** (cells V298 → D1c; 3.1 / 5 / 8 / 11.9 / 17 / 26.9 m/s unless a band is named):

| scenario · metric | V298 | **D1c** | reading |
|---|---|---|---|
| hardT · hand-freeze toggles /s | 9.3 / 10.3 / 12.8 / 10.8 / 9.3 / 11.6 | **1.3 / 0.3 / 0 / 0 / 0 / 0** | the twist chatter is gone |
| hardT · hand-freeze duty | 0.22 / 0.25 / 0.23 / 0.20 / 0.15 / 0.20 | 0.03 / 0.01 / 0 / 0 / 0 / 0 | |
| hardT · hard_ratio (1.6–3 Hz follow) | 0.60 / 0.64 / 0.73 / 0.35 / 0.29 / 0.45 | **0.78 / 0.90 / 1.00** / 0.34 / 0.31 / 0.48 | turn-in authority restored to the design |
| hardT · overshoot ° | 0.61 / 0.28 / 0.02 / 0.48 | 0.71 / **2.19 / 3.10** / 0.81 | the design's own no-twist value (1.0 / 2.2 / 2.7) returns |
| hardT · 4–8 Hz wheel-rate rms | 2.11 / 1.97 / 1.48 | **3.33** / 2.07 / 1.34 | 3.1 m/s worse ×1.6 (stronger edges, BELIEF); stop band F6 |
| stT · overshoot % | 2.5 / 1.1 / 0.0 | 13.3 / 17.2 / 14.7 | = the design's no-twist step value (15.9 / 17.8 / 15.2). The fork's 120 deg/s limiter means no steps reach the car. |
| thT · A3-stop toggles /s (≤ 5 m/s) | 9.4 / 7.6 | **0.25 / 0.25** | the bound does not take over the chatter in closed loop |
| thT · 4–8 Hz rms | 0.57 / 0.33 / 0.59 / 0.16 / 0.25 | 0.41 / 0.26 / 0.62 / 0.11 / 0.07 | lower in 4 of 5 bands |
| thT · overshoot ° at 11.9 | 5.03 | 7.25 | = the no-twist design value 7.20 |
| st / hard / th / s10_02 / db (no twist) | — | **identical to V298** within 0.15 | as expected: the policy acts only on hands, the bound and twists |
| ov_lt511 · release lurch ° | 7.45 / 5.55 / 3.87 / 1.48 / 0.25 / 0.21 | 7.72 / 5.69 / 3.87 / 1.76 / 0.33 / **0.86** | +0.1–0.65° |
| ov_lt1000 · release lurch ° | 7.06 / 4.60 / 3.26 / 1.37 / 0.20 / 0.17 | 7.72 / **5.68** / 3.84 / 1.74 / 0.32 / 0.81 | +0.4–1.1° (512–1229 words no longer freeze) |
| cs (light co-steer 400 helping, 2 s) · droop ° | 0.54 / 0.69 / 0.88 / 0.14 / 0.13 / 0.09 | **3.01 / 2.68 / 2.28 / 1.46** / 0.85 / 0.26 | **declared cost** (§7 M-D1-2) |
| cs · lurch ° | 1.20 / 1.56 / 2.01 / 1.78 | 0.43 / 0.44 / 0.04 / 0.45 | better |
| eng, tmo, sen, dis (run 1) | — | identical to V298 | fail-safe paths untouched |

**N1 lens** (deg past the setpoint after release, worst member, bands 8–12.5 / 12.5–22 m/s):

| scenario | V298 | **D1c** | D1a (= (a)) | D1b (gated) |
|---|---|---|---|---|
| out_2_400_1 | 14.32 / 4.71 | 14.18 / 5.05 | 20.08 / 6.25 | 14.32 / 4.71 |
| out_2_511_3 | 14.35 / 4.71 | 14.18 / 5.05 | 20.08 / **15.90** | 14.35 / 4.71 |
| out_2_1000_3 | 14.42 / 4.72 | 14.23 / 5.04 | 19.98 / **15.98** | 14.42 / 4.72 |
| out_1.5_511_3 | 7.17 / 2.36 | **8.75** / 4.99 | 16.04 / 7.99 | 7.17 / 2.36 |
| part_0.5_511_3 | 7.17 / 2.36 | 7.13 / 3.15 | 7.13 / 3.15 | 7.17 / 2.36 |
| nudge_5_511_3 | 1.99 / 0.80 | 3.64 / 2.35 | 5.80 / **8.02** | 2.07 / 0.84 |
| rev_1.5 / rev_2 (N5 ovs2) | 0.12 / 0.15 | identical | identical | identical |

- **< 8 m/s band:** identical across all variants, V298 included (42° / 21°, spread ≤ 0.3°). The lens's low-speed Ah is
  45–90°, so it does not discriminate there.
- **Peak hand force needed** during the hold, out_1.5 at 8–12.5: V298 816 → D1c 1136 (+39 %), because the I swings to −B
  against the hand.

### 3.3 The A3 cap (4096 → 8192): rejected (EVIDENCE, `out/d1_time_run1_capC8k.txt`, D1c vs D1c-c8k)

| metric (3.1 / 5 m/s) | D1c | D1c-c8k |
|---|---|---|
| hard turn-in overshoot | 1.04 / 2.17° | **11.79 / 7.32°** |
| turn-hold overshoot | 0.64 / 0.54° | 5.88 / 2.17° |
| step overshoot | 15.9 % | 19.9 % |
| ov_lt lurch | 7.7° | 9.9° |

**The low-speed cap is still necessary.** It keeps the I's windup from overshooting low-speed turn-ins.

---

## 4. Route-79 counterfactuals (EVIDENCE for the rule arithmetic on the recorded wire; open-loop BELIEF for torque)

| quantity | V298 (validated replay, R² 0.928) | D1c | method |
|---|---|---|---|
| fork O1 episodes | 415 (345 twist-like, ≤ 50 ms) | **415, unchanged** | D1 does not touch the fork's O1 |
| firmware hand-freeze duty / discarded integration / toggles (hands-off) | 11.4 % / 28.3 % / 325 per min | 0.4 % / 0.8 % / 13 per min | `d1_r79` A |
| same below 5 m/s · 5–8 m/s | 26.2 / 37.7 / 409 · 26.2 / 41.5 / 555 | 0.7 / 0.7 / 19 · 1.2 / 2.0 / 46 | A |
| real-hand frames frozen | 99.7 % | 97.3 % | A |
| stall-surges within ±0.25 s of a toggle (0–5 · 5–10 m/s) | 22/27 · 56/68 | 9/27 · 26/68 | B (M4 detector, unmodified) |
| replay tap in hands-off manoeuvres p50 / p99 / max (LSB) | 46 / 149 / 199 | 57 / **194** / 245 | C (open loop on V298's errors: an upper bound) |
| I at the A3 bound in manoeuvres / A3-stop toggles | 4.2 % / 20 per min | 19.8 % / 141 per min | C (open loop overstates it; closed loop thT gives 0.25 /s vs V298's hand toggles 7–9 /s) |
| identity test power | — | V298 wins 18/18 windows, dR² +0.605 | D |

**What D1 does not move.** The stiffness, the gains and the G rows are unchanged, so the tap on the recorded errors does
not change through P. Every authority gain above comes from the integration kept.

---

## 5. Hazards and fail-safe paths

| path | D1c behaviour | evidence |
|---|---|---|
| engage (ramp 0→0x8000, dir-2 328/tick) | ramp < 0x8000 still freezes the I; gp-0x6dd0 starts at 0 (zeroed by the `0x2A164` epilogue while not running) | listing unchanged at `0xC4CB4`; `eng` identical |
| request drop | A2/B2 → Honda epilogue (I8 := 0, sentinel); ramp-out 66/tick; the cave is not entered | unchanged in-place set |
| 0xE4 timeout / sentinel (0x7FFF) | as V298. E′ is huge and P rails until the request falls. The I can wind only within A3, and **less** than V298 when θ opposes E′ (bound B) | `sen`, `tmo`, `dis` identical (run 1) |
| invalid fresh rate | op-skip `jr 0x2A164` (unchanged bytes and target, relinked displacement) | C1 + linker |
| stock camera frame (arm ≠ 2) | CAM gate before the hand test, unchanged: E′, op := 0; I decays ×0.125/tick | listing `0xC4C5A` |
| **real hand ≥ 1229 words** (Honda pressed) | I frozen, as V298 above 1229; fade ×0.85 at 1216 to ×0.30 at ≥ 2048 (unchanged fadeB) | `d1_r79` A: 97.3 % of pressed ticks frozen |
| **light hand 300–1229** | **no freeze** (V298 froze at 300 opposing / 512 any). The I winds only within the bound: outward ≤ 16\|θ\|+B (≤ 12.5 m/s) or 64\|θ\|+B, capped 4096 at ≤ 6 m/s; toward centre ≤ B ≈ 200 T. Above 614 words the fork's O1 sets the setpoint to the wheel, so E′ ≈ 0 and nothing winds. | `d1_n1`, `d1_time` ov/cs |
| driver override | Always possible. The lane's extra resistance to a light outward hand is bounded by B (+39 % peak hand force in out_1.5 at 8–12.5 m/s). At the stock pressed level the I freezes and the fade starts. | `d1_n1` hf column |
| pol (gp-0x6752 = −1, run-time re-asserted) | D1c adds **no** pol dependence. θ and E′ are both in the gp-0x6a00/E frame; the asymmetric test uses only them. | trace 2026-10-02 §0.3 |
| version string | **open decision.** Keep `A16A` so the fork's angle-interface interlock needs no change, and attribute by the replay identity test (F1). Or bump to `A16B` and add it to the fork's accepted list (one line). | §8 |

---

## 6. Pre-registered FAIL criteria for one short drive

**Exposure.** About 30 s of engaged driving below 10 m/s. It must include one hands-off turn-in and a hands-off return,
and should include one light-hand co-steer released hands-off. Do not fly again if any of these holds:

| # | criterion (wire/rlog, computable in the existing caches) | what a fire means |
|---|---|---|
| F1 | **Rule identity fails:** the D1c-rule replay does not beat the V298-rule replay on R² vs the 0x1AB tap in the pooled drive (dR² < +0.05), or in fewer than 2 of the 30-s windows with ≥ 2 s of hands-off manoeuvre | not live, or mis-built; interpret nothing else |
| F2 | ring presence > 0.5 %, F7 > 0 /100 s, or any new 5–30 Hz line (instrument R4) | revert |
| F3 | after a steeringPressed release at ≥ 8 m/s, \|θ − θsp\| > 8° within 1.5 s, or the wheel crossing the setpoint by > 5° on a straight | the N1 class has returned; revert |
| F4 | a hands-off turn-in at ≤ 10 m/s overshoots θsp by > 6° (sim worst 3.1°) | windup worse than modelled; revert |
| F5 | a light-hand episode (300 < \|word\| < 1229, ≥ 1 s, not pressed) ends with the wheel falling > 4° behind θsp toward centre (sim worst 3.0°) | the cs cost is larger than modelled; revert |
| F6 | ratchet trains ≥ 4.7 per minute of turning at 5–10 m/s (r79), **or** the stall-surge rate within ±0.25 s of \|bar\| 300/512 crossings still ≥ 2× the free rate at 5–10 m/s | the freeze was not the ratchet's mechanism. Stop iterating on the integral policy. |
| F7 | steeringPressed set while the tap stays ≥ 50 % of the rail opposing the driver's torque for > 0.5 s | override impaired; revert |
| F8 | any canValid/CAN-error event attributable to the 427 parse, or the bar's sign disagreeing with the tap's | revert the fork bar change only |
| R9 | the operator reports grinding, ratcheting or anything new | his call; it outranks every band |

---

## 7. Declared misses (each quantified, each with a covering stop band)

| id | miss | size | covered by |
|---|---|---|---|
| M-D1-1 | **The fork's O1 relay, re-slew and 120 deg/s cap** are untouched: 345 twist O1 trips, 73 % of cap-binding in the post-release re-slew. The hand-on yield in AOL turns (63.8 % of hard time) is unchanged. | all of note-2 #1 / #2 (refuters) | outside D1. Graft from the fork-side angle. |
| M-D1-2 | **Light co-steer release droop:** a helping hand of 300–614 words held ≥ 1 s, then released, leaves the wheel up to **3.0° behind** θsp at ≤ 8 m/s (V298 0.5–0.9°). It recovers in ≈ 0.4 s (Ki 2.8/s). | sim worst 3.0° / 2.7° / 2.3° / 1.5° at 3.1 / 5 / 8 / 11.9 m/s | F5 |
| M-D1-3 | **N1 nudge and outward-1.5×:** nudge 3.6° (V298 2.0°); out_1.5 at 8–12.5 m/s 8.75° (V298 7.17°; V298's own out_2 there is 14.3°) | +1.6° | F3 |
| M-D1-4 | **The designed overshoot returns:** hard turn-in 2.2–3.1° at 5–8 m/s; turn-hold 7.2° at 11.9 m/s (a 2.5). V298's twist freezes had suppressed these by accident. | = the C3-rev2 design values | F4 |
| M-D1-5 | **4–8 Hz wheel rate in a 3.1 m/s hard turn:** ×1.6 in the sim (stronger edges, BELIEF) | 3.33 vs 2.11 deg/s | F6 / R9 |
| M-D1-6 | **The low-speed authority ceiling stays:** steady P+I ≤ ≈ 62–65 % of the rail below 6 m/s. Raising the A3 cap overshoots (§3.3); Kp / G0 > +19 % fails GATE 2. | C4 unchanged | — |
| M-D1-7 | **The small-correction stick** (dwells 4.7 / 1.2 / 4.5 / 3.5 per min) is barely touched: db stuck % within ±4 points. Stiffness cannot rise (Ghi1.25 fails GATE 2). | C10 row 1 unchanged | needs setpoint-rate feed-forward (§8) |
| M-D1-8 | **D braking in hands-off unwinds** (D outweighs P at 100–120 deg/s). Lowering Kd at big angles fails GATE 2. | refuter §2c unchanged | — |
| M-D1-9 | **The 1.6–3 Hz hard-turn criterion** (FAIL 8.48 vs V282 ≈ 4) gets **worse**: D1c follows the setpoint's 1.6–3 Hz content (hard_ratio → 0.9–1.0) | sim | the criterion conflicts with tracking; the operator's ruling is needed |
| M-D1-10 | **The I-bound becomes the main windup limiter.** In open loop it stops 20 % of manoeuvre frames (V298 4 %). Closed loop shows no chatter (A3 toggles 0.25 /s). | replay vs sim disagree | F6 / R9 |

---

## 8. What I would graft from the other angles, and open decisions

**Grafts**
- **Fork O1.** Raise O1 to the stock pressed level (1200 raw), or debounce it ≥ 60 ms. Stop resetting `apply_angle_last`
  to the wheel on release. These remove the relay that D1 cannot touch, and pair naturally with D1c's 1229 freeze, so the
  firmware and the fork would agree on what a hand is.
- **Fork setpoint lead.** Send θsp + τ·θ̇sp (τ ≈ the measured 0.15–0.25 s actuator lag) from the plan's rate. This
  addresses the stick, the 260–440 ms lag and the unwind D braking without a GATE-2-limited gain.
- **Firmware, next class.** A filtered setpoint-rate feed-forward in the lane needs one state word, so GATE 1 plus a wire
  probe first. A debounced opposing freeze needs one RAM word, and only if M-D1-2 is ruled unacceptable.
- **Low-speed stiffness.** A fresh 1 kHz angle operand (gp-0x69ca, the H-A class) is the only route past the
  phase-limited Kp at low speed.

**Open decisions for the orchestrator**
1. Keep version `A16A` (no fork interlock change; attribution by F1) or bump to `A16B`.
2. Whether M-D1-2 (co-steer droop ≤ 3°) is acceptable for the ratchet fix.
3. Whether (a2) G0-1400 rides as a separate later dose.
4. Whether the 1.6–3 Hz criterion (M-D1-9) stands against tracking.

**How this differs from the arc.** V298 added the opposing-hand freeze (2026-10-01) for N1. Route 79 then measured that
freeze as the ratchet's mechanism. D1c keeps V298's loop and every gain, and replaces a hand-**word** test with a
**sign-of-angle** test on the integral bound. It is a new mechanism for the same N1 hazard, not a re-run of a dose.
Frozen since V298 (1 build): every gain, the table and the cap. Changed: 3 instructions' worth of integral policy. No new
RAM. The cave is 8 B smaller.
