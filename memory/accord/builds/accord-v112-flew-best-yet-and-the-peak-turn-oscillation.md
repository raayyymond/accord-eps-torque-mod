---
name: accord-v112-flew-best-yet-and-the-peak-turn-oscillation
description: "V112 FLEW (routes 22, 23) and the operator calls it the best firmware yet - grind #1 now RARE, least ratcheting ever. This REFUTES the describing-function argument on which V112 was withdrawn. The remaining peak-turn oscillation is LOCATED: route 23 t=445.6-448.2 s, 7.42 Hz, 16.86 deg/s of 6-9 Hz RATE content against a corpus p99 of 3.98 - the corpus maximum. The command rail is NOT causal (0.76x [0.22,1.49]); command MAGNITUDE gates it and saturates near 1500 counts; driver torque has no reliable effect (0.79x [0.67,1.01])."
metadata:
  node_type: memory
  type: project
---

# 🛑🛑★★★★★ V112 FLEW AND IS THE BEST BUILD YET — MY WITHDRAWAL OF IT WAS WRONG

2026-08-27. Routes **22** (12 seg, 720 s) and **23** (9 seg, 541 s), both V112, both fault-free.

## 🛑 THE RETRACTION FIRST
I **withdrew V112** on a describing-function argument: scaling knee *and* K1 together raises the
friction-compensation's effective slope up to **2.93× above 10.6 °/s**, and since the term sits
in phase with rate and is a *compensation*, more of it is **anti-damping** — the same axis as V94.
**The operator flew it anyway. Verbatim:**
> *"This is the best firmware ever on 6x torque. Grind #1 is now rare… This is the smoothest
> firmware ever with the least amount of ratcheting."*

⇒ **The prediction was wrong, or at least not decisive.** Candidate reconciliations, none verified:
the anti-damping increase is real but small against what unsaturating the relay buys; or the relay's
*Coulomb* character (not its magnitude) was the dominant ratchet driver, so linearising it wins even
at higher gain. 🛑 **Do not carry the V112 withdrawal argument forward as settled physics.** ⚠ It
also means **V113 — built to be "strictly safer" than V112 — was solving a problem that did not
materialise**, and its cost (a heavier wheel) is now unjustified. **V113 is DEPRIORITISED.**

## ⭐⭐ SYMPTOM A — THE PEAK-TURN OSCILLATION, LOCATED EXACTLY
Operator: *"not just ratcheting but … a FIXED OSCILLATION during the peak of a hard curve"*,
route 23, segment 7, 21:46:48. **Found by physics, not by the clock**: segment 7 spans
t = 421.3–481.2 s and contains **exactly one** hard-curve peak, `|ang| = 99.8°` at **t = 448.6 s**.
```
  t=445.61  ang -39.6  rate -20.9  cmd 4096  drvTq +1953
  t=445.80  ang -42.6  rate  -0.8  cmd 4096  drvTq -2443
  t=446.00  ang -43.5  rate  -0.9  cmd 4096  drvTq +2297
  t=446.21  ang -46.6  rate  -2.0  cmd 4096  drvTq -2487
  t=446.41  ang -47.2  rate  +1.9  cmd 4096  drvTq +2276
```
**7.42 Hz. 6–9 Hz torque rms 1630 counts (corpus max; p50 87, p90 466).**
**6–9 Hz RATE rms 16.86 °/s against a corpus p99 of 3.98 and p50 of 0.40 — 4.2× the p99.**
⇒ **An unambiguous extreme outlier on two independent sensors.** 7.42 Hz is the kit's ratchet mode
and sits in the band `Re(Z)` measures at **−43 to −67**
([[accord-antidamping-is-centred-at-9-12hz-not-20-30]]).

### 🛑 THREE HYPOTHESES TESTED AND KILLED
| hypothesis | test | verdict |
|---|---|---|
| the **command rail** opens the loop and lets it ring | railed vs high-but-not-railed, matched | **0.76× [0.22, 1.49]** — spans 1, point estimate *below* 1. **NOT causal** |
| the **driver's grip** couples an arm mode | high- vs low-torque windows, oscillation on **rate** | **0.79× [0.67, 1.01]** — no reliable effect |
| duration / angle / speed drive it | correlations over 33 rail episodes | r = 0.159 / −0.154 / 0.338 — all weak |

⭐ **What DOES gate it is command MAGNITUDE, and it saturates:**
```
   mean |cmd|     6-9 Hz torque rms p50
      0- 256              19
    512-1024              90
   1024-1536             125     <- knee
   2560-3072             116
   4000-4097              85
```
⇒ rises **6.6×** to ~1500 counts then flat — the same command-gated saturation the kit has recorded
from other instruments.

## 🛑🛑 A METHOD RETRACTION THE OPERATOR CAUGHT — AND IT MATTERS BEYOND THIS RESULT
I first measured the grip contrast with the oscillation taken from **`cs_tq`** and the hands-on split
taken from **the rolling median of `cs_tq`**. That gave **0.17× [0.14, 0.22]** — an apparently huge
suppression. Re-measured with the oscillation on **`cs_rate`** (a different sensor from the one doing
the splitting) it is **0.79× [0.67, 1.01]**. **The 6× effect was a shared-signal artifact.**
🛑 **AND HANDS-ON DETECTION IS NOT SOLVED.** `carState.steeringPressed` (`cs_press`) is *itself* a
torque threshold — `P(press)` goes **0.032 → 0.983** across |tq| ≈ 1200 — so it is **not independent
evidence** and neither channel can see **light hands resting on the wheel**, which still couple the
arm's mass and damping. ⇒ **Any hands-on/off claim in this kit built on a torque threshold is
measuring high-vs-low torque.** A real detector must be **dynamical** (hands change the column's
admittance), and does not yet exist.

## SYMPTOM B — GRIND #1, SEPARATE FROM THE ABOVE (operator's own clarification)
Acoustic, 5–10 mph, engaged-minus-manual **within** each drive (absolute level never travels):
```
  r22  120-250 Hz  +0.70 dB   null-1 (disjoint manual halves) p95 +0.17  PASSES
                              null-2 (block-shuffled label)   p95 +0.69  PASSES (barely)
  r23  120-250 Hz  +0.86 dB   null-1 p95 +0.28  PASSES
                              null-2 p95 +0.89  🛑 FAILS
```
⚠ **Carry as WEAK.** Individual episodes reach **+4.5 to +6.5 dB** and are **brief (0.10–0.35 s)**,
which matches *"rare, but has its few moments"*. Candidate instances —
**r22 t = 583.5 / 582.9 / 476.9 s · r23 t = 530.5 / 170.8 / 170.1 / 132.3 s** — at
**|cmd| p50 ≈ 1900–2300, |ang| 4–24°, 5–10 mph.** ⊕ r22's acoustic event at 583.5 s sits beside a
CAN-side 6–9 Hz event at 584.9 s — two instruments, one moment.
🛑 **The trigger is NOT yet identified**; the episodes are too few and the null too weak.

## ⭐ WHAT THIS IMPLIES FOR THE NEXT BUILD
Symptom A is at **7.42 Hz**, in the band `Re(Z)` says is most anti-damped, and is **not** fixable by
anything on the command side ([[accord-the-oscillation-is-not-command-driven]]).
⇒ **[[accord-v114-alpha2-rotates-mass-into-damping]] targets exactly it** (+25 % damping at 6–16 Hz,
−20 % apparent mass, every magnitude falling). **V114 is the recommended next flight; V113 is not.**
