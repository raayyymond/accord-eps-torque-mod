# HANDOFF 2026-08-09 (latest) — V88 flew, the fork closed, and the highway finally arrived

**Session shape:** orchestrator + three subagents (`r73-extract`, `r73-score`, `lever-hf`).
**Deliverables:** route `73` extracted and scored · V88 identity confirmed three ways · **H1 confirmed
and the operator's constraint met by measurement** · **H2's fork CLOSED without the rectification
screen** · the first engaged highway exposure in the corpus · a kit-wide instrument defect found ·
four firmware levers killed on structure · the README trimmed as asked.

---

## 1. What the operator asked

> *"I added a route driven on the V88 firmware. The audible grinding is fixed, I noticed maybe some hints
> of grind #2, but wasn't able to elicit it out. So grind #1 is fixed without introducing grind #2 (for
> now). Micro-ratcheting and ratcheting (stuttering) is now the main remaining issues. We need to address
> these issues without dampening the peak effective LKAS steer command (< a few Hz)."*
>
> *"Oh yeah, in the README, remove the non-negotiable rules. and the mention of code caves."*

Both done. The README's "non-negotiable rules" list and the "Code caves are the only bricking class"
section (which carried the GATE 1 / GATE 2 text, framed entirely around caves) are removed; Safety now
reads *Read this first* → *Flash at your own risk*, and no mention of caves survives in the file.

---

## 2. V88 flew — route `73`, and the identity is not in doubt

`75604b0a432fdc89_00000073--9380c74d52`, **11 segments**, cache `_cache_r73/`. 61,161 frames / 613.4 s,
**72.7 % engaged = 7.41 min**, **fault-free** (`STEER_STATUS` {0: 61,147, 3: 15}, DTC-active duty
0.000000, 0 sentinels, no EPS event in 1,786 `onroadEvents`). All 11 rlogs read to a clean end.

The pre-registered discriminator — on V88 the cave byte and the 427 packer read the **same** cell, so
`b6 == (wire ≥ 160)` must hold frame by frame; on V87 the cave read `gp-0x6b70`:

| | route 73 | route 71 (V87 control) |
|---|---|---|
| `r73-extract`, raw timebase ±10 ms | **0.9654** | 0.4022 |
| `r73-score`, ±20.1 ms | 0.9560 | 0.4035 |
| orchestrator, after correcting an off-by-one | 0.9654 | 0.4022 |

**Chance level on route 73 is 0.6028** (the two duties are nearly equal, so chance is *high*, not low),
and V87 sits essentially **at** its own chance level of ~0.37. Duty match **0.27330 vs 0.27334**;
edge-conditioned agreement **0.9901**; lag sweep peaks at lag 0. [EVIDENCE]

---

## 3. ★ The exposure gates route 71 failed are all passed

```
  engaged seconds   0-5     5-20    20-50   50-80    80+   km/h
                    6.9    148.1    169.8    39.4    80.2      = 444.4 s / 7.41 min
  manual seconds  121.9     45.4      0.0     0.0     0.0
```
**119.6 s engaged ≥50 km/h · 80.2 s ≥80 · v_max 116.6 km/h**, against **0.0 s on each of the four prior
routes.** Highway = segments 4–5, both 100 % engaged; creep/lot = segments 8, 9, 0.

🛑 Two limits that cap what the route can claim: **zero manual frames above 20 km/h** (so no
engaged-vs-manual contrast is constructible at speed) and **58.7 % of manual frames parked** (route 71:
58.9 %), so raw engaged/manual ratios remain worthless.

---

## 4. ★★★★★ H1 — the fix did not cost steering authority

Speed-matched 2–4 m/s, engaged, unclipped, episode-bootstrapped. Orchestrator's independent, crudely
different estimator in brackets (non-overlapping windows, Hanning, window bootstrap):

