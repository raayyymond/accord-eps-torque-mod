# GATE 2 — the re-centred `FUN_000352b4` notch: SIGN VERDICT

**2026-08-20 · subagent · analysis only. Nothing built, flashed or sent on CAN. Ghidra read-only on
`code.bin` (stock).**

---

## 0. VERDICT, up front

🛑 **THE NOTCH IS BACKWARDS. DO NOT BUILD IT.**

Nulling `gp-0x6b86` at ~8 Hz does **not** remove assist from the loop. It removes a **cancelling**
term from a **measured 4:1 near-cancelling sum**, and the aggregator output at 6–9 Hz *grows*.

| quantity | value | grade |
|---|---|---|
| `Δ(u/T_s)` injected by the null | `+a·H_Honda` ≈ **`+0.98a ∠ −11°`** — positive-real, in phase with driver torque | **EVIDENCE** |
| loop-gain ratio `\|u_new\|/\|u_old\|`, **every** f in 6.00–9.50 Hz | **2.1× – 2.6×** (a≈0.10–0.12) · **3.4× – 4.6×** (a = 0.30 – 0.644) | **EVIDENCE** |
| `Re(ΔG·Z)` (first-order `Re(Z)` sensitivity) | **negative at every `a`** ⇒ **more anti-damping** | **EVIDENCE** for the sign; BELIEF for magnitude |
| predicted `ΔRe(Z)` | 4.1× – 27× the existing motor term, same sign ⇒ `Re(Z)` more negative | **BELIEF** |
| the same four cells pushed the **other** way (boost ×1.44–1.50) | `Re(ΔG·Z)` **positive**, `\|u\|` → **0.26×** | **BELIEF** |

**The orchestrator's sign convention was RIGHT (`+a`, not `−a`). Its baseline was WRONG:** the number
quoted as `u/T_s = 0.2075 ∠ +39.7°` is the **`gp-0x6b4c` LANE**, not the aggregator sum. The sum is
**`0.0528 ∠ +15.1°`**. That makes the correction 2–4× *larger* relative to the baseline than the
back-of-envelope assumed, not smaller.

---

## 1. The sign chain, end to end — from the firmware

### 1.1 `gp-0x4f60` → `gp-0x6b82` (the biquad's input)

`FUN_000352b4`, fresh decompile this session:

```python
#  0x354d2   T   = gp-0x4f60                                    # Sensor-B torsion-bar torque
#  0x354ce   Tc  = clamp(T, ±cal(0xC6200))                      # cal(0xC6200)=8192 (NEVER-EDIT cell)
#            Tc  = clamp(Tc + gp-0x6b4a, ±0x6400)               # gp-0x6b4a ≡ 0 today
#            m   = LERP_10pt(|Tc|)                              # X: gp-0x37fc[], Y: gp-0x37e8[]
#  0x355c6   gp-0x69a4 = slope_of_that_segment                  # ⇒ a ≡ gp-0x69a4/1024
#  0x355dc   ld.b -0x6752,gp,r7
#            gp-0x6b7a = min(m,0x2FFF) * sign(Tc) * pol         # pol = (char)gp-0x6752 = -1
#            ... friction-hold limiter stage ...
#  0x358b6   ld.b -0x6752,gp,r11
#            gp-0x6b82 = (limited magnitude) * sign(Tc) * pol   # ← THE BIQUAD'S INPUT TAP
```

**⇒ `∂(gp-0x6b82)/∂T = pol · a = −a` — NEGATIVE REAL.** [EVIDENCE]

`gp-0x6752 = −1` is not re-litigated here (verified three ways on record); what *is* established here
is **what it multiplies and where**: exactly two loads in `FUN_000352b4`, at `0x355dc` and `0x358b6`,
both applying `sign(Tc)·pol` to a positive magnitude.

### 1.2 The biquad — recursion recovered from the decompile

