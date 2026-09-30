# V295 census — FAIL / surprise criteria

**Process note (honest):** this file was written AFTER the first byte reads, decompile and reader census
(c1, c2, c4) had run and BEFORE c6 (trim frequency response). The criteria below for c1–c5 are therefore
post-hoc statements of what would have been a FAIL; the checks that were genuinely pre-committed in code are
(i) the sha256 assertions in `c1_images_and_cells.py` (abort on mismatch) and (ii) the 23 positive controls in
`c2_reader_census.py` (abort on any failure).

A FAIL / surprise for this census would be any of:
- F1: V294 image sha256 != 3143616d…; or the Ghidra program's bytes at 0x28FA4 / 0x29D76 / 0xC63E8.. differ
  from the file (stale import).
- F2: the code region of V294 differs from V293/V282 anywhere except 0x28FA4 / 0x29D76 (a hidden code edit).
- F3: any positive control of the scanner fails (its nulls would be worthless).
- F4: Ghidra `search_instructions` on the fully analysed stock program and the raw Python scan DISAGREE on the
  site set of any load-bearing cell (Ki, deadband, I state, clamps, fb cells, output lag, dither enable, EME).
- F5: the I integrand is NOT E>>5 of the post-shift E (e.g. a separate sp - fb>>5 path) — this would change
  what a Ki does on V294.
- F6: any leak / decay / conditional-integration path on gp-0x6dd0 besides the clamp and the 0x2A164 reset.
- F7: any live reader of a PID cell (gp-0x6dd0, gp-0x6cf8, gp-0x6b32/34/36/2e, 0xC62E4, 0xC63E6, 0xC61BA/BC/B6/BE,
  0xC63EC/EE) OUTSIDE FUN_00028ea6 and the uncalled island 0x2A30E–0x2B421 — a hidden consumer/interlock.
- F8: my integer mirror and the golden model's `lkas_rate_pid_tick` disagree on any tick of the V294 cal
  (with and without Ki/Kd made live).
- F9 (surprise, c6): the trim's phase at the 2–2.7 Hz wheel mode is NOT predominantly damping (|phase from pure
  rate damping| > 45°) for the as-built cells.

Outcome (filled after computing): F1–F8 did not fire. F5 checked two ways (decompile line 977–992 and the
listing 0x29D76–0x29D9A). F9: see c6 output in the report.
