---
name: reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism
description: gp-0x6b9a in FUN_00034a72 is a GATE INPUT only (one of 5 signals in a composite plausibility check producing flag r21), never a value/index -- corrects build_v58_tva.py's "FIR chain output indexing 0xD28DC" claim on two counts. Also discovers FUN_0003b66a's fault-sentinel protocol (+32767/-1 on implausible inputs) that r21's gate exists to catch. WARNING - this file's "float biquad / IIR" claim is WRONG and was retracted by the team lead; see the correction header below.
metadata:
  type: reference
---

# `gp-0x6b9a` in `FUN_00034a72`: gate input, not index; `0xD28DC` is NOT reachable via `0xca23c` (2026-07-30, team-lead request)

> 🛑 **CORRECTION, 2026-07-30, by the team lead after independent byte verification.** The two headline
> findings in this file — `gp-0x6b9a` is a gate input not an index, and `0xD28DC` hangs off `0xca4f4`
> not `0xca23c` — are **CONFIRMED** and were re-derived independently. **Two other claims are WRONG:**
>
> 1. **"Branch A is a genuine floating-point 2-pole biquad… IIR by definition" — NO.**
>    `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)** and the code is
>    `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states (`gp-0x365c`, `gp-0x3658`).
>    Persisted input delays are a **delay line, not feedback**; stateful ≠ recursive. It is the identity
>    3-tap FIR already on record in `BUILD-LINEAGE.md`, and it is a pass-through. There is **no new notch
>    candidate here** and `STATE.md`'s "no biquad anywhere" survives.
> 2. **The sole-writer enumeration rested on `search_instructions` alone.** Right answer, wrong method —
>    a Python byte scan for both gp-relative encodings finds **9** access sites where that tool reported
>    8 (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). CLAUDE.md flags this exact
>    undercount. Never rest a writer/reader set on it alone.
>
> Also missed: `tp+0x74be = 0` (`0xC64BE`) makes `0x3b736–0x3b758` (the `divf.s` block) **dead code**.
> And the consequence this file did not draw: `gp-0x6ba6 == |gp-0x6b9a|`, so it is the **rectification**
> of the signal V58 watched oscillate — that is the mechanism, and it is why V59 exists.
> See `memory/accord-gp6ba6-is-the-boost-amplitude-index.md`.

Answers team-lead's 6-part ask, verifying/extending [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]
and [[reference_accord_gp6bbe_angle_rate_path_traced_net_damping]] (same function, prior session) against
fresh disassembly this session. Both Ghidra (`read_memory`) and an independent PowerShell/.NET byte read of
the raw stock `code.bin` were used for every table dump (dual-method, since this is load-bearing) -- both
agree bit-for-bit across all 204 entries checked (6 tables x 34 modes).

## Headline verdict for team-lead

**`build_v58_tva.py`'s description of `gp-0x6b9a` ("the FIR chain's output, indexing boost's NON-flat table
0xD28DC") is WRONG on both counts it makes:**
1. `gp-0x6b9a` does not index anything in `FUN_00034a72` -- it is consumed ONLY as one of five inputs to a
   composite plausibility/validity gate (flag `r21`); the register that indexes both LERP1 and LERP4 is `r9`,
   sourced from `gp-0x6ba6` (a DIFFERENT cell -- the unsigned/abs magnitude sibling), not `gp-0x6b9a`.
2. `0xD28DC` IS a real table (LERP1, mode 10), but it is reached via pointer table `0xca4f4`, **not**
   `0xca23c` (which resolves to `0xD2888` at mode 10 -- a different table entirely). `0xD28DC` does not
   appear anywhere in `0xca23c`'s 34-mode array (byte-verified, both methods).
`gp-0x6b9a` is therefore **not established as a lever via this description** -- any build targeting "the
0xD28DC boost table via gp-0x6b9a" is targeting the wrong variable/table pairing.

## Q1 -- gp-0x6b9a reaches the r21 gate only, never a value path [EVIDENCE, full disasm 0x34a72-0x35153]

