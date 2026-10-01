# DESIGN PANEL, designer D-structure (2026-10-01): which LOOP STRUCTURE for the 1 kHz angle loop

**Status: DESIGN ONLY.** Nothing was built, flashed or sent. No image or `.rwd` was written; every patched image in this
study exists only in memory inside `ds_bytes.py`. The fork was not touched. Ghidra was used read-only (`decompile_function`,
`disassemble_bytes` with `dry_run: true`, `get_function_*`) on stock `code.bin` and the V294 program (code-identical to
V295 except cal `0xC63EA` and its CRC); nothing was saved.

**Author:** panel designer D-structure (Opus subagent) for the orchestrator `main`. My angle: **a different loop
STRUCTURE**, not another gain set on the C1 structure. Four other designers work the same problem from other angles; I have
not seen their work. **I do not pick a winner.** Every implementation below is scored the same way; the judges pick.

**Base image:** V295 `_v295_V295-V294BASE-ACCELTRIM.B1050-…_plain_image.bin`, sha256 `5c044d6576314052…52ed`
(asserted by every script). Every pre-edit byte quoted here was re-read from it in Python (`ds_bytes.py` asserts each one).

**Scripts** (all under `analysis-2020accord/studies/angle_loop/panel/D-structure/`, fixed seeds, `python <script>`):

