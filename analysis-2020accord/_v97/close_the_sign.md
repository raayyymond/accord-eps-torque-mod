# Closing the sign — BLOCKER 1 (`L`) and BLOCKER 2 (`f'`)

Author: `close-the-sign` agent, 2026-08-12. Study/analysis only.
Tooling: GhidraMCP on `code.bin` (stock, `function_count = 2086`) + Python LE byte reads.
Scripts: `read_L_coeffs.py`, `read_ram_lerp_provenance.py` (both mine).

**Both blockers are CLOSED. A third, previously unstated one is now the whole residual, and it is
exactly ONE BIT.**

---

## 0. Verdict in one paragraph

`L` is not eight floats — it is three floats and six unsigned halfword Q-format cals, and the only
float block is a 3-tap FIR with taps `(1.0, 0.0, 0.0)`, i.e. **an identity: gain 1, phase 0** at
every frequency. `f'` is **strictly positive**, not by luck but because Honda enforces
monotone-nondecreasing `Y` at three separate code sites, unconditionally — and the flash data
agrees in 14/14 records. With those two closed, the open-loop sign of every one of the six Path-2
lane weights collapses to a closed form whose only free factor is
`sign(gp-0x6752) x sign(lane_i)`. `gp-0x6752` is a **±1 vehicle-configuration constant** (never 0,
never chatters) that **cannot be read from the image**. That is the residual: one bit, on a cell
that is trivially observable on-car. **I cannot close it from the binary, and I will not guess it.**

---

## 1. BLOCKER 1 — `L`

### 1.1 The types, read from the loading instructions (`disassemble_function 0x3b8f6`)

| addr | tp+ | opcode @ | type | stock | on car | role |
|---|---|---|---|---|---|---|
| `0xC4048` | 0x5048 | `ld.w` @`0x3b9d2` | **float** | 1.0f | 1.0f | FIR tap b0 |
| `0xC404C` | 0x504C | `ld.w` @`0x3b9de` | **float** | 0.0f | 0.0f | FIR tap b1 |
| `0xC4050` | 0x5050 | `ld.w` @`0x3b9ee` | **float** | 0.0f | 0.0f | FIR tap b2 |
| `0xC40BC` | 0x50BC | `ld.hu` @`0x3bab4` | u16 | 600 | 600 | Coulomb relay divisor |
| `0xC40D0` | 0x50D0 | `ld.hu` @`0x3bb22` | u16 | 408 | 408 | IIR alpha 408/4096 = 0.09961 |
| `0xC40D2` | 0x50D2 | `ld.hu` @`0x3bafe` | u16 | 102 | **204** | K1, Q10 (V89) |
| `0xC40D4` | 0x50D4 | `ld.hu` @`0x3b94e`,`0x3b96a` | u16 | 573 | 573 | IIR alpha 0.13989, **x2 cascade** |
| `0xC40D6` | 0x50D6 | `ld.hu` @`0x3bb60`,`0x3bb8a` | u16 | 246 | 246 | IIR alpha 0.06006, **x2 cascade** |
| `0xC40D8` | 0x50D8 | `ld.hu` @`0x3b98e`,`0x3b9a2` | u16 | 3686 | 3686 | IIR alpha 0.89990, **x2 cascade** |
| `0xC4080` | 0x5080 | `ld.hu` @`0x3baf6` | u16 | 0 | 0 | constant-Coulomb term — **zero, so dead** |

Every `ld.hu` is followed by `cvtf.uws`; the `ld.w`s feed `mulf.s`/`maddf.s` with no `cvtf`.
**Type inferred from the opcode, never from the value.** `0xC4048` was missing from the handover
list.

Consistency anchors, all three pass: `0xC40BC` = 600 (known relay gate), `0xC40D2` = 102→204
(known V89 K1, and `x cal x 0.0009765625` confirms Q10 ⇒ 0.0996 → 0.1992 = the "2x" of record),
and `ld.hu 0x7468[tp]` ⇒ `0xC6468` = 2639, the value already in the loop diagram.

Byte-frozen across stock / v90 / v92 / v94 / v96 in every cell except `0xC40D2`.

### 1.2 The float block is an identity — EVIDENCE

```
S1 = gp-0x363c (x[n-1]),  S2 = gp-0x3638 (x[n-2])
0x3b9d2  ld.w 0x5048[tp]   b0 = 1.0f
0x3b9de  ld.w 0x504c[tp]   b1 = 0.0f
0x3b9ea  maddf.s           acc = x[n]*b0 + S1*b1
0x3b9ee  ld.w 0x5050[tp]   b2 = 0.0f
0x3b9f6  maddf.s           y   = acc + S2*b2
0x3ba04  st.w              S2 <- S1   (shift register)

y[n] = 1.0*x[n] + 0.0*x[n-1] + 0.0*x[n-2]
```

**⇒ |H| = 1.000, arg H = 0.000 deg, at all frequencies.** Any part of the sign calculation that was
blocked on "the 8 coefficients of L" is unblocked: that block does nothing.
(Independently re-confirms `reference_accord_fun3b8f6_fir_not_biquad_...` from the flash bytes.)