Three loads of `gp-0x6b9a` into `r15`, all confirmed by fresh `disassemble_function` + independently by
`search_instructions` (8 total hits for "6b9a" image-wide, `truncated:false`):
- `0x34b5e`, `0x34b68` -- in the mode!=1 fallback branch (dead in stock cal, `tp+0x6499`=1 always taken --
  see [[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]])
- `0x34b72` -- in the live mode==1 branch, alongside `0x34b6e: ld.hu -0x6ba6[gp],r9`

All three converge at `0x34b76` with `r15=gp-0x6b9a` (raw), `r9`=index (gp-0x6ba6 in the live path). `r15` is
then used ONLY here:
```
0x34c9c  addi 0x6400,r15,r6      ; r6 = gp-0x6b9a + 25600   (consumes r15's VALUE, once)
0x34ca4  ori 0xc801,r0,r15       ; r15 OVERWRITTEN with constant 0xc801 -- gp-0x6b9a is dead from here on
0x34cb0  cmp r15,r6 / 0x34cb4 bnc 0x34ce2   ; range check (see Q2)
```
`r15` never reaches `0x34ffa` (the final `term3` multiply) as a value. Team-lead's own reading is CONFIRMED
correct.

## Q2 -- the range test is SYMMETRIC, |gp-0x6b9a| <= 25600 counts, and is one of FIVE conjoined checks [EVIDENCE, derived from carry-flag semantics]

Full composite gate, `0x34c9c`-`0x34cdc`, all via the same "add K, cmp-vs-2K+1-ish, bnc/bc" symmetric-window
idiom already established elsewhere in this function (the angle-rate +-12000 validity check at
`0x34aca`-`0x34ae6`, independently re-derived this session to confirm the idiom):
1. `0x34c9c-cb4`: `|gp-0x6b9a| <= 25600` (0x6400) -- derived by carry-flag analysis: `cmp r15(0xc801=51201),r6`
   sets CY (borrow) iff `r6(unsigned) < 51201`; combined with the ADDI-produced wraparound behavior for
   negative `gp-0x6b9a`, this is exactly `-25600 <= gp-0x6b9a <= 25600` (symmetric, not asymmetric).
2. `0x34cb6-cbe`: `gp-0x6ba6 <= 25600` (already an unsigned magnitude by construction, `ld.hu`)
3. `0x34cc0-cc8`: `gp-0x4f68 <= 25600` (unsigned torque-related threshold cell)
4. `0x34cca-cd0`: `|gp-0x4f60| <= 25600` (raw driver column torque)
5. `0x34cd2-cdc`: `setfc r21` on `cmp(0xfa01=64001, gp-0x6c2e+32000)` -- `|gp-0x6c2e| <= 32000`ish (same idiom,
   result directly becomes `r21` rather than a branch)
`r21 = 1` iff ALL FIVE pass; any failure branches early to `0x34ce2: mov 0x0,r21`. **`gp-0x6b9a` is one of
five gated signals, not a dedicated gate for itself.**

## Q3 -- pointer tables fully dumped, `0xD28DC` confirmed reachable ONLY via `0xca4f4` [EVIDENCE, dual method]

All 6 tables x 34 modes (0-33) read via Ghidra `read_memory` AND independently via a PowerShell `[BitConverter]`
read of `C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin` --
identical results both methods:
- **`0xca23c` (LERP4)**: mode10 -> `0xD2888`. Full mode 0-33 range: `0xCE5B0..0xCF5CC` (modes 0-3, distinct
  layout), then repeating triples `0xD0888/0xD08A4/0xD08C0`, `0xD1888/...`, ..., `0xD9888/0xD98A4/0xD98C0`
  (modes 4-33). **`0xD28DC` does NOT appear anywhere in this table.**
- **`0xca4f4` (LERP1)**: mode10 -> `0xD28DC` (confirmed, the ONLY hit for `0xD28DC` across all 6 tables x 34
  modes). Full range: `0xCE5E8..0xCF604` (modes 0-3), then triples `0xD08DC/0xD08F8/0xD0914`, ...,
  `0xD98DC/0xD98F8/0xD9914` (modes 4-33).
