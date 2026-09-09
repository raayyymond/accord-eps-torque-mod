# HANDOFF 2026-09-09 — V288 flew and was inert on the grind; the 20 Hz line is a plant mode the loop de-damps; V289 (notch on the loop output + fb pole 25 Hz) built, adversarial pass complete, accepted

**Read `docs/STATE.md`'s decision box first.** This is the narrative of the 2026-09-08 → 09 session (the PC shut down once mid-close-out; nothing was lost — every agent's deliverable was on disk).

## 0. One paragraph
The operator drove V288 rev 2 (route `…0000005e--03a9714d78`, 642 s engaged) and bookmarked three grinding episodes. The cave was live and did what it was sized to do (D-clamp binds ×0.03), and the grinding was **unchanged** on V282's own census yardstick — same 20.0–20.4 Hz line, same rate, amplitude and trigger class, one bookmark louder than any V282 episode. That closes the reference-side class. A nine-route, five-build census then showed the line is a **plant mode the LKAS rate loop de-damps** (frequency pinned across Kp 248–696, rising 0.4 Hz with gain while damping falls), not the loop's own crossover; the record's "PM 35–60°" was a stream-offset artefact. The loop's phase at 20 Hz is dominated by two Honda filters nobody had touched, both INSIDE the loop: the 5.05 Hz output lag and the 16.5 Hz feedback lag. The design study ranked the pair "notch 20.05 Hz Q3 on the clamped loop output + fb pole 16.5 → 25 Hz" as the only candidate neutral on every gate. It was built as **V289 rev 1** on the V282 base (185 bytes / 10 runs / two CRC pages), passed adversaries A, C and D, failed B's pre-registered transient-authority criterion B3 (capped-step peak rate ×0.91, accel ×0.93; steady state ×1.00), and the operator **accepted rev 1** with that stated. Expected effect if right: rings decay ≈ 1.7× faster and stop being sustained — not a cure.

## 1. How the session ran (orchestrator + 14 agents; every crux re-verified from disk or bytes)
| agent | surface | outcome |
|---|---|---|
| `qlive` | build identity, filter lag, wallow | V288 live (99.5 % agreement); lag ~3 ms at crossings by construction (unit-slew follower < 16 counts); no 1–3 Hz wallow |
| `marks` | the three bookmarks | 20.12 / 20.00 / 20.39 Hz; env 450 / 177 / 651 (r39 max 397); trigger class unchanged; audio blind |
| `census` | V282 yardstick on V288 | reproduction exact; 258 vs 239 ep/h; f 20.06 vs 20.03; D-bind ×0.03; rung-bell ratio unchanged; no line > 22 Hz |
| `loopshape` | mode nature + loop-shaping design | plant mode; phase budget; ranked pair; struck output-lag pole, leads, D filter |
| `tracer`, `tracer2` | rate-loop lags, hook 0x2A174, RAM census, 0x2A0C6 route | output lag INSIDE the loop; hook = convergence point; r6/r7/r9/r13 scratch; 0x2A0C6 gated on a never-written byte, S ≤ 832 there |
| `builder` | V289 rev 1 | 185 B, two CRC trailers; TDF-II + error feedback; FLAG halfword; docstring fixes after C |
| `advA/B/C/D` | the four surfaces | PASS / FAIL-B3-accepted / PASS / PASS |
| `lerps`, `golden` | page data from the image; golden model | no undeclared cell; contract 90 symbols, hash unchanged |
Orchestrator re-verified: bookmark cores (own recompute), bit-5 duties, 0x2A170–0x2A1F8 bytes in Ghidra, the mode-nature tables, V289 hashes / diff / both CRCs / cal cells / hook bytes, the golden contract.

