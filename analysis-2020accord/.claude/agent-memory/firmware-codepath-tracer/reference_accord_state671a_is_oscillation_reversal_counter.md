---
name: reference-accord-state671a-is-oscillation-reversal-counter
description: gp-0x671a (assist_state) is a hard-reversal COUNTER of gp-0x6c2c (a filtered MOTOR RATE; its source gp-0x4f50 is a wrap-corrected first difference, resolved 2026-08-10) that RISES during oscillation and saturates >=5 within ~125-150ms of sustained 18-21Hz reversal, not a smooth-steering persistence ramp that falls during oscillation.
metadata:
  type: reference
---

FUN_000428d4 (writer of gp-0x671a, "assist_state") is a 3-state (0/1/2) hard-threshold-reversal
detector on gp-0x6c2c, gated to run when FUN_00046ea6(5)==0. Disasm-verified at 0x428d4-0x42a12.

**Core FSM** (states at gp-0x67df, dwell counter gp-0x6759, reversal-run counter gp-0x357c):
- State 0 (neutral): resets both counters every tick; goes to state 1 if CUR>T, state 2 if CUR<-T,
  else stays 0.
- State 1/2 (sticky): stays in state unless (a) dwell counter reaches HYST with no reversal -> decays
  to state 0 (counter_B untouched, cleared next tick at state-0 top), or (b) CUR crosses the OPPOSITE
  threshold (hard reversal) -> flips state, resets dwell, INCREMENTS counter_B by 1.

Byte-read constants (code.bin): T = tp+0x720a = 0xC620A = **12800**; HYST = tp+0x74dd = 0xC64DD =
**50 ticks**; CEIL = tp+0x74fa = 0xC64FA = **5** (used as a comparison threshold by r24/r26, NOT a
hard clamp on gp-0x671a itself — see below).

**gp-0x671a = a function of counter_B** (the reversal-run count), via LAB_000429a0 tail logic gated
by gp-0x6a5e (SIG) vs SPD_THRESH1=tp+0x72de=0xC62DE=640, and a 5000-tick(tp+0x7270=0xC6270) decay
timer on the slow path. 🛑 **CORRECTED 2026-08-10: `gp-0x6a5e` is VOTED VEHICLE SPEED, not driver
torque.** This paragraph previously ended "— NOT vehicle speed", which was WRONG; settled by
`memory/reference-accord-gp6a5e-is-speed-reclassifies-v44-v47.md` (2026-07-29, two independent traces
+ byte-verified pointer chase), and that same error already cost the kit two flashed builds (V44, V47).
⊕ **This entry contained its own refutation**: the threshold it names is `SPD_THRESH1` = `0xC62DE` =
**640**, which at 64 ct/km/h is exactly **10 km/h** — a speed threshold, correctly named, while the
prose denied it. The writer (`FUN_00041eec`@`0x42342`, rate-limited) is unchanged and correct. Since uVar12(counter_B)!=0 forces the
fast "if" branch on ANY tick where a reversal just happened, this fast path dominates during a
sustained oscillation almost regardless of driver-torque level. Under this path, gp-0x671a directly
tracks counter_B once counter_B exceeds the previous stored assist_state (own byte-sim showed it is
NOT hard-clamped to 5 and can climb further — clamp-to-5 only engages in the specific case where a
NEW counter_B <= the OLD assist_state AND that old value was already >=5, a sticky-floor not a
ceiling). For the r24/r26 consumers this doesn't matter: they only test `gp-0x671a < 5`, and the
>=5 condition, once reached, cannot fall back below 5 while reversals keep recurring at least once
every 50 ticks (impossible to un-trip mid-oscillation at any freq >10 Hz).

**CRUX (Python integer-arithmetic simulation, 1kHz tick, synthetic sinusoid on gp-0x6c2c at
amplitude 1.5x-1.05x T):** half-period at 18-21 Hz is 23.8-27.8 ms, well under HYST=50ms, so the
FSM NEVER times out to neutral during sustained oscillation — it keeps counting reversals. counter_B
(and gp-0x671a) reaches 5 within 125-150ms of oscillation onset (125ms@21Hz, 146ms@18Hz) and cannot
drop below 5 for as long as the oscillation continues. Below-threshold amplitude (0.9x T) never
leaves state 0 at all (gp-0x671a stays 0) — confirming the threshold-crossing requirement is a hard
gate, not just a bias.

**Consequence for r24/r26 (FUN_0003aa2c, torsion-bar-rate lanes scaling shared r1=clamp(gp-0x4f62,
+-5120)):** BOTH lanes select a FIXED, elevated calibration when gp-0x671a>=5, and fall back to a
mode-indexed LERP table when <5 — CORRECTING an earlier (unverified) framing that had r26's priority
reversed. Disasm-confirmed priority (register-level, both chains, at 0x3a98-0x3ac16):
```
r24: gate_671d!=0 -> tp+0x7442(0xC6442)=1024
     elif gate_683c!=0 -> tp+0x7446(0xC6446)=512      [dead, 0 writers of gp-0x683c program-wide]
     elif gp-0x671a>=5 -> tp+0x7440(0xC6440)=2048
     else -> LERP (gp-0x6e40/-0x6e38/-0x6e32/-0x6e3a, axis=clamp(gp-0x6ac0,0,0x32c8))
r26: gate_683c!=0 -> tp+0x7444(0xC6444)=512            [dead, same gate as above]
     elif gp-0x671a>=5 -> tp+0x743e(0xC643E)=1536
     else -> LERP (gp-0x6e30/-0x6e2a/-0x6e22/-0x6e28, same axis)
```
gate_671d (gp-0x671d) IS live (2 writers: FUN_0003bcb2, FUN_00041d56) and takes priority over the
state>=5 arm for r24 only; r26 has no such override (its only higher-priority gate is the dead
gate_683c), so **r26's state>=5 arm (cal 0xC643E=1536) is a clean, always-effective oscillation
response** whenever gp-0x671a saturates.

