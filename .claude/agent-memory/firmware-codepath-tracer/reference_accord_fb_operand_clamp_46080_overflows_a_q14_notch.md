---
name: reference_accord_fb_operand_clamp_46080_overflows_a_q14_notch
description: The feedback operand r26 is hard-clamped to +-46080 by cal 0xC62E6 BEFORE any injection point, and the rail is actually reached on the wire (0.2 % of ticks on r62, 0.97 % on r63). A V289-style Q14 TDF-II notch (b1=a1=-31842) OVERFLOWS int32 on that operand (conservative bound 5.87e9, margin x0.37) where it had x1.10 on V289's own +-15360 sum; a sar-3 pre-shift / shl-3 post-shift restores x2.93 margin at 0.032 deg/s of feedback resolution. V850 has mul->64-bit but NO add-with-carry; satadd/satsub exist and are the cheap insurance V289 did not take.
metadata:
  type: reference
---

# The fb operand's ±46080 clamp overflows a V289-style Q14 notch

2026-09-09, subagent `fbhook`. Scripts:
`analysis-2020accord/verify/v290_fbhook_census.py`, `…_headroom.py`. Trace:
`docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md`.

## The bound, and that it is real

`cal(0xC62E6) = 46080` in V282/V289 (stock 7680), applied at `0x28FA6`–`0x28FBC`, i.e. **before** any
hook in `[0x28FBE, 0x29D78)`. Honda's byte-exact fb mirror run on the two V289 routes' `0x18F` stream:
max pre-clamp `|r26|` = 77,410 (r62) / 90,203 (r63); ticks at the rail **0.209 %** / **0.971 %**. The
clamp binds at `|x| ≈ 1492` raw counts ≈ 186 deg/s. **Design to ±46080, not to a percentile.**

## Headroom table (conservative bound `max|coeff| × xmax × 4`, the same one the V289 design used)

| operand | xmax | \|acc\| bound | verdict |
|---|---|---|---|
| V289's own `S` (`0xC61BE`) | 15360 | 1.96e9 | OK, margin **×1.10** (what V289 shipped) |
| `r26` unshifted | 46080 | 5.87e9 | **OVERFLOW**, ×0.37 |
| `r26 >> 1` | 23040 | 2.93e9 | **OVERFLOW**, ×0.73 |
| `r26 >> 2` | 11520 | 1.47e9 | OK, ×1.46 |
| **`r26 >> 3`** | 5760 | 7.34e8 | OK, **×2.93** ← recommended |
| `r26`, Q12 coefficients | 46080 | 1.47e9 | OK, ×1.46 but halves coefficient precision |

The *single* product `|b1·x| = 31842 × 46080 = 1.467e9` does fit; it is the accumulator that does not.
`sar 3` / `shl 3` costs 8 counts on ±46080 = 0.26 raw rate counts = **0.032 deg/s**.

## V850E2 arithmetic actually available (forms observed in this binary)

- `mul reg1,reg2,reg3` — **32×32 → 64-bit**, low in `reg2`, high in `reg3`. Honda always passes `r0` as
  `reg3` to discard the high half (`0x28F8E`, `0x28F92`, `0x2A180`, `0x2A194`). The high half IS
  available — but **V850 has no add-with-carry**, so 64-bit accumulation costs a manual `cmp`+`setf`
  carry per add. Prefer the pre-shift.
- `mulh reg1,reg2` — 16×16 → 32 (`0x29D6C`, `0x2A1F6`). Too narrow for Q14 against ±46080.
- `sar`/`shl`/`shr` imm5 or reg; `sar` floors toward −∞ (keep V289's `andi 0x3fff` error feedback or the
  filter parks up to 64 counts low).
- **`satadd`/`satsub`** — 32-bit saturating. Turns an unforeseen overflow into a bounded error instead of
  a sign inversion. V289's cave did not use them.

Related: [[reference_accord_0x29d72_is_the_feedback_operand_hook_flagsafe]],
[[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]].
