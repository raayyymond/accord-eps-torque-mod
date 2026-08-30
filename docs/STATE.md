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

> 🛑🛑⭐⭐⭐⭐⭐ **V237 BUILT — A RATCHET LEVER THAT COSTS NO EFFORT. The LERP layout that blocked it last tick is now READ OUT OF THE DECOMPILE, and the firmware's own clamp bounds the dose.**
>
> ```
>   image bebd6c6ca9e9ad735016f477dece6dfa275bfaf9bb65a1c5d13d8c8716b812f1
>   rwd   9cab1723e1b969883869677ef7f42e49beba04f09256ac14942a9d5c7b48c764
>   🛑 WITHDRAWN -- BACKWARDS. EIGHT payload bytes on V235: 0xC6906 Y[0..3]  20 -> 80
> ```
>
> ✅ **LAYOUT SETTLED FROM THE READER, not inferred.** `pcVar26 = tp+0x7906` is the Y base; the bounds tests read `tp+0x78FE` and `tp+0x7904`; the out-of-range arms return `tp+0x790C` and `tp+0x7906`. ⇒ **X = [0, 9830, 26214, 32768] at `0xC68FE`, Y = [20,20,20,20] at `0xC6906`.** The reader then clamps: `if (uVar40 < 0xcd) max(2, uVar40) else 0xcc` ⇒ **k is bounded to [2, 204] by the firmware itself.**
> ✅ **NO EFFORT COST, BY CONSTRUCTION.** The branch is an EMA with `a = k/2048` and **DC gain exactly 1**, so k moves the POLE and cannot move static gain. **V237 does not carry V236's 34.2 %-of-driving assist reduction** — `0xC6384` stays at 2048, asserted.
> ```
>   at 7.79 Hz     |H|       arg      corner
>     k= 20      0.1966   -77.26    1.56 Hz   <- engaged today
>     k= 41      0.3819   -66.15    3.22 Hz   <- MANUAL arm; archive: “TOO SMALL” (4.7 % less Q)
>     k= 80      0.6314   -49.46    6.34 Hz   <- V237
>     k=204      0.9063   -23.63   16.70 Hz   <- the firmware's ceiling
> ```
> ⚖ **WHY 80 AND NOT THE CEILING.** 41 is Honda's manual value and the archive already called its effect too small. The ceiling extrapolates to ~21 % less Q, but that is a **linear extrapolation over 5× the measured range** on a branch the record calls incomplete, and a 10× jump on an unmodelled lever is how the V94 drive ended. **80 puts the corner at 6.34 Hz, just BELOW the 7.79 Hz mode** — responsive AT the mode, still rolling off above it — takes 52 % of the available phase change, and leaves 204 as a second rung.
> 🛑 **WHAT IS ASSUMED:** the SIZE rests on the archive's 1.713/1.798 linearisation extrapolated 2.7×. **Direction is well-founded** (the archive's own arithmetic, plus the manual arm at k=41 being the arm WITHOUT the ratchet); **magnitude is an order-of-magnitude estimate.**

> 🛑🛑⭐⭐⭐⭐⭐ **“THE CALIBRATION SURFACE IS EXHAUSTED” WAS AN OVERCLAIM. THERE IS ONE SENSOR-FED LANE NOBODY HAS EVER SCORED AT THE RATCHET, AND IT IS NOW BUILT AS V245.**
>
> Four ticks closed the assist-map path, the notch axis and the loop-delay hypothesis, and I concluded the calibration surface was exhausted **for both symptoms**. That was true of the **assist-map path**. The **resonance PID is a different lane**, and the record had been pointing at it the whole time.
> ⭐ **The golden model's own census, verbatim:** *“LIVE `gp-0x6ad4` resonance PID — **the most reachable authority of any gated lane HERE** … V56's mute of this lane was scored at ~21 Hz — the lane has **NEVER been scored at 6–9 Hz**, so it is OPEN, not eliminated.”*
> ⊕ And the return-to-centre analysis narrows the ratchet's entry to **five sensor-fed lanes** — *“for 52–70 % of the return the LKAS lane is a DC CONSTANT, yet the 6–9 Hz |tq| envelope is unchanged … a constant cannot carry 7.8 Hz.”* **Four are spoken for** (r24 = Lever B, `gp-0x6b26` = the restored damper, `gp-0x6bbe` at 76 % of its rail, the plant-model path = `0xC63AE`). **`gp-0x6ad4` is the fifth**, virgin in **216 of 218 images**.
> ```
>   0xC67C4   1280 -> 512    the ceiling LERP's middle X breakpoint
>   X = [128, 1280, 3200] counts = [2, 20, 50] km/h     Y = [0, 1024, 1024]
>   => full ceiling from 8 km/h instead of 20; up to 3x more through CREEP,
>      and IDENTICAL above 20 km/h.
> ```
> **That is where the ratchet lives** — the record puts it at creep, 1–13 °/s, and *“the damper cannot reach the micro regime”* is the recurring complaint. **This lane can.**
> ✅ **ADDITIVE, NOT A TRADE.** The biquad is untouched, so **V241's entire grinding treatment is carried**. V244 had to give up the 22–30 Hz cut to attack the ratchet; V245 does not.
> 🛑 **THE RISK IS REAL AND THE RECORD NAMES IT: “OPEN lever — may PUMP.”** More ceiling is more authority, and if the lane's phase at 6–9 Hz is wrong that means more **pumping** — a WORSE ratchet. **Nobody has scored this lane in that band**, which is exactly why it is worth a drive and exactly why the outcome cannot be predicted.
> ⭐ **BUILT — image `10494d5fe6a948ef…` · rwd `00bc8ddbb0135cd3…` · 35/35, ONE payload byte.** Cal-only, **no cave**, nothing changes above 20 km/h, instantly revertible to V241. The knot is registered **build-scoped** with the LERP endpoints asserted unmoved, rather than whitelisting the table.
> ⇒ **1525 checks passed, 50/50 builders bit-exact.** Shelf: **V241 · V242 · V243 · V245**.

