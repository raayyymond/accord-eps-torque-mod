---
name: accord-pid-gains-are-rate-scheduled-and-kd-is-flat
description: "All three PID gains in FUN_0003a382 LERP on the SAME axis gp-0x6ac0 (resolver/FOC electrical rate). Kp is NOT flat - Honda rolls it off 40 percent at high rate, Y = 256/256/225/153 on X = 0/300/2000/4000 - which proves the scheduling machinery is live and used. Ki and Kd are FLAT and byte-identical in stock and V112. This is a rate-scheduled, therefore frequency-selective, cal-only lever that the kit had concluded does not exist, and the archived Re(Z) work says the D term PUMPS at 2-12 Hz, straddling the 7-9 Hz symptom."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ HONDA GAIN-SCHEDULES THE PID ON MOTOR RATE — AND LEFT `Kd` FLAT

## [EVIDENCE] The structure — decompiled `FUN_0003a382`, then byte-verified in Python
All three PID gains are **four-knot LERPs on the SAME axis**, `uVar24 = gp-0x6ac0`:
```
  uVar20 <- tp+0x7b26 = 0xC6B26 = Kp  -> x error                       (P)
  uVar16 <- tp+0x7b12 = 0xC6B12 = Ki  -> x error, accumulated          (I)
  uVar12 <- tp+0x7ae6 = 0xC6AE6 = Kd  -> x FIRST DIFFERENCE            (D)

  Kp  X = [0, 300, 2000, 4000]    Y = [256, 256, 225, 153]   <-- NOT FLAT
  Ki  X = [0, 400, 1500, 3000]    Y = [ 98,  98,  98,  98]       flat
  Kd  X = [50, 400, 1500, 3000]   Y = [2048,2048,2048,2048]      flat
```
✅ **All three Y rows are byte-identical in stock and V112** — virgin across the whole build history.
✅ The lane's enable gate is `gp-0x6ac0 < 0x32C9` (**13001**); above that the lane outputs 0.
⚠ [BELIEF, from [[reference-accord-c520c-cap-table-axis-provenance]], not re-verified here]
`gp-0x6ac0` is the **resolver/FOC electrical rate**.

## 🛑 THIS CONTRADICTS A STANDING KIT CONCLUSION
[[accord-factord-is-the-angle-error-lever]] closed with *"this firmware has NO frequency-selective
lever."* ⇒ **That is too strong and should be read as scoped to FactorD.** A gain scheduled on
**rate** is frequency-selective at fixed amplitude, and **Honda's own Kp row proves the machinery is
live, wired and calibrated** — it is not a dormant feature that has to be armed.

## ⭐ WHY IT MATTERS FOR THE 7-9 Hz OSCILLATION
[[accord-the-mod-works-by-deleting-hondas-limiters]] now has quantitative support: the excess tracks
**no** cal that has ever varied, so the cause is the deletion SET — and **every member of that set is
an authority limit**, so restoring any of it spends exactly what the operator forbade
(*"low effective friction and steering mass w.r.t. LKAS command"*). ⇒ the next lever had to be
frequency-selective. **This is one.**
⊕ `STATE-ARCHIVE-2026-08-11` measured `Re(Z)` to 35 Hz and found **D PUMPS ONLY 2-12 Hz and DAMPS
16-35 Hz** ⇒ **Kd is an anti-damping contributor at exactly the symptom band.**
⊕ A **rate-scheduled** rolloff is not the flat cut that measurement scored: shape Kd like Honda
shapes Kp — **unchanged at low rate** (so no loss of steering velocity or acceleration, no added
friction, mass or phase where the LKAS command lives) and **reduced at the top knots**, where the
oscillation's motor rate is.

## 🛑 WHAT IS NOT ESTABLISHED — do not build yet
1. **Knot placement is unmeasured.** Nothing here shows what `gp-0x6ac0` reads during the 7-9 Hz
   event vs during a normal hard curve. **If the two overlap, this lever cannot separate them and
   the idea fails.** ✅ This is the crux and it is measurable from existing telemetry.
