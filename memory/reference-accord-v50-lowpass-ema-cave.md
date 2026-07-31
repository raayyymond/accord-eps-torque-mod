---
name: reference-accord-v50-lowpass-ema-cave
description: 🛑 NO-FLASH (corrected 2026-07-24 — GATE-1 FAILED on-car; the "gp-0x1500 is V48B-flash-proven/clean" claim here is FALSE, see reference-accord-b7260-io-mailbox-array). 2026-07-22 V50 = V38 + ratchet fix + a FIRST-ORDER EMA LOW-PASS (fc~12 Hz, alpha=74/1024) on the shared torsion-bar signal gp-0x4f60, code cave, keeps 4x. BUILT + verified (50/50 CRC, RWD round-trip, all encoders Ghidra-verified), UNFLASHED. Chosen over V48B's notch because fresh data shows the mode is SPEED-DEPENDENT (~21.7 Hz low-speed -> ~8-12 Hz highway) and alias-unresolved -- a low-pass covers the whole band + rolls off 78.6 Hz harder. Polarity-independent. FOC-current-loop hypothesis RULED OUT as a clean lever. Fix path: V51P probe of gp-0x1300/gp-0x1100 -> V51 rebuild.
metadata:
  type: reference
---

# V50 — first-order EMA low-pass on gp-0x4f60 (code cave); the vibration re-characterized

> **🛑 SUPERSEDED 2026-07-24 — V50 IS NO-FLASH; GATE-1 FAILED ON-CAR.** The V50P probe proved `gp-0x1500`
> has a LIVE WRITER (nonzero on 99.47% of the drive; lead re-decoded rlog 5 to confirm): it is **slot 5 of a
> 40-slot × 8-byte I/O-mailbox array at `0xb7260`**, NOT free RAM — see
> [[reference-accord-b7260-io-mailbox-array]]. So this file's central GATE-1 claim ("single 16-bit cell
> gp-0x1500, V48B-flash-proven, eliminates the RAM-collision failure mode") is **FALSE — gp-0x1500 IS the
> RAM collision**, the very V48B mechanism. Two more corrections: (1) GATE-2 is stable but the built 16-bit
> deadband is a **one-way ratchet** (floor-shift asymmetry → −6.5..−7 count DC bias + a local +15% gain
> bump), NOT the strictly-benign "feature" claimed below — fix = round-to-nearest `(74·d+512)>>10`; (2) two
> active raw `gp-0x4f60` readers (`FUN_0002ec52`/`FUN_0002eda8`) were left unfiltered — being traced for the
> rebuild. **Fix path:** a V51P probe of replacement cells `gp-0x1300`/`gp-0x1100` (outside the mailbox
> array) → V51 rebuild (winning cell + round-to-nearest + repointed raw readers, keeps 4×). Everything else
> below (the vibration re-characterization, the filter math, the cave/trampoline mechanics — trampoline
> transparency was RE-VERIFIED PASS on the built image) stands.

## The decision chain that forced a cave (all prior levers exhausted)
- **FOC current-loop hypothesis (operator's) — RULED OUT as a tractable fix** (firmware-codepath-tracer,
  `.claude/agent-memory/firmware-codepath-tracer/reference_accord_foc_inner_current_loop_architecture.md`):
  the outer command gp-0x6b98 is ABSENT from the FOC core FUN_00071272 (read only for its sign); NO
  isolable Kp/Ki PI pair; the core is a ~5300-instr model-based/feedforward FPU computation reading a
  motor-characterization table at abs 0xC50D0-0xC5D84 — INSIDE the risky 0xC5000 block, OUTSIDE the tooled
  0xC6xxx cal region. Loop rate ~8 kHz. ⚠ **CORRECTED 2026-07-31: that figure was computed conditioned on PCLK = 80 MHz, and PCLK is 40 MHz — so the carrier is likely ~4 kHz, not 8. TSG20's own clock-select register has never been verified, so treat BOTH numbers as open.** It matters independently: it bounds what the actuator can physically do at the 20.9 Hz mode. See [[accord-task5-is-100hz-damper-cannot-damp-21hz]]. Verdict: no clean cal-only FOC lever, and an 8 kHz loop whose
  vibration frequency tracks ROAD speed is the ACTUATOR faithfully delivering a mechanical/outer-loop mode,
  not sourcing an electrical one.
- **Cal-only outer-lane cuts: EXHAUSTED** (V39/V42/V43/V44/V45/V46/V47/V48A all null -> distributed
  anti-damping). No cal-only shared filter exists (each lane filters its own copy). => keep-4x forces a cave.

