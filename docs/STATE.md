# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Below it are **83 blockquote blocks in reverse-chronological
> order** — findings, corrections and closures. That is a record, not a briefing. Everything you need
> to make a decision is in this box and the index under it.

## ✈ THE DECISION, IN ONE PLACE

**Two flight candidates, four bytes apart. Both are built, byte-verified and audited.**

| | **V228** | **V222** |
|---|---|---|
| grinding | notch cuts 15–22 Hz **3.6×** | **identical** |
| **ratchet** | **protected** — every delta is a damper raise or flat at 6–9 Hz | **could go either way** |
| **LKAS authority** | 6×, unchanged from the car | **8×** |
| 40–49 Hz (audible) | **+5.9 dB** | **+8.1 dB** |
| delta from the car | 19 bytes | 23 bytes |

- **Cards:** `docs/scoring/DRIVE-CARD-V228.md` · `docs/scoring/DRIVE-CARD-V222.md`
- **Pre-registered:** `docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md` (scorer written and validated
  **before** any data: `rlog-tools/score/score_8x_experiment.py --selftest`)
- **If only one thing gets done: drive V228 TWICE**, on separate outings. A repeat route re-prices
  **every** cross-build claim in the kit at once; no new firmware can do that.
- 🛑 **The flash decision is the operator’s.** He names the file and the bus; repeat both back.

### The three things that are NOT optional to know

1. **One drive falsifies nothing, in either direction.** V67/V68/V85 are byte-identical and grind #2
   appeared on two of them. Keep **acceptability** (his verdict, 1 episode, final) apart from
   **efficacy** (the bands, many drives). See RULE 5b in `BUILD-LINEAGE.md`.
2. **Do not score 30–49 Hz** across the V222/V122 boundary — 52–71 Hz folds into it from above Nyquist.
3. **The grinding fix costs an audible 40–49 Hz lift.** It is unavoidable: only one biquad exists, and
   Lever B cannot substitute (short by 1517×).

> ❌⭐ **A GATE I BUILT AND THEN DELETED — "documented cell values vs the images" DOES NOT WORK.** The withdrawn-claims registry found 7 defects by pattern-matching, so the obvious next axis was checking every `0xADDR = N` claim in the docs against ground truth: a value **no image has ever held** is wrong regardless of which build was meant. It ran over **1028 claims / 206 images** and produced **only false positives**, because that pattern is ambiguous in this record’s prose:
>
> ```
>   0x55DF2 = 9094           the doc means HEX 0x9094; read as decimal
>   0xD782C -> 60/400/140    a LIST of values for three addresses
>   0xC40D2 = 1 reader       a COUNT ("1 reader / 0 writers"), not a value
>   0xC6564 = 40 zero bytes  a SIZE, not a value
>   0xC61BE -> 16384         built and then PULLED, so correctly absent from images
> ```
>
> ⇒ **deleted rather than tuned.** Every filter that removes one class removes real hits with it, and a gate that cries wolf gets ignored — which is worse than no gate. **Recorded so nobody rebuilds it.** ➕ The lesson generalises: **the withdrawn-claims registry works because it matches DISTINCTIVE PHRASES; a value-checker fails because `0xADDR = N` is not distinctive.** Pattern gates need a pattern only the defect produces.

> ✅⭐⭐ **THE 40–49 Hz AUDIO TEST IS THE MOST SENSITIVE READOUT THIS KIT HAS — ~2 min/arm.** Its power was checked before the drive, on the `r24` baseline created this session. Engaged 20 s episodes give **sd = 0.3415 log10 = 3.4 dB** (gating to engaged cut it from 6.7 — **do the gating**), so V228’s +5.9 dB needs **6 episodes = 2.0 min/arm** and V222’s +8.1 dB needs **3 = 1.0 min**. ⇒ **compare the CAN bands: grinding 14 min/arm, 9–12 Hz 17, the ratchet 414.** The audio readout is **~7× more sensitive than the CAN grinding test** and is the **only registered test falsifiable inside one short drive.** 🛑 **A units error nearly killed it:** the ratio is log10 of a POWER ratio, so **dB = 10×log10 and +5.9 dB IS 0.59 log10, not 0.059**. My first pass divided an already-log10 figure by ten and reported **671 / 356 min/arm** — the test looked dead when it is the strongest available. ➕ **And the instrument did not exist before today**: the audio corpus stopped at `ra6` (V106) and the car had **no audio cache at all**. ⇒ **audio is under-used by this kit** — it is sampled at 16 kHz so nothing in it is alias-confounded, unlike the ~101 Hz CAN logs.

