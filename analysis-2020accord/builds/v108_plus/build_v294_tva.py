# -*- coding: utf-8 -*-
r"""V294 -- ACCELERATION TRIM ON THE V293 TORQUE MAP.  Two in-place opcode halfwords + four cal cells.

BASE            V293  (_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048
                       -MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin, sha256 f75e77cf...)  -- ON THE CAR since 2026-09-13
EDITS
  CODE (two 16-bit instructions, each replaced IN PLACE by another 16-bit instruction; no size change, no
  flow change, no new code):
    0x28FA4  `add  r9,r26`  c9d1 -> `subr r9,r26`  89d1   [S]  r26 := s_new - s_old  (was s_old + s_new)
    0x29D76  `shl  0x5,r16` c582 -> `shl  0x2,r16` c282   [E]  E := 4*sp - r26       (was 32*sp - r26)
  CAL:
    0xC62E6  fb clamp                 0 ->  1024   [C]  the trim's HARD BOUND: |r26| <= 1024
    0xC63E8  fb-lag pole a          923 ->  1011   [A]  16.5 Hz -> 2.0 Hz: the acceleration bandwidth
    0xC63EA  fb-lag input gain b   1560 ->   567   [B]  the trim gain (K_alpha/J = 1.0 at the BELIEF scale)
    0xCB994  Kp bank, ALL 28 records 120 ->   960   [K]  x8, so 4*sp*960 == 32*sp*120 (the FF is BIT-IDENTICAL)
  unchanged from V293: Kd bank 0, D clamp 0, Ki 0, r24 2048, the map, the tap, the 0x14A cave.

=== 0. WHAT THIS BUILD IS ===============================================================================
V293 made the LKAS lane a pure torque map: r26 (the rate feedback) was clamped to exactly 0, so
E = 32*sp and P = (E*120)>>8 = 15*sp.  The fork then had to do ALL the wheel's dynamic control at 100 Hz
through a ~60 ms round trip, and it could not damp the 1-2.7 Hz wheel mode (rev 2-6.4, the operator's
"jerky on hard turns" / "ratchety snapping").  The operator's call (2026-09-20): put a loop back in the EPS
at 1 kHz, on ACCELERATION rather than rate, and keep relying on the feedforward.

V294 keeps V293's forward path bit for bit and adds ONE term through the existing P gain:

    r26 = clamp(s_new - s_old, +-1024)            the per-tick change of the lag-filtered wheel rate
    E   = 4*sp - r26                              (the shl 0x5 -> 0x2 keeps the FF product 3840*sp)
    P   = (E*960)>>8 = 15*sp - 3.75*r26           = V293's feedforward MINUS an acceleration trim

s is the fb lag's state, s_new = (a*s + b*x)>>10; s_new - s_old = (b/1024)*(x - lag(x)) is a WASHOUT of the
wheel rate x -- the wheel's ACCELERATION through a first-order low-pass at the lag pole.  With the pole at
2.0 Hz it is an inertia below 2 Hz and a light damper above (7 % of V282's rate loop, -27 dB at 20 Hz).
The trim is hard-bounded at 25 % of the rail by the fb clamp; the other 75 %+ is always the map.

=== 1. THE ARITHMETIC, INTEGER PYTHON, ADDRESSES ON EVERY LINE ===========================================
    def lkas_lane(sp, x, s, cal):                  # Ts = 1 ms; every `>>` floors like `sar`
        b, a  = cal[0xC63EA], cal[0xC63E8]         # 0x28F86 ld.hu (567) ; 0x28F8A ld.h (1011)
        s_new = (a*s >> 10) + (b*x >> 10)          # 0x28F8E/92 mul ; 0x28F9A/A0 sar 0xa ; 0x28FA2 add
        r26   = s_new - s                          # 0x28FA4 subr r9,r26   <-- [S]  (V293: add -> s + s_new)
        r26   = clamp(r26, +-cal[0xC62E6])         # 0x28FA6..0x28FBC, C = 1024  <-- [C]  (V293: 0)
        s     = s_new                              # 0x28FA8 st.w
        E     = (sp << 2) - r26                    # 0x29D76 shl 0x2,r16 <-- [E] ; 0x29D78 sub r26,r16
        P     = clamp((E * 960) >> 8, +-15360)     # 0x29E36 mul (Kp record) ; 0x29E3E sar 0x8  <-- [K]
        D     = 0                                  # Kd 0 AND D clamp 0 (V293, unchanged)
        S     = clamp((254 * P) >> 8, +-15360)     # taper, sum clamp (unchanged)
        y     = output_lag(S)                      # 0x2A174..0x2A1AC (unchanged, 5 Hz)
        T     = clamp((y * 5346) >> 15, +-3072)    # forward gain, output cap (unchanged); rail 2461

  FF identity:  (32*sp*120)>>8 == (4*sp*960)>>8 for every sp -- asserted over the whole map range at [3e],
  and the delivered surface at r26 = 0 is asserted EQUAL TO V293's at every demand index 0..240 at [10].

=== 2. THE DESIGN NUMBERS (analysis-2020accord/studies/v294/v294_design.py) ==============================
  Pole sweep, K_alpha/J = 1.0, damping-ratio change of the wheel mode (light-damping world, BELIEF plant):
      pole     zeta x @5  @8  @12.5 @19  @26 m/s    20 Hz gain vs the loop V282 was marginal on
      16.5 Hz  0.81 0.86 0.98 1.13 1.28            -10 dB      (inertia dominates below 5 Hz: WORSE at low speed)
       8.0 Hz  0.84 0.91 1.06 1.25 1.45            -15 dB
       3.0 Hz  0.95 1.05 1.32 1.64 1.93            -23 dB
    -> 2.0 Hz  1.02 1.16 1.49 1.82 2.05            -27 dB      <-- SHIPPED: better at EVERY speed
       1.4 Hz  1.13 1.30 1.62 1.84 1.93            -30 dB
  Why a lag on acceleration DAMPS: T = -K*H(s)*alpha with H a lag gives J_eff = J + K*Re H and
  b_eff = b - K*w*Im H; Im H < 0 for a lag, so every degree of loop lag converts trim into damping.  Delayed
  RATE feedback does the opposite past 90 deg (V282's 20 Hz crossover resonance).  The trim anti-damps only
  where the total lag passes 180 deg (~26 Hz at this pole), where the output lag has already cut it x0.03.
  Rigid-body loop gain of the trim: max 1.7 at the 2.4 Hz resonance (that IS the damping), -180 deg
  crossings at 24-35 Hz with |L| 0.02-0.05 (26-34 dB gain margin), tau_d 1.5-3 ms.
  int32 headroom: |a*s| at the +-12000 rate guard = 0.246 of 2^31 (4.1x margin).  Clamp binds at
  ~2900 deg/s^2 (or ~230 deg/s of wheel rate above 2 Hz); trim cap = 3.75*1024*0.16 = 614 counts = 25 %.

=== 2b. TWO CORRECTIONS TO THE FRAMING ABOVE, from the adversarial pass (2026-09-20, adversary A) ========
  (i) THE 25 % CAP IS A BACKSTOP NORMAL DRIVING NEVER REACHES.  |H_diff| saturates at 0.557 above the pole,
      so the +-1024 clamp needs |x| >= 1838 = 230 deg/s of wheel rate (at the BELIEF scale; 459 at 4, 115 at
      16).  This car's measured peak wheel rate is 42-56 deg/s (V278r3); the r71 limit cycle was 88 deg/s.
      The trim THROUGH THE WHOLE CHAIN (output lag included) is 0.23 T counts per x-count at 2.4 Hz =
      1.85 T counts per deg/s = 0.0007 torque/(deg/s): at 10 deg/s ~18 counts (0.75 % of the rail), at the
      r71 amplitude ~163 counts (6.6 %).  That is the RIGHT size for what it is -- a damper comparable to the
      wheel's own light-world damping (0.0006 torque/(deg/s)), which is why zeta moves x1.0-2.0 -- but
      "the feedforward keeps >= 75 %" is vacuous; in practice it keeps 93-99 %.  The instrument must
      therefore be a REGRESSION over the drive (sec.3), not a per-frame read: 18 counts is below the
      identity's 22-count residual.
  (ii) AT THE 2-3 Hz MODES THE TRIM IS ~97 % DAMPING (in phase with rate) AND ~26 % INERTIA.  The
      docstring's "inertia below 2 Hz, a light damper above" has the emphasis inverted in the band that
      matters: the pole's own 40 deg of lead at 2.4 Hz plus the output lag's 25 deg leave the trim 15 deg
      from pure rate feedback.  Below 1 Hz it is mostly inertia; above 7 Hz the inertia share goes negative
      (the output lag) while the firmware-side damping share stays positive to 200 Hz -- the loop's -180 deg
      crossings at 24-35 Hz in the design analysis come from the PLANT's own s^2, not the trim.  Favourable,
      and it is why acceleration-through-a-lag was the right operand.

=== 3. THE SENTENCE A NULL LICENSES -- written before the drive ==========================================
The instrument is the CAN-427 delivered-torque tap (T = gp-0x6b38, `(sign<<9)|(|T|>>3)`), untouched, and the
0x18F wheel rate.  Because the feedforward is BYTE-IDENTICAL to V293's, on every engaged ramped frame
    residual = T_tap - FF_V293(idx)*taper = the trim = -3.75*clamp(r26)*0.16
so the trim is readable from the frames of ONE drive, no cross-drive contrast needed -- by REGRESSION, not
per frame (sec.2b: ~18 counts at 10 deg/s against a 22-count residual; the slope over 10^4+ frames is
hundreds of sigma):
  * residual regressed on -(the 0x18F rate through a 2 Hz low-pass, differenced): slope > 0, predicted
    1.85 T counts per deg/s of 2 Hz-band wheel rate (0.23 tap LSB per deg/s), and the FF identity
    R^2 >= 0.98 on low-acceleration frames  ->  THE EDIT IS LIVE WITH THE RIGHT SIGN.
  * residual flat (|slope| inside the 22-count noise) with the identity holding  ->  the trim is NOT LIVE
    (the subr did not take, or r26 is being clamped to 0).  Nothing else from that drive is licensed.
  * residual correlates POSITIVELY with acceleration  ->  SIGN INVERTED = negative virtual inertia.  STOP.
    Revert to V293.  The 25 % clamp bounds the damage but does not make it acceptable.
  * FF identity BROKEN (T no longer tracks FF_V293(idx) at low acceleration)  ->  the shl/Kp pair is not
    the identity this script proves; do not trust anything else from the drive.
  * The wheel mode: 1.6-3 Hz wheel-rate energy in hard turns vs r75/r76 windows; predicted DOWN.  A
    NEW line anywhere in 5-30 Hz is the revert signature (the trim's damper region).

=== 4. THE RISK STATEMENT ===============================================================================
  (a) TWO CODE BYTES CHANGE.  Not a cave -- two 16-bit instructions replaced in place by two 16-bit
      instructions of the same length (the class of V57's displacement repoint and V104's byte edit, both
      flown).  The decoder proves both lengths 2 -> 2 at [2]; nothing after them moves.  Still: this is the
      first code edit since V292's cave.
  (b) SIGN.  Verified two ways at [3b]: the sum operand OPPOSES a moving wheel on V282 (the -379/-763
      columns V293's own table records), and s_new - s_old has the same sign convention as s + s_new, so
      subr gives r26 > 0 for a wheel ACCELERATING in the +T sense and P falls.  A `sub` instead of `subr`
      would invert it; [2] decodes the mnemonic from the built bytes and [3e] runs the integer mirror.
  (c) THE PHYSICAL SCALE: 8 x-counts per deg/s was BELIEF at build time and is now MEASURED (2026-09-21,
      studies/v294/x_scale_from_v292_wire.py): on three V292 routes, where the rate loop was live and the
      lane delivers -4.80 T-counts per x-count, the 427 tap moves 7.1-7.8 x-counts per deg/s of wheel rate
      at every bin from +-2 to +-12 deg/s.  K_alpha/J = 1.0 at 8 is 0.9-1.0 at the measured value.  (An
      adversary's C3 claim of 1.0-1.7 rested on mis-identifying the frame at gp-0x14ce as 0x14A; the 0x14A
      buffer is at gp-0x1518.)  The 25 % clamp is scale-free either way.
  (d) THE FIRST DRIVE IS ON A REVERTED FORK (toggle-config_V294_accel-trim_r1.json: every torque-mode fork
      term off, standard torque controller).  Two things change at once; the within-frame instrument in
      sec.3 attributes the EPS edit regardless, the FEEL is the operator's to score.
  (e) Dwell at the rail (V293's sec.4d) is unchanged -- the FF is identical; the trim can only REDUCE |P|
      below the rail on a wheel accelerating with the command.
  (f) The r24 lane at 2048, the tap, the cave, the taper: all byte-identical to V293.

=== 5. CLASS -- how it differs from the arc ===============================================================
  V282-V292 tuned or opened the EPS RATE loop; V293 deleted it; rev 2-6.4 tried to replace it in the fork
  at 100 Hz.  V294 is the first build to close a NEW loop variable in the EPS: acceleration, through the
  stock PID's own P gain, with the feedforward untouched.  Not a re-run of any flashed lever: the operand
  (a tick difference) has never existed on any image, and no build has ever run Kp 960 or a 2 Hz fb pole.
  The nearest precedents: V289/V291 moved this pole (25 Hz / 9.94 Hz) with the SUM operand live -- a
  different loop; V282's D term was an acceleration feedback on the ERROR (with the setpoint kick and a
  67 % clamp) at 2.9x this trim's gain per washout count.
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

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
import build_v293_tva as V293                                                       # noqa: E402
from build_v293_tva import (Run, OK, BAD, qwalk, u16, s16, u32, rec, y_off, runs, lerp,   # noqa: E402
                            decode_one, scan_rel_cached, hits_at, scan_abs, out_lag_orbit,
                            taper_factor, read_cal, surface as surface293)
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, ANALYSIS_ROOT                # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
TP_BASE = 0xBF000
WRITE_MODE = os.environ.get("ACCORD_V294_WRITE", "").strip().lower()
MAX_PATH = 259

# ---- the base: V293, the image ON THE CAR ------------------------------------------------------------------
BASE_NAME = ("_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048"
             "-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
BASE_SHA = "f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17"
V293_RWD_SHA = "ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba"

# ---- [S] [E] the two opcode edits ---------------------------------------------------------------------------
SUBR_SITE, SUBR_OLD, SUBR_NEW = 0x28FA4, bytes.fromhex("c9d1"), bytes.fromhex("89d1")   # add r9,r26 -> subr r9,r26
SHL_SITE, SHL_OLD, SHL_NEW = 0x29D76, bytes.fromhex("c582"), bytes.fromhex("c282")     # shl 0x5,r16 -> shl 0x2,r16
# ---- [C] [A] [B] the fb stage cals --------------------------------------------------------------------------
FB_CELL, FB_BASE, FB_NEW = 0xC62E6, 0, 1024
FB_A_CELL, FB_A_BASE, FB_A_NEW = 0xC63E8, 923, 1011
FB_B_CELL, FB_B_BASE, FB_B_NEW = 0xC63EA, 1560, 567
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)
FB_A_SITE, FB_B_SITE = 0x28F8A, 0x28F86
FB_BLOCK_LO, FB_BLOCK_HI = 0x28F7C, 0x28FC8
FB_STATE_STORE, FB_STATE_STORE_B = 0x28FA8, bytes.fromhex("644fd1c2")
E_SUB_SITE, E_SUB_B = 0x29D78, bytes.fromhex("ba81")
X_SAT = 12000
# ---- [K] Kp x8 ------------------------------------------------------------------------------------------------
KP_PTR, KP_N, N_SLOTS, KP_BASE, KP_NEW = 0xCB994, 5, 28, 120, 960
E_SHIFT_BASE, E_SHIFT_NEW = 5, 2
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
# ---- frozen from V293 ----------------------------------------------------------------------------------------
KD_PTR, KD_N, DCLAMP_CELL, R24_CELL, MAP_PTR, MAP_N = 0xCB7D4, 4, 0xC61B6, 0xC6446, 0xC9A88, 10
FROZEN = dict(V293.FROZEN)
FROZEN.update({0xC62E6: 0, 0xC61B6: 0, 0xC6446: 2048, 0xC63E8: 923, 0xC63EA: 1560})
EME_FLOATS = V293.EME_FLOATS
PACK_LO, PACK_HI, PACK_V282 = V293.PACK_LO, V293.PACK_HI, V293.PACK_V282
T_STORE_SITE, T_STORE_B = V293.T_STORE_SITE, V293.T_STORE_B
CAVE14A_LO, CAVE14A_HI, CAVE14A_SHA8 = V293.CAVE14A_LO, V293.CAVE14A_HI, V293.CAVE14A_SHA8
CAVE14A_HOOK, CAVE14A_HOOK_B = V293.CAVE14A_HOOK, V293.CAVE14A_HOOK_B
ISLAND_LO, ISLAND_HI = V293.ISLAND_LO, V293.ISLAND_HI
DEFAULT = dict(fb_new=FB_NEW, a_new=FB_A_NEW, b_new=FB_B_NEW, kp_new=KP_NEW, subr=True, shl=True)
# the design ladder (v294_design.py [E0]): K_alpha/J = 1.0 at 1.4 / 2.0 / 3.0 / 4.0 Hz, and 0.5x / 2x at 2.0 Hz
LADDER = {(1015, 392), (1011, 567), (1005, 831), (1000, 1080), (1011, 284), (1011, 1134)}


def pole_hz(a, ts=1e-3):
    """The discrete pole a/1024 at Ts: f = -ln(a/1024) / (2 pi Ts).  923 -> 16.5 Hz, 1011 -> 2.03 Hz."""
    import math
    return -math.log(a / 1024) / (2 * math.pi * ts)


def make_tag(fb, a, b, kp, subr, shl):
    op = "SUBR" if subr else "ADD"
    sh = "SHL2" if shl else "SHL5"
    fpole = pole_hz(a)
    return (f"V294-V293BASE-ACCELTRIM.{op}.{sh}-FB.DIFF.C{fb}-POLE.{fpole:.1f}HZ.{a}.{b}"
            f"-KP.FLAT.{kp}.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP")


# ---- the integer mirrors ------------------------------------------------------------------------------------
def fb_tick(a, b, s, x, op):
    s_new = ((a * s) >> 10) + ((b * x) >> 10)
    return s_new, ((s_new - s) if op == "diff" else (s + s_new))


def fb_clamp(v, c):
    """0x28FA6-0x28FBE, branch for branch (V293's mirror, unchanged code)."""
    if not (v <= c):
        return c
    if v >= -c:
        return v
    return -c


def fb_orbit(a, b, x, op, c):
    s, seen, hist = 0, {}, []
    for _ in range(300000):
        if s in seen:
            return hist[seen[s]:]
        seen[s] = len(hist)
        s, r26 = fb_tick(a, b, s, x, op)
        hist.append(fb_clamp(r26, c))
    return hist[-1:]


def surface(img, slot, idx, r26, cal, e_shift):
    """V294's delivered lane torque at a constant demand index and a constant clamped operand r26.
    Same chain as V293's surface() except E = (sp << e_shift) - r26; e_shift is READ from the image by the
    caller (2 on V294, 5 on V293), never assumed."""
    mX, mY = rec(img, u32(img, MAP_PTR + 4 * slot))[1:]
    kX, kY = rec(img, u32(img, KP_PTR + 4 * slot))[1:]
    dX, dY = rec(img, u32(img, KD_PTR + 4 * slot))[1:]
    sp = lerp(mX, mY, idx)
    kp, kd = lerp(kX, kY, idx), lerp(dX, dY, idx)
    E = (sp << e_shift) - r26
    P_raw = (E * kp) >> 8
    P = max(-cal["PC"], min(cal["PC"], P_raw))
    D = max(-cal["DC"], min(cal["DC"], 0))
    S = max(-cal["SC"], min(cal["SC"], (cal["FADE"] * (P + D)) >> 8))
    y, y_lo, y_hi = out_lag_orbit(cal["LA"], cal["LB"], S)

    def clampT(v):
        v = ((v + 0x8000) & 0xFFFF) - 0x8000
        return max(-cal["OC"], min(cal["OC"], (v * cal["G"]) >> 15))
    return dict(sp=sp, kp=kp, kd=kd, E=E, P_raw=P_raw, P=P, rail=(P_raw != P), S=S,
                T=clampT(y), T_lo=clampT(y_lo), T_hi=clampT(y_hi))


def shl_imm(img, site):
    n, mn, ops, f = decode_one(bytes(img), site)
    assert mn == "shl" and n == 2, (site, mn, ops)
    return f["imm5"]


def fb_op(img, site):
    n, mn, ops, _f = decode_one(bytes(img), site)
    assert n == 2 and "".join(ops.split()) == "r9,r26", (site, mn, ops)
    return {"add": "sum", "subr": "diff"}[mn]


def independent_rebuild(base, fb, a, b, kp, subr, shl):
    """A second splice with a DIFFERENT CRC locator (FF.crc_block_map).  Shares this module's constants."""
    img = bytearray(base)
    touched = set()
    if subr:
        img[SUBR_SITE:SUBR_SITE + 2] = SUBR_NEW
        touched |= {SUBR_SITE, SUBR_SITE + 1}
    if shl:
        img[SHL_SITE:SHL_SITE + 2] = SHL_NEW
        touched |= {SHL_SITE, SHL_SITE + 1}
    for cell, v in ((FB_CELL, fb), (FB_A_CELL, a), (FB_B_CELL, b)):
        struct.pack_into("<H", img, cell, v)
        touched |= {cell, cell + 1}
    for s in range(N_SLOTS):
        p = u32(img, KP_PTR + 4 * s)
        n = u16(img, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(img, o) != kp:
                struct.pack_into("<H", img, o, kp)
                touched.add(o)
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


# =======================================================================================================
def build(fb_new=None, a_new=None, b_new=None, kp_new=None, subr=None, shl=None, quiet=False,
          do_rwd=True, base_bytes=None, mutate=None, dose_check=True, collect=False):
    fb_new = DEFAULT["fb_new"] if fb_new is None else fb_new
    a_new = DEFAULT["a_new"] if a_new is None else a_new
    b_new = DEFAULT["b_new"] if b_new is None else b_new
    kp_new = DEFAULT["kp_new"] if kp_new is None else kp_new
    subr = DEFAULT["subr"] if subr is None else subr
    shl = DEFAULT["shl"] if shl is None else shl
    R = Run(quiet, collect)
    ck, say = R.check, R.say
    TAG = make_tag(fb_new, a_new, b_new, kp_new, subr, shl)
    IMG_NAME = f"_v294_{TAG}_plain_image.bin"
    RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"

    say("=" * 118)
    say(f"  V294 -- ACCELERATION TRIM on the V293 torque map.  subr {subr} / shl2 {shl} / fb clamp {fb_new} "
        f"/ pole a {a_new} b {b_new} / Kp {kp_new} all 28")
    say("=" * 118)

    say("\n  [1] BASE = V293 (the image on the car)")
    base = bytearray(base_bytes if base_bytes is not None else Path(plain_image_path(BASE_NAME)).read_bytes())
    ck(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V293 base sha256 matches", "S")
    ck(qwalk(walk_all_blocks, bytes(base)) == 0, "base CRC chain 50/50  [entailed]", "V")
    ck(qwalk(walk, bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49  [entailed]", "V")
    for a, v in FROZEN.items():
        ck(u16(base, a) == v, f"base 0x{a:05X} == {v}  [entailed]", "V")
    ck(bytes(base[SUBR_SITE:SUBR_SITE + 2]) == SUBR_OLD and bytes(base[SHL_SITE:SHL_SITE + 2]) == SHL_OLD,
       f"base carries `add r9,r26` ({SUBR_OLD.hex()}) at 0x{SUBR_SITE:05X} and `shl 0x5,r16` ({SHL_OLD.hex()}) "
       f"at 0x{SHL_SITE:05X}  [entailed]", "V")
    kptrs = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    ck(all(rec(base, p)[2] == [KP_BASE] * KP_N for p in kptrs),
       f"base Kp bank: all {N_SLOTS} records flat at {KP_BASE} (V293)  [entailed]", "V")
    if dose_check:
        ck(subr and shl, "the two opcode edits are BOTH on -- neither alone is a candidate", "S")
        ck(0 < fb_new <= 4096, f"fb clamp {fb_new}: the trim bound is > 0 and <= 4096 (<= 100 % of the rail)", "S")
        ck(1000 <= a_new <= 1018 and 1 <= b_new <= 4000,
           f"pole a {a_new} in [1000,1018] (1.0-4 Hz) and b {b_new} in [1,4000]", "S")
        ck(kp_new == KP_BASE << (E_SHIFT_BASE - E_SHIFT_NEW),
           f"Kp {kp_new} == {KP_BASE} << ({E_SHIFT_BASE}-{E_SHIFT_NEW}) -- the FF product is preserved EXACTLY", "S")
        # adversary B defect 6 (2026-09-20): b was bounded, not pinned -- a doubled dose passed every check.  The
        # (a, b) pair must be a DOCUMENTED rung of the design ladder (v294_design.py [E0], K_alpha/J = 1.0 at each
        # pole, plus the 0.5x / 2x rungs at the shipped 2 Hz pole).  Anything else is not a candidate.
        ck((a_new, b_new) in LADDER,
           f"(a, b) = ({a_new}, {b_new}) is a documented ladder rung {sorted(LADDER)}; "
           f"{'THE SHIPPED DESIGN POINT' if (a_new, b_new) == (FB_A_NEW, FB_B_NEW) else 'a ladder alternative, NOT the shipped point'}", "S")
    else:
        say("      (dose_check RELAXED -- the ZERO-EDIT CONTROL, not a flight candidate)")

    say("\n  [2] THE TWO INSTRUCTIONS, DECODED before and after (independent V850 decoder, lengths asserted)")
    for site, old, new, want_old, want_new in ((SUBR_SITE, SUBR_OLD, SUBR_NEW, "add r9,r26", "subr r9,r26"),
                                               (SHL_SITE, SHL_OLD, SHL_NEW, "shl 0x5,r16", "shl 0x2,r16")):
        n0, m0, o0, _ = decode_one(bytes(base), site)
        probe = bytearray(base)
        probe[site:site + 2] = new
        n1, m1, o1, _ = decode_one(bytes(probe), site)
        ck(n0 == 2 and n1 == 2 and "".join(f"{m0} {o0}".split()) == "".join(want_old.split())
           and "".join(f"{m1} {o1}".split()) == "".join(want_new.split()),
           f"0x{site:05X}: `{m0} {o0}` (len {n0}) -> `{m1} {o1}` (len {n1}); SAME LENGTH, nothing after it moves", "S")
    # the instruction AFTER each edit still decodes identically on the patched image (no boundary damage)
    for site, new, nxt in ((SUBR_SITE, SUBR_NEW, 0x28FA6), (SHL_SITE, SHL_NEW, 0x29D78)):
        probe = bytearray(base)
        probe[site:site + 2] = new
        a0, a1 = decode_one(bytes(base), nxt), decode_one(bytes(probe), nxt)
        ck(a0 == a1, f"the following instruction 0x{nxt:05X} `{a0[1]} {a0[2]}` decodes IDENTICALLY after the edit", "S")
    for site, cell, mnem, dst in ((0x28F96, FB_CELL, "ld.hu", 13), (0x28F9C, FB_CELL, "ld.hu", 14),
                                  (0x28FB8, FB_CELL, "ld.hu", 26), (FB_A_SITE, FB_A_CELL, "ld.h", 9),
                                  (FB_B_SITE, FB_B_CELL, "ld.hu", 16)):
        _n, mn, ops, f = decode_one(bytes(base), site)
        ck(mn == mnem and f["reg1"] == 5 and TP_BASE + f["disp"] == cell and f["reg2"] == dst,
           f"0x{site:05X}: `{mn} {ops}`, tp+0x{f['disp']:X} == 0x{cell:05X} (= {u16(base, cell)}). No off-by-0x1000", "V")
    ck(s16(base, FB_A_CELL) == FB_A_BASE and a_new < 32768,
       f"a is read `ld.h` (SIGNED): {a_new} < 32768 so it reads as +{a_new}, never negative", "S")

    say("\n  [3] GATE 1 -- image-wide census of every cell this build writes (raw LE byte scan, controls first)")
    S = scan_rel_cached(bytes(base))
    ck([h[0] for h in hits_at(S, V293.GAIN_CELL)] == [0x2A1EE], "CONTROL: the forward gain found at its ONE site", "S")
    ck(len(hits_at(S, V293.SUM_CLAMP)) == 8 and len(hits_at(S, V293.P_CLAMP)) == 7,
       "CONTROL: the sum clamp has 8 and the P clamp 7 accessors", "S")
    fb_h = hits_at(S, FB_CELL)
    ck([h[0] for h in fb_h] == list(FB_SITES) and all(h[3] == "ld.hu" for h in fb_h),
       f"0x{FB_CELL:05X} fb clamp: EXACTLY {len(fb_h)} accessors {[hex(h[0]) for h in fb_h]}, all ld.hu, zero writers", "S")
    a_h, b_h = hits_at(S, FB_A_CELL), hits_at(S, FB_B_CELL)
    ck([h[0] for h in a_h] == [FB_A_SITE] and a_h[0][3] == "ld.h"
       and [h[0] for h in b_h] == [FB_B_SITE] and b_h[0][3] == "ld.hu",
       f"0x{FB_A_CELL:05X} (a): 1 accessor {[hex(h[0]) for h in a_h]} ld.h; 0x{FB_B_CELL:05X} (b): 1 accessor "
       f"{[hex(h[0]) for h in b_h]} ld.hu -- both PRIVATE to the fb lag, zero writers (V289 moved these same two cells)", "S")
    ck(not any(scan_abs(bytes(base), c) for c in (FB_CELL, FB_A_CELL, FB_B_CELL)),
       "no LE32 in the image equals any of the three cal addresses", "S")
    # the two code sites: no branch may land INSIDE either 2-byte instruction (odd targets are impossible on
    # V850), and both are 2-byte instructions on 2-byte alignment; verified by decoding a window around them
    for lo, hi in ((0x28F86, 0x28FC0), (0x29D6C, 0x29D84)):
        pc, ok_ = lo, True
        while pc < hi:
            n, _m, _o, _f = decode_one(bytes(base), pc)
            pc += n
        ok_ = (pc == hi)
        ck(ok_, f"linear decode of [0x{lo:05X},0x{hi:05X}) lands exactly on 0x{hi:05X} -- the edited halfwords "
                f"sit on instruction boundaries", "S")

    say("\n  [3b] SIGN, two ways")
    # (i) V293's own table: at fb > 0 (wheel moving +) V282 delivered LESS/negative torque: fb OPPOSES motion
    cal_b = read_cal(base)
    v282img = None
    try:
        v282img = Path(plain_image_path(V293.BASE_NAME)).read_bytes()
    except Exception:
        pass
    if v282img is not None and hashlib.sha256(v282img).hexdigest() == V293.BASE_SHA:
        c282 = read_cal(v282img)
        t0, t10 = (surface293(v282img, LIVE_SLOT, 10, fb, c282)["T"] for fb in (0, 2434))
        ck(t10 < t0, f"V282 image: T(idx 10) = {t0} at fb 0 and {t10} at fb +2434 (10 deg/s in the + sense): "
                     f"a POSITIVE operand LOWERS the torque -- E = shl(sp) - r26 is negative feedback", "S")
    else:
        say("      (V282 image absent -- sign check (i) SKIPPED and reported)")
    # (ii) the difference operand has the SAME sign convention as the sum: for a rate x that STEPS UP, s rises
    #      and s_new - s_old > 0 during the rise; the sum is positive for positive x.  Both > 0 -> same sense.
    s, seq_sum, seq_diff = 0, [], []
    for k in range(50):
        x = 800 if k >= 5 else 0
        s_new, d = fb_tick(a_new, b_new, s, x, "diff")
        seq_diff.append(d)
        seq_sum.append(s + s_new)
        s = s_new
    ck(max(seq_diff[5:20]) > 0 and max(seq_sum[5:20]) > 0 and all(v >= 0 for v in seq_diff),
       f"integer mirror: a +800 rate step gives s_new - s_old = {seq_diff[5:10]}... (>0 while the rate is RISING) and "
       f"s + s_new > 0 -- SAME sign convention, so subr -> r26 > 0 for + acceleration -> P falls: NEGATIVE feedback", "S")

    say("\n  [3e] THE OPERAND AND THE FF IDENTITY, integer mirrors")
    for x in (0, 80, 800, X_SAT):
        orb = fb_orbit(a_new, b_new, x, "diff", fb_new)
        ck(len(orb) == 1 and orb[0] == 0,
           f"constant x = {x}: the clamped difference operand settles to EXACTLY 0 (orbit {sorted(set(orb))}) -- "
           f"no DC bias at any steady wheel rate; the SUM operand at x = 80 sits at 2434", "S")
    bad = [sp for sp in range(-2048, 2049) if ((sp << E_SHIFT_BASE) * KP_BASE) >> 8 != ((sp << E_SHIFT_NEW) * kp_new) >> 8]
    ck(not bad, f"((sp<<{E_SHIFT_BASE})*{KP_BASE})>>8 == ((sp<<{E_SHIFT_NEW})*{kp_new})>>8 for EVERY sp in [-2048, 2048] "
                f"({len(bad)} mismatches): the FEEDFORWARD PRODUCT IS BIT-IDENTICAL", "S")
    s_max = b_new * X_SAT // (1024 - a_new)
    ck(a_new * s_max < 2 ** 31 and b_new * X_SAT < 2 ** 31,
       f"int32: |a*s| at the +-{X_SAT} rate guard = {a_new * s_max:,} = {a_new * s_max / 2 ** 31:.3f} of 2^31; "
       f"|b*x| = {b_new * X_SAT:,}. Both low-word multiplies stay inside int32", "S")
    ck(abs(fb_new * kp_new) < 2 ** 24, f"|C*Kp| = {fb_new * kp_new:,} -- E*Kp stays inside int32 at the clamp bound", "S")

    say("\n  [6] APPLY")
    code = bytearray(base)
    attributed = set()
    if subr:
        code[SUBR_SITE:SUBR_SITE + 2] = SUBR_NEW
        attributed |= {SUBR_SITE, SUBR_SITE + 1}
    if shl:
        code[SHL_SITE:SHL_SITE + 2] = SHL_NEW
        attributed |= {SHL_SITE, SHL_SITE + 1}
    for cell, v, tag in ((FB_CELL, fb_new, "[C] fb clamp"), (FB_A_CELL, a_new, "[A] pole a"), (FB_B_CELL, b_new, "[B] gain b")):
        if u16(base, cell) != v:
            struct.pack_into("<H", code, cell, v)
            attributed |= {cell, cell + 1}
        ck(u16(code, cell) == v, f"{tag} 0x{cell:05X} {u16(base, cell)} -> {v}", "T")
    kp_cells = 0
    for p in sorted(set(kptrs)):
        n = u16(base, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(base, o) != kp_new:
                struct.pack_into("<H", code, o, kp_new)
                attributed |= {o, o + 1}
                kp_cells += 1
    ck(all(rec(code, p)[2] == [kp_new] * KP_N for p in kptrs),
       f"[K] Kp -> {kp_new} flat on all {len(set(kptrs))} DISTINCT records, {kp_cells} cells", "T")
    if mutate is not None:
        mutate(code, attributed)
    say(f"      {len(attributed)} payload bytes written")

    say("\n  [6b] READ BACK FROM THE BUILT IMAGE, AFTER mutate() -- adversary B's defects 1 and 3 (2026-09-20)")
    # (i) the FULL Y tuple of EVERY Kp record, walked from the pointer family IN THE BUILT IMAGE (V293's [10] census;
    #     a 961 on a non-live knot passed every check when this ran only on slot 7 -- adversary B, defect 1)
    kp_ptrs_img = [u32(code, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    kp_bad = [(s, hex(p), rec(code, p)[2]) for s, p in enumerate(kp_ptrs_img) if rec(code, p)[2] != [kp_new] * KP_N]
    kp_x_bad = [(s, hex(p)) for s, p in enumerate(kp_ptrs_img)
                if (u16(code, p), rec(code, p)[1]) != (u16(base, p), rec(base, p)[1])]
    ck(not kp_bad and not kp_x_bad and kp_ptrs_img == kptrs,
       f"🛑 FULL Y-TUPLE CENSUS of all {N_SLOTS} Kp records on the BUILT image: every Y tuple is EXACTLY ({kp_new},)*{KP_N} "
       f"({len(kp_bad)} violate{': ' + str(kp_bad[:2]) if kp_bad else ''}), every n and X axis untouched "
       f"({len(kp_x_bad)} violate), the pointer array unchanged", "S")
    # (ii) the two instructions' REGISTER FIELDS, not just the mnemonic/immediate (adversary B, defect 3: a
    #      `shl 0x2,r17` slip was caught only by the byte count)
    n_s, m_s, o_s, f_s = decode_one(bytes(code), SUBR_SITE)
    n_e, m_e, o_e, f_e = decode_one(bytes(code), SHL_SITE)
    ck((n_s, m_s, f_s.get("reg1"), f_s.get("reg2")) == (2, "subr" if subr else "add", 9, 26),
       f"0x{SUBR_SITE:05X} on the BUILT image: `{m_s} {o_s}` -- reg1 = r{f_s.get('reg1')} (s_new), reg2 = r{f_s.get('reg2')} "
       f"(s_old, the destination): r26 := r9 - r26", "S")
    ck((n_e, m_e, f_e.get("imm5"), f_e.get("reg2")) == (2, "shl", E_SHIFT_NEW if shl else E_SHIFT_BASE, 16),
       f"0x{SHL_SITE:05X} on the BUILT image: `{m_e} {o_e}` -- imm5 = {f_e.get('imm5')}, DESTINATION r{f_e.get('reg2')} "
       f"(the setpoint register the 0x29D78 `sub r26,r16` consumes)", "S")

    say("\n  [7] EVERYTHING ELSE BYTE-IDENTICAL TO V293 (first assertion is FULL-COVERAGE; the rest are entailed)")
    outside = [x for x in range(START, END) if x not in attributed and code[x] != base[x]]
    ck(outside == [], f"NO byte outside the {len(attributed)} attributed payload bytes differs from V293 "
                      f"({len(outside)} stray)", "S")
    code_bytes = sorted(x for x in attributed if x < 0xC0000)
    code_diff = sorted(x for x in code_bytes if code[x] != base[x])
    ck(code_bytes == [SUBR_SITE, SUBR_SITE + 1, SHL_SITE, SHL_SITE + 1] and code_diff == [SUBR_SITE, SHL_SITE],
       f"FOUR code bytes WRITTEN, {[hex(x) for x in code_bytes]} (the two 16-bit instructions), of which exactly TWO "
       f"differ in value from V293: {[hex(x) for x in code_diff]} (c9->89, c5->c2; the high bytes d1 / 82 are unchanged)", "S")
    for a, v in FROZEN.items():
        if a not in (FB_CELL, FB_A_CELL, FB_B_CELL):
            ck(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}   [entailed]", "V")
    for a, v in EME_FLOATS.items():
        ck(bytes(code[a:a + 4]) == bytes(base[a:a + 4]), f"EME float mirror 0x{a:05X}   [entailed]", "V")
    ck(bytes(code[PACK_LO:PACK_HI]) == PACK_V282 == bytes(base[PACK_LO:PACK_HI]),
       "the CAN-427 delivered-torque tap is byte-identical AND equals the recorded window -- THE INSTRUMENT IS ON THE WIRE", "S")
    ck(bytes(code[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_B, "the tap's source store 0x2A23C intact  [entailed]", "V")
    ck(hashlib.sha256(bytes(code[CAVE14A_LO:CAVE14A_HI])).hexdigest()[:8] == CAVE14A_SHA8
       and bytes(code[CAVE14A_HOOK:CAVE14A_HOOK + 4]) == CAVE14A_HOOK_B, "the 0x14A cave and hook intact", "S")
    ck(bytes(code[E_SUB_SITE:E_SUB_SITE + 2]) == E_SUB_B and bytes(code[FB_STATE_STORE:FB_STATE_STORE + 4]) == FB_STATE_STORE_B,
       "0x29D78 `sub r26,r16` and 0x28FA8 `st.w r9,-0x3d30,gp` untouched  [entailed]", "V")
    dptrs = [u32(base, KD_PTR + 4 * s) for s in range(N_SLOTS)]
    ck(all(rec(code, p)[2] == [0] * KD_N for p in dptrs) and u16(code, DCLAMP_CELL) == 0,
       "Kd bank 0 on all 28 records AND the D clamp 0: NO jerk term (V293's two independent cells)  [entailed]", "V")
    ck(u16(code, 0xC63E6) == 0, "Ki 0: NO rate term through the integrator  [entailed]", "V")
    ck(u16(code, R24_CELL) == 2048, "r24 engaged arm 2048 unchanged  [entailed]", "V")

    say("\n  [8] CRC TRAILERS -- blocks located by walking the chain from the image")
    owners = {}
    for a in sorted(attributed):
        owners.setdefault(tuple(V53.owning_block(code, a)), []).append(a)
    blocks = sorted(owners)
    for b0, b1 in blocks:
        ck(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
        oldc, newc = u32(code, b1), zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        moved = [a for a in owners[(b0, b1)] if code[a] != base[a]]
        ck((newc != oldc) == bool(moved), f"block [0x{b0:06X},0x{b1:06X}) CRC moves IFF a byte changed value "
                                          f"({len(moved)} of {len(owners[(b0, b1)])}); 0x{oldc:08X} -> 0x{newc:08X}", "S")
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        say(f"      page [0x{b0:06X},0x{b1:06X})  trailer 0x{oldc:08X} -> 0x{newc:08X}  ({len(owners[(b0, b1)])} payload bytes)")
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    say("\n  [9] FULL BYTE DIFF vs V293, every run attributed")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    ck(set(diff) <= attributed, f"all {len(diff)} differing bytes are attributed payload or CRC", "S")
    exp_code = sum(1 for s_, o, n_ in ((SUBR_SITE, SUBR_OLD, SUBR_NEW), (SHL_SITE, SHL_OLD, SHL_NEW)) for j in (0, 1) if o[j] != n_[j])
    exp_cal = sum(1 for cell, v in ((FB_CELL, fb_new), (FB_A_CELL, a_new), (FB_B_CELL, b_new)) for j in (0, 1)
                  if struct.pack("<H", u16(base, cell))[j] != struct.pack("<H", v)[j])
    exp_kp = sum(1 for p in set(kptrs) for k in range(KP_N) for j in (0, 1)
                 if struct.pack("<H", u16(base, y_off(p, KP_N, k)))[j] != struct.pack("<H", kp_new)[j])
    exp_crc = sum(1 for _b0, b1 in blocks for j in range(4) if code[b1 + j] != base[b1 + j])
    exp = exp_code + exp_cal + exp_kp + exp_crc
    ck(len(diff) == exp, f"total diff = {exp_code} code + {exp_cal} fb-stage cal + {exp_kp} Kp + {exp_crc} CRC "
                         f"(over {len(blocks)} block(s)) = {exp}, got {len(diff)} -- every term COMPUTED from the base", "S")
    names = {SUBR_SITE: (2, "subr        0x28FA4 [S]"), SHL_SITE: (2, "shl 0x2     0x29D76 [E]"),
             FB_CELL: (2, "fb clamp    0xC62E6 [C]"), FB_A_CELL: (2, "pole a      0xC63E8 [A]"), FB_B_CELL: (2, "gain b      0xC63EA [B]")}
    for p in set(kptrs):
        names[y_off(p, KP_N, 0)] = (2 * KP_N, f"Kp Y  rec 0x{p:05X} [K]")
    trailers = {b1 for _b0, b1 in blocks}
    labelled = [(s_, e_, next((v for k, (n_, v) in names.items() if k <= s_ < k + n_), None)
                 or next((f"CRC trailer 0x{t:06X}" for t in trailers if t <= s_ < t + 4), None)) for s_, e_ in runs(diff)]
    orphan = [(hex(s_), hex(e_ - 1)) for s_, e_, lbl in labelled if lbl is None]
    ck(not orphan, f"every one of the {len(labelled)} differing runs is a named edit or a CRC trailer ({orphan})", "S")
    say("      offset                len  what                       base -> built")
    for s_, e_, lbl in labelled:
        if e_ - s_ <= 10 or (lbl or "").startswith("CRC") or "[S]" in (lbl or "") or "[E]" in (lbl or ""):
            say(f"      0x{s_:06X}-0x{e_ - 1:06X} ({e_ - s_:3d} B)  {(lbl or 'UNATTRIBUTED'):26s} "
                f"{bytes(base[s_:e_]).hex()} -> {bytes(code[s_:e_]).hex()}")
    say(f"      (+ {sum(1 for _s, _e, l in labelled if l and l.startswith('Kp'))} Kp record runs of 10 B each)")

    say("\n  [10] THE DELIVERED SURFACE -- READ FROM THE BUILT IMAGE, and the FF identity against V293")
    cal = read_cal(code)
    e_img, e_base = shl_imm(code, SHL_SITE), shl_imm(base, SHL_SITE)
    op_img, op_base = fb_op(code, SUBR_SITE), fb_op(base, SUBR_SITE)
    ck((e_img, op_img) == (E_SHIFT_NEW, "diff") and (e_base, op_base) == (E_SHIFT_BASE, "sum"),
       f"read back from the bytes: built shl imm {e_img}, operand `{op_img}`; base shl imm {e_base}, operand `{op_base}`", "S")
    a_i, b_i, c_i = s16(code, FB_A_CELL), u16(code, FB_B_CELL), u16(code, FB_CELL)
    say(f"      fb stage on the built image: a={a_i} b={b_i} C={c_i}; pole {pole_hz(a_i):.2f} Hz")
    ck((1.0 <= pole_hz(a_i) <= 4.0) or not dose_check,
       f"the built pole is {pole_hz(a_i):.2f} Hz -- inside the ladder's 1-4 Hz (the shipped design point is 2.0 Hz)", "S")
    tbl, mism = [], []
    for i in range(0, 241):
        v = surface(code, LIVE_SLOT, i, 0, cal, e_img)
        b0 = surface(base, LIVE_SLOT, i, 0, cal_b, e_base)
        b0c = surface293(base, LIVE_SLOT, i, 0, cal_b)
        if (v["P"], v["S"], v["T"]) != (b0["P"], b0["S"], b0["T"]) or (b0["P"], b0["S"], b0["T"]) != (b0c["P"], b0c["S"], b0c["T"]):
            mism.append(i)
        if i % 20 == 0 or i == 240:
            vm = surface(code, LIVE_SLOT, i, -c_i, cal, e_img)
            vp = surface(code, LIVE_SLOT, i, +c_i, cal, e_img)
            tbl.append((i, v, b0, vm, vp))
    ck(not mism, f"🛑 THE FEEDFORWARD IS BYTE-EXACT: V294 at r26 = 0 delivers V293's P, S and T at EVERY demand index "
                 f"0..240 ({len(mism)} mismatches), and this module's surface() reproduces build_v293_tva.surface() on the base", "S")
    say("      idx |  map |  Kp |     P  rail |     T   | V293 T | T at r26=-C (accel AGAINST cmd) | at +C (WITH cmd)")
    for i, v, b0, vm, vp in tbl:
        say(f"      {i:4d} | {v['sp']:4d} | {v['kp']:3d} | {v['P']:6d} {'RAIL' if v['rail'] else '    '} | {v['T']:6d}  | "
            f"{b0['T']:6d} | {vm['T']:6d} ({vm['T'] - v['T']:+5d})              | {vp['T']:6d} ({vp['T'] - v['T']:+5d})")
    v0, vm0, vp0 = (surface(code, LIVE_SLOT, 120, r, cal, e_img)["T"] for r in (0, -c_i, c_i))
    cap = (kp_new * c_i) >> 8
    ck(abs(vm0 - v0) <= 640 and abs(vp0 - v0) <= 640 and abs(vm0 - v0) >= 560,
       f"the trim at the clamp bound is {vm0 - v0:+d} / {vp0 - v0:+d} counts at idx 120 = {100 * abs(vm0 - v0) / 2461:.1f} % of the "
       f"2461 rail (P-domain cap {cap} = (Kp*C)>>8): THE FEEDFORWARD KEEPS >= 75 % BY CONSTRUCTION", "S")
    v240 = surface(code, LIVE_SLOT, 240, 0, cal, e_img)
    ck(v240["T"] == 2461 and v240["rail"], f"the rail is {v240['T']} at idx 240, P clamp binding, exactly V293's", "S")
    ck(all(tbl[k][1]["T"] <= tbl[k + 1][1]["T"] for k in range(len(tbl) - 1)), "monotone in demand index", "S")
    # the operand's frequency response from the BUILT cells (magnitude at the mode band and at 20 Hz)
    import cmath
    import math as _m
    say("      the operand from the built cells, x -> r26 (unclamped), and the trim as P-counts per x-count:")
    for f in (1.0, 2.0, 2.5, 7.0, 20.0):
        z = cmath.exp(2j * _m.pi * f * 1e-3)
        H = (b_i / 1024) * (z - 1) / (z - a_i / 1024)
        say(f"        f={f:5.1f} Hz  |r26/x| {abs(H):6.3f}  phase {_m.degrees(cmath.phase(H)):6.1f} deg  "
            f"trim {kp_new / 256 * abs(H):6.2f} P/x   (V282 at 20 Hz: 44.9 P/x, P+D)")
    z20 = cmath.exp(2j * _m.pi * 20.0 * 1e-3)
    ours20 = kp_new / 256 * abs((b_i / 1024) * (z20 - 1) / (z20 - a_i / 1024))
    ck(ours20 < 0.25 * 44.9, f"trim gain at 20 Hz = {ours20:.2f} P-counts per x-count = {20 * _m.log10(ours20 / 44.9):.1f} dB "
                             f"below V282's P+D there (the loop that was marginal at 20 Hz); gate: < -12 dB", "S")

    say("\n  [11] THE OUTPUT NAME, RE-DERIVED FROM THE BUILT IMAGE'S OWN BYTES")
    img_tag = make_tag(u16(code, FB_CELL), s16(code, FB_A_CELL), u16(code, FB_B_CELL),
                       rec(code, u32(code, KP_PTR + 4 * LIVE_SLOT))[2][0], op_img == "diff", e_img == 2)
    ck(img_tag == TAG, "the tag re-derived from the image's own halfwords and opcodes is CHARACTER-IDENTICAL", "S")
    say(f"      {IMG_NAME}")
    say(f"      {RWD_NAME}")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [12] .rwd ENCODE + READBACK")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V294 output")
        back = bytearray(base)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code), "the decoded .rwd is BYTE-IDENTICAL to the built image", "S")
        ck(qwalk(walk_all_blocks, bytes(back)) == 0 and qwalk(walk, bytes(back)) == 0, "readback CRC 50/50 + 49/49  [entailed]", "V")
        v38 = bytearray(base)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()
        say("\n  [13] INDEPENDENT REBUILD -- a second splice + a DIFFERENT CRC locator")
        ind = independent_rebuild(bytes(base), fb_new, a_new, b_new, kp_new, subr, shl)
        ck(hashlib.sha256(ind).hexdigest() == img_sha,
           "independent rebuild == built image sha256 (shares the constants; cross-checks the CRC locator and splice only)", "S")

    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit the {MAX_PATH}-char limit (image {len(str(out_i))}, rwd {len(str(out_r))})", "S")
    say("\n" + "=" * 118)
    say(f"  image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  .rwd  SHA256 {rwd_sha}")
    say(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['V']} vacuous, {R.census['T']} tautological")
    say("=" * 118)
    return dict(code=bytes(code), base=bytes(base), rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, tag=TAG,
                img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, blocks=blocks, diff=len(diff), attributed=len(attributed))


# =======================================================================================================
def zero_edit_control(base):
    r = build(fb_new=FB_BASE, a_new=FB_A_BASE, b_new=FB_B_BASE, kp_new=KP_BASE, subr=False, shl=False,
              quiet=True, do_rwd=False, base_bytes=base, dose_check=False, collect=True)
    return r["img_sha"], r["diff"], r["attributed"]


def mutation_test(base):
    """Flip each edit in a way the script must CATCH.  Returns [(name, [failures])]."""
    def m_sub_not_subr(code, att):          # `sub r9,r26` = a9d1: the INVERTED sign
        code[SUBR_SITE:SUBR_SITE + 2] = bytes.fromhex("a9d1")

    def m_add_left(code, att):              # the subr did not take
        code[SUBR_SITE:SUBR_SITE + 2] = SUBR_OLD

    def m_shl5_left(code, att):             # the shl did not take: FF x8
        code[SHL_SITE:SHL_SITE + 2] = SHL_OLD

    def m_shl3(code, att):                  # wrong immediate
        code[SHL_SITE:SHL_SITE + 2] = bytes.fromhex("c382")

    def m_kp_one_record(code, att):         # one record left at 120
        p = u32(code, KP_PTR + 4 * 3)
        for k in range(KP_N):
            struct.pack_into("<H", code, y_off(p, KP_N, k), KP_BASE)

    def m_kp_interior_knot(code, att):      # a corrupted interior knot on the live record
        struct.pack_into("<H", code, y_off(LIVE_KP_REC, KP_N, 2), 961)

    def m_kp_nonlive_knot(code, att):       # adversary B defect 1: 961 on a NON-live slot's knot -- was MISSED
        p = u32(code, KP_PTR + 4 * 3)
        struct.pack_into("<H", code, y_off(p, KP_N, 0), 961)

    def m_kp_two_nonlive(code, att):        # adversary B defect 1: two non-live records, diff count preserved
        for s_ in (1, 4):
            p = u32(code, KP_PTR + 4 * s_)
            struct.pack_into("<H", code, y_off(p, KP_N, 4), 961)

    def m_shl_wrong_reg(code, att):         # adversary B defect 3: `shl 0x2,r17` -- right immediate, wrong register
        code[SHL_SITE:SHL_SITE + 2] = bytes.fromhex("c28a")

    def m_b_double(code, att):              # adversary B defect 6: the 2x dose at the byte level
        struct.pack_into("<H", code, FB_B_CELL, FB_B_NEW * 2)

    def m_fb_zero(code, att):               # clamp left at 0: the trim is dead
        struct.pack_into("<H", code, FB_CELL, 0)

    def m_fb_huge(code, att):               # clamp 46080: no bound on the trim
        struct.pack_into("<H", code, FB_CELL, 46080)

    def m_a_old(code, att):                 # pole left at 16.5 Hz
        struct.pack_into("<H", code, FB_A_CELL, FB_A_BASE)

    def m_b_x8(code, att):                  # b eight times too large: int32 overflow at the guard
        struct.pack_into("<H", code, FB_B_CELL, FB_B_NEW * 8)

    def m_stray_byte(code, att):            # an unattributed byte in the code region
        code[0x2A1F0] ^= 0x01

    def m_dclamp(code, att):                # D resurrected
        struct.pack_into("<H", code, DCLAMP_CELL, 10240)

    def m_kd_live(code, att):               # Kd resurrected on the live record
        struct.pack_into("<H", code, y_off(0xE511C, KD_N, 0), 128)

    def m_crc_off(code, att):               # a wrong trailer
        b0, b1 = V53.owning_block(code, FB_CELL)
        struct.pack_into("<I", code, b1, u32(code, b1) ^ 0x1)

    def m_tap(code, att):                   # the instrument damaged
        code[PACK_LO + 4] ^= 0x10

    def m_r24(code, att):
        struct.pack_into("<H", code, R24_CELL, 5244)

    out = []
    for name, fn in [(k, v) for k, v in locals().items() if k.startswith("m_")]:
        try:
            r = build(quiet=True, do_rwd=False, base_bytes=base, mutate=fn, collect=True)
            fails = r["run"].failures
        except SystemExit as e:
            fails = [("S", str(e))]
        except Exception as e:                 # a mutation that breaks the decoder is also CAUGHT
            fails = [("S", f"raised {type(e).__name__}: {e}")]
        out.append((name, fails))
    return out


def main():
    base = Path(plain_image_path(BASE_NAME)).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise SystemExit("V293 base sha256 mismatch -- refusing to go further")
    v293rwd = [f for f in Path(RWD_DIR).glob("*-V293-*") if not f.name.startswith("SUPERSEDED")]
    if len(v293rwd) == 1:
        got = hashlib.sha256(v293rwd[0].read_bytes()).hexdigest()
        print(f"      V293 rwd on disk: {'UNCHANGED' if got == V293_RWD_SHA else '🛑 CHANGED'} ({got[:16]}...)")
        if got != V293_RWD_SHA:
            raise SystemExit("V293's own .rwd has changed -- stopping.")
    else:
        print(f"      (V293 rwd not uniquely present: {len(v293rwd)} -- tripwire SKIPPED and reported)")

    if "--grid" in sys.argv:
        print("=" * 118)
        print("  [0] ZERO-EDIT CONTROL -- every edit disabled must reproduce the V293 base BIT FOR BIT")
        sha0, d0, a0 = zero_edit_control(base)
        print(f"      {'[PASS]' if sha0 == BASE_SHA else '[FAIL]'} zero-edit rebuild == V293 ({d0} differing bytes, {a0} attributed)")
        if sha0 != BASE_SHA:
            raise SystemExit("ZERO-EDIT CONTROL FAILED")
        print("\n  [0b] THE POLE / GAIN LADDER -- dry run, NOTHING WRITTEN (K/J = 1.0 at each pole, and K/J 0.5 / 2.0 at 2 Hz)")
        print(f"      {'a':>5} {'b':>5} {'C':>5} | {'diff':>5} {'blk':>3} | image sha256[:16]   rwd sha256[:16]")
        for a, b in ((1015, 392), (1011, 567), (1005, 831), (1000, 1080), (1011, 284), (1011, 1134)):
            r = build(quiet=True, base_bytes=base, a_new=a, b_new=b)
            print(f"      {a:5d} {b:5d} {FB_NEW:5d} | {r['diff']:5d} {len(r['blocks']):3d} | {r['img_sha'][:16]}   {r['rwd_sha'][:16]}"
                  f"  {'<-- SHIPPED' if (a, b) == (FB_A_NEW, FB_B_NEW) else ''}")
        print("\n  [0c] MUTATION TEST -- flip each edit and prove the script FAILS")
        bad, res = [], mutation_test(base)
        for name, fails in res:
            print(f"      {'[CAUGHT]' if fails else '🛑 [MISSED]'} {name:24s} {len(fails)} assertion(s) fire")
            for _k, m in fails[:2]:
                print(f"                   - {m.split('.')[0][:100]}")
            if not fails:
                bad.append(name)
        print(f"      {'[PASS]' if not bad else '[FAIL]'} {len(res) - len(bad)}/{len(res)} mutations caught" + (f"  MISSED: {bad}" if bad else ""))
        return

    r = build()
    if WRITE_MODE == "rwd":
        print("\n  [14] WRITE -- guarded BEFORE the write")
        out_img, out_rwd = Path(plain_image_path(r["img_name"])), Path(RWD_DIR, r["rwd_name"])
        pre_i = [f.name for f in Path(ANALYSIS_ROOT).glob("_v294*") if not f.name.startswith("SUPERSEDED")]
        pre_r = [f.name for f in Path(RWD_DIR).glob("*-V294-*") if not f.name.startswith("SUPERSEDED")]
        if pre_i or pre_r:
            raise SystemExit(f"WRITE GUARD: a non-superseded V294 artifact already exists ({pre_i}, {pre_r}).")
        with open(out_img, "xb") as fh:
            fh.write(r["code"])
        with open(out_rwd, "xb") as fh:
            fh.write(r["rwd"])
        assert hashlib.sha256(out_img.read_bytes()).hexdigest() == r["img_sha"]
        assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"]
        print("\n      WROTE image + rwd, both re-hashed from the filesystem")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V294_WRITE=rwd to emit the files.  --grid for the control, ladder and mutation test.")


if __name__ == "__main__":
    main()
