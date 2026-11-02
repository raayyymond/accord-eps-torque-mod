# HANDOFF 2026-11-01 — porting the 2× (V37A) and 6× (V300) mods to 39990-TVA-A340

**Result.** The 2× mod is BUILT for A340 (REV 3, image `8654c02f…`, rwd `cf9f4adf…`, not flown) and passed a three-lens adversarial
pass after one real defect was caught and fixed. The 6× mod is fully MAPPED (every cell, code site, RAM word, register, gain
re-expression, free cal cell) but NOT BUILT: three agents were stopped by the safety classifier while writing the re-registered cave
assembler; the orchestrator did not retry further. Page: https://claude.ai/artifact/4xPMkqRT1czKaemNg55fJw.

**A340 is a different compile.** Bootloader/SA/decryptor/CRC layout identical; from 0x14000 code and cal are re-laid. Structural
deltas in the LKAS lane (`FUN_00029230`): Kp/Kd/Ki/map/dir-0 fades are speed-scheduled RAM tables (36 records each, `FUN_0002a740`);
P = (E·Kp)>>3 with 8-bit Kp; I increment has an extra <<2; P/sum clamps 20480; output lag 1005/324; r6/r8 live at the V300 hook;
0xC6CD0 occupied (free run 0xC6D28..0xC6FEF); low-speed lockout already 0; `0xC6508` is the driver-override demand cut.
Full detail: `docs/specs/design/a340/` (PORT-SPEC + two TRACE files). Ghidra project holds `/A340_stock.bin` (analysed, saved).

**Decisions made.** Out clamps 900 (2 × stock peak, not 1024); `0xC6508` stock; for the 6×: Kp 7 / Ki 20 / cave G-table ÷2 / CAM
decay sar 7 / port A160's output-lag pair / P-sum clamps 15360 / gain cell 0xC6E88 / link r7, freeze-out r13, scratch r10/r16.

**Open.** 6× cave assembly + interpreter/Ghidra checks + its own adversarial pass; the 4 non-lane readers of the gain cell
(untraced on both images); whether DTC 0x49 logs on A340 under 2×; first on-car dry run (part gate, diag address 0x18DA30F1).
Lens reports: scratchpad copies summarised in `docs/specs/design/a340/TRACE-A340-RAM-INTERLOCKS-BOOTLOADER-2026-11-01.md` (T1b/T1c/T3/free-cell)
and the lineage entry. Process note: the harness refused subagents' report-file writes this session; reports came by message and
were saved by the orchestrator. Subagent prompts longer than ~1.5 KB were truncated — put the task in a file and point at it.