> 🛑🛑⭐⭐⭐⭐⭐ **THERE IS NO SECOND BIQUAD. THE NOTCH AXIS IS CLOSED AT V241's 21.8 %, AND THE CEILING IS STRUCTURAL.**
>
> The ceiling found last tick — *no notch reaching 6–10 Hz can pass the passband gate* — is a property of **one** 2nd-order section. So: is that the only filter the firmware has? Scanned the whole calibration region `0xC4000–0xC8000` for any 4 consecutive float32 forming a **stable** biquad (`|a2| < 1`, `|a1| < 1 + a2`, plausible `c4`, pole radius ≥ 0.3):
> ```
>   20 candidate blocks -- and 19 are ARTIFACTS.
>   the tell: almost all report zero/pole near 250 Hz, which is just acos(0) when a coefficient
>   happens to be ~0. And they hit at CONSECUTIVE addresses (0xC65F8/FC/600, 0xC6634/38/3C,
>   0xC6BD4/D8) -- a sliding window over runs of similar floats, not distinct filters.
>
>   0xC60A8   a1 -1.5372  a2 0.6346  b1 -1.8808  c4 0.8173   zero 55.23 Hz  pole 42.35 Hz
>   ^ the ONLY block with real filter geometry -- Honda's notch, already known.
> ```
> ⇒ **[EVIDENCE] THE SINGLE 2nd-ORDER SECTION IS ALL THERE IS.** No second biquad to cascade, so the passband ceiling cannot be beaten by splitting the job across two narrower sections. Creating a filter means **code**, which means a **cave** — this kit's only bricking class.
> ⭐ **THE NOTCH AXIS IS THEREFORE CLOSED, and V241 sits at its ceiling.** 22–30 Hz at **21.8 %** of the torque excess is not a compromise and not a guess — it is **the most a single biquad can legally remove**, given `max|H| ≤ 1.0000` and a 0–5 Hz passband floor of 0.99. Nothing further is available on this axis by calibration.
> ⊕ **What that settles, taken with the last three ticks:** the ratchet band is unreachable by notch; the pump/damp rule that seemed to block it is moot; there is no second filter; and every cal in the assist path is measured. **The calibration surface is exhausted for both symptoms, and V241/V242/V243 are what it yields.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE 6–10 Hz NOTCH IS UNREACHABLE — AND THE BLOCKING RULE TURNS OUT TO BE IRRELEVANT. THE BAND IS CLOSED FOR A STRUCTURAL REASON INSTEAD. V244 WITHDRAWN.**
>
> The prize was priced at **66.2 %** of the torque excess against V241's 21.8 %, so V244 was built to settle the disputed rule by driving it — a 12-byte cal edit, no cave. **The kit's own passband gate failed it:**
> ```
>   V244 passband floor over 0-5 Hz = 0.9179   against a 0.99 bar
>   "THIS BUILD TURNS THE BASE ASSIST DOWN, it does not notch"
> ```
> 🛑 **MY OWN LOCALITY CONSTRAINT WAS TOO LOOSE AND THE GATE CAUGHT IT.** I required `|H| ≥ 0.75` outside 5.5–10.5 Hz, which permits a **25 % cut at 5 Hz** — inside the band the driver actually steers in. The gate's bar is 0.99, and V244 sits at **0.9179**. **The 66 % was bought by cutting the driver's own band — the gain-reduction trade wearing a different hat.**
> ⭐ **AND THE SEARCH UNDER THE REAL GATE SETTLES THE BAND FOR GOOD:**
> ```
>   zero Hz   pole Hz      r    max|H|   pb min   torque excess removed
>     10.75     10.50   0.990   1.0000   0.9905          14.7 %   <- closest LEGAL to the ratchet
>     11.00     10.75   0.990   1.0000   0.9919          12.7 %
>     11.50     11.25   0.990   1.0000   0.9940           9.9 %
>
>   V241, aimed at 22-30 Hz:                              21.8 %   and it PASSES the gate
> ```
> ⇒ **[EVIDENCE] EVERY NOTCH THAT ACTUALLY REACHES 6–10 Hz VIOLATES THE PASSBAND GATE.** At 1 kHz a 7.75 Hz notch's skirt inevitably drags 0–5 Hz down; the closest legal geometry sits at **10.75 Hz, ABOVE the ratchet, and removes LESS than V241 does.**
> ⭐⭐ **SO THE PUMP/DAMP RULE NO LONGER BLOCKS ANYTHING.** The band is unreachable for a reason that has nothing to do with the dispute: **the ratchet sits too close to the steering band to notch with a single 2nd-order section at 1 kHz.** Whether the lane damps at 6–15 Hz is now moot for notch design — and the two defects found in that rule no longer need resolving to make progress.
> ✅ **AND IT VINDICATES V241's PLACEMENT.** 22–30 Hz is not a compromise forced by a disputed rule; it is **the best a single biquad can legally do**, by 21.8 % against 14.7 % for the closest ratchet-ward geometry.
> ⇒ **V244 WITHDRAWN**, `.rwd` renamed `SUPERSEDED-DO-NOT-FLASH-…`. The flashable shelf is unchanged: **V241 · V242 · V243**.
> ⊕ The 66 % figure is **RETRACTED**. It was computed under a locality floor of 0.75, which the kit's passband gate rejects.

> ⭐⭐⭐⭐⭐ **THE 6–10 Hz NOTCH IS WORTH ~3× V241 — 66 % OF THE TORQUE EXCESS AGAINST 22 %. THE RULE BLOCKING IT IS NOW WORTH SETTLING, WITH A NUMBER ATTACHED.**
>
> Priced against the **torque** engagement excess — the lane's own domain, where **6–10 Hz carries 68.6 % of all excess weight over 3–45 Hz**:
> ```
>   collateral floor   feasible   zero    pole      r     torque excess removed
>        0.90            NONE
>        0.80             yes    7.75    7.50   0.990          66.2 %
>        0.70             yes    7.75    7.25   0.990          71.0 %
>        0.60             yes    7.25    6.25   0.985          75.5 %
>
>   V241, aimed at 22-30 Hz, on the same weight:                21.8 %
> ```
> ✅ **A genuine LOCAL notch at the ratchet — zero 7.75 / pole 7.50 / r 0.990, non-amplifying (`max|H| ≤ 1.0000`), never cutting anything outside 5.5–10.5 Hz by more than 20 % — removes 66.2 % of the torque excess. Three times what the current build achieves, and it sits ON the ratchet.**
> 🛑 **AND MY FIRST ANSWER WAS THE OPTIMISER CHEATING.** Unconstrained, it returned **pole 4.00 Hz** and claimed **96.8 %** — that is not a notch, it is a **LOW-PASS** that gutted the lane above 4 Hz while keeping unity DC to satisfy the gate. Adding *“a notch must be LOCAL”* — keep |H| above a floor outside the target band — killed it. **Same failure mode as the arbitrary 0.97 threshold earlier: an objective with a missing constraint finds the degenerate answer.**
> ⊕ **AND 0.90 IS INFEASIBLE ENTIRELY.** At 1 kHz, 8 Hz is ~0.05 rad/sample, so a single 2nd-order section's skirt is wide in absolute Hz. **No geometry cuts 6–10 Hz while leaving everything else within 10 %.** The 66 % figure costs up to **20 % collateral** on its neighbours — including the band the disputed rule says damps.
> ⇒ **THE DECISION IS NOW PRICED.** The prize is ~3× the current build, on the symptom nothing has ever moved. The blocker is a rule with **two independent defects** (clamped channel; three routes whose in-band filters differ 1.87×) that is nonetheless **not refuted**. Settling it needs the lane's sign, which needs a **cave or a clamp change** — this kit's only bricking class. **Not built. The operator now has the number.**

