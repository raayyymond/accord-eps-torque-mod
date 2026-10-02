# -*- coding: utf-8 -*-
r"""V298 -- THE FIRST FIRMWARE ANGLE LOOP, PRIMARY + CAMERA INTERLOCK (C3-rev2-P + rev2-A's R1-P-cam gate).

BASE   V295 (_v295_V295-V294BASE-ACCELTRIM.B1050-...TORQUE.TAP_plain_image.bin, sha256 5c044d65...40452ed) -- FLOWN.
DESIGN docs/specs/design/DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md (merged primary = C3B-P byte-for-byte) +
       DESIGN-ANGLE-LOOP-C3-rev2-A-2026-10-01.md (the camera-interlock variant R1-P-cam: gate the lane on
       gp-0x6803 == 2 so the stock camera's 0xE4 cannot be read as an angle setpoint).

V298 = the MERGED PRIMARY (A3 angle-referenced integral bound + opposing-hand freeze sgn 300 + GB-P table +
Ki 40 + the rate-invalid op-skip jr 0x2A164) WITH the camera gate `cmp r0,r25 ; be CAM` applied on top (r25 =
(gp-0x6803 == 2), set by Honda at 0x29A82, read-only).  When the fork sends byte-2 bits 3:2 = 2 the lane runs; a
stock-camera frame (field 0 -> r25 = 0) branches to the CAM handler and the lane goes inert (E' := 0, op := 0, the
I decays I x 0.125/tick), so the camera's command can never be taken as a setpoint.

=== THE KNOWN DEFECT THIS BUILD FIXES (EVIDENCE, two refuters) ===========================================
The design's PRIMARY flight cave hex (c3b_cave_C3B-P.hex, sha 9a10cdc4ec75, 240 B) was produced by
rb_build.add_opskip, which byte-SPLICED a +2-byte op-skip WITHOUT relinking: the G-table base pointer
(mov imm32,r9 -> 0xC4CC4 instead of 0xC4CC6) and the freeze-return jr (lands 0x29D80 instead of 0x29D7E) were
left STALE.  Here the op-skip is injected at the LISTING level and the whole cave is assembled by the two-pass
linker, so EVERY absolute/relative reference (table ptr, FRZ/CAM jr, be/bnh displacements, op-skip jr) is
recomputed from the final layout.  The relinked merged-primary flight cave is sha 83fabd88fa88 (240 B); V298's
flight cave (merged primary + the camera gate) is sha ef1861e10421 (260 B).

=== 0. EVERY BYTE V298 CHANGES vs V295 (the full cell table; read from the BUILT image at [DIFF]/[DELTA]) ==
  IN-PLACE CODE (8 sites, main CRC block [0x13000,0xC4FFC)):
    id    addr      V295 bytes      -> V298 bytes      instruction / loop term
    E1    0x28F4C   24 3f aa 95     -> 24 3f 00 96     ld.h -0x6a56->-0x6a00[gp],r7   x := theta (0.1 deg)
    E2    0x28FA4   89 d1           -> c9 d1           subr->add r9,r26               r26 = 8*theta[n]+8*theta[n-1]
    B2    0x29A50   e2 47 00 00     -> e0 df 34 43     setfe->cmovne r0,r27,r8        r8 = (request==1)?bVar2:0
    A2    0x29A56   da 05           -> b2 05           bne 0x29A60 -> be 0x29A5C      PID runs iff ramp!=0 AND r8!=0
    E4    0x29D6A   08 80 ed 80     -> 24 87 52 96     mov/mulh -> ld.h -0x69ae[gp],r16   sp := gp-0x69ae (demand)
    HOOK  0x29D76   c2 82 ba 81     -> 89 37 8a ae     shl2/sub -> jarl 0xC4C00,r6    the cave hook (r6=0x29D7A)
    OPH   0x29EE0   10 40 bb 41     -> 1a 40 00 00     mov r16/sub -> mov r26,r8 ; nop  D operand = r26 (fresh op)
    V1    0x1310D   30              -> 41              F181 '39990-TVA,A160' -> '...,A16A'   the fork interlock
  THE CAVE (0xC4C00, 260 B flight = 218 code + 42 table; the free cave region was all 0xFF; main CRC block):
    = merged primary (A3+sgn300+GB-P+Ki-arith) + op-skip (jr 0x2A164) + camera gate (cmp r0,r25 ; be CAM ; CAM).
  CALIBRATION (0xC6000 CRC block): a 0xC63E8 1011->0 | b 0xC63EA 1050->8192 | C 0xC62E6 1024->65535 |
    DB 0xC62E4 4->0 | Ki 0xC63E6 0->40 | ICL 0xC61BA 10240->8192 | DCL 0xC61B6 0->10240
  RECORD BLOCK (0xE5000 CRC block): Kp Y 0xE5384 960->112 (x5 knots) | Kd Y 0xE5126 0->48 (x4 knots) |
    FADE NEUTRALIZE fadeB2 record 0xE54FC X/Y (24 B) := fadeB record 0xE564C X/Y  (camera-arm cost removed)

=== 0b. THE CAMERA ARM (gp-0x6803 == 2): WHICH CAL TABLES BECOME LIVE, KEPT vs RE-WRITTEN ================
Requiring gp-0x6803 == 2 for the lane to run means the fork sends 2 every frame, which ALSO selects Honda's
direction-2 arms (trace 2026-09-30 sec.5):
  * engage-SM ramp: ramp-in 0xC63FC = 328 (0.10 s, vs dir-0 0xC63F8 = 33 / 0.99 s); ramp-out 0xC63FA = 66
    (0.50 s, vs dir-0 0xC63F6 = 16 / 2.05 s).  KEPT at the image's stock values (NOT re-written) -- the faster
    ramp-in is a benefit (less engage droop); under A2 the ramp-out only paces an already-decaying output.
  * post-PID torque fade: arm fadeB2 (record 0xE54FC) vs dir-0 fadeB (0xE564C).  dir-2 is ~1.8-2.1x hand
    authority mid-range.  RE-WRITTEN: 0xE54FC's X/Y := 0xE564C's X/Y, so the override feel is V295's (cost removed).
  * post-PID grab factor: arm fadeA2 (record 0xE55A4) vs dir-0 fadeA (0xE56F4).  ALREADY IDENTICAL in the image
    (both X 0,3,6,8,10,20 / Y 255,255,255,255,255,205).  KEPT (no re-write needed).
  * setpoint-stage taper: dir-2 cliff arms 0xCBA74/0xCBA04.  BYPASSED by E4 (the setpoint edit removes the
    setpoint-stage taper), so inert.  KEPT stock.

=== 0c. THE VERSION STRING AND THE REVERT PATH ===========================================================
V1 sets F181 to '39990-TVA,A16A'.  The V298 .rwd '/' header lists BOTH '39990-TVA,A160' (the car runs V295 now,
so the part gate accepts it) AND '39990-TVA,A16A' (what it becomes), keeping '39990-TVA-A110'.  After V298 is
flashed the car reports A16A, so the V295 and V294 revert .rwd files are re-headered to ALSO list A16A and
written as separate '...-REHEADERED-FOR-REVERT-FROM-V298...' files; the ORIGINAL V295/V294 .rwd stay untouched
and are re-hashed before and after.  (FLASH IS GATED on the operator naming the file and the bus -- this script
writes files only.)
"""
import contextlib
import hashlib
import io
import os
import struct
import sys
import zlib
from pathlib import Path

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))
# the angle-loop studies assembler (for the C-check that re-derives the cave from source)
_ST = _d / "analysis-2020accord" / "studies" / "angle_loop"
for _q in (_ST / "panel2" / "E2-integral-most-margin", _ST / "panel" / "D-structure", _ST / "c3" / "rev2B"):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import build_vfourframe_tva as FF                                                    # noqa: E402
import build_v53_tva as V53                                                          # noqa: E402
import eps_lkas_chain_model as M                                                     # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table        # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path, RWD_DIR, ANALYSIS_ROOT   # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                              # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END, CODE_END = 0x13000, 0x100000, 0xC0000
WRITE_MODE = os.environ.get("ACCORD_V298_WRITE", "").strip().lower()
MAX_PATH = 259

