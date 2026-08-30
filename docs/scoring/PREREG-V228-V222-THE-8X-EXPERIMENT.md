# PRE-REGISTRATION — V228 → V222, the first clean 8× experiment

**Written before either build has flown.** Its purpose is to fix, in advance, what each outcome
licenses — so the result cannot be argued into whatever was hoped for afterwards.

---

## Why this pair is worth pre-registering

The kit's 8×-gain evidence is **confounded**. The only 8× route ever flown is `r95` = **V101**, and
V101 **removed Lever B in the same build** (`0xC6446` = 512, arm `0x3AA96` = `c5`, both byte-checked).
More forward gain with *less* loop damping needs more command to hold a line, so nothing in that drive
separates the two.

**V228 and V222 differ in `0xC6CD0` and its clamps, and in nothing else.** Same 20.50 Hz notch, same
Lever B 13107, same `0xC63AE` 512, same friction lane, same probe — verified by a 4-byte image diff.
So in the comparison **the notch and the damper cancel**, and what is left is the gain alone.

That has never been available before.

---

## The prediction, stated in advance

`m = 7128/5346 = 1.3333`. Two competing predictions for **V222 ÷ V228** in every band:

| model | predicted ratio | where it comes from |
|---|---|---|
| **linear** | **1.333×** | a forward gain acting as a plain scale |
| **m^1.74** | **1.650×** | the exponent measured at 22–26 Hz on V101 vs V100 |

🛑 **Both predict V222 is WORSE than V228 in every band**, because the notch is identical on both and
cannot give anything back. The experiment therefore tests **how much worse**, not **whether**.

⇒ **If V222 comes back at or below 1.00× in the 22–26 Hz band, both models are wrong** and the
m^1.74 dose law — which is currently load-bearing for every gain decision in the kit — needs
retracting.

---

## Exposure required, and what is honestly reachable

Measured from real cached drives (episode-to-episode sd of the band/control ratio, 20 s episodes):

| band | sd | n/arm for 1.650× | min/arm | n/arm for 1.333× | min/arm |
|---|---|---|---|---|---|
| **22–26 Hz (decisive)** | 0.430 | **62** | **21** | 183 | 61 |
| grind 15–22 | 0.426 | 61 | 20 | 181 | 60 |
| mid 9–12 | 0.392 | 51 | 17 | 153 | 51 |
| ratchet 6–9 | 0.587 | 115 | 38 | 347 | 116 |

**The 22–26 Hz arm is decisive**: it is where the 8× effect was originally measured, it has the
smallest spread, and both builds notch it identically.

✅ **Reachable: ~21 engaged symptomatic minutes per build** settles the m^1.74 prediction at 22–26 Hz.
🛑 **NOT reachable: the linear prediction (61 min/arm) and the ratchet arm (38–116 min/arm).**

⇒ **Pre-registered scope: this pair can confirm or refute the m^1.74 dose law in the 22–26 Hz band, at
about 21 minutes of engaged driving per build. It cannot settle the ratchet, and it cannot distinguish
a linear gain law from no effect.** Anyone who reports otherwise from a short drive is over-reading it.

---

## What each outcome licenses

| outcome at 22–26 Hz | licenses |
|---|---|
| **V222/V228 ≈ 1.65×**, CI excluding 1.0 | the m^1.74 dose law **stands**; 8× costs what the record says; the notch's cover is the only reason V222 is tolerable |
| **≈ 1.33×**, CI excluding 1.0 | the gain acts **linearly**, not m^1.74 ⇒ **the record's exponent is too steep** and past gain decisions were priced pessimistically |
| **≈ 1.0×**, tight CI | **both models refuted.** The gain does not scale this band at all, and the V101 attribution was confounded by something other than Lever B |
| **wide CI spanning 1.0** | **nothing.** Under-exposed. Do not report a direction |

🛑 **The operator's symptom verdict is a separate instrument and outranks all of the above.** If he
reports the car is worse on V222, that stands on its own regardless of what the band says — the
standing rule is score bands, let the operator score symptoms.

---

## Order, and why

**Fly V228 first.**

1. It **cannot make the RATCHET worse** — every one of its 19 delta bytes is a damper raise or is flat
   at 6–9 Hz. ⚠ **Corrected 2026-08-30:** an earlier version of this line said "cannot make ANYTHING
   worse", which is false — the notch is **not** flat at 40–49 Hz and V228 raises that band by
   ~+5.9 dB (V222 by ~+8.1 dB). The ordering argument survives, because the ratchet is what the
   first drive risks; the absolute claim does not.
