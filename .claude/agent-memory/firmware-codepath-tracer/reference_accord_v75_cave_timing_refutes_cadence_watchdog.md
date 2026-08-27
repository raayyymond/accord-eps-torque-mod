---
name: reference_accord_v75_cave_timing_refutes_cadence_watchdog
description: Full V74-vs-V75 byte diff (142 bytes/37 runs) and instruction-level worst-case cycle count for both probe caves at 0xC4B34. V74's cave is 15 instructions/18 cycles worst-case; V75's is 28 instructions/35 cycles worst-case -- a ~17-cycle (~212 ns at assumed 80 MHz) growth, 4-5 orders of magnitude below any plausible DTC-0x18 watchdog window. Cleanly refutes "the cave growth 45B->68B tripped the cadence watchdog" on timing-margin grounds, independent of reference_accord_dtc18_requires_prior_reset_not_live_trippable's structural refutation.
metadata:
  type: reference
---

# V74->V75 cave diff and timing margin -- traced 2026-08-06

Files (confirmed on disk, Python SHA-256 + byte scan, `[0x13000,0x100000)` per the whole-file-diff trap):
`_v74_engagedcols_x0_12_addonly_plain_image.bin` (sha256 `8ae58c...7bfa959`) vs
`_v75_CY0.566-EX1.200_magprobe_plain_image.bin` (sha256 `e16ba4...1edf61c`) — **the flown V75 build**
(confirmed by the presence of `SUPERSEDED-DO-NOT-FLASH-HARDFAULT-LOSS-OF-ASSIST-2026-08-06-V75-CY0.566-EX1.200.rwd`
in `flashing-2020accord/rwd/`). ⚠ `_v75_CY0.566+EX1.200...` (with a `+`) does **not exist on disk** —
resolved: it was a stale Ghidra open-programs entry, not a real build; ignore it.

## Full diff: 37 runs, 142 bytes, three classes

**Cave** (3 runs, 0xC4B3C-0xC4B77): the probe payload itself, see below.
**CRC words** (10 runs × 4B = 40B, all at `xxFFC` block boundaries): `0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC,
0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC, 0xD8FFC, 0xD9FFC` — one per 0x1000-aligned CRC-checked block touched
by the cal edit, matches record ("142 bytes / 10 CRC words").
**Calibration cells** (24 runs, 45B): repeated small edits at offsets `+0x7DA/+0x7DC/+0x7EE/+0x7F0/
+0x810/+0x812/+0x824/+0x826` relative to each `0xD_xxx0`-aligned block (`0xCF554/0xCF568, 0xD07DA...,
0xD27DA..., 0xD37DA/0xD37EE..., 0xD47DA..., 0xD67DA..., 0xD77DA/0xD77EE..., 0xD87DA..., 0xD97DA/0xD97EE...`)
— these are the mode-indexed replicas of FactorC `Y[0]` (429->566) / FactorE `X[1]` (400->200), consistent
with the kit's existing V74->V75 record. Not re-decoded cell-by-cell this session (already established).

## The cave, byte-exact, both builds [EVIDENCE, `disassemble_bytes(dry_run=true)`]

