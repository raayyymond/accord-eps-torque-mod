# STATE ARCHIVE — blocks moved out of `docs/STATE.md` on 2026-08-30

These are a RECORD of what was believed when written, not an instruction. They were moved to keep
`STATE.md` under its working target; nothing here was retracted by the move. 26 blocks, 55.3 KB.

---

> 🛑🛑⭐⭐⭐⭐⭐ **V235 BUILT — THE CELL-BY-CELL AUDIT FOUND ONE MORE UNJUSTIFIED CELL, AND V235 IS NOW THE CAR PLUS THREE THINGS.**
>
> The audit the close-out contract asks for, run against **STOCK**: V234 differs in **115 non-CRC runs**, of which **only 6 also differ from the car**. The other 109 are what he already drives and need no new justification. Of the 6, five were justified (the notch ×4, the probe) and **one was not**.
> 🛑 **`0xC63AE` = 512 was carried by every build since V206/V210 and is UNPRICED — STATE.md's own words: *“a ratchet null licenses nothing, because `0xC63AE` is unpriced.”*** And the opposite direction is already **NO-GO**: *“1024→2048 | NO-GO | AC gain **non-monotone, REVERSES** across his amplitude range (0.70× @500 ct → 2.00× @6000)”*. It halves the soft relay's **small-signal gain**, which is exactly where LKAS authority at small commands is decided. ⇒ **returned to Honda's and the car's 1024.**
> ```
>   image ad6d485eefb2f6bcc195c062035d5a9dab5fb06dae7f46f68f5ca03a504c18ab
>   rwd   a6a58fa9ce11a0fa411d0b34e1539f68c514e63125692dbec20518c20a5ad0c5
>   28/28 assertions · 15 payload bytes vs the CAR, in 6 runs
>     0xC60A8/AC/B0/B4  the net-damping optimum biquad   12 B
>     0xC40DC           alpha2 8 -> 22 (HONDA's value)     1 B
>     0x55DF2           the biquad-state probe             2 B   telemetry only
> ```
>
> ✅ **That is the smallest, most defensible build of the whole arc**: one control change chosen by optimising against a measured quantity, one restoration of a Honda value the car had moved away from, an instrument on the first, and nothing else moving.
> 🛑 **I GOT THE HEADLINE WRONG AND MY OWN CHECK CAUGHT IT.** The first draft said *“the car plus exactly two things”* and omitted `0xC40DC`. Diffing the built image against the car — rather than trusting the claim — is what found it. `0xC40DC` **is** justified (22 is Honda's; the car's 8 attenuates a MEASURED DAMPER to 0.782× at 18.5 Hz, i.e. it removes damping), but the count was wrong and is corrected in the builder.
> ➕ **V234 stays as the paired arm — two bytes apart — so driving both isolates `0xC63AE` exactly, the same way V233/V234 isolates Lever B.**