```python
#  gate:  cal(0xC649B)==1  and  cal(0xC64FA) <= gp-0x671a       # V103 arms it, engaged-only
#  c1,c2,c3,c4 = float32 @ tp+0x70a8/ac/b0/b4 = 0xC60A8/AC/B0/B4
w[n] = c4*u[n] - c1*w[n-1] - c2*w[n-2]        # x1=gp-0x3814=w[n-2], x2=gp-0x3818=w[n-1]
y[n] = w[n]    + c3*w[n-1] + w[n-2]           # leading/trailing numerator taps are bare adds = 1.0
y    = clamp(y, ±12.0);  iVar34 = round(y*1024)
```
⇒ `H(z) = c4·(1 + c3 z⁻¹ + z⁻²) / (1 + c1 z⁻¹ + c2 z⁻²)`, so `a1=c1, a2=c2, b1=c3, g=c4`, `fs = 1000 Hz`.

Stock bytes at `0xC60A8`, read from `code.bin` this session:
`f8 c2 c4 bf · 75 76 22 3f · 0e be f0 bf · 3a 3b 51 3f` = `−1.5372, 0.63462, −1.8808, 0.81731`
⇒ pole `|r| = 0.796630 @ 42.345 Hz`, zero `|r| = 1.000000 @ 55.225 Hz`, DC 1.000034,
peak `|H|` 0.1–500 Hz = **+0.0003 dB**. Response at 6/7.79/9 Hz: `−0.088 / −0.149 / −0.201 dB`,
`−8.1 / −10.6 / −12.3°`. **The biquad is ~transparent in 6–9 Hz as flown on V103.**

### 1.3 `gp-0x6b86` → the aggregator

```python
gp-0x6b86 = clamp( H(z)·[gp-0x6b82]  +  gp-0x6b7e , ±0x3000 )      # 0 if |gp-0x4f60| > 25600
#  gp-0x6b7e = (gp-0x381c EMA, α = 20/2048, corner 1.56 Hz) of the residual gp-0x6b84 — NOT filtered
```
**The biquad filters `gp-0x6b82` ONLY.** ⇒ `Δ(gp-0x6b86) = (H_new − H_old)·gp-0x6b82` exactly.

`FUN_0003aa2c`, fresh decompile + instruction scan for `-0x6752` (**exactly ONE load in the whole
function, at `0x3ab78`, register-shared by the r24 and r26 terms**):

```python
u = gp-0x6b94 = clamp( FUN_00036682()
      + gp-0x6ade ·zr(±1024)   + gp-0x6b4c ·zr(±10240) + gp-0x6ad4 ·zr(±10240)
      + gp-0x6b62 ·zr(±8192)   + gp-0x6b26 ·zr(±1024)  + gp-0x6bbe ·zr(±2048)
      + gp-0x6bd0 ·zr(±2048)   + gp-0x6b86 ·zr(±12288)
      + clamp(pol * X_r26, ±0x2000)      # → gp-0x6adc  (r26)
      + clamp(pol * X_r24, ±0x2000)      # → gp-0x6ada  (r24)
      , ±0x2800 )                        # SATURATING (the lane gates are zero-REJECT)
```

### 1.4 The lane sign map — **who carries `pol`**

| lane | carries `pol` | where | structural phase vs `T` at 6–9 Hz |
|---|---|---|---|
| `gp-0x6b86` (base assist / friction) | **YES** | upstream, `FUN_000352b4` @`0x358b6` | **180°** (`−a`, real negative) |
| `r24` = `gp-0x6ada` | **YES** | aggregator @`0x3ab78` | **−90°** (`pol × dT/dt`) |
| `r26` = `gp-0x6adc` | **YES** | aggregator @`0x3ab78` | **−90°** (`pol × dT/dt × a`) |
| `gp-0x6b4c` (11-slot assist demand) | **NO** | bare `+` | measured **+41.4°** |
| `gp-0x6bbe`, `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6b62`, `gp-0x6ade`, `gp-0x6bd0` | **NO** | bare `+` | small / zero |

`gp-0x4f62` is the **torque derivative**, confirmed by decompiling its sole writer `FUN_0007e74a`:
`gp-0x4f62 = ((T[n] − T[n−N]) << 1) / Δticks`, `N = cal(0xC6C42) = 4`. r24's deadband
`cal(0xC61F6) = 3` counts — essentially always open. ⇒ r24/r26 are clean `pol × jω` lanes.

### 1.5 🛑 The wire↔firmware sign `s` — PINNED, `s = +1`

This is the hinge the orchestrator flagged. Three independent legs:

