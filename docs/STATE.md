# STATE — living current state of the kit

## 🛑🛑 THE STEERING-RATE DEFICIT IS **MEASURED, REAL AND UNIVERSAL** — AND V111 DID NOT CAUSE IT
2026-08-27. Answers the operator's standing question (*"it feels like the max angular velocity has not
scaled 6x"*). **He is right, and it is not a V111 regression.**

```
  CORPUS POOLED — 18 cached routes, engaged & hands-off (D3) & moving, weighted by n
  demanded deg/s      n        RAIL DUTY (|cmd| >= 4090)      achieved / demanded
      5 - 15       103158             5.9 %                        0.73
     15 - 30        36595            16.9 %                        0.63
     30 - 60        18137            32.0 %                        0.47
     60 +           13407            49.8 %                        0.30
```
🛑 **Rail duty rises monotonically with demand.** Above 60 °/s openpilot emits its absolute maximum
(`STEER_MAX = 4096`) **half the time** and still gets **30 %** of the motion. ⇒ **AUTHORITY-STARVED.**
⊕ **Not the plant** — the **driver reaches 335.2 °/s** at the same speeds; LKAS at a railed command
reaches **84.6**. ⊕ **Not a hard clip** — no pile-up at 84.6 (2 samples within 5 %, vs 13 for manual),
and the engaged max moves with speed. A **soft roll-off.**

### ⭐ NOT A V111 REGRESSION — THIS RETIRES THE α2 REVERT
`ach/dem` at 60+ °/s is **0.09–0.49 across all 18 routes, median ~0.26**; **route 21 (V111) = 0.24.**
The deficit predates V111 on every build. 🛑 **Reverting `0xC40DC` α2 14→22 will NOT restore the
rate**, and the "α2 rotates inertia into friction ⇒ that caps velocity" story cannot explain a deficit
that predates it. ⊕ `gp-0x6b26` is clamped by `cal(0xC407E) = 511` (**decompile-confirmed**, operand
`tp+0x507E`) ⇒ ≤ 2.6 % of the ±20 000 residual, and α2 moves only its friction component
(Δ ≈ 0.078 at 8 Hz) ⇒ **≤ ~40 counts = 0.2 % of range.** Far too small.

### 🛑 FOUR CLAMPS EXCLUDED BY ARITHMETIC — DO NOT RE-PROPOSE
| candidate | why dead |
|---|---|
| `0xC520C` cap table | already struck; measured dead on route `a6` |
| `0xC6202` governor 4762 | full-command LKAS = `15360*5346>>15` = **2506** < 4762; also lockstep-shadowed → fault 0x17 |
| `0xC61B2/B4` arb clamp 3072 | **2506 < 3072** ⇒ never bites at 6x (would at ≥7.35x) |
| a hard 84.6 °/s rate clip | no pile-up |
⊕ `0xC646C` is **891 on every build**; the 6x lives on `0xC6CD0` = **5346** (= **6.000x** exactly).

### ⭐ CONSEQUENCE — IT INDEPENDENTLY CONFIRMS V112
`STEER_MAX` is openpilot-side and off-limits, so the useful lever is **more wheel motion per unit of
command with no added impedance.** **V112's corner move 10.6 → 31.8 °/s covers exactly the band where
`ach/dem` falls 0.63 → 0.47**, and more friction compensation = more assist (verified polarity).
Arrived at from a completely different direction than the ratchet argument that motivated V112.

### 🛑 TWO RETRACTIONS FROM THIS SESSION — both caught by their own controls
1. ~~"rate compresses against command"~~ — matched on speed and angle but **not on demand**; a high
   command also means *holding* a turn. Conditioning on demand dissolves it.
2. ~~"the car delivers 89–107 % of demand"~~ — used **`ct_curv` = `controlsState.curvature` = CURRENT**,
   so it was **circular** (tell: `r = -0.9995` vs measured angle). 🛑 **In this cache
   `ct_curv`/`cc_ccurv` are CURRENT; `ct_dcurv`/`cc_curv` are DEMAND.**

### ⚠ NOT ESTABLISHED
**Where** the roll-off lives. Four clamps excluded; loop bandwidth, the LKAS lane low-pass and plant
load remain. ⚠ The 60+ band is partly **planner steps** — the **15–30 °/s band (0.63, rail 16.9 %)
carries the argument**, being ordinary and physically reachable.

## ⭐⭐ V112 BUILT — THE FIRST LEVER THAT SATISFIES THE BOTH-AT-ONCE DIRECTIVE
```
builder  analysis-2020accord/builds/v108_plus/build_v112_tva.py   37/37   BASE = V111
image    f032878c4e0b8e90d782ddac6ba2d644e09956cc1b267a60ef4fb1c44ee1f96f
.rwd     64f2ee9eb23442673edd43251e1b27db90ba596ebea93016875379fbe0495692
0xC40BC   600 -> 1800   the relay KNEE     (saturation 10.6 -> 31.8 deg/s)
0xC40D2   204 ->  612   K1                 (cancels the knee's gain change EXACTLY)
4 payload bytes + 1 CRC trailer.  ZERO unattributed.  NO CAVE EDIT.
```
⭐ **Scaling BOTH cells is the whole trick.** `gain = (K1/1024)(12/knee)`, `saturation = knee/12` —
the knee is in both, K1 in only one, so K1 cancels the gain change and leaves the saturation change
standing. `(204/1024)(12/600) = (612/1024)(12/1800) = 0.0039844` **exactly** ⇒ **below 10.6 °/s V112
is BIT-IDENTICAL to V111**; above it the term keeps climbing instead of clipping.
⇒ **It adds NO impedance** — it reshapes a feed-forward friction COMPENSATION, so it cannot cap max
angular velocity the way `gp-0x6b26`, the damper and α2 all do. **That is what makes it the first
lever compatible with the operator's directive.**

### ⭐⭐ ROUTE 21 IS THE V111 DRIVE — AND IT MEASURED THE RELAY
Identified by **physics, not assumption**: the 427 tap's quantiles numerically EQUAL the steering rate
from `ang` — p95 39.4 vs 40.4, p99 167.4 vs 171.8, **p99.9 313.4 vs 313.3 °/s**. Only true if the tap
is `gp-0x6abc` at sar 3. ⊕ **Independently confirms the 4.7121 ct/(°/s) scale.**
```
  RELAY SATURATION DUTY  --  5-10 mph, engaged, hands-off, |cmd|>=2048, n=289
     knee  600 (V111)  0.7439   95% CI [0.6691, 0.8146]   <- ON THE CAR
     knee 1200         0.4810
     knee 1800 (V112)  0.2353                             <- BUILT, a 3.2x cut
     knee 2400         0.0484
```
🛑 **THE RELAY IS IN HARD COULOMB MODE 74 % OF THE TIME IN EXACTLY THE REGIME HE NAMED.** First
direct measurement of the mechanism the kit has asserted since V80. ⊕ Unconditioned the same regime
is 18.5 % ⇒ **command drives saturation 4×**, matching the command gate from a different instrument.

### GATES
✅ **GATE 1** — one reader each, two methods agreeing: `0xC40BC` at `0x3BAB4`, `0xC40D2` at `0x3BAFE`.
✅ **GATE 2** — the knee is an **odd, memoryless saturation** ⇒ DF real ⇒ **ZERO phase added.** The
magnitude rises ≤2.97× **but can never exceed the small-signal gain, which is unchanged and already
exercised at low rate every drive.** No new gain regime.
✅ **THE CLAMP OBJECTION IS DEAD** — `cal(0xC7468)=41232` and the residual clamps at ±20000, so
`|model| ≤ 0.4851` and `friction_max = 0.290` against a ±10.0 clamp: **34× headroom** (103× at V111).
⚠ **THE COST, PLAINLY:** above 31.8 °/s the residual falls `0.80·|model|` → `0.40·|model|` — a 2×
reduction in the torque-tracking reference. More assist by the verified polarity, but not small.
And `FUN_0003b8f6` is **not LKAS-gated**, so manual feel changes above 10.6 °/s too.

### 🛑 α2 IS DELIBERATELY LEFT ALONE
`0xC40DC` stays at V111's 14. The α2 cut is the suspected source of the friction he objects to, but
that magnitude is **unverified**, and reverting it would give back three measured improvements for
one regression. **V112 changes the RELAY ONLY**, so his next report is a single-variable read on the
relay hypothesis.

## 🛑🛑 V111 FLEW — OPERATOR REPORT, 2026-08-27. **THREE SYMPTOMS BETTER, STEERING RATE WORSE.**
**AND A STANDING DIRECTIVE THAT RULES OUT A WHOLE CLASS OF LEVER.**

⭐ **V111 is the cleanest single-variable experiment this kit has ever run.** V111 − V108 = three
payload bytes, two of them telemetry; **the only dynamics change is `0xC40DC` α2 22→14.** Every other
cell — relay knee 600, gain 5346, the `gp-0x6b26` Y row, the biquad, the whole 164-byte cave — is
byte-identical. ⇒ **whatever he felt, α2 caused it.**

### HIS WORDS — the primary readout
> *"Regarding the grinding issue, **most of it has been resolved.** However, **grind number one still
> occurs at low speeds between 5 and 10 mph, particularly under strong openpilot commands.** The
> frequency is **higher-pitched than before**, but it is a **muted or attenuated version.**"*
>
> *"**I no longer observe general oscillations** when driving straight or during slight turns. **The
> ratcheting effect also seems reduced**, but this appears to have come at **the cost of maximum
> steering angular velocity and acceleration.**"*

### 🛑🛑 THE DIRECTIVE — binding on every future lever
> *"**Increasing mass and friction should not be our primary approach to resolving the ratcheting if
> it comes at the cost of max steering angular velocity and acceleration. We want both: low apparent
> steering mass and friction to LKAS AND no ratcheting (feedback from driver torque sensor).**"*

⇒ **This is well-posed, because the two requirements live on DIFFERENT PATHS.** MOTION-fed lanes
(`gp-0x6b26` inertia, `gp-0x6bbe` viscous, the base-assist damper) oppose **all** motion and therefore
**cap max angular velocity by construction** — the LKAS command has to push through them. TORQUE-fed
lanes (the PID in `FUN_0003a382` on `gp-0x4f60`, the observer/friction lane) close the loop he calls
*"feedback from driver torque sensor"* and **do not load the LKAS path.**
🛑 **⇒ THE RATCHET LEVER MUST BE TORQUE-PATH. A motion-fed lever cannot satisfy him.**
Full note: `memory/feedback/builds/feedback-do-not-buy-ratchet-with-mass-and-friction.md`.

### ⭐ THE MECHANISM — lowering α2 rotates INERTIA into FRICTION
`gp-0x6b26 = −K·gp-0x6c2c` and `gp-0x6c2c` is filtered **acceleration**, so the term is pure apparent
**mass while in phase**. EMA lag `φ` rotates it; the component in phase with **velocity** — friction —
scales as `sin φ`, and α₂ 22→14 roughly **doubles φ**:
```
    f Hz   FRICTION component 22 -> 14   ratio      MASS ratio
    1.00        0.0120 -> 0.0224         1.87x        1.000x
    5.00        0.0596 -> 0.1104         1.85x        0.990x
    8.00        0.0946 -> 0.1723         1.82x        0.976x
```
⇒ his *"increased mass and friction"* is, by this account, **almost entirely FRICTION**, and friction
acts against velocity — exactly what caps angular velocity. It also explains the ratchet reduction
(more damping at ~8 Hz) and the grinding reduction (−27–−40 % over 61–300 Hz) **from the same byte.**

### 🛑 THE HOLE, STATED RATHER THAN PAPERED OVER
**Magnitude NOT verified.** `gp-0x6b26` clamps at ±511 against a ±20,000 residual (≤ **2.6 %** of
range; engaged p50 recorded at **4.8 counts**) — **doubling 11 % of a 2.6 % term is small to explain a
felt loss of steering rate.** ⚠ **And the counter-argument:** lower α2 also shrinks `|gp-0x6c2c|`, so
`gp-0x6b26` should **rail LESS**, which points the other way. **[BELIEF: right sign, right band,
magnitude unverified.]**

