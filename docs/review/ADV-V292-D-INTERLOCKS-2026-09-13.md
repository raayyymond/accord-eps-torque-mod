# ADVERSARIAL PASS — V292, surface D: INTERLOCKS AND DOWNSTREAM (GATE 1)

**Agent:** `advD2` (firmware-codepath-tracer), SUBAGENT of the orchestrator (`main`). **Date:** 2026-09-13.
**Role:** adversary. The job was to make V292 FAIL on this surface and to be able to return DO-NOT-FLASH.
**Nothing flashed, nothing sent, no build script touched, no Ghidra rename/patch/save.**

**Image under attack:** `_v292_V292-V282BASE-EFCAVE.C4C00.6D74-…_plain_image.bin`,
SHA256 `d1128232993d3a1dcfa4afecb279976f014e6c940f36d88b87db9f2aee3aef33` — **hash-verified from disk
by me before any analysis.** Bases also hash-verified: V291 `a66f9c54…`, V282 `0ea98d06…`,
stock `3f1d55a9…`.

**Method.** Every load-bearing count or null is produced TWICE — GhidraMCP and an independent raw
little-endian Python scan of the BUILT image — and **every scanner was positively controlled before
its null was trusted.** Where the two disagree, the disagreement is adjudicated with a stated
exclusion reason, never averaged. Python: `bin_decompile` env. Scripts in the session scratchpad
(`d1_scan.py`, `d1_main.py`, `d1_forms.py`, `d1_forms2.py`, `d1_exact.py`, `d1_boot.py`,
`d4_branch.py`, `d2_d6.py`).

---

## VERDICT: **PASS** — no DO-NOT-FLASH finding on the interlocks surface.

Four defects found. **None is a build defect**; all four are defects in the *evidence* offered for the
build — a false liveness argument that happens to have a true conclusion, an incomplete census, an
uncontrolled null, and an overstated control. They are reported for the record and for correction of
the design document and the agent-memory file, per the standing rule that findings arriving after
acceptance are reports, not licence to act.

| clause | verdict | basis |
|---|---|---|
| D1 remainder cells / 72-byte run / alignment / boot value | **PASS** (one census correction, F2) | both methods, 7 controls |
| D2 fb state, filter cadence, bail path, r25, register and PSW footprint | **PASS** | both methods |
| D3 EME / governor / lockstep / DTC / latch / `FUN_0004595a` | **PASS** | full-range diff + cell table |
| D4 hook, branch targets, flash virginity, CRC ownership | **PASS** (one null is BELIEF, F3) | 14/14 controls |
| D5 fork `AccordCurvatureLead` OFF | **PASS** | fork working tree |
| D6 dead island 0x2A30E–0x2B421 | **PASS** | control passes |

---

## 0. The delta, re-derived independently

Full byte diff restricted to `[0x13000, 0x100000)` (never a whole-file diff — the `0xFF`-filler trap).

**V282 to V292: 10 runs, 69 bytes. V291 to V292: 5 runs, 58 bytes.** Exactly the claimed delta, nothing
more:

```
0x28F8E-0x28F92   f03f2002 -> 890772bc      hook
0xC4C00-0xC4C34   FF x52   -> the cave       (52 B)
0xC4FFC-0xC5000   26c4ce34 -> 584e432c      block-1 CRC trailer
   (+ inherited from V291, unchanged by V292: 0xC4BAA/AB, 0xC63E8, 0xC63EA/EB, 0xC6446/47, 0xC6FFC)
```

I decoded all 15 cave instructions and both `jr` displacements **from the bytes, by hand, before
reading the design's listing**, and they agree with it exactly. Hook `jr`: `hw1=0x0789` gives
`disp22 = +0x9BC72`, and `0x28F8E + 0x9BC72 = 0xC4C00`. Return `jr`: `hw1=0x07B6`, `hw2=0x4372` gives
`disp22 = 0x364372`, sign-extended `-0x9BC8E`, and `0xC4C30 - 0x9BC8E = 0x28FA2`. Confirmed.

---