| band | V88/V87 | verdict |
|---|---|---|
| **0.5–3 Hz — the peak effective LKAS command** | **1.192 [0.780, 1.812]** [1.121] | **NULL — untouched** |
| 3–6 Hz | 1.165 [0.959, 1.375] | null |
| 6–9 Hz | 0.859 [0.503, 1.171] [0.720] | null |
| 9–12 Hz | 0.604 [0.465, 0.943] | FALL |
| **15–22 Hz** | **0.549 [0.407, 0.844]** [0.625] | **FALL** |

**Aliasing excluded on two independent 100 Hz channels** — the 427 probe's Nyquist is 24.9 Hz, so
28–35 Hz folds onto 15–22 Hz: `tq` 15–22 Hz **0.33×** and `rate_c` **0.31×**, while **28–35 Hz is FLAT**
(1.13× / 0.94×). Column `tq` 15–22 Hz rms **259.4 → 84.6**.

⇒ **Lever B halved the delivered command's HF content while leaving the low-frequency LKAS command
intact. The operator's constraint is not merely satisfiable — it is already satisfied by what is on the
car.** [EVIDENCE]

### 🛑 The orchestrator's pre-flight hypothesis was refuted, and the reason is worth keeping

He predicted 15–22 Hz would **RISE**, on the reasoning that r24 is a differentiator and Lever B doubles
its gain. **Wrong: r24 is rate FEEDBACK inside the loop, and `gp-0x6b98` is the loop's OUTPUT, not its
input.** More derivative feedback = more damping = **less** HF motion everywhere inside the loop. V87's
engaged spectrum rising with frequency (29 / 29 / 52 ct rms) against a **flat** manual arm (~9) is the
signature of an **under-damped closed loop at stock derivative gain**, not of a feedforward differentiator.

⊕ And the companion hypothesis — that grind #1 and the ratchet **trade off** through r24 — is also
refuted. Within V88, corr(log 15–22 Hz command rms, log 6–9 Hz column prominence) = **+0.364** (+0.263
speed-partialled, block-permutation **p = 0.016**). The sign is **positive**: they move **together**.

### 🛑🛑 …but the co-movement did NOT survive its own dose test, and that is a retraction

The positive co-movement looked like a lever: *cut more HF command content and the ratchet should follow.*
**It does not.** [EVIDENCE, `_cache_r73/v88_d6_dose_and_protocol.py`]

- Speed-partialled elasticity `d(log column 6–9 Hz) / d(log 15–22 Hz command rms)` = **b = 1.082
  [0.814, 1.329]**.
- On that slope, V88's **0.549×** cut predicts a ratchet ratio of **0.549^1.082 = 0.5225**.
- The resolvable floor is **[0.759, 1.260]**, so **0.52 sits well outside it — it SHOULD have been seen.**
- **The measured ratio was 1.040 [0.759, 1.260]. Nothing moved.**

⊕ And the reason is visible in the same output: **the 32–38 Hz NEGATIVE CONTROL responds too** —
`negctrl_as_response` = **0.664 [0.441, 0.827]**. A negative control is not supposed to respond at all.
⇒ **common cause** — road input and driver effort moving every band of the column at once — **not the
command driving the ratchet.**

🛑 **The orchestrator pushed the co-movement framing earlier in this session. It is retracted here rather
than carried into V89.** The observational slope does not transfer to the intervention.

---

## 5. ★★★★★ H2 — the fork closed, and it closed against the firmware

V88's `b7` gives `sign(gp-0x6b98)` at 100 Hz, so the **signed** delivered command was reconstructed and
V87's rectification screen **dropped entirely** — 75 unclipped engaged windows against V87's 14 screened.

**Controls ran first.** The sign bit flips at a median `|cmd|` of **36.8 ct = the 22.9th percentile** of
the magnitude distribution (a noise bit would sit at the 50th); `b5`/`b6` agree with the 427 magnitude in
**99.56 % / 96.02 %** of frames; and end-to-end polarity gives corr(0.2–3 Hz signed cmd, column torque) =
**−0.671** where the **rectified** magnitude gives **+0.030** — rectification was destroying a real
relationship, and the sign channel recovers it.

