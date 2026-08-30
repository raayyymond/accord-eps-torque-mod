# STATE ARCHIVE — blocks moved out of `docs/STATE.md` on 2026-08-30

These are a RECORD of what was believed when written, not an instruction. They were moved to keep
`STATE.md` under its working target; nothing here was retracted by the move. 22 blocks, 38.2 KB.

---

> 🛑🛑⭐⭐⭐ **THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET. V222’s ratchet
outcome is a RACE, and open-loop arithmetic cannot call it.** The ★★★★★ record says `0xC6CD0` is *"the
MEASURED CAUSE of the ~23 Hz vibration"*: **V101 flew 8× and the operator reported *"grinding/vibration
now exists at all speeds"*, and V102 went back to 6× at his own choosing.** V222 returns to **8×**, so
that claim had to be checked rather than carried on its star rating.
✅ **In the band he felt, the notch covers it with room to spare.** Vibration grows as m^1.74, so
6×→8× is **1.650×** more 22–26 Hz; the notch cuts that band to **0.281×** ⇒ **net 0.463× — better than
the car** — and it stays a win across the whole exponent CI (**0.423 / 0.463 / 0.493** at m^1.43 /
1.74 / 1.96). Break-even needed 0.606×; it delivers 0.281×.
🛑 **But the notch window is only 15.5–29.8 Hz, and I nearly missed the LOWER crossing by checking
only 22–26.** Forward path (gain growth × notch), **Lever B not included**:

```
  band                 notch    net vs car
  ratchet 6-9          0.997      1.645   WORSE   <- the notch does NOTHING here
  at 7.79 Hz           0.997      1.645   WORSE
  mid 9-12             0.953      1.572   WORSE   <- and this is the Re(Z) PEAK
  gap 12-15            0.799      1.319   WORSE
  grind 15-22          0.280      0.462   better
  22-26 (the 8x band)  0.286      0.472   better
  40 Hz                  --       2.072   WORSE   (in the alias-source region)
```

⇒ **at the ratchet, V222 pairs a 1.65× forward-gain rise with a 2.50× Lever B rise.** They are the
**same order** and **Lever B is the larger**, but whether they net out is a **closed-loop** question this
arithmetic cannot answer.
⚠ **And the 1.65× is an EXTRAPOLATION**: m^1.74 was measured at **22–26 Hz** on V101 vs V100, not at
6–9 Hz. A purely linear response would give **1.33×**. So the honest range at the ratchet is
**1.33–1.65× excitation against 2.50× damping.**
⇒ **CONSEQUENCE, and it is the operator’s to weigh:** the grinding case is strong and well covered.
**The ratchet could go either way, and it could go the wrong way.** This is now a **pre-registered
possibility**, not a surprise — and it compounds with the separate finding that a ratchet **null**
licenses nothing, because `0xC63AE` is unpriced. If the ratchet is worse, the fallbacks in order are
**V221** (identical), then **V217**, then **V122** (the car).

> ✅⭐⭐ **V228 BUILT — V222 WITHOUT THE 8×, i.e. the ratchet race REMOVED.** The risk in the block above comes **entirely from the forward gain**, and that is separable. **V228 = V222 with `0xC6CD0` left at the car’s 5346 (6×) and the clamps `0xC61B2`/`B4` at 3072** — **4 bytes** from V222, **19 bytes** from the car. It keeps **both levers that have evidence behind them**: the 20.50 Hz notch (grinding, net 0.463× at 22–26 Hz) and **Lever B at 13107** (2.50× damping, the kit’s only measured on-car win), and it declines the 1.33–1.65× excitation rise that the notch cannot cover at 6–9 Hz. ⇒ **on V228 the ratchet has no plausible way to get worse** — every delta from the car is either a damper raise or a filter that is flat at the ratchet. 🛑 **COST, stated plainly: LKAS authority stays at the car’s 6×.** That is the whole trade. ⚠ **NOT V212**, which is this base with the car’s Lever B (5244); **V228 is the first build ever to pair a RAISED Lever B with 6×.** image `6cf12db9fc49aee2…`, rwd `b90a200ce53c7f37…`, **72/72** builder assertions, **100 %** orphan-byte coverage, **1138** close-out checks. Builder: `analysis-2020accord/builds/v108_plus/build_v228_tva.py`.

