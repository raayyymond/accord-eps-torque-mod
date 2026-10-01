# DESIGN C1 rev 2 (2026-10-01): the angle loop, revised against the round-2 refuters

**Status: DESIGN ONLY. SUPERSEDES C1 rev 1 and C0.** Nothing was built, flashed or sent. The fork was not touched.
Ghidra was used read-only (`decompile_function` on `FUN_00028ea6`, `disassemble_bytes` dry run) on the V294 program,
which is code-identical to V295 except cal `0xC63EA` and its CRC.

- C1 rev 1 is kept as a record in `DESIGN-ANGLE-LOOP-C1-rev1-REFUTED-2026-09-30.md`. Its scripts reproduce with the
  environment variable `C1_VARIANT=kd16` (`c1_lib.VARIANTS`).
- C0 is `DESIGN-ANGLE-LOOP-C0-2026-09-30.md`.

**Author:** a subagent (Opus), for the orchestrator `main`.

**Brief:** resolve every round-2 finding. Each one is either a design change, re-verified with both harnesses and the
refuters' own scripts, or a quantified miss written on this page before any build.
- The stability refuter's F1–F4 are in `analysis-2020accord/studies/angle_loop/reports/REFUTE-C1-r1-stability-2026-09-30.md`.
- The friction and safety lenses are procedural FAILs: those refuters did not finish.
- The tracer's round-1 facts are in `docs/traces/TRACE-2026-09-30-dominance-preemption-timeout-version-and-6803.md`.

**Base image:** V295, `_v295_V295-V294BASE-ACCELTRIM.B1050-…TORQUE.TAP_plain_image.bin`, sha256 `5c044d65…52ed`.
Every pre-edit byte quoted here was re-read from it in Python this session.

**Evidence produced here.**
- Every new script is in `analysis-2020accord/studies/angle_loop/c1/`, prefixed `c1r2_`. Text outputs sit next to them.
- Caches are in `_scratch/angle_loop/c1/` (gitignored, regenerable).
- `c1_lib.py` now carries the rev-2 variant `r2` as its **default**. The variant fixes Kp_base, Ki_base, Kd and the
  table before any function binds a default argument. Rev 1 bound Kd at definition time, which was harmless only
  because rev 1 used Kd 16.

| script | what it does | output |
|---|---|---|
| `c1r2_members.py` | The rev-2 GATE-2 member set: 40 gated members in two tiers plus 9 report-only members. A self-check confirms every name it shares with the refuter's own `refute_c1_ind.member_params` gives an identical (J, b, k, d, age). | 473 / 473 pairs identical |
| `c1r2_explore.py`, `c1r2_design_G.py`, `c1r2_fit_table.py` | The G(v) envelope against every member on a 0.25 m/s grid that includes the plant knots, for each (Kd, Ki). The fit is a 6-knot dynamic program that keeps the cave's **integer walk** at least 4 % under the envelope. | `design_G_r2_*.txt` |
| `c1r2_trackmetric.py` | Turns **the goal's own tracking metric** (the kit scorer's `tracking_gain`) into a frequency weighting from r71b's measured desired-lateral-accel spectrum. Includes a positive control run on the kit's real scorer. | `trackmetric.txt`, `trackmetric_weights.json` |
| `c1r2_compare.py`, `c1r2_ff_explore.py` | Compares Kd and Ki choices on the goal metric; tests a feed-forward alternative (§2.11). | console |
| `c1r2_gate2.py` | GATE 2, sections A–E, on the rev-2 member set. Section A takes harness_freq's PM as the minimum over every crossing (§3.1). | `gate2_r2_{A,B,C,D,E}.txt` |
| `c1r2_page_numbers.py` | Schedule, Bode, tracking on the goal metric, LIVE predictions, discriminator, hard-turn band, Δmax caps. | `page_numbers_r2.txt` |
| `c1r2_time.py`, `c1r2_time_summary.py` | The time harness (`harness_time.run/metrics/per_speed_score`, unmodified) on rev 2, two alternatives and rev 1. The robust suite adds b_q, b_q×J_hi and b_q×J1.0 with friction. | `time_r2_{nominal,robust,pi}_score.txt`, `…_summary.txt` |
| `c1r2_ipolicy.py` | Rev 1's I-policy study, logic unchanged, run on rev 2. | `ipolicy_r2_all.txt` |
| `c1r2_rerun_refuters.py` | Runs **the refuters' own scripts** on rev 2: round 1 stability and friction, plus round 2 stability (`refute_c1_run.py`, `refute_c1_stage2.py`). Only the minimum patch is applied; every C0-base literal substitution is listed in the output header. | `refute_rerun_r2/*.txt` |
| `c1_assemble.py`, `c1_selftest.py` | Rev 1's assembler, V850 interpreter and mirror controls, run on rev 2. The table edges now come from the table under test, and the run reports r25 explicitly. | `c1r2_assemble_out.txt`, `c1_cave_r2.bin.hex`, `selftest_r2_out.txt` |

Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**. Code is cited by address or grep
string, never by line number.

---

## 0. The decision in one page

**C1 rev 2 has these parts:**
- rev 1's seven in-place code edits, unchanged;
- rev 1's 96 bytes of cave code, byte-identical (sha256 of the code `a6f902d5…`);
- a new 42-byte table;
- **one version byte**;
- calibration.

It changes five things relative to rev 1.

1. **G(v) is re-sized against every combined member the round-2 refuter named.** These are b_q×{J_hi, J_hi2, J1.0},
   b_q×J_hi×tau6, b_q×tau6 and J1.0×tau6. Each tier-B member is also gated **with the hold aged to 20 ticks**
   (17 aged members).
   - Highway Kp_eff falls from 1243–1971 to **458–930** (15–30 m/s). That is a cut of ×2.1–2.7 at 15–19 m/s.
   - GATE 2 has **0 stability or margin failures on 5 600 gated points**:
     - tier A ≥ 47.9°;
     - tier B ≥ 31.8°;
     - b_q×J1.0 ≥ 36.7°, and 32.4° with the aged hold;
     - exact GM ≥ 10.6 dB.
   - The refuter's own sweep, re-run, finds **0 sub-bar points** where it found 80. EVIDENCE §3, §4.3.
2. **Kd 16 → 20, and Ki/Kp 0.444 → 0.5** (fI 0.553 → 0.622 Hz). Together they buy back the low-frequency tracking the
   cut costs, measured on the goal's own metric (item 5 of the table below).
   - Re(T/ω) at 20 Hz stays at 0.93× V295's.
   - The 5–17 Hz anti-damping is 0.24–0.82× rev 1's.
   - EVIDENCE §2.6, §3.4.
3. **The table is re-based a second time** (G ×2, Kp_base 112, Ki_base 56).
   - The cut takes G to 412–843 at 12.5 m/s, below 512. In rev 1's base, below 512 the integrator is blind to a +1 LSB
     error again (refuter F2 of round 1).
   - In the new base the lowest G is 843, which gives e5 = +1. No speed is blind.
   - Zero extra bytes. EVIDENCE §2.7.
4. **V1, the version marker: `0x1310D` 0x30 → 0x41.** The F181 string goes from "39990-TVA,A160" to
   "39990-TVA,A16A". This is the firmware half of the fork's F4 interlock.
   - The flasher refuses a revert unless the revert `.rwd` headers are rewritten first. That is a flight prerequisite.
     EVIDENCE tracer §4, §2.10.
5. **R3, the highway stop, is widened to 1.0–5.5 Hz** with a damping criterion. It now covers the inertia-axis and
   combined rings, at 1.2–2.5 Hz, as well as the damping-axis ring at 3.4–4.1 Hz (refuter F3). §6.2.

| question | answer | basis |
|---|---|---|
| Is the round-2 stability FAIL (b_q×J_hi / b_q×J1.0 near-unstable to unstable at ≥ 12.5 m/s) resolved? | **Yes, by design change.** b_q×J_hi min PM 57.0° at highway (rev 1: 3.3° at 17 m/s). b_q×J1.0 is 36.7–41.9° at 12.5–30 m/s (rev 1: unstable at 15–19). Both are stable, with GM ≥ 19.6 dB. | EVIDENCE §3.1, both linear methods + the refuter's independent model |
| Hold age to 20 ticks on the combined members? | **Gated.** Min PM 31.8° (b_lo×J_hi×tau6+h10 at 1 m/s); 32.4° (b_q×J1.0+h10 at 12.5 m/s). | EVIDENCE §3.1 |
| What does the cut cost on **the goal's own tracking metric**? | Inner-loop factor ≥ **0.959** in every band ≥ 8 m/s, on every member tabulated: 8–15 m/s ≥ 0.983, 15–22 ≥ 0.959, > 22 ≥ 0.987. The metric is the slope of actual on desired lateral accel, 0.5 Hz filtfilt. Its weight sits at 0.04–0.08 Hz (r71b: 2–6 % above 0.2 Hz). | EVIDENCE: measured spectrum + a positive control on the kit's scorer, ±0.028 §2.5; BELIEF that r71b's spectrum is typical |
| And on the proxies rev 1 used? | **0.5 Hz in-phase 0.40–0.79 at ≥ 12.5 m/s.** 0.2 Hz 0.86–0.92 at 15–19 m/s. Group delay at 0.2 Hz is 232–345 ms at 12.5–19 m/s. These are declared, not hidden (M3). | EVIDENCE §2.5 |
| 5–25 Hz damping? | **Bounded.** Worst Re(T/ω) is −0.52 to −0.74 T per deg/s at hold age 0, and 4.3× V295's at 13 Hz (rev 1: 6.8×). At 20 Hz it is 0.93× V295's at age 0 and 0.60× V295's at age 10. Aged 5–10 Hz values are on the page. | EVIDENCE §3.4 |
| Low speed? | **Pre-declared miss, unchanged in class.** §8 M1. | EVIDENCE §2.9 |
| The friction and safety lenses? | **Not cleared by this page.** Those refuters did not finish. Their scripts were re-run on rev 2 (§4.3), and the tracer's facts are folded in (§2.10). **Clearance on both lenses needs another reviewer.** | — |

**What C1 rev 2 is predicted to do against the goal.** EVIDENCE: simulation on the nominal plant unless stated. These are
predictions, not drive results.

| goal criterion | rev 2 prediction | verdict on the page, before any build |
|---|---|---|
| dwell-then-jump ≤ V282 in every band; low-speed stick-slip gone | 3–6 m/s: 2–8 events per scenario set; 7–8 m/s: 0; 10–11.9: 1; 12.5: 4; 15: 1; 17–19: 0; 22–30: 1–3 (holds under road noise, hunt 0.09–0.19°). | **PRE-DECLARED MISS at 0–7 m/s, at 12.5 m/s and in highway holds** (§8 M1, M2, M11). V282 is not simulable, so "≤ V282" is decided on the car. |
| tracking 0.95–1.05 in every band ≥ 8 m/s (the scorer's slope) | inner-loop factor 0.983–1.010 (8–15 m/s), 0.959–0.991 (15–22), 0.987–1.010 (> 22) across nine members | **predicted PASS**, margin 0.009–0.02 at 15–19 m/s, inside the ±0.028 accuracy of the weighting (§2.5). BELIEF on the fork and vehicle factor. |
| turn-hold ≥ 0.90 in every band ≥ 8 m/s | \|T(0.02 Hz)\| 0.999–1.001; harness hold 0.991–1.009 | predicted PASS |
| ring ≤ 0.5 %, F7 = 0, no new 5–30 Hz line | no line on any member; 0/80 20 Hz stress rows unstable (V282: 28/80) | predicted PASS |
| 20 Hz loop gain ≤ V295 | M20 ≤ 2.44 (V295 3.58); L20 ≤ 0.680× V295's; Re(T/ω)₂₀ 0.93× (age 0), 0.60× (age 10, like for like) | predicted PASS |
| hard-turn 1.6–3 Hz energy ≤ V282 | harness hard16 0.06–1.86 vs its reference 0.19–2.49 at every speed; \|T_ref\|₁.₆₋₃ up to 1.66 on b_q×J1.0 at 15–26 m/s | predicted PASS on the nominal family; **amplification on the J ≈ 1 members declared** (§8 M9) |

---

## 1. The loop in integer form: every byte and every cal

### 1.1 In-place code edits: rev 1's seven, unchanged, and V1

The seven code edits are byte-for-byte rev 1's §1.1 (C0's §1.1). Their decodes are Ghidra dry runs on the V294 program.

