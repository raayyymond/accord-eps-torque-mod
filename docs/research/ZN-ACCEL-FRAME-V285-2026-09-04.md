# Ziegler–Nichols on the acceleration frame — is Kp = 0 closable, what is Ku, and does it beat candidate F?

Subagent `zn285`, 2026-09-04, reporting to `team-lead`/`main`. Answers the five questions in the
V285 brief. **ANALYSIS ONLY — nothing was built, no build script was edited, nothing was sent.**

**Image [EVIDENCE]:** `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
sha256 **`0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`**, 1,048,576 bytes, hashed by me.
Every firmware constant below is a **raw little-endian Python byte read of that file**. Structure came from
my own GhidraMCP `disassemble_bytes dry_run:true` on the V282 program (§0.2) plus the decompile-first
structure in `docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md`. `gp = 0xFEDF8000`, `tp = 0xBF000`;
`ld.hu 0x71b6,tp` → `0xC61B6`, anchored against the known 10240 before anything else was computed.

**Runnable mirror:** `analysis-2020accord/studies/zn285/zn_accel_frame.py` — reads the image itself; every
number here is its stdout (`analysis-2020accord/studies/zn285/_scratch_out.txt`).

---

## 0. HEADLINE — the five answers in one screen

1. 🛑 **Kp = 0 with Ki = 0 has ZERO steady-state authority. The plant is TYPE 0 in rate — a constant PID
   output produces a constant, bounded, NON-ZERO wheel rate — so `C(s) = Kd_r·s` gives `L(0) = 0`
   exactly and the integer mirror delivers 0.0 % of a 25 deg/s request at 4 s.** The car would not hold
   a curve. It is **not** unstable and not dangerous in the over-delivery direction; it is *inert* below
   ~1 Hz. **This is a Ku-hunt configuration, not a drivable one.** §1
2. ✅ **The loop is nevertheless perfectly closable at Kp = 0 — it is MORE stable, not less.**
   `|L(7.3 Hz)|` goes **0.976 → 0.843** and the 20 Hz damping budget `Re` goes **+2.06 → +2.59**. §1.4
3. **Q2 confirmed with small corrections.** The orchestrator's −89.7 % / −29.3 % / −9.9 % are right in
   shape; exact discrete values are **−89.7 % at 1 Hz, −30.3 % at 9.64 Hz, −12.1 % at 20 Hz**. §2
4. 🛑 **Q3: the phase premise is BACKWARDS and Ku is ~6× the estimate.** Removing P does **not** remove
   90° of lag — P is **phase-flat**, D is +86…+90°, so removing P **ADDS lead**: **+52° at 7.3 Hz,
   +25° at 20 Hz**. And **`Ku` (as a Kd cell value) = 859 pooled [673 r36 – 1072 r38], not 143–151;
   `Tu` = 137 ms at 7.3 Hz, not 49 ms.** The oscillation frequency does **not** move up: it is set by a
   plant resonance of Q ≈ 41, on which a 52° controller-phase change shifts `f0` by ≈ Δφ/2Q ≈ **1 %**. §3
5. 🛑 **Ku is NOT PHYSICALLY REACHABLE — the ±10240 D clamp bites first**, at Kd ≈ 845–1489 on the
   measured strong-turn frames, i.e. *inside* the Ku band. A Kd sweep would find a **clamp-limited limit
   cycle**, not a linear Ku. §3.3
6. **ZN translation, with the unit chain: `Kd = Kp'·8000`, `Kp = (Kp'/Ti)·256`, `0xC63E6 = 0`.**
   ZN-PID → **Kd 515, Kp 241**; ZN-PI → **Kd 387, Kp 108**. **ZN's Td has NO home in this firmware** —
   it is a second difference of `E` and the sum has exactly three addends (I verified the three `add`s
   myself). ⇒ **the reachable form is ZN-PI.** §3.4, §3.5
7. 🛑 **ZN's own answer makes the operator's live complaint worse.** ZN-PI's Kp 108 delivers **33 % of
   the requested rate** in steady state against V282's 53.5 % and V283's 96.6 %. **ZN is a stability
   recipe and understeer is a DC-authority problem; the two pull opposite ways.** With `0xC63E6` = 50
   left on, both ZN forms recover to ~97 % — but Ki is a *double* integral in the accel frame and no ZN
   form contains one. §3.6
8. ✅ **Q4 resolved, and the loop-shape study is right: candidate F (Kd 160) is FINE.** Kd 160 is not
   above Ku; at Kp 248 the upper root is **Kd ≈ 798**. Kd 160 sits **5× below it**. The orchestrator's
   Ku ≈ 146 comes from two errors: it read the measured `|L| = 0.976` as a **20 Hz** number when it is
   a **7.3 Hz** number, and it assumed `|L|` rises monotonically with Kd. It does not — the two arms sit
   ~123° apart, so **raising Kd shrinks the sum until the servo arm overtakes the r24 arm.** There is
   also a **LOWER** critical value: **Kd ≈ 118 at Kp 248**, i.e. today's 128 is only **8 % above the
   ring's re-arm point** — which independently reproduces the study's "a Kd cut is DO-NOT-FLASH". §4
9. ⭐ **Q5: Ku can be pinned with NO sweep and NO dose — and it already has been, from data on the
   wire today.** `|1−L| ≈ 1/Q` from the ring's ACF gives `|L_today|`; the simultaneous 427 T-tap and the
   r24 cave sign bit give the normalised arm split; Ku falls out in closed form. **Interval ±25 %,
   dominated by ROUTE-TO-ROUTE arm-split variation, not by the Q fit.** §5
10. ⭐ **The measurement worth building is NOT Ku.** Ku (859) is unreachable and nothing wants Kd that
    high. **The LOWER root — Kd ≈ 118 at Kp 248, Kd ≈ 65 at Kp 0 — is 8 % away and is the real gate.**
    Design `telem285` to resolve the arm split *per episode*, not to chase Ku. §5.4

---

## 0.1 What a FAIL looked like, written before the analysis

- Q1 FAIL: the wire shows a sustained PID output with a **ramping** rate (integrator) or a **zero**
  rate (differentiator). Neither occurred; four measured (|T|, rate) pairs give bounded non-zero rates.
- Q3 FAIL: Ku lands near the orchestrator's 143–151 and Tu near 49 ms. It does not.
- Q4 FAIL: candidate F is above Ku. It is not.

## 0.2 The cruxes I verified MYSELF, rather than relaying

**(a) The sum has exactly three addends — there is NO command feedforward and NO second difference.**
My own `disassemble_bytes dry_run:true` over `[0x29ED8, 0x29F40)` on the V282 program:

```
00029ee0  mov   r16, r8            ; r8 = E
00029ee2  sub   r27, r8            ; r8 = dE = E - E_prev        <-- the ONLY difference in the path
00029ee4  mul   r7, r8, r0         ; dE * Kd
00029ee8  ld.hu 0x71b6, tp, r10    ; D clamp = 0xC61B6 = 10240
00029eec  sar   0x3, r8            ; D = (dE*Kd) >> 3
  ... clamp to +-10240 ...