> 🛑🛑⭐⭐⭐⭐⭐ **THE 55 Hz COST IS MECHANICALLY NEGLIGIBLE — V235's LAST OPEN QUESTION CLOSES FAVOURABLY.** The content at 55 Hz cannot be recovered from any route running Honda's notch (|H| = 0.0063 there, so de-embedding means ×25,000 — the numerically invalid operation caught earlier). But **ra4 and ra5 share the same b26 dose (1.5×) and differ in the notch**, and CAN's ~101 Hz sampling folds **52–71 Hz into 30–49 Hz**:
>
> ```
>   true Hz   aliases to    Honda      V105      V235
>   52           49.0      0.0930    0.7514    0.8927
>   55           46.0      0.0063    0.7640    0.9010   <- Honda cuts 121x, V105/V235 pass
>   65           36.0      0.2472    0.7915    0.9186
>
>   lane power, normalised to 4-15 Hz (which BOTH notches leave alone):
>     ra4 (Honda notch)   4-15 1.000   15-30 0.409   30-40 0.00856   40-49 0.01042
>     ra5 (V105 notch)    4-15 1.000   15-30 0.423   30-40 0.00975   40-49 0.00858
>
>   excess in the folded band, ra5 - ra4 = -0.05 % of total power
> ```
>
> ✅ **ra5 passes 52–71 Hz where ra4 notches it out, so real energy there would show as an excess. There is none: −0.05 %, indistinguishable from zero.** ⇒ **Honda's 55 Hz notch removes essentially nothing from this lane, and V235's 143× increase at 55 Hz applies to a band with no energy in it.**
> ✅ **COROLLARY, and it matters for the drive:** the licensed **50–60 Hz (2.13×) and 60–72 Hz (2.22×) LKAS audio excess does NOT originate in the lane V235 modifies.** Releasing the notch there cannot amplify it. The audible excess comes from somewhere else — motor, mechanical, or another path — and this build does not touch it.
> ⚖ **Limits:** two routes, and the two folded sub-bands move in opposite directions (30–40 up 1.138×, 40–49 down 0.823×), which is scatter. The **total** is −0.05 %, far inside any plausible noise, which is what licenses the conclusion — not either sub-band alone.

> 🛑🛑⭐⭐⭐⭐⭐ **THE AGGREGATE PUMPS WHERE THE LANE PUMPS — V235's PREMISE CONFIRMED FROM A SECOND ROUTE AND A SECOND OBSERVABLE.**
>
> `gp-0x6b86` is only ONE of about six lanes summed into the aggregator (model add order at `0x3acc8-0x3ace6`: `r26+r24 → +6b86 → +6bd0 → +6bbe → +6b26 → +[6b62/6ade]`). So the lane pumping is **necessary but not sufficient** — if the other lanes cancelled it at the sum, notching the lane would buy nothing that reaches the motor. **r95 (V101) carries Honda's biquad byte-for-byte and taps `gp-0x6b94`, the aggregator**, so it answers this directly.
>
> ```
>   band     | r95  gp-0x6b94  THE SUM   | ra4  gp-0x6b86  THE LANE
>            |    cos   pow%   coh       |    cos   pow%   coh
>   6-9      | -0.918  78.2%  0.80       | -0.879  51.3%  0.72
>   9-12     | -0.820   6.5%  0.61       | -0.964  12.1%  0.50
>   12-15    | +0.121   1.4%  0.69       | -0.629   6.0%  0.53   <- the one disagreement
>   19-22    | +0.609   2.3%  0.93       | +0.625  10.0%  0.88
>   22-26    | +0.791   9.5%  0.97       | +0.826  16.5%  0.89
>   26-32    | +0.964   0.5%  0.73       | +0.994   1.3%  0.66
>
>   sign agreement 7 of 8 bands · aggregate 19-32 Hz mean cos = +0.788
> ```
>
> ✅ **The other lanes do NOT cancel it: the SUM pumps at 19–32 Hz with coherence 0.93–0.97.** Cutting the lane there reaches the motor. That was the open question V235's whole case rested on, and it is now answered on a route the design was never fitted to, through a different signal.
> ✅ **And the ratchet band is dominated by damping at the aggregate: 6–9 Hz carries 78.2 % of the sum's power at cos −0.918.** V235 leaves it at **1.004×**.
> ➕ **The single disagreement is at 12–15 Hz** — the lane damps (−0.629) while the sum is barely pumping (+0.121, 1.4 % of power). If the SUM is what matters, V235's small net loss there (0.891×) is **not a cost at all.** Noted rather than claimed: 1.4 % of power and one route.

