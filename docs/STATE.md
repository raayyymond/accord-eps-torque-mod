# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Below it are **83 blockquote blocks in reverse-chronological
> order** — findings, corrections and closures. That is a record, not a briefing. Everything you need
> to make a decision is in this box and the index under it.

## ✈ THE DECISION, IN ONE PLACE  — updated 2026-09-02 (V279)

**ON THE CAR: V276 (reference x6, oscillates at 3.9 Hz).  THE FLIGHT CANDIDATE, BY OPERATOR CHOICE: V279.
V278 (K=2 + damping tap) remains BUILT as the fallback.  V277 is WITHDRAWN.**

| | **V279** — PURE FEEDFORWARD: the rate PID opened into a linear torque map |
|---|---|
| base | **V268**, CAL-ONLY (the PID function `FUN_00028ea6` is byte-identical) |
| edits | `0xC62E6` 7680→0 (feedback operand forced to 0) · Kd→0 (28 rec) · map Y=2X (28 rec) · Kp flat 256 (28 rec) · packer `0x55DF0`–`0x55E11` = V278-rev-1 window (sel \| demand>>5 \| sign(E)) |
| surface | `P = 64·idx` exactly, 15360 at idx 240 = the P/sum clamps; delivered `= P×5346>>15` → **2505 at full demand, 6x stock's 417, UNCHANGED** |
| image | `dca2acbc9f805272eafea9a8cda2a57e1ca0de0dbf37ae0d19173ddb5f7871b5` |
| rwd | `6c104b5519a5a5f463842616535bedc3afc72385dcd1abb1daba1a3817c38b25` |
| assertions | **703/703** incl. end-state re-reads from the final image AND the decoded .rwd; independent rebuild reproduces; 85/99 mutations caught, the 3 misses closed |
| artifact | https://claude.ai/code/artifact/4696407c-e0ef-4c44-b1ee-698be51df141 |

**WHY THIS BUILD.** Honda's EPS maps openpilot's TORQUE request onto an ANGULAR-RATE SETPOINT and closes a PID on
measured column rate; openpilot's angle PID has been tuned against that hidden inner loop. Stock's P term rails at
|E| = 440 (±1.8 deg/s of rate error) — with the wheel still, stock delivers its full 417 at a command of ~113
counts (<3% of scale). **The rate loop is a bang-bang rate servo; to openpilot it has looked like an INTEGRATOR.**
V279 gives openpilot a linear torque-into-column plant — what its controller assumes. Cal-only: outside the
bricking class. Mechanism proven from bytes: the zero clamp forces r26=0 on all three branches (`0x28fa6`–`0x28fbc`),
`0xC62E6` has exactly 3 readers in the image (all in that block), D is a pure multiply, the LERPs hold flat beyond
their domains, the setpoint publish cell `gp-0x6a32` has ZERO readers.


🛑 **CORRECTION IN PROGRESS (2026-09-02): the operator runs `force_torque_controller` (LatControlTorque), NOT LatControlPID. The StarPilot paragraph below is VOID -- the multipliers are being re-derived for the torque controller; do not act on Kp 0.33 / 16.7 dB from this text.**
🛑 **THE STARPILOT RETUNE IS PART OF THIS BUILD.** ~~StarPilot runs `LatControlPID`~~ (angle PID) for the Accord;
the `,` in the part number sets `EPS_MODIFIED` and halves kpV/kiV (0.6→0.3, 0.18→0.09); the user multipliers scale
those only; **kf = 0.00006 is never scaled; there is NO friction term.** Effective today: kp 0.099, ki 0.0297.
Derived from HIS V276 log: column response 0.00056 deg/torque-count at −104° at 3.9 Hz, openpilot delay ~56 ms
(−79°) → **3.9 Hz is V279's phase crossover**; |L| there = 0.444 × Kp-multiplier.
**⇒ ENTER Kp 0.33, Ki 0.33 (Ki 0.5 acceptable). Never above Kp 1.0 (7 dB). Leave kf. Do NOT switch to the torque
controller.** 0.33 gives 16.7 dB gain margin at the mode — the same number as today, DERIVED, not inherited.
BELIEF: the low-frequency side (column stiffness known to ~2x from a hands-on log).

⚠ **RISK BEFORE THE DRIVE.** V276 rang when the EPS damping fraction fell to 0.57; V279 takes it to ZERO by
construction. Stability now rests on openpilot's tune and the column's mechanics. Watch, in order: a NEW slow
wallow at 1–2.5 Hz (Kp → 0.2); a return of 3.9 Hz with the tap reading 1.00 (Kp → 0.15); sluggish centering
(Ki → 0.5 first). First minute hands-LIGHT. Peak torque unchanged; taper byte-stock (grip escape unchanged).

**THE INSTRUMENT.** CAN 427: selector bits 3:0 (must read **7**), demand>>5 bits 7:5, `sign(E)` bit 9. With
feedback zeroed, `sign(E) == -sign(cmd)` on EVERY frame: **agreement 1.00 proves the feedback is dead**; ~0.5 means
it is not and nothing else from the drive can be trusted. Null sentence in `build_v279_tva.py`.

**V278, the fallback (built, `4bc51073…`):** reference x2, damping fraction 0.86 (stock 0.94, V276 0.57), damping
comparator tap. Fly it if V279's premise fails on the wire or the retune cannot hold the pure-FF plant.

🛑 **V273/V274/V275 ARE WITHDRAWN — DO NOT FLASH.** All three passed their own assertions and were
falsified by adversarial review. V274: froze torque CELLS and thought that froze TORQUE (the map scales
the ERROR feeding Kp → P saturated over ~80 % of range); its defending assertion was a tautology.
V275: divided Kp/Kd by 6, which cancels only the FEEDFORWARD half of `E = 32*sp - fb` and leaves the
FEEDBACK half 6x weaker — the loop keeps its ambition and goes deaf to the wheel. Both also flattened
the override taper, which is **UPSTREAM** (it produces the demand index) and whose companion hard cutoff
`0xC64B8`=255 is unsatisfiable — so the taper reaching Y=0 is the ONLY live mechanism that zeroes the
command, and the operator's median override torque sits ONE COUNT below its first knot.

🛑 **DO-NOT-FLASH:** V255–V262, V269 (rate-lane `sar` doubling; V255/V256/V269 drove **undriveable**),
and V273/V274/V275 above.


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

> ⭐⭐⭐⭐ **THE GAIN FINDING SURVIVES TWO CONTROLS — AND A “CLAMP-ONLY” ESCAPE FROM THE TRADE DOES NOT EXIST. THE MECHANISM STAYS OPEN, AND I AM NOT GOING TO INVENT ONE.**
>
> **1. 🛑 THE CLAMP IS NOT AN INDEPENDENT LEVER — the escape route I went looking for is closed.** V242's own docstring: **the clamp TRACKS the gain as `gain*512//891`.** So `clamp/gain` is identically **512** on every build, and the openpilot command at which the clamp binds is **512 counts regardless of gain**:
> ```
>   V90  4x  clamp 2048   sat thresh 512   saturated 44.3 %
>   V100 4x  clamp 2048   sat thresh 512   saturated 45.2 %
>   V102 6x  clamp 3072   sat thresh 512   saturated 13.5 %
>   V122 6x  clamp 3072   sat thresh 512   saturated 13.0 %
>   V101 8x  clamp 4096   sat thresh 512   saturated 40.3 %
> ```
> ⇒ gain and clamp are collinear **by construction, not by accident**, delivered torque scales with gain uniformly, and **a clamp-only build would be INERT.** There is no authority-without-ratchet hiding in the clamp.
> **2. ✅ AND THE SATURATION DUTY IS A CONTROL THAT STRENGTHENS THE FINDING.** If the anti-damping were driven by *how hard openpilot pushes*, the 4× builds would be worst — they saturate **44–45 %** of frames against 6×'s **13 %**. **They are the least anti-damped (−55 vs −68).** And within the 6× builds, duty (13.0–24.8 %) does not predict `Re(Z)` either, and what weak trend there is points the *other* way. ⇒ **the effect tracks the GAIN CELL, not command effort.**
> 🛑 **THE MECHANISM IS NOT ESTABLISHED, AND THE OBVIOUS STORY DOES NOT WORK.** The LKAS command lane is a **~1–5 Hz low-pass**, so the command cannot itself carry 7.8 Hz; and a uniform scaling of both torque and motion would leave `Re(Z) = Re(tq/rate)` *unchanged*, since it is a ratio. **So “more gain ⇒ more anti-damping” is a robust EMPIRICAL relation with an OPEN mechanism.** I am recording it that way rather than fitting a story to it — three stories died to their own controls in this session already.
> ⊕ **THE ONE UNTESTED WAY OUT, and its size is bounded.** V57 decoupled the forward reader onto `0xC6CD0`, leaving **four FEEDBACK readers on the shared `0xC646C` = 891 — stock, and never varied in the flown corpus.** The two live ones (`FUN_00036682`, `FUN_00036828`) compute `(raw sensor × gain) >> 15`, and at 7.8 Hz their IIR (`tp+0x73d2 = 14/1024`, fc ≈ 2.18 Hz) still passes ≈ **28 %** — into a **±512 clamp, 5 % of the aggregator's ±10240**. ⇒ lowering `0xC646C` is the only known way to cut feedback response **without touching forward authority**, but **it is capped at ~5 % of the aggregator, and the record already judges this path “probably NOT the 21 Hz driver”.** A candidate, not a plan — and it must be sized before it is built.
> ➕ **Nothing on the shelf moves. V241 remains the flight candidate.**

> ⭐⭐⭐⭐⭐ **2026-08-30 — THE RATE LANE'S REAL GAIN SURFACE, FOUND. BYTE-STOCK IN EVERY BUILD, AND
> ENGAGED-ONLY.** `FUN_0003ad74` builds the LERP that `FUN_0003aa2c` reads as the r24 lane's gain:
> ```
>   idx     = *(byte *)(gp + 0x63fd) * 4                      ; the MODE index
>   A/B/C/D = *(int *)({0xCBF5C, 0xCC044, 0xCC12C, 0xCC214} + idx)
>   blended on cal(0xC6010) = [0, 640, 3200, 6400]
>   -> X into gp-0x6e40.., Y into gp-0x6e38.., then interpolated on motor rate gp-0x6ac0
> ```
> **MODE 26 (ENGAGED)** — `0xD7A88` Y=[3072,3072,2322,1536] · `0xD7AC4` [2560,2560,2246,1946] ·
> `0xD7B00` [2303,2303,2151,1947] · `0xD7B3C` [2150,2150,2049,1947], all X=[0,400,1400/1500,3000].
> **MODE 24 (MANUAL)** is a disjoint set at `0xD6A9C`/`0xD6AD8`/`0xD6B14`/`0xD6B50`.
>
> 🛑 **THIS IS THE DOMINANT ARM.** The cal fallbacks (`0xC6440`=2048, `0xC6442`=1024) fire only when the
> `[0,5]` ramp saturates or `gp-0x671d != 0`, and `0xC6446` (Lever B) is unreachable. ⇒ **no calibration
> cell this kit has ever touched reaches this surface.**
>
> ⭐ **AND IT IS ENGAGED-ONLY, WHICH THE `sar` EDIT IS NOT.** V255/V262 edit the shift at
> `0x3AB76`/`0x3AC20` — in the **code path** — so they dose the rate lane in **manual steering too**.
> The operator's standing instruction is *"low apparent steering mass and friction to LKAS AND no
> ratcheting"*; a `sar` edit spends part of that budget on manual feel he never asked to change.
> ✅ Aliasing checked across all 64 indices of all four pointer arrays: each mode-26 table is referenced
> by index 26 **and no other**.
>
> ⊕ **WHERE GRINDING SITS ON THIS CURVE:** the record puts grind #1 at motor rate ~603 and grind #2 at
> ~1206, i.e. **on the `[400,1400]` rolloff**, where Y has already fallen 3072 → 2322. Flattening that
> rolloff is a further, more surgical lever — **but it is NOT built**, because the record warns Honda's
> rolloff there may be what prevents the parametric-pump mode V58/V59/V60 chased. Uniform scaling
> (V263) preserves the shape and does not touch that question.

> ⭐⭐⭐⭐⭐ **THE V112 SHELF — seven builds, all verified, all unflashed, nothing on the car.**
> ```
>   build  pay  gain  clamp  Kd  arms/surface        targets                    image sha[:12]
>   CAR      0  6.0x   3072  1x  stock               --                         f032878c4e0b
>   V255     2  6.0x   3072  2x  stock               grinding, 1 variable       32852708058b
>   V256     4  6.0x   4096  2x  stock               +authority DISAMBIGUATOR   f9cbb677ecd9
>   V258     6  4.0x   4096  2x  stock               all four, frontier         f4515c684b25
>   V259    15  4.0x   4096  2x  stock + damper      max ratchet (~31 %)        fc7e72aa2e66
>   V261     5  6.0x   3072  2x  cal arms x2         fallback branches only     d71b59cc56ae
>   V262     2  6.0x   3072  4x  stock               rate lane 4x, 1 variable   1be8018a88ba
>   V263    27  6.0x   3072  1x  SURFACE x2 ENGAGED  manual feel UNTOUCHED      1355326e10ad
> ```
> **RECOMMENDED ORDER: V263 or V255 → V256 → V258.** V263 if *"do not make the wheel heavier when I
> drive it myself"* is the binding constraint; V255 if the largest grinding effect is, since it is the
> only dose with flight history (V62/V65, fault-free, ST==4 zero over 86,278 frames). **V256 is the
> highest-information build** — it is the first ever to break the clamp/gain tracking.
> ⚠ V257 dropped from the ladder: it was the **worst** of the twelve winning (gain, clamp) configurations.
> ⚠ V260 **SUPERSEDED-DO-NOT-FLASH** — it dosed only one of the two rate lanes.

