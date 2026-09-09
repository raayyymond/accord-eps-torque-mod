# TRACE 2026-09-08 — LKAS rate-PID filter poles, D-term hook, and RAM/flash census for `loopshape`

**STATUS (final, after both re-census addenda)**: Q1, Q2, Q3, Q5, Q6 — EVIDENCE, accepted. Q0, Q7, Q8,
Q9 — EVIDENCE, answered by decompile in the first ADDENDUM (Q7 corrects my own initial raw-disassembly
misread; recorded, not hidden). Q4 (RAM census) — EVIDENCE, fully closed across two further addenda: a
raw little-endian Python scan covering `ld.b`/`ld.bu`/`ld.h`/`ld.hu`/`ld.w`/`st.b`/`st.h`/`st.w`, the
6-byte extended form, and `gp`-based `set1`/`clr1`/`tst1`/`not1` bit-ops; an absolute-pointer and
`movhi`/`movea` register-indirect scan; and a resolved stack/RAM-layout question (a serious apparent
contradiction with this kit's own record was raised and RESOLVED using existing, more authoritative
memory rather than asserted from scratch — see SECOND FINAL ADDENDUM §"stack scare"). **Verdict: YES,
multiple free 32-bit-aligned words exist** — three candidates (`gp-0x6ab0`, `gp-0x68b0`, `gp-0x6c44`,
each with its run) are verified to the fullest standard this session's tools support. One error of my
own (a hand-arithmetic slip on `st.b`'s opcode) was caught and corrected in the SECOND FINAL ADDENDUM,
not left standing.

**Agent**: `tracer` (subagent, reports to `main`). Study/analysis only — nothing built, flashed, or sent.

**Programs used**: `code.bin` (stock, Ghidra, `is_current: true`, 2086 functions, the only program open
this session — confirmed by `list_open_programs`) for all disassembly/decompile. Raw Python byte reads
against the V288 rev 2 image,
`_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
sha256 `94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c` (re-hashed and confirmed this
session, matches the brief).

**Why stock disassembly is admissible** [EVIDENCE, established in `docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md`,
re-confirmed rather than re-derived this session]: a full byte diff of `FUN_00028ea6`'s body
`[0x28EA6, 0x2A2A0)` between V282 and stock returns exactly 2 differing bytes, `0x2A1F0`-`0x2A1F1`
(the V282 gain-source repoint), and V288 rev 2's own diff vs V282 is 91 bytes confined to
`{0x29D72–75, 0xC4BD6–D9, 0xC4BDC–FD, 0xC4C00–2F, 0xC4FFC–FF}` (per `docs/review/ADVERSARIAL-V288-PREREG-2026-09-07.md`).
None of that touches the feedback/output-lag filters, the D clamp bank, or the tick/task code. **All
structural claims below hold for V282 and V288 rev 2 unchanged.**

**Most of this trace is a targeted re-verification of, and additions to, the exhaustive prior session's
`TRACE-2026-09-06-lag-and-fb-pole-census-v282.md`** (same agent identity, `tracer`) — that file is the
primary source for Q1–Q3 and is cited throughout rather than re-derived line-by-line; new work this
session is the Q4 RAM census (fresh, GhidraMCP `search_instructions` this session) and the Q5 free-flash
re-confirmation against the *current* V288 rev 2 image (the prior census was against a pre-cave V282
free-flash figure).

---

## Q1 — the feedback lag filter (`0x28F7C`–`0x28FBC` / actually `0x28F86`–`0x28FA8`)

**Arithmetic** [EVIDENCE, `disassemble_bytes dry_run:true`, stock, TRACE-2026-09-06 Task 2.1, spot-checked
this session]:

```
0x28F4C  ld.h  -0x6a56, gp, r7      ; x = feedback input, |x| <= 12000 (guarded 0x28F50-58)
0x28F7C  ld.w  -0x3d30, gp, r26     ; s_old = state (32-bit)
0x28F86  ld.hu 0x73ea, tp, r16      ; b = 0xC63EA = 1560   (UNSIGNED load)
0x28F8A  ld.h  0x73e8, tp, r9       ; a = 0xC63E8 = 923    (SIGNED load)
0x28F8E  mul   r16, r7, r0          ; x * b
0x28F92  mul   r26, r9, r0          ; s_old * a
0x28F9A  sar   0xa, r7              ; (b*x) >> 10
0x28FA0  sar   0xa, r9              ; (a*s_old) >> 10
0x28FA2  add   r7, r9               ; r9 = s_new = ((923*s_old)>>10) + ((1560*x)>>10)
0x28FA4  add   r9, r26              ; r26 = s_old + s_new           <-- THE SUM, THE E-FORMER'S OPERAND
0x28FA8  st.w  r9, -0x3d30, gp      ; state := s_new (the increment, NOT the sum)
0x28FA6..0x28FBE                    ; symmetric clamp of r26 to +/- cal(0xC62E6)  [V282/V288: 46080; stock: 7680]
```

Integer mirror: `s_new = ((923*s) >> 10) + ((1560*x) >> 10); y = clamp(s + s_new, ±cal(0xC62E6)); s = s_new`.
DC gain = `2*1560/(1024-923) = 30.891` per raw count of `gp-0x6a56` — **not 0.99** (that figure belongs
to the *other* filter, the output lag; there is **no `>>5`** in this one). Both `mul` are 32×32 keeping
only the low half; both shifts are `sar` (floor toward −∞, a minor sign-asymmetric rounding, not a defect).
No overflow at any candidate pole tested (headroom ≥12.6×, TRACE-2026-09-06 §2.3-2.4).

**Cells** — confirmed by value this session's context and independently in TRACE-2026-09-06 §1.1:
`0xC63E8=923` (a), `0xC63EA=1560` (b), both byte-STOCK in V282/V288, never edited in ~280 builds.
**State cell**: `gp-0x3d30` (0xFEDF42D0), **2 accesses, both inside `FUN_00028ea6`** (`0x28F7C` ld.w,
`0x28FA8` st.w) — **PRIVATE**, no second writer anywhere (unlike the output-lag pair). **Clamp cell**:
`0xC62E6` (V282/V288 = 46080, stock = 7680), read 4× at `0x28FA6`-`0x28FBE`.

**Input operand `gp-0x6a56`, what it physically is** [EVIDENCE, `memory/accord/signals/accord-gp6a56-is-motor-rate-not-an-angle-sensor.md`,
cross-checked this session against the CAN-packer memory record, not independently re-disassembled]:
**it is SYNTHESIZED MOTOR RESOLVER RATE, not an independently-sensed column/wheel angle rate.** Sole
producer `FUN_0003f776`: `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)`,
where `gp-0x6abe` is the motor resolver's own electrical rate. It is what the EPS *transmits* as
`STEER_ANGLE_RATE` on CAN `0x14A[2:3]` (`(-gp-0x6a56)>>3`) and `0x18F[2:3]` (`-gp-0x6a56` directly,
10× finer) — opendbc's ground truth for that signal, but the firmware's own derivation is motor-side,
not an independent sensor.

**Is there ANY other consumer of this filter's state or output besides the E former?** Two separate
questions, both closed:
- **The filter's own STATE (`gp-0x3d30`) and OUTPUT (`r26`, a CPU register, never stored to memory)**:
  **NO other consumer.** State is private (2 accesses, both this filter, TRACE-2026-09-06 §1.4); `r26`
  is consumed exactly once, at `0x29D78` (`sub r26,r16` forming `E`), then dead. No telemetry, no
  interlock, no other lane reads either the state or the post-clamp `y` value.
- **The filter's INPUT (`gp-0x6a56`)** has *many* other consumers — this is the shared upstream signal,
  not the filter's own state. Documented consumers: `FUN_00034a72` (the base-assist boost/viscous lane,
  reads it unfiltered at `0x34AB8`/`0x34E8E`), the two CAN packers above, `gp-0x6a60` (a magnitude
  mirror, `min(abs(gp-0x6a56),65535)`), the driver-override plausibility guard (`reference_accord_driver_override_plausibility_eme.md`:
  a term is zeroed if `|gp-0x6a56| >= 12000`), and the gentle-EME re-arm rate gate (`gp-0x6a60 >= 1600`).
  **None of these reads the PID's filtered state or output — they all read the raw signal upstream of
  this filter**, so they are not a GATE-1 concern for editing `0xC63E8`/`0xC63EA` or the state cell, but
  they ARE a concern for anyone considering editing `gp-0x6a56` itself (out of scope here).

---

## Q2 — the "5.05 Hz output lag" (`0xC63EC=992`, `0xC63EE=507`)

**WHERE**: inside the LKAS rate loop itself, on the loop's OUTPUT, after the P/I/D sum and its clamp,
immediately before the term feeds the arbitration/gain stage. **It is squarely a loop-shaping lever on
the forward path**, not on the setpoint and not after the motor.

```
0x2A138..0x2A172   P/I/D sum, then clamped to +/- cal(0xC61BE)=15360 (the "sum clamp")
0x2A174  ld.hu 0x73ee, tp, r7     ; b = 0xC63EE = 507   (UNSIGNED)
0x2A178  ld.w  -0x3d3c, gp, r9    ; s = state (32-bit)
0x2A180  mul   r7, r12, r0        ; S (the clamped sum) * b
0x2A184  ld.h  0x73ec, tp, r7     ; a = 0xC63EC = 992   (SIGNED)
0x2A194  mul   r9, r7, r0         ; a * s
0x2A1A0  sar   0xa, r12 ; 0x2A1A6 sar 0xa, r7           ; both >>10
0x2A1A8  add   r12, r7            ; s_new
0x2A1AA  add   r7, r9             ; s_old + s_new
0x2A1AC  sar   0x5, r9            ; y = (s_old+s_new) >> 5   <-- goes on to the gain stage / gp-0x6b3x publishes
0x2A1B0  st.w  r7, -0x3d3c, gp    ; state := s_new
```

Integer mirror: `s_new = ((992*s)>>10) + ((507*S)>>10); y = (s + s_new) >> 5; s = s_new`, with `S` the
clamped P+I+D sum. **DC gain = 2×507/(1024−992)/32 = 0.9902.** At 20 Hz `|H| ≈ 0.242` (only 24% of DC
survives — this is a strong low-pass on the loop's own output, TRACE-2026-09-06 §2.3).

**What feeds it**: the clamped PID sum `S` (post `0xC61BE`=15360 sum clamp). **What it feeds**: `y`
publishes toward the loop's gain/clamp stage (`0xC6CD0` carrier gain, per this kit's existing lane
record) and ultimately `gp-0x6b38`/`gp-0x6b3c`, the delivered LKAS-lane torque. **It is inside the rate
loop, on the forward/output path** — moving this pole changes the loop's own open-loop phase and gain
at 20 Hz directly (2.45–2.80× magnitude swing from a 5→15 Hz move, TRACE-2026-09-06 §2.3-2.4), unlike
the setpoint-side filter the V288 spec built, which does not touch the return ratio at all.

**Reachability (GATE 1)**: **PASS**, independently re-proven in TRACE-2026-09-06 Addendum 3 — the second
reader pair (`0x2A892`/`0x2A8A2`) sits inside the duplicate compiled copy `[0x2A30E, 0x2B421)`, which a
7/7-controlled branch scan (with the `prepare`/`jr` Format-V collision trap caught and adjudicated) found
has **zero live entries**. Editing `0xC63EC`/`0xC63EE` moves exactly one filter, applied once per tick.

**Downstream frequency-selective risk**: Honda's oscillation-reversal detector `FUN_000428d4` watches
`gp-0x6c2c` (a *different* signal, derived from raw motor rotor position, upstream of this output-lag
filter and not downstream of it) — moving this pole to 15 Hz raises the loop's own 20–40 Hz content
2.45–2.80×, which is a genuine cost to price (TRACE-2026-09-06 §4.1, still open — needs a `gp-0x6c2c`
amplitude tap, not resolved this session either).

---

## Q3 — the D term, `ΔE`, the sentinel, and the clamp

**Where `ΔE` (dE) is formed** [EVIDENCE, `disassemble_bytes`, stock, TRACE-2026-09-06 §"D clamp,
disassembled"]:

```
0x29EE0  mov  r16, r8       ; r8 = E (current)
0x29EE2  sub  r27, r8       ; r8 = dE = E - E_prev        <-- dE FULLY FORMED HERE, register-only
0x29EE4  mul  r7, r8, r0    ; r8 = dE * Kd                (r7 = Kd LERP result, divq @0x29ED8)
0x29EE8  ld.hu 0x71b6, tp, r10  ; L = cal(0xC61B6) = 10240   [UNSIGNED]
0x29EEC  sar  0x3, r8       ; D = (dE * Kd) >> 3          <<< THE >>3, CONFIRMED
0x29EEE..0x29F08            ; symmetric clamp of D to +/- L, built as 0 - L via `subr r0` (NOT a
                             ;   separate negative-limit cell)
