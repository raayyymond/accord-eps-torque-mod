# ADV UNIT-SCALE — V297 (C3-rev2-F fallback) — 2026-10-01

**Author:** adversary UNIT-SCALE, a SUBAGENT of the orchestrator `main`. Read-only: nothing built, flashed or sent.
Ghidra: `disassemble_bytes dry_run:true` and `decompile_function` on the open V294 program (code-identical to V295;
Python diff below), plus one **decode-only** import (see §3). Nothing was saved. Python = `bin_decompile` env.

## VERDICT: **DO_NOT_FLASH**

**Why:** there is no V297 image. Criterion **U0** fired. The builder reported "NOT BUILT", and I confirmed it from the
filesystem with two methods:
- `ls`/`grep` and a Python `os.walk` over both repos, run at the start and again at the end: **0** V296/V297-named
  images, `.rwd` files or build scripts.
- `build_v297_tva.py` does not exist.
- No V297 program is open in Ghidra.
- `accord-firmwares` `git status` is clean.

The unit/scale chain cannot be re-derived from bytes that do not exist, so nothing has cleared any gate.
**"A null from the wrong image is not a null."** Everything in §2–§4 was read from the **V295 base** and the
**design hex**. None of it counts as credit for a V297 image. It is a pre-build defect hunt: its defects carry into
any build, but its passes do not.

FAIL criteria were written before any check: `00_FAIL_CRITERIA_unit_scale_written_first.txt` (U0–U11, 23:49:53Z).

| criterion | status |
|---|---|
| U0 no artifact | **FIRED** → DO_NOT_FLASH |
| U1 orphan artifact | clear (0 V297-named files outside this folder) |
| U2–U11 | **NOT EVALUABLE on V297** (no image). Pre-build design checks in §2–§4: 2 design-level defects (§4), the rest consistent |

V295 originals re-hashed at the end: image `5c044d6576314052…`, `.rwd` `f42a06bda5a737eb…`. Both unchanged.

---

## 1. Base sanity (EVIDENCE, `u1_prebuild_bytes.py`)

- **V294 vs V295, `[0x13000,0x100000)`: 6 differing bytes.** They are `0xC63EA/B` (cal b) and `0xC6FFC..F` (CRC). The
  V294 Ghidra program is therefore a valid decoder for V295 code.
- Every in-place site the design edits holds exactly the design's "V295 →" bytes:
  E1 `24 3f aa 95` · E2 `89 d1` · B2 `e2 47 00 00` · A2 `da 05` · E4 `08 80 ed 80` · HOOK `c2 82 ba 81` ·
  E5a `c7 00` · E5b `10 40 bb 41` · V1 `30`.
- Unit-chain cals in V295 match the page:

  | cell | address | value |
  |---|---|---|
  | a | `0xC63E8` | 1011 |
  | b | `0xC63EA` | 1050 |
  | C | `0xC62E6` | 1024 |
  | DB | `0xC62E4` | 4 |
  | Ki | `0xC63E6` | 0 |
  | ICL | `0xC61BA` | 10240 |
  | DCL | `0xC61B6` | 0 |
  | OCL | `0xC61B4` | 3072 |
  | P clamp | `0xC61BC` | 15360 |
  | SCL | `0xC61BE` | 15360 |
  | Kp Y | `0xE5384` ×5 | 960 |
  | Kd Y | `0xE5126` ×4 | 0 |

- Cave region `0xC4C00..0xC4D00` is all `0xFF` in V295.
- Selector-7 records (`u10_kp_kd_records.py`):
  - `0xCB994[7]` → `0xE5378` (n = 5, X = 0, 68, 112, 136, 208; Y at `+0xC` = **`0xE5384`**).
  - `0xCB7D4[7]` → `0xE511C` (n = 4, X = 0, 11, 22, 32; Y at `+0xA` = **`0xE5126`**).
  - Both are reached through the decoded LERP base arithmetic at `0x29DC6` and `0x29E76`. The design's Y addresses are correct.

