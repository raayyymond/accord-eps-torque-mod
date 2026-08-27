# HANDOFF — 2026-07-22 (later) — V50 = EMA low-pass cave on gp-0x4f60 (BUILT, UNFLASHED); FOC ruled out

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** V38 on-car (4× LKAS). This session ruled
out the operator's FOC-current-loop hypothesis, re-characterized the vibration from fresh data, and built a
frequency/alias/polarity-robust low-pass cave. **Read `memory/reference/builds/reference-accord-v50-lowpass-ema-cave.md` first.**

## 0. TL;DR
- **V50 = V38 + the state-4 ratchet fix + a first-order EMA LOW-PASS (fc≈12 Hz, α=74/1024) on the shared
  torsion-bar signal gp-0x4f60**, via a code cave that filters gp-0x4f60 into one 16-bit cell (gp-0x1500)
  and repoints the 7 collocated carriers. Keeps 4×. BUILT + VERIFIED, UNFLASHED.
- **Chosen over V48B's notch** because fresh data shows the mode is SPEED-DEPENDENT and the aliasing is
  unresolved — a low-pass covers the whole band and is alias-robust; a notch is fragile.
- **Both mandatory gates addressed.** GATE 2 (closed-loop) CLOSED. GATE 1 (RAM) = best-available cell with
  a LOW-but-not-proven residual, closeable by a live RAM watch.
- **The operator's FOC hypothesis is RULED OUT** as a tractable lever (no isolable PI gains; model-based
  coeffs in the risky 0xC5000 block; the 8 kHz loop is the actuator, not the source).

## 1. The decision chain (why a cave, why a low-pass)
- **FOC current loop (operator hypothesis) — ruled out.** `FUN_00071272` (FOC core) reads gp-0x6b98 only
  for its sign; no isolable Kp/Ki; ~5300-instr model-based/feedforward FPU math reading a motor-char table
  at 0xC50D0-0xC5D84 (inside the risky 0xC5000 block, outside the tooled cal region); loop ~8 kHz. It
  faithfully delivers a mechanical/outer-loop mode; it does not source it. (Agent memory:
  `reference_accord_foc_inner_current_loop_architecture.md`.)
- **Cal-only outer-lane cuts: exhausted** (V39/V42/V43/V44/V45/V46/V47/V48A null → distributed
  anti-damping); no cal-only shared filter exists. Keep-4× ⇒ a cave is the only path.
- **Vibration re-characterized (fresh V38-behavior drive aa5b3e0c01, `studies/spectra/analyze_manual_vibration.py` +
  `studies/telemetry/manual_speed_split.py`):** SPEED-DEPENDENT — ~21.7 Hz at 3-8 m/s (worst/most-audible, matches b9),
  ~8-12 Hz at highway speed. Broad, low-Q. A fixed 21.4 Hz notch misses the high-speed content.