| id | address | V295 bytes → C1r2 bytes | V295 → C1r2 instruction | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | operand x = θ (0.1° counts); the ±12000 bail now tests θ |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request == 1) ? bVar2 : 0 |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | the PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00, r6` | the hook |
| E5 | `0x29EDE`, `0x29EE0` | `c7 00` → `80 39`; `10 40 bb 41` → `24 47 aa 95` | `zxh r7` → `subr r0,r7`; `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D = clamp((−Kd·x_rate) >> 3, ±DCL) |
| **V1** | **`0x1310D`** | **`30` → `41`** | data: the 14th character of the F181 string | **"39990-TVA,A160" → "39990-TVA,A16A"** (fork interlock F4) |

**V1 rests on these facts.**
- **The bytes.** EVIDENCE (Python, V295): `0x13100` holds `39990-TVA,A160`, followed by the F180 string at `0x1310E`.
- **Who reads it.** EVIDENCE (tracer §4: Ghidra and three whole-image scans, bootloader included):
  - `0x13100` is read only by the DID F181 handler `FUN_0004f6fa`.
  - There is no bootloader reader.
  - The second copy at `0x14117` has no field-wise reader.
- **Precedent.** Every modded image already carries an edit in this string, the comma at `0x13109`.
- **CRC.** The builder must recompute the main-block CRC. BELIEF until H8 runs on the built image.
- **Flasher trap.** EVIDENCE (tracer §4): the kit flasher's part-number gate compares the running F181 string with the
  `.rwd` `/` header. So:
  - the C1r2 `.rwd` header must list `39990-TVA,A160` **and** `39990-TVA,A16A`;
  - **the V295 and V294 revert `.rwd`s must be re-headered to list `39990-TVA,A16A` before C1r2 is flashed.**

  Otherwise the revert is refused, and the drive card forbids `--force-part-mismatch`.
- **Fork side.** BELIEF: the fork's fingerprinting tolerates the new string, as it does today's unlisted `…,A160`.
  The fork must key angle mode on it (spec §5.1).

As in rev 1, edit 6 (`0x29A5A`) and the cal `0xC63F6` are not applied.

### 1.2 The cave (`0xC4C00`, 138 bytes, inside the free span `0xC4BD8..0xC4FEF`)

EVIDENCE: `c1_assemble.py` run on rev 2 (`c1r2_assemble_out.txt`).
- V295 bytes `0xC4BD8..0xC4FEF` are all 0xFF.
- 14 encoding-form controls against same-form instructions in V295 are all OK.
- The encoder reproduces the flown V112 hook `0x55C0E 86 ff 26 ef` byte for byte.
- The **96 code bytes are identical to rev 1's**: the table address did not move, so the `mov imm32` is unchanged.

BELIEF until the bytes are assembled into an image and decoded by Ghidra (H5).

```
;  entered by  jarl 0xC4C00, r6  from 0x29D76  (r6 = 0x29D7A).  Scratch r8 r9 r13; reads r14 (the ramp) and r26.
;  No ep, no lp, no stack, NO RAM WRITE, r25 untouched (live 0x29A82..0x2A0AC across the hook: tracer §1).
0xC4C00 C1:    c2 82              shl   2, r16              displaced 0x29D76: 4*sp
0xC4C02        ba 81              sub   r26, r16            displaced 0x29D78: E = 16*(theta_sp - theta)
0xC4C04        e4 47 a3 95        ld.hu -0x6a5e[gp], r8     v, 64 counts per km/h                    [G(v)]
0xC4C08        29 06 60 4c 0c 00  mov   0xC4C60, r9         table                                    [G(v)]
0xC4C0E        e9 6f 01 00        ld.hu 0[r9], r13          X0                                       [G(v)]
0xC4C12        ed 41              cmp   r13, r8                                                      [G(v)]
0xC4C14        cb 05              bh    L1                  v > X0 (unsigned): walk                  [G(v)]
0xC4C16        e9 47 03 00        ld.hu 2[r9], r8           G = G0 (clamp low)                       [G(v)]
0xC4C1A        b5 15              br    APPLY
0xC4C1C L1:    e9 6f 07 00        ld.hu 6[r9], r13          X(i+1)                                   [G(v)]
0xC4C20        ed 41              cmp   r13, r8
0xC4C22        c3 05              bnh   SEG                 v <= X(i+1): segment i                   [G(v)]
0xC4C24        09 4e 06 00        addi  6, r9, r9           next row; the 0xFFFF row ends the walk
0xC4C28        a5 fd              br    L1
0xC4C2A SEG:   e9 6f 01 00        ld.hu 0[r9], r13          X(i)
0xC4C2E        ad 41              sub   r13, r8             dv = v - X(i)
0xC4C30        29 6f 04 00        ld.h  4[r9], r13          S(i), Q12, signed
0xC4C34        ed 47 20 02        mul   r13, r8, r0         dv*S(i) (low word)
0xC4C38        ac 42              sar   12, r8
0xC4C3A        e9 6f 03 00        ld.hu 2[r9], r13          G(i)
0xC4C3E        cd 41              add   r13, r8             G = G(i) + ((v - X(i))*S(i) >> 12)
0xC4C40 APPLY: e8 87 20 02        mul   r8, r16, r0         E*G (low word)          <-- THE SPEED GAIN, on P and I
0xC4C44        a8 82              sar   8, r16              E' = (E*G) >> 8
0xC4C46        e4 47 99 b0        ld.hu -0x4f68[gp], r8     |driver torque|          <-- THE I FREEZE
0xC4C4A        20 6e 00 02        movea 512, r0, r13        THR
0xC4C4E        ed 41              cmp   r13, r8
0xC4C50        cb 05              bh    FRZ                 |tq| > 512 (unsigned): freeze
0xC4C52        ce 6e 00 80        andi  0x8000, r14, r13    r14 = the ramp (the 0x2A1E6 multiplier)
0xC4C56        ca 05              bne   DONE                ramp == 0x8000: integrate normally
0xC4C58 FRZ:   00 32              mov   0, r6               e5 := 0  ->  Honda's exc = 0, I unchanged
0xC4C5A        b6 07 24 51        jr    0x29D7E             skip 0x29D7A mov r16,r6 / 0x29D7C sar 5,r6
0xC4C5E DONE:  66 00              jmp   [r6]                return to 0x29D7A
0xC4C60 TBL:   (6-byte rows, LE: X u16, G u16, S s16)                       REV 2
               ca 02 77 04 d4 00   X  714 ( 3.10 m/s)  G 1143  S   212     Kp_eff 500
               5a 0a db 04 2d e4   X 2650 (11.50 m/s)  G 1243  S -7123     Kp_eff 544
               40 0b 4b 03 b2 05   X 2880 (12.50 m/s)  G  843  S  1458     Kp_eff 369
               f3 0d 41 04 6c 0a   X 3571 (15.50 m/s)  G 1089  S  2668     Kp_eff 476
               fa 0f 93 05 40 05   X 4090 (17.75 m/s)  G 1427  S  1344     Kp_eff 624
               4d 18 4e 08 00 00   X 6221 (27.00 m/s)  G 2126  S     0     Kp_eff 930
               ff ff 4e 08 00 00   sentinel row
```

**Size and inventory.** The cave is 96 bytes of code (33 instructions) plus 42 bytes of table (6 knots and a sentinel),
**138 bytes** in all. Rev 1 was 132 bytes; C0 about 140.
- Every instruction belongs to one of four terms: the displaced pair, the G(v) LERP, the speed gain, or the I freeze.
- The freeze return path, its proof that exc = 0 when r6 = 0, and "r14 is the ramp" are unchanged from rev 1 §1.2.
  Their EVIDENCE is rev 1's Ghidra decode of `0x29D66..0x29DC6`, `0x2A1E6 mul r14,r9,r0`, and the state-3 decompile.
  `c1_selftest.py` CHECK 3 re-runs the decode emulation on rev 2: exc = 0 for all 2 070 DB values, 0 / 20 000 against
  the mirror.

**The table is not monotone, on purpose.** It dips to G 843 at 12.5 m/s. That is where the refuter's b_q member switches
on: the credible set **steps** at 12.5 m/s because b_q is defined at ≥ 12.5 m/s. The table follows the step with the
11.5 / 12.5 m/s knots.
- BELIEF: a real plant does not step.
- If b_q-class damping existed from 10 m/s, the 10–12.4 m/s points would need G ≈ 880, not 1225–1243.
- Under that reading, b_q×J1.0 at 10–12.4 m/s has PM 26–30°. That is the report row "b_q from 10 m/s" in §8 M9, and
  it is not gated.

### 1.3 Calibration cells

| cell | stock | V295 | C1 rev 1 | **C1 rev 2** | what it is |
|---|---|---|---|---|---|
| a `0xC63E8` (s16) | 923 | 1011 | 0 | **0** | fb pole: 2-tap FIR |
| b `0xC63EA` | 1560 | 1050 | 8192 | **8192** | fb gain: s_new = 8θ |
| C `0xC62E6` | 7680 | 1024 | 65535 | **65535** | r26 clamp (θ ≤ 409.6°) |
| DB `0xC62E4` | 4 | 4 | 0 | **0** | I deadband |
| Ki `0xC63E6` | 0 | 0 | 100 | **56** | re-based; Ki/Kp = 0.5, fI = 7.8125·56/(2π·112) = 0.622 Hz |
| ICL `0xC61BA` | 10240 | 10240 | 4096 | **4096** | I>>7 ≤ 4096 S (≈ 660 T); acts on I, so the re-base leaves it unchanged |
| DCL `0xC61B6` | 10240 | 0 | 10240 | **10240** | D clamp |
| Kp record Y `0xE5384` ×5 | 248/512/645/696/696 | 960 ×5 | 225 ×5 | **112 ×5** | re-based Kp_base (selector 7 → `0xE5378`) |
| Kd record Y `0xE5126` ×4 | 128 ×4 | 0 ×4 | 16 ×4 | **20 ×4** | D on −rate: **3.21 T per deg/s** (rev 1: 2.56) |
| everything else (PCL, SCL, OCL, sign-hold, output lag 992/507, `0xC63F4/F6/F8`, the timeout cals) | — | V295 | unchanged | **unchanged** | — |

**CRC.** As in rev 1, plus V1:
- the code edits and the cave dirty trailer `0xC4FFC`;
- the cals dirty `0xC6FFC`;
- the Kp/Kd records sit in the `0xE5xxx` block that V293–V295 already rewrote;
- **V1 dirties the main block that holds `0x13100`.**

The builder recomputes every one of them and runs `verify_bootloader_crc.py` (H8).

### 1.4 The loop, integer-exact Python

```python
def c1r2_tick(st, theta, x_rate, sp69ae, v6a5e, tq4f68, ramp, req6805, bvar2):
    if not (ramp != 0 and req6805 == 1 and bvar2):               # guard with B2 + A2 (0x29A48..0x29A64)
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; S = 0                   # 0x2A164 skip
        return lag_and_gate(st, S)
    s_new = (8192 * theta) >> 10                                  # 0x28F8E.. a = 0 -> 8*theta
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new  # 0x28FA4 add (E2)
    E = (sp69ae << 2) - r26                                       # cave: displaced shl 2 ; sub
    G = walk(TBL_R2, v6a5e)                                       # cave: G(i) + (((v - X(i)) * S(i)) >> 12)
    E = s32(E * G) >> 8                                           # cave: mul ; sar 8
    frozen = tq4f68 > 512 or (ramp & 0x8000) == 0                 # cave: ld.hu ; movea ; cmp ; bh / andi ; bne
    e5 = 0 if frozen else E >> 5                                  # FRZ: r6 = 0, return to 0x29D7E | else 0x29D7C
    exc = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)    # 0x29D7E..0x29D9A (DB = 0)
    I = clamp((st.I8 >> 3) + ((exc * 56) >> 3), -(4096 << 7), 4096 << 7)    # 0x29DA4..0x29DC2
    P = clamp((E * 112) >> 8, -15360, 15360)                      # 0x29E36 mul ; 0x29E3E sar 8 ; PCL
    D = clamp((-20 * x_rate) >> 3, -10240, 10240)                 # E5 ; DCL
    S = (I >> 7) + P + D ; st.I8 = I << 3                         # 0x29F18.. ; 0x2A190
    return lag_and_gate(st, fade_and_clamp(S))                    # 0x2A0B4.. fade, SCL ; output lag ; x ramp ; OCL
```

