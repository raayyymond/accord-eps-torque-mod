# DESIGN PANEL 2, designer E2 (2026-10-01): THE INTEGRAL POLICY, MOST MARGIN THEN FEWEST BYTES

**Status: DESIGN ONLY.** Nothing was built, flashed or sent; the fork was not touched; no image or `.rwd` was written.
Ghidra was used read-only (`decompile_function`, `get_function_by_address`, `get_function_callers`, `search_instructions`,
`disassemble_bytes` with `dry_run: true`) on stock `code.bin` and the open V294 program; nothing was saved.

**Author:** designer E2, a subagent (Opus) of the orchestrator `main`. Three other designers work other axes; I have not
read their pages. **No winner is picked here; the judges pick.**

**Brief (my axis):** resolve the round-2 refuters' **F1** (turn-hold / tracking at ≥ 8 m/s: the integrator clamp ICL 4096
≈ 668 T is below the spring load) together with **F4's release lurch and engage droop**, choosing the integral policy
that gives the **smallest worst-case lurch and droop on b_lo×J_hi and bc** while meeting **turn-hold ≥ 0.90 and the goal's
tracking ≥ 0.95 on r71b's paths at ≥ 8 m/s**, then minimising bytes. Consider at least: (i) freeze on ramp / hand /
hand-opposing-error, (ii) a leaky integrator under the hand, (iii) no firmware I with the DC from a fork integral,
(iv) the `gp-0x6803 == 2` arm, with its readers outside the lane traced.

Every implementation here is **rev2-A's P2 skeleton** (fresh-rate D, Kd 34, the 6-knot G(v), Kp 112, Ki 56, the A2/B2
guards, E1/E2/E4/OPH/V1) with **only the integral policy and ICL changed**. The policy block is the last part of the
cave; it is independent of the D operand and the G table, so it carries over unchanged onto whatever skeleton the D-axis
designer's fix produces (the inherited D-frame defect is declared in §5, not resolved here).

Every decision-bearing claim is marked **EVIDENCE** (method given) or **BELIEF**. Code is cited by address.

---

## 0. The answer in one page

### 0.1 What the evidence settled (all on the COMMON scorers: `c2/rev2A/score_time.py` extended additively, `panel/score_freq.py` by composition)

