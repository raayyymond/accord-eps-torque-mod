---
name: v37-dtc0x49-fix-and-0xc64b8-blast-radius
description: "V36 (debounce-SM off) FLASHED then, mid-drive, threw a BURST of dashboard error lights + dropped LKAS (comma) while base steering stayed fine. Root cause (Ghidra self-verified, 2026-07-14): the debounce SM runs TWO counters off torque gp-0x682f on the same tick — counter A gp-0x6757 (STEER_STATUS=4, 5 cyc) and counter B gp-0x6758 (DTC-0x49, saturates at cal 0xC64E0+0xC64E1=50+50=100 cyc, gate cal 0xC64B8=112). EVERY STEER_STATUS=4 fire/hold branch executes an in-code interlock gp-0x6758=0; that reset was the ONLY thing keeping counter B from saturating. V36 made STEER_STATUS=4 unreachable → interlock never runs → counter B free-runs on sustained torque>112 → 100 cyc (~1s @100Hz) → STEER_STATUS=7 + FUN_00016de6(0x49,1,1,1)=DTC 0x49 → dash lights + openpilot drops LKAS (treats 7 as permanent fault). V37 = V36 + raise 0xC64B8 112→0xFF so counter B can never increment. cal-only, 49/49 CRC. **FLASHED 2026-07-14 → gentle EME RESOLVED on-car (operator-confirmed); no dash-lights regression.** ⚠ 0xC64B8 is ALSO a LIVE torque-arb branch @0x29a78 (accepted side effect). CORRECTION: FUN_0002a30e AND FUN_0002a93a are BOTH DEAD; the live logic is inlined in m_steer_torque_arbitration."
metadata:
  node_type: memory
  type: project
  originSessionId: bb3c56a3-9cc3-4eec-ab08-f3ac2d00eedd
---

**2020 Accord `39990-TVA-A160`, V850E2, stock `code.bin` (gp=0xFEDF8000, tp=0xBF000).** Follow-on to
[[v36-debounce-sm-root-cause-and-build]]. Operator flashed **V36** and reported: **halfway through a drive a
burst of dashboard warning lights flashes and LKAS through the comma stops, but the steering wheel (base power
assist) keeps working.** Ghidra trace (my own decompile + a firmware-codepath-tracer subagent, every
load-bearing claim cross-checked) root-caused it and built **V37** to fix it.

## STATUS UPDATE 2026-07-14 (later) — V37 FLASHED, gentle EME RESOLVED
The operator **flashed V37 and reports the gentle EME is resolved** (the felt sharp wheel-straightening mid-turn
is gone) with **no dash-lights / no LKAS-drop regression** (the V36 DTC-0x49 fault is fixed). This is the
decisive outcome of the V36→V37 discriminating experiment: disabling the `STEER_STATUS` debounce SM (the
`gp-0x682f` torque / `param_1` rate condition) eliminated the felt cut ⇒ the gentle EME **is** driven by that
debounce condition (the [[v36-debounce-sm-root-cause-and-build]] "likely, same-signals" branch is confirmed;
the "separate path" branch is ruled out). The exact motor-zeroing instruction remains unlocated as a *static*
fact but is empirically defeated by the cal disable. Companion artifact: `analysis-2020accord/model/eps_lkas_chain_model.py`
(runnable CAN→motor pseudocode, parameterized for V9/V31/V37).

## Root cause — V36 unmasked DTC 0x49 by removing an in-code interlock
The live debounce SM (inlined in `m_steer_torque_arbitration`) runs **two counters off the same torque channel
`gp-0x682f` on the same tick**:
- **Counter A `gp-0x6757`** → `STEER_STATUS=4` (gentle EME) after **5** cycles; gates = the 7 cals V36 maxed
  (`0xC64B4/B5/B6/B7`, `0xC61C0/C2/C4`).
- **Counter B `gp-0x6758`** → `STEER_STATUS=7` + **`FUN_00016de6(0x49,1,1,1)` = DTC 0x49** after
  **100** cycles (`cal 0xC64E0`+`cal 0xC64E1` = 50+50); increment gate = **`cal 0xC64B8`=112** (untouched by V36).

