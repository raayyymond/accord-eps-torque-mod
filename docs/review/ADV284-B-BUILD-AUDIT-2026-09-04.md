# ADV284-B — ADVERSARIAL BUILD-SCRIPT & ARTIFACT AUDIT, V284

**Agent:** `adv284B` (subagent; adversary on the BUILD-SCRIPT / ARTIFACT surface only).
**Date:** 2026-09-04. **Target:** V284, `build_v284_tva.py`, its plain image and its `.rwd`.
**Explicitly NOT my surface:** the arithmetic (adv284A), the unit/scale chain, the interlocks/downstream census.

## VERDICT: **FLASH — WITH FOUR NAMED CAVEATS**

The **artifact is sound**. I reproduced it bit-for-bit with my own code, and every byte-level and CRC-level
gate is clean under independent implementations. The caveats are all defects in the build's **self-description
and self-assessment** — the assertion census and two docstring numbers — not in the bytes that will be flashed.

---

## 1. PRE-REGISTERED FAIL CRITERIA (written before opening any artifact)

Recorded at `…/scratchpad/advB/FAIL-CRITERIA.md` before the script or images were read.

| | A FAIL on my surface is… | Result |
|---|---|---|
| **F1** | My independent rebuild does not reproduce `1b46f24f…` bit for bit | **CLEAN** |
| **F2** | Any byte differs V282→V284 outside the claimed 12; any other slot/map/taper/FROZEN/count/pad/cave moved; anything outside `0x13000-0x100000` | **CLEAN** |
| **F3** | Any page CRC stale under my own block map; more or fewer than one trailer changed | **CLEAN** |
| **F4** | `.rwd` not byte-identical over the extent; wrong extent; >1 flashable rwd; a differing sibling | **CLEAN** |
| **F5** | The claimed substantive count inflated >25 % vs my classification; a load-bearing docstring claim with no assertion; a stale hard-coded expectation | **TRIPPED** → caveats 1, 2, 3 |
| **F6** | Any docstring number not reproducible from the built image | **TRIPPED** → caveat 4 |
| **F7** | Any of the builder's three "surprises" false | **CLEAN — all three TRUE** |

A caveat verdict was pre-authorised in the same file for "findings that are real but do not endanger the
flash". F5 and F6 are exactly that class: nothing they touch changes a flashed byte.

---

## 2. F1 — INDEPENDENT REBUILD  ✅ **[EVIDENCE]**

I wrote my own minimal builder (`b3_rebuild.py`). It imports **nothing** from the kit — not the build
script, not `build_vfourframe_tva`, not `verify_bootloader_crc`. It walks `u32(0xCB994 + 4*7)` → `0xE5378`,
checks the count word is 5, packs the ten halfwords, then re-CRCs using **its own linked-list block walker**
built from the trailer fields (`u16(END-8)`, `u16(END-6)`) read out of the image.

```
[REBUILD] pointer u32(0xCB994+4*7) = 0xE5378; count word = 5
[REBUILD] re-CRC'd blocks: [('0xe5000', '0xe5ffc')]
[REBUILD] my sha256   = 1b46f24f3ea0988a7786d4dd4cfc4db84bba2f41d44f3a2176386727828b74ff
[REBUILD] on-disk sha = 1b46f24f3ea0988a7786d4dd4cfc4db84bba2f41d44f3a2176386727828b74ff
[REBUILD] MATCH: True
```

**This closes a gap the script's own `[9]` does not.** `independent_rebuild()` uses `FF.crc_block_map`, and
`V53.owning_block` — used by `build()` — calls **the same `crc_block_map`**. The script's "second
implementation with no shared state" is independent in the *record-writing* path but **shares the
CRC-block-locating path with `build()`**; a fault in `crc_block_map` would be invisible to both. My walker
is a genuinely separate derivation and agrees. *(See caveat 3.)*

---

## 3. F2 — FULL-FILE DIFF  ✅ **[EVIDENCE]**