1. **ICL must rise, and 8192 is enough for the curves r71b actually drove.** EVIDENCE (`e2_final.py ext`, T1/T2 below):
   turn-hold sized from r71b (lateral acceleration up to the route's own sustained maximum and beyond) goes from
   **0.66–0.83 (P2) to ≥ 0.98 at ICL 8192** for the r71b-sized curves (formula a ≤ 2.5 m/s²; 0.905–0.93 at a 3.5, past
   r71b's p99.9 at 15–22 m/s), and **≥ 0.99 at ICL 12288**. The goal's own tracking metric on r71b's paths goes from
   **0.856 / 0.892 (P2, 15–22 / 8–15 m/s, worst member; it reproduces the refuter's F1 through the common scorer) to
   0.991 / 0.986** (r71b's torque word replayed).
2. **ICL alone is REFUTED by its own lurch.** EVIDENCE: under the brief's light-hand convention (a stiff hand with a
   constant torque word below the 512 freeze), the release lurch scales with ICL: **P2 7.2° → 17.6° at ICL 8192 (nominal,
   11.75 m/s); b_lo×J_hi 10.5° → 25.2°.** The integral POLICY must change, as the brief says.
3. **There are TWO lurch mechanisms, and the convention hides the second.** EVIDENCE (per-speed tables, §3.1):
   **M-a** — the I winds against a light hand during the hold (∝ ICL, word-independent below the freeze); **M-b** — after a
   large release the I winds on the big post-release error during the return (∝ step size × Ki, capped only by ICL; it
   is the whole story below 8 m/s and for every FIRM-hand case at ≤ 8 m/s).
4. **The light-hand lurch depends on a scale nobody has measured: torque-word counts per T count (κ).** With a
   consistent sensor (word = hand torque / κ, κ ≤ ~1.3 T/word), the 512 hard freeze binds before ICL and **ICL does not
   change the light-hand lurch at ≥ 8 m/s at all** (EVIDENCE, the `lk` rows). The brief's constant-word convention is the
   κ → ∞ limit. κ on this car is **BELIEF** (the r71b torque-bar fit `p5b_ms_bar_out.txt` gives a bar-input gain of
   0.003–0.09 T per bar count, i.e. a small κ, with ±100 % error). **A policy with "most margin" must therefore hold
   for every κ** — that is the criterion this page uses.
5. **Every LEAK policy fails the goal on the car's real torque word.** EVIDENCE: replaying r71b's own measured
   `gp-0x4f60` (carState torque × 128/125; the sign relation is EVIDENCE, §2.1) time-aligned with its own angle paths,
   the leak-above-512 policy scores **0.938–0.959** at 8–22 m/s and the leak-on-opposing-hand policy **0.81–0.89**: the
   driver's resting hands read 100–300 words most of the time (§2.2) and bleed the I in normal driving. **Policy (ii) is
   rejected by evidence.**
6. **The sign-aware hand freeze (policy i) works but only above its threshold, and costs ~0.007 of tracking.**
   EVIDENCE: opposing-hand freeze at 300 words: replay duty 3.9 %, goal metric 0.980 / 0.984 / 0.996 (8–15 / 15–22 /
   > 22 m/s, −0.006…−0.007 vs ICL-only); it removes the M-a lurch for
   hands reading > 300 words and the torque-source-hand lurch (4.1° → 1.4°), and does nothing for a hand reading less.
7. **NEW, policy (v): the ANGLE-REFERENCED I BOUND (ARB) is the only κ- and word-independent bound on M-a.** The I may
   wind further only while it is below what the spring at the CURRENT wheel angle could need:
   `t = sgn(E')·(I >> 7) < (|gp-0x6a00| << sh) + B`. A hand that holds the wheel away from the setpoint drops the bound
   to B, so the I stops at the level the turn needed; a normal turn never reaches the bound. EVIDENCE: turn-hold and
   tracking **identical** to ICL-only (to 0.001); **no steady hold on r71b ever exceeded the bound** (the 427 tap vs the
   bound at every steady hands-off hold, ≥ 43 T to spare, §2.3). With a **two-level slope** (26 T/deg ≤ 12.5 m/s,
   102 T/deg above) it also caps most of M-b at 8–12.5 m/s: the worst lurch over EVERY hand model at ≥ 8 m/s is
   **3.0 / 3.6 / 5.2 / 6.2°** (nominal / bc / b_lo×J_hi / +h10) against P2's 7.2 / 7.8 / 10.5 / 10.9° and ICL-only's
   17.6 / 19.7 / 25.2 / 26.0°. Below 8 m/s it regresses against P2 (M-b at parking speed; the A3 cap repairs it, §6.6).
8. **Engage droop is set by the ramp-in, not by any I policy.** EVIDENCE: every column gives the same droop to 0.01°;
   the `gp-0x6803 == 2` arm's 0.10 s ramp-in (policy iv) cuts the worst droop **33–35 %** (b_lo×J_hi 6.1° → 4.2° at
   8 m/s; 7.9° → 5.2° at 3 m/s). Its costs: the post-PID fade arm `0xCBAE4` pushes **×1.8 harder against a 2400-word
   hand** (×2.1 at 2048 raw), and the fork must send byte-2 bits 3:2 = 2 on every frame. Its readers outside the lane are
   **all dead code plus one UDS DID read-out** (§4, EVIDENCE, scan with a positive control). It also opens a firmware
   **camera interlock** for F5 at +20 B (§4.4).
9. **Policy (iii), no firmware I with a fork integral, fails the goal** (§3.4) and is fork code beyond the interface.
10. **Every scored column passes every pre-registered bar of the common time scorer's own suite** (T5: 18 scenarios ×
    12 speeds × 5 members) — and the ICL raise improves two of its reported side metrics (510 ms timeout hold 1.01° →
    0.58°; hard-turn 1.6–3 Hz ratio 1.40 → 1.29 with A2).

### 0.2 The implementations (bytes counted as rev2-A counts them: in-place code 20 + cal 24 + cave; RAM words 0 for all)

All numbers from the common time scorer (`e2_final.py ext`, `e2_a3.py`), worst over the members named in §6; turn-hold
= min over 8–30 m/s on r71b-sized curves; goal metric = min over the four members, with r71b's own torque word replayed;
lurch = the worst over EVERY hand model at ≥ 8 m/s (nominal / bc / b_lo×J_hi / b_lo×J_hi+h10) and, separately, below
8 m/s; droop = engage under load at ≥ 8 m/s on b_lo×J_hi, stock ramp-in / 6803-arm ramp-in.

| impl | integral policy (all on P2's skeleton) | cave B (vs P2) | written B | turn-hold a ≤ 2.5 / a 3.5 | goal metric 8–15 / 15–22 (replay) | worst lurch ≥ 8 m/s | worst lurch < 8 m/s (nom / b_lo×J_hi) | droop ≥ 8, b_lo×J_hi | verdict before any build |
|---|---|---|---|---|---|---|---|---|---|
| P2 (reference) | ICL 4096; freeze \|tq\| > 512 or ramp-in | 156 (0) | 200 | 0.69–0.83 / 0.66 | **0.891 / 0.855** | 7.2 / 7.8 / 10.5 / 10.9° | 4.3 / 10.5° | 6.1° / 4.2° | fails F1 (the refuters') |
| **E2-R1** | ICL 8192, P2's policy | 156 (0) | 200 | 0.983 / 0.905 | 0.986 / 0.991 | **17.6 / 19.7 / 25.2 / 26.0°** | 13.7 / 21.7° | 6.1° / 4.2° | fixes F1, **breaks F4** (the brief's premise, now measured) |
| **E2-S** | R1 + freeze when the hand OPPOSES E' and \|word\| > 300 | 172 (+16) | 216 | 0.983 / 0.905 | 0.980 / 0.984 | 17.6 / 19.7 / 25.2 / 26.0° (any hand reading ≤ 300) | 13.7 / 21.7° | 6.1° / 4.2° | fixes F1; F4 only for hands > 300 words |
| E2-L | R1 + LEAK (τ 146 ms) above \|word\| 512 | 168 (+12) | 212 | 0.983 / 0.905 | **0.938** / 0.958 | 17.6 / 19.7 / 25.2 / 26.0° | 13.7 / 21.7° | 6.1° / 4.2° | **REJECTED: fails the goal metric on the real word** |
| **E2-A** | R1 + angle-referenced I bound, one slope (102 T/deg + 200 T) | 188 (+32) | 232 | 0.983 / 0.905 | 0.986 / 0.991 | 4.8 / 6.9 / 9.0 / 10.1° | 13.7 / 21.6° | 6.1° / 4.2° | fixes F1; F4 ≥ 10 m/s; 8 m/s M-b remains |
| **E2-A2** | R1 + ARB, two slopes (26 T/deg ≤ 12.5 m/s, 102 above) | 204 (+48) | 248 | 0.983 / 0.905 | 0.986 / 0.991 | **3.0 / 3.6 / 5.2 / 6.2°** | 7.8 / 13.9° | 6.1° / 4.2° | **fixes F1 and F4 at ≥ 8 m/s for every hand model**; regresses < 8 m/s (declared M-E2-1) |
| E2-A2S | A2 + the opposing-hand freeze at 300 | 220 (+64) | 264 | 0.983 / 0.905 | 0.980 / 0.984 | 3.0 / 3.6 / 5.2 / 6.2° | 7.8 / 13.9° | 6.1° / 4.2° | A2 + the 300-T torque hand 3.0° → 1.4°, for −0.006 of metric |
| **E2-A2-12k** | A2 at ICL 12288 | 204 (+48) | 248 | **0.985 / 0.993** | **0.996 / 0.991** | 3.0 / 3.6 / 5.2 / 6.2° | 7.8 / 13.9° | 6.1° / 4.2° | A2 + turn-hold margin to 0.99 past r71b's curves, 0 bytes, **no lurch cost** (the bound binds first) |
| E2-A2-NR | A2 without the ramp-in freeze | 198 (+42) | 242 | 0.983 / 0.905 | 0.986 / 0.991 | 3.0 / 3.6 / 5.2 / 6.2° | 7.8 / 13.9° | 5.6° (overshoot 2.0°) / 4.2° | the firmware-only droop attempt: −9 % droop for a 2° engage overshoot; dominated by (iv) |
| **E2-A2-X** | A2 + the fork sends `6803 == 2` (ramp-in 0.10 s, fade arm `0xCBAE4`) | 204 (+48) + 1 fork bit | 248 | 0.983 / 0.905 | 0.986 / 0.991 | 3.0 / 3.6 / 5.2 / 6.2° | 7.8 / 13.9° | **4.2°** (all speeds 5.2° vs 7.9°) | droop −33 %; ×1.8 harder against a firm hand; enables the camera gate |
| **E2-A3** / A3-12k | A2 + a low-speed cap (bound ≤ 4096 S = P2's own ICL at ≤ 6 m/s) | 222 (+66) | 266 | as A2 / A2-12k (≥ 8 m/s unchanged) | as A2 / A2-12k | 3.0 / 3.6 / 5.2 / 6.2° | **4.3 / 10.6°** (P2 4.6 / 10.5) | 6.1° / 4.2° | **A2 at ≥ 8 m/s, P2 (or better) below**; low-speed turn-hold back to P2's 0.90–0.95 (§6.6) |
| E2-K0 | Ki 0 + a FORK angle integral τ_o 1 s | 132 (−24) | 173 + fork code | 0.85 two s after the ramp | 0.97 / **0.92** | 36–43° at 8 m/s | — | — | **fails the goal; fork code; not offered** |
| E2-A2S-C | A2S + the camera gate (needs 6803 == 2) | 240 (+84) | 284 | as A2S | as A2S | as A2S | as A2S | with (iv) | the F5 follow-up, H1 only (§4.4) |

RAM words: 0 for every implementation. Cave count: 1 (at `0xC4C00`, inside the free span `0xC4BD8..0xC4FEF`: the
largest, 240 B, ends at `0xC4CF0`).

### 0.3 How the implementations differ, in one sentence each

- **E2-R1** proves the brief's premise: the clamp alone fixes F1 and breaks F4.
- **E2-S** fixes F1 and the over-threshold hand; it is the fewest-bytes policy that moves the convention lurch at all.
- **E2-A / E2-A2** fix F1 and bound M-a for every hand; A2 also caps M-b at 8–12.5 m/s. **A2 is the most-margin
  firmware-only policy on this axis** (judges' call).
- **E2-A2S** adds the opposing-hand freeze for the hands A2 does not see (a force hand that lets the wheel move back).
- **E2-A2-12k** buys turn-hold margin to 0.99 at curves past r71b for zero bytes and with no measured lurch cost (the
  bound binds before the clamp).
- **E2-A2-NR** is the firmware-only droop attempt (no ramp-in freeze); **E2-A2-X** is A2 with the `6803 == 2` arm.
- **E2-K0** is policy (iii) quantified, not proposed.

---

## 1. The record this page resolves against

- **F1** (nonlinear refuter, round 2): ICL 4096 S ≈ 657–668 T < the identified spring load at 15–22 m/s; goal metric on
  r71b 0.85–0.86 / 0.89–0.92; turn-hold 0.73–0.87 at 1.5–2.0 m/s². **Reproduced here through the common scorer:** P2 0.856
  / 0.892 on r71b (worst member, T2) and 0.66–0.83 turn-hold (§T1), and the ICL-lift diagnostic (0.997) is reproduced as ICL 12288's
  0.991–0.999.
- **F4** (lurch and droop): light-hand lurch 10.4–10.8° on b_lo×J_hi at 11.75 m/s (P2 reproduces 10.48°); engage droop
  ≤ 6.3–6.9° on b_lo×J_hi at 8 m/s (P2 reproduces 6.13°).
- **The I path** (EVIDENCE, my dry-run disassembly of V294 `0x29D60..0x29DCC`, which equals the mirror):
  `0x29D7A mov r16,r6 ; sar 5,r6` (e5) → `0x29D7E cmp r10,r6` (DB) → `0x29D9C ld.hu Ki` → `0x29DA0 ld.hu ICL` →
  **`0x29DA4 ld.w -0x6dd0[gp],r10` (I8 = 8·I)** → `mul ; shl 0xa ; sar 3` → clamp `cmovgt/cmovle` into r2 →
  S = (I >> 7) + P + D → `0x2A190 st.w r24,-0x6dd0`. **gp-0x6dd0 has exactly two live accesses (`0x29DA4` read,
  `0x2A190` write) plus two in the uncalled twin `FUN_0002a93a`** (EVIDENCE, Python LE scan, stock and V295).
- **The cave's two exits** (P2, unchanged): `jmp [r6]` → `0x29D7A` (e5 = E' >> 5) or `mov 0,r6 ; jr 0x29D7E` (e5 = 0,
  I unchanged). A LEAK exit sets r6 = −(I8 >> s) and takes the same `jr 0x29D7E` (Honda's inc = (r6·Ki) >> 3, DB 0).

---

## 2. Data facts the policies rest on (r71b, V294, route `00000071--a7b8ba5d9d`)

### 2.1 The sign of the hand (EVIDENCE, `e2_data_r71b.py`, `e2_data_r71b_out.txt`)

- The kit's r71b cache column `tq` is the raw 0x18F field; carState torque = −raw (slope −1.0006, corr −0.99966).
- The 0x18F packer writes raw = −floor(gp-0x4f60 · 125/128) (speed/driver-torque trace §3.3, V295 bytes `0x55C50`).
  ⇒ **carState torque = +gp-0x4f60 · 125/128.**
- With the driver steering alone (lateral inactive): corr(torque, angle) **+0.663**, corr(torque, rate) **+0.646**; holding
  a turn alone, sign(torque) = sign(angle) in **66/66** frames. gp-0x6a00 = 10 × openpilot's angle, same sign (angle
  trace §2). ⇒ **sign(gp-0x4f60) is the direction the hand pushes, in the gp-0x6a00 frame.**
- ⇒ A hand **opposing** the loop (pushing the wheel away from the setpoint) has **sign(gp-0x4f60) ≠ sign(E')**.

### 2.2 What the torque word reads when nobody is steering (EVIDENCE, same script, sections (2) and (4))

- Engaged, steeringPressed false: |word| p50 101–128, p95 292–548 by speed band; at |rate| < 10 deg/s p50 111, p95 302,
  p99 738.
- A reaction fit `tq = c0 + c1·rate + c2·accel + c3·sgn(rate)` explains only R² 0.25–0.34; the reaction **opposes the
  motion** (c1, c2, c3 all negative: −0.9…−18 per deg/s, −0.21…−0.43 per deg/s², −52…−101), plus an offset −40…−50.
- The residual is broad (0–2 Hz 24 %, 10–20 Hz 32 %); Honda's own 5 Hz IIR of the word (gp-0x3d34) barely changes the
  percentiles (p95 366 → 308). **BELIEF:** "not pressed" is not "hands off" — the operator's resting hands read
  100–300 words, and a threshold below ~300 sees them.
- Consequence measured, not assumed: §T2's replay columns.

### 2.3 The hold loads the I must be allowed to carry (EVIDENCE, `e2_data_hold.py`, `e2_data_hold_out.txt`)

On V294 (torque mode) the lane torque in a steady hands-off hold **is** the hold load at that wheel angle. Reading the
CAN-427 tap (frame `(sign << 9) | (|T| >> 3)`, polarity check sign(T) = sign(cmd) on 0.999 of frames) at every steady
hold (|rate| < 2 deg/s for ≥ 0.5 s, hands not pressed): **no frame exceeds the ARB bound** at any speed — margin
≥ 111 T (one slope, B 1250), and ≥ 43 T (3–8 m/s) / 52 T (8–12.5 m/s) with the two-level slope's 26 T/deg below
12.5 m/s. A 13 T/deg low slope **would** be exceeded (+28 T at 31°), so 26 T/deg is the floor. The tap includes the P
share, so this over-counts the I's need (conservative).

### 2.4 Curve sizes on r71b (EVIDENCE, livePose yaw × v)

|a_lat| p99 / p99.9 / 3-s sustained max: 8–15 m/s 2.61 / 3.66 / 2.43 m/s² (58.5° at 10.6 m/s); 15–22 m/s 2.20 / 2.51 /
2.05 (17.4° at 18.2 m/s); > 22 m/s 2.74 / 2.98 / 2.18 (11.4° at 28 m/s). In the turn-hold test's formula units
(L 2.83 m, SR 16, no understeer) r71b's sustained maxima are a ≈ 2.2–2.5 at ≤ 18 m/s and ≈ 3.4 at 28 m/s (the formula
over-states a_lat at speed). The test grid a ∈ {1.5, 2.5, 3.5} covers them.

---

## 3. The policies, one by one

### 3.1 The two lurch mechanisms (EVIDENCE, `e2_explore.py lurch` per-speed tables)

| nominal, 11.75 m/s | P2 (ICL 4096) | ICL 8192 | ICL 12288 |
|---|---|---|---|
| stiff hand, word 100 (M-a) | 7.17° | 17.59° | 26.12° |
| stiff hand, κ 0.6 (consistent sensor) | 1.48° | 1.48° | 1.48° |
| firm hand, word 2400 | 1.56° | 1.56° | 1.56° |

| nominal, 3.1 m/s (A_TURN 90°, the hand releases a 45° offset) | P2 | ICL 8192 | ICL 12288 |
|---|---|---|---|
| stiff hand, κ 0.6 | 4.24° | 12.14° | 12.13° |
| firm hand, word 2400 (I frozen during the hold) | 4.25° | 10.96° | 10.94° |

At 11.75 m/s the lurch is the I wound during the hold (M-a: only the constant-word convention shows it). At 3.1 m/s the
I is frozen during a firm hold and still the lurch grows ×2.6 with ICL: it is the windup on the 45° post-release error
(M-b), which P2's small clamp happened to cap. **A policy that only looks at the hand cannot touch M-b.**

### 3.2 Policy (i): freeze on ramp-in / hand / hand-OPPOSING-error — implementation E2-S

Cave block (after P2's `|tq| > 512` hard freeze), +16 B, `e2_cave_S300.hex`:

```
0xc4c64  20 6e 2c 01   movea 300,r0,r13        T = 300 words                         [OPPOSING HAND]
0xc4c68  ed 41         cmp   r13,r8            r8 = |gp-0x4f68| (already loaded)
0xc4c6a  d3 05         bnh   N2                |tq| <= T: no hand
0xc4c6c  24 4f a0 b0   ld.h  -0x4f60[gp],r9    the SIGNED hand word (sign = push direction, §2.1)
0xc4c70  30 49         xor   r16,r9            sign(hand) xor sign(E')
0xc4c72  c6 05         blt   FRZ               signs differ: the hand pushes AWAY from the setpoint -> freeze
N2: (P2's ramp-in test, FRZ, DONE unchanged)
```

- What it does: an opposing hand above 300 words stops the I; an aiding hand (co-steer) and the resting hand below 300
  are unchanged from P2.
- Cost on the real word (EVIDENCE, T2 replay): freeze duty 3.9 % on r71b's paths, goal metric −0.006…−0.008.
  At 200 words the duty is 16.7 % and the metric loses 0.02 (exploration, `e2_explore_rr.txt`); on Honda's 5 Hz IIR
  (`gp-0x3d34`, read-only, written every valid tick at `0x29080`, cals 31/634 at `0xC63E2/4`) the duty is 14.4 %.
  **300 raw is the cheapest working threshold.**
- What it does not do: any hand reading ≤ 300 words, and M-b.

### 3.3 Policy (ii): leak under the hand — implementation E2-L (REJECTED by evidence)

Cave: P2's hard test branches to LEAK instead of FRZ, +12 B (`e2_cave_L13.hex`):
`LEAK: ld.w -0x6dd0[gp],r6 ; sar 13,r6 ; subr r0,r6 ; jr 0x29D7E` ⇒ e5 = −(I8 >> 13), inc = (e5·56) >> 3 ≈ −I·56/8192 per
tick (τ 146 ms). The sign-aware variant (opposing > 200 leaks) was explored as LS / A2L.

- It is the best firm-hand policy by overshoot (firm-hand lurch ≤ 0.8° at ≥ 8 m/s, ≈ 0 at ≥ 10: the I is gone at
  release) — paid as a slow, short return instead (0.67 s, 1.9° short 0.5–3 s after the release, T3b).
- **It fails the goal's tracking on the real word:** 0.938–0.959 (L) and 0.81–0.89 (LS) on r71b's replayed torque
  (T2 and `e2_explore_rr.txt`), because 1–17 % of normal frames trip it. A leak threshold high enough to be safe is the
  hard freeze's 512, where a frozen I already does the job. **Not offered.**

### 3.4 Policy (iii): no firmware I, the DC from a fork angle integral — implementation E2-K0 (quantified, not offered)

Firmware: Ki stays V295's 0, ICL/DB untouched, the cave's policy block deleted (−24 B, `e2_cave_K0.hex`; 173 B written).
Fork model (`e2_k0.py`): θ_sp = θ_plan + acc, acc += (θ_plan − θ_meas, 60 ms old)·0.01/τ_o, frozen above 1200 wire
words (BELIEF: the fork's pressed threshold). τ_o 1 s and 2 s (the refuters' floor is 1 s).

EVIDENCE (`e2_k0_out.txt`; one column per job because the setpoint depends on the column's own angle; nominal and
b_lo×J_hi; turn-hold at a 1.5/2.5 on 8 speeds; the r71b paths; the light stiff hand, word 400):

| | turn-hold, 8 s hold | turn-hold 2 s after the ramp | goal metric 8–15 / 15–22 / > 22 m/s | light-hand lurch, max (8 / 11.75 / 19 / 26.9 m/s) |
|---|---|---|---|---|
| P2 (reference) | 0.69 / 0.71 | same | 0.900 / 0.856 / 1.002 | 7.2 / 10.5° |
| **K0, τ_o 1 s** | 0.997 / 0.996 | **0.85** | 0.969 / **0.920** / 0.971 (nominal); 0.967 / **0.919** / 0.967 (b_lo×J_hi) | **36.2° / 43.3°** at 8 m/s; 10.3 / 12.8° at 11.75 |
| K0, τ_o 2 s | 0.940 / 0.941 | 0.69 | 0.911 / **0.787** / 0.910 | 18.8 / 26.0° at 8 m/s |

- **It fails the goal's tracking at 15–22 m/s** (0.92 at the fastest integral the refuters' stability floor allows),
  because with no firmware I the inner loop's DC gain is Kp_T/(Kp_T + k) ≈ 0.43 at 17 m/s and a 1 s integral cannot
  close a 0.1–0.5 Hz path.
- **Its lurch is unbounded by anything in the firmware**: a hand below the fork's pressed threshold winds the fork
  integral for as long as it is held (36–43° after 3 s at 8 m/s). A fork-side clamp would be fork code beyond the angle
  interface.
- "P sized for the hold" instead of an integral would need Kp_T ≥ 10·k ≈ 800 T/deg at 17 m/s (×13 P2's), far outside
  GATE 2. **Policy (iii) is not offered.** Its only merit is 24 fewer cave bytes.

### 3.5 Policy (iv): the `gp-0x6803 == 2` arm (fork sends byte-2 bits 3:2 = 2) — overlay E2-…-X

See §4 for the trace. In the time domain it is two things: ramp-in 0.10 s instead of 0.99 s (`ramp_in` 328 vs 33 in the
scorer; engage droop T4) and the post-PID fade arm `0xCBAE4` (column A2-X; firm-hand and light-hand rows of T3).

### 3.6 Policy (v), NEW: the angle-referenced I bound — implementations E2-A, E2-A2 (and E2-A2S, -12k, -NR, -X)

**Idea.** The I's job in a held turn is the spring (and friction) at the wheel's angle. Let it wind further only while it
is below what the spring at the **current** wheel angle could need, plus a margin B: freeze when
`sgn(E')·(I >> 7) ≥ (|θ| << sh) + B`, θ = gp-0x6a00 (the held angle the P sees). Unwinding is never blocked.

- A hand that holds the wheel short of the setpoint drops the bound toward B → the I stays at the level the turn needed
  → the release finds no excess I. **No torque word is read, so no κ and no threshold enter.**
- A normal turn: the load slope is ≤ 13 T/deg below 12.5 m/s and ≤ 54 T/deg above (EVIDENCE, `e2_arb_slope.py`: every gated
  time member, 5 % error allowance, B 200 T); the bound slope is 26 / 102 T/deg + 200 T.
  Turn-hold and the goal metric are unchanged from ICL-only to 0.001 (T1, T2).
- The two-level slope (A2) additionally caps M-b at 8–12.5 m/s: during the return the I may not exceed 26 T/deg·θ + 200 T.

Cave block of E2-A2 (+48 B over P2, `e2_cave_A2.hex`; E2-A, one slope, is +32 B):

```
0xc4c64  24 4f 00 96   ld.h  -0x6a00[gp],r9    th (0.1 deg)                       [ANGLE-REFERENCED BOUND]
0xc4c68  e0 49         cmp   r0,r9
0xc4c6a  ae 05         bge   A1
0xc4c6c  80 49         subr  r0,r9             |th|
0xc4c6e  e4 47 a3 95   ld.hu -0x6a5e[gp],r8    v (64 counts per km/h)             [two-level slope]
0xc4c72  20 6e 40 0b   movea 2880,r0,r13       12.50 m/s
0xc4c76  ed 41         cmp   r13,r8
0xc4c78  bb 05         bh    AH
0xc4c7a  c4 4a         shl   4,r9              ~26 T/deg  (|th| << 4 = 160 S/deg x 0.160 T/S)
0xc4c7c  a5 05         br    AB
0xc4c7e  c6 4a         shl   6,r9  (AH)        ~102 T/deg
0xc4c80  09 4e e2 04   addi  1250,r9,r9 (AB)   + B = 1250 S (~200 T)
0xc4c84  24 6f 31 92   ld.w  -0x6dd0[gp],r13   I8 = 8 I (Honda's I state, READ only)
0xc4c88  aa 6a         sar   10,r13            I >> 7 = the I's share of S
0xc4c8a  e0 81         cmp   r0,r16
0xc4c8c  ae 05         bge   A2
0xc4c8e  80 69         subr  r0,r13            t = sgn(E')(I >> 7)
0xc4c90  e9 69         cmp   r9,r13  (A2)      t - bound
0xc4c92  ce 05         bge   FRZ               winding past the bound: freeze
```

E2-A3 inserts, right after the `addi` (+18 B, `e2_cave_A3.hex`, H1 and CONTROL C 0 mismatches): the low-speed cap that
gives the bound P2's own ICL at parking speed, where the post-release windup M-b is the whole lurch:

```
movea 1382,r0,r13      VCAP = 1382 counts = 6.0 m/s
cmp   r13,r8           r8 = v (still, from the slope test)
bh    NC               v > 6 m/s: no cap
movea 4096,r0,r13      CAP = 4096 S (~660 T = P2's ICL)
cmp   r13,r9
cmovh r13,r9,r9        bound = min(bound, CAP)
NC:
```

### 3.7 Verification of every cave (EVIDENCE)

| check | result | script / output |
|---|---|---|
| CONTROL A: my builder with no policy == `c2/rev2A/c2_cave_P2.hex` | byte-identical (156 B) | `e2_asm.py` → `e2_asm_out.txt` |
| CONTROL B: my interpreter == `ds_asm.run_bytes` on P2's bytes | 0 / 20 000 | same |
| H1: each cave's assembled BYTES executed vs `cave_ref` (the ordered policy decision), 40 000 inputs incl. sign, threshold, bound, speed-knee and validity edges; every non-scratch register (r14, r25 included) unchanged; RAM unchanged | **0 mismatches** for P2, S300, S200, A, Ah, AS, L13, A-NR, A2, A2S, A3, A2L, A2-NR, A2S-C, K0 | same |
| CONTROL C: the vectorised E2Lane (every time-domain number) makes the same decision as `cave_ref`, 8 000 random one-tick states each | **0 mismatches**, every implementation | `e2_ctlC.py` → `e2_ctlC_out.txt` |
| CONTROL E2-0: E2Lane with every new key at its default == DSLane, bit for bit, through the scorer's own run | max\|ΔT\| 0, max\|Δθ\| 0 (4 scenarios × P2/F2/P2-ICL8192) | `e2_lane.py` → `e2_lane_selftest.txt` |
| score_time CONTROL 1–3 re-run after my additive edit | all OK (unchanged) | `c2/rev2A/score_time_selftest.txt` |
| encoding forms new to the panel | `xor` = Ghidra's `xor r9,r12` at `0x504E2` (`29 61`); `blt` at `0x1C006` (`b6 05`); `bge` `0x29D94`; exact bytes decoded by Ghidra dry run: `ld.h -0x4f60,gp,r9` @`0x3B672`, `cmp r9,r13` @`0x2B59E`, `sar 0xa,r13` @`0x34F40`, `shl 6,r9` @`0x368AC`, `shl 4,r9` @`0x4FB3A`; `ld.w -0x6dd0[gp]` = the lane's own `0x29DA4` form | `e2_form_hits_out.txt` |

Scratch set of every cave = P2's {r6, r8, r9, r13, r16, r26}; no RAM written; reads added: gp-0x4f60 (S), gp-0x6a00,
gp-0x6dd0, a second gp-0x6a5e (A/A2), r25 (the camera gate only). **BELIEF until Ghidra decodes a BUILT image (H5).**

---

## 4. Policy (iv): what `gp-0x6803 == 2` touches, inside and outside the lane

### 4.1 Every access (EVIDENCE, `e2_scan_6803.py`, raw LE scan of stock and V295 at every halfword alignment; controls: the trace's four writers `0x526AC/0x526F8/0x52732/0x527CC` and the arm reader `0x29A74` all found)

23 accesses, identical in stock and V295: 4 writers (`FUN_00052676`, the 0xE4 RX handler), 8 engage-SM readers
(`0x29376…0x296A2`) and the arm reader `0x29A74` in the lane, **8 readers in `0x2A552…0x2A822`**, **1 at `0x2A976`**, and
**1 at `0x4E87E`**.

### 4.2 The readers outside the lane (EVIDENCE: Ghidra decompile + a controlled raw caller scan, `e2_scan_callers.py`)

| site | function | what it is | reachable? | effect of 6803 = 2 |
|---|---|---|---|---|
| `0x2A552…0x2A822` (8 reads) | `FUN_0002a508` | a copy of the lane's engage/ramp state machine (same states 1–8, same cals `0xC63F4/F6/F8/FA/FC`) | **NO**: 0 Format-V jarl/jr targets, 0 LE32 pointer literals, 0 movhi/movea pairs; the preceding instruction `0x2A504 dispose …, lp` is a return (no fall-through). Control: the same scan finds `0x22522 → 0x28EA6`. | none (dead) |
| `0x2A976` | `FUN_0002a93a` | the uncalled twin island (also holds gp-0x6dd0 accesses `0x2AC96/0x2B05C`) | **NO**, same scan | none (dead) |
| `0x2B35A` (asked about) | `FUN_0002b35a` | does **not** read 6803; reads `gp-0x679e` (set to 1 only on the 6803 = 2 ramp-in path) to pick `0xC63DA/DE` vs `0xC63DC/E0` for gp-0x697e/697c, and forwards gp-0x6b38 → gp-0x6b3c | **NO**, same scan (preceded by `jmp [lp]`) | none: dead, and the four cals are all **1024** in stock and V295 (my read), so 697e/697c = 1024 either way |
| `0x4E87E` | `FUN_0004e82e` | **UDS ReadDataByIdentifier handler for DID 0x48AC**: DID-table record at `0xB7870` = handler `0x0004E82E`, DID `0x48AC`, length `0x38`; it packs gp-0x69ae×13/4, (6802 & 3) \| (6803 & 3) << 2 \| 6805 << 7, the torque, gp-0x6a56, gp-0x6b38 and gp-0x6807 into a 56-byte response (NRC 0x31 if a session bit is clear) | only on a diagnostic request | **read-only**: the DID would report field 2 instead of 0. No control effect. |

`gp-0x679e` is also read inside the lane's SM (`0x2936E…0x296FC`) for the same 697e/697c choice (writes `0x2A26C`,
`0x2A296`, `0x2A2A2`): no effect, cals equal. `gp-0x679f` has 16 writers and no reader (scan).

### 4.3 Inside the lane (the 2026-09-30 trace §5, re-confirmed where it matters)

- Engage SM: ramp-in **0.10 s** (`0xC63FC` = 328/tick) instead of 0.99 s (`0xC63F8` = 33); ramp-out 0.50 s (`0xC63FA`
  = 66) instead of 2.05 s (`0xC63F6` = 16) — the ramp-out only paces an output A2 has already released.
- r25 = (gp-0x6803 == 2), `0x29A82 setfe r25` (my dry run), read at `0x29FDE cmp r0,r25` → `mov 0xCBAE4,r6` (my dry run):
  the post-PID fade arm. Values (my LERP): at a 2400-word firm hand (|tq| >> 5 = 75) stock 77/255 = 0.30, arm 2
  138/255 = 0.54 (**×1.8**); ×2.1 at 2048 raw; weaker only above ~3240 raw.
- The setpoint-taper arm (`0xCBA04/0xCBA74`) is inert under E4. ⚠ **The fork must keep sending 2 when it drops the
  request**, or state 7 falls to the 2.05 s path.

### 4.4 What (iv) buys beyond droop: a firmware camera interlock for F5 (+20 B, `e2_cave_A2S-C.hex`, H1 0 mismatches)

r25 is live in a register at the hook (the trace's def-use; my dry run of `0x29A82` and `0x29FDE`). The stock camera's
0xE4 carries field 0 in bits 3:2 (kit record, **BELIEF until re-measured on bus 2**), so r25 = 0 on a camera frame.

```
cmp r0,r25 ; be CAM                       (at the head of the policy block)
CAM: mov 0,r16 ; mov 0,r26 ; ld.w -0x6dd0[gp],r6 ; sar 6,r6 ; subr r0,r6 ; jr 0x29D7E
```

On any frame without field 2: P = 0, D = 0, the I decays ×0.125 per tick (gone in ~3 ms), the output lag releases in
~0.1 s. It requires the fork to send 2 on every frame — the same bit (iv) needs. **Not in any scored column** (the time
scorer has no r25 input); offered as the F5 follow-up the round-2 revisions asked for.

---

## 5. GATE 1 and GATE 2

**GATE 1 (EVIDENCE):** no implementation writes RAM (H1 checks memory unchanged). New reads only: gp-0x4f60 (signed hand,
written by `FUN_0007f3f8`, called at `0x221E0` before the lane at `0x22522` in the same 1 kHz pass — speed/torque trace §3.2),
gp-0x6a00 (already the P's angle), gp-0x6dd0 (Honda's I state, read before its own read at `0x29DA4` in the same tick;
the cave sees last tick's I8 exactly as Honda's code does), gp-0x6a5e (already read by the walk), r25 (camera gate).

**GATE 2 (EVIDENCE, `e2_freq.py` → `e2_freq_out.txt`, the common frequency scorer, 34 gated members × 140 speeds).**
Every policy acts only through the I's input r6 and Honda's clamp, so the small-signal loop is P2's while no condition
holds, and P2 with the I frozen (= Ki 0) while one does.

| loop | tier-A min PM | tier-B min PM | peak 5–30 Hz | M20 / L20 × V295 | GATE-2 fails |
|---|---|---|---|---|---|
| P2 (every E2 implementation, conditions off) | 46.7° (J_hi, 1 m/s) | 32.6° (b_lo×J_hi+h10, 1 m/s) | −5.6 dB | 0.67 / 0.68 | **0** |
| P2-I0 (every frozen state; K0's firmware loop) | 62.6° | 48.4° | −5.0 dB | 0.67 / 0.68 | **0** |
| P2 under the D-frame reading FA (D × 1/1.155) | 43.2° | 28.3° | −6.7 dB | 0.58 / 0.58 | **50 (J_hi 1–3.5 m/s; b_lo×J_hi+h10)** |
| P2-I0 under FA | 60.3° | 45.4° | −6.0 dB | 0.58 / 0.58 | 0 |

- **Inherited, not resolved here:** the refuters' F2 (D-operand frame) fails every E2 implementation exactly as it fails
  P2 (reproduced: J_hi 43.2°, b_lo×J_hi+h10 28.3°). The fix lives in the D gain/G table (another axis); the E2 policy
  block is independent of it and carries over byte for byte.
- **Every freeze makes the loop MORE stable** (P2-I0 +16° tier A, +16° tier B), so no E2 condition can push GATE 2 below
  P2's own numbers. The leak (rejected) sits between the two loops (BELIEF, not scored).
- The rejected F3 class (ms_free products at PM 13.5°) is a P2-skeleton property, unchanged by the I policy.

---

## 6. The scored tables (the common time scorer; one batch per scenario × speed × member, every column identical inputs)

Columns: P2 (rev2-A primary, unchanged) · R1 (ICL 8192) · S (8192 + opposing freeze 300) · L (8192 + leak > 512) ·
A (8192 + ARB one slope) · A2 (8192 + ARB two slopes) · A2S (A2 + opposing freeze 300) · A2-12k (A2 at ICL 12288) ·
A2-NR (A2, no ramp-in freeze) · A2-X (A2 + the `0xCBAE4` fade arm; read it with the 0.10 s ramp-in rows of T4).

Members: the scorer's nominal / bc / F_hi / b_lo×J_hi (+h10 for the hands). Speeds: 8–30 m/s plus 3.1/5 for context.
Hand models in T3: "stiff hand, word w" = the brief's convention (ds_time `ov_light`, the word SIGNED as the hand pushes);
"sensor κ" = the same stiff hand read by a consistent sensor (word = hand torque / κ); "torque hand" = a constant −300 T
for 3 s; "FIRM" = harness `ov_fade` (word −2400).

*(generated by `e2_report.py` from `exp_final_ext.json` and `final_suite.json`; T3 cells are "≥ 8 m/s / < 8 m/s")*

### T1. Turn-hold sized from r71b (min hold ratio over 8-30 m/s; target = a * L * SR / v^2, capped 90 deg)
| member | a (m/s2) | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | 1.5 | 0.813 | 0.984 | 0.986 | 0.987 | 0.984 | 0.984 | 0.985 | 0.988 | 0.985 | 0.987 |
| nominal | 2.5 | 0.693 | 0.987 | 0.987 | 0.987 | 0.987 | 0.987 | 0.987 | 0.992 | 0.987 | 0.987 |
| nominal | 3.5 | 0.664 | 0.909 | 0.909 | 0.909 | 0.909 | 0.908 | 0.909 | 0.993 | 0.909 | 0.907 |
| bc | 1.5 | 0.807 | 0.992 | 0.992 | 0.992 | 0.991 | 0.991 | 0.992 | 0.992 | 0.992 | 0.992 |
| bc | 2.5 | 0.689 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.997 | 0.983 | 0.983 |
| bc | 3.5 | 0.661 | 0.905 | 0.905 | 0.906 | 0.905 | 0.905 | 0.906 | 0.995 | 0.906 | 0.905 |
| F_hi | 1.5 | 0.806 | 0.987 | 0.988 | 0.985 | 0.985 | 0.985 | 0.985 | 0.985 | 0.985 | 0.988 |
| F_hi | 2.5 | 0.689 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.992 | 0.983 | 0.983 |
| F_hi | 3.5 | 0.661 | 0.905 | 0.905 | 0.905 | 0.905 | 0.905 | 0.905 | 0.993 | 0.905 | 0.905 |
| b_lo*J_hi | 1.5 | 0.828 | 0.991 | 0.991 | 0.991 | 0.991 | 0.991 | 0.991 | 0.991 | 0.991 | 0.991 |
| b_lo*J_hi | 2.5 | 0.707 | 0.997 | 0.997 | 0.997 | 0.997 | 0.997 | 0.997 | 0.997 | 0.997 | 0.997 |
| b_lo*J_hi | 3.5 | 0.678 | 0.928 | 0.928 | 0.928 | 0.928 | 0.928 | 0.928 | 0.994 | 0.928 | 0.928 |

### T2. The goal's tracking metric on r71b's own angle paths (OLS slope, 0.5 Hz LPF), clean / with r71b's torque word replayed
| band | torque word | statistic | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8-15 | clean | min of 4 members | 0.892 | 0.986 | 0.986 | 0.986 | 0.987 | 0.986 | 0.986 | 0.998 | 0.986 | 0.986 |
| 8-15 | replay | min of 4 members | 0.891 | 0.986 | 0.980 | 0.938 | 0.986 | 0.986 | 0.980 | 0.996 | 0.986 | 0.986 |
| 15-22 | clean | min of 4 members | 0.856 | 0.993 | 0.993 | 0.993 | 0.993 | 0.993 | 0.993 | 0.995 | 0.993 | 0.993 |
| 15-22 | replay | min of 4 members | 0.855 | 0.991 | 0.984 | 0.958 | 0.991 | 0.991 | 0.984 | 0.991 | 0.991 | 0.991 |
| >22 | clean | min of 4 members | 1.000 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 |
| >22 | replay | min of 4 members | 1.000 | 1.001 | 0.996 | 0.990 | 1.001 | 1.001 | 0.996 | 1.001 | 1.001 | 1.001 |
| all | clean | I freeze/leak duty | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| all | replay | I freeze/leak duty | 0.010 | 0.010 | 0.039 | 0.010 | 0.010 | 0.010 | 0.039 | 0.010 | 0.010 | 0.010 |

### T3. Release lurch (overshoot past the setpoint after the hand lets go), max over speeds; >= 8 m/s | < 8 m/s
**nominal**
| hand | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| stiff hand, word 100 | 7.17 / 4.2 | 17.59 / 13.7 | 17.59 / 13.7 | 17.59 / 13.7 | 4.83 / 13.7 | 1.92 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.92 / 7.8 |
| stiff hand, word 200 | 7.17 / 4.2 | 17.59 / 13.7 | 17.59 / 13.7 | 17.59 / 13.7 | 4.83 / 13.7 | 1.92 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.92 / 7.8 |
| stiff hand, word 400 | 7.17 / 4.2 | 17.59 / 13.7 | 5.26 / 13.7 | 17.59 / 13.7 | 4.83 / 13.7 | 1.92 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.91 / 7.8 | 1.92 / 7.8 |
| stiff hand, word 511 | 7.17 / 4.2 | 17.59 / 13.7 | 3.95 / 12.4 | 17.59 / 13.7 | 4.83 / 13.7 | 1.92 / 7.8 | 1.91 / 7.4 | 1.91 / 7.8 | 1.91 / 7.8 | 1.92 / 7.8 |
| stiff hand, sensor kappa 0.15 | 3.82 / 4.3 | 3.81 / 12.2 | 3.82 / 12.2 | 1.30 / 10.3 | 2.52 / 10.6 | 1.83 / 7.9 | 1.83 / 7.9 | 1.83 / 7.9 | 1.83 / 7.9 | 1.82 / 7.9 |
| stiff hand, sensor kappa 0.6 | 3.27 / 4.2 | 3.28 / 12.1 | 3.28 / 11.7 | 1.39 / 9.8 | 2.41 / 10.5 | 1.77 / 7.8 | 1.78 / 7.9 | 1.77 / 7.8 | 1.77 / 7.8 | 1.77 / 7.8 |
| stiff hand, sensor kappa 2.0 | 7.17 / 4.2 | 12.13 / 10.3 | 5.68 / 10.0 | 10.94 / 8.2 | 3.34 / 9.9 | 1.91 / 7.5 | 1.88 / 7.5 | 1.91 / 7.5 | 1.91 / 7.5 | 1.92 / 7.5 |
| 300 T torque hand, word 500 | 4.07 / 3.8 | 4.07 / 3.3 | 1.39 / 0.3 | 4.07 / 3.2 | 4.08 / 3.3 | 3.01 / 3.9 | 1.39 / 0.4 | 3.00 / 3.2 | 3.01 / 3.2 | 3.01 / 3.9 |
| 300 T torque hand, word 150 | 4.07 / 3.8 | 4.07 / 3.3 | 4.07 / 3.3 | 4.07 / 3.2 | 4.08 / 3.3 | 3.01 / 3.9 | 3.01 / 3.3 | 3.00 / 3.2 | 3.01 / 3.2 | 3.01 / 3.9 |
| FIRM hand, word 2400 | 3.32 / 4.3 | 3.31 / 11.0 | 3.12 / 10.4 | 0.82 / 8.9 | 2.81 / 11.0 | 1.83 / 8.0 | 1.83 / 7.9 | 1.84 / 8.0 | 1.85 / 8.0 | 1.83 / 7.9 |

**bc**
| hand | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| stiff hand, word 100 | 7.77 / 6.8 | 19.70 / 17.0 | 19.69 / 17.0 | 19.70 / 17.0 | 6.92 / 16.8 | 3.63 / 8.7 | 3.63 / 8.7 | 3.62 / 8.7 | 3.62 / 8.7 | 3.63 / 8.7 |
| stiff hand, word 200 | 7.77 / 6.8 | 19.70 / 17.0 | 19.69 / 17.0 | 19.70 / 17.0 | 6.92 / 16.8 | 3.63 / 8.7 | 3.63 / 8.7 | 3.62 / 8.7 | 3.62 / 8.7 | 3.63 / 8.7 |
| stiff hand, word 400 | 7.77 / 6.8 | 19.70 / 17.0 | 6.98 / 16.7 | 19.70 / 17.0 | 6.92 / 16.8 | 3.63 / 8.7 | 3.63 / 8.7 | 3.62 / 8.7 | 3.62 / 8.7 | 3.63 / 8.7 |
| stiff hand, word 511 | 7.77 / 6.8 | 19.70 / 17.0 | 5.43 / 13.5 | 19.70 / 17.0 | 6.92 / 16.8 | 3.63 / 8.7 | 3.63 / 7.6 | 3.62 / 8.7 | 3.62 / 8.7 | 3.63 / 8.7 |
| stiff hand, sensor kappa 0.15 | 4.80 / 6.0 | 4.79 / 13.5 | 4.80 / 13.4 | 1.67 / 10.3 | 3.24 / 10.9 | 2.24 / 7.7 | 2.23 / 7.7 | 2.23 / 7.7 | 2.23 / 7.7 | 2.24 / 7.8 |
| stiff hand, sensor kappa 0.6 | 4.40 / 6.0 | 4.40 / 13.3 | 4.30 / 12.7 | 1.34 / 9.6 | 3.34 / 10.7 | 2.38 / 7.6 | 2.36 / 7.7 | 2.37 / 7.7 | 2.38 / 7.7 | 2.39 / 7.6 |
| stiff hand, sensor kappa 2.0 | 7.77 / 6.1 | 13.37 / 11.1 | 5.97 / 10.4 | 13.04 / 7.8 | 5.12 / 10.3 | 3.62 / 7.3 | 2.94 / 7.2 | 3.61 / 7.3 | 3.61 / 7.3 | 3.63 / 7.2 |
| 300 T torque hand, word 500 | 5.02 / 4.4 | 4.95 / 4.3 | 1.02 / 0.1 | 5.02 / 4.4 | 5.02 / 4.4 | 3.41 / 4.4 | 1.03 / 0.1 | 3.41 / 4.4 | 3.41 / 4.3 | 3.41 / 4.9 |
| 300 T torque hand, word 150 | 5.02 / 4.4 | 4.95 / 4.3 | 4.95 / 4.3 | 5.02 / 4.4 | 5.02 / 4.4 | 3.41 / 4.4 | 3.41 / 4.4 | 3.41 / 4.4 | 3.41 / 4.3 | 3.41 / 4.9 |
| FIRM hand, word 2400 | 4.10 / 5.8 | 4.10 / 11.2 | 3.87 / 10.6 | 0.94 / 8.5 | 3.56 / 11.2 | 2.25 / 7.8 | 2.25 / 7.9 | 2.26 / 7.8 | 2.25 / 7.8 | 2.28 / 7.8 |

**b_lo*J_hi**
| hand | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| stiff hand, word 100 | 10.47 / 10.5 | 25.15 / 21.7 | 25.15 / 21.7 | 25.15 / 21.7 | 9.00 / 21.6 | 5.18 / 13.9 | 5.21 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 |
| stiff hand, word 200 | 10.47 / 10.5 | 25.15 / 21.7 | 25.15 / 21.7 | 25.15 / 21.7 | 9.00 / 21.6 | 5.18 / 13.9 | 5.21 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 |
| stiff hand, word 400 | 10.47 / 10.5 | 25.15 / 21.7 | 10.38 / 21.7 | 25.15 / 21.7 | 9.00 / 21.6 | 5.18 / 13.9 | 5.21 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 |
| stiff hand, word 511 | 10.47 / 10.5 | 25.15 / 21.7 | 8.80 / 21.5 | 25.15 / 21.7 | 9.00 / 21.6 | 5.18 / 13.9 | 5.21 / 13.6 | 5.20 / 13.9 | 5.20 / 13.9 | 5.20 / 13.9 |
| stiff hand, sensor kappa 0.15 | 7.53 / 10.3 | 8.95 / 21.3 | 8.84 / 21.3 | 4.50 / 19.4 | 6.00 / 18.2 | 4.25 / 12.7 | 4.19 / 12.7 | 4.24 / 12.7 | 4.24 / 12.7 | 4.19 / 12.7 |
| stiff hand, sensor kappa 0.6 | 7.56 / 10.3 | 8.69 / 21.3 | 7.90 / 21.3 | 3.71 / 18.6 | 5.96 / 18.2 | 4.33 / 12.7 | 4.25 / 12.7 | 4.32 / 12.7 | 4.33 / 12.7 | 4.34 / 12.7 |
| stiff hand, sensor kappa 2.0 | 10.47 / 10.5 | 17.18 / 21.6 | 8.18 / 21.3 | 15.68 / 16.7 | 7.41 / 18.0 | 5.16 / 12.7 | 4.74 / 12.7 | 5.20 / 12.7 | 5.20 / 12.7 | 5.20 / 12.7 |
| 300 T torque hand, word 500 | 6.02 / 4.1 | 6.03 / 4.2 | 1.90 / 1.5 | 6.03 / 4.2 | 6.03 / 4.2 | 3.08 / 4.2 | 1.91 / 1.5 | 3.07 / 4.2 | 3.08 / 4.2 | 3.08 / 4.2 |
| 300 T torque hand, word 150 | 6.02 / 4.1 | 6.03 / 4.2 | 6.02 / 4.2 | 6.03 / 4.2 | 6.03 / 4.2 | 3.08 / 4.2 | 3.07 / 4.2 | 3.07 / 4.2 | 3.08 / 4.2 | 3.08 / 4.2 |
| FIRM hand, word 2400 | 7.24 / 10.2 | 7.79 / 20.8 | 7.55 / 20.6 | 3.73 / 17.3 | 6.01 / 18.4 | 4.18 / 12.7 | 4.13 / 12.7 | 4.18 / 12.7 | 4.17 / 12.7 | 4.19 / 12.7 |

**b_lo*J_hi+h10**
| hand | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| stiff hand, word 100 | 10.85 / 12.7 | 26.01 / 24.2 | 26.00 / 24.2 | 26.01 / 24.2 | 10.09 / 24.1 | 6.17 / 15.9 | 6.16 / 15.9 | 6.16 / 15.9 | 6.16 / 16.1 | 6.16 / 16.1 |
| stiff hand, word 200 | 10.85 / 12.7 | 26.01 / 24.2 | 26.00 / 24.2 | 26.01 / 24.2 | 10.09 / 24.1 | 6.17 / 15.9 | 6.16 / 15.9 | 6.16 / 15.9 | 6.16 / 16.1 | 6.16 / 16.1 |
| stiff hand, word 400 | 10.85 / 12.7 | 26.01 / 24.2 | 11.69 / 24.2 | 26.01 / 24.2 | 10.09 / 24.1 | 6.17 / 15.9 | 6.16 / 15.9 | 6.16 / 15.9 | 6.16 / 16.1 | 6.16 / 16.1 |
| stiff hand, word 511 | 10.85 / 12.7 | 26.01 / 24.2 | 10.08 / 24.1 | 26.01 / 24.2 | 10.09 / 24.1 | 6.17 / 15.9 | 6.16 / 15.2 | 6.16 / 15.9 | 6.16 / 16.1 | 6.16 / 16.1 |
| stiff hand, sensor kappa 0.15 | 8.63 / 12.4 | 10.50 / 23.9 | 10.35 / 23.9 | 5.70 / 22.6 | 6.80 / 19.8 | 5.05 / 14.3 | 5.00 / 14.3 | 5.05 / 14.3 | 5.05 / 14.3 | 5.02 / 14.3 |
| stiff hand, sensor kappa 0.6 | 8.64 / 12.4 | 10.14 / 23.9 | 9.34 / 23.9 | 4.89 / 22.2 | 6.87 / 19.8 | 5.12 / 14.3 | 5.07 / 14.3 | 5.11 / 14.3 | 5.12 / 14.3 | 5.15 / 14.3 |
| stiff hand, sensor kappa 2.0 | 10.85 / 12.7 | 17.89 / 24.2 | 9.59 / 24.0 | 15.10 / 20.1 | 8.20 / 20.1 | 6.15 / 14.3 | 5.58 / 14.3 | 6.15 / 14.3 | 6.15 / 14.3 | 6.16 / 14.4 |
| 300 T torque hand, word 500 | 6.20 / 4.3 | 6.21 / 3.5 | 2.08 / 2.0 | 6.20 / 3.7 | 6.21 / 3.7 | 3.23 / 3.7 | 2.08 / 2.0 | 3.22 / 3.7 | 3.23 / 3.7 | 3.22 / 3.7 |
| 300 T torque hand, word 150 | 6.20 / 4.3 | 6.21 / 3.5 | 6.20 / 3.7 | 6.20 / 3.7 | 6.21 / 3.7 | 3.23 / 3.7 | 3.23 / 3.7 | 3.22 / 3.7 | 3.23 / 3.7 | 3.22 / 3.7 |
| FIRM hand, word 2400 | 8.31 / 12.3 | 9.17 / 23.4 | 8.98 / 23.2 | 4.89 / 20.7 | 6.81 / 20.0 | 4.95 / 14.3 | 4.92 / 14.3 | 4.96 / 14.3 | 4.96 / 14.3 | 4.98 / 14.3 |

**worst lurch over every hand model, >= 8 m/s**
| member | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| nominal | 7.17 | 17.59 | 17.59 | 17.59 | 4.83 | 3.01 | 3.01 | 3.00 | 3.01 | 3.01 |
| bc | 7.77 | 19.70 | 19.69 | 19.70 | 6.92 | 3.63 | 3.63 | 3.62 | 3.62 | 3.63 |
| b_lo*J_hi | 10.47 | 25.15 | 25.15 | 25.15 | 9.00 | 5.18 | 5.21 | 5.20 | 5.20 | 5.20 |
| b_lo*J_hi+h10 | 10.85 | 26.01 | 26.00 | 26.01 | 10.09 | 6.17 | 6.16 | 6.16 | 6.16 | 6.16 |

### T3b. After the release: return time to within 10 % (s) and the shortfall 0.5-3 s after (deg), max over >= 8 m/s
| member | hand | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | stiff hand, word 400 | 0.12 s / 0.62 | 0.07 s / 1.67 | 0.27 s / 0.20 | 0.07 s / 1.67 | 0.23 s / 0.24 | 0.27 s / 0.19 | 0.28 s / 0.19 | 0.27 s / 0.19 | 0.27 s / 0.19 | 0.27 s / 0.19 |
| nominal | stiff hand, sensor kappa 0.6 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.45 s / 0.70 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.30 s / 0.18 | 0.30 s / 0.18 |
| nominal | FIRM hand, word 2400 | 0.33 s / 0.19 | 0.33 s / 0.18 | 0.34 s / 0.19 | 0.67 s / 1.94 | 0.33 s / 0.18 | 0.34 s / 0.18 | 0.34 s / 0.19 | 0.33 s / 0.19 | 0.33 s / 0.18 | 0.33 s / 0.18 |
| b_lo*J_hi | stiff hand, word 400 | 0.12 s / 2.46 | 0.09 s / 2.68 | 0.19 s / 1.98 | 0.09 s / 2.68 | 0.18 s / 2.09 | 0.19 s / 2.37 | 0.20 s / 2.36 | 0.19 s / 2.37 | 0.19 s / 2.37 | 0.19 s / 2.38 |
| b_lo*J_hi | stiff hand, sensor kappa 0.6 | 0.19 s / 2.10 | 0.19 s / 1.77 | 0.20 s / 1.73 | 0.31 s / 1.60 | 0.20 s / 1.76 | 0.21 s / 2.02 | 0.21 s / 2.00 | 0.21 s / 2.04 | 0.21 s / 2.04 | 0.21 s / 2.04 |
| b_lo*J_hi | FIRM hand, word 2400 | 0.24 s / 1.87 | 0.24 s / 1.67 | 0.24 s / 1.66 | 0.64 s / 1.53 | 0.24 s / 1.65 | 0.24 s / 1.89 | 0.24 s / 1.88 | 0.24 s / 1.90 | 0.24 s / 1.88 | 0.23 s / 1.91 |

### T4. Engage under a handed-over load: max droop (deg), >= 8 m/s | all speeds; stock ramp-in (0.99 s) and the 6803 == 2 ramp-in (0.10 s)
| member | ramp-in | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | 0.99 s | 4.53 / 4.67 (ovs 0.19) | 4.53 / 4.66 (ovs 0.20) | 4.53 / 4.66 (ovs 0.19) | 4.53 / 4.66 (ovs 0.19) | 4.53 / 4.66 (ovs 0.19) | 4.53 / 4.66 (ovs 0.19) | 4.53 / 4.66 (ovs 0.19) | 4.53 / 4.67 (ovs 0.20) | 4.12 / 4.12 (ovs 0.39) | 4.53 / 4.66 (ovs 0.19) |
| nominal | 0.10 s | 3.03 / 3.03 (ovs 0.12) | 3.02 / 3.02 (ovs 0.12) | 3.02 / 3.02 (ovs 0.12) | 3.02 / 3.02 (ovs 0.12) | 3.03 / 3.03 (ovs 0.12) | 3.02 / 3.02 (ovs 0.12) | 3.03 / 3.03 (ovs 0.12) | 3.02 / 3.02 (ovs 0.13) | 3.03 / 3.03 (ovs 0.13) | 3.03 / 3.03 (ovs 0.12) |
| bc | 0.99 s | 5.01 / 5.19 (ovs 0.05) | 5.01 / 5.19 (ovs 0.05) | 5.01 / 5.20 (ovs 0.06) | 5.01 / 5.19 (ovs 0.05) | 5.02 / 5.20 (ovs 0.05) | 5.02 / 5.20 (ovs 0.05) | 5.01 / 5.20 (ovs 0.05) | 5.02 / 5.20 (ovs 0.06) | 4.65 / 4.70 (ovs 0.46) | 5.01 / 5.19 (ovs 0.05) |
| bc | 0.10 s | 3.36 / 3.36 (ovs 0.02) | 3.36 / 3.36 (ovs 0.02) | 3.36 / 3.36 (ovs 0.03) | 3.36 / 3.36 (ovs 0.03) | 3.36 / 3.36 (ovs 0.02) | 3.36 / 3.36 (ovs 0.02) | 3.36 / 3.36 (ovs 0.03) | 3.36 / 3.36 (ovs 0.02) | 3.36 / 3.36 (ovs 0.04) | 3.36 / 3.36 (ovs 0.03) |
| b_lo*J_hi | 0.99 s | 6.14 / 7.91 (ovs 0.42) | 6.13 / 7.90 (ovs 0.42) | 6.13 / 7.90 (ovs 0.43) | 6.13 / 7.90 (ovs 0.43) | 6.13 / 7.90 (ovs 0.42) | 6.14 / 7.90 (ovs 0.43) | 6.13 / 7.90 (ovs 0.43) | 6.13 / 7.90 (ovs 0.42) | 5.59 / 6.94 (ovs 2.01) | 6.13 / 7.90 (ovs 0.42) |
| b_lo*J_hi | 0.10 s | 4.21 / 5.19 (ovs 0.32) | 4.22 / 5.19 (ovs 0.32) | 4.21 / 5.19 (ovs 0.31) | 4.21 / 5.19 (ovs 0.31) | 4.22 / 5.20 (ovs 0.32) | 4.22 / 5.19 (ovs 0.32) | 4.21 / 5.19 (ovs 0.32) | 4.22 / 5.19 (ovs 0.32) | 4.21 / 5.19 (ovs 0.31) | 4.21 / 5.19 (ovs 0.32) |
| b_lo*J_hi+h10 | 0.99 s | 6.33 / 8.12 (ovs 0.62) | 6.33 / 8.12 (ovs 0.63) | 6.33 / 8.12 (ovs 0.64) | 6.33 / 8.12 (ovs 0.63) | 6.33 / 8.12 (ovs 0.63) | 6.33 / 8.13 (ovs 0.64) | 6.33 / 8.12 (ovs 0.63) | 6.33 / 8.12 (ovs 0.63) | 5.82 / 7.24 (ovs 2.51) | 6.33 / 8.12 (ovs 0.64) |
| b_lo*J_hi+h10 | 0.10 s | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.54) | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.54) | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.54) | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.53) | 4.45 / 5.46 (ovs 0.55) |

### T5. THE COMMON TIME SCORER, its own scenarios / speeds / members / metrics (score_time.SCENS x SPEEDS x MEMBERS)
| metric (every member) | P2 | R1 | S | L | A | A2 | A2S | A2-12k | A2-NR | A2-X |
|---|---|---|---|---|---|---|---|---|---|---|
| rh hold ratio, min >= 8 m/s (bar >= 0.90) | 0.990 | 0.990 | 0.990 | 0.991 | 0.991 | 0.991 | 0.991 | 0.990 | 0.991 | 0.988 |
| T 5-30 Hz in holds, max (bar <= 2.0) | 0.692 | 0.755 | 0.732 | 0.726 | 0.726 | 0.736 | 0.729 | 0.735 | 0.717 | 0.730 |
| detector reversals, max (bar 0) | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| sentinel push toward, max deg (bar <= 0.1) | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 |
| tmo abs(T) after sentinel + 0.25 s, max (bar < 50) | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| int32 wraps | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| s02 wire gain, min >= 8 m/s | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 | 0.833 |
| s05 wire gain, min >= 8 m/s | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 | 0.096 |
| dwell-then-jump events s02+s05+ssm, sum >= 8 m/s | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 2.000 | 1.000 | 1.000 | 1.000 |
| dwell-then-jump events s02+s05+ssm, sum < 8 m/s | 34.000 | 33.000 | 32.000 | 36.000 | 32.000 | 34.000 | 32.000 | 34.000 | 34.000 | 33.000 |
| ov_light400 (unsigned word) lurch, max >= 8 m/s | 10.437 | 24.830 | 24.825 | 24.832 | 9.004 | 5.177 | 5.210 | 5.204 | 5.204 | 5.197 |
| ov_light1000 lurch, max >= 8 m/s | 7.576 | 8.259 | 8.261 | 2.948 | 6.929 | 5.123 | 5.159 | 5.159 | 5.159 | 5.170 |
| ov_fade (firm) lurch, max >= 8 m/s | 7.240 | 7.789 | 7.795 | 3.709 | 5.987 | 4.178 | 4.185 | 4.188 | 4.180 | 4.188 |
| eng_load droop, max >= 8 m/s | 6.137 | 6.131 | 6.135 | 6.133 | 6.133 | 6.137 | 6.134 | 6.133 | 5.592 | 6.135 |
| co-steer release droop, max | 2.165 | 2.159 | 0.997 | 2.159 | 2.159 | 2.160 | 1.009 | 2.163 | 2.153 | 2.156 |
| dead band lag, max >= 8 m/s | 0.305 | 0.316 | 0.313 | 0.310 | 0.311 | 0.310 | 0.313 | 0.309 | 0.307 | 0.317 |
| tmo hold deviation, max | 1.012 | 0.578 | 0.577 | 0.589 | 0.581 | 0.581 | 0.586 | 0.576 | 0.596 | 0.593 |
| hard turn 1.6-3 Hz / command's own, max >= 8 m/s | 1.395 | 1.359 | 1.360 | 1.359 | 1.359 | 1.288 | 1.288 | 1.288 | 1.288 | 1.288 |


### 6.5 Reading T1–T5

- **T1/T2 (F1):** every ICL-raised column meets turn-hold ≥ 0.90 and the goal metric ≥ 0.95 at ≥ 8 m/s, clean and with
  the real torque word, **except L (0.938 at 8–15 m/s with the replay: REJECTED)**. A2-12k is the only column ≥ 0.98
  everywhere including a 3.5 (0.993). The policy block costs nothing on F1: A, A2, A2-12k equal R1/I12k to 0.001.
- **T3 (F4 lurch):** the brief's own unsigned `ov_light400` in T5 and the signed hand family in T3 agree: ICL alone
  ×2.4 (R1 24.8° vs P2 10.4°, b_lo×J_hi); S only helps a hand above its threshold *and* signed opposing (on T5's
  unsigned word it reads as aiding: 24.8°); **A2 is the first column whose worst lurch over every hand model at
  ≥ 8 m/s is below P2's on every member** (3.0 / 3.6 / 5.2 / 6.2° vs 7.2 / 7.8 / 10.5 / 10.9°) and below the 8° bar
  rev2-B pre-registered, aged hold included.
- **T4 (F4 droop):** no I policy moves it (±0.01°); the 0.10 s ramp-in of (iv) cuts it by a third; A2-NR −9 % for a
  2° engage overshoot.
- **T5 (the common scorer's own pre-registered bars):** every column passes every bar (hold ≥ 0.988, 5–30 Hz ≤ 0.76
  counts, 0 reversals, sentinel push ≤ 0.002°, timeout |T| 0, 0 wraps). Side effects of the ICL raise worth noting:
  the 510 ms timeout hold deviation **improves** 1.01° → 0.58° (the I holds the turn instead of P sagging) and the
  hard-turn 1.6–3 Hz ratio improves 1.40 → 1.29 with A2; the co-steer release droop **halves** with the opposing-hand
  freeze (S/A2S 1.0° vs 2.2°: a driver pushing past the setpoint no longer drains the I). The s02 0.2 Hz wire gain
  (0.833) and the small-signal dwell-then-jump counts are identical across columns: the I policy neither fixes nor
  worsens the F4 small-correction class (another axis).

### 6.6 E2-A3: the < 8 m/s repair of A2 (EVIDENCE, `e2_a3.py`; same common-scorer batches; P2 / A2 / A3 / A3-12k)

Lurch, worst over the hand family (`lh` 100/400, `lk` 0.15/0.6/2.0, `ls` 300/0.6, firm), "< 8 m/s | ≥ 8 m/s", then per
speed below 8 m/s; then turn-hold at 3.1–7 m/s where the cap can bind:

```
# e2_a3: A2 vs A3 (low-speed cap = P2's ICL below 6 m/s); lurch max per member, < 8 m/s | >= 8 m/s, worst over hands
nominal        P2 4.59 | 7.16 A2 7.96 | 3.00 A3 4.31 | 3.01 A3-12k 4.31 | 3.00
   v  3.1: P2 4.25 A2 7.96 A3 4.31 A3-12k 4.31
   v  5.0: P2 4.21 A2 3.45 A3 3.43 A3-12k 3.44
   v  6.0: P2 4.41 A2 3.65 A3 3.66 A3-12k 3.65
   v  7.0: P2 4.59 A2 3.46 A3 3.46 A3-12k 3.46
   v  8.0: P2 4.57 A2 3.00 A3 3.01 A3-12k 3.00
bc             P2 6.83 | 7.78 A2 8.72 | 3.63 A3 6.41 | 3.63 A3-12k 6.41 | 3.63
   v  3.1: P2 6.37 A2 8.72 A3 6.41 A3-12k 6.41
   v  5.0: P2 6.78 A2 5.13 A3 5.12 A3-12k 5.13
   v  6.0: P2 6.81 A2 4.19 A3 4.19 A3-12k 4.19
   v  7.0: P2 6.83 A2 3.95 A3 3.96 A3-12k 3.96
   v  8.0: P2 6.74 A2 3.63 A3 3.63 A3-12k 3.63
b_lo*J_hi      P2 10.54 | 10.47 A2 13.88 | 5.21 A3 10.60 | 5.21 A3-12k 10.60 | 5.21
   v  3.1: P2 10.54 A2 13.88 A3 10.60 A3-12k 10.60
   v  5.0: P2 9.16 A2 7.87 A3 7.86 A3-12k 7.86
   v  6.0: P2 8.72 A2 6.39 A3 6.39 A3-12k 6.40
   v  7.0: P2 8.38 A2 5.51 A3 5.54 A3-12k 5.53
   v  8.0: P2 8.09 A2 5.21 A3 5.21 A3-12k 5.21
b_lo*J_hi+h10  P2 12.69 | 10.85 A2 15.94 | 6.16 A3 12.76 | 6.16 A3-12k 12.76 | 6.16
   v  3.1: P2 12.69 A2 15.94 A3 12.76 A3-12k 12.76
   v  5.0: P2 10.64 A2 9.30 A3 9.30 A3-12k 9.20
   v  6.0: P2 9.99 A2 7.50 A3 7.51 A3-12k 7.50
   v  7.0: P2 9.51 A2 6.45 A3 6.45 A3-12k 6.45
   v  8.0: P2 9.18 A2 6.16 A3 6.16 A3-12k 6.16
turn-hold 3.1-7 m/s min nominal    a 0.5: P2 0.999 A2 0.999 A3 0.999 A3-12k 0.998
turn-hold 3.1-7 m/s min nominal    a 1.0: P2 0.947 A2 0.999 A3 0.947 A3-12k 0.947
turn-hold 3.1-7 m/s min nominal    a 1.5: P2 0.932 A2 0.999 A3 0.934 A3-12k 0.934
turn-hold 3.1-7 m/s min bc         a 0.5: P2 0.999 A2 0.999 A3 0.999 A3-12k 0.999
turn-hold 3.1-7 m/s min bc         a 1.0: P2 0.950 A2 0.999 A3 0.950 A3-12k 0.950
turn-hold 3.1-7 m/s min bc         a 1.5: P2 0.935 A2 0.999 A3 0.937 A3-12k 0.937
turn-hold 3.1-7 m/s min F_hi       a 0.5: P2 0.992 A2 0.998 A3 0.992 A3-12k 0.992
turn-hold 3.1-7 m/s min F_hi       a 1.0: P2 0.939 A2 0.999 A3 0.939 A3-12k 0.939
turn-hold 3.1-7 m/s min F_hi       a 1.5: P2 0.927 A2 0.999 A3 0.928 A3-12k 0.928
turn-hold 3.1-7 m/s min b_lo*J_hi  a 0.5: P2 0.986 A2 0.998 A3 0.986 A3-12k 0.986
turn-hold 3.1-7 m/s min b_lo*J_hi  a 1.0: P2 0.924 A2 0.998 A3 0.924 A3-12k 0.924
turn-hold 3.1-7 m/s min b_lo*J_hi  a 1.5: P2 0.904 A2 0.998 A3 0.910 A3-12k 0.910
```

The common scorer's own low-speed scenarios (3.1 / 5 m/s, all five members, `e2_a3.py lo`):

```
# e2_a3 low-speed (3.1 / 5 m/s) on the common scorer's own scenarios and metrics: P2 / A2 / A3 / A3-12k
dj_events        s02+s05+ssm : P2 32.00 A2 32.00 A3 32.00 A3-12k 34.00
stick_pct        ssm         : P2 90.70 A2 90.70 A3 90.12 A3-12k 90.12
hold_ratio       rh          : P2 0.98 A2 1.00 A3 0.98 A3-12k 0.98
overshoot_pct    st          : P2 32.92 A2 29.07 A3 26.39 A3-12k 26.39
db_lag           db          : P2 0.60 A2 0.60 A3 0.60 A3-12k 0.60
lurch_overshoot  ov_light400 : P2 10.54 A2 13.88 A3 10.60 A3-12k 10.60
lurch_overshoot  ov_fade     : P2 10.21 A2 12.72 A3 9.60 A3-12k 9.58
cs_droop         cs          : P2 2.17 A2 2.16 A3 2.17 A3-12k 2.16
hold_slips       rh          : P2 14.00 A2 8.00 A3 14.00 A3-12k 14.00
```

- **A3 = A2 at ≥ 6 m/s and = P2 (within 0.1°) at parking speed**: the low-speed lurch returns to P2's (10.6° vs 10.5°
  b_lo×J_hi; 4.3° vs 4.6° nominal) and is lower than P2's at 5–7 m/s. The firm-hand release at 3–5 m/s is better than
  P2's (9.6° vs 10.2°).
