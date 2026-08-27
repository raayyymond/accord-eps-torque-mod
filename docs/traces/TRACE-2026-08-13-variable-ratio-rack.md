# Does the firmware know the rack is variable-ratio? — 2026-08-13, `tracer-rack-ratio`

> ## 🛑 REVISION 2, after team-lead's two objections — **I CONCEDE THE CENTRAL NEGATIVE. IT WAS INVERTED.**
> Sections 1–5 below stand as written. **Section 4's verdict "right shape, right variable, reachable —
> wrong band" is WITHDRAWN.** It was derived under the wrong criterion. See **§7** for the re-issued
> verdict, **§8** for the sign (now resolved to EVIDENCE), and **§9** for a build-direction inversion in
> the objection itself that must not reach a build script.



**Verdict: YES, partially — and it is inside the plant model.** The firmware carries a
**13-point LERP indexed by absolute steering angle**, `0xC6B64`–`0xC6B98`, whose shape is
qualitatively the operator's rack curve (low at centre, flat away from centre, transition
complete by ~120°). It multiplies the **driver-torque term of the plant model** in
`FUN_0003b8f6`. Its depth is **1.2058×**, roughly **one third (log-scale)** of the ~1.7×
variation implied by the supplied rack curve.

🛑 **This table is NOT new to the kit. It was found 2026-08-05 and judged "not the mechanism",
and again in `builds/v80_v107/build_v86_tva.py:141` where it is called "DEAD".** What is new here is (a) the
rack-ratio *framing*, (b) an assembly-level proof of the index variable, and (c) a
double-method proof that no symmetric-notch curve exists anywhere in the cal space.

---

## 1. The shape search — no symmetric notch exists

Two independent Python passes over `[0xBF000, 0xF0000)` (offset == absolute address, LE).

**Method A — record-format scan** (`[n:u16][X n×s16][Y n×s16]`, the kit's established
convention; anchored by `0xC6B64` = 13 matching `FUN_0003b8f6`'s own `tp+0x7b7e`/`tp+0x7b98`
end-pointers). 2,089 structurally valid records. Requiring a **true interior V** — descend then
ascend, both flanks ≥10% of max — leaves **4 distinct shapes**:

| addr | X | Y | why not a rack curve |
|---|---|---|---|
| `0xC68B4` | `0,330,490,630,770,930,4020` | `0,-1428,-1967,-2264,-2367,-2280,1678` | signed bipolar, ends nowhere near equal |
| `0xC6870` | same X | `0,-45,-62,-71,-74,-72,53` | same, scaled |
| `0xC63D0` | `6,31,98,307,1024` | `1024,1024,1024,31,634` | collapse to 3%, no recovery to flat |
| `0xC528C` | `0,200,500,1000,2000` | `6888,6888,6888,4000,8933` | ends 30% **above** the flat, not equal to it |

**Method B — format-free sliding window** (no layout assumption at all): windows of 7/9/11/13
u16s with the minimum at the centre index, both halves monotone into it, and flat ends matching
within 20%. **24 hits, every one a pure STEP DOWN** (`[87,87,87,70,70,70,70]`,
`[122,122,122,100,100,…]`, `[60,60,60,40,40,40,50]` …) — a descending half followed by a flat
half, admitted by the monotonicity test but carrying no rising flank.

⇒ **EVIDENCE: there is no flat-notch-flat, symmetrically-indexed rack-ratio table in this
firmware.** Both methods agree. If a rack ratio is represented, it is represented on an
**absolute-|angle|** axis — which is exactly what the brief predicted, and what was found.

### The candidate: `0xC6B64`–`0xC6B98` [EVIDENCE — Python byte read, stock `code.bin`]

```
0xC6B64  count = 13
X (gp-0x6a10 counts, 0.1°/count):
    0   340   640   850  1000  1200  1400  1576  1736  1916  2084  2280  4776
  ° 0.0  34.0  64.0  85.0 100.0 120.0 140.0 157.6 173.6 191.6 208.4 228.0 477.6
Y (Q10 gain, 1024 = 1.000):
  899   908   981  1060  1083  1084  1084  1084  1084  1084  1084  1084  1084
```

