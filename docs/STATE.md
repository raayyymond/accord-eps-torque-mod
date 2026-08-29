# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V168 SUPERSEDES V158 AS FLY-FIRST.** V168 *is* V158 plus one byte, so it carries both levers, and the two symptoms score from the SAME 15 s episode in different bands (grind 15-25 Hz, ratchet 5-12 Hz, both in `cs_tq`) — **separated by the INSTRUMENT, not by the build**. Fly V158 alone only to isolate the grind lever on FEEL. Card: `docs/scoring/DRIVE-CARD-V168.md`.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-assist-map-session.md` carries every finding, every retraction and the open-items list with what would close each.
## 🛑🛑 **THE ENGAGED RATCHET MAY BE OURS: WE AMPLIFY A DESTABILISING INERTIA TERM 3-8x, ENGAGED-ONLY — V175 REVERTS IT**
**A new mechanism, traced end to end this session, decompile-first.** It is the first account that
explains **why the ratchet is ENGAGED-amplified ~15x** in terms of a cell we ourselves moved.

### ✅ THE TRACE [EVIDENCE — both ends confirmed in Ghidra + a raw LE byte scan]
`FUN_00036c12` is the **sole writer** of `gp-0x6b26` (one `st.h -0x6b26[gp]` at `0x36CF0`; the other
five disp16 sites decode as `ld.h`, opcode 0x39 vs 0x3B):
```
   gp-0x6b26 = clamp( ((gp-0x6c2c * validgate) * LERP_0xCBE74[mode](gp-0x6a5e) >> 6) * 0x111 >> 0x12,
                      +- cal[0xC407E] )
```
- `gp-0x6c2c` is the **ACCELERATION** — `FUN_00041464` @`0x41602` `sub r7,r9` is a FIRST DIFFERENCE of
  the EMA-filtered resolver rate, then ×32, clamped, EMA'd, `>>9`.
- **the acceleration enters LINEARLY**; the LERP is indexed by `gp-0x6a5e`, a **scheduling** variable,
  not by α ⇒ `gp-0x6b26 = K(mode, sched) · α`, a pure apparent-inertia term.
- ⇒ **its loop contribution scales as ω²: 66.7x more at 8.17 Hz than at 1 Hz.**
  🛑 **This is the frequency selectivity the kit concluded it did not have** — and it is
  **STRUCTURAL, from differentiation order, not from a filter.** It costs NO phase lag anywhere.
  (It does not contradict [[accord-factord-is-the-angle-error-lever]], which refuted a *filter*-based
  1/ω selectivity. This is a different thing.)

### ✅ THE GATE CANNOT CLOSE
`FUN_00038148` admits it into the six-term Path-2 sum with `w[3]` = `tp+0x73a6` = **`0xC63A6`**, gated
on `(gp-0x6b26 + 0x400) < 0x801` i.e. `|x| <= 1024` (a **store-zero**, not a clamp). But the writer
clamps to **±`0xC407E` = 511** on stock, V173 and V174 alike ⇒ **511 < 1024, the gate is open EVERY
frame** and `w[3]` is an unconditional multiplier. [EVIDENCE, read from all three images.]

### 🛑 THE SIGN — IT IS POSITIVE ACCELERATION FEEDBACK, I.E. **NEGATIVE APPARENT INERTIA**
The Y rows are NEGATIVE, so `gp-0x6b26 = −|K|·α`. Through the verified polarity chain
([[accord-friction-polarity-more-friction-is-more-assist]], whose step 4 gives `f' >= 0` EVERYWHERE):
```
   alpha UP -> MODEL DOWN -> res UP -> gp-0x6b70 UP (f'>=0) -> target effort DOWN -> MORE ASSIST
```
⇒ **assist RISES with acceleration** ⇒ lowers effective mass **and lowers the damping ratio of the
resonance**. Amplifying it is the wrong direction — exactly what
[[accord-gp6b26-is-inertia-not-damping]] already said: *"the whole V74/V75/V91/V92 dose direction was
aimed at the wrong physics."*

### 🛑🛑 AND THE FLIGHT BUILD AMPLIFIES IT 3.0x / 3.0x / **8.14x**, ON THE ENGAGED MODES ONLY
```
   0xD7A5C m26 ENGAGED   Honda (-9830,-5734,-1966)  ->  FLOWN (-29490,-17202,-16000)
   0xD7A6C m27 ENGAGED   Honda (-9830,-5734,-1966)  ->  FLOWN (-29490,-17202,-16000)
   0xD6A6C m24 MANUAL    Honda (-9830,-5734,-1966)  ->  UNCHANGED
```
⊕ **The one destabilising ω²-weighted term is amplified 3-8x on exactly the modes where the ratchet
is amplified ~15x, and left alone in manual, where it barely appears.** [BELIEF — a structural match,
not yet a measured cause.]

### ⚠ THE RELAY HAZARD IS **UNEXCLUDED** ON THE CURRENT BUILD
Saturating ±511 turns `−K·α` into `sign(α)·511` — a **RELAY**, V80's exact failure
([[accord-v80-damper-relay-and-grind1-inert]]).
```
   K            alpha to saturate      stock-referred threshold
   Honda 1.0x       ~3195                     511
   FLOWN 3.0x       ~1065                     170     <== the CURRENT build
```
✅ The only on-car measurement is **V76's: `|gp-0x6b26| > 448` fired 0 / 63,477 frames**, route 65,
positive control 99.926%. 🛑 **That null is at 448. The threshold that matters at 3.0x is 170 —
2.6x lower, and NEVER MEASURED.** Bounded at Honda's K; **unknown at the flown K.**

### ✅ `0xC63A6` IS **UN-STRUCK** — ITS BLOCKING GATE IS CLEARED
It was struck 2026-08-11/12 because Path 2's sign depended on an **unknown LERP slope**, with the
release condition *"re-derive the slope from V96/V97's own instruments."* **That slope is now known:
`f' >= 0` everywhere (structural) and measured p50 2.174 hands-off / 0.346 hands-on**, with the
cross-check `d(gp-0x6b94)/d(gp-0x6b70)` = +0.2529/+0.2565/+0.2617 and a passing positive control.
⇒ **the cell is available.** V175 deliberately does **not** spend it (asserted FROZEN at 1024): a
revert to Honda's own numbers is a lower risk class and carries an on-car saturation measurement.

### ✅ V175 BUILT — 12 BYTES, SUBTRACTIVE, ENGAGED-ONLY
Base **V173**. `0xD7A5C`/`0xD7A6C` → Honda's row, **read from the stock image, never typed**.
**26/26 assertions · 12 payload bytes in 3 runs · CRC 50/50 · readback byte-identical · mode 24
untouched · `0xC407E` and `0xC63A6` asserted frozen · V173's four section coefficients asserted
carried.** image `a4e0dc4254ad8559…` · rwd `5bf63d0ea539fd18…` · builder
`analysis-2020accord/builds/v108_plus/build_v175_tva.py`.
✅ **THE DISCRIMINATOR vs V173's poles is ENGAGED vs MANUAL.** They stack and both attenuate the
ratchet, so amplitude alone cannot attribute — but V173's poles act in **both** modes and this revert
**cannot act in manual**. Ratchet falls *and* the engaged/manual ratio falls ⇒ the inertia dose was
carrying it. Ratio unchanged ⇒ V173's poles did it. Neither moves ⇒ both accounts fail together.
Score with `rlog-tools/score/grind_engaged_vs_manual.py` beside `score_band_excess.py`.
⚠ **It removes drag — creep effort will be lighter than the operator is used to.** Intended, and he
should be told.

## ✅ **V174 BUILT — THE PRE-REGISTERED SECOND POINT ON THE FRONTIER. V173 STILL FLIES FIRST.**
Cut so that the verdict *"better, but the ratcheting is still there"* costs **no build delay**.
🛑 **V174 IS NOT AN ALTERNATIVE TO V173 AND MUST NOT BE FLOWN FIRST.** It is the *expensive* point
on the same curve; flying it first throws away the ability to tell which point the car needed.
```
   ONE knob:  slow pole 0.970 -> 0.980   (C_B0 byte-identical, Honda's 55.23 Hz notch KEPT)
     0xC60A8  C_A8  -1.53719997 -> -1.45500004    raw BFBA3D71
     0xC60AC  C_AC  +0.63462001 -> +0.46549999    raw 3EEE5604
     0xC60B4  C_B4  +0.81730998 -> +0.08808687    raw 3DB466E4   (solved for unity DC)

                 flying    V174    ratio        V173 for comparison
     3.00 Hz     0.9975   0.7288   0.731x        0.8476
     8.64 Hz     0.9789   0.3393   0.347x        0.4761   RATCHET  (2.9x vs V173's 2.1x)
    21.00 Hz     0.8659   0.1275   0.147x        0.1894   GRIND    (6.8x vs V173's 4.6x)
    55.23 Hz     0.000128 0.000009               0.000013 Honda's notch, KEPT and deeper
```
✅ **27/27 assertions · 12 payload bytes · CRC chain 50/50 · readback byte-identical ·
`[0xC5000,0xC5FFC)` untouched.** Base **V158** (`42078806f5582903…`), so it carries V158's damper.
image `c3d6776cc72d4657…` · rwd `5e4ba53db14442cb…` · builder
`analysis-2020accord/builds/v108_plus/build_v174_tva.py`.
✅ **GATE 2 magnitude PASS: max |H| = 0.9880 to Nyquist** ⇒ can only REMOVE loop gain.
✅ **GATE 1 as V173**: `gp-0x6b86` has exactly one consumer outside its producer, no monitor.
⚠ **THE HONEST COST: +42.8 ms of group delay at 1 Hz** (V173 spends +29.1). The operator feels that
as **steering weight**, which is the thing he has explicitly said must not be the price of the fix —
so this build is **his call on a lag verdict**, not a default.
🛑 **DO NOT CUT PAST `p_slow` = 0.985 WITHOUT AN OPERATOR LAG VERDICT IN HAND.** Beyond there the
added lag exceeds anything this kit has ever shipped.
⚠ **The coefficients are RE-DERIVED FROM THE FORMULA inside the builder and asserted against the
pinned raw words** — a 6-dp decimal does not round-trip a float32; see [[feedback-float-spec-must-be-the-formula]].

## ✅ **100/12 Hz EXCLUDED · THE MODE GENUINELY WANDERS ±0.71 Hz · AND TWO OF MY OWN CLAIMS RETRACTED**
🛑 **RETRACTION 1 — I ran the assist section at FS=100 Hz. IT RUNS AT 1 kHz.** Verified against the
lineage's own three stock response points (notch 55.23 Hz, −1.25 dB @21, −3.01 dB @30, −0.02 dB @3):
FS=1000 reproduces all four, FS=100 reproduces none. **Two claims I made this session die with it:**
- ❌ *"Honda's notch is at 5.53 Hz, a 10x error in the record"* — **WRONG, the record was right.**
  The notch is at **55.226 Hz**. The 10x error was mine.
- ❌ *"V173 cuts the LKAS band up to 6.5x and doubles group delay"* — **WRONG.** At the true rate
  **LKAS 0.5–3 Hz is −0.05 to −1.42 dB — essentially intact.**

### ✅ THE 100/12 = 8.3333 Hz FIRMWARE-CYCLE HYPOTHESIS IS DEAD
Killed by a **synthetic positive control**, not by argument. Inject a *truly fixed* 8.3333 Hz line into
1/f noise with matched segment counts and run the identical estimator:
```
   synthetic FIXED line, SNR 0.5 / 1.0 / 2.0 -> sd 0.0051 / 0.0026 / 0.0011 Hz
   observed, 15 routes                       -> sd 0.7904 Hz     (150x larger)
   within-route split-half sd 0.3535  =>  TRUE route-to-route sd 0.7069 Hz
```
=> the estimator reproduces a fixed frequency to **0.005 Hz**. The spread is **real**, not noise.
**A firmware divider cannot produce a frequency that moves +-9 % between drives.** ✅ Also checked the
image directly: `add 1,rX` paired with `cmp N,rX` gives N=12 only **4** sites vs 22 for N=8 and 13 for
N=10, and the N=12/13/14 hits sit at regular 0x3E strides — **unrolled loop trip counts, not dividers.**