## 2. The unit chain, re-derived from V295 bytes (EVIDENCE unless marked)

```
0x526CC sxh r6 ; 0x526D2 shl 2 ; 0x526D4 subr r0,r6 ; jarl clamp(+-0x4000) ; 0x526F2 st.h -> gp-0x69ae
        => sp69ae = clamp(-4*raw, +-16384)          raw = 0xE4 bytes 0-1, BE s16
cave 0xC4C00 shl 2,r16 ; 0xC4C02 sub r26,r16       => E = 4*sp69ae - r26
0x28F4C (E1) ld.h -0x6a00 -> r7 = theta (0.1 deg) ; 0x28F50/54 bail unless theta in [-12000,12000]
0x28F8E mul b ; 0x28F9A sar 0xa ; 0x28F92 mul a,s_old ; sar 0xa ; 0x28FA2 add -> s_new ; 0x28FA4 (E2) add r9,r26
        a = 0, b = 8192  => s_new = 8*theta exactly (2^13 >> 10, no truncation) ; r26 = 8 theta[n] + 8 theta[n-1]
0x28FA6..0x28FBC  r26 clamped symmetric +-C (C = 65535)  => |theta| saturates at 409.6 deg
        => E = -16*(raw + theta_eps) = 16*(theta_sp - theta) with theta_sp := -raw   (0.1 deg counts)
```

**Angle frame.**
- `0x40B04..0x40B18`: `gp-0x69ec := −gp-0x6a00`, the 0x14A angle source.
- `u2_wire_rate_vs_angle.py`: the 0x14A field correlates with d(field)/dt as expected.
- `u9_cmd_frame_r75.py`: the kit's cache `ang` = carState angle (slope 1.0000, corr 0.99999).
- ⇒ **`gp-0x6a00` = +10 × carState angle.** 0.1° per count, same sign.

**Command frame (on-car).**
- On r75, engaged and hands-off, 47 813 frames: **corr(0xE4 raw, carState angle) = −0.761**, sign agreement 7.6 %.
- So `raw` is in the CAN-reference frame (positive = right), and `θ_sp_eps = −raw` has the sign of `gp-0x6a00`.
- **The firmware chain is sign-consistent.** The fork must send `raw = −10·θ_sp(carState)`, the same convention as its
  torque command today.

**Held-rate operand `gp-0x6a56`** (decompile of `FUN_0003f776`, disasm `0x3F77E..0x3F7AE`):
- `x = pol·((abe·48·1159) >> 15)`, clamped to ±12000.
- Validity is Honda's **two-sided unsigned** test: `addi 0x32c8` ; `addi −0x6591` ; `bc` ⇒ invalid iff
  `(abe + 13000) u≥ 26001`. When invalid, x := 0 (shadow-checked).
- 0x18F packing (`0x55C62/66`): rate field = −x, 1:1. 0x14A packing (`0x40B48..4E`, `0x55B48`): rate field = −x × 0.125.
- Wire cross-check: 0x18F rate vs 0x14A rate gives slope **7.995**, corr 0.9998.

**The 1.155 ratio, re-proven on the car** (`u2`, r71b, 21 735 frames, corr **+0.9969**). Slope of the rate field
against d(angle field)/dt, by |angle|:

| \|angle\| | measured slope | predicted (from the C() knots) |
|---|---|---|
| < 10° | **0.882** | 1/1.155 = 0.866 |
| 10–30° | 0.874 | |
| 30–60° | 0.911 | |
| 60–120° | 1.014 | |
| > 120° | **1.04** | 1/0.962 = 1.040 |

- ⇒ x = **8.00 counts per deg/s of the LINEAR (motor) angle**, which is 7.05 per deg/s of θ near centre and 8.33 outward.
  The design's "κ 0.866" frame is right.
- ⇒ **sign(dθ/dt) = sign(x)**, so the fallback's P and its held D act in one frame. The fallback is pol-invariant:
  x and θ both carry pol.

