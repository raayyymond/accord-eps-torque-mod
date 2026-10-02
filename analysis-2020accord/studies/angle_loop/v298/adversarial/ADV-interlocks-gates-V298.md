# ADVERSARIAL PASS — INTERLOCKS / DOWNSTREAM / GATE 1 / GATE 2 on the BUILT V298 image

**Adversary:** INTERLOCKS-GATES (subagent of `main`). **Job:** make the built image FAIL.
**Image re-derived from:** `_v298_…A16A_plain_image.bin` sha256 `177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066`
(my own copy, re-hashed, re-imported fresh into Ghidra `/advIG/ADVIG_V298_177abf04.bin` — NOT the builder's 0-function
disasm-only program; and Python LE byte reads straight off the image). Nothing flashed/sent; files on disk only.

**FAIL criteria were written FIRST** (`FAIL-CRITERIA-interlocks-gates-V298.md`, before any analysis) and are scored below.
Scripts beside this file: `advig_diff.py`, `advig_regflow.py` (+ `regs_28ea6_v298.tsv` from `DumpRegsIG.java`),
`advig_bytes.py`, `advig_overflow.py`, `advig_gpcensus.py`, `advig_gate2_members.py`, `advig_crc_rwd.py`.

## VERDICT: PASS_WITH_DEFECTS — flash-blockers F1–F10 all CLEAN on the image; residuals are DECLARED, not hidden

DO_NOT_FLASH was structurally reachable: a stale relink target, any cave RAM write, a credible GATE-2 member failing,
a reachable overflow, a torque path on an invalid setpoint, or an inverted camera gate would each have tripped it.
**None tripped.** The build faithfully implements the merged C3-rev2-P + camera interlock and FIXES the known relink
defect. The defects below are the design's own declared BELIEF premises and fork-config prerequisites, plus one
declared operating-point margin — each verified to be a declared item, none a concealed new defect.

---

## F1 — relink targets (the KNOWN DEFECT class). CLEAN. [EVIDENCE: `advig_bytes.py`, bytes off the image + Ghidra decode]

| field | site | image bytes | target | want | defect was |
|---|---|---|---|---|---|
| HOOK jarl | 0x29D76 | `89378aae` | **0xC4C00** (r6=0x29D7A) | 0xC4C00 | — |
| op-skip jr | 0xC4C14 | `b6075055` | **0x2A164** | 0x2A164 | — |
| FRZ-return jr | 0xC4CC4 | `b607ba50` | **0x29D7E** | 0x29D7E | **0x29D80** |
| CAM-return jr | 0xC4CD4 | `b607aa50` | **0x29D7E** | 0x29D7E | — |
| G-table ptr (mov imm32,r9) | 0xC4C1C | `2906da4c0c00` | **0xC4CDA** | 0xC4CDA | **0xC4CC4** |

Honda's own A2/B2 skips `0x29A5C`/`0x29A64` → `0x2A164` (bytes `80070807`/`80070007`) — the op-skip reuses the EXISTING
epilogue. **GB-P table @0xC4CDA is byte-exact** to the design (7 rows `(714,1178,1041)(1843,1465,-6264)(2304,760,-2033)
(2707,560,1570)(4032,1068,2118)(6198,2188,0)(ffff,2188,0)`), ends at 0xC4D04, 0xFF after. **The stale 0xC4CC4 pointer and
0x29D80 return of the on-disk `c3b_cave_C3B-P.hex` are fixed in the built image.**

## F9 — shipped == validated; .rwd decodes; CRC. CLEAN. [EVIDENCE: `advig_crc_rwd.py`, kit `verify_bootloader_crc`/`encode_eps`]

