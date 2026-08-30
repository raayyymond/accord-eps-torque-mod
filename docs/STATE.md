# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V222.** = **V221 with four bytes REMOVED from the delta.** Delta from the CAR (**V122**) is **23 payload bytes** — notch 20.50 Hz (grinding) · `0xC63AE` 512 (ratchet) · `0xC6CD0` 6×→8× + clamps (authority) · `0xC6446` 5244→13107 (Lever B) · the 427 probe. Every deliberate lever is byte-identical to V221; what changed is that the friction lane now matches the car at EVERY rate rather than only below its knee. Drive card: `docs/scoring/DRIVE-CARD-V222.md`. **V221 is the fallback** (`DRIVE-CARD-V221.md`), V217 behind it. Shelf: `docs/scoring/SHELF.md`. Pre-registered scoring: `docs/scoring/SCORING-V217-preregistered.md` (applies to all three).

> 🛑⭐ **THE GOVERNOR RAMP-TIME HYPOTHESIS IS RETIRED — by the task rate, now that it is known.** The model records it as the leading ratchet hypothesis, *"later CONFIRMED as a real contributor"*, while its own docstring says why that could never have been quantitative: *"[OPEN] the wall-clock conversion (task rate contested); cycle counts here are exact, milliseconds are deliberately NOT computed."* **The task rate is no longer contested** — the control task is confirmed ~1 kHz — so the milliseconds are computable, and they retire it: `lkas_max = min((8192*gain)>>15, 4096)`, ramp = lkas_max/step. **Honda 0.4/1.1 ms · the car 2.6/6.5 ms · the shelf 3.5/8.7 ms** — against a ratchet period of **128.4 ms**, i.e. **15–37× faster than one cycle**. The *"V38 made the ramp 4× longer"* observation is arithmetically right and operationally irrelevant: **4× of 0.4 ms is 1.7 ms**. The earlier "confirmed contributor" verdict was reached with no task rate and is confounded with V42’s state-4 substitution, which the record itself calls the root-cause fix. 🛑 **AND DO NOT TOUCH THE CELLS ANYWAY**: `0xC6206`/`0xC6208` are 512/205 in **217 of 219 images**; the exceptions are V45 (205/205, falsified) and **V40 (0xFFFF — ☠ EPS lamp + NO POWER STEERING AT IGNITION)**. The record attributes that fault to these two cells and says the mechanism was **magnitude, not direction**: the guard never fired → snap-to-target → DTC 0x1d with **no debounce** → motor off. Since the LKAS command is a ~1–5 Hz low-pass, its natural per-cycle change is a few counts, so **any large step makes the guard functionally inert** — the exact condition that faulted V40. **No demonstrated safe raise, and nothing to buy.** Study: `analysis-2020accord/studies/mixer/governor_ramp_time_retired_by_the_task_rate.py`.

> 🛑⭐ **AUDIT OF THE TASK-RATE RECORD — the governor retirement holds, but a RETRACTED veto was
still live in a MANDATORY file.** Having just retired a hypothesis on the strength of the task rate, I
audited every conclusion that rests on one. **Both of this session’s rate-sensitive studies are on the
correct time base**: `FUN_0003a382` (the resonance PID) and `FUN_00036682` (the bias tracker) are both
**task 1 = 1 kHz** — the first by three independent records, the second because its sole caller *is* the
aggregator. That mattered: at 100 Hz the PID’s D term would be **0.979 vs P 0.250**, inverting *"85 %
stiffness-like"* into *"predominantly lead"*. It is not. ✅ And the **governor is explicitly inside the
1 kHz scope** — the confirming memory names *"arbitration, the aggregator, shaper, governor"* — so the
retirement stands. 🛑 **But the audit found `docs/BUILD-LINEAGE.md` — which `CLAUDE.md` makes MANDATORY
before proposing any calibration edit — still carrying `★★ RTOS task 5 runs at 100 Hz` as a live
structural finding, when it was RETRACTED on 2026-08-12** (the derivation rested on an **address
coincidence**, and flown `gp-0x6bbe` telemetry contradicts it). The paragraph already carried the
*clock-chain* correction but closed with *"the 1 kHz/**100 Hz** figures survive on ON-CAR measurement"* —
**only the 1 kHz half does** (`0xC64DF` = 100 cycles, observed at 100.00 ms); **task 5 has never been
measured at all.** ⇒ the **ZOH veto is unsupported**: V44/V47’s nulls now rest on the FactorC speed-axis
argument **alone** (the damper is identically zero below 35 km/h — solid, cal-level, and independent of
any task rate), and the claim that *"r24/r26 are the ONLY damping with the bandwidth to act on grind #1"*
is **unsupported too**. ⚠ **Unsupported is not refuted, and nothing here changes the flight order**:
Lever B’s standing rests on its **measured** V88 win, not on that argument. ⊕ Also corrected: the
task-rate memory claimed 1 kHz on **two** independent routes, but the **OSTM0 route is refuted** — PCLK
is **40 MHz, not 80**, and OSTM0 is not the RTOS tick, which the arc map calls *"a recorded red herring an
agent nearly shipped"*. **1 kHz is unaffected** — it stands on the on-car dwell, which never used that
chain — but it stands on **one** route, and no future agent should reason from PCLK = 80 MHz.

> 🛑⭐ **LEVER B AT 13107 CARRIES A RESIDUAL PUMPING RISK AT THE RATCHET — and the corpus CANNOT
clear it.** Lever B **is** the r24 engaged derivative gain, and the kit’s three-way-verified sign finding
(`gp-0x6752` = **−1**) concludes **r24’s 6–9 Hz contribution is sign-negative, −431 to −1294 ct —
"PUMPING"**. The ratchet is **7.79 Hz**, inside that band, and V222 raises Lever B **2.5× above the car**.
⊕ **The corpus turned out to contain a real ON/OFF contrast at BYTE-MATCHED forward gain** — within
`0xC6CD0` = 5346, Lever B is **512/arm `0xc5`** on V102–V103 and **5244/arm `0xfb`** on V104–V122 ⇒
**2 routes vs 9**, forward gain (the biggest confounder) held byte-identical. Engaged, the ratchet band
moves **1.08×, p = 0.58**. ❌ **But that null does NOT clear the risk and is not presented as if it
did**: the detection floor is **3.55×** (2 vs 9 routes; the smallest attainable rank p is 0.036 and needs
complete separation), and **the built-in control FAILED to stay quiet** — computed on **disengaged**
driving, where Lever B is **inert**, the same contrast shows the table’s **largest** separation
(**+0.212 log10, p = 0.073**). ⇒ the arms differ by road and route, not only by lever, so the engaged
null is **not attributable**. Rate-stratifying does not rescue it (spread stays 1.9–8×; direction is
**mixed** — +1.34× at creep, 0.38× at 8–20 rate, nothing significant). The arms are also not
single-variable. ⇒ **the only real evidence remains V88’s direct A/B: 6–9 Hz at 0.859× — the SAFE
direction — at HALF this dose.** V222 stays the flight candidate; the ratchet is now **pre-registered to
WATCH**, with V221 then V217 (the V88-proven 5244) as fallbacks. Drive card updated.
Study: `analysis-2020accord/studies/mixer/lever_b_pumping_check_at_matched_gain.py`.

> ✅⭐⭐ **AND THEN IT WAS MEASURED: r24 DAMPS AT 6–9 Hz. The "PUMPING" claim is WRONG in direction
AND ~4× in size.** No flown route carries the `gp-0x6ada` mirror (the corpus tops out at `r24` = V122,
the build on the car), so r24 has never been observed — **but it is COMPUTABLE**, because its only input
is column torque and that is on the wire. Mirrored exactly: `gp-0x4f62 = T[n]−T[n−4]` at 1 kHz →
`× cal(0xC6446) >> 10` → `clamp ±8192` → `× gp-0x6752 (=−1)`, i.e. as a transfer
**`r24(f) = −(cal/1024)·(1−e^{−j2πf·0.004})·T(f)`**. At 7.79 Hz the difference term is **fixed** at
`|H| = 0.19547, arg +84.39°`, so the entire question reduces to **one measurable quantity — the phase of
column torque vs rate.** Measured on **6 routes / 5 builds**: torque **lags rate by −122°**, spread only
**18.9°** ⇒ **r24 sits at +143.6° vs rate, 36° from the ANTI-rate axis, net-work factor −0.805 —
DAMPING.** Magnitude at the car’s Lever B: **187 counts against the record’s claimed 431–1294**, i.e.
**overstated 2.3–6.9×**. ✅ **Two controls with non-trivial expectations pass exactly** (a viscous torque
must land at −95.6° = quadrature, a stiffness torque at +174.4° = damping), and the `csd` convention is
**pinned with a constructed +90° lead rather than assumed** — the exact trap that has inverted this kit
decision-bearingly before. ✅ **V88 agrees independently**: raising this same gain 512→5244 measured
**6–9 Hz at 0.859× on-car**. ⚠ **Frame-dependent** (a global flip makes it pumping) — it rests on the
operator-confirmed table under which driver torque and steering angle share a frame and assist acts in
the driver’s direction; and ⚠ **open-loop**, so it says what r24 computes, not what the closed loop does
with it. ⊕ **Two bugs the controls caught before publication**: at the ~100 Hz cache rate
`round(4 ms × 100) = 0`, so a naive span silently becomes a **10 ms** difference (2.5× the gain, 8.4× of
phase error) — computed analytically instead; and the `csd` sign was inverted. ⇒ **the pumping concern
on V222 is resolved in the safe direction by three independent lines**, and the drive card is updated.
Study: `analysis-2020accord/studies/mixer/r24_reconstructed_magnitude_and_phase.py`.