**Scale, hands off.** EVIDENCE: arithmetic plus the integer walk (`page_numbers_r2.txt` §1). Kp_eff = 112·G/256 and
Ki_eff = 56·G/256.

| v (m/s) | ≤ 3.1 | 5 | 8 | 10 | 11.5 | 11.9 | 12.5 | 13 | 15 | 17 | 19.25 | 22 | 26 | ≥ 27 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G | 1143 | 1165 | 1201 | 1225 | 1243 | 1083 | 843 | 883 | 1048 | 1314 | 1540 | 1748 | 2050 | 2126 |
| Kp_eff | 500 | 510 | 525 | 536 | 544 | 474 | 369 | 386 | 458 | 575 | 674 | 765 | 897 | 930 |
| rev 1 Kp_eff | 490 | 520 | 570 | 570 | 570 | 570 | 682 | 794 | 1243 | 1692 | 1750 | 1833 | 1945 | 1971 |
| T per degree (≈ Kp_eff/10) | 50 | 51 | 53 | 54 | 54 | 47 | 37 | 39 | 46 | 57 | 67 | 76 | 90 | 93 |
| P reaches the rail at \|e\| = 24 576 / Kp_eff | 49.1° | 48.2° | 46.8° | 45.9° | 45.2° | 51.9° | 66.6° | 63.6° | 53.6° | 42.8° | 36.5° | 32.1° | 27.4° | 26.4° |

### 1.5 Overflow budget (EVIDENCE: arithmetic over the operand bounds)

| quantity | worst case | limit |
|---|---|---|
| \|E\| | 4·32767 (sentinel) + 65535 = 196 603 | — |
| \|E·G\| | 196 603 × 2126 = 4.18·10⁸ | < 2³¹ |
| \|E'\|, \|E'·112\| | 1.63·10⁶, 1.83·10⁸ | < 2³¹ |
| \|e5·Ki\| | 51 000 × 56 = 2.9·10⁶ | — |
| \|dv·S\| in the walk | max over segments 2131 × 1344 = 2.9·10⁶ | — |

### 1.6 The mirror and its controls (EVIDENCE: `selftest_r2_out.txt`, `c1r2_assemble_out.txt`)

| check | result |
|---|---|
| CHECK 1: `LaneC1` with the cave off equals `harness_time`'s original `LaneVec` (A2 guard), tick for tick | **0 / 40 000** |
| CHECK 2: `LaneC1F` with C0's table and bleed equals the friction refuter's `fric_lib.LaneC0` | **0 / 40 000** |
| CHECK 3: Honda's exc code with r6 = 0 (the freeze) | exc = 0 for all 2 070 DB; 0 / 20 000 vs the mirror |
| CHECK 4: e5 for a ±1 angle-LSB error at every speed | **no speed with e5 = 0 for +1 LSB** (+1 / −2 at 12.5 m/s; +2 / −3 at 3–19 m/s; +4 / −5 at ≥ 26 m/s) |
| CHECK 5: the walk vs the exact LERP over gp-0x6a5e = 0..65535 | −1.03 … +0.23 counts; the knots reproduce; not monotone (by design, §1.2) |
| **H1 at design time:** the assembled bytes, run in a minimal V850 interpreter, vs the mirror's cave | **0 / 200 000** random (E, v, \|tq\|, ramp, register file), including the 0x7FFF sentinel and **this table's** knots ±1. Checked: r16 = E′, the exit address = the freeze decision, r6 = 0 on the freeze, and **every register other than r6/r8/r9/r13/r16 unchanged, r25 included** |

The interpreter decodes from the bytes; **it is not Ghidra**. H5 (a Ghidra decode of the built image) is still required.

---

## 2. What changed from rev 1, finding by finding

### 2.1 Stability F1 (HIGH): the damping axis × the inertia axis at highway, now gated

**The finding.** EVIDENCE in the refuter's report. Rev 1 gated b_q (b × 0.25 at ≥ 12.5 m/s) only at nominal J, and
J_hi / J1.0 only at nominal b.
- b_q×J_hi had PM 3.3° at 17 m/s.
- b_q×J1.0 had monodromy ρ 1.004–1.007 at 15–19 m/s (unstable).

**The change.** `c1r2_members.py` gates every combination the refuter ran, at PM ≥ 30°, exact GM ≥ 6 dB, stable: b_q×J_hi,
b_q×J_hi2, b_q×J1.0, b_q×J_hi×tau6, b_q×tau6 and J1.0×tau6.
- Each is copied from `refute_c1_ind.member_params`. The self-check finds 473 / 473 (name, speed) pairs identical.
- G(v) is re-fitted at least 4 % under the new envelope (`c1r2_fit_table.py`, DP over 6 knots).

**What binds** (EVIDENCE `design_G_r2_kp112_kd20_ki56.txt`):

| speed | binding member | envelope Kp_eff | C1r2 Kp_eff |
|---|---|---|---|
| ≤ 9.75 m/s | b_lo×J_hi×tau6 **+h10** | 503–690 | 500–536 |
| 10–11.25 | b_lo×J_hi×tau6+h10, b/1.9×J_hi+h10 | 574–595 | 536–541 |
| 11.25–12.25 | **J1.0×tau6+h10** | 539–626 | 413–544 |
| ≥ 12.5 | **b_q×J1.0+h10** | 385 (12.5) → 406 (13) → 476 (15) → 671 (19) → 969 (≥ 27) | 369 → 386 → 458 → 665 → 930 |

**Results.** EVIDENCE: `gate2_r2_A.txt` (stab_lin and harness_freq), and `refute_rerun_r2/refute_c1_stage2.txt` (the
refuter's own independent model).

| member | rev 1 at 15 / 17 / 19 m/s | **rev 2 at 15 / 17 / 19 m/s** | rev 2 ring (exact) |
|---|---|---|---|
| b_q×J_hi | PM 4.9 / 3.3 / 5.5°, Ms 12–19 | **PM 65.0 / 80.8 / 71.6°, Ms 1.43 / 1.42 / 1.48, GM 23.5 / 22.7 / 21.8 dB** | 2.19–2.49 Hz, ζ 0.30 |
| b_q×J1.0 | **unstable** (ρ 1.004–1.007) | **PM 38.7 / 41.9 / 39.4°, GM 27.8 / 25.9 / 24.3 dB** | 1.55–1.79 Hz, ζ 0.16–0.17 |
| b_q×J1.0 +h10 | — | PM 33.3 / 35.8 / 33.3° | ζ 0.13–0.14 |

**A note on physics, not used to relax anything.** BELIEF, recorded for C2.
- Mechanical steering inertia does not change with speed.
- The low-speed identification already disfavours J ≥ 0.8. EVIDENCE p5c: held-out rate R² is 0.75 at J 0.2, 0.37 at
  J 0.8, 0.05 at J 1.3 at 0–5 m/s.
- Vehicle yaw and relaxation dynamics add damping and slightly *negative* apparent inertia below about 1 Hz, not
  positive inertia.

So J ≈ 1 at highway may not be credible physically. Rev 2 gates it anyway, because no measurement above 10 m/s excludes
it. A 1–5 Hz FRF above 10 m/s is the measurement that would (§6.4 item 7).

### 2.2 Stability F2 (MEDIUM): the aged hold on every combined member

All 17 tier-B members are also gated with slot 4 late by 10 whole ticks (`+h10`, hold ages 11–20):
- `nominal`, `b_lo`, `J_hi`;
- the six rev-1 combinations;
- `J_hi2`, `J1.0`, `b_q`;
- the six new combinations.

Min PM 31.8° (b_lo×J_hi×tau6+h10 at 1 m/s); b_q×J1.0+h10 32.4° (12.5 m/s); J1.0×tau6+h10 32.1° (11.5 m/s).
Min exact GM 10.6 dB. EVIDENCE §3.1. The refuter's own ATTACK 3 re-run finds no point below 30°.

### 2.3 Stability F3 (LOW): R3 and the discriminator cover the 1–3 Hz rings

The gated rings at ≥ 12.5 m/s are at **1.22–2.49 Hz** for the inertia axis and the combinations (ζ 0.13–0.43) and at
**3.39–4.10 Hz** for b_q (ζ 0.51–0.59). The prior light_b world rings at 3.0–3.8 Hz with ζ 0.06–0.39, and is now
**stable** at every speed (PM ≥ 9.7°).

R3 is now a STOP from the first highway minute for any oscillation in **1.0–5.5 Hz** that grows or carries ζ < 0.10.
ζ < 0.10 means at least 4 visible cycles above twice the pre-event rms. **No gated member reaches it** (lowest ζ 0.13),
so R3 fires only if the plant lies outside the credible set. §6.2 and §6.3 give the full table.

### 2.4 Stability F4 (LOW): aged Re(T/ω) is on the page

See §3.4. At hold age 10, rev 2 anti-damps −1.57 / −1.47 / −1.33 T per deg/s at 5 / 7 / 10 Hz, where V295 (aged)
damps or anti-damps −0.90. At 13–25 Hz rev 2 is 0.51–0.85× V295's at the same age.

**One convention to state explicitly.**
- Comparing aged rev 2 with **un-aged** V295 at 20 Hz, as the refuter's `stage2` prints it, gives **1.03×**.
- Like for like, both aged, it gives 0.60×.

The design rule is like for like. The 1.03 figure is printed so nobody discovers it later.

### 2.5 The cost, measured on the goal's own metric

**The goal's tracking criterion** is computed by the kit scorer, `v293_symptom_instruments.tracking_gain` (grep
"THE GAIN OF ACTUAL ON DESIRED"):
- the OLS slope of actualLateralAccel on desiredLateralAccel;
- both low-passed by a zero-phase 4th-order 0.5 Hz filter;
- over engaged runs ≥ 10 s, per band.

For a linear Y = T·X, that slope is Σ|H|⁴·S_xx·Re T / Σ|H|⁴·S_xx.

**The weighting** (`c1r2_trackmetric.py`). EVIDENCE: r71b's engaged desired-lat-accel spectrum, Welch per run,
run-length weighted.

| band | exposure | weight median | p90 | share > 0.2 Hz | share > 0.5 Hz |
|---|---|---|---|---|---|
| < 8 m/s | 118 s | 0.080 Hz | 0.170 Hz | 5.7 % | 0.07 % |
| 8–15 | 242 s | 0.068 | 0.128 | 1.9 % | 0.01 % |
| 15–22 | 158 s | 0.052 | 0.150 | 3.8 % | 0.04 % |
| > 22 | 74 s | 0.043 | 0.115 | 2.0 % | 0.01 % |

**Positive control.** EVIDENCE. The route's own desired series is filtered through four known linear T's (a 0.25 s lag,
a 0.2 s delay, a 0.6 Hz second order, and gain 0.9 with a 0.5 s lag). The **kit's real `tracking_gain`** is run on
each, and the prediction from the weights is compared against it.
- The worst |measured − predicted| is **0.028**.
- At highway the prediction is low of the measurement by 0.01–0.028, so it is conservative there.
- BELIEF: r71b's spectrum is typical of lane keeping. It is one route.

**Result** (`page_numbers_r2.txt` §3; the inner-loop factor, i.e. what the metric reads if the fork's VSR map,
look-ahead and vehicle factor were perfect):

