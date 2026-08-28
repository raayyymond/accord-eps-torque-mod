---
name: accord-antidamping-is-a-state-effect-of-engaging
description: "The engaged Re(Z) deficit is nearly COMMAND-INDEPENDENT: at |cmd| < 512 it is -59/-60/-67 at 9-12 Hz against a MANUAL +7, essentially as deep as at high command. Engaging alone flips the sign. That rules out the relay, the 6x gain and every command-proportional lane. Separately, the gp-0x6b26 damping lane is EXHAUSTED as a lever: its feasible ceiling is +241 counts against a -2464 deficit (9.8%), because int16 caps the mode-26/27 Y row at x1.111."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE ANTI-DAMPING IS A **STATE EFFECT OF ENGAGING**, NOT A COMMAND EFFECT

2026-08-27, routes 21 (V111) + 22, 23 (V112). `Re(Z) = Re(H1[rate → column torque])`, engaged
split by command magnitude, hands low-torque, moving.

```
  route      arm            2-4   4-6   6-9  9-12 12-16 16-20 20-24
   r21   MANUAL               3     6     7     7     7     8    11
   r21   ENG |cmd| < 512    -17   -18   -32   -59   -51   -18    -4
   r21   ENG |cmd| >= 512     3    -4   -42   -52   -29   -13    -5
   r22   MANUAL               4     5     6     7     9     7    10
   r22   ENG |cmd| < 512     -2    -2   -23   -60   -51   -14    -3
   r22   ENG |cmd| >= 512     0     1   -30   -41   -18   -11    -3
   r23   ENG |cmd| < 512     -2   -13   -32   -67   -54   -17    -2
   r23   ENG |cmd| >= 512     0    -8   -67   -69   -43   -12    -4
```
🛑 **At `|cmd| < 512` the deficit is already −59 / −60 / −67 at 9–12 Hz, against a MANUAL +7.**
**Engaging alone flips the sign, with essentially no command present.**

## WHAT THIS RULES OUT
- the **Coulomb relay** (`0xC40BC`/`0xC40D2`) — command-proportional by construction
- the **6× gain** (`0xC6CD0`) — it scales the command
- **every command-proportional lane**, including the ones the kit has been dosing since V80
⇒ **the culprit is something engagement switches ON as a STATE.**

## ⭐ THE PRIME SUSPECT — THE MODE INDEX
`gp+0x63fd` changes **24 → 26/27 on engagement** (V73 probed it over 104,061 frames: 8 manual /
10 engaged values, 18 transitions, all on engagement edges). That index re-selects an **entire
family of calibration records**, not one cell.
🛑 **And in STOCK, mode 24 ≡ mode 26 byte-identical across all six factor families**
([[accord-stock-mode24-equals-mode26-damper-is-ours]]) — **Honda's engaged and manual surfaces are
the same. Every difference between them is OURS.** ⇒ the engaged-minus-manual `Re(Z)` gap is a
candidate readout of the *sum of the kit's own mode-26/27-only edits*.
⚠ **NOT yet verified**, and one part cuts the other way: the `gp-0x6b26` **damper** is 3× larger on
mode 26/27 than on 24 (Y −29490 vs −9830, V106), which should make ENGAGED *more* damped, not less.
So the mode story cannot be the whole account. **Open.**

## 🛑🛑 AND THE `gp-0x6b26` LANE IS **EXHAUSTED** AS A LEVER
Maximising 6–16 Hz damping subject to *mass ≤ V112* and *peak |H| ≤ V112* (the anti-rail constraint
V107 violated):
```
   config                6-16Hz damping   mass   peak|H|
   V112  (a2 14, Yx1)         1.000       1.000   1.000
   V115  (a2  8, Yx1)         1.252       0.796   0.669
   best feasible (a2 5, Yx1.111) 1.466    0.606   0.508
```
`gp-0x6b26`'s own measured contribution is **+518 to +565 counts/rad/s** at 6–9 Hz (the V94 flight),
against a measured deficit of **−43 per °/s = −2464 per rad/s**:
```
   V115           +131 counts  =  5.3 % of the deficit
   best feasible  +241 counts  =  9.8 % of the deficit
```
🛑 **To close the deficit this lane would need ×5.8. int16 caps the mode-26/27 Y row at ×1.111**
(it already sits at **−29490 of 32767**). ⇒ **V115 will REDUCE the peak-turn oscillation, not
eliminate it. Say so; do not oversell it.**
⊕ **Do not raise the Y row for the last ×1.111**: it buys +2.4 % of the deficit and puts Y[0] at
−32763, four counts from the int16 edge, in the cell that produced V94 (unsafe to drive) and V107
(railed).

## ⇒ WHAT THIS MEANS FOR THE PROGRAMME
The remaining oscillation **cannot be fixed by dosing any lane the kit currently doses.** The next
real step is to **identify what engagement switches on that removes ~2464 counts of Re(Z) at
6–12 Hz**, starting from the mode-index family and the engage state machine.
🛑 **This supersedes "add more damping" as the strategy.**

Related: [[accord-antidamping-is-centred-at-9-12hz-not-20-30]] ·
[[accord-the-oscillation-is-not-command-driven]] ·
[[accord-v112-flew-best-yet-and-the-peak-turn-oscillation]]
