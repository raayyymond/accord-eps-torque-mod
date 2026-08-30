# DRIVE CARD — V228, and the choice between it and V222

## 🚗 AT THE CAR — everything operational, in one block

```
  FILE   39990-TVA,A160-V228-V222BASE-GAIN.STAYS.6X.AS.CAR-0x13000-0x100000.rwd
  rwd    sha256 b90a200ce53c7f37...        image sha256 6cf12db9fc49aee2...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop** — that is a complete result, and no measurement
overrides it.

**Stop and say so if:**
- the **ratchet is clearly worse** than your car → fall back **V221 → V217 → V122**
- a **new higher-pitched grind** appears on lane changes/turns → expected at 40–49 Hz, **say so anyway**
- anything faults, or the EPS lamp lights

➕ **If it feels good, keep driving.** The band numbers need **minutes**, not one episode — and a
**second V228 drive is worth more than any new build** (see below).

---

**V228 is V222 minus the 8× gain step. Four bytes apart. They ask you for different things.**

---

## The choice, in one table

| | **V222** | **V228** |
|---|---|---|
| grinding (15–22 Hz) | notch cuts it **3.6×** | **identical** — same notch, same bytes |
| the 8× vibration band (22–26 Hz) | net **0.463×** vs your car | not applicable — no gain raise |
| **ratchet (6–9 Hz)** | **could go either way, including worse** | **protected** |
| **LKAS authority** | **8×** | **6× — unchanged from what you drive now** |
| delta from your car | 23 bytes | **19 bytes** |

**Both carry Lever B at 13107** (2.50× the damping on your car) and the same 20.50 Hz notch. That is
the whole of what they share, and it is the part with evidence behind it.

---

## Why the ratchet is a risk on V222 and not on V228

You flew 8× once before — **V101, route `0x95`** — and reported:

> *"grinding/vibration now exists at all speeds… only occurs during LKAS command… I can get it to go
> away if I apply some torque… as soon as I let go, the grinding returns and grows into a steady
> state."*

V102 went back to 6× at your own choosing. V222 returns to 8×, on the argument that the notch added
since then covers it.

**In the band you actually felt, that argument holds.** 8× brings 1.65× more 22–26 Hz energy; the notch
cuts that band to 0.281× ⇒ **net 0.463×, better than your car**, and it stays a win across the full
uncertainty range.

🛑 **But the notch only spans 15.5–29.8 Hz. At the ratchet it does nothing (0.997).** So on V222:

```
  at 6-9 Hz:   forward gain raise   1.33x - 1.65x   (excitation, UP)
               Lever B raise        2.50x           (damping, UP)
```

Same order of magnitude, Lever B larger — **but that is a closed-loop question and no arithmetic I can
do settles it.** V228 declines that race by not taking the gain: every one of its 19 bytes is either a
damper raise or a filter that is flat at the ratchet.

---

## Which to fly

**Fly V228 if** the ratcheting/stuttering is what bothers you most, or if you want the grinding fix without putting the ratchet at risk. Authority stays exactly where it is today.

🛑 **One honest correction to an earlier version of this card, which said V228 "cannot make anything worse".** That is wrong. It cannot make the **ratchet** worse. But **both builds raise the 40–49 Hz band** — the notch retune moves Honda’s own 55 Hz notch away, which lifts what sits above it: **V228 by ~+5.9 dB, V222 by ~+8.1 dB**, against the **+9.7 dB(A)** "grind #2" that caused a lever to be removed back at V62. **That band is audible.** Your own words for it, from when it last showed up: *"a higher-speed grind #2 on lane changes/turns, only LKAS-engaged."* ⚠ **But if you hear it, that does NOT prove the notch caused it** — grind #2 has appeared on a build carrying none of the levers once blamed for it (V71c), so its origin is genuinely open. The **measured** 40–49 Hz level is what tests the mechanism; **hearing it** tells us it happened, not why.

**Fly V222 if** you want the LKAS authority as well and are willing to have the ratchet possibly get
worse in exchange, knowing you can fall back.

⚠ **If you are undecided, V228 is the one that cannot make the RATCHET worse** (it does still raise
40–49 Hz — see the correction above; no build avoids that). V222 remains available
afterwards, and flying V228 first also makes V222 interpretable: the two differ in exactly one lever,
so a V228 drive followed by a V222 drive is the cleanest 8×-gain experiment this kit has ever had.

**Fallback order from either:** V221 → V217 → V122 (your car).

---

## The trade you are actually making

**You cannot get the grinding fix without lifting 40–49 Hz.** That was checked properly rather than
assumed: keeping Honda’s 55 Hz notch and buying the 15–22 Hz cut from Lever B instead would need Lever B
**1517× past its calibration ceiling**, and the describing function says the extra gain would not
deliver anyway because this build already sits at the p99 knee. There is also only **one biquad** in the
whole firmware, so 20.50 Hz and 55 Hz are mutually exclusive.

⇒ **The real choice is: the grinding fix with an audible 40–49 Hz lift (~+5.9 dB on V228, ~+8.1 dB on
V222), or neither.** Staying on your car keeps 40–49 Hz where it is and keeps the grinding too.

## ⭐ GOOD NEWS ON EXPOSURE — the numbers below are for the CAN readout, and AUDIO is far better

The exposure figures in the next section (14 min/arm for grinding, ~7 h for the ratchet) are for the
**CAN** band readout, which is what this kit has always used. Measured on your car, **audio is 2.2× to
10.5× more efficient in every band**:

```
  grinding 15-22 Hz    AUDIO  1.3 min/arm     CAN  14.0 min/arm
  ratchet  6-9 Hz      AUDIO 98.3 min/arm     CAN 413.7 min/arm