> 🛑🛑⭐⭐⭐⭐⭐ **V234 BUILT — A CORRECTION TO MY OWN SHELF. EVERY BUILD V221→V233 CARRIED LEVER B 2.5× ABOVE A MEASURED OPTIMUM WHOSE UPPER FLANK IS THE WORST BUILD IN THE CORPUS.**
>
> The record states it outright: *“**THE LANE IS AN OPTIMUM AND V88 IS SITTING ON IT. BOTH FLANKS ARE NOW MEASURED:** V61 (net below V88) *‘made it WORSE… the rate lane is the mode's damper’*; V71c (net above) **worst in the corpus** … ⇒ **LEVER B IS OFF EVERY FUTURE SHORTLIST, IN BOTH DIRECTIONS**.”* V71c is *“the worst build ever recorded on all three symptoms (ratchet at the corpus record 8,521 ct p-p)”*.
>
> ```
>   READ FROM THE IMAGES        0xC6446      0xC6444
>   V88-era (V100)                 5244          512
>   car V122                       5244          512
>   V217                           5244          512
>   V221                          13107          512   <- the step
>   V228 / V231 / V232 / V233     13107          512   <- my whole shelf inherits it
> ```
>
> ```
>   image 7adbc68f2b8163c69c6b387171a2fc18938f8f1dce8127abf6cfff9907be42e6
>   rwd   a34204862389afa3cf0086c92284f8369ce35de3257de508f48d76b38e9426f4
>   29/29 assertions · TWO payload bytes · CRC 50/50 · cave BYTE-IDENTICAL · probe CARRIED
> ```
>
> ✅ **V234 = the net-damping-optimal notch (V233's 25.0/23.5/0.96) + the ONLY rate-lane dose this kit has bracketed on both sides.** The r26 arm `0xC6444` is untouched at 512 throughout, so V233 and V234 are **two bytes apart** and driving both isolates Lever B exactly.
> ⛔ **NOT CLAIMED: that 13107 is harmful.** It has never flown, and V71c's evidence concerns the NET rate-lane dose reached via the **r26 arm**, not via `0xC6446` itself. What is true is that carrying an **unflown 2.5× step**, on a lever the record puts off the shortlist **in both directions**, in the **same direction** as the flank measured catastrophic, **while recommending the build**, is not defensible. V234 removes the step; V233 stays as the paired arm.
> 🛑 **HOW IT WAS MISSED:** I read the Lever B ladder as a settled carried value and never checked it against the V88 optimum memory — the same file I had already cited three times this session for its measurement protocol. **Reading a memory for one fact does not mean its other instructions have been applied.**

> 🛑🛑⭐⭐⭐⭐⭐ **V233 BUILT AND FULLY COMPLIANT — THE BEST BUILD ON THE SHELF, AND THE FIRST DESIGNED BY OPTIMISING AGAINST A MEASUREMENT RATHER THAN A HYPOTHESIS.**
>
> ```
>   image 399424fd8b03266950ed07d5e47964705c9a87bf2f86c4370c0999179d0ae42a
>   rwd   8b418939011854b5f5eadd2d46c683ac88347bd939c9089cbbb67e1b668e0f15
>   zeros 25.0 Hz, poles 23.5 Hz, r 0.96 · 43/43 assertions · max |H| 0.999991 · probe CARRIED
>
>   net damping    6-9      9-12    12-15    22-30    30-40   damping  pumping
>   car / V231   1.000x   1.000x   1.000x   1.000x   1.000x   1.000x   1.000x
>   V228         0.861x   0.799x  -0.055x  -0.088x  -0.498x   0.535x  -0.293x
>   V232         0.985x   0.990x   0.858x   0.694x  -0.123x   0.944x  +0.285x
>   V233         1.004x   1.000x   0.891x  -0.050x  -0.888x   0.965x  -0.469x
> ```
>
> ✅ **It holds the ratchet band exactly (1.004×, 1.000×) and flips BOTH pumping bands negative.** J is **18.1 % better than Honda and 16.5 % better than V232**, and unlike the geometry that scored higher, it **never amplifies** (max |H| 0.999991).
> 🛑 **FIVE DESIGNS, FIVE GATES, NONE WEAKENED.** In order: (1) 20.0/20.5/r0.98 BOOSTED the band it was meant to cut and leaned on a ~70° phase rotation — the same class of sign assumption behind the aborted V94 drive; (2) 19.5/16.5/r0.97 rotated 10.5 Hz by **−14.4°** where the lane sits at cos −0.989; (3) a **1.5× threshold carried over from V232** was arbitrary for a different mechanism — corrected to *“> Honda”* with the reason recorded in the builder; (4) 24.0/22.0/r0.97 cleared all of those and was **deleted** for peaking at |H| 1.0020 rather than granted a third documented exception; (5) **25.0/23.5/r0.96 passes everything.**
> ✅ **The search space was 124,381 candidates: 42,920 survived no-amplification, 27,174 the passband floor, 9,089 the no-boost rule, and 7,314 the damping-region gates.** The gate set is FEASIBLE for one biquad — it just excludes every design that looked best on the objective alone.
> ➕ **Cost, unchanged and still real:** 55 Hz runs **143× louder** than Honda's cut, in a band with licensed LKAS audio excess. Every geometry that cuts 19–30 Hz with one cell pays it. **V231 remains the control arm.**

> 🛑🛑⭐⭐⭐⭐⭐ **NET DAMPING — `|H|·cos(φ)` — IS THE METRIC EVERY NOTCH COMPARISON IN THIS KIT HAS BEEN MISSING, AND IT PUTS V232 AHEAD OF V231.** A lane's damping contribution is neither its magnitude nor its phase but their product. Applying the flown lane phases (6–9 cos −0.918, 9–12 −0.989, 12–15 −0.629, 22–30 +0.936, 30–40 +0.821) to each build's filter difference:
>
> ```
>   build         6-9      9-12    12-15    22-30    30-40    damping bands  pumping bands
>   car / V231  1.000x   1.000x   1.000x   1.000x   1.000x       1.000x         1.000x
>   V228        0.861x   0.799x  -0.055x  -0.088x  -0.498x       0.535x        -0.293x
>   V232        0.985x   0.990x   0.858x   0.694x  -0.123x       0.944x         0.285x
> ```
>
> 🛑 **V228 is worse than it has ever looked.** It **destroys 46.5 % of the net damping** and **flips 12–15 Hz from damping to pumping** (net −0.055×). Its |H| tables never showed this because they omitted the phase term.
> ✅ **V232 preserves 94.4 % of the damping while cutting the pumping to 28.5 %** — a **3.5× pumping reduction for 5.6 % of the damping**, and it barely touches the ratchet band itself (0.985× at 6–9, 0.990× at 9–12). That is a far better trade than the |H|-only view suggested, and it is the reason the ordering changes.
> ⇒ **V232 BECOMES THE LEAD; V231 IS THE CONTROL ARM.** This is not vacillation on the same evidence — the net-damping product is analysis that had not been done. **Both builds carry the biquad-state probe**, so the earlier “drive V231 first to establish liveness” argument no longer separates them.
> ➕ **V232's cost is unchanged and still real:** 55 Hz runs **97× louder** than Honda, in a band with licensed LKAS audio excess. **But Honda's 9.35× cut there is on the car today and has not stopped the grinding**, while the pumping it leaves at 22–40 Hz is the mechanism the lane measurement actually identifies.
> ⛔ **AND THE BOOST IDEA IS DEAD, structurally.** Using the cell to ADD gain where the lane damps fails because **a pole pair cannot add gain at a frequency without adding phase at it**: every geometry boosting 6–9 Hz by even 5 % rotates the phase there by >15°, and the rotation costs more damping than the gain adds (rotate −45° and cos −0.918 → −0.375; rotate −90° and it PUMPS). **Not a tuning failure — a structural one. Do not re-propose it.**

> 🛑⭐⭐⭐⭐ **THE HARMONIC HYPOTHESIS IS REFUTED — AND THE CONTROL IS THE ONLY REASON I KNOW IT.** 22–40 Hz doubled is 44–80 Hz, almost exactly the audio band with licensed LKAS excess, so if that were a harmonic relationship V232 would fix both bands and the one-biquad trade would dissolve. Per engaged window, dominant mechanical frequency in 22–40 Hz against dominant audio frequency in 44–80 Hz, 7 routes, n=396:
>
> ```
>   pooled ratio median          2.038
>   SHUFFLED-pairing median      2.049      <- identical
>   P(|ratio-2.00| < 0.10) real  0.343
>   ... shuffled                 0.351      lift 0.98x
>   shuffled null 95% band  [0.268, 0.356]  <- contains the real value
> ```
>
> **The ratio clusters at 2.0 only because two bounded ranges have a quotient mechanically confined near 2.** Without the shuffled control I would have reported *“ratio 2.038, harmonic confirmed”* and promoted V232 to the lead on nothing. ⇒ **no harmonic lock; the V231-vs-V232 trade STANDS.**
> ⭐ **AND A SHARPER POINT ABOUT V232, which this made me notice: it cuts a band the operator has never named.** His symptoms are the **felt ratchet at 7.79 Hz** — where the lane *damps* — and **audible grinding**, which the audio localises to 50–72 Hz. **V232 cuts 22–40 Hz, which is neither.** Its case rests entirely on a mechanism (unanimous pumping) with no reported symptom in that band; V231's cut at 44–65 Hz overlaps a band with a licensed symptom correlate but no measured mechanism. **Each has exactly one leg.**
> ⇒ Under the kit's own rule that *the operator's lived experience overrides analyst recommendations*, **V231 keeps the lead**: its band is one he actually reports. V232 stays second — a real lever aimed at a real mechanism, awaiting evidence that the mechanism is his symptom.

> 🛑⭐⭐⭐⭐⭐ **V232 BUILT — THE FIRST NOTCH PLACEMENT EVER CHOSEN FROM WHERE THE LANE PUMPS. 16 BYTES ON V231.**
>
> ```
>   image c15fa8633352771f6f9cb5c37eac75ddebe7e648892620cdd7e7f07bc2784329
>   rwd   81127bd876289fdc444596ee3bd331278ade8cd1980547d93204767217cfca46
>   39/39 assertions · CRC 50/50 · cave BYTE-IDENTICAL · probe CARRIED
>   zeros 34.0 Hz, poles 28.0 Hz, r 0.920   (RE-CUT -- see below)
> ```
>
> ✅ **THE GAP IT FILLS.** Honda centres the notch at 55.23 Hz, **above** the measured pumping band:
> * 22–40 Hz (where the lane PUMPS, all 3 routes agree): Honda cuts only **1.51×**
> * 44–65 Hz (where Honda is centred): Honda cuts **9.35×**
>
> **Honda cuts the band it is centred on 6× harder than the band the lane actually pumps in — and that 9.35× is on the car today and has not stopped the grinding.** V232 cuts the pumping band **4.80×**, i.e. **3.2× better on the measured energy source**.
> ✅ **The DAMPING region is held, which is the constraint earlier sweeps lacked.** At 9–12 Hz the lane sits at **cos −0.989**, so any rotation there costs damping directly. V232 moves it **−3.9°** (cos −0.989 → ≈ −0.996) and holds 6–15 Hz magnitude within **4.3 %**. DC gain 1.000000, peak |H| 0.9999.
> 🛑 **COST, PLAINLY: 55 Hz goes 97× LOUDER — it gives up Honda's HF cut, the SAME price V228 pays.** The difference is that **V232 buys something measured for it and V228 does not**: V228's 20.5 Hz notch sits at the crossover and its skirt cuts the damping region.
> 🛑 **THE FIRST V232 CUT WAS DEFECTIVE AND THE GATE CAUGHT IT.** Geometry 34.0/29.5/0.900 gave a **0–5 Hz passband floor of 0.9892**, under the 0.99 gate — a ~1 % droop means the build **turns base assist down rather than notching**. Re-cut at **34.0/28.0/0.920**: floor **0.9946**, damping-region magnitude **0.990** (was 0.963), for only 1.6 % less cut (4.80× vs 4.88×). **The gate now lives inside the builder**, so a future re-cut cannot regress it.
> ⚖ **NOT a strict improvement on V231 — it is the other side of a one-biquad trade.** V231 cuts 44–65 Hz (audible; 2.1–2.2× licensed LKAS excess there); V232 cuts the pumping. **The record does not say which matters more to the operator's symptom.** ⇒ **drive V231 first, V232 second.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE NOTCH LANE DAMPS BELOW 15 Hz AND PUMPS ABOVE 22 Hz — SO HONDA'S 55 Hz PLACEMENT IS RIGHT AND EVERY BUILD SINCE V172 MOVED THE NOTCH OUT OF THE PUMPING REGION INTO THE DAMPING REGION.** This is the first mechanical explanation the arc has had.
>
> Measured on **`gp-0x6b86`, the notch's own lane**, flown on CAN 427 in ra4/ra5/ra6 (V104–V106), phase against WHEEL RATE, engaged, coherence-gated at 0.30. The sign mapping is fixed by the kit's own b26 result — *“+137/+139° vs wheel rate, |cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z)”* for a lane it calls **“a REAL 6–9 Hz DAMPER”** ⇒ **cos < 0 = damping, cos > 0 = pumping.**
>
> ```
>   band       median cos    verdict     route agreement      coherence
>   6-9          -0.918      DAMPING     all 3 agree          0.51-0.72
>   9-12         -0.989      DAMPING     all 3 agree          0.50-0.60
>   12-15        -0.629      DAMPING     all 3 agree          0.53-0.59
>   15-22        +0.551      PUMPING     DISAGREE -- crossover 0.53-0.77
>   22-30        +0.936      PUMPING     all 3 agree          0.57-0.80
>   30-40        +0.821      PUMPING     all 3 agree          0.32-0.37
>   40-50        +0.285      PUMPING     DISAGREE             0.35-0.38
> ```
>
> 🛑 **THREE INDEPENDENT REASONS V228's RELOCATION IS WRONG:**
> 1. **Honda's 55 Hz notch sits inside the unanimous PUMPING region (22–40 Hz).** It cuts an energy source. **V228 vacates that cut** — the same 100×-at-55 Hz fact recorded above, now with a mechanism.
> 2. **V228's 20.5 Hz notch sits AT the crossover**, and its skirt reaches down into **12–15 Hz where the lane unanimously DAMPS (cos −0.629)** ⇒ it cuts damping there.
> 3. **At 9–12 Hz the lane is at cos −0.989 — near-perfect damping — and V228 adds 25° of lag.** Rotating −0.989 by 25° gives ≈ −0.6 to −0.8: **a 20–40 % loss of the damping factor**, in the band the Re(Z) instrument already ranks most anti-damped.
> ✅ **⇒ V229/V231 (Honda's geometry) is CORRECT. V228's placement is wrong on three counts.** And the 56-build null history now has a mechanism: **the notch was repeatedly moved from where the lane pumps to where it damps.**
> ⚠ **LIMITS, stated:** 3 routes, all V104–V106, so era-confounded. 15–22 Hz and 40–50 Hz are NOT licensed (routes disagree). And `gp-0x6b86` is measured **downstream of Honda's biquad**, which was ARMED on those builds — so the 22–50 Hz phase is the residual after Honda's own cut, not the raw lane. The pump/damp SIGN per band is what is claimed; the magnitudes are not.

> 🛑🛑⭐⭐⭐⭐⭐ **THE Re(Z) SIGN FRAME IS RESOLVED — ANALYTICALLY, NOT EMPIRICALLY — AND IT WITHDRAWS V230 AND CLOSES α2 IN BOTH DIRECTIONS.**
>
> **The empirical anchor FAILED first, and diagnosably.** The one directional pair with caches is r95/V101 (*“GRINDING/VIBRATION AT ALL SPEEDS, ONLY WHILE LKAS COMMANDS”*) against r96/V102, the 6× revert he chose himself. Three of four bands read *“less negative = worse”* (9–12 Hz **+22.8**, 12–15 **+17.6**) — **but V101 is the 8× build, and Re(Z) = torque/rate, so higher loop gain raises rate for the same torque and mechanically makes Re(Z) less negative.** The confound moves it in exactly the observed direction; one pair cannot separate them. **Anchor abandoned.**
> ✅ **The frame resolves from the OPERATOR-CONFIRMED convention instead.** `Re(Z)` is computed from `cs_tq` (`carState.steeringTorque`) over `cs_rate` (`carState.steeringRateDeg`) — **both driver-frame quantities**, and the confirmed table puts **+driver torque and +angle both toward LEFT**. The command/torque frame mismatch that memory warns about **does not touch this pair.** So mechanical power `T·ω` is unambiguous:
> * **Re(Z) > 0** — torque in phase with rate ⇒ the driver does work on the column ⇒ **dissipative**
> * **Re(Z) < 0** — torque anti-phase ⇒ **the column does work on the driver's hands ⇒ ANTI-DAMPING**
>
> 🛑 **CONSEQUENCE 1 — V230 IS WITHDRAWN, not merely shelved.** The lane census records `gp-0x6b26` as *“the restored damper measured **+518/+565 counts of positive Re(Z)**”*. Positive ⇒ **it is a DAMPER**. V230's α2 cut removes **30 % of it at 7.79 Hz and 60 % at 18.5 Hz** ⇒ it removes damping. **That is also why V94's 6× cut of the same lane ended a drive** — the two facts now agree instead of merely coexisting. Artifacts renamed `SUPERSEDED-DO-NOT-FLASH-`.
> 🛑 **CONSEQUENCE 2 — α2 IS CLOSED IN BOTH DIRECTIONS.** Raising it is the helpful direction, and there is nothing there: the low-pass tends to the high-pass alone as `a2 → 1`, and **Honda's 22 already sits at 99.3 % of that ceiling at 7.79 Hz and 96.5 % at 18.5 Hz** — maximum available gain **1.007× and 1.037×**. ⇒ **`0xC40DC` is spent. Do not re-propose it in either direction.**
> ➕ **What this does NOT unblock:** the notch's 25° of lag at 9–12 Hz. Knowing Re(Z) < 0 says 9–12 Hz is the *most anti-damped band*; it does not say what phase lag in the notch's own lane does to Z, which needs that lane's share of the total. **V231 still stands as the build that measures it.**

> 🛑⭐⭐⭐⭐ **PROBE-SITE AUDIT — where the kit's 427 taps sat relative to the lever each build moved.** Applying the rule from the correction above (*score the motion, never the lever's own output*) to the flown probe history. **Only verified rows are asserted; the rest are marked unverified rather than guessed.**
>
> ```
>   build        lever moved                    427 tap        blind for that lever?
>   V90/91/92    0xCBE74 Y rows = b26 gain      gp-0x6B26      YES -- probe IS the lane output
>   V94          same cell, 6x cut              gp-0x6B26      YES -- but the car answered anyway
>   V101         8x gain + Lever B removed      gp-0x6B94      no -- delivered command, downstream
>   V107         b26 SPEED SCHEDULE             gp-0x6C2C      no -- taps the lane's INPUT
>   V111/112/122 (relay work)                   gp-0x6ABC      no -- 'the relay input'
>   V96 / V99    0xC63AC / 0xC40BC knee         gp-0x6B70      UNVERIFIED -- topology not checked
>   V104/105/106 b26 Y-row dose                 gp-0x6B86      UNVERIFIED -- b86's relation to the
>                                                              b26 lane is not established here
> ```
>
> ✅ **The kit already found the right pattern without naming it.** V107 moved the tap to `gp-0x6C2C`, the b26 lane's **input**, precisely when it dosed that lane — and V111 moved to `gp-0x6ABC`, described in the lineage as *“the relay input”*. **Input-side probes are exactly what the invariance rule prescribes**, because under `y = K·α` it is α that moves. Those two builds are the template.
> 🛑 **The confirmed-blind set is V90/V91/V92/V94** — probe site *is* the lane whose gain moved. Their nulls license nothing about those levers. The record already reached that verdict for the ×1.5 dose (*“do not file it FALSIFIED”*); this audit says it is a **property of the design**, not a one-off.
> ⚖ **I am NOT claiming the whole null history is explained by this.** Two rows are verified blind, three verified fine, two unverified. That is the honest extent.
>
> ➕ **ONE THING THIS CHANGES ABOUT V230, without overclaiming.** The lane census files `gp-0x6b26` as *“the restored damper measured +518/+565 counts of positive Re(Z) (V214–V217)”* — a **measurement**, not a null: the lane is characterised as PUMPING, not dead. And **V94's 6× was a broadband Y-row cut** while **V230's α2 is frequency-selective** — 0.993 at 1 Hz, 0.932 at 3 Hz, 0.746 at 7.79 Hz. So V230 removes the lane's HF content while sparing the low frequency the broadband cut also destroyed. **That is a materially different intervention from V94's**, and it raises V230 above “the direction that once went badly”.
> 🛑 **It does NOT promote V230 to the lead.** Whether cutting that lane at 6–9 Hz helps or hurts still depends on the **Re(Z) sign frame, which `rez_spectrum.py` flags as UNRESOLVED** — the same unanchored sign that has blocked two other levers this session. **V231 stays the recommendation.**

