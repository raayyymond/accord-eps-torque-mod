# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔⛔ **TWO LEVERS CLOSED — r26's ARM AND THE FUN_00036682 FILTER POLE**
Both were about to be built. Both are negatives, recorded so they are never re-proposed.

### ⛔ 1. `0xC6444` (r26's LKAS-gated arm) — FALSIFIED, AND THE FALSIFICATION IS VALID
The golden model **strikes** this cell on the grounds that it *"is reachable only on a build whose
control path is already ruled out"*. **That premise is stale** — the repointed control path
(`0x3AA96 = 0xfb`) is exactly what has been flying since V88, so the cell IS reachable now:
```
   build  0x3AA96        r26 0xC6444   r24 0xC6446   reachable?
   71a    0xc5 (stock)         512          512      NO -- gp-0x683c has 0 writers
   71b    0xc5 (stock)         512          512      NO
   71c    0xfb (repointed)    3072         5244      YES  <-- IT WAS GENUINELY TESTED
   88     0xfb                 512         5244      YES
   122    0xfb                 512         5244      YES
   160    0xfb                 512         6553      YES
```
✅ **[EVIDENCE] V71c carried the REPOINTED gate, so `0xC6444 = 3072` really was read on-car.** The
falsification is **NOT void** — and memory records the **6x cut back to 512 as LOAD-BEARING**, i.e.
raising r26 was **WORSE** and cutting it was part of what made V88 good.
=> **raising r26 is the wrong direction, already flown.** I was one step from re-flying V71c.
⭐ The lineage check earned its keep again: the model's *strike* and the *reason* for the strike can
both be stale while the underlying verdict still stands. **Re-derive the reachability, then trust the
flight result.**

### ⛔ 2. `0xC63D2` — FUN_00036682's FILTER POLE IS A SLOW TRIM, NOT A RATCHET LEVER
`FUN_00036682` is a **backlash/hysteresis band followed by a one-pole low-pass**, writing `gp-0x6b46`
— both an aggregator lane and one of the six lanes EMA'd into ACTUAL:
```
   iVar8   = clamp(residual - ((lower + upper) >> 1), ±512)      backlash band
   iVar14 += ((iVar8*1024 - iVar14) * cal 0xC63D2) >> 10         one-pole IIR
   gp-0x6b46 = iVar14 >> 10
```
```
   0xC63D2 = 6  =>  a = 0.005859  =>  CORNER 0.93 Hz
      f      |H|      lag            raising the pole to cut the lag:
     2.0   0.4236   64.6 deg           cal   6  fc  0.93 Hz  |H| 0.119  lag 81.8 deg
     7.8   0.1191   81.8 deg           cal 128  fc 19.89 Hz  |H| 0.939  lag 18.8 deg
    21.0   0.0445   83.7 deg           cal 512  fc 79.58 Hz  |H| 0.998  lag  2.8 deg
```
⚠ **The lag looks damning (81.8°) but the MAGNITUDE is 0.119** — the lane is attenuated **8x** at the
ratchet. It is a **deliberately slow trim term** (0.93 Hz), separated from the fast dynamics by design.
⛔ **Raising the pole to cut lag would raise this lagging lane's gain 8x at 7.8 Hz — EXACTLY the V162
error** (more gain, no useful phase, into a Q 14–29 resonance). Lowering it changes almost nothing
(lag already asymptotic to 90°, magnitude already small). **Not a lever in either direction.**
⊕ History: `0xC63D2` = 6 on 154 images, 3 on nine (V124/125/127/129/131/133–136) — all inside the
8x-gain/regression cluster, i.e. never a clean test, and 3 makes the lane *less* present, not more.
⊕ **The BACKLASH element itself remains structurally interesting** — a hysteresis nonlinearity is the
textbook small-amplitude ratchet generator — **but it sits BEFORE the low-pass**, so whatever it
injects at 7.8 Hz is attenuated to 12 % before reaching the aggregator. **[OPEN]** its half-width is
`(gp-0x6b44 * uVar7) >> 15` with `gp-0x6b44` a computed RAM cell, not a cal, so there is no direct
calibration lever on the band width. What would close it: identify `gp-0x6b44`'s writer.

### ✅ THE DAMPING LEVERS ARE NOW GENUINELY EXHAUSTED WITHIN THE MODEL'S CONSTRAINTS
```
   r24  (Lever B 0xC6446)   at 6553 = the int16 ceiling in V160         EXHAUSTED
   gp-0x6bd0 (V158)         dose 50, inside the model's own ~43 [30,60] AT PRESCRIPTION
   r26  (0xC6444)           raising it FLEW as V71c and was worse       FALSIFIED
   gp-0x6ad4                stiffness, D path ~1300x too weak, u16-bound STRUCTURALLY ELIMINATED
   gp-0x6b26                -K x acceleration = added inertia            DOES NOT DAMP
   0xC63D2                  slow trim, |H| 0.119 at 7.8 Hz               NOT A LEVER
```
=> **V160 carries both mechanisms that actually damp, each at or at the model's stated limit.**

