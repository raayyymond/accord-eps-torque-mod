---
name: accord-crc-block-lookup-and-cave-hook-template
description: 2020 Accord TVA-A160 — address→CRC-block lookup (which block covers a cal/cave edit and where its CRC word lives), per-build cave occupancy, and the byte-validated V85 cave/jarl-hook template. Measured 2026-08-09 from the V86B image.
metadata:
  type: reference
---

# CRC block lookup, cave occupancy, and the flown cave/hook template

Measured 2026-08-09 on `_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin`
(V86B = the build on the car at the time), corroborated against stock `code.bin` and 88 built images.
Extends [[accord-codecave-c4b34-c4fef-larger-than-documented]], which already has the correct 1212-byte
empty-cave figure — this file adds the per-build occupancy, the block lookup, and the hook idiom.

## Address → CRC block lookup (the thing you actually need before any edit)

Replay `analysis-2020accord/verify_bootloader_crc.py::_blocks(img, 0x13000, 0xED000, bridge)` and ask
which block covers your address. Results for the cells this kit edits most:

| edit address | covering block | CRC word | in bootloader's 49-block walk? |
|---|---|---|---|
| `0xC63B4`, `0xC63B8` (and all `0xC6xxx` cals) | `[0x0C6000, 0x0C6FFC)` | **`0x0C6FFC`** | YES — block #48 |
| cave `0xC4B34..0xC4FF0` | `[0x013000, 0x0C4FFC)` | **`0x0C4FFC`** | YES — block #49 |
| app code, e.g. `FUN_0003b66a` @ `0x3B66A` | `[0x013000, 0x0C4FFC)` | **`0x0C4FFC`** | YES — block #49 |
| free run `0xC5788..0xC5FF0` (2152 B) | `[0x0C5000, 0x0C5FFC)` | `0x0C5FFC` | **NO — skipped by the 0xC6000 bridge** |

⇒ **A cal-only edit at `0xC63B8` needs exactly ONE CRC word recomputed: `0xC6FFC`.** A cave edit needs
`0xC4FFC`. A build touching both needs both. `walk_all_blocks()` (50 blocks) is the hygiene gate;
`walk()` (49) predicts the UDS NRC 0x72.

## 🛑🛑 CRC blocks are a LINKED LIST, **NOT** uniform 4 KB pages — this nearly caused a brick

2026-08-10: an orchestrator "corrected" a V90 spec to emit a second trailer at `0x055FFC`, reasoning that
`0x55DF2` must live in a `0x055000` page. **That model is wrong and acting on it bricks the ECU.**
`[0x013000, 0x0C4FFC)` is ONE 0xB1FFC-byte block — the bootloader's own hard-coded main block
(`0xB07A` = `0x13000`, `0xB080` = `0xB1FFC`) — and it covers **all app code**: hook `0x55C0E`, the 427
packer `0x55DF2`, K1 `0xC40D2`, and the cave `0xC4B34`. **All four share the single trailer `0xC4FFC`.**
Verified end to end on the V89 image: `zlib.crc32(img[0x13000:0x13000+0xB1FFC]) = df43b558` and
`img[0xC4FFC:0xC5000] = 58b543df` ⇒ MATCH.

Writing at `0x055FFC` fails twice: it is **inside** the covered range, so it invalidates the very CRC it
is meant to fix; and it is **live code** — `img[0x55FFC:0x56000] = 6477b8f0` = `st.h r14,-0xf48,gp` in
`FUN_00055f2e`.

⊕ **Cheap test for whether an address is a trailer at all — a real one has sane link fields at −8/−6:**
`0xC4FFC` → `start_page=0x0000, num_pages=0x00C6` ✓ · `0xD7FFC` → `0x0000/0x00D9` ✓ ·
**`0x055FFC` → `start_page=0x5EC8` ⇒ block start `0x5EC8000` = 99 MB, past the end of a 1 MB image** ✗.
**Never infer a trailer address by dividing by 0x1000. Replay `_blocks()` and read the answer.**

🛑 The count of CRC words a build updates tracks how many 0x1000 pages it writes, and it is easy to
under-estimate: **V86B updated 14** — `0xC4FFC, 0xC6FFC, 0xCEFFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC,
0xD4FFC, 0xD6FFC, 0xD7FFC, 0xD8FFC, 0xD9FFC, 0xE4FFC, 0xE5FFC` — because its damper/cal tables are
spread across those pages. Never assume "two".

