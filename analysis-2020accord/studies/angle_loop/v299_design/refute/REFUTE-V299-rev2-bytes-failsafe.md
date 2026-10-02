# REFUTE V299 rev 2 — BYTES / FAIL-SAFE (2026-10-02)

**Role:** RE-REFUTER (bytes + fail-safe) of `DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md`. Job: (a) check every defect
my earlier colleague raised (`REFUTE-V299-bytes-failsafe.md`, D1/D2/D3) is RESOLVED in rev 2, not re-worded; (b) try
to break the revision itself on a wrong byte, bad relink, stale state word, broken CRC, GATE 1, or a fork path that
drops steering / cannot be overridden. **Default = refuted where uncertain; a "do not build" verdict was reachable.**
Read-only: Python LE rebuild of the V298 image, a fresh analysis-free Ghidra import of my own rebuilt image (never
the ADVIG DB), fork/DBC source read. EVIDENCE = image bytes / a script I ran this session (named, wall) / Ghidra
listing; BELIEF = inference. **Classifier interruptions this session: 1 (noted, continued).**

V298 image `_v298_…A16A_plain_image.bin` sha256 `177abf04…` (0x100000 B, confirmed).

## 0. What a FAIL looks like (pre-registered, before any check — `refute/rev2_bytes/PREREG.txt`)
F-a old byte asserted by rev 2 §1.1 ≠ V298 · F-b my rebuild ≠ rev 2's cave/image sha, trailer, or 67-diff count ·
F-c Ghidra decode ≠ §1.1's 24 instructions / an instruction straddles 0xC4CAC · F-d a branch targets a
non-instruction-start or an external xref hits the span · F-e any `st.*`/new RAM in the cave (GATE 1) · F-f camera /
op-skip / sentinel / ramp / hard-freeze path changes behaviour beyond 512→1229 + the bound · F-g the cap structure ≠
§1.3 on the 1381–1383 / 2879–2881 edges · F-h CRC chain or bootloader walk ≠ 0, or an edit straddles a block ·
F-i a prior defect merely re-worded.

**None of F-a…F-h materialised.** One finding on F-i / the fail-safe surface (§6). **VERDICT: PASS_WITH_DEFECTS.**

