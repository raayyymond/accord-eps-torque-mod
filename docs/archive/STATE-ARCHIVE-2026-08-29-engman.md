# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⚠ **CORRECTION — `FUN_000382d8`/`FUN_000389ec` ARE NOT PURELY MONITOR-SIDE**
Earlier this session I filed both as monitor-side because they write no aggregator lane. **That test
was too narrow.** `FUN_000389ec` writes `gp-0x64b8`/`gp-0x64b6`/`gp-0x641c`/`gp-0x640a` — **exactly the
RAM LERP rows `FUN_00038148` reads** to shape Path 2's output — and `FUN_000382d8` feeds
`FUN_000389ec` through `gp-0x62fc..0x630c`.
=> **the chain is `FUN_000382d8` → `FUN_000389ec` → the RAM LERP → `FUN_00038148` (Path 2)**, so both
ARE in the torque path, via a RAM table rather than a direct lane write.
⭐ **A function can be in the loop without writing a lane cell.** "Writes no aggregator lane" proves
it is not a lane PRODUCER; it does **not** prove it is out of the loop. **Follow the RAM it writes.**

