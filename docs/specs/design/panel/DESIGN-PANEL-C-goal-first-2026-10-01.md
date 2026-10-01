# DESIGN PANEL C — goal-first (2026-10-01)

**Status: DESIGN ONLY.** Nothing built, flashed or sent. The fork was not touched. Ghidra was used read-only on the
V294 program (code-identical to V295 except cal `0xC63EA`); it disconnected mid-session, so the final byte decode of the
built image (H5) stays a flight prerequisite, exactly as C1 rev 2 left it. Every pre-edit byte quoted here was re-read
in Python from the V294 plain image this session (`cgf_bytes.py`).

**Author:** panel designer **C (goal-first)**, for the judges. I did not see the other four designers.

**My angle — GOAL PERFORMANCE FIRST.** Meet the goal's tracking (scorer slope 0.95–1.05) and turn-hold (≥ 0.90) in
every band ≥ 8 m/s, attack the low-speed dead zone, and close the operator's "loose/understeer on highway" feel (the
0.2–1 Hz lag that C1 rev 2 declared as its miss M3) — then pay with the **smallest robustness concession I can defend
with a pre-registered stop.** The concession is declared with the member, the speed, and the stop band that catches it.

**The one idea that makes this possible, and the one number that proves it.** C1 rev 2 was forced to cut highway gain
(Kp_eff 458–930) because its D term read the **held** rate `gp-0x6a56` (a 100 Hz sample-and-hold), which anti-damps
above ~7 Hz and so capped Kd at 20; the ring-damping shortfall then capped the highway gain on the combined
damping×inertia members. Designer C reads D from the **fresh 1 kHz rate `gp-0x6abe`** — **zero extra cave bytes** (one
`ld.h` displacement in the E5 edit). Fresh D has no hold, so its Re(T/ω) is **age-independent** and bounded at −0.33 …
−0.44 T per deg/s across 5–25 Hz (vs V295's −0.79 at 20 Hz), which lets **Kd rise to 28** while M20 stays ≤ V295. The
extra ring damping lets the highway gain rise to **Kp_eff 628 / 729 / 835 / 928 / 1079 at 15 / 17 / 19 / 22 / 27 m/s —
35–40 % above C1 rev 2 — with the whole CREDIBLE member set still gated at PM ≥ 30** (Tier A ≥ 45) and 0 unstable
points anywhere. Only the single least-credible corner (`b_q×J≈1.0`, i.e. 0.25× damping AND J≈1.0, both BELIEF on both
axes and physically doubtful) is conceded to PM 23.5–29° — and even there the loop is **stable, GM ≥ 19 dB, ring ζ ≥
0.16** — caught on-car by the pre-registered R3 stop.

**EVIDENCE for the fresh-rate sign (the crux; I verified it myself in Ghidra before trusting it).** Decompile of
`FUN_0003f776` (the producer of `gp-0x6a56`) on the V294 program:
`gp-0x6a56 = pol·((gp-0x6abe·0x30·cal[0xC613A])>>15)`, with `pol = gp-0x6752 = −1`, `cal = 1159`, so
**`gp-0x6a56 = −1.698·gp-0x6abe`**. V295's D edit damps as `D = (−Kd·gp-0x6a56)>>3`; substituting the fresh rate,
`−Kd·gp-0x6a56 = +1.698·Kd·gp-0x6abe`, so **fresh D keeps +Kd (no `subr` at 0x29EDE) and reads `gp-0x6abe`**, and the
cal Kd scales ×1.698 (Kd_eff 28 → cal 48) to deliver the same physical damping. `gp-0x6abe` is live in production (three
independent traces), written in slot 0 at `0x22200` **before** the PID at `0x22522`, so it is fresh same-tick.

**Reproducibility.** Every number below is from a script in
`analysis-2020accord/studies/angle_loop/panel/C-goal-first/` (fixed seeds, fixed member grid):
`cgf_freq.py` (the mixed-hold frequency model + the gp-0x6abe EMA; a control asserts it reproduces `harness_freq.C_fb`
to ratio 1.0000 when D is held), `cgf_design.py` (schedule/cals), `cgf_gate2.py` (exact-pole GATE 2 over the full
`c1r2_members` factorial with hold ages 1–20 + Re(T/ω)), `cgf_goalmetric.py` (the goal's own tracking metric via
`c1r2_trackmetric`), `cgf_time.py` (exact nonlinear 1 kHz sim, Karnopp friction, 100 Hz holds; a control asserts the
lane is bounded and, with the cave off + D held, equals the V295 mirror), `cgf_bytes.py` (every byte asserted against
the image). Member source: `c1/c1r2_members.py` (the full factorial of damping × inertia × delay × hold-age), used
unmodified and extended only in the concession split — no member dropped.

Every decision-bearing claim is EVIDENCE (with method) or BELIEF.

---

## 0. The three implementations, in one page

| | **CGF-1** (headline) | **CGF-1b** (byte variant) | **CGF-2** (low-speed attack) |
|---|---|---|---|
| idea | fresh-rate D (gp-0x6abe), held angle operand, higher highway gain | CGF-1 + fresh **rebuilt** gp-0x6a00 operand at 1 kHz | CGF-1 + friction feed-forward (dead-zone break) |
| in-place edits | 7 code sites + V1 (**25 bytes**) | same 7 + V1 | same 7 + V1 |
| cave | C1 rev 2's 96-byte code **byte-identical** + new 48-byte table (**144 B**) | +~50 B to rebuild gp-0x6a00 (**~196 B**) | +~28 B FF block (**~172 B**) |
| new RAM words | **0** | 0 | 0 |
| what it buys | highway gain +35–40 % vs rev 2; 20 Hz budget far under V295; age-independent damping | a further +15–20 % highway gain and removes the 5–13 Hz anti-damping | removes the low-speed dead zone (bc 3.1 m/s: step error 0.20°→0.04°, hunt 0.61°→0.00°) |
| concession | `b_q×J≈1.0` (+tau6/+h10) PM 23.5–29° (stable, GM ≥ 19 dB, ζ ≥ 0.16), caught by R3 | same, slightly smaller | same as CGF-1 |

**Minimise note.** CGF-1 is the minimum: it reuses C1 rev 2's proven cave **code byte-for-byte** and changes only the
D displacement (0 bytes), the table, and cals. CGF-1b and CGF-2 are cave changes offered for the judges to weigh against
the gain they buy. A 6-knot table (−6 B) is available if the 12.5 m/s knot is dropped (costs ~1 dj event at 12.5).

---

## 1. The loop in integer form (CGF-1), every byte, every cal

### 1.1 In-place code edits (EVIDENCE: `cgf_bytes.py`, each old byte asserted against the V294 image; encoder
positive-controlled on existing `ld.h`/`cmov` instructions)

