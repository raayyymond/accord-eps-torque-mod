---
name: reference_accord_gp6752_is_the_frame_converter_and_k1_makes_it_lighter
description: "gp-0x6752 = -1 is NOT a stray negation -- it is the DRIVER-FRAME <-> AGGREGATOR/MOTOR-FRAME converter, applied at exactly the 7 places a signal crosses between the two frames and nowhere else. Settles the K1 (0xC40D2) friction question: raising it makes the wheel LIGHTER. Answer sign-chain questions by counting FRAME CROSSINGS, not negations."
metadata:
  type: reference
---

# `gp-0x6752` is a FRAME CONVERTER, not a negation — and it settles the K1 question

Traced 2026-08-22, task `friction-sign` from `main`: *"the memory says raising K1 makes the wheel
LIGHTER and is marked VERIFIED. I have found its sign chain is incomplete"* — the PID's tail
multiplies by `gp-0x6752` = −1 and the memory
`accord-friction-polarity-more-friction-is-more-assist` never crosses it. Program `code.bin`.

## THE FINDING [EVIDENCE — 7 sites, read from the live DB this session]

`gp-0x6752` is applied at **exactly the places a signal crosses between two sign conventions**:

```
DRIVER frame     = gp-0x4f60 (Sensor-B column torque) and the plant model in FUN_0003b8f6
AGGREGATOR frame = gp-0x6b94 / gp-0x6b98 (the motor command) and its lanes
aggregator_value = gp-0x6752 * driver_value        gp-0x6752 = -1
```

| addr | function | crossing |
|---|---|---|
| `0x3B92E` | `FUN_0003b8f6` | `ld.b -0x6752 -> cVar5`, **used twice** |
| (cVar5) | `FUN_0003b8f6` | `gp-0x6b98` (motor cmd) `* cVar5` -> plant-model frame |
| `0x3B91C` | `FUN_0003b8f6` | `ld.h -0x6abc`; `* cVar5 * 12` -> the friction term's VELOCITY sign |
| `0x381EE` | `FUN_00038148` | the six aggregator lanes `* POL` before differencing vs MODEL |
| `0x3668E` | `FUN_00036682` | `gp-0x4f60 * 0xC646C * POL` -> aggregator lane `gp-0x6b46` |
| `0x358C2` | `FUN_000352b4` | `mulh r11,r14`: assist-map magnitude `* POL` -> `gp-0x6b82` -> `gp-0x6b86` |
| `0x3AB78` | `FUN_0003aa2c` | r24/r26 `* POL` -> aggregator addends |
| `0x3A71A` | `FUN_0003a382` | PID(driver-frame error) `* POL` -> `gp-0x6ad4` |

No site applies it twice; no driver-frame-internal computation applies it at all. This is why the
golden model already *names* the cell `assist_polarity` and why it is set from a **boot config
record** — it is a hardware orientation / assembly-handedness byte.

⚠ **SCOPE**: `gp-0x6752` has **55** `ld.b`/`st.b` sites program-wide. Only the 7 on the
friction->felt-effort path plus the aggregator's other addends were audited. "No counterexamples"
is a claim about THIS PATH, not the program.

## 🛑 THE REUSABLE RULE

**Answer a sign-chain question by counting FRAME CROSSINGS, not negations.** A parity count over
`gp-0x6752` gives the wrong answer here, because the factor is not an operation on the value — it is
a change of units. The old memory made *two* errors that cancelled (omitted the `x(-1)`, and read
"`gp-0x6ad4` up" as "more assist" without establishing a frame) and got the right answer with
unusable reasoning.

## THE K1 ANSWER — LIGHTER, and it does not depend on the operating point

`0xC40D2` (K1, the `|model|`-proportional modelled Coulomb friction in `FUN_0003b8f6`) **102 -> 204
makes the wheel LIGHTER.** Mirror script: `analysis-2020accord/studies/models/friction_k1_sign_chain.py`.

