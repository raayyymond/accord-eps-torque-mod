# HANDOFF — 2026-07-21 (late) — V48B: the 21.4 Hz notch, BUILT + Ghidra-verified (code cave)

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** V38 on-car.
**Headline:** The 21.4 Hz notch (V48B) is no longer a design — it is a **BUILT, byte-exact,
CRC-clean, RWD-round-tripped, and fully Ghidra-re-disassembled** code-cave candidate. It is
**UNFLASHED**. Read `docs/VIBRATION-DOSSIER.md` first for the *why*; this handoff is the *how* and the
verification record.

> ⚠ **CODE CAVE — the kit's only change class that has ever bricked (V24/V27).** This one reuses the
> exact trampoline/CRC/cave plumbing V31P flashed and drove on-car (jr/jarl into `0xC4B34`), so the
> *plumbing* is proven; the **new** risk is the cave's arithmetic (a biquad), which is why every
> instruction was independently decoded by Ghidra from the built image. Flash only after the one open
> safety item (§5) is closed and on explicit operator instruction naming the file + bus.

---

## 0. What V48B is (one paragraph)
V48B = V38 + the confirmed state-4 ratchet fix (`0x454FE` bne→br) + a **21.4 Hz notch biquad** inserted
as a code cave. The cave reads Sensor-B/TAS torque `gp-0x4f60`, runs a Direct-Form-I Q12 notch, and
stores the **filtered copy** to a new RAM cell `gp-0x1500`. The 7 **live** base-assist carrier reads of
`gp-0x4f60` are repointed to read that filtered cell instead; the raw `gp-0x4f60` (shadow-lockstep +
2 hard-shutdown monitors + 2 CAN) is left completely untouched, as are the 2 mode-gated **dormant**
carrier reads. This is the split-independent, least-feel-affecting lever from the loop-gain model — the
one guaranteed to attenuate the 21 Hz loop gain regardless of which collocated carrier dominates, which
is exactly what the V48A null (muting the two "strongest" carriers did nothing) pointed to.

## 1. Files
- `analysis-2020accord/build_v48b_tva.py` — the builder. Produces the RWD + `_v48b_plain_image.bin`.
- `analysis-2020accord/v48b_cave_asm.py` — the cave assembler (every encoding cross-validated vs ≥2 real
  `code.bin` instructions; the single source of truth for the cave bytes).
- `analysis-2020accord/eps_v48b_notch_design.py` — RBJ→biquad design + fixed-point validation (unchanged).
- `analysis-2020accord/eps_v48b_cave_model.py` — **NEW** bit-exact model of the cave's integer math
  (`mulhi` 16×16→32, int32 accumulate, `sar 12`, clamp ±25600, int16 state); proves notch depth,
  DC-unity, and no int32 overflow even at full ±32767 input; emits golden I/O vectors.
- Artifacts (gitignored, under `../accord-firmware/flashing-2020accord/rwd/`):
  `39990-TVA,A160-V48B-LKAS-4x-V38base-ratchet-notch21p4hz-Q12-DFI-gp1500-0x13000-0x100000.rwd`
  (SHA-256 `0d25f022…`), image `_v48b_plain_image.bin` (SHA-256 `a26b0571…`).

## 2. The notch (validated numerically)
- RBJ peaking-dip, f0=21.4 Hz, Q=5, −8 dB, fs=1000 Hz → **DF-I Q12 int16 coeffs
  `b0=4045 b1=-7949 b2=3977 a1=-7949 a2=3926`** (scale 4096).
- Cave-exact integer sim: **−7.9 dB at 21.4 Hz**, ~0 dB in-band, and **exactly +0.000 dB at DC**
  (`(b0+b1+b2)/(a0+a1+a2) = 73/73 = 1.000` → *zero* steady-state torque offset; feel preserved).