> 🛑⭐⭐ **V227 IS MEASURED INERT AT THE RATCHET — its lever is a ceiling that does not bind.** The
lane work-factor method (below) also sizes each lane, and `gp-0x6ad4`’s 6–9 Hz output is **47.2 counts**
against a recorded ceiling of **164–341** at ratchet speeds. **The ceiling is 3.5–7× above the signal**,
so `0xC67C4` — V227’s only edit — **cannot act there.** That is exactly the *"third outcome is INERT"*
the record flagged for V227, now **measured rather than speculated**. ⊕ The same number killed the
build I was about to cut: a mirror-image lever raising the same knee would be inert for the identical
reason. ⚠ V227 may still act at **DC/low frequency** through the integrator’s anti-windup window
(a sustained error can pin it), but **not in the ratchet band** — so it must not be described as a
ratchet rung. ⇒ **the lever that acts regardless of the ceiling is the lane GAIN `0xC6AF0` (= 5).**

> ⭐⭐ **THE LANE WORK-FACTOR RANKING — `gp-0x6ad4` is on the OPPOSITE side from r24, and the argument
uses NO sign convention.** The r24 reconstruction generalises: every lane is a known transfer on a
signal that is on the wire, so each lane’s phase against rate is computable without observing it.
Measured inputs (2 controls pass: rate-vs-itself **+0.0°**, angle-vs-rate **−79.2°** against an ideal
−90°), torque at **−120.7°**:

| lane | out phase vs rate | note |
|---|---|---|
| `r24` / `r26` | **+143.7°** | span-4 diff gives **+84.4°** of lead |
| **`gp-0x6ad4`** | **+67.7°** | P/I/D gives only **+8.4°** — D and I antiphase and nearly cancel |

**Both carry the same `gp-0x6752` polarity, so the 76° split is the TRANSFER, not a polarity artefact.**
🛑 **The absolute labels are deliberately NOT relied on**: the kit records that its canonical `Re(Z)`
tool uses the OPPOSITE convention to a work factor, and that reading one against the other *"produced
the wrong answer twice"*. What survives any global flip is the **separation** — and the good side is
fixed by an **on-car measurement**: V88 raised r24 and cut 6–9 Hz to **0.859×**. ⇒ `gp-0x6ad4` is on the
harmful side. ⊕ **But size it before believing in it**: the PID lane is **exactly 0.25× r24 on all six
routes** (both scale with |T|), so as phasors **r24 187 ct ∠+143.7° + PID 47 ct ∠+67.7° = 203 ct
∠+130.8°** — the PID lane **erodes r24’s work factor from −0.806 to −0.653**, i.e. **19 %**, and
removing it entirely would buy back **~23 %**. **Real, quantified, and modest — not a fix.**
⚠ Open-loop; and the record’s opposite classification (*"net PID DAMPS"*) inverts **all three** P/I/D
terms, the signature of a convention flip rather than a physics disagreement.
Study: `analysis-2020accord/studies/mixer/lane_work_factors_who_pumps_the_ratchet.py`.

> ⭐⭐ **r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING IT CANNOT PASS — and the span cal is NOT a new
lever.** Two closures, both structural rather than empirical. ⊕ **First, a consistency check that
lands**: the measured torque phase reproduces the kit’s central symptom independently —
`Re(Z) ∝ cos(−120.7°) = −0.51 < 0`, the anti-damping replicated on three drives, now from a
convention pinned by a constructed +90° lead rather than assumed.
**CLOSURE 1 — the phase is capped by the SHAPE of a finite difference.**
`arg(1 − e^{−jωN·dt}) = 90° − ωN·dt/2 ≤ +90°` for **any** N > 0. So
`r24 phase ≤ −120.7 + 90 + 180 = +149.3°`, and **180° — a pure damper — is unreachable**. The work
factor is capped at **0.860**; the shipped N = 4 already delivers **0.806 = 94 % of that ceiling**.
⇒ **≥ 14 % of r24’s output is REACTIVE at the ratchet under ANY calibration**, and rotating it further
would need **more than 90° of lead** — a second derivative or a lead-lag. **No such cal exists on this
lane.** ✅ This is a fixed efficiency, not a diminishing return, so **damping still scales LINEARLY with
Lever B** — it supports V222/V223 rather than limiting them.
**CLOSURE 2 — `0xC6C42` (the span N, never moved in 219 images) is a redundant GAIN knob with a cliff.**
Across the whole usable range N = 1..7 the **phase moves only 8.4° while the magnitude moves 7.0×** —
**91 % magnitude, 9 % phase**. N = 7 buys **1.65×** the damping of N = 4, but that is pure magnitude,
which is Lever B’s job. And it is the **worse** way to buy it: 🛑 **N = 8 SILENTLY ZEROES the lane,
killing r24 AND r26 together** — so the in-range optimum sits **ONE STEP** from a double kill-switch
with no fault, no DTC and no symptom beyond losing the kit’s best lever; N is **shared with r26**, a
strictly wider blast radius; and Lever B has **12.5× headroom** bounded only by the ±8192 rail with no
dangerous neighbour. ⇒ **do NOT propose `0xC6C42`.** This block exists so it is not re-proposed.
Study: `analysis-2020accord/studies/mixer/r24_phase_is_structurally_capped.py`.

> ✅⭐ **DELIVERY LAG CANNOT INVERT r24 — the concern is retired, and the sign of the error is
FAVOURABLE.** r24 sits **36° short** of a pure damper, and transport lag rotates that at **2.80°/ms**
at 7.79 Hz, so a lag nobody had measured decided whether the kit’s best lever helps, is inert, or
inverts. **Attempt 1 — measure it from the wire — FAILED, honestly.** A phase slope from openpilot’s
command to steering rate needs coherence; measured over 6 routes engaged, the median is **0.140 / 0.162
/ 0.181 / 0.162 / 0.184 / 0.234** across 0.5–12 Hz. **Nothing clears 0.25**, so no delay is fitted — a
slope through coherence that low is noise. ⊕ The failure is informative: **the command explains only
~18 % of steering-rate variance at the ratchet**, independently supporting the record’s *"the EPS
generates it"* and *"a fast vibration cannot be COMMANDED via LKAS"*. **Attempt 2 — bound it
structurally — SUCCEEDS.** The confirmed task map puts the whole path inside **task 1 at 1 kHz**
(*"arbitration, the aggregator, shaper, governor"*), so charging **three full ticks plus the FOC
carrier** gives **3.25 ms = 9.1°**. Inversion to pumping needs **77.2 ms — 24× more**, i.e. ~77 task
ticks inside a chain that completes within **one**; inertness needs **109.3 ms**. Not a close call.
✅ **And the direction helps**: because r24 is short of 180° rather than past it, lag inside the bound
rotates it **toward** a pure damper — work factor **−0.805 → −0.889**. ⚠ A bound, not a measurement;
it rests on the on-car-confirmed 1 kHz task map and the recorded one-tick re-entry.
⊕ **Correction to a figure quoted mid-session**: the inert/pump thresholds are **109.3 ms / 77.2 ms**,
not the 32 / 51 ms first stated — those were computed rotating the wrong way. **The conclusion is
unchanged and strengthened.**
Study: `analysis-2020accord/studies/mixer/delivery_lag_cannot_invert_r24.py`.

> 🛑🛑⭐⭐ **SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED TO UNRESOLVED. The
separation-based conclusions are UNAFFECTED.** I published *"r24 DAMPS at 6–9 Hz"* as EVIDENCE earlier
this session. The first external check of that **absolute** label fails. The instrument makes a
retrodiction that can be tested against V88, which raised r24 and measured three bands on-car:

| band | φ(T,rate) | r24 phase | work factor | **V88 on-car** |
|---|---|---|---|---|
| ratchet 6–9 | −120.7° | +143.9° | **−0.808** | 0.859× |
| mid 9–12 | −150.8° | +111.6° | **−0.368** | 0.604× |
| grind 15–22 | **+119.8°** | +16.5° | **+0.959** | **0.549×** |

**V88 helped MOST at 15–22 Hz — exactly where the instrument says r24 pumps hardest.**
`corr(work, V88 ratio) = −0.803`; the prediction required **positive**. ➕ **Flipping the sign gives
+0.803 and retrodicts V88 across all three bands**, which is what a globally inverted frame looks like.
🛑 **My controls pinned the PIPELINE, not the PHYSICS.** A constructed +90° lead reading +90°, and a
viscous torque landing in quadrature, establish internal consistency — they say nothing about whether
r24’s output reaches the motor with the same sign as `cs_rate`. That frame question was flagged OPEN
from the start, and this is the first evidence bearing on it. ⚠ The evidence is **weak**: n = 3 bands,
not independent, and **V88 changed 5 bytes, not only Lever B**. It is not proof of an inversion — it is
enough to withdraw the absolute claim.
✅ **WHAT IS UNAFFECTED, BY DESIGN.** Every actionable conclusion was deliberately re-anchored on the
**separation between lanes plus V88’s on-car result**, with no absolute label in the chain: r24 and
`gp-0x6ad4` are **76° apart on opposite sides**, V88 fixes r24’s side as beneficial, the PID lane is
**0.25× r24**, **V227’s ceiling does not bind**, the **span cal is a redundant gain knob**, the phase is
**structurally capped**, and **delivery lag is bounded at 3.25 ms**. **None of those use the sign.**
⇒ **V222 remains the flight candidate and the guidance is unchanged**, because it rests on V88’s direct
measurement. ⇒ **What IS withdrawn**: any statement that r24 damps or pumps *in absolute terms*, and
with it the claim that the record’s *"net PID DAMPS"* is a convention flip — **it may be the record that
is right and me that is inverted.**
Study: `analysis-2020accord/studies/mixer/r24_retrodiction_test_fails.py`.

