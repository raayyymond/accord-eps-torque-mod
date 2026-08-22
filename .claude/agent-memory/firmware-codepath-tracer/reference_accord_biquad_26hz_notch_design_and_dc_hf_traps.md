---
name: reference_accord_biquad_26hz_notch_design_and_dc_hf_traps
description: "Honda's FUN_000352b4 biquad CAN be retuned to a true 26 Hz notch at unity DC as a PURE CAL EDIT (16 bytes, 4 float32 cells, zero blast radius, no cave). Records the solved coefficient set, the two traps that make the obvious construction WRONG (DC collapse 4.48x, and an HF BOOST at 42.3 Hz forced by fixing DC with poles-at-the-notch), the fix (poles BELOW zeros, Honda's own pattern), and that V103 -- not V104 -- is the single-variable base."
metadata:
  type: reference
---

# Retuning Honda's biquad to a 26 Hz notch — solved, with the two traps

Designed 2026-08-22. Program: stock `code.bin` + `_v103_*` / `_v104_*` plain images. All numbers computed
from the coefficients and cross-checked by reproducing stock exactly.

## The section
`H(z) = c4·(1 + b1·z⁻¹ + z⁻²) / (1 + a1·z⁻¹ + a2·z⁻²)` at **fs = 1000 Hz**, in `FUN_000352b4`.
Signal path `gp-0x6b82` → biquad → `gp-0x6b86` → aggregator → motor ⇒ **it is INSIDE the loop.**

| cell | addr | stock | the ONE reader |
|---|---|---|---|
| `a1` | `0xC60A8` | −1.537200 | `0x035A40` |
| `a2` | `0xC60AC` | +0.634620 | `0x035A44` |
| `b1` | `0xC60B0` | −1.880800 | `0x035A58` |
| `c4` | `0xC60B4` | +0.817310 | `0x035A30` |

**Stock reproduces exactly:** zeros **|z| = 1.000000 @ 55.2254 Hz**, poles **r = 0.796630 @ 42.3451 Hz**,
**H(0) = 1.000034**, 99% ring **20.2 ms**, and **max |H| = 1.0000 — stock never boosts anywhere.**

### 🛑 BLAST RADIUS: ZERO. Two methods.
Each cell: **exactly ONE access, ZERO writers**, all four reads inside a **40-byte window
`0x035A30`–`0x035A58`**. Second method: **no `movea`/`movhi` anywhere forms imm16 `0x60A8`/`0x60AC`/
`0x60B0`/`0x60B4` (0 hits each)** ⇒ nothing reaches them by absolute addressing either. **EVIDENCE.**

## The structural constraint — and it is a GIFT, not an obstacle
The end taps are hardcoded `addf.s` with no multiply ⇒ **`b0 ≡ b2 ≡ c4`**, so the numerator is forced
**palindromic**. `z² + b1·z + 1 = 0` ⇒ product of roots ≡ 1 ⇒ for |b1| < 2 the zeros are a conjugate pair
of **modulus exactly 1**. ⇒ **a TRUE PERFECT NULL, and its frequency is set by `b1` ALONE:**
```python
b1 = -2*math.cos(2*math.pi*f_notch/1000.0)     # f=26.0 Hz -> b1 = -1.973372   (NOT -1.97336)
```

## 🛑 TRAP 1 — the DC collapse
`H(0) = c4·(2+b1)/(1+a1+a2)`. Stock `2+b1` = 0.11920; at 26 Hz it becomes **0.026628 — a 4.48×
collapse.** Leave `c4`/`a1`/`a2` alone and the steering weight drops immediately and the operator feels it.
`a1`, `a2`, `c4` must be **re-solved together**.

## 🛑🛑 TRAP 2 — fixing DC the OBVIOUS way forces an HF BOOST (this is the one that would have shipped)
Put the poles at the notch angle (the textbook narrow notch) and solve `c4` for unity DC, and you boost
above the notch, because
```
|H(Nyq)| / |H(0)| = [(2-b1)/(2+b1)] * [(1+a1+a2)/(1-a1+a2)]     and (2-b1)/(2+b1) = 149.2
```
| poles @26 Hz | ring | max\|H\| | \|H(42.3 Hz)\| |
|---|---|---|---|
| r = 0.95 | 90 ms | **1.098** | **0.975** vs stock 0.385 = **2.53× WORSE** |
| r = 0.88 | 36 ms | **1.608** | 0.966 |

⚠ **42.3 Hz is exactly where V59 measured a MARGINAL parametric pump (42.19 Hz = 2× the 21 Hz mode,
eps 0.013–0.169 vs threshold 0.147).** The obvious construction trades the 26 Hz mode for a 2.5× louder
42 Hz pump. **Always check `max |H|` over 0–500 Hz against stock's 1.0000 before shipping a biquad edit.**

⭐ **THE FIX — Honda already showed it: put the POLES BELOW THE ZEROS.** Stock is poles 42.3 / zeros 55.2.
Do the same and DC holds at unity with **no HF boost at all.**

