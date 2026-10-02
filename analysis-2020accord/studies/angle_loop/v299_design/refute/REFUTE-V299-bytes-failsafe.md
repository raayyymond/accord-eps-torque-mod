# REFUTE V299 — BYTES / FAIL-SAFE (2026-10-02)

**Role:** adversarial refuter, bytes + fail-safe surface. Job: make V299 FAIL on a wrong byte, a bad relink,
a stale state word, a broken CRC plan, GATE 1, or a fork path that drops steering / cannot be overridden.
**Default = refuted where uncertain. A "do not build" verdict was reachable (see section 0).**
Read-only: Python LE re-read of the V298 image, Ghidra `disassemble_bytes` on the V298 DB (never written),
DBC/fork source read. EVIDENCE = image bytes / a script I ran this session (named, wall) / Ghidra listing;
BELIEF = inference. Classifier interruptions this session: 1 (noted, continued).

Target spec: `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-2026-10-02.md`.
V298 image: `_v298_...A16A_plain_image.bin`, sha256 `177abf0435508517…` (confirmed, 0x100000 B).

## 0. What a FAIL looks like (pre-registered, before I started)
- **wrong byte** — any spec'd V299 byte != the V298 image at that address, or a decode that does not yield section 1.2.
- **bad relink** — any branch (into or out of the cave) landing inside the rewritten span 0xC4C6A–7D on a
  nop/partial instruction; or the GB-P table pointer (`mov 0xC4CDA,r9`) / any displacement shifted.
- **stale state word** — a new RAM word written by the cave without init on engage/disengage/bail/sentinel/
  request-drop; or an existing word left in a register state the downstream depends on, now wrong.
- **CRC** — the recomputed trailer not reproducing; a SECOND integrity check (CRC chain / bootloader replay /
  a cal-ID checksum) left stale; or an edit straddling a CRC-block boundary.
- **fork fail-safe hole** — 0x1AB listed so canValid can drop in angle mode; a mis-deploy where firmware
  commands angle with no fork fade/override; the driver's hand no longer able to win.

**None of these materialised.** VERDICT: **PASS_WITH_DEFECTS** (3, all documentation / verification-completeness,
no byte error, no brick path). V298 is the flown precedent for this exact edit class (cave bytes + one F181
byte + one main-block CRC trailer), route 79.

## 1. Byte table — independently rebuilt, bit-exact (EVIDENCE: refute/rf_build.py, 0.07 s)
I applied the spec section 1.1 patch to the V298 image from scratch and recomputed the CRC:

| quantity | spec | my independent rebuild | match |
|---|---|---|---|
| differing content bytes (cave 21 + F181 1) | 22 | 22 | yes |
| main-block trailer [0x13000,0xC4FFC) via zlib.crc32 | `2d ad cf 2e` | `2d ad cf 2e` (0x2ECFAD2D) | yes |
| V299 cave sha256 (260 B @0xC4C00) | `0ea16bde…a990c82b` | `0ea16bde…a990c82b` | yes |
| V299 image sha256 | `ac15b533…d43160ec` | `ac15b533…d43160ec` | yes |
| total diff vs V298 | 26 | 26 | yes |

Every spec'd V298 source byte re-read LE and matches the image (rf_bytes.py, 0.11 s): 0xC4C64 `00 02`,
0xC4C6A `20 6e 2c 01`, 0xC4C6E `ed 41`, 0xC4C70 `d3 05`, 0xC4C72 `24 4f`, 0xC4C74 `a0 b0`,
0xC4C76 `30 49 d6 25 24 4f 00 96`, 0x1310D `41`, trailer `f3 d8 7c 6b` (= zlib.crc32([0x13000,0xC4FFC)) LE). OK.
0xC4C7C is `00` in V298 and `00` in V299 (nop) -> correctly counted as unchanged (span is 20 B, diffs 19). OK.

