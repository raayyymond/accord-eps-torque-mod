# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V168 SUPERSEDES V158 AS FLY-FIRST.** V168 *is* V158 plus one byte, so it carries both levers, and the two symptoms score from the SAME 15 s episode in different bands (grind 15-25 Hz, ratchet 5-12 Hz, both in `cs_tq`) — **separated by the INSTRUMENT, not by the build**. Fly V158 alone only to isolate the grind lever on FEEL. Card: `docs/scoring/DRIVE-CARD-V168.md`.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-assist-map-session.md` carries every finding, every retraction and the open-items list with what would close each.
## ✅ **THE SAME METHOD DOES *NOT* RETIRE V204 — and the reason is structural, not a shortfall of effort**

V207 died because its producer had an explicit cap: `min(·, LERP2(angle))` with `max(LERP2 Y) = 2560`.
I applied the identical method to `gp-0x6b4e`, the last unmeasured nonlinearity. **It does not close,
and the contrast is the point.**

### **`gp-0x3d8c` IS AN UNCAPPED ACCUMULATOR**
```asm
   0x271de  movea -0x61b8, gp, ep       ; slot array base, indexed by r14
   0x271e4  sld.hu 0x0, ep, r16         ; running min/max across the slots
   0x271ec  cmovc  r21, r16, r16        ; (repeated for bases -0x61d0, -0x61e8, -0x6324)
   ...
   0x272f6  add    r12, r2              ; the ACCUMULATE
   0x27300  cmp    0xa, r15             ; ~10 slots
   0x27304  jr     0x271de              ; loop
   0x27318  st.w   r6, -0x3d8c, gp      ; ** stored with NO cap, NO clamp, NO min() **
```
⇒ **the saturation to ±10240 is applied DOWNSTREAM, at the reader** (`0x27442`–`0x27454`,
`movea 0x2800` / `cmovle`), **not at the writer.** There is nothing between the accumulate and the
store that bounds it. A sum of ~10 signed halfword terms has no structural ceiling below the
saturation, so **the saturation is genuinely reachable on paper** — exactly unlike the compensation.

### ⭐ **WHICH IS WHY V204 SURVIVES AND V207 DID NOT**
```
   V207's producer   capped by min(., LERP2), max 2560  ->  bound PROVEN, gate cannot fire, RETIRED
   V204's producer   an uncapped 10-slot accumulator    ->  bound NOT PROVABLE, must be MEASURED
```
**That is the honest dividing line between what analysis can settle and what needs a drive**, and it is
worth having explicitly: the analytic route retired one build and confirmed the necessity of the other.

### ⚠ **WEAK CORROBORATION THAT IT MAY STILL BE SMALL — stated as weak**
`gp-0x6b4c`, the *sibling* 11-slot assist sum, is measured at **`|·| ≥ 4096` duty 0.000000 over 17,614
engaged frames.** If `gp-0x3d8c` behaves similarly it would sit far under 10240. **But it is a
different cell with a different slot mask** — `gp-0x6b4c`'s is `0xC4124` = [0,0,5,0,5,5,0,0,0,5,0],
four slots forced zero — so this transfers only as a prior, not as a bound. **[BELIEF]**

### ✅ **NEW STRUCTURE, NOT NAMED IN THIS KIT BEFORE**
The mixer's slot loop carries **four parallel slot arrays** at `gp-0x61b8`, `gp-0x61d0`, `gp-0x61e8`
and `gp-0x6324`, each walked by the same index, with **running min/max** (`cmp` + `cmovc`) alongside
the sum — and it writes **five** separate accumulators (`gp-0x3d74`, `gp-0x3d88`, `gp-0x3d70`,
`gp-0x3d98`, `gp-0x3d8c`) in one pass at `0x27308`–`0x27318`. Only the last is traced anywhere in this
kit; **the other four have never been named.**

## ✅⭐⭐ **THE SATURATION CENSUS IS CLOSED — the last gate CANNOT FIRE, and V207 is retired BEFORE flying**

I built V207 last tick to measure whether the delivery chain zero-rejects the merged command. **The
question is answerable from the image, and the answer is no.** Decompiling `FUN_000456a4` — rather
than reading assembly upward, which is what I had been doing and what `CLAUDE.md` warns against —
gives the whole structure at once:
```c
   uVar6 = gp-0x6a10;                                  // ABSOLUTE STEERING ANGLE
   if ( gp-0x6ac0 (|filtered motor rate|) > LERP1(angle) ) {         // a rate DEADBAND
       v = ((gp-0x6ac0 - LERP1(angle)) * cal(0xC6204)) >> 10;
       v = min(v, LERP2(angle));                       // <-- ** THE CAP **
       gp-0x6ad0 = (gp-0x6abe > 0) ? -v : v;
   } else gp-0x6ad0 = 0;
   gp-0x6acc = gp-0x6ace + gp-0x6ad0;
```
⇒ **the compensation is CAPPED by `min(·, LERP2)`**, so its bound is `max(LERP2's Y table)`:
```
   LERP1 (rate deadband)  X 0xC6832..6836 [3800, 4000, 4150]   Y 0xC6838..683C [5000, 3037, 1000]
   LERP2 (** the cap **)  X 0xC67D2..67D6 [3200, 3800, 4150]   Y 0xC67D8..67DC [ 512, 1024, 2560]
   gain cal 0xC6204 = 3072
```
```
   max compensation          = max(LERP2 Y)   =  2560
   governor gp-0x6ace        <= cal(0xC6202)  =  4762   (gp-0x4f64 is a min() with this)
   worst-case |gp-0x6acc|    = 4762 + 2560    =  7322    vs the gate window 8192
   ** MARGIN 870 COUNTS. THE GATE CANNOT FIRE. **
```
⊕ **The alternate rescaling branch is dead twice over.** `gp-0x6acc = cal(0xC648E) + (sum ×
cal(0xC6134))/1000` is guarded on `cal(0xC64BA) == -0x17`, and that cal reads **0** — disarmed — **and
even if armed it is an identity**: offset `0xC648E` = 0, gain `0xC6134` = 1000/1000 = 1.000.

### ✅ **THIS UPGRADES THE GOLDEN MODEL'S OWN CAVEAT**
`eps_chain_delivery.py` states the envelope *"4762 governor + 2560 compensation = 7322"* but adds
*"this model does not claim every combination is contained."* **It IS contained, provably** — the 2560
is not an observed typical value, it is `max(LERP2 Y)`, and the `min()` makes it a hard ceiling.

### 🛑🛑 **THE CENSUS IS NOW COMPLETE AND CLOSED**
```
   command -> motor path   every clamp: structurally unable to clip, or measured at zero duty
                           (incl. gp-0x6b70 at 1 frame in 72,916 engaged)
                           all six aggregator gates: producer <= window, cannot fire
   delivery chain          the merged-command zero-reject: producer bounded 870 counts under it
```
⇒ **NO clamp saturates and NO gate fires anywhere between the LKAS command and the motor.**
⇒ **The record's "command-gated saturation" model has NO mechanism in the firmware command path.**
⚠ That does not make the *symptom* description wrong — it means the saturating element, if one exists,
is **not in the firmware's command path**: it would have to be in the FOC/PWM inner loop, or mechanical.

### ✅ **V207 IS RETIRED BEFORE FLYING — which is the whole point of doing this analytically**
Its `.rwd` is renamed `SUPERSEDED-DO-NOT-FLASH-ANSWERED-…`. **A drive was saved by reading a
three-knot table.** ⊕ **V204 returns to the top of the shelf** — `gp-0x6b4e`'s writer saturation is
now the only unmeasured nonlinearity left in the path.

### ⭐ **AND THE COMPENSATION IS WORTH RECORDING IN ITS OWN RIGHT**
It is a **motor-rate deadband, scheduled on steering angle**: inert until `|filtered motor rate|`
exceeds LERP1(angle), whose knots **fall** with angle (5000 → 1000), then capped by LERP2(angle),
whose knots **rise** with angle (512 → 2560). **So it arms more easily and permits more at large
steering angles.** Never named anywhere in this kit before.

## ⭐⭐ **THE DELIVERY CHAIN HAS A ZERO-REJECT ON THE MERGED COMMAND — and it is the ONE gate not structurally dead**

The census had cleared the whole command→motor path: no clamp saturates, no aggregator gate can fire.
**The delivery chain was never censused.** It has one, and it is the first with a real margin.

### ✅ **BYTE-CONFIRMED AT `0x431D0`–`0x431D8`**
```asm
   0x431c4  ld.h   -0x6acc, gp, r9      ; the MERGED COMMAND
   0x431d0  addi   0x2000, r9, r6       ; r6 = x + 8192
   0x431d4  addi   -0x4001, r6, r0      ; flags only: carry iff r6 >= 16385
   0x431d8  cmovc  0x0, r9, r11         ; ** carry -> r11 = 0, else r11 = x **
```
⇒ **outside ±8192 the merged command is REPLACED BY ZERO**, not clipped. **A zero-reject on the
command itself is the most violent nonlinearity in the whole chain** — all-or-nothing, and exactly the
"command-gated saturation" shape the record's ratchet model needs.

### ✅ **AND ITS PRODUCER IS NOT STRUCTURALLY BOUNDED BELOW IT**
The comp-add, at `0x458B8`–`0x458CE`:
```asm
   0x458b8  ld.h  -0x6acc, gp, r13      ; previous value (lockstep read)
   0x458bc  ld.h  -0x6ace, gp, r12      ; the GOVERNOR OUTPUT
   0x458c0  ld.h  -0x4cc8, gp, r15      ; its lockstep twin
   0x458c4  st.h  r6,     -0x6ad0, gp   ; the COMPENSATION is stored here
   0x458c8  add   r6, r12               ; ** gp-0x6acc = gp-0x6ace + gp-0x6ad0 **
   0x458cc  sxh   r12                   ; sign-extended to int16 -- WRAPS at +-32768, no clamp
```
```
   gp-0x6ace   <= 4762     the governor output; gp-0x4f64 is pinned at its cal max 99.9%+ of the time
   gp-0x6ad0   ** UNKNOWN **  a LERP output (0x45892-0x458a2), sign-flipped on gp-0x6abe
   the gate    +-8192
```
⇒ **the gate fires iff `|governor + compensation| > 8192`, i.e. iff the compensation exceeds ~3430
while the governor is railed.** 🛑 **Every one of the aggregator's six gates was structurally dead
(producer ≤ window, guaranteed). This one is not — its firing is a genuine question.**
⊕ The golden model's own note concedes the point: the conservative envelope is *"4762 governor + 2560
compensation = 7322"*, **870 counts under the window**, and it says outright *"this model does not
claim every combination is contained."*

### 🛑 **AND NEITHER CELL HAS EVER BEEN MEASURED**
`gp-0x6acc` appears in the record only as a *chain description* — *"the aggregator DOES reach the motor
— the `gp-0x6acc` bridge"* — never as a measurement. `gp-0x6ad0` appears nowhere at all. **No probe in
sixty builds has read either.**

### ⭐ **THIS IS THE NEXT PROBE TARGET, AND IT OUTRANKS V204**
V204 asks whether `gp-0x6b4e` reaches a saturation that merely *clips* a model lane. **This asks
whether the merged command is being ZEROED** — a far larger effect, on the one gate the census could
not rule out, on a cell nothing has ever looked at.
⊕ `gp-0x6ad0` is the better tap of the two: it is the unknown term, `gp-0x6ace` is already bounded,
and their sum is what the gate tests. A tap on `gp-0x6ad0` gives the margin directly.
⚠ **[EVIDENCE]** the gate, the comp-add and the governor bound, all byte-confirmed above.
**[BELIEF]** that it actually fires — unmeasured, and the conservative envelope says it may not.

## 🛑🛑 **NO GATE REJECTS EITHER — the command-gated-saturation model has NO mechanism in this path**

Last tick killed the clamps. The remaining candidate was the aggregator's **zero-REJECT gates**, which
drop a lane to **0** rather than clipping it — a harder nonlinearity than any clamp, and exactly the
shape the record's model needs. Mirroring the compare bit-exactly:
```c
   (int)*(short *)(gp - 0x6b4e) * (uint)( (int)*(short *)(gp - 0x6b4e) + 0x2800U < 0x5001 )
```
an **unsigned** compare of `(x + W)` against `2W+1`, which passes **exactly `|x| ≤ W`** and rejects at
`|x| = W+1`. Against each lane's own producer bound:
```
   lane          window W   producer   can it ever reject?
   gp-0x6b4e       10240      10240    NO  -- writer SATURATES to +-10240 (0x27442..0x27454)
   gp-0x6b4c       10240      10240    NO  -- and |.| >= 4096 measured duty 0.000000 / 17,614 fr
   gp-0x6b26        1024        511    NO  -- producer clamped to 511 by cal 0xC407E
   gp-0x6b46        1024        512    NO  -- FUN_00036682 tail clamps its driver to +-0x200
   gp-0x6bd0        2048       1024    NO  -- <=1024 highway, 0 in 100 % of the micro regime
   gp-0x6bbe        2048        512    NO  -- flat +-512 bound, p50 74
```
⇒ **NOT ONE OF THE SIX CAN EVER FIRE.** `gp-0x6b4e` is the tightest case and it is **exact**: the
writer saturates to ±10240 and the gate passes `|x| ≤ 10240`, so the saturated value passes **by one
count**. That is not luck — **every window is sized at or above its own producer's bound.**

### ⭐ **WHICH REFRAMES THEM: THESE ARE FAULT GUARDS, NOT SHAPING NONLINEARITIES**
Honda sized each window so a healthy lane can never trip it. They exist to drop a **corrupted** lane
(a stuck or wild value), not to shape the control law. **Reading them as shaping elements — which the
"find what clips" hunt invites — is a category error**, and it is why they look promising on paper and
are dead in the code.

### 🛑🛑 **COMBINED: THE MODEL HAS NO MECHANISM ANYWHERE IN THE COMMAND→MOTOR PATH**
```
   clamps   every one either structurally unable to clip, or measured at zero duty --
            including the last survivor gp-0x6b70 at 1 frame in 72,916 engaged
   gates    none can fire, by construction
```
⇒ **If the ratchet is a command-gated saturation, the saturating element is NOT in this path.** The
remaining places it could live are the ones this census never covered: the **delivery chain** — the EME
shaper, the integrator, the FOC/PWM stage — and the **plant** itself.
⚠ **[EVIDENCE]** for the census; **[BELIEF]** that the model is therefore wrong — it may simply be
looking at the wrong stage.

### ✅ **V204 SURVIVES THIS — and it is the one thing here that does**
`gp-0x6b4e` is still **SATURATED BY ITS WRITER** at ±10240. The gate passing is irrelevant to that:
**the clipping already happened upstream**, at `0x27442..0x27454`. Whether `gp-0x3d8c` actually drives
it to the rail is **unmeasured**, and V204 reads exactly that cell. ⇒ **V204 stays the probe to fly**,
and it is now the *only* saturation question left standing in this path.

## 🛑🛑 **`gp-0x6b70` DOES NOT SATURATE — V205's question answered from cache, V206's best argument REFUTED**

V205 was built to ask whether `gp-0x6b70` clips, because the saturation census had eliminated every
other clamp in the command→motor path. **The answer was already on disk.**
`BUILD-LINEAGE-CATCHUP` records V96/V97's probe verbatim:
> *"**PROBE:** CAN 427 ← `gp-0x6b70` (LSB **12.8 ct**, no-clip `8192×5>>6 = 640 ≤ 1023`)"* ·
> *"`b7` = `gp-0x6b70 < 0` … V96's own rungs"*

⇒ 427 carries the **magnitude** at `raw = (|x|×5)>>6` and rung `b7` carries the **sign** — the design
law's own sign-bit-plus-magnitude pattern. The ±8192 writer clamp lands at **raw 640**. V100's
changelog repoints 427 away from `gp-0x6b70`, which bounds the window at **V96–V99: routes 7d / 7e /
7f / 80 / 81 / 82, all cached.** (427 arrives at half the base rate, so engagement is *interpolated
onto the 427 timebase* rather than assumed.)
```
   route  build          n_eng    p50     p95     max    AT CLAMP
   r7d    V96 (aborted)    542   1370    4990    8320    0.001845
   r7e    V97            30753    154    1856    3238    0.000000
   r7f    V97            34476    141    1677    3405    0.000000
   r80    V97              860    602    2483    2675    0.000000
   r81    V98             3296    883    2726    3162    0.000000
   r82    V99             2989    538    2624    3008    0.000000
   POOLED  72,916 engaged 427 frames, ONE at the clamp  ->  duty 0.000014
```

### 🛑 **CONSEQUENCE 1 — V206's STRONGER JUSTIFICATION IS DEAD**
Two ticks ago I re-justified V206 as *"raises the effective ceiling by exactly 2×"*, matching the
record's instruction to *"find what clips, and either raise its ceiling or soften its corner"* — and
argued it **survived the speed-invariance objection because it was about clip duty, not loop gain.**
**That argument is refuted: the ceiling is reached on 1 frame in 72,916.** ⇒ **V206 raises a ceiling
that is never reached.** What survives is only its **gain** effect (describing function, GATE 2
verified) — **which is the justification that IS in tension with the ratchet being speed-invariant.**
**V206 is demoted, not withdrawn**, and its case is now the weaker of the two.

### 🛑🛑 **CONSEQUENCE 2 — THE SATURATION MODEL HAS NO SURVIVING CLAMP IN THIS PATH**
The census eliminated every other clamp by structure or by measurement, and the sole survivor is now
measured non-saturating. ⇒ **If the ratchet is a command-gated saturation, the saturating element is
NOT a clamp in the command→motor path.** The remaining candidates are of a different kind: the
aggregator's **zero-REJECT gates**, which drop a lane to 0 rather than clipping it — a harder
nonlinearity than any clamp.

### ⭐ **CONSEQUENCE 3 — THIS RE-RANKS THE SHELF. V204 IS NOW THE PROBE TO FLY.**
`gp-0x6b4e` **SATURATES at ±10240 and its zero-reject window is exactly ±10240** — it is the one
element that both saturates and sits in a reject gate, and **its magnitude has never been measured.**
**V204 reads exactly that cell.** ⇒ **V204 → the probe worth a drive. V205 → demoted, its question
answered here.**
⊕ And V205's secondary value is answered too: `gp-0x6b70`'s operating range is now known —
**p50 141–1370, p95 1677–4990, against the 8192 clamp.**

### ✅ **THAT RANGE ALSO SIZES V206 HONESTLY**
The describing-function table was computed over A = 25–12800. The **real** operating range is
p50 ≈ 500, p95 ≈ 2500, where the measured N ratio is **0.47–0.72** ⇒ **V206 delivers a 1.4–2.1× gain
reduction where the signal actually lives**, not the 2× a flat reading would suggest.

## ✅⭐⭐ **AN UNREAD ON-CAR DOSE-RESPONSE FOR THE RATCHET LEVER — and the shelf gets a FREE endpoint**

Decoding the rung specs for the V102–V106 routes turned the sweep's numbers into measurements. The
biggest one had been sitting in two caches for weeks.

### ✅ **`b5` IS THE SAME RUNG ON FIVE CONSECUTIVE BUILDS**
From the lineage: V102's cave defines `b5 = |gp-0x6ae2| ≥ |gp-0x6b26|` — **modelled friction vs the
INERTIA term** — and V103 changes *"exactly ONE rung"* (`b3`), leaving `b5` byte-identical.
```
   route  build   n_eng     b5
   r96    V102    57,629   0.2481
   r9e    V103    40,638   0.2384
   ra4    V104    67,039   0.2305
   ra5    V105    49,021   0.2798
   ra6    V106   123,802   0.1907     <- V106 = V105 + ONE cell: the inertia curve
```
⇒ **inertia exceeds modelled friction ~75 % of engaged time** on every build. That alone is worth
knowing: **V196/V199/V202 halve the term that dominates**, not the minor one.

