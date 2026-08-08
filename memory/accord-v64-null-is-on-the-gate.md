---
name: accord-v64-null-is-on-the-gate
description: "V64 flashed 2026-07-31 → grinding unfixed, but the probe read 0x87 constant for 14,980 frames — the detector never armed, so the cal edits were never in force. A null on the GATE, not on the damping hypothesis."
metadata: 
  node_type: memory
  type: project
  originSessionId: bc782257-b6f6-4f50-b561-9f5907a74209
  modified: 2026-07-31T22:46:43.512Z
---

**V64 flashed and driven 2026-07-31, route `00000035--77808fe7ce`** (3 segs, 14,980 frames / 149.8 s,
all creep, disengaged-then-engaged, 1,958 reverse frames). Operator: *"The vibration/grinding at low
speeds is not fixed."*

🛑 **The probe says WHY, and it is not the damping hypothesis.** `0x14A` byte4 = **constant `0x87`**,
zero variance: bit7 liveness **set**, bits 6/5/4/3 (`gp-0x671a>=5` / `!=0` / `gp-0x67df!=0` /
`gp-0x671d!=0`) **all clear on every frame**. Confirmed four ways — raw byte histogram, the dedicated
decoder, an independent raw-CAN rederivation, and V59's probe ruled out (its bit5 was set essentially
always; here 0/14,981, and other routes show byte4 varying `0xBF/0x8F/0x9F/0x87`).

⇒ **`gp-0x6c2c` never crossed T = 12800, so V64's two cal edits (`0xC6440` 2048→4096, `0xC643E`
1536→3072) were never in force for a single frame.** The drive tested the *gate*, not the damping
direction. That remains untested on-car.

**Spectra agree independently: V64 ≡ V59.** Engaged creep 21.30 Hz / 149× / 4.31e8 vs V59's 21.18 Hz /
227× / 5.26e8; in the best-populated 2–3 m/s bin the two agree to **20.98 vs 20.99 Hz and env99 1811 vs
1804**. V61's spread into manual driving is gone. Flight-clean: `ST==4` zero, all six watched events zero,
CAN at 100.03 Hz.

✅ **The build was aimed CORRECTLY** — this closes the dispute flagged at `build_v63_tva.py:63`.
`cmp r14,r12 / bc` @`0x3AA7C` sets `r2 = 1` iff `gp-0x671a >= CEIL`, and both `ld.hu 0x743e[tp]`
@`0x3AB68` and `ld.hu 0x7440[tp]` @`0x3AC12` are taken iff `r2 != 0`. ⚠ The golden model's
`selected_state_value` is **r22** (from cals `0xC6138`=1 / `0xC6136`=0), a *different register* from the
arm selector **r2** — both model readings were right, describing different variables.

⚠ **bit3 = 0% ⇒ r24 WAS covered** (the `gp-0x671d` override was idle, so r24 would have taken `0xC6440`).

**The detector genuinely ran** — `FUN_000428d4`'s whole body is gated on `FUN_00046ea6(5)==0` (bit 5 of
`gp-0x18d0|gp-0x18d4`), which briefly looked like an alternative explanation. Closed: bit 5 has **exactly
one caller image-wide — the detector itself** (verified by raw byte scan of all 47 `jarl` sites; Ghidra
found only 44, the known undercount), the only dynamic indices are cals `0xB9A14-16` = **0, 2, 6**, and
the mask is DTC-driven and self-clearing (`gp-0x18d4` is rebuilt by plain assignment each fault sweep).

⇒ **Next flash recommended: V62** (unconditional 2× on the rate lane, 6 bytes, no detector in the loop).
See [[accord-gp671a-blast-radius-not-a-free-lever]] for why lowering T ranks behind it, and
[[accord-gp6c2c-is-motor-rate-derivative]] for the sizing if it is ever revisited.
