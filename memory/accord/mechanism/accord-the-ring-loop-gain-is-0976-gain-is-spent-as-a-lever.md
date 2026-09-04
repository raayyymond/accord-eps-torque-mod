---
name: accord-the-ring-loop-gain-is-0976-gain-is-spent-as-a-lever
description: 2026-09-04, CORRECTED SAME DAY - THIS IS THE 7.3 Hz STRONG-TURN RING, NOT THE 20 Hz GRIND (see the correction section; the 20 Hz ring has NO usable measured loop gain - it is -1 by construction at a spectral line). MEASURED on r32-r38 - the 7.3 Hz ring's loop gain with the Kp table flat at 248 is 0.976 [0.944-0.990] (stock 1.027 [1.017-1.044]). Headroom to instability is 2.5 %, and V284's Kp raise spends +13 % (idx 68) to +31 % (idx 36-44) of loop gain against it, driving the ring ABOVE UNITY across its whole raised band (the original '1.0-5.6 % headroom / spends 2.1-5.4 %' framing understated this ~10x and named the wrong symptom); a model-free dose-response over the flown builds concurs at 0.997 [0.964-1.011]. THEREFORE GAIN IS SPENT AS A LEVER ON THIS LOOP - no further Kp raise anywhere without a fresh margin measurement. The estimator matters: the POOLED HALF-POWER WELCH WIDTH IS RETIRED because it tracks bin width, not physics (r38 gave Q = 0.9 / 12.3 / 26.7 across nperseg); replaced by a PER-EPISODE COMPLEX-ACF fit |rho(tau)| = exp(-alpha*|tau|), Q = pi*f0/alpha, sensitivity <= 0.004 across knobs. Ring sharpness gives distance from instability by |1 - L| ~ 1/Q; which SIDE of 1 you are on is chosen by the F7 episode counts, not by Q.
metadata:
  type: reference
---

# The 7.3 Hz ring's loop gain is 0.976 — gain is spent as a lever on this loop — 2026-09-04

🛑 **READ THE CORRECTION AT THE BOTTOM OF THIS FILE FIRST.** The body below was written attributing this number to the 20 Hz grind. **It is the 7.3 Hz strong-turn ring.** The verdict survives; the frequency, the magnitude of the effect and the symptom it bears on all change.

## The measurement

| build / condition | ring loop gain `|L|` at **7.3 Hz** (corrected) |
|---|---|
| stock | **1.027** [1.017–1.044] |
| Kp table flat 248 (V281 rev 3 / V282 / V283) | **0.976** [0.944–0.990] |

Method (EVIDENCE, and the frequency is 7.3 Hz not 20.3 — see the correction): per-episode complex-ACF fit `|ρ(τ)| = exp(−α|τ|)` on the analytic signal, `Q = πf₀/α`,
then `|1 − L| ≈ 1/Q`. The **sign** of `1 − L` — which side of instability the loop sits on — is settled by
the F7 episode counts across builds, not by Q, which is symmetric about 1.

Independent corroboration: a **model-free dose–response** across the flown builds gives 0.997
[0.964–1.011] — same conclusion, no plant model.

## The consequence, and it closed a whole lever class

Headroom to `|L| = 1` is **1.0–5.6 %**. V284's shaped Kp raise (248 → 512 over idx 32–44) spends
**2.1–5.4 %** of that. ⇒ **V284 SHELVED, DO NOT FLASH**, and more generally:

> 🛑 **Do not raise Kp anywhere on this loop without a fresh margin measurement.** Gain is spent.

The operator reached the same verdict independently from the drive: *"I don't like the direction this
firmware has gone. We should keep Kp fixed, if not 0."*

