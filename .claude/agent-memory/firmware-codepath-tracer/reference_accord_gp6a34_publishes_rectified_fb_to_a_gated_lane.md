---
name: reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane
description: gp-0x6a34 = |floor32(clamped feedback sum)| >> 5, published once per tick at 0x290CA in FUN_00028ea6. Its ONLY other live reader (0x2A0CA, decompile line 764) is gated behind gp-0x680a==1 (a narrow lane, not the general engaged path) and feeds a per-variant LERP (tp+0x7714/0x7720/0x7722/0x7730, a DIFFERENT table than the speed-indexed one at gp-0x674e's base 0xCB844) whose result is re-signed by the ORIGINAL (pre-rectification) feedback sign. Also documents a self-caught tracing error: the walk key for the knot table right after the rectification (0x28FC8+) is gp-0x6a5e (vehicle speed), NOT this value -- a raw-disassembly-only read wrongly guessed otherwise.
metadata:
  type: reference
---

# `gp-0x6a34` = rectified `|fb|`, consumed only in the `gp-0x680a==1` lane — and a self-corrected tracing error

2026-09-08, subagent `tracer`, stock `code.bin`, `decompile_function` on `FUN_00028ea6`. Answers
`loopshape`'s Q7 ("what consumes r16 after the bp/subr r0,r16 rectification at 0x28FC4?").

## The mistake, stated first

My FIRST pass, from raw disassembly alone (`disassemble_bytes` over `0x28FA0`-`0x29040`), saw the
rectified value (`r16`, saved to `r9` at `0x28FDE mov r16,r9`) immediately followed by a per-variant
knot-walk (base table `0xCB844`, selector `gp-0x674e`) and guessed the walk was indexed by that saved
value. **Wrong.** Decompiling showed the walk key (`uVar20`) is `*(ushort*)(gp-0x6a5e)` — a
vehicle-speed-class cell, loaded independently much earlier in the function (`0x28F0E`), long before the
feedback filter even runs. The saved `r9` (rectified `|fb|`) is not read again by that walk at all — it
survives untouched through it (none of the walk's instructions write `r9`) and is consumed elsewhere
entirely (below). [[feedback_check_own_memory_before_retracing_and_variable_reuse_trap]] and this kit's
own prior record (`reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation.md`: "Ghidra's
decompile reuses r9/r27 across the P/D blocks and misreads easily") both predicted exactly this failure
mode for this function; decompiling caught it before it reached the operator.

## The real answer

```c
*(short *)(gp-0x6a34) = (short)(uVar18 >> 5);   // 0x290C6 shr 0x5,r9 ; 0x290CA st.h r9,-0x6a34,gp
```

`gp-0x6a34` has exactly 2 live accesses in `FUN_00028ea6` (confirmed by a whole-program
`search_instructions` and by an earlier, independent RAM census this same session — see
`reference_accord_gp6a2c_to_6a5e_neighborhood_saturated_gp6a2a_is_free.md`, which found this address
occupied). The one reader (decompile line 764):

```c
if (((uVar18 != 0) || (cVar15=='\x01')) && bVar3) {
  if (gp-0x680a == 1) {                                  // a NARROW lane, not general-engaged
    uVar20 = gp-0x6a34;                                   // reload the rectified |fb|>>5
    sVar27 = LERP(uVar20, table at tp+0x7714/0x7720/0x7722/0x7730);   // a THIRD table, distinct
                                                            //   from the speed-indexed 0xCB844 one
    uVar20 = -sign(uVar35) * sVar27;    // uVar35 = the ORIGINAL signed clamped fb, pre-rectification
  } else { /* driver-override taper branch, gp-0x682f -- unrelated */ }
}
```

`gp-0x680a` was previously identified (V288 adversarial pass, `ADVERSARIAL-V288-PREREG-2026-09-07.md`,
"D addendum 2") as "the third skip (gp-0x680a lane, 0x2A0C6)" in the disengage-handling context — I have
not re-derived what specifically selects this lane beyond that prior identification. **Answer to the
actual question asked: this is a genuine, feedback-magnitude-dependent term (re-signed by fb's own
direction), NOT diagnostics-only, but it is gated to this narrow lane, not the general torque path.**
Where the resulting `uVar20` ultimately lands was not traced further this session — exact next step if
this lane becomes decision-bearing.

Full trace: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`, ADDENDUM Q7.
