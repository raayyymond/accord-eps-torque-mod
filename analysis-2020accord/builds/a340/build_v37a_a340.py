# -*- coding: utf-8 -*-
r"""builds/a340/build_v37a_a340.py -- V37A REV 3 ("PTM-lite", the 2x mod) PORTED TO 39990-TVA-A340.  REV 3.

=== REV 3 (2026-11-01, adversarial Lens C FAIL, orchestrator-verified) ============================
REV 2 forced the DTC-0x49 gate byte 0xC6508 to 0xFF as A160 V37 does.  On A340 that SAME byte is also the driver-override
cutoff: the lane compares the hand-torque index gp-0x67f5 against it at 0x2A076 (`cmp r11,r15 ; cmovh 0,r10,r10 ; bnh`) and
zeroes the LKAS demand index when the hand pushes harder.  On A160 the B-type fade records reach Y = 0 at X = 112, so the
gate was redundant there; on A340 those records stay at 255 (ptr tables 0xC7694/0xC76C4) and the byte is the ONLY cutoff.
REV 3 leaves 0xC6508 at STOCK (112): the override cutoff stays exactly Honda's.  Consequence: the soft DTC-0x49 counter that
the same byte gates (0x2961C/0x2962E) also stays live, i.e. the V37 mask is NOT ported -- a DTC 0x49 may log under 2x
authority as it did on A160 V36.  REV 2 (image 4a9c8cd4..., rwd 11a78b8f...) is deleted from disk.

=== REV 2 (2026-11-01, orchestrator decision) =====================================================
REV 1 set both output clamps to 1024 (A160's value).  On A340 that made the full-demand torque clamp-bound at 1024 =
2.28x the stock A340 peak (450), not 2x.  REV 2 sets the lane output clamp 0xC61C2 and the limit&pack clamp 0xC61C0 to
900 = 2 x 450: the rail is clamp-bound at EXACTLY 2x stock's peak, and the sub-rail slope stays 2x via gain 1776.
REV 1 (image 0b7731e4..., rwd d7d71528...) is deleted from disk.

SHARED GAIN CELL: 0xC648A has 6 tp readers on A340 -- the lane 0x2A620, its uncalled twin 0x2B46A, and FOUR NON-LANE
readers 0x2C1D8, 0x2D00A, 0x37208, 0x373CC.  Doubling the cell doubles all four, exactly as A160 V37 does with its
shared 0xC646C (6 readers there too).  The four consumers' functions are UNTRACED -- flagged for the adversarial pass.

STUDY BUILD.  A built image on disk is not a flash.  Nothing here sends anything to a car; flashing is gated on the
operator naming the file and the bus.  Files are written ONLY with ACCORD_V37A_A340_WRITE=1 (default: dry run).

BASE = A340 STOCK (sha256 01a53539...), NOT an A160 image.  The two firmwares are different compiles: no address
carries over.  Every A340 address below was re-found by FUNCTION by the T1a (LKAS lane) and T1c (interlocks) tracers
and is asserted here against the A340 stock bytes before it is written.

THE EDITS (A160 V37A rev 3 -> A340):
  (a) forward gain     A160 0xC646C 891->1782   ->  A340 0xC648A 888 -> 1776   (lane reader ld.h 0x748a[tp] @0x2A620)
  (b) lane out clamp   A160 0xC61B4 512->1024   ->  A340 0xC61C2 512 -> 900  (REV 2; = 2 x the stock A340 peak 450)
      limit&pack clamp A160 0xC61B2 512->1024   ->  A340 0xC61C0 512 -> 900  (FUN_0002bfa4)
  (c) rate-reference map: A160 28 records via 0xC9A88 -> A340 36 records via THREE speed pointer tables
      0xC72A4 / 0xC72D4 / 0xC7304 (12 variants each), blended into RAM gp-0x635c/-0x6348 by FUN_0002a740.
      n = 10, X 0,6,16,35,53,77,102,127,160,240 (untouched); Y[i] := round-half-up(2*Ytop*X[i]/240), Ytop = the
      record's own stock top (187 -> 374 at X = 240).  Stock Y 0,17,41,69,91,119,142,165,187,187.
  (d) feedback clamp   A160 0xC62E6 7680->15360 ->  A340 0xC62F8 7680 -> 15360 (3 ld.hu readers 0x29338/3E/5A)
  (e) STEER_STATUS debounce package: 0xC61D0/D2/D4 -> 0xFFFF x3; 0xC6504..07 -> 0xFF x4; DTC-0x49 gate 0xC6508 -> 0xFF
  (f) EME ramp step 0xC652E 17 -> 27
  (g) EME corridor x4 + boost floor 4096, int16 AND f32 mirrors together (lockstep: int == float*1024)
  (h) part-number '-' -> ',' at 0x13109 and 0x14120  (F181 becomes 39990-TVA,A340)

A340-SPECIFIC STRUCTURE THE PORT HAS TO RESPECT (T1a, EVIDENCE; see the surface mirror below):
  * P = (E*Kp)>>3 with Kp 8-bit (A160: >>8, 16-bit Kp).  Stock Kp Y 10,15,19,21,21 at X 0,68,112,136,208.
  * stock ICL 0xC61C8 = 0 and Ki = 0 on all 36 records: I == 0 identically.
  * P clamp 0xC61CC = 20480, an extra post-fade clamp 0xC61CA = 20476, sum clamp 0xC61CE = 20480.
  * output lag a/b 0xC63FC/0xC63FE = 1005/324: DC gain 2b/((1024-a)*32) = 1.0658 (A160: 0.990).
  * forward gain 0xC648A is SHARED: 6 tp readers (lane 0x2A620, twin 0x2B46A, 0x2C1D8, 0x2D00A, 0x37208, 0x373CC).
    A160's 0xC646C has the matching 6 and V37 doubled it there too; the other four consumers move with it.

CONSEQUENCE, READ FROM THE BUILT IMAGE BY THE MIRROR (printed below):
  stock A340 tops out UNDER its 512 clamp at 450 (P 15708 < 20480).  With gain 1776 the unclamped stalled-wheel bound
  would reach ~1173 (P rails at 20480 -> S 20320 -> y ~21.6k -> (y*1776)>>15).  REV 2's 900 clamp binds first, so the
  full-demand torque is EXACTLY 900 = 2x stock's peak; the idx where it becomes clamp-bound is printed.  (A160 V37A:
  rail 820 = 2x 410, under its 1024 clamp.)
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
from firmware_paths import plain_image_path, RWD_DIR                   # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                               # noqa: E402
import eps_lkas_chain_model as GM                                                     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE = os.environ.get("ACCORD_V37A_A340_WRITE", "").strip() == "1"
MAX_PATH = 259

FW_ROOT = Path(os.environ["ACCORD_FIRMWARE_ROOT"])
A340_PATH = FW_ROOT / "analysis-2020accord" / "other bins" / "39990-TVA-A340.bin"
A340_SHA = "01a53539e19bb0b54fb339a08644ca6981b844fad41276a1f8c305f13aa6f071"
A160_STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"
A160_V37A_NAME = "_v37a_REV3_plain_image.bin"

LABEL = "V37A-A340-REV3"
TAG = "MAP.LINE.2XTOP374-GAIN1776-CLAMPS900-FBCLAMP15360-V36PKG.DTCGATE.STOCK"
IMG_NAME = "_v37a_a340_REV3_plain_image.bin"
RWD_NAME = f"39990-TVA,A340-{LABEL}-{TAG}-0x{START:X}-0x{END:X}.rwd"
VSTR = [b"39990-TVA-A310", b"39990-TVA-A340", b"39990-TVA,A340"]
HW_STR = b"001100121020"

# ---- the edit table (A340 addresses, stock value, new value) -------------------------------------------------------
GAIN = (0xC648A, 888, 1776)
OUT_CLAMP = (0xC61C2, 512, 900)
LP_CLAMP = (0xC61C0, 512, 900)
FB_CLAMP = (0xC62F8, 7680, 15360)
DEBOUNCE_U16 = [(0xC61D0, 12800, 0xFFFF), (0xC61D2, 8960, 0xFFFF), (0xC61D4, 11520, 0xFFFF)]
DEBOUNCE_U8 = [(0xC6504, 112, 0xFF), (0xC6505, 96, 0xFF), (0xC6506, 54, 0xFF), (0xC6507, 64, 0xFF)]
DTC_GATE = (0xC6508, 112)   # REV 3: LEFT AT STOCK -- it is also the driver-override cutoff on A340 (Lens C)
EME_STEP = (0xC652E, 17, 27)
# EME corridor + boost floor: (int16 addr, f32 addr, stock int, new int)  -- lockstep pairs int == f32*1024
EME_PAIRS = [(0xC679E, 0xC65E8, 1024, 4096), (0xC67A0, 0xC65EC, 1024, 4096),
             (0xC67AA, 0xC65FC, -1024, -4096), (0xC67AC, 0xC6600, -1024, -4096),
             (0xC67B8, 0xC6614, 0, 4096), (0xC67BA, 0xC6618, 1536, 4096), (0xC67BC, 0xC661C, 2048, 4096)]
PN_BYTES = (0x13109, 0x14120)
PN_STRINGS = (0x13100, 0x14117)                                      # the two 14-byte '39990-TVA-A340' copies

MAP_PTR_TABS = (0xC72A4, 0xC72D4, 0xC7304)                           # low / mid / high speed, 12 variants each
MAP_N, MAP_YOFF = 10, 0x16
MAP_X = (0, 6, 16, 35, 53, 77, 102, 127, 160, 240)
MAP_Y_STOCK = (0, 17, 41, 69, 91, 119, 142, 165, 187, 187)
MAP_Y_NEW = (0, 9, 25, 55, 83, 120, 159, 198, 249, 374)             # round-half-up(2*187*X/240), asserted below
KP_TABS, KD_TABS, KI_TABS = (0xC77E4, 0xC78D4, 0xC79C4), (0xC7784, 0xC7874, 0xC7964), (0xC77B4, 0xC78A4, 0xC7994)
N_VAR = 12

# in-place code bytes the edits depend on (asserted stock, never written)
GAIN_SITE = (0x2A620, bytes.fromhex("255f8a74"))                     # ld.h 0x748a[tp],r11
FB_SITES = (0x29338, 0x2933E, 0x2935A)                               # ld.hu 0x72f8[tp]
# T1a raw tp-scan reader counts, re-scanned here (positive control 0xC62F8 = 3)
READER_COUNTS = {0xC648A: 6, 0xC61C2: 8, 0xC61C0: 5, 0xC62F8: 3}

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


u8 = lambda b, a: b[a]                                              # noqa: E731
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]                # noqa: E731
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]                # noqa: E731
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]                # noqa: E731
f32 = lambda b, a: struct.unpack_from("<f", b, a)[0]                # noqa: E731


def rec(b, p):
    n = u16(b, p)
    return n, [s16(b, p + 2 + 2 * i) for i in range(n)], [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def line_y(ytop, x):
    """Y'[i] = round-half-up(2 * Ytop * X[i] / 240): straight line from the origin to TWICE the record's stock top."""
    return (2 * ytop * x * 2 + 240) // 480


def walk_counts(img):
    """(checked, fails) for the bootloader replay and the full chain, parsed from the kit verifier's own output."""
    out = []
    for fn in (walk, walk_all_blocks):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fails = fn(bytes(img))
        line = [ln for ln in buf.getvalue().splitlines() if "result:" in ln][-1]
        checked = int(line.split("result:")[1].split("block")[0])
        out.append((checked, fails))
    return out


