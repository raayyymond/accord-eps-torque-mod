# DRIVE CARD — V229 vs V228: the 55 Hz question, open since V172

## 🚗 AT THE CAR

```
  V229   39990-TVA,A160-V229-V228BASE-HONDA.55HZ.NOTCH.RESTORED-0x13000-0x100000.rwd
         rwd sha256 443fa080307cf221...      image sha256 078da4b1f22903a5...

  V228   39990-TVA,A160-V228-V222BASE-GAIN.STAYS.6X.AS.CAR-0x13000-0x100000.rwd
         rwd sha256 b90a200ce53c7f37...      image sha256 6cf12db9fc49aee2...

  BEFORE anything: kill openpilot/pandad  ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

---

## ⭐ DRIVE **V232** — the ordering changed, and here is the number that changed it

```
  V232   39990-TVA,A160-V232-V231BASE-NOTCH.REAIMED.34HZ.PUMPING.BAND-0x13000-0x100000.rwd
         rwd sha256 81127bd876289fdc...     image sha256 c15fa8633352771f...
```

Every notch comparison in this kit — mine included — has been made on **magnitude alone**. But a lane's
damping contribution is `|H| × cos(phase)`. Computing the product against the flown lane phases:

```
  build         6-9      9-12    12-15    22-30    30-40    damping   pumping
  your car    1.000x   1.000x   1.000x   1.000x   1.000x     1.000x    1.000x
  V228        0.861x   0.799x  -0.055x  -0.088x  -0.498x     0.535x   -0.293x
  V232        0.985x   0.990x   0.858x   0.694x  -0.123x     0.944x    0.285x
```

**V232 keeps 94 % of the damping while removing 71 % of the pumping**, and barely touches the ratchet
band itself. **V228 destroys 46 % of the damping and flips 12–15 Hz from damping into pumping** — which
its magnitude tables never showed, because they left the phase term out.

**V231 remains the control arm.** It carries the same probe, so driving V232 first costs you nothing in
diagnosis. Its cost is unchanged and real: 55 Hz runs 97× louder than Honda, in a band where the audio
does show LKAS excess — but Honda's cut there is on your car today and has not stopped the grinding.

---

## The two builds worth driving, and why the choice is genuinely open

**V231** — Honda's notch placement, plus the first instrument ever put on that filter.
**V232** — the notch re-aimed to 34 Hz, at the band the lane measurably pumps in.

They are opposite sides of a trade one filter cell cannot avoid:

```
                  cuts 44-65 Hz      cuts 22-40 Hz      the case for it
  V231 (Honda)       9.35x              1.51x          44-65 overlaps the 50-72 Hz audio band
                                                       where LKAS excess IS licensed (2.1-2.2x)
  V232 (re-aimed)    1.0x               4.80x          22-40 is where the lane measurably PUMPS,
                                                       unanimous across 3 routes
```

I tested whether the audible band is simply the **second harmonic** of the pumping — 22–40 doubled is
44–80 — which would have meant V232 fixes both and this choice disappears. **It does not:** the
ratio's clustering at 2.0 is fully reproduced by shuffled pairings (real 0.343 vs shuffled 0.351,
lift 0.98×). Refuted.

⚠ **The honest asymmetry, and why V231 still leads.** V232 cuts **22–40 Hz — a band you have never
named**. Your symptoms are the felt ratchet near 7.79 Hz (where the lane *damps*, so nothing should be
cut) and audible grinding, which the audio puts at 50–72 Hz. V232's case is a mechanism with no
reported symptom in its band; V231's is a symptom correlate with no measured mechanism. **Each has one
leg.** Your experience outranks the analysis, so the band you actually report wins the first drive.

---

## 🛑 THE NOTCH QUESTION IS NOW ANSWERED FROM FLOWN DATA — HONDA'S PLACEMENT IS RIGHT

I measured the notch's own lane (`gp-0x6b86`) against wheel rate on the three routes that carry it —
ra4, ra5, ra6 — and the answer is unanimous where it matters:

```
  band     verdict     route agreement
  6-9      DAMPING     all 3 agree
  9-12     DAMPING     all 3 agree      <- and V228 adds 25 deg of lag HERE
  12-15    DAMPING     all 3 agree      <- V228's notch skirt reaches into this
  15-22    (crossover, routes disagree)
  22-30    PUMPING     all 3 agree      <- Honda's 55 Hz notch cuts in this region
  30-40    PUMPING     all 3 agree
```

**The lane damps below 15 Hz and pumps above 22 Hz.** A notch is only worth placing where the lane
pumps — cutting where it damps removes damping, which is precisely the mistake that made you abort the
V94 drive.

So **V228's 20.5 Hz notch is wrong on three counts**: it vacates Honda's cut of the pumping region, its
skirt cuts damping at 12–15 Hz, and its 25° of lag at 9–12 Hz rotates a near-perfect damping phase
(cos −0.989) toward zero, costing 20–40 % of the damping there.

⇒ **Honda's placement — which V229 and V231 restore — is correct.** And the 56-build history of notch
builds that changed nothing now has a mechanism: the notch kept being moved out of the region where the
lane pumps into the region where it damps.

⚠ Three routes, all from the V104–V106 era, and the 15–22 Hz crossover is not licensed. The pump/damp
sign per band is what is claimed; the magnitudes are not.

---

## ⭐ DRIVE **V231** — it is V229 plus the first instrument ever put on the notch

```
  V231   39990-TVA,A160-V231-V229BASE-PROBE.BIQUAD.STATE-0x13000-0x100000.rwd
         rwd sha256 a089ba1432a5aa39...     image sha256 34a4400d3d848069...
