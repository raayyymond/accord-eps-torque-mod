---
name: v36-debounce-sm-root-cause-and-build
description: "Gentle-EME root cause RE-LOCATED (2026-07-14, route 7f V31P-V2 telemetry + Ghidra, self-verified): it is the DEBOUNCE STATE MACHINE in FUN_0002a30e (+ inline twin in m_steer_torque_arbitration @0x29210), which sets STEER_STATUS=4 only after 5 sustained cycles (cal 0xC64E2=5, counter gp-0x6757) of (torque gp-0x682f>cal 0xC64B4=112 OR angle-rate param_1>cal 0xC61C0=1600). CORRECTIONS: gp-0x6809 (prior 'deliver-flag cut anchor') has ZERO writers = dead code; decider 0xC6312=320 torque-MAX gate fires ~10Hz benign, NOT the trigger (so V33's disable was wrong gate); V31P-V2's 5 gate flags are non-discriminating (steady 10Hz, nothing rises at the cut). V36 BUILT = V31 + these torque/rate cals raised to unsigned max (0xFF/0xFFFF), cal-only, 49/49 CRC, UNFLASHED."
metadata:
  node_type: memory
  type: project
  originSessionId: bb3c56a3-9cc3-4eec-ab08-f3ac2d00eedd
---

**2020 Accord `39990-TVA-A160`, V850E2, stock `code.bin` (gp=0xFEDF8000, tp=0xBF000).** Session 2026-07-14
analyzed route **7f** rlogs (V31P-V2 flashed; StarPilot NOT updated, so flags decoded from raw CAN 330 bus 1)
and traced the firmware in Ghidra (subagent + my own verification of every load-bearing claim).

## Root cause (re-located — supersedes the decider-gate framing)
The gentle EME (`STEER_STATUS=no_torque_alert_2`, felt as a **sharp slight wheel-straightening mid-turn** —
see [[gentle-eme-fires-on-saturated-lkas-command]]) is produced by a **debounce state machine** that exists in
TWO functions reading the SAME cals and both writing STEER_STATUS byte `gp-0x6807`:
- **`FUN_0002a30e`** (0x2a30e): status producer. Rise cond @0x2a420; hold @0x2a49a; fires `mov 0x4;
  st.b -0x6807` @0x2a46a/0x2a4e6.
- **`m_steer_torque_arbitration`** (~0x29210 inline twin): rise @0x2923e, hold @0x292b8.

Mechanism (byte-verified, both branches, unsigned `ld.bu/ld.hu` + `cmp;bh`): a signed counter **`gp-0x6757`**
starts at **−cal 0xC64E2 (=5)** and only advances while the qualifying condition holds; STEER_STATUS=4 fires
after **5 consecutive qualifying cycles**, then holds via seed cal 0xC64DF=100. Qualifying condition:
`gp-0x682f > cal[0xC64B4=112]  OR  param_1 > cal[0xC61C0=1600]  OR (param_2 && secondary AND-terms on
0xC64B6/B7 & 0xC61C2/C4)`. **`gp-0x682f`** = `min(|arb signal r15|>>5, 255)` (TORQUE channel, made in
m_steer_torque_arbitration @0x29068). **`param_1`** = an angular-RATE magnitude (threshold 1600 == the
decider rate gate value); clamped ≤65535. So the EME = a **sustained (≥5-cycle) high-torque OR high-rate
excursion** (loaded curve + bump) surviving the debounce — unifying the long torque-vs-rate debate.

## Corrections of record (all self-verified in Ghidra this session)
1. **`gp-0x6809` = DEAD CODE.** 0 writers in all 185,116 instrs (4 `ld.bu` reads in m_steer_torque_arbitration,
   no stores; `cmp 0x1,lp / bne` @0x29768 bails every cycle). The 2026-07-06 gating-map Stage-E1 claim
   ("deliver-flag gp-0x6809≠1 = the physical cut") is **refuted**. Do not anchor future telemetry on it.
2. **STEER_STATUS=4 is a lagging REPORT**, not the torque cut (subagent Q2 + my verify). The instruction that
   actually zeroes the LKAS motor term during the felt cut is **still unlocated** (open question).