Diffed over the **whole 1 MiB file**, not just the flashed extent:

```
TOTAL diffs V282 -> V284 over the WHOLE FILE: 12 bytes in 6 runs
  0xE537C (1 B)  44 -> 20      X[1]  68 -> 32
  0xE537E (1 B)  70 -> 24      X[2] 112 -> 36
  0xE5380 (1 B)  88 -> 2c      X[3] 136 -> 44
  0xE5382 (1 B)  d0 -> 58      X[4] 208 -> 88
  0xE5388-0xE538B (4 B)  f800f800 -> 00020002    Y[2],Y[3] 248 -> 512
  0xE5FFC-0xE5FFF (4 B)  7ea6f28e -> 2a7055f2    page CRC
bytes outside 0x13000-0x100000: NONE
```

Exactly the 12 claimed, in the 6 claimed runs. Verified independently:

- **All 28 Kp slots enumerated through the pointer table** — pointers identical V282/V284, all 28 distinct,
  span `0xE4360`–`0xE8288`, **only slot 7 changed**; no other record overlaps slot 7's 24 bytes.
- **Count word** `rec+0x00` = 5 and **pad** `rec+0x16` = 0 on **both** images — untouched.
- **28 Kd slots, 28 assist maps, 112 distinct tapers, 19 FROZEN cells** — all byte-identical. `Ki 0xC63E6 = 0`
  on V284 (V283 sibling carries 50). Cave `0xC4B34-0xC4BD7` (164 B) identical, sha256[:8] `e9596ad9`.
  Hook `0x55C0E` = `86ff26ef`. 427 tap window `0x55DF0-0x55E11` identical. Code region `0x29DC6-0x29E3B`
  byte-identical.
- The blanket-write failure mode this build set out to avoid **did not occur.**
- Page layout confirmed as claimed: `0xE4000` slots 0-5 · `0xE5000` 6-11 · `0xE6000` 12-17 · `0xE7000` 18-23 ·
  `0xE8000` 24-27. Fallback Y by slot confirmed from the image: 205 (0,2,4,5) · 266 (1,6) · 248 (3,7,8,9) ·
  307 (10-27).

---

## 4. F3 — EVERY PAGE CRC, RECOMPUTED FROM SCRATCH  ✅ **[EVIDENCE]**

My own chain walker, from the image's own trailer fields:

```
V282: 50 blocks, 0 stale.   V284: 50 blocks, 0 stale.
chain covers 970,752 bytes = 100.0 % of 0x13000-0x100000 (no uncovered region)
bootloader-faithful walk (0xC6000 bridge replayed): 49 blocks, 0 failures — on BOTH images
exactly one trailer changed: 0xE5FFC.  0xE4FFC / 0xE6FFC / 0xE7FFC / 0xE8FFC bit-unchanged.
```

A naive 4 KB-page scan finds only 46 self-consistent pages; the chain is the correct model and it closes at
50 with full coverage. No stale CRC anywhere. **No DO-NOT-FLASH on the CRC surface.**

---

## 5. F4 — THE `.rwd`  ✅ **[EVIDENCE]**

I wrote my own x31 parser and — rather than take the kit's keys/ops — **derived the 256-byte decode
substitution from the V38 `.rwd` + V38 plain-image pair**. It is bijective over all 256 values, which is
itself a check that the cipher really is a byte substitution.

```
V284 rwd sha256 = f42cfc9b2a197c27a5e14fd059f1f704a2e6f3f27dec3604f822b6771a47e724   (matches)
block start 0x13000, length 0xED000 -> end 0x100000   — extent is exactly as claimed
decoded rwd == plain image over the extent: True
decoded image: CRC chain 50 blocks / 0 stale; bootloader walk 49 / 0 failures
headers: '/' = ['39990-TVA-A110', '39990-TVA,A160']   — correct part number
```