00029f18  sar   0x7, r2            ; r2 = Iterm = iacc >> 7
00029f1e  add   r9, r2             ; + P
00029f24  add   r8, r2             ; + D
00029f2a  mov   r2, r22            ; S = I + P + D      <-- THREE addends, nothing else
```
⇒ **`S = I + P + D` and no fourth term.** A ZN `Td` in the acceleration frame would need `d²E/dt²`;
there is exactly one difference operator in the whole function and one history cell (`gp-0x6cf8`).
[EVIDENCE — my own disassembly, tp arithmetic anchored on `0x71b6 → 0xC61B6 = 10240`.]

**(b) Every cal, byte-read by me from the V282 image** (not from a build script):

| cell | value | role |
|---|---|---|
| `0xC63E6` | **0** | Ki — **zero on V282** (50 only on V283) |
| `0xC63E8`/`EA` | 923 / 1560 | feedback EMA — exact pole **16.527 Hz**, DC **30.891** |
| `0xC63EC`/`EE` | 992 / 507 | output lag — exact pole **5.053 Hz**, DC **0.9902** |
| `0xC61B6` / `0xC61BC` / `0xC61BE` / `0xC61B4` | 10240 / 15360 / 15360 / 3072 | D / P / sum / output clamps |
| `0xC61BA` | 10240 | anti-windup base |
| `0xC6CD0` | 5346 | forward gain (0.16315) |
| `0xE5378` slot 7 | n=5, X `[0,68,112,136,208]`, Y `[248]×5` | **Kp flat 248** |
| `0xE511C` slot 7 | n=4, X `[0,11,22,32]`, Y `[128]×4` | **Kd flat 128** |

Exact `|D| = |P|` corner: **9.638 Hz**.

---

## 1. Q1 — IS THE Kp = 0 LOOP CLOSABLE? The plant's type, settled from the wire

### 1.1 The crux, stated as the brief states it

Does a constant PID output produce a constant **RATE** (plant ≈ static gain in rate ⇒ pure-D control
tracks with droop) or a constant **ANGLE** (plant ≈ differentiator in rate ⇒ pure-D control has zero
low-frequency authority)? **Neither hand-argument was needed: the car has already answered.**

### 1.2 The measurement — V281 rev 3 / V280 rev 2 stalled runs [EVIDENCE]

`HIGHANGLE-r35-V281R3-2026-09-03.md` records, in the "stalled push" row, sustained 1–3 s runs with a
**steady** tap `|T|` and a **steady, bounded, non-zero** wheel rate:

| route / stratum | `\|T\|` (counts) | wheel rate (deg/s) |
|---|---|---|
| r34 (V280 rev 2) idx 40–60 | 663 | 18.5 |
| r34 (V280 rev 2) idx 60–80 | 657 | 34.1 |
| r35 (V281 rev 3) idx 40–60 | 828 | 5.8 |
| r35 (V281 rev 3) idx 60–80 | 795 | 17.8 |

- **An integrator in rate is excluded**: a constant 795–828 counts held for 1–3 s would give a *ramping*
  rate, and the closed loop would have zero droop. The rate is bounded and the droop is large.
- **A differentiator in rate is excluded**: it would give **zero** rate under a sustained torque. The
  wheel is turning at 5.8–34.1 deg/s the whole time.

### 1.3 The DC chain closes with NO free parameter — an independent confirmation [EVIDENCE]

Reconstructing the *commanded* rate from `|T|` and the wheel rate alone, using only byte-read constants
(`|T| = (Kp/256)·(254/256)·0.9902·(5346/32768)·E = 0.15528·E`; `fb = 30.891 × 8 = 247.1` counts per deg/s):

| route / stratum | `\|T\|` | rate | `E = \|T\|/k` | `fb` | `32·sp` | **⇒ reconstructed ref** | plant `g` | `L_dc` |
|---|---|---|---|---|---|---|---|---|
| r34 idx 40–60 | 663 | 18.5 | 4270 | 4572 | 8842 | **35.8 deg/s** | 0.0279 | 1.07 |
| r34 idx 60–80 | 657 | 34.1 | 4231 | 8427 | 12658 | **51.2 deg/s** | 0.0519 | 1.99 |
| r35 idx 40–60 | 828 | 5.8 | 5332 | 1433 | 6766 | **27.4 deg/s** | 0.0070 | 0.27 |
| r35 idx 60–80 | 795 | 17.8 | 5120 | 4399 | 9519 | **38.5 deg/s** | 0.0224 | 0.86 |

The drive reads independently record those stall-run references as **r35 27 deg/s (mean)** and
**r34 30–44 deg/s**. Three of four land inside; the fourth (51.2) is the light-load row. **The chain
closes to a few percent without fitting anything** — which simultaneously confirms the 8 counts/deg/s
rate scaling, the 30.891 feedback DC gain, the 0.9902 lag DC gain and the `Kp/256` slope.

⇒ **VERDICT [EVIDENCE].** The plant from PID output to measured rate is **TYPE 0**: DC gain
`g = 0.007–0.052 deg/s per T count`, strongly load-dependent, **finite and non-zero**. Open-loop DC
return ratio `L_dc = 0.27–1.99`.

### 1.4 The consequence for Kp = 0

With `Kp = 0` and `Ki = 0` the controller is `C(s) = Kd_r·s`, so **`L(0) = 0` exactly** and the
steady-state rate error is **100 %**. Integer mirror, 25 deg/s request, mid-load plant
(`g = 0.030 deg/s/count`, τ = 60 ms), rate delivered at 4 s:

| build / tune | rate at 4 s | % of request | `\|T\|` |
|---|---|---|---|
| V282 as built (Kp 248, Kd 128, Ki 0) | 13.38 deg/s | **53.5 %** | 446 |
| V283 (Ki 50) | 24.16 deg/s | **96.6 %** | 806 |
| **Kp 0, Kd 128, Ki 0 (the Ku-hunt config)** | **0.00 deg/s** | **0.0 %** | **0** |
| Kp 0, Kd 859 (at Ku) | 0.00 deg/s | **0.0 %** | 0 |
| ZN-PI (Kp 108, Kd 387) | 8.35 deg/s | 33.4 % | 278 |
| ZN-PID (Kp 241, Kd 515) | 13.20 deg/s | 52.8 % | 440 |

**But the loop is not "unclosable" in the stability sense — it is MORE stable, by every gate we have:**

| metric | V282 as built | **Kp 0, Kd 128** |
|---|---|---|
| `\|L(7.3 Hz)\|`, pooled arms | 0.976 | **0.843** |
| `Re` @ 20 Hz (aggregator damping) | +2.06 | **+2.59** |
| loop phase change @ 13.5 Hz | 0° | **+34.7°** (margin RETURNED) |
| servo-arm gain @ 80 Hz | ×1.00 | **×0.96** |
| damping→pumping crossover | 61 Hz | **82 Hz** |

⇒ **ANSWER TO Q1.** *Closable — trivially, and with more margin than today.* **Drivable — no.** A
Kp = 0 / Ki = 0 image is **inert below ~1 Hz**: the only thing that reaches the motor is
`d(32·sp)/dt` — a kick on command *change*, nothing held. Lane keeping would not work; the operator
would be steering the car. It is not a "brick in behaviour" in the dangerous direction (it
under-delivers, and every stability metric improves), but it is a **Ku-hunt-only** configuration, and
the hunt would have to be flown on a road where the car not steering itself is acceptable.

⚠ **Residual [BELIEF, and the one I would most like checked].** The plant DC gain `g` varies **7.4×**
across the four measured strata (0.0070 → 0.0519). That is road load and tyre scrub, and it means
`L_dc` — and therefore the ZN answer — is **operating-point dependent by a factor of ~7 at DC**. The
7.3 Hz arm split varies only ~1.6× across routes, so the AC answer is far better conditioned than the
DC one. Any ZN tune is a tune for one load.

---

## 2. Q2 — authority loss from Kp → 0, exactly

`|C(Kp=0)| / |C(Kp=248)|`. **The output lag, the 254/256 taper, the 5346 forward gain, the feedback EMA
and the PLANT are common to P and D and cancel exactly in this ratio** — so this *is* the delivered-surface
ratio at every point downstream, not an approximation to it. V282 has Ki = 0, so `C = P + D` exactly.

| f (Hz) | `\|C\|` Kp 248 | ∠ | `\|C\|` Kp 0 | ∠ | ratio | **loss** | **Δphase** |
|---|---|---|---|---|---|---|---|
| 0.2 | 0.9690 | +1.2° | 0.0201 | +90.0° | 0.021 | **−97.9 %** | +88.8° |
| 0.5 | 0.9701 | +3.0° | 0.0503 | +89.9° | 0.052 | −94.8 % | +86.9° |
| **1** | 0.9743 | +5.9° | 0.1005 | +89.8° | 0.103 | **−89.7 %** | +83.9° |
| 2 | 0.9906 | +11.7° | 0.2011 | +89.6° | 0.203 | −79.7 % | +77.9° |
| 3 | 1.0173 | +17.2° | 0.3016 | +89.5° | 0.297 | −70.4 % | +72.2° |
| 5 | 1.0984 | +27.2° | 0.5026 | +89.1° | 0.458 | −54.2 % | +61.9° |
| **7.3** | 1.2286 | +36.7° | 0.7338 | +88.7° | 0.597 | **−40.3 %** | **+52.0°** |
| **9.638** | 1.3905 | +44.1° | 0.9686 | +88.3° | 0.697 | **−30.3 %** | +44.1° |
| 13.5 | 1.7002 | +52.9° | 1.3568 | +87.6° | 0.798 | −20.2 % | +34.7° |
| **20** | 2.2848 | +61.4° | 2.0093 | +86.4° | 0.879 | **−12.1 %** | **+25.0°** |
| 40 | 4.2424 | +69.7° | 4.0107 | +82.8° | 0.945 | −5.5 % | +13.1° |
| 100 | 10.2295 | +66.8° | 9.8885 | +72.0° | 0.967 | −3.3 % | +5.2° |

**Verdict on the brief's numbers.** −89.7 % at 1 Hz is **exact**. −29.3 % at 9.64 Hz should be
**−30.3 %** and −9.9 % at 20 Hz should be **−12.1 %** — the ±1–2 pp gap is the discrete D term's phase
deficit (`∠D = 90° − 180·f·T`, i.e. 86.4° at 20 Hz, not 90°), which makes P and D *less* than orthogonal
and so makes their vector sum slightly larger than the Pythagorean estimate.

🛑 **The phase column is the correction that matters.** The brief says removing P "removes ~90 deg of
lag from the forward path." **That is backwards.** In the rate frame **P is phase-flat (0°)** and
**D leads by 86–90°**. Removing the flat component rotates the controller **toward +90°** — it **adds**
lead: **+52° at 7.3 Hz, +34.7° at 13.5 Hz, +25° at 20 Hz.** This is the same mechanism the loop-shape
study found in the other direction (its §3: raising Kp *dilutes* the D lead and collapses `Re` from
+0.80 at Kp 248 to −0.07 at Kp 696). Kp → 0 is the maximum-lead end of that same axis.

---

## 3. Q3 — Ku, Tu, and the translation back into cells

### 3.1 Method — no dose, no sweep, on the measured arm split [EVIDENCE for the arms; BELIEF for the composition]

`STUTTER-7HZ-V283-r36-r38` §A13.1's composition rule, used unchanged:
`L_tot(cand) = L_tot(today) · |Ls·R + Lr|`, where `Ls + Lr ≡ 1` are the **normalised** ripple shares at
`f0` measured from the 427 T-tap and the r24 cave sign bit, and `R = C_cand·H_lag / (C_base·H_lag)` is
the servo arm's own ratio. **Only the servo arm carries Kp and Kd**, structurally (`P_raw = E·Kp/256`
and `D = dE·Kd>>3` are both inside `FUN_00028ea6`, upstream of `gp-0x6b38`; there is no Kp or Kd
anywhere in `FUN_0003aa2c`, which writes r24). The common plant path cancels in the ratio.

Measured arms at `f0 = 7.3 Hz`: **pooled `Ls 0.55∠+96°`, `Lr 1.19∠−27°`**; r36 `0.69∠+85° / 1.16∠−36°`;
r38 `0.42∠+95° / 1.12∠−22°`. Measured `|L_tot(today)| = **0.976 [0.944–0.990]**` (per-episode complex-ACF
fit, `|ρ(τ)| = exp(−α|τ|)`, `Q = π f0/α`, `|1−L| ≈ 1/Q`).

🛑 **CORRECTION TO THE BRIEF.** The brief states `0.976` is "at the ~20.3 Hz line". **It is not — it is
the 6–8.5 Hz strong-turn ring**, from `STUTTER-7HZ-V283-r36-r38-2026-09-03.md` §A13.4 and the loop-shape
study's §4.0 ("GATE 2a — the 7.3 Hz strong-turn ring"). **There is no measured `|L|` at 20 Hz at all**;
the 20 Hz mode is classified *driven, not self-sustained* (`GRINDING-DEEP` §2, net `Re > 0`), which
bounds it below 1 but does not measure it. This mis-attribution is the root of the Ku ≈ 146 estimate.

### 3.2 `|L(7.3 Hz)|` as Kd is swept, at Kp = 0 (the ZN Ku-hunt configuration)

| Kd | pooled | r36 | r38 | pooled @ `L`=0.990 | pooled @ `L`=0.944 |
|---|---|---|---|---|---|
| 0 | **1.161** | **1.132** | **1.093** | 1.178 | 1.123 |
| 32 | **1.082** | **1.032** | **1.033** | 1.097 | 1.046 |
| **64** | **1.002** | 0.933 | 0.973 | **1.016** | 0.969 |
| 96 | 0.922 | 0.834 | 0.914 | 0.935 | 0.892 |
| **128** | **0.843** | 0.735 | 0.854 | 0.855 | 0.815 |
| 160 | 0.763 | 0.636 | 0.795 | 0.774 | 0.738 |
| 256 | 0.526 | 0.348 | 0.619 | 0.533 | 0.508 |
| 400 | 0.185 | 0.191 | 0.372 | 0.188 | 0.179 |
| 500 | **0.139** *(minimum)* | 0.468 | 0.239 | 0.141 | 0.134 |
| 700 | 0.605 | **1.085** | 0.338 | 0.613 | 0.585 |
| **859** | **0.975** | 1.550 | 0.589 | **0.989** | 0.943 |
| 1000 | **1.351** | 2.023 | 0.865 | 1.371 | 1.307 |

**The curve is a V, not a ramp.** `Ls·R` and `Lr` sit ~123° apart (near anti-phase after the Kp = 0
rotation), so raising Kd first **cancels** the r24 arm, bottoms out near Kd ≈ 500, then grows past it.

**Roots of `|L(7.3)| = 1.000`:**

| arms | `L_tot` | **lower root (ring re-arms below)** | **upper root = Ku** |
|---|---|---|---|
| pooled | 0.976 | **Kd 65** | **Kd 859** |
| pooled | 0.944 | Kd 51 | Kd 873 |
| pooled | 0.990 | Kd 70 | Kd 853 |
| r36 (largest servo share) | 0.976 | Kd 42 | **Kd 673** |
| r38 (smallest servo share) | 0.976 | Kd 50 | **Kd 1072** |
| *(for reference)* Kp = 248 | 0.976 | **Kd 118** | **Kd 798** |

⇒ **`Ku` (expressed as the `0xE511C` cell value) = 859 pooled, [673 – 1072] across routes.**
The `L_tot` interval [0.944, 0.990] moves it only **853 – 873** — the dominant uncertainty is the
**route-to-route arm split (±25 %)**, not the ACF fit.

### 3.3 🛑 `Tu`, the crossover frequency, and why Ku is not physically reachable

**`Tu` = 1/7.3 Hz = 137 ms, not 49 ms.** The marginal-oscillation frequency is set by the plant's
lightly-damped ~7.3 Hz mode (the ring, `Q ≈ 41` pooled [17.7 – 96.8]), not by a controller crossover.
On a resonance of quality `Q`, a controller phase change `Δφ` moves the −180° crossing by
`Δf/f0 ≈ Δφ_rad / (2Q)`; here `Δφ = +52°` = 0.91 rad and `Q ≈ 41`, so **`Δf/f0 ≈ 1.1 %` — `f0` goes
7.30 → ≈ 7.38 Hz.** The crossover does **not** "move up" in any material sense. (At the pessimistic
`Q ≈ 17.7` it is still only ~2.6 %.)

🛑 **The D clamp bites before Ku does.** `|D|` measured on V283 strong-turn frames is **880–1552 counts
at Kd 128**, and `|D|` scales linearly in Kd against the byte-read `0xC61B6 = 10240` clamp:

| Kd | `\|D\|` lo | `\|D\|` hi | % of clamp |
|---|---|---|---|
| 128 | 880 | 1552 | 15 % |
| 400 | 2750 | 4850 | 47 % |
| 600 | 4125 | 7275 | 71 % |
| **798** (Ku at Kp 248) | 5486 | 9676 | **94 %** |
| **859** (Ku at Kp 0) | 5906 | **10415** | **102 % — RAILED** |

⇒ **the D path saturates at Kd ≈ 845 (worst frames) to 1489 (best frames), i.e. INSIDE the Ku band —
and this is at TODAY's ring amplitude, which grows as the loop approaches marginal stability.** A Kd
sweep therefore cannot produce a clean linear Ku; it produces a **clamp-limited limit cycle** whose
amplitude is set by `0xC61B6`, not by the loop gain. [EVIDENCE for the clamp and the linear scaling;
the measured `|D|` range is the record's.]

### 3.4 The unit chain, explicitly

Let `e_a = dE/dt` be the acceleration error in E-counts/s, so `E = ∫e_a dt`. The firmware sum
`S = Kp_r·E + Kd_r·dE/dt + Ki_r·∫E` re-reads as

```
S = Kd_r · e_a            <- accel-frame PROPORTIONAL   Kp' = Kd_r = (Kd/8)·T
  + Kp_r · ∫ e_a dt       <- accel-frame INTEGRAL       Ki' = Kp_r = Kp/256
  + Ki_r · ∫∫ e_a dt²     <- a DOUBLE integral. No ZN form contains one. Must be 0.