| id | addr | old → new | decode | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `243faa95` → `243f0096` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | operand x = θ (0.1° counts); ±12000 bail tests θ |
| E2 | `0x28FA4` | `89d1` → `c9d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new (2-tap FIR) |
| B2 | `0x29A50` | `e2470000` → `e0df3443` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (req==1)?bVar2:0 |
| A2 | `0x29A56` | `da05` → `b205` | `bne 0x29A60` → `be 0x29A5C` | PID runs iff ramp≠0 ∧ r8≠0 (kills the 0x7FFF sentinel pulse) |
| E4 | `0x29D6A` | `0880ed80` → `24875296` | `mov r8,r16;mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae (= −4·raw) |
| H | `0x29D76` | `c282ba81` → `89378aae` | `shl 2,r16;sub r26,r16` → `jarl 0xC4C00,r6` | the hook |
| **E5′** | `0x29EE0` | `1040bb41` → `24474295` | `mov r16,r8;sub r27,r8` → **`ld.h -0x6abe[gp],r8`** | **D on the FRESH rate, +Kd** |
| V1 | `0x1310D` | `30` → `41` | F181 char | "39990-TVA,A160" → "…,A16A" (fork interlock) |

**Only E5′ differs from C1 rev 2.** Rev 2's E5 changed **two** sites (`0x29EDE c700→8039` to negate Kd, plus
`0x29EE0 →2447aa95` to read the held `gp-0x6a56`). Designer C **keeps `0x29EDE` stock** (`c7 00` = `zxh r7`, so Kd stays
positive) and changes **one** site (`0x29EE0` → `ld.h -0x6abe[gp],r8`). This is strictly fewer bytes than rev 2 and is
the entire mechanism of the headline lever. Total in-place: **25 bytes** (7 code sites + V1), same sites as rev 2.

### 1.2 The cave (`0xC4C00`): C1 rev 2's code, byte-identical; new table

