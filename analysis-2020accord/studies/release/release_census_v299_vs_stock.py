# -*- coding: utf-8 -*-
"""Release census: attribute EVERY byte V299 differs from STOCK to a named row (A/B/C/D/E class). Runs in < 2 s.
Reads the two images only; no build script constant is consulted for a value."""
import glob, hashlib, json, os, struct, sys
R = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
S = open(R + "stock_fw_dump/code.bin", "rb").read()
VP = glob.glob(R + "_v299_*plain_image.bin")[0]
V = open(VP, "rb").read()
assert hashlib.sha256(S).hexdigest().startswith("3f1d55a9") and hashlib.sha256(V).hexdigest().startswith("30ff05fa")
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]
diff = {a for a in range(0x13000, 0x100000) if S[a] != V[a]}
assert len(diff) == 2471, len(diff)

def ptrs(tab, n):
    return [u32(S, tab + 4 * k) for k in range(n)]
rec = lambda p, L: set(range(p, p + L))
rows = []  # (id, cls, name, addrset)
def add(i, c, n, s): rows.append((i, c, n, set(s)))
# ---- A. angle-loop structure
add("A1", "A", "F181 id string '39990-TVA,A16B' (0x13109 ',' + 0x1310D 'B')", {0x13109, 0x1310D})
add("A2", "A", "in-place lane edits E1 0x28F4E, B2 0x29A50, A2 0x29A56, E4 0x29D6A, HOOK 0x29D76, OPH 0x29EE0", set(range(0x28F4E, 0x28F50)) | set(range(0x29A50, 0x29A54)) | {0x29A56} | set(range(0x29D6A, 0x29D6E)) | set(range(0x29D76, 0x29D7A)) | set(range(0x29EE0, 0x29EE4)))
add("A3", "A", "the angle-loop cave 0xC4C00..0xC4D03 (260 B incl. G(v) table, A3 bound, freeze, caps, op-skip, camera gate)", range(0xC4C00, 0xC4D04))
add("A4", "A", "fb-lag re-purposed as r26 = 16*theta: a 0xC63E8 = 0, b 0xC63EA = 8192, C 0xC62E6 = 65535, DB 0xC62E4 = 0", {0xC63E8, 0xC63E9, 0xC63EA, 0xC63EB, 0xC62E6, 0xC62E7, 0xC62E4, 0xC62E5})
add("A5", "A", "dir-2 hand-fade record 0xE54FC X/Y := dir-0 record (camera-arm cost neutralised)", range(0xE54FC, 0xE54FC + 26))
add("A6", "A", "authority chain: 0x2A1F0 repoint -> private forward gain 0xC6CD0 = 5346 (x6); clamps 0xC61B2/B4 = 3072", {0x2A1F0, 0x2A1F1, 0xC6CD0, 0xC6CD1, 0xC61B2, 0xC61B3, 0xC61B4, 0xC61B5})
add("A7", "A", "EME soft-limit quad/ramp int16 (0xC674E.., 0xC6768..) + f32 mirrors (0xC6598..) = the x5 interlock ladder", {0xC674E, 0xC674F, 0xC6750, 0xC6751, 0xC675A, 0xC675B, 0xC675C, 0xC675D, 0xC6768, 0xC6769, 0xC676A, 0xC676B, 0xC676C, 0xC676D} | set(range(0xC6598, 0xC659C)) | set(range(0xC659C, 0xC65A0)) | set(range(0xC65AC, 0xC65B0)) | set(range(0xC65B0, 0xC65B4)) | set(range(0xC65C4, 0xC65C8)) | set(range(0xC65C8, 0xC65CC)) | set(range(0xC65CC, 0xC65D0)))
# ---- B. tuning
add("B1", "B", "Ki 0xC63E6 = 40", {0xC63E6, 0xC63E7})
add("B2", "B", "I clamp ICL 0xC61BA = 8192", {0xC61BA, 0xC61BB})
KP = ptrs(0xCB994, 28); KD = ptrs(0xCB7D4, 28)
add("B3", "B", "Kp bank 0xCB994: slot-7 record 0xE5378 Y = 112 x5", rec(KP[7] + 12, 10))
add("B4", "B", "Kd bank 0xCB7D4: slot-7 record 0xE511C Y = 48 x4", rec(KD[7] + 10, 8))
add("B3x", "B", "Kp bank: the OTHER 27 records Y = 960 flat (V294 torque-mode leftover; stock 205..717 schedules)", set().union(*[rec(p + 12, 10) for i, p in enumerate(KP) if i != 7]))
add("B4x", "B", "Kd bank: the OTHER 27 records Y = 0 (V293 leftover; stock 128/64)", set().union(*[rec(p + 10, 8) for i, p in enumerate(KD) if i != 7]))
# ---- C. telemetry
add("C1", "C", "0x14A cave hook 0x55C0E (jarl 0xC4B34)", range(0x55C0E, 0x55C12))
add("C2", "C", "0x14A telemetry cave body 0xC4B34..0xC4BD7 (164 B)", range(0xC4B34, 0xC4BD8))
add("C3", "C", "CAN-427 MOTOR_TORQUE tap window 0x55DF2..0x55E11 (source repoint + packer shift)", range(0x55DF2, 0x55E12))
# ---- D. legacy
add("D1", "D", "0x454FE gp-0x67fa substitution byte (V42) -- measured INERT", {0x454FE})
add("D2", "D", "biquad arm 0x35A08/0x35A12/0x35A18 + enable cal 0xC649B (Honda's dormant 55 Hz notch, engaged-only)", {0x35A08, 0x35A09, 0x35A12, 0x35A18, 0xC649B})
add("D3", "D", "r24 rate-lane gate byte 0x3AA96 (-> STEER_CONTROL_ACTIVE) + engaged arm 0xC6446 = 2048", {0x3AA96, 0xC6446, 0xC6447})
add("D4", "D", "low-speed steer lockout 0xC62EA = 0 (stock 320 = 5 km/h)", {0xC62EA, 0xC62EB})
add("D5", "D", "base-assist Coulomb relay 0xC40BC knee 1800 / 0xC40D2 K1 612 / 0xC40DC alpha2 14 (V112, carried by rebase)", {0xC40BC, 0xC40BD, 0xC40D2, 0xC40D3, 0xC40DC})
add("D6", "D", "STEER_STATUS debounce cals 0xC61C0..C5 = 0xFFFF x3, 0xC64B4..B7 = 0xFF x4, DTC-0x49 gate 0xC64B8 = 255 (V36/V37)", set(range(0xC61C0, 0xC61C6)) | set(range(0xC64B4, 0xC64B9)))
add("D7", "D", "square-wave hold count 0xC64DE 17 -> 27 (V18)", {0xC64DE})
add("D8", "D", "base-assist damper rate/boost banks 0xCE000..0xD9FFF (all mode slots; V268 flatten) incl. gp-0x6b26 friction-comp Y 0xD7A5C/6C", {a for a in diff if 0xCE000 <= a < 0xDA000 and (a & 0xFFF) < 0xFFC})
MAP = ptrs(0xC9A88, 28); LIM = ptrs(0xCB844, 10)
add("D9", "D", "assist map 0xC9A88, all 28 records: Y -> linear x6 (0,52,86,103,138,275,413,550,688,1032)", set().union(*[rec(p + 22, 20) for p in MAP]))
add("D10", "D", "setpoint ceiling LIM 0xCB844 records Y 15360 -> 16384 (slots 0,1,3,4,6,7,8,9)", set().union(*[rec(p + 20, 20) for p in LIM]))
add("D11", "D", "dead second id-string copy 0x14120 '-' -> ','", {0x14120})
# ---- E. CRC trailers
add("E1", "E", "page-CRC trailers (offset 0xFFC of every touched 4 KB page)", {a for a in diff if (a & 0xFFF) >= 0xFFC})
# fix D8 to exclude trailers
rows = [(i, c, n, (s - {a for a in diff if (a & 0xFFF) >= 0xFFC}) if i == "D8" else s) for i, c, n, s in rows]
# ---- attribute
owner = {}
for i, c, n, s in rows:
    for a in s & diff:
        assert a not in owner, (hex(a), owner[a], i)
        owner[a] = i
orph = sorted(diff - set(owner))
print("orphans:", [hex(a) for a in orph])
assert not orph
out = []
for i, c, n, s in rows:
    k = len(s & diff)
    out.append({"id": i, "cls": c, "bytes": k, "name": n})
    print(f"{i:4s} {c} {k:5d}  {n}")
print("total", sum(o["bytes"] for o in out))
by = {}
for o in out: by[o["cls"]] = by.get(o["cls"], 0) + o["bytes"]
print(by)
os.makedirs("analysis-2020accord/_scratch/out", exist_ok=True)
json.dump({"v299": os.path.basename(VP), "rows": out, "by_class": by}, open("analysis-2020accord/_scratch/out/release_census_v299.json", "w"), indent=1)