### ✅ WHAT WOULD SETTLE IT — AND THE DATA MAY ALREADY BE ON DISK
**Route `21`: 18 segments, uncached, newer than `1e` (V107).** If it is the V111 drive it carries
**V111's own `gp-0x6abc` tap** ⇒ (1) the **relay input amplitude** V111 exists to measure (GATE 2 says
the knee only bites below ~200–400 counts), and (2) `gp-0x6b26`'s real magnitude and rail duty, which
closes the hole above. 🛑 **It must be registered in the `ROUTES` table that
`extract_r7d.extract_route()` reads. That is the single highest-value action available.**

### ⚠ THE UNCOMFORTABLE COROLLARY — a straight α2 revert is NOT an obvious win
It would recover the steering rate but give back **three measured improvements for one regression.**
One EMA pole **couples** the magnitude cut (helps) to the phase lag (hurts). **Do not propose the
revert as a free fix.** ⊕ The real target is a lever that **decouples** them: cut the torque-path
feedback at the ratchet frequency (candidate: **`Kd`, all four knots `0xC6AE6/E8/EA/EC`**, which
reduces a feedback GAIN and therefore **cannot add apparent mass**) while leaving α2 where it is.
⚠ Kd's priced cost is **2.9–4.4:1 against, paid in 18–31 Hz grinding damping** — computed when
grinding was the top complaint. **It no longer is. Re-weigh, do not re-quote.**

## 🛑🛑 V108 FLEW — OPERATOR REPORT, 2026-08-27. **HIGH SPEED FIXED; LOW SPEED UNCHANGED; AND THE PREDICTION LANDED.**

🛑 **ON THE CAR: V108.** No rlogs available for this flight — **the operator's own words are the entire
readout**, and by the standing rule they are the PRIMARY one. Verbatim, in his terms:

- **"High speed behavior is good overall. I don't experience any oscillations or... any oscillations
  even on hard turns at speed at this point. So that has been fixed."**
- **"Twenty miles an hour and above, generally, this is the best that it's ever been in that regime at
  six x."**
- **"Around sixty to sixty five miles an hour, I think sometimes I do hear a grinding, or it's like a
  whole vehicle vibration... I'm not really completely sure that this is our firmware's fault. It might
  have just been the road because it's not consistent."**
- **"Low speed below ten miles an hour, grinding is still there. The audible grinding is still there. It
  seems like it's made up of TWO MODES. One mode that is slightly higher pitch, maybe around a hundred
  hertz. And there's another mode which seems like it's around a hundred or two hundred hertz...
  significantly higher in pitch."**
- **"At low speed, the maximum steering angular velocity is still limited."**
- **"Around ten to fifteen miles an hour, maybe ten to twenty, there is oscillation and grinding."**

### ⭐⭐ THE PREDICTION LANDED — the symptom map and the rail-duty map agree ACROSS A BUILD CHANGE
```
  speed        V107 measured   V108 predicted            operator's report on V108
  <6 mph          1.68 %       1.47 %  (Y[0] BYTE-IDENTICAL -- nothing changed here BY DESIGN)
                                                          grinding still there, TWO modes
  6-15 mph       32.32 %       <=15.46 % (halved, still the worst bin)
                                                          oscillation AND grinding
  15-25 mph      21.27 %       <=10.45 % (halved)         --
  25-40 mph       4.27 %       <= 3.43 %                  "best it's ever been at 6x"
  40+ mph        <=0.23 %      <=0.23 %  (identical to V107)
                                                          "that has been fixed"
```
🛑 **Where the duty fell, he reports it fixed. Where it stayed highest, he still hears it. Where the
calibration was deliberately left byte-identical, nothing changed.** That is the first quantified
on-car prediction in this kit's history and it held. ⚠ **EVIDENCE for the duty numbers and for his
report; BELIEF that the mapping is causal** — one build, no rlogs, and no matched control.

### WHAT THIS SAYS ABOUT THE REMAINING SYMPTOMS
- **The residual grinding sits exactly where V108's rail duty is still highest** (the 10–25 km/h bin, up
  to 15.46 %). **It is the same defect, under-dosed, not a different one.**
- ⭐ **His "two modes, ~100 Hz and something significantly higher" is precisely what V109's α2 targets:**
  −34 % at 100 Hz, −39 % at 200 Hz, for 8 % at the 21 Hz mode and **0 % at manoeuvre frequencies.**
- **The low-speed steering-rate limit is the same railed-damper DC drag** (`sign(α)·511` = 10.7 % of the
  governor ceiling), and it is worst exactly where duty is highest. V109 attacks it without costing
  manoeuvre-band authority.
- ⚠ **The 60–65 mph vibration is probably NOT ours.** At 96–105 km/h the rail duty is **≤0.03 %**, and
  that regime is **byte-identical between V107 and V108** — so a firmware change cannot explain a change
  there. Inconsistent, whole-vehicle and speed-specific fits road surface or a wheel order. **His own
  instinct was right and is recorded as such.**

⇒ **V109 IS THE NEXT BUILD, and now for a measured reason rather than a structural one.**

### 🛑🛑 CORRECTED — **V109 AND V111 DRIVE IDENTICALLY.** THE CHOICE IS THE INSTRUMENT, NOT THE FIX.
⚠ **Earlier in this session I repeatedly recommended "V109 first, then V111". That framing was
WRONG** and is corrected here. They are not a sequence of fixes.
```
  V108 -> V109 :  0xC40DC  16 -> 0e                        1 payload byte  + CRC
  V109 -> V111 :  0x55DF2  d493 -> 4495 ; 0x55E10 a5 -> a3  3 payload bytes + CRC
  V108 -> V111 :  all three of the above                    3 payload bytes + CRC
```
**Every dynamics cell is byte-identical on V109 and V111** — verified from the images:
`0xC40DC` (α2) **14 on both**, `0xC40BC` knee 600, `0xC6CD0` gain 5346, `0xD7A5C` `gp-0x6b26` row,
`0xC60A8` biquad. **V111 IS V109 plus three telemetry bytes.**

⇒ **The decision is which MEASUREMENT the drive buys, not which fix is on the car:**

| build | 427 tap watches | what it answers |
|---|---|---|
| **V109** | `gp-0x6c2c`, sar 5 | sizes the `gp-0x6b26` Y row — open since V107 |
| **V111** | `gp-0x6abc`, sar 3 | **the relay's input amplitude** |

⭐⭐ **RECOMMEND V111 OVER V109 FOR A SINGLE DRIVE**, and GATE 2 is the reason: the knee lever only
bites **below ~200–400 counts** of `|gp-0x6abc|` (describing-function ratio **0.96–0.99** above ~400,
i.e. a knee raise does essentially nothing there). **That amplitude decides whether the ratchet lever
exists at all, and whether the ~1.28:1 trade is even on the table.** The Y-row question is worth less
than that now. ⊕ **Both builds deliver the identical α2 test** on the low-speed grinding, so nothing
about the fix is given up by choosing V111.
⚠ What IS given up: the `gp-0x6c2c` channel goes dark, so the Y-row solve waits for another drive.

### 🛑🛑 KNEE CORRECTION — **`0xC40BC` STOCK IS 600, NOT 300**
⚠ Stated wrong repeatedly this session. From the images: **STOCK 600** → V85 6000 → V87 600 →
**V99 300** → nine builds at 300 (V99–V107) → **V108 600**. ⇒ **V108’s edit was a REVERT to
Honda’s own value**, and for nine builds the relay saturated at **half** Honda’s threshold
(5.3 °/s instead of 10.6). ⭐ **That gives V108’s “best it’s ever been at ≥20 mph” a candidate
cause that is a revert, not an invention** — still unattributed (V108 moved four cells), but the
only one of the four that restores a Honda value the kit had overridden for nine builds.
🛑 **And it reframes the lever: raising above 600 EXCEEDS Honda’s setting.**

### ✅ V111 BUILT — THE RELAY PROBE.  3 PAYLOAD BYTES, NO CAVE EDIT, NO DOSE.
```
builder  analysis-2020accord/builds/v108_plus/build_v111_tva.py   36/36   BASE = V109
image    9c4865cffd337cfb5d27f66843edbff928a8ffbf6f365e4fdeb7e98f7ddfb546
.rwd     221d99c605d2d9d9f86b0788ba6f46621d9738b5b2f5d866ac2b31a81e63f42e
0x55DF2  d4 93 -> 44 95    CAN-427 tap source  gp-0x6c2c -> gp-0x6abc  (THE RELAY INPUT)
0x55E10  a5    -> a3       sar 5 -> sar 3
3 payload bytes + 1 CRC trailer.  ZERO unattributed vs V109.
```
🛑 **IT CHANGES NO DYNAMICS CELL.** The relay knee, K1, the relay offset, alpha2, the 6× gain, the
biquad and all four `gp-0x6b26` mode rows are asserted **byte-identical to V109**. The 164-byte cave
is asserted byte-identical too, so every carried rung still means what routes `a5`/`a6`/`1e` measured.
**No cave edit ⇒ outside this kit's only bricking class.**

**WHAT IT MEASURES.** The full distribution of `|gp-0x6abc|` — the Coulomb relay's input — on the wire
at 49.8 Hz, from which the relay's saturation duty at **any** candidate knee is computed post-hoc.
```
  (wire >= 31) AND NOT (wire >= 125)  ==  EXACTLY the population a knee 600 -> 2400 raise affects
```
Sizing at sar 3: peak 913/1023 (no ceiling), 1 count = 0.340 °/s, knee-600 lands at 31 counts and
knee-2400 at 125. sar 2 would saturate. **Sized against a measured distribution** (the sibling
`gp-0x6ac0` peaks at 1462 ct), not a guess.
⭐ **If that duty is near zero where the operator feels the symptom, the knee lever is dead and no
assist was ever spent.** The null is interpretable — which is why this is a probe and not a dose.

🛑 **FLIGHT ORDER: V109 FIRST, THEN V111.** V109's tap still watches `gp-0x6c2c`, which V108's E5
added specifically so the next drive could solve the `gp-0x6b26` Y row — open since V107.
**Re-pointing the tap costs that solve.** V111 is the build AFTER V109, not instead of it.
⊕ The tap re-point is a **proven** mechanism: V107 made exactly this edit at exactly these two
addresses and flew fault-free as routes `1b`/`1e`; V108 then moved only the shift. Third use.

⚠ **A guard caught a real defect during the build.** The inherited `V106B.assert_frozen` asserts
V106's expected values, and V107 (tap), V108 (knee, sar) and V109 (alpha2) have legitimately moved
four of them since — so it failed on correct edits. **Rebased to the V109-RELATIVE form**: every
kit-frozen cell must equal THE BASE, with only the two deliberately-edited addresses exempt. That is
both correct and stronger. 🛑 **Any future builder inheriting `V106B.FROZEN` has the same latent
bug** — the table is three builds stale.

### 🛑⭐ THE ACOUSTIC COST OF THE GAIN IS MEASURED — **+1.16 dB from 4× to 6×**
Full note: `memory/accord/mechanism/accord-the-acoustic-cost-of-the-gain-is-measured.md`.
Eleven-route audio spectrogram ladder built this session (`rlog-tools/decode/extract_route_audio.py`),
**with a STOCK arm**. Statistic = **MECH (60–400 Hz) − FAR (1200–2000 Hz)**, engaged-minus-manual,
matched speed <10 mph, hands-off, within drive.
```
  gain   n     MECH     FAR   MECH-FAR        6x - 4x = +1.158 dB
   1x    1    +0.01   +0.74     -0.73                   [+0.475, +1.817]
   4x    3    +0.36   +1.16     -0.80                   P(>0) = 1.000
   6x    6    +0.95   +0.58     +0.36         8 of 9 routes outside their own null
   8x    1    +2.01   +0.39     +1.62         n=1 for stock and 8x -- not tested levels
```
🛑 **FAR IS NOT OPTIONAL** — it rises too (+0.74 on stock, +1.16 at 4×), which proves the engaged
and manual segments differ in ways that lift the WHOLE spectrum. **Every single-band
engaged-minus-manual claim on this corpus is confounded by that**, and that is exactly how three
earlier framings died today.
⇒ **The 6× costs ~1.2 dB of steering-band cabin noise over 4×. Goals #1 and #4 are in tension
THROUGH THE GAIN ITSELF, and the tension is now numeric.** ⊕ Independently consistent with
`accord-the-8x-gain-is-the-carrier`, reached from the 20–26 Hz steering-rate band — two unrelated
instruments, same conclusion. 🛑 **It is a PRICE, not a prescription**: the operator wants 6×, and
`accord-4x-lkas-gain-is-the-frozen-variable` warns against recommending a gain cut.