### ⚠ THE WANDER IS ITSELF A DESIGN CONSTRAINT — IT KILLS EVERY NARROW LEVER
🛑 **RETRACTION 3 (same FS=100 root cause): I said a re-centred notch dies because it is too
NARROW for a wandering mode, −0.42 dB worst case. WRONG on both the number and the reason.**
At the true 1 kHz it is relatively far wider and DOES attenuate the wander core — −15.4 dB at −1 sd,
−14.6 dB at +1 sd. **It dies on GATE 2 MAGNITUDE instead, catastrophically.** `C_B4` is pinned by
`C_B4 = (1+C_A8+C_AC)/(2+C_B0)` and `2+C_B0 = 2−2cosθ → 0` as the notch moves toward DC:
```
   notch @ 8.17 Hz, stock poles -> C_B4 = 36.98  (stock 0.8173, x45)
   max |H| absolute = 46.91      GATE 2 needs <= ~1   -> FAILS BY 47x
   GRIND 21 Hz  +16.33 dB (6.5x AMPLIFIED)    Honda's 55 Hz null  +108 dB (10^5 x)
```
⇒ a re-centred notch **amplifies the grind it is meant to help** and destroys Honda's null. This is
exactly the reason V173's own docstring already gives (`C_B4 ~ 1/f²`), reached independently from the
image bytes. ⊕ It is a second, independent argument for what V88 concluded from the wire (*"no notch, no phase lever
exists at 7.79 Hz specifically"*), and it re-confirms the standing lineage rule
🛑 **"THE NOTCH LEVER IS SPENT — do not re-propose a re-centred `0xC60A8` biquad."** V105 flew a
25.5 Hz notch and failed; `docs/review/GATE2-2026-08-20-notch-sign.md` refused re-centring at 6–9 Hz.
=> **the ratchet lever MUST be broadband.** That is exactly what V173's pole move is.

### ✅ V173 RE-PRICED AT THE CORRECT RATE — AND GATE 2 PASSES
```
   band                 V173 / stock          what it means
   LKAS   0.5-3 Hz      -0.05 .. -1.42 dB     authority MAGNITUDE intact
   ratchet 6.5-11 Hz    -4.50 .. -7.97 dB     partial (1.7-2.5x) but robust across the whole wander
   GRIND  15-25 Hz     -10.39 .. -14.70 dB    the primary endpoint, well served
   lane-change 26-31   -15.03 .. -16.51 dB
   COST: group delay  +30.1 ms @0.5 Hz  +29.1 @1  +21.4 @3   (-5.5 deg / -10.8 / -29.2)
```
✅ **GATE 2 (magnitude): PASS, decisively.** `max |H_V173 / H_stock| = 0.999753` over 0.1–499 Hz and
`max |H_V173| = 0.9998` absolute => the section **can only REMOVE loop gain, never add it**, and no new
resonance exists. Same argument class V103 passed on.
⚠ **GATE 2 (phase): a real, bounded cost.** −10.8 deg at 1 Hz and −29.2 deg at 3 Hz is materially more
in-band phase than V103 spent. It is the **mechanism** by which the mode is damped, not a side effect —
but it is the honest price, and the operator feels it as lag, not as lost authority.

### ➕ THE FRONTIER — PRE-REGISTERED NEXT STEP IF V173 IMPROVES BUT DOES NOT CURE
The slow real pole couples attenuation to lag **inseparably** (one real pole, one time constant), at a
strikingly linear rate:
```
   p_slow   corner   ratchet@8.17   grind 15-25   lag@1Hz      ~4.8 ms of 1 Hz lag
   0.9700   4.85 Hz    -5.89 dB      -12.61 dB    +29.1 ms  <== V173
   0.9800   3.22 Hz    -8.77 dB      -16.03 dB    +42.8 ms     buys each extra dB
   0.9850   2.41 Hz   -11.03 dB      -18.49 dB    +54.1 ms     of ratchet attenuation
   0.9900   1.60 Hz   -14.38 dB      -22.00 dB    +69.2 ms
```
=> **If the drive says "better but still there", the next build is `p_slow` 0.970 -> 0.980** (`C_A8`,
`C_AC`, `C_B4` re-solved for unity DC): −2.9 dB more ratchet for +14 ms more lag. **Do not go past
0.985 without an operator lag verdict** — past there the lag is larger than anything the kit has shipped.

## ⚠ **HYPOTHESIS, UNPROVEN: IS THE RATCHET AT EXACTLY 100/12 Hz? — AND THE DRIVE CAN SETTLE IT**
🛑 **Every ratchet frequency I have quoted this session — 7.81, 8.01, 8.20, 8.40, 8.59, 8.79 — is an
exact FFT BIN CENTRE** at 0.1953 Hz spacing. I never resolved the frequency, only which bin it fell
in. That is worth knowing because **100/12 = 8.3333 Hz** sits inside the measured range, and an exact
submultiple of the 100 Hz frame rate would mean a **firmware cycle** rather than a mechanical mode — a
completely different lever.
```
   parabolic peak interpolation on pooled continuous-run PSDs
     nperseg=512   19 routes   mean 8.1682 Hz  sd 0.7027   range 6.78-10.19
     nperseg=1024  12 routes   mean 8.2958 Hz  sd 0.8009   range 7.35-10.42

     100/11 = 9.0909  excluded at 2 SE     100/13 = 7.6923  excluded at 2 SE
     100/12 = 8.3333  consistent -- 0.5 % from the mean at nperseg=1024
```
⚠ **[HYPOTHESIS, NOT EVIDENCE] and two reasons to distrust it:**
1. **I selected the candidate submultiples AFTER seeing the range.** Finding that a mean lands near
   one of three post-hoc candidates is weak, and I have no pre-registration for it.
2. **The per-route scatter (sd 0.80 Hz) is far larger than the interpolation error.** A fixed-frequency
   mode measured at df = 0.098 Hz should not scatter that much, which argues the frequency **genuinely
   varies** route to route — i.e. against an exact submultiple. The alternative reading is that the
   estimator hops between nearby peaks on a noisy median PSD, which would inflate the scatter without
   the frequency moving. **These are not distinguishable at this window length.**

### ✅ WHAT WOULD SETTLE IT — AND THE V173 DRIVE CAN SUPPLY IT FOR FREE
No route in the corpus has **20 s of unbroken engaged creep**, which is why the resolution ceiling is
0.098 Hz. **A single 20-second continuous pass gives df = 0.05 Hz and pins the frequency to ~0.5 %
on that one route** — enough to separate 8.3333 from a nearby mechanical value.
⊕ The drive card already asks for **15 s continuous**. **Stretching one pass to 20 s costs nothing and
adds this test**, which is why it is worth mentioning rather than leaving as a curiosity.
⊕ **If it IS exactly 100/12**: the mechanism is something running on a 12-frame cycle, the lever is
that structure, and V173 would be treating a symptom rather than a cause. **If it is not**: the
mechanical-resonance reading stands and V173's case is unchanged.
🛑 **This changes nothing about the build or the flight order.** V173 attenuates the response
whatever the mode's origin. It is recorded because **the test is nearly free and the answer would
matter a great deal.**

## ⚠ **PRECISION: “COMMAND-DRIVEN” DOES NOT MEAN THE COMMAND CARRIES 8.2 Hz — AND THE DIFFERENCE
MATTERS**
I wrote *“THE RATCHET IS DRIVEN BY THE COMMAND”*. Read carelessly that says the command **contains**
8.2 Hz energy and injects it, which would make *“filter the command at 8 Hz”* an obvious lever.
**It would do nothing, because the command has no 8.2 Hz content.**
```
   command channels in the RATCHET band, 19 routes, excess / own slope-matched null
     sc_tq 0.92 · co_tqcan 0.91 · cc_req 0.88      — all BELOW 1.0, i.e. no peak at all
   and the kit's own record: the LKAS lane is a ~1-5 Hz LOW-PASS, so the command CANNOT
   carry 8.2 Hz even in principle.
```
✅ **What the coupling result actually shows**: band-specific coherence between command and `cs_tq`
at 7–10.5 Hz, above a 30–40 Hz control band and above phase-shuffled surrogates (median **+0.115**,
CI **[+0.027, +0.168]**, n=17). **Coherence at a frequency does not require the input to have a peak
there** — broadband command activity moves the wheel, the motion excites a **plant resonance**, and the
response appears at the plant's frequency, not the command's.
⇒ **the correct statement is: the ratchet is a PLANT resonance EXCITED by command activity, and
amplified ~15× by the engaged loop.** “Command-driven” is shorthand for the excitation source, not a
claim about the command's spectrum.

### ✅ WHY THIS PREVENTS A WRONG LEVER
❌ **Do not propose filtering or notching the LKAS command near 8 Hz.** There is nothing there to
remove — all three command channels sit below their nulls in that band, and the LKAS lane already
low-passes at 1–5 Hz. Such a build would be **inert by construction**, and its null would be
uninterpretable rather than informative.
✅ **The lever remains where V173 puts it**: the **response** path, not the excitation. Reducing `|L|`
attenuates the resonance regardless of how broadband the excitation is — which is exactly why V173
works whether the mode is command-excited or self-excited.
⊕ It also explains the **monotone command scaling** (excess 14.0 → 47.8): more command activity means
more broadband excitation reaching a fixed-frequency mode, **not** more energy at 8.2 Hz specifically.

## 🛑🛑🛑 **RETRACTED: THE CAL ASSOCIATION SCAN IS INVALID AS I RAN IT**
I reported *“a blind cal scan finds the grind's lever”* as a headline. **It does not, and the method
itself is unsound.** Three findings, in the order they emerged:

### 1. It is unstable — a two-label change flipped BOTH verdicts
Correcting `r95` (V102→V101) and adding `r77` (V90) reversed everything: **ratchet 0→2 survivors,
grind 1→0**. `0xC40BC` fell from ρ −0.715 to −0.662, below its threshold.

### 2. Leave-one-out confirms the grind hit was noise
```
   RATCHET  0xC4B58  17/17 leave-one-out subsets   0xC4B5E 13/17   others 3,2,1 / 17
   GRIND    0xC40BC   1/17                          <- the "confirmation" was never stable
```

### 3. 🛑 AND THE STABLE RATCHET HITS ARE ARTEFACTS — THE REGION IS NOT u16 CALS
`0xC4B58` looked convincing at ρ +0.783 and 17/17. But its values across builds are **1443, 1542,
12803, 14022, 14212, 60140, 60141** — jumping with no ordering, which is the signature of a
**mantissa half, not a scalar.** Reading the region as float32 gives absurdities at every alignment
(**−1.43e+26**, denormals like **1.76e−38**), and the raw bytes are plainly packed/structured:
```
   0xC4B50 on V122:  00 3A C4 3A 84 37 ED EA C6 36 BF 00 07 31 44 37 EC EA 24 37 1E 95 60 32
```
⇒ **`0xC4B58` is not a calibration scalar, so correlating it against anything is meaningless.** The
“stable association” is an artefact of slicing packed bytes on a 2-byte grid.

### ✅ WHAT THE ROOT CAUSE WAS, AND WHAT SURVIVES
🛑 **The method assumed every 2-byte-aligned pair in the cal region is a u16 scalar. It is not.**
That region holds floats, packed structures and pointer tables, and the scan silently treated all of
them as numbers. **Every result it produced — for both bands — is withdrawn.**
✅ **What SURVIVES, on its own separate evidence**: `0xC40BC` as the grind's lever. That came from the
**knee sweep**, where the cell was read as the actual relay knee, its values are **sensible and ordered
(300 / 600 / 1800 / 3000)**, and its role is **in the decompiled relay arithmetic**. ρ = −0.69,
p 0.039. **The scan neither confirms nor denies it — it simply never had standing to.**
✅ **V173 is untouched.** Its case is structural throughout: the assist map is the largest torque-fed
term, its cap binds, its section was never retuned, and both gates pass.
⊕ **The fix, if this is ever re-run**: restrict candidates to cells **verified as u16 cals** — by the
knot-count header, by a decompiled read site, or by sensible ordered values — rather than every
aligned pair. `analysis-2020accord/verify/check_lever.py --record` already does that validation.

## 🛑🛑 **I OVER-CORRECTED. THE RATCHET TREND IS UNRESOLVED, NOT ESTABLISHED — AND TWO LABELS WERE WRONG**
Searching memory for **operator verdicts** turned up two hard route→build statements that contradict
labels I had *inferred from filenames*:
- 🛑 **`r95` = V101, NOT V102** — *“V101 flew it at 8× (7128) as route `0x95`, 2026-08-19”*. My
  inference came from `r95_v102_prereg.py`, which is a **pre-registration FOR V102 that used route 95
  as its reference** — not a statement that r95 IS V102.
- ✅ **`r77` = V90** — *“V90 flew as route 77”*. I had **excluded** r77 as unattributable, and it is the
  **richest route in the corpus at 97 windows**.

### 🛑 WITH ONLY HARD ATTRIBUTIONS, MY OWN CORRECTION DOES NOT HOLD
```
                             n    RATCHET post-V102      GRIND post-V102
   session start             5    rho -0.14  p 0.787     rho -0.94  p 0.005
   after enlarging (8 inferred) 11 rho -0.60  p 0.052     rho -0.84  p 0.001
   ALL HARD attributions     8    rho -0.40  p 0.320     rho -0.86  p 0.007
```
✅ **[EVIDENCE] the GRIND trend is ROBUST** — ρ −0.76 to −0.86 across every attribution set tried,
significant in all of them. **That claim stands unchanged.**
🛑 **[UNRESOLVED] the RATCHET trend is NOT robust** — ρ swings **−0.14 → −0.60 → −0.40** with the
label set and is **never significant**. ⇒ **I over-corrected.** *“The ratchet is trending down”* was
as over-stated as *“the ratchet has never moved”* was. **The honest statement is that the ratchet's
build trend is UNRESOLVED at every sample size tried**, while the grind's is settled.
⊕ **What does NOT depend on this**: the ratchet is in torque not wheel rate (19/19 routes),
engaged-only (15/15 vs 6/15 marginal), command-driven (CI excludes zero), and **no varied cal tracks
it** under family-wise control. **V173's case is untouched** — it never rested on the trend.
⚠ **The cal scan used these labels too.** Its ratchet result was a **null** (0 of 94 cells survive),
which two label changes cannot create a survivor from; its grind hit (`0xC40BC`) is worth re-checking
if that cell is ever acted on.

### ⭐ AND V101 PRICES THE 8× GAIN, WHICH IS WORTH HAVING
`r95` is the **8×-gain build** (`0xC6CD0` = 7128), and now correctly labelled it is measurable:
```
   V101 (8x gain)   ratchet 193.2   grind 38.7
   all other builds ratchet  34.5   grind 15.6     (medians)
   => 8x gain: ratchet 5.6x WORSE, grind 2.5x WORSE
```
✅ **This is the first MEASUREMENT behind the standing rule never to raise the LKAS gain**, and it
matches the operator's own report that 8× made grinding worse. **The rule was right and now it has a
number.**

## ⚠ **THE GRIND METRIC WANTS KNEE 1800; THE OPERATOR ALREADY CHOSE 3000. HIS CHOICE WINS.**
`0xC40BC` is the **only** cell surviving a family-wise-controlled scan of 94 varying cals against the
grind, and independently the cell structural reasoning named. So the obvious next question is whether
the flying value has headroom. Plotting the actual shape rather than the correlation:
```
   knee   n   GRIND median   RATCHET median   saturates at |gp-0x6abc|
    300   9      27.4            38.6            25 ct
    600   6       9.5            29.1            50 ct
   1800   2       5.1            12.5           150 ct     <- grind MINIMUM
   3000   1      15.5            38.3           250 ct     <- the FLYING build, worse
```
⚠ **[WEAK] the grind minimum looks like knee ≈ 1800, and 3000 appears to be PAST it.** V112 at 1800
gave the two lowest grind figures in the whole corpus (7.9 and 2.2).
🛑 **But the 3000 point is ONE route** — `r24`, which has **9 windows, the fewest in the corpus** and
therefore the noisiest estimate of any. On that evidence alone I would not move a cell.

### 🛑 AND THE DECISIVE POINT IS NOT STATISTICAL
The flying image is named **`_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST`**. **V122 IS V112's
base with the knee taken from 1800 to 3000, and it is labelled BEST.** The operator has therefore
already driven both values and **chose 3000 on feel.**
✅ **The standing instruction settles it**: *the operator's lived experience overrides analyst
recommendations.* **No build is proposed to revert the knee**, and none should be, on a metric that
disagrees with a decision he made from the driver's seat.
⊕ Worth stating plainly because the temptation is real: the scan makes `0xC40BC` look like the most
defensible lever in the kit, and it is — **for understanding the grind, not for overriding him.**
⊕ It also explains the shape: the knee trades **grind against feel**. Raising it widens the linear
(viscous) region and shrinks the Coulomb one, which is what makes the wheel feel less notchy even
where the 15–25 Hz metric is slightly worse.

## 🛑 **TWO COMMITS CARRY THE WRONG MESSAGE — STALE FILES IN THE JOB TMP DIRECTORY**
🛑 **`068aace3` is titled *“The 511 ceiling is not a hard limit … V132 lifts both”*. Its actual
content is the flash-readiness section of `DRIVE-CARD-V173.md` (30 insertions, one file).** An earlier
commit had the same defect and was caught before pushing.

**Cause, diagnosed:** this job's tmp directory still holds `m7x`/`m8x` message files from a **previous
session** (`m84`–`m89` all present). My pattern of *write a message file, then `git commit -F` it*
silently used **stale content** on any tick where I skipped the write step — `git commit -F m80.txt`
**succeeded** against a V132 message instead of failing as it would have on a missing file.

✅ **Fixed forward, not by force-push.** The bad message is already on `origin`, and its **tree is
byte-identical to what was intended** — verified by `git diff --stat HEAD origin/main` returning
empty. Rewriting pushed history to correct a cosmetic message is not worth the risk, so the record
lives here instead.
⊕ **Message files are now named distinctly** (`msg-<topic>.txt`) and written immediately before use.
⊕ **If you are reading `068aace3` in the log: ignore its title.** It adds the flash-readiness section
to the V173 drive card and nothing else. Nothing about V132 or the 511 ceiling changed in it.

## ✅✅ **BOTH DRIVE-CARD INSTRUCTIONS CONFIRM AT FULL n — AND THE RATCHET CENTRES AT 8.2 Hz, NOT 8.64**
The last two subset results are **operational instructions on the card**, so a wrong one mis-specifies
the drive. Re-tested on **544 windows across 19 routes** (was 244 across 9):
```
   |COMMAND| ct   n win   RATCHET exc   GRIND exc    n=9 was (rat / grd)
   100-250         38      14.0          4.6          17.0 / 5.1
   250-600        137      15.7          8.1          19.4 / 8.5
   600-1500        87      32.4         14.5          39.4 / 12.6   <- grind PEAKS
   1500+          282      47.8          7.0          58.1 / 6.0    <- grind DIES, ratchet grows
```
✅ **[EVIDENCE] the ratchet is MONOTONE in command** (14.0 → 47.8, **3.4×**) ⇒ *“include real
curvature”* stands. ✅ **[EVIDENCE] the grind PEAKS mid-command and DIES above 1500 ct** (4.6 → 14.5 →
7.0) ⇒ *“take the grind verdict from the mid-command windows”* stands.
✅ **And the worst rate band strengthens**: 12–25 deg/s gives ratchet excess **155.2** (was 143.1).

### ✅ THE FREQUENCY IS BETTER PINNED THAN BEFORE — AND SLIGHTLY LOWER
```
   ratchet peak CV:  3.5 % across speed  ·  4.9 % across rate  ·  8.1 % across command
                     (n=9 gave 5.5 % / 12.3 % / 7.0 %)
   peaks across all strata: 7.81 - 9.57 Hz, median ~8.2
   grind peak: 19.92 - 20.90 Hz, tighter still
```
⚠ **The centre is ~8.2 Hz, not the 8.64 Hz quoted throughout this session.** 8.64 came from the
9-route pooled estimate. ⊕ **No design impact**: V173 targets attenuation across **7–11 Hz**, which
brackets 8.2 comfortably (its response there is ≈0.50 against 0.476 at 8.64 — a 5 % difference), and
the notch placement question does not arise because Honda's notch was kept. **The build is unchanged
and the drive card's bands are unchanged.**
⊕ **All three operational results held.** The pattern continues: **effect sizes and shapes survive;
only categorical small-n phrasings have needed correcting.**

## ✅✅✅ **THE CHANNEL RESULT HOLDS — THE ONE THAT MATTERS MOST SURVIVED THE TEST THAT BROKE TWO OTHERS**
Two n≤9 claims had already fallen on the full corpus, so the **channel survey** — the result that set
the scorer's channel and underwrites *“every prior 6–9 Hz endpoint read the wrong channel”* — had to be
re-tested before being trusted further. It was built on **four** routes. On **nineteen**:
```
   channel    routes  mean margin  median   min     n=4 result
   tq         19      28.20        15.52    1.60    7.62
   cs_tq      19      25.80        14.87    1.64    7.42
   ws_fl      19       6.13         6.02    3.74    3.95
   ws_fr      19       5.15         4.91    2.90    4.41
   cs_rate    19       2.60         1.66    0.68    1.03
   ang/wang   19       1.86         1.09    0.39    0.83
   cs_ang     19       1.52         1.16    0.50    0.79
   sc_tq      19       0.92         0.94    0.47    0.56
   co_tqcan   19       0.91         0.85    0.48    0.59
   cc_req     19       0.88         0.82    0.52    0.67
```
✅ **[EVIDENCE] the ordering is unchanged and every margin GREW.** Torque leads the next-best channel
by **5×** (25.8 vs 6.1) and wheel rate by **10×**. ✅ **All three COMMAND channels sit below 1.0 on 19
routes** — the ratchet is not in the command, now on the full corpus rather than four routes.
⇒ **the scorer's channel is right, and the “wrong channel” claim stands.**

### ⚠ ONE PHRASING SOFTENS — the same n≤9 pattern, a third time
I wrote that `cs_rate` scores **“at CHANCE (1.03)”**. On 19 routes it is **2.60 mean / 1.66 median**,
i.e. **above** its null on most routes. **Wheel rate carries a real but ~10× weaker ratchet signal;
it is not at chance.** The operational conclusion is unaffected — scoring the ratchet in `cs_rate`
would still be measuring the weakest usable channel with a floor it barely clears — but the wording
was a small-n overstatement, exactly like the other two.
⊕ **Three for three**: every claim of mine that has needed correcting was a **categorical statement at
n≤9** (*“never moved”*, *“absent in manual”*, *“at chance”*). **Every effect SIZE has held or grown.**

## 🛑 **CORRECTION 2: “ENGAGEMENT *CREATES* THE RATCHET” IS TOO STRONG — IT AMPLIFIES IT ~15×**
The same corpus enlargement that corrected the build-trend claim also softens the engaged/manual one.
```
                          n=7 (earlier)          n=15 (full corpus)
   engaged clears null     7/7                    15/15
   manual  clears null     0/7                    6/15        <- NOT zero
   speed-matched ratio     19.9x [4.82, 35.64]    15.1x [6.0, 38.9]   (n=12 matched)
```
🛑 **[EVIDENCE] the manual arm clears its slope-matched null on 6 of 15 routes**, where the
9-route subset gave 0 of 7. ✅ **But it clears MARGINALLY in 5 of those 6** — 3.3 vs 2.8, 2.7 vs 2.5,
2.3 vs 2.2, 3.8 vs 2.7, 2.9 vs 2.4 — with only `r21` clearly above (8.2 vs 4.7). Meanwhile the
**engaged arm clears 15/15, usually by 10–100×** (up to 339.3 vs 2.7 on `r82`).
⇒ **the right statement is that engagement AMPLIFIES the ratchet by ~15×, not that it CREATES it.**
The mode is faintly present in manual driving and enormously larger when engaged.

### ✅ WHAT THIS CHANGES
⊕ **The ratio TIGHTENS**: 15.1× **[6.0, 38.9]** on 12 matched pairs, against 19.9× [4.82, 35.64] on 4.
Same magnitude, better bounded.
⊕ **The drive endpoint is unaffected.** Engaged sits at 12–339 against a null near 2–5, so the
presence/absence reading holds with an enormous margin; the manual arm was only ever a control.
🛑 **But the MECHANISTIC claim changes.** *“Firmware-created”* implied the mode does not exist without
the loop. It does — faintly. The loop **amplifies an existing mode**, which is exactly the `1−P·L`
picture and is if anything **more** consistent with the account than outright creation would be.
⊕ **No build changes.** V173 reduces `|L|`, which is the amplification.

### ⚠ THE PATTERN IN BOTH CORRECTIONS
Both claims that fell were **presence/absence statements made at n≤9, and both fell in the direction
of my own hypothesis** — *“never moved”* and *“absent in manual”* were the strong readings, and the
full corpus made each one weaker. **Small-n presence/absence claims are the failure mode to watch for
here**, not the effect sizes, which have held.

## ✅✅✅ **THE CORPUS WAS TWICE WHAT I WAS USING — AND IT CLOSES THE DRIVEN/SELF-EXCITED QUESTION**
🛑 **I had been scoring 9 routes. There are 19** whole-route caches carrying the core channels, and
several hold far more engaged-creep windows than anything I used — **`r77` has 97 against `r1e`'s
42.** (The `sNN` entries are per-segment sub-caches of the same drives, so they are not independent
and are excluded.) **Nothing was wrong with the analysis; I simply never enumerated the cache.**
```
   ratchet, all 19 routes, cs_tq, excess / slope-matched null
     r78 12.2/2.2   r7e 31.0/2.0   r7f 39.2/2.3   r96 38.6/2.7   ra4 23.3/1.9
     ra6 29.0/1.9   r1e 21.0/1.9   r22 20.6/2.5   r24 38.3/3.2
     r21 27.2/1.9   r77 20.2/1.6   r79 11.5/2.0   r81 243.7/2.4  r82 237.2/2.3
     r85 58.7/2.8   r95 193.2/2.5  r97  4.4/2.5   r9e 38.1/2.4   ra5 84.6/2.3
   => REAL on 19 of 19 routes.  Peak 7.42-10.16 Hz, consistent with the 8.64 Hz estimate.
```

### ✅ AND THE ONE OPEN QUESTION THAT NEEDED POWER IS NOW ANSWERED
At n = 7 the driven-vs-self-excited test was **inconclusive** — specific on 6/9 routes but the pooled
CI **[−0.021, +0.176] crossed zero**. Same statistic, more data:
```
   band-specific coupling = coherence(7-10.5 Hz) - coherence(30-40 Hz control),
   command -> cs_tq, vs phase-shuffled surrogates.   n = 17 routes

     median specificity  +0.1148
     95 % CI             [+0.0274, +0.1682]      <- EXCLUDES ZERO
     individually specific on 10 of 17
     specificity vs window count: rho +0.31 (p 0.226)
```
✅ **[EVIDENCE] THE RATCHET IS DRIVEN BY THE COMMAND, not self-excited.** The CI excludes zero, and
the positive window-count trend is exactly what an underpowered *real* effect predicts — which is what
`r1e` hinted at when it was the only well-powered route.
⚠ **Not universal**: three routes (`r85`, `r95`, `r97`) show *negative* specificity. The claim is
about the population, not every drive.

### ⭐ WHAT IT CHANGES, AND WHAT IT DOES NOT
⊕ **V173 works either way.** The assist map amplifies whatever reaches the bar, so attenuating it at
8.64 Hz reduces the ratchet whether the excitation is the command or the loop itself. **No build
changes.**
⊕ What it *does* change is **what a null on the drive would mean**: with the ratchet established as
command-driven, a null could no longer be explained by "the excitation was absent on that pass" — the
pass carries command by construction. **It sharpens the pre-registered outcomes rather than altering
them.**
⊕ And it retires an open item that was recorded as *“closes with more continuous windows”*. **It did.**

## ❌ **RING-DOWN DOES NOT TEST THE `P·L` ASSUMPTION EITHER — AND MY FIRST CONTROL WAS VACUOUS**
The last idea for testing `P·L` without driving: a **time-domain** ring-down, immune to the spectral
tilt that killed the other estimators, and the one measure the kit's record says *“passed its
control”*. Since `ζ_eff = ζ_passive · |1−P·L|`, a decay rate that differs across builds would test the
account from data already in hand. Trigger: an abrupt command collapse, then fit the 8.64 Hz envelope
over 0.5 s of free decay.

### 🛑 MY FIRST CONTROL COULD NOT HAVE WORKED
I controlled by fitting the **time-REVERSED** envelope, reasoning that a genuine one-sided decay would
fit worse backwards. It returned **0.64/0.64, 0.61/0.61, 0.80/0.80 … identical on every route** — the
tell. **Reversing a linear fit's x-ordering flips the slope but leaves the residuals unchanged, so r²
is invariant BY CONSTRUCTION.** The control could never discriminate anything. Replaced with the same
fit on engaged segments that have **no** command collapse.

### ❌ AND WITH A REAL CONTROL, THE MEASUREMENT IS TOO WEAK TO USE
```
   route build  alpha 1/s  zeta     Q      CONTROL  verdict
   r78   V91      2.65     0.0489   10.2    2.12    no better than control
   r7e   V96      3.14     0.0579    8.6    2.16    no better than control
   r7f   V96      4.92     0.0906    5.5    1.80    DECAY
   r96   V102     3.40     0.0626    8.0   -0.95    control NEGATIVE -- nonsense
   ra4   V104     4.13     0.0761    6.6    1.51    DECAY
   ra6   V106     3.96     0.0729    6.9    1.59    DECAY
   r1e   V107     1.17     0.0216   23.2    1.62    no better than control
   r22   V112     4.82     0.0888    5.6    1.95    DECAY
   r24   V122     4.49     0.0827    6.0    1.35    DECAY
```
❌ **It clears its control on only 6 of 9 routes, and by 1.5–3.3x** — the decay alphas (1.17–4.92)
**overlap the control alphas (1.35–2.16)** heavily. ❌ **One route's control is NEGATIVE (−0.95)**, i.e.
its no-collapse envelopes *grow* on average, which invalidates the control there outright.
❌ **ζ = 0.022–0.091 does not match the kit's recorded ring-down ζ = 0.017–0.036** except at the
extreme. ❌ **And there is no build ordering**: V91 2.65 · V96 3.14/4.92 · V102 3.40 · V104 4.13 ·
V106 3.96 · V107 1.17 · V112 4.82 · V122 4.49.
⇒ **the ring-down carries no usable damping information at engaged creep in this corpus.**

### ✅ WHAT THIS SETTLES
**Three independent estimator families have now been tried on the `P·L` question and all three fail**:
frequency-domain Q (tilt-confounded), the slope-corrected excess stratified by torque (confounded by
rate, structurally), and now time-domain ring-down (does not clear its own control). **The assumption
is testable only by intervention.** That is no longer a judgement — it is a result, and this closes
the line for good.

## ✅ **TOOL AUDIT: ONE MORE LIVE HAZARD FOUND AND CLOSED**
Having found the primary scorer reading the wrong channel, I audited **all 43 scoring tools** for the
same defect — a ratchet or grind endpoint computed on `cs_rate`, where the ratchet scores at chance.
✅ **No other tool has that defect.** Every remaining ratchet/grind endpoint either reads `cs_tq`,
sweeps channels deliberately, or is a probe-specific scorer with its own anchor.

🛑 **But the audit found a different live hazard**: `docs/scoring/DRIVE-CARD-V158.md` and
`SCORING-V158-preregistered.md` still pointed at **`score_v158_creep.py`**, the scorer this session
**superseded**. Had V158 been flown from its own card, the drive would have been scored with:
- **half-power Q of the 15–25 Hz peak** — withdrawn, NON-MONOTONE (its null sits *above* the data);
- **Q at 5–12 Hz** — withdrawn, a WINDOW artefact (white noise alone returns Q 21.7–29.1);
- **fixed-floor prominence** — withdrawn, large by construction on a red spectrum;
- **non-continuous windows**, where the validated estimator requires continuous runs;
- and **`cs_rate`**, before the channel finding.
✅ **Closed three ways**: the tool now carries a superseded banner **and raises on import** so it
cannot be used by accident; both documents are redirected to `score_band_excess.py`; and no document
outside STATE's own retraction text mentions it any more.

⊕ **The pattern worth keeping**: the defect was not in the analysis, it was in the *plumbing between
the analysis and the drive*. Both instances were found by **running the drive card's own command
verbatim** rather than by reading the code. That check is cheap and it belongs in every close-out.

## 🛑✅ **THE SCORER WAS READING THE WRONG CHANNEL — CAUGHT BY RUNNING THE DRIVE CARD'S OWN COMMAND**
With the design closed, I ran the pipeline end-to-end exactly as it would run on a fresh route. It
found a defect that would have produced a **wrong verdict on the drive**.
```
   score_band_excess.py  read  z['cs_rate']
   but cs_rate scores at CHANCE for the ratchet: margin 1.03 vs cs_tq's 7.42
```
🛑 **[EVIDENCE] the tool the drive card points at was measuring the ratchet in the one channel
where it is not present.** Fixed to `cs_tq`, and the numbers now match the analysis they came from:
```
   r24 / V122, cs_tq        BEFORE (cs_rate)      AFTER (cs_tq)
     ratchet 5-12 Hz          4.4x                 33.2x     split-half 1.21x
     grind  15-25 Hz         23.2x                 14.0x     split-half 3.29x
```
⊕ Note the split-halves **swap**: the ratchet is now the *tighter* endpoint (1.21x) and the grind the
looser (3.29x). That is the right way round — the ratchet is what the channel is good for.

### ✅ AND THE DRIVE CARD'S TWO DISCRIMINATORS ARE NOW IN THE TOOL
One command gives the whole verdict instead of three hand-run analyses:
- **grind sub-bands 15–20 vs 20–25 Hz** — V173's filter attenuates the top **2.2x** more (sloped),
  V158's damper is dose-set and flat ⇒ the SHAPE says which lever produced a reduction.
  Reference measured on the flying build: **15–20 = 5.8x, 20–25 = 14.0x, ratio 2.39.**
- **grind vs ratchet by COMMAND level** — the grind saturates above 1500 ct while the ratchet grows,
  so the two verdicts come from different strata.
⊕ **Both carry an 8-window guard.** On r24 the strata hold 0 and 4 windows and now print *“TOO FEW to
report”* rather than the 198x / 1270x the unguarded version emitted — those came from a background
fit on four windows and were **not credible**. Catching that in the tool is the point of running it
before the drive rather than after.

## ✅✅✅ **EVERY REMAINING LEVER IS BELOW THE MEASUREMENT FLOOR — V173 IS THE WHOLE AVAILABLE FIX**
Pricing what is left after V173, with the corrected `L_other` (r26 gated off ⇒ 0.31–0.55, not 0.825).
Anchor unchanged in kind: the measured `Q_eff/Q_passive = 14.3` fixes `P·L = 0.93`, so `P = 0.93/|L|`.

### ✅ FIRST, THE PREDICTION SURVIVES MY OWN CORRECTION
```
   L_other   P        stock Q   V173 Q   V173 gain
   0.825     0.3292   14.29     2.45     5.8x     <- census value, now known WRONG
   0.550     0.3647   14.29     2.25     6.4x
   0.430     0.3827   14.29     2.16     6.6x     <- corrected, mid
   0.310     0.4026   14.29     2.07     6.9x
```
✅ **[EVIDENCE] V173's predicted effect is INSENSITIVE to the r26 error**: 5.8x at the wrong value,
6.9x at the low end of the right one. **The correction moves the prediction the RIGHT way and by
less than its own uncertainty.** That is the robustness check the earlier numbers lacked.

### 🛑 AND EVERY REMAINING LEVER IS UNMEASURABLE
```
   marginal gain ON TOP of V173 (L_other = 0.43)     new |L|   Q ratio   vs V173
     nothing (V173 alone)                             1.403     2.16      1.00x
     kill the PID entirely                            1.146     1.78      1.21x
     kill r24 entirely                                1.232     1.89      1.14x
     kill PID AND r24 together                        0.975     1.60      1.35x
     add the slope cap 1536 (V168's lever)            1.159     1.80      1.20x
     add the slope cap 1024 (V171's dose)             0.916     1.54      1.40x
```
🛑 **[EVIDENCE] the single-episode split-half floor is 1.63x.** Every entry above is **at or below
it** — so none of these could be distinguished from noise on a drive **even if built and even if the
model is exactly right.**
⇒ **V173 captures essentially all the available loop-gain reduction.** The assist map is the loop, and
V173 is the assist map's lever.

### ✅ WHAT THIS CLOSES, AND WHY NO EIGHTH BUILD
**The analysis is complete.** Not “out of ideas” — *priced*, and every remaining idea is worth less
than the noise on the only measurement available. Building another would be adding a variable that
cannot be read.
⊕ The three named symptoms now stand as: **ratcheting** → V173 (6.6x predicted) · **grinding** →
V158's damper + V173's filter, on the same build · **command oscillation** → shares the grind's band
and lever · **LKAS authority** → measured, not limiting, no lever needed.
⊕ **The next information can only come from the car.** Seven builds, one decision table
(`docs/scoring/BUILD-INVENTORY.md`), one continuous 15-second engaged creep pass with real curvature.

## ❌ **r26 IS ALREADY GATED OFF ENGAGED — NO LEVER THERE, AND MY LOOP DECOMPOSITION OVERCOUNTED**
Looking outside the assist lane: after V173 the assist map is ~54 % of `|L|` and the
engagement-conditional terms ~46 %. The census lists **r26 at 0.098–1.17**, potentially the largest
of those, *“LIVE only while `gp-0x6b5e == 0`”* — a **GATE, not a gain**, and one never examined
(`0xC6444` is falsified on-car but that was a MAGNITUDE cut with the gate still open).
```
   FUN_000361c8, the sole producer (writers 0x36256 / 0x36264, both st.h):
     gp-0x6b5e = +/- POL * ( LERP(gp-0x6bda) * cal(0xC63C2) ) >> 10

   X knots 0xC66CE: [-384, -128, 128, 294, 384, 0]      scale 0xC63C2 = 1024 (unity)
   Y knots 0xC66D8: [   0, 4762, 4762, 717,   0, 0]

   engaged, gp-0x6bda == 0.0000 over 75,227 frames  =>  0 falls in segment [-128, 128]
   =>  LERP returns 4762  =>  gp-0x6b5e = +/-4762   NON-ZERO
```
❌ **[EVIDENCE] r26 is ALREADY gated OFF during engaged creep.** The gate this line was chasing is
**already closed by Honda**, so there is no lever here and `0xC66D8`/`0xC63C2` need not be touched
(both byte-identical across all 167 images).
🛑 **AND IT CORRECTS MY OWN NUMBERS**: I have been carrying the census's **`L_other` = 0.825**,
derived as `2.825 − 2.0`, with r26's 0.098–1.17 inside it. **If r26 is gated off engaged, that figure
overcounts the engaged loop** — the remaining terms are PID 0.2565 + r24 0.049–0.293 + `FUN_00036682`
0.0032 ≈ **0.31–0.55**, not 0.825.
⊕ **This does NOT change the lever choice**: every build's predicted effect was computed as a RATIO
against the same anchoring, and a smaller `L_other` makes the assist map an even LARGER share of the
loop — it strengthens the case for V173 rather than weakening it. But **the absolute Q-ratio figures
carry more uncertainty than their two decimal places suggest**, and that is now on the record.
⚠ **Blast radius, for the record**: `gp-0x6b5e` has **4 readers** — `0x36390`, `0x3AA8E` (the
aggregator), and **`0x4DA92` / `0x4DFAE` outside it**. Had the gate been open, closing it would NOT
have been the clean single-consumer edit `gp-0x6b86` was.

### 🛑 THE tp OFF-BY-0x1000 TRAP RECURRED — EIGHTH RECORDED TIME, CAUGHT BY THE SHAPE
My first read used **`0xC76CE`** instead of `tp+0x76ce` = **`0xC66CE`**, and returned
`X = [15, 4100, 15, 4102, 15, 4104]` / `Y = [4104, 15, 4106, 15, 8192, 15]`. **The interleaved 15s
were the tell** — a knot table is monotone, not alternating — exactly as *“the denormals were the
tell”* on the sixth recurrence. It produced the **opposite conclusion** (apparently “gated off”, by
luck, from entirely the wrong cells). **Anchor first, then read; and check the SHAPE of what comes
back.**

## ✅ **V173 IS ON THE EFFICIENT FRONTIER — THE DESIGN WORK IS COMPLETE**
With Honda's notch fixed and the structure known to separate, the design reduces to choosing **one
real pole pair**. Sweeping every pair that holds DC within 2 % of unity and never amplifies:
```
   added lag   8.64 Hz   3 Hz     poles        21 Hz
     30.1 ms    0.4761   0.8476   0.970/0.475  0.1894   <- V173 AS BUILT
     30.1 ms    0.4691   ~0.85    0.970/0.75   ~0.17    <- best possible at that lag
     46.6 ms    0.3383   0.7285   0.980/0.60   0.1253
     54.6 ms    0.2832   0.7507   0.975/0.95   0.0584
```
✅ **[EVIDENCE] V173 is at the frontier**: the best achievable at its own 30.1 ms lag is **0.4691**
against V173's **0.4761** — a **1.5 %** difference, far inside any measurement floor. Its pole pair was
*inherited* from V172 rather than chosen, and it happens to be essentially optimal. **No rebuild.**
⊕ **The trade is priced if more is wanted**: **0.338 at 46.6 ms** or **0.283 at 54.6 ms**, i.e. buying
another 1.4–1.7x of ratchet attenuation costs 16–25 ms of additional assist lag. That is a **feel**
decision, and it is the operator's — the builds are one coefficient triple away if he wants one.

### ✅ WHAT THIS CLOSES
Design work on the assist lane is **finished**. Both lever classes are cut and verified, both gates
are closed, every artifact re-hashes from disk, and the remaining assumption is testable only by
driving. **Seven builds, one decision table, one 15-second pass.**

## 🚩✅ **V173 BUILT AND SUPERSEDES V172 — THE SAME LEVER WITHOUT GIVING UP HONDA'S NOTCH**
```
   V173 = V158 + THREE float32 cells (C_A8, C_AC, C_B4).  C_B0 left BYTE-IDENTICAL to stock.
   image  a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7
   .rwd   5d213cf8604df90f2df2eaa2a8e40ccedde89f1d66055cb2a22c81edb7245396
   11 payload bytes + one CRC trailer - 25/25 assertions - chain 50/50 - readback identical
```

### ⭐ THE STRUCTURE, COLLAPSED — AND IT SEPARATES
```
   H(z) = C_B4 * ( z^2 + C_B0*z + 1 ) / ( z^2 + C_A8*z + C_AC )
```
✅ the numerator's roots have **product 1** ⇒ the zeros are **always exactly on the unit circle**, so
this is **always a true notch**, at `2 cosθ = −C_B0` ⇒ **`C_B0` ALONE sets the notch frequency.**
✅ the poles are set by `C_A8`/`C_AC` **alone** ⇒ **notch frequency and damping are INDEPENDENT.**
✅ `DC gain = C_B4 (2 + C_B0) / (1 + C_A8 + C_AC)`.

### 🛑 WHICH EXPOSED A DEFECT IN V172
Stock `C_B0` puts Honda's notch at **55.23 Hz, −43.9 dB**. **V172 moved it to 27.17 Hz** as a side
effect of letting an optimiser choose all four coefficients ⇒ **V172 gives up Honda's 55 Hz notch
entirely** (0.000128 → 0.251316 there). **We do not know what that notch is FOR**, and Honda placed a
deep null at a specific frequency in the dominant assist lane deliberately.
✅ **V173 keeps `C_B0` bit-for-bit and moves ONLY the poles:**
```
   freq        FLYING      V172        V173
   0.5 Hz      0.999965    1.006656    0.994633     DC preserved
   3   Hz      0.997530    0.850073    0.847560     driver band -- same as V172
   8.64 Hz     0.978950    0.444078    0.476076     THE RATCHET -- same as V172
   21  Hz      0.865930    0.090235    0.189446     grind 4.6x (V172 got 9.6x)
   40  Hz      0.452204    0.134765    0.054184     better than V172
   55.23 Hz    0.000128    0.251316    0.000013     ** HONDA'S NOTCH KEPT, and deeper **
   group delay added at 0.5 Hz: V172 +30.1 ms, V173 +30.1 ms -- IDENTICAL (same poles)
   loop effect: V173 5.8x vs V172 6.1x - max |H| to Nyquist 0.9946 => NEVER amplifies
```
⇒ **same lag, same ratchet effect, Honda's notch preserved, and THREE cells instead of four.**
The trade is **half the grind attenuation**, which is the right side to err on: the ratchet is the
**unsolved** symptom and both builds are equal there, while the grind **already has V158's damper on
this same base.**

### ❌ WHY THE NOTCH CANNOT BE PUT ON THE RATCHET — STRUCTURAL, NOT AN OPTIMISER FAILURE
`C_B4 = DC(1+C_A8+C_AC)/(2+C_B0)` and `2+C_B0 = 2−2cosθ → 0` as the notch approaches DC, so **`C_B4`
scales as ~1/f²**:
```
   notch  8.64 Hz => C_B4 13.576 => amplifies out-of-band 1503x
   notch 27    Hz => C_B4  1.393 => amplifies 120x
   notch 55.2  Hz => C_B4  0.336 => amplifies 1.0x   <- Honda's placement, the ONLY free one
```
⇒ **Honda put the notch at 55 Hz because that is where it costs nothing.** A notch at the ratchet
needs 13.6x input gain and amplifies everything else. **The POLES, not the notch, are the lever in
the ratchet band.**
🛑 **I withdraw my remark that the optimiser “was fighting a structure it did not understand”** — it
found the right shape for the right reason; the defect was only the notch it displaced.

### 🛑 AND A CORRECTION TO MY OWN NOVELTY CLAIM
I wrote that this session **“RETRACTS two recorded claims — ‘no frequency-selective lever’ and ‘no
notch filter exists’”**. **`MEMORY-PART5` already carries that retraction**, in detail, with the same
four coefficients, the ±19.88° zeros and the “transparent except at the notch” observation.
**The kit found this first; I re-derived it without checking.** That is exactly the failure the
`feedback-search-the-kit-before-naming-a-cause` memory exists to prevent.
⊕ What IS new here: the **collapsed transfer function** and its separability, the **1/f² bound on
notch placement**, the **task-rate resolution** below, and the **built lever**.

### ✅ AND IT UNBLOCKS WHAT THAT MEMORY WAS PARKED ON
`MEMORY-PART5` records this lever as **“BLOCKED ON THE TASK RATE — task 5 is bounded ≥250 Hz but
NEVER pinned”**, with the notch landing anywhere from 13.8 to 55.2 Hz depending on the rate.
✅ **[EVIDENCE] `get_function_callers(0x352b4)` returns exactly `FUN_0002214a`**, which the kit's own
record identifies as **TASK 1, the CONFIRMED 1 kHz task**. The rate uncertainty belongs to **task 5**
(`FUN_00022ca0`), a **different** task that drives the damper. ⇒ **the assist section runs at 1 kHz,
the notch is at 55.23 Hz, and the block is lifted.** Confirmed independently: a full-band scan finds
the flying section's null at **55.0 Hz, −43.9 dB**, matching the ±19.881° zeros exactly.

## ✅ **SAME CLASS, DIFFERENT DRIVE LAW — THE GRIND SATURATES WHERE THE RATCHET KEEPS GROWING**
Both symptoms are engaged-only and both sit in `cs_tq`, so the question was whether they are one
mechanism at two plant modes. **Mostly yes — with one clean difference that matters for scoring.**
```
   244 pooled windows, each assigned to a stratum by its OWN mean operating point

   |COMMAND| ct    n win  |  GRIND Hz  excess  |  RATCHET Hz  excess
   100-250          23    |   19.14     5.1    |    9.57       17.0
   250-600          75    |   19.73     8.5    |    8.59       19.4
   600-1500         46    |   20.12    12.6    |    8.01       39.4
   1500+           100    |   19.14     6.0    |    8.20       58.1

   FREQUENCY   grind CV 9.6 % (speed) - 11.0 % (rate) - 2.1 % (command)
               ratchet CV 5.5 %       -  12.3 %       - 7.0 %
```
✅ **[EVIDENCE] both are FIXED-FREQUENCY** — neither peak moves materially with operating point, so
both carry the `1−P·L` signature of a plant mode whose damping the loop is cancelling. The grind's
**2.1 % CV across command** is the tightest figure either symptom produces.
🛑 **[EVIDENCE] but their DRIVE LAWS differ**: the ratchet is **MONOTONE in command (3.4x)** while
the grind **peaks mid-command (12.6 at 600–1500) and FALLS at high command (6.0 at 1500+)**.
⊕ That non-monotonicity is **consistent with the kit's own recorded fact** that *“saturation
suppresses it 141x”* — at high command the loop rails and the resonance is suppressed. The grind sits
at a higher frequency, so the same command amplitude produces a larger rate and rails sooner.
⚠ **[BELIEF, not EVIDENCE]** the saturation explanation. The drop is 12.6 → 6.0 across strata of 46
and 100 windows; it is a real pattern but a single-drive artefact is not excluded.

### ⭐ THE SCORING CONSEQUENCE, FREE FROM THE SAME EPISODE
The two symptoms are **best read at DIFFERENT command levels**:
```
   RATCHET   strongest at HIGH command (1500+)      excess 58.1
   GRIND     strongest at MID command (600-1500)    excess 12.6, and DIES above it
```
⇒ a pass that spends all its time at high command will read the ratchet well and **under-read the
grind**. **A slow lap with varied curvature covers both**, which is what the drive card already asks
for — this says *why*, and it means the grind verdict should be taken from the mid-command windows
rather than pooled across the whole pass.
⊕ Added to the V172 drive card.

## ✅✅ **THE GRIND IS ENGAGED-ONLY TOO — AND A SUB-BAND SPLIT ATTRIBUTES IT**
Both levers on the fly-first build act at 15–25 Hz, so a grind change needs attributing. The obvious
discriminator — V158's damper is **engaged modes 26/27 only** while V172's filter is **always
active** — would work if the grind existed in manual. **It does not.**
```
   GRIND 15-25 Hz, engaged vs MANUAL creep, slope-matched nulls
     r78  V91    engaged   6.1 / 3.5    manual  2.3 / 3.8    no
     r7e  V96             28.9 / 3.2            2.2 / 4.8    no
     r7f  V96             14.3 / 3.5            2.2 / 3.9    no
     r96  V102           248.2 / 4.0            1.5 / 4.9    no
     ra6  V106            25.3 / 4.0            3.0 / 3.9    no
     r1e  V107            27.7 / 2.7            1.6 / 4.5    no
     r24  V122            14.0 / 3.9            1.9 / 4.1    no
   => the grind clears its null in MANUAL on 0 of 7 routes
```
✅ **[EVIDENCE] the GRIND is engaged-only, exactly like the ratchet** (also 0/7 in manual).
⇒ **both symptoms are FIRMWARE-CREATED BY ENGAGEMENT**, not mechanical modes being amplified. They
differ in frequency and in which levers move them, **not in class**. **This is new** — the ratchet was
established engaged-only earlier this session; the grind had never been tested the same way.
❌ And it kills the manual-arm discriminator: neither symptom exists there to compare.

### ✅ WHAT DOES DISCRIMINATE: THE SHAPE ACROSS THE BAND
V172's filter attenuation is **frequency-SLOPED**; V158's damper adds a rate-proportional term whose
effect is set by the dose, not the frequency, so it is roughly flat across 15–25 Hz.
```
   V172 attenuation:  15 Hz 0.2298 - 17 Hz 0.1828 - 19 Hz 0.1415
                      21 Hz 0.1042 - 23 Hz 0.0694 - 25 Hz 0.0359
   mean 15-20 Hz 0.1737   vs   mean 20-25 Hz 0.0784
   => V172 attenuates the TOP of the band 2.21x more than the bottom
```
⭐ **DISCRIMINATOR, free from the same episode**: score the grind excess in **15–20** and **20–25**
separately.
- **20–25 falls much more than 15–20** ⇒ **V172's filter did it.**
- **both fall about equally** ⇒ **V158's damper did it.**
⊕ Added to the V172 drive card.

## ✅ **GATE 1 PASSES FOR V172 — `gp-0x6b86` HAS EXACTLY ONE CONSUMER, AND IT IS NOT A MONITOR**
V172 low-passes the assist map's output hard (**21 Hz down 9.6x, 40 Hz down 3.3x**). The aggregator
consuming it is fine with that — it is a torque contribution. **The risk was a MONITOR**: a
stuck-signal, rate-of-change or plausibility check that expects the value to keep moving, since
heavily low-passing a watched signal can look like a frozen sensor. Raw LE byte scan across **both**
gp encodings (operand-text search undercounts and cannot see register-indirect access at all):
```
   gp-0x6b86  4 accesses, ALL accounted for
     0x35AB6  ld.h        }  inside FUN_000352b4 -- the producer's own lockstep compare
     0x35AC0  st.h        }  the write
     0x35ACE  st.h r0        the store-zero (the out-of-range branch)
     0x3AC7C  ld.h           FUN_0003aa2c, THE AGGREGATOR -- the only consumer outside the producer

   gp-0x4cde  3 accesses -- the lockstep SHADOW, all inside the producer, written in step
```
✅ **[EVIDENCE] exactly ONE consumer outside the producer, and it is the torque sum this build
intends to change.** No monitor, no plausibility checker, no rate-of-change watchdog reads it.
⇒ **GATE 1 (RAM ownership) PASSES**: heavily filtering this signal cannot trip a fault path,
because nothing is watching it for liveness.
⊕ The lockstep shadow is unaffected by a coefficient change — the value is still written to both
cells in the same instruction pair, so the pairing that trips `FUN_0006b9fa` is preserved.
⊕ The same clearance covers V168, which changes only how the value is COMPUTED, not who reads it.

## ⚠ **THE `P·L` ACCOUNT CANNOT BE TESTED FROM THE EXISTING DATA — THE DRIVE IS NECESSARY**
The account makes one prediction that looked free to check: the assist map's local slope **falls
steeply along its own curve** (6.16 → 0.86 → 0.01, capped at 2.000 below X≈100), so if that slope is
the dominant term in `L`, the ratchet should **weaken at higher driver torque**. No other account has
to predict that.
```
   raw stratification by |driver torque|
     |tq| 80-150    n= 49   map slope 1.807   excess  10.7   |cmd|  303   |rate|  2.4
     |tq| 150-300   n= 34   map slope 0.768   excess  22.9   |cmd|  393   |rate|  6.0
     |tq| 300+      n=161   map slope 0.140   excess  44.2   |cmd| 1946   |rate| 35.4
     excess vs map slope rho -1.00   -- the WRONG sign, but |cmd| and |rate| are rho +1.00
```
❌ **The confounds are perfectly aligned with the stratum**, so the raw test is uninformative.
Stratifying torque WITHIN narrow command bands splits 2-supporting / 1-contradicting — but that is
**also fully explained by the rate confound alone**: excess peaks at **12–25 deg/s and FALLS above
it**, and the two “supporting” rows have mean rates of **40.6 and 59.7** (past the peak) while the
“contradicting” row runs **2.4 → 7.0** (climbing toward it).
🛑 **[INCONCLUSIVE] — and structurally so.** Driver torque, command and wheel rate are all driven by
how hard the wheel is being worked, so **observational data cannot separate the map's slope from the
rate**. This is not a power problem that more windows would fix. **Recorded so it is not re-attempted.**
⇒ **the `P·L` real-positive assumption is testable only by intervention** — i.e. by flying V172 or
V168 and seeing whether the peak moves. That is exactly what the pre-registered outcomes cover, and it
is why no further static analysis is being done on this question.

## ✅ **DO NOT STACK THE TWO LEVERS — AND V172 ALREADY PASSES THE TARGET**
```
   build                        eff s   |L|     Q ratio   vs stock
   STOCK / flying               2.000   2.825   14.29     1.0x
   V169  cap 1792               1.750   2.575    6.57     2.2x
   V168  cap 1536               1.500   2.325    4.26     3.4x
   V170  cap 1280               1.250   2.075    3.16     4.5x
   V171  cap 1024               1.000   1.825    2.50     5.7x
   V172  filter retune          0.907   1.732    2.33     6.1x
   V172 + cap 1536 (stacked)    0.680   1.505    1.98     7.2x
   V172 + cap 1024 (stacked)    0.454   1.279    1.73     8.3x
```
❌ **[EVIDENCE] stacking is a bad trade**: the cap on top of V172 buys **1.17x** (1536) or **1.35x**
(1024) while adding the **FULL static weight cost**. ⊕ V172's build asserts the cap is stock, so the
two cannot be stacked by accident.
✅ **[EVIDENCE] V172 alone already passes the target**: a Q ratio of 3.0 needs `|L| ≤ 2.025`, and
V172 leaves **1.732**.

### ⭐ WHAT A THIRD LEVER WOULD HAVE TO BE
After V172 the loop splits **52 % assist map / 48 % everything else**, and "everything else" is the
census's **engagement-conditional** terms — PID 0.2565, r24 0.049–0.293, r26 0.098–1.17 (live only
while `gp-0x6b5e == 0`), `FUN_00036682` 0.0032.
⇒ **a third lever must come from those, not from the map.**
🛑 **But it is NOT worth starting before a drive result.** Two independent levers already exceed the
target on paper; **which of them the car actually responds to is the one thing no further analysis can
settle**, and both rest on the same `P·L` assumption that a single pass tests. Six builds are cut and
only one can fly at a time — **more builds now would be speculation, not progress.**
⊕ Consolidated into `docs/scoring/BUILD-INVENTORY.md`: the decision table, the hashes, and what each
outcome licenses.