2. It establishes the **grinding baseline with the ratchet protected**, so if grinding improves, that
   result is clean.
3. Only then does V222 add one variable. Flying V222 first and V228 second also works, but risks the
   ratchet on the *first* drive, which is the one most likely to be cut short.

---

## 🛑 Registered BEFORE the drive: acceptability is not efficacy

These are two different questions and only one of them a single drive can answer. Confusing them is
how sixty builds in this record got "falsified" by one quiet drive.

| question | who answers it | drives needed |
|---|---|---|
| **Is the car acceptable to drive?** | **the operator, and only him.** One episode suffices and his verdict is **FINAL** | **1** |
| **Did the lever work?** | the band measurements above | **many** — ~21 min/build here |

⇒ **"It felt no different" does NOT falsify either build.** Symptom presence varies on *byte-identical*
firmware: V67/V68/V85 are identical on all five cells ever blamed for grind #2, and it was reported on
two of them and not the third. The operator on V112: *"I no longer have an understanding of the kinds
of scenarios that illicit grind #1."* A single drive is weak evidence in **both** directions.

⇒ If he reports the car is **worse**, that stands on its own and no band number overrides it. If he
reports it **unchanged**, that is one sample of an intermittent process — the registered response is
**another drive**, not abandoning the build. See RULE 5b in `docs/BUILD-LINEAGE.md`.

---

## Registered limits

1. **Do not score 30–49 Hz.** Both builds move Honda's 55 Hz notch; 52–71 Hz folds into that band at
   the ~101 Hz log rate and cannot be separated afterwards.
2. **A ratchet result of any kind licenses nothing about `0xC63AE`** — that lane's share and sign are
   unmeasured, and it is identical on both builds anyway.
3. All predictions here are **open-loop**. They say what the firmware computes, not what the closed
   loop does.
4. The **m^1.74 exponent was measured at 22–26 Hz**. Applying it to 6–9 Hz is extrapolation, which is
   why the ratchet row above is bracketed by both models rather than asserted.

---

## The scorer exists, and it was validated before the data

`rlog-tools/score/score_8x_experiment.py` implements this document and nothing else — no extra bands,
no alternative statistics, no post-hoc filters. It was written and validated **before either build
flew**, which is what makes this pre-registration binding: a scorer written afterwards, against real
results, is one whose choices were shaped by the answer they produced.

Validated by injecting known ratios into synthetic data:

```
  injected 1.000  ->  recovered 1.019  [0.962, 1.073]   OK
  injected 1.333  ->  recovered 1.324  [1.294, 1.454]   OK
  injected 1.650  ->  recovered 1.602  [1.520, 1.712]   OK
  injected 2.500  ->  recovered 2.433  [2.345, 2.545]   OK
  NULL, two identical builds -> 0.983  [0.924, 1.029]   CI spans 1.0
```

✅ It recovers injected ratios and **does not manufacture an effect from noise** — on the null it
prints *"NOTHING — CI spans 1.0, under-exposed. Do NOT report a direction."* rather than a number.

🛑 Two guards are in the code, not just in this document: it **bootstraps over EPISODES, never
windows** (window bootstraps manufacture significance, a standing instruction here), and it **refuses
to score any band with fewer than 8 episodes per arm** rather than returning a wide, tempting number.

Run: `python rlog-tools/score/score_8x_experiment.py --selftest` to re-verify, then
`python rlog-tools/score/score_8x_experiment.py <v228_route> <v222_route>` after the drives.

---

## The extract-to-cache path, verified before the drive

The scorer reads a route cache that does not exist until a drive is extracted, so the pipeline was
checked end to end rather than assumed.

Every drive so far got a hand-written extractor — **49 of them**, 4 KB to 37 KB, each repeating one
wrapper with two numbers changed. Those two numbers are the CAN-427 tap’s **source** and **shift**, and
they are the single worst thing to hand-type, because the record’s own rule is: *"CAN 427 carries a
DIFFERENT VARIABLE PER BUILD — source + shift move on nearly every build (V94 `gp-0x6b26` sar1 vs
V96–99 `gp-0x6b70` sar6 = **32× apart**). Never pool a 427 percentile across routes; decode from the
image first."*

`rlog-tools/decode/extract_route_generic.py` therefore **refuses to take them as arguments** and derives
them from the build’s own image (`0x55DF2` source hw2, `0x55E10` shift, `wire scale = 2**shift / 5`).
Cross-validated against two independent sources:

```
  V122 (the car)   gp-0x6ABC  sar 3  scale 1.6   matches extract_r24.py's hardcoded 8.0/5.0
  V222 / V228      gp-0x6B4E  sar 5  scale 6.4   matches the builder's NEW_PROBE_HW2 = 0x94B2
```

