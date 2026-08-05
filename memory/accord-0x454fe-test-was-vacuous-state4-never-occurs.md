# 🛑🛑 `0x454FE`'s test was VACUOUS — `gp-0x67fa == 4` NEVER occurs while driving

**Measured 2026-08-05 by V71's own bit5 rung, on both flights.** This corrects a claim the orchestrator
had already published as [EVIDENCE] mid-session.

## The measurement — [EVIDENCE]
`gp-0x67fa == 4`:
- **Route `54` (V71B): 0 / 123,277 frames.**
- **Route `58` (V71C): 8 / 92,826** — and all eight are a single contiguous **80 ms** burst at
  **0.00 km/h, gear = PARK, `latActive` = 0**: a key-on transient.
- **Every 10-second block on both routes reads exactly 0.000000** (108/108 and 81/81).

⇒ **State 4 never occurred while either car was driving.** V42's governor magnitude substitution fires
**only** in state 4.

## What this corrects
Both V71B and V71C carried `0x454FE` = `B5` (the substitution disabled) and the operator reported the
ratchet unchanged on both. **That was written up as "`0x454FE` is FALSIFIED for the ratchet." IT IS NOT.**
**The lever was never in force on either drive — disabling something that never runs cannot change
anything.** It is a **null by construction**, the same class as `0xC6444` on gateless builds, and exactly
what this kit's conditional-null catalogue exists to catch. **The probe caught what the prose had already
asserted.**

## ★ What survives is STRONGER than the claim it replaces
Since state 4 never occurs while driving, **the substitution never runs on STOCK either** ⇒ the state-4
governor mechanism is **STRUCTURALLY ELIMINATED** as a cause of the current 7.79 Hz ratchet, rather than
merely having failed a test. This independently corroborates the symmetry argument already on record: an
asymmetric clamp should print a **rectified** waveform, and the ratchet measures **symmetric** (skew
−0.16…+0.06, crest 2.07–2.45 against a sine's 1.414).

## ⚠⚠ A TENSION THIS OPENS — [OPEN], do not smooth it
**V42 was CONFIRMED on-car** to fix the ~10 s **hard-turn recovery ratchet** — a *different* symptom from
the 7.79 Hz one. **If state 4 never occurs, V42's fix could not have acted either.** Three readings, none
established:
(a) state 4 does occur, but only under conditions absent from routes 54/58;
(b) V42's original attribution was wrong;
(c) the bit5 measurement does not generalise beyond these two drives.
**Re-fly a route with recorded ratchet episodes and a state probe before concluding anything.**

## How to treat the byte
**V72 carries `0x454FE` = `B5` as an inert, UNTESTED byte** — it costs nothing on any drive where state 4
does not occur, and reverting it would risk regressing V42's confirmed (different) fix.
🛑 **Do not describe it as a ratchet fix. Do not describe it as falsified.**

⊕ With V70's `gp-0x67fa == 10` null (0/18,010), the driving state is **{5, 11}** — both inside all three
dispatcher masks (`0x830`, `0x930`, `0xc30`) ⇒ **the "state 10 splits the assist chain" alternative for the
five-build detector null is DEAD on these routes.** The detector and arbitration were dispatched.

Related: [[accord-v42-ratchet-fix-lost-since-v53]] · [[accord-gp67fa-state-gate-on-assist-chain]] ·
[[feedback-probe-the-gate-not-just-the-output]]