❌ **THREE FRAMINGS DIED GETTING HERE, ALL THE SAME ERROR** — a narrow-band acoustic claim with no
adjacent-band control: *"the ≈100 Hz mode is ours"* (controls rise equally; residual ≤ 0 on 6 of 10),
*"an 83.5 Hz comb is the grinding"* (**stock fires too**; the comb estimator has a sub-harmonic
ambiguity), and *"PMSM 6th/12th torque ripple"* (decisively excluded — an order moves 40× across the
rate span, the centroid moves 1.04×).
⭐ **RULE, and the steering-rate work already followed it:** a narrow-band acoustic claim needs
**adjacent control bands**, and an *"it is ours"* claim needs the **STOCK arm BEFORE publishing.**

🛑 **V109's ENDPOINT, RESTATED:** score V109 against V108 on **MECH − FAR**, same road, same driver.
Not a comb, not a single band. ⚠ And V109's α2 cut is band-limited to 61–300 Hz while the excess is
broadband over 60–400 Hz — **it is NOT "aimed squarely" at this**, and the note claiming so was
corrected. **The V109 drive MUST capture audio** or the endpoint is unmeasurable.

### ⭐⭐ THE COMMAND GATE SURVIVED ITS 2-D CONTROL — AND THE RELAY IS NOW **LOCATED IN THE CODE**
**Control first** (the one that killed three other findings today): command and steering rate are
correlated engaged, and the ratchet's rate-dependence is already known, so the command gate had to be
separated from it. 2-D cells, <20 mph, engaged, hands-off, 1058 windows, 6-9/1-3 band shape:
```
                rms<8      8-20 deg/s    20-45
  cmd <1k     0.50(493)    0.93(302)   1.39(83)
  cmd 1-2k        -        1.13( 50)   3.87(32)
  cmd 2-3k        -        4.72( 23)   1.70(22)
  cmd 3k+         -       44.71( 36)   4.33(17)
```
⭐ **At MATCHED rate (8–20 °/s) command drives a 48× fold; at matched command, rate drives only 2.8×.**
⇒ **genuinely command-gated, NOT the known rate effect.** The `3k+ / 8–20 °/s` cell — maximum command,
wheel barely moving, 45× the 7.8 Hz content — is the ratcheting isolated.

**And the mechanism is now located**, `FUN_0003b8f6` @`0x3B8F6` (full arithmetic in
`memory/accord/mechanism/accord-the-coulomb-relay-is-located-c40bc-is-its-knee.md`):
```
fVar13   = clamp( POL * gp-0x6abc * 12 / cal(0xC40BC), -1.0, +1.0 )   <-- THE RELAY
friction = EMA( |model| * cal(0xC40D2)/1024 * fVar13 + cal(0xC4080)/1024 * fVar13 )
gp-0x6ae2 = friction * 1024 ;  iVar20 = (model - friction - inertia) * gain
```
⇒ **magnitude ← `|model|` (tracks COMMAND); shape ← rate against the KNEE.** The two factors of the
product map onto the two axes of the measurement. Saturates at `|gp-0x6abc| >= knee/12`:
300 → 25, 600 → 50. 🛑 **600 is STOCK** — V99 halved it to 300 and it stayed there for NINE
builds (V99–V107); **V108 RESTORED Honda's value.** The operator called
≥20 mph *"the best it's ever been"* — ⚠ unattributed (V108 moved four cells), but it is the only one
that touches the relay.

🛑 **THE COST, BEFORE ANY DOSE:** `clamp(x/knee, ±1)` is **monotonically decreasing in the knee**, and
`accord-friction-polarity-more-assist` is verified nine ways — **more modelled friction = MORE assist**
⇒ **raising the knee REDUCES ASSIST**, trading directly against the 6× goal, in the same direction that
made V93/V94 unsafe. **Do not propose a knee dose until the assist cost is priced in counts.**
🛑 **CRUX, NOT YET VERIFIED: the scale of `gp-0x6abc`.** If it shares the 4.7121 ct/(°/s) column-rate
scale, V108's knee saturates at **~10.6 °/s — inside the 8–20 °/s band where the ratchet was isolated.**
`gp-0x6abc` is a DIFFERENT cell from `gp-0x6ac0`; the scale must be measured, not assumed.
⊕ **An instrument already exists**: `gp-0x6ae2` is the friction output and V106's `b5` rung compares
`|gp-0x6ae2|` against `|gp-0x6b26|`. A knee dose would fly with telemetry on it from day one.

### 🛑🛑 RETRACTED — "THE GAIN STOPS DELIVERING AT LOW SPEED" DOES NOT SURVIVE SPEED-MATCHING
⚠ **I told the operator twice that the data backed his perception. Properly controlled it does not —
and it does not contradict him either.** With **2 mph speed cells** (not a wide `<15 mph` bin) ×
`|cmd| >= 3072`, hands-off, route bootstrap on both arms, ideal 1.500:
```
  <=15 mph   1.292  [0.925, 1.673]   P(<1.500)=0.860   <- 1.500 is INSIDE
  >=15 mph   1.858  [1.387, 2.485]
  CONTRAST   0.711  [0.451, 1.032]   P(<1)=0.963       <- CONTAINS 1
```
**Nothing survives at 95 %.** The earlier 1.030 came from a speed mismatch inside the bin — median
speed within `<15 mph` was **6.2 mph (4×) vs 8.3 mph (6×)**, and acceleration varies strongly across
that range. 🛑 **RULE: match speed in cells <= 2 mph for any cross-build contrast on this corpus;
a `<15 mph` bin is NOT a speed control.**
⇒ **UNDERPOWERED, NOT REFUTED** — the 6× arm carries only 5–15 s per cell and the interval is 1.8×
wide. Closing it needs deliberate matched hands-off low-speed segments at large command, on both a
4× and a 6× build, on the same road.
✅ **UNAFFECTED and still standing:** the ratchet/grind **command gate** (a within-window band contrast
with its own internal controls — two control bands FALL while 6–9 Hz rises 3–4.7×); the hands-off
lesson; the E3 reconciliation (rate is an integral, so a rate test is blind to a torque ceiling, and
pulling `0xC61BE` was correct); and the refutation of stick-slip.

#### ⚠ SUPERSEDED, kept for the audit trail — the original claim
He pushed back on the `STEER_MAX` answer: *"I'm looking for a more structural limitation… one that does
not scale with the 6x LKAS gain… it feels like the max angular velocity has not scaled 6x."* **Tested
and confirmed.** `rlog-tools/studies/authority/gain_delivery_and_command_gate.py`; notes
`accord-gain-stops-delivering-at-low-speed-high-command` + `accord-ratchet-and-grind-are-command-gated-saturation`.

**Instrument:** angular acceleration in the commanded direction ∝ NET TORQUE at the instant. Ladder read
from the images (`0xC6CD0` 891/3564/5346/7128 = 1×/4×/6×/8×), build per route from `probe_build`.
Route-level p90, route bootstrap. **Ideal = 1.500.**
```
  ALL speeds, cmd>=3000    1.429 [1.134, 1.737]   <- the gain DOES reach the motor
  <15 mph,    cmd>=2048    1.030 [0.694, 1.499]   <- it does NOT, here
  15-45 mph,  cmd>=2048    1.814 [1.276, 2.522]   <- full delivery
  RATIO-OF-RATIOS          0.557 [0.359, 0.909]   P(low<high) = 0.992
```
🛑 **AND A CORRECTION MADE MID-ANALYSIS:** the first pass omitted the hands-off mask and returned
*"the gain scales NOWHERE"* (0.948 [0.748,1.182], no knee in any command bin). **That was the DRIVER** —
at low speed his hands move the wheel and his torque swamps LKAS. D3 flipped the low-command bins to
~1.50. ⭐ **Any cross-build torque or rate comparison at low speed is meaningless without a hands-off mask.**

⭐⭐ **AND THE RATCHET RIDES THE SAME GATE — this is the ratcheting answer.** Band SHAPE (power
normalised by 1–3 Hz in the same window), <20 mph, engaged, hands-off:
```
  fold-rise vs <1k cmd    3-5 ctl   6-9 RATCHET   10-13 ctl   14-18 ctl   20-26 grind
  1k-2k                      0.7x         3.0x        0.7x        1.1x          4.0x
  2k-3k                      0.6x         4.7x        0.7x        1.1x          5.7x
  3k+                        1.9x        52.0x        3.3x       12.7x         11.8x
```
**Two control bands FALL while 6–9 Hz rises 3–4.7×.** A cornering confound lifts every band; this does
the opposite. ⇒ **the ratcheting is SWITCHED ON by command magnitude — not a passively-excited
resonance** — and the 20–26 Hz grind rides the same axis.
⇒ 🛑 **[BELIEF, strongly supported] ONE saturating nonlinearity produces both symptoms**, in the same
regime where extra gain stops buying torque. **Sixty builds hunted a LINEAR lever (a pole, a damper, a
gain) for a COMMAND-TRIGGERED nonlinearity. A linear lever cannot fix a relay.** The target is the
saturating element: raise its ceiling or soften its corner.

**EXCLUDED already:** `0xC520C` (rate-indexed, first knot 222.8 °/s, struck by its own author) and the
forward clamps `0xC61B2`/`B4` (**they scale exactly with the gain** — 512/2048/3072/4096 for 1×/4×/6×/8×,
byte-verified V96→V110). **Still open:** the governor's vehicle-speed read (`0xC6316` ≈10 km/h); a shared
base-assist+LKAS sum Honda's own curve already fills at low speed; or — not a lever — the **motor current
limit**, since tyre scrub is highest at low speed. ⇒ **The discriminator is a delivered-torque or
motor-current channel, which the corpus does not carry cleanly across the 4×/6× builds** (CAN 427 was
repointed for probe use from V88 on). **That is the next telemetry to buy.**

### 🛑🛑 GOAL #5 IS ANSWERED, AND THE ANSWER IS NOT IN THE FIRMWARE
**The low-speed steering-rate limit is COMMAND SATURATION at openpilot's `STEER_MAX` = 4096.**
Measured 2026-08-27 from caches already on disk; reproducible via
`rlog-tools/studies/authority/steer_max_saturation.py`. Full note:
`memory/accord/mechanism/accord-low-speed-rate-limit-is-openpilot-steer-max.md`.

**The clamp is real** — `|e4tq|` histogram approaching its edge on r77 engaged decays smoothly
`832 / 903 / 394 / 183 / 112 / 34 / 25 / 3` and then **spikes to 13,783 at exactly 4096**, with
**zero frames above 4096 in ~200 cache files across the whole corpus.**

**It binds exactly where he feels it** — duty of `|e4tq| ≥ 4096` while engaged:
```
  band     r77      ra6      r1e          <-- "below ten mph the max angular velocity
  <6 mph  0.4036   0.3099   0.0745            is still limited"  ... and ...
  6-10    0.3697   0.2100   0.0684        <-- "twenty and above is the best it has ever been"
  10-15   0.2146   0.0889   0.0615
  15-20   0.0965   0.1458   0.0521
  20-30   0.0323   0.0274   0.0503
  30-45   0.0028   0.0000   0.0087
  45+     0.0000   0.0000   0.0021
```

**And the car is NOT the limit.** Achieved rate in the commanded direction keeps **climbing** through
the rail (r77 p90 `66.8 → 78.9 → 93.9 → 143.6`), and the **driver slews the same rack 3–4× faster**
(p90 103–162, max 402–459 °/s). ⇒ **plant headroom exists; openpilot ran out of command.**

⇒ 🛑 **NO FIRMWARE CALIBRATION CAN RAISE IT.** The 6× gain multiplies what arrives; pinned at 4096,
the firmware is already delivering 6× of the most openpilot can ask. The only two routes to more
low-speed rate are **(1) raise `STEER_MAX` openpilot-side — the operator's call, and
`feedback-no-openpilot-side-modifications` says we do not touch it**, or **(2) push the firmware gain
above 6×, which is the measured carrier of the grinding.**
⇒ **Goal #5 and goals #1–3 are in DIRECT TENSION and the binding constraint sits OUTSIDE the
firmware.** This is why the symptom survived every build — **none of them could have moved it.**

