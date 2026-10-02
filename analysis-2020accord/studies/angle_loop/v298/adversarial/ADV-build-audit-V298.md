# ADV build-audit V298 — FAIL criteria (written BEFORE any check ran, 2026-10-01)

Adversary role: BUILD-SCRIPT AUDIT on the built image V298 (sha256 177abf04…). Job: make it FAIL.

A **DO_NOT_FLASH** verdict is returned if ANY of these hold:
- F1. My own from-scratch rebuild (no imports from the builder's script) from V295 (5c044d65…) does not reproduce
  sha256 177abf04… and the difference is not my own error.
- F2. Any byte in [0x13000,0x100000) differing V295→V298 is not explained by a named edit (stray byte), or any
  claimed edit is absent / has a different value in the image than the builder reports.
- F3. Any CRC trailer fails, or the bootloader walk fails, on the built image.
- F4. The .rwd does not decode back bit-for-bit to the plain image (every byte of 0x13000..0x100000).
- F5. The .rwd '/' header does not list the image's own version string (A16A) — the car could not be flashed
  back/forward — or the image's version string is not what the header claims.
- F6. More than one flashable .rwd for V298 (ambiguous which to flash), or a duplicate under another name.
- F7. A revert artifact's payload differs from its original, or an original .rwd / plain image changed hash.
- F8. The FLIGHT cave still carries a stale reference: table pointer ≠ the table's actual address, or any
  jr/jarl/branch target in the cave lands anywhere other than its intended instruction (re-derived from bytes).
- F9. The cave overwrites non-0xFF base bytes, crosses a CRC trailer / block boundary, or any table/code
  reference reads outside what was written.
- F10. Any in-place code edit decodes to something other than the claimed instruction, or a hook's return
  path does not land on a valid instruction boundary of the original stream.

A **PASS_WITH_DEFECTS** is returned for: a misreported assertion census, vacuous/tautological checks presented
as substantive, a golden-model contract miss, stale docstrings, collateral-only defects that do not change the
flashed bytes.

(Results follow below once the checks have run.)

---

# RESULTS (BUILD-SCRIPT AUDIT, independent of build_v298_tva.py) — 2026-10-01

Script: `adv_build_audit_v298.py` (this dir). Image sha256 `177abf04…` on disk == builder claim.
All disassembly via GhidraMCP dry-run on the raw import `V298_DISASM_ONLY_NOT_AN_ARTIFACT.bin`
(bytes confirmed == on-disk image at every site read). Python LE byte scans as the second method.

## VERDICT: PASS_WITH_DEFECTS — flashable from the build-audit surface. One census defect, collateral only.

No condition on the build-script-audit surface reaches DO_NOT_FLASH. (DO_NOT_FLASH remained
structurally reachable — the F1..F10 fail criteria above were each tested and NONE fired.)

## F1 INDEPENDENT REBUILD — PASS
My own apply (V295 + the edit set) + my own zlib.crc32 trailer recompute reproduces V298
BYTE-FOR-BYTE; my sha256 = `177abf04…`. The builder's sha256 is reproducible from V295 by a
script that shares no code with the builder's.

## F2 FULL DIFF V295→V298 — PASS (0 stray)
325 differing bytes in [0x13000,0x100000) = 313 named-edit bytes + 12 CRC-trailer bytes, in 36 runs.
Every differing byte is attributable to a named edit or a recomputed CRC trailer. 0 stray.

## F3 CRC — PASS
Full chain 50/50, bootloader walk 49/49 on the built image. The 3 edited blocks' trailers,
old (V295) → new (V298), independently recomputed:
  [0x13000,0xC4FFC)  0x1349B154 → 0x6B7CD8F3 ✓ (recomputed == stored)
  [0xC6000,0xC6FFC)  0x8D982BD9 → 0x4F36CA24 ✓
  [0xE5000,0xE5FFC)  0x511EEFE8 → 0x50D68D31 ✓
All match the builder's claimed values exactly.

## F4 .rwd DECODE-BACK — PASS
V298 .rwd on-disk sha256 == claim. Decodes (x31, V9B keys) to the V298 image byte-for-byte.

## F5 HEADER / VERSION STRING — PASS
'/' header = ['39990-TVA-A110','39990-TVA,A160','39990-TVA,A16A']. Image F181 string = '39990-TVA,A16A'.
The car currently on A160 will be accepted by the part gate (A160 listed), and it becomes A16A.

## F6 SINGLE FLASHABLE — PASS
Exactly one flashable V298 .rwd (the two REVERT files are clearly named and are revert artifacts).

## F7 REVERT ARTIFACTS — PASS
Originals UNTOUCHED: V295 .rwd f42a06bd… and V294 .rwd a2b418f0… both match their pre-existing hashes.
Revert copies sha256 == builder claims (rev295 fb6969fc…, rev294 e64f035d…). Each revert payload (encs)
== the original's (headers-only change); each revert '/' now lists A16A.

## F8 CAVE RELINK — PASS (the KNOWN DEFECT is genuinely fixed; two refuters, re-derived from the IMAGE)
Ghidra dry-run decode of the flight cave at 0xC4C00 (260 B), corroborated by an independent Python
reference decoder and by the studies two-pass assembler re-deriving the same 260 bytes:
  - G-table pointer: `mov 0xc4cda, r9` @0xC4C1C → table at 0xC4CDA (the REAL table). The defective
    on-disk c3b_cave (9a10cdc4) left it at 0xC4CC4. FIXED.
  - Freeze return `jr 0x00029d7e` @0xC4CC4 and CAM return `jr 0x00029d7e` @0xC4CD4. The defective cave
    landed 0x29D80. FIXED.
  - Op-skip `bnh 0xc4c18` @0xC4C12 / `jr 0x0002a164` @0xC4C14 → Honda's own A2/B2 epilogue (confirmed
    at 0x2A164: `mov 0x0,r24 … mov 0x7fffffff,r16` — no new torque path, zeroes I, sets the sentinel).
  - Camera gate `cmp r0,r25` @0xC4C5A / `be 0xc4cc8` @0xC4C5C → CAM handler (`mov 0x0,r16; mov 0x0,r26;
    ld.w -0x6dd0,gp,r6; sar 0x6,r6; subr r0,r6; jr 0x29d7e`).
  - Table walked from 0xC4CDA == GB-P 7 rows exactly.

