# -*- coding: utf-8 -*-
"""V293 close-out artifact -- every number READ FROM THE IMAGES ON DISK.

Independent reader (the kit's ledger_v38_to_v84_bytes.py hard-codes a V38..V84 build list and a
different cell set, so this rebuilds the matrix with the same conventions rather than editing it):
  * plain images are flat 1 MiB code images, file offset == firmware address
  * V850E2 is LITTLE-ENDIAN; `sar` is arithmetic, Python `>>` on int matches
  * LERP record layout: [npt:u16][X x npt][Y x npt]
  * ANCHORS asserted before any number is used: stock 0xC646C == 891, stock 0x454FE == 0xBA,
    V282 0x2A1F0 halfword == 0x7CD0, V282 0xC63E8 == 923.
"""
import json
import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
STOCK = ROOT / "stock_fw_dump" / "code.bin"
OUT = Path(__file__).resolve().parent / "v293_page_data.json"

u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def lerp(X, Y, x):
    """The firmware's integer LERP (0x29CFE map / 0x29DC6 Kp / 0x29E76 Kd). Truncating divide."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
    raise AssertionError


def fb_ss(a, b, x, C):
    """Exact integer steady state of the fb lag + two-sample sum + clamp, 0x28F86..0x28FBC."""
    s, seen, hist = 0, {}, []
    for _ in range(200000):
        if s in seen:
            cyc = hist[seen[s]:]
            return sum(cyc) // len(cyc)
        seen[s] = len(hist)
        s_new = (a * s >> 10) + (b * x >> 10)
        hist.append(max(-C, min(C, s + s_new)))
        s = s_new
    return hist[-1]


_OL = {}


def out_lag(la, lb, S):
    """Exact integer orbit of the output lag, 0x2A174..0x2A1AC, from cold state 0.
       s' = (la*s>>10) + (lb*S>>10) ;  y = (s + s') >> 5 ;  DC = 2*lb/((1024-la)*32)"""
    neg = S < 0
    S = abs(S)
    key = (la, lb, S)
    if key not in _OL:
        s, seen, hist = 0, {}, []
        for _ in range(500000):
            if s in seen:
                break
            seen[s] = len(hist)
            s2 = (la * s >> 10) + (lb * S >> 10)
            hist.append((s + s2) >> 5)
            s = s2
        _OL[key] = hist[-1]
    return -_OL[key] if neg else _OL[key]


# ---------------------------------------------------------------- the images
def find(patterns):
    hits = []
    for p in sorted(ROOT.glob("*_plain_image.bin")):
        nm = p.name
        for pat in patterns:
            if pat in nm:
                hits.append(p)
                break
    return hits


BASE = ROOT / ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X"
               ".FEEDBACK46080.TORQUE.TAP_plain_image.bin")

# the arc slice for the matrix: every _v2[7-9]* image on disk, plus stock and the anchors
ARC = []
for p in sorted(ROOT.glob("*_plain_image.bin")):
    nm = p.name
    i = nm.find("_v2")
    if i < 0:
        continue
    tail = nm[i + 2:]
    num = ""
    for ch in tail:
        if ch.isdigit():
            num += ch
        else:
            break
    if len(num) == 3 and 270 <= int(num) <= 292:
        ARC.append((int(num), nm, p))
ARC.sort()

V293 = [p for p in ROOT.glob("_v293_*_plain_image.bin")]
V279 = [p for p in ROOT.glob("*v279*_plain_image.bin")]

# ---------------------------------------------------------------- cells
MAP_PTR, KP_PTR, KD_PTR = 0xC9A88, 0xCB994, 0xCB7D4
TAPER_OVR_PTR, TAPER_D_PTR, TAPER_C_PTR = 0xCBA04, 0xCBBC4, 0xCBAE4
SLOT = 7
CELLS = [
    (0xC62E6, "fb saturation clamp"),
    (0xC61B6, "D clamp"),
    (0xC61BC, "P clamp"),
    (0xC61BE, "sum clamp"),
    (0xC61B4, "output clamp"),
    (0xC6446, "r24 engaged arm"),
    (0xC6CD0, "forward LKAS gain"),
    (0xC63E8, "fb lag a"),
    (0xC63EA, "fb lag b"),
    (0xC63EC, "out lag a"),
    (0xC63EE, "out lag b"),
    (0xC63E6, "Ki"),
    (0xC62E4, "I deadband"),
    (0xC61BA, "I clamp"),
    (0xC61F6, "r24 deadband"),
    (0xC674E, "EME soft limit"),
]


def read_build(buf):
    d = {}
    for a, lab in CELLS:
        d[f"0x{a:05X}"] = u16(buf, a)
    d["0x2A1F0"] = u16(buf, 0x2A1F0)
    mrec = u32(buf, MAP_PTR + SLOT * 4)
    krec = u32(buf, KP_PTR + SLOT * 4)
    drec = u32(buf, KD_PTR + SLOT * 4)
    d["map_rec"] = f"0x{mrec:05X}"
    d["map"] = rec(buf, mrec)[1:]
    d["kp_rec"] = f"0x{krec:05X}"
    d["kp"] = rec(buf, krec)[1:]
    d["kd_rec"] = f"0x{drec:05X}"
    d["kd"] = rec(buf, drec)[1:]
    # the full Kp bank, every distinct record -- how global is the flatten?
    banks = {}
    for s in range(28):
        r = u32(buf, KP_PTR + s * 4)
        banks.setdefault(f"0x{r:05X}", []).append(s)
    d["kp_bank"] = {k: [rec(buf, int(k, 16))[2], v] for k, v in sorted(banks.items())}
    dbanks = {}
    for s in range(28):
        r = u32(buf, KD_PTR + s * 4)
        dbanks.setdefault(f"0x{r:05X}", []).append(s)
    d["kd_bank"] = {k: [rec(buf, int(k, 16))[2], v] for k, v in sorted(dbanks.items())}
    orec = u32(buf, TAPER_OVR_PTR + SLOT * 4)
    d["taper_ovr_rec"] = f"0x{orec:05X}"
    d["taper_ovr"] = rec(buf, orec)[1:]
    trec = u32(buf, TAPER_D_PTR + SLOT * 4)
    d["taper_D"] = rec(buf, trec)[1:]
    crec = u32(buf, TAPER_C_PTR + SLOT * 4)
    d["taper_C"] = rec(buf, crec)[1:]
    return d


def surface(d, fb):
    """T(idx) at a fixed feedback operand, byte-exact through the fade and the output lag."""
    mX, mY = d["map"]
    kX, kY = d["kp"]
    PC, SC, OC = d["0xC61BC"], d["0xC61BE"], d["0xC61B4"]
    la, lb, G = d["0xC63EC"], d["0xC63EE"], d["0xC6CD0"]
    out = []
    for idx in range(0, 241):
        sp = lerp(mX, mY, idx)
        kp = lerp(kX, kY, idx)
        E = 32 * sp - fb
        P = max(-PC, min(PC, (E * kp) >> 8))
        S = max(-SC, min(SC, (254 * P) >> 8))      # D == 0 at steady state (dE = 0)
        y = out_lag(la, lb, S)
        T = max(-OC, min(OC, (y * G) >> 15))
        Tceil = max(-OC, min(OC, (max(-SC, min(SC, P)) * G) >> 15))
        out.append((idx, sp, kp, E, P, S, y, T, Tceil))
    return out


def main():
    st = STOCK.read_bytes()
    assert len(st) == 0x100000
    assert s16(st, 0xC646C) == 891, "ANCHOR stock 0xC646C"
    assert st[0x454FE] == 0xBA, "ANCHOR stock 0x454FE"
    v282 = BASE.read_bytes()
    assert u16(v282, 0x2A1F0) == 0x7CD0, "ANCHOR V282 0x2A1F0"
    assert u16(v282, 0xC63E8) == 923, "ANCHOR V282 0xC63E8"
    print("ANCHORS OK")

    res = {"anchors": "stock 0xC646C=891, stock 0x454FE=0xBA, V282 0x2A1F0=0x7CD0, V282 0xC63E8=923"}
    res["images"] = {}
    res["matrix"] = {}

    reads = [("STOCK", st, str(STOCK))]
    # the earlier arc anchors, so the matrix genuinely spans V38 -> V293
    for tag, pat in (("V38", "_v38_plain_image.bin"), ("V62", "_v62_plain_image.bin"),
                     ("V67", "_v67_plain_image.bin"), ("V84", "_v84_LEVERB"),
                     ("V88", "_v88_V87BASE"), ("V102", "_v102_V101BASE"),
                     ("V104", "_v104_V103BASE"), ("V112", "_v112_V112"),
                     ("V247", "_v247_V247"), ("V268", "_v268_V268")):
        hit = [p for p in sorted(ROOT.glob("*_plain_image.bin")) if p.name.startswith(pat)]
        if hit:
            reads.append((tag, hit[0].read_bytes(), hit[0].name))
        else:
            print(f"### MISSING anchor {tag} ({pat})", file=sys.stderr)
    for num, nm, p in ARC:
        reads.append((f"V{num}", p.read_bytes(), nm))
    if V293:
        for p in V293:
            reads.append(("V293", p.read_bytes(), p.name))
    if V279:
        for p in V279:
            if "SUPERSEDED" not in p.name:
                reads.append(("V279", p.read_bytes(), p.name))

    seen = {}
    for name, buf, nm in reads:
        if name in seen:
            seen[name] += 1
            name = f"{name}#{seen[name]}"
        else:
            seen[name] = 0
        d = read_build(buf)
        res["matrix"][name] = d
        res["images"][name] = {"file": nm, "sha256": hashlib.sha256(buf).hexdigest()}
        print(f"{name:8s} fb={d['0xC62E6']:6d} Dclamp={d['0xC61B6']:6d} r24={d['0xC6446']:5d} "
              f"Kp7={d['kp'][1]} Kd7={d['kd'][1]} maptop={d['map'][1][-1]} "
              f"gain={d['0xC6CD0']} pole={d['0xC63E8']}/{d['0xC63EA']}")

    # ---- the delivered surfaces
    d282 = res["matrix"]["V282"]
    surf = {}
    a, b = d282["0xC63E8"], d282["0xC63EA"]
    C = d282["0xC62E6"]
    for rate in (0, 5, 10, 15, 20, 30, 45):
        x = rate * 8                         # 8 raw counts per deg/s
        fb = fb_ss(a, b, x, C)
        surf[f"V282@{rate}"] = {"fb": fb, "T": [r[7] for r in surface(d282, fb)]}
        print(f"V282 wheel {rate:3d} deg/s -> fb operand {fb}")
    if "V293" in res["matrix"]:
        d293 = res["matrix"]["V293"]
        a3, b3, C3 = d293["0xC63E8"], d293["0xC63EA"], d293["0xC62E6"]
        for rate in (0, 10, 20, 45):
            fb = fb_ss(a3, b3, rate * 8, C3)
            s = surface(d293, fb)
            surf[f"V293@{rate}"] = {"fb": fb, "T": [r[7] for r in s]}
            print(f"V293 wheel {rate:3d} deg/s -> fb operand {fb}  T(240)={s[240][7]} "
                  f"Tceil(240)={s[240][8]} P(240)={s[240][4]}")
    # ---- FULL-FILE DIFF of the built V293 against V282 -- runs [0x13000, 0x100000) and also
    #      checks [0, 0x13000), the region the rwd does not carry.
    if "V293" in res["matrix"]:
        import numpy as np
        v293b = [b for n, b, _ in reads if n == "V293"][0]
        _a = np.frombuffer(v282, np.uint8)
        _b = np.frombuffer(v293b, np.uint8)
        _all = [int(x) for x in np.nonzero(_a != _b)[0]]
        diff = [i for i in _all if i >= 0x13000]
        low = [i for i in _all if i < 0x13000]
        clusters = []
        for i in diff:
            if clusters and i == clusters[-1][1]:
                clusters[-1][1] = i + 1
            else:
                clusters.append([i, i + 1])
        # attribute every differing byte: the three cells, the Kp/Kd record Y knots, the CRC trailers
        kpx, kdx = {}, {}
        for s in range(28):
            p = u32(v282, KP_PTR + s * 4)
            n = u16(v282, p)
            kpx[p] = (p + 2 + 2 * n, p + 2 + 4 * n)
            q = u32(v282, KD_PTR + s * 4)
            m = u16(v282, q)
            kdx[q] = (q + 2 + 2 * m, q + 2 + 4 * m)
        att = {"cell": 0, "kpY": 0, "kdY": 0, "crc": 0, "ORPHAN": 0}
        crcs = set()
        for i in _all:
            if any(c <= i < c + 2 for c in (0xC62E6, 0xC61B6, 0xC6446)):
                att["cell"] += 1
            elif any(lo <= i < hi for lo, hi in kpx.values()):
                att["kpY"] += 1
            elif any(lo <= i < hi for lo, hi in kdx.values()):
                att["kdY"] += 1
            elif (i & 0xFFF) >= 0xFFC:
                att["crc"] += 1
                crcs.add((i & ~0xFFF) | 0xFFC)
            else:
                att["ORPHAN"] += 1
        # SEMANTIC check on the BUILT image: the Kp LERP must read 120 and Kd 0 on every slot
        sem = []
        for s in range(28):
            _, Yp = rec(v293b, u32(v293b, KP_PTR + s * 4))[1:]
            _, Yd = rec(v293b, u32(v293b, KD_PTR + s * 4))[1:]
            if set(Yp) != {120} or set(Yd) != {0}:
                sem.append((s, Yp, Yd))
        res["diff"] = {"n_bytes": len(diff), "n_clusters": len(clusters), "n_below_0x13000": len(low),
                       "attribution": att, "crc_trailers": [f"0x{c:05X}" for c in sorted(crcs)],
                       "semantic_fail": sem,
                       "clusters": [[f"0x{a:05X}", b - a,
                                     v282[a:b].hex(" "), v293b[a:b].hex(" ")] for a, b in clusters]}
        print(f"  attribution {att}  |  CRC trailers "
              f"{' '.join(f'0x{c:05X}' for c in sorted(crcs))}")
        print(f"  semantic (Kp=120, Kd=0 on all 28 slots of the BUILT image): "
              f"{'PASS' if not sem else sem}")
        print(f"\n=== FULL-FILE DIFF V293 vs V282: {len(diff)} bytes in {len(clusters)} clusters; "
              f"{len(low)} bytes below 0x13000 ===")
        for a, b in clusters:
            print(f"  0x{a:05X}  {b - a:3d} B   {v282[a:b].hex(' '):<24} -> {v293b[a:b].hex(' ')}")
        rwd = list(Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/flashing-2020accord/rwd")
                   .glob("*V293*.rwd"))
        res["rwd"] = [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in rwd]
        for r_ in res["rwd"]:
            print(f"  rwd {r_['file']}\n      {r_['sha256']}")

    # ---- PROVISIONAL V293 arm, built from V282's OWN CELLS with the pre-registration's edits
    #      applied in memory.  DRAFTING AID ONLY, and skipped entirely once the image exists.
    import copy
    prov = copy.deepcopy(d282)
    prov["0xC62E6"] = 0
    prov["0xC61B6"] = 0
    prov["0xC6446"] = 2048
    prov["kp"] = [d282["kp"][0], [120] * len(d282["kp"][1])]
    prov["kd"] = [d282["kd"][0], [0] * len(d282["kd"][1])]
    res["matrix"]["V293_PROVISIONAL"] = prov
    sp3 = surface(prov, 0)
    surf["V293_PROVISIONAL@any"] = {"fb": 0, "T": [r[7] for r in sp3],
                                    "Tceil": [r[8] for r in sp3], "P": [r[4] for r in sp3]}
    print(f"\nPROVISIONAL V293 (synthesised from V282 cells, NOT from an image):")
    for idx in (0, 40, 80, 120, 160, 200, 239, 240):
        r_ = sp3[idx]
        print(f"  idx {idx:3d}  sp {r_[1]:5d}  P {r_[4]:6d}  T_ceil {r_[8]:5d}  T_ss {r_[7]:5d}")
    res["surface"] = surf

    # ---- the feedback operand transfer (operand vs wheel rate), both builds
    tr = {"rate": list(range(0, 61, 1))}
    tr["V282"] = [fb_ss(a, b, r * 8, C) for r in tr["rate"]]
    if "V293" in res["matrix"]:
        d3 = res["matrix"]["V293"]
        tr["V293"] = [fb_ss(d3["0xC63E8"], d3["0xC63EA"], r * 8, d3["0xC62E6"]) for r in tr["rate"]]
    res["fb_transfer"] = tr

    # ---- the r24 lane transfer, traced form
    #  r24 = -clip(deadband(trunc(clip(0.5*(bar[n]-bar[n-4])) * g / 1024)))
    r24 = {"d": list(range(-400, 401, 4))}
    for arm in (512, 2048, 4451, 4725, 5244):
        r24[str(arm)] = [
            (lambda v: 0 if abs(v) <= 3 else (v - 3 if v > 0 else v + 3))(
                max(-8192, min(8192, (dd * arm) >> 10)))
            for dd in r24["d"]]
    res["r24"] = r24

    # ---- POSITIVE CONTROLS against the build script's own published docstring table
    print("\n=== CONTROLS vs build_v293_tva.py docstring sec.2b (V282 columns) ===")
    exp = {0: (0, -385, -776), 40: (869, 485, 94), 80: (1739, 1355, 964),
           120: (2505, 2219, 1828), 160: (2505, 2505, 2505), 240: (2505, 2505, 2505)}
    s0 = surface(d282, 0)
    s10 = surface(d282, fb_ss(a, b, 80, C))
    s20 = surface(d282, fb_ss(a, b, 160, C))
    for idx, (e0, e10, e20) in exp.items():
        g0, g10, g20 = s0[idx][8], s10[idx][8], s20[idx][8]   # T_ceil convention
        tag = "PASS" if (g0, g10, g20) == (e0, e10, e20) else "**MISMATCH**"
        print(f"  idx {idx:3d}  ceil {g0:6d}/{g10:6d}/{g20:6d}  expected {e0:6d}/{e10:6d}/{e20:6d}  {tag}")
    print(f"  min((15360*5346)>>15, 3072) = {min((15360 * 5346) >> 15, 3072)}  (record: 2505)")
    print(f"  min((15360*891)>>15, 512)   = {min((15360 * 891) >> 15, 512)}  (record: 417)")
    print(f"  out-lag DC = 2*507/((1024-992)*32) = {2 * 507 / ((1024 - 992) * 32):.9f}  (record: 0.990234375)")
    print(f"  fb DC = 2*1560/(1024-923) = {2 * 1560 / (1024 - 923):.4f}  (record: 30.8911)")
    res["controls"] = {"v282_ceil_table": {str(k): [s0[k][8], s10[k][8], s20[k][8]] for k in exp},
                       "expected": {str(k): list(v) for k, v in exp.items()}}

    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}   ({OUT.stat().st_size} bytes)")
    print(f"V293 image present: {bool(V293)}")


if __name__ == "__main__":
    main()
