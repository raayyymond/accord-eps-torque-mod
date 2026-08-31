# STATE ARCHIVE — blocks moved out of `docs/STATE.md` on 2026-08-30

These are a RECORD of what was believed when written, not an instruction. They were moved to keep
`STATE.md` under its working target; nothing here was retracted by the move. 24 blocks, 57.0 KB.

---

> 🛑🛑⭐⭐⭐⭐⭐ **THREE AVENUES CLOSED IN ONE TICK, AND NO FIX. THE LOOP-DELAY HYPOTHESIS IS REFUTED BY ITS OWN CONTROL.**
>
> With calibration exhausted, the question was what **creates** the 6–9 Hz anti-damping. The delay hypothesis is the classic candidate: a delay τ turns assist into anti-damping above `1/(4τ)`.
> ✅ **[EVIDENCE] THE SETUP LOOKED EXCELLENT:**
> ```
>   Re(Z) at 6-9 Hz NEGATIVE on 24 of 24 routes     <- replicates the stock finding corpus-wide
>   arg(Z) fits a LINE over 3-20 Hz, R^2 median 0.820 (up to 0.972)
>   tau median 28.33 ms  [p10 19.0, p90 41.1]
>   1/(4*tau) = 8.83 Hz   <-> the ratchet sits at 7.79 Hz
> ```
> 🛑 **AND THE CONTROL KILLS IT.** If τ sets the anti-damping frequency, `1/(4τ)` and the crossover must **rise together** across routes. They do not:
> ```
>   1/(4tau) vs crossover Re(Z)<0    pearson -0.393  p 0.148    NULL, and the sign is WRONG
>   1/(4tau) vs most-negative f      pearson -0.764  p 0.0009   significant, but BACKWARDS
>
>   median 1/(4tau)  8.19 Hz    median crossover  3.26 Hz    median most-negative  12.38 Hz
> ```
> **`Re(Z)` is already negative from ~3.3 Hz — far below the 8.8 Hz the delay predicts — and the one significant correlation runs the wrong way.** The phase IS delay-like; **τ does not set the crossover.** ⇒ **REFUTED, on the control built into the test rather than on a later re-reading.**
> ⚠ **A near-miss worth recording:** the EMA lag at `k=20` is **−77.26° at 7.79 Hz ≡ 27.5 ms**, against a measured τ of **28.33 ms**. That coincidence is *not* evidence — a first-order pole's phase **saturates** with frequency while the measured phase is **linear**, so the pole cannot be what the fit is describing. Recorded so the coincidence is not re-discovered and believed.
>
> ⭐ **THE STATE AFTER THIS TICK — three closed avenues, stated plainly:**
>   1. **every cal in the assist path is measured** — only `gp-0x69a0` is free, and it is broadband;
>   2. **the one frequency-selective device cannot be aimed at the ratchet** without nulling a lane measured as damping;
>   3. **the anti-damping is not a loop-delay artifact** — refuted above.
> ⇒ **THE RATCHET'S MECHANISM REMAINS UNIDENTIFIED, AND THE CALIBRATION SEARCH SPACE IS EXHAUSTED.** That is the honest state. **V235 stays the lead** — it is the *grinding* build, and grinding is the symptom that has a mechanism and has actually moved before (V62, V88).
> ➕ Readers: `rlog-tools/score/impedance_phase_delay_test.py`, `rlog-tools/score/tau_sets_crossover_control.py`.
> ⊕ A path bug caught before it became a result: `REPO` used two `dirname`s where the layout needs three, so the first run **globbed an empty tree and printed a clean-looking table of zero routes**. A null that comes from an empty input looks exactly like a null that comes from the data.

> 🛑🛑⭐⭐⭐⭐⭐ **V238 AND V240 CUT A MEASURED DAMPER. BOTH CARRY A RATCHET COST, AND THE LEAD REVERTS TO V235. THE RATCHET IS NOT REACHABLE BY CALIBRATION.**
>
> I asked whether **anything** in the firmware is ratchet-SELECTIVE — the property every build in this arc has assumed and none has demonstrated. Two findings, and the second reverses my own last two builds.
>
> **1. THE BIQUAD IS THE ONLY FREQUENCY-SELECTIVE DEVICE, AND IT *CAN* NULL THE RATCHET.** Its zeros sit **on the unit circle**, so a notch aimed at 7.79 Hz gives `|H| = 0.00000` exactly:
> ```
>   pole Hz      r    |H|@7.79    |H|@6    |H|@9   max|H|
>     7.79    0.990    0.00000   0.7719   0.6259   1.0410
>     7.79    0.995    0.00000   0.9214   0.8427   1.0102
> ```
> 🛑 **BUT AIMING IT THERE IS FORBIDDEN BY THE KIT'S OWN MEASUREMENT.** `gp-0x6b86` vs wheel rate, 3 routes, coherence-gated:
> ```
>   6-9    cos -0.918   DAMPING   all 3 agree
>   9-12   cos -0.989   DAMPING   all 3 agree     <- near-perfect damping
>   12-15  cos -0.629   DAMPING   all 3 agree
>   22-30  cos +0.936   PUMPING   all 3 agree
> ```
> The record's instruction is verbatim: *“place a notch only where the lane PUMPS. **Never notch 6–15 Hz on this lane.**”*
>
> **2. 🛑 AND THAT SAME TABLE CONDEMNS V238 AND V240.** They do not use a notch — they use a rate limiter — but they cut the same lane in the same bands:
> ```
>   V240's cut:   6-9  -6.0 %     9-15  -11.7 %     15-22  -3.0 %
> ```
> **They remove the most damping exactly where the lane damps hardest (9-12 Hz, cos −0.989).** And the two records are **consistent, not conflicting**: the aggregate `Re(Z)` at 6–9 Hz is measured anti-damping on **stock at every speed**, so this lane is one of the things *offsetting* Honda's anti-damping — and cutting it makes the net **worse**.
> ⇒ **V238 and V240 renamed `RATCHET-COST-DO-NOT-FLASH-FIRST-…`.** My *“largest measured ratchet lever”* headline for V240 was wrong **twice over**: it is broadband, and at the ratchet it points the wrong way. Corrected once already this session for the first error; this is the second.
> ✅ **V235 IS THE LEAD.** Its notch sits at **25.0 Hz**, inside the unanimous PUMPING band — exactly where the rule says a notch belongs — and its gain at the ratchet is **0.9879**, so it barely touches the damping bands. 15 payload bytes, the smallest build in the arc.
>
> ⭐⭐ **THE ARC'S RESULT, STATED PLAINLY: THE RATCHET IS NOT REACHABLE BY CALIBRATION.**
>   * every cal in the assist-map path is now **measured**; only `gp-0x69a0` moves the band without taking assist away, and it is **broadband** — it cuts damping and pumping alike;
>   * the **one** frequency-selective device cannot be aimed at the ratchet without nulling a damper;
>   * every remaining cal lever is **broadband gain reduction** — the V101 trade arriving through different cells.
> ⇒ **The next real step is not another cal build.** It is finding what *creates* the anti-damping, which the stock baseline says is **Honda's, present at every speed before we touch anything**, and which we multiply 2.4–3.0× at 29–86 km/h.