The real dynamics in `FUN_0003b8f6` are the four one-pole IIRs `y += (x-y)*cal/4096` in the
halfword table above — three of them cascaded twice.

---

## 2. BLOCKER 2 — `f'`

### 2.1 The "RAM table cannot be read" premise is FALSE

`FUN_000382d8` @`0x382d8` is the **sole writer** of both source arrays; its only caller is
`FUN_00022ca0`. It is a 2-D flash table interpolated on vehicle speed and selected by mode:

```
mode = byte at gp+0x63fd                                             0x382e0
brk  = *(int*)(0xCC9FC + mode*4)                    7 speed breakpoints
recs = *(int*)(B + mode*4), B in {0xC7B40 0xC7C28 0xC7D10 0xC7DF8 0xC7EE0 0xC7FC8 0xC80B0}
record: +0x00 count(9), +0x02..+0x12 nine X shorts, +0x14..+0x24 nine Y shorts
writes gp-0x6350[0..8] = Xsrc   @0x38880 / 0x388aa
       gp-0x630c[0..8] = Ysrc   @0x3884c / 0x38886 / 0x388b0
```

`FUN_000389ec` @`0x389ec` rescales into the consumed table (`gp-0x64b8[]` X, `gp-0x641c[]` Y,
stores @`0x39522`,`0x39548` and the copy loop `0x395d4`). `FUN_00038148` @`0x38148` reads exactly
`gp-0x64b8..gp-0x64a6` / `gp-0x641c..gp-0x640a`. Both ends verified — same 10-point table.

🛑 **Tool-zero warning.** `search_instructions operand_pattern="-0x6350\[gp\]"` returned
**0 matches / 183,570 scanned / `truncated:false`**. The real accesses are `movea -0x6350,gp,r11`
plus register-indirect `ld.h -0x6350,r15,r13`. Searching the bare `0x6350` found all nine. Third
occurrence of this class today.

### 2.2 `f' >= 0` is ENFORCED IN CODE, not merely true of the data

```
FUN_000382d8  0x388c4 onward : EIGHT consecutive unconditional rungs, Ysrc[i] = max(Ysrc[i], Ysrc[i-1])
FUN_000382d8  interp branch  : if (i != 0 && y < prev) y = prev              (float path)
FUN_000389ec  0x38de2 / 0x38e48 : Y[i] = max(Y[i], Y[i-1])   (both branches)
FUN_000389ec  0x38e9c / 0x38ea2 : Y[i] = min(Y[i], cal 0xC6200 = 8192)
FUN_000389ec  0x38d1c / 0x38d22 : X[0] = 0, Y[0] = 0   (hard-stored zeros)
```

No gate, no mode condition, every rebuild. **⇒ Y is non-decreasing for ANY cal values, ANY mode,
ANY speed, on ANY build.**

### 2.3 And the data agrees, with margin — 14/14 records

Both live modes, all 7 speed breakpoints (0/15/40/80/120/160/200 km/h):
**X monotone strictly increasing 14/14, Y monotone strictly increasing 14/14.**

Nominal `K1 = K2 = 1024` (`FUN_0003897a` slews to `clamp(gp-0x6982 or 1024, 204, 2048)`, bounds
`0xC6392`=2048 / `0xC639C`=204; same for `gp-0x6984` with `0xC6390`/`0xC639A`) ⇒ **the built table
equals the flash record**. At the 15 km/h record:

```
X: 0    150  300  618  1200 1800 3000 5000 10000 14490(=cal 0xC613C)
Y: 0    429  788  1350 2029 2358 2763 3297  4625  8192(=cal 0xC6200)

f' per segment: 2.860  2.393  1.767  1.167  0.548  0.338  0.267  0.266  0.794
```

A saturating assist curve. **`f'` is strictly positive and ~10x steeper near zero.** In the
hands-off return-to-centre regime the driver torque is ~0, so `|iVar6|` is small and **`f' ~ 2.86`,
the steepest segment.**

### 2.4 What this actually means

The LERP is a **memoryless, sign-preserving, gain-varying** element (`gp-0x6b70 =
sign(iVar6)*LERP(|iVar6|)` with `LERP(0)=0`, so the map is odd and monotone non-decreasing).
**It cannot invert a signal at any frequency.** The closed-loop sign question therefore reduces to
a pure gain/phase problem with a known-positive scalar in the path.

---

## 3. The closed-form sign, and the ONE remaining bit

From `FUN_00038148` (`0x38208`, `0x38218`, `0x381ee`) and `FUN_00037fe6`:

```
sum6   = SUM_i (lane_i * gate_i * W_i) >> 10                     W_i = 0xC63A0..AA, all 1024
target = ((sum6 * polarity * 2639) >> 10) * 16                   polarity = gp-0x6752
gp-0x374c += (target - gp-0x374c) * 102/1024                     IIR, |H| .94/.91/.88, -18.7/-23.6/-26.8 deg
iVar6  = gp-0x6bfe + gated(gp-0x6bfa) - (gp-0x374c >> 4)         the *16 and >>4 cancel exactly
gp-0x6b70 = sign(iVar6) * LERP(|iVar6|),  clamp +-8192
gp-0x6ad6 = (... + gp-0x6b70 * cal_0xC64B0) * speedgain >> 10
```