## 🚩 **FLIGHT ORDER REVISED — V172 FIRST. MY “130 ms LAG” WAS THE WRONG METRIC.**
I recommended V168 first on the grounds that V172 added *“~130 ms”* of lag. **That figure was the
STEP SETTLING TIME, which is not what a driver feels** — settling is dominated by the slowest pole's
tail regardless of whether any signal energy is there. The right metric is **group delay in the band
the driver actually steers in**:
```
   freq       FLYING     V172       ADDED LAG
   0.5 Hz     3.8 ms     33.9 ms    +30.1 ms
   1   Hz     3.8 ms     32.9 ms    +29.1 ms
   3   Hz     3.8 ms     25.1 ms    +21.4 ms
   5   Hz     3.8 ms     17.3 ms    +13.5 ms
   8.64 Hz    3.9 ms      9.3 ms     +5.4 ms
```
✅ **[EVIDENCE] the real added lag is +30 ms, not +130 ms**, and it FALLS with frequency. 30 ms is at
the low end of what is usually reported as noticeable in steering feel.
⇒ **V172's risk is materially lower than I stated, and the recommendation changes.**

### ⭐ WHY V172 NOW GOES FIRST
```
             predicted ratchet   also grind?   what it costs
   V168      3.4x                no            heavier NEAR CENTRE, uniformly, always
   V172      6.2x                9.6x          +30 ms group delay; 3-5 Hz content down 15-32 %
```
✅ **The operator's standing constraint is explicitly about apparent MASS AND FRICTION** — *“low
apparent steering mass and friction to LKAS”*. **V168 raises exactly that, uniformly. V172 leaves it
untouched** (DC gain 1.0067). ✅ **And V172 is the only lever that also attacks the grind.**
⇒ on both the operator's own stated axis and on predicted effect, **V172 is the better first flight.**
⊕ **V168 and its ladder remain cut and ready** as the alternative if V172's lag is the problem.