> 🛑🛑⭐⭐⭐⭐ **V240 IS BROADBAND, NOT RATCHET-SELECTIVE — AND IT IS WEAKEST IN BOTH SYMPTOM BANDS. MY OWN “LARGEST MEASURED RATCHET LEVER” HEADLINE OVERSOLD IT.**
>
> Same 14 routes, same machinery, band by band:
> ```
>   band              ratio     change    what lives here
>   ratchet  6-9      0.9399     -6.0 %   the ratchet
>   grind    9-15     0.8832    -11.7 %
>   grind   15-22     0.9699     -3.0 %   V62's grinding band
>   pump    22-40     0.8294    -17.1 %   (ALIASED from 52-71 Hz)
>   ALL      1-50     0.8933    -10.7 %
> ```
> 🛑 **THE LANE LOSES 10.7 % ACROSS THE WHOLE BAND, AND THE RATCHET GETS 6.0 % — LESS THAN AVERAGE.** V62's grinding band gets **3.0 %**, less still. `gp-0x69a0` is a **rate limiter**, so it cuts high frequency generally; there is nothing ratchet-selective about it. **Both of the operator's symptom bands are among its WEAKEST.**
> ✅ **What stays true:** it never RAISES any band on any route (max ratio 1.000 everywhere), and it is still the only cal in the path that moves the band with `assist p50` at exactly 1.0000.
> ⚠ **AND A COST THE ASSIST PERCENTILES DO NOT SHOW.** `assist p50 = 1.0000` is an amplitude statistic; a **−10.7 % broadband HF cut in the assist lane** is the kind of change that reads as *duller steering*, not as *nothing*. The card now says so in those words rather than leading with the band number.
> ⇒ **V240 REMAINS THE LEAD** — it is the only free lever and it does reduce both symptom bands — **but it is not a fix, and the card no longer implies it might be.**
> ➕ Reader: `rlog-tools/score/v240_band_profile.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **CAL CENSUS BY MEASUREMENT — `gp-0x69a0` IS THE *ONLY* LEVER IN THE WHOLE ASSIST-MAP PATH THAT BUYS DAMPING WITHOUT TAKING ASSIST AWAY.**
>
> Every cal the map path reads, perturbed one at a time through the integer-exact mirror on 10 routes, scored on 6–9 Hz band power **and** on delivered assist:
> ```
>   cal                     scale   band 6-9  assist p50  assist p95
>   gp-0x69a0 NORMAL         0.60     0.9126     1.0000     0.9469   <- V240, THE ONLY FREE ONE
>   CAL_7384  slope cap      0.60     0.9998     1.0000     1.0000   <- inert, confirmed again
>   CAL_7178  slot ceiling   0.6/1.4  1.0000     1.0000     1.0000   <- COMPLETELY INERT
>   CAL_713C  X-ish[9]       0.6/1.4  1.0000     1.0000     1.0000   <- COMPLETELY INERT
>   CAL_7200  torque clamp   0.6/1.4  1.0000     1.0000     1.0000   <- COMPLETELY INERT
>   SPD_CAP_Y torque cap     0.6/1.4  1.0000     1.0000     1.0000   <- COMPLETELY INERT
>   CAL_7468                 1.40     0.3888     0.5192     0.6255   <- just turns ASSIST DOWN
>   BOOST_Y   angle boost    0.60     0.5698     0.6077     0.8092   <- just turns ASSIST DOWN
>   CAL_713A                 1.40     0.7185     0.7386     0.8742   <- just turns ASSIST DOWN
> ```
> ✅ **THE DISCRIMINATION IS THE RESULT.** Three cals move the band — and all three move **assist with it**. `gp-0x69a0` moves the band with **assist p50 at exactly 1.0000**. It is the only cal in the path that changes the lane's *shape* rather than its *gain*, which is precisely the operator's standing constraint: *“low apparent steering mass and friction to LKAS **AND** no ratcheting.”*
> 🛑 **AND THE GAIN LEVERS ARE WORSE THAN PLAIN GAIN SCALING.** Band power goes as gain², so `CAL_7468`'s 0.5192 assist should give **0.269** band; it gives **0.3888**. `BOOST_Y`'s 0.6077 should give 0.369; it gives 0.5698. **Every one of them is strictly worse than simply lowering the overall assist gain** — which the operator already rejected on V101. They are not levers, they are the same trade at a discount.
> ⭐ **FOUR CALS ARE MEASURED COMPLETELY INERT** at ±40 %: `CAL_7178`, `CAL_713C`, `CAL_7200`, `SPD_CAP_Y`. Band ratio **1.0000 exactly** at every dose. They can come off every future shortlist.
> ⇒ **V240 SURVIVES ITS OWN CENSUS.** The lever it moves is the only free one in the path, and the path now has no unexamined cal left.
> ➕ Reader: `rlog-tools/score/cal_census_by_measurement.py`. Runs the whole census in one command.
> ⚠ **WHAT THE CENSUS DOES NOT SAY:** that −8.7 % band is a −8.7 % symptom. It measures the lane's contribution at the band; the step to felt ratcheting is the loop model, which is the part the record calls incomplete.

> 🛑🛑⭐⭐⭐⭐⭐ **V240 — THE *NORMAL* SLEW CURVE HAS NEVER BEEN TOUCHED, AND IT IS THE LARGEST MEASURED RATCHET LEVER THE KIT HAS.**
>
> `FUN_00035b20` selects `gp-0x69a0` from **two** curves on the hard-reversal counter:
> ```
>   NORMAL       0xC6936 X=[320,1600,3200,4480]   0xC693E Y=[358,358,461,512]   <- ALWAYS LIVE
>   OSCILLATING  0xC6912 X=[640,3200,6400,12800]  0xC691A Y=[358,307,307,307]   <- V192 moved THIS
> ```
> 🛑 **V192 TIGHTENED THE WRONG ONE — and said so itself.** Its card: the oscillating curve *“is read ONLY on the counter≥5 branch so it is provably inert in normal driving.”* **The NORMAL curve is byte-stock on all 161 images.** Nobody has ever moved the curve that is actually live.
> ✅ **V240 applies HONDA'S OWN RATIO to it.** Honda's oscillation response steps 512 → 307 = **0.5996**, so `[358,358,461,512] × 0.600 → [215,215,277,307]` — and **Y[3] lands on 307, Honda's own oscillating value exactly.** V240 makes the normal curve as tight at speed as Honda's own oscillation response already is. **Like V192, not a polarity gamble.**
> ⭐ **[EVIDENCE] MEASURED — 14 routes, integer-exact mirror + Welch band power at 6–9 Hz:**
> ```
>   6-9 Hz band   0.9399   -6.0 %   range 0.813 .. 1.000
>   assist p50    1.0000   +0.0 %   <- ordinary driving UNAFFECTED
>   assist p95    0.9469   -5.3 %   <- only the top of assist demand pays
>   gate duty     5.78 %   (was 2.35 %)
>
>   vs  0xC6906 the lag pole   -3.8 % across its WHOLE range
>       0xC6384 the slope cap   0.0 %  -- MEASURED INERT, V236/V239 withdrawn
> ```
> ⇒ **1.6× the pole's ENTIRE range, at no median cost.**
> ✅ **THE OPPOSITE DIRECTION WAS TESTED AND IS WRONG.** Loosening `gp-0x69a0` to remove the relay entirely (gate duty **0.00 %**) **RAISES** 6–9 Hz band power by **2.8 %**. The limiter is helping; V240 makes it help more. That control is what makes the direction evidence rather than a guess.
> ⭐ **V240 BUILT** — image `f2745df252e7ce7e…` · rwd `617f63f3cbd3de34…` · 35/35. V238 base, 8 payload bytes, **31 from the car**. V192's oscillating curve left byte-identical.
> ⚠ **A 6 % LANE-GAIN CUT IS NOT A PROMISE OF A 6 % SYMPTOM CUT.** What is measured is this lane's contribution at the band. The step to *felt* ratcheting is the loop model, and that model has been **wrong twice this session** — it oversold `0xC6384` as *“3.4× more damped”* when the cell is inert, and it framed `0xC6906` as an additive branch when it is a blend.
> ⚠ **HESITATION is the named failure mode** (V192's card), and it applies with **more** force here because this curve is always live. **0.8× = `[286,286,369,410]` is the back-off rung, but it measures only −0.5 %** — a retreat, not a compromise.
> ⊕ **A branch-selection error I caught in my own last two ticks:** `g69a0_of()` defaults to curve **B**, the *oscillating* branch, and my clip-duty and slope-cap measurements used it. Re-run on curve **C** the numbers are unchanged — the two curves are identical below 20 km/h (both 358) and these routes run under 39 km/h — but **the conclusions were resting on the wrong branch until checked.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE ASSIST-MAP LANE IS CLOSED AS A RATCHET LEVER — BOTH ITS CALS ARE NOW MEASURED, AND BOTH ARE TINY. V236 AND V239 ARE WITHDRAWN.**
>
> The census calls `gp-0x6b86`'s lane *the largest torque-fed term*, **5.8–7.8× the entire PID at 7.79 Hz**, and the kit has chased its two calibrations for the whole V236→V239 arc. Both are now sized by direct band-power measurement rather than by the loop model:
> ```
>   0xC6906  the lag pole   WHOLE range (k 20 -> 2)      3.8 %     (last tick)
>   0xC6384  the slope cap  2048 -> 1536                 0.0 %     band ratio 1.0000
>                           pushed to 256 (Honda ships 2048)  4.2 %
> ```
> 🛑 **[EVIDENCE] `0xC6384` IS INERT BECAUSE IT IS OUT OF REACH.** Lowering it moves only the **top X breakpoints** — `Y` is byte-identical at every dose — and the lowest breakpoint that moves anywhere on the speed/angle grid sits at **2844 torque counts**. Over **113,521 engaged frames on 25 routes, only 1.65 % are above that.** On a route whose torque never crosses it, `b82` and `b84` are **BIT-IDENTICAL at every dose down to 256** — the control, run before the conclusion.
> 🛑 **THE CAP'S BRANCH NEVER FIRES AT ANY SHIPPED VALUE.** The natural map slope maxes at **0.350**; the cap sits at **2.000**, i.e. **5.7× above anything the map reaches**. It first binds around 358 and only bites broadly at 256 (970/1440 segments). **V236 chose 1536 — 4.3× above where anything happens.**
> 🛑 **THIS RETIRES THE RECORD'S GATE-2 NUMBER FOR THIS CELL.** *“Q ratio 14.29 → 4.26”* was computed from a loop model that assumes the cap **scales the lane gain**. It does not — it relocates two breakpoints in a region the car barely visits. **Direction, magnitude and mechanism were all wrong for this cell.**
> ⇒ **V236 and V239 WITHDRAWN**, `.rwd` renamed `SUPERSEDED-DO-NOT-FLASH-…`. They are strictly worse than V235/V238: identical grinding treatment, plus a cell that **costs a little assist above 2844 counts and buys nothing measurable**.
> ✅ **THE SHELF REVERTS TO V238** — V235 + the pole's free 2.7 %. It is the best measured build on the shelf, and its ratchet content is honestly 2.7 %.
> ⭐ **THE STRATEGIC RESULT, and the reason this tick matters more than the builds:** the lane the loop census identified as the **largest** torque-fed term yields **at most ~4 % at the ratchet across the entire range of both its calibrations.** Whatever sustains the ratchet, **it is not reachable through this lane's cals.** The search has to move.
> ➕ New readers: `rlog-tools/score/slope_cap_band_size.py`, `rlog-tools/score/clip_duty_and_v238_dose.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **THE ASSIST-MAP LANE IS CLOSED AS A RATCHET LEVER — BOTH ITS CALS ARE NOW MEASURED, AND BOTH ARE TINY. V236 AND V239 ARE WITHDRAWN.**
>
> The census calls `gp-0x6b86`'s lane *the largest torque-fed term*, **5.8–7.8× the entire PID at 7.79 Hz**, and the kit has chased its two calibrations for the whole V236→V239 arc. Both are now sized by direct band-power measurement rather than by the loop model:
> ```
>   0xC6906  the lag pole   WHOLE range (k 20 -> 2)      3.8 %     (last tick)
>   0xC6384  the slope cap  2048 -> 1536                 0.0 %     band ratio 1.0000
>                           pushed to 256 (Honda ships 2048)  4.2 %
> ```
> 🛑 **[EVIDENCE] `0xC6384` IS INERT BECAUSE IT IS OUT OF REACH.** Lowering it moves only the **top X breakpoints** — `Y` is byte-identical at every dose — and the lowest breakpoint that moves anywhere on the speed/angle grid sits at **2844 torque counts**. Over **113,521 engaged frames on 25 routes, only 1.65 % are above that.** On a route whose torque never crosses it, `b82` and `b84` are **BIT-IDENTICAL at every dose down to 256** — the control, run before the conclusion.
> 🛑 **THE CAP'S BRANCH NEVER FIRES AT ANY SHIPPED VALUE.** The natural map slope maxes at **0.350**; the cap sits at **2.000**, i.e. **5.7× above anything the map reaches**. It first binds around 358 and only bites broadly at 256 (970/1440 segments). **V236 chose 1536 — 4.3× above where anything happens.**
> 🛑 **THIS RETIRES THE RECORD'S GATE-2 NUMBER FOR THIS CELL.** *“Q ratio 14.29 → 4.26”* was computed from a loop model that assumes the cap **scales the lane gain**. It does not — it relocates two breakpoints in a region the car barely visits. **Direction, magnitude and mechanism were all wrong for this cell.**
> ⇒ **V236 and V239 WITHDRAWN**, `.rwd` renamed `SUPERSEDED-DO-NOT-FLASH-…`. They are strictly worse than V235/V238: identical grinding treatment, plus a cell that **costs a little assist above 2844 counts and buys nothing measurable**.
> ✅ **THE SHELF REVERTS TO V238** — V235 + the pole's free 2.7 %. It is the best measured build on the shelf, and its ratchet content is honestly 2.7 %.
> ⭐ **THE STRATEGIC RESULT, and the reason this tick matters more than the builds:** the lane the loop census identified as the **largest** torque-fed term yields **at most ~4 % at the ratchet across the entire range of both its calibrations.** Whatever sustains the ratchet, **it is not reachable through this lane's cals.** The search has to move.
> ➕ New readers: `rlog-tools/score/slope_cap_band_size.py`, `rlog-tools/score/clip_duty_and_v238_dose.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **`0xC6906` IS MEASURED SMALL — THE WHOLE CELL IS WORTH 3.8 % AT THE RATCHET. V238 KEEPS ITS 2.7 % BUT MUST NOT LEAD; V239 = V236 + V238 IS THE BUILD.**
>
> Driving the **integer-exact firmware mirror** (`assist_map_mirror`) with 22 routes of real torque/speed/angle, then Welch band power at 6–9 Hz:
> ```
>   gate duty (engaged frames where the slew limiter bites): median 7.4 %, top routes 20–85 %
>   => the gate is LIVE. The cell is not inert.
>
>   BUT the CUT (table1 − table2) carries a median 0.4 % of its power in 6–9 Hz.
>   It is almost entirely LOW frequency, so it is restored at ANY pole value.
>
>   6–9 Hz band power vs the car:  k=8  (V238)   0.9731   −2.7 %   range 0.709..1.005
>                                  k=2  (floor)  0.9622   −3.8 %   range 0.589..1.007
> ```
> 🛑 **[EVIDENCE] THE ENTIRE REACHABLE RANGE OF `0xC6906` AT THE RATCHET IS 3.8 %.** V238 already takes 2.7 % of it; the floor buys 1.1 % more. **A nibble, not a fix.**
> ✅ **This CONVERGES with the archive**, which reached *“THE EFFECT IS TOO SMALL”* from a linearisation of `|1−P·L|`. Two independent routes, same verdict — that is a convergence, not a re-derivation, and it retires the cell as a primary lever.
> 🛑 **AND IT CORRECTS MY OWN LAST CARD.** The per-frame cut looked like **6–14 %** (`p50|b84|` conditional on the gate), but most of that cut is low-frequency and never reaches the band. **The per-frame amplitude overstated the lever 2–5×.** Score the BAND, not the per-frame amplitude.
> ⚠ **A measurement error caught before it reached the operator:** the first pass used a fallback key chain `('tq','sc_t','cs_t')`, and the `loopop_*` caches — which carry no `tq` — **silently fell through to `sc_t`, which is NOT the torque sensor** (p50 129.9, max 159.9, near-constant, against `tq`'s p50 111 / max 4076). That manufactured a **0.0 % gate duty on 40 routes** and would have **retired a live lever**. The fallback is deleted; the script now requires the exact keys or skips the cache. **A fallback that substitutes a different physical signal is not a convenience, it is a silent wrong answer.**
> ⭐ **V239 BUILT — V236 + V238**, image `3c1bf1e9d5f8b79a…` · rwd `f8582ad978dcd6fc…` · 37/37. `0xC6384` is the lever with the **size**: it caps the map's own interpolation slope, so it scales **both** tables — the whole lane, not the residue the pole gates. Combining costs no interpretability now that the pole's contribution is bounded at 3.8 %. **V236 stays on the shelf as the paired arm, exactly 8 bytes from V239.**
> ⚠ **`0xC6384`'s own size is still NOT measured** — *“3.4× more damped”* rests on the loop model the record corrected. Direction well-founded, magnitude soft. The 2.7 %/3.8 % for the pole **are** measured.
> ➕ New reader: `rlog-tools/score/clip_duty_and_v238_dose.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **V237 WAS BACKWARDS — THE LANE IS A *BLEND*, NOT A DIRECT PATH PLUS A LAGGED BRANCH. V238 IS THE SAME CELL THE OTHER WAY, AND IT IS HONDA'S OWN DIRECTION.**
>
> Reading the tail of `FUN_000352b4` properly — decompile first, which is what settled it:
> ```
>   gp-0x37e8   Y array, capped by 0xC6384          -> table1 -> gp-0x6b7a   (V236's cell)
>   gp-0x3810   Y array, ALSO slewed by gp-0x69a0   -> table2 -> uVar25      (V192's cell)
>
>   bVar3  = (table2 < |table1|)            the gate: where the SLEW limiter bit
>   iVar33 = (table1 - table2) * bVar3      exactly what the slew limiter cut
>   iVar34 = table2*bVar3 + table1*!bVar3   the DIRECT path is the LIMITED value
>   out    = iVar34 + EMA_k(iVar33)
>
>   =>  out(f) = table2 + H_k(f)*(table1 - table2)
>            = table1 at DC        (the slew limit fully UNDONE)
>            = table2 at high f    (the slew limit fully IN FORCE)
> ```
> 🛑 **`k` IS NOT A BRANCH GAIN. It is the valve on how much of the slew limiter's tightening survives to the output at a given frequency.** Raising it restores MORE of the cut at 7.79 Hz, which **raises** the lane's gain there; every torque-fed lane is a denominator term in `Z = (Z0+P·F)/(1−P·L)`, so that is **more positive feedback and less damping**. **V237 pushed the ratchet the wrong way and is WITHDRAWN** — `.rwd` renamed `SUPERSEDED-DO-NOT-FLASH-…`.
> ✅ **LOWERING k IS HONDA'S OWN DIRECTION.** `FUN_00035b20` TIGHTENS `gp-0x69a0` when its hard-reversal counter trips — tightening that limiter *is* Honda's built-in oscillation response, and **V192 applied Honda's own 0.600 ratio to it once more**. V238 opens the same mechanism further through a different cell. Like V192, this is **not a polarity gamble**.
> ⭐ **V238 BUILT — `0xC6906` Y[0..3] 20 → 8**, 8 payload bytes on V235. image `34ceb5aefaa9bdd5…` · rwd `e9faa7b461c6118b…` · 36/36.
> ```
>   k     corner     |H| at 7.79 Hz    tau       fraction of the cut UNDONE at the ratchet
>   20    1.554 Hz      0.1966       0.102 s      20 %   <- the car
>    8    0.622 Hz      0.0797       0.256 s       8 %   <- V238
>    2    0.155 Hz      0.0200       1.024 s       2 %   <- the firmware's own floor
> ```
> **8, not the floor:** at `k=2` tau is ~1 s, and V192's card already names the failure mode — *“watch for a brief HESITATION replacing the ratchet ⇒ too tight”*. V238 cuts the restore **2.5×** at tau 0.256 s and leaves 2 as a second rung.
> ✅ **DC gain of the EMA is exactly 1 at every k** (verified against the integer recursion: steady state `iVar24 → iVar33·128`, then the ±0x80 deadband and `>>7` give back `iVar33 − 1`). ⇒ **no static assist change at any steering input.** Unlike `0xC6384`, which IS a real gain and does cost effort.
> 🛑 **ALSO WITHDRAWN with V237: its “the MANUAL arm runs k=41 and has no ratchet” consistency check.** Under the blend it points the OTHER way (manual restores MORE of the cut, not less), and **either reading is confounded** — engagement adds the whole LKAS path, and the archive already found the pole difference *“FAR TOO SMALL”* to explain the engaged/manual contrast. **The manual arm is not evidence for direction in either sense.**
> ⚠ **DIRECTION structural, SIZE unmeasured.** The worth of V238 depends on how hard the slew limiter bites in normal driving — the **clip duty** — which has not been measured on a route. `analysis-2020accord/studies/telemetry/run_clip_duty.py` is the reader that would answer it.
> ⊕ **A cell-identity correction that nearly went the other way:** `gp-0x69a0` is **NOT** `0xC6384`. It is the slew limit `FUN_00035b20` selects from two speed/counter curves (`0xC6912`/`0xC691A` — the `358 307 307 307` block **V192 already moved**, which sits immediately after the pole table and which an earlier pass mistook for part of it). `0xC6384` is separately `tp+0x7384`, read as `float × 1/1024 = 2.000` and capping the **interpolation slope** in the same build loop. **Two different limiters in one loop; V236 and V192 hold one each, V238 holds the valve between them.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE NO-COST RATCHET LEVER IS NOW AIMED — RAISE k — WITH A STRONG CONSISTENCY CHECK. BUT THE SAFE DOSE IS TINY AND THE CELL LAYOUT IS NOT CONFIRMED, SO NO BUILD.**
>
> **The model validates exactly**, which confirms the recursion was read correctly. From `iVar24 += (iVar33*0x80 − iVar24)·k >> 11` the branch is a first-order EMA with `a = k/2048`, **DC gain exactly 1** — which is why k costs no static assist:
> ```
>   at 8.64 Hz   k=20 -> |H| 0.1779, arg -78.20   (archive: 0.1779, -78.20)  MATCH
>                k=41 -> |H| 0.3491, arg -68.02   (archive: 0.3491, -68.02)  MATCH
>
>   at 7.79 Hz (the ratchet):
>     k=20   |H| 0.1966  arg -77.26   corner  1.56 Hz   <- ENGAGED today
>     k=41   |H| 0.3819  arg -66.15   corner  3.22 Hz   <- MANUAL arm
>     k=160  |H| 0.8569  arg -29.65   corner 12.95 Hz
>     k=640  |H| 0.9917  arg  -6.13   corner 59.63 Hz
> ```
>
> 🛑 **RETRACTED — “DIRECTION: RAISE k” was WRONG; the answer is LOWER k. See the blend block above.** The archive's own arithmetic — *“engaged lags 10.18° MORE, which moves `1−P·L` the RIGHT way (1.798 → 1.713)”* — means **more lag ⇒ smaller |1−P·L| ⇒ less damping**. Raising k reduces lag, so it damps.
> 🛑 **RETRACTED — the consistency check is WITHDRAWN: under the blend it points the other way, and either reading is confounded by engagement adding the whole LKAS path.** Original text: the MANUAL arm already runs k=41, and the ratchet is ABSENT in manual** (engaged clears its null 7/7, manual 0/7). **The arm with the higher k is the arm without the symptom** — exactly what this direction predicts, from data that was never used to derive it.
> 🛑 **BUT THE SAFE DOSE IS NEGLIGIBLE.** k 20→41 moves |1−P·L| 1.713→1.798, i.e. **4.7 % less Q** on a Q ratio of 14.3. The archive reached the same place and headlined it *“THE EFFECT IS TOO SMALL”*. Larger k is a different matter — k=640 is a **10× magnitude change and 71° less lag** — but that is far outside the linearisation those figures come from, on the branch the record itself calls **incomplete**.
> 🛑 **AND I STOPPED SHORT OF BUILDING, because the cell layout is NOT established:**
> ```
>   0xC6906..0C   20 20 20 20              four values
>   0xC690E..18   0 4 640 3200 6400 12800  six, ascending -- looks like an X axis
>   0xC691A..20   358 307 307 307          four more
> ```
> That does **not** parse as `[n, X…, Y…]`, and no plausible header nearby yields a valid `n` with a monotone X. **Two 4-value blocks straddling a 6-value axis is not a layout I can edit safely** — the kit's own V850 trap list already contains a *“LERP-vs-(lo,hi)”* misreading, and writing the wrong halfwords corrupts an axis rather than a gain. **Closing it needs a Ghidra trace of the LERP's reader, not a guess about which four cells are Y.**

