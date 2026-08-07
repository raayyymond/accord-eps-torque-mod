---
name: reference_accord_dtc18_requires_prior_reset_not_live_trippable
description: DTC 0x18/fault_id 24 is a BOOT-TIME reset-cause REPORT, not a live per-cycle deadline monitor. FUN_00014b3e (the gp-0x68b7 4-task liveness watchdog, TAUA1I1) does NOT itself call the DTC latch chain -- it calls FUN_00014af6(3), which writes a persistent NVM cause-code (peripheral-ID 0xE) and runs a multi-ten-thousand-tick shutdown/reset sequence (FUN_00060c9a). The actual FUN_00016de6(0x18,...) hard-latch call lives in a DIFFERENT function, FUN_00014ba0, reached only via state-1 processing in the master fault dispatcher FUN_00019f7c (task1/1kHz), and fires conditionally on FUN_0005e662()'s read of that same NVM cause-code. Refines/extends reference_accord_dtc18_cadence_watchdog.md -- does not contradict its gp-0x68b7/4-task-bitmask mechanics, but corrects the implicit assumption that a missed window directly latches DTC 0x18 in the same cycle.
metadata:
  type: reference
---

# DTC 0x18 (fault_id 24) mechanism, corrected -- traced 2026-08-06, stock code.bin

Built while evaluating whether V75's cave growth (45B->68B) could have tripped the cadence watchdog and
caused the V75 stoplight-launch hard fault. Method: decompile-first throughout (`decompile_function`),
`get_function_callers` to walk the chain, `get_xrefs_to`/byte scans to confirm addresses. `gp=0xFEDF8000`,
`tp=0xBF000`.

## The chain, hop by hop [EVIDENCE, fresh decompile this session]

```
EIIC 0x470 (TAUA1I1) -> FUN_00014b3e   [4-task liveness check, per reference_accord_dtc18_cadence_watchdog.md]
  if gp-0x4308==0 (inhibit off) and (gp-0x68b7 & 0xF) != 0xF (not all 4 tasks ran this window):
      _DAT_fedf3cf4 = EIPC            ; snapshot the faulting PC
      FUN_00014aa4(gp-0x430c)         ; store a param
      FUN_00014af6(3)                 ; <-- does NOT call FUN_00016de6 anywhere in this chain
  gp-0x68b7 = 0                        ; clear for next window, unconditionally

FUN_00014af6(param_1=3):
  FUN_00019760(); FUN_0005e0c8(); FUN_0005e70e();
  bVar1 = FUN_0005e662()               ; reads a peripheral-0xE / NVM byte at &DAT_00009600
  FUN_0005e45a(param_1 | bVar1)        ; WRITES a peripheral-0xE / NVM byte at &DAT_00009a00
    -> FUN_0005a408(0xe, &DAT_00009a00, param_1&0xff, 0)   ; the actual NVM write
  FUN_0005e0c8(); FUN_0005e6ee();
  _DAT_ff83f030 = *(gp-0x6e20)
  FUN_00060c9a(1)                      ; <-- see below: a slow shutdown/reset sequence, NOT instant

FUN_00060c9a(param_1):
  ... several sub-calls (FUN_0005ddb2/e4c8/e50e/e6de/e2ea/e7ee/e8f6/e952/db58/a398) ...
  busy-wait loops keyed on FUN_0005aada() (a free-running timer read), including a FINAL wait of
  delta < 0x9c41 (~40000 ticks) before FUN_00060bf6() -- reads as a deliberate, multi-ten-thousand-tick
  quiescing/reset sequence, not an instantaneous trap.
```

**Separately**, `FUN_00014ba0` (a SIBLING of `FUN_00014b3e`, not called by it) is the function that actually
raises DTC 0x18:
```
FUN_00014ba0:
  uVar1 = FUN_0005e662()               ; SAME NVM cause-code read as above
  if (uVar1 & 3) == 0: FUN_00016de6(0x18, 0, 0, 1)         ; param_3=0 -- NOT the hard-latch pattern
  else:                FUN_00016de6(0x18, uVar1&3, 1, 1)    ; param_3=1,param_4=1 -- HARD-LATCH pattern
                        FUN_0005e70e(); FUN_0005e45a(uVar1&0xfc); FUN_0005e0c8(); FUN_0005e6ee();
```
`FUN_00014ba0`'s only caller: `FUN_0001a190` (`FUN_00045608(0,0,0x8000,0x8000)` [the SAME channel-0
gain-collapse actuator as `FUN_0001a16a`, confirming both are motor-off implementations] then
`FUN_00014ba0()`). `FUN_0001a190`'s only caller: `FUN_000197ea` -- which is **state 1's handler** inside
the master fault-state dispatcher `FUN_00019f7c` (confirmed: sole caller `FUN_0002214a`, task1/1kHz).

## `FUN_00019f7c`'s structure -- the state-1 identity matters [EVIDENCE]

