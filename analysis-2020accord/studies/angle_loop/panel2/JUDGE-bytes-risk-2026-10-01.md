# JUDGE: BYTES & RISK, angle-loop design panel ROUND 2, 2026-10-01

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent. The fork was not touched, and nothing was committed.
- Ghidra was used read-only: `disassemble_bytes dry_run:true` and `get_function_by_address` on stock `code.bin`. Nothing was saved.
- Python (`bin_decompile`) read the V295 image (sha `5c044d65…`) and every cave `.hex` on disk.
- No shared scorer or cache was re-run or rewritten.
- The one artefact I made is a merged cave `.hex` in `_scratch/angle_loop/judge2-bytes-risk/` (§5, G1). It is not a build.

**Author:** the bytes-risk judge, a subagent for the orchestrator `main`.

**Lens: PRIORITY 2.** I rank on:
- bytes;
- cave count and size;
- RAM words;
- encodings that stay BELIEF until a built image is decoded;
- hook-site liveness;
- CRC blocks dirtied;
- golden-mirror and interpreter coverage;
- fault paths.

Priority 1 (the goal) is senior, so goal and gate standing carry 20 % of each score. A small build that fails the goal must not
outrank a slightly larger one that meets it.

**The common scorers outrank the designers' pages.** Where they disagree, the scorer is right unless I re-ran and showed otherwise.

Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**. Code is cited by address or grep string.

---

## 0. Verdict

Scores are out of 100: Size 25, Verifiability 30, Liveness / fault-path risk 25, Gate / goal standing 20.

Goal / gate standing is split into two parts:
- **Time, 14 points:** the common time scorer, every criterion it can decide at ≥ 8 m/s.
- **Freq, 6 points:** the common frequency scorer's R2 box.

Bytes are normalised to rev2-A's convention: in-place code 20 + cal 24 + the whole cave including its table. RAM words are listed
separately.

