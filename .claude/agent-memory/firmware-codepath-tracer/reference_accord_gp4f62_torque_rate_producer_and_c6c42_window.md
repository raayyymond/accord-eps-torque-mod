---
name: reference_accord_gp4f62_torque_rate_producer_and_c6c42_window
description: 0xC6C42=4 is a genuine 4-sample lookback window in FUN_0007e74a, a backward-difference torque-RATE estimator (not a pure transport delay) producing gp-0x4f62, which feeds r24/r26 (the V62-V73 rate lane) directly inside FUN_0003aa2c. Runs at 1kHz (see FUN_0002214a state-mask correction), so the window is 4ms, not the previously-miscalculated 12.8ms
metadata:
  type: reference
---

**ARC's claim (0xC6C42=4, "the kit's only pure delay lever") is CONFIRMED as a genuine, real, previously-unbuilt lever — but the CLASS is wrong: it is a backward-difference DIFFERENTIATOR window, not a pure transport delay.** [EVIDENCE, full decompile + dual-encoding census]

`FUN_0007e74a` (0x7e74a-0x7e873), sole caller `FUN_0007f3f8` (0x7f3f8, the Sensor-B torque-sensor fusion function that also produces `gp-0x4f60`), sole caller of THAT `FUN_0006bb08` (called from `FUN_0002214a` — see [[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]]):

```c
// 8-slot ring buffer of gp-0x4f60 (torque) + a wrapped tick-counter, one push per call
ring_torque[idx] = gp-0x4f60;  ring_time[idx] = accumulated_tick_counter;  idx = (idx+1) mod 8;
if (cal(0xC6C42) < 8) {                              // gate: valid window 0..7
    lookback = idx - cal(0xC6C42);                    // N samples back
    dt = ring_time[idx] - ring_time[lookback];         // wrapped elapsed ticks
    gp-0x4f62 = (dt < 1) ? 0 : (2*(ring_torque[idx]-ring_torque[lookback])) / dt;
} else {
    gp-0x4f62 = 0;  // (unless shadow-mismatch triggers the monitor FUN_0006b9ee)
}
```

Raw value at `0xC6C42` = **4** (byte-confirmed). `search_instructions operand_pattern=6c42` finds **zero genuine hits** (1 coincidental branch-target false positive) — this cal's reader is in code Ghidra's `search_instructions` index does NOT surface directly; needed a raw byte scan filtered to valid ld.hu opcode bytes (`0xe5` first-byte, disp`|1` quirk: pattern `43,7c` not `42,7c`) to find the 4 real reader sites, all inside `FUN_0007e74a` (0x7e7d8-0x7e800). **0 writers found image-wide.**

**Downstream (the connection to the rate lane)**: `gp-0x4f62` = "Sensor-B four-sample torque derivative" is read directly inside `FUN_0003aa2c` (the aggregator writing `gp-0x6b94`) as the inputs to **r24** (`gp-0x4f62 × generated Q10 gain, ±3 deadzone, clamp ±8192`) and **r26** (`gp-0x4f62 × averaged gp-0x69a4 × generated Q10 gain, clamp ±8192`) — [[reference-accord-base-assist-lane-architecture]]'s existing, still-valid characterization. **r24/r26 are the kit's most-flown lane (V62 doubled it, V67/V68 gated it, V69-73 explored it extensively)** — `0xC6C42` sizes the underlying derivative's WINDOW for that exact signal family, a genuinely new angle nobody has tried.

**Correct transfer function** (backward difference over N=4 samples at fs=1kHz, NOT a pure delay):
```
H(f) = (2/(N·T)) · (1 − e^{−jNωT}) = (4j/(N·T))·sin(NωT/2)·e^{−jNωT/2}
     ⇒ phase = +90° (ideal-derivative lead) − 180·N·f·T   [degrees; the "group delay" of the window]
     ⇒ |H|/|H_ideal_derivative| = sinc(N·f·T) = sin(π·N·f·T)/(π·N·f·T)
```
At N=4 (stock), 8.21 Hz: phase = 90−5.91 = **+84.09°** (still a strong LEAD, not a lag), magnitude within **−0.015 dB** of an ideal derivative. At 20 Hz: phase = 90−14.40 = **+75.60°**, magnitude **−0.092 dB**. At N=7 (max reachable, gate is `<8`): 8.21 Hz phase=+79.66° (−0.047dB), 20 Hz phase=+64.80° (−0.282dB).

🛑 **Team-lead's own sensitivity hint (−2.96°/count at 8.21Hz) uses the PURE-DELAY convention (`−360·f·N/fs`) — that number is exactly reproduced by the math, but it is the WRONG model for this element.** The correct group-delay convention for a backward-difference window is HALF that: **−1.48°/count at 8.21Hz**, and the element ALSO contributes a fixed +90° lead the pure-delay framing omits entirely. **Authority verdict**: going from N=4 to the max reachable N=7 (Δ=3 counts) shifts phase by only **−4.43° at 8.21Hz** / **−10.80° at 20Hz** — an order of magnitude smaller than `0xC40D4`'s −32° single-cal-move or `0xC63AC`'s dose range (tens of degrees). **Right class (a genuinely novel, never-built lever, confirmed real), low authority for phase-shaping the ratchet on its own** — its main effect is on the ACCURACY (sinc rolloff) of the r24/r26 derivative estimate, not on relocating the loop's −180° crossing.

Traced 2026-08-09, `fw-lever-census` follow-up task (Part 2), reported to team-lead same session.
