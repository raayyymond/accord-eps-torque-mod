# HANDOFF 2026-07-24 (later) — V51P GATE-1 PASS; V52 built-but-incomplete; gp-0x4f60 = 19-carrier surface

Supersedes the earlier 2026-07-24 handoff (`handoffs/2026-07/HANDOFF-2026-07-24-gate1-fail-newid-fourframe-telemetry.md`)
on V51P/V52/cell status. Read `CLAUDE.md`'s **LATEST-2 (2026-07-24)** block first, then
`memory/reference/builds/reference-accord-v51p-gate1-both-cells-clean.md` + `memory/reference/firmware/reference-accord-gp4f60-carrier-surface.md`.

## TL;DR

1. **V51P was FLASHED + DRIVEN (rlog 7) → BOTH candidate cells gp-0x1300 AND gp-0x1100 are GATE-1 CLEAN.**
   Two independent decoders: 0/24000 CAN-330 frames nonzero, beacon 100% live, stock null distinguishable.
   The EMA state cell is no longer the problem — the definitive live-probe clearance gp-0x1500 failed.
2. **V52 BUILT (UNFLASHED)** = V50's EMA low-pass rebuilt on gp-0x1300 + round-to-nearest + the 3
   `FUN_0002eda8` lanes V50 missed. Internally clean (50/50 CRC, x31 round-trip, RWD readback). SHA
   `bf4bc5b4…`. **10 repoints.**
3. **🛑 V52-as-built is INCOMPLETE — do NOT flash it as a fix.** A definitive raw byte-scan proved
   `gp-0x4f60` has **64 raw readers** and **~19 command-path carriers across BOTH the 1 kHz control task
   AND the ~100 Hz assist task.** V52 repoints only 10 → misses 9 (incl. 3 that self-filter → cascade risk,
   + 2 mode-gated). Half the resonance still reaches the command ⇒ not even a valid efficacy test as-is.
4. **NO brick hazard** — every `gp-0x4f60` monitor compares raw vs a LITERAL constant, not a filtered value.
   The risk of the broad filter is **feel/efficacy, not a motor-slam.**
5. **Recommendation: next flash = FOURFRAME (diagnose-then-filter), not V52.** The byte-scan is the concrete
   empirical case for the operator's own reframe: FFT the carrier lane, filter it narrowly at a convergence
   point (`gp-0x6ad6` / `gp-0x6b70`), not the 19-consumer `gp-0x4f60` root.

## 1. Housekeeping (operator's explicit asks — DONE, committed `47e4d96`)

- **rlog captures untracked:** `git rm --cached` on all 37 tracked `.zst` (working copies kept);
  `.gitignore` now ignores the whole `analysis-2020accord/rlogs/` tree (also stops the `manual/aa5b3e0c01/`
  camera media `.hevc`/`.ts` from ever being committed). rlogs are now LOCAL-only.
- **New V51P logs placed:** `rlogs/75604b0a432fdc89_00000007--0a8e7099b8--{1,2,3,4}--rlog.zst`.

## 2. V51P GATE-1 result — both cells CLEAN

Decoded two ways with identical results (`analysis-2020accord/studies/probes/decode_v51p_gate1.py` + a from-scratch lead
verifier). CAN-330 on **bus 1**, 24,000 frames:

| | V51P drive (bus 1) | Stock null (bus 1) |
|---|---|---|
| Beacon = 1 | 100.0% (24000/24000) | 0.0% |
| **B = gp-0x1300 nonzero** | **0 (0.0000%) — never** | 0 |
| **D = gp-0x1100 nonzero** | **0 (0.0000%) — never** | 0 |

Both outside the 0xb7260 mailbox array and the gp-0x1401..0x1502 poison region. **V52 uses B = gp-0x1300**;
D = gp-0x1100 is the drop-in alternate. This clears the *cell*, not the filter's completeness.

## 3. V52 build (`builds/v50_v79/build_v52_tva.py` + `studies/caves/v52_cave_asm.py`, UNFLASHED)

V52 = V50 with three deltas:
1. **State cell gp-0x1500 → gp-0x1300** (V51P-cleared; the definitive live-probe clearance gp-0x1500 lacked).
2. **Round-to-nearest** `y += (74·d + 512)>>10` (one `addi 512,r12,r12` before the `sar 10`) — kills V50's
   arithmetic-floor **−6.5..−7 count DC-bias ratchet** + the local +15% gain bump in the 11-33 count band.
   Frequency response unchanged (α=74/1024) → GATE-2 verdict for the *filter itself* carries and improves.