> 🛑🛑⭐⭐⭐⭐⭐ **I MISREAD THE INVARIANCE FINDING LAST TICK, AND THE CORRECTION MAKES V230 *MORE* SUSPECT, NOT LESS — PLUS THE RULE IT GENERALISES TO.**
>
> ❌ **What I said:** *“V230's α2 lever is probably inert”*, citing the ×1.5 dose that measured INERT at `gp-0x6b26`.
> ✅ **What that finding actually says** — the memory is explicit and I read past it: *“this was never a dead lever; it was an **unmeasurable** one. **Do not file it FALSIFIED.**”* `y = K·α` is invariant to K, but **α — the motion — is not.** The ×1.5 dose was measured at `y`, the one quantity guaranteed not to move. **And V94 cut the same cell 6× and the operator ABORTED the drive, which PROVES the cell reaches the car.**
> ⇒ **V230's lever DOES reach the car.** It is unmeasurable at its own output, its direction matches the 6× cut that ended a drive, and its magnitude is smaller. **The caution stands; my reason for it was wrong.** V230 is not “probably a no-op” — it is “reaches the car, in the direction that once went badly”.
>
> ⭐ **THE RULE THIS GENERALISES TO — and it may explain much of the null history.**
> **Never score a damping-like lever at its OWN OUTPUT. Score it on the MOTION it damps.** In a stable loop the lever's output is the invariant quantity by construction, so a probe there is **structurally blind** — it will read null however well the lever works.
> The kit's own record already contains both halves of the proof:
> * **The b26 ×1.5 dose** was scored at `gp-0x6b26`, the lane's own output ⇒ **null** (p50 0.988, every CI containing 1.00).
> * **V88's win** was scored as band ratios on the **delivered command** — speed-matched, episode-bootstrapped: **15–22 Hz 0.549 [0.407, 0.844], 9–12 Hz 0.604 [0.465, 0.943]**, both CIs excluding 1.00. Same class of lever (a rate-feedback gain), *measured in the right place*.
> * And the V88 note states the mechanism outright: *“r24 is rate FEEDBACK inside the loop, and `gp-0x6b98` is the loop's OUTPUT, not its input.”*
>
> ✅ **V231's PROBE SURVIVES THIS TEST — checked deliberately, because repeating the mistake here would have been easy.** V231 asks a **binary liveness** question, not a dose question: the biquad's state floats boot to exactly `0.0f`, so *“is it ever nonzero?”* is immune to loop compensation — invariance rescales magnitudes, it cannot turn a running filter's state into an exact zero. 🛑 **But the MAGNITUDE readout from V231 is NOT immune**: how hard the filter appears to work is subject to the same invariance, so V231 licenses **liveness cleanly and working-level only weakly.**