def tp_readers(img, cell):
    """Raw LE scan of [0x13000,0xC0000) for 4-byte Format VII tp-relative loads of `cell` (tp = 0xBF000, reg1 = r5):
    ld.b 0x38, ld.h/ld.w 0x39, ld.bu 0x3C/0x3D (disp bit 0 in hw1 bit 5), ld.hu 0x3F.  hw2 carries disp with bit 0
    as the W/H or U selector, so compare hw2 & 0xFFFE (firmware-decompile skill)."""
    disp = cell - 0xBF000
    hits = []
    for a in range(0x13000, 0xC0000, 2):
        hw1 = img[a] | (img[a + 1] << 8)
        if hw1 & 0x1F != 5:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in (0x38, 0x39, 0x3C, 0x3D, 0x3F):
            continue
        hw2 = img[a + 2] | (img[a + 3] << 8)
        if (hw2 & 0xFFFE) == (disp & 0xFFFE):
            hits.append(a)
    return hits


def is_ld_hu_tp(img, a, cell):
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    return ((hw1 >> 5) & 0x3F) == 0x3F and (hw1 & 0x1F) == 5 and (hw2 & 1) == 1 and (hw2 & 0xFFFE) == cell - 0xBF000


def map_records(img):
    """[(table, variant, record address)] for all 36 pointers, read from the image's own pointer tables."""
    return [(t, v, u32(img, t + 4 * v)) for t in MAP_PTR_TABS for v in range(N_VAR)]


