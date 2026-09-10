# TRACE 2026-09-09 — V290 post-lag hook, rate-operand liveness, and RAM census

**Agent**: subagent of `design290` (orchestrator `main`). Study/analysis only — nothing built,
flashed, or sent. GhidraMCP only (`disassemble_bytes dry_run:true`, `search_instructions`,
`get_xrefs_to`), plus raw Python LE byte scans of the actual V289 image for every claim where a
null result is load-bearing (per `firmware-decompile` skill doctrine). Constants read little-endian.
`gp=0xFEDF8000`, `tp=0xBF000`.

**Image**: `_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
imported into Ghidra this session as a second program (no auto-analysis; all disassembly via
`dry_run:true`, so nothing was mutated — the program is left open, un-saved, per this kit's
"never `save_program` after exploratory disassembly" rule). All Q1/Q2/Q3/Q4/Q5 code addresses below
are **byte-identical between V282, V288 rev 2 and V289** except the declared 185-byte V289 diff
(`docs/review/ADV-V289-D-INTERLOCKS-GATE1-2026-09-08.md` §D2), so `code.bin` (stock, fully
auto-analysed, 2086 functions) was used for all disassembly of the loop body outside the cave itself
(0x2A174 hook onward is identical to V282/stock outside the 4-byte `jr`); the cave body
(`0xC4C00-0xC4C8C`, new in V289) was read from the imported V289 program directly.

**This trace extends, and does not re-derive, `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`**
(Q1–Q12 + THIRD FINAL ADDENDUM) and the two closed adversarial passes
`docs/review/ADV-V289-A-ARITHMETIC-2026-09-08.md` / `docs/review/ADV-V289-D-INTERLOCKS-GATE1-2026-09-08.md`.
Where this trace's findings **correct or falsify** something those documents said, that is stated
explicitly, not silently substituted.

---

## Q1 — the rate operand `gp-0x6a56`

### Q1(i) — every writer, image-wide; is it written inside the same tick before the hook?

**[EVIDENCE, two independent methods, set-differenced]**

**Method A — Ghidra `search_instructions operand_pattern:"6a56"`, program-wide (code.bin, 183,576
instructions scanned)**: 30 raw substring hits. Adjudicated: **20 true gp-relative accesses** (19
`ld.h` readers + the fb-filter's own `0x28F4C` read = 20 readers total across 18 functions; 4
`st.h` writers) **+ 5 branch-target digit coincidences** in `FUN_0006a442`/`FUN_00046a42`
(`0x46a50`, `0x6a48a`, `0x6a4aa`, `0x6a4d4`, `0x6a4fe` — branch targets whose hex address happens to
contain the digits `6a56`-adjacent, base register is a branch PC not `gp`; the documented
false-positive class), excluded.

**Method B — raw little-endian Python scan, ALL gp-relative forms** (`ld.b`/`st.b` opcode
`0x38`/`0x3A` disp=hw2 exact; `ld.h`/`ld.w` opcode `0x39`; `ld.hu` opcode `0x3F`; `st.h`/`st.w`
opcode `0x3B`; `ld.bu` opcode `0x3C`/`0x3D` with `reg2≠0` **and the `hw2` bit-0 discriminator against
the `jr`/`jarl` collision** (see "self-caught error" below); 6-byte extended form `reg2==0`; gp-direct
bit-ops opcode `0x3E`), script `analysis-2020accord/verify/v290_q1q3_rateop_and_ram_census.py`,
positive-controlled against 5 known cells (`gp-0x3d3c`, `gp-0x6a32`, `gp-0x6752`/`0x6757`,
`gp-0x6758`, `gp-0x6c44`, all PASS) before trusting the result:

**Total: 25 readers, 4 writers, 0 bitops, 0 ext6.** The 4 writers are **identical** to Method A
(`0x3F7B8`, `0x3F7D0`, `0x3F7E0` — `st.h r6,-0x6a56,gp`; `0x3F81E` — `st.h r0,-0x6a56,gp`), **all
four inside `FUN_0003F776`**, the sole producer (per existing kit memory
`accord-gp6a56-is-motor-rate-not-an-angle-sensor.md`, re-confirmed rather than re-derived).

**5 readers found by the raw scan that Method A (Ghidra) MISSED** — a real undercount, exactly the
class the `firmware-decompile` skill warns about (`search_instructions` only sees
already-analysed instructions): `0x2D9BE` (`ld.h -0x6a56,gp,r6`), `0x3F7F2` (`ld.h -0x6a56,gp,r6`,
**inside the producer `FUN_0003F776` itself** — a self-read, not a new external consumer),
`0x4F942`/`0x4F964` (`ld.h -0x6a56,gp,r13`, inside a divide-heavy helper), `0x51150E`
(`ld.h -0x6a56,gp,r15`, immediately followed by `sar 0x3,r15` — **a `>>3` scale, matching the
memory record's "8 raw counts per deg/s" claim for the CAN packer**, so this is plausibly one of
the two CAN-packer reads the existing record already names by function, now pinned to an exact
address it didn't cite before). **All 5 independently confirmed real** via `disassemble_bytes
dry_run:true` spot-checks (not merely trusted from the raw decode) — none is a misaligned-data false
positive.

**Self-caught decoder error, recorded per doctrine**: the raw scanner's first pass also reported a
6th "new reader" at `0x14B1E`. `disassemble_bytes dry_run:true` on `0x14B18-0x14B25` shows this is
actually `jarl 0x5E0C8,lp` (three back-to-back `jarl`s) — **opcode `0x3C`/`0x3D` with `reg2≠0`
collides with `jr`/`jarl`'s Format-V encoding exactly as `ADV-V289-A-ARITHMETIC-2026-09-08.md` §1
already documents for `ld.bu`** ("the discriminator is `hw2` bit 0: 1 = `ld.bu`, 0 = `jr`/`jarl`").
My first-pass scanner omitted that bit-0 check; fixed and re-run (script updated in place, the fix
is recorded in the script's own comments) — the corrected 25/4 count above is post-fix. **Zero other
opcode-collision false positives found** after applying the fix (checked by re-running the full scan
and manually confirming all 25+4 hits via the positive-control battery plus the 5 spot-checks above).

**Verdict for Q1(i)**: **NO, `gp-0x6a56` is never written between the fb-filter's read (`0x28F4C`,
inside `FUN_00028ea6`) and the hook at `0x2A174`, WITHIN THE SAME TICK.** All 4 writers are in
`FUN_0003F776`, a **different function** from `FUN_00028ea6` (per
`get_function_callers(0x28EA6)` in `ADV-V289-D` §D2: exactly one caller, `FUN_0002214A` — not
`FUN_0003F776`). **BELIEF, not proof, on ordering**: whether `FUN_0003F776` runs before or after
`FUN_00028ea6` within the same 1 kHz dispatch tick was **not established this session** — this
kit's record has never pinned a static task/dispatch order for these two functions (Q6 of the
prior trace: "no period field, no watchdog" — the same gap applies to inter-function ordering). If
`FUN_0003F776` runs **before** `FUN_00028ea6` in the same tick (the design-intent-consistent
ordering — a signal must be produced before it's consumed), then a `ld.h -0x6a56,gp,r7` inside the
V289 cave (which runs strictly after `FUN_00028ea6`'s own `0x28F4C` read, at `0x2A174`+) would see
**the SAME already-updated value the fb filter's `x` used this tick** — i.e., yes, reading it in the
cave gets "this tick's" `gp-0x6a56`, not last tick's. If the ordering is reversed, the cave would see
**next tick's** value early. **Exact next step to resolve this as EVIDENCE rather than BELIEF**: find
where in the RTOS dispatch table (`0xBB920`-adjacent TCB region, per the prior trace's Q6) each of
`FUN_0003F776` and `FUN_00028ea6` is registered, or instrument both with a shared tick-counter probe
on a build and read back the counters — neither was in this session's scope.

### Q1(ii) — width/sign at the fb-filter's own load, and the `-(0x18F rate)` claim

**[EVIDENCE, `disassemble_bytes`, re-confirmed this session, matches the prior trace exactly]**
`0x28F4C: ld.h -0x6a56,gp,r7` — **SIGNED** halfword load (`ld.h`, not `ld.hu`). This is the ONLY
load form used at the fb-filter's own consumption point; none of the other 24 readers found in Q1(i)
uses `ld.hu` on this cell either (all 25 raw-scan readers are `ld.h`, confirmed in the script output)
— **no signed/unsigned mismatch exists anywhere on this cell**, unlike the sum/output clamps'
documented `ld.h`/`ld.hu` mixing defect.

**The `x = −(0x18F wire rate), 8 raw counts/deg/s` claim** [CITED, not re-measured, per the brief's
explicit instruction]: `docs/traces/TRACE-2026-09-08-...` Q1, itself citing
`memory/accord/signals/accord-gp6a56-is-motor-rate-not-an-angle-sensor.md`: *"It is what the EPS
transmits as `STEER_ANGLE_RATE` on CAN `0x14A[2:3]` (`(−gp-0x6a56)>>3`) and `0x18F[2:3]`
(`−gp-0x6a56` directly, 10× finer)"*. This session's new find at `0x51150E` (`ld.h -0x6a56,gp,r15`
then `sar 0x3,r15`) is **consistent with, and plausibly IS, the `0x14A[2:3]` packer's `>>3` scaling**
named in that citation — a new address pinned to an existing claim, not a new claim.

### Q1(iii) — is the filtered feedback (`r26`) still intact at `0x2A174`?

**[EVIDENCE, fresh disassembly this session, `0x29D78-0x2A0C8` and `0x29F60-0x29FEE`, plus a
whole-function `search_instructions operand_pattern:"r26"` re-run (18 hits, matches the prior
trace's Q8 count exactly)]**

**NO on the main/normal engaged path — CORRECTING an implicit assumption of the prior trace's Q8/Q10.**
Q8 established `r26` is untouched from the feedback clamp (`~0x28FBE`) to the E-former (`0x29D78`,
`sub r26,r16`). **This session traces PAST `0x29D78` and finds `r26` is overwritten shortly after**:

```
0x29F76  mov  r13, r26      ; r26 := r13 (a per-variant gain-LERP result — see below), NOT feedback
```

This instruction sits inside the same per-variant gain-LERP chain tracer2's Q3 (Part B correction)
already found feeds `r12` into `0x2A0C4: br 0x2A13E` (the sum-clamp entry) on the **main** engaged
path — confirmed by straight-line disassembly from `0x29F60` through `0x2A0C4` with **no branch out
of this block** other than the internal LERP dispatch (`0x29F98`-`0x29FBE`, a knot-search that stays
inside the block) and the final unconditional `br 0x2A0C4→0x2A13E` (already xref-confirmed by
`ADV-V289-D`/tracer2: `get_xrefs_to(0x2A13A)` = 2 preds, both inside the `0x2A0C6` lane;
`get_xrefs_to(0x2A13E)` = 1 pred, `0x2A0C4`). **So on the path that reaches `0x2A174` via
`0x2A0C4→0x2A13E`, `r26` at `0x2A174` holds whatever `0x29F76` last put there (a LERP scratch value),
not the filtered feedback sum.** No further write to `r26` occurs between `0x29F76` and `0x2A174` on
this path (confirmed: the whole-function `r26` search's next hit after `0x29F76` is `0x29F96` — a
`zxh r26`, a READ-then-widen, not a fresh assignment — then `0x29FE8` `cmovne r26,r9,r23`, which
READS `r26` as a source and writes `r23`, not `r26` — so `r26`'s value from `0x29F76` persists,
unmodified, all the way to `0x2A174`).

**YES on the `0x2A0C6` (`gp-0x680a==1`) lane — CONFIRMS tracer2's finding, with the branch structure
now nailed down.** `get_xrefs_to`-style reasoning (re-derived from straight-line disassembly of
`0x29A44-0x29A74` and `0x2A0C6-0x2A0C8`, matching tracer2's own listing exactly): the `jr 0x2A0C6` at
`0x29A70` fires **before** `0x29F76` is ever reached (lower address, and it is a genuine control-flow
jump, not a fallthrough) — a tick taking this branch **never executes `0x29D78`, `0x29F76`, or
anything in between**, so `r26` at `0x2A0C8` (`cmp r0,r26`, the sign test) still holds the value from
the feedback clamp resolution (`~0x28FBE`), exactly as tracer2 stated. **These two routes are mutually
exclusive per tick** (one `jr`, taken or not) — there is no tick on which both write patterns to `r26`
apply.

**Decision-bearing consequence for V290**: **a cave at or after `0x2A174` MUST NOT read the CPU
register `r26` expecting the filtered feedback sum** — on the overwhelmingly common main path (per
this kit's own belief that `gp-0x680a` is very likely dead, `ADV-V289-D`/tracer2's Q1-Q2 addendum),
`r26` there is stale LERP scratch, not feedback. **The correct way to obtain the filtered feedback
value at a post-lag hook is `gp-0x3d30`** (the fb filter's own PRIVATE state cell, 2 accesses, both
inside `FUN_00028ea6`, per the prior trace's Q1) — reading it fresh via `ld.w -0x3d30,gp,rX` inside
a V290 cave gets the fb filter's **new state (`s_new`, the increment)**, not the clamped
`s_old+s_new` sum the E-former used; if the DESIGN wants that exact clamped sum, it is not preserved
in memory anywhere past `0x28FBE`'s clamp resolution — **only re-deriving it from `gp-0x3d30` (state)
via the filter's own recurrence, or re-reading `gp-0x6a56` (raw, unfiltered) and re-applying the
known filter coefficients (`0xC63E8`/`0xC63EA`, a=923,b=1560, DC 30.89, no `>>5`), are the two options**
— this is a **BELIEF/design-scope note**, not re-derived as a working formula this session.

---

## Q2 — a post-lag injection hook, `0x2A178-0x2A240`

**[EVIDENCE, `disassemble_bytes dry_run:true`, code.bin, `0x2A178-0x2A23F`, 69 instructions, full
listing obtained and read instruction-by-instruction]**

### The lag output and the branchy deadband region

```
0x2A178  ld.w  -0x3d3c,gp,r9      ; s (lag state, old)
0x2A17C  st.h  r12,-0x6b2e,gp     ; publish S (telemetry, already notched by the V289 cave)
0x2A180  mul   r7,r12,r0          ; S * b   (r7 = cal(0xC63EE)=507, loaded by the cave's own tail)
0x2A184  ld.h  0x73ec,tp,r7       ; a = cal(0xC63EC)=992
0x2A188..0x2A1A2  [interleaved: st.h r29->gp-0x6b32, st.w r16->gp-0x6cf8 (sentinel),
                    st.w r24->gp-0x6dd0, ld.bu 0x74a3,tp,r16 (=cVar15/cal flag), st.h r27->gp-0x6b36,
                    st.h r22->gp-0x6b34]   ; Honda's own per-tick telemetry/sentinel publishes
0x2A194  mul   r9,r7,r0           ; a*s
0x2A1A0  sar   0xa,r12 ; 0x2A1A6 sar 0xa,r7   ; both >>10 (b*S)>>10, (a*s)>>10
0x2A1A8  add   r12,r7             ; s_new
0x2A1AA  add   r7,r9              ; s_old + s_new
0x2A1AC  sar   0x5,r9             ; <<< r9 = y, THE LAG FILTER'S OUTPUT
0x2A1AE  cmp   0x1,r16            ; test cVar15 == 1  (flags LIVE across 0x2A1B0!)
0x2A1B0  st.w  r7,-0x3d3c,gp      ; <<< UNCONDITIONAL — state := s_new — CANDIDATE HOOK SITE
0x2A1B4  bne   0x2A1E6            ; cVar15 != 1  -> straight to the ramp multiply, r9=y unchanged
0x2A1B6  ld.bu -0x6806,gp,r12     ; (only if cVar15==1) engaged-state byte
0x2A1BA  cmp   r0,r12
0x2A1BC  bne   0x2A1E6            ; gp-0x6806 != 0 -> straight to ramp multiply, r9=y unchanged
0x2A1BE..0x2A1E0  [a 3-stage deadband/sign test on y (r9) vs cal(0xC61B8), DISENGAGED-ONLY per
                    the prior trace's Q0 decompile finding: "if (cVar15=='\x01' && gp-0x6806=='\0')"]
0x2A1E2  mov   0x0,r9 ; 0x2A1E4 br 0x2A1EE     ; deadband fires -> r9:=0, SKIPS the mult entirely
0x2A1E6  mul   r14,r9,r0          ; <<< r14=gp-0x69b0 (engagement ramp) * r9(y) — Q0's finding
0x2A1EA  sar   0xf,r9 ; 0x2A1EC sxh r9
0x2A1EE  ld.h  0x746c,tp,r7 ; ... [gain stage, cal 0xC6752=-1, cal 0xC61B4=3072 clamp] ...
0x2A23C  st.h  r1,-0x6b38,gp      ; the 427-tap / motor-path delivered value
```

### Every 4-byte instruction strictly between `0x2A1AC` and `0x2A1E6`, and which one is real

There are **six** 4-byte instructions in this span (`0x2A1B0`, `0x2A1B6`, `0x2A1BE`, `0x2A1CA`,
`0x2A1D4`, `0x2A1DA`), but **five of them sit inside the disengaged-only deadband block** (only
executed when `cVar15==1 && gp-0x6806==0`) — a hook there would be **inert during ordinary engaged
driving**, the opposite of what a rate-feedback damping term needs. **Only `0x2A1B0` is
UNCONDITIONALLY executed every tick**, before the first branch (`0x2A1B4`) even evaluates.

**Chosen site: `0x2A1B0` (`st.w r7,-0x3d3c,gp`, 4 bytes, exactly `jr`-length).**

**Registers LIVE across `0x2A1B0`** (read before written afterwards, confirmed by reading every
instruction from `0x2A1AC` through `0x2A220`):
- **`r9` = `y`, the lag output** — read at `0x2A1C2` (inside the conditional block, if taken) and at
  `0x2A1E6` (the ramp multiply, on every path that isn't zeroed) — **this is the injection target**;
  a V290 cave should read, modify, and re-store `r9` here.
- **`r14` = `gp-0x69b0`, the engagement ramp** — loaded far earlier in the function (per Q0 of the
  prior trace, spanning `0x2936A`-`0x29714`), consumed at `0x2A1E6` — must not be clobbered.
- **`r11`** — no write between `0x2A178` and `0x2A1FC` (`add r9,r11`) in this whole listing; it must
  already hold a value from **before** `0x2A1AC` that survives to `0x2A1FC` — **LIVE across the
  candidate site**, must not be clobbered.
- **PSW flags from `cmp 0x1,r16` @ `0x2A1AE`** — consumed by `bne` @ `0x2A1B4`, the very next
  instruction after the candidate site. **This is a genuinely new hazard this session found, not
  flagged by the prior trace (which only analysed the Q10 hook at `0x2A174`, a different site)**:
  most V850 ALU ops set Z/S/OV/CY, so if a V290 cave replaces `0x2A1B0` with a `jr` and its own
  arithmetic runs before `jr`-ing back to `0x2A1B4`, the flags `bne` reads will be **whatever the
  cave's own computation left**, not `cmp 0x1,r16`'s result. **Fix, matching a technique this
  binary's own build process already uses** (`ADV-V289-A-ARITHMETIC-2026-09-08.md` §A5: "flags
  re-armed by `cmp 0x1,r16` @0x2A1AE before `bne` @0x2A1B4" — a note about the EXISTING code's own
  flag lifetime, confirming the discipline this new hook must also follow): the cave's LAST two acts
  before `jr 0x2A1B4` must be **(a)** replicate `st.w r7,-0x3d3c,gp`, **(b)** re-issue `cmp 0x1,r16`
  to restore the flags `bne` expects, in that order (the `cmp` must be last, since the store does not
  itself affect flags on V850 — confirmed, `st.w` is not a flag-setting instruction — so either order
  of store/cmp is flag-safe, but `cmp` must be the final instruction before the `jr`).
- **`lp`** — LIVE (the documented `0x29A2C-0x2A29A` window contains `0x2A1B0`) — **`jr` only, never
  `jarl`**, same discipline as every other hook in this function.

**DEAD scratch, confirmed free** (next access after `0x2A1B0` is a write, on every path): **`r6`**
(next write `0x2A1BE`, first act of its conditional block — safe even if the cave leaves garbage,
since every path that later reads `r6` writes it first); **`r8`** (next write `0x2A1C2`/`0x2A1CA`,
same pattern); **`r10`** (next write `0x2A212`, deep in the conditional block, never read
unconditionally before that); **`r12`** (next write `0x2A1B6`, a fresh `ld.bu`, no path reads `r12`'s
pre-hook value first); **`r13`** (next write `0x2A1D4`). **`r7` is DEAD too** — it is fully
consumed by the `st.w` at `0x2A1B0` itself (that IS its last live use) and not read again until
`0x2A1EE` freshly reloads it — so a cave may use `r7` as scratch AFTER replicating the store with its
value, or hold the store for last.

**What `cmp 0x1,r16`/`bne` selects — precise answer, correcting an over-simplification the brief's
own phrasing invited**: it does **NOT** cleanly split into "both arms reach `0x2A1E6` with `r9`=`y`."
The **bne-taken arm** (`cVar15 != 1`) always reaches `0x2A1E6` with `r9` unmodified. The
**bne-not-taken arm** (`cVar15 == 1`) enters a further 2-stage cal-flag/deadband test; **some** of
those sub-paths still reach `0x2A1E6` with `r9` unmodified (the `bgt`-taken cases at `0x2A1C8`/
`0x2A1E0`, and the `bge`-not-taken continuation through `0x2A1D2`), but **the deadband-fired sub-path
(`0x2A1E2`) sets `r9:=0` and branches to `0x2A1EE`, SKIPPING `0x2A1E6` entirely** — that sub-path
never executes the ramp multiply at all. **So `0x2A1E6` is reached by most, not all, paths out of the
`cmp`/`bne`, and on every path that DOES reach it, `r9` = `y` unmodified since `0x2A1AC`** — a hook at
`0x2A1B0` (before any of this branching) affects `y` on every path, including the ones that later get
zeroed by the deadband — this is intentional and correct, since a rate-feedback damping term added at
`0x2A1B0` should apply before Honda's own disengaged-deadband override has a chance to zero it, exactly
mirroring how the deadband already overrides everything downstream of `y`.

**Is `r9` at `0x2A1E6` already what `gp-0x6b38`/the motor path receive, apart from ×ramp/×gain/clamp?**
**YES, confirmed** by the same listing: `0x2A1E6` (`mul r14,r9,r0`) → `sar 0xf` → `sxh` → feeds into
the gain stage (`0x2A1F6 mulh r7,r13` where `r13=cal(gp-0x6752)=-1` per `ld.b -0x6752,gp,r13` @
`0x2A1F2`, and `0x2A1F8 ld.hu 0x71b4,tp,r16` = clamp `cal(0xC61B4)=3072`) → clamp @ `0x2A204-0x2A220`
→ `st.h r1,-0x6b38,gp` @ `0x2A23C`. **No other transformation exists on this path** — matches the
prior trace's Q0/existing memory `accord-gp6b38-is-the-delivered-lane-torque.md` exactly, now with
the exact gain-stage addresses cited.

**Recommendation for V290**: hook `0x2A1B0`. A band-limited rate-feedback damping term (computed
from a band-pass on `gp-0x6a56`, or reusing the V289 cave's own `n`/`y` state if design option (a) is
chosen instead — see Q1(iii)'s caution about `r26`) should be **added to `r9`** (the lag output `y`)
at this site, **after** replicating `st.w r7,-0x3d3c,gp` and **before** re-issuing `cmp 0x1,r16` as
the cave's last two acts. This lands the injection **after** the 5.05 Hz output lag (per the design
brief's option (b)), avoiding that filter's −76° phase penalty at 20 Hz (the prior trace's Q2:
`|H|≈0.242` at 20 Hz for this lag), and before the engagement ramp/gain/clamp so the term is scaled
and clamped consistently with the rest of the loop's output.

---

## Q3 — free RAM for two more int32 state words

**[EVIDENCE, raw LE Python full-image scan, script `analysis-2020accord/verify/v290_q1q3_rateop_and_ram_census.py`,
band `gp-0x6E50..gp-0x2598` (the `.data`-initialized app RAM band, per
`reference_accord_app_ram_layout_and_boot_init_loops.md`), all gp-relative forms decoded per Q1's
method, positive-controlled (5/5 PASS) before trusting the result]**

**A self-caught arithmetic bug, recorded per doctrine**: the first run of the free-run finder used
`length = start - end + 1` where `start < end` by construction (displacement increases as address
decreases in this band-walk direction) — this produces **negative lengths** for every run longer than
1 byte, and a first (buggy) pass wrongly reported **zero runs ≥ 8 bytes anywhere in the whole band**,
which would have contradicted this kit's own prior "72-byte clean run" type findings elsewhere and
was caught as implausible before being reported. Fixed (`length = end - start + 1`); re-run.

**Corrected result**: of 18,617 displacement positions in the band, **7,027 are occupied** (up from
the ~2,000-ish the earlier, `ld.b`/`st.b`-blind scanners found occupied — consistent with
`ADV-V289-D`'s own finding that the OLDER incomplete scanner's "verified free" claims for
`gp-0x68b0`/`gp-0x6ab0` were **falsified** once `ld.b`/`st.b` were added). **365 free runs total**;
**86 of them are ≥ 8 bytes.**

**The best candidate, adjacent to the V289 cave's own state (`gp-0x6c44..gp-0x6c39`)**:

```
gp-0x6D74 .. gp-0x6D2D   72 bytes, ZERO hits under the full 9-form scanner
  addr 0xFEDF128C .. 0xFEDF12D3
  boot value (u32 at the low-address end): 0x00000000
```

This is **9× the 8-byte minimum asked for**, well inside `disp16` range of `gp` from anywhere the
V289 cave already addresses (no `movea`/base-register games needed — a plain `ld.w`/`st.w
-0x6dNN,gp,rX` reaches it directly, same as the cave's own `-0x6c44` accesses). **Boots to exactly
zero** (computed from the `.data` flash source, `0x86260 + (addr - 0xFEDF11B0)` = flash offset
`0x8629C`, read directly — all-zero).

**Register-indirect / absolute-pointer check, run against this specific candidate** (the standard
this kit's prior "verified free" claims are held to, per `ADV-V289-D` §D1): (a) whole-image scan for
the literal 4-byte LE address anywhere in `[0xFEDF128C, 0xFEDF12D3]` landing at ANY byte alignment —
**zero hits**; (b) `movhi 0xFEDF/movea` proximity scan (a `movhi` building the `0xFEDF____` high half,
followed within 16 bytes by a `movea` whose low-16-bit immediate falls in `[0x128C,0x12D3]`) —
**zero hits** (433 `movhi 0xFEDF...` sites exist image-wide; none pairs with a `movea` landing in this
run). (c) Ghidra cross-check: `search_instructions operand_pattern:"6d2d"` → 0 matches;
`"6d70"`/`"6d74"` → matches exist but are **all branch-target digit coincidences** (`0x36D70`,
`0x36D74`, `0x6D5EA`/`0x6D744` — jump targets in unrelated functions `FUN_00036c12`/`FUN_0006d5da`,
not gp-relative accesses to this cell), the same false-positive class as Q1. **Not a mathematical
proof** (the same residual this kit's own `gp-0x1500` precedent already accepts for every "free cell"
finding — a sufficiently indirect computed-pointer chain is never fully excludable by static
scanning) — but every check this session's toolset supports was run, and all pass clean.

**Two more, smaller, useful candidates near the cave** (both boot to 0, same checks not individually
re-run to the full standard above — flagged as a residual, per the honest-reporting doctrine this
kit uses):
```
gp-0x692E .. gp-0x6927   8 bytes    addr 0xFEDF16D2..0xFEDF16D9   boot u32 = 0x00000000
gp-0x6B8E .. gp-0x6B8B   4 bytes    addr 0xFEDF1472..0xFEDF1475   boot u32 = 0x00000000
```

**Immediate neighbours of the cave's own state, individually probed** (the brief's specific ask,
"is `gp-0x6c48`/`gp-0x6c4c` really occupied, by whom"):
```
gp-0x6c48: 9 raw hits   (e.g. 0x18B10 ld.w)   -- OCCUPIED
gp-0x6c4c: 2 raw hits   (e.g. 0x319CA ld.w)   -- OCCUPIED
gp-0x6c50: 2 raw hits   (e.g. 0x31944 ld.w)   -- OCCUPIED
gp-0x6c54: 3 raw hits   (e.g. 0x31D04 st.w)   -- OCCUPIED
gp-0x6c38: 2 raw hits   (e.g. 0x4172E st.h)   -- OCCUPIED
gp-0x6c34: 6 raw hits   (e.g. 0x2DE12 ld.h)   -- OCCUPIED
gp-0x6c30: 0 raw hits                          -- FREE (isolated single displacement — not a
                                                    2+ word run by itself)
```
**YES — the cave's immediate neighbours (`gp-0x6c48`/`gp-0x6c4c`/`gp-0x6c50`/`gp-0x6c54`/`gp-0x6c38`/
`gp-0x6c34`) are genuinely occupied**, each by a different, unrelated function — confirming the prior
trace's own "densely packed, shared linker-pooled statics" finding for this immediate neighbourhood.
**The nearest usable free run is `gp-0x6D2D..gp-0x6D74`, about 0x2E9 bytes away** — not adjacent, but
well within any single instruction's `disp16` reach from wherever a V290 cave's own code lives.

**Note on falsified prior candidates**: `gp-0x6ab0..gp-0x6aaa` and `gp-0x68b0..gp-0x68aa`, which an
earlier tracer session called "fully verified free," are **confirmed occupied by this session's own
scan too** — e.g. `gp-0x6aa9..gp-0x6ab0` (overlapping the old candidate) shows boot value
`0x02880288` (non-zero, i.e. genuinely initialized `.data`, not bss). **Do not use those two cells**
for V290 — this is a re-confirmation of `ADV-V289-D`'s own falsification, not a new finding.

---

## Q4 — the V289 cave itself, `0xC4C00-0xC4C8C`

**[EVIDENCE, `disassemble_bytes dry_run:true` on the imported V289 program, full 53-instruction
listing, cross-checked against `ADV-V289-A-ARITHMETIC-2026-09-08.md`'s own independent decode —
agrees on every instruction]**

**At `0xC4C3A` (`sub r6,r9`)**:
```
0xC4C38  mov r12,r9      ; r9 := x  (x = S, the clamped loop sum, passed in via r12 from the 0x2A174 hook)
0xC4C3A  sub r6,r9       ; r9 := r9(x) - r6  =>  r9 = n = x - y
```
**`n` = `r9`** (after this instruction). **`y` (linear, pre-clamp)** = `r6`, formed earlier at
`0xC4C1A-0xC4C1C` (`mov r9,r6 ; sar 0xe,r6` — the TDF-II accumulator `acc>>14`, floored). **`x` = `S`**
= `r12`, **unchanged since cave entry** — `r12` is not written again until `0xC4C52` (`mov r6,r12`,
deep inside the FLAG-byte computation, where it is overwritten with `y` in preparation for the final
clamp). So immediately after `0xC4C3A`: `n`→`r9`, `y`→`r6`, `x`(=S, now dead/unused further)→`r12`.

**Free registers between `0xC4C46` and the clamp at `0xC4C72`, for "two extra instructions"**:
walked every instruction in this span reading/writing `r6`/`r7`/`r9`/`r13`:
- **`r13`**: LIVE-then-reused with **zero gap** — it's the store source at `0xC4C46`
  (`st.w r13,-0x6c44,gp`) and is overwritten immediately at the very next instruction (`0xC4C4A: mov
  0x0,r13`), becoming the FLAG accumulator for the rest of the block through `0xC4C6E`. **Not free.**
- **`r6`**: LIVE throughout — used at `0xC4C52` (copied into `r12`), then again at `0xC4C5C`/`0xC4C60`
  (forming `|y|`) and `0xC4C62` (`cmp r6,r7`, the `|n|>=|y|` FLAG bit b7). **Not free anywhere in this
  span.**
- **`r7`**: **FREE from `0xC4C46` to `0xC4C54`** — its last live use before this span was consumed by
  the `st.w` at `0xC4C34` (storing `s2'`); it is not read again until `0xC4C54` freshly assigns it
  (`mov r9,r7`). **8 bytes / up to 4 short instructions of headroom here.**
- **`r9`**: **FREE from `0xC4C56` to `0xC4C72`** — `n` (its value since `0xC4C3A`) is last read at
  `0xC4C54` (copied into `r7`); `r9` is not touched again until `0xC4C72` freshly reloads the clamp
  limit (`ld.hu 0x71be,tp,r9`). **~28 bytes / up to ~7 short instructions of headroom here — the
  larger of the two windows**, and it sits immediately before the clamp, a natural place to fold in
  an extra damping term on `y`/`r12` before it gets clamped.

**Two extra instructions fit comfortably in either gap** (`r7`'s 4-instruction window right after
`0xC4C46`, or `r9`'s larger window right before `0xC4C72`); **`r6` and `r13` offer no such gap**
without save/restore.

**Output clamp**: `0xC4C72: ld.hu 0x71be,tp,r9` — **confirmed, `tp+0x71BE = 0xBF000+0x71BE = 0xC61BE`**,
the same sum-clamp cell (15360) the main loop uses on `S` before the V289 cave ever sees it — i.e.
the notch's OWN output clamp reuses the identical cal cell as the pre-notch sum clamp (a design
choice already documented in `ADV-V289-A` A2/A3, not a new finding here, re-confirmed by address).

---

## Q5 — free flash after the cave

**[EVIDENCE, fresh Python read, V289 image, region `[0xC4C8C, 0xC5000)`]**

```
region [0xC4C8C, 0xC4FF0): 868 bytes, ALL 0xFF (0 non-0xFF bytes) — confirmed by exhaustive scan, not sampling
bytes at 0xC4FF0..0xC4FFB (12 bytes, verbatim): 01 01 01 01 00 00 c6 00 13 00 b2 00
CRC trailer 0xC4FFC..0xC5000: a7 61 1f 82   (LE u32 = 0x821F61A7, block [0xC4000,0xC5000))
```

The 12-byte structure is **byte-identical** to the one the V288 rev 2 trace already found and left
untouched (`docs/traces/TRACE-2026-09-08-...` Q5: "identical to the pre-existing 12-byte unidentified
structure the V288 spec already found and left untouched") — still unidentified, still not disturbed
by V289. **868 bytes free** for a V290 cave extension, more than enough for a damping-term subroutine
plus a band-pass filter's coefficients/state-touching code (the RAM itself is separate, per Q3).

---

## Summary for `design290` / `main`

| Q | headline |
|---|---|
| Q1(i) | `gp-0x6a56` has **4 writers** (all in `FUN_0003F776`), **25 readers** (raw scan found 5 Ghidra's `search_instructions` missed — a real undercount, now closed). Writers are in a different function from the fb filter/cave; **same-tick freshness is BELIEF, not proven** — inter-function tick ordering was not established. |
| Q1(ii) | `ld.h` (signed) at the fb filter, no width/sign mismatch anywhere on this cell (all 25 readers use `ld.h`). `−(0x18F rate)×8/deg/s` claim cited, not re-measured; a new address (`0x51150E`, `>>3`) plausibly pins the CAN-packer read the claim already named. |
| Q1(iii) | **`r26` is REWRITTEN at `0x29F76` on the main engaged path** (LERP scratch, not feedback) — **CORRECTS an implicit gap in the prior trace**: `r26` at `0x2A174` is NOT the filtered feedback on the common path. It IS still the feedback on the (very likely dead) `0x2A0C6` lane. **A V290 cave must not read `r26` for feedback** — use `gp-0x3d30` (the fb filter's private state) instead. |
| Q2 | Chosen post-lag hook: **`0x2A1B0`** (`st.w r7,-0x3d3c,gp`, 4 bytes, unconditional every tick). LIVE: `r9`(=y, the injection target), `r14`(ramp), `r11`(long-lived), **PSW flags from `cmp 0x1,r16`@0x2A1AE** (a NEW hazard this session found — the cave must re-issue `cmp 0x1,r16` as its last act before `jr`-ing back), `lp`(jr-only). DEAD/scratch: `r6,r7,r8,r10,r12,r13`. `0x2A1E6`'s `r9` is confirmed the exact pre-ramp/gain/clamp value that reaches `gp-0x6b38`. |
| Q3 | Best free-RAM candidate: **`gp-0x6D74..gp-0x6D2D`, 72 bytes, boots to 0, zero absolute/`movhi`+`movea`/bit-op hits** — 9× the minimum needed, ~0x2E9 bytes from the cave (not adjacent; the cave's immediate neighbours `gp-0x6c48/4c/50/54/38/34` are all confirmed OCCUPIED). Two smaller candidates also found. The previously-claimed `gp-0x6ab0`/`gp-0x68b0` candidates are RE-CONFIRMED occupied (falsified, matching `ADV-V289-D`). |
| Q4 | At `0xC4C3A`: `n`→`r9`, `y`→`r6`, `x`(S)→`r12` (dead after). Free scratch for 2 extra instructions: `r7` (right after `0xC4C46`) or `r9` (right before `0xC4C72`, the larger window); `r6`/`r13` are never free in this span. Output clamp confirmed `tp+0x71BE = 0xC61BE = 15360`. |
| Q5 | **868 bytes of `0xFF`** confirmed `[0xC4C8C,0xC4FF0)`; the 12-byte tail structure at `0xC4FF0` is `01 01 01 01 00 00 c6 00 13 00 b2 00`, byte-identical to the pre-V289 record. |

## Open questions / verification needed
1. **Q1(i) same-tick ordering** — BELIEF only. Next step: locate `FUN_0003F776`'s and
   `FUN_00028ea6`'s registration in the RTOS dispatch table near `0xBB920`, or a build-time probe
   comparing tick counters.
2. **Q1(iii)'s design-scope note** (how to reconstruct the exact clamped feedback sum from
   `gp-0x3d30` or from re-filtering raw `gp-0x6a56`) is flagged, not solved — out of this brief's
   tracing scope, a design task for `design290`.
3. **Q3's two smaller candidates** (`gp-0x692E..gp-0x6927`, `gp-0x6B8E..gp-0x6B8B`) were not run
   through the full absolute-pointer/`movhi`-`movea` check the primary 72-byte candidate received —
   only the primary candidate is certified to that standard; use it unless a design reason prefers
   one of the smaller, closer ones (which would need that check run first).

## Files
- This trace.
- `analysis-2020accord/verify/v290_q1q3_rateop_and_ram_census.py` — the raw LE decoder/census script
  (Q1 + Q3), positive-controlled, with the `jr`/`jarl` vs `ld.bu` opcode-0x3C/0x3D discriminator bug
  found and fixed in-session (recorded in the script's own comments).