> 🛑🛑⭐⭐⭐⭐⭐ **A SECOND, INDEPENDENT PROBLEM WITH THE 6–15 Hz RULE: ITS THREE “AGREEING” ROUTES DO NOT SHARE A FILTER IN THE BAND IT JUDGES.**
>
> Trying to settle the rule **without new firmware**: the biquad sits IN this lane, so if builds differ in how much they cut 6–15 Hz, the aggregate `Re(Z)` there should move with the cut — cutting a damper makes the anti-damping worse. That screen came back **null** (pearson +0.144 p 0.53, spearman −0.063 p 0.79) — **but the reason is what matters: there is no contrast.** 18 of 21 builds have the biquad **UNARMED** (`0xC649B` = 0), so their cut is identically zero.
> ⭐ **AND THE ONE OUTLIER IS THE FINDING.** Read from the images:
> ```
>   build   armed     max|H|    mean 6-15   mean 22-30
>   V104      yes     1.8499       1.7878       1.4503   *** ABOVE THE 1.0000 BAR ***
>   V105      yes     1.0000       0.9577       0.1968
>   V106      yes     1.0000       0.9577       0.1968
>   V235      yes     1.0000       0.9662       0.2771
>   V241      yes     1.0000       0.9811       0.2846
> ```
> 🛑 **[EVIDENCE] THE PUMP/DAMP TABLE WAS MEASURED ON ra4/ra5/ra6 — AND ra4's BUILD AMPLIFIES 1.79× AT 6–15 Hz WHILE ra5/ra6 CUT 4 %.** That is a **1.87× difference in the lane's own transfer**, in the exact band whose sign the table claims, between three routes that were pooled as if they agreed. **They are not poolable there.**
> ⊕ **And V104 flew carrying `max|H|` = 1.8499 — worse than V194/V195/V196/V198, which were later PULLED for 1.3533–1.7177.** The amplification bar was introduced after V104, so it never applied to it. Worth knowing: a filter the lineage would now reject has already been on the car.
> ⇒ **THE RULE NOW RESTS ON MUCH LESS THAN THE RECORD TREATS IT AS RESTING ON — two independent defects:** (1) measured on `mag427`, which the frame builder **clamps to [0, 0x3ff]** so its phase carries no reliable sign; (2) pooled across three routes whose in-band filters differ by 1.87×.
> ⚠ **NEITHER REFUTES IT.** The lane may still damp at 6–15 Hz. What has changed is the weight the rule can bear: it is currently the only thing blocking the band the torque spectrum says matters, and it is **weakly founded on both axes**. **Still not built on** — settling it needs the sign, and that needs a cave or a clamp change, which is the operator's call.
> ➕ Reader: `rlog-tools/score/notch_cut_vs_rez_across_builds.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **THE 427 SIGN IS KILLED BY THE FIRMWARE, NOT THE DECODER — AND A SIGN PROBE IS NOT A CHEAP IN-PLACE EDIT. The 6–15 Hz rule cannot be settled without a cave or a clamp change.**
>
> The open thread was: the rule forbidding a 6–10 Hz notch — the one band the torque spectrum says matters — may rest on a rectified channel, and settling it needs `gp-0x6b86`'s SIGN on CAN. `FUN_00055d80` is the 0x1AB (427) frame builder, and it decides the question:
> ```c
>   uVar3 = FUN_00049a5a((int)*(short *)(gp - 0x6c18));      // SIGNED short load -- the probe cell
>   uVar4 = FUN_00049a78(uVar3);
>   FUN_00049a90((int)((uVar4 & 0xffff) * 5) >> 3, 0, 0x3ff);  // CLAMPED [0, 1023]
> ```
> 🛑 **[EVIDENCE] THE FIELD IS CLAMPED TO `[0, 0x3ff]`.** Any negative value pins to zero. **The rectification is Honda's, in the frame builder** — not a choice the cache extractor made. Confirmed independently by the data: `mag427` maxes at **exactly 1023** on ra6.
> ⊕ **The probe encoding, decoded properly:** `24 37` is `ld.w disp[gp],r6`, and the displacement is the stored halfword with **bit 0 as an opcode flag**. `stock e8 93 → 0x93E8 → gp-0x6C18`; `V241 ea c7 → 0xC7EA → gp-0x3816`, the biquad state. A repoint is genuinely 2 bytes — but it can only change WHICH cell is read, never that the result is clamped non-negative.
> ⚠ **THE THREE SINGLE-BIT CHANNELS DO NOT RESCUE IT.** The same function writes three bits (`(byte & 1) << 6`, `<< 4`, `<< 3`) sourced from byte cells — but each takes **bit 0**, and the sign of `gp-0x6b86` is **bit 15**. Pointing a bit channel at `gp-0x6b85` yields bit 8 of the value, not its sign. **Getting the sign needs a shift or mask change, or a cave.**
> 🛑 **AND CAVES ARE THIS KIT'S ONLY BRICKING CLASS** — V24, V27 and V48B all bricked the ECU. **I am not cutting one to settle an analysis question on a shelf the operator is about to fly**, and a clamp change touches Honda's own frame builder. **Not built. The cost is now known and the decision is his.**
> ⇒ **The 6–15 Hz rule stays IN DOUBT and unsettleable from the current probe design.** What it would take is now specific: either a cave that writes `sign(gp-0x6b86)` into one of the three bit channels, or a change to the `[0, 0x3ff]` clamp so the magnitude field carries a signed value.

> ✅⭐⭐⭐⭐ **THE THIRD SYMPTOM IN THE BRIEF — “peak command oscillation” — IS ALREADY REFUTED IN THE RECORD, AND THE ROUGHNESS RUNS THE OTHER WAY.**
>
> The brief named three symptoms; grinding and authority are covered by the ladder, and this one was not spoken to. It has been tested — **both readings this bus can observe were refuted with controls** — and the roughness ratio **falls** as the command grows:
> ```
>   command p90 quartile     n     roughness  P(6-30)/P(0.5-3)
>        76 -   276        928        2.4877
>       276 -   473        928        2.8547
>       473 -  1161        928        2.4342
>      1161 -  4096        928        0.6637   <- 3.7x SMOOTHER
>   log roughness vs log command  corr -0.358  p<0.0001, all five routes
> ```
> HF power rises with command (+0.491) but **LF power rises faster (+0.793)**, so the ratio falls. ⇒ **the roughness is a SMALL-command phenomenon**, consistent with the ratchet living at creep.
> 🛑 **AND THE TEMPTING INFERENCE IS WRONG.** *“Roughness falls with command, so more gain will be smoother”* is a **within-build correlation across operating points**, not a between-build prediction — and **V101 at 8× ground badly**, which is direct evidence against it. Raising the gain moves the loop, not just where you sit on the command axis. **Recorded on the card so the ladder is not oversold with it.**
> ⇒ **None of the three builds targets peak-command oscillation, and the card now says so.**

> ✅⭐⭐⭐⭐ **THE FLASHABLE ARTIFACTS VERIFY FROM THE OTHER END — and a false “DO NOT FLASH” was caught by its own control.**
>
> The builders assert their round-trip at build time and `rebuild_shelf_bitexact` re-runs them. This asks the same question **backwards, from the artifact** — so a file corrupted or replaced after its build would be caught:
> ```
>   build  status     start       bytes   payload vs image
>   V122   flown    0x13000      970752   IDENTICAL      <- the build on the car, the CONTROL
>   V88    flown    0x13000      970752   IDENTICAL
>   V108   flown    0x13000      970752   IDENTICAL
>   V241   shelf    0x13000      970752   IDENTICAL
>   V242   shelf    0x13000      970752   IDENTICAL
>   V243   shelf    0x13000      970752   IDENTICAL
> ```
> 🛑 **A FALSE ALARM, AND HOW IT DIED.** My first attempt used `crack_cipher()` and printed **“*** DO NOT FLASH ***”** on all three shelf builds. Running the same test on **flown** builds — including **V122, which is on the car right now** — failed identically. **A check that condemns the firmware currently running the vehicle is a broken check, not a discovery.**
> ⊕ **Two traps, both worth keeping:**
>   1. `crack_cipher()` is for **ORIGINAL HONDA** `.rwd` files, where the table must be recovered from a known plaintext. **The kit's builds use a KNOWN table** — `build_decode_table(FF.V9B[...])`, which is what every builder uses.
>   2. `roundtrip()` derives the expected part number from the filename with `39990[-]?…`, but the kit's filenames use a **COMMA** (`39990-TVA,A160`), so `expected` silently becomes `None`.
>   ⊕ and `parse_x31` returns `blocks` as **dicts** (`{'start','length'}`), not tuples.
> ➕ Saved as `analysis-2020accord/verify/rwd_decodes_to_image.py`, **with the flown builds wired in as controls and a distinct message when a control fails** — so the next run cannot repeat the false alarm silently.

> 🛑⭐⭐⭐⭐⭐ **RECOMMENDATION CORRECTED: V241 (6×) LEADS, NOT V242 (8×). I had been answering “give me more torque” rather than the brief as written.**
>
> The brief: *“the **safest, highest probability of working** firmware with 6x torque (or higher …) up to 16x torque with no grinding, vibration, or oscillation.”* **“Up to 16×” bounds what to EXPLORE; it does not demand the maximum.** Read that way:
>   * **V241 is 6×** — the car's own gain, all the grinding work, and **no torque lever the operator has already rejected**. It satisfies *“6× or higher”* at the floor and is the build most likely to simply work.
>   * **V242 is 8×** — the same build plus a step he **personally rejected** on V101 for grinding. Higher upside, materially lower probability of *“no grinding”*.
> 🛑 **AND LEADING WITH V242 SKIPPED HIS OWN RULING** — *“fix at 6x first, then raise to 8x”*. The fix is **built but never verified on the car**. Flying 8× first jumps the verification his ruling exists to force.
> ⭐ **THE ORDER IS ALSO THE HIGHER-INFORMATION ONE.** If V242 grinds you cannot separate the gain from the grinding work, and you are back where V101 left you. If **V241** grinds, the grinding work has failed and 8× is pointless. If V241 is clean, **V242 is a four-byte step with the grinding question already answered.** Two short drives, each interpretable — which is the kit's own build law.
> ✅ **The one-drive option is still on the card**: if he will accept the risk for a single flash, V242 is the same build plus the gain, and the 8× level itself flew **fault-free** as V101 — what was rejected was feel, not safety.
> ⇒ Card and `SHELF.md` both repointed. **No build changed; only which rung is recommended.**

> ⚠⭐⭐⭐⭐ **THE NOTCH IS AIMED ON 4× DATA AND THE CORPUS CANNOT TEST WHETHER IT TRANSFERS TO 8×. The directional hint in the record is reassuring, and it is a hint, not a measurement.**
>
> **Every route in the IMU engagement profile V241's notch was optimised against is a 4× build** (r5e/V75 → r73/V88, all pre-V100). The recommended build **V242 runs at 8×**, and the record already measured the band moving with gain — V101 (8×) put the peak at **23.0 Hz** against **20.3 Hz** on three 4× routes, *“a POLE MOVED”*.
> ⊕ Two path defects fixed to even ask the question: `extract_imu_cache.py` and the pooled scorer's `can_for` both looked in **one** kit root, while the 6×/8× routes keep their CAN caches under `analysis-2020accord/`. Fixed; **73 new IMU segments extracted** for ra4/ra5/ra6/r95/r96.
> 🛑 **AND THE ANSWER IS THAT THE DATA CANNOT SUPPORT IT:**
> ```
>   route  segments contributing   pooled speed-matched eng / man
>   ra4     2 of 16               44.0 s / 25.2 s     below the 30 s gate
>   ra5     1 of 11                6.7 s / 51.8 s
>   ra6     1 of 26               31.1 s / 26.8 s
>   r96     2 of 15               29.0 s / 71.0 s
>   r95     1 of  5               15.3 s / 24.3 s     <- the ONLY 8x route
> ```
> **The 6×/8× era has almost no speed-matched engaged-AND-manual exposure** — most segments are one arm only, so matching kills them. **The gate was NOT lowered to force an answer.**
> ⊕ **What can be said, and it is mildly reassuring:** the 4× profile peaks at **27.00 Hz** over 15–40 Hz, and V241's trough spans **22.50 → 29.75 Hz**. If the band moves *up* with gain — the direction V101 hints at — it moves **further into** the trough rather than out of it, until about 30 Hz. ⚠ **V101's 20.3→23.0 is a CAN peak, not this IMU excess metric; the two must not be mixed.**
> ⇒ **No change to the ladder.** V241/V242 keep the geometry. The honest line for the card is that the notch is aimed on 4× data, the corpus cannot test the transfer, and the geometry's trough is wide enough that the plausible shift stays inside it.
> ➕ Reader: `rlog-tools/score/engagement_band_vs_gain.py`.

> 🛑⭐⭐⭐⭐ **THE SIGN IS NOT RECOVERABLE FROM THE EXISTING CACHES — the pump/damp rule stays IN DOUBT and can only be settled by a new probe build.**
>
> `mag427`'s field is 10-bit and maxes at 1023, so a two's-complement reading was worth testing. It is **not** signed:
> ```
>   ra4/ra5/ra6 histogram: mass decays SMOOTHLY from zero; only 1.6-2.1 % of frames are >= 512
> ```
> A signed field would put mass near **both** 0 and 1023 (small negatives); this is a monotone decay from zero — **the signature of a magnitude.** The firmware transmitted `|gp-0x6b86|`, and the sign was never on the wire for these builds. (`sar 4` preserves sign in the register; the rectification is upstream of the CAN write.)
> ⇒ **The rule that forbids notching 6-15 Hz cannot be verified or refuted from any existing data.** Settling it needs a build that puts the lane's SIGN BIT on 427, plus a drive. **That is a future probe, not something to fold into a driving build** — it would cost the biquad-state probe the current shelf carries.
> ⭐ **WHY IT MATTERS ENOUGH TO RECORD:** the torque spectrum says the one band worth filtering is **6-10 Hz**, and this rule is the only thing blocking it. If the rule falls, a notch aimed there becomes the strongest lever the kit has ever had — and it would bear on the ratchet, which nothing has moved in thirty-plus builds.

> 🛑🛑⭐⭐⭐⭐⭐ **THE GAIN LADDER — V241 (6×) · V242 (8×) · V243 (10×). AND THERE IS NO 16×: IT IS BLOCKED BY A SAFETY INTERLOCK, NOT A JUDGEMENT CALL.**
>
> Operator brief, 2026-08-30: *“the safest, highest probability of working firmware with 6x torque (or higher …) up to 16x torque with no grinding, vibration, or oscillation, best firmware for autonomous driving.”*
> ```
>   V241   6x   image 2ef7eb8eb2417905…  rwd 57d240d77f568aac…   SAME gain as the car
>   V242   8x   image 424249b0c7d89fad…  rwd a94962b4240613c8…   <-- RECOMMENDED
>   V243  10x   image 5fb9ad74f104de46…  rwd 43a32ac352508557…   the ceiling
> ```
> 🛑 **[EVIDENCE] WHY 16× DOES NOT EXIST.** The forward clamp must stay **below** the soft-EME floor `0xC674E` = 5120, and it tracks the gain as `gain × 512 // 891`:
> ```
>    6x -> 3072 OK     8x -> 4096 OK     10x -> 5120 EQUALS the floor (V219/V225 used 4608)
>   12x -> 6144 EME AUDIT FAILS          16x -> 8192 EME AUDIT FAILS
> ```
> **Above ~10× the command cannot be DELIVERED** — it clips long before the nominal gain — and reaching it means raising a **safety interlock**. `0xC674E` is asserted **FROZEN at 5120** in every build; I did not touch it and would not without an explicit instruction. Even V243's 10× is nominal: its clamp is held at 4608, so delivered authority rises **4096 → 4608, about 12 %**.
> ⭐ **THE LADDER IS FOUR BYTES PER RUNG.** V241 already carries V222's whole lineage — the diff showed V241 = V222 **minus** the 8× step, **plus** the IMU notch, Honda's `0xC63AE` and Lever B at V88's optimum. So V242 = V241 + `0xC6CD0` + two clamps. Nothing else moves.
> 🛑 **THE RISK, NOT BURIED: 8× FLEW AS V101 AND WAS REJECTED** — *“GRINDING/VIBRATION AT ALL SPEEDS, ONLY WHILE LKAS COMMANDS”*; the operator reverted to 6× himself. Peak **moved 20.3 → 23.0 Hz**, de-confounded gain **2.7–3.9× at 22–26 Hz**.
> ✅ **WHY V242 IS NOT A REPEAT:** that 22–26 Hz band is exactly what this lineage's notch attacks, and the notch is aimed by the **IMU — independent of the EPS** — which independently names 22–30 Hz as the largest engagement-created band. **V101 raised the gain with NO grinding treatment.** It may still grind; the lineage is unflown.
> ✅ Registered as **STAGED** in `closeout_verify_published`, with the pricing written into the registry rather than the gate bypassed — that gate exists because of V101.
> ⇒ **1493 checks passed, 48/48 builders bit-exact.**
> ⚠ **WHAT THE BRIEF COULD NOT BE GIVEN:** no authority lever beyond the gain exists — every other cal in the assist path was measured this session and is inert or broadband gain reduction. And **the ratchet is not fixed**; V242 attacks grinding, which two independent instruments now agree is a different problem.

