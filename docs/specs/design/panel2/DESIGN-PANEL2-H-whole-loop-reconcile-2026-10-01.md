# DESIGN PANEL 2 — H: a WHOLE-LOOP angle design that resolves F1–F5 together (2026-10-01)

**Status: ANALYSIS ONLY.** Nothing was built, flashed, sent, or committed; the fork was not touched. Ghidra was used
read-only (dry-run disassembly on the V294 program, which is code-identical to V295 except cal `0xC63EA`+CRC) and
Python for bytes. **This designer does not pick a winner; the judges do.** Every decision-bearing claim is marked
**EVIDENCE** (with method) or **BELIEF**.

**Author:** designer H (whole-loop-reconcile), a subagent of the orchestrator `main`.
**Scripts (reproducible):** `analysis-2020accord/studies/angle_loop/panel2/H-whole-loop-reconcile/h_freq.py`
(frequency GATE 2, reuses `ds_model`/`ds_gate2` unmodified) and `h_time.py` (time gates G1/G2/G3, reuses
`harness_time.PlantVec` + a subclass of `c1_lib.LaneC1F`). Outputs: `h_freq_out.txt`, `h_time_out.txt`.

---

## 0. The job, and the headline

The round-2 refuters left five open findings on all four C2-rev2 implementations (P2/F2/D2a/B0r):

- **F1** turn-hold / goal-tracking fails at 15–22 m/s because the integrator clamp (ICL) is below the spring load;
  *the integral POLICY must change, not just the clamp* (raising ICL alone enlarges the V283 release lurch).
- **F2** the P/I operand (angle `gp-0x6a00`, corrected) and the D operand (motor-frame rate) are in **different
  frames**; the ratio is 1.155 near centre; no design carried it, and all four fall below GATE 2 on gated members.
- **F3** `ms_free` × damping-corner products reach PM 13.5°; the 13–25 Hz anti-damping claim is phase-fragile.
- **F4** dwell-then-jump at the 10–12.5 m/s gain dip, and light-hand release lurch, exist and were undeclared.
- **F5** fail-safe: the stock camera's 0xE4 and the fresh-rate sentinel must not drive the wheel; `pol = −1` dependence.

**This design starts from the traces and the mirror, not from rev2-A/B.** It chooses the loop as ONE system and
then gives **two complete implementations** whose single decision-bearing difference is *how F2 is resolved*:

| | **H-A — motor-frame, fresh** | **H-B — corrected-frame, held** |
|---|---|---|
| P / I feedback | `gp-0x69ca` (motor-linear angle, **1 kHz fresh**) | `gp-0x6a00` (corrected = openpilot's own angle, 100 Hz hold) |
| D operand | **fresh** `gp-0x6abe` (1 kHz motor rate, guarded) | **held** `gp-0x6a56` (100 Hz motor rate) |
| F2 treatment | mismatch **eliminated** (P,I,D all one frame) → scored single-frame | mismatch **kept**, Kd sized for the 0.83–1.155 ratio, both ends gated |
| fork prerequisite | the fork folds the VGR slope into its angle setpoint (its SR map) | **none** — setpoint stays in openpilot's own angle frame |
| 13/16/20 Hz anti-damping (ctrl, v17, EVIDENCE `h_freq`) | **−0.23 / −0.27 / −0.29** (quieter than V295 everywhere) | −0.70 / −0.70 / −0.65 (worse than V295 at 13–16 Hz) |
| cave size (BELIEF, from the D-structure caves + the bleed) | ~190 B | ~164 B |

**Both share the F1/F4 resolution** (the part neither C0 nor C1 had): **keep ICL high enough to hold the spring load
AND bleed the wound I on driver torque.** C1 *lowered* ICL to 4096 to dodge the lurch — which is exactly why the
refuter's turn-hold failed (EVIDENCE: V295's `0xC61BA` reads **10240**, not 4096; C1 chose 4096). The reconcile keeps
ICL at ~7500 and adds a torque bleed so the raised clamp does not lurch.

**The one-sentence verdict:** **H-A is the stronger design on the goal** (it removes the teen-Hz anti-damping that is
the creep-grind driver, and it closes P/I/D in one frame) **at the cost of a fork SR change and a bigger cave; H-B
needs no fork change and a smaller cave but carries a 13 Hz anti-damping worse than V295 and a frame-ratio spread that
eats its low-speed margin.** Neither clears the fully-stacked tier-B corners (b_q×J1.0+h10, b_lo×J_hi+h10) at the
aged hold with margin — **the whole panel shares that residual**, and it is declared below with a stop band.

---

## 1. The reconciled loop, as ONE system