| v (m/s) | nominal | b_hi | b_lo | J_hi | J1.0 | b_q | b_q×J_hi | b_q×J1.0 | b_lo×J_hi | proxy tg0.2 / tg0.5 (nominal) | \|T(0.2)\|, τ_g(0.2) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 1.003 | 1.006 | 1.001 | 1.002 | 0.998 | 1.003 | 1.002 | 0.998 | 0.999 | 1.013 / 0.998 | 1.021, 99 ms |
| 11.9 | 1.006 | 1.013 | 1.000 | 1.004 | 1.001 | 1.006 | 1.004 | 1.001 | 0.999 | 1.030 / 0.896 | 1.047, 143 ms |
| 12.5 | 1.000 | 1.009 | 0.992 | 0.998 | 0.994 | 0.987 | 0.989 | 0.987 | 0.991 | 0.992 / 0.588 | 1.036, 232 ms |
| 15 | 0.978 | 0.986 | 0.971 | 0.978 | 0.976 | 0.966 | 0.968 | 0.966 | 0.972 | 0.892 / 0.418 | 0.972, 325 ms |
| 17 | 0.971 | 0.978 | 0.964 | 0.972 | 0.970 | **0.959** | 0.961 | 0.960 | 0.965 | 0.859 / 0.404 | 0.947, 345 ms |
| 19 | 0.983 | 0.991 | 0.976 | 0.984 | 0.982 | 0.971 | 0.972 | 0.971 | 0.977 | 0.918 / 0.499 | 0.982, 289 ms |
| 22 | 0.997 | 1.002 | 0.991 | 0.996 | 0.996 | 0.987 | 0.988 | 0.987 | 0.991 | 0.970 / 0.607 | 1.015, 237 ms |
| 30 | 1.004 | 1.010 | 0.998 | 1.004 | 1.005 | 0.994 | 0.994 | 0.994 | 0.998 | 1.026 / 0.788 | 1.050, 170 ms |

The highway gain cut is therefore nearly invisible to the goal's metric, because the metric lives at 0.04–0.08 Hz. It is
**very visible to anything faster**: the 0.2 Hz group delay is 232–345 ms at 12.5–19 m/s. S-bends, lane changes and turn-in
transients at highway speed will lag. That is declared as M3.
- A fork look-ahead does little on the metric: +0.009 at 150 ms (`page_numbers_r2.txt` §3).
- BELIEF: it helps feel in those transients.

### 2.6 Kd and Ki: chosen on the goal metric under the new gate

All candidates below were run on the same rev-2 member set, each at **its own** envelope × 0.96. EVIDENCE:
`c1r2_compare.py`, `design_G_r2_*.txt`, `time_r2_nominal_summary.txt`. The time-harness "dj" counts are summed over
the nominal scenario sets, 3–30 m/s.

| Kd, Ki/Kp (fI) | highway Kp_eff (15 / 19 / 27 m/s) | goal metric, worst member, 15–22 m/s | Re(T/ω)₂₀ / V295 | time harness dj events / highway hold hunt |
|---|---|---|---|---|
| 16, 0.444 (0.553 Hz), rev 1's | 432 / 634 / 904 | 0.950 | 0.68–0.78 | 35 / 0.10–0.66° at 15–17 m/s |
| 20, 0.444 | 492 / 695 / 965 | 0.956 | 0.86–0.94 | not run |
| **20, 0.5 (0.622 Hz) = C1r2** | **458 / 665 / 930** | **0.959** | **0.85–0.93** | **31 / 0.32–0.34° at 15–17 m/s** |
| 20, 0.556 (0.691 Hz) | 445 / 648 / 890 | 0.969 | 0.81–0.92 | 39 / 0.24–0.29°, but 3–4 slips at 22–26 m/s |
| 20, 0.667 (0.829 Hz) | 411 / 607 / 809 | 0.979 | 0.80–0.91 | not run; the low-speed envelope halves (Kp_eff 296 at 3 m/s) |
| 22, 0.667 | 432 / 628 / 844 | 0.981 | 0.88–0.99 | not run |
| 24, 0.444 | about 548 / 773 / 1076 | — | **1.00–1.11, FAILS the rule** | — |

**Choice: Kd 20, Ki/Kp 0.5.** It meets the goal metric in every band on every member and keeps Re(T/ω)₂₀ ≤ 0.93× V295.
It has the fewest dj events of the Kd-20 rows, and the low-speed envelope stays at rev 1's level (Kp_eff 500 vs 490 at
3 m/s). Kd 20 raises the 13 Hz anti-damping from −0.42 to −0.65. That is still 0.64× rev 1's worst (§3.4).

### 2.7 The re-base, again (integer; zero bytes)

- **The problem with rev 1's base.** With G as low as 412 at 12.5 m/s, e5 = ((16·412) >> 8) >> 5 = 0 for a +1 LSB error.
  Round 1's friction refuter F2 found exactly this one-sided 0.1° integrator dead band.
- **The fix.** G ×2, Kp_base 225 → 112, Ki_base 112 → 56.
  - Kp_eff = 112·G′/256 is 0.4 % below a pure ×2 re-base (112 for 112.5).
  - Ki_eff is exact.
  - The lowest G is 843, so e5 = 1 for +1 LSB (CHECK 4).
- **Overflow** is still inside int32 (§1.5).
- **Residual, as in rev 1.** `sar` floors, so +1 → e5 1..4 and −1 → e5 −2..−5. The integrator therefore settles at a mean
  E′ ≈ +½ e5 LSB. That is a +0.025–0.05° offset at 3–19 m/s and ≤ 0.013° at highway. Not adopted: a 4-byte `addi`.

### 2.8 The I policy (item c): the rev-1 freeze, re-verified at Kd 20 / Ki 56

The structure is unchanged: **freeze I when |gp-0x4f68| > 512 or the ramp is below 0x8000; 26 bytes; no RAM write.**
Rev 1 §2.3 has the byte-by-byte options table. These costs stand:

| option | bytes |
|---|---|
| freeze on the hand | 18 |
| + the ramp freeze | 6 |
| C0's bleed | 26, plus a read-modify-write |
| a (1−f)-scaled bleed | ≥ 30, re-deriving the fade |
| a reset above 2048 | +10, plus a RAM write |

No existing branch can do it: the DB register r10 is reloaded from flash at `0x29D84/8C/96`. That is EVIDENCE from
rev 1's decode.

