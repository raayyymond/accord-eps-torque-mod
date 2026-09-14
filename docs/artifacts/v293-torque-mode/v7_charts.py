# -*- coding: utf-8 -*-
"""Version-7 chart geometry for the V293 close-out page (the FLIGHT sections).

Every number here is transcribed from a measurement file, never from a build script:
  rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt   (the scorecard)
  rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md        (sections B, E, F, H, I, J)
  docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md             (section 4)
Emits v7_sections.frag — inline SVG figures, no runtime JS, no library.
"""
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------- helpers
def poly(xs, ys, cls):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return f'<polyline points="{pts}" class="{cls}"/>'


def txt(x, y, s, cls="tk", anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{extra}>{s}</text>'


def hgrid(x0, x1, vals, sy, fmt="{:g}", cls="gl"):
    o = []
    for v in vals:
        y = sy(v)
        o.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="{cls}"/>')
        o.append(txt(x0 - 7, y + 4, fmt.format(v), "tk", "end"))
    return "".join(o)


def bar(x, y, w, h, fill, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{extra}/>'


def interp(v, bp, vv):
    return float(np.interp(v, bp, vv))


# =========================================================================== FIG 1
# The measured plant hold, against the fork's OLD and NEW tables. The LERP, before
# and after, on the same axes.  V293-PLANT-IDENT sections F1 / F2 / I2.
K_BP = [4.0, 8.0, 12.5, 18.5, 28.5]
G_BP = [5.0, 12.5, 18.5, 28.5]
K_OLD = [0.17, 0.28, 0.35, 0.45, 0.50]
G_OLD = [120, 95, 85, 70]
# FINAL rev-2 tables. The two low-speed knots are NOT the joint fit's — the adversarial pass
# (ADV-REV2-FORK-PACKAGE) bounded the hold below 8 m/s from route 70's own hands-off frames
# (251 deg held at |u| <= 0.163, which with Coulomb 0.012 gives <= 0.0007 torque/deg) and the
# fit's 0.93 / 1.64 knots sat 2.4x above that bound.
K_NEW = [0.30, 1.00, 2.15, 2.77, 3.15]
G_NEW = [550, 271, 246, 205]
BOUNDED_ABOVE = 8.0  # below this the new curve is bounded by measurement, not fitted to it
MEAS = [  # v, a (torque per degree), CI lo, CI hi
    (4.93, 0.00228, 0.00089, 0.00657),
    (11.96, 0.00764, 0.00617, 0.01063),
    (18.94, 0.01149, 0.01007, 0.01329),
    (22.80, 0.01539, 0.01475, 0.01809),
]


def fig1():
    W, H = 640, 330
    x0, x1, y0, y1 = 64, 596, 26, 258
    vmin, vmax, amax = 0.0, 30.0, 0.019
    sx = lambda v: x0 + (v - vmin) / (vmax - vmin) * (x1 - x0)
    sy = lambda a: y1 - a / amax * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chartw" aria-label="Steady hold '
         'torque per degree of steering angle against speed. The measured plant rises from '
         '0.0023 at 4.9 metres per second to 0.0154 at 22.8. The fork\'s old table runs '
         'from 0.0017 to 0.0071, roughly half. The new table lands on the measurement.">']
    o.append(f'<rect x="{sx(0):.1f}" y="{y0}" width="{sx(BOUNDED_ABOVE)-sx(0):.1f}" '
             f'height="{y1-y0}" fill="var(--plantsoft)"/>')
    o.append(hgrid(x0, x1, [0, 0.004, 0.008, 0.012, 0.016], sy, "{:.3f}"))
    for v in [0, 5, 10, 15, 20, 25, 30]:
        o.append(f'<line x1="{sx(v):.1f}" y1="{y0}" x2="{sx(v):.1f}" y2="{y1}" class="gl"/>')
        o.append(txt(sx(v), y1 + 17, f"{v}", "tk", "middle"))
    # the true LERP of both tables (k(v)/G(v), each interpolated separately)
    vs = np.linspace(1.0, 30.0, 240)
    old = [interp(v, K_BP, K_OLD) / interp(v, G_BP, G_OLD) for v in vs]
    new = [interp(v, K_BP, K_NEW) / interp(v, G_BP, G_NEW) for v in vs]
    o.append(poly([sx(v) for v in vs], [sy(a) for a in old], "ln a282 dash"))
    # the rev-2 curve is drawn dotted where its knots are BOUNDED by route 70 rather than fitted
    lo_v = [v for v in vs if v <= BOUNDED_ABOVE]
    hi_v = [v for v in vs if v >= BOUNDED_ABOVE]
    o.append(poly([sx(v) for v in lo_v],
                  [sy(interp(v, K_BP, K_NEW) / interp(v, G_BP, G_NEW)) for v in lo_v],
                  "ln a293 dot"))
    o.append(poly([sx(v) for v in hi_v],
                  [sy(interp(v, K_BP, K_NEW) / interp(v, G_BP, G_NEW)) for v in hi_v],
                  "ln a293"))
    # knots
    for v in G_BP:
        a = interp(v, K_BP, K_OLD) / interp(v, G_BP, G_OLD)
        o.append(f'<circle cx="{sx(v):.1f}" cy="{sy(a):.1f}" r="3.1" class="kn v282"/>')
        a = interp(v, K_BP, K_NEW) / interp(v, G_BP, G_NEW)
        o.append(f'<circle cx="{sx(v):.1f}" cy="{sy(a):.1f}" r="3.1" class="kn v293"/>')
    # measurement with its confidence interval
    for v, a, lo, hi in MEAS:
        X = sx(v)
        o.append(f'<line x1="{X:.1f}" y1="{sy(lo):.1f}" x2="{X:.1f}" y2="{sy(hi):.1f}" '
                 f'stroke="var(--plant)" stroke-width="1.6"/>')
        for e in (lo, hi):
            o.append(f'<line x1="{X-4:.1f}" y1="{sy(e):.1f}" x2="{X+4:.1f}" y2="{sy(e):.1f}" '
                     f'stroke="var(--plant)" stroke-width="1.6"/>')
        o.append(f'<circle cx="{X:.1f}" cy="{sy(a):.1f}" r="4.4" fill="var(--plant)"/>')
    o.append(txt(sx(17.6), sy(0.0182), "measured plant &#183; joint fit, 95&#160;% CI",
                 "dlbl", "end", ' fill="var(--plant)"'))
    o.append(txt(sx(29.6), sy(0.0143), "new tables", "dlbl", "end", ' fill="var(--v293)"'))
    o.append(txt(sx(29.6), sy(0.0082), "fork tables as flown", "dlbl", "end",
                 ' fill="var(--v282)"'))
    o.append(txt(sx(4.93), sy(0.00657) - 9, "not identified below 8&#8201;m/s", "tk", "middle"))
    o.append(txt(sx(7.7), y0 + 12, "rev-2 knots here are BOUNDED", "tk sm", "end"))
    o.append(txt(sx(7.7), y0 + 24, "by route 70, not fitted", "tk sm", "end"))
    o.append(txt((x0 + x1) / 2, H - 8, "vehicle speed, m/s", "tk", "middle"))
    o.append(txt(6, 14, "steady hold torque per degree (openpilot torque units)", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 2
# Feedforward hold ratio per band: torque commanded per degree / torque needed.
BANDS4 = ["1&#8211;8 m/s", "8&#8211;15", "15&#8211;22", "&gt;22"]
FFR = [  # label, colour var, values
    ("lat-accel FF &#183; as flown", "var(--v282)", [0.650, 1.140, 1.901, 2.057]),
    ("old tables &#215;3.3", "var(--stock)", [3.20, 1.52, 1.54, 1.29]),
    ("old tables &#215;2.15", "var(--v292)", [2.09, 0.99, 1.00, 0.84]),
    ("new tables &#183; rev 2", "var(--v293)", [1.19, 0.94, 0.99, 0.84]),
]


def fig2():
    W, H = 640, 310
    x0, x1, y0, y1 = 62, 606, 24, 242
    ymax = 3.4
    sy = lambda v: y1 - v / ymax * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chartw" aria-label="Feedforward hold '
         'ratio by speed band for four configurations. The flown lateral-acceleration '
         'feedforward reaches 1.90 and 2.06 above 15 metres per second; the new tables sit '
         'between 0.84 and 1.19 in every band.">']
    o.append(hgrid(x0, x1, [0, 1, 2, 3], sy, "{:.0f}"))
    gw = (x1 - x0) / 4
    bw = gw * 0.175
    for gi, bnd in enumerate(BANDS4):
        gx = x0 + gi * gw
        for si, (lab, col, vals) in enumerate(FFR):
            v = vals[gi]
            bx = gx + gw * 0.10 + si * bw
            o.append(bar(bx, sy(v), bw - 3.0, y1 - sy(v), col))
            dy = -5 if si % 2 == 0 else -16
            o.append(txt(bx + (bw - 3) / 2, sy(v) + dy, f"{v:.2f}", "tk sm", "middle"))
        o.append(txt(gx + gw / 2, y1 + 18, bnd, "tk", "middle"))
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y1}" class="gl"/>')
    o.append(f'<line x1="{x0}" y1="{sy(1):.1f}" x2="{x1}" y2="{sy(1):.1f}" '
             'stroke="var(--ok)" stroke-width="1.6" stroke-dasharray="6 4"/>')
    o.append(txt(x1 - 2, y0 + 10, "dashed line 1.00 &#8212; the torque the plant needs",
                 "dlbl", "end", ' fill="var(--ok)"'))
    o.append(txt((x0 + x1) / 2, H - 8, "speed band", "tk", "middle"))
    o.append(txt(6, 14, "torque commanded per degree &#247; torque needed", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 3a
# Dwells per minute at the 0.25 deg/s threshold, log scale.
DW_BANDS = ["0&#8211;5 m/s", "5&#8211;10", "10&#8211;20", "&gt;20"]
DW = [
    ("r70 V293 &#183; hands-off", "var(--v293)", [20.97, 8.08, 5.26, 1.27]),
    ("r70 V293 &#183; all engaged", "var(--v293)", [15.23, 7.66, 4.56, 1.24]),
    ("r6c V282 &#183; all engaged", "var(--v282)", [0.39, 0.64, 0.44, 0.20]),
]


def fig3a():
    W, H = 400, 300
    x0, x1, y0, y1 = 58, 372, 24, 232
    lo, hi = 0.1, 40.0
    sy = lambda v: y1 - (np.log10(v) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Dwells per minute '
         'at the quarter-degree-per-second threshold, log scale. Route 70 reads 15 to 21 per '
         'minute below 5 metres per second against r6c\'s 0.39.">']
    for v in [0.1, 0.3, 1, 3, 10, 30]:
        y = sy(v)
        o.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="gl"/>')
        o.append(txt(x0 - 7, y + 4, f"{v:g}", "tk", "end"))
    gw = (x1 - x0) / 4
    bw = gw * 0.22
    for gi, bnd in enumerate(DW_BANDS):
        gx = x0 + gi * gw
        for si, (lab, col, vals) in enumerate(DW):
            v = vals[gi]
            bx = gx + gw * 0.10 + si * bw
            op = ' opacity="0.55"' if si == 1 else ""
            o.append(bar(bx, sy(v), bw - 2.6, y1 - sy(v), col, op))
            dy = -16 if si == 0 else -5
            o.append(txt(bx + (bw - 2.6) / 2, sy(v) + dy, f"{v:.2f}".rstrip("0").rstrip("."),
                         "tk sm", "middle"))
        o.append(txt(gx + gw / 2, y1 + 17, bnd, "tk", "middle"))
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y1}" class="gl"/>')
    o.append(txt((x0 + x1) / 2, H - 8, "speed band", "tk", "middle"))
    o.append(txt(6, 14, "dwells per minute, threshold 0.25 deg/s", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 3b
# Rate-magnitude concentration by activity bin.
CB = ["q0&#8211;25", "q25&#8211;50", "q50&#8211;75", "q75&#8211;90", "q90+"]
CONC = [
    ("r70 V293", "var(--v293)", [0.371, 0.438, 0.454, 0.468, 0.361]),
    ("r6c V282", "var(--v282)", [0.354, 0.378, 0.375, 0.345, 0.289]),
    ("r39 V282", "var(--v292)", [None, 0.376, 0.357, 0.325, 0.287]),
    ("r35 V281r3", "var(--stock)", [0.360, 0.382, 0.368, 0.351, 0.277]),
]


def fig3b():
    W, H = 400, 300
    x0, x1, y0, y1 = 58, 372, 24, 232
    ymin, ymax = 0.14, 0.50
    sy = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
    sx = lambda i: x0 + 22 + i * ((x1 - x0 - 40) / 4)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Fraction of wheel '
         'travel delivered in the fastest tenth of frames, by steering-activity bin. Route 70 '
         'is above all three reference routes in every bin and the gap widens with activity.">']
    o.append(hgrid(x0, x1, [0.2, 0.3, 0.4, 0.5], sy, "{:.1f}"))
    for lo, lab in ((0.157, "pure 1&#8201;Hz sine"), (0.278, "band-limited noise")):
        o.append(f'<line x1="{x0}" y1="{sy(lo):.1f}" x2="{x1}" y2="{sy(lo):.1f}" class="knr"/>')
        o.append(txt(x1 - 3, sy(lo) - 5, lab, "tk sm", "end"))
    for lab, col, vals in CONC:
        xs = [sx(i) for i, v in enumerate(vals) if v is not None]
        ys = [sy(v) for v in vals if v is not None]
        cls = "ln a293" if "V293" in lab else "ln thin"
        style = "" if "V293" in lab else f' stroke="{col}" opacity="0.85"'
        o.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in zip(xs, ys))}" '
                 f'class="{cls}"{style}/>')
        for a, b in zip(xs, ys):
            o.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="2.8" fill="{col}"/>')
    o.append(txt(sx(4) - 4, sy(0.361) - 11, "r70 V293", "dlbl", "end", ' fill="var(--v293)"'))
    for i, c in enumerate(CB):
        o.append(txt(sx(i), y1 + 17, c, "tk sm", "middle"))
    o.append(txt((x0 + x1) / 2, H - 8, "window bin by its own rms wheel rate", "tk", "middle"))
    o.append(txt(6, 14, "share of travel in the fastest 10&#160;% of frames", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 4
# The measured LAF on the speed x amplitude grid, against the flat 6.0 assumed.
LAFG = [
    ("small demand", "var(--v292)", [1.28, None, None, 3.40]),
    ("mid demand", "var(--plant)", [None, 3.19, 4.17, 6.00]),
    ("large demand", "var(--stock)", [None, 5.21, 6.19, 9.43]),
]


def fig4():
    W, H = 640, 320
    x0, x1, y0, y1 = 64, 596, 24, 244
    ymax = 10.0
    sy = lambda v: y1 - v / ymax * (y1 - y0)
    sx = lambda i: x0 + 62 + i * ((x1 - x0 - 110) / 3)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chartw" aria-label="Measured lateral '
         'acceleration per unit torque on a speed by demand-amplitude grid, against the flat '
         '6.0 the controller assumed. It runs from 1.28 to 9.43, a factor of seven.">']
    o.append(hgrid(x0, x1, [0, 2, 4, 6, 8, 10], sy, "{:.0f}"))
    o.append(f'<line x1="{x0}" y1="{sy(6):.1f}" x2="{x1}" y2="{sy(6):.1f}" '
             'stroke="var(--risk)" stroke-width="2" stroke-dasharray="7 4"/>')
    o.append(txt(x0 + 6, sy(6) - 8, "SteerLatAccel 6.0 &#8212; one number for all of it",
                 "dlbl", "start", ' fill="var(--risk)"'))
    for lab, col, vals in LAFG:
        pts = [(sx(i), sy(v)) for i, v in enumerate(vals) if v is not None]
        if len(pts) > 1:
            o.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" '
                     f'class="ln thin" stroke="{col}"/>')
        for i, v in enumerate(vals):
            if v is None:
                continue
            o.append(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="5" fill="{col}"/>')
            o.append(txt(sx(i), sy(v) - 11, f"{v:.2f}", "tk", "middle"))
    o.append(txt(sx(3) + 16, sy(9.43) + 4, "large", "dlbl", "start", ' fill="var(--stock)"'))
    o.append(txt(sx(3) + 16, sy(6.00) + 16, "mid", "dlbl", "start", ' fill="var(--plant)"'))
    o.append(txt(sx(3) + 16, sy(3.40) + 4, "small", "dlbl", "start", ' fill="var(--v292)"'))
    for i, c in enumerate(["&lt;8 m/s", "8&#8211;15", "15&#8211;22", "&gt;22"]):
        o.append(txt(sx(i), y1 + 18, c, "tk", "middle"))
    o.append(txt((x0 + x1) / 2, H - 8,
                 "speed band &#183; series = rms amplitude of the 0.15&#8211;1&#8201;Hz demand",
                 "tk", "middle"))
    o.append(txt(6, 14, "lateral acceleration per unit torque (m/s&#178; per unit)", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 5a
# Sensitivity peak Ms at 4.5 m/s, per candidate config.
MSC = [
    ("C0 as flown", 12.31, "&#8722;10.8&#176;", "var(--risk)"),
    ("C9 LAF 6, Kp bound", 12.96, "&#8722;10.4&#176;", "var(--ink-mut)"),
    ("C7 LAF 6, low Ki", 10.31, "&#8722;13.2&#176;", "var(--ink-mut)"),
    ("C5 LAF 6", 8.77, "&#8722;15.1&#176;", "var(--ink-mut)"),
    ("C3 hotter", 4.23, "31.5&#176;", "var(--v282)"),
    ("C4 stiffer", 2.57, "54.1&#176;", "var(--v292)"),
    ("C1&#8242; / C2", 2.45, "57.6&#176;", "var(--v292)"),
    ("C10 &#183; rev 2", 2.50, "57.7&#176;", "var(--v293)"),
]


def fig5a():
    W, H = 400, 300
    x0, x1, y0 = 128, 256, 30
    rowh = 27
    xmax = 13.5
    sx = lambda v: x0 + v / xmax * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Sensitivity peak at '
         '4.5 metres per second for every candidate config. As flown reads 12.31 with negative '
         'phase margin; the rev-2 config reads 2.50 with 57.7 degrees.">']
    for v in [0, 4, 8, 12]:
        o.append(f'<line x1="{sx(v):.1f}" y1="{y0 - 6}" x2="{sx(v):.1f}" '
                 f'y2="{y0 + rowh * len(MSC) - 8}" class="gl"/>')
        o.append(txt(sx(v), y0 + rowh * len(MSC) + 7, f"{v}", "tk sm", "middle"))
    for i, (lab, ms, pm, col) in enumerate(MSC):
        y = y0 + i * rowh
        o.append(txt(x0 - 8, y + 9, lab, "tk", "end"))
        dim = ' opacity="0.42"' if "ink-mut" in col else ""
        o.append(bar(sx(0), y, sx(ms) - sx(0), 13, col, dim))
        o.append(txt(sx(ms) + 5, y + 10, f"{ms:.2f} &#183; PM {pm}", "tk sm"))
    o.append(f'<line x1="{sx(2):.1f}" y1="{y0 - 10}" x2="{sx(2):.1f}" '
             f'y2="{y0 + rowh * len(MSC) - 8}" stroke="var(--ok)" stroke-width="1.6" '
             'stroke-dasharray="5 4"/>')
    o.append(txt(sx(2) + 3, y0 - 13, "M&#8347; &#8804; 2 bound", "tk sm", "start",
                 ' fill="var(--ok)"'))
    o.append(txt((x0 + x1) / 2, H - 8,
                 "sensitivity peak M&#8347; at 4.5&#8201;m/s (lower is calmer)", "tk", "middle"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 5b
# Simulated 1 m/s^2 step overshoot, two bands.
OVS = [
    ("C0 as flown", "var(--risk)", [1.41, 1.56]),
    ("C1 &#215;3.3", "var(--stock)", [0.91, 0.67]),
    ("C4 stiffer", "var(--v292)", [0.48, 0.36]),
    ("C10 &#183; rev 2", "var(--v293)", [0.43, 0.32]),
]


def fig5b():
    W, H = 400, 300
    x0, x1, y0, y1 = 58, 372, 30, 232
    ymax = 1.7
    sy = lambda v: y1 - v / ymax * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Simulated overshoot '
         'to a one metre per second squared step. As flown overshoots 1.41 and 1.56; the rev-2 '
         'config 0.43 and 0.32.">']
    o.append(hgrid(x0, x1, [0, 0.5, 1.0, 1.5], sy, "{:.1f}"))
    gw = (x1 - x0) / 2
    bw = gw * 0.19
    for gi, bnd in enumerate(["15&#8211;22 m/s", "&gt;22 m/s"]):
        gx = x0 + gi * gw
        for si, (lab, col, vals) in enumerate(OVS):
            v = vals[gi]
            bx = gx + gw * 0.10 + si * bw
            o.append(bar(bx, sy(v), bw - 3, y1 - sy(v), col))
            o.append(txt(bx + (bw - 3) / 2, sy(v) - 5, f"{v:.2f}", "tk sm", "middle"))
        o.append(txt(gx + gw / 2, y1 + 17, bnd, "tk", "middle"))
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y1}" class="gl"/>')
    o.append(txt((x0 + x1) / 2, H - 8, "simulated response to a 1&#8201;m/s&#178; step",
                 "tk", "middle"))
    o.append(txt(6, 16, "peak overshoot, m/s&#178;", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 6a
# 1-4 Hz prominence per speed band.
PROM = [
    ("r70 V293", "var(--v293)", [6.51, 11.78, 7.65, 3.08]),
    ("r6c V282", "var(--v282)", [2.19, -2.32, -0.75, -0.36]),
    ("r39 V282", "var(--v292)", [1.08, -0.27, 1.69, 2.21]),
    ("r35 V281r3", "var(--stock)", [1.91, 0.61, 0.81, 1.15]),
]


def fig6a():
    """Route 70 against the ENVELOPE of the three reference routes — four overlapping bar
    series in 78 units of width collided, and the envelope is the readable form of the
    same claim."""
    W, H = 400, 300
    x0, x1, y0, y1 = 58, 372, 38, 232
    ymin, ymax = -3.0, 12.5
    sy = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Prominence of the '
         '1 to 4 hertz peak by speed band. Route 70 reads 3.1 to 11.8 decibels; the three '
         'reference routes span minus 2.3 to 2.2 in every band.">']
    o.append(hgrid(x0, x1, [0, 4, 8, 12], sy, "{:.0f}"))
    o.append(f'<line x1="{x0}" y1="{sy(0):.1f}" x2="{x1}" y2="{sy(0):.1f}" class="zl"/>')
    gw = (x1 - x0) / 4
    refs = list(zip(*[v for _, _, v in PROM[1:]]))
    for gi, bnd in enumerate(["0&#8211;5", "5&#8211;10", "10&#8211;20", "&gt;20"]):
        gx = x0 + gi * gw
        lo, hi = min(refs[gi]), max(refs[gi])
        o.append(bar(gx + gw * 0.52, sy(hi), gw * 0.36, sy(lo) - sy(hi), "var(--v282)",
                     ' opacity="0.35"'))
        o.append(txt(gx + gw * 0.70, sy(lo) + 12, f"{lo:.1f}", "tk sm", "middle"))
        o.append(txt(gx + gw * 0.70, sy(hi) - 5, f"{hi:.1f}", "tk sm", "middle"))
        v = PROM[0][2][gi]
        o.append(bar(gx + gw * 0.14, sy(v), gw * 0.30, sy(0) - sy(v), "var(--v293)"))
        o.append(txt(gx + gw * 0.29, sy(v) - 5, f"{v:.1f}", "tk", "middle"))
        o.append(txt(gx + gw / 2, y1 + 17, bnd, "tk", "middle"))
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y1}" class="gl"/>')
    o.append(f'<line x1="{x0}" y1="{sy(3):.1f}" x2="{x1}" y2="{sy(3):.1f}" '
             'stroke="var(--ok)" stroke-width="1.5" stroke-dasharray="5 4"/>')
    o.append(txt(x1, y0 - 8, "3&#8201;dB &#8212; the rev-2 falsifier", "tk sm", "end",
                 ' fill="var(--ok)"'))
    o.append(txt((x0 + x1) / 2, H - 8, "speed band, m/s", "tk", "middle"))
    o.append(txt(6, 14, "1&#8211;4&#8201;Hz prominence above the shoulders, dB", "tk"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 6b
# 18-22 Hz present-window share.
PRES = [
    ("r70 V293", 1.1, 1.142, "var(--v293)"),
    ("r6c V282", 9.8, 2.630, "var(--v282)"),
    ("r35 V281r3", 16.2, 3.487, "var(--stock)"),
    ("r6d V292", 18.1, 3.638, "var(--v292)"),
    ("r6e V292", 18.7, 2.820, "var(--v292)"),
    ("r6f V292", 20.5, 3.277, "var(--v292)"),
    ("r39 V282", 20.9, 2.766, "var(--v282)"),
]


def fig6b():
    W, H = 400, 300
    x0, x1, y0 = 104, 286, 30
    rowh = 27
    xmax = 22.0
    sx = lambda v: x0 + v / xmax * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart" aria-label="Share of two-second '
         'windows carrying an 18 to 22 hertz ring. Route 70 reads 1.1 per cent against 9.8 to '
         '20.9 per cent on every reference route.">']
    for v in [0, 5, 10, 15, 20]:
        o.append(f'<line x1="{sx(v):.1f}" y1="{y0 - 6}" x2="{sx(v):.1f}" '
                 f'y2="{y0 + rowh * len(PRES) - 8}" class="gl"/>')
        o.append(txt(sx(v), y0 + rowh * len(PRES) + 7, f"{v}", "tk sm", "middle"))
    for i, (lab, pct, amp, col) in enumerate(PRES):
        y = y0 + i * rowh
        o.append(txt(x0 - 8, y + 9, lab, "tk", "end"))
        o.append(bar(sx(0), y, max(sx(pct) - sx(0), 1.5), 13, col))
        o.append(txt(min(sx(pct) + 5, x1 - 4), y + 10,
                     f"{pct:.1f}&#160;% &#183; amp {amp:.2f}", "tk sm"))
    o.append(txt((x0 + x1) / 2, H - 8,
                 "share of engaged windows with the ring present, %", "tk", "middle"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== FIG 7
# The rev-2 fork signal flow: plant-FF branch ON, into the open-loop torque map,
# into the spring plant.
def fig7():
    W, H = 1180, 540
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" class="flow2" aria-label="Signal flow of the '
         'rev-2 fork configuration: the model\'s curvature becomes a lateral-acceleration '
         'setpoint, the error drives P and I which are divided by SteerLatAccel, the plant '
         'feedforward adds a spring hold and a move term from the new tables, friction adds a '
         'sign term, and the sum becomes the 0xE4 command into the open-loop V293 torque map '
         'and the spring plant.">']

    def box(x, y, w, h, title, subs=(), cls="n2", extra=""):
        """subs: tuple of mono sub-lines, laid out under the title at a 16-unit rhythm.
        An empty tuple centres the title; a non-empty one pins it to y+18."""
        r = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" class="{cls}"{extra}/>']
        if isinstance(subs, str):
            subs = (subs,) if subs else ()
        r.append(txt(x + w / 2, y + (18 if subs else h / 2 + 4), title, "bt", "middle"))
        for i, s in enumerate(subs):
            r.append(txt(x + w / 2, y + 36 + i * 16, s, "bs", "middle"))
        return "".join(r)

    def arrow(pts, lab=None, at=None, cls="fl"):
        """pts: [(x,y), ...] — one path, one arrowhead at the end, no head at a bend."""
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        r = [f'<path d="{d}" class="{cls}" marker-end="url(#ah2)"/>']
        if lab:
            lx, ly = at if at else ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2 - 6)
            r.append(txt(lx, ly, lab, "tk sm", "middle"))
        return "".join(r)

    o.append('<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
             'markerHeight="6" orient="auto-start-reverse">'
             '<path d="M 0 0 L 10 5 L 0 10 z" fill="var(--flow)"/></marker></defs>')

    # band labels
    for by, lab in ((14, "OPENPILOT &#8212; THE FORK, REV 2 &#183; shaded blocks are what changes"),
                    (366, "THE CAR &#8212; UNCHANGED FIRMWARE, AND THE PLANT ROUTE 70 IDENTIFIED")):
        o.append(f'<rect x="14" y="{by}" width="{W-28}" height="19" class="bandbar"/>')
        o.append(txt(24, by + 14, lab, "bl"))

    # --- reference path
    o.append(box(20, 54, 120, 46, "modeld", ("20&#8201;Hz desiredCurvature",)))
    o.append(arrow([(140, 77), (180, 77)]))
    o.append(box(180, 54, 150, 46, "&#215;v&#178; &#183; lookahead",
                 ("setpoint, LPF 1.2&#8201;Hz",)))
    o.append(arrow([(330, 77), (372, 77)]))
    o.append(box(372, 54, 76, 46, "&#931;", (), "n2 op"))
    o.append(txt(446, 116, "&#8722;", "bt", "middle"))

    # --- three lanes
    o.append(box(470, 40, 350, 74, "P + I &#8212; the only feedback there is", (
        "Kp_eff = SteerKP 0.70 + lsf(v)",
        "Ki_eff = AccordTorqueKi 0.20 &#183; Kp_eff/SteerKP",
        "lsf is ADDED, not scaled: 7.10 at 4.4&#8201;m/s"), "n2 edit"))
    o.append(arrow([(448, 77), (470, 77)]))

    o.append(box(470, 132, 350, 92, "plant feedforward &#183; switched ON", (
        "hold = k(v)/G(v) &#183; angle_des",
        "move = rate_des/G(v) &#183; AccordFFRateGain 1.0",
        "K_V [0.93, 1.64, 2.15, 2.77, 3.15]",
        "G_V [550, 271, 246, 205]"), "n2 edit"))
    # No label on this feed: the box it enters already names `angle_des`, and a caption here
    # collided with both the friction branch and the feedback return.
    o.append(arrow([(330, 88), (350, 88), (350, 178), (470, 178)]))

    o.append(box(470, 240, 350, 50, "friction", (
        "SteerFriction {{FRICTION}} &#183; sign(error + lsf)",), "n2 edit"))
    o.append(arrow([(400, 100), (400, 265), (470, 265)]))

    # --- divider, sum, wire
    o.append(box(860, 54, 140, 46, "&#247; SteerLatAccel", ("12.0 &#8212; P and I only",)))
    o.append(arrow([(820, 77), (860, 77)]))
    o.append(box(1040, 140, 70, 56, "&#931;", (), "n2 op"))
    o.append(arrow([(1000, 77), (1075, 77), (1075, 140)]))
    o.append(arrow([(820, 178), (1040, 178)]))
    o.append(arrow([(820, 265), (1010, 265), (1010, 186), (1040, 186)]))
    o.append(box(990, 290, 170, 52, "0xE4 STEER_TORQUE",
                 ("100&#8201;Hz &#183; &#177;4096 &#183; &#215;3988.5",)))
    o.append(arrow([(1075, 196), (1075, 290)]))

    # --- the car
    o.append(box(990, 400, 170, 54, "V293 torque map",
                 ("OPEN LOOP &#183; 10.34 cts/idx",), "n2 edit"))
    o.append(arrow([(1075, 342), (1075, 400)]))
    o.append(arrow([(990, 440), (840, 440)]))
    o.append(box(580, 396, 260, 104, "the plant &#8212; a SPRING", (
        "u = a(v)&#183;&#952; + b&#183;&#952;&#775; + F&#183;sign(&#952;&#775;)",
        "a 0.0023 &#8594; 0.0154 &#183; F &#8776; 0.011",
        "no inertia identified below 1.5&#8201;Hz",
        "Coulomb band 2F/a = the ratchet"), "n2 plant"))
    o.append(arrow([(580, 440), (465, 440)]))
    o.append(box(290, 413, 175, 54, "steering angle &#952;",
                 ("&#215;v&#178;/(SR&#183;L&#183;(1+Kv&#178;))",)))
    o.append(arrow([(290, 440), (200, 440)]))
    o.append(box(20, 413, 180, 54, "lateral acceleration",
                 ("gyro agrees within 1&#160;%",)))
    # feedback return
    o.append('<path d="M 110 413 L 110 344 L 434 344 L 434 102" class="fl fb" '
             'marker-end="url(#ah2)"/>')
    o.append(txt(24, 330, "measurement &#8212; the loop crosses over at 0.03&#8211;0.25&#8201;Hz, "
                 "so above about 0.1&#8201;Hz the car runs open loop", "tk sm"))
    o.append("</svg>")
    return "".join(o)


# =========================================================================== emit
FRAG = HERE / "v7_figs.frag"
parts = {
    "fig1": fig1(), "fig2": fig2(), "fig3a": fig3a(), "fig3b": fig3b(), "fig4": fig4(),
    "fig5a": fig5a(), "fig5b": fig5b(), "fig6a": fig6a(), "fig6b": fig6b(), "fig7": fig7(),
}
txtout = "\n".join(f"<!--#{k}#-->\n{v}" for k, v in parts.items())
FRAG.write_text(txtout, encoding="utf-8")
print(f"wrote {FRAG}  {len(txtout)} bytes")
for k, v in parts.items():
    print(f"  {k:6s} {len(v):7d}")
