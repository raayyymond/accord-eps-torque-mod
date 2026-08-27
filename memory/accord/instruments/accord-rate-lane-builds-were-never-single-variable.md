---
name: accord-rate-lane-builds-were-never-single-variable
description: "r24 and r26 have SEPARATE gain selectors (gain_B vs gain_A) sharing ONE gate; every post-V38 rate-lane build moved them differently, so no two builds are a single-variable contrast — and the belief that made them look single-variable (r26 inert) is now refuted on-car."
metadata: 
  node_type: memory
  type: project
  originSessionId: cd0a7709-d576-4983-bd00-1d8facc96710
  modified: 2026-08-04T22:23:01.775Z
---

★★★★ **[EVIDENCE — orchestrator disassembled `FUN_0003aa2c` in Ghidra, 2026-08-04, dry-run on stock
`code.bin`.]** The two inline rate lanes have **separate gain selectors**, both gated by the **same
`lp`**:

**r26's selector, `0x3AB56`–`0x3AB6C` (gain_A):**
```
0x3AB56  cmp r0, lp
0x3AB5C  be 0x3AB64
0x3AB5E  ld.hu 0x7444, tp, r8     ; 0xC6444 = 512   <<< THE GATE ARM FOR r26
0x3AB64  cmp r0, r2 / be 0x3AB6C
0x3AB68  ld.hu 0x743e, tp, r8     ; 0xC643E
         (else r8 keeps the gain_A LERP, 3072 at creep)
0x3AB6C  mul r1,r6,r0 / sar 0xa / mul r8,r6,r0 / sar 0xa   <- 0x3AB76 is V62's sar
```
**r24's selector, `0x3ABFA`–`0x3AC18` (gain_B):**
```
0x3ABFA  cmp r0, r6 / be 0x3AC04
0x3ABFE  ld.hu 0x7442, tp, r10    ; 0xC6442 = 1024  <<< MASK ARM (gp-0x671d), OUTRANKS ALL
0x3AC04  cmp r0, lp / be 0x3AC0E
0x3AC08  ld.hu 0x7446, tp, r10    ; 0xC6446 = 5244 on V67/V68  <<< THE GATE ARM
0x3AC0E  cmp r0, r2 / be 0x3AC16
0x3AC12  ld.hu 0x7440, tp, r10    ; 0xC6440 = 2048
         (else r10 keeps the gain_B LERP — the mode-10 surface V69/V70 edit)
0x3AC16  mov r1,r8 / mul r10,r8,r0
```
★ r26 = `dtorque × avg × gain_A` (**two** multiplies, the average formed at `0x3AB52`/`0x3AB54`);
r24 = `dtorque × gain_B` (**one**). **Different LERPs.** V69/V70's `0xD2A7E`/`0xD2ABA` edits are on
**gain_B only** ⇒ they never touched r26.

## ⇒ NO TWO RATE-LANE BUILDS ARE A SINGLE-VARIABLE CONTRAST

| build | r24 (gain_B) | r26 (gain_A) | grind #1 median `e_18-22`, engaged creep |
|---|---|---|---|
| V61 (both taps zeroed) | **×0** | **×0** | 2501 |
| stock | ×1 | ×1 | 879 |
| **V69** (gain_B surface ×4) | ×4 at low rate → **×1 above rateKey ~1400** | **×1** | 746 |
| **V70** (gain_B surface ×2) | ×2 at low rate → **×1 above rateKey ~1400** | **×1** | operator: **BACK** |
| **V62/V65** (`sar` both sites) | **×2** | **×2** | 168 |
| **V67/V68** (gate + arm) | ×1.71 (5244 / 3072) | **÷6.00** (3072 → 512) | **109 (best)** |

🛑 **The ordering is non-monotone in r24 AND non-monotone in r26**, so neither lane alone explains the
record. **The attribution of V42/V61/V62 to "r24 carries the lane" rested on LEG 2 — r26's magnitude
being ~0 — and that is now REFUTED on-car**: V70's probe found **1,644 / 18,010 frames with
`gp-0x6adc` strictly negative**, and a cell pinned at zero cannot clear a `>= 0` test
(see [[accord-r26-is-structurally-inert]], whose LEG 2 this closes).

★★★ **THIS IS THE "STUCK SINCE V38" ANSWER.** The search was not in the wrong neighbourhood — **the
experiments were never single-variable**, and the one belief that made them look single-variable has
just been falsified. Every rate-lane build moved r24 and r26 in different ratios, and the record
priced them all on r24 alone.

## THE LEVER THIS OPENS — `0xC6444`, and it is the record's own flagged candidate
V67/V68's gate cuts **r26 6× while engaged** at the same time as it raises r24. If the **cut** is
what bought their best-in-kit grind #1 — or, on the other side, what caused their **high-speed
grind #2** (present on V67/V68, gone on V69/V70, which reverted the gate) — then **`0xC6444`
512 → ~3072 decouples the two lanes for the first time in the kit.**
⚠ `0xC6444` is **UNTESTED UPWARD**: V42 tested it **downward** (512 → 0, FALSIFIED) — the same
"tested downward ≠ tested upward" distinction the V61→V62 correction turned on. Blast radius already
on record: **1 reader / 0 writers, no float mirror, overflow ceiling ≤ 6553, same CRC block as
`0xC6446`.**

⚠ **AND A SEPARATE, UNRESOLVED PROBLEM SITS ON TOP OF ALL OF THIS.** On route 50 V70's positive
control `gp-0x6ada >= +512` read **0/18,010** against a replay predicting **311** from the route's own
data (**52 even under stock**) ⇒ delivered gain **< ~1574 Q10**, below stock's 3072. `0xC6442 = 1024`
(the `gp-0x671d` mask arm, which outranks everything) is the only arm predicting exactly 0.
⇒ **the gain_B surface may not have been in force at all**, which would make V69's and V70's edits
largely inert. **The next probe must read the gain ACTUALLY IN FORCE (or `gp-0x671d`/`gp-0x671a`),
not another lane output** — see [[feedback-probe-the-gate-not-just-the-output]].
✅ The `gp-0x6ada` identification itself is **verified**, not the problem: `0x3AC42`–`0x3AC54` is
`r24 = clamp(r6, ±0x2000)` and `0x3AD5A st.h r24,-0x6ada,gp` stores exactly that, r24 unclobbered
through the add chain at `0x3ACC8`–`0x3ACDA`.