Disk scan of the entire `accord-firmwares` tree: **exactly one** V284 image and **exactly one** V284 `.rwd`,
no byte-identical duplicate, **no differing sibling**. Both are untracked in git and still need committing.

---

## 6. F7 — THE BUILDER'S THREE "SURPRISES": ALL THREE TRUE  ✅ **[EVIDENCE]**

**(i) V281 rev 2 *lowered* the knots, and its record differs at 10 bytes, not 2.** Confirmed by direct read
of `SUPERSEDED_v281_rev2_FLAT341_plain_image.bin`: X (0,68,112,136,208) → **(0, 24, 68, 136, 208)** — X[1]
68→24 and X[2] 112→68, both **lowered**. Record bytes differing from the V282 base: **10**
(`0xE537C, 0xE537E, 0xE5386-0xE538D`), and `0xE537C`/`0xE537E` are indeed two of the offsets V284 also writes.

**(ii) Two V284 bytes coincidentally equal V280 rev 2's stock bytes.** Confirmed: `0xE5389` and `0xE538B`
(high bytes of Y[2]/Y[3]) are `0x02` in both, because 512 = `0x0200`, 645 = `0x0285` and 696 = `0x02B8` all
share high byte `0x02`. The cumulative count comes out exactly 2 short: V284-vs-V280r2 = **230 B**, union of
the three known deltas = **232 B**, and `d_284_280` is a subset of the union. A coincidence of encoding, not
a reverted lever.

**(iii) `0x29DDA` publishes the demand index to RAM every tick.** Confirmed by **two methods**. My byte
decode of `643f 8696`: src `r7`, base `r4` (= gp), disp `-0x697A` → target `0xFEDF1686`. GhidraMCP
(`dry_run` on the V282 image) independently returns `st.h r7, -0x697a, gp`. `r7` is the same register the
LERP then compares against X[0] at `0x29DEA`, so the stored halfword is the index the lookup uses. The tap
site named in the null-sentence is real.

---

## 7. F5 — ASSERTION RE-CENSUS  🛑 **THE FINDING**

**Note first:** the script self-reports **429/429** in dry-run, not the 432 relayed to me. The extra 3 are
inside `if WRITE_MODE == "rwd"` — the on-disk image re-hash, the on-disk rwd re-hash, and the
"exactly ONE flashable V284 rwd" check. **Three of the "substantive" assertions never run in a dry-run
verification.**

### The script's split vs mine

| | script | mine |
|---|---:|---:|
| SUBSTANTIVE | **269** | **~54**, of which ~41 bear real load |
| vacuous | 26 | 30 |
| tautological | 2 | 2 (+4 constant self-checks) |
| redundant | 132 | **~339** |

**Inflation factor on the substantive count: ~5×.** My F5 threshold was 25 %. **F5 trips.**

### The entailment, proved not asserted (`b8_entail.py`)

Step `[3]` asserts, **first**:

```python
outside = [a for a in range(START, END) if a not in attributed and code[a] != base[a]]
check(outside == [], ...)          # labelled "S"
```

That proves `code[a] == base[a]` for **every** address in `[0x13000, 0x100000)` outside the 20 written
record bytes. I then collected the address range of every "byte-identical" assertion that follows it and
showed mechanically that **all 221 lie inside the extent and none intersects the 20 written bytes**. None
can fail while `outside == []` passes.

**203 of the 269 "SUBSTANTIVE" assertions are therefore REDUNDANT under the script's own definition:**

| family | count |
|---|---:|
| `taper 0x… byte-identical` | 112 |
| `assist map 0x… byte-identical` | 28 |
| `Kd slot N byte-identical` | 28 |
| `Kp slot N byte-identical` | 27 |
| cave + 4 cave sites | 5 |
| hook · 427 tap window · `Ki still 0` | 3 |
| **total entailed by `outside == []`** | **203** |

