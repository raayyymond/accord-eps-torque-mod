---
name: accord-notch-is-the-only-shape-that-survives-gate2
description: "🛑⭐★★★★★ Every IN-LOOP low-pass that meaningfully attenuates 26 Hz DESTROYS the margin that keeps it stable — even −6 dB costs −60° against a gain margin of only 1.6–4.1 dB. A NOTCH is the only shape that escapes, because its phase returns to ZERO at its own centre. V105 retunes Honda's dormant biquad 55 → 25.5 Hz: 4 floats, PURE CAL, zero blast radius, DC held at unity. ⚠ Two traps: DC collapses 4.48×, and fixing DC the obvious way forces a 2.53× HF BOOST at 42.3 Hz."
metadata:
  node_type: memory
  type: reference
---

# A notch is the only shape that survives GATE 2 at 26 Hz

## 1. 🛑 THE STRUCTURAL KILL — every in-loop low-pass fails on PHASE
| 1-pole corner | `\|H(26 Hz)\|` | phase @26 Hz | phase @3 Hz |
|---|---|---|---|
| 15 Hz | 0.500 (−6.0 dB) | **−60.0°** | −11.3° |
| 10 Hz | 0.359 (−8.9 dB) | **−69.0°** | −16.7° |
| 5 Hz | 0.189 (−14.5 dB) | **−79.1°** | −31.0° |

**The measured gain margin is 1.2–1.6× = only 1.6–4.1 dB.** ⇒ **PHASE is the binding constraint, not
gain. There is NO corner high enough to be safe and low enough to matter.**

## 2. ⭐ A NOTCH ESCAPES THE TRADE
Its phase **returns toward zero away from `f0` and is 0° AT `f0`** ⇒ **−23 dB at the mode for −0.1 dB
and −8.6° at 3 Hz.** That is the whole design.

## 3. AND COMMAND-PATH (FEEDFORWARD) FILTERING CANNOT WORK EITHER
GATE 2 does **not** constrain the command path — a feedforward filter is not in the return ratio, so it
cannot change gain or phase margin at all. **But it also cannot help:** the mode is **SELF-EXCITED**
(`f0` = 21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6× — a driven response does not move its frequency with
loop gain). Broadband seed is sufficient. ⊕ **Route B kills it independently:** `gp-0x6b4c` reaches the
aggregator **DIRECT at `0x3AA3E`**, bypassing the 5.05 Hz arbitration IIR — which also **resolves the
long-unexplained 0.71–1.06 command→motor attenuation discrepancy.**

## 4. V105 — THE BUILD
```python
R_POLE, F_POLE, F_ZERO, FS = 0.950, 22.0, 25.5, 1000.0   # 🛑 THE FORMULA IS THE SPECIFICATION
a1 = -2*R_POLE*cos(2*pi*F_POLE/FS)   # -1.8818767088236372   0xC60A8  56e1f0bf
a2 = R_POLE*R_POLE                   #  0.9025               0xC60AC  3d0a673f
b1 = -2*cos(2*pi*F_ZERO/FS)          # -1.9743840279896383   0xC60B0  9eb8fcbf
c4 = (1+a1+a2)/(2+b1)                #  0.8050950074438165   0xC60B4  b51a4e3f  <- FORCED by unity DC
```
```
notch 25.499979 Hz  |z| = 1.000000000 (a TRUE null)   pole 21.999984 Hz  r = 0.950  STABLE
H(0) = 0.999999581       max|H| over 0-500 Hz = 0.999999564   <- NEVER reaches unity anywhere
|H| 7.79 0.9863 · 21.73 0.4150 · 24.9 0.0621 · 25.5 2.09e-6 · 26.8 0.1229 · 42.3 0.6801
tau 19.496 ms · 99% ring 89.7 ms
```
**BLAST RADIUS ZERO** — each cell has **1 reader, 0 writers**, all four inside a 40-byte window
(`0x035A30`–`0x035A58`), and **0 `movea`/`movhi` hits on the imm16s.** **PURE CAL — no cave.**
⭐ **V103/V104 already carry the arming** (`0xC649B` = 1 plus a 4-byte repoint at `0x35A08/09/12/18`),
so the arm path is exercised, not theoretical. **Honda's own gate (`cal(0xC64FA)` = 5 ≤ `gp-0x671a`) is
FALSE on this car** — the bypass is that code edit, not the cal.

