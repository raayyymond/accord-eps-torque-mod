# REFUTE — SAFETY lens on DESIGN C0 (angle loop), 2026-09-30

**Agent:** refuter-safety (subagent of `main`). Study only — nothing built, flashed or sent; fork untouched.
GhidraMCP (V294 program, code-identical to V295 except cal `0xC63EA`+CRC) read-only + Python LE byte scans on
the V295 image `5c044d65…52ed`. `gp=0xFEDF8000`, `tp=0xBF000`. Scratch: `_scratch/angle_loop/refute-safety/`
(`bytes.py`, `census.py`, `sentinel.py`).

**Charge:** make C0 FAIL on safety — find any way it delivers torque the operator did not command; re-decode every
edit byte from the ISA, re-prove GATE 1 on every touched RAM word, and attack the 0xE4 sentinel, the validity gates,
the int32 bounds, the rail, the panda limits, the disengage ramp, and the fork-sends-0 / fork-sends-old-torque cases.

**Bottom line.** Every *firmware-mechanical* safety claim C0 makes checks out when I re-derive it from bytes
(A2/B2 encodings and logic, sentinel closure, GATE 1 on the bleed cell, int32 bounds including the sentinel case).
I could **not** falsify those. **But the dominant uncommanded-torque path is not a firmware bug — it is that C0
re-interprets the 0xE4 payload's failsafe value, and has NO firmware interlock against a wrong payload.** Its entire
defence against a torque-mode fork, a downgrade, a forgotten toggle, or a fork emitting 0/stale with the request bit
held is pushed to fork-side changes (F4, C3/C5/C8, O1) and a panda bound — all BELIEF, none in C0. The design says
this itself ("the angle build must not ship without F4 or an operator procedure"). So the firmware is sound as
described, and **C0-as-a-firmware-artifact is DO-NOT-FLASH on its own.** Verdict: PASS_WITH_DEFECTS, refuted=false.

---

## A. What I verified TRUE (the firmware safety mechanisms hold)