> 🛑🛑⭐⭐⭐⭐⭐ **THE LANE MEASUREMENT WAS CONTAMINATED — AND FIXING IT INDEPENDENTLY RE-SELECTS V235'S EXACT GEOMETRY. ra6's DISSENT IS EXPLAINED.**
>
> **The contamination.** `gp-0x6b86` is measured DOWNSTREAM of the biquad, and I pooled ra4/ra5/ra6 then corrected as if HONDA's filter had been in force on all three. It was not:
>
> ```
>   ra4  V104  b26 dose 1.500x  biquad f8c2c4bf 7576223f 0ebef0bf fc89c13f  (HONDA angles, b4 differs)
>   ra5  V105  b26 dose 1.500x  biquad 56e1f0bf 3d0a673f 9eb8fcbf b51a4e3f  (V105's ~25.5 Hz notch)
>   ra6  V106  b26 dose 3.000x  biquad 56e1f0bf 3d0a673f 9eb8fcbf b51a4e3f  (same)
> ```
>
> 🛑 **MY FIRST FIX WAS NUMERICALLY INVALID AND ITS OWN OUTPUT SHOWED IT.** De-embedding by dividing power by `|H|²` put **99.5 % of the de-embedded power in one band** — division by near-zero at ra5/ra6's own notch. **You cannot recover a lane's response where the in-force filter removed the signal; the information is not there.** Caught by looking at the power distribution, not by the optimiser, which happily returned a different "optimum" from the artifact.
> ✅ **THE CLEAN ROUTE IS ra4**, whose biquad has **Honda's angles** — only `b4`, a flat gain, differs — so it needs **no phase de-embedding at all**, and **100 % of 4–45 Hz is usable** (|H| min 0.5653). ra5/ra6 are only **84.1 %** usable (|H| min 0.0030 / 0.0018).
> ```
>   ra4 INTRINSIC lane      cos(phi)   power %   contribution
>     7-10                    -0.793     44.6%     -0.3535   damps   <- the dominant term
>     19-22                   +0.160      9.7%     +0.0155   PUMPS
>     22-26                   +0.351     16.4%     +0.0575   PUMPS   <- V235's notch sits here
>     26-32                   +0.818      4.6%     +0.0380   PUMPS
>
>   RE-OPTIMISED ON ra4 ALONE, usable bins only:
>     J(Honda) -0.28054   J(V232) -0.29860   J(V235) -0.38119
>     OPTIMUM  zeros 25.0, poles 23.5, r 0.96   bytes fa15f3bf...  == V235 EXACTLY
> ```
>
> ✅ **The one clean route independently re-selects V235's geometry, byte for byte, and V235 beats Honda by 36 % on it.** The contaminated pooling happened to land on the right answer.
> ✅ **AND ra6's LEAVE-ONE-OUT FAILURE IS EXPLAINED: ra6's own notch erases 22–26 Hz**, which is precisely the band the optimisation is about. It was being asked to judge an effect it cannot see. **That is not a generalisation failure of V235; it is a blind spot of the held-out route.**

> 🛑⭐⭐⭐⭐ **V235 CROSS-VALIDATED: THE GEOMETRY IS NOT FITTED, BUT ITS ADVANTAGE IS NOT UNIFORM EITHER.** Leave-one-route-out over the three routes the design was optimised against:
>
> ```
>   1) FIT STABILITY -- re-optimise on each PAIR
>      ra5+ra6   -> 25.0 / 23.5 / 0.96      (held out ra4)
>      ra4+ra6   -> 25.0 / 23.5 / 0.96      (held out ra5)
>      ra4+ra5   -> 25.0 / 23.5 / 0.96      (held out ra6)
>      all three -> 25.0 / 23.5 / 0.96      <- V235
>
>   2) HELD-OUT SCORE       J Honda      J V232      J V235    margin vs Honda
>      ra4                 -0.36667    -0.37874    -0.46391      +0.097  V235
>      ra5                 -0.38603    -0.39354    -0.46089      +0.075  V235
>      ra6                 -0.44792    -0.41635    -0.43770      -0.010  HONDA
> ```
>
> ✅ **The filter choice is not fitted at all** — every fold selects the identical geometry, so dropping any route changes nothing. And because the geometry chosen *without* ra6 is that same geometry, scoring it on ra6 is a genuine held-out test.
> 🛑 **It loses that test on ra6.** V235 wins on 2 of 3 routes by roughly **10× the margin it loses by** on the third, so the average strongly favours it — but **one route prefers Honda, and n=3 is far too few for a confidence interval.** ⇒ **a qualification on the card, not a disqualification, and not a clean win either.**
> ➕ **My own script's verdict line said *“the advantage is fitted to the sample”*, which the numbers do not support** — the geometry is provably not fitted, and 2-of-3 with a 10× margin asymmetry is not the same as a fitted advantage. Corrected where it lives, in `rlog-tools/score/notch_leave_one_route_out.py`, so the next reader gets the accurate reading.

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

