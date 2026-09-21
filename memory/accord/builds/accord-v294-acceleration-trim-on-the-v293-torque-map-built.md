---
name: accord-v294-acceleration-trim-on-the-v293-torque-map-built
description: "V294 BUILT 2026-09-20, NOT FLOWN: V293's torque map + a 1 kHz ACCELERATION trim through the stock PID's own P gain -- two in-place opcode halfwords (0x28FA4 add->subr: r26 = s_new - s_old; 0x29D76 shl 5->2) + fb clamp 0->1024 + fb-lag pole 923->1011 (2.0 Hz) + b 1560->567 + Kp 120->960 on all 28 records; the feedforward is BIT-IDENTICAL to V293 at every demand index, the trim is bounded at 25 % of the rail, 27 dB below V282's 20 Hz loop gain; damping ratio of the wheel mode x1.02-2.05 across 5-26 m/s (BELIEF plant). Fork REVERTED: every torque-mode term defaults off, toggle-config_V294_accel-trim_r1."
metadata:
  type: project
---

# V294 — the acceleration trim on the V293 torque map (built 2026-09-20, NOT FLOWN)

**Operator's call (2026-09-20):** *"the delay kills the idea of a torque mode only control … a PID + feedforward
which track acceleration, not rate/velocity … revert all torque mode changes in this next StarPilot update …
anticipate grinding and stuttering (relying on feedforward/torque mode as much as possible)."*

## What V294 is — six edits on the V293 image (image `3143616d…`, rwd `a2b418f0…`, exactly one on disk)

| where | was (V293) | now | what it does |
|---|---|---|---|
| `0x28FA4` code | `add r9,r26` c9d1 | `subr r9,r26` 89d1 | r26 := s_new − s_old — the per-tick CHANGE of the lag-filtered wheel rate = acceleration through the lag pole, ×b/1024 |
| `0x29D76` code | `shl 0x5,r16` c582 | `shl 0x2,r16` c282 | E = 4·sp − r26 (was 32·sp − r26) |
| `0xC62E6` fb clamp | 0 | 1024 | bounds the trim: |r26| ≤ 1024 → (960·1024)>>8 = 3840 sum counts = **25 % of the 2461 rail** |
| `0xC63E8` pole a | 923 (16.5 Hz) | 1011 (**2.0 Hz**) | the acceleration bandwidth: inertia-like below 2 Hz, a light damper above |
| `0xC63EA` gain b | 1560 | 567 | the trim gain: K_α/J = 1.0 at the BELIEF scale (8 x-counts per deg/s) |
| `0xCB994` Kp bank | 120 ×28 | 960 ×28 | (sp<<2)·960 = (sp<<5)·120 = 3840·sp — **the feedforward product is bit-identical** |

Kd 0, D clamp 0, Ki 0, r24 2048, the map, the 427 tap and the 0x14A cave: byte-identical to V293. 314 diff
bytes over 7 CRC blocks, exactly four below 0xC0000. Script `analysis-2020accord/builds/v108_plus/build_v294_tva.py`
(155 assertions: 62 substantive / 89 vacuous / 4 tautological; zero-edit control reproduces V293; 16/16
mutations caught). Design: `analysis-2020accord/studies/v294/v294_design.py`.

## Why acceleration, and why a 2 Hz pole (the crux, EVIDENCE for the algebra, BELIEF for the plant)

With T = −K·H(s)·α and H a LAG: J_eff = J + K·Re H, b_eff = b − K·ω·Im H. A lag has Im H < 0, so every degree
of loop lag turns the trim into DAMPING; delayed RATE feedback does the opposite past 90° (V282's 20 Hz
crossover resonance). The operand s_new − s_old is exactly α/(s + ω_p)·(b/1024): acceleration through a
first-order low-pass at the lag pole. Pole sweep at K_α/J = 1 (fork plant J 8e-5, k(v) hold map, light b):

