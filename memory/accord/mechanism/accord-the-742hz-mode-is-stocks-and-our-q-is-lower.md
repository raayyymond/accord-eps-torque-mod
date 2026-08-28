---
name: accord-the-742hz-mode-is-stocks-and-our-q-is-lower
description: "The operator's peak-turn oscillation is at 7.42 Hz, which is EXACTLY stock's own ring-down f0 (7.42 Hz, zeta 0.0275-0.0321, Q 15.6-18.2). Our builds measure zeta 0.059-0.072, Q 7.0-8.5 - our damping is already 2x stock's. So the mode is OVER-EXCITED, not under-damped, and adding damping is the wrong axis. Four candidate exciters have now been tested and killed: the command rail, driver grip, command magnitude, and Coulomb relay switching."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ 7.42 Hz IS **STOCK'S OWN MODE**, AND OUR DAMPING IS ALREADY HIGHER THAN STOCK'S

2026-08-27. The operator's *"fixed oscillation at the peak of a hard curve"* measures **7.42 Hz**
(route 23, t = 445.6–448.2 s). The kit's stock baseline
([[accord-the-antidamping-is-hondas]], route `0x97`, V9b) measured the stock ring-down at:
```
   STOCK   f0 7.42 Hz   zeta 0.0275-0.0321   Q 15.6-18.2   line  29.8- 62.0 ct
   V102 6x f0 7.81 Hz   zeta 0.059 -0.072    Q  7.0- 8.5   line 905  -996   ct
```
🛑 **Exact frequency match to stock's f0** — and **our zeta is ~2x stock's, our Q ~half.**
⇒ **We have already ADDED damping to this mode. The 16-30x amplitude is EXCITATION, not a damping
deficit.** **Adding more damping is the wrong axis**, which independently confirms
[[accord-antidamping-is-a-state-effect-of-engaging]]'s finding that the `gp-0x6b26` lane can supply
at most 9.8 % of the `Re(Z)` deficit.

## 🛑 FOUR CANDIDATE EXCITERS TESTED AND KILLED
| hypothesis | test | verdict |
|---|---|---|
| the LKAS command **rail** opens the loop | railed vs high-but-not-railed, matched | **0.76x [0.22, 1.49]** |
| **driver grip** couples an arm mode | high- vs low-torque, oscillation measured on RATE | **0.79x [0.67, 1.01]** |
| command **magnitude** | 6-9 Hz vs mean \|cmd\| | rises 19->125 then SATURATES near 1500 ct |
| **Coulomb relay switching** injects broadband energy | see below | **0.14x [0.11, 0.19]** — INVERTED |

### ⭐ THE RELAY-EXCITER TEST, AND WHY ITS FIRST ANSWER WAS WRONG
Raw, it looked convincing: 6-9 Hz rate rms rises **monotonically 0.40 -> 1.83** across relay-duty
bins (corr **+0.411**, n = 1371 windows), and the operator's own event ran at relay duty **0.4073 vs
a route baseline of 0.0260 — 15.6x**.
🛑 **But the relay threshold is defined on |rate|, and the outcome is also a rate quantity.** Using a
**scale-free shape ratio (6-9 Hz / 0.5-3 Hz)** that cancels overall rate:
```
   relay duty     n     6-9 / 0.5-3 ratio p50
    0.00-0.01   1166          0.482
    0.10-0.30     64          0.348
    0.30-0.60     35          0.093
    0.60-1.01     30          0.047
```
**0.14x [0.11, 0.19]** — high-relay windows carry **relatively LESS** 6-9 Hz. **The dose-response was
entirely the rate confound.** ⇒ **relay switching is NOT the exciter.**
⊕ This also means **V116's knee raise should not be expected to fix the peak-turn oscillation**,
only grind #1 (which rests on the separate saturation-duty prediction).

## ⚠ WHAT REMAINS UNKNOWN — STATE IT PLAINLY
**The exciter of the 7.42 Hz mode is NOT identified.** What is known:
- the mode is Honda's and exists on stock (f0 7.42 Hz, Q 15.6-18.2);
- we drive its line **16-30x** stock's while *lowering* its Q;
- the 6-9 Hz anti-damping is **Honda's**, and we multiply it **2.4-3.0x at 29-86 km/h but NOT at
  highway speed** — a **speed-dependent** multiplication that is itself unexplained;
- the deficit is **command-INDEPENDENT** (present at \|cmd\| < 512), so it is a state effect of
  engaging.
🛑 **Do not propose another damping dose for this symptom without a new mechanism.** The honest next
step is to explain the **2.4-3.0x speed-dependent multiplication of Honda's own anti-damping**.
