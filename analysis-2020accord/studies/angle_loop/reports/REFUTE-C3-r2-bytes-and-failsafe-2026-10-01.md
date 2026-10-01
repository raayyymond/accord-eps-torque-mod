# REFUTE C3 rev2 — lens BYTES-AND-FAILSAFE (2026-10-01)

**Author:** a REFUTER subagent of the orchestrator `main`, lens = bytes + fail-safe. Analysis only: nothing built,
flashed, sent or committed; **Ghidra read-only** (`disassemble_bytes dry_run:true`, `read_memory`, `list_open_programs`)
on the open V294 program (`_v294_…_plain_image.bin`, code-identical to V295 except cal `0xC63EA`+CRC) and stock
`code.bin`; nothing saved. Python = `bin_decompile`. This lens COMPLETED (not partial). Scripts:
`_scratch/angle_loop/c3-rev2-bytes/{decode.py,verify.py}` (an INDEPENDENT V850 decoder, positive-controlled against
Ghidra before any cave was trusted).

Target: `DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md` (merge: PRIMARY **C3-rev2-P = C3B-P byte-for-byte**, FALLBACK
C3-rev2-F, variant C3-rev2-P-cam). Files examined: `c3/rev2B/c3b_cave_C3B-{P,P_score,F}.hex`,
`c3/rev2A/rev2a_cave_R1-{P-cam,F}.hex`, `rb_build.py`, `panel2/E2-integral-most-margin/e2_asm.py`.

---

## VERDICT: REFUTED (do not flash the primary as delivered)

Two independent grounds, both actionable, **neither a loop-design flaw** — the design's control LOGIC (the §1.4
integer loop, the in-place edits, the gate, the op-skip, GATE 1, int bounds) is byte-correct and is MORE fail-safe
than stock on the engage and rate paths. The refutation is:

1. **CONFIRMED (undeclared wrong bytes).** The PRIMARY's **flight** cave `c3b_cave_C3B-P.hex` is mis-assembled:
   `rb_build.add_opskip` splices the +2-byte op-skip without relinking, so two references in the shifted tail are
   stale — the **G-table base pointer** (wrong gain on EVERY engaged tick) and the **FRZ-return `jr`** (wrong target
   on every integral-freeze tick). The SCORE cave — the only one H1 ever executed (0/8000, 0/30000) — is correctly
   linked, so **H1 validated different bytes than the ones that would fly.** This is exactly the kit's "re-disassemble
   from the built image" trap. Undeclared ⇒ a refutation under this lens's criterion. **Correctable:** re-assemble +
   relink the flight cave and re-run H1 on the FLIGHT bytes.
2. **ESCALATED (not fail-safe in firmware, correctly declared).** The stock-camera `0xE4` on a panda relay close is
   read as an angle setpoint and steered to with full P authority; the op-skip does NOT help (the camera sends a
   valid rate). The design itself declares this NOT fail-safe and escalates it (H-cam). This lens concurs with the
   prior C3-r1 bytes verdict: **do not flash** until the orchestrator either rules camera-LKAS-off acceptable for this
   hazard class (program precedent on every flown build V282→V295) or builds the interlock — and the interlock's
   discriminator premise (camera `0xE4` byte-2 field 3:2 = 0) must be re-measured on bus 2 first.

Everything else in the edit set and the cave is **CONFIRMED byte-correct and fail-safe** (below). The fallback
C3-rev2-F and the variant caves have no splice and are correctly linked.

---

## A. CONFIRMED — the in-place edit set (EVIDENCE, this session)

All eight BASE bytes read from V294 by `read_memory` **match the design's "V295" column exactly** (V294≡V295 off the
cave). Each new encoding was decoded field-by-field by an independent decoder and positive-controlled against Ghidra.