A second, independent ground also condemned V284: the gate that **selected** its shape scaled the servo
arm as if D followed Kp. **D does not scale with Kp.** True scaling 1.771∠−16.6°, not 2.065; corrected,
the ranking reverses (M8\* 1.216 vs flat 341's 1.033), so V284's shape was not even the winner of its own
selection.

## 🛑 The estimator lesson — this is the reusable part

The **pooled half-power Welch width is RETIRED as a Q estimator.** It measures the spectrogram's bin
width, not the mode's damping: on r38 it returned **Q = 0.9 / 12.3 / 26.7** as `nperseg` was varied, a
monotone function of the knob. Both my replication and the agent's carried the same defect and both were
retracted.

⇒ **Ship a null control with every estimator.** An estimator that has never been run against a signal
with a known answer — or against a knob it must be insensitive to — is not yet an instrument. The ACF
replacement was accepted only after its sensitivity across knobs came in at ≤ 0.004.

Related: [[accord-the-rate-pid-in-the-acceleration-frame-is-a-PI-our-P-is-its-integral-and-our-D-is-its-proportional]]
(the frame mapping; note Ku is NOT close to the current Kd — that estimate was void, see the correction), [[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]]
(what the 20 Hz mode is), [[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]].

---

## 🛑 CORRECTION, 2026-09-04 (same day) — THIS NUMBER IS THE **7.3 Hz** RING, NOT THE 20 Hz GRIND

**The frequency attribution above was WRONG when this file was written.** Flagged by the `telem285` subagent, verified by me at source.

`0.976 [0.944–0.990]` is `|L_tot(248)|` at the **7.3 Hz strong-turn ring**, from `rlog-tools/studies/osc-highangle/STUTTER-7HZ-V283-r36-r38-2026-09-03.md` **§A14.3** — whose own per-episode `f0` table spans **6.60–7.72 Hz, median 7.3** across r32–r38. Pooled over **5 flat-248 episodes, ~8 s**; the stock-Kp arm is 1.027 [1.017–1.044] over 13 episodes / 29.7 s.

🛑 **And there is NO usable measured 20 Hz loop gain to substitute.** The actual 20 Hz study, `rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md`, states in its own item 7(a): *“at a spectral line inside a closed loop, the ‘plant’ any estimator returns is 1/H_Tr = the inverse controller, so **L_in(line) = −1 by construction**… the L_in-at-20-Hz number cannot itself say limit cycle vs transmitted.”* Any 20 Hz loop-gain figure quoted as a margin is therefore tautological.

### What survives, and what changes

**V284's shelving SURVIVES — and strengthens.** At 7.3 Hz the **P term DOMINATES D** (`|D|/|P| = 33.03·sin(πfT) = 0.757`), so a Kp raise moves this ring far harder than it moves the grind. Scaling the servo lane and pooling with r24 at its measured 7 Hz shares (servo 0.81, r24 1.17, r24 independent of Kp):

| V284 band | Kp | servo lane | pooled `L_tot` | change |
|---|---|---|---|---|
| idx 68 | ×1.48 | ×1.325 | 0.976 → **1.106** | +13.3 % |
| idx 36–44 (peak) | ×2.065 | ×1.753 | 0.976 → **1.277** | +30.8 % |

Headroom at 7.3 Hz is **2.5 %**. V284 spends **+13 % to +31 %** of loop gain against it — it drives the ring **above unity across its whole raised band**, including idx 68 which sits inside the ring's own index range. 🛑 **My original framing (“headroom 1.0–5.6 %, V284 spends 2.1–5.4 %”) UNDERSTATED the problem by roughly 10×**, and attributed it to the wrong symptom.

**What does NOT survive:** the claim that this measurement bears on **grinding**. It does not. It is the strong-turn ring — the operator's *“stuttering when the wheel is turning”* family, not his *“rare, attenuated grinding”*. Gain is spent as a lever **on the 7.3 Hz ring**; the 20 Hz grind's margin remains **unmeasured**.

**Downstream casualty:** a `Ku ≈ 143–151` extrapolation built on this number at 20 Hz is **VOID**. The right basis is the Kd dose–response in `CREEP-20HZ-LOOP-ID` item 4 — `|L(20)|` = 0.37 at Kd 0, 0.51 at Kd 64, ≈ crossover at Kd 128 — which points nearer **Ku ≈ 180** and would put the loop-shape study's candidate F (Kd → 160) **below** Ku rather than above it.

**The reusable lesson**: a number is not an instrument until its **frequency, its method and its episode count** all travel with it. This one lost its frequency in a single copy step.
