---
name: reference-accord-e4-rx-task-timeout-dominance-version-and-6803-arm
description: 0xE4 RX runs in RTOS slot 3 (prio 3, 200 Hz) via 0x22b7e->0x521dc->FUN_000520d0, cooperative checkpoints only => 0-tick preemption window vs the PID (slot 0, prio 6, larger=higher); 0xE4 timeout = 500 ms (cal 0xC626C, 1 ms clock gp-0x3e54) -> sentinel 6805=0xFF at 510-514 ms, last request/setpoint HELD until then; 0x2913A dominates 0x29A50 (B2 r27 proof); F181 = 14 B @0x13100 (+2 NUL), no BL reader; gp-0x6803==2 => ramp-in 0.10 s / ramp-out 0.50 s and post-PID fade arm 0xCBAE4 instead of 0xCBBC4 (r25 live 0x29A82->0x2A0AC).
metadata:
  type: reference
---

Trace: `docs/traces/TRACE-2026-09-30-dominance-preemption-timeout-version-and-6803.md` (2026-09-30, stock code.bin + V294 program).
Scripts: `_scratch/angle_loop/dpt/` (`DptCfg.java` read-only Ghidra CFG/def-use, `jarlscan.py`, `e4_timeout_mirror.py`).

**RTOS priority direction [EVIDENCE].** `FUN_00083854` (ActivateTask) inserts into the ready list `gp-0xe90` sorted
DESCENDING on TCB+5. Schedule (syscall 5, `0x8412c`) switches only if the head's priority is strictly greater than the
running TCB+5. ⇒ **larger = higher.** slot0 `FUN_0002214a` 6 · slot1 4 · slot2 5 · slot3 `FUN_00022b24` 3 · slot4 2 ·
slot5 1 · idle 0.

**Switching is cooperative [EVIDENCE].** The TAUJ1I2 ISR only sets `gp-0x42fc` and `eiret`s. All 82
`jarl 0x14be4` checkpoints sit in task bodies, and there is no CAN EI vector. ⇒ **0xE4 decode is atomic with respect
to the PID.**

**0xE4 RX chain [EVIDENCE].** Slot 3 → `0x22b7e jarl 0x521dc`, which loops 19 descriptor records at
`tp-0x3abc = 0xBB544 + i*0x20`; for idx 7 = 0xE4, +0x18 mask 0x0F means every pass. `0x522c2` calls
`FUN_000520d0(i)`:
- New frame: reset the timer (`FUN_00054520`), check checksum and counter, then `jmp [rec+0x1c]` = `FUN_00052676(status)`.
- No frame: `FUN_000542a6` timeout monitor, then call the handler with the **OLD** state (read at `0x5217c`, before the monitor).

**Timeout [EVIDENCE].** Per-message record `gp-0x32cc + 7*0x2c`, `.data` boot image at flash `0x89F18`:
- +0x28 → `0xC626C` = 500 ms (pending): **the value that sets the timeout**
- +0x00 → `0xC626E` = 60000 (confirmed)
- `0xC6262` = 200 ms, used only if `gp-0x6a98 ≠ 0`
- boot state 4

The clock is `gp-0x3e54`, +1 per slot-0 tick. **The sentinel lands 510–514 ms after the last frame** (mirror, all
phases). Until then the last request and setpoint are held.

**Checksum/counter debounce [decompile only].** Faults count against `500/10 = 50`. **Up to 49 consecutive bad frames
are decoded as valid** (`FUN_000540d0`/`FUN_00054066`).

**B2 dominance [EVIDENCE].** In `FUN_00028ea6` V294: 1,874 instructions, 0 undefined, 0 computed flows.
- Entry→`0x29A50` avoiding `0x2913A` is unreachable.
- Only `def@0x2913A` reaches `0x29A50`.
- The callees `FUN_00046ea6` and `FUN_00016de6` both preserve r27.
- External branches into the region: the 3 raw hits at `0xD86xx` are LERP data.
- r8 and r27 are dead after the guard (first touch is a write on both paths).

**Version string [EVIDENCE].**
- `0x13100` (14 B) is read only by the F181 handler `FUN_0004f6fa` (`0x4F70C`). F180 `FUN_0004f6d6` reads `0x1310E`.
- No bootloader-region reference exists.
- The `0x14117` copy is inside the NVM ROM default block `0x14100` (len 0x28 → RAM `0xFEDFE000`) with no field reader.
  `FUN_00005ed0`'s table at `0x14100` only ever indexes entry 0.
- ⚠ The kit flasher's part gate compares the running F181 with the `.rwd` `/` header. A new string needs re-headered
  revert rwds.

**`gp-0x6803 == 2` [EVIDENCE].**
- Engage SM direction 2: states 6/7/8, `0xC63FC` = 328 in (0.10 s), `0xC63FA` = 66 out (0.50 s); versus states 3/2/4
  with 33 (0.99 s) and 16 (2.05 s).
- `r25 = (6803 == 2)` at `0x29A82` selects the setpoint taper `0xCBA04`/`0xCBA74` (cliff 2240–2560 raw) over
  `0xCB8B4`/`0xCB924`, and the post-PID fade `0xCBAE4` (X 24..112, Y 255..51) over `0xCBBC4` (X 16..96, Y 255..77).
- `0xCBB54` ≡ `0xCBC34` in value.
- **r25 is live across hook `0x29D76`.**

Related: [[reference-accord-0e4-handler-x4-verified-and-gp6803-is-set-me-x00]],
[[reference_accord_sentinel_delivered_st7_sticky_and_guard_block_edits]],
[[accord-rtos-task-table-and-rate-scheduler]], [[reference_accord_a160_rdbi_handlerptr_live_dispatch]].
