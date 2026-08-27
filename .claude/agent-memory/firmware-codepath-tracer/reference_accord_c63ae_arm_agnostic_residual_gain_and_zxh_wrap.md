---
name: reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap
description: 0xC63AE (the Stage-2 LERP index scale, stock 1024, VIRGIN across all 93 images, 1 reader / 0 writers by both methods) is the only ARM-AGNOSTIC lever on the FUN_00038148 observer residual -- it multiplies |iVar6| AFTER the difference is formed, so it works whichever arm a comparator names; its open-loop sign is closed by construction via the code-enforced f'>=0, and it is a GAIN not a pole so an amplitude statistic can see it -- but zxh @0x3825c is a REAL 16-bit truncation and the wrap is structurally reachable even at stock, so the safe dose rests on a creep-only measured distribution.
metadata:
  type: reference
---

# `0xC63AE` — the arm-agnostic residual gain — 2026-08-13, `tracer-arms`

Found while pre-positioning the V99 lever set on the three arms of
`iVar6 = gp-0x6bfe + gp-0x6bfa − (gp-0x374c >> 4)`. Write-up:
`docs/traces/TRACE-2026-08-13-v99-arm-levers.md`.

## Why it is different from every other candidate
It multiplies **`|iVar6|` — the residual itself — after the difference is formed**, so it does not
depend on which arm dominates. Every other cal-only lever on this structure sits on **one** arm, which
is exactly the failure mode behind V89's flat result and V97's uninterpretable one (both arms are
estimates of the same quantity entering a difference; move one and the residual may barely notice).

## The arithmetic, instruction-exact [EVIDENCE — `get_assembly_context` @ `0x38242`]
```
0x38242  ld.hu  0x73ae[tp],r10   ; r10 = 0xC63AE = scale (stock 1024)
0x3824a  mulu   r10,r8,r0        ; r8 = |iVar6| * scale   (UNSIGNED multiply)
0x3824e  cmovlt -0x1,r11,r11     ; r11 = sign(iVar6)  -- re-applied AFTER the LERP
0x38256  shr    0xa,r8           ; >> 10  (LOGICAL)
0x38258  movea  -0x64b8,gp,ep    ; the LERP table itself is ep-based
0x3825c  zxh    r8               ; ****** REAL 16-BIT TRUNCATION ******
0x3825e  cmp    r7,r8            ; vs LERP X[0] at gp-0x64b8
```
```python
idx = ((abs(iVar6) * SCALE) >> 10) & 0xFFFF      # 0x3824a, 0x38256, 0x3825c
out = sign(iVar6) * LERP(idx)                    # 0x3824e
out = clamp(out, -8192, +8192)                   # 0xC6200
```

## The four questions
1. **SIGN — open-loop RESOLVED BY CONSTRUCTION.** `f′ ≥ 0` is enforced in code at three ungated sites
   (`0x388c4`'s eight `max(Y[i],Y[i-1])` rungs, the float-path monotone guard, `0x38de2`/`0x38e48`)
   ⇒ monotone non-decreasing for any cal, any mode, any build. The sign is re-applied separately at
   `0x3824e` from `sign(iVar6)`, which `mulu` on `|iVar6|` cannot touch. ⇒ **raising the scale strictly
   increases `|gp-0x6b70|`, sign-preserving.** 🛑 **Closed-loop sign is NOT thereby closed** — Path 2
   enters as `B = 1 + Q` and `gp-0x6b70` is a PID reference that gets SUBTRACTED.
2. **GAIN, not a pole.** Unlike `0xC63AC` (DC gain 1.000000 at every value — why V97 could not be
   scored) this changes the DC transfer, so an **amplitude statistic sees it**, and the `gp-0x6b70`
   427-lane instrument is already flying and good (98.29 % nonzero, 250 codes, 0.000 % saturation).
3. **BLAST RADIUS — the smallest possible: 1 reader, 0 writers.** Ghidra `ld.hu 0x73ae[tp],r10`
   @`0x38242`; raw both-parity LE scan → **1 hit, same address** (plain `ae73` 0 hits, `|1` form `af73`
   1 hit). Set-difference EMPTY. `ep`-aliasing trap tested: 0 `movea imm,gp,ep` bases in `sld` reach.
4. **HISTORY — VIRGIN across all 93 non-stock images.** Never written by any build script.

⊕ **RULE 7 does not apply** — it is a scalar halfword with one load site, no mode record, no per-mode
row. The V69/V70 wrong-record failure cannot recur for it.

## 🛑 THE COST — a real 16-bit wrap, and a bound I got wrong once
`zxh` truncates the index to 16 bits ⇒ it **wraps** when `(|iVar6|·scale)>>10 > 65535`, sending a
saturating-large index to a small one ⇒ `gp-0x6b70` collapses discontinuously (a V80-class relay).

**I first bounded `|iVar6|` at 42,048 using a MEASURED ACTUAL ceiling of 2,048 as if it were
structural. That was wrong.** Structurally `ACTUAL_ss = ((sum6·2639)>>10)`, and with `gp-0x6b4e ≡ 0`
the six lane windows sum to 16,384 ⇒ ACTUAL reaches **42,224** and `|iVar6|` **82,224**:

| scale | × | wrap threshold | vs structural 82,224 | headroom over measured max 6,891 |
|---|---|---|---|---|
| 1024 | 1.00 | 65,535 | REACHABLE | 9.5× |
| 1434 | 1.40 | 46,797 | REACHABLE | 6.8× |
| 1536 | 1.50 | 43,690 | REACHABLE | 6.3× |
| 2048 | 2.00 | 32,767 | REACHABLE | 4.8× |

⇒ **The wrap is structurally reachable even at STOCK** — a pre-existing Honda condition the lane
windows evidently never co-peg into, **not** something a dose introduces. But margin scales inversely
with the cell. **The safe dose is bounded by the measured `|iVar6|` distribution, which is CREEP-ONLY
(route 80, and it explicitly does not travel above 50 km/h where `0xC669A`/`0xC66A8` truncate the LERP
X axis). [BELIEF, resting on a measured distribution with a known coverage hole.]**

## Two neighbours ruled out in the same pass
- **`0xC6200`** (±8192 clamp) — **inert upward**: p99 3,059 against the rail, 0.000 % saturation, so
  raising does nothing and lowering makes a clipper. **Not private**: read by `FUN_00038148`,
  `FUN_0003a382` **and `FUN_000352b4`** (third consumer found this session). NO-GO.
- **`0xC6468` = 2639** — read at `0x381f2` (ACTUAL arm) **and at `0x3b94a`/`0x3bbba` inside
  `FUN_0003b8f6`, the MODEL producer** ⇒ it scales **both arms together** and **cannot change their
  ratio**. Precisely the wrong tool if the arms are unequal. NO-GO.

## Related
[[reference_accord_request_arm_shadow_lockstep_and_no_cal_cells]] — companion finding, same task.
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] — the measured `|iVar6|` bound this dose limit rests on.
[[reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg]] — the `f′ ≥ 0` proof the sign claim leans on.
[[reference_accord_c63ac_is_the_pure_lead_pole_lever]] — the pole this is the GAIN-class alternative to.