> ⭐⭐⭐ **THE ANTI-DAMPING IS BROADBAND AND ITS PEAK IS AT 9–10 Hz — BETWEEN the two bands the kit
treats as its symptoms.** `Re(Z) = Re(S_TR/S_RR)` measured over 6 routes engaged, magnitude-weighted
rather than phase-only:

| band | mean Re(Z) | mean cos | coherence | |
|---|---|---|---|---|
| ratchet 6–9 | −23.5 | −0.401 | 0.532 | |
| **mid 9–12** | **−67.9** | −0.784 | **0.618** | ← **strongest, and best-measured** |
| the gap 12–15 | −51.3 | **−0.986** | 0.511 | near-perfect antiphase, less magnitude |
| grind 15–22 | −14.2 | −0.591 | 0.631 | |

🛑 **`Re(Z)` is negative across the ENTIRE 4–24 Hz range** — this is **broadband** anti-damping, not a
narrow mode. Its magnitude peaks at **10 Hz (−71.5)** and the anti-damping **power** peaks at **9 Hz**.
⇒ the dominant energy exchange is **~3× the ratchet band and ~5× the grind band**, and it sits in
**9–12 Hz** — a band the kit **scores but has never treated as a target**, since its named symptoms map
to 6–9 (ratchet) and 15–22 (grinding).
➕ **A phase-only read would have put the peak at 13 Hz** (cos −0.998, essentially 179° opposed) — that
is the *phase* extremum, but torque amplitude is lower there, so the *impedance* extremum is at 9–10.
**Magnitude-weighting moved the answer; phase alone would have mis-aimed a lever by 3 Hz.**
✅ Unlike the command–rate coherence null (0.14–0.23), **torque–rate coherence is 0.44–0.76 across
7–23 Hz**, so this is a real measurement over its whole range.
⚠ The **absolute sign** of `Re(Z)` still depends on the unresolved frame; what is frame-free — and what
this block asserts — is the **SHAPE**: the extremum is at 9–10 Hz and the band ordering is
**mid > gap > ratchet > grind**.
⇒ **Consequence for lever design: size and aim at 9–12 Hz, not only at 6–9.**

> ✅ **AND V222’S AIM WAS CHECKED AGAINST THAT — the gap is real but MITIGATED, and the fix is
DEFERRED, not taken.** Computed from the image floats (`0xC60A8/AC/B0/B4`, direct-form II, 1 kHz):
the car is `f0 = 55.23 Hz, r = 0.7966`; V222 is `f0 = 20.50 Hz, r = 0.9575`. V222/car by band:
**6–9 0.998 · 9–12 0.955 · 12–15 0.805 · 15–22 0.281 · 22–30 0.402** ➕ 🛑 **CORRECTED 2026-08-30 — the figures first published here (0.970 / 0.924 / 0.366 / 0.821) came from a PARAMETRIC RECONSTRUCTION, not the image floats, and were WRONG in the pessimistic direction.** V222’s biquad is **NOT symmetric**: its zeros sit at 20.50 Hz but its **poles at 15.50 Hz** (Honda’s own are 12.88 Hz apart, so the shape is structural). A `coef(f0, r)` reconstruction places poles AT the zeros and does not reproduce the build.. ⇒ **the notch cuts the band with
the LEAST anti-damping 2.7× and the band with the MOST by 8 %.** ✅ **But V222 is not blind to the
peak**: Lever B’s transfer is a 4 ms difference, which **RISES** with frequency — `|H|` **0.1955 at
7.79 Hz → 0.2630 at 10.5 Hz = 1.35× stronger at the Re(Z) peak than at the ratchet.** The broadband
lever is best-aimed exactly where the narrowband one is weakest.
🛑 **RE-CENTRING to 13 Hz is REJECTED**: 9–12 would improve to 0.460, but 15–22 degrades **0.366 →
0.807** (surrendering a measured grinding win) and 22–30 goes to **1.402 — a BOOST**, in the region that
folds into the scored 30–49 Hz band.
⏸ **WIDENING is DEFERRED, not rejected.** Lowering the pole radius improves **both** target bands at
once (r = 0.92: 9–12 **0.813**, 15–22 **0.254**), with DC held at exactly **1.000000** by
`c4 = (1+a1+a2)/(2+b1)`. 🛑 **But the skirt extends DOWNWARD into 6–9 Hz — precisely the band where
V214–V217 found the shelf had been cutting a REAL damper 7.15× below the car, a defect found only
through an ABORTED DRIVE.** At r = 0.92 the trade is **8.7 % of the 6–9 damper for a 14.1 % deeper 9–12 cut and only 2.7 % on 15–22** — i.e. it buys almost all of its value in the peak band, which is the right place, but pays for it in the wrong one.
That is far smaller than the 7.15× that caused the abort — **but it is the same DIRECTION, on the one
band four builds were just spent repairing, and it buys 14 % on a notch already delivering 2.7×.**
⇒ **Fly V222 as built.** If its drive shows residual 9–12 Hz content, **r = 0.92 is the pre-computed
follow-up rung** (`a1 −1.82475755, a2 +0.84640000, b1 −1.983432120, c4 +1.30628962`).
Study: `analysis-2020accord/studies/mixer/notch_aim_vs_where_the_energy_is.py`.

> ✅⭐⭐ **AND THE NOTCH IS NOW CLOSED, NOT DEFERRED: V222 IS THE CONSTRAINED OPTIMUM OF ITS OWN
FAMILY.** Searched **109,446** configs (zeros 12–30 Hz × poles 5–30 Hz × r 0.70–0.985). The constraint
set had to be built in **three passes, because the optimiser exploited every omission**:
> ① **band-mean constraints** → an apparent **+360 %**, but the 6–9 *mean* of 1.019 concealed a
**1.265× POINTWISE peak at 6.0 Hz** and a **Q≈33 pole at 7.0 Hz sitting on the ratchet.** Rejected on
**GATE 2** — a lightly-damped pole inside an already anti-damped loop.
> ② **pointwise CEILING only** → an apparent **+394 %**, achieved by **cutting 6–9 Hz to 0.528** — a
1.9× cut of the damper, the V214–V217 defect’s own direction. I had added a ceiling and removed the
floor.
> ③ **pointwise ceiling AND floor, no global lift, no worsening of 52–71 Hz** → best feasible scores
**12.65 against V222’s 23.30, i.e. −45.7 %.**
> ⇒ **nothing in the biquad family beats V222.** Every “improvement” along the way was a missing
constraint. **The notch lever is CLOSED.**

> 🛑🛑⭐⭐ **AND A SCORING TRAP THE SEARCH SURFACED: DO NOT SCORE 30–49 Hz ACROSS THE V222/V122
BOUNDARY.** V222 **removes Honda’s 55 Hz notch** in order to place one at 20.50 Hz. Every cache runs at
**fs ≈ 101 Hz ⇒ Nyquist 50.5**, and the record establishes that **52–71 Hz folds into the scored
30–49 Hz band** from **above Nyquist**, where it can be neither seen nor filtered.
**mean |H| over 52–71 Hz: car 0.1700 vs V222 0.6392 ⇒ V222 passes 3.76× more.**
⚠ A **911×** ratio appears at 55.2 Hz but is an **ARTEFACT** of dividing by the car’s notch null
(|H| = 0.0007) — **the honest figure is the band mean, 3.76×.**
⇒ **any 30–49 Hz difference between V222 and the car is CONFOUNDED** by genuine 52–71 Hz content the
build no longer notches, folded down by the sample rate. **It cannot be separated post hoc.** This
applies to **every notch build**, not just V222.
Study: `analysis-2020accord/studies/mixer/notch_is_the_constrained_optimum_and_the_alias_cost.py`.

> 🛑⭐ **AND THE ALIAS COST CANNOT BE ENGINEERED AWAY — THERE IS EXACTLY ONE BIQUAD.** The obvious fix
for the 30–49 Hz confound is to keep Honda’s 55 Hz notch **and** add the 20.50 Hz one, which needs a
second second-order section. **There is not one.** Scanned the entire cal region **`0xC4000`–`0xD8000`**
at 4-byte stride for float quads with biquad structure (stability triangle `|a1| < 1+a2`, `0 < a2 < 1`,
`|b1| ≤ 2`, non-trivial `c4`), rejecting constant blocks and monotone runs (lookup tables) and
requiring the notch to fall in a plausible 1–200 Hz control band:

```
     addr           a1         a2         b1         c4   zero Hz  pole Hz     DC
   0xC60A8    -1.53720    0.63462   -1.88080    0.81731     55.23    42.35   1.0000   <- the only one
   biquad-shaped quads in the ENTIRE cal region: 1
```

⇒ **one section places ONE notch pair, so the 55 Hz vs 20.50 Hz choice is STRUCTURAL.** The alias cost
can be **ACCEPTED or REVERTED — it cannot be removed**, and reverting would surrender the 3.6× grind cut
that is the build’s main grinding lever. ⇒ **accept it, and score around it** (drive card already says
so).
⚠ **Scope, stated precisely**: this establishes there is exactly one **float32 biquad coefficient block
in the cal region**. A second-order filter implemented in a different numeric format (int16 Q-format)
or with a non-contiguous coefficient layout would not be caught by this scan — the claim is about the
float32 layout, not about every conceivable filter. The record independently calls `FUN_0003b8f6`
*"the dormant biquad"*, singular, which agrees.
➕ Related: Honda shipped this section **DISARMED** (`0xC649B` = 0); the kit armed it at V103.

