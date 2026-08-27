---
name: accord-the-antidamping-is-hondas
description: "Stock Re(Z) at 6-9 Hz is NEGATIVE at every speed — the anti-damping is Honda's, we only multiply it 2.4-3.0x. But at 22-26 Hz stock is DAMPED and our builds REVERSE THE SIGN. First instrumented stock baseline."
metadata:
  type: reference
---

⭐⭐ **The first instrumented STOCK baseline this kit has ever had** — route `0x97` (V9b), **688.8 s
engaged in 19 episodes, p50 72 km/h**, 2.8× the best prior exposure and the first substantially
highway-weighted stock arm. Operator: *"No vibration or grinding. Maybe ever so slightly, barely
perceptible ratcheting."*

## 🛑 THE ANTI-DAMPING AT 6–9 Hz IS HONDA'S [EVIDENCE]
Frozen `decode_v90_probe` estimator, mask `latActive & ~steeringPressed & v>0.5`, `tq`×`rate_f` **both
fields of the same `0x18F` frame** so staleness cancels, speed-matched, shuffled controls ≈0.000,
coh² 0.6–0.8:

| speed | **STOCK** | V100 4× | V102 6× | mod/stock |
|---|---|---|---|---|
| 29–58 km/h | **−1297 [−1805,−989]** | −3376 | −3844 | 2.60× / 2.96× |
| 58–86 km/h | **−1709 [−1937,−1451]** | — | −4089 | 2.39× |
| 86–115 km/h | **−1507 [−1746,−1217]** | −1683 | −1034 | 1.12× / **0.69×** |

⇒ **Honda ships the anti-damping. We multiply it 2.4–3.0× at 29–86 km/h — and NOT at highway speed.**
⇒ **The ratchet has a STOCK FLOOR. It is not purely ours. What is ours is the SIZE.**

## ⭐ BUT AT 22–26 Hz WE REVERSE THE SIGN [EVIDENCE]
| 22–26 Hz | STOCK | V102 6× |
|---|---|---|
| 29–58 km/h | **+247 [+82,+457]** damped | **−134 [−189,−11]** ANTI-damped |
| 58–86 km/h | **+496 [+97,+833]** damped | **−99 [−188,−18]** ANTI-damped |
**Disjoint CIs. The ONLY band where our firmware changes the SIGN rather than the size — and it is the
vibration band.** That is why stock has **no line at all**, not a smaller one.

## THE SPECTRUM — exactly two excesses
Matched speed, tyre orders 1–6 vetoed. 🛑 **Stock's absolute peak in every highway bin is a TYRE ORDER**
(9.57 Hz @70–80, 12.30 @90–100, 14.94 @110–120 km/h — it tracks speed exactly). Per-1-Hz `tq` ratio to
stock at 100–110 km/h is flat 2–5× **except 7:20, 8:16, 24:50**.
⇒ ⭐ **EXACTLY TWO EXCESSES OVER STOCK — 7–8 Hz and 23–25 Hz.** His two symptoms, and nothing else.
**Negative control passes**: at matched 65–115 km/h stock's 18–28 Hz argmax has **prominence 2.31** with a
CI spanning the whole search band, vs **V102's 75.73 at 24.61 Hz.** Two agents, two independent
estimators, same conclusion.

## THE MODE EXISTS ON STOCK; THE AMPLITUDE IS OURS
Ring-down (`studies/damping-q/qd_final.py` verbatim; envelope = `scipy.signal.hilbert`, **never** the broken
`band_envelope`): **STOCK f0 7.42 Hz, ζ 0.0275–0.0321, Q 15.6–18.2, line 29.8–62.0 ct** · **V102 7.81 Hz,
ζ 0.059–0.072, Q 7.0–8.5, line 905–996 ct — 16–30× stock's.**
Positive control **PASSES** (log-log r = +0.970, slope +1.107; trust only **Q ≈ 10–50**).
🛑 **n = 1 usable ring-down per arm** — only 8 falling edges exist on the whole route. **Census limit.**
⇒ **[EVIDENCE]** stock carries the mode. **[BELIEF, n=1]** we do not lower its Q; **we drive it 16–30×
harder.**

## ABSOLUTE LEVELS — what "eliminated" means as a number
`tq` band-RMS, counts, engaged: **6–9 Hz 22.0 @50–65 km/h, 8.2 @85–115 · 22–26 Hz 6.2 / 5.3 · control
32–38 Hz 3.1 / 3.6.** **Stock's whole 2–50 Hz engaged spectrum outside the road band sits at 3–15
counts.** V101's 22–26 Hz at 50–65 is **362** — 48–58× that.

## 🛑 HANDS-ON IS A MANDATORY THIRD MATCHING AXIS
Hands-on windows carry **~2.7×** the 6–9 Hz content, and arms differ hugely: **stock 15.3 % · V100 12.9 %
· V101 40.3 % · V102 4.7 %.** Speed × rate matching does **not** remove it. Re-matched hands-off, V102's
22–26 Hz excess over stock is **1.56×, not 2.94×**, and **V100 (4×) is statistically indistinguishable
from stock in every band except 6–9 Hz.** **The control band collapsing from 1.29× to 1.06× is the tell.**
✅ **`Re(Z)` is unaffected** — its mask is frame-level hands-off by construction.
🛑 **V101 cannot be placed on the matched grid at all** (2 pure hands-off, 3 pure hands-on of 103) ⇒
**every V101 contrast in this kit's record carries an unpriced behavioural confound.**

## 🛑 THE CHEAPEST OPEN QUESTION IN THE KIT
**Engaged-vs-manual 6–9 Hz on stock is UNSCOREABLE** — stock's manual driving is 240/278 windows at
0–5 km/h and **zero above 20 km/h**. One matched cell gives 2.16× [0.41, 4.69], contrast +0.305 against
the record's +0.413 [+0.146,+0.667] — consistent, but the CI spans 11×.
⇒ **CLOSES WITH ~3–5 MINUTES DRIVEN MANUALLY, LKAS OFF, AT 50–110 km/h.** It decides whether the
command-proportional Coulomb relay is **Honda's or ours**, and it needs no build and no flash.

See [[accord-f0-crossover-is-the-endpoint]], [[accord-rez-antidamping-replicated-three-drives]],
[[accord-engagement-amplifies-6-9hz]], [[accord-ratchet-is-a-lightly-damped-resonance]].