### ✅✅ **V105 → V106 IS A SINGLE-VARIABLE PAIR, AND IT MEASURES THE LEVER**
Tripling — see the correction below — the inertia term must LOWER `P(friction ≥ inertia)`. Episode
bootstrap, 4,000 resamples, episodes weighted by length, **per the kit's own “episodes not windows” rule**:
```
   rung                                    V105     V106     delta      95% CI
   b5  |friction| >= |INERTIA|   DOSED    0.2798   0.1907   -0.0891  [-0.1328, -0.0200]  EXCLUDES 0
   b7  a sign rung             CONTROL    0.3835   0.3324   -0.0511  [-0.1257, +0.0650]  includes 0
   b4  a sign rung             CONTROL    0.4338   0.4154   -0.0184  [-0.0413, +0.0217]  includes 0
```
⇒ **Direction correct, CI excludes zero, effect 1.7× the largest control.**
✅ **So `0xD7A5C` DEMONSTRABLY REACHES THE CAR, with the expected sign** — which had never been shown
for the ratchet lever now sitting on the shelf.
⚠ **Honest limits: 9 and 7 episodes.** The CI is wide and `b7` moved 57 % as much as `b5`. **This is
corroborating evidence, not proof.**

### 🛑 **CORRECTION TO A BUILD TAG: V106 IS ×2.000, NOT ×3.0**
Its artifact is named `GP6B26.X3.0`, but read from the images the engaged curve moves
**−14745/−8601/−2949 → −29490/−17202/−5898 — exactly ×2.000 on all three knots.**
**The dose in the tag is wrong**, and any dose-response quoted from the tag rather than the image is
off by 1.5×.

### ⭐⭐ **THE CAVE IS BYTE-IDENTICAL FROM V105 TO V202 — so the shelf already has this endpoint**
```
   v105 v106 v107 v108 v122 v202   cave@0xC4B34 sha  d3bb75d8fce08211   ALL IDENTICAL
   (v103/v104 differ: e997c1138528e334)
```
⇒ **V202/V205/V206 carry V105's exact rungs.** `b5` still means friction-vs-inertia and `b6` still
means the governor clip. **Every shelf build already reports the ratchet lever's effect, for zero
extra bytes.** The design law wants each build interpretable from one short drive — **it now is, on a
channel that was already there.**

### ✅ **PRE-REGISTERED, QUANTITATIVE, AND FREE**
Doses read from the images: V105 = 1.000×, V106 = 2.000×, **V202 = 0.333×**. Extrapolating the
measured per-doubling effect (−0.0891, CI [−0.1328, −0.0200]) across −1.585 doublings:
```
   ** b5 on V202 / V205 / V206 should read 0.42, plausible range 0.31 to 0.49 **
   against 0.2798 measured on V105 and 0.1907 on V106.
   b5 <= 0.28 (i.e. no rise at all) => the halving is NOT reaching the car, and the ratchet lever
   on the shelf is inert -- which would be the single most useful null available.
```
⚠ A log-dose extrapolation 1.6 doublings outside the measured range, from ONE pair. Stated as a range,
not a point.

## ✅ **SWEPT ALL 23 CACHED ROUTES FOR UNREAD RUNGS — 72 informative readings, and the REGISTRY STOPS AT r77**

V105's `b6` sat unread because nothing pointed at it. So I swept every cached route's cave rungs
(`0x14A` byte4 bits 7:3) on engaged frames and put each next to what the route registry says it means.
**23 routes, 72 informative readings, 43 degenerate.**

### ✅ **THE METHOD IS VALIDATED AGAINST A RECORDED VALUE — not asserted**
The lineage says V104's `b6` was `|r24| ≥ |r26|` with *"duty **1.0000** engaged ⇒ carried no
information."* My extraction on route `a4` reads **exactly 1.000000**. ⊕ And route `a5` (V105, same
cave with `b6` repointed to the governor comparison) reads **0.000000**. **A positive and a negative
control on the same bit, across two consecutive builds** ⇒ the bit mapping is right.

### ✅ **THREE ANSWERS READ OUT OF CACHES, NO DRIVE**
- **`r85` IS V100 — confirmed by THREE exact matches.** The lineage's V100 row records *"`d(b5)` AND
  `d(b6)` BOTH 0.000000 … with `b4` = 0.6057 on the same cell"*; `r85` reads **b5 0.000000, b6
  0.000000, b4 0.6057.** Attribution by data, not by guess.
- **`r9e` (V103): `b3` = 0.4675 ⇒ VARIES.** The lineage makes this a run-validity gate: *"🛑 IDENTITY:
  `b3` must VARY. A constant `b3` means the build is not V103 or the rung is dead — RUN-INVALIDATING,
  not a finding."* **The gate PASSES.** That had a stated pass/fail criterion and had never been checked.
- **🛑 `r97` CARRIED NO CAVE AT ALL.** The probe byte is **`7` in all 68,883 engaged frames** — a
  single value, and `0x07` is what the registry itself calls *"the stock STEER_SENSOR_STATUS with NO
  probe bits"*. **68,883 engaged frames — one of the largest exposures in the corpus — with zero
  instrument.** Any analysis expecting rungs from `r97` gets nothing, and nothing said so.

### 🛑 **THE STRUCTURAL GAP: THE REGISTRY STOPS AT r77**
`lib/route_build_registry.py` has entries through the V5x–V7x era. **All 13 newer routes — `r77`
through `ra6`, i.e. the entire V90–V106 arc — return "not in registry"**, so their rung meanings live
only in prose in the lineage. **That gap is exactly why V105's `b6` went unread**: the answer was on
disk and nothing connected it to the question.
⚠ **I did NOT extend the registry, because its `tail` field is the rlog hash and those are not in the
caches** — filling them would mean inventing identifiers. **The blocker is named rather than papered
over**: extending it needs the route tails from the rlog paths, not from `_scratch/cache`.
⊕ `analysis-2020accord/verify/unread_rung_sweep.py` is the tool; it re-runs in seconds and prints
every rung with its duty and its registry evidence, flagging degenerate readings separately.

### ⭐ **AND THE DISTINCTION THAT MATTERS: DEGENERATE ≠ NULL**
43 of the 115 readings are **0.000000 or 1.000000**. **A degenerate rung is not a null result — it is
an uninterpretable one**, and this kit's record shows the two being confused repeatedly (V64's *"the
null is on the GATE, not the hypothesis"*; V68's detector that *"has NEVER been non-zero"*; V104's
`b6` at duty 1.0000 *"carried no information"*). The sweep now labels them apart by construction.

## ✅⭐⭐ **THE SATURATION CENSUS CONVERGES ON `gp-0x6b70` — by elimination, from data already on disk**

The record's instruction is *"find what clips"*. I had found **one** saturating element and built a
ceiling raise for it without checking whether it was the only one, or the binding one. So I enumerated
**every clamp between the LKAS command and the motor**, read each ceiling from the image, and put each
next to its own producer's ceiling — because **a clamp only matters if its input can reach it.**

### ✅ **14 OF 18 CLAMPS CANNOT CLIP AT ALL**
Either the ceiling equals or exceeds its own producer (`gp-0x6b86` 12288 = 12288; the biquad's float
±12.0 = 12288; `gp-0x6b26`'s ±1024 window against a producer clamped to 511 by `0xC407E`;
`gp-0x6b46`'s ±1024 window against ±512 by construction), or the record already measured it inert
(the LKAS setpoint clip — V108 E3, pulled on its own null; the forward clamps `0xC61B2`/`0xC61B4`
— lane max 2505 < 3072; `gp-0x6bd0` — zero in 100 % of the micro regime; `gp-0x6bbe` — p50 74
against a ±2048 window; `gp-0x6b4c` — `|·| ≥ 4096` duty 0.000000 over 17,614 engaged frames).

### ✅✅ **AND THE BIGGEST REMAINING CANDIDATE IS MEASURED DEAD — IN A CACHE WE ALREADY HAVE**
`gp-0x4f64` is the **governor ceiling**, and the record measures it **pinned at its cal max 4762 for
99.9 %+ of engaged time** — so it is effectively a **constant 4762 limit** on the aggregator output,
whose own clamp is 10240, i.e. **2.15× higher.** Whether the aggregator ever reaches it had never been
read out. **But V105's cave `b6` is exactly `|gp-0x6b94| ≥ |gp-0x4f64|`, V105 FLEW as route `a5`, and
that cache is on disk.**
```
   route a5, 65,959 frames, 49,021 engaged (74.3 %)
   bit   duty        rung
    7    0.383468    sign                     <- positive control
    6    ** 0.000000 **  |gp-0x6b94| >= |gp-0x4f64|   THE GOVERNOR CLIP
    5    0.279778                             <- positive control
    4    0.433814                             <- positive control
    3    0.487444    identity                 <- positive control
```
⇒ **The aggregator NEVER reaches the governor ceiling. The governor clip is DEAD**, on 49,021 engaged
frames, **with four rungs on the same byte varying normally** — so this is not a stuck field or a dead
cave. ⊕ `gp-0x6ad6` was already measured the same way: **V100's `b5` duty 0.000000, CI [0, 0.0186],
with `b4` = 0.6057 on the same cell.**

### ⭐ **WHAT SURVIVES: `gp-0x6b70`, AND ONLY `gp-0x6b70`**
**Every other clamp in the command→motor path is either structurally unable to clip or measured at
zero duty.** `gp-0x6b70` is **the only one that can clip and has never been measured** — and it is
exactly the cell **V205 reads and V206 doses.**
⇒ **That is independent corroboration, reached by elimination rather than by following the same
thread.** It did not need a drive: the census came from the image and the duties from caches already
on disk.
⚠ One candidate remains genuinely open besides it — **`gp-0x6b84` (the resid mirror, ±0x3000)** —
unmeasured, and worth a rung if a future cave has a spare one.

## 🛑 **A VACUOUS TEST RETIRED, MY OWN AMPLITUDE PREDICTION WEAKENED — AND V206 RE-JUSTIFIED ON BETTER GROUNDS**

### 🛑 **THE FREQUENCY TEST CANNOT DISCRIMINATE — do not spend a drive endpoint on it**
I planned to predict the limit-cycle frequency and test it against the measured 6–9 Hz ratchet. The
ratchet is a **measured** lightly-damped resonance: 7.79 Hz, **Q 14–29**, ζ 0.017–0.036, ring-down,
three drives. A 2nd-order resonance sweeps 180° over roughly `f0/Q`:
```
   Q = 14  ->  the -180 deg crossing is pinned within +-0.28 Hz of 7.79
   Q = 29  ->  ...................................... +-0.13 Hz
```
⇒ **ANY limit cycle in a loop containing this resonance locks to 7.6–8.0 Hz BY CONSTRUCTION**, which
is inside the measured band. **The test is satisfied by every hypothesis that routes through the
resonance at all, so it has ZERO discriminating power.** Retired before it cost a drive endpoint.

### ⚠ **AND MY OWN AMPLITUDE PREDICTION IS IN TENSION WITH THE RECORD**
Last tick I pre-registered the describing-function peak as a limit-cycle amplitude. That peak is
**speed-indexed**, so it predicts the ratchet's amplitude should vary with speed:
```
   speed ct   320    640   1280   2560   5120        (~5, 10, 20, 40, 80 km/h at 64 ct/km/h)
   predicted  460    438    453    619   1224        ** 2.8x rise from 10 to 80 km/h **
```
But the record characterises the ratchet as **SPEED-INVARIANT**, with amplitude scaling on **wheel
rate / command magnitude** ([[accord-ratchet-is-a-lightly-damped-resonance]],
[[accord-ratchet-axis-is-wheel-rate]]). **Those point in opposite directions.**
⇒ **The limit-cycle-amplitude framing is WEAKENED.** ⚠ Not a clean refutation — a compensating speed
dependence in `|G(jω)|` could cancel it — but **the burden now sits on that coincidence**, and I should
not have pre-registered a speed-varying endpoint against a symptom the record calls speed-invariant.

### ⭐⭐ **BUT V206 IS RE-JUSTIFIED, AND ON THE RECORD'S OWN STATED TARGET**
`accord-ratchet-and-grind-are-command-gated-saturation.md` says it plainly:
> *"Sixty builds hunted a **linear** lever — a pole, a damper, a gain — for what is now measured to be
> a **command-triggered nonlinearity**. 🛑 **A linear lever cannot fix a relay.** The target is the
> SATURATING ELEMENT: **find what clips, and either raise its ceiling or soften its corner.**"*

**`0xC63AE` scales the LERP's input, so halving it DOUBLES the residual needed to reach the ceiling:**
```
   LERP ceiling at X[9] = 14490 at every speed
   k = 1024 (Honda)  ->  clips when |resid| >= 14490
   k =  512 (V206)   ->  clips when |resid| >= 28980        ** exactly 2x the ceiling **
   (resid is gated to +-20000 per term, so the Honda ceiling IS reachable and V206's is much less so)
```
⇒ **V206 raises the effective ceiling of a saturating element by exactly 2× — which is verbatim what
the record instructs.** ⊕ **And this justification SURVIVES the speed-invariance objection**, because
it is about **clipping duty**, not loop gain: the ceiling is 14490 at every speed.
⊕ It is also **the "raise its ceiling" branch, not "soften its corner"** — worth naming, because the
two have different side-effects and only one was available as a single virgin cal.

### ✅ **THE ENDPOINT IS NOW SHARPER — CLIP DUTY, NOT AMPLITUDE**
`gp-0x6b70` saturates at ±8192, and **V205 reads `gp-0x6b70` directly.** So the pre-registration
becomes:
```
   clip duty at +-8192 is HIGH   -> the saturation model is confirmed and V206 is aimed correctly
   clip duty is LOW but non-zero -> V206 is a partial fix; a quarter dose (k=256) quadruples the ceiling
   clip duty is IDENTICALLY ZERO -> the element NEVER clips, the saturation model is wrong HERE,
                                    and V206 should come off the shelf rather than be flown
```
**That is a far better endpoint than the amplitude one** — it is a duty, it needs no scale calibration,
it cannot be averaged away, and one of its three branches retires the build.

## ✅ **GATE 2 RUN ON V206 — IT PASSES, AND IT WAS NOT THE TRIVIAL CHECK IT LOOKED LIKE**

I built V206 last tick having run **GATE 1 but not GATE 2**. The kit makes both mandatory for any
dynamics change, and halving a loop gain is one. Running it properly changed a number I had published.

### 🛑 **"HALVING A GAIN HALVES THE LOOP GAIN" IS FALSE HERE**
`0xC63AE` scales the **input** of a **memoryless, CONCAVE** nonlinearity. Scaling the input down moves
the operating point onto a **STEEPER** part of the curve — and the curve's slope ratio between small
and mid signal is **6.7–10.7×**, so the steepening is large. The two effects fight. The correct
instrument for a memoryless nonlinearity inside a loop is the **describing function**:
```
   f(x) = sgn(x) * LERP(|x|)        the stage at unity
   g(x) = f(k*x)                    the stage with the dose
   ** N_g(A) = k * N_f(k*A)   NOT   k * N_f(A) **
```
### ✅ **MEASURED ON THE REAL CURVE — PASS, worst case 0.794**
```
   amplitude A       25     200     800    3200    6400   12800
   N ratio         0.486   0.472   0.619   0.794   0.771   0.658
```
**The ratio is never a flat 0.500 and never reaches 1.0.** Worst case **0.794 at speed 2560, A=3200**.
⇒ **The dose reduces first-harmonic loop gain at EVERY amplitude and EVERY speed tested**, and being
memoryless it **adds no phase at any frequency**. So the Nyquist locus contracts **radially toward the
origin with no rotation**, which cannot create an encirclement of −1 that did not already exist:
**a stable loop stays stable. GATE 2 PASSES.**

### 🛑 **CORRECTION TO MY OWN BUILDER — do not quote "half"**
V206's docstring said the dose halves the gain. **That is the small-signal limit only** (the
describing function confirms 0.486 at A=25). Across the amplitude range the dose buys **1.26× to
2.1×**, not a uniform 2×. The builder now carries the amplitude table.

### ⭐ **AND A FINDING NOBODY ASKED FOR: THE DESCRIBING FUNCTION PEAKS AT A ≈ 200–400**
```
   speed 2560   N(25)=3.64   N(200)=3.75   N(400)=3.55   N(1600)=1.95   N(12800)=0.61
   speed 5120   N(25)=3.31   N(200)=3.61   N(400)=3.80   N(1600)=2.09   N(12800)=0.63
```
**N is NON-MONOTONIC — it rises then falls, peaking near A = 200–400 counts.** A limit cycle sits where
`N(A)·|G(jω)| = 1`, so **a peak in N is a PREFERRED AMPLITUDE.** ⇒ **If the ratchet is a limit cycle
through this stage, its amplitude should sit near 200–400 counts** — a concrete, falsifiable
prediction that V205's probe can test directly, since it reads exactly this signal.
⊕ V206 lowers that peak from ~3.8 to ~1.9, which would either kill such a cycle or move it.
⚠ **[BELIEF]** — the describing function is EVIDENCE (computed from the image); that the ratchet is
this particular limit cycle is the hypothesis.

⊕ **This is the first GATE 2 in the kit run with a describing function rather than a linear Bode
sum.** For a memoryless nonlinearity in a loop it is the right instrument, and a linear sum would have
reported a flat 0.5 and missed that the dose is 1.6× weaker than that at mid amplitude.

## ✅⭐ **THE `0xC63AE` SIGN IS ESTABLISHED WITHOUT A DRIVE — V206 BUILT, AND ITS PRICE IS STATED**

### ✅ **THE RECORD'S OWN NINE-LINK TRACE ALREADY COVERS THIS STAGE**
`accord-friction-polarity-more-friction-is-more-assist.md` traces the polarity end to end, and **its
step 4 IS this stage**:
```
   4  gp-0x6b70 = clamp(sgn(res)*LERP(|res|), +-8192),  f' >= 0  =>  d/d(MODEL) >= 0 EVERYWHERE
   5  FUN_00037fe6:  gp-0x6ad6 += gp-0x6b70 * w         =>  target felt effort
   9  delivered = gp-0x6752 x gp-0x6b94                 =>  torque in the DRIVER'S direction
   measured cross-check:  d(gp-0x6b94)/d(gp-0x6b70) = +0.2529 / +0.2565
```
⇒ **Lowering `0xC63AE` shrinks `|gp-0x6b70|` toward zero.** V87 measured `gp-0x6b70` **negative
67.19 %** of engaged time, and shrinking a negative value *raises* it ⇒ **less assist on ~2/3 of
frames, more on ~1/3. Net: predominantly LESS assist, a slightly heavier wheel.**
✅ **So the sign needed no drive at all** — it was already in the record, one link away from where I
was looking.

### 🛑 **`0xC64B0` IS NOT A WEIGHT — the recorded `tp+0x74B0` trap, in a new form**
Step 5 of that trace reads *"`gp-0x6ad6 += gp-0x6b70 * w(0xC64B0)=1`"*, so I priced `0xC64B0` as a
gain. It reads **257 = `0x0101`** — **two enable BYTES, not a halfword weight.** `CLAUDE.md` names
this exact address as the off-by-0x1000 case that *"invented lane weights for what are 0/1 enable
flags"*. **The trap recurred in a new guise: not a wrong address, but a byte-pair read as a u16.**
⇒ **`0xC64B0` is not a lever.** The clean one is `0xC63AE`.

### ✅ **V206 = V202 + `0xC63AE` 1024 → 512.** ONE u16 cal, 34/34. `71bd8312c324de9c…`
```
   speed    small-signal gain    with the dose
     640        2.67x        ->     1.33x
    1280        3.04x        ->     1.52x
    2560        3.77x        ->     1.89x
    5120        3.43x        ->     1.72x
```
**GATE 1 is the cleanest possible**: `0xC63AE` has **exactly ONE site image-wide** (`0x38242`, the
reader) and **ZERO writers**, byte-stock on every build. Cal-only, **1 payload byte**, cave
byte-identical — **not the bricking class.** ⊕ It scales **this stage only**; the base power-assist
map is fed by the differently-transformed `Xsrc`/`Ysrc` and is untouched.

### ⚖ **THE PRICE, STATED RATHER THAN BURIED**
**The trade is: the soft relay's small-signal gain halves (the ratchet mechanism) and the wheel gets
somewhat heavier (an authority cost).** The operator has been explicit that he wants **low apparent
friction AND no ratcheting**; this buys one with some of the other. 🛑 **So V206 is deliberately NOT
the recommended build — V205 is**, because V205 measures `gp-0x6b70`'s actual range so this dose can
be **sized rather than guessed**. V206 exists so that if V205 says the range is large, the fix is
already cut. **A quarter dose is the obvious follow-up if half reads in the right direction.**

### 🛑 **THE BYTE-COUNT TRAP RECURRED — and is now DERIVED, not assumed**
I asserted "exactly 2 payload bytes" for a u16 cal. **1024 = `0x0400` → 512 = `0x0200` moves only the
HIGH byte — it is ONE byte.** Same shape as the V181 assertion bug and V198's `0x9540`→`0x9526`. The
builder now **computes** the expectation from the two values instead of stating it.

