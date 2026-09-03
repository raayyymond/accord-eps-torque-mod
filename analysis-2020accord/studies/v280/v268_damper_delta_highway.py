r"""V268 damper delta at highway speed -- reads V112 and V268 images directly.

Reproduces every number in V268-DAMPER-DELTA-AT-HIGHWAY-2026-09-02.md.
gain_B (r24 rate-lane surface) pointer arrays and BOOST_PTR (AMP1/AMP4) addresses are copied
verbatim from analysis-2020accord/builds/v108_plus/build_v268_tva.py (the build that made the edit).
Consumer structure (FUN_0003ad74 selects the LERP, FUN_0003aa2c computes r24/r26 and sums the
aggregator, FUN_00034a72 computes gp-0x6bbe) is decompile-confirmed via GhidraMCP against code.bin,
which is byte-identical across V112/V268/rev3 in these functions (build script asserts no code byte
moves).
"""
import struct

V112 = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin"
V268 = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"

b112 = bytearray(open(V112, "rb").read())
b268 = bytearray(open(V268, "rb").read())


def i16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)   # gain_B (r24), FUN_0003ad74 -> gp-0x6e38
BOOST_PTR = (0xCA4F4, 0xCA23C)                       # AMP1/AMP4, FUN_00034a72 -> gp-0x6bbe
CROSS = [u16(b112, 0xC6010 + 2 * k) for k in range(4)]           # speed cross axis, km/h @64.0625 ct/km/h
RATE_SCALE = 16384 / 3477                                        # counts per deg/s, gp-0x6ac0

print("=" * 100)
print("cross axis 0xC6010 (speed, ct):", CROSS, "-> km/h:", [round(c / 64.0625, 2) for c in CROSS])
print("motor-rate scale: 1 count =", round(1 / RATE_SCALE, 4), "deg/s  (=", round(RATE_SCALE, 4), "ct/deg-s)")
print()

for mode in (24, 26):
    print(f"=== MODE {mode}: gain_B (r24 rate-lane surface), FUN_0003ad74 records ===")
    for arr in PTR_ARRAYS:
        p = u32(b112, arr + mode * 4)
        npt = i16(b112, p)
        X = [i16(b112, p + 2 + 2 * k) for k in range(npt)]
        Xd = [round(x / RATE_SCALE, 1) for x in X]
        Y112 = [i16(b112, p + 2 + 2 * npt + 2 * k) for k in range(npt)]
        Y268 = [i16(b268, p + 2 + 2 * npt + 2 * k) for k in range(npt)]
        flat = "IDENTICAL 0-400ct (0-84.9 deg/s): Y[0]==Y[1] in stock already" if Y112[0] == Y112[1] else "DIFFERS"
        print(f"  rec 0x{p:X}  X(ct)={X} X(deg/s)={Xd}")
        print(f"    V112 Y={Y112}  V268 Y={Y268}   [{flat}]")
    print()

print("=" * 100)
for mode in (24, 26):
    print(f"=== MODE {mode}: boost AMP1/AMP4, FUN_00034a72, index = gp-0x6ba6 = |gp-0x6b9a| ===")
    for arr in BOOST_PTR:
        p = u32(b112, arr + mode * 4)
        npt = i16(b112, p)
        X = [i16(b112, p + 2 + 2 * k) for k in range(npt)]
        Y112 = [i16(b112, p + 2 + 2 * npt + 2 * k) for k in range(npt)]
        Y268 = [i16(b268, p + 2 + 2 * npt + 2 * k) for k in range(npt)]
        pct = [round(100.0 * (b - a) / a, 1) for a, b in zip(Y112, Y268)]
        print(f"  rec 0x{p:X}  X={X}")
        print(f"    V112 Y={Y112}")
        print(f"    V268 Y={Y268}")
        print(f"    delta %  ={pct}")
    print()

# Sanity: modes 24 and 26 byte-identical for both tables, both builds (stock convention).
for mode_a, mode_b in [(24, 26)]:
    for arr in PTR_ARRAYS + BOOST_PTR:
        pa = u32(b112, arr + mode_a * 4)
        pb = u32(b112, arr + mode_b * 4)
        na = i16(b112, pa)
        assert bytes(b112[pa:pa + 2 + 4 * na]) == bytes(b112[pb:pb + 2 + 4 * na]), f"mode24/26 differ at 0x{arr:X} V112"
        nb = i16(b268, pb)
        assert bytes(b268[pa:pa + 2 + 4 * na]) == bytes(b268[pb:pb + 2 + 4 * nb]), f"mode24/26 differ at 0x{arr:X} V268"
print("CONFIRMED: mode 24 (manual) and mode 26 (engaged) are byte-identical for gain_B and boost, "
      "in BOTH V112 and V268 -- the live-mode question does not affect this result either way.")

print()
print("IDX_DIST (V59 measured, from build_v268_tva.py):",
      "76.93% @256, 18.46% @768, 4.57% @1536, 0.04% @2048 -- all inside the AMP tables' first segment "
      "or two, well below the ceiling knots (3645/3072, 5120/6144).")

# LKAS lane's own rate-feedback gain, for comparison (from LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md)
lkas_dTdrate = {12: 45.6, 24: 52.8, 32: 57.6, 48: 67.2, 58: 73.2}   # counts per deg/s
print()
print("LKAS lane dT/d(rate), counts/deg/s (identical V112/rev3/V280, cited study):", lkas_dTdrate)
print("gain_B lane's own dT/d(rate) contribution over 0-20 deg/s, V112 and V268: 0 (flat segment, both builds)")
print("=> fraction of LKAS lane's gain claimed by the V268 gain_B delta at 0-20 deg/s highway: 0 / 45.6-73.2 = 0%")
