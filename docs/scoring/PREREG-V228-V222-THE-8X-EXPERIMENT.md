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

1. It **cannot make anything worse** than the car — every one of its 19 delta bytes is a damper raise
   or a filter flat at the ratchet.
2. It establishes the **grinding baseline with the ratchet protected**, so if grinding improves, that
   result is clean.
3. Only then does V222 add one variable. Flying V222 first and V228 second also works, but risks the
   ratchet on the *first* drive, which is the one most likely to be cut short.

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

## Provenance

- V228 image `6cf12db9fc49aee2…`, rwd `b90a200ce53c7f37…`, 72/72 builder assertions
- V222 image `0e83c7074699d6ab…`, rwd `0766d45cbad4bde1…`
- 4-byte diff verified: `0xC6CD0` 7128↔5346, `0xC61B3`/`B5` 16↔12
- 1138 close-out checks · 100 % orphan-byte coverage on both
- exposure figures: episode-spread measurement over 6 routes / 75 engaged minutes