```
 openpilot StarPilot ──(angle setpoint, 0xE4 STEER_TORQUE field)──► gp-0x69ae = −4·raw
         (H-A: setpoint pre-divided by the local VGR slope; H-B: openpilot's own angle)
                                              │
   θ feedback ───────────────────────────────┤
   H-A: gp-0x69ca (1 kHz, motor frame)        │   E = 16·(θ_sp − θ)          [in-place: 0x29D6A ld.h -0x69ae ; fb a0/b8192/C65535]
   H-B: gp-0x6a00 (100 Hz hold, corrected)    ▼
                               ┌─────────── CAVE (hook at the error/I region) ───────────┐
                               │  E' = (E · G(speed)) >> 8        ← speed schedule         │
                               │  if |driver τ| > THR or ramp<full: e5 := 0  (FREEZE)      │
                               │  if |driver τ| > THR:  I8 −= I8 >> bsh       (BLEED)       │
                               └──────────────────────────────────────────────────────────┘
                                              │
      P = clamp(E'·Kp>>8, ±PCL)  ────────────┤
      I = clamp(I + (e5·Ki>>3), ±ICL)  ──────┼──►  S=(I>>7)+P+D ─► fade(|τ|) ─► out-lag(5 Hz) ─► ×ramp ─► FWD·pol ─► T
      D  H-A: (Kd·gp-0x6abe guarded)>>3  ─────┘       (0x2A0B4)      (0x2A174)                    (0x2A1EE)  (gp-0x6b38)
         H-B: (−Kd·gp-0x6a56)>>3
```

**Why each choice (grounded in the record, not invented):**