> 📐⭐ **THE TWO REMAINING QUESTIONS BOTH NEED A CAVE — SPECIFIED AND GATED, NOT BUILT.** ✅ **Cave A PASSES BOTH GATES on proven precedent only** (2026-08-30): GATE 2 stability **by construction** (read-only on the control path — it writes only CAN payload bits, so there is no loop to destabilise); GATE 2 timing with **huge margin** (a *filter*-sized cave is ~30–80 cycles against **~80,000/tick**, and this is four rungs); GATE 1 on **flown precedent** (`gp-0x6ada` flew at V100 as the 427 source; `0x14A` payload bits since V31p); and **no new register-liveness claim**, because all four rungs are single-operand/immediate — V96’s proven `r6`/`r7` pattern, avoiding the two-operand case. ⇒ **buildable on proven patterns, introducing no new edit class or hook.** 🛑 **NOT built — judgement, not risk:** the shelf already has two candidates and a five-build ladder, and a third artifact would compete for the **scarcest resource, engaged drive time** (~21 min/build, and a repeat route worth more than any new build). **Build it when a drive is worth spending on WHY rather than WHETHER.** The calibration search is exhausted; what is left needs an **instrument**, and instruments here mean caves, which are the kit’s **only bricking class** (V24, V27, V48B). Spec: `docs/specs/design/CAVE-SPECS-THE-TWO-REMAINING-INSTRUMENTS.md`. **They are NOT equally risky, which is the point of writing it down.**
>
> **CAVE A — the frame sign bit — LOW RISK.** Reuses the **proven** `0x55C0E` hook (the `0x14A` call site, 100 Hz, in place since V31p); both prior sign probes flew (V70’s 4-bit, V88’s `b7`). 4 bits of the 7 free: **b7** `sign(r24)` · **b6** `sign(cs_rate)` as the FIRMWARE sees it (so **b7⊕b6 is the work-factor sign directly**, with no cross-channel convention to get wrong) · **b5** `|r24| ≥ 256` (magnitude, per the design law that a bare sign bit decides nothing) · **b4** the lane’s enable (*"probe the gate, not just the output"* — the V64/V68/V92 failure). **Null sentence, pre-written:** b5 duty 0 ⇒ the lane never reached 256 counts and the drive says nothing — an **instrument** result, not a physics one. ⇒ **it would settle the frame and re-price every absolute damping/pumping claim in the record at once.**
>
> **CAVE B — the >50 Hz counter — HIGH RISK, and RECOMMENDED AGAINST.** A counter must **accumulate at 1 kHz**; `0x55C0E` runs at **100 Hz** and can only read out something else’s value, and nothing at 1 kHz maintains one. ⇒ **it needs a SECOND hook inside task 1** — **exactly the edit class that bricked V24, V27 and V48B.** It would buy one band’s interpretability (30–49 Hz, currently confounded because 52–71 Hz folds in from above Nyquist) at the highest risk available. ⇒ **if only one is ever cut, cut A.**
>
> ✅ **Neither is needed to fly V228 or V222.** The flight decision rests on the operator’s symptom verdict and the pre-registered band tests, both of which work today. These would settle **why**, not **whether**.