## ✅⭐ **THE RELAY QUESTION IS ANSWERED FROM THE IMAGE — it is a SOFT relay, and it has its own private gain cal**

**This reverses last tick's conclusion, and corrects a second claim I made there.** I said the curve
could not be read statically and that it *"reshapes with steering angle"*. The first is wrong because
the kit already mirrors `FUN_000389ec` integer-exactly; the second is wrong outright.

### ✅ **THE LERP IS THE POWER-ASSIST CURVE, AND THE MIRROR ALREADY COMPUTES IT**
`assist_map_mirror.py` (validated **200/200** against V72's flown probe) computes the very staging
arrays `FUN_00038148`'s LERP copies verbatim:
```
   0x39548  st.h r9,  -0x64b8, gp  <- gp-0x373c  == the mirror's Xi   (torque axis)
   0x39522  st.h r11, -0x641c, gp  <- gp-0x3714  == the mirror's Yi   (assist axis)
```
⇒ **`gp-0x6b70 = sgn(resid) × ASSIST_CURVE(|resid|)`** — the observer re-uses the **power-assist
curve**, applied to the residual instead of to driver torque. One additive side-effect line in the
mirror exposes it; the return value is unchanged.

### 🛑 **CORRECTION — the curve is SPEED-dependent, NOT angle-dependent**
```
   speed  640 / 2560 / 5120 : ** 1 distinct curve across 8 steering angles ** -> INVARIANT
   fixed angle, 6 speeds    : 6 distinct curves                              -> SPEED-DEPENDENT
   mode 24 vs 26            : identical at 2560; ONE knot differs 0.4 % at 640
```
Steering angle enters through `boost` into `SCALE`, which shapes the **downstream** `Xsrc`/`Ysrc` —
the base assist map — **not the `Xi`/`Yi` this LERP copies.** **My "stratify by steering angle"
instruction in `SHELF.md` was wrong and is now "stratify by SPEED".**

### ⭐ **IT IS NOT A HARD RELAY — IT IS A SOFT ONE, AND THAT IS THE INTERESTING PART**
```
   mode 26, speed 640:  X  0   166   333   678  1200  1800  3000  5000 10000 14490
                        Y  0   443   818  1369  1915  2223  2634  3146  4298  8192

   speed    gain near 0    mid-range (X6..X7)    ratio
     640       2.67x            0.256x           10.4x
    1280       3.04x            0.284x           10.7x
    2560       3.77x            0.352x           10.7x
    5120       3.43x            0.516x            6.7x
```
No flat top inside the operating range (the ceiling is only reached at 14490), **so the hard-relay
hypothesis is REFUTED.** But a curve with **2.7–3.8× gain at small input and 0.26–0.52× at mid-range —
a 6.7–10.7× compression ratio — IS a soft relay**, and high small-signal gain around a zero crossing
is exactly the shape that sustains a small-amplitude limit-cycle. **That is a far better-founded
ratchet mechanism than "it is a relay", and it is consistent with the record's own
"command-proportional Coulomb relay".**

### ⭐⭐ **AND THE STAGE HAS A PRIVATE GAIN CAL: `0xC63AE`**
```c
   0x38242   uVar7 = (|resid| * cal(0xC63AE)) >> 10        // cal = 1024 = unity
```
**`0xC63AE` = 1024, EXACTLY ONE site image-wide (`0x38242`), ZERO writers, VIRGIN** (kit's own
`tp_cal_readers.py`). It scales the LERP's **input**, so in the steep small-signal region the
effective gain scales with it **directly** — halving it halves the soft relay's small-signal gain.
⊕ **It scales THIS STAGE ONLY.** The base power-assist map is fed by `Xsrc`/`Ysrc`, a different
transform of the same source, so **the map itself is untouched.** That matters, because the curve's
shape is otherwise welded to the ROM assist records and could not be changed without changing
steering feel — **which is very likely why the ratchet has resisted sixty builds.**
⚠ **BUT `FUN_00038148` is NOT engagement-gated** (caller `FUN_0002214a` = task 0, 1000 Hz), so this
cal changes manual driving too. 🛑 **And its SIGN of effect on delivered assist is NOT established**
— the path runs `gp-0x6b70 → gp-0x6ad6` (a torque-tracking **reference**, not a motor torque), and the
record is emphatic that sign bets on this path have cost builds. **So it is NOT built this tick.**

### ⭐ **THIS MAKES V205 MORE VALUABLE, NOT LESS**
Its purpose is no longer *"is it a relay"* — that is answered. **It is now: measure `gp-0x6b70`'s
operating range and sign so the `0xC63AE` dose can be SIZED and SIGNED.** The probe reads the exact
signal the cal scales. **Sequence: fly V205 → read the range and sign → dose `0xC63AE`.**

## 🛑 **THE RELAY CURVE IS BUILT AT RUNTIME — it cannot be read from the image, so V205's drive is REQUIRED**

I set out to answer the relay question statically and make V205 unnecessary. **The answer is a
definitive no, and the reason is worth more than the original question.**

### THE TWO HOPS END IN LIVE VEHICLE STATE, NOT IN FLASH
`FUN_00038148`'s LERP reads X from `gp-0x64b6..` and Y from `gp-0x641c..`. `FUN_000389ec` fills both:
```
   0x39508   movea -0x3714, gp, ep        <-- ** ep = gp-0x3714, RAM staging, NOT a flash table **
   0x3950C   sld.hu 0x0, ep, r11              Y[0] <- gp-0x3714
   0x39522   st.h   r11, -0x641c, gp          ...
   0x39548   st.h   r9,  -0x64b8, gp          X[0] <- gp-0x373c
   0x39572   st.h   r16, -0x64b6, gp          X[1] <- gp-0x373a
```
and the staging itself is **COMPUTED, not copied**. Immediately before:
```
   ld.hu -0x6982 / -0x6a10 / -0x6a64 / -0x6984, gp     four LIVE cells
   cvtf.uws  x4                                        u16 -> float
   movhi 0x3a80, r0, r6        = 0.0009765625 = 1/1024     (Q10 -> float)
   mov   0x3dcccccd, r12       = 0.1f
   mulf.s ...                                          FLOAT arithmetic
   add 0x1, r14 / cmp 0x9, r14 / bgt / jr 0x39258       TEN iterations, one per knot
```
⇒ **`gp-0x6a10` is ABSOLUTE STEERING ANGLE** (already in the record). **The curve that decides
whether `gp-0x6b70` is a relay is re-derived every pass from steering angle and three other live
cells.** There is no static curve in the image to read. **V205's drive is REQUIRED, not merely
convenient.**

### ⭐ **AND THIS IS ITSELF THE MORE INTERESTING FINDING**
**A LERP that reshapes with steering angle means the stage's CHARACTER is condition-dependent** — it
can be a relay at one steering angle and smooth at another. ⇒ **A single static answer never existed**,
and the right endpoint for V205 is not *"is it a relay"* but **"over what conditions does it become
one"**, stratified by steering angle. That also fits a symptom the operator reports as coming and
going rather than being uniformly present.
⚠ **[BELIEF, not evidence]** — the reshaping is EVIDENCE (it is in the code); that it explains the
ratchet's intermittency is a hypothesis V205 can test.

### 🛑 **PROCESS — I HAND-ROLLED A gp SCAN AND HIT THE RECORDED ODD/EVEN TRAP**
My scan reported **`gp-0x3738`: 0 hits** and **`gp-0x373a`: 1 hit** for cells the disassembly plainly
reads at `0x39556`/`0x3955A`/`0x39560`/`0x39564`. Cause: `ld.hu -0x373a, gp, r16` encodes
**`hw2 = 0xC8C7`, not `0xC8C6`** — the `(disp | 1)` odd-displacement form `CLAUDE.md` names as a
recurring trap. **A raw `find(pack('<H', disp))` is blind to half the sites.**
✅ **The kit ALREADY HAS the correct scanner** — `analysis-2020accord/verify/scan_gp_relative_no_whitelist.py`
— whose own opcode census prints *"op 0x3F ld.hu ← MISSED by the old whitelist"*. **Use it. Do not
hand-roll a displacement scan.** The null it prevents is the expensive kind: *"0 hits"* reads as
*"dead cell"*.

## 🛑 **A SHAPE STATISTIC ON A BIT-FIELD LOOKED LIKE A FINDING — the relay question needs an instrument**

### THE QUESTION, AND WHY IT MATTERS
`FUN_00038148` ends by mapping the residual magnitude through a LERP and re-applying the sign:
```c
   uVar7 = (|resid| * cal(0xC63AE)) >> 10          // cal = 1024, so uVar7 = |resid|
   sVar8 = LERP(uVar7)                             // X at gp-0x64b6.., Y at gp-0x641c..
   gp-0x6b70 = sgn(resid) * sVar8,  clamped to +-cal(0xC6200) = 8192
```
**If that LERP saturates early the stage is a SIGNED CONSTANT — a relay** — and the record blames the
ratchet on exactly that: *"Engagement amplifies 6–9 Hz 2.8× via a COMMAND-PROPORTIONAL COULOMB RELAY."*
`gp-0x6b70` is also the traced route to `gp-0x6ad6`, the torque-tracking reference. **So this is the
ratchet's own named mechanism sitting on a cell we can read for 3 bytes.**
⚠ The LERP's knots are in RAM **two hops from any cal** (X from `gp-0x373c` staging, Y from an
`ep`-pointed table), so reading them statically is not the cheap path. Read the OUTPUT instead.

### 🛑 **AND HERE IS THE ERROR I NEARLY PUBLISHED**
V96–V99 all carried a 427 tap on `gp-0x6b70` (**V100's changelog repoints it AWAY from `gp-0x6b70`,
which dates the earlier target unambiguously**), and routes `r80`/`r81`/`r82` are cached. I computed a
rail-mass statistic on the cached `probe` column against `cs_tq`/`cs_rate` controls, and it looked like
a result — **0.21–0.45 for the probe vs 0.09–0.19 for the controls.**
Then the distinct-value count:
```
   r80  {15, 79, 143, 207}                    4 values, spaced 64
   r81  {23, 71, 87, 135, 199, 215}           6 values, spaced 48/16/48/64/16
   r82  {55, 103, 119, 167, 231, 247}         6 values, same pattern shifted 32
```
⇒ **spacings of 64 and 16 are BIT positions. That column is the cave's packed BOOLEAN RUNG byte, not
a magnitude.** A shape statistic on it is meaningless, and **my rail-mass numbers carry no information
about `gp-0x6b70` whatsoever. Retracted.**
⊕ `field` is the same rung byte; `row2raw14` is a row index. **There is NO magnitude channel for
`gp-0x6b70` anywhere in the corpus** — the earlier taps packed it into the rung byte.
⭐ **The control did not catch this; LOOKING AT THE DATA did.** `cs_tq` behaved perfectly — the
statistic was fine and the *channel* was wrong, which no control on a different channel can detect.
✅ **`rlog-tools/score/observer_relay_shape.py` now REFUSES a channel with fewer than 64 distinct
levels** and prints the levels it saw. **A rule someone must remember became a check that cannot be
forgotten.**

### ✅ **V205 = V202 + the 427 probe on `gp-0x6b70`, sar 6.** 40/40, 3 payload bytes.
`8cf100864be1d603…` · `0x55DF2` → `0x9490`, **sar 6** (±8192 ⇒ raw 0–128 / 896–1023, resolution 64).
**Three live probes now use three different shifts — 5, 5, 6 — because the shift is a property of the
SOURCE, never of the channel.** It answers in one drive: **few levels with mass at the rails ⇒ the
stage IS a relay**, localising the ratchet's named mechanism to one LERP worth the two hops to reach;
**smooth ⇒ the relay lives elsewhere**, worth as much; **railed at ±8192 ⇒ the observer is saturated
and the 41×-corrected `0xC63AA` sensitivity cannot be applied safely at all.**

### 🛑 **V203 RETIRED — `SUPERSEDED-DO-NOT-FLASH-LOWVALUE-…`**
Its question (is the notch bypassed by the pedestal?) **shrank to 7.9 %** once the EMA rate table was
read as flat `K = 20`. **The shelf is V202 (the fix) · V204 · V205 (the two probes worth a slot) · V199
(low-phase fallback).** ⭐ **Of the probes, V205 is the one to fly** — it aims at the ratchet, the one
symptom nothing in sixty builds has moved.

## 🛑🛑 **THE `0xC63AA` SENSITIVITY IS 41× UNDERSTATED IN THE RECORD — and the dilution ratio is nearly closed**

`BUILD-LINEAGE.md` parks `0xC63AA` as *"still the best structural lever, but it needs the **dilution
ratio** first"*, with the sensitivity recorded as `d(iVar6)/d(0xC63AA) = −(1/16)·(gp-0x6b4c/1024)`.
Mirroring `FUN_00038148`'s decompiled arithmetic exactly:
```c
   0x38148   SUM    = sum over SIX lanes of (x_i * gate_i * w_i) >> 10      // ZERO-REJECT gates
             scaled = (SUM * sgn(gp-0x6752) * cal(0xC6468)) >> 10           // cal = 2639
             target = scaled * 0x10                    // <-- the record DROPPED this
             model += ((target - model) * cal(0xC63AC)) >> 10               // alpha = 102/1024
             resid  = gp-0x6bfe - (model >> 4) + gp-0x6bfa                  // <-- it KEPT this
```
🛑 **The `*0x10` and the `>>4` CANCEL** — the model is stored 16× oversampled so the EMA keeps
precision; it is **not** a divide in the signal path. Perturbing the mirror rather than trusting the
algebra: **zeroing the weight moves the residual by 2.577 × `gp-0x6b4c`**, against the recorded 0.0625.
**2.577 / 0.0625 = 41.2×.**
⚠ **This cuts BOTH ways.** It is far more potent than the record believed — and therefore far more
able to destabilise. `gp-0x6b70` is clamped to ±cal(`0xC6200`) = **8192**, and 2.577 × a `gp-0x6b4c`
of 4000 already **exceeds** it. **This is a lever to size carefully, not a free one.**

### ✅ **TWO OF THE THREE UNKNOWNS ARE NOW CLOSED**
```
   the six model lanes, their weights and their ZERO-REJECT windows (V202)
     gp-0x6bd0  w 0xC63A0 = 1024   +-2048    0 in 100 % of the micro regime
     gp-0x6bbe  w 0xC63A2 = 1024   +-2048    p50 74
     gp-0x6b46  w 0xC63A4 = 1024   +-1024    ** <= 512 BY CONSTRUCTION **   <- CLOSED
     gp-0x6b26  w 0xC63A6 =  512   +-1024    <= 511, clamped by 0xC407E     (V181 halved this weight)
     gp-0x6b4e  w 0xC63A8 = 1024   +-10240   ** gp-0x3d8c SATURATED to +-10240 **   <- THE UNKNOWN
     gp-0x6b4c  w 0xC63AA = 1024   +-10240   < 4096 measured (duty 0.000000 for >= 4096 / 17,614 fr)
```
- **`gp-0x6b46` — CLOSED.** `FUN_00036682`'s tail clamps its driver to **±0x200** and EMAs toward it
  (cal `0xC63D2`), so it can never approach its own ±1024 reject window. A lag-compensator error, not
  a large term.
- **`gp-0x6b4e` — THE ONE REMAINING UNKNOWN, and it is BIG.** `0x2743E`–`0x2746A`:
  `ld.w -0x3d8c,gp,r11` · `movea 0x2800,r0,r26` · `bgt` · `movea -0x2800,r0,r9` · `cmovle r9,r11,r26`
  · `st.h r11,-0x6b4e,gp` (+ lockstep twin at `-0x4cd6`). ⇒ **`gp-0x3d8c` SATURATED to ±10240** — the
  same ceiling as `gp-0x6b4c`, and its reject window is exactly ±10240 so it **never drops out.**
```
   dilution = (gp-0x6b4c * w) / SUM, from the mirror with every other lane at its recorded value
     gp-0x6b4c      gp-0x6b4e = 0      gp-0x6b4e = 500
         250            43.2 %              15.8 %
        1000            75.3 %              42.9 %
        4000            92.4 %              75.1 %
```
⇒ **Whether `0xC63AA` is diluted or dominant is now ENTIRELY a question of how big `gp-0x6b4e` runs —
one number, never measured in the whole corpus.**

### ✅ **V204 = V202 + the 427 probe on `gp-0x6b4e`.** 40/40, 3 payload bytes, control cells identical.
`30e7da9f6d20ff13…` · `0x55DF2` → `0x94B2`, sar 5 (±10240 ⇒ raw 0–320 / 704–1023, resolution 32).
**Small ⇒ `0xC63AA` is the strongest cal-only structural lever in the kit, to be sized against the
±8192 clamp. Comparable or larger ⇒ genuinely diluted, and it should be STRUCK rather than left
parked** — which is itself worth knowing after it has sat open since 2026-08-20.

## 🛑 **THE 8 Hz RATCHET NOTCH STAYS REJECTED — and the friction lane is NOT “reverted to Honda”**

### ✅ **V184's 8 Hz NOTCH RE-PRICED UNDER THE CORRECTED UNDERSTANDING — still the wrong trade**
V184 was killed on **−40.5°** of phase, reasoned when the biquad was believed to sit in the **LKAS
command** path. It sits in the **base power-assist** path, so that phase is steering FEEL, not command
tracking — a different currency, and the lever deserved re-pricing. **29,348 candidates, same gate:**
```
   budget   6-9 Hz (ratchet)   16.3-23 Hz (grind)   phase @1/3/5 Hz        zeros poles radius
    5 deg        1.34x               0.91x          -0.3  -1.4  -4.6        9.25  9.12 0.9925
   12 deg        2.56x               0.93x          -1.2  -4.5 -11.8        8.62  8.38 0.9900
   20 deg        3.50x               0.94x          -2.2  -7.8 -19.2        8.25  7.88 0.9875
   40 deg        6.96x               1.03x          -6.3 -20.6 -39.8        8.25  6.88 0.9725
   -------------------------------------------------------------------------------------------
   V202          1.00x            ** 7.3x **              -7.8 at 5 Hz
```
⇒ **2.56× on the ratchet costs MORE phase than 7.3× on the grind**, and 🛑 **the 16.3–23 Hz column
shows it forfeits the grind fix entirely** (0.91–1.03× — at or slightly worse than Honda).
⇒ **There is ONE biquad and ONE zero pair: it serves the grind OR the ratchet, never both.**
**V184's rejection survives on its own terms. The biquad stays on the grind.** ⊕ Why it is so weak:
6–9 Hz is a 3 Hz-wide band at a low centre, and a notch narrow enough to pass the gate (r ≈ 0.99)
nulls only a sliver of it while its phase skirt reaches down into the 1–5 Hz band the driver lives in.
Added group delay at the 12° point is **+3.32 → +15.83 ms** vs V202's +3.80 → +5.52.

### 🛑🛑 **A MISLEADING LABEL IN MY OWN DOCS — the friction lane is at 0.200× HONDA, not Honda**
```
   friction = clamp(motor_rate * 12 / knee, +-1) * (|model| * K1/1024 + K0/1024)

   build   0xC40BC knee   0xC40D2 K1   multiplier vs Honda BELOW saturation   saturates at
   stock        600           102                1.000x                          50
   V122         3000         1020                2.000x                         250     <- FLEW
   V202         3000          102             ** 0.200x **                      250
```
**V177 reverted K1 (1020→102) and the record — mine included — calls that “K1 → Honda”.** But the
**ramp knee was never reverted**, and the knee multiplies the whole expression:
`(600/3000) × (102/102) = 0.200`. ⇒ **The lane is at ONE FIFTH of Honda's friction below saturation,
and saturation now needs 5× the motor rate (250 vs 50).** Above saturation it equals Honda exactly —
but the ratchet lives in the LOW-rate regime, which is entirely the 0.200× regime.
⊕ **A guard now prints this multiplier for every flashable image at close-out**, so “K1 → Honda” can
never again read as “friction is Honda's”.

### ⚖ **WHY IT IS LEFT ALONE — stated, not silently chosen**
The knee cuts **both ways** and the two directions are in genuine tension:
- **For leaving it:** Coulomb friction is *"exactly what makes torque ripple without motion"* — the
  ratchet's own signature (13.5× on `cs_tq`, 1.7× on `cs_rate`). 0.200× means **less ratchet**. It also
  matches the standing operator directive: *low apparent steering mass and friction to LKAS.*
