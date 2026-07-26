# HANDOFF — 2026-07-22 — 21 Hz re-audit: comma is a passenger; V49 = StageC-flip collocated damper (BUILT, UNFLASHED, GATED)

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** V38 on-car (4× LKAS). This session
re-audited the ~21 Hz vibration from the raw telemetry up, overturned two load-bearing premises, and
produced a build candidate with a hard pre-flash gate. **Read `memory/reference-accord-v49-stagec-flip-collocated-damper.md`
first.**

## 0. TL;DR
- The operator flagged "10 revisions, nothing fixed it — something is wrong with the model." It was.
- **The vibration is a FIRMWARE/PLANT closed loop. The comma is a PASSENGER** — its bus command (CAN 0xE4)
  strips the 21.5 Hz (slew-saturated rate limiter), so no openpilot-side lever (Kp / feedback LPF) can help.
- **The measurement was overstated** (broad 10–22 Hz shelf, not a sharp Q=13.6 line) and the **21.5-vs-78.6
  Hz aliasing is unresolved again** (the "must be 21.5" argument depended on the comma being in the loop).
- **Aggregator topology is COMPLETE** — no missed carrier (gp-0x6ade dead, gp-0x6b62 new but slow).
- **V49 = the ratchet fix + a COLLOCATED torque-rate damper**: flip FUN_0003a382 StageC's derivative sign
  (`subr→sub` @0x3a836) AND band-limit it (pole 0xC644A 1024→64). BUILT + fully verified, **UNFLASHED**.
- **🛑 Flash gate: direction depends on polarity `gp-0x6752` (0xFEDF18AE). +1 = fix, −1 = brick.** It is
  EEPROM-resident (default +1, but not readable from code.bin). **Confirm +1 via a read-only at-rest RAM
  read before any flash.**

## 1. How the model was wrong (the re-derivation, all verified by the lead)
`analysis-2020accord/reanalyze_b9_vibration.py` (re-runnable; dumps `reanalyze_b9_vibration.npz`) re-derived
the measurement from route b9 raw CAN 399, with the decode Honda-checksum-validated (100% over 67,588
frames):
- **21.5 Hz reproduces but is a broad shelf**, ~1.3 dB above the 10 Hz level; true Q ≈ 2–8, not 13.6.
- **Coherence with the openpilot INTERNAL command = 0.66** — which looked like "openpilot is in the loop."
  But the ACTUAL bus command (`sendcan` 0xE4 STEER_TORQUE) coherence is only **0.17**, internal→bus
  attenuation **−10 dB**, no 21.5 peak on the bus. The rate limiter is **slew-saturated** (52% of active
  steps at the ±123/step cap), so Kp/LPF (upstream of the clip) cannot change the bus 21.5 Hz. **Comma =
  passenger.** (Operator's own question — "does the CAN command show the resonance? if not the comma can't
  help" — is what forced this check. It was the right instinct.)
- Multiple coherence(399torque | cmd,angle,rate) = 0.96 → a tight closed loop, no big external driver.

## 2. Topology (carrier-topo trace; lead byte-verified the load-bearing claims)
Sole writer of the aggregator gp-0x6b94 is FUN_0003aa2c (fully decompiled). Complete term list; the only
new lanes are **gp-0x6ade (DEAD, zero writers)** and **gp-0x6b62 (new, slow debounce-like integrator)**.
FUN_0003a382 datapath is disasm-exact (all gains byte-verified): StageA=8·residual (flat), StageC=64·(1−z⁻¹)
(unity-gain derivative, the `subr r14,r15` @0x3a836), S3=integrator 32× down. Everything unity — nothing
filters 21.5 Hz. Polarity gp-0x6752 is EEPROM-resident (irreducible statically; V43's "irreducible gap"
mechanism now pinned).

## 3. V49 — the candidate (`analysis-2020accord/build_v49_tva.py`, BUILT + VERIFIED, UNFLASHED)
Model: `analysis-2020accord/eps_v49_a382_stagec_flip_model.py` (re-runnable).
- Every carrier MAGNITUDE cut failed (V48A cut a382 75% + muted type-8 → null). StageC is the top-ranked,
  never-isolated collocated 1 kHz derivative. **Flipping its sign ADDS damping** (crosses past zero), ~2–3.7×
  the null cut, correct direction — a categorically different move than shrinking anti-damping.
- **★ GATE 2 caught a real flaw in the bare flip:** it creates NEW anti-damping at 55–140 Hz (a derivative
  amplifies with frequency) → brick risk given the 78.6 Hz alias. **Band-limiting StageC (pole 0xC644A→64,
  corner ~10 Hz) fixes it** — damping at 21.5 Hz, NO anti-damping anywhere 1–140 Hz, and (bonus) if the true
  mode is 78.6 Hz the edit is a null not a brick. (V43's pole value, which alone was null; the flip makes it act.)
- Build: V38 + 3 edits, 12 bytes / 5 runs, 2 CRC blocks, 50/50 chain on plain + RWD readback; flip
  re-decodes as `sub r14,r15`; 4× gain + DTC-0x1d clamp trap byte-stock. GATE 1 clean (no new RAM).
  - EDIT 1 (code) 0x454FE bne→br (ratchet); EDIT 2 (code) 0x3A836 subr→sub (StageC flip); EDIT 3 (cal)
    0xC644A 1024→64 (band-limit).

## 4. 🛑 Pre-flash gates (both mandatory, in order)
1. **Confirm polarity gp-0x6752 = +1** via a read-only, at-rest RAM read of abs `0xFEDF18AE` (not steering →
   no OBD-mux blocker; exact UDS payload confirmed first, iron rule). **+1 → flash OK to try; −1 → DO NOT
   FLASH (brick).** Default is +1 and a working car strongly implies +1, but it is an inference.
2. **Ghidra re-disassemble `_v49_plain_image.bin` @0x3A836** to confirm `sub r14,r15` (kit rule for any code
   edit; the build's programmatic V850 decode already agrees).
3. Then the usual: openpilot/pandad killed; explicit operator instruction naming the file + bus.

## 5. Honest residuals / open items
- **a382 is a MINORITY carrier** (V48A null) → V49 may be a PARTIAL cure even at +1 (it cannot brick at +1).
  If partial with the mode confirmed at 21.5 Hz, raise the StageC pole (64→96→128) for more damping + re-check
  the HF band.
- **Aliasing unresolved** (21.5 vs 78.6 Hz) — needs a >100 Hz witness (motor-side telemetry, blocked) to
  settle; the band-limit is chosen to be null-safe if it's the alias.
- **Golden models stale:** `eps_loop_gain_model.py` / `eps_v48c_gate2_closed_loop.py` are calibrated to the
  falsified Q=13.6 / |L|=0.875 sharp-line reading and should be re-fit to the corrected broad shelf.
- FUN_00022ca0 task period (damping/boost rate) and FUN_000352b4's 2-state float filter remain unreversed
  (secondary now that V49 is the lead).

## 6. Files this session
- `analysis-2020accord/reanalyze_b9_vibration.py` (+ .npz) — the re-derivation (comma-passenger, shelf).
- `analysis-2020accord/eps_v49_a382_stagec_flip_model.py` — the GATE-2 model (flip + band-limit).
- `analysis-2020accord/build_v49_tva.py` (+ `_v49_plain_image.bin`, `…-V49-…rwd`) — the candidate.
- `memory/reference-accord-v49-stagec-flip-collocated-damper.md`, `memory/feedback-default-maximal-thoroughness.md`,
  `memory/MEMORY.md`.
