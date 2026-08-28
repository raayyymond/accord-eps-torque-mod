---
name: accord-v113-built-knee-with-k1-held
description: "V113 raises the Coulomb relay knee 600->1800 with K1 HELD at 204, so the friction-compensation term is provably <= V111's at EVERY rate (exhaustive sweep, worst excess +0.000000). This SUPERSEDES V112, which scaled both cells and thereby delivers up to 2.93x MORE anti-damping above 10.6 deg/s - V94's failure mode. Two payload bytes, 39/39 assertions. V112 SHOULD NOT BE FLOWN."
metadata:
  node_type: memory
  type: project
---

# 🛑🛑★★★★★ V113 BUILT — AND IT **SUPERSEDES V112**, WHICH SHOULD NOT BE FLOWN

2026-08-27. **A correction to my own recommendation from earlier the same day.**

```
builder  analysis-2020accord/builds/v108_plus/build_v113_tva.py   39/39   BASE = V111
image    d2e86f8272dff71d402680399649dc35b7e39f6e7b200ae9c5a7ee9812ba823b
.rwd     07d64f509e6d92a538a26b99778888568b2ac8fc88ca731556cfa025e4dc3e5a
0xC40BC   600 -> 1800   the relay KNEE      (saturation 10.6 -> 31.8 deg/s)
0xC40D2   204 ->  204   K1 -- HELD, NOT WRITTEN.  The entire safety argument.
2 payload bytes + 1 CRC trailer (0xC40BC 5802->0807, 0xC4FFC 8ff3fe42->01abcdc0).  NO CAVE EDIT.
```

## 🛑 WHY V112 IS WITHDRAWN
V112 scaled knee **and** K1 ×3 together to hold the small-signal gain exactly. Elegant — and the
wrong direction on the one axis that has already hurt this car.
```
  friction = EMA(|model| * K1/1024 * sat(POL * gp-0x6abc * 12 / knee))
  residual = model - friction - inertia          # MORE friction => MORE assist
```
The EMA (cal `0xC40D0` = 408) adds only **−1.1° at 2 Hz to −11.1° at 21 Hz**, so the term sits
essentially **in phase with RATE** — and it is a friction *compensation*, so more of it is
**ANTI-DAMPING**. Describing function of the odd saturation:
```
   peak rate    V111 g_eff   V112 g_eff   ratio
    <=10 d/s     0.01877      0.01877     1.00    (both unsaturated -- identical)
      30 d/s     0.00828      0.01877     2.27
      80 d/s     0.00316      0.00925     2.93
```
⇒ **V112 delivers up to 2.93× MORE anti-damping above 10.6 °/s**, in the band where
[[accord-rez-antidamping-replicated-three-drives]] measures `Re(Z) < 0` from 2 to ~24 Hz.
🛑 **That is V94's failure mode.** V94 cut the `gp-0x6b26` damper believing it pure inertia;
operator verbatim: *"Made the stuttering and grinding worse, by a lot. So much so that it vibrated
the entire car, and I decided it was not safe to drive."* Measured afterwards that lane sat at
**+137°/+139° vs wheel rate at 6–9 Hz ⇒ +518/+565 counts of POSITIVE Re(Z)** — a real damper.
**Adding anti-damping and removing damping are the same move on the stability axis.**
⊕ And the physics agrees: **real Coulomb friction IS constant-magnitude** (`μN·sign(v)`). A
saturating relay reproduces exactly that. **The saturation was never the bug — it is the model.**

## ⭐ WHAT V113 DOES INSTEAD — AND IT IS PROVED, NOT ARGUED
Raise the knee, hold K1. Because K1 is held, raising the knee can only **shrink** `sat()` at every
rate ⇒ the term is **≤ V111's AT EVERY RATE**. The builder proves it by exhaustive sweep over the
whole reachable input range, `worst excess +0.000000`:
```
   rate      V111 term   V113 term   ratio
    3 d/s     0.05632     0.01877    0.333
   10 d/s     0.18775     0.06258    0.333
   20 d/s     0.19922     0.12517    0.628
   30 d/s     0.19922     0.18775    0.942
   60 d/s     0.19922     0.19922    1.000   <- both railed; equal, never greater
```
Two things improve together, both in the safe direction:
- **less relay-ness** — measured saturation duty in the operator's own grind-#1 regime falls
  **0.7439 [0.669, 0.815] → 0.2353**, a 3.2× cut (route 21, 5–10 mph, engaged, hands-off, cmd≥2048);
- **less anti-damping** — small-signal slope falls **0.0039844 → 0.0013281 (×0.333)**.

## ⚠ THE COST, STATED PLAINLY
Less friction compensation ⇒ the driver feels **more of the real mechanical friction**. The wheel
will feel **HEAVIER than V111**, most noticeably below ~30 °/s. That is the opposite of the
operator's stated *"low apparent friction"* preference and it is the price of not repeating V94.
`FUN_0003b8f6` is **not LKAS-gated**, so manual feel changes too.

## ✅ READ THE NEXT DRIVE AS A THREE-WAY DISCRIMINATOR
| report | conclusion |
|---|---|
| *"heavier but smoother"* | the knee is the right axis — walk the dose back toward 1200 |
| *"smoother and no heavier"* | V112's premise was wrong in the safe direction; nothing lost |
| *"no change"* | the relay is not the ratchet mechanism — **abandon this axis** |

## GATES
✅ **GATE 1** — one reader, two methods agreeing: `0xC40BC` at `0x3BAB4`. K1 not written at all.
✅ **GATE 2** — odd memoryless saturation ⇒ DF real ⇒ **zero phase added**, and the magnitude only
**falls**. There is no stability argument to make: the term is smaller everywhere.
✅ Clamp cannot bind: `|model| ≤ 0.4851` ⇒ `friction_max` 0.0966 vs the ±10.0 clamp, **103×**.
✅ `0xC40D0` = 408 and `0xC4080` = 0 untouched; `gp-0x6b26` Y rows untouched (**V94 territory**);
the 164-byte cave byte-identical ⇒ outside the bricking class.
🛑 `0xC40DC` α2 stays at V111's **14** ⇒ the next report is still a single-variable read.

Related: [[accord-knee-and-k1-decouple-lightness-from-relayness]] ·
[[accord-the-coulomb-relay-is-located-c40bc-is-its-knee]] ·
[[accord-v94-flew-and-the-lane-is-a-damper]] ·
[[feedback-do-not-buy-ratchet-with-mass-and-friction]]