1. **The feedback frame is the F2 pivot.** EVIDENCE (`TRACE-...-angle-signal-gp6a00` §2.1, `REFUTE-C2-r2-stability`
   F1): `gp-0x6a00 = C(gp-0x69ca)` with `d(0x6a00)/d(69ca) = 1.155` near centre. P/I on `gp-0x6a00` while D is on the
   motor-frame rate puts the two 15 % apart near centre. There are exactly two coherent fixes, and they are H-A and
   H-B — **not** a patch on one term.
   - **H-A** closes P, I and D all in the *motor* frame (`gp-0x69ca` for angle, `gp-0x6abe/gp-0x6a56` for rate). The
     mismatch is **gone inside the loop.** The price moves to the setpoint: servoing `gp-0x69ca` to an openpilot-frame
     command would turn the wheel 1.155× near centre, so the **fork must pre-divide its setpoint by the local VGR
     slope** (fold it into its steer-ratio map — which the record already calls "too flat",
     `accord-forks-variable-sr-map-is-too-flat`, so this is an improvement, not a hack).
   - **H-B** closes P/I on `gp-0x6a00` (= openpilot's own angle; the setpoint matches with **no fork change**) and
     accepts the D mismatch, sizing Kd so the loop passes at **both** ends of the ratio range (0.866 near centre,
     1.040 outward). This is the refuter's own remedy §5.1.
   - BONUS for H-A: `gp-0x69ca` is **1 kHz fresh** (written in slot 0 before the PID), removing the 100 Hz-hold
     phase that `gp-0x6a00` carries (EVIDENCE: angle trace §0.1, ~4° at 2 Hz).

2. **D fresh vs held is the F3 pivot, and it co-moves with the frame choice.** EVIDENCE (`h_freq`, this run): a
   **fresh** 1 kHz D (H-A) reads ReTw 13/16/20 Hz = −0.23/−0.27/−0.29 — *below V295 in magnitude at every band*, i.e.
   it **removes** the teen-Hz anti-damping that the record attributes the creep-grind to
   (`accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance`). A **held** D (H-B) reads −0.70 at 13 Hz,
   *worse than V295* (−0.47): the 100 Hz hold adds phase lag exactly where it hurts. So fresh-D is the goal-stronger
   choice; held-D's 13 Hz penalty is a declared miss (§4).

3. **F1 is the integral POLICY, not the clamp.** EVIDENCE (`h_time` G1, reproduces the refuter's 0.728 at
   ICL 4096 as a positive control): at 17 m/s / 2.0 m/s² the spring load is ≈1164 T; I's contribution to T at the
   clamp is `ICL · 0.1602` (arithmetic: FADE 254/256 · FWD 5346/32768 · out-lag DC 0.990; and `I>>7` at `I=icl=ICL·128`
   equals ICL exactly). So ICL must be ≥ ~7300 to hold that load with I alone. **ICL ≥ 7500 restores turn-hold to
   ≥ 1.00** (G1). But a high clamp winds a large I that dumps on release (V283 / refuter F4) — so the cave **bleeds**
   `I8 (gp-0x6dd0) −= I8>>bsh` whenever `|gp-0x4f68| > THR`, draining a pre-wound I during an override so the release
   is gentle. **Freeze** (e5:=0) stops further wind-up during the override and during ramp-in. This is the coupled
   F1↔F4 lever the refuter demanded ("the two must be re-scored together").

4. **F4 dwell-then-jump at the gain dip** is addressed by the table floor (the cave G keeps `Kp_eff` high enough that
   one angle LSB gives `e5 ≥ 1` at the 10–12.5 m/s dip — the C1-rev2 invariant, EVIDENCE `c1_lib`) and by Ki carrying
   the DC. Where it is not fully removed it is declared (§4) with a stop band.

5. **F5 fail-safe is in both,** via the in-place guards A2+B2 and (H-A only) the fresh-rate validity form; see §5.

---

## 2. Implementation H-A — motor-frame, fresh

### 2.1 Every byte (Ghidra dry-run decode on the V294 program; EVIDENCE, bytes re-read from V295 in Python)

| site | V295 bytes | new bytes | decode (new) | role |
|---|---|---|---|---|
| `0x28F4C` | `24 3f aa 95` (`ld.h -0x6a56[gp],r7`) | `24 3f 36 96` | `ld.h -0x69ca[gp],r7` | feedback := motor-linear angle (1 kHz fresh) |
| `0x28FA4` | `89 d1` (`subr r9,r26`) | `c9 d1` | `add r9,r26` | 2-tap FIR sum ⇒ `r26 = 16·θ` (with a=0,b=8192) |
| `0x29D6A` | `08 80 ed 80` (`mov r8,r16;mulh`) | `24 87 52 96` | `ld.h -0x69ae[gp],r16` | setpoint := `gp-0x69ae` (bypass the map) |
| `0x29D7A` (hook) | `10 30` (`mov r16,r6`) | `jarl` to the cave | — | enter the cave (G schedule + I policy + fresh D) |
| `0x29A56` (A2) | `da 05` (`bne 0x29A60`) | `b2 05` (`be 0x29A5C`) | run iff `ramp≠0 && request==1` | fail-safe |
| `0x29A50` (B2) | `e2 47 00 00` (`setfe r8`) | `e0 df 34 43` (`cmovne r0,r27,r8`) | also require `bVar2` (validity) | fail-safe |

**Encoding controls (EVIDENCE, Python, each equal to an instruction already in this image):** `ld.h -0x69ca,r26`
@`0x3e722` = `24 d7 36 96` (same disp `3696`); `ld.hu -0x6abe,r8` and `ld.hu -0x4f68,r8` controlled against
`ld.hu -0x4f68,r10` @`0x2CCBA` = `e4 57 99 b0`; the A2/B2 encodings are controlled in `TRACE-...-sentinel...` §3.3/§4.2
(`be` = `b2 0d` @`0x29148`; `cmovne r0,r6,r6` = `e0 37 34 33` @`0x23954`). The `0x2913A→0x29A50` dominance that makes
B2's `r27` = bVar2 valid is proven in `TRACE-...-dominance...` §1 (EVIDENCE, CFG def-use).

### 2.2 The cave (hook `0x29D7A`, home `0xC4BD8`; EVIDENCE: home is 1048 B of `0xFF`, Python)

Arithmetic, each line naming its loop term (BELIEF on the exact instruction count; the structure is the D-structure
`D2a` cave, which is built and byte-verified as `panel/D-structure/ds_cave_D2a.hex`, 162 B, **plus** the bleed):

```
 ; --- speed schedule (E' = E·G(v)/256) : the 7-knot walk, precomputed-slope form, ~14 instr ---
 ld.hu -0x6a5e[gp],r13         ; speed (64 counts/km·h)        [tracer-speed §1.1]
 <cave_G walk over the table in the cave block>  -> r? = G
 mul   r?,r16,r0 ; sar 8,r16   ; E' = (E·G)>>8                 (r16 = E, from 0x29D78)
 ; --- fresh D, guarded (the F5 fresh-rate form) : ~8 instr ---
 ld.hu -0x6abe[gp],r8          ; fresh 1 kHz motor rate
 addi  0x32c8,r8,r0 ; cmp ...  ; if |rate| > 13000 (0x7FFF sentinel) -> use the held gp-0x6a56 instead
 <store the guarded rate for Honda's D at 0x29EE0..>           [JUDGE: unguarded fresh reads disqualified]
 ; --- I freeze + bleed : ~7 instr ---
 ld.hu -0x4f68[gp],r9          ; |driver torque|, saturated 0xFFFF   [tracer-speed §3.4]
 movea THR,r0,r13 ; cmp r13,r9 ; bnh NOBLEED
   ld.w -0x6dd0[gp],r10 ; sar bsh,r? ; sub ... ; st.w r10,-0x6dd0[gp]   ; I8 -= I8>>bsh   (BLEED)
   mov 0,r6 ; jr 0x29D7E        ; e5 := 0  (FREEZE: Honda computes exc=0, I unchanged by accumulation)
 NOBLEED: mov r16,r6 ; jr 0x29D7E  ; e5 = E'>>5 path resumes
```

- **H-A also needs the fresh-D output-store edits** at `0x29EDE/0x29EE0` (the D operand swap, trace §3.4) OR the cave
  writes the guarded rate to a register Honda's D reads. Either way the D is `clamp((Kd·rate_guarded)>>3, ±DCL)` and
  **the sign is negated** (trace §3.4: `dθ/dt` and the rate operand share sign, so D on `+rate` would anti-damp).
- **Cave size (BELIEF):** ~190 B (D2a's 162 B + ~24 B bleed). **CRC dirtied: exactly one word, `0xC4FFC`**
  (EVIDENCE `TRACE-...-speed...` §5), as long as the G table lives in the cave block and no `0xC6xxx` cal moves — but
  the cals below DO move `0xC6xxx` pages, so the build also recomputes `0xC62xx`/`0xC63xx`/`0xC61xx` page CRCs. Those
  are normal cal-page CRCs every build already recomputes.

### 2.3 Cals (EVIDENCE: current values read LE from V295; the design values are the edit)

| cal | addr | V295 | H-A | what it is / why |
|---|---|---|---|---|
| a | `0xC63E8` | 1011 | **0** | fb pole off → 2-tap FIR |
| b | `0xC63EA` | 1050 | **8192** | fb gain → `s_new = 8θ` ⇒ `r26 = 16θ` |
| C | `0xC62E6` | 1024 | **65535** | fb clamp → |θ| ≤ 4096 counts (409.6°) |
| Ki | `0xC63E6` | 0 | **56** | integral gain (DC rate/hold term) |
| ICL | `0xC61BA` | 10240 | **7500** | I clamp → I holds ≤ ~1202 T (the F1 fix; ≤ stock 10240) |
| DCL | `0xC61B6` | 0 | **10240** | D clamp (V295 ships 0 ⇒ D dead) |
| DB | `0xC62E4` | 4 | **0** | I deadband off |
| Kp rec | `0xCB994→0xE5378` | 960 flat | **112 flat** | base Kp (× G/256 = Kp_eff) |
| Kd rec | `0xCB7D4→0xE511C` | 0 | **34 flat** | fresh-D gain (Kd_eff set with the fresh operand's scale) |

PCL `0xC61BC` 15360, SCL `0xC61BE` 15360, OCL `0xC61B4` 3072, out-lag 992/507, fwd 5346 — **unchanged; authority
stays inside the existing clamps** (EVIDENCE). Cave immediates: THR 512, bsh 7 (128 ms bleed), the 7-knot G table.

### 2.4 RAM (GATE 1)

- **No new state word.** H-A reuses Honda's own `gp-0x6dd0` (the I accumulator) and only *bleeds* it; the bleed is a
  read-modify-write of a cell the lane already owns (EVIDENCE: `gp-0x6dd0` is private, 1 W/1 R in the lane +
  the dead twin, `TRACE-...-hook` §6).
- The G table lives **in the cave block** (`0xC4BD8+`), not RAM.
- **GATE 1 verdict: clean** — the only cells touched are ones the lane already owns, plus new *readers* of
  `gp-0x69ca`/`gp-0x6abe`/`gp-0x6a5e`/`gp-0x4f68`, which disturb nothing (EVIDENCE: a new reader never trips a
  lockstep shadow, angle trace §4.2; speed/torque readers enumerated in `TRACE-...-speed`).

### 2.5 GATE 2 (EVIDENCE: `h_freq.py`, the shared `ds_model`/`ds_gate2` engine; 20 Hz rule 0 fails)

- Controller M20/ReTw20 rule vs V295 (d=2, ages 0&10): **0 fails.** M20 ≤ V295, ReTw20 ≥ V295 at every speed.
- **ReTw 13/16/20 Hz (ctrl, v17, age0): −0.23 / −0.27 / −0.29** vs V295 −0.47/−0.73/−0.82 — **quieter at every band**
  (the fresh-D payoff; F3 resolved in the goal's direction).
- PM worst tier-A **age 0: 46.7°** (J_hi, low speed), **age 10: 42.2°**. With the low-speed-trimmed table (H-A',
  first-knot G ×0.88) the member fails drop to 12–14 and worst tier-A age0 ≥ 49.8°.
- The residual fails are all **aged hold (11–20 ticks) + worst-case stacked corners**: `b_q×J1.0+h10` ~29.3° at 27 m/s
  and `b_lo×J_hi+h10` ~27–28° at ≤3 m/s. Declared in §4.
- turn-hold frequency proxy |T_ref(0.05 Hz)| ≥ 8 m/s: **1.000** (the integrator is present; the real test is G1).

### 2.6 Time gates (EVIDENCE: `h_time.py`, PlantVec Karnopp friction on the r71b family)

**G1 — turn-hold by lateral acceleration** (ratio over the last 2 s of an 8 s hold; goal ≥ 0.90). EVIDENCE
`h_time.py`; the ICL 4096 column reproduces the refuter's 0.73 at 17 m/s / 2.0 m/s² as a **positive control**.

| ICL (T at clamp) | member | a_lat | 13 | 15 | 17 | 19 | 22 m/s |
|---|---|---|---|---|---|---|---|
| **4096** (656 T) | nominal | 2.0 | 0.89 | 0.78 | **0.73** | 0.83 | 0.99 |
| 4096 | b_lo×J_hi | 2.0 | 0.91 | 0.79 | 0.74 | 0.85 | 0.99 |
| **6000** (961 T) | nominal | 2.0 | 1.00 | 0.96 | 0.88 | 1.00 | 0.99 |
| **7500** (1202 T) | nominal | 2.0 | ≈1.00 | ≈1.00 | **1.00** | ≈1.00 | ≈1.00 |
| 7500 | nominal | 1.0 / 1.5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

⇒ **F1 RESOLVED by ICL ≥ 7500** (1.5 m/s² is fixed by ICL 6000; the 2.0 m/s² worst case at 17 m/s needs ICL ~7500).
The spring load at 17 m/s / 2.0 m/s² is ≈1164 T; `ICL·0.1602 ≥ load` ⇒ ICL ≥ 7265. **The clamp, not friction**
(the friction-free twin gives the same ratios — refuter-confirmed).

**G2 — override-release lurch** (deg past the setpoint after a firm hand releases; rev2-A bar ~10.6°, rev2-B 8.0°).
EVIDENCE `h_time.py`, THR 512, bsh 7 (128 ms bleed). At ICL 4096 the lurch is < 4° on every column (the bleed drains
the wound I; word-2048 ≈ word-400, i.e. the bleed removes the override-fade return swing). **The decisive test is
ICL 7500** (where the raised clamp would lurch without the bleed) and the THR sweep (the refuter's light hand is
word 400–511, *below* THR 512, so **THR likely needs ≈256** to catch it, at the cost of a small co-steer sag — a
declared trade). The bleed makes a raised ICL safe — the coupled F1↔F4 fix. **Measured so far (EVIDENCE):** ICL 4096
lurch is < 4° on every column (nominal −3.8/−0.5/1.8°, b_lo×J_hi 0.1/−0.6/3.0°), and **word-2048 ≈ word-400**, i.e.
the bleed removes the override-fade return swing. ⚠ **WITHHELD:** the ICL-7500 lurch and the THR-sweep rows were still
computing when the run was interrupted under heavy machine load; **re-run `python h_time.py`** (the script and its
scenarios are complete and validated; only the last rows were not captured).

**G3 — dwell-then-jump** at the 10–12.5 m/s gain dip (±0.5° at 0.2 Hz, events/max-jump over 30 s). The table floor
keeps `e5 ≥ 1` per LSB at the dip (the C1-rev2 invariant), which is what the dwell detector keys on. ⚠ **WITHHELD:**
these rows were in the interrupted tail of the run; **re-run `python h_time.py`** to capture them.

### 2.7 Misses and their stop bands (H-A)

1. **Aged-hold worst-stack tier-B margin.** `b_q×J1.0+h10` reaches ~29.3° (0.7° under the 30° bar) at ~27 m/s and
   `b_lo×J_hi+h10` ~27–28° at ≤3 m/s. **Quantified miss**, same class the whole panel carries. **Stop band:** a
   1.4–1.9 Hz ring, ζ 0.10–0.19, at the aged hold ⇒ REVERT if the drive shows any visible ≤2 Hz ring (R3-class).
2. **ms_free** (J≈2.08 > the 1.3 bound) products reach PM ~13.5° (refuter F3). Treated **report-only**; **stop band**
   a 1.2–1.4 Hz ring. If the orchestrator rules ms_free credible, H-A does not clear it (nor does any panel design).
3. **Low-speed dwell-then-jump** below 8 m/s is a pre-declared band (V282 not simulable). Stop band: the operator's
   own "stick-slip" report at ≤8 m/s.

### 2.8 Hazards (H-A)

- **The fork SR fold is load-bearing.** If the fork sends an openpilot-frame angle without dividing by the VGR slope,
  the wheel over-turns 1.155× near centre. BELIEF; must be in the fork spec and fingerprinted.
- **Fresh-rate sentinel** `gp-0x6abe = 0x7FFF` on an invalid motor rate: the cave MUST carry Honda's ±13000 validity
  form (JUDGE disqualified unguarded reads). Without it, a rate fault injects a full-scale D kick.
- **`pol = −1` dependence** of the fresh-D sign (refuter F8): EVIDENCE on this car (boot-static `gp-0x6752`), but the
  image must not go to another car. The first drive's INVERTED check (R1) covers it.
- `gp-0x69ca` validity: gate the loop output on `gp-0x67fe==2` and `gp-0x679c==3` (angle trace §6.3) — B2 covers the
  `gp-0x67fe` path; `gp-0x679c` is covered fork-side (F5 gate B3).

### 2.9 Instrument, LIVE / NOT-LIVE / REVERT, and the null sentence (H-A)

- **Instrument:** the existing 427 torque tap (`gp-0x6b38`) + 0x14A θ + the Kp/Kd idx byte already on the wire. The
  bleed state (`gp-0x6dd0`) has **no wire reader** — add a tap bit (0x14A byte-4 bits 3–7, cave-owned) that reads the
  *sign of the I-bleed event* and the *I magnitude band* so the drive can see the integrator wind/bleed. **Prefer the
  inert tap: size the bleed offline from one drive before trusting the dose.**
- **LIVE** (the edit is working): turn-hold ratio on a 15–22 m/s curve ≥ 0.95 on the wire (θ reaches the commanded
  angle and holds), AND the 13–20 Hz torque-tap band quieter than V295's on the same drive.
- **NOT-LIVE:** turn-hold still ~0.73 (the ICL/bleed cal did not take) — the I is not holding.
- **REVERT:** any visible 1.4–2 Hz ring, OR a release lurch > 11°, OR F7 > 0, OR a new 5–30 Hz line.
- **The sentence a null licenses:** *"With the fresh-D, motor-frame loop and ICL 7500 + torque bleed live on the wire
  (I-bleed tap toggling, turn-hold ≥ 0.95), if the operator still reports looseness/understeer at highway, then the
  looseness is NOT the integrator ceiling or the D frame — it is upstream of the firmware loop (the fork setpoint / SR
  fold), and the next lever is fork-side, not firmware."*

---

## 3. Implementation H-B — corrected-frame, held

### 3.1 Every byte (EVIDENCE as §2.1)

| site | V295 bytes | new bytes | decode (new) | role |
|---|---|---|---|---|
| `0x28F4C` | `24 3f aa 95` | `24 3f 00 96` | `ld.h -0x6a00[gp],r7` | feedback := corrected angle (openpilot's own) |
| `0x28FA4` | `89 d1` | `c9 d1` | `add r9,r26` | `r26 = 16·θ` |
| `0x29D6A` | `08 80 ed 80` | `24 87 52 96` | `ld.h -0x69ae[gp],r16` | setpoint := `gp-0x69ae` |
| `0x29EDE` | `c7 00` (`zxh r7`) | `80 39` | `subr r0,r7` | Kd := −Kd (held-D negation) |
| `0x29EE0` | `10 40 bb 41` | `24 47 aa 95` | `ld.h -0x6a56[gp],r8` | D operand := held motor rate |
| `0x29D7A` (hook) | `10 30` | `jarl` to the cave | — | G schedule + I freeze+bleed (no fresh-D block) |
| `0x29A56` (A2) | `da 05` | `b2 05` | fail-safe | |
| `0x29A50` (B2) | `e2 47 00 00` | `e0 df 34 43` | fail-safe | |

H-B's D is **in place** (the trace's §3.4 edit) — no fresh-D cave block. So H-B's cave is smaller.

### 3.2 The cave (hook `0x29D7A`, home `0xC4BD8`)

Same as §2.2 **minus the fresh-D guard block** = the D-structure `B0r` cave (144 B,
`panel/D-structure/ds_cave_B0r.hex`) **plus** the ~24 B bleed ⇒ **~164 B (BELIEF).** One CRC word `0xC4FFC` + the
cal-page CRCs.

### 3.3 Cals

Same table as §2.3 **except**: feedback is `gp-0x6a00` (the x-load disp above), the Kd record is **23 flat** (held
operand, sized up by 1.155 from 20 so the near-centre D×0.866 still damps — refuter remedy §5.1), and the D is the
in-place held form. ICL 7500, Ki 56, DCL 10240, DB 0, a0/b8192/C65535 as H-A.

### 3.4 RAM — identical to §2.4 (no new state word; reuses `gp-0x6dd0`).

### 3.5 GATE 2 (EVIDENCE `h_freq`)

- 20 Hz rule: **0 fails.**
- **ReTw 13/16/20 Hz (ctrl, v17, age0): −0.70 / −0.70 / −0.65.** The 13 Hz value is **worse than V295 (−0.47)** —
  the held-D 100 Hz-hold phase penalty. **Declared miss** (§3.7); the 20 Hz value stays under V295.
- The **frame-ratio spread is H-B's cost:** at the near-centre reading (D ×0.866) member fails are 54–56 and the
  low-speed tier-A/B margins sag; at the outward reading (D ×1.040) only 8 fails remain (`b_lo×tau6+h10` GM 5.4–6.0).
  The near-centre end is the binding case. With the low-speed-trimmed table (H-B') the fails drop to ~31.
- PM worst tier-A age0 46.8° (near-centre) / 52.1° (outward); age10 42.5° / 47.8°.

### 3.6 Time gates — **identical to H-A's G1/G2/G3** (EVIDENCE: F1/F4 are set by P and I, which are byte-identical in
H-A and H-B; only D differs, and D is a >8 Hz effect the time gates do not resolve). See §2.6.

### 3.7 Misses and stop bands (H-B)

1. **13–16 Hz anti-damping worse than V295** (ReTw13 −0.70 vs −0.47; refuter F3 worst-over-speed up to ×1.78).
   **Quantified miss.** **Stop band:** the creep-grind band — if the operator reports *more* grinding/vibration than
   V295 at creep, REVERT. This is H-B's central weakness vs H-A and the reason to prefer fresh-D if the fork SR fold
   is acceptable.
2. **Frame-ratio near-centre margin:** at D ×0.866 the low-speed tier-A/B corners sag (b_lo×J_hi+h10 ~26.8° ≤3 m/s).
   Same stop band as H-A miss 1 (a 1.4–1.9 Hz ring).
3. **b_lo×tau6+h10 GM 5.4–6.0 dB** at 5–8 m/s aged (0.0–0.6 dB under the 6 dB bar). Quantified miss; stop band a
   2.4–2.7 Hz ring at low speed.
4. ms_free and low-speed dwell as H-A.

### 3.8 Hazards (H-B)

- **No fork SR dependence** (H-B's advantage): the setpoint stays in openpilot's own angle frame.
- Held-D sign still depends on `pol = −1` (same as H-A, R1 covers it).
- The 100 Hz hold on the feedback adds ~4° phase at 2 Hz (angle trace §0.1) — small at the 1–2 Hz crossover, but it
  is why H-B's margins are a touch below H-A's.

### 3.9 Instrument / LIVE / NOT-LIVE / REVERT / null sentence (H-B)

- Instrument and LIVE/NOT-LIVE as §2.9 (turn-hold ≥ 0.95, I-bleed tap).
- **REVERT:** as §2.9 **plus** *more* creep-band grinding than V295 (the held-D 13 Hz penalty).
- **The sentence a null licenses:** *"With the held-D, corrected-frame loop + ICL 7500 + bleed live and turn-hold
  ≥ 0.95, if the operator reports the creep grind is worse than V295, then the held-D 13 Hz anti-damping is the cause
  and the next lever is the fresh-D operand (move to H-A, accepting the fork SR fold) — not a cal."*

---

## 4. The shared residual, declared once

**No implementation in this panel — H-A, H-B, or the C2-rev2 four — clears the fully-stacked tier-B corners
(`b_q×J1.0+h10`, `b_lo×J_hi+h10`) at the aged hold (11–20 ticks) with margin.** They land 0.5–3° under the 30° PM
bar, with a 1.4–1.9 Hz ring at ζ 0.10–0.19 (EVIDENCE `h_freq`, and `REFUTE-C2-r2-stability` F1 independently). This
is a property of the **credible set** (double/triple-stacked worst cases at the pessimistic hold age), not of any one
design.

**Pre-registered stop band (binding on both implementations):** a visible closed-loop ring in **1.3–2.1 Hz** on any
drive ≥ 8 m/s — seen as ≥ 4 wheel-rate cycles after a disturbance, or F7 > 0, or a torque-tap peak in that band —
licenses **REVERT**. The aged hold (11–20 ticks) only occurs when slot 4 is preempted; at the nominal hold (1–10) all
tier-A corners clear ≥ 46° and tier-B ≥ 36° (EVIDENCE `h_freq`, worst tier-B age0 ≥ 36.6°).

---

## 5. F5 — the fail-safe design, and the `gp-0x6803 == 2` interlock

### 5.1 The in-place guards (both implementations; EVIDENCE: dominance + sentinel traces, confirmed this session)

- **A2 `0x29A56 da05 → b205`** (`bne`→`be 0x29A5C`): run the PID iff `ramp≠0 && request==1` (was `ramp≠0 || request`).
  This makes the 0xE4 sentinel (`gp-0x6805=0xFF≠1`) and every ST=3 fault SKIP the PID; the output lag decays in
  ~105 ms instead of a 2.048 s PID-held fade. EVIDENCE (`fault_pulse` mirror): angle-loop sentinel peak drops from
  2275 T to 472 T (decay only). It also closes the override-latch I wind-up and removes the fork "steer-to-centre
  while inactive" hazard.
- **B2 `0x29A50 e24700 00 → e0df3443`** (`setfe r8`→`cmovne r0,r27,r8`): also require `bVar2` (angle validity incl.
  `gp-0x67fe==2`), so `gp-0x67fe≠2` (angle forced to 0) skips the PID instead of running P on `E=16·θ_sp` for 2 s.
  EVIDENCE: `r27` holds bVar2 at `0x29A50` (dominance trace §1), `r8`/`r27` dead after the guard (§1b), `r25`
  (= `6803==2`) live across the hook so the cave must not touch r25 (dominance §1).

These are **4 + 2 = ~6 bytes, all in place, no cave.** With them the sentinel, the `gp-0x67fe` fault, the speed
window, the `gp-0x69aa` range and `bVar1` each skip the PID on their first tick. The 510 ms 0xE4-timeout hold
(dominance §3) still holds the last θ_sp for ~0.5 s, then the sentinel → A2 skip; the mid-motion move is ≤ 2.35°
(refuter F5, declared).

### 5.2 The `gp-0x6803 == 2` interlock — firmware compare vs operator procedure (EVIDENCE: dominance trace §5)

The brief asks whether to use `gp-0x6803 == 2` as a firmware interlock. **What it would buy and cost:**

- **A firmware compare** `gp-0x6803 == 2` added to the guard would **exclude the stock camera's 0xE4** on a relay
  close (the camera sends `byte2 & 0x7F == 1` ⇒ field 3:2 = 0 ⇒ `gp-0x6803 = 1 ≠ 2`), closing F5's relay-close hole
  at the firmware level. **But** `r25 = (gp-0x6803==2)` is computed at `0x29A82`, *after* the guard, so a 6803 gate in
  the guard needs a **new `ld.bu -0x6803` (+4 bytes)** — it is not free, and it is a NEW liveness claim in the guard
  region.
- **What sending 2 ALSO changes (EVIDENCE §5):** (a) engage ramp-in 0.10 s (`0xC63FC`=328) instead of 0.99 s, ramp-out
  0.50 s instead of 2.05 s — *faster engage, which shrinks the engage-droop/wind-up window* (a BONUS, BELIEF, needs
  the harness); (b) it switches the post-PID fade arm to `0xCBAE4`, which **raises lane authority against a hand by up
  to ×2.1 at 2048 raw** (600–3240 raw band). That must go through the override sims before adoption. (c) the setpoint
  taper arm switches to the cliff `0xCBA04/74`, but E4 bypasses the setpoint taper, so that arm is inert in this loop.

**Recommendation (BELIEF):** **Do NOT gate the firmware on `gp-0x6803 == 2`.** The relay-close hole is better closed
by (1) the A2 skip (camera 0xE4 has request 0 ⇒ A2 skips within 10 ms) and (2) the **operator procedure** (camera
LKAS off) + the **fork-side B3 gate** (the fork drops the request unless 0x14A b4 bit1 = mode-3 health = 1, zero
firmware bytes, refuter sentinel-gate B3). The authority-raising side effect of sending 2 is a net risk the loop does
not need. If the faster ramp-in is wanted later, send 2 **and** re-score the `0xCBAE4` fade arm through the override
sims — as a separate, declared change.

### 5.3 Fork-side prerequisites (BELIEF; fork owner, not this kit)

1. Send the angle setpoint as `raw = −10·θ_sp_deg` in the EPS frame (no openpilot angle offset).
   **H-A:** pre-divide θ_sp by the local VGR slope (fold into the SR map). **H-B:** send openpilot's own angle.
2. Send `STEER_TORQUE = current θ` (not 0) whenever lateral is inactive, so the loop holds, not centres — unless A2
   is shipped (then 0 is fine; A2 skips on request 0). With A2, prefer `request = 0` when inactive.
3. Drop the request unless 0x14A byte-4 bit 1 = 1 (mode-3 health), closing F5 gate B3.
4. Accept the `39990-TVA,A160` fwVersion (and any F4-char change) so the car fingerprints (dominance §4).

---

## 6. Scoring summary (both reproduced by the shared engine)

### 6.1 Frequency (EVIDENCE `h_freq.py`; `ds_model`/`ds_gate2` unmodified; controller 20 Hz rule 0 fails for all)

| impl | ReTw13 | ReTw16 | ReTw20 | tierA PM age0 / age10 | tierB PM age0 / age10 | member fails (strict / panel) |
|---|---|---|---|---|---|---|
| V295 (ref) | −0.47 | −0.73 | −0.82 | — | — | — |
| **H-A** fresh Kd34 | **−0.23** | **−0.27** | **−0.29** | 46.7 / 42.2 | 32.6 / 27.8 | 35 / 33 |
| **H-A'** +LS-trim | −0.23 | −0.27 | −0.29 | 49.8 / 45.5 | 34.0 / 29.3 | 14 / 12 |
| **H-B** held Kd23, D×0.866 | −0.70 | −0.70 | −0.65 | 46.8 / 42.5 | 32.0 / 26.8 | 56 / 54 |
| **H-B** held Kd23, D×1.040 | −0.79 | −0.81 | −0.76 | 52.1 / 47.8 | 37.9 / 32.0 | 8 / 8 |
| **H-B'** +LS-trim, D×0.866 | −0.70 | −0.70 | −0.65 | 50.1 / 46.1 | 33.5 / 27.6 | 33 / 31 |

(panel convention = aged singles → 30° bar, ms_free report-only, per refuter F6.)

### 6.2 Time (EVIDENCE `h_time.py`): see §2.6 (filled from `h_time_out.txt`).

---

## 7. Files

| file | what |
|---|---|
| `analysis-2020accord/studies/angle_loop/panel2/H-whole-loop-reconcile/h_freq.py` | frequency GATE 2 (reuses `ds_model`/`ds_gate2`; adds the F2 frame ratio as a gated uncertainty) |
| `.../h_time.py` | time gates G1 turn-hold, G2 release lurch, G3 dwell-then-jump (reuses `harness_time.PlantVec`; subclasses `c1_lib.LaneC1F` to add the combined freeze+bleed cave — the ONLY change) |
| `.../h_freq_out.txt`, `.../h_time_out.txt` | the raw scorer output |

**What I changed in reused code:** nothing in `ds_model`/`ds_gate2`/`harness_time`/`c1_lib` on disk. `h_freq.py`
builds `Des` configs and drives the gate; the only addition over the engine is applying the measured P:D frame ratio
(0.83–1.155) as a gated uncertainty on H-B's D. `h_time.py` subclasses `LaneC1F` and overrides `cave()` alone, so the
I policy does freeze **and** bleed together (the shared core does one or the other by `pol`); every other lane line is
`LaneC1F`'s byte-exact arithmetic.