### ❌ A PROTECTED VARIANT WAS TRIED AND IS DOMINATED
A real-pole design constrained to hold 3–5 Hz nearer unity gives `poles [0.95916, 0.63265]`, 3 Hz
gain **0.9322** (vs V172's 0.8501) and 8.64 Hz **0.5716** (vs 0.4441) ⇒ **5.0x damping instead of
6.2x**. It buys back only **4 ms** of group delay (+26.1 vs +30.1 ms at DC) for a **1.2x loss of
damping**. **Dominated — not built.**

## ✅✅✅ **V172 BUILT — TWO INDEPENDENT RATCHET LEVERS NOW EXIST, WITH DIFFERENT FEEL COSTS**
```
   V172 = V158 + four float32 coefficients at 0xC60A8/AC/B0/B4   (the assist section retune)
   image  ff8d07e6ba3e80484b8ef67eeb4d9fd13804ee999d35953038355ab2cd0ab830
   .rwd   c0ed77b773a7e7f300ab438450817e17f49269c67d096edefa56dea140e958a5
   13 payload bytes + one CRC trailer - 23/23 assertions - chain 50/50 - readback identical
```

### 🛑 A MISTAKE I NEARLY SHIPPED AS A NEGATIVE
A frontier sweep appeared to **kill** this lever: every tuning that attenuated 7–11 Hz showed
*“ring Q 30–53”* and 230–413 ms settling, which would be a Q≈40 resonance in the driver's own band.
**But that Q figure is meaningless for REAL poles**, and the rows that mattered had real ones. I was
about to close the lever on a number that did not apply.
✅ Constraining the search to **real poles at r ≤ 0.97** gives `poles [0.97, 0.47509]`, **0.0 %
overshoot, ZERO oscillation cycles on a pulse** — an overdamped low-pass, not a resonator.
⊕ Recorded so it is not repeated: **never read Q off a pole pair without checking it is complex.**

### ✅ WHAT V172 DOES, FROM THE BUILT IMAGE'S OWN BYTES
```
   freq       FLYING     V172       ratio
   0.5 Hz     1.0000     1.0067     1.007   <- DC UNCHANGED: no steady-state weight cost
   3   Hz     0.9975     0.8501     0.852   <- driver band, 15 % down
   5   Hz     0.9931     0.6802     0.685   <- driver band, 32 % down
   8.64 Hz    0.9790     0.4441     0.454   <- THE RATCHET, 2.2x attenuated
   21  Hz     0.8659     0.0902     0.104   <- THE GRIND, 9.6x attenuated
   loop: effective map s 1.958 -> 0.888  =>  |1-P.L| 0.0700 -> 0.4360  =>  6.2x MORE DAMPED
```

### ⭐ THE TWO LEVERS, AND HOW TO CHOOSE
```
             cell(s)              predicted    what it COSTS
   V168      0xC6384 2048->1536   3.4x ratchet  heavier steering NEAR CENTRE, at all times
   V172      0xC60A8..B4 retune   6.2x ratchet  assist ~130 ms SLOWER on fast inputs;
                                  + 9.6x grind  3-5 Hz driver content down 15-32 %
```
✅ **V172 is stronger on paper** — more damping, and it is the only one that also attacks the grind.
🛑 **But its risk is less characterised, and it is the risk that matters here.** A 130 ms lag in the
dominant assist lane means assist arrives late on a quick input — heavier on turn-in, then lightening
— which **could itself read as notchiness**, the very sensation being chased. V168's cost is
uniform and predictable; V172's is dynamic.
⭐ **RECOMMENDATION: fly V168 first.** Not because it is the stronger lever — it is not — but because
its failure mode is legible. **If V168's damping is insufficient, or its static weight is
unacceptable, V172 is the next build and needs no further work.**
⊕ They do **not** stack: V172 asserts the slope cap is still stock, so the two are alternatives and
each is a clean single-variable test against the same V158 base.

### ✅ AND A NULL ON EITHER IS INFORMATIVE ABOUT THE OTHER
Both rest on the **same** real-positive `P·L` assumption. ⇒ if V172 reads null on the ratchet, that
falsifies the assumption for V168 too, and vice versa — so whichever flies first, its null closes
more than one lever. ⊕ V172 adds a second discriminator the cap does not have: **the grind should
fall further than the ratchet** (9.6x vs 2.2x filter attenuation). If the ratchet moves and the grind
does not, the shared-loop account is wrong somewhere and that difference names where.

## ⭐⭐ **LEVER #2 EXISTS: THE ASSIST MAP'S OWN SECOND-ORDER SECTION IS A RETUNABLE NOTCH**
This kit's record says *“this firmware has NO frequency-selective lever”* (FactorD refuted) and
*“no notch filter exists anywhere”*. **Both are wrong.** `FUN_000352b4` carries a genuine biquad in
the **dominant torque-fed lane**, and it is **already enabled on the flying build**.
```
   s1 = gp-0x3814,  s2 = gp-0x3818   (read BEFORE update),  1 kHz
     w = -C_AC*s1 - C_A8*s2 + C_B4*x
     y = (1-C_AC)*s1 + (C_B0-C_A8)*s2 + C_B4*x        y clamped to +/-12.0
     s1 <- s2 ;  s2 <- w
   coefficients 0xC60A8 / 0xC60AC / 0xC60B0 / 0xC60B4 (float32)  ·  enable 0xC649B
```
Simulated directly from the decompiled operand order (a sign slip here inverts the answer, so it is
**simulated, not hand-derived**):
```
   freq       FLYING (stock coeffs)      V106/V107 coeffs
   8.64 Hz    0.9788  -11.8 deg          0.9823  -16.5 deg     <- the RATCHET, PASSED by both
   21   Hz    0.8659  -30.0 deg          0.4925  -72.3 deg     <- the grind
   25.5 Hz                               gain 0.000            <- V106 placed a PERFECT NULL
```
✅ **[EVIDENCE] the structure can place a deep notch — the kit has already done it once**, at
25.5 Hz, in the V105/V106 notch work. ✅ **[EVIDENCE] neither tuning touches the ratchet**: both pass
8.64 Hz at ≈0.98.
✅ **[EVIDENCE] the enable is ON for the flying build** (`0xC649B` = 1 from V104; stock ships **0**),
and the coefficient cells have been changed before **without faults**, so neither the enable path nor
the coefficient path is new risk.

### ⭐ WHY THIS IS A BETTER LEVER THAN THE SLOPE CAP ON THE FEEL AXIS
```
   slope cap 0xC6384   reduces the map's gain at EVERY frequency INCLUDING DC
                       => heavier steering near centre.  Real, monotone with dose.
   notch at 8.64 Hz    reduces the loop's contribution ONLY at the resonance
                       => DC gain 1.0000  =>  NO steady-state feel cost at all.
```
⊕ And it **does not rest on the real-positive `P·L` assumption** that V168's lever needs: a notch
removes gain at the resonant frequency **without adding gain anywhere**, which is the textbook fix
for a loop resonance whatever the loop's phase there.
⚠ **[BELIEF] the DC-cost argument.** It follows from the section's own DC gain, which is measured;
what is *not* measured is whether the operator's felt “weight” tracks DC gain rather than the
mid-band. A first-order claim, not a guarantee.

### 🛑 WHY A RAZOR NOTCH IS THE WRONG DESIGN, AND WHAT REPLACES IT
An optimiser hits **−96 dB at exactly 8.64 Hz with DC gain 1.0000** — but that notch is also that
NARROW, and **the ratchet's own frequency spans 7.81–10.74 Hz across operating-point strata**
(CV 5.5 % speed, 7.0 % command, 12.3 % rate). A razor notch simply misses the mode when it drifts.
⊕ It also **amplified 40 Hz by 1.36x**, which must not be traded away silently.
⇒ the design in progress targets **attenuation across 7–11 Hz** with a pole-radius margin, unity DC,
and **no gain increase anywhere** — GATE 2 on a notch has to cover phase and out-of-band gain, not
just depth, because a notch flips phase across itself and that can destabilise frequencies either
side even while the notch attenuates.

## ✅✅ **THE RATCHET IS A FIXED RESONANCE WITH COMMAND-PROPORTIONAL DRIVE — THE `1−P·L` SIGNATURE**
244 pooled engaged-creep windows, each assigned to a stratum by its **own** mean operating point (the
earlier attempt required contiguous runs *within* a stratum, which fragments the data and left six of
seven strata empty — that cut is superseded).
```
                  n win   peak Hz   excess          FREQUENCY SPREAD
   speed 1-6       17      8.59      18.7
   speed 6-10      57      7.81      15.1
   speed 10-14     84      8.40      27.4           7.81-8.98 Hz   sd 0.46   CV 5.5 %
   speed 14-18     58      7.81      40.0
   speed 18-24     28      8.98      35.5

   |rate| 0-3      42     10.16       9.7
   |rate| 3-6      27     10.74      12.5
   |rate| 6-12     43      8.40      21.7           8.01-10.74 Hz  sd 1.12   CV 12.3 %
   |rate| 12-25    45      8.01     143.1   <- worst rate band
   |rate| 25+      87      8.20      27.6

   |cmd| 100-250   23      9.57      17.0
   |cmd| 250-600   75      8.59      19.4           8.01-9.57 Hz   sd 0.60   CV 7.0 %
   |cmd| 600-1500  46      8.01      39.4
   |cmd| 1500+    100      8.20      58.1   <- MONOTONE, 3.4x across the command range
```
✅ **[EVIDENCE] the FREQUENCY is near-invariant** — CV **5.5 %** across speed, **7.0 %** across
command, **12.3 %** across rate, with only a modest downward drift as rate and command rise.
✅ **[EVIDENCE] the AMPLITUDE is MONOTONE in command magnitude, 17.0 → 58.1 (3.4x).**
⇒ **fixed resonance + command-proportional drive.** That is precisely the `Z = (Z0 + P·F)/(1−P·L)`
signature: the command is the **excitation `F`**, the plant sets the frequency, and the loop sets how
sharply it rings. **A moving loop pole would have shifted the frequency with operating point. It does
not.**

### ⭐ AND IT SHARPENS THE ENGAGED-ONLY EXPLANATION
My earlier account attributed engaged-only entirely to the engagement-conditional lanes joining `L`,
predicting a **4.88x** engaged/manual ratio against a measured **19.9x [4.82, 35.64]** — consistent
but at the very bottom of the CI. **The command-scaling result supplies the missing factor**: in
manual the command is **zero**, so the excitation `F` is absent as well as the extra loop gain.
⊕ The two together land much closer to the measurement than either alone. **⚠ Not a clean product** —
excitation and the engagement-conditional loop terms are both driven by engagement and are not
independent factors to multiply — **but the direction and rough size now agree, where the loop-gain
term alone did not.**

### ✅ WHAT THIS MEANS FOR V168
It **confirms the lever's logic**: `1−P·L` divides the *whole* response, including the
command-driven part, so reducing `|L|` attenuates the ratchet **at every command level** rather than
only at some operating point. It also predicts the **drive should show the effect most clearly at
HIGH command and in the 12–25 deg/s rate band**, where the excess is largest — useful for the pass.

### ⚠ THE LKAS GAIN COSTS RATCHET — STATED, NOT RECOMMENDED
```
   gain 3564 (4x): ratchet excess median 16.5  (n=3)
   gain 5346 (6x): ratchet excess median 34.5  (n=6)   ratio 2.09x
   Mann-Whitney p = 0.167  -- NOT significant, and CONFOUNDED (V96->V102 spans other builds)
```
⚠ **[BELIEF, weak]** raising the LKAS gain raises the ratchet, as **excitation** — consistent with
the command-scaling result above and with the operator's own 8x experience of more grinding.
🛑 **This is NOT a recommendation to lower the gain** — there is a standing instruction never to, and
the operator wants 8x if anything. **The constructive reading is the opposite: damping the resonance
is what BUYS the headroom for more gain.** If V168 works, 8x becomes affordable in a way it is not
today.

## ✅ **LKAS AUTHORITY IS NOT THE BINDING CONSTRAINT — THE COMMAND IS DELIVERED AND RARELY RAILS**
The third of the operator's three named symptoms, measured directly for the first time.
```
   ENGAGED frames, |sc_tq| against its own observed ceiling of 4096 counts
   route build   n       rail duty   >=90 %   >=50 %   p50 |cmd|
   r78   V91     61,987   0.0258     0.0302   0.0523     230
   r7e   V96     61,506   0.0648     0.0739   0.1161     230
   r96   V102    57,629   0.0145     0.0170   0.0401     145
   ra6   V106   123,802   0.0302     0.0338   0.0545     133
   r1e   V107    99,910   0.0277     0.0334   0.0625     247
   r22   V112    48,957   0.0379     0.0428   0.0754     232
   r24   V122    58,652   0.0271     0.0303   0.0495     149
   pooled: rail 3.3 % - >=90 % 3.7 % - >=50 % 6.4 %
```
✅ **[EVIDENCE] the command sits at its ceiling only ~3 % of engaged frames**, and its median is
**133–247 counts, i.e. 3–6 % of the ceiling.** openpilot is overwhelmingly asking for very little.
⇒ **raising an authority ceiling cannot add what was never requested.**

### ✅ AND WHAT IS REQUESTED *IS* DELIVERED
```
   command -> steering RATE, engaged, best lag over 0-400 ms, vs phase-shuffled surrogates
   r78 230 ms r -0.167 (shuf p95 0.087)   ra6  70 ms -0.263 (0.054)   r22 390 ms -0.296 (0.100)
   r7e 150 ms r -0.349 (0.094)            r1e  20 ms -0.293 (0.056)   r24 180 ms -0.441 (0.102)
   r96  40 ms r -0.402 (0.059)                                        DELIVERED on 7/7 routes
```
✅ **[EVIDENCE] the correlation clears its shuffled control on every route**, and its **sign is
negative**, which is exactly the operator-confirmed convention (*+LKAS demands negative angle*). That
sign agreement is a free sanity check on the whole measurement, and it passes.
⇒ **the plant is not swallowing the command.** Authority is not a delivery failure either.

### 🛑 ONE MEASURE OF MINE THAT DOES NOT WORK — RECORDED, NOT DROPPED
I stratified `mean|rate| / mean|cmd|` by command magnitude to look for a friction/stiction signature
(less motion per count at small commands). It shows the **opposite** — the 0–200 stratum has the
**highest** ratio (13.7–57.0 vs 6.2–26.6 at 200–800). **That is an artefact, not a finding**: when the
command is small the wheel motion is dominated by the driver and the road, so the ratio is
small-denominator noise rather than a delivery gain. **The stratification carries no information and
no stiction conclusion may be drawn from it.**

### ✅ THE CONCLUSION, AND WHAT IT LEAVES
**“LKAS authority” is not a firmware authority-ceiling problem.** The ceiling binds 3 % of the time,
the command is delivered when issued, and the firmware already multiplies it **6x** (`0xC6CD0`=5346).
The remaining ways to ask for more are **openpilot-side, which the standing instruction forbids**, and
the one firmware ceiling that was tried is closed: **`0xC407E` is the hard-fault interlock — Honda
ships it at 511, one count under its own 512 trip, and V73 raised it ⇒ V74/V75 FAULTED.**
⇒ **No authority lever is proposed, because the measurement says none is needed.** If the operator's
lived experience of weak lane-keeping persists, the thing to capture is **which manoeuvre** it happens
in — the 3 % rail duty means there IS a small population of railed frames, and those are the only
frames where a ceiling could matter.

## ⭐ **PEAK COMMAND OSCILLATION IS IN THE GRIND'S BAND — IT SHARES THE GRIND'S LEVER**
The third symptom, measured for the first time with the validated estimator. Sweeping the whole
usable spectrum of all three COMMAND channels, excess over each channel's **own** fitted power law,
nulled at that channel's **own** measured slope:
```
   median excess / slope-matched null p95, 7 routes
                 0.5-3   3-5    5-12   12-15   15-25   25-35   35-49
   cc_req        0.68    0.85   0.54   0.64    1.97    0.48    1.06
   co_tqcan      0.93    0.84   0.48   0.50    1.65    0.39    0.82
   sc_tq         0.61    0.88   0.50   0.65    1.55    0.52    0.64
   cs_tq (car)   0.03    0.17   9.15   1.84    5.40    0.35    0.38
```
✅ **[EVIDENCE] the command clears its own null in EXACTLY ONE band — 15–25 Hz, the GRIND's band —
and is below its null everywhere else, including the ratchet's.**
⭐ **The decisive asymmetry**: at 5–12 Hz the car's peak is **LARGER** (9.15) than its 15–25 Hz peak
(5.40), yet the command is **below null** at 5–12 (0.48–0.50) and **above** it at 15–25. So the command
does **not** simply inherit whatever the car does ⇒ **"openpilot re-emits everything" is refuted**,
and the selectivity needs an explanation.
⊕ **It has one**: openpilot steers on **angle/curvature**, and the ratchet is a **TORQUE-only mode
with no angle signature** (angle channels 0.79–0.83, i.e. chance). **A torque-only mode is invisible
to openpilot; a mode that moves the wheel is not.** That predicts exactly the observed pattern.

### ⚠ WHAT IS *NOT* ESTABLISHED — AND MY OWN CONTROL FAILED
⚠ **The correlation is NOT significant**: command 15–25 vs car 15–25 gives ρ **+0.54 / +0.61**,
p **0.215 / 0.148** at n = 7. Positive and the right sign, but it does not stand on its own.
🛑 **My 5–12 Hz negative control DID NOT DISCRIMINATE** — it returned ρ **+0.54 / +0.68**, as high as
the band it was meant to contrast with. It was correlating sub-null noise against the car's peak, so
**it carries no information and the causal direction is NOT established by it.** Recorded rather than
quietly dropped.
⚠ The build trend agrees in direction but is weaker: post-V102 command ρ **−0.70 / −0.80**
(p 0.188 / 0.104) against the car's **−0.90 (p 0.037)**.

### ✅ THE ACTIONABLE CONCLUSION
**Peak command oscillation is not a separate mechanism needing its own lever.** It sits in the
grind's band, moves in the grind's direction across builds, and openpilot must not be modified
(standing instruction). ⇒ **damping the 15–25 Hz resonance is the only permitted route, and V158's
damper shape — already on the fly-first build — is that lever.** No new build is required for it.
⊕ **The V168 drive scores it for free**: the same episode already yields the 15–25 Hz band, so the
command peak can be read alongside the grind with no extra exposure.

## ✅ **THE SLOPE-CAP DOSE LADDER IS CUT — ALL FOUR DIRECTIONS READY, NO REBUILD NEEDED**
```
   build  cap    gain     Q ratio   vs stock   image SHA256 (first 16)
   V169   1792   1.750x    6.57     2.2x       ed9e5fec84378f20   <- SMALLER, if V168 is too heavy
   V168   1536   1.500x    4.26     3.4x       058dd64ac442ef43   <- FLY FIRST
   V170   1280   1.250x    3.16     4.5x       0c923c363a920459   <- next step up
   V171   1024   1.000x    2.50     5.7x       e3cbc92de7a07bf2   <- largest sane dose
```
✅ All four are **V158 + one cal cell**, built through **V168's own verified builder** (one builder,
four build numbers) so the assertions and the CRC/readback path cannot drift apart. **35/35 on each.**
⊕ The feel cost rises monotonically with the dose; **peak authority and max rates are untouched at
every dose** (the curve is uncapped above X≈450) and **no dose touches the LKAS lane**.
⇒ whichever way the V168 drive reads — clean but incomplete, or effective but too heavy — **the next
build already exists.**

