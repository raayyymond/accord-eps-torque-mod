# SCORING V158 — pre-registered BEFORE the drive, 2026-08-29

🛑 **Written and committed before any V158 flight exists.**

## 🛑 THE RECOMMENDATION CHANGED, AND A POWER CALCULATION IS WHY

V160 (V158 + Lever B `0xC6446` 5244 → 6553) was the lead build. **It is demoted to a follow-up.**

V88 measured Lever B single-variable across a **10.24×** step (512 → 5244). V160's increment is
**1.2496×**. Extrapolating log-linearly from V88's own measured band ratios:

| band | V88's 10.24× step | V160's 1.25× increment predicts |
|---|---|---|
| 6–9 Hz | 0.859 | **0.986** — 1.4 % further |
| 9–12 Hz | 0.604 | **0.953** — 4.7 % further |
| 15–22 Hz | 0.549 | **0.944** — 5.6 % further |

against this kit's own same-firmware detection floor:

| band | null CI | not resolvable under |
|---|---|---|
| 6–9 Hz | route-71 split-half [0.18, 5.51] | ~3–5× |
| 18–22 Hz | r22 vs r23 [0.59, 1.34] | ~40 % |
| 21–26 Hz | r22 vs r23 [0.80, 1.20] | ~20 % |

⇒ **the Lever B increment is 4–30× below the floor. It cannot be measured on one drive.** It adds an
untested dose (V62's lesson: *"2× ≈ the OPTIMUM, not a point on a ramp"* — 5244 may already be at or
past optimum) and destroys attribution if the drive comes back worse.

**Fly V158. It is single-variable vs V122, and its change is the only one large enough to resolve.**

## What V158 is

V122 + the golden model's own damper prescription, **6 halfword edits, 10 payload bytes**, 67/67
assertions, CRC 50/50.
image `42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf`

```
0xD77DA / 0xD77EE   FactorC (L2 speed) Y[0]  0 -> 429 / 426   (each mode's own Y[2])
0xD780E / 0xD7822   FactorE (L4 rate)  X[0]  60 -> 12
0xD7818 / 0xD782C   FactorE (L4 rate)  Y[1]  140 -> 539       (its own Y[2])
```

**It is the first build in this kit's history to deliver ANY base-assist damping at creep.** Stock and
every prior build sit at exactly 0 there, because `FactorC Y[0] = 0` zeroes the five-factor product
below 35 km/h.

### The predicted effect, in physical units — stated in advance

| source | viscous damping at creep |
|---|---|
| stock / V122 | **0.000** ct/(deg/s) |
| `gp-0x6bbe` (measured on-car, independent) | 1.571 ct/(deg/s) |
| **V158's damper** (from its own bytes) | **2.733** ct/(deg/s) |
| **total (Path 1 nominal)** | **4.304 — ×2.74** |
| **total NET of Path 2** | **2.63–3.53 — ×1.67 to ×2.25** (stability-bounded; see STATE) |

⚠ **[BELIEF] what that buys in ζ.** *Only* if the firmware's viscous term dominates damping would ζ go
**0.017–0.036 → 0.047–0.099**. If mechanical damping dominates, less. The Path-1 nominal is the
increment, NOT a ζ prediction.** The **x1.7-x2.7 NET** figure above is the one to hold: x2.74 is the
Path-1 nominal, before Path 2's stability-bounded pumping copy is netted off. This is the single
largest uncertainty and the drive is what settles it.


---

## 🛑 WHAT THE DRIVE MUST CONTAIN — not optional

V158's edit is **architecturally inert above ~35 km/h** (that is where stock FactorC already leaves
the dead zone). A highway drive tests nothing.

1. **Engaged creep, 2–8 km/h, with real steering activity.** This is the entire target band. Without
   it there is no result at all.
2. **AUDIO.** Only 5 of ~230 routes have usable creep-engaged audio, and the bus instrument has
   already been shown not to track what the operator hears (the engaged-vs-manual contrast collapses
   to **~1.1×** under controls, yet V88 demonstrably changed the felt symptom).