Measured constants: **`0xC64B0` = 1** (Path 2 live, unity), **speed-gain table = 1024 flat**
across the entire range (`0xC6ACA..` all 1024; only the off-scale knot is 0) ⇒ **gain 1.0, no speed
shaping.**

```
d(gp-0x6ad6)/dW_i = - f' * polarity * (2639/1024) * |H_IIR| * lane_i/1024
gp-0x6ad6 is the PID REFERENCE, subtracted  =>  d(assist)/dW_i = + f' * polarity * 2.577 * |H| * lane_i/1024
```

At `W=1024`, `f'=2.86`, `|H|=0.91` at 7.79 Hz:
**Path-2 gain = `polarity` x 6.71**, phase −23.6° plus one extra task tick.

**Every factor is now known and positive EXCEPT `sign(polarity * lane_i)`.**

### 3.1 `gp-0x6752` is a CONFIGURATION CONSTANT, not a live gate — and this is good news

Writers (5 sites, all found): `0x48e68`, `0x48e88` (`FUN_00048a40`), `0x490c0` (`FUN_000490ac`),
`0x49838`, `0x49844` (`FUN_000497e6`).

```
FUN_000497e6:  if (*(char*)(*(int*)(gp-0x34b8) + 4) == 0x2C) gp-0x6752 = +1; else gp-0x6752 = -1;
FUN_000490ac:  gp-0x6752 = +1                                (init/reset path)
```
Shadow-lockstep paired with `gp-0x4c2d`, `FUN_0006b9fa` on mismatch — the kit's known 4-pair pattern.

**It takes only +1 or -1. Never 0. It does not track steering direction and does not chatter.**
The guard `(int)cVar5 + 1U < 3` in `FUN_0003b8f6`/`FUN_00038148` is a plausibility check on the
config constant, not a live-signal gate.

Two consequences:
1. **The feared failure mode is REFUTED**: Path 2 is *not* muted hands-off. All six lane weights
   are live in the symptom regime. (`gp-0x6bbe` p50 ~73.6 ct sits well inside its
   `|x| <= 2048` zero-reject window, so `0xC63A2` is live there too.)
2. The sign is a **fixed property of this vehicle**, so one observation settles it permanently.

**It is sourced from a RAM/EEPROM config record via a pointer at `gp-0x34b8`. It is NOT in the
flash image. I cannot read it.**

---

## 4. Does V94 pin Path 2's sign? — the quantitative answer

**Sizing.** `gp-0x6b26` reaches the motor two ways:
- **Path 1**: unity into the aggregator, zero phase.
- **Path 2**: `x1 (W=1024)` → `x polarity x 2.577` → IIR `0.91 / -23.6 deg` → `x f' (2.86)` →
  `x 0xC64B0 (=1)` → `x speedgain (=1.0)` → `gp-0x6ad6` → **then through the PID** (Kd = 2.000
  unfiltered, dominant at 7.79 Hz).

**Path 2 is ~6.7x Path 1 before the PID, and the PID multiplies it further.** So on gain alone,
V94's catastrophe was dominated by Path 2, and V94 would pin Path 2's sign.

**But that sizing is CONTRADICTED by the kit's own data, and the contradiction is the real finding.**
V91/V92 raised the same producer x1.5 and measured **0.99 [0.91, 1.26]** against a pre-registered
1.50 — a hard null. A 6.7x-plus-PID path cannot be invisible to a x1.5 dose. So either the sizing
is wrong, or the loop compensates. The kit's own explanation (`gp-0x6b26 = K*alpha`, and in a
stable closed loop the product is invariant to K) resolves it — **and it predicts precisely the
asymmetry that was observed**:

| dose | prediction under closed-loop invariance | observed |
|---|---|---|
| **up** x1.5 (V91/V92) | product invariant ⇒ **null** | **null**, 0.99 [0.91, 1.26] |
| **down** x0.25 (V94) | below the compensable threshold ⇒ **instability** | **aborted drive**, motor accel 3-7x up >9 Hz |

**⇒ `0xC63A6` is not a lever. It is a cliff edge with a plateau above it.** Down is dangerous
(already demonstrated, at cost). Up is a re-run of a measured null. **BELIEF, not EVIDENCE** — the
invariance argument is a model, not a measurement — but the two flown doses are consistent with it
and inconsistent with a linear dose-response in either direction.

**And it does not transfer to `0xC63A2`.** `gp-0x6b26` is INERTIA (in phase with acceleration);
`gp-0x6bbe` is VISCOUS (in phase with rate, ~0 deg). Different phase, different loop role. V94 says
nothing about the viscous lane's sign.

---

## 5. What I could not close, and exactly what would close it

**Residual: `sign(gp-0x6752)`, one bit.**

For `0xC63A2` on the viscous lane, with `lane_6bbe ~ +c*omega` (measured: ~90 ct/(rad/s), phase ~0 deg):