| # | id | score | bytes / cave / RAM | one-line reason |
|---|---|---|---|---|
| 1 | **E2-A2** | **81** | 248 / 1 × 204 / 0 | **The only family that passes every time criterion ≥ 8 m/s on both frames** (replayed-word tracking 0.985/0.991, turn-hold 0.98, light/firm lurch 5.8/4.7°). The hex is on disk; H1 gave 0 mismatches on the designer's interpreter and on the time scorer's. I verified the listing sits at cave offset 0x64. Writes no RAM. Its small-signal loop is P2's, so it inherits P2's R2-box defect (690 fails). |
| 2 | **E2-A3** | 79 | 266 / 1 × 222 / 0 | A2 plus a low-speed cap (+18 B). It restores P2's < 8 m/s lurch (10.6 vs 13.9° b_lo×J_hi). In exchange, low-speed turn-hold falls back to P2's 0.90–0.95. Same verification as A2. |
| 3 | E2-A3-12k | 77 | 266 / 1 × 222 / 0 | A3 at ICL 12288, +0 B. It is the best time row (trk 0.997/0.995), but the extra I authority (≈ 1 970 T, 80 % of the rail) is beyond anything r71b needs. |
| 4 | E2-S | 74 | 216 / 1 × 172 / 0 | Smallest policy (+16 B) that moves the lurch at all, but the light lurch is 11.1° at 8–10 m/s (fail), and hands reading ≤ 300 words are not bounded. |
| 5 | G-P48d | 74 | 200 / 1 × 156 / 0 | **Best D/table donor:** P2's verified code, so 0 code bytes over P2, with a re-sized Kd and a refit table. R2 box: 166 fails, all ms_free products, all declared with R3\*. Alone it fails F1 (trk 0.86, hold 0.74). |
| 6 | G-P44d | 74 | 200 / 1 × 156 / 0 | Same bytes as P48d. It keeps a 10 % margin on the 20 Hz criterion (M20 0.88× vs 0.96×), which my lens prefers because the plant model above 8 Hz is BELIEF. Slightly weaker time row (trk 0.856, in-phase 0.64). |
| 7 | G-P48 | 72 | 200 / 1 × 156 / 0 | 0 fails on the R2 box, but it fails F1 harder (trk 0.835, hold 0.69) and has a declared linear-metric miss (0.935). |
| 8 | G-P44 | 72 | 200 / 1 × 156 / 0 | As G-P48, at Kd 44. |
| 9 | E2-A2-X | 72 | 248 / 1 × 204 / 0 + 1 fork field | A2 plus the `gp-0x6803 == 2` arm. Droop is cut by a third, but the post-PID fade arm `0xCBAE4` leaves ×1.8–2.1 more lane torque against a firm hand. The fork must also send field 2 on every frame, including the request drop. |
| 10 | E1-freeze | 70 | 212 / 1 × 168 / 0 | Light lurch 11.8° at 8–10 m/s (fail). No hex on disk: the time scorer assembled it from E1's 12-byte listing. It writes `gp-0x6dd0`. |
| 11 | G-F24d | 68 | 185 / 1 × 138 / 0 | Held-D code (F2's bytes), and the sign does not depend on pol. But anti-damping is ×1.9 V295 at 13 Hz, it fails F1, and the linear metric is 0.947. |
| 12 | G-F24 | 67 | 185 / 1 × 138 / 0 | 0 R2 fails, but the time row is the weakest of the rate-D set (trk 0.821, hold 0.67) and the exact GM is 6.7 dB thin. |
| 13 | E1-cal ≡ E2-R1 | 66 | 200 / 1 × 156 / 0 | **The same build twice:** P2's hex byte for byte with ICL 8192. It fixes F1 at +0 code bytes, but the light lurch is **24.3°** and the firm lurch 8.4°, neither bounded. |
| 14 | E1-reset | 65 | 212 / 1 × 168 / 0 | The firm reset works (4.2°), but the light lurch is 24.3° (E1 declared about 17°, so it is under-quantified). It adds the cave's first RAM write. Listing only. |
| 15 | G-P48L | 64 | 200 / 1 × 156 / 0 | A deeper dip: in-phase gain collapses to 0.11, timeout-hold excursion 2.91°. Its designer does not offer it. |
| 16 | G-P48k40 | 63 | 200 / 1 × 156 / 0 | Lower Ki costs more tracking (0.903/0.838). Its designer rejects it. |
| 17 | D2a | 62 | 206 / 1 × 162 / 0 | Round-1 winner. Refuted by F1 (trk 0.857, hold 0.73) and the R2 box (702 fails). |
| 18 | P2 | 62 | 200 / 1 × 156 / 0 | rev2-A primary. The same refutation (690 fails). Its cave is the verified base every E/G row builds on. |
| 19 | B0r | 61 | 191 / 1 × 144 / 0 | Held-D, 706 fails, F1. |
| 20 | F2 | 60 | 185 / 1 × 138 / 0 | Held-D, 691 fails, F1. |
| 21 | G-A22 | 52 | 254 / 1 × 210 / **2** | Frame-exact and pol-free, but it costs 2 new RAM words and +54 B. It has the worst time row (trk 0.815, hold 0.66) and 2.3× the texture. The sentinel twin is not reached by any static call form I scanned (§1 V6), but computed dispatch is not excluded. |
| 22 | G-A22d | 51 | 254 / 1 × 210 / 2 | As G-A22. |
| 23 | E2-L | 46 | 212 / 1 × 168 / 0 | The leak fails replayed-word tracking (0.938) and lurch 24.3°. Its designer rejects it. |
| 24 | E2-K0 | 45 | 173 / 1 × 132 / 0 + fork code | Smallest cave and 0 R2 fails, but real-curve hold 0.65, trk 0.915, and it needs fork code beyond the angle interface. |
| 25 | E1-sched | 44 | ≈ 244 / 1 × ≈ 200 / 0 | Mirror only, no listing. Tracking 0.886/0.928 (fail). |
| 26 | H-B | 42 | ≈ 190–214 (BELIEF) / 1 × ≈ 164 / 0 | **No listing.** The hook sketch overwrites a live `sar 5` (§1 V7). Replayed tracking 0.933 and lurch 20.8° are both undeclared. It fails b_q×J1.0+h10 at 29.9° (undeclared). |
| 27 | H-A | 40 | ≈ 216–234 (BELIEF) / 1 × ≈ 190 / 0 | As H-B. Also: its GATE-2 evidence was scored on the held operand, not the `gp-0x69ca` its bytes load. The b_lo×ms_free ring is 0.84 Hz, outside its declared stops. The fork SR fold is load-bearing for wheel angle, and `gp-0x679c` validity is left to the fork. |
| 28 | E1-bleed | 40 | 234 / 1 × 190 / 0 | Replayed-word tracking 0.74–0.83, which fails the goal. Mirror only. Its designer rejects it. |
| — | **E1-splitP** | 0 (DQ) | 200 / 1 × 156 / 0 | **DISQUALIFIED:** the common scorer gives ρ = 1.0000 (ζ ≈ 0) on the credible member b_q×ms_free+h10 at 19 m/s, and 5 052 R2 fails including the nominal member, with no declared stop band. Its designer also rejects it. |

**Headline.** No single candidate passes both common scorers. But the two halves are **byte-orthogonal**, and I verified that:
- **E2's integral-policy block** fixes F1 and F4 with 0 RAM writes. EVIDENCE on the time scorer. It inserts 48 B of code ahead of P2's table.
- **G's D/table re-size** closes F2/F3 down to the declared ms_free products. EVIDENCE on the frequency scorer. It is P2's code byte for byte with different data.

The graft **E2-A2 code + G-P48d (or G-P44d) table + Kd 48 (44)** therefore costs **exactly E2-A2's 248 B, 1 cave of 204 B, 0 RAM**. I built that merged cave in scratch and checked the table pointer (§5 G1). It is the candidate my lens recommends, and it is **not yet scored**. The rows above score the designers' candidates as submitted.

---

## 1. What I verified myself this session

| # | claim | method | result |
|---|---|---|---|
| V1 | Every E2 cave (15 hex files, P2…A2S-C, K0) ends in **P2's 42-byte G table, byte for byte**. So every E2 row's small-signal loop is P2's, and P2's R2-box defect (690 fails) is inherited unchanged. | Python: the last 42 B of each `e2_cave_*.hex` == `c2/rev2A/c2_cave_P2.hex`[-42:] | **EVIDENCE** (confirms the frequency scorer's finding 1, which it asserted by hex parse) |
| V2 | **G-P48/P48d/P44/P44d code == P2's code** (first 114 B identical; 116 B common prefix). G-F24/F24d code == F2's (98 B common prefix). Only table data differs. | Python prefix compare of `g_cave_*.hex` vs rev2-A hex | **EVIDENCE** (G's "same instruction bytes as P2" holds) |
| V3 | **E2-A2's 48-byte policy listing sits at cave offset 0x64**, exactly where the doc's listing puts it (`0xc4c64`). Every instruction hand-decodes as listed (examples below). Each branch displacement lands on its named label: `bge A1` +4 → `0xc4c6e`, `bh AH` +6 → `0xc4c7e`, `br AB` +4 → `0xc4c80`, `bge A2` +4 → `0xc4c90`. | Python `find` of the listing bytes in `e2_cave_A2.hex`, plus hand V850 decode | **EVIDENCE** |
| V4 | The graft is a pure data swap. E2-A2 loads its table with `mov imm32,r9 = 0xC4CA2` at cave +0x1a, and the table sits at +0xa2 (A3: `0xC4CB4` / +0xb4). So E2-A2[:-42] + G-P48d[-42:] keeps the pointer valid with no re-link. Merged A2+G-P48d: **204 B**, sha `14819b5c1452363a`. Merged A3+G-P48d: **222 B**, sha `3aa6d14fe580d6fd`. | Python: find the `0x0620\|reg` imm32 in each cave and its value; build and compare | **EVIDENCE** (the bytes). **BELIEF** that it behaves as both halves predict: no scorer has run it (§7). |
| V5 | **V295 and stock ship ICL `0xC61BA` = 10240**, and V295's DCL `0xC61B6` = 0. So C1/P2's ICL 4096 was a deliberate lowering. "Raise to 8192" is still **below Honda's own clamp**: authority stays inside a stock limit. | LE read of the V295 image and stock `code.bin` | **EVIDENCE** (confirms designer H) |
| V6 | **No 6-byte `jarl/jr disp32` anywhere in `0x13000–0xB0000` targets `FUN_0002a93a` (body `0x2A93A–0x2B06F`) or `FUN_0002a508`, and neither entry appears as an LE32 literal at any alignment.** The scan matched halfwords `0x02E0\|reg1` with an even target and found 5 raw hits, none in either function. Ghidra decodes the instruction boundary 2 B past two of them (`0x1f470 addi`, `0x38ca0 ld.h`), so those hits are mid-instruction bytes. | Python raw scan at every even address. Ghidra dry-run decode. A synthetic planted instance is found by the decoder. | **EVIDENCE** for this form, plus E2's controlled Format-V, LE32 and movhi/movea scans. **Caveat:** no *genuine* in-image disp32 call exists to positive-control the form, so the planted instance proves only the scanner. Computed dispatch (`jmp [reg]` from a table) is **not excluded (BELIEF)**. This partly closes G's H-sentinel item and E1's GATE-1 claim on `gp-0x6dd0`. |
| V7 | **H's hook at `0x29D7A` overwrites two live instructions.** `0x29D7A 10 30` = `mov r16,r6` and `0x29D7C a5 32` = `sar 5,r6` (hw `0x32A5`: reg2 r6, op `010101` sar-imm, imm 5). `0x29D7E ea 31` = `cmp r10,r6`. A 4-byte `jarl` at `0x29D7A` covers both. H's sketched exit `NOBLEED: mov r16,r6 ; jr 0x29D7E` **omits the `sar 5`**, so as sketched e5 = E′ instead of E′ >> 5: a **×32 I increment**. H's time mirror (`LaneC1F` subclass) runs C1's correct arithmetic, so it does not model H's own sketch. | V295 bytes + hand ISA decode, against E2's dry-run reading of the same region | **EVIDENCE** for the bytes and the sketch as written. It is a sketch defect that H1 would catch, but no H bytes exist to run H1 on. |
| V8 | The cave sizes match the designers' tables to the byte for every hex on disk: E2 P2 156, S300 172, L13 168, A 188, A2 204, A2S 220, A3 222, A2S-C 240, K0 132. G: P4x 156, F24 138, A22 210. The free span `0xC4BD8–0xC4FEF` is all `0xFF` in V295. | Python | **EVIDENCE** |

Not re-verified, taken from the common scorers' own validation (their VALIDATE / V1–V5 / H1 lines, which I read):
- the time scorer's H1: 26 hex-backed columns, 0 mismatches each, 6 negative controls fail;
- E1-reset, E1-freeze and E1-splitP were assembled by the time scorer from E1's listing;
- H-A, H-B, E1-bleed and E1-sched are mirror-only (BELIEF).

---

## 2. What decides the table

1. **Two candidates pass every time criterion the common scorer can decide, on all members, both frames, at ≥ 8 m/s:**
   - E2-A2 (with its variants A3, A3-12k and A2-X);
   - nothing else.

   Every G row fails F1, because it keeps ICL 4096. Every E1 row, E2-R1, E2-L and both H rows fail the light-hand lurch or the
   replayed-word tracking. **EVIDENCE:** the time scorer's table.
2. **Every E1/E2 row is P2's small-signal loop** (V1). On the R2 box P2 fails 690 points:
   - 197 on the brief's own members under the frame box: J_hi 42.3°, b_lo×J_hi+h10 26.1°, b_q×J1.0+h10 27.1°;
   - b_q×ms_free+h10 at **8.2° (ζ 0.028)**.

   All are stable (ρ ≤ 0.9977). E1 and E2 both declare F2/F3 "inherited, another axis". The only stop band that covers the
   1.27 Hz ring is rev2-A's inherited R3\*. **That is why E2-A2's freq part is 2 of 6.**
3. **G's tables fix the loop** (R2 box 0–169 fails, the remainder all declared ms_free products) and change **no code byte** (V2).
4. **E2's policy block is independent of the table.** It reads only `gp-0x6a00`, `gp-0x6a5e` and `gp-0x6dd0`, uses P2's scratch set,
   and its H1 checks that every non-scratch register (r14, r25) is unchanged. The frozen-I loop it falls into is more stable than
   the running loop: the frequency scorer finds the I-frozen R2 box passes for every skeleton, with PM ≥ 89.6° at the fade floors.
   **So the graft costs 0 bytes over E2-A2, inherits G's R2 box, and should inherit E2's time standing.** The last part is BELIEF
   until re-run, because G-P48d's table is higher than P2's at 17.5 m/s (1519 vs 1438) and lower at the dip (474 vs 537).

---

## 3. Disqualifications

| id | cause | re-admissible? |
|---|---|---|
| **E1-splitP** | The common frequency scorer: ρ = 1.0000, ζ ≈ 0 on b_q×ms_free+h10 at 19 m/s (FA κ 0.83), and 5 052 R2-box fails including **nominal** (PM nom 45.9, tier A 22.3). No declared stop band. Turn-hold 0.75 on the time scorer. | No. Its designer rejected it for the same reason: P cannot carry the curve. |

**Flagged, not disqualified.** The rule disqualifies instability only, and these are stable.

- **H-A and H-B.** Each hits several items on my pre-written FAIL list (§7):
  - no assembled cave, presented as a design;
  - a hook sketch that overwrites a live instruction without replacing it (V7);
  - GATE-2 evidence computed on a different loop than H-A's bytes build (the frequency scorer's disagreement (a));
  - a release-lurch claim (< 4°) that fails at the specified ICL 7500 (22.2° / 20.8°, time scorer);
  - undeclared replayed-word tracking misses (0.925 / 0.933).

  They are ranked last among scorable rows. **If built from H's sketch as written, they are do-not-flash.**
- **E2-K0 and E1-sched.** Fork code, or no listing, and both fail tracking. Ranked low, not disqualified.

---

## 4. Byte account and subscores

**CRC blocks.** Every cave candidate dirties the same four: main, cave block `0xC4FFC`, cal page(s), and the `E5xxx` record page.
E1-cal and E2-R1 change one cal value in a page P2 already dirties. **No candidate is separated on CRC.**

**Hook.** Every E/G/round-1 row reuses P2's hook `0x29D76` (`c2 82 ba 81 → 89 37 8a ae`, `jarl 0xC4C00,r6`), which was verified
in round 1 and by rev2-A. H uses `0x29D7A` (V7).

| id | in-place | cave | cal | **total** | RAM written | hex on disk | interpreter H1 on the bytes | new RAM write / new read | fault-path notes |
|---|---|---|---|---|---|---|---|---|---|
| E2-A2 | 20 | 204 | 24 | **248** | 0 | yes | designer 0/40 000 + scorer 0/3 000; CONTROL C 0/8 000 | reads `gp-0x6a00`, `gp-0x6dd0`, a second `gp-0x6a5e` | pol = −1 (fresh D, inherited); M-E2-4 caps I at ≈ 200 T + slope·\|θ\| (a crosswind on a straight → P carries the excess; declared) |
| E2-A3 | 20 | 222 | 24 | 266 | 0 | yes | 0 mismatches | as A2 | as A2 |
| E2-A3-12k | 20 | 222 | 24 | 266 | 0 | = A3 | 0 | as A2 | I authority up to ≈ 1 970 T where the bound is not binding |
| E2-A2-X | 20 | 204 | 24 | 248 + fork | 0 | = A2 | 0 | as A2 | fade arm `0xCBAE4` ×1.8–2.1 against a firm hand; the fork must send 2 on every frame |
| E2-S | 20 | 172 | 24 | 216 | 0 | yes | 0 | adds a `gp-0x4f60` read | 3.9 % resting-hand freeze duty |
| G-P48d / P44d / P48 / P44 / P48L / P48k40 | 20 | 156 | 24 | **200** (G's own convention: 213 written / 198 diff = P2's) | 0 | yes | 0/60 000 | none new (P2's) | pol = −1; M20 0.96× (P48) / 0.88× (P44) |
| G-F24 / F24d | ≈ 23 | 138 | 24 | 185 | 0 | yes | 0/60 000 | none new (F2's) | no pol dependence; exact GM 6.7 dB thin (F24) |
| G-A22 / A22d | 20 | 210 | 24 | 254 | **2** (`gp-0x6c44/-0x6c40`, V289-flown) | yes | 0/60 000 incl. RAM | first-tick sentinel `gp-0x6cf8` shared with the twin (V6: no static caller) | no pol; 10 deg/s D quantum |
| E1-cal ≡ E2-R1 | 20 | 156 | 24 | 200 | 0 | = P2 | = P2 | none | light lurch 24.3° unbounded |
| E1-reset / E1-freeze | 20 | 168 | 24 | 212 | **writes `gp-0x6dd0`** | **no** (listing only) | scorer 0/3 000 on the scorer's own assembly | the lane's own I cell, written before its read at `0x29DA4` (V6 supports that the twin does not run) | light lurch 24.3 / 11.8° |
| E1-bleed | 20 | 190 | 24 | 234 | writes `gp-0x6dd0` | no | none (mirror only) | — | tracking fails |
| E1-sched | 20 | ≈ 200 | 24 | ≈ 244 | writes | no | none | — | tracking fails |
| E2-L | 20 | 168 | 24 | 212 | 0 | yes | 0 | — | tracking fails |
| E2-K0 | 17 | 132 | 24 | 173 + fork code | 0 | yes | 0 | — | the fork integral winds under a light hand (36–43° at 8 m/s) |
| P2 / D2a / F2 / B0r | 20–23 | 156 / 162 / 138 / 144 | 24 | 200 / 206 / 185 / 191 | 0 | yes | 0/60 000 | — | refuted (F1 + R2 box) |
| H-A | ≥ 22 | ≈ 190 | 24 | ≈ 216–234 | writes `gp-0x6dd0` (bleed) | **no** | **none** | new P/I operand `gp-0x69ca`; its validity (`gp-0x679c == 3`) is left to the fork | hook sketch drops `sar 5` (V7); the fork SR fold sets the wheel angle (1.155× near centre if absent); the fresh-D guard is a sketch (it falls back to the held cell) and is not D2a's verified form |
| H-B | ≥ 26 | ≈ 164 | 24 | ≈ 190–214 | writes `gp-0x6dd0` | no | none | — | hook sketch as H-A |

**Subscores (S / V / R / G = total).** G = time (out of 14) + freq (out of 6).

| id | S/25 | V/30 | R/25 | G/20 | total | deciding lines |
|---|---|---|---|---|---|---|
| E2-A2 | 18 | 27 | 20 | 14 + 2 = 16 | **81** | Passes the time scorer everywhere ≥ 8 m/s. Writes no RAM. Listing, hex and H1 agree (V3). The < 8 m/s lurch regression (13.9° vs 10.5°) is declared M-E2-1 with R9. Freq = P2. |
| E2-A3 | 16 | 27 | 20 | 16 | 79 | +18 B buys back P2's low-speed lurch; it costs low-speed hold (M-E2-1b, an operator complaint class). |
| E2-A3-12k | 16 | 26 | 19 | 16 | 77 | +0 B over A3, best tracking. The I authority is ×1.5 what r71b needs; prefer 8192 unless a 3.5 m/s² curve is in scope. |
| E2-S | 20 | 27 | 18 | 9 + 2 = 11 | 76 → **74** | Lurch fails at 8–10 m/s, and hands ≤ 300 words are not bounded. The κ-dependent threshold is a BELIEF sensor scale: −2 for an unmeasured scale on the decisive input. |
| G-P48d | 22 | 27 | 18 | 3 + 5 = 8 | 75 → **74** | P2's code. The c_D regression makes the fresh D's size **resolvable in one drive** (window 0.45–0.70 vs P2's 0.30–0.50), which removes the round-1 verifiability penalty. M20 0.96× of V295 sits on a BELIEF > 8 Hz model. Dip small-correction gain is worse than P2's (G-M7, declared). F1 not fixed: −1 for presenting only half the loop. |
| G-P44d | 22 | 27 | 19 | 3 + 5 = 8 | 76 → **74** | As P48d with a 10 % M20 margin. Tie with P48d; my lens leans to P44d's margin, the time scorer to P48d's lurch and in-phase gain. |
| G-P48 / G-P44 | 22 | 27 | 18 | 2 + 6 = 8 | 75 → **72** | 0 R2 fails, but a declared tracking miss (linear 0.935/0.930) on top of F1. −3 for the double tracking miss. |
| E2-A2-X | 17 | 25 | 14 | 16 | 72 | Authority **against the driver** rises ×1.8–2.1. Its benefit depends on fork behaviour this kit cannot verify. |
| E1-freeze | 21 | 22 | 18 | 9 + 2 = 11 | 72 → **70** | No hex. A new RAM write. The lurch fails at 8–10 m/s. |
| G-F24d | 23 | 27 | 17 | 2 + 4 = 6 | 73 → **68** | 13 Hz anti-damping ×1.9 V295 (creep-grind band). Linear 0.947 misses. |
| G-F24 | 23 | 27 | 16 | 1 + 5 = 6 | 72 → **67** | GM 6.7 dB thin. Weakest rate-D time row. |
| E1-cal ≡ E2-R1 | 22 | 28 | 11 | 5 + 2 = 7 | 68 → **66** | Fully verified bytes (P2's hex + one cal). But a **24.3° release overshoot** with nothing bounding it is the largest driver-facing risk of any F1-fixing row. |
| E1-reset | 21 | 22 | 15 | 6 + 2 = 8 | 66 → **65** | The firm reset is real (4.2°), but the light lurch is 24.3° and under-declared (~17°). Listing only. A new RAM write. |
| G-P48L | 22 | 27 | 14 | 1 + 6 = 7 | 70 → **64** | In-phase gain 0.11 at the dip; not offered. |
| G-P48k40 | 22 | 27 | 15 | 1 + 6 = 7 | 71 → **63** | Rejected by its designer. |
| D2a / P2 / B0r / F2 | 21 / 22 / 22 / 23 | 28 | 15 | 3 + 2 = 5 | **62 / 62 / 61 / 60** | Refuted by F1 and the R2 box. Kept as references. |
| G-A22 / A22d | 12 (incl. −6 for 2 RAM) | 22 | 12 | 1 + 5 = 6 | **52 / 51** | 2 new RAM words. Sentinel shared with the twin: static callers excluded (V6), computed dispatch not. Texture 2.3×. Worst time row. |
| E2-L | 21 | 26 | 12 | 1 + 2 = 3 → **46** after −16 for a rejected design (goal fail on the real torque word) | 46 | |
| E2-K0 | 24 − 4 (fork code) = 20 | 24 | 9 | 1 + 6 = 7 → **45** after −15 | 45 | Fork code beyond the interface. Its lurch is unbounded by firmware. |
| E1-sched | 18 | 12 | 12 | 2 + 2 = 4 → **44** after −2 | 44 | No listing. |
| H-B / H-A | 20 / 19 | 6 / 5 | 9 / 8 | 5 + 2 = 7 / 6 + 2 = 8 → **42 / 40** | 42 / 40 | Not scorable as bytes (V7). H-A's GATE 2 is on the wrong operand, its b_lo×ms_free ring is outside its declared stops, and it has fork-dependent angle and validity paths. |
| E1-bleed | 20 | 12 | 10 | 1 + 2 = 3 → **40** after −5 | 40 | Rejected by its designer. |

(Where a total carries an adjustment, the reason is in the row. All adjustments push a goal-failing row below every row that passes
the time scorer, as the priority rule requires.)

---

## 5. Grafts

**G1. THE GRAFT, recommended: E2-A2's policy code + G-P48d's (or G-P44d's) table and Kd record.**
- **Bytes:** 248 written, 1 cave of 204 B, 0 RAM. Identical in size to E2-A2.
- **Code:** E2-A2's bytes, already H1-tested.
- **Data:** G's gated table and the Kd record cells `0xE5126` ×4 = 48 (or 44). P2 already writes those cells, with 34.
- **Merged cave:** built as `_scratch/angle_loop/judge2-bytes-risk/graft_A2_GP48d.hex` (sha `14819b5c1452363a`), and A3+G-P48d as 222 B (sha
  `3aa6d14fe580d6fd`). V4 checks the table pointer.

**Expected, BELIEF until re-run:**
- R2 box = G-P48d's: 166 fails, all b_q×ms_free, declared with R3\*. The policy block cannot reduce small-signal margin, because
  frozen states are more stable.
- The time row ≈ E2-A2's at ≥ 8 m/s.

**Must re-run before it is a candidate:**
1. H1 on the merged bytes, on both interpreters.
2. `panel2/score_freq.py` R2 box.
3. `panel2/score_time.py`, all columns, both frames. G-P48d's dip G 474 vs P2's 537 may move the ARB's 26 T/deg low slope margin
   and the dip small-correction rows (G-M7).
4. `e2_data_hold.py` against the merged table: the bound must still clear every r71b steady hold.

The orchestrator's credibility ruling on b_q×ms_free picks between:
- the d table: a stability miss, declared under R3\*;
- the non-d G-P48 table: a linear tracking miss, 0.935.

**Both cost the same bytes.**

**G2. Keep ICL 8192, not 12288, unless the goal explicitly covers a 3.5 m/s² curve.** It costs +0 B either way.
- 8192 holds every r71b-sized curve (EVIDENCE: the time scorer and E2's T1), and it is below stock's 10240 (V5).
- 12288 adds I authority nothing measured needs.

**G3. Do NOT take the `gp-0x6803 == 2` arm (E2-A2-X) or the firmware camera gate (E2-A2S-C, +36 B).** Both raise hand-side
authority ×1.8–2.1. For F5 take H's zero-byte route instead:
- the A2 skip on request 0;
- the fork B3 health gate;
- camera LKAS off by procedure.

E2's trace of the 6803 readers outside the lane (dead code plus one UDS DID read-out) is worth filing either way.

**G4. G's c_D regression as the fresh-D instrument.** It needs no new bit, and the D step is resolvable in one drive. Add E2's
one-episode I-component read for the ARB. Together they make every edit in the graft observable without a cave telemetry bit.

**G5. Fix the shared PM extractor** (`% 360 - 180`, G's finding 1) before any further envelope search. It changes no published
gated number (0 / 80 920) but corrupts envelope searches.

**G6. File V6 in the GATE-1 record.** No static `jarl disp32` / `jr disp32` / LE32 reference to `FUN_0002a93a` or
`FUN_0002a508` exists. That covers 4 of the 5 static call forms (E2's Format-V, LE32 and movhi/movea scans, plus V6). It
strengthens E1-reset's and H's claim that the lane owns `gp-0x6dd0` alone, and G-A22's sentinel. Computed dispatch remains
BELIEF.

**G7. E2-A3's low-speed cap (+18 B)** only if the operator rules that a < 8 m/s release lurch outweighs low-speed hold. His
recorded complaint is "loose at low speed", which argues for A2.

---

## 6. Disagreements, with cause

1. **E1: "inherits P2's GATE-2 PASS exactly (0 fails, tier A 46.7, tier B 30.5)".** True on the round-1 set only. On this round's
   R2 box the inherited P2 loop fails 690 points (frequency scorer; V1 confirms E2 carries the same table).
2. **E1: M6-E1 light lurch "up to ~17°".** The time scorer measures 24.3° at 10.25 m/s. E1's speed grid skipped 10.25–12.25 m/s.
3. **E1-cal and E2-R1 are one build** (P2's hex + ICL 8192). They are listed twice and scored once.
4. **H: "ICL 7500 + bleed makes the raised clamp safe, lurch < 4°".** It was measured only at ICL 4096. At 7500 with THR 512 the
   lurch is 22.2° / 20.8° (time scorer). H's own G2 rows at 7500 were withheld.
5. **H: hook at `0x29D7A`.** It overwrites `mov r16,r6 ; sar 5,r6`, and the sketched exit omits `sar 5` (V7). H's mirror does not
   model its own sketch.
6. **H: GATE 2 for H-A.** The common scorer found that `h_freq.des_HA` scored the held `gp-0x6a00` operand, not `gp-0x69ca`, and
   double-aged the +h10 members. H's "fully-stacked residual" is an artefact for H-A. Its real residual is the ms_free products,
   with a 0.84 Hz ring outside its declared bands.
7. **H: cave sizes ~190 / ~164 B.** BELIEF. The in-place D swap (H-A) and the missing `sar 5` are not counted. My range is
   ≈ 216–234 / 190–214 written.
8. **G: "written 213" for P2-class rows.** G counts differently from rev2-A's 200. G's own "diff 198" equals P2's, so the
   normalised total is 200.
9. **G: H-sentinel "untraced".** Partly closed by V6. Computed dispatch remains.
10. **G: "every implementation passes every pre-registered bar".** True of rev2-A's bars. Against the goal, every G row fails
    tracking and turn-hold (time scorer). G ceded F1 to the integral axis, so this is a difference in bar set, not a defect.
11. **E2: none on bytes.** Every size, table and listing I checked matches (V1, V3, V8).

---

## 7. What this judgement cannot see, and what a FAIL looked like

**Written before scoring, as a FAIL for this judge:**
- an uncommanded-torque fault path;
- an unassembled cave presented as final;
- a live instruction or register clobbered at a hook;
- a hard-gate breach at the nominal member;
- GATE-2 evidence computed on a different loop than the bytes build;
- instability on a credible member without a declared stop.

Each one triggers disqualify or rank last. Results:
- E1-splitP: instability + nominal breach → DQ.
- H-A / H-B: unassembled + hook clobber + wrong-loop evidence → last.

**Limits:**
- **The graft (G1) is not scored.** No H1, no GATE 2, no time run on the merged bytes. Its expected standing is BELIEF built from
  two EVIDENCE halves.
- **Everything above ~8 Hz is model.** That includes G-P48d's M20 0.96× and the 13–25 Hz anti-damping rows.
- **V6 has no genuine in-image positive control for the disp32 form.** The null is exhaustive over the encoding, but rests on the
  ISA definition.
- **The κ (torque-word scale) behind every light-hand lurch number is unmeasured (BELIEF).** E2's family brackets it. E2-A2 is the
  only policy whose bound does not read the torque word.
- **F5 cannot be simulated** (the camera relay case, pol ≠ −1). Every fresh-D row, the graft included, carries the pol = −1
  dependence (record EVIDENCE, boot-static). The image must not go to another car. The R1 INVERTED check covers the first drive.

**Flight prerequisites for whichever row or graft is chosen, not waived:**
- H5: Ghidra decode of the BUILT image, including the policy block and the D operand sign.
- H6: B2 dominance, r8 deadness and r25/r14 liveness on the built image.
- H8: every CRC recomputed.
- V1: re-header the revert `.rwd`.
- The adversarial pass on the built image, with "do not flash" reachable.
