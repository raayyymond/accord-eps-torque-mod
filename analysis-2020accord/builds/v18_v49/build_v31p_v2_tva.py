"""builds/v18_v49/build_v31p_tva.py - V31P = V31 (UNCHANGED cals) + gentle-EME GATE-FIRING TELEMETRY
piggybacked into CAN 330 (0x14A) spare bits, via 4 decision-site trampolines + 1 builder hook.

PURPOSE (2026-07-13, operator-directed "Decision B")
=========================================================================================================
Log, live, WHICH gentle-EME gate actually fires -- not which threshold is merely crossed. Five suspect
gates are instrumented at their real firmware decision sites; each latches one bit into a scratch RAM
flag byte. The CAN-330 content builder reads the flags (plus two live state flags) and packs them into
330's genuinely-spare bits, which openpilot already logs raw. No OBD, no UDS, no CAN-TX ID, no bus
conflict -- rides into the raw `can` rlog during LKAS. openpilot's carState never reads these bits and no
DBC signal claims them (whole-image + fork audit, 2026-07-13).

CHANNEL: CAN 330 / 0x14A (DLC8, 100 Hz, car-facing, gateway-forwarded), builder FUN_00055a98,
buffer 0xFEDF6AE8. Two spare regions, both confirmed never-written by any instruction in the image AND
undefined in openpilot's DBC:
  byte4 bits 7:3 (mask 0xF8) = 5 gate-fire flags
  byte7 bits 7:6 (mask 0xC0) = 2 live state flags
The Honda 4-bit counter/checksum (FUN_00057b24 @0x55c18) is computed AFTER the pack hook, so it covers
the telemetry bits and openpilot validates them normally.

FLAG BYTE (scratch RAM): gp-0x1500 = 0xFEDF6B00 (u8; whole-image scan = 0 references; boot-zeroed).
  bit0 ENGAGE_SM_CUT  (decider FUN_00040d58, r12==2: voterMax>=cal 0xC6312=320 torque disengage)
  bit1 VOTER_AVG      (deliver-commit FUN_0003d04c, gp-0x6a5e>=cal 0xC62FE=320)
  bit2 GATE5_TORQUE   (deliver-commit, |gp-0x4f68|>=cal 0xC61EA=4096)
  bit3 ANGLE_DB       (FUN_0003c7fc angle deadband |angle-ref|>cal 0xC6354=4825, #1 suspect)
  bit4 RATE_GATE      (decider FUN_00040d58, r12==5: gp-0x6a60>=cal 0xC6310=1600)
Latch semantics: gate stubs OR-set a bit each firing; pack hook read-then-clears every 330 frame (~10 ms)
inside the builder's di section, so each frame's bits = "fired since last frame" (catches sub-sample cuts).

330 WIRE PAYLOAD (added by V31P; all other bits stock):
  byte4 bit3=ENGAGE_SM_CUT bit4=VOTER_AVG bit5=GATE5_TORQUE bit6=ANGLE_DB bit7=RATE_GATE
  byte7 bit6=TRUMP (live gp-0x67FE==2)   bit7=DELIVER_CUT (live gp-0x6809!=0)

THE CODE EDITS (all byte-verified against stock master.bin, 2026-07-13; disps computed in Python)
=========================================================================================================
4 code-cave trampoline stubs + 1 pack helper at cave 0xC4B34 (1212 B of 0xFF, [0xC4B34,0xC4FEF]), plus
5 equal-length (4-byte) in-place SITE swaps that redirect into the cave:

  site 0x40e64  st.b r12,-0x35b6[gp]  -> jr decider_stub   (decider shared epilogue; r12 = refusal code)
  site 0x3d098  jr 0x3d1ea            -> jr gate5_stub     (Gate-5 exclusive bail jr)
  site 0x3d0b4  jr 0x3d1e6            -> jr voteravg_stub  (voterAvg exclusive bail jr)
  site 0x3c93c  st.b r0,-0x6770[gp]   -> jr angle_stub     (angle-deadband cut convergence)
  site 0x55c0e  movea -0x1518,gp,r6   -> jarl pack_telemetry,lp  (330 builder, just before checksum)

TRANSPARENCY / SAFETY (why the control logic is unchanged)
=========================================================================================================
- Each stub RE-EXECUTES the displaced instruction (or, for the two bail jrs, jumps to the original target)
  so the original control effect is preserved bit-for-bit; the ONLY added effect is a flag OR-set.
- Stubs clobber only r10 (proven dead at every return: bail targets 0x3d1e6/0x3d1ea `mov ..,r10`,
  0x40e68/0x3c940 `mov ..,r10`) and set PSW harmlessly (no downstream reader). pack_telemetry clobbers
  only r6/r7/r8 (all reassigned by the 3 instructions after its return) and preserves r10.
- No pass-path is touched: when a gate does NOT fire, control never reaches these anchors.
- All V31 calibration edits RETAINED UNCHANGED -> the car drives EXACTLY as flashed V31.
- Edits lie in CRC blocks [0x13000,0xC4FFC) (cave+sites+PN) and [0xC6000,0xC6FFC) (cals), both recomputed.

SAFETY: STUDY ARTIFACT. UNFLASHED. No flash until the operator names file + bus (kit iron rule).
Validate by re-disassembling _v31p_plain_image.bin in Ghidra (cave stubs + 5 sites) before trusting.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
BIN_OUT      = plain_image_path("_v31p_v2_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V31 CALIBRATION EDITS (ALL RETAINED, UNCHANGED from V31/V31T) =====================
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  CORRIDOR_INT, "INT dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+4096 (x4)"),
    (0xC6750,  1024,  CORRIDOR_INT, "INT dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+4096 (x4)"),
    (0xC675A, -1024, -CORRIDOR_INT, "INT dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-4096 (x4)"),
    (0xC675C, -1024, -CORRIDOR_INT, "INT dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-4096 (x4)"),
]
CORRIDOR_GUARD = [
    (0xC6748,     2, "INT TABLE1 N (count)"),
    (0xC674A, -8192, "INT TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "INT TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "INT TABLE2 N (count)"),
    (0xC6756,  1024, "INT TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "INT TABLE2 X[1] velocity bkpt"),
]
FLOAT_CORRIDOR_PATCHES = [
    (0xC6598,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[0] tp+0x7598  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC659C,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[1] tp+0x759c  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC65AC, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[0] tp+0x75ac  corridor mirror  -1.0->-4.0 (x4)"),
    (0xC65B0, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[1] tp+0x75b0  corridor mirror  -1.0->-4.0 (x4)"),
]
FLOAT_CORRIDOR_GUARD_I = [
    (0xC658C, 2, "FLOAT dir1 N (count, int32)"),
    (0xC65A0, 2, "FLOAT dir2 N (count, int32)"),
]
FLOAT_CORRIDOR_GUARD_F = [
    (0xC6590, -8.0, "FLOAT dir1 X[0]"),
    (0xC6594, -1.0, "FLOAT dir1 X[1]"),
    (0xC65A4,  1.0, "FLOAT dir2 X[0]"),
    (0xC65A8,  8.0, "FLOAT dir2 X[1]"),
]
INT_BOOST_FLOOR_PATCHES = [
    (0xC6768,    0, BOOST_INT, "INT boost Y[0] tp+0x7768  rate<=700  0->4096   (FLOOR)"),
    (0xC676A, 1536, BOOST_INT, "INT boost Y[1] tp+0x776a             1536->4096 (FLOOR)"),
    (0xC676C, 2048, BOOST_INT, "INT boost Y[2] tp+0x776c             2048->4096 (FLOOR)"),
]
FLOAT_BOOST_FLOOR_PATCHES = [
    (0xC65C4, 0.0, BOOST_FLT, "FLOAT boost Y[0] tp+0x75c4  mirror  0.0->4.0 (FLOOR)"),
    (0xC65C8, 1.5, BOOST_FLT, "FLOAT boost Y[1] tp+0x75c8  mirror  1.5->4.0 (FLOOR)"),
    (0xC65CC, 2.0, BOOST_FLT, "FLOAT boost Y[2] tp+0x75cc  mirror  2.0->4.0 (FLOOR)"),
]
INT_BOOST_GUARD = [
    (0xC6760,    3, "INT boost N (count)"),
    (0xC6762,  700, "INT boost X[0] tp+0x7762"),
    (0xC6764,  800, "INT boost X[1] tp+0x7764"),
    (0xC6766, 1100, "INT boost X[2] tp+0x7766"),
]
FLOAT_BOOST_GUARD_I = [
    (0xC65B4, 3, "FLOAT boost N (count, int32)"),
]
FLOAT_BOOST_GUARD_F = [
    (0xC65B8,  700.0, "FLOAT boost X[0]"),
    (0xC65BC,  800.0, "FLOAT boost X[1]"),
    (0xC65C0, 1100.0, "FLOAT boost X[2]"),
]
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]
FLOAT_SPEEDGAIN_GUARD_F = [
    (0xC65F0,   2.0, "SPEED-gain float Y[0] -- stock"),
    (0xC65F8,   0.5, "SPEED-gain float Y[2] -- stock"),
]
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# --- NO-CODE-EDIT guard: stock soft-EME code sites MUST remain byte-identical ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
]

# ===================== V31P: gate-firing telemetry (cave stubs + site trampolines) =====================
CAVE_BASE = 0xC4B34            # start of the 1212-byte 0xFF cave [0xC4B34,0xC4FEF]
FLAG_DISP = -0x1500           # scratch flag byte gp-0x1500 (0xFEDF6B00), whole-image 0 refs


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def jr(target, pc):
    """V850 jr disp22 (4 bytes). Verified vs stock jr 0x3d098=80075201."""
    disp = (target - pc) & 0x3FFFFF
    return _le16(0x0780 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


def jarl_lp(target, pc):
    """V850 jarl disp22,lp (4 bytes). Verified vs stock jarl @0x55aa8=bcff9a9f."""
    disp = (target - pc) & 0x3FFFFF
    return _le16(0xFF80 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


def H(hexstr):
    return bytes.fromhex(hexstr)


# Fixed-instruction encodings, each derived from a byte-verified stock reference instruction.
# (mnemonic comments are the intended decode; Ghidra re-disassembly of the built image is the check.)
def assemble_cave(base):
    """Lay out the 4 stubs + pack helper at `base`. Returns (bytes, syms{name:addr})."""
    b = bytearray()
    syms = {}

    def here():
        return base + len(b)

    def emit(x):
        b.extend(x)

    # ---- decider_stub: r12=refusal code (preserve). bit0 if ==2, bit4 if ==5, bit5 if ==4 ----
    syms["decider"] = here()
    emit(H("6262"))                    # cmp 0x2,r12          (ref cmp 0x8,r28=68e2)
    emit(H("ba05"))                    # bne +6  (skip set1)  (Format III, cond=NZ)
    emit(H("c40700eb"))                # set1 0,-0x1500[gp]   ENGAGE_SM_CUT  (ref set1/clr1)
    emit(H("6562"))                    # cmp 0x5,r12
    emit(H("ba05"))                    # bne +6
    emit(H("c42700eb"))                # set1 4,-0x1500[gp]   RATE_GATE
    emit(H("6462"))                    # cmp 0x4,r12          (V2: angle-consensus, V34's gate)
    emit(H("ba05"))                    # bne +6
    emit(H("c42f00eb"))                # set1 5,-0x1500[gp]   ANGLE_CONSENSUS  (V2 NEW)
    emit(H("44674aca"))                # st.b r12,-0x35b6[gp] (re-exec displaced; exact stock bytes)
    emit(jr(0x40e68, here()))          # jr 0x40e68  (return past the anchor)
    # ---- gate5_stub ----
    syms["gate5"] = here()
    emit(H("c41700eb"))                # set1 2,-0x1500[gp]   GATE5_TORQUE
    emit(jr(0x3d1ea, here()))          # jr 0x3d1ea  (original Gate-5 bail target)
    # ---- voteravg_stub ----
    syms["voteravg"] = here()
    emit(H("c40f00eb"))                # set1 1,-0x1500[gp]   VOTER_AVG
    emit(jr(0x3d1e6, here()))          # jr 0x3d1e6  (original voterAvg bail target)
    # ---- angle_stub ----
    syms["angle"] = here()
    emit(H("c41f00eb"))                # set1 3,-0x1500[gp]   ANGLE_DB
    emit(H("44079098"))                # st.b r0,-0x6770[gp]  (re-exec displaced; exact stock bytes)
    emit(jr(0x3c940, here()))          # jr 0x3c940  (return past the anchor)
    # ---- hardcut_stub (V2 NEW): gp-0x676e==4 = all-3-phase disable in FUN_0003d4a2 @0x3de6c ----
    #      NOT the gentle EME (that keeps the motor enabled) -- this is the HARD-cut / full-shutdown
    #      discriminator: predicted 0 at gentle EMEs (CAN 427 OUTPUT_DISABLED never fired at any cut),
    #      lights up only on a real hard EME. Site is reached ONLY when gp-0x676e==4 (exclusive).
    syms["hardcut"] = here()
    emit(H("c43700eb"))                # set1 6,-0x1500[gp]   HARD_CUT
    emit(H("20363f00"))                # movea 0x3f,r0,r6    (re-exec displaced; exact stock bytes)
    emit(jr(0x3de70, here()))          # jr 0x3de70  (return past the anchor)
    # ---- pack_telemetry: called via jarl (lp=0x55c12) ----
    syms["pack"] = here()
    # V2: byte4[7:3] = (flagbyte & 0x1f) << 3 ; byte7[7:6] = (flagbyte & 0x60) << 1
    #     (all latched; NO live-reads -> no phase bug. clobbers r6/r7/r8 only, same as V31P.)
    emit(H("843f01eb"))                # ld.bu -0x1500[gp],r7   (r7 = flagbyte)
    emit(H("0740"))                    # mov r7,r8              (r8 = flagbyte copy for byte7)
    emit(H("c73e1f00"))                # andi 0x1f,r7,r7        (gates bit0-4)
    emit(H("c33a"))                    # shl 0x3,r7
    emit(H("8437edea"))                # ld.bu -0x1514[gp],r6   (byte4; ref exact 0x55ad4)
    emit(H("c6360700"))                # andi 0x7,r6,r6         (keep status bits2:0)
    emit(H("0731"))                    # or r7,r6
    emit(H("4437ecea"))                # st.b r6,-0x1514[gp]
    # byte7[7:6] = (flagbyte & 0x60) << 1  ->  bit5 ANGLE_CONSENSUS -> b6, bit6 HARD_CUT -> b7
    emit(H("c83e6000"))                # andi 0x60,r8,r7        (r7 = flagbyte & bits5,6)
    emit(H("c13a"))                    # shl 0x1,r7            (bit5->0x40, bit6->0x80)
    emit(H("a437efea"))                # ld.bu -0x1511[gp],r6   (byte7; ref exact 0x55c1c)
    emit(H("c6363f00"))                # andi 0x3f,r6,r6        (keep bits5:0 counter/checksum)
    emit(H("0731"))                    # or r7,r6
    emit(H("4437efea"))                # st.b r6,-0x1511[gp]    (ref exact 0x55c2a)
    emit(H("440700eb"))                # st.b r0,-0x1500[gp]    (clear flag byte = latch reset)
    emit(H("2436e8ea"))                # movea -0x1518,gp,r6    (re-exec displaced; exact stock bytes)
    emit(H("7f00"))                    # jmp [lp]               (ref exact 0x55c40)
    return bytes(b), syms


def site_patches(syms):
    """(file_offset, stock_bytes, new_bytes, note) for the 5 in-place trampoline swaps."""
    return [
        (0x40e64, H("44674aca"), jr(syms["decider"],  0x40e64),
         "decider epilogue st.b r12,-0x35b6[gp] -> jr decider_stub"),
        (0x3d098, H("80075201"), jr(syms["gate5"],    0x3d098),
         "Gate-5 bail jr 0x3d1ea -> jr gate5_stub"),
        (0x3d0b4, H("80073201"), jr(syms["voteravg"], 0x3d0b4),
         "voterAvg bail jr 0x3d1e6 -> jr voteravg_stub"),
        (0x3c93c, H("44079098"), jr(syms["angle"],    0x3c93c),
         "angle cut st.b r0,-0x6770[gp] -> jr angle_stub"),
        (0x3de6c, H("20363f00"), jr(syms["hardcut"],  0x3de6c),
         "FUN_0003d4a2 gp-0x676e==4 all-phase disable movea 0x3f,r0,r6 -> jr hardcut_stub"),
        (0x55c0e, H("2436e8ea"), jarl_lp(syms["pack"], 0x55c0e),
         "330 builder movea -0x1518,gp,r6 -> jarl pack_telemetry,lp"),
    ]


# ===================== patch/guard helpers (same as V31T) =====================
def patch_cal_u(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_corridor(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<h", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_float(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<f", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6.1f} -> {new:6.1f}   {note}")


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def patch_code(code, table):
    for addr, old, new, note in table:
        assert len(old) == len(new), f"code patch length mismatch @0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"CODE 0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}: {old.hex()} -> {new.hex()}   {note}")


def guard_s16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_int32(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<i", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_float(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA,A160"]))
        elif tag == b"!":
            new.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new.append((tag, [CAN_SIG_BYTE]))
        else:
            new.append((tag, list(vals)))
    return new


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def recompute_crc(code, start, crc_off):
    old = struct.unpack_from("<I", code, crc_off)[0]
    new = zlib.crc32(code[start:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", code, crc_off, new)
    print(f"  CRC [0x{start:X},0x{crc_off:X}) @0x{crc_off:X}: 0x{old:08X} -> 0x{new:08X}")


TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),
    (0x13000, 0xC4FFC),   # covers PN + all 5 trampoline sites + the cave stubs
]


def build(label, code_stock, headers, tag):
    print("=" * 88)
    print(f"{label}: V31 (unchanged cals) + gate-firing telemetry into CAN 330 spare bits")
    code = bytearray(code_stock)

    cave_bytes, syms = assemble_cave(CAVE_BASE)
    sites = site_patches(syms)
    print(f"  cave @0x{CAVE_BASE:X}: {len(cave_bytes)} bytes, ends 0x{CAVE_BASE + len(cave_bytes):X}")
    for name in ("decider", "gate5", "voteravg", "angle", "pack"):
        print(f"     {name:9s} @0x{syms[name]:05X}")

    # ---- pre-patch guards ----
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    for addr, b, note in NO_CODE_EDIT_SITES:
        assert bytes(code[addr:addr + len(b)]) == b, f"NO_CODE_EDIT guard @0x{addr:X} ({note})"
    # cave region we write must currently be all 0xFF
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == b"\xff" * len(cave_bytes), \
        "cave target is not 0xFF -- refusing to overwrite"

    # ---- V31 calibration patches (retained) ----
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)

    # ---- V31P telemetry: write cave stubs, then the 5 site trampolines ----
    print("  --- writing cave stubs ---")
    code[CAVE_BASE:CAVE_BASE + len(cave_bytes)] = cave_bytes
    print(f"  0x{CAVE_BASE:05X}: {len(cave_bytes)}B cave  {cave_bytes.hex()}")
    print("  --- site trampolines (equal-length in-place swaps) ---")
    patch_code(code, sites)

    # ---- post-patch guards ----
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    for addr, b, note in NO_CODE_EDIT_SITES:
        assert bytes(code[addr:addr + len(b)]) == b, f"NO_CODE_EDIT guard @0x{addr:X} ({note})"
    # cave tail (beyond stubs) still 0xFF up to 0xC4FF0
    assert bytes(code[CAVE_BASE + len(cave_bytes):0xC4FF0]) == b"\xff" * (0xC4FF0 - CAVE_BASE - len(cave_bytes)), \
        "cave tail must remain 0xFF"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # ---- readback asserts (decode the emitted .rwd from scratch) ----
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == 1782, "GAIN lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B4 - START)[0] == 1024, "CLAMP b4 lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B2 - START)[0] == 1024, "CLAMP b2 lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for addr, _, new, _ in CORRIDOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int corridor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float corridor @0x{addr:X}"
    for addr, _, new, _ in INT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int boost floor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float boost floor @0x{addr:X}"
    # V31P telemetry present in the decoded .rwd
    assert bytes(ecu_plain[CAVE_BASE - START:CAVE_BASE - START + len(cave_bytes)]) == cave_bytes, \
        "cave stubs lost in decoded rwd"
    for addr, _old, new, note in sites:
        got = bytes(ecu_plain[addr - START:addr - START + len(new)])
        assert got == new, f"site trampoline lost @0x{addr:X} ({note}): got {got.hex()}"
    for addr, b, note in NO_CODE_EDIT_SITES:
        got = bytes(ecu_plain[addr - START:addr - START + len(b)])
        assert got == b, f"unexpected soft-EME code edit @0x{addr:X} ({note})"
    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    assert ecu_plain.count(pn_old) == 0 and ecu_plain.count(pn_new) == 2, "PN lost"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, bb in runs:
        print(f"     0x{a:05X}-0x{bb:05X} ({bb - a + 1}B)")

    if not matches or fails:
        print(f"  *** {label} self-check FAILED -- not writing ***\n")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    with open(BIN_OUT, "wb") as f:
        f.write(full_image(ecu_plain))
    print(f"  WROTE {os.path.relpath(out, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)} (1MB plain image for Ghidra verify)\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print("V31P = V31 cals + gentle-EME GATE-FIRING telemetry into CAN 330 (0x14A) spare bits")
    print("       flag byte gp-0x1500; 4 decision-site trampolines + 1 builder hook -> cave 0xC4B34\n")
    build("V31P-V2", code, headers, tag="gateflags-v2-angleconsensus-hardcut-caveC4B34")
    return 0


if __name__ == "__main__":
    sys.exit(main())
