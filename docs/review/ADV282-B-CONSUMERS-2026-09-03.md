# ADV282-B — Consumers, interlocks, instrument validity (V282)

**Target:** `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
(sha256 `0ea98d06b2…`) vs base V281 rev 3 (sha256 `98a7a514…`). GhidraMCP only; `code.bin` (stock, 2086
functions, full auto-analysis) used for structural/xref work, plus the flown V280 image (`CAVE_V280`
already a named function there) for the hooked cave itself. Python (`bin_decompile` env) for byte-level
independent re-derivation.

**Verdict up front: PASS. No DO-NOT-FLASH condition found on any of the four attack surfaces.**

---

## What a FAIL would have looked like (written before the pass)

- The Honda checksum for CAN 0x14A computed from a stale copy of byte 4/7, so V282's bits corrupt a
  frame openpilot's `HONDA_CHECKSUM` validator then rejects — DO-NOT-FLASH.
- `STEER_SENSOR_STATUS_1`/`_2` (0x14A byte 4 bits 5/6, the DBC names for the two repointed bits) actually
  gated something in panda safety or `carstate.py` (an angle/rate sanity check, a fault latch) — DO-NOT-FLASH.
- `gp-0x6ada`, `gp-0x6b94` or `gp-0x6b38` turning out NOT to be what the doc claims (r24's processed
  output / the motor-bound aggregate / T) — the instrument would be measuring the wrong thing, and any
  drive-time decision built on its duty would be wrong — FAIL (not necessarily DO-NOT-FLASH, since the
  edit is still read-only, but the whole rationale for cutting the build collapses).
- Any INTERNAL reader of the TX buffer bytes the cave writes (a lockstep monitor treating its own outbound
  frame as an input) — would make V282's bit changes visible to ECU logic, not just to the wire — DO-NOT-FLASH.
- The independent CRC/rwd rebuild not reproducing the shipped bytes — evidence the build's own
  self-report can't be trusted — FAIL.

None of these occurred.

---

## 1. Checksum ordering — cave runs before the checksum is computed (EVIDENCE)

Confirmed two ways.

**(a) In the hooked image** (`_v280_…` program, `CAVE_V280` is a named Ghidra function), `disassemble_bytes`
(`dry_run:true`) over `0x55BC0-0x55C5F` shows the call order inside the enclosing routine:

```
0x55BF2-0x55C02   write rolling-counter bits into byte 7 (gp-0x1511) high nibble
0x55C0E           jarl 0xc4b34,lp        ; CAVE_V280 -- writes byte 4 (gp-0x1514) bits 3-7
0x55C12-0x55C18   mov 0x8,r7 ; movea 0x14a,r0,r8 ; jarl 0x57b24,lp   ; checksum(buf, len=8, id=0x14a)
0x55C1C-0x55C2A   fold checksum's return (low nibble) into byte 7, alongside the counter bits set earlier
```

**(b) In stock `code.bin`**, `0x55C0E` (before any hook exists) is itself the plain instruction
`movea -0x1518,gp,r6` — the SAME instruction `CAVE_V280` executes as its own epilogue before `jmp lp`.
The hook is a length-preserving trampoline: 4 bytes of `jarl` replace 4 bytes of `movea`, and the cave's
tail restores the exact same `movea` before returning. Decompiling the full stock function
(`FUN_00055a98`, `code.bin`) shows the checksum call explicitly:

```c
bVar4 = FUN_00057b24(unaff_gp + -0x1518, 8, 0x14a);
*(byte *)(unaff_gp + -0x1511) = *(byte *)(unaff_gp + -0x1511) & 0xf0 | bVar4 & 0xf;
```

`FUN_00057b24` (decompiled from `code.bin`) is Honda's classic nibble-sum checksum
(`return 0x10 - (sum) & 0xf`) — the same algorithm opendbc's `HONDA_CHECKSUM` signal type implements
(`opendbc/can/dbc.py:194`, `ChecksumState(4,2,3,5,False,SignalType.HONDA_CHECKSUM,honda_checksum)`), so
openpilot DOES actively validate this checksum on receipt.

**Conclusion:** the checksum call sits strictly AFTER byte 4 is finalized (by the cave or, in stock, by
the inline bit-0..2 writers) and BEFORE the frame is queued. V282 changes nothing about this ordering —
its diff is confined to 6 bytes inside `CAVE_V280`'s own comparator operands (see §4), never touching the
hook, the checksum call, or the counter/checksum write-back logic. The transmitted checksum will always
correctly cover whatever byte 4 value the (possibly repointed) comparators produce, exactly as it does
today for the pre-existing bits 0-4/7.

## 2. Internal ECU consumers of byte 4 / byte 7 — none exist (EVIDENCE)

`search_instructions` over the full stock analysis (183,576 instructions, `truncated:false`) for every
operand referencing the buffer:

| cell | accesses | all inside |
|---|---|---|
| `gp-0x1514` (byte 4) | 8 (incl. one 32-bit `ld.w`/`st.w` pair in `FUN_0002193e`) | `FUN_00055a98` + its own helper `FUN_0002193e` |
| `gp-0x1511` (byte 7) | 4 | `FUN_00055a98` only |
| `gp-0x1518` (buffer base) | 2 | `FUN_000218fe` (an unrelated helper writing a DIFFERENT field, `-0x1518` as a 16-bit store) + the hook site itself |

The one non-obvious hit — a 32-bit `ld.w -0x1514[gp]` in `FUN_0002193e` — decompiles to a read-modify-write
that masks `0xff0000ff` (preserving bytes 4 and 7) and writes only the middle two bytes (5-6) with a
byte-swapped 16-bit value; it is a HELPER CALLED BY `FUN_00055a98` itself (xref: one call site,
`0x55B44`, unconditional), not an external reader. `get_xrefs_to` independently undercounted here (2 hits
for `gp-0x1514`, 0 for `gp-0x1511` — a known Ghidra jarl/gp-relative xref gap per the firmware-decompile
skill), so this is reported from the `search_instructions` positive count, corroborated by manually
reading every hit's enclosing function.

**Conclusion:** in the entire 2086-function stock image, the only code that ever touches these two buffer
bytes is the routine that builds and checksums the 0x14A frame. No lockstep monitor, no plausibility
check, no other consumer reads them back. Since V282's diff is 10 bytes total, all inside `CAVE_V280` and
its CRC trailer (§4), this holds for V282 unchanged — there is no possibility of a NEW internal reader.

## 3. External (openpilot) consumers of byte 4 bits 5/6 — none exist (EVIDENCE)

CAN ID 0x14A = message 330 = `STEERING_SENSORS`, confirmed via
`opendbc_repo/opendbc/dbc/generator/honda/_steering_sensors_a.dbc` (StarPilot fork, the operator's own
tree — `C:/Users/dudei/Desktop/Projects/openpilots/StarPilot/`):

```
BO_ 330 STEERING_SENSORS: 8 EPS
 SG_ STEER_SENSOR_STATUS_1 : 34|1@0+ (1,0) [0|1] "" EON     <- byte4 hw bit 5 (V282's "bit 5")
 SG_ STEER_SENSOR_STATUS_2 : 33|1@0+ (1,0) [0|1] "" EON     <- byte4 hw bit 6 (V282's "bit 6")
 SG_ STEER_SENSOR_STATUS_3 : 32|1@0+ (1,0) [0|1] "" EON     <- byte4 hw bit 7 (untouched)
```

(Motorola `@0` bit numbering: bit 32 = byte4 MSB = hw bit 7, bit 33 = hw bit 6, bit 34 = hw bit 5 —
exactly the two bits V282 repoints.)

- `grep -rn STEER_SENSOR_STATUS` across the whole StarPilot tree returns hits **only inside the DBC
  generator files themselves** — no Python, no C, nothing in `carstate.py`, `interface.py`, or the safety
  layer reads these signals.
- `carstate.py` (`opendbc/car/honda/carstate.py:187-188`) reads exactly two signals from
  `STEERING_SENSORS`: `STEER_ANGLE` and `STEER_ANGLE_RATE` (bytes 0-3, untouched by this cave and by V282).
- `opendbc/safety/modes/honda.h` has **zero** references to `330`, `0x14a`, or `STEERING_SENSORS` — panda
  safety does not gate on this message at all.

**Conclusion:** `STEER_SENSOR_STATUS_1/2` are DBC-defined but functionally dead on the openpilot side.
V282 changes the duty of two bits that (a) openpilot never reads for control or safety, and (b) still
pass the same `HONDA_CHECKSUM` validation they always did (§1). The cost-FAIL criterion in the doc's own
pre-registration — "invisible… the operator reports any change in feel" — is structurally guaranteed, not
just likely: there is no code path from these two bits to any actuator, gate, or fault latch.

## 4. Instrument validity — operand identities, gates, and the fault-arm (EVIDENCE)

Decompiled `FUN_0003aa2c` (`code.bin`, body `0x3aa2c-0x3ad73`) in full — this is the aggregator/r24
function the doc's claims rest on.

**`gp-0x6ada` IS r24's fully processed output.** The function computes a deadbanded, gain-arm-selected,
sign-flipped, +/-0x2000-clamped quantity and stores it at the very end:

```c
*(short *)(unaff_gp + -0x6ada) = (short)iVar16;   // iVar16 = clamp(+/-8192, sign(-1) * deadband(gain*idx>>10, tp+0x71f6))
```

confirmed as the ONLY writer in the whole image (`search_instructions` on `-0x6ada`: exactly 1 hit,
`st.h r24,-0x6ada,gp @0x3AD5A` — note the source register is literally named `r24`, matching the "r24
lane" naming used throughout). This is called UNCONDITIONALLY every tick — `FUN_0003aa2c` is called
unconditionally from `FUN_0002214a` (the 1 kHz task entry the doc's own §6 flags as unconfirmed for period;
its unconditional-call structure here is independent corroboration that it runs every task cycle) — so
`gp-0x6ada` is never stale, only sometimes not summed (next point).

**`gp-0x671d` IS the fault-debounce gain-arm gate, exactly as claimed**, and it selects between the three
cal addresses the pre-registration table names:

```c
if (*(char *)(unaff_gp + -0x671d) == '\0') {
    if (bVar4) { if (!bVar1) { uVar11 = *(ushort*)(unaff_tp + 0x7440); } }  // tp+0x7440 = 0xC6440 = 2048 (stock arm)
    else       { uVar11 = *(ushort*)(unaff_tp + 0x7446); }                  // tp+0x7446 = 0xC6446 = 5244 (engaged arm)
} else {
    uVar11 = *(ushort*)(unaff_tp + 0x7442);                                 // tp+0x7442 = 0xC6442 = 1024 (fault arm)
}
```

(`tp = 0xBF000`, so `tp+0x7440/42/46 = 0xC6440/C6442/C6446` — matches the pre-registration's cal table
exactly; when neither branch fires, `uVar11` keeps a table-LERP value from an earlier block indexed on
`gp-0x6ac0`, the rectified column rate.)

**Writers of `gp-0x671d`, traced fully:**
- Zeroed at `0x3BD2A` (`FUN_0003bcb2`), a shared reset helper called unconditionally from SEVEN different
  mode-handler functions (`FUN_0003c946/ca2a/ce48/c5ea/c7fc/d274/debc`) — consistent with "reset on
  re-entry to a family of states," not a periodic reset.
- Incremented (saturating at 255) at `0x41E8A-0x41EC6` (`FUN_00041d56`), called unconditionally from the
  SAME 1 kHz task (`FUN_0002214a`) as `FUN_0003aa2c`. The full decompile shows a model-based estimator
  (`fVar3`, a 5-term linear combination against `tp+0x70e8..0x7120` coefficients) whose scaled residual is
  compared against a two-level hysteresis (`tp+0x71f8`/`tp+0x71fa`); the counter increments by 1 on each
  tick the sustained threshold is exceeded and drives a DTC report (`FUN_00016de6(0x5e, 1, tp+0x7500<=count, 1)`)
  once it clears a further threshold. `gp-0x4c24` is confirmed as its lockstep mirror (write only commits
  if `gp-0x671d == gp-0x4c24`, else `FUN_0006b9fa` resyncs) — matches the doc's "lockstep twin" claim.

**BELIEF, not evidence:** what specifically makes this residual exceed threshold in ordinary healthy
driving (the physical meaning of `fVar3` and the `tp+0x70xx` coefficients was not traced further) —
structurally this reads as a model-mismatch/plausibility fault debounce that should sit near zero in
healthy driving and only rise under a genuine anomaly, but I have not proven the counter's duty is low on
a normal drive. **This is exactly the open question V282's own bit-6 duty is designed to settle
empirically** — I am not resolving it here, only confirming the mechanism the doc describes is real and
correctly wired.

**`gp-0x6b94` (aggregator) IS a lockstep-protected, +/-10240-clamped sum that includes r24.** Same
function, later:

```c
iVar19 = iVar9 + iVar19 + <gp-0x6ad4 term> + iVar14 + <gp-0x6b26 term> + <gp-0x6bbe term>
        + <gp-0x6bd0 term> + <gp-0x6b86 term> + iVar21 + iVar16;     // iVar16 = r24
...
if (sVar6 == sVar20) { gp-0x6b94 = clamp(iVar14+iVar19, +/-0x2800); gp-0x4ce0 = same; }
else { FUN_0006b9fa(&gp-0x4ce0); }   // lockstep resync
```

`gp-0x6b94` has ONE writer (this function) and FIVE independent downstream readers elsewhere in the image
(`FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`, `FUN_0007ff08`, plus the internal lockstep-compare read) —
consistent with "the motor-bound total," fanning out to multiple later stages. **V282's cave only READS
this cell** (`ld.h -0x6b94[gp],r6`, never a store) — it cannot desync the `gp-0x6b94`/`gp-0x4ce0` lockstep
pair or alter what any of the five downstream consumers see, by construction.

**The `gp-0x67ac` gate is real and matches the doc's own disclosed caveat.** The sum above only executes
when `gp-0x67ac != 1` (the doc's "r20==0 path"); when `gp-0x67ac == 1`, r24 (`iVar16`) is computed and
published to `gp-0x6ada` as always, but is NOT added into `gp-0x6b94`. This means the cave's `|r24|>=|T|`
and `|r24|>=|aggregator|` comparisons can be evaluated on cycles where r24 isn't actually contributing to
the motor sum — a real limitation, but one the build's own doc already flags ("gate the decode on
`gp-0x67ac` if a discrepancy appears"). Not a new finding; confirmed structurally correct as described.

**`gp-0x6b38` (T) is untouched by this function** and remains a clean, small-fanout cell: `search_instructions`
finds exactly 3 total accesses in the whole image — one writer (`FUN_00028ea6`, the LKAS PID, at `0x2A23C`)
and two readers (both in `FUN_0004e82e`). This corroborates T's identity as the 427 tap source independent
of `FUN_0003aa2c`.

## 5. Full-file diff, CRC recompute, and .rwd round-trip — independently reproduced (EVIDENCE)

All done fresh in Python (`bin_decompile` env), reading the files myself, not trusting the build script's
own self-report:

1. **Byte diff, V281 rev 3 -> V282:** exactly 10 bytes differ — the 6 payload bytes the doc's edit table
   predicts (`0xC4B36-37`, `0xC4B42-43`, `0xC4B64`, `0xC4B70` — 2 of the 8 "touched" bytes are no-ops
   because the new displacement's low byte matches the old one) plus the 4-byte CRC trailer at `0xC4FFC`.
   No other byte in the 1 MB image changed.
2. **Independent rebuild:** patched the base V281 rev 3 image with the 4 documented `ld.h` displacement
   edits, located the owning CRC block generically via `build_vfourframe_tva.crc_block_map` (not a
   hardcoded address), recomputed its CRC-32 with `zlib.crc32`, and wrote it back. Result: **byte-for-byte
   identical to the shipped V282 image** (sha256 `0ea98d06b2…` matches exactly).
3. **CRC chain replay:** ran `verify_bootloader_crc.walk_all_blocks` and `.walk` (imported fresh, called
   on the files as read from disk) against both the base and the shipped V282 image — 50/50 and 49/49
   blocks pass on both, my own independent rebuild included.
4. **.rwd round-trip:** decoded the actual shipped `.rwd`
   (`flashing-2020accord/rwd/39990-TVA,A160-V282-…rwd`) with the TVA cipher
   (`build_decode_table(FF.V9B["keys"], FF.V9B["ops"])`, applied to `parse_x31(rwd)["encs"][0]`) and
   compared to the analyzed plain image: **byte-for-byte identical, sha256 matches exactly.** This is the
   file that would actually be flashed, decoding to precisely what this whole review analyzed.

## Open items (not FAILs, carried forward)

1. `gp-0x671d`'s physical trigger condition in NORMAL driving is BELIEF, not evidence (§4). V282's own
   bit-6 duty measurement is the intended way to settle it — this review does not pre-empt that.
2. The doc's own disclosed `gp-0x67ac` gate means the comparator can be evaluated on cycles where r24
   isn't in the sum; already flagged in the build script, re-confirmed structurally correct here.
3. I did not trace `gp-0x6b94`'s five downstream readers to the motor drive stage itself — their EXISTENCE
   and the fact V282 only reads (never writes) `gp-0x6b94` is what matters for this adversarial pass, and
   both are confirmed; a full downstream trace was out of scope for a read-only instrument review.

## Verdict

**PASS.** No consumer inside the ECU or in openpilot depends on the two repointed bits. The checksum that
protects the frame they live in is computed after they're written, unchanged from every prior build. The
three tapped RAM cells are what the doc says they are, confirmed from decompiled stores, with their gates
and interlocks (the `gp-0x671d`/`gp-0x4c24` lockstep pair, the `gp-0x6b94`/`gp-0x4ce0` lockstep pair, the
`gp-0x67ac` sum gate) all independently re-derived and structurally intact. The shipped `.rwd` decodes to
exactly the image this review analyzed. Recommend flashing.