```c
// TRIP block: fires when gp-0x685c!=0 (DTC hard-latch, set by FUN_00018738 from ANY of Monitor1/
// Monitor2/FUN_00045a20/the gp-0x6bd0 shadow pair/DTC-0x18's own hard branch) OR a few other flags:
if (bVar7 != 1 && iVar4==1 && (iVar2!=0 || gp-0x685c!=0 || ... ) && gp-0x3ee8==0) {
    gp-0x67fa = 8;  FUN_00021e46(); FUN_0001a16a();  gp-0x3ee8=1;   // <- the KNOWN motor-off/EPS-lamp trip
}
// STATE DISPATCH on bVar7 (now possibly ==8 from the trip above, or whatever it already was):
state 1  -> FUN_000197ea()   // <- calls FUN_0001a190 -> FUN_00014ba0 -> conditionally DTC 0x18
state 3  -> FUN_00019888()
state <5 -> FUN_00019970()
state 5  -> FUN_00019b10()
state <7 -> FUN_00019bd0()
state 7  -> FUN_00019cd4()
state 8  -> FUN_00019cfa()   // <- NOT FUN_000197ea; state 8's own handler, not traced this session
state <10-> FUN_00019f00()
state 10 -> FUN_00019d90()
state 11 -> FUN_00019e7c()
```
**State 1 is a DIFFERENT state from the state-8 hard-shutdown state the trip block sets.** DTC 0x18's
raise is gated behind reaching state 1 specifically, which reads structurally like an early/boot-sequence
check (the state-1 handler's own internal branch further gates on cal bytes `tp+0x74f9==0xAA` at
`0xBF000+0x74F9=0xC64F9` and `tp+0x74d0==3` at `0xBF000+0x74D0=0xC64D0`), not a live re-entrant state
reachable purely from an in-drive amplitude/frequency event.

## Verdict [EVIDENCE unless flagged BELIEF]

**DTC 0x18/fault_id 24 requires an ACTUAL prior MCU reset to be raised at all.** The reset-cause byte
`FUN_0005e662()` reads (peripheral-ID 0xE, address `&DAT_00009600`) only changes value when something
WRITES a new cause code — and the only writer found this session is `FUN_0005e45a` inside
`FUN_00014af6`'s own chain (different address, `&DAT_00009a00`, but same peripheral-0xE channel family;
the two addresses are [BELIEF] read as different fields of the same NVM/reset-cause record, not
independently confirmed as literally the same byte). `FUN_00060c9a`'s multi-ten-thousand-tick busy-wait
structure [EVIDENCE, fresh decompile] reads as a genuine shutdown/reboot sequence, not an in-place trap.

**⇒ This REFUTES "cave growth trips DTC 0x18 mid-cycle" on a SECOND, independent, structural ground** —
beyond the timing-margin argument (cave growth ~17-35 worst-case cycles / ~212-438ns at assumed 80 MHz
CPU clock, vs a watchdog window that must be >= the slowest monitored task's period, >=1-10ms — see the
V75-incident cave-diff memory for the full arithmetic). Even if the timing margin were somehow closer,
DTC 0x18 cannot fire from a slow cycle WITHOUT an intervening actual reset+reboot, and the V75 incident's
observed signature (in-place transition to the fault state, no apparent bus-dropout/reboot gap) does not
match that mechanism.

**[EVIDENCE] Byte-confirmed: `FUN_00014b3e`/`FUN_00014ba0`'s code (0x14b3e-0x14d80ish) is untouched by
V75** — the full V74-vs-V75 diff (`_v74_engagedcols_x0_12_addonly_plain_image.bin` vs
`_v75_CY0.566-EX1.200_magprobe_plain_image.bin`, Python byte scan over [0x13000,0x100000)) shows zero
diff runs anywhere near 0x14000; all 37 diff runs (142 bytes total) are confined to the probe cave
(0xC4B3C-0xC4B77) and calibration/CRC regions (0xC4FFC and up). The watchdog mechanism itself is
identical between the two builds.

## Open items
1. `FUN_00060bf6` (the actual reset trigger, presumably) not decompiled this session.
2. TAUA1I1's period register was NOT located (SVD's `TAUA1CDR1` addressOffset `0x7F3804` added to
   `baseAddress 0xFF809000` produces an address outside sensible 32-bit peripheral space — flagged as a
   probable SVD quirk for this specific register group, not resolved this session; the existing
   `reference_accord_dtc18_cadence_watchdog.md`'s "OPEN" flag on this same point stands).
3. Whether `DAT_00009600` and `DAT_00009a00` are literally the same NVM byte (read vs write address) is
   BELIEF, not independently confirmed.
4. State 8's own handler `FUN_00019cfa` (the "already in hard shutdown" per-cycle housekeeping) was not
   traced this session.

## Related
[[reference_accord_dtc18_cadence_watchdog]] (the gp-0x68b7 4-task bitmask mechanics this refines, not
supersedes) · [[reference_accord_hard_shutdown_full_map_v75_incident]] (FUN_0001a16a / FUN_00045608
channel-0 actuator, same actuator FUN_0001a190 also calls) · [[reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75]]
and [[reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a]] (the DTC 0x1c/0x1d family, ranked ahead of
DTC 0x18 for the V75 incident on this same session's evidence).
