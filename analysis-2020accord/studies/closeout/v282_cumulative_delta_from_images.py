# -*- coding: utf-8 -*-
"""V282 CUMULATIVE NON-STOCK DELTA, read DIRECTLY FROM THE IMAGES.

stock = the true stock dump `stock_fw_dump/code.bin`; V282 = `_v282_..._plain_image.bin`.
Raw little-endian byte reads; NO build-script constants are consulted anywhere in this file.

Produces:
  1. sha256 of both images,
  2. the full byte diff over [0x13000, 0x100000) as runs,
  3. every scalar cell read from BOTH images,
  4. every LERP bank walked through its pointer table in BOTH images,
  5. an ATTRIBUTION CENSUS: every differing byte assigned to a named row; asserts zero orphans.

Run: python v282_cumulative_delta_from_images.py     (ACCORD_FIRMWARE_ROOT honoured)
Output: <kit>/_scratch/out/v282_cumulative_delta.json  + a human table on stdout.
"""
import os, json, hashlib, struct

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(KIT, "_scratch", "out", "v282_cumulative_delta.json")
IMG = {
    "stock": ROOT + "stock_fw_dump/code.bin",
    "V282":  ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
                    "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
B = {k: open(v, "rb").read() for k, v in IMG.items()}
H = {k: hashlib.sha256(v).hexdigest() for k, v in B.items()}
LO, HI = 0x13000, 0x100000

u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
u8 = lambda b, a: b[a]
f32 = lambda b, a: struct.unpack_from("<f", b, a)[0]
hx = lambda b, a, n: b[a:a + n].hex()

# ---------------------------------------------------------------- 1. raw diff
diff_idx = [a for a in range(LO, HI) if B["stock"][a] != B["V282"][a]]


def runs(idx, gap=2):
    out = []
    for a in idx:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = a + 1
        else:
            out.append([a, a + 1])
    return [(s, e) for s, e in out]


RUNS = runs(diff_idx)

# ---------------------------------------------------------------- 2. scalars
CELLS = [
    ("0x13109", u8,  "version-string byte (UDS read)"),
    ("0x14120", u8,  "version-string byte (UDS read)"),
    ("0x2A1F0", u16, "displacement of the forward-LKAS gain load"),
    ("0x3AA96", u8,  "r24/r26 rate-lane gate byte"),
    ("0x454FE", u8,  "gp-0x67fa selector substitution byte"),
    ("0xC40BC", u16, "Coulomb-relay knee"),
    ("0xC40D2", u16, "relay gain K1"),
    ("0xC40DC", u8,  "alpha2 (2nd HF filter coeff)"),
    ("0xC61B2", u16, "forward tracking clamp (+)"),
    ("0xC61B4", u16, "forward output clamp T"),
    ("0xC61B6", u16, "D-term clamp"),
    ("0xC61BC", u16, "P clamp"),
    ("0xC61BE", u16, "PID sum clamp S"),
    ("0xC61C0", u16, "STEER_STATUS debounce SM cal"),
    ("0xC61C2", u16, "STEER_STATUS debounce SM cal"),
    ("0xC61C4", u16, "STEER_STATUS debounce SM cal"),
    ("0xC62E6", s16, "LKAS PID feedback saturation clamp (stored x256)"),
    ("0xC62EA", u16, "low-speed steer lockout threshold"),
    ("0xC63E6", u16, "Ki (LKAS rate PID)"),
    ("0xC63E8", u16, "feedback lag pole a"),
    ("0xC63EA", u16, "feedback lag pole b"),
    ("0xC63EC", u16, "output lag pole a"),
    ("0xC63EE", u16, "output lag pole b"),
    ("0xC6446", u16, "r24 engaged rate-lane gain arm (Lever B)"),
    ("0xC646C", u16, "shared sensor scale"),
    ("0xC649B", u8,  "biquad enable cal"),
    ("0xC64B4", u16, "STEER_STATUS debounce SM cal"),
    ("0xC64B6", u16, "STEER_STATUS debounce SM cal"),
    ("0xC64B8", u8,  "DTC-0x49 fail-counter increment gate"),
    ("0xC64DE", u8,  "gp-0x6b2c square-wave hold count"),
    ("0xC6598", f32, "EME float mirror +A"),
    ("0xC659C", f32, "EME float mirror +B"),
    ("0xC65AC", f32, "EME float mirror -A"),
    ("0xC65B0", f32, "EME float mirror -B"),
    ("0xC65C4", f32, "EME ramp float knot 0"),
    ("0xC65C8", f32, "EME ramp float knot 1"),
    ("0xC65CC", f32, "EME ramp float knot 2"),
    ("0xC674E", s16, "EME soft-limit +A (int16)"),
    ("0xC6750", s16, "EME soft-limit +B"),
    ("0xC675A", s16, "EME soft-limit -A"),
    ("0xC675C", s16, "EME soft-limit -B"),
    ("0xC6768", u16, "EME ramp knot 0"),
    ("0xC676A", u16, "EME ramp knot 1"),
    ("0xC676C", u16, "EME ramp knot 2"),
    ("0xC6CD0", s16, "private forward LKAS gain (Q15)"),
]
scalars = []
for a, rd, what in CELLS:
    A = int(a, 16)
    sv, vv = rd(B["stock"], A), rd(B["V282"], A)
    scalars.append(dict(addr=a, what=what, stock=sv, V282=vv, changed=sv != vv))

# ---------------------------------------------------------------- 3. code windows
CODEW = [
    ("0x2A1F0", 2,  "forward-gain load displacement"),
    ("0x2A174", 4,  "V289 notch hook site (must be STOCK on V282)"),
    ("0x29D72", 4,  "V288 hook site (must be STOCK on V282)"),
    ("0x35A08", 2,  "biquad ARM flag source repoint"),
    ("0x35A12", 1,  "biquad arm comparison"),
    ("0x35A18", 1,  "biquad arm branch condition"),
    ("0x55C0E", 4,  "0x14A telemetry cave hook"),
    ("0x55DF2", 32, "CAN-427 MOTOR_TORQUE tap source window + packer sar"),
    ("0xC4B34", 8,  "0x14A telemetry cave, first 8 bytes"),
    ("0xC4BD6", 4,  "0x14A cave exit"),
    ("0xC4BDC", 8,  "V288/V289 telemetry tail (must be blank on V282)"),
    ("0xC4C00", 8,  "V288/V289 filter cave (must be blank on V282)"),
    ("0xC4FFC", 4,  "page CRC 0xC4xxx"),
    ("0xC6FFC", 4,  "page CRC 0xC6xxx"),
]
code = [dict(addr=a, n=n, what=w,
             stock=hx(B["stock"], int(a, 16), n), V282=hx(B["V282"], int(a, 16), n))
        for a, n, w in CODEW]

# ---------------------------------------------------------------- 4. LERP banks
def walk(img, ptr_table, slot=7):
    """Honda LERP family: pointer table[slot] (u32) -> record; record = n (u16), X[n] (u16), Y[n] (s16).

    slot 7 is the LIVE variant selector (measured on the V276 wire, record 11 `TVCA4`)."""
    b = B[img]
    entry = struct.unpack_from("<I", b, ptr_table + 4 * slot)[0]
    n = u16(b, entry)
    X = [u16(b, entry + 2 + 2 * i) for i in range(n)]
    Y = [s16(b, entry + 2 + 2 * n + 2 * i) for i in range(n)]
    return dict(ptr_entry=hex(entry), n=n, X=X, Y=Y)


BANKS = {
    "assist_map_0xC9A88": 0xC9A88,
    "kp_0xCB994":         0xCB994,
    "kd_0xCB7D4":         0xCB7D4,
    "fadeA_0xCBA04":      0xCBA04,
    "fadeB_0xCBA74":      0xCBA74,
    "taper_opp_0xCB8B4":  0xCB8B4,
    "taper_same_0xCB924": 0xCB924,
}
banks = {k: {img: walk(img, p) for img in ("stock", "V282")} for k, p in BANKS.items()}

# ---------------------------------------------------------------- 5. attribution census
REGIONS = [
    ("R1  version-string marker",               [(0x13109, 0x1310A), (0x14120, 0x14121)]),
    ("R2  forward-gain load repoint",           [(0x2A1F0, 0x2A1F2)]),
    ("R3  biquad arm repoint (3 sites)",        [(0x35A08, 0x35A1A)]),
    ("R4  rate-lane gate byte",                 [(0x3AA96, 0x3AA97)]),
    ("R5  gp-0x67fa substitution byte",         [(0x454FE, 0x454FF)]),
    ("R6  0x14A cave hook",                     [(0x55C0E, 0x55C12)]),
    ("R8  CAN-427 torque tap window",           [(0x55DF2, 0x55E12)]),
    ("R18 Coulomb relay knee / K1 / alpha2",    [(0xC40BC, 0xC40DD)]),
    ("R7  0x14A telemetry cave body",           [(0xC4B34, 0xC4BD8)]),
    ("R28 page CRC trailers",                   [(0xC4FFC, 0xC5000), (0xC6FFC, 0xC7000)]
                                                + [(p + 0xFFC, p + 0x1000)
                                                   for p in range(0xCE000, 0xDA000, 0x1000)]
                                                + [(p + 0xFFC, p + 0x1000)
                                                   for p in range(0xE4000, 0xE9000, 0x1000)]),
    ("R10 forward clamps 0xC61B2/B4",           [(0xC61B2, 0xC61B6)]),
    ("R19 STEER_STATUS debounce 0xC61C0..C4",   [(0xC61C0, 0xC61C6)]),
    ("R11 feedback saturation clamp",           [(0xC62E6, 0xC62E8)]),
    ("R14 low-speed steer lockout",             [(0xC62EA, 0xC62EC)]),
    ("R12 r24 engaged rate-lane gain",          [(0xC6446, 0xC6448)]),
    ("R13 biquad enable cal",                   [(0xC649B, 0xC649C)]),
    ("R20 STEER_STATUS debounce 0xC64B4/B6",    [(0xC64B4, 0xC64B8)]),
    ("R21 DTC-0x49 gate",                       [(0xC64B8, 0xC64BA)]),
    ("R22 square-wave hold count",              [(0xC64DE, 0xC64E0)]),
    ("R17 EME float mirrors",                   [(0xC6598, 0xC65D0)]),
    ("R15 EME soft-limit quad",                 [(0xC674E, 0xC6752), (0xC675A, 0xC675E)]),
    ("R16 EME ramp triple",                     [(0xC6768, 0xC676E)]),
    ("R9  private forward LKAS gain",           [(0xC6CD0, 0xC6CD2)]),
    ("R23 rate-lane + boost bank flatten",      [(0xCE000, 0xDA000)]),
    ("R24/25/26 LERP data (map / Kp / ceiling)", [(0xE4000, 0xE9000)]),
]


def owner(a):
    for name, exts in REGIONS:
        for s, e in exts:
            if s <= a < e:
                return name
    return None


census, orphans = {}, []
for a in diff_idx:
    o = owner(a)
    if o is None:
        orphans.append(hex(a))
    else:
        census[o] = census.get(o, 0) + 1

res = dict(images=IMG, sha256=H, extent=[hex(LO), hex(HI)],
           diff_bytes=len(diff_idx), diff_runs=len(RUNS),
           runs=[[hex(s), hex(e), e - s] for s, e in RUNS],
           scalars=scalars, code=code, banks=banks, census=census, orphans=orphans)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w"), indent=1)

print("sha256 stock", H["stock"])
print("sha256 V282 ", H["V282"])
print("diff bytes %d over %d runs (gap<=2)" % (len(diff_idx), len(RUNS)))
print("\nATTRIBUTION CENSUS (differing bytes per named row):")
tot = 0
for k in sorted(census):
    print("  %-44s %5d" % (k, census[k]))
    tot += census[k]
print("  %-44s %5d" % ("TOTAL ATTRIBUTED", tot))
print("  ORPHANS:", orphans if orphans else "NONE")
assert not orphans, "unattributed differing bytes"
assert tot == len(diff_idx)
print("\nSCALARS THAT MOVED:")
for s in scalars:
    if s["changed"]:
        print("  %-9s %-52s %14s -> %s" % (s["addr"], s["what"], s["stock"], s["V282"]))
print("\nSCALARS VERIFIED UNCHANGED (stock == V282):")
print("  " + ", ".join(s["addr"] for s in scalars if not s["changed"]))
print("\nCODE WINDOWS:")
for c in code:
    print("  %-9s %-48s %s -> %s" % (c["addr"], c["what"], c["stock"], c["V282"]))
print("\nLERP BANKS (slot 7 = the live variant selector record):")
for k, v in banks.items():
    print("  %s  record %s  n=%d  MOVED=%s" %
          (k, v["V282"]["ptr_entry"], v["V282"]["n"], v["stock"] != v["V282"]))
    print("    X      %s" % (v["V282"]["X"],))
    print("    stockY %s" % (v["stock"]["Y"],))
    print("    V282 Y %s" % (v["V282"]["Y"],))
print("\nwrote", OUT)