| claim | method | result |
|---|---|---|
| Every edit-site V295 byte matches the design's "V295" column | Python read of the V295 image (`bytes.py`) | ✓ exact: `0x28F4C 24 3f aa 95`, `0x28FA4 89 d1`, `0x29A50 e2 47 00 00`, `0x29A56 da 05`, `0x29D6A 08 80 ed 80`, `0x29EDE c7 00`, `0x29EE0 10 40 bb 41`; cals a1011/b1050/C1024/DB4/Ki0/ICL10240/DCL0 |
| Current guard decodes as the design states | Ghidra dry-run `0x29A48..0x29A64` | ✓ `setfne r20`(ramp≠0); `setfe r8`(req==1); `bne`/`bne`/`jr 0x2a164`. Stock = RUN iff (ramp≠0 ∨ req) ∧ inputs valid |
| **A2** `b2 05` = `be 0x29A5C` | decoded an **in-image** `b2 05` at `0x290E4` → `be` disp6 | ✓ With A2, RUN iff **ramp≠0 ∧ req==1 ∧ inputs valid**. Sentinel sets req=0xFF ⇒ PID **skips** |
| **B2** `e0 df 34 43` = `cmovne r0,r27,r8` (register form) | field delta from control `0x23954 e0 37 34 33`(cmovne r0,r6,r6): only reg2 r6→r27 and reg3 r6→r8 change; low 11 bits 0x334 = register-form (imm form at `0x1a7a4` has 0x314) | ✓ |
| cmov ternary direction: r8 := (req==1)?bVar2:0 | raw pcode of a `cmovne 0x0,…` at `0x1a7a4`: `reg3 = reg2·(cond-false)`, i.e. `reg3 = cond ? reg1 : reg2`. cond=NE on `cmp 1,r8` | ✓ req≠1 → r8=r0=0; req==1 → r8=r27=bVar2 |
| GATE 1 on the I-bleed cell `gp-0x6dd0` (cave's only RAM write) | positive-controlled Python LE 4-byte gp-form census (`census.py`; controls `gp-0x4f60`,`gp-0x6806` found) + trace's 6-byte/indirect scan | ✓ live accesses = **only** the lane's read `0x29DA4` + write `0x2A190`; `0x2AC96/0x2B05C` = uncalled twin; `0x3FBE7` = odd-addr false hit. Cave bleed is an **in-task RMW of a lane-private cell**, consumed by the lane's own read 0x2E later |
| Sentinel value is **32767**, not the brief's 16384 | fault stores `movea 0x7fff` at `0x52688/52722/527BC`; E4 `24 87 52 96` = `ld.h -0x69ae[gp],r16` loads it **raw** (control `0x29032 24 6f 52 96`); the ±16384 clamp `FUN_00049a90` is on the non-fault store path only | ✓ design §2.6 right, brief wrong |
| int32 safety, incl. a one-tick sentinel reaching the cave | `sentinel.py`: worst over θ∈±4096/±12000 at C0 cals (G 1707, Kp 450, Ki 199) | ✓ worst \|product\| = **5.90e8 < 2³¹**; no wrap even on the sentinel — the preemption residual is a railed P, not a sign-flip |
| ±12000 bail now gates θ | E1 only swaps the load operand at `0x28F4C`; the bail at `0x28F50..5A` tests the loaded value r7 = θ | ✓ catches the +32700 wrap (→ ST7 sticky, LKAS off for the drive) |

**A2 fully closes the 0xE4 RX sentinel on the normal (non-preempted) tick** because all three fault branches of
`FUN_00052676` (reachable ones: `0x5268C` param4, `0x52726` param∈{1,2,3,5,6,7}; `0x527C6` is coding-dead) set
`gp-0x6805=0xFF`, and A2 requires req==1 to run. This is the single most important safety claim and it is TRUE.

---

## B. Findings — ways C0 can deliver uncommanded torque (ranked)

### F1 (HIGH) — Payload-semantics inversion; NO firmware interlock against a wrong 0xE4 payload
C0 re-reads the 0xE4 `STEER_TORQUE` field as an **angle setpoint** (`θ_sp = −raw`, 0.1° counts, sp clamp ±409.6°).
This inverts the field's failsafe meaning:
- **Torque firmware (V295): raw=0 ⇒ no torque = safe neutral.** **Angle firmware (C0): raw=0 ⇒ "steer to 0°"** at
  full loop authority — a centring command, violent if sent mid-turn.
- **A stale/old torque command is a huge angle.** A torque-mode fork value of e.g. raw=−2000 (a modest left torque)
  becomes θ_sp=+200° ⇒ the loop drives hard to +200°.
- **A2 gates only the request BIT, never the payload.** If request stays 1 and the payload is wrong (fork bug,
  downgrade, forgotten toggle, momentary 0), the loop executes it. P rails at only **8.2° error at ≥26 m/s**
  (design §1.4), so a wrong setpoint = full-rail (2461) autonomous steer with **no** fork torque command.
- Every mitigation — **F4** (distinct fwVersion so a torque fork can't drive the angle image), **C3/C5** (start/hold
  θ_sp at the measured angle), **O1**, **C8** — is **fork-side, BELIEF, and NOT in C0.** The design states "Today
  nothing distinguishes the images."
- **EVIDENCE:** the firmware reads `gp-0x69ae` raw and has no field-type/consistency check (bytes, this session).
  **BELIEF:** the fork behaviours.
- **Flight bar:** do not flash without F4 **and** an operator procedure **and** a measured panda bound (F7).

### F2 (MEDIUM) — The preemption window is the one path the sentinel still reaches P, on an untraced assumption
If `FUN_00052676` (0xE4 RX) can preempt the lane task between the early latch of req/bVar2 (`0x29A4E`/`0x2913A`)
and the cave's `ld.h -0x69ae` at the hook `0x29D76`, one tick computes E on sp=32767 ⇒ P rails for 1 ms into the
5.05 Hz output lag. **B2 does not help** — bVar2 is computed on the pre-fault `gp-0x69ae` early in the same tick.
- I confirmed it is bounded: no int32 wrap (F-bound 5.9e8), and the *next* tick skips (req=0xFF) ⇒ one tick.
- **Unproven:** task priority is NOT traced, so the "≤1 ms impulse, safe" claim is BELIEF; a multi-tick or
  worse-phased preemption would break the bound. Also BELIEF: which 0xE4 statuses/**timeouts** actually drive the
  fault handler and set `gp-0x6805=0xFF` — a fork crash (0xE4 stops) holds the last angle until a timeout handler
  (untraced) sets the request to 0xFF and A2 skips. **EVIDENCE** for the window's existence and its int32 bound;
  **BELIEF** for its safety and for the timeout trigger.

### F3 (MEDIUM) — Mode-3 / in-range wrong angle is invisible to the firmware
When `gp-0x679c ≠ 3` with a baseline-wrong but in-range θ (sentinel trace gate B3), the lane computes E on a wrong
θ and steers to a wrong angle. **No lane gate tests `gp-0x679c` or the baseline.** The only mitigation is fork-side
**C8** (drop request unless 0x14A b4 bits0–2 = 7), BELIEF and not in C0. Residual = a wrong steer for ~10 ms + the
fork round trip. Rare (1 in 2.3 M frames) but a real uncommanded-steer path the firmware cannot see. **EVIDENCE:**
the lane's inputs are only ±12000(θ) and bVar2; neither covers an in-range wrong baseline.

### F4 (MEDIUM) — Authority model change: error-driven rail that did not exist in torque mode
Closing the loop in firmware gives the ECU **autonomous** authority to the rail from any setpoint error
(45–300 T/deg; rails at 8.2–54.6° by speed). The peak clamp (OCL 3072, rail 2461, SCL/PCL 15360) is unchanged, but
the *conditions* that reach peak torque are now internal — this is the mechanism that turns F1/F3 into full-rail
steers. The firmware does not cap demanded authority by speed; the design relies on fork **Δmax(v)** (C6, BELIEF).
**EVIDENCE:** arithmetic from the verified loop; clamps re-read unchanged.

### F5 (LOW–MED) — B2's safety benefit is unproven (bVar2 dominance)
B2's value depends on r27 = bVar2 holding at `0x29A50`. I confirmed on the **normal run path** r27 is preserved
(only writers are `0x2913A` and post-guard sites per the r27 census), and that bail/invalid paths are caught by the
`r25` input check regardless — so a dominance failure is a **loss of B2's benefit or a functional skip, not a new
torque hazard on the normal path.** But "`0x2913A` dominates `0x29A48`" remains BELIEF and must be re-proven on the
**built image** (gate H6) before B2 is credited with closing the `gp-0x67fe≠2` hazard. **EVIDENCE** within the
analysed body; **BELIEF** on dominance.

### F6 (LOW / informational) — Disengage hand-back shortened by A2
With A2, every disengage and every ST=3/fault releases in ~100 ms (output-lag decay) instead of Honda's 2 s
PID-held fade. This *reduces* torque faster (safer for the sentinel) and is normal angle-car behaviour, but it is an
operator-facing change in how control is handed back. Not an uncommanded-torque hazard. **EVIDENCE:** guard + lag.

### F7 (LOW / unverifiable here) — Panda setpoint bound assumed absent
The design asserts "the panda bounds nothing on 0xE4." If the comma/StarPilot safety model actually limits the 0xE4
magnitude/rate for this Honda, that is protective; if not, the fork has unbounded authority within the sp clamp
(±409.6°) at any slew. **I cannot verify this from firmware** — it is fork/panda-side. It is a flight prerequisite:
measure what the running panda enforces on 0xE4 under the angle build, because it is the only backstop to F1 if F4
is ever bypassed.

---

## C. Do-not-flash conditions from the safety lens (what a FAIL looks like)

Flash C0 only after ALL of: **(1)** F4 fwVersion interlock exists so a torque-mode fork cannot command the angle
image, plus an operator toggle procedure; **(2)** the running panda's actual 0xE4 magnitude/rate bound under the
angle build is measured (F7); **(3)** the 0xE4 RX **task priority** is traced to prove the preemption window is ≤1
tick, and the **timeout/fault trigger** is traced to prove `gp-0x6805→0xFF` on a fork crash (F2); **(4)** B2's
bVar2 dominance is re-proven on the **built image** (H6), and H1–H8 run on the assembled cave/hook; **(5)** the fork
sends the measured angle while inactive and never raw=0-as-command (C3/C5/O1/C8). The design already lists most of
these as prerequisites; this pass makes the safety reasons explicit and ranks F1 as the dominant one.

**Not refuted:** the firmware mechanisms (A2, B2, the cave's RAM ownership, the int32 budget, the sentinel closure)
are sound as the design describes them. The build's safety is real but **conditional on unbuilt fork work** — so the
artifact is a design, not a flight candidate, exactly as the design states.
