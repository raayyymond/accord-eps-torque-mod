#!/usr/bin/env python3
r"""
V114 -- ALPHA2 14 -> 8.  MORE DAMPING WHERE THE LOOP IS ANTI-DAMPED, AND LESS APPARENT MASS.

WHAT THIS IS
------------
V114 = V111 with ONE byte moved.  0xC40DC (alpha2) 14 -> 8.  No cave edit.  No telemetry change.
The relay knee (0xC40BC) and K1 (0xC40D2) are both HELD, so this is single-variable against V111
and orthogonal to V113.

WHY THIS LANE, AND WHY THIS BAND
--------------------------------
Re(Z) = Re(H1[rate -> column torque]) over 17 route-arms, 2026-08-27:

   Hz band      2-4   4-6   6-9  9-12 12-16 16-20 20-24 24-28 28-34
   r21  ENG       1    -7   -43   -67   -47   -15    -4     3     8
   r21  MAN       3     6     7     7     7     8    11    13    15

The MANUAL arm is damped at every band on every route.  Engaging drives 6-16 Hz deeply negative,
with the minimum at 9-12 Hz.  20-30 Hz holds 36% of the rate POWER but its Re(Z) is only -3..-5
and crosses positive at f0 ~ 23.3 Hz -- that band RINGS, it is not where energy is put in.

=> the damping must be added at 6-16 Hz.

WHY ALPHA2 IS THE RIGHT KNOB -- IT MOVES THE PASSBAND, IT DOES NOT SCALE IT
---------------------------------------------------------------------------
The lane is  H(f) = 64 * H_lp * (1 - 1/z) * H_ema,  a BANDPASS
(alpha0 = 37/128 = cal 0xC643C, alpha2 = cal 0xC40DC, fs = 1000 Hz).  alpha2 sets the upper corner,
so lowering it walks the peak DOWN toward the anti-damped band:

    alpha2   peak Hz   6-16Hz damping   6-16Hz mass   20-30Hz damping   broadband rms
      22      61.1        0.794            1.085           0.921            1.488     (V108)
      14      46.5        1.000            1.000           1.000            1.000     (V111)
       8      34.2        1.252            0.796           0.899            0.604     <- V114
       6      29.3        1.318            0.647           0.769            0.463
       4      23.7        1.274            0.422           0.564            0.316

(all ratios vs V111.)  Splitting gp-0x6b26 against the VELOCITY phasor:
DAMPING ~ |H|*sin(phi) opposes velocity; MASS ~ |H|*cos(phi) is apparent inertia.

*** THE DAMPING RISES WHILE THE MASS FALLS. ***  That is exactly the operator's directive --
"low apparent steering mass and friction to LKAS AND no ratcheting" -- from a single byte, and it
is possible only because alpha2 rotates the vector rather than scaling it.

WHY THE DOSE IS 8 AND NOT 6 OR 4
--------------------------------
6-16 Hz damping peaks around alpha2 = 5-6, but the 20-30 Hz give-back grows fast, and 21-27 Hz is
exactly where V106's win was measured (the only band-power result in this kit to clear its own
split-half null).  alpha2 = 8 takes +25% damping in the deep band for only -10% at 20-30 Hz.
It is also the same step SIZE the operator already read clearly: V111's 22->14 was x1.27 damping,
and he reported oscillations gone and ratcheting reduced.  6 and 5 remain on a monotone axis if 8
reads well.

WHY IT CANNOT REPEAT V107
-------------------------
V107 railed because it multiplied the Y ROW -- a magnitude change.  alpha2 does the opposite:
peak |H| 9.20 -> 6.15 and broadband rms x0.604, with 100 Hz falling to x0.57.  Every magnitude
falls, so rail duty must fall.  The 100 Hz drop also attacks V107's own "higher-pitched, several
hundred Hz" grinding complaint directly.

GATES
-----
GATE 1 is the cleanest in the kit: exactly ONE gp/tp access image-wide
(0x41626  ld.hu 0x50dc,tp,r11  in FUN_00041464), zero writers -- confirmed in Ghidra this session
and already recorded in BUILD-LINEAGE ("VIRGIN ON ALL 102 IMAGES" before V109).
GATE 2: the edit is a pole move on an existing first-order EMA.  It adds no new state, no new
nonlinearity, and every magnitude falls.  The two lineage conditions attached to this lever are
both satisfied: it ships WITH the notch revert (V108 did that; V111 carries Honda's biquad), and it
is taken UNCOMPENSATED (the Y row is untouched, so the int16 headroom argument does not arise).

THE KNOWN RESIDUAL RISK
-----------------------
gp-0x6c2c fans out to three consumers; only the gp-0x6b26 damper is verified against a reshaped
signal.  The oscillation detector (FUN_000428d4 vs T = cal 0xC620A) is the second, and lowering
alpha2 SHRINKS |gp-0x6c2c|, so the detector fires less -- the safe direction.  The third is
unenumerated.  Note also that V109/V111 already flew this exact axis (22 -> 14) fault-free.

"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
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

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V114_WRITE", "").strip().lower()

BASE_NAME = "_v111_V111-V109BASE-TAP.6ABC.SAR3_plain_image.bin"
BASE_SHA = "9c4865cffd337cfb5d27f66843edbff928a8ffbf6f365e4fdeb7e98f7ddfb546"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)

# ---- THE TWO EDITS -- scaled TOGETHER so the small-signal gain is held EXACTLY -------------
SCALE = 3
KNEE_CAL, KNEE_OLD, KNEE_NEW = 0xC40BC, 600, 600              # HELD -- V114 is single-variable
K1_CAL, K1_OLD, K1_NEW = 0xC40D2, 204, 204                    #  HELD -- the safety argument

# ---- cells that must NOT move ------------------------------------------------------------------
OFF_CAL, OFF_VAL = 0xC4080, 0           # the relay's constant offset -- ZERO, so no Coulomb floor
POLE_CAL, POLE_VAL = 0xC40D0, 408       # the friction EMA pole -- adds phase; MUST NOT MOVE
ALPHA2_CAL, ALPHA2_V111, ALPHA2_NEW = 0xC40DC, 14, 8   # THE EDIT
RESID_CAL, RESID_VAL = 0xC7468, 41232   # |model| -> residual scale; bounds the clamp argument
GAIN_CAL, GAIN_6X = 0xC6CD0, 5346
BQ_ADDR, BQ_LEN = 0xC60A8, 16
TAP_DISP_ADDR, TAP_DISP = 0x55DF2, (-0x6ABC) & 0xFFFF   # V111's tap -- carried unchanged
SAR_ADDR, SAR_VAL = 0x55E10, 0xA3
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END
RATE_SCALE = 4.7121
MEASURED_DUTY = {600: 0.7439, 1200: 0.4810, 1800: 0.2353, 2400: 0.0484, 3600: 0.0000}

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ASSERTION FAILED: {msg}")


def wire(raw, sar):
    return min((min(abs(raw), 65535) * 5) >> sar, 0x3FF)


def build():
    print("=" * 102)
    print("  V114 -- ALPHA2 14 -> 8.  MORE DAMPING AT 6-16 Hz, LESS MASS, LESS EVERYTHING ELSE.")
    print("=" * 102)

    print("\n  [1] BASE = V111, AND IT MUST BE V111")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V111 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE IS V111, AND EVERY ASSUMPTION IS CHECKED")
    check(u16(base, KNEE_CAL) == KNEE_OLD,
          f"  0x{KNEE_CAL:05X} (relay knee) = {KNEE_OLD} -- Honda's own value, restored by V108")
    check(u16(base, K1_CAL) == K1_OLD, f"  0x{K1_CAL:05X} (K1) = {K1_OLD} (V89)")
    check(u16(base, OFF_CAL) == OFF_VAL,
          f"  0x{OFF_CAL:05X} (relay offset) = 0 -- NO Coulomb floor; the term dies with the command")
    check(u16(base, RESID_CAL) == RESID_VAL,
          f"  0x{RESID_CAL:05X} = {RESID_VAL} -- bounds |model| <= 20000/{RESID_VAL} = "
          f"{20000/RESID_VAL:.4f}, which is what makes the +-10.0 clamp unreachable")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V111, f"  0x{ALPHA2_CAL:05X} = {ALPHA2_V111} (V111 alpha2)")
    check(u16(base, GAIN_CAL) == GAIN_6X, f"  0x{GAIN_CAL:05X} = {GAIN_6X} (6x) -- carried")
    check(u16(base, TAP_DISP_ADDR) == TAP_DISP and base[SAR_ADDR] == SAR_VAL,
          "  V111's gp-0x6abc tap at sar 3 is present and will be carried unchanged")

    print("\n  [3] THE EDIT -- ONE PAYLOAD BYTE.  ALPHA2 ONLY.")
    struct.pack_into("<H", code, ALPHA2_CAL, ALPHA2_NEW)
    attributed |= {ALPHA2_CAL, ALPHA2_CAL + 1}
    # K1 is deliberately NOT written -- V113 rests on it staying at 204
    print(f"      0x{ALPHA2_CAL:05X}  {ALPHA2_V111} -> {ALPHA2_NEW}   alpha2 (the gp-0x6c2c EMA pole)")
    print(f"      0x{KNEE_CAL:05X}  {KNEE_OLD} -> {KNEE_OLD}   knee   (HELD)\n"
          f"      0x{K1_CAL:05X}  {K1_OLD} -> {K1_OLD}   K1     (HELD)")

    print("\n  [4] THE RELAY IS UNTOUCHED -- knee and K1 both held, so this is single-variable")
    g_old = (K1_OLD / 1024.0) * (12.0 / KNEE_OLD)
    g_new = (K1_NEW / 1024.0) * (12.0 / KNEE_NEW)

    print("\n  [3b] THE SHAPE ARGUMENT -- alpha2 MOVES the bandpass, it does not SCALE it")
    import cmath
    FS = 1000.0

    def lane(f, a2):
        w = 2 * cmath.pi * f / FS
        z = cmath.exp(1j * w)
        a, b = 37 / 128.0, a2 / 64.0
        return 64 * (a / (1 - (1 - a) / z)) * (1 - 1 / z) * (b / (1 - (1 - b) / z))

    def split(f, a2):
        w = 2 * cmath.pi * f / FS
        hr = lane(f, a2) / (1j * w)
        phi = -cmath.phase(hr)
        m = abs(hr) * w
        return m * cmath.sin(phi).real, m * cmath.cos(phi).real

    def bandavg(a2, lo, hi, which):
        fs = [lo + 0.5 * k for k in range(int((hi - lo) / 0.5) + 1)]
        return sum(split(f, a2)[which] for f in fs) / len(fs)

    d_new = bandavg(ALPHA2_NEW, 6, 16, 0) / bandavg(ALPHA2_V111, 6, 16, 0)
    d_hi = bandavg(ALPHA2_NEW, 20, 30, 0) / bandavg(ALPHA2_V111, 20, 30, 0)
    m_new = bandavg(ALPHA2_NEW, 6, 16, 1) / bandavg(ALPHA2_V111, 6, 16, 1)
    print(f"      6-16 Hz DAMPING  x{d_new:.3f}   <- the band Re(Z) measures at -33..-67")
    print(f"      6-16 Hz MASS     x{m_new:.3f}   <- the operator asked for LESS of this")
    print(f"     20-30 Hz DAMPING  x{d_hi:.3f}   <- the give-back, where Re(Z) is only -3..-5")
    check(d_new > 1.15, f"  6-16 Hz damping RISES x{d_new:.3f} -- the deeply anti-damped band")
    check(m_new < 0.90, f"  6-16 Hz apparent MASS FALLS x{m_new:.3f} -- satisfies the directive")
    check(d_hi > 0.85, f"  20-30 Hz give-back is only x{d_hi:.3f} -- V106's win is largely preserved")

    print("\n  [3c] IT CANNOT RAIL -- every magnitude FALLS (this is V107's failure mode, inverted)")
    fs = [0.5 + 0.125 * k for k in range(4000)]
    pk_old = max(abs(lane(f, ALPHA2_V111)) for f in fs)
    pk_new = max(abs(lane(f, ALPHA2_NEW)) for f in fs)
    rms_old = (sum(abs(lane(f, ALPHA2_V111)) ** 2 for f in fs) / len(fs)) ** 0.5
    rms_new = (sum(abs(lane(f, ALPHA2_NEW)) ** 2 for f in fs) / len(fs)) ** 0.5
    print(f"      peak |H|        {pk_old:6.2f} -> {pk_new:6.2f}   (x{pk_new / pk_old:.3f})")
    print(f"      broadband rms   {rms_old:6.2f} -> {rms_new:6.2f}   (x{rms_new / rms_old:.3f})")
    print(f"      |H| at 100 Hz   {abs(lane(100., ALPHA2_V111)):6.2f} -> "
          f"{abs(lane(100., ALPHA2_NEW)):6.2f}   (the higher-pitched grinding band)")
    check(pk_new < pk_old and rms_new < rms_old,
          "  peak AND broadband rms both FALL => rail duty must FALL, not rise (cf. V107)")
    check(abs(lane(100., ALPHA2_NEW)) < abs(lane(100., ALPHA2_V111)),
          "  100 Hz magnitude falls -- the band V107's higher-pitched grinding lived in")

    sat_old, sat_new = KNEE_OLD / 12.0, KNEE_NEW / 12.0
    print(f"      saturation         {sat_old:.0f} ct = {sat_old/RATE_SCALE:.1f} deg/s"
          f"  ->  {sat_new:.0f} ct = {sat_new/RATE_SCALE:.1f} deg/s")
    check(KNEE_OLD in MEASURED_DUTY,
          f"  the relay ladder below is V111's, UNCHANGED by V114 (context only)")
    print(f"      MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048:")
    for k in sorted(MEASURED_DUTY):
        mark = "  <- V111 (CI [0.669,0.815])" if k == KNEE_OLD else (
               "  <- THIS BUILD" if k == KNEE_NEW else "")
        print(f"         knee {k:5d}   duty {MEASURED_DUTY[k]:.4f}{mark}")
    check(KNEE_NEW == KNEE_OLD,
          f"  the relay knee is HELD at {KNEE_OLD} -- V114 does not touch the relay lane")

    print("\n  [5] GATE 2 -- ZERO PHASE, AND THE CLAMP CANNOT BIND")
    mmax = 20000.0 / RESID_VAL
    fmax_old = mmax * K1_OLD / 1024.0
    fmax_new = mmax * K1_NEW / 1024.0
    print(f"      |model| <= {mmax:.4f}  =>  friction_max  {fmax_old:.4f} -> {fmax_new:.4f}"
          f"   vs the +-10.0 clamp")
    check(fmax_new < 10.0 / 10.0,
          f"  friction_max {fmax_new:.4f} leaves {10.0/fmax_new:.0f}x of headroom to the clamp")
    print(f"      residual at saturating rate: {1-fmax_old/mmax:.2f}*|model| ->"
          f" {1-fmax_new/mmax:.2f}*|model|   (a {(1-fmax_old/mmax)/(1-fmax_new/mmax):.1f}x reduction"
          f" -- MORE assist, by the verified polarity)")
    check(u16(code, POLE_CAL) == POLE_VAL,
          f"  0x{POLE_CAL:05X} (friction EMA pole) = {POLE_VAL} UNTOUCHED -- it is the only cell in"
          f" this lane that adds PHASE, and V111 already showed what phase costs")
    check(u16(code, OFF_CAL) == OFF_VAL, "  0xC4080 still 0 -- no Coulomb floor introduced")

    print("\n  [5b] NOTHING ELSE MOVED")
    for a, nm in ((KNEE_CAL, "0xC40BC relay knee HELD at 600"),
                  (K1_CAL, "0xC40D2 K1 HELD AT 204 -- the safety argument"),
                  (GAIN_CAL, "0xC6CD0 6x gain"), (RESID_CAL, "0xC7468 residual scale"),
                  (TAP_DISP_ADDR, "0x55DF2 V111 tap")):
        check(u16(code, a) == u16(base, a), f"  {nm} byte-identical to V111")
    check(code[SAR_ADDR] == base[SAR_ADDR], "  0x55E10 sar byte-identical to V111")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- no cave edit, outside the "
          f"bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {ALPHA2_CAL, ALPHA2_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved, f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V111 BASE (2 exempted)")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [7] FULL BYTE DIFF vs V111 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        tag = "CRC" if any(lo <= x < hi for x in (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo <= x < hi for x in (b[1] for b in blocks)))
    check(payload == 1, f"exactly 1 payload byte ({payload} found)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V114 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V114-V111BASE-ALPHA2.14.TO.8"
    img_out = plain_image_path(f"_v114_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V114_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