> ✅⭐⭐ **THE LAST UNCHARACTERISED REGION IS CLOSED: THE FOC CURRENT LOOP IS TRANSPARENT AT THE
RATCHET.** `gp-0x6b98` is *"the final merged command and the only path to FOC"*, and everything below it
was the one stage the golden model only **abstracts** (`motor_pwm_output` is a placeholder
`duty = q_current_ref / 51200`, with *"[OPEN] the PWM carrier Hz"*). It is also where the record says
the ratchet physically lives — *"motor/rack-side, which no channel on this bus observes."* So it looked
like the obvious remaining place to search. **It is not, and the bound is not close.**
The model verifies the structure even where the carrier Hz is open: the FOC/PWM ISRs
(**EIIC 0x600** = ADC-complete inner loop, **0x970**) run **asynchronously and FAR FASTER** than the
1 kHz task, on a **~4–8 kHz** carrier. A current loop is tuned to 1/10–1/20 of switching ⇒ **200–800 Hz**
bandwidth. As a first-order loop at 7.79 Hz:

```
    BW (Hz)   |H| @7.79    phase        verdict
        800     0.99995    -0.56 deg    transparent   <- plausible for an 8 kHz carrier
        200     0.99924    -2.23 deg    transparent   <- plausible for a 4 kHz carrier
         50     0.98808    -8.86 deg    mild
         25     0.95472   -17.31 deg    mild
```

⇒ **even at an implausible 25 Hz bandwidth the loop contributes −17.3° and 0.955 gain.** For it to
matter at the ratchet (≈45°) the current loop would need **BW = 7.8 Hz — slower than the 1 kHz task
that feeds it**, contradicting the verified ISR structure.
⇒ **[EVIDENCE] the FOC gains cannot be a ratchet lever at any plausible tuning.** And *"motor/rack-side"*
points at the **PLANT** — mechanical, which **no firmware calibration can change** — not at this loop.
⚠ It is also the **worst edit class available**: motor control, **no instrument on it**, and code caves
in exactly this kind of region are this kit’s **only bricking class** (V24, V27, V48B).

> 🛑⭐⭐ **WITH THAT, THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION FROM THE AGGREGATOR.**
Upstream: the **aggregator lane census** is closed at 7.79 Hz and only r24 has ever been shown to help.
Downstream: the **governor** is retired by the task rate, and the **FOC loop** is transparent. Sideways:
the **notch** is the constrained optimum of its only second-order section, the **span cal** is a
redundant gain knob next to a double kill-switch, **creep damping** is exhausted, **authority** caps at
11×, **Lever B** is linear across its whole uint16 range, and **delivery lag** is bounded at 3.25 ms
against a 77 ms inversion threshold. ⇒ **The binding constraint is now a DRIVE, not analysis.** V222 is
built, verified and audited against all three asks; **nothing further can be learned about it from data
already on disk.**

> ✅⭐ **NEW GATE: NO ORPHAN BYTES. Every non-stock byte on the whole ladder has a written home.**
An **orphan** is a byte that differs from stock and that **no document in the kit mentions**. Orphans
are how this kit loses things: **V42’s ratchet fix sat silently REVERTED across eighteen builds
(V53–V70)** because nothing checked that the bytes on the candidate still matched the bytes the record
described. A byte nobody can explain is the same failure pointed the other way — and the operator is
entitled to know what every non-stock byte in his ECU does.

```
  build   payload bytes   runs   cited     record: 4998 distinct 0x addresses across 789 files
  V217         320         115   100.0 %
  V221         320         115   100.0 %
  V222         323         116   100.0 %   <- the flight candidate
  V223-V226    323         116   100.0 %
  V227         324         117   100.0 %
```

⇒ **ZERO orphan runs anywhere on the shelf.** ➕ Two cells that looked unannotated when I first grepped
are in fact fully documented — my search was too narrow, not the record: **`0x2A1F0` is V57’s decouple
displacement** (`746C`→`7CD0`, which is *why* the stock dump reads `0xFFFF` at `0xC6CD0`), and
**`0xC61C0`/`C2`/`C4` are the angle-rate tiers of the `STEER_STATUS` debounce SM** raised to unsigned
max at V36, with `0xC64B4`/`B6`/`B8` the matching V37 gentle-EME defeat.
⚠ **Scope:** this proves each byte has a written **home**, **not** that the annotation is correct,
current, or that the byte does what it claims — those need the lineage and a drive.
➕ Correcting a figure I gave the operator: the cumulative delta is **323** payload bytes, not 331; the
first count failed to exclude the `0xE4FFC`/`0xE5FFC` CRC trailers.
Gate: `analysis-2020accord/verify/no_orphan_bytes.py` (takes a build tag, defaults to v222).

> 🛑🛑⭐⭐⭐ **THE RATCHET BAND CANNOT BE SCORED BY BAND POWER — IT NEEDS ~7 HOURS PER ARM. This may
be why "nothing has moved micro-ratcheting in sixty builds."** The kit’s design law says every build
must be interpretable from ONE short symptomatic drive, and *"UNINTERPRETABLE is a DESIGN FAILURE on
our side."* That was never checked quantitatively. Measured, from real cached data — the
episode-to-episode spread of the band/control ratio, which **is** the noise floor for a single-episode
drive:

```
  band         sd(log10)   MDE, 1 episode/arm   MDE, 2 each   V88 measured on-car
  ratchet 6-9     0.587          42-45x            14.2x           0.859x
  mid 9-12        0.392          11-13x             5.9x           0.604x
  grind 15-22     0.426          13-15x             6.5x           0.549x
```

⇒ **one episode cannot resolve ANY of them**: the floor is 12–45× and the effects are 1.2–1.8×. V88 got
its 0.549× from a **full route**, not one episode. Exposure needed per arm at 80 % power:

```
  band          n episodes   minutes/arm      if V222 DOUBLES V88's effect
  grind 15-22        42          14.0          11 episodes,   3.7 min   achievable
  mid 9-12           51          17.0          13 episodes,   4.3 min   achievable
  ratchet 6-9      1241         413.7         311 episodes, 103.7 min   NOT achievable
```

🛑 **The ratchet band is 30× more expensive than the other two**, because its episode-to-episode
spread is a factor of **3.9** — the ratchet is INTERMITTENT, so 20 s windows vary enormously while the
effect is small. ⇒ **band power could never have detected a V88-sized ratchet improvement at any
exposure this operator has ever given.** ⚠ **That does NOT mean improvements happened** — it means the
instrument cannot answer the question, so sixty builds of "no ratchet change" is **weaker evidence than
it reads as.**
✅ **This is exactly why the standing instruction is "SCORE BANDS; LET THE OPERATOR SCORE SYMPTOMS"** —
now quantified. The operator’s verdict needs **one** episode; the band readout needs **minutes**. They
are different instruments and a 20 s band ratio must not be reported as evidence either way.
➕ **The known alternative for the ratchet is RING-DOWN** — the record calls ζ = 0.017–0.036 *"the only
estimator that passes its control"*, and it is a per-burst measurement rather than a band average, so
its variance structure is different. **Its power has NOT been computed; that is the open question.**

> ✅⭐ **AUTHORITY AUDIT: V222’S 8× STEP SCALES ITS CLAMP EXACTLY — margin identical to the car to four
digits.** A gain raise whose forward clamp does not follow silently turns the authority lever into a
**clipper**, so this was checked from the images rather than assumed. `lane_max = (0xC61BE × gain) >> 15`
must stay under the clamp `0xC61B2/B4`, which must stay under the EME wall `0xC674E`:

| build | gain | lane max | clamp | EME wall | margin |
|---|---|---|---|---|---|
| **V122 (the car)** | 6.0× | 2505 | 3072 | 5120 | **1.2263×** |
| **V217 / V221 / V222 / V223** | 8.0× | 3341 | 4096 | 5120 | **1.2260×** |
| V225 (the 10× rung) | 10.0× | 4176 | 4608 | 5120 | 1.1034× |

⇒ **V222 preserves the car’s clamp margin exactly** — the 8× step is proportional, not a bare gain
raise. ➕ **And V225’s smaller margin is NOT an oversight**: proportional scaling to 10× would need clamp
byte **20 = 5120, which is EXACTLY the EME wall**, and the ordering constraint requires strict
inequality. **18 is forced by the wall, not chosen carelessly.** ⚠ Byte **19** (margin 1.165×) was
available and would give **5.6 % more headroom** while still clearing — free if V225 is ever re-cut.
🛑 **STRUCTURAL CEILING ON THIS PATH — and it is CLOSE.** `lane_max` reaches the EME wall at 12.26×, but the practical limit is tighter because the clamp is a BYTE << 8 and must sit strictly between them:
```
    6x  lane 2505  clamp bytes 10..19  best margin 1.942x
    8x  lane 3341  clamp bytes 14..19  best margin 1.456x   <- V222
   10x  lane 4176  clamp bytes 17..19  best margin 1.165x   <- V225 (built with 18 = 1.103x)
   11x  lane 4594  clamp bytes 18..19  best margin 1.059x   <- the LAST workable step
   12x  lane 5011  NO VALID CLAMP EXISTS -- the path is exhausted
```
⇒ **the forward-gain authority lever has ONE ~10 % step left beyond V225, not an open runway.** Past 11× the clamp cannot be placed at all, and a gain raise there would clip by construction.

> ✅⭐ **THIRD ASK CLOSED — LEVER B CAN NEVER CLIP THE MICRO REGIME, AT ANY VALUE IN ITS RANGE.** The
record’s standing instruction on peak command oscillation is *"roughness is a SMALL-COMMAND phenomenon
… size levers for the micro regime"*, so the question is whether V222/V223 stay **linear where the
roughness actually lives**, not at the peaks. Measured `|dT|` over the span-4 ms window, pooled across
6 routes engaged, **n = 455,183**: **p50 16.5 · p90 104.1 · p99 298.9 · max 977.4** counts.
Lever B saturates when `|dT| × cal/1024 ≥ 8192`:

