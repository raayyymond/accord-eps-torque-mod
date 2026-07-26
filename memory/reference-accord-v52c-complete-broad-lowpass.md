---
name: reference-accord-v52c-complete-broad-lowpass
description: V52C = the EMA low-pass on gp-0x4f60 with ALL 19 command-path carriers repointed to gp-0x1300 — BUILT, every pre-flash gate passed, UNFLASHED.
metadata:
  type: reference
---

**V52C = the COMPLETE broad low-pass. BUILT + ALL PRE-FLASH GATES PASSED, UNFLASHED.**
`_v52c_plain_image.bin` SHA `af01c8bd…`; 132 changed bytes vs V38 in 24 runs; 50/50 CRC; x31
round-trip + RWD readback clean. Files: `build_v52c_tva.py`, `v52_cave_asm.py`,
`verify_v52c_image.py`, `eps_v52c_gate2_broad.py`.
Handoff: `docs/HANDOFF-2026-07-24-v52c-complete-broad-lowpass.md`.

**What it is:** V38 + the confirmed state-4 ratchet fix + an 86-byte code cave at `0xC4B34` running a
first-order EMA (`y += (74·(x−y) + 512) >> 10`, α=74/1024, fc≈11.9 Hz at the 1 kHz producer rate) on
the torsion-bar sensor `gp-0x4f60`, writing a filtered COPY to `gp-0x1300`, with **all 19 command-path
carriers repointed** to read that copy. Trampoline `jr` at `0x7FEAC` displacing `cmp r0,r8`/`mov r8,r14`,
re-executed LAST so PSW flags are fresh for the `bge` at `0x7FEB0`. 4× gain (`0xC646C`=3564) and the
DTC-0x1d clamp trap byte-stock.

**★ WHY ALL 19, NOT A CHOSEN SUBSET (operator directive, and the governing principle):** a MIXED
raw/filtered population is ITSELF the hazard — any self-consistency / dual-path / lockstep / mirror
check straddling the split would see a divergence that does not exist today. **That is exactly how V27
bricked: ASYMMETRY, not magnitude.** It is also the most stable option measured, so the two criteria
agree. A per-lane cost/benefit approach (which the lead started with) additionally rests on
classifications that turned out to be wrong — uniformity is the more robust decision under uncertainty.

**Gates — all passed:**
- **GATE-1 (RAM ownership of `gp-0x1300`) — FIVE independent clearances:** V51P live probe (0/24000
  CAN-330 frames non-zero, full 16-bit, beacon 100% live); outside the `0xb7260` mailbox array; 0 LE32
  pointer refs image-wide; 0 `movhi` materialising the `0xFEDF` page in code; absent from the
  `0x89c34`/`0xbbc48` descriptor tables. **The method reproduces both historical failures as controls**
  — `gp-0x1500` (V50, failed on-car) is INSIDE the array AND has 2 pointer-table entries
  (`0xb73ac`, `0xbb658`); `gp-0x14FA` (V48B, bricked) is inside the array.
- **GATE-2 (closed-loop stability) — CLOSED:** stability edge **4.66× (stock) → 21.19×**,
  `worst_re`=0.189, GM 14.48 dB; **monotonic** in the filtered fraction over a 41-point sweep under
  both calibrations (no destructive partial blend); no unity-gain crossing 0.3–150 Hz, so there is no
  low-frequency crossover for the filter's lag to erode; ZOH/aliasing improves. **A first-order EMA has
  no resonant pole and |H|≤1 everywhere** — unlike V48B's notch, whose own poles WERE the brick mechanism.
- **Monitor asymmetry:** none. Every live comparison is vs a LITERAL/cal constant or the same
  function's own prior filtered state. 3 shadow pairs exist (`gp-0x6b86`↔`0x4cde`, `gp-0x6ba6`↔`0x4ce8`,
  `gp-0x6b9a`↔`0x4ce4`) but write both legs atomically from ONE freshly-computed value →
  **input-invariant**, so raw-vs-filtered cannot change whether they fire. They call `FUN_0006b9fa`
  (weak, writes `gp-0x444f`/`gp-0x4e53`), NOT `FUN_0006b9ee` (→ fault 0x17 → hard motor-off).
- **Dual-path / key-on:** prior-sample cells (`gp-0x3798`, `gp-0x6a80`) have **0 external readers** and
  zero-init at boot. RAM clears on power-up and a flash REQUIRES a power cycle, so no stale state
  survives the flash, and from a zero state `|filtered| ≤ |raw|` on cycle 1 → a key-on transient can
  only SHRINK. **(V48B's failure was a key-on slam; this is the inverse.)**
- **Ghidra re-disassembly of the BUILT image:** PASS (A)–(G) on a freshly re-imported copy.
- **Task timing vs DTC 0x18** (hard-eligible cadence watchdog): cave = ~0.06% of the 1 ms tick.

**Only 5 command-path reads stay RAW, all comparing vs LITERAL constants:** health gates `0x28F26`,
`0x42C20` (M1), `0x43EDA` (M2), plus dormant mux arms `0x34392`, `0x34ACE`. Also raw: 2 diagnostic
(`0x2EC66`/`0x2ECBA`) and 3 dead (`0x2A992`, `0x2D9A2`, `0x2DAE6`). **Health gates and all
telemetry/CAN/UDS/freeze-frame readers MUST see the true sensor.** `verify_v52c_image.py` enforces
this as a machine-checked completeness invariant that FAILS on any unexplained raw read in
`[0x28000,0x46000)`.

⚠ **`gp-0x4f60` is SHADOWED (shadow `gp-0x4486`)** — a mismatch calls `FUN_0006b9ee` → fault 0x17 →
HARD motor-off. This is why the filter writes a COPY and never the source. **Never "simplify" this by
filtering `gp-0x4f60` in place.**

**Residuals (honest):** filtering `0x36846` slightly desensitises the DTC-0x23 rate check (verified NOT
hard-fault eligible, and the direction is safer — an EMA attenuates the per-cycle jump that trips it);
and the dual-path audit used 4-byte scans only, so a hidden 6-byte-form reader of the *destination*
cells is low-risk but not formally excluded.

🛑 **STILL UNFLASHED. A code cave is this kit's only bricking class (V24/V27/V48B). Flash ONLY on
explicit operator instruction naming the file and the bus.**
See [[reference-accord-gp4f60-carrier-surface]], [[accord-dtc-0x18-hard-eligible-cadence-watchdog]],
[[accord-gp4f60-two-encodings-enumeration-trap]], [[feedback-stale-ghidra-import-defeats-hash-check]].