BASE_NAME = ("_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
             "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
BASE_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"
V295_RWD_NAME = ("39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT"
                 ".960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd")
V294_RWD_NAME = ("39990-TVA,A160-V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960"
                 ".ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd")
V295_RWD_SHA = "f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87"
V294_RWD_SHA = "a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a"

CAVE_BASE = 0xC4C00
CAVE_FREE_END = 0xC4FF0                         # the main-block CRC node begins at 0xC4FF0 (probe)
SKIP_TGT = 0x2A164
FRZ_RET = 0x29D7E
HOOK_RET = 0x29D7A

# the relinked caves (frozen; re-derived from e2_asm at [CAVE-C] if the studies modules import)
FLIGHT_SHA = "ef1861e10421b0645b27e9ff8605a93b245f16fe2a350c65f0a067084497303a"
SCORE_SHA = "9dffd41f463fed423da6a10b06a6275a29234e097132752cdd3f761192f82ab5"
POL_A3S_CAM = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096, sgn=300, cam=True)

# in-place code edits: (addr, V295 old, V298 new)
CODE_EDITS = [
    (0x28F4C, "24 3f aa 95", "24 3f 00 96", "E1  x := theta"),
    (0x28FA4, "89 d1", "c9 d1", "E2  r26 = s_old + s_new (add)"),
    (0x29A50, "e2 47 00 00", "e0 df 34 43", "B2  r8 = (req==1)?bVar2:0"),
    (0x29A56, "da 05", "b2 05", "A2  be 0x29A5C"),
    (0x29D6A, "08 80 ed 80", "24 87 52 96", "E4  sp := gp-0x69ae"),
    (0x29D76, "c2 82 ba 81", "89 37 8a ae", "HOOK  jarl 0xC4C00,r6"),
    (0x29EE0, "10 40 bb 41", "1a 40 00 00", "OPH  mov r26,r8 ; nop"),
    (0x1310D, "30", "41", "V1  A160 -> A16A"),
]
# lane cals in the 0xC6000 block: (addr, V295, V298, signed?, name)
CAL_EDITS = [
    (0xC63E8, 1011, 0, True, "fb pole a"),
    (0xC63EA, 1050, 8192, False, "fb gain b"),
    (0xC62E6, 1024, 65535, False, "fb clamp C"),
    (0xC62E4, 4, 0, False, "I deadband DB"),
    (0xC63E6, 0, 40, False, "Ki"),
    (0xC61BA, 10240, 8192, False, "I clamp ICL"),
    (0xC61B6, 0, 10240, False, "D clamp DCL"),
]
KP_Y, KP_N, KP_V295, KP_V298 = 0xE5384, 5, 960, 112
KD_Y, KD_N, KD_V295, KD_V298 = 0xE5126, 4, 0, 48
FADE_DST, FADE_SRC = 0xE54FC, 0xE564C            # 6803==2 arm record <- 6803!=2 arm record (24 payload bytes)
FADE_N = 6
VSTR_OLD, VSTR_NEW = b"39990-TVA,A160", b"39990-TVA,A16A"
VSTR_STOCK_ALT = b"39990-TVA-A110"

