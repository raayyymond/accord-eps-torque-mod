---
name: accord-v293-torque-mode-built-the-model-independent-test
description: "🛑🛑⭐⭐⭐⭐⭐ V293 BUILT 2026-09-13, NOT FLOWN — CLEARED AS THE FLIGHT CANDIDATE OVER ONE DISSENT (B2 as written), V282 the fallback, the fork preset MANDATORY (Testing Ground 9 'Accord EPS Torque Mode' variant B: LAF 6.0 / friction 0.00 / Kp 0.3 / Ki 0.15, rate-plant FF OFF), the first drive an IDENTIFICATION drive, the low-speed 1–4 Hz V276 signature the FIRST revert trigger; the decision to fly is the operator's and nothing licenses a claim that grinding or stutter is fixed. A/C/D PASS; B1, B3, B4, B5, B7 PASS and B8 reported; B2 and B6 FAIL AS WRITTEN and both are adjudicated — B6 is a broken check (it condemns flown V282 3/10 cells, worst PM 35.6°, against V293's 3/10 worst 33.2°), B2 is adjudicated PASS on intent because its calibration was measured on V292, a build that did NOT open the loop, and |S| ≡ 1 is an identity the bytes prove. Standing fork defect found on the way: StarPilot feeds error_with_lsf into get_friction where upstream feeds the raw error ⇒ compensator gain (friction/0.30)·(1+lsf/kp), ×17.9 at Kp 0.3 and ×6.6 LIVE on V282 today; a LOWER Kp is WORSE; repair is preset friction 0.00. 🛑 A's carried finding governs the language: the sub-rail slope is 10.34 counts/idx vs V282's 21.35 at fb = 0, so below idx 116 V293 delivers 0.47–0.49 of V282's STALLED-wheel torque — NEVER write 'authority unchanged' about V293 and never show only the rail. TORQUE MODE on the V282 base, cal-only, not one code byte: 0xC62E6 46080 → 0 (the fb saturation clamp; the LKAS rate loop is OPEN at every frequency, E = 32·setpoint), the Kd bank 0xCB7D4 → 0 AND 0xC61B6 → 0 (D ≡ 0 twice over, which the prereg's A1 clause requires), the Kp bank 0xCB994 all 28 records → 120 flat (V282's Kp 248 at fb = 0 would rail from idx 116), 0xC6446 5244 → 2048 (the orchestrator's ruling against the design's 4451). Class: V279 rev 2's structure rebased onto V282 — never-tried, not falsified. image f75e77cf…, rwd ac472386…, 378 diff bytes over 6 CRC blocks, 242 assertions, 16/16 mutations, independent rebuild reproduces. Peak authority ×1.000 — the DELIVERED rail is 2461 on BOTH images (2462 is the linear DC, 2505 the structural ceiling; never quote 2505 as delivered). Predicted ring ×0.285 (on-car anchor ×0.24–0.29) for a 5–9 Hz price of ×1.74–1.85 broadband / ×2.10 on loaded high-angle windows. 🛑 The predictor's one out-of-sample test FAILED on V292. ~90 % of the ring benefit is Kd = 0 + Kp, not the clamp; there is NO intermediate clamp dose. Fork: one selection, Testing Ground 9 'Accord EPS Torque Mode' variant B, uncommitted, ships on A -- reworked from a param the same day, all five AccordEpsTorqueMode/AccordTorqueMode* keys DELETED, and SAFE MODE NO LONGER FORCES IT OFF (it manages params; Testing Grounds are not params)."
metadata:
  node_type: memory
  type: project
---

**What it is.** V282 + cal cells and cal records only — **not one code byte, no cave.**
**image `f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17`** · **rwd
`ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba`**
(`39990-TVA,A160-V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd`;
**exactly one V293 rwd on disk**). Both re-hashed from the files at close-out; the builder's dry run and
the build-audit adversary's **independent rebuild from the V282 image + the prereg's edit list** land on
the same two. **242 assertions** (census 64 substantive / 172 vacuous / 6 tautological, post-`scriptfix`), **16/16 mutations
caught**. **378 diff bytes over 6 CRC blocks**, re-derived a third time straight from the two images:
1 (`0xC62E7`) + 1 (`0xC61B7`) + 2 (`0xC6446–47`) + **112 Kd knots** + **240 Kp knots** = 356 payload,
+ **22** trailer bytes. ⚠ **Two of the six trailers differ in only 3 of 4 bytes** (`0xE6FFC`, `0xE7FFC`),
so a scan that requires a full 4-byte trailer run finds only FOUR blocks and undercounts.