- **Against:** the record's verified polarity is **more modelled friction = MORE assist** (nine links,
  Ghidra-traced). So 0.200× is also **an authority reduction** in that lane — against a stated goal.
🛑 **Reverting the knee to 600 would RAISE friction 5×, which contradicts a standing operator
instruction, so it is NOT built.** It is recorded here as the one remaining unattributed non-stock cell
in the friction lane, with its effect stated in both directions, for the operator to decide.

## ✅ **TWO AUTHORITY LEVERS CHECKED AND CLOSED — and a latent 18.52 Hz injector found silent**

### ✅ **THE SIGN-FLIPPING SQUARE-WAVE INJECTOR IS INERT — checked on the CURRENT build, not inherited**
`BUILD-LINEAGE.md` flags `0xC64DE` as *"a latent, engagement-triggered 18.5 Hz square-wave torque
injector wired into the 6× gain path, four halfwords from being live"*. Read from the images:
```
   0xC64DE (a BYTE, not a halfword)   stock 17 => 29.41 Hz     V202 27 => ** 18.52 Hz **
   0xC6734  n = 4
   0xC6736  X = [0, 31872, 31936, 32000]
   0xC673E  Y = [0, 0, 0, 0]      <-- stock AND V202.  ** SILENT. **
```
⇒ **NOT the grind's source.** Two independent reasons it cannot fire: the amplitude LERP is all zeros,
and the record's *"every other writer of `gp-0x6b2c` is a store-zero"*.
⚠ **But V18's 17→27 moved a latent injector INTO the grind band** (p10 16.33 / median 20.12 / p90
22.15 Hz), and its amplitude table sits **24 bytes from `0xC674E`/`0xC6750`, which this kit edits**
(1024→5120). **A guard is now in `closeout_verify_published.py` — every flashable image is checked.**
⊕ Reverting `0xC64DE` 27→17 is **a functional no-op while the amplitude is zero**, so it is hygiene,
not a fix. **Not built** — it would add a shelf build for no measurable change.

### ✅ **THE SETPOINT CLIP IS CLOSED — already built as V108 E3 and PULLED on its own null**
`0xC61BE` = 15360 was raised to 16384 and killed by its pre-registered endpoint: route `1e`, 93,356
frames / 924 s, achieved `|rate_c|` low-half-vs-top **still rising at all five speed bins** (3.89× /
3.12× / 2.91× / 2.62× / 2.14×, every CI excluding 1.0) where a bound clip would pin it flat.
**The clip is IDLE. Do not re-propose it.**

### ⭐ **SO WHAT DOES LIMIT AUTHORITY? THE ARITHMETIC, READ FROM THE IMAGE**
```
   lane_max = (setpoint_clip * gain) >> 15          clip = 15360

   stock       0xC646C =  891   ->   417 counts =  4.1 % of the aggregator clamp 10240
   V202 (6x)   0xC6CD0 = 5346   ->  2505        = 24.5 %
   8x          0xC6CD0 = 7128   ->  3341        = 32.6 %   ** exceeds the 3072 fwd clamps **
   10x         0xC6CD0 = 8910   ->  4176        = 40.8 %
```
⊕ Anchor reproduces exactly: `(15360 × 891) >> 15 = 417` = the separately recorded stock-V9 maximum.
⇒ **The aggregator has 4× unused headroom; nothing downstream binds at 6×.** The forward clamps
(`0xC61B2`/`0xC61B4` = 3072) are inert at 6× **because 2505 < 3072** — that is the real reason behind
*"0 % of the effect"*, and it also shows **why V101 had to raise them to 4096 for 8×: 3341 > 3072.**
⇒ **Every other candidate is measured non-binding**: the setpoint clip (idle), the `0xC520C` cap table
(`gp-0x4f64` at its max 4762 for 99.9 %+ of engaged time), the low-speed lockout (zeroed since V53).
⇒ 🛑 **`0xC6CD0` IS THE ONLY FIRMWARE AUTHORITY LEVER.** That is why it has been attempted three
times, and the enumeration is now closed rather than open.

### ⭐ **A TESTABLE PREDICTION THAT MAKES THE SEQUENCING CONCRETE**
The record measures **vibration ∝ m^1.74 but authority only ∝ m^0.88** for a gain step m. **A
sublinear authority exponent means something is eating the command — and the obvious candidate is the
vibration itself**: a command oscillating at 23 Hz partially cancels its own steering effect, so net
authority grows slower than the gain that produced it.
⇒ **If that is right, cutting the 23 Hz loop gain should RAISE the exponent toward 1.0**, and V202
cuts it **3.4×** there. **Sequence: fix the grind → re-measure the authority exponent → then raise the
gain.** ⚠ **BELIEF, not evidence** — it needs a gain pair measured on a notched base, which no drive
has ever provided. But it is the first mechanism offered for the sublinearity, which the record has
carried as a bare number since V101.

### 🛑 **TOOLING GOTCHA — `stock_fw_dump/code.bin` reads `0xFFFF` at `0xC6CD0`**
Because **V57 CREATED that cell** (it decoupled the forward reader off the shared `0xC646C`, which is
byte-identical 891 in stock and V202). **Do not use the stock dump as a stock reference for post-V57
migrated cals** — it will hand you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and `0xC64DE`
read correctly from it.

## ✅⭐ **V202 — THE NOTCH IS A POINT FIX; WIDENING THE SHOULDER IS WHERE THE ATTENUATION IS**

### 🛑 **FIRST, A RETRACTION OF MY OWN NUMBER FROM LAST TICK**
I said the pedestal `gp-0x6b7e` passes **64.6 %** of a 19.75 Hz input past the notch. **That is the
value at the CLAMP CEILING `K = 204`.** I quoted the ceiling without reading the table. The table:
```
   0xC68FE/0900/0902/0904   X = 0, 9830, 26214, 32768      a FLAT schedule
   0xC6906/0908/090A/090C   Y = 20, 20, 20, 20             K = 20 at EVERY knot
   K = 20 -> alpha 0.009766 -> fc 1.56 Hz -> ** 7.9 % at 19.75 Hz **
```
`0xC6382` = 41 is the alternate rate, selected only when the `gp-0x6b62` gate is true — and that gate
is measured at **duty 0.0000 over 75,227 engaged frames**, so it never fires engaged.
⇒ **The bypass is real but SMALL: 7.9 %, not 64.6 %. It is not a threat to the fix.** The probe keeps
its 3 bytes because 7.9 % of a large limiter cut can still dominate what survives a 25× notch, and
nobody has measured whether the friction-hold limiter cuts at all engaged.

### 🛑 **RE-CENTRING THE NOTCH BUYS NOTHING — a single biquad cannot cover the band**
A joint minimax over (zero, pole, radius) across **16.3–23.0 Hz** (the grind's p10–p90 on `cs_rate`
plus the ~23 Hz gain-driven line), under the same two constraints, improves worst-case leakage by
**1.1×** and makes the **median worse (15.6× → 5.0×)**. **V199's centre stays put.**
⇒ **The honest characterisation: the notch is a POINT fix.** V199 gives 15.6× at the median grind
frequency but **1.6× at the p10 edge and 2.2× at 23 Hz.** A drive whose peak lands low gets far less
than the design headline. **Score the drive stratified by its own peak frequency, never pooled.**