3. **At least one slow hard turn, hands-off, engaged** — the peak-command oscillation.
4. **A matched MANUAL creep segment** — same speeds, LKAS off. Without it every ratio is uncontrolled,
   and this session watched three uncontrolled ratios collapse when controls were added
   (2.8→1.12, 1.29→0.911, 1.309→0.958).

## PRIMARY — the operator's report

Standing rule: **score bands, let the OPERATOR score symptoms.** Three questions, each vs **V122**:

1. **ratcheting / stuttering at creep** — better / same / worse, **and at what speed**;
2. **grinding** — better / same / worse, and at what speed;
3. **steering effort / apparent mass at creep.** ⚠ V158 ADDS damping, which is drag. The operator's
   standing constraint is *low apparent mass and friction to LKAS AND no ratcheting*. If the ratchet
   improves but the wheel feels heavier at parking speeds, **that is the trade to report**, and the
   answer is to lower the dose, not abandon the lever.

## SECONDARY — bands, episode-clustered and speed-matched

Use **`rlog-tools/score/score_v158_creep.py`**. 🛑 **NOT `score_v133_creep.py`** — audited 2026-08-29 and its `boot()` is a **WINDOW** bootstrap (`rng.choice(e[:, i], len(e))`), which this kit’s standing rule forbids; measured **2.6x too confident** on synthetic data. The corrected scorer resamples EPISODES. Requirements it already satisfies:

- **episode bootstrap, never window bootstrap** — window bootstraps manufacture significance;
- a **30–40 Hz negative control** — a ratio moving in both signal and control bands is a global
  change, not a damping result;
- a **per-window speed census** — a moving wheel order manufactures "only on route X" lines;
- **safe cache pairs only**: `(t, probe)` or `(raw14_t, raw14_b4)`. Pairing `t` with `raw14_b4` reads
  the cave byte ~10 ms early = **28° of phase error at 7.79 Hz**.

## What will NOT be claimed

- No spectrum from the 427 wire (`0x1AB` samples at **49.8 Hz** ⇒ Nyquist 24.9 Hz).
- No ζ estimate from a band ratio — ζ needs a **ring-down**, the only estimator that passed its control.
- No "damping restored" claim from a 6–9 Hz ratio inside [0.18, 5.51]. **"Cannot resolve" is the
  honest reading, not "unchanged."**
- No amplitude claim from the `gp-0x6b98` probe — it under-ranges to ~1.5 bits; it is a **spectral**
  instrument only.

## Decision tree — committed in advance

| V158 result vs V122 | next build | why |
|---|---|---|
| ratchet **better**, effort acceptable | **V160** | take the free Lever B increment; then consider a damper dose ladder |
| ratchet **better**, wheel too heavy | lower FactorC `Y[0]` 429 → 234 (its own `Y[1]`) | dose 50 → 27, monotone, halves the drag |
| ratchet **unchanged**, effort unchanged | **V165** — damper dose ladder | the x1.7-x2.7 net was too small ⇒ the firmware term does not dominate the plant damping; the model’s *"err low"* argument is then overturned BY DATA |
| ratchet **worse** | **V167** (`0xC63A0` 1024→512), NOT a bare revert | **NAMED MECHANISM**: gp-0x6bd0 feeds BOTH aggregators, and Path 2 (FUN_00038148 @0x38150) applies an EXTRA pol multiply, so at pol = -1 it arrives PUMPING-signed. 0xC63A0 is that term’s Path-2 weight ALONE, so halving it removes half the pumping while keeping Path 1’s damping — it DISCRIMINATES, where a revert to V122 discards both and tells you nothing. Revert to V122 only if V167 is also worse. |
| **no creep episodes in the drive** | re-drive | the edit is inert above 35 km/h; a null would be for the wrong reason |

## Confounds stated in advance

- V158 changes **FactorC and FactorE together**. They are not separable on one drive, and the model's
  own analysis says neither alone reaches the required dose — so this is deliberate, not sloppy.
- **The damper is a drag term.** Any ratchet improvement is expected to come *with* some added effort.
  Reporting both is what makes the next dose choice possible.
- Damping fades as rate → 12 counts (`dose ∝ rate − 12`), so the very deepest micro regime gets less
  than the table suggests. This is deliberate (the model argues `X[0] = 12`, not lower).