```
d(assist)/dW  ~  + polarity * omega
  polarity = +1  =>  raising W adds assist WITH the motion = NEGATIVE viscous damping
                     => raising 0xC63A2 makes the 7.8 Hz ring WORSE;  LOWER it to damp
  polarity = -1  =>  exactly the reverse;                             RAISE it to damp
```

I will not pick. A wrong pick here is a V94 repeat, and the operator drives the car.

⚠ A second, smaller caveat, stated so nobody trips on it later: `gp-0x6bbe`'s "+90 ct/(rad/s),
phase ~0 deg" was measured against **bus-frame** wheel rate, while `polarity` maps the **motor/model
frame**. Composing them needs the frame convention as well as the bit. A direct observation of the
end-to-end sign (option A or B below) sidesteps both.

### How to close it, cheapest first

**A. No new flight — re-read flown data (try this first).**
Any route carrying both a `gp-0x6bbe` probe (V92: `CAVE.6BBE`, `427.6BBE.SAR4`) and *any*
downstream cell (`gp-0x6b70`, `gp-0x374c`, `gp-0x6ad6`) gives the sign directly as the sign of the
cross-correlation at 6-9 Hz. V96 probed `6B70`/`374C`; the brief says its measurement failed —
**worth confirming whether it failed on identity/range or produced no data at all**, because a
low-resolution but sign-correct record is sufficient here. Sign needs far less SNR than magnitude.

**B. No new flight — check V89's measured direction against the traced prediction.**
`accord-friction-polarity-more-assist` traced nine links and reports "Direction measured". That
chain runs through the same `polarity` factor. If V89's on-car direction matches the trace under
`polarity = +1`, the bit is empirically anchored with zero new exposure. **I did not do this check
— it needs the V89 route data, which is outside what I was scoped to.** It is the highest-value
next step and it is cheap.

**C. One frame of telemetry (if A and B both fail).**
`gp-0x6752` is a **single byte, ±1**. It needs **one bit** of cave budget and one frame — not a
route, not a dose, not a spectrum. It is constant, so the first frame after ignition settles it
forever. This is the smallest instrument this kit has ever needed.

---

## 6. Defects found in work already accepted — REPORTED, NOT FIXED

1. **The handover list of eight "float coefficients" was wrong** — 3 floats + 6 u16, and it omitted
   `0xC4048` (the only nonzero FIR tap).
2. **`STATE.md` §A6b's "the transfer cannot be read from the image"** is false. It can; see §2.
3. **Mode 24 and mode 26 are NOT byte-identical in this table family** — rec[0], rec[3], rec[4],
   rec[5] and the breakpoint array all differ (e.g. rec[3] `Y[1]` 643 vs 515).
   `accord-stock-mode24-equals-mode26-damper-is-ours.md` asserts byte-identity but is scoped to the
   six **damper** factor families, a different table set — so I do not read it as contradicted.
   Flagging it because it will be read as global. ⊕ In the 6-20 km/h symptom regime the car sits
   between rec[0] and rec[1], and **rec[1] and rec[2] ARE byte-identical between modes**, so mode
   choice barely moves this curve there.
4. **My own earlier flag on `gp-0x6bfe`/`gp-0x6bfa` was wrong** — the loop diagram is correct.
   `gp-0x6bfe` is written at `0x3bc3e` in `FUN_0003bc20`; `gp-0x6bfa` at `0x273b0`, `0x273c8`,
   `0x273d6` in `FUN_00026c80`. Distinct real cells, not an off-by-2 on `6bfc`/`6bf6`.

---

# ADDENDUM — IIR pricing, the V86 cross-check, and V86's own probe data

## 7. Call rate = 1000 Hz. EVIDENCE, two independent ways.

**(a) Structural.** Both jarls live in `FUN_0002214a` under the **identical** guard:
```
uVar2 = 1 << (*(byte*)(gp-0x67fa) & 0xf)
uVar4 = uVar2 & 0x830
if (uVar4 != 0) { FUN_0003b66a; FUN_0003b8f6();  <-- jarl 0x2240e ; FUN_0003bc20; FUN_00041d56; }
...
if (uVar4 != 0) { ... FUN_00038148();            <-- jarl 0x22676 ; ... FUN_00037fe6(); }
```
**Same variable, same expression, no counter, no modulo, no decimation.** `0x830` is a STATE
bitmask on `gp-0x67fa` (states 4/5/11), not a phase divider — which independently re-confirms
`reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md` from the decompile.
So whatever rate one runs at, the other runs at.

**(b) Numerical.** `0xC63AC` = 102 (alpha = 102/1024) has a known on-car phase of
−18.7 / −23.6 / −26.8 deg at 6 / 7.79 / 9 Hz:
```
fs = 1000 Hz -> -18.70  -23.63  -26.73   max err 0.07 deg   <== MATCH
fs =  500 Hz -> -33.58  -40.26  -43.96   max err 17.16 deg
fs =  200 Hz -> -55.59  -59.90  -61.68   max err 36.89 deg
fs =  100 Hz -> -63.84  -64.12  -63.57   max err 45.14 deg
```
⊕ Free internal check: `0xC40D0`/4096 = 408/4096 = 0.099609 = **exactly** 102/1024, so the friction
filter carries a phase that is already validated on-car.