EVIDENCE: `cgf_bytes.py` prints the cave code as byte-identical to C1 rev 2's 96-byte block (the displaced `shl2/sub`,
the 6-knot→now-7-knot G(v) integer walk, `E' = (E·G)>>8`, the I freeze on `|gp-0x4f68|>512 ∨ ramp<0x8000`, the
`jr 0x29D7E` / `jmp [r6]` return). It writes **no RAM** (r25 untouched; the freeze leaves Honda's I8 at `gp-0x6dd0`
unchanged). The only change is the 48-byte table (7 knots + sentinel):

```
X    714 ( 3.10 m/s)  G 1268  S  1117   Kp_eff  555
X   1843 ( 8.00 m/s)  G 1576  S -3243   Kp_eff  690
X   2304 (10.00 m/s)  G 1211  S  -711   Kp_eff  530
X   2765 (12.00 m/s)  G 1131  S  1804   Kp_eff  495
X   3571 (15.50 m/s)  G 1486  S  2142   Kp_eff  650
X   4378 (19.00 m/s)  G 1908  S  1260   Kp_eff  835
X   6198 (26.90 m/s)  G 2468  S     0   Kp_eff 1080
X  65535              G 2468  S     0   sentinel
```

Interpolated Kp_eff: 11.9→497, 12.5→517, 17→729, 22→928. **Cave size 144 B** (96 code + 48 table), inside the free span
`0xC4BD8..0xC4FEF` (1048 B, dirties only CRC `0xC4FFC`).

### 1.3 Calibration (relative to V295)

| cell | stock | V295 | **CGF** | what it is |
|---|---|---|---|---|
| a `0xC63E8` | 923 | 1011 | **0** | fb pole (2-tap FIR) |
| b `0xC63EA` | 1560 | 1050 | **8192** | fb gain: s_new = 8θ |
| C `0xC62E6` | 7680 | 1024 | **65535** | r26 clamp |
| DB `0xC62E4` | 4 | 4 | **0** | I deadband |
| Ki `0xC63E6` | 0 | 0 | **56** | Ki/Kp = 0.5, fI = 0.622 Hz |
| ICL `0xC61BA` | 10240 | 10240 | **4096** | I>>7 clamp (≈660 T) |
| DCL `0xC61B6` | 10240 | 0 | **10240** | D clamp |
| Kp Y `0xE5384`×5 | 248… | 960 | **112**×5 | Kp_base (re-based) |
| **Kd Y `0xE5126`×4** | 128 | 0 | **48**×4 | **D on the FRESH rate: Kd_eff 28 (cal 48 = 28×1.698)** |

### 1.4 The loop, integer-exact (CGF-1)

```python
def cgf1_tick(st, theta, gp6abe, sp69ae, v, tq, ramp, req, bvar2):
    if not (ramp != 0 and req == 1 and bvar2):          # A2+B2
        st.I8 = 0; return lag_and_gate(st, 0)
    s_new = (8192 * theta) >> 10                         # 8*theta (a=0,b=8192)
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new
    E = (sp69ae << 2) - r26                              # = 16*(theta_sp - theta)
    G = walk(TBL, v)                                     # cave G(v)
    E = s32(E * G) >> 8                                  # E' = (E*G)>>8   (speed gain on P and I)
    frozen = (abs(tq) > 512) or ((ramp & 0x8000) == 0)
    e5 = 0 if frozen else E >> 5
    I = clamp((st.I8>>3) + ((e5 * 56) >> 3), -(4096<<7), 4096<<7); st.I8 = I << 3
    P = clamp((E * 112) >> 8, -15360, 15360)
    D = clamp((48 * gp6abe) >> 3, -10240, 10240)        # +Kd * FRESH rate  (gp6abe = -1.698-scaled, so this damps)
    return lag_and_gate(st, fade((I>>7) + P + D))
```

At DC, T (lane counts) ≈ 0.1002·Kp_eff per degree of angle error (EVIDENCE arithmetic). The D delivers Kd_eff 28 = 28
T per deg/s of damping, from the fresh rate with no 100 Hz hold.

---

## 2. GATE 2 — magnitude and phase in every loop (CGF-1)

Two independent linear methods agree (the `cgf_freq` exact periodic poles / exact GM, and its LTI fundamental, which
reproduces `harness_freq.C_fb` to ratio 1.0000 on a control). Conditions: 100 Hz hold ages 1–20 (the +h10 members),
the 5.05 Hz output lag, 2/6 ms transport, and the **full factorial** r71b member set (damping ∈ {nom, b_lo, b/1.9, b_q}
× inertia ∈ {0.2, 0.5, 0.8, 1.0} × delay ∈ {2, 6 ms} × age ∈ {0, +10}). EVIDENCE: `cgf_gate2.py`,
`gate2_noff_report.txt`.

