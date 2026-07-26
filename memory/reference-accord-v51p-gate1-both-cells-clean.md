---
name: reference-accord-v51p-gate1-both-cells-clean
description: V51P probe drive PROVED both candidate cells gp-0x1300 and gp-0x1100 are RAM-clean (0 live writers) — GATE-1 for the next EMA cell is passed.
metadata:
  type: reference
---

**V51P (read-only cell-probe) was FLASHED + DRIVEN (route `75604b0a432fdc89_00000007--0a8e7099b8`,
4 segments, rlog 7) → BOTH candidate cells are GATE-1 CLEAN.** Decoded two independent ways
(`analysis-2020accord/decode_v51p_gate1.py` + a from-scratch lead verifier) with identical results:

- CAN-330 on **bus 1** only: 24,000 frames. **Beacon = 100.0%** (24000/24000, no dropouts) → the probe
  executed on every frame, so a "clean" read is trustworthy (the discriminating-signal lesson from V31P).
- **B = gp-0x1300 (0xFEDF6D00): 0/24000 nonzero (0.0000%) — CLEAN, full 16-bit coverage, never onset.**
- **D = gp-0x1100 (0xFEDF6F00): 0/24000 nonzero (0.0000%) — CLEAN, full 16-bit coverage, never onset.**
- Stock null (`rlogs/manual/aa5b3e0c01`, 76,520 frames): beacon/B/D bit positions 100% zero → the probe's
  signature is unambiguously distinguishable from stock traffic.

This is the **definitive live-probe RAM-ownership clearance** that gp-0x1500 (V50's cell) FAILED — see
[[reference-accord-b7260-io-mailbox-array]]. Both cells sit OUTSIDE the 0xb7260 mailbox array and the
gp-0x1401..0x1502 poison region. Either is safe as the EMA state cell for a rebuilt low-pass; **V52 uses
B = gp-0x1300** (first-listed), with D = gp-0x1100 the drop-in alternate.

⚠ Note: this clearance makes the *cell* safe (retires V50's GATE-1 residual). It does NOT by itself make a
gp-0x4f60 source-filter complete or correct — the *carrier* surface turned out to be ~19 lanes, not 10; see
[[reference-accord-gp4f60-carrier-surface]]. The rlog `.zst` files are kept LOCAL only (gitignored, not
tracked).