✅ **Retired in the same pass:** the `gp-0x69b0` authority ramp. All five rate cals mapped
(`0xC63F4/F6/F8/FA/FC` = 328/16/33/66/328, two up + three down, all stock and virgin), and the
pre-registered test returned its null — **STEER_STATUS is identically 0 across 3,312 s engaged on four
routes, every speed band, zero transitions**, with the control passing (status 3 exists, only at
0.0 mph and only disengaged). The ramp reaches full scale ~1 s after engagement and holds.
🛑 **And a correction:** the record files `0xC63F8`=33 vs `0xC63FC`=328 as a *"10× LEFT/RIGHT
asymmetry"* and deprioritised it on a left/right null. **`gp-0x6803` is a MODE fork, not a direction
flag** — three values, two parallel SM chains (1→3→2 vs 1→6→7). Right answer, wrong reason; do not let
a future session revive the cals on "left/right was never the issue".

### 🛑 V110 IS DEAD — TWO INDEPENDENT KILLS, and the second one closes the whole Kd lever
`Re(Z)` **is** already measured to 35 Hz **with phase** on route 77 (`rlog-tools/studies/impedance/v92_rez_extend.py`,
89,471 frames / 884.5 s engaged hands-off, 221 windows, all ten bands passing a pre-declared
coh² ≥ 0.10 AND ≥ 5× shuffled gate). **There is no separate `G_bar(f)` unknown — the measured `arg Z(f)`
already contains the whole rotation, plant included.** The disputed memory's numbers reproduce from it
**to within 4 %** via `Re(Z)_branch = |Z|·|H|·cos(argZ + argH)`.
**And the sign reverses, convention-free:** `cos(argZ + argH_D)` = **−0.802 at 7.79 Hz** but **+0.894 at
20 Hz** ⇒ **D PUMPS at 7.8 Hz and DAMPS at 18–22 Hz.** Halving Kd would remove damping in **20–40 mph —
the exact regime the operator just called the best it has ever been.**
⭐ **And 18–22 Hz is the BEST-CONDITIONED band in the whole sweep** — episode-parity split-half agrees to
**2 % (r77), 1 % (r78), 15 % (r79)**. The conclusion rests on the most reliable band available.
⭐ **Now replicated on THREE drives** (628 windows / 74 episodes / 2145 s engaged hands-off): pooled
`d = −0.2303 [−0.2411, −0.2125]` at 18–22 Hz, **−0.236 / −0.208 / −0.224 per drive**, P(damping) = 1.000.
Halving Kd would remove **Δd = +0.1151**. At 26–31 Hz `d = −0.3049`, Δd = **+0.1525** — ⚠ heterogeneous
(r79 is neutral at −0.0072), so the honest claim there is *"never helps"*, not a magnitude.
⭐ **And it is robust in a way a single skew cannot defeat:** 18–22 Hz needs a channel skew ≥ **+8.6 ms**
to flip, 26–31 Hz needs ≤ **−5.9 ms** — **OPPOSITE DIRECTIONS.** No single skew, and no torque-channel
low-pass at any corner from 6 Hz to ∞, makes D pump in both grinding bands. The normalised `d` depends
**only on `arg Z(f)`**, so every magnitude error — plant, the `rate_f` 0.7996 scale — cancels exactly.
⚠ The one honest residual: pooled `arg Z` falls at **−7.80 deg/Hz** over 16–35 Hz, which *if it were all
instrument delay* would be 21.7 ms and would flip 18–22. It is probably not delay — the phase **rises**
+30° from 3 → 7.79 Hz first, and a delay can only make phase fall — but it cannot be decomposed from the
bus. Closing it needs an on-car gain-step system ID at 18–31 Hz.
⊕ Crossover, pooled: **24.97 Hz [24.48, 25.35]**; per drive 25.40 / 24.07 / 23.97 ⇒ quote the
between-drive spread **24.0–25.4 Hz**, since the per-drive bootstrap CIs do not overlap.

#### 🛑🛑 KILL 2 — V110 IS NOT "Kd 2048→1024". IT IS **ONE KNOT OF A FOUR-KNOT LERP.**
Independent of the sign, and **orchestrator-confirmed from the images and the decompile, not relayed.**
Byte diff V109→V110 is 5 bytes: `0xC6AE7 08→04` plus the CRC trailer. **`0xC6AE8`/`EA`/`EC` all remain
2048.** Decompile of `0x3A382`:
```
axis = gp-0x6ac0                                  # motor / resolver rate
X = (50, 400, 1500, 3000) @ 0xC6ADE/E0/E2/E4      # 0xC6ADE is X[0], NOT a separate gate cal
Y = (Y0, Y1,  Y2,   Y3 )  @ 0xC6AE6/E8/EA/EC
  axis <=   50 -> Y0 alone          <-- the ONLY place V110's edit acts alone
  50 ..   400  -> LERP(Y0, Y1)      <-- ramps out against a still-stock Y1 = 2048
  400 ..  1500 -> LERP(Y1, Y2)      <-- the edit is NEVER READ at or above axis 400
  1500 .. 3000 -> LERP(Y2, Y3);  axis >= 3000 -> Y3
enable: axis < 0x32C9 (12,993)     =>  the edit touches the bottom ~0.4 % of the axis
```
⭐ **AND THAT IS WORSE THAN INERT.** Stock Y is **flat 2048 at all four knots**, so the LERP is
currently a **constant**. A one-knot edit does not reduce a gain — it **converts a constant into a
rate-dependent function**, introducing a nonlinearity that does not currently exist, at 2× the
oscillation frequency, inside a loop already known to be marginally stable. Describing-function
territory, not a linear gain cut. ⇒ **On a flat table, a one-knot edit is never a gain change.**

⇒ **THE KD LEVER IS CLOSED, NOT JUST V110.** The correct four-knot form — which
`docs/review/GATE2-2026-08-11-cbe74-independent.md:150` already recommended — is precisely what makes
KILL 1's cost real. **Do not rebuild it properly.** V110's builder docstring has been corrected in
place and the artifact stays on disk, parked, as the audit trail.

#### 🛑 THE GATE-1 LESSON — add it to the gate
V110's census said *"one reader (`0x3A460`), zero writers"*. **That is TRUE OF THE BYTES and FALSE OF
THE LEVER**: Y0 is also reached through a **walked pointer** (`puVar11++`), the register-indirect form
that operand-text search structurally cannot see. ⇒ **A GATE-1 census that counts ACCESSES to a cal
cell cannot tell you whether the cell is a scalar or one knot of a table — that requires reading the
READER'S STRUCTURE.** This is the same blind spot as `accord-gp4f60-two-encodings-enumeration-trap`,
in a new costume.

⇒ **V110 stays parked permanently.** My rejection of the "no computation behind it" refutation was
correct, and it is now proven rather than merely plausible — but the build it was defending is dead
anyway, for a reason that had nothing to do with the sign.
⊕ **A method note worth keeping:** the 500-draw phase-randomised surrogate gives |z| ≈ 1 on `d`, and
that is **NOT a failed control** — a random-phase null is the *wrong null* for `d`, which is a bounded
arcsine quantity whose null is "phase is uniform". The correct uncertainty is the **episode bootstrap
on the phase: ±5–6° against a 62° flip threshold.** Do not later read that z≈1 row as a refutation.

#### THE FULL D-ROTATION COST LADDER, and where the argument is weakest
```
   band     d pooled   Δd on halving Kd   cost vs the +0.0389 ratchet benefit   flips at
   6-9      +0.0779      -0.0389 (help)          --                        tau -18.7 ms
   16-18    -0.1129      +0.0565                1.45x        ⚠ tau +5.2 ms, LP fc 27.3 Hz
   18-22    -0.2303      +0.1151                2.96x           tau +8.6 ms, LP fc 10.8 Hz
   22-26    -0.2898      +0.1449                3.72x           tau +9.3 ms, LP fc  4.1 Hz
   26-31    -0.3049      +0.1525                3.92x           tau -5.9 ms, NO LP possible
   31-35    -0.1124      +0.0562                1.44x           tau -1.3 ms
```
⚠ **16–18 Hz is the weakest link in the sweep** — it flips on only **+5.2 ms** of skew or a 27 Hz
low-pass. **If the channel-defect argument is ever reopened, that is the band it will be won in, not
18–22.** ⊕ **22–26 Hz is the most consistent band measured** (−0.2879 / −0.2993 / −0.2892 across three
drives) and is where the crossover sits. 31–35 Hz is heterogeneous — do not lean on it.

### 🛑 NAMING CORRECTION — the `Re(Z)` instrument is **bar torque ÷ MOTOR rate**
The kit calls it a *"driving-point impedance"* throughout. It is not one. `0x18F[2:4]` STEER_ANGLE_RATE
is **not independently sensed** — per `accord-gp6a56-is-motor-rate-not-an-angle-sensor` it is a fixed
Q15 scale of `gp-0x6abe`, the **motor resolver electrical rate**. So `Z = tq / rate_f` is
**torsion-bar torque ÷ motor rate.** ⚠ This is true of the **whole instrument — the 7.79 Hz anchor and
the `mean(T·ω)` sign anchor included** — not just the 16–35 Hz extension, so **it changes no comparison
and no verdict.** But the name is doing work it has not earned, and a future agent reading
"driving-point impedance" will assume a column-side measurement that was never made.

### 🛑 OPEN — one cave bit would settle "V110 inert" vs "V110 injects a nonlinearity"
`gp-0x6ac0`, the Kd/Ki/Kp LERP axis, is the resolver/FOC electrical rate. Its **duty below 50 and below
400** is exactly what separates the two readings, and **it is not on disk**: no cache carries
`gp-0x6ac0`, and the adjacent `g6ac2` field is a **single BACKDRIVE bit** (`extract_r67_v81.py:266`),
constant 1.0 on r77 and a **stale decode on V100+ routes**. The `rate_f → gp-0x6ac0` scale is also
unknown, so even the shape would not give an absolute.
⇒ **Two comparator rungs — `axis < 50` and `axis < 400` — give the duty directly.** Cheap, and it is
the difference between *"V110 does nothing"* and *"V110 modulates Kd at 2× the oscillation frequency"*.
⚠ **It does not reopen V110** — KILL 1 stands either way. Worth one bit the next time a cave is cut,
because the same axis gates Ki and Kp.

### ✅ THE THREE V36-BLANKED CELLS ARE CLOSED — benign, correctly in force, and NOT a lever
`0xC61C0` = **1600**, `0xC61C2` = **896**, `0xC61C4` = **1280** in stock; all three **`0xFFFF` since V36**
and byte-identical through V110. **12 reads, 0 writers**, exactly as flagged — four each in
`FUN_00028ea6` and `FUN_0002a30e`, all `ld.hu`, implementing one **4-tier OR-envelope**:
```
   torque > cal(0xC64B4)=112 (rise) / 0xC64B5=96 (hold)          [torque alone]
     OR  rate > cal(0xC61C0)=1600                                 [rate alone]
     OR (torque > 0xC64B7=64  AND rate > 0xC61C2=896)             [combined A]
     OR (torque > 0xC64B6=54  AND rate > 0xC61C4=1280)            [combined B]
   -> 5 consecutive qualifying cycles (cal(0xC64E2)=5) -> STEER_STATUS = 4
```
⇒ **`0xFFFF` disables the three RATE arms, leaving the torque-alone arm.** This is exactly the
gentle-EME fix the record describes, **validated on-car by V37 (2026-07-14) and correctly still in
force.** ⚠ **NOT a lever for anything currently being chased**: it is a level-threshold + 5-cycle
debounce, so **it cannot produce an in-band oscillation by construction**; it watches different signals
from the ratchet's `gp-0x6b26`/`gp-0x6c2c` path; and when it fires it writes **three status bytes and
nothing in the torque chain.** Max steering rate is `0xC61BE`, a different cell (byte-stock through
V110). **Do not touch these.**

