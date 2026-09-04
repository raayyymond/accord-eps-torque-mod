# PID frame sizing — Kp vs Kd of `FUN_00028ea6`, in the rate, angle and acceleration frames

Subagent `pidframe`, 2026-09-04, reporting to `team-lead`/`main`. Answers the operator's question
verbatim: *"Why Kp? Kp is effectively Kd for our torque. How does our Kd (angle rate) compare to Kp
(angle rate)? Is it sized appropriately for PID on angle acceleration (Kp > Kd on angular
acceleration)?"*

**Image traced [EVIDENCE]:**
`C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
sha256 `fd0c321abbf933c0d846a8eaf48b594f44f5a9bd491e4396b44abc562551ef3d`, 1,048,576 bytes — hashed
directly. Every constant in this document is a **raw little-endian Python byte read of that file**;
none is quoted from the kit's model or from a build script. Structure came from GhidraMCP
`decompile_function`/`disassemble_bytes` on the V282 project (V282→V283 differ by 5 bytes: `0xC63E6`
Ki 0→50 and its CRC at `0xC6FFC`), decompile-first then assembly, per the standing instruction.
`gp = 0xFEDF8000`, `tp = 0xBF000`.

Runnable mirror: `analysis-2020accord/studies/pidframe/pid_frame_sizing.py` (reads the image itself;
every number below is its stdout).

⚠ **Address-arithmetic note.** Ghidra renders a tp-relative load as `ld.hu 0x71bc, tp, rX`. The cal is
`0xBF000 + 0x71BC = 0xC61BC` — **`0xC6…`, never `0xC7…`**. I made the off-by-0x1000 error once during
this trace (read the output-lag pair as `0xC73EC/EE` and got 45246/14) and caught it against the known
992/507; recording it because the skill says it has now recurred six times.

---

## 1. THE TICK RATE — pinned, and it is 1 kHz [EVIDENCE]

This is the crux; every frequency number depends on it. It is pinned, and unlike the r24 lane it is
**not** DMA-paced.

1. **`FUN_00028ea6` has exactly one caller: `FUN_0002214a`** (`get_function_callers`, and the call
   site is `jarl 0x00028ea6, lp` at **`0x22522`** — the positive control the decompile skill names).
2. **`FUN_0002214a` is the 1 kHz control task**, confirmed two independent ways in
   [[control-task-tick-confirmed-1khz]] (`memory/misc/control-task-tick-confirmed-1khz.md`):
   `OSTM0CMP = 79999` auto-reload / 80 MHz PCLK = 1000 Hz, **and** the `STEER_STATUS=4` dwell cal
   `0xC64DF = 100` cycles measured on the bus at 100.00 ms. Neither route depends on the retracted
   `syscall8` derivation.
3. **The call is not decimated.** Re-read fresh this session:

   ```
   000221bc  ld.bu -0x67fa[gp],r6     ; r6 = the EPS main state variable
   000221c2  andi  0xf,r6,r8
   000221c6  shl   r8,r15,r25         ; r25 = 1 << state   (a ONE-HOT of the state, not a counter)
   ...
   00022518  andi  0x930,r25,r27      ; states {4,5,8,11}
   0002251c  be    0x00022526         ; skip the PID if the state is not one of those
   00022522  jarl  0x00028ea6,lp      ; <-- the LKAS rate PID
   ```
   `r25` is a one-hot of `gp-0x67fa` (the EPS state machine, 0–15). **There is no modulo, no phase
   counter, no rate divider anywhere between the task entry and the call.** For contrast, the task-5
   divider `FUN_00014be4` uses an explicit `gp-0x4304` mod-100 counter — nothing of that shape exists
   here. And at `0x22182` the same function does `st.h r7,-0x3e54[gp]`, incrementing the canonical
   elapsed-tick counter once per call.
4. **The `dE` state is updated on every call, on both branches.** `*(int *)(gp-0x6cf8) = E` sits in the
   function tail, after the if/else rejoins; the fault/disengaged branch stores the sentinel
   `0x7FFFFFFF`, which the range test `0x177000 < eprev + 0xBB800` then converts into `dE = 0` on the
   next entry. So `dE` is a **true one-tick difference**, and the first engaged tick after any gap has
   `D = 0` by construction.

⇒ **`dt` for the D term = 1.000 ms.** [EVIDENCE]

⭐ And it is confirmed a third time, *from the car*, in §6: at 100 Hz the D term would be railed against
its ±10240 clamp on the measured V283 strong-turn frames; it is not.

---

## 2. The arithmetic, mirrored exactly, with instruction addresses [EVIDENCE]

Integer `>>` throughout (Python `>>` on a negative int is an arithmetic shift, same as V850 `sar`).
Constants byte-read little-endian. Full runnable version in
`analysis-2020accord/studies/pidframe/pid_frame_sizing.py`.

```python
# ---- error -------------------------------------------------------------------------------------
# 0x29D6C  mulh  r13,r16              sp = sign * LERP(mapY, idx)
# 0x29D72  st.h  r16,-0x6a32[gp]      publish the setpoint
# 0x29D76  shl   0x5,r16              sp <<= 5
# 0x29D78  sub   r26,r16              E = 32*sp - fb        (r26 = fb, two-sample-summed at 0x28FA4)
E = sp * 32 - fb