> 🛑🛑⭐⭐⭐⭐⭐ **THE RULE THAT BLOCKS THE ONLY USEFUL BAND MAY REST ON A RECTIFIED CHANNEL. MY OWN RE-CHECK WAS INVALID FOR THE SAME REASON — REPORTING BOTH.**
>
> The torque spectrum says the one band worth filtering is **6–10 Hz**, and a single claim forbids it: *“never notch 6–15 Hz on this lane”*, from `gp-0x6b86`'s measured phase (cos −0.918 / −0.989 / −0.629, 3/3 routes). That rule condemned V238 and V240 and now blocks the strongest lever the data points to, so it was worth re-deriving.
> ⚠ **MY RE-CHECK FLIPPED ALL SIX BANDS — WHICH IS A RED FLAG, NOT A RESULT.**
> ```
>   band     mine    record        band     mine    record
>   6-9    +0.565   -0.918        15-22   +0.635   +0.551
>   9-12   +0.894   -0.989        22-30   -0.338   +0.936
>   12-15  +0.933   -0.629        30-40   +0.106   +0.821
> ```
> ✅ **I VALIDATED MY PIPELINE FIRST, on signals whose phase I know** — `lane = −rate` returns cos −1.000 (damping), `lane = +rate` returns +1.000 (pumping), quadrature returns 0.000. The convention is right. **So a wholesale six-band inversion had to come from the DATA, and it does:**
> 🛑 **`mag427` IS RECTIFIED — all non-negative on all three routes** (min 0.00 across 93k/66k/155k samples). A rectified signal's phase against wheel rate carries no reliable sign: rectification folds the negative half-cycles and doubles the fundamental. **My re-check is therefore INVALID, and it is not evidence that the record is wrong.**
> 🛑 **BUT THE SAME DEFECT REACHES THE RECORD'S OWN TABLE.** It was measured on `gp-0x6b86` via CAN 427 on **ra4/ra5/ra6** — and those three caches carry **`mag427` WITHOUT `sgn427`**. The extractor family does produce a sign channel (`extract_r85.py` writes both), and **59 other caches carry it — but not these three.** So unless the original analysis had a signed source these caches do not hold, **the table's SIGNS rest on a rectified channel too.**
> ⇒ **STATUS: the rule is IN DOUBT, not overturned.** I am **not** acting on it — no 6–10 Hz notch is being built, and **V238/V240 stay costed**. A load-bearing claim that may rest on a rectified channel is a flag to resolve, not a licence.
> ➕ **THE FIX IS CONCRETE AND NOW POSSIBLE:** re-extract ra4/ra5/ra6 **with `sgn427`**, which the extractor family already supports and which the revived `extract/` toolchain can finally run. Then the pump/damp table can be derived on a signed channel for the first time — and with it, whether the 6–10 Hz band is genuinely forbidden.
> ⭐ **The kit's own memory already warned about this class:** *“`band_envelope` is RECTIFIED, not analytic”*. The warning existed; the table was built anyway.
> ➕ Reader: `rlog-tools/score/pump_damp_recheck.py` (the convention self-test is in the script).

