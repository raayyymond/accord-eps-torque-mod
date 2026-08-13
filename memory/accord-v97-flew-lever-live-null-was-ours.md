---
name: accord-v97-flew-lever-live-null-was-ours
description: "V97 (0xC63AC 102->150) flew route 0x80; the operator felt NOTHING and stopped. Both of his hypotheses — wrong address, dead code — are REFUTED: the guard on FUN_00038148 is BYTE-IDENTICAL to the assist-mixer's (a shut gate = no power assist at all) and sign(gp-0x374c) toggled 181x in 109 s. The null is on the EXPERIMENT — no instrument, 1 episode, and DC gain 1.000 means no amplitude statistic could ever see it. Filed UNINTERPRETABLE, NOT falsified. Do not re-dose."
metadata:
  type: project
---

# ★★★★★ V97 FLEW — THE LEVER WAS LIVE, THE NULL WAS OURS

**Route `0x80`, 2026-08-12, fault-free.** 109.2 s · **17.2 s engaged, ONE episode** · engaged p50
**5.13 km/h**, v_max 6.6 · **19.5 % override / 80.5 % hands-off**. A deliberate parking-lot creep.

> *"I did not feel any difference in grinding or stuttering (micro-ratcheting) behavior at all on V97,
> so I stopped the drive."*

## ✅ BOTH OPERATOR HYPOTHESES REFUTED [EVIDENCE]

**"A mistaken cal address" — excluded 3 ways.** `0x38202` bytes `e5 6f ad 73` = `ld.hu 0x73ac[tp],r13`;
`tp+0x73AC = 0xC63AC`, reading **102 / 102 / 150** (stock / V96 / V97). Off-by-0x1000 excluded
(`0xC53AC` = 683 identical in all three); neighbours `0xC63A0..0xC63AE` all 1024 unchanged. Census
**1 reader / 0 writers**, five methods; **Ghidra ∖ Python set-difference EMPTY**. V96→V97 = **5 bytes**.

**"The logic isn't used" — refuted statically AND dynamically.**
```
0x221D6  andi 0x830,r25,r28
0x225EE  cmp r0,r28 / be → jarl 0x26C80    ← the assist-channel MIXER
0x22672  cmp r0,r28 / be → jarl 0x38148    ← OURS. BYTE-IDENTICAL guard, same r28
```
⇒ **a shut gate means NO POWER ASSIST AT ALL.** Plus `sign(gp-0x374c)` **toggled 181× in 109 s**.
**No speed gate, no rate gate, no engagement gate on the path.**

## 🛑 WHY IT COULD NOT BE SCORED — three independent reasons, none of them the lever
1. **NO INSTRUMENT** — V96's regressor is **34× over-range**; `M ≡ 0` on **10,749/10,749** frames
   (3rd replication: 7e 99.90 %, 7f 99.97 %, r80 **100 %**). **Conceded in `build_v97_tva.py:99-100`
   BEFORE the flash.**
2. **EXPOSURE** — **1** hands-off episode ≥2 s and **1** return, vs 24/27 and 14/11 on 7e/7f; the
   `|Q|=1.233` direction result rests on **25**.
3. **THE OBSERVABLE** — **DC gain 1.000000 at any `A`: a POLE, not a GAIN** ⇒ no amplitude statistic
   can see it, **and none was pre-registered**. Measured anyway: phase **+3.27°** / **−4.08°**,
   *opposite signs*; 6–9 Hz cross-build **5.92× < r7e's own split-half 6.98×**.

⇒ **`0xC63AC` is UNINTERPRETABLE — a null with no positive control. NOT FALSIFIED. DO NOT RE-DOSE.**
Filing it either way is the arc's most expensive mistake in opposite directions.

⊕ **V97 never claimed a grinding/ratcheting fix** — it prices only a 21 Hz *cost* and argues direction
from **hands-off returns**, while the drive was 80 % hands-off *at creep*, a different regime.
**"No difference in grinding" is consistent with the build working exactly as specified.**

⚠ **Identity is V96-OR-V97, not single-frame V97** — the two images differ by 5 bytes with identical
cave and bit maps, so **no frame can separate them**. `[[accord-probe-design-law-compare-dont-quantise]]`

Related: `[[accord-observer-residual-two-arms-v89-v97]]` ·
`[[accord-dead-lever-taxonomy-and-liveness-checklist]]` · `[[accord-v88-flew-grinding-fixed-command-intact]]`