## ✅✅✅ **V168 BUILT — THE BASE-ASSIST SLOPE CAP, A LEVER CLASS THE KIT HAS NEVER TRIED**
```
   V168 = V158 + 0xC6384  2048 -> 1536   (2.000x -> 1.500x)
   image  058dd64ac442ef43c790965c9a5fc011f147f7ff0a5e7cd0c0d1bb8889c7b0ff
   .rwd   0f0ace3b5bc0a8541227e06c831c555797566374b298ba606614f5a09a1356f1
   ONE payload byte (0xC6385: 08 -> 06) + one CRC trailer.  35/35 assertions.
   CRC chain 50/50 - readback byte-identical - all six curve records untouched.
```
✅ **`0xC6384` is byte-identical on ALL 161 IMAGES** — the first time this kit has moved it.
⚠ **The payload is ONE byte, not two**: `0x0800 -> 0x0600` differs in the high byte only. The build
asserts the **VALUE**, not a hardcoded byte count — the hardcoded-2 assertion has bitten this kit
before and it fired here too, on the first run.

### ⭐ HOW THIS BUILD'S CLASS DIFFERS FROM THE WHOLE ARC SINCE V38
```
   V38-V52    authority / filters / poles / caves
   V53-V61    telemetry probes and lane mutes
   V62-V73    the rate lane (r24 / r26)
   V74-V83a   the base-assist DAMPER          V84 damper reverted to Honda
   V85-V122   friction / knee / alpha2, the Coulomb relay
   V133-V167  the damper's SHAPE and the Path-2 weight
   ---------------------------------------------------------------------------------
   V168       the BASE-ASSIST MAP's own slope cap  <- the DOMINANT torque-fed loop term
```
Every earlier lever acts on a term that is **not** the dominant one. `gp-0x6b86` is **5.8–7.8x the
entire PID** and has the widest window of all eleven aggregator slots. **This is a new lever, not the
same lever pushed the other way.**

### ✅ WHY IT IS AIMED AT THE RATCHET SPECIFICALLY
The grind and the ratchet **dissociate**: post-V102 the grind falls ρ = −0.94 (p 0.005) in three
channels while the ratchet does not move (ρ = −0.14, p 0.787) against a floor that would have shown
1.9x. Every lever the kit has found is the grind's. V168 is the first aimed at the other one.
⊕ **V168 is built on V158**, so it carries the grind lever too and **both symptoms score from the
SAME single episode in different bands** — the two are separated by the **INSTRUMENT**, not the build.

### 🛑 THE NON-STOCK DELTA, READ FROM THE BUILT IMAGE
```
   V168 vs STOCK: 341 differing bytes, 321 payload + 5 CRC trailers, in 12 blocks
     0xC4000  169 B   friction / knee / alpha2 / clamp family (V85-V122)
     0xC6000   42 B   main cal -- incl. the 6x LKAS gain, Lever B, and THIS BUILD'S 1 byte
     0xE4000   36 B   } arbitration setpoint limits raised at V38 (0x3c -> 0x40 pattern)
     0xE5000   36 B   }
     0xD7000   22 B   the damper records (V158's FactorC/FactorE shape)
     0x55000    6 B   CAN tap
     0x35000    4 B   · 0x2A000 2 B · 0x13000/0x14000/0x3A000/0x45000 1 B each
```

### ✅ WHAT A NULL WILL LICENSE — WRITTEN BEFORE THE CUT
One continuous **15 s** engaged creep pass, scored by `rlog-tools/score/score_band_excess.py`:
- **ratchet 5–12 Hz excess falls BELOW its slope-matched null** ⇒ the ratchet is gone in that regime
  and the loop-gain account is confirmed;
- **excess unchanged** (V122 reference ≈33, null ≈4) ⇒ a predicted 3.4x damping increase produced
  nothing ⇒ **falsifies the real-positive `P·L` assumption**, so this loop does not produce the 14.3x
  cancellation and the assist map is exonerated the way the Coulomb relay now is;
- **excess RISES** ⇒ lowering `|L|` sharpened the mode, possible only if `P·L` is not real-positive
  ⇒ revert and re-derive the phase.
✅ A single 15 s episode detected the ratchet **11/11 at 5–65x margin**, so **all three outcomes are
readable from one pass. There is no uninterpretable branch.**

### 🛑 THE FEEL COST — THE OPERATOR'S CALL
Lowering the cap means **less assist per unit driver torque near centre ⇒ heavier steering there**,
against a standing constraint. Narrower than it sounds: the curve is **uncapped above X≈450 so peak
authority and max rates are untouched**, and the map is **driver-torque fed, not the LKAS lane**
(`0xC616C`=0 ⇒ `gp-0x6b4a`≡0, asserted in the build). 1536 is the **smallest** dose clearing the
one-episode margin; 1280 and 1024 remain if it reads clean but incomplete.

## ⭐⭐ **THE ASSIST CURVE IS IN THE IMAGE, THE 2.000 SLOPE CAP **BINDS**, AND GATE 2 PASSES**
The curve was never unreachable — it is **initialised-data copied ROM→RAM at boot**, which is why
only 3 `st.h` target the 20-knot block and 2 of those are clears. Found by searching the whole image
for the shape the decompile requires (10 ascending X bounded by the input clamp 8192, 10 ascending Y
bounded by the output clamp 12288):
```
   0xCE47A  X  0   25   60  100  150  250  450  900 1800 4150
            Y  0  154  338  460  549  635  702  766  824  857
            slope 6.16 5.26 3.05 1.78 0.86 0.34 0.14 0.06 0.01
            max 6.16  vs cap 2.000  =>  BINDS on 3 of 9, over X 0-100

   0xCF372  max slope 16.37  binds 4/9 over X 0-450
   0xCF3CA  max slope 11.97  binds 3/9 over X 0-150
   (+ 0xCE4A6 / 0xCF39E / 0xCF3F6 duplicates — the mode-selected pointer-table family)
```
✅ **[EVIDENCE] the cap is NOT inert — it clamps the steep low-torque segments on every record**,
pinning the map's **small-signal gain at exactly 2.000**, which is the **CEILING** value of `s` in the
loop census. The loop's largest single term therefore sits at its maximum, permanently.
✅ **[EVIDENCE] all six curve records are byte-identical across the 161 images**, and `0xC6384` reads
**2048 on all 161** (exact u16 read; an earlier 40-byte window check of mine spanned `0xC63A0`/
`0xC63AC`, which DID change, and wrongly suggested 5 variants — **that was my error, the cap is
untouched**).

### ✅ GATE 2 — ANCHORED ON THE MEASURED Q RATIO, NOT A CENSUS PHASE
⚠ My first pass used the census's `L` phase (−148°) with `P` real-positive. That puts `P·L` in the
third quadrant and gives `|1−P·L| = 1.92 > 1` — a loop that **ADDS** damping, contradicting the
measured 93 % cancellation. The phase cannot be pinned (the census says `P`'s phase *“is not in the
image”*) **and the sign of the whole result depends on it**, so anchor on the measurement instead.
```
   MEASURED Q_eff/Q_passive = 40/2.8 = 14.3  =>  |1-P.L| = 0.0700  =>  P.L = 0.9300 at stock
   [ASSUMPTION, stated] P.L real-positive at the peak -- what the measured ratio REQUIRES,
   and the standard form for a damping-cancelling loop.

   cap    s       |L|     |1-P.L|   Q ratio    vs stock
   2048   2.000   2.825   0.0700    14.29      stock
   1792   1.750   2.575   0.1523     6.57      2.2x MORE damped
   1536   1.500   2.325   0.2346     4.26      3.4x MORE damped
   1024   1.000   1.825   0.3992     2.50      5.7x MORE damped
```
✅ **MAGNITUDE: PASSES**, and the effect is large. ✅ **PHASE: PASSES** — the map term is a **real
gain**, so lowering the cap **scales `|L|` without rotating it**; under the real-positive `P·L` the
measurement requires, `|1−P·L|` can only move away from zero ⇒ **monotonically more damped at every
cap value, with no value at which it reverses.**
⚠ **What would falsify the assumption**: if `P·L` were not near the positive real axis, the measured
14.3x cancellation could not come from this loop at all. **The on-car test is the same either way** —
lower the cap and see whether the 8.64 Hz torque peak drops below its slope-matched null.

### 🛑 THE FEEL TRADE — AND WHY IT IS NARROWER THAN IT LOOKS
The cap binds over the **LOW-torque** segments (X 0–100 to 0–450 of a ±8192 range), so lowering it
means **less assist per unit driver torque near centre ⇒ heavier steering there** — the regime the
operator asked to keep light. **Stated plainly because it cuts against a standing constraint.**
⊕ But it is narrower than the constraint's wording suggests: the constraint is about *“max steering
angular velocity and acceleration”* and *“low apparent mass and friction **to LKAS**”*, and
- the curve is **UNCAPPED and unchanged above X≈450** ⇒ **peak authority and max rates are untouched**;
- the map is fed by `clamp(gp-0x4f60) + gp-0x6b4a`, i.e. the **driver torque sensor**, not the LKAS
  command lane (`gp-0x6b4c`) ⇒ **[BELIEF — `gp-0x6b4a`'s provenance is NOT yet established; if it
  carries an LKAS-derived offset this claim weakens.]**
⊕ **Recommended first dose 1536 (1.5x)** — predicted **3.4x** more damping, which clears the
one-episode detection margin comfortably, and is the smallest step that does. **Not the largest dose:
the feel cost is real and the operator should meet it in the smallest useful increment.**

## ⚠ **THE ASSIST-CURVE INITIALISER IS STILL UNLOCATED — TWO CANDIDATE PATHS RULED OUT**
Hunting the RAM-resident 10-knot curve (needed to finish GATE 2 on the slope cap `0xC6384`).
Both leads the byte scan produced are **not** the initialiser:
```
   0x38FD0 / 0x38FEE / 0x39522   st.h r0, -0x6430/-0x6444/-0x641c, gp
       -> STORE-ZERO with a lockstep shadow (shadow = knot - 0x184C; mismatch calls
          FUN_0006b9fa, the lockstep-fault handler).  A CLEAR path, carries no values.
          Exactly the documented store-zero trap.

   0x39A0C..                     blend each knot toward ep = tp+0x7564 = 0xC6564, in float
       ANCHOR CHECK: 0xC6384 reads 2048 (the slope cap) => tp = 0xBF000 CONFIRMED, so the
       0x1000 trap is not in play here.
       -> but 0xC6564 is ZERO, and zero on ALL 161 IMAGES  =>  this blends the curve toward
          zero: a FADE-OUT / degradation ramp, not an initialiser.
```
✅ **[EVIDENCE] `0xC6564` = 0 on all 161 images**, so nothing the kit has ever built changed it.
⊕ Region context: `0xC6520-0xC6560` is a **float32 array stored as (lo16,hi16) halfword pairs**
(`0 16840` = 25.0, `0 16968` = 50.0, `0 16256` = 1.0), which is why a naive u16 read of that
neighbourhood looks like noise. Recorded so the next pass does not mis-read it as integers.
❌ **No monotone 10-knot table bounded by the input clamp (8192) exists in `0xC6400-0xC6700`.**

