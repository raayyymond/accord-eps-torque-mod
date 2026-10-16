# -*- coding: utf-8 -*-
r"""V300 rev 2 -- THE RELEASE: stock + the firmware ANGLE LOOP, nothing else.  BUILT FROM STOCK (not V299-minus-reverts).

REV 2 (2026-10-15): the GATE 2 re-score on the stock-plant terms (studies/release/GATE2-RESCORE-STOCK-PLANT-TERMS.md) FAILS
the revert of the DampAxis lane gp-0x6b26 (GM 20 -> 5.2 dB and |T| +5.4 dB at 3 m/s with stock values), so its 13 bytes
stay at V299's values: Y rows 0xD7A5C (6 B) + 0xD7A6C (6 B) and the producer's EMA alpha2 0xC40DC (1 B).  Rev 1 (749 B,
sha a6a24117...) is deleted; exactly one V300 rwd on disk.

Spec: docs/review/RELEASE-CENSUS-V299-vs-STOCK-2026-10-15.md (the census of every V299-vs-stock byte, classed
A structure / B tuning / C telemetry / D legacy / E CRC).  Orchestrator decisions (2026-10-15), binding:

  KEEP  (copied byte-for-byte FROM THE V299 IMAGE at build time, never from constants here)
    A1  F181 id string: 0x13109 '-' -> ','   (the letter at 0x1310D is set BELOW to the release letter 'C')
    A2  in-place lane edits: E1 0x28F4E (x := theta gp-0x6a00) . B2 0x29A50 + A2 0x29A56 (PID-run guard:
        ramp != 0 and request == 1) . E4 0x29D6A (sp := gp-0x69ae) . HOOK 0x29D76 (jarl 0xC4C00) . OPH 0x29EE0
        (D operand := the fresh motor-frame rate)
    A3  the angle-loop cave 0xC4C00..0xC4D03 (260 B): G(v) table, E' = (E*G)>>8, Ki integrator, A3 angle-
        referenced integral bound (asymmetric, two-level cap), 1229 hand freeze, op-skip, camera gate gp-0x6803 == 2
    A4  fb-lag re-purposed as r26 = 16*theta: a 0xC63E8 = 0, b 0xC63EA = 8192, C 0xC62E6 = 65535, DB 0xC62E4 = 0
    A5  dir-2 hand-fade record 0xE54FC (26 B) := the dir-0 record (the camera-interlock arm's fade neutralised)
    A6  authority chain: 0x2A1F0 displacement -> private forward gain 0xC6CD0 = 5346 (x6); clamps 0xC61B2/B4 = 3072
    A7  EME soft-limit ladder: int16 0xC674E/50/5A/5C = +-5120, 0xC6768/6A/6C = 5120 and their f32 mirrors = +-5.0
    B1  Ki 0xC63E6 = 40 . B2 ICL 0xC61BA = 8192 . B3/B4 Kp/Kd (ALL 28 records, see TUNING below)
    D4  low-speed lockout 0xC62EA = 0 (stock 320 = 5 km/h; the goal says "every speed")
    D6  STEER_STATUS debounce 0xC61C0..C5 = 0xFFFF x3, 0xC64B4..B7 = 0xFF x4, DTC-0x49 gate 0xC64B8 = 255
        (the x6 authority trips Honda's gentle-EME debounce otherwise -- on-car, V36/V37)
    D8k DampAxis lane Y rows 0xD7A5C / 0xD7A6C (-29490,-17202,-16000; stock -9830,-5734,-1966) -- GATE 2 (rev 2)
    D5k DampAxis producer EMA alpha2 0xC40DC = 14 (stock 22) -- GATE 2 (rev 2)
  NEW vs V299
    B3x/B4x  Kp 112 and Kd 48 written on ALL 28 Kp/Kd records (V299 carried V294's 960 / V293's 0 on the 27
        records the live selector (7) does not index; the release puts every slot on the same surface)
    F181 letter 'C' at 0x1310D  ->  39990-TVA,A16C
  REMOVED (stock bytes, because the build starts from stock)
    C1 0x55C0E hook . C2 0xC4B34 cave (164 B) . C3 0x55DF2..0x55E11 CAN-427 tap        -- ALL telemetry
    D1 0x454FE . D2 biquad arm 0x35A08/12/18 + 0xC649B . D3 r24 gate 0x3AA96 + arm 0xC6446 . D5 Coulomb relay
    0xC40BC/D2 . D7 0xC64DE . D8 the base-assist damper banks 0xCE000..0xD9FFF minus D8k (980 B) . D9 the x6 assist map
    (28 records) . D10 LIM ceilings . D11 0x14120

Assertions (census in the stdout footer: S substantive / C constant / V vacuous / T tautological):
  (1) release XOR stock == exactly KEEP + B3x/B4x + F181 + trailers, run by run
  (2) release XOR V299  == exactly REMOVED + B3x/B4x + F181 + trailers, run by run
  (3) the cave 0xC4C00..0xC4D03 sha-identical to V299's when TUNING == V299's (else: the diff is exactly the
      tuning immediates)
  (4) every byte outside the touched runs == stock
  (5) CRC chain 50/50 + the bootloader walk 49/49 on the built image
  (6) rwd payload decodes back to the image byte-for-byte; cipher validated non-circularly on V38
  (7) pages 0xCE..0xD9 byte-identical to stock INCLUDING their trailers
  (8) Kp/Kd read back on all 28 records through the pointer tables (0xCB994 / 0xCB7D4) with the record layout
      derived from the record header (N knots -> Y at +2+2N), not assumed

FLASH IS GATED on the operator naming the file and the bus -- this script writes files only, guarded by
ACCORD_V300_WRITE=rwd.  Nothing here sends anything.
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

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import build_vfourframe_tva as FF                                                     # noqa: E402
import build_v53_tva as V53                                                           # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table         # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path, RWD_DIR                   # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V300_WRITE", "").strip().lower()
MAX_PATH = 259

# =====================================================================================================================
#  TUNING -- the ONE block task 1b edits.  Every value below is written INTO the image; the defaults are V299's and
#  are asserted equal to the V299 image at build time (so a silent drift of this block from V299 fails loudly).
#  Set V299_IDENTICAL = False after changing any value; assertion (3) then checks the cave diff is only immediates.
# =====================================================================================================================
TUNING = dict(
    KP=112,              # Kp, flat, all 5 knots of all 28 records (deg-error gain on E' = 16*G*(theta_sp-theta)>>8)
    KD=48,               # Kd, flat, all 4 knots of all 28 records (on the fresh motor-frame rate, OPH)
    KI=40,               # 0xC63E6
    ICL=8192,            # 0xC61BA  I clamp (icl = (ICL<<10)>>3)
    FREEZE=1229,         # cave movea @0xC4C62 -- hard integral freeze when raw |hand torque| > FREEZE (1200 wire)
    VCAP=1382,           # cave movea @0xC4C8C -- v-word at/below which CAPLO applies (~6 m/s)
    VNOCAP=2880,         # cave movea @0xC4C7E -- v-word above which the bound is shl 6 and uncapped (~12.5 m/s)
    CAPLO=4096,          # cave movea @0xC4C94
    CAPHI=6144,          # cave movea @0xC4C9A
    B_LO=1250,           # cave addi @0xC4C88 -- toward-centre integral allowance (S units), shl-4 path
    B_HI=1250,           # cave addi @0xC4CA8 -- same, shl-6 path
    # G(v) table at 0xC4CDA: (X = v-word knot, G = gain /256, S = slope) x 7, last X = 0xFFFF sentinel
    G_TABLE=[(714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570),
             (4032, 1068, 2118), (6198, 2188, 0), (65535, 2188, 0)],
)
V299_IDENTICAL = True   # flip to False when TUNING departs from V299's values
# cave immediates: name -> (address of the imm16 inside the cave)
CAVE_IMM = dict(FREEZE=0xC4C64, VNOCAP=0xC4C80, VCAP=0xC4C8E, CAPLO=0xC4C96, CAPHI=0xC4C9C, B_LO=0xC4C8A, B_HI=0xC4CAA)
G_TABLE_ADDR = 0xC4CDA
# =====================================================================================================================

STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"
V299_NAME = ("_v299_V299-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3-2LVL.4096.6144.V2880.FRZ1229.OPH300.OPSKIP.KP112.KD48"
             "-FB.SUM.SP69AE.A16B_plain_image.bin")
V299_SHA = "30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08"
V299_CAVE_SHA = "e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608"

CAVE_BASE, CAVE_LEN = 0xC4C00, 260
RELEASE_LETTER = b"C"
VSTR_A110, VSTR_A160 = b"39990-TVA-A110", b"39990-TVA,A160"
VSTR_A16A, VSTR_A16B = b"39990-TVA,A16A", b"39990-TVA,A16B"
VSTR_REL = b"39990-TVA,A16" + RELEASE_LETTER

TAG = (f"V300-REV2-RELEASE-ANGLELOOP.FROMSTOCK-KP{TUNING['KP']}.KD{TUNING['KD']}.KI{TUNING['KI']}.ICL{TUNING['ICL']}"
       f"-FRZ{TUNING['FREEZE']}.CAP{TUNING['CAPLO']}.{TUNING['CAPHI']}-NOTELEMETRY.NOMAP.STOCKASSIST.DAMPAXIS.V299.A16"
       + RELEASE_LETTER.decode())
IMG_NAME = f"_v300_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"

OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self, quiet=False, collect=False):
        self.n = self.ok = 0
        self.census = {"S": 0, "C": 0, "V": 0, "T": 0}
        self.quiet, self.collect, self.failures = quiet, collect, []

    def check(self, cond, msg, kind="S"):
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


def qwalk(fn, img):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(bytearray(img))


def rng(a, n):
    return set(range(a, a + n))


# ---------------------------------------------------------------------------------------------------------------------
#  THE CENSUS ROWS -- the address sets, re-derived from the STOCK image's pointer tables (mirrors the census script)
# ---------------------------------------------------------------------------------------------------------------------
def census_rows(stock):
    def ptrs(tab, n):
        return [u32(stock, tab + 4 * k) for k in range(n)]

    def rec_y(p):                                   # record: u16 N, X[N], Y[N]  -> the Y span
        n = u16(stock, p)
        return p + 2 + 2 * n, n

    KP, KD = ptrs(0xCB994, 28), ptrs(0xCB7D4, 28)
    MAP, LIM = ptrs(0xC9A88, 28), ptrs(0xCB844, 10)
    rows = {}
    rows["A1"] = {0x13109, 0x1310D}
    rows["A2"] = rng(0x28F4E, 2) | rng(0x29A50, 4) | {0x29A56} | rng(0x29D6A, 4) | rng(0x29D76, 4) | rng(0x29EE0, 4)
    rows["A3"] = rng(CAVE_BASE, CAVE_LEN)
    rows["A4"] = rng(0xC63E8, 4) | rng(0xC62E6, 2) | rng(0xC62E4, 2)
    rows["A5"] = rng(0xE54FC, 26)
    rows["A6"] = rng(0x2A1F0, 2) | rng(0xC6CD0, 2) | rng(0xC61B2, 4)
    rows["A7"] = (rng(0xC674E, 4) | rng(0xC675A, 4) | rng(0xC6768, 6) | rng(0xC6598, 8) | rng(0xC65AC, 8)
                  | rng(0xC65C4, 12))
    rows["B1"] = rng(0xC63E6, 2)
    rows["B2"] = rng(0xC61BA, 2)
    kp_y = [rec_y(p) for p in KP]
    kd_y = [rec_y(p) for p in KD]
    rows["B3"] = rng(kp_y[7][0], 2 * kp_y[7][1])
    rows["B4"] = rng(kd_y[7][0], 2 * kd_y[7][1])
    rows["B3x"] = set().union(*[rng(y, 2 * n) for i, (y, n) in enumerate(kp_y) if i != 7])
    rows["B4x"] = set().union(*[rng(y, 2 * n) for i, (y, n) in enumerate(kd_y) if i != 7])
    rows["C1"] = rng(0x55C0E, 4)
    rows["C2"] = rng(0xC4B34, 164)
    rows["C3"] = rng(0x55DF2, 32)
    rows["D1"] = {0x454FE}
    rows["D2"] = {0x35A08, 0x35A09, 0x35A12, 0x35A18, 0xC649B}
    rows["D3"] = {0x3AA96} | rng(0xC6446, 2)
    rows["D4"] = rng(0xC62EA, 2)
    rows["D5"] = rng(0xC40BC, 2) | rng(0xC40D2, 2)
    rows["D5k"] = {0xC40DC}                                                   # rev 2: DampAxis alpha2, KEPT
    rows["D6"] = rng(0xC61C0, 6) | rng(0xC64B4, 5)
    rows["D7"] = {0xC64DE}
    rows["D8k"] = rng(0xD7A5C, 6) | rng(0xD7A6C, 6)                          # rev 2: DampAxis Y rows, KEPT
    rows["D8"] = {a for a in range(0xCE000, 0xDA000) if (a & 0xFFF) < 0xFFC} - rows["D8k"]
    rows["D9"] = set().union(*[rng(p + 22, 20) for p in MAP])
    rows["D10"] = set().union(*[rng(p + 20, 20) for p in LIM])
    rows["D11"] = {0x14120}
    return rows, (KP, KD, kp_y, kd_y)


KEEP_ROWS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "B1", "B2", "B3", "B4", "D4", "D6", "D8k", "D5k")
REMOVED_ROWS = ("C1", "C2", "C3", "D1", "D2", "D3", "D5", "D7", "D8", "D9", "D10", "D11")


def build(quiet=False, do_rwd=True, run=None):
    R = run if run is not None else Run(quiet)
    ck, say = R.check, R.say
    say("=" * 118)
    say("  V300 -- THE RELEASE: stock + the angle loop (A structure, B tuning on all 28 slots, D4, D6); no telemetry,")
    say("         no x6 map, Honda's base assist.  Built FROM STOCK; V299 is the byte SOURCE for the kept runs.")
    say("=" * 118)

    # [1] sources
    say("\n  [1] SOURCES")
    stock = Path(stock_fw_path()).read_bytes()
    v299 = Path(plain_image_path(V299_NAME)).read_bytes()
    ck(hashlib.sha256(stock).hexdigest() == STOCK_SHA, f"stock sha256 == {STOCK_SHA[:16]}...", "S")
    ck(hashlib.sha256(v299).hexdigest() == V299_SHA, f"V299 sha256 == {V299_SHA[:16]}...", "S")
    ck(qwalk(walk_all_blocks, stock) == 0, "stock CRC chain 50/50  [entailed]", "V")
    ck(hashlib.sha256(v299[CAVE_BASE:CAVE_BASE + CAVE_LEN]).hexdigest() == V299_CAVE_SHA,
       f"V299 cave sha256 == {V299_CAVE_SHA[:12]}...", "S")

    rows, (KP, KD, kp_y, kd_y) = census_rows(stock)
    diff_v299 = {a for a in range(START, END) if stock[a] != v299[a]}
    trailers = {a for a in diff_v299 if (a & 0xFFF) >= 0xFFC}
    owned = set().union(*[rows[k] for k in rows])
    ck(len(diff_v299) == 2471 and not (diff_v299 - owned - trailers),
       f"census re-derived: V299 vs stock = {len(diff_v299)} bytes, every one owned by a row or a trailer", "S")

    # [2] the tuning defaults == the V299 image (the TUNING block has not drifted silently)
    say("\n  [2] TUNING block vs the V299 image")
    t299 = dict(KP=u16(v299, kp_y[7][0]), KD=u16(v299, kd_y[7][0]), KI=u16(v299, 0xC63E6), ICL=u16(v299, 0xC61BA),
                **{k: u16(v299, a) for k, a in CAVE_IMM.items()})
    g299, t = [], G_TABLE_ADDR
    while True:
        X, G, S = struct.unpack_from("<HHh", v299, t)
        g299.append((X, G, S))
        if X == 0xFFFF:
            break
        t += 6
    t299["G_TABLE"] = g299
    same = all(TUNING[k] == t299[k] for k in TUNING)
    ck(same == V299_IDENTICAL, f"TUNING == V299's image values: {same} (V299_IDENTICAL flag {V299_IDENTICAL})", "S")
    ck(len(TUNING["G_TABLE"]) == 7 and TUNING["G_TABLE"][-1][0] == 0xFFFF, "G table: 7 rows, 0xFFFF sentinel", "S")
    ck(all(0 <= TUNING[k] <= 0xFFFF for k in CAVE_IMM) and 0 <= TUNING["KP"] <= 0xFFFF and 0 <= TUNING["KD"] <= 0xFFFF,
       "every tuning immediate fits its u16 field", "S")

    # [3] APPLY -- copy the kept runs from V299 onto stock; then Kp/Kd all 28; then the tuning; then the letter
    say("\n  [3] APPLY")
    code = bytearray(stock)
    keep = set().union(*[rows[k] for k in KEEP_ROWS])
    for a in sorted(keep):
        code[a] = v299[a]
    for (y, n) in kp_y:
        for i in range(n):
            struct.pack_into("<H", code, y + 2 * i, TUNING["KP"])
    for (y, n) in kd_y:
        for i in range(n):
            struct.pack_into("<H", code, y + 2 * i, TUNING["KD"])
    struct.pack_into("<H", code, 0xC63E6, TUNING["KI"])
    struct.pack_into("<H", code, 0xC61BA, TUNING["ICL"])
    for k, a in CAVE_IMM.items():
        struct.pack_into("<H", code, a, TUNING[k])
    for i, (X, G, S) in enumerate(TUNING["G_TABLE"]):
        struct.pack_into("<HHh", code, G_TABLE_ADDR + 6 * i, X, G, S)
    code[0x1310D:0x1310E] = RELEASE_LETTER
    ck(bytes(code[0x13100:0x1310E]) == VSTR_REL, f"F181 == {VSTR_REL.decode()}", "T")

    # [4] CRC -- every owning block of a touched byte, trailer recomputed; pages 0xCE..0xD9 untouched
    say("\n  [4] CRC")
    touched = {a for a in range(START, END) if code[a] != stock[a]}
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    say("      owning blocks: " + ", ".join(f"[0x{s:06X},0x{e:06X})" for s, e in blocks))
    ck(all(not (0xCE000 <= s < 0xDA000) or s == 0xD7000 for s, e in blocks),
       "the only owning block in the base-assist pages 0xCE..0xD9 is 0xD7 (the kept DampAxis Y rows)", "S")
    new_trailers = set()
    for s, e in blocks:
        struct.pack_into("<I", code, e, zlib.crc32(bytes(code[s:e])) & 0xFFFFFFFF)
        new_trailers |= rng(e, 4)
    ck([s for s, e in blocks] == [0x13000, 0xC6000, 0xD7000, 0xE4000, 0xE5000, 0xE6000, 0xE7000, 0xE8000],
       f"{len(blocks)} owning blocks == main + 0xC6 + 0xD7 + 0xE4..0xE8 (rev 2 adds 0xD7)", "S")
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (NRC 0x72 predictor)", "S")

    # [5] assertion (1): release XOR stock == KEEP + B3x/B4x + F181 letter + trailers, run by run
    say("\n  [5] release XOR stock")
    d_stock = {a for a in range(START, END) if code[a] != stock[a]}
    exp_stock = (keep | rows["B3x"] | rows["B4x"] | {0x1310D}) & {a for a in range(START, END)}
    # kept bytes that happen to equal stock (e.g. two 0xFF in the cave, X knots of Kp/Kd records) are not diffs:
    exp_stock = {a for a in exp_stock if code[a] != stock[a]} | {a for a in new_trailers if code[a] != stock[a]}
    stray = sorted(d_stock - exp_stock)
    missing = sorted(exp_stock - d_stock)
    ck(not stray and not missing, f"release vs stock: {len(d_stock)} bytes, 0 stray, 0 missing "
       f"(stray {[hex(a) for a in stray[:6]]}, missing {[hex(a) for a in missing[:6]]})", "S")
    for k in KEEP_ROWS + ("B3x", "B4x"):
        n = sum(1 for a in rows[k] if code[a] != stock[a])
        say(f"        {k:4s} {n:5d} differing bytes of {len(rows[k])}")
    ck(all(code[a] == stock[a] for a in range(START, END) if a not in exp_stock),
       "assertion (4): every byte outside the touched runs == stock", "S")

    # [6] assertion (2): release XOR V299 == REMOVED + B3x/B4x + letter + trailers (+ tuning if it moved)
    say("\n  [6] release XOR V299")
    d_v299 = {a for a in range(START, END) if code[a] != v299[a]}
    removed = set().union(*[rows[k] for k in REMOVED_ROWS])
    exp_v299 = {a for a in removed | rows["B3x"] | rows["B4x"] | {0x1310D} if code[a] != v299[a]}
    exp_v299 |= {a for a in (new_trailers | trailers) if code[a] != v299[a]}
    if not V299_IDENTICAL:
        exp_v299 |= {a for a in rows["A3"] | rows["B1"] | rows["B2"] | rows["B3"] | rows["B4"] if code[a] != v299[a]}
    stray2, missing2 = sorted(d_v299 - exp_v299), sorted(exp_v299 - d_v299)
    ck(not stray2 and not missing2, f"release vs V299: {len(d_v299)} bytes, 0 stray, 0 missing "
       f"(stray {[hex(a) for a in stray2[:6]]}, missing {[hex(a) for a in missing2[:6]]})", "S")
    for k in REMOVED_ROWS:
        ck(all(code[a] == stock[a] for a in rows[k]), f"{k:4s} back to stock ({len(rows[k])} B)", "S")

    # [7] the cave, the pages, the records
    say("\n  [7] READBACK on the BUILT image")
    cave = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_LEN])
    if V299_IDENTICAL:
        ck(hashlib.sha256(cave).hexdigest() == V299_CAVE_SHA, "assertion (3): cave sha-identical to V299's", "S")
    else:
        cd = {CAVE_BASE + i for i in range(CAVE_LEN) if cave[i] != v299[CAVE_BASE + i]}
        allowed = set().union(*[rng(a, 2) for a in CAVE_IMM.values()]) | rng(G_TABLE_ADDR, 6 * 7)
        ck(cd <= allowed, f"assertion (3'): cave diff vs V299 ({len(cd)} B) lies in the tuning immediates only", "S")
    ck(all(code[a] == stock[a] for a in range(0xCE000, 0xDA000) if a not in rows["D8k"] and not (0xD7FFC <= a < 0xD8000)),
       "assertion (7): pages 0xCE..0xD9 byte-identical to stock incl. trailers, except the 12 kept DampAxis bytes + the 0xD7 trailer", "S")
    ck(all(code[a] == v299[a] for a in rows["D8k"] | rows["D5k"]) and sum(1 for a in rows["D8k"] | rows["D5k"] if code[a] != stock[a]) == 13,
       "rev 2: the 13 DampAxis bytes (0xD7A5C x6, 0xD7A6C x6, 0xC40DC) == V299, all 13 differ from stock", "S")
    ck(struct.unpack_from("<3h", code, 0xD7A5C) == (-29490, -17202, -16000) == struct.unpack_from("<3h", code, 0xD7A6C)
       and code[0xC40DC] == 14, "DampAxis Y rows (-29490,-17202,-16000) x2 and alpha2 14 on the image", "T")
    ck(all(u16(code, y + 2 * i) == TUNING["KP"] for (y, n) in kp_y for i in range(n)) and len(set(KP)) == 28,
       f"assertion (8): Kp == {TUNING['KP']} on all 5 knots of all 28 records (N from each header)", "S")
    ck(all(u16(code, y + 2 * i) == TUNING["KD"] for (y, n) in kd_y for i in range(n)) and len(set(KD)) == 28,
       f"assertion (8): Kd == {TUNING['KD']} on all 4 knots of all 28 records", "S")
    ck(all(u16(code, kp_y[i][0] - 2 - 2 * kp_y[i][1] + 2 + 2 * j) == u16(stock, kp_y[i][0] - 2 * kp_y[i][1] + 2 * j)
           for i in range(28) for j in range(kp_y[i][1])), "Kp X knots (the demand-index axis) untouched = stock", "S")
    ck(u16(code, 0xC63E6) == TUNING["KI"] and u16(code, 0xC61BA) == TUNING["ICL"], "Ki / ICL on the image", "T")
    ck((struct.unpack_from("<h", code, 0xC63E8)[0], u16(code, 0xC63EA), u16(code, 0xC62E6), u16(code, 0xC62E4))
       == (0, 8192, 65535, 0), "fb-lag a/b/C/DB = 0/8192/65535/0 (r26 = 16*theta)", "T")
    ck(u16(code, 0xC6CD0) == 5346 and u16(code, 0xC61B2) == 3072 and u16(code, 0xC61B4) == 3072
       and bytes(code[0x2A1F0:0x2A1F2]) == bytes(v299[0x2A1F0:0x2A1F2]), "authority chain 5346 / 3072 / repoint", "T")
    ck(u16(code, 0xC62EA) == 0 and all(code[a] == 0xFF for a in rng(0xC61C0, 6) | rng(0xC64B4, 5)),
       "D4 lockout 0 + D6 debounce/DTC package 0xFF", "T")
    ck(u32(code, 0xC4C1E) == G_TABLE_ADDR, "the cave's G-table pointer == 0xC4CDA", "S")
    ck(bytes(code[0x29D76:0x29D7A]) == bytes(v299[0x29D76:0x29D7A]) and bytes(code[0x55C0E:0x55C12]) == bytes(stock[0x55C0E:0x55C12]),
       "the angle hook present; the telemetry hook stock", "S")
    ck(all(code[a] == 0xFF for a in range(0xC4B34, 0xC4BD8)), "the telemetry cave region is 0xFF", "S")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()

    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [8] .rwd ENCODE (headers '/' = A110, A160, A16A, A16B, A16C) + READBACK + non-circular cipher check")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches (container template)", "C")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        headers = header_add(info["headers"], [VSTR_A16A, VSTR_A16B, VSTR_REL], R)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(headers, info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V300 output")
        back = bytearray(stock)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code), "assertion (6): the .rwd decoded back is BYTE-IDENTICAL to the built image", "S")
        v38 = bytearray(stock)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        got = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in parse_x31(rwd)["headers"]}
        ck(got.get("/") == [s.decode() for s in (VSTR_A110, VSTR_A160, VSTR_A16A, VSTR_A16B, VSTR_REL)],
           f"V300 .rwd '/' header lists {got.get('/')}", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()

    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")
    say("\n" + "=" * 118)
    say(f"  image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  .rwd  SHA256 {rwd_sha}")
    say(f"  release vs stock {len(d_stock)} B in {len(blocks)} CRC blocks   |   release vs V299 {len(d_v299)} B")
    say(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['C']} constant-checks, "
        f"{R.census['V']} vacuous/entailed, {R.census['T']} tautological")
    say("=" * 118)
    return dict(code=bytes(code), stock=stock, v299=v299, rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, tag=TAG,
                img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, d_stock=sorted(d_stock), d_v299=sorted(d_v299),
                rows=rows, blocks=blocks)


def header_add(headers, strings, R):
    out = []
    for tag, vals in headers:
        vals = list(vals)
        if tag == b"/":
            R.check(VSTR_A160 in vals and VSTR_A110 in vals, "source .rwd '/' lists A110 + A160", "C")
            for s in strings:
                if s not in vals:
                    vals.append(s)
        if tag == b"!" and len(vals) >= 1:
            for _ in strings:
                vals.append(vals[-1])
        out.append((tag, vals))
    return out


def main():
    r = build()
    rr = r["run"]
    print(f"\n  census: {rr.census}  ({rr.ok}/{rr.n})")
    out_img, out_rwd = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    if WRITE_MODE == "rwd":
        print("\n  [9] WRITE -- guarded, re-hashed after")
        others = [p for p in Path(RWD_DIR).glob("*V300*") if p.name != RWD_NAME]
        if others:
            raise SystemExit(f"WRITE GUARD: another V300 rwd exists: {[p.name for p in others]}")
        if out_img.exists():
            assert hashlib.sha256(out_img.read_bytes()).hexdigest() == r["img_sha"], "existing image differs!"
            print(f"      [PASS] image already on disk and matches: {out_img}")
        else:
            with open(out_img, "xb") as fh:
                fh.write(r["code"])
            print(f"      [PASS] image written: {out_img}")
        if out_rwd.exists():
            assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"], "existing rwd differs!"
            print(f"      [PASS] rwd already on disk and matches: {out_rwd}")
        else:
            with open(out_rwd, "xb") as fh:
                fh.write(r["rwd"])
            assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"]
            print(f"      [PASS] rwd written: {out_rwd}")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V300_WRITE=rwd to emit the files.")
    return r


if __name__ == "__main__":
    main()
