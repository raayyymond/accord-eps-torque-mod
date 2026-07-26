---
name: reference-accord-polarity-gp6752-is-static-boot-config
description: gp-0x6752 (the arb-core "polarity" multiplier, {-1,0,+1}) is a boot-time-parsed, shadow-validated STATIC config constant, not a live per-cycle torque/motor sign — it cannot chatter on a dithering command. Clean negative for the "sign-chatter" hypothesis.
metadata:
  type: reference
---

# gp-0x6752 "polarity" is a static per-boot config constant, not a live signal

2026-07-19/20 tracer pass, GhidraMCP only (no r2/rizin available this session) against
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (STOCK). Dispatched to check whether the
arb-core polarity term is a bare unhysteretic sign multiplier that could chatter on a dithering near-zero
LKAS command (companion to [[reference-accord-arb-neardeadband-sign-latch]]).

## Where it's read (consumer, arb core)
`FUN_00028ea6` @ `0x2a1f2`: `ld.b -0x6752,gp,r13` (SIGNED byte) then `0x2a1f6 mulh r7,r13` (r7=GAIN cal
0xC646C) — polarity multiplies the GAIN cal directly, and that product multiplies the combined command at
`0x2a1fe`. Also validated at function entry (`0x28f22-0x28f2c`, `ld.b` signed, `(polarity+1U)<3` unsigned
trick == polarity ∈ {-1,0,1}) and hard-required nonzero at `0x28f5e-0x28f66` (polarity==0 bails the entire
combined-torque computation for that function, `jr 0x290b0`).

## Where it's written (producers — whole-image search, ONLY 3 functions, byte pattern "6752")
- **`FUN_00048a40`** — a generic table/record parser (`switch` on a record-type byte 0x00-0xC0 read from a
  pointer-walked buffer, populates dozens of unrelated `gp-0x34xx` cal fields and `DAT_fedf4b8x` bitfield
  flags — this is a boot-time CONFIG TABLE loader, structurally unrelated to torque). Only record-type
  **0x54** touches polarity, via a shadow-pair check against `gp-0x4c2d`:
  ```c
  if ((char)psVar10[2] == ',')      { gp-0x6752 = 1;    gp-0x4c2d = 1; }     // record field == 0x2C
  else if ((char)psVar10[2] == -6)  { gp-0x6752 = 0xff; gp-0x4c2d = 0xff; }  // record field == 0xFA (-6)
  else { /* untouched */ }
  ```
  If the shadow pair disagrees first, it calls `FUN_0006b9fa` (mismatch-repair) instead of writing — same
  shadow-lockstep pattern CLAUDE.md documents for `gp-0x4f64`.
- **`FUN_000490ac`** — the table-load driver: shadow-sets `gp-0x6752=1` as a default, then loops calling
  `FUN_00048a40()` (cap 400 iterations) until a parse-done flag is set. **Single caller, `FUN_00057e5e`**
  (xref-confirmed, an init routine — not the torque hot path).
- **`FUN_000497e6`** — a periodic re-validator: re-reads the SAME saved record pointer from the 0x54 parse
  (`gp-0x34b8`) and re-derives polarity from it via the same shadow-check-or-repair pattern every call.
  No static callers found (consistent with this kit's documented indirect-call-table tooling gap), but its
  body (increment a per-slot counter, call `FUN_0001cba6` on mismatch) reads as a periodic
  watchdog/service tick, not a per-torque-cycle function.

**None of the three functions read the LKAS setpoint, driver torque, or motor state.** They read a parsed
config-table record. Value space is exactly `{0 (pre-init sentinel), +1, -1}`.

## Conclusion
Polarity is a **fixed per-vehicle-variant calibration constant** (plausibly LHD/RHD or motor-wiring
convention), loaded once at boot and only re-touched for memory-integrity (shadow-pair repair), never
re-derived from a live signal. **It cannot chatter cycle-to-cycle from a dithering LKAS/torque command** —
the "bare unhysteretic sign multiplier on a dithering signal" hypothesis is refuted for this variable.
The actual sign-flip chatter mechanism in the arb core is the `gp-0x6b30` same-sign latch documented in
[[reference-accord-arb-neardeadband-sign-latch]], which operates on the shaped torque term itself, not on
this polarity constant.

## Confidence
[VERIFIED] — clean, unambiguous decompiled C for all 3 producer functions, whole-image write-site search
(59 total hits for pattern "6752", only 5 are stores, all in these 3 functions), xref-confirmed caller for
`FUN_000490ac`.

## Related
[[reference-accord-arb-neardeadband-sign-latch]] · [[reference-accord-segmentE-arbitration-shaper-dtc-gate-table]]