## Cave occupancy per build (0xFF-run scan, first non-FF byte after 0xC4B34)

| build | cave bytes used | free start | free bytes |
|---|---|---|---|
| stock | 0 | `0xC4B34` | **1212** |
| V81 | 68 | `0xC4B78` | 1144 |
| V84 | 66 | `0xC4B76` | 1146 |
| V85 | 68 | `0xC4B78` | 1144 |
| V86 / V86B | 62 | **`0xC4B72`** | **1150** |

🛑 The frequently-quoted **"1144 free bytes at 0xC4B78" is the V81/V85 residual, NOT the empty-cave
figure.** Empty cave is 1212 at `0xC4B34`. Always re-measure against the actual base image.

## The flown cave + hook template (V85, byte-verified)

Hook at `0x55C0E` (CAN 0x14A / 330 TX builder, inside `FUN_00055a98`): stock 4 bytes
`2436e8ea` = `movea -0x1518,gp,r6` replaced by `86ff26ef` = `jarl 0xC4B34, lp`.

```
0xC4B34 mov   0x0,r7            ; accumulator
0xC4B36 ld.h  -0x6abc,gp,r6     ; sample a signal
        sar/add/cmp/bnh ladder  ; quantise -> bits into r7
0xC4B60 shl   0x4,r7            ; data -> bits 7:4
0xC4B62 add   0x8,r7            ; bit 3 = "cave ran" liveness marker
0xC4B64 ld.bu -0x1514,gp,r6     ; telemetry byte = CAN 0x14A byte 4
0xC4B68 andi  0x7,r6,r6         ; preserve live bits 2:0
0xC4B6C or    r7,r6
0xC4B6E st.b  r6,-0x1514,gp
0xC4B72 movea -0x1518,gp,r6     ; <-- byte-copy of the OVERWRITTEN instruction
0xC4B76 jmp   lp                ; 7f00, returns to hook+4
```

The last 22 bytes `483a 8437edea c6360700 0731 4437ecea 2436e8ea 7f00` are **byte-identical across V84,
V85, V86 and V86B** — that tail is the reusable epilogue.

**Invariants:** leaf — no `prepare`, no stack use; scratch is **r6 and r7 only**; all state in
gp-relative RAM; the last real instruction is a byte-copy of whatever the hook overwrote; return
`jmp lp`. Every flown cave writes only `gp-0x1514` — **none has ever allocated new RAM**, which is why
they were safe. A filter cave needing persistent state is a materially riskier class; see
[[accord-v850-scan-traps-formatv-and-storezero]] and GATE 1.

**Why `0x55C0E` is a safe site** (the criteria to reuse when picking a new one): the preceding
instruction is itself `jarl …,lp` and the following is `jarl 0x57b24,lp`, so **lp is already dead**;
r6 is the hooked instruction's own destination and r7 is unconditionally overwritten by the next
instruction, so both are dead-on-entry; r10 is live across and the cave never touches it.

## Validated `jarl …, lp` (Format V) encoder

```python
d = target - hook                 # must be even; |d| < 2**21 (whole 1 MB image reachable)
hw1 = 0xFF80 | ((d >> 16) & 0x3F) # 0xFF80 = reg2=r31(lp), opcode 11110
hw2 = d & 0xFFFE
bytes([hw1 & 0xFF, hw1 >> 8, hw2 & 0xFF, hw2 >> 8])   # little-endian
```
Validated: `hook=0x55C0E, target=0xC4B34` reproduces `86ff26ef` exactly. Always re-validate an encoder
against this known-good pair before trusting a new displacement.

## Two tool traps hit while measuring this

- **`get_xrefs_to` on a gp-relative RAM address returns a misleading zero.** Queried `0xFEDF1534`
  (= `gp-0x6acc`) → "No references found"; a raw little-endian byte scan found **6** real accesses.
- **Format VII gp-relative opcode field is `0x38/0x39/0x3A/0x3B` (ld.b / ld.h·ld.w / st.b / st.h·st.w),
  NOT `0x30/0x31/0x34/0x35`** — those are Format VI `addi`/`movea`. A scan built on the wrong table
  returned **0 hits on all four spine cells**, which reads exactly like a real null. Caught only because
  `0x431C4 = 244f3495` was known ground truth. **Always seed a byte scanner with a known-good encoding
  and assert it matches before trusting any count.**