### ⭐ A CHEAPER ROUTE TO THE SAME ANSWER — THE FIRMWARE ALREADY COMPUTES IT
The question GATE 2 needs is only *does the 2.000 cap BIND at the creep operating point?*, and
`FUN_000352b4` **already tracks that**: the map-build loop keeps a running maximum of the capped
per-segment slope in **`gp-0x69a6`** (`uVar40` in the decompile, written `*(short*)(gp-0x69a6)`).
⇒ **`gp-0x69a6` == 2048 means the cap is binding.** That is a **one-cell telemetry read**, not a
firmware-reconstruction problem, and it answers the gate directly on-car in a single episode.
⚠ **[BELIEF]** the cap does bind in the mid-torque range: the domain-average slope is
`12288/8192 = 1.5` against a cap of **2.000**, so the cap can only bite on segments steeper than 1.33x
the average — which is the normal shape of a power-assist curve, and is the loaded-wheel creep
regime. **Unverified until `gp-0x69a6` is read.**

### ✅ THE RECOMMENDATION IS UNCHANGED
**V158 still flies first.** It targets the GRIND, which is firmware-reachable and demonstrably
moving (post-V102 ρ = −0.94, p = 0.005, in three channels). The ratchet needs a different lever, and
that lever's gate is one telemetry cell away — **not** a reason to delay a build that addresses the
other symptom.

## ⭐ **THE RATCHET'S PRIME SUSPECT IS THE BASE-ASSIST MAP — AND ITS LANE IS NOT MEMORYLESS**
Two independent routes now point at the same lane. **From the DATA** (this session): the ratchet is
firmware-created, engaged-only, in **torque not angle**, and untouched by all 278 bytes the kit has
changed. **From the CODE** (a prior tracer's loop-topology census, re-read and confirmed):
```
   Z = (Z0 + P.F) / (1 - P.L)      every torque-fed lane is a DENOMINATOR term
   Q_eff / Q_passive = 40 / 2.8 = 14.3   =>  the loop cancels ~93 % of the mode's damping
   gp-0x6b86 (base assist map, FUN_000352b4) is the LARGEST torque-fed term: window
   +/-0x3000, the widest of all 11, and 5.8-7.8x the ENTIRE PID at 7.79 Hz
```
✅ **[EVIDENCE] its slope cap `0xC6384` = 2048 (2.000x) is byte-identical on ALL 161 IMAGES**, as
are `0xC6382` = 41 and the input clamp `0xC6200` = 8192. Independently confirmed by my own
untouched-cell scan, which found `0xC6384` absent from the 28 changed bytes in `0xC6000`.
⇒ **the largest available `L` lever has never been moved, which is exactly the profile of a cause
the kit's 30+ builds could not have touched.**

### 🛑 A CORRECTION TO THE CENSUS — THE LANE HAS STATE
The census priced this lane as **MEMORYLESS** (*“transfer at 7.79 Hz is real, 0°, magnitude = the
local slope”*). **The decompile shows otherwise.** `FUN_000352b4` ends with a **parallel lagged
branch** added to the direct path:
```
   iVar33 = clamp(gp-0x6b7a - sVar15, +/-0x3000) * (uVar25 < uVar18)     # a DIFFERENCE, comparator-gated
   iVar24 += (iVar33*0x80 - iVar24) * k >> 11                            # gp-0x381c, 32-bit state, 1 kHz
   gp-0x6b86 = clamp(iVar34 + (iVar24 -/+ 0x80) >> 7, +/-0x3000)         # direct + LAGGED, in PARALLEL
```
⊕ A difference passed through a lag and added back is a **lead-lag / dynamic-assist compensator**,
not a static curve ⇒ **the lane's transfer is NOT the memoryless slope the census assumed**, and any
`|L|` computed from the slope alone is incomplete.

### ⭐ AND ITS POLE IS SELECTED BY ENGAGEMENT — BUT THE EFFECT IS TOO SMALL
```
   k = cal(0xC6382) = 41        if (iVar14 != 0 && return-centre != 0)     <- MANUAL
     = LERP(0xC6906..) = 20     otherwise                                  <- ENGAGED
   (return-centre is DEAD ENGAGED, 0.0000 duty / 75,227 frames, so the arms genuinely differ)

   at 8.64 Hz, closed form AND the real integer recursion agreeing to 4 dp:
     ENGAGED k=20  corner 1.56 Hz   |H| 0.1779  arg -78.20 deg
     MANUAL  k=41  corner 3.22 Hz   |H| 0.3491  arg -68.02 deg
   => engaged lags 10.18 deg MORE, which moves 1-P.L the RIGHT way (1.798 -> 1.713)
```
🛑 **[EVIDENCE] but that is only a ~5 % change in the denominator, against an observed ~20x
presence-vs-absence contrast. The pole difference is REAL, points the right way, and is FAR TOO
SMALL to be the mechanism.** Recorded as a negative so it is not re-derived.

### ❌ AND THE FLOAT SECOND-ORDER BLOCK IS NOT IT EITHER
`FUN_000352b4` carries a genuine 2nd-order float section (states `gp-0x3814`/`gp-0x3818`, coeffs
`0xC60A8..0xC60B4`), gated on `0xC649B==1 && 0xC64FA <= gp-0x671a`.
✅ **[EVIDENCE] it is HONDA'S and ships DISABLED** — `0xC649B` stock = **0**, and the kit enabled it
on 58 of 161 images (V104 on; the V105/V106 notch work).
❌ **Enabling it did nothing to the ratchet**: `0xC649B` vs ratchet **ρ +0.26, p 0.500**; its
coefficients moved at V106/V107 with **ρ −0.31 to −0.45, all p ≥ 0.226.**

### 🛑 THE BLOCKER, STATED PRECISELY
The 10-knot curve itself is **RAM-resident** (`gp-0x641e..gp-0x6430` X, `gp-0x6444..` Y), so the
**local slope at the creep operating point — which is what sets `|L|` — is not readable from the
image**, and GATE 2 on `0xC6384` cannot be completed without it.
⊕ **`search_instructions` returned ZERO for stores to that block; a raw LE byte scan across BOTH gp
encodings found 27 accesses** (`0x38FD0`/`0x38FEE`/`0x39522` store-shaped; `0x43CBC-0x43CF6` touches
all ten X knots, but decompiles as a READER into stack locals). **Another instance of the documented
undercount — the null was false.** The initialiser is still unlocated.

## ✅✅ **THE RATCHET SCORES FROM ONE 15-SECOND EPISODE — THE 8-PASS SPEC WAS THE WRONG ENDPOINT**
Last tick's drive spec asked for **8 passes of 15 s** to resolve a 1.68–2.74x *ratio*. That is
**unbuildable** under the standing design law — *a spec needing matched episodes or minutes of
exposure is unbuildable, and the operator stops the drive the moment the symptom persists.*
✅ **And it was the wrong endpoint.** The engaged-vs-manual result is **PRESENCE/ABSENCE** (peak
clears its null on **7/7** engaged arms, **0/7** manual), so killing the ratchet is an **~8x** move
from excess ≈33 to below null ≈4 — not a 1.7x one.
```
   single continuous engaged-creep episodes from the existing corpus
     15 s ->  5 windows   11 episodes   RATCHET DETECTED 11/11 = 100 %
     20 s ->  6 windows    5 episodes                     5/5  = 100 %
     30 s -> 10 windows    4 episodes                     4/4  = 100 %
   excess 25.5-155.7  vs slope-matched null 1.9-4.9   =>  5-65x MARGIN
```
✅ **[EVIDENCE] ONE 15 s continuous engaged creep pass answers the primary question.** More passes
only sharpen the *graded* question (how much smaller), which is secondary to *is it fixed*.
⚠ The **grind's** margin on the flying build is smaller (V122 excess 14.0 vs null ≈4, i.e. 3.5x), so
a marginal grind read from one episode is **inconclusive, not negative**. The ratchet's is not.

## ⚠ **DRIVEN vs SELF-EXCITED: INCONCLUSIVE, LEANING DRIVEN — AND UNDERPOWERED FOR THE SAME REASON AS EVERYTHING ELSE**
The ratchet is engaged-only but absent from every command channel. Two mechanisms fit that:
**DRIVEN** (the command carries no 8.6 Hz line but the firmware's RESPONSE to it creates one
⇒ a forward-path nonlinearity, and the lever is in the forward path) or **SELF-EXCITED** (a
closed-loop instability running at its own frequency ⇒ the lever is in the feedback path).
That distinction decides which half of the chain to search, so it was worth a test.
```
   band-SPECIFIC coupling = coherence(7-10.5 Hz) - coherence(30-40 Hz control band),
   `co_tqcan` -> `cs_tq`, vs phase-shuffled surrogates (spectrum preserved, timing destroyed)

     r78  V91    -0.021 (shuf +0.091)  not specific     r1e  V107  +0.522 (+0.097)  SPECIFIC
     r7e  V96    +0.133 (+0.039)  SPECIFIC             r22  V112  +0.087 (+0.060)  SPECIFIC
     r7f  V96    +0.176 (+0.042)  SPECIFIC             r24  V122  +0.068 (+0.062)  SPECIFIC
     r96  V102   +0.019 (+0.047)  not specific         ra4  V104  +0.148 (+0.105)  SPECIFIC
     ra6  V106   -0.060 (+0.116)  not specific

   across routes: median +0.087   95 % CI [-0.021, +0.176]   <- CROSSES ZERO
```
⚠ **[INCONCLUSIVE]** 6/9 routes are individually specific and the pooled median is positive,
but **the CI includes zero**, so *driven* is not established. ⊕ **RAW coherence was worse than
useless**: the 30–40 Hz control band scored as high as the ratchet band on most routes, i.e.
command→torque coupling is **broadband**, so any coherence claim without the control-band
subtraction is meaningless. Recorded so it is not re-derived.
⭐ **The one informative detail**: `r1e` — the only route with **14** windows — shows by far the
largest specific effect (**+0.522** vs a shuffled p95 of +0.097, a 5x margin), while the seven-
window routes scatter around zero. That is the signature of a real effect seen at insufficient
power, not of a null.
⇒ **What would close it**: the same thing every open question here needs — **more continuous
engaged-creep windows.** At 14 windows the answer was unambiguous on the one route that had them.

## 🛑🛑 **THE COULOMB RELAY IS A *GRIND* LEVER, NOT A RATCHET LEVER — AND THE TWO SYMPTOMS DISSOCIATE**
The kit has blamed the command-proportional Coulomb relay (`FUN_0003b8f6`, knee `0xC40BC`)
for the engaged 6–9 Hz amplification since V80. **The nine scored routes span that knee over
10x, and the ratchet does not respond.**
```
   route build  knee  gain  friction | RATCHET  GRIND      (cs_tq excess, validated estimator)
   r78   V91     600  3564   204     |   9.8      6.1
   r7e   V96     600  3564   204     |  16.5     28.9
   r7f   V96     600  3564   204     |  32.9     14.3
   r96   V102    300  5346   204     |  49.4    248.2
   ra4   V104    300  5346   204     |  15.8     54.7
   ra6   V106    300  5346   204     |  67.8     25.3
   r1e   V107    300  5346   204     |  28.8     27.7
   r22   V112   1800  5346   612     |  35.8     15.0
   r24   V122   3000  5346  1020     |  33.2     14.0

   knee vs RATCHET   rho -0.06  p 0.874      <- NOTHING
   knee vs GRIND     rho -0.69  p 0.039      <- a real lever
```
✅ **[EVIDENCE] the clean GAIN-MATCHED comparison** (all four rows at gain 5346, so the
4x→6x step cannot explain it): knee 300 → 1800/3000 cuts the **grind 41.2 → 14.5 = 2.8x**
while the **ratchet moves 39.1 → 33.2 = 1.18x, inside its own 1.63x split-half floor.**
⚠ **[CONFOUND, stated]** knee and friction `0xC40D2` move together in that comparison
(204 → 612/1020), so the *grind* effect is knee-or-friction, not knee alone. **The ratchet
null is unaffected by that confound** — neither predictor moves it (friction ρ +0.30, p 0.44).
⇒ **the relay attribution for the RATCHET is withdrawn.** It remains a good grind lever.

### ⭐ EVERY LEVER THE KIT HAS PULLED IS A GRIND LEVER
Across **31 images V91→V122 only 278 bytes ever changed** — 0.027 % of the image:
```
   0x35A08-0x35A18 · 0x3AA96 · 0x55DF2-0x55E10 · 0xC40BC-0xC40DC · 0xC4B34-0xC4C03
   0xC4FFC-0xC4FFF · 0xC60A8-0xC60B6 · 0xC61B3-0xC61B5 · 0xC63AC · 0xC640B-0xC6447
   0xC649B · 0xC6AE7 · 0xC6CD0 · 0xC6FFC-0xC6FFF · 0xD6A6C-0xD6A71 · 0xD7A5C-0xD7A71
   untouched ENTIRELY: 0xC5000 model coeff · 0xC7000 · 0xC9000 damper tables · 0xCC000 gain arrays
```
Those 278 bytes include the **4x→6x LKAS gain**, **Lever B**, the **relay knee** and the
**friction** cells. They moved the **grind by 42x** and the **ratchet by nothing**.
✅ **[EVIDENCE] grind and ratchet are DISSOCIATED mechanisms** — same builds, same routes, same
estimator, opposite responses. They need separate levers, and every lever found so far is the
grind's.

### ⭐ THE SHARPEST REMAINING CLUE: TORQUE WITHOUT ANGLE
```
   ratchet margin over each channel's own slope-matched null
     tq 7.62 · cs_tq 7.42   <- the torsion bar
     ws_fr 4.41 · ws_fl 3.95
     cs_rate 1.03 · cs_ang 0.79 · ang 0.83 · wang 0.83   <- ANGLE: nothing
     sc_tq 0.56 · co_tqcan 0.59 · cc_req 0.67            <- COMMAND: nothing
```
✅ **[EVIDENCE] the ratchet is a TORQUE oscillation with no matching ANGLE oscillation.** It
twists the torsion bar without measurably moving the wheel — which is exactly how a driver
feels *ratcheting* rather than *shaking*, and it rules out anything that would have to move
the road wheels to be seen.
⇒ **[BELIEF] it is a motor-torque disturbance injected downstream of the command and upstream
of the bar, active only when engaged.** **What would close it**: a phase test at 8.64 Hz on
each engaged-gated contributor to the motor-torque sum, restricted to cells in the untouched
set above.

## 🛑🛑⭐ **THE RATCHET IS 100 % FIRMWARE-CAUSED — AND UNTOUCHED BY EVERY LEVER THE KIT HAS PULLED**
Three results that only make sense together, all from the validated slope-corrected excess
estimator with slope-matched nulls.

### ✅ 1. IT IS IN THE TORQUE CHANNEL, NOT WHEEL RATE — A 7x BETTER INSTRUMENT
```
   ratchet 5-12 Hz margin over each channel's OWN slope-matched null, mean of 4 routes
     tq        7.62      <- EPS/driver torque
     cs_tq     7.42
     ws_fr     4.41      <- front wheel speed, also real
     ws_fl     3.95
     cs_rate   1.03      <- THE INCUMBENT CHANNEL, AT CHANCE
     ang/wang/cs_ang  0.79-0.83
     sc_tq 0.56 · co_tqcan 0.59 · cc_req 0.67   <- the COMMAND: ratchet absent
```
✅ **[EVIDENCE] in `cs_tq` the ratchet is REAL on 9/9 routes** (excess 9.8–67.8 vs null 2.6–4.1).
✅ **[EVIDENCE] it is NOT in the command** — all three command channels sit below their nulls,
confirming the older *“not in openpilot's command”* claim with a validated estimator.
⚠ **This RETRACTS the “and ANGLE-RATE” half of that older claim**: wheel rate scores **1.03**,
i.e. chance. Every 6–9 Hz endpoint this kit has used was reading the wrong channel.

### 🛑 2. THIRTY-PLUS BUILDS HAVE NOT MOVED IT — AND THE TEST HAD THE POWER TO SEE IT
```
   band     channel   full-range rho    post-V102 rho        V102 vs rest
   GRIND    cs_tq     -0.02 (n.s.)      -0.94   p = 0.005    12.3x
   GRIND    tq        +0.03 (n.s.)      -0.94   p = 0.005    14.4x
   GRIND    cs_rate    0.00 (n.s.)      -0.83   p = 0.042    15.0x
   RATCHET  cs_tq     +0.50  p 0.168    -0.14   p = 0.787     1.6x
   RATCHET  tq        +0.42  p 0.262    -0.31   p = 0.544     1.9x

   ratchet PEAK FREQUENCY over nine builds: 8.64 +/- 0.64 Hz, CV 7.4 %, vs build rho -0.26 (p 0.51)
```
✅ **[EVIDENCE] the GRIND falls monotonically V102→V122 in THREE independent channels**
(ρ = −0.94, p = 0.005, replicated) ⇒ the kit's builds are measurably working on the grind.
🛑 **[EVIDENCE] the RATCHET does not move at all.** Observed spread is **6.9–8.3x** against a
split-half floor of **1.63–1.91x**, so a trend of ≥1.9x would have shown. Its frequency is pinned
at **8.64 Hz ± 7.4 %** across V91→V122. The weak full-range ρ is **POSITIVE** — if anything newer
builds ratchet slightly *more* — though not significantly.

### ⭐⭐ 3. AND YET IT EXISTS ONLY WHEN ENGAGED — SO FIRMWARE CREATES IT OUTRIGHT
```
   route build   engaged exc / null    manual exc / null    ratio    speed-matched?
   r78   V91     11.7 / 4.7            3.2 / 4.6            3.63     no (2.8 km/h)
   r7e   V96     11.5 / 4.7            2.4 / 4.7            4.82     YES
   r7f   V96     93.6 / 4.2            2.6 / 4.0           35.64     YES
   r96   V102    55.4 / 4.6            2.0 / 5.0           27.73     YES
   ra6   V106    48.0 / 4.5            2.7 / 4.1           17.90     no (5.0 km/h)
   r1e   V107    17.1 / 2.9            2.5 / 4.5            6.92     no (2.9 km/h)
   r24   V122    32.5 / 4.5            2.7 / 4.6           12.09     YES

   engaged arm beats its null on 7/7 routes ; manual arm on 0/7
   speed-matched ratio median 19.91x  [4.82, 35.64]
```
✅ **[EVIDENCE] there is NO ratchet peak in manual driving at the same speed** — the manual arm
sits *below* its own null on every route. This is not a mechanical resonance that engagement
amplifies; **engagement CREATES it.**
⚠ **SUPERSEDES the recorded “engaging amplifies 6–9 Hz by 2.8x”** — that figure came from the
tilt-confounded band ratio, which dilutes a peak into its neighbourhood. The validated
contrast is **~20x**, and the manual arm has no peak at all.

### 🛑 WHAT THIS MEANS FOR THE SEARCH — THE LEVER IS ONE WE HAVE NEVER TOUCHED
The three results are only consistent one way: **the ratchet is entirely firmware-caused, and
every calibration lever pulled between V91 and V122 is orthogonal to it.** So it is not
mechanical, not unreachable, and not a measurement failure — **it is a live firmware path at
8.6 Hz, engaged-only, that no build in this kit has yet modified.**
⇒ the question is no longer *“is there a lever?”* but **“which engaged-only path is live at
8.6 Hz that V91–V122 all left byte-identical?”** — answerable by intersecting the engaged-gated
code with the set of cells no build has touched.
⚠ **[BELIEF, not EVIDENCE]** that the responsible path is reachable by calibration at all; it may
need a structural edit. **What would close it**: the intersection above, then a phase test at
8.6 Hz on each candidate.

## 🛑🛑 **THE SPECTRAL TILT CONFOUNDED EVERY 6–9 Hz ENDPOINT — THREE MEASURES WITHDRAWN, ONE SURVIVES**
Chasing why the ratchet Q showed no build trend produced a chain of retractions and one
durable positive result. **The wheel-rate signal is RED**, slope **1/f^0.80 to 1/f^2.37**
across routes — and that tilt alone reproduces everything the old measures reported.
```
   CONTROL: coloured noise, NO resonance whatsoever, nperseg=512, 8 segments
     1/f^1.5  ->  prominence 27.4   fitted Q 1.00   fit r2 0.585
     1/f^2.0  ->  prominence 64.9   fitted Q 1.00   fit r2 0.710
   REAL ROUTES:   prominence 12.2-173.3   fitted Q 1.0-17.6   r2 0.28-0.87
```
❌ **WITHDRAWN — fixed-floor prominence**: comparing 5–12 Hz against a 28–40 Hz floor is large
by construction on any red spectrum. ❌ **WITHDRAWN — fitted Lorentzian Q**: returns Q≈1 with
r² 0.6–0.7 on pure coloured noise, which is exactly what the real routes gave. ❌ **WITHDRAWN
— long-window half-power Q**: white noise alone returns **Q 21.7–29.1** at nperseg=1024, the
same range as the "real" 15.8–21.4, and it **cannot separate true Q=5 from true Q=20**.
⇒ the 0.6×ceiling guard I added earlier is **insufficient** — it rejects white noise but not
coloured, and the routes are coloured.

### ✅ WHAT SURVIVES — SLOPE-CORRECTED EXCESS WITH A SLOPE-MATCHED NULL
Fit the route's **own** power law over 3–40 Hz using only bins **outside** the bands under
test, measure the peak's excess over it, and null it at **that route's measured slope**:
```
   band              excess        slope-matched null p95    verdict
   GRIND 15-25 Hz    9.9 - 421.9   2.6 - 4.1                 REAL on 9/9 routes  (3-100x margin)
   RATCHET 5-12 Hz   2.0 - 8.9     2.7 - 4.1                 real on only 6/9    (1.1-2.3x)
```
✅ **[EVIDENCE] the grind resonance is unambiguous; the ratchet is marginal IN THIS CHANNEL.**
That is the real reason every 6–9 Hz endpoint has underperformed — **the feature is 10–50x
weaker in wheel rate**, a signal-strength problem, not a noise problem. More episodes cannot
fix it; a different channel might.
✅ **[EVIDENCE] and the excess orders by build**: **V91 9.9 → V102 421.9 → V122 23.2**. The 42x
jump lands on the 4x→6x gain step, and the kit has clawed it back to **2.3x above V91's
4x-gain level** — independently matching the earlier Q ordering (9.00 at V102 → 4.50 at V122).

### 🛑 AND IT RETRACTS AN INFERENCE RULE I HAD ALREADY COMMITTED
The pre-registration said *“Q RISING above 4.50 falsifies the damping account → fly V167”*.
**Half-power Q is NON-MONOTONE**: its null sits **ABOVE** the data (real 13.7–34.7 vs null p95
**58–78**), because on a noisy median periodogram the half-power crossing lands on an adjacent
bin. Adding damping lowers Q, but once the peak weakens toward the floor **Q rises again
toward the noise value** ⇒ **a rise cannot distinguish “damping failed” from “damping
worked”**, which is precisely the discrimination the drive was for. **Corrected**: excess is
monotone in peak strength and carries the one-sided logic without the defect.

### ✅ THE DRIVE REQUIREMENT, NOW A MEASURED NUMBER
```
   split-half floor vs windows per half:  3 -> 2.23x    6 -> 1.57x   (extrapolates ~1.2-1.3x at 12-16)
   a continuous pass of T s yields floor((T-5.12)/2.56)+1 windows:  15 s -> 4,  10 s -> 2
   V158's predicted effect is 1.68-2.74x  =>  needs ~24-32 windows
   => 8 passes of 15 s = 32 windows (ADEQUATE);  8 of 10 s = 16 (marginal)
```
⊕ New tool `rlog-tools/score/score_band_excess.py` — the validated estimator, its
slope-matched null, and the split-half floor, with the window warning built in.

## 🛑🛑 **MY RATCHET Q WAS AN ARTEFACT OF THE WINDOW — AND IT EXPLAINS EVERY 6–9 Hz FAILURE**
Having found Q works at 21 Hz, I measured it at the ratchet's own 5–12 Hz. **There IS a resonance
there** — peak 5.5–8.6 Hz, prominence **17–68x** on all nine routes — but its Q showed no build trend,
which was suspicious given how cleanly the 21 Hz Q tracked. It is a **resolution artefact**.
```
   Welch nperseg = NW//2 = 128 at 100 Hz  =>  df = 0.781 Hz
   largest resolvable Q at frequency f  =  f / (2 * df)

   at  7.8 Hz  ceiling = 5.0    measured 1.17-5.50   <- PINNED AT THE CEILING
   at 21.0 Hz  ceiling = 13.4   measured 4.50-9.00   <- comfortably below, VALID
```
✅ **[EVIDENCE] memory's ring-down puts the ratchet at ζ 0.017–0.036, i.e. Q = 14–29.** At df = 0.78 Hz
that is **unmeasurable** — the half-power width would be 0.27–0.56 Hz, narrower than one bin.
⇒ **the 5–12 Hz Q values I reported are the WINDOW's width, not the resonance's. Withdrawn.**
✅ **The 15–25 Hz Q measurement STANDS** — 4.50–9.00 against a ceiling of 13.4, so it is measuring the
resonance and not the window. Everything built on it is unaffected.

### ⭐ AND THIS EXPLAINS A LONG-STANDING PUZZLE
Every 6–9 Hz endpoint this kit has tried has performed badly — the band ratio resolves **1 route in
9**, and the CIs are enormous. **The reason is structural: the ratchet is too NARROW to resolve in a
2.56 s window.** Its energy is smeared across bins, so band sums mix it with neighbouring content and
Q pins at the ceiling. **This is not a noise problem to be beaten with more episodes; it is a
resolution problem, and only a longer window fixes it.**

### ✅ THE DRIVE REQUIREMENT THAT FOLLOWS
```
   to resolve Q = 29 at 7.8 Hz needs df <= 0.134 Hz  =>  nperseg >= 744  =>  >= 7.4 s of
   CONTINUOUS engaged creep per analysis window
```
⇒ **the drive needs engaged creep passes of >= 10-15 s CONTINUOUS each**, not merely many short ones.
⊕ This sits alongside, not against, the existing *“8+ separate passes”* requirement — both are met by
**8+ passes of 10-15 s each**, which is also just a natural slow lap of a car park.
⊕ A resolution guard is now in `peak_q`: it returns **NaN when the measured Q exceeds 0.6x the
window's ceiling**, so the scorer can never again report a window artefact as a damping measurement.

## ✅ **Q's BUILD-ORDERING IS NOT GAIN-CONFOUNDED — AND THE GAIN COST ~2x IN DAMPING RATIO**
```
   build   Q      gain    knee   alpha2
   V91     5.20   3564     600     22      4.00x gain
   V96     4.67   3564     600     22      4.00x
   V102    9.00   5346     300     22      6.00x   <- Q JUMPS at the gain step
   V104    7.25   5346     300     22      6.00x
   V106    7.67   5346     300     22      6.00x
   V107    6.67   5346     300     22      6.00x
   V112    6.50   5346    1800     14      6.00x
   V122    4.50   5346    3000      8      6.00x
```
✅ **[EVIDENCE] the V102→V122 fall is NOT gain-confounded** — the gain is **constant at 5346 across the
whole run**, so the 9.00 → 4.50 decline is attributable to the other cals, not to the gain.
✅ **[EVIDENCE] V158 does not touch the gain** (`0xC6CD0` = 5346 on V122 and V158 alike), so the
V122→V158 comparison is clean on this axis too.
✅ **[EVIDENCE] V122's Q = 4.50 is BELOW the 4x baseline mean of 4.94** ⇒ the kit's builds have not
merely recovered the damping the gain raise cost, they have slightly exceeded it.

### ⚠ AND THIS CHALLENGES A STANDING CLAIM
Memory records: *“The 4x LKAS gain … scales **EXCITATION, not loop gain**.”* **Q disagrees.** Q is a
**shape** parameter: if the gain scaled only excitation, the resonance would grow in amplitude but
**Q would be unchanged**. Q went **4.67 → 9.00** at the gain step — the peak got **sharper**, not just
taller. **A gain that changes Q is acting inside the loop.**
⇒ that gives the operator's 8x experience (*more* grinding) a mechanism it did not previously have:
raising the gain **reduces the damping ratio** rather than merely amplifying what is there.
⚠ **[BELIEF, not EVIDENCE] — the step is CONFOUNDED**: V96→V102 spans several builds (V100, V101,
V102), not the gain alone, and there are only **two routes** at 4x. The Q jump lands exactly on the
gain change, which is suggestive, but this does **not** isolate it. **What would close it**: any route
at 4x gain with otherwise V122-like cals, or a deliberate single-variable gain build — which the
operator has already ruled out on other grounds.
⊕ It does **not** change the recommendation: the gain stays frozen at 6x, and **nothing here suggests
raising it.** If anything it strengthens the existing rule against 8x by supplying the missing why.

## ✅✅✅ **A BETTER ENDPOINT: Q OF THE 15–25 Hz RESONANCE — AND IT MAKES V158 DETECTABLE**
Testing the prediction's assumption (2) — *is the band resonance-limited?* — answered it and produced
a better instrument at the same time.

### ✅ THE BAND IS STRONGLY RESONANCE-LIMITED ON EVERY ROUTE
```
   route  build   peak Hz   prominence vs 28-40 Hz floor   Q
   r96    V102     21.09            610.3                 9.00
   ra4    V104     ~                 ~                    7.25
   ra6    V106     17.97             66.5                 7.67
   r1e    V107     15.62             53.3                 6.67
   r22    V112     20.31             35.5                 6.50
   r24    V122     21.09             32.2                 4.50
```
✅ **[EVIDENCE] assumption (2) HOLDS** — prominence 32–610x above the floor, so amplitude does scale
with 1/damping there and the V158 prediction's basis is sound.
✅ **[EVIDENCE] Q has FALLEN 9.00 → 4.50 across the build sequence** ⇒ ζ = 1/(2Q) rose **0.056 →
0.111, a 2x damping increase** — a direct measurement of the kit's builds adding damping, independent
of the engaged/manual ratio entirely.

### ⭐ AND Q IS A MUCH BETTER INSTRUMENT THAN THE BAND RATIO
```
   Q split-half reproducibility     median 1.20x   p90 1.50x   max 2.00x   (9 routes)
   band-ratio reproducibility       median 1.72x   p90 2.93x   max 3.60x
```
Q is a **SHAPE** parameter, so it is immune to the level shifts that inflate the ratio's noise — the
same level shifts the acoustic uniformity guard had to be built to catch.
```
   V122 reference Q = 4.50
   V158 predicts Q -> 1.64 .. 2.68   (the x1.68-2.74 damping increase)
   that is a x1.68-2.74 change against a 1.20x median / 1.50x p90 floor
   => DETECTABLE, where the band ratio was NOT
```
✅ **This converts V158's drive from “likely unresolvable” to “detectable with margin”.** Added to the
scorer as the PRIMARY instrumented endpoint, with its own split-half reproducibility printed per drive
and a prominence guard (Q is not reported when prominence < 3).

### ⚠ ONE HONEST WRINKLE
On r24 the **pooled** Q is **4.50** while its two halves give **6.00 and 6.75** — pooling more windows
shifts the half-power points, so the pooled estimate is not the average of its halves. The comparison
stays valid because **both sides use the same procedure**, but it means the split-half figure may
**understate** the pooled estimate's true uncertainty. Recorded rather than smoothed over.
⊕ The one-sided logic is unchanged and now sharper: **Q RISING above 4.50 falsifies the damping
account** and points at the Path-2 pumping branch, whose build (V167) already exists.

## ✅✅ **V158 DOES HAVE A FALSIFIABLE PREDICTION — IT IS JUST ONE-SIDED**
V158 had no instrumented prediction at all, which left the drive unfalsifiable on that axis. The
damping arithmetic supplies one, and its **asymmetry** is what makes it useful.
```
   Path-2 case          net added      total viscous     vs baseline 1.571
   worst  (39 % nom)      1.066           2.637              x1.68
   best   (72 % nom)      1.968           3.539              x2.25
   ignored (100 %)        2.733           4.304              x2.74

   IF firmware damping dominates AND the band is resonance-limited (amplitude ~ 1/damping):
       predicted 18-22 Hz   3.88  ->  1.42 .. 2.32
   IF mechanical damping dominates, the effect shrinks toward x1.00 (no change).
   => honest range: 3.88 -> 1.42 .. 3.88, i.e. a x1.00 to x2.74 REDUCTION
   => against a floor of 1.72x median / 2.93x p90 / 3.60x on r24 itself,
      A REDUCTION IS LIKELY UNRESOLVABLE.
```

### ⭐ BUT THE OTHER DIRECTION IS SHARP
**Nothing in the damping account predicts an INCREASE.** Every mechanism in V158 — FactorC lifted,
FactorE's dead zone opened — adds a term that opposes motion in Path 1. So:
```
   V158 reads clearly ABOVE 3.88  (outside [1.60, 10.87] high, or above r24's own half-split 7.56)
       => the damping account is FALSIFIED
       => and it is evidence for the ONE named risk: the Path-2 PUMPING copy dominating
       => which has a BUILT answer, V167 (0xC63A0 1024 -> 512), that halves exactly that term
```
✅ **So the drive is falsifiable even though the positive direction is underpowered.** An underpowered
two-sided test becomes a usable **one-sided discriminator**, and the branch it discriminates into
already has its build cut.
⚠ **[ASSUMPTIONS, stated because the range depends entirely on them]** (1) firmware viscous damping is
a non-trivial share of the plant's total damping — unmeasured; (2) the 18–22 Hz band is
resonance-limited so amplitude scales as 1/damping — plausible but unverified at that band;
(3) the Path-2 net is inside the stability-bounded 39–100 % window. **Any of these failing collapses
the predicted reduction toward x1.00; none of them can produce an increase.** That asymmetry is the
part worth trusting.

## ✅ **ALL 24 UNFLOWN BUILDS TRIAGED AGAINST THE DETECTION FLOOR — ONLY V138 CLEARS IT**
Swept every built-but-unflown image through `eps_closed_loop_sim.ratio_filter`.
```
   V137   alpha2 8->5    lane ratio @20Hz 0.7462   x1.34 reduction   BELOW the 1.72x floor
   V138   alpha2 8->2    lane ratio @20Hz 0.3364   x2.97 reduction   CLEARS
   the other 22 builds -- V139..V167, including V158/V160/V164/V165/V167 --
       no change on the gp-0x6b26 lane, so this simulator cannot price them
```
✅ That is a **limit of the tool, not a defect in those builds**: `ratio_filter` covers the b26 lane
only. V158's damper is `gp-0x6bd0`, Lever B is r24, the deadband builds are elsewhere. And the golden
model does not simulate the damper cascade either — it takes `gp-0x6bd0` as an *input* to the
aggregator. **So V158's prediction rests on the physical-units argument (0.000 → 1.05–1.96 ct/(deg/s)
net), and no tool in the kit can convert that into a predicted band ratio.**

