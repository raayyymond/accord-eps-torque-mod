# -*- coding: utf-8 -*-
"""Render the V293 close-out page from the IMAGE-DERIVED json. Re-runnable."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = json.load(open(HERE / "v293_charts.json"))
D = json.load(open(HERE / "v293_page_data.json"))
M, IMG = D["matrix"], D["images"]
_side = HERE / "v293_diff.json"
if _side.exists():
    D.update(json.load(open(_side)))
P = {}


def gridx(ticks, y0, h, cls="g"):
    return "".join(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y0 + h}" class="gl"/>'
                   f'<text x="{x}" y="{y0 + h + 15}" class="tk" text-anchor="middle">{t}</text>'
                   for x, t in ticks)


def gridy(ticks, x0, w, anchor="end", dx=-7):
    return "".join(f'<line x1="{x0}" y1="{y}" x2="{x0 + w}" y2="{y}" class="gl"/>'
                   f'<text x="{x0 + dx}" y="{y + 4}" class="tk" text-anchor="{anchor}">{t}</text>'
                   for y, t in ticks)


def rgridy(ticks, x0, w, dx=7):
    return "".join(f'<text x="{x0 + w + dx}" y="{y + 4}" class="tk" text-anchor="start">{t}</text>'
                   for y, t in ticks)


def dots(pts, cls):
    return "".join(f'<circle cx="{x}" cy="{y}" r="2.6" class="{cls}"/>' for x, y in pts)


# ---- chart axes -----------------------------------------------------------
for key in ("map", "kp", "kd", "fb", "r24"):
    a = C[key]["ax"]
    x0, y0, w, h = float(a[0]), float(a[1]), float(a[2]), float(a[3])
    P[f"{key}.xaxis"] = gridx(C[key]["xt"], y0, h)
    P[f"{key}.yaxis"] = gridy(C[key]["yt"], x0, w)
for key in ("taper", "speedtaper"):
    a = C[key]["ax"]
    x0, y0, w, h = float(a[0]), float(a[1]), float(a[2]), float(a[3])
    P[f"{key}.xaxis"] = gridx(C[key]["xt"], y0, h)
    P[f"{key}.yaxis"] = gridy(C[key]["yt"], x0, w)
a = C["surface"]["ax"]
sx0, sy0, sw, sh = float(a[0]), float(a[1]), float(a[2]), float(a[3])
P["surface.xaxis"] = gridx(C["surface"]["xt"], sy0, sh)
P["surface.yaxis"] = gridy(C["surface"]["yt"], sx0, sw)

P["map.rate_axis"] = rgridy(C["map"]["rate_yt"], 56, 372)
P["map.v282_knots"] = dots(C["map"]["v282_knots"], "kn v293")
P["map.stock_knots"] = dots(C["map"]["stock_knots"], "kn stock")
P["kp.stock_knots"] = dots(C["kp"]["stock_knots"], "kn stock")
P["taper.knots"] = dots(C["taper"]["knots"], "kn v282")
P["speedtaper.Cknots"] = dots(C["speedtaper"]["Cknots"], "kn stock")
P["speedtaper.Dknots"] = dots(C["speedtaper"]["Dknots"], "kn v282")

# knot rules on the Kp / Kd panels
P["kp.knotrules"] = "".join(
    f'<line x1="{x}" y1="20" x2="{x}" y2="206" class="knr"/>'
    f'<text x="{x}" y="16" class="tk sm" text-anchor="middle">{l}</text>'
    for x, l in zip(C["kp"]["knotx"], C["kp"]["knotlbl"]))
P["kd.knotrules"] = "".join(
    f'<line x1="{x}" y1="20" x2="{x}" y2="206" class="knr"/>'
    f'<text x="{x}" y="16" class="tk sm" text-anchor="middle">{l}</text>'
    for x, l in zip(C["kd"]["knotx"], C["kd"]["knotlbl"]))

for k, v in C.items():
    if isinstance(v, dict):
        for kk, vv in v.items():
            if isinstance(vv, (str, int, float)):
                P.setdefault(f"{k}.{kk}", str(vv))

# ---- the delivered-surface table ------------------------------------------
RATE = 32 / (30.8911 * 8)
rows = []
for idx, t in sorted(C["surface"]["tbl"].items(), key=lambda kv: int(kv[0])):
    ref = M["V282"]["map"][1]
    sp = None
    mX, mY = M["V282"]["map"]
    i = int(idx)
    if i <= mX[0]:
        sp = mY[0]
    elif i >= mX[-1]:
        sp = mY[-1]
    else:
        for j in range(len(mX) - 1):
            if mX[j] <= i <= mX[j + 1]:
                sp = mY[j] + (mY[j + 1] - mY[j]) * (i - mX[j]) // (mX[j + 1] - mX[j])
                break
    rows.append(
        f'<tr><td class="n">{idx}</td><td class="n">{sp}</td><td class="n">{sp * RATE:.1f}</td>'
        f'<td class="n">{round(i * 16.125736):,}</td>'
        f'<td class="n v293b">{t["v293"]:,}</td><td class="n">{t["v282_0"]:,}</td>'
        f'<td class="n">{t["v282_10"]:,}</td><td class="n">{t["v282_20"]:,}</td>'
        f'<td class="n">{t["v282_45"]:,}</td></tr>')
P["surface.rows"] = "".join(rows)

# ---- the cross-build matrix -----------------------------------------------
ORDER = ["STOCK", "V38", "V62", "V67", "V84", "V88", "V102", "V104", "V112", "V247", "V268",
         "V270", "V273", "V276", "V278#1", "V279#1", "V280#1", "V281#2", "V282", "V283",
         "V285", "V287#1", "V288#1", "V289", "V291", "V292"]
LBL = {"V278#1": "V278r3", "V279#1": "V279", "V280#1": "V280r2", "V281#2": "V281r3",
       "V287#1": "V287r2", "V288#1": "V288r2"}
NOTE = {
    "STOCK": "Honda", "V38": "the rebase", "V62": "rate lane; gain x4",
    "V67": "Lever B gate armed", "V84": "Lever B arm 5244", "V88": "grinding reported fixed",
    "V102": "gain x6 chosen", "V104": "rate-lane gate live", "V112": "long-frozen base",
    "V247": "damper dead zone", "V268": "damper flattened",
    "V270": "Ki probe", "V273": "map linearised x2.79", "V276": "map x6 + fb 46080; rang",
    "V278#1": "map x2; 3.9 Hz gone", "V279#1": "TORQUE MODE, never flown",
    "V280#1": "map x6 linear", "V281#2": "Kp flattened to Y[0]", "V282": "+ r24 comparator cave",
    "V283": "Ki 50, rejected", "V285": "Kp 0, bench only", "V287#1": "D clamp 7680, rejected",
    "V288#1": "setpoint pre-filter", "V289": "sum notch + fb pole 25 Hz",
    "V291": "fb pole 9.94 Hz", "V292": "+ error-feedback cave; FLEW, revert",
}
have = [k for k in ORDER if k in M]
if "V293" in M:
    have.append("V293")
    NOTE["V293"] = "TORQUE MODE on V282"
elif "V293_PROVISIONAL" in M:
    have.append("V293_PROVISIONAL")
    LBL["V293_PROVISIONAL"] = "V293"
    NOTE["V293_PROVISIONAL"] = "TORQUE MODE on V282"

MROWS = [
    ("0xC62E6", "fb saturation clamp", lambda d: f'{d["0xC62E6"]:,}'),
    ("0xCB7D4", "Kd, live slot 7", lambda d: str(d["kd"][1][0])),
    ("0xC61B6", "D clamp", lambda d: f'{d["0xC61B6"]:,}'),
    ("0xCB994", "Kp, live slot 7", lambda d: (str(d["kp"][1][0]) if len(set(d["kp"][1])) == 1
                                              else f'{d["kp"][1][0]}&#8211;{d["kp"][1][-1]}')),
    ("0xC6446", "r24 engaged arm", lambda d: f'{d["0xC6446"]:,}'),
    ("0xC9A88", "assist map top", lambda d: f'{d["map"][1][-1]:,}'),
    ("0xC6CD0", "forward LKAS gain", lambda d: f'{d["0xC6CD0"]:,}'),
    ("0xC63E8", "fb lag pole a / b", lambda d: f'{d["0xC63E8"]}/{d["0xC63EA"]}'),
    ("0xC63E6", "Ki", lambda d: str(d["0xC63E6"])),
]
head = "".join(f'<th class="n">{LBL.get(k, k)}</th>' for k in have)
body = []
for addr, lab, fn in MROWS:
    cells = []
    prev = None
    for k in have:
        v = fn(M[k])
        cls = "n"
        if v != prev and prev is not None:
            cls += " chg"
        if k in ("V293", "V293_PROVISIONAL"):
            cls += " v293b"
        cells.append(f'<td class="{cls}">{v}</td>')
        prev = v
    body.append(f'<tr><td class="m">{addr}</td><td>{lab}</td>{"".join(cells)}</tr>')
P["matrix.head"] = head
P["matrix.body"] = "".join(body)
P["matrix.notes"] = "".join(
    f'<tr><td class="m">{LBL.get(k, k)}</td><td>{NOTE.get(k, "")}</td>'
    f'<td class="m sha">{IMG.get(k, IMG.get("V282"))["sha256"][:12] if k in IMG else "—"}</td></tr>'
    for k in have)

# ---- identity strip --------------------------------------------------------
if "V293" in IMG:
    P["v293.file"] = IMG["V293"]["file"]
    P["v293.sha"] = IMG["V293"]["sha256"]
    P["prov.state"] = "built"
else:
    P["v293.file"] = "not yet written to disk"
    P["v293.sha"] = "pending — the image had not been written when this page was rendered"
    P["prov.state"] = "provisional"
P["v293.rwd"] = (D["rwd"][0]["sha256"] if D.get("rwd") else "no .rwd on disk")
P["v293.nrwd"] = str(len(D.get("rwd", [])))
DF = D.get("diff")
if DF:
    at = DF["attribution"]
    P["diff.n"] = f'{DF["n_bytes"]:,}'
    P["diff.clusters"] = str(DF["n_clusters"])
    P["diff.low"] = str(DF["n_below_0x13000"])
    P["diff.cell"] = str(at["cell"])
    P["diff.kpY"] = str(at["kpY"])
    P["diff.kdY"] = str(at["kdY"])
    P["diff.crc"] = str(at["crc"])
    P["diff.orphan"] = str(at["ORPHAN"])
    P["diff.trailers"] = " &#183; ".join(DF["crc_trailers"])
    P["diff.sem"] = ("PASS &#8212; the Kp LERP reads 120 and the Kd LERP reads 0 at every demand "
                     "index on all 28 slots" if not DF["semantic_fail"]
                     else f'FAIL on slots {DF["semantic_fail"]}')
else:
    for k in ("n", "clusters", "low", "cell", "kpY", "kdY", "crc", "orphan"):
        P[f"diff.{k}"] = "—"
    P["diff.trailers"] = "—"
    P["diff.sem"] = "not run — no built image"
P["v282.sha"] = IMG["V282"]["sha256"]
P["stock.sha"] = IMG["STOCK"]["sha256"][:16]

PROV_BANNER = (
    '<div class="verdict"><p class="vlbl">Numbers not yet from the built image</p>'
    '<p class="vtxt">The V293 image was <b>not on disk</b> when this page was rendered, so every '
    'V293 number below is computed by applying the four pre-registered cal edits '
    '<b>in memory to the V282 image’s own cells</b> and running the same byte-exact integer '
    'chain. It reproduces the build script’s published surface table to the count, but it is '
    '<b>not a read of the built bytes</b> and must not be treated as one. This block disappears '
    'when the page is re-rendered against the image.</p></div>')
P["prov.banner"] = "" if "V293" in IMG else PROV_BANNER

tpl = (HERE / "page.tmpl.html").read_text(encoding="utf-8")
out = tpl
for k, v in sorted(P.items(), key=lambda kv: -len(kv[0])):
    out = out.replace("{{" + k + "}}", str(v))
left = [s for s in out.split("{{")[1:]]
if left:
    print("!! UNSUBSTITUTED:", sorted({s.split("}}")[0] for s in left}))
(HERE / "v293-torque-mode.html").write_text(out, encoding="utf-8")
print(f"rendered {len(out):,} bytes -> v293-torque-mode.html   (state: {P['prov.state']})")