**Safety check on cal 0xC643E:** single reader program-wide (FUN_0003aa2c@0x3ab68 only; other
`743e`/`6442` hits are branch-target address literals, correctly excluded). No float mirror found.
gp-0x671a itself, however, has a WIDER blast radius than r24/r26 — also read by FUN_0003a382 (the
unfiltered residual lane, [[reference-accord-fun3a382-unfiltered-residual-lane]]), FUN_000352b4,
FUN_00035b20, FUN_00036c12 — so touching gp-0x671a's PRODUCTION (T, HYST in FUN_000428d4) would
ripple beyond r24/r26; touching the CONSUMER cal 0xC643E alone does not.

**Open / not resolved this session:**
- ✅ **RESOLVED 2026-08-10 — `gp-0x4f50` IS A RATE, NOT AN ANGLE.** This bullet previously read
  *"consistent with a MOTOR/RESOLVER ELECTRICAL-OR-MECHANICAL ANGLE"*, hedged as "an INFERENCE from
  usage context, not a labeled confirmation". **The hedge was right and the inference was wrong.**
  Raised by TorquePath, **decompile-verified by me** (`FUN_00068f52`, whole body):
  ```c
  uVar1 = u16(gp-0x29c2);                             // PREVIOUS raw angle
  iVar2 = param_1 - (uVar1 == 0x8000 ? param_1 : uVar1);   // FIRST DIFFERENCE
  if (iVar2 < 0x2001) { if (iVar2 < -0x2000) iVar2 += 0x4000; } else iVar2 -= 0x4000;  // WRAP, mod 0x4000
  iVar3 = (iVar2 * 120000 + round) >> 0xe;            // x120000 >> 14 = x7.32421875
  iVar2 = clamp((s16(gp-0x4f4e) + iVar3) / 2, ±13000);// 2-point boxcar
  gp-0x29c2 = param_1;  gp-0x29c4 = iVar2;  gp-0x4f4e = iVar3;
  ```
  **You only wrap-correct the difference of a modular quantity** ⇒ the ANGLE is `param_1`/`gp-0x29c2`
  (16384 counts/rev); **`gp-0x4f50` is its derivative.** The old reading conflated the function's INPUT
  with its OUTPUT. ⊕ Two corroborations an angle fails: `FUN_00068fbe` plausibility-checks |value|
  against `0xC491A`=5500 / `0xC491C`=5000 (a wrapping angle would trip that every revolution), and
  `FUN_00041464` **EMAs** it (nonsense across a wrap discontinuity). ⊕ The sin/cos evidence was never
  discriminating — π/180 converts deg **or** deg/s.
  ⊕ **Detail TorquePath's paraphrase dropped:** the `uVar1 == 0x8000` special case makes the difference
  identically 0, so **0x8000 is an INIT/INVALID sentinel on the stored angle** and the first tick after
  it yields rate 0 rather than a bogus huge first difference.
  ⊕ **Scale, closed form:** `gp-0x4f50` per °/s of the angle's own units = `333.333 / f_tick_Hz`. At
  **1 kHz** the inherited **4.7121 ct/(°/s)** implies a wheel→angle ratio of **14.14**; the ±13000 clamp
  is then 10.83 % of a revolution per tick. Both are physical at 1 kHz and not at 100 Hz ⇒ **independent
  corroboration of 4.7121 AND of the 1 kHz tick.** ⚠ 14.14 is plausible only if the 16384 counts are per
  **MECHANICAL** revolution; if they are **electrical**, the implied gear ratio would be 14.14/pole-pairs
  ≈ 3, which is not physical for a column EPS. **Pole-pair count not extracted — flagged, does not
  affect the rate identity.**
  **The amplitude of gp-0x6c2c during the real 18-21Hz steering vibration is UNKNOWN** — the crux
  simulation above is only valid if the real signal's rate excursion exceeds +-12800 in its native
  units each half-cycle; this is the single biggest unverified link in the chain.
- gp-0x6b5e (r26's OTHER gate, zeroes the LERP-path averaging when gate_6b5e!=0 AND a state-selected
  flag tp+0x7136/0x7138==1): producer is FUN_000361c8, itself a LERP-table output (axis gp-0x6bda,
  sign-flipped by gp-0x6bf0) tested as a boolean (nonzero). gp-0x6bda/gp-0x6bf0 are both widely shared
  across the FUN_0003aa2c-adjacent gain-shaping cluster (FUN_00035e00/FUN_00036022/FUN_000360fe/
  FUN_00036388/FUN_0003a382/FUN_00042af8/FUN_00043e44 among others) — not independently identified.
- No gp-0x6806 (STEER_CONTROL_ACTIVE) or other LKAS-active read exists anywhere inside FUN_0003aa2c
  or FUN_000428d4 (program-wide search of both operands, clean negative, both functions absent from
  the 7-function reader set of gp-0x6806). The closest thing to a "driver state" gate inside this
  path is gp-0x6a5e (voted VEHICLE SPEED -- corrected 2026-08-10, see above), not an LKAS/hands-off flag.
