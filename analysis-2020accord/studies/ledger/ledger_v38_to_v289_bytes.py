#!/usr/bin/env python3
"""DELIVERED-BYTES LEDGER, V38 -> V289 (the rate-loop era cells).  Reads the PLAIN IMAGES ON DISK, never the build scripts.

Companion of ledger_v38_to_v84_bytes.py (which stops at V84 and reads the damper-era cells).  This one walks the milestone
builds of the whole post-V38 arc and reads the handful of cells the V276 -> V289 rate-loop work has moved or depended on,
plus the code bytes that mark each hook.  Plain images are flat 1 MiB code images: file offset == firmware address
(anchored below on 0xC646C == 891 on stock).  V850 is LITTLE-ENDIAN.

Run:  python ledger_v38_to_v289_bytes.py            (prints the matrix; writes ledger_v38_to_v289.json beside the CWD)
"""
import glob
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
STOCK = ROOT / "stock_fw_dump" / "code.bin"

# milestone builds, in flight order (the V38 -> V84 ledger covers the damper era in full; here one image per class change)
BUILDS = ["38", "57", "62", "84", "87", "101", "102", "104", "105", "108", "112", "122", "235", "241", "268",
          "276", "277", "278", "279", "280", "282", "283", "284", "285", "289"]
NOTE = {"38": "8x-era base", "57": "private fwd gain 0xC6CD0", "62": "rate lane sar (only measured grind fix)", "84": "damper back to Honda",
        "87": "REBASE on raw V38", "101": "8x gain", "102": "6x gain (flown)", "104": "c4 biquad gain, Lever B", "105": "25.5 Hz notch (assist lane)",
        "108": "Honda notch restored", "112": "relay knee", "122": "knee 3000, alpha2 8 (BEST of that era)", "235": "damper cells -> Honda", "241": "IMU notch",
        "268": "both pumps, V112 base", "276": "REFERENCE 6x map + feedback", "277": "override cliff softened", "278": "r3: reference 2x", "279": "pure feedforward (fb 0, Kd 0)",
        "280": "r2: LINEAR map to 6x, fb clamp 46080", "282": "Kp flat 248 + r24 comparator tap (FLOWN)", "283": "Ki 50", "284": "shaped Kp", "285": "Kp 0 (bench only)",
        "289": "SUM NOTCH cave + fb pole 25 Hz"}

# (addr, width, label): width 1 = byte, 2 = signed LE halfword, 4 = 4 raw bytes (code)
SITES = [
    (0xC646C, 2, "shared sensor scale (stock 891)"),
    (0xC6CD0, 2, "private forward LKAS gain (5346 = 6x)"),
    (0x2A1F0, 2, "gain-read displacement @0x2A1EE (7CD0 => 0xC6CD0)"),
    (0xC61B4, 2, "LKAS-gain output clamp T"),
    (0xC61B6, 2, "D-term clamp"),
    (0xC61BC, 2, "P clamp"),
    (0xC61BE, 2, "sum clamp S"),
    (0xC62E6, 2, "feedback (r26) clamp"),
    (0xC63E6, 2, "Ki"),
    (0xC63E8, 2, "fb lag pole a (923 = 16.5 Hz; 875 = 25 Hz)"),
    (0xC63EA, 2, "fb lag pole b (DC 2b/(1024-a))"),
    (0xC63EC, 2, "output lag pole a (992 = 5.05 Hz)"),
    (0xC63EE, 2, "output lag pole b"),
    (0xC6446, 2, "r24 engaged arm (Lever B)"),
    (0x3AA96, 1, "r24/r26 gate byte (C5 dead / FB latActive)"),
    (0x3AB76, 1, "V62 sar r26 (AA stock / A9 x2)"),
    (0x3AC20, 1, "V62 sar r24 (AA stock / A9 x2)"),
    (0x55DF2, 1, "427 tap source byte"),
    (0x55E10, 1, "427 packer shift byte"),
    (0x29D72, 4, "V288 hook site (st.h sp publish / jr)"),
    (0x2A174, 4, "V289 hook site (ld.hu 0x73ee,tp,r7 / jr 0xC4C00)"),
    (0xC4C00, 4, "cave @0xC4C00 first bytes"),
    (0xC4B34, 4, "0x14A telemetry cave first bytes"),
    (0xC4BD6, 4, "0x14A cave exit (jmp [lp] / jr tail)"),
]
# LERP banks indexed by the live selector 7: (pointer array, npt, label)
BANKS = [(0xC9A88, 10, "assist map slot 7 (Y knots)"), (0xCB994, 5, "Kp slot 7 (Y knots)"), (0xCB7D4, 4, "Kd slot 7 (Y knots)")]


