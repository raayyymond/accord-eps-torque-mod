# Steering Torque-Demand Task Hunt — 2020 Accord EPS (V850E2)
# Date: 2026-05-25
# Target: function that reads LKAS CAN torque (0xFEDF68CC) and/or column-torque ADC,
#         applies assist curve, writes q-current demand for FOC loop.
# Known-excluded: 0x6404c, 0x6428e, 0x65afe, 0x68f52, 0x710d4, 0x711f8, 0x71272,
#                 0x6c5ce, 0x61614, 0x1492a, 0x1ce68, 0x1ddd0, 0x197d0, 0x197ea, 0x6d116

## XRef scan — absolute readers of LKAS frame addresses
### 0xFEDF68CC (STEER_TORQUE staged, int16 big-endian)
  Result: 0 Ghidra xrefs — accessed via GP-relative instruction, not tracked as data ref.
### 0xFEDF68DC
  Result: 0 Ghidra xrefs.
### 0xFEDF68E4
  Result: 3 xrefs:
    0x1de52 READ  from FUN_0001ddd0 (excluded CAN frame copy loop; reads _DAT_fedf68e4 as src ptr)
    0x1df44 WRITE from FUN_0001df1c (CAN RX ISR: sets _DAT_fedf68e4 = 0xFEDF68CC)
    0x1e06a WRITE from FUN_0001e044 (CAN RX ISR: sets _DAT_fedf68e4 = 0xFEDF68CC)
  NOTE: FUN_0001df1c and FUN_0001e044 are CAN peripheral receive ISRs that stage the
  incoming CAN frame pointer to 0xFEDF68CC and then call FUN_0001ddd0 to copy it.
  The LKAS torque decode (big-endian byte-swap + scaling) happens downstream in a
  CAN callback dispatched from FUN_0001ddd0 via table at DAT_000b73fc.

## Task Dispatcher Topology [VERIFIED in-disasm]
FUN_0002214a (1ms periodic scheduler, gp-0x6d28 tick counter)
  called by: (ISR / hardware timer, no Ghidra CALL xref)
  -> FUN_0006bb08 (main task dispatcher, CALL at 0x221e0)
       -> FUN_0006bab4 (EPS state machine driver)
            -> FUN_00086206 (watchdog counter)
       -> FUN_0006bea8 (sub-dispatcher for mode bits 0xd38)
            -> FUN_000650a4(1)   relay/contactor control
            -> FUN_0005c090(2)   temperature safety check
            -> FUN_0006651e(3)   *** STEERING TORQUE-DEMAND TASK *** [PRIMARY CANDIDATE]
       -> FUN_00065eda(0x10)     motor computation outer shell
            -> FUN_000197d0(0xf) sensor-validity bit-test (reads gp-0x6d78)
            -> FUN_00069272()    rotor flux angle / Park transform
            -> FUN_00068f3e()    resolver quadrant update wrapper
            -> FUN_00068cf4()    demand sanity checker
            -> FUN_00069046/72() 3-phase PWM commit

## PRIMARY CANDIDATE: FUN_0006651e [INFERRED — strong evidence, not byte-traced to gp-0x1734]
Address: 0x6651e
Called from: FUN_0006bea8 at 0x6bee0 (task slot 3, when param & 0xd38 != 0)
Evidence:
  - Dispatches to FUN_0006634e() (assist curve interpolation) when gp-0x4e65 == 0 (assist-active)
  - Dispatches to FUN_00068dfe() (soft-start ramp) when gp-0x4e65 == 1 or 2
  - Reads gp-0x34ac struct (+10 = temp byte) for thermal compensation
  - Computes float fVar3 = (temp-70)^2 * 1.7e-6 + (temp-70)*0.001 + 0.968
  - On assist completion (gp-0x2a40 == 1): clamps gp-0x4fc0/4fbe/4fc2/4fc4 to calibrated limits
  - Commits via FUN_00069046(), FUN_00069072(), FUN_0005e0aa() — 3-phase PWM hardware write
  - Tracks EPS assist-mode state in gp-0x4e65

## ASSIST CURVE SUB-FUNCTION: FUN_0006634e [V] verified-in-disasm
Address: 0x6634e
Called from: FUN_0006651e at 0x6660e (only caller)
Evidence:
  - Reads struct ptr iVar15 = *(int*)(gp-0x34ec) — "lower" assist table row (gp = 0xFEDF8000)
  - Reads struct ptr iVar14 = *(int*)(gp-0x34e8) — "upper" assist table row
  - Struct layout: +4 = ushort torque value, +6 = ushort speed, +0xc/+0xd = gain bytes, +10 = temp index
  - Interpolates between rows based on temperature delta (iVar14[10] - iVar15[10])
  - Writes gp-0x4fb8 / gp-0x4fbc / gp-0x4fb6 / gp-0x4fba (torque+speed cmds per axis)
  - Writes gp-0x4e5b, gp-0x4e5c (gain outputs)
  - Calls FUN_000690f8() which converts to base duty cycles:
      gp-0x4fc0 / gp-0x4fbe = base duty ch0
      gp-0x4fc2 / gp-0x4fc4 = base duty ch1

## SECONDARY (downstream consumer): FUN_00065eda [V] verified-in-disasm
Address: 0x65eda
Called from: FUN_0006bb08 at 0x6bc50 (task slot 0x10, runs same cycle after 0x6651e)
Evidence:
  - Reads gp-0x5000, gp-0x4ffe (per-axis current demands)
  - Reads gp-0x2a3c, gp-0x2a3a (duty-cycle scalars from FUN_0006634e)
  - Computes total current magnitude sqrt(gp-0x4fe4^2 + gp-0x4fec^2) -> gp-0x4ff4
  - Scales and clamps to [tp+0x59a8 .. tp+0x59a6]
  - Final commit: FUN_00069046/69072/5e0aa

## OPEN QUESTION: Path from gp-0x1734 (LKAS CAN torque) to assist table pointer gp-0x34ec
The struct pointers at gp-0x34ec and gp-0x34e8 are set by an as-yet-untraced function
that indexes the assist table using the current column/CAN torque value.
Column torque ADC confirmed at gp-0x4e8c / gp-0x4e8a / gp-0x4e88
  (read by FUN_00062948 torque-sensor plausibility check).
LKAS CAN torque at gp-0x1734 is GP-relative; no Ghidra xref but CAN staging path confirmed:
  HW CAN RX -> FUN_0001df1c / FUN_0001e044 -> sets _DAT_fedf68e4 = 0xFEDF68CC
            -> FUN_0001ddd0 -> callback table 0xb73fc[CAN_ID] -> FUN_0001debc dispatcher
NEXT STEP: Identify the function that writes *(int*)(gp-0x34ec). Candidates:
  - A function in the 0x60000-0x65000 range not yet decompiled
  - Could be inside FUN_0006bab4 chain or a CAN callback
  TOOL: xrefs_list with DATA/WRITE type on absolute 0xFEDF4B14 (= gp-0x34ec)
        OR decompile FUN_0006404c (ADC ISR) head to see if it also updates the assist pointer