### 2.1 Headline (EVIDENCE: 759 gated points + 143 report points, exact poles)

| tier | members | gate | result |
|---|---|---|---|
| **A** | nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6 | PM ≥ 45, GM ≥ 6 dB, stable, no 5–50 Hz pole ζ < 0.2 | **77 pts, min PM 55.6°, min GM 17.2 dB, 0 unstable, 0 below 45°** |
| **B** (credible) | every factorial cell EXCEPT the concession — incl. b_q×J_hi, J_hi2 (J 0.8) combos, b_lo×J_hi, **all +h10** | PM ≥ 30, GM ≥ 6 dB, stable | **550 pts, min PM 31.6°, min GM 15.2 dB, 0 unstable, 0 below 30°** |
| **concession** | `J≈1.0 × reduced-damping` (b_lo/b/1.9/b_q × J1.0, ±tau6, ±h10) | REPORTED; caught on-car by R3 | 132 pts, **min PM 23.5°, min GM 19.2 dB, 0 unstable**, ring 1.3–1.9 Hz **ζ 0.16–0.25** |
| report | J1.3, ms_free, light_b, … | tabulated | min PM 15.4° (light_b @ 27, the prior world); caught by R3 |

**20 Hz budget vs V295, nominal (EVIDENCE):** at every speed M20 **3.04–3.16** ≤ V295 3.58; L20 under V295; ReCr20
**−0.37 … −0.44** ≥ V295 −0.79 (less anti-damping). No 5–30 Hz peak: worst credible |T|/|T_ref| = **−2.88 / −9.04 dB**
(gate +3 dB).

### 2.2 PM by member at the design speeds (°) (EVIDENCE: `gate2_noff_report.txt`)

| v | Kpe | nom | J_hi | b_lo | b_lo×J_hi | b_q | b_q×J_hi | b_q×J_hi+h10 | **b_q×J1.0** | **b_q×J1.0+h10** | J1.0 | light_b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.1 | 555 | 76.4 | 55.6 | 65.4 | 47.2 | 76.4 | 55.6 | 51.0 | 44.7 | 41.0 | 44.7 | 38.9 |
| 8.0 | 690 | 79.3 | 60.5 | 63.4 | 46.9 | 79.3 | 60.5 | 56.5 | 53.6 | 50.0 | 53.6 | 31.6 |
| 10 | 530 | 88.2 | 74.9 | 90.1 | 55.2 | 88.2 | 74.9 | 71.1 | 57.3 | 54.0 | 57.3 | 41.9 |
| 11.9 | 496 | 81.4 | 77.0 | 100.3 | 62.0 | 81.4 | 77.0 | 73.1 | 50.1 | 46.8 | 50.1 | 44.4 |
| 12.5 | 517 | 82.4 | 81.1 | 103.6 | 70.8 | 77.7 | 55.1 | 53.6 | **32.5** | **28.9** | 60.4 | 43.1 |
| 15 | 628 | 85.3 | 86.9 | 104.4 | 101.9 | 91.3 | 53.5 | 53.0 | **32.8** | **29.4** | 83.7 | 36.4 |
| 17 | 729 | 86.7 | 88.2 | 103.8 | 105.2 | 124.4 | 64.7 | 66.2 | 37.6 | 34.4 | 87.6 | 30.8 |
| 19 | 835 | 82.7 | 82.6 | 100.5 | 97.7 | 116.4 | 60.3 | 59.9 | 35.5 | 31.7 | 79.8 | 25.6 |
| 22 | 928 | 77.2 | 75.6 | 94.0 | 88.4 | 98.9 | 59.1 | 57.2 | 36.9 | 32.8 | 71.7 | 21.5 |
| 27 | 1079 | 69.0 | 66.2 | 83.2 | 76.5 | 83.4 | 55.7 | 51.8 | 38.0 | 33.4 | 61.9 | 15.4 |

The concession is visible: `b_q×J1.0+h10` dips to 28.9–29.4° at 12.5–15 m/s (and `b_q×J1.0×tau6+h10` to 23.5°, the
worst single point). **Everything else, including `b_q×J_hi` (J 0.5) and the J 0.8 combos, holds PM ≥ 30°.**

### 2.3 Re(T/ω) vs V294/V295 (EVIDENCE: `re_tw_table.txt`, T counts per deg/s, nominal, worst over speeds)

| | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 Hz |
|---|---|---|---|---|---|---|---|---|
| **CGF age 0** | −0.33 | −0.33 | −0.39 | −0.43 | −0.44 | −0.44 | **−0.44** | −0.42 |
| **CGF age 10** | −0.33 | −0.33 | −0.39 | −0.43 | −0.44 | −0.44 | **−0.44** | −0.42 |
| V295 age 0 | +0.00 | +0.00 | +0.00 | −0.36 | −0.57 | −0.70 | **−0.79** | −0.79 |
| V294 age 0 | +0.00 | +0.00 | +0.00 | −0.19 | −0.31 | −0.38 | −0.43 | −0.43 |

**The fresh D makes CGF age-independent** (age 0 = age 10 — a property V295 does not have). At **20 Hz CGF anti-damps
−0.44 < V295's −0.79 — the gate "20 Hz gain ≤ V295" passes.** At **13 Hz CGF is −0.43 vs V295 −0.36** — CGF anti-damps
slightly more at 5–13 Hz because the **P operand is still the held angle** (its phase anti-damps 5–13 Hz). This is the
one honest cost of the held operand; it is small (−0.33 … −0.43 = **2–9 % of the nominal plant damping b = 5–26**, and
≤ 7 % of V295's 20 Hz removal) and **CGF-1b removes it** (see §5). Declared as **M-HF** below.

### 2.4 The goal's own tracking metric (EVIDENCE: `cgf_goalmetric.py`, via `c1r2_trackmetric`, ±0.028 positive control)

Inner-loop factor (what the kit scorer's tracking_gain reads if the fork supplies the DC), worst over nine members per
band ≥ 8 m/s: **8 m/s 1.002 · 10 1.001 · 11.9 1.001 · 12.5 0.995 · 15 0.981 · 17 0.973 · 19 0.981 · 22 0.991 · 27
0.996.** **Worst 0.973 (17 m/s, b_q) — PASS (≥ 0.95), and better than C1 rev 2's 0.959.** turn-hold |T(0.05 Hz)|
0.999–1.010 at every band — PASS (≥ 0.90). The higher highway gain is what buys the improvement over rev 2 and shortens
the 0.2–1 Hz lag (the operator's highway feel).

---

## 3. Time domain (CGF-1 and CGF-2), nominal and bc (EVIDENCE: `cgf_time.py`, exact 1 kHz Karnopp sim)

Control: the lane stays bounded (0/2000 rail-exceed); with the cave off + D held it matches the V295 mirror structure.

**Tracking / turn-hold (nominal), CGF-1** — |θ/θ_sp| gain, 3° amplitude:

| v | tg 0.2 Hz | tg 0.5 Hz | hold 20 s | ess ° |
|---|---|---|---|---|
| 8 | 1.05 | 1.13 | 1.004 | −0.02 |
| 12.5 | 1.07 | 1.09 | 1.007 | −0.04 |
| 15 | 1.02 | 0.90 | 1.009 | −0.05 |
| 17 | 0.99 | 0.82 | 1.004 | −0.02 |
| 19 | 1.01 | 0.90 | 1.010 | −0.05 |
| 26.9 | 1.06 | 1.12 | 1.002 | −0.01 |

The 0.5 Hz gain dips to 0.82–0.90 at 15–19 m/s (the inner loop alone; the fork supplies the slow DC). turn-hold ~1.0
everywhere, ess ≤ 0.05° — PASS.

**Low-speed dead zone (step 2° + 0.1 Hz ±1.5° small-amp), nominal and bc, CGF-1 vs CGF-2 (friction FF):**

| member | v | cand | step ess ° | hunt p2p ° | sine tg | max FF |
|---|---|---|---|---|---|---|
| nom | 3.1 | CGF-1 | −0.048 | 0.296 | 1.125 | 0 |
| nom | 3.1 | **CGF-2** | −0.090 | **0.181** | 1.119 | 170 |
| bc | 3.1 | CGF-1 | **−0.201** | **0.607** | 1.167 | 0 |
| bc | 3.1 | **CGF-2** | **0.042** | **0.000** | 1.155 | 170 |
| bc | 5.0 | CGF-1 | 0.015 | 0.000 | 1.117 | 0 |
| bc | 5.0 | CGF-2 | 0.041 | 0.000 | 1.119 | 137 |

**CGF-2's friction FF removes the bc low-speed dead zone: step error 0.20° → 0.04°, hunt 0.61° → 0.00°.** This is the
goal's low-speed criterion ("stick-slip gone") met on the worst identified friction world.

**Override release lurch (nominal, hold 1° then release), CGF-1:** 0.04–0.16° at 8–27 m/s (both `|tq|` regimes freeze,
since both exceed the 512 threshold). **5–30 Hz texture** (0.5° 0.3 Hz setpoint): wheel-rate rms **0.035–0.040 deg/s** at
12.5–27 m/s — no texture/grind.

---

## 4. CGF-2 — the friction feed-forward cave (the low-speed attack)

### 4.1 The mechanism (EVIDENCE: Ghidra disasm `0x29D76..0x29E3F`, this session)

The cave can inject a friction FF onto **P only** (not the integrator) by exploiting that **r16 (= E′) survives
untouched from the cave return at `0x29D7E` all the way to the P computation at `0x29E34 mov r16,r8`** (verified: no
instruction writes r16 in `0x29D7E..0x29E32`), while the I excitation is `r6`. So CGF-2's cave always returns via
`0x29D7E` (the freeze-style skip of `0x29D7A mov r16,r6`) with:
- **r6 = e5 (clean):** `(E′>>5)`, or 0 if frozen — the integrator sees the un-FF'd error (no FF wind-up);
- **r16 = E′ + FF:** the P term sees the dead-zone break.

`FF = clamp((E′·GFF)>>6, −Fff(v), +Fff(v))`, GFF = 64 (unity slope near zero), applied only below ~10 m/s. This is a
ramp that saturates at the friction level: near zero it adds proportional break torque, beyond it a constant ±Fff.

### 4.2 Cave arithmetic added (~28 B, BELIEF until assembled; the decouple is EVIDENCE)

```
APPLY: ... E' in r16 ...
       mov  r16, r6 ; sar 5, r6        ; e5 (clean I excitation)        -- or r6 := 0 on the freeze
       (speed gate: cmp V_FF, v ; bh NOFF)
       mov  r16, r8 ; shl 6? ... mul GFF ; sar 6   ; FF = (E'*64)>>6 = E'
       clamp FF to +-Fff               ; ld.hu Fff ; cmp ; cmov
       add  r8, r16                     ; r16 = E' + FF  (P sees it)
NOFF:  jr   0x29D7E                     ; I uses r6, P uses r16
```

### 4.3 Sizing from the wire (NO blind dose) — what drive 1 measures

- **Fff(v) = ≈ Fc(v), the breakaway torque**, measured at every dwell end (the 0x18F rate going 0 → >0.5°/s after ≥100
  ms stuck, hands-off): `lane_torque (tap×8) − k̂(v)·θ`. The prior Fc (76/13.5/15.8 T at 3.1/8/11.9 m/s, under-estimated
  ×0.46–0.58 at speed, so bc ≈ ×1.8 low speed → ~137 T at 3 m/s) sets the DESIGN PLACEHOLDER
  (Fff = 170/120/60/30/0 T at 3/6/8/10/12.5 m/s), hard-capped at 400 T (≤ 16 % of the 2461 rail).
- The **inert tap** (427 CAN tap, already on the wire) carries the lane torque, so drive 1 sizes Fff offline from the
  breakaway reads — a strictly better experiment than a blind dose. **Instrument for CGF-2 = the same 427 tap plus the
  0x14A angle and 0x18F rate; no new telemetry bit.**
- **Synergy:** with the FF breaking the dead zone, the integrator does less work, so CGF-2 may lower **ICL 4096 → 2048**
  (≈330 T), halving the worst override wind-up/lurch. Offered as a cal option, sized on the same drive.

---

## 5. CGF-1b — fresh rebuilt gp-0x6a00 operand (the byte variant)

The tracer gives the 1 kHz rebuild: `gp-0x6a00 = gp-0x3608 + gp-0x69ca + pol·C(gp-0x6cc4 − gp-0x69d0)` (call
`FUN_0003e600`, which clobbers r6–r16 and ep and writes the benign `gp-0x69dc` — a GATE-1 item). Replacing the held
operand with this fresh rebuild (EVIDENCE: `cgf_freq` op_hold='fresh' sweep):
- highway Kp_eff rises a further **~15–20 %** (to ~1050–1450 at 17–27 m/s, crossover 0.77–0.93 Hz) at the same PM;
- it **removes the 5–13 Hz anti-damping** of M-HF (the P-operand hold is gone), at the cost of M20 rising to 2.56–2.68
  (still ≤ V295 3.58) and ~50 cave bytes + the `FUN_0003e600` call's GATE-1 (r25 save, `gp-0x69dc` benign-write proof).

Offered as the variant for the judges if the highway feel or the 5–13 Hz damping is wanted and the cave bytes are
acceptable. The frame is **exact** (no steady-state tracking error), unlike reading `gp-0x69ca` raw (which would carry
the 1.155 slope + 0–7.3° correction mismatch — rejected; see §7).

---

## 6. The instrument — what proves CGF live in one short drive

Same wire set as C1 rev 2 (no new telemetry bit): 0xE4 sendcan (θ_sp, request), 0x14A STEER_ANGLE (θ, 100 Hz), 0x18F
rate + torque, the 427 tap (T = gp-0x6b38, +sign(cmd)), 0x18F STEER_STATUS, and the F181 string ("…,A16A"). Regression
`tap = c_P·(raw − f14A) + c_I·Σ(raw − f14A)dt + c_D·ω_18F + c0` over hands-off windows.

| verdict | condition |
|---|---|
| LIVE: image | carFw EPS = `39990-TVA,A16A` |
| LIVE: E-loop | c_meas/c_raw ∈ [−1.25, −0.80] |
| LIVE: speed schedule | c_P ≈ Kp_eff/800 within ±30 % per band (0.69 at 15 → 0.91 at 19 → 1.35 at 27 m/s), **and** the dip c_P(12.5) < c_P(8) |
| **LIVE: fresh D** | c_D opposes the rate at full 1 kHz **with no 100 Hz staircase** in the residual (the held-D build leaves a 10-tick staircase in the D residual; fresh D does not) |
| LIVE: the freeze | in hands-on episodes (|0x18F|>600, |θ_sp−θ|>0.3°) the I component changes < 3 tap counts / 0.5 s |
| LIVE: A2 | after any request drop, |tap| < 20 within 0.15 s |
| **LIVE: CGF-2 FF** | at dwell ends below 10 m/s, a step in lane torque of ≈ Fff at the error-sign crossing, absent on CGF-1 |
| NOT LIVE | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface |
| INVERTED | c_meas/c_raw > 0 → abort |

---

## 7. Pre-declared misses (each with its band and its revert signature)

| # | criterion | band / member | predicted | revert signature that catches it |
|---|---|---|---|---|
| **M-CONC** | PM ≥ 30 on every combined member | `b_q×J≈1.0` (+tau6/+h10), 12.5–19 m/s | PM 23.5–29°, **stable, GM ≥ 19 dB, ring 1.3–1.9 Hz ζ 0.16–0.25** | **R3: ≥ 12.5 m/s, a 1.0–5.5 Hz oscillation that grows or shows ≥ 4 cycles above 2× pre-event rms (ζ<0.10).** No gated member reaches ζ<0.10 (lowest 0.16); R3 fires only if the plant is outside the credible set. |
| **M-HF** | Re(T/ω) ≥ V295 across 5–30 Hz | 5–13 Hz, all speeds | CGF −0.33…−0.43 vs V295 +0.00…−0.36 (2–9 % of plant b; age-independent) | R4: a narrowband 5–30 Hz line absent on V282/V295; R5: ring presence > 0.5 %. CGF-1b removes M-HF. |
| **M1** | low-speed stick-slip gone / dwell-then-jump ≤ V282 | 0–7 m/s, **CGF-1 only** | bc 3.1 m/s step ess 0.20°, hunt 0.61° | **Solved by CGF-2** (ess 0.04°, hunt 0.00°). On CGF-1 it is a declared miss; V282 not simulable, decided on-car. |
| **M3′** | tracking faster than the scorer metric | 15–19 m/s | 0.5 Hz |θ/θ_sp| 0.82–0.90 (rev 2: 0.40–0.61) — improved but not unity | R6: |θ−θ_sp| > 10° hands-off > 0.5 s. The residual lag is smaller than rev 2's but non-zero. |
| **M6** | release after a light hand below the 512 freeze threshold | all | inherited from rev 2 (a hand reading < 512 internal counts winds I) | R2/R7; CGF-2's lower-ICL option (330 T) halves it. |
| **M9** | hard-turn 1.6–3 Hz amplification on J-heavy members | 12.5–30 m/s | credible worst \|T_ref\|₁.₆₋₃ **1.89** (b_q×J_hi2×tau6+h10 @30); concession **2.39** (b_q×J1.0×tau6+h10 @15) | R3 (same ring band). Declared; nominal/low-J members are ≤ 0.93. |
| **M12** | fork stops sending | all | EPS holds last θ_sp ~0.51 s, then A2 + ~0.1 s decay | tracer EVIDENCE; same as rev 2 |

**What a FAIL looks like (before any build):** any Tier-A point PM<45 or GM<6; any Tier-B (credible) point PM<30, GM<6,
or unstable; M20 > V295 or any 5–30 Hz |T|,|T_ref| > +3 dB on a credible member; the goal metric < 0.95 on any member
≥ 8 m/s; on-car turn-hold < 0.90 or tracking outside 0.95–1.05 in any band ≥ 8 m/s; a new 5–30 Hz line; or any R1–R9.

---

## 8. Hazards

| hazard | mitigation | residual | E/B |
|---|---|---|---|
| wrong fresh-rate **sign** (anti-damping = undriveable) | EVIDENCE: FUN_0003f776 decode, gp-0x6a56 = −1.698·gp-0x6abe, so +Kd on gp-0x6abe damps | re-prove on the built image (H5) | EVIDENCE decode; BELIEF until H5 |
| gp-0x6abe not fresh / not live at the PID | EVIDENCE: written slot 0 @0x22200 before PID @0x22522; live in production (3 traces) | none found | EVIDENCE |
| gp-0x6abe clamp (±13000) + EMA lag | D clamps at ~360 deg/s; EMA α 0.2891 adds only −1.5° at the ring, −17° at 20 Hz (helps the budget) | — | EVIDENCE loop-lag-map |
| 0xE4 sentinel / timeout / mode-3 exit | A2 + the ±12000 bail (now on θ) + the freeze | last θ_sp held ~0.51 s (M12) | EVIDENCE tracer |
| the concession corner is real | R3 (ζ<0.10) + GM ≥ 19 dB headroom; §6.4-style highway FRF on drive 1 measures J(highway) to retire it | ring 1.3–1.9 Hz ζ 0.16–0.25 if J≈1 is real | EVIDENCE model; BELIEF physics |
| 5–13 Hz anti-damping (M-HF) | bounded ≤ 0.43 T/deg/s (2–9 % of b); CGF-1b removes it | small, age-independent | EVIDENCE model |
| CGF-2 FF decouple wrong (I winds up) | EVIDENCE: r16 survives 0x29D7E→0x29E34; r6 carries e5 | re-prove on the built image (H5) | EVIDENCE disasm; BELIEF until H5 |
| CGF-2 FF over-dose (jerk) | hard cap 400 T (≤16 % rail); sized from the wire, not guessed | a wrong k̂ over-sizes Fff | EVIDENCE arithmetic |
| V1 / revert re-header | the C1r2/V295/V294 revert .rwd headers must list A16A | flight prerequisite | EVIDENCE tracer |

**Flight prerequisites (fork + build, same class as rev 2):** F4 version marker + fork angle param; the .rwd re-header;
C8 mode-3 engage gate; C6 Δmax(v); O1 override taper; no fork integral below 8 m/s / τ_o ≥ 1 s; camera LKAS off; the
panda 0xE4 bound; and H5/H6 (re-prove the bytes, the fresh-D sign, the FF decouple, B2 dominance on the **built** image).

---

## 9. Concerns / open items

1. The concession and M9 rest on members that are BELIEF on both axes (b_q frequency-dependent damping, unmeasured at
   3–5 Hz; J≈1.0, unmeasured above 10 m/s and physically disfavoured). The §6.4 highway FRF on drive 1 is what retires
   them; until then the R3 stop is the guard.
2. The goal-metric pass rests on one route's spectrum (r71b), ±0.028 positive control; the 17 m/s margin (0.973 vs 0.95)
   is 0.023 — inside that accuracy, same caveat as rev 2.
3. Everything above ~8 Hz is model, not measurement. The fresh-D 5–25 Hz Re(T/ω) is bounded and age-independent, but
   the plant there is unidentified.
4. CGF-2's FF byte count (~28 B) and the decouple are BELIEF until the cave is assembled and Ghidra decodes the built
   image (H5). The decouple's premise (r16 survives) is EVIDENCE from the disasm this session.
5. The friction/safety lenses need an independent adversarial pass (the "do not flash" verdict must be reachable), per
   the kit's close-out contract — not done on this page.