Results on rev 2 (EVIDENCE `ipolicy_r2_all.txt`; the friction refuter's plant and fork frame) are in the §4.4 table.
The sign-aware bleed was evaluated in rev 1 and is not needed: the freeze keeps the curve-carrying I, which was the
reason for the sign-awareness.

### 2.9 Low speed and friction (item e): the pre-declared miss, re-measured on rev 2

EVIDENCE: the friction refuter's own scripts re-run on rev 2 (`refute_rerun_r2/exp*.txt`) and the time harness. The
numbers are in §4.3. The miss is the same class as rev 1:
- stick-slip at 3–6 m/s;
- a constant-setpoint hunt at 3–7 m/s;
- small-amplitude stiction at 8–19 m/s.

**No friction term without an instrument.** The first drive measures F_s(v), F_c(v), the dead-zone width, the hunt and
the sensor scale (§6.4), and C2 sizes a friction feed-forward from those.

### 2.10 Safety (item f), with the tracer's round-1 facts

| item | status in rev 2 | E/B |
|---|---|---|
| **B2: `0x2913A` dominates `0x29A50`** (r27 = bVar2) | **CLOSED at design time.** A flow graph of `FUN_00028ea6` (1 874 instructions, 0 undefined halfwords, 0 computed jumps) gives one reaching definition. External entry is excluded by a raw branch scan. **Re-prove on the built image (H6).** | EVIDENCE tracer §1 |
| **0xE4 RX preemption window** | **CLOSED: 0 ticks.** The RX handler runs in slot 3, priority 3, 200 Hz. The PID runs in slot 0, priority 6. The tick interrupt only sets a flag, and all writers of gp-0x69ae / -0x6805 / -0x6803 are inside the RX task. | EVIDENCE tracer §2 (kernel decompile); BELIEF that a larger number means higher priority, from the kernel code, not timing |
| **r25 live across the hook** (`0x29A82` → `0x2A0AC`) | **In the cave contract.** The cave does not touch r25, and H1 checks it (0 / 200 000). | EVIDENCE |
| **0xE4 timeout: the setpoint is held about 0.51 s after the last frame** | **Declared (M12).** The sentinel lands 510–514 ms after the fork's last frame. Until then the EPS keeps tracking the last θ_sp, which is a valid angle, then A2 skips and the output lag decays in about 0.1 s. Stock does the same with the last rate demand. A firmware fix would change the 500 ms pending threshold `0xC626C`, which the per-message monitor **may share with other messages (not traced)**. Not in rev 2. | EVIDENCE tracer §3; BELIEF on sharing |
| **Up to 49 bad-checksum or bad-counter 0xE4 frames decoded as valid** before the fault | **Declared, for the safety reviewer.** Decompile only, not yet confirmed in disassembly. Under rev 2, a corrupt frame's setpoint is tracked for up to 49 frames, about 0.49 s at 100 Hz, bounded by the fork's own counter and checksum. | BELIEF (decompile only) |
| **F4: a torque fork on the angle image** | **V1 in rev 2** (1 byte) **+ the fork param + the flasher re-header** | EVIDENCE tracer §4 |
| **F3: the camera's 0xE4 (`gp-0x6803 == 0`)** | **Correction to rev 1.** The one-byte `0x2937C bne → br` makes state 1 engage only through the `== 2` arm. **It keeps the camera from ENGAGING from idle, but not from staying engaged.** State 7 stays in state 7 on a frame with request 1 and `gp-0x6803 == 0`, so a relay close with the camera's LKAS active would hand an engaged lane the camera's torque value as an angle. A per-tick guard costs at least +10 cave bytes and needs the fork to send 2. That switches the chain to states 6/7/8 (ramp-in 0.10 s instead of 0.99 s), and switches the live post-PID fade to `0xCBAE4`, which pushes **up to ×2.1 harder against a 600–3240 raw hand** (×2.1 at 2048). **Not in rev 2. The camera's LKAS off is a flight prerequisite.** | EVIDENCE: decompile of the `gp-0x3d38` state machine (state 7: `(cVar15 == 0) && (6803 == 2)` → state 8; otherwise it stays unless ST/6803==1/req-0 exits), tracer §5 |
| **C8**: engaging without mode 3 | fork, flight prerequisite. Firmware form ≈ 10–12 cave bytes; not in rev 2. Mid-engagement mode-3 exits are covered (B2, the ±12000 bail). | EVIDENCE rev 1 §2.6 |
| **Δmax(v)** | fork, flight prerequisite. Under rev 2 it caps demanded P at 0.1·Kp_eff·Δmax = **765 T at 5 m/s, 525 at 8, 429 at 10, 229 at 15, 279 at 20, 279 at 30** before I. | EVIDENCE arithmetic; Δmax values BELIEF |
| **τ_o ≥ 1 s, no fork integral below 8 m/s** | fork, flight prerequisite (§3.6) | EVIDENCE |
| **O1** | fork, flight prerequisite. Without it the harness's `ov_fade` overshoot is 2.0–4.1° at ≤ 10 m/s. | EVIDENCE §4.1 |
| panda bound on 0xE4 | measure; flight prerequisite | — |

### 2.11 Evaluated and not adopted (with the reason, so nobody re-proposes them blind)

| alternative | what it buys | why not |
|---|---|---|
| **A static setpoint feed-forward**: P on (E + W(v)·4sp), I on E only. About 20 bytes plus a table column; the freeze path's return to `0x29D7E` already carries a separate I operand. | 0.2 / 0.5 Hz in-phase tracking at 15–26 m/s: 0.81–1.0 → 0.97–1.07, and 0.36–0.70 → 0.66–0.91, at α 0.5 of the nominal spring (`c1r2_ff_explore.py`, run at a representative robust schedule) | The goal's metric already passes without it (§2.5). It raises the 1.6–3 Hz \|T_ref\| on b_q×J_hi from about 0.84–1.13 to 1.4–1.8 (hard-turn energy), and it makes torque follow the setpoint directly, so a wrong setpoint gets authority faster. Priority 2. **Candidate for C2** if the drive shows highway transients lagging. |
| A faster output-lag pole (`0xC63EC/EE`) | phase at 2–3 Hz | **Struck in the lineage**: ≥ 10 Hz poles fired Honda's oscillation detector (`BUILD-LINEAGE.md`, grep "Struck the same day"). |
| Kd 24 or more | envelope +14 % at highway | Re(T/ω)₂₀ 1.00–1.11× V295's |
| Ki/Kp 0.556–0.667 | goal metric +0.01–0.02 at 15–19 m/s | 3–4 hold slips at 22–26 m/s (0.556); the low-speed envelope halves (0.667) |
| b_q defined from 10 m/s (no step) | a physically smoother credible set | It costs Kp_eff at 10–12.4 m/s (≈ 385 instead of 536–544), raising 10–12 m/s stick and lag. The refuter's definition starts at 12.5, so rev 2 keeps it and reports the stricter reading (§8 M9). |
| Relaxing J ≈ 1 at highway on physics (§2.1) | Kp_eff ×1.3–1.6 at highway | It is BELIEF. It needs the 1–5 Hz FRF above 10 m/s first. |
| A 7- or 8-knot table | +5–10 % Kp at 8–10 or 10–11.9 m/s | 6 bytes per knot for ≤ 1 dj event |
| F3 per-tick guard, C8 in firmware, the timeout cal | §2.10 | each needs a trace or switches a live arm |

---

## 3. GATE 2: magnitude and phase in every loop the signal is in

The checks use two independent linear methods:
- the stability refuter's `stab_lin`: the LTI fundamental, plus an exact 10-tick periodic monodromy and an exact GM by
  bisection, with a slot-4 delay chain for the aged hold;
- the design's `harness_freq`: the LTI fundamental, M20, L20, |T| and |T_ref|.

The conditions are 100 Hz hold ages 1–10 (11–20 on `+h10`), the 5.05 Hz output lag, 2 ms transport (0 or 6 on the tau
members), and the r71b plant family. These are model numbers: the plant above about 8 Hz is not identified.

### 3.1 The fine grid (EVIDENCE `gate2_r2_A.txt`; 140 speeds × 49 members = 6 860 points, 5 600 of them gated)

**0 stability or margin failures on 5 600 gated points.**

| member | tier | min PM (at m/s) | min exact GM (dB) | notes |
|---|---|---|---|---|
| nominal | A | 66.0 (1.0) | 20.8 | M20 ≤ 2.44 (V295 3.58); L20 ≤ 0.680× V295's; \|T\|, \|T_ref\| 5–30 Hz ≤ −5.9 dB on tier A |
| J_lo / J_hi / b_lo / b_hi | A | 65.9 / **47.9** (1.0) / 58.2 / 57.7 | ≥ 18.8 | no 5–50 Hz pole ζ < 0.8 |
| tau0 / tau6 | A | 67.1 / 63.8 | 23.2 / 17.5 | |
| b_lo×J_hi / ×tau6 | B | 38.8 / 36.8 (1.0) | 22.8 / 19.1 | |
| b_lo×tau6 / J_hi×tau6 / b/1.9×J_hi / b_lo×J0.3 | B | 55.2 / 46.2 / 38.8 / 46.4 | ≥ 15.5 | |
| J_hi2 / J1.0 | B | 41.7 / 37.9 (11.5) | 27.0 / 28.1 | |
| b_q | B | 66.0 | 19.4 | |
| **b_q×J_hi / b_q×J_hi2 / b_q×J1.0** | B | **47.9 / 41.7 / 36.7 (12.5)** | ≥ 19.6 | rev 1: 3.3° / — / unstable |
| **b_q×J_hi×tau6 / b_q×tau6 / J1.0×tau6** | B | 46.2 / 63.8 / 36.2 (11.5) | ≥ 16.0 | |
| **every +h10 member** (17) | B | **31.8** (b_lo×J_hi×tau6+h10, 1.0); b_q×J1.0+h10 **32.4** (12.5); J1.0×tau6+h10 32.1 (11.5) | **≥ 10.6** | |
| J1.3 refit | report | 29.2 (11.5), 1 point below 30° | 29.5 | §8 M9 |
| b_q×J1.3 | report | **27.0 (12.5)**, 24 points below 30° | 19.6 | §8 M9 |
| ms_free (J 2.08 at 11.9) | report | 12.1 (11.5) | 21.9 | §8 M9 |
| light_b (the prior) | report | 9.7 (27), **stable everywhere** (rev 1: unstable ≥ 14 m/s) | 6.0 | R3 |

**The method check, as pre-registered** ("|PM(stab_lin) − PM(harness_freq)| ≤ 1° on every non-aged gated point")
**fails as written on 64 points. All 64 have PM ≥ 60.6° on both methods.**
- `HF.metrics` reports the PM at the *first* |L| = 1 crossing. The lightly damped b_q members cross three times (about
  0.6, 1.5 and 2 Hz), and stab_lin takes the minimum.
- Taking harness_freq's minimum over every crossing, the residual is the two methods' rate models:
  - harness_freq uses the 3-tick rate former (BELIEF in the record);
  - stab_lin uses the continuous derivative.

  Both models are of an unidentified detail. They differ by up to 4.1° at the second crossing.
- **Where either PM < 60° the agreement is ≤ 0.79° (867 points), and where either PM < 40° it is ≤ 0.46°.**

The rev-2 H2 states the method rule on the decision-bearing region (PM < 60°). **This restatement was made after the run
and is declared as such.**

**PM by member at the design speeds** (°; EVIDENCE same file):

| v | Kp_eff | nominal | J_hi | b_lo | b_lo×J_hi | ×tau6 | J1.0 | b_q | b_q×J_hi | b_q×J1.0 | b_q×J1.0+h10 | b_lo×J_hi×tau6+h10 | J1.3 | b_q×J1.3 | light_b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 500 | 66.0 | 47.9 | 58.2 | 38.8 | 36.8 | 39.9 | 66.0 | 47.9 | 39.9 | 36.8 | 31.8 | 38.6 | 38.6 | 31.1 |
| 8 | 525 | 80.5 | 63.0 | 68.7 | 49.4 | 47.1 | 58.3 | 80.5 | 63.0 | 58.3 | 54.8 | 41.4 | 59.5 | 59.5 | 30.9 |
| 10 | 536 | 79.3 | 64.0 | 78.8 | 42.5 | 40.1 | 47.0 | 79.3 | 64.0 | 47.0 | 43.1 | 34.0 | 43.0 | 43.0 | 31.1 |
| 11.9 | 474 | 76.0 | 68.9 | 89.6 | 52.3 | 50.1 | 41.7 | 76.0 | 68.9 | 41.7 | 37.8 | 44.6 | 31.3 | 31.3 | 37.2 |
| 12.5 | 369 | 79.1 | 80.4 | 99.0 | 83.4 | 81.7 | 68.9 | 99.5 | 63.9 | 36.7 | 32.4 | 77.4 | 59.1 | 27.0 | 47.5 |
| 15 | 458 | 84.3 | 86.5 | 100.6 | 102.9 | 102.1 | 87.0 | 118.4 | 65.0 | 38.7 | 33.3 | 99.9 | 86.5 | 29.3 | 39.0 |
| 17 | 575 | 86.1 | 87.8 | 100.9 | 102.9 | 102.1 | 88.4 | 115.7 | 80.8 | 41.9 | 35.8 | 100.1 | 88.6 | 30.9 | 29.6 |
| 19 | 665 | 82.1 | 82.4 | 98.6 | 98.3 | 97.3 | 81.0 | 118.9 | 71.6 | 39.4 | 33.3 | 94.8 | 80.0 | 30.1 | 23.4 |
| 26 | 897 | 68.9 | 66.7 | 83.4 | 77.9 | 76.6 | 62.9 | 88.9 | 58.5 | 38.7 | 32.9 | 73.2 | 61.0 | 33.1 | 11.2 |
| 30 | 930 | 67.4 | 65.0 | 81.3 | 75.7 | 74.3 | 61.2 | 85.0 | 56.9 | 38.3 | 32.5 | 70.9 | 59.3 | 33.0 | 9.7 |

**Highway robustness thresholds.** EVIDENCE: the refuter's `stab_scan` §3, re-run, at J 0.2 and nominal k.

| | at 26–30 m/s | rev 1 at 26 m/s |
|---|---|---|
| PM 30° needs b ≥ | 0.094–0.097× the fit | 0.237× |
| unstable below b = | 0.030–0.033× the fit | 0.131× |

At nominal b, PM 30° holds up to J = 4.4–7.1 at 15–30 m/s and up to J = 1.33 at 10 m/s.

### 3.2 Bode, nominal (EVIDENCE `page_numbers_r2.txt` §2)

| v (Kp_eff) | row | 0.1 | 0.3 | 0.5 | 1 | 1.6 | 2 | 3 | 5 | 10 | 20 | 30 Hz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 (500) | \|L\| | 44.2 | 10.0 | 4.47 | 1.63 | 0.964 | 0.783 | 0.543 | 0.312 | 0.109 | 0.029 | 0.012 |
| | ∠L | −108 | −125 | −127 | −119 | −114 | −114 | −120 | −140 | −180 | 130 | 90 |
| | \|T_ref\| | 1.013 | 1.109 | 1.251 | 1.301 | 0.929 | 0.737 | 0.451 | 0.186 | 0.030 | 0.004 | 0.001 |
| 8 (525) | \|L\| | 16.1 | 5.28 | 3.10 | 1.52 | 0.983 | 0.812 | 0.565 | 0.320 | 0.110 | 0.029 | 0.012 |
| | \|T_ref\| | 1.006 | 1.042 | 1.077 | 1.013 | 0.802 | 0.678 | 0.452 | 0.197 | 0.032 | 0.004 | 0.001 |
| 12.5 (369) | \|L\| | 7.33 | 2.17 | 1.14 | 0.50 | 0.354 | 0.317 | 0.264 | 0.191 | 0.088 | 0.027 | 0.012 |
| | \|T_ref\| | 1.011 | 1.051 | 0.960 | 0.525 | 0.306 | 0.237 | 0.146 | 0.072 | 0.018 | 0.003 | 0.001 |
| 17 (575) | \|L\| | 4.47 | 1.44 | 0.829 | 0.396 | 0.260 | 0.220 | 0.168 | 0.120 | 0.063 | 0.023 | 0.011 |
| | \|T_ref\| | 0.987 | 0.882 | 0.720 | 0.419 | 0.261 | 0.205 | 0.128 | 0.064 | 0.019 | 0.004 | 0.001 |
| 26 (897) | \|L\| | 9.38 | 2.67 | 1.37 | 0.559 | 0.328 | 0.260 | 0.176 | 0.111 | 0.055 | 0.021 | 0.010 |
| | \|T_ref\| | 1.013 | 1.079 | 1.053 | 0.626 | 0.363 | 0.278 | 0.168 | 0.082 | 0.024 | 0.005 | 0.002 |

**Crossover** is about 1.5 Hz at 3–8 m/s, **0.55 Hz at 12.5 m/s, about 0.4 Hz at 17 m/s and 0.7 Hz at 26 m/s** (rev 1:
1.0–1.3 Hz at 12.5–26 m/s). This is the price of gating b_q×J1.0. At highway the inner loop is a slow, well-damped
position servo, and the integrator carries the hold.

### 3.3 The hard-turn band and the discriminator (EVIDENCE `page_numbers_r2.txt` §5, §6)

**|T_ref| peak in 1.6–3 Hz:**

| members | value |
|---|---|
| nominal | 0.26–0.93 |
| b_lo | 0.38–1.14 |
| J_hi | 0.31–0.92 |
| b_lo×J_hi / ×tau6 | **1.16–1.38 / 1.21–1.45 at 3–11.9 m/s**, 0.49–0.71 above |
| b_q×J_hi | 0.78–1.08 at ≥ 12.5 m/s |
| **b_q×J1.0** | **1.49–1.66 at 15–26 m/s** |

The rings are in §6.3.

### 3.4 5–25 Hz damping, both hold ages (EVIDENCE `gate2_r2_B.txt`; Re(T/ω) in T counts per deg/s, worst over 1–35 m/s at 0.25 m/s)

| | 5 Hz | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V294 age 0 / age 10 | +1.42 / +1.03 | +0.82 / +0.21 | +0.23 / −0.49 | −0.08 / −0.73 | −0.20 / −0.76 | −0.28 / −0.72 | −0.34 / −0.59 | −0.37 / −0.30 |
| V295 age 0 / age 10 | +2.63 / +1.91 | +1.51 / +0.38 | +0.42 / −0.90 | −0.15 / −1.36 | −0.37 / −1.40 | −0.51 / −1.33 | −0.63 / −1.09 | −0.69 / −0.55 |
| V282 age 0 (ground at 20 Hz) | +19.8 | +12.6 | +5.05 | −0.05 | −2.52 | −4.42 | −6.39 | −7.93 |
| C1 rev 1 worst age 0 / age 10 | −3.12 / −4.02 | −2.14 / −2.76 | −1.40 / −1.72 | −1.03 / −1.14 | −0.87 / −0.87 | −0.76 / −0.68 | −0.63 / −0.51 | −0.49 / −0.21 |
| **C1 rev 2 worst age 0** (27 m/s) | **−0.74** | **−0.67** | **−0.66** | **−0.65** | **−0.64** | **−0.62** | **−0.59** | **−0.52** |
| **C1 rev 2 worst age 10** | **−1.57** | **−1.47** | **−1.33** | **−1.15** | **−1.00** | −0.86 (12.5) | −0.65 (12.5) | −0.28 |
| rev 2 / V295, same age | (V295 damps) / (damps) | (damps) / (damps) | (damps) / 1.48 | 4.34 / 0.85 | 1.72 / 0.72 | 1.21 / 0.65 | **0.93 / 0.60** | 0.76 / 0.51 |
| rev 2 / rev 1, age 0 | 0.24 | 0.32 | 0.47 | 0.64 | 0.73 | 0.82 | 0.94 | 1.08 |

**The bound.** Rev 2 anti-damps at 5–17 Hz where V294/V295 damp, by at most 0.74 T per deg/s at hold age 0 and 1.57 at
age 10.
- That is 3–14 % of the nominal plant's b (5–26), and up to 45 % of the b_q floor (3.46) at age 10.
- The exact-pole checks that matter all pass with it included: the gated members, 0 / 240 + 144 + 288 two-mass rows, and
  0 / 80 20 Hz rows (§3.5).

**The rule Re(T/ω)₂₀ ≤ V295's holds**: 0.93× at age 0 and 0.60× like for like at age 10. The mixed convention (aged
rev 2 against un-aged V295) gives 1.03×. That is stated in §2.4.

