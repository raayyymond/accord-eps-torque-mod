"""
c2_reader_census.py -- V295 census, step 2: reader/writer census of every cell that shapes the LKAS PID,
by an independent raw Python scan of each IMAGE (never the build scripts), positive-controlled.

Encodings scanned (V850E2, little-endian; hw0 = first halfword):
  4-byte Format VII  hw0 = reg2<<11 | op6<<5 | reg1, reg1 in {gp=4, tp=5, r0=0}, disp16 in hw1:
     op 0x38 ld.b    disp = sext(hw1)
     op 0x39 ld.h / ld.w (hw1 bit0 = 1 -> .w)          disp = sext(hw1 & ~1)
     op 0x3A st.b    disp = sext(hw1)
     op 0x3B st.h / st.w (hw1 bit0 = 1 -> .w)          disp = sext(hw1 & ~1)
     op 0x3C/0x3D ld.bu  ONLY if hw1 bit0 = 1          disp = sext((hw1 & ~1) | (op & 1))   <- parity trap
                     (hw1 bit0 = 0 is Format V jr/jarl -- rejected)
     op 0x3E  set1/clr1/not1/tst1 (Format VIII, bit ops, byte RMW)   disp = sext(hw1)
     op 0x3F ld.hu   ONLY if hw1 bit0 = 1 (hw1 bit0 = 0 is mul/setfcc/... Format IX/XI)  disp = sext(hw1 & ~1)
  6-byte Format XIV (extended disp23):  hw0 & 0xFFE0 in {0x0780, 0x07A0}, reg1 = hw0 & 31,
     sub-op = hw1 & 0xF in {5,7,9,0xD,0xF}; disp = (sext(hw2) << 7) | ((hw1 >> 4) & 0x7F)
  absolute:  every LE32 == the target (mov imm32 operand, pointer tables)
  6-byte mov imm32 (hw0 = 0x0620 | reg): reported through the LE32 hit at +2.
Blind spots (stated, not closed): register-indirect loads/stores through a pointer that is not a literal,
ep-relative sld/sst (short forms), and arithmetic address construction other than a literal.

Positive controls are run FIRST on the V294 image; if any fails the script aborts.
Run:  python c2_reader_census.py  -> _scratch/out/c2_census.json
"""
import json
import os
import struct
from pathlib import Path

from c1_images_and_cells import IMAGES, load

GP = 0xFEDF8000
TP = 0xBF000
LO, HI = 0x13000, 0x100000     # code + cal + caves (0xC4xxx caves live above 0xC0000)


def s16(v): return v - 0x10000 if v & 0x8000 else v


def scan(b):
    """yield (addr, length, mnem, base_reg, reg2, disp) for every even offset"""
    out = []
    n = len(b)
    for a in range(LO, min(HI, n) - 6, 2):
        h0 = b[a] | b[a + 1] << 8
        h1 = b[a + 2] | b[a + 3] << 8
        reg1 = h0 & 31
        op = (h0 >> 5) & 0x3F
        reg2 = h0 >> 11
        m = None
        if op == 0x38:
            m, d = "ld.b", s16(h1)
        elif op == 0x39:
            m, d = ("ld.w" if h1 & 1 else "ld.h"), s16(h1 & 0xFFFE)
        elif op == 0x3A:
            m, d = "st.b", s16(h1)
        elif op == 0x3B:
            m, d = ("st.w" if h1 & 1 else "st.h"), s16(h1 & 0xFFFE)
        elif op in (0x3C, 0x3D) and (h1 & 1):
            m, d = "ld.bu", s16((h1 & 0xFFFE) | (op & 1))
        elif op == 0x3E:
            sub = (h0 >> 14) & 3
            m, d = ("set1", "not1", "clr1", "tst1")[sub], s16(h1)
        elif op == 0x3F and (h1 & 1) and reg2 != 0:
            m, d = "ld.hu", s16(h1 & 0xFFFE)
        if m is not None:
            out.append((a, 4, m, reg1, reg2, d))
        if (h0 & 0xFFE0) in (0x0780, 0x07A0) and (h1 & 0xF) in (5, 7, 9, 0xD, 0xF):
            h2 = b[a + 4] | b[a + 5] << 8
            disp = (s16(h2) << 7) | ((h1 >> 4) & 0x7F)
            k = {(0x0780, 5): "ld.b", (0x07A0, 5): "ld.bu", (0x0780, 7): "ld.h", (0x07A0, 7): "ld.hu",
                 (0x0780, 9): "ld.w", (0x0780, 0xD): "st.b", (0x07A0, 0xD): "st.h", (0x0780, 0xF): "st.w"}.get((h0 & 0xFFE0, h1 & 0xF), "x6?")
            out.append((a, 6, k + "(x6)", h0 & 31, (h1 >> 11) & 31, disp))
    return out


def abs_hits(b, val):
    pat = struct.pack("<I", val)
    r, i = [], b.find(pat, LO)
    while i != -1 and i < HI:
        r.append(i)
        i = b.find(pat, i + 1)
    return r


