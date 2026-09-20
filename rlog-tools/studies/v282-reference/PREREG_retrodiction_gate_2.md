# PRE-REGISTRATION #2 — the jerk-lead repair, and the LAST attempt at a controller-ordering statistic

**Written and committed 2026-09-20, BEFORE the repaired statistic was computed.** Gate #1 is at
`PREREG_retrodiction_gate.md` (committed 74a7e9d); it FAILED and its class-closing null is committed at 879448f.

🛑 **THIS IS THE LAST ATTEMPT. If gate #2 fails, the Tier B class is closed PERMANENTLY for this kit and no
third repair may be proposed.** Recorded here so that promise is binding before the result is known.

## Why a second attempt is legitimate and not a re-litigation

Gate #1's null says the class is closed *"until the instability mechanism itself is modelled — not until a better
estimator is found."* **Modelling the mechanism is the unlock the null itself names.** This attempt is that, and
it is admissible only because the missing term was found in the data rather than invented to rescue the result:

Gate #1's repair failed because it **got r73's frequency wrong** — it places r73's object at **1.7–1.9 Hz** while
r73's own wire shows it at **4.0–6.5 Hz** (×3.7–5.9 the wheel-rate band power of its matched control r72; the
"4 Hz chatter" this kit's memory recorded on 2026-09-14, six days before any of this). A model that cannot place
the object of the very term it adds is not yet a model of the mechanism.

The candidate is visible in gate #1's own wire regression, not newly invented: the relay acts on
**`clip((err + 0.22·jerk)/0.30)`**, not on plain error. Gate #1 modelled it on plain error. **A jerk term is
phase lead, and lead moves a −180° crossing UP in frequency** — the direction required.

## The repair to be made — ONE term, and only one

Add the **jerk (derivative) content of the relay's own argument** to the describing-function term: the relay input
is `err + Kj·jerk` with `Kj ≈ 0.22` read from the fork source and confirmed by gate #1's wire regression
(coefficient of `clip(arg/0.30)` = 2.530 on r73 vs 0.311 on r72, same commit). Carry the two terms already in
gate #1 (the relay itself, the `AccordRateLoopGain` inner loop) unchanged.

🛑 **ANTI-FUDGE: exactly ONE new term. If more than the jerk lead is needed to pass, that is a FAIL** — it means
the model is being tuned to the answer. In particular, **the error notch may not be added to rescue the ranking**;
it is the leading rival explanation for why post-r71 routes flew clean, and gate #1's judge specifically named
adding it as the temptation to refuse. Model the flown notch *correctly* where it flew (it did fly on r72/r73 at
Q = 1.0 — a record error fixed at 879448f), but do not introduce it as the separating mechanism.

## 🛑 THE ANCHOR SET, corrected and fixed NOW, before the result

Corrected from the wire and from the per-commit guard rule, both established at 879448f **before this gate was
written**, and not adjustable afterwards:

| route | relay live? | outcome label | basis |
|---|---|---|---|
| **r71** | YES, `SteerFriction` 0.011 | **POSITIVE — limit cycle at 2.34 Hz** | observed, recorded |
| **r73** | YES, back-filled 0.2120 (commit `e8e62f0e1` predates the guard) | **POSITIVE — chatter at 4.0–6.5 Hz** | its own wire, ×3.7–5.9 vs matched control r72; kit memory 2026-09-14 |
| r72 | no (`SteerFriction` 0.0) | CLEAN | matched control for r73, same commit |
| T64 / rev 6.4 (2 routes) | no (guard live, `AccordFrictionHyst` 0.015) | CLEAN | flying now |
| V282 (3 routes) | YES, 0.010–0.030 (pre-guard commits) | CLEAN | months of driving |

⚠ Note what this costs the hypothesis rather than helps it: **the three V282 routes are relay-live and flew
clean.** A statistic that simply ranks "relay live" as risky will fail clause (b) on them. That is deliberate.

## 🛑 THE GATE — four clauses, ALL must pass. Harder than gate #1 by design.

**(a) FREQUENCY, BOTH POSITIVES.** The model must place r71's object within **±25 %** of 2.34 Hz **and** r73's
within **±25 %** of the 4.0–6.5 Hz band, from each route's own flown parameters. *Gate #1 passed this for r71 and
failed it for r73; that failure is the whole reason for this attempt, so it is now scored explicitly.*

**(b) ORDERING.** **Both positives must rank above ALL five clean routes**, on at least 2 of 3 plants not taken
from either positive's own log. Stronger than gate #1's "r71 top on ≥2 of 3", and it is the clause the
relay-live V282 routes make genuinely hard.

**(c) NO FALSE ALARM.** rev 6.4's flown controller — driving now — must not rank above either positive on any plant.

**(d) POWER.** The adversary must compute the probability that a statistic with **no** discriminating content
passes (a)+(b)+(c) by chance on this anchor set. **If that probability exceeds 0.10, the gate is too weak and the
verdict is FAIL regardless of what the statistic scored.** Gate #1 was retrospectively estimated to be clearable
by a useless statistic ~1 in 4; that must not recur.

## What each outcome licenses — binding, written before the result

**PASS (all four):** the statistic becomes this kit's safety currency, replacing the struck `VM` and shake-band
`|L|`. Re-derive the closure ladder on it — ARM-KP3, the patched KP 5/6 points, Tier B 8/12/16 — and report
whatever it says, including if Tier B dies anyway on its own numbers.

**FAIL (any clause, or clause (d)):**
> *Two independent pre-registered attempts to build a controller-ordering safety statistic have failed. The
> Tier B class is CLOSED PERMANENTLY for this kit. No third repair may be proposed. Closure beyond ARM-KP3's
> measured 15.9 % requires either an instrument this kit does not have, or an EPS-side change that restores the
> inner rate servo — a firmware question, out of scope by the operator's own standing constraint.*

**EITHER WAY**, ARM-KP3 is untouched: it is defended on hand-verified notch algebra and on the three-crossing
derivation (`orch_armkp3_crossing.py`), not on any ordering statistic. It remains a mechanism check scored on
G0–G2, never on J.

## Guards

- Anchors are FIXED above. No relabelling after the result, in either direction.
- `Kj` comes from the fork source, not fitted. If it must be fitted to pass, that is a FAIL.
- A statistic passing only on a positive's own plant fails (b) by construction.
- Clause (d) can fail the gate even on a nominal pass. That is intentional.