```

⇒ **the grinding question needs about a minute and a half of engaged driving per build, not fourteen.**
Audio also samples at 16 kHz, so unlike the CAN logs nothing in it is alias-confounded.

⚠ Measured on one route only, and audio is a different physical quantity from steering rate — so treat
it as the primary readout and keep CAN as the cross-check, rather than trusting it alone.

## 🛑 WHAT ONE DRIVE CAN AND CANNOT FALSIFY — read this if the drive disappoints

**These symptoms are intermittent, and that cuts BOTH ways.** The kit already has a standing rule that
*"absence of a complaint is not a report of absence"*. What is newly established is that **presence
varies too**:

- **V67, V68 and V85 are byte-identical** on all five cells ever blamed for grind #2. It was reported
  on the first two and **not** on the third.
- Your own words on V112: ***"I no longer have an understanding of the kinds of scenarios that illicit
  grind #1."***

⇒ **So a single drive is weak evidence in BOTH directions.** "No better" does **not** falsify a build,
and "better" does **not** confirm one. That is written here **before** the drive so it cannot sound like
an excuse afterwards.

### Two different questions, and only one of them is yours to answer in a single drive

| question | who answers it | how many drives |
|---|---|---|
| **Is the car acceptable to drive?** | **You, and only you.** One episode is enough, and your verdict is final | **1** |
| **Did the lever work?** | the band measurements | **many** — 14 min/arm for grinding, ~7 h for the ratchet |

**Your job is the first question.** If it feels wrong, stop — that is a complete and sufficient result,
and no measurement overrides it. But if it feels *unchanged*, that is **not** a verdict on the lever;
it is one sample of an intermittent process, and the honest response is another drive rather than
abandoning the build.

⚠ This is also why the **repeat route** matters more than the next new build: it is the only thing that
separates "this build does nothing" from "this symptom did not happen to fire today."

## ⭐ IF YOU CAN ONLY DO ONE THING: DRIVE V228 TWICE

Not V228 then V222 — **V228 twice, on separate outings.**

Every cross-build number this kit has ever reported is **one route against one route**, and the
route-to-route variation underneath them has never been measured. From the only two repeat pairs in the
whole corpus, it could be small (σ = 0.09) or large (σ = 0.40); two pairs cannot tell. At the small
value most of the record stands. At the large value **only one result in the kit’s history survives** —
and V88’s 0.549×, the basis for Lever B and therefore for this very build, is not among them.

**A second V228 route fixes that for everything at once.** It is the one measurement that re-prices
V62, V88, the 8× dose law and the pre-registered experiment simultaneously. No new firmware can do it,
and it costs nothing but a second drive.

## ✅ THE PAIR IS PRE-REGISTERED

V228 and V222 differ in the forward gain and **nothing else**, so flying both gives the **first clean 8× experiment** this kit has had — the only prior 8× route, V101, **removed Lever B in the same build**, which is why the record’s 8× evidence is confounded.

What each outcome licenses is fixed **in advance** in `docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md`, including the honest scope: **~21 engaged minutes per build** settles the m^1.74 dose law at 22–26 Hz, but the pair **cannot settle the ratchet** and **cannot tell a linear gain law from no effect** — those need 38–116 min/arm.

## The drive

Same protocol as V222. **Your symptom verdict is the primary readout.**

🛑 **A short drive cannot prove a band number.** Measured from real cached drives, the smallest change
one 15–30 s episode could establish is **13–15×** for grinding, **11–13×** for 9–12 Hz and **42–45×**
for the ratchet — while the expected effects are **1.2–1.8×**. To resolve them needs roughly **14 min**
of engaged symptomatic driving per arm for grinding and about **7 hours** for the ratchet, which nobody
is going to do.

⇒ **If it feels different, that is the finding.** Say it in your own words. Do not wait for a number to
confirm you, and do not let a short-drive band ratio be read as contradicting you — it cannot.

---

## Limits that apply to both builds

1. **Do not score 30–49 Hz.** Both builds move Honda's 55 Hz notch to 20.50 Hz, and 52–71 Hz folds into
   that band at the ~101 Hz log rate. Any difference there is confounded and cannot be separated
   afterwards.
2. **A ratchet null licenses nothing about `0xC63AE`.** That lever's lane share and even its sign have
   never been measured; it would need a cave sign-bit to settle.
3. The reconstruction work behind all of this is **open-loop**. It says what the firmware computes, not
   what the car does with it.

---

## Verification behind V228

- **72/72** builder assertions · **1138** close-out checks · **100 %** orphan-byte coverage
- image sha256 `6cf12db9fc49aee2…` · rwd sha256 `b90a200ce53c7f37…`
- file: `39990-TVA,A160-V228-V222BASE-GAIN.STAYS.6X.AS.CAR-0x13000-0x100000.rwd`
- builder: `analysis-2020accord/builds/v108_plus/build_v228_tva.py`

🛑 **The flash decision is yours.** Name the file and the bus, and I will repeat both back before
anything happens. openpilot/pandad must be killed first (`tmux kill-server`).