> ✅⭐ **"LEVER A, r26-HALF ONLY" — GENUINELY UNTRIED IN 205 IMAGES, AND CLOSED ANYWAY ON SIZE.** Lever A is **two** bytes, one per rate lane: `0x3AB76` (r24 via `gain_B`) and `0x3AC20` (r26 via `gain_A`). Only the **r24 half** is implicated in grind #2, while Lever A as a package is the kit’s **strongest measured fix (29× above the placebo floor)** — so the r26 half alone looked like a real lever hiding inside a build that was struck as a package. Scanned all **205 live images**:
>
> ```
>   (0x3AB76, 0x3AC20)   images   builds
>   (0xaa, 0xaa)            200   STOCK -- both lanes sar 2
>   (0xa9, 0xa9)              4   V62, V65, V71a, V131 -- LEVER A, BOTH halves
>   (0xab, 0xab)              1   V139
>   DIFFERING                 0   <- the halves have NEVER been separated
> ```
>
> ⇒ **confirmed untried.** But it is **inert by arithmetic**: the two lanes share one input (`gp-0x4f62`), so their outputs scale with their arms — and `0xC6444` (r26) is **512 on every build** against `0xC6446` (r24) at **13107**, i.e. **25.6× smaller**. r26 is **3.8 %** of the pair, so doubling it adds **3.8 %** where **Lever B already adds 150 %** on the dominant lane. The only way to make r26 matter is raising its arm, which **flew as V71c and is FALSIFIED**.
> ⚠ **This is a MAGNITUDE argument, not a mechanism one.** If r26 acted at a materially different PHASE from r24 it could matter more than its size implies — but the input is **shared**, and nothing in the record measures r26 separately, so there is no reason to expect it. ⇒ **do not build it; if someone wants to, measure r26’s phase first.**

> 🛑⭐⭐ **SYMPTOM PRESENCE VARIES ON IDENTICAL FIRMWARE — so ONE drive falsifies nothing, in EITHER direction.** The kit’s standing rule covers only absence (*"absence of a complaint is not a report of absence"*). **Presence varies too**, on two independent lines: **V67/V68/V85 are byte-identical** on all five grind-#2 cells, with the symptom reported on two and not the third; and the operator on V112 — ***"I no longer have an understanding of the kinds of scenarios that illicit grind #1."*** ⇒ **"no better" does not falsify a build and "better" does not confirm one.** ➕ **A distinction the record does not make explicitly, now on the drive card: ACCEPTABILITY vs EFFICACY.** *Is the car acceptable to drive?* — the operator answers it, one episode is enough, and his verdict is **final**. *Did the lever work?* — the bands answer it, and they need **many** drives (14 min/arm for grinding, ~7 h for the ratchet). **Confusing the two is how sixty builds got "falsified" by single drives.** ⇒ this is the strongest argument yet for the **repeat route**: it is the only thing separating *"this build does nothing"* from *"this symptom did not fire today."*

> ⭐⭐ **GRIND #2 IS NOT DETERMINED BY THE RATE-LANE CELLS — a natural experiment already in the record.** Chasing its open origin, the five cells ever blamed were read from the images across every build that reported it:
>
> ```
>   build   r24 arm  r26 arm  sarA  sarB  gate   grind #2?
>   V62         512      512  0xa9  0xa9  0xc5   YES
>   V65         512      512  0xa9  0xa9  0xc5   YES
>   V67        5244      512  0xaa  0xaa  0xfb   YES
>   V68        5244      512  0xaa  0xaa  0xfb   YES
>   V85        5244      512  0xaa  0xaa  0xfb   no (absence report)
>   V122       5244      512  0xaa  0xaa  0xfb   ?   <- the car
>   V222/228  13107      512  0xaa  0xaa  0xfb   ?
> ```
>
> 🛑 **V67, V68 and V85 are BYTE-IDENTICAL on all five cells**, and grind #2 was reported on two of them and not the third. ⇒ **these cells do not determine it.** Either it varies with conditions on identical firmware, or the V85 absence is a false negative — and the record already flags absence reports as **weak evidence, not a cure**. Either way the conclusion holds.
> ➕ **A hypothesis of mine died here too:** V71c’s distinguishing edit was `0xC6444` → 3072 (the r26 arm), and V62/V65’s `sar`×2 raised **both** lanes, which suggested **r26** as the common factor. **Dead** — the r26 arm is **512 on every other grind-#2 build.**
> ⇒ **Consequence for the flight candidates:** V222/V228 carry **exactly V85’s configuration** on these cells, with only Lever B higher. There is **no route from these cells to grind #2**, which is consistent with the separate finding that the 40–49 Hz notch lift is a **different mechanism** and that hearing grind #2 would not attribute to it.
> ⚠ **This does NOT explain grind #2.** Its origin stays open; what is now closed is that these five cells are not it.