🛑 **And that surfaces a live trap for this experiment: V222/V228 read a DIFFERENT VARIABLE from the
car’s route, at 4× a different scale.** Any 427 comparison against route `r24` would be wrong twice
over.
✅ **The 8× scorer is unaffected** — it uses `cs_rate`, which is build-independent — and V228 and V222
**share a tap**, so their 427 channels are directly comparable to each other.

Run `python rlog-tools/decode/extract_route_generic.py --check V228` before the drive to confirm the
tap, rather than discovering it wrong afterwards.

---

## 🛑 A SECOND PRE-REGISTERED TEST: the 40–49 Hz AUDIO lift

Both builds relocate Honda’s 55 Hz notch to 20.50 Hz, which **lifts 40–49 Hz** — the "grind #2" band.
That is a side effect of the grinding fix and it is **unavoidable** (Lever B cannot substitute; it would
need to be 1517× past its cal ceiling, and only one biquad exists). So it should be **tested**, not
merely warned about.

✅ **The baseline did not exist until 2026-08-30 and was created for this.** The audio corpus stopped
at `ra6`/V106 — there was **no audio cache for the car at all**, which made the prediction untestable.
`r24` is now extracted (14 segments, 3148 spectral frames), and it shows something worth knowing:

```
  r24 (V122 = THE CAR), audio power relative to its own 30-40 Hz neighbour:
     ratchet    6-9 Hz    -4.9 dB
     grind #1  15-22 Hz   -1.3 dB
     8x band   22-26 Hz   -0.5 dB
     GRIND #2  40-49 Hz   +4.2 dB   <- ALREADY the most elevated band on the car
     above notch 55-65    -0.5 dB
```

**40–49 Hz is already the loudest relative feature on the car before any change.**

### The prediction, fixed in advance

| build | predicted lift | predicted level (rel 30–40 Hz) |
|---|---|---|
| **V228** (notch only) | **+5.9 dB** | **≈ +10.1 dB** |
| **V222** (notch + 8×) | **+8.1 dB** | **≈ +12.3 dB** |

| outcome | licenses |
|---|---|
| lift within ±3 dB of prediction | the notch-relocation mechanism is **confirmed**; the trade is real and priced |
| **no lift** (within ±2 dB of the car) | the notch arithmetic is **wrong somewhere** — stop and find it before any further build reasons from it |
| lift **much larger** than predicted | something amplifies beyond the open-loop transfer; treat as a closed-loop effect and re-open |

### 🛑 What this test CANNOT do — attribute a SYMPTOM

The band measurement above is a **mechanism test** and is valid as such. But if the operator reports **grind #2 itself**, that **cannot be attributed to the notch relocation**, because **grind #2’s origin is OPEN**. The record is explicit: *"grind #2 is V62’s `sar`" is REFUTED* — **V71c produced grind #2 carrying NEITHER `sar` byte.** The surviving claim is only that the r24 half is *"directionally supported"* as a contributor.

⇒ So the two readouts must be kept apart:

| readout | what it can show |
|---|---|
| **40–49 Hz audio level** vs the r24 baseline | whether the **notch-relocation mechanism** does what the arithmetic says |
| **the operator hearing grind #2** | that grind #2 occurred — **not** what caused it |

➕ **His own description, for what to listen for:** *"a higher-speed grind #2 on lane changes/turns, only LKAS-engaged."* There is also a recorded **absence** report on another build — *"I did not experience any grind #2 from my hard turning or on the highway"* — which the record correctly flags as **weak negative evidence, not a cure.**

🛑 **This band is NOT alias-confounded.** Audio samples at **16 kHz** (Nyquist 8 kHz), so unlike
30–49 Hz on the ~101 Hz CAN logs, 40–49 Hz here is directly measurable. It is also **audible** — if a
new higher-pitched grind appears, this is the first place to look.

Extract with `python rlog-tools/decode/extract_audio_grind.py <route>` (the route must be added to its
`ROUTES` dict, as `r24` now is).

---

## Provenance

- V228 image `6cf12db9fc49aee2…`, rwd `b90a200ce53c7f37…`, 72/72 builder assertions
- V222 image `0e83c7074699d6ab…`, rwd `0766d45cbad4bde1…`
- 4-byte diff verified: `0xC6CD0` 7128↔5346, `0xC61B3`/`B5` 16↔12
- 1138 close-out checks · 100 % orphan-byte coverage on both
- exposure figures: episode-spread measurement over 6 routes / 75 engaged minutes