3. **3 more repoints** — the `FUN_0002eda8` 3-way branch (0x2F318/0x2F330/0x2F33E, all r7, word1 0x3F24)
   that V50 missed → feeds `gp-0x6b6c` → `FUN_000339cc` → base-assist lane/channel 9.

Cave = 86 B @0xC4B34 (V50's 82 + the round `addi`). Verify: 50/50 CRC, x31 round-trip, RWD readback,
diff = exactly 114 bytes (10 repoints + ratchet + trampoline + cave + CRC), 4× (0xC646C=3564) and the
DTC-0x1d clamp trap confirmed stock. **V52 SHA `bf4bc5b4…`, RWD SHA `37776648…`.**

⚠ Still requires (kit rule, NOT yet done) before any flash consideration: **Ghidra re-disassembly of the
built `_v52_plain_image.bin`** (cave + hook transparency + 10 repoints) — deferred because the build is
incomplete (see §4). The `FUN_0002eda8` repoint's monitor-safety WAS verified: two tracers + a byte-scan
agree the one DTC-0x1d monitor it touches (channel 9, `FUN_00033ba8`) derives both legs from the same
now-filtered cell (shared-input, no raw-vs-filtered divergence), and the surfaced 3rd reader of gp-0x6b6c
(`0x4FFD0`) is a benign self-referential diagnostic logger.

## 4. ★ THE FINDING: gp-0x4f60 is a 19-carrier surface, not 7 (why V52 is incomplete)

The `FUN_0002eda8` miss proved V50's carrier enumeration was unreliable, so a **definitive raw byte-scan**
(disp16 0xB0A0, gp-relative loads over [0x13000,0xC4FFC)) was run: **64 raw `gp-0x4f60` readers image-wide.**
Classifying the ~23 command-region readers (2 firmware-codepath-tracer agents) →

**~19 command-path CARRIERS. V52 repoints 10; the 9 MISSING:**

| Site | Reg / word1 | Function (task) | Destination | Note |
|---|---|---|---|---|
| 0x29A90 | r12 / 0x0C24 | FUN_00028ea6 (1 kHz control) | gp-0x6a32/gp-0x6b2c cluster | arbitration LERP curve select |
| 0x2B69E | r? / verify | FUN_0002b62c (~100 Hz assist) | gp-0x6aea → FUN_0004e96a | EMA/corridor blend |
| 0x2DF32 | r? / verify | FUN_0002db94 (~100 Hz) | gp-0x6b1a → FUN_0002e52e | LERP boost/damping blend |
| 0x33D2A | r? / verify | FUN_00033d10 (~100 Hz) | gp-0x6b78 → FUN_0003405a | **float PID controller** |
| 0x36682 | r11 / 0x0B24 | FUN_00036682 (control) | gp-0x6b46 → FUN_00038148 | **SELF-FILTERS (IIR)** |
| 0x36846 | r14 / 0x0E24 | FUN_00036828 (~100 Hz) | gp-0x6b44 | **SELF-FILTERS (EMA)** |
| 0x3B908 | r9 / 0x0924 | FUN_0003b8f6 (control) | gp-0x6bfc → gp-0x6bfe | **SELF-FILTERS heavily (float IIR)** |
| 0x3F8E2 | r11 / 0x0B24 | FUN_0003f884 (dispatch) | gp-0x6a0a → FUN_0003b338 | **mode-gated (gp-0x4e5f); liveness UNCONFIRMED** |
| 0x3FCC6 | r7 / 0x0724 | FUN_0003fc16 (control) | gp-0x6a0a | **mode-gated (tp+0x74cf + gp-0x4ebc)** |

Chains converge at **`FUN_00037fe6`** (7-lane grand sum → `gp-0x6ad6` → `FUN_0003a382`, the governor-slew
lane) and **`FUN_00038148`** (→ `gp-0x6b70`). These convergence points are the natural **narrow-filter**
targets.

**MONITOR HAZARDS: none.** Every monitor read compares raw `gp-0x4f60` vs a literal constant: M1
`FUN_00042af8`@0x42C20 (±25600 counts → gp-0x6af8), M2 `FUN_00043e44`@0x43EDA (IEEE-754 double 25.0), the
FUN_00028ea6 plausibility gate @0x28F26 (±25600). So the broad filter can't brick via a V27-class
raw-vs-filtered lockstep — correct architecture (health gates belong on the raw sensor).

**Benign readers** (leave raw): producer 0x7Exxx-0x81xxx; CAN packers (0x1Cxxx broadcast, 0x55xxx CAN-399,
0x4D8xx, UDS 0x4E4xx/0x4E8xx); diagnostic loggers FUN_0004fbde/FUN_0002ec52; angle-cal SM 0x69C12.
**Dead:** FUN_0002a93a (0x2A992), orphan fragment 0x2d5fe-0x2db93 (0x2D9A2/0x2DAE6).

## 5. Recommendation

**Next flash = FOURFRAME**, not V52. Filtering `gp-0x4f60` at the source + repointing consumers is a
whack-a-mole across a **19-lane, two-task surface** (3 self-filter → cascade/over-attenuation, 2 mode-gated),
and GATE-2 was only closed for a 7-lane insertion. That is the exact fragility the diagnose-then-filter
reframe avoids:

> Flash FOURFRAME (`builds/telemetry/build_vfourframe_tva.py`, IDs 0x6a0-0x6a3, red-panda-visible) → drive with the buzz,
> **applying the operator's vibration-window filter to the FFT** (4-6 mph OP-engaged; or 3+ mph OP-engaged,
> no driver override, significant commanded LKAS torque) → FFT the 16 backward-chain signals → filter the
> ONE carrier lane narrowly at a convergence point (`gp-0x6ad6` / `gp-0x6b70`).

