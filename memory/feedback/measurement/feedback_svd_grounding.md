# feedback_svd_grounding — ground decompilation in the V850 CMSIS SVD

**Operator preference (stated 2026-07-07):** For future firmware decompilation work, ground as much of our
analysis and understanding as possible in the **V850 CMSIS-SVD** (authored from the datasheet / hardware
manual), rather than reasoning about bare peripheral addresses.

## What this means in practice

- The canonical SVD for the 2020 Accord EPS is
  `analysis-2020accord/reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd` — for the exact chip **Renesas µPD70F3508 /
  V850E2** (product ID `0DB40h`, confirmed from the `PRDNAME` reset value). It is the authoritative memory map.
- When a trace touches a peripheral register (CAN/FCN, timers, ADC, ports, DMA, etc.), **cite the SVD register
  and field NAME**, not just the absolute address — e.g. a store to `0xFF481000` is
  `FCN0M0DAT0B` (FCN0 message buffer 0, data byte 0), and a TX/RX direction bit is `FCN0M{n}STRB.SSOW` (bit 7,
  0=RX / 1=TX). This makes the disasm→hardware mapping datasheet-traceable and unambiguous.
- Prefer the SVD to resolve peripheral-topology questions. Example win: Segment A used the SVD's addressBlock
  declarations to prove `0xFF489000` is FCN0's *own* `+0x9000` sub-block, correcting two sibling agents who had
  read it as a separate "channel B." The SVD settled a genuine cross-agent disagreement.
- Two CAN controllers are declared: **FCN0 `0xFF480000`**, **FCN1 `0xFF4A0000`**; 64 message buffers each at
  `base + 0x1000 + N*0x40`; per-buffer registers `FCN0M{N}DAT0B..DAT7B` (data bytes, sub-offset `B*4`),
  `FCN0M{N}DTLGB` (data length), `FCN0M{N}STRB` (config incl. direction).
- If the SVD lacks a needed peripheral or field, note the gap and fall back to datasheet/manual reasoning — but
  say which source grounds each claim.

## Why

Bare-address reasoning is where confident-wrong firmware conclusions hide (a mis-attributed peripheral base can
send an analysis down the wrong controller). SVD names are the datasheet's own vocabulary; anchoring to them
keeps traces checkable against Renesas documentation and against each other. Pair this with the existing
`feedback_rigorous_validation` discipline (byte-verify; belief-vs-evidence separation).

## Tooling note

The SVD is also loaded into Ghidra (the `reference/svd_for_ghidra/` path) so peripheral registers appear by name in
decompilation. For r2/rizin work, keep the SVD open alongside and translate addresses to names by hand (grep
the SVD for the `FCN0M<n>` / `FCN0GM` / `FCN0DN` blocks, or the relevant peripheral prefix).