# ---- I term ------------------------------------------------------------------------------------
# 0x29D7C  sar   0x5,r6               Ei = E >> 5
Ei = E >> 5
# 0x29D7E..0x29D9A                    deadband +-cal(0xC62E4)=4      (i.e. +-128 in E units)
dbE = Ei - 4 if Ei > 4 else (Ei + 4 if Ei < -4 else 0)
# 0x29DAC shl 0xa,r13 ; 0x29DAE sar 0x3,r13     lim  = (cal(0xC61BA) << 10) >> 3 = 10240*128 = 1310720
lim  = (10240 << 10) >> 3
# 0x29DA8 mul r6,r9   ; 0x29DB2 sar 0x3,r9      inc  = (dbE * cal(0xC63E6)) >> 3     Ki = 50 on V283
inc  = (dbE * 50) >> 3
# 0x29DB0 sar 0x3,r10                           iacc = iacc8 >> 3   (gp-0x6dd0 stores iacc * 8)
iacc = (iacc8 >> 3) + inc                     # 0x29DB4 add r9,r10
# 0x29DB6..0x29DC2 cmovgt/cmovle                clamp iacc to +-lim
iacc = lim if iacc > lim else (-lim if iacc < -lim else iacc)
# 0x29F18 sar 0x7,r2                            Iterm = iacc >> 7   (ceiling therefore 10240 counts)
Iterm = iacc >> 7

# ---- P term ------------------------------------------------------------------------------------
Kp = LERP(0xE5378, idx)               # 0x29DC6 mov 0xcb994,r10 ; slot 7 -> 0xE5378 ; divq @0x29E2C
# 0x29E36 mul r9,r8 ; 0x29E3E sar 0x8,r8        P = (E * Kp) >> 8
P = (E * Kp) >> 8
P = clamp(P, +-cal(0xC61BC))          # 0x29E42 ld.hu 0x71bc,tp    = 15360

# ---- D term ------------------------------------------------------------------------------------
Kd = LERP(0xE511C, idx)               # 0xCB7D4 + 4*7 -> 0xE511C ; FLAT 128, four knots
# 0x29EE0 mov r16,r8 ; 0x29EE2 sub r27,r8       dE = E - E_prev   (E_prev = gp-0x6cf8, or E if sentinel)
dE = E - E_prev
# 0x29EE4 mul r7,r8 ; 0x29EEC sar 0x3,r8        D = (dE * Kd) >> 3
D = (dE * Kd) >> 3
D = clamp(D, +-cal(0xC61B6))          # 0x29EE8 ld.hu 0x71b6,tp    = 10240

# ---- sum, override taper, clamp ----------------------------------------------------------------
# 0x29F1E add r9,r2 (+D)                        S = Iterm + P + D
S = Iterm + P + D
# 0x2A0A0 mul ; 0x2A0BC sar 0x8 ; 0x2A0BE mul ; 0x2A0C2 sar 0x8
#   taperK = (tapA*tapB & 0xffff) >> 8   = 254 when neither driver-override taper has bitten
S = (254 * S) >> 8
S = clamp(S, +-cal(0xC61BE))          # = 15360