## 1. D1 — the two remainder words and the 72-byte run — **PASS**

### 1.1 The scanner, and why its null is worth something

The design's scan enumerates known load/store opcode fields. Mine deliberately does **not**: it accepts
**any** halfword pair whose `hw1` bits [4:0] == 4 (`gp` == `r4`) and whose `hw2` matches the target
displacement or its `|1` / `&0xFFFE` parity variants, **regardless of opcode field**, and only then
classifies. An opcode-table error therefore cannot produce a false null in my census.

Encodings were derived empirically from stock control sites rather than from spec memory:

| form | control | bytes | rule |
|---|---|---|---|
| `ld.w -0x3d30,gp,r26` | `0x28F7C` | `24 d7 d1 c2` | op 0x39, `hw2 = disp OR 1` |
| `st.w r9,-0x3d30,gp` | `0x28FA8` | `64 4f d1 c2` | op 0x3B, `hw2 = disp OR 1` |
| `ld.h -0x6a56,gp,r7` | `0x28F4C` | `24 3f aa 95` | op 0x39, `hw2 = disp` (even) |
| `ld.hu -0x6a98,gp,r13` | `0x1982E` | `e4 6f 69 95` | op 0x3F, `hw2 = disp OR 1` |
| `st.h r13,-0x3ee4,gp` | `0x19C84` | `64 6f 1c c1` | op 0x3B, `hw2 = disp` (even) |
| `st.b r1,-0x3d2c,gp` | `0x290D4` | `44 0f d4 c2` | op 0x3A, `hw2 = disp` |
| `ld.bu -0x674e,gp,r12` | `0x28FC8` | `84 67 b3 98` | op 0x3C, `hw2 = disp OR 1` |

**Controls: 7/7 cells found** (`gp-0x3d30` 3 hits, `gp-0x3d34` 2, `gp-0x3d2c` 2, `gp-0x6a98` 46,
`gp-0x3ee4` 11, `gp-0x6a56` 30, `gp-0x674e` 10). A scanner that finds thousands of real gp touches
image-wide and then finds nothing on the target is a **verified** zero.

### 1.2 Result

| form | V292 | V291 | V282 | stock |
|---|---|---|---|---|
| 4-byte gp-relative, **instruction-aligned**, anywhere in the 72-byte run | **4** | **0** | **0** | **0** |
| 6-byte extended-displacement gp form, exact filter | **0** | — | — | — |
| Format-VIII gp bit-ops (op field 0x3E) | **0** | — | — | — |
| absolute LE32 pointer into the run, any byte alignment | **0** | — | — | — |
| `movhi 0xFEDF`/`0xFEDE` + reachable displacement | **0** | — | — | — |

The four are exactly the cave's:

```
0xC4C08  ld.hu -0x6d74,gp,r13     e4 6f 8d 92
0xC4C12  st.h  r13,-0x6d74,gp     64 6f 8c 92
0xC4C18  ld.hu -0x6d72,gp,r13     e4 6f 8f 92
0xC4C22  st.h  r13,-0x6d72,gp     64 6f 8e 92
```

**Adjudications (every raw hit given an exclusion reason):**

- **`0x22397`** — appears only when the scan steps by 1 byte. **Odd address; a V850 instruction cannot
  begin there.** Excluded: misaligned. Re-running on even offsets only removes it and leaves exactly
  the four cave sites.
- **Ten load/store-*shaped* sites with a displacement inside the run but a non-`gp` base register**
  (`0x223D2`, `0x22BEA`, `0x40788`, `0x4DC0E`, `0x64BE0`, `0x64CCC`, `0xBD2EE`, `0xBD6D6`, `0xBE62E`,
  `0xBEA16`). **All have `hw2` bit 0 == 0.** These are `jarl`/`jr`, not loads — the documented
  Format-V vs `0x3C`/`0x3D` opcode collision, whose discriminator is exactly `hw2` bit 0 (loads = 1).
  Excluded with reason. Independently: for any base `B` the effective address is `B + sx16(disp)`, so
  to land in the run `B` would have to lie in `[0xFEDF7FF4, 0xFEDF803B]` — within 0x3B of `gp` itself.