- Pole r=0.979 (stable); accumulator peaks 92M and is provably < 2^31 with ≥2× margin even at the full
  ±32767 int16 sensor range; states fit int16. Output clamped to ±25600 (= the monitors' own ±0x6400).

## 3. The cave (138 bytes @ `0xC4B34`, 41 instrs) — Ghidra-verified from the built image
Entered by `jr 0xC4B34` at `0x7FEAC` (the producer `FUN_0007f3f8`'s shared epilogue, where `r8` =
settled `gp-0x4f60`). Sequence:
1. `addi -16,sp,sp` + `st.w r10/r11/r12` — save scratch (transparent).
2. Biquad on a **fresh** `ld.h -0x4f60[gp]` (not via r8): a uniform `mulhi`/`add` chain with immediates
   `[b0,b1,b2,-a1,-a2]=[4045,-7949,3977,7949,-3926]` over `[x,x1,x2,y1,y2]` → r10 (int32 acc).
3. `sar 12,r10`; clamp to ±25600 via `movea 0x6400/0x9c00` + `cmp` + `ble/bge +4` skipping one `mov`.
4. State shift `x2=x1; x1=x; y2=y1; y1=y` (y1 IS the output cell `gp-0x1500`).
5. `ld.w r10/r11/r12` + `addi 16,sp,sp` — restore; **then** re-exec `cmp r0,r8`+`mov r8,r14` **last**
   (so the `bge 0x7feb4` at the return address sees the correct flags); `jr 0x7FEB0`.

**Transparency property (the anti-brick invariant):** the only registers whose values differ across the
hook vs. the original two instructions are r10/r11/r12 (saved+restored → identical) and r14/flags
(reproduced by the re-exec'd cmp/mov). r8 is never written; sp is restored exactly. So state at `0x7FEB0`
= original + the notch RAM write, nothing else.

**Independent Ghidra decode of the BUILT image (`disassemble_bytes`, dry_run):** all 41 cave instructions
decode as intended — `mulhi` immediates = the exact coefficients (`0xfcd/-0x1f0d/0xf89/0x1f0d/-0xf56`),
clamp `movea`s = ±25600, `ble/bge` skip exactly their `mov`, final `jr` resolves to `0x0007feb0`; the
trampoline `0x7FEAC` = `jr 0x000c4b34` with the return path (`bge 0x7feb4`, `subr r0,r14`, `ld.hu`) intact;
repoint `0x3A6CA` = `ld.h -0x1500,gp,r10` (reg preserved); ratchet `0x454FE` = `br 0x000455c4`.

## 4. RAM + repoints
- **RAM (gp=0xFEDF8000):** y1/output = `gp-0x1500` (0xFEDF6B00, **V31P flash-validated** free; `.bss`
  map is identical across V31/V38); x1/x2/y2 = `gp-0x14FC/14FA/14F8` (0xFEDF6B04/06/08 — a clean run
  bounded by single flag bytes, clear in both the gp-relative scan and the resolved register-indirect
  set; the whole `0xFEDF6xxx` window has exactly one register-indirect access, at `0x6898`).
  ⚠ A prior record claimed `gp-0x14E0` was a 4-byte free word — **corrected**: 3 of those bytes are live;
  the true free run there is `0xFEDF6B20–0x6B23`. The **256-byte block at `gp-0x7F00` (0xFEDF0000) was
  REJECTED** — it's a page base with 433 `movhi 0xFEDF,r0,rX` sites, impractical to prove clean.
- **Repoints (7 LIVE, patch disp16 only: `a0 b0`→`00 eb`, opcode+dest reg unchanged):** `FUN_0002c478`
  @2c480, `FUN_000352b4` @354d2/@35aa4, `FUN_0003a382` @3a6ca/@3a7ca, `FUN_0003b49a` @3b4a8,
  `FUN_0003b66a` @3b672. The 6 previously-unclassified `gp-0x4f60` readers are ALL classifier /
  return-center / UDS-diagnostic consumers (subagent-confirmed) → correctly keep RAW. Producer runs
  before all carriers in the 1 kHz task → the filtered copy is **same-cycle fresh**.
- **NOT repointed:** the 2 dormant reads `FUN_00034350` @0x34392 / `FUN_00034a72` @0x34ace — bypassed in
  stock cal (`0xC6498/99`=1); the red-team confirmed they're the dormant fallback arm of a cal-gated
  **mux** (not a comparator), so leaving them raw is correct. Available as an operator option.

## 5. Safety review (adversarial) — status
- **Byte/CRC:** 50/50 CRC (single MAIN block `[0x13000,0xC4FFC)` — every edit lives there), RWD
  round-trip, exact diff vs V38 = 160 bytes / 12 runs (ratchet + cave + trampoline + 7×2 repoint + CRC).
  4× gain `0xC646C=3564` and the DTC-0x1d clamp trap (`0xD209C`/`0xC6554`) byte-stock.
- **Raw `gp-0x4f60` / shadow `gp-0x4486`:** never touched → zero interaction with the shadow-lockstep
  (fault 0x17), the 2 hard-shutdown monitors, the 2 CAN broadcasts, diagnostics.
- **Lockstep-asymmetry red-team (V27 class):** type-8 lockstep `FUN_00027b0a` = **matched-safe** (0 raw
  `gp-0x4f60` reads; both sides trace to the one filtered read via the shared slot array). All other
  repointed-lane consumers (`gp-0x6b86`, `gp-0x6ad4`, `gp-0x6ad6`, `gp-0x6ba6/9a`) = **0 raw reads**.
  `FUN_00043e44` (DTC 0x1d) `gp-0x4f60` read = a ±25.0 plausibility sanitize, unrelated to its lockstep.
- **✅ THE LAST ITEM — `FUN_00042af8` (DTC 0x1c) — CLOSED, SAFE.** Traced `gp-0x6afa` to the terminal
  compare (`reference_accord_v48b_monitor1_dtc1c_notch_safety_closed.md`). The DTC-0x1c trip is **not** a
  magnitude/upper-bound "fight" gate — it is an **int/float lockstep**: `FUN_00042af8` (int) and
  `FUN_00043e44` (float, DTC 0x1d) independently recompute the **same** cal-gated (`0xC64CB`, exactly 2
  readers program-wide) formula from the **same** `gp-0x6b4a` cell, agreeing to a ±5-count tolerance,
  driving `gp-0x3564` (+10/cyc, thr 100). Both engines read the **already-notched** sample → matched, not
  a raw-vs-filtered split. A shared-input perturbation cannot erode int/float agreement (both still agree
  to ≪ ±5 counts regardless of input value), and a strictly-attenuating (never-peaking) notch can only
  **shrink** the ~1-tick per-cycle delta the tolerance already absorbs. Same "matched, not V27-class"
  pattern as the type-8 lockstep and the damper/boost mux. Residual (flagged, low): fault-bit-8's exact
  self-consistency formula was read from decompiler output, not disassembled instruction-by-instruction —
  same upstream lineage on both operands, no raw/filtered split found.

- **NET SAFETY VERDICT: no asymmetric raw-vs-filtered divergence-trip mechanism exists at any monitor.**
  Raw `gp-0x4f60`/shadow untouched; type-8 lockstep matched; all other repointed-lane consumers have 0
  raw reads; damper/boost dormant reads are a cal-gated mux (not a comparator); DTC-0x1c/0x1d corridor
  monitors are a matched int/float lockstep on a shared notched input. **This is a code cave** — the
  ultimate check is still first-minutes on-car observation after flash; nothing above substitutes for it.

## 6. What "finished" means here / next steps
1. **Close §5's `FUN_00042af8` item** (final trace in flight) → then V48B is fully safety-signed.
2. **Operator flash decision** — code cave; flash only on explicit instruction naming the file + bus,
   after killing openpilot/pandad. On-car: watch for any DTC / dash light in the first minutes (the
   cave runs at 1 kHz from ignition).
3. If V48B kills the vibration → the two-inertia mode + the collocation/loop-gain model are confirmed and
   the ratchet-#2 (vibration-induced) should vanish with it. If null → per the dossier, the anti-damping
   may be more mechanically dominant than firmware can fully cancel from this injection point; the
   remaining firmware options are a collocated torque-rate damper (V48-D) or reducing 4× (rejected).

## 7. Method notes worth keeping
- The handoff record said "return to `0x7feb4`" — **wrong**; the return is `0x7FEB0` (the flag-consuming
  `bge`), decoded from bytes and Ghidra-confirmed. Returning to `0x7feb4` would have skipped the `bge`.
- `disassemble_bytes` decodes bytes *resident at an address*; to verify a built image, **import it**
  (`V850:LE:32:default`, base 0) and dry-run-disassemble — the established pattern (a `_v39` image was
  already imported in the project).
- `FUN_0004c780` has a **6-byte** `ld.h -0x4f60[gp]` (extended-disp form) — not a repoint candidate, but
  it disproves "every `gp-0x4f60` read is the 4-byte `24 XX a0 b0` idiom." Worth a memory note.
