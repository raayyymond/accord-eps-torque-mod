# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **THE STATIC SEARCH IS NOW COMPLETE — EVERY LANE IN THE AGGREGATOR IS ADJUDICATED**
```
   lane / cal              phase or structure at 7.8 Hz            verdict
   r24  (Lever B 0xC6446)  K x d(torque)/dt, +90 deg               DAMPS -- at 6553 = int16 ceiling (V160)
   gp-0x6bd0 (V158)        -sign(rate) x f(|rate|), f near-linear   DAMPS -- dose 50, model's own [30,60]
   r26  (0xC6444)          same class as r24                       FALSIFIED -- flew as V71c, worse
   gp-0x6ad4               P 99.88 % @ -1.7 deg, D 0.02 %          STIFFNESS -- structurally eliminated
   gp-0x6b26               -K x acceleration                       ADDED INERTIA -- does not damp
   gp-0x6bbe               measured viscous, 1.571 ct/(deg/s)      already live; raising = more assist
   gp-0x6b46 / 0xC63D2     slow trim, |H| 0.119, 81.8 deg lag      NOT a lever either direction
   backlash band 0xC61A0   floor 123 ct, virgin                    CLOSED by limit-cycle exclusion
   gp-0x6b62 return-centre DEAD engaged (0.0000 / 75,227 frames)   inert
   gp-0x6ade               0 writers image-wide                    dead
   gp-0x6b4c LKAS          command lane                            EXCLUDED (a DC constant carries no 7.8 Hz)
```
=> **V160 carries the only two lanes that actually damp, each at or at the model's stated limit.**
✅ **[EVIDENCE] this is an exhaustive adjudication of the aggregator, not a survey** — every lane the
model lists now has a phase or a structural verdict.

### ⚠ WHAT THIS MEANS, STATED PLAINLY
Further progress is **measurement-limited, not analysis-limited.** The instrumented engaged-vs-manual
contrast collapses to **~1.1x** under controls (≤10 % of the 6–9 Hz band, ≤2 % of RMS as a 7.8 Hz line),
yet V88 demonstrably changed the felt symptom — **so the bus instrument is the weak link, not the
firmware model.** The next real information comes from a creep drive **with audio**, which is the one
input static analysis cannot supply.