```

**dE itself is NEVER stored anywhere** — it lives only in register `r8` between `0x29EE2` and the
`mul` at `0x29EE4`, two instructions later. There is no cal, EMA, or window on it: it is a plain 1-tick
backward difference of the already-combined error `E`, so the setpoint's and feedback's shares of `dE`
cannot be separated or filtered independently without new code (TRACE-2026-09-06 Addendum 5b).

**Sentinel** [EVIDENCE, re-derived independently by `main` and cross-checked against a third emulator in
`ADVERSARIAL-V288-PREREG-2026-09-07.md`'s "B addendum"/"Sentinel path" entries, not re-disassembled fresh
this session — relayed as EVIDENCE from that closed adversarial pass, not BELIEF]: `gp-0x6cf8` is
Honda's own **first-tick-after-a-gap guard**, 32-bit, written every tick at `0x2A18C` — the current `E`
on the normally-engaged route, or the sentinel `0x7FFFFFFF` on the three disengage/skip routes (loaded
at `0x2A16C`/`0x2A0EA`, confirmed no intervening overwrite of `r16` before the `0x2A18C` store on any of
the three). It is read at `0x29E5E`, **after** the D-forming code above: `|prev| > 768000 ⇒ dE := 0`,
Honda's own "don't derivative-kick on the first tick back" guard. One live reader, one live writer, two
orphans inside the unreachable duplicate span — private-in-effect, same pattern as the lag poles.

**Clamp `0xC61B6` = 10240** [EVIDENCE, TRACE-2026-09-06 Addendum 4, re-confirmed against every
`build_v27x_tva.py` script this kit has — the kit's OWN records were already correct; a brief-level
mislabel (`0xC61BA` vs `0xC61B6`) was caught and closed, not a build defect]:
- **Symmetric about ±ONE cell** — no separate negative-limit cell; the negative bound is built as
  `0 - L` via `subr r0` at `0x29EFC`/`0x29F06`. All four loads (`0x29EE8`,`0x29EF2`,`0x29EF8`,`0x29F02`)
  are `ld.hu` (unsigned) — **no ld.h/ld.hu mismatch on this specific clamp**, so lowering it cannot ever
  install a wrong-sign limit (that latent defect exists on the T clamp `0xC61B4` and sum clamp `0xC61BE`
  instead, both of which load their positive clip with a SIGNED `ld.h` while everything else in the same
  clamp uses `ld.hu` — dormant at every shipped value, only arms if either cell is ever set ≥32768).
- **4 live readers**, all inside `FUN_00028ea6` (`0x29EE8`,`0x29EF2`,`0x29EF8`,`0x29F02`); 3 further
  readers exist only inside the proven-unreachable duplicate `[0x2A508,0x2B422)`. **No writers anywhere.**
- With the live flat Kd (`0xE511C`=128): `D = dE*128>>3 = dE*16`, rails at `|dE| = 640`.
- ⚠ **`0xC61BE` (the post-gain sum clamp, 15360), NOT D's own clamp, is the binding constraint on D**
  per the earlier V276 finding — P alone often already fills the sum clamp at low override index, so D
  is discarded downstream regardless of its own headroom. Any dose sized against `0xC61B6` should be
  checked against `0xC61BE`'s occupancy, or the result risks being an uninterpretable null.

**Where D joins P**: at the sum-clamp site `0x2A138`-`0x2A172` (`0xC61BE`=15360), immediately before the
output-lag filter (Q2) is applied to the clamped sum.

### Hook candidates, live registers, and what a cave may clobber

| # | site | length | what it replaces | registers LIVE across it (method) | safe scratch | what's already known about this exact site |
|---|---|---|---|---|---|---|
| (a) | `0x29EE4` (`mul r7,r8,r0`, forming `dE*Kd`) | 4 B, `jr`-length | the D multiply itself | `r7`=Kd LERP result (consumed only by this mul; must survive if replaying it), `r8`=dE (fresh from `0x29EE2`, must survive), **`lp` is LIVE from `0x29A2C` to `0x2A29A`** — this window fully contains `0x29EE4`, so **any `jarl` here corrupts a real Honda gate check firing every 1 kHz tick** (`memory/.../reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site.md`, independently re-derivable from `search_instructions operand_pattern:"lp"` inside `FUN_00028ea6`) | **`r10` only** — the very next instruction (`0x29EE8`) unconditionally overwrites it before any other read, a liveness claim read directly off the bytes, not inferred | Already the kit's own documented insertion site for a raw-`dE` tap or a D-side filter; **`jr` only, never `jarl`**, and the subroutine must replay `mul r7,r8,r0` before jumping back to `0x29EE8`, since downstream needs the real `D` |
| (b) | on `r26` between `0x28FA4` (feedback sum formed) and `0x29D78` (E formed) | — | no single 4-byte instruction sits here doing nothing else — `r26` is consumed almost immediately by the clamp (`0x28FA6`+) then by the `sub` at `0x29D78`; a hook here would need to sit AFTER the clamp (i.e. effectively at/after `0x28FBE`) rather than truly "on r26" pre-clamp | `r26` itself is the value to filter (must be read, new value substituted before `0x29D78`); the clamp code between `0x28FA4` and `0x28FBE` reads/writes `r26`,`r6`,`r12` per TRACE-2026-09-06 §2.1 — not independently re-traced instruction-by-instruction this session for scratch availability | **not established this session** — flagged as the exact next step below | This is the loopshape-relevant hook for a feedback-side filter/notch; unlike (a), I have NOT this session re-derived a clean same-length swap point or a proven-dead scratch register for it — do not treat it as ready the way (a) and the Q2 output-lag pole are |

**Honest gap, stated plainly**: candidate (a) is fully specified (site, length, liveness, scratch,
`jr`-only constraint) because it is this kit's own pre-existing documented insertion site. Candidate (b)
— a hook truly "on r26" for a feedback-side filter/notch, as opposed to editing the existing feedback
EMA's cal cells — has **not** been reduced to a concrete same-length-swap address with proven-dead
scratch this session. **Exact next step**: `disassemble_bytes dry_run:true` over `0x28FA4`-`0x28FBE`
(the clamp block) to find a swappable instruction and prove a dead register across it, the same method
used for `0x29EE4`.

---

## Q4 — RAM census: free cells near `gp-0x6a32` for a biquad's state

**Method** [EVIDENCE, `search_instructions` this session, whole-program scope, cross-checked by manual
opcode-field decode of 5 known instructions against Ghidra's own resolved output to confirm the tool is
not lying about these operands — see appendix]: swept every halfword-aligned displacement from
`gp-0x6a1a` to `gp-0x6a5e` (23 candidates spanning the immediate ±0x30-byte neighbourhood of the V288
state cell `gp-0x6a32`), using `operand_pattern` matching on the literal hex displacement (this matches
AFTER Ghidra's own SLEIGH decode, so it is immune to the hand-rolled-opcode-table traps this skill warns
about — its residual risks are Ghidra's own decode correctness, already-analysed-code coverage, and
register-indirect access, all addressed below).

**RESULT: this neighbourhood is almost completely saturated with live, multi-function shared state.**
Of 23 candidates swept, **21 are occupied** by real gp-relative `ld.h`/`ld.hu`/`st.h` accesses (not
false positives — confirmed `gp` as the base register in Ghidra's own operand text for every one, e.g.
`gp-0x6a34` has 3 live readers/writers across `FUN_00028ea6` and its orphan `FUN_0002a93a`; `gp-0x6a38`
and `gp-0x6a3a` are shared scratch touched by 6+ unrelated functions including `FUN_000534da`). This is
a genuinely useful **negative** finding: **do not assume the cell immediately next to a known-free slot
is also free** — `gp-0x6a32` was free precisely because it is an isolated dead publish, not because its
neighbourhood is empty.

**Candidates found, with evidence for each:**

| cell | address | width | evidence | residual |
|---|---|---|---|---|
| `gp-0x6a2a` | 0xFEDF15D6 | halfword | **ZERO gp-relative hits** in a whole-program `operand_pattern` sweep; the one raw text hit (`0x66a2a`) is a branch-target digit coincidence, base is a code address not `gp` (the documented false-positive class). No `movea -0x6a2a,gp,...` anywhere (checked explicitly). | Register-indirect access via a `movea` of a *different* nearby displacement (e.g. `-0x6a20`, `-0x6a1c`, which DO have `movea` bases) walking forward to reach `0x6a2a` was not excluded — no evidence found for it, but not proven impossible. Also not checked: whether this address falls inside a crt0 block-copy/clear range (would be benign — guarantees 0 at boot — not disqualifying). |
| `gp-0x683c` | 0xFEDF17C4 | byte (1 B) | **Re-confirmed this session.** In STOCK, `0x3AA94 ld.bu -0x683c,gp,r15` is real — but this is the exact V104 rate-lane gate byte the V282/V288 build repoints (byte `0x3AA96`: `0xC5`→`0xFB`, converting the displacement to `-0x6806`); TRACE-2026-09-06 Addendum 2 §3 confirms this repoint is present at the byte level in V282/V288. **In the built image this session cares about, `gp-0x683c` has zero references of any kind** (independently documented pre-existing, `reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site.md`; today's stock-side hit corroborates rather than contradicts this — it is exactly the dead-in-V288 stock instruction the repoint replaces). | Only 1 byte — insufficient alone for a 16- or 32-bit filter state; useful only as a 1-bit/2-bit auxiliary (e.g. a sign/saturating counter), as that memory already concluded. |
| `gp-0x6994` | 0xFEDF166C | halfword | **1 writer image-wide** (`0x42A86`, Honda's oscillation-detector cut-factor diagnostic mirror), **ZERO gp-relative readers** (TRACE-2026-09-06 Addendum 2 §1, corroborated three ways: no absolute dword pointer into the range, no `mov imm32` RAM base equal to it, empty reader list). | **Not clean** — flagged HONESTLY by the source trace itself: 324 `mov imm32` sites carry a RAM base below this address whose copy lengths were never bounded, so a block copy reaching this cell is not excluded. **Reusing this cell means accepting that documented residual**, not a fresh one. |

**A 4th fully-clean cell was NOT found this session.** I extended the sweep to `gp-0x6a1a`–`gp-0x6a5e`
(23 candidates) plus 4 more probes in the adjacent filter-state bank (`gp-0x3d28/2c/38/40`, all occupied
by `FUN_00028ea6`/`FUN_0002b422`/`FUN_00023d24`'s own byte-granular state) and found only the one clean
halfword above. **This is a real, evidenced negative, not a gap in effort**: the RAM directly surrounding
the LKAS PID's working state is densely packed and shared across many unrelated functions (the linker
appears to pool statics from many translation units into one contiguous gp-relative block, not
per-function-private regions). **A biquad's full 4×32-bit state (8 halfwords, or 4 words) cannot be
assembled from isolated free cells found by this method in this neighbourhood.**

**Exact next step, if a biquad's full state is still wanted**: a systematic Python full-image
occupancy map (every gp-relative displacement 0x0000–0x7FFF, both 4-byte and 6-byte extended forms,
built from the byte-verified opcode table in the appendix below) would find every gap in ONE pass rather
than ~30 one-at-a-time queries, and could search a wider radius or a different bank (e.g. near the
already-known-quiet `gp-0x6994`/`gp-0x683c` neighbourhoods rather than `gp-0x6a32`'s). Not run this
session — flagging as the correctly-scoped next step rather than continuing the expensive manual sweep.

### Appendix — the gp/tp-relative disp16 opcode table, byte-verified this session

Cross-checked against 5 known instructions' raw bytes (not merely inherited) to confirm Ghidra's
`search_instructions` operand text is trustworthy for this census:

| mnemonic | opcode field `(hw1>>5)&0x3F` | hw2 rule | verified against |
|---|---|---|---|
| `ld.h` | `0x39` | `hw2` = true disp (LSB=0, even) | `0x28F8A` (`254fe873`) |
| `ld.w` | `0x39` (same field as `ld.h`; LSB of `hw2` is the width flag) | `hw2` = true disp with LSB forced to 1 | `0x2A178` (`244fc5c2`) |
| `st.h` | `0x3B` | `hw2` = true disp (LSB=0, even) | `0x29D72` (`6487ce95`) |
| `st.w` | `0x3B` (same field as `st.h`; LSB of `hw2` is the width flag) | `hw2` = true disp with LSB forced to 1 | `0x2A1B0` (`643fc5c2`) |
| `ld.hu` | `0x3F` | `hw2` = true disp with LSB forced to 1 (fixed, not a width flag here — V850 has no `ld.wu`) | `0x28F86` (`e587eb73`) |
| `ld.bu` (even target) | `0x3C` | not fully re-derived this session (see below) | `0x3AA70` (`8467e798`) |

`reg1 = hw1 & 0x1F` (4=gp, 5=tp); `reg2 = (hw1>>11)&0x1F`. This is a **narrower, independently
byte-verified subset** of the table the `firmware-decompile` skill and prior sessions describe — I did
**not** re-derive the `ld.bu`/`st.b` displacement-recovery formula this session (my one attempt at it,
checking `0x3AA70`, produced numbers inconsistent with a simple `(hw2<<1)|opcode_bit0` model and I did
not chase it further, since it was not load-bearing for the ld.h/ld.hu/ld.w/st.h/st.w census above,
which covers every width a biquad state cell would plausibly use). **Byte-level neighbours of every
"free" cell above are therefore an honest residual**, exactly as the V288 spec treated its own two
byte-adjacent candidates — not certified clean.

---

## Q5 — free flash after the V288 rev 2 cave

**[EVIDENCE, fresh Python read this session, V288 rev 2 image, region `[0xC4C30, 0xC4FFC)`]**:

```
region length: 972 bytes
non-0xFF bytes: exactly 12, at 0xC4FF0-0xC4FFB: 01 01 01 01 00 00 C6 00 13 00 B2 00
  (identical to the pre-existing 12-byte unidentified structure the V288 spec already found and left untouched)