| id | addr | base (V294, read) | new bytes | new instruction (independent decode = Ghidra on the form) | verified |
|---|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` ✓ | `24 3f 00 96` | `ld.h -0x6a00[gp],r7` (x:=θ) | ✓ |
| E2 | `0x28FA4` | `89 d1` ✓ (`subr r9,r26`) | `c9 d1` | `add r9,r26` (2-sample sum) | ✓ |
| B2 | `0x29A50` | `e2 47 00 00` ✓ (`setfe r8`) | `e0 df 34 43` | `cmovne r0,r27,r8` (cond 0xA) ⇒ r8:=(request==1)?r27:0 | ✓ |
| A2 | `0x29A56` | `da 05` ✓ (`bne 0x29A60`) | `b2 05` | `be 0x29A5C` (cond 0x2, disp +6) | ✓ |
| E4 | `0x29D6A` | `08 80 ed 80` ✓ (`mov r8,r16;mulh`) | `24 87 52 96` | `ld.h -0x69ae[gp],r16` (sp:=θ_sp) | ✓ |
| HOOK | `0x29D76` | `c2 82 ba 81` ✓ (`shl 2;sub`) | `89 37 8a ae` | `jarl 0xC4C00,r6` (disp 0x9AE8A, r6:=0x29D7A) | ✓ |
| OPH | `0x29EE0` | `10 40 bb 41` ✓ (`mov r16,r8;sub r27,r8`) | `1a 40 00 00` | `mov r26,r8 ; nop` (D operand = r26) | ✓ |
| V1 | `0x1310D` | `30` ✓ | `41` | F181 `…A160`→`…A16A` | ✓ |

Positive controls (independent decoder == Ghidra dry-run): `c282`=shl, `ba81`=sub, `89d1`=subr, `80070807@0x29a5c`=
`jr 0x2a164`, `89378aae@0x29d76`=`jarl 0xc4c00,r6`, `24573192`=`ld.w -0x6dd0[gp]`, `ce05`=bge, `a36a`=`sar 3`, etc. —
all match.

### A.1 The A2/B2 gate becomes a CONJUNCTION — stricter than stock, fail-safe (EVIDENCE Ghidra 0x29A48..0x29A64)

Stock reaches the lane body (and hence the hook) iff **(ramp≠0 OR request==1) AND r25≠0**. After B2+A2 the gate is:

```
0x29A48 cmp r0,r14 ; 0x29A4A setfne r20        ; r20 = (ramp != 0)
0x29A4E cmp 0x1,r8 ; 0x29A50 cmovne r0,r27,r8  ; r8  = (request==1) ? r27(bVar2) : 0      [B2]
0x29A54 cmp r0,r20 ; 0x29A56 be  0x29A5C        ; ramp==0  -> jr 0x2a164 (skip)            [A2]
0x29A58 cmp r0,r8  ; 0x29A5A bne 0x29A60        ; r8==0    -> fall to 0x29A5C jr 0x2a164
0x29A5C jr 0x2a164                               ; the skip
0x29A60 cmp r0,r25 ; 0x29A62 bne 0x29A68        ; r25==0 (gp-0x6803 != 2) -> 0x29A64 jr 0x2a164
```

⇒ lane runs iff **ramp≠0 AND request==1 AND bVar2≠0 AND r25≠0 (gp-0x6803==2)**. Every failing engage condition routes
to `jr 0x2a164` — Honda's own sentinel/decay epilogue. **More restrictive than stock; strictly safer.** (`r27=bVar2`
at `0x29A50` relies on prior record EVIDENCE — r27 is defined upstream of `0x29A20`; the local encoding and the
`r8 = request==1 ? r27 : 0` / conjunction semantics are confirmed this session.)

### A.2 The skip epilogue `0x2A164` — no torque path on skip (EVIDENCE Ghidra)

Both A2/B2 skips decode to `jr 0x0002a164` (`80 07 08 07` @`0x29A5C`→`0x2A164`; `80 07 00 07` @`0x29A64`→`0x2A164`).
`0x2A164` is Honda's shared skip epilogue: `st.w r16,-0x6cf8` with r16=`0x7FFFFFFF` (**first-tick sentinel**),
`st.w r24,-0x6dd0` with r24=0 (**I state := 0**), and zeroes `gp-0x6b2e/-0x6b32/-0x6b34/-0x6b36` (lane state), then
Honda's decaying output path. **No new torque path exists on this route.** The flight cave's op-skip (§C) jumps here.

### A.3 r26 / r25 / r14 liveness (EVIDENCE Ghidra 0x29D7A..0x29EDE)

- **r26** carries the fresh D operand from cave-exit to the OPH: **no instruction writes r26 in `0x29D7A..0x29EDE`**
  (destinations seen: r2,r6,r7,r8,r9,r10,r13,r16,r24,r27,r28,r29,ep — never r26). At `0x29EE0` the stock
  `mov r16,r8;sub r27,r8` is replaced by `mov r26,r8;nop` ⇒ D operand = r26. ✓
- **r25** = `(gp-0x6803==2)`, single writer `setfe r25 @0x29A82` (untouched by any edit); the cave does not write r25
  (scratch set {r6,r8,r9,r13,r16,r26}), so the cam variant's in-cave `cmp r0,r25` reads the live value. ✓
- **r14** = ramp; the cave reads it (`andi 0x8000,r14,r13`) and does not write it. ✓

### A.4 int32 bounds — no wrap even at hostile full-range inputs (EVIDENCE `verify.py`/hand-derive)

|E|≤196 603 (sp full int16 ×4 + r26 clamp 65535); |E·G|≤4.30e8; E'≤1.68e6; E'·Kp(112)≤1.88e8; 48·op(±13000)≤6.24e5;
I increment e5·40≤2.1e6; all `< 2^31`. The op-validity `(op+13000) unsigned ≤ 26000` correctly passes op∈[−13000,13000]
and routes op=±13001.. and the 0x7FFF sentinel to the op-skip. Matches the score grid's wraps=0.

### A.5 GATE 1 — zero RAM written by any cave (EVIDENCE independent decode, code region only)

`c3b_cave_C3B-P.hex`, `…_score.hex`, `c3b_cave_C3B-F.hex`, `rev2a_cave_R1-P-cam.hex`, `rev2a_cave_R1-F.hex`:
**NO store instructions** in any code region. The skip routes to Honda's epilogue, which owns `gp-0x6dd0/-0x6cf8/…`.
GATE 1 clean. ✓

---

## B. CONFIRMED-CORRECT caves (fallback + variants)

`verify.py` resolves every external branch / `jr` / table-base pointer in each cave's code region:

| cave | FRZ-return `jr` | G-table base `mov …,r9` | op-skip |
|---|---|---|---|
| C3B-P **score** (238 B) | → `0x29D7E` ✓ | → `0xC4CC4` = table ✓ | none |
| C3B-F fallback (220 B) | → `0x29D7E` ✓ | → `0xC4CB2` = table ✓ | none (held D; F3 declared) |
| R1-P-cam (246 B) | → `0x29D7E` ✓ (×2: FRZ + CAM) | → `0xC4CCC` = table ✓ | camera gate `cmp r0,r25;be CAM` |
| R1-F (226 B) | → `0x29D7E` ✓ | → `0xC4CB8` = table ✓ | none |

All correctly linked. The fallback and variants are byte-sound (their build-time H1 on the FLIGHT bytes is still
required). R1-P-cam's in-cave `cmp r0,r25` reads the live `(gp-0x6803==2)` flag (A.3). **Note** the design's own
H-cam text says `gp-0x6803==2` *also* arms the engage-SM direction-2 ramp and the `0xCBAE4` ×1.8–2.1 fade, so the
interlock is not free — a cal must neutralise the fade (the merge lists `0xE54FC ← 0xE564C`); that cal is not in
scope for a byte decode here and is flagged for the builder.

---

## C. REFUTING FINDING (CONFIRMED) — the primary's FLIGHT cave is mis-assembled

`rb_build.add_opskip` builds the flight cave as `code[:i] + <6-byte op-skip> + code[i+4:]` — it splices the op-skip in
place of the 4-byte `cmovh r0,r26,r26` and **does not re-link**. `verify.py` byte-diff:

```
score 238 B, flight 240 B, delta +2
first difference at cave offset 0x12 (0xC4C12): score e0 d7 36 d3… / flight b3 05 b6 07 50 55…
tail after splice identical (score[i+4:] == flight[i+6:])?  True   <-- every tail byte shifted +2, content unchanged
```

The op-skip bytes themselves are correct: `0xC4C10 cmp r13,r8 ; 0xC4C12 bnh 0xC4C18 ; 0xC4C14 jr 0x2a164` — the
invalid-rate route to Honda's epilogue (F3) **works**. But the design's own claim "**only those 6 bytes differ from
_score**" is precisely the defect: two tail references that MUST change did not —

| ref | score (correct) | flight (as delivered) | consequence |
|---|---|---|---|
| **G-table base** `mov 0x____,r9` | `0xC4CC4` = table start | **`0xC4CC4`** but table is now at **`0xC4CC6`** | the speed-gain walk reads the `jmp [r6]` opcode `66 00` as table row 0 (X=102, G=714…) → **wrong P/I gain on EVERY engaged tick** |
| **FRZ-return** `jr` (bytes `b6 07 c0 50`) | @`0xC4CBE` → `0x29D7E` | @`0xC4CC0` → **`0x29D80`** | every integral-freeze tick (hard-freeze \|tq\|>512, opposing-hand, A3-bound, ramp) lands one instr late, **skips `cmp r10,r6`**, and the following `ble 0x29D82` runs on stale flags — a sequence H1 never executed |

The DONE exit (`jmp [r6]`, r6 = register) is unaffected (not PC-relative). **H1 (0/8000 + e2_asm 0/30000) ran ONLY on
the score cave**; the design states the flight cave was "decoded by Ghidra dry-run (§1.2)" but §1.2 decodes only the
op-skip bytes, not the FRZ `jr` or the table pointer — the splice collateral was never decoded until this lens.

**Severity:** the table-pointer bug alone corrupts the gain on the primary control path (undeclared) — decisive. The
FRZ bug is an undeclared deviation on a very common path. **Not a design-logic flaw** (the §1.4 loop and the listing
are correct); it is a build-tool defect in the delivered flight artifact. **Fix:** assemble the flight cave by
re-linking after inserting the op-skip (recompute the FRZ `jr` displacement and the table-base immediate), then run
H1/e2_asm on the **FLIGHT** bytes, and H5-decode the FRZ `jr`, the table pointer AND the op-skip on the built image.
Until then the primary must not fly. The 220 B C3B-F fallback (no op-skip, no splice) is unaffected.

---

## D. Fail-safe against wrong-payload sources (the lens's core question)

Setpoint source = `gp-0x69ae` (E4), written by the 0xE4 RX handler; `0xE4` RX cannot preempt the lane; 510 ms timeout
→ sentinel. Does every torque path require a valid, current setpoint?

| source | behaviour | status |
|---|---|---|
| **invalid motor rate** (`gp-0x6abe`=0x7FFF / \|rate\|>13000) | op-skip `jr 0x2a164` → PID skipped, I:=0, sentinel, decay — **no torque path** | **fail-safe (CONFIRMED A.2/A.4)** |
| **not engaged** (ramp 0 / request≠1 / bVar2=0 / gp-0x6803≠2) | conjunction gate → `jr 0x2a164` | **fail-safe, stricter than stock (A.1)** |
| **stock camera 0xE4 on relay close** | read as angle setpoint, full P authority; op-skip does NOT help (valid rate) | **NOT fail-safe in firmware — ESCALATED (declared H-cam)** |
| **torque-mode fork** | torque read as angle; bounded by clamps; interlock = V1 `…A16A` + fork key + re-headered reverts | **declared (H-fork-tq); bounded** |
| **zero-emitting fork** (0 with request 1) | drives toward centre; bounded by ICL 8192 / P-clamp / fade; caught by R6 | **NOW declared** (merge added the sub-case the C3-r1 bytes refuter flagged); bounded |
| **fork stops** (510 ms hold) | last VALID θ_sp held 0.51 s = stock; mid-motion ≤ 2.4° | **declared (H-tmo); stock parity** |
| **pol=−1 dependence** (C3-rev2-P fresh D only) | wrong-sign D on a pol=+1 car; image car-specific + R1 INVERTED drive-1; C3-rev2-F pol-free | **declared (H-pol); procedural** |

The camera is the only wrong-payload path that is **not fail-safe in firmware and not covered by a stop band** (only
a procedure / an unverified-premise interlock). Per this lens's criterion it is a refutation of "fail-safe in
firmware," which the design openly escalates — so it is `do not flash` pending the orchestrator's hazard-class ruling,
not a hidden defect.

---

## E. Could not verify / out of scope (each flagged)

- **`r27 = bVar2` at `0x29A50`** — r27 is defined upstream of the window read; relies on prior record EVIDENCE. Local
  encoding + gate semantics confirmed.
- **"gp-0x67fe ≠ 2 and mode ≠ 3"** (task line) — I located the confirmed engage interlock `gp-0x6803==2` (via r25) and
  a `gp-0x682f`-vs-cal branch at `0x29A86` (`jr 0x29CC4`), but not a distinct `gp-0x67fe` gate. The confirmed gate is
  stricter than stock, so this does not bear on fail-safe; noted as unverified.
- **No image exists** → H5–H10 on a BUILT image (hook/exit decode, A2/B2 dominance, CRC walk, F181 `A16A`, pol re-prove)
  remain build-time, including re-decoding the flight cave's FRZ `jr` + table pointer + op-skip on the built bytes.
- The camera byte-2 discriminator and `pol = gp-0x6752 = −1` are kit record, not re-measured here.

---

## F. What a FIX looks like (so the pass can return "flash after these")

1. Re-assemble `c3b_cave_C3B-P.hex` with a proper link (FRZ `jr`→`0x29D7E`, table-base `mov`→the shifted table addr),
   OR fix `rb_build.add_opskip` to relink; re-hash; **run H1/e2_asm on the FLIGHT bytes** (not the score cave).
2. Orchestrator ruling on H-cam (camera-LKAS-off acceptable, or build C3-rev2-P-cam + re-measure the 0xE4 byte-2
   discriminator on bus 2).
3. The builder's H5–H10 on the built image + the ≥3-agent adversarial pass with "do not flash" reachable — none waived.