The script **already applies exactly this reasoning** to the 19 FROZEN re-reads sitting between
`outside == []` and these 203 — it labels those `"R"` with the comment *"entailed by the base read in [1] +
`outside == []` immediately above"* — and then does not apply the same rule to the 203 that follow in the
same block under the same entailment. This is the V274 shape: a large passing count that is mostly one
assertion wearing 203 costumes.

Further reclassifications:

- **4 should be VACUOUS, not substantive** — `all 28 pointers DISTINCT`, `NOT contiguous at stride 0x18`,
  `28 records live on exactly 5 pages`, `no other record overlaps slot 7`. All are reads of the **base**
  image, entailed by `BASE_SHA` — the script's own definition of V.
- **4 are constant self-checks** — the `constants gate:` block tests the module's own literals
  (`NEW_KP_X`, `NEW_KP_Y`), not the image. Useful as a guard against a bad edit to the file; zero evidence
  about the artifact. The image-side twins (`IMAGE X strictly increasing`, `every segment width read from
  the image is > 0`) **are** substantive and are the real divq brick gate.
- **4 are weakly redundant** — the `page 0x… CRC trailer UNCHANGED` checks in `[5]`; entailed by
  construction (one `pack_into` to `b1`) rather than by a prior assertion. Cheap and defensible.

### The assertions that actually carry load (~31 decisive)

`V282 base sha256` · **`outside == []`** (the load-bearing assertion of the whole build) · `exactly 20 record
bytes written` · `COUNT word untouched` · `PAD untouched` · the four CRC-surface checks (`exactly ONE block
owns the edit`, `block is [0xE5000,0xE5FFC)`, `no edit on the trailer`, `CRC actually moved`) ·
`walk_all_blocks == 0` and `walk == 0` on the built image · the four `[6]` diff checks (`set(diff) ⊆
attributed`, `payload == 8`, `len(diff) == 12`, `every diff inside the record or trailer`) · the four `[7]`
rwd checks including the **non-circular cipher validation against the V38 plain image** · `[9]`'s rebuild ·
`IMAGE X strictly increasing` + `segment width > 0` · the **regex pin to `STUTTER-7HZ-…A11.4`** · the V280r2
and V281r3 hash checks + the stock-LERP read · the seven gain-band checks.

The regex pin is the best assertion in the file: it fails if the study and the build ever disagree about the
M8★ table. Most builds have no such link at all.

### Weak spots inside the load-bearing set

- **Two external images are read with NO hash assertion.** `BASE_SHA`, `PARENT_SHA` and `GRANDPARENT_SHA`
  are all asserted; `REV2_NAME` and `SIBLING_NAME` are **not**. Eight "S" assertions rest on files whose
  identity is unverified — swap either file and they silently change meaning.
- **The sibling block fails open.** `[1d]`'s rev-2 guard does `check(False, …)` when the file is missing —
  correct. `[6b]`'s V283 guard just **prints and skips**, so five "S" assertions can vanish without failing
  the run. Asymmetric; the `[1d]` pattern is the right one.
- **Five `gain@idx == PREREG_CURVE` checks are stale hard-coded expectations.** `PREREG_CURVE` is a literal
  dict transcribed by hand from the study. The X/Y knots *are* live-pinned by the regex; the curve values
  (506/416/296) are not, and would not notice if the study changed.

---

## 8. F6 — DOCSTRING vs IMAGE  🛑 **TWO NUMBERS DO NOT REPRODUCE**

Everything checkable reproduces **except two**, both in the same sentence, and **neither has an assertion
behind it**:

