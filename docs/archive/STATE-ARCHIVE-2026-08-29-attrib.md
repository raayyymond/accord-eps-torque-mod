# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔ **`0xC63AE` IS NOT A CLEAN LOOP-GAIN LEVER EITHER — SAME TRAP, DIFFERENT CELL**
The stability work suggested one more candidate, and it fails the rule written two ticks ago.

`FUN_00038148` computes `uVar7 = |iVar6| * cal(0xC63AE) >> 10` **before** the LERP, so `0xC63AE`
(**virgin, 1024 on all 142 images**) scales the **whole Path-2 forward path**. Unlike a per-term
weight it preserves the observer's relative weighting, so it looked like the clean loop-gain
reduction — and one that needs no V158 base.

⛔ **But `gp-0x6ad6` is the PID's FEEDBACK term, not a gain node:**
```
   uVar19 = *(short*)(gp-0x6ad6)              <- data read
   uVar24 = clamp(uVar19, +-cal 0xC6200)
   iVar30 = gp-0x4f60 - uVar24                <- THE ERROR
```
=> shrinking it **moves a SUBTRACTION**: `err = measured - feedback`, so a smaller feedback gives a
**LARGER** error and a **LARGER** PID output. The loop-gain reduction and the error growth push
**opposite ways**, and which wins depends on the same unknown `s`. **Net ambiguous => not built.**

⭐ **This is the rule from two ticks ago applied to myself**: *before lowering a scalar, ask what the
sum is FOR.* In an aggregator a scalar is a **gain**; here it feeds a **subtraction**, so it sets an
**operating point**. The observer-weight trap and this one are the same trap wearing a different cell.
⊕ **Path 2 now has no clean cal lever at all**: the per-term weights corrupt the model, and the
output scale moves an operating point. `0xC63A0` remains the sole exception, and only because
`gp-0x6bd0` was exactly 0 at creep before V158.