> ⚠⭐ **CORRECTION: "V62’s lever CREATED grind #2" is NOT settled — I have been repeating it.** The V222 builder says the `sar` bytes are stock because V62’s ×2 *"CREATED grind #2 at 40–49 Hz"*, and I carried that forward for several ticks. The lever index says otherwise: **"grind #2 is V62’s `sar`" is REFUTED — V71c produced grind #2 carrying NEITHER `sar` byte**, so its **origin is OPEN**; only *"the r24 half caused grind #2"* survives, and only as *directionally supported*. ⇒ **Consequence for the pre-registered 40–49 Hz test:** the **band measurement** still tests the notch-relocation mechanism, but **hearing grind #2 cannot be attributed to the notch**, because it occurs without any of these levers. The two readouts are now kept apart in the pre-registration. ➕ The operator’s own description, recorded for the drive: *"a higher-speed grind #2 on lane changes/turns, only LKAS-engaged."*

> 🛑⭐⭐ **AND THE 40–49 Hz LIFT IS UNAVOIDABLE — there is no way to buy the grinding fix without it. CLOSED.** The obvious escape is to keep Honda’s 55 Hz notch and buy the 15–22 Hz cut from **Lever B** instead, which damps broadband and never touches the notch. It fails, by two independent arguments and an enormous margin.
>
> ```
>   target: the notch cuts 15-22 Hz to 0.0790 POWER
>
>   TEST 1  empirical dose law, exponent -0.258 from V88 two points:
>      Lever B 13107 -> 0.790   26214 -> 0.660   65535 (cal MAX) -> 0.522
>      to MATCH the notch needs 9.9e+07  =  1517x past the uint16 ceiling
>
>   TEST 2  the describing function:
>      V222 already sits at 0.93x the p99 knee -- past a knee, more k buys NOTHING
> ```
>
> ➕ The exponent rests on **two** dose points, which the record explicitly warns against (*"V62’s lesson: 2× was the OPTIMUM, not a point on a ramp"*). It is used here only to show the idea fails by **orders of magnitude** — a margin no exponent uncertainty can close.
> ⇒ Combined with **one biquad exists**, so 20.50 Hz and 55 Hz are **mutually exclusive**, this closes it: **the 40–49 Hz lift is the PRICE of the grinding fix, not an oversight in the build.** The alternative build (Honda’s notch kept, Lever B raised instead) would deliver **0.79× power at 15–22 Hz ≈ −1 dB — imperceptible.**
> ⇒ **So the real choice is: grinding fix WITH an audible 40–49 Hz lift, or neither.** That is the operator’s call and it is now stated plainly rather than buried in a trade nobody named.

> 🛑🛑⭐⭐⭐ **CORRECTION: "V228 CANNOT MAKE ANYTHING WORSE" IS FALSE. Both builds raise the GRIND-#2 BAND (40–49 Hz), and that band is AUDIBLE.** Chasing why V62’s lever — the kit’s most robust measured fix, 29× above the placebo floor — is absent from every build found something about the builds that ARE on the shelf. V62’s `sar×2` (`0x3AB76`/`0x3AC20`) is byte-stock `0xAA` on V88, V122, V222 and V228, removed because it **created grind #2 at 40–49 Hz, +9.7 dB(A)**. But the current builds reach the same band by a **different route**: the notch retune moves Honda’s 55 Hz notch away, which LIFTS 40–49 Hz.
>
> ```
>   40-49 Hz vs the car        power     dB
>   V228 (notch only)          3.87x   +5.9
>   V222 (notch + 8x)          6.39x   +8.1
>   grind #2 as reported               +9.7 dB(A)
> ```
>
> ⇒ **V222’s predicted lift is COMPARABLE to the grind #2 that got a lever removed.** V228’s is smaller but still positive. 🛑 **So my repeated claim that V228 "cannot make anything worse" is WRONG.** The accurate claim is narrower: **V228 cannot make the RATCHET worse** — every delta is a damper raise or flat at 6–9 Hz — **but the notch is not flat at 40–49 Hz.**
> ✅ **Unlike 30–49 Hz on the CAN logs, this band is AUDIO-measurable (44.1 kHz), so the alias caveat does NOT apply.** It is a real, checkable, audible prediction, and the kit already has audio extractors to score it. ➕ Units, because the kit errs here: the notch `|H|` is an AMPLITUDE transfer (1.968 → power 3.875) while m^1.74 was measured in band-POWER units (1.650); an intermediate line of mine said +10.1 dB by mixing the two, and **+8.1 dB is correct.**