```
d(friction)/dK1 = |model|*ratio/1024        sign = sign(ratio) = sign(v in MODEL frame)
d(MODEL)/dK1    = -2639*|model|*ratio/1024   <- OPPOSITE to the motion   [0x3BBC2 subf.s]
d(res)/d(MODEL) = +1                                                      [FUN_00038148]
d(6b70)/d(res)  = f' >= 0   (LERP on |res|, odd, monotone non-decreasing) <- holds EVERYWHERE,
                            so the chain never assumes where the residual sits
d(6ad6)/d(6b70) = +1 * w(0xC64B0)=1 * LERP(1024)>>10 = +1.000 EXACTLY
d(6ad4)/d(6ad6) = -POL*Kpid = +Kpid   (ZERO only if |6ad6| >= 8192 -- the V100 rail)
delivered_driver_frame = POL * gp-0x6b94
```

★ **The closed-loop statement is the self-checking one and needs no parity count:**
`u = POL*K*(Ts - Tref)`, `Ts = P*u + Text`  =>  `Ts = (L*Tref + Text)/(1+L)`, `L = -P*POL*K`.
`L > 0` is forced physically (at `L < 0` the loop AMPLIFIES `Text`; at `L < -1` it runs away; the
car assists and does not run away). => `dTs/dTref = L/(1+L) > 0` => **`gp-0x6ad6` IS A TARGET FELT
EFFORT; lowering it lightens the wheel.**

⊕ **Control that would have caught an error**: this predicts `d(gp-0x6b94)/d(gp-0x6b70) > 0`; the
kit independently MEASURED **+0.2529 / +0.2565 / +0.2617**. One extra or one missing negation would
have predicted negative.

⊕ `gp-0x6ad4` has **exactly 2 touches program-wide** — `0x3A8A0 st.h` (sole writer) and
`0x3ACA8 ld.h` (sole reader) — so nothing can negate between the PID and the aggregator.

Cals byte-read from stock: `0xC40D2`=102, `0xC4080`=0, `0xC40BC`=600, `0xC6468`=2639,
`0xC6200`=8192, `0xC63AE`=1024; all seven weights `tp+0x74ad..0x74b3` = **1**; the `gp-0x6ad6`
output LERP `tp+0x7aca..0x7ad8` is **flat [1024]x8** => gain exactly 1.000. `0xC40D2` = **204** on
V89/V98/V100/V104/V105/V106, 102 on stock.

## 🛑 TWO TRAPS THIS SESSION SURFACED

1. **`0xC40D2` (K1, a `tp`-block scalar in the PLANT MODEL) is NOT the x1.5 friction TABLE**
   (`0xCF6E0 ... 0xD9A6C`, 14 mode records behind pointer array `0xCBE74`, feeding the
   **`gp-0x6b26` friction LANE**) that V73 introduced and V81 reverted. Two different mechanisms
   sharing one word. V81's *"removes drag the operator is used to"* says **nothing** about K1.
2. **`gp-0x4f62` is `d(gp-0x4f60)/dt`, not a second torque channel.** `FUN_0007e74a` @`0x7E860`:
   a ring-buffered N-sample finite difference (`gp-0x2814[]` values, `gp-0x27f4[]` timestamps,
   N from `tp+0x7c42`). It is **r24's input**. In `FUN_0003aa2c` the `gp-0x4f62` lane reads like
   base assist in the decompile and is not — the real assist map is `gp-0x6b86` from
   `FUN_000352b4`. I nearly anchored the whole argument on the wrong lane before checking.

## DEFECT REPORTED, NOT FIXED
`analysis-2020accord/model/eps_chain_core.py` seeds `assist_polarity: int = 1`, contradicting the
★★★★★ on-car-verified −1. The golden model is the live reference and its default is the
pre-correction value. Changing it moves the `_self_check()`/`_demo()` hash `740f4bcd...`, so it
needs a deliberate contract update.

## OPEN
- The RAM LERP `gp-0x64b8[]`/`gp-0x641c[]` monotonicity (`f' >= 0`) was taken from
  `accord-ram-lerp-is-flash-derived-and-fprime-is-nonneg`, **not re-verified**. A negative slope
  segment anywhere breaks the derivative argument.
- **Did V100's `|gp-0x6ad6| >= 8192` comparator fly?** Its duty decides whether K1's dose is
  *small* or *structurally zero*. That is the single fact that would close this completely.

Related: [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]] (the VALUE;
this file is the MEANING) · [[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] ·
[[reference_accord_assist_map_rom_source_found_and_shares_stage2_fork]] ·
[[feedback_audit_your_own_claims_before_others_act_on_them]]
