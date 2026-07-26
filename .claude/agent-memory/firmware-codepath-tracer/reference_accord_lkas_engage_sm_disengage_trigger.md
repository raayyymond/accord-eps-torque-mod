---
name: reference-accord-lkas-engage-sm-disengage-trigger
description: Accord TVA-A160 gentle-EME = engage-SM disengage FUN_00040d58 when gp-0x6a62>=cal 0xC6312 (stock 320, no debounce). gp-0x6a62 = voter MAX of 5 coil tracks, rising-edge UNFILTERED, clamp 32000. Scale needs live read (NOT the CAN sensor). Lever = raise 0xC6312. 2026-07-02 V33 DISABLES it: 0xC6312 -> 65535 (u16 max, ld.hu/unsigned) -> torque disengage never fires (invalid-sensor sentinel gp-0x6a62==0xffff kept). Cal reads at 0x40db8/dd0/df4 (NOT 0x40dae/dc6/dea = gp-0x6a62 value reads); radare2 v850.gnu-verified, exactly 3 readers / 0 writers / no twin.
metadata:
  type: reference
---

# Accord 39990-TVA-A160 LKAS engage-SM disengage trigger (gentle EME / no_torque_alert_2)

Stock code.bin (/master.bin, 2113 fns). gp=0xFEDF8000, tp=0xBF000. [V] = disasm-verified. Updated 2026-06-30.

## The trigger [V]
`FUN_00040d58(param_1)` returns the next engage state; the engaged handler `FUN_00041222` (state 7) calls it with
param=2. **param 2 (ENGAGED) and param 3 (HOLDING) disengage on exactly one condition:**
`gp-0x6a62 >= cal 0xC6312` (`if (gp-0x6a62 != 0xffff && gp-0x6a62 < 0xC6312) stay; else return 2 = disengage`).
**No debounce.** The **cal** `0xC6312` is read (`ld.hu 0x7312[r5=tp]`) at exactly 3 sites, all in
`FUN_00040d58` (`0x40db8/0x40dd0/0x40df4`). ⚠ **Corrected 2026-07-02 (radare2 v850.gnu):** the neighboring
`0x40dae/0x40dc6/0x40dea` are the `gp-0x6a62` **value** reads (`ld.hu -0x6a62[r4=gp]`), NOT the cal — the
base-register field (r5=tp vs r4=gp) was decoded from the raw instruction bytes. Whole-image enumeration this
session confirmed **exactly 3 readers, 0 writers, no absolute/indexed access, no int/float twin** for 0xC6312.

| param | gate (signal >= cal -> disengage) |
|---|---|
| 1 (engaging) | gp-0x6a60>=0xC6310=1600, gp-0x4f68>=0xC61CE=4096, gp-0x6ba4>=0xC61CC=3584, then gp-0x6a62<0xC6312 to deliver |
| 2,3 (ENGAGED/HOLDING) | **gp-0x6a62 >= 0xC6312=320 ONLY** |
| 4 (re-arm) | gp-0x6a60>=0xC6310 ... |

## Corrections (2026-06-30) to earlier notes
- **`FUN_00040e74` is NOT the signature writer** — it is a one-liner `gp-0x35b5 = gp-0x35b6` (commits the substate
  byte the decider set). The dispatcher state `gp-0x679c` is driven by `FUN_00040d38(n)` from `FUN_00041222`.
- **gp-0x6806/6807/6809** (CONTROL_ACTIVE / STEER_STATUS / deliver flag) have **no gp-relative store** in 185k
  instructions — written via a pointer/struct path (unresolved). Does not weaken the lever: in ENGAGED/HOLDING the
  only disengage condition is the 320 gate.

## SCALE CAVEAT — RESOLVED [V]
`gp-0x6a62` = voter `FUN_00041eec` output = **MAX of the 5 column-coil track magnitudes** (each raw_ADC×41/64),
**rising-edge UNFILTERED** (the only slew limit is decay, 16/cyc cal 0xC64ED). So on a torque spike it tracks the
instantaneous peak coil — explaining why 320 (a small number) trips on a hard turn/bump even though it's max-of-5.
**The 320 vs road-data (CAN ~1239–2290) mismatch is a SCALE difference, not a lag:** `gp-0x6a62` and the CAN
`STEER_TORQUE_SENSOR` are **two DIFFERENT sensors** (sensor A vs sensor B) with independent calibration —
[[reference-accord-dual-torque-sensor-architecture]]. There is NO static bridge; the gate scale must be pinned by
a **live RAM read of gp-0x6a62 (0xFEDF159E)**. The earlier "either gp-0x6a62 is a dispersion metric or it's
gp-0x6a60>=1600 that trips" speculation is closed: it is the max-coil at 320.

## Signal identities [V]
- `gp-0x6a62` (0xFEDF159E) = voter MAX of 5 sensor-A coil tracks; shadow twin `gp-0x4cae` (0xFEDF35B2); clamp 32000.
- `gp-0x6a5e` (0xFEDF15A2) = voter AVG/voted twin; the assist-curve axis (table 0xce578 [612..1238] increasing,
  ×'d in `FUN_00034a72`) — proves sensor A is **driver column torque**.
- `gp-0x6a60` (0xFEDF15A0) = ABS magnitude of gp-0x6a56 (angle-rate-derived); used by engage-attempt gate 0xC6310.

## The lever
Raise cal **`0xC6312`** (stock 320, 2-byte LE). Lockstep-clean: 3 readers all in `FUN_00040d58`, no int/float
twin, value appears once in the cal block → cal-only edit, recompute the 0xC6000-block CRC. Re-engage ramp byte
cal `0xC64DE = 17`.

## ✅ 2026-07-02 — V33 = DISABLE the torque disengage (0xC6312 320 → 65535, u16 max)
The operator judged the gentle-EME trigger scenario always-unsafe for hands-off LKAS and directed disabling it.
`0xC6312` is `ld.hu` (unsigned 16-bit) compared unsigned (`bnl`), so its datatype max is **0xFFFF = 65535**;
`gp-0x6a62` is voter-clamped to 32000, so at 65535 `gp-0x6a62 < threshold` is unconditionally true → the
torque-magnitude disengage **never fires**. The separate `gp-0x6a62 == 0xffff` invalid-sensor sentinel
(0x40dca/0x40dce) is a SENSOR-FAULT path and is **left intact**. **V33 = `build_v33_tva.py`** = V31 + this one
cal edit; cal-only (decider code byte-identical to stock), 49/49 CRC, V33-vs-V32 delta = only the 2-byte
threshold + its block CRC, **UNFLASHED**. Handoff `docs/HANDOFF-2026-07-02-v33.md`. Trade: driver can no longer
wrest LKAS authority via column torque through this gate (openpilot brake/cancel/override still works upstream).