## 8. The four IIRs priced at 1 kHz — and the headline is NOT `0xC40D4`

| cal | val | stages | alpha | fc | @6 Hz | @7.79 Hz | @9 Hz |
|---|---|---|---|---|---|---|---|
| `0xC40D6` accel/inertia | 246 | **x2** | 0.06006 | **9.86 Hz** | 0.730 / **−60.5°** | 0.616 / **−73.9°** | 0.546 / **−81.6°** |
| `0xC40D4` torque input | 573 | x2 | 0.13989 | 24.0 Hz | 0.941 / −26.0° | 0.905 / −33.3° | 0.877 / −38.0° |
| `0xC40D0` friction | 408 | x1 | 0.09961 | 16.7 Hz | 0.941 / −18.7° | 0.906 / −23.6° | 0.880 / −26.7° |
| `0xC40D8` `gp-0x4f60` | 3686 | x2 | 0.89990 | 366 Hz | 1.000 / −0.5° | 1.000 / **−0.6°** | 1.000 / −0.7° |

Two things fall straight out:
- **`0xC40D6` = 246 is the dominant phase element in the whole function** — its corner sits at
  **9.86 Hz, right on top of the 7.79 Hz ring**, and it contributes **−73.9°**, 2.2x more than
  `0xC40D4`. It is on the **acceleration / inertia** term.
- **`0xC40D8` = 3686 is a pass-through** (−0.6 deg, |H| = 1.000). It is **not a lever**; anyone
  proposing it is proposing a no-op.

**Lineage, read from the images (92 plain images + stock), not from the scripts:**
```
0xC40D0 = 408   in 92/92   VIRGIN
0xC40D2 = 102 in 85, 204 in 7   (V89)
0xC40D4 = 573 in 91, 286 in EXACTLY ONE image (_v86)   FALSIFIED
0xC40D6 = 246   in 92/92   VIRGIN
0xC40D8 = 3686  in 92/92   VIRGIN  (but a no-op, see above)
```

## 9. The V86 cross-check — MY MODEL SAYS IT SHOULD HAVE WORKED. It didn't.

`0xC40D4` 573 -> 286, x2 cascade, at 7.79 Hz: **gain x0.759, phase −33.3° -> −65.4°, delta −32.1°**,
on `fVar18` — which is the **dominant term of `iVar6`** via
`0x3bc1a st.h -0x6bfc` -> `0x3bc3e st.h -0x6bfe` -> `0x38218 ld.h -0x6bfe`.
That is a large change. Measured: **1.001 [0.976, 1.060]** against a pre-registered [0.797, 0.875].

**I checked the obvious escape hatch and it is CLOSED.** V86's own probe (`0x14A` byte4 b7:b3)
measured the lane and its gate. Decoded with the kit's own `decode_v86_probe.py` (self-test PASS),
route 6f, 23,058 frames / 232 s:
```
FINGERPRINT b3 = 1.0000        build identity confirmed
GATE        b4 = 1.0000        gp-0x67ab < 2 -- ZERO frames with the gate clear
NONZERO     b6 = 0.9975        gp-0x6b70 is live
MAG         b5 = 0.8822        |gp-0x6b70| >= 64      (engaged 0.945 vs manual 0.782)
SIGN        b7 = 0.5461        swinging both ways, not railed
6-20 km/h window: gate 1.0000, nonzero 0.9988
```
**⇒ Not a V64-class null.** The lane was in circuit 100% of the time, live, substantial, and
engagement-sensitive; and the cal was byte-verified in force (286 in exactly one image of 92).
So V86's null is a **real null on a live lane**, and my model owes an explanation.

**Best candidate — closed-loop suppression, and it is the SAME mechanism the kit already invoked
for V91/V92.** `FUN_0003b8f6`'s input `gp-0x6b98` is the **FOC motor command — the loop OUTPUT**.
So this filter sits *inside* the closed loop, where a forward-path perturbation is suppressed by
1/(1+L). A secondary, magnitude-only mechanism: `gp-0x6bfc = (fVar18 − friction(|fVar18|) − inertia)`
and the friction term is itself proportional to `|fVar18|`, so attenuating `fVar18` attenuates both
the direct term and its own subtrahend — the difference is less sensitive than either.

🛑 **This is a warning for V97, not just a post-hoc excuse.** `0xC63A2` is *also* an internal
element of the same loop. And a lane proportional to a state that the lane's own action suppresses
(a viscous term proportional to the rate it damps) will always show a sub-linear dose-response.
**⇒ If V97 touches a lane weight, the dose must be large and the scoring must be on the ring
amplitude (the state), never on the lane's own value.**

## 10. NEW MEASUREMENT — `gp-0x6b70` is ~acceleration-proportional and WEAKLY ANTI-DAMPING

Cross-spectrum of `sign(gp-0x6b70)` (V86 probe b7) against wheel rate, route 6f, Welch, contiguous
segments, with two controls:
```
ENGAGED, all speeds    n=14115   phase(6-9 Hz) = +100.4 deg   coh^2 = 0.507
ENGAGED 6-20 km/h      n=10851   phase(6-9 Hz) = +104.4 deg   coh^2 = 0.460
MANUAL,  all speeds    n= 8832                                coh^2 = 0.002
CONTROL rate time-reversed        coh^2 = 0.003
CONTROL sign shuffled             coh^2 = 0.002
```
**Coherence 0.46-0.51 against controls at 0.002-0.003 — a factor of ~200, and engagement-conditional.**