| pole | ζ× @5 · 8 · 12.5 · 19 · 26 m/s | 20 Hz gain vs the loop V282 was marginal on |
|---|---|---|
| 16.5 Hz (stock) | 0.81 · 0.86 · 0.98 · 1.13 · 1.28 | −10 dB — inertia dominates below 5 Hz, WORSE at low speed |
| 8 Hz | 0.84 · 0.91 · 1.06 · 1.25 · 1.45 | −15 dB |
| **2.0 Hz (shipped)** | **1.02 · 1.16 · 1.49 · 1.82 · 2.05** | **−27 dB** |
| 1.4 Hz | 1.13 · 1.30 · 1.62 · 1.84 · 1.93 | −30 dB |

The trim anti-damps only where the total lag passes 180° (~26 Hz here), where the 5 Hz output lag has cut it
×0.03. Rigid-body loop gain: max 1.7 at the 2.4 Hz resonance (that IS the damping), −180° crossings at 24–35 Hz
with |L| 0.02–0.05. int32 headroom at the ±12000 rate guard: 0.246 of 2³¹. Clamp binds at ~2900 deg/s² (or
~230 deg/s of wheel rate above 2 Hz). The difference operand settles to EXACTLY 0 at any steady rate (no DC
bias, unlike the sum's floor to 2434 at x = 80).

🛑 **Scale-free anchor:** V282's D term was an acceleration feedback on the ERROR at 48.7 P-counts per
washout count (with a setpoint kick and a 67 % clamp); V294's trim is 3.75·(567/1024)·… = **2.08 P-counts per
x-count above 2 Hz, 7 % of V282's rate loop**. Whatever the x scale, V294 sits between V293 (no feedback) and
V282 on the acceleration axis and AT V293 on the rate axis.

## The within-frame instrument (no cross-drive contrast needed)
Because the FF is byte-exact V293's, on every engaged ramped frame `residual = T_tap − FF_V293(idx)·taper =
the trim`. Regress it on −(0x18F rate through a 2 Hz LPF, differenced): slope > 0 with the FF identity R² ≥ 0.98
on low-acceleration frames = LIVE, RIGHT SIGN. Flat = not live (nothing else licensed). POSITIVE correlation =
SIGN INVERTED, stop, revert to V293. New line anywhere in 5–30 Hz = the revert signature.

## The fork side (Dom, uncommitted at the time of writing → see the handoff for the commit)
Every V293 torque-mode term now DEFAULTS OFF (params_keys.h default = stock; starpilot_variables defaults; the
controller's getattr fallbacks) and `AccordRatePlantFF` defaults off (its model is a rate servo or a bare
torque map, V294 is neither). One new toggle `AccordJerkLpHz` (default 1.2 = generic; 4.0 = rev 6's measured
value) gates the one torque-mode-era edit that had no switch. Nothing deleted. Config
`toggle-config_V294_accel-trim_r1.json` = the V282-era values (SteerKP 0.9, Ki 0.3) + AccordRatePlantFF false +
SteerLatAccel 14.0 + SteerFriction 0.011 + every torque-mode term at stock; revert file
`…_REVERT_to_V293_r64.json`.

## Adversarial pass (two Opus agents, disjoint surfaces, FAIL criteria fixed before they ran): BOTH PASS
- **A (arithmetic/sign/scale):** both opcodes decode as claimed with lengths 2→2; the sign is negative
  feedback by four legs (polarity flag cancels, register assignment, integer mirror, delivered torque);
  the FF identity holds for EVERY 32-bit sp (mod 2³² argument); the surface at r26 = 0 equals V293's at all
  241 indices under every taper/polarity/ramp; int32 margin 4.06×; the 20 Hz ratio re-derived −26.7 dB;
  all three cal cells are FLASH (tp-relative) so no register-indirect write can reach them. **Two framing
  corrections:** (i) the 25 % cap is a backstop that binds only at ≥230 deg/s of wheel rate (peak measured
  42–56; r71's limit cycle 88): through the whole chain the trim is **1.85 T counts per deg/s of 2 Hz-band
  rate** (~18 counts at 10 deg/s, 163 at 88), a damper comparable to the wheel's own — right for a ζ lever,
  but the instrument must be a REGRESSION over the drive, not a per-frame read; (ii) at 2–3 Hz the trim is
  ~97 % damping / 26 % inertia (pure inertia only below ~1 Hz).
- **B (build audit/interlocks):** independent rebuild reproduces the hash; the .rwd decodes to the image;
  every changed cell private (3/1/1 accessors, zero writers, base and built accessor sets identical); the
  0x14A cave reads the delivered torque and four non-PID cells, NOT the published P/I/D cells (which have
  zero readers anywhere; S is read once in the orphan island); the fb state has one load and one store both
  in the filter; no governor/EME function reads any changed or rescaled cell; V293's D1 conclusion (lane cap
  3072 cannot drive soft-EME wind-up) survives unchanged. **One sentence for the page:** the trim can add up
  to 616 counts at ZERO command (a behaviour V293 could not produce; V282 flew 2463 there), so if the base
  assist were within 616 counts of the 5120 EME floor AND the wheel ramped hard for 75 ms, V294 enters the
  5120–5325 band where V293 could not — bounded, 0.25× V282's flown exposure. After a filter BAIL the first
  tick's operand equals the fresh state (22–1023 counts, one tick, smoothed by the 5 Hz lag). **Six defects,
  four now fixed in the script** (full 28-record Y census after mutate; register fields read back; b pinned
  to the design ladder; the two missed mutations added → 20/20 caught, 159 assertions); substantive count
  by B's census 41 vs the script's 66; `decode_one` mis-decodes the 6-byte `mov imm32` (neither V294 window
  contains one); the record's 30th `gp-0x6a56` access at 0x14B1E is a `jarl` (count is 29 — erratum added).

- **C (Ghidra, 2026-09-21, after GhidraMCP reconnected and the subagent cap was clarified to Fable-only):**
  C1/C2/C4/C5 PASS from the decompiler — the two edits and their following instructions, 1874 instruction
  boundaries identical to V293, the diagnostic packer at 0x4E82E is a pure record (no threshold), the cell
  census matches; one refinement: `0x2A0C8 cmp r0,r26` is a second in-function reader of the operand on the
  unreachable `gp-0x680a == 1` damper lane (zero writers, boots 0). **C3 was reported FAIL (x = 1.0–1.7, trim
  5–8× weak) and is WITHDRAWN on the wire:** its chain identified the frame at gp-0x14ce as 0x14A, but the
  record places the 0x14A buffer at gp-0x1518; the direct measurement on three V292 routes (rate loop live,
  lane delivers −4.80 T-counts per x-count) gives **x = 7.1–7.8 counts per deg/s at every rate bin**
  (`studies/v294/x_scale_from_v292_wire.py`). **8 stands, now EVIDENCE.** Its ISR finding (the rate former
  differences a 16384-count/rev position at ~3 ms → 1 count/deg/s of that shaft, ×1.6978 to x) is consistent
  with 8 if that shaft is geared ~4.71:1 to the steering wheel (claim B's 4.7121 × 1.6978 = 8.00). **Adversary C then retracted C3 from the bytes (advC_report2.md): the 0x14A rate field is written by FUN_00055a98 as `(gp-0x69ea) >> 3` at 0x55B48 with gp-0x69ea = −gp-0x6a56, so the bus field is −x/8 and **x = 8.00 counts per deg/s exactly**; the ±1500.0 plausibility bound there × 8 = 12000 = the operand's own clamp. The 0x14A buffer is gp-0x1518 (checksum call with the literal 0x14a); gp-0x14ce belongs to a table-dispatched frame of unresolved ID. The rate former differences the MOTOR RESOLVER electrical angle (atan2 over the sin/cos ADC channels, 2π/16384), so the shaft ratio × ISR period product is fixed at 0.0141 s and its split is BELIEF; x itself no longer depends on it.

## Not verified / BELIEF
J = 8e-5 and the light-b world; the shaft ratio behind the ISR constant (the x scale itself is now measured); the pole
choice is the design's ONE free parameter — one cal cell (0xC63E8) moves it, the ladder is in the build script.
Two code bytes change: NOT cal-only, the class of V57's displacement repoint (in-place, same length).

Related: [[accord-v293-torque-mode-built-cleared-over-one-dissent]] · [[accord-the-relay-is-not-the-instability-mechanism-tier-b-closed]] ·
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]] · [[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]]
