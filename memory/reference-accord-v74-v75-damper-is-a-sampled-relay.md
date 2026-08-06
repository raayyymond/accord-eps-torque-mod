---
name: reference-accord-v74-v75-damper-is-a-sampled-relay
description: V74/V75's FactorE Y[1]:=Y[2] made the base-assist damper a bang-bang relay inside a feedback loop; stock has no plateau, and the relay is a 100 Hz sampled-data artifact.
metadata:
  type: reference
---

★★★★★ **[EVIDENCE, byte-read by the orchestrator from the images] V74 AND V75 TURNED THE
BASE-ASSIST DAMPER INTO A BANG-BANG RELAY. STOCK HAS NO SUCH THING.**

Mode 26 (engaged) `FactorE` record `0xD780C`:

| build | X | Y | constant-magnitude band |
|---|---|---|---|
| stock | `[60,400,2500,4000]` | `[0,140,539,927]` | **none — monotone ramp** |
| V73 | `[60,400,2500,4000]` | `[0,140,539,927]` | **none** |
| **V74** | `[12,400,2500,4000]` | `[0,**539**,539,927]` | rate 400–2500 = **85–531 °/s** |
| **V75** | `[12,**200**,2500,4000]` | `[0,539,539,927]` | rate 200–2500 = **42–531 °/s** |

`Y[1] == Y[2]` ⇒ magnitude **constant** across `X[1]→X[2]` while the sign comes from `gp-0x6abe`
(`0x3469e: cmp r0,r11 / ble / subr r0,r8`). Constant magnitude + sign-following = **relay**.
Amplitude at creep (FactorC flat at `Y[0]` for all speed < 2240 ct = 35 km/h): V74 **225**, V75 **297**.

🛑 **THIS IS EXACTLY THE ERROR THE DESIGN CLAIMED TO AVOID.** `STATE.md` argued *"`Y[0] = 0` is
preserved, so magnitude vanishes with rate ⇒ no discontinuity, no chatter mechanism … the OPPOSITE of
V72's error."* `Y[0] = 0` **is** preserved — but that governs only **below `X[1]`**. Above `X[1]` the
argument inverts. **V75's `X[1]` 400→200 dragged the relay band down into ordinary creep steering.**

★★ **THE RELAY IS A SAMPLED-DATA ARTIFACT, NOT A TABLE DISCONTINUITY.** The continuous surface is
continuous (`Y[0]=0`, `X[0]=12` ⇒ magnitude ≈ 0 at the sign flip). But `gp-0x6bd0` is recomputed at
**100 Hz and HELD** (`FUN_00034350` ← `FUN_00022ca0`, task 5). For `rate = A·sin(ωt)`:

| symptom | A (ct) | f | rate travel per 10 ms tick | time inside `\|rate\| < X[1]` |
|---|---|---|---|---|
| grind #1 | ~1184 | 21 Hz | **~1560 ct** | V75 **2.6 ms** · V74 5.2 ms |
| ratchet | ~461 | 7.79 Hz | ~226 ct | V75 27 ms · V74 55 ms |

⇒ **At 21 Hz the crossing is a quarter of one sample — unresolvable — so the held output jumps
`+297 → −297` in one tick (a 594-count step) regardless of how the table is shaped.** At 7.79 Hz the
crossing takes 3–6 samples and IS resolved, so shaping does real work there. **The two symptoms want
different fixes.**

★★ **THE DAMPER IS INSIDE A LOOP, AT 2× WEIGHT.** `FUN_00038148 → gp-0x6b70 → FUN_00037fe6 →
gp-0x6ad6 → FUN_0003a382`, where `ERR = clamp(driver_torque − clamp(gp-0x6ad6, ±8192), ±0x2800)` drives
a P+I+D → `gp-0x6ad4`. **`0xC63A0` = 1024 stock → 2048 from V72 onward** (V72's Lever C, a bare `tp`
scalar ⇒ **MODE-PROOF and always live**). 🛑 `BUILD-LINEAGE.md:259` still claims this chain's weights are
*"all unity (1024 = 1.0) and stock … no hidden loop gain in the aggregation"* — **FALSE since V72**, a
RULE 4-class ledger error. And `RULE 7` files Lever C as *"inert by table selection"* — it is not
mode-indexed; it was only **functionally** inert because the damper it weights was zero. **V74 turned the
damper on and silently armed it.**

**Exposure, from a frame-by-frame replay of route 5d through both surfaces** (validated against V74's own
on-car `damp_nz` probe bit: 99.83% agreement at rate ≥ 200 ct), engaged 0–35 km/h:

| | plateau time | **entries** | median dwell | sign flips |
|---|---|---|---|---|
| V74 | 14.11 s (7.53%) | **35** | 210 ms | 16 |
| V75 | 28.25 s (15.08%) | **282** | **10 ms — one tick** | 42 |

⇒ **V75 did not make the damper stronger (1.32×) so much as make it SWITCH (8.1× the boundary
crossings, 13.7× at creep).** Transition rate 0.128/s → 1.152/s engaged; direction consistent across
8 of 9 episodes (sign test **p = 0.039**). Magnitude ratios do **not** clear their own paired split-half
null at n = 9 — only direction is establishable.

⊕ Only place on route 5d where the relay engages a live oscillation: a **1.2 s burst at 113 km/h,
engaged, coherent at 29.67 Hz**, with openpilot's own command at 29.33 Hz. V74 spends 0/300 frames on
its plateau there; V75 spends 14. Damper p-p 445 → 728. ⚠ This is a **replay** of V75's surface over
V74's telemetry — it shows contact, not amplification.

See [[reference-accord-v75-fault-refutation-ledger]] for the six mechanisms ruled out, and
[[reference-accord-monitor2-corridor-and-the-c64a4-trap]] for the surviving candidate.
