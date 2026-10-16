# BUILD V300 **rev 2** — THE RELEASE (stock + the angle loop), built 2026-10-15, NOT FLOWN

> **Rev 2 reason:** the GATE 2 re-score on the stock-plant terms (`studies/release/GATE2-RESCORE-STOCK-PLANT-TERMS.md`) FAILS the revert of the DampAxis lane gp-0x6b26 (GM 20 → 5.2 dB, |T| +5.4 dB at 3 m/s), so its **13 bytes stay at V299's values**: Y rows `0xD7A5C` (6 B) + `0xD7A6C` (6 B) = (−29490, −17202, −16000) ×2 and α2 `0xC40DC` = 14. Rev 1 (749 B, image `a6a24117…`, rwd `ed891cf3…`) is DELETED; exactly one V300 rwd on disk.

Study/build artifact. Nothing flashed, nothing sent. Builder: `release-builder` (fork) for orchestrator `main`.
Spec: `docs/review/RELEASE-CENSUS-V299-vs-STOCK-2026-10-15.md`. Script: `analysis-2020accord/builds/v108_plus/build_v300_tva.py`
(2.1 s; `ACCORD_V300_WRITE=rwd` to emit). **E** = evidence (method given) · **B** = belief.

## 0. Artifacts (sha256 re-read from disk after the write — E)