> 🛑⭐⭐ **CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR. The kit HAD a route-variance measurement; I missed it.** The ★★★★★ 8× memory records a **MEASURED placebo floor of 1.45× (`r75` vs `r76`, byte-identical V89)** — that is a **third within-build pair**, and it means the dose law was **already** priced the way I claimed was missing. With three pairs `sigma_route` is **0.0985 point / 0.2876 upper** (tighter than the 0.396 below). Re-priced against the kit’s own floor:
>
> ```
>   claim                    vs the 1.45x placebo floor
>   V62 grinding, high end        28.97x   robust
>   8x dose law G             1.86-2.69x   CLEARS -- the law STANDS
>   V88 grinding 0.549x            1.26x   clears, but MARGINALLY
>   V88 ratchet 0.859x             0.80x   INSIDE the floor -- not evidence of anything
> ```
>
> ✅ **The 8× dose law stands and my single-route framing of it was unfair** — the kit priced it against a measured floor and it clears by 1.9–2.7×.
> 🛑 **But this corrects MY OWN reasoning too.** The r24 work anchored on *"V88 raised r24 and cut 6–9 Hz to 0.859×, so r24’s side is beneficial"*. **That 6–9 Hz value is INSIDE the placebo floor.** The anchor survives on the **grinding** band (0.549×, clears by 1.26×) and **not** on the ratchet band — where **V88 never had a result distinguishable from route noise.** ⇒ every conclusion I drew that used V88’s *ratchet* number is weaker than stated; those using its *grinding* number stand, marginally.
> ➕ **This does not change either flight candidate** — Lever B’s case was always the grinding band — but it does mean **nobody has ever shown Lever B helps the ratchet**, which is worth knowing before reading a ratchet result from the next drive.

> 🛑🛑⭐⭐⭐ **THE KIT’S CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION — and a repeat route is now the highest-value data available.** Every cross-build result in this record is **one route vs one route**, so its error bar is `sigma_route * sqrt(2)`. That quantity has never been estimated. From the only two within-build pairs (`r7e`/`r7f` = V96, `r22`/`r23` = V112): point estimate **0.0897**, χ² 95 % upper bound **0.3960** (2 df is very wide).
>
> ```
>   claim                    ratio   z @point   z @upper   survives the conservative bound?
>   V88 grinding 15-22       0.549      2.1       0.47     NO   <- the kit ONLY measured win
>   V88 mid 9-12             0.604      1.7       0.39     NO
>   V88 ratchet 6-9          0.859      0.5       0.12     NO
>   V62 grinding, low end    0.125      7.1       1.61     marginal
>   V62 grinding, high end   0.024     12.8       2.90     YES  <- the ONLY survivor
>   8x dose law G          2.7-3.9  3.4-4.7  0.77-1.06     NO
>   V222 predicted 6x->8x    1.650      1.7       0.39     NO
> ```
>
> At the point estimate most of the record survives; at the conservative bound **only V62’s largest effect does.** ⚠ **This is NOT "the record is wrong."** The 95 % upper bound is a worst case — a 4.4× inflation of σ from 2 df — and the truth lies between. What it does say is that the evidence base carries an **unpriced** uncertainty wide enough to matter, including under **V88’s 0.549×, which is the sole basis for Lever B and therefore for BOTH flight candidates.**
>
> ⇒ **THE RECOMMENDATION THIS PRODUCES IS UNUSUAL AND WORTH ACTING ON: a REPEAT ROUTE on one build is worth more than another new build.** Two more within-build pairs take `sigma_route` from 2 df to 6+, and that **retroactively re-prices every cross-build claim in the kit at once** — V62, V88, the dose law and the pre-registered 8× test together. No new firmware can do that. ➕ It is also nearly free: it needs driving, not building, and the V228 drive already wants ~21 engaged minutes, which naturally spans more than one session.