- `0xca154` (LERP3, Y3/speedLERP1 index): mode10 -> `0xD2834` (matches prior memory's "Table A" exactly).
- `0xc7970` (LERP5, Y5/speedLERP2 index): mode10 -> `0xD20C0` (matches prior memory's "Table B" exactly;
  `0xC7998` cited in that memory = `0xc7970+4*10`, the mode-10 SLOT ADDRESS, not a different table).
- `0xca06c` (Y1-blend coeff): mode10 -> `0xD2006` = **102** (byte-dumped, matches prior memory).
- `0xca40c` (mode-gain byte): mode10 -> `0xD2012` = **128** (byte-dumped, matches prior memory, =1.0 exactly
  since 128/128).
Y-table contents (dumped per the LERP struct format in [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]],
count-dependent Y-base = 2+2*count): LERP1 `0xD28DC` count=6 X=[0,512,1490,2529,3645,5120]
Y=[16384,14657,11672,9365,8244,8187]; LERP4 `0xD2888` count=6 X=[0,307,1024,1741,3072,6144]
Y=[16384,14392,10265,8997,8176,8176] -- both match the prior-session memory exactly, now re-derived fresh via
two independent methods.

## Q4 -- r9 (the shared LERP1/LERP4 index) is gp-0x6ba6, round-tripped through scratch cell gp-0x6bba [EVIDENCE]

`r9` is set once at `0x34b6e` (`ld.hu -0x6ba6[gp],r9`, live mode==1 path) or via the dead fallback branch, then
immediately saved to a SCRATCH RAM CELL: `0x34b8e: st.h r9,-0x6bba[gp]`. The intervening 4-state debounce FSM
(`0x34d40-0x34e8a`, gp-0x682e) clobbers `r9` internally in several exit paths, so **every one of its ~6 exit
points reloads `r9 = gp-0x6bba`** before falling through to the rate-error computation (e.g. `0x34dbe`,
`0x34dd8`, `0x34e2e`, `0x34e68`, `0x34e82` -- all `ld.hu -0x6bba[gp],r9`). `r9` is untouched from the last FSM
reload through `0x34f5e-fc4`'s second table walk (LERP4), where `0x34f78: cmp r11,r9` uses it directly as the
index. **`gp-0x6bba` is a scratch relay cell for `gp-0x6ba6`'s value across the FSM, not an independent
signal** -- both LERP1 and LERP4 are keyed by the SAME `gp-0x6ba6` value.

## Q5 -- gp-0x6b9a's sole writer is FUN_0003b66a@0x3b8b0; it is NOT an "FIR chain" -- two cascaded IIR branches, one a float biquad; discovers a FAULT-SENTINEL protocol [EVIDENCE, fresh full disasm]

Confirmed via `search_instructions` (8 hits for "6b9a", `truncated:false`) AND fresh `disassemble_function` on
`FUN_0003b66a` (`0x3b66a-0x3b8f2`) -- reused from [[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]],
now re-verified with the full instruction listing:
- **Three input-validity gates at function entry** (`0x3b67a-82`: `|gp-0x4f60|<=25600`; `0x3b686-94`: a
  `gp-0x6abc`(motor-rate) window; `0x3b6a8-b8`: `|gp-0x4f62|<=25600`) -- SAME symmetric-window idiom as
  `FUN_00034a72`'s r21 gate. **If ANY fails, jump to `0x3b87e`: `r13=0xFFFF`(-1), `r28=0x7FFF`(+32767) --
  FAULT SENTINELS, not zero.** This is a new finding not in prior memory sessions.
- **Branch A** (`0x3b6bc-0x3b7b6`): genuine FLOATING-POINT 2-pole biquad (`mulf.s`/`maddf.s`/`divf.s`/
  `cvtf.ws`, coefficients `tp+0x5018/0x501c/0x5020`, recursive state `gp-0x365c/-0x3658` etc, read-modify-write
  every call -- this is IIR by definition, not FIR) combined with a torque-ratio term (`gp-0x4f62/gp-0x4ebc`,
  gated `tp+0x74be`), clamped via `cmpf.s`, truncated to int (`trncf.sw`) at `0x3b862` -> `r28`.