# =====================================================================================================================
#  THE A340 SURFACE MIRROR -- integer Python, line for line with FUN_00029230's PID section (A340 addresses)
# =====================================================================================================================
def a340_lerp(X, Y, x):
    """The lane's RAM-table LERP walk (e.g. map @0x2A2D0..0x2A332): signed compares (bgt/bge), flat below X[0] and
    above X[n-1]; Y[i] + ((Y[i+1]-Y[i])*(x-X[i])) divq (X[i+1]-X[i]) -- divq truncates toward zero."""
    if x <= X[0]:                                   # 0x2A2E6 cmp r7,r16 ; bgt -> else ld.h -0x6348 (Y[0])
        return Y[0]
    if x >= X[-1]:                                  # 0x2A2F8 cmp r10,r16 ; bge -> ld.h -0x6336 (Y[9])
        return Y[-1]
    i = 0
    while x >= X[i + 1]:                            # 0x2A30C..0x2A314 walk
        i += 1
    num, den = (Y[i + 1] - Y[i]) * (x - X[i]), X[i + 1] - X[i]     # 0x2A322 sub ; 0x2A328 mul ; 0x2A32C sub
    q = abs(num) // abs(den)
    return Y[i] + (-q if (num < 0) != (den < 0) else q)            # 0x2A32E divq ; 0x2A332 add


def a340_cal(img):
    """Every cell the mirror reads, from THIS image.  Variant 0, low-speed record (all 36 asserted identical)."""
    p = lambda t: u32(img, t)                       # noqa: E731
    _, mx, my = rec(img, p(MAP_PTR_TABS[0]))
    _, kx, ky = rec(img, p(KP_TABS[0]))
    _, dx, dy = rec(img, p(KD_TABS[0]))
    _, ix, iy = rec(img, p(KI_TABS[0]))
    return dict(map_x=mx, map_y=my, kp_x=kx, kp_y=ky, kd_x=dx, kd_y=dy, ki_x=ix, ki_y=iy,
                db=u16(img, 0xC62F6), icl=u16(img, 0xC61C8), p_clamp=u16(img, 0xC61CC), d_clamp=u16(img, 0xC61C4),
                fade_clamp=u16(img, 0xC61CA), sum_clamp=u16(img, 0xC61CE), lag_a=s16(img, 0xC63FC),
                lag_b=u16(img, 0xC63FE), gain=s16(img, GAIN[0]), out_clamp=u16(img, OUT_CLAMP[0]),
                fb_clamp=u16(img, FB_CLAMP[0]))