> 🛑🛑⭐⭐⭐⭐⭐ **V231 BUILT — V229 PLUS THE FIRST INSTRUMENT EVER PUT ON THE NOTCH. THREE BYTES, ALL IN THE TELEMETRY TAP; NO CONTROL BYTE MOVES.** After 56 builds that RELOCATED this filter, **none has ever measured whether it RUNS.**
>
> ```
>   image 34a4400d3d848069890a7d2be298d4ba3118e86251421d535f2f534676cace37
>   rwd   a089ba1432a5aa39d14ad281a4934f2d8fd347e5c5d2ed7e62412fd2a8449c18
>   31/31 assertions · 3 payload bytes · CRC 50/50 · cave BYTE-IDENTICAL
> ```
>
> ✅ **THE NULL IS INTERPRETABLE, which is the whole point.** The filter's state floats boot to **exactly 0.0f** (V103's GATE 1, `.data` initialiser at flash `0x89898`), so if the arming gate never fires the state stays zero forever. 427 now taps **`gp-0x3816`** — the HIGH half of the z1 float at `gp-0x3818`. ⇒ *“identically zero across N engaged frames ⇒ the filter never executed.”*
> ✅ **ENCODING VERIFIED IN THE INSTRUCTION STREAM, not assumed** — `0x55DF0` is `ld.h -0x6c18,gp,r6` (`2437e893`), so `hw2 = 65536 − offset` and the load is SIGNED; `0x55E10` is `sar 0x3,r6` (`a332`), so the shift byte is `0xA0|N`. `sar 3` is kept: any real nonzero float has |high half| ≥ 8, so it cannot alias a live state to a wire zero.
> 🛑 **I TRIED THE CORPUS FIRST AND IT COULD NOT ANSWER.** The biquad was DORMANT before V103 and ARMED after, and five routes carry audio across that boundary (r95/V101, r96/V102 vs r9e/V103, ra4/V104, r24/V122). Difference-in-differences on engaged/not audio, speed AND gear matched:
>
> ```
>   band      ARMED e/n   DORMANT e/n   armed/dorm
>   6-9          1.36x        4.21x        0.32x
>   15-22        1.15x        2.63x        0.44x   <- CONTROL, should be ~1.0
>   50-60        1.64x        1.93x        0.85x   <- the notch band
>   85-99        1.20x        1.02x        1.18x   <- CONTROL
> ```
>
> **The CONTROL bands move MORE than the test band**, and the armed arm spans 6× within itself (1.64 / 0.73 / 4.38). **That is not a null on the biquad — it is a design that cannot see it.** Cabin audio at 55 Hz is road and engine; cutting ONE assist lane 159× barely moves it. ⇒ audio is the wrong instrument for liveness, and the lane itself is the right one.
> ➕ **COST:** 427 is a shared channel, so V231 gives up V229's `gp-0x6b4e` reading. Pure instrument trade.

> 🛑🛑⭐⭐⭐⭐⭐ **V230's α2 LEVER IS PROBABLY INERT, AND ITS DIRECTION IS THE ONE THAT ONCE ENDED A DRIVE. V229 GOES BACK TO BEING THE RECOMMENDATION.** I built V230 to escape the one-biquad trade, then checked the lineage on the lane it acts on — and the lane is already characterised.
>
> ✅ **The lane has exactly ONE output and it has been dosed and flown.** `gp-0x4f50 → FUN_00041464 → gp-0x6c2c → FUN_00036c12 [the 0xCBE74 LERP] → gp-0x6b26 (±511)`, no second consumer. **A ×1.5 dose measured INERT at `gp-0x6b26` itself** — p50 **0.988**, every CI containing 1.00, against a pre-registered 1.50 (r78/V91, r79/V92). Class **T10, “the instrument is invariant to the lever”**: `y = K·α` where α is what K damps, so **in a stable closed loop the product is invariant to K.**
> 🛑 **And the large dose is not benign: V94 cut the same cell 6× and the operator ABORTED the drive** — which is also what proves the cell reaches the car. So this lane is inert at small dose and dangerous at large dose, in the CUT direction.
> ⚖ **Where V230 sits, measured against THE CAR (not against V229):** α2 8 → 3 gives **0.993 at 1 Hz, 0.746 at 7.79 Hz (−25 %), 0.506 at 18.5 Hz (−49 %)**. That magnitude is comparable to the ×1.5 that measured inert, and its **sign is the same as V94's 6× cut**. ⇒ **most likely a no-op; if not, it acts the way the aborted drive did.**
> ➕ **Worth recording separately: V228 and V229 ALSO move this lane, the other way.** Both carry α2 = 22 against the car's 8 — **+6 % at 7.79 Hz, +28 % at 18.5 Hz, +114 % at 55 Hz** in that lane. Nobody had flagged that either; by the same invariance it is probably also inert, but it is a non-stock delta the operator is entitled to know about.
> ⇒ **RECOMMENDATION REVERTS TO V229.** Its lever is the notch, which acts on `gp-0x6b82` in `FUN_000352b4` — a **different lane**, never shown invariant, and a phase-shaping device rather than a gain, so the `y = K·α` argument does not directly apply to it. **V230 stays on the shelf as a second-order option, not the lead.**
> ➕ **The measurement that prompted the check** (3 routes carrying `gp-0x6b26` on CAN 427 — r77/V90, r78/V91, r7d/V94, decoded from `0x55DF2`): the lane is **52.8 % 6–9 Hz** (coherence 0.728 with wheel rate), 17.4 % 9–12, **10.9 % 15–22** (coh 0.686). It is primarily a RATCHET-band lane, which is why perturbing it in the aborted-drive direction is not a small matter.