Gradient profile — **94.6% of the entire swing lives in 34°–100°**:

| angle band | gain | Δ | gradient | share of swing |
|---|---|---|---|---|
| 0–34° (centre floor) | 899 → 908 | 1.0100× | 0.029 %/° | **4.9 %** |
| 34–100° (flank) | 908 → 1083 | 1.1927× | 0.27–0.38 %/° | **94.6 %** |
| >120° (plateau) | 1084 | flat | 0 | 0 % |

**Total swing 1.2058×.** Supplied rack curve: flat/notch ≈ 1/0.55…1/0.60 = **1.67–1.82×**
[BELIEF — the brief's stated proportions; I do **not** have digitised rack numbers].
⇒ the firmware compensates **31–37 % of the mechanical ratio variation in log terms**.

**Virginity [EVIDENCE, Python over 96 images]:** `0xC6B64..0xC6B9B` is **byte-identical in all
96** stock + `_v*_plain_image.bin` files. `builds/v80_v107/build_v86_tva.py:141` names it but only to *reject*
it — never writes it. Same for the `0xC633A` gate cal below.

---

## 2. Does `FUN_0003b8f6` read angle? — **YES, unambiguously**

`0x3ba12: ld.hu -0x6a10[gp],r15` — and it is the LERP index (`0x3ba1c: movea 0x7b64,tp,r10`).
This **refutes** the brief's "structurally blind to rack position" hypothesis.

### Complete input list [EVIDENCE — full `disassemble_function` at `0x3b8f6`, every `ld`]

**RAM (gp-relative), with its entry gate:**

| cell | addr | gate |
|---|---|---|
| `gp-0x6b98` aggregator/motor cmd | `0x3b8f6` | `\|x\| ≤ 8192` |
| `gp-0x4f60` torque sensor | `0x3b908` | `−25600 ≤ x ≤ 25600` |
| `gp-0x6abc` motor rate | `0x3b91c` | `\|x\| ≤ 12999` |
| `gp-0x6752` polarity (`ld.b`) | `0x3b92e` | `x ∈ {−1,0,1}` |
| **`gp-0x6a10` absolute steering angle** | **`0x3ba12`** | `< 0x2711` (10001 ct = 1000.1°), else gain forced to 1024 |

State (read+written EMA memories): `gp-0x3628`, `-0x3624`, `-0x3620`, `-0x361c`, `-0x363c`,
`-0x3638`, `-0x362c`, `-0x3634`, `-0x3630`, `-0x3618`.

**Cal (tp-relative, tp = 0xBF000 — anchored: `tp+0x746e` → `0xC646E`, the kit's known INERTIA
gain, and `tp+0x50d2` → `0xC40D2`, V89's K1; no off-by-0x1000):**

`0xC6468` output scale · `0xC40D4` EMA α (cmd chain ×2) · `0xC40D8` EMA α (torque chain ×2) ·
`0xC613A` torque-chain gain · `0xC4048`/`0xC404C`/`0xC4050` FIR taps (float) ·
**`0xC6B64`–`0xC6B98` the angle LERP** · `0xC40BC` rate knee · `0xC4080` K0 ·
`0xC40D2` K1 friction · `0xC40D0` friction EMA α · `0xC40D6` inertia EMA α (×2) ·
`0xC646E` inertia gain.

### 🛑 Where the angle gain is applied — this is the structural crux

```
0003ba7e: cvtf.uws r12,r16      ; r16 = (float) angle_gain          [LERP output, Q10]
0003ba82: mulf.s  r16,r8,r14    ; r14 = angle_gain × r8             [r8 = clamp(FIR(torque), ±15)]
0003ba8a: maddf.s r13,r14,r7,r8 ; r8  = r14/1024 + r7               [r7 = EMA²(motor cmd)]
```

```
MODEL_pre = EMA²(motor_cmd)  +  (angle_gain(|steer|)/1024) × clamp(FIR(EMA²(torque_sensor)), ±15)
gp-0x6bfc = clamp(0xC6468 × (MODEL_pre − friction − inertia), ±20000)   → gp-0x6bfe → FUN_00038148
```

**The angle gain multiplies ONLY the driver-torque term — not the motor-command term.** The
driver-torque→rack-load conversion is *precisely* what a rack ratio governs. Structurally this
is a rack-ratio compensation sitting exactly where one belongs. [Strong structural EVIDENCE;
the *interpretation* as rack-ratio compensation is BELIEF.]

---

## 3. `gp-0x6a10` IS absolute angle — assembly proof, and a correction to my own memory

Sole real writer: `FUN_0003fc16` @ `0x3fca4`. The producer, byte-verified:

```
0003fc36: ld.h  0x641c[gp],r11     ; r11 = trim
0003fc3a: ld.h  -0x69e0[gp],r15
0003fc3e: ld.hu 0x733a[tp],r9      ; r9  = cal(0xC633A) = 130
0003fc42: add   r11,r15            ; r15 = gp-0x69e0 + gp+0x641c
0003fc44: cmp   r9,r15
0003fc4a: ble   0x0003fc50
0003fc4c: mov   r14,r15            ; clamp HIGH -> +130
0003fc50: subr  r0,r14             ; r14 = -130
0003fc54: bge   0x0003fc60
0003fc5a: subr  r0,r15             ; clamp LOW  -> -130
0003fc60: ld.h  -0x69ca[gp],r6     ; absolute steering angle, 0.1°/count
0003fc68: sub   r15,r6             ; r6 = angle - clamp(offset, ±130)
0003fc8a: jarl  0x00049a5a,lp      ; abs()
0003fc94: jarl  0x00049a78,lp      ; saturate to 0xFFFF
0003fca4: st.h  r10,-0x6a10[gp]
```

```
gp-0x6a10 = | gp-0x69ca − clamp(gp-0x69e0 + gp+0x641c, ±130 counts) |
                                                        ±130 ct = ±13.0°
```

**The subtracted correction is hard-clamped to ±13.0°** (`0xC633A` = 130, enable `0xC64A8` = 1,
both byte-identical across all 96 images). ⇒ `gp-0x6a10` is **absolute steering-angle magnitude
to within a bounded ±13° offset** — it cannot be a free-running tracking error.

🛑 **This corrects `.claude/agent-memory/firmware-codepath-tracer/reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles.md`**, whose
"**Problem 2 — wrong variable, judged fatal**" rests on `gp-0x6a10` being a tracking error.
That premise is false. `builds/v80_v107/build_v86_tva.py:141` reached the same conclusion independently from
data (99.94 % match to `|angle| ≥ 0.85°`); this is now confirmed from the instruction stream.
**Memory not edited — flagged to the orchestrator per standing instruction.**

⊕ Note for the operator's left-offset zero: `gp-0x69e0 + gp+0x641c` is subtracted *and clamped
to ±13°*, i.e. the firmware already applies a bounded centre-offset correction on this axis.

---

## 4. The geometry falsifier — run early, and it REVERSED once

🛑 **First attempt used the wrong engagement key and produced a false kill.** `cs_eng` is
all-zero on r80/r81 (r82: 933 frames, |angle| max 16.9°, table swing 1.0044× → "unreachable").
`cc_lat` (latActive) is the kit-confirmed signal — r81 gives 6,591 frames, matching the V98
memory exactly. Re-run with `cc_lat ≥ 0.5`:

| route | engaged frames | p50 | p75 | p90 | p95 | max | ≥34° | ≥100° | gain swing |
|---|---|---|---|---|---|---|---|---|---|
| r80 | 1,719 | 10.3° | 26.2° | 37.1° | 42.7° | 55.1° | 0.141 | 0.000 | 1.032× |
| r81 | 6,591 | 34.2° | 80.4° | 217.2° | 305.1° | 346.2° | 0.502 | 0.215 | 1.206× |
| r82 | 5,979 | 10.9° | 33.4° | 77.1° | 339.9° | 379.7° | 0.245 | 0.089 | 1.206× |

**Pooled n = 14,289: the full 1.2058× table swing is exercised — 100 % of it.**

⇒ **The reach objection is REFUTED.** The 2026-08-05 rejection's "Problem 1" priced the table
over an assumed 0–45° band and got 3.8 %; the actual engaged distribution reaches 346–380°.
Both pillars of that rejection are now undermined — reach by flight data, variable by assembly.

### 🛑 But the geometry does NOT fit the operator's own words

He reports **worst grinding with the angle in the CENTRE band**. Across 0–34° this table moves
**899 → 908 = 1.0100×, 4.9 % of its swing, 0.029 %/°** — essentially flat. Its entire gradient
(94.6 %) sits at **34–100°**, outside the band he names.

So: the table is *reachable*, and its transition band (34–100°) plausibly coincides with where a
±72° rack notch's flanks would sit [BELIEF — depends on lock-to-lock, ~±432° for this car, and
on the brief's "notch ≈ 1/6 of the plotted range"]. **But it is flat exactly where the symptom
is worst.** A flat gain cannot generate an angle-dependent error gradient in the centre band.

---

## 5. Implicit constant ratio [WEAK — flagged, not established]

The only hardcoded ratio-like scalar on the motor-rate → model path:

```
0003baae: mulh r1,r6            ; r6 = polarity × gp-0x6abc (motor rate)
0003bab0: mul  0xc,r6,r0        ; ×12
```
feeding both the `0xC40BC` rate ramp and, via `(iVar20 − prev) × 0.5 × 17.453293`
(`mov 0x418ba058` = 1000·π/180), the inertia term.

**×12 is a constant where a variable-ratio rack demands a function of angle.** [BELIEF] I cannot
tell from the instruction stream whether 12 is a steering/gear ratio or a Q-format units factor —
`gp-0x6abc` is 4.7121 counts/(column °/s), and 4.7121 × 12 = 56.5 has no obvious physical
reading. **To settle it I would need** the units of `gp-0x3618`/`gp-0x3634` established against a
measured motor rate, which this trace did not do.

---

## 6. Bottom line

| question | answer |
|---|---|
| Symmetric notch table anywhere? | **NO** — two methods, 0 hits |
| Absolute-angle-indexed gain with rack-curve shape? | **YES** — `0xC6B64`–`0xC6B98` |
| Does the plant model read angle? | **YES** — `0x3ba12`, and it gates the driver-torque term |
| Is `gp-0x6a10` absolute angle? | **YES** — ±13° bounded offset, assembly-proven |
| Is the table reachable engaged? | **YES** — full 1.2058× swing exercised, n=14,289 |
| Does it explain a **centre-band** symptom? | **NO** — flat there (1.01× over 0–34°) |
| Does the firmware know the rack is variable-ratio? | **PARTIALLY** — ~1/3 of the variation, compensated on the flanks only |

### What I could not resolve
**The SIGN of the compensation.** The table is *low at centre*. Whether that is the correct
direction depends on the reference frame of `MODEL_pre` — if the driver-torque term is
rack-force-referred, a lower stroke ratio at centre means *more* force per unit torque and the
gain should be **high** at centre (wrong way); if it is column/motor-referred, higher mechanical
advantage at centre means *less* motor effort and the gain should be **low** at centre (right
way). **I will not guess.** To settle it: establish the units of `gp-0x6bfe` at
`FUN_00038148`'s input against the ACTUAL arm `gp-0x374c>>4`, which is known to be
motor-referred — if both arms are motor-referred, 899-at-centre is the correct direction and the
firmware is under-compensating by ~3×.

**No build and no calibration edit is proposed.** The lever that suggests itself, named and
stopped per brief: **`0xC6B80` (Y[0], = 899)** — the centre-floor knot of a virgin table, the
only cell that changes plant-model behaviour *in the band the operator names*. Blocked on the
sign question above. *(Sign resolved in §8; direction of travel corrected in §9.)*

---

# 7. RE-ISSUED VERDICT — the "wrong band" kill was inverted

## 7a. Objection 1 (the criterion) — **CONCEDED, and it changes the answer**

Team-lead is right. I tested the wrong quantity. In a disturbance observer the error is the
**mismatch**, so a flat model against a varying plant is precisely how you *get* an
angle-dependent residual. Re-run with both curves normalised to their own flat value,
`M(θ)` = the firmware table / 1084, `R(θ)` = the rack curve from team-lead's pixel fractions:

**Residual LEVEL, `R(θ) − M(θ)` (lock = ±432°)** — this is what the observer actually sees:

| θ | plant `R` | model `M` | mismatch |
|---|---|---|---|
| **0°** | 0.575 | 0.829 | **−0.254** |
| **20°** | 0.575 | 0.834 | **−0.259** |
| **34°** | 0.603 | 0.838 | **−0.234** |
| 50° | 0.725 | 0.874 | −0.149 |
| 64° | 0.830 | 0.905 | −0.074 |
| 85° | 0.989 | 0.978 | +0.012 |
| ≥100° | 1.000 | 1.000 | ~0 |

⇒ **The mismatch is MAXIMAL AND FLAT across the centre band and decays to zero by ~85–100°.**
The model over-predicts the driver-torque term there by **0.829/0.575 = 1.44×**.

**Residual GRADIENT, `|dR/dθ − dM/dθ|`:** peaks at **28.8–33.9°** for lock 400–480° (the
floor→flank knee), with 80 % of the mismatch swing inside **32–84°**. ⚠ Sensitive to the lock
assumption — at lock = 500° the argmax jumps to 85.3°, because the plant's flank then extends
past where the model has already flattened. That knife-edge is a real weakness of this analysis.

**Engaged exposure [EVIDENCE, `cc_lat` ≥ 0.5, n = 14,289]:**

| band | r80 | r81 | r82 | **pooled** |
|---|---|---|---|---|
| centre floor 0–34° | 0.859 | 0.498 | 0.755 | **0.649** |
| flank 34–100° | 0.141 | 0.287 | 0.156 | **0.215** |
| plateau >100° | 0.000 | 0.215 | 0.089 | **0.137** |
| mismatch-gradient 32–84° | 0.164 | 0.280 | 0.168 | — |

⇒ **He spends 65 % of engaged time exactly where the mismatch LEVEL is largest**, and ~22 % where
its gradient is largest. **Under the correct criterion his observation is matched, not contradicted.**

## 7b. Objection 2 (the geometry) — **I cannot check the image, but I CAN check the scale**

🛑 **I was never given the rack image and there is none in the repo** (searched by name and by
extension). **I cannot verify team-lead's pixel measurements** — the 7 % / 20 % fractions and the
0.55–0.60 depth are taken on trust and every number in §7a inherits that.

**But the lock-to-lock assumption is checkable, and it was too high.** [EVIDENCE — all frames,
engaged or not]:

| route | all-frame max \|angle\| | p99.9 |
|---|---|---|
| r80 | 389.4° | 389.3° |
| r81 | **398.4°** | 398.1° |
| r82 | 387.7° | 387.7° |

p99.9 ≈ max on all three ⇒ **the wheel dwelt at a hard stop. Lock ≈ ±390–400°, not ±500°.**
(Lower bound is solid; that it is the mechanical stop rather than signal saturation is BELIEF.)

Re-deriving team-lead's fractions at lock = 400°: floor edge **28°**, flank outer **80°**.
Against the firmware's **34°** and **100°** — agreement to ~25 % on both edges. At lock = 500° it
was 35°/100° vs 34°/100°. **Either scale gives the same conclusion: the shapes align.**
**Team-lead's alignment claim survives the scale correction.** ⊕ Independent corroboration that
this table is a rack-position schedule: its own top breakpoint `X[12]` = **477.6°**, i.e. it is
laid out to span the full physical travel and a margin.

⇒ **Team-lead is right that the firmware is flat at centre BECAUSE THE RACK IS FLAT AT CENTRE.**
That is the notch floor, not an absence of compensation.

## 7c. The re-issued verdict

> **Right shape, right variable, reachable, RIGHT band — and UNDER-SCALED.** The firmware carries a
> real partial variable-ratio-rack compensation, aligned in shape and position with the mechanical
> curve, tracking only **31–37 % of it in log terms**. The residual model↔plant mismatch is
> **maximal and flat across the centre band (−0.25 normalised, a 1.44× over-prediction)**, decaying
> to zero by ~100°, and the operator spends **65 % of engaged time there**.

**Confidence:** the firmware side is EVIDENCE (bytes, assembly, flight data). The plant side is
**BELIEF resting entirely on team-lead's pixel reading of an image I have not seen** — if the
notch depth is not ~0.575, every mismatch number above scales with it.

---

# 8. THE SIGN — now resolved to EVIDENCE

`FUN_00038148` [decompile + `search_instructions`]:

```
iVar5 = (short)*(gp-0x6bfe) - (iVar4 >> 4);     // MODEL - ACTUAL, coefficients exactly ±1
```

Two independent facts put both arms in one frame:
1. **Unit coefficients.** MODEL and ACTUAL are differenced with no scaling on either side.
2. ⭐ **Both arms carry the SAME output-scale cal `0xC6468`** — `0x3b94a: ld.hu 0x7468,tp,r2`
   (MODEL, in `FUN_0003b8f6`) and `0x381f2: ld.hu 0x7468,tp,r16` (ACTUAL accumulator, in
   `FUN_00038148`). Only 5 reads of `0xC6468` exist image-wide; two of them are these.

`gp-0x374c`'s lanes (`gp-0x6b4e/6b4c/6b26/6b46/6bd0/6bbe`) are aggregator/motor-command domain.
⇒ **MODEL is motor-command-referred. [EVIDENCE]**

**Direction in that frame:** at centre the stroke ratio is low ⇒ more mechanical advantage ⇒ less
motor effort per unit driver torque ⇒ the gain *should* be **low at centre**. The firmware is
**899 = low at centre. The direction is correct.** [BELIEF on the physics — but note the direction
is **Honda's own calibration**, and they specified the rack. Claiming Honda inverted the direction
is a far stronger claim than claiming they scaled it partially.]

⇒ **The sign question dissolves. The open question is DEPTH only: the firmware under-compensates.**

---

# 9. 🛑 BUILD-DIRECTION INVERSION IN THE OBJECTION — must not reach a build script

Team-lead wrote: *"whether `0xC6B80` under-compensates (raise it) or over-compensates (the opposite)."*
**Raising `0xC6B80` is the wrong way for under-compensation.**

`0xC6B80` **is `Y[0]` = 899, the centre-floor knot.** The flat plateau is `Y[5..12]` = 1084.

```
swing = Y[flat] / Y[0] = 1084 / 899 = 1.206
raise Y[0]  899 -> 1000  =>  swing 1.084   FLATTER  = LESS compensation
lower Y[0]  899 ->  623  =>  swing 1.740   DEEPER   = MORE compensation (matches a 0.575 notch)
```

⇒ **To deepen the compensation you LOWER `0xC6B80`, toward ~623.** Raising it moves *away* from the
rack curve. Flagging because this is exactly the inversion class that produces a wrong-direction
build. **Still no build proposed** — and the dose above is arithmetic, not a recommendation.