1. **Firmware packer** `FUN_00055c42` @`0x55c50`: `CAN 0x18F byte0-1 = −(gp-0x4f60 × 125/128)`.
2. **DBC**: `STEER_TORQUE_SENSOR` bytes 0-1 BE signed, **scale −1.0**.
3. **Extractor**: `extract_r29_cache.py` and the whole `extract_r7d` chain apply `× −1.0` to the raw
   BE int16 (`v86_probe_consolidate.py` PROV block states it explicitly).

⇒ `tq = −(raw BE) = +0.9766 × gp-0x4f60` ⇒ **`T^fw = +1.024 · tq`, `s = +1`.** [EVIDENCE]

Cross-check, independent and empirical: the r24 sign bit `v103_b4` (`gp-0x6ada < 0`) against `tq`.
`sign(gp-0x6ada) = pol·sign(dT^fw/dt)`. Band-limited `tq → sgn(r24)` at 0.3–3 Hz gives phase
**−92.3°**, i.e. `sgn(r24) ∝ −s·jω·tq` with `−s < 0` ⇒ `s = +1`. ✓
⚠ A raw finite-difference sign-agreement test on the same pair gives the **opposite** answer
(0.35–0.46 agreement at spans 2–8). That test is **VOID**: `gp-0x4f62` is a 4 ms derivative sampled
by CAN at 100 Hz, so its sign stream aliases badly. The band-limited estimate is the valid one, and it
agrees with the three-leg firmware chain. Recorded so nobody re-runs the broken version.

⚠ Operator-confirmed frame convention (negative driver torque + negative angle = right turn; +LKAS
demands negative angle) enters **only** as a consistency check on `κ`'s sign, below. It is not load-
bearing for the verdict; leg 1–3 above are.

### 1.6 `κ` — the motor-command frame

For the base assist to *assist*, `κ·(pol·a·T)` must push the pinion the way the driver is pushing.
With `pol·a·T = −a·T`, that forces **`κ < 0`**: the motor-command frame is opposite to the torque
sensor. Equivalent to the operator's "LKAS and driver torque are in opposite frames". [EVIDENCE, by
necessity from §1.1.]

---

## 2. The complex lane budget at 6–9 Hz — MEASURED

Method (frozen): 4 s Hann windows, 50 % overlap, detrended, Welch-summed **inside engaged episodes
only** (`cc_lat`); band estimate `H = Σ_band S_xy / Σ_band S_xx`; **CI = bootstrap over EPISODES**.
`x` = `tq`, `y` = the 427 channel.

### 2.1 Four builds, two 427 targets

| route | build | 427 packs | `\|H\|` | phase | `coh²` | band-RMS ratio [CI] | eps |
|---|---|---|---|---|---|---|---|
| `0x85` | V100 (4×) | `gp-0x6b94` **SUM** | 0.0485 | **+17.0°** | 0.249 | 0.0948 [0.0632, 0.1036] | 2 |
| `0x95` | V101 (8×) | `gp-0x6b94` **SUM** | 0.0572 | **+13.6°** | 0.411 | 0.0774 [0.0745, 0.0902] | 3 |
| `0x96` | V102 (6×) | `gp-0x6b4c` **LANE** | 0.1897 | **+43.5°** | 0.652 | 0.2131 [0.2104, 0.2366] | 8 |
| `0x9e` | V103 (6×) | `gp-0x6b4c` **LANE** | 0.2068 | **+39.5°** | 0.825 | 0.2200 [0.2029, 0.2482] | 6 |

**Positive controls.** The band-RMS ratios reproduce the sibling's 0.0946 (sum) and 0.2117 / 0.2202
(lane) to 3 s.f., independently. Episode-swap surrogates: r9e lane real `|H| = 0.2068` vs surrogate
median 0.021 / p95 0.148; r85 sum real 0.0485 vs surrogate 0.0004. ⚠ The r85 surrogate is degenerate
(2 episodes ⇒ one possible permutation) — it is a single realisation, not a distribution.

🛑 **The number the brief quotes as `u/T_s = 0.2075 ∠ +39.7°`, coh² 0.888, CI [+35.3,+41.3]° is the
LANE.** My lane figure is `0.2068 ∠ +39.5°`, coh² 0.825, CI [+35.5,+41.3]° — the same computation.
The brief's own sum figure (0.0946, coh² 0.279) cannot be the same quantity.

