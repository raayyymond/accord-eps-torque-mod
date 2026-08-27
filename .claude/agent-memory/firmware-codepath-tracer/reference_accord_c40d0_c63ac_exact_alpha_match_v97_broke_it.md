---
name: reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it
description: Stock encodes a BIT-IDENTICAL alpha between 0xC40D0 (MODEL arm friction EMA, 408/4096) and 0xC63AC (ACTUAL arm accumulator pole, 102/1024) -- both exactly 0.099609375 and -23.63 deg at 7.79 Hz, across two DIFFERENTLY-SCALED cal cells -- and V97 broke it by setting 0xC63AC=150; measured on a common basis V97 moved the two stages from 9.62 deg apart to 17.45 deg apart, i.e. FURTHER out of alignment. Also refutes "the MODEL arm is UNFILTERED": FUN_0003b8f6 applies SEVEN EMA stages before gp-0x6bfe.
metadata:
  type: reference
---

# The exact α match stock encodes between the two observer arms — 2026-08-13, `tracer-arms`

Found while retargeting onto the MODEL↔ACTUAL **mismatch** after the V98 comparator showed
`iVar6 ≈ MODEL − ACTUAL` with the two arms comparable (`b6` = 0.4235, `b5` = 0.0000 engaged).
Write-up: `docs/traces/TRACE-2026-08-13-v99-arm-levers.md` §9–§11.

## 1. 🛑🛑 "THE MODEL ARM IS UNFILTERED" IS FALSE [EVIDENCE — `decompile_function(0x3b8f6)`]

`FUN_0003b8f6` applies **seven EMA stages** before `gp-0x6bfc` → `gp-0x6bfe`. One-pole
`y += (x−y)·cal/4096`, fs = 1000 Hz (proven two ways):

| cal | val | stages | fc | phase @7.79 Hz | role / load addrs |
|---|---|---|---|---|---|
| `0xC40D4` | 573 | **×2** | 24.0 Hz | **−33.25°** | command `gp-0x6b98`×pol → `fVar18`, **MAIN PATH** `0x3b94e`,`0x3b96a` |
| `0xC40D8` | 3686 | ×2 | 366 Hz | −0.62° | `gp-0x4f60` side term — **NO-OP** `0x3b98e`,`0x3b9a2` |
| `0xC40D0` | 408 | ×1 | 16.7 Hz | **−23.63°** | the friction term itself `0x3bb22` |
| `0xC40D6` | 246 | **×2** | 9.86 Hz | **−73.86°** | d/dt of rate → INERTIA, subtracted `0x3bb60`,`0x3bb8a` |

"UNFILTERED" is true only of `FUN_00038148` — the filtering happens one level up. **The `STATE.md` /
brief diagram is wrong on this point.**

## 2. ⭐⭐ THE EXACT MATCH [EVIDENCE — LE reads from `code.bin` and the V98 image]

```
0xC40D0 = 408 / 4096 = 0.099609375     MODEL arm, friction-path EMA   @0x3bb22
0xC63AC = 102 / 1024 = 0.099609375     ACTUAL arm, accumulator pole   @0x38202
                       ^^^^^^^^^^^  BIT-IDENTICAL.  Both -23.63 deg @ 7.79 Hz.
```

**Two differently-scaled cal cells (÷4096 and ÷1024) chosen so the resulting α is bit-identical.**
[EVIDENCE for the identity. **BELIEF, strong**, that it is a deliberate matched-pole design for a
difference of correlated estimates — an exact match across two different scalings is hard to get by
accident. The kit's own record already noted `0xC40D0/4096` = *exactly* `102/1024` without drawing
this consequence.]

## 3. V97 BROKE IT — and the direction now looks wrong

`0xC63AC` = 150 ⇒ α = 0.146484375 ⇒ **match broken.** Pole arithmetic (`a = A/1024`, `0x38210`/`0x38220`):

| A | α | fc | phase @7.79 Hz |
|---|---|---|---|
| 70 | 0.0684 | 11.3 Hz | −33.27° (≈ the MODEL **main** path) |
| **102 (stock)** | 0.09961 | 16.70 Hz | **−23.63°** — **≡ `0xC40D0` exactly** |
| **150 (V97, on car)** | 0.14648 | 25.21 Hz | **−15.81°** |
| 205 | 0.2002 | 35.55 Hz | −11.01° |

**V97 moved the pole +7.82°** (the operator-facing figure is confirmed) — but on a common basis it moved
the two stages from **9.62° apart to 17.45° apart: FURTHER out of alignment, not closer.**
⇒ **V97 is not "under-dosed with headroom" — its DIRECTION is suspect.** The corrective move is **DOWN**
(150 → 102 restores the exact match; A = 70 would instead match the MODEL's main path).

🛑 **SCOPE LIMIT — do not over-read this.** It compares two *filter stages* on a common basis. It is
**not** a total arm-to-arm phase budget: the six lanes feeding the accumulator have their own upstream
dynamics (unsummed here), and so does whatever feeds the command into `0xC40D4`.
**"V97 went the wrong way" is EVIDENCE about the two poles and BELIEF about the arms.**

## Related
[[reference_accord_c63ac_is_the_pure_lead_pole_lever]] — the pole; its "+12.6° margin" framing assumed
lead was wanted, which this file questions.
[[reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness]] — companion finding, same decompile.
[[reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode]] — the per-cal phase table this extends.