Both open in Ghidra as `_v74_engagedcols_x12_plain_image.bin` / `_v75_c566_ex1200_magprobe_plain_image.bin`
— **verified NOT stale**: `read_memory(0xC4B30,80)` on each matches the Python byte read of the actual
on-disk files exactly (a live check against the kit's own "stale Ghidra import" trap).

Common prologue `0xC4B34-0xC4B3B` (8B, identical both builds): `mov 0,r7; ld.h -0x6bd0[gp],r6; cmp r0,r6`
(loads `gp-0x6bd0`, the V75 damper lever itself, into r6; both builds' probes start by testing it).

**V74 cave — 0xC4B34 to 0xC4B61 (46B), 15 real instructions, then 22B zero-padding to the 68B cave
allocation** (both builds' allocation is 68B, `0xC4B34-0xC4B77`, confirmed both hit `0xFF` filler at
`0xC4B78`):
```
be 0xC4B42 (skip if gp-0x6bd0==0) / movea 0x10,r0,r7 (bit4 = "gp-0x6bd0 != 0")
ld.bu -0x67fa[gp],r6; andi 0xf,r6,r6; or r6,r7           ; bits[3:0] = state (gp-0x67fa) & 0xF
shl 3,r7                                                  ; pack: bit7=nonzero-flag, bits[6:3]=state
ld.bu -0x1514[gp],r6; andi 7,r6,r6; or r7,r6; st.b r6,-0x1514[gp]   ; preserve low 3 bits, write
movea -0x1518,gp,r6; jmp lp                               ; trampoline epilogue (replays stolen instr)
```

**V75 cave — 0xC4B34 to 0xC4B77 (68B, ALL used, zero padding), 28 real instructions** — a genuinely
larger/different probe (magnitude "thermometer" bucket of `|gp-0x6bd0|` + a separate `gp-0x6ac2`
nonzero flag, matching the flown filename's own `thermo-6ac2` tag):
```
cmp r0,r6; be (skip if ==0); bge (skip negate if >=0); subr r0,r6 (abs); add 8,r7 (nonzero flag)
shr 5,r6                                                  ; |value|>>5
cmp 4,r6; blt (skip +4); cmp 9,r6; blt (skip +2); cmp 0xe,r6; blt (skip +1)   ; 3-level magnitude ladder
shl 4,r7                                                  ; pack into upper nibble
ld.hu -0x6ac2[gp],r6; cmp r0,r6; be (skip if ==0); add 8,r7    ; separate ceiling-index/back-drive flag
ld.bu -0x1514[gp],r6; andi 7,r6,r6; or r7,r6; st.b r6,-0x1514[gp]
movea -0x1518,gp,r6; jmp lp
```
The magnitude thresholds (`>=4*32=128`, `>=9*32=288`, `>=14*32=448`) are the SAME `448` the task brief's
own probe-rung language references — confirms this cave is a magnitude-bucket telemetry probe on
`gp-0x6bd0`, read-only (no store instruction targets `gp-0x6bd0` anywhere in either cave — confirmed by
the disassembly listing, matches the prior session's "read-only on gp-0x6bd0" finding for the sibling V76
cave).

## Worst-case cycle count [assumption stated: 1 cycle/ALU-ld-st instruction, taken branch = 3 cycles,
not-taken = 1 cycle, unconditional jmp[reg] = 3 cycles (standard V850-family pipeline-flush figures, NOT
independently confirmed against the UPD70F3508 datasheet this session), CPU clock = 80 MHz (HEAPCLK, per
`memory/accord/firmware/accord-task5-is-100hz-damper-cannot-damp-21hz.md`'s CLMA1-register-derived figure — the load-
bearing chain per that memory; PCLK=40MHz is the peripheral clock and does not apply to instruction
timing)]

**Key finding: for THIS specific "test-then-skip-one-instruction" branch shape, a TAKEN branch costs the
CPU strictly MORE than falling through and executing the skipped instruction** (taken=3 vs not-taken(1)+
skipped-instr(1)=2, net +1 per taken branch) — so the worst case is the path with the MOST taken branches,
not the path with the most instructions executed.

- **V74 worst case = 18 cycles**, at `gp-0x6bd0==0` (the `be` branch taken): `mov+ld.h+cmp+be(3)+ld.bu+
  andi+or+shl+ld.bu+andi+or+st.b+movea+jmp(3)` = 1+1+1+3+1+1+1+1+1+1+1+1+1+3 = 18.
- **V75 worst case = 35 cycles**, at `0<gp-0x6bd0<128` (i.e. magnitude bucket "<4" after `>>5`, be/bge
  giving the "positive nonzero" 5-cycle leading segment) **and** `gp-0x6ac2==0` (trailing `be` taken):
  leading(8) + shr(1) + magnitude-ladder-all-taken(12) + shl+ld.hu(2) + trailing cmp+be-taken(4) +
  final ld.bu/andi/or/st.b/movea/jmp(8) = 35. (Full instruction-by-instruction trace available on
  request; independently cross-checked by direct sequential summation, both methods agree at 35.)

**Delta: +17 cycles worst case ≈ +212.5 ns at 80 MHz. Full V75 cave cost: 35 cycles ≈ 437.5 ns.**

## The margin argument — clean, and doesn't depend on which task hosts the cave

`FUN_00055a98` (the cave's host, the CAN `0x14A`/STEER_ANGLE_RATE periodic TX packer, confirmed by two
independent methods in `reference_accord_probe_cave_c4b34_trampoline_and_jarl_encoding.md`) has **zero
static callers** (`get_function_callers` returns none — indirect Table-B dispatch, reconfirmed this
session). `0x14A` is measured on the actual CAN bus at **exactly 100.000 Hz** (period 10.0000 ms, linear
fit across 4 segments — `memory/reference/can/reference-accord-can-tx-100hz-base-tick-and-gateway-evidence.md`), cross-
confirmed by cadence-table arithmetic across 3 independently-cadenced slots (0x18F cadence=1 -> 100Hz,
0x1AB cadence=2 -> 50Hz, 0x14A cadence=1 -> 100Hz — internally consistent). **[EVIDENCE, wire-measured]
the cave's effective invocation rate is 100 Hz regardless of which RTOS mechanism drives it.**

I traced part of the underlying CAN-TX dispatch chain (`FUN_0001d68e` <- `FUN_0001d82e`/`FUN_0001d96e`/
`FUN_0001db74` <- `FUN_0001dcaa`/`FUN_0001cd96`/6 others) and confirmed it is a SHARED generic mailbox-
queue subsystem reachable from multiple contexts (e.g. `FUN_0001c306`, one sibling dispatcher for table
slots 11-15, IS called directly from task1/`FUN_0002214a`; `FUN_0004a1b2`, an unrelated serial/diagnostic
protocol handler, is called from task5/`FUN_00022ca0` and ALSO funnels into the same `FUN_0001cd96`
helper) — **but could NOT pin the exact call site for table slot 10 (0x14A) specifically within this
session's budget.** This is flagged OPEN. **It does not matter for the verdict**: even under the MOST
ADVERSARIAL assumption (the cave executes synchronously inside task1's own 1kHz body, directly counting
against its own deadline), the growth (17 cycles / 212.5 ns) is ~1/4,700 of a 1 ms window and the full
cave cost (35 cycles / 437.5 ns) is ~1/2,285 — the DTC-0x18 window itself is lower-bounded by task5's
100Hz/10ms period (task5 is one of the 4 monitored tasks per `reference_accord_dtc18_cadence_watchdog.md`),
giving 3-4 additional orders of magnitude of margin on top of that.

## Verdict

**REFUTED, cleanly, with margin to spare (4-5 orders of magnitude) regardless of unresolved task-identity
questions.** Combined with [[reference_accord_dtc18_requires_prior_reset_not_live_trippable]]'s structural
finding (DTC 0x18 requires an actual prior MCU reset+reboot to be raised at all — a pure execution-time
cost, however large, cannot trip it without an intervening scheduler starvation event of a totally
different character), **the cave is exonerated as a cause of the V75 hard fault on two independent
grounds.**

## Related
[[reference_accord_dtc18_requires_prior_reset_not_live_trippable]] · [[reference_accord_probe_cave_c4b34_trampoline_and_jarl_encoding]]
(host function identity) · `memory/reference/can/reference-accord-can-tx-100hz-base-tick-and-gateway-evidence.md`
(wire-measured cadence) · `memory/accord/firmware/accord-task5-is-100hz-damper-cannot-damp-21hz.md` (80 MHz CPU clock
figure, cited not re-derived).