## The vibration, re-characterized from fresh V38-behavior data (analyze_manual_vibration.py + manual_speed_split.py)
The manual drive (aa5b3e0c01, openpilot 2026.002.000, drives as V38) confirms and SHARPENS the 2026-07-22
re-audit's broad-shelf retraction: the felt mode is **SPEED-DEPENDENT** —
- low speed 3-8 m/s (worst/most-audible regime): **~21.7 Hz** (20-25 Hz band dominates), matches route b9;
- 8-15 m/s: ~8.4 Hz; >15 m/s highway: ~12.5 Hz.
So it spans ~8-22 Hz, sliding DOWN with speed. Broad, low-Q (~4-5), wandering. A fixed narrow 21.4 Hz notch
is fragile (misses the high-speed content); the 21.5-vs-78.6 Hz aliasing is still unresolved. See
[[reference-accord-v49-stagec-flip-collocated-damper]] (the prior broad-shelf finding this extends).

## Why V50 is a LOW-PASS, not V48B's notch
- **Frequency-robust:** a low-pass attenuates the whole 8-22 Hz band at once (a notch centered at 21.4 misses 8-12 Hz).
- **Alias-robust:** fc=12 Hz EMA gives **-6.2 dB @21.4 Hz AND -16.3 dB @78.6 Hz** -> works whether the true
  firmware mode is 21.7 or the aliased 78.6 (a 21.4 Hz notch would be a NULL at 78.6).
- **Polarity-independent:** no sign term -> sidesteps the V49 gp-0x6752 gate (which we still cannot read;
  the route the operator gave was NOT a V49P drive, so the polarity telemetry read as stock -> gate unresolved).
- **Gate-1 simple:** a first-order EMA has ONE 16-bit state cell; V48B's biquad had 4, one of which
  (gp-0x14FA) aliased a live status byte and bricked. One cell removes that failure mode.
- **Deadband is a FEATURE here:** the 16-bit integer EMA (y += (74*(x-y))>>10) has a ~14-count deadband;
  simulation shows it FULLY suppresses ripple <14 counts and OVER-attenuates 20-40 count ripple (-8 to
  -10 dB) — ideal for quenching a limit cycle toward zero. A dead-zone is a <=1-gain nonlinearity -> it
  only ADDS stability, cannot create a new instability.

## Both mandatory gates
- **GATE 2 (closed-loop stability) — CLOSED** (`analysis-2020accord/eps_v50_gate2_lowpass.py`, re-runnable):
  the EMA is STABLE under BOTH the pessimistic (Q_cl=13.6) and the realistic broad-shelf (Q_cl~4.8) loop
  calibrations; hard self-excitation edge 4.66x -> ~21x; no resonant pole (robust by construction);
  stable under +-30 deg carrier-phase error. fc=12 Hz (alpha 74/1024) balances -6.2 dB at the mode vs
  -13 deg feel at 3 Hz. Re-fit to the broad shelf shows the loop is far less marginal than the falsified
  Q=13.6, so this gentle corner suffices.
