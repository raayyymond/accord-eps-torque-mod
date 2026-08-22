---
name: reference_accord_v62_sar_absent_v104_v105_and_r24r26_at_historical_dose_ceiling
description: CONFIRMED (direct byte read, both plain images) -- V62's sar 0xa->0x9 doubling at 0x3AC20(r24)/0x3AB76(r26) is NOT on V104 or V105; both read stock 42AA/32AA. V104/V105 carry ONLY the V67/V88-style arm mechanism (gate repointed to gp-0x6806, r24 arm 0xC6446=5244, r26 arm 0xC6444=512 untouched, a 6x CUT to r26 exactly as documented for V67/V68). This is the SAME r24/r26 dose combination that already produced the BEST recorded grind#1 (18-22Hz) median (109) in the kit's own dose table -- better than V62/V65's 168. The operator's V105 "still grinding/ratcheting" report is therefore a report on a car ALREADY at this lane's best historically-measured dose, which argues against simply adding more r24/r26 dosing (including restoring V62's sar edit) as a high-probability fix for the CURRENT complaint.
metadata:
  type: reference
---

# V62's mechanism confirmed absent from V104/V105; r24/r26 is already at its best recorded dose

Traced 2026-08-22, `leverb-gate` session, team-lead's brief items 3-4. [EVIDENCE: direct PowerShell
byte reads, `[System.IO.File]::ReadAllBytes`, on `stock_fw_dump/code.bin`,
`_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4_plain_image.bin`, and
`_v105_V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64_plain_image.bin`.]

## Byte-exact confirmation

| address | role | stock | V104 | V105 |
|---|---|---|---|---|
| `0x3AC20` | r24's post-multiply shift | `sar 0xa` (`42 AA`) | `sar 0xa` (`42 AA`) | `sar 0xa` (`42 AA`) |
| `0x3AB76` | r26's post-multiply shift | `sar 0xa` (`32 AA`) | `sar 0xa` (`32 AA`) | `sar 0xa` (`32 AA`) |
| `0x3AA96` | shared gate operand (`gp-0x683c`→C5 / `gp-0x6806`→FB) | `C5` | `FB` | `FB` |
| `0xC6446` | r24 flat arm | 512 | 5244 | 5244 |
| `0xC6444` | r26 flat arm | 512 | 512 (untouched) | 512 (untouched) |

**Confirms and closes the question the other agent raised**: V62's edit (`sar 0xa`→`sar 0x9`, a literal
doubling of BOTH r24's and r26's output, dose-exact and independent of the LERP surface/arm mux) is
byte-identically STOCK on V104 and V105. **The car has V88's mechanism (arm repoint) but not V62's
(shift doubling) — these are two structurally different levers the record had been treating loosely as
one family**, per [[reference_accord_rate_lane_v62_to_v69_gain_arc]]'s own table (which only tracked
this through V69; this file extends the confirmation through V105).

## What "having V88's mechanism" actually delivers — both halves, not just r24 up

Because r24 and r26 share the SAME gate operand (`lp`, now `gp-0x6806`, confirmed LIVE at creep in
[[reference_accord_gp6807_is_live_speed_gated_not_dead_can_status]]), the V104/V105 edit simultaneously:
- **r24**: switches OFF the mode-10 LERP surface, ONTO flat `0xC6446`=5244 — ≈2.00× at grind#1's own
  operating point (creep ~7.2 km/h, ~128°/s; LERP there ≈2622, and 5244/2622=2.000 exactly, per
  [[reference_accord_rate_lane_v62_to_v69_gain_arc]]'s pre-existing measurement, re-confirmed unchanged).
- **r26**: switches OFF its own default surface (≈3072 at creep), ONTO flat `0xC6444`=512 — a **6.00×
  CUT**, untouched by V104/V105, identical to the mechanism already documented for V67/V68.

## The dose table already has this exact combination, and it is the BEST recorded

From the kit's own grind#1 (18-22Hz) median dose table (golden model docstring,
`_inline_torque_rate_a`, cross-checked this session — not re-measured, cited from existing record):
```
build              r26 x    r24 x    grind #1 median e_18-22
V61                0.000    0.000            2501
stock/V69/V70      1.000    1.000       879 / 746 / 729
V72                0.177    1.000       unmoved (0.953)
V62/V65            2.000    2.000             168
V67/V68            0.177    1.994             109   <-- SAME mechanism as V104/V105's r24/r26 state
```
**V67/V68's combination (r26 cut 6×, r24 boosted ~2×) already produced the single best recorded
grind#1 number in the whole table — better than V62/V65's uniform 2× doubling (109 vs 168).**
V104/V105 carry this exact r24/r26 state (confirmed by the byte table above), on top of the biquad
gain raise (E1) and, on V105, an added 25.5Hz notch (per the build's own file name and docstring) —
i.e. the CURRENT car is not under-dosed in this lane relative to the kit's own history; **it is at, or
very close to, the best dose this specific mechanism has ever produced, by this specific metric.**

## Consequence for a V106 proposal in this lane

**The operator flew V105 (this exact r24/r26 state, PLUS a dedicated frequency-targeted biquad+notch
aimed at ~24.9-25.5Hz) and reports grinding AND ratcheting still present.** Given r24/r26 is already
at its historical-best dose point and [[reference_accord_r24_leverb_transfer_function_flat_no_recenter]]
shows the lane has no frequency selectivity to retune, **stacking V62's sar-doubling on top, or raising
`0xC6446`/`0xC6444` further, has weak prior support as a fix for the CURRENT complaint** — the same
class of intervention (r24/r26 dosing) already produced its best-known result and the symptom persists.
This is offered as a clean, low-risk, already-twice-flown (V62, V65) byte-exact option if the team
wants to try it anyway (GATE 1/2 profile is as good as this kit gets — a single in-place immediate
edit on an already-executing `sar`, no new RAM state, no new call, already proven safe twice on-car),
**not as a recommendation** — the record argues the missing piece more likely lies outside this lane.

Byte-exact restoration, if wanted: `0x3AC20` `42 AA`→`42 A9` (r24, sar 0xa→0x9), `0x3AB76` `32 AA`→
`32 A9` (r26, sar 0xa→0x9). 2 bytes total, no CRC-block interaction beyond the existing block these
sites already sit in on every V62/V65/V67/V68/V104/V105 build.

## Related
[[reference_accord_rate_lane_v62_to_v69_gain_arc]] — the full V62→V69 arc this file extends to V104/V105.
[[reference_accord_r24_leverb_transfer_function_flat_no_recenter]] — why frequency re-centering is not
a coherent alternative build in this lane.
[[reference_accord_gp6807_is_live_speed_gated_not_dead_can_status]] — why the shared gate is live at
creep, making both halves of this analysis (r24 up, r26 down) actually in force in the operator's regime.