> *"⚠ The 32→36 leg is 4 wide — **99 Kp counts per index step**, the steepest ramp in any shipped record
> (**Honda's narrowest is 48**)."*

**(a) "99 Kp counts per index step" is wrong — it is 66.** Read from the built image: the 32→36 leg is
ΔY = 512−248 = 264 over ΔX = 4 → **66.0 counts per index**. The delivered curve steps
`idx 32..37 = [248, 314, 380, 446, 512, 512]`, i.e. **+66 per index**, max per-index step 66 at idx 33-36.

**(b) "Honda's narrowest is 48" is wrong — it is 24.** Across all 28 shipped Kp records on the V280 rev 2
image the segment widths are `{24, 32, 44, 48, 64, 68, 72, 80}`; the narrowest is **24** (the 112→136 leg of
the stock X axis, present on slot 7 itself).

**Both errors run in the conservative direction** — the docstring makes the leg sound *steeper* (99 vs 66)
and *more unprecedented* (4-vs-48 rather than 4-vs-24) than it is. The flown risk is lower than advertised,
not higher, so neither is a flash blocker. But they are unasserted numbers in the permanent record, and the
sentence they sit in is the build's own headline safety caveat.

**The companion claim in the same sentence is TRUE and is the one worth keeping:** 66 counts/index against
Honda's steepest shipped ramp of **5.33** counts/index — V284's leg is **12.4× steeper than anything Honda
ships**. That is a much stronger statement than the width comparison and it survives correction.

Everything else checks out from the image: prereg curve exact at all seven indices (248/248/248/506/416/296/248) ·
gain changes on **exactly idx 33-87**, 55 of 256 · never drops at any index · peak 512 = **2.065×** 248
("2.06×") · stock LERP peak 696, `512 < 696`, `0.7356` ("0.74×") · idx 0-32 and idx 88-255 bit-identical to
V282 · narrowest X segment 4, strictly increasing · cave 164 B.

**Load-bearing docstring claims with NO assertion at all** (naming them, per my brief):
the benefit / ring-return / P-rail table (1.622 · 0.949 · 0.0036) and the per-route chain |T| figures
(1549/1289/954/1738) — study outputs, unfalsifiable from the image, and the *entire* justification for the
table · the `gp-0x674e` selector census (one writer at `0x4272A`, four reads), which is the load-bearing
argument for slot-7-only · *"the selector maxes at 9"* · *"idx 0-32 is 18.2 % of engaged time"*, which
appears inside an assertion **message** whose condition tests only `NEW_KP_X[1] >= 32`.

---

## 9. THE FOUR CAVEATS

1. **The assertion census is wrong by ~5×.** 203 of 269 "SUBSTANTIVE" are redundant, entailed by
   `outside == []` asserted earlier in the same block. Real substantive count ≈ 54, decisive ≈ 31. Correct
   the census in the record; do not let "269 substantive" stand as the build's evidence weight.
2. **Two docstring numbers are wrong** — 99 counts/index (it is 66) and Honda's narrowest segment 48 (it is
   24). Both err conservatively. Replace with the stronger true claim: 66 vs Honda's steepest 5.33, i.e.
   12.4× steeper than any shipped ramp.
3. **The script's `[9]` "independent rebuild" is not fully independent** — it shares `crc_block_map` with
   `build()` via `V53.owning_block`. My own walker closes this; the reassurance comes from **this audit**,
   not from the script.
4. **Two external images are read without a hash assertion** (`SUPERSEDED_v281_rev2_…`, `_v283_…`), and the
   V283 sibling block **fails open** — five "S" assertions skip silently if the file is absent. Three
   further "substantive" assertions run only in write mode.

**None of the four changes a flashed byte.** All four are record/process defects.

---

## 10. WHAT WOULD HAVE MADE ME SAY DO-NOT-FLASH

A hash mismatch on my own rebuild; any 13th differing byte; a stale CRC on any of the 50 blocks; a byte moved
in another slot, a map, a taper or a FROZEN cell; a duplicate or differing `.rwd`; a duplicate X knot
(divq-by-zero — the one genuine brick path on this record); or a `.rwd` that did not decode back to the image.
**I checked every one of those with my own code and none of them is present.**

---

*Reported by `adv284B` to the orchestrator. Findings arriving after acceptance are reports, not licence to
act — I have modified nothing but this file.*
