# ADV284-C — Interlocks / Slot Selection / Page Ownership adversarial pass

**Target:** V284 = V282 + Kp record `0xE5378` (slot 7) reshaped on both axes, idx 33-87, peak 512.
Image: `_v284_..._plain_image.bin`, sha256 `1b46f24f...` (as given in brief).
**Surface:** slot selection correctness, page/CRC ownership, downstream interlocks, knot-axis hazard.
**Method:** GhidraMCP only, on the `_v282_..._plain_image.bin` program (proven code-identical to V284 in
every function touched below — see "Base identity" — so tracing code on it is tracing V284's code) plus
raw Python byte scans on the actual V284 image file for every load-bearing count/null. All scans
positive-controlled before being trusted.

## Pre-registered FAIL criteria (written before touching the image)

1. Slot mutability — more than one live writer of `gp-0x674e`, or a field-reachable path to change it.
2. The ×4 scaling gap — the raw selector byte used as a byte-offset into `0xCB994` without a scale step.
3. Twin liveness — `FUN_0002a93a` reachable by any call path.
4. Page privacy — another consumer's stride/axis assumption colliding with slot 7's edited bytes.
5. Downstream trip — the 2.06x Kp reaching a rail/interlock/DTC threshold the flat-248 image never reaches.
6. Knot degeneracy — any reachable state presenting a non-increasing X to the `divq` at `0x29E2C`.

None triggered. Verdict: **FLASH**, with two named caveats (non-blocking, both documentation-completeness
findings, not build defects) — see "Caveats" at the end.

## Base identity (why tracing V282's code traces V284's code)

Full-range diff `[0x13000,0x100000)`, V282 vs the actual V284 file, byte for byte (own script, not the
build script's accounting):

```
0xe537c 0xe537c len 1      (X[1] low byte:  0x44 -> 0x20)
0xe537e 0xe537e len 1      (X[2] low byte:  0x70 -> 0x24)
0xe5380 0xe5380 len 1      (X[3] low byte:  0x88 -> 0x2c)
0xe5382 0xe5382 len 1      (X[4] low byte:  0xd0 -> 0x58)
0xe5388 0xe538b len 4      (Y[2],Y[3]:      0xf8,0x00 x2 -> 0x00,0x02 x2)
0xe5ffc 0xe5fff len 4      (page CRC trailer)
```

**Twelve bytes, total, across the whole 1 MB image outside the bootloader region.** No code byte differs.
[EVIDENCE — my own Python diff over the actual `_v284_...` and `_v282_...` files on disk, not the build
script's self-report.] This licenses tracing every function below on the already-open V282 program.

## 1. The record edit itself, independently re-derived

Reading raw bytes at `0xE5378` on both images (my own script, not `rec()` from the build script):

```
offset  field    V282        V284
+0x00   count    05 00       05 00        (5)
+0x02   X[0]     00 00       00 00        (0, explicit — matches the disasm's sld.hu +0x2 = X[0])
+0x04   X[1]     44 00 (68)  20 00 (32)
+0x06   X[2]     70 00 (112) 24 00 (36)
+0x08   X[3]     88 00 (136) 2c 00 (44)
+0x0a   X[4]     d0 00 (208) 58 00 (88)
+0x0c   Y[0]     f8 00 (248) f8 00 (248)
+0x0e   Y[1]     f8 00 (248) f8 00 (248)
+0x10   Y[2]     f8 00 (248) 00 02 (512)
+0x12   Y[3]     f8 00 (248) 00 02 (512)
+0x14   Y[4]     f8 00 (248) f8 00 (248)
+0x16   pad      00 00       00 00
```

Exact match to the build script's claimed X/Y before and after. [EVIDENCE — independent byte read,
offsets re-derived from the disassembly below, not copied from `build_v284_tva.py`'s `rec()`.]

## 2. The ×4 scaling gap — RESOLVED, found and located

This was the single most load-bearing unverified claim in the brief. Disassembled `0x29C80-0x29E40`
of `FUN_00028ea6` (`dry_run:true`, on the already-analyzed V282/V284-identical code):

```
0x29CC4  ld.bu  -0x674e, gp, r12     r12 = raw selector byte (the coded slot, 0-9)
0x29CC8  ld.bu  -0x6830, gp, r21
0x29CCC  mov    0x0, r7
0x29CCE  shl    0x2, r12             <-- r12 = r12 << 2 = selector * 4        *** THE ×4 ***
0x29CD0  ld.bu  0x74f0, tp, r16
   ... (unrelated map/taper-index work in between) ...
0x29DC6  mov    0xcb994, r10         r10 = KP_PTR base
0x29DCC  mov    r12, ep              ep  = r12  (ALREADY *4 from 0x29CCE)
0x29DCE  add    r10, ep              ep  = 0xCB994 + selector*4
0x29DD0  sld.w  0x0, ep, ep          ep  = *(0xCB994 + selector*4)  = record base
0x29DD2  mov    r12, r9
0x29DD4  add    r10, r9
0x29DD6  ld.w   0x0, r9, r10         r10 = same record base (redundant re-read)
```

**Finding: the shift IS present, at `0x29CCE`, well before the table walk.** The byte loaded at
`0x29CC4` is scaled by 4 immediately and that scaled value is what reaches `0x29DCC`/`0x29DCE`. The
build script's own comment ("scaled somewhere upstream") is now nailed down to one instruction.
[EVIDENCE — `disassemble_bytes` dry-run, address-anchored, on code proven identical to V284.]

**Consequence:** for selector=7, `ep = *(0xCB994 + 28)` — the SAME pointer the build script's static read
confirms equals `0xE5378`. The reshaped record is provably the one the live lookup dereferences, *given*
the runtime selector value is 7 (see §4).

## 3. Twin liveness — `FUN_0002a93a` — DEAD, confirmed four independent ways

- `get_function_callers("FUN_0002a93a")` → **0 callers**.
- `search_instructions(mnemonic="jarl", operand_pattern="2a93a")` → **0 matches** (171,746 instructions
  scanned on this program).
- **Positive-controlled raw byte scan** (independent of Ghidra's analysis database, decodes V850 Format-VI
  `jarl disp22,reg` directly from bytes: opcode field = bits 6-10 of hw1 = `0x1E`, disp = `(hw1&0x3F)<<16
  | hw2`, sign-extended from bit 21): controlled against **5** known jarl call sites (the hook at `0x55C0E`
  → `0xC4B34`; `0x22A7C` → `0x42692`; and the skill's three standing controls `0x22522→0x28EA6`,
  `0x23276→0x34350`, `0x2291E→0x3AA2C`) — **all 5 matched exactly**. Run against the full V284 image
  (not just already-analyzed instructions): **0 hits** targeting `0x2A93A`.
- Raw scan for the literal pointer value `0x0002A93A` as any 4-byte LE sequence anywhere in the 1 MB
  image (rules out reachability via an indirect call / function-pointer table): **0 occurrences**.

[EVIDENCE, four-way corroborated, one method fully positive-controlled per the firmware-decompile skill's
"never trust an uncontrolled null" rule.] `FUN_0002a93a` does not run on this image by any mechanism I can
find. It does not consume the reshaped record.

## 4. Page ownership — broader than documented, but the edit is still provably scoped

Raw scan of the entire V284 image for any 4-byte LE value in `[0xE5000,0xE6000)`, grouped into
contiguous stride-4 arrays (i.e. real pointer tables, not coincidental matches):

| array base | slots found | page range |
|---|---|---|
| `0xC9A88` (MAP_PTR, named) | 6 | `0xE5000-0xE50DC` |
| `0xCB7D4` (KD_PTR, named) | 6 | `0xE5108-0xE516C` |
| `0xCB844` **(not named by the build script)** | 6 | `0xE5180-0xE5248` |
| `0xCB8B4` (TAPER_PTRS[2], named) | 6 | `0xE5270-0xE52D4` |
| `0xCB924` (TAPER_PTRS[3], named) | 6 | `0xE52E8-0xE534C` |
| `0xCB994` (**KP_PTR — the edited table**) | 6 | `0xE5360-0xE53D8` (slot 7 = `0xE5378`) |
| `0xCBA04` (TAPER_PTRS[0], named) | 6 | `0xE53F0-0xE5454` |
| `0xCBA74` (TAPER_PTRS[1], named) | 6 | `0xE5468-0xE54CC` |
| `0xCBAE4` **(not named)** | 6 | `0xE54E0-0xE556C` |
| `0xCBB54` **(not named — live-referenced in the same PID function, `mov 0xcbb54,r10` at `0x29F08`)** | 6 | `0xE5588-0xE5614` |
| `0xCBBC4` **(not named — matches a prior memory finding of a post-PID fade table at this address)** | 6 | `0xE5630-0xE56BC` |
| `0xCBC34` **(not named — also live-referenced in the same PID function, `mov 0xcbc34,r8` at `0x29F78`)** | 6 | `0xE56D8-0xE5764` |

**Finding: the page carries at least 12 distinct pointer-table families, not the ~5 the build script's
own prose credits (map/Kp/Kd/2 tapers).** Two of the unnamed ones (`0xCBB54`, `0xCBC34`) are read by the
*same* PID function immediately after the Kp lookup — they are almost certainly the Kd-blend and a
post-computation taper/fade path, not idle data.

**But the edit itself is still provably private**, independent of this undercount: the full-file byte
diff in §1 — an unbiased scan of the *entire* image, not a bank-by-bank enumeration — shows exactly 12
differing bytes total, all inside slot 7's own 24-byte record (`0xE5378-0xE538E`) or the one page-CRC
trailer. **No byte belonging to any of the other 11 families changed.** The build script's own "no other
record overlaps slot 7" check ([1b]) only walks `KP_PTR`'s own 28 entries — it does not know about the
other 7 unnamed families — but the unbiased full diff makes that gap harmless: it would have caught a
collision regardless of whether the colliding table was named.

**This is a documentation-completeness gap in the build script's commentary, not a build defect.** I flag
it as a caveat because it means more consumers than credited share this page's one CRC (see §5).

## 5. Downstream — clamps, precedent, and the page-CRC's own on-car record

- Every clamp cell the P/sum path uses is read directly off the image and is unchanged: `0xC61B4=3072`,
  `0xC61B6=10240`, `0xC61BA=10240`, **`0xC61BC=15360`, `0xC61BE=15360`** (the P clamp — traced directly:
  `0x29E3A ld.hu 0x71BC,tp,r6` = `tp+0x71BC = 0xC61BC`, compared against the shifted P term at `0x29E3E
  sar 0x8,r8` before the `cmp/ble` clamp at `0x29E40-0x29E5C`), `0xC6AE6=2048`, `0xC644A=1024`,
  `0xC6446=5244` (r24 gain, untouched), `0xC62E6=46080` (feedback clamp, untouched). [EVIDENCE — direct
  disassembly of the clamp site plus the tp-anchor arithmetic, corroborating the build script's FROZEN
  table on the live code path itself, not just as a byte-equality assertion.]
- **Peak delivered Kp (512) stays under the stock LERP's peak (696)** that already flew on r32/r33/r34
  without incident (V280 rev 2, per lineage). The raised gain does not exceed authority this car has
  already carried on a public road.
- **The page-CRC recompute mechanism has already flown on real hardware, on this exact page.** Read
  directly from the images (not the build script's claim): `_v280_...` (parent) page-0xE5000 trailer =
  `d0d211ec`; `_v281r3_...` (child, **FLOWN, route r35** per the build lineage and prior memory) trailer =
  `7ea6f28e`, with **46 payload bytes changed** across the page between those two images. V282/V284 both
  carry that same `7ea6f28e` trailer unchanged from V281 rev 3 until this build's own recompute. The
  identical recompute-and-store mechanism this build uses was therefore already exercised, on this exact
  4 KB block, on a build the operator drove — a materially stronger check than "the build script's own
  CRC walker passes."
- I traced the generic fault-setter `FUN_0006b9fa` (sets a DTC word at `gp-0x4D6C`, calls
  `FUN_0006CE7C(4)`) and pulled its full caller list (~85 functions across the firmware). **The rate-PID
  function containing the Kp lookup (`FUN_00028ea6`, the `0x29Cxx-0x29Fxx` range) is not among its
  callers** — there is no inline fault trip wired directly into this function on a Kp/P-term value.
  [EVIDENCE for "no direct trip", by omission from a complete caller enumeration.]
- **Open item, not resolved by me:** the brief's cited shadow-consistency flag family at `gp-0x683b` /
  `-0x4c3f..-0x4c42` (another agent's finding). I did not independently trace that family forward or
  find any reference to it inside `FUN_00028ea6`'s Kp/P-term path in the code I disassembled. I am not
  asserting it is unaffected — I am stating I found no connection in my own trace and did not have
  budget to close it out. **This is the one item I'd want a second pass on before calling the downstream
  census complete.**

## 6. Knot degeneracy — bounded to the general cal-corruption risk, not elevated by this build

`X` is a static flash constant inside a record that is never written at runtime — only the *selector*
(which record to read) is runtime-variable (§ above), never the record's own bytes. Strictly-increasing
is verified twice independently (my own byte read in §1, plus the build script's own image-level
assertion). The only way `X` presents non-increasing to the `0x29E2C divq` is physical flash
corruption/bit-flip on this specific 8-byte span — a risk every cal-only build ever flown on this kit
carries identically (including V281 rev 3, V282, V283), not something V284 introduces or raises.

## Verdict

**FLASH.**

All six pre-registered FAIL criteria were checked against the actual image/code and none triggered:
1. Slot selector: one writer, one caller of that writer, gated behind a UDS-coding-completion bit —
   consistent with, and now re-confirmed independent of, the standing "selector=7, static" record.
2. ×4 scale: found, at `0x29CCE`, closing the brief's single most load-bearing open question.
3. Twin (`FUN_0002a93a`): dead, four independent confirmations, one fully positive-controlled.
4. Page privacy: the page is more shared than documented (12 families, not ~5), but the edit is proven
   scoped to slot 7 alone by an unbiased full-image diff, independent of that undercount.
5. Downstream: clamps unchanged, peak gain under a value that already flew, and the exact CRC mechanism
   already flew on this exact page (V281 rev 3 / r35).
6. Knot axis: static, double-verified increasing; residual risk is generic flash-corruption risk, not
   build-specific.

**Caveats (non-blocking, named per the protocol):**
- The build script's own page-ownership commentary undercounts the true number of cal families sharing
  `0xE5000` (12 vs. ~5 credited) — correct the record, no action needed on the image itself.
- The `gp-0x683b` shadow-consistency flag family another agent flagged was not traced to a conclusion by
  me; I found no evidence it touches this path, but I did not chase it to closure either.

I expect to be closing out now — nothing further planned on this surface unless asked to chase the
`gp-0x683b` open item.
