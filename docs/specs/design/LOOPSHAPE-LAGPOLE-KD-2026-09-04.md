# Loop shape: the output-lag pole `0xC63EC`/`0xC63EE` and `Kd` `0xE511C` — a two-parameter design study

Subagent `loopshape`, 2026-09-04, reporting to `team-lead`. **DESIGN STUDY, NOT A BUILD.** No image was
written, no build script exists, nothing was flashed or sent. Follow-up to
`docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md` (§5c/§7c) and
`rlog-tools/studies/grind/V282-R24-TAP-READ-r36-r38-2026-09-03.md` (§6).

**Image**: `…\accord-firmwares\analysis-2020accord\_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
sha256 `fd0c321abbf933c0d846a8eaf48b594f44f5a9bd491e4396b44abc562551ef3d`, 1,048,576 bytes, hashed by me.
Every constant below is a **raw little-endian Python byte read of that file**. Structure from GhidraMCP
(`decompile_function`, `disassemble_bytes dry_run:true`) on the V282 project — V282 and V283 differ only in
`0xC63E6` (Ki) and its CRC, so the code is identical for this purpose. `gp = 0xFEDF8000`, `tp = 0xBF000`.

**Runnable mirror**: `analysis-2020accord/studies/loopshape/loopshape_pole_kd.py` — reads the image itself;
every number in this document is its stdout (`_scratch/loopshape_out.txt`).

⚠ *tp arithmetic, the trap that has now recurred six times:* Ghidra renders these as `ld.h 0x73ec, tp, r7`.
`0xBF000 + 0x73EC = 0xC63EC` — **`0xC6…`, never `0xC7…`**. Anchored against the known 992/507 and against
`0x71bc` → `0xC61BC` = 15360 before anything else was computed.

---

## 0. HEADLINE

1. ✅ **GATE 1 IS CLOSED — CLEAR, but only after a scare and only on a chain of five arguments.** The
   output-lag pole `0xC63EC`/`0xC63EE` is read from **two** sites and the Kd family `0xCB7D4` is indexed
   from **two** functions — but the second consumer of each lives in `[0x2A30E, 0x2B421)`, a **duplicate
   compiled copy** of `FUN_00028ea6` that is unreachable. **The pole is applied ONCE per tick; there is no
   `H²`.** The verdict to publish for Kd is the two-parter: **shared in code, private in effect.**
   Only the feedback EMA `0xC63E8`/`0xC63EA` is single-site in the first place. §1.
2. 🛑 **THE OPERATING POINT MOVED AND IT MAKES EVERYTHING TIGHTER.** `|L_tot(7.3, Kp 248)|` is
   **0.976 [0.944–0.990]** (per-episode ACF fit), superseding the 0.92–0.94 this study was briefed with
   and the 0.90 carried before that. Today's stability margin `|1−L|` is therefore **0.024 at the point
   estimate and 0.010 at the pessimistic end, not 0.068** — the ring is **2.8× to 6.8× closer to
   self-sustaining** than the brief assumed. Which candidates pass is interval-invariant (the gate is a
   ratio); **how much room they have is not.** §4, §8.
3. 🛑 **A `Kd` CUT ALONE IS DO-NOT-FLASH AT ANY VALUE.** At the new operating point every cut crosses
   unity at the ring's own frequency, pooled: **Kd 112 → |L| 1.028, 96 → 1.064, 64 → 1.137, 0 → 1.287**
   (pessimistic end; at the 0.976 point estimate Kd 112 already reads 1.013). The record's warning
   reproduces from the bytes and is **stronger than the record stated** — this is not "the trouble moves
   to 8 Hz", it is the cycle coming back at 7.3 Hz.
4. ✅ **The loop model is validated against the wire with no free parameter.** The byte-derived servo arm
   reproduces GRINDING-DEEP §2's **measured** lane phase at both symptom frequencies to within 4°
   (−61.3° model vs −62° measured at 7 Hz; −65.1° vs −69° at 20 Hz), implying the plant contributes ≈0°
   and ≈−4°. **The servo lane's phase IS the electronics.** [EVIDENCE]
5. ⭐ **It also reproduces the grind's measured Kp dependence, and by a mechanism the record had not
   stated**: raising Kp dilutes the D term's lead, rotating the lane *past* quadrature, so `Re` (its
   damping contribution) **collapses from +0.80 at Kp 248 to +0.12 at 600 to −0.07 at Kp 696 even as
   `|Z|` grows 1.5×.** More gain, less damping. That is why "presence follows Kp(idx)", and it is a
   fourth, independent argument against the Kp lever. §3.
6. ⭐ **A Kd cut also drags the servo lane's damping/anti-damping crossover from 61 Hz to 34 Hz (Kd 64)
   or 19.7 Hz (Kd 48)** — a **sign inversion inside the band no instrument on this car can see.** This is
   new, it is a harder objection than the phase-lead argument the record carries, and it belongs in the
   probe design law rather than only here. §6.2.
7. ✅ **The pidframe pairing survives, but its value is not what was claimed.** The lag-pole raise **alone**
   is better than any (pole, Kd<128) pair on *both* symptom metrics. What the Kd cut actually buys is
   **blind-band safety**: pole 15 Hz + Kd 64 carries **×1.54 of HF gain flat to Nyquist against ×2.60–2.96
   for the pole raise alone**, while still improving both bands. That is a real escape from the trade — for
   a different reason than the one written down.
8. 🛑 **NO CANDIDATE IS READY TO BUILD, and GATE 1 was never the strongest blocker.** The 7.3 Hz
   *benefit* is **unmeasurable from one drive** — the F7 census is already at the floor (0.00 per 100 s
   across four routes and 206 s), so only a regression is readable there. And the 20 Hz **magnitude is
   not predictable**: the only cross-build step available to calibrate `ΔRe` → `Δbar amplitude`
   (V280 rev 2 → V281 rev 3) is **inconsistent with that map by two orders of magnitude** — the byte model
   puts the servo damping change at **+4.7 %** against a measured **×0.348** amplitude drop. I can give
   the sign; I cannot give the size. **This is the most important finding in the study and it is a hole
   in the framework every recent grind document reasons through.** §9.2, §10 item 7.
9. ⇒ **My answer is "not ready, here is the probe."** §9.4 names it: a **read-only tap on `gp-0x3d3c`**
   plus a `|D| ≥ |P|` comparator rung sited where both operands carry no DC, and a continuous ring
   statistic pre-registered against the sub-detector population so the 7 Hz benefit has a floor it can
   move off.

---

## 1. GATE 1 — RAM/cal ownership and the reader census, per cell

**Two independent methods, set-differenced.** (a) A `firmware-codepath-tracer` subagent's GhidraMCP pass.
(b) My own raw little-endian halfword scan of the V283 image over `[0x13000, 0x100000)`, decoding the
preceding halfword of every match (`_scratch/tp_scan.py`).
**Positive control on both**: displacement `0x71bc` → `0xC61BC` (the P clamp, known read at `0x29E42`).
My scan finds it at `0x29E3A / 0x29E44 / 0x29E4A / 0x29E58` and **also** at `0x2AD2C / 0x2AD34 / 0x2AD44`.

| cell | disp | tp reads | writers | **VERDICT** |
|---|---|---|---|---|
| `0xC63E8` = 923 (fb EMA pole `a`) | `0x73e8` | **1** — `0x28F8A` | 0 | ✅ **PRIVATE** to `FUN_00028ea6` |
| `0xC63EA` = 1560 (fb EMA `b`) | `0x73ea` | **1** — `0x28F86` | 0 | ✅ **PRIVATE** |
| `0xC63EC` = 992 (out-lag pole `a`) | `0x73ec` | **2** — `0x2A184` (live), `0x2A8A2` (**orphan**) | 0 | ✅ **shared in code, PRIVATE IN EFFECT** |
| `0xC63EE` = 507 (out-lag `b`) | `0x73ee` | **2** — `0x2A174` (live), `0x2A892` (**orphan**) | 0 | ✅ **shared in code, PRIVATE IN EFFECT** |
| `0xE511C` (Kd record, slot 7) | — | via `0xCB7D4`; `0xCB7F0` → `0xE511C` byte-read by me | 0 | ✅ **shared in code, PRIVATE IN EFFECT** |
| `0xCB7D4` (Kd LERP pointer table) | — | **2 base loads** — `0x29E76` (live), `0x2AD64` (**orphan**) | 0 | ✅ same |

**Zero writers to all four pole cells is a CONTROLLED null**, not an assumption: the store scanner's
opcode field (`st.h` = `0x3b`) was established from a Ghidra-confirmed `st.h r21,-0x373e,gp` at `0x3954C`,
and the full census over `hw2` `0x73e8`–`0x73ef` with `hw1 & 0x1f == 5` returned only `0x39` (`ld.h`) and
`0x3f` (`ld.hu`).

**Full raw tp census, for anyone set-differencing against this:** `0x28F86` op3f r16 hw2=`73eb` ·
`0x28F8A` op39 r9 hw2=`73e8` · `0x2A174` op3f r7 hw2=`73ef` · `0x2A184` op39 r7 hw2=`73ec` ·
`0x2A892` op3f r10 hw2=`73ef` · `0x2A8A2` op39 r10 hw2=`73ec`. Six, no others, no stores.
(`ld.hu` encodes `hw2 = disp|1`; `ld.h` encodes `hw2 = disp`.)

Third raw hit `0x7FD5C` for `0x73ed` is a **false positive** (opcode field `0x12`, `reg1 = r1`, not `tp`).
`0x19704 / 0x5A5EE / 0x5EC58` are likewise false positives on `0x71bc` (opcode `0x0d`, `reg1 = r10`).

### 1.1 🛑 `search_instructions` missed the second lag reader entirely — and it flipped the verdict

`0x2A892` and `0x2A8A2` sit in `[0x2A508, 0x2A93A)`, a **1074-byte region Ghidra has never analysed** —
undefined in the V282 program *and* in the more-analysed stock `code.bin`. `search_instructions` returned
58 matches with `truncated:false` and did not contain them. Only the raw byte scan did. This is the
documented undercount trap, and here it turned a PRIVATE verdict into a SHARED one. **The gap is
byte-identical to stock**; `FUN_00028ea6`'s body is not (our cave edits).

### 1.2 What the second lag reader is — a clone sharing the SAME filter state

`0x2A504` is `dispose {...}, lp` (the return of `FUN_0002a30e`). **`0x2A508` is a new function entry**: an
unsigned 9-way dispatch on the state byte `gp-0x3d38` → handlers `0x2A87A`(0) `0x2A546`(1) `0x2A75E`(2)
`0x2A5F0`(3) `0x2A676`(4) `0x2A5D0`(5) `0x2A6C8`(6) `0x2A7E4`(7) `0x2A7AE`(8), default `0x2A87A`.

Inside it, `0x2A892` is a near-exact clone of the PID's own output-lag tail. Side by side, from my own
`dry_run` disassembly of both:

```
FUN_00028ea6, 0x2A174  (the LIVE lag)            the CLONE, 0x2A892
  ld.hu 0x73ee,tp,r7     ; b = 507                 ld.hu 0x73ee,tp,r10    ; b = 507
  ld.w  -0x3d3c,gp,r9    ; lag_s   <-- SAME        ld.h  -0x6b2e,gp,r9    ; S, read back
  st.h  r12,-0x6b2e,gp   ; publish S               ld.w  -0x3d3c,gp,r14   ; lag_s  <-- SAME
  mul   r7,r12           ; S*507                   mul   r10,r9           ; S*507
  ld.h  0x73ec,tp,r7     ; a = 992                 ld.h  0x73ec,tp,r10    ; a = 992
  mul   r9,r7            ; lag_s*992               mul   r14,r10          ; lag_s*992
  sar 0xa,r12 / sar 0xa,r7 / add r12,r7            sar 0xa,r9 / sar 0xa,r10 / add r9,r10
  add   r7,r9  / sar 0x5,r9      ; out             add r10,r14 / sar 0x5,r14      ; out
  st.w  r7,-0x3d3c,gp    ; lag_s = s_new           st.w r10,-0x3d3c,gp    ; lag_s = s_new
  ld.bu 0x74a3,tp,r16 / cmp 0x1                    ld.bu 0x74a3,tp,r8 / cmp 0x1
  ld.h  0x71b8,tp,...    ; clamp 0xC61B8           ld.h 0x71b8,tp,...     ; clamp 0xC61B8
  ld.hu -0x69b0,gp / mul / sar 0xf ; ramp          ld.hu -0x69b0,gp / mul / sar 0xf ; ramp