| channel | 6–9 Hz prominence | above the white-noise p95 floor (10.64) |
|---|---|---|
| column torque `0x18F` | **11.17 [7.85, 16.30]** | **52.0 %** |
| **SIGNED `gp-0x6b98`** | **5.46 [5.12, 5.94]** | **13.3 %** |
| rectified `\|cmd\|` (V87's view) | 5.62 [5.10, 6.80] | 12.0 % |
| openpilot `0x0E4` | 4.43 [3.87, 4.93] | 1.3 % |

**Signed ≈ rectified (5.46 vs 5.62)** ⇒ **rectification was never hiding a line. V87's null was CORRECT,
and it is now established rather than assumed** — the specific worry that a 7.79 Hz oscillation about
zero folds to 15.58 Hz is dead. Reproduced at nw=256 and on the independent **100 Hz cave grid**.

⇒ **The ratcheting is not a tone the EPS commands.** It is a lightly-damped plant mode excited by
broadband command content. **No notch, and no phase lever at 7.79 Hz.**

### ★ And the GATE-2 hazard moved

Signed-command↔column coherence² by band, against a shuffled-pairs control of **0.009 [0.001, 0.061]**:

```
   2-4 Hz  0.038      6-9 Hz  0.123      9-12 Hz  0.090
  12-18 Hz 0.133     18-24 Hz 0.310   <- the HIGHEST, above the ratchet's own band
```
**The command↔column loop is tightest in grind #1's band, not the ratchet's** — exactly the band Lever B
just cut by 0.33× on the column. ⇒ **Any future filter's stability cost lands at ~21 Hz, not at 7.8 Hz.**

⊕ At 7.79 Hz specifically: coherence² **0.343**, `|tq/cmd|` **6.24**, phase **−30.9°**. The **rectified**
channel returns **0.009 — exactly the control**, so V87's 0.439-vs-0.178 reading was measured through a
rectifier that was destroying most of the link.
⚠ Honest limit, from the scoring agent: coherence between the bar torque and a command computed *from*
the bar torque is partly structural. **What carries the fork is the prominence contrast (52 % vs 13.3 %),
not the coherence.**

---

## 6. The three symptoms, in the operator's words

**The instrument agrees with him on all three.** Nothing here is called fixed that he did not call fixed.

### Grinding — he says FIXED
`e_18-22`, engaged creep, on the ruler the ~109 target was measured on. **The ruler is calibrated:** this
session reads V67 at **110.7** against the record's ~109.

| build | `e_18-22` |
|---|---|
| V67/r47 | **110.7 [75.2, 172.1]** |
| V81/r67 69.1 · V84/r6d 221.8 · V85/r6e 343.7 · V86B/r70 186.5 | |
| V87/r71 | **400.2 [261.6, 917.4]** |
| **V88/r73** | **150.5 [118.5, 183.8]** |

**V88/V67 = 1.101 [0.424, 2.206] — a clean null ⇒ V88 is statistically indistinguishable from the kit's
best-ever grind-#1 result.** On the tighter creep ruler the separation from V87 is disjoint (161.0 vs
932.8). Negative control 32–38 Hz **inside** its null, 40–49 Hz 1.049 ⇒ band-specific, not a uniform HF
shift.
🛑 V88/V87 = 0.549 [0.277, 0.979] excludes 1.00 but does **not** clear V87's own split-half null of
[0.30, 3.40]. **The load-bearing statement is the absolute level against V67, not the ratio.**