⭐ **AND IT CLOSED A MUCH OLDER QUESTION.** The record's long-standing *"the actual assist-reduction
instruction during the felt cut is still unlocated"* (2026-07-14) is at least partly answered:
`STEER_STATUS` outside {0,1,2} **blocks an increment of `gp-0x69b0` and a state advance** — a real
gating effect, not a report:
```
   0x2a55a  ld.bu -0x6807,gp,r14        ; STEER_STATUS
   0x2a56a  jr 0x2a890                  ; 3,4,5,6,7 -> BAIL
   0x2a572  ld.hu 0x73f8,tp,r14         ; else cal(0xC63F8) = 33
   0x2a588  st.h  r11,-0x69b0,gp        ; gp-0x69b0 += 33
```
Since `gp-0x69b0` is the **Q15 multiplier gating the whole LKAS block** (established separately this
session, `0x2A1E6 mul r14,r9,r0`), **the felt cut is not a hard zero — it is a STALLED RAMP**, which
fits "gentle" far better than a hard cut and is consistent with V37 having fixed it on-car.
⚠ **BELIEF** — the `gp-0x69b0`→motor chain was not re-traced in that pass.

🛑 **AND THE UNDERCOUNTING TRAP REPRODUCED CONCRETELY, WITH A NEW CAUSE.** `FUN_0002a30e`'s Ghidra body
**stops at `0x2A507`** (a `dispose` epilogue on one exit path mis-detected as the function end), but the
code continues contiguously to at least **`0x2A8A6`**. `get_function_by_address` returns *"No function
found"* for that whole region ⇒ **`search_instructions` found 32 reads of `gp-0x6807` where a raw byte
scan found 40. Eight real reads were invisible.** ⭐ **Code that is disassemblable but NOT
function-bound is invisible to `search_instructions`** — that is the mechanism behind this trap, stated
concretely for the first time. ⊕ `get_bulk_xrefs` gave its false *"no references"* a **fifth** time.

### 🛑 A MEASUREMENT-DISCIPLINE FINDING ONE LEVEL UP FROM THE STANDING RULE
Crossover frequency (`Re(Z)` = 0), episode-bootstrapped per drive:
**r77 25.40 [24.93, 25.72] · r78 24.07 [23.67, 24.30] · r79 23.97 [23.81, 24.17].**
🛑 **The three per-drive CIs DO NOT OVERLAP**, and the between-drive spread is **~4× the within-drive
CI.** ⇒ **the episode bootstrap UNDERSTATES the real uncertainty.** Quote the between-drive spread
wherever it is larger. This is `feedback-episodes-not-windows` one level up: **episodes are not
independent across drives either.**
⊕ **And the manual hands-off arm still does not exist**: pooled over r77/r78/r79 it is **2 windows /
21.4 s**, unchanged since 2026-08-11 — r78's 27.6 s and r79's 13.3 s are too fragmented to yield a
single 5.12 s window. **The manual hands-off coast experiment is still owed.**

---

## ⚠ SUPERSEDED BLOCK, 2026-08-27 (build session) — **V107 FLEW AND THE DAMPER IS A COULOMB RELAY · V108 IS THE FIRST SUBTRACTIVE BUILD IN THIS ARC**

🛑 **ON THE CAR: V107** (routes `1b` 35.8 s and `1e` 988.6 s engaged, both fault-free).
**V108 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS, no SSH.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-27-v107-flew-the-damper-is-a-relay.md`** — 16 retractions,
14 open items with what closes each, the V108 drive card, and the V109 lever already priced and gated.
```
V108 image  7a9577dd181a235845e87e592fbd1a191957674aef7b0f17caac6907c114a9e4
V108 .rwd   4fbfda0d76af2f1b592bd9e510cd926dbfabb6a02b7a25730e7018f07cf4c4d1
builder     analysis-2020accord/builds/v108_plus/build_v108_tva.py   54/54 assertions   BASE = V107
E1  0xC60A8..B7  V105's 25.5 Hz notch -> HONDA'S OWN 16 BYTES (copied, never typed).  Arm KEPT.
E2  0xD7A5C/6C   Y (-29490,-24000,-16000) -> (-29490,-17202,-16000)   V106's Y0+Y1, V107's Y2
E4  0xC40BC      300 -> 600 (Honda)
E5  0x55E10      sar 3 -> sar 5    (the tap was sized against a 5x arithmetic error)
E3  0xC61BE      BUILT AT 16384, THEN **PULLED** ON ITS OWN PRE-REGISTERED NULL.  Byte-stock.
31 bytes vs V107 in 11 runs, ZERO unattributed.  CAL-ONLY.  THE CAVE IS BYTE-IDENTICAL TO V107.
```



### 🛑🛑 THE VISIBLE OSCILLATION IS **OPENPILOT'S WEAVE**, NOT THE EPS — AND IT IS A SEPARATE DEFECT
Route `1e`, 998.9 s engaged / 338.6 s manual, 10 episodes. Full note:
`memory/accord/mechanism/accord-visible-oscillation-is-openpilots-weave.md`.
**46 events covering 17.3 % of engaged time, up to 24.02° p2p = 77.6 mm at the rim, at 0.44–2.93 Hz.**
🛑 **His "under or around 10 Hz" is really 0.4–1.6 Hz — above 4 Hz the angle NEVER reaches a centimetre
on any engaged window (4–6.3 Hz max 4.3 mm; 6.3–10 Hz max 3.6 mm).** Every earlier search scanned
4–10 Hz and was structurally incapable of finding it.
```
  angle phase vs COMMAND   all 46: +46.8 deg [+29.4,+71.3] R=0.581, angle LAGS in 72 %
                     near-straight: +63.3 deg              R=0.740, angle LAGS in 85 %
                     1.0-1.6 Hz median lag +0.088 s  <- sits on steerActuatorDelay = 0.100 s
  angle phase vs DRIVER TORQUE   -63.2 deg [-88.1,-24.8]  => the HANDS REACT to the wheel
  car follows the wheel kinematically in EVERY event (yaw/prediction p50 1.17, range 0.73-1.61)
  engaged/manual angle PSD, speed-stratified, 0.4-3.5 Hz:  0.022-0.21  => engaged is 5-45x QUIETER
```
⇒ **[BELIEF, strongly supported] a limit cycle in openpilot's own lateral loop.** The EPS-originated
signature (angle leading command) is a **28 % minority** with the pooled CI excluding zero on the wrong
side, the car yaws with the wheel every time (excluding a column/rack torsional mode), and the driver's
hands lag. ⭐ **It explains why sixty firmware builds never moved it: there was never a firmware lever
on it.** 🛑 `feedback-no-openpilot-side-modifications` is standing — **the operator's call, not ours.**
🛑 **AND IT IS NOT THE GRINDING.** Inside events vs speed-matched engaged baseline: rail duty **1.01
[0.88, 1.22]**, audio 100 Hz–2 kHz **+0.50 dB [−1.18, +2.54]** against a control spread of [−6.2, +7.9].
**Two independent defects; V109 and any successor must target them separately.**
⚠ **The one thing that could change it:** manual exposure above 24 km/h on `1e` is **35.8 s total**, so
the >24 km/h rate ratios rest on 0–2 manual events and the stratified PSD only has cells at 6–36 km/h —
while **5 of the 13 near-straight events are at 39–76 km/h.** Closes with deliberate matched manual
segments at 50–80 km/h on the same road.
⭐ **METHOD LESSON:** a single wideband 0.4–3 Hz detector would have found **nothing** — at these
amplitudes a 0.45 Hz cornering input destroys the zero-crossings of a small 1.2 Hz limit cycle riding on
it. Five sub-bands found it. Controls passed first, including a **ringing control** (impulse/step/ramp
through every band filter, **zero spurious chains in 15 combinations**).

### ⭐⭐ V109 BUILT — `0xC40DC` (α2) 22 → 14. **GATE 1 AND GATE 2 BOTH CLOSED.**
```
V109 image  e9eb51fcad9ffc8768cd3e8eb601619d0f2acc0f702f01c4732243c70cc7f4d6
V109 .rwd   83047f0fd3b5b656720487d5f70755c3b2506c4293097b403abf003e972087c1
builder     analysis-2020accord/builds/v108_plus/build_v109_tva.py   30/30   BASE = V108
5 bytes vs V108 (1 payload + 4 CRC).  Cal-only.  Cave byte-identical.  UNCOMPENSATED.
```
**V109 = V108 + one cell.** α2 is the only axis of this lane nobody has ever touched — V106 changed its
MAGNITUDE, V107 its SPEED SCHEDULE, and both pay for any HF reduction **one-for-one at 21.7 Hz** because
Y is a flat multiplier. **Shape does not.** Uncompensated:
```
   f Hz     1      3    7.79  21.73    27     40    61.1   100    200    300
  ratio   1.000  0.998 0.988  0.920  0.888  0.816  0.732  0.657  0.607  0.596
```
⇒ **~0 % cost at manoeuvre frequencies, 1.2 % at the ratchet, 8.0 % at the mode (below the ~9 %
perceptual floor) — and 27–40 % cut across 61–300 Hz.** Phasor at 21.73 Hz = **222.77°**, safe sector.

**GATE 1 CLOSED — and the fan-out is FOUR consumers, not three.** Cell: one access image-wide, zero
writers (`disp|1`, 6-byte and register-indirect forms all checked). Signal: friction lane = the target ·
oscillation detector **SAFE and margin IMPROVES** (arms at 12800 vs a corpus max ~5,300; V64 flew 1,158
reversals with **zero arms**) · `FUN_00071272` writes a **36-byte-stride diagnostic log record** at
`gp-0x26e8`, not the torque path · `FUN_0007b022` has **four outputs with zero readers** and its fifth
(`gp-0x4f64`) is cleared by tracing **its own three producers**. `gp-0x6c2e`/`cal(0xC40DA)` = 3 are
**independent AT THE PRODUCER** — separate state, separate cal, separate shift — with disjoint reader
sets as a second reason.
🛑 **GATE 2's real cost: the 90–180° sector ENTRY slides DOWN 74.1 → 54.0 Hz.** That is why **V109 MUST
sit on a V108 base** — across 54–74.5 Hz V105's notch left the parallel lane a geometric-mean **5.15×
(+14.2 dB)** louder than Honda's, and V108 reverts it. **`build_v109_tva.py` ASSERTS the base.**
🛑 **Rail duty under this dose is NOT predictable** — the only method available was measured **32× wrong**
on this lane, the loop term is 14–16×, and α2 sits upstream of the distribution any solve would need.
**V109 is a deliberate single-variable experiment against V108**, and that two-point contrast is the only
thing that can size this cell. **Recommendation: fly V108 first**, so the contrast exists.

### ⭐⭐ THE HEADLINE — `gp-0x6b26` IS NOT A DAMPER ABOVE ~30 Hz, AND V107 MADE IT A RELAY
The lane is `64·H1·(1−z⁻¹)·H2` (EMAs α0 = 37/128 = `cal(0xC643C)`, α2 = 22/64 = `cal(0xC40DC)`) —
**a BANDPASS peaking at 61.1 Hz, −3 dB span 25.1→153.0 Hz, never below 4.49× to Nyquist.** At 100 Hz it
runs at **10.86×, 40 % MORE than at the 21.7 Hz mode it was meant to damp.** Two independent derivations.
V107's own re-aimed 427 tap then measured the consequence — `P(|gp-0x6b26| = 511)`, engaged, route `1e`,
episode-bootstrapped over 10 episodes:
```
   bin      V107 rail duty          V106 same samples      <10   1.68% vs 1.47% EXACT
   10-25   32.32% [29.93,35.68]     <= 15.46%            40-64   4.27% vs <= 3.43%
   24-40   21.27% [19.93,22.51]     <= 10.45%             >=65   <= 0.23% / <= 0.03% BOTH