> 🛑🛑⭐⭐⭐⭐⭐ **V230 BUILT — ONE BYTE ON V229, AND THE FIRST BUILD TO CUT *BOTH* 15–22 Hz AND 55 Hz.** One biquad cannot notch 18 Hz and 55 Hz; V228 and V229 sit on opposite sides of that structural trade. **`0xC40DC` (alpha2) is a SECOND HF lever in a DIFFERENT lane** (the cascaded EMA bandpass feeding `gp-0x6b26`), and its low-pass has **DC gain 1 for any value**, so lowering the cal moves the corner **without touching low frequency**:
>
> ```
>   cal    1 Hz    3 Hz  |  18.5 Hz          55 Hz          corner
>    22   1.000   1.000  |  1.000           1.000           67.0 Hz   Honda / V228 / V229
>     8   0.999   0.991  |  0.782 (1.28x)   0.466 (2.14x)   21.3 Hz   the CAR
>     5   0.997   0.975  |  0.595 (1.68x)   0.296 (3.37x)   12.9 Hz
>  -> 3   0.992   0.932  |  0.396 (2.53x)   0.178 (5.62x)    7.6 Hz   V230
>     2   0.981   0.861  |  0.273 (3.66x)   0.118 (8.45x)    5.1 Hz
> ```
>
> ```
>   image bb11115a54ba97b4216f7bb2a12c1a9da2d0ba4c7495d80f008d7bc35eac3f61
>   rwd   4aac1c8a54c3c9da2df2c7d9823e83e7503b9bae30f6276bb1bfe8f1978d75e0
>   28/28 assertions · ONE payload byte · CRC 50/50 · cave BYTE-IDENTICAL
> ```
>
> ✅ **Why 3 and not 2:** the operator's standing directive forbids adding felt mass or friction to deliberate steering (~1–3 Hz). Cal 3 leaves the lane at **0.992 / 0.932**; cal 2 buys 1.4× more at 18.5 Hz for **four times** the 3 Hz cost. Cal 3 is where the curve turns.
> ✅ **GATE 1 is the cleanest in the kit** — *“exactly ONE gp/tp access image-wide, zero writers”*, one reader at `0x41626`. The cal has been 22/16/14/8/5/2 historically, so **3 is inside the built range**, and none of V124–V179 ever flew ⇒ **UNTESTED on-car, not falsified.**
> ⛔ **NOT CLAIMED:** the 2.53× is **in the `gp-0x6b26` lane**, not in delivered torque. The notch cuts `gp-0x6b82` in another function — **parallel lanes, ratios do NOT multiply.** No total is asserted. And V230 confounds two changes vs V228, so **V229 remains the clean single-variable control**.
> ➕ **RISK:** V230's 18.5 Hz cut (2.53×, one lane) is SMALLER than V228's (4.9×, another lane). If the grinding sits squarely at 15–22 Hz **in the notch's own lane**, V228 may still beat it there — while remaining 100× louder at 55 Hz.

> 🛑🛑⭐⭐⭐⭐⭐ **V229 BUILT — V228 WITH HONDA'S 55 Hz NOTCH PUT BACK. TWELVE PAYLOAD BYTES. THE FIRST BUILD SINCE V172 TO DECLINE THE RELOCATED NOTCH.**
>
> ```
>   image 078da4b1f22903a5364b54b0035790f0fac6453a4717e881290eefb15bc14a42
>   rwd   443fa080307cf221bb27f0b7dcda1c277648cab17b305f3e199e3f050a5d3c6d
>   28/28 assertions · CRC 50/50 · readback byte-identical · cave BYTE-IDENTICAL
>
>                 |H| 18.5 Hz   |H| 55 Hz    phase @10.5 Hz
>   car / Honda      0.8978      0.0063         -14.4 deg
>   V228             0.2045      0.6285         -39.3 deg   (unflown; nothing past -21.3)
>   V229             0.8978      0.0063         -14.4 deg   (back on the driven geometry)
> ```
>
> **THE ARGUMENT.** Both 15–22 Hz and 50–72 Hz carry licensed LKAS-caused noise (audio, speed AND gear matched, route-clustered). The cut depths differ by **32×**: V228 buys **4.9× at 18.5 Hz** while giving up **159× at 55 Hz**. When two bands are comparably affected, the deeper cut is worth more — and that holds whichever band is marginally worse.
> ⛔ **NOT CLAIMED: that 50–72 Hz is worse than 15–22 Hz.** Paired within-route is NOT licensed on either channel — **1.73× [0.48, 2.55]** direct, **1.23× [0.87, 1.86]** AM. The notch program is not aimed at the wrong band; it is aimed at one licensed band out of several, and pays for that aim with a far deeper cut elsewhere.
> ✅ **V229 also satisfies a standing lineage constraint V228 VIOLATES.** On `0xC40DC`: *“it must ship WITH the notch revert or not at all.”* V228 ships `0xC40DC` = 22 — which passes MORE HF (corner 21.3 → 67.0 Hz) — alongside a notch that no longer cuts 54–74 Hz. Both cells push HF the same way. **V229 is that revert.**
> ➕ **COST, PLAINLY:** V229 gives up V228's 4.9× cut at 18.5 Hz. If the grinding really is at 15–22 Hz, **V229 will be worse there.** The pair is a clean 12-byte single-variable contrast, so driving both settles a question open since V172 — and *all three* outcomes are informative, including “no difference”, which would retire the whole notch axis after 56 builds. `docs/scoring/DRIVE-CARD-V229-vs-V228.md`.

> 🛑🛑⭐⭐⭐⭐⭐ **THE LKAS-CAUSED CABIN NOISE IS BROADBAND, NOT CONFINED TO 15–22 Hz — SO V228 GIVES UP A 159× CUT IN A 2.2× PROBLEM TO BUY A 4.9× CUT IN A 1.45× PROBLEM.** Measured on the **alias-free audio** (0–100 Hz, 0.98 Hz bins), engaged vs not-engaged, **matched on BOTH speed and gear** (gear pins engine order — 60–72 Hz is 1800–2160 rpm of 4-cylinder 2nd-order, a real confound), route-level bootstrap over 6 routes:
>
> ```
>   band (Hz)    LKAS excess          95% CI        licensed
>   15-22           1.45x         [1.03, 3.70]        YES     <- where the notch program aims
>   22-30           1.68x         [1.13, 2.99]        YES
>   30-40           1.13x         [0.79, 1.27]        no
>   40-50           1.33x         [1.00, 2.91]        YES
>   50-60           2.13x         [1.13, 3.82]        YES     <- Honda's notch sits here
>   60-72           2.22x         [1.27, 5.04]        YES
>   72-85           1.86x         [1.39, 3.79]        YES
>   85-99           1.27x         [1.02, 1.75]        YES
> ```
>
> ⛔ **WHAT THIS DOES *NOT* SAY.** 50–72 Hz is **NOT** established as worse than 15–22 Hz. The paired within-route test — the right one, since the band CIs overlap heavily — gives **1.73× [0.48, 2.55], NOT licensed**, on per-route ratios 1.76 / 0.27 / 2.34 / 1.70 / 0.85 / 2.77 (4 of 6 routes). **The notch program is not aimed at the wrong band.** It is aimed at *one* licensed band out of several.
> ✅ **WHAT IT DOES SAY, and it is enough to change the build decision.** There is licensed LKAS-driven acoustic energy at **50–72 Hz (2.1–2.2×)**, and that is exactly where Honda's notch cuts **159×** (|H| 0.0063 at 55 Hz). V228 relocates that single cell to 20.5 Hz, where it cuts **4.9×** (|H| 0.2045 at 18.5 Hz) in a **1.45×** band, and leaves |H| 0.6285 at 55 Hz. ⇒ **the relocation trades a very deep cut in a real problem band for a shallow cut in a smaller one.**
> 🛑 **THE LIKELIER GRINDING CHANNEL IS UNASSESSED.** `extract_audio_grind.py`'s own docstring argues the audible signature of a rough mechanism is **broadband noise AMPLITUDE-MODULATED at the mode rate**, not a sub-100 Hz tone — *“a steering rack is a hopeless radiator”* down there. Running PASS B under the same matching leaves **1 route**: **under-powered, no verdict.** Everything above is the DIRECT-acoustic channel, which the extractor considers the less likely one. **Fixing that under-powering is worth more than any new build.**
> ➕ Unmatched, every band read 4–18× and 60–72 Hz looked like a clean winner at 17.81×. Speed matching alone cut that to 2.25× and killed 15–22 Hz entirely; adding gear brought it back. **Most of the raw engaged/not contrast is speed and RPM, exactly as `accord-averaged-spectrum-needs-matched-speed-distributions` warns.**