> 🛑🛑⭐⭐⭐⭐⭐ **V236's MAGNITUDE IS SOFT — the record corrects the census that produced it. AND THERE IS A NO-EFFORT-COST RATCHET LEVER, UNTOUCHED IN 161 IMAGES, WHOSE DIRECTION IS UNKNOWN.**
>
> **The correction, from `STATE-ARCHIVE-2026-08-29-wander.md`:** the loop census priced `gp-0x6b86`'s lane as **memoryless** (*“transfer at 7.79 Hz is real, 0°, magnitude = the local slope”*), and the decompile shows otherwise — a **parallel lagged branch**, a comparator-gated difference through a lag added back to the direct path. That is a **lead-lag compensator, not a static curve** ⇒ *“any `|L|` computed from the slope alone is **incomplete**.”*
> ⇒ **V236's “3.4× more damped” rests on a slope-only `|L|`.** The cap scales the DIRECT path but not the lagged branch, so the real reduction in loop gain is **smaller than 3.4× implies**. **Direction holds; magnitude is soft.** The drive card should not carry 3.4× as if it were measured.
>
> ⭐ **AND THE LAGGED BRANCH HAS ITS OWN CAL, WHICH IS A POLE RATHER THAN A GAIN:**
> ```
>   0xC6382 (MANUAL arm)  = 41   on stock, the car, V158, V168, V222, V235, V236 -- NEVER MOVED
>   0xC6906 (ENGAGED arm) = LERP  20 20 20 20 | 0 4 640 3200 6400 12800  -- FLAT at k = 20
>
>   at 8.64 Hz:   k=20 (engaged)  |H| 0.1779  arg -78.20 deg
>                 k=41 (manual)   |H| 0.3491  arg -68.02 deg
> ```
> ✅ **THIS ANSWERS THE QUESTION I SET: the trade is NOT strictly an identity.** Via `0xC6384`, ratchet damping and near-centre assist are the **same parameter** — it is a gain, so buying damping costs effort, unavoidably. But `0xC6906` is a **POLE**: it reshapes this lane's response at the ratchet frequency **with no static-assist cost at all**, and it runs **only when engaged**, which matches an engaged-only symptom.
> 🛑 **WHY I AM NOT PROPOSING IT: THE DIRECTION IS UNKNOWN.** Raising k raises the branch's magnitude AND reduces its lag; whether that adds or removes damping depends on how the branch enters `1−P·L`, and **the record flags precisely that model as incomplete for this branch.** An unaimed lever on the lane that produced the aborted V94 drive is not something to build on a guess. **Recorded as a characterised CANDIDATE with its gate stated, not a build.**
> ➕ **What would aim it:** the lagged branch's contribution to `|L|` at 7.79 Hz, computed from the decompiled recursion rather than the slope — the same treatment the direct path already has. That is an analysis, not a drive.