### ⚠ WHICH EXPOSES A REAL TENSION, WORTH STATING RATHER THAN HIDING
```
                  mechanism                     instrumented outcome
   V158   STRONGEST -- broadband viscous        UNPREDICTABLE, and likely below the floor
          damping, quantified, targets the      (the 6-9 Hz band resolves 1/9 routes;
          actual symptom at the actual band)     18-22 Hz needs a ~3.6x move at V122)
   V138   WEAKER -- an EMA corner moved from    PREDICTED x2.97, tool-backed, CLEARS the floor
          19.9 Hz to 5.0 Hz
```
⇒ **For a drive meant to FIX the car, V158 is the better bet.** Its mechanism is the strongest in the
kit and it is the first build ever to deliver damping where the symptom lives.
⇒ **For a drive meant to LEARN something instrumented, V138 is more informative** — it is the only
unflown build whose predicted effect clears the measured floor.
✅ **This does not reopen the V137 question**: V137 is below the floor on the same arithmetic and stays
withdrawn. **V158 remains the recommendation**, because the pre-registration's PRIMARY endpoint is the
operator's report, not the instrument — and what he feels can move even when the band ratio cannot
resolve it. **V138 is the follow-up if he wants a number rather than a verdict.**

⭐ **THE GENERAL POINT**: *“which build should fly”* and *“which build will produce a readable
measurement”* are **different questions with different answers**, and this kit has been conflating
them. Naming both, per build, is more useful than ranking builds on one axis.

## ✅✅ **THE V158-vs-V137 AMBIGUITY IS RESOLVED — V137 IS PREDICTED BELOW THE INSTRUMENT FLOOR**
Last tick I handed the operator a choice between V158 and V137 and called it *“his call”*. **That was
premature** — the kit's own closed-loop simulator can price alpha2, and it says the two are not
comparable.

### ✅ alpha2 HAS A REAL MECHANISM: IT IS AN EMA COEFFICIENT, `>>6`, READ AT `0x41626`
```
   alpha2   a=al/64   corner Hz   |H|@20Hz   |H|@7.8Hz   flown as
     22      0.3438      54.7       0.959      0.993     V91-V107
     14      0.2188      34.8       0.892      0.981     V112
      8      0.1250      19.9       0.729      0.939     V122   <- corner INSIDE the 18-22 band
      5      0.0781      12.4       0.544      0.857     V137 (unflown)
      2      0.0312       5.0       0.245      0.544     V138 (unflown)
```
⚠ But the **open-loop** magnitude does not explain the history: alpha2 22→8 gives **x0.76** while the
measured excess fell **x0.067 (15x)**. A 1.3x open-loop change cannot produce a 15x drop ⇒ either the
loop amplifies it, or the collinear knee/K1 did the work.

### ✅ THE KIT'S OWN SIMULATOR PRICES IT — USING ONLY THE PART IT SAYS TO TRUST
`eps_closed_loop_sim.py`'s header is explicit: the **lane arithmetic is exact and validated against
Ghidra**, while **the plant is only identified 5–~13 Hz** and every routine that uses it above 13 Hz
raises. So I used `ratio_filter`, which is lane-only, and avoided the plant entirely.
```
   pair            lane ratio @20 Hz    measured 18-22 Hz change
   V112 -> V122         0.8172          7.10 -> 3.88 = x0.55     <- VALIDATES the method
   V122 -> V137         0.7462          (unflown)
   V122 -> V138         0.3364          (unflown)
```
✅ **The V112→V122 step validates it**: lane predicts 0.82, measured 0.55 — same direction, right
order, the measured change slightly larger than the lane alone, which is what a closed loop gives.

### ⛔ AND THAT SETTLES THE CHOICE
```
   detection floor (measured, 9 within-drive replicates)   median 1.72x   p90 2.93x

   V137   predicts x0.746  =  a 1.34x reduction   ->  BELOW THE FLOOR, not detectable
   V138   predicts x0.336  =  a 2.97x reduction   ->  at the p90 floor, MARGINAL
```
⇒ **V137 would most likely produce “not resolved” and teach nothing.** It is not a defensible
alternative to V158; **I overstated it last tick and am withdrawing that framing.**
✅ **V158 is the flight.** If the operator later wants the alpha2 axis, **V138 (alpha2 2) is the
version worth a drive**, because it is the one whose predicted effect clears the floor — and it is
already built.
⚠ **[NOTE] `ratio_filter` prices the `gp-0x6b26` LANE, not the measured `cs_rate` band.** The two are
coupled through the loop but are not the same signal, so these are **input-side predictions**, not
direct forecasts of the endpoint. The V112→V122 agreement is one point of empirical support, not a
calibration.

⭐ **THE LESSON**: I offered a choice where the kit already had the arithmetic to decide. **Before
handing the operator an “either/or”, check whether an existing tool can price both options** — here it
took one call to a simulator that was written for exactly this question.

## ⚠ **AN ALTERNATIVE FIRST FLIGHT EXISTS — V137, ALREADY BUILT AND UNFLOWN**
Correlating the measured 18–22 Hz excess against the kit's pre-specified load-bearing cals across the
eight builds with flown routes:
```
   build  18-22Hz   gain  LeverB  knee   K1   alpha2   path2w  b26clamp
   V91     11.81    3564   5244    600   204    22      1024      511
   V96     14.24    3564   5244    600   204    22      1024      511
   V102   742.19    5346    512    300   204    22      1024      511   <- Lever B OFF, worst
   V104   327.51    5346   5244    300   204    22      1024      511   <- Lever B restored
   V106    87.17    5346   5244    300   204    22      1024      511
   V107    57.93    5346   5244    300   204    22      1024      511
   V112     7.10    5346   5244   1800   612    14      1024      511
   V122     3.88    5346   5244   3000  1020     8      1024      511

   knee r = -0.730 | K1 r = -0.648 | alpha2 r = +0.657 | the rest are constant
```
🛑 **EXPLORATORY ONLY: n = 8, and knee/K1/alpha2 moved TOGETHER at V112 and V122.** They are
collinear and **cannot be separated by this data.** No causal claim is made for any one of them.

