# -*- coding: utf-8 -*-
r"""rb_table.py -- C3 rev2-B: build a G(v) table that keeps G >= 512 at EVERY speed (N2) while staying close to
G-P48, and verify the integer-walk G >= 512 property and the one-sided-quantum property is gone.

ANALYSIS ONLY.  The table is DATA only (0 code bytes vs C3-P's cave); it is scored by the common frequency scorer
(rb_freq.py) and the refuter model (rb_gate2.py).  N2 is: Honda's I quantum e5 = ((E*G)>>8)>>5 is one-sided when
G < 512 (e5 = 0 for a +0.1 deg error, -1 for -0.1 deg), so small-signal in-phase tracking collapses in the dip.
Keeping G >= 512 makes e5 see at least +-1 per 0.1 deg at every speed.

usage: python rb_table.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "panel2"))
sys.path.insert(0, str(AL / "panel"))
sys.path.insert(0, str(AL / "c1"))
import c1_lib as C  # noqa: E402

GD = AL / "panel2" / "G-d-operand-and-margins"
gj = json.loads((GD / "g_impls_frozen.json").read_text())
GP48 = [tuple(r) for r in gj["G-P48"]["rows"]]
GF24 = [tuple(r) for r in gj["G-F24"]["rows"]]

# The G-P48 dip is at the 2707 knot (G 463), interpolating to 462 at vc 2621-2814 (11.38-12.21 m/s).
# rev2-B raises the dip floor to >= 540 (margin over 512) by lifting the 2707 knot and re-sloping its neighbours so
# the walk stays >= 520 everywhere, keeping the 714/1843 (low-speed) and 4032/6198 (high-speed) knots of G-P48.
# The I path sees at least +-1 per 0.1 deg at G 520 (e5(+1)= (520*16>>8)>>5 = 1).


def walk_min(rows):
    """min integer-walk G over 0..7000 counts (0..30 m/s) and the vcount where it occurs."""
    mn, arg = 1 << 30, None
    for vc in range(0, 7001):
        g = C.cave_G(vc, rows)
        if g < mn:
            mn, arg = g, vc
    return mn, arg


def quantum_one_sided(G):
    """e5 for a +1 / -1 count (0.1 deg) error at gain G: ((E*16*G)>>8)>>5 with E = +-16 (16 counts per 0.1 deg of E').
    returns (e5_plus, e5_minus).  one-sided iff e5_plus == 0."""
    def e5(Ecounts):
        Ep = (Ecounts * G) >> 8
        return Ep >> 5
    return e5(16), e5(-16)


# --- rev2-B P table (G-P48 with the dip lifted to >= 520; low/high-speed knots kept) -----------------------------
# knots (X, G, S Q12).  S chosen so the segment to the next knot is linear between the two G values:
# S(i) = round((G(i+1)-G(i)) * 4096 / (X(i+1)-X(i))).
def reslope(knotsGX):
    out = []
    for i, (X, G) in enumerate(knotsGX):
        if i + 1 < len(knotsGX):
            X1, G1 = knotsGX[i + 1]
            S = round((G1 - G) * 4096 / (X1 - X)) if X1 != 0xFFFF else 0
        else:
            S = 0
        out.append((X, G, S))
    return out


# P: keep G-P48's 714(1178) 1843(1465) 4032(1068) 6198(2188); lift 2304 & 2707 so the dip floor is ~540
KN_P = [(714, 1178), (1843, 1465), (2304, 760), (2707, 560), (4032, 1068), (6198, 2188), (0xFFFF, 2188)]
# F: keep G-F24's 714(1009) 1843(1255) 4032(915) 6198(1948); lift 2304 & 2707 so the dip floor is ~540
KN_F = [(714, 1009), (1843, 1255), (2304, 720), (2707, 560), (4032, 915), (6198, 1948), (0xFFFF, 1948)]

GB_P = reslope(KN_P)
GB_F = reslope(KN_F)


def report():
    out = []
    for nm, rows, old in (("GB-P (rev2B P)", GB_P, GP48), ("GB-F (rev2B F)", GB_F, GF24)):
        mn, arg = walk_min(rows)
        mo, _ = walk_min(old)
        out.append(f"{nm}: rows {rows}")
        out.append(f"   walk min G = {mn} at vc {arg} ({arg / 230.4:.2f} m/s)  [old {mo}]; >= 512 ? {mn >= 512}")
        for v in (10, 11, 11.5, 11.75, 12, 12.5, 13, 14, 15, 17, 20, 26.9):
            vc = int(v * 230.4)
            g = C.cave_G(vc, rows)
            qp, qm = quantum_one_sided(g)
            out.append(f"     v {v:5.1f}  vc {vc:5d}  G {g:5d}  e5(+0.1 deg)/{qp}  e5(-0.1 deg)/{qm}"
                       + ("  ONE-SIDED" if qp == 0 else ""))
    print("\n".join(out))
    (HERE.parents[3] / "_scratch" / "angle_loop" / "c3-rev2B").mkdir(parents=True, exist_ok=True)
    (HERE.parents[3] / "_scratch" / "angle_loop" / "c3-rev2B" / "rb_table_out.txt").write_text("\n".join(out))


if __name__ == "__main__":
    report()