```
        cal   x car  |dT|_sat  sat duty  micro gain  delivered
       5244    1.0x    1599.7    0.000%       84.5     100.0%   <- the car
      13107    2.5x     640.0    0.014%      211.1     100.0%   <- V222
      26214    5.0x     320.0    0.740%      422.2      98.6%   <- V223
      39321    7.5x     213.3    3.093%      633.2      94.0%
      52428   10.0x     160.0    5.674%      844.3      88.1%
      65535   12.5x     128.0    7.859%     1055.4      82.6%   <- cal MAX (uint16)
```

⇒ **V222 delivers 100.0 % of its dose and V223 delivers 98.6 %** — both fully linear in the micro
regime, with micro gain scaling **exactly proportionally** (84.5 → 211 → 422). ➕ **And the whole ladder
is usable**: even at the cal maximum, saturation onset (128 ct) sits **7.8× above the p50 of 16.5 ct**,
so **no uint16 value can clip the regime the symptom lives in**; delivery degrades only gracefully, to
**82.6 %** at the extreme. ⚠ What DOES clip is the top of the distribution — 7.9 % of frames at cal max
— i.e. large excursions, not roughness. ⇒ **the dose reaches the symptom, and the ladder has room
beyond V223 if the drive asks for it.**
➕ Correcting my own working line: an intermediate print called the high end *"mostly clipped"*. It is
not — **82.6 % still arrives at the maximum.**

> ✅ **PRE-FLIGHT AUDIT OF ALL THREE ASKS IS NOW COMPLETE.** ① **Grinding** — the notch cuts 15–22 Hz
2.7×; it reaches the 9–12 Hz `Re(Z)` peak by only 8 %, but Lever B covers that band **1.35× more
strongly than the ratchet**, and both re-centring and widening are priced and deferred. ② **LKAS
authority** — the 8× step scales its clamp **exactly**, preserving the car’s margin to four digits;
the path’s structural ceiling is **11×**. ③ **Peak command oscillation** — the dose is **fully linear in
the micro regime** and cannot be clipped there at any cal. **Nothing in the audit argues against flying
V222 as built.**

> 🛑 **AND THE FRAME TEST IS INCONCLUSIVE — reported as such, not dressed up.** The plan was to
calibrate the pipeline against the operator-confirmed *"+ LKAS demands negative steering angle"*.
Measured: median `corr(sc_tq, cs_ang)` = **−0.166**, which matches the convention — **but 2 of 6 routes
come out POSITIVE** and the magnitudes are **0.015–0.413**, i.e. noise-level. The 0.1–0.5 Hz phase reads
**−89.3°**, dominated by plant dynamics rather than a clean 0/180 readout. ⇒ **the frame is NOT
resolvable from bus data**; it needs a probe putting the delivered assist on the wire with a known
sign, which is a cave build. **It blocks nothing** — every actionable conclusion is anchored on V88.

> 🛑 **RECORD DEFECT FIXED — `r95` is V101, not V102, and the correction had been made in only HALF
the files.** `r95` flew **V101 = 8× (`0xC6CD0` 7128) with Lever B REMOVED** (`GAIN8X.C6CD0.7128-NOLEVERB`);
`r95_v102_prereg.py` is the pre-registration **FOR** V102 **MEASURED ON** r95=V101, and its own docstring
says so — the filename was read as an attribution. `cal_association_scan.py` and `cal_scan_stability.py`
had already been corrected; **`dissociation_full_corpus.py` and `knee_headroom.py` had not**, and the
latter is a **cal-association scan**, so it was attaching **gain 5346 to a 7128 route — a 1.33× error on
the single most important cal.** All four now agree, with a guard that scans every live script.
➕ **Two image-reading traps recorded**, both of which returned plausible-looking wrong data rather than
an error: **(1)** in a `*_plain_image.bin` the **file offset IS the address** — rebasing by `0x13000`
yields `0xFFFF` for every cal and an arm byte of `0x63`; **(2)** a bare `*v104*` glob matches
`SUPERSEDED-DO-NOT-FLASH-…` **before** the live image, because `S` sorts before `_`.

> 🛑⭐⭐ **THE AGGREGATOR LANE CENSUS IS NOW CLOSED AT 7.79 Hz — and only ONE lane has ever been shown to help.** The return-to-centre analysis proves the ratchet enters through a **sensor-fed** lane, so the aggregator’s lanes are the whole search space. All ten now have a character: `gp-0x6b62` DEAD (0 of 75,227) · `gp-0x6ade` DEAD (0 writers) · `gp-0x6bd0` identically zero below 35 km/h · `gp-0x6bbe` viscous but at **76 % of its rail** · `gp-0x6ad4` **~85 % stiffness-like**, 14.6 % lead (V227 experiments here) · `gp-0x6b26` the restored damper, +518/+565 counts of positive Re(Z) · `gp-0x6b86` the notch lane, base assist not the command path · `r24` **Lever B, the one measured win**, doubled in V221/V222 · `r26` shares r24’s dtorque · and `gp-0x6b46`, **the last open one, closed here**. ⊕ `FUN_00036682` decompiles as a **first-order follower on scaled column torque with its own output as feedback**: τ = 1024/6 samples = **171 ms, fc 0.93 Hz**, giving **|H| 0.119 (−18.5 dB) at −81.8°** at the ratchet — reproducing the model’s recorded figures from the cal rather than quoting them. 🛑 **The attenuation is the FEATURE**: its input is column torque, so raising `0xC63D2` would inject torque-band content straight into the delivered command — the **opposite** of the stated lever class. The only direction that serves it is DOWN, and V124–V133 already went there (alpha 3, never flown). ⇒ **the cal-level search over aggregator lanes is complete; what remains is to fly what is built.** Study: `analysis-2020accord/studies/mixer/fun36682_is_a_slow_bias_tracker.py`.

> ⭐ **V227 — THE ONE RATCHET LANE NOBODY HAS SCORED.** The model’s lane census calls `gp-0x6ad4` *"the most reachable authority of any gated lane"* and states that **V56’s mute of it was scored at ~21 Hz, so the lane has NEVER been scored at 6–9 Hz — OPEN, not eliminated."* Its return-to-centre analysis independently narrows the ratchet’s entry to a **sensor-fed** lane, leaving {r24/r26, `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`, the plant-model path} — and of those, r24 is Lever B (already at 13107), `gp-0x6b26` is the restored damper, `gp-0x6bbe` sits at 76 % of its rail, and the plant-model path is `0xC63AE`. **`gp-0x6ad4` is the one left.** The lever is its ceiling LERP knee: `0xC67C4` **1280→512**, so the ceiling reaches full at **8 km/h instead of 20** — **3.00× at 3 and 6 km/h, 2.25× at 10, and IDENTICAL from 20 km/h up**; Y is asserted unchanged, so it moves the KNEE not the height. **Virgin in 216 of 218 images** — only V162/V163 ever carried it, and that branch was orphaned at the rebase to V164, **the same rebase that orphaned Lever B’s 6553**. Built as **V227 = V222 + one halfword**, 78/78. ⊕ **What the cell actually feeds, confirmed in the disassembly: TWO roles.** The `0xC67C2` LERP produces `iVar10`, used as **(1)** the symmetric output clamp on `gp-0x6ad4` (`0x3a88c-0x3a894`) and **(2)** the **anti-windup window on the integrator** (`iVar10*32 ± P`). The clamp half cannot invert a sign — a symmetric clamp is memoryless and odd. The anti-windup half **can** change dynamics: an integrator with headroom stops saturating and contributes its full phase. ⊕ **PRICED FROM THE CALS: it binds through the INTEGRATOR, and "inert" is now UNLIKELY.** Kp 256 / Ki 98 flat / Kd 2048 flat / Kout unity, and **both EMA cals are 1024 — alpha = 1.0, no filtering at all** ⇒ `out = 0.25*err + 2*d(err) + I/32`, |gain| at 7.79 Hz = **0.268**. The **output clamp** needs |err| ≈ **849 counts at 6 km/h** and err is a *tracking* error, so it probably misses. But the **integrator gains 0.0957·err EVERY MILLISECOND** into a window of only ±bound×32 — at 3 km/h a sustained 100-count error pins it in **191 ms**, which is the normal operating condition rather than a rare excursion. V227 **triples that window** (±1824 → ±5472 at 3 km/h). 🛑 **That sharpens the risk rather than removing it**: an integrator allowed to run longer contributes more low-frequency phase lag — the classic way to make a lightly-damped mode WORSE. ⚠ And a **third outcome is INERT** — both roles act only where the bound BINDS, and nothing measures |PID sum| because `gp-0x6ad4` is not mirrored anywhere. ⊕ **AND AT 7.79 Hz THE LANE IS ~85 % STIFFNESS, NOT DAMPING.** As phasors from the same cals: P **0.2500** @ 0°, D **0.0979** @ +90°, I **0.0611** @ −90° — D and I antiphase and largely cancelling, leaving **0.0368 net lead against 0.2500 in phase with the error**, i.e. a **14.6 % lead fraction**. `err` is a TORQUE error, so the in-phase part is stiffness-like rather than damping-of-velocity, and **stiffening a loop around a lightly-damped resonance is a recognised way to make it MORE prominent**. The integrator equals P only at **1.90 Hz** and is 24 % of the output at the ratchet, so V227’s anti-windup effect is smaller there than at DC. ⇒ **V227 is reclassified as an EXPERIMENT on the one unscored lane, not a candidate fix** — the arithmetic is open-loop and says nothing about the closed loop, which is why it still earns a drive, but expect nothing. 🛑 **OPEN lever, NOT a predicted fix**: whether more authority there damps or **pumps** 6–9 Hz depends on a loop phase nobody has measured — that is what "never scored" means — so **it can make the ratchet worse**, and it is cal-only and reversible. ⊕ Gate [19] **correctly fired** on the table-knot move; it is now a **build-scoped** exception naming one cell on one build, with a staleness check, rather than a widened whitelist. **1107 checks, 0 failed.**