## ⭐ THE SOLVED SET — FINAL: centre **25.5 Hz**, poles 22.0 Hz, r = 0.950
🛑 **This supersedes the earlier "candidate B" (centre 26.000, poles 22.5). Three of four cells differ.**
🛑 **THE SPECIFICATION IS THE FORMULA. The decimals below are 17-significant-digit reference values, and
the hex is an ASSERTION TARGET — never the source.** (6-dp decimals do NOT round-trip a float32; see
[[feedback_float_cal_spec_is_the_formula_not_a_rounded_decimal]] — this exact block nearly shipped
`-1.881877`, which encodes to `58e1f0bf`, not `56e1f0bf`.)
```python
R_POLE, F_POLE, F_ZERO, FS = 0.950, 22.0, 25.5, 1000.0
a1 = -2.0*R_POLE*math.cos(2.0*math.pi*F_POLE/FS)   # -1.8818767088236372  -> 0xC60A8  56e1f0bf
a2 = R_POLE*R_POLE                                  #  0.90249999999999997 -> 0xC60AC  3d0a673f
b1 = -2.0*math.cos(2.0*math.pi*F_ZERO/FS)           # -1.9743840279896383  -> 0xC60B0  9eb8fcbf
c4 = (1.0+a1+a2)/(2.0+b1)                           #  0.80509500744381646 -> 0xC60B4  b51a4e3f
```
Compute at double precision, then `struct.pack('<f', ...)`, then **assert** the four byte strings.
To re-centre the notch, change `F_ZERO` alone and re-solve `c4`; `b1 = -2cos(2*pi*f/FS)` sets the null.
**H(0) = 1.000000** · pole r = 0.9500 **STABLE** · tau 19.5 ms, **99% ring 90 ms** (stock 20.2 ms) ·
flatness 0–10 Hz **2.78%** · **max |H| = 1.0000 — never boosts.**
⚠ **Never copy these hex strings into a build** — recompute with `struct.pack('<f', …)` from the decimals
and assert the round-trip. Two agents produced *different* byte strings for the same decimals in one day.

| f (Hz) | \|H\| | dB | Δphase vs stock |
|---|---|---|---|
| 3 | 0.9985 | −0.01 | **−1.12°** |
| 6 | 0.9929 | −0.06 | **−2.65°** |
| 7.79 | 0.9863 | −0.12 | **−3.97°** |
| 9 | 0.9796 | −0.18 | **−5.11°** |
| 21 | 0.4922 | −6.16 | −42.3° |
| 24.9 | 0.0621 | −24.14 | −63.4° |
| **25.5** | **0.0000** | **null** | +113.8° |
| 26.0 | 0.0493 | −26.15 | +111.6° |
| 26.8 | 0.1229 | −18.21 | +108.5° |
| 42.3 | 0.6801 | −3.35 | +96.4° |
| 100 | 0.8256 | −1.66 | −35.5° |

**GATE 2 PASSES:** 6–9 Hz costs only 2.7–5.1° of lag with magnitude essentially unchanged (very slightly
*lower* than stock); 21 Hz *improves* (0.492 vs 0.866); cost is confined to 32–100 Hz and never exceeds
unity. ⊕ `gp-0x6752` = −1 ⇒ net PID **damps** at 6–9 Hz, so the small added lag erodes a damping margin
rather than feeding a pumping one.
**Trade curve** (one parameter, the pole frequency): `fp`=17.3 r=.949 keeps 42.3 Hz at stock 0.383 but
costs **−12.3°** at 7.79 Hz; `fp`=24.5 r=.955 is phase-neutral (**−0.3°**) but puts 42.3 Hz at 0.833
(2.16× stock) and rings 100 ms. **fp≈22 is the knee.**

### 🛑 WHY 25.5 AND NOT 26.0 — a point-null is WASTED on this mode
At **Q 14–29** the mode's own −3 dB bandwidth is **f/Q = 0.90–1.86 Hz** — it occupies ~1–2 Hz, so
**band coverage beats depth.** Worst-case |H| over the 24.0–27.1 Hz uncertainty band:
**centre 25.5 → 0.1601 vs centre 26.0 → 0.2074.** And 25.5 wins at **every** point on the gain ladder
(1× 21.90: 0.396 vs 0.439 · 4× 23.61: 0.204 vs 0.251 · **6× 24.90: 0.062 vs 0.111**) while still giving
**−26.2 dB at 26.0 and −18.2 dB at 26.8** across route `a4`'s measured peak. Against a loop with only
**1.6–4.1 dB of gain margin, −18 dB is already overwhelming** — you need *enough everywhere the mode
might be*, not −119 dB at one frequency. It also **hedges the right way**: the mode moves DOWNWARD as
gain falls, and the two independent estimates (`f0` 24.90 below, `a4` peak 26.0–26.8 above) straddle 25.5.

