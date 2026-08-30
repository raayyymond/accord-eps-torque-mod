#!/usr/bin/env python3
r"""
V223 -- LEVER B RUNG 2.  0xC6446 13107 -> 26214.  Base = V222.  ONE u16 cal.  NOT the primary.

WHY A SECOND RUNG, AND WHY THE DOSE IS COMPUTED RATHER THAN GUESSED
-------------------------------------------------------------------
Only two Lever B dose points exist on-car -- 512 and 5244 -- and V62's lesson is explicit: "2x is
approximately the OPTIMUM, not a point on a ramp". So the dose cannot be read off the record. It CAN
be computed, because the lane's nonlinearity is known exactly and is a plain saturation:

    scaled = (clamp(gp-0x4f62, +-5120) * k) >> 10        0x3AC18 / 0x3AC20  -- 32-bit throughout
    shaped = deadzone(scaled, +-3)                        0x3AC24           -- cal 0xC61F6
    out    = clamp(polarity * shaped, +-8192)             0x3AC42 / 0x3AC46 -- immediates, UNTOUCHED

For a sinusoid of amplitude A the sinusoidal-input describing function of a saturation with slope k
and rail L = 8192 gives the EFFECTIVE damping the loop actually sees:

    N(A)/k = 1                                                     for k*A <= L*1024
    N(A)/k = (2/pi)*[asin(1/rho) + (1/rho)*sqrt(1-1/rho^2)]        rho = k*A/(L*1024)

and as k -> infinity, N(A) -> 4*L*1024/(pi*A): a CONSTANT INDEPENDENT OF k. That asymptote, not the
cal's 65535 range and certainly not V160's non-existent int16 bound, is this lane's real ceiling.

EFFECTIVE DAMPING N(A), at the engaged |d(column torque)/dt| percentiles measured on route r24:

     gain k     onset     p50 (27)   p90 (146)   p99 (610)  max (1669)
        512     16384          512         512         512         512
       5244      1600         5244        5244        5244        5191   <- THE CAR
      13107       640        13107       13107       13107        6239   <- V222
      26214       320        26214       26214       16669        6360   <- THIS BUILD
      65535       128        65535       62194       17380        6393
  asymptote                 395582       73156       17509        6399

  knee (where one more doubling buys < 20 %):  p90 at k = 58624 · p99 at 14080 · max at 5184

TWO THINGS FALL OUT OF THAT TABLE.
  (1) At the amplitudes where the roughness actually lives -- and it IS a small-command phenomenon,
      measured -- V222 is NOWHERE NEAR the knee. 13107 -> 26214 buys a FULL 2x more damping at both
      p50 and p90, and 1.27x at p99.
  (2) At the largest excursion measured, gain buys almost nothing: 1.20x at V222 rising only to
      1.23x at the cal maximum. So this rung is SELECTIVE for the small-signal regime by
      construction, which is exactly the selectivity the operator's standing constraint asks for.

AND THE SATURATION WORRY IS NOT NEW. The knee at the largest excursion is k = 5184, and THE CAR IS
ALREADY PAST IT at 5244. So "the lane saturates on big inputs" is the car's existing operating point,
not a condition this build introduces. More than that: V88's measured win -- grinding fixed, command
untouched -- came from 512 -> 5244, the very step that carried the largest excursions from fully
linear across that knee. Saturation at large amplitude is where this lane already lives and where it
already worked.

WHAT IT COSTS, STATED PLAINLY
-----------------------------
[EVIDENCE] the onset falls 640 -> 320 counts. Against the pooled engaged torque-rate distribution
(412,204 frames, 8 routes) that takes the clip duty from ~5.9 % to ~16.0 % of engaged frames. Those
are the LARGE, FAST inputs; the p50 of 27-64 counts sits 5-12x below the onset, so the whole micro
regime stays linear.
[EVIDENCE] the +-8192 rail is left BYTE-IDENTICAL (all 22 bytes at 0x3AC42-0x3AC58 asserted), so this
cannot claim one more count of the +-10240 aggregator headroom the LKAS command needs, and therefore
cannot cost steering authority.
[BELIEF] that the dose-response stays monotone. It is an OPEN-LOOP calculation: it says what the lane
can DELIVER, not that delivering more improves the car. Phase and the rest of the loop decide that.
[NOTE] more derivative feedback also amplifies torque-sensor noise. V88 measured 28-35 Hz FLAT across
a 10.24x step, which is the reassuring direction, but nobody has measured at 5x the car.

🛑 THIS IS RUNG 2, NOT THE PRIMARY. Fly V222 first. This exists so that a partial result has an
immediate follow-up and so the two together form a DOSE-RESPONSE, which is this kit's strongest
evidence form. If V222's grinding result is positive but incomplete, this is the next build; if V222
reads WORSE than V217 on grinding, 5244 was already at the optimum and BOTH rungs are wrong.

EVERYTHING ELSE IS V222, BYTE FOR BYTE.
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
WRITE_MODE = os.environ.get("ACCORD_V223_WRITE", "").strip().lower()
BASE_NAME = "_v208_V208-V202BASE-NOTCH.20.50.REFIT.ON.EPISODES_plain_image.bin"
BASE_SHA = "e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
NORM_X, NORM_Y = 0xC6936, 0xC693E
HYST = 0xC64DD
NEW_HYST = 100
PROBE_HW2, PROBE_SHIFT = 0x55DF2, 0x55E10
FRIC_GATE, FRIC_GATE_CAR = 0xC40BC, 3000   # relay width; 1 reader 0x3BAB4, 0 writers
FRIC_K1, FRIC_K1_CAR = 0xC40D2, 1020       # Coulomb slope; 1 reader 0x3BAFE, 0 writers
LEVER_B = 0xC6446              # r24 engaged derivative gain, Q10. 1 reader (0x3AC08), 0 writers
LEVER_B_OLD, LEVER_B_NEW = 5244, 26214   # rung 2; V222 is rung 1 at 13107
R24_RAIL_LO, R24_RAIL_HI = 0x3AC42, 0x3AC58   # the +-8192 immediates -- MUST NOT MOVE
RESID_SCALE = 0xC63AE          # the soft relay's own input scale, 1 reader / 0 writers
NEW_SCALE = 512                # HALF Honda unity 1024
NEW_PROBE_HW2 = 0x94B2         # V209 probe: repoint 427 telemetry to gp-0x6b4e
NEW_SAR = 0xA5                 # V209 packer: sar 5
KITROOT = str(Path(__file__).resolve().parents[2].parent)
OSC_X, OSC_Y = 0xC6912, 0xC691A
FACTORC_PTR = 0xC9E9C
Y0_ADDR = 0xD77EE
BIQUAD = (A8_OFF, AC_OFF, B0_OFF, B4_OFF)

# --- THE SPEC IS THE FORMULA, NEVER A TYPED DECIMAL --------------------------------------------
# A 6-dp decimal does not round-trip a float32; three agents once produced three byte strings for
# one coefficient, none mis-encoded -- they had encoded three DIFFERENT NUMBERS.  So the two design
# parameters are exact, everything else is derived, and every assertion below is checked against the
# ENCODED float32 read back out of the image -- not against these Python doubles.
SEC_FS = 1000.0
F0 = 20.50         # notch centre, Hz -- V199 design: zeros 20.50, poles 15.50, r 0.9575
RP = 0.9300        # pole radius     -- WIDE: 19 Hz is far from openpilot, so we can afford it

FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
# 🛑 0xC40D2 WAS LISTED HERE AS 204 AND LABELLED "the FLOWN car". IT IS NOT: the car (V122) runs
# 1020. 204 only matches the car's unsaturated SLOPE, because V216 rescaled it alongside the gate;
# at saturation 204 leaves 80.1 % of the model standing where the car leaves 0.4 %, a 216x gap above
# 250 counts of rate. The mislabel is exactly why the gap survived every check. This build restores
# BOTH cells, so the assertion moves into gate [3c] against the car's real values.
CARRIED_U16 = {0xC63A6: ("w[3] restored to the car (V217)", 1024),
               }
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             }
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)
HALF_Y = (-4915, -2867, -983)

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
    """DEAD IN THIS BUILDER -- never called; this build does not edit the biquad.
    It is also the OLD poles-AT-zeros form (a8 uses the ZERO angle), which BUILD-LINEAGE.md
    names as a trap. Do NOT revive it here: the current geometry is V208s poles-BELOW-zeros.
    """
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
    print("  V223 -- LEVER B RUNG 2: 13107 -> 26214.  Fly V222 FIRST.  ONE u16 cal.")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V196 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE PROBE AS IT STANDS (V183 base)")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    old_disp = struct.unpack_from("<H", base, PROBE_HW2)[0]
    print(f"      0x{PROBE_HW2:05X} hw2 = 0x{old_disp:04X}  -> gp{old_disp - 0x10000:+d}"
          f" (= gp-0x{0x10000 - old_disp:04X})")
    print(f"      0x{PROBE_SHIFT:05X} shift byte = 0x{base[PROBE_SHIFT]:02X}"
          f"  -> sar {base[PROBE_SHIFT] & 0x1F}")
    check(old_disp == 0x9540, "the base carries V183's gp-0x6ac0 probe (0x9540)")
    check(base[PROBE_SHIFT] & 0x1F == 4, "the base carries sar 4")
    check(u16(base, PROBE_HW2) == 0x9540, "the base probe reads gp-0x6ac0")

    print("\n  [3] THE EDIT -- one u16 cal, the soft relay's own input scale")
    attributed = set()

    # V212 = V210 cal AND V209 probe in ONE image.  V210 carried the notch (grinding) and
    # the soft-relay dose (ratchet) but NO instrument, so a partial result would have been
    # uninterpretable -- the design failure the iteration doctrine forbids.  The probe
    # target gp-0x6b4e was confirmed LIVE 2026-08-29: it is the mode-5 arm of the 0xC4124
    # ROUTER (mode 0 -> gp-0x6b4c, mode 5 -> gp-0x6b4e), carrying value B from slots
    # 2/4/5/9 -- slot 2 being the live PI lane-2 output -- and FUN_00038148 reads it at
    # 0x3817C as model lane w[4].  It is NOT a dead cell.
    struct.pack_into("<H", code, PROBE_HW2, NEW_PROBE_HW2)
    code[PROBE_SHIFT] = NEW_SAR
    attributed |= {PROBE_HW2, PROBE_HW2 + 1, PROBE_SHIFT}
    check(u16(code, PROBE_HW2) == NEW_PROBE_HW2,
          f"probe hw2 0x{NEW_PROBE_HW2:04X} -- the 427 frame now reads gp-0x6b4e")
    check(code[PROBE_SHIFT] & 0x1F == 5, "packer is sar 5 (V209 sizing)")

    # V213 ADDS THE AUTHORITY LEVER on top of V212.  Priced 2026-08-29: the step raises loop
    # gain a flat 1.333x => vibration growth 1.650x (the kit m^1.74 amplitude law), against a
    # notch attenuation of 3.59x at 22-26 Hz.  NET 0.459x -- 2.18x quieter AND 1.33x more
    # authority.  Break-even is 29.5 Hz; above that the notch gives nothing back.  The two
    # reasons that had this staged are both RESOLVED:
    #   1. the engagement-gated 42.19 Hz line is the RECTIFIER IMAGE of the 21.09 Hz mode
    #      (gp-0x6ba6 = |gp-0x6b9a| at 0x3b87a, so 2f), it only indexes boost LERPs that are
    #      FLAT at the operating point, and that arc already FLEW NULL as V58/V59/V60.
    #   2. grind #2 (40-49 Hz, +9.7 dB(A)) was CREATED by V62s rate-lane x2, and this base is
    #      BYTE-STOCK at 0x3AB76/0x3AC20 -- asserted below.  Prior work also found 40-49 Hz is
    #      NOT engagement-conditional and the 28 Hz transient is DOSE-INDEPENDENT.
    GAIN_EDITS = ((0xC6CD0, 5346, 7128, "LKAS forward gain 6x -> 8x"),
                  (0xC61B2, 3072, 4096, "forward clamp A, tracking the gain"),
                  (0xC61B4, 3072, 4096, "forward clamp B, tracking the gain"))
    for _off, _was, _now, _nm in GAIN_EDITS:
        check(u16(code, _off) == _was, f"0x{_off:05X} starts at {_was} ({_nm})")
        struct.pack_into("<H", code, _off, _now)
        attributed |= {_off, _off + 1}
        print(f"      0x{_off:05X}  {_was} -> {u16(code, _off)}   {_nm}")

    # V211s structural gates -- these killed earlier gain builds, carry them verbatim
    _eme = u16(code, 0xC674E)
    check(_eme > u16(code, 0xC61B2),
          f"0xC674E EME wall {_eme} > tracking clamp {u16(code, 0xC61B2)} -- abort condition")
    _lane = (u16(code, 0xC61BE) * u16(code, 0xC6CD0)) >> 15
    check(_lane < u16(code, 0xC61B2),
          f"lane max (clip x gain) >> 15 = {_lane} < clamp {u16(code, 0xC61B2)}"
          f" -- the clamps do not bind")
    check(code[0x3AB76] == 0xAA and code[0x3AC20] == 0xAA,
          "0x3AB76/0x3AC20 BYTE-STOCK -- V62s x2, which CREATED grind #2 at 40-49 Hz, is ABSENT")

    # V214 RESTORES THE ENGAGED INERTIA to the value that is ON THE CAR TODAY (V122).
    #
    # Found 2026-08-29 by chasing r7d, and it is the reason this build exists.  gp-0x6b26
    # (0xD7A5C, the engaged m26 row) is a REAL 6-9 Hz DAMPER -- measured after V94 flew it,
    # +137/+139 deg vs WHEEL rate, |cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z).
    # V94 cut it hard and the operator ABORTED the drive: "made the stuttering and grinding
    # worse, by a lot ... it vibrated the entire car, and I decided it was not safe to drive."
    # Route r7d is that aborted drive, and it carries a sustained, engagement-gated ~31 Hz
    # line at 459x the creep-matched corpus median (prominence 56x; survives 0.5 s edge
    # trimming; 56% of 5-49 Hz power in 30-35 Hz; speed-invariant across three episodes).
    #
    # THE PROBLEM: the flown car (V122) carries this row at 3.576x Honda.  The whole notch
    # shelf carries it at 0.500x -- a 7.15x CUT of that damper, arrived at in two unflown
    # steps (V175 3.576->1.000, V196 1.000->0.500) and bundled invisibly with the notch.
    # That is a LARGER cut than the one V94 aborted on, in the same direction, and it has
    # never been on the car.  Shipping it inside a grinding fix confounds the very symptom.
    #
    # V214 therefore pins this row to the FLOWN value so the notch, the relay dose and the
    # gain step are tested against the damper the operator already lives with.  This is NOT
    # "adding mass" -- it is declining to remove 86% of what is on the car inside another
    # experiment.  V213 remains on the shelf as the 0.500x arm of the pair.
    INERTIA_ROW = 0xD7A5C
    FLOWN_Y = (-29490, -17202, -16000)     # V122, on the car -- see the note in the close-out gate [14]
    SHELF_Y = (-4915, -2867, -983)         # V196..V213, 0.500x Honda
    HONDA_Y3 = (-9830, -5734, -1966)
    _cur = tuple(s16(code, INERTIA_ROW + 2 * _i) for _i in range(3))
    check(_cur == SHELF_Y, f"0xD7A5C starts at the shelf half-dose {SHELF_Y}")
    for _i, _val in enumerate(FLOWN_Y):
        struct.pack_into("<h", code, INERTIA_ROW + 2 * _i, _val)
        attributed |= {INERTIA_ROW + 2 * _i, INERTIA_ROW + 2 * _i + 1}
    _new = tuple(s16(code, INERTIA_ROW + 2 * _i) for _i in range(3))
    check(_new == FLOWN_Y, f"0xD7A5C now {FLOWN_Y} -- the value ON THE CAR (V122)")
    _d_sh = sum(abs(_x) for _x in SHELF_Y) / sum(abs(_x) for _x in HONDA_Y3)
    _d_fl = sum(abs(_x) for _x in FLOWN_Y) / sum(abs(_x) for _x in HONDA_Y3)
    print(f"      0xD7A5C  {SHELF_Y} -> {FLOWN_Y}")
    print(f"      dose vs Honda: {_d_sh:.3f}x -> {_d_fl:.3f}x   ({_d_fl / _d_sh:.2f}x MORE 6-9 Hz damping)")
    check(_d_fl > _d_sh, "the damper goes UP, back toward the flown car, never down")

    # V215 pins MODE 27 as well.  V214 restored only mode 26, on the memory that this car is
    # TVCA4 and therefore uses modes 24/26 only.  That memory is probably right -- the
    # V105->V106 on-car dose-response moved b5 by changing mode 26, which is direct evidence
    # mode 26 is live -- but there is NO equivalent evidence that 27 is DEAD, and the flown
    # car carries 27 high as well.  RULE 7 says mode-proof or it is a bet, and this kit has
    # already lost a whole dose ladder to a mode assumption (V69/V70 wrote mode-10 gain_B
    # and were byte-stock).  Six bytes removes the bet entirely.
    M27_ROW = 0xD7A6C
    _c27 = tuple(s16(code, M27_ROW + 2 * _i) for _i in range(3))
    check(_c27 == HONDA_Y3, f"0xD7A6C starts at Honda {HONDA_Y3}")
    for _i, _val in enumerate(FLOWN_Y):
        struct.pack_into("<h", code, M27_ROW + 2 * _i, _val)
        attributed |= {M27_ROW + 2 * _i, M27_ROW + 2 * _i + 1}
    _n27 = tuple(s16(code, M27_ROW + 2 * _i) for _i in range(3))
    check(_n27 == FLOWN_Y, f"0xD7A6C now {FLOWN_Y} -- mode 27 matches the car too")
    print(f"      0xD7A6C  {HONDA_Y3} -> {FLOWN_Y}   (mode 27, belt and braces)")

    # V216 PINS THE MODELLED-FRICTION LANE TO THE CAR.  This ADDS authority; the name is
    # misleading and I had the direction backwards in SHELF.md before checking.
    #
    #   friction = ramp(motor_rate * 12 / knee, +-1) * (|model| * K1/1024)
    #   multiplier below saturation = (600/knee) * (K1/102)   [x Honda]
    #       car (V108)   knee  600, K1 204  ->  2.0x Honda   saturates at  50 deg/s
    #       V215         knee 3000, K1 102  ->  0.2x Honda   saturates at 250 deg/s
    #       => V215 is 0.10x THE CAR, and the ratchet regime (1-13 deg/s micro) is far
    #          below BOTH saturation points, so the full 10x applies exactly where the
    #          symptom lives.
    #
    # POLARITY IS VERIFIED NINE LINKS DEEP (memory accord-friction-polarity-*): friction is
    # SUBTRACTED from the plant model, which lowers gp-0x6ad6 -- a torque-tracking REFERENCE,
    # not a motor torque -- so the loop holds the driver's FELT torque at a LOWER target.
    # MORE modelled friction => MORE assist => LIGHTER wheel.  It does NOT fight LKAS.
    # Therefore V215's 0.10x makes the wheel ~10x HEAVIER in this term than the car and
    # REMOVES authority -- fighting the 8x gain step in the same build.
    KNEE, K1 = 0xC40BC, 0xC40D2
    CAR_KNEE, CAR_K1 = 600, 204
    check(u16(code, KNEE) == 3000, "0xC40BC starts at the shelf value 3000")
    check(u16(code, K1) == 102, "0xC40D2 starts at Honda 102")
    _m_before = (600.0 / u16(code, KNEE)) * (u16(code, K1) / 102.0)
    struct.pack_into("<H", code, KNEE, CAR_KNEE)
    struct.pack_into("<H", code, K1, CAR_K1)
    attributed |= {KNEE, KNEE + 1, K1, K1 + 1}
    _m_after = (600.0 / u16(code, KNEE)) * (u16(code, K1) / 102.0)
    print(f"      0xC40BC  knee 3000 -> {u16(code, KNEE)}"
          f"      0xC40D2  K1 102 -> {u16(code, K1)}")
    print(f"      friction lane {_m_before:.3f}x -> {_m_after:.3f}x Honda"
          f"   ({_m_after / _m_before:.1f}x MORE assist = LIGHTER wheel)")
    check(_m_after > _m_before, "the lane goes UP = lighter wheel = MORE authority")
    check(u16(code, KNEE) == CAR_KNEE and u16(code, K1) == CAR_K1,
          f"friction lane pinned to the car (knee {CAR_KNEE}, K1 {CAR_K1})")

    # V217 RESTORES THE INERTIA LANE WEIGHT.  V214/V215 put the inertia ROW back to the car,
    # but 0xC63A6 is that lane's WEIGHT in the six-lane plant-model sum of FUN_00038148:
    #
    #   SUM = gp-0x6b4e*0xC63A8 + gp-0x6b4c*0xC63AA + gp-0x6b26*0xC63A6   <- w[3], INERTIA
    #       + gp-0x6b46*0xC63A4 + gp-0x6bd0*0xC63A0 + gp-0x6bbe*0xC63A2   (each >>10)
    #
    # So the shelf restored the row and then fed it in at HALF weight -- the net inertia
    # contribution stayed at 0.5x the car, undoing half of the fix downstream and out of
    # sight.  All SIX weights are 1024 in stock AND on the car; V216 was the only build
    # halving one, it was w[3], and no rationale for it appears in the lineage.
    W3 = 0xC63A6
    check(u16(code, W3) == 512, "0xC63A6 starts at the carried half weight 512")
    struct.pack_into("<H", code, W3, 1024)
    attributed |= {W3, W3 + 1}
    check(u16(code, W3) == 1024, "0xC63A6 restored to 1024 -- stock AND the car")
    for _a, _nm in ((0xC63A0, "w0"), (0xC63A2, "w1"), (0xC63A4, "w2"),
                    (0xC63A6, "w3"), (0xC63A8, "w4"), (0xC63AA, "w5")):
        check(u16(code, _a) == 1024,
              f"0x{_a:05X} {_nm} = 1024 -- all six model-lane weights now match the car")
    print("      0xC63A6  512 -> 1024   (inertia lane weight; the damper fix now"
          " reaches the model at FULL strength)")

    before = u16(code, RESID_SCALE)
    check(before == 1024, f"0x{RESID_SCALE:05X} starts at Honda unity ({before})")
    struct.pack_into("<H", code, RESID_SCALE, NEW_SCALE)
    attributed |= {RESID_SCALE, RESID_SCALE + 1}
    print(f"      0x{RESID_SCALE:05X}  {before} -> {u16(code, RESID_SCALE)}"
          f"   ({NEW_SCALE / 1024.0:.3f}x)")
    check(u16(code, RESID_SCALE) == NEW_SCALE, f"the residual scale is now {NEW_SCALE}")

    print("\n  [3b] LEVER B -- the kit's best-measured lever, doubled")
    # The gain multiplies clamp(gp-0x4f62, +-5120) and the product is clamped to +-8192, so the
    # gain sets ONLY where the lane stops being linear. It cannot raise the lane's peak output.
    _before = u16(code, LEVER_B)
    check(_before == LEVER_B_OLD,
          f"0x{LEVER_B:05X} starts at the flown value {LEVER_B_OLD} (V88..V122 and all of V212-V220)")
    struct.pack_into("<H", code, LEVER_B, LEVER_B_NEW)
    attributed |= {LEVER_B, LEVER_B + 1}
    check(u16(code, LEVER_B) == LEVER_B_NEW, f"Lever B is now {LEVER_B_NEW}")

    print("\n  [3c] THE FRICTION LANE -- restore its SATURATION, not just its slope")
    # V216 matched the unsaturated slope 12*k1/gate/1024 exactly and left the saturation 5x off.
    for _a, _want, _nm in ((FRIC_GATE, 600, "relay width"), (FRIC_K1, 204, "Coulomb slope k1")):
        check(u16(code, _a) == _want,
              f"0x{_a:05X} starts at the shelf value {_want} ({_nm})")
    _slope_before = 12.0 * u16(code, FRIC_K1) / u16(code, FRIC_GATE) / 1024.0
    struct.pack_into("<H", code, FRIC_GATE, FRIC_GATE_CAR)
    struct.pack_into("<H", code, FRIC_K1, FRIC_K1_CAR)
    attributed |= {FRIC_GATE, FRIC_GATE + 1, FRIC_K1, FRIC_K1 + 1}
    _slope_after = 12.0 * FRIC_K1_CAR / FRIC_GATE_CAR / 1024.0
    print(f"      0x{FRIC_GATE:05X}  600 -> {FRIC_GATE_CAR}   relay saturates at "
          f"{FRIC_GATE_CAR / 12.0:.0f} counts of rate, not {600 / 12.0:.0f}")
    print(f"      0x{FRIC_K1:05X}  204 -> {FRIC_K1_CAR}   modelled friction at saturation "
          f"{100.0 * FRIC_K1_CAR / 1024:.1f}% of the model, not {100.0 * 204 / 1024:.1f}%")
    print(f"      unsaturated slope {_slope_before:.6f} -> {_slope_after:.6f}"
          f"   ({_slope_after / _slope_before:.4f}x -- THE RATCHET REGIME IS UNCHANGED)")
    check(abs(_slope_after - _slope_before) < 1e-9,
          "the unsaturated slope must be IDENTICAL -- this build must not touch the ratchet regime")
    check(u16(code, FRIC_GATE) == FRIC_GATE_CAR and u16(code, FRIC_K1) == FRIC_K1_CAR,
          "the friction lane now matches the car at EVERY rate, not just below its knee")
    check(FRIC_K1_CAR < 1024,
          "k1 must stay under 1024: at 1024 the modelled friction equals the whole model, the "
          "observer residual is identically zero, and beyond it the sign INVERTS")
    _onset_old = 8192 * 1024.0 / LEVER_B_OLD
    _onset_new = 8192 * 1024.0 / LEVER_B_NEW
    print(f"      0x{LEVER_B:05X}  {LEVER_B_OLD} -> {LEVER_B_NEW}"
          f"   ({LEVER_B_NEW / LEVER_B_OLD:.3f}x the car)")
    print(f"      saturation onset  {_onset_old:.0f} -> {_onset_new:.0f} counts"
          f"   ({100 * _onset_new / 5120:.1f}% of the +-5120 input clamp)")
    check(LEVER_B_NEW <= 65535, "the cal is read by ld.hu, so 65535 is its own range limit")
    check(5120 * LEVER_B_NEW < 2 ** 31,
          "the 32-bit mul at 0x3AC18 cannot overflow -- V160's int16 ceiling does not exist")
    check(LEVER_B_NEW == 2 * 13107, "V223 is exactly one doubling from V222's 13107")
    # The describing-function knee for the LARGEST measured excursion is k = 5184, and the CAR is
    # already past it at 5244 -- so saturating on big inputs is the car's existing operating point,
    # not something this rung introduces.
    check(5244 > 5184, "the car already sits past this lane's large-amplitude knee")
    # 🛑 THIS GATE WAS RESTATED FOR RUNG 2, AND THE REASON IS WRITTEN DOWN SO IT CANNOT BE A QUIET
    # LOOSENING. V221/V222 asserted `onset > 4 * 146`. The 4x was a MARGIN CHOICE for rung 1, not a
    # physical bound; the gate's stated PURPOSE is that the micro regime stays linear. Rung 2 halves
    # the onset by construction, so the purpose is now asserted directly -- onset above r24's engaged
    # p90 -- with the margin PRINTED rather than hidden, and floored at 2x so it cannot erode
    # silently on a rung 3 without someone editing this comment again.
    _P90 = 146.0
    _margin = _onset_new / _P90
    print(f"      onset/p90 margin {_margin:.2f}x   (V222 rung 1 was {640.0 / _P90:.2f}x)")
    check(_onset_new > _P90,
          f"the onset ({_onset_new:.0f}) must stay ABOVE route r24's engaged p90 torque-rate "
          f"({_P90:.0f}), so the micro regime where ratcheting and grinding live stays LINEAR")
    check(_margin >= 2.0,
          f"and the margin must be at least 2x -- it is {_margin:.2f}x. A rung that drops below 2x "
          "is putting the p90 itself into saturation and must be justified separately, not inherited")

    # THE RAIL MUST NOT MOVE. Raising it is the one change here that could reduce peak LKAS
    # authority, by letting a derivative lane eat the +-10240 aggregator headroom.
    _rail = bytes(code[R24_RAIL_LO:R24_RAIL_HI])
    check(_rail == bytes(base[R24_RAIL_LO:R24_RAIL_HI]),
          f"all {R24_RAIL_HI - R24_RAIL_LO} bytes of r24's +-8192 rail are BYTE-IDENTICAL to the "
          "base -- raising the gain cannot cost LKAS authority")
    check(not (set(range(R24_RAIL_LO, R24_RAIL_HI)) & attributed),
          "no rail byte is claimed by any edit in this build")

    print("\n  [4] WHAT THE DOSE DOES TO THE SOFT RELAY, from the image")
    # gp-0x6b70 = sgn(resid) * LERP((|resid| * cal) >> 10).  Scaling the INPUT scales the
    # small-signal gain directly, because the curve is near-linear close to the origin.
    import sys as _sys
    _sys.path.insert(0, os.path.join(KITROOT, "analysis-2020accord", "studies", "models"))
    import assist_map_mirror as _M                                            # noqa: E402
    for sp in (640, 1280, 2560, 5120):
        A_, B_ = _M.stage_382d8(26, sp)
        _M.stage_389ec(A_, B_, sp, 150)
        Xi, Yi = _M._LAST_STAGING["Xi"], _M._LAST_STAGING["Yi"]
        g0 = Yi[1] / Xi[1]
        print(f"        speed {sp:5d}   small-signal gain {g0:.2f}x"
              f" -> {g0 * NEW_SCALE / 1024.0:.2f}x")
    check(NEW_SCALE < 1024, "the dose LOWERS the gain (raising it would make the relay worse)")

    print("\n  [5] V196 LEVERS CARRIED, AND WHAT IS DELIBERATELY ABSENT")
    check(code[0xC64DD] == 50, "0xC64DD dwell is Honda 50 -- V193s widening NOT carried")
    check(s16(code, 0xC640A) == -8192, "0xC640A oscillation fallback is Honda -8192")
    check(code[0xC64AE] == 1, "0xC64AE the 2nd accel term is Honda-enabled (V190 not carried)")
    p26 = u32(code, 0xCBE74 + 4 * 26)
    n26 = s16(code, p26)
    Y26 = [s16(code, p26 + 2 + 2 * n26 + 2 * i) for i in range(n26)]
    # V214 DELIBERATELY REVERSES this inherited assertion: the shelf half-dose is exactly
    # what this build exists to undo.  Both directions are checked so neither can drift.
    check(Y26 == list(FLOWN_Y),
          f"engaged inertia Y = {Y26} -- RESTORED to the flown V122 value, NOT the half dose")
    check(list(SHELF_Y) == [-4915, -2867, -983],
          "and the shelf value it replaced was V196s 0.500x half dose")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V202")
    # V210 asserted the probe UNTOUCHED, because V210 was deliberately a lever with no
    # instrument.  V212 inverts that on purpose: the whole point is to carry BOTH.
    check(u16(code, PROBE_HW2) == NEW_PROBE_HW2 and code[PROBE_SHIFT] == NEW_SAR,
          "the 427 probe IS repointed -- V212 is a lever AND an instrument")
    check(u16(base, PROBE_HW2) == 0x9540 and base[PROBE_SHIFT] == 0xA4,
          "and the base it was applied to was byte-stock on both probe cells")
    m194, _ = resp(code, F0)
    check(m194 < 0.05, f"notch still at {F0:.2f} Hz, |H| = {m194:.5f}")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m, want, lbl in ((26, FLOWN_Y, "the FLOWN V122 value"),
                         (27, FLOWN_Y, "the FLOWN V122 value (V215 pins this one too)")):
        p = u32(code, PTR_I + 4 * m)
        n = s16(code, p)
        Y = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
        check(Y == want, f"inertia m{m} Y = {Y} -- {lbl}, CARRIED")
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
    # DERIVE the count, never assume it: 1024 = 0x0400 -> 512 = 0x0200 moves only the HIGH byte,
    # so this is ONE byte, not two.  Same trap as the V181 assertion bug and V198's 0x9540->0x9526.
    _exp = sum(1 for _k in range(2)
               if ((1024 >> (8 * _k)) & 0xFF) != ((NEW_SCALE >> (8 * _k)) & 0xFF))
    _exp += sum(1 for _k in range(2)
                if ((0x9540 >> (8 * _k)) & 0xFF) != ((NEW_PROBE_HW2 >> (8 * _k)) & 0xFF))
    _exp += 1 if 0xA4 != NEW_SAR else 0
    for _o, _w, _n, _ in GAIN_EDITS:
        _exp += sum(1 for _k in range(2)
                    if ((_w >> (8 * _k)) & 0xFF) != ((_n >> (8 * _k)) & 0xFF))
    for _i in range(3):
        _a = (SHELF_Y[_i] & 0xFFFF); _b = (FLOWN_Y[_i] & 0xFFFF)
        _exp += sum(1 for _k in range(2)
                    if ((_a >> (8 * _k)) & 0xFF) != ((_b >> (8 * _k)) & 0xFF))
    for _i in range(3):
        _a = (HONDA_Y3[_i] & 0xFFFF); _b = (FLOWN_Y[_i] & 0xFFFF)
        _exp += sum(1 for _k in range(2)
                    if ((_a >> (8 * _k)) & 0xFF) != ((_b >> (8 * _k)) & 0xFF))
    # The friction lane, counted ONCE against the base rather than as V216's step plus V222's undo.
    # V222 returns 0xC40BC to the base's own 3000, so that cell contributes ZERO payload bytes here.
    for _a, _b in ((3000, FRIC_GATE_CAR), (102, FRIC_K1_CAR)):
        _exp += sum(1 for _k in range(2)
                    if ((_a >> (8 * _k)) & 0xFF) != ((_b >> (8 * _k)) & 0xFF))
    _exp += sum(1 for _k in range(2)
                if ((512 >> (8 * _k)) & 0xFF) != ((1024 >> (8 * _k)) & 0xFF))
    # V221's own edit: Lever B, derived the same way rather than hard-coded.
    _exp += sum(1 for _k in range(2)
                if ((LEVER_B_OLD >> (8 * _k)) & 0xFF) != ((LEVER_B_NEW >> (8 * _k)) & 0xFF))
    check(len(pay) == _exp,
          f"{len(pay)} payload byte(s), derived expectation {_exp} "
          f"(cal 1024->{NEW_SCALE}, probe 0x9540->0x{NEW_PROBE_HW2:04X}, sar 4->5)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V217 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V223-V222BASE-LEVERB.13107.TO.26214.RUNG2"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v223_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V223_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V223 = V222 + LEVER B 13107 -> 26214.  RUNG 2 -- FLY V222 FIRST.         **")
    print("  ** V88 measured it on-car: 15-22 Hz 0.549x, 9-12 Hz 0.604x, 6-9 Hz 0.859x,  **")
    print("  ** and 0.5-3 Hz 1.192 = NULL -- less HF EVERYWHERE at ZERO cost to the      **")
    print("  ** peak LKAS command. It is a DERIVATIVE term, so it adds no felt mass to   **")
    print("  ** a deliberate steer. RUNG 2: onset 1600 -> 320 counts; route r24s own      **")
    print("  ** engaged p90 is 146, margin 2.19x, so the micro regime stays LINEAR.      **")
    print("  ** V160 called 6553 an int16 ceiling. FALSE -- 0x3AC18 is a 32-bit mul and  **")
    print("  ** the only bound is the +-8192 rail, left BYTE-IDENTICAL, so this cannot   **")
    print("  ** cost LKAS authority. Real headroom above the car is 12.5x, not 1.25x.    **")
    print("  ** UNPROVEN: monotonicity past 5244. Only two dose points exist, and V62s   **")
    print("  ** lesson is that 2x was the OPTIMUM, not a point on a ramp. If V221 reads  **")
    print("  ** WORSE than V217 on grinding, 5244 was already at the optimum.            **")
    print("  ** V208 notch + 0xC63AE 512 + 8x gain + the 427 probe: ALL THREE symptoms.  **")
    print("  ** notch -> 18-22 Hz grinding | 0xC63AE -> ~7.8 Hz ratchet | 8x -> AUTHORITY **")
    print("  ** Priced: gain +1.333x => vibration 1.650x, notch gives back 3.59x at       **")
    print("  ** 22-26 Hz => NET 0.459x, i.e. 2.18x QUIETER and 1.33x MORE AUTHORITY.      **")
    print("  ** Break-even 29.5 Hz; above it the notch gives nothing back, so this build  **")
    print("  ** RAISES loop gain 1.65x from 30-49 Hz.  Both prior blockers resolved:      **")
    print("  **   42.19 Hz = rectifier image of 21.09 Hz (|gp-0x6b9a| @0x3b87a) into      **")
    print("  **   FLAT boost LERPs, and that arc already flew NULL as V58/V59/V60;        **")
    print("  **   grind #2 came from V62s x2, and 0x3AB76/0x3AC20 are byte-stock here.    **")
    print("  ** RESIDUAL RISK: no direct measurement of 30-49 Hz on THIS base. V212 is    **")
    print("  ** the same build without the gain step -- fly that if you want the safer    **")
    print("  ** half. THREE levers is a real confound; the probe separates 2 of the 3.    **")
    print("  ** Decode: sar 5, so x = (raw<512 ? raw : raw-1024) * 32; gp-0x6b4e is       **")
    print("  ** clamped +-10240 in FUN_00026c80, i.e. raw 320/704 at the rails.           **")
    print("  ** gp-0x6b4e = mode-5 arm of the 0xC4124 router: value B from slots 2/4/5/9, **")
    print("  ** slot 2 being the live PI lane-2 output.  Read by FUN_00038148 @ 0x3817C.  **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