### 2.2 The budget closes

Pooled: `u/T_s = 0.0528 ∠ +15.1°` · `gp-0x6b4c/T_s = 0.1982 ∠ +41.4°`.

```
RESIDUAL (all lanes except gp-0x6b4c) = sum − lane = 0.1527 ∠ −129.8°
                                       = −0.0980 − j0.1173
```

🛑 **The lane and the residual are 171.2° apart — near-perfect anti-phase. That is the cancellation,
measured with PHASE for the first time, and replicated across four builds.**

Decompose the residual using only the **structural** phases from §1.4 (the only real-valued lane at
6–9 Hz is `gp-0x6b86` at 180°; r24/r26 are at −90°):

| term | value / `T_s` | counts (at `\|T_s\|` = 396.4) | source |
|---|---|---|---|
| `gp-0x6b4c` | 0.1982 ∠ +41.4° | 78.6 | **measured** |
| `gp-0x6b86` | **0.0980 ∠ 180°** ⇒ **`a = 0.098`** | **38.8** | solved from Re(residual) |
| `r24 + r26 (+ 6bbe)` | 0.1173 ∠ −89.9° | **46.5** | solved from Im(residual) |
| `gp-0x6b62`, `gp-0x6ade`, `gp-0x6bd0` | 0 | 0 | on record |
| **Σ = `u`** | **0.0528 ∠ +15.1°** | **20.9** | **measured** |

**The closure is not circular in the interesting place**: it is a 2-equation solve, and it returns
`|r24+r26| = 46.5 ct` — squarely inside the brief's independently-supplied `r24 ≈ 40–61 ct` — and an
`a` inside its own `(0, 2.0]` range. [EVIDENCE-grade *inference*; BELIEF that no other lane carries
significant 6–9 Hz content.]

🛑 **`a ≈ 0.10` (0.098 from the 4-build pool; 0.117 from r9e alone), NOT 0.644.** At `a = 0.644`,
`|gp-0x6b86|` alone would be 255 ct — 12× the whole sum and 3× the biggest measured lane — requiring
an unmeasured ~250 ct lane at ∠−11° to cancel it. No candidate exists: the remaining lanes' windows
are ±1024 / ±2048, and `gp-0x6ad4` (±10240) is a torque *derivative* lane (∠±90°), which cannot
cancel a real term.

### 2.3 Cross-build caveat, and why it survives

Sum and lane come from different builds with different LKAS forward gains. **But doubling the LKAS
gain (V100 4× → V101 8×) moved the sum's 6–9 Hz transfer only 0.0485 → 0.0572 (+18 %)**, and the lane
is 0.190 / 0.207 at the *same* 6× on two builds. ⇒ the 6–9 Hz content is not LKAS-driven and the
cross-build pooling is defensible. It is still the single largest weakness in the chain.

⚠ **7 episodes (r9e) / 6 usable ≥2.5 s, 3 (r95), 2 (r85) is the hard limit on every CI here.**

---

## 3. Does the notch help or hurt?

### 3.1 Model-free: the loop gain

`Δu = (H_new − H_old)·gp-0x6b82`, `gp-0x6b82/T = −a`. At the null `H_new(f₀) = 0`:

```
Δ(u/T) = (0 − H_Honda)·(−a) = + a · H_Honda ≈ +0.98a ∠ −11°      ← POSITIVE REAL
```

