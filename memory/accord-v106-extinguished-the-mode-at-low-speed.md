---
name: accord-v106-extinguished-the-mode-at-low-speed
description: "V106 (gp-0x6b26 Y row x3.0 stock, engaged modes only) FLEW as route a6 and EXTINGUISHED the 21-27 Hz mode at low speed - prominence 1.51 vs stock's 1.46, argmax following the band edge exactly as stock's does. The 18-30 ratio is the FIRST band-power result in this kit's history to clear its own within-drive split-half null. RULE 7 closed: the car reads modes 26/27 engaged."
metadata:
  type: project
---

# 🛑🛑★★★★★ V106 EXTINGUISHED THE MODE AT LOW SPEED — AND RULE 7 IS CLOSED

2026-08-23, route `a6`. **1,224.0 s engaged (2.5× any prior drive), fault-free.**

## THE RESULT
Engaged, <16 km/h, max-demand arm (|e4tq| ≥ 1600):
```
             peak Hz  PROMINENCE  18-30 RMS   argmax vs search-band edge
STOCK 1x      18.23      1.46       0.3121    follows the edge  <- no line
V104 6x       22.23      6.89       7.6624    pinned            <- a real line
V105 notch    20.48      3.42       5.6967    pinned            <- a real line
V106          18.23      1.51       3.7255    follows the edge  <- NO LINE
```
**Two independent within-spectrum signatures of no line: stock-level prominence, AND an argmax that
wanders with the search window instead of staying pinned.**

⭐ **FIRST BAND-POWER RESULT IN THIS KIT'S HISTORY TO CLEAR ITS OWN WITHIN-DRIVE NULL.**
`18-30 a6/V105 = 0.347` against a6's own split-half null `[0.482, 1.982]`. a5's null spanned
0.26–3.8; a6's is tight because of the exposure. **Positive control `a6/STOCK = 5.735` — the
instrument had not gone dead.**

🛑 **THE CONFOUND THAT WAS CUT.** a6's engaged command is ~4× SMALLER than a5's (|e4tq| p90 791 vs
3341) and the mode is command-driven, so "the band collapsed" was equally consistent with
"openpilot didn't push". Re-run in cells of (speed) × (**absolute** |e4tq|) over 7–8 matched cells,
it survives. **Always cut this confound; it is available on every future drive.**

## RULE 7 IS CLOSED — the car DOES read modes 26/27 engaged
🛑 A **pooled** `b5` duty is the WRONG estimator: `gp-0x6b26 = K·α` where α is what K damps, so in a
stable closed loop **the product is invariant to K** (V91/V92 measured 0.99). A pooled null is
ambiguous between "no dose" and "dose worked". **Condition on measured α** and the ambiguity
disappears — at fixed α the comparator's operand B is proportional to k.
```
b5 duty at matched alpha:  a6/a5 ratio  0.716 0.603 0.534 0.552 0.605 0.643 0.711 0.555
                           8/8 bins below 1, sign p = 0.0039
within-drive:  engaged 0.1907  vs  MANUAL 0.4509 = -0.2602   (a5: +0.1031)
```
⇒ **Every earlier `0xCBE74`-family result becomes interpretable; the V91/V92 mode-record suspicion
is CLEARED.** And the ×1.5 WAS in force: delivered multiplier **1.68× [1.16, 1.88]**, excluding
both 1.00 and 3.00.

## WHAT SURVIVES — and it is a HIGH-SPEED phenomenon
Prominence by regime (stock in parentheses): low 12.5→4.2→**2.0** (2.5) · mid 4.3→5.9→**3.2** (2.4)
· hwy 40–95 13.3→24.0→**6.5** (1.3) · **hwy-matched 55–70 6.1→5.1→1.4 (1.6) = AT STOCK**.
Since 55–70 is at stock and a6's 40–95 exposure is dominated by >70 (778 s vs 224 s), **the 6.5 is
carried by the >70 portion.** That is exactly where Honda's speed taper makes the dose 4.2× weaker.

## THE RATE COST IS AN ACCELERATION PENALTY, NOT A SLEW CEILING [3 lines]
No rail (a6 is the LEAST piled-up of four builds at p99.9) · steady state restored to V104's level
(`H(0)=0` predicts this) · **wheel acceleration down 2–4×**. At matched ABSOLUTE max demand,
achieved rate p90: V88 326 · V104 166 · V105 229 · **V106 157** ⇒ **~30 % of peak rate given up vs
V105.** A finite manoeuvre pays; it does not pay as a ceiling.

## ⊕ THE RATCHET IS LKAS-DEMAND-DRIVEN — a NEW discriminator
The 7.4–8.6 Hz LINE is **the only band with a POSITIVE residual demand association after partialling
out motor rate** (+0.1139 [+0.0374,+0.2548]); carrier and placebo both go NEGATIVE. 2/2 rate strata,
both CIs excluding 1, placebo flat. **Demand effect, not the historical rate effect.**

Related: [[accord-uniform-dose-axis-exhausted-schedule-is-the-lever]] · [[accord-v107-built-reshape-b-and-tap]] ·
[[accord-three-grinds-are-one-frequency]] · [[feedback-design-the-statistic-inside-a-drive]]
