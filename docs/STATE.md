# STATE — living current state of the kit

## 🛑🛑 LATEST BLOCK, 2026-08-21 (late) — **V104 BUILT, UNFLASHED. `c4` IS A FLAT LANE GAIN AND IT IS VIRGIN.**

🛑 **ON THE CAR: V103, unchanged. NOTHING WAS FLASHED; NO CAN OR UDS WAS SENT.**
**V104 exists as an unflashed artifact.** Full narrative — every finding including the negative ones,
**17 retractions**, 15 open items with what closes each:
**`docs/HANDOFF-2026-08-21-v104-built-c4-boost-and-lever-b.md`.** Read it before proposing anything.

### V104 — three levers, 16 bytes, no cave change
| artifact | SHA256 |
|---|---|
| `_v104_…-427.6B86.SAR4_plain_image.bin` | `b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03` |
| `39990-TVA,A160-V104-…-0x13000-0x100000.rwd` | `41e707121cf86d8fc8d8c27f98fa722632858466ebbce952a4adcf7234fd4fa2` |

| addr | V103 → V104 | what |
|---|---|---|
| `0xC60B4` | `3a3b513f` → `fc89c13f` (0.81731 → 1.51202, **×1.850**) | the dormant biquad's overall gain `c4` — **a flat scalar on the torque-sensor assist lane, engaged-only** |
| `0x3AA96` · `0xC6446` | `c5`→`fb` · 512→5244 | **LEVER B RESTORED** — off the car since V101 |
| `0x55DF2` · `0x55E10` | `b4`→`7a` · `a6`→`a4` | CAN 427 → `gp-0x6b86`, `sar 4` — **the dose instrument** |

Cave **byte-identical to V103** (164 B). 119/119 assertions, 3 runs identical, SHAs hard-asserted in
the script. Hashes and byte diff **re-verified from disk by the orchestrator**, not from the builder.

### ⭐ THE LEVER — and why it is not a repeat
**`0xC60A8/AC/B0/B4` are byte-stock in ALL 73 built images V38→V103.** `c4` has **never been proposed,
priced or killed**. Both prior biquad refusals relocated the **poles**; this moves only the **gain**,
so every objection to them (pole phase, the 12–14 Hz peak, the engagement ring) evaporates.
`c4` is a **pure flat scalar**: one reader image-wide, pcode-confirmed, **zero added phase at any
frequency**, engagement transient 20.25 ms and constant across dose.
🛑 **It is a BROADBAND ×1.85 LANE RAISE, not "the 6–9 Hz lever."** At fs = 1000 the null is at
**55.23 Hz**, `|H| < 1` only on **36.8–82.2 Hz**, and the ratio is a **flat 1.8500 everywhere**.
`|H| ≥ 1` on **90.9 %** of the axis.

### 🛑 THE DOSE-RESPONSE IS INVERTED — under-dosing is the dangerous end
`A(k) = A₀ + (k−1)·c·L` is a **straight line**; closest approach to the origin is **k = 0.83, a CUT**.
Exact Möbius `Z(k) = Z(1)·A(1)/A(k)` (the first-order proxy is invalid — `ΔG` is 93 % of `|G₀|`):
**k = 1.05 → one corner 4.26× WORSE** · k = 1.26 → anti-damping zeroed · **k = 1.85 → amp 0.30×, and
NOT ONE of 204,000 joint-uncertainty corners is worse.** On the **measured** `a` the `Re Z` crossing is
at **k = 1.545**, so **k = 1.35 would not have cleared it.** ⇒ **This inverts how the kit has sized
every lever for sixty builds.**

### ⭐⭐ TWO MEASUREMENTS THAT MADE IT POSSIBLE
1. **V102→V103 IS A CLEAN SINGLE-VARIABLE PAIR** — 55 bytes, coefficients/gain/Levers A,B all
   identical. **Arming the filter is the same kind of perturbation a `c4` edit makes.** Inverting it:
   **`a_filt = 0.0457`, Im/Re residual **−3.1 %** (a free check it could have failed).
   ⚠ **CI [−0.0047, +0.0816] INCLUDES ZERO** (P(a>0) = 0.957, ~2σ), **four** transport assumptions.
   🛑 `a_filt` is the **as-flown duty-weighted sensitivity of the SUM to a change in `H`** — the correct
   coefficient for pricing `c4` **by construction**. **It is NOT the ROM map slope.**
2. **THE ASSIST MAP, READ FROM ROM AND VALIDATED 200/200** against V72's flown probe (87,940 frames).
   `0xC7B40` is a **pointer array indexed by the MODE NUMBER**. 🛑 **The axis assignment is the opposite
   of the obvious one** — `gp-0x373c`/`gp-0x3714` are the map's *inputs*; a second transform swaps the
   roles. The swapped reading predicts **10,293 vs the measured 200 — 51.5× out.**
   ⇒ **`a` = 0.069 pooled engaged**, speed-scheduled **0.123 parking → 0.046 at 120 km/h**. **The
   budget's 0.098/0.117 is high by 1.4×/1.7×** (the closure could not see the speed schedule).

### ✅ THE CLIP GATE IS CLOSED — the V80 relay mode is unreachable
`|gp-0x6b82| ≤ |gp-0x6b7a| ≤ 12288` proven at instruction level; the biquad **cannot amplify**
(zeros on the unit circle, peak `|H|` = 1.0000). **Engaged clip duty at k = 1.85 = 0.000000** — zero
frames in **1,704 s across five builds**, zero in **all 2,000 bootstrap resamples**, rigorous bound
clean to **k ≤ 3.40**, first clip at **k = 10.76**. **The clamp is SYMMETRIC ±12.0** (four
confirmations) — `movhi 0x4140` does double duty as compare constant *and* saturated output.

### 🛑 THE DERIVATIVE FIX IS STRUCTURALLY IMPOSSIBLE, CAL-ONLY
> **No cal-only site has an independently settable sign.** Every rate lane's sign is `pol`-tied or comes
> from an **unsigned** gain table — writing it negative zero-extends into a huge wrong-signed gain.
> **A property of the firmware's gain-table convention, not a per-lane accident.**

**`gp-0x6bbe` reversed to "already a `−K·(column rate)` damper"** (a second `pol` load cancels the
first) and **`K1` IS signed** ⇒ a real two-way lever — but **DEAD ON HEADROOM**: flat ±512 bound,
**already at 76 % of rail**, usable dose ≤1.31× for a 3.8 % cut, and `1/|A|` gets *worse*.
**`gp-0x6ade` is a permanently-dead unit-weight aggregator slot** — the cleanest cave target found.

### 🛑 `f0` IS THE WRONG ENDPOINT FOR ANY FLAT-GAIN LEVER — structurally
**`f0` is a ZERO CROSSING of `Re(Z)`. A pure gain change SCALES `Z`, and scaling cannot move a zero —
only PHASE can.** Predicted `|Δf0| < 0.01 Hz at every k` vs a ±1.05 Hz floor: **dead by ~100×.**
Choosing it would have manufactured a guaranteed null (the V97 failure).

### PRE-REGISTERED READOUTS (full text in the handoff §6)
- **Endpoint 0 — dose delivered:** 427 6–9 Hz ratio vs `0x9e`. **PASS [1.50, 1.70]** · ARM-FAIL ≈1.00.
  🛑 **DO NOT PRE-REGISTER 1.85** — the slot carries Honda's own `abs()`, which reads a true 1.85 as
  **1.603**. ⭐ Not confounded: **`k` is BINARY** (one cal in a CRC block ⇒ no half-failed arm).
- **Endpoint 1 — Lever B, separately attributable:** 21.0–22.5 Hz band RMS, **ONE ≥15 s engaged block
  HELD AT 50–80 km/h — the speed band is part of the pre-registration.** LR 14.1:1 held vs **3.3:1**
  unheld. 🛑 **22–26 Hz is NOT clean** (c4 moves it 0.893). ⚠ `c4`'s inertness at 21–22.5 reflects
  **model INSENSITIVITY** (`|A|` = 0.990), not confidence.
- **Endpoint 2 — 6–9 Hz `Re(Z)`, unattributable but diagnostic:** ⭐ **`Re Z ≤ −3784` has P ≤ 0.030
  under EVERY hypothesis in which either lever works ⇒ it falsifies the `|κG| = 0.630 / A = 0.440`
  identification WITHOUT needing attribution.**

### 🛑 A LATENT DATA DEFECT — AUDITED AND GUARDED
**`x6b94` is a byte-identical ALIAS of `x6b4c` (the LANE) in `_cache_r96`, `_cache_r97`, `_cache_r9e`.**
Only `r85`/`r95` carry the real sum. ⚠ **`r97` is the STOCK baseline and was not in the original
report.** **Same error class that made GATE2's notch dose 4× too large.** Guard shipped:
`analysis-2020accord/check_427_alias.py`. ⊕ `damp_nz`/`g6ac2` are **stale decodes on V100+ routes**.

### 🛑 THE FACT THAT OUTRANKS THE PHYSICS
Operator on **stock** (688.8 s engaged): ***"No vibration or grinding. Maybe ever so slightly, barely
perceptible ratcheting."*** On **V102 (6×)**: ***"Vibration and grinding somewhere between 4× and 8×.
Ratcheting was bad."*** **The symptoms track `0xC6CD0` monotonically across four operator-scored doses.
They are OURS.** And **Lever B fixed grinding on V88 but did NOT move ratcheting** (1.040
[0.759,1.260]). **Nothing in sixty builds has moved ratcheting.**

### 🛑 V101/V102/V103 ALL CARRIED NEITHER GRIND-#1 FIX
`0x3AA96 = c5`, `0xC6446 = 512` — **stock, through three grinding reports.** The V81/V87 defect
recurring unnoticed for three more builds. **V104 repairs it. Lever B is a REGRESSION REPAIR, not an
experiment** — its warrant is the road measurement (**0.40 [0.27, 0.58]**, operator: *"the audible
grinding is fixed"*), **not the model**, whose ranking of it was withdrawn (`ΔG` = 2.4× the whole loop
gain, outside validity).