**D sign.**
- E5a `0x29EDE zxh r7 → subr r0,r7` gives Kd → −Kd. E5b `0x29EE0` makes the D operand `ld.h -0x6a56`.
- So **D = (−24·x) >> 3 = −3x**, clamped to ±10240. That is −24 S per deg/s linear, ≈ 3.85 T per deg/s.
- This sign matches the stock rate loop's own feedback sign, which proves +S → +x, so the held D **damps**.
- **Every path to the D multiply passes E5a** (`u4_branch_targets.py`, positive-controlled: it finds the two known
  `br 0x29EDE` at `0x29E9E` and `0x29EB4`). It finds **0 branches into `0x29EE0..0x29EE4`**, so no path skips the
  negation. Kd is flat (Y ×4 = 24), so the LERP always yields exactly 24 before the negation.

**Driver-torque cells** (`u5`, positive-controlled on the 4 known `gp-0x69ae` writers):
- `gp-0x4f68` has a **single writer**, `0x7FECA`, and it stores `min(|gp-0x4f60|, 0xFFFF)` (`0x7FEA8..0x7FECA`).
  Every reader uses `ld.hu`. So the 512 hard-freeze and 300 opposing-freeze thresholds share one unit, raw driver
  torque (= wire × 1.024; 512 raw = 500 wire).
- `gp-0x4f60` frame (`u6`): 0x18F torque = −(tq·125 >> 7) (`0x55C50..5C`), with the same negation as the rate field.
  In manual driving with |tq| > 1200: corr(tq, rate) **+0.58**, corr(tq, angle) **+0.57**, sign agreement 0.86.
- ⇒ **the hand torque is in the θ frame**, so the opposing-hand freeze (`xor r16,r9 ; blt`) is not inverted.

**Ramp.**
- Ramp-up at `0x29574..0x29594`: when ramp + step ≥ 0x8000, ramp := **0x8000 exactly**.
- So the cave's `andi 0x8000,r14` freezes I through ramp-in and releases it only at full ramp, as designed.
- That `r14` = `gp-0x69b0` at the hook is trace record, which I did not re-trace (BELIEF here).

**I / P downstream** (`0x29D7A..0x29E5C`, dry-run):
- e5 = Ep >> 5, then deadband DB.
- I = clamp((I8 >> 3) + ((e5·Ki) >> 3), ±ICL << 7), and I8 := I << 3.
- P = clamp((Ep·Kp(sel 7)) >> 8, ±`0xC61BC`).
- The cave's bound compares `I8 >> 10` = I >> 7, its contribution to S in S counts. Consistent.
- The freeze exit `mov 0,r6 ; jr 0x29D7E` lands right after `mov r16,r6 ; sar 5,r6`, so e5 := 0. The normal exit
  `jmp [r6]` = `0x29D7A`.

**Speed key `gp-0x6a5e`.**
- The cave reads it with `ld.hu` and walks with `bh`/`bnh`. Both are unsigned, matching the unsigned voter, and the
  `0xFFFF` sentinel row terminates the walk.
- 64 counts per km/h = 230.4 per m/s:
  - EVIDENCE in firmware: the 0xE51A8 axis is 3200…8320 = 50…130 km/h at /64.
  - BELIEF: the DBC's 0.01 km/h raw unit.
  - Knots: 714 = 3.10, 1382 = 6.00, 1843 = 8.00, 2304 = 10.0, 2707 = 11.75, 2880 = 12.5, 4032 = 17.5, 6198 = 26.9 m/s.
- The cave reads the speed **ungated**, but the PID only runs when Honda's own speed-valid flag `r29` is set:
  - EVIDENCE: on the invalid branch `0x28F1C` sets `mov 0,r29`; then `0x29118 cmp r0,r29 ; be → r8 = 0` gives bVar2 = 0,
    and B2/A2 skip the PID.
  - BELIEF (trace-inherited, not re-derived): that `r29 = 0` exactly ⇔ "speed channel bad or `gp-0x67f4` ≠ 1".