## 🗂 INDEX TO THE BLOCKS BELOW

| what you want | look for the block titled |
|---|---|
| the flight order | *FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD* |
| why V222’s ratchet is a risk | *THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET* |
| what V228 is | *V228 BUILT — V222 WITHOUT THE 8×* |
| the audible side effect | *"V228 CANNOT MAKE ANYTHING WORSE" IS FALSE* · *THE 40–49 Hz LIFT IS UNAVOIDABLE* |
| **my own withdrawn claims** | *SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED* · *CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR* · *CORRECTION: "V62’s lever CREATED grind #2" is NOT settled* |
| what measurement can and cannot do | *THE RATCHET BAND CANNOT BE SCORED BY BAND POWER* · *RING-DOWN COMPUTED* · *CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION* |
| what is closed and will not be re-proposed | *THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION* · *THE NOTCH IS NOW CLOSED* · *EXACTLY ONE BIQUAD* · *FOC CURRENT LOOP IS TRANSPARENT* · *LEVER A r26-HALF ONLY* · *r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING* |
| what is still open | *THE TWO REMAINING QUESTIONS BOTH NEED A CAVE* · *OPEN OBSERVATION — an 11.4× residual* · *THE FRAME TEST IS INCONCLUSIVE* |
| the session narrative | *SESSION HANDOFF* (last block) |

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

> ⭐ **RING-DOWN COMPUTED: it is the better ratchet instrument, but only for LARGE effects — and a
quality filter BIASES AGAINST the mode of interest.** 304 ring-down events extracted over **75.1
engaged minutes** across 6 routes (**4.05 events/min**), from command drops ≥35 % within 100 ms.

```
  min R2   kept  ev/min  p50 zeta  sd(log10)  min/arm to see a 2x change
     0.0    304    4.05    0.0400     0.474            9.6
     0.3    171    2.28    0.0709     0.294            6.6   <- best exposure
     0.8     52    0.69    0.1384     0.272           18.8
     0.9     29    0.39    0.1427     0.209           20.7
```

✅ **For a 2× change in ζ, ring-down needs ~7–10 engaged min/arm against band power’s ~104.** That is a
**10–15×** improvement and makes a large ratchet effect **measurable on a drive somebody would
actually do.**
🛑 **But it does NOT rescue a V88-sized effect**: 1.16× still needs **209–404 min/arm**. ⇒ **neither
instrument can resolve a small ratchet change at any realistic exposure** — and that conclusion is
robust across every filter setting, so it does not depend on implementation details.
🛑🛑 **THE TRAP, and it is the interesting part: filtering on fit quality selects AGAINST the
ratchet.** As R² rises the median ζ climbs **0.040 → 0.143** — but the record’s ratchet is
**ζ = 0.017–0.036 (Q 14–29)**, and ζ = 0.14 is **Q ≈ 3.6**, heavily damped. A **lightly** damped mode
barely decays across a 0.5 s window, so its fit is POOR by construction; a clean exponential over that
span is something **faster-decaying and probably not the ratchet at all.** ⇒ **do not filter ring-downs
on R²** without checking what it selects.
⚠ **Scope:** this is a quick re-implementation, not the kit’s validated scorer, and it does **not**
reproduce the record’s ζ (0.040 unfiltered vs 0.017–0.036). The **exposure ratios** are indicative; the
absolute ζ values are **not** trustworthy here. ⇒ **OPEN: re-run this variance estimate through
`rlog-tools/score/ratchet_ringdown.py` with its own controls** (time-reversal, random-frame) before any
build is sized against it.