> 🛑🛑🛑⭐⭐⭐⭐⭐ **2026-08-30 — LEVER B IS UNREACHABLE. IT HAS NEVER DONE ANYTHING.**
> `FUN_0003aa2c` picks the r24 rate-lane arm before the multiply at `0x3AC18`:
> ```c
>   if (*(char *)(gp - 0x671d) == 0) {
>       if (*(char *)(gp - 0x683c) == 0) {          // ALWAYS TRUE -- zero writers
>           if (!(gp-0x671a < cal_byte(0xC64FA)))   // the [0,5] ramp vs 5
>               r10 = cal(0xC6440);                 // 2048   <- LIVE
>           // else: the runtime LERP on motor rate  <- LIVE, and the DOMINANT path
>       } else {
>           r10 = cal(0xC6446);                     // 5244   <- LEVER B, DEAD CODE
>       }
>   } else {
>       r10 = cal(0xC6442);                         // 1024   <- LIVE
>   }
> ```
> **`gp-0x683c` has ZERO writers**, so `bVar4` is permanently true and the Lever B arm is never selected.
> The record carried this as *"single-method, wants a raw byte scan"* — **the scan was never run.** It has
> now been confirmed **two independent ways**: (1) the decompile of `FUN_00052e32`, which writes the whole
> neighbourhood (`-0x683b`, `-0x683d`, `-0x683e`, `-0x6832`…`-0x6835`) and **never `-0x683c`**; (2) a
> **corrected** byte-form scan — 🛑 for byte forms the displacement's bit 0 lives in **`hw1` bit 5**, so the
> opcode is bits **6–10**, and decoding it as 5–10 conflates odd/even displacements. A naive scan reports
> 14 "sites"; the control (`gp-0x683b`, demonstrably written) has opcode set `{0x1E}`, and every `0x1E`
> site at "`-0x683c`" matches only the halfword form ⇒ its real displacement is `-0x683b`.
>
> ⇒ 🛑 **EVERY LEVER B RESULT IN THIS KIT IS OF A DEAD CELL.** Voided: the anti-damping census collapses
> to **the GAIN ALONE**; *"Lever B moves the ratchet without spending authority"*; **V88's "bracketed
> optimum" of 5244**; the `_LEVER_B_LADDER` registry; and the two Lever B rows of the calibration-ceiling
> table (5.81 + 2.90 units). **The calibration ceiling is LOWER than stated, and only one cell was ever
> really tracking the ratchet.**
>
> ⚠ **AND THE SELECTOR THRESHOLD IS A BYTE**: `cal_byte(0xC64FA)` = **5**, not the 517 a halfword read
> gives. Wrong-width read, same family as the off-by-0x1000 trap.
>
> **THE LIVE ARMS, none ever moved from stock in any build:** `0xC6442` = 1024 · `0xC6440` = 2048 ·
> `0xC643E` = 1536 (sibling lane) · and a **runtime LERP on motor rate that NO calibration cell can reach.**
>
> ✅ **THIS MAKES V255 BETTER.** The `sar` edit sits **after** the multiply, so it doubles whichever arm is
> live — including that LERP branch. And V255's saturation caveat is **VOID**: it was computed against the
> dead 5244. At the live arms (1024–2048) the doubled lane clips at input **2048–4096** against a measured
> p50 of **859** — no saturation where the symptoms live.
> ⇒ **The rate lane has not actually been dosed since V65**: Lever B was dead, and the `sar` was reverted.
> **V255 is the first real dose of this lane in ~200 builds.**

> 🛑🛑🛑⭐⭐⭐⭐⭐ **2026-08-30 — THE KIT'S ONLY MEASURED GRINDING FIX HAS NOT BEEN ON THE CAR SINCE V65.**
> V62 (`sar 0xa`→`sar 0x9` at **`0x3AB76`** and **`0x3AC20`**) measured **18–22 Hz down 8×** (42× at
> |rate| 16–32 °/s) against a flat 30–40 Hz control, and the operator said *"Original grinding at 2–5 mph
> is gone!"* Read from the **images**, not the record:
> ```
>   stock                      aa32  aa42   1x Kd
>   V62 / V65                  a932  a942   2x Kd   <- the fix
>   V70                        aa32  aa42   REVERTED
>   V88 V100 V108 V111 V112    aa32  aa42   1x Kd   <- V112 is the car
>   V131 V139                  a932  a942   2x Kd   <- restored again
>   V122 V241 V251 V254        aa32  aa42   1x Kd   <- lost again; the whole old shelf
> ```
> `BUILD-LINEAGE-PART1` says *"Restored in V71"*. **The images say it was added and dropped TWICE.**
> A mechanical audit of every flown image vs V112 confirms this is the **only genuine instance** — the car
> also lacks the notch relocation, FactorC/E and the `0xC646C` decoupling, but those were never *lost*:
> **V112 simply predates ~140 builds of work.**
>
> **MECHANISM.** The grinding mode is a lightly-damped **MECHANICAL** resonance — 21.4 Hz, **Q = 13.6**,
> ~0.23 s coherence — not a digital limit cycle. Its `phi'` coefficient is **positive and LINEAR in Kd**,
> and at Kd = 0 the mode has **no damping term at all**. The rate lane IS that Kd. Engaged vs disengaged
> at matched speed, hands-off: **9,200× more 21 Hz power engaged**, while the disengaged pool carries 6×
> MORE low-frequency energy — so the loop closes **through the physics**, not through firmware.
>
> ⭐ **AND A DERIVATIVE IS NOT THE FRICTION THE OPERATOR RULED OUT** — it scales with frequency, so at
> 1 Hz it delivers **4.7 %** of its 21.4 Hz output (3 Hz → 14 %, the ratchet 7.8 Hz → 36 %). It acts where
> motion is fast and is nearly absent where he steers. The dangerous form is the **Coulomb relay**
> (`4M/πa` → ∞ as amplitude → 0), which is what made V80 the worst grinding ever produced.

> 🛑🛑⭐⭐⭐⭐⭐ **THE GAIN→RATCHET SLOPE IS ~−6.6 PER 1×, NOT −4.4 — AND IT IS CONFOUNDED WITH THE CLAMP.**
> Coherence-gated 6–9 Hz `Re(Z)` over **16 flown builds**, gain read from the images:
> ```
>   gain    n    median Re(Z)    range              4x -> 6x  =  -6.6 per 1x
>   4.0x    6       -55.37       -46.6 .. -66.8     6x -> 8x  =  -7.8 per 1x
>   6.0x    9       -68.49       -62.3 .. -74.9   <- V112, the car
>   8.0x    1       -84.06
> ```
> ⇒ 6× → 4× is worth **~13 units, 20 % of the 65-unit requirement, from one cell.**
> 🛑🛑 **BUT `clamp = gain × 512 // 891` HELD EXACTLY ON ALL SIXTEEN** (4x→2048, 6x→3072, 8x→4096).
> **Gain and clamp are PERFECTLY COLLINEAR in the whole flown corpus** — nothing distinguishes *"lower
> gain helps"* from *"lower clamp helps"*, and they predict **opposite** outcomes for every shelf build,
> since all of them raise the clamp.
> ⇒ ⭐ **V256 IS THE DISAMBIGUATING EXPERIMENT** — clamp alone, gain held at the car's 6×, which no build
> has done in 16 flights. Readers: `rlog-tools/score/gain_clamp_collinearity.py`, `gain_clamp_plane.py`.
> ⊕ **The `0xC674E` abort rule stays UNFOUNDED** (settled 2026-08-27); the 5119 cap in the plane tool is
> conservatism, now labelled as such. **Leave the mirrored INT/FLOAT quad alone — that is the V27 class.**

> ⭐⭐⭐⭐⭐ **THE V112-BASED LADDER — BUILT, VERIFIED, UNFLASHED 2026-08-30.** All on the **V112** base
> (what the operator says is on the car), every payload byte attributed, MANUAL damper records asserted
> byte-identical in all five, V27 quad asserted in sync and untouched, all reproduce bit-for-bit.
> ```
>   build  pay  gain  clamp  rate  damper   targets                image sha256[:16]
>   CAR      0  6.0x   3072    1x   stock   --                     f032878c4e0b8e90
>   V255     2  6.0x   3072    2x   stock   grinding, 1 variable   32852708058ba3e7
>   V256     4  6.0x   4096    2x   stock   + authority  ** THE DISAMBIGUATOR **  f9cbb677ecd98757
>   V257     6  5.0x   4096    2x   stock   all four, mild         d43ab1a1a73a8da5
>   V258     6  4.0x   4096    2x   stock   all four, frontier     f4515c684b25d3e3
>   V259    15  4.0x   4096    2x    OPEN   maximum ratchet        fc7e72aa2e66584a
> ```
> **V258's cells all sit at previously-FLOWN values** (gain 3564 flew V38–V100, clamp 4096 flew as V101,
> the two `sar` bytes flew as V62/V65) — **only the combination is new.**
> **RECOMMENDED ORDER: V255 → V256 → V258.** V257 is dominated (it was the worst of the twelve winning
> configurations); V259 moves five levers and is for after the direction is known.
> 🛑 A broken check was found and fixed: both V257/V258 inherited a peak-torque assertion with a hardcoded
> stale command value — it **FAILED in V258 and PASSED IN V257 FOR THE WRONG REASON** (reporting 3415
> instead of 4096). The *"a check that looks right and is not"* class.

> 🛑🛑🛑 **UNRESOLVED: WHICH BUILD IS ON THE CAR. THE OPERATOR SAYS V112; THIS FILE SAYS V122.**
> Raised by the operator 2026-08-30: *"last on car is V112"*. This file (below) says *"Confirmed V122 is
> the last flown (route r24)"*. **Both cannot be right, and every "vs the car" number computed in the
> 2026-08-27 → 2026-08-30 sessions used V122 as the baseline.**
>
> **THE ENTIRE DIFFERENCE IS THREE CELLS + the CAL CRC**, read from the two images over `[0x13000,0x100000)`:
> ```
>   cell        what it is                        V112     V122
>   0xC40BC     Coulomb-relay knee                1800     3000
>   0xC40D2     K1                                 612     1020
>   0xC40DC     alpha2 (HF filter coefficient)      14        8
> ```
> ⚠ **CONSEQUENCE FOR THE V253 RATIONALE:** V253 was cut on 2026-08-29 specifically to hold `alpha2` at
> **8**, on the argument that *the car has 8* and V122's own name is `ALPHA2.8-BEST`. **If the car is V112
> the car runs alpha2 = 14, and that argument collapses** — V253 would be aimed at a value the operator
> may never have driven. **Do not fly V253 on the "match the car" rationale until this is settled.**
>
> ✅ **WHAT IS UNAFFECTED:** none of these three cells is in the gain, clamp, damper or notch lanes, so the
> gain/clamp arithmetic behind V251/V252/V254 and the damper sizing are unchanged in kind. What shifts is
> only the baseline image the deltas were measured against.
>
> ⇒ **HOW TO SETTLE IT:** re-flashing a known file makes the question disappear. Absent that, a UDS read of
> any one of the three cells settles it — **gated: needs the operator's explicit payload confirmation.**

> 🛑🛑🛑⭐⭐⭐⭐⭐ **THE DEFINITIVE ANSWER TO “ELIMINATE ALL RATCHETING”: CALIBRATION CANNOT. Every lane is now measured, and the arithmetic does not reach.**
>
> Requirement to CANCEL: **65 counts per deg/s** of damping. Every lever at its measured maximum:
> ```
>   lever                                            units    of the 65
>   damper lane, flat out                            18.87       29.0 %
>   gain 6x -> 0x  (removes LKAS entirely)           26.40       40.6 %
>   Lever B 512 -> 5244  (ALREADY on the car)         5.81        8.9 %
>   Lever B 5244 -> 7866 (V246)                       2.90        4.5 %
>   gp-0x6bbe at its rail                             0.52        0.8 %
>   resonance PID D term                              0.00        0.0 %   (closed: bad trade)
>   -----------------------------------------------------------------
>   SUM OF EVERYTHING, including removing LKAS       54.50       83.8 %
>
>   PRACTICAL ceiling, LKAS still usable:            26.2         40 %
> ```
> 🛑 **EVEN REMOVING LKAS TORQUE ALTOGETHER, CALIBRATION REACHES 84 %. WITH THE SYSTEM STILL FUNCTIONAL, ~40 %.** This is not a shortfall in effort — the cal surface has been censused twice (an FDR regression over every cell that ever varied, and a mechanical starved-lane sweep over every LERP), and every lane is priced. **The ratchet is not calibration-eliminable.**
> ⇒ **WHAT WOULD REACH IT IS A CODE CAVE** — adding a damping term that does not exist in stock firmware. **That is this kit's only bricking class: V24, V27 and V48B all bricked the ECU**, and this is the operator's daily driver. **Not proposed, and not to be built without an explicit instruction with that risk stated.**
> ✅ **WHAT IS ACHIEVABLE AND ALREADY BUILT: V254 captures ~15 % of the ratchet while DELIVERING 7 % more mean torque and 33 % more peak** — because the clamp, not the gain, sets delivered torque. Pushing to the full 40 % means the damper flat out, at ~15 % of authority.
> ⇒ **This closes the ratchet as a calibration problem.** Grinding and peak command oscillation are different: the notch treats one, and V251/V254's clamp measurably treats the other.

> ⭐⭐⭐⭐⭐ **V254 — THE ONLY CONFIGURATION STRICTLY BETTER THAN THE CAR ON ALL THREE SYMPTOMS AT ONCE. AND IT GETS THERE BY *LOWERING* THE GAIN.**
>
> The operator asks for more torque and less ratchet, and the gain relation says those conflict. **But peak delivered torque is set by the CLAMP, not the gain** — `delivered = min(cmd·gain/891, clamp)`. So lowering the gain while raising the clamp:
> ```
>   loses torque per unit of command          (bad)
>   raises the ceiling it is clipped at        (good -- and it repays more than the loss)
>   reduces the anti-damping                   (good)
>   raises the command at which the loop rails (good -- less peak command oscillation)
> ```
> **Three of four point the same way, and the fourth is outweighed.** Measured over **1,691,012 engaged frames** of real openpilot command, every row on one corpus:
> ```
>   configuration      gain  clamp  rail duty  mean deliv   Re(Z)        vs the car
>   V122 (the car)     6.0x   3072     30.2 %      1688     -64.8            --
>   V251 (clamp only)  6.0x   4096     24.9 %      1968     -64.8    +17 % tq /  0.0
>   V252 (8x)          8.0x   4096     30.2 %      2251     -73.6    +33 % tq / -8.8
>   V254 (this)        5.0x   4096     22.3 %      1801     -54.9     +7 % tq / +9.9
> ```
> ✅ **[EVIDENCE] V254 IS THE ONLY ROW THAT BEATS THE CAR ON TORQUE *AND* RATCHET *AND* RAIL DUTY SIMULTANEOUSLY.** `0xC61B2/B4` 3072→4096 and `0xC6CD0` 5346→4455, on top of V241's notch and the full damper — **4 payload bytes.**
> ```
>   +7 %  mean delivered torque     the clamp ceiling rises 3072 -> 4096
>   +33 % PEAK delivered torque     the clamp IS the peak
>   -26 % rail duty  30.2 -> 22.3   the loop is open less often
>   +9.9  Re(Z)  -64.8 -> -54.9     15 % of the 65 needed: +4.4 gain, +5.5 damper
> ```
> 🛑 **THE HONEST WEAKNESS: “5×” READS LIKE LESS TORQUE.** *Delivered* torque goes UP, but if the operator judges the car by feel at a given steering input rather than by lane-holding, a lower gain may feel **softer below the rail** even with the mean and peak both higher. **That is a feel question only a drive settles.** **V251** (clamp only, gain untouched) is the conservative alternative: +17 % torque, no gain change, no ratchet benefit.
> ⚠ And the gain→ratchet slope is **confounded with era** — one era-free contrast supports it, not a controlled experiment. If it is wrong, V254 keeps its torque and rail gains and loses only the +4.4.
> ⇒ **1844 checks passed, 59/59 bit-exact.** image `80d11a28e5e73a35…` · rwd `1e336dfbdda6b23f…`