### 🛑 `0x14A` HAS ZERO FREE BITS
byte4 **7:3** = V103's five passes; byte4 **2:0 are HONDA'S** (`gp-0x6799`/`gp-0x679b`/`gp-0x679a`,
written before the cave hook; V103's masks deliberately preserve them); byte7 5:0 Honda + 7:6 identity.
**A memory claiming {2,1,0} free caused a real V104 defect (a comparator that clobbered a live bus bit)
— cut, caught, reverted. Corrected in place.** A wider channel needs `0x18F`/`0x1AB` or displacing one
of V103's five.

---

## ⚠ SUPERSEDED BLOCK, 2026-08-21 (early) — **V103 FLEW (route `0x9e`). THE 8 Hz MODE IS THE *LOOP*, NOT THE PLANT.**
🛑 **Its "NOTHING WAS BUILT / no V104 artifact exists" line is STALE — V104 IS BUILT (unflashed).**
Its LOOP result and its three refusals STAND. Its dose sizing does NOT: `a` was later MEASURED from ROM
at **0.069**, not the **0.098** solved here. See the LATEST BLOCK above.


🛑 **ON THE CAR: V103.** It was flashed and driven as route `0x9e` — **the record below that says
"built, not flashed, decision deferred" was STALE and is corrected here.** Both symptoms failed: the
operator reports **grind #1 present** and **high-steer-rate ratcheting present**.
**NOTHING WAS BUILT OR FLASHED on 2026-08-21. No V104 artifact exists.**
**Full narrative: `docs/HANDOFF-2026-08-21-route9e-and-the-loop-is-the-cause.md`** — every finding
including the negative ones, and **17 open items with what closes each.** Read it before proposing
anything.

### ⭐⭐ THE RESULT — the loop is identified, and it IS the cause
From the 4×/8× gain steps (routes `0x85`/`0x95`, both packing the aggregator **SUM**):
`|κG| = 0.630 [0.512, 1.001]` · `A = 1+P = 0.440 ∠ +25.0°` · closed-loop amplification
**2.28× [1.51, 9.4]** · gain margin **1.2–1.6** · identified passive plant `Z₀ = 2792 ∠ −92.45°`,
`Re(Z₀)/|Z₀| = −0.043` — **a near-lossless spring.**
⇒ 🛑 **100 % of the measured `Re(Z) = −3761` at 6–9 Hz is LOOP-GENERATED.** The ratchet is the assist
loop's own near-instability, **not** a mechanical resonance being excited.
⚠ **PROVISIONAL — the pair is CONFOUNDED:** route `0x85` (V100) has `0x3AA96 = fb` ARMED /
`0xC6446 = 5244`; route `0x95` (V101) has `c5` DEAD / 512. **The rate lane is one of the two things
that changed. This kit has NEVER flown two builds differing only in `0xC6CD0`.**

### 🛑 THE LAW — supersedes every 6–9 Hz sizing argument in this file
> **At 6–9 Hz the aggregator is a 4:1 near-CANCELLATION — individual lanes are LARGER than their sum
> (`coh²(T,sum)` = 0.279 vs `coh²(T,lane)` = 0.80–0.89). ANY single-lane perturbation is amplified
> ~4× at the output. SIZE EVERY 6–9 Hz LEVER AGAINST THE SUM (0.053), NEVER AGAINST A LANE.**

Band-specific (only 1.68 at 21.0–22.5 Hz). **This retroactively explains why sixty builds of
lane-sized doses produced nothing or the opposite of what was predicted.**
Sizing: `ΔP = c·ΔG`, `|c| = 13.09`. **`ΔG = 0.047` takes `|A|` 0.44 → 0.87.** A lane-sized dose is
**~4× over**; a **wrong sign** drives `|A|` to 0.15 — a **6.7× amplification.**

### 🛑 THREE LEVERS PRICED, ALL THREE REFUSED — do not re-propose without new evidence
| lever | verdict |
|---|---|
| **Honda's biquad re-centred as a NOTCH** (`0xC60A8`–`B4`) | **DEAD.** `Re(u/T)` rises monotonically 6.0–9.5 Hz (2.08–2.37×); `ΔRe(Z)` = **−461…−3028** ⇒ MORE anti-damping. Flips only if `arg(Z) > −79.4°`; measured **[−117.6°, −126.3°]**. ⚠ The killer was a baseline error — `0.2075∠+39.7°` is the **LANE**; the SUM is `0.0485∠+17.0°`, so the correction was added to a baseline **4× too large**. |
| **Same cells as a resonant BOOST** | **DEAD, 3 ways.** (1) 21.7 Hz is a **cost** — `ΔG` is 67–77° from `u/T`, near quadrature, ratio 1.08–1.20. (2) A 2-pole section has **exactly −90° at its own pole** ⇒ `\|ΔH\| = 1.378` **larger than `\|H\|`**, `\|u\|` → **3.34×**, Nyquist encirclement at every `r`. (3) States freeze while disarmed ⇒ **1.2 cycles of 8 Hz ring at EVERY engagement.** Knife edge is **×1.98, not ×3.** |
| **RAISING r24/r26** | **REFUTED (c).** V71c's dose sits in (1.000, 1.707] for every `a` ⇒ **cannot have overshot**; for `a < 5.57` the model says **V88 is the worse build** — it is not. Identification swings **3.1×** on dropping 1 of 2 episodes. **ESCAPE HATCH OPEN: `a > 5.57` inverts it, and `a` has NEVER been measured.** |

🛑 **AND A CORRECTION THE KIT OWES ITSELF:** *"V71c was the worst build ever on all three symptoms"* is
a **BAND statement, not the operator's.** **His words: "attenuated but still present", and he ranked
V71c ABOVE V71b.** `BUILD-LINEAGE.md:646` lists V71c among builds that **measurably moved grind #1**.

### ⭐ ROUTE `0x9e` — the largest clean capture the kit has (647.8 s, 406.4 s engaged, 7 episodes)
Fault-free, identity PASS (`b3` duty 0.4599, 32,494 transitions). **`f0` = 25.23 [24.88, 25.91]** vs
V102's 24.90 — **+0.33 Hz against a ±1.05 Hz split-half floor: a correctly-anticipated null**, and
V103's filter is **−0.149 dB at 7.79 Hz**, inert where the ratchet lives.
🛑 **Command-adjusted, the ENTIRE stock→V102 `f0` march disappears (24.896 vs 24.904).**
⇒ **`f0 ≈ 21.3 + 0.60·m` IS NOT A GAIN LAW. Retire it.**
- **Ratchet:** engaged/manual **24.29× [10.77, 48.37]** matched on speed AND rate; engaged 6–9 Hz RMS
  16→60→369→**490** with wheel rate while **manual is flat (33→29)**; coherence vs driver torque —
  assist sum **0.892**, openpilot command **0.237**, **IMU 0.000–0.002**.
- 🛑 **GRIND #1 IS THE 21.0–22.5 Hz SLICE, NOT 15–22 Hz.** At <10 km/h **77.3 %** of 15–22 power sits
  there. Line **21.73 Hz, prominence 39.18 vs null p95 3.07**, split-half stable, **absent in manual**;
  wheel order excluded (same 0.395 Hz bin at 5.6 and 12.8 km/h). Band ratio by speed: **5–10 km/h 9.88**
  · 10–20 4.37 · 20–40 2.23 · 40–70 3.52 · >70 2.91.
- ⭐ **THE OPERATOR'S OWN CLAIM, MEASURED:** *"applying torque kills the buzz"* — engaged, <20 km/h,
  rate ≥6 °/s: **425.1 hands-off vs 26.4 hands-on = 16.12× [5.29, 41.29]**, band-specific.
- **His 3-part grind hypothesis:** command scaling **SUPPORTED but narrowed** (slew limit 123 LSB/tick
  = **80.3 assist ct at 6×**, on the limit **39.5 %** of frames at 5–10 km/h — but grind tracks **wheel
  rate**, not the step) · return-to-centre **REFUTED in his regime** (0.0000/2,622 frames; lane live in
  89 of 87,316, **all MANUAL at |angle| 383–398°**) · road passthrough **REFUTED** (ratio-of-ratios
  **23.1× [7.9, 42.5]**; wheel-speed coherence 0.012, **below its own shuffle floor**).

### 🛑 THE GAIN CEILING IS A **STABILITY** PROBLEM, NOT A CLAMP PROBLEM
- **The 9× ceiling was OURS.** `0xC674E` has **exactly one reader** image-wide and **no instruction
  compares it to the clamp** — the assert is a kit convention. ⭐ **Keep it: it binds at 10×, the
  governor at 10.69×, so everything it forbids is authority the governor flattens anyway.**
- 🛑🛑 **RETRACTED 2026-08-21 — THERE IS NO FLAT 10.7× CEILING. The claim misread its own cited
  instruction.** It quoted `ld.hu -0x4f64,gp,r8` as evidence for `cal(0xC6202)` = 4762 — but that
  instruction reads **RAM**, not the cal. **The real governor bound is
  `bound = (gp-0x4f64 × channel5) >> 15`, then `clamp(aggregator_sum, ±bound)`** (`0x453f0`-`0x453fe`,
  `FUN_0004503c`) — **PROPORTIONAL and recomputed at runtime, not fixed.**
  ⚠ **`0xC6202`'s REAL role:** exactly **ONE reader in the whole image** (`0x7b06a`, inside
  `FUN_0007b022`, the `gp-0x4f64` **writer** — *not* the governor). It is a **Q10 scale factor**
  (÷1024 → 4.650390625) feeding the float computation that produces `gp-0x4f64`. **Its arithmetic
  effect if raised is GENUINELY UNKNOWN, not merely risky.** Same failure mode as `0xC6200`, which sat
  mislabelled by one of its four roles for ten builds. **Ledger correction:** the recorded
  *"`0xC6202/04/06/08` cluster at `0x045410`-`0x0457de`"* is **wrong for `0xC6202`** (that range holds
  `0xC6206`/`0xC6208` in `FUN_0004503c` and `0xC6204` in `FUN_000456a4`).
- ⭐⭐ **WHAT ACTUALLY LIMITS TORQUE — AND IT COLLAPSES WHERE WE WANT IT MOST.** `gp-0x4f64` is RAM,
  continuously recomputed from a **motor-electrical-rate-scheduled ROM table** (bank A, `0xC520C` +
  mirror `0xC5224`; bytes re-read this session: count 5, X = 1050/1700/2500/3700/4100,
  **Y = 5325 / 3584 / 2406 / 1587 / 512**, slopes at `0xC5030`).
  ⇒ **the ceiling swings 10.4× — 5325 at rest, 512 at high motor rate — i.e. it TIGHTENS exactly in the
  fast-correction regime more torque is wanted for.** At 16× (full scale 7128) the clip fraction is
  **~34 % at low motor rate but ~93 % at high motor rate.**
  🛑 **[BELIEF, TESTABLE, HIGH VALUE] real driving may ALREADY be saturating this at 6×** during fast
  corrections — which would mean part of the felt grinding is the assist hitting a ceiling and dropping
  out, not only a resonance. **Closes with a raw tap on `gp-0x6ac0` (motor electrical rate) +
  `gp-0x4f64` (the live ceiling). Put it in V104's telemetry.**
- ⭐ **THERE IS A RAISABLE LIMIT, AND IT HAS ALREADY FLOWN SAFELY.** Flattening bank A (`0xC520C` +
  mirror `0xC5224` → Y = 5325 flat, slopes → 0) removes the motor-rate throttling and holds the ceiling
  uniform. **This is V41's CHANGE 2 — cal-only, and V41 booted and drove cleanly.** It does not reach
  16×'s 7128 full scale, but it removes the collapse to 512. **Lowest-risk headroom lever found.**
  ⚠ **The fault-0x17 rejection does NOT reach it:** 0x17 trips on the two RAM mirrors **disagreeing
  between cycles**, never on the calibration value (`FUN_0006b9ee` → `FUN_0006ce7c(0x17)`, decompiled) —
  a bank-A edit keeping both mirror copies identical **cannot** trip it. The old rejection was attached
  to the wrong cell.
  🛑 **STAY AWAY FROM `0xC6206`/`0xC6208`** — V40 raised both to `0xFFFF`: EPS lamp, no power steering.
- ✅ **`gain ÷ 2` full-scale is UNCHANGED and still correct** — it is a different, earlier stage
  (`FUN_00028ea6`'s Q15 multiply, setpoint full scale 16384, 16384/32768 = 0.5 exactly). The withdrawn
  trace's error was **what it compared that against**, not the arithmetic itself.
- ⚠ **METHOD:** of 17 candidate accesses to `gp-0x4f64`, **6 (35 %) were FALSE POSITIVES** —
  base-register aliasing (`st.b r7,-0x4f64,r18`, base `r18` not `gp`) and coincidental byte patterns.
  **Scans find candidates; only the decoder settles them.**
- 🛑 **BUT STABILITY BINDS FIRST, AND IT WAS HIT AT 8×.** V101 had **13.0 % clamp and +25.2 % governor
  margin** and gave the worst report, with the **peak MOVING 20.3 → 23.0 Hz** — *a pole moving, not
  excitation.* `|κG|` 0.63@4× → 0.75@8×, extrapolating to **0.97–2.0 at 16×**.
  ⇒ **DAMPING IS THE PREREQUISITE FOR MORE GAIN, NOT A DETOUR.**

### V104 — SPECIFIED, NOT BUILT (`docs/SPEC-2026-08-20-v104.md`, rev 3)
**Gain FROZEN at 6×** per the operator's ruling (*"fix at 6x first, then raise to 8x"*; long-term target
is **16×**). An **instrument build, by conclusion not fallback** — no lever survived GATE 2.
**427 source → `gp-0x6b94`** (`0x55DF2`, 2 B, flown at V100) · **`|gp-0x6adc| ≥ |gp-0x6ada|` rung**
(measures `a`, closes the escape hatch) · **identity `0xC4BC0` `033a`→`013a`** (`byte7[7:6]==1 AND
b3==0` has **zero matches in 714,055 frames**) · telemetry cave.
🛑 **`0x55E10` STAYS `a6` (`sar 6`).** `sar 4` was sized for the LANE (1498); the repoint moves the
source to the SUM (10240) and **`sar 4` OVERFLOWS ×3.13.**
**Then V105 = V104 with ONLY the gain cell changed — the first de-confounded gain pair ever flown.**

