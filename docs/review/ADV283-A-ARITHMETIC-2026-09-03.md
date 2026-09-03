# ADV283-A — Arithmetic adversarial pass on V283 (LKAS rate-PID Ki 0→50)

**Adversary:** adv283a. **Job:** make V283 FAIL on arithmetic. **Verdict: PASS.**

Image under test: `_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
(sha256 `fd0c321a…`) vs base V282 (sha256 `0ea98d06…`). Tool: GhidraMCP on `code.bin` (stock, fully
analysed, 2086 functions) for structure/decompile/pcode, cross-checked with raw Python byte scans per
the `firmware-decompile` skill. All addresses below are EVIDENCE (Ghidra decompile/disasm/pcode or a raw
byte read), not inference, unless marked BELIEF.

## What a FAIL would have looked like (written before opening Ghidra)
Any of: excess/E not correctly sign-extended on one side of the deadband; `mul` vs `mulu` corrupting the
retained low-32 product; a `>>` that turned out to be logical (`shr`) instead of arithmetic (`sar`) on a
signed operand; the cmovgt/cmovle clamp saturating to the wrong sign; `acc_new<<3` overflowing s32; the
accumulator persisting across a disengage/re-engage (windup); a non-zero I term reaching an
EME/plausibility/lockstep consumer through the shared clamp cal or a telemetry cell; or a bad CRC/rwd
that wouldn't even flash.

## 1. Byte diff (EVIDENCE — Python, full-file, both images identical length)
Exactly 5 bytes differ between V282 and V283, both `[0x13000,0x100000)`:
```
0xC63E6  00 -> 32 (decimal 0->50)      -- Ki cal, one byte of the u16 (high byte 0xC63E7 unchanged, =0)
0xC6FFC  72 -> 0C
0xC6FFD  DF -> D6
0xC6FFE  EA -> C4
0xC6FFF  75 -> 40                      -- page CRC trailer for block [0xC6000,0xC6FFC)
```
No other byte moved. The code region `0x29D6C-0x2A190` (the whole PID) is byte-identical across V282,
V283 and stock `code.bin`.

## 2. CRC (EVIDENCE — kit's own `verify_bootloader_crc.py`, run against the actual V283 image)
Both the bootloader-replay walk (49 blocks, the `0xC6000` bridge) and the full-chain walk (50 blocks,
including `[0xC5000,0xC5FFC)`) **PASS with 0 mismatches** on V283. Block 48 `[0xC6000,0xC6FFC)`
(`calc=0x40C4D60C stored=0x40C4D60C OK`) confirms the recomputed trailer at `0xC6FFC` is valid, not just
different. The image will pass its own integrity check.

## 3. The deadband / excess computation (`E = 32·sp − fb`, `excess = deadband(E>>5, 0xC62E4)`)
Disassembled `0x29d70-0x29d9c` directly (dry_run):
```
29d76 shl 0x5,r16      ; r16 = 32*sp
29d78 sub  r26,r16     ; r16 = 32*sp - fb   = E
29d7c sar  0x5,r6      ; r6  = E>>5          ARITHMETIC shift (sar, not shr)
29d7e cmp  r10,r6
29d82 ble  0x29d8c
29d84 ld.hu 0x72e4,tp,r9 ; deadband cal (0xC62E4)
29d88 subr r6,r9        ; excess = (E>>5) - deadband      [E>>5 > deadband case]
29d8a br   0x29d9c
29d8c ld.hu 0x72e4,tp,r13
29d90 subr r0,r13        ; r13 = -deadband
29d92 cmp  r13,r6
29d94 bge  0x29d9c        ; within deadband -> excess stays 0
29d96 ld.hu 0x72e4,tp,r9
29d9a add  r6,r9          ; excess = (E>>5) + deadband      [E>>5 < -deadband case]
```
**Both signs of the deadband are handled** (0x29d84-8a for the positive side, 0x29d8c-9a for the
negative side); the brief's concern #1 ("a branch that only handles the positive side") does not hold.
`E>>5` uses `sar` (arithmetic), so a negative `E` is correctly sign-preserved before the compares.
`excess` (r9) is a genuine signed 32-bit two's-complement value going into the multiply — no truncation
or zero-extension anywhere in this chain.

## 4. `mul r6,r9,r0` (Ki·excess) — signed vs unsigned is a non-issue here
`29da8: mul r6,r9,r0` — r6=Ki (zero-extended via `ld.hu`, always ≥0), r9=excess (signed). V850 `mul`
is the *signed* 32×32→64 form (dest r0 for the discarded high word — r0 is hard-wired zero, i.e. the
high word is thrown away, not read anywhere). **This matters less than it looks**: for a 32×32→32
truncated multiply, the retained low 32 bits are bit-identical whether the operands are interpreted as
signed or unsigned (two's-complement multiplication is a ring homomorphism mod 2³²). So even if this
were `mulu`, the value stored back into r9 would be unchanged. Confirmed via p-code
(`get_function_pcode`-equivalent `analyze_dataflow`): `INT_MULT(r9,r6)` feeding directly into
`INT_SRIGHT(...,3)` — a single 32-bit truncated multiply, matching the builder's "mul, low32 kept"
claim. **Not a bug.**

## 5. Every `>>3`/`>>7` in the chain is arithmetic, not logical (EVIDENCE — asm mnemonic + raw p-code)
```
29dae sar 0x3,r13   ; bound = (clamp_cal<<10)>>3
29db0 sar 0x3,r10   ; acc_old>>3
29db2 sar 0x3,r9    ; prod>>3
29f18 sar 0x7,r2    ; I_term = acc_new>>7
```
For the I-term extraction specifically, `analyze_dataflow` on `0x29f18` resolved the op as
`INT_SRIGHT` (Ghidra's *signed* right-shift p-code op), not `INT_RIGHT` (logical) — this is Ghidra's
own semantic reconstruction, not just a mnemonic string, so it is strong evidence the underlying
hardware shift is arithmetic. `acc_old` (`ld.w`, full 32-bit signed) and the product both stay correctly
signed through every division-by-power-of-2 in this chain. **Not a bug.**

## 6. The clamp (`cmovgt`/`cmovle`) — traced at the instruction level, symmetric and correct
```
29db4 add    r9,r10        ; r10 = unclamped sum = acc_old>>3 + prod>>3
29db6 cmp    r13,r10       ; flags = r10 - bound
29db8 cmovgt r13,r2,r2      ; r2 = (r10>bound) ? bound : r2        [r2 unread if not taken -- see below]
29dbc bgt    0x29dc6         ; if clamped-high, done -- skip the rest
29dbe subr   r0,r13         ; r13 := -bound
29dc0 cmp    r13,r10         ; flags = r10 - (-bound) = r10+bound
29dc2 cmovle r13,r10,r2       ; r2 = (r10<=-bound) ? -bound : r10   [r10 = the REAL unclamped sum]
```
This is a standard two-`cmov` saturating clamp: `r2 = clamp(r10, -bound, +bound)`. The apparent
oddity at `29db8` (`cmovgt r13,r2,r2` — reg2==reg3==r2, i.e. "keep r2's prior value if not taken") is
**not a bug**: in the not-taken (`r10<=bound`) path, execution always falls through to `29dc2`, which
*unconditionally* overwrites r2 with either `-bound` or `r10`. r2's pre-`29db8` value is provably dead
in that path — it is never read before being redefined. Confirmed the clamped value (r2) is exactly
what feeds the I-term extraction: `analyze_dataflow` backward from `0x29f18`'s `sar 0x7,r2` terminates
at the `MULTIEQUAL` (phi) for r2 at `0x29dc6`, which merges precisely the two clamp exits (`29db8`
taken / `29dc2` fallthrough). **I initially mis-read the Ghidra-decompiled C boolean soup for this
clamp as possibly inverted (a mid-derivation p-code register-version tracking mistake on my part,
conflating pre- and post-`subr` values of r13); re-grounding in the raw asm — which is unambiguous —
resolved this. Flagging the near-miss for the record: don't trust the decompiler's synthesized
`bVarN` overflow-flag booleans over a clean cmov/branch trace for a clamp.** Verdict: clamp is correct,
symmetric, no wrong-sign saturation.

## 7. `acc_new<<3` overflow — checked, does not overflow s32
`bound = (10240<<10)>>3 = 1,310,720`. `acc_new<<3` (restoring to the stored scale) has max magnitude
`1,310,720 × 8 = 10,485,760`, far inside signed-32 range (±2.147×10⁹). **No overflow.**

## 8. Accumulation rate — sanity magnitude, not bit-exact (BELIEF, order-of-magnitude only)
Taking the brief's own sizing (`|excess|` up to ≈2400, from `E ≤ 77k>>5`, not independently re-derived
by me this pass): `prod>>3 ≈ excess·50/8 ≈ 15,000` per tick against `bound = 1,310,720` — roughly 87
ticks of sustained max excess to saturate the integrator from zero. This is a slow ramp, not an
instant-saturation profile; nothing here suggests a scaling mismatch large enough to be an arithmetic
defect (as opposed to a tuning choice, which is out of this pass's scope).

## 9. Reset path / anti-windup — a real, unconditional-store reset exists (EVIDENCE)
`get_xrefs_to(0x2a164)` → two `UNCONDITIONAL_JUMP` sources, `0x29a5c` and `0x29a64`, both inside
`FUN_00028ea6` — these are the taken-arm of the function's top-of-function engagement/plausibility gate
(the `if` the earlier decompile shows testing `gp-0x6752`, `gp-0x4f60`, `gp-0x6a56` bounds — consistent
with existing kit record on this gate; I did not re-derive the gate's semantic meaning from scratch this
pass, so that specific mapping is BELIEF, not re-verified EVIDENCE). At `0x2a164` the reset code sets
`r24=0` (among others: r29,r27,r22=0, r16=0x7fffffff) and falls through to the SAME merge point
(`0x2a174`, a `MULTIEQUAL`/phi for r24) as the normal engaged path. From `0x2a174` to the store at
`0x2a190` (`st.w r24,-0x6dd0,gp`) the code is straight-line with **no branches** — the store is
**unconditional** every call, confirming the brief's claim. Net effect: **every tick the gate is false,
the accumulator is forced to 0 and written back**; windup cannot survive a disengage/re-engage cycle.
Boot-time initial value (before the very first gate evaluation ever runs) was **not verified this
pass** — open item, though it is very likely covered by the same reset path since the engagement gate
is almost certainly false immediately after power-up. **Needs**: confirm RAM zero-init or the very-first
tick's gate state if this is to be closed as EVIDENCE rather than BELIEF.

## 10. Cal `0xC61BA` (I clamp) outside readers — CORRECTION OF RECORD, does not block V283
The brief (and the build script's own docstring, `KI_CLAMP = 0xC61BA # ... 3 outside readers per kit
record`) states three outside readers at `0x36ABA`, `0x3BCC2`, `0x5AAFC`. Checked directly:
- `get_function_by_address` on each address resolves to `FUN_00036828` (343 instrs), `FUN_0003bcb2`
  (46 instrs), `FUN_0005aae0` (19 instrs) — all small, fully-scanned functions.
- `search_instructions` scoped to each function for operand `71ba` (tp+0x71ba = 0xC61BA): **0 matches
  in all three.** Positive-controlled: the same scan for a known-present operand (`73d4`) in
  `FUN_00036828` found it immediately, so the null is not a scan artifact.
- Independent raw Python byte scan across the full 1MB image, honoring the `hw2=disp|1` encoding for
  `ld.hu` (per the `firmware-decompile` skill), for the disp16 form of `tp+0x71ba`: **exactly 2 hits**,
  `0x29da0` (the live PID, `FUN_00028ea6`) and `0x2aca0` (the dead twin, `FUN_0002a93a`). No others in
  the entire image.

**Conclusion: 0xC61BA has zero readers outside this PID and its dead twin**, not three. This does not
affect V283's correctness (0xC61BA is byte-unchanged by this build), but the "3 outside readers" belief
in the kit record / build docstring appears stale or mistaken and should be corrected or re-verified
before it is used to justify NOT moving that cal in a future build.

## 11. Dead twin `FUN_0002a93a` — confirmed dead, cannot compete for the accumulator
`get_function_callers("FUN_0002a93a")` → **no callers**. Its `gp-0x6dd0` accesses (`0x2ac96` read,
`0x2b05c` write) and its `0xC61BA` read (`0x2aca0`) are unreachable dead code; they cannot race or
interfere with the live accumulator.

## 12. `0x59B90` — confirmed NOT a reader of the Ki cal (EVIDENCE, with a self-caught near-miss)
Proper Ghidra disassembly (`disassemble_bytes`, dry_run) of `0x59b88-0x59b9f`:
```
59b90: ld.h -0x4ec2, gp, r14      ; 6-byte extended gp-relative form
59b96: sar 0x8, r14
59b98: sst.b r14, 0x5, ep          ; part of an unrelated CAN packer
```
This reads `gp-0x4ec2` (a GP-relative cell, different base register/space entirely), not
`tp+0x73e6`. `search_instructions` for `73e6` inside `FUN_00059912` (the containing function): 0
matches. **Confirms the builder's own claim.** Note for the record: my first pass at this address was a
hand-decoded 4-byte guess from raw bytes that looked like it might hit `tp+0x73e6` — exactly the
"never hand-decode from raw bytes" trap the `firmware-decompile` skill warns about. Ghidra's own
disassembler immediately showed it as a 6-byte instruction at a different displacement; the manual
guess was wrong. Recorded here as a live demonstration of the trap, not as a finding about V283.

## Verdict
**PASS.** No sign/width/overflow/clamp-direction defect found in the integrator arithmetic itself. The
CRC is valid on the actual built image (both bootloader-replay and full-chain walks). The reset path is
real, unconditional-store, and prevents windup from persisting across a disengage/re-engage. One
correction of record (item 10) — informational, does not block this build. One open item (item 9,
boot-time initial state) — does not by itself justify DO-NOT-FLASH given the per-tick reset already
found, but is the concrete next thing to check if anyone wants to close it out as full EVIDENCE.

## Open questions / next verification step if pursued further
1. Boot-time value of `gp-0x6dd0` before the first gate evaluation (RAM zero-init timing vs first
   engage) — would need a boot/init-routine trace, not done this pass.
2. The gate condition at the top of `FUN_00028ea6` (`gp-0x6752`, `gp-0x4f60`, `gp-0x6a56` bounds) was
   read from decompile text and cross-referenced against existing kit memory, not independently
   re-derived bit-by-bit this pass — if its meaning is load-bearing elsewhere, re-verify directly.
3. The extended 6-byte gp/tp-relative encoding form was not exhaustively scanned for `0xC61BA` or
   `gp-0x6dd0` (only the disp16 form was raw-scanned); given the extremely small, page-adjacent
   displacements involved this is a low-probability gap, but not a zero-probability one.