## 2. What changed my mind, in order
1. **"Cut the excitation and the bell shrinks" was falsified on the wire**, cleanly: the excitation the filter targeted is measurably gone and the bell is the same size. The amplitude is set by the loop's damping.
2. **Crossover vs plant mode** flips every candidate's verdict, so the census had to be run before any ranking was trusted: frequency vs gain settled it (a crossover moves down 2–4 Hz with −26° of controller phase; the line moved UP 0.4 Hz).
3. **The V287 design doc had struck the fb pole on a misread** (0x2A1E6 is y × the engagement ramp). Two tracers and my own byte read agree.
4. **A tracer's "free RAM" was wrong on two of three runs** — its sweep missed byte forms. The builder's byte-granular scan and adversary D's independent census caught it; only the 12-byte run gp-0x6c44..gp-0x6c39 is used.
5. **B3 failed because the design's authority row was for a different topology** (notch on the feedback operand). The built notch on the loop output removes the ring's own overshoot on a step. The operator judged that acceptable; it is recorded as his decision, not mine.

## 3. Process lessons (for the skill, not this file)
- Subagents waiting on a background Bash run were **never woken** by its completion (three times: census, loopshape ×2); each sat idle for up to 2.5 h until I inspected processes and messaged them. Check `Get-CimInstance Win32_Process` and the log mtime before believing "still running".
- The builder ran a per-tick byte emulator that copied the 1 MiB image every tick (~10 min per run) and iterated four times without reporting. The fix that landed: FAST (2 s) gates the write, `--full` (4 s) runs the sweeps on the pure-Python mirror with a short byte==mirror equivalence. **Ask for that split in the brief.**

## 4. On disk
- Candidate: `../accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd` sha256 `20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c`; image `_v289_…_plain_image.bin` `f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed`.
- Script `analysis-2020accord/builds/v108_plus/build_v289_tva.py`. Design `docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md`. Trace `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`. Prereg + verdicts `docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md`, `ADV-V289-{A,B,C,D}-*.md`, `V289-LERPS-FROM-IMAGE-2026-09-08.md`.
- Drive reads: `rlog-tools/studies/grind/{V288-QLIVE,V288-MARKS,GRIND1-CENSUS-V288}-R5E-2026-09-08.md` (+ scripts), `loopshape20_{mode_nature,loop_model}.py`. Extractors `rlog-tools/decode/extract_r5e_v288.py`, `studies/grind/extract_r5e_v280cache.py` (cache key `5e2` / `r5e_v288`).
- Page: https://claude.ai/code/artifact/6ee52635-8425-4d63-86a7-6a2b60e7a444
- Golden model: `lkas_sum_notch`, `lkas_fb_lag` (SECTION 5C), contract 90 symbols, hash `740f4bcd…` unchanged.

## 5. Decoder note for the first V289 drive
0x14A byte 4: **b5 = sign(S − y)** (1 when the notched-out component is negative; duty ≈ 0.50 engaged = alive; read its cross-spectrum with the 0x18F rate at the line), **b7 = |S − y| ≥ |y|** (predicted 0.10–0.11 engaged at the 100 Hz instants, 0.12–0.37 in bookmark windows; **reads 1.000 while disengaged — score engaged-only**), b4/b6 unchanged from V282, b3 as V282, b0–2 stock. V288's "b5 = sign(y)" no longer applies.

## 6. Open items
1. Revert signatures to watch: new line at 14–17 Hz or 22–24 Hz; a sustained ~16 Hz lower-pitch grind (smooth-plant branch); any new straight-road vibration.
2. On the design's fit (iii) the pair's ζ falls while the notch alone holds — if the drive is a null, the notch-alone Q4 fallback is the next candidate, not a re-cut of the pair.
3. 1 kHz task slack unmeasured (~2.5 µs estimated for the cave); FLAG halfword 0 for ~30 instructions per tick (preemption residual); register-indirect RAM residual.
4. Golden model: the rate PID stage (E former, P/D, gain LERPs 0xCBB54/0xCBC34/0xCBBC4/0xCBAE4) is still absent.
5. `docs/STATE.md` 179 KB, `BUILD-LINEAGE.md` 204 KB — both under the cap; archive older STATE blocks at the next close-out.