> 🛑⭐ **THE "459×" HEADLINE FOR THE ABORTED DRIVE IS RATE-CONFOUNDED — the within-spectrum figures are not.** That number is normalised against a **creep-matched** corpus median, i.e. matched on SPEED only, and at the same speed r7d’s wheel was running **6.6× faster** than its control (|rate| p50 24.00 vs 3.61). Whether that matters is testable without r7d, on the routes that have exposure: over **1,368 engaged windows across 7 routes** (6 of 7 positive), **log 30–35 Hz power vs log RATE corr +0.739 (p<0.0001)** against **vs log SPEED corr −0.182** — weaker *and negative*. By rate quartile the band moves **63×** across the range. ⇒ a speed-matched comparison leaves that 6.6× inside the number, so **459× is an UPPER BOUND, not a measurement.** ⊕ **The same run says how to normalise it away**: `log(30-35 / 12-18) vs log RATE` has **corr −0.041, p=0.13 — no rate dependence at all**, because rate lifts the bands together. So a band-to-control RATIO is rate-robust while raw band power is not. ⇒ **what survives is every r7d figure that is a within-spectrum ratio** — prominence **56×**, **56 %** of 5–49 Hz power sitting in 30–35, and the engaged/manual contrast **54×** (same route, same rates on both arms). 🛑 **r7d is NOT withdrawn** — it is re-based onto statistics it already had. Study: `analysis-2020accord/studies/mixer/the_459x_is_rate_confounded.py`.

> 🛑⭐ **RETRACTION — MY OWN "CUTTING APPARENT INERTIA RAISES LOOP GAIN BROADBAND" DOES NOT SURVIVE.** I measured it **creep-matched, i.e. SPEED-matched**, over 9 routes (corr −0.853 / −0.747 / −0.574 / −0.790, every band together). It was already flagged as carried by one drive (perm p 0.0087 → 0.2486 without `r7d`) and confounded with build order (+0.750). I then established separately that **speed-matching a rate-driven signal manufactures an effect** — and `gp-0x6b26` is `-K*alpha`, acceleration feedback, **rate-driven**. So it was built on the estimator I had just shown to be wrong for this class of signal. Re-run rate-matched: **every correlation flips POSITIVE** (+0.23 to +0.74) and **none is significant** (all p ≥ 0.19); and 🛑 **r7d is absent from every rate bin** — 1,084 engaged frames is too few for a windowed spectrum, so the instrument **cannot test the low-dose end at all**, which is exactly where the effect was claimed. ⇒ **the inference is WITHDRAWN**: one drive, confounded with build order, measured on the wrong axis, sign-unstable when corrected. ⊕ **What stands:** the *description* of r7d (the ≈31 Hz line, in-loop, absent from the command), and the build decision — V214–V217 restored the damper to the car’s own value on *"match the flown image"*, never on a dose-response. Study: `analysis-2020accord/studies/mixer/inertia_dose_broadband_lift_retracted.py`.

> ⭐ **THE RATE-MATCHED INSTRUMENT NOW WORKS — and the knee trend it finds does NOT survive its own checks.** Gating SAMPLES on instantaneous rate fragments the signal below a spectral window (0 usable windows in 3 of 4 bands). Classifying **whole windows by their own median rate**, with a within-window spread cap p90/p50≤3, gives **175/86/148** windows in the slowest bin. The manual side is still empty at low rate on these routes, so each window is normalised **within itself** against the 30–40 Hz control band — alias-contaminated, but identically on every route, so usable as a cross-route normaliser and nothing absolute rests on it. Tool: `rlog-tools/score/rate_matched_band_ratio.py`. **What looks like a finding:** grind 15–22 is monotone decreasing in onset at 3–8 (4.133/3.603/2.580) and 8–20 (5.493/5.449/2.965), with V111-vs-V122 CIs **disjoint in both** — read alone, a sharper relay carries MORE grind energy, so V222’s knee restoration would REDUCE it. **Why it is not claimed:** the largest bin (0–3, n=175/86/148) sorts **nothing**; the ratchet band at 8–20 is **non-monotone** while grind is monotone, which a loop lever should not do; the **middle** onset is highest in mid 9–12, a route signature; onset is confounded with build number; and the arithmetic predicts no effect below 50 counts of rate anyway. ⇒ **[BELIEF, WEAK], not claimed** — and the V222 drive settles it for free, since V222 sits at onset 250 where the whole V196–V217 shelf sat at 50. Study: `analysis-2020accord/studies/mixer/relay_knee_ladder_window_classified.py`.

> ⭐ **A SLOPE-CONTROLLED, THREE-POINT, FLOWN LADDER ON THE RELAY KNEE — AND IT SHOWS NOTHING.** Route `r21`’s cache said **"UNKNOWN-V108-or-V111"**; V108 and V111 differ in only 3 payload cells with a **byte-identical cave**, so the rungs cannot tell them apart. Resolved from the record (`HANDOFF-2026-08-28-v112` tabulates `r21 V111`, written by the session that flew `r22` as V112 whose own base is V111), which unlocks **83,782 engaged frames** and exposes a ladder nobody had noticed: **V111/r21 onset 50 · V112/r22 onset 150 · V122/r24 onset 250**, all with the **same unsaturated slope 0.003984**, and V111→V112 a **true single-variable pair — 2 cells, 4 payload bytes**. That is the controlled experiment the record’s *"de-relaying made the ratchet 2.3× worse"* never had. **Result: non-monotone in every symptom band, and the CONTROL band orders identically to them** (both [0,2,1]) ⇒ route difference, not a lever. ⊕ **It agrees with the arithmetic**: with the slope held the three settings are identical below 50 counts of rate, and the ratchet lives at 1–13 °/s — so V222 restoring the knee 600→3000 should not move the symptom bands, and does not. 🛑 **Method limit: rate-gating and Welch are incompatible** — gating on an INSTANTANEOUS rate fragments the signal below a spectral window and **3 of 4 rate bands returned ZERO usable windows**. This is a WEAK instrument that found nothing, not a strong one that proved nothing. Study: `analysis-2020accord/studies/mixer/relay_knee_flown_ladder_null.py`.

> 🛑⭐ **THE ABORTED DRIVE’S FRICTION RELAY WAS NORMAL FOR ITS RATE — and speed-matching said otherwise.** `r7d` flew V94, which carries V90’s cave **byte-for-byte**, and `r77` flew V90 — so both read **the same rungs** with **identical friction cals** (`0xC40BC` 600, `0xC40D2` 102). That makes `r77` the natural control for the aborted drive and nobody had used it. Speed-matched at creep it looks like a finding: `b5` (*the modelled Coulomb friction is non-zero*) reads **0.746 vs 0.886**, 1.19× more relay activity on the drive that was stopped. A 1 s block bootstrap already refused it, and the reason is one column nobody would print: **at the same SPEED the aborted drive’s wheel was moving 6.6× faster** (|rate| p50 3.61 vs 24.00). Matched on the axis the relay’s own arithmetic uses — `ratio = clamp(rate*12/cal(0xC40BC), ±1)` — the difference **vanishes**: b5 reads 0.466/0.473, 0.997/0.962, 1.000/0.992 across matched rate bands, largest gap **0.035**, and marginally LOWER on the aborted drive; b6 has no consistent direction. ⇒ **[EVIDENCE] the firmware’s own friction state on that drive was normal for its rate**, so **its signature is not in the friction lane**. 🛑 **Method: speed-matching a rate-driven signal manufactures an effect** — the same trap the record already names for the ratchet, on a different quantity. ⊕ The rung values come from `rlog-tools/probe/sweep_cave_rungs.py`, added the same day; it also corrects two defects in its own first version, the important one being that `r97` has **NO CAVE** (probe byte stuck at stock 0x07 across 68,883 engaged frames) rather than five rungs that never fire. Study: `analysis-2020accord/studies/mixer/aborted_drive_friction_relay_is_normal.py`.

> ⭐ **THE DELIVERED COMMAND’S SYMPTOM-BAND CONTENT IS SENSOR-SHARED, NOT COMMAND-SHARED — measured on `gp-0x6b94` ITSELF.** The stated lever class is *"less broadband HF in the delivered command"*, but that had only ever been argued from proxies. Route `r85` flew V100, whose 427 probe telemeters the aggregator output itself with its sign on a cave bit, and that cache had never been used this way. Coherence² over **60 engaged 4 s windows**, both inputs on the SAME windows: **2–4 Hz 0.163 vs 0.041 · 6–9 Hz 0.235 vs 0.085 · 9–12 Hz 0.134 vs 0.049 · 12–18 Hz 0.241 vs 0.051** against a shuffled null of 0.002–0.006 ⇒ **2.9–5.2× more coherent with the COLUMN than with openpilot’s request, in every band including the ratchet’s.** Whatever sits in the delivered command there is **loop content, not commanded content** — the same conclusion V88’s signed-command test reached from the other side, and **independent support for Lever B’s lever class**. 🛑 **The control had to be fixed first**: the initial shuffled-pairs null read **exactly 1.000** because a coherence from ONE segment pair is identically 1 — the null must average over MISMATCHED pairs the way the measurement averages over matched ones. ⚠ Limits, stated: **closed loop so no causal arrow**; absolute coherences 0.13–0.24 so neither input alone explains most of the variance; `r85` is **highway (11.0 m/s), not creep**; and nothing above ~20 Hz, since 427 is a ~50 Hz stream ZOH’d to 100. Study: `analysis-2020accord/studies/mixer/delivered_command_is_sensor_fed_not_commanded.py`.

