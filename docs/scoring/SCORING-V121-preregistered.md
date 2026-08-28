# PRE-REGISTERED SCORING — V121

**Build:** `39990-TVA,A160-V121-V112BASE-RELAY.KNEE3000.K1.1020.MAXSAFE-0x13000-0x100000.rwd`
**image** `ce565da74ad93f77c81a3e2572758d5c2df505f6d32889b65c5536904ea7596c`
**.rwd** `8c154edb69ae4649ba55ac4760ae55aec56bd5be2b336e0d8f1e4a46b33512c9`
40/40 assertions · 50/50 CRC · 4 payload bytes · cal-only, no cave · α2 held at 14.

> 🛑 **Written BEFORE the drive, so the result cannot be reinterpreted after it.** Every number below
> is fixed now. Nothing sent to the car; flashing requires the operator to name the file and the bus.

---

## THE EDIT AND WHY IT IS THE ONLY REMAINING DIRECTION

```
0xC40BC  knee  1800 -> 3000     relay saturates 31.8 -> 53.1 deg/s
0xC40D2  K1     612 -> 1020     holds the small-signal gain EXACTLY at V112's 0.0039844
```

Adding **dissipation** is measured-closed: `Y[0]` has 1.11× int16 headroom, and `Y[1]` was flown at
−24000 on V107 and **rails 32.32 % at 10–25 km/h**; at 24–40 km/h — where the oscillation lives —
V108 already rails ≤10.45 %. The binding limit is `gp-0x6b26`'s ±511 clamp (`0xC407E`), which
**cannot be raised** (V73 raised it → V74/V75 hard-faulted). ⇒ **only excitation reduction remains.**

V121 softens the Coulomb relay — the signum indicted as the excitation path — **while holding the
assist constant**, which is why it supersedes V120 (halving K1 would cut excitation *and* assist).

---

## WHAT TO EXPECT — stated as ranges, not hopes

| rate | V112 friction | V121 | ratio |
|---|---|---|---|
| ≤ 30 °/s | — | — | **1.000×, bit-identical** |
| 50 °/s | 0.5977 | 0.9387 | 1.571× |
| ≥ 100 °/s | 0.5977 | 0.9961 | 1.667× |

**More modelled friction = MORE assist**, so above ~32 °/s this should feel *stronger*, not heavier.
⚠ `FUN_0003b8f6` is **not LKAS-gated**, so **manual steering also changes above 31.8 °/s** — the same
trade V112 made.

---

## PRIMARY ENDPOINT (pre-registered, one number)

**Harmonic ratio** — median peak prominence at `2f₀`/`3f₀` over the off-multiple controls
`2.37f₀`/`2.63f₀`, on the top 5 % of engaged windows by 6–9 Hz content.
Tool: `rlog-tools/studies/peakturn/harmonic_dose_vs_knee.py`.

```
V112 measured:  r22 0.970 · r23 1.455 · median 1.213
knee trend:     300 -> 1.743 · 600 -> 1.412 · 1800 -> 1.213
```

| outcome | reading |
|---|---|
| **< 1.05** | relay confirmed as the excitation path; knee is the lever; go further only if rail duty allows |
| **1.05 – 1.35** | **NOT RESOLVED** — inside V112's own two-drive spread (0.970–1.455). Do not call it either way |
| **> 1.45** | mechanism **refuted**; stop pursuing the relay for this symptom |

🛑 **V112's own two drives span 0.970–1.455.** A single V121 drive landing anywhere in that band
means **nothing**, and I will say so rather than reading a trend into it.

## SECONDARY (reported, never used to overturn the primary)

1. **6–9 Hz rate rms p90 at |ang| ≥ 20°**, matched on small-angle p90 — the design that survives
   route variance. V112: r22 2.909, r23 8.320.
2. **Assist check:** engaged p99 |rate| should be **≥ V112's** (77.1 °/s). A drop below ~70 °/s means
   the knee cost authority and V116 (the smaller step) is the fallback.
3. **Fault-free:** `STEER_STATUS == 4` count must be **0**. Any fault ⇒ revert immediately.
4. 🛑 **GRIND #1 IS NOW AN ENDPOINT — CORRECTED 2026-08-28 on the operator's report that it moved
   to a higher frequency.** Band is **21-26 Hz**, not 18-22: the engaged excess peaks at ~23 Hz on
   recent builds (15.0 Hz on stock), and the kit's two old bands straddle it. On 21-26 Hz the knee
   shows a monotone dose-response — knee 300 / 600 / 1800 → 0.631 / 0.246 / 0.213, ratio 300/1800 =
   **2.956 [1.164, 4.079]** and 300/600 = **2.565 [1.010, 4.664]**, both excluding 1.0.
   ✅ **V121 continues that axis (1800 → 3000), so grind #1 SHOULD improve.** Report the 21-26 Hz
   engaged share, p90, as a share of 1-45 Hz. V112 baseline: **0.21341**.
   ⚠ knee is confounded with K1, so a change attributes to the axis, not to either cell.

---

## OPERATOR ASKS — worth more than another analysis pass

1. **Include 2–5 mph engaged creep**, several minutes. No post-V107 route has any, which is why
   grind #1 cannot currently be measured at all.
2. **Mark grind #1 when it happens** — a horn tap or a spoken note. One timestamp made the peak-turn
   oscillation locatable; the same would work here.
3. **Separately: one stock-configuration drive** takes the angle-gating result from **p = 0.100 to
   p = 0.018**. It needs no build and no flash.

---

## HONEST STATUS

**V121's effect on the oscillation is UNKNOWN.** Its harmonic rationale is **[BELIEF]** — monotone
across three knee levels but ρ = −0.291, p = 0.257 — and the one simulation available failed to
reproduce that trend (invalidly, since a memoryless nonlinearity in a closed loop cannot be simulated
from the loop's own output, but it did not support it either).

What V121 *is*: the largest gain-matched knee step that keeps `K1/1024 = 0.996` under the
sign-inversion ceiling, bit-identical below 31.8 °/s, more assist above, cal-only, 4 bytes — and the
only direction on this symptom that is not measured-closed.
