# ADVERSARIAL PASS — V289 rev 1 — pre-registered FAIL criteria (written BEFORE the build exists)

Orchestrator, 2026-09-08 evening. V289 = V282 + (1) a second-order notch (20.05 Hz, Q 3, DC 1) code cave on the
clamped LKAS PID sum S, hooked at 0x2A174, (2) cal 0xC63E8/0xC63EA 923/1560 → 875/2301 (feedback lag pole 16.5 → 25 Hz,
DC 30.89 held), (3) 0x14A byte-4 rung: b5 = sign(S−y), b7 = |S−y| ≥ |y|, b4/b6 kept, b0–2 stock.
Design: `docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md`. Trace: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`.

**The pass must be able to return "do not flash". Any one of the following is a FAIL for its surface:**

## A — ARITHMETIC (re-derive from the IMAGE bytes, never from the script)
- A1 The cave's realised transfer, computed from the integer coefficients READ FROM THE IMAGE, differs from the design by
  more than 0.3 Hz in f0, or DC gain ≠ exactly 1 (integer identity at x = const for all |x| ≤ 15360 after settling), or notch depth < 20 dB.
- A2 Any int32 overflow of the accumulator or state for |S| ≤ 15360 under worst-case state (analytic bound AND exact-integer
  chirp/step/rail tests with V850 `sar` floor and 32×32→32 `mul` semantics).
- A3 Limit cycle / stuck-LSB: with S = const the output does not settle to exactly S, or with S = 0 the state does not decay to 0.
- A4 Any operand-order, sign, width (ld.h vs ld.hu), displacement or branch-target error in the cave or rung, decoded with an
  INDEPENDENT decoder and confirmed in Ghidra on the built image; the displaced `ld.hu 0x73ee,tp,r7` not replicated before return.
- A5 Register clobber: r16, r22, r24, r27, r29, lp, or r12-after-write touched; any `jarl` in the cave.

## B — UNITS / LOOP / GATE 2
- B1 The fb-pole cal DC gain not held: 2·b/(1024−a) departs from 30.89 by > 0.5 %; or the cell widths/signedness wrong (2301 must fit).
- B2 GATE 2 recomputed from the bytes on the census-fitted plant: loop gain below 5 Hz changed by > 5 %; the 7 Hz strong-turn
  gate |Ls·R + Lr| > 1.02 (re-arms the 7 Hz ring); phase at 3.9 Hz (openpilot outer loop) worse than −5°.
- B3 Peak wheel rate or peak acceleration on a capped-frame command step (mirror, byte-exact) falls below 0.95× V282 (authority cut).
- B4 The notch band of removed content, measured on the r5e_v288 / r39 setpoints through the full mirror, does NOT reduce the
  18–22 Hz content of S by ≥ 6 dB — i.e. the cave would be inert on the wire.

## C — BUILD-SCRIPT AUDIT
- C1 Independent rebuild does not reproduce the image hash; CRC over [0x13000, 0xC4FFC) does not match the stored cell.
- C2 Full-file diff vs the V282 image contains any byte outside the declared runs (hook, cave, rung, two cal cells, CRC).
- C3 Assertion census: any assertion the script calls decisive that is entailed by the base hash or is a readback of what was
  just written; docstring text that describes a different revision than the bytes.
- C4 More than one flashable V289 rwd on disk, or a name that does not match the image.

## D — INTERLOCKS / GATE 1 / DOWNSTREAM
- D1 Any reader or writer of the chosen state/handoff words anywhere in the image (Ghidra xrefs + raw LE scan of all gp-relative
  forms incl. ld.b/st.b and bit ops, movhi/movea proximity, absolute pointers, block clears) other than the new cave/rung.
- D2 Any path that reaches 0x2A178 without passing 0x2A174 (the cave skipped while its state is consumed), or a path where the
  notch state carries a stale value into the first engaged tick large enough to change T by > 5 % (needs the 0x2A0C6 S value).
- D3 The output-lag / gain / clamp stage downstream consuming y with a width narrower than S (truncation), or any interlock
  (EME, oscillation detector FUN_000428d4 on gp-0x6c2c, lockstep) whose input changes because S is notched.
- D4 The rung overwrites a stock Honda bit (b0–2) or a bit another decoder depends on without a documented remap.

A finding that does not meet a criterion above is a residual to record, not a FAIL. Findings after acceptance are reports.