```

**V231 drives identically to V229.** All three changed bytes are in the telemetry tap; not one control
byte moves. So you get V229's lever *and* the measurement, at zero cost to how the car behaves.

**Why it matters.** After 56 builds that moved the notch around, **none has ever measured whether the
notch runs at all.** If you drive V229 and report "no change", I cannot tell you whether the notch is
inert or simply not where your symptom lives. V231 answers that from the same drive.

The filter's internal state boots to exactly `0.0f`. If its enable never fires on the car, that state
stays zero forever. V231 puts that state on CAN 427, so the reading licenses one clean sentence either
way:

- **identically zero across the drive** → the filter never executes, and **the entire notch axis is
  dead** — which would explain 56 builds of nothing, and retire the axis for good
- **nonzero** → it runs, and how hard it works is measurable for the first time

I tried to settle this from the existing corpus first and could not: the biquad was dormant before V103
and armed after, and five routes have audio across that boundary, but the **control bands moved more
than the test band** and one arm spanned 6× within itself. Cabin audio at 55 Hz is road and engine — one
assist lane cut 159× barely shows up in it.

---

## 🛑 CORRECTION — DRIVE **V229**, NOT V230

I recommended V230 first. **That was wrong, and here is why.** V230's lever (`0xC40DC`) acts on the
`gp-0x6b26` lane, and after building it I checked what the record already says about that lane:

- It has **exactly one output**, so a null there is a null on the lever, full stop.
- **A ×1.5 dose on it measured INERT** — p50 0.988, every CI containing 1.00, against a pre-registered
  1.50. The lane is in the closed-loop **invariance partition**: `y = K·α`, so scaling K leaves the
  product alone.
- **V94 cut that same cell 6× and you aborted the drive.** So the cell does reach the car — it is inert
  at small dose and bad at large dose, **in the cut direction**.

Measured against **your car**, V230 is −25 % at 7.79 Hz and −49 % at 18.5 Hz in that lane: comparable
to the dose that measured inert, and the **same sign** as the one that ended a drive.

🛑🛑 **V230 IS NOW WITHDRAWN — DO NOT FLASH IT.** The Re(Z) sign frame resolved from your own confirmed steering convention: `Re(Z) < 0` means the column is doing work on your hands, i.e. anti-damping. The lane census measured `gp-0x6b26` at **+518/+565 counts of POSITIVE Re(Z)** — so it is a **damper**, and V230 cuts 30 % of it at 7.79 Hz and 60 % at 18.5 Hz. **V230 removes damping.** That is also why V94’s 6× cut of the same lane ended a drive. Its files are renamed `SUPERSEDED-DO-NOT-FLASH-`.

⛔ **And `0xC40DC` is closed in the other direction too** — raising it is the helpful way, but Honda’s 22 already sits at **99.3 % of the theoretical ceiling at 7.79 Hz**, so the most it could ever buy is **1.007×**. There is nothing there.

🛑 **CORRECTED.** I first wrote that this makes V230 "probably a no-op". That was a misreading:
the record says the ×1.5 dose was **unmeasurable, not dead** — *"do not file it FALSIFIED"* — because
`y = K·α` is invariant to K while **α, the actual motion, is not**. The dose was measured at the one
quantity guaranteed not to move.

⇒ **V230's lever DOES reach the car** — V94's 6× cut aborting a drive is what proves it. It is simply
unmeasurable at its own output. Its direction matches that 6× cut and its size is smaller. **So the
caution stands and is now better founded, not weaker:** V230 stays on the shelf. **Drive V231.**

⚠ **One thing this turned up that applies to all three builds:** V228 and V229 both carry `0xC40DC` = 22
against your car's 8 — that lane runs **+6 % at 7.79 Hz, +28 % at 18.5 Hz, +114 % at 55 Hz** compared to
what you drive now. By the same invariance it is probably inert too, but it is a real non-stock delta
and you should know it is there.

---

## (superseded) DRIVE V230 FIRST — it is the only build that cuts BOTH bands

```
  V230   39990-TVA,A160-V230-V229BASE-ALPHA2.3-BOTH.CUTS-0x13000-0x100000.rwd
         rwd sha256 4aac1c8a54c3c9da...      image sha256 bb11115a54ba97b4...