TAG = "V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A"
IMG_NAME = f"_v298_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
REVERT_V295_RWD = f"39990-TVA,A160-V295-REHEADERED-FOR-REVERT-FROM-V298-A16A-0x{START:X}-0x{END:X}.rwd"
REVERT_V294_RWD = f"39990-TVA,A160-V294-REHEADERED-FOR-REVERT-FROM-V298-A16A-0x{START:X}-0x{END:X}.rwd"

OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self, quiet=False, collect=False):
        self.n = self.ok = 0
        self.census = {"S": 0, "C": 0, "V": 0, "T": 0}
        self.quiet, self.collect, self.failures = quiet, collect, []

    def check(self, cond, msg, kind="S"):
        assert kind in self.census
        self.n += 1
        self.census[kind] += 1
        cond = bool(cond)
        self.ok += cond
        if not self.quiet:
            print(f"      {OK if cond else BAD} [{kind}] {msg}")
        if not cond:
            self.failures.append((kind, msg))
            if not self.collect:
                raise SystemExit(f"ASSERTION FAILED: {msg}")

    def say(self, s=""):
        if not self.quiet:
            print(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


# ---------------------------------------------------------------------------------------------------------
#  THE CAVE: re-derive from the studies assembler (two-pass relink), freeze by sha
# ---------------------------------------------------------------------------------------------------------
def reassemble_caves():
    """Re-derive the flight and score caves from e2_asm + rb_table with the op-skip injected at the LISTING
    level (two-pass relink).  Returns (flight_bytes, score_bytes) or (None, None) if the studies modules
    cannot be imported here."""
    try:
        import e2_asm as EA
        import rb_table as T
    except Exception:
        return None, None

    def inject_opskip(entries):
        out, i, n = [], 0, len(entries)
        while i < n:
            lab, ins, com = entries[i]
            if ins == ("cmovh", 0, 26, 26):
                out.append((lab, ("bnh", "CONT"), "rate valid: continue  [op-skip]"))
                out.append((None, ("jr", SKIP_TGT), "rate INVALID: jr 0x2A164 (Honda A2/B2 epilogue)  [F3]"))
                out.append(("CONT", entries[i + 1][1], entries[i + 1][2]))
                i += 2
                continue
            out.append((lab, ins, com))
            i += 1
        return out

    def asm(entries):
        labels, pc = {}, EA.CAVE
        for lab, ins, _ in entries:
            if lab:
                labels[lab] = pc
            pc += EA.size(ins)
        out, pc = bytearray(), EA.CAVE
        for lab, ins, com in entries:
            out += b"".join(struct.pack("<H", h) for h in EA.enc(ins, pc, labels))
            pc += EA.size(ins)
        return bytes(out)

    ent = EA.listing(POL_A3S_CAM, [tuple(r) for r in T.GB_P])
    return asm(inject_opskip(ent)), asm(ent)


# embedded, frozen (hex of the relinked flight / score caves; verified against FLIGHT_SHA / SCORE_SHA below)
FLIGHT_HEX = ("c282ba8124d742951a46c832206e9065ed41b305b6075055e447a3952906da4c0c00e96f0100ed41cb05e9470300b515"
              "e96f0700ed41c305094e0600a5fde96f0100ad41296f0400ed472002ac42e96f0300cd41e8872002a882e0c9e235"
              "e44799b0206e0002ed41db2d206e2c01ed41d305244fa0b03049d625244f0096e049ae058049e447a395206e400b"
              "ed41bb05c44aa505c64a094ee204206e6605ed41eb05206e0010ed49ed4f364b246f3192aa6ae081ae058069e969"
              "ce05ce6e0080ca0d0032b607ba50008200d224373192a6328031b607aa506600ca029a0411043307b90588e70009"
              "f8020ff8930a30022206c00f2c04460836188c080000ffff8c080000")
SCORE_HEX = ("c282ba8124d742951a46c832206e9065ed41e0d736d3e447a3952906d84c0c00e96f0100ed41cb05e9470300b515"
             "e96f0700ed41c305094e0600a5fde96f0100ad41296f0400ed472002ac42e96f0300cd41e8872002a882e0c9e235"
             "e44799b0206e0002ed41db2d206e2c01ed41d305244fa0b03049d625244f0096e049ae058049e447a395206e400b"
             "ed41bb05c44aa505c64a094ee204206e6605ed41eb05206e0010ed49ed4f364b246f3192aa6ae081ae058069e969"
             "ce05ce6e0080ca0d0032b607bc50008200d224373192a6328031b607ac506600ca029a0411043307b90588e70009"
             "f8020ff8930a30022206c00f2c04460836188c080000ffff8c080000")
FLIGHT = bytes.fromhex(FLIGHT_HEX)
SCORE = bytes.fromhex(SCORE_HEX)


# ---------------------------------------------------------------------------------------------------------
#  A self-contained reference decoder for the handful of control-flow forms the cave leans on (independent
#  of the studies interpreters), used to PROVE every absolute/relative reference in the embedded flight cave.
# ---------------------------------------------------------------------------------------------------------
def decode_refs(code, base=CAVE_BASE):
    """Return dicts of the resolved references: mov-imm32 (table ptr), Format-V jr/jarl targets, Bcond
    targets, and the camera cmp/be.  Enough to assert the relink is correct."""
    movimm32, jrs, bconds = [], [], []
    for off in range(0, len(code) - 2, 2):
        hw1 = code[off] | (code[off + 1] << 8)
        op6 = (hw1 >> 5) & 0x3F
        reg2, reg1 = hw1 >> 11, hw1 & 0x1F
        if (hw1 & 0xFFE0) == 0x0620 and off + 6 <= len(code):            # mov imm32,reg1
            movimm32.append((off, reg1, u32(code, off + 2)))
        if (hw1 >> 7) & 0xF == 0xB:                                       # Bcond (Format III)
            cond = hw1 & 0xF
            d = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            bconds.append((off, cond, base + off + d))
        if op6 in (0x3C, 0x3D) and off + 4 <= len(code):                 # Format V jr/jarl (hw2 even)
            hw2 = code[off + 2] | (code[off + 3] << 8)
            if not (hw2 & 1):
                disp = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
                disp = disp - (1 << 22) if disp & (1 << 21) else disp
                jrs.append((off, reg2, (base + off + disp) & 0xFFFFFFFF))
    return dict(movimm32=movimm32, jrs=jrs, bconds=bconds)


# ---------------------------------------------------------------------------------------------------------
def build(quiet=False, do_rwd=True, base_bytes=None, run=None):
    R = run if run is not None else Run(quiet)
    ck, say = R.check, R.say
    say("=" * 118)
    say("  V298 -- the first firmware ANGLE LOOP, PRIMARY + CAMERA INTERLOCK (C3-rev2-P + R1-P-cam gate)")
    say("=" * 118)

    # [1] BASE = V295
    say("\n  [1] BASE = V295")
    base = bytes(base_bytes if base_bytes is not None else Path(plain_image_path(BASE_NAME)).read_bytes())
    ck(hashlib.sha256(base).hexdigest() == BASE_SHA, f"V295 base sha256 == {BASE_SHA[:16]}...", "S")
    ck(qwalk(walk_all_blocks, base) == 0, "base CRC chain 50/50  [entailed]", "V")
    ck(qwalk(walk, base) == 0, "base BOOTLOADER CRC replay 49/49  [entailed]", "V")

    # [2] THE CAVE -- re-derive from source (C), freeze by sha (C), prove every reference (S)
    say("\n  [2] THE CAVE -- relinked (two-pass), sha-frozen, every reference decoded")
    ck(hashlib.sha256(FLIGHT).hexdigest() == FLIGHT_SHA, f"flight cave sha256 == {FLIGHT_SHA[:12]}... ({len(FLIGHT)} B)", "C")
    ck(hashlib.sha256(SCORE).hexdigest() == SCORE_SHA, f"score cave sha256 == {SCORE_SHA[:12]}... ({len(SCORE)} B)", "C")
    rf, rs = reassemble_caves()
    if rf is not None:
        ck(rf == FLIGHT and rs == SCORE, "the studies assembler re-derives the embedded flight/score caves byte-for-byte", "C")
    else:
        say("      (studies assembler not importable here -- the sha freeze above stands; Ghidra H5 decodes the built bytes)")
    refs = decode_refs(FLIGHT)
    tptr = [v for _, r1, v in refs["movimm32"] if r1 == 9]
    ck(tptr == [CAVE_BASE + 0xDA], f"op-skip RELINK: the mov imm32,r9 table pointer = {hex(tptr[0]) if tptr else None} "
       f"(= cave+0xDA, the REAL table; the defective cave left it at 0xC4CC4)", "S")
    jr_tgts = sorted({t for _, r2, t in refs["jrs"] if r2 == 0})
    ck(SKIP_TGT in jr_tgts, f"op-skip jr target = {hex(SKIP_TGT)} (Honda's A2/B2 skip epilogue)", "S")
    ck(all(t in (SKIP_TGT, FRZ_RET) for t in jr_tgts) and FRZ_RET in jr_tgts,
       f"every jr lands on {{0x2A164 (skip), 0x29D7E (freeze/CAM return)}}: {[hex(t) for t in jr_tgts]} "
       f"(the defective cave's freeze jr landed 0x29D80)", "S")
    # the table walked from the pointer must be GB-P
    t = tptr[0] - CAVE_BASE
    rows = []
    while t + 6 <= len(FLIGHT):
        X, G, S = struct.unpack_from("<HHh", FLIGHT, t)
        rows.append((X, G, S))
        if X == 0xFFFF:
            break
        t += 6
    ck(rows == [(714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570),
                (4032, 1068, 2118), (6198, 2188, 0), (65535, 2188, 0)],
       f"the table reached through the relinked pointer is GB-P, 7 rows: {rows}", "S")
    # the camera gate: cmp r0,r25 (e0 c9) then be CAM
    cam_at = FLIGHT.find(bytes.fromhex("e0c9"))
    ck(cam_at >= 0, "camera gate `cmp r0,r25` (e0 c9) present in the cave", "S")
    be = [(o, c, tg) for o, c, tg in refs["bconds"] if o == cam_at + 2 and c == 0x2]
    ck(len(be) == 1, f"camera gate `be CAM` at cave+{hex(cam_at+2)} -> {hex(be[0][2]) if be else None} (inert handler)", "S")
    ck(CAVE_BASE + len(FLIGHT) <= CAVE_FREE_END, f"the cave [0x{CAVE_BASE:X}, 0x{CAVE_BASE+len(FLIGHT):X}) fits the free "
       f"region below 0x{CAVE_FREE_END:X}", "S")

    # [3] APPLY -- code edits, cave, cals, fade record
    say("\n  [3] APPLY")
    code = bytearray(base)
    attributed = set()

    def put(a, nb, label):
        nonlocal code
        code[a:a + len(nb)] = nb
        for i in range(len(nb)):
            if code[a + i] != base[a + i]:
                attributed.add(a + i)

    for a, old, new, nm in CODE_EDITS:
        ob, nb = bytes.fromhex(old.replace(" ", "")), bytes.fromhex(new.replace(" ", ""))
        ck(bytes(base[a:a + len(ob)]) == ob, f"code 0x{a:05X} base == {old} ({nm})", "S")
        put(a, nb, nm)
    ck(all(x == 0xFF for x in base[CAVE_BASE:CAVE_BASE + len(FLIGHT)]), "cave region is all 0xFF in V295 (free)", "S")
    put(CAVE_BASE, FLIGHT, "cave")
    for a, old, new, signed, nm in CAL_EDITS:
        ck(u16(base, a) == old, f"cal 0x{a:05X} base == {old} ({nm})", "S")
        put(a, struct.pack("<h" if signed else "<H", new), nm)
    for i in range(KP_N):
        ck(u16(base, KP_Y + 2 * i) == KP_V295, f"Kp Y[{i}] 0x{KP_Y + 2*i:05X} base == {KP_V295}", "S")
        put(KP_Y + 2 * i, struct.pack("<H", KP_V298), "Kp")
    for i in range(KD_N):
        ck(u16(base, KD_Y + 2 * i) == KD_V295, f"Kd Y[{i}] 0x{KD_Y + 2*i:05X} base == {KD_V295}", "S")
        put(KD_Y + 2 * i, struct.pack("<H", KD_V298), "Kd")
    # fade record neutralization: 0xE54FC X/Y (24 B at +2) := 0xE564C X/Y
    ck(u16(base, FADE_DST) == FADE_N and u16(base, FADE_SRC) == FADE_N, "both fade records have count 6 (header kept)", "S")
    src_xy = bytes(base[FADE_SRC + 2:FADE_SRC + 2 + 4 * FADE_N])
    ck(bytes(base[FADE_DST + 2:FADE_DST + 2 + 4 * FADE_N]) != src_xy, "fade arms differ in V295 (the 1.8-2.1x cost is live)", "S")
    put(FADE_DST + 2, src_xy, "fadeB2 := fadeB")
    ck(bytes(code[FADE_DST + 2:FADE_DST + 2 + 4 * FADE_N]) == src_xy and bytes(code[FADE_DST:FADE_DST + 2]) == bytes(base[FADE_DST:FADE_DST + 2]),
       "fadeB2 record X/Y now == fadeB record X/Y (24 bytes); count byte unchanged", "S")

    # [4] CRC -- owning blocks located by walking the chain, trailers recomputed
    say("\n  [4] CRC -- owning blocks, trailers recomputed")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in attributed})
    ck(set(blocks) == {(0x13000, 0xC4FFC), (0xC6000, 0xC6FFC), (0xE5000, 0xE5FFC)},
       f"attributed bytes own exactly 3 CRC blocks: {[(hex(s), hex(e)) for s, e in blocks]}", "S")
    for b0, b1 in blocks:
        oldc, newc = u32(code, b1), zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        say(f"      block [0x{b0:06X},0x{b1:06X})  trailer 0x{oldc:08X} -> 0x{newc:08X}")
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50 (the full linked list)", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (NRC 0x72 predictor)", "S")

    # [5] FULL BYTE DIFF vs V295 -- every differing offset attributed
    say("\n  [5] FULL BYTE DIFF vs V295 over [0x13000, 0x100000)")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    trailer_bytes = {b1 + i for (b0, b1) in blocks for i in range(4)}
    expected = set(attributed) | trailer_bytes
    stray = [hex(a) for a in diff if a not in expected]
    ck(not stray, f"every differing byte is an attributed edit or a recomputed CRC trailer ({len(stray)} stray)", "S")
    ck(set(diff) == expected, f"the diff == the {len(attributed)} edit bytes + {len(trailer_bytes)} trailer bytes "
       f"= {len(expected)} (got {len(diff)})", "S")
    n_code = sum(1 for a in attributed if a < CODE_END)
    n_cave = sum(1 for a in attributed if CAVE_BASE <= a < CAVE_BASE + len(FLIGHT))
    n_cal = sum(1 for a in attributed if a >= CODE_END and not (CAVE_BASE <= a < CAVE_BASE + len(FLIGHT)))
    say(f"      edits: in-place code {n_code} + cave {n_cave} + cal/record {n_cal} = {len(attributed)} bytes; "
        f"+ {len(trailer_bytes)} trailer bytes")

    # [6] READBACK through decoded instructions on the BUILT image
    say("\n  [6] READBACK on the BUILT image")
    ck(bytes(code[CAVE_BASE:CAVE_BASE + len(FLIGHT)]) == FLIGHT, "the cave on the built image == the relinked flight bytes", "T")
    ck(u16(code, 0xC63EA) == 8192 and struct.unpack_from("<h", code, 0xC63E8)[0] == 0 and u16(code, 0xC62E6) == 65535,
       "fb filter cals on the built image: a=0, b=8192, C=65535 (pure 2-sample sum, r26 = 16*theta)", "T")
    ck(u16(code, 0xC63E6) == 40 and u16(code, 0xC61BA) == 8192 and u16(code, 0xC61B6) == 10240,
       "Ki=40, ICL=8192, DCL=10240 on the built image", "T")
    ck(all(u16(code, KP_Y + 2 * i) == 112 for i in range(KP_N)) and all(u16(code, KD_Y + 2 * i) == 48 for i in range(KD_N)),
       "Kp Y = 112 x5, Kd Y = 48 x4 on the built image", "T")
    ck(bytes(code[0x1310D:0x1310D + 1]) == b"\x41" and bytes(code[0x13100:0x1310E]) == VSTR_NEW,
       f"F181 string on the built image == {VSTR_NEW.decode()}", "T")
    ck(bytes(code[FADE_DST + 2:FADE_DST + 2 + 4 * FADE_N]) == bytes(code[FADE_SRC + 2:FADE_SRC + 2 + 4 * FADE_N]),
       "fadeB2 == fadeB on the built image (camera-arm fade cost neutralized)", "T")

    # [7] CUMULATIVE NON-STOCK DELTA -- read from STOCK and the BUILT image
    say("\n  [7] CUMULATIVE NON-STOCK DELTA (stock dump vs the BUILT image)")
    stock = Path(stock_fw_path("code.bin")).read_bytes()
    ck(hashlib.sha256(stock).hexdigest() == STOCK_SHA, "stock dump sha256 matches", "C")
    d298 = {a for a in range(START, END) if code[a] != stock[a]}
    d295 = {a for a in range(START, END) if base[a] != stock[a]}
    say(f"      bytes differing from STOCK: V298 {len(d298)}  V295 {len(d295)}  (V298 adds the cave + the angle-loop "
        f"edits + the camera fade neutralize over V295's torque-mode delta)")
    ck(d295 - d298 == set() or True, "V298's non-stock set is a superset-with-replacements of V295's (reported, not asserted)", "V")

    # [8] DELIVERED SURFACE of the angle loop, from the BUILT image's own table (Kp 112 * G)
    say("\n  [8] DELIVERED ANGLE-LOOP GAIN SURFACE (Kp_eff = Kp * G / 256, from the built table)")
    kp = u16(code, KP_Y)
    for v in (3.1, 8.0, 10.0, 11.75, 15.0, 22.0, 26.9):
        vc = int(round(v * 3.6 * 64))
        # integer G walk of GB-P
        g = rows[0][1] if vc <= rows[0][0] else None
        if g is None:
            i = 0
            while rows[i + 1][0] < vc:
                i += 1
            X, G, S = rows[i]
            g = G + ((vc - X) * S >> 12)
        say(f"      v={v:5.1f} m/s  G={g:5d}  Kp_eff={kp * g / 256:7.1f}  (deg-error gain)")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [9] .rwd ENCODE (headers: '/' += A16A, '!' parallel) + READBACK + independent re-splice")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches (container template)", "C")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        headers = header_add_a16a(info["headers"], R)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(headers, info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V298 output")
        back = bytearray(base)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code), "the .rwd decoded back is BYTE-IDENTICAL to the built image", "S")
        v38 = bytearray(base)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        pr = parse_x31(rwd)
        got = {tag: [v.decode("latin1") for v in vals] for tag, vals in [(t.decode("latin1"), vv) for t, vv in pr["headers"]]}
        ck(got.get("/") == [VSTR_STOCK_ALT.decode(), VSTR_OLD.decode(), VSTR_NEW.decode()],
           f"V298 .rwd '/' header lists {got.get('/')}", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()

    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")
    say("\n" + "=" * 118)
    say(f"  PREDICTED image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  PREDICTED .rwd  SHA256 {rwd_sha}")
    say(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['C']} constant-checks, "
        f"{R.census['V']} vacuous/entailed, {R.census['T']} tautological")
    say("=" * 118)
    return dict(code=bytes(code), base=base, rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, tag=TAG,
                img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, diff=diff)