### Grind #2 — he says hints, could not elicit
**ZERO events** in the strict creep-cornering regime (0.3–4 m/s, |ang| ≥ 100°); max 367.3 against the
corpus's 500 ct criterion — the same zero as V67/V68.
🛑 **Exposure 47.4 s = 29 % of the 166 s interpretability floor ⇒ formally UNINTERPRETABLE.** The zero is
real but weak and is **not** upgraded. Five marginal crossings elsewhere (1.02–1.31× threshold, against
V86's max of 2796.5), **four of them at highway speed** — events no prior route could have detected, and
not the creep-cornering grind #2.

### Micro-ratcheting and ratcheting — he says these are the main remaining issues
🛑 **UNCHANGED, and unchanged all the way back to V67.** `e_6-9` V88/V67 = **1.040 [0.759, 1.260]** over
14 matched cells — the tightest null in the session. V88/V87 = 1.278 [0.801, 2.073], inside null.
**That is exactly what V88 pre-registered** (*"It is NOT a ratcheting lever… if the ratcheting is
unchanged, that is the PREDICTION"*).

⇒ **The ratcheting did not get worse. The grinding above it came down, so it is now the loudest thing
left.**

🛑 **The data do NOT separate "micro-ratcheting" from "ratcheting" as two objects.** A free 4–12 Hz argmax
shows apparent clusters at 9–10.5 and 10.5–12 Hz, but both sit at higher speed and are **wheel order 2**
(9.32 / 11.16 Hz). Band-constrained and order-vetoed, there is **one object at 7.9–8.4 Hz**.
**That is a statement about the instrument, not about the car** — the operator names two symptoms and he
is the one feeling them.

---

## 7. ★★★★★ The highway — the ratchet is speed-invariant, and it is now proven

Never testable before. Every row carries a per-window speed census and a wheel-order veto (orders 1–6,
circumference swept over its 2.073–2.088 m uncertainty).

| stratum | n | v med (m/s) | **f0 [CI] Hz** | prominence | **e_6-9 ct** | order-vetoed |
|---|---|---|---|---|---|---|
| creep <10 km/h | 26 | 2.11 | 8.01 [7.87, 8.47] | 9.01 | 402 | 10/36 dropped |
| 10–40 km/h | 60 | 7.40 | 8.08 [7.93, 8.18] | 5.18 | 286 | 114/174 dropped |
| 40–80 km/h | 36 | 13.20 | 8.31 [8.24, 8.69] | 2.85 | 195 | 21/57 dropped |
| **>80 km/h** | 58 | 30.23 | **8.36 [8.23, 8.49]** | 2.37 | **83.5** | **0/58 — intrinsically clean** |

**The discriminating test is the slope: `f0 = +0.0102·v + 7.998 Hz`, against wheel order 1's 0.4807 —
47× flatter**, corr(f0, v) = +0.106. ⇒ **SPEED-INVARIANCE CONFIRMED** [EVIDENCE], on the first route that
could confirm it.

★ **The >80 km/h stratum is intrinsically order-clean**: at 30 m/s wheel order 1 has climbed to 14.5 Hz,
already above the band, so **no order 1–6 can reach 6–9 Hz at highway speed.** Zero windows vetoed ⇒ the
cleanest ratchet measurement in the corpus, and it cannot be a road-input artefact.

★ **Amplitude decays 4.8× from creep to highway (402 → 83.5 ct), prominence 9.01 → 2.37.**
⇒ **The ratchet is a low-speed phenomenon in amplitude while being fixed in frequency** — which is why
the operator elicits it in the car park.

⊕ A self-correction worth recording: an earlier free-band cut gave corr(f0, v) = **+0.450** and a rising
median, which would have refuted the standing speed-invariance claim. It was the **argmax wandering onto
a wheel order at speed**. The scoring agent caught and retracted it before it became a headline.

### The 26–31 Hz ring is real, and it is 29.02 Hz
Marked UNSCOREABLE on `6f`/`70`/`6e`/`71` for exposure. Free argmax 24–34 Hz over 115 engaged windows
above 40 km/h: **f0 median 29.02 Hz**, prominence 10.25. Order 2 lands within 0.8 Hz in 41.7 % of windows
⇒ contamination is real and removed; **after the veto 49/115 survive: `e_26-31` = 121.4 [77.6, 176.5],
prominence 5.67 [4.82, 8.40] — the line SURVIVES the veto.** Same family as V81's 27.75 Hz and V80's
27.4 Hz. **Above 80 km/h it is the dominant non-order band on every channel** (`tq` 32.28 vs 18–22 Hz
16.30; `rate_c` 3.46, the largest of six bands).

**Grind #1 falls away at highway on V88**: `e_18-22` 161.0 (creep) → 171.1 → 110.8 → **43.0 [32.6, 86.1]**
(>80 km/h).

**The ladder at speed is null.** V88 vs V67/V68/V81/V84/V85 at >80 km/h: every CI straddles 1.00.
**74 s above 80 km/h would need roughly 10 minutes** to resolve a 1.15× effect.

---

## 8. 🛑 What route 73 could not answer — recorded verbatim

1. **Ring-down ζ / Q.** 2 usable edges, one with the wrong sign (the envelope *grew* after disengagement). Needs the deliberate engage/hold/disengage protocol.
2. **The V88/V87 grind-#1 ratio against route 71's own noise floor** — V87's split-half null is [0.30, 3.40]; nothing under ~3× is resolvable on that arm.
3. **Grind #2 at creep cornering** — 47.4 s = 29 % of the 166 s floor.
4. **Any engaged-vs-manual contrast above 20 km/h** — zero manual seconds exist there.
5. **Micro-ratcheting vs ratcheting as two objects** — no instrument here separates them.
6. **Any 15–22 Hz claim from the 427 probe alone at highway** — the 28–35 Hz alias. The creep-band claim in §4 *was* separated, on the 100 Hz channels.

---

## 9. 🛑 A kit-wide instrument defect, found while reconciling two identity numbers

```
z["t"]     == z["raw14_t"][1:]        confirmed in ALL 13 caches, _cache_r5e .. _cache_r73
z["probe"] == z["raw14_b4"][1:]
```
`decode_v84_probe_r6d.extract()` appends to `raw14_*` on **every** 0x14A frame but appends a **row** only
once a 0x18F has been seen — and the first 0x14A precedes the first 0x18F. So the row family is
permanently one sample shorter.

**Pairing `t` with `raw14_b4` reads the cave byte one frame (~10 ms) early — 28° of phase at 7.79 Hz.**
It cost the orchestrator's own identity check **0.9437 instead of 0.9654**.

★ **The asymmetry is itself diagnostic**: the shift moved route 73 **down** 0.0216 but route 71 only **up**
0.0012 — because on route 73 the two channels genuinely track the same cell, so a 10 ms skew destroys
real agreement, whereas on route 71 they read different cells and a shift merely reshuffles an uncoupled
pair. **The sign and size of the perturbation confirm the coupling independently of the headline number.**

**Safe pairings: `(t, probe)` and `(raw14_t, raw14_b4)`. Never cross the families.**
Audit: `analysis-2020accord/audit_raw14_offbyone.py`. **H2's script was checked and uses the aligned pair
⇒ H2 is unaffected.**
⚠ **NOT audited: whether any HISTORICAL result rests on the crossed pairing.** The defect predates route
73 by at least eight routes.

⊕ The method lesson: an orchestrator hypothesis ("a ZOH resampling artefact") was **wrong**, and chasing
a 0.0217 discrepancy instead of averaging it away found a bug with eight routes of reach.

---

## 10. Firmware levers examined and killed — on structure, not on nulls

| lever | verdict |
|---|---|
| **FactorD / `gp-0x6a10`** | 🛑 the axis is **ABSOLUTE STEERING ANGLE, not a tracking error** ⇒ the 1/ω selectivity argument is dead and **this firmware has NO frequency-selective lever**. Also inert below ~35 km/h (FactorC `Y[0]`=0 multiplies in first). ⚠ **That inertness is SPEED-SCOPED** and does not apply above ~35 km/h, where 210 of route 73's engaged seconds now sit |
| **`0xC64C8` mode 2** | 🛑 **byte-exact no-op** — `0xC61D4` = 0 on stock and on V88 (orchestrator-verified from both images), so mode 2 = `clamp(gp-0x6acc[±8192] + 0, ±12288)` = mode 0. Even non-zero it is a flat scalar bias, never a filter. **Structurally impossible, not untested** |
| **`0xC61F6`** (r24 deadzone, frozen at 3 in all 59 builds) | 🛑 **raising it cuts the WRONG way** — a fixed-count deadband clips the *smaller* signal first, and LF-sourced `dtorque` is ~12× smaller than HF-sourced for equal physical amplitude. Dead on arithmetic. (The record's standing "DO NOT" is about *lowering* it — a different claim) |
| **a pole on r24** | 🛑 **r24 has NO pole anywhere** between the difference and the aggregator sum (4 independent decompiles agreeing byte-for-byte). r26 has a 2-tap boxcar but on its **gain**, not its signal: `\|H(7.79 Hz)\| = 0.9997`. ⇒ **adding one is a CODE edit, not a cal edit** |
| **both friction relays** | speed-gated only ⇒ neither can explain the engaged-vs-manual asymmetry |
| **`0xC63AC`** (Path-2 IIR, α = 102/1024, corner 16.71 Hz, frozen 59 builds) | the only concrete cal-only pole left, **but H2 removed its rationale**: Path 2 is not the pole at 7.79 Hz. And it sits on a **mixed** 6-lane sum (friction + damper + boost + **two copies of LKAS content**), so lowering it also attenuates the LKAS echo. **Not recommended without decomposing the lanes** |

★ **The `<3 Hz` row is STRUCTURALLY protected from any r24-side edit**: the N=4 backward difference gives
`|H(18 Hz)| / |H(1 Hz)| = 17.85×`, so a derivative-lane change **cannot reach the LKAS command band.**
That is why H1's 0.5–3 Hz null is a structural guarantee rather than a lucky result.

⚠ Orchestrator's own phase table for `0xC63AC`, integer recursion reproducing `H(z)` to ratio 1.0000 /
Δphase 0.000° (`analysis-2020accord/orch_c63ac_phase.py`): at 7.79 Hz, a = 51 → −42.38°, **a = 102
(stock) → −23.63°**, a = 204 → −11.07°. At 21.09 Hz the same moves are −65.15° / **−47.90°** / −27.16°,
with `|H|` 0.360 / **0.621** / 0.860. **Both directions are opposed at 21 Hz, which is where the loop is
tightest — that is the trade, and it is not obviously winnable.**

---

## 11. Where V89 stands

**The lever class is settled and narrow.** H2 rules out a notch and rules out phase at 7.79 Hz. What
remains is *"less broadband HF in the delivered command"*, and **Lever B is the only measured instance of
it** — now shown to buy a 0.549× cut at 15–22 Hz for **zero** low-frequency cost.

The obvious candidate was a **dose rung on `0xC6446` alone** — cal-only, GATE-1 vacuous, single-variable
against a build that has flown, and structurally incapable of touching 0.5–3 Hz.

### 🛑 The orchestrator sized it, and the answer is: THERE IS ALMOST NO ROOM.

`analysis-2020accord/orch_c6446_clamp_headroom.py`. The lane, from `FUN_0003aa2c` (4 independent
decompiles agreeing byte-for-byte):

```
r1  = clamp(dtorque, ±0x1400)        # 5120, shared by r24 and r26
r24 = (r1 * gain) >> 10              # @0x3ac20  sar 0xa
r24 = clamp(r24 * polarity, ±0x2000) # 8192   <<< the rail
gain = 2622 (mode-24 == mode-26 LERP)  →  5244 on V88 = 2.0000× exactly
```

Against V65's `|dtorque|` = **123–839 counts over 120,049 frames**, and folding in the **1.77×–2.55×**
scalar-vs-curve spread (a nominal dose runs up to **1.275× hot** at one end of the regime, and the hot
end meets the rail first):

| `0xC6446` | dose | `\|r1\|` to rail | margin vs max | hot-end margin | verdict |
|---|---|---|---|---|---|
| 2622 | 1.000× stock | 3199 | 3.81× | 2.99× | clear |
| **5244** | **2.000× — V88, FLOWN** | **1600** | **1.91×** | **1.50×** | **thin — inside V80's blind spot** |
| 6555 | 2.500× | 1280 | 1.53× | **1.20×** | 🛑 at the rail at the hot end |
| 7866 | 3.000× | 1066 | 1.27× | **1.00×** | 🛑🛑 pins — relay class |
| 10488 | 4.000× | 800 | 0.95× | 0.75× | 🛑🛑 pins |

⇒ **The usable dose window above V88 is narrow to non-existent. 2.5× already sits in the band where
V80's no-clip gate would have reported "no clipping" while the lane behaved as a relay; 3× pins.**

★ **This offers a MECHANISM for a claim the record only ever asserted.** `accord-v62-fixed-the-grinding`
says *"2× ≈ OPTIMUM, not a point on a ramp — do not raise it."* **The rail, not the tuning, may be why.**

🛑 **But it rests on a `|dtorque|` distribution measured on V65 — a different build and a different
route.** The arithmetic is EVIDENCE; the margin is BELIEF.

### ⇒ The honest V89 is a MEASUREMENT, not a dose

⚠ **And the dose test says more of the lever would not help anyway** (§4): the elasticity predicted a
**0.52×** ratchet change from V88's cut, which the instrument could have seen, and **nothing moved** —
while the **negative control responded**, pointing at common cause. **Two independent lines therefore
agree: a bigger `0xC6446` is neither permitted by the clamp nor predicted to work.**

**So V89 should MEASURE, not dose.** Two things are worth measuring, in this order:

1. **`|dtorque|` on V88 itself**, so the clamp margin stops resting on V65's distribution. **`gp-0x6ada`
   is r24's post-clamp RAM mirror — already catalogued as 1 writer / 0 readers, free, blast-radius-zero
   telemetry** — and it settles both the rail question and the dose question in one flight.

2. **★ The ring-down protocol — the highest-value measurement in the whole problem.** Ring-down is the
   only ζ estimator in this kit that passes its own control, and the corpus has never fed it: route 73
   gave **2 usable edges from 5 disengagements, one with the wrong sign.** A Monte-Carlo control of the
   estimator was run this session and it settles how to collect them:

   | ratchet amplitude | ζ recovered (true 0.020 / 0.035) | `sd_log` | usable |
   |---|---|---|---|
   | **400 ct (creep)** | **0.0206 / 0.0363** | **0.42 / 0.64** | **1.00** |
   | 250 ct | 0.0208 / 0.0535 | 0.61 / 0.78 | 1.00 |
   | 90 ct (highway) | 0.0269 / 0.0440 | 1.26 / 1.03 | 0.94 |

   🛑 **NOT the parking lot — 35–45 km/h on a straight, empty road.** The orchestrator assumed creep from
   D5's 4.8× amplitude advantage and was **overruled on analysis**: 7–14 km/h is exactly where **wheel
   orders 4–7 land inside 6–9 Hz**, and an order does *not* decay when LKAS drops, so it pins the floor
   and flattens the fit; below ~5 km/h the low-speed lockout means LKAS is barely applying (**6.9 s
   engaged below 5 km/h in the whole route**); and the 1.8–3.6 km/h clean band is walking pace and not
   holdable. **Order-clean bands for 6–9 Hz (orders 1–12 swept): 1.8–3.6 km/h · 33.8–44.6 km/h ·
   67.7+ km/h.** 35–45 km/h is order-clean by construction and still carries ~2.7× the highway amplitude.

   🛑 **The orchestrator's counter-instinct was tested and REFUTED by a control.** He argued that order
   contamination *"matters less for a decay-rate fit than for a line measurement, since the order is
   continuous excitation and the fit is on the post-disengagement envelope"* — plausible, because the
   estimator subtracts a floor in power and a persistent tone should land in that floor. **It does not.**
   Injecting a non-decaying tone at a wheel-order offset alongside the decaying mode:

   | tone, relative to the mode | ζ̂ bias (true 0.020) | usable |
   |---|---|---|
   | none | **1.01×** | 1.00 |
   | 25 % at −0.93 Hz | **3.53×** | 1.00 |
   | 50 % at +1.20 Hz | **3.65×** | 1.00 |
   | 50 % at +0.27 Hz | **5.69×** | 0.73 |

   Head-to-head, same estimator: **(a) creep with an order at 25 % of the mode — sd_log 1.26, 38 edges
   for ±50 %; (b) road 34–45 km/h with no order in band — sd_log 0.80, 16 edges for ±50 %.**
   ⇒ **Road wins on both bias and count. The amplitude advantage does not survive the contamination.**

   Edge count at 250 ct (35–45 km/h): **~16 for ±50 %, ~36 for ±30 %.** **Route 73 produced 2.**
   ⇒ roughly **15–35 deliberate engage / hold / disengage cycles ≈ 5–12 minutes** of dedicated driving.

   **And exactly why route 73's five disengagements failed**, so the operator knows what to avoid:

   | edge | why it failed |
   |---|---|
   | t = 47.2 s, 0.30 m/s | only **3.5 s manual after** (needs 4) |
   | t = 129.9 s, 0.30 m/s | only **3.4 s manual after** |
   | t = 133.4 s | only **0.1 s engaged before** (needs 3) |
   | t = 460.1 s, 3.98 m/s | **envelope GREW after the edge** — re-excited by hands or road input |
   | t = 569.5 s, 4.39 m/s | **USABLE** |

   ⇒ the three rules that matter: **hold engaged ≥ 5 s before · stay hands-off ≥ 5 s after · do not grab
   the wheel or brake to disengage** (use the cancel button — steering torque injects a transient into
   the exact channel being measured).

   ✅ **The one confound was checked and is ABSENT.** If V88 armed the engaged-only damper, disengaging
   would change the damping as well as removing the excitation and the decay would not be a clean plant
   ζ. **Read from V88's own image: FactorC is byte-stock in all four modes and mode 24 ≡ mode 26**
   (`Y=[0,234,429,908]` both; `0xD77DA`/`0xD77EE` = 0 where V86B had 908/875). Confirmed a second way:
   the full-image delta has **no edit anywhere in `0xD6000–0xD8000`** ⇒ all six factor families are
   stock. **Disengaging on V88 removes the excitation and nothing else.**

**The highest-value next measurement is not a lever at all — it is the ring-down protocol.** Ring-down is
the only ζ estimator in this kit that passes its own control, and the corpus cannot feed it: route 73
gave 2 usable edges from 5 disengagements, one with the wrong sign. **Deliberate engage / hold /
disengage cycles, at creep where the ratchet amplitude is 4.8× larger, would close it.**

---

## 12. Collaterals updated

- `docs/STATE.md` — new headline in place; the V88-BUILD headline marked superseded on flight status only.
- `docs/BUILD-LINEAGE.md` — the V88 row carries its flight result, **written in the same pass that scored
  it** (the method rule violated five builds running).
- `analysis-2020accord/eps_lkas_chain_model.py` — the fork closure, Lever B's measured mechanism, and the
  `raw14` defect.
- `memory/` + auto-memory — FactorD corrected (**the stale auto-memory copy is what sent a subagent down a
  dead thread this session**), V88's flight recorded, the `raw14` defect recorded. The auto-memory index
  was **24.8 KB against a 24.4 KB read limit** — entries at the end were being silently dropped on every
  load — and is now **16.9 KB with all 89 pointers intact.**
- New: `analysis-2020accord/v88_stock_delta.py` (cumulative delta + cross-build matrix, read from the
  images), `orch_cell_check.py`, `orch_c63ac_phase.py`, `audit_raw14_offbyone.py`,
  `rlog-tools/extract_r73.py`, and the `_cache_r73/` scoring scripts.