**The interlock:** every branch that sets/holds `STEER_STATUS=4` also executes `gp-0x6758 = 0` (live stores at
`0x29292`/`0x292b2`/`0x2930e`). In stock, sustained loaded-curve torque trips counter A at cycle 5 and the
`STEER_STATUS=4` fire + its ≤100-cycle hold **zero counter B every cycle** → counter B never reaches 100 →
**DTC 0x49 was structurally unreachable.** V36 raised counter A's thresholds → `STEER_STATUS=4` never fires →
the `gp-0x6758=0` writes never run → counter B free-runs on the still-live `torque>112` gate → saturates at 100
(~1 s @ ~100 Hz) → **DTC 0x49 + STEER_STATUS=7**. Dash lights = the EPS confirmed-DTC; LKAS drop = openpilot
treats `STEER_STATUS=7` as a permanent fault (`steerFaultPermanent`, repo `HANDOFF-2x`), zeroing `latActive`;
base assist survives because 0x49 is a LKAS/assist-monitor DTC, not a hardware shutdown. (The exact in-firmware
MIL/cluster aggregator was not traced — the DTC-set + fault-broadcast is verified; the cluster mapping is the
standard downstream.)

## ⚠ 0xC64B8 blast radius — it is NOT solely the DTC gate (operator-accepted)
Whole-image scan (185,116 instrs). `0xC64B8` has **6 direct byte reads (all `ld.bu`); NO absolute-pointer load;
NO wide `ld.hu`/`ld.w` spanning the byte** (neighbours `0xC64B4/B5/B6/B7` are all single-byte reads):
- `0x2920a`, `0x2921c` — `m_steer_torque_arbitration` **LIVE** = DTC counter-B gate → **intended disable**.
- **`0x29a78`** — `m_steer_torque_arbitration` **LIVE** = **torque-arbitration branch**
  (`torque>112 ? high-torque cutoff : full arb-curve interp`; the dead twin `FUN_0002a93a` sets the main arb
  term `iVar13=0` in the `>112` branch). Raising `0xC64B8`→255 makes `torque>255` never true ⇒ the live arb
  always takes the full-interpolation path for torque in (112,255] — a **drivability change in the loaded-curve
  regime**. **Operator accepted this** (2026-07-14).
- `0x2a3ec`, `0x2a3fe` (`FUN_0002a30e`), `0x2a97a` (`FUN_0002a93a`) — **dead**, inert.

## CORRECTION OF RECORD — FUN_0002a30e AND FUN_0002a93a are BOTH DEAD
Both have **0 callers, 0 xrefs, 0 data-table pointers** (byte-pattern searched both LE entry pointers). Their
logic is **inlined live inside `m_steer_torque_arbitration`** (called every tick by `w_steer_control_task@0x2214a`):
the debounce SM at `0x29120–0x2931e`, the arb curve around `0x29a5c–0x2a2xx`. Almost certainly a compiler
inlining artifact (out-of-line copies emitted then not dead-stripped; register-renamed but logically identical).
**This supersedes the `[[v36-debounce-sm-root-cause-and-build]]` / handoff / CLAUDE.md framing that calls
`FUN_0002a30e` "the status producer" — that standalone copy never executes.** gp-0x6758 is the DTC-0x49 fail
counter (an older firmware-tracer memory mislabeled it a "ramp gain accumulator").

## V37 build — the fix (BUILT, verified, UNFLASHED)
`analysis-2020accord/builds/v18_v49/build_v37_tva.py` → `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V37-V36-DTC0x49-OFF-torqueMax255-rateMax65535-dtcGate255-0x13000-0x100000.rwd` (+ `../accord-firmware/analysis-2020accord/_v37_plain_image.bin`).
**V37 = V36 + raise `0xC64B8` 112→`0xFF`** ⇒ `gp-0x682f`(≤255) can never exceed it ⇒ counter B never increments
⇒ DTC 0x49 can never fire (STEER_STATUS=4 stays disabled, so nothing re-arms the interlock; gp-0x6758 sits at 0).
**Cal-only, 0 code edits.** Verified: 49/49 CRC, `decode==patched`, both FSM code ranges byte-identical to stock,
all 3 live `0xC64B8` reader instructions untouched; `0xC6312` left stock 320; counter-B sat cals `0xC64E0/E1`
untouched. **V37 vs V36 = exactly 5 bytes: `0xC64B8` + its CRC `0xC6FFC`** (the `0xC4FFC` CRC is unchanged since
`0xC64B8` isn't in that block). 42 total byte-diffs vs stock (V36's 41 + `0xC64B8`). **UNFLASHED** — study
artifact until operator names file + bus.

**Trade-offs (operator-accepted):** (1) genuine DTC-0x49 fault detection is now disabled; (2) the live arb
high-torque cutoff at `0x29a78` is defeated for torque in (112,255]. **Deeper open item unchanged:** the actual
LKAS-motor-zeroing instruction of the felt gentle EME is still unlocated — V37 (like V36) is a discriminating
experiment on the DTC/STEER_STATUS side, not proof the felt cut is fixed. NEXT = flash V37, drive the loaded-curve
section, confirm (a) no dash-lights/LKAS-drop and (b) whether the felt wheel-straightening persists.