> 🛑⭐⭐⭐⭐ **V236's COST, MEASURED RATHER THAN ADJECTIVAL: it reduces assist over 34.2 % of engaged driving, concentrated near centre.**
>
> I had been calling it *“25 % less assist at small inputs”* without measuring how much driving is at small inputs. The cap binds only over X 0–100 of the map's axis, and `cs_tq` is on every route:
> ```
>   scale check: pooled max 8139 vs the map's last knot 4150 and clamp 8192 -- CONSISTENT
>
>   segment        fraction   cumul    cap binds?
>      0 -   25       9.8 %    9.8 %   YES
>     25 -   60      12.4 %   22.1 %   YES
>     60 -  100      12.0 %   34.2 %   YES
>    100 -  150      13.5 %   47.6 %
>    150 -  250      21.4 %   69.0 %
>    250 -  450      11.5 %   80.5 %
>
>   ENGAGED TIME WHERE V236 REDUCES ASSIST: 34.2 %   (pooled n = 877,942 over 13 routes)
> ```
>
> ⚖ **A third of engaged driving, not a sliver — but not constant either.** Median driver torque is **128–226 counts** across routes, so **normal cornering sits just above the capped region and is untouched**. The 34 % is concentrated in **near-centre, small-correction steering**, which is exactly where added effort is noticeable.
> ✅ **It is the DRIVER's feel, not LKAS.** `0xC616C` = 0 on all 161 images ⇒ the map is fed by the torque sensor alone, so nothing here changes what LKAS can ask for. That was already proven; this measurement says where the *driver* would feel it.
> ➕ **And the absolute magnitude is modest**: the cap already clips the raw small-signal slopes (6.16 / 5.26 / 3.05 over the first three segments) down to 2.000, so V236 takes an already-reduced number down another 25 %. **The operator now has the number instead of my adjective**, which is what he needs to decide whether the only gated ratchet lever is worth its price.

