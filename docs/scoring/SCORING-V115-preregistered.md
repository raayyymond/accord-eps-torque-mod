# PRE-REGISTERED SCORING — V115  (the α2 lever, for GRIND #1)

**Build:** `39990-TVA,A160-V115-V112BASE-ALPHA2.14.TO.8-0x13000-0x100000.rwd`
**image** `5f804a8a2aee5e18da226cfebe4b2bec564713a4183613e3aed846460a191a97`
**.rwd** `f1a47bb7…` · 42/42 assertions · cal-only, no cave.

```
0xC40DC   14 -> 8      alpha2, the EMA-A coefficient in FUN_00041464   (1 PAYLOAD BYTE + 1 CRC trailer)
byte-verified identical to V112: knee 1800 · K1 612 · K0 0 · pole 408 · clamp 511
                                 gain 5346 · Lever B gate FB / arm 5244
```

> 🛑 **Written BEFORE the drive.** Every threshold below is fixed now. Nothing has been sent to the
> car; flashing requires the operator to name the file and the bus.

---

## WHY THIS BUILD — the one frequency-selective lever in the firmware

`alpha2` is EMA-A's coefficient (`state += (diff·alpha2) >> 6` ⇒ `alpha = alpha2/64`) acting on a
**first difference**, so the lane is `|1−z⁻¹|·|H_ema|` — **a differentiator whose response rises with
frequency.** Lowering `alpha2` pulls the corner down and therefore cuts **high** bands far more than
low ones. **Selectivity by construction, not by tuning.**

```
   freq       a2=14      a2=8      ratio    what lives there
    3.0 Hz   0.018795   0.018665  0.993x   LKAS command band -- UNTOUCHED
    7.8 Hz   0.048071   0.046008  0.957x   the peak-turn oscillation / the damper   -4.3 %
   23.4 Hz   0.126319   0.098848  0.783x   GRIND #1 PEAK                           -21.7 %
```

**Selectivity 5.07× toward grind #1 and away from the damper**, with the LKAS command band
effectively untouched ⇒ **it removes loop gain at 21–26 Hz without adding mass, friction or inertia.**

**Safety gate, against the kit's worst precedent:** this is the lane **V94 cut 6× (to 0.167×)**, after
which the operator aborted (*"vibrated the entire car"*). **V115 costs 4.3 % of that damper — 1/20th
of V94's change.** ⊕ And the precedent is flown: **V109's `alpha2` 22→14 was selective the same way
(7.19×) and flew fault-free on V111 and V112.**

---

## PRIMARY ENDPOINT (pre-registered, one number)

**21–26 Hz engaged share** — band power as a fraction of that window's own 1–45 Hz power, p90, over
engaged windows with `v > 1 m/s`.
Tool: `rlog-tools/studies/peakturn/grind_lever_hunt_corrected_band.py`.

```
V112 baseline (r22, r23):  0.21341
predicted, if the lane arithmetic is right: about 0.783 x 0.21341 = 0.167
```

| outcome | reading |
|---|---|
| **≤ 0.180** | α2 confirmed — the axis works; **α2 = 6 is the next step** (−35.2 % grind, −8.7 % damper) |
| **0.180 – 0.230** | **NOT RESOLVED** — inside the V112 two-drive spread. Do not call it either way |
| **> 0.230** | α2 **refuted** for grind #1; stop this axis and fly V121 instead |

🛑 **The band is 21–26 Hz, NOT 18–22.** The kit's old bands straddle the real peak (~23 Hz on recent
builds, 15.0 Hz on stock) and both miss it — that error produced every grind #1 null this session.

## SECONDARY (reported, never used to overturn the primary)

1. **Peak frequency, 15–40 Hz, top-quartile windows.** V112: **21.09 / 21.29 Hz**. α2 lowers the pole,
   so expect **≤ 21.1 Hz**. A *rise* would contradict the mechanism.
2. **The damper must survive:** 6–9 Hz rate rms p90 at |ang| ≥ 20°, matched on small-angle p90.
   V112: r22 2.909, r23 8.320. **A large rise is the V94 signature ⇒ revert.**
3. **Assist check:** engaged p99 |rate| ≥ V112's **77.1 °/s**. α2 should not touch this (0.993× at
   3 Hz); a drop would mean the lane matters more at low frequency than the arithmetic says.
4. **Fault-free:** `STEER_STATUS == 4` must be **0**.

---

## OPERATOR ASKS

1. **Note whether grind #1 changed in character, not just level** — it moved *up* in frequency once
   already, and that is what invalidated the kit's band. If it moves again, say so.
2. **Include 2–5 mph engaged creep** if convenient. Not required for the primary endpoint any more,
   but it restores the historical comparison.
3. **Separately: one stock-configuration drive** takes the angle-gating result from p = 0.100 to
   p = 0.018. No build, no flash.

---

## HONEST STATUS

**The structural half is strong**: the selectivity is arithmetic from the traced lane, and the safety
margin against V94 is 20×. **The empirical half is weak**: `alpha2 = 14` exists on only **3 routes**
(V111, V112), so the measured amplitude and frequency hits are **collinear with build era**. The
arithmetic also assumes the **1 kHz** task rate for `FUN_00041464`.

⇒ **[EVIDENCE that the lane is frequency-selective; BELIEF that it moves grind #1 on the road.]**
V115 is one payload byte, the smallest possible test of the axis, and its predecessor step already
flew twice without fault.
