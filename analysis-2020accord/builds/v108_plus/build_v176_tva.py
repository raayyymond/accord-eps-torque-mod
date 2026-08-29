#!/usr/bin/env python3
r"""
V176 -- BOTH LEVERS AT THE STRONGER DOSE.  Base = V175.  3 cells (12 bytes).
        = V175's engaged inertia revert  +  V174's slow pole 0.980.
        The maximum-attenuation build that still sits inside the kit's own lag guardrail.

WHY THIS EXISTS
---------------
The operator has stated the priority four times: eliminate the grinding and the ratcheting.  V175 is
the CHEAPER point on the pole curve (+29.1 ms of lag at 1 Hz); V174 is the stronger one (+42.8 ms).
V176 is simply V175 with V174's pole, i.e. **both levers, at the stronger dose, in one image**.

    build   poles          engaged inertia    ratchet @8.64   grind @21   lag @1 Hz
    flying  0.7966 pair    3.0x Honda            0.9789         0.8659       +2.1 ms
    V173    0.970/0.475    3.0x Honda            0.4761         0.1894      +29.1 ms
    V175    0.970/0.475    HONDA'S OWN           0.4761         0.1894      +29.1 ms   <- fly first
    V174    0.980/0.475    3.0x Honda            0.3393         0.1275      +42.8 ms
    V176    0.980/0.475    HONDA'S OWN           0.3393         0.1275      +42.8 ms   <- this build

** The section response of V176 is IDENTICAL to V174's ** -- the inertia revert is a different
mechanism in a different lane and does not change the biquad.  What V176 adds over V174 is the
removal of the 3.0x engaged apparent-inertia dose; what it adds over V175 is the stronger pole.

THE HONEST TRADE, STATED PLAINLY
---------------------------------
+42.8 ms of group delay at 1 Hz (-15.9 deg) versus V175's +29.1 ms.  ** That is lag the operator will
feel as steering weight, and he has said explicitly that apparent mass and friction must NOT be the
price of fixing the ratcheting. **  So this build is a CHOICE he makes, not a default:

  * fly V175 first if the lag matters as much as the ratcheting;
  * fly V176 first only if he wants the strongest available attack on the ratcheting and is willing
    to judge the lag on the same drive.

Either way the drive card's staging and endpoint power analysis apply unchanged, because the ENGAGED
vs MANUAL discriminator is a property of the inertia revert, which both builds carry.

WHAT IS *NOT* IN HERE, AND WHY
-------------------------------
  * `0xC63A6` (w[3], the virgin weight on the same inertia lane) is asserted FROZEN at 1024.  It
    multiplies the same quantity the revert already cut; spending it now would push the product BELOW
    Honda's own value on a lane whose sign chain is nine links long, with no more information than we
    have today.  It is the fine adjustment AFTER a drive result, not a stacking opportunity.
  * `p_slow` beyond 0.980.  The kit's own guardrail is ** do not cut past 0.985 without an operator
    lag verdict in hand **, and 0.980 is the last point below it.
  * anything in the FOC / current loop.  Untouched by design: a mistake there is a motor-stability
    problem, not a feel problem.

RISK
----
Identical class to V174 and V175 combined, and both were verified independently: three float32
calibration cells the kit has moved on-car without fault, plus two int16 triples reverting to values
Honda ships.  No cave, no code edit, no RAM claim.  Poles REAL at [0.980, 0.475] => overdamped,
cannot ring.  `C_B0` untouched => Honda's 55.23 Hz notch bit-for-bit.  GATE 2 magnitude: max |H| =
0.988 over 0.5-499 Hz => the section can only REMOVE loop gain.  GATE 1 as V175: `gp-0x6b26` has
exactly ONE writer (re-verified 2026-08-29 with a scanner carrying no opcode whitelist and no
disp-parity assumption, after two holes were found in the earlier one).
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

# --- PATH BOOTSTRAP -------------------------------------------------------------------------
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

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V176_WRITE", "").strip().lower()

BASE_NAME = "_v175_V175-V173BASE-GP6B26.ENGAGED.Y.REVERT.HONDA_plain_image.bin"
BASE_SHA = "a4e0dc4254ad8559e0c7744277cbe609d3c4c7da90284bc145d035a0816ae357"

P_SLOW, P_FAST = 0.980, 0.475
COEFFS = {
    0xC60A8: (0xBFBA3D71, "C_A8  -1.45500004    pole sum      -> poles 0.980 / 0.475, both REAL"),
    0xC60AC: (0x3EEE5604, "C_AC  +0.465499997   pole product"),
    0xC60B4: (0x3DB466E4, "C_B4  +0.0880868733  input gain, solved for unity DC"),
}
NOTCH_CAL, NOTCH_WORD = 0xC60B0, 0xBFF0BE0E
W3_CAL, W3_VAL = 0xC63A6, 1024          # asserted FROZEN -- not spent by this build
CLAMP_CAL, CLAMP_VAL = 0xC407E, 511
HONDA_Y = (-9830, -5734, -1966)
ENGAGED_ROWS = {0xD7A5C: "mode 26 (ENGAGED)", 0xD7A6C: "mode 27 (ENGAGED)"}
MANUAL_ROW = 0xD6A6C
FS = 1000.0
V175_AT_RATCHET, V175_AT_GRIND = 0.476076, 0.189446

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def f32_at(buf, off):
    return struct.unpack_from("<f", buf, off)[0]


def row(buf, off):
    return tuple(struct.unpack_from("<h", buf, off + 2 * i)[0] for i in range(3))


def resp(c, f):
    import cmath
    z = cmath.exp(2j * 3.141592653589793 * f / FS)
    num = c["C_B4"] * ((1 - c["C_AC"]) + (c["C_B0"] - c["C_A8"]) * z)
    den = z * z + c["C_A8"] * z + c["C_AC"]
    return abs(num / den + c["C_B4"])


def coeffs_of(buf):
    return {"C_A8": f32_at(buf, 0xC60A8), "C_AC": f32_at(buf, 0xC60AC),
            "C_B0": f32_at(buf, 0xC60B0), "C_B4": f32_at(buf, 0xC60B4)}


def poles_of(c):
    a, b = c["C_A8"], c["C_AC"]
    disc = a * a - 4 * b
    if disc >= 0:
        r = disc ** 0.5
        return [(-a + r) / 2, (-a - r) / 2], True
    r = (-disc) ** 0.5
    return [complex(-a / 2, r / 2), complex(-a / 2, -r / 2)], False


def gd_ms(c, f):
    import cmath
    h = 1e-3
    ph = []
    for x in (f - h, f, f + h):
        z = cmath.exp(2j * 3.141592653589793 * x / FS)
        ph.append(cmath.phase(c["C_B4"] * (z * z + c["C_B0"] * z + 1.0)
                              / (z * z + c["C_A8"] * z + c["C_AC"])))
    for i in (1, 2):
        while ph[i] - ph[i - 1] > 3.141592653589793:
            ph[i] -= 2 * 3.141592653589793
        while ph[i] - ph[i - 1] < -3.141592653589793:
            ph[i] += 2 * 3.141592653589793
    return -(ph[2] - ph[0]) / (2 * 2 * 3.141592653589793 * h) * 1000.0


def build():
    print("=" * 102)
    print("  V176 -- BOTH LEVERS AT THE STRONGER DOSE   (base V175: revert + poles 0.980)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V175 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE BASE ALREADY CARRIES THE INERTIA REVERT -- this build does NOT re-do it")
    for off, what in ENGAGED_ROWS.items():
        check(row(base, off) == HONDA_Y, f"0x{off:05X} {what} already Honda's {HONDA_Y}")
    check(row(base, MANUAL_ROW) == HONDA_Y, f"0x{MANUAL_ROW:05X} mode 24 (MANUAL) Honda's")
    check(struct.unpack_from("<H", base, CLAMP_CAL)[0] == CLAMP_VAL,
          f"0x{CLAMP_CAL:05X} clamp = {CLAMP_VAL}")

    print("\n  [3] THE EDIT -- three float32 cells, re-derived from the FORMULA")
    b0 = f32_at(base, NOTCH_CAL)
    a8 = struct.unpack("<f", struct.pack("<f", -(P_SLOW + P_FAST)))[0]
    ac = struct.unpack("<f", struct.pack("<f", P_SLOW * P_FAST))[0]
    b4 = struct.unpack("<f", struct.pack("<f", (1.0 + a8 + ac) / (2.0 + b0)))[0]
    for off, want in ((0xC60A8, a8), (0xC60AC, ac), (0xC60B4, b4)):
        w = struct.unpack("<I", struct.pack("<f", want))[0]
        check(w == COEFFS[off][0],
              f"0x{off:05X} formula gives raw word {w:08X}, matching the pinned constant")
    attributed = set()
    for off, (word, why) in sorted(COEFFS.items()):
        struct.pack_into("<I", code, off, word)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X}  {f32_at(base, off):+.9g} -> {f32_at(code, off):+.9g}   {why}")

    print("\n  [4] THE RESULT -- computed from the BUILT IMAGE's own bytes")
    old, new = coeffs_of(base), coeffs_of(code)
    p, real = poles_of(new)
    check(real, f"poles are REAL {[round(float(x), 5) for x in p]} -- overdamped, cannot ring")
    check(abs(max(abs(x) for x in p) - P_SLOW) < 1e-5,
          f"slow pole is {max(abs(float(x)) for x in p):.6f}, the intended {P_SLOW}")
    for f, tag in ((0.5, "DC"), (3.0, "driver band"), (8.64, "THE RATCHET"), (21.0, "THE GRIND")):
        print(f"      {f:6.2f} Hz   {resp(old, f):.4f} -> {resp(new, f):.4f}   "
              f"({resp(new, f)/resp(old, f):.3f}x)   {tag}")
    check(resp(new, 8.64) < V175_AT_RATCHET,
          f"ratchet {resp(new, 8.64):.6f} strictly better than V175's {V175_AT_RATCHET}")
    check(resp(new, 21.0) < V175_AT_GRIND,
          f"grind   {resp(new, 21.0):.6f} strictly better than V175's {V175_AT_GRIND}")
    check(abs(resp(new, 0.5) - 1.0) < 0.02, f"DC gain {resp(new, 0.5):.4f} within 2 % of unity")
    check(struct.unpack_from("<I", code, NOTCH_CAL)[0] == NOTCH_WORD,
          f"0x{NOTCH_CAL:05X} C_B0 UNCHANGED -- Honda's 55.23 Hz notch kept")
    check(resp(new, 55.23) < 0.001, f"55.23 Hz still notched: {resp(new, 55.23):.6f}")
    import numpy as _np
    g = max(resp(new, float(x)) for x in _np.arange(0.5, 499.5, 0.5))
    check(g <= 1.001, f"GATE 2 magnitude: max |H| to Nyquist is {g:.4f} -- never amplifies")

    print("\n  [5] WHAT THIS BUILD DELIBERATELY DOES NOT SPEND")
    check(struct.unpack_from("<H", code, W3_CAL)[0] == W3_VAL,
          f"0x{W3_CAL:05X} w[3] FROZEN at {W3_VAL} -- the virgin weight is NOT stacked here")
    check(struct.unpack_from("<H", code, CLAMP_CAL)[0] == CLAMP_VAL,
          f"0x{CLAMP_CAL:05X} clamp FROZEN at {CLAMP_VAL}")
    for off, what in ENGAGED_ROWS.items():
        check(row(code, off) == HONDA_Y, f"0x{off:05X} {what} still Honda's -- revert carried")
    lag = gd_ms(new, 1.0) - gd_ms(old, 1.0)
    print(f"      added group delay at 1 Hz vs V175: {lag:+.1f} ms")
    print(f"      ** TOTAL vs the flying build: about +42.8 ms at 1 Hz -- the operator's call **")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = struct.unpack_from("<I", code, blk[1])[0]
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [7] FULL BYTE DIFF vs V175 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload <= 12, f"{payload} payload bytes (<= 12: three float32 coefficients)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V176 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V176-V175BASE-POLE.0.980-REVERT.CARRIED"
    img_out = plain_image_path(f"_v176_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V176_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V175 remains fly-first unless the operator chooses the stronger dose knowing "
          "the lag. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