> 🛑🛑⭐⭐⭐⭐ **NEITHER OF MY LANE SCANS CAN IDENTIFY THE RATCHET'S SOURCE — one was in the wrong channel, the other has no discriminating power. AND I INVERTED A PHASE CONVENTION AGAIN.**
>
> Redoing the all-lanes scan against `cs_tq`, the channel the ratchet actually lives in:
> ```
>   lane        routes   coh 6-9   coh ctl    phase     verdict
>   gp-0x6C2C     1        0.982     0.295     19.1°    follows torque
>   gp-0x6B70     1        0.980     0.452     19.6°    follows torque
>   gp-0x6B26     2        0.979     0.507     19.3°    follows torque
>   gp-0x6ABC     3        0.978     0.481     19.0°    follows torque
>   gp-0x6B86     3        0.973     0.337     19.2°    follows torque
>   gp-0x6B4C     2        0.963     0.315     18.4°    follows torque
>   gp-0x6B94     1        0.961     0.241     19.8°    follows torque
> ```
> 🛑 **THE UNIFORMITY IS THE FINDING.** Seven different lanes, coherence 0.95–0.98, phase all within **15.9–19.8°**. That is not seven results — **every one of these lanes is a filtered function of the SAME torque sensor**, so coherence with `cs_tq` is trivial and shared, and the common ~19° (≈7 ms at 7.5 Hz) is a shared path delay. **The measurement cannot discriminate between them.**
> 🛑 **AND I INVERTED THE PHASE CONVENTION — the SECOND csd inversion in this kit's history.** `scipy.csd(x,y)` returns `arg(Y)−arg(X)`; with `x=lane, y=cs_tq` a POSITIVE phase means **`cs_tq` leads the lane**, i.e. the lane FOLLOWS. My first pass printed *“LEADS cs_tq”* for exactly that condition and would have named **all seven lanes ratchet drivers**. The record already carries one such inversion, which *“recommended LOWERING `0xC63AC` when the correct move was raising it”*. Corrected in the script itself, not just in prose.
> ⇒ **NET: neither scan identifies a source lane.** The rate-referenced one looked in a channel the ratchet is absent from (`cs_rate` margin **1.03 = chance**); the torque-referenced one looks in the right channel but has **no discriminating power**. My earlier conclusion *“no linear lane is the ratchet's source”* is **withdrawn as unsupported** — not reversed, unsupported.
> ✅ **This does not weaken V236.** The assist map is the suspect on the handoff's own reasoning — largest torque-fed term at 5.8–7.8× the PID, the cap binds 3/9 knots, GATE 2 passes on magnitude and phase — none of which rests on either of my scans.