### 🛑🛑 METHOD FINDING THAT OUTRANKS THE PHYSICS
**The `ld.bu` displacement's LOW BIT lives in `hw1` bit 5, not `hw2`.** `85 67 fb 74` →
`ld.bu 0x74fa,tp,r12` but `a5 7f fb 74` → `ld.bu 0x74fb,tp,r15` — **identical `hw2`**. The kit's rule
(*"`ld.bu` → `hw2 == enc|1`"*) is **WRONG** and has been **conflating ADJACENT CELLS**. `0xC64FA` has
**8** readers, not the recorded 18; the other **10 read `0xC64FB`**, uncharacterised. **Suspect every
prior byte-cell reader/writer count. Adjudicate with `disassemble_bytes`, never displacement bytes.**
⚠ Also: **`steeringPressed` IS `|cs_tq| > 1200`** (98.97 % agreement) ⇒ **every hands-on/off AMPLITUDE
contrast on `tq` is CIRCULAR.** And **a "zero writers" claim can be TRUE FOR STOCK AND FALSE FOR A
BUILD** (`gp-0x683c`: 0 writers stock, but V67+ repoint it to `gp-0x6806`, 15 writers).

---

## ⚠ SUPERSEDED BLOCK, 2026-08-20 (late) — **`f0` IS THE ENDPOINT. V103 BUILT. `gp-0x6752` = −1.**
🛑 **Its "V103 BUILT AND NOT FLASHED / STOCK on the car" status is STALE — V103 FLEW as route `0x9e`.**
Its measurements stand; its flight-status rows and its `f0`-as-a-gain-law framing do not.

⚠⚠ **STALE AS OF 2026-08-21 — THIS PARAGRAPH IS SUPERSEDED. V103 WAS FLASHED AND FLEW AS ROUTE `0x9e`.
ON THE CAR: V103.** See the LATEST BLOCK at the head of this file. The two sentences below describe the
state as of 2026-08-20 only, and are retained as history.
~~**ON THE CAR: STOCK (V9b).** He flashed V102, drove route `0x96`, then flashed stock and drove
route `0x97`. **V103 is BUILT AND NOT FLASHED — and the operator has deferred the decision on it.**~~
**Full narrative: `docs/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md`** — it carries **every** finding
(including the negative ones) and **36 open items**, per standing instruction. Read it before proposing
anything.