> 🛑🛑⭐⭐⭐⭐⭐ **THE TORQUE CHANNEL AND THE CHASSIS DISAGREE COMPLETELY — AND THE NOTCH ACTS ON TORQUE. V241's OBJECTIVE IS IN THE WRONG DOMAIN.**
>
> The last untested link in V241's chain: its geometry was optimised against **chassis motion**, but the notch filters a **torque lane**. Same local-excess design, same speed matching, run on `tq`:
> ```
>   band            TORQUE     IMU
>   ratchet 6-10     2.849   1.516    <- TORQUE peaks here
>   mid    10-15     0.946   1.547
>   grind  15-22     1.245   1.621
>   V241   22-30     1.337   2.481    <- IMU peaks here
>   upper  30-45     1.052   1.575
>
>   profile agreement across 3-45 Hz:  spearman rho = +0.040  p = 0.61   -- NONE
> ```
> 🛑 **[EVIDENCE] IN TORQUE, ENGAGEMENT'S DOMINANT EFFECT IS THE RATCHET BAND (2.849), AND V241's BAND IS NEARLY THE WEAKEST (1.337).** The two profiles are **uncorrelated**. The IMU's 22–30 Hz peak is a **motion** phenomenon the torque lane does not share.
> ⇒ **V241 (and V235 equally) is aimed at a band that is near the bottom of the spectrum it can actually reach.** The 28 % improvement over V235 is real *on the motion objective*; both are aimed by a spectrum that is not the lane's.
> 🛑 **AND THE BIND IS NOW EXPLICIT.** In the domain the notch acts on, the biggest engagement effect sits at **6–10 Hz** — and the record forbids notching there, because the lane is measured **damping** (cos −0.918 / −0.989 / −0.629, 3/3 routes) and cutting it is what condemned V238/V240. **The one band worth filtering is the one band that must not be filtered.**
> ✅ **This also unifies the session's findings rather than contradicting them:** the ratchet is a **torque** phenomenon (`tq` 2.849; the record's own margins `tq 7.62 · cs_tq 7.42 · cs_rate 1.03`), while the 22–30 Hz band is a **motion** phenomenon (IMU 2.481, and the audio confirms it is real, not folded). **They are different things in different domains — which is exactly the grinding/ratchet dissociation, now located in the physics rather than just in the statistics.**
> ⚠ **CAVEATS, both real:** `tq` rides the ~101 Hz CAN frame, so its 22–30 Hz carries ~30 % folded from 71–79 Hz — that inflates it if anything, so the 1.337 is an **upper** bound. And `tq` is the driver **sensor**, not the lane output; the notch changes assist, which reaches `tq` only through the loop.
> ⇒ **V241 STAYS THE LEAD** — it beats V235 on the motion objective and respects Honda's damping floor, which V235 did not. **But the honest expectation for either build is lower than the last two ticks implied, and the card now says so.**
> ➕ Reader: `rlog-tools/score/torque_vs_imu_band_agreement.py`.

> ✅⭐⭐⭐⭐ **V241's GEOMETRY IS NOT FITTED TO THE MEDIAN CAR — it wins under 5 of 6 objective weightings, and the one exception explains exactly what separates it from V235.**
>
> The obvious weakness of V241's objective is that it weights the **median** route. If the geometry only suits the median, it is fitted. Re-searched under every reasonable alternative:
> ```
>   weighting                  zero Hz  pole Hz     r      cost
>   MEDIAN (V241 used this)      29.75    22.50  0.940  0.31079  <- V241
>   MEAN                         29.75    22.50  0.940  0.38980  <- V241
>   GEOMETRIC MEAN               29.75    22.50  0.940  0.31743  <- V241
>   WORST ROUTE (minimax)        29.75    22.50  0.940  0.40573  <- V241
>   p75 across routes            29.75    22.50  0.940  0.38251  <- V241
>   UNWEIGHTED (flat 22-30)      25.00    22.00  0.960  0.06746
> ```
> ✅ **[EVIDENCE] Identical geometry under median, mean, geometric mean, minimax and p75.** With the leave-one-route-out result (same winner on all 10 folds), the shape is robust to **both** which routes are used and how they are combined.
> ⭐ **AND THE ONE EXCEPTION IS THE MOST USEFUL LINE IN THE TABLE.** Weighting the band **flatly** reproduces **25.00 / 22.00 / 0.960 — essentially V235's geometry.** So the entire difference between the two builds is that **V235 aimed at the NOMINAL CENTRE of 22–30 Hz, while V241 aims at where the excess MEASURABLY IS.** The only objective that prefers V235 is the one that ignores the measurement.
> ⊕ That also explains the geometry's shape: with the pole at 22.50 and the zero at 29.75, the trough spans the whole excess band rather than nulling one frequency — which is why it beats a sharper notch centred at the peak.
> ➕ Reader: `rlog-tools/score/notch_weighting_robustness.py`.

