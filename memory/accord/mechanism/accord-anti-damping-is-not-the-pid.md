---
name: accord-anti-damping-is-not-the-pid
description: "At 6-9 Hz the PID's own terms sum to a NET DAMPER (P -0.145, I -0.053, D +0.077 => -0.121) while the measured driving-point impedance Re(Z) reads -3375 ct*s/rad = ANTI-DAMPING, at coherence 0.769 vs a shuffled 0.001. So the anti-damping is NOT coming from FUN_0003a382 — it is another aggregator lane, or the plant. Every remaining firmware candidate has to answer this, and the manual hands-off coast (2 windows / 21.4 s in the whole corpus) is the experiment that decides it."
metadata:
  type: reference
---

# 🛑🛑 The anti-damping is NOT the PID — measured 2026-08-11 (V90, route 77)

```
   at 6-9 Hz:  P -0.145    I -0.053    D +0.077   =>   NET -0.121   ==  DAMPING
   measured Re(Z) at 6-9 Hz  =  -3375 ct*s/rad   ==   ANTI-DAMPING
   (coherence 0.769 against a shuffled 0.001, 221 windows / 884.5 s)
```

🛑 **Two opposite sign conventions are in play and confusing them inverts this. Both stated:**
per-term dissipative products (the D-sweep's convention) — **negative = damping**, positive = pumping;
`Re(Z)` — **positive = damping**, negative = anti-damping. Predicted phases: inertia +90°, damper 0°,
spring −90°, negative damping 180°.

> ⇒ **The PID is a net DAMPER at the ratchet frequency, and the column is anti-damped anyway. The
> anti-damping is NOT coming from `FUN_0003a382`.** It is another aggregator lane, or the plant itself.
> **[EVIDENCE for both halves; BELIEF as to which alternative.]**

**It reframes the whole search:** a lever that trims a PID term is trimming something that is **already
on the damping side of the ledger.** Every remaining firmware candidate has to answer this.

## Supporting measurements

- **`Re(Z) < 0` across 2–16 Hz, REPLICATED at 37× V89's exposure** — −3375 at 6–9 Hz against V89's
  ≈ −3300 on an independent drive; phase −125° to −152°, never near +90° ⇒ **inertia refuted again.**
- **Extended to 35 Hz on the frozen estimator** (pre-declared trust gate coh² ≥ 0.10 **and** ≥ 5×
  shuffled; all ten bands pass; §4.1's own bands reproduce bit-for-bit as the positive control):
  **`Re(Z)` FLIPS SIGN between 22–26 and 26–31 Hz** — the column is **anti-damped 2–26 Hz and
  positively damped 26–35 Hz**, at the two highest coherences in the sweep.
  ⇒ **grind #2's band is not anti-damped at all**, corroborating the load/speed dissociation from a
  second, unrelated instrument.
- 🛑 **This result depends entirely on the rate channel.** With `rate_c` instead of `rate_f`, 26–31 Hz
  reads +0.184 PUMPING instead of −0.336 DAMPING at identical coherence. See
  [[accord-rate-channel-rule-and-its-scope]].

## 🛑 The experiment that decides whether ANY firmware lever can work

Three results converge: `Re(Z) < 0` across 2–26 Hz · the PID is a net damper there · the damping
levers that could push against it are **spent** ([[accord-six-levers-closed-on-arithmetic]]).

> **If the 2–26 Hz anti-damping lives in the PLANT rather than the firmware loop, NO firmware lever
> can remove it** — firmware could only *add damping against* it, and the available damping levers are
> far too small. **The measurement that separates the two cases is the MANUAL HANDS-OFF COAST, and the
> entire corpus contains 2 windows / 21.4 s of it** (V89's routes had 6/1/0).

**Cost ~15–20 minutes.** Measured yield **0.25 qualifying windows per second** of continuous hands-off
time ⇒ ~6 runs of 30 s = ≈40 windows (usable but wide); ~14 runs = ≈100 windows (comparable to the
engaged arm). Half at 30–50 km/h, half at 60–80 km/h. **It also yields 12–16 clean ring-down edges for
free**, against the 1 the entire corpus has.
**Manoeuvre:** straight/empty/level road → **disengage with the CANCEL BUTTON, not the brake and not
by grabbing the wheel** → hands off, foot off the brake, steady throttle → coast 25–30 s → re-take
normally; hold ~5 s of steady engaged driving *before* pressing cancel so the edge has a pre-state.
**Invalidating:** any braking · `steeringPressed` · re-engaging · leaving the speed band · a gear
change · stopping · any steering input.
🛑 **Safety is the operator's judgement, not the kit's.** A missing control is a far better outcome
than an incident.

⊕ **A hint, underpowered and NOT evidence:** `ENGAGED hands-ON moving` (11 windows) reads `Re(Z)`
**+441** at 2–4 Hz and **+1214** at 4–6 Hz — the driver's grip appears to restore positive damping,
consistent with the corpus's standing grip finding. **coh² 0.023–0.228 vs a shuffled 0.006–0.035, so
6–9 Hz in particular is uninterpretable.**

Source: `docs/scoring/SCORING-2026-08-11-v90-flight.md` §4.1, §4.1a, §4.1c, §11.0–11.2 ·
`docs/review/GATE2-2026-08-11-cbe74-independent.md` N1.
Related: [[accord-ratchet-is-a-lightly-damped-resonance]] · [[accord-rate-channel-rule-and-its-scope]] ·
[[accord-six-levers-closed-on-arithmetic]] · [[accord-friction-polarity-more-friction-is-more-assist]]