| file | sha256 |
|---|---|
| image `../accord-firmwares/analysis-2020accord/_v300_V300-REV2-RELEASE-ANGLELOOP.FROMSTOCK-KP112.KD48.KI40.ICL8192-FRZ1229.CAP4096.6144-NOTELEMETRY.NOMAP.STOCKASSIST.DAMPAXIS.V299.A16C_plain_image.bin` | `7d58c823544e9e6ec369e7cc0fc0d7aa42fc8b075ad9b0005f58973d400f384e` |
| rwd `../accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V300-REV2-RELEASE-ANGLELOOP.FROMSTOCK-KP112.KD48.KI40.ICL8192-FRZ1229.CAP4096.6144-NOTELEMETRY.NOMAP.STOCKASSIST.DAMPAXIS.V299.A16C-0x13000-0x100000.rwd` | `42f562c069d39c877b66067fe56c6437c43b1609c48ffec8a83dc7303b8e7603` |
| cave `0xC4C00..0xC4D03` (260 B) | `e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608` (== V299's) |
| stock source `stock_fw_dump/code.bin` | `3f1d55a9…` · V299 byte source `30ff05fa…` |

rwd header `/` lists `39990-TVA-A110, 39990-TVA,A160, 39990-TVA,A16A, 39990-TVA,A16B, 39990-TVA,A16C` (flashes over stock, V298, V299 or itself).
F181 on the image: **`39990-TVA,A16C`**. Exactly one V300 rwd on disk (write guard refuses a second name).

## 1. What V300 is

**Built FROM STOCK.** The kept runs are copied byte-for-byte from the V299 image (never from constants), then Kp 112 / Kd 48 are
written on all 28 records, the tuning immediates re-written from the `TUNING` block (defaults asserted == the V299 image), the
id letter set to `C`, and the owning CRC blocks recomputed.

| vs | bytes | blocks |
|---|---|---|
| release vs **stock** | **766** (= rev 1's 749 + 13 DampAxis + the 0xD7 trailer; 32 trailer bytes in all) | 8 CRC blocks: main `[0x13000,0xC4FFC)`, `0xC6`, **`0xD7`**, `0xE4`, `0xE5`, `0xE6`, `0xE7`, `0xE8` |
| release vs **V299** | 2110 | — |
| V299 vs stock (for scale) | 2471 in 19 pages | — |

Kept (A structure 322 B · B tuning · D4 · D6 · **D8k + D5k: the 13 DampAxis bytes, rev 2**) / new (B3x/B4x: Kp 112, Kd 48 on the 27 non-selected records; letter C) /
removed to stock (C1–C3 telemetry · D1 · D2 · D3 · D5 (knee 0xC40BC, K1 0xC40D2) · D7 · D8 damper banks 0xCE–0xD9 minus D8k · D9 ×6 map · D10 LIM · D11) — the
census's rows, verbatim. The `TUNING` block at the top of the script is the ONE place task 1b edits (KP, KD, KI, ICL, FREEZE,
VCAP, VNOCAP, CAPLO, CAPHI, B_LO, B_HI, G_TABLE); flip `V299_IDENTICAL = False` after a change and assertion (3′) then checks
that the cave diff vs V299 lies in the tuning immediates only.

## 2. Assertion census (48/48 — E, stdout of the build)

38 substantive · 3 constant-checks · 1 vacuous/entailed (stock CRC walk) · 6 tautological (readbacks of what was just written, kept
as labelled smoke checks). The decision-bearing ones:

| # | assertion | result |
|---|---|---|
| 1 | release XOR stock == KEEP (incl. D8k/D5k) + B3x/B4x + letter + trailers, 0 stray / 0 missing | 766 B, PASS |
| 2 | release XOR V299 == REMOVED + B3x/B4x + letter + trailers, 0 stray / 0 missing; each removed row == stock | 2110 B, PASS |
| 3 | cave sha-identical to V299's | PASS |
| 4 | every byte outside the touched runs == stock | PASS |
| 5 | CRC chain 50/50 + bootloader replay 49/49 on the built image | PASS |
| 6 | rwd decodes back to the image byte-for-byte; cipher table validated non-circularly on the V38 plain image | PASS |
| 7 | pages 0xCE..0xD9 byte-identical to stock incl. trailers EXCEPT the 12 kept DampAxis bytes + the 0xD7 trailer; 0xD7 is the only owning block there; the 13 bytes == V299 and all 13 differ from stock | PASS |
| 8 | Kp == 112 on all 5 knots × 28 records, Kd == 48 on all 4 knots × 28, N read from each record header; X knots == stock; 28 distinct records per table | PASS |
| — | TUNING block == V299 image values (the drift guard) | PASS |
| — | telemetry hook stock, telemetry cave region 0xFF, angle hook present, G-table pointer 0xC4CDA | PASS |

## 3. Golden model (E)

`_self_check_v300` added to `analysis-2020accord/model/eps_chain_control.py` (exported through `eps_chain_delivery.py` and the
facade; called from `_self_check()`; prints nothing). It asserts against the BUILT V300 image, the stock dump and the V299 image:
cave == V299's; a/b/C/DB, Ki, ICL, DCL, authority chain == V299's; Kp/Kd on all 28 records via the pointer tables with stock X
knots; telemetry/map/LIM/r24/biquad/Coulomb knee+K1/damper pages (minus the 13 kept DampAxis bytes, asserted == V299)/D1/D11 == stock; id string A16C; the six in-place edits + the fade record
== V299's; D4/D6 kept. Contract after the edit: **96 non-dunder symbols** (95 + `_self_check_v300`), `_self_check()+_demo()`
stdout sha256 **`740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`** (2512 B) — **unchanged**.

## 4. H1 cave mirror on the V300 image (E)

`python analysis-2020accord/studies/release/h1_v300_built.py` (re-run on the rev-2 image `7d58c823…`, ~10 s; derived from `v299_build/h1_v299_built.py`, only the image
path/sha/output names differ): built cave == `rev2_cave.hex`; golden `bound()` == spec `cave_rev2` 0/6000; random valid/frz 0/5881,
op-skip 0/5381, camera 0/738, targeted 0/4000; negative controls N1 (V298 bytes) 2056 and N2 (alt4) 118 mismatches — both fire.
Outputs `h1_v300_built.out.txt` / `.json` beside the script.

## 5. Not done here (for the orchestrator)

- No adversarial pass yet; the census's §3 pre-registered items (D9 side channels, D6 readers, D3+D8 GATE 2 re-score, D7 readers,
  C stock-byte identity / `gp-0x1518`) are the lenses' brief.
- Lineage/STATE/handoff entries not written (per brief).
- D3 (r24 gate/arm), D5's knee/K1, the rest of D8, D9, D10 and all telemetry remain stock per the GATE 2 report; only the DampAxis lane is kept.
- B: the on-car consequence of D8/D5/D7/D2 reverting is a change in hands-on base-assist feel; the loop's authority (rail 2461)
  is unchanged — from the census, not re-measured.

## 6. Every run of release vs stock (207 runs; read from the BUILT image — E)

Columns: start address · length · census row · stock bytes · V300 bytes (hex, LE as stored; runs > 16 B truncated).