> 🛑🛑⭐⭐⭐⭐⭐ **HONDA'S BIQUAD *IS* A 55 Hz NOTCH, AND EVERY BUILD SINCE V172 HAS BEEN PAYING IT AWAY TO BUY THE 20 Hz CUT.** There is only ONE biquad. The kit has been **relocating** it, not adding one — and no instrument could see the cost, because CAN's Nyquist is 50.5 Hz.
>
> ```
>   car / Honda   zeros 55.23 Hz, poles 42.35 Hz (r 0.797)   deepest cut 55 Hz, |H| = 0.0063  (159x)
>   V228          zeros 20.50 Hz, poles 15.50 Hz (r 0.958)   deepest cut 21 Hz, |H| = 0.0433
>
>                 |H| 18.5 Hz   |H| 55 Hz   |H| 65 Hz
>   car / Honda      0.8978      0.0063      0.2472
>   V228             0.2045      0.6285      0.6457     <- 100x louder at 55 Hz (+40 dB)
> ```
>
> ✅ **EVIDENCE (computed from the encoded float32 in each image).** Geometric-mean ratio vs the car over **54–74.5 Hz: 4.23x (+12.5 dB)** for V228's notch lane alone. `docs/BUILD-LINEAGE.md` already carries a standing constraint on exactly this band — *“it must ship WITH the notch revert or not at all — across 54–74.5 Hz V105's coefficients leave the base-assist lane a geometric-mean 5.15x (+14.2 dB) louder than Honda's”* — and **V228 sits at 82 % of that declared-unshippable level.** The second dynamic cell, `0xC40DC` 8→22, adds **2.29x (+7.2 dB)** over the same band in its own lane.
> 🛑 **THE TRADE IS STRUCTURAL, NOT A TUNING MISS.** One 2nd-order section cannot notch 18 Hz *and* 55 Hz. Every notch build since V172 has bought the 15–22 Hz cut by vacating Honda's 55 Hz cut. **This has never been flown** — the car still carries Honda's 55 Hz notch intact — so V228 would be the FIRST build the operator drives that gives it up.
> 🛑 **MY “READY ALTERNATIVE” FROM THE PREVIOUS COMMIT IS WITHDRAWN AS AN IMPROVEMENT.** Poles at 18.00 Hz / r 0.9625 halves the 9–12 Hz phase excess (−24.8° → −12.6°) but is **WORSE on the axis that matters more**: **5.43x (+14.7 dB)** over 54–74.5 Hz — *above* the 5.15x the lineage declared unshippable — with a weaker grinding cut (0.24x vs 0.17x). I proposed it without checking the HF axis. It is a phase-for-noise trade, not a free win. **V228's geometry beats it on two of the three axes.**
> ➕ **BELIEF, and the reason this matters for the complaint:** the operator reports *grinding* — an audible phenomenon. A build that cuts 15–22 Hz while raising 54–74 Hz by 12.5 dB may well be reported as WORSE. That would not be a null; it would be the trade landing on the wrong side. **This is the single most likely explanation on the table for why sixty builds of notch work have never fixed the grinding**, and it is testable with the audio arm alone — CAN cannot see above 50.5 Hz.

> 🛑🛑⭐⭐⭐⭐⭐ **V228 MAKES *TWO* PHASE-BEARING CHANGES vs THE CAR, NOT ONE — AND THEY ARE PARALLEL LANES, SO THEIR PHASES MUST NOT BE ADDED.** A full byte diff of the car (V122) against V228 is **27 bytes in 11 runs**: 2 CRC trailers, the 2-byte 427 telemetry tap, and four levers. Two of the four are dynamic:
>
> ```
>                          7.79 Hz     10.5 Hz     18.5 Hz
>   notch 0xC60A8..B7      -14.8 deg   -24.9 deg   -75.9 deg    (more LAG)
>   EMA2  0xC40DC 8->22    +13.4 deg   +17.3 deg   +25.5 deg    (more LEAD, and +1.06/1.10/1.28x gain)
> ```
>
> 🛑 **THEY DO NOT CANCEL.** The biquad filters `gp-0x6b82` *inside* `FUN_000352b4`; the EMA2 chain feeds `gp-0x6b26` from a different function. Different signals, different functions ⇒ **parallel, not series.** Adding −24.9° to +17.3° to get “−7.6°, nearly neutral” would be wrong, and was the first thing the numbers suggested. What actually changes is the **relative** phase between two contributions to the assist sum.
> ✅ **`0xC40DC` is the EMA2 coefficient of a cascaded bandpass** — `step = a1(x−y1)` (high-pass, a1 = 37/128 at `0xC643C`) → `×32` → EMA2 low-pass (a2 = cal/64) → `>>9`. **V228 restores Honda's 22; the car carries a non-stock 8.** That moves the low-pass corner **21.3 Hz → 67.0 Hz**, so V228 passes *more* HF through this lane: **+28 % at 18.5 Hz, +61 % at 31 Hz, +125 % at 61 Hz.**
> ✅ **THE BIQUAD IS LIVE ON V228, ENGAGED-ONLY — verified, and I nearly called it inert.** The decompile shows it gated on `cal(0xC649B)==1 && cal(0xC64FA) <= gp-0x671a`, and the kit's own record says `gp-0x671a ≥ 5` was **0 of 255,292 engaged frames** ⇒ *“Honda ships this biquad DORMANT.”* But **V103 armed it** with three code patches (`0x35A06` `844fe798`→`844ffb97` repointing the arm source from `gp-0x671a` to the LKAS engagement flag `gp-0x6806`, `0x35A12` `ec49`→`e049`, `0x35A18` `e9370000`→`ea370000`) plus `0xC649B` 0→1. **All four are byte-intact on V103, V107, V122, V208, V222 and V228** — this is NOT another V42-style lost-at-rebase. The gate is now LKAS-engaged, which is why the notch is an engaged-only device.