> ⚖⭐⭐⭐⭐⭐ **THE DAMPER TRADE, FULLY PRICED — AND IT ARGUES AGAINST A MAXIMAL BUILD. V250 IS THE SENSIBLE CEILING.**
>
> Correcting my own correction: *“cannot cancel the ratchet”* is too pessimistic as a verdict. The ratchet is a **limit cycle bounded by nonlinearity**, so reducing net anti-damping does not have to reach zero to move the amplitude balance. The right question is the **trade**, and both sides are computable — damping uses the curve's **slope**, authority cost uses its **magnitude**:
> ```
>   config          c vs req     damper torque taken from openpilot
>                                p50      p90      p99
>   V122 (car)          1.3 %      0       20      146
>   V249                4.2 %      0       67      388
>   V250                8.4 %      0      133      512
>   MAX E+B+D          29.0 %      0      459      512
> ```
> 🛑 **AT THE MAXIMUM THE DAMPER TAKES 459 COUNTS AT p90 STEERING RATE — 15 % OF THE 3072 CLAMP — and rails at p99.** The benefit:cost ratio is roughly **2:1 and LINEAR**, so there is no sweet spot to find: 29 % of the ratchet costs 15 % of the authority the operator asked to *increase*. **The maximal build is not worth proposing.**
> ✅ **AND ONE GOOD STRUCTURAL DETAIL FALLS OUT.** At the **median** engaged steering rate (1.77 °/s = 8.3 counts) the damper is **OFF in every configuration**, because `FactorE X[0]` sits at **12 counts**. So it costs nothing in quiet driving and engages only during active steering — including ratchet bursts, whose operating point is 99 counts. **That is the right shape**, and it vindicates the record's deliberate choice of `X[0] = 12` over 6.
> ⇒ **V250 (8.4 % for 4.3 % authority) is the ceiling worth flying**, and it is already built. **V249 (4.2 % for 2.2 %) remains the first step.**

> 🛑🛑🛑⭐⭐⭐⭐⭐ **RETRACTION, AND IT IS THE BIG ONE: THE DAMPER SUPPLIES ~4 % OF THE REQUIREMENT, NOT 90 %. I COMPARED THE WRONG QUANTITY, AND EVEN AT ITS CEILING THIS LANE CANNOT CANCEL THE RATCHET.**
>
> **The error.** I priced the damper by its output MAGNITUDE — 50 counts against a ~56-count requirement — and called it 89 %. **For a small oscillation riding on a larger steady rate the damping coefficient is the curve's SLOPE, not its value.** `T = −sign(rate)·M(|rate|)`, so with `rate = R₀ + δ·sin` and `R₀ ≫ δ` the oscillating part is `−M′(R₀)·δ`. **I used `M` where `M′` belongs, and was wrong by ~20×.**
> **Which regime applies is measurable, and I measured it** rather than assuming:
> ```
>   slow |rate| (<3 Hz)   p50 1.65 deg/s
>   6-9 Hz amplitude      p50 0.72 deg/s      ratio p50 0.35, p90 0.96
>   the rate sign reverses in only 9.4 % of engaged windows  =>  SLOPE REGIME
> ```
> ⭐ Units, from the record: `gp-0x6ac0 = 4.71210813 counts per deg/s`, so the damper's operating point of 99 counts is **21 °/s** — while the ratchet's own 6–9 Hz amplitude is **0.72 °/s**. The oscillation is a small ripple on a much larger motion, and the sign almost never flips.
> ```
>   c = seed·(B/1024)(C/1024)(D/1024)·(dE/drate)/1024 · 4.7121      [counts per deg/s]
>
>                                     c        vs requirement 65
>   V122 (the car)                 0.813             1.3 %
>   V247 / V249                    2.742             4.2 %
>   V250                           5.485             8.4 %
>   + FactorD x2 as well          10.970            16.9 %
>   MAX: steepest legal E, B+D x2 18.866            29.0 %
> ```
> 🛑🛑 **EVEN AT ITS CEILING THE DAMPER LANE REACHES 29 %. IT CANNOT CANCEL THE RATCHET.** Every *“50 counts against a ~56-count requirement”*, *“89 % / 179 %”* and *“V249 nearly cancels it”* elsewhere in this file, the handoff, the memories and the build docstrings **is wrong and is superseded by this block.**
> ⇒ **WHAT SURVIVES.** V249 is still **directionally right and the largest the lane offers at a sane dose — 3.4× the car's damping** — and it is engaged-only, cal-only and cheap. **But the operator must not expect the ratchet to disappear.** It is a few-percent improvement, not a fix.
> 🛑 **AND THE SEARCH REOPENS.** If the damper cannot do it and the cal census found nothing else, then **the ratchet may not be calibration-reachable at all** — which is where the arc stood before the damper was found. The damper was a real discovery (a lane structurally switched off); it is simply **not big enough**.
> ✅ **The pre-registered prediction is REPLACED:** `Re(Z)` should move from **−64.8 to about −62**, not to −6.8. If the operator reports the ratchet unchanged on V249, **that is the predicted outcome**, not a falsification of the damper direction.
> ➕ Readers: `v249_predicted_effect.py` (🛑 carries the SUPERSEDED magnitude form) and the regime measurement that corrected it.

> 🛑🛑⭐⭐⭐⭐⭐ **THE PRE-REGISTERED PREDICTION FOR V249 — WRITTEN BEFORE THE DRIVE, SO A NULL IS READABLE INSTEAD OF “UNINTERPRETABLE”.**
>
> The design law: *“before cutting, write the sentence a null will license.”* V249 goes after a symptom sixty builds have failed to move, so the drive is only worth what was said in advance.
> ```
>   measured 6-9.5 Hz torque amplitude   50 counts (p50, 7,603 engaged windows)
>   damper on the car (V122)              2.9 counts   <- weighted by the REAL speed mix
>   damper on V249                       47.8 counts
>   V249 adds 44.9 counts against 50     =  89.5 %
>
>   PREDICTION:  Re(Z) at 6-9 Hz moves from -64.8 TOWARD ZERO, to roughly -6.8
> ```
> ✅ **AND AN INDEPENDENT CONSISTENCY CHECK FALLS OUT.** The band torque amplitude measures **50 counts**; the requirement derived earlier by a completely different route — `Re(Z) × the 0.86 °/s rate amplitude` — was **~56 counts**. **Two methods, same number.** That is the first time the requirement has been corroborated rather than just computed.
> ⊕ **The car's damper delivers 2.9 counts mean** once weighted by where the operator actually drives, because **34 % of engaged windows sit below the FactorC knee where it is exactly zero.**
> **THE DECISION RULE, ON THE RECORD:**
> | outcome | what it licenses |
> |---|---|
> | `Re(Z)` moves toward zero by roughly this | mechanism right, dose calibrated. **V250** is the margin step if more is wanted |
> | unchanged | the damper does **not** reach the loop the ratchet lives in ⇒ **RULES OUT the damper lane by experiment**, which sixty builds of inference never could |
> | more negative | the sign argument is inverted somewhere ⇒ **REVERT V249 immediately** |
> 🛑 **FIRST-ORDER, NOT A SIMULATION.** It assumes the damper torque enters the same summing junction the impedance is measured across, and that the plant is linear over the increment — the standard small-signal assumptions used throughout this arc. **Read the SIGN and the ORDER, not the decimal.**
> ➕ Reader: `rlog-tools/score/v249_predicted_effect.py`.

> ⭐⭐⭐⭐⭐ **V253 BUILT — V241 WITH THE OPERATOR'S OWN ALPHA2 KEPT. AGAINST THE CAR, THE NOTCH IS NOW THE ONLY CONTROL CHANGE.**
>
> He asked what V241 changes against the car, and the answer surfaced that V241 **reverts a cell his own build name calls BEST** (`V122 = KNEE3000.K1.1020-ALPHA2.8-BEST`). Rather than leave that as a question, the one-byte variant is built:
> ```
>   V253 vs V122 (the car): 22 bytes in 7 runs
>     0xC60A8-B6   12 B   the NOTCH             <- the ONLY control change
>     0x55DF2       2 B   CAN 427 telemetry source -- no control path
>     2 CRC trailers      derived
>
>   alpha2 0xC40DC:   car 8    V253 8    V241 22
> ```
> ✅ **THE STANDING RULE DECIDED THIS, NOT THE STATISTICS.** *“The operator's lived experience overrides analyst recommendations.”* The corpus leans toward 22 (−62.87 across 14 builds vs −70.13 at 8) but it is **n=1 at his value, p 0.136, and confounded with era** — alpha2 went 22→14→8 exactly as the gain went 4×→6×. **A confounded n=1 contrast is not grounds to silently undo a choice he named BEST.**
> ⭐ **AND IT BUYS A BETTER EXPERIMENT REGARDLESS.** With alpha2 held, the notch is the sole control delta from the car — so if the drive changes anything, **the notch did it**, and there is no second cell to argue about afterwards.
> ⇒ **WHICH TO FLY:** no feel-preference on alpha2 → **V241** is fine and its value is marginally better supported. Chose 8 deliberately → **V253**. One byte apart; either reverts to the other in a single flash. image `c9b127b1e851c9ee…` · rwd `b5a41b7b1da0625d…`
> ⇒ **1803 checks passed, 58/58 bit-exact.**

> ⚠⭐⭐⭐⭐ **OPERATOR QUESTION ANSWERED: V241 vs THE CAR IS ONLY 23 BYTES — AND ONE OF THEM REVERTS A CELL THE CAR'S OWN BUILD NAME CALLS “BEST”.**
>
> Confirmed **V122 is the last flown** (route r24); **V112 came earlier in the same lineage** and V122 superseded it. Diffing V241 against V122 over `[0x13000,0x100000)`:
> ```
>   biquad, 4 runs, 12 B    THE NOTCH re-aimed to 29.75/22.50/0.940   <- the intended change
>   0xC40DC   8 -> 22       alpha2, reverted to Honda's value
>   0x55DF2                 CAN 427 TX packer source -- TELEMETRY, not a control path
>   2 CRC trailers          derived
> ```
> ⇒ **V241 is essentially “the car + a re-aimed notch + alpha2 reverted”.**
> 🛑 **THE ALPHA2 REVERT IS WORTH FLAGGING: V122's own name is `ALPHA2.8-BEST`.** V115 took it 14 → 8 and V122 carried it. V241's lineage restored Honda's 22. Across the flown corpus:
> ```
>   alpha2  8   n=1    Re(Z) -70.13   <- the car
>   alpha2 14   n=2    Re(Z) -69.53
>   alpha2 22   n=14   Re(Z) -62.87   <- V241
>                      rho +0.376, p 0.136
> ```
> The direction **weakly favours 22** (less anti-damping), so V241's value looks slightly better rather than worse — **but n=1 at the car's value, p 0.136, and CONFOUNDED WITH ERA**: alpha2 went 22 → 14 → 8 as the gain went 4× → 6×, so the trend may be the gain effect in disguise. **The corpus cannot separate them.**
> ⇒ **If the operator chose 8 because the car FELT better, that outranks this** — his lived experience beats a confounded n=1 contrast, per the standing rule. **A one-byte V241 variant holding alpha2 at 8 is available on request**, and would make the notch the ONLY change from the car, which is a cleaner experiment regardless.

