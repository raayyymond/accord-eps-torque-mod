# STATE archive 2026-08-28 — sections superseded during the Lever B iteration

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **RECONCILIATION — I HAVE BEEN SEARCHING A SPACE THE KIT ALREADY CLOSED**
`accord-ratchet-is-a-lightly-damped-resonance` is a **PROMOTED ★★★★★ memory** and it says, in its own
description: *"the firmware search on it is CLOSED."* Re-reading it in full against my last several
turns changes the ranking, and one of my own claims does not survive.

### ✅ WHAT THAT MEMORY ESTABLISHED — three methods, each past its own control
```
   Q 14-29, zeta 0.017-0.036   ring-down, the ONLY estimator that passes a control (r = +0.937)
   LIMIT CYCLE EXCLUDED        Welch ladder: car 20.9 vs pure tone 53.8, bursty AM 52.1-52.5
   NOT rim-side                |T/Omega| rises smoothly THROUGH the line; car 1.30x vs Q=10 -> 3.40x
   frequency tracks LOAD       +0.467 Hz over a 17.8x column-torque range at FIXED speed
   d log f / d log A = -0.034  kills rate-limit, backlash and classic stick-slip
   ENGAGEMENT SUPPLIES IT      0 of 97 fully-manual windows carry a line; engaged/manual 11.7-13.4x
```
🛑 **The closure is a SHAPE argument**: every gain-bearing element on the torque path is either a
**flat Q10 scalar** (which would lift the 26–31 and 32–38 Hz control bands too — they went *down*,
0.61–0.76) or a **differentiator** (favours HF, wrong direction). A band-limited lift at 6–9 Hz needs
a **resonant/biquad structure, and none exists in the chain.** It also states outright:
**"a 2-pole EMA has DC gain exactly 1 so no EMA can be the amplifier."**

### 🛑🛑 **MY "PREMISE SUPPORTED" CLAIM DOES NOT SURVIVE — RETRACTED**
Two turns ago I measured `gp-0x6b70`'s 6–9 Hz share at **8.7 % / 10.2 % engaged vs 6.6 % / 7.4 %
manual** and called V152/V153's premise *supported*, comparing against a **flat baseline**.
**That was the wrong comparator.** The symptom's own engagement contrast is **11.7–13.4×**.
```
   the SYMPTOM, engaged/manual band power      11.7 - 13.4 x
   gp-0x6b70,  engaged/manual 6-9 Hz share      1.32 -  1.38 x
```
⇒ **a carrier must show the carried signature. `gp-0x6b70` shows ~1.3× where the symptom shows
~12×** — and a Q 14–29 resonance cannot turn a 1.3× excitation change into a 12× output change.
⇒ **[RETRACTED] `gp-0x6b70` is NOT the carrier of the symptom.** The loop passes the band, which is
all my measurement showed; passing a band is not carrying a symptom.

### ⭐ THE ONE THING THE CLOSURE DOES **NOT** EXCLUDE — AND V152/V153 ARE EXACTLY IT
`memory/MEMORY.md` attaches this caveat to that very memory, and it is the whole opening:
> ⚠ *Its "no biquad ⇒ firmware search CLOSED" argument does **NOT exclude a loop pole**.*

⇒ **the shape argument excludes AMPLIFIERS; it does not exclude POLES.** A pole changes **phase**,
which changes how much the loop **re-excites** a mode that rings for ~Q ≈ 20 cycles (≈ 2.5 s at
7.8 Hz) after every kick.
⇒ **`0xC63AC` was V97 — recorded as *"the arc's FIRST loop-POLE lever"*.** **V152/V153 move that
same pole AND its byte-exact twin `0xC40D0`, matched, in the LOWERING direction.**
✅ **So V152/V153 sit in the ONE slot the kit's own closure leaves open** — not as carrier
attenuators (retracted above) but as **loop-pole/phase levers**. **That is a better justification
than the one I gave them, and it survives the shape argument.**
⚠ V97 moved `0xC63AC` **alone and UPWARD** and read **UNINTERPRETABLE**. V152/V153 move **both,
matched, downward** — a different move, and the only one that never breaks the arm-match.

### 🛑 HOW THE OTHER BUILDS FARE AGAINST THE SHAPE ARGUMENT
```
   V152/V153  loop POLES, matched          <- the ONE class the closure leaves open   SURVIVES
   V149       a SWITCH (5.12x step)        shape argument covers gains, not switches  SURVIVES
   V139       the r24/r26 PUMP arms        a pump is not a flat scalar in effect      SURVIVES
   V155/V154  inertia-lane WEIGHT          a flat Q10 scalar -- BUT on an omega^2 lane,
                                           so its EFFECT is frequency-shaped         PARTLY
   V151       the knee                     relay already ~99 % unsaturated            WEAK
```
⇒ **[DECISION] V153 stays first, for the loop-pole reason, not the transmission reason.**
⇒ **And the honest frame for the operator: the mode is MOTOR/RACK/TYRE side and no channel on this
bus observes it.** Firmware cannot remove a mechanical resonance — it can only change what excites
it and the phase with which the loop feeds it. **Every remaining build is an excitation or phase
lever. None of them can "eliminate" a mechanical mode**, and the record should say so.

