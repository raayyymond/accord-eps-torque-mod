# ADVERSARIAL PASS — V291 (C10), pre-registration

**Written by the orchestrator BEFORE the image existed on disk and BEFORE any adversary was briefed.**
Per `CLAUDE.md`: a build's own assertions cannot falsify it; this pass exists to make it FAIL. Four
independent agents, disjoint surfaces, each re-deriving from the BUILT IMAGE, never from the build
script's constants or from this brief. Verdicts are appended below by each agent; the orchestrator
verifies the crux of every decision-bearing finding before acting on it.

## The build under attack

**V291 = V282 + three calibration halfwords in the 0xC6000 page (+ its CRC at 0xC6FFC).** Class:
*open the LKAS rate loop at high frequency + partial revert of Lever B*. Design record:
`docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` (body + Addenda A–D), traces
`docs/traces/TRACE-2026-09-13-fb-lag-filter-bytes.md`,
`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`, wire
`rlog-tools/studies/grind/OPENLOOP-RING-DAMPING-2026-09-13.md`, `B-OF-F-V282-2026-09-13.md`.

| cell | V282 | V291 (C10) | what it is |
|---|---|---|---|
| `0xC63E8` (tp+0x73E8, `a`, `ld.h` SIGNED @0x28F8A) | 923 | **962** | LKAS rate-PID feedback lag pole, `s_new = (a·s>>10) + (b·x>>10)`, `r26 = s + s_new` |
| `0xC63EA` (tp+0x73EA, `b`, `ld.hu` @0x28F86) | 1560 | **958** | same filter; DC = 2b/(1024−a): 30.891 → 30.903 (held); corner 16.53 → 9.94 Hz |
| `0xC6446` (tp+0x7446, `ld.hu` @0x3AC08, Q10) | 5244 | **4725** | r24 ENGAGED gain arm (V84's Lever B, stock 512); −9.90 % |

Optional, decided by the builder: a displacement-only re-point of the 0x14A cave's b7 rung to read
`sign(s)` (gp-0x3d30 low halfword) as the in-situ phase instrument. If present, the 0xC4000 page CRC
at 0xC4FFC also changes and surface D must attack the rung.

## What a FAIL looks like — fixed before the pass runs

**Any one of the following is a FAIL, and a FAIL on A, B(1–4) or D(1–3) is "DO NOT FLASH".**

### A — ARITHMETIC (re-derive from the image; hunt overflow, sign, truncation, width)
1. The realised DC of the feedback filter from the BUILT bytes differs from 30.891 by more than 0.5 %,
   or the realised corner is outside 9.94 ± 0.4 Hz.
2. Any int32 overflow in `a·s` or `b·x` with |x| ≤ 12000 and the state at its steady state 15.4·x,
   or the state cell is not 32-bit on the live path.
3. The feedback quantiser dead zone at b = 958 exceeds 0.15 deg/s (expected 1024/958 = 1.07 raw
   counts = 0.134 deg/s), or the negative-state stick zone exceeds 2× V282's.
4. The r24 arm arithmetic: 4725 is not read `ld.hu` at Q10, or `u·4725` can overflow int32 with the
   ±5120 input clamp, or the ±3 deadband / ±8192 clamp behave differently at 4725 than at 5244 in a
   way not proportional.
5. `a` is not ≤ 1023 or would sign-extend wrongly through the `ld.h` at 0x28F8A.

### B — UNIT / SCALE CHAIN and CLOSED-LOOP STABILITY (GATE 2), re-derived from bytes
1. Any of the 121 linear-stable family fits goes unstable under C10 (byte-exact electronics).
2. The record's 7.3 Hz gate exceeds 1.01 under EITHER r24 scaling — the cal scaling (k = 0.9010) or the
   wire's effective-arm scaling (bof: effective ≈ 0.45× the cal) — or the folded (r24-embedded) gate
   disagrees with the surrogate at k = 1.
3. Max |1/(1+L)| over 12–26 Hz is not reduced by at least ×2 vs V282, or a NEW lightly damped pole
   (ζ < 0.05) appears anywhere in 3–30 Hz on any fit.
4. |T(3.9)| > 1.15, or |ΔL| below 5 Hz > 30 %, or byte-exact capped-step overshoot > 1.205 (1.6×
   V282's worst), or steady-state authority ≠ ×1.00 ± 1 %.
5. The 5–9 Hz sensitivity bump reaches or exceeds 1.0 on the worst fit (C10 predicts 0.91).
6. The k-folded 20 Hz columns (Addendum D) move C10's ring ratio below ×2.43 (the readability floor)
   once the r24 cut's loss of 20 Hz damping is included.
7. openpilot's outer loop: the record's adverse bound (≤ 0.38) × C10's |T(3.9)| exceeds 0.5.

### C — BUILD-SCRIPT AUDIT
1. An independent rebuild from the V282 image does not reproduce the reported image and rwd sha256.
2. The full-file diff vs V282 is anything other than the payload bytes of the three cells (+ the cave
   rung bytes if the telemetry switch is on) plus the touched page CRC trailer(s).
3. The rwd does not decode back to the plain image with the kit's own decoder, or any page CRC is wrong
   by the kit's CRC routine.
4. The assertion census finds a load-bearing claim that is tautological (a readback of what was just
   written) or entailed by the base hash, presented as evidence of the edit's effect.
5. More than one V291 `.rwd` exists on disk, or a `SUPERSEDED` name is missing where a rev was replaced.

### D — INTERLOCKS AND DOWNSTREAM (GATE 1 and consumers)
1. Any reader of tp+0x73E8 / tp+0x73EA other than 0x28F8A / 0x28F86, or any reader of tp+0x7446 outside
   the r24 gain-select block, on the BUILT image by raw byte scan (4-byte and 6-byte forms) AND Ghidra.
2. Any consumer of the feedback state gp-0x3d30 other than the filter's own ld.w/st.w, or any path on
   which the state can be stale at re-engage (the filter must run every tick).
3. The r24 change reaches the EME shaper, the governor's slew cal (0xC6206/08), the lockstep monitors or
   the DTC plausibility thresholds in a way that changes their trip conditions — or the `gp-0x671d` latch
   (which collapses r24 to 1024 on V280+) becomes reachable where it was not.
4. If the b7 rung is re-pointed: the rung reads a halfword whose sign is not sign(s) at every |x| the car
   reaches, or the change is not displacement-only, or b0–2 (stock Honda) are disturbed.
5. The fork: with `AccordCurvatureLead` OFF (the default) nothing on the openpilot side changes; with it
   ON, the +1.5–1.9 dB it adds at 5–10 Hz lands on C10's 9 Hz bump — price that interaction and state
   whether the toggle may be enabled on the same drive.
6. The dead twin island 0x2A30E–0x2B421 reads none of the three edited cells.

## What PASS licenses
A build that is cut, hashed, recorded, and handed to the operator with its pre-registered read
(Addendum C §C2.3): ring half-peak decay ≈545 → ≈183 ms on hands-off creep, 10 Hz T-vs-rate phase
−14° ± 4°, 7.3 Hz −12.5°; revert signatures per the design memo §10 (a return of the 6–9 Hz strong-turn
ripple, a new 8–17 Hz line, the grinding unchanged, a 22–30 Hz line, a darty feel). **It does not license
any claim that the grinding is fixed — the operator scores the symptom.**

---

## Verdicts (appended by the agents; orchestrator's crux checks marked ✔)

| surface | verdict | decisive numbers | file |
|---|---|---|---|
| **A arithmetic** | **PASS** | filter re-derived from the image: DC 30.903, corner 9.94 Hz, no overflow; fb input quantum 1 → 2 raw counts (first-tick D kick from one rate LSB now 0); b3 instrument window ≈ 0.25–1.5 deg/s mean rate ✔ | `ADV-V291-A-ARITHMETIC-2026-09-13.md` |
| **B units / stability** | 🛑 **DO-NOT-FLASH** on **B4 (4th clause)** + one UNGATED cost; **B3 RE-SCORED PASS** (§11, after `biv`); B1/B2/B5/B6/B7 PASS; **no instability on any fit at any scaling** | B3 (re-score): the r24-folded Ms 12–26 improvement is **×3.3–4.2** on the admissible EFFECTIVE arm (κ 0.449, k_eff 0.895) across the whole ±8 %/±18° B(f) perturbation box, f0 17.45–17.95 Hz (clear of 15–17), no new ζ < 0.05 pole ✔ (`biv` closed the deadband hypothesis and identified 9.94–14 Hz at nperseg 512); B4: byte-exact steady state **×1.34–1.80 at sp = 3 counts** (within 3 % at sp = 33, 0.3 % at 330; sub-deg/s absolute) ✔ follows from the b = 958 quantum — intrinsic to ANY cal-only fb-pole change; UNGATED: worst-fit sensitivity worse than V282 on **121/121 fits over 3.0–18.2 Hz, peak ×1.99 at 12.85 Hz** ✔ (a well-damped shoulder, now in a MEASURED band); B5 fails with AccordCurvatureLead ON | `ADV-V291-B-LOOP-2026-09-13.md` §9–§11 |
| **C build audit** | **PASS** | independent rebuild (CRC chain walked from the image) reproduces image a66f9c54… and rwd 8ce8d5b7… ✔; 15 bytes; 49/49 + 50/50 CRC; rwd round-trips; 12/12 mutations caught; census inflated (377 → 67 substantive by independent classification); two process defects (tag not derived from integers; no write guard) | `ADV-V291-C-BUILD-2026-09-13.md` |
| **D interlocks** | **PASS** | one reader per edited cell on the built image, both methods; fb state accessors = filter ld.w/st.w + the new cave read; every EME/governor/lockstep/DTC cal byte-identical; latch moves the safe way; dead island reads none of the cells. Residuals: plausibility-monitor "no new trip" is BELIEF-grade; latch conclusion conditional on B; b3 pins to 1 below 0.25 deg/s (condition its duty on |rate| ≥ 2 counts) | `ADV-V291-D-INTERLOCKS-2026-09-13.md` |

**ORCHESTRATOR'S VERDICT, 2026-09-13 (final, after the B3 re-score): V291 (C10) is NOT CLEARED FOR FLASHING
by the letter of this pre-registration** — B4's steady-state clause (×1.00 ± 1 %) fails byte-exactly at tiny
demand. **The basis is narrower than at first report:** B3 passed once `biv` settled the r24 arm (effective,
κ 0.449) and identified the 9.94–14 Hz band (nperseg 512; numbers move ≤ 8 % / ≤ 18°). What remains:
1. **B4** — the feedback quantum b/1024 rises 0.66 → 1.07 raw counts, so below ~0.5 deg/s of wheel rate the
   rate loop is effectively open and delivered rate at sp = 3 counts is ×1.34–1.80 of V282's (0.23–0.41 deg/s
   absolute; within 3 % at sp = 33). **No cal-only fb-pole change can meet the clause as written** — holding
   DC at every amplitude needs the filter in a cave with an error-feedback remainder word (design memo
   §A4.5: DC 1.00000 down to one count). The orchestrator wrote a criterion the class cannot satisfy in the
   byte-exact sense; that is a finding about the class, recorded, not a reason to soften the criterion.
2. **The ungated 9–18 Hz sensitivity shoulder** — worst-fit |1/(1+L)| ×1.3–2.0 worse than V282 over
   3–18 Hz, peak ×1.99 at 12.85 Hz, no pole below ζ 0.36; the band that killed V289 (but V289's was a ζ 0.03
   line). No gate priced it; adversary B proposes "ratio ≤ 1.25 pointwise over 3–30 Hz, worst fit" (C10
   reads 1.99). Whether a well-damped ×2 shoulder there is an acceptable price for ×3–4 at 20 Hz is the
   operator's decision, not the pass's.
The rwd stays on disk under its own name (the only V291; it is what the pass scored). Flying it is the
operator's decision against this verdict, as V289's accepted B3 FAIL was; if flown, the pre-registered
read and the revert signatures in the lineage entry apply, with the 10–18 Hz shoulder pre-registered as a
named revert signature (worst-fit sensitivity ×1.3–2.0, peak near 13 Hz; integer cycle at ~15 Hz), and
`AccordCurvatureLead` OFF.