| cell | STOCK | V282 | **V293** | what it is |
|---|---|---|---|---|
| `0xC62E6` | 7680 | 46080 | **0** | the LKAS rate-PID **feedback saturation clamp** at `0x28FA6–0x28FBE`, before `sub r26,r16` @`0x29D78`. Zero forces the feedback operand to exactly 0 on **all three branches** ⇒ `E = 32·setpoint`. Three accessors image-wide (`0x28F96`/`0x28F9C`/`0x28FB8`), all `ld.hu`, **zero writers** |
| Kd bank `0xCB7D4` (28 records) | 128 | 128 | **0** | `D = (dE·0)>>3 = 0` exactly. With fb dead, `dE = 32·d(setpoint)` is a pure setpoint kick: one demand-index count near the map top is `dE = 137`, i.e. `D = 2192` at Kd 128 = **87 % of the delivered peak from one command step** |
| `0xC61B6` | 10240 | 10240 | **0** | the **D clamp**, same three-branch idiom ⇒ D = 0 on every branch. 7 readers, 0 writers. Carried **alongside** the Kd zero because the prereg's A1 FAILs unless D is exactly zero **with either cell alone** |
| Kp bank `0xCB994` (all 28) | 248…717 | **flat per slot 205/248/266/307** (V281r3 flattened each to its own Y[0]; live slot 7 = 248) | **120 flat** | at fb = 0, `P = (32·Y·Kp)>>8`; Kp 120 on V282's map reaches 15480 at idx 240 and clips to V282's **own** 15360 P-rail, linear below. V282's Kp 248 at fb = 0 would rail from **idx 116 (48 % of demand)**. All 28 because **the fb clamp is ONE GLOBAL cell while Kp is per-slot** (selector measured 7, max 9 ⇒ a contingency). 🛑 **Kp 119 is ruled out by prereg A2** — it delivers 2504, one count below V282's rail |
| `0xC6446` | 512 | 5244 | **2048** | the r24 engaged arm |

Everything else byte-identical to V282: the ×6 map, clamps 15360/3072, gain 5346, `Ki = 0`, the fb lag pole
923/1560 (**its state keeps running; only its clamped output is zero**), the output lag, the override taper,
the idx clamps, the `0x14A` cave rungs **b4–b7** (b3 stays V282's **aliased** bit, NOT V292's fb-state rung)
and the `0x1AB` tap of `gp-0x6b38`.

**Class [EVIDENCE].** **V279 rev 2's structure (built 2026-09-02, never flown) rebased onto V282** — the
LKAS lane stops being a rate regulator and becomes a linear **torque map**, `T = f(cmd)·taper`. **Never-tried,
not falsified.** V279 passed five attackers with `0xC62E6` = 0 on a V268 base, and `0x28F7C–0x28FC8` plus
`0x29D78` are **byte-identical V268 → V282**, so that proof transfers. New here: the base, the r24 dose, the
fork preset. The nearest FLOWN relative is **V276**, which limit-cycled at 2–4 Hz — which is why the outer
loop is **gated** (prereg B6), not assumed.

