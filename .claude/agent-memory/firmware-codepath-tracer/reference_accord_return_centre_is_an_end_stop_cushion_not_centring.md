---
name: reference_accord_return_centre_is_an_end_stop_cushion_not_centring
description: RE-IDENTIFICATION -- the lane the kit calls "return-to-centre" (gp-0x6b62, FUN_00036388) is a RACK END-STOP CUSHION. FUN_00035e00 arms it on a STALL detector (|gp-0x6b98|>4096 AND motor rate gp-0x6ac0<200) and splits into two 0/1/2 "at the stop" enums gp+0x6440/gp+0x6441. Its gate is shut because the travel envelope's half-width is FLOORED BY CALIBRATION at cal(0xC6150)>>1 = 9390, which reproduces the measured hands-off gp-0x6bda = 9262 EXACTLY. No LKAS gate exists; the lane is dead engaged AND ~99.3% dead in manual, on stock and on every build.
metadata:
  type: reference
---

# The "return-to-centre" lane is a RACK END-STOP CUSHION — 2026-08-12 (`fw-return`, team-lead's V97 crux pass)

Full writeup: `analysis-2020accord/_v97/fw_return.md`. Dispatched to test the hypothesis
*"the return-centre lane is muted while engaged, so the clean manual return is that lane doing its
job."* **Refuted.** All Ghidra on `code.bin` explicitly — the session's *current* program was the V96
image with **0 functions**.

## The re-identification [EVIDENCE]

`FUN_00035e00` @`0x35e00` arms the whole cluster on:
```
|gp-0x6b98| > cal(0xC618E)=4096    final motor command HIGH (governor max is 4762)
&& gp-0x6ac0 < cal(0xC620C)=200    motor electrical rate LOW -> not turning
&& gp-0x4f68 > cal(0xC6190)=7680 && gp-0x6a5e >= cal(0xC62E2) && gp-0x67f4==1 && gp-0x6990==0
```
**High command + near-zero motor rate = STALL.** It splits on `sign(gp-0x6bf0)` into two independent
0/1/2 enums `gp+0x6440`/`gp+0x6441` (**left stop / right stop**); `FUN_00036388` requires the enum to
reach **2** ("at the stop") for the direct path (`0x363a2`, `0x364d6`). Diagnostic
`FUN_000193ce(0xb,0)` fires on any state change. `gp-0x6bf4=|gp-0x6bf0|` is separately tested against
`(cal(0xC6150)>>1) − 0x280 = 8750`, a second "near end of travel" threshold from the same cal.

**`gp-0x6bf0` is POSITION-like, proven at zero extra cost:** if it were a rate, the arm (rate<200)
and the gate (|x|>8878) would be mutually exclusive ⇒ the lane could NEVER fire. V92 measured it
firing (89 frames). ⇒ position. (Producer `FUN_0003bd7c` @`0x3c0cc`:
`(accumulator × cal(0xC6464)) >> 12 × polarity(gp-0x6752)`, lockstep shadow `gp-0x4cf6`.)

## Why the gate is shut: the envelope half-width is FLOORED BY CALIBRATION [EVIDENCE]

`FUN_00036022` @`0x36022`, mirrored exactly:
```python
OFFSET = 0 if u8(gp-0x67fe)==2 else s16(0xC614C)   # 0x36026 ; cal = 128
x = s16(gp-0x6bf0)                                 # 0x36068
dist = (x - s16(gp-0x6bd6)) if x < 1 else (s16(gp-0x6bd8) - x)   # >= 0 EITHER WAY
w16(gp-0x6bda, dist - OFFSET)
```
🛑 **CORRECTS [[reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization]]**,
which had the positive branch as `x − UPPER`. It is `UPPER − x`. ⇒ `gp-0x6bda` is a **non-negative
distance to an envelope edge**, which is what makes the lane legible as an end-stop cushion.

Gate table @`0xC695C` byte-read: `X=[-397,-192,140,294,384] Y=[0,2560,2560,717,0]`. Both ends clamp
to 0. Since `dist ≥ 0` and OFFSET=128, `gp-0x6bda ≥ −128 > −397` ⇒ **the −397 edge can NEVER bind;
the gate is purely `dist < 512`.**

`FUN_00035d38` @`0x35d38` keeps UPPER(`gp-0x6bd8`)/LOWER(`gp-0x6bd6`) as a **non-decaying max/min-hold**
of `gp-0x6bf0`, capped ±cal(0xC614A)=±10048, reset to ±(cal(0xC6150)>>1)=**±9390**. The only
*narrowing* path (the re-centre branch) is **DEAD**: guarded by `gp-0x37ba==0`, and `gp-0x37ba`'s sole
image-wide writer is `st.h r0` (**zero**) @`0x35df6` (6 hits, `truncated:false`; the `tp-0x37ba` hits
at `0x83bb0+` are a different base).

⇒ half-width ∈ **[9390, 10048]** always ⇒ **gate needs |gp-0x6bf0| > 8878.**

**EXACT cross-validation:** the kit's independently-recorded hands-off `gp-0x6bda ≈ 9262` is
reproduced to the count by `18780>>1 − 128 = 9262` at x≈0. A firmware cal reproducing an on-car
measurement exactly — this retires the "cited-not-reverified 9262" caveat in
[[reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff]].

## The hypothesis is refuted two independent ways [EVIDENCE]

1. **V92's own data**: manual duty is **0.0074**, not ~1 ⇒ the lane is ~99.3% dead in MANUAL too, so
   it cannot be what makes the manual return clean.
2. **Firmware**: zero engagement dependence. The only state byte in the producer is `gp-0x67fe`, a
   **sensor-validity** state whose sole writers are 4 `st.b` sites in `FUN_0003bd7c`/`FUN_0003e760`.
   59 accesses enumerated, `truncated:false`.

Re-confirms from a second direction that no `if (LKAS != 0) suppress return` branch exists — see
[[reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism]].

## Lineage — Honda's, not ours [EVIDENCE]
`grep -lE "C6150|C614A|C614C|C618A|C627E|..." build_v*_tva.py` → only `build_v92_tva.py`, all hits
read-only assertions. Byte-verified frozen at stock across **stock/v90/v91/v92/v93/v94/v96**:
`0xC6150`=18780, `0xC614A`=10048, `0xC614C`=128, `0xC618A`=1024, `0xC627E`=20.

## Do not re-arm it
Only cal-only route is narrowing `0xC6150` = telling the ECU the rack is shorter than it is. GATE 1
passes (cal-only); **GATE 2 fails on inspection** (magnitude-ramped relay, LERP peak 2560≈2.5× Q10,
1024-count snap, ±0x2800 clamp, injected unweighted at 1 kHz — a step at a *position*, the V80 class).
Blast radius: 7 read sites / 5 functions (`0x35ce6,0x35d3e,0x35d42,0x35e0c,0x35e5a,0x360d2,0x5691a`),
incl. `FUN_000568d0` which also writes the `gp+0x6440` enum feeding a diagnostic.

## Related
[[reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record]] — the polarity
correction this same pass produced, and the reason `byte7 b6` was wrongly indicted.
[[reference_accord_micro_regime_has_no_scheduled_dissipation]] — the Q4 census from this pass.