> ✅⭐⭐⭐⭐⭐ **THE PID DERIVATIVE'S SIGN IS DETERMINATE AFTER ALL — AND IT SAYS DO NOT BUILD THE CUT. THE LAST OPEN LEVER IS CLOSED.**
>
> I recorded the D term as *“sized but sign unknown”*. **The sign is computable, not unknowable.** The PID's error is torque-derived, so the D term injects a torque proportional to `d(tq)/dt`, which **leads `tq` by exactly 90°**. Damping is torque antiphase with rate (180°); pumping is in phase (0°). So the D contribution sits at **`arg(Z) + 90°`** — and `arg(Z)` is measurable on the same non-rectified instruments:
> ```
>   ratchet  6-9.5 Hz   arg(Z) -151.1 deg   D at  -61.1 deg   damping fraction -0.483  -> PUMPS
>   grinding 22-30 Hz   arg(Z)  +21.6 deg   D at +111.6 deg   damping fraction +0.367  -> DAMPS
> ```
> 🛑 **THE D TERM PUMPS AT THE RATCHET AND DAMPS AT THE GRINDING BAND.** Cutting it trades one symptom for the other — **and the trade is bad**, because the D term is **0.43× the P term at 8.5 Hz but 1.26× at 25 Hz**: cutting removes considerably more damping from grinding than it removes pumping from the ratchet.
> ⇒ **CANDIDATE CLOSED. Do not cut `0xC6AE6` or move `0xC644A`.** That is worth more than another speculative build, and it explains V43's null (`0xC644A` 1024 → 64) as a real result rather than a mis-scored one: the two effects partly cancel.
> ✅ **AND THE PHASES CHECK OUT INTERNALLY** — an independent consistency test of the whole measurement stack: `cos(−151.1°) = −0.87` gives a **negative** Re(Z) at the ratchet, and `cos(+21.6°) = +0.93` gives a **positive** Re(Z) at 22–30 Hz. Both match the Re(Z) values measured separately, by a different estimator, earlier in the session.
> ⚖ **[BELIEF]** the sign rests on the standard small-signal argument — that the plant seen by the injected torque is the plant `Z` describes. It is the same argument that settled the damper's sign, but it is a model step, not a direct measurement of the D term.
> ➕ Reader: `rlog-tools/score/pid_derivative_sign.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **THE RESONANCE PID RUNS A RAW DERIVATIVE WITH D GAIN 8× ITS P GAIN, BYTE-STOCK IN ALL 18 FLOWN BUILDS. THE LAST STRUCTURALLY SUSPICIOUS THING IN THE CHAIN — SIZED, BUT ITS SIGN IS NOT KNOWN.**
>
> Decompiling `FUN_0003a382` (the lane the record calls *“never scored at 6–9 Hz”*):
> ```
>   P gain  0xC6B26  [256, 256, 225, 153]   at rate 99:  256   (Q10 0.25)
>   I gain  0xC6B12  [ 98,  98,  98,  98]   at rate 99:   98   (Q10 0.096)
>   D gain  0xC6AE6  [2048, 2048, 2048, 2048] at rate 99: 2048 (Q10 2.0)   <- 8x the P gain
>
>   derivative pole 0xC644A = 1024 on ALL 18 flown builds
> ```
> ⭐ **AND IT CORRECTS THE GOLDEN MODEL.** The model calls this an *“UNFILTERED residual lane (2 passthroughs + a raw derivative)”*. **There IS a pole** — an IIR at `tp+0x744a` — but it reads **1024**, and `state += (x−state)*1024>>10 == x` is a **passthrough**. So the derivative is raw **by cal value, not by structure.** That distinction matters: **there is a pole to move.**
> ```
>   a raw one-sample difference has gain proportional to frequency:
>     D/P share   at 8.5 Hz: 0.43      at 25 Hz: 1.26   <- D DOMINATES in the grinding band
> ```
> 🛑 **ALL THREE PID GAINS ARE BYTE-STOCK ACROSS ALL 18 FLOWN BUILDS** — the same census blind spot that hid the damper. And the record's own note stands: *“V56's mute of this lane was scored at ~21 Hz — the lane has NEVER been scored at 6–9 Hz.”*
> ⚠ **I AM NOT BUILDING THIS, AND THE REASON IS THE SIGN.** I can size the term but **not its direction**: a derivative adds +90° of phase, so reducing D could damp the loop or destabilise it depending on the rest of the loop's phase — this is the *“OPEN lever, may PUMP”* situation the record warns about. **V43 already tried the pole** (`0xC644A` 1024 → 64) and got a **null**, but that was scored at ~21 Hz, so it does not settle 6–9 Hz either.
> ⇒ **TOP CANDIDATE FOR THE NEXT SESSION, and the honest reason to stop here: the shelf already holds six unflown builds.** A seventh whose direction is a guess would spend a drive to learn less than V249 will.

> ✅⭐⭐⭐⭐⭐ **THE 6–10 Hz NOTCH QUESTION IS CLOSED — AND NOT THE WAY EITHER SIDE EXPECTED. THE LANE THE DAMPING FLOOR GATES HAS TOO LITTLE AUTHORITY AT 6–9 Hz FOR ANY AIMING TO MATTER.**
>
> The notch is forbidden from 6–10 Hz by the **damping-band floor**, justified by a lane phase of `cos −0.918/−0.989/−0.629` — **taken from the rectified 427 channel**, which cannot carry phase. Meanwhile the system measures **anti-damped** there on non-rectified instruments. So the floor might be protecting nothing, and it blocks the kit's strongest device.
> 🛑 **THE DIRECT TEST CANNOT RUN — AND THAT IS ITSELF THE FINDING.** `|H|@7.79 Hz` is **0.9829 on fourteen flown builds and 0.9863 on three**: **no flown build has ever cut 6–9 Hz.** The regression returns rho +0.026, p 0.92 — an absence of *contrast*, not evidence. **The floor has never been tested against a trusted instrument.**
> ⭐ **BUT ONE ROW CARRIES THE ANSWER ANYWAY.** V104 ran **`c4 × 1.85`** — and `c4` is a **pure flat scalar**, so that is an **85 % dose on the ENTIRE notch lane**:
> ```
>   corpus Re(Z) at 6-9 Hz :  median -64.77   sd 9.07   range -84.06 .. -46.61   n=17
>   V104  (lane x1.85)     :         -64.77   z = +0.00   -- the 47th percentile
>   V105  (lane back to 1x):         -67.78   z = -0.33
> ```
> ✅ **[EVIDENCE] AN 85 % DOSE ON THE WHOLE LANE MOVED THE SYSTEM ANTI-DAMPING BY 0.00 sd.** The lane is **not a meaningful contributor at 6–9 Hz, in either direction** — so cutting there would be as invisible as amplifying there was.
> ⇒ **THIS EXPLAINS WHAT THE ARC NEVER RESOLVED.** The notch could never reach the ratchet — not because it was mis-aimed, and not because a gate blocked it, but because **the lane does not act there at all.** And it independently corroborates the damper as the right target: **the damper delivers ~50 counts at that frequency where the notch lane delivers nothing measurable.**
> ⚠ **The damping-band floor is still UNTESTED**, and its original evidence is still rectified-channel. It simply no longer matters, because the lever it blocks is empty. **Leave the floor in place** — it costs nothing now.
> ➕ Reader: `rlog-tools/score/notch_depth_vs_antidamping.py`.

> ✅⭐⭐⭐⭐⭐ **THE RATCHET RESONANCE IS NOT DRIFTING — SO IT IS STRUCTURAL, NOT A WEARING PART, AND FIRMWARE DAMPING IS A LEGITIMATE TREATMENT RATHER THAN A PALLIATIVE.**
>
> The most important thing to rule out before recommending more flashing: the ratchet is **real chassis motion** (IMU-confirmed, independent of the EPS) and a **lightly-damped resonance (Q 14–29)**. A resonance has a mass and a stiffness — so if its frequency were **walking**, something would be *changing*, and the right advice would be *“have the front end inspected and stop flashing.”* `f = (1/2π)√(k/m)`, so a 10 % frequency drop is a ~20 % stiffness loss — well within what a worn bushing or loosening joint produces, and easily visible.
> ```
>   15 routes, builds V90..V122, peak of the engaged 5.5-10.5 Hz band per 20 s segment
>
>   median peak        8.50 Hz     route-to-route sd 0.48
>   within-route IQR   1.33 Hz     <- the estimator's own noise floor
>   trend             +0.0103 Hz per build  =  +0.33 Hz over the whole span
>   Spearman rho      +0.277   p 0.318
> ```
> ✅ **[EVIDENCE] THE TREND IS FOUR TIMES SMALLER THAN THE NOISE FLOOR AND NOT SIGNIFICANT.** The resonance is a **fixed structural property of the car**. ⇒ V249 is aimed at a **real and stationary** target, and nothing here indicates a mechanical inspection.
> ⚠ **ONE DISCREPANCY, FLAGGED RATHER THAN SMOOTHED:** this puts the median at **8.50 Hz** where the record's characterisation says **7.79 Hz**. That sits inside the route-to-route spread (sd 0.48, IQR 1.33), and the damper's operating point (`gp-0x6ac0` = 99 counts) was **measured on-car** rather than derived from the frequency, so nothing downstream moves. But the two numbers come from different methods and should not be quoted as one.
> ➕ Reader: `rlog-tools/score/ratchet_frequency_drift.py`.

> ⭐⭐⭐⭐ **V252 — 8× ON TOP OF EVERY FIX. THE AUTHORITY STEP THE BRIEF ASKED FOR, AND THE ONLY BUILD ON THE SHELF THAT MAKES A SYMPTOM WORSE ON PURPOSE.**
>
> The brief was *“6× or higher, up to 16×, with no grinding, vibration or oscillation.”* Until this session the gain step was **unaffordable**: the ratchet tracks the forward gain (rho −0.819 over 17 flown builds), so 8× meant more of the exact symptom being chased with **nothing on the other side of the ledger.** That has changed.
> ```
>   0xC6CD0   5346 -> 7128    forward LKAS gain, 6x -> 8x    -- ONE cell
> ```
> ⭐ **THE CLAMP IS ALREADY RIGHT.** V251 set it to **4096**, which *is* `gain*512//891` at 8× — so V252 **restores** the tracking rather than breaking it further, and never touches the clamp. Asserted at build time.
> **WHAT IS BOUGHT AND PAID, measured rather than asserted:**
> ```
>   BOUGHT   +33 % assist per unit of command, EVERYWHERE -- not just at the peaks
>   PAID     the rail returns 683 -> 512 counts: V251's 23 % rail-time cut is GIVEN BACK
>   PAID     ~13 units of Re(Z) anti-damping, from the gain/ratchet relation
>   OFFSET   V249 supplies ~50 counts of damping against a ~56-count requirement -- the first
>            time in this arc anything has been on the other side of that ledger
> ```
> 🛑 **THIS IS THE ONE BUILD THAT WORSENS A SYMPTOM DELIBERATELY.** Every other build in the V246–V251 group is symptom-reducing or symptom-neutral. **It is NOT the build to fly if the ratchet is the priority**, and it is **only meaningful after V251 has flown clean** — otherwise it inherits an unfixed ratchet and adds 13 units to it.
> ⚠ **THE HISTORY IT WALKS BACK INTO:** 8× flew once as **V101** and was rejected — *“grinding and vibration at all speeds, only while LKAS commands.”* **V101 carried no notch, no damper and no grinding treatment.** V252 carries all three. That is the whole bet, and it is unflown.
> ⇒ **1772 checks passed, 57/57 bit-exact.** The `_STAGED` gate **caught this build** and refused it until registered as a documented gain-raiser — the safety mechanism working exactly as intended.

> ⭐⭐⭐⭐⭐ **V251 IS ALSO THE ANSWER TO *LKAS AUTHORITY* — AND IT IS THE ONLY AUTHORITY LEVER THAT COSTS NO RATCHET.**
>
> I undersold this build as *“not a torque step”*. True of the **gain**; false of **delivered torque**. Computing `delivered = min(|cmd| × gain/891, clamp)` over the flown command stream:
> ```
>   route  build   mean 3072  mean 4096   gain    p99 3072   p99 4096
>   r96    V102         1189       1308  +10.0 %      3072       4096
>   ra6    V106         1118       1240  +10.9 %      3072       4096
>   r1e    V107         1638       1841  +12.4 %      3072       4096
>   r22    V112         1601       1824  +13.9 %      3072       4096
>   r24    V122         1181       1300  +10.1 %      3072       4096
>
>   MEAN DELIVERED TORQUE  1345 -> 1502  =  +11.7 % MORE AUTHORITY
>   PEAK AVAILABLE         3072 -> 4096  =  +33.3 %
> ```
> ✅ **[EVIDENCE] THE p99 SITS AT EXACTLY 3072 ON EVERY ROUTE** — the clamp value itself. **The top 1 % of openpilot's requests were ALL being clipped**, on every drive in the corpus. They now arrive.
> ⭐ **AND IT IS AUTHORITY OPENPILOT WAS ALREADY ASKING FOR.** The gain is untouched, so assist per unit of command is identical and **the ratchet's measured gain dependence is not engaged.**
> ⇒ **THE TRADE, STATED FOR THE OPERATOR:**
> ```
>   V242 (8x gain)   +33 % authority   costs ~13 units of Re(Z)  -- measurably more ratchet
>   V251 (clamp)     +11.7 % authority  costs ZERO ratchet       -- the gain never moves
> ```
> **V251 is strictly better per unit of ratchet cost.** If the operator wants authority without paying in ratchet, this is the whole of what is available — and it was invisible until the rail was measured.

> ✅⭐⭐⭐⭐ **V251'S SAFETY CASE IS FLIGHT HISTORY, NOT A MODEL: ITS PEAK IS A VALUE THAT HAS ALREADY FLOWN, REACHED LESS OFTEN.**
>
> Two things had to be checked before recommending a build that **breaks the clamp/gain tracking**:
> **1. Is the tracking a FIRMWARE INVARIANT or a build convention?** A convention. `0xC61B4` is the clamp in the arbitration (`FUN_00028ea6`) and `0xC61B2` in `limit_and_pack` (`FUN_0002b422`) — **both are plain clamps, and neither is compared against the gain anywhere.** Breaking the tracking changes *where the clip happens*, nothing else. They are also the same two cells V242 moves.
> **2. Is a 4096 clamp at 6× new territory?** No:
> ```
>   build   gain   clamp   peak deliv   rail @cmd   status
>   V122   6.00x    3072         3072         512   FLOWN, on the car
>   V101   8.00x    4096         4096         512   FLOWN -- rejected for GRINDING
>   V251   6.00x    4096         4096         683   this build
> ```
> ✅ **PEAK DELIVERED COMMAND *IS* THE CLAMP** — an absolute limit, independent of gain. **V251 shares V101's peak of 4096, and V101 flew.** V251 merely **reaches** that peak less often (683 counts of openpilot command against V101's 512).
> ⭐ **And what the operator rejected V101 for — *“grinding/vibration at all speeds”* — came from its 8× GAIN, which V251 does not carry.** V251 is 6× with V101's clamp: the half of V101 that was never the complaint.
> ⊕ The soft-EME interlock `0xC674E` = 5120 is asserted **frozen**, and 4096 stays below it. Also relevant: the record's *“gentle EME fires on saturated LKAS command”* means **less saturation should mean fewer EME interventions, not more.**

> ⭐⭐⭐⭐⭐ **V251 — THE FIRST LEVER EVER AIMED AT *PEAK COMMAND OSCILLATION*, THE ONE SYMPTOM THIS ARC HAD NEVER GIVEN ONE. AND IT COSTS NO TORQUE AND NO RATCHET.**
>
> The operator names **three** symptoms; the third has had no lever in sixty builds. It has a specific mechanism: **while the command is at its rail the loop is briefly OPEN** — openpilot asks for more and receives a fixed value — the textbook setup for a limit cycle. Measured over **2,353 railed vs 5,850 free** engaged windows, each symptom band normalised by a **12–18 Hz control band** so the *hard-driving* factor cancels:
> ```
>   ratchet  / control :  railed 2.378   free 0.788   ratio 3.02   p ~ 0
>   grinding / control :  railed 0.631   free 0.335   ratio 1.88   p 2e-265
> ```
> 🛑 **THE FIRST VERSION OF THAT TEST FAILED AND ITS OWN CONTROL SAID SO.** Normalising by TOTAL energy put the **control** band at ratio 0.250 — moving *more* than either symptom band — because railing correlates with cornering, whose large low-frequency content inflates the denominator and pushes every fraction down. Normalising by the control band is what made the split readable.
> 🛑 **AND IT CORRECTS TWO OF MY OWN CLAIMS.** *(a)* The gain ladder cannot fix this: the clamp **tracks** the gain as `gain*512//891`, so the rail sits at **512 counts of command AT EVERY GAIN** — V242/V243 buy **no headroom at all**. *(b)* I earlier called a clamp-only build *“inert”*. That was true of the **damper's magnitude** and **false of saturation**, which is what this build is about.
> ```
>   0xC61B2 / 0xC61B4   3072 -> 4096     forward clamps, both signs
>   0xC6CD0             5346             the GAIN, asserted UNCHANGED at 6x
>
>   rail moves        512 -> 683 counts of openpilot command
>   mean rail duty   17.6 % -> 13.5 %   =  23 % less time with the loop open
> ```
> ✅ **NOT A TORQUE STEP.** The gain is untouched, so assist per unit of command is identical and **the ratchet's measured gain dependence is not engaged.** What changes is that openpilot's larger requests are *delivered* instead of clipped.
> ⭐ **BUILT ON V249, so ONE BUILD NOW ADDRESSES ALL THREE SYMPTOMS:** V241's notch (grinding) · V249's two damper dead zones (ratchet + grinding) · V251's clamp (peak command oscillation). **image `b1976f8f442e7533…` · rwd `2d14f2426dfa3c7f…` · 2 payload bytes.**
> ⚠ **THE RISK:** the top ~4 % of requests now arrive instead of being clipped, so the car may feel more decisive in hard corners. **4096 has flown before** (V101, at 8× gain) and stays below the soft-EME interlock **5120**, which is asserted frozen. Revert to 3072 to undo. And the 3.0× is **observational** — railing is chosen by openpilot, not assigned.
> ⇒ **1735 checks passed, 56/56 builders bit-exact.** Flight order: **V241 → V249 → V251**.

> ✅⭐⭐⭐⭐⭐ **GATE 2 PASSES ON V247/V249/V250: THE DAMPING IS REAL DAMPING AT THE RATCHET, NOT A DISGUISED SPRING.**
>
> The build assumes the damper opposes motion — but `gp-0x6abe`/`gp-0x6ac0` are **filtered** from `gp-0x4f50` in `FUN_00041464`, and a filter with a low corner would rotate that opposition into a **spring term that neither damps nor pumps**. The kit's own GATE 2 demands *magnitude AND phase, in every loop the signal is in*, and I had not run it on this build.
> The filter is **EMA1** — `y0 += ((u*1024 − y0) * alpha0) >> 7` @`0x415DA..0x415E8`, so `alpha_eff = alpha0/128`, with `alpha0` at `0xC643C`:
> ```
>   alpha0 = 37  ->  alpha_eff 0.2891  ->  corner fc = 46.0 Hz   (unchanged V122 -> V249)
>
>   at  7.79 Hz (ratchet) : lag 6.8°   cos(phi) = 0.993   -> 99.3 % still OPPOSES rate
>   at 25 Hz   (grinding) : lag 20.5°   cos(phi) = 0.937   -> 94 % still OPPOSES rate
> ```
> ✅ **[EVIDENCE] The corner is 46 Hz, far above both symptom bands, so the phase error is negligible where it matters.** V249's ~50 counts is **~50 counts of genuine damping**, not a rotated vector.
> 🛑 **THIS WAS A REAL RISK, NOT A FORMALITY.** A 2 Hz corner would have given a 76° lag and `cos = 0.24` — three quarters of the build's output would have been a spring term, and the drive would have read as a null with no way to tell why. The gate had to be run before recommending the build, and it had not been.
> ⊕ `alpha0` is **shared** and **unchanged** by V247/V249/V250 — none of them touch the filter, so this margin is inherited, not spent.