### THE FOUR THINGS THAT CHANGED
1. 🛑 **`gp-0x6752` = −1, NOT +1.** A second writer (`FUN_00048a40`) overwrites the pre-seed from a boot
   config record at flash `0x14C0`, below every `.rwd`'s `0x13000` floor. **Verified three ways**
   (orchestrator, an independent agent, and V98's own on-car comparator at duty 0.0000 / 5 routes).
   ⇒ **D pumps, P and I damp, net PID damps at 6–9 Hz** — GATE2's original headline, on a verified
   footing. ⇒ **r24/r26 PUMPS at 6–9 Hz (−431…−1294 ct).** ⚠ **V49 was gated on this with "brick if −1"
   and was never flashed — that caution was correct.**
2. ⭐ **THE ENDPOINT IS NOW `f0`**, the `Re(Z)` zero-crossing: **21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×,
   CIs disjoint, `f0 ≈ 21.3 + 0.60 × m`.** Anti-damping is a **REGION** from ≤16 Hz to `f0` on **every**
   arm including stock. **It needs NO symptomatic driving** — the negative margin is **standing**, not
   burst-conditional. **~100 s hands-off at 30–85 km/h; above 85 km/h contributes nothing.**
3. ⭐ **THE ANTI-DAMPING AT 6–9 Hz IS HONDA'S** (stock −1297/−1709/−1507); we multiply it 2.4–3.0× below
   86 km/h. **But at 22–26 Hz we REVERSE THE SIGN** (stock +247/+496 → V102 −134/−99, disjoint) — the only
   band where our firmware flips sign rather than size, and it is the vibration band.
4. 🛑🛑 **AND THE GAIN ATTRIBUTION IS NOW IN DOUBT.** `f0` moves **−0.99 Hz with COMMAND AMPLITUDE at
   FIXED gain**, and openpilot commands **4.7× harder on stock** (465 / 253 / 98). Pooled, **the gain term
   goes non-significant (+30 [−99,+159], ΔR² = 0.0009).** ⇒ **[BELIEF] most of the march this kit
   attributed to `0xC6CD0` may be openpilot winding up on a weaker car.** **MANDATORY from V103 onward:
   report median `|0x0E4|` alongside `f0`.**

⭐ **RECOMMENDED NEXT ACTION — one drive, no build, no flash** (three agents converged on it): 3–5 min
MANUAL at 50–110 km/h (decides whether the engagement relay is Honda's or ours) **plus** ~100 s
high-command vs ~100 s low-command, hands-off, 30–85 km/h (decides whether `f0` tracks gain or command).
**One ~15-minute outing retires two open items with zero flash risk.**

⚠ **SUPERSEDED BELOW:** the *"8× gain is the carrier"* block is retained for its measurements, but its
**attribution is now contested by item 4**, and its band-RMS ratios are **~2× inflated** — hands-on is a
mandatory third matching axis (arms range 4.7 %–40.3 %). See handoff §4.5.

**Full narrative: `docs/HANDOFF-2026-08-20-v102-the-gain-is-the-carrier.md`.** Read it before
proposing anything — it kills nine levers and corrects twelve things in this kit's own record.

### THE RESULT
**V101's 8× LKAS gain (`0xC6CD0` = 7128) is the SOLE MEASURED CAUSE of the ~23 Hz vibration the
operator reported at all speeds.** De-confounded 2×2 against route `71` (V87 = 4×, Lever B already
dead), in **shape units against a measured placebo floor of 1.45×**:
**gain G = 2.7–3.9× · Lever B = 0.84–1.30× (INSIDE the floor) · `0xCBE74` k = 0.86–0.90 (inert).**
The peak **MOVED**: 20.3 Hz on three separate 4× routes → **23.0 Hz** on V101 ⇒ a **pole moved**.
The line is **in the firmware's own demand** (`gp-0x6b94` 21–24 Hz shape 1.71× [1.33,2.29]) with the
**aggregator's sign reversing 25–37 /s at amplitudes where V100 reverses 0.7–3.2** (re-weighted
excess 3.06× ⇒ **not** quantisation; internal control b4 flat at 1.24×).
🛑 **NO firmware clamp binds anywhere** — `b6` duty **0.000000** over 17,614 engaged frames with all
four positive controls passing; the setpoint is LERP-clipped to 15360 **upstream** of the gain so
`0xC61B2`/`0xC61B4` sit at **81.5 % of rail on every build since V14**. The only saturating element
is **openpilot's own ±4096 rail, ~12 % duty on BOTH builds**.
🛑 **NOT a limit cycle** — growth σ inside a phase-randomised surrogate null (1.13/0.91), kurtosis
3.85/3.38. A **very lightly damped resonance**, consistent with there being no amplitude-setting
saturation inside the ECU.

### V102 — BUILT, NOT FLASHED
`build_v102_tva.py`, **three cells on a V101 base**, dose chosen by the operator from a measured
dose-response curve: **`0xC6CD0` 7128→5346 (8×→6×)**, `0xC61B2`/`0xC61B4` **4096→3072** (tracking,
`5346×512//891 = 3072` exact) + a **154 B two-comparator cave** + **427 repointed to `gp-0x6b4c`**.
**Lever B stays REMOVED** (`0x3AA96`=0xC5, `0xC6446`=512) and **`0xC40D2` stays at 204**, instrumented
by the new b5 comparator but **not dosed** (its endpoint failed a power test at every exposure).
image SHA256 `61197f8ceffc401f9396e9023d07995820e17bb957007a6cd48d227dbfe32455` ·
.rwd `b49e7efa8c47bfe1fcdb639885c90ce840143fece8a7d87fdf62b66f2308b5cb`.
**Orchestrator-verified from the shipped files on disk.** EME audit ALL PASS, `0xC674E`=5120 > 3072,
`0xC407E`=511, CRC 50/50, `[0xC5000,0xC5FFC)` identical to base, zero unattributed bytes,
bit-for-bit reproducible.
⭐ **STRUCTURAL CEILING: the build ABORTS at 10×** — the soft-EME floor `0xC674E`=5120 must stay
**>** the tracking clamp. **This firmware caps the LKAS gain below 10×.**

### 🛑 THE DOSE-RESPONSE (two points, no third rung — `p` is EMPIRICAL, not a law)
Vibration **m^1.74 [1.43,1.96]** · authority **m^0.88 [0.75,1.04]**. At 6×: 22–26 Hz **0.61×
[0.57–0.66] of V101**, wheel rate under hard command **0.78× of V101 but still 1.43× of V100**.
🛑 **The naive mechanism is REFUTED**: within either route the 22–26 Hz band does **not** scale with
command amplitude (slope **+0.01 [−0.36,+0.31]** across a >10× range) ⇒ **the gain acts on the LOOP,
not the drive.**

### PRE-REGISTERED READOUT — score with `rlog-tools/score_v102.py`
Primary: within-route `tq` band-RMS(21.5–25.5) ÷ band-RMS(2.5–4.5), median over 1 s engaged windows.
**V101 = 5.07 · V100 = 0.62 · V102 predicted 0.61× of V101.** Power **94.2 % at 20 s**, 97.1 % at 25 s.
**≈1.0× of V101 ⇒ the gain is NOT the carrier and this session's attribution is REFUTED.**
🛑 **Q / −3 dB width is NOT an endpoint** — two analysts disagree on its *sign* (31.4→47.4 vs
34.5→23.6) at a resolution where 3 bins decide it. **UNRESOLVED.**

### 🛑 NINE LEVERS KILLED ON EVIDENCE, NONE ON THE ROAD — do not re-propose
`0xC61B2`/`0xC61B4` (inert, 81.5 % of rail since V14) · **Lever B** (null at 22–26 Hz; its *removal*
is a ~3× win at 6–9 Hz **at creep only**, neutral at road speed) · **`0xCBE74`** (inert both bands) ·
**`0xC40D2`** (null both bands, real exposure) · **`0xC63AC`** (full Bode sum: |L| 0.875×1.38 =
**1.208** at cal 205 ⇒ predicted WORSE) · **`0xC63AA`** (sign is frequency-dependent, not fixed) ·
**dead biquad `0xC649B`** — 🛑 **KILL REASON CORRECTED 2026-08-20. The `gp-0x6b62` attribution is WRONG**
(a decompiler variable-name collision — `gp-0x6b62` selects the IIR *coefficient*, cal `0xC6382`=41, not
the biquad's input). **The real arm is `cal(0xC649B)==1 AND cal(0xC64FA) ≤ gp-0x671a`, and `gp-0x671a ≥ 5`
has NEVER been observed true — 0 across 255,292 engaged frames on three builds (V64/V67/V68).** ⇒ the
verdict *"inert"* stands but **for a different reason**, and **V103 arms it anyway via a private in-place
`cmp` patch at `0x35A12`** (NOT `0xC64FA`, which is the SHARED detector CEIL with 18 in-code readers).
See `HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §5.2. · **PID `Kd`** (sign unresolvable at 23 Hz — it
is the measured Re(Z) crossover — **and it changes MANUAL steering**) · **`0xC6194`** (dead-dead).

### 🛑 CORRECTIONS TO THIS KIT'S OWN RECORD — see the handoff §9 for all twelve
1. **`gp-0x6b4c` IS NOT THE LKAS COMMAND.** It is `Σ_{i=0..10}(0xC4118[i]≠0 ? gp-0x62b0[i] : 0)` — an
   **11-slot assist sum**, LKAS being one slot, algebraically flat. Explains why its sign agreed with
   openpilot's command **at chance** (52.80 % vs 54.36 %) while flipping 8.2/s vs 0.31/s.
2. **V101's GATE 2 premise is MEASURED FALSE** — *"doubling the gain… does NOT change any closed-loop
   pole."* The pole moved and the demand oscillates.
3. **`band_envelope` is BROKEN in `_r31_common.py` AND `_r2b_common.py`** — one-sided `H=2X` then
   `irfft` ⇒ a **rectified** signal, not an analytic envelope. Ratios survive. ~20 callers. NOT FIXED.
   🛑 **SCOPE NARROWED 2026-08-20 — THIS RETRACTION WAS OVER-BROAD.** Measured on a clean 8 Hz
   `exp(−1.0 t)` decay, the broken envelope recovers **λ = 1.036 vs 1.000 — a 3.6 % error** (rectification
   noise averages out of a log-linear fit); envelope **CV** is inflated 1.127 vs 0.923 (**+22 %**).
   ⇒ **CV / duty / p50-amplitude results ARE corrupted and stay retracted.** ✅ **BUT `qd_final.py` /
   `qd_lib.envelope_stats` — the code that actually produced ζ = 0.017–0.036 and Q = 14–29 — call
   `scipy.signal.hilbert`, NOT `band_envelope`.** ⇒ **the ring-down ζ/Q result was NEVER at risk and is
   UN-RETRACTED.** Drop it from this list; keep growth-rate, decay-τ, p50 and CV/duty.
4. **`0xC6446` is NOT "10×"** — Honda's 512 is **inert**; **5244 = 2.00 × 2622**, the LERP's value at
   grind #1's point, and the ratio drifts elsewhere.
5. **PID gains**: `0xC6ADC`/`0xC6B08`/`0xC6B1C` are **headers**; `0xC6AE6`/`0xC6B12`/`0xC6B26` are
   **Y[0]** at header+0xA. Kd/Ki flat at all four knots. **All N = 0/102, virgin.**
6. **V102's identity asserts a CLEARED bit** (`b3==0`) — forgeable in a way a SET bit is not.
   **V103 RULE: go back to a SET bit.** Generation-3 space is EXHAUSTED.

V100 flew as route `0x85`, 2026-08-13, 5 segments (15/16/18/19/20 — **segment
17 is ABSENT from disk**), **29,999 frames · 249.2 s engaged in 6 episodes — ~4× the best engaged
exposure ever recorded on this kit.** Fault-free: 0 sentinels on `0x14A`/`0x18F`, `CONFIG_VALID`
1.00000, `OUTPUT_DISABLED` 0.00000, DTC bit2 0.00000, `STEER_STATUS` {0: 30,000}. Identity duty
**1.000000** (`byte7[7:6]==2` AND `b3==1`). 427 lane unsaturated at both 1023 and the structural 800.
Engaged p50 **39.6 km/h**, p90 99.6, max 104.5; **≥50 km/h 88.4 s, ≥80 km/h 45.5 s** — the kit's
first substantially non-creep engaged drive. 🛑 **V100 is a ZERO-CALIBRATION instrument ⇒ the
control law he drove is V99's, bit for bit.**

🛑🛑 **V101 IS BUILT AND NOT FLASHED.** See the heading above for the full delta. EME audit passed.

### 1. 🛑🛑 E1 AND E2 BOTH READ EXACTLY ZERO — THE REFERENCE-CLAMP HYPOTHESIS IS DEAD
`d(b5)` (`|gp-0x6ad6| ≥ cal 0xC6200` = 8192) = **0.000000** over 24,925 engaged frames, **in all 8
wheel-rate bins**, 95 % CI **[0, 0.0186]** (rule of three on measured τ 0.350–1.547 s, block
bootstrap over 6 episodes). `d(b6)` (the ±10240 error clamp) = **0.000000**; because `d(b5)`=0 the
conditioning set is the **entire** engaged sample, so MARGINAL ≡ CONDITIONAL and all three E2
statistics resolve. Positive controls healthy: **`b4` = sign(`gp-0x6ad6`) 0.6057 engaged — the SAME
CELL as b5**, 16.84 flips/s; `b7` 0.5222, 12.42 flips/s.
⇒ **The pre-registered ZERO sentence is licensed: *"`gp-0x6ad6` never reached the PID's ±8192 clamp
in any engaged frame… THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND MUST NOT BE RE-PROPOSED."*** The
composite sentence closes the **whole saturation family**. `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565`
stands **UNCONDITIONED** in the flown regime.
✅ **THE NULL IS ON THE HYPOTHESIS, NOT THE GATE — proven three ways, not assumed.** (a) Both cave
rungs disassembled from the **built image** and proven correctly coded: all four branches `0x05AE` =
**cond 0xE = signed GE**, not the `ba05`/`b205` inversion class; `tp+0x7200` resolves to `0xC6200`
which reads 8192; `shl 0x4` places the bits at byte4 b5/b6; **no guard on either rung**; and the
rungs **share their accumulator and store** with the controls that measured 0.5222/0.6057/1.000000
⇒ the detector provably ran 29,999 times. (b) **The last open gap — `mov`'s flag-transparency
between `cmp` and `bge`, carried as BELIEF since V98 — is CLOSED EMPIRICALLY**: V98's cave carries
the **byte-identical idiom** (`e639` / `023a`|`043a` / `ae05`) at the same bit positions, and **V98's
bit-6 comparator measured duty 0.4235 on-car.** (c) **Structure predicts the null independently** —
see §2.

### 2. ⭐ `gp-0x6ad6`'s REACHABILITY BUDGET WAS A GATE-3 ERROR — 2.09×, NOT ~12×
The old figure summed each term's **admission window**; the correct figure uses each lane's **own
writer clamp**. Read from the image: **term 0 `gp-0x6b4a` ≡ 0** (`0xC616C`=0) · term 1 ±1024
(`0xC617E`) · **term 2 `gp-0x6bbc` ≡ 0 — NO WRITER** · term 3 `gp-0x6b70` ±8192 · **term 4
`gp-0x6bce` ≡ 0 — NO WRITER** · term 5 ±1024 (`0xC61C6`) · term 6 ±6144 **but riding the `gp-0x6bda`
detent gate measured 0.0000 over 75,227 engaged frames** · term 7 ±512 (**zero below ~30 km/h**).
**Total reachable 17,152 = 2.09× the 8192 threshold.** At creep, worst case ≈ **3,167+1,024+1,024 =
5,215 < 8,192** ⇒ **the clamp cannot bind, predicted from structure alone.**
⚠ **A speed-LERP multiplies the whole sum before the ±25600 clamp** (`0x38124`), **identity at stock**
(Y `0xC6ACA..0xC6AD8` all 1024) — see §4 for why it is not a lever.
⚠ `gp-0x67ab` is **structurally BOOLEAN** (only producers: `setfne`, `mov 0x1`, `mov 0x0`) ⇒ V86's
`< 2` rung was **a tautology**, not a coding slip. Whether it is ever 1 is **OPEN** (`gp-0x61a0[]`'s
value set unresolved; `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]` contains no 2/3/4, so **BELIEF: never**).

### 3. 🛑🛑 SIX LEVERS CLOSED THIS SESSION — enumerate before proposing anything
| lever | verdict |
|---|---|
| PID reference clamp `0xC6200` | **MEASURED DEAD** (§1). Also **self-cancelling** as a global edit — it clamps term 3 *and* the threshold with the same cell ⇒ the ratio is invariant. Its unchased reader `0x39ff6` is now chased: a **motor-phase fault threshold** ⇒ **DO NOT EDIT stands, with a reason.** |
| `0xC6194` slew limiter | **DEAD TWICE** — input ≡ 0 (partition all-1s) and output reaches only `gp-0x6b4a` ≡ 0 (`0xC63CC`=0). 🛑🛑 **AND `0xC4118` IS A HARD NEVER-ARM: the partition byte does DOUBLE DUTY — zeroing it to "arm" the limiter sets `gp-0x3d88`→0 ⇒ `gp-0x6b4c`→0 ⇒ LKAS STEERING SILENTLY DEAD while openpilot believes it is steering.** ⚠ The record's kill reason (*"output ×0"*) was **MISATTRIBUTED — it belongs to `0xC6196`** (`0xC6194`=3, `0xC6196`=0, verified). |
| `0xC63AE` 1024→2048 | **NO-GO** — AC gain is **non-monotone and REVERSES** across his amplitude distribution (0.70× at 500 ct → 2.00× at 6000). ⇒ **STATE's old "the only candidate above the floor" row is WITHDRAWN.** |
| deadband + sign-latch (`0xC61B8`/`0xC64A3`) | **STRUCTURALLY DEAD** — the enable is `gp-0x6806 == 0`, and **`gp-0x6806` IS THE ENGAGEMENT FLAG** ⇒ the block runs **MANUAL ONLY**, while the symptom is engagement-required (**83.0 % vs 0.0 %, Fisher p = 3.8×10⁻⁴¹**). ⚠ It is a **LATCHING KILLSWITCH, not a hysteresis** — it outputs the input or exactly zero; backlash's growing-lag describing function **does not transfer**. |
| `0xC63EC`/`0xC63EE` command low-pass | **DEAD ON ARITHMETIC.** Command 6–9 Hz = **8.08 %** of its own total RMS ⇒ a 0.564× band attenuation moves the whole command **0.223 %** — **39× below V85's already-not-felt 1.088.** Independently: **91.1 % of bar 6–9 Hz power is INCOHERENT with the command**, and **the bar LEADS the command by −18.5 ms** (bar = source, command = echo). ⭐ **The phase cost was FREE** — it filters an **exogenous input**, outside the loop ⇒ cannot move a closed-loop pole at any dose. |
| PID Kp / Ki / Kd | **REFUSED — the SQUEEZE.** Kp ×2 delivers **1.130× [0.999, 1.711]** at 6–9 Hz, **ON the 1.088 not-felt bound**; ×4 delivers 1.720× (felt) but **92 % rail duty hands-on**. *"The dose that is safe is not felt, and the dose that is felt is not safe."* **Kd's sign is untrustworthy** (only **53.4°** of φ_G flips it, and −90° is *expected* for a motor/rack-side mode ⇒ **V94 verbatim**). **Ki ≡ Kp's question** — *"the integrator is pinned" IS "the P term has railed"*, the same inequality on the same unmeasured **AUTH**. |

### 4. ⛔ THE SPEED LERP IS NOT A LEVER — THIRD AXIS MISIDENTIFICATION IN THE RECORD
**`gp-0x69aa` IS NOT VEHICLE SPEED.** It is a **Q15-normalised governor DERATE, unity `0x8000`,
MIN-only, seeded at unity, sole writer `0x45342`** (`mulu`/`shr 0xf`/`st.h`); X knots are exactly
`[0,.2,.4,.6,.7,.8,.9,1.0]×32768`. **MIN-only seeded at unity ⇒ pinned at the top knot in normal
driving ⇒ `Y[0..6]` inert by operating point** (the FactorC/FactorE dead-zone class). ⚠ `X[7]` reads
`0x8000` = **−32768 signed**. 🛑 **This was ALREADY corrected at `TRACE-2026-08-10:257` and a later
session repeated it.** ⇒ new memory `accord-verify-a-lerp-axis-before-designing-to-it`.

### 5. ⭐⭐ THE RATE LANE IS CLOSED AT AN OPTIMUM — V88 IS SITTING ON IT
Read from the images (`0x3AA96` gate · `0xC6444` · `0xC6446`), orchestrator-verified:
```
stock/V62/V65   gate 0xC5 DEAD    512 /  512     net = (5244 + 512a)/(3072 + 3072a)
V67/V68/V88     gate 0xFB ARMED   512 / 5244     1.707 @a=0  ->  0.937 @a=1
V71c            gate 0xFB ARMED  3072 / 5244     1.707 @a=0  ->  1.354 @a=1
V100 (on car)   gate 0xFB ARMED   512 / 5244     = V88
```
🛑 **At `a = 0`, V88 and V71c are ARITHMETICALLY IDENTICAL (both 1.707).** On-car they are the
corpus **extremes** — V88 *"grinding fixed"*, **V71c the worst build ever recorded on all three
symptoms** (ratchet at the corpus record 8,521 ct p-p). ⇒ **`a` is materially non-zero and the r26
arm is LOAD-BEARING — proved from images, no drive.**
⇒ 🛑 **ACCOUNT A IS REFUTED.** *"More derivative feedback ⇒ more damping ⇒ less HF"* predicts the
**higher** net dose (V71c) should be **better**. It was dramatically worse. ⚠ **Correct
`memory/accord-v88-flew-grinding-fixed-command-intact.md`'s mechanism paragraph — keep the coupling,
fix the direction.**
⇒ ⭐ **BOTH FLANKS ARE NOW MEASURED**: V61 (below V88) *"made it WORSE"*; V71c (above) worst in
corpus. **The standing "2× ≈ OPTIMUM, not a point on a ramp" now has both sides.**
⇒ 🛑🛑 **LEVER B IS REMOVED FROM EVERY FUTURE SHORTLIST, IN BOTH DIRECTIONS.** This retires the
kit's self-declared *"leading open question"*. ✅ And `0xC6444`'s falsification was **verified in the
safe direction** — V71c had the gate **ARMED**, so the *"null by construction"* note does not reach it.

### 6. ⭐ THE OPERATOR'S OWN AXIS — HE IS RIGHT ON TWO OF THREE CLAIMS
His words: *"speed independent… the stuttering is worst when **d(LKAS demand)/dt** is high."*
🛑 **The corpus null that looks like it covers this was on WHEEL rate — a different quantity. It does not.**
- ✅ **HARSHNESS MATTERS**: hands-OFF pooled partial **+0.0815 [+0.0404, +0.1244]**, 5,716 windows /
  **118 episodes**, 8 routes, conditioned on log|rate| and log v, residualised **within route**.
- ✅ **APPROXIMATELY SPEED-INDEPENDENT**: +0.111 / +0.077 / +0.131 across 10–30 / 30–60 / 60+ km/h.
- 🛑 **NOT SELECTIVE FOR THE STUTTER BAND**: control-band-free sweep 2–44 Hz is **positive in EVERY
  band**, floor ≈ +0.09, **6–9 Hz +0.124 on the declining shoulder of a +0.224 peak at 2–5 Hz** (the
  LKAS lane's own passband). Excess over the 25–42 Hz floor is **+0.03**. ⇒ **BROADBAND EXCITATION,
  not resonance selectivity** — converging with the on-record *"~28 Hz lane-change transient is
  DOSE-INDEPENDENT ⇒ excitation, not gain."*
- 🛑 **HANDS-ON IS UNRESOLVED, NOT NULL**: +0.012 [−0.097, +0.114], and **the hands-off point
  estimate lies INSIDE that CI** ⇒ **the arms are not distinguishable.** Closing it needs ~155 s more
  hands-on exposure. ⚠ **Only 10 of 49 routes are cached in the current schema**; the 994.9 s corpus
  needs ~40–60 min of re-extraction.
🛑 **Every number here is a BAND. THE OPERATOR SCORES THE SYMPTOM. Nothing was fixed and he has
called nothing fixed.**

### 7. 🛑 FIVE SCAN-BLINDNESS CLASSES IN ONE SESSION — all caught by a DECOMPILE, never by a scan
1. **`jarl` Format-V mask** → zero callers for a function Ghidra found instantly.
2. **`movea` base + runtime index** → a live array reads as *"nothing reads slot 1"*.
3. **A byte written by a WIDER store** (`0x27328 st.w` covering `gp-0x3d94`) → false *"0 writers"*.
4. **Wrong `st.b` opcode** → **20 writers reported as ZERO**.
5. **`hw2 = disp|1` applied to `st.b`** → conflated `gp-0x6805`'s stores into `gp-0x6806`
   (`0x97FA|1 == 0x97FB`, verified). **Corrected rule: `st.b`/`ld.b` → `hw2 == enc` EXACTLY;
   `ld.bu` → `enc|1`; halfword/word → either.**
⇒ ⭐ **THE LESSON: an implausible null is a bug report — and so is an implausible non-null. The
decompile is the arbiter either way.**

### 8. ⚠ THREE RECORD DEFECTS CORRECTED — do not re-cite the old forms
1. **`reference-accord-fun3a382-pid-phase-6to9hz-standing-correction` is RETRACTED — arithmetic bug.**
   It mixes normalisations (P and I in ×32, D in ×1, **understating D by exactly 32×**); replaying
   the bug reproduces its own table to 0.1° at all four frequencies. **The PID is in LEAD at 6–9 Hz
   (−0.9° / +8.2° / +13.3°), not a −11°…−27° lag.** ✅ No build was sized on it. 🛑 **But it also
   lives in `.claude/agent-memory/firmware-codepath-tracer/reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md`,
   which every future tracer loads as its own prior — corrected there too.**
2. **The Kd "contradiction" was never one** — **D pumps 2–12 Hz and damps 16–35 Hz**; both memories
   quote a true half of one curve. The kill stands as a **cost/benefit** judgement (a cut buys
   −0.076 at the ratchet, pays +0.225 and +0.323 in his two grinding bands). **Fix: make each entry
   state its BAND.**
3. **`memory/reference-accord-pregain-deadband-c61b8.md`'s "low-speed lockout" reading is WRONG** —
   it is a **speed correlation on a creep-dominated corpus**, beaten by V67's direct identity test
   (`gp-0x6806` == `latActive` on **150,302/150,327 = 99.983 %**) and broken outright by route `0x85`
   (engaged p50 39.6 km/h). ⚠ Also: `reference_accord_gp67ac_*` **conflates three arrays** —
   `0xC4124` @`0x26d1a`, `0xC4118` @`0x272c2`, and the real mode test on **RAM `gp-0x61a0[]`** @`0x27288`.

### 9. ⚠ SCOPE CORRECTIONS THAT NARROW EXISTING KILLS
- **The base-assist damper kill is a CREEP kill.** On route `0x85` FactorC's 35 km/h zone **IS open**
  (88.4 s ≥50 km/h) — but **FactorE's 12.7 °/s zone is NOT**, so `ch₀` stays **exactly zero across
  the whole micro bin (1–13 °/s, 102.7 s) at every speed to 104 km/h**, reaching only **1.5–8 % of
  ceiling** where both are open. ⇒ *"zero on 100 % of the micro regime"* **STILL HOLDS**; *"zero on
  95.91 % of engaged frames"* **does NOT transfer.** **Narrowed, not overturned.** ⚠ That file's
  *sizing* argument and its *"raising `Y[0]` is required"* claim were **already refuted** at the V99
  close-out — do not re-derive them.
- **The exposure claim is retired**: *"E2-class endpoints are unbuildable because he stops within
  15–30 s"* — route `0x85` gave **249.2 s in 6 episodes**. ⚠ **Scope it honestly: one good drive is
  not a new protocol.** He still stops when he feels the symptom, and **that remains correct
  behaviour.** Design for one short symptomatic episode; treat longer exposure as a **windfall**.
- **`gp-0x6ac0`'s three inherited figures RECONCILED** — **330 = highway, 528 = hands-off RETURNS,
  1,941 = MANUAL cranking. None was the engaged operating point.** Measured engaged on route `0x85`
  (4 differentiators, all upper bounds): **crosses 300 ct (4.91 %), NEVER reaches 2000 (0.00 %)**.
- 🛑 **My own "steeringPressed under-counts hands-on" hypothesis is REFUTED** — the kit's own corpus
  figure is **87.7 / 12.3**, and the 67 %-vs-84–95 % gap is **route composition** (r81 is genuinely
  33.4 % hands-on). ⚠ **Keep distinct from the V94 regime-exclusion finding, which STANDS.**

### 10. ⭐ A FIRMWARE DESIGN IDIOM, NEWLY NAMED — and a GATE-3 consequence
**This firmware uses LATCHING ZERO-OUTPUT DROPOUTS in at least two places** — the `gp-0x6b30`
sign-latch and the aggregator's `0x3acc4 cmovc 0x0,r6,r13`, which **DROPS** a lane past ±10240 rather
than clamping it. ⇒ 🛑 **GATE 3 must ask whether a lane has a DROPOUT, not only a clamp — a dropout
is invisible to every no-clip rule the kit runs.** That is the V80 lesson (*"'does not clip' and 'is
not a relay' are different statements"*) in a new form.

### 11. 🛑 WHY NO V101 WAS CUT — stated so it is not re-litigated
Every candidate bit was **vacuous, self-answered, a bare confirmation, or unable to change a build
decision**: the 427 SHARE endpoint is **moot** (the low-pass died on arithmetic); the dropout rung is
**structurally unreachable** (`AUTH ≤ 5120 < 10240` always) — the **V69 `bit4` failure class**; `b5`
**answered itself from the images** (§5); `b4` is a confirmation of a well-supported claim; and the
AUTH comparator, even fully cleared, licenses only **1.13×**. **A build that measures dead levers is
worse than no build**, and it would have been his **third consecutive** zero-calibration build.
⇒ **The search space is materially smaller than it was, and nothing was spent to shrink it.**

---

## 🛑🛑 SUPERSEDED BLOCK, 2026-08-13 (final) — THE PID REFERENCE IS CLAMPED, AND THE RACK QUESTION IS CLOSED
⚠ **Item 1 below is now MEASURED DEAD — see §1 above. Items 2–4 stand.**

**Read this before the V99 block below.** Four results landed after the V99 score, from the operator's
own two questions. ~~**V99 is ON THE CAR. V100 is BUILT AND NOT FLASHED.**~~
🛑🛑 **STALE AS OF 2026-08-14 — V100 HAS FLOWN (route `0x85`) AND IS ON THE CAR. V99 IS NOT.** Caught by
the mandatory close-out gate (`grep -n "ON THE CAR\|UNFLASHED\|never flashed"`), which is exactly what
that gate exists for — this would otherwise have been the **eleventh** instance of the kit's
"row says UNFLASHED after it flew" defect. **See the LATEST BLOCK at the head of this file.**

1. 🛑🛑 **`0xC6200` (= 8192) HARD-CLAMPS THE PID's REFERENCE `gp-0x6ad6` BEFORE THE ERROR SUBTRACTION**
   (`0x3a798` → `0x3a7a2` → clamp `0x3a7b8`/`0x3a7c8` → `sub` `0x3a7ce`; a SECOND clamp bounds the error
   at ±10240 at `0x3a7d0`; P, I and D all derive from that one `err`). ⇒ **`|gp-0x6ad6| ≥ 8192` makes
   `∂(gp-0x6ad4)/∂(gp-0x6b70)` EXACTLY ZERO through all three terms at once.** [EVIDENCE — Ghidra,
   orchestrator-reproduced; `read_memory(0xC6200)` = `00 20` LE.]
   🛑 **⇒ `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` IS THE *UNSATURATED* DERIVATIVE — valid only while
   `|gp-0x6ad6| < 8192`. Never quote it unconditioned.** Both duties are UNMEASURED; **V100's `b5`/`b6`
   measure them.** `0xC6200` is **four** things + one unchased reader (`0x39ff6`) ⇒ **DO NOT EDIT IT.**
2. ✅ **THE 4× LKAS GAIN (`0xC6CD0`) IS EXONERATED, TWICE.** It does **not** reach term 0 — `FUN_0002b422`
   writes a **literal zero** (`r0`) into field `+2` at `0x2b52a` while the 4× goes to field `+4` ⇒
   `gp-0x6b4c`. And it is **not saturating**: its ceiling went **512 → 2048, exactly 4× with the gain**,
   and the next fixed clamp sits **5×** above. *"Extra command buys no extra authority"* is **REFUTED**.
3. 🛑 **TERM 0 (`gp-0x6b4a`) IS IDENTICALLY ZERO.** Its producer passes through
   `clamp(driver_torque, ±cal 0xC616C)` and **`0xC616C` = 0** in stock and V99 ⇒ both writer branches
   yield zero. ⇒ **The reference is entirely terms 1–7, block-gated by `gp-0x67ab`. Term 7 IS
   `gp-0x6b70`, whose own clamp is the SAME cell `0xC6200` ⇒ ZERO HEADROOM.** That is where the rail
   search now sits — and V100 already measures it. ⚠ `0xC616C` is a standing **NEVER-RAISE** cell.
4. ✅ **THE RACK QUESTION IS CLOSED — AND `0xC6B64` IS ADEQUATE.** `FUN_0003b8f6` **does** read absolute
   steering angle (`0x3ba12`) and indexes a compensation table at `0xC6B64` (**virgin on all 96 images**)
   ⇒ **the "plant model is structurally blind to rack position" hypothesis is REFUTED.** Measured from
   **47 routes / 427 min, four independent estimators**: **16.9:1 near centre → 11.1:1 at lock**, swing
   0–120° = **1.176 [1.147, 1.201]** against the firmware's **1.206×** ⇒ **ADEQUATE, agreeing to 0.01–0.07
   at every knot.** 🛑 **The 1.67–1.82× desk estimate off the service-manual schematic is REFUTED.**
   Beyond 120° the rack keeps quickening while the model goes flat ⇒ **~20 % uncompensated, but ALL such
   exposure is below 5 m/s.** Centre offset **−4.25°** (openpilot's learned −4.78°).
   ⭐ **The rack is SYMMETRIC** — all 19 paired per-bin CIs cover equality, and an **injected 2 % asymmetry
   WOULD have been detected ⇒ a real ≥2 % asymmetry is EXCLUDED.** θ₀ exonerated both ways (sweeping
   −7…−1.5° moves the L/R difference by **0.9 %**, under its own CI half-width).
   ⇒ **NO angle-dependent plant-model error exists in the band he drives. That line is dead as a symptom
   explanation.** Traces: `docs/TRACE-2026-08-13-measured-steering-ratio.md` · `…-variable-ratio-rack.md`
   · `…-4x-gain-to-term0.md` · `…-v100-6ad6-and-ivar6.md`.

🛑 **TWO INSTRUMENT FACTS THAT INVALIDATE EXISTING ANALYSES:**
- **`carState.yawRate` is IDENTICALLY ZERO on this car** — 0 nonzero of 512,895 samples. Anything reading
  `cs_yaw` reads zeros. Use `livePose.angularVelocityDevice.z` (**z-DOWN ⇒ negative on a LEFT turn**).
- **`vEgo` is INVALID as a speed reference for any rear-axle kinematic quantity at angle** — it averages
  all four wheels and runs **+7.9 %** fast at 250–400°, **shaped exactly like a flat plateau.** It produced
  a **FALSE PASS of the ratio study's own positive control** before being caught. Use `(ws_rl+ws_rr)/2`.

⚠ **GOLDEN-MODEL GAP, OPENED AND MARKED:** `eps_chain_control.py` models `gp-0x6ad4` as a lane and **does
not model the PID's internals at all**, so the clamps above are absent from it. A header note now sits at
the exact site. **Implementing it changes delivered numbers and must be its own verified pass with a
re-derived contract.** The 87-symbol / `740f4bcd…` contract **PASSES** as of this close-out.

---

**Last updated: 2026-08-13 (later still) — V99's FLIGHT SCORE IS IN. `0xC40BC` IS CLOSED AT ANY DOSE.**
V99 flew despite an already-retracted rationale (`0xC40BC` delivers 0.5–1.2% against a ~9% floor;
see §3b/§5 of the V98 handoff), and the flight itself now shows WHY the lever can never work: E1
(below) shows doubling the friction knee does not move the MODEL-vs-ACTUAL balance at ANY wheel
rate, so no dose of this cell — not 300, not 6000, not anything — can be the fix. **Operator,
verbatim: *"I think it helped with the audible aspect of the grinding, though I'm not sure."***
🛑 Nothing is called fixed. He has not called anything fixed.

⚠ **SUPERSEDED HEADING — V99 IS NO LONGER ON THE CAR; V100 FLEW AS ROUTE `0x85` ON 2026-08-13.**
The V99 flight record below stands as history. **~~ON THE CAR:~~ FLOWN: V99.** Route `0x82`, 2026-08-13, **2 segments, 121.7 s**, base = V98. **12 bytes vs
V98** (orchestrator re-verified from the images, `analysis-2020accord/ledger_v38_to_v99_bytes.py`):
`0xC40BC` 600→**300** (2 B) + `0xC63AC` 150→**102** = back to STOCK's own value (1 B) + `0xC4B52`
identity byte `00`→**02** (1 B, cave) + two 4-byte CRC trailers (`0xC4FFC`, `0xC6FFC`). image sha256
`a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726` — **matches the handoff's stated
hash, independently reproduced.** builder `analysis-2020accord/build_v99_tva.py`, 134/134 assertions.

🛑 **V100 IS BUILT AND NOT FLASHED — V99 REMAINS ON THE CAR.** Stating both explicitly; this kit has
shipped ten instances of a stale flight-status row and this is not the eleventh. V100 is a
ZERO-CALIBRATION instrument build (128 B vs V99, 12 runs, independently re-verified — see
`docs/BUILD-LINEAGE.md`'s V100 row and `docs/HANDOFF-2026-08-13-v99-flew-the-rail-and-v100.md` §12
for the full build record). **The flash decision is the operator's.**

**FLIGHT [EVIDENCE, `scorer-v99`, `docs/TRACE-2026-08-13-v99-flight-score.md`]:** fault-free — 0
sentinels on `0x14A`/`0x18F`, `CONFIG_VALID` 1.00000, `OUTPUT_DISABLED` **0.00000**, DTC bit2 0.00000
/ 0 transitions, `STEER_STATUS` **{0: 12004}**. **IDENTITY PASS with ZERO margin consumed:** `b5`
duty **1.000000** (0 of 12,005 frames; V98 measured 0.0022 on the byte-identical rung) **and**
`byte7[7:6]` = {2: 12,005}. ⚠ `byte4[7:3]` is **all EVEN** {6,12,14,20,28,30} — expected, **not a
fault**; the ~50-build "always ODD" convention would have wrongly pulled this build. **Engaged 59.8 s
in 4 episodes** (15.9 / 31.3 / 2.5 / 10.1 s), engaged p50 **6.66 km/h**, plus **60.2 s of interleaved
LKAS-off arm**. 427: 245 codes, p99 232, **0.000% saturation**. `b3` duty 0.0000 (R5b reproduces on a
FIFTH route).

### 🛑🛑 E1 READS NULL — `0xC40BC` IS CLOSED AT ANY DOSE, NOT JUST 300
All four rate bins moved, **all four DOWN** (lever bins 0.7335 / 0.8749; control bins 0.9374 /
0.9119). `build_v99_tva.py` pre-registered verbatim: *"A change in ALL FOUR bins is an
operating-point / route artefact, NOT the lever."* **The pre-registered null sentence is licensed
verbatim:**
> *"Doubling the modelled-Coulomb small-signal gain in the 1-13 deg/s micro regime does not move the
> MODEL-vs-ACTUAL arm balance at any wheel rate, so the friction ramp's KNEE POSITION is not what
> sets that balance while he feels the symptom — and since the reachable friction set is unchanged,
> no larger dose of THIS cell can do it either. The next lever must be outside `FUN_0003b8f6`'s
> friction path."*
⇒ **Because the reachable friction set is bit-identical between V98 and V99, this closes `0xC40BC`
at ANY dose, not just 300 — see `docs/BUILD-LINEAGE.md`'s V85/V99 rows.**
⚠ **The residual, honestly:** the 0–5 °/s ratio (0.7335) sits apart from the other three — that IS
the predicted full-dose bin — but the offset-immune DiD CIs overlap. **The closure rests on the
pre-registered rule, not on a demonstration that the lever did nothing.**
⚠ **E2 was UNDERPOWERED and could not arbitrate** — its null width (0.343) exceeds the entire 0.10
gap between the hypotheses it was built to separate. **Its formal NULL is a power artefact, not a
finding — it is not evidence for anything and must not be cited as such.**

### 🛑 V98's ENGAGED/MANUAL HEADLINE WAS OVERSTATED BY ~22% — CORRECTED
The `b6` MODEL-vs-ACTUAL duty contrast (raw **0.4235 engaged vs 0.8041 manual**, as scored in
`docs/SCORING-2026-08-13-v98-route81.md`) is **rate-confounded**: manual exposure is 1.84× more
60+ °/s weighted than engaged on route 81 (3.72× on route 82), and `b6` is itself strongly
rate-dependent. Matched on a 4|rate|×6 speed grid (5.12 s block bootstrap): **route 81 (V98) matched
engaged 0.4543 vs manual 0.7493, diff −0.2950 [−0.4099, −0.1727]** (15 cells, 96.0% engaged / 83.4%
manual exposure surviving); **route 82 (V99) matched diff −0.3372 [−0.5354, −0.1895]**. **The
finding survives — engagement swells the ACTUAL arm relative to MODEL, both CIs exclude zero widely
— but the magnitude was overstated by about a fifth. Quote the matched figures, not 0.4235-vs-0.8041,**
and the two routes' matched CIs overlap heavily ⇒ **V99 did not change the engaged/manual gap.**

⚠⚠ **SUPERSEDED — the block below describes V98, the PREVIOUS build. Its mechanism findings (the
comparator result, the `f′` compression finding) still stand as analysis; its "ON THE CAR" status
does not.** 🛑🛑 **V98 FLEW as route `0x81`**; the COMPARATOR ANSWERED, and it
refuted the "arms are wildly unequal" belief. `0xC63AC` moves from UNINTERPRETABLE to **WRONG-DIRECTION**.

Route `0x81` (`75604b0a432fdc89_00000081--c7103d2cb4`, 3 segments,
cache `_cache_r81/`), 2026-08-12, **fault-free** — 0 sentinels on `0x14A`/`0x18F`, `CONFIG_VALID`
1.00000, `OUTPUT_DISABLED` 0.00178, DTC bit2 0.00000, `STEER_STATUS` `{0: 17981, 3: 2}`.
**IDENTITY IS SINGLE-FRAME PROOF:** `0x14A` byte7[7:6] == **2** on **17,983 / 17,983 frames,
duty 1.000000** (V96/V97 hard-wire 1; ≤ V91 give 0 ⇒ structurally excluded).
181.5 s total · **65.9 s engaged in 3 episodes** (longest 29.8 s) · engaged p50 **5.58 km/h** ·
⭐ **plus a BACK-TO-BACK LKAS-OFF ARM** — engaged ends 110.56 s, the operator's deliberate
*"this is how smooth it should be"* demonstration begins 110.57 s. **Consecutive frames, same lot,
same tyres.** This is the within-drive matched control the kit had never obtained.
⇒ **MAKE THE LKAS-OFF ARM MANDATORY IN EVERY FUTURE DRIVE PROTOCOL.** V98's spec called it
*"optional and free"*; it is neither.

⊕ **V98 was a ZERO-CALIBRATION INSTRUMENT BUILD — no symptom verdict is expected or claimable from
it.** The V97→V98 delta is **146 bytes, 142 cave + 4 CRC, ZERO calibration bytes** (verified from the
images two ways).

---

## 🛑🛑 THE SESSION'S REAL RESULT — `f′` COMPRESSION. READ THIS BEFORE PROPOSING ANY OBSERVER LEVER.

**`f′`, the Stage-2 LERP's local slope, is a deterministic function of `|iVar6|`:**
```
|iVar6| ct : 0-178  178-356  356-719  719-1200  1200-1800  1800-3000  3000-5000
f'         : 2.539   2.174    1.496    0.948      0.488      0.346      0.248
```
| route 81, engaged | steeringPressed | D3 mask |
|---|---|---|
| `\|iVar6\|` p50 **hands-ON** | **2,829 ct** | **2,818 ct** |
| `\|iVar6\|` p50 hands-OFF | 188 ct | 337 ct |
| **f′ p50 hands-ON / hands-OFF** | **0.346 / 2.174** | **0.346 / 2.137** |

🛑 **THE FIRMWARE DESENSITISES THIS LANE 6.3× EXACTLY WHEN THE DRIVER PUSHES — and pushing is how the
operator provokes the symptom.** Two independent masks agree to 2 %. **Every perturbation of `iVar6`
reaches the car through `f′`, and V89 and V97 BOTH argued their direction on hands-off data (the steep
part) while the symptom lives on the flat part.** ⇒ **ONE mechanism for both nulls, consistent with
V98's comparable arms and the lively 427 lane, requiring nothing unmeasured.** [BELIEF, fits all data]

🛑 **CONDITIONED 2026-08-13 (later) — this line used to read "PATH 2 IS AUTHORITATIVE... no dilution
anywhere" unconditionally. `tracer-6ad6` found a hard clamp inside the same chain; team-lead verified
the crux in Ghidra directly (`read_memory(0xC6200)` = 8192, `disassemble_bytes` reproduces the
listing instruction-for-instruction).** `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` at 7.79 Hz, **valid ONLY
under the condition `|gp-0x6ad6| < 8192`** — the `0xC6200` clamp at `0x3a7b0-0x3a7c8` sits INSIDE
this very chain (`FUN_0003a382`, all three of P/I/D driven from the same clamped difference) and
**zeroes the derivative when it binds.** The clamp duty is UNMEASURED — V100's RUNG A measures it.
**Do not delete the number; it is still correct in the unsaturated regime.** Positive control still
reproduces the recorded PID lead to 3 s.f. (that check is unaffected — it ran unsaturated). Both
gates OPEN, incl. **`gp-0x67ab` ≡ 0 STRUCTURALLY** (closes `HANDOFF-2026-07-27:287`).

### ⭐ THE PERCEPTUAL BRACKET — and every candidate scored against it
**~0.55× (−45 %) IS felt (V88, V62). ~1.09× (+9 %) IS NOT (V85, V89).**
| lever | dose in his regime | verdict |
|---|---|---|
| `0xC63AC` 150→102 | 0.8–2.5 % of Path-2's 140.6 ct | **below floor ~20×** |
| **`0xC40BC` 600→300** | **0.5–1.2 %** | **below floor 8–18×** |
| `0xC63AE` 1024→**2048** | ≈ **+28 %** on the lane | ⭐ **the only one ABOVE** |

🛑 **`0xC40BC` is structurally dead in his regime: 93.1 % of hands-on engaged frames sit ABOVE the
10.61 °/s knee, where 300 and 600 are ARITHMETICALLY IDENTICAL** (orchestrator-verified; mean ramp
ratio **1.050**, a ×1.05 not a ×2). And `friction = |fVar18|·ramp·K1/1024` ⇒ **`0xC40BC` and `0xC40D2`
are two factors of the SAME PRODUCT — V99's perturbation is 0.096× V89's, which measured FLAT.**

### 🛑 FOUR RETRACTIONS FROM THIS SESSION — do not re-cite any of them
1. **"Stock encodes an exact pole match and V97 broke it"** — the cell identity is real and probably
   deliberate (`round(0.1·4096)=410`, Honda shipped **408 = 4×102**), **but it is a match between two
   STAGES, not the ARMS**, which do not share an input and are already **84° and 0.557-vs-0.906 apart
   at stock.** 🛑 **NEVER quote the 0.111/0.136/0.151 "phantom".** Survives: V97 moved the arms
   **further apart** (+7.82°, +5.4 %).
2. **"REQUEST is minor"** — `b5` tests REQUEST vs **ACTUAL**; the denominator is the **RESIDUAL**
   (`|iVar6|` p50 389 ct). The kit's own retracted "≤ 9 %" error, repeated. **REQUEST is now the most
   important unmeasured term in the chain.**
3. **427 "broadband ⇒ no band-specific claim"** — an **artefact**: 427 is transmitted at 49.835 Hz and
   a ZOH images 5–15 Hz onto 35–45 Hz. With a valid **20–24 Hz** control, 6–9 Hz excess is **2.30× on
   427 and 1.97× on column — they agree.**
4. **V86's `gp-0x67ab < 2` rung could NEVER have fired** (`< 2` is true of both states), yet
   `BUILD-LINEAGE.md` cites it as *"lever in force three ways."*
⚠ Also: `0xC63A0` weights **`gp-0x6bd0`**, not `gp-0x6b26` (that is `0xC63A6`).

🛑 **PRIOR OPERATOR REPORT, on V97 (route `0x80`), VERBATIM:** *"I did not feel any difference in
grinding or stuttering (micro-ratcheting) behavior at all on V97, so I stopped the drive."*
⊕ **"Stuttering" ≡ micro-ratcheting — his own parenthetical.** It is not a fourth symptom.

⚠ **IDENTITY IS V96-OR-V97, NOT SINGLE-FRAME V97.** `0x14A` byte7[7:6] ≠ 0 on **10,750/10,750** frames
⇒ **not V94, not V92, not anything ≤ V91** (all mask those bits off — structural). But **V96→V97 is
5 bytes (one cal + its CRC)**: cave, 427 repoint and every bit map are **identical**, so *no* frame can
separate them. We rely on the operator's statement that V97 was flashed.
⇒ 🛑 **STANDING REQUIREMENT: every build must carry a BUILD-IDENTITY FIELD that changes on every cut,
independent of the lever under test.** 2 bits (byte7[7:6]) gives only ONE clean generation and
V96/V97 already burn {1,3}; a durable field needs ≥3 bits and its own `0x18F` hook — **as its own
build**, never combined with a new measurement class (that is how V24/V27/V48B bricked ECUs).

🛑🛑 **THIS FILE SAID "ON THE CAR: V94 … it is still flashed" FOR A FULL SESSION AFTER V96 FLEW, AND
IT COST REAL WORK.** It sent the session's strongest analyst to close its verdict with *"fly V96, S2
answers it"* — V96 had already flown and its regressor was 34× over-range, so **S1 and S2 are BOTH
VOID**. Seventh instance of the kit's "row says UNFLASHED after it flew" defect.
⇒ **NEW CLOSE-OUT GATE, mechanical, run it every time:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`, reconciled
against the identity bit from the most recent route. The old rule ("write the flight result in the
same pass that scores the flight") only fires if someone remembers; this one fails loudly.

## ⭐ FLOWN 2026-08-12 AS ROUTE `0x81` — **V98**, the first COMPARATOR probe in the kit
🛑 **This heading read "BUILT AND UNFLASHED" for a full session after V98 flew — the EIGHTH instance
of the "row says UNFLASHED after it flew" defect. Corrected 2026-08-13.** See the flight result and
the comparator verdict at the head of this file.

```
39990-TVA,A160-V98-V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2-0x13000-0x100000.rwd
  image c9babfed6acf24c0c5877754149a60fd5866dae8407029d7a3a5d74870d151d9
  rwd   fcfa1baa82ea8fbca104eee5c8a398b7d5de8762629351128b05e0cb811e5e3c
  builder analysis-2020accord/build_v98_tva.py   199/199   BASE = V97 (on the car)
```
🛑 **ZERO calibration bytes. ZERO 427 bytes. Cave only — AN INSTRUMENT, NOT A FIX.**
It answers the one question this session could not: **which arm of the observer residual dominates.**

| bit | signal | role |
|---|---|---|
| byte4 b7 | `gp-0x6b70 < 0` | V96's rung, byte-identical |
| **b6** | ⭐ `\|gp-0x6bfe\| ≥ \|gp-0x374c>>4\|` | **MODEL vs ACTUAL** |
| **b5** | ⭐ `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` | **REQUEST vs ACTUAL** — with b6, ranks all three arms per frame, **no scale assumption** |
| b4 | `(gp-0x374c>>4) < 0` | V96's rung — **the converse positive control** (measured `arg(B′)−arg(rate)` = +78.6°/+78.0°) |
| b3 | `gp-0x6752 ≥ 0` | closes a multi-session blocker; **a DEPENDENCY, not a rider** |
| byte7[7:6] | hard-wired **2** | identity + liveness |

**Orchestrator-verified from disk:** both hashes ✓ · V97→V98 diff **146 B**, all in `0xC4B34–0xC4BCD`
+ `0xC4FFC`, **zero unattributed** ✓ · **every cal cell identical to V97** ✓ · **GATE 2 re-derived
independently — exactly 3 stores across exactly 2 cells (`gp-0x1514`, `gp-0x1511`)** ✓.
**GATE 1 PASS** on all four cells; wider 32-bit span scan **67 accesses, ZERO span-only hits**.
**Hook proven from the image to be the 100 Hz `0x14A` builder, NOT the 1 kHz task** (`0x55C14 =
movea 0x14A,r0,r8`). Cave **112 → 154 B (+37.5 %)**, 12.7 % of the extent — stated, not claimed away.

🛑 **SCORER WARNING — the ~50-build "byte4[7:3] is always ODD" convention DOES NOT HOLD on V98.**
`b3` is a measurand, so **byte4 goes EVEN whenever `gp-0x6752 < 0` — that is the FINDING, not a fault.**
Liveness moved to **byte7**. Without this a scorer pulls a working build.
🛑 **`0x7FFF` sentinel pre-registered:** when the plausibility latch fires, `gp-0x6bfe` = `0x7FFF` and b6
reads TRUE for an unrelated reason. The latch rails `gp-0x6b70` ⇒ **427 pins at exactly 1023.
Score b6 only on frames with 427 ≠ 1023, and report the excluded count.**
⚠ **One open gap before any flash:** `mov`'s flag-transparency is **BELIEF** — SLEIGH + Honda's own
instruction scheduling, not a manual quotation.

**DRIVE PROTOCOL: ONE parking-lot creep, LKAS engaged, hands on — stop the moment the symptom is felt.**
~15–30 s of engaged frames. **No matched arms, no episode counts, no highway, no second drive.**
Optional and free: a few seconds of the same creep LKAS-off; and 60 s turning the wheel by hand with the
car OFF (a positive is strong, a negative is weak).

---

## 🛑 V97's VERDICT — UNINTERPRETABLE. Not falsified. **Do not re-dose `0xC63AC`.**

`0xC63AC` 102 → 150, the Path-2 IIR pole in `FUN_00038148`. **FLEW route `0x80`.**

✅ **THE LEVER IS LIVE — BOTH OF THE OPERATOR'S OWN HYPOTHESES ARE REFUTED.**
- *"A mistaken cal address"* — **excluded 3 ways.** `0x38202` bytes `e5 6f ad 73` = `ld.hu 0x73ac[tp]`;
  `tp+0x73AC = 0xC63AC` reads **102 / 102 / 150** (stock / V96 / V97); off-by-0x1000 excluded
  (`0xC53AC` = 683, identical in all three) and the six neighbour cals `0xC63A0..0xC63AE` all 1024
  unchanged. Census **1 reader / 0 writers**, five methods, Ghidra∖Python set-difference **EMPTY**.
- *"The logic we touched isn't used"* — **REFUTED statically AND dynamically.** `FUN_00038148`'s sole
  caller guards it with `andi 0x830,r25,r28` + `cmp r0,r28`/`be` @`0x22672`, **byte-identical to the
  guard on the assist-channel mixer** @`0x225EE` ⇒ **a shut gate would mean NO POWER ASSIST AT ALL.**
  And `sign(gp-0x374c)` **toggled 181× in 109 s** on this route. **No speed gate, no rate gate, no
  engagement gate anywhere on the path**, and the accumulator update precedes the only in-function gate.

🛑 **WHY IT COULD NOT BE SCORED — three independent reasons, none of them the lever:**
1. **NO INSTRUMENT.** V96's cave is carried unchanged; its regressor is **34× over-range** — `M ≡ 0` on
   **10,749/10,749** frames (third replication: 7e 99.90 %, 7f 99.97 %, r80 **100 %**), `Mlo` duty
   **0.0000**. S1/S2 **VOID** — conceded in `build_v97_tva.py:99-100` **before the flash**.
2. **EXPOSURE.** **1** engaged hands-off episode ≥2 s and **1** decaying-angle return, against **24/27**
   and **14/11** on 7e/7f — and the `|Q| = 1.233` direction result rests on **25**.
3. **THE OBSERVABLE.** **DC gain is 1.000000 at any `A` — a POLE, not a GAIN** ⇒ **no amplitude
   statistic can see it, and none was pre-registered.** Measured anyway: phase contrast **+3.27°** in
   one cell, **−4.08°** in the other (**opposite signs**); 6–9 Hz cross-build ratio **5.92× is SMALLER
   than r7e's own split-half noise 6.98×**; the `sign(gp-0x374c)` crossing-rate test sits inside its own
   split-half noise with the control bit moving too. **Four channels, four closing mechanisms.**

⊕ **V97 NEVER CLAIMED a grinding or ratcheting fix.** Its header prices only a **21 Hz cost** and argues
direction from **hands-off returns**. *"No difference in grinding"* **is consistent with the build
working exactly as specified.**

⚠ Correction: the build docstring's per-`A` phase row is **mis-tabulated** (correct: −23.63° / −15.81°);
the **deltas the decision rested on are right**. Task rate is **1000 Hz, EVIDENCE** (`0xC64DF` = 100
measured on-car at 100.00 ms + the `0x830 ⊆ 0x930` lockstep) — 🛑 **NOT from OSTM0**, which is 500 Hz
because PCLK is 40 MHz; that inference is a recorded red herring an agent nearly shipped this session.

🛑 **The number V95 is BURNED — see §A5.** ⚠ The `rlog-tools/v95_*.py` files are **analysis**
scripts, not build scripts.

🛑🛑 **THIS FILE HAS A HARD SIZE CAP: 256 KB. Keep it under ~150 KB.** On 2026-08-09 it reached
**506 KB / 6,114 lines / 53 sections** — past the `Read` limit, so no agent could load it in one call
and **the tail was silently invisible**. 47 superseded sections were split out verbatim to
**`docs/STATE-ARCHIVE-pre-V89.md`** (432 KB) by `analysis-2020accord/shrink_state_md.py`; the
2026-08-11 V90-flight headline went to **`docs/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`**
(30 KB) at the 2026-08-12 close-out; **the V96/V94/routes-78-79/V88 flight headlines went to
`docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`** (54 KB) by `analysis-2020accord/shrink_state_md_2026_08_13.py`
at the 2026-08-13 (later still) close-out — **177 KB → 126 KB**, each archived section's durable
facts confirmed to survive in `memory/` or `docs/BUILD-LINEAGE.md` before it moved. Nothing was
deleted. **Update this file IN PLACE at every close-out. Never append a new dated block — supersede
the old one.** Per-build history belongs in `docs/BUILD-LINEAGE.md`, narrative in `docs/HANDOFF-*.md`,
durable facts in `memory/`.

**Reading order:** this file → `docs/BUILD-LINEAGE.md` (RULES 3/5/6/7 first) → the latest
`docs/HANDOFF-*.md` → `memory/MEMORY.md` + `memory/MEMORY-PART2.md` + `memory/MEMORY_CONSTELLATION.md`.
🛑 `memory/MEMORY.md` was split in two on 2026-08-12 — it had reached **287 KB against a 256 KB `Read`
cap**, so its tail was silently invisible. **Read BOTH parts.** The archives are records, **not**
instructions — do not reason from them.

---

## ★★★★★ THE STRUCTURE, ESTABLISHED 2026-08-12 — V89 AND V97 PUSHED ON OPPOSITE ARMS OF ONE OBSERVER RESIDUAL

`FUN_00038148` @`0x38236-0x3823A`, coefficients **exactly ±1**, verified from raw bytes
(`0x38238 subr r15,r6` = opcode `0x0C`; `0x3823A add r9,r6` = opcode `0x0E`):

```
FUN_0003b8f6  — the 1 kHz PLANT MODEL / disturbance observer
                K0 0xC4080=0 (NEVER RAISE) · K1 0xC40D2=204 (V89, ON THE CAR) · relay 0xC40BC=600
                EMAs 0xC40D4=573 · 0xC40D6=246 · 0xC40D0=408 · 0xC40D8=3686   (all four VIRGIN)
      │ gp-0x6bfc → FUN_0003bc20 (plausibility ±20000, else force 0x7FFF)
      │ gp-0x6bfe ────── MODEL   ────────┐  UNFILTERED   ◄── V89's K1 acts HERE
LKAS 11-slot aggregator FUN_00026c80     │
      │ gp-0x6bfa ────── REQUEST ────────┤  UNFILTERED   (its ±20000 gate is DEAD — writer pre-clamps)
six lanes → ×sign(gp-0x6752) → ×2639(0xC6468) → <<4
      │ IIR pole 0xC63AC 102→150 = ALL OF V97
      │ (gp-0x374c>>4) ─ ACTUAL  ────────┘  ◄── V97's pole acts HERE.  MEASURED < 2048, 100 % of r80
                              iVar6
          gp-0x6b70 = sign(iVar6) × LERP(|iVar6|), clamp ±8192 (0xC6200)  = the PID REFERENCE
```

🛑 **BOTH ARMS ARE ESTIMATES OF THE SAME QUANTITY, in the same units, scaled by the same `0xC6468`=2639,
entering a DIFFERENCE.** ⇒ **V89's K1 measured FLAT and V97's pole felt like nothing, and one unmeasured
quantity explains both: the arms may be wildly unequal, so whichever you move, the residual barely
notices.** [BELIEF — but it is the first account explaining two nulls with one mechanism.]

🛑🛑 **A "≤ 9 % share" bound was computed and is RETRACTED — DO NOT REUSE IT.** Bounding one arm against
the other's *admitted range* is invalid for a difference of correlated estimates; the denominator is the
**residual**, not the range. **Path-2's share is UNRESOLVED, not small.**

### The Stage-2 transfer is FULLY READABLE — and the rescale is the IDENTITY
🛑 **`STATE.md` §A6b's "the transfer cannot be read from the image" is FALSE**, and so is the standing
*"`f′` swings ≥10× and cannot be pinned statically"*: **the swing is 1.000×.** `gp-0x6982`/`gp-0x6984`
(the X-divisor and Y-multiplier) have **ZERO writers image-wide** — Ghidra + raw disp16 + raw disp23 +
an exhaustive 32-bit-literal search, **with a working positive control** (the neighbours `gp-0x6980/86/
88/8A` all DO have `st.h` writers and the scan found them) — and both boot to **1024** from `.data`
(flash `0x8672E`/`0x8672C`). The `[204,2048]` cal rails guard a value that never moves.

Knots (mode 26, creep; `0xC63AE`=1024 ⇒ the LERP index is `|iVar6|` **raw**):
```
0.0 km/h  X [0,200,400,800,1200,1800,3000,5000,12000,14490]  Y [0,471,880,1408,1689,1953,2376,2844,4114,8192]
6.6 km/h  X [0,178,356,719,1200,1800,3000,5000,10681,14490]  Y [0,452,839,1382,1838,2131,2546,3043,4245,8192]
```
**Route 80 inverted:** `|gp-0x6b70|` p50 320 → `|iVar6|` **126–136** · p90 2,534 → **2,965–3,675** ·
max 3,187 → **5,681–6,891**. ⇒ **`|iVar6|` ≤ ~6,900 at creep, ~130 half the time** — 2.9× tighter than
the ±20,000 clamp. ⊕ **`|iVar6| ≈ 130` median against a six-lane term admitted to 2048 hints at strong
CANCELLATION between the three terms** — exactly what an observer residual should do. [live hypothesis]
⚠ **These numbers DO NOT TRAVEL above 50 km/h** — `0xC669A`/`0xC66A8` truncate the LERP's X axis to
7,000 there. ⚠ **`mode 24 ≠ mode 26` in THIS family** (recs 0/3/4/5 differ) — the
"stock ships 24 ≡ 26" memory is scoped to the **damper** families and does not generalise here.
🛑 **CORRECTED 2026-08-13 (later) — the parenthetical used to also claim "breakpoints differ"; that
is WRONG.** `tracer-c63ae` (crux verified by the team lead): **the mode-24/26 breakpoints do NOT
differ** — both read `[0,960,2560,5120,7680,10240,12800]`. Only records 0/3/4/5 differ, not the
X-axis knots.

### Other results from route `0x80`
- **427 lane (`gp-0x6b70`) is a GOOD instrument**: nonzero **98.29 %**, 250 codes, **0.000 % saturation**,
  p99 3,059 of a ±8192 clamp. Not a V64/V68-class dead probe.
- **The observer's plausibility latch has NEVER fired**: `427 == 1023` duty **0 on 87,423 frames** across
  80/7e/7f — and `>640` (the true reachable ceiling through the clamp) is also **0**.
- **`b3` constant ⇒ `gp-0x674e < 28` settles RULE 7 for the authority curve** — the `Y[last]=0` records
  are live; modes 28–39 excluded. That rung is now **SPENT** and can be reallocated.
- ⚠ **`0xC62EA` = 0 on V97 (stock 320 ≈ 5 km/h)** — the low-speed lockout has been disabled since ~V35,
  so creep sits in a regime stock Honda would have locked out. Context for anything felt at 5 km/h.

## → ARCHIVED SECTIONS — moved out 2026-08-21
Everything from *"ARCHIVED 2026-08-13 — V96's flight headline"* onward now lives in
**`docs/STATE-ARCHIVE-2026-08-21-pre-v104.md`** — verbatim, nothing edited. That file holds the
archived flight headlines, the **STANDING CORPUS RESULTS**, the **STANDING INSTRUMENT CORRECTIONS**,
the methodology + signal-identity corrections, the tyre line, and the superseded on-the-car block.
🛑 **The instrument corrections and corpus results are still LOAD-BEARING — read that file before
any analysis session.**