> 🛑🛑⭐⭐⭐⭐ **THE NOTCH IS A PHASE DEVICE, AND ITS PHASE AT 9–12 Hz HAS NEVER BEEN EXAMINED — THE WHOLE ARC V172→V228 IS UNFLOWN.** `0xC60A8/AC/B0/B4` has been discussed as a notch (how deep, how wide, centred where) for 40+ builds; a 2nd-order section moves phase over a far wider span than magnitude. Read from the encoded float32 in each image:
>
> ```
>                    7.79 Hz          10.5 Hz          18.5 Hz
>   car (V122)    0.9829 / -10.6   0.9686 / -14.4   0.8978 /  -26.1
>   V105-V107     0.9863 / -14.6   0.9676 / -21.3   0.7107 /  -55.5
>   V208-V228     0.9796 / -25.4   0.9257 / -39.3   0.2045 / -102.0
> ```
>
> ✅ **EVIDENCE — grouping all 199 images by biquad and intersecting with the route→build map: EVERY cached route flew −14.4° or −21.3° at 10.5 Hz. V172→V228 — 40+ builds, every one of V202–V228 — has never produced a flown route.** So the current geometry's 9–12 Hz behaviour is unobserved, in the band the kit's own instrument calls most energetic (Re(Z) −65.4, P(most anti-damped) = 1.000).
> ✅ **The lag comes from the POLE FREQUENCY, not the width** — V208 puts poles at 15.52 Hz below its 20.50 Hz zeros. A ready alternative (poles 18.00 Hz, r 0.9625) **halves the 9–12 Hz phase excess (−24.8° → −12.6°) for 30 % of the grinding cut (4.84× → 3.37×)**, 6–9 Hz magnitude unchanged, no resonant peak. `docs/specs/design/NOTCH-PHASE-AND-THE-POLE-FREQUENCY-LEVER.md`.
> 🛑 **THE SIGN IS UNRESOLVED AND THE CORPUS CANNOT RESOLVE IT.** The natural experiment (V105–V107 vs the rest, 6.9°) gives **episode-level −8.53 [−14.62, −0.58] excluding zero** but **route-level +1.77 [−21.87, +10.53] SPANNING ZERO** — the point estimate flips sign. Episodes nest inside routes; the route is the unit. It is also confounded with build order. ⇒ needs a deliberate drive.
> ➕ **Consequence for V228's drive card:** “cannot make the ratchet worse” is a MAGNITUDE claim and is now qualified there — V228 carries 15° more ratchet-band phase lag than the car and 25° more at 10.5 Hz, beyond anything ever driven.
> ➕ **`band_contrast.py` now takes `cluster_a=`/`cluster_b=`** and resamples whole routes; its self-test shows the same data reading LICENSED [0.708, 0.925] episode-level and NOT LICENSED [0.551, 1.489] route-clustered.

> 🛑🛑⭐⭐⭐ **WITHDRAWN: "audio is 2.3–7× more efficient than CAN." On a LIKE-FOR-LIKE comparison there is NO licensed difference in either direction.** The efficiency claim drove an instrument recommendation, so it needed the CI treatment it never got. Both instruments computed the same way (ungated, 20 s episodes, same control band), efficiency = `(sd_CAN/sd_AUD)²` because minutes scale with sd²:
>
> ```
>   band     sd AUD   sd CAN    ratio          95% CI      licensed?
>   6-9       0.516    0.379    0.54x   [0.34, 1.35]   NO -- audio WORSE, spans 1.0
>   9-12      0.400    0.273    0.47x   [0.23, 1.31]   NO -- audio WORSE, spans 1.0
>   15-22     0.365    0.417    1.31x   [0.39, 5.76]   NO -- spans 1.0
> ```
>
> 🛑 **Where the 2.3–7× came from, and why it was wrong:** it compared **r24-GATED audio** against **gated CAN**, using an engaged-gating factor measured on **one route** and applied to a median drawn from **other** routes. Gated-vs-gated would be fair; gated-by-proxy-vs-gated was not. ⇒ **no efficiency advantage is established for either instrument.**
> ✅ **What still stands:** audio is **alias-free at 16 kHz**, which CAN is not — that is structural, not statistical, and is why the 40–49 Hz test is worth running at all. And the **validity** result is unaffected: CAN agreed with the operator in the one powered band, audio contradicted him in the one where it was powered. **CAN remains primary on validity; audio is now the cross-check on NEITHER efficiency NOR validity grounds — it is kept because it is a different physical observable and cheap to compute.**
> ➕ **Third withdrawal in this chain**, all the same shape: a point estimate quoted before a CI. The chain is why `rlog-tools/lib/band_contrast.py` now exists.

> ✅⭐⭐ **I AUDITED MY OWN SESSION CLAIMS AGAINST THE CI RULE. The load-bearing one HOLDS at P = 1.000.** Having withdrawn two findings for being point estimates, the rest needed the same test. Most are **deterministic** — filter responses computed from image floats, the r24 transfer, the notch band ratios — where a CI is meaningless. The **statistical** ones needed it, and the most decision-bearing is the `Re(Z)` band ordering, which I used to argue the anti-damping peaks at 9–12 Hz and to critique V222’s notch aim:
>
> ```
>   Re(Z), route-level bootstrap, n=6 routes
>     ratchet 6-9    -38.4  [-48.3, -29.9]
>     mid 9-12       -65.4  [-69.2, -61.4]   <- CI overlaps NO other band
>     gap 12-15      -46.9  [-52.4, -43.7]
>     grind 15-22    -12.2  [-14.9, -10.6]
>
>   P(9-12 Hz is the MOST anti-damped, under route resampling) = 1.000
> ```
>
> ⇒ **it survives.** ➕ The point values shift slightly from the first report (mid −67.9 → −65.4, ratchet −23.5 → −38.4) because the aggregation differs — band-mean-then-median here vs grid-interpolate-then-median before — **but the ORDERING is invariant, and the ordering is what the claim rested on.** ⇒ *"size and aim levers at 9–12 Hz"* stands.

> 🛑🛑⭐⭐⭐ **SELF-CORRECTION, AND IT WALKS BACK TWO OF MY OWN CLAIMS: I read a POINT ESTIMATE on 7 EPISODES as evidence, twice.** Both the "V222’s dose curve is contradicted" and "CAN agrees 2 of 3" readings came from medians with **no confidence interval**, on a comparison my own scorer would have **REFUSED** (`r95` has 7 episodes; `MIN_EPISODES` is 8). With episode bootstraps:
>
> ```
>   r95 (V101 8x) vs r96 (V102 6x)        CAN                        AUDIO
>   22-26 (the 8x band)   [-0.331,+0.160] NOTHING     [-0.395,-0.016] contradicts him
>   15-22 grind           [-0.371,+0.416] NOTHING     [-0.359,+0.001] NOTHING
>   6-9  ratchet          [+0.079,+0.637] AGREES      [-0.992,+0.031] NOTHING
> ```
>
> 🛑 **WITHDRAWN: "the record’s 8× dose curve is contradicted at 22–26 Hz."** That CI spans zero and licenses **nothing**. The record’s predicted +0.215 sits just outside the upper bound, which on 7 episodes is not evidence of anything. ⇒ the honest statement is **"I could not reproduce it"** — route 71, the record’s actual second arm, **has no cache** — **not "it is contradicted."**
> ⚠ **SOFTENED: "CAN agrees 2 of 3."** Only the **6–9 Hz** band is powered, and CAN agrees there. 15–22 licenses nothing either way.
> ✅ **What SURVIVES:** CAN agrees with the operator in the one band where the comparison is powered; audio contradicts him in the one band where **it** is powered. **CAN stays primary, audio stays the cross-check** — but on **1 band each way**, not 2–0.
> ➕ **The lesson is mine and it is the kit’s own standing rule:** *"window bootstraps manufacture significance; get a CI before quoting a ratio."* I built the MIN_EPISODES guard **this session** to prevent exactly this, then bypassed it by computing medians directly. **Use the scorer.**