0xC4FFC-0xC4FFF: CRC trailer = f0 07 c2 4a  (matches the adversarial pass's computed 0x4AC207F0)
```

**Confirmed: 960 contiguous bytes of `0xFF`, unreferenced, from `0xC4C30` to `0xC4FEF`**, after V288 rev
2's own filter cave + telemetry rung (which occupy `0xC4BD8`–`0xC4C2F`, read directly this session and
matching the adversarial pass's documented byte ranges). This is free flash **remaining after** the
currently-candidate V288 rev 2 build, available for a Q3-style D-hook or Q2-style pole-move subroutine
without touching the CRC block boundary (`[0x13000, 0xC4FFC)`, unchanged).

---

## Q6 — the 1 kHz task budget

**No new evidence found this session** — re-confirming rather than extending TRACE-2026-09-06 §"TASK 3":
the task descriptor at `0xBB920` is a 48-byte RTOS TCB record (stack pointer, priority/attribute word,
entry point) carrying **no period field**; the static OSTM0 timer derivation is refuted in this kit's
own record (PCLK is 40 MHz, not 80 MHz, so the 79999-count reload implies 500 Hz, not 1000); the sole
surviving evidence for the 1 kHz rate is a **behavioural** one — the `0xC64DF`=100 STEER_STATUS debounce
cal produced a measured 100.00 ms dwell on the CAN bus, giving 1 tick = 1.000 ms. **I did not search for
a watchdog or overrun counter this session** (not requested as a priority item and the existing "no
period field, no static timer proof" finding already answers the bounded version of this question) —
if the operator wants the absolute period nailed down statically rather than behaviourally, the exact
next step (unchanged from the prior trace) is reading the OSTM0/TAUA compare register and prescaler
against the CKSC/PLL init and the `UPD70F3508_V850E2Px4.svd`.

---

---

## ADDENDUM — `loopshape`'s four follow-up questions (Q0, Q7-Q9)

**Method**: `decompile_function` on `FUN_00028ea6` (stock) this time — the function's dispatch structure
is dense enough (1874 instructions, many overlapping register-reuse windows) that hand-tracing registers
purely from disassembly risks exactly the mistake this kit's own record already flagged twice for this
function (`reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation.md`: "Ghidra's decompile
reuses r9/r27 across the P/D blocks and misreads easily"; TRACE-2026-09-06 Addendum 6 caught itself doing
this with `r22`). **I made exactly that mistake once this session too** (see Q7) and caught it by
decompiling rather than trusting my own raw-disassembly read — recorded below, not hidden.

### Q0 — the multiply at `0x2A1E6` (`mul r14,r9,r0 ; sar 0xf ; sxh`)

**SETTLED: `r9` = the OUTPUT-LAG FILTER'S result `y`; `r14` = `gp-0x69b0`, the ENGAGEMENT RAMP. NEITHER
prior reading was fully right; the tracer-memory reading is closer.**

Decompile (`FUN_00028ea6`, lines 1224-1245) shows this unambiguously:

```c
iVar23 = ((int)sVar27 * *(int*)(gp-0x3d3c) >> 10) + ((int)(iVar23*(uint)uVar25) >> 10);  // s_new
iVar31 = *(int*)(gp-0x3d3c) + iVar23;   // s_old + s_new
iVar34 = iVar31 >> 5;                    // y  <-- THIS IS r9 downstream (the output-lag filter's y)
*(int*)(gp-0x3d3c) = iVar23;             // state := s_new
if ((cVar15=='\x01') && (gp-0x6806=='\0')) {         // DISENGAGED-ONLY branch (cal flag AND !engaged)
    ... (a deadband/sign test on y, using gp-0x6b30) ...
    if (<deadband/sign condition>) { iVar23 = 0; goto LAB_0002a1ee; }
}
iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf);   // <-- 0x2A1E6: y * ramp, >>15, sign-extended
LAB_0002a1ee:
... iVar23 feeds the T = gp-0x6b38 chain (§ existing memory accord-gp6b38-is-the-delivered-lane-torque) ...
```

`uVar18` here is the SAME variable repeatedly reloaded from `gp-0x69b0` throughout the function's long
engagement-ramp state-machine (confirmed: `search_instructions operand_pattern:"69b0" function:FUN_00028ea6`
returns 41 hits, all `ld.hu`/`st.h` on that exact cell, spanning `0x2936A`-`0x29714` — the ramp is
computed/held across dozens of dispatch branches before this point). `iVar34`/`r9` is confirmed to be `y`
by direct instruction correspondence: `0x2A1AC sar 0x5,r9` (the filter's own final shift) is the LAST
write to `r9` before `0x2A1E6` on the ENGAGED path (the deadband branch is disengaged-only and, when it
fires, explicitly sets `r9`→`iVar23`=0 and **branches around** `0x2A1E6` entirely — confirmed by the raw
asm: `0x2A1E2 mov 0x0,r9 ; 0x2A1E4 br 0x2A1EE`, skipping the multiply).

**This means the rectified/quantized `|floor32(fb)|` value from `0x28FC0`-`0x28FC6` (which I initially
suspected, see Q7 below) is NOT an input to this multiply at all** — it is a completely separate,
earlier computation with its own consumer (Q7). **The V287 design doc's `|q32(H_fb·rate)|` reading for
this site is WRONG** — it conflated the two. The five tracer memories calling `r14`/this site "the
ramp" are RIGHT about `r14`, but the full picture is `y × ramp`, not the ramp alone or the ramp times a
raw feedback magnitude. **Decision-bearing consequence for `loopshape`**: moving the output-lag pole
(`0xC63EC`/`0xC63EE`) changes `y` directly, which changes what the ramp scales here — the output-lag
pole and this "carrier"-adjacent multiply are NOT independent, on the engaged path.

### Q7 — what consumes `r16` after the `bp`/`subr r0,r16` rectification at `0x28FC4`?

**CORRECTED FROM MY OWN FIRST READ.** My first pass (from raw disassembly alone, before decompiling)
guessed the immediately-following per-variant knot-walk (base table `0xCB844`, selector `gp-0x674e`)
consumed this value as its walk key. **That is wrong** — decompile line 61/64 shows the walk key
(`uVar20`) is `*(ushort*)(gp-0x6a5e)` (a **vehicle-speed-class cell**, independently loaded much earlier
in the function at `0x28F0E`, long before the feedback filter runs), not our rectified `|fb|`. I caught
this myself by decompiling rather than asserting the raw-disassembly guess.

**The actual, single consumer** [EVIDENCE, decompile line 170 + a targeted `search_instructions`
confirming exactly 2 accesses to `gp-0x6a34` in this function]:

```c
*(short *)(gp-0x6a34) = (short)(uVar18 >> 5);     // 0x290C6 shr 0x5,r9 ; 0x290CA st.h r9,-0x6a34,gp
```

i.e. the rectified value is shifted right 5 more bits and **published to `gp-0x6a34`**. This cell has
**exactly one other live reader** in `FUN_00028ea6` (decompile line 764), gated behind `gp-0x680a==1` (a
narrow mode/lane, previously identified in the V288 adversarial pass as "the third skip, `gp-0x680a`
lane, `0x2A0C6`" — I have not re-derived what selects this lane beyond that prior identification):

```c
if (((uVar18 != 0) || (cVar15=='\x01')) && bVar3) {
  if (gp-0x680a == 1) {
    uVar20 = gp-0x6a34;                                  // reload
    sVar27 = LERP(uVar20, table at tp+0x7714/0x7720/0x7722/0x7730);   // a THIRD, different table
    uVar20 = -sign(uVar35) * sVar27;   // uVar35 = the ORIGINAL SIGNED clamped fb sum, pre-rectification
  } else { /* a different branch entirely, using gp-0x682f — the driver-override taper, unrelated */ }
}
```

**Answer to Q7's actual question**: it is neither a pure LERP index feeding the general torque path nor
diagnostics-only — it is a genuine, feedback-magnitude-dependent table lookup whose result is re-signed
by the feedback's own direction (`-sign(fb)·LERP(|fb|)`), but **this whole computation is GATED to the
narrow `gp-0x680a==1` lane**, not the everyday engaged path. I have not traced where this signed term
ultimately lands (it feeds `uVar20`/`iVar31` locally in that branch; tracing it to a final gp-cell would
need another decompile pass I did not run this session — flagged as the exact next step if this lane
becomes decision-bearing). **The orphan reader in `FUN_0002a93a` (the proven-unreachable duplicate) does
not count**, per this kit's standing GATE-1 finding for that whole block.

### Q8 — a feedback-operand (`r26`) filter hook, `0x28FBC`-`0x29D78`

**`r26` is a CALLEE-SAVED register** (`prepare {...,r26,...}` at the function's own entry `0x28EA6`;
`dispose ...,{...,r26,...},lp` at `0x2A30A`) — confirmed by `search_instructions function:FUN_00028ea6
operand_pattern:"r26"`, which returns exactly 18 hits total for the WHOLE function. This is why it can
carry the clamped feedback sum untouched across such a long span: **`r26` is written once per tick**
(the clamp resolution ending at one of `0x28FAE`/`0x28FB8`-`0x28FBC`, or zeroed to 0 at `0x290B6` on the
input-guard-failure bail path) **and not touched again until `0x29D78` (`sub r26,r16`, the E-former)**.
No intermediate read or write of `r26` exists in that whole window — confirmed by the same
whole-function `r26` search (every hit between those two addresses is accounted for above).

**On `lp`-liveness as a constraint**: `lp` is live from an EARLIER reuse instance too (`0x28EBC ld.hu →
lp`, consumed at `0x290D2`, per existing kit memory) — this window CONTAINS `0x28FBE`-`0x28FC0`, the
r26-clamp convergence point. **This does not block a `jr`-based hook** — `jr` never writes `lp` (unlike
`jarl`), so the established "same-length swap, `jr` not `jarl`" technique is safe regardless of which
`lp`-reuse window a hook site falls inside. The binding constraint is `jarl` specifically, not `lp`
liveness per se.

**A concrete same-length site between the clamp and `0x29D78`**: the three clamp branches
(`0x28FAE mov r14,r26`+`br`; `0x28FB2`-`0x28FB6`; `0x28FB8`-`0x28FBC`) all converge at `0x28FBE mov
r26,r16` (2 bytes) immediately followed by `0x28FC0 sar 0x5,r16` (2 bytes) — together a swappable 4-byte
window. **This is NOT a clean single-purpose slot**: those two instructions start the Q7 rectification
sequence, so a cave replacing them must replicate `r16 := r26` and `r16 >>= 5` (using either the raw or
the filtered `r26`, a DESIGN choice, not a tracing fact) before `jr`-ing back to `0x28FC2`. Registers
`r13`, `r14`, `r9` are all dead at this exact point (last used inside the clamp resolution itself, freshly
reloaded before their next real use later in the function) — confirmed by the same instruction listing
already in this trace's Q1/Q2 sections, not re-derived separately. **I did not find a cleaner, single-
purpose 4-byte slot operating on `r26` alone** — every instruction that touches `r26` is part of either
the clamp or the final subtract, both of which are live logic, not dead code.

**The V288-cave-chaining alternative — cleaner, and fully confirmed**: at the V288 cave's entry (reached
via the `jr` at `0x29D72`, replacing the dead `sp`-publish store), **`r26` is live (holds `fb`, per the
V288 spec's own liveness table) and is NOT read or written by anything between `0x29D72` and `0x29D78`
in the current code** (confirmed by the same whole-function `r26` search above — the only hit in that
range is the final `0x29D78` consumer). **YES — `r26` is writable there with zero risk of an intermediate
consumer seeing a stale or partially-filtered value**, because there is no intermediate consumer at all.
This is a strictly better hook site than Q8's first candidate: one hook (already built, at `0x29D72`)
could be extended to filter both `sp` (as V288 already does) and `fb` (a new addition) in the same
subroutine, before resuming at `0x29D76`, with no new insertion point needed in the function body itself.

### Q9 — the D-path filter at `0x29EE4`: is `dE` the full error, and is there free 32-bit RAM there?

**CONFIRMED: `dE` (`r8` at `0x29EE2`) is the FULL combined error `E = 32·sp − fb`, not the setpoint part
alone.** `E` is formed once, at `0x29D78` (`r16 := 32·sp − r26`, both halves already summed), copied to
`r8` at `0x29EE0` (`mov r16,r8`), then differenced against the previous tick's `E` (`r27`, per this
kit's existing record) at `0x29EE2` (`sub r27,r8`). There is no point downstream of `0x29D78` where the
setpoint and feedback contributions to `E` exist as separate values — this re-confirms, rather than
newly discovers, Addendum 5(b) of the 2026-09-06 source trace ("the setpoint and feedback halves of dE
CANNOT be scaled separately, structurally").

**Free 32-bit RAM near this site: NONE FOUND, honestly.** This is the same negative result as this
trace's own Q4 census, restated for the specific ask: a biquad-class filter needs at minimum two
32-bit-aligned words (four preferred); the RAM census above found exactly one clean free cell
(`gp-0x6a2a`, a single halfword) and confirmed it is **isolated** — both its neighbours at halfword
spacing (`gp-0x6a28`, `gp-0x6a2c`) are occupied, so it cannot be paired into a 32-bit word. I additionally
checked the neighbours of the other free-but-residual candidate, `gp-0x6994`: **`gp-0x6992` and
`gp-0x6996` are both occupied** too (by `FUN_0002eb42`/`FUN_00032a2a`/`FUN_00032ffe` and
`FUN_0003b338`/`FUN_0003b416` respectively), so that cell is also isolated. **A D-path biquad cannot be
built from any free RAM found in this kit's census so far** — this is the same "wider systematic scan
needed" conclusion as Q4, now confirmed to hold specifically for a site near `0x29EE4` too, not just near
`gp-0x6a32`.

---

## Summary for `main` / `loopshape`

1. **Feedback filter**: `gp-0x3d30` state, PRIVATE (2 accesses, 1 function), input `gp-0x6a56` is
   synthesized motor-resolver rate (many OTHER consumers of the raw signal, but zero other consumers of
   this filter's own state/output). DC 30.89, no `>>5`.
2. **Output-lag pole (`0xC63EC`/`0xC63EE`)**: on the loop's own forward output, post-sum-clamp,
   pre-gain-stage — a real loop-shaping lever, GATE-1 clean (duplicate copy proven unreachable).
3. **D term**: `dE` register-only at `0x29EE2`, `×Kd>>3` at `0x29EE4`/`0x29EEC`, symmetric clamp
   `0xC61B6`=10240 (four `ld.hu`, no sign-mismatch risk), binding constraint is actually the downstream
   sum clamp `0xC61BE`. Hook candidate (a) at `0x29EE4` is fully specified (scratch `r10`, `jr`-only,
   `lp` is live and jarl-unsafe in this whole window). Hook candidate (b), a true pre-clamp tap on the
   feedback sum `r26`, is **not** reduced to a concrete site this session — flagged as the next step.
4. **RAM**: the immediate neighbourhood of `gp-0x6a32` is densely occupied; only `gp-0x6a2a` (clean
   halfword), `gp-0x683c` (clean byte, dead-in-V288), and `gp-0x6994` (1 writer/0 readers but a
   documented register-indirect residual) were found free. **A 4th clean cell was not found** — a
   biquad's full state needs a wider systematic scan, not more one-at-a-time queries.
5. **Free flash**: 960 bytes confirmed `0xFF` from `0xC4C30`–`0xC4FEF`, after V288 rev 2's own cave.
6. **Task budget**: unresolved statically, as before; 1 kHz rests on the CAN dwell measurement alone.
0. **`0x2A1E6` multiply** (Q0): `r9`=`y` (the output-lag filter's own result), `r14`=`gp-0x69b0` (the
   engagement ramp). Corrects V287's `|q32(H_fb·rate)|` reading; confirms the ramp reading but shows it's
   `y × ramp`, not the ramp alone — the output-lag pole and this site are coupled.
7. **`gp-0x6a34` publish** (Q7): the rectified `|fb|` feeds a SECOND per-variant LERP (not the
   speed-indexed one I first guessed), producing a signed term, gated to a narrow `gp-0x680a==1` lane —
   not diagnostics, not the general torque path. My first raw-disassembly read was wrong; corrected by
   decompiling.
8. **`r26` hook** (Q8): `r26` is callee-saved, dormant from the clamp (`~0x28FBE`) to the E-former
   (`0x29D78`) with zero intermediate readers. The V288 cave's own entry (`0xC4C00`) is the cleanest hook
   — `r26` is live there with nothing downstream reading the unfiltered value before `0x29D78`.
9. **D-path RAM** (Q9): `dE` is confirmed the FULL combined error, not a setpoint-only component. No
   free 32-bit-aligned RAM was found near `0x29EE4` either — `gp-0x6a2a` and `gp-0x6994` are both
   isolated (their neighbours are occupied), so a D-path biquad can't be built from cells found so far.

---

## FINAL ADDENDUM — raw Python re-census (the CLAUDE.md-mandated second method) and the systematic scan

**Why this exists**: `main` asked for the Q4 census to be re-done with a raw little-endian Python scan
rather than resting on `search_instructions`, because an undercount in the "free cell" direction is the
dangerous one (`gp-0x1500` passed both static methods and still failed on-car). This addendum does that,
and along the way surfaces and resolves a real scare I raised against my own work — recorded in full,
not smoothed over.

### 1. The opcode table, byte-verified this session (narrower than a full ISA table, honestly bounded)

**[EVIDENCE — every entry cross-checked against a real instruction's bytes via `disassemble_bytes`,
matched against Ghidra's own resolved mnemonic/operands]**. Format: 4-byte gp/tp-relative disp16 —
`reg1 = hw1 & 0x1F` (gp=4, tp=5), `reg2 = (hw1>>11)&0x1F`, `opcode6 = (hw1>>5)&0x3F`.

| opcode6 | hw2 rule | mnemonic | verified against |
|---|---|---|---|
| `0x39` | `hw2` LSB=0 → true disp even | `ld.h` | `0x28F8A` (`254fe873`) |
| `0x39` | `hw2` LSB=1 → true disp odd, `disp=hw2&0xFFFE` | `ld.w` | `0x2A178` (`244fc5c2`) |
| `0x3B` | `hw2` LSB=0 | `st.h` | `0x29D72` (`6487ce95`) |
| `0x3B` | `hw2` LSB=1, `disp=hw2&0xFFFE` | `st.w` | `0x2A1B0` (`643fc5c2`) |
| `0x3F` | `hw2` LSB fixed 1, `disp=hw2&0xFFFE` | `ld.hu` | `0x28F86` (`e587eb73`) |
| `0x3C` | `disp=hw2&0xFFFE` (even target) | `ld.bu` | `0x671a` (`8467e798`), `0x683c` (`847fc597`) — 2 examples |
| `0x3D` | `disp=(hw2&0xFFFE)\|1` (odd target) | `ld.bu` | `tp+0x74f1` (`a587f174`) — confirms the parity-split theory against its EVEN sibling at the SAME base address (`tp+0x74f0`, `8587f174`, `hw2` identical `0x74F1` in both — the opcode LSB alone carries true parity) |
| 6-byte extended, `reg2`(hw1 bits11-15)`==0`, `op6∈{0x3C,0x3D}` | `disp = sign_extend23((hw3<<7)\|((hw2>>4)&0x7F))` | mixed widths | `ld.h -0x4f60,gp,r6` = `84 07 07 32 61 ff` (from existing kit memory `reference_accord_fun28ea6_lkas_rate_pid_full_decode.md`, independently re-verified this session: decoded disp = **exactly** `-0x4f60`) |

**🛑 Honest, stated gap: `st.b`/`ld.b` (signed byte) 4-byte forms are NOT resolved.** My one confirmed
`st.b` example (`-0x357c,gp,r0` = `440784ca`) decodes to `opcode6=0x3A`. If `st.b` follows the same
parity-split pattern as `ld.bu`, its odd-target sibling would be `opcode6=0x3B` — **numerically
identical to `st.h`/`st.w`'s shared opcode**, which cannot be right without a further discriminator I
have not found. **I did NOT invent a formula to paper over this.** My scanner below does **not** decode
`st.b`/`ld.b`/bit-ops(`set1`/`clr1`/`tst1`/`not1`) at all — this is a real residual on every result
below, exactly the class of gap this kit's own doctrine says to state rather than hide. Mitigant: bit-ops
in this image use a `movhi`-derived base (`r18=0xFEDF0000`), not `gp` directly (confirmed for the one
example found, `0x020772` etc.) — a genuine `gp`-based bit-op was not found, but I did not exhaustively
search for one either.

### 2. Positive controls, and one that correctly caught a control error of mine

**[EVIDENCE, `gp_census.py`, this session, V288 rev 2 image, region `[0x13000,0x100000)`]**

```
gp-0x3d3c (output-lag state): 4/4 hits  -- 0x2A178 ld.w, 0x2A1B0 st.w, 0x2A89A ld.w, 0x2A8BA st.w  PASS
gp-0x6a32 (V288 state):        5 hits   -- 0x2AC68 st.h (orphan) + 4 inside the V288 cave itself
                                            (0xC4BDE/0xC4C0E/0xC4C24/0xC4C28)                        PASS