- **6-byte extended form.** The design's prefix rule (`hw0 AND 0xFFE0` in `{0x0780,0x07A0}`)
  **over-matches `jr`** — Ghidra decodes `0x14070` (`84 07 0c 98`, which fits that rule) as
  `jr 0x5d87c`. Safe direction for a null, but the rule is not what the design thinks it is. I derived
  the true layout from two Ghidra decodes — `hw2 = disp[22:7]`, `hw1[10:4] = disp[6:0]`,
  `hw1[15:11] = reg3` — and **validated it on three controls** (`0x48E56` gives `gp-0x6752`,
  `0x14820` gives `gp-0x4310`, `0x48E5C` gives `gp-0x4c2d`, 3/3 exact). The exact filter
  (`hw2 == 0xF325`) returns **0** on `gp` and **0** on any base.
- **Absolute-pointer scanner controlled** (finds the `imm32 0xCB844` at `0x28FCE`).

### 1.3 Alignment

`rem_b = 0xFEDF128C` — halfword- **and** word-aligned. `rem_a = 0xFEDF128E` — halfword-aligned, not
word-aligned. Both accesses are `ld.hu`/`st.h`, so **both are correctly aligned for their width.**
The halfword choice is what makes `rem_a`'s odd-word address legal; a `ld.w` there would have been a
misaligned access.

### 1.4 Boot value — **EVIDENCE, and I found the loop**

I did not take the mapping on trust. The `.data` initialiser is at **`0x1475C`–`0x14794`**, decoded by
Ghidra:

```
0x1475C  mov 0x86260, r14          ; SOURCE pointer
0x14766  mov 0xfedf11b0, ep        ; DESTINATION pointer
0x1476C  ld.w 0x0,r14,r8  / sst.w r8,0x0,ep      ; 16 bytes per iteration
         … r6, r15, r12 …
0x14782  addi 0x10, r14, r14
0x14786  mov 0x8ab18, r10          ; SOURCE END
0x1478E  addi 0x10, ep, ep
0x14792  cmp r10, r14
0x14794  bc 0x1476C
```

So flash `[0x86260, 0x8AB18)` maps to RAM `[0xFEDF11B0, 0xFEDF5A68)`, i.e.
`src(ram) = 0x86260 + (ram - 0xFEDF11B0)`.

| cell | RAM | flash source | bytes |
|---|---|---|---|
| **control** `gp-0x6AB0` (the known NON-ZERO cell that falsified an earlier "free" claim) | `0xFEDF1550` | `0x86600` | `88 02 88 02` — **mapping confirmed at an independent point 0x3A0 away** |
| `rem_b` `gp-0x6D74` | `0xFEDF128C` | `0x8633C` | `00 00` |
| `rem_a` `gp-0x6D72` | `0xFEDF128E` | `0x8633E` | `00 00` |

The whole 72-byte source `0x8633C–0x86383` is **all zero**, identical in V292, V291 and stock, and sits
inside a 238-byte contiguous zero region. So **both cells boot to exactly 0.**

The `.bss` fill at `0x147C0` writes `0xEBEBEBEB` into `[0xFEDEC000, 0xFEDEF920)` — **below**
`0xFEDF0000`, clear of the run.

### 1.5 The prereg's explicit overflow question — answered, PASS

*"Verify that a garbage remainder of 65535 cannot overflow `x*b + rem` or `s*a + rem`."*

`ld.hu` caps the cell at 65535 by construction. Driving the integer recurrence with a **maximal 65535
remainder injected every tick** and `|x| = 12000` sustained:

| term | value | int32 max | margin |
|---|---|---|---|
| `b*x + rem` | 11,496,000 + 65,535 = 11,561,535 | 2,147,483,647 | **x185.7** |
| `a*s + rem` (s driven to 187,508) | 180,448,231 | 2,147,483,647 | **x11.9** |

No overflow, and `|x| <= 12000` is **guaranteed at the hook** — see section 2.3. The `andi 0x3ff`
returns any value, boot garbage included, to `[0,1023]` in one tick.