> ✅⭐⭐⭐⭐⭐ **THE SEARCH IS EXHAUSTIVE NOW: THE PATTERN THAT HID THE DAMPER OCCURS EXACTLY ONCE IN THE WHOLE CALIBRATION SURFACE, AND V249 ADDRESSES IT.**
>
> Two blind spots produced V247/V249, and the second is a **mechanical signature** rather than a judgement call: a lane whose LERP value at the operating point is a trivial **fraction of its own range** is structurally starved there — scaling it is near-vacuous, and only reshaping delivers. Sweeping every pointer-array LERP in the cal region at the ratchet's operating point:
> ```
>   boost amp y1     91.8 %      damper FactorB  100.0 %
>   boost amp y4     84.6 %      damper FactorC   47.2 %
>   boost curve      84.1 %      damper FactorD  100.0 %
>   friction lane    87.0 %      damper FactorE    1.7 %   <== STRUCTURALLY STARVED
> ```
> ✅ **[EVIDENCE] `FactorE` IS THE ONLY ONE.** Every other lane runs at **47–100 %** of its range at the operating point; `FactorE` runs at **1.7 %**. **V249 takes it to 13.0 %.** ⇒ **there is no second lever of this class hiding anywhere in the calibration surface.**
> 🛑 **MY FIRST VERSION OF THIS TEST RETURNED ZERO HITS AND WAS WRONG.** It looked for the operating point *below* `X[0]` — but `FactorE`'s problem is the opposite: **99 counts sits just PAST the dead-zone edge of 60**, on the first rising segment, where the curve has climbed to only 16 of 927. *“Below the dead zone”* misses that entirely; *“fraction of the lane's own range”* catches it. The corrected test is what makes the sweep exhaustive.
> ⚠ **STARVED ≠ WORTH OPENING.** A hit means the lane contributes almost nothing and cannot be scaled into life. Whether to *open* it needs the lane's **sign** — the damper was safe to open because it **opposes the motion by construction.** Opening a lane that PUMPS at 6–9 Hz would make the ratchet worse.
> ➕ Reader: `rlog-tools/score/dead_zone_sweep.py`, kept with its own first-version error documented.

> 🛑⭐⭐⭐⭐⭐ **THE GRINDING RISK IN V249 CANNOT BE TESTED FROM THE CORPUS — AND THE REASON IS THE FINDING: THE STOCK DAMPER IS DOING ESSENTIALLY NOTHING, ANYWHERE.**
>
> V249 raises the grinding band 4.1×, and V62's *“2× is the OPTIMUM, not a point on a ramp”* says more damping is not monotonically better. I tried to falsify that from flown data with a **regression discontinuity at the damper's switch-on speed.** **The design was wrong**, and both halves of why are worth keeping:
> **1. There is no step to find.** The LERP is **continuous at its knee** — below `X[0]` it clamps to `Y[0] = 0`, and above it ramps *from* 0. So the damper is zero on *both* sides of 35 km/h; there is a **kink in slope, not a step in value.** All three bands returned the same jump (+0.0072, control included, z 0.37–1.02) — the estimator was reading noise, and **the control band is what caught it.**
> **2. 🛑 THE DEEPER REASON, AND IT MATTERS MORE:**
> ```
>   V122 ENGAGED, at the ratchet rate of 99 counts
>     25 km/h  FactorC   0   damper  0        80 km/h  FactorC 429   damper  6
>     35 km/h  FactorC   0   damper  0       100 km/h  FactorC 588   damper  9
>     50 km/h  FactorC 140   damper  2       120 km/h  FactorC 748   damper 11
> ```
> **The stock damper NEVER EXCEEDS ~11 COUNTS ANYWHERE IN THE NORMAL SPEED RANGE.** Against a torque signal with p50 136 and band envelopes in the hundreds, that is a **sub-percent** effect — **no design can detect it, so no drive in the corpus can say whether damping this lane helps or hurts grinding.**
> ⇒ **AND IT REFRAMES V249.** It is not *“more damping”* — it is going from **effectively NO DAMPER to a real one** (6 → 50 above 35 km/h, **0 → 50 below**). ⭐ **V62's caution may therefore not transfer at all:** that lesson came from a lane that was already doing something, and this one is not.
> ⚠ **STATUS: the grinding side of V249 is GENUINELY OPEN and only a drive settles it.** The ratchet direction is well-founded — the damper opposes the motion **by construction**; the grinding direction is a free hypothesis the same build tests. **If grinding worsens on V249, that is the signature, and V241 is the way back.**
> ➕ Reader: `rlog-tools/score/damper_switch_on_discontinuity.py`, kept **with its own design error documented.**

> ⭐⭐⭐⭐⭐ **V249 IS ONE LEVER AIMED AT BOTH SYMPTOMS. THE DAMPER IS RATE-PROPORTIONAL, SO OPENING IT RAISES THE GRINDING BAND TOO — AND BELOW 35 km/h IT CURRENTLY SUPPLIES LITERALLY ZERO AT EITHER.**
>
> `gp-0x6ac0` is `|motor rate| >> 10`. The ratchet sits at the measured **99 counts**; a 22–30 Hz oscillation of similar amplitude turns the motor ~3× faster, so the grinding band maps to ~**300 counts**. Damper magnitude through the decompiled mirror, ENGAGED:
> ```
>                     V122   V247   V249   V250
>   80 km/h
>     ratchet   (99)     6     50     50    100      8.3x
>     grinding (300)    41    167    167    335      4.1x
>
>   25 km/h  -- below the FactorC knee
>     ratchet   (99)     0      0     50    100      0 -> full
>     grinding (300)     0      0    167    335      0 -> full
> ```
> ✅ **[EVIDENCE] the same edit lifts BOTH bands** — 8.3× at the ratchet and 4.1× at the grinding band, at 80 km/h. And **below 35 km/h the car currently has NO damping at all at either frequency**, which V249 takes to full. The operator's two symptoms may share one cell.
> ⚠ **AND THE CAUTION THAT GOES WITH IT.** V62's lesson on a *different* lane was *“2× is the OPTIMUM, not a point on a ramp”* — more damping is not monotonically better, and this raises the grinding band **4.1×**. If grinding gets WORSE rather than better on V249, that is the signature, and V247 (which leaves low speed alone) or V241 is the way back. **The ratchet direction is well-founded; the grinding direction is a hypothesis this build happens to test for free.**
> ⊕ At high rate (fast steering) V249 delivers **225** against V122's 122–225, so quick manoeuvres meet up to 1.8× the stock damper — **engaged only**, never in the driver's hands.