```

V228 and V229 sit on opposite sides of a trade that **one filter cell cannot escape**. V230 escapes it
by using a *second, different* lever in a *different lane*:

```
                      18.5 Hz              55 Hz
  your car        no cut               159x cut (Honda's notch)
  V228            4.9x cut             100x LOUDER than your car
  V229            no cut               159x cut
  V230            2.53x cut *          159x cut  +  5.62x more *
                                       (* in the gp-0x6b26 lane)
```

It is **one byte** on V229: `0xC40DC` 22 → 3. That cal is the low-pass corner of a separate filter
chain, and because its DC gain is 1 at *any* setting, lowering it moves the corner **without touching
low frequency** — `0.992 at 1 Hz, 0.932 at 3 Hz`. So it buys high-frequency cut **without adding felt
mass or friction where you actually steer**, which is your standing requirement.

⚠ **Honest limits.** The 2.53× is a cut *in one lane*, not in delivered torque — the notch cuts a
different signal in a different function, and those ratios **do not multiply**. V230's 18.5 Hz cut is
smaller than V228's. And V230 changes two things versus V228, so **V229 is the clean control** if you
want to know *why* something changed rather than just whether it did.

---

## The one thing to understand

**There is exactly ONE filter cell in this ECU. Honda uses it as a 55 Hz notch.**

Every build since V172 — about 56 of them — has **moved** that cell down to ~20 Hz, to put a cut where
the 15–22 Hz grinding is. Moving it **vacates Honda's 55 Hz cut**. Nobody priced that, because CAN's
Nyquist is 50.5 Hz: 55 Hz folds down and masquerades as 30–49 Hz content, so **no CAN-based instrument
in this kit could ever have seen the bill.**

```
                |H| 18.5 Hz   |H| 55 Hz
  your car         0.8978       0.0063     <- Honda's 159x cut at 55 Hz
  V228             0.2045       0.6285     <- 4.4x quieter at 18 Hz, 100x LOUDER at 55 Hz
  V229             0.8978       0.0063     <- Honda's notch back; V228's 18 Hz cut given up
```

**One 2nd-order section cannot notch 18 Hz and 55 Hz. The trade is structural — no retuning escapes it.**

## Why this is worth a drive

On the alias-free audio, engaged vs not-engaged, **matched on both speed and gear**, bootstrapped over
routes:

```
  band (Hz)    direct acoustic       AM of broadband carrier
  15-22       1.45x [1.03, 3.70]      1.21x [1.05, 1.39]     <- where V228 cuts
  50-60       2.13x [1.13, 3.82]      1.58x [1.10, 2.70]     <- where Honda/V229 cuts
  60-72       2.22x [1.27, 5.04]      1.34x [1.06, 2.05]
```

**Both bands carry real, licensed LKAS-caused noise.** So the question is which cut is worth more —
and the cut depths differ by **32×**: V228 buys 4.9× at 18.5 Hz while giving up 159× at 55 Hz.

⚠ **What is NOT claimed:** that 50–72 Hz is *worse* than 15–22 Hz. Tested properly — paired within
route, because the band CIs overlap — it is **not licensed** on either channel (1.73× [0.48, 2.55]
direct; 1.23× [0.87, 1.86] AM). The notch program is not aimed at the wrong band. It is aimed at one
licensed band out of several, and it pays for that aim with a much deeper cut elsewhere.

## Which to drive

**Drive V229 first.** It is closer to your car than any build in the last 56: the only difference from
V228 is 12 bytes of filter coefficient, and it puts the 9–12 Hz phase back on the one geometry that has
actually been driven. V228 carries −39.3° at 10.5 Hz where nothing has ever flown past −21.3°.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop** — that is a complete result.

**Stop and say so if:**
- the **ratchet is clearly worse** than your car → fall back **V221 → V217 → V122**
- anything faults, or the EPS lamp lights

## What each outcome means

| you report | what it settles |
|---|---|
| **V229 better than V228** | the 55 Hz cut matters more than the 18 Hz cut — **56 builds of notch relocation were the wrong trade**, and the direction is to keep Honda's notch and attack 15–22 Hz some other way |
| **V228 better than V229** | your grinding really is at 15–22 Hz; the relocation is justified, and the 54–74 Hz cost is one worth paying |
| **no difference** | the biquad is not where your symptom lives at all, and the whole notch axis can be retired — which would be worth knowing after 56 builds |

**Every one of those is a result.** This is the first single-variable test of an assumption the kit has
been making since V172 without ever checking it.

## Cost, plainly

V229 gives up V228's 4.9× cut at 18.5 Hz. **If your grinding is genuinely at 15–22 Hz, V229 will be
worse there than V228.** That is the honest mirror of V228's own cost, and it is exactly why the pair
is worth driving rather than either alone.

## What V229 keeps

Everything else in V228, byte for byte: Lever B `0xC6446` = 13107 (the kit's only measured on-car win,
from V88), `0xC40DC` = 22, `0xC63AE` = 512, the `0xC407E` = 511 fault interlock, the friction lane at
the car's values, the 427 telemetry tap, and the 164-byte cave **byte-identical** — so this is not the
bricking class.

It also **satisfies a standing constraint V228 violates.** `BUILD-LINEAGE.md` on `0xC40DC`: *"it must
ship WITH the notch revert or not at all."* V228 ships `0xC40DC` = 22 — which passes **more** HF
(corner 21.3 → 67.0 Hz) — alongside a notch that no longer cuts 54–74 Hz. Both cells push the same way.
V229 is that notch revert.
