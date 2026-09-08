---
name: accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed
description: "V288 rev 2 (2026-09-07) = V282 + a 48-byte code cave that low-passes the LKAS rate-PID SETPOINT (y += (sp-y)>>4, +1 fix, 10.3 Hz at 1 kHz, 15 ms delay, kick /16) with an engage-time init from Honda's own sentinel; 0 cal bytes; adversarial pass PASSED on rev 2 after rev 1 FAILED twice (stale state across disengage; stock 0x14A bit 0 overwritten); image 94cabdef…, rwd 43efd0c9…; UNFLOWN."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fb8c05d-08ba-46ea-96e0-19a3b1899a03
  modified: 2026-09-08T05:30:35.906Z
---

# V288 rev 2 — setpoint pre-filter cave, built and adversarially passed (2026-09-07)

**What it is.** Hook 0x29D72 (`st.h r16,-0x6a32[gp]`, a dead publish of the assist-map output sp) → `jr 0xC4C00`.
Cave: `ld.w -0x6cf8[gp],r6 ; mov 0x7fffffff,r9 ; cmp r9,r6 ; be <st.h>` (engage init: y := sp on the first
engaged tick after any gap) then `ld.h y ; sub ; sar 4 ; (+1 if step==0 && d!=0) ; add ; st.h ; ld.h→r16 ; jr 0x29D76`.
State = gp-0x6a32 itself (zero readers image-wide; the only other writer is in the unreachable PID copy at 0x2AC68).
Telemetry: 0x14A byte 4 **bit 5 = sign(y)** (replaces V282's |r24|≥|aggregator| comparator; bit 6 = |r24|≥|T| kept).
Diff vs V282: 91 bytes / 5 regions / **0 calibration bytes**. K is one constant (K=3 fallback: 21 Hz, 7 ms, kick /8).
Files: `_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-…` (image sha256 94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c, rwd 43efd0c98446d331a5b529cbaf93f1173e61e9daa132903cf3467078a7207714).

**Why this class.** A reference pre-filter sits OUTSIDE the rate loop: E = 32·sp_f − fb, nothing feeds sp_f back, so the
loop's return ratio and GATE 2 are untouched by construction. V287's D clamp attacked the same excitation INSIDE the loop
and clipped feedback D in loaded strata. First build V38→V288 ever to touch the reference the PID compares against.

**Adversarial record.** Rev 1 FAILED: (B) disengage paths skip the hook so y froze and seeded re-engage (11 ms railed
wrong-direction worst case); (A) rung wrote 0x14A b4.0, a STOCK Honda flag. Rev 2 PASSED A/B/C/D (A and B with
conditions: instrument renamed; outer-loop PM never measured, 15 ms ≈ 20° at 3.9 Hz is a stated cost).

**Status:** built, unflown. Operator scores the symptom. See [[accord-0xe4-command-is-not-a-staircase-slew-cap-is-the-excitation-grind1-is-a-rung-bell]],
[[accord-disengage-skips-the-pid-hook-and-gp-0x6cf8-is-hondas-first-tick-sentinel]], [[accord-0x14a-byte4-bits-0-2-are-stock-honda-cave-owns-3-7]].
