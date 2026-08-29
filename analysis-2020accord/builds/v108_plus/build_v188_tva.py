#!/usr/bin/env python3
r"""
V188 -- MOVE HONDA'S NOTCH ONTO THE RATCHET.  Base = V185.  Four float32 cells.

WHAT IS NEW AS A CLASS
----------------------
Every filter build in the arc (V43 pole, V173/V174/V184 poles) moved the DENOMINATOR -- the poles --
which makes a LOW-PASS.  V188 moves the NUMERATOR.  That has never been done.

The section is  H(z) = B4*(z^2 + B0*z + 1) / (z^2 + A8*z + AC).  The numerator's roots have product
1, so they sit ON the unit circle for every value of B0: the numerator is ALWAYS a perfect notch,
and B0 alone sets its frequency,  B0 = -2*cos(2*pi*f0/fs).  Honda placed it at 55.226 Hz.

WHY A NOTCH AND NOT ANOTHER LOW-PASS
------------------------------------
A low-pass cannot separate 8 Hz from 3 Hz -- they are only 1.5 octaves apart -- so it pays for
ratchet attenuation with phase in openpilot's band:

    lever                          ratchet atten   phase @3 Hz   dB per degree
    V184 (poles 0.980 low-pass)         -8.8 dB       -40.5 deg       0.22
    best low-pass at a <=10 deg budget  -0.8 dB       -10.0 deg       0.08
    V188 (notch on the ratchet)         -6.0 dB        -9.9 deg       0.61   <-- 2.8x better

A notch returns phase to ~0 away from itself, which is exactly why it can attenuate 8 Hz while
leaving 1-3 Hz alone.  This was shown to be a FORCED tradeoff, not a search failure: unity DC gain
pins B4 = (1+A8+AC)/(2+B0), and with the notch near 8 Hz that forces the poles within ~0.05 of the
unit circle -- so REAL poles (a low-pass) land their corner at 8 Hz too, reproducing V184's problem.
One biquad cannot serve LKAS phase, ratchet attenuation and 55 Hz protection at once.

WHY THE GRIND AND NOT THE RATCHET -- ONE BIQUAD, ONE NOTCH, AND THE MIDDLE IS DOMINATED
---------------------------------------------------------------------------------------
Optimising a single notch for the COMBINED objective puts it at 14.1 Hz and yields only 2.2x /
2.3x -- WORSE than either specialist.  A narrow notch cannot cover two separated bands, so this is
a genuine either/or:

    design                  ratchet 5-12   grind 15-25   phase @3 Hz
    V187  notch 8.80 Hz         6.0x          0.9x         -10.0 deg
    V188  notch 19.40 Hz        1.3x         14.3x          -3.8 deg   <-- this build
    middle notch 14.10 Hz       2.2x          2.3x          -8.2 deg   (dominated)

THE MECHANISM DECIDES IT, and the record already established both mechanisms:
  * THE GRIND IS A CLOSED-LOOP INSTABILITY.  21.09 Hz, ** 9,200x less power with LKAS off **, and
    de-confounded 2x2 attribution to the LKAS gain 0xC6CD0 (effect 2.7-3.9x).  A notch inside the
    loop AT the unstable frequency BREAKS THE LOOP -- that is a cure, not a mitigation.
  * THE RATCHET IS A PLANT RESONANCE.  Ring-down zeta 0.017-0.036, Q 14-29, motor/rack-side, limit
    cycle EXCLUDED.  A notch on the command only reduces its EXCITATION; road input still rings the
    mode.  And the ratchet already has an INDEPENDENT lever on this build -- the engaged inertia
    revert carried from V184.
  * The biquad is ENGAGED-GATED (0xC649B = 1, arm = the LKAS engagement flag) and the grind is
    ENGAGED-ONLY on 7/7 routes.  An engaged-only filter against an engaged-only instability.

It also costs a THIRD of the phase (-3.8 vs -10.0 deg at 3 Hz), because 19 Hz is far from
openpilot's band -- which is why the notch can be made WIDE (r 0.9300 vs 0.9795) and still pass.
Per-route grind peaks: p10 15.74 / median 19.92 / p90 21.68 Hz, so width is what matters here.

    15 Hz -6.2 dB   18 Hz -15.3 dB   21 Hz -13.7 dB   23 Hz -6.7 dB   25 Hz -3.0 dB

THE COST, STATED PLAINLY -- HONDA'S 55 Hz NULL IS GIVEN UP
-----------------------------------------------------------
There are only two zeros.  Using them at 8.3 Hz means 55.226 Hz goes from |H| = 0.0007 (-96 dB) to
~1.04 (+63 dB).  Our logging is 100 Hz, Nyquist 50, so 55 Hz is NOT DIRECTLY OBSERVABLE.

It was tested indirectly by ALIASING: 55.226 Hz sampled at 100 Hz folds to 44.774 Hz, inside band.
    across 295 routes:  median ratio 0.99, max 2.69, ZERO routes above 3
    control frequencies with no special meaning (41/43/46.5/48 Hz):  maxima 3.6 - 6.5
=> the alias bin is QUIETER than arbitrary neighbours.  EVIDENCE against a road-excited 55 Hz plant
   mode -- the notch shapes what the ECU COMMANDS, not what the torque sensor SEES, so a mechanical
   mode would still alias through.
!! HONEST LIMIT: the notch is active in every drive in the corpus, so this CANNOT distinguish "no
   55 Hz source" from "a command-excited loop mode that the notch is currently suppressing."  That
   second case is the one that would bite, and it is NOT excluded.  BELIEF, not EVIDENCE.
   Mitigation: this is a CAL-ONLY edit.  Caves are this kit's only bricking class; a cal edit is
   recoverable by reflashing.  If the car makes a new high note, stop and reflash V185.

RESIDUAL RISK -- THE NOTCH'S OWN PHASE SWING
--------------------------------------------
A notch flips phase through itself.  At 7.0 Hz the section still has |H| = 0.60 but -47.9 deg of
lag.  openpilot's band (0.5-3 Hz) sees only -9.9 deg, so ITS margin is safe.  But the ratchet is
engaged-AMPLIFIED 3.58x, i.e. a loop is involved at ~8 Hz, and adding lag on the low side of the
notch could in principle move that amplification down to ~7 Hz rather than remove it.
=> a drive discriminates: ratchet GONE vs ratchet MOVED DOWN in frequency.  Both are informative;
   the scorer prints the peak frequency, so this is pre-registered and cannot be read after the fact.

WHAT IS CARRIED FROM V185
-------------------------
    K1 -> Honda (V177) - accel EMA alpha -> Honda (V179) - w[3] halved (V181)
    engaged inertia dose -> Honda, engaged == manual in every data table (V184)
    the 427 probe on gp-0x6ac0 (V183)
    0xC407E hard-fault interlock FROZEN at 511
"""
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

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
WRITE_MODE = os.environ.get("ACCORD_V188_WRITE", "").strip().lower()
BASE_NAME = "_v185_V185-V184BASE-BIQUAD.HONDA.PHASE.SAFE_plain_image.bin"
BASE_SHA = "54e114d172d89dcb049a28e2ef8e43dfbdb53c515a3bd05ce6e069a9d4c94935"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
BIQUAD = (A8_OFF, AC_OFF, B0_OFF, B4_OFF)