# ---- output lag  (a = cal(0xC63EC) = 992, b = cal(0xC63EE) = 507) ------------------------------
# 0x2A180 mul / 0x2A1A0 sar 0xa ; 0x2A194 mul / 0x2A1A6 sar 0xa ; 0x2A1AC sar 0x5
s_new = ((992 * lag_s) >> 10) + ((S * 507) >> 10)
out   = (lag_s + s_new) >> 5          # two-sample sum, DC gain 0.9902
lag_s = s_new

# ---- engagement ramp, forward gain, output clamp -----------------------------------------------
# 0x2A1E6 mul r14,r9 ; 0x2A1EA sar 0xf,r9       out = (out * gp-0x69b0) >> 15
# 0x2A1FE mul r13,r11; 0x2A202 sar 0xf,r11      T   = (out * gp-0x6752 * cal(0xC6CD0)) >> 15
T = (out * (-1) * 5346) >> 15
T = clamp(T, +-cal(0xC61B4))          # = 3072   -> gp-0x6b38 -> gp-0x6b3c
```

**Feedback, for completeness** (`0x28F8E`/`0x28F92` mul, `0x28F9A`/`0x28FA0` `sar 0xa`, `add r9,r26`
@`0x28FA4`): `y[n] = (923·y[n-1] + 1560·x[n]) >> 10`, `fb = y[n] + y[n-1]`, DC gain **30.891**.

### 2.1 The cals, byte-read from the V283 image [EVIDENCE]

| cell | value | what it is |
|---|---|---|
| `0xC63E6` | **50** | Ki (0 on V282 and every build before V283) |
| `0xC61BA` | 10240 | anti-windup base ⇒ `iacc` limit 1,310,720 ⇒ **I-term ceiling 10240 counts** |
| `0xC62E4` | 4 | integrator error deadband, applied to `E>>5` ⇒ ±128 in E units |
| `0xC61BC` | 15360 | P clamp |
| `0xC61B6` | 10240 | D clamp |
| `0xC61BE` | 15360 | sum clamp |
| `0xC61B4` | 3072 | output clamp |
| `0xC6CD0` | 5346 | forward gain (6.00× of `0xC646C`'s 891) |
| `0xC63EC` / `0xC63EE` | 992 / 507 | output-lag pole / zero ⇒ **pole at 5.05 Hz**, DC gain 0.9902 |
| `0xC63E8` / `0xC63EA` | 923 / 1560 | feedback EMA ⇒ **corner 15.7 Hz**, DC gain 30.891 |
| `0xE5378` (slot 7) | n=5, X `[0,68,112,136,208]`, Y `[248,248,248,248,248]` | **Kp — flat 248** |
| `0xE511C` (slot 7) | n=4, X `[0,11,22,32]`, Y `[128,128,128,128]` | **Kd — flat 128** |

The Kp and Kd LERPs are indexed by the **same** variable: `uVar30 = uVar33 = idx`, written to
`gp-0x674b` at the decompile's line 953 and to `gp-0x697a` at line 1014. [EVIDENCE]

---

## 3. Sizing in the RATE frame (the loop as built)

Continuous-time equivalents at T = 1 ms, `S = Ki_r·∫E + Kp_r·E + Kd_r·dE/dt`:

| | gain | from |
|---|---|---|
| `Kp_r` | **0.968750** | `Kp/256`, Kp = 248 |
| `Kd_r` | **0.016000 s** | `(Kd/8)·T`, Kd = 128 |
| `Ki_r` | **1.525879 /s** | `(Ki/8)/32/128/T`, Ki = 50 |

Corners: **`Kp_r/Kd_r` = 60.55 rad/s = 9.636 Hz** (D overtakes P); **`Ki_r/Kp_r` = 1.575 rad/s =
0.251 Hz** (I overtakes P).

### |D| / |P| per unit E — exact discrete, `2·(Kd/8)·sin(πfT) / (Kp/256)`

| Kp | 0.5 Hz | 1 Hz | 2 Hz | **7.3 Hz** | 13 Hz | **20 Hz** | 40 Hz |
|---|---|---|---|---|---|---|---|
| **248 flat** (V281r3/V282/V283) | 0.052 | 0.104 | 0.208 | **0.757** | 1.349 | **2.074** | 4.140 |
| 341 (V281 rev 2, unflown) | 0.038 | 0.075 | 0.151 | 0.551 | 0.981 | 1.508 | 3.011 |
| 512 (M8* peak, idx 36–44) | 0.025 | 0.050 | 0.101 | 0.367 | 0.653 | 1.005 | 2.005 |
| 696 (stock LERP top) | 0.018 | 0.037 | 0.074 | 0.270 | 0.481 | 0.739 | 1.475 |

**D overtakes P at:** Kp 248 → **9.64 Hz** · 341 → 13.25 Hz · 512 → **19.91 Hz** · 645 → 25.09 Hz ·
696 → 27.08 Hz. Under the stock LERP the corner is a function of demand index: 9.64 Hz at idx 0,
19.91 Hz at idx 68, 27.08 Hz at idx ≥ 208.

**I overtakes P at 0.2507 Hz** — the I term is essentially a DC/quasi-DC bias; see §6.

*(If T were 10 ms the corner would be 0.96 Hz and `|D|/|P|` at 20 Hz would be 19.4. That case is
excluded in §1 and again in §6.)*

---

## 4. The operator's frames — the direct answer

The three terms, re-labelled by what they act on. Nothing changes in the firmware; only the name of
the controlled variable changes.

| firmware term | RATE frame (as built) | **ANGLE frame** | **ACCELERATION frame** |
|---|---|---|---|
| I (`Ki` 50) | integral, 1.5259 /s | **PROPORTIONAL**, `Kp_θ` = 1.5259 | double integral |
| P (`Kp` 248) | proportional, 0.96875 | **DERIVATIVE**, `Kd_θ` = 0.96875 s | **INTEGRAL**, `Ki_a` = 0.96875 |
| D (`Kd` 128) | derivative, 0.016 s | **2nd DERIVATIVE**, `Kdd_θ` = 0.016 s² | **PROPORTIONAL**, `Kp_a` = 0.016 s |
| — | — | — | **DERIVATIVE: does not exist. `Kd_a` = 0.** |

**The operator's premise is correct, and the numbers are larger than "derivative-heavy" suggests.**
In the angle frame, `Kd_θ/Kp_θ` = 0.6349 s, so **derivative-on-angle overtakes proportional-on-angle at
0.2507 Hz** — below anything the car does. Above that:

| f | D-on-angle / P-on-angle | 2nd-derivative / derivative |
|---|---|---|
| 0.5 Hz | 1.99× | 0.052 |
| 2 Hz | 7.98× | 0.208 |
| **7.3 Hz** (strong-turn ring) | **29.1×** | 0.757 |
| 13 Hz | 51.8× | 1.349 |
| **20 Hz** (creep grind) | **79.7×** | 2.074 |
| 40 Hz | 159× | 4.140 |

**In the acceleration frame there is no derivative term at all.** The loop is a **PI on acceleration**
whose corner is `Ki_a/Kp_a` = 60.55 rad/s = **9.636 Hz** — the *same* number as "D overtakes P",
because they are the same statement said twice.

So the literal question — *is Kp > Kd on angular acceleration?* — has the answer: **yes, trivially,
because Kd on acceleration is zero.** The comparison that actually exists in that frame is
proportional vs integral, and it says the loop is **integral-dominated below 9.64 Hz and
proportional-dominated above it**. The car's two live symptoms sit on opposite sides of that single
corner: the 7.3 Hz strong-turn ring is in the **integral-dominated** half, the 20 Hz creep grind in
the **proportional-dominated** half. That is why one lever has never moved both. [EVIDENCE for the
arithmetic; BELIEF for the causal reading of the two symptoms.]

---

## 5. What the D term is actually FOR — it cancels the output-lag pole [EVIDENCE]

Sizing the terms against each other is not the whole story, because the forward path has a first-order
lag right after the sum: `0xC63EC` = 992 ⇒ a pole at **5.05 Hz**. Multiply controller × lag and the
picture inverts.

**Forward path `|C(f)·H_lag(f)|` and its phase** (Kp = 248, Ki = 50):

| f (Hz) | Kd = 0 | Kd = 64 | **Kd = 128 (live)** | Kd = 256 |
|---|---|---|---|---|
| 1 | 0.971 / −25.3° | 0.960 / −22.4° | **0.952 / −19.5°** | 0.943 / −13.7° |
| 5 | 0.683 / −47.6° | 0.700 / −32.9° | **0.759 / −19.8°** | 0.967 / −0.6° |
| 7.3 | 0.547 / −57.3° | 0.582 / −36.5° | **0.682 / −19.9°** | 0.986 / −0.3° |
| 13 | 0.348 / −69.9° | 0.423 / −36.3° | **0.589 / −17.3°** | 1.006 / −1.3° |
| 20 | 0.235 / −76.6° | 0.347 / −32.0° | **0.551 / −14.6°** | 1.013 / −2.8° |
| 40 | 0.120 / −83.2° | 0.288 / −24.5° | **0.523 / −13.2°** | 1.012 / −6.8° |

The zero at 9.64 Hz sits about one octave above the pole at 5.05 Hz. **Kd = 128 is a lead
compensator sized to hold the forward path's phase between −13° and −20° across the whole 5–40 Hz
band**, at the price of holding its magnitude near 0.55 instead of letting it roll off to 0.12.
Kd = 256 would cancel the pole almost exactly (phase within 7° of zero everywhere).

⇒ **The loop is not "derivative-heavy" in delivered torque per unit error — it is deliberately
FLAT.** What the D term buys is phase; what it costs is that the loop gain never rolls off inside the
electronics. The roll-off that does exist is in the **feedback** path: the EMA at `0xC63E8/0xC63EA`
has a 15.7 Hz corner and contributes −38° at 13 Hz and **−50.5° at 20 Hz**. That is where the phase
margin is spent, and the record's independently-measured "inner loop PM ~50° at 13–15 Hz" lands
exactly there.

**Electronics loop shape, normalised to DC** (controller × lag × feedback, Ki excluded so the DC
reference is finite):

| f (Hz) | Kd = 0 | **Kd = 128 (live)** | Kd = 128, Kp = 512 |
|---|---|---|---|
| 5 | 0.680 | **0.771** | 0.704 |
| 7.3 | 0.520 | **0.660** | 0.559 |
| 13 | 0.284 | **0.487** | 0.346 |
| 20 | 0.156 | **0.367** | 0.227 |
| 40 | 0.047 | **0.207** | 0.111 |

---

## 6. Cross-check against the measurement — and a third proof of the tick rate [EVIDENCE]

Measured on V283 r36–r38 strong-turn frames (`STUTTER-7HZ-V283-r36-r38-2026-09-03.md`): `|P|` p50
≈ 1900, `|D|` 880–1552, `|I|` 3377–7004 counts.

- `|P| = (248/256)·|E|` ⇒ **`|E|` ≈ 1961 counts**.
- At **1 kHz**, a 7.3 Hz E of that amplitude predicts **`|D|` = 1439 counts**. Measured 880–1552.
  ✅ **The prediction lands inside the measured range, near its centre.**
- At **100 Hz** the same E predicts `|D|` = 14,268 — **above the ±10240 D clamp**, so D would sit
  railed on every strong-turn frame. It does not. ⇒ **100 Hz is excluded by the car's own data.**
- Inverting the measured ratio: `|D|/|P|` = 0.46–0.82 at T = 1 ms ⇒ **f = 4.5–7.9 Hz**, i.e. the D/P
  ratio independently recovers the 7.3 Hz strong-turn line without being told about it.
- A direct integer run of the mirror (2 s of a 7.3 Hz ripple, `|fb|` = 1961) gives peak `|P|` = 1899,
  peak `|D|` = 1440, D/P = 0.758 against the predicted 0.757.

**The I term does NOT participate in the 7 Hz dynamics.** At 7.3 Hz the AC part of I would be **65
counts**; measured is 3377–7004, i.e. **52–107× larger**. That size is only reachable by accumulation
against a *sustained one-sided* error: `dbE = 1961/32 − 4 = 57.3`, ramping `iacc` at 358/tick, so
`|I|` = 7004 needs 2504 ticks = **2.50 s** of one-signed error — a stall run, not an oscillation.
The anti-windup ceiling on the I term is 10240 counts, so 7004 is 68 % of the way to the rail.

⇒ **On V283, `I` is a slowly-built DC bias, `P` and `D` are the dynamics.** [EVIDENCE]

---

## 7. Consequence for the two builds on the table

### (a) M8* — Kp 248 → 512 over idx 32–88

M8* raises the **rate-frame proportional** term, which in the operator's angle frame is raising the
**derivative-on-angle** action, and in his acceleration frame is raising the **integral** action.

| idx | Kp flat | corner | Kp M8* | corner | Kp stock | corner |
|---|---|---|---|---|---|---|
| 0–32 | 248 | 9.64 Hz | 248 | 9.64 Hz | 248–372 | 9.6–14.5 Hz |
| 36–44 | 248 | 9.64 Hz | **512** | **19.91 Hz** | 387–418 | 15.0–16.3 Hz |
| 56 | 248 | 9.64 Hz | 440 | 17.10 Hz | 465 | 18.1 Hz |
| 68 | 248 | 9.64 Hz | 368 | 14.30 Hz | 512 | 19.91 Hz |
| ≥ 88 | 248 | 9.64 Hz | 248 | 9.64 Hz | 572–696 | 22.2–27.1 Hz |

What that does, in absolute loop gain (controller magnitude, Ki = 50):

| f | Kp = 248 | Kp = 512 | change |
|---|---|---|---|
| 2 Hz | 0.974 ∠+4.7° | 2.004 ∠+2.3° | **×2.06** |
| 7.3 Hz | 1.210 ∠+35.4° | 2.136 ∠+19.1° | **×1.77** |
| 20 Hz | 2.274 ∠+61.2° | 2.915 ∠+43.1° | **×1.28** |

⇒ **M8* raises loop gain everywhere, most at low frequency and least at high.** Relative to DC it
makes the loop *less* HF-heavy (the 20 Hz normalised shape falls 0.367 → 0.227); in absolute terms it
still adds **+28 % of loop gain at 20 Hz** and **+77 % at 7.3 Hz**, inside the index band 32–88 where
both symptoms live. It also removes 18° of phase lead at 20 Hz (the P term is phase-flat, so adding it
dilutes the D term's lead).

**Predicted, and it should be pre-registered before the drive [BELIEF, from the loop-gain arithmetic
above]:**
- the 20 Hz creep grind, a crossover resonance whose presence the record says *follows Kp(idx)*, gets
  **modestly worse in the 32–88 band** — not better — because absolute 20 Hz loop gain rises 28 %;
- the 7.3 Hz stutter gets **1.77× more P per unit error**, which is the intended mechanism (break the
  stall by gain instead of by accumulation) but is also 1.77× more drive into a limit cycle if the
  stall does not break;
- idx 0–32 is untouched, so ~18 % of engaged time sees no change at all.

This is not an argument against flying M8*; it is the sentence a null will license, written before the
drive. If the grind gets worse only inside idx 32–88 and is unchanged below 32, that is M8* acting and
not noise.

### (b) Moving Kd (`0xE511C`)

**Lineage [EVIDENCE, byte-read across 287 images — 286 builds plus stock]:**

- `0xE511C` slot 7 is `[128,128,128,128]` in **284 of 286 builds and in stock**.
- The only two exceptions are **V279 rev 1 and V279** (`PURE.FEEDFORWARD.FB0.KD0`), which set it to
  `[0,0,0,0]` — but as part of a three-way change that *also* zeroed the feedback and flattened Kp to
  256, i.e. the loop was opened. **`docs/BUILD-LINEAGE.md` records V279 as UNFLOWN.**
- In every build script that names it (`build_v281_tva.py`, `v281r3`, `v282`, `v283`, `v284`) it
  appears only as `LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128,128,128,128)` — an **assertion that it has
  not moved**, never an edit.

⇒ **Kd has never been moved as an isolated lever, and has never flown at any value but 128.** The same
byte-read shows `0xC63E8/EA` (feedback EMA), `0xC63EC/EE` (output lag), `0xC62E4`, `0xC61BA`,
`0xC61B6`, `0xC61BC`, `0xC61BE` are **identical in all 287 images** — none of them has ever moved either.

**Testing the record's warning against my own sizing.** The record says *less D moves the ring to
~8 Hz rather than removing it*, and *the 20 Hz grind is D-dominated (D ~55 %) so cutting D makes the
grind worse.* Both survive, and the second needs a qualification:

| Kd | corner | \|C\| @7.3 Hz | phase | \|C\| @20 Hz | phase |
|---|---|---|---|---|---|
| 0 | — | 0.970 | −2.0° | 0.970 | −0.7° |
| 64 | 19.28 Hz | 1.033 | +18.8° | 1.431 | +43.8° |
| **128 (live)** | **9.64 Hz** | **1.210** | **+35.4°** | **2.274** | **+61.2°** |
| 256 | 4.82 Hz | 1.750 | +55.0° | 4.181 | +73.0° |

Halving Kd to 64 cuts 20 Hz loop gain by **4.0 dB** but only 1.4 dB at 7.3 Hz, **and removes 17° of
phase lead at 7.3 Hz**. So it lowers the gain where the grind crosses over and simultaneously reduces
the damping where the ring already lives. That is exactly the shape that **moves the trouble down to
~8 Hz instead of removing it** — the record's warning reproduces from the bytes. [EVIDENCE for the
transfer functions; the identification of "trouble" with the operator's symptoms is BELIEF.]

The qualification: the D fraction at 20 Hz is `2.074/(1+2.074)` = **67 %** by this arithmetic, against
the record's measured ~55 %. The difference is the direction that matters — the measured share is
*lower* than the open-form prediction, consistent with the D clamp and the feedback EMA both biting —
so "D-dominated at 20 Hz" is if anything understated, not overstated.

### (c) The honest answer: neither candidate fixes the shape

Both M8* and a Kd move are **gain** edits. The frequency at which this loop's phase margin is actually
spent is set by two poles neither of them touches:

1. the **feedback EMA**, `0xC63E8 = 923` → 15.7 Hz corner, −38° at 13 Hz, **−50.5° at 20 Hz**;
2. the **output lag**, `0xC63EC = 992` → 5.05 Hz corner, −55° at 7.3 Hz, −76° at 20 Hz, which the D
   term is already spending its whole budget cancelling.

The controller is a lead network sized to hold the forward path flat and near-zero phase from 5 to
40 Hz. The consequence is that **the loop has no roll-off of its own anywhere the plant is still
resonant** — the only thing that finally ends the loop gain is the 15.7 Hz feedback pole, and it ends
it with 50° of lag at exactly the frequency the grind sits at. Moving Kp slides the whole controller
up or down; moving Kd trades the 20 Hz gain against the 7.3 Hz phase. **No setting of the two makes
the loop roll off before its own phase runs out** — that is the mis-shaping, and it is structural.

The cells that would change the *shape* rather than the *level*:

- **`0xC63E8/0xC63EA` (feedback EMA, 923/1560)** — a faster pole would return phase at 13–20 Hz at the
  cost of feeding more sensor noise into E, which the raw first-difference D term then multiplies by
  16. ⚠ This is the highest-leverage cell in the loop **and the most dangerous**, because D has no
  filter of its own; it needs GATE 2 in both magnitude and phase before anyone builds it.
- **`0xC63EC` (output lag, 992)** — already on the record's ranked list as "lag pole 5→15 Hz". Raising
  the pole frequency removes the lag the D term exists to cancel, which would then make a Kd *cut*
  benign rather than destabilising. **That pairing — lag pole up AND Kd down — is the only
  combination in these tables that lowers 20 Hz loop gain without stripping 7.3 Hz phase**, and
  neither cell has ever been moved in 286 builds.
- **The absent one:** there is no derivative filter. `D = (dE·Kd)>>3` is an ideal differentiator to
  Nyquist, bounded only by the ±10240 clamp and by whatever the feedback EMA happens to remove. A
  textbook loop would have `Kd·s/(1+s/ωN)`; this one does not, and there is no cal that adds one.

⚠ **None of this is a build recommendation.** Every cell named in this section is untouched in 286
builds, sits in the closed loop, and would need GATE 1 and GATE 2 before it is a candidate. I am
naming them because the operator asked whether the loop is mis-shaped, and the answer is that it is —
in a way that is one layer beneath both builds currently on the table.

---

## What would falsify this document

- **The tick rate.** If `FUN_0002214a` were shown to be reached at other than 1 kHz, every frequency
  here scales. §1 pins it three ways (call-site with no divider · two independent 1 kHz derivations for
  the task · the D clamp not being railed on the car), so this is the claim I am most confident in.
- **The `254` taper factor.** I assumed both selected override tapers read 255 (no driver override).
  With a driver override biting, the whole sum is scaled, but the *ratios* in §3–§5 are untouched
  because the taper multiplies P, D and I identically.
- **The plant.** Every table here is the **electronics only** — controller, lag, feedback. No plant
  model is included, so nothing here predicts a crossover frequency by itself; it predicts *changes*
  to loop gain and phase at fixed frequencies, which is what the build decision needs.
