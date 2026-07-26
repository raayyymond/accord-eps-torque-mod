---
name: reference-accord-setpoint-limit-15360-lerp
description: "The LKAS setpoint's +/-15360 clamp is a DEGENERATE LERP (flat Y row in all 28 records, 5 banks) selected by gp-0x674e via pointer array 0xCB844 -- the only code site referencing it. Live record for A160 = 0xE41A8. Raising it 15360->16384 is +6.71% top-end at every build tier and is EME-safe (no float twin; the gentle-EME channel is driver-torque-fed). RESOLVED + SHIPPED IN V38 2026-07-18: the former CRC build blocker is cleared by adding (0xE4000,0xE4FFC)+(0xE5000,0xE5FFC) to TOUCHED_BLOCKS -- first build to touch a bootloader block outside 0xC6xxx; chain survives because the linked-list page fields at block_start-8/-6 live in the PRECEDING block. V38 patches all 8 selector-reachable records, not just the live one"
metadata:
  node_type: memory
  type: reference
---

The `+/-15360` clamp applied to the LKAS setpoint inside `m_steer_torque_arbitration`, fully characterized 2026-07-18. Verified against stock `code.bin` by direct disassembly + raw byte dump (both by the lead and by two independent `firmware-codepath-tracer` passes that converged).

## The mechanism is a DEGENERATE LERP, not a curve

Call site `0x28fc8-0x29044`:

```
0x28fc8  ld.bu -0x674e, gp, r12      ; mode selector, a BYTE
0x28fcc  mov   0xcb844, r8           ; pointer array base
0x28fd2  shl   0x2, r12              ; x4 (u32 pointers)
0x28fd6  ld.w  0x0, r12, ep          ; -> record pointer
0x28fe2  addi  0x14, r8, r8          ; +20 = the Y row
         ... 9-point LERP: mul @0x29026, divq @0x2902c ...
0x29032  ld.h  -0x69ae, gp, r13      ; the LKAS setpoint
0x29036  andi  0xffff, r16, r22
0x2903a  cmp r22,r13 / bgt / subr r0,r16 / cmovle   ; SYMMETRIC +/- clamp
```

Record format = 40 bytes: `[u16 count=9][9x u16 X][9x u16 Y][u16 pad]`.

**Every record's Y row is FLAT 15360 at all 9 breakpoints.** The X row is identical everywhere too: `(3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320)`. Both out-of-range early exits also return 15360 (`0x28fec` -> Y[0], `0x29002` -> Y[8]). **The axis input is irrelevant to the output value.**

The axis is `gp-0x6a5e` (the AVG voter = driver column torque), read `@0x28f0e`. So this table was *designed* to taper LKAS authority as the driver pushes back — and was then shipped flattened. That is a latent tuning surface, not just a clamp.

## Banks, selector, and the live record

Pointer array `0xCB844` (u32 LE) — **the ONLY code site referencing it is `0x28FCE`** (byte-scan confirmed; `get_xrefs_to` agrees, showing only `0x28fd6`/`0x28fda`). No other subsystem shares it.

- idx 0-5 -> `0xE4180 + 0x28*i`
- idx 6-11 -> `0xE5180 + 0x28*i`
- idx 12-15 -> `0xE6180 + 0x28*i`
- (further entries exist: `0xE7180`, `0xE8100`, then a different 0x14-stride family from `0xCB8B4`, used by the high-torque-cutoff branch `@0x29a78` — unrelated.)

`gp-0x674e` is **NOT the variant slot index** (a tracer initially claimed this). `FUN_00057f8e` returns the slot (0-15); that slot is then used as an *index to fetch a byte*:

```
0x4271e  mulhi 0x24, r10, r6       ; slot * 0x24
0x42722  add   tp, r6              ; tp = 0xBF000
0x42724  ld.bu 0xe01a, r6, r8      ; byte at 0xCD01A + slot*0x24
0x4272a  st.b  r8, -0x674e, gp
```

Across all 16 slots `gp-0x674e` takes only `{0,1,3,4,6,7,8,9}`. **Our A160 = slot 2 (key `TVAA1`) -> gp-0x674e = 1 -> live record `0xE41A8`, Y row at `0xE41BC..0xE41CC`.** See [[reference-accord-ecu-id-variant-table]] for the table layout and the HW-ID provenance caveat.

## Why raising it is safe (and what it buys)

openpilot `CAR.HONDA_ACCORD` uses `torqueBP = [[0, 4096]]`, so setpoint max = `4096 * -4` = 16384 > 15360. The top **6.25%** of the command range is clipped.

Raising 15360 -> 16384 gives **+6.71% top-end at every build tier** (V9 417->445 vs clamp 512; V31 835->891 vs 1024; V38 1670->1782 vs 2048). The arb output clamp never binds, so the gain is fully observable — but only above 3840/4096 of command.

EME exposure, all three mechanisms checked:

- **Gentle EME — causally impossible.** `gp-0x682f = min(|r15| >> 5, 255)` (`0x29048-0x29068`), and `r15` is loaded once at `0x28f26` from **`gp-0x4f60`** and never rewritten through `0x29068` (every instruction in that span read directly). `gp-0x4f60` is Sensor-B column torque, i.e. the DRIVER's hands — not the LKAS command. See [[reference-accord-gp4f60-is-sensor-b-column-torque]].
- **Hard EME — no one-sided setpoint-table edit exists.** Zero hits for IEEE-754 float `15360.0` image-wide (both endiannesses); no mirrored copy of this table. The monitor casts the integer `gp-0x6acc`; the separate +/-5/1024 checks compare same-cycle int/float wall computations, not setpoint prediction versus lagging actual.
- **Soft EME — setpoint exposure is small, but the old whole-command bound was incomplete.** The raise adds only +6.7% to the LKAS contribution. Assist joins before the first governor, however, so conservative `abs(gp-0x6acc)` is 4762+2560=7322, not the old 4342 estimate. V38 is fault-free on-car; 5120 is not a static proof for every assist-inclusive combination.