> 🛑🛑⭐⭐⭐⭐⭐ **V236 BUILT — THE RATCHET LEVER WAS FOUND, GATED AND BUILT AS V168 LAST YEAR, THEN SILENTLY LOST IN THE REBASE CHAIN. SAME FAILURE AS LEVER B.**
>
> ```
>   0xC6384 (base power-assist map SLOPE CAP):
>     stock 2048 · car 2048 · V158 2048 · V222 2048 · V231 2048 · V235 2048
>     V168  1536   <- the ONLY build ever to carry it, and it never flew
>
>   image 509785673468a346ac366dfb2fb8e491231f49a4e440e22ef9ce4fe39602d862
>   rwd   25646ed45da588e05f2386e79239e47bad9da0ea26dfacaea8727af74e66d8f7
>   30/30 assertions · TWO payload bytes on V235
> ```
>
> **The case, from `HANDOFF-2026-08-29-the-ratchet-is-the-assist-map.md`, which did the work:** the ratchet is **in TORQUE, not wheel rate** (`tq 7.62 · cs_tq 7.42 · cs_rate 1.03 = CHANCE`); **engagement CREATES it** (engaged 7/7, manual 0/7, speed-matched **19.9× [4.82, 35.64]**); **nothing has moved it** (ρ −0.14, p 0.787 post-V102; pinned at 8.64 Hz ± 7.4 %) while the **grind falls ρ −0.94 (p 0.005)** ⇒ the symptoms dissociate. `gp-0x6b86` is the largest torque-fed term, **5.8–7.8× the entire PID**, and its slope cap pins small-signal gain at exactly 2.000.
> ```
>   cap    s       |L|     |1-P.L|   Q ratio   vs stock
>   2048   2.000   2.825   0.0700    14.29     stock -- the car
>   1536   1.500   2.325   0.2346     4.26     3.4x MORE DAMPED   <- V236
> ```
> ✅ **MAGNITUDE and PHASE both pass** — the term is a REAL GAIN, so lowering the cap scales |L| without rotating it: **monotone, no reversal at any value.** That is the property every notch geometry lacked.
> ✅ **IT CANNOT TOUCH LKAS, re-verified on V235:** `0xC616C` = 0 ⇒ a clamp with limit 0 annihilates its input ⇒ `gp-0x6b4a ≡ 0` ⇒ the map is fed by the **driver torque sensor alone**.
> 🛑 **THE COST COLLIDES WITH A STANDING OPERATOR DIRECTIVE, and that is his call not mine.** The cap pins SMALL-SIGNAL gain, so 2048→1536 cuts the capped slope 25 % over X 0–100 — **felt as more effort at small inputs.** His instruction: *“Increasing mass and friction should not be our primary approach… We want both.”* This is the only gated ratchet lever the kit has ever produced, and it does the thing he asked to avoid. ⊕ **It does NOT cost angular velocity or acceleration** — the cap is on the map's slope, not a rate or authority limit, and 0 of 15 command/authority cells move.
> ➕ **THE ASSUMPTION ONLY A DRIVE CAN CLOSE:** `P·L` real-positive. The handoff says so — *“closes on the V168 drive itself; an unchanged excess falsifies it.”*
> 🛑 **AND IT CORRECTS MY OWN WORK TODAY:** my all-lanes scan scored `cos(phase vs cs_rate)`, and **`cs_rate` is at CHANCE for the ratchet (1.03)**. So *“every lane damps at 6–9 Hz”* is about generic 6–9 Hz motion, **not about the ratchet**. The conclusion that no lane is the ratchet's linear source does not follow from it, and the ratchet-band scan should be redone in **torque**.

