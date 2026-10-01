---
name: reference_accord_angle_loop_in_place_edit_set_and_8bit_setpoint
description: 2026-09-30, V295 bytes. The LKAS map path quantizes the setpoint to an 8-bit index (241 levels, 16.1257 wire counts/step, 1-step floor asymmetry) so it cannot carry an angle; an angle P loop + rate D needs only same-length in-place edits (x disp 0x28F4C, add at 0x28FA4, ld.h -0x69ae at 0x29D6A, Kd negate + rate load at 0x29EDE/0x29EE0) plus a=0,b=8192,C=65535; speed-Kp, I bleed, angle validity and sentinel clamp need a cave.
metadata:
  type: reference
---

Image V295 (sha `5c044d65…`); code 0x28EA6..0x2A30E byte-identical to V294 (Ghidra program used).
Trace: `docs/traces/TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md`.
Mirror: `analysis-2020accord/studies/angle_loop/lane_mirror_v295.py` (agrees with the golden model tick-for-tick).

**Setpoint = 8-bit index (EVIDENCE).** `idx = |clamp(((G*clamp(clamp(-4*raw,±16384),±LIM))>>16)>>6, ±240)|`,
`sp = sign*Y(idx)` (`mulh` at 0x29D6C: Y must stay ≤ 32767). One step is 16.1257 wire counts. Floor asymmetry:
raw +1 gives idx 1, raw −1 gives idx 0. An angle sent through it is 1.61 deg per step, which is unusable.

**In-place edit set (encodings positive-controlled on existing instructions in the image):**

| site | V295 bytes | candidate bytes | effect |
|---|---|---|---|
| 0x28F4C | `24 3f aa 95` | `24 3f 00 96` | x := gp-0x6a00. This ONE load also feeds the ±12000 bail gate |
| 0x28FA4 | `89 d1` | `c9 d1` | subr → add: the two-sample sum |
| 0x29D6A | `08 80 ed 80` | `24 87 52 96` | ld.h -0x69ae[gp],r16: sp = −4·raw unquantized. r8/r13 dead after; 0x29D6C is not a branch target |
| 0x29EDE | `c7 00` | `80 39` | subr r0,r7: −Kd |
| 0x29EE0 | `10 40 bb 41` | `24 47 aa 95` | ld.h -0x6a56[gp],r8: D = clamp((−Kd·x)>>3), 0.16·Kd T per deg/s |
| 0x29A5A | `ba 05` | `b0 05` | optional: skip/reset I iff ramp==0, whatever the request bit |

Cals: a 0xC63E8 = 0, b 0xC63EA = 8192, C 0xC62E6 = 65535. These give `r26 = 8θ[n]+8θ[n−1]` and
`E = 16(θ_sp − θ)` with `θ_sp = −raw`: 0.1 deg per wire count, ±409.6 deg. T ≈ Kp/100 T counts per 0.1 deg.
Keep Kp ≤ 10922, the int32 bound on E·Kp including the sentinel.

**Sign (EVIDENCE).** In mode 3 the STEER_ANGLE wire = −gp-0x6a00 (0x40B04..0x40B18) and the rate wire =
(−x)>>3 (0x40B48..0x40B4E). With DBC factors −0.1/−1 and the measured slope +1.00, sign(dθ/dt) = sign(x).
So the angle P is negative feedback, and a D on +x would ANTI-damp.

**Needs a cave:**
- speed-scheduled Kp (the Kp key is idx);
- an I bleed on driver torque (the fade multiplies the sum, never the accumulator);
- angle validity (gp-0x6a00 is forced to 0 outside gp-0x67fe ∈ {1,2});
- a clamp on the 0x7FFF sentinel.

**Do not** use a = −1024 (a pole at z = −1).

**V295-base displacement-only (just the x edit):** r26 = LPF_2Hz(Δθ)·80.77 = 0.808 counts per deg/s. That is a
DC rate damper, not an angle loop.

**Kit-memory errata found (reported, not applied):**
- `reference_accord_lkas_pid_register_map_and_taper.md` §3: fade B's axis is gp-0x682f (|tq|>>5), NOT speed
  gp-0x6a5e.
- `reference_accord_op_0e4_steer_command_full_path.md`: the NORMAL gp-0x69ae store is 0x526F2. The sentinel
  stores are 0x5268C/0x52726/0x527C6, the reverse of what that note says.

Related: [[reference_accord_0xe4_fault_sentinel_rails_the_lane_on_v293_plus]],
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]], [[reference_accord_kp_kd_schedule_axis_is_the_demand_index]].