**Range.**
- The r26 clamp and the sp clamp both sit at **409.6°**.
- Max |angle| over **29 cached routes** = 396.3° (r73), with 0 routes over 409.6°. The clamp is not reached in
  practice (margin ≈ 13°).

## 3. The default C3B-F cave, decoded (PRE-BUILD; not V297)

- Decode-only file: `_scratch/angle_loop/adv-unit-scale-v297/C3BF_CAVE_DISASM_ONLY_NOT_AN_ARTIFACT.bin`
  (sha `7d0d3f81…`). It is V295 plus the 220 B `c3b_cave_C3B-F.hex` (sha **`9de9365fa952`**, = the page) at `0xC4C00`.
- No CRC, no `.rwd`. It was imported into the Ghidra folder `/advU297` without analysis, disassembled with `dry_run`,
  then closed.
- `c3b_cave_C3B-F.hex` and `c3b_cave_C3B-F_score.hex` are byte-identical, so the default fallback has no op-skip and
  no add_opskip relink exposure.

What the decode shows:
- **Table pointer:** `mov 0xC4CB2,r9` is the first byte after `jmp [r6]` at `0xC4CB0`, so it is **correctly linked**.
- **The table matches the page's GB-F:** `(714,1009,892) (1843,1255,−4753) (2304,720,−1626) (2707,560,1097)
  (4032,915,1953) (6198,1948,0) (0xFFFF,1948,0)`.
- **G walk:** G = G_i + ((dx·S_i) >> 12), with S_i read as a signed `ld.h`. That is Q12; every slope equals ΔG/ΔX × 4096
  within 0.01 %.
- **Ep:** `(E·G) >> 8`.
- **Constants:** 0x200 = 512 · 0x12C = 300 · 0xB40 = 2880 · 0x4E2 = 1250 · 0x566 = 1382 · 0x1000 = 4096 (cap applied
  via `cmovh`, unsigned min).

Integer mirror of the decoded walk (`u7_gbf_surface.py`):
- **min G = 560 at v = 2705 (11.74 m/s). No G < 512 anywhere in v ∈ [0, 32000]**, so the N2 refutation is cleared on
  the design hex.
- The integer floor is within 1.23 LSB of linear interpolation.

Delivered small-signal surface, hands-off at full ramp. The output-lag DC 0.990 is inherited, BELIEF.

| m/s | G | P per deg (S) | T per deg | P-sat / T-rail (2461) at |
|---|---|---|---|---|
| ≤ 3.1 | 1009 | 276 | 44.2 | 55.7° |
| 8.0 | 1254 | 343 | 54.9 | 44.8° |
| 10.0 | 720 | 197 | 31.5 | 78.0° |
| 11.75 | 560 | 153 | 24.5 | 100° |
| 17.5 | 914 | 250 | 40.1 | 61.5° |
| ≥ 26.9 | 1948 | 532 | 85.3 | 28.9° |

The rail is the SCL product, 15360 × 0.1602 = **2461** (OCL 3072 is not reached). This is the same rail as V295.

**Overflow census (bytes):**
- Within the cave and the I/P stages: |E| ≤ 131 071; |E·Gmax| = 2.55e8 < 2³¹; |Ep| ≤ 997 368; Ep·Kp = 1.1e8;
  (Ep >> 5)·Ki = 1.2e6; worst slope term = 4.2e6.
- The held D term reaches 12000·24 = 2.9e5 before its >> 3.
- **No intermediate in the cave, I, P or D stages overflows.** The S sum and the T stage were not re-derived (§5).

## 4. Findings

1. **U0 (BLOCKING): no V297 image.** DO_NOT_FLASH. The adversarial pass on the BUILT image is still owed in full once an
   image exists. That means H1 on the FLIGHT bytes, a Ghidra decode of the image as imported, and U2–U11 re-run from
   those bytes.

2. **MEDIUM (design / instrument, applies to P and F): the pre-registered LIVE / INVERTED criterion never states the
   frame of θ, and in the kit's own cache frame it reads inverted.**
   - The page regresses `tap = c_P·(raw − 10θ) + …` and scores LIVE when c_meas/c_raw ∈ [−1.25, −0.80], and
     INVERTED → abort (R1) when the ratio > 0.
   - From the bytes, E = −16·(raw + gp-0x6a00), and gp-0x6a00 = +10·carState angle.
   - The kit's v280 caches carry `ang` = carState angle (slope 1.0000).
   - So with θ = carState angle, a **correct, live loop gives c_meas/c_raw ≈ +1 and is called INVERTED**. A genuinely
     inverted loop gives ≈ −1 and is called **LIVE**.
   - The formula is right only if θ is the **raw 0x14A field × 0.1** (= −carState angle).
   - **Fix:** name the frame on the page, or write the regressor as `(raw + 10·θ_carState)` with LIVE ⇔ ratio ∈
     [+0.80, +1.25].
   - EVIDENCE: `0x526D2/D4`, `0x40B04..0E`, `u9`.

3. **LOW–MEDIUM (design, fork prerequisite):** the FLIGHT PREREQUISITES say only "θ_sp on 0xE4 in the EPS 0.1°/count
   frame".
   - The sign is implied only in §7 (θ_sp = −raw/10).
   - Required, from the bytes and the car: **raw = −10·θ_sp(carState)**, which is CAN-reference, positive = right.
   - A fork that sends +10·θ_sp would command the mirrored angle. At engage it would pull hard toward −θ_meas, and the
     firmware cannot detect it.
   - State the sign explicitly next to the frame.

4. **REQUIREMENT (hardened fallback, the page's recommended F): there are no bytes, so nothing can be checked.**
   - When written, its rate-validity read must reproduce Honda's **two-sided unsigned** test, `(abe + 13000) u< 26001`,
     as at `0x3F786..0x3F792`. A signed compare would be one-sided.
   - It must be relinked. The add_opskip stale-link defect applies to any helper-spliced cave.
   - It must be H1'd on the flight bytes.

5. **INFO:** the rest of the unit chain in §2–§3 is consistent with the page, from bytes and two on-car checks. That
   covers the angle frame, the 1.155 / κ ratio, x at 8 counts per deg/s, the Kd sign and units, the torque-cell units
   and frame, the speed key, the G Q-format and min G, the ramp ceiling, the rail, and overflow. **These are design-level
   consistencies, not V297 passes.**

## 5. Not done

- No V297 bytes, so no image-level work: no H1, no image decode, no CRC, no assertion census. U2–U11 remain open
  for the built image.
- Not re-derived: the output-lag DC (0.990), the clamp function `FUN_00049a90` (decompile is a cmov clamp, consistent
  with the trace), `r29`'s validity preconditions, and `r14` liveness at the hook. Each is marked BELIEF where used.
- The 0xE4 request-bit position used in `u6` is the opendbc layout (BELIEF). The torque-frame conclusion does not
  depend on it.

## Files

- `00_FAIL_CRITERIA_unit_scale_written_first.txt` — the FAIL criteria, written before any check.
- `u1_prebuild_bytes.py` — base sanity: V294/V295 diff, edit-site bytes, cals.
- `u2_wire_rate_vs_angle.py` — the κ / 1.155 ratio and the rate sign, on route 71b.
- `u3_scan_69ea_writer.py` — writers of the 0x14A rate source.
- `u4_branch_targets.py` — every path to the D multiply passes E5a.
- `u5_scan_torque_cells.py` — the driver-torque cells.
- `u6_wire_torque_frame.py` — the hand-torque frame.
- `u7_gbf_surface.py` — the G walk, min G and the delivered surface.
- `u8_wire_command_direction.py` — weak r71b check.
- `u9_cmd_frame_r75.py` — the command frame on the car.
- `u10_kp_kd_records.py` — the Kp / Kd records.
- Decode aid: `_scratch/angle_loop/adv-unit-scale-v297/C3BF_CAVE_DISASM_ONLY_NOT_AN_ARTIFACT.bin`.