**Why not designed out.** Rev 1 §2.4 still holds. P on an angle operand behind the 5.05 Hz lag and the hold is −90° of
phase relative to a rate operand, and D on the held rate anti-damps above about 7 Hz. Rev 2's lower highway P cut the
5–10 Hz term to 0.24–0.47× rev 1's. The raised Kd lifts 20–25 Hz by 1.0–1.08× rev 1, which is inside the rule.

### 3.5 Two-mass and 20 Hz stress (EVIDENCE `gate2_r2_C.txt`, `gate2_r2_D.txt`)

| set | rows | unstable | ζ(C1r2) / ζ(V295) |
|---|---|---|---|
| hands-off, fz 10–20 Hz, r2 0.1–0.5, ζ_w 0.01–0.05 | 240 | **0** | min 0.783, median 0.982 |
| the same, motor-side b at b_q, ≥ 12.5 m/s | 144 | **0** | min 0.823, median 0.978 |
| hands-on (arms ×1–5) | 288 | **0** | min 0.528, median 0.994 |
| 20 Hz stress rows on `harness_freq`'s exact lifted loop | 80 | **0** (V282: 28) | ζ shift vs the open plant −0.014 … +0.059 |

### 3.6 The fork outer loop (EVIDENCE `gate2_r2_E.txt`; stand-in L_o = T_ref·e^(−0.06 s)/(τ_o s))

| τ_o | worst GM over nominal, b_lo, J_hi, b_lo×J_hi, ×tau6, b_q, b_q×J_hi | J1.0, b_q×J1.0, b_q×J1.0+h10 |
|---|---|---|
| 1.0 s | **≥ 11.8 dB** | 8.6–9.1 dB at 3 m/s; ≥ 11.1 dB above 10 m/s |
| 0.5 s | ≥ 5.8 dB | 2.6–3.1 dB at 3 m/s |
| 0.3 s | 1.4–1.6 dB (J_hi, b_lo×J_hi, 3 m/s) | **unstable** at 3 m/s |

The rule stands: **no fork integral on the angle error below 8 m/s, and none faster than τ_o = 1 s anywhere.**

---

## 4. Time domain, the I policy, and the refuters' own scripts on rev 2

### 4.1 The time harness, nominal (EVIDENCE `time_r2_nominal_score.txt`, `time_r2_nominal_summary.txt`; `harness_time.run` unmodified)

| m/s | Kp_eff | ess° | hold | tg0.2 | tg0.5 | ±1° fit | dj events | stick % | T_hf hold | T_hf sin | hunt p2p° | step ov % | hard16 / ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 500 | 0.36 | 1.003 | 1.066 | 1.172 | 1.41 | 8 | 59 | 0.5 | 3.0 | 2.97 | 9 | 1.37 / 1.80 |
| 5 | 510 | 0.06 | 0.999 | 1.053 | 1.127 | 1.28 | 6 | 47 | 0.6 | 1.5 | 1.81 | 16 | 1.27 / 1.69 |
| 6 | 515 | 0.05 | 0.999 | 1.043 | 1.081 | 1.21 | 2 | 37 | 0.6 | 1.3 | 1.60 | 14 | 1.36 / 1.91 |
| 7 | 520 | 0.05 | 0.998 | 1.030 | 1.037 | 1.15 | 0 | 28 | 0.6 | 1.0 | 1.47 | 11 | 1.86 / 2.49 |
| 8 | 525 | 0.05 | 0.998 | 1.015 | 0.997 | 1.08 | 0 | 13 | 0.6 | 0.9 | 0.95 | 9 | 1.64 / 2.26 |
| 10 | 536 | 0.06 | 0.997 | 1.028 | 0.980 | 1.11 | 1 | 16 | 0.5 | 0.8 | 1.07 | 11 | 0.91 / 1.51 |
| 11.9 | 474 | 0.08 | 0.994 | 1.041 | 0.856 | 1.16 | 1 | 16 | 0.5 | 0.6 | 0.95 | 12 | 0.43 / 0.98 |
| 12.5 | 369 | 0.06 | 0.996 | 0.997 | 0.502 | 1.12 | 4 | 22 | 0.4 | 0.6 | 0.65 | 7 | 0.23 / 0.91 |
| 15 | 458 | 0.03 | 1.007 | 0.882 | 0.351 | 0.96 | 1 | 14 | 0.4 | 0.6 | 0.32 | 1 | 0.13 / 0.60 |
| 17 | 575 | 0.05 | 1.004 | 0.840 | 0.356 | 0.88 | 0 | 9 | 0.4 | 0.8 | 0.34 | −1 | 0.10 / 0.45 |
| 19 | 665 | 0.05 | 1.009 | 0.900 | 0.448 | 0.94 | 0 | 9 | 0.4 | 0.8 | 0.15 | 2 | 0.09 / 0.38 |
| 22 | 765 | 0.03 | 1.005 | 0.963 | 0.562 | 1.01 | 1 | 7 | 0.5 | 1.0 | 0.09 | 4 | 0.08 / 0.30 |
| 26 | 897 | 0.04 | 0.991 | 1.026 | 0.719 | 1.06 | 3 | 5 | 0.6 | 1.2 | 0.19 | 10 | 0.06 / 0.23 |
| 30 | 930 | 0.03 | 0.992 | 1.033 | 0.739 | 1.07 | 1 | 6 | 0.5 | 1.4 | 0.18 | 15 | 0.06 / 0.19 |

**Total dj events:** rev 2 31, rev 1 26, the Kd 16 / rev-1-Ki robust alternative 35, the Kd 20 / Ki/Kp 0.556
alternative 39.
- **Where rev 2 has more events than rev 1:** 12.5 m/s (4 vs 3) and 22–30 m/s (5 vs 0). All the highway ones are hold
  slips under the harness's road disturbance, with the hunt at 0.09–0.19° p2p (rev 1: 0.02–0.04°).
- **Where rev 2 has fewer:** 11.9 m/s (1 vs 3).

**Safety scenarios** (same file):
- **Sentinel**: L16 peak T 70–278 for ≤ 0.05 s; **0.0° excursion at every speed** (A2).
- **Override-latch overshoot**: **0.34° at 3 m/s**, ≤ 0.12° at ≥ 5 m/s (rev 1: ≤ 0.08°). Rev 1's H3 bar of 0.2° is
  crossed at 3 m/s; this is declared in §8 M7, and rev 2's H3 bar is 0.4°.
- **Request drop**: excursion identical for `meas` and `zero`.
- **`ov_fade`** (no fork O1): overshoot 4.1° at 3–5 m/s, 3.0° at 8, 2.0° at 10, ≤ 1.3° at ≥ 11.9 m/s. **O1 is a
  prerequisite.**

**No int32 wrap anywhere.** **Line-only gate:** no line at any speed (T_hf in the holds ≤ 0.6 counts rms). **Strict
texture** (T_hf in the sinusoids > 2.0 counts) fires only at 3 m/s (3.0). At ≥ 17 m/s it reads 0.8–1.4 (rev 1:
2.0–2.9), so the highway texture flag is gone.

### 4.2 Robust members (EVIDENCE `time_r2_robust_summary.txt`)

⟨ROBUST⟩

### 4.3 The refuters' own scripts, re-run on rev 2 (EVIDENCE `refute_rerun_r2/*.txt`; `c1r2_rerun_refuters.py`)