## 2. Decode — the new bytes are the claimed instructions (EVIDENCE: Ghidra V298 listing + V850 Format I/II)
V298 ground truth (Ghidra disassemble_bytes 0xC4C00–0xC4CD9): op-skip `jr 0x2A164` @0xC4C14, G-table ptr
`mov 0xC4CDA,r9` @0xC4C1C, GB-P walk 0xC4C18–52, `mul;sar 8` (E') @0xC4C54, camera gate `cmp r0,r25 ; be 0xC4CC8`
@0xC4C5A, hard freeze `ld.hu -0x4f68 ; movea 0x200 ; cmp ; bh 0xC4CC2` @0xC4C5E, opposing clause
`movea 0x12c ; cmp ; bnh 0xC4C7A ; ld.h -0x4f60 ; xor r16,r9 ; blt 0xC4CC2` @0xC4C6A, theta load `ld.h -0x6a00`
@0xC4C7A, abs/shift/+1250/cap/bound/ramp 0xC4C7E–CC0, FRZ `mov 0,r6 ; jr 0x29D7E` @0xC4CC2, CAM 0xC4CC8–D4, `jmp r6` @0xC4CD8.

New-byte encodings, re-derived from V850 Format I/II and cross-checked against bytes Ghidra already decoded in THIS image:
| new byte | instr | derivation | cross-check in V298 |
|---|---|---|---|
| `cd 04` @0xC4C64 | imm16 1229 | 0x04CD LE | — (512->1229; 1200 raw x1.024) |
| `24 4f 00 96` @0xC4C6A | ld.h -0x6a00,gp,r9 | identical bytes | = 0xC4C7A in V298 OK |
| `09 68` @0xC4C6E | mov r9,r13 | (13<<11)\|9 = 0x6809 | mov Format I OK |
| `30 69` @0xC4C70 | xor r16,r13 | (13<<11)\|(9<<5)\|16 = 0x6930 | xor r16,r9 = `30 49` @0xC4C76 OK |
| `ae 05` @0xC4C72 | bge +4 (->0xC4C76) | cond-br disp +4 | `ae 05` @0xC4C80, 0xC4CB4 OK |
| `00 4a` @0xC4C74 | mov 0,r9 | (9<<11)\|(0x10<<5) = 0x4A00 | mov-imm5 Format II OK |
| `00 00` x4 @0xC4C76–7D | nop (mov r0,r0) | 0 | OK |

Flow (V299): |hand_u|>1229 -> FRZ (edit 1); else theta->r9, r13=theta^E', bge skips `mov 0,r9` when same sign
(xor sets S/Z, clears OV -> bge tests sign>=0), else r9:=0; nops fall to 0xC4C7E; abs/shift/+1250/cap ->
bound = (|theta|<<shift)+1250 if sign(theta)==sign(E') else 1250; compare to sgn(E')*(I>>10); ramp<0x8000 -> FRZ.
= spec section 1.2. **Register discipline clean:** r16 (E') not modified by xor...,r13; r13 reloaded at 0xC4C88 before
use; r8 (hand word) reloaded at 0xC4C84; no stale dependency. **No st.* anywhere in the cave on any path -> GATE 1
holds, 0 new RAM, 0 new state word to init.** Read set SHRINKS (gp-0x4f60 no longer read); all other reads = V298.

## 3. Relink / branch audit (EVIDENCE: Ghidra listings 0xC4C00–0xC4CD9)
In-place, same length -> no displacement moves; table ptr `mov 0xC4CDA,r9` unchanged. Every branch target enumerated:
front of cave 0xC4C12->18, 0xC4C14->2A164, 0xC4C28->30, 0xC4C2E->54, 0xC4C36->3E, 0xC4C3C->30, 0xC4C5C->CC8;
tail 0xC4C80->84, 8E->94, 92->96, A0->AC, B4->B8, BA->C2, C0->D8, C4->29D7E, D4->29D7E. **The only xref that ever
landed inside 0xC4C6A–7D was V298's own bnh 0xC4C7A @0xC4C70, which is removed by the edit.** Nothing external
targets the span. Cave entered only by jarl 0xC4C00,r6 @0x29D76 (V298's hook, untouched by V299). FRZ/CAM/DONE
returns 0x29D7E/0x29D7E/0x29D7A and op-skip 0x2A164 are all outside the edited bytes -> unchanged. **No relink error.**
Patch-by-address is required: the 512-movea pattern `20 6e 00 02` also occurs at Honda 0x6271E (my scan); a
pattern patch would corrupt it. The spec patches by address (section 1.1). OK.

## 4. CRC plan (EVIDENCE: rf_build.py, build_v298_tva.py read)
Both edits (0xC4C62–7D, 0x1310D) lie inside the single CRC block **[0x13000,0xC4FFC)** -> one trailer recompute
suffices; it reproduces `2d ad cf 2e` exactly (section 1). **DEFECT D3:** the V298 build additionally asserts the whole
CRC CHAIN walk_all_blocks==0 (50/50) and the BOOTLOADER CRC replay walk==0 (49/49, NRC 0x72 predictor),
not just the per-block zlib.crc32. Because both edits are in-block, those checks WILL pass after the single
trailer recompute — but the spec section A / section 1.1 names only zlib.crc32. The builder must run
walk_all_blocks/walk (as build_v298 does) or a hand-recompute could miss the chain/bootloader dependency.
Verified in-block: 0x1310D>=0x13000, 0xC4C7D<0xC4FFC, no edit straddles a boundary. No cal-ID checksum separate
from the main block: V298 flew having changed 0x1310D (30->41) with only the main-block trailer recomputed ->
that precedent covers V299's identical F181 edit.

## 5. Fail-safe paths (EVIDENCE: listings + DBC + fork source)
| path | behaviour | status |
|---|---|---|
| engage, ramp<0x8000 | andi 0x8000 ; bne still freezes I; gp-0x6dd0 zeroed by 0x2A164 epilogue while not running | unchanged bytes OK |
| request drop / A2 / B2 | cave not entered; Honda epilogue (I:=0, sentinel) | unchanged OK |
| invalid fresh rate \|gp-0x6abe\|>13000 | op-skip jr 0x2A164 | unchanged OK |
| stock camera (r25==0) | CAM gate be 0xC4CC8 BEFORE the hand test -> E'/op:=0, I x0.125 | unchanged OK |
| real hand >=1200 raw | I frozen at 1229 within a tick; Honda fade x0.85->x0.30 (rec 0xE54FC) + 0.5 s request-drop ramp byte-identical -> **driver always wins** | fade bytes re-read, untouched OK |
| light hand 512–1229 word | I now winds (V298 froze at 512); bounded by A3 (<=4096 S low speed) -> <= rail 2461 T; override fade unchanged | BEHAVIOUR change by design; no new over-authority (BELIEF, bounded by clamp) |
| mis-deploy A16B firmware + old fork | old fork lists only {A16A} -> fingerprint miss -> no angle engage (safe) | fork values.py/interface read OK |
| mis-deploy new fork + A16A firmware | runs fork override-only changes on V298's loop (ratchet unchanged, safe); carFw attributes it | OK |

## 6. Fork 0x1AB parser — the counter/checksum worry is MOOT (EVIDENCE: _honda_common.dbc, d1_427_check read)
**DEFECT D1 (reasoning).** The fork DBC defines `BO_ 427 STEER_MOTOR_TORQUE: 3 EPS` with a SINGLE signal
`MOTOR_TORQUE : 1|10@0+ (1,0)` and **no CHECKSUM, no COUNTER**. So opendbc CANParser performs NO checksum/counter
validation on 0x1AB -> the spec/S3 section 4.2 claim "a counter fault >=5 still drops canValid" does **not apply to
this message**. d1_427_check's "checksum 100.000 % / counter 99.997 %" validates byte-2 nibbles that opendbc never
reads and that the trimmed DBC does not define — true-but-irrelevant. The REAL canValid gate is F6's nan
(no-alive-timeout) listing plus the VLDict-non-optional guard (list only under EPS_ANGLE_LOOP_FW, never read
unlisted). That gate is correct and fail-safe. **Fix:** in section 5 / F6 replace the counter-fault language with
the nan/VLDict gate; net safety is sound (safer than framed). MOTOR_TORQUE occupies byte0[1:0]+byte1; the fork's
own sign-extension s10 = +/-(raw & 0x1FF) and scale -8 are a VALUE claim (arithmetic lens, not this lens).

## 7. Open build-round prerequisites (DEFECT D2 — flagged by the spec, recorded here as blocking gates)
Before any image is written/flashed, these MUST pass (the spec defers them as "barred" this round):
1. golden-model _self_check_v299 mirror of the in-place cave (contract 94->95 symbols, _self_check+_demo
   hash 740f4bcd… unchanged — it prints nothing); byte-exact vs section 1.2.
2. decode the BUILT image in Ghidra; re-run H1 on the BUILT bytes (not the dry-run hex); 0 mismatches.
3. the CLAUDE.md adversarial pass on the built image (arithmetic, unit/scale, build-script audit incl. the
   CRC chain/bootloader section 4, interlocks/downstream) with "do not flash" reachable.
4. wire instrument for the drive: the rule-identity replay is zero-byte and already on the wire (no freeze bit
   spent) — adequate; no new state word needs a probe.

## 8. Verdict
**PASS_WITH_DEFECTS.** The byte spec is bit-exact (independent rebuild reproduces trailer, cave sha, image sha,
26 diff bytes). Decodes are correct; register discipline clean; GATE 1 holds (0 st.*, 0 new RAM, 0 new state
word); no relink error; CRC plan reproduces and no edit straddles a block. Fail-safe polarity correct in every
path incl. mis-deploy and hand override. Defects are documentation / verification-completeness (D1 0x1AB
reasoning, D2 deferred build gates, D3 name the chain/bootloader CRC checks), none a wrong byte or brick path.

Scripts (both <1 s, under refute/): rf_bytes.py, rf_build.py. Ghidra: read-only, DB not written.