Interpretation, using the established `assist ∝ −gp-0x6b70`:
- +90 deg would be exactly acceleration-proportional. **+100 deg ⇒ the lane is dominated by an
  apparent-INERTIA component**, echoing the kit's `gp-0x6b26`-is-inertia result at the aggregate level.
- The dissipative projection is `cos(100.4°) = −0.181` ⇒ `gp-0x6b70` has a component **anti-phase
  with rate**, so `assist ∝ −gp-0x6b70` carries **+0.18 x rate** — assist pushing WITH the motion.
  **The lane is weakly ANTI-DAMPING at 6-9 Hz.** Consistent with the corpus-level
  `Re(Z) < 0` result replicated on three drives, strongest in the micro regime.

🛑 **Scope of this claim.** EVIDENCE for the **aggregate** `gp-0x6b70`. It does **not** decompose
into which input drives it — the anti-damping could come from `gp-0x6bfe` (the plant model, the
dominant term of `iVar6`) rather than from any of the six lanes. So it does **not** by itself give
the sign for `0xC63A2`, and I am still not naming a direction. What it does establish, firmly:
**the lane is live, in circuit, engagement-conditional, and currently on the wrong side of zero.**

---

# 11. EXACT REPLACEMENT SENTENCE FOR `docs/STATE.md` §A6b

I did **not** edit `STATE.md`. Apply this yourself.

