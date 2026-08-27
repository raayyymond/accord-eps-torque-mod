---
name: reference-accord-v55-dual-probe-built
description: "V55 BUILT 2026-07-28, UNFLASHED -- a DUAL report-only probe on the proven 0x14A byte4 piggyback: bit7 = damper variant index >= 10, bits 6:3 = a 4-bit window on gp-0x6b98 (the final merged command). It PARTITIONS the hypothesis space instead of testing a ninth lever. Includes the decoder trap where a V54 rlog decodes as a plausible V55 reading."
metadata:
  node_type: memory
  type: reference
---

# V55 -- the partition probe

```
_v55_plain_image.bin  SHA 9ed79e68e1d02362efff5262a9f142e6e1a6596104d800d5fd6a95cef86e576c
V55 .rwd              SHA 2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf
82 bytes off V38: hook 0x55C0E (4) + cave 0xC4B34 (68) + 0xC62EA (2) + two CRC trailers
```

```
bit  7    = (damper variant INDEX >= 10)                     [static]
bits 6:3  = clamp((gp-0x6b98 >> 9) + 8, 1, 15)               [motor command, 512 counts/level]
bits 2:0  = stock STEER_SENSOR_STATUS, preserved
```

**It is a PARTITION, not a lever.** Every falsified vibration lever sits on the command path and assumes
the ~20 Hz is *commanded*. `gp-0x6b98` is the final merged command and the only path to FOC:
present => the command path stays in scope; absent => all eight were doomed by construction and the search
moves to the plant. A null **bounds** the command's 20 Hz content to ~<512 counts against the sensor's
~550 rms -- it does not prove zero, and 100 Hz cannot separate 20 Hz from 80 Hz.

## Build facts worth reusing

- `gp-0x6b98` is **SIGNED** (`st.h` writes, `ld.h` reads at all 29 four-byte-form read sites), clamped
  +-0x2000 at `0x43b0e..0x43b20`, store at `0x43b52`. Using `ld.hu`/`shr` (as V54 did for the *unsigned*
  `gp-0x6966`) would corrupt every negative command -- **check the signedness of a new probe source.**
- **`ld.bu` encodes displacement bit 0 in the OPCODE low bit**: op `0x3C` for even, `0x3D` for odd, with
  `hw2 = (disp & 0xFFFE) | 1`. `gp+0x63fd` is odd *and positive*. V54's helper hard-coded `0x3C` and could
  only emit even displacements.
- **Bit 0 of `hw2` discriminates width for STORES too**, not just loads: `st.w` carries `|1` exactly like
  `ld.w`; only `st.h`/`st.b` are bare. A scan for a *word* variable's writer that assumes bare stores
  misses it.
- Every cave instruction is either byte-identical to V54's flashed cave or differs by a **single
  register/condition field** from a byte-confirmed real instance. No novel opcode value.

Gates: 50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the readback,
and the cave + hook **re-disassembled from the written image via GhidraMCP** (SHA-verified copy under a
distinct filename, `auto_analyze=false`, `dry_run=true`, never saved). GATE 1 vacuous (no scratch RAM,
r6/r7 only). GATE 2 vacuous (report-only; `0xC6AF0` and all damper cals asserted stock).

## Decoder trap: a V54 rlog decodes as a plausible V55 reading

V54 packs `wire = min((gp-0x6966>>7)+1,31)` into bits 7:3 of the **same byte**. On V54 authority is
pinned, so `byte4 == 0x0F` all drive -- which decodes under V55's layout as `field == 1, bit7 == 0`, i.e.
a confident "command pinned low, variant index < 10". Reserving 0 does **not** help, because the other
build writes a 1 into those bits. The guard: a live V55 field samples the **motor command** and therefore
**cannot be constant** on a driving car. `probe/decode_v55_motorcmd.py` refuses to interpret a constant field
and says why. Verified: V54 rlog -> REFUSE, V53 rlog -> VOID.