```
**V107's own builder predicted ≤1.05 % everywhere and REJECTED its alternative at 6.2 % as "V80 relay
territory".** A railed acceleration term is `sign(α)·511` — a bang-bang Coulomb relay, V80's exact
mechanism. 🛑 **The safety case could not see it: CAN 427 arrives at 49.8 Hz (Nyquist 24.9), and the
lane's entire −3 dB band is above that.**
🛑 **REFINED 2026-08-27 — that framing is right about SPECTRA and WRONG about DUTY.** Rail duty is
`P(|c2c| ≥ thr(v))`, a functional of the **MARGINAL** distribution; the 427 tap samples instantaneous
values, so its marginal is **UNBIASED** and only its SPECTRUM is aliased. **The measured duties are
sound.** What the 49.8 Hz tap genuinely cannot do is see the **25–153 Hz band the lever ACTS ON** —
which is why an α2 dose cannot be sized from it, and why **V107's error was a MODELLING error (an
open-loop push-through applied to a closed loop), not an instrument error.**
The rail threshold shrank **1.42–2.71×** across 24–90 km/h
while **Y[0] stayed byte-identical below 20 km/h** — and the operator reports grinding at 15–40 mph and
none below 5–6 mph. **The symptom map and the rail-duty map are the same map.**

### ⭐ "IT PERSISTS AFTER DISENGAGE" — MEASURED AT ~2.05 s, AND IT IS OURS
Mode records 26/27 are held until `gp-0x69b0` ramps to exactly 0 (`FUN_00028ea6`, 1 kHz, five rates =
100/497/993/**2048** ms + a ~40 ms commit hold). Wire-saturation duty is **zero from +2.0 s onward**;
last railed sample 1.81 / 0.85 / 0.40 s. **Pre-registered: 0.10/0.50/0.99 EXCLUDED, 2.05 CONSISTENT.**
Both controls passed — two of three transitions SPEED UP and still go to zero, and at matched steering
rate post-disengage `|c2c|` p50 = 72 with **0.00 %** rail duty against engaged p50 = 1080 and **20.43 %**.

🛑 **CORRECTED 2026-08-27 — `gp-0x69b0` IS A Q15 MULTIPLIER, NOT A GATE, SO THE RELEASE IS A CROSSFADE.**
An earlier census over its 45 accesses found **zero `mul` instructions** and concluded "gate". That does
not follow: **the multiply's operand is a REGISTER loaded ~2,700 bytes earlier**, and an operand-text
search over accesses to a symbol finds loads and stores but cannot see what is done with the value —
the same blind spot `CLAUDE.md` already records for register-indirect writes.
**The multiply is `0x2A1E6  mul r14,r9,r0`, then `0x2A1EA sar 0xf,r9`, `0x2A1EC sxh r9`** ⇒
`LKAS_lane = sxh((lane × gp-0x69b0) >> 15)`. Register liveness proved mechanically: all 41 accesses to
`gp-0x69b0` sit in `0x2936A`–`0x2972A`, every read is `ld.hu …,r14`, and **`r14` is never written across
the 1015 instructions between the state machine's exit at `0x29734` and the multiply** (the only
instruction with `r14` last is `0x29A48 cmp r0,r14`, PSW-only), with **zero `jarl`/`callt`/`trap`** in
that span so no callee can clobber it.
⊕ **The sign objection dissolves too**: the cell is *stored* with `st.h` but *read exclusively* with
`ld.hu`, and the SM saturates it at `0x8000` (`0x29490 ori 0x8000,r0,r14`). 32768 does not fit a signed
int16, so it stores as −32768 and reads back as **+32768 unsigned** — "signed, resting at 0/−32768" is
exactly what an unsigned Q15 0…32768 looks like in a raw halfword dump. **Range 0.000–1.000.**
⇒ **During the ~2.05 s tail there IS a decaying LKAS command while the engaged-only damper is still in
force** — a crossfade, not a hold-then-snap. The measured 2.05 s release stands unchanged; what changes
is what the car is doing during it.

### ⭐ THE 2×2 — THE RELAY IS MOSTLY PLANT, AND A 32× MISS IS EXPLAINED
Holding Y fixed, **engaged `|c2c|` alone gives 27× the rail duty of manual `|c2c|` at 10–25 km/h.**
`gp-0x6b26` feeds aggregator → motor → motor rate → `gp-0x6c2c`: **it is a closed loop**, so V107's
open-loop push-through (which assumes the input distribution is invariant to K) was **32× wrong**.
Reached independently from the code and from the data. 🛑 **No open-loop duty prediction on this lane
can be trusted again.**

### ⭐⭐ THE CLOSED-LOOP TERM IS NOW MEASURED — 14-16x, AND IT IS THE SAME MAP AS THE SYMPTOM
Median `|gp-0x6c2c|` engaged vs manual, matched speed, within route `1e`:
```
   <10 km/h    62.4 vs 22.4  =  2.79x     (n = 6248 / 20044)
   10-25      974.4 vs 60.8  = 16.03x     (n = 14950 / 3921)
   24-40      860.8 vs 52.8  = 16.30x     (n = 15483 / 2679)
   40-64      560.0 vs 40.0  = 14.00x     (n = 30250 /  896)
```
⇒ **~94 % of the engaged acceleration signal is LOOP-GENERATED.** [EVIDENCE for the ratio; BELIEF that
it is all loop — engagement also adds LKAS excitation, so 14-16x bounds the loop term ABOVE.]
⭐ **2.79x below 10 km/h against 14-16x above it is the SAME MAP as the operator's "grinding at 15-40 mph,
none below 5-6 mph" and the SAME MAP as the rail duty.** Three independent quantities, one shape.

### ⭐ V108's OWN PREDICTION — the first quantified one this kit has made, and its method is held out
An exact-integer reimplementation of the cascade, run per-sample over route `1e`, **reproduces the
MEASURED rail duty on all five speed bins with nothing fitted**: 1.60 vs 1.68 · 33.52 vs 32.32 ·
21.15 vs 21.27 · 5.19 vs 4.27 · [0.00,0.16] vs <=0.23 %. **HELD OUT on route `1b` — a different drive,
same build — 33.76 % at 10-25 km/h against `1e`'s 33.52 %.**
⇒ **V108's Y-row change alone is predicted to take 10-25 km/h rail duty from V107's measured 33.52 % to
7.0-15.4 %** — roughly halving the relay duty. ⚠ Route `1b` also gives 31.88 % at 24-40 against `1e`'s
21.15 % and 21.72 % at 40-64 against 5.19 %: **duty is strongly driving-dependent above 25 km/h.**
🛑 **A CLOSED-LOOP SIMULATOR IS NOT AVAILABLE AND THE REASON IS STRUCTURAL.** The identified column model
(`J_w` = 1.248, `b_w` = 35.8, corner 4.57 Hz) has a **measured validity band of 5-13 Hz**, while the lane
peaks at 61.1 Hz with a -3 dB span of 25.1-153.0 Hz ⇒ **100 % of the lane's band, and its peak, lie above
the plant's ceiling**, and above 13 Hz `|Z|/w` collapses 1.33 -> 0.45 for reasons the record itself
records as unresolved (real plant, or an internal low-pass in the torque channel). `ClosedLoopSim` is
implemented in `analysis-2020accord/model/eps_closed_loop_sim.py` and **refuses to run without
`allow_extrapolation=True`; no number in this block came from it.**

### 🛑 THE GHIDRA EMULATOR CANNOT VALIDATE THIS ARITHMETIC — three doors, three distinct reasons
1. `emulate_function` is **hardcoded x86** — fails `"Undefined register: ESP"` on every V850 call
   regardless of arguments; `V850:LE:32:default` has no ESP and nothing aliased to it. Server-side fix:
   take the SP from `getDefaultCompilerSpec().getStackPointer()`. `emulate_hash_batch` shares the defect.
2. `run_script_inline` is gated behind **`GHIDRA_MCP_ALLOW_SCRIPTS=1`**. Ghidra's own `EmulatorHelper`
   IS language-agnostic and would work; that env var is the whole blocker.
3. 🛑 **NEW — `get_function_pcode` is structurally insufficient to emulate from, and would have produced
   a confident WRONG answer.** No block out-edges, and the decompiler's condition-normalisation flips
   conditions while swapping edges (at `0x36C38`/`0x36CCE`/`0x36CEE` the inverted sense is right, at
   `0x36C48` the non-inverted sense is right) ⇒ **polarity is unrecoverable**; and **SSA varnodes collapse
   onto one `(space,offset)` key** (`u30300` is reused by the loads at `0x36C94`/`98`/`9C`).
⇒ **The arithmetic is validated instead by THREE NON-EXECUTION METHODS THAT AGREE** — decompile,
assembly, and the p-code IR — and the kit's mirrors are CORRECT. Confirmed at IR level: `INT_SEXT`x2 ->
`INT_MULT` -> `INT_SRIGHT #6` (arithmetic) -> `INT_MULT #111` -> `INT_SRIGHT #12` (arithmetic).
⊕ **Exact rail thresholds are 1063 / 1306 / 1959 ct** at 0/20/90 km/h — `sar` FLOORS, so the clamp is
reached ~0.2 % earlier than the closed form's 1064.9/1308.5/1962.7.
⊕ **The LERP divide is `INT_SDIV` (truncates toward zero), not floor** — identical for today's monotone
Y rows, but **a non-monotone Y row would make a floor-division mirror off by one.**
⊕ 🛑 **An unpriced nonlinearity: the `d32` clamp (±0xFA0000) saturates the lane** above an input of
~10,320 ct @7.79 Hz, 3,944 @21.7, 1,961 @61.1, 1,668 @100. Above it the lane delivers 8-32 % of `|H|`.
**The kit's whole alpha2 sweep table is a linear-`|H|` calculation.** Safe for the railing question
(railing needs only ~88 ct of input at 61 Hz) but **NOT safe for broadband claims.**

### 🛑 E3 WAS BUILT AND PULLED — the pre-registration was honoured
`0xC61BE` = 15360 is UPSTREAM of the 6× gain, so the lane's reach is `(clip × gain) >> 15` and has been
**81.5 % of its own output clamp on EVERY build since V14** — which is also why `0xC61B2`/`0xC61B4`
measured "0 % of the effect": **they are inert BECAUSE this clip caps the lane 18.5 % below them.**
Anchored two ways (`(15360×891)>>15 = 417` = the recorded stock V9 maximum). But the knee test on route
`1e` (93,356 frames / 924 s, `|e4tq|` p99 = max = 4096) shows **achieved rate still rising 2.1–3.9× at
the top of the command range at all five speeds, every CI excluding 1.0** ⇒ **the clip is IDLE and the
raise buys zero. PULLED.** ⚠ Not proof it can never bind — the clipped quantity carries int32 recursive
state (`gp-0x6cf8`, `gp-0x6dd0`), so it is also **not reconstructible from logs.**
⭐ Zero-firmware confirmation exists if ever wanted: **stock UDS DID `0x48AC` bytes 7–8 = `gp-0x6b38`**
(RDBI entry `0xB7864`, no security access); a bound clip pins it at ~2481, and **anything above 2505
falsifies the model.** Blocker on record: EPS UDS is bus-1 + OBD-mux only. **Nothing was transmitted.**

### 🛑 V109's LEVER IS ALREADY PRICED AND GATED — `0xC40DC` (α2), VIRGIN ON ALL 102 IMAGES
At K2 = 14 the delivered response is **FLAT across 18–30 Hz (1.024→0.966) and cuts 20–35 % over
61–300 Hz** — it de-rails **without giving back one count of mode-band damping**, which lowering Y cannot
do (Y is a flat multiplier). GATE 1 on the cell is the cleanest possible (exactly ONE gp/tp access
image-wide, zero writers, `disp|1` trap handled); GATE 2 at the mode is clean to K2 = 3.
**HELD OUT of V108 for three reasons:** the sector entry moves **DOWN** (74.1 → 54.0 Hz), `gp-0x6c2c`
fans out to **three** consumers of which two are unverified against a *reshaped* signal, and the only
available duty-prediction method was just measured 32× wrong.
🛑🛑 **AND IT MUST SHIP WITH THE NOTCH REVERT OR NOT AT ALL**: across 54–74.5 Hz V105's coefficients
leave the base-assist lane a geometric-mean **5.15× (+14.2 dB)** louder than Honda's, 21.8× at the
sector's new entry point. V108 ships E1, so the prerequisite will be on the car.
⊕ Take it **uncompensated** — the int16 boundary is exact: `29490 × 1/0.90 = 32,767` against a floor of
32,768, so a **−10 % α2 cut is the LAST one Y[0] can compensate.**