```

**One control I ran WAS wrong, and I am recording the error rather than the corrected number alone**:
I first controlled against `0xC646C` expecting 5 hits and got **0**. That is not a scanner bug — `0xC646C`
is `tp+0x746c` (**`reg1=5`, tp-relative**), and my scanner (correctly, for this task) only decodes
`reg1==4` (gp). Using a tp-relative cell as a positive control for a gp-only scanner was my mistake, not
a finding. The two REAL gp-relative controls above both pass, and are what the candidate results below
actually rest on.

### 3. Candidates re-confirmed by the raw scan — independent of `search_instructions`

| cell | raw-scan hits | verdict |
|---|---|---|
| `gp-0x6a2a` | **0** | **RE-CONFIRMED FREE**, second independent method |
| `gp-0x683c` | **0** | **RE-CONFIRMED FREE**, second independent method |
| `gp-0x6994` | **1** (`0x42A86 st.h reg2=r7`) | matches the known single writer, no readers |
| `gp-0x6992`/`gp-0x6996` (6994's neighbours) | 3 / 2 | occupied, confirms isolation |
| `gp-0x6a28`/`gp-0x6a2c` (6a2a's neighbours) | 5 / 1 | occupied, confirms isolation |

### 4. 🛑 A scare I raised against my own work, and how it was resolved — not glossed over

Running the systematic full-range scan (§5) turned up hundreds of large "free" runs at large negative
displacements. Before reporting them, I checked whether they could be **stack**, using a stray TCB field
from the OLDER `TRACE-2026-09-06` trace that labelled `0xBB920+0x00 = 0xFEDF70C8` "stack pointer" and
`+0xC = 0xFEDEC000` "stack base" — those two values bracket **`gp-0x86E4`..`gp-0xF38`**, which would have
swallowed `gp-0x6a32` itself (a cell this whole kit already relies on) and made most of my free-run
results suspect.

**Resolved by an EXISTING, more authoritative memory this kit already has**
(`reference_accord_app_ram_layout_and_boot_init_loops.md`, from a direct disassembly of the app's own
entry/init code at `0x140A8`-`0x147F6`), which the TCB-derived guess should have deferred to:

- **The real stack is `0xFEDEC000..0xFEDEF91C`** (`sp=0xFEDEF91C` at entry, painted with the
  `0xEBEBEBEB` canary down to `0xFEDEC000`, confirmed by disassembly of the boot canary-paint loop) —
  in gp terms, **`gp-0xC000..gp-0x86E4`**. My ENTIRE scanned range (`gp-0x7FF2..gp-0x4`) sits **above**
  `gp-0x86E4` (i.e. at smaller-magnitude, less-negative displacements) — **completely outside stack
  reach.** The `0xFEDF70C8` value in the older trace was either a different field or a mislabel; I did
  not re-derive what it actually is, since it doesn't matter once the boot-code-derived stack bound is
  in hand. **Flagging that older trace's TCB label as suspect for whoever owns it, not correcting it
  myself.**
- **`.data` occupies `gp-0x6E50..gp-0x2598`** (flash `0x86260..0x8AB18` copied to RAM `0xFEDF11B0..0xFEDF5A68`
  at boot); everything else in the 80 KB window `0xFEDEC000..0xFEDFFFFF` (`gp-0xC000..gp+0x1FFF`) boots
  to zero (bss). **Both `gp-0x6a2a` and `gp-0x683c` fall inside the `.data` band**, so their absence of
  runtime writers does NOT mean "boots to garbage" — their boot value is a specific, computable flash
  byte, not zero automatically. Computed this session:

```
gp-0x6a2a boot value = 0x0000 (0)      -- flash[0x86260 + (0xFEDF15D6-0xFEDF11B0)] = flash[0x86686]
gp-0x683c boot value = 0x0100 (256)    -- flash[0x86260 + (0xFEDF17C4-0xFEDF11B0)] = flash[0x86874]
gp-0x6994 boot value = 0x0064 (100)    -- flash[0x86260 + (0xFEDF166C-0xFEDF11B0)] = flash[0x8671C]
```

`gp-0x6a2a` boots CLEAN (0). `gp-0x683c` boots to 256 — its low byte (0) is consistent with the
pre-repoint `ld.bu` read of it as a byte, which would see 0; a NEW halfword use of this cell must
account for the nonzero high byte at boot (an init write, or design around it) since nothing re-zeroes
it after boot. **A build-script detail, not a tracing blocker** — the same class of "choose the boot
value by editing the flash source byte" lever the RAM-layout memory itself documents.

### 5. The systematic full-image scan, and its honest limits

**[EVIDENCE for the raw hit-counts; BELIEF/UNRESOLVED for "therefore safe to use," stated explicitly]**
Scanned every halfword-aligned gp-relative displacement from `-0x7FF2` to `-0x4` (the full range any
4-byte disp16 form in this image actually reaches) for occupancy under the validated forms in §1 (`st.b`/
`ld.b`/bit-ops excluded, per the stated gap). Found **273 maximal runs of ≥2 contiguous free 32-bit-
aligned words**, ranging from 2 words (8 bytes) to 418 words (1672 bytes, at `gp-0x74f8..gp-0x6e72`,
just outside the `.data` band's upper edge). Two representative candidates near the LKAS PID's own
working set, individually verified with the SAME residual check already used for `gp-0x6a2a`/`gp-0x683c`
(a `search_instructions` sweep of every displacement in the run PLUS a `movea`-with-that-displacement
check, both zero):

```
gp-0x6ab0 .. gp-0x6aaa   2 words (8 bytes), zero hits of any kind, zero movea materialisations
gp-0x68b0 .. gp-0x68aa   2 words (8 bytes), same
```

**What I did NOT do, stated plainly**: I did not individually re-verify all 273 runs with the
`movea`/register-indirect check — that would be 273+ more tool calls. **The two runs above, plus
`gp-0x6a2a`/`gp-0x683c`, are the only ones I certify to the same standard as this kit's existing
`gp-0x6a32`/`gp-0x683c` precedents.** The other 271 runs (including the large `.data`/bss-boundary ones)
are a **real, evidenced, but UNVERIFIED-FOR-REGISTER-INDIRECT-RISK inventory** — safe from the stack
(§4) and structurally within valid app RAM, but not yet cleared to the "no `movea` anywhere materialises
this address" standard. **Exact next step, if 2+ 32-bit words are actually needed for a build**: run the
same `movea`/`addi` check used above against each specific candidate run before it is chosen, not
against all 273 speculatively.

---

## SECOND FINAL ADDENDUM — `ld.b`/`st.b` resolved, bit-ops censused, register-indirect checked, verdict given

**Why this exists**: `main` asked for the census to be re-done with EVERY gp-relative encoding —
`ld.b`/`ld.bu`/`ld.h`/`ld.hu`/`ld.w`, `st.b`/`st.h`/`st.w`, the 32-bit-displacement/absolute forms, the
`set1`/`clr1`/`tst1`/`not1` bit forms, and the `disp|1` word-form trap — because the prior addendum
explicitly left `st.b`/`ld.b` and bit-ops undecoded. This addendum closes those gaps and gives the
explicit yes/no verdict asked for.

### 1. `ld.b`/`st.b` — RESOLVED, and my own earlier collision fear was a hand-arithmetic error

**[EVIDENCE — 5 independent gp-based `ld.b` examples and 2 gp-based `st.b` examples (one even, one odd
target, from the SAME function at adjacent addresses `gp-0x6757`/`gp-0x6758`), all decoded
programmatically this time, not by hand]**:

| opcode6 | rule | mnemonic | example |
|---|---|---|---|
| `0x38` | `disp = hw2` exactly, BOTH parities, no adjustment | `ld.b` (signed byte) | `gp-0x6752` (even, `0x23A6E`) and `gp-0x6757` (odd, `0x29236`) — same opcode, same exact-`hw2` rule, both confirmed |
| `0x3A` | `disp = hw2` exactly, BOTH parities, no adjustment | `st.b` | `gp-0x6758` (even, `0x29164`) and `gp-0x6757` (odd, `0x2916A`) — same opcode, same rule |

**My prior addendum's worry — that odd-target `st.b` might collide with `st.h`/`st.w`'s shared `0x3B`
— was WRONG, and the error was mine, not the ISA's**: I first computed `hw1=0xc744`'s opcode field by
hand and got `0x39`; recomputing it programmatically gives `51012 >> 5 = 1594`, `1594 mod 64 = 58 =
0x3A` — I had mis-multiplied `0xc744` to decimal by hand (`50980` instead of the correct `51012`).
**`ld.b` and `st.b` each use ONE clean opcode for both parities (`0x38`, `0x3A`), with no collision
against `ld.h`/`ld.w` (`0x39`) or `st.h`/`st.w` (`0x3B`).** The corrected scanner (below) implements
this properly. Recording the error rather than hiding it, per this kit's own doctrine.

### 2. Bit-ops (`set1`/`clr1`/`tst1`/`not1`, Format VIII) — CENSUSED for `gp` as base, not assumed absent

**[EVIDENCE, whole-image scan, `reg1==4` specifically]**: `set1`'s confirmed encoding (from the earlier
`r18`-based example, `0x020772`) is `opcode6 (bits5-10 of hw1) == 0x3E`, `reg1 = hw1&0x1F`. Scanning the
whole image for `opcode6==0x3E` AND `reg1==4` (i.e. `gp` used DIRECTLY as the bit-op base, not via a
`movhi`-derived register like the one example already on record) finds **27 hits** — so this form is
**not** absent for `gp`, contrary to what I implied by extrapolating from one `r18` example. Checked
every one of the 27 `hw2` values (the encoded bit-field target) against `0x6a2a`/`0x683c`/`0x6994`/
`0x6ab0`/`0x6aaa`/`0x68b0`/`0x68aa`: **zero matches**, under both a signed and the raw-positive reading
Ghidra displayed for the `r18` example. Several of the 27 hits sit inside the cal/data region (`>0xC0000`),
i.e. are almost certainly false positives from data bytes coincidentally matching the bit pattern — I did
not adjudicate those individually since none of them matter to the candidates either way.

### 3. Register-indirect / absolute-pointer check, done for real this time

**[EVIDENCE, raw byte scan]** For `gp-0x6a2a`, `gp-0x683c`, `gp-0x6994`, `gp-0x6ab0`, `gp-0x68b0` (and
their run partners): (a) a raw search for the exact 4-byte little-endian absolute address
(`0xFEDF15D6`, `0xFEDF17C4`, `0xFEDF166C`, `0xFEDF1550`, `0xFEDF1750`) anywhere in the image at ANY byte
alignment — **zero hits, all five**; (b) a loose `movhi`-high-halfword-then-`movea`-low-halfword
proximity scan (the high 16 bits of the address found, then the low 16 bits found within the next 16
bytes) — **zero hits, all five**. Combined with the confirmed absence of any `ld`/`st`/bit-op encoding
touching these displacements (§1-2 plus the original scan), this is the closest this kit's own methods
get to excluding register-indirect risk for these specific cells — **not a mathematical proof (a
sufficiently indirect computed-pointer chain could still exist and is never fully excludable by static
scanning, per this kit's own `gp-0x1500` precedent), but every check this session's toolset can perform,
run.**

### 4. Block-clear loops — only the one already found; no second bulk clear touches these cells

**[EVIDENCE]** `search_instructions mnemonic:"sst.w"` (the store-via-`ep` form the boot clear loop uses)
returns matches concentrated entirely in the early bootloader/C-runtime-library region (`0x0000`-`~0x4000`),
each an ISOLATED single-field store inside a small helper function's prologue/struct-init — not a second
memset-style loop. **The only bulk RAM clear in the image remains the one already documented**
(`reference_accord_app_ram_layout_and_boot_init_loops.md`, `0x146C0`, zeroing the entire
`0xFEDEC000..0xFEDFFFFF` window at boot) — already accounted for in the prior addendum (it explains WHY
these cells boot to a known value, it does not touch them again at runtime).

### 5. THE VERDICT

**YES — multiple free 32-bit-aligned words exist in the `gp`-relative range, verified to the fullest
standard this session's tools support.** Three concrete, individually-verified candidates (zero hits
under the corrected 9-form scanner in §1 of this addendum + the original scan, zero `gp`-based bit-ops,
zero absolute-pointer or `movhi`/`movea` register-indirect hits, confirmed outside the true stack range
`gp-0xC000..gp-0x86E4`):

| candidate | size | status |
|---|---|---|
| `gp-0x6ab0 .. gp-0x6aaa` | **2 words, 8 bytes** | fully verified |
| `gp-0x68b0 .. gp-0x68aa` | **2 words, 8 bytes** | fully verified |
| `gp-0x6c44 .. gp-0x6c3a` | **3 words, 12 bytes** | fully verified |

Any of these three satisfies the stated "4 bytes minimum" with margin; the 12-byte candidate approaches
the "8-16 preferred" range. **A 4-word (16-byte) candidate fully verified to this standard was not
found within this session's time budget** — the systematic scan (prior addendum §5) found 266 candidate
runs total (22,212 free bytes, several ≥16 bytes, the largest 1672 bytes), but only these three plus
`gp-0x6a2a`/`gp-0x683c` have been individually run through the FULL check set above. **Exact next step
if 16 bytes are truly required**: run the same 4-part check (opcode-table scan already covers the whole
image; bit-op check; absolute-pointer scan; `movhi`/`movea` proximity scan) against one of the larger
named runs from the prior addendum's §5 table before committing to it.

---

## THIRD FINAL ADDENDUM — Q10-Q12: a notch cave on the clamped sum `S` (`gp-0x6b2e`, `r12`)

**Context** (per `loopshape`'s brief): the leading candidate is a biquad notch on the clamped P+I+D sum
`S`, hooked between the sum clamp (`0xC61BE`) and the output-lag filter at `0x2A174`, so the output lag
filters the NOTCHED `S` instead of the raw one.

### Q10 — the hook site, register liveness, and why "before `0x2A174`" isn't achievable as one site

**[EVIDENCE, `disassemble_bytes dry_run:true`, stock, `0x2A130`-`0x2A1B4`]** The sum clamp resolves
through **four separate paths that all converge at `0x2A174`, not before it**:

```
0x2A13A  mulh r10, r12          ; r12 = raw scaled sum
0x2A13C  subr r0, r12           ; r12 = -r12
0x2A13E  ld.hu 0x71be,tp,r9     ; limit = cal(0xC61BE)=15360
0x2A142  cmp  r9, r12
0x2A144  ble  0x2A14C
0x2A146  ld.h 0x71be,tp,r12     ; clip HIGH            -> br 0x2A174   (2-byte br)
0x2A14A  br   0x2A174
0x2A14C  ld.hu 0x71be,tp,r6 ; subr r0,r6 ; cmp r6,r12 ; bge 0x2A160
0x2A156  ld.hu 0x71be,tp,r12 ; subr r0,r12 ; sxh r12  ; clip LOW -> br 0x2A174
0x2A15E  br   0x2A174
0x2A160  sxh  r12                                     ; in range -> br 0x2A174
0x2A162  br   0x2A174
0x2A164  mov 0x0,r24 ; mov 0x0,r29 ; mov 0x0,r27 ; mov 0x0,r22   ; <-- disengage/skip entry
0x2A16C  mov 0x7fffffff,r16                                       ;     sentinel
0x2A172  mov 0x0,r12            ; S FORCED TO 0                    ; falls through, no branch
0x2A174  ld.hu 0x73ee,tp,r7     ; <<<<< THE ONLY TRUE CONVERGENCE POINT — HOOK HERE
0x2A178  ld.w  -0x3d3c,gp,r9
0x2A17C  st.h  r12,-0x6b2e,gp   ; publish S (== gp-0x6b2e, the "S" telemetry cell)
0x2A180  mul   r7,r12,r0        ; S consumed here, r12 becomes b*S (S itself dies here)
```

**`r12` = the clamped `S` is confirmed on the engaged path** (all three clip/in-range branches leave it
in `r12`) **and confirmed exactly `0` on the `0x2A164` disengage/skip path** (`mov 0x0,r12` at `0x2A172`,
falling straight through into `0x2A174` — no branch skips it). This directly matches what the brief
asked to confirm.

**Why the cave cannot go "before `0x2A174`"**: three of the four converging predecessors are 2-byte
`br` instructions (`0x2A14A`, `0x2A15E`, `0x2A162`) — too short for a 4-byte `jr`, and even if they
were long enough, they are three SEPARATE addresses, not one common site. The fourth predecessor
(`0x2A172`) falls through with no branch at all. **`0x2A174` itself is the only address every path
passes through**, exactly analogous to how `0x28FBE` was the sole convergence point for the feedback
clamp in Q8. **Hook: replace the 4-byte `ld.hu 0x73ee,tp,r7` at `0x2A174` with a 4-byte `jr <cave>`.**
Every existing branch that targets `0x2A174` (all three, plus the fallthrough) still lands correctly on
whatever instruction occupies that address, so no other byte needs to move.

**What the cave must do before returning**: replicate `ld.hu 0x73ee,tp,r7` (`r7 := cal(0xC63EE) = 507`)
as its last act, then `jr 0x2A178` — the displaced instruction's only job was to produce that one value,
consumed at `0x2A180`.

**Register liveness at `0x2A174`, verified by reading every instruction from `0x2A174` through the
downstream stores** (not inferred): `r16` (E on the engaged route / `0x7FFFFFFF` sentinel), `r22`,
`r24`, `r27`, `r29` are all LIVE — each is published by the interleaved stores immediately after
(`0x2A188`→`gp-0x6b32`, `0x2A18C`→`gp-0x6cf8` the sentinel, `0x2A190`→`gp-0x6dd0`, `0x2A19C`→`gp-0x6b36`,
`0x2A1A2`→`gp-0x6b34`) and none of them is read or written between `0x2A174` and those stores by
anything the cave would displace — **the cave must not touch these five registers.**

**Scratch confirmed free (4 registers, matching the biquad's stated need)**: `r6`, `r7`, `r9`, `r13` are
**not read by any instruction between `0x2A174` and `0x2A1B0`** (checked by reading every operand in
that span) — their pre-cave values are dead, each is freshly overwritten later (`r7`/`r9` immediately at
`0x2A178`/`0x2A180`/`0x2A184`/`0x2A194` by the EXISTING code that still runs after the cave returns;
`r6` next written at `0x2A1BE`; `r13` next written at `0x2A1D4`). `r7` has one constraint: the cave's
LAST write to it, before `jr`-ing back, must be `507` (replicating the displaced instruction) — free to
use internally before that.

**`lp`**: LIVE (the documented `0x29A2C`-`0x2A29A` window contains `0x2A174`) — **`jr` only, never
`jarl`**, same discipline as every other hook in this function.

### Q11 — is `0x2A174` reached on every disengage/skip route? YES for two of three confirmed directly; the third needs one more caveat

**[EVIDENCE]** `0x2A164` (the target of `0x29A5C`/`0x29A64` per the existing kit record) falls straight
through `0x2A166`-`0x2A172` into `0x2A174` with **no branch anywhere in that span** — confirmed by the
listing above. **`S = 0` exactly on this route.**

**[EVIDENCE, fresh disassembly `0x2A0A0`-`0x2A138`]** `0x2A0C6` (the target of `0x29A70`, "the
`gp-0x680a` lane") also reaches `0x2A174` — but NOT by zeroing `r12` directly. It zeroes `r24`/`r27`/
`r29`/`r22` and sets the `r16` sentinel (the SAME five-register pattern as `0x2A164`), then runs its own
LERP computation (reading `gp-0x6a34` — **the same rectified-feedback-magnitude cell from Q7 of the
first ADDENDUM** — through a table at `tp+0x7710`-`0x7730`) producing a value in `r10`, which **feeds
directly into the SAME clamp entry at `0x2A138`** (`add r9,r10` → `mulh r10,r12` → the clamp → `0x2A174`).
**So `0x2A0C6` DOES reach the hook every time, but I have NOT confirmed its `S` is exactly zero** — it is
whatever this alternate LERP produces, clamped the same way as the normal path. This is the honest
caveat the brief's "if yes... if some path bypasses it" framing invited: **no path bypasses `0x2A174`**,
but **the `S=0` claim is proven for `0x2A164` only, not (yet) for `0x2A0C6`.**

**Consequence for the notch state**: since ALL paths reach the hook every tick, **a notch filter placed
there runs continuously, including disengaged** — no path skips the cave, so there is no "cold" state
that needs a sentinel-triggered re-init the way the V288 setpoint filter needed one (that cave sits
downstream of a value that COULD freeze while disengaged; this one is on a value proven to reach zero on
at least one of the two disengage-adjacent routes and to always be visited). Whether the state "decays
to 0 naturally" depends on `0x2A0C6`'s LERP output actually being small/zero, which is unconfirmed —
**exact next step**: trace the `tp+0x7710`-`0x7730` LERP's knot values (V282/V288 cal bytes) to determine
its output range, the same way Q7's sibling LERP was characterised.

**I did not verify the `0x29A70` → `0x2A0C6` edge itself this session** (relayed from the existing V288
adversarial-pass record, not re-derived) — flagging as inherited, not independently re-confirmed, though
the CONSEQUENCE of reaching `0x2A0C6` (that it flows into `0x2A138`/`0x2A174`) is my own fresh disassembly.

### Q12 — cycle budget and free-flash re-confirmation

**Cycle cost [BELIEF for the per-instruction cycle counts — no V850E2 datasheet timing table was traced
this session; EVIDENCE for the instruction count and the clock]**: a biquad cave in this shape is
roughly 5 `mul` + ~10 `ld`/`st` + a handful of branches, call it 20-25 instructions. Even at a
pessimistic 4 cycles/instruction (V850E2's pipeline typically retires simple ALU/load ops in 1-2 cycles
and `mul` in 2-4, so this is a deliberately generous upper bound, not a measured figure), that is
**≈80-100 cycles**. At the kit's confirmed `PCLK = 40 MHz` (the OSTM0/80 MHz derivation is refuted
elsewhere in this record), 100 cycles is **2.5 µs — 0.25% of the 1 ms tick**, with roughly an order of
magnitude of margin even under the pessimistic assumption. **No slack indicator exists to check this
against** — re-confirming, not newly discovering, TASK 3 of the first source trace: the TCB carries no
period field and no watchdog/overrun counter was found. The bound above is a structural argument
("this is a tiny fraction of any plausible tick"), not a measurement against a real headroom figure —
stated as such, not dressed up as more than it is.

**Free flash [EVIDENCE, fresh byte read, V288 rev 2 image]**: re-confirmed this session —
`0xC4C2C`-`0xC4C2F` = `b6 07 4a 51` (the tail of V288's own filter-cave code, non-`0xFF`), and
`0xC4C30` onward is immediately `0xFF`. The region `[0xC4C30, 0xC4FFC)` (972 bytes) has exactly the same
**12 non-`0xFF` bytes** at `0xC4FF0`-`0xC4FFB` as previously found (the pre-existing unidentified
structure, left untouched) — **960 bytes still free**. **V288's own `jr 0x29D76` return and the `0x14A`
telemetry rung are confirmed fully contained in `0xC4BD6`-`0xC4C2F`** (per the adversarial pass's own
byte ranges, re-checked against this session's direct read) — **neither is in the way of new code placed
at `0xC4C30` onward.**

---

## ADDENDUM — `0x2A0C6` route and V289 pre-build items (`tracer2`, for `main`)

**Agent**: `tracer2` (subagent, reports to `main`). Study/analysis only. **Programs**: `code.bin` (stock,
Ghidra, only program open — confirmed via `list_open_programs`) for all disassembly; raw Python byte
reads against the V288 rev 2 image named in `main`'s brief (sha256 unchanged, not re-hashed this pass —
relying on the prior session's hash confirmation) for cal/table VALUES only.

### Q1 — what is `S` on the `0x2A0C6` route, and what selects it

**[EVIDENCE, `disassemble_bytes dry_run:true`, stock, `0x2A0A0`-`0x2A140` and `0x29A40`-`0x29A80`, plus
`get_xrefs_to` on `0x2A13A`/`0x2A13E`]**

**The branch condition, fully resolved** (the brief's open item — "I did not verify the `0x29A70` →
`0x2A0C6` edge itself" from the prior addendum):

```
0x29A44..0x29A5C   two Honda disengage/skip tests (r14==0 && r8==1  ->  jr 0x2A164)
0x29A60..0x29A64   a third test (r25==0  ->  jr 0x2A164)
0x29A68  ld.bu -0x680a, gp, r13      ; r13 = gp-0x680a, a byte flag
0x29A6C  cmp   0x1, r13
0x29A6E  bne   0x29A74               ; r13 != 1  -> falls to the ELSE branch (gp-0x682f driver-override
                                      ;   taper, decompile lines 793-794, unrelated to this route)
