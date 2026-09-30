# -*- coding: utf-8 -*-
"""ab1b_twin_flags.py -- second consumers of what b scales: is the twin island (reader 0x2AFAE of gp-0x6a34) really
uncalled, and is the damper-mode gate gp-0x680a (reader 0x2A0CA) really never written?  Raw scan, positive-controlled.
ANALYSIS ONLY."""
exec(open(__file__.replace("ab1b_twin_flags.py", "ab1_bytes.py")).read().split("ALL = list(scan(img))")[0])

ISL_LO, ISL_HI = 0x2A30E, 0x2B421


def branches(b, lo=0x13000, hi=0x100000):
    for o in range(lo, hi - 6, 2):
        hw1, hw2 = u16(b, o), u16(b, o + 2)
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0:          # Format V jr/jarl disp22
            t = o + sext(((hw1 & 0x3F) << 16) | hw2, 22)
            yield o, ("jarl" if (hw1 >> 11) else "jr"), t
        if (hw1 & 0xFFE0) == 0x02E0:                                  # jr/jarl disp32 (6 bytes)
            d = u32(b, o + 2)
            if d & 1 == 0:
                yield o, "j32", o + sext(d, 32)


BR = list(branches(img))
ctl = [x for x in BR if x[0] == 0x22522 and x[2] == 0x28EA6]
print("control: jarl 0x22522 -> FUN_00028ea6 found:", bool(ctl))
assert ctl
ctl2 = [x for x in BR if x[2] == 0x3AA2C]
print("control: callers of FUN_0003aa2c:", ["0x%X" % x[0] for x in ctl2][:5])
into = [(o, k, t) for o, k, t in BR if ISL_LO <= t <= ISL_HI and not (ISL_LO <= o <= ISL_HI)]
print("branches from OUTSIDE into the twin island [0x%X,0x%X]: %d  %s" % (ISL_LO, ISL_HI, len(into),
      [("0x%X" % o, k, "0x%X" % t) for o, k, t in into][:20]))
le = [o for o in range(0, len(img) - 3) if ISL_LO <= u32(img, o) <= ISL_HI and (u32(img, o) & 1) == 0]
print("LE32 even constants pointing into the island (anywhere, incl. data): %d  %s" % (len(le), ["0x%X" % o for o in le][:20]))
# island function entry 0x2A93A specifically
print("branches to 0x2A93A:", [("0x%X" % o, k) for o, k, t in BR if t == 0x2A93A])


def bitops(b, base_reg, disp, lo=0x13000, hi=0x100000):
    out = []
    for o in range(lo, hi - 4, 2):
        hw1, hw2 = u16(b, o), u16(b, o + 2)
        if ((hw1 >> 5) & 0x3F) == 0x3E and (hw1 & 0x1F) == base_reg and sext(hw2, 16) == disp:
            out.append((o, ["set1", "not1", "clr1", "tst1"][hw1 >> 14], (hw1 >> 11) & 7))
    return out


ALL = list(scan(img))
for disp, nm in ((-0x680A, "gp-0x680a (damper-mode gate)"), (-0x6809, "gp-0x6809 (dither enable)")):
    acc = [(o, d[0]) for o, d in ALL if d[2] == 4 and d[1] > 0 and overlaps(d[3], d[1], disp, disp)]
    bo = bitops(img, 4, disp)
    print("%s: loads/stores %s ; bit-ops %s" % (nm, [("0x%X" % o, m) for o, m in acc], [("0x%X" % o, m, bit) for o, m, bit in bo]))
# positive control for the bit-op decoder: any set1/clr1 on gp somewhere
anyb = [o for o in range(0x13000, 0xC0000, 2) if ((u16(img, o) >> 5) & 0x3F) == 0x3E and (u16(img, o) & 0x1F) == 4]
print("bit-op decoder control: gp-relative bit ops found image-wide: %d (first 0x%X)" % (len(anyb), anyb[0] if anyb else 0))