- Image cave[0xC4C00:+260] == the H1 FLIGHT hex byte-for-byte (sha `ef1861e10421…`, the builder's reported flight sha).
  Builder's H1 reproduced here: **0/40000** (valid 14458 + op-skip 20607 + CAM 4935); both negative controls caught
  (G-byte flip 262/4000, op-skip +2 2038/4000). Flight(260) vs score(258) differ ONLY in the op-skip region; valid-rate
  opcode streams identical — so the score cave GATE 2 covers the flight cave's valid-rate loop.
- CRC chain on the built image: **walk() 49/49, walk_all_blocks() 50/50, 0 mismatch**. The 3 recomputed trailers verify:
  0xC4FFC `6B7CD8F3`, 0xC6FFC `4F36CA24`, 0xE5FFC `50D68D31`.
- V298 .rwd decrypts (cipher `((i^0x10)^0xbf)-0x9e`) to the plain image over [0x13000,0x100000) **exactly**; `/` header
  lists `['39990-TVA-A110','39990-TVA,A160','39990-TVA,A16A']`. Both REVERT copies decode to the true V295 / V294 plain
  images with A16A added to `/`; the untouched originals still list only `[A110, A160]`. One flashable V298 .rwd on disk.

## F2 — register liveness at the hook / through the cave / op-skip. CLEAN. [EVIDENCE: `advig_regflow.py` on Ghidra's own per-insn IN/OUT]

- The cave writes only **r6,r8,r9,r13,r16,r26**. r8/r9/r13 are dead at every return (rewritten before read). r16(=Ep),
  r26(=fresh op), r6(=output carrier) are the DESIGNED outputs: r16→stock tail P/e5, r26→OPH 0x29EE0 (D operand, with
  **no writer between the hook and OPH** — flows unclobbered), r6→jmp target / e5 on FRZ/CAM.
- r25 (camera flag) and r14 (ramp) are **read-only** in the cave; r25's sole def is the stock `setfe r25 @0x29A82`, r14's
  defs are the stock engage SM — the cave touches neither.
- **op-skip liveness:** the epilogue 0x2A164 live-in is {gp,lp,r11,r14,r15,r20,sp,tp}. Reaching-defs of r11/r14/r15/r20
  at the op-skip (0xC4C14) are **IDENTICAL** to Honda's own A2/B2 skips (0x29A5C/0x29A64); gp/lp/sp/tp are
  callee-saved/globals the cave never writes. The op-skip presents exactly the state Honda's epilogue was built for.

## F3 / GATE 1 — RAM ownership. CLEAN. [EVIDENCE: `advig_gpcensus.py` positive-controlled (gp-0x6b38, 7 hits), + no `st.*` in the cave]

- **The cave contains zero `st.*` — it writes 0 RAM.** It adds only READERS: gp-0x6abe, gp-0x6a00, gp-0x4f60,
  gp-0x6dd0 (×2), gp-0x4f68. Every read cell's WRITERS are UNCHANGED from stock (e.g. I-state gp-0x6dd0: 2 writers,
  both Honda's 0x2A190/0x2B05C; fresh op gp-0x6abe: 4 writers, all in FUN_00041xxx, earlier in the 1 kHz pass).
- No new state word → no engage/disengage/bail init requirement. The first-tick sentinel gp-0x6cf8 and I-state gp-0x6dd0
  reset is Honda's own epilogue (0x2A164 writes `0x7FFFFFFF`→gp-0x6cf8, `0`→gp-0x6dd0), reused on every skip.

## F7 — A2/B2/op-skip guard semantics on the REAL control flow. CLEAN. [EVIDENCE: Ghidra flow 0x29A40–0x29A64]

PID RUN (reaches the hook) requires **ramp≠0 (be 0x29A5C on r20=setfne(r14≠0)) ∧ request==1 ∧ bVar2≠0 (r8 via
cmovne/cmp) ∧ stock r25-early ∧ valid rate (cave op-skip)**. Every other case routes to **0x2A164**, which zeroes I8
and sets the sentinel — **no torque path, and the integral is NOT written on any skip path** (op-skip reaches 0x2A164
after only register ops/loads — 0 RAM written in between).

## F4 — fail-safe on invalid / stale / wrong-payload setpoint. CLEAN (declared residual on wrong-payload).

- **0xE4 timeout:** request held ≤510 ms (stock parity) then drops → B2 skip → I zeroed, output decays. Fail-safe.
- **rate invalid** (gp-0x6abe = 0x7FFF or |·|>13000): op-skip → 0x2A164. Valid-rate window measured **exactly ±13000**.
- **camera / gp-0x6803≠2:** CAM handler (see F10). **gp-0x67fe≠2 / mode≠3:** gate via the inherited engage SM → ramp
  decays → FRZ then A2 skip. **Preemption:** 0-tick window (slot 0 highest prio, cooperative) — inherited, unaffected.
- **wrong-payload / zero-emitting fork** (req 1 ∧ 6803==2 ∧ fwVersion A16A, all asserted): reads the payload as a
  setpoint — **bounded** by the P/I/D + output clamps, caught by R6 and the driver. Not fail-safe in the strict sense;
  **DECLARED (H-fork-tq), gated behind the fork angle-loop key + V1**. Same class as any angle-command controller.

## F5 — integer overflow / truncation / wrapping store. CLEAN. [EVIDENCE: `advig_overflow.py` byte-derived mirror, 400k random + exhaustive corners]

**0 int32-overflow events.** Max |Ep(r16)| = 1,676,650, |r6| = 33,553,902, |r26| = 13,000 — all ≪ 2³¹. The P term is
**clamped** in the stock tail (`0x29E40 cmp r6,r8 ; ble … against tp-0x71bc`) BEFORE use, so an adversarial saturated
setpoint saturates P rather than wrapping an int16; D/I are clamped by DCL(10240)/ICL(8192). H1 + the golden model agree
tick-for-tick on fb/E/P/S/T over 20000 engaged ticks (the clamps are exercised).

## F8 — GATE 2 on the BUILT cals/table. PASS with a DECLARED margin. [EVIDENCE: `rb_gate2.py` @Ki40 + `advig_gate2_members.py`; the scorer's GB_P == the image table]

- **θ=0 R2-box (the brief's GATE 2):** C3B-P **0 PM-fails / 0 GM<6dB / 0 peak>+3dB**; worst PM 38.5° (bar 30).
- **operating-point GATE 2 (the test that REFUTED C3):** **0 exact ρ≥1** (no divergence). Partitioned by member:
  - **NON-ms_free credible set: 45120/45120 points PASS**, worst PM **32.8° > bar 30** (b_lo×J_hi@8.0). 0 fails.
  - **ms_free J≈2 family: 758 PM<bar (ρ<1)**, worst 4.6°/8.2°/21.2° — **exactly the design's declared M-F1 numbers.**
    Report-only: ρ<1 everywhere, disfavoured by the held-out r71b ident (prefers J≤0.5), friction-masked ±0.1–0.6°,
    covered by stop band **R3\* 0.25–0.9 Hz**. **Operator must arm R3\* on drive 1** (a growing 0.25–0.9 Hz curve-hold
    ring = revert). This is a thin but declared/bounded margin, not a flash-blocker.
- No governor/EME/lockstep/DTC cal is among the 325 changed bytes (all in code / cave / 3 CRC trailers / PID-cal block /
  PID-record block / version; **0 stray**). The lane output still flows through the inherited EME shaper + governor +
  output clamps (unchanged). Kp 960→112 and the fade neutralization are safe-direction/authority-neutral; Kd 0→48 enables
  the fresh-D term, GATE-2-covered and DCL-clamped.

## F10 — camera interlock. Direction CLEAN; discriminator is BELIEF (flight prerequisite). [EVIDENCE: Ghidra cave 0xC4C5A/0xC4CC8]

`cmp r0,r25 ; be 0xC4CC8`: r25==0 (stock-camera frame, 6803≠2) → **CAM handler forces r16=0 (E'=0→P=0), r26=0
(op=0→D=0), r6=-(I8>>6) decay** → lane inert, decaying; the camera's 0xE4 cannot become a setpoint (E' zeroed before any
consumer; the only setpoint mirror, gp-0x6a32, has **0 readers**). Direction is correct (fork-6803==2 runs, camera inert).
⚠ **The premise "stock camera sends byte-2 field 3:2 = 0" is kit record, NOT re-measured (trace open item 4).** I cannot
verify a bus value from the image. V298 is strictly safer than the flown V282→V295 baseline on this axis (it adds a
firmware interlock on top of the procedure), but **camera-LKAS-off remains the mandatory first-flight practice** and the
6803 discriminator must be re-measured on bus 2 before the interlock is RELIED upon.

---

## Residuals (all DECLARED in the design; none is a concealed new defect) — flight prerequisites

1. **Camera discriminator (6803≠2 for the stock camera) = BELIEF.** Re-measure bus-2 byte-2 field 3:2; camera-LKAS-off first flight.
2. **pol = −1** (the fresh-D sign, `gp-0x6752`) is boot-static RAM, **car-specific, not image-verifiable**. Re-prove on this car; R1 INVERTED catches drive 1.
3. **Operating-point ms_free J≈2 margin** (PM→4.6°, ρ<1) — declared M-F1; arm R3\* (0.25–0.9 Hz growing ring = revert).
4. **Fork prerequisites:** fork must send 6803==2 EVERY frame incl. request-drop (else lane inert / engage SM → dir-0
   timing); must accept fwVersion `39990-TVA,A16A` (else no fingerprint/engage); angle integral τ_o≥1 s and none below 8 m/s.
5. **gp-0x6a32** (E4-changed store) has 0 gp-relative readers (inert); a register-indirect reader was not exhaustively excluded (low risk — it is a diagnostic mirror Honda already wrote in stock).
6. Cumulative non-stock delta is large (2471 bytes vs stock, mostly inherited V282/V293 torque-mode cells) — the close-out non-stock message must enumerate each per the 5-part contract.

## What a FAIL would have looked like (and did not)
Any relink target off (F1) · a cave `st.*` or a new I-state writer (F3) · r25/r14 clobbered or op-skip liveness mismatch
(F2) · a credible (non-ms_free) GATE-2 member below bar or any ρ≥1 (F8) · an int32 overflow / wrapping store (F5) · a
torque path on timeout/invalid-rate/skip (F4/F7) · an inverted camera gate or a non-decaying CAM term (F10) · shipped
cave ≠ H1 bytes or .rwd not decoding to the image (F9). All checked against the image; none present.