0x29A70  jr    0x2A0C6               ; r13 == 1  -> THIS route
```

**Answer: the sole condition is `gp-0x680a == 1`**, tested only after the two disengage/skip tests have
already failed (so this is neither of Honda's own skip cases). It is a **mode/variant-select byte**, not
an "engaged but steering-request off" state and not literally a fault flag as far as any evidence this
session found shows — see the reachability finding below, which argues it is not any *live* state at all.

**The `0x2A0C6` computation itself** [fresh disassembly, `0x2A0C6`-`0x2A138`]:

```python
# r26 = fb, the clamped feedback sum -- STILL LIVE here (Q8's prior finding: r26 untouched from the
#   clamp resolution to 0x29D78; this route branches AROUND 0x29D78 without ever reading r26, so it
#   reaches 0x2A0C6 with r26's clamp-time value intact)
sign_fb = +1 if r26 >= 0 else -1                      # 0x2A0C8 cmp r0,r26 ; 0x2A0D4 cmovlt -1,r12,r12
x = gp_0x6a34                                          # 0x2A0CA ld.hu -0x6a34,gp,r8 (UNSIGNED) -- the Q7
                                                        #   rectified/quantized |fb| magnitude, >>5
lo_bound = cal(0xC6712)                                # 0x2A0D0 ld.hu 0x7712,tp,r9  (tp+0x7712 = 0xC6712 --
                                                        #   NOT 0xC7712, the tp+0x1000 trap; positive-
                                                        #   controlled below against 6 known cals)