```
Inverting:
```
Kd  (0xE511C) = Kp' · 8/T = Kp' · 8000              (T = 1 ms, pinned three ways)
Kp  (0xE5378) = Ki' · 256 = (Kp'/Ti) · 256
Ti  as built  = Kd_r/Kp_r = (Kd/8)·T / (Kp/256) = 16.52 ms   ⇒ 1/(2π·Ti) = 9.64 Hz  ✓ the D=P corner
Ku' (accel-frame proportional gain at marginal stability) = (Kd_u/8)·T
```
🛑 **Everything else in the chain cancels.** The `>>8` on P, the `>>3` on D, the `×254>>8` taper, the
`32×` on `sp`, the output lag, the `5346>>15` forward gain and the feedback EMA all multiply P, D and I
**identically**, so none of them enters a ZN ratio. They set the loop's absolute scale — which is
exactly the thing `Ku` absorbs by being *measured*. This is why the ZN translation needs no scale
factor at all.

### 3.5 The ZN constants, in cells

`Ku' = (859/8)·0.001 = 0.10737 s`, `Tu = 137.0 ms`:

| form | rule | `Kp'` | `Ti` | **`Kd` (`0xE511C`)** | **`Kp` (`0xE5378`)** | `Td` |
|---|---|---|---|---|---|---|
| **ZN classic PID** | 0.6·Ku, Tu/2, Tu/8 | 0.06442 s | 68.5 ms | **515** | **241** | 17.1 ms → 🛑 **NO CELL EXISTS** |
| **ZN classic PI** | 0.45·Ku, Tu/1.2 | 0.04832 s | 114.2 ms | **387** | **108** | — |