### ✅ WHAT IS SOLID ENOUGH TO ACT ON
Two things survive the confounding:
1. **Lever B off vs on**: V102 (512) reads **742**, the worst in the set; restoring it at V104 drops to
   **328**. Consistent with V88's measured single-variable result. Lever B stays.
2. **The knee/K1/alpha2 axis moved the endpoint twice**, 57.9 → 7.1 → 3.88. Whatever the split between
   the three, **that axis is the only one with a replicated on-car association with this endpoint.**

### ⚠ SO THERE IS A DEFENSIBLE ALTERNATIVE TO FLYING V158 FIRST
```
   V137   V122 + alpha2 8 -> 5    ONE halfword (5 bytes with CRC)   BUILT, UNFLOWN
   V138   V122 + alpha2 8 -> 2    ONE halfword                      BUILT, UNFLOWN
```
**The two builds answer different questions, and both are legitimate:**

| | V158 | V137 |
|---|---|---|
| rationale | the golden model's own damper prescription, sized at the measured operating point | continue the axis that has twice moved the endpoint on-car |
| mechanism | **strong** — broadband viscous damping, quantified in ct/(deg/s) | **weak/confounded** — collinear with knee and K1 |
| on-car history at creep | **none** | **two steps, both in the right direction** |
| size | 6 halfwords | 1 halfword |

✅ **V158 remains my recommendation**, because its rationale is mechanistic and its dose is sized
against a measured operating point, where V137's support is an n=8 correlation on collinear cals.
⚠ **But if the operator prefers to continue what has demonstrably been working rather than test a new
mechanism, V137 is the build for that, it is already built, and it is one halfword.** That is his call,
not mine, and it is cheap either way — both are cal-only and reversible.

## ⛔ **PAIRED SPEED-MATCHING IS WORSE — AND I AM STOPPING THE ESTIMATOR TUNING THERE**
The instrument's limit is its noise floor, so the obvious move is to lower it. The current speed match
is a percentile **filter**, not a **pairing**; matching each engaged window to a nearest-speed manual
window should cancel more variance. **Tested on the same nine routes, it does the opposite.**
```
   route  build   UNPAIRED A/B   PAIRED A/B
   r78    V91         1.72          1.08
   r7e    V96         1.44          3.63
   r7f    V96         1.29          1.01
   r96    V102        1.48          1.64
   ra4    V104        2.13          2.97
   ra6    V106        1.11          2.18
   r1e    V107        1.82          4.98
   r22    V112        2.76         11.43
   r24    V122        3.60          3.52
   ---------------------------------------------------------
   UNPAIRED   median 1.72x   p90 2.93x   max  3.60x
   PAIRED     median 2.97x   p90 6.27x   max 11.43x
```
✅ **[EVIDENCE] pairing is ~1.7x WORSE at the median and 2x worse at p90.** Two reasons: it **discards
every window without a partner within 0.75 km/h**, so *n* collapses; and a **median of individual
ratios** is a noisier statistic than a **ratio of medians**, because each individual ratio carries the
noise of two windows rather than of two pooled distributions. **The existing design stands.**

### ⭐ AND I AM STOPPING HERE, DELIBERATELY
There are more variants to try — a narrower 19–21 Hz band, log-space averaging, a trimmed mean. **I am
not going to try them.** With **nine routes**, differences below roughly 20 % in split-half scatter are
not distinguishable, and selecting the best of several estimators **by the same statistic used to judge
them** is exactly the selection that manufactures an apparent improvement. That is the tuning analogue
of the window bootstrap this session already had to remove.
✅ **One principled alternative was pre-specified, tested, and lost. The instrument is what it is:
median 1.72x, p90 2.93x, and 3.60x at the reference build.** Those are the numbers the V158 drive will
be judged against, and they were fixed before the drive rather than chosen after it.

## ⚠⚠ **THE INSTRUMENT IS RUNNING OUT OF RANGE — AND I MUST WALK BACK LAST TICK'S PREDICTION**
Replaced the single cross-route replicate with **nine within-drive split-half replicates**: split each
route's episodes in half, score each half independently, compare.
```
   route  build   half A    half B     A/B
   r78    V91      13.74      7.97    1.72x
   r7e    V96      10.49     15.15    1.44x
   r7f    V96      19.10     14.77    1.29x
   r96    V102    787.68    531.49    1.48x
   ra4    V104    321.67    150.78    2.13x
   ra6    V106    108.85     98.31    1.11x
   r1e    V107     46.16     83.92    1.82x
   r22    V112      4.95     13.65    2.76x
   r24    V122      2.10      7.56    3.60x   <- the REFERENCE build, and the WORST
   -------------------------------------------------------------
   median 1.72x    p90 2.93x    max 3.60x
```
✅ The old 1.84x was **accurate, not optimistic** — it sits at the median. But it was **the wrong
number to use**, because reproducibility is **worst where the excess is smallest**, and V122 is the
smallest. As the ratio approaches 1 the noise stops shrinking with it.

### ⚠ WHAT V158 WOULD ACTUALLY HAVE TO DO
```
   to clear the 1.72x median floor  ->  V158 must read <= 2.26
   to clear the 2.93x p90 floor     ->  V158 must read <= 1.32
   to clear r24's own 3.60x         ->  V158 must read <= 1.08
   and a ratio of 1.0 means engaged == manual: the excess is GONE
```
⇒ **V158 is instrumentally detectable only if it very nearly ELIMINATES the engaged excess.** Last
tick I wrote *“detectable if the move exceeds ~1.84x”*. **That was too generous** — it used the median
floor where V122's own route sits at 3.60x. **Corrected.**

### ✅ AND IT REFRAMES THE SIX-BUILD TREND HONESTLY
```
   V102 -> V104   2.27x   marginal
   V104 -> V106   3.76x   RESOLVED
   V106 -> V107   1.50x   BELOW FLOOR
   V107 -> V112   8.16x   RESOLVED
   V112 -> V122   1.83x   marginal
   cumulative     191x    far above the floor
```
✅ **Individual build steps are mostly NOT resolved; the CUMULATIVE trend is.** The monotone run is
carried by two large steps (V104→V106, V107→V112). ⚠ In particular **V112→V122 (1.83x) is marginal**,
so the endpoint did not independently confirm the operator's V122 verdict — it is consistent with it,
which is a weaker claim and the one that is supported.

⭐ **THE LESSON**: an instrument validated over a 191x range is not thereby validated at the bottom of
that range. **Calibrate the floor AT THE OPERATING POINT you will actually use it at.** I validated on
the full sweep and then quoted a detection threshold from the median, while the reference build sits
at the noisy end.

## ✅✅✅ **THERE IS A WORKING CROSS-BUILD INSTRUMENT AFTER ALL — AND IT HAS TRACKED THE KIT FOR SIX BUILDS**
The 18–22 Hz within-drive engaged/manual ratio, paired with each route's build tag from its own cache:
```
   route  build   18-22 Hz eng/man
   r78    V91          11.81
   r7e    V96          10.02
   r7f    V96          18.46          <- the ONLY within-build replicate
   r96    V102        742.19          <- peak
   ra4    V104        327.51
   ra6    V106         87.17
   r1e    V107         57.93
   r22    V112          7.10
   r24    V122          3.88          <- the build now on the car

   V102 -> V122: SIX consecutive builds, STRICTLY MONOTONE DECREASING, 191x total
   corr(build number, log10 excess) = -0.920
   within-build scatter (V96, two routes) = 1.84x   =>  signal/noise ~104x
```
✅ **[EVIDENCE] the endpoint tracks the operator's own verdict**: he called V112 *“the best firmware
yet … least ratcheting ever”* and V122 better still — and the statistic falls 7.10 → 3.88 across
exactly that pair, after falling 742 → 7.10 over the four builds before it.

### ⭐ WHY THIS DOES NOT CONTRADICT THE RECORDED 20–36x BETWEEN-BUILD FLOOR
That floor was measured on **absolute band amplitude between routes** — six routes with identical
control cals spanning 19.9x, another six spanning 36.2x. This is a **within-drive RATIO**, which
cancels road, tyre, weather, alignment and the speed profile before any cross-build comparison happens.
**Same lane, different quantity.** ⊕ This is the third time this session that two records looked
contradictory and turned out to measure different quantities (see also
`gp-0x6bbe` slope-vs-magnitude). **Check the quantity before calling it a contradiction.**

### ✅ SO V158 CAN BE SCORED AGAINST V122's 3.88
The pre-registration's *“expect NOT RESOLVED”* stands for **6–9 Hz**. For **18–22 Hz** there is now a
concrete reference and a concrete prediction:
```
   V122 reference        3.88   [1.60, 10.87]
   V158 predicts         LOWER -- the damper is broadband viscous and opposes motion at 18-22 Hz too
   detectable if         the move exceeds the ~1.84x within-build scatter
   no effect looks like  ~3.9, inside [1.60, 10.87]
```

### ⚠ WHAT THIS RESTS ON — STATED PLAINLY
**[BELIEF, not EVIDENCE] the 1.84x scatter figure rests on ONE within-build replicate** (V96's two
routes). It is the weakest link and everything downstream inherits it.
🛑 **TIME IS COLLINEAR WITH BUILD NUMBER.** Tyre wear, season, road surface and the operator's own
driving all advance monotonically with build order too. A monotone run of six has a chance probability
of ~1/360, so the ordering is unlikely to be coincidence — **but “the builds caused it” and “something
else that also advances with time caused it” are not separated by this data.** The V158 drive is a
genuine test precisely because V158 is a large, single, *known* change against V122.

## 🛑🛑 **SCORE V158 AT 18–22 Hz, NOT 6–9 Hz — THE INSTRUMENT CAN ONLY SEE ONE OF THEM**
Ran both bands through the null gate on every route with a computable null.
```
   route  manEp   6-9 Hz  eng/man         18-22 Hz eng/man          resolves
   r1e      5     3.19 [ 1.67,   6.84]    57.93 [ 28.82, 111.51]    18-22
   r22      4     0.57 [ 0.23,   2.45]     7.10 [  1.29,  17.21]    neither
   r24      5     0.20 [ 0.04,   0.86]     3.88 [  1.60,  10.87]    18-22
   r78      5     1.17 [ 0.44,   2.07]    11.81 [  3.52,  25.51]    neither
   r7e      6     2.19 [ 0.69,   5.26]    10.02 [  4.01,  38.80]    18-22
   r7f      6     1.76 [ 0.35,  19.03]    18.46 [  4.75,  30.64]    18-22
   r96      5     1.04 [ 0.54,   4.45]   742.19 [291.03,1422.98]    18-22
   ra4      4     4.83 [ 0.57,  13.59]   327.51 [ 22.53, 655.22]    18-22
   ra6      7    11.58 [ 3.53,  33.37]    87.17 [ 35.87, 404.97]    BOTH
   ------------------------------------------------------------------------
   6-9 Hz   resolved 1/9        18-22 Hz resolved 7/9
```
✅ **[EVIDENCE] the 18–22 Hz band is a ~7x more sensitive instrument than 6–9 Hz.**
✅ **[EVIDENCE] a large, REPLICATED phenomenon**: the engaged/manual ratio at 18–22 Hz is **> 1 on all
nine routes**, spanning **3.88 to 742** — engagement multiplies that band at creep on every drive
measured. 6–9 Hz scatters around 1 (0.20–11.58) with **no consistent direction**.

### ⚠ CORRECTION TO MY OWN PRE-REGISTRATION
I designated 18–22 Hz a *“built-in control that should not move”* because Lever B is unchanged
V122→V158. **That was wrong.** V158's damper is `-sign(rate) x f(|rate|)` — a **BROADBAND VISCOUS**
term whose LERP is on rate MAGNITUDE, not on frequency. It opposes motion at **all** frequencies, so
it should reduce 18–22 Hz as well as 6–9 Hz.
⇒ **18–22 Hz is an ENDPOINT for V158, not a control** — and it is the only endpoint the instrument
can actually resolve.

### ✅ THE REVISED SCORING PLAN
```
   PRIMARY (instrumented)   18-22 Hz engaged/manual at creep, null-gated   resolves 7/9
   SECONDARY                 6-9 Hz  -- the symptom's own band, but         resolves 1/9
                             expect NOT RESOLVED; that is the floor
   CONTROL                  30-40 Hz, unchanged
   PRIMARY OVERALL          the operator's report -- unchanged
```
⚠ **A caveat that must travel with this**: because Lever B also lives at 18–22 Hz and is unchanged
between V122 and V158, a move there is attributable to the damper **only because Lever B is
byte-identical across the pair** — verified. On any future build that touches BOTH, 18–22 Hz stops
being attributable.

## 🛑🛑 **POWER ANALYSIS ON REAL DATA — THE 6–9 Hz SCORER RESOLVES 1 ROUTE IN 23**
Ran the validated scorer over **every cached route** to answer, before the drive, whether the band
instrument can detect V158 at all.
```
   route  engEp  manEp   6-9 Hz  eng/man        verdict
   r1e     22      5     3.19  [ 1.67,   6.84]  not resolved
   r22      9      4     0.57  [ 0.23,   2.45]  not resolved
   r24     10      5     0.20  [ 0.04,   0.86]  not resolved
   r78     15      5     1.17  [ 0.44,   2.07]  not resolved
   r7e     16      6     2.19  [ 0.69,   5.26]  not resolved
   r7f     19      6     1.76  [ 0.35,  19.03]  not resolved
   r81      4      4     6.10  [ 3.27, 122.43]  no null (too few episodes)
   r96     16      5     1.04  [ 0.54,   4.45]  not resolved
   ra4     20      4     4.83  [ 0.57,  13.59]  not resolved
   ra6     15      7    11.58  [ 3.53,  33.37]  *** RESOLVED ***
   + 13 further routes: NO MATCHED CREEP ARMS AT ALL
```
✅ **[EVIDENCE] 10 of 23 routes are scoreable; 1 of those 10 resolves.** ⇒ **the 6–9 Hz band scorer
resolves roughly ONE DRIVE IN TWENTY-THREE.**

### 🛑 SO SET EXPECTATIONS HONESTLY, BEFORE THE DRIVE
**The band scorer is unlikely to detect V158's effect.** That is not a defect in V158 and not a defect
in the scorer — it is the noise floor of the endpoint, measured rather than assumed. **The operator's
report is the primary endpoint, and on most drives it is the ONLY one.** The pre-registration already
says this; now it has a number behind it.

### ⭐ AND THE BINDING CONSTRAINT IS IDENTIFIED EXACTLY
```
   engaged episodes   9-22   never the limit
   manual  episodes   3- 7   THE LIMIT, on every single scoreable route
```
Thirteen routes have **no matched creep arms at all**, and the ten that do average **5 manual
episodes**. The one route that resolved, ra6, has **the most manual episodes (7)**.
⇒ **the missing ingredient has always been MANUAL CREEP, and it is the cheapest thing to fix.**
**8+ separate manual creep passes** is the single change that would most improve the drive's power —
more than any extra engaged driving. This is now the headline requirement on the drive card.

⊕ Note r24's 0.20 [0.04, 0.86] would read as a strong engaged *reduction* at 6–9 Hz on a naive CI, and
the null correctly rejects it. Seven of the ten scoreable routes have CIs spanning 1.0; **the endpoint
is dominated by between-episode variance, not by firmware.**

## ⛔✅ **NO STABLE ACOUSTIC MARKER ACROSS ROUTES — AND SPEED-MATCHING ALONE IS NOT ENOUGH**
Two results from running the creep acoustic contrast across four existing routes.

### ⛔ THE HF CLUSTERS DO NOT REPLICATE — THE ENDPOINT MUST STAY WITHIN-DRIVE
r24's fallback threw up a coherent **2389–2688 Hz cluster at +4–5.5 dB**, which looked like it might be
an acoustic signature of the ratchet. It is not:
```
   r24  (fallback)  2389-2688 Hz  +4.2 .. +5.5
   r23  (primary)    408- 416 Hz  +5.2 .. +7.3
   ra6  (primary)    908- 920 Hz  +9.7 .. +10.5
   r22  (primary)    193/385/387/443/488/1885/2705 Hz  +3.0 .. +4.8
```
**Every route has a different cluster.** ⇒ there is **no stored acoustic signature to compare a V158
drive against**; the acoustic endpoint must be **within-drive** (V158's engaged arm vs its own manual
arm), exactly like the band scorer. Recorded so nobody builds a cross-route acoustic reference.

### ⛔ AND ra6 EXPOSED A HOLE IN MY OWN GUARD
```
   ra6   speed gap 1.18 km/h   -> PASSED the speed check
         20-50 Hz +3.00 dB  AND  2000-5000 Hz +3.21 dB  -- the WHOLE spectrum lifted together
```
A speed match does **not** exclude a global level difference (mic gain, window position, engine load,
surface). My tool checked the speed gap and then reported the spectrum as a result. **That is the same
class of error the 30–40 Hz negative control exists to catch in the band scorer** — I had built the
acoustic tool without its analogue.

✅ **THE UNIFORMITY GUARD**, now added and validated on real data:
```
   ra6   band spread 1.55 dB, median level +3.21 dB  ->  🛑 FAILED (global level shift)
   r22   band spread 1.23 dB, median level +0.34 dB  ->  ✅ PASSED (band-specific)
```
The test is **large level AND small spread**, not spread alone — which is why r22's similar spread
passes on a near-zero level while ra6's fails on +3.21 dB.
⭐ **EVERY CONTRAST NEEDS A NEGATIVE CONTROL, INCLUDING THE ONES YOU JUST BUILT.** I added the null
gate to the band scorer after it over-claimed, then built an acoustic tool with no equivalent and it
over-claimed the same way on the first route that could expose it.

## ✅✅ **THE AUDIO CHANNEL IS VALIDATED — AND IT WAS POINTED AT THE WRONG BAND AND SPEED**
Audio is the channel that has tracked the operator's report where the bus has not, so it was the last
drive-side dependency to audit. It runs: **16,364 blocks aligned to the CAN timebase on r24**, with
`zstandard`/`cereal` present and 635 rlog segments on disk.

### ⛔ BUT `audio_engaged_vs_manual.py` ANSWERS A DIFFERENT QUESTION
Its own comment explains why it abandoned the engaged/manual split on r24 — *“hopelessly
speed-confounded (52.8 vs 11.5 km/h median) … produces a uniform +10 dB”* — and substituted a
within-engaged **21–26 Hz** high-vs-low contrast, speed-matched at **28–82 km/h**. Sound for r24. But
for V158 that is **the vibration band, not the 6–9 Hz ratchet**, at **a speed where V158 is
architecturally inert.** Run as-is on the V158 drive it would report on the wrong band at the wrong
speed.

### ✅ `rlog-tools/decode/audio_creep_v158.py`
- **PRIMARY: engaged vs manual, restricted to CREEP (1–24 km/h), speed-matched.** The r24 confound came
  from engaged *highway* against manual *creep*; the drive card's matched manual creep segment is
  precisely what makes this contrast valid instead of confounded.
- **It REFUSES if the arm medians differ by more than 2 km/h**, naming the r24 +10 dB artefact as the
  reason — rather than reporting a speed difference as an acoustic result.
- **FALLBACK: within engaged creep, high-vs-low 6–9 Hz** — the kit's validated design, retargeted from
  21–26 Hz to the ratchet band — clearly labelled as unable to separate *“the damper worked”* from
  *“less ratchet happened to occur”*.
- Reports 20–2000 Hz so no band is pre-committed; refuses loudly at every insufficient-data point.

### 🛑 IT IMMEDIATELY CAUGHT A REAL CONFOUND ON r24 — AND THAT IS A DRIVE REQUIREMENT
```
   596 creep audio windows: 271 engaged, 325 manual
   speed-matched 3.4-17.8 km/h: engaged p50 10.3 vs manual p50 7.9, gap 2.43 km/h
   ⛔ REFUSED (gap > 2.0) -> fell back, and said so
```
r24 **has** creep audio in both arms, and the primary contrast was **still** invalid because the two
arms sat 2.43 km/h apart. ✅ **So it is not enough to drive “some creep engaged and some creep
manual”** — the two arms must be **the same stretch at the same speed**. That is now in the drive card.
⊕ The guard is what makes a null trustworthy: without it this route would have produced a confident
acoustic number built on a speed difference.