def header_add_a16a(headers, R):
    """Return a copy of the x31 headers with '39990-TVA,A16A' appended to the '/' (supported parts) and a
    parallel entry appended to '!' (SA secret, x31 ignores it but keep the lists parallel)."""
    out = []
    for tag, vals in headers:
        vals = list(vals)
        if tag == b"/":
            R.check(VSTR_OLD in vals, "source .rwd '/' already lists A160 (the car's current string)", "C")
            if VSTR_NEW not in vals:
                vals.append(VSTR_NEW)
        if tag == b"!" and len(vals) >= 1:
            vals.append(vals[-1])            # same SA secret for the new entry
        out.append((tag, vals))
    return out


def write_revert(name_in, sha_in, name_out, R):
    """Re-header a revert .rwd to list A16A; write it as a new file; the original stays untouched and is
    re-hashed before and after."""
    ck = R.check
    src = Path(RWD_DIR, name_in)
    b0 = src.read_bytes()
    ck(hashlib.sha256(b0).hexdigest() == sha_in, f"{name_in[:40]}... sha256 unchanged BEFORE re-header", "C")
    info = parse_x31(b0)
    headers = header_add_a16a(info["headers"], R)
    rwd = encode_x31(headers, info["blocks"], info["encs"])
    # the re-encoded revert must decode to the SAME payload as the original (headers-only change)
    ck(parse_x31(rwd)["encs"] == info["encs"], f"{name_out[:40]}... payload == the original's (headers-only change)", "S")
    pr = parse_x31(rwd)
    got = [vv.decode("latin1") for t, vals in pr["headers"] if t == b"/" for vv in vals]
    ck(VSTR_NEW.decode() in got, f"{name_out[:40]}... '/' now lists {got}", "S")
    b1 = src.read_bytes()
    ck(hashlib.sha256(b1).hexdigest() == sha_in, f"{name_in[:40]}... sha256 unchanged AFTER re-header (original untouched)", "C")
    return rwd, hashlib.sha256(rwd).hexdigest()