> 🛑🛑⭐⭐⭐⭐⭐ **THE COULOMB RELAY IS ALREADY LARGELY DE-RELAYED ON THE CAR, AND THE RATCHET PERSISTED THROUGH A 4.6× REDUCTION IN ITS DUTY. NO BUILD WAS NEEDED TO FIND THIS.**
>
> Decompiling `FUN_0003b8f6` gives the relay explicitly:
> ```
>   iVar20 = gp-0x6752 (polarity) * gp-0x6abc * 12
>   uVar8  = cal(0xC40BC)                       the gate
>   ratio  = iVar20 / uVar8 ;  relay = clamp(ratio, -1, +1)   SATURATED when |ratio| >= 1
> ```
> ⇒ it saturates when **|gp-0x6abc| ≥ cal/12** — and `gp-0x6abc` is **already tapped** on r21/r22/r24, which is the flown knee ladder itself. The onsets 50/150/250 fall straight out of the decompile, independently confirming the ladder's own column. **The saturation duty was measurable from existing caches all along.**
>
> ```
>   build   cal    onset   |gp-0x6abc| p50 / p90    SATURATION DUTY   n_eng
>   V111     600      50       138 /  576             76.64 %         83,778
>   V112    1800     150       147 / 1293             49.99 %         48,956
>   V122    3000     250       128 /  347             16.75 %         58,650   <- THE CAR
> ```
>
> 🛑 **THE DE-RELAYING WAS ALREADY DONE.** Stock's *“pinned across 99.62 % of its range = pure relay”* is not the car's condition: **the car saturates on 16.75 % of engaged frames.** The ladder spans **77 % → 17 %, a 4.6× reduction in relay duty, all three flown — and the ratchet persisted throughout.** That is a real dose-response on the relay hypothesis, and it fails.
> ⚖ **THE CONDITIONAL LOOKS SUPPORTIVE AND IS CONFOUNDED.** Duty is higher in high-ratchet windows on all three builds (car: **0.278 vs 0.110**, 2.5×). But **the ratchet's own motion IS the relay's input** — more 6–9 Hz rate means larger `|gp-0x6abc|` means more saturation, causation or not. The association is exactly what a pure bystander would produce. **Not evidence for the relay.**
> ⇒ **The Coulomb relay is substantially weakened as the ratchet's source**, on the strongest instrument the kit recognises: the operator drove all three rungs and reported no change, across a 4.6× swing in the mechanism's own duty. **It is not fully excluded** — his verdicts on the ladder were not per-rung symptom scores — but it is no longer the prime suspect, and **a 427 relay probe is no longer worth a channel.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE RELAY KNEE CANNOT BE TESTED FROM FLOWN CAN AT ALL — DEMONSTRATED, NOT ASSERTED. AND THE WAY THROUGH IS A 427 TAP, NOT A CAVE.**
>
> With every LINEAR lane eliminated as the ratchet's source, the nonlinear candidate the record already names becomes the suspect: engagement multiplies 6–9 Hz by **2.8× (+0.413 [+0.146, +0.667])** with **no rate dependence**, via `FUN_0003b8f6`, *a Coulomb relay PROPORTIONAL TO THE COMMAND* saturating against `0xC40BC` — *“pinned across 99.62 % of its range at stock = pure relay”*.
> The flown 3-point ladder (V111 600 / V112 1800 / V122 3000, same slope, onsets 50/150/250) returned a null, and its own memory calls that *“a weak instrument that found nothing”*, naming the fix: **windows selected by SUSTAINED rate**. I ran it.
>
> ```
>   sustained-rate windows      creep 0-3    low 3-8    mid 8-15    high 15+
>     V111 (knee 600)              366          0          0          10
>     V112 (knee 1800)             173          0          0          12
>     V122 (knee 3000)             316          0          0           5
>
>   creep band, ratchet 6-9:   V111 3.509   V112 3.778   V122 3.463   flat, non-monotone
> ```
>
> 🛑 **TWO STRUCTURAL FACTS, and together they close the route:**
> 1. **3–15 °/s NEVER SUSTAINS.** Zero windows on all three routes. Steering is either creeping (<3 °/s) or transient (>15 °/s) — there is no steady mid-rate driving to measure. The ratchet's own regime (1–13 °/s) is therefore only partly observable at all.
> 2. **Where the data IS plentiful — creep, 855 windows — the three knees are IDENTICAL BY CONSTRUCTION**, since with the slope held they differ only above 50 counts. So the flat result is a null on a regime where the builds do not differ.
> ⇒ **The spectral route to the knee is CLOSED. It is not that the ladder was weak; it is that no amount of estimator work can test a cell in a regime the corpus cannot populate.**
> ✅ **BUT THE RECORD'S SUGGESTED FIX — a within-frame CAVE RUNG — IS NOT THE ONLY OPTION, AND IT IS THE BRICKING CLASS.** A **CAN 427 tap on the relay's own ratio or saturation state** gives a per-frame reading with no spectrum and no cave: 2–3 bytes in the telemetry tap, exactly the class of edit that worked for V231's biquad-state probe. **That is the way to settle whether the relay saturates in the ratchet regime**, and it is a safe build rather than the one class that has bricked this ECU three times.