def index(ins):
    """(base_reg, disp) -> list of (addr, mnem, len)"""
    ix = {}
    for a, ln, m, r1, r2, d in ins:
        ix.setdefault((r1, d), []).append((a, m, ln))
    return ix


def gp_cell(off):     # gp - off
    return (4, -off)


def tp_cell(addr):
    return (5, addr - TP)


# ---------------- targets ------------------------------------------------------------------------------
FLASH = {  # address: what
    0xC62E4: "I deadband", 0xC62E6: "fb operand clamp C", 0xC63E2: "sibling filter a2", 0xC63E4: "sibling filter b2",
    0xC63E6: "Ki", 0xC63E8: "fb-lag pole a", 0xC63EA: "fb-lag gain b", 0xC63EC: "out-lag a", 0xC63EE: "out-lag b",
    0xC61B2: "fwd clamp (FUN_0002b422)", 0xC61B4: "lane out clamp", 0xC61B6: "D clamp", 0xC61B8: "out gate thr",
    0xC61BA: "I clamp", 0xC61BC: "P clamp", 0xC61BE: "sum clamp", 0xC64A3: "out gate arm", 0xC6CD0: "fwd gain (V57+)",
    0xC646C: "stock fwd gain / sensor scale", 0xC64F0: "idx clamp +", 0xC64F1: "idx clamp -", 0xC64B8: "override idx cut",
    0xC6446: "r24 engaged arm", 0xC63DA: "697e tgt a", 0xC63DC: "697e tgt b", 0xC63DE: "697c tgt a", 0xC63E0: "697c tgt b",
    0xC6976: "activity LERP X0", 0xC6712: "damper-mode LERP X0", 0xC6710: "damper-mode table base", 0xC6736: "dither LERP X0",
    0xC613A: "rate producer Q15 scale",
}
BANKS = {0xC9A88: "assist map", 0xCB994: "Kp", 0xCB7D4: "Kd", 0xCB844: "LIM", 0xCB8B4: "G ne", 0xCB924: "G eq",
         0xCBA04: "G ov ne", 0xCBA74: "G ov eq", 0xCBB54: "taper A", 0xCBC34: "taper B", 0xCBAE4: "taper C", 0xCBBC4: "taper D"}
RECORDS = {0xE5378: "Kp rec sel7", 0xE511C: "Kd rec sel7", 0xE502C: "map rec sel7"}
RAM = {  # gp offset (positive number, cell = gp - off): what
    0x6a56: "x (rate operand)", 0x4ca6: "x lockstep mirror", 0x3d30: "fb-lag state s", 0x3d2c: "fb sentinel",
    0x3d34: "sibling filter state", 0x6dd0: "I state (8*I)", 0x6cf8: "E_prev", 0x3d3c: "out-lag state",
    0x6a32: "sp published", 0x697a: "idx published", 0x674b: "idx byte (427 tap)", 0x6a34: "|fb>>5|",
    0x680a: "damper-mode flag", 0x6b2c: "addend (dither)", 0x6b2e: "S published (tapered, clamped)",
    0x6b32: "P published", 0x6b34: "raw sum published", 0x6b36: "D published", 0x6b30: "yr (ramped y)",
    0x6b38: "T lane torque", 0x6b3c: "gated forward", 0x69b0: "engage ramp", 0x6809: "dither enable",
    0x6803: "0xE4 byte-2 field (taper/G arm)", 0x682f: "|bar|>>5 sat", 0x6830: "|d bar|>>6", 0x6752: "pol",
    0x69ae: "cmd (-4*wire)", 0x697e: "published scale a", 0x697c: "published scale b", 0x6806: "ramp-up flag",
    0x67a4: "forward gate state", 0x674e: "variant selector", 0x6805: "engage request", 0x3570: "soft-EME integrator",
}

CONTROLS = [  # (image, addr, base, disp, mnem-prefix)  -- known from the V294 decompile/listing
    ("v294", 0x28F4C, 4, -0x6a56, "ld.h"), ("v294", 0x28F7C, 4, -0x3d30, "ld.w"), ("v294", 0x28FA8, 4, -0x3d30, "st.w"),
    ("v294", 0x28F66, 4, -0x3d2c, "ld.bu"), ("v294", 0x28F8A, 5, 0x73E8, "ld.h"), ("v294", 0x28F86, 5, 0x73EA, "ld.hu"),
    ("v294", 0x290CA, 4, -0x6a34, "st.h"), ("v294", 0x48E56, 4, -0x6752, ""),  # 6-byte form
    ("v294", 0x29D6E, 5, 0x72E4, "ld.hu"), ("v294", 0x29D9C, 5, 0x73E6, "ld.hu"), ("v294", 0x29DA0, 5, 0x71BA, "ld.hu"),
    ("v294", 0x29DA4, 4, -0x6dd0, "ld.w"), ("v294", 0x2A190, 4, -0x6dd0, "st.w"), ("v294", 0x2A18C, 4, -0x6cf8, "st.w"),
    ("v294", 0x29E5E, 4, -0x6cf8, "ld.w"), ("v294", 0x29E3A, 5, 0x71BC, "ld.hu"), ("v294", 0x2A184, 5, 0x73EC, "ld.h"),
    ("v294", 0x2A174, 5, 0x73EE, "ld.hu"), ("v294", 0x2A23C, 4, -0x6b38, "st.h"), ("v294", 0x29A68, 4, -0x680a, "ld.bu"),
    ("v294", 0x29A7C, 4, -0x682f, "ld.bu"), ("v294", 0x2A1EE, 5, 0x7CD0, "ld.h"),
]