---

## 2. D2 — fb state, cadence, bail path, registers, PSW — **PASS**

### 2.1 `gp-0x3d30` consumers — exactly three, all accounted for

| address | instruction | role |
|---|---|---|
| `0x28F7C` | `ld.w -0x3d30,gp,r26` | the filter reads `s_old` |
| `0x28FA8` | `st.w r9,-0x3d30,gp` | the filter writes `s_new` |
| `0xC4BA8` | `ld.w -0x3d30,gp,r6` | **the V291 `0x14A` bit-3 rung — READ ONLY** |

V282 has only the first two (the rung was not yet repointed). **The cave does not touch `gp-0x3d30`
at all.** Confirmed by reading `0xC4BA8` in context: `24 37 d1 c2` (`ld.w`), then `60 32`
(`cmp 0x0, r6`), then a `Bcond` — a sign test, no write-back to the state.

Sentinel `gp-0x3d2c`: exactly two accessors, `0x28F66` (`ld.bu`, read) and `0x290D4` (`st.b r1`,
write). **The cave touches neither.**

Bonus: `0xC63E8` and `0xC63EA` each have **exactly one reader image-wide** (`0x28F8A`, `0x28F86`) —
the pole cells remain private.

### 2.2 The cave's register and flag footprint, read off my own decode of all 15 instructions

- **WRITES:** `r7`, `r9`, `r13`, `r14` (plus the two discarded `r0` high words, as on stock).
- **READS:** `r16`, `r7`, `r26`, `r9`, `r13`, `gp`(r4), `tp`(r5).
- **NEVER NAMED:** `r25`, `r1`, `r6`, `r2`, `r10`, `lp`(r31), `ep`(r30), `sp`, and every other
  register. `r16` and `r26` are read-only and survive for `0x28FBE` and `0x28FA4`.

`r25` is set at `0x290AC`/`0x290C0` and tested at `0x29A60` (a filter bail forces skip 2). **The cave
cannot disturb it** — it never names it, and `jr` (not `jarl`) leaves `lp` alone.

**PSW: no hazard.** The cave's `add`/`andi`/`sar` all set flags. The first flag consumer after the
return point is `ble` at `0x28FAC`, and it is armed by `cmp r13,r26` at `0x28FA6` — downstream of the
return. `0x28FA2 add r7,r9` and `0x28FA4 add r9,r26` also set flags and are themselves overwritten by
that `cmp`; the intervening `st.w` sets none. No cave flag reaches a consumer.

### 2.3 The filter's guards, decoded from the image (not inherited)

```
0x28F40  addi 0x1,r6,r12 ; cmp 0x3,r12 ; bc 0x28F4C ; else jr 0x290B0    BAIL 1 (mode/index)
0x28F4C  ld.h -0x6a56,gp,r7                                              x
0x28F50  addi 0x2ee0,r7,r11        ; r11 = x + 12000
0x28F54  addi -0x5dc1,r11,r0       ; flags only: CY set iff r11 >= 24001
0x28F58  bnc 0x28F5E ; else jr 0x290B0                                   BAIL 2  |x| > 12000
0x28F5E  cmp r0,r14 ; bne 0x28F66 ; else jr 0x290B0                      BAIL 3
0x28F66  ld.bu -0x3d2c,gp,r9                                             SENTINEL
0x28F72  cmp 0x1,r9 ; bne 0x28F82
0x28F78  ld.w -0x3d34,gp,r6 ; ld.w -0x3d30,gp,r26      sentinel==1  -> normal
0x28F82  mov 0x0,r6 ; mov 0x0,r26                      sentinel!=1  -> s := 0   (RESET)
0x28F86  ld.hu 0x73ea,tp,r16   b ; 0x28F8A ld.h 0x73e8,tp,r9   a
0x28F8E  <<< HOOK >>>
```

- **`|x| <= 12000` is guaranteed at the hook** — BAIL 2 is *upstream*, and it tests `r7` while `r7`
  still holds raw `x`. The cave's output never re-enters it. Design claim **confirmed from the bytes.**