## 1. Byte table — independently rebuilt bit-exact (EVIDENCE: `rev2_bytes/re_build.py`, 0.07 s)
I applied rev 2 §1.1 to the V298 image from scratch (my own patch dict, not rev 2's script) and recomputed the CRC:

| quantity | spec rev 2 | my rebuild | match |
|---|---|---|---|
| old bytes asserted = V298 (26 addrs incl. hard-freeze region) | all | all 26 match | yes |
| cave content bytes differing [0xC4C00,0xC4D04) | 62 | 62 | yes |
| F181 byte @0x1310D | 1 | 1 | yes |
| main trailer [0x13000,0xC4FFC) | `95 3b dd 70` | `0x70DD3B95` → `95 3b dd 70` | yes |
| V299 cave sha256 (260 B @0xC4C00) | `e22193b9…1133608` | `e22193b9…1133608` | yes |
| V299 image sha256 | `30ff05fa…748c38f08` | `30ff05fa…748c38f08` | yes |
| total diff vs V298 | 67 (cave 62 + F181 1 + trailer 4) | 67 | yes |

F181: 0x1310D `41`('A')→`42`('B') ⇒ `39990-TVA,A16A`→`…A16B` (string re-read at 0x13100, EVIDENCE). The 62 cave diffs
are confined to 0xC4C64 (imm) and 0xC4C6A–0xC4CA8; camera gate 0xC4C5A, op-skip 0xC4C14, G-table ptr 0xC4C1C, the
GB-P rows and the FRZ/CAM/DONE tails are byte-identical (diff=67 exactly accounts for only the attributed bytes).

## 2. Decode — the rebuilt bytes are the claimed instructions (EVIDENCE: Ghidra, read-only import)
I imported my rebuilt image as `REFUTE_V299R2_DISASM_ONLY.bin` (V850:LE:32, **no auto-analysis**, folder
`/refuteR2scratch`; the ADVIG DB was never written) and `disassemble_bytes` 0xC4C5E–0xC4CD9. Every instruction equals
§1.1 / §1.3:

- **Hard freeze (structure = V298, only the immediate changed):** `movea 0x4cd,r0,r13` @0xC4C62 (= 1229), `cmp r13,r8`,
  `bh 0xC4CC2` @0xC4C68. 1229 raw = wire 1200 = Honda `steeringPressed`. ✓ (F-f clear)
- **The span (24 instr, 0xC4C6A→ends 0xC4CAC):** `ld.h -0x6a00,gp,r9`(θ) · `cmp r0,r16`;`bge 0xC4C74`;`subr r0,r9`
  (r9=θ·sgn E′) · `cmp r0,r9`;`bge 0xC4C7A`;`mov 0x0,r9` (clamp ≥0) · `ld.hu -0x6a5e,gp,r8`(v) · `movea 0xb40`(2880);
  `cmp`;`bh 0xC4CA6` (v>2880 → shl6 no cap) · `shl 0x4,r9`;`addi 0x4e2`(+1250) · `movea 0x566`(1382);`cmp`;`bh 0xC4C9A`
  · `movea 0x1000`(4096);`br 0xC4C9E` | `movea 0x1800`(**6144, NEW**) · `cmp r13,r9`;`cmovh r13,r9,r9` (bound:=min_u)
  ;`br 0xC4CAC` · `shl 0x6,r9`;`addi 0x4e2`. ✓
- **Tail resumes V298 at 0xC4CAC:** `ld.w -0x6dd0,gp,r13`;`sar 0xa`(S=I>>10);`cmp r0,r16`;`bge`;`subr r0,r13`;
  `cmp r9,r13`;`bge 0xC4CC2`(FRZ, winding past bound);`andi 0x8000,r14,r13`;`bne 0xC4CD8`;FRZ/CAM/`jmp r6`. ✓

**GATE 1:** the decoded new instructions are loads/compares/branches/shifts/adds/`cmovh`/`mov-imm`/`subr` only —
**zero `st.*`, zero new RAM, zero new state word.** The rest of the cave is byte-identical to V298 (GATE-1 clean, flew).
Register discipline: r16 (E′) untouched by the span; r13/r8 reloaded before each use; read set SHRINKS (gp-0x4f60 no
longer read). ✓ (F-e clear)

**Cap edges (F-g), from the branch semantics (`bh` = unsigned strictly-greater, Ghidra-confirmed):** v=1382 →
cap 4096; v=1383 → 6144; v=2880 → shl4+capped; v=2881 → shl6 no cap — equals §1.3's `cap = 4096 if vv<=1382 else
6144` and `vv>2880` gate exactly. `cmovh` after `cmp r13(cap),r9(bound)` sets bound:=min(bound,cap) (reg2−reg1 flags).
✓ `rev_h1.py cave_rev2` uses the same vlo 1382 / vhi 2880 / 4096 / 6144; the kit-interpreter H1 (bytes==mirror) is
deferred to the built image in §11.1 — the plan is coherent (negatives pre-specified) and the decode already matches.

## 3. Relink / branch census (EVIDENCE: the rebuilt-image listing)
In-place, same length; the G-table ptr `mov 0xC4CDA,r9` and every tail target are unchanged. Every branch target is an
instruction start: 0xC4C68→CC2, C70→C74, C76→C7A, C84→CA6, C92→C9A, C98→C9E, CA4→CAC, CBA→CC2, CC0→CD8. The only
in-span target an external path could reach is the fall-through from the hard freeze at 0xC4C6A; cave entry remains
`jarl 0xC4C00,r6` @0x29D76 (untouched). No branch lands mid-instruction; nothing straddles 0xC4CAC (last new instr
`addi` @0xC4CA8 len 4 ends exactly at 0xC4CAC). Patch-by-address is required (rev 2 does this): `movea 0x1000` recurs
at 0x31C74, `movea 0x200` at 0x6271E — `movea 0x1800` occurs nowhere. ✓ (F-c, F-d clear)

## 4. CRC (EVIDENCE: `rev2_bytes/re_crc_gate1.py` via `lib/verify_bootloader_crc.py`, 0.01 s)
Both edits (0x1310D, 0xC4C64–CA8) are inside the single block **[0x13000,0xC4FFC)**; no straddle. On my rebuilt image:
**`walk_all_blocks` = 0 bad (full chain 50/50)** and **`walk` = 0 bad (bootloader replay 49/49, the NRC-0x72
predictor, 0xC6000 bridge included)**. Block #50 [0x13000,0xC4FFC) calc = `0x70DD3B95` = the trailer. §11.3's assertions
reproduce. ✓ (F-h clear) — this is the exact check prior D3 asked to be named, now run and green.

## 5. Prior colleague's defects — resolution status
- **D2 (deferred build gates) — RESOLVED.** §11.1 lists all six as blocking PASS gates (golden-model mirror 94→95 /
  hash `740f4bcd…` unchanged; by-address build-script with image/cave/trailer asserts + assertion census; H1 on the
  BUILT image with pre-specified negatives; Ghidra decode of the built image; the four-lens adversarial pass with
  "do not flash" reachable; fork F12). rwd + CRC plans in §11.2/§11.3.
- **D3 (name the CRC chain + bootloader checks, not just zlib.crc32) — RESOLVED and VERIFIED.** §11.3 asserts
  `walk_all_blocks==0` and `walk==0`; I ran both on the rebuilt image, 0 bad (§4).
- **D1 (0x1AB counter/checksum) — PARTIALLY resolved; a NEW error introduced → §6.** Rev 2 correctly overturns the
  prior "no COUNTER" (the DBC does define `COUNTER 21|2`) and adds `ignore_counter`. But it replaces it with a fresh
  factual error ("There is no CHECKSUM"), which is wrong and has an instrument consequence.

## 6. NEW DEFECT — §2.1 "there is no CHECKSUM" on 427 is false (EVIDENCE: DBC + opendbc parser, fork `2712e1336`)
**Claim (rev 2 §2.1 / change-table F6):** `BO_ 427` has `CONFIG_VALID, MOTOR_TORQUE, OUTPUT_DISABLED, COUNTER` and
**"There is no CHECKSUM"**, so the parser does no checksum validation and only `ignore_counter=True` is needed; the
checksum is re-done by hand in carstate on `cp.vl_raw`.

**What the source actually says:**
- `opendbc/dbc/honda_accord_2017_can_ext_generated.dbc:86` (the DBC the car loads) **and** `_honda_common.dbc:66`
  both define `SG_ CHECKSUM : 19|4@0+` on message 427 (byte-2 low nibble). The CHECKSUM signal IS present.
- `opendbc/can/dbc.py set_signal_type`: a signal named exactly `CHECKSUM` gets `sig.calc_checksum = chk.calc_checksum`,
  and for a `honda_*` DBC `get_checksum_state` returns `HONDA_CHECKSUM, honda_checksum`. So 427's CHECKSUM carries
  `calc_checksum = honda_checksum`.
- `opendbc/can/parser.py MessageState.parse`: `if not self.ignore_checksum and sig.calc_checksum is not None:` →
  computes the honda checksum and, on mismatch, `checksum_failed=True; return False`. **Rev 2 sets `ignore_counter`
  but never `ignore_checksum`**, so the parser DOES validate the honda checksum on 427.

**Consequences (crux verified myself):**
1. **Not a steering-drop / override-loss hole** (so NOT a FAIL on my axis). 427 is listed with `float("nan")` ⇒
   `optional_msg=True` ⇒ `ignore_alive=True` ⇒ `MessageState.valid()` returns True unconditionally, and `counters_valid`
   is untouched (`ignore_counter`). A 427 checksum failure makes `parse` return False but **cannot drop `can_valid`**.
   The pre-registered worry "0x1AB listed so canValid can drop in angle mode" does NOT materialise.
2. **Instrument-correctness risk (the real defect).** `update()` refreshes `self.vl_raw[address]` **only when
   `parse()` returns True.** On any 427 frame where opendbc's `honda_checksum` disagrees with the EPS's actual byte-2
   checksum, `parse` returns False and **`vl_raw` goes stale** — so the fork's own carstate decode of `cp.vl_raw`
   (steeringTorqueEps, the bar, the rule-identity replay) reads a frozen/old frame. The whole scheme only works if
   opendbc's `honda_checksum` matches the EPS 427 checksum on every good frame — which rev 2 never checked, because it
   believed there was no parser checksum. If they match, the manual carstate re-check (F6) is redundant/tautological
   (it re-validates a frame the parser already passed); if they differ, the instrument is silently dead on-car.
3. **Wrong design basis recorded.** §2.1 line "the DBC does not declare" a checksum is incorrect and should not be
   cited as the reason the manual check is needed.

**Severity: medium** — not a wrong firmware byte, not a brick, not a loss of driver override (the bytes and canValid
are safe). It is a fork-parser / instrument correctness error with a false stated basis. It sits on the boundary with
the fork-safety-interface lens, but the prior bytes refuter owned the 0x1AB item, so its resolution is in scope here.

**Fix (small, matches rev 2's own intent):** on the 427 state set **`ignore_checksum = True`** alongside
`ignore_counter = True` (one line, as already done for 0x201), so `vl_raw` always refreshes; keep the fork's own
`honda_checksum` in carstate as the single meaningful gate. **Before relying on either, confirm the kit's
`d1_427_check` honda-checksum == opendbc's `honda_checksum(0x1AB,…)`** (the "100.000 %" figure must be recomputed with
opendbc's function, not a bespoke one) so a mismatch cannot freeze the bar. Correct the §2.1 text: CHECKSUM:19|4 IS
defined; the parser validates it unless ignored.

## 7. Verdict
**PASS_WITH_DEFECTS.** The byte build is bit-exact (independent rebuild reproduces cave `e22193b9…`, image `30ff05fa…`,
trailer `95 3b dd 70`, 67 diff bytes, 26/26 old-byte asserts). Decodes equal §1.1/§1.3 incl. the hard-freeze immediate
1229, the two-level cap, and the unchanged V298 tail; GATE 1 holds (0 `st.*`, 0 RAM); no relink error; CRC chain and
bootloader replay both 0 bad, no block straddle; cap edges correct. Prior D2 and D3 are resolved and (for D3) verified.
Prior D1's counter half is fixed, but rev 2's new "no CHECKSUM" claim is false (§6): a medium instrument defect with a
wrong basis, not a brick or a steering-drop. The §11.1 prerequisites (golden-model mirror, H1 on the BUILT image,
Ghidra decode of the BUILT image, the four-lens pass, fork F12) remain the gates before any flash.

Scripts (all < 1 s, `refute/rev2_bytes/`): `re_build.py`, `re_crc_gate1.py`; PREREG `PREREG.txt`. Ghidra: fresh
analysis-free import of my rebuilt image only; the ADVIG DB was not written.
