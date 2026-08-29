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

## WHY THIS ONE — WE HAVE BEEN DRIVING A RELAY

`0xC40D2` (K1) scales the modelled Coulomb friction, and that term is a **sign function of motor
velocity**:

```
friction = |model| · sign(motor rate) · K1/1024
⇒ every velocity reversal STEPS it by 2·|model|·K1/1024

   Honda   K1 =  102  →  0.199 × |model|
   V89     K1 =  204  →  0.398 × |model|      (flew, "delivered but small")
   flying  K1 = 1020  →  1.992 × |model|      ← what you have been driving since V122
```

At an 8 Hz ratchet the motor reverses **~16 times a second**, so a step of about **2× the model
value** is injected 16 times a second, **in sync with the oscillation**. That is a **relay** — the same
failure mode as V80, which produced "the worst grinding ever" in a different lane.

🛑 **V89's own docstring pre-registered this** — *"larger K1 = a larger step at each reversal,
notchiness on turn-in… transient, unmeasured."* **V122 then took it to five times that value and it
has still never been tested.** V177 puts it back to Honda's 102.

⊕ A relay's gain **does not shrink with amplitude**, which is exactly why none of my linear
transfer-function work would ever have found it. It also means it can sustain a mode that the linear
analysis says should already be damped.

---

## THE DRIVE — STAGED, SAME AS BEFORE

**STAGE 1 — do this and nothing else.**
1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h**, real curvature. Don't break it up.
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
| ratchet falls in **both** engaged and manual, ratio ~unchanged | **K1's relay** — the new one |
| ratchet falls in **engaged only**, ratio falls | the **inertia** revert |
| ratchet falls, ratio unchanged, manual unchanged | the **assist-section poles** |
| nothing moves | all three accounts fail together |

---

## WHAT TO EXPECT IN THE SEAT

- ⚠ **Steady effort will feel slightly HEAVIER.** The verified chain is *more modelled friction → more
  assist → lighter*, so undoing 10× removes some of the lightness V89 was chasing. **This is the
  trade** — a little steady weight against removing a 2×|model| step at every reversal. If it is too
  heavy, say so; that is a real result.
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