> ⭐⭐⭐⭐⭐ **V241 BUILT — THE NOTCH RE-AIMED ON THE INDEPENDENT INSTRUMENT. 28 % MORE OF THE MEASURED EXCESS, AND IT STOPS CUTTING THE DAMPING BAND HARDER THAN HONDA.**
>
> V235's geometry was fitted to a **CAN objective** — the EPS's own channels, the same subsystem the build modifies. The IMU had no part in it, and it names 22–30 Hz as the largest engagement-created band. **V235's band is right; its shape is not:**
> ```
>   V235   zero 25.00 Hz  pole 23.50 Hz  r 0.960   cost 0.43254   min|H| 6-15 = 0.9108
>   stock  zero 55.23 Hz  pole 42.35 Hz  r 0.797   cost 0.57508   min|H| 6-15 = 0.9344
>   V241   zero 29.75 Hz  pole 22.50 Hz  r 0.940   cost 0.31079   min|H| 6-15 = 0.9374
> ```
> ✅ **V241 removes 28.1 % more of the measured engagement excess than V235** (V235 ranks 256 of 1522 feasible geometries), **and cuts LESS of the damping band.** 🛑 **V235 sat at 0.9108 there — BELOW stock's 0.9344 — so it was cutting ~2.5 % more of the band the record says never to notch. V241 is back above Honda's floor at 0.9374.**
> ✅ **LEAVE-ONE-ROUTE-OUT: 29.75 / 22.50 / 0.940 wins on ALL TEN folds — one distinct winner in ten.** Not fitted to any single route; the same check V235's geometry passed on the CAN objective.
> ⭐ **BUILT** — image `2ef7eb8eb2417905…` · rwd `57d240d77f568aac…` · **33/33, 12 payload bytes.** Both gates recomputed **from the written bytes**: `max|H| = 1.0000` (the lineage bar) and `min|H| 6-15 = 0.9374 ≥ 0.9344`. Coefficients written **by formula**, never by decimal.
> 🛑 **AND A THRESHOLD ERROR I CAUGHT MID-RUN.** The first pass imposed an arbitrary **0.97** floor on the damping band — and **STOCK ITSELF came back “VIOLATES”**, because Honda dips to 0.9344. An arbitrary bar that rejects the car is not a bar. The record had to make this exact correction once before, when a **1.5× threshold carried from V232** was replaced by *“the bar is Honda”*. **The floor is now what stock achieves, measured from the image.**
> ⚠ **NOT CLAIMED:** that 28.1 % of modelled cost is 28 % less grinding. The weight is chassis **motion**; the notch filters a **torque** lane. Better-founded aim, not a promise.
> ⇒ **V241 IS THE LEAD; V235 IS THE PAIRED ARM, exactly 12 bytes away**, so the geometry can be isolated after the fact.
> ➕ Readers: `rlog-tools/score/notch_vs_imu_profile.py`, `rlog-tools/score/imu_engagement_spectrum.py`.

> ✅⭐⭐⭐⭐⭐ **V235's NOTCH IS AIMED AT THE LARGEST ENGAGEMENT-CREATED BAND IN THE CORPUS — confirmed on the independent IMU, which had no part in choosing it.**
>
> Rather than scoring the kit's three named bands, ask the open question: **at which frequencies does engagement raise chassis motion above what the road explains?** Speed-matched, each route divided by its own road control, 10 routes:
> ```
>   band          Hz     median   p25..p75    routes>1
>   ratchet     6-10      1.496   0.96..2.12     45 %
>   mid        10-15      1.696   1.05..3.59     47 %
>   grind      15-22      1.621   1.14..2.18     64 %
>   V235 notch 22-30      2.481   2.16..5.01     67 %   <-- LARGEST
>   upper      30-45      1.575   1.34..2.04     63 %
> ```
> ✅ **[EVIDENCE] 22–30 Hz is the biggest engagement effect in the whole 3–45 Hz range**, and the per-bin profile peaks at **25–26 Hz (2.400 / 2.452)** — precisely where V235's notch sits. **The notch geometry was chosen by CAN-based net-damping optimisation; the IMU had no part in it and independently names the same band.**
> ⭐ **It is ~1.7× the ratchet band**, which turns out to be the *weakest* of the named bands here (1.496, and only 45 % of routes above 1). Together with the V88 ranking, that is a consistent picture across two instruments: **the band V235 attacks is where engagement actually does the most, and it is not the ratchet band.**
> ⚠ **THE BOUND:** the IMU measures **motion**, and the notch filters a **torque** lane. A band loud in the chassis need not be the band that matters in torque — but a notch aimed at the loudest engagement-created motion band is a far better-founded placement than one aimed at a band the chassis never shows.
> ⊕ **A fix that mattered:** routes differ slightly in IMU sample rate, so their Welch grids differ by a bin. The first run crashed on `vstack` rather than silently averaging misaligned frequencies — every curve is now interpolated onto one grid. A shape error is a lucky failure; the same mismatch one bin smaller would have quietly smeared the peak.
> ➕ Reader: `rlog-tools/score/imu_engagement_spectrum.py`.

> ✅⭐⭐⭐⭐⭐ **THE GRINDING METRIC IS REAL — V88 RANKS CORRECTLY ON AN INSTRUMENT NO CALIBRATION CAN TOUCH, AND THE PREDICTION WAS WRITTEN BEFORE THE ANSWER WAS READ.**
>
> The same speed-matched IMU pipeline, scored in three bands, each against its own road control:
> ```
>   build  route    eng s   man s   ratchet 6.5-9.5   grind 15-22   mid 9.5-15
>   ?      r31       38.5    70.5             1.096         1.090        0.632
>   ?      r37       59.1    40.5             1.169         0.753        1.062
>   ?      r3a       40.3    31.9             0.893         0.841        0.980
>   ?      r3b       48.1    45.6             2.870         0.854        3.801
>   ?      r5d       64.4    55.1             2.935         0.669        1.164
>   V75    r5e       38.7    43.0             1.566         1.504        0.392
>   V80    r66      101.8   158.2             1.133         0.989        1.075
>   V85    r6e       50.2    60.3             1.514         0.965        0.900
>   V86B   r70       82.9    86.7             1.140         1.042        0.709
>   V88    r73       57.2    83.7             2.481         0.715        0.851
>   MEDIAN                                    1.341         0.909        0.940
> ```
> **The pre-registered prediction, stated in the script before the answer was read:** *“V88 is the kit's ONE measured grinding fix. If the grinding metric is real, V88 should sit LOW in the grind column and not in the ratchet column.”*
> ```
>   V88 grind 15-22      0.715   ->  only 11 % of other builds are BELOW it   (near-BEST)
>   V88 ratchet 6.5-9.5  2.481   ->        78 % of other builds are BELOW it   (near-WORST)
> ```
> ✅ **[EVIDENCE] It landed exactly there.** Two things are confirmed at once, off-EPS:
>   1. **the kit's grinding metric measures something real** — the build CAN says fixed grinding ranks near-best for grinding on a sensor that cannot be gamed by any calibration;
>   2. **the dissociation is real** — the same build is near-WORST for the ratchet. Grinding and ratcheting are different problems, now agreed by two independent instruments.
> ⭐ **AND A BAND-LEVEL ASYMMETRY WORTH KEEPING:** the ratchet band's median is **1.341** (engaged exceeds its road control) while the grind band's is **0.909** (it does not). **Engagement creates the ratchet band; it does not create the grinding band** — consistent with grinding being a modulation of something already present rather than something engagement summons.
> ⇒ **THIS SUPPORTS THE CURRENT LEAD.** V235 targets grinding — the symptom with a mechanism, a measured past success, and now an off-EPS confirmation that its metric is sound and that it is a separate problem from the ratchet.
> ⚠ **Still a screen:** one route per build, so build and road are perfectly confounded; n = 10 routes, 5 mapped builds. The V88 result is a **confirmed prediction**, not an attribution.
> ➕ Reader: `rlog-tools/score/imu_bands_by_build.py`.