## 🛑 **THE ADMISSION-GATE CLASS — HALF CLOSED FROM THE RECORD, AND V154/V155 DEMOTED**
Last turn I flagged the lane admission gates as a **third switching class** and called measuring
their duty *"the cheap next probe."* **Three of the six were already measured.** The kit's own rule
— *search the record before naming a cause* — applied to my own proposal.
```
   lane        gate     recorded magnitude                              gate trips?
   gp-0x6b26   +-1024   p50 5.5 / p90 39.1 / p99 114.3 / MAX 319.1      NO -- 3.2x margin
                        (+-511 clamp upstream, clamp duty 0.000000)
   gp-0x6b4c  +-10240   V101 b6: |gp-0x6b4c| >= 4096 duty 0.000000      NO -- 2.5x margin
   gp-0x6bbe   +-2048   p50 73.6 ct, flat across 0-6 deg/s              NO (large margin)
   gp-0x6b4e  +-10240   disjoint partition twin of gp-0x6b4c            NOT MEASURED
   gp-0x6b46   +-1024   unmapped lane                                   NOT MEASURED
   gp-0x6bd0   +-2048   the damper                                      NOT MEASURED
```
⇒ **[EVIDENCE] no gate that has ever been measured has EVER tripped.** For `gp-0x6b26` the gate is
**unreachable by construction** — an upstream `±cal(0xC407E)` = **±511** clamp binds first, and the
admission gate sits at **±1024**. ⇒ **the admission-gate class is NOT the ratchet's source on any
lane the kit has instrumented**, and only three lanes remain open.

### 🛑🛑 **AND IT DEMOTES MY OWN BUILD — V154/V155 ARE SMALLER THAN I RANKED THEM**
The same measurement that closes the gate also **sizes the lane**:
```
   gp-0x6b26 MAX 319.1        vs  gp-0x6b4c < 4096 (measured)      =>  <= ~8 % of the sum AT ITS MAX
   gp-0x6b26 p50 5.5                                               =>  a few tenths of a % typically
```
⇒ **halving this weight moves `sum6` by a few percent at most.** The ω² argument still holds — its
**share at 7.8 Hz is higher** than its share over all frames — but it starts from a **small base**,
and that share has **never been measured**.
⇒ **[CORRECTION to my own ranking last turn] V154/V155 drop BELOW V152. The mechanism is still the
cleanest in the kit — pure gain, no phase cancellation, zero DC cost — but the expected magnitude is
SMALL.** I ranked them second on mechanism quality without sizing the lane. **Sizing came first and
I skipped it.**
✅ **They remain SAFE on the one axis that matters**: `FUN_00036c12` carries an **int32 WRAPAROUND**
(`mul r13,r6,r0`, ×0x111, high half discarded, **unclamped and UPSTREAM of `0xC407E`**) that binds
at ≈**1.6005×** the present level and would deliver a **full-scale SIGN INVERSION**. **V154/V155
REDUCE the lane, moving AWAY from it.** Any build that RAISES `gp-0x6b26` moves toward it.

### ⭐ WHY THE OTHER LANES ARE NOT SELECTIVE LEVERS
**`gp-0x6b4c` and `gp-0x6b4e` are the DISJOINT PARTITION SUMS of the same 11-slot request array**
`gp-0x62c8[]`, split by the mode bytes — i.e. **they carry the assist request itself.** They are the
dominant terms and they carry **DC**, so cutting their weights (`0xC63AA`/`0xC63A8`) would reduce
authority broadly rather than selectively. **Not selective levers.**
⇒ **the inertia lane is the ONLY frequency-selective lane in the observer sum**, which is why it was
worth building even at a small expected magnitude.

### ✅ THE HONEST RE-RANKING
```
   1. V153   observer corner /4, BOTH arms matched   1.95x less at 7.8 Hz, no DC cost, CERTAIN   3 B
   2. V152   the same lever at /2                    1.26x less, conservative                    3 B
   3. V149   removes the 5.12x r24 switch            bigger IF it fires; may be INERT            2 B
   4. V139   both pump arms halved                   demonstrated on-car potency                 2 B
   5. V155   inertia lane /4     cleanest mechanism, SMALL magnitude (lane <= ~8 % of the sum)   1 B
   6. V154   inertia lane /2                                                                     1 B
   7. V150   r26 suppression switch removed          can only suppress the pump                  1 B
   8. V148   deadband + probe                        MEASURES whether gp-0x671d toggles          3 B
   9. V151   knee 3000 -> 3600                       MARGINAL, costs 17 % of the term            2 B
```
⇒ **V153 stays first**: it acts on the WHOLE residual path rather than one small lane, it is
**certain to act** (the EMA runs every 1 kHz tick), its reduction is **quantified**, and it costs
**nothing at DC**.


---

🛑 **1 older section(s) moved to `docs/archive/STATE-ARCHIVE-2026-08-28.md`** to hold this file under the 145 KB target.