🛑 **THE RAIL — three numbers have been called it and only ONE is delivered.** **2461** is the DELIVERED
rail, the byte-exact steady state through the fade and the output lag, and it reads **2461 on the V293
image AND on the V282 image** (the residue is the output lag's integer fixed-point interval). **2462** is
the same chain's **LINEAR DC** — what the tracer reported. **2505** is the **structural ceiling**
`min((15360·5346)>>15, 3072)`, the `T_ceil` convention the V279/V282/V292 docstrings print. **Never quote
2505 as delivered; neither build reaches it at fade 254.** ⇒ the design doc's *"peak ×0.9992, 2461 vs
2463"* is superseded: **peak authority is ×1.000**, and the ×0.9992 came from comparing the two builds by
two different methods. 🛑 **2461 is an AT-REST number** — the prereg's erratum shows the taper is **ONE
speed-derated stage, not two** (`factor = ((tapAB·tapCD) & 0xFFFF) >> 8`, 254/256 at rest only because
both halves return 255 there), and that **the live speed table is D (`0xCBBC4`), selected by `gp-0x6803`**
(the `0xE4` `SET_ME_X00` field openpilot sends as 0) — **the kit memory was right, the tracer's C
(`0xCBAE4`) reading wrong.** Condition every on-car rail read on speed, and score "identical rail" on
matched trajectories, since the output lag's floors give an interval of fixed points.

**Authority — three senses, and they disagree.** Peak **×1.000** (2461 delivered on both images) ·
torque at a given command **with the wheel still ×0.48**
below idx 115, rising to ×1.00 at 240 · torque **delivered on the operator's own episodes ×0.82 rms** on
r39's grinding windows and **×3.6** on loaded high-angle turns, because V282's servo has already nulled
there. **Sense 3 is the one he drives.** No single Kp makes all three ×1.00 — V282's delivered torque is not
a function of the command at all. 🛑 *"×6 rate setpoint"* **has no meaning under torque mode** (a setpoint
means something only because a loop tracks it).

**The trade, stated as a trade.** Ring predicted **×0.285** [0.27, 0.30] on r39's loudest windows, **×0.40**
on r6c, with an **on-car anchor** — the reciprocal of V282's own measured engaged ÷ disengaged ratio — of
**×0.24–0.29**; ζ(20 Hz) 0.030 → 0.157–0.325. **Price: the 5–9 Hz wheel band rises ×1.74–1.85 broadband and
×2.10 (r39) / ×1.45 (r35) on loaded high-angle windows**, because V282's loop is a disturbance-rejecting
servo below ~13 Hz and opening it removes that rejection (`|1 + L_V282(7.3 Hz)| = 2.04`). **That is the band
V292's flight just measured rising, and the band the operator called worse.** 🛑 **The one out-of-sample
test of this predictor FAILED on V292** (×0.535 predicted, the loop's contribution measured UP ×1.20–2.00),
and the failure is the **method's** — the design agent reproduced the published number with its own
implementation. Stall class removed arithmetically: P-rail duty 0.66 → 0.000 on r31's own stall window.
**Outer loop is NOT the risk**: Ms 1.09–1.38 vs V282's 1.04–1.35, PM 64° vs 66°; no cell in the 6×3×3 grid
reproduces V276's signature that V282 does not also reproduce — **V276's shape returns as a feedforward
mis-scaling ×3.17 at 5 m/s**, which the fork preset prevents.

**⭐ Two findings that belong in the operator's hands before he decides.** (1) Sweeping `0xC62E6` 46080 → 0
with Kp 120 / Kd 0 held moves the ring only **×0.299 → ×0.272** ⇒ **~90 % of the ring benefit is Kd = 0 and
the Kp re-level, not the clamp**; the clamp is what changes the delivered **quantity** (the goal's other
half) and is nearly free on the ring. **The two goals are separable.** (2) 🛑 **There is NO intermediate
dose** — `0xC62E6` is a **clamp, not a gain**, so a small non-zero value is a **Coulomb relay on
sign(wheel rate)**: swept byte-exact at 256/512/1024/2048/4096 every value is worse than 0 on every column,
and with the command frozen the relay **adds** 18–22 Hz (×1.005–1.079) and 5–9 Hz (×1.02–1.10) motion.

**Why r24 = 2048 and not the design's 4451 [BELIEF, and deliberately scoreable].** The orchestrator ruled it
before any image existed: (i) the same model under-predicted V292's measured 5–9 Hz cost **three-fold**, so
a criterion-exact arm (4451 restores gate73 to exactly 1.010) carries no margin against the loudest symptom;
(ii) 2048 is the record's own priced lever (*"7.3 Hz ring 0.98 → 0.48, no margin or authority cost"*);
(iii) ⭐ **in torque mode the cut is FREE at 20 Hz** — with the servo present, cutting r24 costs ζ (paired
Δζ −0.044/−0.075/−0.086 at κ 0.10/0.20/0.45), with the servo **gone** it **RAISES** ζ (+0.036/+0.097/+0.183,
96–100 % of plants): **r24's apparent 20 Hz damping was a partial cancellation of the servo's de-damping.**
Adversarial B is briefed to score 4451 and 2048 **side by side**, so the ruling is falsifiable. ⚠ The other
end is closed: `0xC6446` = 512 is **not** a free improvement — V70 at 512 put grind #1 back at creep.

**READ IT BY.** The first drive is an **IDENTIFICATION drive, not a symptom drive** (hands-off, laterally
engaged, ≥ 400 frame pairs per |τ| bucket in ≥ 4 buckets to |τ| 0.5, both signs, fitted by instrumental
variables against `modelV2.action.desiredCurvature·v²` — **not** from `torqued`, whose buckets do not fill
on this car). Then the tune, then the symptom drive. On the symptom drive: the within-frame identity
`T_tap = f(cmd)·taper` with `sign(T) = −sign(cmd)` ≈ 1.00 proving the feedback is dead (T saturating below
the map top means the map is not the live source); the ring by the **drive-controlled** measure only;
F7 and tap ripple/level at |angle| ≥ 30°; a 1–4 Hz line in command **and** angle; b4–b7 duties as the r24
control. Edit-live control: regress `|427 tap|` on `f(cmd)·fade` — R² **−4.82 → +0.92**, residual 349 → 47
counts; b7 duty 0.996 → 0.808 is the mover, b4 the negative control.

**THE SENTENCE A NULL LICENSES:** *if the 18–22 Hz ring's amplitude and ring-down are unchanged with the
LKAS loop open on every frame — the identity holding — then the 20 Hz object is not the LKAS loop's, and
the whole in-loop class, V38 → V293, is closed.* **REVERT IF:** grinding unchanged (his word); the 6–9 Hz
ripple returns (F7 ≥ 2/100 s or ripple/level ≥ 0.25); **a 1–4 Hz oscillation of command and angle — the
V276 signature, the fix is the fork preset not the firmware, but the drive stops**; a 10–18 Hz line; a
darty or loose feel; a one-sided pull at rest; any EME or DTC.

**The fork side — one Testing Ground slot, and the mismatch is NOT symmetric.** **Testing Ground 9,
"Accord EPS Torque Mode", variant B**, **uncommitted, ships on A**. 🛑 **Reworked from a param to a slot
on 2026-09-13, hours after it first shipped** — the operator rejected a toggle whose only job is to apply
a preset of other toggles, and the fork already had the mechanism (A = installed tune, B = experiment).
**`AccordEpsTorqueMode` and the four `AccordTorqueMode*` keys no longer exist** in params_keys, the
Galaxy layout, `starpilot_variables` or `SAFE_MODE_MANAGED_KEYS`; the selection lives in
`/data/testing_grounds/slots.json` and the gate is `testing_ground.use("9","B")`, so any other slot
equals A. **B only while a torque-map image (V293+) is in the ECU.** To V293: **flash first, select B
second**; reverting: **select A first, flash second**. 🛑 B + rate-servo image = **OVER-DELIVERY,
feedforward ×2.55, and nothing downstream catches it** (`opendbc/safety/modes/honda.h` applies no
magnitude, rate, driver-torque or RT-window limit to `0xE4`). A + torque-map image = under-delivery,
recoverable. 🛑🛑 **SAFE MODE NO LONGER FORCES IT OFF** — it manages params and has never touched Testing
Grounds, so a trip leaves B active; correct on V293, but not a route back to the rate-servo tune during a
revert. Provisional tune, all four PROVISIONAL and now **CONSTANTS not sliders** (re-tuning needs a source
edit and a reinstall): LAF 6.0 (carried over, **not an identification**), friction **0.00**, Kp 0.3,
Ki 0.15 — net command ×0.929 of today's at one operating point, **a coincidence, not a margin**. Verify
from `starpilotLateralState.epsTorqueMode` at 100 Hz, **not** from `initData.params` — the mode is not a
param at all, so its absence there is expected and means nothing. ⭐ The **selection** is logged too, as
`customReserved9` (slotId/slotName/variant/variantLabel/reason), on a 15 s `the_galaxy` heartbeat plus
every manual change — corroboration, not a gate.

**🛑 STATUS — THE PASS IS COMPLETE AND V293 IS CLEARED OVER ONE DISSENT.**

> **V293 is CLEARED as the flight candidate over ONE DISSENT (B2 as written), with V282 the fallback, the
> fork preset (Testing Ground 9 "Accord EPS Torque Mode" variant B: LAF 6.0 / friction 0.00 / Kp 0.3 /
> Ki 0.15, rate-plant FF OFF)
> MANDATORY, the first drive an IDENTIFICATION drive, and the low-speed 1–4 Hz signature the first revert
> trigger. The decision to fly is the operator's. Nothing licenses any claim that the grinding or the
> stutter is fixed — he scores the symptom; the pre-registered read and the terminal null sentence stand.**

**A PASS (A1–A4) · C PASS (C1–C5) · D PASS (D1–D5) · B: B1, B3, B4, B5, B7 PASS, B8 reported, B2 and B6
FAIL AS WRITTEN and both adjudicated.**
- 🛑 **B6 FAIL AS WRITTEN at the MEASURED τ — a BROKEN CHECK that fires cleanly.** V293 at the repaired
  preset breaks **3 of 10** controller-loop cells (worst **PM 33.2°** at 5 m/s / τ 0.25) and **flown V282
  at its own tune breaks 3 of 10 too** (worst **PM 35.6°** at 28.5 m/s / τ 0.22); both go unstable inside
  [0.5×, 2×] on the path-following channel. **Scored on intent — no worse than the build on the car — it
  PASSES.** ⚠ **Residual: the creep margin at 5 m/s is ~10–20 % of plant gain on BOTH builds; the failure
  mode there is the V276 1–4 Hz signature, the first thing to watch.**
- **B4 PASS, the thinnest margin in the pass** — ripple/level 0.028/0.034/0.048 vs a 0.25 gate (stock
  0.044/0.033/0.087, **V293 sits between stock and V282**); predicted F7 ≈ 1.24/100 s vs 2, **×1.6 only**.
- **B7 PASS** — 0/250 plants with ζ < 0.10 in 10–18 Hz; 13–17 Hz ×1.058 vs a ×1.5 gate.
- **B8** — the command-driven 18–22 Hz torque is **×0.055–0.137 of V282's ring and has NO POLE: it cannot
  ring.**
- 🛑 **`advB3` DIED of an out-of-memory error** after B3 and the B6 sub-check; **`advB3b` completed the rest.**
- **A PASS on A1–A4** — the clamp block simulated from its own decoded bytes over **4,023 int32 states
  gives ZERO non-zero operands**, against a **capable-null control of 4,012 for V282 at 46080**; `D ≡ 0`
  by **each cell alone**; `0x2A0C6` unreachable by three methods incl. **zero LE32 hits of `0xFEDF17F6`**
  (this closes the tracer's residual); **rail 2461 = 2461** on matched cold-start trajectories; **P first
  rails at idx 239**; linear fit **10.336·idx − 1.89**; b3 is V282's aliased `ld.w gp-0x3680`; the tap
  under-reads by 0–7 counts.
- 🛑🛑 **A's CARRIED FINDING — NOT GATED, AND IT GOVERNS HOW THIS BUILD MAY BE DESCRIBED. The sub-rail
  slope is 10.34 counts/idx against V282's 21.35 at fb = 0.** Below idx 116, **V293 delivers 0.47–0.49 of
  V282's STALLED-WHEEL torque** (idx 58: **598 vs 1236**), meeting it only at idx 239–240: *"the peak is
  identical and needs twice the demand to reach."* ⇒ 🛑 **NEVER WRITE "AUTHORITY UNCHANGED" ABOUT V293,
  AND NEVER SHOW ONLY THE RAIL.**
- 🛑🛑 **B6 INTERIM FAIL — on the build + PRESET PAIR, and the FIRMWARE IS NOT THE DEFECT.** PM **22.8°**
  at 5 m/s / κ 1.00 / τ 0.20 s (Ms 4.32, crossover 0.82 Hz), because StarPilot feeds **`error_with_lsf`**
  (= `error·(1 + lsf/kp)`) into `get_friction` where upstream feeds the **raw** error ⇒ compensator gain
  **`(friction/0.30)·(1 + lsf/kp)` = ×17.9** at Kp 0.3 and 5 m/s. ⭐ **A LOWER Kp IS WORSE** (loop gain
  minimised near Kp ≈ 1.0) — which **inverts the preset's own rationale for Kp 0.3**. **Repair is
  fork-side: preset friction 0.01 → 0.00** ⇒ PM 42.2°, Ms 2.06, GM ×1.40. ⚠ Conditional on **τ ≥ 0.18 s**,
  and **τ = 0.20 s is the operator's `SteerDelay` toggle ECHOED, not identified** (Honda port prior
  0.10 s). ✅ **The 1–4 Hz V276 signature does NOT reproduce on frequency** (cycles at 1.21–1.25 Hz).
  ⚠ The clause's literal "[0.5×, 2×]" wording is **broken** (V282 fails it at 28.5 m/s κ 2) but **the FAIL
  does not rest on it** — κ 1.00, where V282 reads 40.1°.
- **B3 PASS** before the agent died: rail **×1.000000 by three methods**, slope **0.641212 counts/CAN
  count**, P clamp binds at **idx 239**. 🛑 **`advB3` then DIED of an OUT-OF-MEMORY error mid-run**;
  **`advB3b`** is re-running B1, B2, B4, B5, B7, B8 and the B6 re-score at the repaired preset.
- 🛑🛑 **TWO RECORD DEFECTS `advB3` FOUND ON ITS WAY DOWN, both in machinery other results rest on.**
  **(a) The module-default `B(f)` fit is BAD** — `nb=1, nd=4` gives rms `ln|B|` 0.54, phase 38° and **a
  spurious UNSTABLE 4.5 Hz root**; **use the design's `nb=1, nd=3`** and re-check anything fitted with
  the default. **(b) `r24_plant_refit.py` cannot regenerate `r24_plant_refit.json`** — `fit_B(nb=4, nd=2)`
  now raises on the properness guard, so **the prereg's own named reference family for B1 is not
  reproducible from its own script**; the JSON is an artifact with no working producer.
- ⭐ **r24 ARM CORRECTION: `0xC6440` = 2048 is the DISENGAGED arm and reads 2048 on EVERY image including
  STOCK** (Honda's stock ENGAGED arm is `0xC6446` = 512). ⇒ **V293 sets the engaged arm EQUAL to the
  disengaged one** — a far more interpretable dose than "a rung between 512 and 5244".
  ✅ **RESOLVED: the lane is SWITCHED, not gated off** — `g = 1024 if gp-0x671d else 0xC6446 if lateral
  else 0xC6440` (`0x3ABFE` / `0x3AC08` / `0x3AC12`) ⇒ **on V293 the r24 lane is BIT-IDENTICAL engaged and
  disengaged**, so the on-car ×0.24–0.29 anchor is an **ESTIMATE of V293's ring, not a lower bound**.
  ⚠ Three residuals keep it an estimate: V293 still injects `f(cmd)` (forced ring **3.49** vs V282's
  **10.30** counts on the replay); the disengaged reference is **mostly stationary**; and the **r26
  base-assist arm `0xC6444` also moves with the `0x3AA96` gate** — unresolved.
- **B1 PASS at 2048** — 0 unstable fits on every family and κ; **4451 has 5 unstable** on the broad family
  at κ 0.45. ⚠ The literal `ζ < 0.05` clause is **broken** (condemns flown V282 on 250/250 and 12/12),
  scored as "no unstable fit and no worse than V282"; ⚠ **the both-poles family at κ 1.45 is EMPTY
  (n = 0)**, unscoreable.
- **B5 PASS at 2048** — 5–9 Hz **×1.50–1.59 vs V282**, **×1.05–1.13 vs STOCK**, under both thresholds;
  **4451 trips the first leg on r39**. ⭐ **The rise is BROADBAND, peakiness UNCHANGED** — structurally
  unlike V292's resonant 7 Hz re-arm.
- ⭐⭐ **B1 + B5 VINDICATE THE 2048 RULING**: it was recorded as BELIEF against the design's 4451, briefed
  to be scored side by side, and **2048 wins on both clauses while 4451 fails each**. Now EVIDENCE there.
- 🛑 **B2 FAIL AS PRE-REGISTERED — adjudication is the orchestrator's, pending the full B table.** The
  mandated V292 calibration (**×1.90–3.64**) on the replay's ×0.285/×0.403 gives **×0.54–1.47 vs a
  ≤ ×0.50 gate**; **the uncalibrated replay and the on-car anchor both PASS**; and that calibration
  **over-predicts ×1.3–2.0** against the car's own measured open-loop configuration. **The anchor is
  usable at 18–22 Hz but NOT at 5–9 Hz, where it and the replay disagree in SIGN.**
- ⏱ **τ MEASURED — and "τ = 0.20 s" was never a measurement** (`TAU-ACTUATOR-DELAY-2026-09-13.md`, six
  routes, `controlsState.desiredCurvature` → steering-angle curvature; the `0xE4` → rate pair is
  **unusable**, the rate-plant FF makes the wheel **LEAD** by one round trip): **258 ms** [251, 264] at
  3–8 m/s, **232** at 8–15, **211** at 15–25, **182** at 25+. ⭐ **V292's routes sit inside that scatter —
  V292 changed nothing; the TUNE did.** 🛑 **Not a pure delay** (three estimators differ by up to 100 ms;
  the fitted pole is **1.4–4.3 Hz = the torque controller's bandwidth plus plant, NOT the EPS servo**) ⇒
  **use `tau_eq(f)` at the crossover**; the dead-time/servo-lag split is **not identified**, so **quote
  totals**. ⇒ **B6's τ ≥ 0.18 s premise HOLDS at every band**, with margin at the 5 m/s FAIL point.
  🛑 **Nothing in the fork measures τ:** `liveDelay.lateralDelay` is the toggle echoed;
  `lateralDelayEstimate` is **~99 % seed**, gated ≥ 15 m/s, on livePose yaw that lags the gyro 73–90 ms;
  and `full_lateral_delay(x) = x + 0.2` while **`lagd`'s toggle branch skips that wrapper**, so the field
  **mixes two conventions** (a fork defect, reported not fixed).
- **C PASS** — independent rebuild byte-identical. Non-blocking: the substantive census **overstated
  by 23**; **seven single-knot mutations invisible to the assertions**; the tag does not encode the D-clamp
  integer; two docstring errors. **None in the artifact.**
- **D1 PASS, and the number is what makes it one.** This was the clause most likely to return do-not-flash,
  because a torque-mode lane holds full commanded torque however fast the wheel already moves, so **dwell
  at the rail rises even though the peak does not.** The census found the mechanism and bounded it: the
  **soft-EME integrator `gp-0x3570` in the shaper `FUN_00042af8`** arms **SM2 at `|I>>15| ≥ 15361`** on the
  excess of `|cmd|` over `max(corridor, IIR, boost floor 5120)`; ⭐ **the LKAS lane's rail ≈ 2481 cannot
  reach the bound at all**; the only newly opened band is **`5120 < |cmd| ≤ 5325` needing 75 ms CONTINUOUS
  residency**; SM2/SM3 self-clear; `FUN_0007b022`'s energy budget is unreachable; every interlock cal
  byte-identical. ⚠ **D5's wording is FALSE but INERT** — the dead island *does* read `0xC61B6`, uncalled.
- **A and B have not reported. B carries B5 (the 5–9 Hz rise) and B6 (the outer loop) plus the side-by-side
  scoring of r24 4451 vs 2048 — until it does, the trade above is a design claim, not an adjudicated one.**

**Build-hygiene facts worth carrying:** **378 diff bytes, ZERO below `0xC0000`** (the cal-only claim is a
byte fact, not a docstring claim). 🛑 **The SCRIPT hash moved and the IMAGE hash did not** —
`build_v293_tva.py` was `8ffb29a9…` at write time, then `scriptfix` applied C's four hygiene fixes and it
is `27d6ff76…`, while the image re-hashes to `f75e77cf…` unchanged. **Quote a script hash with its moment;
the artifact is the invariant.**

Sources: prereg `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` · design
`docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md` · lineage
`docs/BUILD-LINEAGE-PART6-V291-ONWARD.md` · trace
`docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` · card
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` · builder
`analysis-2020accord/builds/v108_plus/build_v293_tva.py`.

Related: [[accord-v292-flew-and-is-a-revert-7hz-rearmed-ring-not-reduced]],
[[accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05]],
[[accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted]],
[[accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz]],
[[accord-lkas-commands-rate-not-torque]], [[accord-v276-mechanism-is-a-matter-of-degree]],
[[project-starpilot-fork-lateral-state-2026-09-10]].