> 🛑⭐⭐⭐⭐⭐ **NO BUILD HAS EVER MOVED THE RATCHET — AND THAT IS NOW CONFIRMED ON AN INSTRUMENT NO BUILD COULD HAVE GAMED.**
>
> Every ratchet score in the record was computed from the **EPS's own CAN channels** — the same subsystem the builds modify. So a hypothesis has stood open this whole arc: *maybe a build did fix it, and CAN-based scoring could not see it.* The comma's gyro cannot be altered by any calibration, so it settles that. Each build scored against **its own road control**, speed-matched:
> ```
>   build  route   segs   eng s   man s  gyro exc  road ctl   ratio
>   V75    r5e        7    38.7    43.0     4.118     2.630   1.566
>   V80    r66       15   101.8   158.2     3.350     2.955   1.133
>   V85    r6e        7    50.2    60.3     5.102     3.371   1.514
>   V86B   r70        4    82.9    86.7     1.737     1.524   1.140
>   V88    r73       11    57.2    83.7     4.723     1.904   2.481
>   median 1.514   spread 1.133 .. 2.481
> ```
> 🛑 **[EVIDENCE] NO BUILD SITS BELOW THE SPREAD.** The arc's ratchet null is **real**, not an artefact of scoring the ratchet through the very subsystem being modified.
> ✅ **AND V88 — the kit's ONE measured grinding fix — carries the HIGHEST ratchet ratio (2.481).** That is exactly the dissociation the record already reports from CAN (*grind falls ρ −0.94 p 0.005 while the ratchet stays pinned at 8.64 Hz ± 7.4 %*), now reproduced **off-EPS**. Two independent instruments agreeing that **grinding and ratcheting are different problems** is the strongest form that claim has ever had.
> ⚠ **THIS IS A SCREEN, NOT AN ATTRIBUTION.** One route per build, so build and road are **perfectly confounded** — a route driven on rougher tarmac cannot be separated from a worse build. n = 5. A standout would have been a lead to chase; the absence of one is the useful part.
> ➕ Reader: `rlog-tools/score/imu_ratchet_by_build.py` (route→build map from `rlog-tools/lib/v95_rez_lib.py`).

> ✅⭐⭐⭐⭐⭐ **THE RATCHET IS REAL MOTION — CONFIRMED ON A SENSOR PHYSICALLY INDEPENDENT OF THE EPS, FOR THE FIRST TIME IN THIS KIT.**
>
> Every prior ratchet finding came off the EPS's own CAN channels, so all of them shared one failure mode: an artefact of EPS signal processing, a decode error, or torsion-bar scaling. The comma's LSM6DS3TR-C shares none of that. Pooled per route across segments, **speed-matched**, with a **road control** on vertical acceleration:
> ```
>   route  segs  eng s  man s   f0 Hz  gyro exc  road ctl  ratio
>   r66      15  101.8  158.2    6.71     3.350     2.955  1.133
>   r70       4   82.9   86.7    9.08     1.737     1.524  1.140
>   r73      11   57.2   83.7    7.30     4.723     1.904  2.481
>   r5d      17   64.4   55.1    8.09     4.315     1.470  2.935
>   r6e       7   50.2   60.3    9.08     5.102     3.371  1.514
>   r31       4   38.5   70.5    9.47     1.737     1.585  1.096
>   r37      15   59.1   40.5    7.50     3.220     2.755  1.169
>   r3b      14   48.1   45.6    6.71     8.017     2.793  2.870
>   r5e       7   38.7   43.0    7.10     4.118     2.630  1.566
>   r3a       7   40.3   31.9    9.08     4.606     5.158  0.893
> ```
> ✅ **[EVIDENCE] 9 of 10 routes positive · sign test p 0.0215 · Wilcoxon p 0.0195 · median ratio 1.341, bootstrap 95 % CI [1.118, 2.481] — the CI excludes 1.**
> 🛑 **AND I NEARLY RECORDED THE OPPOSITE.** Read by eye, the two highest-exposure routes (r66, r70) give the two lowest ratios — which looks exactly like the noise signature, a well-powered arm regressing to nothing. **Tested rather than eyeballed, that pattern is not there:** ratio vs exposure is **null** (pearson −0.078 p 0.83, spearman +0.297 p 0.40), and the **top-half-exposure routes give the HIGHER median ratio (1.513 vs 1.169)**. The apparent trend was two points out of ten, and it was one edit away from going into the record as *“the ratchet does not reach the chassis”* — the opposite of what the data says.
> ⭐ **WHAT IT ESTABLISHES:** the ratchet produces **real chassis motion**, engagement-gated, at 6.7–9.5 Hz, above what road input explains. **Every CAN-side ratchet finding now has an independent corroboration it has never had.**
> ⚠ **WHAT IT DOES NOT:** the effect is **modest (1.34×)**, `f0` scatters across 6.71–9.47 Hz so this is a **band, not a sharp line**, and n = 10 routes. It does **not** settle resonance vs stick-slip, and the IMU on the windscreen bounds **motion**, not torque.
> ⊕ **Two more stale-path defects fixed to get here**, from the same 2026-08-26 reorg as last tick's: the IMU extractor carried a **hardcoded 6-route dict** that rejected every other route with a bare `KeyError` — including **every route holding the speed-matched exposure** — and read caches from the pre-reorg `_cache_{tag}/` path. It now globs the rlogs like its sibling and reads `_scratch/cache/{tag}/`. **225 IMU caches now exist, up from 109.**
> ➕ Reader: `rlog-tools/score/ratchet_in_the_imu_pooled.py`.

> ⚠⭐⭐⭐⭐ **THE IMU TEST IS UNDERPOWERED, NOT DECISIVE — BUT SPEED MATCHING IS VALIDATED, AND THE CORPUS'S ENGAGED/MANUAL CONFOUND IS NOW QUANTIFIED.**
>
> The comma's LSM6DS3TR-C is **physically independent of the EPS**, so it is the one instrument whose answer cannot be an artefact of EPS signal processing, a decode error, or torsion-bar scaling. Unmatched, it looked like a result:
> ```
>   UNMATCHED   13 segments   gyro excess 3.18   road control (az) 2.50   broadband ratio 20.2
> ```
> 🛑 **The broadband ratio of 20.2 is the tell: the arms differ in ROAD AND SPEED, not just engagement.** And the road control on vertical acceleration came back at **2.50** against the gyro's 3.18 — most of the “excess” was driving conditions.
> ✅ **SPEED MATCHING WORKS, AND THE VALIDATION IS THE BROADBAND COLLAPSE:**
> ```
>   MATCHED      3 segments   gyro excess 3.18   road control (az) 2.37   broadband ratio  2.73
> ```
> The confound drops **20.2 → 2.73**. But the sample collapses to **n = 3**, and gyro 3.18 against a road control of 2.37 is only **1.34×**. The `f0` estimates also scatter to the search-window edges (9.47 / 8.49 / 6.71) — the signature of taking the max of noise, not finding a peak.
> ⇒ **VERDICT: inconclusive and underpowered.** The IMU neither confirms nor refutes that the ratchet is real gross motion. **Resonance vs stick-slip stays open.**
>
> ⭐ **THE CORPUS FACT THIS PRODUCED, which bears on far more than this test:**
> ```
>   351 route caches inspected
>    64 have >= 20 s in BOTH arms
>    29 survive speed matching                 (45 %)
>   median segment retains 60 % of its smaller arm   (p10 0.05, p90 1.00)
> ```
> **The operator engages LKAS at speeds where he does not drive manually**, so every engaged-vs-manual claim in the record carries a speed confound. It is **not fatal** — 45 % of usable segments survive and the median keeps 60 % of its exposure — but it means the effective corpus for any engaged/manual contrast is **roughly half** what a raw segment count suggests. My own 13 → 3 collapse was worse than the corpus average only because the IMU caches cover different routes than the speed-matched set.
> ➕ **The actionable next step is now possible for the first time:** the `extract/` toolchain was revived last tick, so IMU caches can be built for the **29 speed-matched segments** that lack them — which is exactly what this test was short of.
> ➕ Readers: `rlog-tools/score/ratchet_in_the_imu.py` (speed matching built in).

