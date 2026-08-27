---
name: v42-state4-ratchet-and-r26-built
description: "V42 = V38 + one CODE byte killing the state-4 governor ratchet + 18 cal halfwords zeroing the r26 lane. BUILT + independently verified, UNFLASHED. First non-cave code edit in the kit's history."
metadata:
  node_type: memory
  type: project
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T05:31:00.909Z
---

**Current candidate. BUILT + independently VERIFIED, NOT FLASHED (2026-07-20).**

```
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V42-LKAS-4x-V38base-state4-ratchet-off-r26-off-0x13000-0x100000.rwd
RWD   sha256 968badc728f2de162194f2772f0112ba45c7570aad26ed72530cc15ad4dfebc8
plain sha256 7cf165a7e4475da1ca20e036cb8f9921bb9b3d124ff32bec0aebc2c76799b64c
```

Builder `analysis-2020accord/builds/v18_v49/build_v42_tva.py`. Baseline = the exact on-car V38 image. **35 changed bytes in 14 runs.**

**CHANGE 1 — the ratchet (CODE, 1 byte).** `0x454FE`: `0x65BA → 0x65B5`, V850 Bcond condition nibble `0xA (BNE) → 0x5 (BR)`, making the state-4 substitution block `[0x45500,0x455C4)` unreachable. Displacement untouched ⇒ target stays `0x455C4` (asserted by decoding both). **No external Bcond or `jr` enters that block** (scanned `0x4503C`-`0x45700`). ★ **First code edit since V27 and the first ever that is not a cave/trampoline** — it flips one branch condition in place, no relocation, no length change. Root cause: [[reference-accord-state4-governor-ratchet]]. Safety **proved by construction**, not argued — see that node.

**CHANGE 2 — the vibration (CAL, 18 halfwords).** Zeroes the `r26` adaptive torque-rate gain surface: Y rows at `0xC6A72`/`0xC6A86`/`0xC6A9A`/`0xC6AAE` (4 records × 4) plus overrides `0xC6444`(512→0) and `0xC643E`(1536→0). A flat-extrapolated LERP over an all-zero Y row is 0 everywhere ⇒ `r26 == 0` unconditionally. X rows, counts, terminators and **all four `r24` cals** (`0xC6440/42/46`, deadzone `0xC61F6`) asserted untouched, so the two lanes stay provably independent.

⚠ **The two changes have DIFFERENT confidence levels and that must not be blurred.** Change 1 fixes a *verified root cause*. Change 2 targets `r26`, the **last mechanism standing after eliminating nine candidates** — well-founded and fitting every on-car constraint, but a hypothesis. They hit **separately observable** symptoms and are **independently backable-out**, so a null on the vibration falsifies `r26` without implicating Change 1.

**Byte-count gotcha:** 35, not 45. Ten of the 36 `r26` bytes were **already `0x00`** — 3072=`0x0C00`, 2048=`0x0800`, 1536=`0x0600`, 2560=`0x0A00`, 512=`0x0200` all have a zero low byte, so zeroing those halfwords moves only the high byte. The builder asserts the exact allowed byte **set**, not a count.

**Verification:** bootloader walk 49/49 and full chain 50/50 on baseline, built image and decoded RWD readback; two CRC trailers recomputed (`0xC4FFC` main block for the code edit, `0xC6FFC` cal block for `r26`); RWD round-trips; x31 checksum valid; part number intact. **Re-verified independently outside the builder, sharing no helper** — CRC walk, Bcond decode, diff and the cipher table all re-derived from first principles.

**How to apply:** flash only on explicit operator instruction naming file and bus. **Score the two symptoms separately.** If the vibration survives, `r26` is falsified and the next free experiment is `STEER_DELTA 3 → 0.75` on the comma — run it as a **separate trial**, not concurrently, or the two vibration interventions become unattributable. Full writeup: `docs/handoffs/2026-07/HANDOFF-2026-07-20-v42-state4-ratchet.md`. Related: [[reference-accord-lkas-lane-is-a-lowpass]], [[reference-accord-gain-rescaling-invariance-partition]], [[v40-governor-slew-root-cause]].