> 🛑⭐ **THE TWO CLAMPS THAT COULD ZERO THE RATCHET LEVER NEVER SATURATE — MEASURED, WITH A LIVE CONTROL.** The golden model warns that `|gp-0x6ad6| >= cal(0xC6200) = 8192` makes `d(gp-0x6ad4)/d(gp-0x6b70)` **exactly zero through P, I and D at once**, and flagged both clamps as **never measured**. That bears directly on the shelf: the ratchet lever `0xC63AE` acts by scaling the residual into `gp-0x6b70`, so a saturating reference clamp would make it dead on those frames — the V64 failure, *"the null is on the GATE, not the hypothesis"*. **The measurement existed all along: V100 flew as route `r85` and its cave carries exactly these two bits.** Pooled over six cached segments, **49,850 engaged frames: d(b5) = d(b6) = 0.000000**, 95 % upper bound **6.0e-05**. 🛑 **The positive control is what makes it a result rather than a dead probe** — same cave, same route: `b3` is the deliberate constant-1 identity bit (the cave RAN) and `b4`/`b7` toggle **4,343** and **3,153** times. ⇒ **[EVIDENCE] neither clamp saturates engaged**, the `0.2565 @ 7.79 Hz` unsaturated derivative is valid essentially always, and **the ratchet lever is NOT gated off**. ⊕ It transfers to the candidate in the SAFE direction: `gp-0x6b70` IS term 7 of `gp-0x6ad6`, and V222 HALVES `0xC63AE`, shrinking that term — if V100 never reached the clamp, V222 reaches it less. ⚠ Directional for term 7, not a proof for the whole sum. 🛑 `0xC6200` is **four things at once** and has **40 readers** — do not edit it. Study: `analysis-2020accord/studies/mixer/pid_reference_clamp_duty_measured.py`; the model’s stale note is corrected in place, contract re-verified.

> 🛑⭐ **LEVER B’S INPUT HAS A SILENT KILL-SWITCH, AND A FLOWN DRIVE BOUNDS AN OPEN CLOCK QUESTION.** `gp-0x4f62` is produced by `FUN_0007e74a` as a **span-N finite difference over an 8-slot ring**, N = `0xC6C42` = 4, dividing by the MEASURED dt — so the magnitude is right at any rate and **only the PHASE depends on the span**, `lag = 180*f*N*T`. 🛑 **The code’s own guard is `if N < 8 ... else gp-0x4f62 = 0`, so writing 8 or more ZEROES the torque rate and kills r24 AND r26 together** — Lever B would report its full 13107 gain and deliver **nothing**, and every existing check would still pass, because they all check the GAIN and never its input. `0xC6C42` = 4 in **all 218 images**, so it has never bitten; a gate now asserts it and was negative-tested. ⊕ **V88 bounds the producer rate**: the SIGN of an effect at a known frequency is a phase measurement, and V88 measured **15–22 Hz → 0.549×, i.e. DAMPING**. A span-4 difference stops damping at 90°, which at 20.5 Hz needs T ≥ 6.10 ms ⇒ **the producer runs faster than ~164 Hz, and a 100 Hz ring is EXCLUDED** (it would have PUMPED, cos = −0.844). The measured profile corroborates it — damping STRENGTHENS with frequency (0.859 → 0.604 → 0.549), where a lag near 90° would weaken it. ⇒ **at ~1 kHz the lag is 5.6° at 7.79 Hz, so Lever B is already near-pure damping and there is NO lever here — N = 4 left alone.** Study: `analysis-2020accord/studies/mixer/lever_b_input_phase_and_killswitch.py`.

> 🛑⭐ **THE THREE RUNG-2 ARMS WERE STALE — REBASED ONTO V222 AS V224/V225/V226.** V218, V219 and V220 were cut off **V217**, so each LACKED **Lever B at 13107** and the **friction-lane restoration**. Flying one after V222 would have **silently handed back two levers** — the same failure shape as [[V42’s ratchet fix lost at a rebase]] and the damper cut hidden inside V196–V213. Each arm is rebuilt on V222’s base carrying its own lever and nothing else: **V224** `0xC63AE` 512→256 (ratchet) · **V225** `0xC6CD0` 8×→10× **with its clamps** `0xC61B3/B5` 16→18 (authority) · **V226** notch poles 15.50→13.50 (grind). **All five builds — V222, V223, V224, V225, V226 — now share the same 23 payload bytes from the car**, differing only by the one lever each exists to test. ⊕ Registered in all three verifier lists, and a **new gate** makes the 10× arm’s clamp raise mandatory: a gain raise without `0xC61B3/B5` = 18 is not the priced build and now fails. ⇒ **1044 checks, 0 failed** (was 950).

> 🛑⭐ **THE CLOSE-OUT DID NOT COVER THE FLIGHT CANDIDATE.** `PUB` in `closeout_verify_published.py` **stopped at V220** while **V222 was the recommended build**, so the artifact being handed over for flashing had passed **none** of the 835 checks — not gate [17]’s delta manifest, not [14]’s damper pricing, not [16]’s cave anchor, not [21]’s notch arm. Cause: three separate build lists (`PUB`, the shelf rebuild, the 427 decoder) and only two were kept in step. **Adding V221–V223 immediately fired two gates, both correctly:** the staged-gain gate (they carry V217’s 8× step byte-identically — added to the priced set with the reason recorded) and the **Lever B anti-drift gate**, which is the protection that catches silent lever loss. 🛑 **It was NOT widened**: Lever B is now a deliberate ladder, so the gate keeps ONE expected value per build and enumerates it — 13107 for V221/V222, 26214 for V223, **5244 as the default for every other build**, so an unlisted or new build still fails on drift. ⊕ Negative-tested: reverting V222’s Lever B, demoting V223’s rung, and moving one rail byte each made the gate fire; images restored and hash-verified. ⇒ **835 → 950 checks, 0 failed.** ⊕ Same tick: an audit of every checkable numeric claim in the golden-model facade — **4/4 survive**; the pedestal figure was its only error. New do-not-edit fact: `0xC6200` (the assist-map input clamp, 8192) has **40 readers**.

> 🛑⭐ **THE NOTCH’S PEDESTAL BYPASS IS OVERSTATED 4.1× — A CORRECTION TO THE FILE AGENTS READ FIRST.** The golden-model facade warns that `gp-0x6b7e`, added to the biquad output AFTER the filter, *"passes 64.6 % of its input STRAIGHT PAST THE BIQUAD"* at 19.75 Hz. **That figure is the clamp ceiling (K = 204), not the cal.** Read from the image: the direct cal `0xC6382` = **41**, and the 4-point LERP at `0xC6906..0xC690C` has Y = **[20, 20, 20, 20]** — **flat, so not a shaped lever at all**. The reachable set is K ∈ {20, 41}: fc 1.55 / 3.19 Hz, |H(20 Hz)| = **0.078 / 0.159**. ⇒ **max bypass 0.159, not 0.646**, and **the notch is correspondingly LESS diluted than the record has been claiming** — good news for the shelf’s main grinding lever. Both cals are **VIRGIN in all 215 images**; driving K to its floor of 2 takes the bypass to 0.008 but caps out at removing a 15.9 % path, so it is a small lever, not the missing one. ⚠ This bounds the pedestal’s TRANSFER, not how much 20 Hz energy its input carries — only a measurement settles the split. ⊕ Re-confirmed while tracing: `gp-0x6b86` is the **base power-assist** output, not the LKAS command, so **no notch dose can cost LKAS authority or fix command oscillation directly**. Golden-model contract re-verified after the edit: 87 symbols, 2,512 bytes, hash unchanged.

> 🛑⭐ **LEVER B’S REAL CEILING IS ITS DESCRIBING FUNCTION, AND V222 IS NOWHERE NEAR IT.** The lane is a plain saturation (slope k, rail ±8192), so for a sinusoid of amplitude A the effective damping the loop sees is `N(A)/k = (2/pi)[asin(1/rho) + (1/rho)sqrt(1-1/rho^2)]`, `rho = k*A/(L*1024)`, and as k→∞ it tends to `4L*1024/(pi*A)` — **a constant independent of k**. That asymptote is the ceiling, not the cal range and not V160’s non-existent int16 bound. Evaluated at route `r24`’s engaged torque-rate percentiles: the knee (one more doubling buys <20 %) is at **k = 58624 for p90, 14080 for p99 and 5184 for the largest excursion**. ⇒ **at the amplitudes where the roughness lives, V222’s 13107 is far below the knee** — one more doubling buys a full **2×** at p50 and p90 — **while buying essentially nothing at the largest excursion** (1.20×→1.23× even at the cal maximum), so the rung is selective for the small-signal regime by construction. ⊕ **The saturation worry is not new: the car at 5244 is ALREADY past the large-amplitude knee of 5184**, and V88’s measured win came from 512→5244, the very step that carried the largest excursions across it. **V223 = V222 + 13107→26214** is built as rung 2. Study: `analysis-2020accord/studies/mixer/lever_b_describing_function_optimum.py`.

> 🛑⭐ **THE CAL-LEVEL SEARCH SPACE FOR CREEP-REGIME DAMPING IS EXHAUSTED.** Roughness is a small-command phenomenon, so the lever must live at creep. Every cal path there is closed, from the bytes. **The base-assist damper is a PRODUCT of five Q10 LERP gains and two are exactly zero at creep** — FactorC (axis SPEED) is dead below 35 km/h and FactorE (axis RATE) below 60 counts, and since both `Y[0]` are 0, **scaling any record by any k is structurally vacuous**. ⊕ **The edit nobody has ever made:** across **all 214 images on disk** the FactorC X axis is `(2240, 3840, 5120, 8960)` — **exactly one distinct vector, never once moved** — while `Y[0]` has been set **nine** different ways across ~40 builds. Every arming attempt raised `Y[0]` at a FIXED `X[0]`, which puts a **step** at 35 km/h; that is how V80 became a relay and flew as the worst grinding ever measured. So the untried edit is lowering `X[0]` to extend the RAMP down — V80’s own stated lesson — and **it fails too**: even at `X[0]` = 64 (1 km/h) the product reaches only **0.096 % of full gain**, because FactorE contributes just 5.6 % at a 200-count motor rate. The other four candidates are each closed on their own terms: `gp-0x6bbe` (the one measured viscous lane) is already at **76 % of its ±512 rail** so its virgin weight `0xC63A2` would amplify a part-relay signal; `0xC40D2` needs k1 = 25600 to halve the residual at 5 °/s, **25× past the sign-inversion boundary**; ranking the lanes from the 427 probe’s seven historical source cells is not possible from the existing caches (only `r95` carries a decoded 427 magnitude channel); and a notch is already excluded because the ratcheting is not a tone the EPS commands. ⇒ **what remains is to fly what is built, or a code cave** — this kit’s only bricking class. Study: `analysis-2020accord/studies/mixer/creep_damping_search_space_closed.py`.