```

Same cal cells, same RAM state, same input cell, same mode byte, same clamp, same ramp, same shifts.

### 1.2b 🛑 My first reading was WRONG, and the way it was caught is the transferable part

I argued that `0x2A508` must be LIVE because it **writes** `gp-0x69b0`, the engagement ramp
`FUN_00028ea6` **reads** at `0x2A1E6`, and a producer of a cell live code consumes must run. **The tracer
refuted that from the bytes rather than deferring to it, and it was right to.**

> **`FUN_00028ea6` writes `gp-0x69b0` TWELVE times inside its own body** — `st.h` at `0x293AC`, `0x293FE`,
> `0x2942A`, `0x29494`, `0x294B4`, `0x2950C`, `0x29594`, `0x295AC`, `0x29656`, `0x2969C`, `0x29714`,
> `0x2972A`, plus 29 reads in the same range (75 accesses image-wide; scanner positively controlled on
> `gp-0x3d3c`, which returned exactly the four expected sites). **The LKAS PID produces its own ramp and
> consumes it in the same call.** The orphan is not needed for it and is not the producer.

Same for the dispatch state byte `gp-0x3d38`: read at `0x29322` **inside `FUN_00028ea6`** and written by
`st.b` at eight sites `0x293A2`…`0x29720`, all inside it. So `gp-0x3d38` is **the PID's own internal
sub-state byte**, not an independent state machine and not the `gp-0x67fa` EPS state the control task
one-hots.

⇒ **The general lesson, which generalises past this study: a cell having a writer in suspect code proves
nothing about that code's liveness if live code also writes the same cell.** "X produces what live code
consumes" is only an argument when X is the *sole* producer, and that has to be censused, not assumed.

### 1.2c ✅ Why the orphan is unreachable — the five arguments

**It is a duplicate compiled copy of `FUN_00028ea6`, not a second lane.** The two dispatch heads are the
same instruction sequence differing **only in the register field**:

```
live  0x29322  ld.bu -0x3d38,gp,r10   8457c9c2      orphan  0x2A508  ld.bu -0x3d38,gp,r6   8437c9c2
      0x29326  cmp   0x5,r10          6552                  0x2A50C  cmp   0x5,r6          6532
      0x29328  bnc   0x29342          d90d                  0x2A50E  bnc   0x2A52A         e90d
      0x2932A  cmp   0x1,r10          6152                  0x2A510  cmp   0x1,r6          6132
      0x29330  cmp   0x3,r10          6352                  0x2A51A  cmp   0x3,r6          6332
      0x29334  jr    0x295B4                                0x2A51E  jr    0x2A75E