Across the route spread: ZN-PID `Kd 404–643 / Kp 189–301`; ZN-PI `Kd 303–482 / Kp 85–135`.
**`0xC63E6` (Ki) must be 0 in both forms.**

🛑 **ZN's `Td` has no realisable home, confirmed from the bytes.** An accel-frame derivative is
`d(e_a)/dt = d²E/dt²` — a **second difference of E**. §0.2's disassembly shows exactly **one** difference
operator (`sub r27,r8` at `0x29EE2`), **one** history cell (`gp-0x6cf8`), and a sum with **exactly three
addends**. There is no cal that creates a second difference and no spare term to repurpose (the output
lag and the feedback EMA are lags, not leads). ⇒ **the reachable tune is ZN-PI, not ZN-PID.** [EVIDENCE]

### 3.6 🛑 What ZN's answer does to the operator's live complaint

| tune | `\|L(7.3)\|` | `Re`@20 | Δphase @13.5 | HF ×@80 Hz | **steady-state rate delivered** |
|---|---|---|---|---|---|
| V282 as built (248/128/0) | 0.979 | +2.06 | 0° | 1.00 | **53.5 %** |
| V283 (248/128/**50**) | 0.979 | +2.06 | 0° | 1.00 | **96.6 %** |
| **ZN-PI (108/387/0)** | **0.339** | **+4.79** | **+28.9°** | **×2.93** | 🛑 **33.4 %** |
| **ZN-PID (241/515/0)** | **0.531** | **+5.72** | **+25.0°** | **×3.91** | **52.8 %** |
| ZN-PI + Ki 50 | 0.339 | +4.79 | +28.9° | ×2.93 | 97.7 % |
| ZN-PID + Ki 50 | 0.531 | +5.72 | +25.0° | ×3.91 | 96.8 % |

**Both ZN tunes are enormously more stable than today** — `|L(7.3)|` falls to 0.34–0.53, `Re`@20 more
than doubles, and 25–29° of phase margin is returned at 13.5 Hz. **That is the whole benefit.**

**The cost is in two places:**
1. 🛑 **DC authority.** ZN-PI's `Kp 108` is *below* today's 248, and Kp is the **only** DC authority
   when Ki = 0. It delivers **33 % of the requested rate** against V282's 53.5 %. **The operator's
   headline complaint is prolific understeer. ZN-PI makes it substantially worse.** ZN-PID's Kp 241 is
   a wash with today. **ZN is a stability recipe; understeer is a DC-authority problem, and in this
   loop the two live on the same cell and pull opposite ways.**
2. ⚠ **HF gain into an unfiltered differentiator.** `D = (dE·Kd)>>3` is an ideal differentiator to
   Nyquist with no filter anywhere. ZN-PI carries **×2.93** of servo-arm gain flat from 25 Hz to
   500 Hz; ZN-PID **×3.91**. For comparison the loop-shape study capped its own blind-band constraint
   at ×1.15. **Neither ZN tune would pass that study's C4.**

**The resolution, if the operator wants ZN's shape and the car's authority: keep `0xC63E6 = 50`.**
It restores 97 % tracking under either form. But it is a **double integral in the accel frame** and no
ZN rule sizes one — it would be a Honda-frame fix bolted onto an accel-frame tune, and its stability
contribution would have to be checked separately (at 7.3 Hz the AC part of I is ~65 counts against
`|P|` ≈ 1900, i.e. **3 %**, so it is nearly free at the ring; that is the record's own §6 finding and
I reproduce it).

---

## 4. Q4 — the dispute with the loop-shape study. **The study is right; the Ku ≈ 146 estimate is wrong.**

**There is no contradiction.** At `Kp = 248` the upper root is **Kd ≈ 798**; candidate F's **Kd 160
sits 5× below it**. F is nowhere near Ku.

| candidate | Kp | Kd | ring ratio | `\|L\|`@0.976 | `Re`@20 | Δph@13.5 | HF×@80 | xover | rate % |
|---|---|---|---|---|---|---|---|---|---|
| V282 as built | 248 | 128 | 1.000 | 0.976 | +2.06 | 0° | 1.00 | 61 Hz | 53.5 % |
| **F: Kd 160** | 248 | 160 | **0.934** | **0.912** | **+2.37** | +5.6° | 1.24 | 66 Hz | 53.5 % |
| Kd 192 | 248 | 192 | 0.869 | 0.848 | +2.67 | +9.7° | 1.48 | 69 Hz | 53.5 % |
| 🛑 Kd 112 | 248 | 112 | **1.038** | **1.013** | +1.91 | −3.5° | 0.88 | 58 Hz | 53.5 % |
| 🛑 Kd 64 | 248 | 64 | **1.145** | **1.117** | +1.46 | −18.7° | 0.52 | **34 Hz** | 53.5 % |
| Kp 0 only | 0 | 128 | 0.863 | 0.843 | +2.59 | +34.7° | 0.96 | 82 Hz | **0.0 %** |
| Kp 0, at Ku | 0 | 859 | 1.024 | **1.000** | +9.45 | +34.7° | **6.47** | 82 Hz | **0.0 %** |
| ZN-PI | 108 | 387 | 0.347 | 0.339 | +4.79 | +28.9° | **2.93** | 79 Hz | **33.4 %** |
| ZN-PID | 241 | 515 | 0.544 | 0.531 | +5.72 | +25.0° | **3.91** | 77 Hz | 52.8 % |

**I reproduce the loop-shape study independently, to 2–4 %**: its F row reads ring 0.948 / `|L|` 0.910 /
`Re` +2.37; mine reads 0.934 / 0.912 / +2.37. Its Kd 112 reads 1.038 / 1.013; mine reads 1.038 / 1.013.
Its Kd 64 crossover reads 34.0 Hz; mine 34.2 Hz. (My "as built" ring computes to 1.003 rather than
1.000 because the published arms are rounded to 2 d.p.; every row carries the same 0.3 % offset.)

**Where Ku ≈ 146 came from, and why it fails:**
1. It read the measured `|L| = 0.976` as a **20 Hz** number. It is a **7.3 Hz** number (§3.1). There is
   no measured `|L|` at 20 Hz.
2. It assumed `|L|` **rises monotonically** with Kd, so that removing P (dropping `|L|` to ~0.88) had to
   be "restored" by ×1.12–1.18 of Kd. **`|L|` is a V in Kd, not a ramp** (§3.2). Between the lower root
   (65) and the minimum (≈500), **more Kd is more stable**, because the servo arm rotates to ~123° from
   the r24 arm and cancels it. This is the same geometry the study cites for why a Kd *cut* is
   DO-NOT-FLASH ("Shrinking and rotating `Ls` moves the sum *away* from unity in the direction that
   **increases** its magnitude").
3. It composed the phase argument with the wrong sign (§2): removing P adds lead, it does not remove lag.

⭐ **The finding the dispute exposes, which is worth more than the adjudication.** The lower root at
`Kp 248` is **Kd ≈ 118 [102 – 125] pooled**. **Today's Kd = 128 is only 8 % above the ring's re-arm
point.** The interesting critical value in this loop is **below** the shipping value, not above it.
Everything the record says about Kd cuts follows from that one number.

---

## 5. Q5 — ⭐ CAN Ku BE MEASURED WITHOUT A SWEEP? Yes — and it already has been.

### 5.1 The closed form

```
Ku (as a Kd cell value)  =  the Kd solving   |L_today| · | Ls·R(f0, Kp, Kd) + Lr |  =  1
```
Three inputs, all of them **already on the V282/V283 wire**:

| input | how it is obtained | status |
|---|---|---|
| **`f0`** | peak of the 6–8.5 Hz rate spectrum, per episode | on the wire (0x18F, 100 Hz) |
| **`\|L_today\|`** | ring sharpness: `\|1−L\| ≈ 1/Q`, `Q = π f0/α` from a per-episode complex-ACF fit `\|ρ(τ)\| = exp(−α\|τ\|)` | **measured: 0.976 [0.944–0.990]** |
| **`Ls`, `Lr`** | normalised ripple shares at `f0`: `Ls = zT/(zT+zr)`, `Lr = zr/(zT+zr)`, where `zT` is the **427 torque tap**'s phasor and `zr` the **r24 cave sign bit**'s | **both flown since V282** |
| **`R(f0,Kp,Kd)`** | closed form from the byte-read cals | this document |

⇒ **No dose, no sweep, no build.** This is the kit's own "prefer the inert tap to the blind dose" law
applied to a stability margin instead of a gain: the quantity is already computed and discarded, the
tap already exists, and every candidate Kd is sized offline from one drive.

### 5.2 How tight the interval is, and what dominates it

| source of uncertainty | Ku range | contribution |
|---|---|---|
| `\|L_today\|` over its full [0.944, 0.990] | **853 – 873** | **±1.2 %** |
| **arm split, route to route** (r36 0.69∠85° → r38 0.42∠95°) | **673 – 1072** | **±25 %** |

🛑 **The Q fit is NOT the limiting factor — the arm split is, by 20×.** And the arm-split spread is
**real physical variation** (servo share 0.42–0.69 across routes), not estimator noise. So:

- **Pooling is the wrong operation.** Ku is a property of an *operating point*, and the operating point
  moves. The estimate must be **per episode**, paired with that episode's own `Q`.
- Even so, the interval is **fit for purpose** for the decision actually on the table: every candidate
  anyone has proposed (Kd 112–192) is **3.5× to 10× below** the *lowest* route's Ku (673). The Ku
  question is not close.

### 5.3 What would make it fail

1. 🛑 **The composition rule is the load-bearing assumption, and it has already self-refuted once.**
   `L_tot = L_servo + L_r24` with *ripple shares taken as loop-gain shares* holds only if both lanes
   traverse the *same* remaining path. `STUTTER-7HZ` §A13.3 composed `oversteer283`'s measured absolutes
   under this rule and got `|L_tot| = 1.76`, which would be violently unstable against a measured
   `F7 = 0.00 per 100 s`. **That inconsistency is unresolved.** The *normalised* form used here is
   `s`-free and survives it, but the rule underneath is the same rule. [BELIEF, flagged]
2. **`|1−L| ≈ 1/Q` gives the DISTANCE from +1, not `|L|`.** Converting it to `|L| = 1 − 1/Q` assumes
   `∠L_today = 0`. So `|L_today|` is a **conservative lower bound on the margin**, which is what a gate
   wants — and Ku computed from it is correspondingly a **lower bound on Ku**, i.e. safe in the right
   direction.
3. 🛑 **Above Kd ≈ 845 the extrapolation is void** — the D clamp saturates (§3.3), so the *linear* Ku
   at 859 is a number the hardware cannot realise. Ku is a **bound**, not an attainable setting.
4. **A different mode could reach unity first, in the blind band.** The 427 tap is 50 Hz sampled
   (Nyquist 25 Hz) and the 0x18F streams are 100 Hz. Everything above ~25 Hz is unobservable. Kp = 0
   moves the servo lane's damping→pumping crossover **up** (61 → 82 Hz) and Kd raises push it up
   further, so the *direction* is safe; but the **magnitude** up there rises ∝ Kd through an
   **unfiltered** differentiator (×6.5 at Kd 859), and nothing on this car can see it.
5. **`Q ≈ 41` implies a sensitivity peak of ×42, which the operator describes as "a damped ring at
   ~40 %".** The loop-shape study flagged this gap and could not close it; nor can I. Carry `|L|` as the
   gate, do not convert it to a felt amplitude.

### 5.4 ⭐ What I would tell `telem285` — the highest-value output of this task

1. 🛑 **Do not instrument for Ku. Instrument for the LOWER root.** Ku (673–1072) is unreachable (D
   clamp) and nothing wants Kd anywhere near it. The **lower root — Kd ≈ 118 at Kp 248, Kd ≈ 42–65 at
   Kp 0 — is 8 % from the shipping value** and is the boundary any Kd edit actually approaches. Every
   DO-NOT-FLASH verdict in the record is about that root.
2. **The statistic to pre-register is the ring ratio `|Ls·R + Lr|`, per episode**, with its own `Q` from
   the same episode. Not a pooled route number, and not `|L|` converted into an amplitude.
3. **What has to be on the wire, simultaneously and in the same frames:** (a) the **427 torque tap**
   (already flown), (b) the **r24 lane phasor** — today only its **sign bit** at 0x14A b4.4 is
   published, which gives phase but **not magnitude**; the magnitude `s` is still a **closed-form
   estimate** over 0.30–0.52. **Publishing a magnitude channel for r24 is the single change that would
   remove the last estimated quantity in the whole framework.** (V282's `|r24| ≥ |T|` /
   `|r24| ≥ |aggregator|` comparator rungs already bound it; a graded rung would size it.)
4. **A Kp = 0 image is a legitimate but expensive way to reduce the arm-split uncertainty** — it rotates
   the servo arm ~52° and would test the composition rule hard (it predicts `|L(7.3)|` 0.976 → 0.843,
   `Re`@20 +2.06 → +2.59, and a **20 Hz creep line that gets BETTER, not worse**). But it costs a drive
   with no lane keeping. **The same rotation is available for free, offline, from data already
   collected**, which is why I do not recommend flying it.

---

## 6. What would falsify this document

- **The tick rate.** Everything scales with `T = 1 ms`. It is pinned three ways in `PID-FRAME` §1
  (no divider at the call site · two independent 1 kHz derivations for `FUN_0002214a` · the D clamp not
  being railed on the car). I did not re-derive it.
- **The 8 counts/deg/s rate scaling.** §1.3's reconstruction closing to a few percent is my evidence for
  it, and it is a *joint* test with the rest of the DC chain — if the scaling is wrong, the DC chain is
  wrong by the same factor and the reconstructed references would not have landed on the independently
  reported 27–44 deg/s.
- **The composition rule** (§5.3 item 1). If it is wrong, every Ku number here moves — though the
  *qualitative* result — that `|L|` is a V in Kd with the interesting root **below** 128, and that F is
  far from Ku — survives any monotone re-scaling of the arms.
- **The plant's type.** §1.2's four (|T|, rate) pairs are the whole basis. If those rows are not
  sustained-torque/sustained-rate windows but transients, the type argument weakens. The drive read
  describes them as 1–3 s runs, and the I-term's 2.5 s one-signed accumulation to 7004 counts on V283 is
  an independent witness that the error really is sustained.
- **`Q ≈ 41`.** A different `Q` moves `|L_today|` and therefore Ku by ±1.2 % (§5.2) — negligible.