2. **It changes MANUAL steering.** `FUN_0003a382` is gated on `gp-0x67fa & 0xc30` — the normal-driving
   cluster, **not** an LKAS flag ([[reference-accord-fun3a382-unfiltered-residual-lane]]).
3. **GATE 2 applies** — the D term is inside a loop; magnitude *and* phase.
4. ⚠ The kit **REFUSED** flat Kp/Ki/Kd scaling before ("the SQUEEZE": Kp x2 = 1.130x, on the 1.088
   not-felt bound; x4 rails 92 % hands-on). **That refusal was about FLAT scaling and does not
   transfer to a non-flat row** — but it does warn that this lane's authority is easy to misjudge.
✅ **Cal-only, one Y row, no cave** ⇒ outside the kit's only bricking class.
Tool: `analysis-2020accord/verify/read_pid_rate_schedule.py`.

## 🛑 THE CRUX TEST RAN, AND THE LEVER **LARGELY FAILS IT** — 2026-08-28, same session
The section above pre-registered the crux: *"nothing shows what `gp-0x6ac0` reads during the 7-9 Hz
event vs during a normal hard curve. **If the two overlap, this lever cannot separate them and the
idea fails.**"* **It ran. They overlap.**

Proxy: `|cs_rate|` p95 per window (motor rate = wheel rate × a fixed gear/pole ratio ⇒ monotone in
`gp-0x6ac0`). 8,200 engaged windows, 17 routes. **OSCILLATING** = 6-9 Hz rms in the top 5 %;
**NORMAL HARD CURVE** = |ang| ≥ 20° with 6-9 Hz below its 60th pct.
```
   OSCILLATING       n = 410   median |rate| p95 = 47.06 deg/s
   NORMAL HARD CURVE n = 106   median |rate| p95 = 24.49 deg/s

   knot T    % OSCILLATING caught    % NORMAL-CURVE caught    ratio
      20            83.4                    61.3             1.36x
      30            66.1                    44.3             1.49x
      40            60.2                    36.8             1.64x
      60            22.4                    27.4             0.82x   <- inverts
     200             5.6                     2.8             1.98x   <- 5.6 % is useless

   AUC(oscillating > normal hard curve) = 0.630     (0.5 = none)   p = 1.9e-05
```
🛑 **AUC 0.630 is weak separation.** Every threshold that catches a useful share of the
oscillation also catches **a third to a half of normal hard curves**, and at 60 deg/s the ratio
*inverts*. ⇒ **a rate-scheduled `Kd` knot cannot act on the oscillation while sparing normal hard
steering**, which is exactly the cost the operator forbade.

### ⚠ IT IS WEAK, NOT ZERO — and two caveats cut opposite ways
⊕ A LERP is a **smooth** curve, not a gate. The medians *do* separate **1.9×** and highly
significantly, so a gradual rolloff would reduce `Kd` roughly **1.9× more** during oscillation than
during normal steering. **That is a real but modest differential**, not the clean selectivity the
idea needed.
⚠ **The proxy may UNDERSTATE separation**: `gp-0x6ac0` is the **motor** electrical rate, and the
motor sees the oscillation more strongly than the wheel does (wheel inertia filters it). ⇒ the true
AUC on the real axis could be higher. **Measuring `gp-0x6ac0` directly needs a cave probe**, which is
this kit's only bricking class — so this caveat cannot be cheaply resolved.
⇒ **STATUS: PARKED, not struck.** The structural finding above (Honda rate-schedules the PID; `Kd`
is flat and virgin) **stands and is EVIDENCE**. What fails is the specific claim that the rate axis
discriminates this symptom. **Do not build it on the strength of the structure alone.**
Tool: `rlog-tools/studies/peakturn/rate_axis_separation_roc.py`.