**If the operator wants the broad V52 anyway** (direct low-pass efficacy test), completing it needs:
(a) register verification for 0x2B69E/0x2DF32/0x33D2A (one dry-run disasm each → word1);
(b) **self-filter cascade analysis** for 0x36682/0x36846/0x3B908 (they already IIR/EMA — repointing to the
    12 Hz copy cascades → over-attenuation; may need to leave raw or re-tune fc);
(c) **mode-gate liveness confirmation** for 0x3F8E2/0x3FCC6 (are gp-0x4e5f / gp-0x4ebc live in normal
    driving, or fallback/speed-only?);
(d) a **full GATE-2 re-analysis** for the 19-lane insertion (the 7-lane verdict does not carry);
(e) then rebuild (19 repoints) + Ghidra re-disasm of the built image.

## 6. Open items

- **Direction unresolved (operator's call):** complete-and-certify broad V52, vs FOURFRAME→FFT→narrow.
- V52's Ghidra re-disasm of the built image is NOT yet done (deferred pending direction; the build is
  incomplete anyway).
- Register operands for 0x2B69E/0x2DF32/0x33D2A confirmed via decompile, not re-disassembled at the byte.
- Mode-gate liveness (gp-0x4e5f, gp-0x4ebc) inferred, not proven.
- FOURFRAME red-panda flash-test (parked collision listen → flash → confirm 4 IDs @62.5 Hz, no bus
  disruption) still outstanding from the prior handoff — it's the gate to the FFT path.

## 7. Files this session

- **New:** `analysis-2020accord/studies/probes/decode_v51p_gate1.py`, `builds/v50_v79/build_v52_tva.py`, `studies/caves/v52_cave_asm.py`;
  `memory/reference/builds/reference-accord-v51p-gate1-both-cells-clean.md`, `memory/reference/firmware/reference-accord-gp4f60-carrier-surface.md`;
  agent-memory `reference_accord_gp6b6c_full_reader_map_fun4fbde_diagnostic_only.md`.
- **Updated:** `CLAUDE.md` (LATEST-2 block), `memory/MEMORY.md`, `analysis-2020accord/model/eps_lkas_chain_model.py`
  (header correction: 7 → 19 carriers), `.gitignore`.
- **Built (gitignored, UNFLASHED):** `_v52_plain_image.bin` + the V52 `.rwd` under `../accord-firmware`.

## Process notes

- **The kit-mandated raw byte-scan (over `search_instructions`) was decisive twice this session** — it
  caught the 3rd gp-0x6b6c reader (0x4FFD0) and, more importantly, the 64-vs-12 reader-count gap that
  reframed V52 from "cell-swap + 1 lane" to "19-lane fragile surface." Never trust a `search_instructions`
  reader/writer count for a load-bearing filter/monitor decision.
- **Both cells clean is a stronger result than needed** (only one was required) — gp-0x1100 is banked as a
  proven-clean alternate for any future cave.