def main():
    imgs = load()
    scans = {k: scan(v[0]) for k, v in imgs.items()}
    ixs = {k: index(v) for k, v in scans.items()}
    out = {"n_accesses": {k: len(v) for k, v in scans.items()}}
    print("gp/tp/r0-relative accesses decoded per image:", out["n_accesses"])

    # ---- positive controls (abort on any failure) ----
    fails = 0
    for img, a, base, d, mp in CONTROLS:
        hits = [h for h in ixs[img].get((base, d), []) if h[0] == a and h[1].startswith(mp)]
        ok = bool(hits)
        fails += not ok
        print(f"  CONTROL {img} {a:#07x} {'gp' if base == 4 else 'tp'}{d:+#x} {mp:6s} -> {'PASS' if ok else 'FAIL'} {hits}")
    abs_ok = 0x29DC8 in abs_hits(imgs["v294"][0], 0xCB994)
    print(f"  CONTROL abs LE32 0xCB994 at 0x29DC8 (mov imm32 @0x29DC6) -> {'PASS' if abs_ok else 'FAIL'}")
    fails += not abs_ok
    assert fails == 0, f"{fails} positive controls failed -- the scanner's nulls are worth nothing"
    print(f"  all {len(CONTROLS) + 1} positive controls PASS\n")

    res = {}

    def report(label, key_fn, items, absval=None):
        for addr, what in items.items():
            key = key_fn(addr)
            row = {}
            for k in imgs:
                hits = sorted(ixs[k].get(key, []))
                ab = abs_hits(imgs[k][0], absval(addr)) if absval else []
                row[k] = {"sites": [(hex(a), m, ln) for a, m, ln in hits], "abs": [hex(x) for x in ab]}
            res[f"{label}:{addr:#x}"] = {"what": what, **row}
            v = row["v294"]
            rd = [s for s in v["sites"] if not s[1].startswith(("st", "set1", "clr1", "not1"))]
            wr = [s for s in v["sites"] if s[1].startswith(("st", "set1", "clr1", "not1"))]
            same = all(row[k]["sites"] == v["sites"] for k in imgs)
            print(f"{label} {addr:#07x} {what:34s} V294: {len(rd)} rd / {len(wr)} wr ; abs {len(v['abs'])} ; "
                  f"identical sites on all 4 images: {same}")
            for s in v["sites"]:
                print(f"        {s[0]:>8s} {s[1]}")
            if v["abs"]:
                print(f"        abs LE32 at {v['abs']}")
            if not same:
                for k in imgs:
                    if row[k]["sites"] != v["sites"]:
                        print(f"        ({k} differs: {row[k]['sites']})")

    print("=== FLASH CAL CELLS (tp-relative + absolute) ===")
    report("tp", tp_cell, FLASH, absval=lambda a: a)
    print("\n=== PER-VARIANT BANK BASES (absolute LE32 -- the mov imm32 operand) ===")
    for addr, what in BANKS.items():
        row = {k: [hex(x) for x in abs_hits(imgs[k][0], addr)] for k in imgs}
        res[f"bank:{addr:#x}"] = {"what": what, **row}
        print(f"bank {addr:#07x} {what:10s} V294 abs LE32 at {row['v294']} ; same on all: {all(row[k] == row['v294'] for k in imgs)}")
    print("\n=== sel-7 RECORD POINTERS (who holds a pointer to the record) ===")
    for addr, what in RECORDS.items():
        row = {k: [hex(x) for x in abs_hits(imgs[k][0], addr)] for k in imgs}
        res[f"rec:{addr:#x}"] = {"what": what, **row}
        print(f"rec  {addr:#07x} {what:12s} V294 LE32 at {row['v294']}")
    print("\n=== RAM CELLS (gp-relative + absolute 0xFEDFxxxx) ===")
    report("gp", lambda off: gp_cell(off), RAM, absval=lambda off: (GP - off) & 0xFFFFFFFF)

    od = Path(__file__).resolve().parent / "_scratch" / "out"
    od.mkdir(exist_ok=True)
    (od / "c2_census.json").write_text(json.dumps(res, indent=1))
    print("\nwrote", od / "c2_census.json")


if __name__ == "__main__":
    main()