### ⭐ **WHAT ACTUALLY BUYS ATTENUATION IS PHASE — and V199 sits on the frontier at its budget**
```
   phase budget @5Hz   best 16.3-23 Hz attenuation
        2 deg                 4.3x
        3 deg                 4.8x     <- V199 is 4.7x at -2.95 deg: ON the frontier
        5 deg                 5.8x
        8 deg                 7.3x     <- V202
       12 deg                 9.7x
       20 deg                14.8x
```
Attenuation roughly **doubles per 8–10°**. ➕ **That phase is spent in the DRIVER-ASSIST loop, not the
LKAS command path** (last tick's decompile), so its cost is steering FEEL — and feel is judged in ms:
```
   added group delay 0.5-5 Hz     V199  +1.30 -> +2.37 ms
                                  V202  +3.80 -> +5.52 ms      ~3 ms more
```
**Human steering-feel thresholds are tens of ms.** ~3 ms is not perceptible, and it buys:
```
   f Hz     Honda    V199     V202      V199      V202
   16.33   0.9216  0.5717   0.4093      1.6x      2.3x
   18.00   0.9036  0.2969   0.1947      3.0x      4.6x
   20.12   0.8777  0.0561   0.0356     15.6x    ** 24.7x **
   21.00   0.8659  0.1762   0.1123      4.9x      7.7x
   22.15   0.8495  0.3039   0.1969      2.8x      4.3x
   23.00   0.8367  0.3794   0.2494      2.2x      3.4x
   26.00   0.7865  0.5542   0.3840      1.4x      2.0x
   30.00   0.7071  0.6684   0.4875      1.1x      1.5x
```
✅ **Strictly better at EVERY frequency in and above the band.** The **23 Hz** row is the one that
bears on **LKAS authority**: the record says that line is what the 8× gain excites, and the notch sits
in the loop that sustains it — 2.2× → 3.4×. ⚠ Still not enough to re-open a lever abandoned three
times; **the notch does NOT make 8× affordable on its own.**

### ✅ **V202 = V199 with the poles dropped 17.45 → 15.25 Hz, radius 0.9675 → 0.9600.**
**Zeros UNMOVED at 19.75 Hz**, still a true null (depth 0.00099). `max|H|` = **0.999998** ≤ 1.0, so it
still can only remove loop gain. 31/31, 9 payload bytes, cave byte-identical.
`2c5bc569c2c5e4c6…`
### ✅ **V203 = V202 + the 427 probe on `gp-0x6b7e`.** 40/40, 3 payload bytes. `0da3b7b9a4bfa906…`
⭐ **FLY V203.** 🛑 **V200/V201 renamed `SUPERSEDED-DO-NOT-FLASH-DOMINATED-…`** — probes on a base
V202 strictly dominates. **V199 stays flashable as the low-phase fallback; the shelf is V199 · V202 · V203.**

## 🛑🛑⭐ **CORRECTION + A THREAT TO V199: `gp-0x6b86` IS THE BASE POWER-ASSIST, AND THE NOTCH HAS A BYPASS**

**Decompiled `FUN_000352b4` [EVIDENCE].** The tp anchors check out exactly — `tp+0x749b` = `0xC649B`
(the arm cell), `tp+0x74fa` = `0xC64FA` (the CEIL), `tp+0x70a8/ac/b0/b4` = **the four coefficient cells
we have been editing** — so this is that filter, confirmed from the code and not from a label.

```
   gp-0x4f60 (TORQUE SENSOR) -> clamp +-8192 -> 10-knot assist-map LERP -> x sign x pol
     -> gp-0x6b7a -> friction-hold limiter -> gp-0x6b82 -> BIQUAD -> clamp +-12.0 -> x1024
     -> + gp-0x6b7e  <-- UNFILTERED, ADDED AFTER THE FILTER
     -> clamp +-0x3000 -> gp-0x6b86 -> FUN_0003aa2c aggregator
```

### 🛑 **CORRECTION — I published the wrong label last tick**
My exciter map said *"`gp-0x6b86` 12288 LIVE biquad output — **LKAS command**, 1–5 Hz."* **That is
WRONG.** `gp-0x6b86` is the **BASE POWER-ASSIST output**, driven by the torque sensor through the
10-knot assist map. The golden model's own gap note had it right; my label did not.
⇒ **openpilot's command does not pass through this filter.** Consequences, both ways:
- ❌ **The notch CANNOT fix peak command oscillation directly.** My close-out said it gives back phase
  *"in the currency peak command oscillation is paid in"* — **retracted.** The phase it spends is in the
  **driver-assist** loop. (Command oscillation may still fall if it *tracks* the grind, which the record
  says it does — but that is an indirect claim, not this filter acting on the command.)
- ✅ **The notch costs NOTHING in LKAS authority.** It is not in the command path, so no notch dose can
  reduce how hard openpilot can steer. That removes the whole authority objection from this lever.
- ✅ **It is still the right place for the GRIND**: motion → column torque → sensor → assist map →
  biquad → aggregator → motor → motion **is** the loop, and the notch cuts its gain at 19.75 Hz.

### 🛑🛑 **THE BYPASS — `gp-0x6b7e` IS NOT A CONSTANT, AND IT IS FAST ENOUGH TO CARRY THE GRIND**
From the decompile:
```c
   iVar33 = clamp(gp-0x6b7a - limited, +-0x3000) * bVar3      // bVar3 = the limiter is CUTTING
   iVar24 = iVar24 + ((iVar33*0x80 - iVar24) * K >> 11)       // an EMA, state at gp-0x381c
   gp-0x6b7e = (iVar24 -+ 0x80) >> 7                          // deadband +-0x80, then >> 7
```
`K` is clamped to **[2, 204]** ⇒ `alpha = K/2048` reaches **0.0996** ⇒ the EMA corner reaches
```
   fc = -ln(1 - 0.0996) * 1000 / (2*pi) = 16.7 Hz
   |H_ema(19.75 Hz)| = 0.0996 / |1 - 0.9004*exp(-j*0.1241)| = 0.0996 / 0.15419 = 0.646
```
⇒ **at its fastest the pedestal passes 64.6 % of a 19.75 Hz input straight past the notch.**
🛑 **So V199's 10.1× is an UPPER BOUND on what reaches `gp-0x6b86`.** If the grind arrives mostly
through the pedestal, a null on V199 would be **uninterpretable** — we could not separate *"the notch is
aimed wrong"* from *"the notch was bypassed"*. **That is a design failure on our side, and it is exactly
what the iteration doctrine says to fix BEFORE flying, not after.**
⊕ The pedestal is gated by `bVar3` = *the friction-hold limiter is cutting*. If that never fires
engaged, the whole parallel path is inert — **but nobody has ever measured it.**

### ✅ **V201 = V199 + the 427 probe on `gp-0x6b7e`.** 40/40, 3 payload bytes, control cells identical.
`354f9dfb93cf6fcd…` · `0x55DF2` → `0x9482`, `0x55E10` → sar 5 (±12288 span, resolution 32).
**It answers in one drive:** pedestal carries 19.75 Hz ⇒ **the notch is being bypassed**, and the lever
is the EMA rate `K` (the LERP at `tp+0x7900`/`0x7906`) or the ±0x80 deadband — **existing code, never
touched**. Quiet ⇒ V199's 10.1× is real. Zero throughout ⇒ the limiter never cuts engaged and this
path leaves the model.
⭐ **V201 is now the build to fly if you want ONE drive to be interpretable.** V199 is the fix; V200
probes the ratchet lever; **V201 probes whether the fix can even work.**

## 🛑🛑⭐ **EVERY NOTCH BUILD SINCE V188 ADDS LOOP GAIN — the lineage named this trap and I walked into it**

`BUILD-LINEAGE.md`, V105 section, in its own words:
> *"THE HIDDEN ONE: fixing DC with **poles at the notch angle** (the textbook narrow notch) forces
> `max|H|` to **1.098–1.608** … Fix: **Honda's own poles-BELOW-zeros layout**. **Check `max|H|` over
> 0–500 Hz against stock's 1.0000 before shipping any biquad edit.**"*

V188 onward put the poles **at the same angle as the zeros**. Measured from the built images:
```
   build   max|H| 0-500 Hz   zeros   poles   radius   verdict
   v122        1.0000        55.23   42.35   0.7966   PASS  (Honda's layout)
   v188/89/94  1.3533        19.40   19.40   0.9300   ** FAIL -- adds 35 % loop gain **
   v195/96/98  1.7177        19.75   19.75   0.9000   ** FAIL -- adds 72 % loop gain **
   v199        1.0000        19.75   17.45   0.9675   PASS
```
⇒ **V196 amplifies 1.88× Honda at 35 Hz, 4.57× at 45 Hz, 1.72× at Nyquist.** That is precisely what
V103's own GATE 2 exists to forbid — the sentence that licensed arming this section at all was
*"|H| ≤ 1.000032 everywhere 0.1–500 Hz ⇒ the filter can only REMOVE loop gain, never add it."*
**A filter that ADDS gain in the loop whose instability we are chasing is not a fix, it is a new risk.**

🛑 **HOW IT SHIPPED: V195's own GATE 2 assertion was written `check(mx <= 2.0, ...)`.** The bar is
stock's **1.0000**. The assertion passed 1.7177 without complaint. **The gate existed and was set wrong.**

### ⭐ **WHY THE BAR IS ABSOLUTE 1.0, NOT "vs Honda"**
`0xC649B` 0→1 **alone is INERT** — the record: *"the real arm is `gp-0x671a ≥ 5`, **never observed true
across 255,292 engaged frames** on three builds (V64/V67/V68)."* ⇒ **Honda ships this biquad DORMANT.**
The car ran `H ≡ 1` at every frequency for its whole life until **V103 armed it engaged-only** on
`gp-0x6806`. So Honda's 55.226 Hz null is **not a protection Honda relies on at this operating point**,
and the honest reference for *"is this filter worse than the car has ever been"* is `H ≡ 1`.
⇒ **Under that reference V199 is never worse than stock at ANY frequency; V196 is worse above 30 Hz.**
⊕ This also **deflates V108's revert rationale** for V105 (*"+14.0 dB at 61.1 Hz vs Honda's null"*): it
compared against a filter state **the car never occupies**.

### ✅ **V199 — THE SAME NOTCH, BUILT SO IT CANNOT ADD LOOP GAIN.** Base V196, 4 float32 cells, 31/31.
```
                     zeros    poles   radius   max|H|     d phase @5Hz   18-21 Hz atten
   V196 (defective)  19.75    19.75   0.9000   1.7177       -7.80 deg        16.8x
   V199              19.75    17.45   0.9675   1.000000     -2.95 deg        10.1x
```
**The zeros do not move** — 19.75 Hz, the `cs_rate` refit, kept exactly; the notch is still a TRUE null
(depth `|H|` = 0.00156 at 19.76 Hz). The poles come **below** the zeros, Honda's layout.
⊕ **It gives back 4.85° of LKAS-band phase** — the currency peak command oscillation is paid in, and the
reason V184's 8 Hz notch was abandoned at −40.5°. Added lag vs V196 is **positive at every LKAS
frequency**: +0.53° @0.5 Hz, +1.05° @1 Hz, +2.08° @2 Hz, +3.08° @3 Hz.
⊕ **The price, stated plainly: 10.1× attenuation over 18–21 Hz instead of 16.8×.** A sweep of 1,485
(pole frequency, radius) pairs found **521** that pass the gate; inside that set the tradeoff is hard and
monotone — the corner that is free at 54–74.5 Hz costs **−46° at 5 Hz**, the corner that is free in phase
gives only **6.9×**. **V199 is the deepest notch with added phase ≤ 3°.**
⊕ 55.226 Hz: **V196 1.5183 → V199 0.8150**, so V199 is below unity there too.
`c86646ab48c4a625…` · preflight **8/8** · 9 payload bytes · cave byte-identical · CRC 50/50.

### ✅ **V200 = V199 + the 427 probe on `gp-0x6ada` (the r24 rate lane).** 40/40, 2 payload bytes.
`db0b613aad11e678…` — V198's probe rebuilt on the corrected base.

### 🛑 **V194 · V195 · V196 · V198 ARE RENAMED `SUPERSEDED-DO-NOT-FLASH-GATE2-…`**
All four carry a filter that adds 35–72 % loop gain. **The shelf is now TWO: V199 and V200.**
⚠ Their `_plain_image.bin` files stay under their own names — V199 chains off V196's image.

## ✅⭐ **V198 SUPERSEDES V197 — probe the BIGGEST 8 Hz exciter, not the second-biggest**
The completed exciter map reordered the probe choice, and following it beats defending yesterday's
build:
```
   gp-0x6ada   8192 clamp   r24 RATE LANE, omega^1     <-- V198 probes this
   gp-0x6bbe   2048 clamp   viscous, omega^1           <-- V197 probed this  (SUPERSEDED)
   gp-0x6b26    511 eff.    inertia, omega^2           <-- what V196 halves
```
⇒ the rate lane carries **4× the viscous term's clamp and 8× the inertia term's**, so it is the
**biggest competitor to the term V196 halves.** Measuring the largest candidate is worth more than
measuring the second-largest.
⊕ The record already designates this exact cell as a telemetry target: *"both inline lanes are
mirrored to RAM and nothing reads them — `gp-0x6ada` (r24) / `gp-0x6adc` (r26), post-clamp ⇒ free
zero-blast-radius telemetry."* Reading it costs nothing and disturbs nothing.
⊕ And unlike every other candidate, the rate lanes have a **MEASURED on-car dose-response history**
(V62's `sar`×2: *"18–22 Hz down 8–42×"*; V88's Lever B: *"grinding FIXED on-car"*) — so if the
measurement says a bigger lever is needed, it lands somewhere already characterised.
✅ **V198 = V196 + 3 telemetry bytes.** `0x55DF2` 0x9540→0x9526, `0x55E10` sar 4→sar 5. 40/40.
`9fbbf90b0bed9cb32eb7c3a44a30c2108f361a736ff3f1ebc205f47e5cf3190d`
⊕ **sar 5** because the aggregator clamps `gp-0x6ada` to ±8192: positives raw 0–256, negatives
768–1023, resolution 32, unambiguous to |x| ≤ 16352. **Three probes, three different shifts — 6, 3,
5 — because the shift is a property of the SOURCE, never of the channel.**
⊕ V197's `.rwd` is renamed `SUPERSEDED-DO-NOT-FLASH-…` and its decoder deleted. **The shelf is four:
V194 · V195 · V196 · V198.**

## ✅⭐ **THE EXCITER MAP IS COMPLETE — zero unknowns, and my "4 LIVE" count was WRONG**
The three terms I could not label are identified. Two of them were hiding in plain sight: the
aggregator's own tail stores them.
```c
   *(short *)(gp - 0x6adc) = iVar21;      *(short *)(gp - 0x6ada) = iVar16;
```
⇒ **`iVar21` and `iVar16` ARE THE r26 AND r24 RATE LANES** — the lanes V62–V88 spent a dozen builds
on. They are **LIVE, summed into the aggregator, with 8192 clamps.**
⇒ **`gp-0x6ade` has exactly ONE site in the whole image — a READ at `0x3AA48` — and NO WRITER.**
Both methods agree (Ghidra: 1 match; raw byte scan: 1 site). It holds its BSS-zeroed value forever,
so it contributes **nothing**. **DEAD.**
```
   cell        clamp   status
   gp-0x6b86   12288   LIVE    the biquad output -- LKAS command, 1-5 Hz
   gp-0x6b4c   10240   LIVE    the 11-slot assist sum
   gp-0x6ad4   10240   eliminated as a cause by V56
   gp-0x6b62    8192   DEAD ENGAGED (0.0000 / 75,227 frames)
   gp-0x6adc    8192   LIVE    <-- the r26 RATE LANE
   gp-0x6ada    8192   LIVE    <-- the r24 RATE LANE
   gp-0x6bbe    2048   LIVE    viscous, omega^1 -- BYTE-STOCK across the whole arc
   gp-0x6bd0    2048   DEAD in 100 % of the micro regime
   gp-0x6ade    1024   DEAD    read once, never written
   gp-0x6b26    1024   LIVE    the inertia term, omega^2, clamped to 511   <-- V196 halves this
```
⇒ **6 LIVE · 4 dead or eliminated · 0 unidentified.** My earlier "4 LIVE" was wrong — it missed the
two rate lanes because the decompiler had named them `iVar21`/`iVar16`.

### ⭐ **WHAT THIS CHANGES: r24/r26 CARRY 8× THE INERTIA TERM'S AUTHORITY**
```
   gp-0x6ada / gp-0x6adc   clamp 8192      rate-derived => omega^1, so live at 8 Hz
   gp-0x6b26               clamp 1024      further clamped to 511 by 0xC407E
```
✅ **And they are already-PROVEN grind levers**, both carried on V196:
- **V62's `sar`×2 on the r24 lane — *"18–22 Hz down 8–42×, the kit's first measured fix"***
- **V88's Lever B, `0xC6446` = 5244 — *"grinding FIXED on-car"*, operator-confirmed**

⇒ **IF THE RATCHET NEEDS A BIGGER LEVER THAN THE INERTIA TERM, THE RATE LANES ARE WHERE TO LOOK.**
They have 8× the authority, they are ω¹ so they carry 8 Hz content, and unlike the viscous path they
are **already partly characterised on-car**. That is a far better-founded direction than any new
mechanism — and it needs **no new hypothesis**, only a dose choice on a lane with a measured
dose-response history.
⚠ **But not before V197's measurement.** The same discipline applies: the rate lanes' 8 Hz content
has not been measured either, and three of my hypotheses died this session for exactly that reason.

## ✅ **V197 — V196 PLUS THE ONE MEASUREMENT THAT SAYS WHETHER ITS RATCHET LEVER IS WELL AIMED**
V196 halves the **smallest live exciter** (`gp-0x6b26`, clamp 1024, further clamped to 511) while
`gp-0x6bbe` is live, **ω¹**, carries **twice the clamp**, and is **byte-stock across the whole arc**.
Constants cannot say which dominates the 8 Hz sum. **So measure it rather than guess again.**
```
   0x55DF2  hw2   0x9540 (gp-0x6AC0)  ->  0x9442 (gp-0x6BBE)
   0x55E10  shift sar 4               ->  sar 3
   V197 vs V196 = 3 payload bytes, ALL TELEMETRY. Not one control cell changes.
```
✅ **40/40 assertions.** `b70483e02b110b740aa93635f9ddeebe1ddc19b38958b824598eba712a4d392b`
⊕ **The shift is sized to the SOURCE again:** `gp-0x6bbe` is clamped to ±2048 by its writer, so
**sar 3** keeps 8-count resolution with the sign intact (positives raw 0–256, negatives 768–1023,
unambiguous to |x| ≤ 4088). V194 used sar 6 because `gp-0x6c2c` spans the full int16 — **using sar 6
here would throw away three bits of a ±2048 signal.**
⊕ Decoder: `rlog-tools/probe/decode_v197_viscous_term.py <tag> --v197`, which refuses on any other
build's capture.

⊕ **A correction to my own earlier summaries while verifying this:** V196 does **NOT** carry V190's
`0xC64AE` disable, V191's `0xC640A`, V192's slew curve or V193's dwell — it descends
V195 ← V189 ← V188 ← V185, which never included them. **V196's complete lever set is: the notch,
K1 → Honda, accel alpha → Honda, w[3] halved, FactorC m27 → stock, and the engaged inertia half
dose.** The builder now asserts m26 = half dose and m27 = Honda separately, which is what caught it.

⇒ **THE FORK IS NOW CLEAN:** fly **V196** to fix, or **V198** to fix *and* learn where the ratchet's
energy actually comes from. They are the same car; the probe costs three telemetry bytes.
⚠ **V197 (this build) was SUPERSEDED by V198** — the completed exciter map showed `gp-0x6ada`
carries 4× `gp-0x6bbe`'s clamp, so it is the more informative target. Section above.

## ⭐ **THE EXCITER LIST: ONLY FOUR AGGREGATOR TERMS ARE LIVE, AND V196 TOUCHES THE SMALLEST**
The ratchet is a **plant** resonance, so firmware can only reduce what **excites** it. The exciters
are the terms summed in `FUN_0003aa2c` into `gp-0x6b94`. Each carries a hard clamp — an upper bound
on its contribution, readable from the decompiled constants without any probe:
```
   cell        clamp   what it is                     status
   gp-0x6b86   12288   the BIQUAD output              LIVE - carries the LKAS command (1-5 Hz)
   gp-0x6b4c   10240   the 11-slot assist sum         LIVE - low frequency
   gp-0x6ad4   10240   unfiltered residual PID lane   ELIMINATED as a cause by V56
   gp-0x6b62    8192   return-centre / detent         DEAD ENGAGED (0.0000 / 75,227 frames)
   iVar21       8192   a clamped branch product       unidentified
   iVar16       8192   a clamped branch product       unidentified
   gp-0x6bbe    2048   VISCOUS + DC pedestal          LIVE - rate-derived, omega^1
   gp-0x6bd0    2048   the base-assist damper         DEAD in 100 % of the micro regime
   gp-0x6ade    1024   a clamped input                unidentified
   gp-0x6b26    1024   the INERTIA term  <-- V196     LIVE - acceleration-derived, omega^2
                                                             and clamped further, to 511
```
⇒ **4 LIVE · 3 dead or eliminated · 3 unidentified.**
🛑 **V196 halves the term with the SMALLEST clamp of any live exciter — 1024 against 12288 for
the biquad output, 12× less authority**, and `0xC407E` clamps it to 511 on top of that.
✅ **That is not automatically bad**: the large terms carry the LKAS command, which the record shows
is a **1–5 Hz low-pass**, so their energy sits well BELOW the ratchet. The inertia term is the only
**ω²** one — concentrated exactly where the ratchet is. **A small clamp on a high-frequency term can
still dominate the 8 Hz sum.** Constants cannot settle which.

### ⭐ **`gp-0x6bbe` IS THE NEXT THING TO MEASURE — AND IT IS BYTE-STOCK**
It is **LIVE**, **rate-derived (ω¹, so also elevated at 8 Hz)**, and carries **twice the inertia
term's clamp**. Its writer `FUN_00034a72` was decompiled and its cals identified:
```
   0xC6370  2560   scales gp-0x6c2e (the 2nd accel EMA) into this path
   0xC6372   205   EMA coefficient on the torque term
   0xC615A   512   fallback clamp when gp-0x6a62 >= 0x7d01
   ** identical on STOCK, V122 and V196 => the VISCOUS PATH IS BYTE-STOCK, untouched by the
      entire post-V38 arc **
```
⊕ Note `0xC6370` scales **`gp-0x6c2e`**, the second acceleration EMA flagged as unexplored earlier —
so that channel does reach the viscous path after all.

🛑 **AND DELIBERATELY, NO BUILD FOLLOWS FROM THIS.** Three of my hypotheses have been killed by
their own tests this session (Coulomb sign-flip, common-cause correlation, relay-as-oscillator).
Proposing a fourth speculative lever on an untouched, byte-stock path — on the strength of a clamp
width and a frequency-weighting argument, with **no measurement of its actual 8 Hz content** — would
be repeating exactly that pattern.
⇒ **The honest next step is a MEASUREMENT, not a lever: repoint the 427 probe onto `gp-0x6bbe` and
compare its 8 Hz content against the inertia term's.** That decides whether V196 is touching the
dominant exciter or a minor one, and it is the same one-channel move that V194 already demonstrates.

## 🛑 **MY RELAY CLAIM OVERREACHED — the ratchet is a DRIVEN RESONANCE, not a relay limit cycle**
Last section proposed the flying build's saturated inertia term as the ratchet's mechanism. That put
it in direct tension with the recorded ★★★★★ *"lightly-damped resonance, ring-down ζ 0.017–0.036,
**limit cycle EXCLUDED**"*, because a relay in a loop is exactly what makes a limit cycle. **Tested,
and the record wins.**
```
   1037 engaged-creep windows, cs_tq.  f0 median 7.81 Hz (IQR 7.62-8.40)

   HARMONIC STRUCTURE  (prominence above local background)
     f0  19.45   3*f0  4.14   5*f0  2.95   2*f0 (even control) 3.70   off-harmonic control 3.41
     3f0/2f0 = 1.12      3f0/control = 1.21      => NO odd-harmonic excess.  A relay would show one.

   AMPLITUDE DISTRIBUTION
     log10 peak power sd 1.025  =>  p10-p90 spans 521x
     => BROAD.  A limit cycle's amplitude is set by the loop and would span a few x, not 500.
```
⇒ **both discriminating signatures say DRIVEN RESONANCE.** The record's limit-cycle exclusion is
corroborated by two independent statistics, and **my relay-as-oscillator claim is withdrawn.**

### ✅ WHAT SURVIVES, AND IT STILL SUPPORTS V196
The term can still be **saturated** — that arithmetic is unchanged (flying saturates at
|accel| > 1065, V196 at 6389). What is withdrawn is that saturation *creates* the oscillation.
```
   the plant owns the resonance (Q 14-29, ring-down) -- nothing in the firmware sets its frequency
   a PINNED, sign-flipping term injects broadband energy that EXCITES that resonance
   => V196 reduces an EXCITER, not the oscillator
```
✅ **The sign-safety argument SURVIVES INTACT.** Reducing a saturated term's injected energy is
directionally safe **whichever way its sign runs** — less injection is less excitation either way.
That was the part that mattered for V196, and it does not depend on the limit-cycle claim.
⚠ But the *strength* of the rationale is lower: **V196 reduces one exciter among several**, rather
than removing the mechanism. Expect a partial effect, not elimination.

➕ **THIS IS THE THIRD HYPOTHESIS OF MINE KILLED BY ITS OWN TEST THIS SESSION** — after the Coulomb
sign-flip and the common-cause correlation. In each case the discriminating control was designed
before the result was known. **That is the process working, not failing**; the alternative is
carrying three wrong mechanisms into a build.

## ⭐⭐ **THE FLYING BUILD'S INERTIA TERM IS A SATURATED RELAY — the best mechanism for the ratchet yet**
```
   gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E)=511 )
   scale = |L| * 273 / 2**24 ;  the clamp binds when |accel| > 511 / scale

                        L        scale    saturates at |accel|
   FLYING V122     -29490       0.4799            1065     <-- pinned almost always
   V195 = Honda     -9830       0.1600            3195
   V196 = half      -4915       0.0800            6389     <-- 6x more headroom
   detector fires at                             12800
```
🛑 **The flying build saturates at |accel| > 1065 — TWELVE TIMES below the detector's own
threshold.** Above that the term is **pinned at ±511 and flips sign with acceleration: a RELAY, not
a proportional inertia.** A sign-flipping constant driven by acceleration is exactly a
ratchet-generating mechanism, and this is a far better account than "anti-damping".
✅ **SO THE REVERTS' REAL EFFECT IS NOT REDUCING A GAIN — IT IS UN-SATURATING THE TERM.** V196 keeps
it **proportional across 6× more of the acceleration range** than the build on the car. That also
explains the dose ladder without appealing to a sign: 3× Honda ⇒ pinned from 1065; Honda ⇒ 3195;
half ⇒ 6389.
⊕ **This is a stronger rationale than the one V196 was built on**, and it does **not** depend on the
anti-damping sign that V190/V196 flagged as BELIEF. Un-saturating a relay is directionally safe
whichever way the sign runs. **The pre-registered "ratchet gets worse ⇒ revert" outcome stays, but
it is now less likely.**
⊕ Compare the recorded [[accord-v80-damper-relay-and-grind1-inert]]: *"the damper became a RELAY,
worst grinding ever — restore the RAMP, don't merely lower k."* **Same failure shape, different
lane** — and the same fix: get the term back into its proportional region.

### ⚠ **AND THE TWO REMAINING BRANCHES ARE MUTUALLY EXCLUSIVE**
```
   |accel| > 12800   the detector fires (V191/V192/V193 act) -- but the inertia term saturated at
                     1065-6389 long before, so V196's half-dose does little there
   |accel| < 3195    the half-dose works proportionally -- but the detector NEVER fires, so
                     V191/V192/V193 are inert
```
⇒ **V196 and V194 are effective in DISJOINT regimes.** One measurement decides which branch is worth
pursuing at all: **V194's probe on `gp-0x6c2c`.** That is now the strongest reason to fly V194 — not
to fix anything, but because it tells us which of the two remaining ratchet routes is live.

### ➕ The range bound, for completeness
The term is clamped at 511 against an aggregator spanning ±10240, so it is **at most 5.0 % of the
command**, and halving it moves **at most 2.5 %**. ⚠ That is its share of FULL RANGE; because it is
acceleration-derived its share of the **8 Hz content** is larger, by an amount this bound cannot
determine.

## ✅ **CLOSE-OUT VERIFICATION — 21/21 FROM DISK, AND BOTH BUILDERS REPRODUCE BIT-FOR-BIT**
Everything published this session re-checked from the filesystem, not from a build log or from
memory:
```
   [1] published image SHA256 vs disk          V194 / V195 / V196   all match
   [2] every claimed cell value on V196        notch B0 -1.9846207 (19.75 Hz) - pole^2 0.81
                                               K1 102 (not the flying 1020) - w[3] 512
                                               engaged inertia [-4915,-2867,-983] = half Honda
                                               MANUAL inertia [-9830,-5734,-1966] UNTOUCHED
                                               0xC407E frozen 511 - V196 vs V195 = exactly 6 bytes
   [3] superseded artifacts                    exactly 3 flashable; no V185-V193 unmarked
   [4] mandatory-read caps                     largest 190.9 KB (BUILD-LINEAGE-PART1), cap 256
   [5] every tool written this session parses
   + BOTH BUILDERS RE-RUN AND REPRODUCE BIT-FOR-BIT   V195 a3ea8683... V196 f904e43a...
```
⊕ **Worth stating explicitly: V196's detector dwell `0xC64DD` is Honda's 50** — V193's widening is
**not** carried, because V196 descends V195 ← V189, not through V193. **That is what makes V196
unable to change normal driving**, and it is now asserted rather than assumed.
⊕ Tool: `analysis-2020accord/verify/closeout_verify_published.py` — re-runnable in one command.

## ✅⭐ **A SOUND NOTCH PREDICTION IS RESTORED — and it is the pre-registration for the drive**
The 21.5× open-loop score was wrong because it multiplied the **whole** spectrum by `|H|²`,
attenuating the broadband floor a notch in the assist path cannot touch. The closed-loop fix went out
with the contaminated ratio it rested on. The defensible model splits the spectrum:
```
   P(f) = B(f) + X(f)          B = the smooth background (road / plant / sensor floor)
                               X = the EXCESS, i.e. the resonance the loop amplifies
   only X passes the assist path  =>  P_new = B + X * |H_new / H_old|^2
```
and reports **the same slope-corrected excess the scorer prints**, so it is directly comparable to a
drive.
```
   cs_rate GRIND 15-25 Hz, 67 routes, null ~3.9x
                            p10    p25    p50    p75    p90
   measured (flying)       11.8   22.5   31.6   64.8  136.4
   after V188 notch         1.6    1.9    2.8    5.0    9.5
   after V195 notch         1.3    1.5    2.2    4.1    7.3

   reduction, V195:  p25 9.7x   median 12.7x   p75 23.4x
   routes falling BELOW the null:   V195  49/67 (73 %)     V188  43/67 (64 %)
```
✅ **THE HEADLINE: on roughly 3 drives in 4, the grind should read as "not real" by the scorer.**
✅ **It also confirms V195's re-fit on a sound statistic** — 73 % vs 64 % below null, 12.7× vs 10.3×
median reduction. The re-fit was worth doing, and now that is established without the
floor-attenuation error.
⊕ This replaces the withdrawn 21.5× / 7.7× / 52× figures. **It attenuates only the excess, never the
background, so it cannot repeat that error.**
⊕ Tool: `rlog-tools/score/notch_prediction_excess_only.py`.

### 🛑 THE PRE-REGISTRATION, IN THE FORM THE SCORER WILL PRINT
```
   grind excess falls from ~32x to ~2x, below the ~3.9x null   => THE GRIND IS GONE  (expected on
                                                                  ~73 % of drives)
   falls to 4-10x                                              => working but incomplete; this is
                                                                  the p75-p90 tail
   stays above ~15x                                            => the notch is NOT reaching the
                                                                  signal.  Check the biquad arm
                                                                  (0xC649B) and the engagement gate
                                                                  before touching the design.
   grind peak MOVES to ~24-28 Hz                               => displaced, not removed; re-centre
```

## 🛑🛑 **RETRACTION: THE PER-ROUTE SEVERITY NUMBERS WERE BROADBAND-CONTAMINATED**
I built two ticks of analysis on the **engaged/manual power ratio per route**. A control killed it:
```
   corr(log ratchet, log grind)                     +0.748
     partial, controlling 0.5-3 Hz activity         +0.793   survives
     partial, controlling the 30-45 Hz CONTROL band -0.177   ** COLLAPSES **

   corr(log ratchet, log ctrl) = +0.914      corr(log grind, log ctrl) = +0.859
```
🛑 **Both symptom bands correlate ~0.9 with a band containing NEITHER symptom** ⇒ the
engaged/manual ratio is elevated **BROADBAND** on some routes — it measures how the exposure differed
between LKAS-on and LKAS-off, not band-specific severity.

❌ **WITHDRAWN:**
- the per-route engaged/manual severity distributions (grind "87.8× worst quartile", ratchet "466×")
- **"the notch gives ~52× on bad drives"** — built on that ratio
- the closed-loop loop-gain estimate **L ≈ 0.78–0.81 and the 7.7×**, which inferred `L` from the same
  contaminated ratio

➕ **THE ROOT CAUSE OF THE ERROR:** the kit's scorers use a **slope-corrected excess** — a band
against its own local background, on the **same** windows — precisely because it is band-specific by
construction. **I drifted onto an engaged/manual ratio and inherited an exposure confound.** Use the
excess; it is what the scorers use for this reason.

## ✅ **REDONE PROPERLY — and it REFUTES the common-cause hypothesis**
Per-route slope-corrected excess, **engaged windows only**, 67 routes, null ~3.9×:
```
   band                          p10   p25   p50    p75    p90    max
   RATCHET  cs_tq   5-12 Hz     13.7  24.7  60.7  186.9  242.5  381.8
   GRIND    cs_rate 15-25 Hz    11.8  22.5  31.6   64.8  136.4  413.7
   99 % of routes are ABOVE the null for BOTH symptoms
```
✅ **`corr(log ratchet excess, log grind excess) = +0.304` — weakly related.** The +0.748 **was** the
broadband confound. ⇒ **the two symptoms are largely independent, and SEPARATE LEVERS remain the
right design** — which is what V196 already does (notch for the grind, inertia half-dose for the
ratchet). The common-cause idea is refuted, not adopted.

✅ **WHAT THE SCORER SHOULD PRINT ON A TYPICAL DRIVE** — useful for pre-registration, because a
single drive is one route, not the pooled corpus:
```
   a typical route:  ratchet excess ~61x   grind excess ~32x
   a bad route:      ratchet ~187x         grind ~65x
   a mild route:     ratchet ~25x          grind ~23x
```
⚠ These are **larger** than the pooled figures quoted earlier (13.5× / 7.3×) because pooling a
median spectrum across routes attenuates each route's own peak. **Both are correct for what they
measure; the PER-ROUTE number is what a single drive will show.**

🛑 **WHAT REMAINS UNQUANTIFIED: how much the notch will actually deliver.** The open-loop score
(21.5×) over-promises, and the closed-loop estimate that would have bounded it is withdrawn with the
ratio it rested on. **The honest position is that the notch's on-car effect is now UNPREDICTED — the
drive measures it.** What survives is the ranking (V195's fit beats V188's) and the firmware facts
(DC gain unity, −0.77° at 3 Hz, notch depth at 19.75 Hz).

## ⭐⭐ **THE NOTCH DELIVERS MOST EXACTLY WHERE THE GRIND IS WORST — and this supersedes the 7.7×**
Last section's "honest 7.7×" was computed on the **POOLED** spectrum. Per route, the engaged/manual
grind ratio varies enormously, so pooling was misleading **in both directions**:
```
   engaged/manual GRIND power ratio, 15-25 Hz on cs_rate, per route (30 routes)
     p10   2.3x     p25  7.7x     p50  24.6x     p75  57.9x     p90 102.9x     max 397.1x  (r9e)
```
✅ **That reconciles the discrepancy.** The recorded *"9,200× less power with LKAS off"* and my
pooled *11.3×* are not in conflict — they are different points on a very wide distribution. **Neither
is "the" number.**

✅ **AND THE NOTCH'S BENEFIT TRACKS SEVERITY**, because loop gain is highest where the grind is worst:
```
   worst quartile (eng/man >= 57.9x)   median ratio 87.8x  ->  notch gives 51.9x
   best  quartile (eng/man <=  7.7x)   median ratio  2.7x  ->  notch gives  2.4x

   worst individual routes:  r9e 397.1x -> 224.3x  ·  r96 168.4x -> 102.4x  ·  r95 157.9x -> 89.5x
```
⇒ **THE OPERATOR-FACING STATEMENT: on the drives where grinding is worst, expect roughly 50× less
grind power; on drives where it is already mild, roughly 2×.** That is the right shape for a fix — it
does the most when it is needed most — and it is far more useful than any single averaged figure.

🛑 **THE NUMBER HAS NOW BEEN CORRECTED TWICE. The progression is the point:**
```
   21.5x   open-loop score            -- valid only for RANKING designs; attenuates the
                                         disturbance floor, which a notch cannot remove
    7.7x   closed-loop, POOLED        -- right method, wrong aggregation: pooling a median
                                         spectrum underweights the bad routes
   2.4x .. 51.9x   closed-loop, PER ROUTE   <- the honest answer, and it is a RANGE
```
**A single number was the wrong output all along.** Record the range, not a point estimate.

## 🛑⭐ **THE CLOSED-LOOP PREDICTION IS *WEAKER* THAN THE OPEN-LOOP ONE — MY NOTCH FIGURES WERE OVERSTATED**
Every notch estimate so far multiplied the measured spectrum by `|H|²`. That treats the filter as a
feedforward attenuator. The grind is a **closed-loop** effect, so the measured engaged/manual ratio
identifies the loop gain directly: `R = 1/|1−L|²`.
```
   cs_rate, 15-25 Hz, pooled creep windows
     engaged (measured)      3.2
     manual  (measured)      0.3      <- the floor a broken loop returns to
     OPEN-loop prediction    0.2      x16.9 reduction   <- what I have been quoting
     CLOSED-loop prediction  0.4      x 7.7 reduction   <- the honest number
     engaged/manual ratio   11.3x     <- the CEILING on any assist-path fix in this band
```
🛑 **The open-loop estimate attenuates the DISTURBANCE FLOOR as well** — but that floor is set by
road and plant, and **the notch sits in the ASSIST path, so it cannot remove it.** The loop can only
give back what it added.
⇒ **CORRECTION: the "21.5× / 15.0× / 14.3×" figures quoted for V188/V195/V196 are OPEN-LOOP and
OVERSTATE the achievable reduction.** The honest band-integrated prediction is **~7.7×, with 11.3× as
the hard ceiling.** The *ranking* of the designs is unaffected — they were all scored the same way —
so V195's re-fit is still better than V188's, but the absolute promise was too large.

⊕ **The notch DOES fully break the loop at its centre**: `g = 0.0025` at 19.73 Hz drives `R` from
27.8 to **1.00** — exactly the manual level. It is away from the centre that the ceiling bites
(`g` 0.26–0.60 at 22–25 Hz ⇒ `R` only 1.5–2.4).

⚠ **A DISCREPANCY TO FLAG, NOT RECONCILE:** this gives loop gain **L ≈ 0.78–0.81** at the peak — an
amplified resonance, **not** the near-unity instability implied by the recorded *"9,200× less power
with LKAS off"*. Different channel, band and conditions; **do not treat 9,200× and 11.3× as the same
measurement.** Which is right matters for how much the notch can deliver, and **only a drive settles
it.**

⊕ Simplification stated in the tool: `L` is taken real and positive near the resonance (worst case).
A power ratio does not identify phase, so this is the right order of magnitude, not an exact figure.
⊕ Tool: `rlog-tools/score/closed_loop_notch_prediction.py`.

## 🛑⭐ **THE 8× LKAS GAIN HAS BEEN TRIED AND ABANDONED THREE TIMES, NOT ONCE**
Backfilling the lineage from the images (V122–V196, 57 builds) immediately turned up history the
record does not carry:
```
   0xC6CD0   the LKAS gain      stock 0xFFFF (inert)
     V101   3564 -> 7128   4x -> 8x    ** and the grind came back **
     V102   7128 -> 5346   8x -> 6x
     V124   5346 -> 7128   6x -> 8x    <-- undocumented
     V137   7128 -> 5346   back to 6x  <-- undocumented
     V142   5346 -> 7128   6x -> 8x    <-- undocumented
     V147   7128 -> 5346   back to 6x  <-- undocumented
```
🛑 **8× was reached and backed away from THREE separate times.** My authority recommendation
(*"confirm the grind fix, then 6× → 8×"*) therefore enters **territory that has already failed
three times**, not unexplored ground. It is still the right *sequence* — the notch is what breaks
the gain/grind coupling, and that is genuinely new — but **the prior on 8× is much worse than the
V101 story alone suggests, and the operator should be told that before it is proposed again.**
⊕ Also surfaced: **`0xC40BC`** (the Coulomb ramp knee) was raised **3000 → 3600 at V151 and reverted
at V152** — another undocumented try-and-back-off.

## ✅ **THE LINEAGE GAP IS PARTIALLY CLOSED — `grep <address>` WORKS AGAIN FOR V122–V196**
`docs/BUILD-LINEAGE.md` carried a banner: *"THIS LINEAGE STOPS AT V121. V122–V178 HAVE NO ROWS —
INCLUDING THE FLYING BUILD."* That file is a **mandatory pre-read before proposing any calibration
edit**, and the standing rule *"grep the lineage before naming any address"* **silently passed** for
every cell those builds moved. That is how the 10× K1 dose and the 72 dead bytes stayed invisible.
✅ **`docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md`** — **generated, not narrated**: every row is
a byte diff between two images on disk. **43 cells across 57 builds, 7.4 KB.**
⚠ **Honest limits, stated in the file itself:** it carries **no reasoning**; **not every build
number has an image** (gaps 122→124, 125→127, 127→129, 129→131, 131→137, 142→147, 161→164,
165→167, 177→179, 181→183), so a change across a gap reads as *"at or before this build"*; and
anything load-bearing should still be diffed **against the stock image**, not against the file.

## ✅ **THE THIRD SYMPTOM RESOLVED: "PEAK COMMAND OSCILLATION" NEEDS NO SEPARATE LEVER**
🛑 **A lead/lag test is NOT usable here, and that was established BEFORE running it:** at 20 Hz one
period is 50 ms = **5 samples** at 100 Hz, so lag resolves only modulo half a period, while
openpilot's latency is 1–3 periods. Coherence is usable; lag is not.
```
   sc_tq x cs_rate       @ 1 Hz    @ 8 Hz    @ 20 Hz
   pooled                 0.115     0.119      0.180
   hands OFF (31 win)     0.338        -       0.181
   SHUFFLED floor         0.049     0.050      0.048
```
✅ **The low pooled 1 Hz figure was a MIXED-EXPOSURE ARTEFACT.** Hands-off it rises to **0.338, ~7×
the floor** — the command *does* move the wheel at 1 Hz. **This was flagged as a question, not
reported as an authority finding, and the stratification is why.**
✅ **20 Hz coupling is weak but real (0.181, 3.8× floor) and UNCHANGED by hands** ⇒ not driver-related.
➕ **The decisive fact is a prior, not this test: the LKAS lane is a ~1–5 Hz low-pass, so openpilot
CANNOT COMMAND a 20 Hz oscillation.** Whatever the 3.3× excess in `sc_tq` is, it is not commanded.
⇒ **the command's 20 Hz content is the command REACTING to the grind (or an artefact), not driving
it ⇒ no separate firmware lever is indicated for the third symptom, and the notch in V195/V196 is
already the intervention that addresses it.**
⚠ Only **31 hands-off and 1 hands-on** 20.5 s episodes exist in the whole corpus — consistent with
the earlier finding of zero continuous 15 s hands-on engaged-creep windows. **Hands-on remains the
corpus's blind spot.**
⊕ Tool: `rlog-tools/score/command_coupling_at_grind.py`.

### ⇒ ALL THREE STATED SYMPTOMS NOW HAVE AN ANSWER
```
   GRINDING            a real MOTION oscillation, strongest in cs_rate  -> the notch (V195: 21.5x)
   RATCHETING          torque-dominant, omega^2 lane                    -> inertia half-dose (V196)
                                                                           + the K1 revert
   COMMAND OSCILLATION cannot be commanded (1-5 Hz low-pass); it tracks -> fixed BY fixing the grind
                       the grind                                           no separate lever
   LKAS AUTHORITY      the knob is 0xC6CD0 and it is the grind's carrier -> sequenced: confirm the
                                                                           grind fix, THEN 6x -> 8x
```

## ✅ **V196 — THE ONE FREQUENCY-SELECTIVE RATCHET LEVER LEFT, AND IT COSTS NOTHING AT DC**
The biquad is spent on the grind. The only other **frequency-selective** lever aimed at the ratchet
is `gp-0x6b26`: built from the acceleration EMA, so its loop contribution scales as **ω²** —
**67× stronger at 8.2 Hz than at 1 Hz.**
```
   gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )
   L = LERP(0xCBE74[mode], gp-0x6a5e)

   FLYING V122   engaged Y = (-29490, -17202, -16000)   ~3x Honda   ** and it ratchets **
   V189..V195    engaged Y = ( -9830,  -5734,  -1966)   = Honda
   V196          engaged Y = ( -4915,  -2867,   -983)   = HALF Honda
```
✅ **ENGAGED ONLY.** m24 (manual) and m26 (engaged) are **distinct records** (`0xD6A64` vs
`0xD7A54`), so only `0xD7A5C..0xD7A61` moves and **manual driving stays byte-identical** — the V74
pattern the TVCA4 memory endorses.
⚠ **This deliberately RE-CREATES an engaged/manual asymmetry** that earlier work removed. The
difference is **direction**: the ones removed made engaged **worse** (more anti-damping when
engaged); this makes engaged **better**. Recorded explicitly so a later reader does not "fix" it.
✅ **THE TRADE, PLAINLY:** negative apparent inertia makes the wheel feel lighter to fast inputs, so
halving it means the wheel feels closer to its true inertia at high frequency — very fast steering
inputs get marginally less help. **But ZERO at DC** (acceleration is zero in steady state), so **no
LKAS authority is lost and no steady steering weight is added.** A half-dose rather than zero
precisely because the trade is real.
✅ **V196 = V195 + three int16.** `f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e`
⚠ Sign basis: the ★★★★★ anti-damping reading plus the dose ladder. **If inverted, the term was
damping and the ratchet gets worse — revert to V195, three int16.**

⇒ **THE SHELF NOW SEPARATES CLEANLY BY SYMPTOM:**
```
   V195   the GRIND lever, re-fitted on the channel the grind lives in.  No sign bets.
   V196   V195 + the RATCHET lever, omega^2-selective, engaged-only, free at DC.  One sign bet.
   V194   V193 + the gp-0x6c2c probe, if the detector question is worth a drive.
```

## ✅ **V195's LOW SHOULDER IS CLEAR — AND THE WIDER NOTCH IS GENTLER THAN V189's**
A notch adds lag below itself, so a wider pole (0.9000 vs V188/V189's 0.9300) needed its own check;
the V188 result does not transfer. Measured on **`cs_rate`**, pooled engaged-creep windows:
```
   f (Hz)   excess   V189 |H|  V189 lag   V195 |H|  V195 lag
   15.04     1.66      0.486    -29.9      0.449    -27.7
   16.21     2.35      0.372    -34.0      0.349    -30.5
   16.99     2.95      0.288    -36.9      0.278    -32.4
   17.97     3.80      0.176    -40.5      0.184    -34.8
   18.95     7.90      0.057    -44.3      0.085    -37.1
```
✅ **Frequencies with excess>2 AND |H|>0.5 AND lag<−30°: ZERO.** The danger pattern needs all three
at once, and for a notch lag and attenuation grow together — the worst three points (16.2–17.6 Hz)
have |H| already cut to 0.22–0.35 exactly where the lag peaks.
➕ **AND V195's LAG IS SMALLER THAN V189's AT EVERY SHOULDER FREQUENCY** (−37.1° vs −44.3° at
18.95 Hz). The lower-Q notch has a gentler phase transition. ⇒ **V195 dominates V189 on BOTH axes:
1.43× more grind power removed AND less shoulder lag.** That is unusual and worth stating — the
re-fit was not a trade.
⊕ Tool kept: `rlog-tools/score/notch_shoulder_check.py`.

## ✅✅ **V195 — THE NOTCH RE-FITTED ON THE CHANNEL WHERE THE GRIND ACTUALLY LIVES**
V188 centred the notch at 19.40 Hz by minimax over **`cs_tq`, the driver torque sensor**. The
cross-channel work then showed the grind is a **motion** oscillation, strongest in **`cs_rate`**
(excess 7.3× vs 5.1× in torque). **The fit had been done on the weaker instrument.** Re-fitting on
`cs_rate`, same minimax criterion, same GATE 2 constraints, 67 routes:
```
   per-route GRIND peak 15-25 Hz    cs_rate  p10 16.33  med 20.12  p90 22.15 Hz
                                    cs_tq    p10 15.74  med 19.92  p90 21.68 Hz

   design                       median remaining   p90 remaining   phase @3 Hz
   V188/V189  19.40 Hz r 0.9300   0.0666  15.0x    0.0962  10.4x     -3.8 deg
   V195       19.75 Hz r 0.9000   0.0466  21.5x    0.0698  14.3x     -4.6 deg
```
✅ **1.43× more grind power removed at the median, 1.38× at p90, for 0.8° more phase.**
⊕ The substantive change is **the pole radius, not the centre**: 0.9300 → 0.9000 makes the notch
**wider**, because the rate-channel peak distribution is wider than the torque-channel one. The
0.35 Hz centre shift is minor by comparison.
✅ **V195 = V189 + four float32 cells. 11 payload bytes, 30/30 assertions.**
`a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b`
```
   DC gain 1.000003   max|H| 1.7177   added lag vs V189: -0.27 deg @1 Hz, -0.77 deg @3 Hz
   notch at 19.76 Hz  |H| 0.00094     15 Hz 0.42 - 21 Hz 0.12 - 22.2 Hz 0.23 - 25 Hz 0.48
```
⊕ Still engagement-gated, so manual driving stays bit-for-bit stock — **including Honda's 55.226 Hz
null, which is given up only while LKAS is engaged.**

⇒ **V195 REPLACES V189 as the recommendation.** Same lever set, same risk profile, a better-aimed
notch — and the improvement came from measuring the symptom in the right channel rather than from any
new firmware insight.

## 🛑 **THREE CLAIMS TESTED, TWO DIED TO THEIR OWN CONTROLS — and one of them was mine from last tick**

### ❌ 1. THE COULOMB SIGN-FLIP HYPOTHESIS IS REFUTED
Coulomb friction opposes motion, so it must flip sign at rate zero-crossings. Testing that with a
**matched** control (samples DWELLING at similarly low |rate| without changing sign):
```
   RATCHET  5-12 Hz   cross/dwell  3.73  [2.97, 4.35]
   GRIND   15-25 Hz   cross/dwell  4.96  [3.84, 5.92]   <- the CONTROL is HIGHER
```
⇒ crossings excite **everything** broadly; there is no Coulomb-specific preference.
**The friction explanation for the ratchet is NOT supported.** (The K1 revert is still defensible —
it returns a 10× dose to Honda — but not on this rationale.)

### ❌ 2. AND THE RATE-SCALING TEST WAS CONFOUNDED
The ratchet/control ratio rises 63.7 → 211 peaking at 20–40 °/s — **but the GRIND control does the
same** (9.6 → 24.9), and the ratchet/grind ratio stays flat at 6.2–8.5 throughout. The common
rise-and-fall is the **normalisation**, not a rate signature. Inconclusive, not supportive.

### 🛑 3. **I OVER-CLAIMED LAST TICK: "THE RATCHET IS NOT IN THE MOTION" IS TOO STRONG**
The first coherence attempt returned **1.000 for everything including the shuffled surrogate** —
degenerate, because one sub-window per segment makes coherence trivially 1. **The shuffled floor
caught it.** Redone with 2048-sample episodes and 256-sample sub-windows:
```
   coherence cs_tq x cs_rate    @ 8 Hz  0.888      @ 20 Hz  0.842
   SHUFFLED floor                       0.049               0.053
```
⇒ **torque and motion are STRONGLY COUPLED at 8 Hz.** The ratchet's motion is **small, not absent** —
the rack is stiff at 8 Hz, so a large torque ripple produces little movement. That is consistent with
the recorded *"lightly-damped resonance, Q 14–29, motor/rack-side"*, and it is **not** a
torque-sensor-only artifact.
⇒ **CONSEQUENCE: `gp-0x6c2c` DOES contain 8 Hz, so the detector's amplitude gate is NOT provably
uncrossable.** V193's premise is **not** dead, and **V194's probe is still the honest decider**, not a
formality. The "peaks below 12800" branch is a real possibility again, not the expected outcome.
⊕ What survives from last tick unchanged: **the GRIND is a genuine motion oscillation, strongest in
RATE (7.3×)** — so the notch remains well aimed.
⊕ An independent rate (`d(cs_ang)/dt` computed here) gives ratchet 1.5× / grind 2.6× — it corroborates
the small ratchet but **degrades the grind too**, because differentiating a quantised angle amplifies
HF noise. `cs_rate` is the better motion instrument.

➕ **THE PROCESS POINT: three claims, and the CONTROL killed or corrected two of them before any of it
reached a build.** A refuted hypothesis with a control that fired is worth more than a confirmed one
without. 🛑 *Run the control BEFORE the measurement* — the shuffled floor at 1.000 is exactly what a
broken estimator looks like when nobody checks.

### ✅ WHERE THIS LEAVES THE RECOMMENDATION
**V189 still stands** — the notch is aimed at a confirmed motion oscillation, and the reverts return
10× and 3× doses to Honda on their own merits. But **the detector route (V191–V194) is back to
UNDECIDED rather than ruled out**, and V194 is the build that settles it.

## 🛑🛑⭐ **THE RATCHET IS NOT IN THE MOTION — IT IS A TORQUE-PATH EFFECT, AND THAT RE-AIMS EVERYTHING**
Every prediction this session rested on **`cs_tq`, the driver torque sensor**. Running the same
slope-corrected excess across **all** channels, 1080 pooled engaged-creep windows, null ~3.9×:
```
   channel                       RATCHET 5-12          GRIND 15-25
   cs_tq   driver torque         13.5x @  8.01 Hz       5.1x @ 20.12 Hz
   cs_rate steering RATE          1.7x @  8.01 Hz  ***  7.3x @ 20.31 Hz
   sc_tq   LKAS command           1.2x                  3.3x
   probe   cave channel           2.2x                  1.9x
   cs_press hands-on              1.2x                  1.8x
```
✅ **THE GRIND IS A GENUINE MOTION OSCILLATION** — **strongest in RATE (7.3×)**, present in torque and
command. That confirms the closed-loop model and means **the notch is well aimed.**
🛑 **THE RATCHET IS NOT IN THE MOTION AT ALL** — 13.5× in torque, **1.7× in rate, BELOW the null.**
The wheel is not oscillating at 8 Hz; the **torque** is. That is a **friction / stiction** signature,
and it matches the operator's word for it: he feels it, he does not see the wheel move.

### 🛑 CONSEQUENCE 1 — THE DETECTOR ROUTE CANNOT REACH THE RATCHET, FOR A SECOND REASON
`FUN_000428d4` watches **`gp-0x6c2c`, an ACCELERATION EMA**. No 8 Hz in the rate ⇒ none in its
derivative ⇒ **the amplitude gate `|gp-0x6c2c| > 12800` will not be crossed either.** So V191, V192
**and V193** are inert for the ratchet on **both** counts — frequency (established last tick) **and now
amplitude.** V194's probe will confirm it; the pre-registered "peaks below 12800" branch is now the
*expected* outcome, not merely a possibility.

### ✅ CONSEQUENCE 2 — THE RATCHET'S PRIME SUSPECT IS THE FLYING BUILD'S 10× COULOMB FRICTION
```
   friction = clamp(motor_rate * 12 / cal[0xC40BC], +-1) * (|model| * K1/1024 + K0/1024)

   cal        STOCK  V88  V89  V108  V122(FLYING)  V177..V194
   0xC40D2 K1   102  102  204   204     ** 1020 **     102      <- TEN TIMES Honda
   0xC40BC knee 600  600  600   600        3000        3000
```
⇒ **the car is running 10× Honda's modelled Coulomb friction**, and Coulomb friction is exactly what
makes torque ripple without motion. **V177's K1 revert — already carried on V189 through V194 — is
aimed straight at the lane the measurement points to.**
⚠ The ramp knee is **3000 vs Honda's 600** and has never been reverted (it was 600 as late as V108).
A 5× knee makes the ramp shallower, i.e. *less* friction below saturation — aligned with the
operator's "low apparent friction" requirement, so it is left alone, **but it is non-stock and
unattributed to any stated intent.**

### ⭐ **THIS RE-ORDERS THE RECOMMENDATION — V189 IS NOW THE BEST BUILD**
```
   V189   the grind NOTCH (aimed at a confirmed MOTION oscillation)
          + the inertia revert and the K1 revert (aimed at the TORQUE path, where the ratchet is)
          no sign bets - nothing that can change normal driving - both symptoms addressed
   V190   adds a sign-bet lever on the MOTION path, where the ratchet is NOT
   V191-3 add detector levers now shown unreachable on BOTH frequency and amplitude,
          and V193 can change normal driving for no expected benefit
   V194   = V193 + the probe that confirms the above
```
⇒ **RECOMMEND V189.** Everything after it is aimed at the motion path; the measurement says the
ratchet is not there. **V194 remains worth flying only if the operator wants the `gp-0x6c2c`
measurement itself** — which is now a confirmation, not a fork.

## ✅✅ **THE V194 DELTA IS NOW 100 % ATTRIBUTED — and V57 turns out to be the authority build**
Every payload byte of V194 vs stock is explained. The two stragglers were the **part-number marker**
(`39990-TVA-A160` → `39990-TVA,A160`, two copies) — a UDS-visible flag that the ECU is modified.

**What was NOT in the record: V57 is a large LKAS-AUTHORITY build.** Beyond the `0xC646C`
decoupling it is credited with, it also carries:
```
   0xC62EA          320 -> 0        ** the LOW-SPEED STEER LOCKOUT, DISABLED **
   0xC659A..0xC65CE float32 +-1.0 -> +-5.0   a family of saturation limits raised FIVE-FOLD
   0xC674E..0xC676C int     +-1024 -> +-5120  the same family, integer form
   0xC61C0/C2/C4    1600 / 896 / 1280 -> -1   saturated, i.e. removed as constraints
   0xC64B4/B6/B8    24688 / 16438 / 112 -> -1 / 255   saturated
```
⇒ **substantial authority work is ALREADY ON THE CAR and has been since V57**, and the lineage
describes that build only as *"the `0xC646C` decoupling"*. Worth knowing before adding more.

### ✅ THE HEADLINE FOR THE OPERATOR
```
   V122 (what he drives) vs stock   310 payload bytes
   V194                  vs stock   319 payload bytes
   ** V194 changes NINE cells relative to the car as it is today **
     4  the grind notch          0xC60A8 / AC / B0 / B4        V188
     3  detector-conditional     0xC64AE - 0xC691A - 0xC64DD   V190/V192/V193
     2  pure instrument          0x55DF2 - 0x55E10             V194
```
Everything else on V194 is already flying. **The proposal is nine bytes of change, of which two are
telemetry and three do nothing unless Honda's own oscillation detector fires.**
✅ Tool: `analysis-2020accord/verify/cumulative_delta_vs_stock.py` — now attributes 100 % and still
refuses to stay silent about anything new.

## 🛑✅ **THE CUMULATIVE DELTA — AND IT FOUND 72 DEAD BYTES ON THE BUILD HE IS DRIVING**
The close-out contract requires enumerating **every** cell that differs from stock, read from the
**built image**. Doing it for V194 turned up a block nothing in the record explains:
```
   0xE4194..0xE41A4 - 0xE41BC..0xE41CC - 0xE420C..0xE421C - 0xE4234..0xE4244
   0xE5194..0xE51A4 - 0xE51BC..0xE51CC - 0xE51E4..0xE51F4 - 0xE520C..0xE521C
   8 runs x 9 entries = 72 halfwords, EVERY ONE 15360 -> 16384  (+6.67 %)
   context:  X = [3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320]   Y = [15360 x8] -> [16384 x8]
   present on V108, V122, V158, V189, V194  => introduced at V108
```
🛑 **AND THEY ARE DEAD.** `0xC61BE` — the clamp on that path — is **byte-stock at 15360 on V194**,
so every raised entry is cut straight back. The lineage records why: V108 built the
`0xC61BE` → 16384 raise **and then PULLED it** on a pre-registered null.
⇒ **V108 raised the TABLES and pulled the CLAMP. 72 bytes of half-applied edit have been carried on
every build since — including the one on the car right now — doing nothing.**
⊕ That is exactly the category the contract calls *"carried by accident"*, and it had never been
found because nobody had run a full cumulative diff against stock.

### ✅ THE 9 CELLS V194 CHANGES RELATIVE TO WHAT HE DRIVES TODAY
```
   0xC60A8/AC/B0/B4   the GRIND NOTCH, 55.226 Hz -> 19.40 Hz              V188
   0xC64AE            2nd omega^2 accel term disabled                      V190
   0xC691A            oscillating slew curve tightened by Honda's 0.60     V192
   0xC64DD            detector dwell 50 -> 100 (the ratchet becomes visible) V193
   0x55DF2 / 0x55E10  the 427 probe -> gp-0x6c2c at sar 6                 V194
```
Everything else on V194 is already on the flying build. **V122 vs stock = 310 payload bytes;
V194 vs stock = 319.** So the whole proposal is **9 bytes of change from what he drives**, of which
**4 are the notch, 3 are detector-conditional, and 2 are pure instrument.**

✅ Tool kept: **`analysis-2020accord/verify/cumulative_delta_vs_stock.py`** — prints the full
attributed delta and **refuses to stay silent about anything it cannot attribute**, which is how the
72 bytes surfaced.

## ✅ **V190's XREF CHAIN BYTE-CONFIRMS — the BELIEF caveat is LIFTED**
Last section flagged that V190's xref counts came from `search_instructions` and were not
byte-confirmed. Re-derived from raw bytes, both gp-relative encodings, whole image:
```
   cell                          ghidra   raw-real   verdict
   gp-0x6bc2   V190 chain           2         2      COMPLETE
   gp-0x6ad6   V190 chain           3         3      COMPLETE  (2 raw hits adjudicated away)
   gp-0x6c2e   the 2nd accel EMA    5         5      COMPLETE
   gp-0x6b26   CONTROL              5         5      the scanner is CALIBRATED
   gp-0x6b2e   the caught case      2         3      ghidra undercounted by 1 (0x2A896)
```
⇒ **V190's completeness moves from BELIEF to EVIDENCE.** Only `gp-0x6b2e` was genuinely
undercounted, and that one is already recorded.

### 🛑 **MY OWN SCANNER OVER-REPORTS — THE MIRROR IMAGE OF GHIDRA'S UNDERCOUNT**
The two extra `gp-0x6ad6` hits were **false positives I manufactured**:
```
   0xBCC52  disassembles as  `st.b r7, -0x6ad5, gp`     <- -0x6ad5, NOT -0x6ad6
```
My scan accepted **both** `(hw2 & 0xFFFE)` and `(hw2 & 0xFFFE) | 1` for every opcode, so it matched
the NEIGHBOURING cell. And the surrounding stream is six consecutive `st.b r7` to scattered
unrelated displacements (`0x446c`, `0x6cdb`, `-0x42a4`, `-0x1a90`, `0xd65`) — **that is DATA being
force-disassembled, not code.**
➕ **THE RULE, and it cuts both ways:** *Ghidra UNDERCOUNTS (it only sees analysed code and still
reports `truncated:false`); a naive byte scan OVERCOUNTS (it cannot tell code from data, and a
loose displacement rule matches neighbours).* **Neither is authoritative alone. Adjudicate every
disagreement by disassembling the disputed address and checking it sits in a sensible instruction
stream** — which is exactly how `0x2A896` was confirmed real and `0xBCC52` was rejected.
✅ **Scanner refinement owed:** derive the odd/even displacement bit from the OPCODE FIELD
(`0x3D` ⇒ odd, `0x3C` ⇒ even, as established for `ld.bu`) instead of accepting both. Accepting
both is what produced the neighbour match.

⊕ **Ghidra reports `analyzed: true` with 2086 functions, yet `0x2A896` has no function.**
"Analysed" does not mean complete coverage on this image — so the `CLAUDE.md` instruction to analyse
the whole `.bin` first is **already satisfied as far as the tool is concerned**, and the residual
gaps are not fixable by re-running analysis. **The byte scan plus adjudication is the only complete
method.**

## 🛑 **LKAS AUTHORITY: `0xC61BE` IS MISLABELLED, AND THE REAL KNOB IS COUPLED TO THE GRIND**
`0xC61BE` is described in the lineage as *"the LKAS request clip"*. **It is not.** Decompiled:
```c
   FUN_0002a93a  (driver torque gp-0x682f -> a pointer-table assist map)
       uVar11 = clamp(uVar11, +-cal(0xC61BE));      // 15360
       gp-0x6b2e = uVar11;                          // the BASE-ASSIST output
   ... consumed at 0x2A896:  r9 = (gp-0x6b2e * cal(0xC63EE)) >> 10
```
⇒ **it clamps the BASE-ASSIST path (driver torque → assist), not the LKAS request.** Raising it adds
**manual** assist, not LKAS authority. **The label is wrong and the lever is aimed at the wrong lane.**

### 🛑🛑 **AND I NEARLY RECORDED A FALSE NULL — THE TWO-METHOD RULE CAUGHT IT**
`search_instructions` returned **2 hits for `gp-0x6b2e`, both stores**, which reads as *"a dead cell,
so `0xC61BE` is provably inert"*. That is a clean, quotable, **wrong** conclusion. The raw byte scan
found a **third** site:
```
   0x2A896   hw1 = 0x4F24  ->  opcode bits5-10 = 0x39 = ld.h, reg r9
             = `ld.h -0x6b2e, gp, r9`   ** A READER **
```
It sits in a region Ghidra has **not analysed**, which is exactly the recorded failure mode:
*"`search_instructions` silently undercounts — it scans only already-analysed instructions and still
reports `truncated:false`."*
⚠ **CONSEQUENCE FOR THIS SESSION'S OTHER SEARCHES.** The xref counts behind **V190** — `gp-0x6bc2`
(1 writer / 1 reader) and `gp-0x6ad6` (1 writer / 2 readers) — came from the same tool and were
**not** byte-confirmed. They may undercount. The chains I built on them are still the best available
reading, but **their completeness is BELIEF, not EVIDENCE.** (By contrast `gp-0x671a`, the setf
family and the dormant-cal sweep were all byte-scanned and stand.)
➕ **`CLAUDE.md` already says to analyse the whole image in Ghidra first. The image is NOT fully
analysed, and that is a live hazard for every operand search in this session.**

### ✅ **THE HONEST ANSWER ON AUTHORITY — IT IS SEQUENCED, NOT BLOCKED**
```
   the real LKAS authority knob is 0xC6CD0, the LKAS gain:  reach = (clip * cal(0xC6CD0)) >> 15
     V57..V88   3564  = 4x     <- the value at which grinding was CONFIRMED FIXED on-car (V88)
     V101       7128  = 8x     <- and the grind came back
     V102..now  5346  = 6x     <- where it sits today
   the SAME cell is what the de-confounded 2x2 named as the CARRIER of the ~23 Hz vibration
   (effect 2.7-3.9x).  Authority and grind are the SAME LEVER pushed in opposite directions.
```
⇒ **that coupling is exactly what the notch breaks.** V188's notch removes the gain's 19.4 Hz
consequence **without touching the gain**, so:
```
   step 1  fly the notch, confirm the grind is gone            <- V194 does this
   step 2  THEN 0xC6CD0 6x -> 8x becomes available, restoring the authority V102 gave up,
           with the notch now suppressing the vibration that made 8x untenable
```
🛑 **Do NOT raise the gain before the grind result is in** — that is the V101 mistake, and it is
the one build in the arc that demonstrably brought the grind back.

## ✅ **V194 — MEASURE THE ONE NUMBER THAT DECIDES WHETHER V191/V192/V193 CAN WORK AT ALL**
V193 opened the detector's **frequency** window. There is a **second** gate, and it has never been
measured: the counter increments only when **`|gp-0x6c2c|` exceeds T = `cal(0xC620A)` = 12800.**
⇒ if the ratchet's acceleration never reaches T, then **V191, V192 AND V193 are all inert** and the
next lever is **T**, for an amplitude reason rather than the frequency one. That fork is worth one
CAN channel.
✅ **V194 repoints the 427 probe from `gp-0x6ac0` (V183) onto `gp-0x6c2c`, the detector's own input.**
```
   0x55DF2  hw2 of `ld.h disp, gp, r6`   0x9540 (-0x6AC0)  ->  0x93D4 (-0x6C2C)
   0x55E10  the pack shift               sar 4 (0xA4)      ->  sar 6 (0xA6)
```
🛑 **THE SHIFT IS NOT COSMETIC — `gp-0x6ac0` WAS UNSIGNED, `gp-0x6c2c` IS SIGNED.** The packer does
`andi 0xffff` (zero-extend) then `sar N` then masks to 10 bits, so for a signed source the shift must
be chosen to make the field carry the sign:
```
   sar 6:   positive x -> raw    0 .. 511        negative x -> raw 512 .. 1023
   decode:  x = (raw < 512 ? raw : raw - 1024) * 64
   resolution 64 counts   range +-32704   ** T = 12800 lands at raw 200 **
```
A smaller shift wraps negatives into the positive range and makes the channel unreadable. **That is
the trap this build exists to avoid, and it is why the shift moves WITH the source.** Verified by a
round-trip assertion over ±1000 / ±12800 / ±32704 in the builder.
✅ **40/40 assertions.** `2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10`
⊕ Decoder shipped: **`rlog-tools/probe/decode_v194_detector_input.py <route-tag>`**, which prints the
percentiles and the verdict directly.
⊕ Every V193 lever is carried — **this build adds an instrument, it does not remove a fix.**

### ⇒ WHAT ONE SHORT DRIVE NOW SETTLES
```
   |x| peaks well past 12800   => amplitude is fine; the detector route is LIVE and V193's window
                                  fix is the operative change
   peaks below 12800           => T IS THE BLOCKER. V191/V192/V193 are ALL inert, and the next
                                  build lowers T (0xC620A) instead
   peaks near 12800            => marginal; T needs a modest reduction
```
➕ This is the design law working as intended: **the probe was sized against its OWN lane's
reachable output** (±32704 at 64-count resolution, threshold mid-scale at raw 200), not against a
downstream clamp — and it pairs a magnitude channel with a sign, which is the pattern every probe
that ever DECIDED something has used.

## 🛑🛑⭐ **HONDA'S OSCILLATION DETECTOR HAS A FREQUENCY WINDOW, AND THE RATCHET FALLS OUTSIDE IT**
`FUN_000428d4` is a reversal counter on **`gp-0x6c2c` (the acceleration EMA)**:
```c
   T    = cal(0xC620A) = 12800        amplitude threshold
   HYST = cal(0xC64DD) = 50           DWELL LIMIT, in task ticks
   state +latched:  if (dwell >= HYST) -> neutral          // TIMES OUT
                    else if (x < -T)   -> -latched, count++
                    else dwell++
```
A reversal only COUNTS if the opposite peak arrives **within HYST ticks**. `FUN_000428d4`,
`FUN_00041464` and `FUN_000352b4` **all share the single caller `FUN_0002214a`** ⇒ same task, the
**1 kHz** control task (corroborated: the biquad response was verified at fs = 1000 Hz against three
stock points). So HYST = 50 ticks = **50 ms**:
```
   countable  <=>  half-period < 50 ms  <=>  f > 10.0 Hz
     ratchet  7.34 - 8.59 Hz    half-period 58 - 68 ms   ** OUTSIDE the window **
     grind   15   - 25   Hz     half-period 20 - 33 ms      inside
```
🛑 **THE DETECTOR CANNOT COUNT AN 8 Hz OSCILLATION.** The dwell expires before the opposite peak
arrives, so `gp-0x671a` never leaves 0 for the ratchet ⇒ **V191 and V192, which both act only on the
counter≥5 branch, are INERT FOR THE RATCHET.** They may still act on the **grind**, which is inside
the window, if its amplitude reaches T. **This is the "nothing changes" outcome, now predictable
BEFORE the drive rather than after it.**

➕ **AND IT CORRECTS A RECORDED ASSUMPTION.** The lineage treats **T** as the detector knob
(*"lowering T changes five things at once"*). **T is the WRONG knob for the ratchet: no amount of
lowering an AMPLITUDE threshold makes an 8 Hz oscillation countable when the DWELL is what expires.**
**HYST is the binding constraint**, and it has never been touched.

### ✅ **V193 — OPEN THE WINDOW SO THE RATCHET IS VISIBLE**
```
   0xC64DD  50 -> 100      dwell 50 ms -> 100 ms
     HYST  50  =>  f > 10.0 Hz    ratchet EXCLUDED
     HYST 100  =>  f >  5.0 Hz    the whole 5-12 Hz band INSIDE, with margin
```
With the ratchet finally visible to the detector, **V191's and V192's damping responses — which are
gated on exactly that counter — can act on it.** One byte, 31/31 assertions.
`0f1a7bb6849f17824cbc9fa7e8a6aeeb40e8fe4bb548fc7310fa4e17052b7992`

⚠ **THE RISK IS DIFFERENT IN KIND FROM V191/V192 — SAY IT PLAINLY.** V191 and V192 are conditional
on a state that never occurs during the ratchet, so they **cannot** affect normal driving. **V193
makes that state REACHABLE**, so for the first time in this chain the detector-conditional damping
can engage while driving. A spurious detection tightens the slew limit for a hold period and could
read as brief heaviness. The counter still needs **|gp-0x6c2c| > 12800 on BOTH sides** — a large
acceleration excursion — so it is bounded, not free-running. But it is a real change to normal
driving, unlike everything else in the V189–V192 chain.

⇒ **TWO OPTIONS, and the choice is the operator's:**
```
   V192  the conservative build: five levers, ALL provably inert in normal driving.
         But per the finding above, its detector-gated pair cannot reach the ratchet.
   V193  V192 + one byte that makes the detector see the ratchet, unlocking that pair.
         The only build in the chain that can change how the car feels when nothing is wrong.
```

## ✅✅✅ **V192 — HONDA'S OSCILLATION RESPONSE DOES NOTHING AT LOW INDEX. V192 CLOSES THAT GAP.**
`FUN_00035b20` switches the slew limit `gp-0x69a0` between two curves on the reversal counter:
```
   NORMAL      (counter < 5)   X = [ 320, 1600, 3200,  4480]   Y = [358, 358, 461, 512]
   OSCILLATING (counter >= 5)  X = [ 640, 3200, 6400, 12800]   Y = [358, 307, 307, 307]
                                                                    ^^^ IDENTICAL
```
🛑 **At the LOW index the two curves are the SAME (358)** — so Honda's oscillation response gives
**no tightening at all** there — and the oscillating breakpoints are **stretched 2×**, pushing what
tightening exists even further out.
✅ **V192 applies Honda's OWN ratio once more.** Honda chose `512 → 307` = **0.600** as its response
to detected oscillation; V192 scales the whole oscillating curve by that same 0.600:
```
   Y = [358, 307, 307, 307]  ->  [215, 184, 184, 184]
```
so the limit is tightened across the entire index range, **including the low end where the detector
currently does nothing.**

### ⭐ **WHY THIS IS THE SAFEST LEVER IN THE SESSION**
```
   PROVABLY INERT IN NORMAL DRIVING   the curve is read ONLY on the counter>=5 branch; below
                                      saturation the NORMAL curve is used and is byte-untouched.
   THE DIRECTION IS HONDA'S, NOT MINE Honda tightens the slew limit on detection; V192 tightens it
                                      MORE.  ** This is not a polarity gamble like V190/V191 -- the
                                      sign is established by Honda's own two curves. **
   MECHANISM IS EXPLICIT              gp-0x69a0 rate-limits the boost-table walk in FUN_000352b4
                                      (delta = ((step * limit * 4) >> 12)), so lowering it slows how
                                      fast the assist may change DURING an oscillation.  That is
                                      what damping an oscillation means.
```
✅ **V192 = V191 + four halfwords at `0xC691A`.** 32/32 assertions.
`c36b6ca12e27633f6a52a9a0d8c32feab71e08606fb253d4ef96cf3a17d5cdc1`
⚠ **Watch for:** a slew limit too tight during an event could read as a brief **HESITATION** rather
than a ratchet. That is a *different* symptom, not a worse one, and it is pre-registered.

## 🛑 **CORRECTION TO V191's RATIONALE — THE "4.2× BOOST" DOES NOT HOLD AT CREEP**
I justified V191 by saying the oscillation fallback `0xC640A` = −8192 is **4.2× stronger** than the
LERP it replaces. **That compares against the LERP's HIGH-INDEX end, which is not the creep operating
point.**
```
   inertia LERP (mode 26)   X = [0, 1280, 5760]   Y = [-9830, -5734, -1966]   index gp-0x6a5e
   fallback when oscillating                        -8192
     index 0      LERP -9830  ->  fallback is 17% WEAKER
     index 1280   LERP -5734  ->  fallback is 43% stronger
     index 5760+  LERP -1966  ->  fallback is 4.2x stronger   <- the figure I quoted
```
✅ **But `gp-0x6a5e` is the SAME index FactorC uses, and the recorded evidence is that it sits below
FactorC's first breakpoint 2240 across 100% of the micro regime.** ⇒ **at creep the LERP returns its
STRONG end and −8192 sits INSIDE the range — it is not reliably a boost at all.**
⇒ **V191 is still a valid lever, but its honest description is *"when the detector saturates, remove
the anti-damping term"*, NOT *"undo a 4.2× boost."*** The builder assertion and the card now say so.

## ✅ **THE DETECTOR MAP IS COMPLETE — AND HONDA USES IT TO DAMP**
All three `gp-0x671a` consumers are now read:
```
   FUN_00036c12   counter >= 5  ->  L = cal(0xC640A) = -8192 instead of the LERP
                  the ONE place the assist gain itself changes.  V191 zeroes it.
   FUN_0003a382   two counter-indexed LERPs, X = [5,10,15] and [5,8,10], Y FLAT at 1024 / 5120.
                  ** The counter is CLAMPED AT 5 and the first breakpoint IS 5, so `5 < counter`
                  is never true => both return Y[0] permanently. INERT over the reachable range. **
                  (the recorded worry that T is "a shape parameter on a load-bearing lane" is only
                  true if T or CEIL are moved -- at stock CEIL=5 these tables are constants)
   FUN_00035b20   SWITCHES CURVES on the counter, for the slew limit gp-0x69a0:
                     normal  X = [320, 1600, 3200, 4480]   Y = [358, 358, 461, 512]
                     osc     X = [640, 3200, 6400, 12800]  Y = [358, 307, 307, 307]
                  ** the oscillating curve is SMALLER (307 vs up to 512) with breakpoints stretched
                  2x => Honda TIGHTENS the slew limit when it detects oscillation. It DAMPS. **
```
➕ **So Honda's detector is a damping mechanism**, and V191 is *consistent with that design intent*
rather than opposed to it — it takes the same "when oscillating, back off" idea further.

### ⭐ **THE NEXT LEVER, AND IT HAS V191's IDEAL SHAPE**
`0xC691A..0xC6920` is the **oscillating** slew curve, `Y = [358, 307, 307, 307]`. Lowering it tightens
the slew limit **further** during a detected oscillation — **and it is read ONLY on the counter≥5
branch, so it is provably inert in normal driving**, exactly like V191. It also pushes in the
direction Honda already chose, which makes it far safer than a sign bet.

## ✅✅✅ **V191 — THE FIRMWARE BOOSTS ITS ANTI-DAMPING *AFTER* ITS OWN DETECTOR SEES OSCILLATION**
`gp-0x671a` is Honda's **HARD-REVERSAL COUNTER** — a built-in oscillation detector, clamped at
CEIL = 5 (`0xC64FA`). `FUN_00036c12` branches on it:
```c
   if (gp-0x671a < 0xFF && gp-0x67f4 == 1) {
       if (gp-0x671a < cal(0xC64FD)=5)   L = LERP(0xCBE74[mode], gp-0x6a5e);   // normal
       else                              L = cal(0xC640A) = -8192;             // OSCILLATING
   } else                                L = cal(0xC640C) = -3277;
   gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )
```
```
   LERP Y (Honda, mode 26) = [-9830, -5734, -1966]     on X = [0, 1280, 5760]
   fallback when OSCILLATING = -8192   ** 4.2x STRONGER than the LERP's weak end **
```
⇒ **once sustained oscillation is DETECTED, the anti-damping acceleration gain can jump 4.2×
STRONGER.** That is positive feedback on the thing the detector just found, and it is a plausible
reason the ratchet **sustains instead of decaying** — which is exactly the character the ring-down
work established (ζ 0.017–0.036, Q 14–29).

### ✅ WHY THIS LEVER IS BETTER-SHAPED THAN ANYTHING ELSE IN THE ARC
```
   PROVABLY INERT OUTSIDE THE SYMPTOM   0xC640A is read ONLY on the counter>=5 branch, so below
                                        saturation the cell is never loaded.  No steering-feel and
                                        no LKAS-authority change on a calm road -- BY CONSTRUCTION,
                                        not by measurement.
   ACTS EXACTLY DURING THE SYMPTOM      the one moment we want the term gone.
   ONE HALFWORD, cal-only, no cave.     never touched in the whole post-V38 arc.
```
✅ **V191 = V190 + `0xC640A` −8192 → 0.** 30/30 assertions.
`82ce1db4e73099377c61a78c1b5033b5ca3ba3368062761e8836c709b0c29f4b`
⊕ It also **does not depend on `gp-0x6a5e`'s value during the ratchet** — zeroing removes the term
outright, so the edit is unambiguous whether or not −8192 was a "boost" at the live operating point.

### ✅ AND IT SETTLED A REAL WORRY ABOUT V189
The same branch decides whether the **inertia LERP is used at all.** Had `gp-0x671a` normally sat at
or above 5, the LERP would be bypassed and **V184/V189's inertia revert would have been INERT** — the
same failure class as mode 27. ✅ **It is not: the counter is a reversal count clamped at 5, so
normal driving sits BELOW the threshold and the LERP path IS live.** The revert is real.

⚠ **Sign basis is shared with V190** — `gp-0x6b26` anti-damping per the ★★★★★ result plus the
3×-dose / 3.58×-ratchet observation. **If inverted, this term was DAMPING and zeroing it during an
oscillation makes the ratchet worse.** Same pre-registered revert.

## ✅ **V190 UN-RETRACTED — THE DECIDING TEST IS THE SIGN *RELATIVE TO* `gp-0x6b26`, AND IT MATCHES**
The retraction one section below was **wrong, and here is the specific error**: I judged
`gp-0x6bc2` in isolation, asking *"does opposing acceleration mean damping?"* — a question that
rests on the aggregator→plant sign, **which is exactly the link I had already flagged as unproven.**
The answerable question is the **RELATIVE** one.
```
   the gp-0x6bc2 path, both inversions now PROVEN:
     d(gp-0x6ad4)/d(gp-0x6ad6) = (-K) * (-1) = +K      the two inversions CANCEL
     gp-0x6ad6 ~ -a                              =>    gp-0x6ad4 ~ -a
   the inertia term, added DIRECTLY with no inversions:
     gp-0x6b26 = -K*alpha                        =>    gp-0x6b26 ~ -a
```
⇒ **BOTH terms enter the aggregator with the SAME SIGN, so they are the same class.** Whatever
`gp-0x6b26` is, `gp-0x6bc2` is.
✅ The kit's ★★★★★ finding [[accord-gp6b26-is-inertia-not-damping]] says `gp-0x6b26` is an
**inertia term giving NEGATIVE apparent inertia — anti-damping**. **Empirical support:** the flying
build carries **3×** Honda's dose of it (`m26 Y = −29490/−17202/−16000` vs `−9830/−5734/−1966`) **and
ratchets 3.58× more when engaged.** If these terms were damping, tripling one should have *reduced*
the ratchet.
⇒ **`gp-0x6bc2` is anti-damping too, and disabling it (V190) is directionally correct.**

🛑 **What was actually learned, and it is not nothing:** `FUN_0003a382` was decompiled and
**`error = measured − reference` is now PROVEN**, as is `gp-0x6ad4 = −K·error`. Those two links were
BELIEF before this tick. The mistake was framing an absolute question the data cannot answer
(*"is this damping?"*) instead of the relative one it can (*"is this the same sign as the term we
already characterised?"*).
➕ **GENERAL RULE: when an absolute sign depends on an unproven link, do not guess it — ask whether
the new term matches a term already characterised through the SAME unproven link. The unknown link
cancels.**

✅ **V190 restored as the recommendation.** Its sign now rests on **consistency with the ★★★★★
`gp-0x6b26` result plus the 3×-dose/3.58×-ratchet observation**, not on an independent proof — so
the pre-registered "ratchet gets worse ⇒ revert to V189" outcome **stays on the card.**

## 🛑❌ **V190 IS RETRACTED AS A RECOMMENDATION — I VERIFIED THE SIGN AND IT WENT THE OTHER WAY**
V190 disabled the `gp-0x6bc2` acceleration term on the BELIEF that it was destabilising. I said the
sign rested on a five-link chain and pre-registered the failure mode. **Decompiling the consumer
settled it, and the belief was wrong.**

**`FUN_0003a382`, the only reader of `gp-0x6ad6`:**
```c
   uVar24 = clamp(gp-0x6ad6, +-cal(0xC6200))
   iVar30 = gp-0x4f60 - uVar24              // error = MEASURED - REFERENCE   <- record CONFIRMED
   ... PID(error) ...
   iVar30 = (PID * gain >> 10) * gp-0x6752  // gp-0x6752 = -1
   gp-0x6ad4 = clamp(iVar30, ...)           // => gp-0x6ad4 is proportional to -error
```
and `gp-0x6ad4` is an additive term in the `FUN_0003aa2c` aggregator (already decompiled).

**The chain, now with five links PROVEN instead of assumed:**
```
   gp-0x6bc2  ~ -a                (gp-0x6752 = -1)                          PROVEN
   gp-0x6ad6 += gp-0x6bc2  ~ -a                                             PROVEN
   error = measured - gp-0x6ad6   ~ +k*a                                    PROVEN
   gp-0x6ad4 = -K*error           ~ -k*a                                    PROVEN
   aggregator += gp-0x6ad4        => the sum OPPOSES acceleration           PROVEN
   (unproven: whether a more-negative gp-0x6b94 is less assist in the driver's direction)
```
⇒ **opposing acceleration is POSITIVE damping — stabilising.** So disabling the term would most
likely make the ratchet **WORSE**, which is exactly the inverted-sign outcome the card pre-registered.
⊕ **Independent support:** Honda ships this flag **enabled**. A manufacturer adds acceleration
feedback for damping; it would not enable a destabilising one. The decompile and the shipped
configuration agree.

✅ **ACTION: V189 is restored as the recommendation. `docs/scoring/DRIVE-CARD-V190.md` is marked
NOT RECOMMENDED** (the artifact is kept — it stays a legitimate probe if V189 leaves ratchet behind
and we want to test this term deliberately, knowing it may worsen it).

🛑 **THE PROCESS POINT, worth more than the build:** the lever was built, recorded, and its sign
labelled **BELIEF** with the failure mode pre-registered — and then the verification killed it
**before it cost a drive.** *"I'm not sure, here's what I'd need to verify"* is the preferred output;
this is what it looks like when the check comes back negative. **Do not ship a lever whose sign
rests on an unverified chain when the chain is decompilable in one tick.**

## ✅✅✅ **V190 — A WHOLE FEEDBACK PATH THE ARC HAS NEVER TOUCHED, AND IT PEAKS AT CREEP**
Tracing the second acceleration EMA found a complete path nobody here has ever looked at:
```
   FUN_00041464   gp-0x6c2e = EMA(rate derivative) >> 9        the 2nd accel channel (cal 0xC40DA)
   FUN_00036f30   L = LERP(0xC68EA/0xC68F2, speed)
                  gp-0x6bc2 = clamp(((L*a)>>6) * sign(gp-0x6752) * gp-0x69be >> 6, +-gp-0x6bc0)
   FUN_00037fe6   gp-0x6ad6 = clamp((SUM + gp-0x6bc2*cal(0xC64AE) + ...) * LERP >> 10, +-25600)
                              ^ gp-0x6ad6 is the TORQUE-TRACKING REFERENCE
```
🛑 **AND THE RECORD'S DESCRIPTION OF THIS SUM WAS WRONG.** It says *"the six-term Path-2 sum in
`FUN_00038148`, weights `0xC63A0..0xC63AA`, only w[3] is frequency-selective."* Actually:
**`FUN_00037fe6` · SEVEN terms · flags at `0xC64AD..0xC64B3`** — and they are **ENABLE FLAGS (0/1),
not gains**, all reading 1 in stock/V122/V189. (Their siblings `0xC64AB`/`0xC64AC` ship at **0**,
which is what proves 0 is a supported state.) ⇒ **there are TWO ω²-scaled terms, not one.**

### ✅ WHY THIS IS THE RIGHT SHAPE FOR THE RATCHET
```
   omega^2 scaling      acceleration-derived => 66x stronger at 8.2 Hz than at 1 Hz
   speed weighting      X = [0, 4, 32, 96] km/h   Y = [64, 64, 32, 32]
                          1 km/h -> 64      24 km/h -> 41      40+ km/h -> 32
                        ** 2x STRONGER AT CREEP **, and the ratchet is a creep symptom
   DC contribution      ZERO -- acceleration is 0 in steady state
```
✅ **So it costs NO LKAS authority and NO added steering weight** — which is exactly the operator's
standing constraint: *do not buy the ratchet fix with apparent mass or friction.*
✅ **V190 = V189 + `0xC64AE` 1→0.** One byte, cal-only, 41/41 assertions.
`ab75a383fad5c65ad03645daffa8d3a93d15916040b438d3a01275e82196744f`

⚠ **THE SIGN IS BELIEF, NOT EVIDENCE — and this is the honest limit.** `gp-0x6752` is −1 (verified
3 ways) so `gp-0x6bc2 ≈ −k·a`; following the recorded polarity chain (`gp-0x6ad6` ↓ ⇒ error ↑ ⇒
**more** assist), positive acceleration → more assist → **positive acceleration feedback = negative
apparent inertia = destabilising**, so removing it should damp the ratchet. **That chain has five
links.** EVIDENCE: the term exists, is acceleration-derived, is 2× weighted at creep, flag reads 1.
BELIEF: the sign. 🛑 **If the sign is inverted the term was providing DAMPING and the ratchet gets
WORSE** — a one-byte revert to V189 undoes it. That failure mode is pre-registered on the card.

## ❌ **NEGATIVE RESULT, RECORDED SO IT IS NEVER REPEATED: THERE IS NO SECOND DORMANT FILTER**
Hunted every dormant Honda feature with the gate signature the biquad uses — a **tp-relative CAL BYTE
that reads 0 in stock** and is compared against a constant. **48 such cals exist.** Every one that
touches the steering path was resolved by decompile:
```
   0xC649B                the BIQUAD ARM        -- already used (V103)
   0xC64AB / 0xC64AC      MUTE switches (cal==0 ENABLES the term) in the gp-0x67ac==1 aggregator
                          branch, gating the RETURN-CENTRE/DETENT term -- which the record already
                          measured DEAD ENGAGED (0.0000 over 75,227 frames).  Useless to us.
   0xC40EB..0xC40EE       DIAGNOSTIC SENSOR OVERRIDES, one per channel:
                            if (magic == 0x49d6b173 && cal == 0xE9)
                                gp-0x6abc = base + value*cal(0xC6134)/1000;   // synthetic
                            else gp-0x6abc = real sensor;
                          Honda's factory injection path for gp-0x6abc/6abe/6ac0/6ac2.
                          NOT a filter, and not something to arm on a moving car.
```
⇒ **ONE biquad, ONE notch. The V188/V189 allocation decision is FINAL, not provisional.**

✅ **BONUS — the delivery path is now decompile-confirmed end to end:**
`FUN_00041464` (sensors, and `gp-0x6c2c = EMA(accel) >> 9` with the EMA coefficient at **`tp+0x50DC`
= `0xC40DC`, exactly the cell V179 moved**) → `FUN_000352b4` (boost + the biquad) → **`gp-0x6b86`**
→ `FUN_0003aa2c` aggregator sum (clamped ±12288) → `gp-0x6b94` → governor → motor.
⊕ **So the notch's output really does reach the motor** — V188/V189's premise is verified, not assumed.
⊕ A **second, parallel EMA** on the same acceleration input exists: `>>7` with coefficient
`tp+0x50DA` = **`0xC40DA`** → `gp-0x6c2e`. Unexplored.

🛑 **METHOD TRAP HIT AND FIXED IN THE SAME TICK — the recorded V850 odd/even displacement bug.**
`ld.bu disp16[tp]` has **two** opcode fields: bits5-10 == **0x3D ⇒ displacement ODD**
(`disp = (hw2 & 0xFFFE) | 1`), **0x3C ⇒ EVEN** (`disp = hw2 & 0xFFFE`). My first scan filtered on
0x3D alone and then computed the displacement as even, so it **caught only the odd half AND reported
every address one too low** — inventing a phantom cal `0xC649A` next to the real arm `0xC649B`.
✅ Caught by cross-checking one address against Ghidra's own decode. **Validate any cal scan by
requiring a KNOWN cell to appear** — here, the arm `0xC649B` at `0x359FE`.

