# DESIGN V299 — SYNTHESIS (2026-10-02): the in-place integral-policy fix under a relay-free, param-gated fork

**Status: DESIGN. Nothing built, flashed, sent or committed; fork, firmware, golden model, STATE, lineage and git untouched.**
Author: the DESIGN-SYNTHESIS subagent. Ghidra read-only (`disassemble_bytes dry_run` on `ADVIG_V298_177abf04.bin`). Python =
`bin_decompile`. **EVIDENCE** = image bytes, route-79 caches, fork source at Dom `2712e1336`, or a script I ran this session (named,
wall time given); **BELIEF** = a model (the r71b plant family, M3's reaction-twist fit R² 0.31) or an inference. Bands are scored
here; the operator scores symptoms. Classifier interruptions: 0.

Inputs read in full: D1–D5 design pages, S1/S2/S3 scorer reports, the three judge reports, the drive read §5, both refutations.
Nothing upstream was binding; every decision-bearing number below was re-derived or re-run by me (§A).

---

## 0. The answer in one page

**V299 firmware = V298 + 26 bytes: D1c's three integral-policy edits applied IN PLACE inside V298's cave (21 B), F181 `A16B` (1 B),
main-block CRC (4 B).** Cave stays 260 B at 0xC4C00, no relink, 0 RAM written, 0 new state words, every gain/table/clamp/op-skip/
camera gate byte-identical to V298, so the linear loop and GATE 2 are V298's. The three edits:

| # | edit | bytes | loop term it changes | measured mechanism it moves |
|---|---|---|---|---|
| 1 | hard-hand integrator freeze `movea 512` → `movea 1229` (= 1200 raw × 1.024, Honda's steeringPressed level) | 2 | I frozen only under a Honda-recognised hand | the freeze firing on the wheel's own reaction twist (p90 607–681 < 8 m/s) |
| 2 | the opposing-hand clause (`movea 300 ; cmp ; bnh ; ld.h -0x4f60 ; xor ; blt FRZ`) removed | −16 (nop-filled) | no freeze keyed on the signed word | the 300-crossing relay: stall-surges 80.7 vs 30.3 /min near vs away (5–10 m/s), none on V282/V294 |
| 3 | asymmetric A3 bound: `mov r9,r13 ; xor r16,r13 ; bge +4 ; mov 0,r9` after `ld.h -0x6a00[gp],r9` | +8 | when sign(θ) ≠ sign(E′) the I may wind toward centre only to B = 1250 S (≈ 200 T) | replaces clause 2's N1 job (a light outward hand no longer lets the I swing to −(16\|θ\|+B)); unwind overshoot 4.2° → 0.6° |

**Fork update (Dom, one commit; every term a param defaulting to V298, so with defaults the commit replays r79's 0xE4 byte-identically):**
O1 gate G4 (> 1200 raw instant; 600–1200 held 80 ms; off ≤ 500), O1 lead 0.06 → 0, a 0.4 s takeover ramp on rate AND clip after
engage/release, rate cap 120 → 250 deg/s, error clip ×1.6 at the ≤ 11.75 m/s knots, the torque bar = the EPS's own 0x1AB lane
torque / 2461 (today's drawing direction), a status bit-field in the free `carOutput.actuatorsOutput.torque`, F181 tuple {A16A, A16B}.
**Two Galaxy toggle configs on one firmware:** `V299-A` = relays + bar (cap/clip at V298 values) and `V299-B` = A + cap 250 + clip ×1.6.
A reads note 4 and N1; B reads note 2. Each is attributable by its own instrument (§6), so one short drive interprets both.

**Predicted, per operator note** (EVIDENCE = r79 replay on the recorded wire or an S2 cell I ran; BELIEF = closed-loop truth):

| note | r79 measured | V299 predicted | basis |
|---|---|---|---|
| 1 small-angle robust at all speeds | GATE 2 R2 box 0 fails, worst PM 39.1°; C2 2° slow-drift e_rms 0.99/0.60° at 15/25 m/s | **unchanged by construction** (loop bytes identical; S1 = V298); C2 0.95/0.53°, fast g@0.5 s 0.33/0.75 (0.29/0.69) | S1 finding 1; S2 row (§3.2) |
| 2 "not 6×" in hard manoeuvres | hands-off wheel p99 140 deg/s, tap peak 183 LSB (59 % of rail); cap bound 50 % of hands-off hard frames; 345 twist O1 trips, 415 releases; I keeps 0.52–0.57 | **B:** 60° hands-off turn-in: wheel peak **172 / 158 deg/s** at 3 / 8 m/s (V298 97 / 90), t90 **0.78–1.25 / 0.85 s** (1.77 / 1.80), tap peak 51 / 68 % [71] of rail; P-cap 36/40/26/17 → **61/63/43/25 %**; r79 twist O1 trips **345 → 30**, releases 415 → 79; I kept 0.95 at 8 m/s. **Hand-steered turns still yield by design** (unchanged). The 3 m/s t90 is bimodal on the twist seed (X3, §7) | S2 row + cap sweep (BELIEF); D2 counterfactual re-run (EVIDENCE) |
| 3 bar ≠ wheel | pinned 59.7 % of engaged time; \|corr\| 0.135 with the delivered torque | bar **is** the delivered lane torque: pinned **0 %**, r79 p50/p99/max 0.05/0.35/0.60; sign = today's direction (0.942 S3 / 0.854 my re-run) | `d1_427_check` + `jg_bar_sign_check` re-run (EVIDENCE) |
| 4 stuttery / ratchety | hands-off freeze toggles 325 /min, duty 11.4 %, 28.3 % of integration discarded (38–42 % < 8 m/s); stall-surges near a toggle 22/27 (0–5) · 56/68 (5–10 m/s) | toggles **13 /min**, duty **0.4 %**, discarded **0.8 %** (0.7 / 2.0 % < 8 m/s); near-toggle stall-surges **9/27 · 26/68**; pressed-hand freeze kept 97.3 %. S2: hand-freeze toggles 14.7/16.1 → **1.2/0.0 /s**, 4–8 Hz wheel rate 8.5/9.1 → **7.0/5.9 deg/s** (below V298), N1 worst lurch 13.9 → **9.1°**, unwind overshoot 4.2 → **0.6°**. Enrichment near 300/512 crossings → gone (BELIEF: the sim has no stall-surge trains). **Small-correction stick: declared miss** | `d1_r79` re-run (EVIDENCE); S2 row |

**Why this and not the others.** All three judges ranked D1c's firmware first: the only firmware that removes the measured note-4 relay
**and** holds N1 (D1a/D5b's 5-byte firmware is MEASURED at 15.9–23.7° release lurch; D4b needs +52 B and a RAM word; D3a's K2 yields
370–400 ms late at 75 % rail; D3b opens an unreplayed soft-EME band; D4a/GB-S13 fails the panel R2 box). D2a's fork is the only change that
ADDS margin to a fork loop (O1 GM 6.0 → 9.4 dB at Trt 60 ms, S1) with the best-formed override (S3). The judge's in-place construction cuts
D1c from 152 relinked to 21 in-place bytes; verified in §1.3. Grafts: D2a (fork), D1 (bar sign), D4 (LP+motion gate in RESERVE), D5
(drive-card item 1, question P4); from D3 only its finding that the rail never binds.

---

## 1. Firmware

### 1.1 Every byte (V298 image sha256 `177abf04…`; all V298 bytes re-read by me, Python LE; decodes = Ghidra's V298 listing + the forms it already executes)

| addr | V298 | V299 | decoded (V298 → V299) | loop term / why |
|---|---|---|---|---|
| 0xC4C64–65 | `00 02` | `cd 04` | imm16 of `movea …,r0,r13` @0xC4C62: 512 → 1229 | hard freeze iff \|gp-0x4f68\| > 1229 (`cmp r13,r8 ; bh FRZ` unchanged) |
| 0xC4C6A–6D | `20 6e 2c 01` | `24 4f 00 96` | `movea 0x12c,r0,r13` → `ld.h -0x6a00[gp],r9` | θ load (0.1°/count), moved up by 16 B |
| 0xC4C6E–6F | `ed 41` | `09 68` | `cmp r13,r8` → `mov r9,r13` | r13 = θ |
| 0xC4C70–71 | `d3 05` | `30 69` | `bnh 0xC4C7A` → `xor r16,r13` | sign(θ) ^ sign(E′) into the S flag |
| 0xC4C72–73 | `24 4f` | `ae 05` | first half of `ld.h -0x4f60[gp],r9` → `bge 0xC4C76` | same sign (winding away from centre): keep \|θ\| |
| 0xC4C74–75 | `a0 b0` | `00 4a` | second half → `mov 0,r9` | toward centre: θ term := 0, bound = B |
| 0xC4C76–7B, 7D | `30 49 d6 25 24 4f 00 96` | `00 00 00 00 00 00 00 00` | `xor r16,r9 ; blt FRZ ; ld.h -0x6a00` → 4 × `nop` (0xC4C7C is `00` in both) | fall-through to `cmp r0,r9` @0xC4C7E (V298's \|θ\| / shift / +B / cap / bound / ramp test, unchanged) |
| 0x1310D | `41` | `42` | F181 `39990-TVA,A16A` → `…A16B` | carFw attribution; fail-safe against an un-updated fork (S3) |
| 0xC4FFC–FF | `f3 d8 7c 6b` | `2d ad cf 2e` | main-block trailer = crc32 [0x13000, 0xC4FFC) | V298's trailer reproduces with `zlib.crc32` (my re-run); builder re-walks the chain |

Totals: **21 cave bytes + 1 + 4 = 26** (vs D1c relinked 157). Cave sha256 `0ea16bdede4e58a538e728685500b5efd43e0c592f7928fa860649e8a990c82b`
(260 B); predicted image sha256 `ac15b53359de2cffd448ba109ec19ec46e5dbd05bf8cd7c62d43d0f8d43160ec` (not written). Patch **by address**: `20 6e 00 02`
also occurs at Honda 0x6271E (my scan). Cal blocks 0xC6000/0xE5000, the rail (PCL/SCL 15360, OCL 3072, fwd 5346), Ki 40, Kp 112, Kd 48,
GB-P rows (714,1178,1041)…, the fade records: untouched (re-read).

### 1.2 The cave, integer-exact (addresses = the in-place layout; constants little-endian from the image)

```python
def v299_cave(sp, r26, ramp, r25, g6abe, g6a5e, g4f68, g6a00, g6dd0, rows=GBP, flight=True):
    r16 = s32(s32(sp << 2) - r26)                        # 0xC4C00 shl 2,r16 ; 0xC4C02 sub r26,r16   E = 16(th_sp - th)
    r26 = s16(g6abe)                                     # 0xC4C04 ld.h -0x6abe[gp],r26              fresh motor rate (D operand)
    if ((r26 + 13000) & 0xFFFFFFFF) > 26000:             # 0xC4C08 addi 13000 ; movea 26000 ; cmp ; bnh CONT
        return ('SKIP', 0x2A164)                         # 0xC4C14 jr 0x2A164  (Honda's epilogue: I8 := 0, sentinel)
    G = walk(rows, g6a5e & 0xFFFF)                       # 0xC4C18..0xC4C52 the GB-P walk on gp-0x6a5e (unchanged)
    r16 = s32(r16 * G) >> 8                              # 0xC4C54 mul r8,r16 ; 0xC4C58 sar 8        E' = (E G) >> 8
    if r25 == 0: return ('CAM', r16=0, r26=0, r6=-(g6dd0 >> 6))   # 0xC4C5A cmp r0,r25 ; be 0xC4CC8  camera gate (unchanged)
    if (g4f68 & 0xFFFF) > 1229: return ('FRZ', r6=0)     # 0xC4C5E ld.hu -0x4f68 ; 0xC4C62 movea 1229 ; cmp ; bh 0xC4CC2   [1]
    r9 = s16(g6a00)                                      # 0xC4C6A ld.h -0x6a00[gp],r9                theta           [2: the 300 clause is gone]
    if s32(r9 ^ r16) < 0: r9 = 0                         # 0xC4C6E mov r9,r13 ; 0xC4C70 xor r16,r13 ; 0xC4C72 bge ; 0xC4C74 mov 0,r9   [3]
    pass                                                 # 0xC4C76..0xC4C7D 4 x nop
    r9 = abs(r9)                                         # 0xC4C7E cmp r0,r9 ; bge ; subr r0,r9
    v = g6a5e & 0xFFFF
    r9 = s32(r9 << (6 if v > 2880 else 4)) + 1250        # 0xC4C84..0xC4C98 shift by speed, + B
    if v <= 1382 and (r9 & 0xFFFFFFFF) > 4096: r9 = 4096 # 0xC4C9A..0xC4CA8 low-speed cap (KEPT: removing it overshoots +8..12 deg, D1/D3/D5)
    t = s32(g6dd0) >> 10                                 # 0xC4CAC ld.w -0x6dd0 ; sar 10            I in S units
    if r16 < 0: t = -t                                   # 0xC4CB2..0xC4CB6  t = sgn(E') I
    if t >= r9: return ('FRZ', r6=0)                     # 0xC4CB8 cmp r9,r13 ; bge 0xC4CC2         winding past the bound
    if (ramp & 0x8000) == 0: return ('FRZ', r6=0)        # 0xC4CBC andi 0x8000,r14 ; bne 0xC4CD8    ramp-in freeze
    return ('DONE', 0x29D7A)                             # 0xC4CD8 jmp [r6] -> Honda's I: inc = ((E'>>5)*40)>>3, ICL 8192; P/D/sum as V298
# frozen <=> |hand| > 1229  or  sgn(E').(I8>>10) >= bound  or  ramp < 0x8000 ;  bound = B if sign(th) != sign(E') else (|th|<<4|6)+B, cap 4096 at v<=1382
```

= D1's `d1c_cave` at the in-place addresses; the golden model gets it as `_self_check_v299` (contract 94 → 95 symbols, hash unchanged: it
prints nothing) — a build-round prerequisite (S3-11), not done here (barred).

### 1.3 Verification of the in-place construction (EVIDENCE, run this session)

| check | method | result |
|---|---|---|
| no transfer lands in the rewritten span | Ghidra dry-run listing of 0xC4C00–0xC4CD9 (77 instructions): every branch target enumerated | the only target inside 0xC4C6A..0xC4C7D is the removed block's own `bnh 0xC4C7A` @0xC4C70; the cave is entered only by `jarl 0xC4C00,r6` @0x29D76 (hook listing re-read); FRZ/CAM/DONE returns 0x29D7E / 0x29D7A, op-skip 0x2A164 unchanged |
| the bytes execute the mirror | `synthesis/syn_h1_inplace.py` (8.0 s): V850E2 interpreter (nl_cave.Cpu/score_time.Cpu2, D3's harness) on the in-place FLIGHT cave vs `d1_time.D1Lane.cave_stage` (asym, thr 1229, sgn 0); checks E′, exit address, r6, r26, every preserved register, no RAM written | **0/5748 valid, 0/5516 op-skip, 0/736 camera** mismatches |
| D1c's relinked hex implements the same loop | same harness on D1's `d1c_flight.hex` | 0/1945 valid, 0/1798 skip, 0/257 cam |
| the check can fail | in-place bytes vs a mirror without the asymmetric bound; vs the V298 mirror | **8/712** and **157/712** mismatches |
| control | V298 bytes vs V298 mirror | 0/712, 0/682, 0/106 |
| instruction forms | Ghidra's V298 listing carries `xor r16,r9` = `30 49`, `mov r16,r6` = `10 30`, `mov 0,r6` = `00 32`, `bge +4` = `ae 05` (twice) | the new bytes are those forms with the register fields 13/9: `30 69`, `09 68`, `00 4a`, `ae 05`; `00 00` = nop (= `mov r0,r0`) |

**Relink plan: none.** The table pointer `mov 0xC4CDA,r9` @0xC4C1C and every displacement are unchanged. The build round still decodes the
BUILT image in Ghidra, re-runs H1 on the built bytes, and runs the adversarial pass (CLAUDE.md), per S3-10.

**GATE 1.** No `st.*` in the cave (listing + H1 "no RAM written" on every path). Read set shrinks: gp-0x4f60 (the signed word) is no
longer read; gp-0x6abe/-0x6a5e/-0x4f68/-0x6a00/-0x6dd0 and r25 as V298. No new state word, so no engage/disengage/bail init to trace;
gp-0x6dd0 stays Honda's, zeroed by the 0x2A164 epilogue on every A2/B2/op-skip path (unchanged bytes).

**Wire instrument (zero bytes, inert, on the wire now).** (i) **Rule-identity replay** (D1's `d1_r79` test D): the lane replayed on the
flight's own inputs under the V298 and V299 rules, R² vs the 0x1AB tap per 30-s settled window; on r79 (V298 true) V298 wins **18/18**
windows, dR² p50 +0.605 (my re-run); on a V299 wire the order must invert (F1). (ii) **carFw = A16B**. (iii) The bar shows the tap live.
No freeze bit is spent: it would need the 0x14A telemetry cave (a second cave) and the replay already separates the rules at dR² +0.6.

---

## 2. Fork update (StarPilot, branch Dom, on top of `2712e1336`; one commit; read-only here)

| # | file / function | the diff in words | param (default = V298 → config A / B) | toggle? |
|---|---|---|---|---|
| F1 | `opendbc/car/honda/values.py` `CarControllerParams`, `carcontroller.py __init__` | `ANGLE_LIMITS.MAX_ANGLE_RATE` from a param (deg/s ÷ 100), clamped [60, 450]; VM jerk/accel limits untouched (`lateral.apply_steer_angle_limits_vm`: `min(jerk-limit, MAX_ANGLE_RATE)`, so above ≈ 6 m/s the jerk limit still governs) | `AccordAngleMaxRate` 120 → A 120 / **B 250** | yes |
| F2 | `_update_angle` | `ANGLE_ERROR_MAX_V` knots ≤ 11.75 m/s × scale, clamped [1, 2]; 17.5 / 26.9 m/s knots unchanged (highway untested on r79) | `AccordAngleClipScale` 1.0 → A 1.0 / **B 1.6** (27.2/24.8/31.2/27.2/8.5/4.5°) | yes |
| F3 | `_update_angle` (override state) | **G4 gate**: ON if \|tq\| > hard, or \|tq\| > 600 for ≥ debounce·100 consecutive frames; OFF at ≤ 500 (unchanged `ANGLE_OVERRIDE_OFF`); one int counter, reset when \|tq\| ≤ 600 or not latActive | `AccordAngleOvrHard` 600 → **1200**; `AccordAngleOvrDebounce` 0 → **0.08** s | yes |
| F4 | `_update_angle` (O1 setpoint) | `θ + rate·lead` | `AccordAngleOvrLead` 0.06 → **0** | yes |
| F5 | `_update_angle` (release / engage) | on the O1 release edge and the latActive rising edge: limiter restarts from the wheel (as today) and a timer scales BOTH `max_angle_delta` and `error_max` by `since/T` | `AccordAngleTakeover` 0 → **0.4** s | yes |
| F6 | `carstate.py` `get_can_parsers` + `update` | list `("STEER_MOTOR_TORQUE", float("nan"))` on the pt bus **only when `EPS_ANGLE_LOOP_FW`** (never read it unlisted: `VLDict` auto-adds it non-optional, S3); `raw = MOTOR_TORQUE` (10-bit, `_honda_common.dbc`), `s10 = (-1 if raw & 0x200 else 1)·(raw & 0x1FF)`, `ret.steeringTorqueEps = -8·s10` (T, + = left, the carState convention; tap + = right on 100 % of r79 holds) | — (code; no Honda consumer of `steeringTorqueEps` today) | n/a |
| F7 | `selfdrive/ui/onroad/starpilot/torque_bar.py` `TorqueBar._update_state` (angle branch) | on the Accord angle FW with the param on: `bar = clip(-carState.steeringTorqueEps / 2461, -1, 1)` (2461 T = SCL 15360 × 5346 / 32768, the lane rail); keep the 0.1 s filter; the `(a_lat + accel_diff)/maxLateralAccel` formula stays for every other car. **Unit test on r79 caches: sign agreement with today's bar ≥ 0.85** (D2/D5 as written are inverted: 0.058/0.146) | `AccordAngleBarFromEps` false → **true** (A and B) | yes |
| F8 | `carcontroller.py update` (instrument) | in angle mode `new_actuators.torque` (0 on 100 % of r79 frames) := 1·O1 + 2·takeover-active + 4·rate/jerk-bound + 16·clip-bound + 32·debounce-pending + 64·O1-entered-via-hard | — (always on in angle mode) | n/a |
| F9 | `values.py`, `interface.py` | `HONDA_ACCORD_EPS_ANGLE_LOOP_FW` → tuple {A16A, A16B}; `_get_params` uses `in` | — | n/a |
| F10 | `common/params_keys.h` | the seven `AccordAngle*` keys (PERSISTENT, SETTINGS_SIMPLE) so Galaxy carries them | — | — |

**Not changed:** `SteerDelay` / `UseAutoSteerDelay` (D2a's +0.10 s is left out of this drive: S1 cannot assess its 20 Hz effect and it
would add a third mechanism to one drive); no post-clip lead (S1 finding 5: positive wheel-rate feedback while clip-bound); no plan lead
(D2b: later, separate); `SteerRatio` 16.84 pin kept.

**Toggle configs** (written by the kit codec as `fork-config/write_v298_config.py` does; the keys exist only after F10 is deployed and
Params rebuilt): `toggle-config_V299-A_relays-bar.json` = V298 rev-2 config + {OvrHard 1200, OvrDebounce 0.08, OvrLead 0, Takeover 0.4,
BarFromEps true, MaxRate 120, ClipScale 1.0}; `toggle-config_V299-B_authority.json` = A + {MaxRate 250, ClipScale 1.6}; REVERT = the
V298 rev-2 config (all seven at V298 defaults).

**The override path, proven to yield to a real hand (binding rule):**
- **Physical yield is firmware-only and unchanged**: the dir-2 hand fade (×0.85 at \|bar\| 1216 → ×0.30 at ≥ 2289, record 0xE54FC) and the
  0.5 s request-drop ramp are byte-identical (S3 census, my re-read of the cal/record blocks). The I freezes at 1229 = Honda's own
  steeringPressed level, within one 1 kHz tick (V298: 512). The lane is ≤ 2461 T in every state.
- **Setpoint yield**: G4 fires the same frame \|tq\| > 1200 raw. On r79 it catches **116/116** steeringPressed episodes, never later than
  steeringPressed + 10 ms (the i−1 pairing), vs V298's 600/500 (my re-run of `cf_fork_r79.py`, 1.7 s). S2 OV (hand 1500 words): fork O1 at
  40 ms (V298 30), release t90 0.43–0.52 s, release overshoot ≤ 2.6°.
- **Declared cost** (S2, BELIEF on the stiff-hand model): during an active override drag at 5 m/s the lane's residual torque is 0.89 of its
  pre-hand value (V298 0.76), peak tap under the hand 56 % of rail (47 %), hand force 435 T (372, **+17 %**): the I integrates until 1229,
  and with lead 0 the setpoint trails the dragged wheel by a frame. The driver always wins (fade); FAIL band F7; toggle fallback
  `AccordAngleOvrLead` 0.03 (keeps most of the O1-loop margin, D2's table).
- Light hands 300–1200 raw: no firmware freeze (V298 froze); the I winds only within the asymmetric bound (toward centre ≤ B ≈ 200 T);
  above 600 raw the fork follows the wheel after ≤ 80 ms. N1 lens (S2 LH, light 400-word hand 2 s): worst release lurch **9.1°** (V298 13.9,
  D1c 11.2), outward 5 m/s median 3.7° (7.0); co-steer release droop ≤ 1.6° (V298 ≤ 2.3°, D1 lens worst 3.0°).

---

## 3. GATE 2 and the time criteria

### 3.1 GATE 2 at the common grid (S1's one engine; inner loop = V298 by bytes; EVIDENCE as computed by S1, anchors re-read)

| loop (state) | block | fails | worst PM − bar (where) | min GM | note |
|---|---|---|---|---|---|
| inner PID (= V298) | R2 box, 19 members × 16 speeds × 5 frames × e −1/0/10 | **0** | +9.1° (39.1°, b_lo×ms_free+h10 @11 m/s FA.83) | 12.4 dB | panel-2 engine agrees; SCORE-FREQ C3B-P 38.5° @11.9 |
| inner PD (I frozen / at the bound) | same | 0 | +17.1° | — | the asymmetric bound only switches PID ↔ PD |
| inner PID, r79 frames (D ×0.55 / ×0.88, P ×0.93 / ×0.96) | | 2 sub-bar | 28.5–30.0° at b_lo×ms_free+h10 @10–11 m/s, ρ 0.991–0.994, ζ 0.11–0.14 | | V298's own; inherited |
| inner, curve-hold op-points a 1.5 / 2.5 m/s² | | V298's 24 / 101 (ms_free family, declared R3*) | min 6.1° (ms_free), ρ 0.9985 | | unchanged; the ms_free ruling is the operator's |
| friction DF A 1° | | V298's 1441 sub-30 (PM < 30° below 0.5–2° sliding amplitude) | | | no limit cycle predicted; unchanged |
| **O1 relay loop, lead 0 (B and A)** | 19 members × 3 frames × e 0/10, PID/PD | — | Trt 30 / 60 / 90 ms: **64.1° / 11.4 dB · 44.3–45.0° / 9.4–9.6 dB · 33.1–33.8° / 8.3 dB** | | V298 (lead 0.06): 66.1 / 11.8 · 61.1 / **6.0** · 27.5 / **3.2 dB**; crossing moves 5.2 → 4.7 Hz; max \|S_tot\| 2.42 (V298 3.72) |
| clip-bound loop (PID, no post-clip lead) | | — | 64.1 / 11.4 · 44.3 / 9.6 · 33.1 / 8.3 | | = V298's (clip ×1.6 changes how often it closes, not its margins) |
| path loop (τ_o 1 s, 60 ms) | nominal | — | PMo 59.3° | 16 dB | = V298 (no reference lead) |
| 13–17 / 18–22 Hz \|L\| vs V295 | | | 0.942 / 0.973 | | = V298; 5–30 Hz ×1.000 |

### 3.2 The composite scored as ONE row of the common S2 scorer (`synthesis/syn_s2.py`, 36 s for 4 groups in 4 processes; `syn_s2_ti.py`
cap sweep 5.2 s; S2's engine unchanged, only the candidate table extended; my V298 row reproduces S2's published V298 row cell for cell)

Member r79F, median of noise seeds 1–3; [worst over both members × seeds]. TI = 60° hands-off turn-in at 320/216 deg/s.

| cand | t90 s 3/8 | ω pk deg/s 3/8 | ovs ° [worst] | tap pk % rail [worst] | frz tog/s 3/8 | I kept 3/8 | hand-lost @3 | stall-surge 3/8 | O1 eps 3/8 | r4–8 Hz 3/8 | r1.6–3 Hz 3/8 | unwind under ° @3 | LH worst lurch ° | LH outward @5 median | OV t_O1 ms 5/15 | tap under hand % @5 | hand T @5 | C2 slow e_rms 15/25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 1.77/1.80 | 97/90 | 1.6 [2.5] | 54 [60] | 14.7/16.1 | 0.57/0.52 | 0.40 | 5/9 | 11/14 | 8.5/9.1 | 5.1/6.5 | 4.2 | 13.9 | 7.0 | 30/160 | 47 | 372 | 0.99/0.60 |
| D1c (fw only, V298 fork) | 1.23/1.43 | 103/84 | 3.0 [5.0] | 57 [67] | 0.0/0.0 | 0.58/0.96 | 0.00 | **0/0** | 8/13 | 6.6/8.7 | 6.9/6.9 | 0.6 | 11.2 | 4.1 | 30/160 | 48 | 366 | 0.95/0.54 |
| D2a (fork only, V298 fw) | 1.06/0.92 | 121/121 | 1.0 [1.7] | 57 [64] | 9.8/13.5 | 0.46/0.47 | 0.54 | 2/2 | 2/2 | 5.7/5.8 | 9.5/11.6 | 1.8 | 14.9 | 6.8 | 40/240 | 55 | 399 | 0.92/0.51 |
| **V299 = D1c fw + config B (cap 250)** | **0.78/0.85** | **172/158** | 3.6 [5.9] | 68 [71] | 0.8/0.0 | 0.57/0.95 | 0.04 | 3/3 | 3/3 | **6.7/5.9** | 17.5/15.8 | **0.6** | **9.1** | **3.6** | 40/240 | 56 | 435 | 0.95/0.53 |
| same, cap 300 | 1.22/0.85 | 138/158 | 3.6 [5.9] | 68 [71] | 1.2/0.0 | 0.59/0.95 | 0.04 | 4/3 | 4/3 | 7.0/5.9 | 17.2/15.8 | 0.6 | 9.1 | 3.7 | 40/240 | 56 | 435 | 0.95/0.53 |
| G:D1c+D3fork (S2's graft, reference) | 0.42/0.48 | 222/178 | 3.6 [7.2] | 73 [74] | 1.6/0.4 | 0.46/0.91 | 0.22 | 0/0 | 0/0 | 4.5/3.4 | 20.9/12.7 | 0.6 | 9.1 | 4.2 | **370/400** | **70** | 439 | 0.91/0.51 |

**Cap sweep at 3 m/s (t90 per seed 0/1/2/3, r79F):** cap 200: 1.10/0.83/0.82/1.32 · 220: 1.29/0.80/0.80/1.30 · 250: 1.24/0.78/0.78/1.26 ·
300: 1.40/0.76/1.22/1.22; wheel peak 160–173 deg/s for every cap ≥ 200; O1 episodes 3–5 per seed at every cap; word p99 1100–1240
(V298's rates: 680–940). At 8 m/s every cap gives 0.85 s / 158 deg/s (the VM jerk limit governs). **Reading:** above 200 deg/s the wheel is
loop-limited, not cap-limited; the 3 m/s outcome is bimodal per seed — 0.8 s when the twist stays under 1200, ≈ 1.25 s (= D1c alone)
when one instant-1200 trip lands. Cap 250 is chosen as the middle of a range the sweep cannot separate; the decider is X3 (§7), not the cap.
**Config A (cap 120, clip 1.0) on D1c firmware = the D1c row with D2a's O1 gate**: t90 ≈ 1.2/1.4 s, ω unchanged, toggles 0, N1 ≈ 9–11°.

LH per condition (lurch ° median [worst] / droop / O1 eps in the hold), V299 vs V298: c5 2.4 [3.6]/1.5/2 vs 2.6 [4.4]/1.2/7 · o5 3.6 [9.1]/0.7/2
vs 7.0 [13.9]/2.3/7 · c15 1.6 [2.6]/1.6/1 vs 0.3 [0.7]/0.3/6 · o15 0.9 [2.6]/0.9/1 vs 0.0 [1.5]/0.0/5. RD: identical for every row. D1's
`rb_n1` lens (same loop): out_2_511 at 12.5–22 m/s 5.05° (V298 4.71, D1a 15.90), nudge 3.64° (1.99), part_0.5 7.13° (7.17).

---

## 4. Route-79 counterfactuals (EVIDENCE for the rule arithmetic on the recorded wire; open loop for torque; all re-run by me)

| quantity | V298 (r79) | V299 rule | script |
|---|---|---|---|
| hands-off hand-freeze duty / discarded integration / toggles per min (all; < 5; 5–8 m/s) | 11.4 % / 28.3 % / 325 (26.2/37.7/409; 26.2/41.5/555) | **0.4 / 0.8 / 13** (0.7/0.7/19; 1.2/2.0/46) | `d1_r79` A, 3.3 s |
| pressed-hand ticks still frozen | 99.7 % | 97.3 % | A |
| stall-surges within ±0.25 s of a freeze toggle (0–5 · 5–10 · 10–20 m/s) | 22/27 · 56/68 · 6/9 | **9/27 · 26/68 · 1/9**; toggle rate 291/526/273 → 41/88/168 /min | B |
| replayed tap in hands-off manoeuvres p50 / p99 / max (LSB) | 46 / 149 / 199 (R² 0.928) | 57 / 194 / 245 (open loop on V298's errors: an upper bound) | C |
| rule-identity power | V298 wins 18/18 windows, dR² +0.605 | the next drive runs it reversed | D |
| fork O1 episodes / no-press episodes / s | 415 / 347 / 13.8 | **79 / 30 / 1.6**; hands caught 116/116 ≤ +10 ms; releases 415 → 79 | `cf_fork_r79` A, 1.7 s |
| open-loop P demand on the hard windows p90 / max (LSB), clip-bound share | 66 / 115, 0.2 % | B: 191 / 192, 20.1 % (recorded wheel, not re-closed) | B |
| cap-bound frames in the 0.3 s after a release | 83.6 % | 58.6 % (A) · 81.8 % (B, cap 300 run; cap 250 not re-run: BELIEF similar) | B |
| 0x1AB validity (61,113 frames, bus 1) | — | checksum 100.000 %, counter step 99.997 %, CONFIG_VALID 100 % | `d1_427_check`, 5.8 s |
| bar pinned ≥ 0.9 / p50 / p99 / max | 59.7 % | **0 %** / 0.05 / 0.35 / 0.59 | `cf_fork_r79` C |
| bar sign vs today's drawing (second method, wire angle, n 31,987) | — | +tap/307.6: 0.854, corr +0.822; −tap (D2/D5 as written): 0.146, corr −0.822 | `jg_bar_sign_check`, 0.04 s |

---

## 5. Hazards and fail-safe paths

| path | V299 behaviour | evidence |
|---|---|---|
| engage (ramp 0 → 0x8000 at 328/tick) | ramp < 0x8000 still freezes the I (0xC4CBC unchanged); gp-0x6dd0 zeroed by the 0x2A164 epilogue while not running; fork: limiter from the wheel, takeover ramp 0 → full over 0.4 s | listing; S2 `eng`/RD identical |
| request drop / A2 / B2 | the cave is not entered; Honda epilogue (I8 := 0, sentinel); dir-2 ramp-out 66/tick (0.5 s) | unchanged in-place set; S2 RD identical for every row |
| 0xE4 timeout → 0x7FFF sentinel (fork dead) | as V298: P rails until the request falls; the I winds less than V298 when θ opposes E′ (bound B); no fork term can act | `sen`/`tmo` identical (D1 run 1) |
| invalid fresh rate (\|gp-0x6abe\| > 13000) | op-skip `jr 0x2A164`, bytes and target unchanged | H1 0/5516 |
| stock camera frame (arm ≠ 2) | CAM gate before the hand test: E′, op := 0, I decays ×0.125/tick | H1 0/736; listing |
| real hand ≥ 1200 raw | I frozen at 1229 within a tick; fade ×0.85 → ×0.30; fork setpoint = wheel the same frame | §2 |
| light hand 300–1200 raw | no freeze; I bounded (toward centre ≤ B); fork follows after ≤ 80 ms above 600 raw; release lurch ≤ 9.1° worst (S2), droop ≤ 1.6° | S2 LH; D1 N1 |
| hands-off reaction twist | freeze clear of it at V298's rates (p99 1103–1206 < 1229); at B's rates the sim's p99 is 1100–1240 → occasional instant-1200 O1 trips (X3) and rare 1229 freezes (hand-lost 0.04) | S2 sweep (BELIEF) |
| authority rises (B) | P may reach 61–63 % of rail at ≤ 8 m/s (V298 36–40 %); sim tap peak 68 % [71]; rail 2461 T, OCL 3072, EME/governor/lockstep/DTC cells untouched (S3); watch tap p99 vs 250 LSB | S3; S2 |
| plan glitch (step) | setpoint slews ≤ 250 deg/s (≤ the jerk limit above ≈ 6 m/s), bounded by the clip and the rail; no lead | arithmetic |
| mis-deploy: new fork on A16A / old fork on A16B | the first = D2a-on-V298 (ratchet unchanged, safe; carFw attributes it); the second = `EPS_ANGLE_LOOP_FW_MISSING`, permanent steer fault, no engage | S2 D2a row; fork `interface.py` (read) |
| 0x1AB parser | listed with `nan` (no alive timeout); a counter fault ≥ 5 still drops `canValid` (S3): r79 99.997 % clean; F8 watches it | S3 §4.2 |
| pol (gp-0x6752 = −1) | no new pol dependence: the asymmetric test uses θ and E′, both in the gp-0x6a00/E frame | trace 2026-10-02 |

---

## 6. The instrument and the drive card

**What the drive read must add** (to `rlog-tools/studies/angle_loop/drive_read_fastlane.py` / `angle_loop_drive_read.py`, after C13's
repairs — dir-2 ramp, +10-tick word timing, the R3* reversal clause): (1) the rule-identity replay, V299 rule vs V298 rule, R² vs the 0x1AB
tap per 30-s window and pooled (F1); (2) the G4 O1 reconstruction vs `co_ang` (≥ 99 % of latActive frames) and the `co_tq` bit decode:
O1 / takeover / rate-bound / clip-bound / debounce-pending / **via-hard** per frame; the via-hard census on hands-off turn-ins (X3);
(3) `cs_tqeps == −8·tap` on every frame (F8) and the drawn-bar sign vs the tap; (4) stall-surges per minute within ±0.25 s of \|bar\|
300/512 crossings (the old relay: must be flat) **and** of 1229 crossings (the re-armed relay); (5) per hands-off turn-in: t90, wheel peak,
tap peak, overshoot, sent-setpoint rate; (6) the O1 episode census split twist / hand / via-hard; (7) 4–8 Hz wheel rate near vs away from
O1; (8) R4 5–30 Hz lines, 13–17 / 18–22 Hz eng/dis; (9) release lurch after every light hold; (10) dwells/min (recorded miss); (11) carFw, `ld_lat` = 0.35.

**Drive card** (one route; ~15–30 s of symptomatic frames per item; the operator stops at the first ratchet or grind):
- Prerequisites: car LKAS **off** (violated on r79); pull Dom, Rebuild Params, flash V299 (operator names file and bus), reboot, restore
  config **A**, reboot; check carFw `A16B`, `steerControlType` angle, `SteerRatio` 16.84, the bar moves with the wheel's push, `co_tq` ≠ 0, no fault.
- **Part A (config A):** 30 s of engaged turning at 3–10 m/s, hands hovering, one hands-off turn-in and return; one light 1 s co-steer hold
  then release at ~5 and ~15 m/s; one firm grab and a hand-steered turn (expect V298's immediate yield). Reads note 4, N1, F1–F8.
- **Part B (config B, applied while parked, openpilot restarted):** 2–3 hands-off turns ≥ 60° at ≤ 8 m/s (empty lot / quiet junction, AOL on,
  hands hovering) — the exposure r79 never had (1.2 s); one grab/release; 60 s of highway hands-off. Reads note 2 and X3. Skip B if A fires any F.
- Glance at the bar throughout: the automation's lane torque as a fraction of the 6× rail (r79 would have shown ≤ 0.60).

**The sentence a null licenses.** *If F1 passes (the V299 rule is live) and the stall-surge rate near 300/512 crossings is flat, yet the
operator still reports stutter in Part A, the integrator-freeze relay was not the ratchet's mechanism; stop iterating the integral policy
(the remaining candidate is the small-correction stick, §8).* *If in Part B the via-hard bit fires on > 50 % of hands-off turn-ins, the twist
is the binder for the fork class (D2's X3): the next step is a 2-frame hard-path debounce (a toggle) and, if the freeze re-arms at 1229,
D4b's LP + motion gate (reserve).*

---

## 7. Pre-registered FAIL criteria — do not fly again if any holds

| # | criterion | means |
|---|---|---|
| F1 | the V299-rule replay does not beat the V298-rule replay on R² vs the tap (pooled dR² < +0.05, or < 2 of the ≥ 2-s hands-off windows) or carFw ≠ A16B | not live / mis-built: interpret nothing else |
| F2 | ring presence > 0.5 %, F7 > 0 /100 s, any new 5–30 Hz line; 18–22 Hz eng/dis > 2.5 (r79 1.83) or 13–17 Hz > 3.5 (2.94) | revert |
| F3 | after a hand release (steeringPressed falling edge or \|bar\| > 300 for ≥ 0.5 s): \|θ − θsp\| > 8° within 1.5 s at ≥ 8 m/s, or a swing past the setpoint > 5° on a straight; or the operator reports a lurch | the N1 class returned; revert |
| F4 | a hands-off turn-in at ≤ 10 m/s overshoots θsp by > 6° (sim 3.6 [5.9]) or > 15 % of the turn | windup beyond the model; revert |
| F5 | a light-hand episode (300 < \|word\| < 1229, ≥ 1 s, not pressed) ends with the wheel > 4° behind θsp toward centre (sim ≤ 1.6°) | droop larger than modelled; revert |
| F6 | ratchet trains ≥ 4.7 per minute of turning at 5–10 m/s, **or** stall-surges within ±0.25 s of \|bar\| 300/512 crossings still ≥ 2× the free rate | the freeze was not the mechanism; stop this class |
| F6b | stall-surges within ±0.25 s of \|bar\| **1229** crossings ≥ 2× the free rate, or hands-off hand-freeze onsets > 20 /min of turning (B) | the relay re-armed one level up → D4b's LP + motion gate is next |
| F7 | steeringPressed set while the tap stays ≥ 50 % of the rail opposing the driver for > 0.5 s, or the operator reports "fights my hands" | override feel impaired; set `AccordAngleOvrLead` 0.03 / revert |
| F8 | `cs_tqeps ≠ −8·tap` on > 0.1 % of frames, any canValid drop in angle mode, or the bar's sign disagreeing with the tap | revert the bar/parser change only |
| F9 (B) | lane tap > 250 LSB on any hands-off frame, or ≥ 300 for > 0.3 s | authority beyond the modelled envelope; drop config B |
| X3 (B, falsifier) | > 50 % of hands-off turn-ins at ≤ 8 m/s carry an O1 via the hard path (bit 64), or no-press O1 > 6 per latActive minute (r79 31, predicted 2.7) | the twist binds the fork class; see §6 |
| R9 | the operator reports grinding, ratcheting, vibration or anything new | his call; outranks every band |

---

## 8. Declared misses (each sized, each covered)

| id | miss | size | cover |
|---|---|---|---|
| M1 | **small-correction stick** (dwells/min 4.70/1.16/4.47/3.53 vs V282 0.24–0.84) not addressed: gain is GATE-2-capped (D1/D3/D5a), friction FF hunts/buzzes on the fork's 275 /min one-quantum setpoint reversals (D4), the firmware friction channel is inert at Kf ≤ 28 (D5a), S2 cannot reproduce the stick | C10 row 1 unchanged | recorded (§6); next class = fork hysteretic setpoint quantiser + torque-domain breakaway channel (D4/D5 grafts) |
| M2 | **the goal's hard-turn 1.6–3 Hz wheel-rate criterion** (r79 8.48 vs V282 ≈ 4) **worsens**: 5.1/6.5 → 17.5/15.8 deg/s (B); even A follows the setpoint better (6.9/6.9) | a faster slew IS 1.6–3 Hz content | operator ruling (§10); the stutter readouts are stall-surges, trains, 4–8 Hz |
| M3 | hand-steered turns yield by design (63.8 % of r79's hard time); no co-steer authority | unchanged | operator ruling P4 |
| M4 | overshoot returns to the design's value: 3.6° [5.9] on hands-off turn-ins (V298 1.6 [2.5], whose twist freezes suppressed it) | +2° | F4 |
| M5 | override feel under an active drag: residual 0.89 (0.76), hand +17 % (BELIEF) | | F7 + lead-0.03 toggle |
| M6 | X3: at 3 m/s the sim's twist p99 straddles 1200; one trip per turn costs ≈ 0.45 s of t90 | bimodal | X3 pre-registered; G9 debounce next |
| M7 | residual stall-surges in B's sim (3/3 per turn vs D1c's 0/0): the fork's faster slew on Coulomb friction, not the freeze | BELIEF on cause | A vs B split in the drive card |
| M8 | highway authority untested (17.5/26.9 m/s knots and VM jerk unchanged; 6 s of r79 hard frames > 12.5 m/s) | | later |
| M9 | the low-speed authority ceiling stays (A3 cap 4096: raising it overshoots +8–12°; G0 ×1.19 is GATE-2-clean but mixed in time: D1-a2, a later separate dose) | C4 | — |
| M10 | SteerDelay / plan lead (D2a/D2b) left out: the 0.1–0.4 s of unmodelled lag at 10–22 m/s (C8) is not attacked this drive | | D2b later, separately |
| M11 | the plant family matches r79 only at 10–13 m/s (S1 §2.9); the twist model is R² 0.31 and extrapolated above \|α\| 1000 in B | | every sim number is BELIEF |

---

## 9. How this class differs from V298 and from the arc since V38; terms dropped

V298 (2026-10-01) was the first loop this car closed on steering ANGLE (lineage PART6: C3-rev2-P + the camera interlock). **V299 keeps
that loop byte for byte** — every gain, table, clamp, operand, guard and gate — and changes only the **integral policy**: which hand
stops the I, and how far the I may wind. It is not a dose on a flown lever and not a re-run: the opposing-hand freeze was added by V298
for N1 and measured by route 79 as the ratchet's mechanism (the only hand-word test left is Honda's own pressed level), and the
sign-of-angle bound is a mechanism no image has carried. The arc: V38–V52 authority/filters/poles/caves · V53–V61 probes · V62–V73 the
rate lane · V74–V84 the damper · V282–V292 tuning/opening the EPS rate loop (V291/V292 opened it above 8 Hz, the 7 Hz cycle re-armed;
V289's notch handed its margin to a 16 Hz pole) · V293 torque mode · V294/V295 an acceleration trim with \|L\| ≤ 0.63 (failed their goal) ·
V298 the angle loop. V299 is the first build whose firmware edit is **smaller than its fork edit**, and the first where fork and firmware
agree on what a hand is (1200 raw ≡ 1229 words). Frozen since V298: every cell but 0xC4C64 and the 20-byte span. Caves: still one, 260 B,
0 RAM — in-place before relink, applied to the kit's own loop.

**V298 terms re-asked and dropped as no longer necessary:** the opposing-hand freeze at 300 (its N1 job moves to the asymmetric bound +
the fork's debounced O1); the hard freeze at 512 (raised to Honda's level); the fork's 600-instant O1 (held 80 ms; instant only ≥ 1200);
the 0.06 s O1 lead (it thinned the O1-loop GM to 6 dB); the 120 deg/s cap and the ×1.0 clip below 12 m/s in config B. **Kept, on
evidence:** the A3 low-speed cap 4096 (removing it overshoots), Kd 48 fresh (the loop's damping), the error clip (now the authority
bound), the camera interlock, the op-skip, A2/B2, the Honda fade.

---

## 10. Escalations — decisions that are the operator's

1. **The 1.6–3 Hz hard-turn criterion vs note 2.** Every authority design worsens it (B ×3). Keep it as a goal criterion (then B cannot
   pass it) or replace it by the stutter readouts (stall-surges, trains, 4–8 Hz, dwells). Not dropped silently.
2. **Note 2 in hand-steered turns (D5's P4).** Every design yields under a firm hand; r79's hard manoeuvres were hand-steered. Co-steer
   authority in AOL turns is an unproposed design (D3's K2 was a partial step and paid in override feel).
3. **Setpoint yield at Honda's level: instant (shipped) vs held 20 ms (G9).** Instant trips on the faster twist (X3); 20 ms misses the
   ≤ 20 ms taps (D2: 103/116 caught) while the firmware fade/freeze yield at once regardless.
4. **The ms_free GATE-2 definition** (S1 finding 2): it decides whether any highway stiffness (GB-S13) is ever eligible; this synthesis
   does not stiffen the loop the operator called robust.
5. **Accepting +17 % hand force during an active override drag** (M5) for the O1-loop margin of lead 0, or lead 0.03.
6. **One drive, two configs** (A then B) vs two drives: A alone is the ratchet read; B alone would confound it.
7. **The rail** (D3b) is not proposed: reached on 0 ms in every sim; it would open the unreplayed soft-EME band.

---

## A. What I ran (all < 30 s; nothing outside `v299_design/synthesis/`, `_scratch/v299_SYN/` and this file)

| script | wall | result |
|---|---|---|
| Python LE re-read of every cited cell (cave, imm16s, table, pointer, A3 cap, PCL/SCL/OCL, fwd, Ki, F181, CRC, free run, pattern census, hook) | 0.5 s | all as stated; V298 trailer = `zlib.crc32` |
| Ghidra dry-run listings 0xC4C00–0xC4CD9 (77 instr.), 0x29D60–0x29D8F | — | branch census §1.3; `jarl 0xC4C00,r6` @0x29D76 |
| `synthesis/syn_h1_inplace.py` | 8.0 s | in-place bytes 0/5748 · 0/5516 · 0/736; relinked D1c 0/1945; negatives 8/712, 157/712 |
| `D1-firmware-minimal/d1_r79.py` | 3.3 s | §4 rows A–D reproduced |
| `D2-fork-first/cf_fork_r79.py` | 1.7 s | G4 79/30/1.6 s, 116/116 ≤ +10 ms, bar pinned 0 % |
| `D1-firmware-minimal/d1_427_check.py` | 5.8 s | 0x1AB checksum 100 %, counter 99.997 % |
| `judges/jg_bar_sign_check.py` | 0.04 s | +tap 0.854 / corr +0.822; −tap inverted |
| `synthesis/syn_s2.py` (TI/LH/OV/C2, 4 processes) | 36 s total (per group ≤ 13 s) | the composite row, §3.2; V298 row = S2's published row |
| `synthesis/syn_s2_ti.py` (cap sweep, TI only) | 5.2 s | §3.2 sweep |
| not re-run (inherited): S1's frequency numbers (output tables re-read), D1's `rb_n1` lens, the designers' own sims | | |

Files: this spec; `v299_design/synthesis/{syn_h1_inplace.py, syn_s2.py, syn_s2_ti.py, out/syn_inplace_cave.hex}`; `_scratch/v299_SYN/{syn_h1_inplace.txt, syn_s2.json, syn_s2.md, syn_s2_ti.json, syn_s2_ti.md}`.