~~**[OPEN]** the transient lockstep margin during a fast setpoint slew: the ~6.7% scales a pre-existing "actual lags predicted" error term against the `+/-5/1024` bit32 threshold.~~

✅ **CLOSED 2026-07-18 — and the premise was WRONG.** The `+/-5/1024` compare at `0x4463a` is **not** a predicted-vs-lagging-actual check. Both operands are same-cycle redundant computations of the *same* bound in two datatypes: the int wall `gp-0x6af6` (written by `s_motor_torque_rate_shaper` @`0x43a7e`/`0x43e38`) vs the float twin `lp` (built in `FUN_00043e44` from the float mirrors `0xC6598/A4/AC/C4`). It is an **int-vs-float lockstep** — which [[reference-accord-corridor-lockstep]] already recorded correctly; the "actual lags predicted" phrasing here was a mischaracterization that manufactured a non-existent concern.

**The LKAS setpoint is not an operand of the +/-5/1024 wall compare.** Its command-path entry into the watchdog is `gp-0x6acc` @`0x4467a`, scaled by 2^-10 and sanitized at **+/-8192 counts**. In-range values are kept; only out-of-range values become zero. The conservative assist-inclusive envelope is 7322, leaving 870 counts to this sanitize, not the previously claimed ~2x margin.

⇒ **A faster or larger setpoint slew cannot consume the wall's int/float lockstep margin because both wall sides are same-cycle redundant computations.** Full trip structure is in [[reference-accord-watchdog-fault-sm-fun43e44]].

## ~~BUILD BLOCKER~~ — RESOLVED 2026-07-18, SHIPPED IN V38

**The blocker described below is CLEARED.** `build_v38_tva.py` now covers the bank blocks and V38 carries the raise. Historical framing retained because the fails-closed mechanism is worth remembering.

`0xE4180` sits in bootloader CRC block `[0xE4000, 0xE4FFC)` with its trailer at `0xE4FFC` (confirmed by running `verify_bootloader_crc.py` on the stock dump: 49 blocks, 0 mismatches; blk#23 covers curves 0-5, blk#22 the E5 bank, blk#21 the E6 bank).

Builds through V37 recomputed CRCs only for `TOUCHED_BLOCKS = [(0xC6000, 0xC6FFC), (0x13000, 0xC4FFC)]`. Patching the table without adding the bank block made `walk()` report a mismatch and the builder's self-check refuse to emit the `.rwd` — a **safe, fails-closed** outcome, but a failure.

**The fix (V38, 2026-07-18):**

```python
TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),
    (0xE4000, 0xE4FFC),   # setpoint records sel 0/1/3/4 (blk#23) -- NEW
    (0xE5000, 0xE5FFC),   # setpoint records sel 6/7/8/9 (blk#22) -- NEW
    (0x13000, 0xC4FFC),
]
```

**Chain topology survives.** `walk()` finds each next block via u16 page fields at `block_start-8/-6`, which live inside the **preceding** block's CRC range — never inside a block we patch. Post-patch the walk still finds exactly **49 blocks, 0 mismatches**. This is the general rule for touching any new bootloader block: patch data, recompute that block's trailer, leave the `-8/-6` page fields alone.

## Scope shipped: ALL 8 SELECTOR-REACHABLE RECORDS (not just the live one)

Across all 16 variant slots `gp-0x674e` takes only `{0,1,3,4,6,7,8,9}`. Rather than rely on the slot-2/`TVAA1` resolution (whose HW-ID provenance is **not** closable from `code.bin` — see [[reference-accord-ecu-id-variant-table]]), V38 patches **all eight reachable records**, so the raise lands regardless of how the slot resolves:

| sel | record | sel | record |
|---|---|---|---|
| 0 | `0xE4180` | 6 | `0xE5180` |
| **1** | **`0xE41A8`** (LIVE, A160) | 7 | `0xE51A8` |
| 3 | `0xE41F8` | 8 | `0xE51D0` |
| 4 | `0xE4220` | 9 | `0xE51F8` |

Y row = record `+0x14`, 9 halfwords. **72 halfwords total = 144 bytes of intent, but only 36 bytes per bank actually differ** (15360=`0x3C00` → 16384=`0x4000`; the low byte is `0x00` in both, so one byte per halfword moves). Unreachable records 2, 5, 10-15 are **left stock at 15360**. X axis rows, record counts, and pads are guarded stock pre- and post-patch.

Patch surface (corrected twice — an early estimate of 144 halfwords wrongly assumed 9 x 16 variants; the narrow 9-halfword scope was then widened deliberately for slot-resolution robustness):

| scope | records | halfwords | shipped? |
|---|---|---|---|
| this car only | 1 (`0xE41A8`) | 9 | no |
| all reachable | 8 | **72** | **yes, V38** |

## Verdict

Safe and correct to raise, and now **shipped in V38** — but it remains a **trim, not a lever**: +6.71% on the top 6% of the range. Gain `0xC646C` is still the lever that actually moves top-end torque. It was folded into a build with other content rather than spinning a flash cycle for it, as recommended.

Related: [[reference-accord-arbitration-limit-family]], [[reference-accord-lkas-delivery-and-governor]], [[reference-tva-bootloader-crc-scheme]], [[reference-accord-base-assist-lane-architecture]]