| script | what it does | output |
|---|---|---|
| `ds_model.py` | ONE linear model of every structure, built two ways: the analytic LTI fundamental (hold = mean z⁻ᵃ) and the EXACT periodic 1 kHz model (affine rows per tick, slot 4 after the lane, lifted 10-tick monodromy, exact GM, and the exact same-frequency harmonic) | self-check in `__main__` |
| `ds_gate2.py` | the credible set (the brief's), the bars, the speed-gain envelope (PM/GM on every gated member + the 20 Hz rules), the integer table fit (LP, ≥ 4 % under), the full-grid gate | used by `ds_final.py` |
| `ds_lane.py` | the integer-exact lane for every structure (one numpy column per implementation) | used by `ds_time.py` |
| `ds_time.py` | the 1 kHz time harness: harness_time's plant, scenarios and metrics unchanged, plus the sensors the structures need (the integer EMA mirror of `gp-0x6abe`, the 1 kHz accumulator `gp-0x6cc4`), Honda's oscillation-detector mirror, a light-hand override and an engage-under-load scenario | `_scratch/…/time_final.json` |
| `ds_final.py` | the candidates (one source of truth) and the pipeline `env / fit / gate / retw / track / time` | `final_*.txt`, `_scratch/…/*.json` |
| `ds_asm.py` | every cave as a listing → bytes (two-pass), 27 encoding-form controls against the V295 image, and H1: the assembled bytes EXECUTED by a V850 interpreter against the lane's cave arithmetic on 60 000 random inputs per cave | `ds_asm_out.txt`, `ds_cave_<id>.hex` |
| `ds_bytes.py` | every byte each candidate changes, applied in memory to V295, a full diff over `[0x13000, 0x100000)` that must contain exactly the listed bytes | `ds_bytes_out.txt` |
| `ds_gate1.py` | GATE 1 census of the cave RAM words and the cells the caves read (4-byte and 6-byte gp forms, Format VIII, LE32 literals), positive-controlled | `ds_gate1_out.txt` |
| `ds_selftest.py` | CHECK 1 lane vs `c1_lib.LaneC1F` · CHECK 2 integer lane vs linear model, every structure · CHECK 3 model vs the refuter's `stab_lin` | `ds_selftest_out.txt` |
| `ds_explore.py`, `ds_explore2.py` | rounds 1 and 2: every structure × parameters, the envelope and its 20 Hz cost, before any table was fitted | `ds_explore_out.txt`, `ds_explore2_out.txt` |
| `ds_hold_diff.py` | D1's first question in arithmetic: is a 1-tick difference of a 100 Hz-held angle useless? | `ds_hold_diff_out.txt` |
| `ds_d3_tune.py` | can the cascade meet the goal's tracking metric at any (Kp, Ki)? | `ds_d3_tune_out.txt` |
| `ds_report.py` | every table on this page that carries numbers, generated from the result files | `ds_report_out.md` |

Every decision-bearing claim is marked **EVIDENCE** (with the method) or **BELIEF**. Code is cited by address or grep string.

---

## 0. The answer in one page

### 0.1 What I evaluated

Three structures, eight implementations, and the C1r2 structure as the baseline (B0 with the C1 lib table as published,
B0r refitted to the brief's credible set exactly as I fit every candidate). All share C1's skeleton where they can: the
seven in-place edits, the cave hook at `0x29D76`, the G(v) speed table, the I freeze, and V1.

| id | structure (what differs from B0) | where the edit lands |
|---|---|---|
| **B0** / **B0r** | C1r2: P + I on angle error, **D on the HELD rate** (E5) | baseline |
| **D1a** | **D from the angle operand's own 1-tick difference, cal-only**: no E5, Honda's stock D on the error `Kd·(E′[n] − E′[n−1])>>3` | Kd record + DCL only |
| **D1b** | D from the **fresh 1 kHz motor-position accumulator** `gp-0x6cc4` difference (32× finer than 0.1°, no hold) | cave → r26 → `0x29EE0 mov r26,r8` |
| **D1c** | D from the **held-angle difference spread over ~8 ticks** (a 21 Hz low-pass in the cave, one RAM word): the "10-tick-aware" difference | cave + RAM `gp-0x6c44` |
| **D2a** | D on the **fresh 1 kHz motor-rate EMA** `gp-0x6abe` (the same signal `gp-0x6a56` holds at 100 Hz), with Honda's own validity test | cave → r26 |
| **D2b** | D2a + an **output-lag lead in the FORWARD path** (on E′ for P only; zero 5.2 Hz cancels the 5.05 Hz output-lag pole, new pole 10.3 Hz) | cave + RAM `gp-0x6c40` |
| **D2c** | D2a + the **same lead in the FEEDBACK path** (on r26, so P and I) | cave + RAM `gp-0x6c40` |
| **D3a** | **cascade**: the V282-style rate loop INSIDE (held `gp-0x6a56`, fb filter 923/1560 with its 16.5 Hz pole, Kp 24, Ki 12), the angle error OUTSIDE forming its rate setpoint in the cave | cave at the hook |
| **D3b** | cascade with a **FRESH inner operand** (`0x28F4C` → `ld.h -0x6abe[gp],r7`), Kp 46, Ki 12 | cave + one displacement |

### 0.2 Scoreboard (every number from a script; the full tables are in §6)

| id | bytes (in-place + cave + cal) / RAM | GATE 2 fails (brief's set, 4 760 pts) | T per deg at 3.1 / 11.75 / 17 / 26.9 m/s (B0r = 52 / 24 / 57 / 90) | Re(T/w)20 age 0 / 10 (V295 −0.82 / −0.89) | goal metric worst ≥ 8 m/s (bar 0.95) | dj 3–5 m/s n / bc | lurch firm / light-400 deg | texture 5–30 / 40–200 Hz | own-terms verdict |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 23 + 96+48 + 24 = **191** / none | **13** (ms_free PM45 ×12, ms_free+h10) | 41 / 31 / 56 / 89 | -0.69 / -0.51 | 0.957 (17 m/s) | 7 / 8 | 4.61 / 5.4 | 0.6 / 0.63 | fails the brief's ms_free corner |
| B0r | 23 + 96+48 + 24 = **191** / none | 0 | 52 / 24 / 57 / 90 | -0.69 / -0.52 | 0.958 (17 m/s) | 7 / 7 | 4 / 5.88 | 0.66 / 0.78 | baseline: passes; misses as C1r2 class |
| D1a | 17 + 96+48 + 24 = **185** / none | 0 | 58 / 17 / 57 / 58 | -0.79 / -0.80 | 0.944 (11.9 m/s) | 4 / 4 | 9.6 / 10.55 | 2.53 / 26.76 | **fails** texture, goal 11.9 m/s, releases |
| D1b | 20 + 112+48 + 24 = **204** / gp-0x6c44 | 0 | 53 / 24 / 60 / 94 | -0.17 / -0.03 | 0.962 (17 m/s) | 5 / 9 | 4.18 / 6.3 | 0.64 / 0.78 | passes; best 5–25 Hz damping |
| D1c | 20 + 140+48 + 24 = **232** / gp-0x6c44 | 0 | 51 / 24 / 55 / 89 | -0.65 / -0.20 | 0.956 (17 m/s) | 4 / 4 | 4.19 / 6.16 | 5.4 / 4.21 | **fails** texture; dominated by D1b |
| D2a | 20 + 114+48 + 24 = **206** / none | 0 | 52 / 23 / 60 / 93 | -0.34 / -0.20 | 0.961 (17 m/s) | 6 / 7 | 4.12 / 6.29 | 0.67 / 0.76 | passes; ½ B0r's 20 Hz anti-damping, no RAM |
| D2b | 20 + 154+48 + 24 = **246** / gp-0x6c40 | 0 | 66 / 25 / 67 / 108 | -0.52 / -0.20 | 0.967 (17 m/s) | 4 / 4 | 3.2 / 6.16 | 1.02 / 1.83 | passes; highest stiffness of the angle kind, best tracking and releases |
| D2c | 20 + 150+48 + 24 = **242** / gp-0x6c40 | 0 | 62 / 25 / 63 / 103 | -0.50 / -0.20 | 0.962 (17 m/s) | 4 / 4 | 3.14 / 5.66 | 0.98 / 1.34 | passes; as D2b without the setpoint kick, −4–7 % stiffness |
| D3a | 15 + 118+48 + 18 = **199** / none | 0 | 37 / 20 / 46 / 82 | -0.59 / +0.02 | 0.913 (11.9 m/s) | 8 / 8 | 2.81 / 4.58 | 0.48 / 0.52 | **fails** goal metric 0.913; thinnest GM |
| D3b | 16 + 118+48 + 18 = **200** / none | 0 | 61 / 33 / 67 / 113 | -0.73 / -0.55 | 0.894 (15 m/s) | 4 / 6 | 2.53 / 4.6 | 0.89 / 0.82 | **fails** goal metric 0.894; highest 10–13 m/s stiffness |

Rows: B0 = the C1 lib table scored as published; B0r = the C1r2 structure refitted exactly as every candidate. Time-domain columns are nominal unless 'n / bc'. Byte totals are WRITTEN bytes (changed in-place code incl. V1, the whole cave incl. its table, changed cal); the full diff
against V295 is 2–5 smaller where cave bytes happen to equal 0xFF (`ds_bytes_out.txt`); CRC trailers excluded.

### 0.3 What the structures teach (each finding marked)

1. **The D operand is the structural lever with the largest payoff in 5–25 Hz, and it costs the envelope little.**
   At the same DC damping (20 S counts per deg/s ≈ 3.2 T per deg/s), the worst-speed Re(T/ω) at 20 Hz is −0.69 (B0, held
   rate), −0.34 (D2a, fresh EMA) and −0.17 (D1b, fresh accumulator difference) at hold age 0, against V295's −0.82; at
   hold age 10 it is −0.52 / −0.20 / −0.03 against V295's −0.89. Over 10–20 Hz D1b is essentially neutral at age 10
   (+0.04 … −0.06). The fitted stiffness is within −13 … +6 % of B0r's at every speed (the −13 % at 10 m/s, in the ms_free
   dip).
   **EVIDENCE** (model, two methods agreeing to 1e-13; §6.3). **BELIEF** for the plant above 8 Hz (never identified).
2. **A 1-tick difference of the 100 Hz-held angle is NOT useless — but as a cal-only D it is the wrong D.** Its
   same-frequency fundamental is exactly the 10 ms average rate, and at 20 Hz its phase (−43°) is BETTER than the held rate
   operand's (−56°, the EMA plus the hold) (`ds_hold_diff_out.txt`). What makes D1a lose is structure, not the hold:
   (i) through the cave's E′ its gain is `∝ G(v)` — D rises with the speed schedule, so the 20 Hz rule binds first and caps
   the highway stiffness FLAT at 58 T per degree (B0r: 90 at 26.9 m/s) while the low-speed PM needs it high; (ii) 90 % of its power is
   the 100 Hz carrier, 26 dB down through the output lag, still the largest 40–200 Hz torque content of any candidate (§6.4);
   (iii) it differentiates the 0xE4 staircase: one frame's setpoint step × Kd/8 × 16 G/256 saturates DCL on ordinary
   steering (CHECK 2: 23–35 % departure from linear on the setpoint path; 1.4 / 4.6 % at 2 / 7 Hz below the clamp — the same residual
   every structure shows from the setpoint-hold age convention). **EVIDENCE.**
3. **The output-lag pole CAN be compensated in the cave, and it stays well under Honda's oscillation detector** (§3.0): the detector watches the motor's ACCELERATION and needs ±12 800 counts ≈ 42 000 deg/s² (EVIDENCE,
   decompile + scale chain), it cuts only at ≤ 15 km/h, and the worst simulated excursion of ANY candidate, leads included, is 0.226 of it (the stiff hand's grab at 3 m/s,
   identical for every candidate) with zero reversals counted in any run.
   What the lead costs is not the detector: it is 5–13 Hz anti-damping (D2b −0.76 … −0.89 at age 0 vs D2a −0.37 … −0.57)
   and a step-authority kick. What it buys over B0r: +25–27 % stiffness at 1–8 m/s, +16–20 % at 15–30 m/s, the best goal
   metric (≥ 0.967), the smallest release lurch and engage droop of the angle kind, 0 highway hold slips. **EVIDENCE** (model, sim).
4. **Placement: forward vs feedback are NOT the same loop here.** The record's "placement decides authority, not the
   filter" holds when the filter sees the whole error. In this lane the I can be kept OFF the lead (forward: the cave returns
   E′>>5 to Honda's I and E_L to P) or ON it (feedback: r26 is led before the I). Forward buys +4–7 % envelope and a
   setpoint kick of ×(1+kh) on P; feedback has no kick. A forward lead on P AND I would be the same loop as D2c with a
   different T_ref (the record's case). **EVIDENCE** (model, §3).
5. **The cascade is an I-P loop, and that is why it fails the goal's tracking metric.** The inner I integrates
   `4 sp_r − R·x`, and Σx is the angle: the integrator carries a P term on the MEASURED angle (−7.5·Ki S counts per degree)
   that the setpoint never sees. With the held operand (D3a, the literal "existing V282 rate loop inside") the gates hold
   only at Kp ≤ 24 and the envelope at 1–8 m/s is the lowest of all (37–39 T/deg). With the fresh operand (D3b) the
   envelope at 10–13 m/s is the HIGHEST of all (+32–52 % over B0r) — but the goal metric reads 0.894–0.949 at 10–19 m/s
   (bar 0.95). `ds_d3_tune.py` shows what raising Ki gives back. **EVIDENCE** (model).
6. **The C1 lib table (B0) fails the brief's credible set**: `ms_free` is a single corner in the brief (PM ≥ 45°), C1r2
   tabulated it as report-only; B0 has PM 32.8° at 11.9 m/s and 12 sub-45° points at 9.75–12.25 m/s, `ms_free+h10` 30.0°.
   Refitted to the brief's set (B0r) the C1r2 structure passes, with the dip at 10–12.5 m/s 16–23 % deeper than the lib
   table and the 1–8 m/s stiffness 10–27 % higher (the lib table sits well under the envelope there). **EVIDENCE**
   (`gate_final_B0.json`). The C1r2 PAGE's 6-knot table also fails the c1r2_members factorial cells (b/1.9×J1.0×tau6+h10:
   PM 8.7° at 11.5 m/s) — the lib table was evidently refit after the page; the page was not updated. Reported, not fixed.
7. **A correction of record, decision-bearing for D2:** `gp-0x6c2c` (the detector's input) is a filtered derivative of the
   motor RATE, i.e. an ACCELERATION, not "a derivative of motor rotor position" (TRACE-2026-09-06 addendum (a)): in
   `FUN_00041464` the same EMA state whose `>>10` is `gp-0x6abe` (scaled by `FUN_0003f776` into the steering-RATE cell
   `gp-0x6a56`, 8 counts per deg/s) is the state that is differenced into `gp-0x6c2c`. **EVIDENCE** (decompile, both
   functions, this session). Reported, not fixed.

---

## 1. Common ground (every implementation)

### 1.1 The shared in-place edits (C1's set, re-read from V295; decodes)

| id | address | V295 → new | V295 → new instruction | loop term | decode of the NEW bytes |
|---|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | x := θ (0.1°) — **angle kind only** | C1 rev 2's Ghidra dry run (inherited); form control `0x40AEA 24 77 00 96 = ld.h -0x6a00[gp],r14` |
| E1′ | `0x28F4C` | `24 3f aa 95` → `24 3f 42 95` | → `ld.h -0x6abe[gp],r7` | x := fresh motor-rate EMA — **D3b only** | **Ghidra dry run on the exact bytes at `0x5658C`: `ld.h -0x6abe, gp, r7`** (this session) |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new (stock's sum) | inherited (C1 rev 2) |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := request==1 ? bVar2 : 0 | inherited |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 | **Ghidra on `b2 05` at `0x15456`: `be` (+6)** |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae | inherited; form `0x29032 24 6f 52 96` |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00, r6` | the hook | encoder reproduces the flown V112 hook `0x55C0E 86 ff 26 ef` |
| V1 | `0x1310D` | `30` → `41` | F181 `…,A160` → `…,A16A` | the fork interlock | data |

**The D-path edit differs by structure:**

| ids | address | V295 → new | instruction | decode |
|---|---|---|---|---|
| B0, B0r | `0x29EDE` / `0x29EE0` | `c7 00` → `80 39`; `10 40 bb 41` → `24 47 aa 95` | `subr r0,r7` ; `ld.h -0x6a56[gp],r8` (C1's E5) | inherited |
| D1a | none | — | Honda's stock `mov r16,r8 ; sub r27,r8` stays: D on E′ | — |
| D1b, D1c, D2a, D2b, D2c | `0x29EE0` only (3 bytes change) | `10 40 bb 41` → `1a 40 00 00` | `mov r26,r8 ; nop` (Kd stays `zxh r7`, positive) | **Ghidra on `1a 40` at `0x211A2`: `mov r26, r8`** |
| D3a, D3b | none | — | Kd 0, DCL 0 (V295's) ⇒ D ≡ 0 | — |

### 1.2 Facts this panel adds (each re-derived this session)

| fact | method | E/B |
|---|---|---|
| `gp-0x6abe` = `(EMA(1024·gp-0x4f50; α = 0xC643C/128 = 37/128)) >> 10`, written only by `FUN_00041464` (st.h `0x41790/0x417A0/0x419F8/0x41A18`); invalid `gp-0x4f50` (`(x + 13000) > 26000` unsigned) writes `0x7FFF` | Ghidra decompile `FUN_00041464` (stock); Python census (28 accesses, 6 are 6-byte `ld.h` in `FUN_00059912`, Ghidra-decoded as loads) | EVIDENCE |
| `FUN_00041464` is called at `0x22200`, the PID at `0x22522`, in the same 1 kHz task `FUN_0002214a` ⇒ `gp-0x6abe` is FRESH at the lane | raw `jarl` scan of `0x2214A..0x22A88`; Ghidra `get_function_callers` | EVIDENCE |
| `gp-0x6a56 = clamp(pol·((gp-0x6abe·48·cal(0xC613A = 1159)) >> 15), ±12000)` in slot 4 ⇒ `x = −1.6978·gp-0x6abe` ⇒ **`gp-0x6abe` = −4.712 counts per deg/s** (x = 8.00 per deg/s, record) | Ghidra decompile `FUN_0003f776`; cal byte read | EVIDENCE |
| `gp-0x6cc4` (the motor-position accumulator) is fresh at the lane (`FUN_0003bd7c` at `0x2224A`), and has a second writer `FUN_0003bcb2` (re-reference `gp-0x6cc4 := param_2 − param_1`, lockstep shadow `gp-0x4d0c`, 7 callers incl. the baseline setter `FUN_0003c7fc`) | Ghidra decompile + callers; Python census (45 accesses) | EVIDENCE |
| **r26 is dead from `0x29D7A` to `0x29F76`** (its first touch is the write `0x29F76 mov r13,r26`): the cave can hand the D multiply an operand in r26 | Ghidra dry-run listings `0x29D60..0x29DC8`, `0x29DC6..0x29E34`, `0x29E30..0x29F34`, `0x29F30..0x2A1B4`; every branch in the range stays in it | EVIDENCE |
| **r16 is not written on the PID path between `0x29E34` and the E_prev store `0x2A18C st.w r16,-0x6cf8[gp]`** (its only writes there are `0x2A0EA`, in the unreachable `gp-0x680a` lane, and `0x2A16C`, the skip epilogue) ⇒ D on E (D1a) differentiates exactly the cave's r16 | same listings | EVIDENCE |
| Honda's D on E: `r27 = E_prev if −768000 ≤ E_prev ≤ 768000 else E` (`0x29E62..0x29E7E cmovnc r16,r8,r27`), `D = clamp((zxh(Kd)·(r16 − r27)) >> 3, ±[0xC61B6])` | same listing | EVIDENCE |
| The 0xE4 setpoint is a 100 Hz hold; the RX task runs AFTER the lane in the arrival tick (0-tick preemption window, tracer) ⇒ ages 1..10 in the linear model (harness_time and the CHECK-2 drive land the frame before the lane, ages 0..9: a 1 ms convention difference, BELIEF on which is the car) | tracer §2; CHECK 2 residual 1.3 % / 4.4 % at 2 / 7 Hz | EVIDENCE for the hold; BELIEF for the phase |

### 1.3 The tools, and the controls they passed

| control | result | E/B |
|---|---|---|
| `ds_model` analytic L vs its own exact harmonic (lifted periodic) for all 13 structure/reference rows | max relative difference 1.2e-13 (T_ref: 3.5e-4 with the setpoint hold, the closed-loop alias coupling the analytic form ignores) | EVIDENCE |
| `ds_model` vs the stability refuter's independent `stab_lin` (rate model 'ideal'), 56 C1r2 points incl. b_q×J1.0(+h10), b_lo×J_hi×tau6+h10 | max abs(ΔPM) **0.000°**, max abs(Δρ) 5.2e-14; reproduces the C1 page's 36.7° / 32.4° / 66.0° / 47.9° / 31.8° / 32.1° / 80.8° | EVIDENCE |
| `ds_lane` (C1r2 config) vs `c1_lib.LaneC1F` (the C1 pages' byte-exact lane), 40 000 random ticks incl. sentinel, skips, wraps | **0 mismatches** in T, I, P, D | EVIDENCE |
| `ds_lane` vs `ds_model`, every structure, open-loop sinusoidal drive (the integer lane's S fundamental vs the analytic C_θ, C_ref) | θ path ≤ 1.8 % at 0.5 / 2 / 7 Hz for all nine; setpoint path 0.3–4.4 % (the 1 ms age convention), D1a's setpoint path 23–35 % because a frame's setpoint step saturates DCL (1.4 / 4.6 % below the clamp, = the common age residual) — a real nonlinearity of D on E; **ALL CHECKS PASS** | EVIDENCE |
| `ds_asm` H1: every cave's assembled bytes executed by the interpreter vs the lane's cave arithmetic | **0 / 60 000** mismatches per cave (r16, the exit address, r6 on freeze, r26 the D operand, RAM writes, every other register incl. r25 unchanged, no other RAM touched) | EVIDENCE (interpreter, not Ghidra; H5 open) |
| 27 encoding-form controls (each form against the same form in V295), the V112 hook re-encoded byte for byte | all OK | EVIDENCE |
| Ghidra dry-run decodes of exact new bytes where they occur in the image | `ld.h -0x6abe,gp,r7` (`0x5658C`), `mov r26,r8` (`0x211A2`), `be` (`0x15456`), `cmove r0,r8,r8` (`0x23FCC`), `cmove r0,r6,r6` (`0x772CE`), `cmovh` form (`0x3539E`), `mov 0x7fffffff,r9` (`0x2AFCE`), `add r26,r16` (`0x593F0`), `shl 0x3,r26` (`0x4C204`), `ld.w -0x6cc4,gp,r8` (`0x3E72A`), `st.w r9,-0x3d30,gp` (`0x28FA8`) | EVIDENCE; the remaining cave bytes are BELIEF until H5 decodes a built image |
| GATE 1 census (`ds_gate1.py`): positive controls gp-0x3d30 (2 = 2 expected), gp-0x6cf8 (4), the 6-byte path on gp-0x6752 (the 4 known sites `0x48E56/68/76/88`) | **gp-0x6c44 and gp-0x6c40: 0 accesses of any form, no LE32 literal**; neighbour gp-0x6c48 has 9 (untouched) | EVIDENCE static; on-car precedent V289's cave used these words (record); register-indirect access cannot be excluded statically |

### 1.4 The credible set, the bars and the rate model

- **Gated (the brief's set):** tier A (PM ≥ 45°, exact GM ≥ 6 dB, stable, |T|,|T_ref| ≤ +3 dB in 5–30 Hz, M20 ≤ V295's,
  L20 ≤ V295's on the member): nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6, **mode13, mode20** (the nominal plant with a
  collocated two-mass mode at 13 Hz ζ 0.1 / 20 Hz ζ 0.05, r2 0.2 — harness_time's members), **ms_free**. Tier B
  (PM ≥ 30°, exact GM ≥ 6 dB, stable): b_lo×J_hi, b_lo×tau6, J1.0, b_q, b_q×J_hi, b_q×J1.0, b_q×tau6, **and every one of
  the 17 members above with the hold aged 11–20 (`+h10`)**. 34 gated members × 145 speeds (1–35 m/s at 0.25 plus the plant
  knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9) = 4 760 gated points per candidate (140 grid speeds). bc = b_lo in the linear model (its friction is
  time-domain).
- **Reported, not gated:** the rest of `c1r2_members`' full factorial (b/1.9, J_hi2, J_hi×tau6, the 3- and 4-way products
  with +h10), J1.3 and its products, tau10, light_b (the prior), b_q0, bq10 — 56 members.
- **The 20 Hz rules, applied INSIDE the envelope:** M20 ≤ V295's and Re(T/ω)₂₀ ≥ V295's at hold age 0 AND 10, same rate
  model, at every speed; L20 ≤ V295's on every tier-A member.
- **Rate model:** the bytes (§1.2): x is the 100 Hz hold of 8 × an EMA (α 37/128, 54 Hz) of the motor rate. The C1 pages
  and harness_freq used a 3-tick position difference (BELIEF in the record) or the ideal rate (stab_lin). I use the EMA
  ('ema') for every design number; on the C1r2 structure it costs 0.1–3° of PM against 'ideal' (§1.3 rows).
- **Fitting:** every candidate's own envelope on the full grid, then an integer table at the C1 lib knot speeds
  (3.1, 8, 10, 11.75, 15.5, 17.5, 26.9 m/s; 7 rows + the 0xFFFF row = 48 bytes) at least 4 % under it, verified on the
  EXACT integer walk (`c1_lib.cave_G`). Exact GM by bisection on the lifted monodromy for every gated point.

### 1.5 One structural fact behind every number: where the margin is spent

Every candidate's envelope is bound by the same three members (§6.1): **J_hi / b_lo×J_hi+h10 / b_lo×tau6+h10 at 1–8 m/s,
ms_free (J 2.1 at 11.9 m/s, PM ≥ 45°) at 10–12.5 m/s, and b_q×J1.0+h10 at ≥ 13 m/s.** No structure here changes which
members bind; the structures change how much stiffness they leave and what they cost at 5–25 Hz.

---

## 2. Design D1 — PD on the angle, D built from the angle operand's own difference

### 2.0 Does the 100 Hz hold make a 1-tick difference useless? (`ds_hold_diff_out.txt`)

`θ_h` changes on one tick in ten. Its 1-tick difference is an impulse train: zero for nine ticks, the full 10 ms change on
the tenth. Its **same-frequency fundamental is exactly `(z⁻¹ − z⁻¹¹)/10 ms`, the 10 ms average rate**:

| f (Hz) | Δθ_h(1 tick)·1000 | held x/8 (EMA + hold) | fresh EMA `gp-0x6abe` | fresh `gp-0x6cc4` difference |
|---|---|---|---|---|
| 5 | 0.996 ∠−10.8° | 0.992 ∠−14.3° | 0.996 ∠−4.4° | 1.000 ∠−0.9° |
| 10 | 0.984 ∠−21.6° | 0.968 ∠−28.5° | 0.984 ∠−8.7° | 1.000 ∠−1.8° |
| 13 | 0.972 ∠−28.1° | 0.946 ∠−37.0° | 0.973 ∠−11.3° | 1.000 ∠−2.3° |
| 20 | 0.935 ∠−43.2° | 0.879 ∠−56.4° | 0.939 ∠−16.8° | 0.999 ∠−3.6° |

**So no: in the loop the held difference is a slightly BETTER rate operand than the held rate cell itself** (the cell
carries the EMA's 2.5 ms on top of the hold). **EVIDENCE** (arithmetic). Its costs are elsewhere:
- 90 % of its power is not at the signal frequency (a 1 Hz, 10 deg/s motion): the 100 Hz carrier and its aliases, 26 dB
  down through the output lag. **EVIDENCE** (simulation in the same script).
- One 0.1° count of θ_h through a D of 20 S per deg/s is a one-tick S impulse of 2 000 (T peak 5.0 counts), against a
  P step of 31 S (5.0 T counts, held). The fine accumulator's quantum is 1/278.5° (T peak 0.18). **EVIDENCE.**
- The "10-tick-aware" difference IS possible in the cave: D1c spreads each impulse over ~8 ticks with a first-order
  low-pass (one RAM word). It removes the clamp saturation and most of the 100 Hz carrier and costs phase (§2.3).

### 2.1 D1a — cal-only D on the error (Honda's stock D, no E5)

**The loop (integer; every line is Honda's bytes or C1's cave, unchanged):**

```python
r26 = clamp(8*th_h[n] + 8*th_h[n-1], +-65535)              # E1 0x28F4C, E2 0x28FA4, a 0 / b 8192 / C 65535
E   = (sp69ae << 2) - r26 ; E1 = (E * G(v)) >> 8           # C1's cave at 0xC4C00 (displaced pair, the walk, mul ; sar 8)
I   = clamp((I8 >> 3) + ((dz(E1 >> 5) * 56) >> 3), +-(4096 << 7))   # frozen when |tq| > 512 or the ramp is not full
P   = clamp((E1 * 112) >> 8, +-15360)                       # 0x29E34..0x29E5C
r27 = E_prev if -768000 <= E_prev <= 768000 else E1         # 0x29E5E..0x29E7E cmovnc (E_prev = gp-0x6cf8 = last r16)
D   = clamp((256 * (E1 - r27)) >> 3, +-10240)               # 0x29EDE zxh r7 ; 0x29EE0 mov r16,r8 ; sub r27,r8 (STOCK)
```
- **What D is, physically:** per deg/s of wheel rate the average D is `0.02·Kd·G/256` S counts = 5.12·G/256 (26.5 S at G 1326,
  8.0 S at G 399 = 11.75 m/s); it ALSO responds to the setpoint rate with the same gain (D on error), and it arrives as one
  impulse per 0.1° count of θ_h (§2.0).
- **Why Kd 256:** in round 2 (`ds_explore2_out.txt`) Kd 200 collapses the 1–3 m/s envelope (b_hi binds: D too small at low
  G), Kd 320 rule-binds the whole table at 49 T/deg. 256 is the best compromise; the 20 Hz rule then caps G FLAT at 1326
  everywhere except the ms_free dip. **EVIDENCE** (model).
- **Bytes: 185** (17 in-place code — C1's seven without E5 — + 144 cave (C1's 96 code bytes + this table's 48) + 24 cal).
  **No RAM.** Its D costs zero code bytes: that is its only merit.

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> 00 01         Kd record Y[0] 0 -> 256                              
   cal  0x0e5128  00 00        -> 00 01         Kd record Y[1] 0 -> 256                              
   cal  0x0e512a  00 00        -> 00 01         Kd record Y[2] 0 -> 256                              
   cal  0x0e512c  00 00        -> 00 01         Kd record Y[3] 0 -> 256                              
   cave 0xc4c00..0xc4c90: 144 bytes (96 code + 48 table)  sha256 fb8a0db9ff715231
   FULL DIFF vs V295 over [0x13000, 0x100000): 183 bytes; changed bytes: in-place code 17, cal 24, cave 144 (its bytes that differ from 0xFF: 142); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

The cave is C1's listing with this candidate's table (assembled and H1-tested in `ds_asm_out.txt`, 0 / 60 000).

- **GATE 2 (brief's set): 0 fails.** Tier A min J_hi 52.3° (1 m/s), ms_free 48.1°; tier B min b_q×J1.0+h10 31.6° (15.5 m/s);
  min exact GM 8.4 dB; **M20 3.12 against V295's 3.38 and L20 0.92× V295's — both rules nearly binding** (they set the table).
- **Re(T/ω):** at age 0 −0.79 at 17–20 Hz (0.96× V295's); at age 10 −1.51 at 10 Hz where V295 is −1.17 (worse), −0.80 at
  20 Hz (0.90×).
- **Goal metric: 0.944 at 11.9 m/s — below 0.95** (the ms_free dip, G 399). All other bands ≥ 0.953.
- **Time domain (§6.4):** the fewest dwell-then-jump events at 3–5 m/s (4 / 4), but **the largest release lurch of any
  candidate (firm 9.6° / 18.6° on bc, light 10.5° / 20.5°)**, the largest step overshoot (21.6 % / 42.1 %), **5–30 Hz
  texture 2.5 counts rms (above the 2.0 line bar)** and **40–200 Hz content 26.8 counts rms (35× B0r)**. The release lurch
  is the DCL clamp: once the wheel moves faster than ~40 deg/s, one frame's θ_h step drives D past 10 240 and the damping
  is clipped exactly when the release needs it. **EVIDENCE** (sim); the mechanism is the arithmetic above.
- **Verdict on its own terms:** the cal-only D answers "can the angle operand's own difference be the D" with **yes in the
  loop, no in the lane**: it fails the texture bar, the goal metric at 11.9 m/s and every release scenario. Not
  recommended by its own numbers; kept as the scored minimum-bytes implementation of D1.

### 2.2 D1b — D on the fresh 1 kHz motor-accumulator difference

**The loop (integer):** C1's angle P + I and G walk unchanged; the D operand is built in the cave and handed to Honda's
multiply in r26:

```python
d   = ld.w gp-0x6cc4                        # the 1 kHz motor-position accumulator (FUN_0003bd7c @0x2224A, before the PID)
op  = (d - d_prev) << 3 ; d_prev = d        # cave RAM gp-0x6c44 (written on every PID tick, not on skips)
D   = clamp((72 * op) >> 3, +-10240)        # 0x29EDE zxh r7 (Kd 72) ; 0x29EE0 mov r26,r8 ; nop  -> D = 72 (d - d_prev)
```
- **Scale (BELIEF on the frame, EVIDENCE on each link):** θ (gp-0x6a00) moves 1.155 counts per lin(d) count near centre
  and 0.962 outward (TRACE angle §2.1), lin(d) = d/32.17 per 0.1°, pol −1 ⇒ Δd = −278.5 counts per degree near centre,
  −334 outward. D = −20.05 S per deg/s near centre, −24.0 outward (the VGR correction lives in gp-0x6a00, not in the
  accumulator). The gate used the near-centre scale; at the outward scale M20 rises ×1.2 to 2.9 (< 3.38).
- **No first-tick guard (8 bytes saved, declared):** after skip ticks `d_prev` is stale; the first PID tick gives ONE tick
  of D, bounded by DCL (10 240 S → ≤ 26 T counts peak through the output lag) and multiplied by the ramp (≈ 0 at an engage).
  A re-reference of gp-0x6cc4 by `FUN_0003bcb2` while engaged does the same (one tick, ≤ DCL).
- **Bytes: 204** (20 in-place: the seven + `0x29EE0` 3 bytes; 160 cave = 112 code + 48 table; 24 cal). **RAM: 1 word,
  gp-0x6c44** (GATE 1 §1.3: 0 accesses of any form in V295).

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   code 0x029ee0  10 40 bb 41  -> 1a 40 00 00   mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop          D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> 48 00         Kd record Y[0] 0 -> 72                               
   cal  0x0e5128  00 00        -> 48 00         Kd record Y[1] 0 -> 72                               
   cal  0x0e512a  00 00        -> 48 00         Kd record Y[2] 0 -> 72                               
   cal  0x0e512c  00 00        -> 48 00         Kd record Y[3] 0 -> 72                               
   cave 0xc4c00..0xc4ca0: 160 bytes (112 code + 48 table)  sha256 73426e8938386e96
   FULL DIFF vs V295 over [0x13000, 0x100000): 202 bytes; changed bytes: in-place code 20, cal 24, cave 160 (its bytes that differ from 0xFF: 158); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D1b: cave at 0xc4c00: 160 bytes = 112 code (37 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      c2 82              ('shl_i', 2, 16)                         displaced 0x29D76: 4 sp
  0xc4c02        ba 81              ('sub', 26, 16)                          displaced 0x29D78: E = 4 sp - r26
  0xc4c04        24 d7 3d 93        ('ld_w', -27844, 4, 26)                  d = gp-0x6cc4 (1 kHz motor-position accumulator)   [D OPERAND]
  0xc4c08        24 6f bd 93        ('ld_w', -27716, 4, 13)                  d_prev (cave RAM gp-0x6c44)
  0xc4c0c        64 d7 bd 93        ('st_w', 26, -27716, 4)                  d_prev := d
  0xc4c10        ad d1              ('sub', 13, 26)                          op = d - d_prev (= -0.2785 counts per deg/s per tick)
  0xc4c12        c3 d2              ('shl_i', 3, 26)                         op << 3
  0xc4c14        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v)]
  0xc4c18        29 06 70 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v)]
  0xc4c1e        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c22        ed 41              ('cmp', 13, 8)                           
  0xc4c24        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c26        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c2a        b5 15              ('br', 'APPLY')                          
  0xc4c2c L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c30        ed 41              ('cmp', 13, 8)                           
  0xc4c32        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c34        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c38        a5 fd              ('br', 'L1')                             
  0xc4c3a SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c3e        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c40        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c44        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c48        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c4a        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c4e        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c50 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        E * G (low word)                                 [THE SPEED GAIN]
  0xc4c54        a8 82              ('sar_i', 8, 16)                         E' = (E G) >> 8
  0xc4c56        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c5a        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c5e        ed 41              ('cmp', 13, 8)                           
  0xc4c60        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c62        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c66        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c68 FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c6a        b6 07 14 51        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c6e DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c70 TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 1217, 1121) (1843, 1526, -7970) (2304, 629, -935) (2707, 537, 2830) (3571, 1134, 2932) (4032, 1464, 1293) (6198, 2148, 0) (65535, 2148, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails.** Tier A min J_hi 46.3° at 1 m/s (thin: 1.3°); tier B min b_lo×J_hi+h10 32.0° (1 m/s), b_q×J1.0+h10
  33.7°; **min exact GM 15.6 dB, the largest of all** (the D does not lag, so it adds no phase at the GM frequency).
- **Re(T/ω), the best of every candidate:** age 0 −0.47 (5 Hz) … −0.17 (20 Hz) = **0.21× V295 at 20 Hz**; age 10 essentially
  neutral at 10–20 Hz (−0.06 … +0.04).
- **Goal metric ≥ 0.962** (17 m/s) — passes, margin 0.012.
- **Time domain:** ≈ B0r (dj 5 / 9 at 3–5 m/s, 3 hold slips at 15–30 m/s under the harness road disturbance, lurch firm 4.2° /
  6.0°, light 6.3° / 6.9°, droop 4.6° / 5.2°), texture 0.64 / 0.78 counts (≈ B0r).

### 2.3 D1c — the held difference spread over ~8 ticks (21 Hz low-pass, one RAM word)

**The loop (integer):** the "10-tick-aware" difference — the held angle's step spread over ~8 ticks:

```python
s_new = ld.w gp-0x3d30                       # the fb state, stored at 0x28FA8 this tick (= 8 th_h[n])
ds    = (2*s_new - r26) << 3                 # s_new - s_old = 8 (th_h[n] - th_h[n-1]) counts, << 3
lp    = lp + ((ds - lp) >> 3)                # 21 Hz pole; cave RAM gp-0x6c44 ; first tick after a skip: lp := 0
D     = clamp((250 * (-lp)) >> 3, +-10240)   # 0x29EE0 mov r26,r8 ; nop ; Kd 250  -> 20 S per deg/s at DC
```
- **Bytes: 232** (20 in-place + 188 cave (140 code + 48) + 24 cal). **RAM: gp-0x6c44.** Hazard: Δs is read from the clamped
  r26 (±65 535 = 409.6°): beyond that angle D is garbage (P is too, as in C1).

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   code 0x029ee0  10 40 bb 41  -> 1a 40 00 00   mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop          D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> fa 00         Kd record Y[0] 0 -> 250                              
   cal  0x0e5128  00 00        -> fa 00         Kd record Y[1] 0 -> 250                              
   cal  0x0e512a  00 00        -> fa 00         Kd record Y[2] 0 -> 250                              
   cal  0x0e512c  00 00        -> fa 00         Kd record Y[3] 0 -> 250                              
   cave 0xc4c00..0xc4cbc: 188 bytes (140 code + 48 table)  sha256 848b91731677f8c2
   FULL DIFF vs V295 over [0x13000, 0x100000): 227 bytes; changed bytes: in-place code 20, cal 24, cave 188 (its bytes that differ from 0xFF: 183); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D1c: cave at 0xc4c00: 188 bytes = 140 code (47 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      c2 82              ('shl_i', 2, 16)                         displaced 0x29D76: 4 sp
  0xc4c02        ba 81              ('sub', 26, 16)                          displaced 0x29D78: E = 4 sp - r26
  0xc4c04        24 47 d1 c2        ('ld_w', -15664, 4, 8)                   s_new = gp-0x3d30 (the fb state, stored at 0x28FA8)  [D OPERAND]
  0xc4c08        c1 42              ('shl_i', 1, 8)                          
  0xc4c0a        ba 41              ('sub', 26, 8)                           ds = 2 s_new - r26 = s_new - s_old = 8 x the held-angle step
  0xc4c0c        c3 42              ('shl_i', 3, 8)                          ds << 3
  0xc4c0e        24 6f bd 93        ('ld_w', -27716, 4, 13)                  lp (cave RAM gp-0x6c44)
  0xc4c12        ad 41              ('sub', 13, 8)                           
  0xc4c14        a3 42              ('sar_i', 3, 8)                          
  0xc4c16        cd 41              ('add', 13, 8)                           lp += ((ds << 3) - lp) >> 3   (pole 21 Hz)
  0xc4c18        24 6f 09 93        ('ld_w', -27896, 4, 13)                  Honda's E_prev gp-0x6cf8 (0x7FFFFFFF after any skip tick)  [ENGAGE INIT]
  0xc4c1c        29 06 ff ff ff 7f  ('mov_i32', 2147483647, 9)               
  0xc4c22        e9 69              ('cmp', 9, 13)                           
  0xc4c24        e0 47 24 43        ('cmovz', 0, 8, 8)                       first tick: lp := 0
  0xc4c28        64 47 bd 93        ('st_w', 8, -27716, 4)                   
  0xc4c2c        80 41              ('subr', 0, 8)                           
  0xc4c2e        08 d0              ('mov', 8, 26)                           op = -lp
  0xc4c30        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v)]
  0xc4c34        29 06 8c 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v)]
  0xc4c3a        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c3e        ed 41              ('cmp', 13, 8)                           
  0xc4c40        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c42        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c46        b5 15              ('br', 'APPLY')                          
  0xc4c48 L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c4c        ed 41              ('cmp', 13, 8)                           
  0xc4c4e        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c50        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c54        a5 fd              ('br', 'L1')                             
  0xc4c56 SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c5a        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c5c        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c60        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c64        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c66        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c6a        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c6c APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        E * G (low word)                                 [THE SPEED GAIN]
  0xc4c70        a8 82              ('sar_i', 8, 16)                         E' = (E G) >> 8
  0xc4c72        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c76        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c7a        ed 41              ('cmp', 13, 8)                           
  0xc4c7c        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c7e        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c82        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c84 FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c86        b6 07 f8 50        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c8a DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c8c TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 1164, 889) (1843, 1409, -6388) (2304, 690, -1514) (2707, 541, 2361) (3571, 1039, 2674) (4032, 1340, 1326) (6198, 2041, 0) (65535, 2041, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails;** min exact GM **7.0 dB** (b_lo×tau6+h10, 8 m/s) — the thinnest GM of the angle kind.
- **Re(T/ω): worse than B0r at 5–13 Hz** (age 0 −1.16 … −1.21 at 5–10 Hz vs −0.84; age 10 −2.00 at 5 Hz) — the 21 Hz pole
  adds lag where the D matters — and better at 17–25 Hz.
- **Time: 5–30 Hz texture 5.4 / 3.9 counts rms in holds — above the 2.0 bar (a FAIL of the line-only gate)**: the low-pass
  turns the 100 Hz impulse train into a 5–30 Hz one. dj 5 events at 8–12.5 m/s on bc.
- **Verdict on its own terms: dominated by D1b** (more bytes, worse 5–13 Hz damping, texture). The answer to "is a
  10-tick-aware difference possible in the cave?" is yes (40 code bytes, one RAM word); it is not worth having, because
  the fresh accumulator (D1b) gives the same D with no hold at all for fewer bytes.

---

## 3. Design D2 — compensation placement, the output-lag pole and Honda's oscillation detector

### 3.0 Honda's oscillation detector: what it watches, and where a cave must stay

**What it is (EVIDENCE: Ghidra decompile of `FUN_000428d4` and `FUN_00041464` on stock, both byte-identical in V295 by a
Python slice compare; cals read from V295):**

```
FUN_00041464 (1 kHz, called at 0x22200):
  u     = EMA(1024 * gp-0x4f50 ; 37/128)          # 54 Hz; the SAME state whose >>10 is gp-0x6abe (-4.712 per deg/s)
  d     = u_new - u_prev                           # one-tick difference of the motor-RATE EMA = acceleration
  d32   = clamp(32 d, +-0xFA0000)                  # (d >= 0x7D000 -> +0xFA0000)
  s2   += ((d32 - s2) * cal(0xC40DC)) >> 6         # V295: 14 -> 39 Hz (stock 22 -> 67 Hz)
  gp-0x6c2c = s2 >> 9
FUN_000428d4 (1 kHz, 0x22926; skipped while DTC bit 5 is set):
  FSM on gp-0x67df: an excursion beyond +12800 (0xC620A) then beyond -12800 (or vice versa) counts one reversal into
  gp-0x357c; gp-0x6759 counts ticks between them and the FSM resets at cal(0xC64DD) = 50 ticks  => only content
  faster than 10 Hz can count
  if gp-0x6a5e <= cal(0xC62E0) = 960 (15 km/h): factor = LERP(0xC694A {0,15,20,25} -> 0xC6952 {32768,32768,19661,
  19661}, level gp-0x671a)  -> gp-0x6994 -> FUN_00045608(2, ...)   (governor slot 2, MIN-folded: x0.600 at >= 20)
  else factor = 0x8000 (no cut)
```

**What it watches, in physical units:** `gp-0x6c2c = 64·Δ(gp-0x6abe)/tick = 64 × 4.712 × α/1000 = 0.3016·α` counts,
α = the motor-side wheel acceleration in deg/s², low-passed at 54 and 39 Hz. **The 12 800 threshold is ≈ 42 400 deg/s²**
(≈ 50 700 at 20 Hz after the filters): a sustained > 10 Hz oscillation of at least ±3.2° at 20 Hz or ±10.7° at 10 Hz,
for 15–20 alternations (≥ 0.375 s at 20 Hz), at ≤ 15 km/h. **EVIDENCE** for each link (two decompiles, the cal, x = 8.00
per deg/s); the composite scale is arithmetic on EVIDENCE, BELIEF only in that the plant model's θ is the sensed motor-side
angle (the redo audit measured d(steeringAngleDeg)/dt ÷ steeringRateDeg = 1.002–1.007).

**Why the record struck the output-lag pole move:** on V282 the inner RATE loop had a 20 Hz crossover resonance; a faster
output stage passes more of that resonance to the motor. `grind1_detector_margin_v287.py` ranked it with a SCALE-FREE
method (the threshold at which a measured waveform would reach N reversals), because the 2026-09-06 trace could not find the
scale. With the scale above, the absolute margin is computable, and the angle loop has no 20 Hz crossover.

**How a cave stays under it:** keep the > 10 Hz motor acceleration far below 42 000 deg/s² — i.e. do not create a
lightly damped closed-loop pole above 10 Hz (the gate's tier-A "no 5–50 Hz pole ζ < 0.2" and "|T| ≤ +3 dB in 5–30 Hz"
already enforce it on the model) — and measure it: every time-domain run in §6.4 carries the detector mirror
(`ds_time.Detector`), max |gp-0x6c2c| / 12 800 and the max reversal count.

### 3.1 D2a — D on the fresh motor-rate EMA

**The loop (integer):**

```python
op = ld.h gp-0x6abe                                        # fresh 1 kHz motor-rate EMA, -4.712 counts per deg/s
op = 0 if (op + 13000) > 26000 (unsigned) else op          # Honda's OWN validity form (FUN_0003f776): incl. the 0x7FFF sentinel
D  = clamp((34 * op) >> 3, +-10240)                        # 0x29EE0 mov r26,r8 ; nop ; Kd 34 -> -20.0 S per deg/s
```
- The validity test is the one `FUN_0003f776` applies before it writes `gp-0x6a56`, so the fresh D is zero exactly when
  the held operand would have been zero: no new fault exposure. A pure in-place alternative (`0x29EE0 → ld.h -0x6abe[gp],r8`,
  4 bytes, no cave instructions) was **rejected**: on an invalid motor rate it would multiply 0x7FFF into D and rail DCL
  (10 240 S ≈ 1 650 T counts) for as long as the fault lasts.
- **Bytes: 206** (20 in-place + 162 cave (114 code + 48) + 24 cal). **No RAM.**

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   code 0x029ee0  10 40 bb 41  -> 1a 40 00 00   mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop          D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> 22 00         Kd record Y[0] 0 -> 34                               
   cal  0x0e5128  00 00        -> 22 00         Kd record Y[1] 0 -> 34                               
   cal  0x0e512a  00 00        -> 22 00         Kd record Y[2] 0 -> 34                               
   cal  0x0e512c  00 00        -> 22 00         Kd record Y[3] 0 -> 34                               
   cave 0xc4c00..0xc4ca2: 162 bytes (114 code + 48 table)  sha256 caa6f39c2ba57f05
   FULL DIFF vs V295 over [0x13000, 0x100000): 204 bytes; changed bytes: in-place code 20, cal 24, cave 162 (its bytes that differ from 0xFF: 160); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D2a: cave at 0xc4c00: 162 bytes = 114 code (37 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      c2 82              ('shl_i', 2, 16)                         displaced 0x29D76: 4 sp
  0xc4c02        ba 81              ('sub', 26, 16)                          displaced 0x29D78: E = 4 sp - r26
  0xc4c04        24 d7 42 95        ('ld_h', -27326, 4, 26)                  op = gp-0x6abe (fresh 1 kHz motor-rate EMA)        [D OPERAND]
  0xc4c08        1a 46 c8 32        ('addi', 13000, 26, 8)                   Honda's validity form (FUN_0003f776): op + 13000
  0xc4c0c        20 6e 90 65        ('movea', 26000, 0, 13)                  
  0xc4c10        ed 41              ('cmp', 13, 8)                           
  0xc4c12        e0 d7 36 d3        ('cmovh', 0, 26, 26)                     op + 13000 > 26000 unsigned (incl. the 0x7FFF sentinel): op := 0
  0xc4c16        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v)]
  0xc4c1a        29 06 72 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v)]
  0xc4c20        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c24        ed 41              ('cmp', 13, 8)                           
  0xc4c26        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c28        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c2c        b5 15              ('br', 'APPLY')                          
  0xc4c2e L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c32        ed 41              ('cmp', 13, 8)                           
  0xc4c34        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c36        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c3a        a5 fd              ('br', 'L1')                             
  0xc4c3c SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c40        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c42        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c46        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c4a        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c4c        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c50        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c52 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        E * G (low word)                                 [THE SPEED GAIN]
  0xc4c56        a8 82              ('sar_i', 8, 16)                         E' = (E G) >> 8
  0xc4c58        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c5c        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c60        ed 41              ('cmp', 13, 8)                           
  0xc4c62        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c64        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c68        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c6a FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c6c        b6 07 12 51        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c70 DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c72 TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 1195, 1204) (1843, 1527, -7988) (2304, 628, -925) (2707, 537, 2773) (3571, 1122, 2941) (4032, 1453, 1278) (6198, 2129, 0) (65535, 2129, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails;** tier A min J_hi 46.7°; min exact GM 15.1 dB.
- **Re(T/ω):** age 0 −0.57 … −0.31 (**20 Hz −0.34 = 0.41× V295**); age 10 −0.74 … −0.14 (**20 Hz −0.20 = 0.22× V295**).
- **Goal metric ≥ 0.961.** **Time ≈ B0r** (dj 6 / 7, lurch firm 4.1° / 5.7°, droop 4.7° / 5.2°, texture 0.67 / 0.77).
- **What D2a vs D1b decides:** the same D at DC; D1b has no EMA (2.5 ms less lag: −0.17 vs −0.34 at 20 Hz) and costs a RAM
  word; D2a costs no RAM and inherits Honda's validity test.

### 3.2 D2b — forward-path output-lag lead (P only)

**The loop (integer):** D2a's D, plus a first-order lead on E′ for P only; Honda's I keeps the unled E′:

```python
E1  = (E * G(v)) >> 8
w   = w + ((E1 - w) >> 4) ; w = E1 on the first tick after a skip   # cave RAM gp-0x6c40 (Honda's sentinel gp-0x6cf8)
e5  = 0 if frozen else E1 >> 5          # Honda's 0x29D7A/7C done in the cave; returns to 0x29D7E: the I integrates E1
r16 = 2*E1 - w                          # = E1 + (E1 - w): P = clamp((r16 * 112) >> 8) sees the lead
# Lf(z) = 1 + (1 - (1/16)/(1 - (15/16) z^-1)): zero 5.22 Hz (cancels the 5.05 Hz output-lag pole 992/1024), pole 10.27 Hz
```
- **Output-lag compensation, in the cave:** for the P path the 5.05 Hz output stage becomes, in effect, a 10.3 Hz one; the
  D (fresh rate) and the I still see the 5.05 Hz lag. **Honda's oscillation detector does not see it:** worst simulated
  `gp-0x6c2c` excursion 0.224 of the threshold (the stiff hand's grab at 3 m/s, the same for every candidate), **zero
  reversals in every run** (§3.0, §6.4). **EVIDENCE** (sim).
- **Bytes: 246** (20 in-place + 202 cave (154 code + 48) + 24 cal). **RAM: gp-0x6c40.**

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   code 0x029ee0  10 40 bb 41  -> 1a 40 00 00   mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop          D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> 22 00         Kd record Y[0] 0 -> 34                               
   cal  0x0e5128  00 00        -> 22 00         Kd record Y[1] 0 -> 34                               
   cal  0x0e512a  00 00        -> 22 00         Kd record Y[2] 0 -> 34                               
   cal  0x0e512c  00 00        -> 22 00         Kd record Y[3] 0 -> 34                               
   cave 0xc4c00..0xc4cca: 202 bytes (154 code + 48 table)  sha256 f03bf259e9f878ef
   FULL DIFF vs V295 over [0x13000, 0x100000): 241 bytes; changed bytes: in-place code 20, cal 24, cave 202 (its bytes that differ from 0xFF: 197); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D2b: cave at 0xc4c00: 202 bytes = 154 code (49 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      c2 82              ('shl_i', 2, 16)                         displaced 0x29D76: 4 sp
  0xc4c02        ba 81              ('sub', 26, 16)                          displaced 0x29D78: E = 4 sp - r26
  0xc4c04        24 d7 42 95        ('ld_h', -27326, 4, 26)                  op = gp-0x6abe (fresh 1 kHz motor-rate EMA)        [D OPERAND]
  0xc4c08        1a 46 c8 32        ('addi', 13000, 26, 8)                   Honda's validity form (FUN_0003f776): op + 13000
  0xc4c0c        20 6e 90 65        ('movea', 26000, 0, 13)                  
  0xc4c10        ed 41              ('cmp', 13, 8)                           
  0xc4c12        e0 d7 36 d3        ('cmovh', 0, 26, 26)                     op + 13000 > 26000 unsigned (incl. the 0x7FFF sentinel): op := 0
  0xc4c16        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v)]
  0xc4c1a        29 06 9a 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v)]
  0xc4c20        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c24        ed 41              ('cmp', 13, 8)                           
  0xc4c26        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c28        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c2c        b5 15              ('br', 'APPLY')                          
  0xc4c2e L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c32        ed 41              ('cmp', 13, 8)                           
  0xc4c34        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c36        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c3a        a5 fd              ('br', 'L1')                             
  0xc4c3c SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c40        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c42        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c46        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c4a        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c4c        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c50        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c52 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        E * G (low word)                                 [THE SPEED GAIN]
  0xc4c56        a8 82              ('sar_i', 8, 16)                         E' = (E G) >> 8
  0xc4c58        24 6f c1 93        ('ld_w', -27712, 4, 13)                  w (cave RAM gp-0x6c40)                           [FWD LEAD]
  0xc4c5c        10 40              ('mov', 16, 8)                           
  0xc4c5e        ad 41              ('sub', 13, 8)                           E' - w
  0xc4c60        a4 42              ('sar_i', 4, 8)                          
  0xc4c62        c8 69              ('add', 8, 13)                           w += (E' - w) >> 4   (pole 10.3 Hz)
  0xc4c64        24 47 09 93        ('ld_w', -27896, 4, 8)                   Honda's E_prev gp-0x6cf8 (0x7FFFFFFF after any skip tick)  [ENGAGE INIT]
  0xc4c68        29 06 ff ff ff 7f  ('mov_i32', 2147483647, 9)               
  0xc4c6e        e9 41              ('cmp', 9, 8)                            
  0xc4c70        f0 6f 24 6b        ('cmovz', 16, 13, 13)                    first tick: w := E'
  0xc4c74        64 6f c1 93        ('st_w', 13, -27712, 4)                  
  0xc4c78        10 30              ('mov', 16, 6)                           e5 = E' >> 5 (Honda's 0x29D7A/7C, done here: the I integrates E')
  0xc4c7a        a5 32              ('sar_i', 5, 6)                          
  0xc4c7c        c1 82              ('shl_i', 1, 16)                         
  0xc4c7e        ad 81              ('sub', 13, 16)                          r16 = E_L = 2 E' - w  (P sees the lead; zero 5.2 Hz)
  0xc4c80        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque|                                  [I FREEZE on the hand]
  0xc4c84        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c88        ed 41              ('cmp', 13, 8)                           
  0xc4c8a        e0 37 36 33        ('cmovh', 0, 6, 6)                       |tq| > THR: e5 := 0
  0xc4c8e        ce 6e 00 80        ('andi', 32768, 14, 13)                  ramp gp-0x69b0 (r14)                             [I FREEZE on ramp]
  0xc4c92        e0 37 24 33        ('cmovz', 0, 6, 6)                       ramp not full: e5 := 0
  0xc4c96        b6 07 e8 50        ('jr', 171390)                           return to 0x29D7E (exc from r6)
  0xc4c9a TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 1501, 1070) (1843, 1796, -10307) (2304, 636, -589) (2707, 578, 3162) (3571, 1245, 3323) (4032, 1619, 1615) (6198, 2473, 0) (65535, 2473, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails;** min exact GM 11.4 dB; T530 −1.4 dB (the closest of the angle kind to the +3 dB bar).
- **Envelope vs B0r: +27 % at 1–5 m/s, +25 % at 8, +16 % at 15, +18–20 % at 17–30**; in the ms_free dip −10 % (10 m/s)
  … +11 % (12.5 m/s).
- **Re(T/ω):** age 0 −0.79 … −0.89 at 5–10 Hz (≈ B0r), **−0.52 at 20 Hz (0.63× V295)**; age 10 −1.31 at 5 Hz, −0.20 at 20 Hz.
- **Goal metric ≥ 0.967 — the best of all candidates.**
- **Time:** dj 4 / 4 at 3–5 m/s (fewest of the angle kind, with D1a/D1c/D2c), **0 hold slips at 15–30 m/s** (B0r 3), **the
  smallest release lurch of the angle kind (firm 3.2° / 4.1°)**, the smallest engage droop (4.1° / 4.4°); costs: texture
  1.0 / 1.8 counts (5–30 / 40–200 Hz, 1.5–2.3× B0r, under the bar), a ×2 P kick on setpoint steps (step peak T at 8 m/s
  1 029 vs B0r 787 counts).

### 3.3 D2c — feedback-path output-lag lead (P and I)

**The loop (integer):** the same filter on the MEASUREMENT, before the error is formed; P and I both see it:

```python
w   = w + ((r26 - w) >> 4) ; w = r26 on the first tick      # cave RAM gp-0x6c40
r26 = 2*r26 - w                                             # the led feedback
E   = (sp69ae << 2) - r26 ; E1 = (E * G(v)) >> 8            # then C1's freeze/I/P and D2a's fresh D, unchanged
```
- **Bytes: 242** (20 in-place + 198 cave (150 code + 48) + 24 cal). **RAM: gp-0x6c40.**

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 00 96   ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7           operand x := theta (0.1 deg)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   code 0x029ee0  10 40 bb 41  -> 1a 40 00 00   mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop          D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)
   cal  0x0c63e8  f3 03        -> 00 00         a 1011 -> 0                                          
   cal  0x0c63ea  1a 04        -> 00 20         b 1050 -> 8192                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 38 00         Ki 0 -> 56                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0c61b6  00 00        -> 00 28         DCL 0 -> 10240                                       
   cal  0x0e5384  c0 03        -> 70 00         Kp record Y[0] 960 -> 112                            
   cal  0x0e5386  c0 03        -> 70 00         Kp record Y[1] 960 -> 112                            
   cal  0x0e5388  c0 03        -> 70 00         Kp record Y[2] 960 -> 112                            
   cal  0x0e538a  c0 03        -> 70 00         Kp record Y[3] 960 -> 112                            
   cal  0x0e538c  c0 03        -> 70 00         Kp record Y[4] 960 -> 112                            
   cal  0x0e5126  00 00        -> 22 00         Kd record Y[0] 0 -> 34                               
   cal  0x0e5128  00 00        -> 22 00         Kd record Y[1] 0 -> 34                               
   cal  0x0e512a  00 00        -> 22 00         Kd record Y[2] 0 -> 34                               
   cal  0x0e512c  00 00        -> 22 00         Kd record Y[3] 0 -> 34                               
   cave 0xc4c00..0xc4cc6: 198 bytes (150 code + 48 table)  sha256 01705da4fb9dd20f
   FULL DIFF vs V295 over [0x13000, 0x100000): 237 bytes; changed bytes: in-place code 20, cal 24, cave 198 (its bytes that differ from 0xFF: 193); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D2c: cave at 0xc4c00: 198 bytes = 150 code (49 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      24 6f c1 93        ('ld_w', -27712, 4, 13)                  w (cave RAM gp-0x6c40)                           [FB LEAD]
  0xc4c04        1a 40              ('mov', 26, 8)                           
  0xc4c06        ad 41              ('sub', 13, 8)                           r26 - w
  0xc4c08        a4 42              ('sar_i', 4, 8)                          >> 4
  0xc4c0a        c8 69              ('add', 8, 13)                           w += (r26 - w) >> 4   (pole 10.3 Hz)
  0xc4c0c        24 47 09 93        ('ld_w', -27896, 4, 8)                   Honda's E_prev gp-0x6cf8 (0x7FFFFFFF after any skip tick)  [ENGAGE INIT]
  0xc4c10        29 06 ff ff ff 7f  ('mov_i32', 2147483647, 9)               
  0xc4c16        e9 41              ('cmp', 9, 8)                            
  0xc4c18        fa 6f 24 6b        ('cmovz', 26, 13, 13)                    first tick: w := r26
  0xc4c1c        64 6f c1 93        ('st_w', 13, -27712, 4)                  
  0xc4c20        c1 d2              ('shl_i', 1, 26)                         
  0xc4c22        ad d1              ('sub', 13, 26)                          r26L = 2 r26 - w = r26 + (r26 - w)  (zero 5.2 Hz)
  0xc4c24        c2 82              ('shl_i', 2, 16)                         displaced 0x29D76: 4 sp
  0xc4c26        ba 81              ('sub', 26, 16)                          displaced 0x29D78: E = 4 sp - r26
  0xc4c28        24 d7 42 95        ('ld_h', -27326, 4, 26)                  op = gp-0x6abe (fresh 1 kHz motor-rate EMA)        [D OPERAND]
  0xc4c2c        1a 46 c8 32        ('addi', 13000, 26, 8)                   Honda's validity form (FUN_0003f776): op + 13000
  0xc4c30        20 6e 90 65        ('movea', 26000, 0, 13)                  
  0xc4c34        ed 41              ('cmp', 13, 8)                           
  0xc4c36        e0 d7 36 d3        ('cmovh', 0, 26, 26)                     op + 13000 > 26000 unsigned (incl. the 0x7FFF sentinel): op := 0
  0xc4c3a        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v)]
  0xc4c3e        29 06 96 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v)]
  0xc4c44        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c48        ed 41              ('cmp', 13, 8)                           
  0xc4c4a        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c4c        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c50        b5 15              ('br', 'APPLY')                          
  0xc4c52 L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c56        ed 41              ('cmp', 13, 8)                           
  0xc4c58        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c5a        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c5e        a5 fd              ('br', 'L1')                             
  0xc4c60 SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c64        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c66        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c6a        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c6e        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c70        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c74        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c76 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        E * G (low word)                                 [THE SPEED GAIN]
  0xc4c7a        a8 82              ('sar_i', 8, 16)                         E' = (E G) >> 8
  0xc4c7c        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c80        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c84        ed 41              ('cmp', 13, 8)                           
  0xc4c86        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c88        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c8c        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c8e FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c90        b6 07 ee 50        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c94 DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c96 TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 1426, 954) (1843, 1689, -8761) (2304, 703, -1403) (2707, 565, 2987) (3571, 1195, 2959) (4032, 1528, 1551) (6198, 2348, 0) (65535, 2348, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails;** min exact GM 11.9 dB.
- **Envelope vs B0r: +19–20 % at 1–5 m/s, +17 % at 8, 0 … +7 % in the dip, +11–14 % at 15–30.**
- **Re(T/ω):** age 0 −0.80 … −0.87 at 5–10 Hz, −0.50 at 20 Hz; age 10 −1.29 at 5 Hz, −0.20 at 20 Hz.
- **Goal metric ≥ 0.962.** **Time:** the smallest step overshoot of the angle kind (12.1 % / 12.3 %), lurch 3.1° / 3.8°,
  dj 4 / 4, 0 hold slips; texture 1.0 / 1.7 counts.

### 3.4 What placement decides here (and the notch)

- **D2b vs D2c are different loops, not the same loop with a different T_ref.** The record's law ("placement decides
  transient authority, not the filter", V289) was for a filter that sees the whole error. Here the forward lead acts on P
  only, the I integrating the unled E′; the feedback lead acts on r26, so the I integrates the led error. On the θ path
  `C_θ(fwd) = −g·(Kp/256·Lf + Ki/32768/(1−z⁻¹))·r26` vs `C_θ(fb) = −g·(Kp/256 + Ki/32768/(1−z⁻¹))·Lf·r26`. The lead
  under the integrator costs phase at the I corner, hence D2b's +4–7 % envelope over D2c. **EVIDENCE** (model).
- **A forward lead on P AND I** (the cave returning E_L through the normal path, 4 bytes fewer than D2b) has exactly
  D2c's θ path and differs only on the setpoint path by Lf: that is the record's case — same margins, a ×2 setpoint kick.
  It is dominated by D2c (same loop, more authority on 0xE4 steps) and was not carried.
- **Transient authority, measured (step scenario, nominal, peak lane T):** 3 m/s D2b 2 171 / D2c 2 134 / B0r 1 978;
  8 m/s D2b 1 029 / D2c 861 / B0r 787; at ≥ 12.5 m/s all within ±7 %. Step overshoot D2b 15.8 % / D2c 12.1 % (max over
  speeds). **EVIDENCE** (sim).
- **The notch (the brief's other option) was not carried.** In an angle loop the crossover is 0.4–1.5 Hz; the 20 Hz
  content is the D term's, and the fresh D already gives 0.2–0.4× V295's 20 Hz anti-damping with L20 ≤ 0.70× V295's. A
  biquad costs two state words and ~40 bytes, and the record's only notch (V289) moved the ring to a pre-existing 16 Hz
  pole. Nothing in the gates asks for it. **BELIEF** (no notch was simulated).

---

## 4. Design D3 — cascade: angle P outside, the rate loop inside

### 4.0 The loop, and why it is an I-P structure

The literal request: "angle P outside, the EXISTING V282-style rate loop inside (rate feedback kept as the inner damping
with its 16.5 Hz lag, angle error forming the rate setpoint)". The x operand stays the RATE (no E1), E2 restores stock's
sum, a/b go back to stock (923/1560: DC 30.89, 16.5 Hz pole), and the cave turns the angle error into the rate setpoint:

```python
x     = gp-0x6a56 (D3a, held) | gp-0x6abe (D3b, E1' at 0x28F4C; the +-12000 bail now gates the 0x7FFF sentinel)
s_new = ((923 * s_old) >> 10) + ((1560 * x) >> 10) ; r26 = clamp(s_old + s_new, +-65535)      # 0x28F86..0x28FBC
th    = ld.h gp-0x6a00 ; e4 = sp69ae - (th << 2)  (0 if |th| > 12000: the -0x8000 baseline wrap)  # the cave
sp_r  = (e4 * G(v)) >> 6 ; E = (sp_r << 2) - r26  (D3a)  |  (sp_r << 2) + r26  (D3b: gp-0x6abe = -x/1.698)
I     = Honda's on E (Ki 12, frozen as C1) ; P = clamp((E * Kp) >> 8) ; D = 0 (Kd 0, DCL 0 as in V295)
```

**Why it is an I-P loop (EVIDENCE, arithmetic on the bytes):** Σₙ r26 = 30.89·Σₙ x = 30.89 × 8 × 1000·Δθ(deg) per degree of
travel, so the inner I state is `(Ki/32768)·Σ(4 sp_r) − 7.54·Ki·(θ − θ_engage)` S counts: a P on the MEASURED angle
(−90 S per degree at Ki 12) that the setpoint does not see, plus the integral of the outer error. At DC the integral wins
(no steady error); at 0.04–0.2 Hz the measurement-P holds the wheel back from the setpoint. That is the tracking cost the
goal metric reads, and the reason the releases are gentle (§6.4: the smallest lurch and step overshoot of all).

### 4.1 D3a — the V282-style held rate loop inside

- **Bytes: 199** (15 in-place: E2, B2, A2, E4, H, V1 — no E1, no D edit; 166 cave = 118 code + 48 table; 18 cal: a, b, C,
  DB, Ki, ICL, Kp×5). **No RAM.**

```
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   cal  0x0c63e8  f3 03        -> 9b 03         a 1011 -> 923                                        
   cal  0x0c63ea  1a 04        -> 18 06         b 1050 -> 1560                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 0c 00         Ki 0 -> 12                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0e5384  c0 03        -> 18 00         Kp record Y[0] 960 -> 24                             
   cal  0x0e5386  c0 03        -> 18 00         Kp record Y[1] 960 -> 24                             
   cal  0x0e5388  c0 03        -> 18 00         Kp record Y[2] 960 -> 24                             
   cal  0x0e538a  c0 03        -> 18 00         Kp record Y[3] 960 -> 24                             
   cal  0x0e538c  c0 03        -> 18 00         Kp record Y[4] 960 -> 24                             
   cave 0xc4c00..0xc4ca6: 166 bytes (118 code + 48 table)  sha256 81bc5052536a6c58
   FULL DIFF vs V295 over [0x13000, 0x100000): 197 bytes; changed bytes: in-place code 15, cal 18, cave 166 (its bytes that differ from 0xFF: 164); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D3a: cave at 0xc4c00: 166 bytes = 118 code (39 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      24 47 00 96        ('ld_h', -27136, 4, 8)                   th_h = gp-0x6a00 (0.1 deg)                       [OUTER angle error]
  0xc4c04        08 4e e0 2e        ('addi', 12000, 8, 9)                    validity form: th + 12000 <= 24000 unsigned
  0xc4c08        c2 42              ('shl_i', 2, 8)                          4 th
  0xc4c0a        a8 81              ('sub', 8, 16)                           e4 = gp-0x69ae - 4 th = 4 (th_sp - th)
  0xc4c0c        20 6e c0 5d        ('movea', 24000, 0, 13)                  
  0xc4c10        ed 49              ('cmp', 13, 9)                           
  0xc4c12        e0 87 36 83        ('cmovh', 0, 16, 16)                     |th| > 1200 deg (incl. the -0x8000 baseline wrap): e4 := 0  [ANGLE VALIDITY]
  0xc4c16        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v) on the OUTER gain]
  0xc4c1a        29 06 76 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v) on the OUTER gain]
  0xc4c20        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c24        ed 41              ('cmp', 13, 8)                           
  0xc4c26        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c28        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c2c        b5 15              ('br', 'APPLY')                          
  0xc4c2e L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c32        ed 41              ('cmp', 13, 8)                           
  0xc4c34        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c36        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c3a        a5 fd              ('br', 'L1')                             
  0xc4c3c SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c40        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c42        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c46        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c4a        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c4c        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c50        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c52 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        e4 * G                                           [the OUTER angle P]
  0xc4c56        a6 82              ('sar_i', 6, 16)                         sp_r = (e4 G) >> 6  (ka = 4)
  0xc4c58        c2 82              ('shl_i', 2, 16)                         4 sp_r (the displaced shl 2)
  0xc4c5a        ba 81              ('sub', 26, 16)                          E = 4 sp_r - r26 (held rate, x = gp-0x6a56)     [the INNER rate error]
  0xc4c5c        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c60        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c64        ed 41              ('cmp', 13, 8)                           
  0xc4c66        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c68        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c6c        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c6e FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c70        b6 07 0e 51        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c74 DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c76 TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 993, 203) (1843, 1049, -2372) (2304, 782, -2571) (2707, 529, 2067) (3571, 965, 2994) (4032, 1302, 1677) (6198, 2189, 0) (65535, 2189, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **Inner gain is capped by the held operand:** Kp_in 40–46 FAILS the gates at almost every speed (round 1/2: b_lo+h10,
  J_lo+h10 at low speed); Kp 24 passes. This is V282's lesson, re-measured on the credible set.
- **GATE 2: 0 fails; min exact GM 6.3 dB** (b_lo×tau6+h10, 7.75 m/s) — the thinnest of all; T530 −0.7 dB.
- **Envelope vs B0r: −29 … −38 % at 1–8 m/s**, −6 … −23 % at 10–19 m/s, −9 … −13 % at 22–30 m/s.
- **Re(T/ω): the worst 5–13 Hz anti-damping of all** (age 0 −1.55 … −1.66, age 10 −2.49 at 5 Hz): the 16.5 Hz fb pole and
  the hold sit in the inner loop's own phase.
- **Goal metric 0.913 at 11.9 m/s — FAILS 0.95** (0.914–0.945 at 12.5–19 m/s). `ds_d3_tune.py`: Ki 24 makes it worse (0.837).
- **Time:** the smallest firm-release lurch (2.8° / 1.7°) and step overshoot (8.9 %), the largest dj count at 3–5 m/s
  (8 / 8) and dj 4 at 8–12.5 m/s on bc; tracking fit gain 0.81–0.98 at 0.2 Hz, 0.52–0.91 at 0.5 Hz.
- **Verdict on its own terms:** the existing rate loop inside an angle loop is gentle and slow; it fails the goal's tracking
  criterion and has the thinnest margins. Not recommended by its own numbers.

### 4.2 D3b — a fresh inner operand

- **Bytes: 200** (16 in-place: E1′ is ONE byte at `0x28F4E` (`aa → 42`), + E2, B2, A2, E4, H, V1; 166 cave; 18 cal). **No RAM.**

```
   code 0x028f4c  24 3f aa 95  -> 24 3f 42 95   ld.h -0x6a56[gp],r7 -> ld.h -0x6abe[gp],r7           operand x := gp-0x6abe (FRESH motor-rate EMA; the +-12000 bail now gates it)
   code 0x028fa4  89 d1        -> c9 d1         subr r9,r26 -> add r9,r26                            r26 = s_old + s_new (stock's sum)
   code 0x029a50  e2 47 00 00  -> e0 df 34 43   setfe r8 -> cmovne r0,r27,r8                         r8 := (request == 1) ? bVar2 : 0
   code 0x029a56  da 05        -> b2 05         bne 0x29A60 -> be 0x29A5C                            PID runs iff ramp != 0 AND r8 != 0
   code 0x029d6a  08 80 ed 80  -> 24 87 52 96   mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16    sp := gp-0x69ae
   code 0x029d76  c2 82 ba 81  -> 89 37 8a ae   shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6           the hook
   code 0x01310d  30           -> 41            F181 '39990-TVA,A160' -> '...,A16A'                  the fork interlock (C1 rev 2's V1)
   cal  0x0c63e8  f3 03        -> 9b 03         a 1011 -> 923                                        
   cal  0x0c63ea  1a 04        -> 18 06         b 1050 -> 1560                                       
   cal  0x0c62e6  00 04        -> ff ff         C 1024 -> 65535                                      
   cal  0x0c62e4  04 00        -> 00 00         DB 4 -> 0                                            
   cal  0x0c63e6  00 00        -> 0c 00         Ki 0 -> 12                                           
   cal  0x0c61ba  00 28        -> 00 10         ICL 10240 -> 4096                                    
   cal  0x0e5384  c0 03        -> 2e 00         Kp record Y[0] 960 -> 46                             
   cal  0x0e5386  c0 03        -> 2e 00         Kp record Y[1] 960 -> 46                             
   cal  0x0e5388  c0 03        -> 2e 00         Kp record Y[2] 960 -> 46                             
   cal  0x0e538a  c0 03        -> 2e 00         Kp record Y[3] 960 -> 46                             
   cal  0x0e538c  c0 03        -> 2e 00         Kp record Y[4] 960 -> 46                             
   cave 0xc4c00..0xc4ca6: 166 bytes (118 code + 48 table)  sha256 f642cf4ca39a6081
   FULL DIFF vs V295 over [0x13000, 0x100000): 198 bytes; changed bytes: in-place code 16, cal 18, cave 166 (its bytes that differ from 0xFF: 164); UNLISTED: none
   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block, and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)
```

```
D3b: cave at 0xc4c00: 166 bytes = 118 code (39 instructions) + 48 table (8 rows incl. the 0xFFFF row)
  0xc4c00 C      24 47 00 96        ('ld_h', -27136, 4, 8)                   th_h = gp-0x6a00 (0.1 deg)                       [OUTER angle error]
  0xc4c04        08 4e e0 2e        ('addi', 12000, 8, 9)                    validity form: th + 12000 <= 24000 unsigned
  0xc4c08        c2 42              ('shl_i', 2, 8)                          4 th
  0xc4c0a        a8 81              ('sub', 8, 16)                           e4 = gp-0x69ae - 4 th = 4 (th_sp - th)
  0xc4c0c        20 6e c0 5d        ('movea', 24000, 0, 13)                  
  0xc4c10        ed 49              ('cmp', 13, 9)                           
  0xc4c12        e0 87 36 83        ('cmovh', 0, 16, 16)                     |th| > 1200 deg (incl. the -0x8000 baseline wrap): e4 := 0  [ANGLE VALIDITY]
  0xc4c16        e4 47 a3 95        ('ld_hu', -27230, 4, 8)                  v = gp-0x6a5e (64 counts per km/h)            [G(v) on the OUTER gain]
  0xc4c1a        29 06 76 4c 0c 00  ('mov_i32', 'TBL', 9)                    r9 -> table                                     [G(v) on the OUTER gain]
  0xc4c20        e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X0
  0xc4c24        ed 41              ('cmp', 13, 8)                           
  0xc4c26        cb 05              ('bh', 'L1')                             v > X0 (unsigned): walk
  0xc4c28        e9 47 03 00        ('ld_hu', 2, 9, 8)                       G = G0 (clamp low)
  0xc4c2c        b5 15              ('br', 'APPLY')                          
  0xc4c2e L1     e9 6f 07 00        ('ld_hu', 6, 9, 13)                      X(i+1)
  0xc4c32        ed 41              ('cmp', 13, 8)                           
  0xc4c34        c3 05              ('bnh', 'SEG')                           v <= X(i+1): segment i
  0xc4c36        09 4e 06 00        ('addi', 6, 9, 9)                        next row (the 0xFFFF row ends the walk)
  0xc4c3a        a5 fd              ('br', 'L1')                             
  0xc4c3c SEG    e9 6f 01 00        ('ld_hu', 0, 9, 13)                      X(i)
  0xc4c40        ad 41              ('sub', 13, 8)                           dv = v - X(i)
  0xc4c42        29 6f 04 00        ('ld_h', 4, 9, 13)                       S(i), Q12, signed
  0xc4c46        ed 47 20 02        ('mul', 13, 8, 0)                        dv * S(i) (low word)
  0xc4c4a        ac 42              ('sar_i', 12, 8)                         >> 12
  0xc4c4c        e9 6f 03 00        ('ld_hu', 2, 9, 13)                      G(i)
  0xc4c50        cd 41              ('add', 13, 8)                           G = G(i) + ((v - X(i)) * S(i) >> 12)
  0xc4c52 APPLY  e8 87 20 02        ('mul', 8, 16, 0)                        e4 * G                                           [the OUTER angle P]
  0xc4c56        a6 82              ('sar_i', 6, 16)                         sp_r = (e4 G) >> 6  (ka = 4)
  0xc4c58        c2 82              ('shl_i', 2, 16)                         4 sp_r (the displaced shl 2)
  0xc4c5a        da 81              ('add', 26, 16)                          E = 4 sp_r + r26 (fresh gp-0x6abe = -x/1.698)   [the INNER rate error]
  0xc4c5c        e4 47 99 b0        ('ld_hu', -20328, 4, 8)                  |driver torque| gp-0x4f68                       [I FREEZE on the hand]
  0xc4c60        20 6e 00 02        ('movea', 512, 0, 13)                    THR = 512
  0xc4c64        ed 41              ('cmp', 13, 8)                           
  0xc4c66        cb 05              ('bh', 'FRZ')                            |tq| > THR (unsigned): freeze
  0xc4c68        ce 6e 00 80        ('andi', 32768, 14, 13)                  r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]
  0xc4c6c        ca 05              ('bne', 'DONE')                          ramp full: integrate
  0xc4c6e FRZ    00 32              ('mov_i5', 0, 6)                         r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged
  0xc4c70        b6 07 0e 51        ('jr', 171390)                           return past 0x29D7A/0x29D7C
  0xc4c74 DONE   66 00              ('jmp', 6)                               return to 0x29D7A
  0xc4c76 TBL    ca 02              ('half', 714)                            table: X u16, G u16, S s16 Q12 per row
  table rows: (714, 851, 453) (1843, 976, -2888) (2304, 651, -2002) (2707, 454, 1555) (3571, 782, 1821) (4032, 987, 1095) (6198, 1566, 0) (65535, 1566, 0)
  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs (sentinels, table edges, validity edges, first-tick, register file): 0 mismatches
```

- **GATE 2: 0 fails;** min exact GM 8.9 dB; **T530 +0.2 dB (the highest of all, under the +3 dB bar)**.
- **Envelope vs B0r: +11–17 % at ≤ 8 m/s, +52 % at 10, +38 % at 11.75, +32 % at 12.5, +18–21 % at 15–22, +26 % at
  26.9–30 — the highest of all at 10–13 m/s**, where every angle-kind design is pinned by ms_free.
- **Re(T/ω):** age 0 −1.43 … −1.48 at 5–7 Hz, −0.73 at 20 Hz (0.89× V295); age 10 −1.69 at 5 Hz, −0.55 at 20 Hz.
- **Goal metric 0.894–0.949 at 10–19 m/s — FAILS 0.95.** Raising Ki does not rescue it (§4.3).
- **Time:** the smallest step overshoot (1.2 %), lurch 2.5° / 1.5–3.1°; tracking fit gain 0.73–0.90 at 0.2 Hz — the worst.
- **light_b (the prior, report only): PM 1.4° at 26.9 m/s, a 4.4 Hz ring with ζ 0.010** — the cascade is the structure most
  exposed to the prior's light damping (D3a: PM 0.7°). R3 covers the band (§5).

### 4.3 Can the cascade meet the goal's tracking metric? (`ds_d3_tune_out.txt`)

Each (Kp, Ki) at its own gated envelope; the goal metric is the minimum over the tracking members at 0.96× that envelope, speeds 8–27 m/s:

```
D3 fresh Kp46 Ki12       T/deg@env 3: 66 8: 75 10: 51 11.9: 35 12.5: 47 15: 58 17: 73 19: 83 22: 97 27:119 | goal min >=8 m/s 0.969 0.952 0.899 0.919 0.900 0.898 0.920 0.957 0.974 | worst 0.898  [10s]
D3 fresh Kp40 Ki20       T/deg@env 3: 53 8: 63 10: 33 11.9: 22 12.5: 30 15: 43 17: 57 19: 65 22: 76 27: 93 | goal min >=8 m/s 0.990 0.967 0.916 0.942 0.940 0.942 0.956 0.979 0.988 | worst 0.916  [18s]
D3 fresh Kp40 Ki28       T/deg@env 3: 43 8: 54 10: 25 11.9: 16 12.5: 22 15: 35 17: 47 19: 54 22: 63 27: 78 | goal min >=8 m/s 0.993 0.965 0.903 0.938 0.948 0.953 0.965 0.984 0.992 | worst 0.903  [27s]
D3 fresh Kp32 Ki24       T/deg@env 3: 32 8: 46 10: 21 11.9: 14 12.5: 20 15: 31 17: 43 19: 49 22: 58 27: 69 | goal min >=8 m/s 0.993 0.965 0.904 0.939 0.947 0.953 0.966 0.985 0.992 | worst 0.904  [35s]
D3 fresh Kp46 Ki32       T/deg@env 3: 47 8: 56 10: 26 11.9: 16 12.5: 24 15: 37 17: 51 19: 58 22: 67 27: 83 | goal min >=8 m/s 0.992 0.965 0.903 0.939 0.950 0.955 0.966 0.985 0.992 | worst 0.903  [44s]
D3 fresh Kp24 Ki12       T/deg@env 3: 39 8: 52 10: 28 11.9: 19 12.5: 26 15: 35 17: 49 19: 56 22: 66 27: 81 | goal min >=8 m/s 0.988 0.965 0.913 0.939 0.927 0.934 0.950 0.976 0.987 | worst 0.913  [53s]
D3 fresh Kp24 Ki24       T/deg@env 3: 18 8: 32 10: 15 11.9: 10 12.5: 14 15: 23 17: 33 19: 38 22: 44 27: 53 | goal min >=8 m/s 0.993 0.961 0.893 0.935 0.947 0.958 0.969 0.987 0.993 | worst 0.893  [63s]
D3 fresh Kp16 Ki16       T/deg@env 3: 12 8: 27 10: 14 11.9:  9 12.5: 14 15: 21 17: 31 19: 35 22: 42 27: 42 | goal min >=8 m/s 0.993 0.965 0.911 0.943 0.948 0.957 0.969 0.987 0.991 | worst 0.911  [72s]
D3 held Kp24 Ki12        T/deg@env 3: 40 8: 41 10: 32 11.9: 21 12.5: 30 15: 37 17: 49 19: 58 22: 69 27: 87 | goal min >=8 m/s 0.974 0.965 0.913 0.940 0.923 0.928 0.947 0.976 0.987 | worst 0.913  [81s]
D3 held Kp24 Ki24        T/deg@env 3: 26 8: 28 10: 16 11.9:  9 12.5: 14 15: 20 17: 30 19: 36 22: 44 27: 56 | goal min >=8 m/s 0.982 0.946 0.837 0.912 0.919 0.939 0.958 0.983 0.992 | worst 0.837  [89s]
D3 held Kp16 Ki16        T/deg@env 3: 19 8: 30 10: 15 11.9:  9 12.5: 14 15: 20 17: 30 19: 35 22: 42 27: 51 | goal min >=8 m/s 0.991 0.956 0.882 0.928 0.932 0.949 0.964 0.984 0.992 | worst 0.882  [98s]
```

**No point reaches 0.95 at 10–11.9 m/s; the best worst-case is 0.916 (fresh, Kp 40 / Ki 20, at the price of the envelope).** Raising Ki strengthens the measurement-P (−7.5·Ki S per degree) as fast as the error integral, so the I-P lag at 0.04–0.2 Hz does not close. **EVIDENCE** (model): the cascade cannot meet the goal's tracking metric on this credible set at any scanned gain.

### 4.4 Through the map path (evaluated, not carried)

**D3c = the cascade with the angle error entering THROUGH the map path** (a cave at `0x29032`, replacing
`ld.h -0x69ae[gp],r13`, returning a scaled error in r13; LIM, the driver-torque setpoint taper, the 8-bit idx, the map and the
idx-keyed Kp/Kd stay). Evaluated, not carried:
- **Its linear loop is D3a's / D3b's** with ka·G replaced by the map's slope, so its envelope, 20 Hz numbers and the I-P
  tracking failure are theirs (§4.1–4.3). **EVIDENCE** (the chain is a static gain at small signal: tracer `setpoint_chain`).
- **What it adds:** the outer error is quantised to one idx per 64.5 r22 counts (≥ 0.1° per idx only if the cave scales the
  error ×16, which limits the outer range to ±24° before idx saturates at 240 = a constant-rate slew); Kp/Kd become
  keyed on |angle error| (a cal-only nonlinear gain the direct path lacks); **the setpoint taper (`0xCB924`/`0xCB8B4`, flat
  to |tq|>>5 = 80, zero at 112) would fade the OUTER error under the driver's hand — a release by construction**, which
  is the one property worth carrying to C2.
- **Why not carried:** it inherits the cascade's tracking failure, needs a new hook site, and its liveness is not traced.
  From the Ghidra listing of `0x28FC8..0x2906F`, r7, r8, r12 and r14 are written before being read after `0x29032`
  (candidates for the link and scratch) — **BELIEF until a liveness trace on the full function**.

---

## 5. Pre-declared misses, revert signatures, hazards and instruments

### 5.1 Pre-declared misses (each with its band and predicted size; every number from §6)

Common to every candidate (the class C1r2 declared, re-measured here on each structure):

| goal criterion | band | B0r | D1b | D2a | D2b | D2c | D3b | basis |
|---|---|---|---|---|---|---|---|---|
| low-speed stick-slip gone; dwell-then-jump ≤ V282 | 3–5 m/s | dj 7 / 7 per scenario set, stick 9.3 % | 5 / 9, 9.0 % | 6 / 7, 9.0 % | 4 / 4, 7.8 % | 4 / 4, 8.2 % | 4 / 6, 9.7 % | sim nominal / bc; V282 not simulable |
| release after a LIGHT hand (below the 512 freeze threshold) | 3–30 m/s | 5.9° / 6.5° | 6.3° / 6.9° | 6.3° / 6.8° | 6.2° / 6.5° | 5.7° / 6.0° | 4.6° / 5.3° | sim, max over speeds |
| engage under a handed-over load | 3–30 m/s | droop 4.7° / 5.2° | 4.6° / 5.2° | 4.7° / 5.2° | 4.1° / 4.4° | 4.2° / 4.6° | 4.2° / 4.7° | sim, max |
| tracking faster than the goal metric (0.2 Hz) | 12.5–19 m/s | 0.90–0.95 harness gain, phase −23…−25° | 0.92–0.95 | 0.92–0.95 | 0.94–0.97 | 0.88–0.94 | **0.68** | sim s02 |
| highway hold slips under road disturbance | 15–30 m/s | 3 | 3 | 3 | 0 | 0 | 0 | sim rh |

Candidate-specific (FAILs of a goal criterion, declared now):
- **D1a:** goal metric 0.944 at 11.9 m/s; texture 2.5 counts (5–30 Hz) and 26.8 counts (40–200 Hz); release lurch up to
  20.5° (bc); step overshoot up to 42 %.
- **D1c:** texture 5.4 counts rms in holds (> 2.0).
- **D3a:** goal metric 0.913–0.945 at 11.9–19 m/s; min exact GM 6.3 dB.
- **D3b:** goal metric 0.894–0.949 at 10–19 m/s.
- **Report members below 30° (not gated, the brief's set excludes them):** the factorial's b/1.9 and b_lo × J_hi2 / J1.0 ×
  tau6 (+h10) cells at 1–2 m/s and b_q×J1.3(+h10) at 15.5–15.75 m/s ring at **0.9–2.1 Hz with ζ ≥ 0.085**; light_b rings
  at **3.7–4.4 Hz** (ζ 0.08 D1b/D2a … 0.005 D3a). No point of any member is unstable.

### 5.2 Revert signatures (written before any build)

C1r2's R1–R9 apply to every candidate unchanged (inverted, rail hands-off, a new 5–30 Hz line, ring presence > 0.5 % or
F7 > 0, |θ−θ_sp| > 10° hands-off, request-drop push, STEER_STATUS ≠ 0, the operator's words), with **R3 widened to every
speed: an oscillation in 0.8–5.5 Hz in 0x14A or the 0x18F rate that grows or shows ≥ 4 visible cycles above twice the
pre-event rms (ζ < 0.10)** — it covers every sub-30° report member above (0.9–2.1 Hz) and light_b (3.7–4.4 Hz). Added per
structure:

| id | added revert signature | why |
|---|---|---|
| D1a | the operator's "buzz/fizz" on a straight; any 0x18F rate content at 40–50 Hz (aliased 100 Hz) | the 100 Hz D impulse train |
| D1b | a single-frame tap spike ≥ 30 counts coincident with a request-bit glitch or a baseline (re-reference) event | the stale `d_prev` one-tick D |
| D2a | none beyond R1–R9 | — |
| D2b | a tap kick ≥ 2× the P step on a fork setpoint step, ringing at 8–12 Hz | the forward lead on 0xE4 steps |
| D2c | none beyond R1–R9 | — |
| D3a, D3b | turn-in lag: abs(θ_sp − θ) > 3° for > 1 s at > 12.5 m/s in a ≤ 0.2 Hz manoeuvre | the I-P tracking miss, measured |

### 5.3 Hazards

| hazard | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|
| 0xE4 fault sentinel 0x7FFF | A2 (sim: 0.00° push every speed) | same | same | same | same | same | same | same | 0.01° on bc |
| invalid motor rate (gp-0x6abe = 0x7FFF) | held x → 0 (FUN_0003f776) | — | — | — | **cave validity → op 0** | same | same | held x → 0 | **±12000 bail → STEER_STATUS 7 latch** (fail-safe, LKAS off) |
| angle baseline wrap (−0x8000) | ±12000 bail on θ | same | same | same | same | same | same | **cave e4 := 0** (x bail tests the rate) | same |
| stale cave RAM after skips | none | none | one tick ≤ DCL × ramp | first tick lp := 0 | none | first tick w := E′ | first tick w := r26 | none | none |
| `gp-0x6cc4` re-reference (`FUN_0003bcb2`) while engaged | — | — | one tick ≤ DCL | — | — | — | — | — | — |
| abs(θ) > 409.6° (r26 clamp) | P wrong | same | same | P and D wrong | P wrong | same | same | — (rate) | — |
| setpoint-step authority | ×1 | **D kick, DCL-clipped** | ×1 | ×1 | ×1 | **×2 on P, 16 ms** | ×1 | ×1 (I-P) | ×1 (I-P) |
| camera 0xE4 on a relay close, torque fork on the angle image, fork crash 0.51 s hold | C1r2 §2.10 / M12 apply to every candidate unchanged | | | | | | | | |

### 5.4 The instrument that proves each one live in one short drive

Every candidate is observable with signals already on the wire (0xE4 θ_sp, 0x14A θ, 0x18F rate and driver torque, the
427 tap T = gp-0x6b38, the F181 string). The regression is C1r2 §6.1's
`tap = c_P·e + c_I·∫e + c_D·ω + c0` on hands-off windows, extended per structure so that each candidate has a coefficient
no other candidate has (tap units: counts of T/8; e in 0.1° counts; ω in deg/s):

| id | LIVE (in addition to carFw `39990-TVA,A16A`, c_P(v) within ±30 % of `Kp_eff(v)/800`, the dip at 10–12.5 m/s) | NOT LIVE / wrong image | decides |
|---|---|---|---|
| B0r, D2a, D1b | c_D ∈ [0.30, 0.50] tap per deg/s, flat in speed; c on the SETPOINT rate ≈ 0 | c_D ≈ 0 (no D) or c_sp > 0.1 (D on E) | D on a rate operand present |
| D1a | c_D ∝ G(v): 0.53 at ≤ 8 m/s → 0.16 at 11.75 m/s; **c on θ̇_sp equal to c_D** (D on error) | flat c_D | the cal-only D |
| D1b vs D2a vs B0r (fresh vs held operand) | **static, not runtime: the operand address is in the image (H5 decodes `0x29EE0` and the cave's load).** No one-drive wire test separates a 5.5 ms operand lag behind the 5 Hz output lag (BELIEF: ~10° at 5 Hz, below what 15–30 s of road excitation resolves) | — | the image check |
| D2b | a regressor on the error RATE (setpoint and measurement together): c_ė / c_P = 15 ms (the lead time kh(1−β)/β·1 ms) | c_ė ≈ 0 | the forward lead |
| D2c | c on θ̇ (measurement only) = c_P·15 ms + c_D, **c on θ̇_sp ≈ 0** | — | the feedback lead (placement) |
| D3a, D3b | a regressor on the measured angle travel since engage: c_θ = −0.0151·Ki tap per 0.1° = **−0.18 tap per 0.1° at Ki 12** (the I-P term: 7.54·Ki S per degree × 0.160 T per S ÷ 8) | c_θ ≈ 0 | the cascade |

The lead state w (D2b/D2c) and d_prev/lp (D1b/D1c) are runtime states with no tap of their own; each one's effect is the
coefficient in the table, sized against its own operand. **BELIEF** that 15–30 s of hands-off frames in two speed bands
resolve c_ė and c_θ (the C1r2 page's exposure request: one stretch > 22 m/s, one at 12.5–15 m/s, one at 5–10 m/s).

---

## 6. The tables (generated by `ds_report.py` from the result files; nothing typed by hand)

### Time-domain gates condensed (nominal / bc); speeds 3 5 8 10 12.5 15 19 26 30 m/s

| id | dj events 3-5 m/s (s02+s05+ssm) | dj 8-12.5 | dj 15-30 | stick % 3 m/s | hold slips 15-30 (rh) | turn-hold min >= 8 | s02 fit gain >= 8 (min-max) | s05 fit gain >= 8 (min-max) | step overshoot % max | lurch firm deg max | lurch light 400 max | light 1000 max | engage droop max | sentinel push deg (toward the sentinel, max) | T 5-30 Hz rms max (holds) | T 40-200 Hz rms max (s05) | detector max frac / reversals | int32 wraps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 7 / 8 | 0 / 0 | 0 / 0 | 9.65 / 10.3 | 3 / 0 | 0.99 / 0.99 | 0.93-1.01 / 0.91-0.99 | 0.74-1.07 / 0.73-1.03 | 16.86 / 13.88 | 4.61 / 4.85 | 5.4 / 6.07 | 4.59 / 4.8 | 5.28 / 5.8 | 0 / 0 | 0.6 / 0.62 | 0.63 / 0.64 | 0.209/0 / 0.222/0 | 0 / 0 |
| B0r | 7 / 7 | 0 / 0 | 0 / 0 | 9.26 / 9.65 | 3 / 0 | 0.99 / 0.99 | 0.93-1.01 / 0.91-0.99 | 0.73-1.06 / 0.72-1.03 | 15.63 / 17.19 | 4 / 5.19 | 5.88 / 6.51 | 3.98 / 5.65 | 4.67 / 5.21 | 0 / 0 | 0.66 / 0.69 | 0.78 / 0.78 | 0.211/0 / 0.225/0 | 0 / 0 |
| D1a | 4 / 4 | 0 / 1 | 0 / 0 | 8.21 / 8.6 | 1 / 0 | 1 / 0.98 | 0.91-0.98 / 0.88-0.95 | 0.66-0.97 / 0.65-0.94 | 21.63 / 42.1 | 9.6 / 18.61 | 10.55 / 20.54 | 10.54 / 20.49 | 4.58 / 4.96 | 0 / 0 | 2.53 / 2.58 | 26.76 / 26.6 | 0.211/0 / 0.226/0 | 0 / 0 |
| D1b | 5 / 9 | 0 / 0 | 0 / 0 | 9 / 9.52 | 3 / 0 | 0.99 / 0.99 | 0.94-1.01 / 0.92-0.99 | 0.76-1.07 / 0.75-1.03 | 16.4 / 20.5 | 4.18 / 6.04 | 6.3 / 6.88 | 4.18 / 6.51 | 4.6 / 5.17 | 0 / 0 | 0.64 / 0.65 | 0.78 / 0.79 | 0.211/0 / 0.226/0 | 0 / 0 |
| D1c | 4 / 4 | 0 / 5 | 0 / 0 | 9.26 / 9.91 | 4 / 0 | 1 / 0.99 | 0.95-1.05 / 0.92-0.99 | 0.68-1.06 / 0.67-1.03 | 16.15 / 16.41 | 4.19 / 5.03 | 6.16 / 6.84 | 4.16 / 5.94 | 4.45 / 4.94 | 0 / 0 | 5.4 / 3.86 | 4.21 / 4.17 | 0.211/0 / 0.225/0 | 0 / 0 |
| D2a | 6 / 7 | 0 / 0 | 0 / 0 | 9 / 9.78 | 3 / 0 | 0.99 / 0.99 | 0.94-1.01 / 0.92-0.99 | 0.76-1.07 / 0.74-1.03 | 16.19 / 19.62 | 4.12 / 5.72 | 6.29 / 6.78 | 4.11 / 6.16 | 4.66 / 5.2 | 0 / 0 | 0.67 / 0.68 | 0.76 / 0.77 | 0.211/0 / 0.225/0 | 0 / 0 |
| D2b | 4 / 4 | 0 / 0 | 0 / 0 | 7.82 / 8.6 | 0 / 0 | 0.99 / 0.99 | 0.95-1.01 / 0.93-0.98 | 0.78-1.07 / 0.76-1.02 | 15.79 / 15.21 | 3.2 / 4.12 | 6.16 / 6.54 | 3.19 / 4.88 | 4.14 / 4.43 | 0 / 0 | 1.02 / 1.06 | 1.83 / 1.82 | 0.211/0 / 0.224/0 | 0 / 0 |
| D2c | 4 / 4 | 0 / 0 | 0 / 0 | 8.21 / 8.87 | 0 / 0 | 0.99 / 0.97 | 0.91-0.99 / 0.87-0.97 | 0.75-1.04 / 0.74-1.01 | 12.06 / 12.32 | 3.14 / 3.77 | 5.66 / 5.99 | 3.13 / 4.52 | 4.16 / 4.58 | 0 / 0 | 0.98 / 1.67 | 1.34 / 1.33 | 0.210/0 / 0.225/0 | 0 / 0 |
| D3a | 8 / 8 | 0 / 4 | 0 / 0 | 10.17 / 10.82 | 0 / 0 | 0.99 / 0.98 | 0.83-0.98 / 0.81-0.94 | 0.52-0.91 / 0.52-0.87 | 8.92 / 1.26 | 2.81 / 1.71 | 4.58 / 4.65 | 2.59 / 1.77 | 5.48 / 5.84 | 0 / 0 | 0.48 / 0.53 | 0.52 / 0.52 | 0.189/0 / 0.206/0 | 0 / 0 |
| D3b | 4 / 6 | 0 / 0 | 0 / 0 | 9.65 / 10.04 | 0 / 0 | 0.97 / 0.96 | 0.74-0.90 / 0.73-0.89 | 0.52-0.85 / 0.52-0.84 | 1.22 / 0.47 | 2.53 / 1.52 | 4.6 / 5.26 | 2.47 / 3.09 | 4.22 / 4.67 | 0 / 0.01 | 0.89 / 0.93 | 0.82 / 0.82 | 0.210/0 / 0.225/0 | 0 / 0 |


### What each structure buys: the angle stiffness of the FITTED table (T counts per degree of error at DC, P path), and the envelope it sits under

| id | 1 | 3.1 | 5 | 8 | 10 | 11.75 | 12.5 | 15 | 17 | 19 | 22 | 26.9 | 30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 41 | 41 | 47 | 57 | 37 | 31 | 34 | 44 | 56 | 64 | 74 | 89 | 89 |
| B0r | 52 | 52 | 56 | 63 | 31 | 24 | 28 | 44 | 57 | 65 | 75 | 90 | 90 |
| D1a | 58 | 58 | 58 | 58 | 28 | 17 | 25 | 49 | 57 | 58 | 58 | 58 | 58 |
| D1b | 53 | 53 | 59 | 67 | 28 | 24 | 29 | 46 | 60 | 69 | 78 | 94 | 94 |
| D1c | 51 | 51 | 55 | 62 | 30 | 24 | 28 | 43 | 55 | 64 | 73 | 89 | 89 |
| D2a | 52 | 52 | 58 | 67 | 27 | 23 | 29 | 46 | 60 | 68 | 78 | 93 | 93 |
| D2b | 66 | 66 | 71 | 79 | 28 | 25 | 31 | 51 | 67 | 77 | 89 | 108 | 108 |
| D2c | 62 | 62 | 67 | 74 | 31 | 25 | 30 | 49 | 63 | 73 | 84 | 103 | 103 |
| D3a | 37 | 37 | 38 | 39 | 29 | 20 | 23 | 34 | 46 | 54 | 65 | 82 | 82 |
| D3b | 61 | 61 | 65 | 70 | 47 | 33 | 37 | 53 | 67 | 78 | 91 | 113 | 113 |

| id (envelope binding member at 3.1 / 11.75 / 17 / 26.9 m/s) | 3.1 | 11.75 | 17 | 26.9 |
|---|---|---|---|---|
| B0 | J_hi | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| B0r | J_hi | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D1a | RULE M20/Re20 | ms_free | RULE M20/Re20 | RULE M20/Re20 |
| D1b | J_hi | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D1c | b_lo*J_hi+h10 | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D2a | J_hi | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D2b | b_lo*J_hi+h10 | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D2c | b_lo*J_hi+h10 | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D3a | b_lo*tau6+h10 | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |
| D3b | b_lo | ms_free | b_q*J1.0+h10 | b_q*J1.0+h10 |

### GATE 2, full grid (1-35 m/s at 0.25 + the plant knots, 145 speeds), every member: min PM (deg) and the speed

Tier A bar 45 deg, tier B bar 30 deg; `+h10` = slot 4 ten ticks late (hold ages 11-20).  **bold** = below the bar.

| member | tier | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | A | 67.6 (26.9) | 64.8 (1) | 69.9 (26.9) | 64.5 (1) | 65.0 (1) | 64.9 (1) | 65.6 (1) | 65.4 (1) | 71.0 (1) | 65.2 (1) |
| J_lo | A | 66.0 (26.9) | 65.9 (27) | 67.8 (26.9) | 65.8 (27) | 66.0 (26.9) | 65.8 (27) | 68.0 (26.9) | 69.5 (26.9) | 71.6 (27) | 75.9 (1) |
| J_hi | A | 52.3 (1) | 47.0 (1) | 52.3 (1) | 46.3 (1) | 47.4 (1) | 46.7 (1) | 47.8 (1) | 48.2 (1) | 57.4 (1) | 55.9 (1) |
| b_lo | A | 62.5 (8) | 55.5 (1) | 59.0 (1) | 57.1 (1) | 54.1 (1) | 56.8 (8) | 51.3 (8) | 51.6 (8) | 54.1 (1) | 47.6 (6.75) |
| b_hi | A | 57.7 (26.9) | 57.7 (26.9) | 58.9 (26.9) | 57.7 (26.9) | 57.8 (26.9) | 57.7 (26.9) | 59.3 (26.9) | 60.9 (26.9) | 63.1 (27) | 79.2 (1) |
| tau0 | A | 68.0 (26.9) | 66.0 (1) | 70.2 (26.9) | 65.6 (1) | 66.1 (1) | 66.0 (1) | 67.1 (1) | 66.9 (1) | 72.3 (1) | 66.9 (1) |
| tau6 | A | 66.7 (26.9) | 62.5 (1) | 68.8 (1) | 62.2 (1) | 62.6 (1) | 62.7 (1) | 62.7 (1) | 62.4 (1) | 68.4 (1) | 61.7 (1) |
| mode13 | A | 67.6 (26.9) | 64.8 (1) | 69.9 (26.9) | 64.4 (1) | 64.9 (1) | 64.8 (1) | 65.5 (1) | 65.2 (1) | 70.9 (1) | 65.0 (1) |
| mode20 | A | 67.6 (26.9) | 64.8 (1) | 69.9 (26.9) | 64.5 (1) | 64.9 (1) | 64.9 (1) | 65.6 (1) | 65.3 (1) | 71.0 (1) | 65.1 (1) |
| ms_free | A | **32.8 (11.9)** | 47.6 (9) | 48.1 (10.5) | 47.7 (8.75) | 48.4 (9) | 47.6 (8.75) | 47.8 (8.75) | 47.2 (9) | 47.2 (11.9) | 47.7 (10.5) |
| b_lo*J_hi | B | 44.7 (8) | 37.3 (1) | 42.8 (1) | 36.9 (1) | 37.6 (1) | 37.4 (1) | 37.2 (1) | 37.3 (1) | 45.1 (1) | 41.1 (8) |
| b_lo*tau6 | B | 59.1 (8) | 52.4 (1) | 55.3 (1) | 54.1 (1) | 50.6 (8) | 53.1 (8) | 46.9 (8) | 47.2 (8) | 50.5 (1) | 42.9 (7.75) |
| J1.0 | B | 43.5 (1) | 39.3 (1) | 42.6 (1) | 38.6 (1) | 39.8 (1) | 39.0 (1) | 39.5 (1) | 40.7 (1) | 52.3 (1) | 55.8 (1) |
| b_q | B | 70.7 (1) | 64.8 (1) | 71.5 (1) | 64.5 (1) | 65.0 (1) | 64.9 (1) | 65.6 (1) | 65.4 (1) | 71.0 (1) | 65.2 (1) |
| b_q*J_hi | B | 52.3 (1) | 47.0 (1) | 52.3 (1) | 46.3 (1) | 47.4 (1) | 46.7 (1) | 47.8 (1) | 48.2 (1) | 53.9 (27) | 48.0 (26.9) |
| b_q*J1.0 | B | 40.3 (15.5) | 39.2 (15.5) | 37.4 (15.5) | 37.5 (15.5) | 39.1 (15.5) | 37.6 (15.5) | 37.3 (15.75) | 36.7 (15.5) | 38.3 (15.5) | 35.1 (15.5) |
| b_q*tau6 | B | 68.8 (1) | 62.5 (1) | 68.8 (1) | 62.2 (1) | 62.6 (1) | 62.7 (1) | 62.7 (1) | 62.4 (1) | 68.4 (1) | 60.7 (13.75) |
| nominal+h10 | B | 65.3 (26.9) | 59.1 (1) | 64.8 (1) | 58.9 (1) | 59.1 (1) | 59.4 (1) | 60.3 (1) | 60.1 (1) | 64.4 (1) | 63.0 (1) |
| J_lo+h10 | B | 63.8 (26.9) | 63.8 (27) | 66.3 (26.9) | 63.5 (27) | 63.9 (26.9) | 63.5 (27) | 65.4 (26.9) | 67.0 (26.9) | 69.5 (27) | 74.3 (1) |
| J_hi+h10 | B | 48.7 (1) | 42.6 (1) | 47.6 (1) | 41.7 (1) | 43.1 (1) | 42.2 (1) | 42.9 (1) | 43.4 (1) | 52.9 (1) | 52.9 (1) |
| b_lo+h10 | B | 53.9 (8) | 47.8 (1) | 49.8 (1) | 52.2 (1) | 45.0 (8) | 52.6 (1) | 47.2 (8) | 47.6 (8) | 45.2 (1) | 46.3 (1) |
| b_hi+h10 | B | 55.9 (26.9) | 55.9 (27) | 57.6 (26.9) | 55.7 (27) | 56.0 (26.9) | 55.7 (27) | 57.2 (26.9) | 58.8 (26.9) | 61.3 (27) | 75.6 (1) |
| tau0+h10 | B | 65.8 (26.9) | 60.2 (1) | 66.1 (1) | 60.0 (1) | 60.3 (1) | 60.5 (1) | 61.7 (1) | 61.5 (1) | 65.8 (1) | 64.6 (1) |
| tau6+h10 | B | 64.2 (1) | 56.8 (1) | 62.1 (1) | 56.7 (1) | 56.8 (1) | 57.3 (1) | 57.5 (1) | 57.4 (1) | 61.8 (1) | 59.8 (1) |
| mode13+h10 | B | 65.3 (26.9) | 59.0 (1) | 64.7 (1) | 58.8 (1) | 59.0 (1) | 59.4 (1) | 60.2 (1) | 60.0 (1) | 64.3 (1) | 62.9 (1) |
| mode20+h10 | B | 65.3 (26.9) | 59.0 (1) | 64.7 (1) | 58.9 (1) | 59.1 (1) | 59.4 (1) | 60.2 (1) | 60.1 (1) | 64.4 (1) | 63.0 (1) |
| ms_free+h10 | B | **30.0 (11.9)** | 43.6 (9) | 45.1 (9.5) | 43.9 (8.75) | 44.4 (9) | 43.8 (8.75) | 43.8 (8.75) | 43.4 (8.75) | 44.2 (11.9) | 45.8 (10.5) |
| b_lo*J_hi+h10 | B | 38.7 (8) | 32.1 (1) | 37.2 (1) | 32.0 (1) | 32.4 (1) | 32.6 (1) | 32.1 (1) | 32.2 (1) | 39.6 (1) | 38.0 (8) |
| b_lo*tau6+h10 | B | 50.4 (8) | 44.2 (8) | 46.1 (1) | 49.4 (1) | 41.3 (8) | 49.5 (8) | 43.1 (8) | 43.5 (8) | 41.6 (1) | 42.2 (6.75) |
| J1.0+h10 | B | 40.8 (1) | 36.1 (1) | 39.3 (1) | 35.0 (1) | 36.6 (1) | 35.5 (1) | 35.6 (1) | 36.9 (1) | 49.2 (1) | 53.1 (1) |
| b_q+h10 | B | 66.0 (1) | 59.1 (1) | 64.8 (1) | 58.9 (1) | 59.1 (1) | 59.4 (1) | 60.3 (1) | 60.1 (1) | 62.6 (13.75) | 63.0 (1) |
| b_q*J_hi+h10 | B | 48.7 (1) | 42.6 (1) | 47.6 (1) | 41.7 (1) | 43.1 (1) | 42.2 (1) | 42.9 (1) | 43.4 (1) | 46.3 (27) | 44.3 (26.9) |
| b_q*J1.0+h10 | B | 34.7 (15.5) | 33.6 (15.75) | 31.6 (15.5) | 33.7 (27) | 33.5 (15.5) | 34.0 (27) | 33.3 (26.9) | 33.2 (15.5) | 32.4 (15.75) | 32.6 (15.5) |
| b_q*tau6+h10 | B | 64.2 (1) | 56.8 (1) | 62.1 (1) | 56.7 (1) | 56.8 (1) | 57.3 (1) | 57.5 (1) | 57.4 (1) | 58.3 (13.75) | 59.8 (1) |
| J_hi*tau6 | report | 50.9 (1) | 45.2 (1) | 50.5 (1) | 44.5 (1) | 45.7 (1) | 45.0 (1) | 45.8 (1) | 46.2 (1) | 55.6 (1) | 53.6 (1) |
| J_hi*tau6+h10 | report | 47.3 (1) | 40.9 (1) | 45.8 (1) | 40.0 (1) | 41.4 (1) | 40.5 (1) | 40.9 (1) | 41.4 (1) | 51.1 (1) | 50.6 (1) |
| J_hi2 | report | 45.5 (1) | 41.0 (1) | 45.1 (1) | 40.3 (1) | 41.5 (1) | 40.7 (1) | 41.6 (1) | 42.5 (1) | 53.4 (1) | 55.2 (1) |
| J_hi2+h10 | report | 42.5 (1) | 37.5 (1) | 41.3 (1) | 36.4 (1) | 38.0 (1) | 36.9 (1) | 37.3 (1) | 38.3 (1) | 49.9 (1) | 52.3 (1) |
| J_hi2*tau6 | report | 44.3 (1) | 39.6 (1) | 43.6 (1) | 38.9 (1) | 40.1 (1) | 39.3 (1) | 39.9 (1) | 40.9 (1) | 52.0 (1) | 53.5 (1) |
| J_hi2*tau6+h10 | report | 41.3 (1) | 36.1 (1) | 39.8 (1) | 35.0 (1) | 36.6 (1) | 35.5 (1) | 35.7 (1) | 36.7 (1) | 48.5 (1) | 50.6 (1) |
| J1.0*tau6 | report | 42.4 (1) | 38.0 (1) | 41.3 (1) | 37.3 (1) | 38.5 (1) | 37.7 (1) | 38.1 (1) | 39.3 (1) | 51.1 (1) | 54.3 (1) |
| J1.0*tau6+h10 | report | 39.7 (1) | 34.8 (1) | 37.9 (1) | 33.8 (1) | 35.4 (1) | 34.2 (1) | 34.2 (1) | 35.4 (1) | 48.0 (1) | 51.6 (1) |
| b_lo*J_hi*tau6 | report | 42.3 (8) | 35.2 (1) | 40.6 (1) | 34.8 (1) | 35.5 (1) | 35.2 (8) | 34.8 (1) | 34.9 (1) | 42.9 (1) | 38.0 (8) |
| b_lo*J_hi*tau6+h10 | report | 36.3 (8) | 30.1 (1) | 34.9 (1) | 30.0 (1) | 30.3 (1) | 30.5 (8) | 29.8 (1) | 29.9 (1) | 37.4 (1) | 35.1 (8) |
| b_lo*J_hi2 | report | 38.6 (1) | 31.6 (1) | 36.2 (1) | 30.9 (1) | 32.1 (1) | 31.4 (1) | 31.6 (1) | 32.1 (1) | 42.4 (1) | 40.7 (8) |
| b_lo*J_hi2+h10 | report | 35.0 (1) | 27.4 (1) | 31.8 (1) | 26.6 (1) | 28.0 (1) | 27.2 (1) | 26.9 (1) | 27.6 (1) | 38.1 (1) | 37.5 (8) |
| b_lo*J_hi2*tau6 | report | 37.2 (1) | 29.9 (1) | 34.4 (1) | 29.2 (1) | 30.5 (1) | 29.8 (1) | 29.7 (1) | 30.2 (1) | 40.7 (1) | 38.2 (8) |
| b_lo*J_hi2*tau6+h10 | report | 33.1 (8) | 25.8 (1) | 30.0 (1) | 24.9 (1) | 26.3 (1) | 25.5 (1) | 25.1 (1) | 25.7 (1) | 36.4 (1) | 35.2 (8) |
| b_lo*J1.0 | report | 36.7 (1) | 30.0 (1) | 34.0 (1) | 29.3 (1) | 30.6 (1) | 29.8 (1) | 29.7 (1) | 30.6 (1) | 41.9 (1) | 41.4 (10) |
| b_lo*J1.0+h10 | report | 33.5 (1) | 26.3 (1) | 30.0 (1) | 25.3 (1) | 26.9 (1) | 25.9 (1) | 25.4 (1) | 26.3 (1) | 38.1 (1) | 38.5 (8) |
| b_lo*J1.0*tau6 | report | 35.4 (1) | 28.5 (1) | 32.4 (1) | 27.8 (1) | 29.1 (1) | 28.3 (1) | 28.0 (1) | 28.8 (1) | 40.4 (1) | 39.3 (8) |
| b_lo*J1.0*tau6+h10 | report | 32.2 (1) | 24.8 (1) | 28.4 (1) | 23.8 (1) | 25.4 (1) | 24.4 (1) | 23.7 (1) | 24.6 (1) | 36.4 (10) | 36.3 (8) |
| b/1.9 | report | 62.5 (8) | 55.5 (1) | 59.0 (1) | 57.1 (1) | 54.1 (1) | 56.8 (8) | 51.3 (8) | 51.6 (8) | 54.1 (1) | 47.6 (6.75) |
| b/1.9+h10 | report | 53.9 (8) | 47.8 (1) | 49.8 (1) | 52.2 (1) | 45.0 (8) | 52.6 (1) | 47.2 (8) | 47.6 (8) | 45.2 (1) | 46.3 (1) |
| b/1.9*tau6 | report | 59.1 (8) | 52.4 (1) | 55.3 (1) | 54.1 (1) | 50.6 (8) | 53.1 (8) | 46.9 (8) | 47.2 (8) | 50.5 (1) | 42.9 (7.75) |
| b/1.9*tau6+h10 | report | 50.4 (8) | 44.2 (8) | 46.1 (1) | 49.4 (1) | 41.3 (8) | 49.5 (8) | 43.1 (8) | 43.5 (8) | 41.6 (1) | 42.2 (6.75) |
| b/1.9*J_hi | report | 44.7 (8) | 37.3 (1) | 42.8 (1) | 36.9 (1) | 37.6 (1) | 37.4 (1) | 37.2 (1) | 37.3 (1) | 45.1 (1) | 41.1 (8) |
| b/1.9*J_hi+h10 | report | 38.7 (8) | 32.1 (1) | 37.2 (1) | 32.0 (1) | 32.4 (1) | 32.6 (1) | 32.1 (1) | 32.2 (1) | 39.6 (1) | 38.0 (8) |
| b/1.9*J_hi*tau6 | report | 42.3 (8) | 35.2 (1) | 40.6 (1) | 34.8 (1) | 35.5 (1) | 35.2 (8) | 34.8 (1) | 34.9 (1) | 42.9 (1) | 38.0 (8) |
| b/1.9*J_hi*tau6+h10 | report | 36.3 (8) | 30.1 (1) | 34.9 (1) | 30.0 (1) | 30.3 (1) | 30.5 (8) | 29.8 (1) | 29.9 (1) | 37.4 (1) | 35.1 (8) |
| b/1.9*J_hi2 | report | 38.6 (1) | 31.6 (1) | 36.2 (1) | 30.9 (1) | 32.1 (1) | 31.4 (1) | 31.6 (1) | 32.1 (1) | 42.4 (1) | 40.7 (8) |
| b/1.9*J_hi2+h10 | report | 35.0 (1) | 27.4 (1) | 31.8 (1) | 26.6 (1) | 28.0 (1) | 27.2 (1) | 26.9 (1) | 27.6 (1) | 38.1 (1) | 37.5 (8) |
| b/1.9*J_hi2*tau6 | report | 37.2 (1) | 29.9 (1) | 34.4 (1) | 29.2 (1) | 30.5 (1) | 29.8 (1) | 29.7 (1) | 30.2 (1) | 40.7 (1) | 38.2 (8) |
| b/1.9*J_hi2*tau6+h10 | report | 33.1 (8) | 25.8 (1) | 30.0 (1) | 24.9 (1) | 26.3 (1) | 25.5 (1) | 25.1 (1) | 25.7 (1) | 36.3 (10) | 35.2 (8) |
| b/1.9*J1.0 | report | 36.7 (1) | 30.0 (1) | 34.0 (1) | 29.3 (1) | 30.6 (1) | 29.8 (1) | 29.7 (1) | 30.6 (1) | 40.7 (10) | 39.6 (10) |
| b/1.9*J1.0+h10 | report | 33.5 (1) | 26.3 (1) | 30.0 (1) | 25.3 (1) | 26.9 (1) | 25.9 (1) | 25.4 (1) | 26.3 (1) | 36.1 (10) | 37.3 (10) |
| b/1.9*J1.0*tau6 | report | 35.4 (1) | 28.5 (1) | 32.4 (1) | 27.8 (1) | 29.1 (1) | 28.3 (1) | 28.0 (1) | 28.8 (1) | 38.8 (10) | 37.5 (10) |
| b/1.9*J1.0*tau6+h10 | report | 32.2 (1) | 24.8 (1) | 28.4 (1) | 23.8 (1) | 25.4 (1) | 24.4 (1) | 23.7 (1) | 24.6 (1) | 34.2 (10) | 35.3 (10) |
| b_q*J_hi*tau6 | report | 50.9 (1) | 45.2 (1) | 50.5 (1) | 44.5 (1) | 45.7 (1) | 45.0 (1) | 45.8 (1) | 46.2 (1) | 50.9 (27) | 44.5 (26.9) |
| b_q*J_hi*tau6+h10 | report | 47.3 (1) | 40.9 (1) | 45.8 (1) | 40.0 (1) | 41.4 (1) | 40.5 (1) | 40.9 (1) | 41.4 (1) | 43.2 (27) | 40.9 (26.9) |
| b_q*J_hi2 | report | 45.5 (1) | 41.0 (1) | 44.6 (15.5) | 40.3 (1) | 41.5 (1) | 40.7 (1) | 41.6 (1) | 42.5 (1) | 43.4 (27) | 39.2 (15.5) |
| b_q*J_hi2+h10 | report | 39.5 (26.9) | 37.5 (1) | 38.2 (15.5) | 36.4 (1) | 38.0 (1) | 36.9 (1) | 37.3 (1) | 37.5 (26.9) | 36.8 (27) | 35.9 (26.9) |
| b_q*J_hi2*tau6 | report | 43.2 (26.9) | 39.6 (1) | 42.1 (15.5) | 38.9 (1) | 40.1 (1) | 39.3 (1) | 39.9 (1) | 39.9 (26.9) | 40.7 (27) | 36.4 (15.5) |
| b_q*J_hi2*tau6+h10 | report | 37.1 (26.9) | 36.1 (1) | 35.6 (15.5) | 35.0 (1) | 35.8 (26.9) | 35.5 (1) | 35.0 (26.9) | 34.8 (26.9) | 34.1 (27) | 33.0 (26.9) |
| b_q*J1.0*tau6 | report | 38.1 (15.5) | 36.9 (15.5) | 35.1 (15.5) | 35.2 (15.5) | 36.9 (15.5) | 35.3 (15.75) | 34.9 (15.75) | 34.4 (15.5) | 36.0 (15.5) | 32.6 (15.5) |
| b_q*J1.0*tau6+h10 | report | 32.5 (15.75) | 31.3 (15.75) | 29.2 (15.5) | 31.4 (27) | 31.2 (15.5) | 31.7 (27) | 30.8 (26.9) | 30.8 (26.9) | 30.0 (15.75) | 30.1 (15.75) |
| b_lo*J0.3 | report | 50.9 (8) | 44.3 (1) | 49.4 (1) | 44.8 (1) | 43.7 (1) | 44.6 (8) | 42.5 (8) | 42.7 (8) | 47.1 (1) | 41.6 (8) |
| b_lo*J0.3+h10 | report | 43.3 (8) | 37.6 (1) | 41.8 (1) | 39.7 (1) | 36.1 (8) | 40.0 (8) | 37.5 (8) | 37.7 (1) | 39.6 (1) | 39.3 (7.5) |
| J1.3 | report | 41.9 (1) | 38.0 (1) | 40.5 (1) | 37.3 (1) | 38.5 (1) | 37.7 (1) | 37.8 (1) | 39.2 (1) | 51.6 (1) | 57.1 (1) |
| b_lo*J1.3 | report | 28.7 (11.9) | 29.0 (1) | 32.0 (11.9) | 28.2 (1) | 29.6 (1) | 28.7 (1) | 28.2 (1) | 29.3 (1) | 38.5 (11.9) | 39.3 (10) |
| b_q*J1.3 | report | 30.2 (15.75) | 29.1 (15.75) | 29.1 (15.5) | 27.0 (15.75) | 29.5 (15.75) | 27.2 (15.75) | 28.1 (15.75) | 28.0 (15.75) | 31.3 (15.75) | 29.8 (15.75) |
| b_q*J1.3+h10 | report | 25.1 (15.75) | 24.0 (15.75) | 23.8 (15.5) | 23.3 (15.75) | 24.4 (15.75) | 23.6 (15.75) | 24.3 (15.75) | 24.1 (15.75) | 25.9 (15.75) | 26.9 (15.75) |
| tau10 | report | 65.8 (26.9) | 60.2 (1) | 66.1 (1) | 60.0 (1) | 60.3 (1) | 60.4 (1) | 59.7 (1) | 59.5 (1) | 65.8 (1) | 58.3 (1) |
| b_lo*tau10 | report | 55.6 (8) | 49.3 (1) | 51.6 (1) | 50.8 (8) | 46.9 (8) | 49.5 (8) | 42.4 (8) | 42.9 (8) | 47.0 (1) | 38.2 (8) |
| light_b | report | 9.7 (26.9) | 9.1 (27) | 32.2 (1) | 12.7 (27) | 5.4 (26.9) | 11.7 (27) | 10.0 (26.9) | 9.7 (26.9) | 0.7 (27) | 1.4 (26.9) |
| b_q0 | report | 70.7 (1) | 64.8 (1) | 71.5 (1) | 64.5 (1) | 65.0 (1) | 64.9 (1) | 65.6 (1) | 65.4 (1) | 59.3 (12.5) | 56.2 (12.5) |
| b_q0*J_hi | report | 47.4 (12.5) | 47.0 (1) | 49.8 (12.5) | 46.3 (1) | 47.4 (1) | 46.7 (1) | 47.8 (1) | 48.2 (1) | 42.6 (12.5) | 41.7 (12.5) |
| bq10*J1.0 | report | 34.9 (10) | 39.2 (15.5) | 36.3 (10) | 37.5 (15.5) | 39.1 (15.5) | 37.6 (15.5) | 37.3 (15.75) | 36.7 (15.5) | 36.3 (10) | 35.1 (15.5) |
| bq10*J1.0+h10 | report | 30.6 (10) | 33.6 (15.75) | 31.6 (15.5) | 33.7 (27) | 33.5 (15.5) | 34.0 (27) | 33.3 (26.9) | 33.2 (15.5) | 31.6 (10) | 32.6 (15.5) |
| bq10*J1.0*tau6+h10 | report | 28.9 (10) | 31.3 (15.75) | 29.2 (15.5) | 31.4 (27) | 31.2 (15.5) | 31.7 (27) | 30.8 (26.9) | 30.8 (26.9) | 29.7 (10) | 30.1 (15.75) |

### GATE 2 summary per candidate (gated members only unless stated)

| id | gated points | FAILS (PM/GM/rho/T530/M20/L20) | min exact GM dB (member, v) | max rho | least-damped 0.3-8 Hz pole (member, v) | max M20 (V295) | max L20/V295 | max T530 dB | max Tr 1.6-3 Hz (member) | report: worst PM (member, v) |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 4760 | 13 (PM45 12, PM30 1) | 9.1 (b_lo*tau6+h10, 8) | 0.9927 | 1.79 Hz z 0.136 (b_q*J1.0+h10, 17.5) | 2.36 (3.38) | 0.697 | -3.9 | 1.87 (b_q*J1.0+h10, 26.9) | 9.7 (light_b, 26.9) |
| B0r | 4760 | 0 (0) | 8.5 (b_lo*tau6+h10, 8) | 0.9906 | 1.80 Hz z 0.133 (b_q*J1.0+h10, 17.5) | 2.36 (3.38) | 0.697 | -3.7 | 1.92 (b_q*J1.0+h10, 27) | 9.1 (light_b, 27) |
| D1a | 4760 | 0 (0) | 8.4 (b_lo*tau6+h10, 1) | 0.9930 | 1.68 Hz z 0.145 (b_q*J1.0+h10, 15.5) | 3.12 (3.38) | 0.923 | -1.4 | 1.86 (b_q*J1.0+h10, 15.5) | 23.8 (b_q*J1.3+h10, 15.5) |
| D1b | 4760 | 0 (0) | 15.6 (b_q*J1.0+h10, 27) | 0.9909 | 1.77 Hz z 0.127 (b_q*J1.0+h10, 17.5) | 2.42 (3.38) | 0.714 | -6.2 | 2.06 (b_q*J1.0+h10, 27) | 12.7 (light_b, 27) |
| D1c | 4760 | 0 (0) | 7.0 (b_lo*tau6+h10, 8) | 0.9905 | 1.80 Hz z 0.135 (b_q*J1.0+h10, 17.5) | 2.07 (3.38) | 0.610 | -2.5 | 1.89 (b_q*J1.0+h10, 26.9) | 5.4 (light_b, 26.9) |
| D2a | 4760 | 0 (0) | 15.1 (b_q*J1.0+h10, 27) | 0.9909 | 1.77 Hz z 0.127 (b_q*J1.0+h10, 17.5) | 2.29 (3.38) | 0.677 | -5.6 | 2.03 (b_q*J1.0+h10, 27) | 11.7 (light_b, 27) |
| D2b | 4760 | 0 (0) | 11.4 (b_lo*tau6+h10, 8) | 0.9905 | 1.85 Hz z 0.146 (b_q*J1.0+h10, 17.5) | 2.33 (3.38) | 0.691 | -1.4 | 1.94 (b_lo*J_hi+h10, 1) | 10.0 (light_b, 26.9) |
| D2c | 4760 | 0 (0) | 11.9 (b_lo*tau6+h10, 8) | 0.9903 | 1.69 Hz z 0.144 (b_q*J1.0+h10, 15.75) | 2.31 (3.38) | 0.683 | -1.8 | 1.86 (b_lo*J_hi+h10, 1) | 9.7 (light_b, 26.9) |
| D3a | 4760 | 0 (0) | 6.3 (b_lo*tau6+h10, 7.75) | 0.9875 | 1.88 Hz z 0.143 (b_q*J1.0+h10, 17.5) | 2.07 (3.38) | 0.613 | -0.7 | 1.57 (b_q*J1.0+h10, 27) | 0.7 (light_b, 27) |
| D3b | 4760 | 0 (0) | 8.9 (b_lo*tau6, 8) | 0.9906 | 1.96 Hz z 0.154 (b_q*J1.0+h10, 17.5) | 2.33 (3.38) | 0.690 | +0.2 | 1.68 (b_q*J1.0+h10, 26.9) | 1.4 (light_b, 26.9) |

### The gated fails, listed
- **B0**: ms_free PM45 at 9.75-12.25 m/s (12 pts); ms_free+h10 PM30 at 11.9-11.9 m/s (1 pts)
- **B0r**: none
- **D1a**: none
- **D1b**: none
- **D1c**: none
- **D2a**: none
- **D2b**: none
- **D2c**: none
- **D3a**: none
- **D3b**: none

### Re(T/w), T counts per deg/s (> 0 damps), worst over 1-35 m/s, the EMA rate model; V294/V295/V282 same model

| ctl | age | 5 Hz | 7 Hz | 10 Hz | 13 Hz | 15 Hz | 17 Hz | 20 Hz | 25 Hz |
|---|---|---|---|---|---|---|---|---|---|
| V294 | 0 | +1.33 | +0.67 | +0.05 | -0.25 | -0.36 | -0.42 | -0.44 | -0.41 |
| V295 | 0 | +2.46 | +1.24 | +0.09 | -0.47 | -0.66 | -0.77 | -0.82 | -0.76 |
| V282 | 0 | +17.98 | +10.06 | +1.82 | -3.50 | -5.88 | -7.52 | -8.87 | -9.05 |
| B0 | 0 | -0.82 | -0.82 | -0.85 | -0.83 | -0.80 | -0.76 | -0.69 | -0.55 |
| B0r | 0 | -0.84 | -0.84 | -0.86 | -0.84 | -0.81 | -0.77 | -0.69 | -0.55 |
| D1a | 0 | +0.09 | -0.14 | -0.53 | -0.71 | -0.77 | -0.79 | -0.79 | -0.72 |
| D1b | 0 | -0.47 | -0.30 | -0.22 | -0.19 | -0.18 | -0.18 | -0.17 | -0.17 |
| D1c | 0 | -1.16 | -1.21 | -1.18 | -1.05 | -0.94 | -0.82 | -0.65 | -0.40 |
| D2a | 0 | -0.57 | -0.44 | -0.39 | -0.37 | -0.36 | -0.35 | -0.34 | -0.31 |
| D2b | 0 | -0.79 | -0.89 | -0.87 | -0.76 | -0.68 | -0.61 | -0.52 | -0.41 |
| D2c | 0 | -0.80 | -0.87 | -0.83 | -0.73 | -0.65 | -0.59 | -0.50 | -0.40 |
| D3a | 0 | -1.55 | -1.66 | -1.54 | -1.26 | -1.05 | -0.85 | -0.59 | -0.29 |
| D3b | 0 | -1.43 | -1.48 | -1.40 | -1.20 | -1.06 | -0.91 | -0.73 | -0.48 |
| V294 | 10 | +0.91 | +0.05 | -0.63 | -0.81 | -0.78 | -0.68 | -0.48 | -0.13 |
| V295 | 10 | +1.69 | +0.08 | -1.17 | -1.50 | -1.44 | -1.26 | -0.89 | -0.25 |
| V282 | 10 | +9.93 | -0.83 | -10.80 | -15.03 | -15.41 | -14.34 | -10.95 | -3.63 |
| B0 | 10 | -1.65 | -1.61 | -1.46 | -1.20 | -1.00 | -0.79 | -0.51 | -0.09 |
| B0r | 10 | -1.68 | -1.62 | -1.47 | -1.20 | -1.00 | -0.80 | -0.52 | -0.10 |
| D1a | 10 | -0.69 | -1.21 | -1.51 | -1.46 | -1.32 | -1.13 | -0.80 | -0.26 |
| D1b | 10 | -0.64 | -0.28 | -0.06 | +0.03 | +0.04 | +0.03 | -0.03 | -0.10 |
| D1c | 10 | -2.00 | -1.94 | -1.60 | -1.12 | -0.80 | -0.52 | -0.20 | +0.12 |
| D2a | 10 | -0.74 | -0.42 | -0.23 | -0.15 | -0.14 | -0.15 | -0.20 | -0.24 |
| D2b | 10 | -1.31 | -1.16 | -0.82 | -0.50 | -0.35 | -0.23 | -0.20 | -0.22 |
| D2c | 10 | -1.29 | -1.11 | -0.77 | -0.47 | -0.33 | -0.22 | -0.20 | -0.22 |
| D3a | 10 | -2.49 | -2.40 | -1.82 | -1.08 | -0.65 | -0.30 | +0.02 | +0.25 |
| D3b | 10 | -1.69 | -1.50 | -1.23 | -0.96 | -0.80 | -0.67 | -0.55 | -0.38 |

### Time domain, member **nominal** (ds_time.run: harness_time's plant / scenarios / metrics, the integer lane, EMA rate sensor, fixed seed 11)

**3 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.03 | 1.01 | 0.99 | 1.01 | 1.02 | 1.01 | 1.00 | 1.00 | 0.98 | 0.97 |
| tracking 0.2 Hz phase deg | -3 | -2 | -1 | -2 | -2 | -2 | -1 | -2 | -11 | -9 |
| tracking 0.5 Hz fit gain | 1.24 | 1.20 | 1.16 | 1.20 | 1.20 | 1.20 | 1.16 | 1.16 | 1.03 | 0.98 |
| turn-hold ratio | 1.003 | 1.002 | 1.001 | 1.002 | 0.999 | 1.002 | 1.002 | 1.001 | 1.003 | 1.003 |
| dwell-then-jump events (s02+s05+ssm) | 4 | 5 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| stick % (s02) | 10 | 9 | 8 | 9 | 9 | 9 | 8 | 8 | 10 | 10 |
| +-1 deg fit gain (ssm) | 1.54 | 1.39 | 1.32 | 1.38 | 1.32 | 1.39 | 1.32 | 1.26 | 1.10 | 0.75 |
| hold slips (rh) | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 1 | 0 |
| dead zone: hold error deg (rh) | 0.22 | 0.09 | 0.07 | 0.10 | 0.05 | 0.11 | 0.24 | 0.05 | 0.33 | 0.30 |
| hunt p2p deg (rh holds) | 3.38 | 2.91 | 1.33 | 2.88 | 2.74 | 2.92 | 2.23 | 2.23 | 0.39 | 0.00 |
| step overshoot % | 10 | 9 | 22 | 9 | 9 | 9 | 7 | 7 | 5 | 1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 4.61 | 4.00 | 9.60 | 4.18 | 4.19 | 4.12 | 3.20 | 3.14 | 2.81 | 2.53 |
| lurch, LIGHT hand tq 400: overshoot deg | 4.61 | 3.99 | 10.55 | 4.17 | 4.16 | 4.12 | 3.20 | 3.13 | 2.50 | 2.47 |
| lurch, light hand tq 1000: overshoot deg | 4.59 | 3.98 | 10.54 | 4.17 | 4.16 | 4.11 | 3.19 | 3.13 | 2.59 | 2.47 |
| override-latch overshoot deg | 0.72 | 0.27 | 0.28 | 0.25 | 0.11 | 0.27 | 0.14 | -0.02 | 0.06 | -0.13 |
| engage droop deg | 5.28 | 4.67 | 4.19 | 4.60 | 4.38 | 4.66 | 3.94 | 4.09 | 5.42 | 4.07 |
| engage peak T | 409 | 410 | 412 | 412 | 407 | 412 | 407 | 404 | 394 | 379 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 32.57 | 32.42 | 32.58 | 32.42 | 32.60 | 32.40 | 32.49 | 32.55 | 33.82 | 32.99 |
| 5-30 Hz T rms in holds (texture) | 0.54 | 0.62 | 2.53 | 0.53 | 1.22 | 0.57 | 0.81 | 0.81 | 0.46 | 0.61 |
| 5-30 Hz T rms (s05) | 2.91 | 3.00 | 5.01 | 2.62 | 3.32 | 2.75 | 3.67 | 3.56 | 2.66 | 3.29 |
| 40-200 Hz T rms (s05) | 0.63 | 0.78 | 26.76 | 0.78 | 4.21 | 0.76 | 1.83 | 1.34 | 0.52 | 0.82 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 1.14/1.80 | 1.42/1.80 | 1.49/1.80 | 1.44/1.80 | 1.52/1.80 | 1.42/1.80 | 1.53/1.80 | 1.50/1.80 | 0.95/1.80 | 1.27/1.80 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 | 0.19 | 0.21 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**5 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.01 | 1.00 | 0.98 | 1.00 | 1.00 | 1.00 | 0.99 | 0.99 | 0.97 | 0.95 |
| tracking 0.2 Hz phase deg | -5 | -3 | -3 | -3 | -4 | -3 | -2 | -4 | -13 | -11 |
| tracking 0.5 Hz fit gain | 1.19 | 1.17 | 1.08 | 1.17 | 1.17 | 1.17 | 1.13 | 1.12 | 0.96 | 0.93 |
| turn-hold ratio | 0.999 | 0.999 | 0.999 | 0.999 | 1.000 | 0.999 | 0.999 | 1.001 | 1.006 | 0.999 |
| dwell-then-jump events (s02+s05+ssm) | 3 | 2 | 0 | 1 | 0 | 2 | 0 | 0 | 4 | 0 |
| stick % (s02) | 9 | 9 | 8 | 9 | 10 | 9 | 8 | 8 | 12 | 10 |
| +-1 deg fit gain (ssm) | 1.30 | 1.25 | 1.18 | 1.24 | 1.23 | 1.24 | 1.20 | 1.15 | 1.11 | 0.93 |
| hold slips (rh) | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 1 | 0 |
| dead zone: hold error deg (rh) | 0.06 | 0.05 | 0.05 | 0.05 | 0.23 | 0.05 | 0.05 | 0.12 | 0.31 | 0.04 |
| hunt p2p deg (rh holds) | 1.87 | 1.75 | 0.64 | 1.71 | 1.60 | 1.75 | 1.40 | 1.27 | 0.32 | 0.17 |
| step overshoot % | 17 | 16 | 19 | 16 | 16 | 16 | 12 | 12 | 1 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 4.24 | 3.92 | 5.15 | 4.14 | 4.02 | 4.07 | 3.03 | 2.97 | 1.60 | 1.09 |
| lurch, LIGHT hand tq 400: overshoot deg | 4.20 | 3.92 | 7.31 | 4.33 | 3.91 | 4.21 | 2.97 | 2.79 | 2.31 | 2.33 |
| lurch, light hand tq 1000: overshoot deg | 4.25 | 3.89 | 6.05 | 4.18 | 3.96 | 4.10 | 2.96 | 2.89 | 2.42 | 1.67 |
| override-latch overshoot deg | 0.17 | 0.07 | 0.15 | 0.05 | -0.04 | 0.06 | 0.05 | -0.12 | -0.03 | -0.13 |
| engage droop deg | 5.04 | 4.64 | 4.37 | 4.57 | 4.40 | 4.60 | 3.96 | 4.12 | 5.46 | 4.15 |
| engage peak T | 370 | 373 | 376 | 374 | 372 | 373 | 370 | 367 | 354 | 354 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 20.79 | 20.65 | 21.12 | 20.62 | 20.79 | 20.62 | 20.61 | 20.68 | 20.79 | 20.46 |
| 5-30 Hz T rms in holds (texture) | 0.54 | 0.60 | 2.27 | 0.55 | 1.21 | 0.59 | 0.87 | 0.77 | 0.34 | 0.63 |
| 5-30 Hz T rms (s05) | 1.43 | 1.55 | 4.02 | 1.37 | 2.48 | 1.41 | 2.25 | 2.06 | 1.59 | 2.04 |
| 40-200 Hz T rms (s05) | 0.42 | 0.48 | 19.08 | 0.50 | 2.34 | 0.49 | 1.11 | 0.81 | 0.31 | 0.49 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 1.17/1.69 | 1.38/1.69 | 1.41/1.69 | 1.42/1.69 | 1.36/1.69 | 1.41/1.69 | 1.46/1.69 | 1.39/1.69 | 0.82/1.69 | 1.26/1.69 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.15 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.20 | 0.19 | 0.13 | 0.19 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**8 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.97 | 0.97 | 0.95 | 0.97 | 0.97 | 0.97 | 0.97 | 0.96 | 0.92 | 0.90 |
| tracking 0.2 Hz phase deg | -6 | -5 | -5 | -5 | -5 | -5 | -3 | -5 | -16 | -12 |
| tracking 0.5 Hz fit gain | 1.06 | 1.06 | 0.97 | 1.06 | 1.06 | 1.06 | 1.05 | 1.04 | 0.85 | 0.85 |
| turn-hold ratio | 0.999 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 0.999 | 0.997 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 2 | 6 | 5 |
| +-1 deg fit gain (ssm) | 1.08 | 1.07 | 1.03 | 1.06 | 1.09 | 1.06 | 1.05 | 1.02 | 0.98 | 0.92 |
| hold slips (rh) | 0 | 0 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| dead zone: hold error deg (rh) | 0.03 | 0.03 | 0.04 | 0.03 | 0.04 | 0.03 | 0.03 | 0.13 | 0.05 | 0.03 |
| hunt p2p deg (rh holds) | 0.82 | 0.63 | 0.12 | 0.52 | 0.85 | 0.53 | 0.47 | 0.46 | 0.51 | 0.90 |
| step overshoot % | 9 | 9 | 9 | 12 | 9 | 11 | 7 | 6 | -0 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 2.96 | 3.02 | 2.88 | 3.34 | 2.66 | 3.30 | 2.70 | 2.10 | 0.71 | 0.44 |
| lurch, LIGHT hand tq 400: overshoot deg | 4.14 | 4.29 | 5.19 | 4.60 | 4.42 | 4.57 | 3.58 | 3.35 | 2.60 | 2.99 |
| lurch, light hand tq 1000: overshoot deg | 3.04 | 3.17 | 3.09 | 3.59 | 2.76 | 3.51 | 2.85 | 2.37 | 1.22 | 0.76 |
| override-latch overshoot deg | -0.03 | -0.03 | 0.05 | -0.03 | -0.04 | -0.03 | -0.03 | -0.13 | -0.04 | -0.13 |
| engage droop deg | 4.83 | 4.63 | 4.58 | 4.53 | 4.45 | 4.53 | 4.02 | 4.16 | 5.48 | 4.22 |
| engage peak T | 314 | 315 | 325 | 314 | 318 | 314 | 315 | 311 | 310 | 312 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | 0.00 | 0.00 | 0.00 | -0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 14.35 | 14.35 | 14.41 | 14.36 | 14.46 | 14.35 | 14.36 | 14.35 | 14.29 | 14.10 |
| 5-30 Hz T rms in holds (texture) | 0.60 | 0.66 | 2.49 | 0.64 | 0.89 | 0.67 | 1.02 | 0.78 | 0.48 | 0.89 |
| 5-30 Hz T rms (s05) | 0.90 | 1.06 | 3.78 | 0.89 | 2.21 | 0.93 | 1.66 | 1.48 | 0.73 | 1.07 |
| 40-200 Hz T rms (s05) | 0.32 | 0.34 | 11.56 | 0.35 | 1.41 | 0.35 | 0.74 | 0.55 | 0.22 | 0.35 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 1.70/2.26 | 1.79/2.26 | 1.68/2.26 | 1.85/2.26 | 1.96/2.26 | 1.85/2.26 | 1.92/2.26 | 1.86/2.26 | 1.07/2.26 | 1.58/2.26 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.13 | 0.13 | 0.13 | 0.14 | 0.13 | 0.14 | 0.15 | 0.14 | 0.10 | 0.14 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**10 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.00 | 1.01 | 0.97 | 1.01 | 1.01 | 1.01 | 1.01 | 0.99 | 0.92 | 0.88 |
| tracking 0.2 Hz phase deg | -12 | -15 | -16 | -18 | -17 | -18 | -18 | -17 | -24 | -22 |
| tracking 0.5 Hz fit gain | 1.07 | 1.03 | 0.88 | 0.99 | 1.01 | 0.98 | 0.96 | 0.99 | 0.76 | 0.75 |
| turn-hold ratio | 0.994 | 0.993 | 0.998 | 0.993 | 0.997 | 0.993 | 0.993 | 0.993 | 1.005 | 0.994 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 5 | 6 | 6 | 7 | 8 | 7 | 7 | 6 | 8 | 7 |
| +-1 deg fit gain (ssm) | 1.15 | 1.16 | 1.09 | 1.16 | 1.17 | 1.16 | 1.16 | 1.10 | 0.95 | 0.85 |
| hold slips (rh) | 1 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.13 | 0.15 | 0.06 | 0.17 | 0.09 | 0.17 | 0.17 | 0.15 | 0.12 | 0.06 |
| hunt p2p deg (rh holds) | 1.22 | 1.26 | 0.44 | 1.28 | 1.06 | 1.27 | 1.28 | 1.06 | 0.78 | 1.18 |
| step overshoot % | 10 | 9 | 7 | 9 | 8 | 9 | 9 | 7 | -0 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 2.07 | 2.12 | 2.28 | 2.21 | 2.21 | 2.20 | 2.24 | 1.89 | 0.65 | 0.46 |
| lurch, LIGHT hand tq 400: overshoot deg | 5.40 | 5.88 | 6.51 | 6.30 | 6.16 | 6.29 | 6.16 | 5.66 | 4.09 | 4.14 |
| lurch, light hand tq 1000: overshoot deg | 2.02 | 2.06 | 2.26 | 2.16 | 2.14 | 2.15 | 2.17 | 1.88 | 0.96 | 0.68 |
| override-latch overshoot deg | 0.16 | 0.20 | 0.15 | 0.24 | 0.10 | 0.25 | 0.27 | 0.10 | -0.03 | -0.21 |
| engage droop deg | 3.72 | 3.99 | 4.25 | 4.20 | 3.61 | 4.20 | 4.14 | 4.00 | 4.03 | 3.28 |
| engage peak T | 245 | 244 | 246 | 243 | 243 | 243 | 244 | 241 | 232 | 233 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | -0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 9.80 | 9.93 | 9.58 | 9.95 | 9.78 | 9.95 | 9.94 | 9.81 | 9.31 | 9.04 |
| 5-30 Hz T rms in holds (texture) | 0.41 | 0.37 | 1.12 | 0.29 | 1.35 | 0.32 | 0.38 | 0.40 | 0.35 | 0.54 |
| 5-30 Hz T rms (s05) | 0.57 | 0.46 | 1.64 | 0.39 | 2.20 | 0.46 | 0.65 | 0.59 | 0.53 | 0.65 |
| 40-200 Hz T rms (s05) | 0.19 | 0.18 | 3.47 | 0.17 | 0.87 | 0.16 | 0.21 | 0.20 | 0.17 | 0.20 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.59/1.51 | 0.46/1.51 | 0.47/1.51 | 0.38/1.51 | 0.46/1.51 | 0.38/1.51 | 0.37/1.51 | 0.41/1.51 | 0.40/1.51 | 0.58/1.51 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.08 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.09 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**12.5 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.01 | 1.01 | 0.96 | 1.01 | 1.03 | 1.01 | 1.01 | 0.99 | 0.88 | 0.81 |
| tracking 0.2 Hz phase deg | -20 | -25 | -28 | -25 | -28 | -25 | -23 | -25 | -40 | -36 |
| tracking 0.5 Hz fit gain | 0.92 | 0.82 | 0.67 | 0.83 | 0.78 | 0.83 | 0.85 | 0.83 | 0.54 | 0.56 |
| turn-hold ratio | 0.997 | 1.002 | 1.011 | 1.002 | 1.022 | 1.002 | 1.000 | 1.002 | 1.000 | 0.984 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 6 | 8 | 8 | 7 | 10 | 7 | 7 | 7 | 11 | 10 |
| +-1 deg fit gain (ssm) | 1.13 | 1.09 | 0.98 | 1.09 | 1.03 | 1.09 | 1.10 | 1.04 | 0.79 | 0.70 |
| hold slips (rh) | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.07 | 0.08 | 0.05 | 0.07 | 0.05 | 0.08 | 0.07 | 0.06 | 0.07 | 0.14 |
| hunt p2p deg (rh holds) | 0.64 | 0.53 | 0.64 | 0.52 | 0.63 | 0.52 | 0.57 | 0.46 | 1.65 | 1.64 |
| step overshoot % | 7 | 6 | 3 | 6 | 4 | 6 | 6 | 4 | -1 | -2 |
| lurch, FIRM hand (tq 2400): overshoot deg | 1.31 | 1.34 | 1.30 | 1.36 | 1.31 | 1.35 | 1.35 | 1.17 | 0.38 | 0.25 |
| lurch, LIGHT hand tq 400: overshoot deg | 5.21 | 5.67 | 6.27 | 5.66 | 5.83 | 5.66 | 5.37 | 5.29 | 4.58 | 4.60 |
| lurch, light hand tq 1000: overshoot deg | 1.26 | 1.30 | 1.29 | 1.32 | 1.28 | 1.32 | 1.30 | 1.17 | 0.55 | 0.37 |
| override-latch overshoot deg | 0.14 | 0.15 | 0.08 | 0.14 | 0.07 | 0.15 | 0.15 | 0.03 | -0.09 | -0.31 |
| engage droop deg | 2.59 | 2.76 | 2.94 | 2.74 | 2.33 | 2.75 | 2.64 | 2.68 | 2.91 | 2.46 |
| engage peak T | 205 | 203 | 202 | 203 | 202 | 203 | 204 | 200 | 194 | 194 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 5.83 | 5.80 | 5.63 | 5.80 | 5.72 | 5.80 | 5.81 | 5.69 | 5.26 | 5.03 |
| 5-30 Hz T rms in holds (texture) | 0.41 | 0.36 | 0.81 | 0.30 | 1.30 | 0.32 | 0.43 | 0.40 | 0.30 | 0.42 |
| 5-30 Hz T rms (s05) | 0.47 | 0.39 | 1.34 | 0.30 | 1.88 | 0.35 | 0.46 | 0.48 | 0.38 | 0.40 |
| 40-200 Hz T rms (s05) | 0.16 | 0.16 | 1.69 | 0.16 | 0.64 | 0.16 | 0.19 | 0.17 | 0.17 | 0.17 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.21/0.91 | 0.18/0.91 | 0.17/0.91 | 0.18/0.91 | 0.18/0.91 | 0.18/0.91 | 0.19/0.91 | 0.19/0.91 | 0.15/0.91 | 0.21/0.91 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.06 | 0.06 | 0.05 | 0.06 | 0.05 | 0.06 | 0.06 | 0.06 | 0.05 | 0.06 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**15 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.93 | 0.93 | 0.92 | 0.94 | 0.95 | 0.94 | 0.95 | 0.92 | 0.83 | 0.74 |
| tracking 0.2 Hz phase deg | -28 | -27 | -24 | -26 | -31 | -26 | -23 | -26 | -40 | -37 |
| tracking 0.5 Hz fit gain | 0.74 | 0.73 | 0.70 | 0.76 | 0.68 | 0.76 | 0.78 | 0.75 | 0.52 | 0.52 |
| turn-hold ratio | 1.011 | 1.011 | 1.006 | 1.008 | 1.007 | 1.007 | 1.005 | 0.996 | 0.993 | 0.969 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 8 | 8 | 5 | 6 | 12 | 7 | 4 | 6 | 10 | 9 |
| +-1 deg fit gain (ssm) | 0.93 | 0.93 | 0.91 | 0.95 | 0.93 | 0.96 | 0.96 | 0.91 | 0.74 | 0.65 |
| hold slips (rh) | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.07 | 0.07 | 0.06 | 0.03 | 0.10 | 0.03 | 0.04 | 0.14 | 0.04 | 0.14 |
| hunt p2p deg (rh holds) | 0.39 | 0.40 | 0.40 | 0.32 | 0.44 | 0.33 | 0.24 | 0.28 | 1.27 | 1.32 |
| step overshoot % | 1 | 1 | 1 | 1 | -0 | 1 | 2 | -1 | -1 | -4 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.73 | 0.73 | 0.75 | 0.75 | 0.70 | 0.75 | 0.75 | 0.60 | 0.25 | 0.07 |
| lurch, LIGHT hand tq 400: overshoot deg | 3.13 | 3.14 | 2.98 | 3.09 | 3.25 | 3.09 | 2.92 | 2.87 | 2.87 | 2.81 |
| lurch, light hand tq 1000: overshoot deg | 0.71 | 0.72 | 0.74 | 0.73 | 0.68 | 0.73 | 0.73 | 0.60 | 0.34 | 0.14 |
| override-latch overshoot deg | -0.04 | -0.03 | 0.02 | 0.02 | -0.05 | 0.01 | 0.01 | -0.10 | -0.12 | -0.31 |
| engage droop deg | 2.14 | 2.15 | 2.06 | 2.10 | 1.89 | 2.11 | 2.02 | 2.06 | 2.29 | 1.99 |
| engage peak T | 237 | 237 | 240 | 239 | 236 | 239 | 239 | 232 | 235 | 234 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 3.81 | 3.81 | 3.82 | 3.85 | 3.77 | 3.86 | 3.86 | 3.75 | 3.54 | 3.32 |
| 5-30 Hz T rms in holds (texture) | 0.38 | 0.39 | 1.25 | 0.29 | 2.16 | 0.35 | 0.44 | 0.42 | 0.38 | 0.52 |
| 5-30 Hz T rms (s05) | 0.45 | 0.40 | 2.56 | 0.36 | 1.86 | 0.39 | 0.71 | 0.60 | 0.37 | 0.49 |
| 40-200 Hz T rms (s05) | 0.17 | 0.18 | 3.02 | 0.18 | 0.69 | 0.17 | 0.25 | 0.22 | 0.17 | 0.19 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.12/0.60 | 0.12/0.60 | 0.15/0.60 | 0.13/0.60 | 0.13/0.60 | 0.13/0.60 | 0.14/0.60 | 0.14/0.60 | 0.10/0.60 | 0.14/0.60 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**19 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.94 | 0.94 | 0.91 | 0.94 | 0.97 | 0.95 | 0.95 | 0.91 | 0.88 | 0.78 |
| tracking 0.2 Hz phase deg | -23 | -23 | -26 | -21 | -27 | -21 | -19 | -23 | -32 | -33 |
| tracking 0.5 Hz fit gain | 0.80 | 0.80 | 0.66 | 0.82 | 0.75 | 0.83 | 0.85 | 0.80 | 0.64 | 0.58 |
| turn-hold ratio | 1.009 | 1.009 | 1.010 | 1.009 | 1.010 | 1.009 | 1.009 | 0.990 | 0.992 | 0.976 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 4 | 4 | 5 | 3 | 11 | 3 | 3 | 3 | 6 | 7 |
| +-1 deg fit gain (ssm) | 0.94 | 0.94 | 0.87 | 0.95 | 0.95 | 0.95 | 0.95 | 0.91 | 0.82 | 0.70 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.05 | 0.05 | 0.05 | 0.04 | 0.05 | 0.04 | 0.04 | 0.05 | 0.04 | 0.06 |
| hunt p2p deg (rh holds) | 0.17 | 0.16 | 0.33 | 0.12 | 0.19 | 0.13 | 0.08 | 0.11 | 0.47 | 0.70 |
| step overshoot % | 2 | 2 | 2 | 2 | 0 | 2 | 2 | -2 | -2 | -4 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.46 | 0.46 | 0.46 | 0.46 | 0.44 | 0.46 | 0.47 | 0.33 | 0.25 | 0.08 |
| lurch, LIGHT hand tq 400: overshoot deg | 2.56 | 2.54 | 2.63 | 2.49 | 2.60 | 2.49 | 2.33 | 2.29 | 2.44 | 2.37 |
| lurch, light hand tq 1000: overshoot deg | 0.43 | 0.44 | 0.45 | 0.44 | 0.41 | 0.45 | 0.45 | 0.33 | 0.27 | 0.11 |
| override-latch overshoot deg | -0.03 | -0.03 | -0.01 | -0.00 | -0.05 | 0.00 | -0.01 | -0.11 | -0.04 | -0.15 |
| engage droop deg | 1.27 | 1.27 | 1.30 | 1.25 | 1.09 | 1.25 | 1.18 | 1.22 | 1.34 | 1.19 |
| engage peak T | 189 | 189 | 191 | 191 | 188 | 191 | 191 | 183 | 187 | 185 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 2.41 | 2.42 | 2.38 | 2.45 | 2.39 | 2.45 | 2.45 | 2.34 | 2.33 | 2.17 |
| 5-30 Hz T rms in holds (texture) | 0.43 | 0.42 | 1.40 | 0.33 | 5.40 | 0.39 | 0.48 | 0.98 | 0.43 | 0.71 |
| 5-30 Hz T rms (s05) | 0.62 | 0.59 | 3.26 | 0.53 | 1.91 | 0.54 | 1.14 | 0.88 | 0.52 | 0.75 |
| 40-200 Hz T rms (s05) | 0.19 | 0.20 | 2.85 | 0.20 | 0.57 | 0.20 | 0.31 | 0.26 | 0.18 | 0.21 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.09/0.38 | 0.09/0.38 | 0.08/0.38 | 0.10/0.38 | 0.09/0.38 | 0.10/0.38 | 0.11/0.38 | 0.10/0.38 | 0.08/0.38 | 0.09/0.38 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.05 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**26 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.00 | 1.00 | 0.98 | 1.00 | 1.05 | 1.00 | 1.00 | 0.96 | 0.98 | 0.90 |
| tracking 0.2 Hz phase deg | -15 | -15 | -23 | -12 | -19 | -12 | -11 | -16 | -19 | -22 |
| tracking 0.5 Hz fit gain | 1.04 | 1.05 | 0.76 | 1.07 | 1.01 | 1.07 | 1.07 | 1.00 | 0.90 | 0.76 |
| turn-hold ratio | 1.002 | 1.002 | 1.006 | 0.992 | 1.016 | 0.994 | 1.000 | 1.014 | 1.009 | 0.986 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 2 | 2 | 3 | 5 | 8 | 5 | 4 | 10 | 3 | 5 |
| +-1 deg fit gain (ssm) | 1.05 | 1.05 | 0.99 | 1.06 | 1.10 | 1.06 | 1.05 | 1.01 | 0.99 | 0.86 |
| hold slips (rh) | 3 | 3 | 1 | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.03 | 0.04 | 0.03 | 0.03 | 0.03 | 0.02 | 0.03 | 0.14 | 0.04 | 0.04 |
| hunt p2p deg (rh holds) | 0.16 | 0.17 | 0.13 | 0.19 | 0.13 | 0.20 | 0.16 | 0.03 | 0.05 | 0.12 |
| step overshoot % | 10 | 10 | 7 | 10 | 9 | 10 | 10 | 2 | 4 | -3 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.30 | 0.30 | 0.34 | 0.30 | 0.27 | 0.30 | 0.31 | 0.20 | 0.21 | 0.14 |
| lurch, LIGHT hand tq 400: overshoot deg | 2.82 | 2.81 | 3.36 | 2.76 | 2.87 | 2.76 | 2.51 | 2.48 | 2.71 | 2.59 |
| lurch, light hand tq 1000: overshoot deg | 0.28 | 0.28 | 0.32 | 0.28 | 0.26 | 0.28 | 0.29 | 0.20 | 0.22 | 0.15 |
| override-latch overshoot deg | 0.05 | 0.05 | 0.05 | 0.05 | 0.06 | 0.05 | 0.05 | -0.05 | 0.00 | -0.04 |
| engage droop deg | 0.59 | 0.59 | 0.68 | 0.57 | 0.41 | 0.58 | 0.55 | 0.56 | 0.61 | 0.55 |
| engage peak T | 103 | 102 | 102 | 103 | 100 | 103 | 104 | 98 | 100 | 94 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | 0.00 | -0.00 | -0.00 | -0.00 | 0.00 | 0.00 | -0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 1.47 | 1.46 | 1.47 | 1.46 | 1.48 | 1.45 | 1.46 | 1.37 | 1.47 | 1.38 |
| 5-30 Hz T rms in holds (texture) | 0.44 | 0.44 | 1.20 | 0.38 | 4.41 | 0.44 | 0.61 | 0.57 | 0.36 | 0.51 |
| 5-30 Hz T rms (s05) | 0.83 | 0.86 | 3.83 | 0.91 | 2.18 | 0.88 | 1.64 | 1.27 | 0.78 | 1.11 |
| 40-200 Hz T rms (s05) | 0.20 | 0.21 | 2.19 | 0.21 | 0.53 | 0.21 | 0.33 | 0.27 | 0.20 | 0.22 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.06/0.23 | 0.07/0.23 | 0.04/0.23 | 0.06/0.23 | 0.06/0.23 | 0.06/0.23 | 0.08/0.23 | 0.08/0.23 | 0.06/0.23 | 0.07/0.23 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**30 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.99 | 0.99 | 0.98 | 0.99 | 1.03 | 0.99 | 0.99 | 0.92 | 0.97 | 0.88 |
| tracking 0.2 Hz phase deg | -14 | -12 | -23 | -12 | -19 | -12 | -11 | -17 | -18 | -21 |
| tracking 0.5 Hz fit gain | 1.03 | 1.06 | 0.76 | 1.05 | 0.97 | 1.05 | 1.06 | 0.97 | 0.91 | 0.77 |
| turn-hold ratio | 1.000 | 0.993 | 1.010 | 0.994 | 1.019 | 0.993 | 0.998 | 1.018 | 1.008 | 0.983 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 4 | 6 | 6 | 6 | 10 | 6 | 6 | 6 | 0 | 8 |
| +-1 deg fit gain (ssm) | 1.06 | 1.07 | 1.01 | 1.06 | 1.10 | 1.06 | 1.05 | 1.02 | 1.01 | 0.88 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.03 | 0.03 | 0.05 | 0.02 | 0.04 | 0.02 | 0.03 | 0.14 | 0.04 | 0.05 |
| hunt p2p deg (rh holds) | 0.15 | 0.18 | 0.11 | 0.17 | 0.12 | 0.18 | 0.16 | 0.02 | 0.05 | 0.07 |
| step overshoot % | 15 | 15 | 12 | 16 | 14 | 16 | 16 | 6 | 9 | 1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.31 | 0.31 | 0.32 | 0.31 | 0.29 | 0.31 | 0.31 | 0.21 | 0.23 | 0.16 |
| lurch, LIGHT hand tq 400: overshoot deg | 2.91 | 2.89 | 3.52 | 2.84 | 2.95 | 2.85 | 2.58 | 2.55 | 2.80 | 2.66 |
| lurch, light hand tq 1000: overshoot deg | 0.30 | 0.30 | 0.31 | 0.30 | 0.25 | 0.30 | 0.31 | 0.20 | 0.23 | 0.17 |
| override-latch overshoot deg | 0.10 | 0.10 | 0.10 | 0.10 | 0.09 | 0.10 | 0.10 | 0.00 | 0.05 | 0.00 |
| engage droop deg | 0.46 | 0.45 | 0.53 | 0.45 | 0.27 | 0.45 | 0.40 | 0.42 | 0.46 | 0.40 |
| engage peak T | 80 | 82 | 81 | 82 | 78 | 82 | 82 | 75 | 80 | 75 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | -0.00 | 0.00 | 0.00 | -0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 1.26 | 1.26 | 1.27 | 1.26 | 1.27 | 1.26 | 1.27 | 1.17 | 1.27 | 1.18 |
| 5-30 Hz T rms in holds (texture) | 0.45 | 0.44 | 1.06 | 0.40 | 4.61 | 0.44 | 0.63 | 0.79 | 0.35 | 0.51 |
| 5-30 Hz T rms (s05) | 0.95 | 1.03 | 3.75 | 0.97 | 2.26 | 0.99 | 1.69 | 1.42 | 0.93 | 1.34 |
| 40-200 Hz T rms (s05) | 0.21 | 0.21 | 1.96 | 0.21 | 0.48 | 0.21 | 0.32 | 0.27 | 0.20 | 0.22 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.05/0.19 | 0.05/0.19 | 0.04/0.19 | 0.06/0.19 | 0.06/0.19 | 0.06/0.19 | 0.06/0.19 | 0.06/0.19 | 0.05/0.19 | 0.06/0.19 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.04 | 0.04 | 0.03 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Time domain, member **bc** (ds_time.run: harness_time's plant / scenarios / metrics, the integer lane, EMA rate sensor, fixed seed 11)

**3 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.02 | 1.00 | 0.98 | 1.00 | 1.00 | 1.00 | 0.99 | 0.99 | 0.97 | 0.96 |
| tracking 0.2 Hz phase deg | -3 | -2 | -1 | -1 | -2 | -1 | -1 | -2 | -10 | -9 |
| tracking 0.5 Hz fit gain | 1.24 | 1.19 | 1.11 | 1.19 | 1.19 | 1.19 | 1.14 | 1.14 | 0.99 | 0.96 |
| turn-hold ratio | 1.003 | 1.001 | 0.999 | 1.000 | 1.000 | 1.001 | 1.001 | 1.001 | 1.002 | 1.001 |
| dwell-then-jump events (s02+s05+ssm) | 4 | 5 | 3 | 5 | 4 | 5 | 4 | 4 | 4 | 4 |
| stick % (s02) | 10 | 10 | 9 | 10 | 10 | 10 | 9 | 9 | 11 | 10 |
| +-1 deg fit gain (ssm) | 1.43 | 1.32 | 1.21 | 1.31 | 1.22 | 1.33 | 1.26 | 1.20 | 1.03 | 0.72 |
| hold slips (rh) | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.11 | 0.07 | 0.06 | 0.06 | 0.10 | 0.09 | 0.06 | 0.05 | 0.25 | 0.09 |
| hunt p2p deg (rh holds) | 2.81 | 2.45 | 1.03 | 2.41 | 2.30 | 2.47 | 1.85 | 1.83 | 0.00 | 0.00 |
| step overshoot % | 11 | 12 | 42 | 14 | 11 | 13 | 9 | 8 | 1 | 0 |
| lurch, FIRM hand (tq 2400): overshoot deg | 4.85 | 5.19 | 18.61 | 6.04 | 5.03 | 5.72 | 3.98 | 3.55 | 1.71 | 1.52 |
| lurch, LIGHT hand tq 400: overshoot deg | 4.74 | 5.71 | 20.54 | 6.56 | 6.10 | 6.23 | 4.35 | 3.87 | 1.22 | 2.32 |
| lurch, light hand tq 1000: overshoot deg | 4.80 | 5.65 | 20.49 | 6.51 | 5.94 | 6.16 | 4.34 | 3.87 | 1.36 | 2.32 |
| override-latch overshoot deg | 0.30 | 0.05 | 0.08 | -0.01 | -0.03 | 0.06 | -0.03 | -0.13 | -0.03 | -0.13 |
| engage droop deg | 5.80 | 5.21 | 4.62 | 5.17 | 4.91 | 5.20 | 4.40 | 4.55 | 5.84 | 4.53 |
| engage peak T | 397 | 406 | 407 | 405 | 397 | 405 | 403 | 399 | 389 | 378 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 33.04 | 33.08 | 33.12 | 33.08 | 33.26 | 33.06 | 33.11 | 33.13 | 33.51 | 32.98 |
| 5-30 Hz T rms in holds (texture) | 0.56 | 0.66 | 2.58 | 0.57 | 1.09 | 0.61 | 0.91 | 0.84 | 0.42 | 0.65 |
| 5-30 Hz T rms (s05) | 2.53 | 2.68 | 5.89 | 2.33 | 2.82 | 2.45 | 3.68 | 3.38 | 2.95 | 3.75 |
| 40-200 Hz T rms (s05) | 0.64 | 0.78 | 26.60 | 0.79 | 4.17 | 0.77 | 1.82 | 1.33 | 0.52 | 0.82 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 1.41/1.80 | 1.81/1.80 | 1.74/1.80 | 1.81/1.80 | 1.90/1.80 | 1.80/1.80 | 1.85/1.80 | 1.81/1.80 | 1.29/1.80 | 1.63/1.80 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.22 | 0.23 | 0.23 | 0.23 | 0.23 | 0.22 | 0.22 | 0.23 | 0.21 | 0.22 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**5 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 1.00 | 0.99 | 0.97 | 0.99 | 0.99 | 0.99 | 0.99 | 0.98 | 0.95 | 0.94 |
| tracking 0.2 Hz phase deg | -4 | -3 | -3 | -3 | -3 | -3 | -2 | -4 | -13 | -11 |
| tracking 0.5 Hz fit gain | 1.14 | 1.12 | 1.04 | 1.12 | 1.12 | 1.12 | 1.10 | 1.09 | 0.93 | 0.91 |
| turn-hold ratio | 0.999 | 1.000 | 0.999 | 1.000 | 1.001 | 1.000 | 1.000 | 1.001 | 1.000 | 0.998 |
| dwell-then-jump events (s02+s05+ssm) | 4 | 2 | 1 | 4 | 0 | 2 | 0 | 0 | 4 | 2 |
| stick % (s02) | 10 | 10 | 9 | 9 | 10 | 9 | 8 | 9 | 13 | 11 |
| +-1 deg fit gain (ssm) | 1.26 | 1.21 | 1.14 | 1.20 | 1.18 | 1.21 | 1.18 | 1.13 | 1.07 | 0.90 |
| hold slips (rh) | 3 | 2 | 3 | 2 | 3 | 2 | 2 | 2 | 0 | 3 |
| dead zone: hold error deg (rh) | 0.05 | 0.03 | 0.05 | 0.03 | 0.08 | 0.03 | 0.03 | 0.13 | 0.02 | 0.10 |
| hunt p2p deg (rh holds) | 1.48 | 1.39 | 0.40 | 1.41 | 1.34 | 1.42 | 1.11 | 0.99 | 0.14 | 0.57 |
| step overshoot % | 14 | 17 | 34 | 21 | 16 | 20 | 15 | 12 | 1 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 4.67 | 5.09 | 10.14 | 5.62 | 4.89 | 5.50 | 4.12 | 3.77 | 0.89 | 1.10 |
| lurch, LIGHT hand tq 400: overshoot deg | 5.30 | 6.47 | 13.49 | 6.88 | 6.75 | 6.78 | 5.77 | 5.27 | 1.59 | 4.73 |
| lurch, light hand tq 1000: overshoot deg | 4.71 | 5.53 | 11.93 | 6.08 | 5.36 | 5.95 | 4.88 | 4.52 | 1.77 | 3.09 |
| override-latch overshoot deg | -0.01 | -0.03 | -0.02 | -0.03 | -0.03 | -0.02 | -0.03 | -0.12 | -0.04 | -0.14 |
| engage droop deg | 5.54 | 5.16 | 4.77 | 5.08 | 4.93 | 5.11 | 4.39 | 4.56 | 5.81 | 4.59 |
| engage peak T | 356 | 361 | 365 | 361 | 361 | 361 | 360 | 357 | 345 | 356 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | -0.00 | 0.00 | -0.00 | -0.00 | -0.00 | -0.00 | -0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 20.67 | 20.54 | 20.77 | 20.54 | 20.66 | 20.53 | 20.52 | 20.58 | 20.43 | 20.25 |
| 5-30 Hz T rms in holds (texture) | 0.57 | 0.62 | 2.13 | 0.52 | 1.39 | 0.59 | 0.92 | 0.81 | 0.39 | 0.82 |
| 5-30 Hz T rms (s05) | 1.48 | 1.65 | 3.88 | 1.44 | 2.13 | 1.54 | 2.40 | 2.36 | 1.80 | 2.27 |
| 40-200 Hz T rms (s05) | 0.41 | 0.48 | 18.78 | 0.48 | 2.27 | 0.48 | 1.09 | 0.79 | 0.31 | 0.50 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 1.40/1.69 | 1.61/1.69 | 1.63/1.69 | 1.65/1.69 | 1.71/1.69 | 1.64/1.69 | 1.64/1.69 | 1.60/1.69 | 1.22/1.69 | 1.50/1.69 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.16 | 0.18 | 0.18 | 0.18 | 0.18 | 0.18 | 0.21 | 0.20 | 0.14 | 0.20 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**8 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.97 | 0.96 | 0.95 | 0.96 | 0.97 | 0.96 | 0.96 | 0.96 | 0.91 | 0.89 |
| tracking 0.2 Hz phase deg | -6 | -5 | -5 | -4 | -5 | -4 | -3 | -5 | -16 | -12 |
| tracking 0.5 Hz fit gain | 1.03 | 1.03 | 0.94 | 1.03 | 1.03 | 1.03 | 1.02 | 1.01 | 0.83 | 0.84 |
| turn-hold ratio | 1.001 | 1.001 | 0.999 | 1.001 | 0.998 | 1.001 | 1.001 | 1.001 | 0.999 | 0.996 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 5 | 5 | 4 | 4 | 5 | 4 | 3 | 4 | 8 | 6 |
| +-1 deg fit gain (ssm) | 1.07 | 1.06 | 1.02 | 1.06 | 1.07 | 1.06 | 1.06 | 1.01 | 0.97 | 0.90 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 1 | 0 | 4 |
| dead zone: hold error deg (rh) | 0.03 | 0.03 | 0.04 | 0.03 | 0.07 | 0.03 | 0.03 | 0.13 | 0.03 | 0.03 |
| hunt p2p deg (rh holds) | 0.55 | 0.41 | 0.09 | 0.28 | 0.58 | 0.29 | 0.28 | 0.38 | 0.87 | 1.16 |
| step overshoot % | 7 | 11 | 7 | 15 | 11 | 14 | 10 | 6 | -0 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 3.26 | 3.66 | 4.47 | 4.16 | 3.32 | 4.11 | 3.24 | 2.66 | 0.31 | 0.97 |
| lurch, LIGHT hand tq 400: overshoot deg | 6.07 | 6.51 | 8.94 | 6.72 | 6.84 | 6.74 | 5.74 | 5.37 | 3.16 | 5.26 |
| lurch, light hand tq 1000: overshoot deg | 3.78 | 4.38 | 6.00 | 4.85 | 4.05 | 4.84 | 4.14 | 3.71 | 0.80 | 2.39 |
| override-latch overshoot deg | -0.03 | -0.03 | -0.03 | -0.03 | -0.04 | -0.03 | -0.03 | -0.13 | -0.03 | -0.15 |
| engage droop deg | 5.31 | 5.12 | 4.96 | 5.01 | 4.94 | 5.02 | 4.43 | 4.58 | 5.79 | 4.67 |
| engage peak T | 314 | 314 | 317 | 314 | 314 | 314 | 315 | 313 | 313 | 318 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | -0.00 | 0.00 | 0.00 | 0.00 | -0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 14.16 | 14.16 | 14.11 | 14.17 | 14.30 | 14.17 | 14.17 | 14.19 | 14.03 | 13.84 |
| 5-30 Hz T rms in holds (texture) | 0.62 | 0.69 | 2.21 | 0.65 | 0.88 | 0.68 | 1.06 | 0.83 | 0.53 | 0.93 |
| 5-30 Hz T rms (s05) | 1.18 | 1.32 | 3.98 | 1.03 | 2.19 | 1.09 | 2.26 | 1.55 | 0.93 | 1.38 |
| 40-200 Hz T rms (s05) | 0.32 | 0.34 | 11.43 | 0.35 | 1.37 | 0.36 | 0.74 | 0.54 | 0.22 | 0.35 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 2.00/2.26 | 2.10/2.26 | 2.05/2.26 | 2.23/2.26 | 2.42/2.26 | 2.23/2.26 | 2.16/2.26 | 2.11/2.26 | 1.36/2.26 | 1.85/2.26 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.13 | 0.14 | 0.13 | 0.14 | 0.14 | 0.14 | 0.16 | 0.15 | 0.11 | 0.15 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**10 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.98 | 0.99 | 0.95 | 0.99 | 0.99 | 0.99 | 0.98 | 0.97 | 0.91 | 0.86 |
| tracking 0.2 Hz phase deg | -12 | -15 | -16 | -17 | -17 | -17 | -17 | -16 | -24 | -22 |
| tracking 0.5 Hz fit gain | 1.02 | 0.99 | 0.85 | 0.96 | 0.97 | 0.96 | 0.94 | 0.95 | 0.74 | 0.74 |
| turn-hold ratio | 0.998 | 0.999 | 1.002 | 1.000 | 1.010 | 1.000 | 1.001 | 0.999 | 0.998 | 0.991 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 9 | 10 | 12 | 11 | 11 | 11 | 11 | 10 | 13 | 12 |
| +-1 deg fit gain (ssm) | 1.12 | 1.13 | 1.04 | 1.13 | 1.09 | 1.13 | 1.12 | 1.07 | 0.91 | 0.81 |
| hold slips (rh) | 3 | 3 | 0 | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.05 | 0.05 | 0.07 | 0.06 | 0.04 | 0.06 | 0.06 | 0.13 | 0.04 | 0.13 |
| hunt p2p deg (rh holds) | 0.42 | 0.34 | 0.36 | 0.42 | 0.46 | 0.43 | 0.48 | 0.28 | 1.19 | 1.46 |
| step overshoot % | 3 | 3 | 0 | 3 | 2 | 3 | 3 | 1 | -0 | -1 |
| lurch, FIRM hand (tq 2400): overshoot deg | 1.86 | 1.94 | 2.07 | 2.00 | 2.11 | 1.98 | 2.00 | 1.67 | 0.18 | 0.08 |
| lurch, LIGHT hand tq 400: overshoot deg | 5.82 | 6.28 | 7.41 | 6.81 | 6.55 | 6.78 | 6.54 | 5.99 | 3.95 | 4.05 |
| lurch, light hand tq 1000: overshoot deg | 1.85 | 1.92 | 2.09 | 1.99 | 2.09 | 1.97 | 1.98 | 1.71 | 0.53 | 0.33 |
| override-latch overshoot deg | -0.02 | 0.02 | -0.04 | 0.05 | -0.04 | 0.05 | 0.06 | -0.09 | -0.08 | -0.24 |
| engage droop deg | 3.89 | 4.14 | 4.48 | 4.35 | 3.82 | 4.35 | 4.26 | 4.13 | 4.13 | 3.40 |
| engage peak T | 242 | 242 | 242 | 243 | 242 | 243 | 243 | 240 | 241 | 245 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| request-drop excursion deg (meas / zero worst) | 9.10 | 9.09 | 8.85 | 9.08 | 8.94 | 9.09 | 9.09 | 8.97 | 8.70 | 8.46 |
| 5-30 Hz T rms in holds (texture) | 0.43 | 0.39 | 0.83 | 0.26 | 1.03 | 0.32 | 0.35 | 0.40 | 0.38 | 0.56 |
| 5-30 Hz T rms (s05) | 0.77 | 0.56 | 1.54 | 0.47 | 2.16 | 0.52 | 0.67 | 0.68 | 0.65 | 0.83 |
| 40-200 Hz T rms (s05) | 0.19 | 0.18 | 3.50 | 0.18 | 0.84 | 0.17 | 0.22 | 0.20 | 0.17 | 0.21 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.79/1.51 | 0.65/1.51 | 0.75/1.51 | 0.55/1.51 | 0.70/1.51 | 0.55/1.51 | 0.52/1.51 | 0.59/1.51 | 0.64/1.51 | 0.81/1.51 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.09 | 0.08 | 0.08 | 0.08 | 0.08 | 0.08 | 0.08 | 0.08 | 0.08 | 0.10 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**12.5 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.99 | 0.98 | 0.93 | 0.98 | 0.99 | 0.98 | 0.98 | 0.96 | 0.86 | 0.79 |
| tracking 0.2 Hz phase deg | -20 | -25 | -28 | -25 | -29 | -25 | -23 | -25 | -40 | -36 |
| tracking 0.5 Hz fit gain | 0.90 | 0.82 | 0.68 | 0.83 | 0.77 | 0.83 | 0.85 | 0.82 | 0.54 | 0.56 |
| turn-hold ratio | 1.011 | 1.011 | 0.997 | 1.011 | 1.000 | 1.011 | 1.014 | 1.003 | 0.992 | 0.976 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 4 | 0 |
| stick % (s02) | 13 | 15 | 18 | 15 | 17 | 15 | 14 | 15 | 21 | 19 |
| +-1 deg fit gain (ssm) | 1.08 | 1.02 | 0.87 | 1.02 | 0.87 | 1.03 | 1.04 | 0.99 | 0.66 | 0.56 |
| hold slips (rh) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.24 | 0.21 | 0.04 | 0.21 | 0.06 | 0.21 | 0.24 | 0.19 | 0.05 | 0.16 |
| hunt p2p deg (rh holds) | 0.16 | 0.28 | 0.80 | 0.24 | 0.33 | 0.25 | 0.17 | 0.24 | 1.74 | 1.72 |
| step overshoot % | 1 | 0 | -1 | 0 | -1 | 0 | 1 | -2 | -2 | -4 |
| lurch, FIRM hand (tq 2400): overshoot deg | 1.08 | 1.09 | 1.03 | 1.11 | 1.08 | 1.11 | 1.13 | 0.91 | 0.01 | -0.05 |
| lurch, LIGHT hand tq 400: overshoot deg | 5.66 | 6.11 | 7.02 | 6.14 | 6.31 | 6.13 | 5.77 | 5.66 | 4.65 | 4.65 |
| lurch, light hand tq 1000: overshoot deg | 1.07 | 1.08 | 1.03 | 1.10 | 1.06 | 1.10 | 1.11 | 0.93 | 0.18 | 0.06 |
| override-latch overshoot deg | -0.03 | -0.03 | -0.04 | -0.03 | -0.04 | -0.04 | -0.04 | -0.14 | -0.19 | -0.39 |
| engage droop deg | 2.59 | 2.75 | 2.96 | 2.74 | 2.38 | 2.75 | 2.64 | 2.68 | 2.89 | 2.45 |
| engage peak T | 209 | 209 | 209 | 209 | 209 | 209 | 209 | 206 | 208 | 208 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| request-drop excursion deg (meas / zero worst) | 5.09 | 5.04 | 4.91 | 5.05 | 4.99 | 5.04 | 5.07 | 4.94 | 4.62 | 4.41 |
| 5-30 Hz T rms in holds (texture) | 0.33 | 0.30 | 0.75 | 0.26 | 0.54 | 0.29 | 0.30 | 0.30 | 0.33 | 0.43 |
| 5-30 Hz T rms (s05) | 0.51 | 0.39 | 1.33 | 0.36 | 2.04 | 0.41 | 0.51 | 0.50 | 0.42 | 0.45 |
| 40-200 Hz T rms (s05) | 0.17 | 0.16 | 1.72 | 0.17 | 0.60 | 0.17 | 0.19 | 0.17 | 0.17 | 0.18 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.32/0.91 | 0.31/0.91 | 0.36/0.91 | 0.32/0.91 | 0.35/0.91 | 0.32/0.91 | 0.31/0.91 | 0.31/0.91 | 0.29/0.91 | 0.34/0.91 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.07 | 0.06 | 0.06 | 0.06 | 0.06 | 0.07 | 0.07 | 0.07 | 0.06 | 0.07 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**15 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.91 | 0.91 | 0.90 | 0.92 | 0.92 | 0.92 | 0.93 | 0.89 | 0.81 | 0.73 |
| tracking 0.2 Hz phase deg | -27 | -27 | -24 | -25 | -31 | -26 | -23 | -26 | -40 | -37 |
| tracking 0.5 Hz fit gain | 0.73 | 0.72 | 0.68 | 0.75 | 0.67 | 0.74 | 0.76 | 0.74 | 0.52 | 0.52 |
| turn-hold ratio | 0.994 | 0.994 | 0.995 | 0.995 | 0.993 | 0.995 | 0.995 | 0.983 | 0.986 | 0.958 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 15 | 14 | 13 | 13 | 19 | 13 | 12 | 13 | 18 | 19 |
| +-1 deg fit gain (ssm) | 0.89 | 0.89 | 0.87 | 0.92 | 0.85 | 0.92 | 0.92 | 0.87 | 0.70 | 0.61 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.04 | 0.04 | 0.04 | 0.04 | 0.05 | 0.04 | 0.04 | 0.14 | 0.05 | 0.18 |
| hunt p2p deg (rh holds) | 0.53 | 0.54 | 0.55 | 0.47 | 0.62 | 0.49 | 0.38 | 0.43 | 1.32 | 1.34 |
| step overshoot % | -1 | -1 | -1 | -1 | -1 | -1 | -1 | -4 | -2 | -6 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.51 | 0.51 | 0.56 | 0.56 | 0.49 | 0.55 | 0.57 | 0.39 | -0.01 | -0.05 |
| lurch, LIGHT hand tq 400: overshoot deg | 3.40 | 3.41 | 3.23 | 3.37 | 3.52 | 3.37 | 3.14 | 3.08 | 2.95 | 2.87 |
| lurch, light hand tq 1000: overshoot deg | 0.52 | 0.52 | 0.56 | 0.55 | 0.49 | 0.55 | 0.56 | 0.42 | 0.09 | -0.05 |
| override-latch overshoot deg | -0.06 | -0.07 | -0.04 | -0.04 | -0.14 | -0.04 | -0.04 | -0.14 | -0.17 | -0.35 |
| engage droop deg | 2.20 | 2.20 | 2.11 | 2.16 | 1.99 | 2.17 | 2.08 | 2.12 | 2.33 | 2.05 |
| engage peak T | 245 | 245 | 247 | 246 | 245 | 246 | 246 | 240 | 245 | 243 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 3.49 | 3.50 | 3.48 | 3.54 | 3.48 | 3.54 | 3.56 | 3.44 | 3.26 | 3.06 |
| 5-30 Hz T rms in holds (texture) | 0.39 | 0.40 | 1.38 | 0.30 | 0.75 | 0.35 | 0.43 | 0.42 | 0.39 | 0.59 |
| 5-30 Hz T rms (s05) | 0.43 | 0.47 | 2.37 | 0.40 | 1.90 | 0.41 | 0.67 | 0.61 | 0.38 | 0.53 |
| 40-200 Hz T rms (s05) | 0.18 | 0.18 | 3.01 | 0.18 | 0.67 | 0.18 | 0.25 | 0.22 | 0.18 | 0.19 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.23/0.60 | 0.23/0.60 | 0.25/0.60 | 0.24/0.60 | 0.25/0.60 | 0.24/0.60 | 0.24/0.60 | 0.23/0.60 | 0.18/0.60 | 0.22/0.60 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**19 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.91 | 0.91 | 0.88 | 0.92 | 0.93 | 0.92 | 0.93 | 0.88 | 0.85 | 0.76 |
| tracking 0.2 Hz phase deg | -23 | -22 | -25 | -21 | -27 | -21 | -19 | -22 | -31 | -31 |
| tracking 0.5 Hz fit gain | 0.77 | 0.78 | 0.65 | 0.79 | 0.74 | 0.79 | 0.81 | 0.77 | 0.63 | 0.58 |
| turn-hold ratio | 0.991 | 0.991 | 0.991 | 0.992 | 0.991 | 0.992 | 0.992 | 0.971 | 0.990 | 0.966 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 10 | 10 | 11 | 8 | 17 | 8 | 8 | 8 | 14 | 11 |
| +-1 deg fit gain (ssm) | 0.89 | 0.89 | 0.83 | 0.91 | 0.90 | 0.91 | 0.92 | 0.86 | 0.78 | 0.68 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.04 | 0.04 | 0.05 | 0.04 | 0.05 | 0.04 | 0.04 | 0.14 | 0.04 | 0.12 |
| hunt p2p deg (rh holds) | 0.25 | 0.24 | 0.38 | 0.20 | 0.28 | 0.21 | 0.15 | 0.18 | 0.57 | 0.72 |
| step overshoot % | -2 | -2 | -2 | -2 | -2 | -2 | -2 | -6 | -2 | -6 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.31 | 0.32 | 0.32 | 0.34 | 0.30 | 0.33 | 0.34 | 0.19 | 0.07 | -0.04 |
| lurch, LIGHT hand tq 400: overshoot deg | 2.82 | 2.80 | 2.86 | 2.77 | 2.89 | 2.77 | 2.54 | 2.51 | 2.59 | 2.48 |
| lurch, light hand tq 1000: overshoot deg | 0.31 | 0.32 | 0.31 | 0.33 | 0.30 | 0.33 | 0.33 | 0.21 | 0.14 | -0.03 |
| override-latch overshoot deg | -0.04 | -0.04 | -0.05 | -0.04 | -0.05 | -0.04 | -0.04 | -0.14 | -0.05 | -0.18 |
| engage droop deg | 1.33 | 1.32 | 1.36 | 1.30 | 1.16 | 1.31 | 1.24 | 1.27 | 1.38 | 1.24 |
| engage peak T | 192 | 193 | 193 | 194 | 192 | 194 | 194 | 186 | 192 | 191 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 2.25 | 2.26 | 2.22 | 2.27 | 2.24 | 2.27 | 2.27 | 2.17 | 2.18 | 2.02 |
| 5-30 Hz T rms in holds (texture) | 0.45 | 0.44 | 1.45 | 0.32 | 0.64 | 0.40 | 0.49 | 0.41 | 0.50 | 0.74 |
| 5-30 Hz T rms (s05) | 0.58 | 0.55 | 2.94 | 0.57 | 1.99 | 0.66 | 1.03 | 0.89 | 0.56 | 0.75 |
| 40-200 Hz T rms (s05) | 0.20 | 0.20 | 2.84 | 0.21 | 0.58 | 0.20 | 0.31 | 0.25 | 0.20 | 0.21 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.15/0.38 | 0.16/0.38 | 0.14/0.38 | 0.17/0.38 | 0.18/0.38 | 0.17/0.38 | 0.17/0.38 | 0.16/0.38 | 0.13/0.38 | 0.16/0.38 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.06 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**26 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.96 | 0.96 | 0.93 | 0.98 | 0.99 | 0.98 | 0.96 | 0.90 | 0.94 | 0.87 |
| tracking 0.2 Hz phase deg | -14 | -14 | -21 | -12 | -18 | -12 | -11 | -15 | -18 | -21 |
| tracking 0.5 Hz fit gain | 0.98 | 0.97 | 0.76 | 0.98 | 0.94 | 0.98 | 0.99 | 0.93 | 0.86 | 0.76 |
| turn-hold ratio | 1.015 | 1.014 | 0.985 | 1.015 | 1.001 | 1.014 | 1.016 | 0.983 | 0.987 | 0.985 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 10 | 9 | 11 | 5 | 14 | 5 | 7 | 8 | 10 | 8 |
| +-1 deg fit gain (ssm) | 0.98 | 0.98 | 0.91 | 1.00 | 1.01 | 1.00 | 0.99 | 0.95 | 0.93 | 0.83 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.05 | 0.05 | 0.05 | 0.05 | 0.04 | 0.04 | 0.05 | 0.05 | 0.04 | 0.04 |
| hunt p2p deg (rh holds) | 0.03 | 0.03 | 0.08 | 0.02 | 0.03 | 0.02 | 0.01 | 0.03 | 0.06 | 0.20 |
| step overshoot % | 1 | 0 | -3 | 1 | -2 | 2 | 3 | -5 | -3 | -3 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.26 | 0.26 | 0.26 | 0.27 | 0.26 | 0.27 | 0.27 | 0.16 | 0.13 | 0.06 |
| lurch, LIGHT hand tq 400: overshoot deg | 3.22 | 3.21 | 3.75 | 3.17 | 3.29 | 3.18 | 2.83 | 2.80 | 3.02 | 2.82 |
| lurch, light hand tq 1000: overshoot deg | 0.26 | 0.26 | 0.26 | 0.26 | 0.24 | 0.26 | 0.25 | 0.15 | 0.16 | 0.07 |
| override-latch overshoot deg | -0.04 | -0.04 | -0.04 | -0.03 | -0.04 | -0.04 | -0.04 | -0.14 | -0.04 | -0.04 |
| engage droop deg | 0.63 | 0.62 | 0.71 | 0.60 | 0.46 | 0.61 | 0.56 | 0.58 | 0.64 | 0.56 |
| engage peak T | 98 | 99 | 99 | 100 | 99 | 100 | 100 | 94 | 97 | 97 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 1.34 | 1.32 | 1.29 | 1.36 | 1.30 | 1.37 | 1.37 | 1.25 | 1.30 | 1.26 |
| 5-30 Hz T rms in holds (texture) | 0.39 | 0.35 | 0.68 | 0.35 | 3.86 | 0.39 | 0.58 | 1.52 | 0.32 | 0.60 |
| 5-30 Hz T rms (s05) | 0.96 | 0.94 | 3.38 | 0.94 | 2.19 | 0.93 | 1.68 | 1.38 | 0.82 | 1.17 |
| 40-200 Hz T rms (s05) | 0.21 | 0.21 | 2.25 | 0.22 | 0.50 | 0.22 | 0.33 | 0.28 | 0.22 | 0.23 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.12/0.23 | 0.12/0.23 | 0.08/0.23 | 0.12/0.23 | 0.13/0.23 | 0.12/0.23 | 0.14/0.23 | 0.13/0.23 | 0.10/0.23 | 0.12/0.23 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**30 m/s**

| metric | B0 | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|---|
| tracking 0.2 Hz fit gain | 0.94 | 0.98 | 0.91 | 0.96 | 0.96 | 0.97 | 0.94 | 0.87 | 0.91 | 0.86 |
| tracking 0.2 Hz phase deg | -14 | -12 | -22 | -12 | -20 | -12 | -11 | -15 | -17 | -20 |
| tracking 0.5 Hz fit gain | 0.95 | 0.98 | 0.76 | 0.97 | 0.96 | 0.97 | 0.98 | 0.90 | 0.87 | 0.76 |
| turn-hold ratio | 1.018 | 1.018 | 0.982 | 1.017 | 1.005 | 1.017 | 1.018 | 0.980 | 0.985 | 0.982 |
| dwell-then-jump events (s02+s05+ssm) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stick % (s02) | 15 | 10 | 14 | 6 | 18 | 10 | 11 | 10 | 17 | 10 |
| +-1 deg fit gain (ssm) | 0.99 | 1.01 | 0.92 | 1.00 | 1.02 | 1.00 | 1.00 | 0.96 | 0.94 | 0.85 |
| hold slips (rh) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dead zone: hold error deg (rh) | 0.05 | 0.04 | 0.05 | 0.04 | 0.05 | 0.04 | 0.05 | 0.05 | 0.05 | 0.05 |
| hunt p2p deg (rh holds) | 0.02 | 0.01 | 0.03 | 0.01 | 0.01 | 0.02 | 0.01 | 0.01 | 0.04 | 0.15 |
| step overshoot % | 7 | 8 | 0 | 7 | 2 | 7 | 8 | -0 | 1 | 0 |
| lurch, FIRM hand (tq 2400): overshoot deg | 0.27 | 0.28 | 0.28 | 0.28 | 0.25 | 0.28 | 0.27 | 0.15 | 0.15 | 0.11 |
| lurch, LIGHT hand tq 400: overshoot deg | 3.32 | 3.31 | 3.94 | 3.28 | 3.40 | 3.28 | 2.92 | 2.89 | 3.13 | 2.92 |
| lurch, light hand tq 1000: overshoot deg | 0.25 | 0.26 | 0.27 | 0.27 | 0.24 | 0.26 | 0.26 | 0.16 | 0.19 | 0.11 |
| override-latch overshoot deg | 0.01 | 0.02 | 0.00 | 0.02 | 0.01 | 0.02 | 0.01 | -0.09 | 0.01 | 0.01 |
| engage droop deg | 0.47 | 0.47 | 0.55 | 0.46 | 0.29 | 0.46 | 0.42 | 0.45 | 0.48 | 0.42 |
| engage peak T | 78 | 79 | 78 | 80 | 78 | 79 | 80 | 75 | 77 | 77 |
| sentinel push deg toward the sentinel (L / R worst; <= 0 = none) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| request-drop excursion deg (meas / zero worst) | 1.14 | 1.19 | 1.10 | 1.17 | 1.11 | 1.17 | 1.16 | 1.07 | 1.11 | 1.10 |
| 5-30 Hz T rms in holds (texture) | 0.33 | 0.41 | 0.59 | 0.36 | 0.08 | 0.38 | 0.55 | 1.67 | 0.34 | 0.53 |
| 5-30 Hz T rms (s05) | 0.82 | 0.87 | 3.43 | 0.91 | 2.21 | 0.90 | 1.73 | 1.33 | 0.76 | 1.21 |
| 40-200 Hz T rms (s05) | 0.21 | 0.21 | 2.00 | 0.21 | 0.48 | 0.21 | 0.32 | 0.26 | 0.21 | 0.23 |
| hard-turn 1.6-3 Hz wheel rate rms / ref | 0.10/0.19 | 0.10/0.19 | 0.07/0.19 | 0.11/0.19 | 0.10/0.19 | 0.11/0.19 | 0.12/0.19 | 0.11/0.19 | 0.09/0.19 | 0.10/0.19 |
| detector max abs(gp-0x6c2c) / 12800 (all scen.) | 0.05 | 0.05 | 0.04 | 0.05 | 0.04 | 0.05 | 0.05 | 0.05 | 0.04 | 0.05 |
| detector max reversals (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| int32 wraps (all scen.) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


---

## 7. Concerns and open items

1. **Everything above ~8 Hz is model, not measurement** (the r71b ident sees nothing above 8 Hz). The 5–25 Hz rankings rest on
   the hold, the EMA, the output lag and the transport delay, which are bytes; the plant there is BELIEF.
2. **The rate model changes the baseline's numbers.** The bytes say x is the held EMA of the motor rate (§1.2); the C1 pages
   used a 3-tick position difference or the ideal rate. Under the EMA, B0's Re(T/ω) and PM move by 0.1–3° (§1.3). Every
   design number here uses the EMA; the C1 pages' numbers are not directly comparable without re-running them under it.
3. **ms_free at PM ≥ 45° (the brief's single corner) binds every design at 10–12.5 m/s** and costs the C1 lib table
   (B0) 12 sub-bar points. If the judges treat ms_free as report-only (C1r2's choice), every envelope here rises at
   10–12.5 m/s by up to ×1.3 (B0 `env_final_B0.json` per-member results) — and D3b's advantage there shrinks.
4. **The D1b frame scale** (motor counts per degree of gp-0x6a00) varies ×0.83–1.0 with the steering angle (the VGR
   correction); the gate used the low end. Measuring the D gain on the car (instrument §5.3) settles it.
5. **No candidate removes the low-speed friction misses** (dj 4–9 events per scenario set at 3–5 m/s, stick 8–11 % at
   3 m/s, light-hand lurch 5.7–6.9° on the angle kind). Structure does not fix friction; a friction term (C1r2 §6.4's C2)
   would sit in any of these caves.
6. **The light-hand case is the worst release on every angle-kind design** (5.7–6.9° on nominal/bc at a hand below the
   512 freeze threshold): the I winds behind a hand the freeze cannot see. Common to the structure class; declared.
7. **The cave encodings are BELIEF until Ghidra decodes a built image (H5)**, despite 27 form controls, 11 exact-byte
   Ghidra decodes and 0 / 60 000 interpreter mismatches per cave.
8. **GATE 1 for gp-0x6c40 / gp-0x6c44 is static** (0 accesses of every form, controlled); register-indirect access cannot be
   excluded statically. V289's flown cave used these words (record) — on-car precedent, not proof for this image.
9. **The setpoint-hold age** (frame before or after the lane in the arrival tick) is 1 ms of BELIEF; the linear model uses
   1..10, harness_time 0..9.
10. **The C1r2 page and the C1 lib disagree on the table** (the lib's 7-knot table is a later refit; the page's 6-knot table
    fails the factorial b/1.9×J1.0×tau6+h10 at PM 8.7°). I scored the lib (B0) and my own refit (B0r). Reported, not fixed.
11. **The fork interlock byte V1 is counted in every candidate's bytes** (1 byte) for parity with C1r2; it is a fork
    prerequisite, not a loop term.