3. **Decider `0xC6312`=320 torque-MAX gate (r12==2 in FUN_00040d58 @0x40dd6→0x40e64) fires ~10 Hz benign**,
   957× in route 7f, and does NOT correlate with the cut. V33's 320→65535 disabled the WRONG gate. The hook is
   correctly placed (verified 0x40dd6 disengage path reaches the 0x40e64 store); it's just not the trigger.
4. **V31P-V2's 5 gate flags are non-discriminating**: all fire on a steady ~10 Hz benign cadence; pre-cut
   200ms firing rate ≈ whole-drive baseline; nothing rises at either STEER_STATUS=4 edge. Cuts don't even land
   on the drive's CAN torque/rate peaks (2007/1551 vs max 4770; 24/34°/s vs max 304°/s) → trigger is an
   internal signal invisible to CAN and uncaught by the 10 Hz bits. See [[v31p-gateflags-330-piggyback-built]].

## V36 build (this session)
`analysis-2020accord/build_v36_tva.py` → `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V36-V31-debounceSM-OFF-torqueMax255-rateMax65535-0x13000-0x100000.rwd`.
**V36 = V31 (all cals unchanged) + disable the debounce-SM torque & rate conditions**: bytes 0xC64B4/B5/B6/B7
112/96/54/64→**255 (0xFF)**, u16s 0xC61C0/C2/C4 1600/896/1280→**65535 (0xFFFF)**. Unsigned compares ⇒ these
`cal<signal` tests become permanently false ⇒ the debounce counter can never advance ⇒ STEER_STATUS=4 can
never be produced by EITHER function. **Cal-only, 0 code edits (both FSM functions byte-identical to stock,
independently diffed), 49/49 CRC, decode==patched, UNFLASHED.** Left stock deliberately: 0xC64B8=112 (feeds
the SEPARATE gp-0x6758 counter → STEER_STATUS=7 + DTC 0x49 fault path, not the gentle EME) and 0xC6312=320
(V31 base; not the trigger). Blast radius verified contained: 0xC64B4-B7 & 0xC61C0/C2/C4 are read ONLY by the
two FSM functions.

⚠ **V36 is a DISCRIMINATING EXPERIMENT, not a guaranteed fix** (honest status): it provably kills the
STEER_STATUS=4 debounce SM, but because the actual motor-zeroing path (correction #2) is unlocated, IF the felt
assist-drop is driven by this same gp-0x682f/param_1 condition (likely — same signals/arbitration function) V36
eliminates the gentle EME; IF the felt straightening persists with NO STEER_STATUS=4, that result proves the
assist-drop is a separate path. NEXT = flash V36 (operator names file+bus), drive the 5:27 route section, check
whether the wheel-straightening is gone.

## ⚠ UPDATE 2026-07-14 (later) — V36 FLASHED → DTC-0x49 dash-lights REGRESSION → V37. See [[v37-dtc0x49-fix-and-0xc64b8-blast-radius]].
Operator flashed V36; **mid-drive a burst of dashboard warning lights flashed and LKAS (comma) dropped, base
steering fine.** Root cause: the SAME function runs a SECOND counter `gp-0x6758` (DTC-0x49, saturates at
`cal 0xC64E0`+`cal 0xC64E1`=100 cyc, gate `cal 0xC64B8`=112) whose ONLY reset was the in-code interlock
`gp-0x6758=0` that every STEER_STATUS=4 branch executes. V36 killed STEER_STATUS=4 → interlock never runs →
counter B free-runs on sustained torque>112 → DTC 0x49 + STEER_STATUS=7 (openpilot drops LKAS). So **leaving
0xC64B8 stock did NOT preserve fault detection harmlessly — it left the fault path live with its safety-relief
removed.** **V37 = V36 + 0xC64B8→0xFF** fixes it (counter B never increments). Two framing corrections from the
V37 trace: **`FUN_0002a30e` is DEAD** (0 refs) — the live producer is the inline twin in
`m_steer_torque_arbitration`; and **`0xC64B8` is ALSO a LIVE torque-arb branch @0x29a78**, not solely the DTC
gate (operator accepted that side effect). Full detail + build verification in the V37 memory.
