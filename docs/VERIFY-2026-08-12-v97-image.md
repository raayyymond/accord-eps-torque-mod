# VERIFY 2026-08-12 — V97 image byte verification

Pure Python byte work, no Ghidra used (per task). All reads from disk with
`ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares`, interpreter
`C:/Users/dudei/anaconda3/envs/bin_decompile/python` (3.12.13). Every claim below is
**EVIDENCE** (a from-disk read or script re-run), not a relayed report, unless marked BELIEF.

---

## 1. Hash re-check — MATCH

```
.rwd   78c674a899971a6a9763c2d7c89bf4c9169f35dfba3fbe4ce62d9bc445a17372   986,042 bytes
image  7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3  1,048,576 bytes
```
Both recomputed from disk match the quoted values exactly.

## 2. Rebuild reproduction — bit-for-bit, PASS

`build_v97_tva.py` re-run twice:
- Dry run (`ACCORD_V97_WRITE` unset): 127/127 assertions PASSED, image/`.rwd` SHA256 identical
  to the quoted values (encode+readback runs even in dry mode; only the disk write is gated).
- Full run (`ACCORD_V97_WRITE=rwd`): re-writes the *same* bytes back (script refuses to overwrite
  a differing file; the existing files matched, so this was a no-op content-wise) and runs the extra
  "shipped .rwd re-read" block → **131/131 assertions PASSED**.

**The quoted "131/131" is the full-run assertion count, not a CRC block count.** The CRC chain
itself is **50 blocks, 0 mismatches** (`walk_all_blocks` → `50 block(s) checked, 0 mismatch(es) ->
PASS`), consistent with every other build in the kit. No discrepancy — the task brief's "CRC block
count (claimed 131/131)" conflated the two; flagging so the number isn't misfiled as a block count.

## 3. Address / value check — the crux, PASS

