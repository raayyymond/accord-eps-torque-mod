# -*- coding: utf-8 -*-
"""Emit exact SVG geometry for the V293 close-out page. Nothing eyeballed."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.load(open(HERE / "v293_page_data.json"))
M = D["matrix"]
OUT = {}


def lerp(X, Y, x):
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])


class Ax:
    def __init__(self, x0, y0, w, h, xlo, xhi, ylo, yhi):
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        self.xlo, self.xhi, self.ylo, self.yhi = xlo, xhi, ylo, yhi

    def X(self, v):
        return self.x0 + (v - self.xlo) / (self.xhi - self.xlo) * self.w

    def Y(self, v):
        return self.y0 + self.h - (v - self.ylo) / (self.yhi - self.ylo) * self.h

    def pts(self, xs, ys):
        return " ".join(f"{self.X(a):.1f},{self.Y(b):.1f}" for a, b in zip(xs, ys))

    def xticks(self, vals, fmt="{:g}"):
        return [(round(self.X(v), 1), fmt.format(v)) for v in vals]

    def yticks(self, vals, fmt="{:g}"):
        return [(round(self.Y(v), 1), fmt.format(v)) for v in vals]


def knotdots(ax, X, Y):
    return [(round(ax.X(a), 2), round(ax.Y(b), 2)) for a, b in zip(X, Y)]


# ============================================================ A. assist map
mX, mY = M["V282"]["map"]
sX, sY = M["STOCK"]["map"]
ax = Ax(56, 20, 372, 186, 0, 240, 0, 1100)
idxs = list(range(0, 241))
OUT["map"] = {
    "ax": ["56", "20", "372", "186"],
    "v282": ax.pts(idxs, [lerp(mX, mY, i) for i in idxs]),
    "stock": ax.pts(idxs, [lerp(sX, sY, i) for i in idxs]),
    "v282_knots": knotdots(ax, mX, mY),
    "stock_knots": knotdots(ax, sX, sY),
    "xt": ax.xticks([0, 48, 96, 144, 192, 240]),
    "yt": ax.yticks([0, 250, 500, 750, 1000]),
    "rate_yt": [(round(ax.Y(v), 1), f"{v * 32 / (30.8911 * 8):.0f}") for v in [0, 250, 500, 750, 1000]],
    "slope": mY[-1] / 240,
}

# ============================================================ B. Kp schedule
kX = M["V282"]["kp"][0]
kY282 = M["V282"]["kp"][1]
kYstock = M["STOCK"]["kp"][1]
axk = Ax(56, 20, 372, 186, 0, 240, 0, 760)
OUT["kp"] = {
    "ax": ["56", "20", "372", "186"],
    "stock": axk.pts(idxs, [lerp(kX, kYstock, i) for i in idxs]),
    "v282": axk.pts(idxs, [248] * 241),
    "v293": axk.pts(idxs, [120] * 241),
    "other_levels": {str(v): round(axk.Y(v), 1) for v in (205, 266, 307)},
    "stock_knots": knotdots(axk, kX, kYstock),
    "knotx": [round(axk.X(v), 1) for v in kX],
    "knotlbl": [str(v) for v in kX],
    "xt": axk.xticks([0, 48, 96, 144, 192, 240]),
    "yt": axk.yticks([0, 120, 248, 400, 600, 760]),
    "y248": round(axk.Y(248), 1), "y120": round(axk.Y(120), 1),
}

# ============================================================ C. Kd schedule
dX = M["V282"]["kd"][0]
axd = Ax(56, 20, 372, 186, 0, 48, 0, 150)
xs = list(range(0, 49))
OUT["kd"] = {
    "ax": ["56", "20", "372", "186"],
    "v282": axd.pts(xs, [128] * 49),
    "other": axd.pts(xs, [64] * 49),
    "v293": axd.pts(xs, [0] * 49),
    "knotx": [round(axd.X(v), 1) for v in dX],
    "knotlbl": [str(v) for v in dX],
    "xt": axd.xticks([0, 11, 22, 32, 48]),
    "yt": axd.yticks([0, 64, 128, 150]),
    "y128": round(axd.Y(128), 1), "y64": round(axd.Y(64), 1), "y0": round(axd.Y(0), 1),
}

# ============================================================ D. feedback operand transfer
tr = D["fb_transfer"]
axf = Ax(56, 20, 372, 186, 0, 60, -400, 16000)
OUT["fb"] = {
    "ax": ["56", "20", "372", "186"],
    "v282": axf.pts(tr["rate"], tr["V282"]),
    "v293": axf.pts(tr["rate"], [0] * len(tr["rate"])),
    "xt": axf.xticks([0, 15, 30, 45, 60]),
    "yt": axf.yticks([0, 4000, 8000, 12000, 16000], "{:,.0f}"),
    "y0": round(axf.Y(0), 1),
    "at10": tr["V282"][10], "at20": tr["V282"][20], "at45": tr["V282"][45],
}

# ============================================================ E. override taper record
oX, oY = M["V282"]["taper_ovr"]
axo = Ax(56, 20, 372, 150, 60, 92, -10, 275)
ox = [60] + list(oX) + [92]
oy = [oY[0]] + list(oY) + [oY[-1]]
fine = list(range(60, 93))
OUT["taper"] = {
    "ax": ["56", "20", "372", "150"],
    "v282": axo.pts(fine, [lerp(oX, oY, v) for v in fine]),
    "knots": knotdots(axo, oX, oY),
    "xt": axo.xticks([60, 70, 80, 90]),
    "yt": axo.yticks([0, 128, 254]),
}
cX, cY = M["V282"]["taper_C"]
dX2, dY2 = M["V282"]["taper_D"]
axs2 = Ax(56, 20, 372, 150, 0, 120, -10, 275)
fs = list(range(0, 121))
OUT["speedtaper"] = {
    "ax": ["56", "20", "372", "150"],
    "C": axs2.pts(fs, [lerp(cX, cY, v) for v in fs]),
    "Dd": axs2.pts(fs, [lerp(dX2, dY2, v) for v in fs]),
    "Cknots": knotdots(axs2, cX, cY), "Dknots": knotdots(axs2, dX2, dY2),
    "xt": axs2.xticks([0, 30, 60, 90, 120]),
    "yt": axs2.yticks([0, 128, 255]),
}

# ============================================================ F. r24 lane transfer
r = D["r24"]
axr = Ax(56, 20, 372, 186, -400, 400, -2200, 2200)
OUT["r24"] = {
    "ax": ["56", "20", "372", "186"],
    "a5244": axr.pts(r["d"], [-v for v in r["5244"]]),
    "a2048": axr.pts(r["d"], [-v for v in r["2048"]]),
    "a512": axr.pts(r["d"], [-v for v in r["512"]]),
    "xt": axr.xticks([-400, -200, 0, 200, 400]),
    "yt": axr.yticks([-2000, -1000, 0, 1000, 2000], "{:,.0f}"),
    "y0": round(axr.Y(0), 1), "x0": round(axr.X(0), 1),
    "slope5244": 5244 / 1024, "slope2048": 2048 / 1024, "slope512": 512 / 1024,
}

# ============================================================ G. delivered surface
S = D["surface"]
axg = Ax(62, 20, 500, 230, 0, 240, -900, 2700)
key293 = "V293@0" if "V293@0" in S else "V293_PROVISIONAL@any"
OUT["surface"] = {
    "ax": ["62", "20", "500", "230"],
    "provisional": key293.startswith("V293_PROV"),
    "v293": axg.pts(idxs, S[key293]["T"]),
    "v282_0": axg.pts(idxs, S["V282@0"]["T"]),
    "v282_10": axg.pts(idxs, S["V282@10"]["T"]),
    "v282_20": axg.pts(idxs, S["V282@20"]["T"]),
    "v282_45": axg.pts(idxs, S["V282@45"]["T"]),
    "xt": axg.xticks([0, 48, 96, 144, 192, 240]),
    "yt": axg.yticks([-500, 0, 500, 1000, 1500, 2000, 2500], "{:,.0f}"),
    "y0": round(axg.Y(0), 1),
    "rail": round(axg.Y(2461), 1),
    "ceil": round(axg.Y(2505), 1),
    "tbl": {str(i): {"v293": S[key293]["T"][i], "v282_0": S["V282@0"]["T"][i],
                     "v282_10": S["V282@10"]["T"][i], "v282_20": S["V282@20"]["T"][i],
                     "v282_45": S["V282@45"]["T"][i]}
            for i in (0, 12, 24, 48, 96, 120, 160, 200, 240)},
}

# ============================================================ MINIS for the diagram
# Each mini is drawn in its own local box, origin (0,0), size W x H; the diagram <use>s
# them by translating a <g>.  No axes -- a baseline plus the two curves.
MW, MH = 96, 44


def mini(xlo, xhi, ylo, yhi):
    return Ax(0, 0, MW, MH, xlo, xhi, ylo, yhi)


mm = mini(0, 240, 0, 1100)
mk = mini(0, 240, 0, 760)
md = mini(0, 48, 0, 150)
mf = mini(0, 60, 0, 16000)
mt = mini(60, 92, 0, 275)
mr = mini(-400, 400, -2200, 2200)
ms = mini(0, 240, -900, 2700)
OUT["mini"] = {
    "W": MW, "H": MH,
    "map_v282": mm.pts(idxs, [lerp(mX, mY, i) for i in idxs]),
    "map_stock": mm.pts(idxs, [lerp(sX, sY, i) for i in idxs]),
    "kp_v282": mk.pts(idxs, [248] * 241),
    "kp_v293": mk.pts(idxs, [120] * 241),
    "kp_stock": mk.pts(idxs, [lerp(kX, kYstock, i) for i in idxs]),
    "kd_v282": md.pts(xs, [128] * 49),
    "kd_v293": md.pts(xs, [0] * 49),
    "fb_v282": mf.pts(tr["rate"], tr["V282"]),
    "fb_v293": mf.pts(tr["rate"], [0] * len(tr["rate"])),
    "fb_zero": round(mf.Y(0), 1),
    "taper": mt.pts(fine, [lerp(oX, oY, v) for v in fine]),
    "sC": mini(0, 120, 0, 275).pts(fs, [lerp(cX, cY, v) for v in fs]),
    "sD": mini(0, 120, 0, 275).pts(fs, [lerp(dX2, dY2, v) for v in fs]),
    "r24_5244": mr.pts(r["d"], [-v for v in r["5244"]]),
    "r24_2048": mr.pts(r["d"], [-v for v in r["2048"]]),
    "r24_zero": round(mr.Y(0), 1),
    "surf_v293": ms.pts(idxs, S[key293]["T"]),
    "surf_v282_0": ms.pts(idxs, S["V282@0"]["T"]),
    "surf_v282_20": ms.pts(idxs, S["V282@20"]["T"]),
    "surf_zero": round(ms.Y(0), 1),
}

Path(HERE / "v293_charts.json").write_text(json.dumps(OUT, indent=1))
print(json.dumps({k: (v if not isinstance(v, dict) else
                      {kk: (vv[:90] + "..." if isinstance(vv, str) and len(vv) > 90 else vv)
                       for kk, vv in v.items()}) for k, v in OUT.items()}, indent=1)[:6000])