- **Branch B** (`0x3b7b6-0x3b884`): two cascaded single-pole EMAs (state cells `gp-0x364c`, `gp-0x3648`),
  BOTH stages using coefficient `tp+0x73ba` = cal `0xC63BA`, **byte-verified fresh this session:
  `read_memory(0xC63B0,16)` -> u16@offset10 = 512** (Q10, alpha=0.5) -- matches prior memory exactly.
- **Sum**: `r28 = BranchA_int + BranchB_int` (`0x3b86a: add r14,r28`), scaled by `tp+0x73b6` (`0x3b86c-70`),
  sign split into `r13=abs(r28)` (`0x3b876-7c`) -> `gp-0x6ba6`, `r28`(signed) -> `gp-0x6b9a`.
- Both writes are SHADOW-LOCKSTEP pairs with consistency-monitor calls (`jarl 0x6b9fa`), same pattern
  documented elsewhere in this kit for other paired cells.

**Mechanistic tie-in**: the fault sentinels (+32767, and -1 read unsigned as 65535 for `gp-0x6ba6`) are BOTH
`> 25600` -- i.e., `FUN_00034a72`'s r21 gate (Q2) is specifically sized to catch `FUN_0003b66a`'s own
fault-sentinel protocol and prevent it corrupting the `gp-0x69ba` EMA state (Q6). The two functions were
evidently designed together around this contract.

**"FIR chain" is filter-theory-incorrect** for what `build_v58_tva.py` describes -- both branches are
explicitly recursive/stateful (feedback via `gp-0x365c` family and `gp-0x364c`/`gp-0x3648`), which is the
definition of IIR, not FIR (feedforward-only, no state). This matters for any phase/group-delay reasoning
about this signal.

## Q6 -- r24 at 0x34fc4 is gp-0x69ba (LERP4's prior EMA-blend state), forced to 0 when r21 fails [EVIDENCE]

`r24 = gp-0x69ba` (loaded `0x34f7a`). At `0x34fc4-c8`: `cmovne 0x0,r24,r24` -- **if `r21 != 1`, r24 is forced
to 0** (this is what `gp-0x6b9a` etc. ultimately gate: not a multiply operand, but whether the FSM's LERP4
blend state gets zeroed). If `r21==1`, `r24` blends with the fresh LERP4 lookup (`r6`="Y4", from `0xD2888`,
range 8176-16384 per Q3): **asymmetric EMA** -- direct/instant assign on DECREASE (`r6<=r24`, `0x34fce-d0`
-> `0x34fe8`), filtered EMA blend on INCREASE (`r6>r24`, `0x34fd2-e6`, coefficient at `tp+mode*4+0xb06c`).
**New finding this session**: `tp+0xb06c = 0xca06c` exactly (`0xBF000+0xb06c=0xCA06C`) -- **Y4's blend
coefficient is literally the SAME per-mode table as Y1's blend coefficient** (`0xca06c`, =102 at mode10,
independently confirmed by address arithmetic + byte read). This is the OPPOSITE asymmetry direction from
Y1/`gp-0x69bc`'s blend (documented in [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] as
instant-on-INCREASE/filtered-on-DECREASE) -- Y4 is instant-on-DECREASE/filtered-on-INCREASE ("fast release,
slow attack"), physically distinct behavior worth flagging for any future lever analysis of this cell.
`r24`(gated/blended) then feeds `0x34ffa`'s `term3` multiply exactly as documented in
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] section 4 (K1-vs-ceiling order), reused
unmodified here.

## Related
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] -- prior session's full trace of the same
function's baseline/FSM/K1-chain; this file extends it with the r21 gate's exact structure and the
fault-sentinel mechanism, neither documented there.
[[reference_accord_gp6bbe_angle_rate_path_traced_net_damping]] -- source of the rate-error/K1/speedLERP
framing this file's Q6 answer builds on.
[[reference-accord-gp4f60-v48b-reader-closure-and-mode-gated-bypass]] -- source of the mode==1 live-branch
fact and the `tp+0x73ba=512` alpha figure, both reused and re-verified here.