- **GATE 1 (RAM ownership) — cell chosen on strongest evidence; residual is LOW-risk, statically
  unresolvable, closeable by a live RAM watch:** the single 16-bit cell is **gp-0x1500 (0xFEDF6B00)**.
  Evidence FOR: (1) V48B wrote it every cycle and drove (its brick was gp-0x14FA, a DIFFERENT cell);
  (2) bytes 0-1 direct-clean by two exhaustive methods (all 8 gp-opcode families, readers+writers);
  (3) the CAN-0xE4 handler FUN_00052676 does NOT touch it (lead-decompiled; it reads the 0xE4 bytes from
  gp-0x1424/1426); (4) **the 0xbb640/0xb7260 tables are a BOOT-TIME SELF-TEST / DIAGNOSTIC framework**
  (real table @0xbb560, preceded by ASCII "Failed"/"OK"×4/"UERBuerbSPE" + a {4,8,16,32,64,128} bitmask;
  10 records) — NOT a hot 100 Hz CAN dispatcher, so 0xFEDF6B00 is diagnostic scratch, not a per-frame copy
  target during driving; (5) the table WALKER is UNFINDABLE by static analysis — 3 methods (literal-address
  search, movhi/movea base construction, caller graph) all zero, twice-reproduced over the full 1 MB image.
  **RESIDUAL (honest):** because the walker can't be found, a register-indirect writer is not PROVEN absent
  (won't round "couldn't find" into "no writer" — the V48B gap). BUT the risk profile is MUCH better than
  V48B: worst case = a RARE diagnostic write, and the EMA SELF-HEALS (any stomp is pulled back toward truth
  in ~14 ms; alpha=74/1024) with downstream clamps bounding a single-cycle transient — vs V48B's CONTINUOUS
  1000 Hz monitor-byte alias. **Definitive closure = a live RAM watch (read-only UDS memory-read of
  0xFEDF6B00 at rest + during a drive, confirm static) — a safe pre-flash test.** Cell C is also NOT free
  (a ~600-byte boot-shadow control block); all 10 records share the same unresolved walker -> gp-0x1500 is
  the best-available cell.

## Build (BUILT + VERIFIED, UNFLASHED)
`analysis-2020accord/build_v50_tva.py` + `v50_cave_asm.py` + `eps_v50_gate2_lowpass.py`. V38 + 4 changes,
104 bytes / 12 runs, single MAIN CRC block (0xC4FFC), 50/50 chain on plain + RWD round-trip:
- CHANGE 1 (code, 1B) 0x454FE bne->br — the CONFIRMED state-4 ratchet fix (carried).
- CHANGE 2 (code, 82B) EMA cave @0xC4B34 (trampoline `jr` at 0x7FEAC displacing cmp r0,r8 + mov r8,r14,
  re-executed LAST; runs the 16-bit EMA on a fresh gp-0x4f60 read; 74*d by shift-add — NOT mulhi, which
  truncates to 16 bits; ld.h/st.h gp-0x1500).
- CHANGE 3 (code, 4B) trampoline.
- CHANGE 4 (code, 7x2B) repoint the 7 live carriers gp-0x4f60->gp-0x1500 (Gate-1 reconfirmed sites:
  FUN_0002c478@2c480, FUN_000352b4@354d2/@35aa4, FUN_0003a382@3a6ca/@3a7ca, FUN_0003b49a@3b4a8,
  FUN_0003b66a@3b672). The 2 dormant reads (0x34392/0x34ace) left RAW (stock cal 0xC6498/99=1).
- UNTOUCHED: raw gp-0x4f60/shadow, the 2 hard-shutdown monitors, 2 CAN broadcasts, 0xC646C=3564 (4x),
  the DTC-0x1d damping clamp trap (0xD209C/0xC6554). Every cave ENCODER cross-verified vs real code.bin
  instructions (caught 2 latent brick-bugs pre-build: mulhi 16-bit truncation + ld.w/st.w word-select bit).

## Pre-flash gates — GATE 1 DONE (2026-07-23); GATE 2 has a READY probe
1. **Ghidra re-disassemble of the built `_v50_plain_image.bin` — DONE, PASSED (2026-07-23).** Imported
   (auto_analyze off) + dry_run disassembled: the 82-byte cave decodes as the 27 designed instructions
   (save r10-r13 → ld.h gp-0x1500 → ld.h gp-0x4f60 → sub → shift-add 74·d → sar 10 → add → st.h gp-0x1500 →
   restore → re-exec cmp r0,r8 + mov r8,r14 → jr 0x7feb0). Trampoline (jr 0xC4B34) is TRANSPARENT: at the
   return 0x7feb0 the original bge/subr abs-idiom is intact and the cave's re-exec'd cmp is the last
   flag-setter → r14=|r8| exactly as stock. All 7 repoints decode as ld.h -0x1500[gp],rX (regs preserved);
   the 2 dormant reads stayed raw -0x4f60; ratchet=br, 4x gain=3564, DTC-0x1d clamp trap byte-stock.
2. **Live RAM watch on gp-0x1500 — a READY read-only probe is BUILT + VERIFIED (2026-07-23), NOT YET
   FLASHED/DRIVEN.** `build_v50probe_tva.py` / `_v50probe_plain_image.bin`: V49P/V31P-CLASS telemetry cave
   (i.e. the same proven-safe CAN-spare-bits technique that V31P/V31P-V2 were actually flashed+driven with;
   this specific probe binary has NOT itself been on-car yet) — no scratch RAM, no control-loop change — that
   reads gp-0x1500 into CAN 330 byte4[7:3]/byte7[7:6] on the CURRENT (V38) firmware. Ghidra-verified (ld.bu
   -0x1500,gp,r7 ×2; jarl 0xc4b34,lp). Flash it, drive, decode CAN 330 with `decode_v49p_polarity.py` — if
   gp-0x1500 stays 0 across the drive → nothing writes it → gp-0x1500 CONFIRMED free → V50 flash-ready; if
   non-zero → a writer exists → move the cell. (The current firmware has NO arbitrary-RAM UDS read — its DIDs
   read fixed globals — so this read-only telemetry probe is how the live watch is run. The probe flash is
   itself an operator iron-rule call, but it is the SAFE telemetry class, not the V50 control cave.)
   **⚠ The existing manual rlog `aa5b3e0c01` does NOT count as this drive** — it was captured 2026-07-22,
   before this probe existed, and `compare_330_caves.py` already showed it carries no live telemetry cave
   (CAN 330 byte4[7:3] pinned to the stock V38 pattern; same check that left the V49 polarity gate
   unresolved). A fresh drive with `_v50probe_plain_image.bin` actually flashed is required to close this.
Then the usual: openpilot/pandad killed; explicit operator instruction naming the file + bus. CODE CAVE =
the kit's only bricking class (V24/V27/V48B). If V50 is a PARTIAL cure, lower the corner (fc 12->10->8,
alpha 74->62->50) for more attenuation at more feel cost.

## Related
[[feedback-account-for-prior-iterations-before-new-build]], [[feedback-default-maximal-thoroughness]],
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]], [[reference-accord-v48b-flashed-catastrophic-ram-collision]],
[[reference-accord-v48c-gate2-notch-stable-brick-was-ram]], [[reference-accord-collocation-motor-rate-damper-dead]],
[[reference-accord-v49-stagec-flip-collocated-damper]].