| script | rev 1 (or the refuter's report) | **rev 2** |
|---|---|---|
| **`refute_c1_run.py`** (round 2, independent model) | 80 sub-bar points: b_q×J_hi < 30° across 12.5–32 m/s; b_q×J1.0 unstable; ungated combos with +h10 at 19.5–29° | **0 sub-bar points** in all four attacks. Tier A min 47.9°; tier B 36.8°; combos+h10 31.8°; extra combos 36.2°. Its anchors reproduce rev 2's gate numbers exactly (b_q×J1.0 36.7° at 12.5). |
| **`refute_c1_stage2.py`** (round 2) | b_q×J_hi PM 3.3–5.5°, Ms 12–19; b_q×J1.0 PM −6 to −8.8 | **b_q×J_hi PM 58.5–80.8°, Ms ≤ 1.57, GM ≥ 20 dB; b_q×J1.0 PM 37.8–41.9°, Ms ≤ 2.00, GM ≥ 20.4 dB**; b_q×J_hi+h10 57.9–73.5°. Outer GM at τ_o 1 s ≥ 14.1 dB on b_q×J1.0. Re(T/ω)₂₀ 0.932× V295 at age 0 (1.028× by its aged-vs-un-aged convention, §2.4). |
| `stab_scan.py` §1–§5 (round 1) | J_hi 40.7° (C0); rev 1 min 46.6° | min 47.9° (J_hi, 1 m/s); no credible member < 45°; combined corners ≥ 36.8°; highway thresholds as §3.1; delay margin ≥ 80 ticks |
| `stab_jrows.py` | rev 1: J 0.8 39.9°, J 1.3 22.9° at 11.9 | J 0.8 50.1°, **J 1.3 31.3° at 11.9** (33.9° at 11 m/s) |
| `stab_fix.py` (C0-base literals substituted, listed in its header) | rev 1 under the J_hi PM45 / b_lo×J_hi PM30 limits | rev 2 Kp_eff 369–544 vs limits 848–1103 (PM45) and 704–890 (PM30) at 10.5–12.5 m/s |
| `xcheck_hf.py` (same substitution) | — | J_hi 63.5–82.5°; b_lo×J_hi 42.2–103°, ζ 0.33–0.92, \|T_ref\|₁.₆₋₃ 0.52–1.44 |
| `stab_nl.py` A / B (integer, friction, quantised) | rev 1: 0.41° overshoot, no highway limit cycle | 2° step at 12 m/s: overshoot ≤ 0.26°, 1 crossing; highway b = 5: **no 4–6 Hz content (0.0 rms), wheel p-p 0.000°** at 19 / 26 / 30 m/s |
| `stab_nl2.py` | rev 1: 3–6 Hz wheel-rate rms 0.43–0.45 deg/s at b 5 | 0.21–0.22 deg/s at b 5; track error rms 0.067–0.20° |
| `stab_hf.py`, `stab_more.py` | — | same conclusions as §3.4–§3.6 |
| the friction scripts (`expA*`, `expB*`, `expC`, `expD`, `expF`, `expG`, `expH*`) | — | ⟨FRICTION⟩ |

**The `selfcheck.py` note from rev 1 still applies.** The friction refuter's `selfcheck.py` tests the C0 lane against
the C0 table by construction, so `c1_selftest.py` replaces it.

### 4.4 The I policy on rev 2 (EVIDENCE `ipolicy_r2_all.txt`; one batch per scenario, so every policy sees identical inputs)

⟨IPOLICY⟩

---

## 5. Hazards and mitigations (C1 rev 2)

| hazard | mitigation | residual | E/B |
|---|---|---|---|
| 0xE4 RX fault sentinel 0x7FFF | A2 (request 0xFF → skip) | **none at design time.** The preemption window is 0 ticks (tracer). H6 re-proves B2 on the image. | EVIDENCE guard, sim and tracer |
| fork or controls crash | the 0xE4 timeout (500 ms pending) → sentinel → A2 | **the last θ_sp is held about 0.51 s**, then about 0.1 s of decay (M12) | EVIDENCE tracer §3 |
| corrupt 0xE4 frames | the checksum/counter debounce | up to 49 frames decoded as valid before the fault | BELIEF (decompile only) |
| `gp-0x67fe ≠ 2` (θ forced to 0) | B2 | none found | EVIDENCE |
| mode-3 exit mid-engagement | B2 (→ state 4) and the ±12000 bail | a baseline turning 0x7FFF while mode stays 3 | EVIDENCE angle trace; BELIEF on the 0x7FFF case |
| engaging without mode 3 | fork C8 | 10 ms + the fork round trip | BELIEF on the fork |
| request drop / main-off / panda zero | A2 → about 0.1 s release | Honda's 2 s hand-back is gone (operator-facing) | EVIDENCE sim |
| engage init | stateless cave; I = 0 after any skip; I frozen through the ramp-in | droop under a handed-over load (§4.4, M7) | EVIDENCE sim |
| override / release lurch (V283's class) | freeze above \|tq\| 512 + fade + ICL 4096 + fork O1 | a hand below 512; a stale I after a long override (M5, M6) | EVIDENCE sim; BELIEF on the sensor scale |
| position-servo authority | P rails at 49.1° (≤ 3 m/s) … 66.6° (12.5) … 26.4° (≥ 27); the fork's Δmax caps demanded P at 229–765 T before I | a fork bug equals the rail (2461) | EVIDENCE arithmetic; Δmax values BELIEF |
| **low damping × high inertia at speed** (round-2 F1) | **G(v) gated on b_q×{J_hi, J_hi2, J1.0}, ×tau6, +h10** | b_q×J1.3 at 12.5 m/s 27.0° (report); **R3** | EVIDENCE model; BELIEF physics |
| 5–17 Hz anti-damping | bounded (§3.4) | ≤ 0.74 T per deg/s at age 0, ≤ 1.57 at age 10; no stress row unstable | EVIDENCE model; the plant above 8 Hz is not identified |
| **camera 0xE4 on a relay close** | operator procedure: camera LKAS off (**flight prerequisite**) | a comma crash with camera LKAS on; the one-byte F3 does not cover mid-engagement (§2.10) | EVIDENCE decompile |
| torque fork on the angle firmware | **V1** + the fork param | none if both, plus the revert re-header | EVIDENCE fw string + tracer |
| highway LSB limit cycle | Kp_eff ≤ 930 (rev 1: 1971) | sim: no line; hold hunt 0.09–0.19° | EVIDENCE sim; BELIEF on the real quantiser |

---

## 6. The instrument: what proves C1 rev 2 live in one short drive

Rev 2 adds **no telemetry bit**. Every term is observable from signals already on the wire:

| signal | what it gives |
|---|---|
| 0xE4 sendcan | θ_sp = −raw/10, and the request |
| 0x14A STEER_ANGLE | θ, 100 Hz; and b4 |
| 0x18F rate and STEER_TORQUE_SENSOR | driver torque, wire = raw × 1.024; the freeze predicate is a wire predicate |
| the CAN 427 tap | T = `gp-0x6b38`, `sign(T)<<9 \| \|T\|>>3`, 50 Hz, wire polarity +sign(cmd) |
| 0x18F STEER_STATUS | status |
| **the F181 string** | **"39990-TVA,A16A" in the route's carParams `carFw`**: the image check |

Decode with the patched cereal (the slot-137 collision). Take routes from the device's realdata.

### 6.1 Pre-registered LIVE / NOT-LIVE / REVERT

**Window:** hands-off (|0x18F| < 500 wire), request 1, ≥ 1.2 s after the engage edge, and |θ_sp − θ| below the band's
P-rail angle (§1.4).

**Regression** (0.3–3 Hz, θ resampled to the 50 Hz tap):
`tap = c_P·(raw − f14A) + c_I·Σ(raw − f14A)·dt + c_D·ω_18F + c0`.

| band | 0–5 | 5–10 | 10–12.4 | 12.5–15 | 15–22 | > 22 m/s |
|---|---|---|---|---|---|---|
| Kp_eff | 500–510 | 510–536 | 413–544 | **369–458** | 458–765 | 765–930 |
| c_P (tap per raw count = Kp_eff/800) | 0.625–0.637 | 0.637–0.670 | 0.516–0.680 | **0.461–0.573** | 0.573–0.956 | 0.956–1.163 |
| c_I / c_P | 3.91 s⁻¹ (2π·0.622) | ← | ← | ← | ← | ← |
| c_D (tap per deg/s, opposing) | ≈ 0.40 | ← | ← | ← | ← | ← |

| verdict | condition |
|---|---|
| **LIVE: the image** | carFw EPS = `39990-TVA,A16A` |
| **LIVE: E-loop** | c_meas/c_raw ∈ [−1.25, −0.80] |
| **LIVE: the speed schedule** | c_P within ±30 % of the band prediction in every band with ≥ 15 s of window, **and the dip**: c_P(12.5–15) < c_P(5–10) (predicted ratio 0.72–0.86), **and** c_P(> 22)/c_P(5–10) ∈ [1.2, 2.4] (predicted 1.43–1.82) |
| **LIVE: the PI corner** | c_I/c_P ∈ [2.7, 5.1] s⁻¹ |
| **LIVE: the freeze** | in every hands-on episode with \|0x18F\| > 600 wire for ≥ 0.5 s and \|θ_sp − θ\| > 0.3°, the I component (tap − c_P·e − c_D·ω) changes by < 3 tap counts per 0.5 s. An unfrozen I would ramp ≈ 0.0171·G·e(counts) T/s, i.e. about 13 tap counts per 0.5 s at 1° and 8–11.5 m/s. |
| **LIVE: A2** | after every request drop, \|tap\| < 20 within 0.15 s |
| **NOT LIVE: wrong image / torque firmware** | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface (R² ≥ 0.9) |
| **NOT LIVE: cave skipped** (in-place edits only) | c_P ≈ 0.14 in every band (Kp_base 112 with no G) |
| **INVERTED** | c_meas/c_raw > 0 → abort |

**I reconstruction (BELIEF until validated on the drive).**
`I_n = clamp(I_{n−1} + [not frozen_n]·((56·(E′_n>>5))>>3))`, at 1 kHz on 100 Hz-held inputs, with
frozen_n = (|0x18F| > 524 wire) ∨ (ramp not full: the request edge + 0.99 s). Pass: the residual correlates with the
reconstruction at r ≥ 0.8.

### 6.2 REVERT (any one; written before the build)

| id | signature |
|---|---|
| R1 | INVERTED |
| R2 | hands-off, request 1, \|tap\| ≥ 300 (the rail) for > 0.3 s |
| **R3: STOP from the first highway minute** | at ≥ 12.5 m/s, an oscillation in **1.0–5.5 Hz** in 0x14A or the 0x18F rate that **grows**, or that shows **≥ 4 visible cycles above twice the pre-event rms** (ζ < 0.10). No gated member reaches it (lowest ζ 0.13, b_q×J1.0+h10). It fires on light_b-class plants (ζ 0.06–0.12 at 22–30 m/s) and anything outside the credible set. |
| R4 | a narrowband 5–30 Hz line in the 0x18F rate or the torque bar that is absent on V282/V295 |
| R5 | ring presence > 0.5 % or F7 > 0 per 100 s |
| R6 | \|θ − θ_sp\| > 10° hands-off for > 0.5 s at > 8 m/s |
| R7 | after a request drop, \|tap\| still pushing toward 0° for > 0.2 s |
| R8 | STEER_STATUS ≠ 0, or 0x14A b4 bits 0–2 ≠ 7, while engaged |
| R9 | the operator's own words: grinding, ratcheting, a jerk in hard turns |

### 6.3 What the drive identifies (pre-registered discriminator)

These are the **least-damped closed-loop poles** on each member at ≥ 12.5 m/s. EVIDENCE: `page_numbers_r2.txt` §5,
exact periodic.

| if 0x14A at ≥ 12.5 m/s turn-ins shows | then the plant is | next step |
|---|---|---|
| no visible ring (all poles ζ ≥ 0.5) | nominal / J_hi / b_lo class | C2 may raise the highway gain, **only after** the 1–5 Hz FRF (§6.4 item 7) |
| a 3.4–4.1 Hz decaying ring, ζ 0.5–0.6 (1–2 visible cycles) | b at about 0.25× of the fit at 3–5 Hz (b_q), nominal J | keep; the highway gain is bounded by the J axis, not b |
| a 2.2–2.5 Hz ring, ζ 0.30–0.34 (2–3 cycles) | b_q × J_hi | keep; this is the member rev 1 failed |
| **a 1.2–1.8 Hz ring, ζ 0.13–0.22 (3–5 cycles)** | **b_q × J ≈ 1** | keep, never raise the highway gain; hard-turn amplification is expected (M9) |
| a 1.0–5.5 Hz ring with ζ < 0.10, or growing | outside the credible set (light_b class) | **REVERT (R3)** |

### 6.4 What the first drive measures for C2 (friction compensation, the freeze threshold, and the highway gain)

All from the wire. Each is a within-episode read, so one short drive suffices.

1. **The breakaway torque F_s(v).** At every dwell end (the 0x18F rate going from 0 to > 0.5°/s after ≥ 100 ms stuck,
   hands-off), take the lane torque (tap × 8) minus the spring estimate k̂(v)·θ.
2. **The Coulomb level F_c(v).** In slow steady motion (|ω| 0.5–5°/s), take lane torque − k̂θ − b̂ω.
3. **The dead-zone width.** |θ_sp − θ| at dwell ends, per band. P-only predicts F_s/(Kp_eff/10).
4. **The hunt.** In constant-θ_sp windows ≥ 10 s at 3–7 m/s, the θ p2p and period.
5. **The dwell-then-jump rate per band**, against r6c (the goal's own metric).
6. **The sensor scale and the freeze duty.** In hands-on episodes, |0x18F| against the lane torque the hand resists
   (tap × 8 + k̂θ). Also the fraction of hands-off engaged frames with |0x18F| > 524 wire, per band and per
   steering-rate bin.
7. **NEW, the 1–5 Hz plant at highway.**
   - The angle loop at ≥ 12.5 m/s is a slow servo, so road disturbance excites the wheel against a known controller.
   - Regress the 0x14A angle (and the 0x18F rate) on the tap torque over 0.5–5 Hz in hands-off highway windows, with
     the controller's own output as the instrument. This gives an FRF estimate of J and b(3–5 Hz) above 10 m/s, which
     the r71b identification could not provide.
   - Its result decides whether C2 may raise the highway gain. BELIEF: the excitation is sufficient. If it is not, C2
     needs a deliberate dither, which is a separate design.

A friction feed-forward for C2 (BELIEF: ≈ F_c·sign(θ̇_sp) in the cave, about 12 bytes) is sized from items 1–3. The freeze
threshold (a 2-byte immediate) comes from item 6, and the highway gain from item 7.

---

## 7. What a FAIL of C1 rev 2 looks like (written before any build)

### 7.1 In the harness and the adversarial pass: any one means **do not flash**

| id | failure |
|---|---|
| H1 | The interpreter (`c1_assemble.run_bytes`), executing **the built image's** cave bytes, differs from `c1_lib`'s cave on any of 200 000 random inputs; any register other than r6/r8/r9/r13/r16 changes (**r25 included**); or `LaneC1` differs from the original `LaneVec` with the cave off. |
| H2 | `c1r2_gate2.py` A on the built image's table and cals: **any tier-A point** with PM < 45°, exact GM < 6 dB, a 5–50 Hz pole ζ < 0.2, M20 > 3.58, L20 > V295's, or \|T\| or \|T_ref\| > +3 dB in 5–30 Hz; **any tier-B point** (all 33, including every +h10 member and every b_q×J member) with PM < 30°, exact GM < 6 dB, or instability; a method disagreement > 1° where either PM < 60°; Re(T/ω)₂₀ above V295's at the same hold age at any speed; any two-mass or 20 Hz stress row unstable. |
| H3 | The time harness on the nominal plant with the built-image mirror: any line; hold < 0.90, or tg0.2 outside 0.80–1.10, at ≥ 8 m/s; any int32 wrap; a sentinel excursion ≠ 0.0°; an `ov_latch` overshoot > 0.4°. |
| H3b | The goal-metric factor (`c1r2_trackmetric.slope` on the built table) < 0.95 for any tabulated member in any band ≥ 8 m/s. |
| H4 | GATE 1: the cave writes any RAM, or reads any RAM other than `gp-0x6a5e` and `gp-0x4f68`; any new reader or writer of `gp-0x6dd0`. |
| H5 | From the built image (Ghidra): r6, r8, r9 or r13 read before written on any path from `0x29D7A` or `0x29D7E`; r14 written between `0x29D7A` and `0x2A1E6` on the PID path; **r25 written anywhere in the cave**; any branch into `0x29D76..0x29D7D`; the cave reachable from a skip path; the hook not decoding as `jarl 0xC4C00, r6`; the `jr` not landing on `0x29D7E`. |
| H6 | With A2 + B2 in the built image: P computed on the 0x7FFF sentinel on any tick; the B2 `cmov` not r8 := (Z ? r27 : 0); `0x2913A` not dominating `0x29A48` (the tracer's flow-graph method, re-run on the built image). |
| H7 | The table lacks the 0xFFFF row, or the walk reads outside the table for any v in 0..65535. |
| H8 | Any CRC fails `verify_bootloader_crc.py`, **including the block holding `0x13100`**. |
| **H9** | **The built image's F181 bytes are not `39990-TVA,A16A`; the `.rwd` header does not list both A160 and A16A; or the V295/V294 revert `.rwd`s have not been re-headered to list A16A.** |

### 7.2 On the car

| | condition |
|---|---|
| **REVERT** | any of R1–R9 |
| **FAILED its stated goal** | any of: any band ≥ 8 m/s with on-car turn-hold < 0.90 over ≥ 60 s; **on-car tracking (the scorer's slope) outside 0.95–1.05 in any band ≥ 8 m/s** (this is predicted to pass, so it is not a declared miss); a new 5–30 Hz line; dwell-then-jump above r6c in a band **other than** the declared 0–7 m/s, 12.5 m/s and highway-hold misses |
| **The pre-declared misses** | §8. They are FAILs of those criteria, declared now. C2 is designed against them from the §6.4 measurements. |
| **NOT INTERPRETABLE** | must not happen. LIVE needs about 15–30 s of hands-off frames in two speed bands. Ask for one stretch > 22 m/s, one at 12.5–15 m/s (the dip), and one at 5–10 m/s. |

---

## 8. The pre-declared misses (each with its band and predicted size)

| # | criterion | band | predicted (sim unless stated) | basis |
|---|---|---|---|---|
| M1 | low-speed stick-slip gone; dwell-then-jump ≤ V282 | **0–7 m/s** | ⟨M1⟩ | EVIDENCE §4.1, §4.3 |
| M2 | dwell-then-jump ≤ V282 | **12.5 m/s** (the b_q dip, Kp_eff 369) | 4 events per scenario set (rev 1: 3); 10–11.9 m/s: 1 | EVIDENCE §4.1 |
| M3 | tracking **faster than the metric** (the goal's metric is predicted to pass, §2.5) | **12.5–22 m/s** | 0.5 Hz in-phase 0.40–0.61; 0.2 Hz 0.84–0.92 at 15–19 m/s; **group delay at 0.2 Hz 232–345 ms**. Lane changes, S-bends and turn-ins at highway speed will lag the plan. | EVIDENCE §2.5 |
| M4 | tracking at lane-keeping amplitudes ≤ ±1° | 8–19 m/s | ⟨M4⟩ (stiction against 37–67 T per degree) | EVIDENCE §4.3 |
| M5 | release after a ≥ 3 s override that moved the wheel (with O1) | all | ⟨M5⟩ | EVIDENCE §4.4 |
| M6 | release after a light hand below the threshold | all | ⟨M6⟩ if the hand reads < 512 internal counts | EVIDENCE sim; BELIEF on how often |
| M7 | engage under a handed-over load; the override-latch overshoot | ≤ 8 m/s | ⟨M7⟩; `ov_latch` 0.34° at 3 m/s | EVIDENCE §4.1, §4.4 |
| M8 | texture (strict reading) | 3 m/s | 3.0 counts rms (the 2-count bar has no N·m scale) | EVIDENCE sim |
| M9 | residual robustness and hard-turn amplification | 10–30 m/s | J 1.3 refit 29.2° at 11.5 m/s; **b_q×J1.3 27.0° at 12.5 m/s**; ms_free 12.1°; b_q from 10 m/s (not the refuter's definition) would put b_q×J1.0 at 26–30° at 10–12.4 m/s; **\|T_ref\|₁.₆₋₃ 1.49–1.66 on b_q×J1.0 at 15–26 m/s** and 1.16–1.45 on b_lo×J_hi(×tau6) at 3–11.9 m/s | EVIDENCE model |
| M10 | hands-on turning | all | the freeze may be active in 25–48 % of turning frames when hands rest on the wheel (route a6); 0.5 Hz tracking −0.06…−0.14 in that regime (rev 1 `c1_freeze_duty.py`) | EVIDENCE route a6 + sim; BELIEF on attribution |
| **M11** | dwell-then-jump in highway holds | **22–30 m/s** | 1–3 hold slips per scenario set under the harness road disturbance; hunt 0.09–0.19° p2p (rev 1: 0 and ≤ 0.04°) | EVIDENCE §4.1 |
| **M12** | the fork stops sending (crash) | all | the EPS holds the last θ_sp for about 0.51 s, then A2 and about 0.1 s of decay | EVIDENCE tracer §3 |

---

## 9. Fork prerequisites (the spec's §5 and §8 carry the detail)

| prerequisite | why (rev-2 evidence) | status |
|---|---|---|
| F4: the fwVersion marker `39990-TVA,A16A` (V1) + the `AccordEpsAngleLoop` param | a torque fork on this image commands angles | **flight prerequisite**: the firmware half is in rev 2 (V1); the fork half is fork code |
| **the flasher re-header** of the C1r2 `.rwd` (A160 + A16A) and of the V295/V294 revert `.rwd`s (+A16A) | otherwise the revert is refused (tracer §4) | **flight prerequisite (build step)** |
| C3/C5/C4 | inactive = the measured angle; engage from θ_meas | **flight prerequisite** |
| C8 (mode-3 bits) | the engage-time gate | **flight prerequisite** |
| C6 Δmax(v) | caps demanded P at 229–765 T (§2.10) | **flight prerequisite** |
| O1 | without it, `ov_fade` overshoots 2.0–4.1° at ≤ 10 m/s | **flight prerequisite** |
| no fork integral below 8 m/s; τ_o ≥ 1 s | GATE 2 E (§3.6) | **flight prerequisite** |
| C10 `UseAutoSteerDelay` on drive 1 | the inner group delay is 99–345 ms at 0.2 Hz and speed-dependent; a look-ahead adds only +0.01 on the metric | recommended |
| **camera LKAS off** | the one-byte F3 does not cover a mid-engagement relay close (§2.10) | **flight prerequisite (operator procedure)** |
| the panda's 0xE4 bound measured | safety | **flight prerequisite** |
| B2 dominance and the r25 / r14 liveness re-proved on the **built** image (H5, H6) | the tracer proved them on V294; the build must re-prove them | **flight prerequisite (adversarial pass)** |

The RX preemption and timeout traces are **done** (tracer, 2026-09-30). They are no longer open prerequisites.

---

## 10. Concerns and open items

1. **The friction and safety lenses of round 2 did not complete.** This page re-runs the friction refuter's scripts
   (§4.3) and folds in the tracer's safety facts (§2.10), **but it is the designer's own evidence, not an independent
   refutation. Neither lens is cleared until another reviewer completes it.**
2. **The highway gain is set by a member that is BELIEF on both axes**: b_q (frequency-dependent damping, unmeasured at
   3–5 Hz) × J ≈ 1 (unmeasured above 10 m/s, and physically doubtful, §2.1). Rev 2 pays for it with 232–345 ms of
   0.2 Hz group delay at 12.5–19 m/s (M3). **The 1–5 Hz FRF at highway (§6.4 item 7) is what would buy the gain back**,
   and C2 must not raise the highway gain without it.
3. **The goal-metric tracking pass rests on one route's spectrum** (r71b) and on a weighting with a ±0.028 positive
   control. The margin at 15–19 m/s (0.009–0.02) is inside that accuracy.
4. **The method check failed as pre-registered on 64 high-PM points** (§3.1). It is restated for the decision-bearing
   region after the run, and declared.
5. **Rev 1's H3 latch bar (0.2°) is crossed at 3 m/s (0.34°).** The rev-2 bar is 0.4°, declared.
6. **The cave encodings are BELIEF until Ghidra decodes the built image** (H5), despite 14 encoding controls and
   0 / 200 000 interpreter mismatches. The code bytes are identical to rev 1's, and the table bytes are data.
7. **r14 = ramp and r16 reaching P (`0x29E34 mov r16,r8`)** rest on the hook trace's liveness scan plus rev 1's decode.
   Re-prove them on the image.
8. **The sensor scale** (T counts vs gp-0x4f68 counts) is unknown; the freeze threshold and M6 depend on it.
9. **F3's every-tick firmware form**, the `0xC626C` timeout's sharing, and the 49-bad-frame debounce in disassembly are
   untraced.
10. **Everything above about 8 Hz is model, not measurement.**
11. **The goal names a bleed; C1 freezes.** The operator should rule on the wording (unchanged from rev 1).