> 🛑⭐ **V216 RESTORED THE FRICTION LANE’S SLOPE BUT NOT ITS SATURATION — A 216× DIFFERENCE FROM THE CAR ON FAST STEERING.** `FUN_0003b8f6` is the **plant-model observer**: `ratio = clamp(polarity * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)`, `friction = EMA(|model| * ratio * cal(0xC40D2)/1024)`, `model_out = clamp((model - (friction + damping)) * cal(0xC6468), +-20000)` → `gp-0x6b70`. The unsaturated slope is `12*k1/gate/1024` and V216 matched the car **exactly** (0.003984 both: car gate 3000/k1 1020, shelf 600/204) — which is why every check passed. But what each SATURATES AT is `k1/1024` of the whole model: the car models friction at **99.6 %** and the shelf at **19.9 %**, so above 250 counts of rate the car’s observer residual is **annihilated** (model_out 7) while the shelf’s stays fully live (1512) — **216×**. 🛑 **The ratchet regime is 1.0× identical at every rate the ratchet occupies**, so no ratchet expectation changes; this is a FAST-STEERING claim only. **V222 restores both cells** and drops the delta from 27 to 23 payload bytes. ⚠ A close-out entry listing `0xC40D2` = 204 as *"the FLOWN car"* was REMOVED — the car is 1020, and that mislabel is exactly why the gap survived. ⊕ **And the record’s headline for this cell is NOT IDENTIFIED**: *"de-relaying made the ratchet 2.3× worse"* (600 vs 6000, 30 routes) held `k1` at 102 while the gate moved 10×, so the small-signal slope fell 10× too (0.001992 → 0.000199). *"De-relayed"* and *"10× less modelled friction"* fit equally well and are different levers. `0xC40D2` alone separates them — 1 reader (`0x3BAFE`), 0 writers, with a **real** boundary at k1 = 1024 where the residual is identically zero and beyond which the sign inverts. Never tested in isolation.

> 🛑⭐ **BOTH TESTABLE READINGS OF "PEAK COMMAND OSCILLATION" ARE NEGATIVE, AND THE ROUGHNESS IS AT THE OPPOSITE END.** 🛑 Bands are instruments — this does not score the symptom, it says where the roughness sits. **(1) The command reversing after a peak: REFUTED twice.** Integral windup fails its own dose-response (reversal vs time-at-rail corr **+0.099, p=0.188**, n=179; partial **+0.101, p=0.177** with lateral demand removed; per-route corrs +0.189/+0.005/−0.167/−0.263/+0.244, **two negative**). ⚠ **And a first result of mine is RETRACTED**: railed-vs-near-rail gave a 2.86× ratio in 5/5 routes, but the control was broken — a near-rail *run* can end because the command wandered out of the band mid-manoeuvre, so its "exit" is an arbitrary sample rather than a peak. On **true local maxima**, measured identically in both arms: railed p75 **0.155** vs not-railed p75 **0.207** (*the control is higher*), and corr(peak magnitude, reversal) **+0.024, p=0.48, n=858**. **(2) The car oscillating while the command is large: REFUTED, and it reverses.** Over **3,711** two-second engaged windows, the roughness ratio P(6–30 Hz)/P(0.5–3 Hz) by command quartile is **2.49 / 2.85 / 2.43 / 0.66** — the top quartile is **3.7× SMOOTHER** (corr −0.358, p<0.0001). Raw HF power does rise (+0.491) but the manoeuvre rises faster (+0.793). ⇒ **the roughness is a SMALL-COMMAND, small-signal phenomenon, so levers must be sized for the MICRO REGIME, not peak demand** — which independently validates V221’s Lever B dose (onset 640 counts vs the car’s engaged torque-rate p90 of 146). Study: `analysis-2020accord/studies/mixer/peak_command_oscillation_two_readings.py`.

> 🛑⭐ **LKAS AUTHORITY NOW HAS A DIRECT MEASUREMENT, AND THE ONE 8× DRIVE IN THE CORPUS IS CONFOUNDED.** openpilot’s command **pins at ±4096 on 2.7 % of engaged frames on the car’s own drive**, in **sustained 475–732 ms runs** (max 6 s), same-signed between runs, with steer rate 6–21× higher than off-rail ⇒ honest saturation in real manoeuvres, not hunting and not a decode artifact. On `r24` the command’s p90 is 733 but its **p99 is the rail**. When it is pinned openpilot has **no authority left**, so rail duty at matched lateral demand (`|curvature| × speed²`) is a direct authority metric needing no plant model. Among Lever-B-carrying builds it is monotone: **4× → 6× cuts rail duty 8.3× / 5.2× / 4.1× / 2.3× / 1.5×** across rising demand bins. 🛑 **The apparent counter-evidence at 8× is a confound**: the single 8× route (`r95`, **V101**) **removed Lever B in the same build** — byte-checked `0xC6446` = 512 and arm `0x3AA96` = `c5`, both stock, against 5244/`fb` everywhere else. More forward gain with less loop damping needs more command to hold a line. ⇒ **no clean 8× data point exists, and V221 is the first build ever to pair 8× with Lever B RAISED rather than removed.** Readout: `rlog-tools/score/score_authority.py` (self-tests to 1.00× on `r24`, 4.05–7.18× on a 4× route). Study: `analysis-2020accord/studies/mixer/lkas_command_rail_duty_vs_gain.py`.

> 🛑⭐ **V160'S INT16 CEILING ON LEVER B IS FALSE, AND IT FROZE THE KIT'S BEST LEVER FOR 130+ BUILDS.** `0xC6446` — the r24 engaged derivative gain, the only lever that has ever moved both symptom families at once with the LKAS command measurably untouched (V88: 15–22 Hz **0.549×**, 9–12 Hz **0.604×**, 6–9 Hz **0.859×**, 0.5–3 Hz **1.192 = NULL**; operator report *grinding fixed, command intact*) — has been **5244 on every build since V67**. V160 raised it to 6553 and called that *"the EXACT int16 ceiling for this lane"*. There is no int16 anywhere on the path. Decompiled first, then confirmed instruction by instruction: `0x3AC08 ld.hu` (zero-extended ⇒ the cal's own range is 0–65535) → `0x3AC18 mul r10,r8,r0` (**32-bit**, high word discarded) → `0x3AC20 sar 0xa` (still 32-bit) → `0x3AC42/46` the ±8192 output clamp, **the only bound, and an immediate**. Worst case 5120 × 65535 = 3.4e8, an order of magnitude inside int32. ⇒ **real headroom above the car is 12.5×, not 1.25×.** V160/V161/V163 built 6553 three times, never flew, and it was orphaned at a rebase to V164. V221 takes it to **13107**, chosen so the saturation onset (640 counts) stays 4.4× clear of route `r24`'s own engaged p90 torque-rate (146) — the micro regime where ratcheting and grinding live remains fully linear. The ±8192 **rail is asserted byte-identical**, so this structurally cannot cost LKAS authority. 🛑 **Only two dose points exist (512, 5244)** and V62's lesson is *"2× is the OPTIMUM, not a point on a ramp"* — so V221 is a **dose probe as much as a fix**.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-30-the-cal-search-closes.md` — the cal search closes in every direction, V227 is measured inert at the ratchet, a 30–49 Hz scoring trap, and **five withdrawn claims (three of them mine)**. Prior: `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-damper-the-shelf-was-cutting.md` — the damper finding, the mixer decode, five self-retractions, and the open-items list with what would close each. Prior: `HANDOFF-2026-08-29-the-assist-map-session.md`.

## 📁 **EARLIER STATE (V204 → V208) IS ARCHIVED — with its closures kept here**

Split out 2026-08-30 at **138.6 KB**, against the ~150 KB soft target. The narrative, the numbers
and the retractions now live in `docs/archive/STATE-ARCHIVE-2026-08-30-v204-v208.md` — **a record,
not an instruction.** What that era CLOSED is kept below, because a closure is what stops a lever
being re-proposed:

| closed | verdict |
|---|---|
| the notch shelf | was cutting a **real 6–9 Hz damper 7.15× below the car**; fixed V214–V217 |
| the saturation census | **closed** — the last gate cannot fire; V207 retired **before** flight |
| `gp-0x6b70` saturation | **does not saturate**; V206’s best argument retracted |
| the command-gated-saturation model | **no mechanism exists** in this path — no gate rejects either |
| the 8 Hz ratchet notch | **stays rejected**; the friction lane is NOT "reverted to Honda" |
| two authority levers | **checked and closed**; a latent 18.52 Hz injector found silent |
| `0xC63AA` sensitivity | **41× understated** in the old record |
| the relay | a **SOFT** relay, curve **built at runtime** — unreadable from the image |
| `0xC63AE` sign | established **without a drive**; V206 built and priced |

🛑 **Tooling gotcha kept live, because it still bites:** `stock_fw_dump/code.bin` reads `0xFFFF`
at `0xC6CD0` because **V57 created that cell**. Do not use the stock dump as a stock reference for
post-V57 migrated cals — it hands you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and
`0xC64DE` read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