# --- THE SPEC IS THE FORMULA, NEVER A TYPED DECIMAL --------------------------------------------
# A 6-dp decimal does not round-trip a float32; three agents once produced three byte strings for
# one coefficient, none mis-encoded -- they had encoded three DIFFERENT NUMBERS.  So the two design
# parameters are exact, everything else is derived, and every assertion below is checked against the
# ENCODED float32 read back out of the image -- not against these Python doubles.
SEC_FS = 1000.0
F0 = 19.40         # notch centre, Hz -- ON THE GRIND, minimax over 67 routes
RP = 0.9300        # pole radius     -- WIDE: 19 Hz is far from openpilot, so we can afford it

FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
CARRIED_U16 = {0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0x55DF2: ("427 probe source gp-0x6ac0 (V183)", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 4 (V183)", 0xA4)}
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def design():
    """The four coefficients, from the two design parameters.  Doubles here; the image gets f32."""
    th = 2.0 * math.pi * F0 / SEC_FS
    b0 = -2.0 * math.cos(th)
    a8 = -2.0 * RP * math.cos(th)
    ac = RP * RP
    b4 = (1.0 + a8 + ac) / (2.0 + b0)
    return a8, ac, b0, b4


def resp(img, fr):
    """|H| and phase AT A FREQUENCY, computed from the ENCODED float32 in the image."""
    import cmath
    z = cmath.exp(2j * math.pi * fr / SEC_FS)
    h = (f32(img, B4_OFF) * (z * z + f32(img, B0_OFF) * z + 1.0)
         / (z * z + f32(img, A8_OFF) * z + f32(img, AC_OFF)))
    return abs(h), math.degrees(cmath.phase(h))


def build():
    print("=" * 102)
    print("  V188 -- NOTCH ON THE GRIND, THE CLOSED-LOOP INSTABILITY   (base V185)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V185 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] DESIGN PARAMETERS -> COEFFICIENTS (formula, not typed decimals)")
    a8, ac, b0, b4 = design()
    print(f"      F0 = {F0:.2f} Hz   RP = {RP:.4f}   fs = {SEC_FS:.0f} Hz")
    print(f"      B0 = -2*cos(2*pi*F0/fs)   = {b0:+.10g}")
    print(f"      A8 = -2*RP*cos(2*pi*F0/fs)= {a8:+.10g}")
    print(f"      AC = RP*RP                = {ac:+.10g}")
    print(f"      B4 = (1+A8+AC)/(2+B0)     = {b4:+.10g}")

    print("\n  [3] THE EDIT -- four float32 cells")
    attributed = set()
    for off, val, nm in ((A8_OFF, a8, "A8"), (AC_OFF, ac, "AC"),
                         (B0_OFF, b0, "B0"), (B4_OFF, b4, "B4")):
        before = f32(code, off)
        struct.pack_into("<f", code, off, val)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X} {nm}  {before:+.9g} -> {f32(code, off):+.9g}")

    print("\n  [4] ASSERT AGAINST THE ENCODED float32, NOT THE PYTHON DOUBLES")
    for off, val, nm in ((A8_OFF, a8, "A8"), (AC_OFF, ac, "AC"),
                         (B0_OFF, b0, "B0"), (B4_OFF, b4, "B4")):
        enc = f32(code, off)
        rel = abs(enc - val) / max(abs(val), 1e-30)
        check(rel < 1e-6, f"{nm} encodes to {enc:+.9g}, rel err {rel:.2e} < 1e-6")

    print("\n  [5] DC GAIN -- the assist level the driver feels MUST NOT MOVE")
    mag0, _ = resp(code, 0.0)
    check(abs(mag0 - 1.0) < 2e-3, f"|H(DC)| = {mag0:.6f} (unity within 0.2%)")

    print("\n  [6] GATE 2 MAGNITUDE -- max |H| over 0-500 Hz")
    grid = [x * 0.25 for x in range(1, 240)] + [60.0 + 2.0 * k for k in range(221)]
    mx = max(resp(code, x)[0] for x in grid)
    at = max(grid, key=lambda x: resp(code, x)[0])
    check(mx <= 2.0, f"max |H| = {mx:.4f} at {at:.2f} Hz (<= 2.0)")

    print("\n  [7] GATE 2 PHASE -- openpilot's band, vs what the car flies today")
    for fr in (0.5, 1.0, 2.0, 3.0):
        _, pn = resp(code, fr)
        _, pb = resp(base, fr)
        d = pn - pb
        check(abs(d) <= 10.0, f"{fr:4.1f} Hz added lag {d:+6.2f} deg (budget 10.0)")

    print("\n  [8] THE NOTCH IS WHERE IT WAS DESIGNED, AND DEEP")
    mags = [(x, resp(code, x)[0]) for x in [15.0 + 0.02 * k for k in range(501)]]
    fmin, vmin = min(mags, key=lambda t: t[1])
    check(abs(fmin - F0) < 0.10, f"deepest point at {fmin:.2f} Hz (designed {F0:.2f})")
    check(vmin < 0.05, f"notch depth |H| = {vmin:.5f} at the centre")
    print("      response across the grind band:")
    for x in (8.8, 12.0, 15.0, 17.0, 18.0, 19.4, 21.0, 23.0, 25.0, 30.0):
        m, p = resp(code, x)
        mb, _ = resp(base, x)
        print(f"        {x:5.2f} Hz  |H| {m:7.4f}  ({20 * math.log10(max(m / mb, 1e-12)):+6.1f} dB"
              f" vs V185)   phase {p:+7.1f} deg")

    print("\n  [9] WHAT WE GIVE UP -- Honda's 55.226 Hz null, DISCLOSED NOT HIDDEN")
    m55n, _ = resp(code, 55.226)
    m55b, _ = resp(base, 55.226)
    print(f"      55.226 Hz  |H| {m55b:.6f} -> {m55n:.6f}   "
          f"({20 * math.log10(max(m55n / max(m55b, 1e-12), 1e-12)):+.1f} dB)")
    print("      alias test, 295 routes: median 0.99, max 2.69, zero routes > 3;")
    print("      controls 41/43/46.5/48 Hz reach 3.6-6.5  => no road-excited 55 Hz mode.")
    print("      NOT excluded: a command-excited loop mode the notch currently suppresses.")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m in (26, 27):
        p = u32(code, PTR_I + 4 * m)
        n = s16(code, p)
        Y = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
        check(Y == HONDA_Y, f"inertia m{m} Y = {Y} -- the dose revert CARRIED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, not the bricking class")

    print("\n  [11] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = u32(code, blk[1])
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block byte-identical to base")

    print("\n  [12] FULL BYTE DIFF vs V185")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 16, f"{len(pay)} payload bytes (<= 16: four float32 cells)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V188 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V188-V185BASE-NOTCH.ON.THE.GRIND"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v188_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V188_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** 15-25 Hz power: median 0.0701 = 14.3x, p90 0.1045 = 9.6x, for -3.8 deg @3 Hz. **")
    print("  ** COST: Honda's 55 Hz null is given up. Cal-only, so reflash V185 recovers. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