- The price: at ≤ 6 m/s the I is capped at P2's 668 T again, so turn-hold there is P2's (0.90–0.95 at a 1.0–1.5)
  instead of A2's 0.998 — "loose at low speed" is an operator complaint, so this is a real trade, declared (M-E2-1b).
- Dwell-then-jump and stick-slip at 3–5 m/s are unchanged by any I policy (32–34 events, ~90 % stuck on ±1°: the
  M1 class every candidate in the record carries).


---

## 7. Pre-declared misses (each quantified, with the stop band that covers it)

Stop bands are rev2-A's (R1–R9, R3\* 0.5–5.5 Hz, R4) unchanged, plus the E2 ones in §9.

| # | criterion (goal) | band | predicted (A2 / A2-12k; the others in §0.2) | stop band / revert | basis |
|---|---|---|---|---|---|
| M-E2-1 | the loop releases to the driver (lurch) | **< 8 m/s**, large releases (25–45° at 3–5 m/s, no fork O1) | A2 8.0° nominal / 13.9° b_lo×J_hi vs P2's 4.6° / 10.5°: the post-release windup (M-b) at ICL 8192 under a 26 T/deg bound. **A3 repairs it: 4.3° / 10.6°** (§6.6) | R9 (operator: "a lurch on letting go"); release overshoot > P2's T3 value + 2° at < 8 m/s | EVIDENCE sim |
| M-E2-1b (A3 only) | "loose at low speed" (turn-hold below 8 m/s, not a goal criterion) | ≤ 6 m/s, curves needing > 668 T | A3 = P2: hold 0.90–0.95 at a 1.0–1.5 (A2 0.998) | operator words ("looser at low speed than V295/P2") | EVIDENCE sim (`e2_a3_out.txt`) |
| M-E2-2 | turn-hold ≥ 0.90 | a 3.5 at ≥ 15 m/s (past r71b's p99.9 at 15–22) | A2 0.905–0.928; **A2-12k 0.993** | on-car turn-hold < 0.90 ≥ 60 s in a band = FAILED (rev2-A §8.2) | EVIDENCE sim |
| M-E2-3 | an override hand is not a disturbance | a hand that lets the wheel come back (a force hand) reading ≤ 300 words, held for seconds | the I absorbs it as it absorbs any disturbance: release overshoot ≤ 3.0 / 3.4 / 3.1 / 3.2° (A2, ≥ 8 m/s), = P2's 4.1–6.2° class and smaller | R9 | EVIDENCE sim; it is the I doing its job |
| M-E2-4 | steady-state with a large constant road load at θ ≈ 0 (crown, crosswind) | any speed | the bound caps the I at 200 T + slope·\|θ\|; P carries any excess with a steady error = excess / Kp_T (e.g. 100 T at 22 m/s → 1.3°). **Never seen on r71b** (§2.3: every steady hold ≥ 43 T under the bound) | a steady hands-off error > 1° on a straight at ≥ 12.5 m/s (H-E2 on-car revert) | EVIDENCE r71b; BELIEF for other roads |
| M-E2-5 | the resting-hand word | all | S/A2S freeze 3.9 % of normal frames on the replay (goal metric −0.006…−0.008) | — (inside the metric's bar) | EVIDENCE replay; BELIEF transfer (the replay is V294's word on V294's motion) |
| M-E2-6 | GATE 2 under the D-operand frame | 1–3.5 m/s (J_hi), 1 m/s (b_lo×J_hi+h10) | inherited from P2: tier A 43.2°, tier B 28.3° (FA reading) | another axis's fix; the policy block carries over unchanged | EVIDENCE (`e2_freq_out.txt`) |
| M-E2-7 | engage droop | ≤ 10 m/s | 6.1° b_lo×J_hi at 8 m/s (stock ramp-in); **4.2° with (iv)** | — | EVIDENCE sim |
| M-E2-8 (X only) | override force | 600–3240 raw hands | the `0xCBAE4` fade arm leaves up to ×2.1 more lane torque against the hand (×1.8 at 2400 raw) | R9 ("heavier in my hands") | EVIDENCE cal LERP |

---

## 8. The instrument: what one short drive must show (no new telemetry bit)

The I is not on the wire; it is identified **within an episode** from signals already there (rev2-A §7.1's regression:
`tap = c_P·(raw − 10θ) + c_I·Σ(raw − 10θ)·dt + c_D·ω + c0`, 0x14A θ, 0x18F torque word and rate, the 427 tap). The
policies act only with a hand on the wheel, so the drive must contain **one deliberate episode**, ~15 s:

> At 10–15 m/s in a steady curve the fork is holding, rest one hand on the wheel and hold it lightly about 2–4° toward
> straight for 3 s (keep the 0x18F word under ~500), then let go.

| reading | E2-A / A2 predicted | P2 / R1 predicted | decides |
|---|---|---|---|
| I component (tap − c_P·e − c_D·ω, 1 Hz LP) during the 3 s hold | flat within ~200 T of its pre-hold value | ramps toward ICL (668 / 1336 T) until the word reaches 512 | **LIVE: the bound** |
| overshoot past θ_sp after release (0x14A) | ≤ 3° (T3, the curve's speed) | 7–25° by the same table | the lurch claim |
| the same with the word > 300 opposing (S/A2S only) | I flat from the first frame | ramps | **LIVE: the opposing freeze** |
| the 427 tap at an engage edge (A2-X with 6803 = 2) | reaches its level in ~0.10 s; droop per the T4 0.10 s row | ~0.99 s ramp; the 0.99 s row | **LIVE: the arm** (and the fork's own 0xE4 byte 2 carries bits 3:2 = 2 on the wire) |

The sentence a null licenses: *"if the I component ramps during a light hold, the bound is not live; if it is flat but
the release still overshoots by more than T3 + 2°, the plant is outside the credible set — revert either way."*

---

## 9. What a FAIL looks like (written before any build)

- **H-E2-1** any H1 / CONTROL C mismatch on the BUILT image's cave; any register outside {r6, r8, r9, r13, r16, r26}
  written; r25 written (the camera gate READS it); any RAM written.
- **H-E2-2** GATE 2 on the built table and cals below P2's own numbers (P2: 0 fails; P2-I0: 0 fails).
- **H-E2-3** turn-hold < 0.90 on any member at any speed ≥ 8 m/s for a ≤ 2.5 (r71b-sized), or the r71b goal metric
  < 0.95 in any band with the torque word replayed.
- **H-E2-4** any r71b steady hold whose tap exceeds the built bound (re-run `e2_data_hold.py` on the built constants).
- **On the car: REVERT** on release overshoot > 8° after any hand episode at ≥ 8 m/s; a steady error > 1° in a held
  curve at ≥ 12.5 m/s hands-off (the bound binding where it must not); plus rev2-A's R1–R9 unchanged.

---

## 10. Files (all reproducible with `python`, the bin_decompile env; caches in `_scratch/angle_loop/E2-integral-most-margin/`)

| file | what it does | output |
|---|---|---|
| `e2_common.py` | loads THE common time scorer `c2/rev2A/score_time.py` by path (a different `panel/score_time.py` shadows the name) | — |
| `e2_lane.py` | E2Lane: DSLane with the integral policy as switches; CONTROL E2-0 | `e2_lane_selftest.txt` |
| `e2_exp.py` | the added scenarios (turn-hold sized, r71b goal metric ± torque replay, hand family, engage, firm hand) and metrics | — |
| `e2_explore.py` | round 1: 14 policy columns (exploration only: its ARB columns ran an earlier, I8-domain form of the bound; every ARB number on this page is from `e2_final.py` / `e2_a3.py`; §3.1 and the S200/LS duties are the only exploration figures quoted) | `e2_explore_{th,rr,lurch,eng}.txt` |
| `e2_final.py` | the scored run: `ext` (T1–T4) and `suite` (T5, the scorer's own list) | `exp_final_ext.json`, `final_suite.json` |
| `e2_report.py` | every table on this page | `e2_report_out.md` |
| `e2_asm.py` | listings → bytes, controls A/B, H1 | `e2_asm_out.txt`, `e2_cave_<id>.hex` |
| `e2_ctlC.py` | CONTROL C (lane decision == cave_ref) | `e2_ctlC_out.txt` |
| `e2_a3.py` (`lo`) | the A3 refinement on the hand family / low-speed turn-hold, and the scorer's own low-speed scenarios | `e2_a3_out.txt`, `e2_a3_lo_out.txt` |
| `e2_arb_slope.py` | the bound slope a normal turn needs, per member and speed; the fade-arm values | `e2_arb_slope_out.txt` |
| `e2_freq.py` | GATE 2 on the common frequency scorer | `e2_freq_out.txt` |
| `e2_k0.py` | policy (iii) with a fork integral | `e2_k0_out.txt` |
| `e2_data_r71b.py`, `e2_data_hold.py` | §2's data facts | `e2_data_r71b_out.txt`, `e2_data_hold_out.txt` |
| `e2_scan_6803.py`, `e2_scan_callers.py`, `e2_form_hits.py` | §4's scans and the encoding-form hits | `*_out.txt` |

**Edit to a shared file (declared):** `c2/rev2A/score_time.py` `run()` gained three additive hooks — `lane_cls` (a DSLane
subclass), `scn['ramp_in']` (engage ramp increment, default 33) and `scn['tq_cols']` (a per-column sensor model). Every
default reproduces the original; its CONTROL 1–3 were re-run after the edit and still read max|ΔT| 0.