**REMOVE** the claim that the LERP transfer cannot be read from the image (the "table lives in RAM
(`gp-0x64b8` / `gp-0x641c`)" argument), and **REPLACE** with:

> The LERP consumed by `FUN_00038148` is **not** dynamic: `FUN_000382d8` (`0x382d8`, sole writer of
> both source arrays, only caller `FUN_00022ca0`) builds `gp-0x6350[]`/`gp-0x630c[]` by
> interpolating **flash** records on vehicle speed, selected by the mode byte at `gp+0x63fd`
> (breakpoint pointers at `0xCC9FC + mode*4`; record pointers at `0xC7B40 / 0xC7C28 / 0xC7D10 /
> 0xC7DF8 / 0xC7EE0 / 0xC7FC8 / 0xC80B0 + mode*4`; 7 speed knots 0-200 km/h, 9 X shorts at +0x02 and
> 9 Y shorts at +0x14). `FUN_000389ec` (`0x389ec`) rescales those into `gp-0x64b8[]`/`gp-0x641c[]`
> at a nominal `K1 = K2 = 1024`, so the built table equals the flash record. **The transfer is
> therefore fully readable from the image, and `f'` is computable.** Moreover `f' >= 0` does not
> depend on the cal values at all: monotone-nondecreasing `Y` is enforced unconditionally in code at
> three sites (`FUN_000382d8 0x388c4` — eight consecutive rungs; `FUN_000389ec 0x38de2` and
> `0x38e48`), with `X[0] = Y[0] = 0` hard-stored at `0x38d1c`/`0x38d22` and `Y` capped at cal
> `0xC6200` = 8192. All 14 flash records (7 speeds x 2 live modes) are strictly increasing in both
> axes. **The LERP is a memoryless, sign-preserving, gain-varying element: it cannot invert a signal
> at any frequency, so it closes the OPEN-loop sign of all six Path-2 lane weights.** The remaining
> unknown is the CLOSED-loop bracket (`B = 1 + Q`) and the one-bit vehicle constant `gp-0x6752`,
> which is sourced from an EEPROM/RAM config record via a pointer at `gp-0x34b8` and is **not** in
> the flash image.

⊕ Two smaller `STATE.md`-adjacent corrections, for whoever edits it:
- Any text describing `FUN_0003b8f6`'s coefficients as "8 floats" should read **3 floats
  (`0xC4048`/`0xC404C`/`0xC4050`, taps 1.0/0.0/0.0 — an identity) + 6 u16 Q-format cals**.
- `gp-0x6bfe` and `gp-0x6bfa` in the V96 structure diagram are **correct** — real, distinct, live
  cells, not an off-by-2 on `gp-0x6bfc`/`gp-0x6bf6`.

---

# 12. Q1 — `0xC63AC` 102→130 makes the ring WORSE. Do not cut it. Push it DOWN.

## The measurement that decides it
V96 probes `byte4 b7 = sign(gp-0x6b70)` **and** `byte4 b6 = sign(gp-0x374c>>4)` — the exact branch
`0xC63AC` filters. Cross-spectra vs wheel rate, 6-9 Hz, `nperseg=256`, contiguous engaged segments:
```
route   set            n       arg V vs rate      arg B' vs rate     arg V - arg B'
7e      ENGAGED       61386   +97.3  (coh .554)   -78.6 (coh .465)   +178.1 (coh .493)
7f      ENGAGED       68954  +101.8  (coh .557)   -78.0 (coh .474)   +178.1 (coh .309)
control B' shuffled                                                   coh .0035 / .0001
```
⊕ `arg V` replicates my route-6f/V86 figure (+100.4°) on a different build.
⊕ **`V` and `B'` are 178.1° apart on BOTH routes** ⇒ `iVar6 = A − B'` has its 6-9 Hz phase set by
the **B branch (the lane sum)**, not by `A` (`gp-0x6bfe`).
⚠ In the hands-off subset `arg B'` coherence collapses (.095 / .078), so `arg B'` is only
well-measured over the full engaged set. The verdict below is robust across the entire measured
range of `arg B'` anyway — see the sensitivity table.

## The composition, done explicitly
```
gp-0x374c = H(alpha)*target ;  B' = gp-0x374c>>4 ;  iVar6 = A - B' ;  V = f'*iVar6
dV = -f' * B' * (H2/H1 - 1)          k := |f'B'| / |V|   (unknown; bracketed 0.5 .. 2.0)
0xC63AC 102->130 :  H2/H1 = 1.0381 angle +5.18 deg  ;  (H2/H1 - 1) = 0.0996 angle +70.14 deg
```
**`arg(dV) = arg(B') + 70.14 + 180`.** Over the full measured range of `arg B'`:
```
arg B' = -91.4 -> arg dV = +158.7  cos = -0.932     ANTI-DAMPING
arg B' = -78.6 -> arg dV = +171.5  cos = -0.989     ANTI-DAMPING
arg B' = -74.5 -> arg dV = +175.6  cos = -0.997     ANTI-DAMPING
```
**The perturbation is essentially PURE negative damping for every phase we actually measured.**

## Result — the dissipative projection `|V| cos(theta)`
```
route 7e  baseline theta = +97.30, |V|cos = -0.1270
   cal 130  k=0.5 -> -0.1763 (x1.39 WORSE)  k=1 -> -0.2255 (x1.78)  k=2 -> -0.3240 (x2.55)
   cal 70   k=0.5 -> -0.0422 (better)       k=1 -> +0.0427          k=2 -> +0.2124
   cal 51   k=0.5 -> +0.0228 (better)       k=1 -> +0.1725          k=2 -> +0.4721
route 7f  baseline theta = +101.78, |V|cos = -0.2042
   cal 130  k=0.5 -> -0.2535 (x1.24 WORSE)  k=1 -> -0.3028 (x1.48)  k=2 -> -0.4014 (x1.97)
   cal 70   k=0.5 -> -0.1189 (better)       k=1 -> -0.0337          k=2 -> +0.1368
   cal 51   k=0.5 -> -0.0534 (better)       k=1 -> +0.0974          k=2 -> +0.3990
```
**Raising `0xC63AC` makes the anti-damping WORSE on both routes for every k. Lowering it helps on
both routes for every k, and at k >= 1 it crosses into genuinely dissipative.**

## The mechanism, in one sentence
**`arg V` sits just PAST +90°.** `cos` is negative there and becomes MORE negative as theta rises.
The IIR's "lead" rotates theta **further past 90°, away from the damping axis** — a lead is only a
fix when you are lagging *toward* 180°, and here we are sitting *above* +90° already. **This is
exactly the frame trap you flagged, and it resolves against the build.**

## Two more reasons the DOWN direction is the safe one
```
21 Hz gain vs stock 102:   cal 130 -> 1.1522  RAISES it  (the V62 risk fw-levers flagged)
                           cal  70 -> 0.7597  REDUCES it (V62-safe)
                           cal  51 -> 0.5801  REDUCES it (V62-safe)
```
🛑 **But mind the arithmetic dead zone on the way down** — `((target - gp-0x374c) * cal) >> 10`:
```
cal 130 : |diff| >=  8 counts to move the accumulator    cal 102 : >= 11
cal  70 : |diff| >= 15                                   cal  51 : >= 21
```
`gp-0x374c` holds `target * 16` so typical diffs are large, but **51 nearly doubles the dead zone vs
stock** and could introduce stiction on small signals. **`70` is the conservative pick.**

# 13. Q2 — `0xC40D6` is NOT the better cell, and this is the decisive negative

`0xC40D4` and `0xC40D6` both shape **`A` (`gp-0x6bfe`)** — the branch the measurement above shows is
**not** what sets `gp-0x6b70`'s phase at 6-9 Hz. And that branch's authority over the ring has
**already been measured directly**: V86 rotated `A` by **−32.1°** via `0xC40D4` and scored
**1.001 [0.976, 1.060]** — with its own probe confirming the lane was in circuit 100% of the time.
**`0xC40D6` at a comparable dose rotates the same branch by a comparable amount, so expect the same
null.** ⇒ **No cal inside `FUN_0003b8f6` is a good bet for the 7.79 Hz ring.**

⚠ **Honest bound.** The 178.1° anti-phase shows `A` is nearly *collinear* with `B'`; it does **not**
prove `|A|` is small (a large `A` in phase with `B'` fits equally well). So the Q2 negative rests
primarily on **V86's flown null**, not on the phase geometry. The geometry corroborates; it does not
carry the claim alone.

## 🛑 SELF-CORRECTION — my "closed-loop suppression" explanation for V86 was WRONG
I offered `1/(1+L)` suppression as the reconciliation for V86's null. **Retract it.** It contradicts
the kit's own amplification result: if engaging multiplies the 6-9 Hz band **2.8x**, then
`|1+L| < 1` at 7.79 Hz, so an internal perturbation is **amplified, not suppressed**. The correct
explanation is the branch-authority one above. This matters because the two reconciliations differ
where it counts: suppression would have condemned **every** cal in the loop including `0xC63AC`,
whereas branch authority condemns only the `FUN_0003b8f6` cals and leaves **`0xC63AC` high-authority
— it sits on the dominant branch.** It is a real lever; it was simply pointed the wrong way.

---

# 14. 🛑🛑 RETRACTION — MY Q1 ANSWER WAS INVERTED. `0xC63AC` SHOULD GO **UP**.

## The error
`scipy.signal.csd(x, y)` returns **`arg(Y) − arg(X)`**, not `arg(X) − arg(Y)`. I labelled every
cross-spectrum the wrong way round. Verified on a synthetic signal with `y` lagging `x` by 45°:
```
csd(x,y) angle = -45.00 deg   =>  convention is arg(Y) - arg(X).  MY LABELS WERE INVERTED.
csd(x, dx/dt)  = +76.12 deg   =>  exactly the first-difference ideal 90 - (w/2) = 90 - 13.88. Pipeline now fully understood.
```

## What CAUGHT it — the cross-check against the team lead's independent `Q`
`Q = −d(gp-0x6b70)/dT` ⇒ predicted `arg(V) − arg(T) = arg Q + 180 = +46.3° (7e) / +48.5° (7f)`.
```
BEFORE correction:  argV-argT = -43.4 / -41.7   ->  dev -89.7 / -90.2   *** ~90 deg, replicated ***
AFTER  correction:  argV-argT = +43.4 / +41.7   ->  dev  -2.9 /  -6.8   AGREE
```
**Two fully independent pipelines — my 100 Hz sign-bit Welch and the lead's 50 Hz episode-bootstrapped
`Q` — now agree to within 7°.** A replicated ~90° deviation was the tell; it was not a data problem.

## Corrected phases (all `arg(first) − arg(second)`)
```
route   argV-argT            argV-argRate      argB-argRate      argV-argB
7e      +43.4 (coh .767)     -97.3 (coh .554)  +78.6 (coh .465)  -178.1 (coh .493)
7f      +41.7 (coh .699)    -101.8 (coh .557)  +78.0 (coh .474)  -178.1 (coh .309)
```

## CORRECTED Q1 RESULT — raising `0xC63AC` REDUCES the anti-damping
`arg(dV) = arg(B') + 70.14 + 180`, now `= -31.3°`, `cos = +0.854` ⇒ **dV is DAMPING.**
```
7e baseline |V|cos = -0.1270 : cal 130 -> -0.0845 / -0.0419 / +0.0432   (k = 0.5/1/2)  ALL BETTER
7f baseline |V|cos = -0.2042 : cal 130 -> -0.1619 / -0.1196 / -0.0350                  ALL BETTER
                               cal 150 -> better still (7e crosses into dissipative at k>=1)
                               cal  70 -> WORSE on both routes for every k
```
**Raising `0xC63AC` is the fix. Lowering it — what I recommended — would have made the car worse.**
Mechanism, corrected: `arg V` sits just **below −90°**; raising alpha rotates it **toward −90° and past
it**, i.e. toward the damping axis. The lead arrives as lead (the lead's `|Q| = 1.233 > 1` gate) **and
the lead is the right thing to want.**

⊕ The cost I flagged is still real and now applies to the correct direction: `cal 130` raises 21 Hz
gain by **1.152x** (the V62 risk). The dead-zone argument no longer applies — it only bit going down.

## What SURVIVES the correction, unchanged
- **`gp-0x6b70` is apparent INERTIA + weakly ANTI-DAMPING.** `cos` is even: `cos(-97.3°) = cos(+97.3°)`.
  The dissipative projection and every duty/coherence figure are untouched.
- **`arg V − arg B' = ±178.1°`** — magnitude unchanged ⇒ the **B branch still dominates `iVar6`**.
- **§13 / Q2 is unaffected**: `0xC40D6` sits in the `A` branch, and that rests on V86's *flown null*
  plus the anti-phase **magnitude**, neither of which uses a phase sign.
- **§12's retraction of "closed-loop suppression" stands** — that argument was about amplification vs
  suppression, not phase.
- **Sections 1-11 are untouched.** Blocker 1, Blocker 2, `f' >= 0`, the LERP provenance, the `L`
  correction and the V86 probe duties use no cross-spectral phase at all.

## 🛑 NEW TRAP FOR THE KIT
**`scipy.signal.csd(x,y)` gives `arg(Y) − arg(X)`.** Any kit script that reports a cross-spectral
phase should be checked against a synthetic known-lag pair before its sign is trusted. This one was
caught only because an independent measurement existed to disagree with — **the ~90° replicated
deviation was the signature.**