### 🛑 THE INSTRUMENT LESSONS
**CAN 427 is 49.8 Hz, not 100** (Nyquist 24.9) — no spectral claim can come off it. **The between-drive
audio contrast is PERMANENTLY unavailable** — the parked, engine-on cabin differs **3–12×** between
drives and no openpilot-version finding touches that; route `1e` has 35.4 s of matched manual inside the
grinding window, so within-drive is available and strictly better. **The device was reflashed** — the
route counter reset (`a6` → `1b`/`1e`) and **`0000001b` exists TWICE on disk with different hashes**;
key every cache on `counter--hash`, and never assume low route number = old build.
✅ **The a6-vs-1e confound is CLOSED for the CAN channels** (one openpilot commit `7c6741a9`→`36d0c074`,
AGNOS unchanged at 19.6.2, every lateral CarParams field identical).
🛑 **The whole extractor family was DEAD** (`ModuleNotFoundError: _grind2_lib`) because the 2026-08-26
reorg moved a module into `lib/` while the `PATH BOOTSTRAP` block stops at the FIRST `.pkgroot`.
**FIXED in 729 files** — it now walks every `.pkgroot` root in the repo, nearest first.

### 🛑 SIXTEEN RETRACTIONS THIS SESSION — the four that change what anyone should do
1. **`0xC520C` STRUCK as a lever** (retracted by its own author). Peak `gp-0x6ac0` = 1462 ct against a
   first knot at 1050, reached **0.11 % of engaged time, never past the second**; `gp-0x4f64` sits at its
   max 4762 for **99.9 %+** of engaged time. Reconciles `b6` = 0.000000 and explains V41's null.
   **Stands as a documented mechanism, not a lever.**
2. **`0xC64DE` is NOT a "re-engage ramp"** — it is the **half-period of a sign-flipping square wave**;
   V18 moved it **29.41 → 18.52 Hz, into grind #1's band**; burst ~381 ms; **amplitude LERP is all zeros
   ⇒ structurally INERT.** ⚠ A latent 18.5 Hz injector into the 6× path, four halfwords from live.
3. **`accord-4x-lkas-gain-is-the-frozen-variable` is STALE** — 4× only through V100, **8× on V101, 6×
   since V102** (`0xC6CD0` = 5346 = exactly 6.000×; 891 = 1×).
4. **`gp-0x4f62` "peaks at 125 Hz" DOES NOT FOLLOW FROM THE CODE** — ring buffer + variable tick weights
   + a conditional call; the effective delay is unresolved. **Do not reuse 125 Hz.**
