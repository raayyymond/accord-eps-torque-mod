# V299 rev 2 — GOLDEN MIRROR + H1 + rebuild (build-round subagent report)

**Status: ANALYSIS ONLY.** Nothing was flashed, no CAN was sent. The `_v299_…_plain_image.bin` written to
`accord-firmwares/analysis-2020accord/` is a study artifact until the operator names the file and the bus.
No git touched in either repo. **Classifier interruptions: 1** (one mid-turn safety interruption after the
Ghidra cave decode of the built image; noted and continued — defensive analysis on the operator's own ECU).

**EVIDENCE** = image bytes, the Ghidra dry-run decode, the kit V850E2 interpreter, or a script run this session
(named with its wall time). **BELIEF** = none load-bearing here; this is a byte/arithmetic verification task.

Built image (job 3 output, written this session):
`_v299_V299-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3-2LVL.4096.6144.V2880.FRZ1229.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16B_plain_image.bin`
sha256 **`30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08`**; cave (0xC4C00..0xC4D04, 260 B)
**`e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608`** — both match the spec exactly.

---

## 1. Golden mirror — `_self_check_v299` (EVIDENCE)

Added `_self_check_v299()` to `analysis-2020accord/model/eps_chain_control.py`, beside `_self_check_v298`;
imported and called from `_self_check()` in `eps_chain_delivery.py`; **exported through the facade**
`eps_lkas_chain_model`.

It reads the V299 cave immediates and the F181 string FROM the built image (globs `_v299_*plain_image.bin`
in `ACCORD_FIRMWARE_ROOT`; **skips silently if absent** so the hashed stdout is unchanged either way), asserts
them against the design, then runs a scalar integer mirror of `cave_rev2` (spec §1.3) — reading the asserted
immediates, not hard-coded constants — and asserts hand-computed cases:

- **two-level cap regimes:** `bound(1000,Ep>0,v)` = 4096 at v≤1382 (incl. v=1382), 6144 at 1383≤v≤2880, and
  `(1000<<6)+1250` (uncapped) at v=2881; small-angle `16|θ|+1250` below the cap.
- **asymmetric bound:** sign(θ)≠sign(E′) ⇒ the |θ| term drops ⇒ bound == B == 1250, on both the capped and
  the no-cap paths; and ≠ the same-sign bound (the clause actually moves it).
- **hard freeze at raw 1229/1230:** `a4f68`=1229 does **not** freeze (proceeds); 1230 freezes; E′ is still
  computed before the freeze.
- **the other exits:** op-skip window edges (`op+13000` in/out of [0,26000]), camera gate (r25=0 → CAM),
  winding past the bound (I>>10 ≥ bound → FRZ), ramp-in freeze, and the armed DONE path.

Also asserts the shared V298 cals (fb a/b/C, Ki/ICL/DCL, Kp 112×5, Kd 48×4), the relinked table pointer, the
GB-P 7 rows, the op-skip/FRZ/CAM jr tails and the camera-gate bytes — all byte-identical to V298.

**Contract verified** (`import eps_lkas_chain_model`, image present):
- **95 non-dunder symbols** (94 → 95; `_self_check_v299` is the one added facade symbol).
- `_self_check()` + `_demo()` stdout = 2512 bytes, sha256
  **`740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`** — **UNCHANGED** (prints nothing).
- Positive control: `_self_check_v299()` runs its assertions clean with the image present; skip path is clean
  when the image is absent.

## 2. H1 — kit V850E2 interpreter on the BUILT cave vs the mirror (EVIDENCE; `h1_v299_built.py`, 9.8 s)

The cave is read FROM the built image (`img[0xC4C00:0xC4D04]`, sha `e22193b9`, == the reviser's
`rev2_cave.hex`) and executed by `panel2/score_time.Cpu2` (via the reviser's `rev_h1` harness: exit pc, r16=E′,
r26=op, r6 on freeze/camera, RAM-untouched, non-scratch registers). Compared against the mirror arithmetic
(`rev_h1.cave_rev2`), which a cross-check proves identical to the golden model's `bound()` (0/6000).

| class | cases | mismatches |
|---|---|---|
| random valid/frz (2 seeds) | 5881 | **0** |
| random op-skip | 5381 | **0** |
| random camera (r25=0) | 738 | **0** |
| targeted (1382<v≤2880, 1381–1383/2879–2881 edges, I straddling 4096–6144) | 4000 | **0** |
| cross-check golden `bound()` == spec `cave_rev2` | 6000 | **0** |

**Negative controls (targeted 2000, must mismatch > 0 — the check can fail):**
- **N1** V298 cave bytes vs the V299 mirror: **2056** mismatches (the single-cap edit is observable; first at
  v=1382, a run/freeze exit split).
- **N2** rejected single-cap `alt4` bytes vs the V299 mirror: **118** mismatches (the two-level cap is
  distinguishable from the single 6144).

## 3. Ghidra decode of the BUILT image (EVIDENCE)

Dry-run decode of 0xC4C00–0xC4CD9 on the 30ff05fa bytes (program `REFUTE_V299R2_DISASM_ONLY.bin`, byte-identical
to the written image; no program saved) reproduces spec §1.1's 24 rev-2 instructions exactly: the hard-freeze
`movea 0x4cd`(=1229) at 0xC4C62 with `bh` freeze; the asymmetric `cmp r0,r16 / bge / subr` then `cmp r0,r9 /
bge / mov 0,r9`; the two-level cap `movea 0xb40`(=2880) gate, `shl 4` + `addi 0x4e2`, `movea 0x566`(=1382) gate
selecting `movea 0x1000`(=4096) or `movea 0x1800`(=6144), `cmovh`; the `shl 6` uncapped path; `sar 0xa`(=I>>10);
the winding/ramp freezes; `jmp [r6]` DONE. Tail from 0xC4CAC and the FRZ/CAM `jr 0x29D7E` match V298.

## 4. Rebuild reproduces the image bit-for-bit — TWO independent methods (EVIDENCE)

1. **Bare splice** (this session): V298 base (177abf04) + overlay the 260-B rev-2 cave + `0x1310D 41→42` +
   recompute the single main-block CRC `[0x13000,0xC4FFC)` → trailer `f3 d8 7c 6b → 95 3b dd 70`; image sha
   **30ff05fa**, diff vs V298 = exactly **67 bytes** (60 in-span + 2 imm16 + 1 F181 + 4 trailer, 0 stray);
   `walk_all_blocks`=0 (50/50), `walk`=0 (49/49).
2. **`build_v299_tva.py`** (created from the V298 template; V298-based, one CRC block; 28/28 assertions —
   17 substantive, 5 constant, 2 entailed, 4 tautological): PREDICTED image sha **30ff05fa**; cave
   `e22193b9`; trailer `95 3b dd 70`; diff == 67; chain 50/50; bootloader 49/49; the rwd decodes back
   byte-identical to the built image; cipher validated non-circularly on V38; `'/'` = [A110, A160, A16A,
   A16B]. Run in predict mode (no files written by the script).

## 5. Files written this session

- `analysis-2020accord/model/eps_chain_control.py` — `_self_check_v299` added.
- `analysis-2020accord/model/eps_chain_delivery.py` — import + call in `_self_check()`.
- `analysis-2020accord/model/eps_lkas_chain_model.py` — facade export (+1 symbol → 95).
- `analysis-2020accord/builds/v108_plus/build_v299_tva.py` — the build script.
- `analysis-2020accord/studies/angle_loop/v299_build/h1_v299_built.py` + `.out.txt` + `.json` — the H1 run.
- `accord-firmwares/analysis-2020accord/_v299_…A16B_plain_image.bin` — the built image (study artifact).
- This report.