def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]


def find_image(v):
    hits = [p for p in glob.glob(str(ROOT / ("_v%s_*plain_image.bin" % v))) if "SUPERSEDED" not in os.path.basename(p) and "DO-NOT-FLASH" not in os.path.basename(p)]
    if v == "38":
        hits = [str(ROOT / "_v38_plain_image.bin")]
    if len(hits) != 1:
        print("### V%s: %d candidate images %s" % (v, len(hits), [os.path.basename(h) for h in hits]), file=sys.stderr)
        return hits[0] if hits else None
    return hits[0]


def lerp_Y(b, ptr, npt):
    base = u32(b, ptr + 4 * 7)
    if base >= 0x100000:
        return "PTR_OOR"
    return [s16(b, base + 2 + 2 * npt + 2 * i) for i in range(npt)]


def main():
    imgs = {"STOCK": STOCK.read_bytes()}
    order = ["STOCK"]
    for v in BUILDS:
        p = find_image(v)
        if p:
            imgs["V" + v] = Path(p).read_bytes(); order.append("V" + v)
    st = imgs["STOCK"]
    assert len(st) == 0x100000 and s16(st, 0xC646C) == 891 and st[0x454FE] == 0xBA
    print("ANCHORS OK (stock 0xC646C=891, 0x454FE=0xBA); images: %s\n" % " ".join(order))
    out = {"order": order, "scalars": [], "banks": []}

    def fmt(v, w):
        if w == 1: return "%02X" % v
        if w == 4: return v.hex()
        return str(v)

    def rd(b, a, w):
        return b[a] if w == 1 else (b[a:a + 4] if w == 4 else s16(b, a))

    print("=== SCALAR / CODE SITES, run-length along the build order (only rows that change somewhere; [CONSTANT] rows listed at the end) ===")
    const = []
    for addr, w, label in SITES:
        vals = {n: rd(imgs[n], addr, w) for n in order}
        out["scalars"].append({"addr": "0x%05X" % addr, "w": w, "label": label, "vals": {n: fmt(vals[n], w) for n in order}})
        if len(set(fmt(v, w) for v in vals.values())) == 1:
            const.append("0x%05X %s = %s" % (addr, label, fmt(vals["STOCK"], w))); continue
        print("\n0x%05X  %s" % (addr, label))
        prev = None; run = []; segs = []
        for n in order:
            v = fmt(vals[n], w)
            if v != prev:
                if run: segs.append((prev, run))
                run = [n]; prev = v
            else:
                run.append(n)
        if run: segs.append((prev, run))
        for v, r in segs:
            print("    %-12s : %s" % (v, (r[0] + ".." + r[-1]) if len(r) > 1 else r[0]))
    print("\n[CONSTANT across every image above]")
    for c in const:
        print("    " + c)

    print("\n=== LERP BANKS (selector 7), run-length ===")
    for ptr, npt, label in BANKS:
        vals = {n: lerp_Y(imgs[n], ptr, npt) for n in order}
        out["banks"].append({"ptr": "0x%05X" % ptr, "label": label, "vals": {n: str(vals[n]) for n in order}})
        print("\n%s (ptr 0x%05X)" % (label, ptr))
        prev = None; run = []; segs = []
        for n in order:
            v = str(vals[n])
            if v != prev:
                if run: segs.append((prev, run))
                run = [n]; prev = v
            else:
                run.append(n)
        if run: segs.append((prev, run))
        for v, r in segs:
            print("    %-14s %s" % ((r[0] + ".." + r[-1]) if len(r) > 1 else r[0], v))

    print("\n=== notes per milestone ===")
    for v in BUILDS:
        if "V" + v in imgs:
            print("  V%-4s %s" % (v, NOTE.get(v, "")))
    outp = Path(os.environ.get("LEDGER_OUT", "ledger_v38_to_v289.json"))
    outp.write_text(json.dumps(out, indent=1))
    print("\nwrote %s" % outp)


if __name__ == "__main__":
    main()
