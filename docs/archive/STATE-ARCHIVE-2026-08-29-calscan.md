# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **THE “UNRESOLVED HOP” IS CLOSED — AND V158's PATH-2 RISK IS NOW BOUNDED AT ~20 %**
The model's longest-standing open item on this chain (*“there is AT LEAST ONE UNRESOLVED HOP here…
gp-0x6b94's 4 unchecked readers … [OPEN]”*) resolves by triaging those four on what they **write**:
```
   FUN_00036bec   gp-0x6b48 = EMA(gp-0x6b94 x 64, cal tp+0x73d8) >> 6    SECONDARY -- feeds the
                                                                        backlash fn FUN_00036828
   FUN_0004503c   writes gp-0x6ace                                       *** THE GOVERNOR -- the hop ***
   FUN_0004595a   gp-0x6aca / gp-0x68c8..ce / gp-0x6d9c                   not the chain
   FUN_0007ff08   gp-0x4e62 / gp-0x4e3e / gp-0x2e10 / gp-0x2df6           not the chain
```
✅ **`FUN_0004503c` writing `gp-0x6ace` matches the byte-verified bridge already in memory**:
`gp-0x6b94 → governor → gp-0x6ace → comp-add → gp-0x6acc → shaper → gp-0x6b08 → gp-0x6b98 → FOC`.
=> **the model's note is STALE; memory had the answer.** ⊕ A second consumer is new: `gp-0x6b94` also
drives the **backlash** function through `gp-0x6b48`, which the model did not record.

### ⭐ THE CONSEQUENCE: PATH 2 DOES NOT REACH THE MOTOR INDEPENDENTLY
It feeds `gp-0x6ad4` **back into the SAME aggregator**, so **both routes exit through `gp-0x6b94`** and
can be compared directly:
```
   PATH 1 (direct)   gp-0x6bd0 -> FUN_0003aa2c -> gp-0x6b94                        gain 1.000
   PATH 2 (loop)     x w(0xC63A0)=1.0 · x pol(-1) · x double 9.6 Hz EMA (0.615)
                     x RAM-LERP slope s · err = 6b98-src - gp-0x6ad6 (-1)
                     x PID (64>>5 = 2) x ceiling 170/1024 (0.332) · x pol(-1)
                     -> gp-0x6ad4 -> the SAME aggregator -> gp-0x6b94        gain 0.204 x s
```
⚠ **[BELIEF] net sign** `(+1)(−1)(−1)(−1) = −1` ⇒ **opposite to Path 1 ⇒ pumping.** Hand-traced
through three inversions; not verified end-to-end, and note the model's claim is about the sign
*inside* Path 2, not the net at the aggregator.
✅ **[EVIDENCE] net magnitude 0.204 × s** ⇒ **Path 1 dominates unless the RAM-LERP local slope
s > 4.9.** That LERP is a **bounded shaping curve, not a gain stage**, so s > 4.9 is implausible.

### ✅ WHERE THIS LEAVES V158
**The named risk is now BOUNDED at roughly 20 % of the damping it buys**, not merely "unresolved".
Path 1 damping should dominate by ~5x. Combined with V74 having flown this dose fault-free and the
model having prescribed the edit knowing the architecture, **V158's risk profile is materially better
than it looked two ticks ago — and I should say so as plainly as I stated the risk.**
⊕ **V167 remains the right “worse” branch** — if the drive is worse anyway, halving `0xC63A0` is the
one edit that tests this bound directly, because it halves exactly the 0.204 term.
⚠ **[OPEN] the RAM-LERP slope `s`** is the last unknown. Closing it needs the `gp-0x64b8`/`gp-0x641c`
rows, which are built by `FUN_000389ec` from `FUN_000382d8`'s tables — the model records two failed
attempts at exactly this extraction.