> 🛑🛑⭐⭐⭐⭐⭐ **EVERY TAPPED LANE DAMPS AT THE RATCHET — SO THE RATCHET'S ENERGY SOURCE IS NOT IN ANY ASSIST LANE THE KIT CAN OBSERVE.** The net-damping metric was built for the notch and applied only there. Applying it to **every lane ever put on CAN 427**, 13 routes across 7 taps, cos(phase vs wheel rate), coherence-gated:
>
> ```
>   lane        routes     6-9 Hz    9-12 Hz    15-22 Hz   22-30 Hz
>   gp-0x6ABC      3       -0.844    -0.978     -0.314     -0.184
>   gp-0x6B26      2       -0.875    -0.987     +0.167     +0.886
>   gp-0x6B4C      2       -0.902    -0.953     +0.574     +0.921
>   gp-0x6B70      1       -0.889    -0.986     +0.038     +0.914
>   gp-0x6B86      3       -0.918    -0.989     +0.551     +0.936
>   gp-0x6B94      1       -0.918    -0.820     +0.545     +0.797   <- the AGGREGATE
>   gp-0x6C2C      1       -0.646    -0.996     +0.070     -0.234
> ```
>
> ✅ **EVERY value at 6–9 Hz is NEGATIVE, and every value at 9–12 Hz is negative.** Not one lane injects energy at 7.79 Hz, and the aggregate opposes the motion at **−0.918**. Yet driver-side `Re(Z)` is NEGATIVE at 6–9 Hz on three replicated drives — the column IS doing work on the driver's hands.
> 🛑 **⇒ THE RATCHET'S SOURCE IS OUTSIDE THE OBSERVABLE ASSIST LANES.** A direct explanation for sixty builds failing on it: **reducing a damping lane makes it worse, and raising one is bounded by that lane's own ceiling.** No aggregator cal change can be the fix, because there is nothing there to remove. The record already suspected the plant; this confirms it **from the lane side**, which had never been checked.
> 🛑 **THE LIMIT, AND IT MATTERS AS MUCH AS THE FINDING.** This is a LINEAR cross-spectral measurement. A **nonlinear** mechanism — stick-slip, a Coulomb relay, a deadband — can inject energy without showing positive cos in a linear cross-spectrum, and the kit has a Coulomb relay finding and describes the ratchet as stick-slip-like. ⇒ **what is refuted is a LINEAR lane source; a nonlinear one remains open and is invisible to this method.** This is NOT “the ratchet is unfixable”.
> ➕ **Consequence for V235:** its value is on the **grinding**, where the lanes demonstrably pump (22–30 Hz, +0.79 to +0.94 on six of seven taps). It was never going to fix the ratchet — and now there is a reason rather than a hope.

> 🛑 **SESSION NARRATIVE: `docs/handoffs/2026-08/HANDOFF-2026-08-30-the-notch-was-in-the-wrong-place.md`** — the arc V228→V235, the six claims of mine that were wrong and what caught each, the two defects found in builds I was recommending, and the standing blocks. **Read it before the blocks below**, which are in reverse chronological order.

> 🛑🛑⭐⭐⭐⭐ **THE GAIN HEADROOM IS NOT COMPUTABLE FROM THE CORPUS — so no gain step may be proposed on V235's damping. Recording this as a BLOCK, not an open question.**
>
> The idea was sound: V101's 8× vibrated because loop gain rose with nothing added to absorb it, and V235 adds **36 % more net damping** (J −0.28054 → −0.38119 on the clean lane) by flipping both pumping bands negative. So how much gain could that carry?
> 🛑 **It cannot be answered from what exists:**
> ```
>   route  build  gain   biquad      427 tap      clamps
>   r95    V101   7128   f8c2c4bf    gp-0x6B94    4096/4096   <- VIBRATED, operator rejected
>   r96    V102   5346   f8c2c4bf    gp-0x6B4C    3072/3072   <- his own revert
> ```
> * **not single-variable** — V101 moved the forward clamps too (4096 vs 3072), so gain and clamp are confounded;
> * **different 427 taps**, so the lane observable is not comparable;
> * the only common signal is **driver-side Re(Z), which the gain confounds mechanically** — `Re(Z) = torque/rate`, so more loop gain raises rate and makes Re(Z) less negative regardless of symptom. **The rejected build reads LESS anti-damped** (9–12 Hz −38.9 vs −61.7), which is the artifact, not a fact.
> ⇒ **36 % more damping vs a 33 % gain step is not a comparison, it is a coincidence of two numbers that are not commensurable.** Converting damping into gain headroom needs an OPEN-LOOP transfer — the kit's own GATE 2 — and the kit has never measured one.
> 🛑 **STANDING BLOCK: do not propose a gain step on the strength of V235's damping.** A gain change is the exact class that produced *“GRINDING/VIBRATION AT ALL SPEEDS”* (V101) and the worst-in-corpus build (V71c). **What would close it:** an open-loop measurement at two gains with everything else byte-identical and the SAME tap — which is a drive-dependent experiment, not an analysis.

> 🛑🛑⭐⭐⭐⭐⭐ **V235 AGAINST THE OPERATOR'S THREE STATED GOALS — and it only addresses two of them.** He asked for grinding, LKAS authority and peak command oscillation. Every argument I have made for V235 is about the first. Checking the other two:
>
> **1. GRINDING / RATCHETING — addressed.** The notch cuts the band the lane and the aggregate both pump in (19–32 Hz, coherence up to 0.97), while holding the damping band at **1.004×**.
>
> **2. LKAS AUTHORITY — V235 DOES NOTHING. Verified, not assumed:**
> ```
>   0xC6CD0 gain 5346 · 0xC61B2/B4 clamps 3072 · 0xC61B3/B5 12 · 0x3AA96 251
>   0x3AC42/0x3AC58 rails · 0xC6446 5244 · 0xC6444 512 · 0xC6C42 4
>   0xC62EA 0 · 0xC407E 511 · 0xC6194 3 · 0xC6316 640
>   => 0 of 15 command/authority cells differ from the car.
> ```
> 🛑 **And authority may not be improvable at all by the obvious lever.** The command rails at ±4096 on 2.7 % of engaged frames, and raising `0xC6CD0` buys authority back — but **the operator flew 8× as V101 and reported *“GRINDING/VIBRATION AT ALL SPEEDS”*, then reverted to 6× at his own choosing.** So the gain route to authority is **measured harmful**, by him. Any future authority work has to come from somewhere else.
>
> **3. PEAK COMMAND OSCILLATION — the premise is REFUTED on this bus, and V235 acts in the regime that survived.** Both testable readings failed their controls: *“the command reverses after a peak”* gives corr **+0.099 (p=0.188)** over 179 rail events with two of five routes NEGATIVE; *“the car oscillates while the command is large”* **reverses** — the roughness ratio FALLS with command size. ⇒ **the roughness is a SMALL-command phenomenon.** A biquad is linear, so V235's notch acts identically at every amplitude, including the small-command regime where the roughness actually lives. **It addresses the phenomenon, not the phrasing.**
> ⚖ **Net: V235 is aimed at 2 of the 3 stated goals and is inert on the third.** That belongs on the card rather than being left for him to infer from silence.

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


## 📁 **EARLIER BLOCKS (26) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