## F9 CAVE EXTENT — PASS
Cave [0xC4C00,0xC4D04) is all-0xFF in V295 (free), fits below the builder's 0xC4FF0 probe and well
inside the main CRC block trailer 0xC4FFC; tail [0xC4D04,0xC4FF0) remains 0xFF in V298.

## F10 IN-PLACE EDITS — PASS (all 8 decode as claimed, via Ghidra)
  0x28F4C  ld.h -0x6a00,gp,r7            (E1  x:=theta)
  0x28FA4  add r9,r26                    (E2  r26 = s_old+s_new; clean 2-byte boundary)
  0x29A50  cmovne r0,r27,r8              (B2  r8=(req==1)?bVar2:0)
  0x29A56  be 0x00029a5c                 (A2  reuses Honda's own `jr 0x2a164` at 0x29A5C)
  0x29D6A  ld.h -0x69ae,gp,r16           (E4  sp:=demand)
  0x29D76  jarl 0x000c4c00,r6            (HOOK; return 0x29D7A; displaced shl2/sub re-executed at cave head)
  0x29EE0  mov r26,r8 ; nop              (OPH  D operand = r26)
  0x1310D  30→41                         (V1  A160→A16A)
Normal return 0x29D7A (`mov r16,r6; sar 0x5,r6`) and freeze/CAM return 0x29D7E (`cmp r10,r6`) are both
clean instruction boundaries; freeze/CAM supply their own r6 and skip the r16→r6 recompute by design.

## ASSERTION CENSUS — the one DEFECT (PASS_WITH_DEFECTS, collateral only)
Builder self-reports 70 assertions: S=48, C=13, V=3, T=6. I reproduced that census by running the script.
The 3 V (base 50/50, base 49/49, the `or True` superset note) and 6 T (readbacks of just-written bytes)
are honestly labeled. BUT **27 of the 48 "Substantive" assertions read ONLY base values** (8 code base==,
7 cal base==, 5 Kp base, 4 Kd base, cave-is-0xFF, 2 fade-record reads) and are therefore **entailed by the
V295 base-sha256 check** — the exact class the kit's own adversarial doctrine (V274) says to count as
vacuous/entailed. Strict re-census: V should be ~30, genuinely-independent S ~21.
- Severity: LOW / collateral. It does NOT change the flashed bytes, and the builder correctly states the
  REAL falsifiers are external to the build's own assertions (H1 0/40000 + the Ghidra decode) — which this
  audit independently reproduced (my rebuild, the Ghidra relink decode, CRC recompute). The build is
  genuinely correct; only the S/V split is optimistic.

## ITEMS OUTSIDE THIS SURFACE (carried to the arith/unit/interlock adversaries + orchestrator, not my findings)
- CAM handler returns r6 = −(I>>6), i.e. "inert" only insofar as I is held near 0; a non-zero accumulated
  I still produces output on a camera frame. Behavioral — interlock adversary to adjudicate vs the "lane
  goes inert" claim. (Structure verified; magnitude/decay not scored here.)
- The camera discriminator (stock camera's 0xE4 byte-2 field 3:2 = 0 → r25=0), POL=−1, τ_o≥1 s fork
  prereq, and fwVersion acceptance are BELIEF / fork-config prerequisites per the builder — not build bytes.
- A fully independent re-run of H1 on the FLIGHT bytes (behavioral equivalence to cave_stage) is the
  arithmetic adversary's deep domain; here the relink is corroborated structurally (Ghidra) and by the
  studies two-pass assembler re-deriving the 260 bytes byte-for-byte (the build's [C] check passed).