if x <= lo_bound:                                       # 0x2A0F2 bh 0x2A0FA (branch if x>lo_bound)
    y = cal_y[0]                                        # 0x2A0F4: cal(0xC6722) = clamp-low
elif x >= hi_bound:                                     # hi_bound = cal(0xC6720); 0x2A100 bnc 0x2A10C
    y = cal_y[7]                                        # 0x2A10C: cal(0xC6730) = clamp-high
else:
    y = LERP(x, x_table=cal[0xC6712:0xC6720:2], y_table=cal[0xC6722:0xC6730:2])   # 8-knot piecewise-linear
S = -sign_fb * y                                        # 0x2A13A mulh r10,r12 ; 0x2A13C subr r0,r12
# S then falls into the SAME clamp entry as the main path: 0x2A13E ld.hu 0xC61BE,tp,r9 (limit 15360)...
```

**Actual table values, read from the V288 rev 2 image** [EVIDENCE, raw Python LE read, method
positive-controlled against 6 already-known cals in the SAME read — `0xC63E8`=923, `0xC63EA`=1560,
`0xC63EC`=992, `0xC63EE`=507, `0xC61BE`=15360, `0xC61B6`=10240, all exact — so the `tp+0x1000` arithmetic
and the file offset are trustworthy for this read]:

```
0xC6710 = 8                                    (knot count)
x-knots  0xC6712..0xC6720 (step 2): [64, 65, 67, 73, 80, 88, 96, 104]
y-knots  0xC6722..0xC6730 (step 2): [608, 704, 704, 832, 832, 832, 832, 832]
```

**So `S` on this route is NOT zero and NOT a P/I/D quantity** — it is a *fast-saturating, sign-flipped
function of the feedback magnitude*: for `|x| <= 64`, `y=608`; the curve steps to `704` by `x=65`, to `832`
by `x=73`, and is FLAT at `832` for every `x >= 73` up to and past the table's own upper knot (`104`).
**`S ∈ {-832..-608} ∪ {608..832}`, sign opposite `fb`** — i.e. a near-constant-magnitude "anti-feedback"
term, not a smoothly-varying one. In counts of the `0xC61BE`=15360 sum clamp, this is **4.0%-5.4% of the
clamp ceiling** — small, and it never approaches saturating that clamp on its own.

**Is this route reachable at runtime? [EVIDENCE for the null; BELIEF, clearly labeled, for what it implies]**
`gp-0x680a` was checked for writers by **two independent, positive-controlled methods**, per the skill's
"positive-control every scan" rule:
1. `search_instructions operand_pattern:"-0x680a"` — **2 hits total, image-wide, both `ld.bu` reads** (the
   test above at `0x29A68`, and one orphan read in the proven-unreachable duplicate `FUN_0002a93a` at
   `0x2A96A`). **Zero writers.**
2. A raw Python LE byte scan (the trace's own byte-verified opcode table: `st.b` opcode `0x3A`, `st.h`/
   `st.w` opcode `0x3B`, `gp`-based bit-ops opcode `0x3E`, `reg1==4` for `gp`) over the WHOLE image
   (stock and V288 rev 2, both — identical), for displacement `-0x680a` (`0x97F6` two's-complement).
   **Positive control**: the same scanner run against `gp-0x6a34`'s known writer (`0x290CA st.h`) finds
   it correctly (1/1). Run against `gp-0x680a`: **zero hits of any kind** (no `st.b`, `st.h`, `st.w`, or
   `gp`-based bit-op). A separate absolute-pointer scan (exact 4-byte LE `0xFEDF17F6` anywhere in the
   image) and a loose `movhi`-then-`movea` proximity scan for the same address both also return **zero**.
3. `gp-0x680a` sits inside the documented `.data` band (`gp-0x6E50..gp-0x2598`, from
   `reference_accord_app_ram_layout_and_boot_init_loops.md`), so its runtime value is NOT an assumed-zero
   bss default — it is a specific flash-sourced byte. Computed this session: **boot value = `0x00` in
   BOTH stock and V288 rev 2** (flash offset `0x868A6`).

**Conclusion**: `gp-0x680a` boots to 0 and has **zero writers found by any method this session's tools
support** — the same standard this kit's own record already applies to calling `gp-0x1500`-class cells
"free." **BELIEF, not proof** (per the skill's own caveat on register-indirect risk: a sufficiently
indirect computed-pointer write is never fully excludable by static scanning): **the `0x29A70` →
`0x2A0C6` edge is very likely DEAD in this firmware** — `r13` reads 0 every tick, so the `bne 0x29A74` at
`0x29A6E` is always taken, and the `jr` at `0x29A70` is never reached. This matches this kit's own
recorded pattern of dead selector-gated branches (`accord-variant-selector-max-is-nine.md`,
`accord-lever-b-is-unreachable.md`) — a documented class, not a one-off.

### Q2 — does this matter for the notch's state

**Given Q1's finding, this is close to moot, but answered fully as asked.** A biquad with DC gain 1
(the design's own `notch_tick`, `B` sums to `A`) is a **linear, always-stable filter regardless of input
history** — no input value, however it arrives, can make its state diverge; the only question is
transient size at re-engage, not stability.

- **If `gp-0x680a==1` never fires (the evidenced-and-believed case)**: irrelevant — the notch never sees
  this branch's output at all, and the state's only inputs are the normal engaged-path `S` and the
  provably-zero `0x2A164` disengage value.
- **If it somehow DID fire (the residual, unexcluded-by-proof case)**: the injected `S` is bounded to
  `|S| <= 832` — **4.0-5.4% of the `0xC61BE`=15360 clamp**. Compare this to the transient ALREADY present
  on the very first engaged tick of the NORMAL path: a fresh engagement with a large initial error can
  legitimately deliver `S` up to the full `±15360` clamp on tick one (there is no ramp-limiting on `S`
  itself, only on the separate engagement-ramp multiplier `gp-0x69b0` applied downstream at `0x2A1E6`,
  per Q0 of the first addendum). **A stale notch state from this route, even in the worst unexcluded case,
  is smaller than the discontinuity the main engaged path can already produce on an ordinary first tick.**
- **Verdict: a sentinel-style re-init (Honda's `gp-0x6cf8` pattern, or the V288 setpoint-filter's own
  engage-init) is NOT needed for this hook.** It would be tidy, not required — consistent with the prior
  addendum's own Q11 conclusion that no route "freezes" a stale value the way the V288 setpoint filter's
  source value could.

### Q3 — is `r12` at `0x2A174` really the clamped P+I+D sum, with nothing rescaling it after the clamp

**Split into two parts, because fresh disassembly this session forces a correction to how the two
routes into the clamp were described.**

**Part A — nothing rescales `r12` between the clamp resolving and `0x2A174`: CONFIRMED, independently.**
`get_xrefs_to` on `0x2A13A` returns exactly 2 predecessors (`0x2A0F8`, `0x2A110`) — **both inside the
`0x2A0C6` lane itself** (its own out-of-range short-circuits). `get_xrefs_to` on `0x2A13E` returns
exactly 1 predecessor (`0x2A0C4`) — **the main/normal path's own unconditional branch**. Combined with
the prior addendum's own disassembly of `0x2A13E`-`0x2A174` (the `0xC61BE`=15360 compare/clip/in-range
branches, all converging at `0x2A174` with `r12` untouched or zeroed), this is airtight: **whichever route
sets `r12`, nothing after that point rescales it before `0x2A174`.** Clamp cell/value re-confirmed by
this session's own positive-controlled read: `0xC61BE = 15360`.

**Part B — a correction: the `mulh r10,r12`/`subr r0,r12` pair at `0x2A13A`/`0x2A13C` belongs ONLY to the
`0x2A0C6` lane, not the main path.** The main/normal path's own tail (`0x2A0A0`-`0x2A0C4`) branches
**directly and unconditionally to `0x2A13E`** (`0x2A0C4: br 0x2A13E`), **skipping `0x2A13A`/`0x2A13C`
entirely** — confirmed by the xref counts above. So on the everyday engaged path, whatever value reaches
`0x2A13E` in `r12` was finalized by the code ending at `0x2A0C4`, not by a `mulh`/negate step.

**What actually feeds `r12` into `0x2A0C4` — an honest scope note, not fully re-traced this session**:
fresh disassembly of `0x29F08`-`0x2A0C4` (the span between the D-clamp resolving and the main path's
entry to the sum-clamp comparison) shows **a chain of at least three more per-variant piecewise-linear
table lookups** (`mov 0xcbb54,r10`/`0xcbc34,r8`/`0xcbbc4,r13`/`0xcbae4,r6` base pointers, each indexed by
a register-selector offset and walked with the same `sld.hu`/loop/`divq` LERP idiom as Q1's table above),
**not a single bare `P+I+D` addition** at that point. This matches this kit's own documented
"ONE selector indexes ALL FIVE per-variant banks" pattern (`accord-one-selector-indexes-all-five-banks.md`)
rather than a simple three-term sum. **I did not trace this chain back further to `0x29D78`/`0x29EE0`
this session** — it is out of this brief's scope (the notch only cares what value is being clamped at
`0xC61BE`, not its full derivation) and re-deriving it fully would need another pass. **Restated
precisely for the notch design**: `r12` at `0x2A174` on the engaged path is **the fully-formed,
per-variant-gain-scaled control value that the firmware itself clamps to `±15360` before the output-lag
filter** — calling it "the clamped P+I+D sum" (the first session's shorthand) is directionally right but
elides at least one gain-LERP stage; **the notch's input range is still bounded exactly as stated
(`±15360`), which is what actually matters for sizing the cave** — this correction changes the label, not
the bound.

### Q4 — the 100 Hz `0x14A` telemetry rung: register liveness and read atomicity

**Register liveness — relayed as EVIDENCE from the closed adversarial pass, re-attempted independently
this session with an honest result.** `docs/review/ADVERSARIAL-V288-PREREG-2026-09-07.md` states
(line 43): *"0x14A cave. Full listing 0xC4B34–0xC4BFD: no `jarl`, only r6/r7 written, so `lp` is intact
at the relocated `jmp [lp]` @0xC4BFC."* I attempted an independent raw-byte corroboration this session
(a fixed-2-byte-stride opcode-field scan for the `jarl` opcode field, `(hw1>>6)&0x1F==0x1E`, over
`0xC4B34`-`0xC4C30` of the V288 rev 2 image) and it is **INCONCLUSIVE, not confirmatory** — V850 is a
variable-length (2/4/6-byte) ISA, and a fixed-stride scan across a 252-byte region without walking real
instruction boundaries produces spurious mid-instruction matches (I got 7 "hits", which is not
credible for a ~63-instruction cave and was not adjudicated instruction-by-instruction). **I did not
open the V288 image as a second Ghidra program to get a byte-exact disassembly** — that is a real, if
small, mutation to the shared project (a new persistent program), which I did not judge this narrow
re-verification worth doing unprompted. **My honest position: the adversarial pass's "r6/r7 only, no
`jarl`" finding stands as EVIDENCE from that closed, already-adjudicated review; my own attempted
re-verification this session neither confirms nor refutes it — it is simply not a valid method for this
question.** Exact next step if a from-scratch re-confirmation is required: `import_file`/`open_program`
the V288 rev 2 image in Ghidra and run `disassemble_bytes dry_run:true` over `0xC4B34`-`0xC4C30`.

**Read atomicity — BELIEF, as the brief asked, since not independently provable from this session's
toolset.** Both `S` (`gp-0x6b2e`) and any new notch-output cell `y` would be individual 16-bit halfwords,
matching the pattern of every other published cell in this loop (`gp-0x6b32`/`0x6b34`/`0x6b36`, all
halfwords). **BELIEF**: a halfword-aligned load on V850E2's 32-bit data bus completes in a single bus
transfer (standard for this class of core; not re-derived from the `UPD70F3508` datasheet/SVD timing
tables this session). Under that belief, each INDIVIDUAL word-read cannot be torn mid-value. **The
residual hazard is not single-word tearing but cross-cell skew**: the 100 Hz task reads `S` and `y` with
two separate instructions, so it can observe `S` from tick `N` and `y` from tick `N+1` if a 1 kHz update
lands between the two reads. This is **the same class of hazard the existing three-sign rung already
accepts** (it already reads multiple independently-updated 1 kHz cells — `gp-0x6b32`/`0x6b34`/`0x6b36` —
without any lock, and has flown on V288 without an incident attributable to it) — **not a new risk
category**, just the same one restated for a fourth/fifth cell pair.

### Summary for `main`

1. **Branch condition, fully resolved**: `gp-0x680a == 1` selects the `0x2A0C6` route (after Honda's own
   two disengage/skip tests fail). It is a mode-select byte, not literally the "steering-request off,
   override, or fault" framing in the brief — none of those; see (2).
2. **`gp-0x680a` is very likely a DEAD selector** — zero writers by two independent positive-controlled
   methods, boots to 0 in stock and V288, no absolute/`movhi`+`movea` pointer to it found either. BELIEF,
   not proof (register-indirect residual, same caveat this kit always carries).
3. **`S` on this route, IF it ever fired**: `S = -sign(fb) * LERP_8knot(gp-0x6a34)`, a fast-saturating
   curve, `|S| ∈ [608, 832]` — 4.0-5.4% of the `0xC61BE`=15360 clamp. Not zero, not P/I/D, but small and
   bounded.
4. **No sentinel/re-init needed for the notch** — even in the unexcluded worst case, this route's `S` is
   smaller than the transient the normal engaged path can already produce on an ordinary first tick.
5. **Clamp confirmed** (`0xC61BE`=15360, positive-controlled read) and **confirmed nothing rescales `r12`
   between the clamp and `0x2A174`** (xref-counted: exactly 1 predecessor into `0x2A13E`, exactly 2 into
   `0x2A13A`, both accounted for). **Correction**: the `mulh`/`subr` pair at `0x2A13A`/`0x2A13C` belongs
   only to the `0x2A0C6` lane; the main path skips it via a direct branch. What feeds `r12` on the main
   path is a chain of per-variant gain-LERPs (not re-traced fully to `P+I+D` this session) — the notch's
   `±15360` input bound is unaffected by this correction.
6. **0x14A rung liveness**: relayed as EVIDENCE from the closed adversarial pass (r6/r7 only, no `jarl`);
   my own attempted re-verification this session was methodologically inconclusive (fixed-stride scan on
   a variable-length ISA) — flagged honestly rather than presented as confirmation.
7. **Read atomicity**: BELIEF that aligned halfword reads are non-tearing on V850E2 (not re-derived from
   the datasheet this session); the real residual is cross-cell skew between two separately-read cells,
   which is the same hazard class the existing three-sign rung already accepts.