Independent script (not `build_v97_tva.py`'s internal checks) reads `0xC63AC` as an LE halfword
directly from stock, V96, and V97:

| image | 0xC63AC |
|---|---|
| stock | 102 |
| V96 | 102 |
| V97 | **150** |

Address anchored two ways:
- `tp(0xBF000) + 0x73AC == 0xC63AC` (computed); the off-by-0x1000 trap address `0xC73AC` is a
  different, unrelated value — the recurring trap is excluded by construction, not by inspection.
- The six neighboring weight cals `0xC63A0, 0xC63A2, 0xC63A4, 0xC63A6, 0xC63A8, 0xC63AA, 0xC63AE`
  all read **1024** in stock/V96/V97 unchanged. `0xC63AC` alone moves, and only its low byte
  (`0x66→0x96`; high byte `0x00` in both) — rules out a neighbor-cell misread.

## 4. Full byte diff, V96 → V97 — exactly the cal + its CRC trailer

```
0xC63AC : 0x66 -> 0x96        (the cal, low byte only)
0xC6FFC : 0x70 -> 0x14   \
0xC6FFD : 0x1e -> 0x3b    | CRC-32 trailer of block [0xC6000,0xC6FFC), old 0x31281E70 -> new
0xC6FFE : 0x28 -> 0x00    | 0x0F003B14 — matches the builder's own recomputed value exactly
0xC6FFF : 0x31 -> 0x0f   /
```
**5 bytes total, zero unattributed.** No other byte differs anywhere in `[0x13000, 0x100000)`.

## 5. Full byte diff, STOCK → V97 — the cumulative non-stock delta

270 differing bytes in `[0x13000, 0x100000)`, grouped into **113 contiguous runs**. Each run was
attributed to its first-appearing build by walking the direct lineage chain that actually produced
V97 — **not** the full V22–V86 branch, because **V87 forked fresh from the V38 image**, discarding
V39–V86 except specific cherry-picked cal values (matches `BUILD-LINEAGE.md` / the golden model's
recorded rebase history). Chain used: `stock → V38 → V87 → V88 → V89 → V90 → V92 → V96 → V97`.

| introducing build | runs | bytes | what it is |
|---|---:|---:|---|
| **V38** | 97 | ~185 | the LKAS 4×/corridor/EME/DTC/lockout/CRC-trailer baseline — everything V22–V38 folded together (this lineage forks from the V38 image, so finer sub-attribution within V22–V38 is not resolvable from this chain alone) |
| **V87** | 8 | ~124 | `0x2A1F0-1` (V57 gain restore), `0x454FE` (V42 ratchet fix, **restored** — see below), `0x55C0E-11`/`0x55DF2-3` (telemetry hook/CAN427 repoint), `0xC4B34-0xC4BA3` (111-byte cave, V87's own 427/`gp-0x6b98` probe), `0xC62EA-B` (V53 steer-to-zero), `0xC6CD0-1` (V57's 4× forward LKAS gain) |
| **V88** | 2 | 3 | `0x3AA96` (Lever B gate), `0xC6446-7` (Lever B arm 512→5244) |
| **V89** | 1 | 1 | `0xC40D2` (K1 friction, 102→204) |
| **V92** | 4 | 17 | `0x55E10` (CAN427 packer scale, sar4), `0xD7A5C-61`/`0xD7A6C-71`/`0xD7FFC-FF` (mode-record duplicate table + its CRC trailer — the `0xCBE74` ×1.5 dose; **the address `0xCBE74` itself is a pointer/index and never moves** — see note below) |
| **V97** | 1 | 1 | `0xC63AC` — this build's own edit |
| **total** | **113** | **270** | |

⚠ **Correction to the task brief's cell list**: `0xCBE74` read as an LE value is **byte-identical
across every sampled image, stock through V97, including V91/V92**. Dumping the surrounding 0x40
bytes shows the whole region `[0xCBE60,0xCBEA0)` is untouched in every image checked (stock, V90,
V91, V92, V96, V97) — it holds what looks like a small pointer/index table (24-bit LE addresses into
`0xC7xxx`/`0xD0xxx`/`0xD1xxx`), not the dosed scalar. The actual "×1.5 dose" bytes documented in
memory (`accord-cbe74-dose-measured-inert-wrong-mode-record.md`) live in the **mode-record mirror
table at `0xD7A5C`/`0xD7A6C`** (+ its own CRC trailer at `0xD7FFC`): stock `9ad9 9ae9 52f8`, V91/V92
`67c6 67de 7bf4` (the ×1.5 row), V93/V94 `66f6 66fa 14fe` (the cut), **V96/V97 back to `67c6 67de
7bf4`** — i.e. V96's "REVERT.CBE74" reverted the V93/V94 cut **back to V91/V92's ×1.5 value, not to
stock**. This is a from-disk correction of the address, not a change to any conclusion already on
record (the memory file's own analysis was keyed to the correct D7Axx bytes).

## 6. `.rwd` / image inventory — exactly one per build number

```
rwd dir : 39990-TVA,A160-V96-...rwd   (one)
          39990-TVA,A160-V97-...rwd   (one)
bin dir : _v96_..._plain_image.bin    (one)
          _v97_..._plain_image.bin    (one)
```
`find $ACCORD_FIRMWARE_ROOT -iname "*v95*"` → **0 results, anywhere in the firmware root.**
Confirmed: **no V95 `.rwd` and no V95 plain image exist on disk at all** — not merely "gone", never
found in this listing. (The record's claim that Ghidra still holds two V95 programs pointing at
missing files was **not checked** here — this task was scoped to pure Python byte work with no
Ghidra tool calls, per the brief. Reporting the disk-side half only, as instructed: confirm, don't fix.)

No superseded/duplicate V96 or V97 artifacts exist under any name (checked the full `rwd/` listing).

## 7. Cross-build cell matrix (read from images, not scripts)

`ledger_v94_cells.py` was **not used** — brief flags it silently ignores `LEDGER_TARGET=V96` in
`grid` mode and `KeyError`s in `matrix` mode; worked around with a direct from-images reader instead
(no fix applied to the ledger script, per "report, don't fix").

Sampled at `stock, V38, V42, V53, V57, V62, V67, V71C, V72, V73, V74, V75, V76, V80, V81, V83A, V84,
V85, V86, V86B, V87, V88, V89, V90, V91, V92, V93, V94, V96, V97` (30 images spanning the whole arc;
denser than a bare stock-vs-V97 pair so reversions are visible, not just endpoints).

| address | width | V97 value | frozen (of last N sampled builds ending at V97) | notes |
|---|---|---:|---|---|
| `0xC63AC` | u16 | 150 | **1** — this build | Path-2 IIR pole, V97's own edit |
| `0xC63A4` | u16 | 1024 | **30/30 — virgin the entire sampled arc** | w[2] weight, never touched |
| `0xC63A6` | u16 | 1024 | **30/30 — virgin the entire sampled arc** | w[3] INERTIA weight, never touched |
| `0xC40D2` | u16 | 204 | 8 (V89→V97) | K1 friction gain; 102 stock/V38..V88, 204 from V89 |
| `0xC407E` | u16 | 511 | 18 (V76→V97) | hard-fault interlock; 511 stock, **850 at V73/V74/V75 (faulted!)**, restored to 511 at V76, held since |
| `0xC40BC` | u16 | 600 | 10 (V87→V97) | Coulomb relay gate; 600 stock/most builds, **6000 at V85/V86/V86B (measured 2.3× worse)**, back to 600 at V87 |
| `0xCBE74` | u16 | 59096 | **30/30 — virgin the entire sampled arc** | ⚠ see §5 correction — this address is not the dosed cell |
| `0xC6446` | u16 | 5244 | 9 (V88→V97) | Lever B arm; reverted to stock (512) at rebases **twice** in this sample (V72, V87) before landing 5244 at V88 |
| `0xC6CD0` | u16 | 3564 | 16 (V80→V97) | the frozen 4× forward LKAS gain; 65535(stock-scale)→3564 at V57, briefly lost at V76's fresh-from-V38 rebase, restored V80 |
| `0x454FE` | u8 | 181 | 17 (V80→V97) | V42 ratchet-fix byte; lost/restored **three times** in this sample (186 at V53/V57/V62/V67, 181 at V71C-V75, 186 again at V76, 181 from V80 on) |
| `0x55DF2` | u8 | 144 | 2 (V96→V97) | CAN427 telemetry source-repoint byte — changes every time a build repoints the debug channel; zero control-path role |
| `0x55E10` | u8 | 166 | 2 (V96→V97) | CAN427 packer `sar` shift amount, paired with `0x55DF2`; same telemetry-only role |

Full raw grid (all 30 columns) is in the script output above this table's construction; available on
request if needed verbatim.

---

## Summary

| item | verdict |
|---|---|
| Hashes (.rwd, image) | **MATCH**, both re-hashed from disk |
| Rebuild reproduces bit-for-bit | **YES** — 131/131 assertions in full-run mode; CRC chain 50/50 |
| `0xC63AC` = 102/102/150 in stock/V96/V97 | **CONFIRMED**, doubly anchored |
| V96→V97 diff | exactly 5 bytes: the 1-byte cal + its 4-byte CRC trailer, zero unattributed |
| STOCK→V97 cumulative diff | 270 bytes / 113 runs, **all attributed**, none orphaned |
| Exactly one `.rwd`/image per build number | **YES** for V96 and V97; **V95 fully absent from disk** |
| Cross-build cell matrix | built from images; two corrections found (see below) |

**Two findings worth carrying forward, both from-disk, neither fixed (reporting per instruction):**
1. `0xCBE74` itself never moves in any sampled image — it's a pointer/index, not the dosed cell. The
   real ×1.5-dose bytes are at `0xD7A5C`/`0xD7A6C` (+ trailer `0xD7FFC`), and V96's "REVERT.CBE74"
   put them back to V91/V92's ×1.5 value, **not stock**.
2. The task brief's "131/131" is the assertion count from the full write-mode run (with the
   shipped-`.rwd` re-verification block), not a CRC block count — the CRC chain is 50 blocks, matching
   every other build.

**Bottom line on the operator's suspicion ("dead lever, wrong address"): REFUTED on the byte side.**
`0xC63AC` is exactly where the build script says it is, reads exactly 102→150, and nothing else in
the image moved except its own CRC trailer. If V97 is inert on the car, the byte evidence does not
support "wrong address" or "logic that never executes at the flash level" as the explanation — that
would need to be chased in the code path (reader site, gating, closed-loop effect), which is outside
this task's pure-Python byte scope.
