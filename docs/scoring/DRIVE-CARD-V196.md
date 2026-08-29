# DRIVE CARD — V196, the grind lever plus the ratchet lever

**File:** `39990-TVA,A160-V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE-0x13000-0x100000.rwd`
**Image SHA256** `f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V195 plus three int16.** V195 carries the grind notch; V196 adds the one frequency-selective
lever left for the ratchet — halving the engaged anti-damping inertia term.

| | |
|---|---|
| engaged inertia Y | `(-9830, -5734, -1966)` → **`(-4915, -2867, -983)`** |
| manual inertia Y | **untouched, byte-identical** |
| frequency weighting | **ω² — 67× stronger at 8.2 Hz than 1 Hz** |
| effect at DC | **zero** — no LKAS authority cost, no added steering weight |
| carried | the re-fitted notch · K1 → Honda · accel alpha → Honda · w[3] halved · FactorC m27 stock |

## ⭐ Why this should work — the term is a SATURATED RELAY today
`gp-0x6b26` is clamped at ±511. The build on your car saturates that clamp at
**|accel| > 1065**, so above that it is **pinned and flips sign with acceleration — a relay,
not a proportional inertia.** V196 raises the saturation point to **6389**, keeping the term
proportional across **6× more** of the range.

🛑 **Tested and partly withdrawn:** the ratchet shows **no odd harmonics** (3f0/control 1.21)
and a **521× amplitude spread**, so it is a **driven resonance, not a relay limit cycle** — the
plant owns the oscillation. The saturated term does not *create* it; it **injects broadband
energy that excites it**. So expect V196 to reduce **one exciter among several**, i.e. a partial
effect rather than elimination.

✅ **What survives: the sign-safety.** Reducing a saturated term's injected energy is
directionally safe whichever way its sign runs — less injection is less excitation either way.
That is the part that mattered, and it does not depend on the withdrawn claim.

## The trade, so you know what to feel for
Negative apparent inertia makes the wheel feel **lighter to fast inputs**. Halving it moves the
wheel closer to its true inertia **at high frequency only**. Slow steering, LKAS authority and
steering weight are unchanged — the term is zero at DC.

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.**
2. `python rlog-tools/score/score_band_excess.py <route-tag>`
3. `python rlog-tools/score/cross_channel_band_excess.py`

## 🛑 Pre-registered
```
   ratchet excess 26.7x -> toward the manual floor 2.8x (null ~3.9)  => RATCHET GONE
   cs_rate grind excess 7.3x -> below the null                       => GRIND GONE
   ratchet gets WORSE                                                => the anti-damping sign is
                                                                        inverted; revert to V195
   ratchet unchanged, grind gone                                     => the ratchet is not in this
                                                                        lane either; the remaining
                                                                        candidate is the detector
                                                                        route, i.e. V194
```

## ⚠ Stop conditions
- **Ratcheting noticeably worse** ⇒ inverted sign. Reflash V195.
- **Wheel feels heavy or dead to fast inputs** ⇒ the half-dose is too much; quarter it.
- **A new high note WHILE ENGAGED** ⇒ the 55 Hz null. Manual driving is stock.