Full sweep, `f₀ = 8.05 Hz`, `r = 0.990`, baseline = V103 (biquad armed with Honda's coefficients):

| f (Hz) | `H_new` dB | `Δ(u/T)` | `u_V103/T` | `u_new/T` | ratio (a=0.098) | ratio (a=0.644) |
|---|---|---|---|---|---|---|
| 6.00 | −1.78 | 0.065 ∠+23° | 0.0597 ∠+27° | 0.124 ∠+25° | **2.08×** | 4.34× |
| 7.00 | −4.92 | 0.081 ∠ +7° | 0.0613 ∠+29° | 0.140 ∠+17° | **2.28×** | 4.56× |
| 8.00 | −29.8 | 0.096 ∠−10° | 0.0632 ∠+30° | 0.149 ∠ +6° | **2.37×** | 4.54× |
| 8.50 | −11.1 | 0.101 ∠−19° | 0.0641 ∠+31° | 0.151 ∠ +0° | **2.35×** | 4.43× |
| 9.50 | −3.16 | 0.108 ∠−35° | 0.0661 ∠+32° | 0.147 ∠−10° | **2.22×** | 4.03× |

🛑 **There is NO frequency in 6.00–9.50 Hz where the notch reduces the 6–9 Hz loop gain.** `Re(u/T)`
increases monotonically by +0.06 to +0.63 across the band. The effect is **not** confined to the null.

### 3.2 Direction of `Re(Z)`

`Re(Z)` measured on r9e (`Z = S_wT/S_ww`, `w = rate_f` rad/s, `T = tq` counts, engaged, 6 episodes):

| band | `Re(Z)` [CI] | `Im(Z)` [CI] | `\|Z\|` | `arg(Z)` | coh² |
|---|---|---|---|---|---|
| 2–4 | +1285 [−99,+2269] | −568 | 1405 | −23.9° | 0.43 |
| 4–6 | +899 [−607,+1683] | −2239 | 2413 | −68.1° | 0.60 |
| **6–9** | **−3762 [−4520,−2610]** | **−5752 [−6150,−4993]** | **6873** | **−123.2°** | **0.84** |
| 9–13 | −4885 | −671 | 4931 | −172.2° | 0.43 |
| 15–22 | −440 | +1307 | 1379 | +108.6° | 0.92 |
| 22–26 | −138 | +1160 | 1168 | +96.8° | 0.96 |

(`Re(Z)` at 6–9 Hz reproduces the record's −3639 [−4324,−3114]. `|Z|` **peaks** at 6–9 Hz.)

First-order sensitivity (the kit's own pricing form, `ΔRe(Z) ∝ Re(ΔG·Z)`):

| perturbation | `ΔG` | `Re(ΔG·Z)` | vs existing motor term `Re(G·Z) = −112.7` | direction |
|---|---|---|---|---|
| **NULL (the proposed notch)**, a=0.098 | 0.096 ∠ −11° | **−461** | **4.1×, same sign** | **more anti-damping — WORSE** |
| NULL, a=0.117 | 0.115 ∠ −11° | −550 | 4.9×, same sign | WORSE |
| NULL, a=0.644 | 0.632 ∠ −11° | −3028 | 26.9×, same sign | WORSE |
| BOOST ×1.44, a=0.098 | 0.042 ∠ +169° | **+203** | opposite sign | **less anti-damping — BETTER** |
| BOOST ×1.50, a=0.098 | 0.048 ∠ +169° | +230 | opposite sign | BETTER |

**Robustness of the sign.** `Re(ΔG·Z) < 0` requires `arg(ΔG) + arg(Z)` outside ±90°. `arg(ΔG) = −11°`
is fixed by the decompiled sign chain; `arg(Z) = −123.2°`, and the episode bootstrap gives
`arg(Z) ∈ [−117.6°, −126.3°]`. The sign flips only for `arg(Z) > −79.4°` — **far outside the CI.**

### 3.3 🛑 What I could NOT compute — and it matters

The exact closed-loop result is `ΔRe(Z) = |κ|·Re(ΔG·Z/A)`, `A = 1 + κG`. §3.2 uses `A ≈ 1`.

**I tried to identify the plant and it FAILED.** Fitting `Z(f)·(1 − κG(f)) = b + jωJ` over nine bands
on route 0x85 (the only route where the 427 lane *is* `u`) returns `κ = 3.54∠+80°`, `b = −408`
(non-physical), `J = 0.05`, and residuals of 3–15× — the model is falsified, not merely imprecise.

Worse, the measured `|Z|` **peak** at 6–9 Hz is itself evidence that `|κG| ≈ 1` there (a minimum of
`|A|`), i.e. **the 8 Hz mode may be the assist loop's own near-instability rather than a passive
mechanical resonance**. If so `1/A` is large with an ill-conditioned phase, and a 2–4× step in `G` is
an excursion of unpredictable direction and large size. Either way:

**⇒ GATE 2 cannot be passed. A 2.1–4.6× step in the open-loop gain at a mode with measured Q = 10.21
(ζ = 0.049), whose closed-loop sign I cannot certify, is not a calibration trim.**

---

## 4. Centre and `r` — the numbers, conditional on overruling §0

`f_n` = 8.162 Hz, CI [8.015, 8.187]; exogenous estimator 8.123; 0–5 m/s bin 7.95 (the grinding
regime). Mode bandwidth `f/Q` = 0.80 Hz. Design was cut at 7.79 Hz — **stale, and below every current
estimate.**

**RECOMMEND `f₀ = 8.05 Hz` (covers 7.95 and the whole CI), `r = 0.990`.**

Trade table (co-located pole/zero, all four cells moving together, `fs = 1000 Hz`):

| f₀ | r | peak \|H\| 0.1–500 Hz | −3 dB BW | atten @6/7/8/8.5/9 Hz | τ_ring |
|---|---|---|---|---|---|
| 8.05 | 0.960 | +4.36 dB @500 | 6.88 Hz | −6.9 / −12.3 / −38.6 / −19.5 / −13.0 | 24.5 ms |
| 8.05 | 0.975 | +1.94 dB @500 | 5.82 Hz | −5.3 / −10.3 / −36.5 / −17.4 / −11.1 | 39.5 ms |
| 8.05 | 0.985 | +0.74 dB @500 | 4.20 Hz | −3.1 / −7.3 / −33.0 / −14.1 / −8.0 | 66.2 ms |
| **8.05** | **0.990** | **+0.34 dB @500** | **3.00 Hz** | **−1.8 / −4.9 / −29.8 / −11.1 / −5.5** | **99.5 ms** |
| 8.05 | 0.995 | +0.09 dB @500 | 1.57 Hz | −0.5 / −1.9 / −24.0 / −6.1 / −2.2 | 199.5 ms |

Why 0.990: BW 3.00 Hz spans ≈[6.6, 9.6] — covers the CI, the low-speed bin and mode drift with hand
inertia; peak `|H|` is only **+0.34 dB** and it is a flat HF shelf (+0.26 dB at 21 Hz, +0.28 at 23,
+0.29 at 26), so it does **not** lift the 21–26 Hz vibration band materially. `r = 0.975` would put
**+1.94 dB** of broadband lift on the base-assist lane — unacceptable given the 8× / ~23 Hz carrier
result. ⚠ **Residual GATE-3 flag: τ_ring 99.5 ms vs Honda's 4.40 ms (23×).**

### Bytes — `f₀ = 8.05 Hz, r = 0.990`, IEEE-754 float32, little-endian

| address | coeff | value (float32) | LE bytes |
|---|---|---|---|
| `0xC60A8` | `c1 = a1 = −2r·cos ω₀` | `−1.977467775` | **`aa 1d fd bf`** |
| `0xC60AC` | `c2 = a2 = r²` | `+0.980099976` | **`d5 e7 7a 3f`** |
| `0xC60B0` | `c3 = b1 = −2·cos ω₀` | `−1.997442245` | **`30 ac ff bf`** |
| `0xC60B4` | `c4 = g` | `+1.029096842` | **`72 b9 83 3f`** |

Verified from the float32 round-trip: poles `0.98873389 ± 0.05005273j`, `|r| = 0.990000` @ **8.0500 Hz**;
zeros `0.99872112 ± 0.05055808j`, `|r| = 1.000000` @ **8.0500 Hz**; DC gain **0.999991**;
peak `|H|` over 0.1–500 Hz = **+0.3362 dB @ 500 Hz**.

**Encoder positive controls (both PASSED):**
1. Encoding Honda's own `(−1.5372, 0.63462, −1.8808, 0.81731)` gives
   `f8 c2 c4 bf 75 76 22 3f 0e be f0 bf 3a 3b 51 3f` — **byte-identical to `read_memory(0xC60A8,16)`
   on stock `code.bin`.**
2. My `coeffs(7.79, 0.990)` reproduces the kit's own recorded design bytes
   `0xC60A8 = f0 22 fd bf`, `0xC60AC = d5 e7 7a 3f`, `0xC60B0 = 83 b1 ff bf` **exactly.**

---

## 5. Escape hatches, ranked

Optimal removal fraction `ε*` minimising `|u − ε·L|` at 6–9 Hz, from the measured budget:

| lane `L` | `ε*` | `\|u\|` at `ε*` | `\|u\|` at `ε = 1` (full null) |
|---|---|---|---|
| `gp-0x6b4c` | **+0.239** | 0.0234 (**0.44×**) | 0.1527 (**2.89×**) |
| `gp-0x6b86` | **−0.520** (⇒ **boost ×1.52**) | 0.0138 (**0.26×**) | 0.1496 (**2.83×**) |
| r24 + r26 | −0.116 | 0.0510 (0.97×) | 0.1405 (2.66×) |

🛑 **Every full single-lane null at 6–9 Hz is a 2.5–2.9× step. That is a general design law for this
firmware, not a property of this lever:** the aggregator at 6–9 Hz is a 4:1 cancellation, so **any**
single-lane perturbation is amplified ~4× at the output. Size levers against the **sum** (0.053),
never against a lane.

**Ranking:**

1. **Active damping `−K·φ′` on the torsion-bar rate (the V105 candidate) — BEST.** It targets `Re(Z)`
   directly, its only bad failure mode is a wrong sign (pre-registerable, readable from one drive),
   and the 4× cancellation amplification means a *small* `K` suffices. 🛑 **Size `K` against `u` =
   0.053, not against a lane — a lane-sized dose would be ~4× over.**
2. **Boost `gp-0x6b86` at 8 Hz by ×1.44–1.52 — the same four cells, opposite direction.** Both
   criteria agree it is favourable (`|u|` → 0.26×; `Re(ΔG·Z)` positive). ⚠ **NOT a build
   recommendation**: it needs a pole-dominant retune whose numerator zero must be parked elsewhere
   (the "+30 dB peak" hazard), the optimum is a knife edge (past ~×3 it is worse than baseline), and it
   rests on a cross-build phase with 2–3 episodes on the sum side. **Worth a dedicated measurement
   before a build.**
3. **Trim `gp-0x6b4c` by ~24 %** — the measured minimiser (0.44×). Not buildable: that lane is
   algebraically flat (`FUN_00026c80`, no filter to retune) and >48 % attenuation is worse than
   baseline.
4. **Shallower notch (larger `r`)** — DEAD as a dose control. The numerator `z² + c3 z + 1` has root
   product 1, so whenever the roots are complex the zeros sit **exactly on the unit circle**: the
   depth is `−∞` by construction. `r` sets only the *width*. There is no "partial notch" in this
   structure.
5. **Phase-lead** — DEAD, and backwards. `Re(ΔG·Z) > 0` needs `arg(ΔG) ∈ (+33°, +213°)`. The lane sits
   at ∠169° (inside); a **+60° lead** rotates `ΔG` to ∠−71° (outside ⇒ worse). A **lag** would be
   favourable — but the biquad only produces lag together with the null.
6. **The re-centred notch as specified** — DEAD. §3.

---

## 6. What I could not compute

- **`ΔRe(Z)` in calibrated units.** Needs `|κ|` (torsion-bar counts per aggregator count at 6–9 Hz).
  The plant identification failed (§3.3). Only the **direction** is established, under `A ≈ 1`.
- **Whether `|κG| ≈ 1` at 8 Hz** (i.e. whether the 8 Hz mode is the assist loop's own near-instability).
  The `|Z|` peak is suggestive; it is not proof. **This is the single most valuable open question here** —
  it decides whether *any* 6–9 Hz lever is controllable. It needs a route where the 427 lane packs `u`
  **and** enough engaged episodes for a real CI (route 0x85 gave 2).
- **`a` from the firmware directly.** The 10-point map is built at runtime into `gp-0x37fc[]`/`gp-0x37e8[]`
  from RAM sources `gp-0x6444…−0x641e`; I did not trace the mode-record loader that fills them.
  `a ≈ 0.098` here is *solved from the budget*, not read from a table.
- **`gp-0x6b4c`'s internal make-up at 6–9 Hz.** coh²(T, lane) = 0.65–0.83 says it is torque-coherent —
  so at least one of its 7 live slots is assist-like — but which slot is untraced.
- **A phase for the sum with a real CI.** 2 episodes (r85) / 3 (r95).
