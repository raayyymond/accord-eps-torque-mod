---
name: accord-golden-model-lacks-the-lkas-rate-pid-stage-contract-is-88-symbols
description: "✅ RESOLVED 2026-09-13: the LKAS rate PID stage EXISTS in the golden model now (SECTION 5D of eps_chain_control.py, `lkas_rate_pid_tick`) — E = 32·sp − fb, I/P/D, the taper, the sum clamp, the output lag, the gain and the output clamp, byte-exact with V282 defaults read from the image. V288's prefilter and V289's notch/fb-lag finally have a caller. Contract: 94 symbols (was 88 on 2026-09-07, 90 on 2026-09-08); stdout hash 740f4bcd… / 2,512 bytes UNCHANGED."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fb8c05d-08ba-46ea-96e0-19a3b1899a03
  modified: 2026-09-13T22:02:31.530Z
---

# ✅ RESOLVED 2026-09-13 — the golden model now carries the LKAS rate PID; the contract is 94 symbols

**The gap this note was created to record is CLOSED.** Grep `lkas_rate_pid_tick` in
`analysis-2020accord/model/eps_chain_control.py` (SECTION 5D). The history below is kept as a record.

## What exists now (2026-09-13)
`lkas_rate_pid_tick(sp, fb, idx, st, cal, pol, taper, engaged)` mirrors stock `FUN_00028ea6` from the
error former at `0x29D76` to the lane-torque store `st.h r1,-0x6b38,gp` @`0x2A23C`, every line annotated
with its instruction address: the `E>>5` deadband and the integrator (the cell holds **8·I**), P =
`(E·Kp)>>8` clamped `±[0xC61BC]`, D = `(ΔE·Kd)>>3` clamped `±[0xC61B6]` behind the `±768000` E_prev
window, the sum `(I>>7)+P+D`, the always-on `×254/256` taper, the `±[0xC61BE]` sum clamp, **V289's notch
hook**, the output lag (`0xC63EC`/`0xC63EE`, its own state `gp-0x3d3c`), the ramp, the forward gain
`0xC6CD0` and the `±[0xC61B4]` output clamp. Three more exported symbols: `lkas_rate_pid_surface`
(cold-start march to the delivered surface), `lkas_output_lag`, `lkas_rate_lerp`.

**V288's `lkas_setpoint_prefilter` and V289's `lkas_sum_notch`/`lkas_fb_lag` now have a real call site**
— see [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]] and
[[accord-v289r1-sum-notch-plus-fb-pole-built-b3-accepted-the-20hz-line-is-a-plant-mode]].

**Calibration fields added**, every default read little-endian from the V282 image (sha256
`0ea98d06b292ca1a…`): `pid_err_deadband` 0xC62E4=4 · `pid_ki` 0xC63E6=0 · `pid_i_clamp` 0xC61BA=10240 ·
`pid_p_clamp` 0xC61BC=15360 · `pid_d_clamp` 0xC61B6=10240 · `pid_e_prev_window`=768000 (a CODE literal) ·
`out_lag_a`/`out_lag_b` 0xC63EC/EE=992/507 · `out_lag_gate` 0xC61B8=102 · `out_lag_gate_arm` 0xC64A3=1 ·
`lkas_forward_gain` 0xC6CD0=5346 (**not** `lkas_output_gain`; stock code reads 0xC646C=891) · `out_clamp`
0xC61B4=3072 (stock 512) · `override_taper_factor`=254 · the three selector-7 banks `assist_map_x/y`,
`kp_x/y`, `kd_x/y`. **EpsState**: `pid_i_state` gp-0x6dd0 · `out_lag_s` gp-0x3d3c · `pid_ramp` gp-0x69b0 ·
`pid_sum_publish` gp-0x6b2e · `lkas_lane_torque` gp-0x6b38 (the CAN-427 tap's source).

**V293 in the model** is `replace(Calibration(), fb_clamp=0, kd_y=(0,)*4, pid_d_clamp=0, kp_y=(120,)*5)`.
⚠ V293 also moves the r24 engaged arm `0xC6446` 5244→2048, which is a **different lane** and is
deliberately NOT a Calibration field — a V293 `Calibration` is the PID stage, not the whole build.

## How to apply
- **The golden model IS now citable for this stage's arithmetic** — that reverses this note's old advice.
  `_self_check_v293()` reproduces `build_v293_tva.py`'s printed surface table **to the count** at all 25
  demand indices (V293's P/S/T/T_ceil and V282's delivery at 0/10/20 deg/s, including the NEGATIVE V282
  columns at low demand) and the feedback operand 0/2434/4908 on V282 vs 0/0/0 on V293 — by *marching*
  the model's tick from cold boot where the builder solves a fixed point, so it is two methods agreeing.
- **CLAUDE.md's contract line must say "exactly 94 symbols"**, hash `740f4bcd…`, 2,512 bytes.
- 🛑 **The rail is 2461 counts.** 2505 drops the taper AND the output lag; 2462 uses the *linear* lag DC.
  Never quote 2505 as a delivery. See [[accord-v278r3-torque-tap-reads-310-and-damping-is-sign-t-ne-sign-rate]].
- 🛑 **REFINEMENT TO THE RECORD, measured by this self-check.** `TRACE-2026-09-13-lkas-pid-tracked-quantity`
  §4a says muting at the input gain `b = 0` leaves `s = −1` absorbing so `fb` rests at **−2**. The
  absorbing SET is bigger: `floor(a·s/1024) == s` for every `s ∈ [−1024/(1024−a), −1]`, i.e. **`s ∈ [−10, −1]`
  at a = 923**, and a large negative excursion lands on **−10**, so `fb` rests anywhere in **[−20, −2]**,
  seed-dependent. The record's conclusion is unaffected and still holds: `b = 0` is not an exact mute, the
  clamp cell `0xC62E6` is, which is why V279 and V293 both use the clamp.

## History (kept as a record)
- **2026-09-07, 88 symbols** — V288 added `Calibration.spfilt_k`, `EpsState.sp_filter_y` (gp-0x6a32),
  `EpsState.pid_prev_err_cell` (gp-0x6cf8, 0x7FFFFFFF sentinel), `lkas_setpoint_prefilter`,
  `_self_check_v288()`. 705,894-case equivalence vs the build script, 0 mismatches.
- **2026-09-08, 90 symbols** — V289 added `sum_clamp`, `fb_lag_a`/`fb_lag_b`, `fb_clamp`, `sum_notch`,
  `EpsState.fb_lag_s`/`notch_s1`/`notch_s2`/`notch_e`/`notch_flag`, `lkas_sum_notch`, `lkas_fb_lag`.
  152,500-tick equivalence vs the build script, 0 mismatches. **Neither stage had a caller yet.**
- **2026-09-13, 94 symbols** — the PID itself. `eps_chain_control.py` grew 134 → 161 KB and is now the
  largest of the five modules; still under the 256 KB `Read` cap, but it is the one to watch.
