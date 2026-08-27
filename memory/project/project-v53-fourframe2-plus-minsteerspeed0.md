---
name: project-v53-fourframe2-plus-minsteerspeed0
description: V53 = FOURFRAME2 byte-for-byte + `0xC62EA` 320→0 (minimum steer speed to 0). BUILT 2026-07-27, UNFLASHED. Supersedes FOURFRAME2 as the flash candidate — one drive answers both open questions.
metadata:
  type: project
---

**V53, built 2026-07-27 on operator instruction ("V38 base + FOURFRAME2 + minimum steer speed 0").
UNFLASHED.**

```
_v53_plain_image.bin  SHA 6be6055357506b87afe21ea622d46bda35ececfe5bb9038834e643d0f0292e1f
39990-TVA,A160-V53-LKAS-4x-V38base-FOURFRAME2-telem-STRB01FIX-authority-refmodel
  -newid0x6a0-0x6a3-mbx16-19-100hz-minsteerspeed0-lockout0xC62EA-320to0-0x13000-0x100000.rwd
                      SHA 29e444ca4a68e4dc1408d62e090cc6372927cb0ae7ca918465e3903125f9e114
```

## What it is
**FOURFRAME2 plus exactly six bytes**: `0xC62EA`/`0xC62EB` (320 → 0) and the CAL-block CRC trailer at
`0xC6FFC`. Cave, hook and MAIN CRC are **byte-identical to FOURFRAME2** — the builder asserts this against
`_vfourframe2_plain_image.bin` rather than trusting it. 855 bytes vs stock (FOURFRAME2 is 853); 737 vs V38.

`builds/v50_v79/build_v53_tva.py` **imports the 774-byte cave from `builds/telemetry/build_vfourframe_tva.py`** instead of re-typing it, so
there is zero transcription surface. Worth reusing as a pattern for any future "existing cave + one cal".

⚠ It does **not** carry the V42 ratchet fix — `0x454FE` stays stock `0x65BA`, asserted. That matches
FOURFRAME on the car today, so V53 is not a regression, but the confirmed one-byte root-cause fix is absent.

## Why 0 and not the previously-recorded suggestion of 64
Stock **already unlocks true standstill**: `gp-0x68b3` (the window bypass) is written in `FUN_0004d0d0`
only when `gp-0x6a62 == 0`, i.e. exactly zero. So stock permits 0 km/h and forbids 1–319 counts. Setting
the LO bound to 0 **removes that discontinuity** rather than moving it — 0 vs 64 differ only over the
0–1 km/h sliver. The old "suggest 64, not 0" note in `docs/STATE.md` predates that reasoning.

## Safety re-verified at build time, in Python, independently of Ghidra
- **Exactly one reader image-wide**, sweeping BOTH V850E2 encodings over `[0x13000,0xC4FFC)`: the `disp|1`
  halfword `0x72EB` occurs **once**, at `0x28EBE` — the displacement of `ld.hu 0x72ea[tp],lp` @`0x28EBC`.
  The single bare-`0x72EA` hit is at **odd** address `0x21167`, so it cannot be an instruction operand.
  (The 6-byte extended-displacement form still carries the low 16 disp bits as an aligned halfword, so the
  same sweep covers it — see [[accord-gp4f60-two-encodings-enumeration-trap]].)
- **LERP-masquerade check passed** (the trap in `docs/handoffs/2026-07/HANDOFF-2026-07-24-low-speed-steer-lockout.md` §4e):
  the nearest `movea …,tp,rX` table base below the lever is `0x7010`, a 4-point record
  (X = 0/640/3200/6400), ending ≥ 0x2DA bytes short. A displacement scan alone cannot rule this out.
- **SNA detection intact** — the `0x7FFF` sentinel still fails the untouched HI bound `0xC62E8` = 12800.
- **`0xC62EE` left stock** and asserted: a permissive on a CAN-commanded assist-shutdown task, never a
  lockout, and never to be raised.
- **Opposite risk class from V40**, which wrote `0xFFFF` into a slew guard so it never fired (snap-to-target
  → DTC 0x1d → motor off). Here nothing is removed from a limiter; a comparison threshold is widened at its
  low end, on a gate whose failing branch only reports status and withholds assist.
- Builder gates all pass: 50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run
  on the readback.

## Why the two changes belong together
The lockout edit **creates the condition the telemetry needs to observe**. On route 13
`STEER_CONTROL_ACTIVE` is a deterministic function of speed (ST=3 *is* the sub-5 km/h gate), so cells B and
C have zero speed overlap and "needs applied torque" cannot be separated from "needs v > 1.4 m/s". One
parking-lot drive on V53 measures `gp-0x6966` (settling the `0xC6AF0` direction), captures all three terms
of the `FUN_0003a382` loop, and fills the empty engaged-at-low-speed cell.

⚠ **Still cannot settle 21 vs 78.91 Hz** — the cave transmits at 100 Hz and samples instantaneously.

## Expected behaviour change
Below ~3 mph the EPS now accepts LKAS torque where it refused. `CP.minSteerSpeed = 0.0`, but the StarPilot
fork runs `steerAtStandstill = False`, so at a dead stop openpilot still will not command. Real window is
roughly 0.1–3 mph — creep, parking lots, stop-and-go — where static-friction steer effort is high.

Related: [[accord-low-speed-lockout-window-c62ea]], [[reference-accord-fourframe-strb-ssam-defect]],
[[reference-accord-vibration-needs-applied-torque]], [[accord-check-build-lineage-before-proposing-lever]].
