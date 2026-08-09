---
name: accord-plant-model-residual-aggregator-chain
description: "The FUN_0003b8f6 -> FUN_0003bc20 -> FUN_00038148 -> FUN_00037fe6 chain traced end to end, with censuses, the 0/1 enable flags, gp-0x67fa == {11}, and three new flatten-into-a-relay hazards."
metadata:
  node_type: memory
  type: reference
---

★★★★ **THE PLANT-MODEL → RESIDUAL → ASSIST-AGGREGATOR CHAIN, TRACED END TO END** (2026-08-09).
Folded into `analysis-2020accord/eps_lkas_chain_model.py`.

```
FUN_0003b8f6 @0x3b8f6   1 kHz plant-model estimator
                        sole caller FUN_0002214a, guard andi 0x830 => states {4,5,11}
  model  = EMA2(gp-0x6b98 x polarity/1024, a=0xC40D4=573/4096)
         + clamp(FIR(EMA2(gp-0x4f60/1024, a=0xC40D8=3686/4096)) x 0xC613A/32768, +-15)
           x LERP13(gp-0x6a10, X@0xC6B66, Y@0xC6B80)/1024
  FRICTION = clamp(EMA(|model| x 102/1024 + 0/1024, a=0xC40D0=408/4096) x ratio, +-10)  -> gp-0x6ae2
      ratio = clamp(polarity(gp-0x6752) x gp-0x6abc x 12 / cal(0xC40BC), +-1)  [saturates at cal/12]
  INERTIA  = EMA^2[d/dt(polarity x gp-0x6abc x 12) x 17.453293] x 0xC646E      -> gp-0x6ae0
  gp-0x6bfc = clamp(0xC6468(=2639) x (model - FRICTION - INERTIA), +-20000)    @st 0x3BC1A

FUN_0003bc20 @0x3bc20   plausibility |x| < 20000 -> gp-0x6bfe, status gp-0x695c (0x400 ok / 0xFFFF bad)

FUN_00038148 @0x38148   resid = gp-0x6bfe
                              - (EMA(SUM 6ch x weights 0xC63A0..0xC63AA, coeff 0xC63AC=102) >> 4)
                              + gp-0x6bfa
                        gp-0x6b70 = clamp(SIGN(resid) x LERP_RAM(|resid| x 0xC63AE >> 10),
                                          +-0xC6200=8192)                      @st 0x382D2

FUN_00037fe6 @0x37fe6   ASSIST AGGREGATOR
                        sum = -gp-0x6b4a + SUM(term x BYTE enable 0xC64AD..0xC64B3, all 0x01)
                        gate: the six optional terms are summed whenever gp-0x67ab != 1
                        gp-0x6ad6 = clamp(sum x speedLERP(gp-0x69aa)/1024, +-25600)  @st 0x38142

-> FUN_0003a382 (PID; gp-0x6ad6 is its feedback/bias term) -> gp-0x6ad4 -> aggregator
   -> governor -> gp-0x6acc bridge -> gp-0x6b98 -> FOC -> PWM
```

**Censuses (dual-encoding scan) [EVIDENCE]:** `gp-0x6bfc` 2 hits · `gp-0x6bfe` 2 · `gp-0x6b70` 2 ·
`gp-0x6ad6` 3 · `gp-0x67ab` 3 (the `0x37FE6` hit is a genuine `ld.bu` — the aggregator's entry read).

- **`0xC64AD`..`0xC64B3` are 0/1 ENABLE FLAGS, not gains.** **`0xC64B0` gates `gp-0x6b70`.**
  The aggregator's speed LERP is **flat 1024**.
- **`0xC6200` has 15 readers**, and the governor cals `0xC6202/04/06/08` cluster **disjointly** at
  `0x045410`–`0x0457de` ⇒ **`0xC6200` is NOT governor-shared** — confirmed twice, and consistent with
  V40 having written `0xFFFF` into `0xC6206`/`0xC6208` while leaving `0xC6200` untouched.
  ⚠ **3 of its 15 readers are UNIDENTIFIED ⇒ RULE 11 is NOT satisfied on it.**
- ⚠ **`Y[0]` of the RAM LERP is UNRESOLVED.** `Y[0] = *(u16*)(gp-0x3714)` via `movea -0x3714,gp,ep`
  @`0x39508` + `sld.hu 0x0,ep,r11` @`0x3950C` → `st.h r11,-0x641c,gp` @`0x39522`, inside
  `FUN_000389ec`. The only ordinary-addressing access image-wide is a **store-zero** at `0x38D22` —
  **a lead, not an answer**; the block is `ep`-relative and invisible to a displacement scan.

## 🛑🛑 THREE NEW "FLATTEN A CURVE INTO A RELAY" HAZARDS — the V72/V80 error, one family over
V80 is the recorded cost of making this error once: **the worst grinding in this car's history.**

| cell | stock | forbidden move | what it produces |
|---|---|---|---|
| **`0xC4080`** | **0** | 🛑 **NEVER RAISE** | `FRICTION += cal/1024 × ratio` has **no `\|model\|` factor** ⇒ a **latent PURE COULOMB RELAY**: amplitude-independent, unbounded in index |
| **`0xC63AE`** | 1024 | 🛑 **never → 0** | the LERP index becomes ≡ 0 ⇒ output ≡ `±Y[0]`, a constant ⇒ **a pure relay at full authority** |
| **`0xC6200`** | 8192 | 🛑 **never < `Y[0]`** | the clamp produces the same relay from the other side |

## 🛑 `gp-0x67fa`'s REACHABLE SET IS EFFECTIVELY {11} ALONE
State 5 **structurally dead**, state 10 measured **0.0000%**, state 4 measured **0/123,277**.
⇒ **V42's `0x454FE` is present on V85 (`0xB5`) and MEASURED INERT.** Keep the byte — silently lost three
times, costs nothing — but **carrying it is not addressing ratcheting**, and no build may be justified
on it.
⊕ **`gp-0x671a` is RULED OUT** as a lever axis: stuck at 0 across **1,158 reversals** on V64.

⊕ **Recorded, virgin, untested and NOT proposed:** `FUN_00036388` contains a **relay-with-dwell** —
dwell counter `gp-0x6a82`, +1/tick while `|gp-0x6b64| < 0xC618A` (=1024), ceiling `0xC627E` = 20;
**past 20 ticks the output SNAPS to 1024**, writing `gp-0x6b62`. Cals `0xC618A` / `0xC627E` / `0xC63C0`
were **never edited by any build** (grep-confirmed). Disfavoured by
[[accord-ratchet-is-a-linear-loop-oscillation]]'s no-comb evidence.

Related: [[accord-fun3b8f6-coulomb-relay-proportional-to-command]],
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]],
[[accord-levers-killed-2026-08-09]], [[accord-v85-flew-lever-delivered-bands-are-null]].