## 5. 🛑 TWO TRAPS THAT WOULD HAVE SHIPPED
1. **DC COLLAPSE 4.48×** — moving `b1` to the notch frequency drops the numerator's DC term 0.11920 →
   0.026628. **`c4` and the poles must be re-solved TOGETHER or the steering weight changes.** Honda set
   `H(0)` = 1.000034 deliberately; the section is **feel-neutral by design.**
2. 🛑 **THE HIDDEN ONE — fixing DC the obvious way forces an HF BOOST.** Put the poles **at** the notch
   angle (the textbook narrow notch) and `max|H|` becomes **1.098–1.608** with **`|H(42.3)|` = 0.975 vs
   stock 0.385 = 2.53× WORSE** — because `(2−b1)/(2+b1)` = **149.2**. ⚠ **Exactly where V59 measured a
   MARGINAL parametric pump** (42.19 Hz, eps 0.013–0.169 vs threshold 0.147). **A 26 Hz notch built the
   obvious way trades the 26 Hz mode for a 2.5× louder 42 Hz pump.**
   ⭐ **FIX: Honda's own POLES-BELOW-ZEROS layout** (stock is poles 42.3 / zeros 55.2).
   🛑 **CHECK `max|H|` OVER 0–500 Hz AGAINST STOCK'S 1.0000 BEFORE SHIPPING ANY BIQUAD EDIT.**

## 6. WHY 25.5 Hz AND NOT 26.0
**The mode's own −3 dB bandwidth is `f/Q` = 0.90–1.86 Hz** (Q 14–29) — **it is not a tone, so band
coverage beats a point-null.** And the two centre estimates disagree (`f0` says **24.90 at 6×**; route
`a4` scores the peak at **26.0–26.8**). 25.5 straddles them and wins at **every** rung of the ladder:

| mode sits at | centre 26.0 | **centre 25.5** |
|---|---|---|
| 1× — 21.90 Hz | −7.2 dB | **−8.0 dB** |
| 4× — 23.61 Hz | −12.0 dB | **−13.8 dB** |
| 6× — 24.90 Hz | −19.1 dB | **−24.1 dB** |
| worst over 24.0–27.1 Hz | 0.216 | **0.160** |

**It also hedges toward the direction the mode travels as gain falls.** `b1` is one float if re-centring
is ever needed — **change `F_ZERO` alone.**

## 7. THE COSTS, STATED
**42 Hz 1.75× worse** (0.385 → 0.680) · **engagement ring 20 → 90 ms** (the filter's state freezes while
disarmed and resumes from stale state) · **6–9 Hz +2.7–5.1° of lag**, magnitude essentially unchanged.

## 8. ⚠ IT IS NOT THE REFUSED NOTCH
`docs/GATE2-2026-08-20-notch-sign.md` refused re-centring **at 6–9 Hz**, killed on `Re(u/T)` phase.
**This targets 26 Hz — a different band and a different argument.** ⭐ **`0xC60A8`/`AC`/`B0` are
byte-stock in all 74 built images V38→V104; only `c4` has ever moved, once, at V104 — and it was NULL.**

## Related
[[accord-26hz-mode-is-a-steering-rate-phenomenon]] — the target ·
[[accord-v104-flew-and-failed-verify-from-telemetry]] · [[accord-v59-parametric-pump-marginal]] ·
[[accord-honda-biquad-arm-gate-is-false-on-this-car]] · [[accord-the-8x-gain-is-the-carrier]]
