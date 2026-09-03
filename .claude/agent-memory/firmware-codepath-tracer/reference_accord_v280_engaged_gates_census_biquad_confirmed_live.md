---
name: reference_accord_v280_engaged_gates_census_biquad_confirmed_live
description: Census of every engagement-gated (gp-0x6806) mechanism on the flown V280 image, byte-verified against stock this session. FIRST CHECK of Honda's 55Hz biquad (FUN_000352b4) against a post-V103 flown image -- it IS live and engaged-only on V280 (arm byte 0xC649B=1, V103 repoint present). Rate lane r24 flat gain confirmed 10.24x raised (0xC6446 512->5244) on V280. Flags reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead's "0xC40DC virgin on all 102 images" as STALE -- it's V109's documented lever (BUILD-LINEAGE.md), reads 14 on V280 not stock's 22.
metadata:
  type: reference
---

# V280 engaged-gate census, byte-verified vs stock — 2026-09-03, `fwloops20` session, for `team-lead`

Task: census every engaged-only loop/gain for the 18-22Hz creep-grind symptom
(`rlog-tools/studies/osc-highangle/HIGHANGLE-r34-2026-09-03.md` §8-9). Full doc:
`docs/traces/TRACE-2026-09-03-engaged-only-loops-at-20hz.md`. Method: **fresh Python LE byte read**
of every cal cell against `../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin` AND the
flown image
`../accord-firmwares/analysis-2020accord/_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
— not a static-cal-block read alone, and not relayed from memory unchecked. GhidraMCP not reopened
this session; structure inherited from prior sessions' traces (cited), only the byte-level V280-vs-
stock deltas are new.

## 🛑🛑 NEW: Honda's 55Hz biquad (`FUN_000352b4`) is LIVE and ENGAGED-ONLY on V280 — first check since V103

[[accord-honda-biquad-arm-gate-is-false-on-this-car]] established Honda's own arm condition
(`gp-0x671a<5`) is measured FALSE on-car, so the notch is permanently dormant on stock, and that
V103's 3-instruction repoint (`0x35A06/12/18`) substitutes `gp-0x6806!=0` (STEER_CONTROL_ACTIVE) for
the dead condition. **This session is the first to check whether that repoint survived onto V280.**
Byte read, this session:
```
              0xC649B(arm)  0x35A06        0x35A12   0x35A18
stock         00            844fe798a77a   ec49      e937
V280          01            844ffb97a77a   e049      ea37     <- repoint + arm present
```
⇒ **The notch is live, engaged-only, on the current flown image.** Coefficients unchanged
(`0xC60A8/AC/B0/B4` byte-identical stock=V280): pole |r|=0.7966@42.345Hz, zero |r|=1.0@55.225Hz. Own
response at 20Hz: -1.12dB/-28.5° (mild — not a standalone 20Hz generator by itself, but a real
engaged-only phase-lag contributor now present in whatever loop reads its output, absent on every
pre-V103 build).

## Rate lane r24 (`FUN_0003aa2c`) engaged flat gain — confirmed 10.24x raised on V280

Gate opcode byte `0x3AA96`: stock `0xC5` (off) → V280 `0xFB` (on, `gp-0x6806!=0` selects the flat
cal and discards the speed/rate LERP entirely, per [[reference_accord_rate_lane_v62_to_v69_gain_arc]]
§8). `0xC6446`: stock=**512** → V280=**5244** (10.24x). Matches the V67/V68/V69 lineage cited in that
memory — carried forward unchanged in magnitude through V280, just re-confirmed on the current image.

## Carrier gain `0xC6CD0` and clamp — confirmed 6x, present on V280

`0xC6CD0`=**5346** (=6.00x of `0xC646C`'s 891, matches [[accord-the-8x-gain-is-the-carrier]]'s "V102 =
0xC6CD0 7128->5346 (6x)"). Clamp `0xC61B4`/`0xC61B2`: stock **512** → V280 **3072** (6x, tracks 1:1).
`0xC646C` itself (the shared 4x sensor-to-command scale, 6 static readers) is **UNCHANGED**, 891 both
— the V57+ repoint to the private `0xC6CD0` slot is what carries the raise now, not this shared cell.

## LKAS PID debounce/cutout cals — ALL disarmed on V280

`0xC64B4/B5/B6/B7/B8`: stock 112/96/54/64/112 → V280 **255/255/255/255/255**.
`0xC61C0/C2/C4`: stock 1600/896/1280 → V280 **0xFFFF/0xFFFF/0xFFFF**. Every compare in this chain is
unsigned against an operand that cannot exceed 255 (resp 12800) — both mechanisms are structurally
unsatisfiable on V280, matching the V112/V268-base pattern already on record in
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]]. Confirms that memory's V112 finding transfers
unchanged to V280 (same base lineage, re-verified independently this session).

## Crossover threshold `0xC62E6`

stock **7680** → V280 **46080** (K=6, matches the flown image's own filename `FEEDBACK46080`; ties to
[[reference_accord_v276_crossover_threshold_and_packer_rectifies_sign]]'s K-in-raw-counts table).

## `0xC61BE` (post-gain PID-sum clamp, the D-starvation cell from the V276 census) — UNCHANGED

stock=V280=**15360**. The V276 finding that this clamp (not D's own `0xC61B6`=10240, also unchanged)
starves the D term because P alone fills it at low driver-override index
([[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]]) is **still structurally true on
V280** — no build has touched this cell.

## 🛑 STALE-MEMORY FLAG: `0xC40DC` is NOT virgin — it's V109's documented lever, and V280 carries 14

[[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]] (2026-08-22) states *"Both pole
cals (0xC643C=37, 0xC40DC=22) are VIRGIN on all 102 images — never-tried, not falsified."* Byte read
this session: **V280's `0xC40DC` = 14, not stock's 22.** `docs/BUILD-LINEAGE.md:277,284` documents
this as **V109's α2 band-limit lever** (`22→14`), carried forward through the V122-onward lineage
(`BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md:28`: "V124: 8→5 · V138: 5→2 · V139: 2→8 · ...", i.e. it
kept moving after V109 too, settling at 14 by V280). **The "virgin on all 102 images" memory is stale**
— it was probably true for the specific 102-image corpus that session's byte-scan covered (pre-V109,
or that session's scan didn't include the V109+ lineage), but is FALSE for the current flown build.
`0xC643C`=37 unchanged, confirmed still accurate. **Recommend whoever owns
`reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead` correct the `0xC40DC` virgin claim** —
did not edit it myself per this kit's "ask before updating a memory that looks stale" convention;
flagging here and to team-lead instead.

## Related
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] · [[reference_accord_rate_lane_v62_to_v69_gain_arc]] ·
[[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]] ·
[[accord-honda-biquad-arm-gate-is-false-on-this-car]] · [[reference_accord_v276_crossover_threshold_and_packer_rectifies_sign]] ·
[[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]] · [[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]]