⊕ Also: the `0xE4`/`0xE5` "skip" is **the selector-reachability complement, not a bug** (our car is
TVCA4 → slot 11 → selector 7 → `0xE51A8`, **raised**; V74's slot naming is right and V38's is wrong);
*"`H(0)=0` ⇒ cannot rate-limit"* is **VOID once the term rails** (a railed term is 10.7 % of governor
authority as constant DC drag through the whole acceleration phase); *"gp-0x6b26 can never raise a
resonance"* was only ever checked **to 40 Hz** — above **74.5 Hz** the phasor sits in the
resonance-raising sector continuously to Nyquist; and the *"16384 makes the two ceilings agree"* framing
is **VOID** (the E4/E5 taper clamps `gp-0x69ae`, bounded at ±16384 by STEER_MAX = 4096 **by
construction**, so V38's edit was correct and complete and there was no miss).

### THE DRIVE CARD FOR V108 — in the handoff §3
**Primary: the operator's report per scenario.** Then rail duty by speed bin off the uncensored `sar 5`
tap · `|gp-0x6c2c|` at ≥70 km/h (V107's item #2, still unanswered) · 18–30 Hz prominence against a6 as
**E1's risk readout** (V105's flight run backwards predicts ×1.30 [0.88, 1.82], a CI spanning 1) · a
**within-drive** third-octave audio split at 45–130 Hz, which **falsifies E1's HF case if it comes back
flat and broadband above 200 Hz** · `b5` at matched α · fault-free confirmation.
🛑 **AND THE TOP NON-BUILD ITEM, now with a new requirement: the alternating drive PLUS deliberate
disengagements at CONSTANT speed, throttle held ~15 s.** The operator disengaged three times on `1e` and
changed speed every time (−13.6, −6.1, **+10.7** km/h) — natural driving, fatal to the measurement.

---

## ⚠ SUPERSEDED BLOCK, 2026-08-23 — **V106 FLEW AND EXTINGUISHED THE MODE AT LOW SPEED · RULE 7 CLOSED · THE UNIFORM DOSE AXIS IS EXHAUSTED · V107 RESHAPES THE SCHEDULE**

🛑 **ON THE CAR: V106** (route `a6`, 1,224.0 s engaged, fault-free).
**V107 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-23-v107-the-schedule-is-the-lever.md`** — drive card, 13 retractions,
6 record defects, 14 open items with what closes each.
```
V107 image  c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45
V107 .rwd   78eae7da20a87f1a95295eca11da0d08f4cf2b3b823785594cde4be93a7b24ff
builder     analysis-2020accord/builds/v80_v107/build_v107_tva.py   55/55 assertions   BASE = V106
E1  0xD7A5C / 0xD7A6C   (-29490,-17202,-5898) -> (-29490,-24000,-16000)   modes 26/27, X untouched
E2  0x55DF2  7a 94 -> d4 93   427 tap: gp-0x6b86 -> gp-0x6c2c
    0x55E10  a4 -> a3         sar 4 -> sar 3
```

### ⭐ THE HEADLINE — V106 EXTINGUISHED THE 21–27 Hz MODE AT LOW SPEED
Engaged, <16 km/h, max-demand arm: prominence **1.51 against STOCK's 1.46**, and V106's argmax
**follows the search-band edge exactly as stock's does** while V104's and V105's stay pinned. Two
independent within-spectrum signatures of no line present.
**`18-30 a6/V105 = 0.347` CLEARS route a6's own within-drive split-half null [0.482, 1.982] — the
FIRST band-power result in this kit's history to do so.** Positive control `a6/STOCK = 5.735`.
🛑 The confound was cut: a6's engaged command is ~4× SMALLER than a5's, so the result was re-run in
matched (speed × **absolute** demand) cells and survives.

**Operator's report:** grinding attenuated in all three scenarios; ratcheting still present at high
LKAS demand; max LKAS-driven steering rate limited; LKAS-off feel normal.

### ⭐ RULE 7 IS CLOSED — the car reads modes 26/27 engaged
`b5` at **matched α** (a pooled duty is the WRONG estimator — the K·α product is invariant to K):
a6/a5 ratio **8/8 bins below 1, sign p = 0.0039**; within-drive engaged 0.1907 vs MANUAL 0.4509.
The ×1.5 WAS in force: delivered multiplier **1.68× [1.16, 1.88]**, excluding both 1.00 and 3.00.

### 🛑 WHAT SURVIVES, AND WHY V107 IS A RESHAPE
Residual is a ~27 Hz line **above ~70 km/h** (55–70 is measured AT STOCK: 1.4 vs 1.6). That is exactly
where Honda's taper makes V106 **4.2× weaker** (−24,546 at creep vs −5,898 at ≥90 km/h).
**The uniform axis is int16-EXHAUSTED:** Y[0] stock −9830 ⇒ k_max **3.3335**, V106 at ×3.0 = **90 %**
of the floor. ×4/×5/×6 are OVERFLOW. **Y[2] has ×5.56 of room and that is where the line is.**
RESHAPE B holds Y[0] byte-identical ⇒ creep clamp duty and relay index unchanged BY CONSTRUCTION.
A flat schedule was REJECTED: **6.2 % clamp duty at 70–90 km/h = V80 relay territory**, against B's
≤1.05 %. And **route a6 spent 809 of its 1,224 engaged seconds above 70 km/h.**

### THE RATE COST IS AN ACCELERATION PENALTY, NOT A SLEW CEILING
No rail · steady state restored to V104's level (`H(0)=0` predicts it) · wheel acceleration down
2–4×. At matched ABSOLUTE max demand, achieved rate p90: V88 326 · V104 166 · V105 229 · **V106 157**
⇒ **~30 % of peak rate given up vs V105.**

### THE RATCHET IS LKAS-DEMAND-DRIVEN — the next target, and a NEW discriminator
The 7.4–8.6 Hz LINE is the **only** band with a positive residual demand association after
partialling out motor rate (+0.1139 [+0.0374,+0.2548]); carrier and placebo go negative. 2/2 rate
strata, both CIs excluding 1, placebo flat.

### ⭐ THE ARCHITECTURAL ANSWER — the feedforward lane EXISTS
`0xC4124[1]` 0→5 moves LKAS to Honda's own post-governor lane; four channels already use it. Both
cal tables **0 writers**; the ASIL monitor dispatches on the same byte ⇒ follows by construction; the
authority gate is UPSTREAM of the router. **Topology change, NOT authority — it does NOT buy back
steering rate** (the damper subtracts at the FINAL add, downstream of both lanes). **V108 candidate.**

### 🛑 RECORD DEFECTS FOUND — reported, deliberately NOT silently patched
1. **Golden model `assist_polarity = 1`** where `gp-0x6752` is **−1**; nothing overrides it, so every
   `_demo()`/`_self_check()` run uses the pre-retraction sign. **NOT fixed** — `_self_check()`'s
   expectations were computed at +1, and editing them to match the model's new output would make the
   test agree with the code by construction. Defect note in place; **contract re-verified intact
   (2,512 B, `740f4bcd…`)**.
2. **V100 FLEW as route `0x85`** (2026-08-13); `BUILD-LINEAGE-CATCHUP-V76-V100.md` still says "BUILT
   AND NOT FLASHED" — the eleventh stale flight-status row, by that row's own warning. ⭐ **And V100
   carried the `|gp-0x6ad6| ≥ 8192` rail comparator — 🛑 **and this file's claim that its duty was NEVER HARVESTED is FALSE. It was harvested 2026-08-14 and re-run 2026-08-27: d(b5) = 0.000000 over 24,925 engaged frames, gate proven live by `b4` on the same cell at duty 0.6057. The dose is MERELY SMALL, not structurally zero — K1 = 204 IS delivered.** — it decides
   whether `0xC40D2`'s dose is small or structurally ZERO.
3. `accord-gp6b4c-is-an-11-slot-assist-sum` — modes 5/7 **re-route**, they do not zero.
4. `accord-friction-polarity-*` — conclusion stands, sign chain **replaced** (frame crossings).
5. `MEMORY.md` pointed at a file renamed after the operator retracted its claim (**"v84 fixed the
   highway ring"** → `accord/builds/accord-v84-flew-and-fixed-nothing.md`). **Fixed.**

### 🛑 THE INSTRUMENT LESSON — a STATIONARY mode returns a FAKE frequency slope
Injected at an amplitude ladder through the same argmax pipeline, a mode that does **not** move
returns **−1.14 / −0.759 / +1.731 Hz per e-fold** when the amplitude axis is INDEPENDENT of the band
power, with the sign tracking (band centre − mode frequency). Against band RMS the floor is **zero**.
⇒ **`accord-f0-crossover-is-the-endpoint`'s −1.93 Hz/e-fold was measured against COMMAND amplitude and
sits inside that artefact's range.** NOT retracted (`f0` is a `Re(Z)` crossing, not an argmax) — but
**push a stationary synthetic through the actual `Re(Z)` code before it sizes anything.** OPEN.

### 🛑 THE TOP NON-BUILD ITEM — THE ALTERNATING DRIVE, open since the V105 handoff
~30 s engaged / 30 s manual at 5–15 km/h, same road, same session, command swept hard and soft. It
closes the ~8 Hz LINE null (a6 had only **7** engaged episodes, one of them 941.6 s), the <16 km/h
pitch-vs-amplitude cell (30 and 46 windows), and the engaged/manual contrast above 25 km/h (a6 has
**0.0 s** of manual driving in 25–60 km/h).

---

## ⚠ SUPERSEDED BLOCK, 2026-08-22 — V105 flew and relocated the mode · the three grinds are one frequency · V106 is a damper

🛑 **ON THE CAR: V105** (route `a5`, verified from the wire — three legs, strongest being the biquad's own
427 output matching the image floats). **V106 BUILT, VERIFIED, UNFLASHED. Nothing flashed, no CAN, no UDS.**
Narrative: **`docs/handoffs/2026-08/HANDOFF-2026-08-22-v106-the-damper-and-the-one-mode.md`** — the full drive card with
**nine numbered open questions**, 21 retractions, 20 open items with what closes each.
```
V106 image  78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a
V106 .rwd   e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc
builder     analysis-2020accord/builds/v80_v107/build_v106_tva.py   50/50 assertions
```

### 🛑 THE OPERATOR CORRECTED THE KIT TWICE AND WAS RIGHT TWICE
1. **"All 3 grinds are the same frequencies, under different scenarios."** CONFIRMED. Peak-searched
   **15–48 Hz**, stratified by HIS scenarios: S1 (<10 km/h) / S2 (hard manual turns under LKAS) / S3
   (highway) **all peak at 21–27 Hz**, and **38–48 Hz prominence is 0.3–4.9 (≈ baseline) in all 21
   build×scenario cells.** 🛑 **The kit's "grind #2 = 44.9 Hz Q≈37, NOT a harmonic" and "grind #3 ≈ 46 Hz"
   are NOT REPRODUCED.** Restate as three CONDITIONS of one mode. ⚠ Ceiling: `0x18F` Nyquist is 50.57 Hz,
   so nothing above ~50 Hz is observable at all; the harmonic test is **not runnable at highway**
   (2 × 25–27 = 50–54 Hz).
2. **"Why don't we put telemetry on the mode?"** — he found a four-build hole. **The mode record has NEVER
   been directly telemetered.** V93 was built as a discriminator (via dose-ratio inference) and never
   flew; `accord-cbe74-dose-measured-inert-wrong-mode-record` names it as the suspect for V91/V92.
   **V106 closes RULE 7 at zero cost — see below.**
⊕ **And a corpus claim is re-attributed: "applying torque kills the buzz" is really "applying RATE kills
the buzz."** At `|tq| ≥ 1000` with no rate condition the mode is fully present (PSD 51.7); adding
`rate ≥ 40 °/s` extinguishes it. Same drive, same channel, only the mask differs.

### ⭐⭐ V105 SCORED — THE NOTCH WAS AIMED AT EMPTY SPECTRUM, AND THE MODE RELOCATED
**On V104 only 1.2 % of the engaged <16 km/h 18–30 Hz POWER sat inside V105's own stopband.** A perfect
25.5 Hz notch could have removed at most that. **The mode is at 21.7–22.9 Hz**; the two estimates that
named 25.5 are discredited (`a4`'s peak regression had **R² = 0.039**; `f0` is a `Re(Z)` zero-crossing,
never the spectral peak).
```
                 peak Hz     shift            |H_V105| at its OWN peak    18-30 band power
<16 km/h  V104    22.73                              0.3039
          V105    20.48    -2.25 [-2.50,-0.50]       0.5442  <- 1.79x     0.769 [0.548,1.135]
55-70 km/h V104   25.97                              0.0467              (CI SPANS 1)
          V105    27.47    +1.50 [+0.50,+2.50]       0.1795  <- 3.84x
```
🛑 **The mode moved to where the notch costs it LESS, with band power CONSERVED.** That is a
describing-function intersection sliding, not attenuation. ⇒ **filtering is structurally the wrong tool.**

### 🛑🛑 ROUTE `a5` CANNOT RESOLVE V105 FROM V104 ON ANY BAND — the standing limit
Within-drive split-half null spans **0.26–3.8**. 18–30 Hz reads 0.410 [0.240, 0.688] — **inside it.**
Two pipelines independently reported narrow-band "cuts" (0.348 and 0.343) and **both authors withdrew
them** as band placement: 18–22 goes UP 30 % while 20.5–23 goes DOWN 65 %, because the mode moved.
⇒ **No V105-vs-V104 band-power ratio is resolved.** What survives is everything that is not a cross-drive
ratio: peak location and shift, `|H|`-at-own-peak, the 427-lane shape, the grind-#1 centre, cave duties.
⭐ **THE TRANSFERABLE LESSON: on this corpus, design the statistic to live INSIDE a drive.**

### ⭐ THE RATCHET IS A SEPARATE, GAIN-DRIVEN ~8 Hz LINE THAT DOES NOT EXIST ON STOCK
Pre-registered split of 6–12 Hz into a **LINE (7.4–8.6 Hz)** and a **FLOOR**, replicated on two statistics:
```
                      median E (6x vs stock)   4-dose ladder beta (1x/4x/6x/8x)
LINE                       +1.559                   +1.525  => E_line  +1.136
FLOOR                      +0.256                   +0.693  => E_floor +0.300
CARRIER 21-28                  -                    +1.390
CTRL 32-38 (placebo)           -                    +0.395
```
🛑 **On STOCK the line power is EXACTLY ZERO in 3 of 4 highway cells.** `E_line` centred **above 1** — a
by-product cannot outgrow its source ⇒ the line is a **SIBLING** of the carrier, not a demodulation
(AM bounded at **m < 0.05**; measured 6–12 Hz RMS is **~75×** the entire demodulation budget).
⇒ **`E = 0.406` "partial coupling" was a MIXING ARTEFACT, and every 6–9 Hz band-RMS number in this kit's
history dilutes the real effect by 2–3× by pooling line and floor.**
⊕ **H3 (governor-ceiling dropout) RETIRED** by two independent channels: `v105_b6` = **0.000000 across
65,959 frames**, and the reconstructed peak-follower never reaches the 223 °/s knee on five routes.

### V106 — 12 BYTES, PURE CAL, AND IT PROVES ITS OWN PREMISE
```
0xD7A5C  mode 26 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)
0xD7A6C  mode 27 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)   = x3.0 stock
```
`gp-0x6b26 = -K·angular_acceleration`. **The only lever with a signed on-car precedent pointing this way**
(V93/V94 lowered it and the operator aborted the drive as unsafe). **Damping removes a DF intersection;
a notch relocates it.** Reaches **both** bands — gain **1.478 @ 7.79 Hz**, **3.706 @ 21.73 Hz**.
🛑 **`H(f=0) = 0` EXACTLY** — the differencer `32·(1−z⁻¹)` is identically zero at DC for any `a1/a2/K`, so
**it cannot rate-limit a held 6× command at any multiplier.** A proof, not a measurement.
⭐ **MODE PROOF AT ZERO COST:** the carried cave rung **`b5` = ( |gp-0x6ae2| ≥ |gp-0x6b26| )** — operand B
at `0xC4B70` = `da94` = `-0x6b26`, **the exact cell dosed**. Engaged duty must collapse from its **0.4019**
baseline if the car reads 26/27 engaged; unchanged confirms the V91/V92 suspicion. **MANUAL is the
built-in control.** **RULE 7 closed either way.**
🛑 **26/27 ONLY.** The family has **FOUR** members (`builds/v80_v107/build_v100_tva.py`'s `DOSE_FAMILY_Y` lists three;
`builds/v80_v107/build_v105_tva.py` already had four): mode 24 = **MANUAL** (dosing it is inert for an engaged symptom and
changes manual feel), mode 25 = **role unconfirmed** (V69/V70 trap class). Both left at stock.
**`0xC407E` untouched at 511** — one count under its own 512 trip, so the RULE-11 interlock is intact **by
construction, not by care** (V73 raised a different clamp past its trip; V74/V75 both faulted mid-drive).

### 🛑 WHAT V106's LOGS MUST ANSWER — the drive card, in the handoff §5
**Q1 `b5` duty (the mode proof — outranks the symptom score) · Q2 clamp duty by rate bin (predicted ~1 %
in S1, ~0.06 % in S2 — clipping, if any, appears in grind #1's scenario, 26× more than in #2) · Q3 peak
LOCATION + the WIDEST band (damping predicts frequency unchanged, PSD down; if it MOVES again that is a
new result) · Q4 the ~8 Hz LINE scored separately from the FLOOR · Q5 the operator's report per scenario,
the PRIMARY readout · Q6 does the wheel feel heavier in fast turns · Q7 was the ×1.5 ever in force ·
Q8 housekeeping rungs · Q9 exposure.**

### ⚠ CORRECTIONS TO CARRY (the orchestrator's own, all four)
1. **"The high-rate cost is zero"** — RETRACTED. On the wire `|gp-0x6b26|` **peaks at 40–100 °/s and
   collapses above 100**; MAX at 200–400 °/s is **104 counts**, not the 543 predicted (5.2× over). ⇒ the
   raise **arrives in full at high rate — a real added opposition, not free** — but by the same token it
   **arrives in scenario 2 too**, so V106 can reach grind #2.
2. **"Dose all three modes symmetrically"** — WRONG; mode 24 is manual.
3. **"The 21–28 Hz ↔ grinding tie is inherited"** — the operator corrected it and the ladder confirms him.
4. **"V105 delivered −24.1 dB and he felt nothing"** — that was `|H|` at 24.9 Hz. At the mode it is
   **−7.6 dB**. The honest statement is *"~8 dB and he felt nothing."*

### ⭐ THE ARCHITECTURAL RESULT — the operator's own framing is reachable, and step 1 is telemetry
`FUN_0003a382` forms **`iVar30 = gp-0x4f60 − reference`** — raw torsion bar. **MODEL feeds the REFERENCE
side, never the MEASUREMENT side** ⇒ *"already doing this, and doing it badly"*. ⭐ **And it self-cancels
at DC by construction:** Stage-1 gives `d(iVar6)/d(gp-0x6b4c) = +2.578`, MODEL gives **−2.578** (identical
`polarity` and `0xC6468`, Stage-1's ×16/>>4 a designed no-op), and REQUEST is a **hard-coded zero**.
🛑 **The DC/mean-shift mechanism is CLOSED AT NULL; the AC/DF question at 18–28 Hz is OPEN.**
🛑 **`0xC6CD0` is EXOGENOUS by Mason's gain formula** — a source node never enters `Δ(z) = 1 − ΣL(z)`.
**There is no "move the gain outside the loop" to perform.**
🛑 **THE CAVE RISK MODEL WAS WRONG:** `0x3AC78` is a **task-1, 1 kHz trampoline inside the aggregator that
FLEW CLEAN on V39**, and V48B's own postmortem **exonerates the clock rate**. Corrected: *a task-1
trampoline is proven; a STATEFUL filter allocating NEW RAM into a live path is not.*
⊕ **Telemetry ceiling fully mapped: only 3 IDs cross the gateway — `0x14A` 0 free bits, `0x18F` 10,
`0x1AB` 5. Fifteen, permanently.** A byte-exact `|gp-0x6b26|`+sign spec exists for `0x18F` (hook `0x55D50`,
byte-stock on every build; 1048 free cave bytes at `0xC4BD8`) — `[0,511]` is **exactly 9 bits + sign**.
**Not shipped on V106**: the stub is an instruction-level spec, not assembled bytes.

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
  builder analysis-2020accord/builds/v80_v107/build_v98_tva.py   199/199   BASE = V97 (on the car)
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
   **0.0000**. S1/S2 **VOID** — conceded in `builds/v80_v107/build_v97_tva.py:99-100` **before the flash**.
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
**`docs/archive/STATE-ARCHIVE-pre-V89.md`** (432 KB) by `analysis-2020accord/archive/shrink_state_md.py`; the
2026-08-11 V90-flight headline went to **`docs/archive/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`**
(30 KB) at the 2026-08-12 close-out; **the V96/V94/routes-78-79/V88 flight headlines went to
`docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`** (54 KB) by `analysis-2020accord/archive/shrink_state_md_2026_08_13.py`
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

## → ARCHIVED 2026-08-27 — the V103→V107 superseded blocks
The six dated blocks for the **V103–V107** sessions (2026-08-13 final, 08-20 late, 08-21 early,
08-21 late, 08-22 early, 08-22 late) now live in
**`docs/archive/STATE-ARCHIVE-2026-08-27-v103-to-v107.md`** — verbatim, nothing edited.
V107’s and V106’s blocks are KEPT inline below, as the two most recent predecessor states.
⚠ They are a record, not an instruction, and their “on the car” lines are stale.

## → ARCHIVED SECTIONS — moved out 2026-08-21
Everything from *"ARCHIVED 2026-08-13 — V96's flight headline"* onward now lives in
**`docs/archive/STATE-ARCHIVE-2026-08-21-pre-v104.md`** — verbatim, nothing edited. That file holds the
archived flight headlines, the **STANDING CORPUS RESULTS**, the **STANDING INSTRUMENT CORRECTIONS**,
the methodology + signal-identity corrections, the tyre line, and the superseded on-the-car block.
🛑 **The instrument corrections and corpus results are still LOAD-BEARING — read that file before
any analysis session.**
