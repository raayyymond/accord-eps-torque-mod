---
name: reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound
description: V75 headroom analysis for the FUN_00034350 damper (FactorC/E) and friction lane -- the ceiling table 0xC77A0 quantified, the E_Y1-vs-E_Y3 no-clip asymmetry that gives free headroom at the operating point, and the aggregator's zero-reject window confirmed INCLUSIVE at the exact limit (not "never the boundary" as build_v74_tva.py's comment implies).
metadata:
  type: reference
---

Task: team-lead asked for V74 lever headroom / a V75 dose ladder. Full decompile-first confirmation of
`FUN_00034350` (damper), `FUN_00036c12` (friction), `FUN_0003aa2c` (aggregator) against `code.bin`, plus
byte-exact reads of `_v74_engagedcols_x0_12_addonly_plain_image.bin` (SHA256 `8ae58cb8f4…`, matches
`docs/STATE.md`). See [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] for
the base trace this extends.

## The ceiling table, quantified [EVIDENCE, decompile 0x34350]
`0xC77A0[mode*4]` -- 2-point LERP indexed on **`gp-0x6ac2`** (NOT `gp-0x6ac0`, which indexes FactorE --
a *different* signal, physical identity NOT resolved this session). Mode 26 (LIVE): `X=[300,800]
Y=[512,1024]`. At the symptom's rate (~99-127, same order as `gp-0x6ac0`, [BELIEF] `gp-0x6ac2` is also
low there) the ceiling sits at its floor: **512**. This clamps `|gp-0x6bd0|` via a shadow-lockstep pair
with `gp-0x4cf2` (`FUN_0006b9fa` on mismatch) -- symmetric, `clamp(product, -ceiling, +ceiling)`.

## THE ASYMMETRY THAT MATTERS FOR ANY FUTURE DOSE LEVER ON THIS DAMPER
V74's own no-clip rule is `(C_Y0 * E_Y3) >> 10 <= floor` -- it binds on **E_Y3** (FactorE's last point,
reached only at rate >= 4000, an extreme corner never seen in-burst; p99 in-burst is 353-367, still under
E's `X[1]=400`). But the OPERATING-POINT value (rate 99-127) is governed by **E_Y1** (reached by rate
>= 400), which on V74 is 539 -- well under E_Y3=927. **Consequence: E_Y1 can be raised up to E_Y3's
CURRENT value for zero new clip anywhere on the (speed,rate) grid**, because the no-clip formula never
looks at E_Y1 directly. Verified numerically: mode 26, raising E_Y=[0,539,539,927]->[0,927,927,927]
gives dose 50->86 (1.72x) at rate 99, with the worst-case corner UNCHANGED (388 vs floor 512, identical
to V74). This is a structural fact about the LERP + no-clip-check shape, not mode-specific -- it will
recur on any future damper-dose lever built on this table family.

## Combined headroom under the EXISTING ceiling
`floor*1024 / (C_Y0*E_Y3)` = `524288/397683` = **1.318x** combined (C x E product) before the ceiling
clips anything NEW, for mode 26 specifically (other modes differ -- V74's own build already needed to
cap modes 29/32/33 individually; re-run `derive_lever_e()`'s per-mode check for any future edit, never
hand-copy one mode's numbers).

## The aggregator's zero-reject window is INCLUSIVE at the limit [EVIDENCE, decompile 0x3aa2c]
```
friction term: gp-0x6b26 * ((gp-0x6b26 + 0x400) < 0x801)   -- accepts v in [-1024,+1024] INCLUSIVE
damping term:  gp-0x6bd0 * ((gp-0x6bd0 + 0x800) < 0x1001)  -- accepts v in [-2048,+2048] INCLUSIVE
```
Solved exactly: v=1024 (resp. 2048) is ACCEPTED; v=1025 (resp 2049) is the first REJECTED value.
`build_v74_tva.py`'s comment "`CLAMP_HARD_CAP=1000, never 1024`" is therefore a **safety margin**, not
an architectural cliff sitting exactly at 1024 -- the true edge is 1024 inclusive. Matches
`eps_lkas_chain_model.py`'s `_range_gate()` (`-limit <= value <= limit`), confirming the golden model's
Python approximation was already correct; this decompile pins the exact V850 boundary instruction that
model was abstracting.

## Seed gp-0x698a -- refines [[reference_accord_gp698a_seed_factora_ceiling_and_v72_probe_null_investigation]]
[EVIDENCE, decompile 0x26c80, fresh this session] STATE.md's 2026-08-05 headline claims "9 channels
hardcoded to 1024, one calibrated to a 1024 floor, one with no runtime writer" for the 11-channel
MIN-reduce feeding `gp-0x698a`. **What I actually decompiled does not match that framing.** Each of the
11 channels runs an 8-STATE machine (`tp+0x5124+i`): states 1/6/7 write a flat 1024; states 0/2/3/4/5
(the majority) instead copy a LIVE tracked value `gp-0x6230[i]`. This is state-dependent per-tick
behaviour, not a fixed per-channel hardcode. Whether `gp-0x6230[i]` typically sits >=1024 in ordinary
engaged-creep driving (making STATE.md's "pinned at 1024" true in practice) is **[BELIEF, still
unresolved]** -- traced 2 functions deep in the prior session (`FUN_00026c80`->`FUN_00025c32`) without
finding a nameable physical signal. The MIN-reduce CEILING (`seed <= 1024`, mathematically guaranteed by
the running-min structure seeded at 1024) IS solid and confirmed. Practically moot either way: **seed has
no calibration table and no address -- it is a computed RAM value, not moddable**, so this doesn't gate
any V75 lever regardless of which framing is right. Flagging so "9 hardcoded" isn't cited as
decompile-verified fact in a future session -- it isn't, as read this session.

## FactorB/FactorD are already at their ceiling
Confirmed flat 1024 (Q10 unity) on every engaged mode, both mode 24 and mode 26, byte read. These are
plausibility/gating multipliers (default to unity when the sensor-validity condition holds), not tunable
gains -- 1024 IS their ceiling by design; raising them above unity is not a sensible lever.

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]
[[reference_accord_gp698a_seed_factora_ceiling_and_v72_probe_null_investigation]]
[[reference_accord_task5_100hz_live_verified_full_producer_census]] (FactorC/E cos response, prior session)