- **The guards are plausibility/mode, not engagement** — the filter runs on every tick that passes
  them, engaged or not. Consistent with the prior record.
- **Bail path:** all three bails `jr 0x290B0`, skipping the whole block including the hook. The cave
  does not run; the remainders keep their values.

### 2.4 The stale-remainder question — traced through the cave, harmless

On the first post-bail tick the sentinel forces `s_old = 0` (`mov 0x0,r26` at `0x28F84`). Walking the
cave with `r26 = 0` and a stale `rem_a` in `[0,1023]`:

```
mul r26,r9,r0     -> r9  = 0
add r13,r9        -> r9  = rem_a          (<= 1023)
andi 0x3ff,r9,r13 -> r13 = rem_a          (unchanged, already < 1024)
st.h              -> rem_a := rem_a       (no change)
sar 0xa,r9        -> r9  = 0
```

**Exactly inert** — not merely small. `rem_b` is likewise bounded to at most one count of `step_b`.
Confirmed rather than assumed.

---

## 3. D3 — EME / governor / lockstep / DTC / latch — **PASS**

The full-range diff is the strongest possible statement here: **every byte outside the three changed
runs is identical V291 to V292.** Read out explicitly for the named interlock cells:

| cell | addr | stock | V282 | V291 | V292 | V291==V292 |
|---|---|---|---|---|---|---|
| governor slew A / B | `0xC6206`/`08` | 512 / 205 | 512 / 205 | 512 / 205 | 512 / 205 | yes |
| shaper cal | `0xC61DA` | 1092 | 1092 | 1092 | 1092 | yes |
| EME int quad | `0xC674E`/`50`/`5A`/`5C` | +/-1024 | +/-5120 | +/-5120 | +/-5120 | yes |
| EME ramp triple | `0xC6768`/`6A`/`6C` | 0/1536/2048 | 5120 x3 | 5120 x3 | 5120 x3 | yes |
| DTC debounce | `0xC61C0`/`C2`/`C4` | 1600/896/1280 | 65535 x3 | 65535 x3 | 65535 x3 | yes |
| STEER_STATUS debounce | `0xC64B4`/`B6`/`B8` | 24688/16438/112 | 65535/65535/255 | same | same | yes |
| `gp-0x671d` SET / RELEASE | `0xC61FA`/`F8` | 5530 / 1024 | 5530 / 1024 | 5530 / 1024 | 5530 / 1024 | yes |
| r24 deadband | `0xC61F6` | 3 | 3 | 3 | 3 | yes |
| gain_B arm / other arm | `0xC6442`/`40` | 1024 / 2048 | 1024 / 2048 | same | same | yes |
| lane ceiling / sum clamp / fb clamp | `0xC61B4`/`BE`/`0xC62E6` | 512/15360/7680 | 3072/15360/46080 | same | same | yes |
| **r24 ENGAGED arm** | `0xC6446` | 512 | 5244 | **4725** | **4725** | yes (V291's, unchanged) |
| Ki / `0xC6444` | `0xC63E6`/`0xC6444` | 0 / 512 | 0 / 512 | same | same | yes |
| output-lag a / b | `0xC63EC`/`EE` | 992 / 507 | 992 / 507 | same | same | yes |

**Cells differing V291 to V292: NONE.**

*(Note: `0xC6598`, the EME float mirror, is a 32-bit float; read as int16 it is 0 in all four images,
so that row of the V291-D table should be read as a float. Byte identity V291 to V292 holds
regardless, from the full-range diff.)*

**`FUN_0004595a`** (the plausibility monitor): Ghidra gives body `0x4595A – 0x45A1F`. None of the three
changed ranges (`0x28F8E-92`, `0xC4C00-34`, `0xC4FFC-0xC5000`) intersects it, so it is
**byte-identical**. Its *inputs* change only by the intended mean-exact rounding: V292 removes a
-32-count DC offset from the feedback, which makes `|E|` and everything downstream of it **smaller**
at small demand, not larger — the safe direction for any threshold.

**The `gp-0x671d` latch is not made reachable.** Its SET/RELEASE cals are unchanged, its input channel
is the r24 lane, and the only r24 cal (`0xC6446`) is V291's, not V292's. V292 adds no new path to it.

---

## 4. D4 — the hook — **PASS** (one null is BELIEF; see F3)

### 4.1 Displaced instruction and branch targets

`0x28F8E` is `mul r16,r7,r0`, **exactly 4 bytes and halfword-aligned**, so it is `jr`-replaceable. `lp`
is untouched, so `jr`, never `jarl`.

**Raw Format-V + Format-III branch-target scan over the BUILT image**, with both documented traps
applied (odd targets rejected for the `prepare` collision; `hw2` bit 0 == 1 means load, not branch):
**21,229 distinct targets**, and **CONTROLS 14/14 PASS** — the three BAIL `jr`s to `0x290B0`, six
in-block `Bcond`s, the function entry `0x28EA6`, both engagement skips, **and both of the cave's own
`jr`s** (`0xC4C00` from `0x28F8E`; `0x28FA2` from `0xC4C30`).

| test | result |
|---|---|
| branch targets strictly inside `[0x28F90, 0x28FA2)` | **0** |
| `0x28FA2` targeted from anywhere other than the cave's return | **no** — one target, `0xC4C30` |
| `0xC4C00` targeted from anywhere other than the hook | **no** |
| Ghidra `get_bulk_xrefs` on all 11 halfwords `0x28F8E…0x28FA2` | **empty for every one** |

### 4.2 Flash

| check | result |
|---|---|
| `0xC4C00–0xC4C33` all `0xFF` on **V282** and **V291** | both yes |
| whole `0xC4BD8–0xC4FEF` (1048 B) all `0xFF` on both bases | yes |
| V292 leaves `0xC4C34–0xC4FEF` still `0xFF` | yes |
| 12-byte structure at `0xC4FF0` (`010101010000c6001300b200`) | **byte-identical** in V282, V291, V292 |
| `0x14A` telemetry cave tail `0xC4BD0–0xC4BD7` | **byte-identical** V291 to V292 |
| cave inside the block, not a gap | `0x13000 <= 0xC4C00 < 0xC4FFC` yes |

### 4.3 CRC ownership — verified by recomputation, not by reading the build script

`zlib.crc32`, both blocks, all three images:

| image | `[0x13000,0xC4FFC)` to `0xC4FFC` | `[0xC6000,0xC6FFC)` to `0xC6FFC` |
|---|---|---|
| V282 | `4eb06b44` = stored | `75eadf72` = stored |
| V291 | `34cec426` = stored | `ed9b12bb` = stored |
| **V292** | **`2c434e58` = stored** | **`ed9b12bb` = stored (identical to V291, so no cal edit)** |

Both the hook and the cave lie in block 1, which is the one recomputed.

### 4.4 Runtime flash checksum — the prereg did not name this; I hunted it

| probe | result |
|---|---|
| CRC32 polynomial constants (`0xEDB88320`, `0x04C11DB7`, `0x82F63B78`, `0x1EDC6F41`) as LE32 anywhere | **0** |
| CRC32 lookup-table signature | **0** |
| `mov imm32` materialising `0xC4FFC`, `0xC5000`, `0x13000`, `0xC4000` | **0** each |

**The decisive evidence is empirical, not static: V289's cave body occupied `0xC4C00–0xC4C8C`** —
verified by my own V282-to-V289 diff of the V289 image (`f0c10c29…`) — **overlapping the exact 52-byte
range V292 uses, and V289 flew on r62/r63.** Flash at `0xC4C00` is therefore *proven* executable on
this ECU with only the `0xC4FFC` trailer recomputed. That closes the runtime-CRC question far more
firmly than the static scan, which could in principle be blind to a hardware CRC peripheral.

### 4.5 Timing

Honda executes 6 instructions in the displaced span; V292 executes 1 `jr` + 15 = 16. **Net +10
instructions**, all cheap: 2 `ld.hu`, 2 `add`, 2 `andi`, 2 `st.h`, 2 `jr`. Order **~15 cycles**,
sub-microsecond. **BELIEF, flagged:** I did not verify the core clock or wait states, so I give no
microsecond figure. The empirical bound is better anyway — V289's cave was 53 instructions and flew.

---

## 5. D5 — the fork with `AccordCurvatureLead` OFF — **PASS**

Read from the operator's own fork working tree (`openpilots/raayyymond-StarPilot/StarPilot`):

- `common/params_keys.h:393` — `{"AccordCurvatureLead", {PERSISTENT, BOOL, "0", "0", …}}`: default
  **"0"**, safe-mode default **"0"**.
- `starpilot/common/starpilot_variables.py:828` — read with `default=False`.
- `system/the_galaxy/tests/test_device_settings_layout.py:504` — asserts the declared default is `"0"`.
- `selfdrive/controls/controlsd.py:607` — the toggle is a **conjunct in the guard**:
  `if (CC.latActive and self.starpilot_toggles.accord_curvature_lead and not …)`. With it False the
  block is skipped and `new_desired_curvature` is not modified.

So with the toggle OFF, **nothing changes on the openpilot side.**

---

## 6. D6 — the dead twin island `0x2A30E–0x2B421` — **PASS**

| cell | accessors inside the island |
|---|---|
| `gp-0x6D74` (`rem_b`) | **0** |
| `gp-0x6D72` (`rem_a`) | **0** |
| `gp-0x3d30` (fb state) | **0** |
| `gp-0x3d2c` (sentinel) | **0** |

**Positive control PASSES:** the same scanner, aimed at `tp+0x73EC` = `0xC63EC`, finds the island's
known reader at **`0x2A8A2`**. A scanner that finds the island's own read and then finds nothing on
the touched cells is a verified zero. `0xC63E8`/`0xC63EA` have one reader each image-wide, neither in
the island.

---

## 7. Defects found — all in the EVIDENCE, none in the build

### F1 — the "zero new liveness claims" argument, as written, is FALSE

`DESIGN-V292-FBLP-CAVE-2026-09-13.md` section 3.2 and the agent-memory file
`reference_accord_0x28f8e_zero_liveness_hook_in_the_fb_filter.md` both state that the span
*"unconditionally **WRITES** `r7`, `r9`, `r13`, `r14` **before reading any of them**."*

From the image, that is wrong for two of the four:

```
0x28F8E  mul r16,r7,r0      READS r7 before writing it   (r7 = x, from ld.h -0x6a56,gp,r7 @0x28F4C)
0x28F92  mul r26,r9,r0      READS r9 before writing it   (r9 = a, from ld.h 0x73e8,tp,r9  @0x28F8A)
```

**`r7` and `r9` are LIVE-IN to the span.** The claim holds only for `r13` and `r14`.

**The conclusion survives** — the cave replicates both `mul`s verbatim as its first two instructions,
consuming the live-in values identically, so nothing is lost. But the *proof* is not the proof that
was written, and the correct statement is narrower: *nothing after `0x28FA2` needs the pre-hook values
of `r7`/`r9`/`r13`/`r14`, and the cave preserves the two live-in reads by replicating the muls first.*

**Why this matters beyond bookkeeping:** the argument is presented as the property that makes this the
right hook, and the memory file is written to be reused at future sites. Applied to a site where the
live-in operands are *not* replicated, it would license an unsafe cave. **Recommend correcting both
the design section 3.2 and the memory file.**

### F2 — the GATE 1 census is incomplete: there IS a non-cave writer

The design's GATE 1 table reports **"ZERO on either cell, and ZERO anywhere in the whole 72-byte run."**
There is one writer it cannot see, because it is **register-indirect** and a gp-relative operand scan
is structurally blind to that class:

**the boot `.data` copy loop at `0x1476C`–`0x14794`** — `sst.w` with `ep` walking from `0xFEDF11B0`,
source `0x86260` to `0x8AB18`. `0xFEDF128C`/`0xFEDF128E` are inside its destination range.

**Harmless** — it runs once at boot, before the 1 kHz task, and writes `00 00` (I verified the source
bytes). It is in fact the very mechanism that produces the boot value the design asserts. But the
census sentence should read *"zero accessors other than the boot `.data` initialiser."* This is the
`gp-0x1500` failure class — the one that passed both static methods and still failed on-car — so the
distinction is worth keeping sharp.

I searched for a **runtime** block writer as well and found none: every `mov imm32` with a RAM operand
was enumerated (331 sites, 15 distinct base values), each base's maximum observed displacement was
computed, and **no (base, displacement) pair lands in the run**. The one `mov 0x55555555` in the image
(`0x69F1A`) is not a RAM march over this region.

### F3 — the indirect-jump null is UNCONTROLLED and is reported as BELIEF, not EVIDENCE

I scanned for any LE32 word anywhere in the image pointing into `[0x28F90, 0x28FA2)` — a jump-table
entry or function pointer that a static branch scan cannot see. **Result 0 — but the control FAILED:**
no LE32 word equals *any* of six known-live entries (`0x28EA6`, `0x34350`, `0x3AA2C`, `0x290B0`,
`0x22522`, `0x2A174`). The image apparently stores no absolute code pointers in that form, so the
scanner would not have found one had it existed. **A null from an uncontrolled scanner is worth
nothing, and I am not counting it.**

What stands instead: Ghidra's `get_bulk_xrefs` is empty on all 11 halfwords, and a computed jump
landing 4 bytes into a straight-line arithmetic span is not a shape a compiler emits. **Marked
BELIEF.** Exact next step to convert it: a Ghidra `search_instructions` sweep for `jmp [reg]` sites,
then bound each one's switch table, and confirm none can produce a target in the span.

### F4 — the design overstates its own control coverage (minor)

The design lists `ld.bu -0x3d2c` at `0x28F66` as *"an **odd** displacement, exercising the parity
trap."* **`0x3d2c` is even.** Both of its `ld.bu` controls (`-0x3d2c`, `-0x674e`) decode to opcode
field `0x3C`, the even form; the odd form (`0x3D`) was never exercised. No effect on the verdict — my
census was opcode-agnostic for *finding* — but the claimed 8/8 control set covers 7 distinct forms,
not 8.

---

## 8. What a FAIL would have looked like, and why this is not one

Written so the pass is falsifiable rather than decorative. A DO-NOT-FLASH on this surface required any
of: a second accessor of either remainder cell; any accessor anywhere in the 72-byte run on the bases;
a branch target inside the displaced span; a live register or a flag clobbered at the hook; a changed
EME/governor/lockstep/DTC/latch cal; the wrong CRC block recomputed; the cave's flash not virgin; or
the island touching a changed cell. **Every one of those was tested and none occurred.** The four
defects are in the documentation and the evidence, and correcting them does not move a single byte of
the image.

## 9. Residuals carried forward (not blockers)

1. **F3**, the indirect-jump null, is BELIEF. Next step named above.
2. `0x28FA2`'s downstream `+/-46080` clamp (`0xC62E6`) and the r24 arm at `0xC6446` are **V291's**
   risks, already adjudicated on that build; V292 neither adds to nor removes them.
3. The +10-instruction cost is bounded empirically by V289, not by a cycle budget I verified.

## 10. Tooling note for the rest of the pass

**The current GhidraMCP program can change under an agent mid-task** when another agent imports an
image; nothing in the tool output flags it, and reads simply start answering from a different binary.
I hit this: three reads I believed were against `code.bin` were against `advA2`'s freshly imported
V292 image, and I briefly reported a false "stock database corrupted" alarm before catching it with
`get_current_program_info` and retracting. `code.bin` is intact and stock (`0x28F8E = f0 3f 20 02`,
`0xC4C00 = FF…`, `0xC63E8 = 9b 03 18 06`, re-read after an explicit `switch_program`). **Any
stock-versus-built claim from Ghidra this session should call `switch_program` explicitly first.**