def qwalk(fn, img):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bad = fn(bytearray(img))
    return bad


def v298_artifacts():
    img = [f for f in Path(ANALYSIS_ROOT).glob("_v298*") if not f.name.startswith("SUPERSEDED")]
    rwd = [f for f in Path(RWD_DIR).glob("*V298*") if not f.name.startswith("SUPERSEDED")]
    return img, rwd


def main():
    base = Path(plain_image_path(BASE_NAME)).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise SystemExit("V295 base sha256 mismatch -- refusing to go further")
    r = build()
    # revert re-headered copies (built in-memory; written only in WRITE mode)
    print("\n  [10] REVERT re-headered copies (V295, V294) -- originals untouched")
    rr = r["run"]
    rev295, rev295_sha = write_revert(V295_RWD_NAME, V295_RWD_SHA, REVERT_V295_RWD, rr)
    rev294, rev294_sha = write_revert(V294_RWD_NAME, V294_RWD_SHA, REVERT_V294_RWD, rr)
    print(f"      revert-V295 .rwd sha256 {rev295_sha}")
    print(f"      revert-V294 .rwd sha256 {rev294_sha}")
    print(f"\n  PREDICTION, before any write:  image {r['img_sha']}\n                                 rwd   {r['rwd_sha']}")
    print(f"  census: {rr.census}  ({rr.ok}/{rr.n})")
    if WRITE_MODE == "rwd":
        print("\n  [11] WRITE -- guarded, re-hashed + decoded after")
        pre_i, pre_r = v298_artifacts()
        if pre_i or pre_r:
            raise SystemExit(f"WRITE GUARD: a V298 artifact already exists ({[f.name for f in pre_i]}, {[f.name for f in pre_r]})")
        out_img, out_rwd = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
        rv295, rv294 = Path(RWD_DIR, REVERT_V295_RWD), Path(RWD_DIR, REVERT_V294_RWD)
        with open(out_img, "xb") as fh:
            fh.write(r["code"])
        with open(out_rwd, "xb") as fh:
            fh.write(r["rwd"])
        with open(rv295, "xb") as fh:
            fh.write(rev295)
        with open(rv294, "xb") as fh:
            fh.write(rev294)
        assert hashlib.sha256(out_img.read_bytes()).hexdigest() == r["img_sha"]
        assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"]
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        back = bytearray(r["base"])
        back[START:END] = bytes(parse_x31(out_rwd.read_bytes())["encs"][0]).translate(dec_tbl)
        assert bytes(back) == r["code"], "on-disk rwd does not decode to the on-disk image"
        # originals still intact
        assert hashlib.sha256(Path(RWD_DIR, V295_RWD_NAME).read_bytes()).hexdigest() == V295_RWD_SHA
        assert hashlib.sha256(Path(RWD_DIR, V294_RWD_NAME).read_bytes()).hexdigest() == V294_RWD_SHA
        print(f"      [PASS] image + rwd + 2 revert copies written; originals untouched")
        print(f"      {out_img}\n      {out_rwd}\n      {rv295}\n      {rv294}")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V298_WRITE=rwd to emit the files.")
    return r


if __name__ == "__main__":
    main()
