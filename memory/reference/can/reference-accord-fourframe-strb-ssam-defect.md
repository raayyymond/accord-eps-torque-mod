# FOURFRAME never transmitted — STRB=0x80 leaves SSAM=0 ("message buffer not used")

**Established 2026-07-27, verified three ways.** The FOURFRAME telemetry cave's four new IDs
(`0x6A0`-`0x6A3`) were absent from the route-13 rlog because **the mailboxes were never enabled**, not
because a downstream gateway dropped them.

## The defect
The cave writes `movea 0x80,r0,r7` / `st.b r7,0x0[r6]` → **`STRB = 0x80`** at mailboxes 16-19
(sites `0xC4B6A`, `0xC4C1A`, `0xC4CCA`, `0xC4D7A`; target addresses `0xFF481024 + m*0x40`, all correct).

`STRB` layout (V850E2/Px4 manual p.1249/1268):
`bit7 SSOW | bits6-3 SSMT[3:0] | bit2 SSRT | bit1 | bit0 SSAM`

- **`SSAM`: 0 = "Message buffer not used", 1 = "Message buffer used"**
- §20.8.1: a buffer joins the TX priority search only when **SSAM=1**, SSMT=0000B, RDYF=1
- `0x80` sets `SSOW` — the **receive-side** overwrite control, meaningless on a TX buffer — and leaves
  SSAM=0

## Stock proves it empirically
`FUN_0001cf30`: TX mailboxes 0-6 get `mov 0x1,r23` @`0x1D02C` → `st.b r23,0x24[r24]` @`0x1D08C` = **0x01**.
The unused free pool 7-32 gets `st.b r0,0x24[r10]` @`0x1D1AC` = **0x00**. `0x80` has bit0 clear —
**the same as the unused pool.**

## Root cause and blast radius
`builds/telemetry/build_vcantx_test_tva.py:54` labelled bit7 SSOW as "SSOW bit7=1 -> TX direction". FOURFRAME reused it
verbatim. **The VCANTX seed build carries the same defect** and would also have been silent.

## Fix
`movea 0x80,r0,r7` → `movea 0x1,r0,r7`: bytes `203e8000` → `203e0100`. Identical 4-byte encoding, so the
cave layout and every branch displacement are unchanged. **4 sites, 8 bytes, plus the block CRC.**
Shipped in FOURFRAME2 (`_vfourframe2_plain_image.bin`).

## Everything else in the cave was correct
MID0W as a 32-bit `ID<<18` with IDE=0, DTLGB=8, and `CTL = 0x0100` then `0x0200` byte-identical to
stock's own sequence at `0x1D7EE`/`0x1D7FC`. There is **no global mailbox-enable mask** on this
peripheral — per-mailbox `STRB.SSAM` is the only "buffer in use" control.

## Knock-on: the gateway-whitelist theory is WEAKENED
`0x19F` was its strongest control, and it is **not clean**: its callback `FUN_00055F2E` is an
unconditional `return 1`, but **slot 8 is gated at its own request site** (`0x5559E andi 0x40,r15,r16` →
`FUN_0001eaa6` enable / `FUN_0001eaf4` disable), and **there is no equivalent conditional site for slot 9
(`0x18F`)**. `0x1AB` uses the same gated structure and does reach the bus. The difference is one runtime
bit in `[gp+0x6400]`, not the mechanism. Do not cite the absent-ID set as gateway evidence without
pinning that bit.

See [[reference-accord-can-tx-100hz-base-tick-and-gateway-evidence]] and
[[accord-check-build-lineage-before-proposing-lever]].