> 🛑🛑⭐⭐⭐⭐⭐ **V247 WAS AIMED AT ONLY 64 % OF THE PROBLEM — I BUILT HALF THE RECOMMENDED LEVER. V249 AND V250 CLOSE IT, AND THE DAMPER LADDER IS NOW COMPLETE ACROSS THE WHOLE SPEED RANGE.**
>
> The record's recommendation was to open **both** dead zones. **V247 opened only the RATE half.** `FactorC`'s SPEED dead zone is `X[0] = 2240` counts = **35 km/h with `Y[0] = 0`**, and zero × anything = 0 — so **below 35 km/h the whole damper is structurally zero no matter what `FactorE` does.** Stratifying the measured anti-damping by speed, coherence-gated, **4,772 engaged windows**:
> ```
>    0-10 km/h  -55.5      10-20  -65.6      20-35  -71.7     <- damper DEAD
>   35-50 km/h  -68.4      50-70  -60.0      70+    -57.4     <- damper live
>
>   below the knee: 36.4 % of engaged windows, Re(Z) -64.7
>   above the knee: 63.6 %,                    Re(Z) -60.9
> ```
> 🛑 **THE ANTI-DAMPING IS PRESENT AT EVERY SPEED, ROUGHLY UNIFORMLY — IT IS NOT A CREEP-ONLY PHENOMENON**, and below the knee it is if anything **worse**. So V247 could act on 64 % of engaged driving and was inert by construction on the other 36 %.
> ⇒ **V249** = V247 + `FactorC Y[0] 0 → 429` (`:= Y[2]`, the record's own value) · **V250** = V249 + `FactorB ×2`. Priced through the decompiled mirror, from the real image bytes:
> ```
>   build     10 km/h   25 km/h   80 km/h   MANUAL 25 km/h
>   V122            0         0         6              0
>   V241            0         0         6              0
>   V247            0         0        50              0    <- high speed only
>   V248            0         0       100              0    <- high speed only
>   V249           50        50        50              0    <- all speeds,  89 % of requirement
>   V250          100       100       100              0    <- all speeds, 179 %
> ```
> ✅ **[EVIDENCE] MANUAL READS 0 ON EVERY BUILD** — the engaged-only guarantee is now verified from the **shipped artefacts** across the entire ladder, not asserted at build time. Honda's dead zones exist so the wheel is not heavy in the driver's hands; **none of this added damping reaches them.**
> ⇒ **V249 SUPERSEDES V247 and V250 SUPERSEDES V248** as recommendations — the earlier pair are the high-speed-only versions and stay on the shelf only as the discriminating variants.
> ⚠ **THE RISK V249 CARRIES THAT V247 DOES NOT:** openpilot engaged at low speed now meets a damper Honda deliberately removed there. **If LKAS feels sluggish in slow corners or traffic, `FactorC Y[0]` back to 0 returns V247 exactly.**
> ⇒ **1699 checks passed, 55/55 builders bit-exact.** Flight order: **V241 → V249 → V250 → V246**.

> ✅⭐⭐⭐⭐⭐ **V247/V248 VERIFIED AGAINST THE DECOMPILED ARITHMETIC, FROM THE REAL BYTES — AND A REAL GAP IN THE GOLDEN MODEL CLOSED IN THE PROCESS.**
>
> The 90 % / 181 % figures came from a hand LERP, so they needed an independent derivation. **The golden model could not supply one: it does NOT implement this lane at all** — `assist_shaping_lanes` takes `damping_6bd0` as a *supplied input defaulting to 0*, and every `FactorB`/`FactorC`/`FactorE` reference in the four modules is a **comment**. That gap was harmless while the damper was untouched and is not harmless now.
> ⇒ **`analysis-2020accord/model/damper_fun34350_mirror.py`** mirrors `FUN_00034350` in integer Python, address by address, reading the real tables out of the real images — including both gates (`FactorC` forced to unity above `0x7d00` or on an implausible voter; the `FactorE` validity window that zeroes the **whole term**) and the strict-`<=` bottom clamp.
> ```
>   build      B     C     D     E   ceiling  magnitude  vs req
>   V122    1024   429  1024    16      512          6     11 %
>   V241    1024   429  1024    16      512          6     11 %
>   V246    1024   429  1024    16      512          6     11 %
>   V247    1024   429  1024   120      512         50     89 %
>   V248    2048   429  1024   120      512        100    179 %
>
>   manual (mode 24):  V122 = 6   V247 = 6   V248 = 6     <- unchanged
> ```
> ✅ **[EVIDENCE] The hand figures were 6.7 / 50.6 / 101.3; the integer mirror gives 6 / 50 / 100 — agreement within truncation.** The dose claims stand on the decompiled chain now, not on my arithmetic.
> ✅ **AND THE ENGAGED-ONLY CLAIM IS NOW VERIFIED FROM THE BUILT ARTEFACTS, not merely asserted at build time:** the manual damper reads **6 counts on V122, V247 and V248 alike.** Manual steering feel is untouched, confirmed by reading the shipped images.
> ⊕ **The mirror is a SIBLING module, not imported by the facade**, so the golden model's contract is intact and re-verified: **87 symbols, hash `740f4bcd…` — both OK.**
> ⚠ **Still a real gap:** the golden model itself remains without this lane. The mirror documents and prices it, but folding it into the facade would change the 87-symbol/hash contract and should be done deliberately, not as a side effect.

> 🛑🛑⭐⭐⭐⭐⭐ **THE SEARCH IS COMPLETE. ALL FIVE SENSOR-FED LANES ARE NOW ACCOUNTED FOR — BUILT, OR CLOSED BY ARITHMETIC, OR CLOSED BY THE OPERATOR'S OWN CONSTRAINT. THE ONLY THING THAT REACHES THE REQUIREMENT IS THE DAMPER.**
>
> The on-car evidence confines the ringing to five lanes: *“for 52–70 % of the return the LKAS lane is a DC CONSTANT, yet the 6–9 Hz |tq| envelope is unchanged … a constant cannot carry 7.8 Hz ⇒ **the ringing enters through a SENSOR-FED lane, not the command lane.**”*
> ```
>   r24/r26      Lever B  0xC6446    -> V246 BUILT (1.5x)
>   gp-0x6ad4    PID knee 0xC67C4    -> V245 BUILT (1280 -> 512)
>   gp-0x6b26    inertia  0xC63AE    -> CLOSED: an INERTIA term; raising it adds apparent MASS
>   gp-0x6bbe    viscous  0xC63A2    -> CLOSED: 2.4 % of requirement, 3.2 % at its rail
>   plant model  k1       0xC40D2    -> V222 restored to 1020, carried
>
>   base-assist damper gp-0x6bd0 (NOT sensor-fed -- it OPPOSES the motion):
>                V247   50.6 counts    90 % of requirement
>                V248  101.3 counts   181 %
> ```
> ✅ **`gp-0x6bbe` WAS THE LAST GENUINELY OPEN ONE** — the only lane measured as *truly* viscous (flat **90 ct/(rad/s)**, phase ~0° vs rate) and a **virgin single-reader cal** the record explicitly refused to call vacuous without a number. The number: `90 ct/(rad/s) = 1.571 ct/(deg/s)` against a **65 ct/(deg/s)** requirement = **2.4 %**, and it already sits at **76 % of its ±512 rail** so it can rise at most **1.32×** ⇒ **3.2 % maximum.** Closed on arithmetic, which is what the record asked for.
> ⭐ **`gp-0x6b26` closes on the operator's own words rather than a number:** it is an **inertia** term, so raising it adds **apparent mass** — *“increasing mass and friction should not be our primary approach … we want LOW apparent steering mass and friction.”* Wrong direction by construction.
> ⇒ **THE WHOLE SEARCH NOW RESOLVES TO ONE SENTENCE:** the ringing enters through sensor-fed lanes that are individually too small to cancel it, and the lane that *could* cancel it — **the damper, whose entire purpose is to oppose this motion** — has been sitting behind a dead zone the operating point never clears, **byte-stock in every build ever flown.** V247 and V248 are the first builds to open it.
> ➕ Reader: `rlog-tools/score/sensor_fed_lane_census.py`.

> ⭐⭐⭐⭐ **V248 BUILT — THE MARGIN RUNG. V247 REACHES 90 % OF THE REQUIREMENT; THIS TAKES IT TO 181 %, FROM THE SAME LANE, WITH THE ARITHMETIC EXACT.**
>
> V247's ~50.6 counts against a ~56-count requirement is close — **and the requirement is itself an estimate**, so if it is really 70 or 80 then V247 lands short. This buys margin from the cell best suited to it:
> ```
>   0xD774C   FactorB (engaged, mode 26)   Y = [1024]x4 -> [2048]x4
>
>   V247    50.6 counts    90 % of requirement
>   V248   101.3 counts   181 % of requirement      still 5x under the 512 ceiling
> ```
> ⭐ **WHY `FactorB` IS THE RIGHT CELL FOR MARGIN, AND WHY ITS SHAPE IS SAFE BY CONSTRUCTION.** It is a **FLAT Q10 gain at unity** across its whole axis — a pure multiplier with **no dead zone, no knee and no slope to get wrong**. And at high rate the product **already clamps**:
> ```
>   stock, high rate:  1024 x (908/1024) x (927/1024) = 822  -> clamped to 512
>   V248,  high rate:  that x2 = 1644                        -> clamped to 512, IDENTICAL
> ```
> ⇒ **doubling it changes NOTHING at the top end and lifts only the low/mid-rate region** — exactly where the ratchet lives and exactly where the damper was too small. **The lever's shape matches the target by construction rather than by tuning.**
> 🛑 **FLY V247 FIRST — THIS IS THE MARGIN RUNG, NOT THE FIRST ATTEMPT.** V247 vs V241 is one variable; V248 vs V247 is one variable. Flying V248 first **wastes the discrimination**: if the ratchet improves you will not know whether the dead zone or the gain did it, and if the wheel feels heavy you will not know which half to walk back.
> ⚠ **COST, twice V247's:** ~101 counts is **~3.3 % of the 3072 forward clamp**, engaged only. If LKAS feels reluctant, `FactorB` back to 1024 returns to V247 exactly.
> ⭐ **BUILT — image `d2b554038a59f9c2…` · rwd `fa50afd325c88adb…` · 4 payload bytes.** **1627 checks passed, 53/53 builders bit-exact.**
> ⇒ **FLIGHT ORDER: V241 → V247 → V248 → V246.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE ENTIRE BASE-ASSIST DAMPER HAS BEEN BYTE-STOCK IN EVERY FLOWN BUILD. ALL FIVE RECORDS. THE CENSUS WAS BLIND TO THE WHOLE LANE — AND SIXTY BUILDS NEVER TOUCHED IT.**
>
> The FDR census tests only cells that **varied**; a byte-identical cell has nothing to correlate. Sweeping the complement — every damper record, across all 18 flown builds:
> ```
>   FactorB   NEVER VARIED      FactorC   NEVER VARIED      FactorD   NEVER VARIED
>   FactorE   NEVER VARIED      ceiling   NEVER VARIED
> ```
> ⇒ **the census's null said nothing whatsoever about the damper.** V247's lever was hiding in exactly this blind spot, and so are three more.
> ⭐ **PRICED BY ARITHMETIC at the measured operating point** (speed 5120 counts, `gp-0x6ac0` = 99), against the **~56 counts** needed to cancel `Re(Z) = −65`:
> ```
>                                            magnitude   vs requirement
>   stock                                          6.7        12 %
>   V247: FactorE X[0]=12, Y[1]:=Y[2]             50.6        90 %
>   FactorB flat 1024 -> 2048  (alone)            13.5        24 %
>   FactorD flat 1024 -> 2048  (alone)            13.5        24 %
>   FactorC Y[2] 429 -> 908    (alone)            14.2        25 %
>   V247 + FactorB 2048                          101.3       181 %
>   V247 + FactorB + FactorD                     202.5       362 %
>                          headroom to the 512 ceiling: 76x from stock, 10x from V247
> ```
> ✅ **V247 ALONE REACHES 90 % OF THE COMPUTED REQUIREMENT**, and `FactorB`/`FactorD` are **flat Q10 gains sitting at unity** — pure multipliers with linear leverage and *no shape to corrupt*, so if V247 proves the direction but falls short, the next step is arithmetic rather than invention.
> 🛑 **HEADROOM IS NOT PERMISSION, AND NOTHING MORE IS BEING BUILT.** More damping costs LKAS authority — it opposes openpilot's own steering, and V247's 51 counts is already **1.6 % of the 3072 forward clamp** — and a damper large enough to matter can change loop behaviour away from the band it was aimed at (**GATE 2**). **V247 must fly first.** A ladder built before the first rung is scored is three wasted drives.
> ⊕ **AND IT REFRAMES THE WHOLE ARC.** Sixty builds went into rate lanes, filters, notches, caves and probes. **The damper — the one lane whose entire purpose is to oppose this motion — was never touched once.** That is the single most useful sentence to hand the next session.
> ➕ Reader: `rlog-tools/score/damper_never_varied_sweep.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **V247 — THE DAMPER'S RATE DEAD ZONE, OPENED, ENGAGED ONLY. THE BIGGEST UNFLOWN LEVER IN THE KIT, AND THE FIRST ONE COMPUTED TO ACTUALLY REACH THE RATCHET.**
>
> The FDR census said the cal surface was exhausted — **but a census can only test cells that have VARIED, and the damper's dead zones are BYTE-STOCK IN ALL 18 FLOWN BUILDS.** They were never tested because they were never moved.
> ```
>   FactorE (engaged, mode 26 @0xD780C)   X=[60, 400, 2500, 4000]   Y=[0, 140, 539, 927]
> ```
> Below `X[0]=60` counts of motor rate the LERP clamps flat to `Y[0]=0`, and **zero × anything = 0, so the damper is simply OFF.** The ratchet's measured operating point is `gp-0x6ac0 = 99` — *just* past the edge, on the first rising segment where the curve is still almost nothing:
> ```
>   LERP(99) stock              =  16.1   ->  damper delivers ~6.7 counts
>   LERP(99) X[0]=12, Y[1]=539  = 120.8   ->  damper delivers ~50.6 counts     7.5x
> ```
> ✅ **AND THE REQUIREMENT IS MET, BY TWO INDEPENDENT ROUTES.** `Re(Z) = −65` at the measured p50 band amplitude of 0.86 °/s is **≈56 counts of torque — only 0.5 % of the aggregator's ±10240**, so the magnitude needed to cancel the ratchet was never the problem. And the record's *own* pricing of this same lever, done for a different purpose, reads **“BOTH dead zones opened ~50”** against **“a requirement of ~43”**. **Two routes land at ~50 against 43–56.**
> ⭐ **WHY IT NEVER FLEW — IT WAS NEVER FALSIFIED, ONLY MIS-ADDRESSED.** V72 and V73 tried this and were **INERT BY TABLE SELECTION**: they edited **modes 10/11**, assuming this part number is row 2 *TVAA1*. It is not — the car is **row 11 *TVCA4*, modes 24 manual / 26 engaged.** So the lane is **unflown and unfalsified**, not tried-and-failed.
> ⭐⭐ **ENGAGED ONLY, AND THAT IS WHAT MAKES ADDED DAMPING AFFORDABLE.** Every mode owns its own record — mode 26 @`0xD780C`, mode 24 @`0xD6820`, **no sharing** — so **manual feel is byte-identical**. The operator's standing instruction is *“increasing mass and friction should not be our primary approach … we want LOW apparent steering mass and friction”*; **a damper that exists only while the car drives itself does not spend that.**
> 🛑 **GATE 2 — V72'S EXACT MISTAKE, AVOIDED AND ASSERTED.** V72 set `Y[0..2] → 927`, flat across the whole rate axis, turning a rate-proportional damper into a **near-bang-bang RELAY** — and a relay in a loop at a lightly-damped resonance is a **limit-cycle generator**. This does the opposite, with all three asserted at build time: **`Y[0]` stays 0** (zero damping at zero rate, so no relay) · the curve stays **monotone** `[0,539,539,927]` · it **OPENS the dead zone rather than raising a gain**, so the lane becomes *more* rate-proportional in the symptom's range, not flatter.
> ⚠ **THE COST, AND THE UNCERTAINTY.** ~50 counts against the 3072 forward clamp is **~1.6 % of LKAS authority**, spent only while engaged — if LKAS feels lazier, this is the cell and `60/140` is the way back. And both the ~56 requirement and the ~50 delivery are **estimates**: the damper's phase is right *by construction* (`−sign(rate)`), but its effect on `Re(Z)` is **computed, not measured**, and this lane has never been observed working on this car.
> ⭐ **BUILT — image `7a59497a592ea6e3…` · rwd `eb92273e2e416403…` · 3 payload bytes.** Cal-only, no cave, engaged-only, instantly revertible. **1590 checks passed, 52/52 builders bit-exact.**
> ⇒ **FLIGHT ORDER NOW: V241 → V247 → V246.** V247 displaces V246 as the second flight because it is computed to nearly cancel the ratchet where V246's effect is smaller and statistically marginal.

> ⭐⭐⭐⭐⭐ **THE SEARCH IS CLOSED SYSTEMATICALLY: OF EVERY CALIBRATION CELL THAT VARIES ACROSS THE FLOWN CORPUS, ONLY *TWO THINGS* TRACK THE RATCHET'S ANTI-DAMPING — THE GAIN AND LEVER B. THERE IS NO HIDDEN LEVER.**
>
> Lever B was found **opportunistically**, by noticing it happened to correlate. This is the exhaustive version: every u16 in `[0xC4000,0xCC000)` that differs between any two flown images, regressed against the coherence-gated 6–9 Hz `Re(Z)`, with Benjamini-Hochberg FDR and collinear cells grouped into indistinguishable classes.
> ```
>   16 flown builds · 17 varying cells (cave and CRC trailers excluded)
>
>   GAIN + its two tracking clamps    rho -0.803   q 0.0010
>   Lever B                           rho +0.677   q 0.0168
>   ---- nothing else survives FDR ----
> ```
> 🛑 **AND THE FIRST PASS FOUND FIVE MORE “HITS” THAT WERE ALL ARTEFACTS — worth recording because they look exactly like levers.** `0xC4B48`–`0xC4B98` all fall inside the **164-byte cave at `0xC4B34`**, which holds each build's **probe payload**: it differs by *instrument design*, not by any damping mechanism. `0xC6FFC`/`0xC6FFE` are the **CRC trailer** of block `0xC6000` — a *derived* checksum that moves whenever anything in its block moves. Both classes score highly and mean nothing; excluding them cut 103 varying cells to 17. **A cross-build byte census must exclude derived and instrument bytes or it manufactures levers.**
> ⇒ **WHAT THIS SETTLES.** The gain is locked to authority; three escapes from that lock were closed this session (clamp tracks the gain · `0xC646C` is 0.7 % · the command has nothing at 6–9 Hz to filter). **Lever B is the only cell in the entire calibration region that moves the ratchet without spending authority — established by exhaustion, not by noticing.** That is precisely what V246 carries.
> ⚠ **LIMITS, unchanged and real:** one route per build, builds differ in many cells at once, and a cell that never varied in the flown corpus **cannot be tested here at all** — this censuses what has flown, not what exists. Absence from this table is not proof of inertness.
> ➕ Reader: `rlog-tools/score/antidamping_cell_census.py`.

> ⭐⭐⭐⭐ **V246'S DOSE IS VALIDATED, AND NO FURTHER RUNG IS WARRANTED. THE DESCRIBING-FUNCTION ASYMPTOTE HAS ALREADY BITTEN ABOVE THE MEDIAN AMPLITUDE — SO LEVER B'S ENTIRE BENEFIT LIVES EXACTLY WHERE THE RATCHET DOES.**
>
> Pricing the dose against the **measured** 6–9.5 Hz torque-rate envelope rather than an assumed one, through the lane's own arithmetic (`out = clamp(deadzone((clamp(rate,±5120)·k)>>10, ±3), ±8192)`):
> ```
>   A              k=5244    k=7866   k=13107    saturating?
>   p50   859        5244      7866     11157    13107 only
>   p90  4253        2451      2485      2502    ALL
>   p99  6541        1617      1626      1630    ALL
>   max  7574        1400      1405      1408    ALL
>
>   still LINEAR:   5244: 70.4 %   7866: 57.6 %   13107: 39.5 %
> ```
> ✅ **[EVIDENCE] ABOVE p50 EVERY DOSE SATURATES AND THE DELIVERED DAMPING IS WITHIN ~1–2 % REGARDLESS OF `k`** — 2451 vs 2502 at p90, 1617 vs 1630 at p99. `N(A) → 4L·1024/(πA)`, independent of `k`, exactly as the lane's describing function predicts. **Dose spent above the knee is wasted.**
> ⭐ **AND THAT IS THE RIGHT SHAPE FOR THIS TARGET.** All of Lever B's reachable benefit is concentrated in the **low-amplitude half of frames** — and the ratchet is a **micro-regime** symptom (creep, 1–13 °/s). At `p50` the 1.5× step delivers a **full +50 %** of effective damping; at `p90` it delivers **+1.4 %**. The lever bites where the symptom is and nowhere else.
> ⇒ **THIS VALIDATES V246's 1.5× RATHER THAN ARGUING FOR MORE.** Going on to 2.5× would add ~42 % at `p50` and **under 1 % everywhere above it**, while moving twice as far from **V88's bracketed grinding optimum** — the one real risk this build carries. **No V247 is warranted until V246 has flown**, and building one now would spend a drive to learn almost nothing.
> ⚠ **PRICES THE RATCHET SIDE ONLY.** Nothing here says a larger dose is safe at 22–30 Hz; `5244` was bracketed for **grinding**.
> 🛑 **A TOOLING TRAP CAUGHT IN PASSING, and it silently produced a clean-looking empty table:** `np.gradient(q, t)` divides by zero on the caches' **duplicate timestamps**, NaN-ing the whole envelope with only a `RuntimeWarning`. Use the uniform sample rate. Same family as the fallback-key-chain null.
> ➕ Reader: `rlog-tools/score/lever_b_dose_headroom.py`.

> ⭐⭐⭐⭐⭐ **V246 BUILT — LEVER B 1.5×. THE FIRST LEVER MEASURED TO MOVE THE RATCHET *WITHOUT SPENDING AUTHORITY*, WHICH IS THE TRADE THE OPERATOR HAS BEEN ASKING FOR ALL ALONG.**
>
> The ratchet's anti-damping tracks the **forward gain**, and forward gain is also what buys authority — so they are locked, and **three escapes were opened and closed this tick, all by arithmetic, none needing a drive:**
> ```
>   the tracking CLAMP     follows the gain as gain*512//891  =>  a clamp-only build is INERT
>   the 0xC646C FEEDBACK   |k| = 0.0073 at 7.79 Hz            =>  zeroing it moves Re(Z) by 0.13 of 65
>   a forward LOW-PASS     LKAS carries 0.09-1.7 % of its     =>  there is nothing there to filter
>                          0-5 Hz energy at 6-9.5 Hz
> ```
> ✅ **LEVER B IS THE ONE CELL THAT IS NOT LOCKED TO AUTHORITY AND DOES MOVE THE RATCHET.** Controlling for gain — the mirror of the control run on gain itself:
> ```
>   WITHIN GAIN 6x    LeverB  512 (n=2)   Re(Z) -73.59
>                     LeverB 5244 (n=7)   Re(Z) -67.78
>                     Mann-Whitney p = 0.0556,  +5.81 in favour of the HIGHER dose
> ```
> ⭐ **AND THE HEADROOM IS COMPUTED, NOT GUESSED.** Lever B's real ceiling is its **describing function** — the lane is a plain saturation, `N(A) → 4L·1024/(πA)` independent of `k`. The knee sits at **k = 58624 at p90** torque-rate amplitude, **14080 at p99**, **5184 at max**. ⇒ at *typical* amplitudes the car's **5244 is far BELOW the knee, still in the LINEAR region where raising k genuinely buys damping**; only the largest excursions are already saturated.
> ```
>   0xC6446   5244 -> 7866   (1.50x)   well under the p99 knee of 14080
> ```
> ⚠ **WHAT IS ASSUMED, AND IT IS THE WHOLE RISK: 5244 is V88's BRACKETED optimum for GRINDING**, and this moves off it. V62's lesson is *“2× is the OPTIMUM, not a point on a ramp.”* **Whether the step costs grinding is NOT established** — the only cross-build grinding comparison available is an uncontrolled band fraction (no speed matching, no road control) whose groups overlap heavily. It happens to point the *same* way (less grinding at the higher dose) but **that is not evidence and is not claimed as any.** V222's 2.5× (13107) was flagged as over-dosing, which is exactly why this stops at 1.5×.
> ⭐ **BUILT — image `c97e535f3177c564…` · rwd `f336b0d53d335fde…` · 2 payload bytes.** Cal-only, no cave, and **ONE VARIABLE against V241**: identical notch, identical gain, identical everything else. Instantly revertible.
> ⇒ **1557 checks passed, 51/51 builders bit-exact.** Shelf: **V241 · V242 · V243 · V245 · V246**.
> ⊕ Readers: `size_c646c_feedback_lever.py` (the feedback closure) and `gain_vs_clamp_collinearity.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **CORRECTION TO MY OWN HEADLINE: THE GAIN↔ANTI-DAMPING LINK IS A STRONG ASSOCIATION WITH *ONE* ERA-FREE CONTRAST — NOT THE CLEAN CAUSAL BREAK I WROTE. LEVER B MOVED IN THE SAME STEP.**
>
> I claimed the V100→V101→V102 reversal *“breaks the era confound”*. **Half of it does not.** `V101` changed the gain **and removed Lever B** (`0xC6446` 5244 → 512) in the same build:
> ```
>   V100   gain 3564   LeverB 5244   Re(Z) -66.83
>   V101   gain 7128   LeverB  512   Re(Z) -84.06   <- BOTH changed: leg is CONFOUNDED
>   V102   gain 5346   LeverB  512   Re(Z) -74.91   <- LeverB held: this leg is CLEAN
> ```
> ⇒ **only the second leg is era-free** — gain 8× → 6× with Lever B held, `Re(Z)` **+9.15**. **That is ONE pair**, not a two-legged reversal.
> ✅ **WHAT SURVIVES, AND IT IS STILL SUBSTANTIAL:**
> ```
>   rho(GAIN,   Re(Z)) = -0.819  p 0.0001   n=17
>   rho(LeverB, Re(Z)) = +0.661  p 0.0038   <- Lever B correlates too, and PROTECTIVELY
>   within LeverB = 5244 (n=14): rho(GAIN, Re(Z)) = -0.762  p 0.0015
> ```
> **The gain association survives controlling for Lever B.** But inside those 14 builds the gains are 4× (all early) and 6× (all late), **so build era remains confounded and this corpus cannot fully separate them.**
> ⚠ **HONEST STATUS: gain is the best-supported single explanation for the ratchet's anti-damping, with one era-free contrast behind it — not an established cause.** *“Era”* is not a mechanism, it is a placeholder for the other things those builds changed, and **Lever B was one of them and it did correlate.** No further competing lever has been identified.
> ⊕ **AND A GENUINELY USEFUL SIDE-RESULT: Lever B is PROTECTIVE.** `rho +0.661` means the builds carrying **5244** are LESS anti-damped than the three carrying 512. **V241 carries Lever B at 5244** — V88's measured optimum — so the flight candidate already holds the protective value.
> ⇒ **THE PRACTICAL ADVICE IS UNCHANGED IN DIRECTION AND WEAKER IN CERTAINTY:** V241 at 6× is the safe rung; 8× and 10× are **likely** worse for the ratchet rather than **measured** worse. The drive card has been corrected to say exactly that.

> 🛑🛑⭐⭐⭐⭐⭐ **THE LKAS GAIN *IS* THE RATCHET'S ANTI-DAMPING. IT PRICES THE GAIN LADDER, AND IT EXPLAINS WHY NO OTHER LEVER HAS EVER MOVED THE RATCHET IN SIXTY BUILDS.**
>
> Regressing the coherence-gated 6–9 Hz `Re(Z)` on `0xC6CD0` across every flown build:
> ```
>   4x  (7 builds)   Re(Z)  -46.6 .. -66.8
>   6x  (9 builds)   Re(Z)  -62.3 .. -74.9
>   8x  (1 build)    Re(Z)  -84.1
>   slope -0.0074 per count · R2 0.726 · Spearman rho -0.819 · p 0.0001 · n = 17
> ```
> ⚠ **Gain rises monotonically with build era, so the trend ALONE proves nothing.** What breaks that confound is a **reversal**, and there is one — three consecutive builds where the gain goes **up then down**:
> ```
>   V100  4x  ->  Re(Z) -66.83
>   V101  8x  ->  Re(Z) -84.06     gain UP,   anti-damping DEEPENS  (-17.23)
>   V102  6x  ->  Re(Z) -74.91     gain DOWN, anti-damping RECOVERS (+9.15)
> ```
> ✅ **[EVIDENCE] `Re(Z)` FOLLOWS THE REVERSAL. Build era is monotone and cannot produce one.** ≈ **−4.4 of `Re(Z)` per 1× of gain.**
> ⭐⭐ **WHY THIS CLOSES THE ARC'S CENTRAL PUZZLE.** The ratchet was never a lever we had failed to find — **it tracks the gain the kit itself kept raising.** That is why every cal, filter, damper, cave and notch measured null on it, and why **no build V90→V122 moved the anti-damping** (median −64.8, sd 9.1): none of them changed the thing that sets it.
> ⇒ **HOW IT WAS REACHED — three eliminations first, all from bytes:** engagement re-indexes the mode table 24→26, and of everything that re-index touches, **the five base-assist damper records and all three boost tables are BYTE-IDENTICAL** between manual and engaged. Only **friction** differs (3× — `Y −9830/−5734/−1966` → `−29490/−17202/−16000`), and its dose spans **1.0×–3.0× across 17 flown builds with NO relation to `Re(Z)`** (rho −0.263, p 0.31). ⇒ no re-indexed calibration explains it, which left the applied LKAS torque — and that is what the gain sets.
> 🛑🛑 **THE PRICE OF THE LADDER, AND THE OPERATOR MUST SEE IT BEFORE FLYING:**
> ```
>   V241   6x   the car's present gain    Re(Z) ~ -70   (V122 measured -70.13)
>   V242   8x   +2x                       Re(Z) ~ -79   ratchet WORSE
>   V243  10x   +4x                       Re(Z) ~ -88   ratchet WORSE STILL
> ```
> **This does not withdraw V242/V243** — the operator asked for the ladder and it is built and verified — but it converts them from *“more authority, ratchet unknown”* into *“more authority, measurably more ratchet”*. **V241 remains the recommendation, and now for a measured reason rather than a cautious one.**
> ⚠ **LIMITS:** n = 75–170 windows, **one route per build**, and adjacent builds differ in more than the gain cell. The reversal is what carries this, not the regression. **A SCREEN that prices a trade-off — not a controlled experiment.**
> ➕ Readers: `rlog-tools/score/gain_vs_antidamping.py`, `friction_dose_vs_antidamping.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **NO BUILD FROM V90 TO V122 HAS MOVED THE 6–9 Hz ANTI-DAMPING — AT ALL. THAT IS THE MECHANISM-LEVEL REASON SIXTY BUILDS PRODUCED NOTHING ON THE RATCHET.**
>
> Now that the ratchet's anti-damping measures **linear and amplitude-independent**, a per-build comparison of it is finally *interpretable* — and that same amplitude-independence is what makes it interpretable, since a quantity that swings with amplitude cannot be compared across routes that differ in amplitude. Engaged windows, `tq` vs `cs_rate` (**both non-rectified**), **coherence ≥ 0.60 only**:
> ```
>   V90 -60.0 · V91 -53.4 · V96 -54.2/-54.0 · V98 -46.6 · V99 -56.6 · V100 -66.8 · V101 -84.1
>   V102 -74.9 · V103 -72.3 · V104 -64.8 · V105 -67.8 · V106 -63.5 · V107 -62.3 · V111 -70.6
>   V112 -68.5 · V122 -70.1
>   median -64.77   sd 9.07   range -84.1 .. -46.6 over 17 builds
> ```
> ✅ **[EVIDENCE] NOTHING IS OFF THE PACK.** The only two flagged at |z| ≥ 2 are the **smallest-n routes** (V98 on 26 windows, V101 on 75); the spread is 14 % of the median with no structure by build era. **Thirty-plus builds of levers — rate lanes, dampers, filters, caves, the notch arc — and not one of them came near this number.** The record's *“nothing has moved the ratchet”* now has a mechanism behind it rather than a symptom tally.
> ⊕ **AN OBSERVATION, NOT A FINDING, IN THE CONTROL BAND.** At 22–30 Hz the builds *do* separate — `V90 +14.1 · V96 +12.8 · V106 +11.7` against `V107 −1.5 · V111 −8.3 · V112 −12.0`, and then **V122 +10.7**. Since `Re(Z)` there swings −17 → +17 *with amplitude*, most of that ordering is the amplitude confound — but **V112 and V122 are amplitude-matched (A 1.85 vs 1.69) and 22 points apart**, so not all of it is. ⚠ **n = 51 windows each, one route per build: a screen.** If it holds, **V122 — the build on the car — damps the grinding band where its three predecessors pumped it.**
> ➕ Reader: `rlog-tools/score/antidamping_by_build.py`.

> 🛑🛑⭐⭐⭐⭐⭐ **RETRACTED WITHIN THE HOUR BY ITS OWN CONTROL — “A PROTECTIVE DAMPING TERM RUNNING OUT” WAS MOSTLY REGRESSION DILUTION. WHAT SURVIVES IS BETTER AIMED: THE 6–9 Hz ANTI-DAMPING IS *LINEAR*, AND THE REAL NONLINEARITY IS AT 22–30 Hz.**
>
> The decile shape (`Re(Z)` −23 → −65 with amplitude) has an alternative explanation I should have tested before writing a mechanism onto it: **at small A the SNR is low, and `Re(Z) = CSD/PSD` is biased toward zero when the estimate is noisy.** Coherence per decile settles it:
> ```
>   6-9.5 Hz   coherence 0.292 -> 0.908 as A rises      rho(A,coh) +0.569
>              rho(A, Re(Z))  ALL windows        -0.406
>              rho(A, Re(Z))  HIGH-COHERENCE half -0.192      <- halved
>              within high-coherence: low-A -54.6 vs high-A -57.8   <- essentially FLAT
>
>   22-30 Hz   within high-coherence: low-A -16.9 vs high-A +17.3   <- SURVIVES, and it is huge
> ```
> 🛑 **WITHDRAWN:** *“a Coulomb-like protective term of ~10.5 that runs out by ~2 °/s.”* Once measurement quality is controlled the 6–9 Hz anti-damping barely moves with amplitude — **−54.6 to −57.8 across the whole range, a 6 % change against the 180 % the uncontrolled deciles showed.** The `D(A)` table was reading noise.
> ✅ **[EVIDENCE] WHAT SURVIVES, AND IT IS SHARPER THAN WHAT I RETRACTED:**
> **1. The 6–9 Hz anti-damping is AMPLITUDE-INDEPENDENT ⇒ it is LINEAR.** Engagement adds a roughly constant **≈ −56** at the ratchet (against **−0.81** manual, 31/31 routes). A constant `Re(Z) < 0` is a *linear* negative damper, not a nonlinearity.
> **2. THE GENUINE NONLINEARITY IS AT 22–30 Hz — the GRINDING band, not the ratchet.** There `Re(Z)` flips sign with amplitude, **−16.9 → +17.3**, and that survives the coherence control (rho +0.593 within the high-coherence half). **Small oscillations there are PUMPED; large ones are DAMPED.**
> ⇒ **AND THIS RE-OPENS THE ARC'S CENTRAL PROHIBITION.** *“No LINEAR lane is the source, so the ratchet is nonlinear”* was the reason the linear-lane census was closed. **The ratchet now measures as linear**, and the lane phases that closed that census came from the **rectified** 427 channel, which cannot carry phase. ⇒ **a linear lane may well be the source, and the ban on notching 6–10 Hz rests on the same suspect measurement.** ⚠ Not licence to build — licence to *re-measure the lane signs on a non-rectified channel*, which is the next step.
> ⚠ **Three readings of this data in one session — “source”, “damper”, “running out” — and the controls killed the first two and now the third.** The lesson is in `feedback-`: **compute the control BEFORE writing the mechanism**, not after.
> ➕ Reader: `rlog-tools/score/ratchet_damping_runs_out.py`, now carrying the coherence control and the retraction.
> ⭐ **Nothing on the shelf moves. V241 stays the flight candidate.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE RATCHET IS A PROTECTIVE DAMPING TERM *RUNNING OUT*, NOT A SOURCE SWITCHING ON — AND THAT INVERTS THE DIRECTION OF EVERY LEVER THIS ARC HAS TRIED.**
>
> Binning engaged 2 s windows by **A = the 6–9.5 Hz oscillation amplitude of `cs_rate`** (°/s) and reporting the **signed** median `Re(Z)` per decile — every window kept, no sign selection:
> ```
>   6-9.5 Hz   A 0.25 -> -23.3   A 0.98 -> -58.6   A 3.73 -> -64.9   A 8.39 -> -62.0   rho -0.406
>   22-30 Hz   A 0.30 ->  -6.2   A 1.13 -> + 1.4   A 5.35 -> +12.9   A 14.4 -> +16.1   rho +0.668
> ```
> ✅ **[EVIDENCE] THE TWO BANDS MOVE IN OPPOSITE DIRECTIONS** (p 8e-300 and p ~0, 7,603 windows each). **No method artefact — filter leakage, the ratio form, driver grip, speed — moves two bands opposite ways.** The amplitude dependence is real and band-specific.
> ✅ **[EVIDENCE] THE COULOMB RELAY IS RULED OUT AS THE SOURCE.** A relay's describing function `N(A) = 4F/(πA)` makes its contribution **fall as 1/A**, so a relay source must WEAKEN with amplitude. **The anti-damping STRENGTHENS** (−23 → −65) and then plateaus. That is the opposite signature, and it retires the arc's standing nonlinear candidate.
> ⚖ **[BELIEF — consistent with the deciles, not the only reading] `Re(Z)(A) = −65 + D(A)/A`:**
> ```
>   A      0.245  0.353  0.454  0.573  0.743  0.983  1.359  2.061  3.732
>   D(A)    10.2   10.9   10.7    8.2    8.5    6.3    6.1    3.5    0.4
> ```
> `D` is roughly **CONSTANT (~10.5) below A ≈ 0.5** — a **COULOMB-like** term, a *force* not a viscosity, since a viscous damper would give `D ∝ A` — and it **decays to nothing by A ≈ 2–4 °/s**, which sits inside the record's own **1–13 °/s** ratchet regime. ⇒ a **fixed −65 anti-damper that is MASKED at small amplitude by a protective term, and exposed once that term runs out.**
> ⭐⭐ **WHY THIS MATTERS: THE FIX IS TO *ADD* DAMPING AT 6–9 Hz, NOT CUT IT.** Every lever this arc has tried **cuts** that band — which is what the standing rule forbids and what condemned V238 and V240. **Extending the protective term never touches that wall.** It is the first direction found that is not blocked by it.
> 🛑 **NOT DONE — WHICH CAL SETS THAT TERM.** The friction-lane saturation is **NOT** it: that one saturates at **250 counts** of `gp-0x6abc` and is **1.0× identical in the ratchet regime** by its own table. **Nothing should be built until the cell is identified** — this is a mechanism, not yet a lever.
> ➕ Readers: `rlog-tools/score/ratchet_damping_runs_out.py` (the decile shape) and `relay_describing_function.py` (the log-log fit — ⚠ it regresses only `Re(Z)<0` windows, a selection; the decile reader supersedes it).
> ⭐ **Nothing on the shelf moves. V241 stays the flight candidate.**

> ⭐⭐⭐⭐⭐ **THE 6–9 Hz ANTI-DAMPING REPLICATES ON NON-RECTIFIED INSTRUMENTS — UNANIMOUSLY. THE RECTIFICATION DOUBT IS SETTLED FOR THE *SYSTEM* SIGN, AND STILL OPEN FOR THE *LANE* SIGN.**
>
> `tq` and `cs_rate` never pass through `FUN_00055d80`, so `Z = CSD(rate,tq)/PSD(rate)` is immune to the doubt that hangs over every 427-derived phase:
> ```
>   ENGAGED  Re(Z) 6-9 Hz : median -58.20    negative on 31 of 31 routes
>   MANUAL   Re(Z) 6-9 Hz : median  -0.81    negative on 13 of 25  (a coin flip)
>   ENGAGED - MANUAL      : median -56.38    more negative on 25 of 25, p = 0.0000
>   control 22-30 Hz eng  : POSITIVE +8..+17 on nearly every route
> ```
> ✅ **Engagement injects anti-damping at 6–9 Hz while the 22–30 Hz control stays POSITIVE** — band-specific, so not a sign error and not a broadband artefact. This **replicates** the record's own *“the 6–9 Hz anti-damping is HONDA'S; at 22–26 Hz we REVERSE the sign”*, now on instruments the rectification cannot touch.
> 🛑 **AND IT DOES NOT LICENSE A 6–10 Hz NOTCH — I checked, because it looked like it did.** System-level `Re(Z)` and per-lane phase are **different objects**. The record already holds *both* *“the system is anti-damped at 6–9 Hz”* and *“every tapped lane damps at 6–9 Hz”*, and **their coexistence is exactly what forces the source to be NONLINEAR**: no combination of damping linear lanes can produce an anti-damped system. That points back at the **command-proportional Coulomb relay**, which is already de-relayed to 16.75 % duty on the car.
> ⚠ Manual-arm coherence is low (0.06–0.23 vs the engaged arm's 0.4–0.9), so the paired contrast is carried by the engaged side. Not speed-matched.
> ➕ Reader: `rlog-tools/score/rez_nonrectified_replication.py`. **Nothing on the shelf moves: V241 stays the flight candidate, V238/V240 stay costed.**

> 🛑🛑⭐⭐⭐⭐⭐ **THE SETTLED POSITION ON `gp-0x6b86`, AFTER TWO WRONG HEADLINES IN ONE TICK: ITS ENERGY IS KNOWN, ITS SIGN IS NOT — AND THE SIGN IS THE WHOLE QUESTION.**
>
> Rectification (`FUN_00055d80` clamps 427 to `[0, 0x3ff]`) is **asymmetric in what it destroys**, and that asymmetry decides which claims survive:
> ```
>   ENERGY at f0   -> RECOVERABLE, it reappears at 2f0     => the ranking is SOUND
>   PHASE  at f0   -> DESTROYED outright                   => the sign is NOT MEASURED
> ```
> ✅ **WHAT IS ESTABLISHED:** `gp-0x6b86` carries the most ratchet-band energy of every lane 427 ever flew — complete separation over **4 lanes and 8 routes**, the four losers clustered at baseline (1.75–2.11) and `gp-0x6b86` apart at 2.94–5.36.
> 🛑 **WHAT IS NOT:** whether that lane **damps or pumps** at 6–9 Hz. I first called it the ratchet's source, then corrected to *“a damper we must not cut”* on the strength of `cos −0.918 / −0.989 / −0.629`. **Both overreached: that phase was measured ON THE RECTIFIED CHANNEL**, which is the exact doubt the drive card already flags. **Neither reading is established.**
> ⚠ **AND THE DOUBT IS NOT LOCAL TO ONE LANE.** *“Every tapped lane damps at the ratchet — 13 routes, 7 taps, all negative at 6–9 Hz”* is the claim that closes the linear-lane census **and** condemns V238/V240. If those signs came from 427, they are **suspect together**, and the arc's central wall — *“the one band worth filtering is the one band that must not be filtered”* — rests on them.
> ⇒ **THE ONE MEASUREMENT THAT SETTLES IT, and the data is already on disk:** take the phase between **two NON-rectified instruments** — the torque sensor `tq` and the **IMU** (independent of the EPS entirely, and already shown to see the ratchet, 9/10 routes, p 0.0215). **No probe, no build, no drive.** That is the next tick.
> ⭐ **NOTHING ON THE SHELF MOVES ON THIS.** V241 stays the flight candidate; V238/V240 stay costed until the sign is measured rather than inherited.

> 🛑🛑⭐⭐⭐⭐ **`gp-0x6b86` CARRIES THE MOST RATCHET-BAND ENERGY OF EVERY LANE 427 EVER FLEW — BUT THAT IS *NOT* “THE RATCHET'S LANE”, AND I HEADLINED IT WRONGLY BEFORE CHECKING THE PHASE THE RECORD ALREADY HELD.**
>
> The **measurement** stands and is clean. The **causal reading I hung on it does not**, and the discriminator was already in this file: **`gp-0x6b86`'s measured phase at 6–9 Hz is cos −0.918 / −0.989 / −0.629, 3/3 routes — the lane is DAMPING there, not pumping.** A *source* shows cos > 0. ⇒ **the lane with the most 2f₀ energy is the lane RESPONDING hardest to the ratchet, not the one causing it** — which is precisely why cutting it condemned V238 and V240.
> ⇒ **What the ranking actually establishes:** of every lane 427 has flown, `gp-0x6b86` is where the ratchet is most VISIBLE. That is a good instrument and a bad target. It is consistent with — not a correction to — the standing result that **every tapped lane damps at the ratchet, so no LINEAR lane is the source.**
>
> CAN 427 carried a **different lane per build**, so the corpus is a natural experiment. Reading the clamped channel at **2f₀** (where a rectified 7.8 Hz oscillation lands), as a **local excess within the engaged arm**:
> ```
>   lane         routes   median   per route
>   gp-0x6b86         3    3.288   ra4 3.29, ra5 5.36, ra6 2.94
>   gp-0x6c2c         1    1.944   r1e 1.94
>   gp-0x6b94         2    1.931   r85 2.11, r95 1.75
>   gp-0x6b4c         2    1.849   r96 1.82, r9e 1.88
> ```
> ✅ **[EVIDENCE] ALL THREE `gp-0x6b86` ROUTES SIT ABOVE ALL FIVE ROUTES OF THE OTHER THREE LANES — complete separation over 4 lanes and 8 routes.** And the split is **bimodal**: the four losing lanes cluster tightly at **1.75–2.11** — baseline, essentially no local 2f₀ line at all — while `gp-0x6b86` stands apart at **2.94–5.36**.
> ⭐ **STRENGTHENED, by correcting my own blocker.** The first pass asserted *“rlogs stop at route a6, so `gp-0x6c2c` / `gp-0x6abc` / `gp-0x6b4e` cannot be ranked.”* **`r1e` (V107) carries `mag427` on `gp-0x6c2c` with 989 s engaged — the BEST-POWERED ROUTE IN THE CORPUS** — and adding it did not overturn the result. `gp-0x6abc` (r21/r22/r24) genuinely has no decoded `mag427`, and `gp-0x6b4e` has no cache; those two stay unrankable.
> 🛑 **AND THE FIRST VERSION OF THIS RANKING WAS WRONG, KILLED BY ITS OWN CONTROL.** Using the engaged/manual ratio, `gp-0x6b4c` came top at **300–377×** — and the denominator check showed why: **it is nonzero on 0.354 % / 0.273 % of MANUAL frames.** The lane is simply *dead when not engaged*, so the ratio was a division by noise measuring liveness, not ratchet energy. Switching to a **local excess within the engaged arm** removes the confound entirely — and `gp-0x6b4c` then ranks **last**.
> ⊕ **A second correction, on the lane's IDENTITY: `gp-0x6b86` IS NOT THE ASSIST-MAP LANE — IT IS THE OUTPUT OF THE BIQUAD LANE**, i.e. **the lane the entire V172→V241 notch arc has been shaping.** The facade's own chain:
> ```
>   ... -> biquad H(z) -> float clamp +-12.0 -> x1024
>       -> + gp-0x6b7e   (UNFILTERED pedestal, NOT scaled by c4)
>       -> clamp +-0x3000 -> gp-0x6b86 -> FUN_0003aa2c aggregator
> ```
> ✅ **THE GOOD NEWS: THE NOTCH IS IN THE RIGHT LANE.** The ratchet is not somewhere the kit's main instrument cannot reach — it rides the exact lane the notch sits in. That is the opposite of a dead end.
> 🛑 **THE BAD NEWS, AND IT EXPLAINS THE ARC'S CENTRAL FAILURE: `gp-0x6b7e` IS ADDED AFTER THE BIQUAD — AN UNFILTERED BYPASS AROUND THE NOTCH.** Whatever rides the pedestal reaches the aggregator with **no filtering at all**, at any notch aiming. That is why every notch build moved grinding and **none moved the ratchet**, and it is a mechanism, not a coincidence.
> 🛑 **AND THE PEDESTAL IS NOT A FREE TARGET EITHER — I re-derived it wrongly mid-tick and the record had it right.** It is not a parallel path carrying its own copy of the signal; it is the term that **UNDOES the slew limiter's cut**: `out(f) = table2 + H_k(f)·(table1 − table2)`. The 0.197 at 7.79 Hz is *the fraction of the cut undone*, not a path ratio. Its cell is `0xC6906` = **V238**, already built and already **costed at ~3.8 % of the lane** — right conclusion, wrong reasoning, now fixed.
> ⇒ **THE BIND IS UNCHANGED AND IT IS THE ARC'S REAL WALL:** every device in this lane acts at 6–9 Hz by *cutting* it, and at 6–9 Hz this lane is a **damper we need**. **The one band worth filtering is the one band that must not be filtered.** Nothing found this tick moves that.
> ⚠ **LIMITS, all real:** build and 427-source are **perfectly confounded** — each lane is seen only on the builds that probed it. 3 vs 2 vs 2 routes. And **rlogs stop at route a6**, so the three lanes V107+ put on 427 (`gp-0x6c2c`, `gp-0x6abc`, `gp-0x6b4e`) cannot be ranked at all — one of them could rank higher still.
> ➕ Readers: `rlog-tools/score/rank_lanes_by_ratchet_energy.py` (the engaged/manual version, kept with its confound documented) and the liveness-free local-excess version.

> ⭐⭐⭐⭐⭐ **THE CLAMPED 427 CHANNEL IS NOT USELESS AFTER ALL — READ IT AT 2f₀. THE LANE-RANKING BLOCKER IS REMOVED, AND IT WAS REMOVED BY A FIX MADE THIS SESSION.**
>
> Re-auditing the four lanes I called *“spoken for”* after V245 showed one of them was not. **Two closures are sound:** the base-assist damper is a **product of five Q10 gains with two exactly zero at creep**, so scaling any of them is structurally vacuous (even the untried `FactorC X[0]` edit reaches **0.096 %** of full gain); and `0xC40D2`'s Coulomb slope would need `k1 = 25600`, **25× past the boundary where its sign inverts**. Those stay closed.
> 🛑 **BUT ONE CLOSURE NAMED ITS OWN BLOCKER, AND I REMOVED IT THIS SESSION:** *“427 lane ranking — not possible from the existing caches … **would need re-extraction from the rlogs**.”* The `extract/` toolchain was **dead since the 2026-08-26 reorg** and is now fixed — and **every rlog for the 427-era routes is on disk** (r95, r96, r9e, ra4–ra6, r77–r79, r7d).
> ⭐ **AND THE RECTIFICATION IS NOT FATAL EITHER.** `FUN_00055d80` clamps the field to `[0, 0x3ff]`, which destroys **phase** — but a rectified narrowband signal at `f₀` puts its energy at **2f₀**. Tested on the three routes carrying `mag427`, engaged/manual power ratio:
> ```
>   route   eng s    7.8 Hz   15.6 Hz   2f0/f0
>   ra4       663     7.178    37.217    5.185
>   ra5       485     5.361    30.256    5.644
>   ra6      1225     0.744     2.414    3.244
> ```
> **The 2f₀ excess is 3.2–5.6× the f₀ one on every route — the rectification signature, unambiguous.** ⇒ **the lane's ratchet-band ENERGY is recoverable from the clamped channel.** Phase is gone (the sign finding stands); energy is not.
> ⇒ **THE CONCRETE NEXT STEP, now unblocked:** 427 carried a **different lane per build** — `V104 gp-0x6b86 · V107 gp-0x6c2c · V112/V122 gp-0x6abc · V212–V220 gp-0x6b4e`. Re-extract `mag427` for those routes and rank the lanes by 2f₀ energy. **That answers “which lane carries the ratchet” — the question this whole arc has failed to answer — from data already on disk.**
> ⊕ **Still open:** `gp-0x6bbe`'s weight `0xC63A2` is a **virgin single-reader cal**, and its closure (*“the lane is already at 76 % of its ±512 rail”*) is a **caution, not a proof of vacuity** — 76 % is not 100 %, and whether that is a p50 or a peak was never stated.

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


## 📁 **EARLIER BLOCKS (24) ARCHIVED 2026-08-30**

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