| addr | n | row | stock | V300 |
|---|---|---|---|---|
| `0x13109` | 1 | A1 | `2d` | `2c` |
| `0x1310D` | 1 | A1 | `30` | `43` |
| `0x28F4E` | 2 | A2 | `aa95` | `0096` |
| `0x29A50` | 4 | A2 | `e2470000` | `e0df3443` |
| `0x29A56` | 1 | A2 | `da` | `b2` |
| `0x29D6A` | 4 | A2 | `0880ed80` | `24875296` |
| `0x29D76` | 4 | A2 | `c582ba81` | `89378aae` |
| `0x29EE0` | 1 | A2 | `10` | `1a` |
| `0x29EE2` | 2 | A2 | `bb41` | `0000` |
| `0x2A1F0` | 2 | A6 | `6c74` | `d07c` |
| `0xC40DC` | 1 | D5k | `16` | `0e` |
| `0xC4C00` | 254 | A3 | `ffffffffffffffffffffffffffffffff…` | `c282ba8124d742951a46c832206e9065…` |
| `0xC4D00` | 4 | A3 | `ffffffff` | `8c080000` |
| `0xC4FFC` | 4 | trailer | `7549f248` | `fd56165e` |
| `0xC61B3` | 1 | A6 | `02` | `0c` |
| `0xC61B5` | 1 | A6 | `02` | `0c` |
| `0xC61BB` | 1 | B2 | `28` | `20` |
| `0xC61C0` | 6 | D6 | `400680030005` | `ffffffffffff` |
| `0xC62E4` | 1 | A4 | `04` | `00` |
| `0xC62E6` | 2 | A4 | `001e` | `ffff` |
| `0xC62EA` | 2 | D4 | `4001` | `0000` |
| `0xC63E6` | 1 | B1 | `00` | `28` |
| `0xC63E8` | 4 | A4 | `9b031806` | `00000020` |
| `0xC64B4` | 5 | D6 | `7060364070` | `ffffffffff` |
| `0xC659A` | 2 | A7 | `803f` | `a040` |
| `0xC659E` | 2 | A7 | `803f` | `a040` |
| `0xC65AE` | 2 | A7 | `80bf` | `a0c0` |
| `0xC65B2` | 2 | A7 | `80bf` | `a0c0` |
| `0xC65C6` | 2 | A7 | `0000` | `a040` |
| `0xC65CA` | 2 | A7 | `c03f` | `a040` |
| `0xC65CE` | 1 | A7 | `00` | `a0` |
| `0xC674F` | 1 | A7 | `04` | `14` |
| `0xC6751` | 1 | A7 | `04` | `14` |
| `0xC675B` | 1 | A7 | `fc` | `ec` |
| `0xC675D` | 1 | A7 | `fc` | `ec` |
| `0xC6769` | 1 | A7 | `00` | `14` |
| `0xC676B` | 1 | A7 | `06` | `14` |
| `0xC676D` | 1 | A7 | `08` | `14` |
| `0xC6CD0` | 2 | A6 | `ffff` | `e214` |
| `0xC6FFC` | 4 | trailer | `0c9e3cef` | `9889f71b` |
| `0xD7A5C` | 6 | D8k | `9ad99ae952f8` | `ce8ccebc80c1` |
| `0xD7A6C` | 6 | D8k | `9ad99ae952f8` | `ce8ccebc80c1` |
| `0xD7FFC` | 4 | trailer | `7042af1c` | `f4e7acbb` |
| `0xE4112` | 1 | B4x | `80` | `30` |
| `0xE4114` | 1 | B4x | `80` | `30` |
| `0xE4116` | 1 | B4x | `80` | `30` |
| `0xE4118` | 1 | B4x | `80` | `30` |
| `0xE4126` | 1 | B4x | `80` | `30` |
| `0xE4128` | 1 | B4x | `80` | `30` |
| `0xE412A` | 1 | B4x | `80` | `30` |
| `0xE412C` | 1 | B4x | `80` | `30` |
| `0xE413A` | 1 | B4x | `40` | `30` |
| `0xE413C` | 1 | B4x | `40` | `30` |
| `0xE413E` | 1 | B4x | `40` | `30` |
| `0xE4140` | 1 | B4x | `40` | `30` |
| `0xE414E` | 1 | B4x | `80` | `30` |
| `0xE4150` | 1 | B4x | `80` | `30` |
| `0xE4152` | 1 | B4x | `80` | `30` |
| `0xE4154` | 1 | B4x | `80` | `30` |
| `0xE4162` | 1 | B4x | `80` | `30` |
| `0xE4164` | 1 | B4x | `80` | `30` |
| `0xE4166` | 1 | B4x | `80` | `30` |
| `0xE4168` | 1 | B4x | `80` | `30` |
| `0xE4176` | 1 | B4x | `40` | `30` |
| `0xE4178` | 1 | B4x | `40` | `30` |
| `0xE417A` | 1 | B4x | `40` | `30` |
| `0xE417C` | 1 | B4x | `40` | `30` |
| `0xE436C` | 1 | B3x | `cd` | `70` |
| `0xE436E` | 8 | B3x | `cd016602b802b802` | `7000700070007000` |
| `0xE4384` | 10 | B3x | `0a011402b802b802b802` | `70007000700070007000` |
| `0xE439C` | 1 | B3x | `cd` | `70` |
| `0xE439E` | 8 | B3x | `9a01cd02cd02cd02` | `7000700070007000` |
| `0xE43B4` | 1 | B3x | `f8` | `70` |
| `0xE43B6` | 8 | B3x | `00028502b802b802` | `7000700070007000` |
| `0xE43CC` | 1 | B3x | `cd` | `70` |
| `0xE43CE` | 8 | B3x | `cd016602b802b802` | `7000700070007000` |
| `0xE43E4` | 1 | B3x | `cd` | `70` |
| `0xE43E6` | 8 | B3x | `9a01cd02cd02cd02` | `7000700070007000` |
| `0xE4FFC` | 4 | trailer | `b3e8dac1` | `20b4c671` |
| `0xE5112` | 1 | B4x | `80` | `30` |
| `0xE5114` | 1 | B4x | `80` | `30` |
| `0xE5116` | 1 | B4x | `80` | `30` |
| `0xE5118` | 1 | B4x | `80` | `30` |
| `0xE5126` | 1 | B4 | `80` | `30` |
| `0xE5128` | 1 | B4 | `80` | `30` |
| `0xE512A` | 1 | B4 | `80` | `30` |
| `0xE512C` | 1 | B4 | `80` | `30` |
| `0xE513A` | 1 | B4x | `80` | `30` |
| `0xE513C` | 1 | B4x | `80` | `30` |
| `0xE513E` | 1 | B4x | `80` | `30` |
| `0xE5140` | 1 | B4x | `80` | `30` |
| `0xE514E` | 1 | B4x | `80` | `30` |
| `0xE5150` | 1 | B4x | `80` | `30` |
| `0xE5152` | 1 | B4x | `80` | `30` |
| `0xE5154` | 1 | B4x | `80` | `30` |
| `0xE5162` | 1 | B4x | `40` | `30` |
| `0xE5164` | 1 | B4x | `40` | `30` |
| `0xE5166` | 1 | B4x | `40` | `30` |
| `0xE5168` | 1 | B4x | `40` | `30` |
| `0xE5176` | 1 | B4x | `40` | `30` |
| `0xE5178` | 1 | B4x | `40` | `30` |
| `0xE517A` | 1 | B4x | `40` | `30` |
| `0xE517C` | 1 | B4x | `40` | `30` |
| `0xE536C` | 10 | B3x | `0a011402b802b802b802` | `70007000700070007000` |
| `0xE5384` | 1 | B3 | `f8` | `70` |
| `0xE5386` | 8 | B3 | `00028502b802b802` | `7000700070007000` |
| `0xE539C` | 1 | B3x | `f8` | `70` |
| `0xE539E` | 8 | B3x | `0502cd02cd02cd02` | `7000700070007000` |
| `0xE53B4` | 1 | B3x | `f8` | `70` |
| `0xE53B6` | 8 | B3x | `0502cd02cd02cd02` | `7000700070007000` |
| `0xE53CC` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE53E4` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE54FE` | 1 | A5 | `18` | `10` |
| `0xE5500` | 1 | A5 | `2d` | `1a` |
| `0xE5502` | 1 | A5 | `40` | `26` |
| `0xE5504` | 1 | A5 | `50` | `30` |
| `0xE5506` | 1 | A5 | `60` | `40` |
| `0xE5508` | 1 | A5 | `70` | `60` |
| `0xE550C` | 1 | A5 | `cd` | `f3` |
| `0xE550E` | 1 | A5 | `a4` | `da` |
| `0xE5510` | 1 | A5 | `7d` | `b3` |
| `0xE5512` | 1 | A5 | `5a` | `4d` |
| `0xE5514` | 1 | A5 | `33` | `4d` |
| `0xE5FFC` | 4 | trailer | `1406ba24` | `3028deb0` |
| `0xE6112` | 1 | B4x | `40` | `30` |
| `0xE6114` | 1 | B4x | `40` | `30` |
| `0xE6116` | 1 | B4x | `40` | `30` |
| `0xE6118` | 1 | B4x | `40` | `30` |
| `0xE6126` | 1 | B4x | `40` | `30` |
| `0xE6128` | 1 | B4x | `40` | `30` |
| `0xE612A` | 1 | B4x | `40` | `30` |
| `0xE612C` | 1 | B4x | `40` | `30` |
| `0xE613A` | 1 | B4x | `40` | `30` |
| `0xE613C` | 1 | B4x | `40` | `30` |
| `0xE613E` | 1 | B4x | `40` | `30` |
| `0xE6140` | 1 | B4x | `40` | `30` |
| `0xE614E` | 1 | B4x | `40` | `30` |
| `0xE6150` | 1 | B4x | `40` | `30` |
| `0xE6152` | 1 | B4x | `40` | `30` |
| `0xE6154` | 1 | B4x | `40` | `30` |
| `0xE6162` | 1 | B4x | `40` | `30` |
| `0xE6164` | 1 | B4x | `40` | `30` |
| `0xE6166` | 1 | B4x | `40` | `30` |
| `0xE6168` | 1 | B4x | `40` | `30` |
| `0xE6176` | 1 | B4x | `40` | `30` |
| `0xE6178` | 1 | B4x | `40` | `30` |
| `0xE617A` | 1 | B4x | `40` | `30` |
| `0xE617C` | 1 | B4x | `40` | `30` |
| `0xE636C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE6384` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE639C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE63B4` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE63CC` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE63E4` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE6FFC` | 4 | trailer | `38b3b8d5` | `ff2735a2` |
| `0xE7112` | 1 | B4x | `40` | `30` |
| `0xE7114` | 1 | B4x | `40` | `30` |
| `0xE7116` | 1 | B4x | `40` | `30` |
| `0xE7118` | 1 | B4x | `40` | `30` |
| `0xE7126` | 1 | B4x | `40` | `30` |
| `0xE7128` | 1 | B4x | `40` | `30` |
| `0xE712A` | 1 | B4x | `40` | `30` |
| `0xE712C` | 1 | B4x | `40` | `30` |
| `0xE713A` | 1 | B4x | `40` | `30` |
| `0xE713C` | 1 | B4x | `40` | `30` |
| `0xE713E` | 1 | B4x | `40` | `30` |
| `0xE7140` | 1 | B4x | `40` | `30` |
| `0xE714E` | 1 | B4x | `40` | `30` |
| `0xE7150` | 1 | B4x | `40` | `30` |
| `0xE7152` | 1 | B4x | `40` | `30` |
| `0xE7154` | 1 | B4x | `40` | `30` |
| `0xE7162` | 1 | B4x | `40` | `30` |
| `0xE7164` | 1 | B4x | `40` | `30` |
| `0xE7166` | 1 | B4x | `40` | `30` |
| `0xE7168` | 1 | B4x | `40` | `30` |
| `0xE7176` | 1 | B4x | `40` | `30` |
| `0xE7178` | 1 | B4x | `40` | `30` |
| `0xE717A` | 1 | B4x | `40` | `30` |
| `0xE717C` | 1 | B4x | `40` | `30` |
| `0xE736C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE7384` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE739C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE73B4` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE73CC` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE73E4` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE7FFC` | 4 | trailer | `f80758a6` | `3f93d5d1` |
| `0xE80BA` | 1 | B4x | `40` | `30` |
| `0xE80BC` | 1 | B4x | `40` | `30` |
| `0xE80BE` | 1 | B4x | `40` | `30` |
| `0xE80C0` | 1 | B4x | `40` | `30` |
| `0xE80CE` | 1 | B4x | `40` | `30` |
| `0xE80D0` | 1 | B4x | `40` | `30` |
| `0xE80D2` | 1 | B4x | `40` | `30` |
| `0xE80D4` | 1 | B4x | `40` | `30` |
| `0xE80E2` | 1 | B4x | `40` | `30` |
| `0xE80E4` | 1 | B4x | `40` | `30` |
| `0xE80E6` | 1 | B4x | `40` | `30` |
| `0xE80E8` | 1 | B4x | `40` | `30` |
| `0xE80F6` | 1 | B4x | `40` | `30` |
| `0xE80F8` | 1 | B4x | `40` | `30` |
| `0xE80FA` | 1 | B4x | `40` | `30` |
| `0xE80FC` | 1 | B4x | `40` | `30` |
| `0xE824C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE8264` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE827C` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE8294` | 10 | B3x | `330133029a029a029a02` | `70007000700070007000` |
| `0xE8FFC` | 4 | trailer | `9aa1e24a` | `4a0f6ce8` |
