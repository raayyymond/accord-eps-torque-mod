# STATE archive — superseded during the slope-cap GATE 2 work

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **UN-RETRACTED AND BUILT — V159 REMOVES AN 18 % PARAMETRIC MODULATION OF K_p AT 2f**
🛑 **I over-corrected last turn.** The "parametric pump" finding was **retracted in error**;
decompiling `FUN_0003a382` proves the original layout reading was right.
```c
   X[0] = tp+0x7b1e   X[last] = tp+0x7b24    =>  X is 4 halfwords at 0xC671E
   Y[0] = tp+0x7b26   Y[last] = tp+0x7b2c    =>  Y is 4 halfwords at 0xC6726
   X = [96, 104, 608, 704]        Y = [704, 832, 832, 832]
```
⇒ exactly the "X at base, Y at base+8" layout I first assumed. **The retraction is withdrawn.**
⊕ **What went wrong**: lanes B/C read non-ascending X under the same layout, and I let that anomaly
override **direct instruction evidence** for lane A. **A neighbouring record being unreadable is not
evidence against a record whose layout the decompile confirms line by line.**

### ⭐ THE MECHANISM, CONFIRMED
`FUN_0003a382` is a three-term torque-tracking servo whose **K_p is a LERP on `gp-0x6ac0`, the
RECTIFIED motor rate.** The golden model's **measured** in-burst operating point is
**`gp-0x6ac0` = 99 [94, 113]**, which lies **inside the FIRST segment (X 96 -> 104)** where Y rises
**704 -> 832 = an 18.2 % swing across 8 counts.**
⇒ and a **rectified** index sweeps at **2f**, so during a 7.8 Hz ratchet it traverses that window at
**15.6 Hz**.
⇒ **[EVIDENCE] the PID's proportional gain is PARAMETRICALLY MODULATED ~18 % at 2f at the symptom's
own operating point — STRUCTURALLY, on STOCK.**
⊕ This is the qualitative prediction the golden model made and never located, and a **named
candidate source** for [[accord-v59-parametric-pump-marginal]] (*"the pump is real but MARGINAL"*).

### ✅ V159 — ONE HALFWORD
```
   0xC6728  K_p Y[1]  832 -> 704        Y = [704, 704, 832, 832]
   2 payload bytes, 54/54, CRC 50/50
   image 47ac7932a16334d1a7719e2d0efdd955eef3cc2ab841b7bbb7d6813872389916
   rwd   7c51b28bddba3acfa129cd7a4c0e19efaad8f52ce3928332a66c7b6ccd0f5080
```
✅ **segment 0 becomes FLAT** ⇒ the 2f sweep sees **no gain change**: swing **18.2 % -> 0.0 %**.
✅ **DOWNWARD**: it **lowers** K_p between 96 and 104, so no clamp becomes newly reachable.
✅ **MONOTONE preserved** — the ramp is not deleted, it **moves to X 104..608**, the same 704->832
rise over a **63x wider span**.
✅ **RULE 7 SATISFIED BY STRUCTURE**: the decompile reads this table with **bare `tp` displacements
and NO index register** ⇒ a **flat scalar table shared by all modes**. There is no mode to get wrong.
✅ **VIRGIN**: `0xC6728` = 832 on **all 158 build images**.

### ⚠ WHAT IS NOT ESTABLISHED
⚠ **[BELIEF]** that removing an 18 % parametric modulation is audible. **The mechanism and its
magnitude are EVIDENCE; its share of the symptom is not.**
⚠ **[OPEN]** lanes B (`tp+0x7b0a`) and C (`tp+0x7ade`) read **non-ascending X** under the confirmed
layout (`[256,256,0,8]`, `[717,0,0,5]`). Unexplained, and **left open** — it does not bear on lane A.
⚠ **V159 does NOT close V158's shared-axis GATE 2.** It addresses the **PID side** of that coupling,
not the FactorE side. **V158 and V159 are INDEPENDENT single-lever builds — do not stack them.**

### ✅ THE QUEUE
```
   V158   damper, the golden model's own prescription      shared-axis GATE 2 still OPEN
   V159   K_p 2f modulation removed                        RULE 7 satisfied, virgin, monotone, down
   V148 / V150 / V151                                      probe / grind-#2 / marginal
   V152 / V153                                             GATE-2-OPEN, demoted
   SUPERSEDED  V139 V149 V154 V155 V156 V157
```
⭐ **V159 is the first build of this session derived from a mechanism located in the firmware rather
than from a lever list**, and the only one whose RULE 7 is satisfied *by the instruction encoding*
rather than by a mode table.