> 🛑🛑⭐⭐⭐⭐⭐ **THE AUDIO CANNOT SEE THE RATCHET AT ALL — AND THE ENTIRE `extract/` TOOLCHAIN HAS BEEN DEAD SINCE THE 2026-08-26 REORG.**
>
> **1. THE HARMONICS TEST, DONE PROPERLY, FINDS NOTHING.** Re-extracted from the rlogs at **0.977 Hz bins** (vs the `_spec` caches' 3.91 Hz) with a per-window engagement flag, and replaced the contaminated comb with a **smooth broadband baseline** — so broadband engagement loudness is absorbed and only LOCAL excess survives:
> ```
>   route        f0 Hz    f0    2f0   3f0   4f0   5f0     (excess OVER the local baseline)
>   r97 (stock)   7.81   1.00  1.16  1.00  1.00  2.17
>   ra4           8.79   1.18  1.04  4.39  1.49  1.29
>   ra5           6.84   1.16  1.00  1.05  1.76  1.53
>   ra6           7.81   1.20  1.04  1.00  0.73  1.03
>   MEDIAN               1.17  1.04  1.03  1.24  1.41
> ```
> **NOTHING survives the baseline.** `f0` is **1.17×** — barely above nothing — and the harmonic columns are scattered noise (ra4's 4.39 and r97's 2.17 are isolated, not a comb). The f0 search lands on a **different frequency every route** (7.81 / 8.79 / 6.84 / 7.81), which is what happens when there is no peak to find.
> ⇒ **The 6.4× “excess” from the previous tick was broadband engagement loudness**, exactly what the contaminated control was hiding. **The audio does not resolve the ratchet as a spectral line.**
> 🛑 **THAT IS A NEGATIVE ABOUT THE INSTRUMENT, NOT THE MECHANISM.** Resonance-vs-stick-slip is **still open** — the audio simply cannot answer it, either because the ratchet is felt rather than radiated, or because road noise dominates it at 6–9 Hz. **This line of attack is closed.**
>
> **2. ⭐ AND THE REAL FIND: THE WHOLE `extract/` FAMILY WAS BROKEN.** Every extractor imports `rlog_parse` from `ROOT/"rlog-tools"`, but the **2026-08-26 reorg moved it to `rlog-tools/lib/`**. `CLAUDE.md` warns that `__file__`-relative anchors were re-based; **these were missed**, and nothing surfaced it because **the caches were already on disk** — the toolchain that MAKES caches was dead while every consumer kept working.
> ⇒ **51 files fixed**, each now putting the kit root *and every code subfolder* on the path. Two needed indentation-aware handling (the insert sits inside a block); a naive flat replacement broke them and the parse-check caught it before writing. **0 stale inserts remain outside gitignored `_scratch/`.**
> ⊕ Without this, no new route cache of any kind could be built. It is the reason this tick could run the test at all.
> ➕ Reader: `rlog-tools/score/ratchet_harmonics_fine.py`. New caches: `_audio_r{97,a4,a5,a6}.npz`.

> ⚠⭐⭐⭐⭐ **THE RATCHET-HARMONICS TEST IS INCONCLUSIVE, AND MY CONTROL WAS CONTAMINATED. NO MECHANISM CLAIM EITHER WAY.**
>
> The record calls the ratchet *“a lightly-damped RESONANCE, Q 14–29”*, and the whole arc has tried to add damping to it. A **stick-slip limit cycle** looks nearly identical in a ring-down but calls for the opposite fix — break the friction, not add damping — and **harmonics discriminate them**: a linear resonance radiates at `f0` only; a relaxation oscillation radiates at `2f0`, `3f0`, `4f0` too. The 16 kHz audio is the right instrument, since `3f0`/`4f0` land in the CAN band the record shows is folded.
> ```
>   engaged/manual power ratio, 13 routes, median
>     f0  (7.8 Hz)   6.439        3f0 (23.4 Hz)  1.958
>     2f0 (15.6 Hz)  5.272        4f0 (31.2 Hz)  2.599
>     control comb   3.790
> ```
> **The pattern is `f0 ≈ 2f0 >> 3f0 ≈ 4f0`.** A strong second harmonic with weak third and fourth is the signature of an **asymmetric / one-sided** nonlinearity rather than a symmetric stick-slip (which gives ODD harmonics, 3f and 5f). That would point at something like the Coulomb relay.
> 🛑 **BUT I CANNOT CLAIM IT, BECAUSE MY CONTROL IS NOT A CONTROL.** The comb sits at `1.5/2.5/3.5 × f0` = **11.7 / 19.5 / 27.3 Hz** — *inside* the bands the record already shows are engagement-elevated (grinding 15–22, pumping 22–30). It is not a neutral baseline, so it **inflates** and the harmonic ratios **understate**. Worse, **`2f0` = 15.6 Hz sits in the grinding band itself**, so the one piece of structure the test found — the second harmonic — **cannot be separated from the grinding.**
> ⇒ **VERDICT: the test does not discriminate.** It is consistent with a mild asymmetric nonlinearity and equally consistent with broadband engagement loudness plus grinding. **The record's “linear resonance” reading is neither confirmed nor overturned**, and nothing should be built on this tick's numbers.
> ➕ **What WOULD discriminate:** a control comb at frequencies the corpus shows are NOT engagement-elevated, and a fundamental resolved better than **3.91 Hz bins** — the `_spec` caches are too coarse to separate 7.79 from 7.8×2/2. Both are re-extractable from the rlogs; the extractor's own docstring promises 0.977 Hz bins, which these caches do not carry.
> ➕ Reader: `rlog-tools/score/ratchet_harmonics_audio.py` (the caveat is printed by the script, not just recorded here).

> ✅⭐⭐⭐⭐⭐ **V235's NOTCH PLACEMENT IS CLEARED — THE 22–30 Hz BAND IS REAL, NOT AN ALIAS. First time the kit has bounded the fold risk on the evidence that aims the notch.**
>
> The pump/damp table that puts V235's notch at 25 Hz was measured on **CAN at ~101 Hz**, so its *“22–30 Hz PUMPING”* row could have been **folded from 71.1–79.1 Hz** and the notch aimed at a ghost. The `_spec` caches are **16 kHz PCM, alias-free**, and cover **ra4/ra5/ra6 — the very routes the table was measured on**:
> ```
>   route      P(20-32)     P(69-81)    ratio
>   ra4       3.582e+05    1.443e+05     2.48   <- the pump/damp routes
>   ra5       3.345e+05    1.152e+05     2.90
>   ra6       3.839e+05    2.166e+05     1.77
>   median over 13 routes                2.34   (min 1.57, ALL > 1)
> ```
> ✅ **[EVIDENCE] Real 20–32 Hz energy dominates its alias source by ~2.3× on every route.** The band is genuinely there, so **the notch is aimed at something real and its placement stands.**
> ⚠ **THE HONEST QUALIFICATION: at a ratio of 2.34 the fold still supplies ~30 % of the CAN band power.** So the *sign* of the pump/damp row is sound; its *magnitude* carries a ~30 % contamination, and any number derived from that band's CAN magnitude should say so.
> ⊕ **A METHOD WORTH REUSING:** the kit's alias memory says the 30–49 Hz fold *“cannot be fixed after the fact”* — true for the CAN caches alone, but the **audio spectra bound it**, because they see both the band and its fold source separately. That is a general check for any CAN-derived band above ~20 Hz, and it had never been run.
> ⊕ A second empty-input null caught the same way as the last one: the `_spec` caches are **0–2000 Hz at 3.9 Hz bins**, not the 0–500 Hz at 0.977 Hz their extractor's docstring describes, so a `>=3 bins` filter emptied the table. **Check the row count before reading a null.**
> ➕ Reader: `rlog-tools/score/alias_bound_on_notch_band.py`.

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



## 📁 **EARLIER BLOCKS (22) ARCHIVED 2026-08-30**

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