> ❌⭐ **A HYPOTHESIS OF MINE, PROPOSED AND KILLED: 22–26 Hz is NOT demonstrably alias-contaminated.** 22–26 Hz had failed two independent checks, and the fold arithmetic is real — at **fs ≈ 101.1 Hz**, **75.1–79.1 Hz folds exactly into 22–26**, the same mechanism the record already documents for 52–71 → 30–49. Audio samples at 16 kHz and CAN sees 75–79 Hz directly, so for once the fold source was testable rather than inferable.
>
> ```
>   within-route corr, audio 75-79 Hz vs CAN 22-26 Hz:
>     r24 +0.439   r85 -0.261   r96 -0.118   r97 +0.167   r9e -0.616   ra4 +0.119
>     median +0.001 over 6 routes -- essentially random
> ```
>
> ⇒ **not supported.** ⚠ **But the test is weak and must not be cited as a clean kill:** acoustic 77 Hz is **not the same physical quantity** as steering-rate 77 Hz, so an absent correlation could mean no fold OR that the microphone does not hear what the rate signal would alias. ⇒ **the ARITHMETIC concern stands and cannot be checked from the bus** — 22–26 Hz may still be contaminated by content above Nyquist, exactly as 30–49 is, and only a 1 kHz cave counter could settle it (**Cave B — recommended against, it needs a new hook in task 1**).
> ➕ So the two failures at 22–26 remain **unexplained**, not explained-away. Recorded so the next session neither re-proposes the fold nor treats it as excluded.

> 🛑🛑⭐⭐ **V222’S JUSTIFICATION RESTS ON A MEASUREMENT I CANNOT REPRODUCE — and V228 does not need it.** V222’s case is that the notch covers the 8× cost **at 22–26 Hz** (net 0.463×). That rests on the record’s dose curve, which says **at 6× the band is 0.61× of V101** — i.e. `r95` (V101, 8×) should sit **+0.215 log10 ABOVE** `r96` (V102, 6×). Measured:
>
> ```
>   control 30-40 Hz (mine)     r95 1.914   r96 2.076   diff -0.162   CONTRADICTS
>   control 32-38 Hz (RECORD)   r95 1.946   r96 2.077   diff -0.132   CONTRADICTS
>   the record predicts        +0.215                   ~2.2x discrepancy either way
> ```
>
> 🛑 **But this is NOT a refutation, and must not be cited as one.** Two things block it: `r95` carries only **7 episodes** (below the scorer’s own MIN_EPISODES of 8), and **route 71 — the record’s actual second arm in its de-confounded 2×2 — HAS NO CACHE**, so their design cannot be run at all. What can be said is narrower and still worth saying: **the record’s key 8× measurement is not independently reproducible from the cached corpus, and the one comparison that IS available points the other way.**
> ➕ It also aligns with the separate validity check, where **CAN failed at 22–26 Hz** — the same band — while agreeing with the operator at 15–22 and 6–9. Two independent probes both stumble on 22–26.
> ⇒ **CONSEQUENCE, and it is practical: V228 does not depend on any of this.** It takes no gain step, so it needs no dose curve, no 22–26 Hz cover argument, and no 8× pricing. **V222 is the build whose case has a soft foundation; V228’s case is the notch and Lever B, both measured directly.** This is now a second, independent reason to fly V228 first.

> 🛑🛑⭐⭐⭐ **THE AUDIO-FIRST RECOMMENDATION IS WITHDRAWN. Audio is more SENSITIVE; CAN is more VALID.** Having recommended audio-first on exposure efficiency, I ran the validity check I had been careful not to run: **does either instrument agree with what the operator actually reported?** He called **V101 (`r95`) *"grinding/vibration now exists at all speeds"*** and chose **V102 (`r96`)** instead, so a valid instrument must score `r95` **worse**.
>
> ```
>   band            AUDIO                    CAN
>   22-26 (8x)   NO (says V101 better)    NO (says V101 better)
>   15-22 grind  NO (says V101 better)    YES
>   6-9 ratchet  NO (says V101 better)    YES
>                 -----------              -------
>                   0 of 3                  2 of 3
> ```
>
> ⇒ **audio contradicts his verdict in EVERY band; CAN agrees in two of three.** Sensitivity without validity is measuring the wrong thing more precisely, so **the audio-first ordering is withdrawn.** ➕ Note CAN also fails at **22–26 Hz — the band the record says the 8× effect lives in** — which is its own open question.
> ⚠ **Weak, and labelled weak:** this is **one route pair**, and `r95` carries only **7 episodes / 2.9 engaged minutes**, far under any threshold used elsewhere. The routes also differ in more than the build. It is not proof audio is invalid — it is enough to **stop recommending audio as the primary readout on sensitivity alone.**
> ✅ **What stands:** audio’s exposure advantage is real (2.3–7×) and it is alias-free. **Keep scoring both** — the scorer already does — but treat **CAN as primary and audio as the cross-check**, which is the reverse of what I said two ticks ago. ⇒ **the operator’s own verdict outranks both**, which is the standing rule and is now the only instrument with a validity record.

> ⚠⭐⭐ **CORRECTION TO THE BLOCK BELOW — I MEASURED THE QUIETEST ROUTE. The audio advantage is REAL but SMALLER: 7.0× at the median, not 10.5×.** The block below rested on `r24` alone, which is the same single-route gap that left every cross-build claim unpriced — so it was checked against the other **7 audio caches**. `r24` turns out to be the **lowest or near-lowest sd in 3 of 4 bands**, and the sd itself varies **~2× across routes** (6–9 Hz: 0.327–0.687 ungated).
>
> ```
>   minutes/arm at V88-sized effects   r24(opt)   MEDIAN   p90(pess)     CAN
>   grinding 15-22 Hz                       1.3      2.0        3.7    14.0
>   ratchet  6-9 Hz                        98.3    114.7      181.0   413.7
>   mid      9-12 Hz                        7.3      7.3       15.3    17.0
>
>   advantage at the MEDIAN route: grinding 7.0x, ratchet 3.6x, mid 2.3x
>   and on the NOISIEST route it is still 2.3x-3.8x
> ```
>
> ✅ **The recommendation is unchanged** — score audio first, keep CAN as the cross-check — because the advantage holds **across the whole route range**, not just on the best one. ➕ **Engaged-gating is worth 1.5–2.4× on its own** (measured on `r24`: 0.478→0.286 at 6–9, 0.308→0.131 at 15–22), so **gate before comparing.** ⇒ read every figure in the block below as the **optimistic end**.

> 🛑⭐⭐⭐ **AUDIO BEATS CAN IN EVERY BAND, BY 2.2× TO 10.5× — THE KIT HAS BEEN SCORING WITH THE LESS SENSITIVE INSTRUMENT.** Episode-level sd on the car, engaged 20 s episodes, log10 power, converted to the exposure each readout needs at MATCHED effect sizes:
>
> ```
>   band                effect        AUDIO min/arm   CAN min/arm   advantage
>   grinding 15-22   V88 0.549x                 1.3          14.0      10.5x
>   22-26            2.0x                       2.0          10.7       5.3x
>   ratchet 6-9      V88 0.859x                98.3         413.7       4.2x
>   mid 9-12         V88 0.604x                 7.3          17.0       2.3x
> ```
>
> ⇒ **the grinding question — the operator’s primary symptom — collapses from 14 min/arm to 1.3.** And the ratchet, the symptom that has resisted sixty builds, drops from **~7 hours to under 2**. ➕ It is also **alias-free**: audio samples at **16 kHz**, so nothing in it suffers the fold that makes CAN’s 30–49 Hz uninterpretable.
> 🛑 **Why this was invisible:** the audio corpus stopped at `ra6` (V106) and **the car had no audio cache at all** until it was extracted on 2026-08-30. Every scoring decision since has been CAN-based by default, not by comparison.
> ⚠ **THREE CAVEATS, before this is over-trusted.** ① The sd figures come from **ONE route**, so route-to-route variation in the **variance itself** is unmeasured — the same gap that made the cross-build claims unpriced. ② Audio measures a **different physical quantity** (acoustic) from CAN (steering rate); they need not respond identically to a firmware change, and audio may carry road noise CAN does not. ③ The 15–22 Hz audio sd of **0.131** is low enough to deserve a sanity check on a second route before the 10.5× is relied on.
> ⇒ **RECOMMENDATION: score audio FIRST on the next drive, and keep CAN as the cross-check** — not the reverse, which is what the kit has been doing.