## 🛑 BUILD BASE: V103, NOT V104 — this is a confound, and it is avoidable
```
          c4          a1         a2         b1        arm(0xC649B)
STOCK  +0.817310  -1.537200  +0.634620  -1.880800     0x00
V103   +0.817310  -1.537200  +0.634620  -1.880800     0x01   <- armed, Honda's coefficients EXACTLY
V104   +1.512023  (same)     (same)     (same)        0x01   <- V103 + c4 x1.85 flat-gain experiment
```
The solved `c4` (+0.805095) is **within 1.5% of stock**, because the DC constraint forces it there
(`c4` is **not** a free choice — you cannot hold `H(0)=1` and keep V104's 1.512023).

🛑 **I first recommended the V103 base on single-variable grounds. THE ORCHESTRATOR OVERRULED IT AND WAS
RIGHT — build on V104.** Record the reasoning, because the general lesson outranks this build:
- **V103 points CAN 427 at `gp-0x6b4c`; only V104 carries `|gp-0x6b86|` — the biquad's OWN output.** That
  is the **only** direct readout that the notch is in force, i.e. the **dose gate**. A notch with no dose
  gate is precisely the uninterpretable-null failure of V64/V68/V92
  ([[feedback-probe-the-gate-not-just-the-output]]). **Instrumentation outranks single-variable purity.**
- The "second variable" is a **MEASURED NULL, not an unknown**: `c4` ×1.85 flew on V104/route `a4`,
  670 s engaged, fault-free, dose provably delivered (1.824× on `gp-0x6b86`, speed-matched), operator
  reported no change, and the one moving band statistic died inside his own speed window. **Reverting a
  lever whose on-car effect is measured ≈ nothing is a return to a known baseline, not a confound.**
- V103 also has **Lever B stock**, which V104 restored — dropping it makes the A/B a three-difference
  comparison instead of one hop from what is on the car.
⇒ **The single-variable rule ([[accord-rate-lane-builds-were-never-single-variable]]) is about UNKNOWN
second variables. A measured-null second variable does not trigger it.**

## The arming path — confirmed FROM V104's image, not from the record
`cal(0xC649B)` **0x00 → 0x01**; `cal(0xC64FA)` **UNCHANGED at 0x05** — Honda's own gate cal was *not* the
mechanism. The bypass is a **4-byte code edit**, the only difference in all of `0x35200–0x35C00`:
`0x35A08` `e7`→`fb` · `0x35A09` `98`→`97` · `0x35A12` `ec`→`e0` · `0x35A18` `e9`→`ea`.
⇒ **V103/V104 already carry arming + repoint, so the notch is a PURE CAL EDIT — 16 bytes, 4 aligned
float32 cells, no cave, outside this kit's only bricking class.**

## ⚠ Open, and neither blocks a cut
1. **Which centre frequency.** The `f0` ladder puts the mode at **24.90 Hz at 6×** (the operator's
   setting); route `a4` scores **26.0–26.8 Hz**. Candidate B deliberately spans both (−18.7 dB @24.9,
   −22.2 dB @26.8). `b1` is one float — re-centre with the formula above.
2. **A sign discrepancy at 6–9 Hz:** one brief said *"P and I are net pumping, D is the lone damper"*;
   [[accord-gp6752-is-negative-one]] says the **opposite** (D pumps, P/I damp). Unresolved; it changes how
   any 6–9 Hz result is read, not the design.

Related: [[reference_accord_tau_env_fills_the_2to13hz_gap_amplitude_modulation]] — if the 2–13 Hz
"ratchet on top of the vibration" is this mode's own envelope, notching 26 Hz should remove **both**
symptoms, which is this build's falsifiable prediction.

## ✅ AS BUILT AND VERIFIED — V105, 2026-08-22
⚠ Filename says `26hz` for historical reasons (the design started at 26.0). **The shipped centre is 25.5 Hz.**

`_v105_V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64_plain_image.bin`
sha256 `2666a000415a29fef98ac9cd6c183536269c3e61a61fc822c17586f2adde7e00`, base **V104**.

**Verified from the built image's own bytes, two independent legs agreeing on every quantity:**
```
a1 0xC60A8 56e1f0bf = -1.88187671    a2 0xC60AC 3d0a673f = +0.902499974
b1 0xC60B0 9eb8fcbf = -1.97438407    c4 0xC60B4 b51a4e3f = +0.805095017     [all exact-formula]
H(0) 0.9999996 · pole r 0.9500000 STABLE · zero 25.499979 Hz · pole 21.999984 Hz
tau 19.50 ms · 99% ring 89.7 ms · max|H| 0-500 Hz never reaches unity
|H|  7.79 0.986282 · 21.00 0.492245 · 24.90 0.062089 · 25.50 2.086e-06 · 26.80 0.122877 · 42.30 0.680140
diff vs V104: 24 bytes / 8 runs = 4 coefficient runs + 2 cave halfwords + 2 CRC trailers. ZERO unattributed.
cave b6 -> |gp-0x6b94| >= |gp-0x4f64| (aggregator sum vs governor ceiling = live clamp-duty readout)
b5 UNTOUCHED (0xC4B64=1e95, 0xC4B70=da94) · dose gate 0x55DF2=0x7a (CAN 427 <- gp-0x6b86)
```
🛑 **All five transfer-function checks came back |d| = EXACTLY 0.00e+00** — the built floats reproduce the
formula bit-for-bit, so the response is *identical*, not approximate. **The 6-dp lossy trap did not fire.**

