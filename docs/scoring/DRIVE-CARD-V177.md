# DRIVE CARD — V177  ·  **FLY THIS ONE FIRST**

**Supersedes `DRIVE-CARD-V175.md`.** V177 *contains* V175 and adds **one** cell.

```
image  fc93255645014a0f0d70c199c8e86fa11c6a435b2054c97363b92b6dbd1b8d02
rwd    86cd9394c0f426fe1539294f04b80e5d92ff1ca362af5b1f9fd172d6722eb0f7
file   39990-TVA,A160-V177-V175BASE-K1.COULOMB.REVERT.HONDA.102-0x13000-0x100000.rwd
```

🛑 **Nothing is flashed without you naming the file and the bus, and me repeating them back.**
🛑 **Kill openpilot/pandad first** (`tmux kill-server` on the comma device).

---

## WHY THIS ONE — A VELOCITY-DEPENDENT ASSIST TERM AT 10× HONDA

`0xC40D2` (K1) scales the modelled Coulomb friction. That term is a **saturated ramp** in motor
velocity:

```
ramp     = clamp( motor_rate × 12 / 0xC40BC , ±1 )
friction = ramp × ( |model|·K1/1024 + K0/1024 )        K0 = 0 on every build

  config            K1     ramp width    saturated amp      slope through zero
  Honda            102    ±50 counts    0.0996×|model|      0.00199 / count
  FLYING (V122)   1020   ±250 counts    0.996 ×|model|      0.00398 / count
  V177 (this)      102   ±250 counts    0.0996×|model|      0.000398 / count
```

You have been driving a term whose **saturated amplitude is 10× Honda's** and whose **slope through
zero is 2× Honda's**, sitting directly in the assist path. It has never been tested above 204.

✅ **V177 gives Honda's amplitude at one fifth of Honda's slope** — the gentlest of the three
configurations — because it reverts K1 while keeping V122's wider ramp.

🛑 **Correction to an earlier draft of this card.** I described this as a *relay* injecting a
1.99×|model| **step** ~16 times a second. That was **wrong**: V122 widened the ramp by the same 5× it
raised K1, so the transition spans ±250 rate counts and there is no step. `K0` is also 0, so friction
→ 0 as |model| → 0. The build is unchanged and still right; only my stated mechanism was overstated.

## THE DRIVE — STAGED, SAME AS BEFORE

**STAGE 1 — do this and nothing else.**
1. **TWO passes of engaged creep, 15 s each, 1–24 km/h, real curvature. About 30 s total.**
   **1a — drive it HOW YOU NORMALLY DO** (hands off, or resting). This is the pass that can be
   **scored today**: the whole 27-window historical baseline is hands-off, so this is the only
   pass comparable to it, and the card's thresholds below apply to it.
   **1b — the same again with HANDS ON THE WHEEL.** This answers the confound that `cs_tq` is
   the DRIVER torque sensor, and builds the first hands-on baseline the kit has.
   🛑 **Honest limit on 1b: its detection thresholds are UNKNOWN.** The corpus contains
   **ZERO** continuous 15 s hands-on engaged creep windows, so nothing can be promised about
   what it resolves — it is a baseline-building pass, not a scored one.
   Don't break either pass up — the analysis window is 5.12 s.
2. **Stop.** If the ratcheting/stuttering is obviously still there, say so and we are done with this build.

**STAGE 2 — ONLY if Stage 1 shows it gone or clearly reduced.**
3. **Three more short passes, alternating engaged / LKAS-off**, ~15 s each, same road.

```
python rlog-tools/score/score_band_excess.py <route-tag>
python rlog-tools/score/grind_engaged_vs_manual.py <route-tag>
```

---

## THE DISCRIMINATOR — NOW THERE ARE TWO, AND THEY SEPARATE CLEANLY

`0xC40D2` is a bare `tp` scalar, so it is live in **manual AND engaged**. The inertia revert is
mode-26/27 **only**. The poles act in both. So:

| what you see | which lever did it |
|---|---|
| ratchet falls in **both** engaged and manual, ratio ~unchanged | **K1** — the oversized Coulomb term |
| ratchet falls in **engaged only**, ratio falls | the **inertia** revert |
| ratchet falls, ratio unchanged, manual unchanged | the **assist-section poles** |
| nothing moves | all three accounts fail together |

---

## WHAT TO EXPECT IN THE SEAT

- ⚠ **Steady effort will feel slightly HEAVIER.** The verified chain is *more modelled friction → more
  assist → lighter*, so undoing 10× removes some of the lightness V89 was chasing. **This is the
  trade** — a little steady weight against removing a term whose saturated amplitude was 10×
  Honda’s. If it is too heavy, say so; that is a real result.
- Creep will still feel lighter than the flying build overall (V175's inertia revert is carried).
- Slightly laggier at low frequency (+29 ms at 1 Hz, from V173's poles).
- 🛑 **LKAS authority is NOT measurable on this drive** (one pass bounds it only to 19×). Your
  impression is the instrument — if the car feels like it is not pulling as hard in a lane, say so.

🛑 **Score bands are mine; symptoms are yours.** I will not call anything fixed that you have not.

---

## IF IT IS BETTER BUT NOT GONE

1. **`0xC63A6` (w[3])** — the virgin weight on the inertia lane, un-struck this session. Cheapest,
   most targeted, no lag cost.
2. **V176's pole (0.980)** — −2.9 dB more ratchet, −3.4 dB more grind, for **+14 ms more lag**.
3. **`0xC40DC`** — the acceleration EMA alpha, which V122 also moved 22→8. A *phase* change on the
   inertia term; direction not yet established, so it needs tracing before it is a lever.

## IF IT IS WORSE

Revert and tell me which symptom worsened. A ratchet that **rises** would falsify the polarity chain,
which is the most informative single result available.

---

## 🛑 PRE-REGISTERED, BEFORE THE DRIVE — THE EXACT NUMBERS THE SCORER WILL PRINT

Measured on route `r24`, the **flying build**, same channel and same estimator the scorer uses:

| band | ENGAGED (your car now) | MANUAL | null |
|---|---|---|---|
| GRIND 15–25 Hz | **11.1×** | **2.3×** | ~3.9× |
| RATCHET 5–12 Hz | **26.7×** | **2.8×** | ~3.9× |

**Both manual arms are BELOW the null.** The resonance is engaged-only, so falling below 3.9 is a
reachable outcome, not a hope — manual already sits there.

**So the drive asks one binary question: does the excess fall below ~3.9×?**

| outcome | reading |
|---|---|
| excess drops below ~3.9× | **the symptom is gone by the instrument** — engaged now looks like manual |
| excess falls but stays above | the inertia lane is contributing but is not the whole story |
| excess unchanged (11.1 / 26.7) | the inertia dose is not the mechanism; that account fails |

🛑 **The POLES cannot move these numbers** — a slope-corrected excess measures *peakiness*, and a
broadband low-pass steepens the out-of-band fit too (V184 predicts 11.1 → 11.3). **These columns test
the inertia revert, which V184 and V185 both carry.**

✅ **The poles are tested by the SPECTRAL SLOPE instead**, which the scorer already prints:
`FLYING 1/f^2.671 · V185 1/f^2.671 · V184 1/f^4.531`. History spans 0.80–2.37, so **4.53 would be
outside anything ever recorded** — unmistakable on one pass.

⊕ Because the excess endpoints respond only to the inertia revert, **V184 and V185 are
indistinguishable on them.** V184's only extra is the slope change, bought with **+16.4° of
engaged-only phase lag** that could not be priced against openpilot's margin. **That is why V185 is
the recommended first drive.**