> 🛑⭐⭐ **AND THE RATCHET ARM OF V222/V224 IS UNPRICED AGAINST THAT FLOOR — its lane’s SHARE and its
SIGN have both never been measured.** `0xC63AE` is **1024 in stock and on the car**, **512 on
V217–V223**, **256 on V224**. The record annotates it only as a *"Stage-2 input"* scale on the second
aggregator chain. A weight cut moves ζ only as much as that lane weighs in the net:

```
  D_net(w) = D_other + w*D_lane ;  f = |D_lane| / D_car
     lane ANTI-damps:  zeta_new/zeta_old = 1 + f*(1-k)      cutting it HELPS
     lane      damps:  zeta_new/zeta_old = 1 - f*(1-k)      cutting it HURTS

     lane f    V222 k=.5 anti   V224 k=.25 anti   V222 damp   V224 damp
       0.20         1.100            1.150          0.900       0.850
       0.50         1.250            1.375          0.750       0.625
       1.00         1.500            1.750          0.500       0.250
       2.00         2.000            2.500          0.000       0.000
```

⇒ to clear the **2.00×** ring-down floor, **V222 needs f = 2.00** and **V224 needs f = 1.33** — i.e. this
ONE Stage-2 input would have to supply anti-damping worth **1.3–2× the entire net damping.** (f *can*
exceed 1, since `D_other > D_car` when the lane is anti-damping, but that is a lane dominating the whole
balance.) **⇒ if the lane is anything less than dominant, the ratchet arm is BELOW the measurement
floor — unmeasurable by design, which is the kit’s own definition of a build failure rather than a lever
failure.**
🛑 **And the SIGN is the load-bearing unknown.** If the lane **damps**, cutting it makes ζ **worse**:
at a modest f = 0.5, **V224 would cut ζ to 0.62× the car.** Nobody has measured which way it goes.
✅ **Scope — this does NOT argue against flying V222.** `0xC63AE` = 512 is the V217 baseline, not a new
V222 edit, and the build’s audited levers are Lever B and the notch. What it says is narrower and
worth saying before the drive rather than after a null: **the ratchet arm specifically is unpriced, so
a ratchet null on this drive licenses NOTHING about `0xC63AE`.** The grinding and authority arms are
priced and audited; this one is not.
➕ Corrected mid-derivation: my first pass had a sign error that made a **bigger** cut need a **larger**
lane share, which is backwards. The table above is the corrected algebra and passes that sanity check.

> 🛑 **AND THE SIGN CANNOT BE RECOVERED FROM CACHE — every 427-derived channel is RECTIFIED, verified.**
The obvious move was the r24 method: reconstruct the lane and measure its phase against rate. It does
not work here, and the reason is worth recording. Checked across **r7e / r80 / r81 / r82** (V96–V99, the
builds that put `gp-0x6b70` on CAN 427 at `sar 6`):

```
  ab_mt              0..251, 250 distinct, ZERO negatives   <- the 427 torque byte, RECTIFIED
  probe / field / raw14_b4   only 4-8 distinct values       <- cave threshold rungs, not waveforms
  slow3 / g6ac2      constant                               <- carry nothing on these routes
```

⇒ **rectification destroys the sign by construction**, and the cave channels are **comparator duties**,
not sampled waveforms — neither can yield a phase. The record’s *"CAN 427 is RECTIFIED"* is confirmed
empirically here rather than quoted.
➕ **Why r24 worked and this does not:** r24’s **input** (column torque) is on the wire **unrectified**,
so its lane could be reconstructed from a known transfer applied to a known signal. `gp-0x6b70` has no
equivalent unrectified input available — the chain `FUN_00038148 → gp-0x6b70` sums several weighted
lanes, and reconstructing it would require every one of them.
⇒ **The sign needs ONE CAVE SIGN BIT.** ✅ That is a **proven, low-risk pattern in this kit**, not a new
cave class: **V70 flew a 4-bit sign probe** and **V88’s `b7` carried a sign at 100 Hz**. It is the
cheapest instrument that would settle whether cutting `0xC63AE` helps or hurts.
⚠ But it is still a **cave**, and caves are this kit’s **only bricking class** (V24, V27, V48B) — so it
is a proposal for after V222 flies, not a reason to delay the drive.

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


## 📁 **EARLIER BLOCKS (20) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

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