- **openpilot context (operator, this session):** the drive ran op 2026.002.000 with the new
  PID+FF-from-model + a CAN-output low-pass. The bus command carries ~2.5× less HF than the old b9 drive,
  and the vibration PERSISTED — an independent confirmation the fix must be firmware-side (the OP-output LP
  can't fix a base-assist-loop instability). The route was NOT a V49P drive → the V49 polarity gate stays
  unresolved (moot for V50, which is polarity-independent).

## 2. GATE 2 — closed-loop stability (CLOSED)
`analysis-2020accord/studies/models/eps_v50_gate2_lowpass.py` (re-runnable). The EMA is stable under BOTH the pessimistic
(Q_cl=13.6) and the realistic broad-shelf (Q_cl≈4.8) loop calibrations; hard self-excitation edge 4.66×→~21×;
no resonant pole (robust by construction); stable under ±30° carrier-phase error. fc=12 Hz gives −6.2 dB at
21.4 Hz AND −16.3 dB at 78.6 Hz (alias-robust), −13° feel at 3 Hz. Simulation shows the 16-bit integer EMA's
~14-count deadband is a FEATURE — it fully suppresses ripple <14 counts and over-attenuates 20-40 count
ripple (−8 to −10 dB), ideal for quenching a limit cycle; a dead-zone is a ≤1-gain nonlinearity → only adds
stability.

## 3. GATE 1 — RAM ownership (gp-0x1500; low residual, live-watch closure)
Single 16-bit cell **gp-0x1500 (0xFEDF6B00)** = state AND output. Evidence: V48B-flash-proven (its brick was
gp-0x14FA, a different cell); bytes 0-1 direct-clean (two exhaustive methods); the CAN-0xE4 handler
FUN_00052676 doesn't touch it; the 0xbb640/0xb7260 tables are a BOOT-TIME SELF-TEST/DIAGNOSTIC framework
(strings "Failed"/"OK"/"UERBuerbSPE"; 10 records), NOT a hot 100 Hz dispatcher; the walker is UNFINDABLE by
static analysis (3 methods, twice-reproduced over the full image). **Honest residual:** a register-indirect
writer is not PROVEN absent, but the risk is far below V48B (rare diagnostic write + self-healing EMA +
downstream clamps, vs V48B's continuous 1000 Hz monitor-byte alias). Cell C is also not free (boot-shadow
block); gp-0x1500 is the best-available cell.

## 4. The build (`builds/v50_v79/build_v50_tva.py` + `studies/caves/v50_cave_asm.py`, BUILT + VERIFIED, UNFLASHED)
V38 + 4 changes, 104 bytes / 12 runs, single MAIN CRC block (0xC4FFC), 50/50 chain on plain + RWD round-trip:
- CHANGE 1 (1B) 0x454FE bne→br — confirmed state-4 ratchet fix (carried).
- CHANGE 2 (82B) EMA cave @0xC4B34 — trampoline `jr` @0x7FEAC displacing cmp r0,r8 + mov r8,r14 (re-exec'd
  last); 16-bit EMA on a fresh gp-0x4f60 read; 74·d by SHIFT-ADD (not mulhi, which truncates to 16 bits);
  ld.h/st.h gp-0x1500. Every encoder cross-verified vs real code.bin instructions (2 latent brick-bugs
  caught pre-build: mulhi truncation + ld.w/st.w word-select bit).
- CHANGE 3 (4B) trampoline. CHANGE 4 (7×2B) repoint the 7 live carriers gp-0x4f60→gp-0x1500 (Gate-1
  reconfirmed sites). 2 dormant reads left raw. UNTOUCHED: raw gp-0x4f60/shadow, the 2 hard-shutdown
  monitors, 2 CAN broadcasts, 0xC646C=3564 (4×), the DTC-0x1d clamp trap.
- Output RWD: `39990-TVA,A160-V50-LKAS-4x-V38base-ratchet-lowpass-fc12hz-ema-gp1500-...rwd`; plain image
  `_v50_plain_image.bin`.

## 5. 🛑 TWO pre-flash gates still OPEN (V50 is NOT flash-ready)
1. **Ghidra re-disassemble the built `_v50_plain_image.bin`** @ cave 0xC4B34 + trampoline 0x7FEAC + the 7
   repoints (kit rule for any cave; deferred this session for budget). Encoder-level verification is done;
   this is the in-context belt-and-suspenders.
2. **Live RAM watch on gp-0x1500 (0xFEDF6B00-07)** — read-only UDS memory-read at rest + during a drive to
   confirm it's static (closes the Gate-1 residual; static analysis is proven infeasible). Iron rule: the
   exact UDS payload must be confirmed with the operator first.
Then the usual: openpilot/pandad killed; explicit operator instruction naming the file + bus. CODE CAVE =
the kit's only bricking class. If V50 is a PARTIAL cure, lower the corner (fc 12→10→8; α 74→62→50).

**⚠ UPDATE (2026-07-23):** item (1) is DONE (Ghidra re-disasm of the built image, PASSED) and item (2) has
pivoted from a raw UDS read to a CAN-330 spare-bit probe (`builds/v50_v79/build_v50probe_tva.py`, V49P/V31P-class,
BUILT+VERIFIED, UNFLASHED) — see `memory/reference/builds/reference-accord-v50-lowpass-ema-cave.md`. **The existing manual
rlog `aa5b3e0c01` does NOT satisfy gate (2)**: it was captured 2026-07-22, a day before this probe existed,
and `studies/caves/compare_330_caves.py` already confirmed it carries no live telemetry cave (CAN 330 pinned to the stock
V38 pattern — the car was on stock V38 for that drive, same finding that closed out the V49P polarity
question as unresolved). A fresh drive with the probe actually flashed is still required before V50 is
flash-ready.

## 6. Files this session
- `analysis-2020accord/studies/probes/decode_v49p_polarity.py`, `studies/caves/compare_330_caves.py` — the V49P-telemetry check (route
  was NOT V49P; 330 spare bits read stock).
- `analysis-2020accord/studies/spectra/analyze_manual_vibration.py`, `studies/telemetry/manual_speed_split.py`, `archive/inspect_op_config.py` — the
  fresh vibration re-characterization + openpilot-config check.
- `analysis-2020accord/studies/models/eps_v50_gate2_lowpass.py` — GATE 2.
- `analysis-2020accord/studies/caves/v50_cave_asm.py`, `builds/v50_v79/build_v50_tva.py` (+ artifacts) — the candidate.
- `memory/reference/builds/reference-accord-v50-lowpass-ema-cave.md`, `feedback/builds/feedback-account-for-prior-iterations-before-new-build.md`,
  `MEMORY.md`.
- Agent memory: `reference_accord_foc_inner_current_loop_architecture.md`,
  `reference_accord_v50_ram_audit_gp1500_gp14e0_and_status_table.md`.