> ⚠⭐ **OPEN OBSERVATION, NOT A FINDING: an 11.4× residual 6–9 Hz gap between V106 and V107 that CANNOT be attributed.** A scorer dry-run threw this off unasked. Raw, route `r1e` (V107) carries **22.6×** the 6–9 Hz band ratio of `ra6` (V106) — two builds separated by one `gp-0x6b26` damper reshape, in the lineage leading to the car. Across **17 routes**, 6–9 Hz regresses on log median |rate| at **slope +0.452/decade, r = +0.599, p = 0.011**, and correcting for it drops the gap to **11.4×** — so **rate explains about half, not all**, and the two routes remain the corpus extremes at **+2.63** and **−1.92 sd**. 🛑 **It still cannot be attributed, for a structural reason: every build has exactly ONE route, so build and route are perfectly confounded.** The lone exception is V112 (`r22`/`r23`), which shows **1.6× spread within a single build** — 11.4× is well beyond that, but that is one comparison against one estimate. ➕ **I was wrong in both directions inside one tick** — first flagging it as a build effect, then calling it a rate confound; the test says neither. Recorded so the next session neither chases it nor dismisses it. ⇒ **RESOLVED INTO A CLEAN "UNRESOLVED", 2026-08-30.** There are **two** within-build pairs, not one — `r7e`/`r7f` are both **V96**, alongside V112’s `r22`/`r23`. Rate-corrected, their spreads are **1.05×** and **1.51×**, giving `sigma_route` = **0.0897** log10. Against that point estimate the 11.4× gap is **8.3 sigma** — overwhelming. But a variance from **2 pairs has 2 df**, and the χ² 95 % upper bound is `sigma_route` = **0.3960**, at which the same gap is **1.9 sigma — not significant.** The same data supports both. ➕ And the adjacency is unremarkable: **P(the max and min residual land on adjacent builds by chance) = 0.125** over 20,000 permutations. ⇒ **UNRESOLVED, and it needs a repeat route rather than more analysis.** ➕ That is my **third** framing of this one observation — build effect, then rate confound, then "more likely real"; only this one is what the arithmetic licenses. Recorded that way so the next session inherits the uncertainty rather than any of the three claims.

> 🚩 **FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD: V228 or V222.** They are **four bytes apart** and ask for different things. **V228** keeps the notch and Lever B and leaves the forward gain at the car’s 6× → grinding fix with **the ratchet protected**, authority unchanged. **V222** adds the 8× → **more LKAS authority, ratchet could go either way.** ⚠ **If undecided, V228 is the one that cannot make anything worse**, and flying it first makes V222 interpretable afterwards (they differ in exactly one lever — the cleanest 8× experiment this kit could run). Cards: `docs/scoring/DRIVE-CARD-V228.md` · `docs/scoring/DRIVE-CARD-V222.md`. ➕ **PRE-REGISTERED, before either flies:** `docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md` — the pair is the **first clean 8× experiment** this kit has had, because the only prior 8× route (V101) **removed Lever B in the same build**. V228/V222 differ in the gain and **nothing else**, so the notch and the damper cancel. ✅ **~21 engaged min/build settles the m^1.74 dose law at 22–26 Hz.** 🛑 **It CANNOT settle the ratchet (38–116 min/arm) and cannot distinguish a linear law from no effect (61 min/arm).**

> 🚩 **V222 (the higher-authority option).** = **V221 with four bytes REMOVED from the delta.** Delta from the CAR (**V122**) is **23 payload bytes** — notch 20.50 Hz (grinding) · `0xC63AE` 512 (ratchet) · `0xC6CD0` 6×→8× + clamps (authority) · `0xC6446` 5244→13107 (Lever B) · the 427 probe. Every deliberate lever is byte-identical to V221; what changed is that the friction lane now matches the car at EVERY rate rather than only below its knee. Drive card: `docs/scoring/DRIVE-CARD-V222.md`. **V221 is the fallback** (`DRIVE-CARD-V221.md`), V217 behind it. Shelf: `docs/scoring/SHELF.md`. Pre-registered scoring: `docs/scoring/SCORING-V217-preregistered.md` (applies to all three).

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


## 📁 **EARLIER BLOCKS (18) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` and
`docs/archive/STATE-ARCHIVE-2026-08-30b-handoff-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