```

The same signature appears three independent times — the dispatch head, the lag tail, and the Kd LERP
preamble (where `sld.w 0x0,ep,ep` `00f5`, `add 0x2,ep` `42f2` and `bh` `cb05` are byte-identical because
they touch no renamed register). Every cal cell in the region is paired with a live twin: `0xC63DA`,
`0xC63DC`, `0xC63DE`, `0xC63E0`, `0xC63E6` (Ki), `0xC63EC`/`EE`, `0xC63F4`/`F6`/`F8`/`FA`/`FC`, `0xC61BC`.
The whole of `[0x2A30E, 0x2B421)` is one recompilation of `FUN_00028ea6`'s body, **byte-identical to
stock**.

1. **The 1 kHz task cannot reach it.** `FUN_0002214a`'s decompile gates on `1 << (gp-0x67fa & 0xf)` and,
   under `(uVar2 & 0x930) != 0`, calls exactly `FUN_00028ea6(0x11)`, `FUN_0002b422(0x12)`,
   `FUN_0002b57a(0x13)` — all direct. Its whole body (~60 calls) contains **no indirect call at all**.
2. **No direct branch in.** Two independently written, positively-controlled `jarl`/`jr` disp22 scanners
   (mine and the tracer's; controls `0x28EA6←0x22522`, `0x34350←0x23276`, `0x3AA2C←0x2291E`, all found
   with the exact expected caller and no extras) return nothing into the region.
3. **No immediate can materialise an address in it.** The 6-byte `mov imm32,reg` scan is
   positively controlled (it finds both known `mov 0xcb7d4` sites) and its one hit, `0x5A366
   mov 0x2b000,r8`, is adjudicated out — it is immediately `st.w`-ed into a config struct as data and
   never used as a branch register. Decisively: **the halfword `0xA892` — the low half of `0x2A892` —
   occurs NOWHERE in the image**, so no `mov`/`movea` pair can build that address.
4. **No pointer table.** No absolute dword anywhere equals `0x2A30E`, `0x2A508` or `0x2A93A`. ⚠ This test
   is **weak on its own** — the control `0x28EA6` also has no such dword — so it is corroborating only.
5. 🛑 **The precedent that would have reopened this is superseded.** I had cited `FUN_0002a30e` as a
   "live function with no discoverable caller", which would have made every null above worthless. That
   framing was **corrected in this kit on 2026-07-14** (`docs/handoffs/2026-07/HANDOFF-2026-07-14-v37-dtc0x49-fix.md`:
   *"both standalone functions are DEAD… 0 callers"*, the live debounce being inlined in
   `m_steer_torque_arbitration` under the control task) and **re-confirmed 2026-09-01** with four
   independent nulls. Two adversaries proved the adjacent `FUN_0002a93a` unreachable the same day by four
   positive-controlled methods each. **`FUN_0002a30e` is dead; it is not the live-without-a-caller case.**

⇒ **EVIDENCE-grade: the two consumers are mutually exclusive because only one exists at runtime. The
output lag is applied ONCE per tick. §2's model, `PID-FRAME-SIZING` §5 and V282 §6's dose table all
stand.**

⚠ **The one residual, stated plainly.** Neither the tracer nor I could build a trustworthy
`jmp [reg]` / `jarl [reg]` census — scanning every 2-byte offset without instruction alignment yields
540 non-`lp` "hits" including `jmp [gp]` (46) and `jmp [tp]` (18), i.e. data misread as code. **The
tracer declared that census unusable and quoted no number from it**, which is the right call and worth
recording as practice. The gap is narrow: an indirect branch still needs the target in a register, and
argument 3 shows no instruction in this image ever loads one.

### 1.2d The adjudication that stops the next reader confusing two things

The other PID cals show a clean **two-cluster** structure: P clamp `0xC61BC` at `0x29E3A`–`0x29E58`
(live) and `0x2AD2C`–`0x2AD44`; D clamp at `0x29EE8`–`0x29F02` and `0x2ADD4`–`0x2ADEC`; I deadband at
`0x29D6E`–`0x29D96` and `0x2AC62`–`0x2AC88`. That **second cluster is `FUN_0002a93a`** (entry `0x2A93A`).
🛑 **The second lag-pole site at `0x2A892`/`0x2A8A2` sits BELOW `0x2A93A`, so it is NOT `FUN_0002a93a`** —
it is a *third* consumer, in the `0x2A508` dispatch. Both are inside the same orphan block and both are
dead, but they are different functions and must not be conflated: the comfortable explanation
("it's just the dead twin again") does not apply to the lag site without the separate argument above.

### 1.3 The Kd family is read from a second function too

`0x2AD64`, inside `FUN_0002a93a` (body `0x2A93A`–`0x2B06F`), is a **second independent LERP walk over the
same pointer family**, confirmed by me from the disassembly:

```
0002ad64  mov    0xcb7d4, r16        ; the Kd LERP pointer table base
0002ad6e  add    r16, ep
0002ad70  sld.w  0x0, ep, ep         ; ep = *(0xCB7D4 + index)  -> a record pointer
0002ad74  ld.w   0x0, r6, r10        ; a SECOND record pointer from the same base
0002ad78  sld.hu 0x2, ep, r13 ; ...  ; classic knot walk
```

**Both indexers compute the SAME slot, from the same variant selector** [EVIDENCE, from the decompiles]:
`FUN_0002a93a` does `(uint)*(byte *)(gp − 0x674e) << 2` and `FUN_00028ea6` does the identical thing at
its lines 804 / 810 / 861, reaching the Kd LERP at line 1059. The tracer checked the Ghidra
variable-reuse trap explicitly — `iVar23` is not reassigned between line 861 and line 1059 — so the index
really is `selector × 4`, in both branches. With the measured live selector **7**, that is
`0xCB7D4 + 28 = 0xCB7F0 → 0xE511C` and no other record.

**Correction to my own first reading of `0x2AD6E`/`0x2AD74`: it fetches ONE record, not two.** The two
addends are the same value — the compiler simply failed to CSE `*(&PTR_0xCB7D4 + iVar)`, once for the
record base and once for `record + 10` (the y-knot array). Byte proof in the live copy at `0x29E6E`:
`mov r12,ep` then `mov r12,r10` — the same index into both.

⇒ **`0xE511C` is SHARED IN CODE (two indexers, same slot) but PRIVATE IN EFFECT (only one indexer can
execute).** Editing it changes the live rate PID's Kd and nothing else.

⚠ Two things a Kd edit must account for. **(a) The LERP argument is `idx & 0xff`**, ceiling 255, and
`gp-0x674b` is that same clipped byte while `gp-0x697a` is an *unclipped halfword* — they diverge above
255, so `gp-0x697a` is not a proxy for the Kd knot index. **(b) Slot 7's Kd table is FLAT
(`Y = [128,128,128,128]` on `X = [0,11,22,32]`), so the knot index cannot change Kd at all today** — any
Kd edit is a change to the Y knots and applies across the entire index domain. There is no way to make
Kd index-dependent without also moving the X knots.

⚠ **The slot value 7 is a wire measurement, not re-derived here.** If 7 is wrong, everything specific to
`0xE511C` moves with it. The *structural* claim — that both copies index the same slot as each other,
whatever it is — does not depend on the value. [BELIEF on the value, EVIDENCE on the structure.]

### 1.4 Interlocks, register-indirect walkers, and image transfer

**Why a census on the V282 image is valid for V283 and V284** — "a null from the wrong image is not a
null" is a standing rule here, so this is stated rather than assumed. V282 → V283 differs in **5 bytes**
(`0xC63E6` Ki plus a CRC); V283 → V284 in **12 bytes** (the slot-7 Kp record's X and Y plus one page
CRC). **No code byte differs between any of them**, and `0xC63E8`/`EA`/`EC`/`EE` = 923/1560/992/507 and
`0xC6446` = 5244 are byte-identical across V281 rev 3, V282 and V283. A **code** census on V282 therefore
transfers. [EVIDENCE — confirmed independently by `team-lead` from the images.]

**CRC trailers that an edit must recompute:**
- `0xC63E8`/`EA`/`EC`/`EE` → block `[0xC6000, 0xC6FFC)`, trailer **`0xC6FFC`**. Plain CRC-32 (IEEE,
  reflected, poly `0xEDB88320`, init/final `0xFFFFFFFF`), little-endian, reproduced **exactly** on both
  images: V282 `0x75EADF72`, stock `0xEF3C9E0C`.
- `0xE511C` → block `[0xE5000, 0xE5FFC)`, trailer **`0xE5FFC`**: stock `0x24BA0614` → V282 `0x8EF2A67E`,
  both self-consistent.
- `0xCB7D4` → **UNVERIFIED.** The `0xCB000` range does not satisfy `crc32(base..base+0xFFB)`; its `+0xFFC`
  dword is `0x000DCA74`, identical in stock and V282, and looks like a length field. **Do not record this
  as "no CRC needed"** — run `analysis-2020accord/lib/verify_bootloader_crc.py::_blocks()` and read the
  answer. (No candidate in this study edits `0xCB7D4`.)
- 🛑 **The blocks are a LINKED LIST, not uniform 4 KB pages.** The tracer's first report proposed a
  per-`0x1000` scheme and **retracted it**: `[0x013000, 0x0C4FFC)` is ONE `0xB1FFC`-byte block covering
  all app code, verified on both images (`crc32` = `0x4EB06B44` V282 / `0x48F24975` stock, each matching
  the dword at `0xC4FFC`; link fields `0xC4FF4`/`0xC4FF6` read start_page 0, num_pages `0xC6`). An
  existing kit memory records that the divide-by-`0x1000` inference "nearly caused a brick". **Never
  infer a trailer address by dividing by `0x1000`.**

**Register-indirect cal-block access does exist** — the thing operand-text search cannot see. A
controlled scan for `mov imm32,reg` with an immediate in the cal windows found four sites hitting
`0xC6000`. `0x146DC` loads `0xC6000`, computes `end = 0xC7000`, and runs a 16-bytes-per-iteration
`ld.w`/`sst.w` loop to `0xFA800000` — **it copies the entire `0xC6000` block, all four PID cells
included.** `FUN_00059560` is an address translator (`p − 0x058C6000`, mapping `0xC6000 → 0xFA800000`)
and `0x5963E` is a bounds guard for writes into `[0xC6000, 0xC8000)`. [BELIEF, callers not traced: these
are the reprogramming/diagnostic path, not a live control-loop reader.] They matter here only in that
**they prove "no other operand-text reader" was never sufficient as a census** — which is exactly why the
raw scan mattered.

**No lockstep/plausibility monitor and no EME/governor consumer of these six cells was found** — but that
is a "did not find", and given the copy loop above it is not a proven zero.

🛑 **`r24` does NOT pass through the output lag.** My own scan is the proof: `0xC63EC`/`0xC63EE` have
exactly two readers and **neither is in `FUN_0003aa2c`**, where `gp-0x6ada` (r24) is written at `0x3AD5A`.
This is the topology the whole 7 Hz sizing depends on, and it is now confirmed by a second method.

⚠ **`0xE511C` is not virgin, and the null is not clean.** Kd is 128 in **284 of 286 builds and in stock**.
The two exceptions are **V279 and V279 rev 1**, which set it to `[0,0,0,0]` — but confounded with a
zeroed feedback and Kp flat 256, i.e. the loop was opened — and **V279 is recorded UNFLOWN**. So Kd has
never been moved as an isolated lever and has never flown at any value but 128. That is a
**never-tried**, not a FALSIFIED and not an INERT-BY-MODE. `0xC63E8`/`EA`/`EC`/`EE` are byte-identical in
all 287 images and have **never been touched at all**.

---

## 2. The loop, re-derived from the bytes

Integer arithmetic exactly as `FUN_00028ea6` executes it (instruction addresses in
`PID-FRAME-SIZING-KP-KD-2026-09-04.md` §2, which I re-read from the image), lifted to the z-domain at
**T = 1 ms**:

```python
z  = exp(2j*pi*f*T)
C(f)    = Kp/256  +  (Kd/8)*(1 - 1/z)  +  (Ki/32768)/(1 - 1/z)      # P, D, I
Hlag(f) = (b/32768) * (1 + 1/z) / (1 - (a/1024)/z)                  # a=0xC63EC, b=0xC63EE
F(f)    = (b/1024)  * (1 + 1/z) / (1 - (a/1024)/z)                  # a=0xC63E8, b=0xC63EA
Zservo  = F(f) * C(f) * (254/256) * Hlag(f) * (5346/32768)
R(f)    = ( C_cand * Hlag_cand ) / ( C_base * Hlag_base )            # F, taper, gain, PLANT all cancel
```

**Cals, byte-read** — `Ki 0xC63E6 = 50` · `fb EMA 923/1560` · `out-lag 992/507` · `gain 0xC6CD0 = 5346` ·
`Kd 0xE511C n=4 X=[0,11,22,32] Y=[128,128,128,128]` · `Kp 0xE5378 n=5 X=[0,68,112,136,208] Y=[248]×5`.

**Exact pole frequencies** (`−ln(a/1024)/2πT`, not the Euler approximation): **out-lag 5.053 Hz**,
**feedback 16.527 Hz**. *(PID-FRAME quotes 15.7 Hz for the feedback corner; that is `(1−a/1024)/2πT`, the
Euler form. Nothing downstream turns on it — my code uses the exact z-domain — but the correct number is
16.53 Hz, which is also what the V282 study quotes.)* **DC of the lag `2b/(32(1024−a))` = 0.9902**;
DC of the feedback `2b/(1024−a)` = 30.891. Kd/Kp corner **9.636 Hz**.

### 2.1 ✅ Validation against the wire, with no fitted parameter [EVIDENCE]

GRINDING-DEEP §2 measured the LKAS lane (aggregator counts per wheel-rate count) on V280 rev 2:
**creep 20 Hz = 1.90 ∠−69°**, **loaded high-angle 7 Hz = 2.50 ∠−62°**. Using the *regime-appropriate* Kp
(creep is low demand index → stock LERP ≈ 248–300; loaded high-angle is high index → ≈ 600–696):

| stratum | f | Kp | model phase | measured | **implied PLANT phase** |
|---|---|---|---|---|---|
| creep hands-off | 20 Hz | 248 | −65.1° | −69° | **−3.9°** |
| creep hands-off | 20 Hz | 300 | −69.4° | −69° | **+0.4°** |
| loaded high-angle | 7 Hz | 600 | −61.3° | −62° | **−0.7°** |
| loaded high-angle | 7 Hz | 696 | −63.4° | −62° | **+1.4°** |

**The servo lane's phase is the electronics.** This is what licenses reading `R(f)`'s rotation directly as
the lane's phase change, and it is an independent confirmation of the 1 kHz tick and of the whole mirror.

---

## 3. ⭐ Why more Kp makes the grind worse — the phase mechanism

| Kp | `|Z|` @20 Hz | phase | **Re (damping)** |
|---|---|---|---|
| 248 | 1.90 | −65.1° | **+0.80** |
| 300 | 1.99 | −69.4° | +0.70 |
| 372 | 2.12 | −74.7° | +0.56 |
| 440 | 2.27 | −79.1° | +0.43 |
| 512 | 2.43 | −83.2° | +0.29 |
| 600 | 2.65 | −87.4° | +0.12 |
| 696 | 2.90 | −91.3° | **−0.07** |

Naive `|Z|` reasoning predicts *more* Kp → *more* damping → *less* grind, which is the wrong sign against
the record. The phase fixes it: **P is phase-flat, so adding Kp dilutes the D term's lead and rotates the
lane through quadrature and past it.** `Re` peaks near Kp 250–300 and is gone by 600.
[EVIDENCE for the arithmetic; identifying `Re` with the operator's grinding is the record's claim, BELIEF.]

---

## 4. GATE 2a — the 7.3 Hz strong-turn ring

**Method.** `A9.3` of `STUTTER-7HZ-V283-r36-r38` de-embeds the two arms at `f0` on 63 windows,
**normalised** so `Ls + Lr ≡ 1`. Only the servo arm carries the controller and the lag, so
`L_new = L_today · (Ls·R(7.3) + Lr)`. **This result does not depend on `s`** — the normalised split is
`s`-free. Pooled `Ls 0.55∠+96°`, `Lr 1.19∠−27°`; r36 (the dissenting route, largest servo share)
`0.69∠+85° / 1.16∠−36°`; r38 `0.42∠+95° / 1.12∠−22°`.

### 🛑 4.0 The operating point, and why the interval matters more than the point estimate

`|L_tot(7.3, Kp 248)| = **0.976 [0.944 – 0.990]**`, from a per-episode ACF fit. **This supersedes the
0.92–0.94 this study was briefed with**, which itself superseded a modelled 0.90. Consequences:

| | `|L|` | `|1−L|` today | implied sensitivity peak |
|---|---|---|---|
| optimistic end | 0.944 | 0.056 | ×18 |
| **point estimate** | **0.976** | **0.024** | **×42** |
| pessimistic end | 0.990 | 0.010 | ×100 |

**Which candidates pass is interval-invariant** — the gate is a ratio, `|Ls·R + Lr|`, and that ratio does
not contain `|L_today|`. **The absolute margin is not**: today's `|1−L|` is 0.010–0.056, against the
0.068 the briefed 0.93 implied. **The ring sits 2.8× to 6.8× closer to self-sustaining than assumed, so
every degrading candidate is correspondingly more dangerous and every improving one buys more.**

⚠ Two honest caveats on this number. **(a)** `|1−L| = 1 − |L|` only if `∠L_today = 0` exactly. The ACF fit
gives the magnitude, not the phase, so my `|1−L|` figures are **lower bounds** on the margin — the
conservative direction, which is what a gate wants, but they are not point estimates. **(b)** A
sensitivity peak of ×42–100 is hard to reconcile with the operator's own report of *"a damped ring at
~40 %"* on V281 rev 3. I am not able to close that gap, and it is the same class of problem as §9.2: the
map from a loop-gain number to what the car feels is not calibrated. Carry `|L|` as the gate and do not
convert it into a felt amplitude.

**`|L(7.3)|` at the PESSIMISTIC end (0.990), pooled split. `≥ 1.000` = the cycle returns.**

| lag pole | Kd 0 | 48 | **64** | **96** | **112** | **128 (live)** | 160 | 192 |
|---|---|---|---|---|---|---|---|---|
| **5.05 Hz (live)** | **1.287** | **1.174** | **1.137** | **1.064** | **1.028** | **0.993** | 0.923 | 0.856 |
| 6.99 | 1.252 | 1.111 | 1.065 | 0.973 | 0.928 | 0.884 | 0.797 | 0.714 |
| 7.97 | 1.229 | 1.078 | 1.028 | 0.929 | 0.881 | 0.833 | 0.739 | 0.650 |
| 9.94 | 1.184 | 1.015 | 0.960 | 0.850 | 0.796 | 0.742 | 0.637 | 0.538 |
| 11.94 | 1.141 | 0.960 | 0.901 | 0.783 | 0.724 | 0.666 | 0.553 | 0.446 |
| **14.98** | 1.085 | **0.893** | **0.829** | **0.702** | 0.639 | 0.577 | 0.455 | 0.339 |

r36's curve (largest servo share, so the most sensitive to any servo-arm change) is within ±0.05 of the
pooled throughout and never reverses a verdict.

### 🛑 4.1 A Kd cut alone crosses unity at EVERY value tested

| Kd (pole unchanged) | 112 | 96 | 80 | 64 | 48 | 0 |
|---|---|---|---|---|---|---|
| `|L(7.3)|` at 0.990 | **1.028** | **1.064** | **1.101** | **1.137** | **1.174** | **1.287** |
| `|L(7.3)|` at 0.976 | **1.013** | 1.049 | 1.085 | 1.121 | 1.158 | 1.269 |
| `|L(7.3)|` at 0.944 | 0.980 | 1.015 | 1.049 | 1.085 | 1.120 | 1.228 |

**At the point estimate, even a Kd 128 → 112 nibble is already above unity.** Only at the *optimistic*
end of the interval does 112 survive, and nothing below it does anywhere. The record's *"less D moves
the trouble down to ~8 Hz"* substantially under-states this: at the base pole a Kd cut does not relocate
the trouble, **it puts the loop above unity at the ring's own frequency.** 🛑 **DO-NOT-FLASH a Kd cut in
isolation, at any value, across the whole interval.**

The mechanism is A9.3's, generalised: `Ls` and `Lr` sit ~123° apart, near quadrature, and `Lr` is the
larger arm. Shrinking and rotating `Ls` moves the sum *away* from unity in the direction that **increases**
its magnitude. It is the same geometry that makes the first ~37 % of a Kp *increase* almost free.

---

## 5. GATE 2b — the 20 Hz creep grind

**Method.** The aggregator damping budget `Re(Z_servo·R(20) + s·Z_r24)`, which is plant-free: every lane
enters the 1 kHz aggregator with a unit coefficient (`FUN_0003aa2c`). `Z_servo = 1.90∠−69°` and
`Z_r24 = 3.23∠+5°` are GRINDING-DEEP §2's **measured** creep phasors; `s = 0.43` is the V282 tap's measured
`|r24|`/closed-form ratio. **Positive `Re` = damping.** Today `Re_total = +2.07` (servo +0.68, r24 +1.38).
GRINDING-DEEP §2 classifies the 20 Hz mode as **driven, not self-sustained** (net `Re > 0`), which is why
damping — not `|L|` — is the operative metric here.

**`Re` @20 Hz. Higher is better; below +2.07 is a regression.**

| lag pole | Kd 0 | 48 | **64** | **96** | **128 (live)** | 160 | 192 |
|---|---|---|---|---|---|---|---|
| **5.05 Hz (live)** | +0.85 | +1.31 | **+1.46** | **+1.76** | **+2.06** | +2.37 | +2.67 |
| 6.99 | +0.74 | +1.41 | +1.63 | +2.07 | +2.51 | +2.95 | +3.39 |
| 7.97 | +0.71 | +1.48 | +1.73 | +2.24 | +2.75 | +3.27 | +3.78 |
| 9.94 | +0.68 | +1.65 | +1.98 | +2.63 | +3.27 | +3.92 | +4.57 |
| 11.94 | +0.69 | +1.86 | +2.25 | +3.03 | +3.81 | +4.59 | +5.37 |
| **14.98** | +0.76 | **+2.20** | **+2.68** | **+3.63** | **+4.59** | +5.55 | +6.51 |

**Cross-check against the record's own independent calculation.** V282 §6.2 (which rescaled only the r24
term and did *not* re-derive the servo from bytes) gives `Re@20` +1.43 as-built → +3.03 for the 15 Hz pole,
a **ratio of 2.12**. My byte-derived re-derivation gives +2.07 → +4.59, a **ratio of 2.22**. The absolute
offsets differ (they used `Re_servo(20) = −0.004` from a modelled Kp-248 servo; I use the measured phasor
and the byte-derived phase), but **the ratio the ranking turns on agrees to 5 %.** [EVIDENCE] The V282
study's own caveat — that it inherited the deep analysis's servo phase model — is discharged.

**Sensitivity to `s`, the one estimated quantity, over its whole measured range 0.30–0.52:**

| shape | s = 0.30 | 0.37 | 0.43 | 0.52 |
|---|---|---|---|---|
| as-built (992/507, Kd 128) | +1.65 | +1.87 | **+2.06** | +2.35 |
| 962/982 (pole 10) + Kd 96 | +2.21 | +2.43 | **+2.63** | +2.92 |
| 932/1458 (pole 15) + Kd 64 | +2.26 | +2.48 | **+2.68** | +2.97 |
| 992/507 + **Kd 64 alone** | +1.04 | +1.27 | **+1.46** | +1.75 |

The sign of every verdict is stable across the whole `s` range.

---

## 5b. GATE 2c — 13–15 Hz, where the phase margin actually is

`PID-FRAME` §5 identifies the loop's phase margin as spent by the **feedback EMA** (16.53 Hz pole,
−50.5° at 20 Hz), and the record's independently-measured inner-loop PM is **~50° at 13–15 Hz**. Every
candidate must be scored there too. `|R|` / `∠R` at **13.5 Hz** — a *positive* angle is returned phase
margin, a *negative* one is margin spent:

| lag pole | Kd 0 | 48 | **64** | **96** | **128 (live)** | 192 |
|---|---|---|---|---|---|---|
| **5.05 Hz (live)** | 0.58 / −53.5° | 0.66 / −26.2° | **0.71 / −19.0°** | **0.84 / −7.9°** | **1.00 / 0.0°** | 1.35 / +9.9° |
| 7.97 | 0.83 / −43.5° | 0.95 / −16.1° | 1.03 / −9.0° | 1.22 / +2.1° | 1.45 / +10.0° | 1.96 / +19.9° |
| 9.94 | 0.97 / −37.7° | 1.11 / −10.3° | 1.20 / −3.2° | **1.43 / +8.0°** | 1.69 / +15.8° | 2.28 / +25.7° |
| **14.98** | 1.22 / −26.1° | 1.39 / +1.3° | **1.50 / +8.4°** | 1.79 / +19.6° | 2.12 / +27.4° | 2.86 / +37.3° |

**Reading.** A Kd cut **alone** spends margin exactly where the loop has least of it: Kd 128 → 64 at the
live pole costs **−19.0°** of a ~50° budget, i.e. **38 % of the whole phase margin for one cal edit**.
Kd → 48 costs −26.2°, over half. That is an independent second reason a Kd cut alone is DO-NOT-FLASH,
alongside the ring result in §4 and the 34 Hz sign inversion in §6.2.

Every surviving pair **returns** margin rather than spending it: **A (+8.0°)**, **B (+8.4°)**,
**C (+2.1°)**, **D (+15.8°)**. Candidate **E** (feedback pole 16.53 → 25.03 Hz) returns **+10.9°** at
13.5 Hz — it acts directly on the pole that owns the margin, which is why it is the largest single-lever
phase return in the study, and also why its noise cost is the one to watch.

⚠ These are **changes** to the loop's phase, not the phase margin itself: the absolute ~50° figure is the
record's measurement, and I have not re-derived it. A candidate that returns +8° should be read as
"~50° → ~58°", not as a computed margin. [EVIDENCE for `∠R`; the 50° baseline is the record's.]

---

## 6. The HF risk, re-derived — and where the lane stops damping

### 6.1 The blind-band increment, computed from scratch

The 427 tap is 50 Hz sampled (Nyquist 25 Hz); the 0x18F streams are 100 Hz (usable to ~40 Hz). The
unobservable increment is `worst HF ratio above 25 Hz / ratio at 25 Hz`:

| lag pole (a/b, DC held) | ×@20 Hz | ×@25 Hz | worst above 25 | **BLIND INCREMENT** |
|---|---|---|---|---|
| 980/697 → 6.99 Hz | 1.35 | 1.36 | 1.38 | **×1.018** |
| 974/792 → 7.97 Hz | 1.51 | 1.53 | 1.58 | **×1.029** |
| 962/982 → 9.94 Hz | 1.82 | 1.86 | 1.97 | **×1.055** |
| 950/1172 → 11.94 Hz | 2.09 | 2.17 | 2.36 | **×1.086** |
| **932/1458 → 14.98 Hz** | 2.45 | 2.60 | 2.96 | **×1.142** |
| 914/1743 → 18.09 Hz | 2.74 | 2.96 | 3.58 | ×1.209 |
| 897/2012 → 21.07 Hz | 2.96 | 3.25 | 4.16 | ×1.280 |

**I reproduce the V282 study's ×1.14 for the 15 Hz pole exactly, from my own arithmetic.** The deep
analysis's earlier *"adding ×2.9 of loop gain blind above 25 Hz"* remains an overstatement of the
**unobservable** fraction by ~2.5×. It is *not* an overstatement of the total: ×2.45 at 20 Hz is a large
authority change in the band the grind lives in, and it is fully visible there.

### 6.2 ⭐ Where the servo lane crosses from damping to anti-damping

`Re(Z_servo) = 0` when the lane's phase reaches −90°. Above that frequency the lane **pumps**. Raising the
lag pole pushes the crossing up; cutting Kd pulls it down, hard (Hz, Kp 248):

| lag pole | Kd 0 | 32 | 48 | **64** | **96** | **128** | 192 |
|---|---|---|---|---|---|---|---|
| **5.05 (live)** | 8.9 | 13.3 | 19.7 | **34.0** | **53.0** | **61.2** | 68.5 |
| 9.94 | 12.6 | 21.5 | 36.0 | 51.1 | 65.8 | 72.5 | 78.8 |
| 14.98 | 15.5 | 31.0 | 50.9 | 64.2 | 76.6 | 82.4 | 87.9 |

🛑 **This is the strongest argument against a Kd cut, and the record does not contain it.** At the live
pole, `Kd 128 → 64` drags the damping/anti-damping crossover from **61 Hz down to 34 Hz** — it turns the
whole 34–61 Hz band from damping into pumping, and **34–61 Hz is entirely inside the blind band.**
`Kd → 48` puts it at 19.7 Hz, *below the grind itself*. A Kd cut is not a benign HF-gain reduction; it is a
**sign inversion in a band no instrument on this car can see.**

The pairing repairs it: pole 15 Hz + Kd 64 puts the crossing at **64.2 Hz**, marginally *above* today's
61.2 Hz, while carrying only ×1.54 of HF gain instead of ×2.60–2.96.

### 6.3 HF gain of the whole servo arm, relative to as-built (includes the feedback EMA's roll-off)

| pole / Kd | 25 Hz | 40 Hz | 80 Hz | 250 Hz | 500 Hz |
|---|---|---|---|---|---|
| 5.05 / 128 (live) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 5.05 / 64 | 0.60 | 0.55 | 0.52 | 0.52 | 0.51 |
| 7.97 / 96 | 1.21 | 1.20 | 1.20 | 1.19 | 1.19 |
| 9.94 / 96 | 1.47 | 1.48 | 1.49 | 1.49 | 1.49 |
| **14.98 / 64** | **1.54** | **1.54** | **1.53** | **1.53** | **1.53** |
| 14.98 / 128 | 2.60 | 2.80 | 2.92 | 2.96 | 2.96 |

⚠ **There is no derivative filter anywhere in this loop.** `D = (dE·Kd)>>3` is an ideal differentiator to
Nyquist, bounded only by the ±10240 clamp and by whatever the feedback EMA removes. Any candidate that
raises HF gain raises sensor-noise injection in the same ratio.

---

## 7. DC, authority, and clamps — the constraints that must be held

- **The lag's DC gain is held to 0.9899–0.9905 at every candidate** (`b = round(0.9902·32·(1024−a)/2)`),
  i.e. within 0.06 % of today's 0.9902. **Kd has no DC term at all.** So neither parameter changes
  torque-per-command in steady state, and neither can by itself fix the deadband.
- **What openpilot's outer loop sees**, `|C·Hlag|` relative to as-built: at 0.2 / 0.5 / 1 / 2 / 3 Hz every
  candidate in the passing set is within **1.000–1.07**; the largest departure is **×1.23–1.34 at 5 Hz**
  for the 15 Hz pole. **The outer tune is essentially untouched below 3 Hz.**
- **Clamp headroom.** Measured on V283 strong-turn frames: `|P|` p50 ≈ 1900 (clamp 15360, 12 %), `|D|`
  880–1552 (clamp 10240, 9–15 %), `|I|` 3377–7004 (ceiling 10240, 68 %), tap `|T|` 778–868 at a stall
  (output clamp 3072). `|D|` scales linearly with Kd — even Kd 256 reaches only 30 % of the D clamp. The
  lag pole is **downstream of the sum clamp** and holds DC, so it scales only the AC above ~5 Hz; the
  measured 18–22 Hz bar amplitude is 31 raw, so the output clamp is nowhere near being approached by the
  ripple. **No candidate rails anything.** [EVIDENCE for the clamps and the scaling; the measured
  amplitudes are the record's.]

---

## 8. The surviving (pole, Kd) pairs, ranked

**Constraints, written down before the search** (all five must hold):
`C1` ring **ratio** `|Ls·R + Lr| ≤ 1.000` on the pooled split **and** r36's **and** r38's — equivalently
`|L(7.3)|` no worse than today's at the *same* operating point, so the gate holds across the whole
[0.944, 0.990] interval · `C2` `Re(20) ≥ +2.06` at `s = 0.43` **and** `≥ +1.65` at `s = 0.30`, i.e. no
worse than today at **both ends of the measured `s` range** · `C3` lag DC within 0.5 % of 0.9902 ·
`C4` blind increment above 25 Hz ≤ ×1.15.

| # | cells | pole | Kd | ring ratio | `|L|`@0.976 | `|L|`@0.990 | `Re`@20 (s .43/.30) | HF ×, flat | Re=0 xover | blind |
|---|---|---|---|---|---|---|---|---|---|---|
| — | as-built V283 | 5.05 | 128 | 1.000 | 0.976 | 0.990 | +2.06 / +1.65 | 1.00 | 61.2 Hz | — |
| **A** | `0xC63EC/EE` = **962/982** | 9.94 | **96** | **0.891** | **0.838** | 0.850 | **+2.63 / +2.21** | 1.47 | 65.8 Hz | ×1.055 |
| **B** | `0xC63EC/EE` = **932/1458** | 14.98 | **64** | **0.874** | **0.817** | 0.829 | **+2.68 / +2.26** | **1.54** | 64.2 Hz | ×1.142 |
| **C** | `0xC63EC/EE` = **974/792** | 7.97 | **96** | 0.953 | 0.916 | 0.929 | +2.24 / +1.83 | 1.21 | 61.1 Hz | ×1.029 |
| **D** | `0xC63EC/EE` = **962/982** only | 9.94 | 128 | 0.806 | 0.732 | 0.742 | +3.27 / +2.86 | 1.86 | 72.5 Hz | ×1.055 |
| **E** | `0xC63E8/EA` = **875/2301** only | — | 128 | 0.925 | 0.903 | 0.916 | +2.64 / +2.22 | 1.51 | 78.9 Hz | ×1.179 |
| **F** | `0xE511C` Kd → **160** alone | 5.05 | 160 | 0.948 | 0.910 | 0.923 | +2.37 / +1.95 | 1.25 | 65.6 Hz | ×1.000 |
| 🛑 | `0xE511C` Kd → 112 **alone** | 5.05 | 112 | **1.038** | **1.013** | **1.028** | +1.91 / +1.49 | 0.88 | 57.8 Hz | 1.00 |
| 🛑 | Kd → 96 alone | 5.05 | 96 | **1.079** | **1.049** | **1.064** | +1.76 / +1.34 | 0.79 | 53.0 Hz | 1.00 |
| 🛑 | Kd → 64 alone | 5.05 | 64 | **1.163** | **1.121** | **1.137** | **+1.46 / +1.04** | 0.60 | **34.0 Hz** | 1.00 |

**Reading:**

- 🛑 **Every Kd cut alone fails C1 and C2 and inverts the lane's sign in the blind band. DO-NOT-FLASH in
  isolation, at any value.**
- **The pole raise alone (D) beats every (pole, Kd<128) pair on both symptom metrics.** Only the HF column
  argues against it.
- **B is the pidframe pairing, and it is the best HF trade in the table**: both symptom metrics better than
  today, the damping/anti-damping crossover essentially unchanged, and **HF gain ×1.54 flat instead of
  ×2.60–2.96**. It is also the largest lag-pole move, so it carries the largest blind increment.
- **A is the balanced pick** — smaller pole move, smaller Kd cut, blind increment ×1.055, crossover not
  moved down.
- **C is the conservative pick** — barely above today on `Re`, blind increment ×1.029.
- ⭐ **E is the smallest-risk-of-the-unknown pick.** The feedback EMA 923/1560 → **875/2301** (pole
  16.53 → 25.03 Hz, DC held at 30.89) delivers `|L(7.3)|` 0.976 → 0.903 and `Re@20` +2.06 → +2.64 —
  comparable to A on `Re` though weaker on the ring — on **two cells that are single-site in the first
  place**, so it does not rest on the
  orphan-liveness chain at all. It also pushes the `Re=0` crossover furthest (61 → 79 Hz), the best of any
  single lever. Its cost is different in kind: **×1.51 more sensor noise into an unfiltered ×16
  differentiator**, exactly the risk `PID-FRAME` §7c flagged, and its blind increment is ×1.179 —
  self-limited only because the EMA has a **zero at Nyquist**.
- ⭐ **F is the smallest-footprint candidate in the study and it was not on anyone's list.** A Kd
  *raise* — one cal record, four halfwords plus a CRC — passes all five constraints: ring ratio 0.948,
  `Re@20` +2.37, blind increment **×1.000** (the lag is untouched, so nothing changes in the blind band's
  *shape*), and it moves the `Re=0` crossover the right way (61 → 66 Hz). Its cost is a flat ×1.25 of HF
  gain everywhere through an unfiltered differentiator, and `|D|` rising from 15 % to 19 % of its clamp.
  **It is the direct opposite of the lever this study was asked to evaluate**, and it falls out of the
  same arithmetic that condemns the cut.

---

## 9. 🛑 CAN ANY OF THIS BE READ FROM ONE SHORT SYMPTOMATIC DRIVE? Honestly: not yet

The kit's law is that a build must be interpretable from ~15–30 s of engaged symptomatic frames, and that
"we would not be able to tell" makes a build **not ready**, not a verdict. Three separate problems.

### 9.1 The 7 Hz benefit is at the instrument's FLOOR

`F7` reads **0.00 episodes per 100 s across r35/r36/r37/r38 and 206 s of high-angle time**. Every candidate
here *lowers* `|L(7.3)|`. **A benefit therefore cannot register — only a regression can.** The F7 census is
a one-sided safety check for this lever, not a benefit measure.

**What would work instead**: the **continuous** ring statistic — `rip/L` at `f0` in engaged hands-light
high-angle windows (A9.2 already tabulates it: r35 0.140–0.252 by index band, r36 0.046–0.112) and
`stutter283`'s `|Ls|`/`|Lr|` de-embed. Since the sensitivity peak scales as `1/|1−L|`, the predicted
reduction in `rip/L` is:

| candidate | at `|L|` = 0.944 | **0.976** | 0.990 |
|---|---|---|---|
| **A** pole 9.94 + Kd 96 | ÷4.3 | **÷9.2** | ÷21 |
| **B** pole 14.98 + Kd 64 | ÷4.9 | **÷10.6** | ÷25 |
| **C** pole 7.97 + Kd 96 | ÷2.7 | **÷5.5** | ÷13 |
| **D** pole 9.94 only | ÷6.2 | **÷13.7** | ÷32 |
| **E** fb pole 25.03 only | ÷2.3 | **÷4.1** | ÷8.7 |
| **F** Kd 160 only | ÷2.3 | **÷4.3** | ÷9.2 |

🛑 **Read that table as a ranking, not as a prediction.** The *ordering* is robust and the *direction* is
certain, but the **magnitude spans an order of magnitude across the operating-point interval alone** —
and that is before §9.2's separate finding that the map from a loop-gain change to a felt or measured
amplitude is not calibrated at all. Any pre-registration must therefore be written as **"`rip/L` falls,
and by at least ÷2.3"**, not as a point prediction. Register it as a ratio to the same drive's own replay
(V282 §7 item 2), and fix the window definition and detector **before** the drive.

### 9.2 The 20 Hz magnitude is NOT predictable — the calibration step fails

I tried to calibrate `ΔRe → Δbar amplitude` on the one cross-build step available. It does not work:

- V280 rev 2's creep Kp, pinned from the **measured** lane phase (−69°) against the byte model: **≈300**.
- `Re_total` at Kp 300 = **+2.051**; at V283's flat 248 = **+2.148**. **A +4.7 % change.**
- Measured effect of that step: bar amplitude p50 **69 → 24 raw (×0.348)**, presence 65 % → 16 %.

A 4.7 % damping change cannot produce a 2.9× amplitude change under any driven-mode model unless the
*total* damping sits within a few percent of zero — in which case the calibration is singular and its
output meaningless, **and it would contradict GRINDING-DEEP §2's own classification of the 20 Hz mode as
driven with net `Re` +3.90**. Either the grind's Kp dependence acts through a channel other than the 20 Hz
`Re` budget, or the V280 rev 2 → V281 rev 3 contrast carries a confound (those builds differ by more than
Kp, and the routes differ). **I can give the sign of a candidate's 20 Hz effect. I cannot give the size,
and I cannot convert a predicted `ΔRe` into a predicted bar amplitude.** [EVIDENCE for the arithmetic and
the inconsistency; BELIEF for which explanation is right.]

### 9.3 GATE 1 is CLOSED — but the margin it closed on is thinner than the margin it protects

GATE 1 clears (§1.2c). It clears on a **chain of five arguments**, one of which is a record correction
and one of which (the `jmp [reg]` census) is an admitted gap. That is enough to publish "the pole is
applied once per tick", and it is *not* enough to make the lever ready, because §9.1 and §9.2 are
untouched by it.

### 9.4 ⭐ THE PROBE — still the recommendation, now for two reasons instead of three

> **An inert, read-only tap on `gp-0x3d3c`, the output-lag filter state, plus a `|D| ≥ |P|` comparator
> rung sited where both operands carry no DC.**

It is the right probe by the kit's own design law: the quantity is already computed, a read-only tap
changes nothing on the car, and it lets every candidate dose be sized offline from one drive.

1. **It measures the lag's real transfer on the car**, so the ×2.45 at 20 Hz stops being a modelled
   number and becomes a measured one *before* anything is dosed. This is now the primary reason.
2. **It is an unusually clean discriminator and worth having for its own sake.** `gp-0x3d3c`
   (`0xFEDF42C4`) has **exactly four accesses image-wide — two in the live PID, two in the orphan.** If
   the orphan never runs, the value is a clean single-rate filter obeying
   `s[n] = (992·s[n−1] + 507·S[n]) >> 10` against the already-tapped `gp-0x6b38`; if it ever runs, the
   state is written twice in a tick and the recursion breaks. GATE 1 is closed by argument; **this closes
   it by measurement**, and it is the only thing that can.
3. **It is a magnitude channel, not a bare threshold rung** — the design law's requirement — and its
   positive control is the recursion itself, which must hold at DC whatever else is true.
4. **The `|D| ≥ |P|` rung directly measures the D-fraction the whole Kd question turns on**, and unlike
   V282's statistic (D) it compares **AC to AC**: in the frames of interest both operands are zero-DC, so
   it cannot be biased to zero by a pedestal. That is V282 §7 item 4's lesson applied rather than
   restated.

**The sentence a null licenses**: *"`gp-0x3d3c` satisfies the single-instance recursion over N engaged
ticks with residual < X, confirming by measurement that `0xC63EC`/`0xC63EE` are applied once per tick,
and the measured `|H_lag|` at 18–22 Hz matches the modelled value to within Y %, so candidates A–D can be
sized from the wire."* If the recursion does **not** fit, the licensed sentence is *"the pole is applied
twice; §2's transfer functions, the V282 §6 dose table and `PID-FRAME` §5 are all wrong by one pole, and
the lag-pole lever is withdrawn pending re-derivation."*

⚠ **A third rung would be worth more than any of the doses.** Nothing in §9.2 is fixed by this probe: the
`Re` → amplitude map stays uncalibrated, so even a perfectly measured `ΔRe` still cannot be converted
into a predicted grind amplitude. If a rung is free after the two above, the highest-value thing to buy
is whatever discriminates the §9.2 fork — a within-drive contrast that separates "the grind's Kp
dependence is not the 20 Hz `Re` budget" from "the V280→V281 contrast is confounded".

---

## 10. Corrections and disagreements of record produced by this study

0. 🛑🛑 **THE `Re` → BAR-AMPLITUDE MAP FAILS BY TWO ORDERS OF MAGNITUDE, and every recent grind document
   reasons through it.** The byte model puts the servo damping change from V280 rev 2 (creep Kp ≈ 300,
   pinned from its own measured lane phase) to V283 (flat 248) at **+4.7 %**; the measured effect of that
   step was **×0.348** in bar amplitude and 65 % → 16 % in presence. Those cannot both be true under any
   driven-mode model unless the total damping sits within a few percent of zero — which would contradict
   GRINDING-DEEP §2's own classification of the 20 Hz mode as **driven** with net `Re` +3.90.
   **The fork, stated plainly so the next reader does not have to rediscover it: either the grind's
   measured Kp dependence acts through a channel OTHER than the 20 Hz `Re` budget, or the
   V280 rev 2 → V281 rev 3 contrast carries a confound** (those builds differ by more than Kp, and the
   routes differ). 🛑 **Until that is resolved, a predicted `ΔRe` must NOT be converted into a predicted
   bar amplitude.** Sign only. §9.2.
1. **`0xC63EC`/`0xC63EE` are shared in code but private in effect** — a second reader exists at
   `0x2A892`/`0x2A8A2`, sharing the same RAM state `gp-0x3d3c`, but it is in an unreachable duplicate
   compilation. GRINDING-DEEP §3's claim about the *feedback* pair ("exactly one live reader each")
   **remains true and is now confirmed by a second method**. V282 §6.3's *"this lever does not need a new
   probe"* still needs qualifying: it is true of the *effect*, but the census that established it was
   incomplete — `search_instructions` returned 58 matches with `truncated:false` and contained neither
   second site.
2. **PID-FRAME's feedback corner "15.7 Hz" is the Euler form.** The exact pole is **16.527 Hz**. No
   conclusion changes; the number should be quoted as 16.53 Hz.
3. **The pidframe pairing's stated rationale is not what makes it work.** "Lag pole up and Kd down … lowers
   20 Hz loop gain without stripping 7.3 Hz phase" — at 20 Hz the mode is *driven*, so the operative
   quantity is damping, not loop gain, and a Kd cut **lowers** damping. The pairing is still worth having,
   because the Kd cut buys back roughly half the blind-band HF gain the pole raise costs; but the pole
   raise **alone** dominates it on both symptom metrics.
4. ⭐ **New mechanism, not previously in the record**: a Kd cut drags the servo lane's damping /
   anti-damping crossover from **61 Hz to 34 Hz** (Kd 64) or **19.7 Hz** (Kd 48) — a sign inversion inside
   the blind band. A stronger objection to a Kd cut than the phase-lead argument the record carries.
5. **The grind's Kp dependence is a PHASE effect, not a gain effect** (§3); the byte model reproduces its
   measured sign only when the phase is included.
6. **The `Re@20` ratio for the 15 Hz pole is confirmed independently**: V282 §6.2's 2.12 against my
   byte-derived 2.22, from disjoint servo models.
7. **The operating point `|L_tot(7.3, Kp 248)|` is 0.976 [0.944–0.990]**, superseding the 0.92–0.94 this
   study was briefed with and the modelled 0.90 before it. Today's `|1−L|` is **0.010–0.056, not 0.068**.
   Every earlier document quoting a ring margin off 0.90 or 0.93 is optimistic by 2.8–6.8×.
8. ⚠ **`FUN_0002a30e` is DEAD, and the "live function with no discoverable caller" precedent does not
   apply to it.** I asserted the opposite from a 2026-07 framing that was corrected on 2026-07-14 and
   re-confirmed on 2026-09-01. This is the second time that stale framing has been picked up; it is worth
   a memory of its own.
9. ⭐ **Method note worth keeping: "X produces a cell that live code consumes, therefore X is live" is
   only an argument when X is the SOLE producer.** My own liveness argument for the orphan failed exactly
   there — `FUN_00028ea6` writes `gp-0x69b0` twelve times itself. Census the producers before inferring
   from one.
10. ⭐ **Method note: an indirect-jump census that cannot be positively controlled must be declared
    unusable and quoted with NO number.** The tracer's `jmp [reg]` scan produced 540 "hits" including
    `jmp [gp]` and `jmp [tp]` — data misread as code — and it reported the gap instead of the number.
    That is the behaviour the skill's positive-control rule is for.
11. ⚠ **Parity trap on `gp-0x674e`:** `ld.bu` carries displacement bit 0 in `hw1` bit 5, so op `0x3c`
    (even) and `0x3d` (odd) address **neighbouring cells**. `0x2DBD0` and `0x4E646` are op `0x3d` =
    `gp-0x674d`, a different cell. A `gp-0x674e` census that does not split on the opcode over-counts by
    two.

## 11. What would falsify this document

- **The tick rate.** Every frequency scales with it. PID-FRAME §1 pins 1 kHz three ways; §2.1's phase
  validation is a fourth, independent one — the electronics phase would not match the measured lane phase
  at two frequencies under any other tick.
- **The orphan block turning out to be reachable** (§1.2c). Five arguments say it is not, but one of them
  (`jmp [reg]`) is an admitted gap and one is a record correction. If someone finds the entry path into
  `[0x2A30E, 0x2B421)`, the lag is applied twice, and §2, `PID-FRAME` §5 and V282 §6's dose table all
  fall together. **The `gp-0x3d3c` tap in §9.4 is what would settle it by measurement.**
- **`s` outside 0.30–0.52.** §5's sensitivity table shows every sign is stable inside that range, and §4
  does not depend on `s` at all.
- **The operating-point interval widening, or `∠L_today` being far from 0.** §4.0's `|1−L|` figures are
  lower bounds that assume the ring sits exactly at the phase crossing. The ranking survives; the
  predicted magnitudes in §9.1 do not.
- **The de-embed shares `Ls`/`Lr`.** The ring result is entirely theirs. They are measured on 63 windows
  and the r36/r38 variants bracket the pooled value. Independent consistency check: GRINDING-DEEP §2's
  phasors give a servo-to-r24 phase difference of +132° against A9.3's +123°, and after rescaling §2's
  servo from V280's Kp to 248 the magnitude ratios agree to ~1.5×.
- **The identification of `Re` with the operator's grinding**, and of `|L(7.3)|` with his stutter. Both are
  the record's, both are BELIEF, and §9.2 shows the `Re` → amplitude map is currently unsupported.