def clamp(v, lim):
    return max(-lim, min(lim, v))


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def sxh(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class A340State:
    def __init__(self):
        self.i_cell = 0          # gp-0x6da0 (holds 8*I), .data boot 0
        self.prev_e = 0          # gp-0x6cc8 (E_prev for D)
        self.lag_s = 0           # gp-0x3c9c (output-lag state)


def a340_rate_pid_tick(idx, st, cal, fb=0, pol=1, ramp=0x8000, fade=(255, 255)):
    """One engaged tick of the A340 LKAS rate PID, sp former to the lane-torque store.  Hands-off fades = 255/255."""
    gidx = idx                                       # 0x29F4A ld.bu -0x6711 (last tick's idx; == idx on a hold)
    kd = a340_lerp(cal["kd_x"], cal["kd_y"], gidx) & 0xFF      # 0x29FAC mov r13,r21 ; 0x29FB4 zxb r21
    kp = a340_lerp(cal["kp_x"], cal["kp_y"], gidx) & 0xFF      # 0x2A00A mov r10,r27 ; 0x2A010 zxb r27
    ki = a340_lerp(cal["ki_x"], cal["ki_y"], gidx) & 0xFF      # 0x2A06C andi 0xff,r8,r29
    mag = a340_lerp(cal["map_x"], cal["map_y"], idx)           # 0x2A2D0..0x2A332 (RAM map gp-0x635c/-0x6348)
    sp = sxh(pol * mag)                                         # 0x2A2E2 cmovlt -1 ; 0x2A334 mov ; 0x2A336 mulh r11,r9
    E = s32((sp << 5) - fb)                                     # 0x2A340 shl 0x5,r9 ; 0x2A342 sub r26,r9
    # ---- I : deadband on E>>5, Ki (8-bit) with an extra shl 2, accumulator holds 8*I, clamp (ICL<<10)>>3
    e5 = E >> 5                                                 # 0x2A344 mov ; 0x2A346 sar 0x5,r13
    db = cal["db"]                                              # 0x2A338 ld.hu 0x72f6[tp] (0xC62F6)
    exc = (e5 - db) if e5 > db else ((e5 + db) if e5 < -db else 0)     # 0x2A348..0x2A364
    inc = ((exc * ki) << 2) >> 3                                # 0x2A366 mul r29,r7 ; 0x2A372 shl 2 ; 0x2A378 sar 3
    acc = (st.i_cell >> 3) + inc                                # 0x2A36E ld.w -0x6da0 ; 0x2A376 sar 3 ; 0x2A37A add
    icl = (cal["icl"] << 10) >> 3                               # 0x2A36A ld.hu 0x71c8 ; 0x2A374 shl 0xa ; 0x2A37C sar 3
    I = icl if acc > icl else (-icl if acc <= -icl else acc)    # 0x2A37E..0x2A38A cmovgt / cmovle
    # ---- P
    P = clamp((E * kp) >> 3, cal["p_clamp"])                    # 0x2A390 mul r27,r10 ; 0x2A39C sar 3 ; 0x2A39E.. 0xC61CC
    # ---- D : E_prev plausibility window +-768000, full-error difference
    r10 = st.prev_e if -768000 <= st.prev_e <= 768000 else E    # 0x2A3B6..0x2A3D0 cmovnc r9,r10,r10
    D = clamp((s32(E - r10) * kd) >> 3, cal["d_clamp"])         # 0x2A3D4 subr ; 0x2A3D6 mul r21 ; 0x2A3DA sar 3 ; 0xC61C4
    # ---- sum, hand fade (taper), post-fade clamp, sum clamp
    S = s32((I >> 7) + P + D)                                   # 0x2A3F8 sar 7,r11 ; 0x2A3FE add r7 ; 0x2A40A add r10
    taper = ((fade[0] * fade[1]) & 0xFFFF) >> 8                 # 0x2A4C6 mulh r16,r1 ; 0x2A4CC andi 0xffff ; 0x2A4D0 sar 8
    S = s32((S * taper) >> 8)                                   # 0x2A4D2 mul r11,r13 ; 0x2A4D6 sar 8
    S = clamp(S, cal["fade_clamp"])                             # 0x2A4D8..0x2A4F2 (0xC61CA)
    S = sxh(clamp(S, cal["sum_clamp"]))                         # 0x2A570..0x2A594 (0xC61CE), sxh
    # ---- output lag (two-sample sum, >>5)
    s = st.lag_s
    s_new = s32(((cal["lag_a"] * s) >> 10) + ((S * cal["lag_b"]) >> 10))   # 0x2A5BA/0x2A5BE mul ; sar 0xa x2 ; add
    y = s32((s + s_new) >> 5)                                   # 0x2A5D4 add r8,r15 ; 0x2A5D6 sar 0x5
    st.lag_s = s_new                                            # 0x2A5D8 st.w r8,-0x3c9c
    st.i_cell = s32(I << 3)                                     # 0x2A394 mov r11,lp ; 0x2A39A shl 3 ; 0x2A5CC st.w
    st.prev_e = E                                               # 0x2A5E2 st.w r9,-0x6cc8
    # 0x2A5DC: the |y|<=102 zeroing gate needs gp-0x67cc == 0 (NOT engaged) -- skipped on the engaged path
    yr = sxh((y * ramp) >> 15)                                  # 0x2A618 mul r14,r15 ; 0x2A61C sar 0xf ; sxh
    g = sxh(pol * cal["gain"])                                  # 0x2A620 ld.h 0x748a[tp] ; 0x2A624 ld.b -0x6718 ; mulh
    addend = 0                                                  # r12 = gp-0x6afc: LERP of 0xC6784 whose Y are all 0
    T = clamp(((addend + yr) * g) >> 15, cal["out_clamp"])      # 0x2A62E add ; 0x2A630 mul ; 0x2A634 sar 0xf ; 0xC61C2
    return dict(sp=sp, E=E, kp=kp, P=P, D=D, I=I, S=S, y=y, T=T)  # 0x2A66E st.h r1,-0x6b08[gp]


def a340_rate_pid_surface(idx, cal, fb=0, max_ticks=200000):
    """Stalled-wheel bound (fb = 0 held), marched from the cold-boot state until the lag state repeats."""
    st, seen, last = A340State(), set(), None
    for _ in range(max_ticks):
        key = (st.lag_s, st.prev_e, st.i_cell)
        if key in seen:
            break
        seen.add(key)
        last = a340_rate_pid_tick(idx, st, cal, fb=fb)
    return last


# =====================================================================================================================
def build():
    R = Run()
    ck = R.check
    print("=" * 118)
    print(f"  {LABEL}: V37A rev 3 (2x torque + rate-reference line to 2x top + fb clamp 2x + V37 package) ported to A340")
    print("=" * 118)

    stock = open(A340_PATH, "rb").read()
    print("\n  [0] BASE")
    ck(len(stock) == 0x100000 and hashlib.sha256(stock).hexdigest() == A340_SHA,
       f"A340 stock image sha256 {A340_SHA[:16]}... (1 MB)", "C")
    ck(stock[0x13100:0x1310E] == b"39990-TVA-A340", "F181 string at 0x13100 == 39990-TVA-A340 (this is the A340 image)", "V")
    wc = walk_counts(stock)
    ck(wc == [(49, 0), (50, 0)], f"stock CRC: bootloader replay {wc[0][0]} blocks/{wc[0][1]} fail, full chain "
       f"{wc[1][0]}/{wc[1][1]} (want 49/0 and 50/0)", "V")
    code = bytearray(stock)
    touched = {}                                     # addr -> edit id (for diff attribution)

    def put16(a, v, tag, signed=False):
        struct.pack_into("<h" if signed else "<H", code, a, v)
        for k in (0, 1):
            touched[a + k] = tag

    # ---- [1] the lane's gain / clamps --------------------------------------------------------------------------
    print("\n  [1] (a)(b) FORWARD GAIN AND THE TWO CLAMPS")
    ck(stock[GAIN_SITE[0]:GAIN_SITE[0] + 4] == GAIN_SITE[1],
       "0x2A620 == 25 5f 8a 74 (ld.h 0x748a[tp],r11): the lane reads its forward gain from 0xC648A (no decouple)", "V")
    for cell, want in READER_COUNTS.items():
        hits = tp_readers(stock, cell)
        ck(len(hits) == want, f"raw tp scan: 0x{cell:05X} has {len(hits)} 4-byte loads (T1a: {want}) "
           f"{[hex(h) for h in hits]}", "S")
    for (a, sv, nv), nm in ((GAIN, "forward gain"), (OUT_CLAMP, "lane output clamp"), (LP_CLAMP, "limit&pack clamp")):
        ck(u16(stock, a) == sv, f"stock 0x{a:05X} == {sv} ({nm})", "V")
        put16(a, nv, "a/b")
        ck(u16(code, a) == nv, f"0x{a:05X} {sv} -> {nv} ({nm})", "T")
    ck(u16(code, GAIN[0]) == 2 * u16(stock, GAIN[0]), "gain exactly 2x the STOCK image's value (888 -> 1776)", "S")
    ck(u16(code, LP_CLAMP[0]) == u16(code, OUT_CLAMP[0]) and u16(code, LP_CLAMP[0]) != u16(stock, LP_CLAMP[0]),
       "limit&pack clamp == lane output clamp on the built image, and moved from stock (Lens B D1 guard)", "S")

    # ---- [2] the map, all 36 records ---------------------------------------------------------------------------
    print("\n  [2] (c) RATE-REFERENCE MAP -> straight line to 2x the stock top, all records of all three speed tables")
    recs = map_records(stock)
    addrs = sorted({p for _, _, p in recs})
    ck(all(0xE4000 <= p < 0xE6000 for p in addrs), f"{len(recs)} pointers -> {len(addrs)} DISTINCT records, all in "
       f"[0xE4000,0xE6000)", "S")
    ck(all(rec(stock, p)[0] == MAP_N and tuple(rec(stock, p)[1]) == MAP_X for p in addrs), "every record n == 10, X == stock", "V")
    ck(all(tuple(rec(stock, p)[2]) == MAP_Y_STOCK for p in addrs), f"every record Y == stock {MAP_Y_STOCK}", "V")
    ck(all(stock[p:p + 2 + 4 * MAP_N] == stock[addrs[0]:addrs[0] + 2 + 4 * MAP_N] for p in addrs),
       "all distinct records are byte-identical on stock (so variant / speed blend cannot select a different line)", "V")
    ck(tuple(line_y(187, x) for x in MAP_X) == MAP_Y_NEW, f"formula gives {MAP_Y_NEW} for Ytop 187", "S")
    for p in addrs:
        n, X, Y = rec(stock, p)
        new = [line_y(Y[-1], x) for x in X]
        for i in range(1, n):                         # Y[0] untouched
            put16(p + 2 + 2 * n + 2 * i, new[i], "c", signed=True)
        _, gX, gY = rec(code, p)
        ok = (gX == X and gY == new and gY[0] == 0 and all(gY[i + 1] > gY[i] for i in range(n - 1))
              and max(gY) < 32767 and gY[-1] == 2 * Y[-1])
        ck(ok, f"rec 0x{p:05X}: Y {Y} -> {gY}", "T")
    for v in range(N_VAR):
        ys = [tuple(rec(code, u32(code, t + 4 * v))[2]) for t in MAP_PTR_TABS]
        ck(len(set(ys)) == 1, f"variant {v:2d}: low/mid/high-speed records identical after the edit -> FUN_0002a740's "
           f"blend a+(b-a)*t/dt is exact", "V")
    sp_new = [a340_lerp(MAP_X, MAP_Y_NEW, i) for i in range(241)]
    dev = max(abs(sp_new[i] - 374 * i / 240) for i in range(241))
    ck(dev < 4.0 and sp_new[240] == 374 and all(sp_new[i + 1] >= sp_new[i] for i in range(240)),
       f"integer LERP walk: monotone, 374 at idx 240, within {dev:.2f} counts of the line 374*idx/240", "S")
    ck(all(a340_lerp(MAP_X, MAP_Y_STOCK, i) == GM.lkas_rate_lerp(MAP_X, MAP_Y_STOCK, i) for i in range(241))
       and all(a340_lerp(MAP_X, MAP_Y_NEW, i) == GM.lkas_rate_lerp(MAP_X, MAP_Y_NEW, i) for i in range(241)),
       "A340 LERP mirror == golden-model lkas_rate_lerp at all 241 idx (two implementations)", "S")

    # ---- [3] fb clamp ------------------------------------------------------------------------------------------
    print("\n  [3] (d) FEEDBACK CLAMP")
    a, sv, nv = FB_CLAMP
    ck(u16(stock, a) == sv, f"stock 0x{a:05X} == {sv}", "V")
    ck(all(is_ld_hu_tp(stock, s, a) for s in FB_SITES), f"readers {[hex(s) for s in FB_SITES]} are ld.hu 0x72f8[tp] (unsigned)", "V")
    put16(a, nv, "d")
    ck(nv / (32 * 374) == sv / (32 * 187), f"setpoint:feedback ratio held: {sv}/(32*187) == {nv}/(32*374) = {sv / (32 * 187):.4f}", "S")

    # ---- [4] V37 package: debounce, DTC gate, EME step ---------------------------------------------------------
    print("\n  [4] (e)(f) STEER_STATUS DEBOUNCE PACKAGE, DTC-0x49 GATE, EME RAMP STEP")
    for a, sv, nv in DEBOUNCE_U16:
        ck(u16(stock, a) == sv, f"stock 0x{a:05X} == {sv}", "V")
        put16(a, nv, "e")
    for a, sv, nv in DEBOUNCE_U8 + [EME_STEP]:
        ck(stock[a] == sv, f"stock 0x{a:05X} == {sv}", "V")
        code[a] = nv
        touched[a] = "e" if a != EME_STEP[0] else "f"
    ck(all(u16(code, a) == 0xFFFF for a, _, _ in DEBOUNCE_U16) and all(code[a] == 0xFF for a, _, _ in DEBOUNCE_U8)
       and code[EME_STEP[0]] == 27, "debounce 0xFFFF x3, 0xFF x4, EME step 27", "T")
    ck(code[DTC_GATE[0]] == DTC_GATE[1] == stock[DTC_GATE[0]], "REV 3: DTC-0x49 gate / override cutoff 0xC6508 == STOCK 112 (untouched)", "S")

    # ---- [5] EME corridor + boost floor, lockstep pairs ---------------------------------------------------------
    print("\n  [5] (g) EME CORRIDOR x4 + BOOST FLOOR 4096 (int16 + f32 mirrors)")
    for ia, fa, si, ni in EME_PAIRS:
        ck(s16(stock, ia) == si and f32(stock, fa) * 1024 == si,
           f"stock int 0x{ia:05X} == {si} and f32 0x{fa:05X} == {f32(stock, fa)} (lockstep int == f*1024 holds on stock)", "V")
        put16(ia, ni, "g", signed=True)
        struct.pack_into("<f", code, fa, ni / 1024.0)
        for k in range(4):
            touched[fa + k] = "g"
        ck(s16(code, ia) == ni and f32(code, fa) * 1024 == ni, f"0x{ia:05X} -> {ni}, 0x{fa:05X} -> {ni / 1024.0}: "
           f"lockstep int == f*1024 AFTER the edit", "S")

    # Lens B D1 guards: re-derive the targets from the STOCK image, not from this script's constants
    cor = EME_PAIRS[:4]
    bst = EME_PAIRS[4:]
    ck(all(s16(code, ia) == 4 * s16(stock, ia) and f32(code, fa) == 4.0 * f32(stock, fa) for ia, fa, _, _ in cor),
       "corridor: every int AND f32 cell == 4 x the STOCK image's value (x4 re-derived, not a constant)", "S")
    top = 2 * max(s16(stock, ia) for ia, _, _, _ in bst)
    ck(all(s16(code, ia) == top and f32(code, fa) * 1024 == top for ia, fa, _, _ in bst) and top == 4096,
       f"boost floor: every int AND f32 cell == 2 x the STOCK max boost ({top}; floor flat at 4096)", "S")

    # ---- [6] part number ---------------------------------------------------------------------------------------
    print("\n  [6] (h) PART-NUMBER BYTES")
    for s0 in PN_STRINGS:
        ck(stock[s0:s0 + 14] == b"39990-TVA-A340", f"stock 0x{s0:05X} == 39990-TVA-A340", "V")
    for a in PN_BYTES:
        code[a] = ord(",")
        touched[a] = "h"
    ck(all(code[s0:s0 + 14] == b"39990-TVA,A340" for s0 in PN_STRINGS) and code.count(b"39990-TVA,A340") == 2
       and code.count(b"39990-TVA-A340") == stock.count(b"39990-TVA-A340") - 2,
       f"both copies now 39990-TVA,A340; '39990-TVA-A340' occurrences {stock.count(b'39990-TVA-A340')} -> "
       f"{code.count(b'39990-TVA-A340')}", "T")

    # ---- [7] CRC -----------------------------------------------------------------------------------------------
    print("\n  [7] CRC TRAILERS")
    blocks = sorted({V53.owning_block(code, a) for a in touched})
    print(f"      touched blocks: {[f'[0x{b0:05X},0x{b1:05X})' for b0, b1 in blocks]}")
    mid = walk_counts(code)
    ck(mid[1] == (50, len(blocks)), f"before recompute the full chain fails EXACTLY the {len(blocks)} touched blocks "
       f"({mid[1][1]} of {mid[1][0]})", "S")
    trailers = set()
    for b0, b1 in blocks:
        old = u32(code, b1)
        new = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, new)
        trailers |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:05X},0x{b1:05X}) @0x{b1:05X}: 0x{old:08X} -> 0x{new:08X}")
    wc = walk_counts(code)
    ck(wc == [(49, 0), (50, 0)], f"built CRC: bootloader replay {wc[0][0]}/{wc[0][1]} fail, full chain "
       f"{wc[1][0]}/{wc[1][1]} fail", "S")

    # ---- [8] full-file diff ------------------------------------------------------------------------------------
    print("\n  [8] FULL-FILE DIFF vs A340 STOCK over [0x13000, 0x100000)")
    d = [i for i in range(START, END) if code[i] != stock[i]]
    unowned = [i for i in d if i not in touched and i not in trailers]
    ck(not unowned, f"{len(d)} bytes differ; every one owned by an edit (a)-(h) or a CRC trailer (unowned: "
       f"{[hex(i) for i in unowned[:8]]})", "S")
    low = sorted(i for i in d if i < 0xC0000)
    ck(low == sorted(PN_BYTES), f"below 0xC0000 exactly the two part-number bytes differ: {[hex(i) for i in low]}", "S")
    ck(code[:START] == stock[:START], "bootloader region [0,0x13000) untouched", "S")
    runs = []
    for i in d:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    by = {}
    for i in d:
        k = touched.get(i, "crc")
        by[k] = by.get(k, 0) + 1
    print(f"      {len(runs)} runs; bytes by edit: {dict(sorted(by.items()))}")
    for a0, a1 in runs:
        tag = touched.get(a0, "crc")
        print(f"         0x{a0:05X}-0x{a1:05X} ({a1 - a0 + 1:3d} B) [{tag:>3}]  stock {stock[a0:a1 + 1].hex()[:28]:28}"
              f"  new {bytes(code[a0:a1 + 1]).hex()[:28]}")
    gain_recs = {u32(stock, t + 4 * v) for t in KP_TABS + KD_TABS + KI_TABS for v in range(N_VAR)}
    ck(all(code[p:p + 2 + 4 * u16(stock, p)] == stock[p:p + 2 + 4 * u16(stock, p)] for p in gain_recs),
       f"Kp/Kd/Ki: all {len(gain_recs)} distinct records untouched", "S")

    # ---- [9] the delivered surface ------------------------------------------------------------------------------
    print("\n  [9] DELIVERED SURFACE (fb = 0 stalled-wheel BOUND, hands-off fade 255/255 -> taper 254, ramp 0x8000,")
    print("      cold-boot march) -- A340 mirror read from the A340 images; A160 from the golden model on the A160 images")
    idxs = (0, 6, 12, 24, 32, 48, 60, 64, 96, 120, 160, 200, 238, 240)
    cs, cn = a340_cal(stock), a340_cal(bytes(code))
    for nm, c in (("stock", cs), ("V37A-A340", cn)):
        print(f"      {nm:9}: Kp {c['kp_y']} @ {c['kp_x']}  Kd {c['kd_y']}  Ki {c['ki_y']}  ICL {c['icl']}  "
              f"clamps P {c['p_clamp']} fade {c['fade_clamp']} sum {c['sum_clamp']}  lag {c['lag_a']}/{c['lag_b']}  "
              f"G {c['gain']}  out {c['out_clamp']}  fb {c['fb_clamp']}")
    SA = {i: a340_rate_pid_surface(i, cs) for i in idxs}
    SB = {i: a340_rate_pid_surface(i, cn) for i in idxs}
    a160 = open(FW_ROOT / "analysis-2020accord" / "stock_fw_dump" / "code.bin", "rb").read()
    ck(hashlib.sha256(a160).hexdigest() == A160_STOCK_SHA, "A160 stock image sha256 3f1d55a9...", "C")
    a160v = open(plain_image_path(A160_V37A_NAME), "rb").read()
    print(f"      A160 V37A image {A160_V37A_NAME} sha256 {hashlib.sha256(a160v).hexdigest()}")
    import build_v37a_tva as A160V37A                                                  # noqa: E402
    ca, cb = A160V37A.cal_for(a160), A160V37A.cal_for(a160v)
    GA = {i: GM.lkas_rate_pid_surface(i, ca) for i in idxs}
    GB = {i: GM.lkas_rate_pid_surface(i, cb) for i in idxs}
    print("        idx | A340 stock  sp      P     T | A340 V37A  sp      P     T || A160 stock  sp      P    T |"
          " A160 V37A  sp      P    T")
    for i in idxs:
        a, b, g, h = SA[i], SB[i], GA[i], GB[i]
        print(f"        {i:3d} |      {a['sp']:6d} {a['P']:6d} {a['T']:5d} |     {b['sp']:6d} {b['P']:6d} {b['T']:5d} ||"
              f"      {g['sp']:6d} {g['P']:6d} {g['T']:4d} |     {h['sp']:6d} {h['P']:6d} {h['T']:4d}")
    ck(SB[240]["sp"] == 374 == 2 * SA[240]["sp"], f"A340 reference top 187 -> 374 (x2)", "S")
    ck(all(SB[i]["I"] == 0 and SB[i]["D"] == 0 for i in idxs), "settled I == 0 (ICL 0, Ki 0) and D == 0 on the hold", "S")
    ck(SA[240]["T"] < OUT_CLAMP[1] and SA[240]["P"] < cs["p_clamp"],
       f"stock A340 peak T {SA[240]['T']} is UNDER its 512 clamp; P {SA[240]['P']} under the {cs['p_clamp']} rail", "S")
    full = {i: a340_rate_pid_surface(i, cn) for i in range(241)}
    unclamped = {i: a340_rate_pid_surface(i, dict(cn, out_clamp=32767)) for i in range(241)}
    ck(all(full[i]["T"] == min(unclamped[i]["T"], OUT_CLAMP[2]) for i in range(241)),
       "at every idx 0..240, T == min(unclamped T, 900): the clamp is the only thing between the two surfaces", "S")
    clamp_from = next(i for i in range(241) if unclamped[i]["T"] > OUT_CLAMP[2])
    rail_from = next((i for i in range(241) if full[i]["P"] >= cn["p_clamp"]), None)
    print(f"      unclamped (P*lag*1776)>>15 first exceeds 900 at idx {clamp_from} (T {unclamped[clamp_from]['T']}; "
          f"idx {clamp_from - 1}: {unclamped[clamp_from - 1]['T']}); P rails at 20480 from idx {rail_from}; "
          f"unclamped T at idx 240 = {unclamped[240]['T']}")
    ck(all(full[i]["T"] == OUT_CLAMP[2] for i in range(clamp_from, 241)) and all(full[i]["T"] < OUT_CLAMP[2] for i in range(clamp_from)),
       f"T is clamp-bound at 900 for EXACTLY idx {clamp_from}..240, under it below", "S")
    ck(SB[240]["T"] == OUT_CLAMP[2] == 2 * SA[240]["T"], f"V37A-A340 full-demand T == {SB[240]['T']} == 2 x stock's "
       f"peak {SA[240]['T']}", "S")
    ck(all(SB[i]["T"] >= SA[i]["T"] for i in idxs), "V37A-A340 delivered T >= stock's at every listed idx", "S")
    sp_s = [a340_lerp(cs["map_x"], cs["map_y"], i) for i in range(241)]
    sp_n = [a340_lerp(cn["map_x"], cn["map_y"], i) for i in range(241)]
    cross = next(i for i in range(1, 241) if sp_n[i] >= sp_s[i])
    ck(all(sp_n[i] < sp_s[i] for i in range(1, cross)) and all(sp_n[i] >= sp_s[i] for i in range(cross, 241)),
       f"reference BELOW stock's for idx 1..{cross - 1} (concave stock map steeper at small signal; ratio at idx 6 "
       f"{sp_n[6] / sp_s[6]:.2f}, idx 24 {sp_n[24] / sp_s[24]:.2f}), at/above from idx {cross}, 2x at idx 240", "S")

    # ---- [10] rwd ----------------------------------------------------------------------------------------------
    print("\n  [10] .rwd ENCODE (V38 container; '/' = A310, A340, TVA,A340; '!' x3) + READBACK")
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
    ck(info["blocks"] == [{"start": START, "length": END - START}] or
       (len(info["blocks"]) == 1 and info["blocks"][0]["start"] == START and info["blocks"][0]["length"] == END - START),
       "V38 template has one block [0x13000, +0xED000)", "C")
    rwd = encode_x31(headers, info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V37A-A340 output")
    back = bytearray(stock)
    back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    ck(bytes(back) == bytes(code), ".rwd decoded back is BYTE-IDENTICAL to the built image", "S")
    wc = walk_counts(back)
    ck(wc == [(49, 0), (50, 0)], f"decoded .rwd image CRC {wc[0][0]}/{wc[0][1]} + {wc[1][0]}/{wc[1][1]}", "S")
    v38 = bytearray(b"\xff" * 0x100000)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    ck(bytes(v38[START:END]) == Path(FF.V38_PLAIN).read_bytes()[START:END],
       "cipher validated NON-CIRCULARLY: V38 rwd decodes to the known V38 plain image", "S")
    got = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in parse_x31(rwd)["headers"]}
    print(f"      headers: {got}")
    ck(got.get("/") == [s.decode() for s in VSTR] and got.get("!") == [HW_STR.decode()] * 3
       and got.get("&") == ["BF109E"], "'/' = A310, A340, TVA,A340; '!' 001100121020 x3; '&' BF109E unchanged", "T")
    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")

    img_sha, rwd_sha = hashlib.sha256(bytes(code)).hexdigest(), hashlib.sha256(rwd).hexdigest()
    print("\n" + "=" * 118)
    print(f"  image SHA256 {img_sha}   ({IMG_NAME})")
    print(f"  .rwd  SHA256 {rwd_sha}   ({RWD_NAME})")
    print(f"  vs A340 stock {len(d)} B in {len(runs)} runs, {len(blocks)} CRC blocks")
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
        print("\n      DRY RUN -- NOT WRITTEN.  Set ACCORD_V37A_A340_WRITE=1 to emit the files.")
        return 0
    print("\n  [11] WRITE -- guarded, re-hashed after")
    others = [p for p in Path(RWD_DIR).glob("*V37A-A340*") if p.name != RWD_NAME]
    if others:
        raise SystemExit(f"WRITE GUARD: another V37A-A340 rwd exists: {[p.name for p in others]}")
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
