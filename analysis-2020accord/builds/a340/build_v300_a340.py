# -*- coding: utf-8 -*-
r"""builds/a340/build_v300_a340.py -- V300-A340 REV 3: the 6x "PTM" (A160 V300 rev 2, the firmware ANGLE LOOP) PORTED TO
39990-TVA-A340.  BASE = A340 STOCK (sha256 01a53539...).  NOT FLOWN.

REV 3 (2026-11-02, operator: "make sure DTC 0x49 does not fire on A340"): row D6b -- the DTC-0x49 counter-B gate READS
  0x2961C `ld.bu 0x7508[tp],r12` and 0x2962E `ld.bu 0x7508[tp],r7` are re-pointed (hw2 0x7509 -> 0x7D29) to 0xC6D28, a byte that
  is 0xFF on stock inside the unreferenced run [0xC6D28,0xC6FF0) and is NEVER written (the 16-bit gain cell A6 lives at 0xC6E88 in the
  same run).  The hand index gp-0x67f5 (u8) can never exceed 0xFF, so the counter<50 path stores 0 every tick, the >= 50 free-running
  phase is unreachable and the FUN_00016ed0(0x49) call is dead -- V37's mask, ported.  The override cut 0x2A068/0x2A076 still reads
  0xC6508 == 112 (asserted stock).  REV 2 carried the V36 debounce package with 0xC6508 stock, so the counter could saturate under 6x
  authority as on A160 V36.  4 code bytes in the main CRC block.  REV 2 (image 21fc5783..., rwd b6f6c960...) is deleted from disk.

STUDY BUILD.  A built image on disk is not a flash.  Nothing here sends anything to a car; flashing is gated on the
operator naming the file and the bus.  Files are written ONLY with ACCORD_V300_A340_WRITE=1 (default: dry run).

SPEC (used verbatim): docs/specs/design/a340/PORT-SPEC-A340-2026-11-01.md, section "6x PTM (V300) -> MAPPED";
supporting traces TRACE-A340-LKAS-LANE-2026-11-01.md (sec. 2 sites + stock bytes, sec. 3 cells, sec. 4 records) and
TRACE-A340-RAM-INTERLOCKS-BOOTLOADER-2026-11-01.md.  The cave is re-assembled at build time from the kit copy of the
T4c listing (a340_cave_listing.py) and must equal the frozen 260 B (sha 3e14a246...).  No address below is carried from
A160: each was re-found on A340 by FUNCTION and is asserted against the A340 stock bytes before it is written.

THE EDITS (A160 V300 census row -> A340):
  A1  F181 0x13109 '-' -> ',' and letter 0x1310D '0' -> 'C'  =>  39990-TVA,A34C   (0x14120 NOT touched, as A160 V300 D11)
  A2  in-place lane edits (FUN_00029230):
        E1   0x292EE  24 47 da 95 -> ld.h -0x69c8[gp],r8        x := theta (fb-filter input; stock gp-0x6a26 rate)
        E2   0x29346  stock is already `add r10,r26` -- no edit (asserted)
        B2   0x29E68  e2 47 00 00 -> cmovne r0,r25,r8           r8 = (request==1) ? eligibility(r25) : 0
        A2   0x29E6E  da 05 (bne +10) -> be 0x29E74             PID runs iff ramp != 0 and r8 != 0, else jr 0x2A596
        E4   0x2A334  08 48 eb 48 -> ld.h -0x6976[gp],r9        sp := the 0xE4 demand clamp(-4*raw, +-0x4000)
        HOOK 0x2A340  c5 4a ba 49 -> jarl 0xC4C00,r7            (link r7 -- r6 is LIVE on A340)
        OPH  0x2A3D4  89 51 -> mov r26,r10                      D operand := the fresh 1 kHz rate the cave loads in r26
  A3  the angle-loop cave [0xC4C00,0xC4D04) 260 B: E = 4*sp - r26, op-skip, G(v) table (V300's G and S halved,
      round-half-up), E' = (E*G')>>8, camera gate r25, 1229 hand freeze, asymmetric angle bound with the two-level cap,
      ramp-in, CAM tail decay sar 7.  Exits jr 0x2A596 (skip) / jr 0x2A348 (freeze, out in r13) / jmp [r7] (0x2A344).
  A4  fb lag re-purposed (r26 = 16*theta): a 0xC63F8 953 -> 0, b 0xC63FA 1554 -> 8192, C 0xC62F8 7680 -> 65535,
      DB 0xC62F6 4 -> 0
  A5  dir-2 (camera-arm) hand fades = the u8 cal tables 0xC6C00 / 0xC6C10 := the A340 dir-0 values, read from the
      dir-0 flash records at build time (A340's dir-0 fades are speed-scheduled RAM tables; all 36 records identical)
  A6  authority: 0x2A620 `ld.h 0x748a[tp],r11` hw2 -> 0x7E88 (private cell 0xC6E88 := 6 * 888 = 5328; 0xC6CD0, V300's
      A160 cell, is OCCUPIED on A340); clamps 0xC61C0 / 0xC61C2 512 -> 3072.  The shared 0xC648A (6 readers) stays 888.
  A7  EME soft-limit ladder -- int16 corridor 0xC679E/A0/AA/AC and boost floor 0xC67B8/BA/BC with their f32 mirrors
      0xC65E8/EC/FC/0xC6600 and 0xC6614/18/1C, set to the A160 V300 IMAGE's values (read at build time: +-5120 / 5.0).
      !! NOT LISTED in the port spec's 6x section; carried because A160 V300 keeps A7 (census).  Flag CARRY_A7;
      the orchestrator was told on 2026-11-01 and may rule it out.
  B   gains re-expressed for A340's Q-formats so P and I per unit error equal A160 V300's (G' = G/2 in the cave):
        Kp 7 (P = (E'*Kp)>>3), Kd 48 ((dE*Kd)>>3), Ki 20 (inc = ((e*Ki)<<2)>>3) on ALL 36 records of each table
        (3 speed pointer tables x 12 variants; X knots untouched); ICL 0xC61C8 0 -> 8192;
        P clamp 0xC61CC and sum clamp 0xC61CE 20480 -> 15360; output lag 0xC63FC/0xC63FE 1005/324 -> 992/507 (A160's)
  D4  low-speed lockout 0xC62FC: already 0 on A340 stock -- no edit (asserted)
  D6  STEER_STATUS debounce as the 2x REV 3 build: 0xC61D0/D2/D4 -> 0xFFFF x3, 0xC6504..07 -> 0xFF x4.
      0xC6508 (DTC-0x49 gate AND the A340 driver-override cutoff, Lens C on V37A-A340 REV 2) STAYS STOCK 112.
  D6b REV 3: counter-B gate reads 0x2961C/0x2962E hw2 0x7509 -> 0x7D29 (read 0xC6D28 = 0xFF): the DTC-0x49 mask (V37) without
      touching the override cut.  Same edit as V37A-A340 REV 4 (i).

REV 2 (2026-11-02, adversarial Lens C FAIL on REV 1, accepted by the orchestrator): the 13 DampAxis bytes ARE carried --
  rows 0xD7A5C / 0xD7A6C := A160 V300's -29490,-17202,-16000 (stock -9830,-5734,-1966; same addresses on A340, same X 0,1280,5760,
  same producer/consumer structure) and the producer EMA alpha2 0xC40D4 22 -> 14 (A340's cell; A160's 0xC40DC holds other data on
  A340).  Reason: A160's GATE 2 re-score showed the stock rows FAIL (GM 20 -> 5.2 dB at 3 m/s) with this exact controller, and the
  A340 controller equals A160 V300's to 0.5 %; the A340 plant is BELIEF-identical (K1 900, K2 1157 vs 1159).  REV 1 (image
  597f32ca..., rwd 6cd33202...) deleted.
NOT CARRIED (say so plainly):
  * C* telemetry, D1-D3, D5, D7 (EME step), D8 banks, D9 map, D10 LIM, D11 (0x14120) -- as A160 V300.
  * The post-fade clamp 0xC61CA (A340-only, 20476) stays stock: it sits above the 15360 sum clamp.

Open (BELIEF, for the adversarial pass): the twin 0x2AE74 liveness (no callers found; register-indirect not excluded);
the gp-0x687b lockout term; the 0.1 deg/count angle scale; the cave register map is proven by main's listing liveness
proof and the H1 interpreter, not by an on-car run.
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
from firmware_paths import plain_image_path, RWD_DIR                                  # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                               # noqa: E402
import a340_cave_listing as CL                                                        # noqa: E402
import a340_cave_h1 as H1                                                             # noqa: E402
import build_v37a_a340 as V37A340                                                     # noqa: E402  (A340 lane mirror)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE = os.environ.get("ACCORD_V300_A340_WRITE", "").strip() == "1"
MAX_PATH = 259
CARRY_A7 = True                     # A7 IS in the port spec (PORT-SPEC line "A7 EME ladder as A160 V300"); Lens B D2 corrected the docstring claim

FW_ROOT = Path(os.environ["ACCORD_FIRMWARE_ROOT"])
A340_PATH = FW_ROOT / "analysis-2020accord" / "other bins" / "39990-TVA-A340.bin"
A340_SHA = "01a53539e19bb0b54fb339a08644ca6981b844fad41276a1f8c305f13aa6f071"
A160_V300_NAME = ("_v300_V300-REV2-RELEASE-ANGLELOOP.FROMSTOCK-KP112.KD48.KI40.ICL8192-FRZ1229.CAP4096.6144-NOTELEMETRY"
                  ".NOMAP.STOCKASSIST.DAMPAXIS.V299.A16C_plain_image.bin")
A160_V300_SHA = "7d58c823"          # prefix (memory: V300 rev 2 image 7d58c823...); asserted as a prefix

EXP_IMG_SHA = "dc30a73b104d03b1550ed23aa1088278d1f5cfa5257dbaa095a091de137a56e0"
LABEL = "V300-A340-REV3"
TAG = "ANGLELOOP.KP7.KD48.KI20.ICL8192-GHALF.CAMSAR7-AUTH5328.CL3072-DAMPAXIS.V299.A3400C40D4.14-DTCB.MASK7D28" + (".EME5120" if CARRY_A7 else "")
IMG_NAME = "_v300_a340_REV3_plain_image.bin"
RWD_NAME = f"39990-TVA,A340-{LABEL}-{TAG}-0x{START:X}-0x{END:X}.rwd"
RELEASE_LETTER = b"C"
VSTR = [b"39990-TVA-A310", b"39990-TVA-A340", b"39990-TVA,A340", b"39990-TVA,A34C"]
HW_STR = b"001100121020"

GP, TP = 0xFEDF8000, 0xBF000

# ---- A2: in-place code sites (addr, stock bytes) and the edit, encoded by this script's own encoder ---------------
CAVE_BASE, CAVE_LEN = 0xC4C00, 260
CAVE_SHA = "3e14a246b2ed1313c18dfca196e7b95767e2b4a682d249e74f14eddabb2796d6"
A160_CAVE_SHA = "e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608"
HOOK_RET, FRZ_RET, SKIP_TGT = 0x2A344, 0x2A348, 0x2A596
SITES = {   # id: (addr, stock hex, instruction spec for enc())
    "E1":   (0x292EE, "2447da95", ("ld_h_gp", -0x69C8, 8)),
    "B2":   (0x29E68, "e2470000", ("cmov", 0xA, 0, 25, 8)),       # cmovne: cccc = 0xA (NE), reg3 = cond ? reg1 : reg2
    "A2":   (0x29E6E, "da05",     ("bcond", "be", 0x29E74)),
    "E4":   (0x2A334, "0848eb48", ("ld_h_gp", -0x6976, 9)),
    "HOOK": (0x2A340, "c54aba49", ("jarl", CAVE_BASE, 7)),
    "OPH":  (0x2A3D4, "8951",     ("mov", 26, 10)),
    "A6":   (0x2A620, "255f8a74", ("ld_h_tp", 0xC6E88, 11)),
}
# D6b (REV 3): the two DTC-0x49 counter-B gate reads -> 0xC6D28 (0xFF).  Same constants as build_v37a_a340 (i); asserted equal.
DTC_B_SITES = {0x2961C: "85670975", 0x2962E: "853f0975"}
DTC_B_HOST = 0xC6D28
DTC_B_HW2 = (DTC_B_HOST - TP) | 1                                     # 0x7D29
GATE_READERS_STOCK = [0x2961C, 0x2962E, 0x2A068, 0x2AF52, 0x2AF64, 0x2B6B8]
OVERRIDE_CUT_SITE = (0x2A068, "855f0975")
# A160 positive control for the encoder: (addr, V300-image bytes, spec) -- must reproduce the A160 V300 image
A160_SITES = {
    "E1":   (0x28F4C, ("ld_h_gp", -0x6A00, 7)),
    "B2":   (0x29A50, ("cmov", 0xA, 0, 27, 8)),
    "A2":   (0x29A56, ("bcond", "be", 0x29A5C)),
    "E4":   (0x29D6A, ("ld_h_gp", -0x69AE, 16)),
    "HOOK": (0x29D76, ("jarl", CAVE_BASE, 6)),
    "OPH":  (0x29EE0, ("mov", 26, 8)),
    "A6":   (0x2A1EE, ("ld_h_tp", 0xC6CD0, 7)),
}
# stock bytes asserted but never written
STOCK_ONLY = {"E2 add r10,r26 (already add)": (0x29346, "cad1"), "HOOK_RET mov r9,r13": (0x2A344, "0968"),
              "FRZ_RET cmp r8,r13": (0x2A348, "e869"), "SKIP mov 0,lp": (0x2A596, "00fa"),
              "OPH predecessor cmovnc r9,r10,r10": (0x2A3D0, "e9573253")}

# ---- cal cells: (addr, stock, new, row, signed) ------------------------------------------------------------------
GAIN_SHARED = 0xC648A                 # 888, 6 readers, NOT written (A6 repoints the lane away from it)
GAIN_CELL = 0xC6E88                   # free 0xFFFF (freecell census), := 6 * stock(0xC648A)
CAL = [
    (0xC61C0, 512, 3072, "A6", False), (0xC61C2, 512, 3072, "A6", False),
    (0xC63F8, 953, 0, "A4", True), (0xC63FA, 1554, 8192, "A4", False), (0xC62F8, 7680, 65535, "A4", False),
    (0xC62F6, 4, 0, "A4", False),
    (0xC61C8, 0, 8192, "B", False), (0xC61CC, 20480, 15360, "B", False), (0xC61CE, 20480, 15360, "B", False),
    (0xC63FC, 1005, 992, "B", True), (0xC63FE, 324, 507, "B", False),
    (0xC61D0, 12800, 0xFFFF, "D6", False), (0xC61D2, 8960, 0xFFFF, "D6", False), (0xC61D4, 11520, 0xFFFF, "D6", False),
]
CAL_U8 = [(0xC6504, 112, 0xFF, "D6"), (0xC6505, 96, 0xFF, "D6"), (0xC6506, 54, 0xFF, "D6"), (0xC6507, 64, 0xFF, "D6")]
DTC_GATE_ADDR = 0xC6508
STOCK_CELLS = {"D4 low-speed lockout 0xC62FC": (0xC62FC, 0), "DTC-0x49 gate / override cutoff 0xC6508": (0xC6508, 112, "u8"),
               "D6b host 0xC6D28 (never written)": (0xC6D28, 0xFF, "u8"),
               "post-fade clamp 0xC61CA": (0xC61CA, 20476), "D clamp 0xC61C4": (0xC61C4, 10240),
               "shared fwd gain 0xC648A": (0xC648A, 888)}
DAMPAXIS_ROWS = (0xD7A5C, 0xD7A6C)    # -9830,-5734,-1966 on stock; REV 2: := A160 V300's rows (D8k)
DAMPAXIS_ALPHA2 = (0xC40D4, 22, 14)    # A340 producer FUN_00041fe6 EMA alpha2 (D5k); A160's was 0xC40DC
# A7: (A340 int16, A340 f32, A160 int16, A160 f32)
A7_PAIRS = [(0xC679E, 0xC65E8, 0xC674E, 0xC6598), (0xC67A0, 0xC65EC, 0xC6750, 0xC659C),
            (0xC67AA, 0xC65FC, 0xC675A, 0xC65AC), (0xC67AC, 0xC6600, 0xC675C, 0xC65B0),
            (0xC67B8, 0xC6614, 0xC6768, 0xC65C4), (0xC67BA, 0xC6618, 0xC676A, 0xC65C8),
            (0xC67BC, 0xC661C, 0xC676C, 0xC65CC)]
A7_STOCK_INT = (1024, 1024, -1024, -1024, 0, 1536, 2048)

# ---- B: gain records.  (name, 3 speed pointer tables, n, stock Y, new Y value) -------------------------------------
N_VAR = 12
GAIN_TABLES = [("Kp", (0xC77E4, 0xC78D4, 0xC79C4), 5, (10, 15, 19, 21, 21), 7),
               ("Kd", (0xC7784, 0xC7874, 0xC7964), 4, (32, 32, 32, 32), 48),
               ("Ki", (0xC77B4, 0xC78A4, 0xC7994), 4, (0, 0, 0, 0), 20)]
# ---- A5: dir-2 u8 tables (addr) <- dir-0 record family (3 pointer tables) ------------------------------------------
FADES = [("fadeB2 <- fadeB dir-0", 0xC6C10, (0xC7844, 0xC7934, 0xC7A24)),
         ("fadeA2 <- fadeA dir-0", 0xC6C00, (0xC7814, 0xC7904, 0xC79F4))]
FADE_N = 6

OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self):
        self.n = self.ok = 0
        self.census = {"S": 0, "C": 0, "V": 0, "T": 0}
        self.failures = []

    def check(self, cond, msg, kind="S"):
        self.n += 1
        self.census[kind] += 1
        cond = bool(cond)
        self.ok += cond
        print(f"      {OK if cond else BAD} [{kind}] {msg}")
        if not cond:
            self.failures.append((kind, msg))
        return cond


u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]                # noqa: E731
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]                # noqa: E731
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]                # noqa: E731
f32 = lambda b, a: struct.unpack_from("<f", b, a)[0]                # noqa: E731


def rec(b, p):
    """flash record: u16 n, X[n] s16, Y[n] s16"""
    n = u16(b, p)
    return n, [s16(b, p + 2 + 2 * i) for i in range(n)], [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def u8tab(b, a, n=FADE_N):
    """dir-2 fade table: u8 n, u8 X[n], u8 Y[n]"""
    return b[a], list(b[a + 1:a + 1 + n]), list(b[a + 1 + n:a + 1 + 2 * n])


# ---- an independent encoder for the in-place edits (positive-controlled on the A160 V300 image) ---------------------
BCOND = {"be": 0x2, "bne": 0xA}


def enc(spec, pc):
    op = spec[0]
    if op == "ld_h_gp":                         # Format VII ld.h disp16[gp=r4],reg2 ; hw2 bit 0 = 0 (halfword)
        _, disp, r2 = spec
        assert disp % 2 == 0
        return struct.pack("<HH", (r2 << 11) | (0x39 << 5) | 4, disp & 0xFFFF)
    if op == "ld_h_tp":                         # same, base tp = r5; disp = cell - tp
        _, cell, r2 = spec
        disp = cell - TP
        assert 0 <= disp < 0x8000 and disp % 2 == 0
        return struct.pack("<HH", (r2 << 11) | (0x39 << 5) | 5, disp)
    if op == "cmov":                            # Format XII cmov cccc,reg1,reg2,reg3: reg3 = cond ? reg1 : reg2
        _, cc, r1, r2, r3 = spec
        return struct.pack("<HH", (r2 << 11) | (0x3F << 5) | r1, (r3 << 11) | (0x19 << 5) | (cc << 1))
    if op == "bcond":                           # Format III, disp9
        _, cn, tgt = spec
        d = tgt - pc
        assert -256 <= d < 256 and d % 2 == 0
        d &= 0x1FF
        return struct.pack("<H", (((d >> 4) & 0x1F) << 11) | (0b1011 << 7) | (((d >> 1) & 7) << 4) | BCOND[cn])
    if op == "jarl":                            # Format V jarl disp22,reg2 (opcode field 0x1E in bits 10..6)
        _, tgt, r2 = spec
        d = (tgt - pc) & 0x3FFFFF
        assert (tgt - pc) % 2 == 0 and -(1 << 21) <= tgt - pc < (1 << 21)
        return struct.pack("<HH", (r2 << 11) | (0x1E << 6) | (d >> 16), d & 0xFFFE)
    if op == "mov":                             # Format I mov reg1,reg2
        _, r1, r2 = spec
        return struct.pack("<H", (r2 << 11) | r1)
    raise ValueError(op)


def dec_jr(img, a):
    """Format V jr/jarl at a -> (reg2, target) or None"""
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    if ((hw1 >> 6) & 0x1F) != 0x1E or hw2 & 1:
        return None
    d = ((hw1 & 0x3F) << 16) | hw2
    d = d - (1 << 22) if d & (1 << 21) else d
    return hw1 >> 11, (a + d) & 0xFFFFFFFF


def decode_refs(code, base=CAVE_BASE):
    """(copy of build_v298_tva.decode_refs) mov-imm32, Format-V jr/jarl, Bcond targets, at EVERY even offset"""
    movimm32, jrs, bconds = [], [], []
    for off in range(0, len(code) - 2, 2):
        hw1 = code[off] | (code[off + 1] << 8)
        op6 = (hw1 >> 5) & 0x3F
        reg2, reg1 = hw1 >> 11, hw1 & 0x1F
        if (hw1 & 0xFFE0) == 0x0620 and off + 6 <= len(code):
            movimm32.append((off, reg1, u32(code, off + 2)))
        if (hw1 >> 7) & 0xF == 0xB:
            d = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            bconds.append((off, hw1 & 0xF, base + off + d))
        if op6 in (0x3C, 0x3D) and off + 4 <= len(code):
            hw2 = code[off + 2] | (code[off + 3] << 8)
            if not (hw2 & 1):
                disp = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
                disp = disp - (1 << 22) if disp & (1 << 21) else disp
                jrs.append((off, reg2, (base + off + disp) & 0xFFFFFFFF))
    return dict(movimm32=movimm32, jrs=jrs, bconds=bconds)


def walk_counts(img):
    out = []
    for fn in (walk, walk_all_blocks):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fails = fn(bytes(img))
        line = [ln for ln in buf.getvalue().splitlines() if "result:" in ln][-1]
        out.append((int(line.split("result:")[1].split("block")[0]), fails))
    return out


def tp_refs(img, cell):
    """raw 4-byte tp-relative loads of `cell` over [0x13000,0xC0000) (the V37A-A340 scanner, positive-controlled on
    0xC648A = 6 / 0xC62F8 = 3).  The 6-byte / movea / pointer forms were covered by the freecell census (T6 brief)."""
    return V37A340.tp_readers(img, cell)


def ptr_records(img, tabs):
    return [(t, v, u32(img, t + 4 * v)) for t in tabs for v in range(N_VAR)]


# =====================================================================================================================
def build():
    R = Run()
    ck = R.check
    print("=" * 118)
    print(f"  {LABEL}: the 6x PTM (A160 V300 rev 2 angle loop) ported to 39990-TVA-A340.  BASE = A340 STOCK.  CARRY_A7 = {CARRY_A7}")
    print("=" * 118)

    # ---- [0] base --------------------------------------------------------------------------------------------------
    print("\n  [0] BASE")
    stock = open(A340_PATH, "rb").read()
    ck(len(stock) == 0x100000 and hashlib.sha256(stock).hexdigest() == A340_SHA, f"A340 stock sha256 {A340_SHA[:16]}...", "C")
    ck(stock[0x13100:0x1310E] == b"39990-TVA-A340", "F181 at 0x13100 == 39990-TVA-A340", "V")
    wc = walk_counts(stock)
    ck(wc == [(49, 0), (50, 0)], f"stock CRC bootloader replay {wc[0]} + full chain {wc[1]} (want 49/0, 50/0)", "V")
    a160 = Path(plain_image_path(A160_V300_NAME)).read_bytes()
    a160_sha = hashlib.sha256(a160).hexdigest()
    ck(a160_sha.startswith(A160_V300_SHA), f"A160 V300 rev 2 image sha256 {a160_sha} (reference for the encoder control, "
       f"the cave control and A7's values)", "C")
    code = bytearray(stock)
    touched = {}                                         # addr -> row id

    def put(a, bs, tag):
        code[a:a + len(bs)] = bs
        for k in range(len(bs)):
            touched[a + k] = tag

    # ---- [1] encoder positive control on the A160 V300 image ------------------------------------------------------
    print("\n  [1] ENCODER POSITIVE CONTROL -- the same encoder reproduces every A160 V300 in-place edit from its image")
    for k, (a, spec) in A160_SITES.items():
        e = enc(spec, a)
        ck(a160[a:a + len(e)] == e, f"A160 {k:4s} 0x{a:05X}: enc{spec} = {e.hex(' ')} == V300 image {a160[a:a + len(e)].hex(' ')}", "S")

    # ---- [2] A2 in-place code sites --------------------------------------------------------------------------------
    print("\n  [2] A2 IN-PLACE LANE EDITS (FUN_00029230) + A6 repoint -- stock bytes asserted, new bytes encoded here")
    for k, (a, sh, spec) in SITES.items():
        sb = bytes.fromhex(sh)
        e = enc(spec, a)
        ck(stock[a:a + len(sb)] == sb and len(e) == len(sb), f"stock {k:4s} 0x{a:05X} == {sh}", "V")
        put(a, e, "A6" if k == "A6" else "A2")
        print(f"         {k:4s} 0x{a:05X}: {sb.hex(' ')} -> {e.hex(' ')}   {spec}")
    exp = {"E1": "24473896", "B2": "e0cf3443", "A2": "b205", "E4": "244f8a96", "HOOK": "893fc0a8", "OPH": "1a50",
           "A6": "255f887e"}
    ck(all(bytes(code[a:a + len(bytes.fromhex(exp[k]))]).hex() == exp[k] for k, (a, _, _) in SITES.items()),
       f"encoded bytes == the port spec / T4c bytes (two derivations agree)", "S")
    for nm, (a, sh) in STOCK_ONLY.items():
        ck(stock[a:a + len(bytes.fromhex(sh))].hex() == sh, f"stock-only 0x{a:05X} == {sh} ({nm})", "V")
    j = dec_jr(stock, 0x29E74)
    ck(j == (0, SKIP_TGT), f"A2's new taken target 0x29E74 is `jr 0x2A596` (Honda skip epilogue): {j}", "S")

    # ---- [2b] D6b: DTC-0x49 counter-B gate reads -> 0xC6D28 (0xFF) ----------------------------------------------
    print("\n  [2b] D6b (REV 3): DTC-0x49 COUNTER-B GATE READS 0x2961C/0x2962E -> 0xC6D28 (0xFF) -- V37's mask, override cut untouched")
    ck((DTC_B_SITES, DTC_B_HOST, DTC_B_HW2, GATE_READERS_STOCK, OVERRIDE_CUT_SITE) ==
       (V37A340.DTC_B_SITES, V37A340.DTC_B_HOST, V37A340.DTC_B_HW2, V37A340.GATE_READERS_STOCK, V37A340.OVERRIDE_CUT_SITE),
       "D6b constants == build_v37a_a340 (i) constants (one definition of the edit)", "C")
    ck(stock[DTC_B_HOST] == 0xFF and DTC_B_HOST < GAIN_CELL and GAIN_CELL + 2 <= 0xC6FF0,
       "host 0xC6D28 is 0xFF and does not overlap the A6 gain cell 0xC6E88/89 in the same free run", "V")
    ck(V37A340.byte_readers(stock, DTC_B_HOST) == [] and V37A340.byte_readers(stock, DTC_B_HOST + 1) == [] and not tp_refs(stock, DTC_B_HOST)
       and not tp_refs(stock, DTC_B_HOST - 2) and stock.count(struct.pack("<I", DTC_B_HOST)) == 0,
       "no byte/half/word tp load of 0xC6D28 (parity-exact + loose), no absolute pointer on stock", "S")
    ck(sorted(V37A340.byte_readers(stock, DTC_GATE_ADDR)) == GATE_READERS_STOCK and V37A340.byte_readers(stock, DTC_GATE_ADDR + 1) == [0x46020, 0x460F0],
       "positive control + census: 0xC6508 has exactly its 6 stock byte readers (the 2 loose extra hits read the odd neighbour 0xC6509)", "S")
    for a, sh in DTC_B_SITES.items():
        ck(stock[a:a + 4] == bytes.fromhex(sh) and u16(stock, a + 2) == 0x7509, f"stock 0x{a:05X} == {sh} (ld.bu 0x7508[tp])", "V")
        put(a + 2, struct.pack("<H", DTC_B_HW2), "D6b")
        ck(code[a:a + 2] == stock[a:a + 2] and u16(code, a + 2) == 0x7D29, f"0x{a:05X}: hw1 unchanged, hw2 -> 0x7D29 = ld.bu 0x7D28[tp] (0xC6D28)", "T")
    ck(sorted(V37A340.byte_readers(code, DTC_B_HOST)) == sorted(DTC_B_SITES) and sorted(V37A340.byte_readers(code, DTC_GATE_ADDR)) == sorted(set(GATE_READERS_STOCK) - set(DTC_B_SITES)),
       "BUILT: 0xC6D28 has exactly the two counter-B reads; 0xC6508 keeps the override cut 0x2A068 + the 3 twin reads", "S")
    a, sh = OVERRIDE_CUT_SITE
    ck(bytes(code[a:a + 4]) == stock[a:a + 4] == bytes.fromhex(sh) and bytes(code[0x2A06C:0x2A080]) == stock[0x2A06C:0x2A080],
       "override cut 0x2A068 ld.bu 0x7508[tp],r11 and its compare/cmovh/branch 0x2A06C..0x2A080 byte-identical to stock", "S")
    ck(bytes(code[0x295F2:0x29648]) == bytes(stock[0x295F2:0x29648]).replace(b"\x09\x75", b"\x29\x7d"),
       "the counter-B block 0x295F2..0x29648 differs from stock ONLY in the two hw2 halfwords", "S")
    j = dec_jr(code, 0x2A340)
    ck(j == (7, CAVE_BASE), f"built hook decodes as jarl 0x{CAVE_BASE:X},r7: {j}", "S")
    ck(u16(code, 0x2A622) == GAIN_CELL - TP, f"built 0x2A620 reads tp+0x{u16(code, 0x2A622):04X} = 0x{TP + u16(code, 0x2A622):05X}", "S")

    # ---- [3] A3 the cave -------------------------------------------------------------------------------------------
    print("\n  [3] A3 THE ANGLE-LOOP CAVE -- re-assembled from the kit listing, sha-frozen, decoded on the BUILT image")
    a160c, _, _ = CL.assemble(CL.MODES["A160"])
    ck(hashlib.sha256(a160c).hexdigest() == A160_CAVE_SHA and a160[CAVE_BASE:CAVE_BASE + CAVE_LEN] == a160c,
       "CONTROL: listing in A160 mode == the A160 V300 image's cave byte-for-byte (sha e22193b9...)", "S")
    cave, labels, _ = CL.assemble(CL.MODES["A340"])
    ck(len(cave) == CAVE_LEN and hashlib.sha256(cave).hexdigest() == CAVE_SHA, f"A340 cave {len(cave)} B sha {CAVE_SHA[:16]}...", "C")
    ck(all(b == 0xFF for b in stock[0xC4B2C:0xC4FF0]), "stock [0xC4B2C,0xC4FF0) all 0xFF (free; cave = [0xC4C00,0xC4D04))", "V")
    ck(tuple(V53.owning_block(stock, CAVE_BASE)) == tuple(V53.owning_block(stock, CAVE_BASE + CAVE_LEN - 1)) == (0x13000, 0xC4FFC),
       "cave lies wholly inside the main CRC block [0x13000,0xC4FFC)", "S")
    ck(not tp_refs(stock, CAVE_BASE) and stock.count(struct.pack("<I", CAVE_BASE)) == 0,
       "no tp load and no absolute dword pointer to 0xC4C00 in stock (the region is unreferenced)", "S")
    put(CAVE_BASE, cave, "A3")
    built = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_LEN])
    refs = decode_refs(built)
    code_end = labels["TBL"]
    insn, pc = set(), CAVE_BASE
    for _, ins, _ in CL.listing(CL.MODES["A340"]):
        if ins[0] != "half":
            insn.add(pc)
        pc += CL.EA.size(ins)
    mv = [(o, r, v) for o, r, v in refs["movimm32"] if CAVE_BASE + o in insn]
    ck(mv == [(0x1C, 16, labels["TBL"])] and labels["TBL"] == CAVE_BASE + 0xDA,
       f"mov imm32 table pointer: {[(hex(CAVE_BASE + o), r, hex(v)) for o, r, v in mv]} == r16 <- cave+0xDA", "S")
    jrs = [(CAVE_BASE + o, r, t) for o, r, t in refs["jrs"] if CAVE_BASE + o in insn]
    ck(sorted(t for _, r, t in jrs) == [FRZ_RET, FRZ_RET, SKIP_TGT] and all(r == 0 for _, r, _ in jrs),
       f"exactly 3 jr (no jarl) at insn starts: {[(hex(a), hex(t)) for a, _, t in jrs]} -> 0x2A596, 0x2A348 x2", "S")
    bc = [(CAVE_BASE + o, t) for o, c, t in refs["bconds"] if CAVE_BASE + o in insn]
    ck(len(bc) == 16 and all(t in insn and t < code_end for _, t in bc),
       f"all {len(bc)} Bcond at insn starts land on in-cave instruction starts", "S")
    jmp = sorted((a, u16(code, a)) for a in insn if (u16(code, a) & 0xFFE0) == 0x0060)
    ck(jmp == [(labels["DONE"], 0x0067)], f"one `jmp [r7]` at {[hex(a) for a, _ in jmp]} (normal return to 0x2A344)", "S")
    tbl, t = [], labels["TBL"]
    while True:
        X, G, S = struct.unpack_from("<HHh", code, t)
        tbl.append((X, G, S))
        t += 6
        if X == 0xFFFF:
            break
    ck(tbl == [(X, (G + 1) >> 1, (S + 1) >> 1) for X, G, S in CL.V300_TBL] and t == CAVE_BASE + CAVE_LEN,
       f"G table read from the BUILT image == round-half-up(V300/2), ends at the cave end: {tbl}", "S")
    gpd = set()
    for a in insn:
        hw1 = u16(code, a)
        if (hw1 & 0x1F) == 4 and ((hw1 >> 5) & 0x3F) in (0x39, 0x3F):
            d = u16(code, a + 2) & 0xFFFE
            gpd.add(d - 0x10000 if d & 0x8000 else d)
    ck(sorted(gpd) == sorted([-0x6A8E, -0x6A2E, -0x4EC0, -0x69C8, -0x6DA0]),
       f"gp displacements the cave loads == rate -0x6a8e, speed -0x6a2e, |hand| -0x4ec0, theta -0x69c8, I -0x6da0: "
       f"{sorted(hex(d) for d in gpd)}", "S")
    st_ = [a for a in insn if ((u16(code, a) >> 5) & 0x3F) in (0x3A, 0x3B, 0x3E)]
    ck(not st_, f"the cave has no Format VII st.b/st.h/st.w (writes no RAM): {[hex(a) for a in st_]}", "S")
    H1.QUIET[0] = True
    b0, _ = H1.run("A160", a160c, 2000, 7)
    b1, h1 = H1.run("A340", built, 2000, 11)
    ck(b0 == 0, f"H1 CONTROL: interpreter on the A160 V300 cave vs the scalar reference: {b0}/2000 mismatches", "S")
    ck(b1 == 0 and len(h1) == 3, f"H1: interpreter on the BUILT image's cave vs the A340 reference: {b1}/2000 mismatches, "
       f"exits {h1}", "S")
    saved = dict(CL.MODES["A340"])
    CL.MODES["A340"].update(CAMSAR=6)
    try:
        bn, _ = H1.run("A340", built, 500, 5)
    finally:
        CL.MODES["A340"].clear()
        CL.MODES["A340"].update(saved)
    ck(bn > 0, f"H1 NEGATIVE CONTROL (reference with CAM sar 6): {bn}/500 mismatches (must be > 0)", "S")

    # ---- [4] A6 authority cell + clamps, A4 fb lag, B lane cells, D6 debounce -------------------------------------
    print("\n  [4] CAL CELLS (A4 fb lag, A6 authority, B lane gains/clamps/lag, D6 debounce) -- stock asserted first")
    ck(u16(stock, GAIN_CELL) == 0xFFFF and all(b == 0xFF for b in stock[0xC6D28:0xC6FF0]),
       "free-cell host 0xC6E88 is inside the 0xFFFF run [0xC6D28,0xC6FF0) on stock", "V")
    ck(not tp_refs(stock, GAIN_CELL) and stock.count(struct.pack("<I", GAIN_CELL)) == 0,
       "no tp load and no absolute pointer to 0xC6E88 on stock (freecell census: 6-byte/movea/pointer forms also null)", "S")
    gr = tp_refs(stock, GAIN_SHARED)
    ck(len(gr) == 6 and 0x2A620 in gr, f"positive control: the shared gain 0xC648A has 6 tp loads incl. 0x2A620: {[hex(x) for x in gr]}", "S")
    gnew = 6 * u16(stock, GAIN_SHARED)
    put(GAIN_CELL, struct.pack("<H", gnew), "A6")
    ck(gnew == 5328 and s16(code, GAIN_CELL) == 5328 and 6 * 891 == u16(a160, 0xC6CD0),
       f"0xC6E88 := 6 x stock 0xC648A = {gnew} (A160 V300: 0xC6CD0 = {u16(a160, 0xC6CD0)} = 6 x 891); fits ld.h as positive s16", "S")
    gr2 = tp_refs(code, GAIN_SHARED)
    ck(sorted(gr2) == sorted(set(gr) - {0x2A620}) and tp_refs(code, GAIN_CELL) == [0x2A620],
       f"BUILT: 0xC648A keeps its 5 other readers {[hex(x) for x in gr2]}; 0xC6E88 has exactly one reader, 0x2A620", "S")
    for a, sv, nv, row, sg in CAL:
        got = s16(stock, a) if sg else u16(stock, a)
        ck(got == sv, f"stock 0x{a:05X} == {sv} ({row})", "V")
        put(a, struct.pack("<h" if sg else "<H", nv), row)
    for a, sv, nv, row in CAL_U8:
        ck(stock[a] == sv, f"stock 0x{a:05X} == {sv} ({row})", "V")
        put(a, bytes([nv]), row)
    for nm, v in STOCK_CELLS.items():
        a, want = v[0], v[1]
        got_s = stock[a] if len(v) > 2 else u16(stock, a)
        got_c = code[a] if len(v) > 2 else u16(code, a)
        ck(got_s == want == got_c, f"left at STOCK on the BUILT image: {nm} == {want} (Lens B D1: reads code, not stock)", "S")
    ck(struct.unpack_from("<3h", stock, DAMPAXIS_ROWS[0]) == (-9830, -5734, -1966) == struct.unpack_from("<3h", stock, DAMPAXIS_ROWS[1])
       and struct.unpack_from("<3H", stock, DAMPAXIS_ROWS[0] - 6) == (0, 1280, 5760) and stock[DAMPAXIS_ALPHA2[0]] == DAMPAXIS_ALPHA2[1],
       "stock DampAxis rows -9830,-5734,-1966 with X 0,1280,5760 and alpha2 22 (A340 cells)", "V")
    for a in DAMPAXIS_ROWS:
        put(a, bytes(a160[a:a + 6]), "D8k")
    put(DAMPAXIS_ALPHA2[0], bytes([DAMPAXIS_ALPHA2[2]]), "D5k")
    ck(all(struct.unpack_from("<3h", code, a) == (-29490, -17202, -16000) == struct.unpack_from("<3h", a160, a) for a in DAMPAXIS_ROWS)
       and code[DAMPAXIS_ALPHA2[0]] == 14 == a160[0xC40DC], "REV 2: DampAxis rows := A160 V300's -29490,-17202,-16000 (both rows) and alpha2 14 (D8k/D5k)", "S")
    lag_a, lag_b = s16(code, 0xC63FC), u16(code, 0xC63FE)
    ck((lag_a, lag_b) == (s16(a160, 0xC63EC), u16(a160, 0xC63EE)),
       f"output lag {lag_a}/{lag_b} == the A160 V300 image's 0xC63EC/0xC63EE (DC {2 * lag_b / ((1024 - lag_a) * 32):.4f})", "S")
    ck((u16(code, 0xC61CC), u16(code, 0xC61CE), u16(code, 0xC61C8)) == (u16(a160, 0xC61BC), u16(a160, 0xC61BE), u16(a160, 0xC61BA)),
       "P / sum clamp 15360 and ICL 8192 == the A160 V300 image's 0xC61BC / 0xC61BE / 0xC61BA", "S")
    ck((u16(code, 0xC61C0), u16(code, 0xC61C2)) == (u16(a160, 0xC61B2), u16(a160, 0xC61B4)) == (3072, 3072),
       "clamps 0xC61C0/C2 == the A160 V300 image's 0xC61B2/B4 == 3072", "S")
    ck((s16(code, 0xC63F8), u16(code, 0xC63FA), u16(code, 0xC62F8), u16(code, 0xC62F6))
       == (s16(a160, 0xC63E8), u16(a160, 0xC63EA), u16(a160, 0xC62E6), u16(a160, 0xC62E4)) == (0, 8192, 65535, 0),
       "fb lag a/b/C/DB == the A160 V300 image's 0/8192/65535/0", "S")
    ck(V37A340.is_ld_hu_tp(stock, 0x29338, 0xC62F8) and len(tp_refs(stock, 0xC62F8)) == 3,
       "fb clamp C 0xC62F8 read by 3 ld.hu (unsigned: 65535 is a no-clamp, not -1)", "S")

    # ---- [5] B gain records, all 36 per table ---------------------------------------------------------------------
    print("\n  [5] B  Kp / Kd / Ki on ALL 36 records (3 speed pointer tables x 12 variants), X knots untouched")
    for nm, tabs, n, ystock, ynew in GAIN_TABLES:
        recs = ptr_records(stock, tabs)
        addrs = sorted({p for _, _, p in recs})
        ck(len(recs) == 36 and all(0xE4000 <= p < 0xE4E70 or 0xE5000 <= p < 0xE5E70 for p in addrs),
           f"{nm}: 36 pointers -> {len(addrs)} distinct records, all in the record pages", "S")
        ck(all(rec(stock, p)[0] == n and tuple(rec(stock, p)[2]) == ystock for p in addrs),
           f"{nm}: every record n == {n}, Y == stock {ystock}", "V")
        for p in addrs:
            for i in range(n):
                put(p + 2 + 2 * n + 2 * i, struct.pack("<h", ynew), "B")
        ck(all(tuple(rec(code, p)[2]) == (ynew,) * n and rec(code, p)[1] == rec(stock, p)[1] for p in addrs)
           and all(tuple(rec(code, p)[2]) == (ynew,) * n for _, _, p in ptr_records(code, tabs)) and ynew <= 0xFF,
           f"{nm}: all 36 records read back THROUGH the built pointer tables == {ynew} flat (8-bit: survives zxb/andi 0xff)", "S")
    ck(7 / 8 / 2 == 112 / 256 and (20 * 4 / 8) / 2 == 40 / 8 and 48 / 8 == 48 / 8,
       "per-unit-error equivalence with G' = G/2: Kp 7 >>3 /2 == 112/256 ; Ki ((20<<2)>>3)/2 == 40/8 ; Kd 48 == 48 (D is on r26, not G)", "C")
    ck(u16(a160, 0xC63E6) == 40 and u16(a160, u32(a160, 0xCB994 + 4 * 7) + 2 + 2 * 5) == 112,
       "A160 V300 image: Ki 0xC63E6 == 40, Kp slot 7 == 112 (the targets the re-expression mirrors)", "S")

    # ---- [6] A5 dir-2 hand fades := dir-0 values -------------------------------------------------------------------
    print("\n  [6] A5 dir-2 (camera-arm) hand-fade u8 tables := the dir-0 record values (read from the image)")
    for nm, a, tabs in FADES:
        recs = ptr_records(stock, tabs)
        addrs = sorted({p for _, _, p in recs})
        r0 = rec(stock, addrs[0])
        ck(all(rec(stock, p) == r0 for p in addrs) and r0[0] == FADE_N, f"{nm}: all {len(addrs)} dir-0 records identical, n == 6: {r0}", "V")
        n2, x2, y2 = u8tab(stock, a)
        ck(n2 == FADE_N and all(x2[i] < x2[i + 1] for i in range(5)) and y2[0] == 255,
           f"{nm}: stock u8 table 0x{a:05X} n {n2} X {x2} Y {y2}", "V")
        ck(all(0 <= v <= 255 for v in r0[1] + r0[2]), f"{nm}: dir-0 X/Y all fit u8", "S")
        put(a + 1, bytes(r0[1]) + bytes(r0[2]), "A5")
        n3, x3, y3 = u8tab(code, a)
        ck((n3, x3, y3) == (FADE_N, r0[1], r0[2]), f"{nm}: BUILT 0x{a:05X} n {n3} X {x3} Y {y3} == dir-0", "T")
        ck(code[a + 13] == stock[a + 13], f"{nm}: pad byte 0x{a + 13:05X} untouched", "S")
    ck(u8tab(code, 0xC6C10)[1] == u8tab(stock, 0xC6C10)[1], "fadeB2's X knots were already the dir-0 knots (only Y moves)", "S")

    # ---- [7] A7 EME ladder (lockstep int == f32 * 1024) ------------------------------------------------------------
    print(f"\n  [7] A7 EME soft-limit ladder -- CARRY_A7 = {CARRY_A7} (values read from the A160 V300 IMAGE)")
    for (ia, fa, ia160, fa160), si in zip(A7_PAIRS, A7_STOCK_INT):
        ck(s16(stock, ia) == si and f32(stock, fa) * 1024 == si, f"stock 0x{ia:05X} == {si}, f32 0x{fa:05X} == {f32(stock, fa)}", "V")
        if CARRY_A7:
            ni, nf = s16(a160, ia160), f32(a160, fa160)
            ck(nf * 1024 == ni and abs(ni) == 5120, f"A160 V300 0x{ia160:05X} = {ni}, f32 0x{fa160:05X} = {nf} (lockstep holds there)", "S")
            put(ia, struct.pack("<h", ni), "A7")
            put(fa, struct.pack("<f", nf), "A7")
            ck(s16(code, ia) == ni and f32(code, fa) * 1024 == ni, f"BUILT 0x{ia:05X} = {ni}, 0x{fa:05X} = {f32(code, fa)}: int == f*1024", "S")

    # ---- [8] A1 F181 ----------------------------------------------------------------------------------------------
    print("\n  [8] A1 F181 '-' -> ',' and the release letter 'C'  (0x14120 NOT touched)")
    ck(stock[0x1310D:0x1310E] == b"0" and stock[0x14117:0x14125] == b"39990-TVA-A340", "stock letter '0'; dead copy at 0x14117", "V")
    put(0x13109, b",", "A1")
    put(0x1310D, RELEASE_LETTER, "A1")
    ck(bytes(code[0x13100:0x1310E]) == b"39990-TVA,A34C" and bytes(code[0x14117:0x14125]) == b"39990-TVA-A340",
       f"F181 {bytes(code[0x13100:0x1310E])}; dead copy unchanged", "T")

    # ---- [9] CRC ---------------------------------------------------------------------------------------------------
    print("\n  [9] CRC TRAILERS")
    diff0 = {a for a in range(START, END) if code[a] != stock[a]}
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in diff0})
    print(f"      touched blocks: {[f'[0x{b0:05X},0x{b1:05X})' for b0, b1 in blocks]}")
    ck([b0 for b0, _ in blocks if 0xCE000 <= b0 < 0xDA000] == [0xD7000], "the only owning block in the base-assist pages 0xCE..0xD9 is 0xD7 (the DampAxis rows), as A160 V300 rev 2", "S")
    mid = walk_counts(code)
    ck(mid[1] == (50, len(blocks)), f"before recompute the full chain fails EXACTLY the {len(blocks)} touched blocks ({mid[1]})", "S")
    trailers = set()
    for b0, b1 in blocks:
        old = u32(code, b1)
        new = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, new)
        trailers |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:05X},0x{b1:05X}) @0x{b1:05X}: 0x{old:08X} -> 0x{new:08X}")
    wc = walk_counts(code)
    ck(wc == [(49, 0), (50, 0)], f"built CRC: bootloader replay {wc[0]} + full chain {wc[1]} (want 49/0, 50/0)", "S")

    # ---- [10] full-file diff ---------------------------------------------------------------------------------------
    print("\n  [10] FULL-FILE DIFF vs A340 STOCK over [0, 0x100000), attributed run by run")
    ck(code[:START] == stock[:START], "bootloader region [0,0x13000) untouched", "S")
    d = [i for i in range(START, END) if code[i] != stock[i]]
    unowned = [i for i in d if i not in touched and i not in trailers]
    ck(not unowned, f"{len(d)} bytes differ; every one owned by a row or a CRC trailer (unowned {[hex(i) for i in unowned[:8]]})", "S")
    low = sorted({touched.get(i) for i in d if i < 0xC0000})
    ck(low == ["A1", "A2", "A6", "D6b"], f"below 0xC0000 only rows A1 (F181), A2 (lane), A6 (repoint), D6b (gate reads) differ: {low} (the cave A3 is at 0xC4C00)", "S")
    ck(sorted({touched.get(i) for i in d if CAVE_BASE <= i < CAVE_BASE + CAVE_LEN}) == ["A3"]
       and not [i for i in d if 0xC0000 <= i < 0xC6000 and not (CAVE_BASE <= i < CAVE_BASE + CAVE_LEN) and i not in trailers
                and i != DAMPAXIS_ALPHA2[0]],
       "in [0xC0000,0xC6000) only the cave and the DampAxis alpha2 byte 0xC40D4 differ (plus the main-block trailer)", "S")
    code_runs = sorted({a for a in d if 0x14000 <= a < 0xC0000 and touched.get(a) in ("A2", "A6", "D6b")})
    ck(len(code_runs) <= 26 and sum(1 for a in code_runs if touched[a] == "D6b") == 4,
       f"in-place code bytes differing: {len(code_runs)} (9 sites, <= 26 B; D6b exactly 4)", "S")
    runs = []
    for i in d:
        if runs and i == runs[-1][1] + 1 and touched.get(i, "crc") == touched.get(runs[-1][0], "crc"):
            runs[-1][1] = i
        else:
            runs.append([i, i])
    by = {}
    for i in d:
        by[touched.get(i, "crc")] = by.get(touched.get(i, "crc"), 0) + 1
    print(f"      {len(runs)} runs; bytes by row: {dict(sorted(by.items()))}")
    for a0, a1 in runs:
        tag = touched.get(a0, "crc")
        print(f"         0x{a0:05X}-0x{a1:05X} ({a1 - a0 + 1:3d} B) [{tag:>3}]  stock {stock[a0:a1 + 1].hex()[:28]:28}"
              f"  new {bytes(code[a0:a1 + 1]).hex()[:28]}")
    d8k = {a + k for a in DAMPAXIS_ROWS for k in range(6)} | set(range(0xD7FFC, 0xD8000))
    ck(all(code[a] == stock[a] for a in range(0xCE000, 0xDA000) if a not in d8k) and sum(1 for a in d8k if code[a] != stock[a]) >= 12,
       "pages 0xCE..0xD9 byte-identical to stock incl. trailers EXCEPT the 12 DampAxis row bytes + the 0xD7 trailer (as A160 V300 rev 2)", "S")
    map_recs = {p for _, _, p in ptr_records(stock, (0xC72A4, 0xC72D4, 0xC7304))}
    ck(all(code[p:p + 42] == stock[p:p + 42] for p in map_recs), f"rate-reference map: all {len(map_recs)} records STOCK (no x6 map, as A160 V300)", "S")

    # ---- [11] delivered rail, A340 lane mirror on the BUILT image ------------------------------------------------
    print("\n  [11] DELIVERED RAIL -- the A340 lane mirror (build_v37a_a340.a340_rate_pid_tick) on the BUILT image's cells,")
    print("       forward gain re-read from the repointed cell 0xC6E88, E driven to saturation (the full-error bound)")
    cs, cn = V37A340.a340_cal(stock), V37A340.a340_cal(bytes(code))
    cn = dict(cn, gain=s16(code, TP + u16(code, 0x2A622)), out_clamp=u16(code, 0xC61C2))
    print(f"      built: Kp {cn['kp_y']} Kd {cn['kd_y']} Ki {cn['ki_y']} ICL {cn['icl']} P {cn['p_clamp']} fade {cn['fade_clamp']} "
          f"sum {cn['sum_clamp']} lag {cn['lag_a']}/{cn['lag_b']} G {cn['gain']} out {cn['out_clamp']}")
    rs = V37A340.a340_rate_pid_surface(240, cs)
    rn = V37A340.a340_rate_pid_surface(240, cn, fb=-(1 << 22))
    rn2 = V37A340.a340_rate_pid_surface(240, cn, fb=(1 << 22))
    ck(rn["S"] == cn["sum_clamp"] and rn["T"] < cn["out_clamp"],
       f"saturated: S rails at the sum clamp {rn['S']}; T = {rn['T']} < the 3072 out clamp (the clamp does not bind)", "S")
    ck(abs(rn2["T"] + rn["T"]) <= 2, f"symmetric to the floor-shift LSBs: -E saturation gives T {rn2['T']} (two >> floors toward -inf)", "S")
    print(f"      A340 stock full-demand peak T {rs['T']} ; V300-A340 rail T {rn['T']} = {rn['T'] / rs['T']:.2f} x A340 stock's peak"
          f" (A160 V300: rail 2461 = 6.0 x A160 stock's 410)")
    ck(2400 <= rn["T"] <= 2500, f"rail {rn['T']} within 2400..2500 (A160 V300's 2461 x 888/891 x lag-DC ratio ~ 2453..2473)", "S")
    rail = rn["T"]

    # ---- [12] rwd --------------------------------------------------------------------------------------------------
    print("\n  [12] .rwd ENCODE (V38 container; '/' = A310, A340, TVA,A340, TVA,A34C; '!' x4) + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 (container template)", "C")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    headers = []
    for tag, vals in info["headers"]:
        if tag == b"/":
            vals = list(VSTR)
        elif tag == b"!":
            vals = [HW_STR] * len(VSTR)
        headers.append((tag, list(vals)))
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    ck(len(info["blocks"]) == 1 and info["blocks"][0]["start"] == START and info["blocks"][0]["length"] == END - START,
       "V38 template has one block [0x13000, +0xED000)", "C")
    rwd = encode_x31(headers, info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V300-A340 output")
    back = bytearray(stock)
    back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    ck(bytes(back) == bytes(code), ".rwd decoded back is BYTE-IDENTICAL to the built image", "S")
    wc = walk_counts(back)
    ck(wc == [(49, 0), (50, 0)], f"decoded .rwd image CRC {wc[0]} + {wc[1]}", "S")
    v38 = bytearray(b"\xff" * 0x100000)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    ck(bytes(v38[START:END]) == Path(FF.V38_PLAIN).read_bytes()[START:END],
       "cipher validated NON-CIRCULARLY: V38 rwd decodes to the known V38 plain image", "S")
    got = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in parse_x31(rwd)["headers"]}
    print(f"      headers: {got}")
    ck(got.get("/") == [s.decode() for s in VSTR] and got.get("!") == [HW_STR.decode()] * 4 and got.get("&") == ["BF109E"],
       "'/' = A310, A340, TVA,A340, TVA,A34C; '!' 001100121020 x4; '&' BF109E unchanged", "T")
    ck(bytes(code[0x13100:0x1310E]).decode() in got.get("/", []), "the built F181 string is in the '/' list", "S")
    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")

    img_sha, rwd_sha = hashlib.sha256(bytes(code)).hexdigest(), hashlib.sha256(rwd).hexdigest()
    # Lens B D1 guards: pin the gain values on the BUILT image, the shared gain cell, and freeze the REV 1 image sha
    ck(u16(code, 0xC648A) == u16(stock, 0xC648A) == 888, "shared gain cell 0xC648A untouched on the built image (888)", "S")
    ck(CARRY_A7 is True, "CARRY_A7 pinned True (A160 V300 keeps A7)", "S")
    def _knots_ok(tabs, n, want):
        for t in tabs:
            for k in range(12):
                rp = u32(code, t + 4 * k)
                if u16(code, rp) != n or any(u16(code, rp + 2 + 2 * n + 2 * i) != want for i in range(n)):
                    return False
        return True
    ck(all(_knots_ok(tabs, n, want) for (_, tabs, n, _, want) in GAIN_TABLES),
       "Kp 7 / Kd 48 / Ki 20 pinned on every knot of all 36 records of each table, walked from the BUILT pointer tables", "S")
    ck(img_sha == EXP_IMG_SHA, f"REV 3 image sha frozen: {img_sha[:16]}... (expected {EXP_IMG_SHA[:16]}...)", "S")
    print("\n" + "=" * 118)
    print(f"  image SHA256 {img_sha}   ({IMG_NAME})")
    print(f"  .rwd  SHA256 {rwd_sha}   ({RWD_NAME})")
    print(f"  vs A340 stock {len(d)} B in {len(runs)} runs, {len(blocks)} CRC blocks; rail T {rail}; CARRY_A7 {CARRY_A7}")
    print(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['C']} constant-checks, "
          f"{R.census['V']} vacuous/entailed by the base hash, {R.census['T']} tautological (readback of a write)")
    print("=" * 118)
    return dict(code=bytes(code), rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, run=R, out_i=out_i, out_r=out_r)


def main():
    r = build()
    R = r["run"]
    if R.failures:
        print(f"\n  *** {len(R.failures)} FAIL(S) -- not writing ***")
        for k, m in R.failures:
            print(f"      [{k}] {m}")
        return 1
    if not WRITE:
        print("\n      DRY RUN -- NOT WRITTEN.  Set ACCORD_V300_A340_WRITE=1 to emit the files.")
        return 0
    print("\n  [13] WRITE -- guarded, re-hashed after")
    others = [p for p in Path(RWD_DIR).glob("*V300-A340*") if p.name != RWD_NAME]
    if others:
        raise SystemExit(f"WRITE GUARD: another V300-A340 rwd exists: {[p.name for p in others]}")
    for path, blob, sha in ((r["out_i"], r["code"], r["img_sha"]), (r["out_r"], r["rwd"], r["rwd_sha"])):
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, f"existing {path} differs!"
            print(f"      [PASS] already on disk and matches: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "xb") as fh:
                fh.write(blob)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
            print(f"      [PASS] written: {path}\n             sha256 {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
