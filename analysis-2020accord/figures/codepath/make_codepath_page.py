# -*- coding: utf-8 -*-
"""Generates docs/FIRMWARE-CODEPATH.html — the Artifact page source for the firmware code path (stock + V300 release).
Every plotted number is read from the two images; the cave rows come from the Ghidra dry-run listing of the built cave
(byte-identical in V299 and V300, re-checked here). Runs in ~1 s:
    python analysis-2020accord/figures/codepath/make_codepath_page.py
"""
import os, glob, struct, json, time, hashlib, html
t0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
st = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
vpath = [p for p in glob.glob(ROOT + "_v300_*plain_image.bin") if "REV2" in p][0]
v = open(vpath, "rb").read()
V300_SHA = hashlib.sha256(v).hexdigest()
assert V300_SHA == "7d58c823544e9e6ec369e7cc0fc0d7aa42fc8b075ad9b0005f58973d400f384e", "not the V300 rev-2 image"
u16 = lambda b, a: struct.unpack("<H", b[a:a+2])[0]
DIFF = sum(a != b for a, b in zip(st[0x13000:0x100000], v[0x13000:0x100000])); assert DIFF == 766
def srec(b, a):
    n = u16(b, a); X = [u16(b, a+2+2*i) for i in range(n)]; Y = [struct.unpack("<h", b[a+2+2*n+2*i:a+4+2*n+2*i])[0] for i in range(n)]; return X, Y
dX, dYs = srec(st, 0xD7A54); _, dYv = srec(v, 0xD7A54); assert srec(v, 0xD7A64) == (dX, dYv) and dYv == [-29490, -17202, -16000] and v[0xC40DC] == 14
CAVE = v[0xC4C00:0xC4D04]; CAVE_SHA = hashlib.sha256(CAVE).hexdigest()
listing = json.load(open(os.path.join(KIT, "analysis-2020accord/studies/angle_loop/v299_build/ghidra_listing_v299_cave.json")))
# the listing was taken on V299; assert its bytes are what V300 carries
for ins in listing["instructions"]:
    a = int(ins["address"], 16); b = bytes.fromhex(ins["bytes"])
    assert v[a:a+len(b)] == b, ins
assert v[0xC4CD8:0xC4CDA] == bytes.fromhex("6600")


def rec(b, a):
    n = u16(b, a); return [u16(b, a+2+2*i) for i in range(n)], [u16(b, a+2+2*n+2*i) for i in range(n)]


def lerp(x, X, Y):
    if x <= X[0]: return Y[0]
    if x >= X[-1]: return Y[-1]
    for i in range(len(X)-1):
        if x <= X[i+1]: return Y[i] + (Y[i+1]-Y[i])*(x-X[i])//(X[i+1]-X[i])


rows = [struct.unpack("<HHh", v[0xC4CDA+6*k:0xC4CDA+6*k+6]) for k in range(7)]


def G(vv):
    if vv <= rows[0][0]: return rows[0][1]
    k = 0
    while vv > rows[k+1][0]: k += 1
    x, y, s = rows[k]; return (((vv-x)*s) >> 12) + y


# cal values read from the images
cal = {}
for name, a in [("a", 0xC63E8), ("b", 0xC63EA), ("C", 0xC62E6), ("DB", 0xC62E4), ("Ki", 0xC63E6), ("ICL", 0xC61BA), ("PCL", 0xC61BC),
                ("DCL", 0xC61B6), ("SCL", 0xC61BE), ("rail", 0xC61B4), ("arb", 0xC61B2), ("gain", 0xC6CD0), ("lag_a", 0xC63EC), ("lag_b", 0xC63EE),
                ("lockout", 0xC62EA), ("rampin2", 0xC63FC), ("rampout2", 0xC63FA), ("shg", 0xC64A3), ("dz", 0xC61B8), ("k_stock", 0xC646C)]:
    cal[name] = (u16(st, a), u16(v, a))
KpX, KpYs = rec(st, 0xE5378); _, KpYv = rec(v, 0xE5378); KdX, KdYs = rec(st, 0xE511C); _, KdYv = rec(v, 0xE511C)
fBX, fBY = rec(st, 0xE564C); fB2Xs, fB2Ys = rec(st, 0xE54FC); fB2Xv, fB2Yv = rec(v, 0xE54FC)
mX, mYs = rec(st, 0xE502C); _, mYv = rec(v, 0xE502C); lX, lYs = rec(st, 0xE51A8); _, lYv = rec(v, 0xE51A8)
assert mYs == mYv and lYs == lYv and KpYv == [112]*5 and KdYv == [48]*4 and fB2Xv == fBX and fB2Yv == fBY
F181 = v[0x13100:0x1310E].decode()
RAIL = int(cal["SCL"][1] * 0.990 * 254/256 * cal["gain"][1] / 32768)

# ------------------------------------------------------------------ SVG line-chart helper (hover crosshair via JS) -----------
CHART_ID = [0]
SERIES = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)"]


def chart(title, xlabel, ylabel, series, xlim, ylim, xticks, yticks, vlines=(), hlines=(), note="", W=640, H=300):
    """series: list of (label, [(x,y),...]); vlines: (x,label); hlines: (y,label)."""
    CHART_ID[0] += 1; cid = "c%d" % CHART_ID[0]
    L, R, T, B = 58, 16, 30, 46
    pw, ph = W-L-R, H-T-B
    sx = lambda x: L + (x-xlim[0])/(xlim[1]-xlim[0])*pw
    sy = lambda y: T + ph - (y-ylim[0])/(ylim[1]-ylim[0])*ph
    o = ['<figure class="chart"><svg viewBox="0 0 %d %d" role="img" aria-label="%s" data-chart="%s">' % (W, H, html.escape(title), cid)]
    o.append('<text x="%d" y="18" class="ct">%s</text>' % (L, html.escape(title)))
    for yt in yticks:
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (L, sy(yt), W-R, sy(yt), L-6, sy(yt)+4, yt))
    for xt in xticks:
        o.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (sx(xt), T+ph+16, xt))
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis"/>' % (L, T+ph, W-R, T+ph))
    for x, lab in vlines:
        o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="ref"/><text x="%.1f" y="%d" class="ref-t">%s</text>' % (sx(x), T, sx(x), T+ph, sx(x)+4, T+12, html.escape(lab)))
    for y, lab in hlines:
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="ref"/><text x="%d" y="%.1f" class="ref-t">%s</text>' % (L, sy(y), W-R, sy(y), L+6, sy(y)-5, html.escape(lab)))
    data = []
    for i, (lab, pts) in enumerate(series):
        pts = [(x, y) for x, y in pts if xlim[0] <= x <= xlim[1]]
        d = " ".join("%.1f,%.1f" % (sx(x), min(max(sy(y), T), T+ph)) for x, y in pts)
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round"/>' % (d, SERIES[i]))
        lx, ly = pts[-1]
        o.append('<text x="%.1f" y="%.1f" class="dl" fill="%s" text-anchor="end">%s</text>' % (sx(lx)-2, min(max(sy(ly), T), T+ph)-6-10*i, SERIES[i], html.escape(lab.split(" (")[0][:28])))
        data.append({"label": lab, "pts": [[round(x, 3), round(y, 3)] for x, y in pts]})
    o.append('<text x="%d" y="%d" class="tick" text-anchor="middle">%s</text>' % (L+pw//2, H-4, html.escape(xlabel)))
    o.append('<text transform="translate(12,%d) rotate(-90)" class="tick" text-anchor="middle">%s</text>' % (T+ph//2, html.escape(ylabel)))
    o.append('<g class="hover" hidden><line y1="%d" y2="%d" class="xh"/><rect class="tt" rx="3"/><text class="ttx"></text></g>' % (T, T+ph))
    o.append('</svg><figcaption><span class="legend">%s</span>%s</figcaption></figure>' % (
        " ".join('<i style="background:%s"></i>%s' % (SERIES[i], html.escape(l)) for i, (l, _) in enumerate(series)), (" " + note) if note else ""))
    o.append('<script type="application/json" id="%s">%s</script>' % (cid, json.dumps({"L": L, "pw": pw, "x0": xlim[0], "x1": xlim[1], "T": T, "ph": ph, "y0": ylim[0], "y1": ylim[1], "s": data})))
    return "".join(o)


# ---- chart data from the images ---------------------------------------------------------------------------------------------
vw = list(range(0, 7201, 8)); ms = [x/230.4 for x in vw]
g = [G(x) for x in vw]
c_g = chart("Cave speed gain G(v), Q8 (256 = ×1), read from the table at 0xC4CDA", "vehicle speed (gp-0x6a5e ÷ 230.4, m/s)", "G",
            [("G(v)", list(zip(ms, g))), ("P per degree of error (lane S counts/deg) = 10·16·G·112 / 2^16", [(m, gg*112/256*16/256*10) for m, gg in zip(ms, g)])],
            (0, 31), (0, 2400), [0, 5, 10, 15, 20, 25, 30], [0, 500, 1000, 1500, 2000],
            vlines=[(1382/230.4, "1382: cap 4096→6144"), (2880/230.4, "2880: cap off, ×64")],
            note="Min G 559 at 11.75 m/s (the margin-limited band on the identified plant), 1178 below 3.1 m/s, 2188 above 26.9 m/s. The walk is linear between knots, slope in Q12.")
idx = list(range(0, 241))
c_kp = chart("Kp record 0xE5378 (bank 0xCB994, slot 7) vs demand index", "idx = |cmd| / 16.1 (an inert key once flat)", "Kp",
             [("stock Kp " + str(KpYs), [(i, lerp(i, KpX, KpYs)) for i in idx]), ("V300 Kp 112 flat (all 28 records)", [(i, lerp(i, KpX, KpYv)) for i in idx])],
             (0, 240), (0, 800), [0, 68, 112, 136, 208, 240], [0, 200, 400, 600, 800], note="Stock scheduled Kp on the command index, a rate-loop artefact; the release flattens it so the speed schedule lives in G(v) alone.")
c_kd = chart("Kd record 0xE511C (bank 0xCB7D4, slot 7)", "idx (X knots 0, 11, 22, 32)", "Kd",
             [("stock Kd 128 flat", [(i, lerp(i, KdX, KdYs)) for i in range(0, 41)]), ("V300 Kd 48 flat (all 28)", [(i, lerp(i, KdX, KdYv)) for i in range(0, 41)])],
             (0, 40), (0, 160), [0, 11, 22, 32, 40], [0, 50, 100, 150], note="D = (Kd·op) >> 3 on the fresh motor-frame rate; stock's D was on the error difference.")


def bound(theta, vv, outward=True):
    r9 = theta if outward else 0
    if vv > 2880: return (r9 << 6) + 1250
    b = (r9 << 4) + 1250; cap = 4096 if vv <= 1382 else 6144
    return min(b, cap)


th = list(range(0, 601, 2))
c_b = chart("A3 integral bound on I>>7 (S counts) vs |θ|, cave 0xC4C6A–0xC4CAB", "|steering angle| (deg = gp-0x6a00 ÷ 10)", "bound (S)",
            [("v ≤ 6.0 m/s: 16|θ|+1250, cap 4096", [(t/10, bound(t, 1000)) for t in th]), ("6.0 < v ≤ 12.5 m/s: cap 6144", [(t/10, bound(t, 2000)) for t in th]),
             ("v > 12.5 m/s: 64|θ|+1250, no cap", [(t/10, bound(t, 4000)) for t in th]), ("error toward centre: 1250 at every v", [(t/10, 1250) for t in th])],
            (0, 60), (0, 16000), [0, 10, 20, 30, 40, 50, 60], [0, 4000, 8000, 12000, 16000], hlines=[(8192, "Honda ICL 0xC61BA = 8192")],
            note="The I may wind only up to this, in the direction of E′ (bound = 16|θ|+1250 when sign θ = sign E′, else 1250). S × 0.1602 ≈ lane torque T hands off at full ramp.")
key = list(range(0, 160))
c_f = chart("Hand-torque fade f/255 on (I>>7)+P+D, 0x2A0B4–0x2A0C2", "|driver torque| (raw counts gp-0x4f68; record key = counts >> 5)", "f / 255",
            [("fadeB 0xE564C, arm 0 (stock camera / pre-V298)", [(k*32, lerp(k, fBX, fBY)/255) for k in key]), ("fadeB2 0xE54FC stock values, arm 2", [(k*32, lerp(k, fB2Xs, fB2Ys)/255) for k in key]),
             ("fadeB2 0xE54FC in V300 = fadeB's X/Y (live)", [(k*32, lerp(k, fB2Xv, fB2Yv)/255) for k in key])],
            (0, 5000), (0, 1.05), [0, 1000, 2000, 3000, 4000, 5000], [0, 0.25, 0.5, 0.75, 1.0], vlines=[(1229, "cave freeze |hand| > 1229")],
            note="0.99 at 600 counts, 0.86 at 1200, 0.70 at 1536, floor 0.30 above 2048. The field-2 interlock selects arm 2, so V298 copied arm 0's record into it; V300 keeps that.")
c_m = chart("Honda's demand map 0xE502C (bank 0xC9A88), stock = V300", "idx (0…240)", "Y",
            [("Honda map Y (max 172 = a rate setpoint)", list(zip(mX, mYs)))], (0, 240), (0, 200), [0, 32, 64, 96, 128, 160, 240], [0, 50, 100, 150, 200],
            note="Bypassed for the setpoint by E4 (sp := gp-0x69ae). The ×6 line to 1032 that V282–V299 carried is gone in the release.")
c_l = chart("Command clamp LIM 0xE51A8 vs speed, stock = V300", "speed (m/s)", "LIM",
            [("Honda LIM Y 15360", [(x/230.4, y) for x, y in zip(lX, lYs)])], (13, 37), (0, 18000), [15, 20, 25, 30, 35], [0, 5000, 10000, 15000],
            note="Feeds only idx in angle mode; the ±16384 the angle setpoint sees is the RX writer's constant.")
c_d = chart("DampAxis lane Y(v), record 0xD7A54 (twin 0xD7A64): stock vs kept", "speed (X ÷ 230.4, m/s; X = 0, 1280, 5760)", "Y",
            [("stock Y " + str(dYs), [(x/230.4, y) for x, y in zip(dX, dYs)]), ("V300 rev 2 keeps V299's Y " + str(dYv), [(x/230.4, y) for x, y in zip(dX, dYv)])],
            (0, 25), (-32000, 0), [0, 5, 10, 15, 20, 25], [-30000, -20000, -10000, 0],
            note="The lagged positive-inertia lane gp-0x6b26 on the motor rate (FUN_00041464 → FUN_00036c12, K2 = 0xC40DC = 14 kept). Reverting it fails GATE 2: GM at 3 m/s 20 → 5.2 dB, 5–30 Hz peak +5.4 dB, Ms 1.26 → 2.68 (re-score). The r24 gate/arm revert passes.")
e_deg = [i/10 for i in range(0, 601)]


def T_of(e, Gv):
    E = 160*e; Ep = E*Gv/256; P = max(-15360, min(15360, Ep*112/256)); return P*0.990*(254/256)*cal["gain"][1]/32768


c_t = chart("P-only lane torque vs angle error, read from the image", "angle error |θ_sp − θ| (deg)", "T (gp-0x6b38 counts)",
            [("v ≤ 3.1 m/s, G 1178: 51.6 T/deg", [(e, T_of(e, 1178)) for e in e_deg]), ("11.75 m/s, G 559: 24.5 T/deg", [(e, T_of(e, 559)) for e in e_deg]),
             ("≥ 26.9 m/s, G 2188: 95.8 T/deg", [(e, T_of(e, 2188)) for e in e_deg])],
            (0, 60), (0, 2800), [0, 10, 20, 30, 40, 50, 60], [0, 500, 1000, 1500, 2000, 2500], hlines=[(RAIL, "lane rail %d T (stock chain tops at 410 T)" % RAIL)],
            note="P reaches the rail at 47.7° / 100° / 25.7° of error; the fork's error clip (4.5–17° by speed) keeps P inside that, so the I and its A3 bound carry the steady curve load. I and D add to this; the fade multiplies it.")

# ---- cave table ------------------------------------------------------------------------------------------------------------------------
DESC = {  # addr: (effect, python, term)
 0xC4C00: ("r16 = 4·sp", "E = sp << 2", "E = 16θ_sp − 16θ"), 0xC4C02: ("r16 = 4sp − r26", "E -= r26", "r26 = 16θ from the filter"),
 0xC4C04: ("r26 = op", "op = s16(gp_6abe)", "fresh motor-frame rate"), 0xC4C08: ("r8 = op + 13000", "", "validity window"), 0xC4C0C: ("r13 = 26000", "", ""),
 0xC4C10: ("", "", ""), 0xC4C12: ("continue if (op+13000) ≤u 26000", "if (op+13000)&0xFFFFFFFF > 26000:", "op-skip test (Honda's ±13000 form)"),
 0xC4C14: ("invalid rate → Honda's skip epilogue: I := 0, sentinel, S := 0", "return SKIP", "no torque path on an invalid rate"),
 0xC4C18: ("r8 = v", "vv = gp_6a5e", "speed"), 0xC4C1C: ("r9 = &table", "", "G(v) table pointer (relinked)"), 0xC4C22: ("r13 = X₀ = 714", "", ""), 0xC4C26: ("", "", ""),
 0xC4C28: ("v > X₀ → walk", "", ""), 0xC4C2A: ("G = Y₀ = 1178", "G = rows[0].y", "below 3.1 m/s"), 0xC4C2E: ("", "", ""),
 0xC4C30: ("r13 = X_{i+1}", "while vv > rows[k+1].x: k += 1", "walk"), 0xC4C34: ("", "", ""), 0xC4C36: ("v ≤ X_{i+1} → segment found", "", ""), 0xC4C38: ("next row", "", ""), 0xC4C3C: ("", "", ""),
 0xC4C3E: ("r13 = X_i", "", ""), 0xC4C42: ("r8 = v − X_i", "", ""), 0xC4C44: ("r13 = slope_i (signed)", "", ""), 0xC4C48: ("r8 = (v−X_i)·slope", "", ""),
 0xC4C4C: (">> 12", "G = ((vv-x)*s >> 12) + y", "linear segment, slope Q12"), 0xC4C4E: ("r13 = Y_i", "", ""), 0xC4C52: ("G", "", ""),
 0xC4C54: ("r16 = E·G", "Ep = (E*G) >> 8", "E′"), 0xC4C58: ("", "", "Q8"), 0xC4C5A: ("", "if r25 == 0:", "camera interlock"), 0xC4C5C: ("field ≠ 2 → CAM", "", ""),
 0xC4C5E: ("r8 = |hand|", "h = gp_4f68", ""), 0xC4C62: ("1229", "", "hard-freeze level (V298: 512)"), 0xC4C66: ("", "", ""), 0xC4C68: ("|hand| > 1229 → FRZ", "if h > 1229: return FRZ", "hands on: I frozen, P and D live"),
 0xC4C6A: ("r9 = θ", "r9 = theta", "A3 bound"), 0xC4C6E: ("", "", ""), 0xC4C70: ("", "", ""), 0xC4C72: ("if E′ < 0: r9 = −θ", "if Ep < 0: r9 = -r9", "θ·sgn(E′)"), 0xC4C74: ("", "", ""), 0xC4C76: ("", "", ""),
 0xC4C78: ("if r9 < 0: 0", "r9 = max(r9, 0)", "toward centre ⇒ 0 (asymmetric)"), 0xC4C7A: ("r8 = v", "", ""), 0xC4C7E: ("2880 = 12.5 m/s", "", ""), 0xC4C82: ("", "", ""), 0xC4C84: ("v > 2880 → uncapped path", "", ""),
 0xC4C86: ("16·r9", "b = (r9 << 4) + 1250", "≤ 12.5 m/s"), 0xC4C88: ("+ 1250", "", "friction allowance B"), 0xC4C8C: ("1382 = 6.0 m/s", "", "two-level cap"), 0xC4C90: ("", "", ""), 0xC4C92: ("", "", ""),
 0xC4C94: ("cap 4096 (v ≤ 6 m/s)", "cap = 4096 if vv <= 1382 else 6144", ""), 0xC4C98: ("", "", ""), 0xC4C9A: ("cap 6144 (6 < v ≤ 12.5)", "", "V299's new level"), 0xC4C9E: ("", "", ""),
 0xC4CA0: ("r9 = min_u(b, cap)", "b = min(b, cap)", ""), 0xC4CA4: ("", "", ""), 0xC4CA6: ("64·r9", "b = (r9 << 6) + 1250", "> 12.5 m/s, no cap"), 0xC4CA8: ("+ 1250", "", ""),
 0xC4CAC: ("r13 = 8·I", "t = I8 >> 10", "I in S units (I>>7)"), 0xC4CB0: ("", "", ""), 0xC4CB2: ("", "", ""), 0xC4CB4: ("", "", ""), 0xC4CB6: ("if E′ < 0: t = −t", "if Ep < 0: t = -t", "I projected on E′"),
 0xC4CB8: ("", "", ""), 0xC4CBA: ("t ≥ bound → FRZ", "if t >= b: return FRZ", "winding past the bound"), 0xC4CBC: ("ramp full?", "if not ramp & 0x8000: return FRZ", "ramp-in freeze"), 0xC4CC0: ("→ DONE", "", ""),
 0xC4CC2: ("FRZ: e5 := 0", "", "I unchanged this tick"), 0xC4CC4: ("into Honda's exc test with r6 = 0", "", "P (r16 = E′) and D (r26 = op) stay live"),
 0xC4CC8: ("CAM: E′ := 0", "Ep = 0", "camera field ≠ 2: lane inert"), 0xC4CCA: ("op := 0 ⇒ D = 0", "op = 0", ""), 0xC4CCC: ("r6 = 8·I", "", ""), 0xC4CD0: ("", "", ""),
 0xC4CD2: ("e5 := −(8I >> 6)", "e5 = -(I8 >> 6)", "I ← 0.375·I per tick (Honda adds (e5·40)>>3)"), 0xC4CD4: ("", "", ""), 0xC4CD8: ("DONE → 0x29D7A", "return DONE", "Honda PID on E′"),
}
cave_rows = []
for ins in listing["instructions"]:
    a = int(ins["address"], 16); eff, py, term = DESC.get(a, ("", "", ""))
    cave_rows.append("<tr><td class=mono>%05X</td><td class=mono>%s</td><td class=mono>%s %s</td><td>%s</td><td class=mono>%s</td><td>%s</td></tr>" % (
        a, ins["bytes"], ins["mnemonic"], html.escape(ins["operands"]), html.escape(eff), html.escape(py), html.escape(term)))
cave_rows.append("<tr><td class=mono>C4CD8</td><td class=mono>6600</td><td class=mono>jmp [r6]</td><td>DONE → 0x29D7A</td><td class=mono>return DONE</td><td>Honda PID on E′</td></tr>")
cave_rows.append("<tr><td class=mono>C4CDA</td><td class=mono>42 B</td><td class=mono>table (X:u16, Y:u16, slope:s16) × 7</td><td colspan=3>%s — walk min G 559 at v 2707 (11.75 m/s)</td></tr>" % html.escape(" ".join(str(r) for r in rows)))
CAVE_TABLE = "\n".join(cave_rows)

# ---- diagram layout engine: every box width is computed from its text, rows have fixed gutters, arrows run only in gutters --------------
CH = 6.9          # px per character at 11.5 px sans (measured conservatively)
PAD = 14          # horizontal padding inside a box
LH = 15           # line height
GUT_X = 44        # horizontal gutter between boxes in a row
GUT_Y = 56        # vertical gutter between rows (room for one or two routed horizontals + a label)
MARG = 16


class Box:
    def __init__(self, lines, style=""):
        self.lines = lines; self.style = style
        self.w = int(max(len(l) for l in lines) * CH + 2 * PAD)
        self.h = 12 + LH * len(lines) + 6
        self.x = self.y = 0; self.row = 0; self.col = 0


class Diagram:
    def __init__(self, rows, aria, caption):
        self.rows = rows; self.aria = aria; self.caption = caption; self.arrows = []; self.notes = []
        for r, row in enumerate(rows):
            for c, b in enumerate(row): b.row, b.col = r, c
        self.gut_use = {}

    def _layout(self):
        """Box positions from text widths; the horizontal gutter is widened to hold the widest adjacent-arrow label,
        each vertical gutter is sized from the number of routes it must carry (one 16 px lane each)."""
        adj = [len(l) * CH * 0.92 + 14 for a, b, l, _ in self.arrows if a.row == b.row and abs(a.col - b.col) == 1 and l]
        self.gx = max(GUT_X, int(max(adj)) if adj else 0)
        lanes = {}
        for a, b, l, _ in self.arrows:
            if a.row == b.row and abs(a.col - b.col) != 1: lanes[a.row] = lanes.get(a.row, 0) + 1
            elif b.row == a.row + 1: lanes[a.row] = lanes.get(a.row, 0) + 1
            elif b.row == a.row - 1: lanes[b.row] = lanes.get(b.row, 0) + 1
            elif b.row == a.row - 2: lanes[a.row - 1] = lanes.get(a.row - 1, 0) + 1; lanes[b.row] = lanes.get(b.row, 0) + 1
        self.gy = {r: max(GUT_Y, 16 * n + 28) for r, n in lanes.items()}
        y = MARG; self.W = 0
        for r, row in enumerate(self.rows):
            x = MARG; hmax = max(b.h for b in row)
            for b in row:
                b.x, b.y, b.h = x, y, hmax; x += b.w + self.gx
            self.W = max(self.W, x - self.gx + MARG); y += hmax + self.gy.get(r, GUT_Y)
        self.H = y - self.gy.get(len(self.rows) - 1, GUT_Y) + MARG
        self.gut_use = {}

    def _lane(self, gap):
        n = self.gut_use.get(gap, 0); self.gut_use[gap] = n + 1
        return n

    def arrow(self, a, b, label="", dashed=False):
        self.arrows.append((a, b, label, dashed))

    def note(self, x, y, text):
        self.notes.append((x, y, text))

    def _label(self, x, y, text, anchor="middle"):
        if not text: return ""
        w = len(text) * CH * 0.92 + 8
        lx = x - w / 2 if anchor == "middle" else x
        return '<rect x="%.1f" y="%.1f" width="%.1f" height="15" class="lbl-bg"/><text x="%.1f" y="%.1f" class="lbl" text-anchor="%s">%s</text>' % (lx, y - 11, w, x, y, anchor, html.escape(text))

    def _route(self, a, b, label, dashed):
        cls = ' class="dash"' if dashed else ""
        out = []
        if a.row == b.row:
            if b.col == a.col + 1:            # adjacent, left to right
                y = a.y + a.h / 2; x1, x2 = a.x + a.w, b.x
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"%s/>' % (x1, y, x2, y, cls))
                out.append(self._label((x1 + x2) / 2, y - 6, label))
            elif a.col == b.col + 1:          # adjacent, right to left
                y = a.y + a.h / 2; x1, x2 = a.x, b.x + b.w
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"%s/>' % (x1, y, x2, y, cls))
                out.append(self._label((x1 + x2) / 2, y - 6, label))
            else:                             # same row, not adjacent: go through the gutter below
                gap = a.row; lane = self._lane(gap); yg = a.y + a.h + 14 + lane * 16
                xa = a.x + a.w / 2 + (lane * 14 - 7); xb = b.x + b.w / 2 + (lane * 14 - 7)
                out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f"%s/>' % (xa, a.y + a.h, yg, xb, b.y + b.h + 1, cls))
                out.append(self._label((xa + xb) / 2, yg - 4, label))
        elif b.row == a.row + 1:              # down into the next row through the gutter
            gap = a.row; lane = self._lane(gap); yg = a.y + a.h + 14 + lane * 16
            xa = a.x + a.w / 2 + (lane * 14 - 7); xb = b.x + b.w / 2 + (lane * 14 - 7)
            if abs(xa - xb) < 2:
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"%s/>' % (xa, a.y + a.h, xb, b.y, cls))
                out.append(self._label(xa + 8, (a.y + a.h + b.y) / 2 + 4, label, "start"))
            else:
                out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f"%s/>' % (xa, a.y + a.h, yg, xb, b.y, cls))
                out.append(self._label((xa + xb) / 2, yg - 4, label))
        elif b.row == a.row - 1:              # up into the previous row through the gutter above a
            gap = b.row; lane = self._lane(gap); yg = b.y + b.h + 14 + lane * 16
            xa = a.x + a.w / 2 + (lane * 14 - 7); xb = b.x + b.w / 2 + (lane * 14 - 7)
            out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f"%s/>' % (xa, a.y, yg, xb, b.y + b.h, cls))
            out.append(self._label((xa + xb) / 2, yg - 4, label))
        elif b.row == a.row - 2:              # up two rows: through the gutter above a, a vertical corridor between two boxes of the middle row, the gutter below b
            mid = self.rows[a.row - 1]
            g1 = a.row - 1; l1 = self._lane(g1); y1 = mid[0].y + mid[0].h + 14 + l1 * 16
            g0 = b.row; l0 = self._lane(g0); y0 = b.y + b.h + 14 + l0 * 16
            xb = b.x + b.w / 2 + (l0 * 14 - 7)
            gaps = [(mb.x + mb.w + GUT_X / 2) for mb in mid[:-1]] + [mid[-1].x + mid[-1].w + GUT_X / 2, mid[0].x - GUT_X / 2]
            xc = min(gaps, key=lambda g: abs(g - xb))
            xa = a.x + a.w / 2 + (l1 * 14 - 7)
            out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f H%.1f V%.1f"%s/>' % (xa, a.y, y1, xc, y0, xb, b.y + b.h + 1, cls))
            out.append(self._label((xc + xb) / 2, y0 - 4, label))
        else:
            raise ValueError("route not supported: rows %d -> %d" % (a.row, b.row))
        return "".join(out)

    def check(self, name):
        """Re-derive every routed polyline from the emitted SVG and test it against every box interior (2 px inset)."""
        import re as _r
        svg = self.svg(); bad = []
        boxes = [(bx, bx.x + 2, bx.y + 2, bx.x + bx.w - 2, bx.y + bx.h - 2) for row in self.rows for bx in row]
        def hits(x1, y1, x2, y2):
            out = []
            for bx, l, t, r, btm in boxes:
                # axis-aligned segment vs rect interior
                if x1 == x2 and l < x1 < r and min(y1, y2) < btm and max(y1, y2) > t: out.append(bx.lines[0])
                if y1 == y2 and t < y1 < btm and min(x1, x2) < r and max(x1, x2) > l: out.append(bx.lines[0])
            return out
        for m in _r.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"', svg):
            x1, y1, x2, y2 = map(float, m.groups()); h = hits(x1, y1, x2, y2)
            if h: bad.append(("line", (x1, y1, x2, y2), h))
        for m in _r.finditer(r'<path d="M([\d.]+) ([\d.]+)((?: [VH][\d.]+)+)"', svg):
            x, y = float(m.group(1)), float(m.group(2))
            for seg in m.group(3).split():
                nx, ny = (float(seg[1:]), y) if seg[0] == "H" else (x, float(seg[1:]))
                h = hits(x, y, nx, ny)
                if h: bad.append(("path", (x, y, nx, ny), h))
                x, y = nx, ny
        for m in _r.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="15" class="lbl-bg"', svg):
            x, y, w = map(float, m.groups())
            for bx, l, t, r, btm in boxes:
                if x < r and x + w > l and y < btm and y + 15 > t: bad.append(("label", (x, y, w), [bx.lines[0]]))
        print("%s: %d boxes, %d arrows, collisions: %d" % (name, len(boxes), len(self.arrows), len(bad)))
        for bd in bad: print("   ", bd)
        return bad

    def svg(self):
        self._layout()
        o = ['<figure><svg viewBox="0 0 %d %d" role="img" aria-label="%s" class="diag">' % (self.W, self.H, html.escape(self.aria)),
             '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>']
        o.append('<g class="arrows">' + "".join(self._route(*ar) for ar in self.arrows) + '</g>')
        for row in self.rows:
            for b in row:
                o.append('<g class="box %s"><rect x="%d" y="%d" width="%d" height="%d" rx="4"/>' % (b.style, b.x, b.y, b.w, b.h))
                for i, l in enumerate(b.lines):
                    o.append('<text x="%.1f" y="%d" text-anchor="middle" class="%s">%s</text>' % (b.x + b.w / 2, b.y + 12 + LH * (i + 1) - 4, "t" if i == 0 else "sm", html.escape(l)))
                o.append('</g>')
        for x, y, t in self.notes:
            o.append(self._label(x, y, t, "start"))
        o.append('</svg><figcaption>%s</figcaption></figure>' % self.caption)
        return "".join(o)


# ---- (A) firmware signal flow, front half --------------------------------------------------------------------------------------------
op = Box(["openpilot 0xE4 @100 Hz", "bytes 0-1: raw = −10·θ_des", "byte 2: bit 7 request, bits 3:2 = 2"])
rx = Box(["RX callback FUN_00052676", "gp-0x69ae = clamp(−4·raw, ±16384)", "gp-0x6805 request · gp-0x6803 field"])
sm = Box(["engage SM (ST, state, ramp)", "arm 2: in 0.10 s, out 0.50 s"])
gd = Box(["★ guard 0x29A48 (A2 + B2)", "run iff ramp ≠ 0 ∧ request ∧ bVar2"], "mod")
sp = Box(["★ setpoint E4", "sp := gp-0x69ae (map bypassed)"], "mod")
sens = Box(["sensors", "θ gp-0x6a00: 100 Hz hold, 0.1°", "op gp-0x6abe: fresh 1 kHz rate", "v gp-0x6a5e · hand gp-0x4f60/68"])
fb = Box(["★ feedback filter 0x28F4C", "E1: x := θ · a 0, b 8192, C 65535", "r26 = 8θ[n] + 8θ[n−1] = 16θ"], "mod")
hook = Box(["★ HOOK 0x29D76: jarl 0xC4C00", "r16 = sp · r26 = 16θ · r25 = field"], "mod")
cave = Box(["★ CAVE 0xC4C00 (260 B, no RAM)", "E = 4sp − r26 · op-skip on 0x7FFF", "E′ = (E·G(v)) >> 8 · camera gate", "freeze |hand| > 1229 · A3 bound", "caps 4096 / 6144 · ramp-in freeze"], "cave")
pid = Box(["★ Honda PID 0x29D7A on E′", "I: Ki 40, |I>>7| ≤ 8192", "P = (E′·112)>>8 · D = 6·op", "S = (I>>7) + P + D"], "mod")
fade = Box(["★ hand fade 0x29F08", "f = A(grab)·B(|hand|) ≥ 0.30", "S = clamp((S·f)>>8, ±15360)"], "mod")
outp = Box(["★ output 0x2A174–0x2A23C", "lag 5 Hz → sign-hold → ×ramp", "×pol×5346 >> 15 → ±3072", "T = gp-0x6b38, rail 2461"], "mod")
A = Diagram([[op, rx, sm], [sens, fb, gd], [sp, hook, cave], [pid, fade, outp]],
            "Firmware signal flow, front half: the 0xE4 frame to the lane's torque output; starred boxes are the stages the release changes",
            "(a) From the openpilot frame to the lane torque T. ★ = changed by the release (legend: orange = edited stage, blue = the cave). Arrows run in the gutters only.")
A.arrow(op, rx, "frame"); A.arrow(rx, sm, "request, field"); A.arrow(sm, gd, "ramp"); A.arrow(sens, fb, "θ")
A.arrow(fb, gd, "16θ"); A.arrow(gd, sp, "run"); A.arrow(sp, hook, "sp"); A.arrow(hook, cave, "jarl")
A.arrow(sens, cave, "v, op, hand"); A.arrow(cave, pid, "E′, op"); A.arrow(pid, fade, "S"); A.arrow(fade, outp, "S·f")
FLOW_A = A.svg()

# ---- (B) firmware signal flow, back half ---------------------------------------------------------------------------------------------
lane = Box(["lane T gp-0x6b38 → gp-0x6b3c", "× enable gp-0x67a4 ∈ {2,3}"])
lim = Box(["★ limit / distribute / mix", "FUN_0002b422 ±0xC61B2 (3072)", "→ FUN_00025c32 → FUN_00026c80"], "mod")
base = Box(["base assist (hands-on)", "torque sensor → map → banks (stock)"])
damp = Box(["★ DampAxis lane gp-0x6b26 (kept)", "motor rate → EMA → Δ → EMA(K2 = 14)", "× Y(v) record 0xD7A54 → ±511"], "mod")
agg = Box(["aggregator FUN_0003aa2c", "Σ lanes → gp-0x6b94", "+ friction, return-centre, r24 (stock)"])
gov = Box(["governor", "ceiling 0xC6202 = 4762"])
eme = Box(["★ EME shaper FUN_00042af8", "corridor ±5.0 / floor 5.0 ladder", "→ gp-0x6b98"], "mod")
foc = Box(["FOC FUN_00071272", "PI current loop → SVPWM"])
plant = Box(["rack / column plant", "spring k(v) + Coulomb → θ, op"])
Bd = Diagram([[lane, lim, base], [damp, agg], [gov, eme, foc], [plant]],
             "Firmware signal flow, back half: the lane torque through the aggregator, governor, EME shaper and FOC to the motor and the plant",
             "(b) From the lane torque to the motor. The aggregator sums the LKAS lane with Honda's base-assist lanes; only the ★ clamps, the DampAxis values and the EME ladder are non-stock there.")
Bd.arrow(lane, lim, "T"); Bd.arrow(lim, agg, "gp-0x6b4c"); Bd.arrow(base, agg, "gp-0x6bbe"); Bd.arrow(damp, agg, "gp-0x6b26")
Bd.arrow(agg, gov, "gp-0x6b94"); Bd.arrow(gov, eme, ""); Bd.arrow(eme, foc, "gp-0x6b98"); Bd.arrow(foc, plant, "motor torque")
FLOW_B = Bd.svg()

# ---- closed-loop control view ---------------------------------------------------------------------------------------------------------
c_sp = Box(["θ_sp from the fork", "100 Hz · raw = −10·θ_des"])
c_rx = Box(["0xE4 poll", "200 Hz, held ≤ 5 ms"])
c_sum = Box(["Σ  E = 4sp − 16θ", "1 kHz"], "sum")
c_g = Box(["★ × G(v) >> 8", "559 … 2188 by speed"], "cave")
c_pid = Box(["★ PID on E′, 1 kHz", "P = E′·112>>8 · D = 6·op", "I: Ki 40, A3 bound, freeze 1229"], "mod")
c_out = Box(["× fade f(|hand|) ≥ 0.30", "±15360 → lag 5 Hz → sign-hold", "× ramp × pol·5346>>15 → ±3072"])
c_mot = Box(["aggregator → governor", "→ EME → FOC → motor"])
c_plant = Box(["plant: column + rack", "spring k(v) + Coulomb friction"])
c_op = Box(["op gp-0x6abe", "fresh every 1 ms (slot 0)"])
c_hold = Box(["θ hold gp-0x6a00", "written at 100 Hz, read at 1 kHz", "1–10 ms old · r26 = 8θ[n] + 8θ[n−1]"])
L = Diagram([[c_sp, c_rx, c_sum, c_g], [c_pid, c_out, c_mot], [c_plant, c_op, c_hold]],
            "Closed-loop block diagram of the angle loop with each block's update period: a 1 kHz loop closed on a 100 Hz angle hold with a fresh 1 kHz rate for the D term",
            "Control view. The setpoint and the angle feedback are both 100 Hz holds inside a 1 kHz loop; the D operand is fresh. Feedback paths return through the gutter below the top row.")
L.arrow(c_sp, c_rx, "raw"); L.arrow(c_rx, c_sum, "4·sp"); L.arrow(c_sum, c_g, "E"); L.arrow(c_g, c_pid, "E′"); L.arrow(c_pid, c_out, "S"); L.arrow(c_out, c_mot, "T")
L.arrow(c_mot, c_plant, "motor torque"); L.arrow(c_plant, c_op, "resolver rate"); L.arrow(c_op, c_hold, "motor count → θ")
L.arrow(c_op, c_pid, "op (fresh)"); L.arrow(c_hold, c_sum, "16θ (−)")
LOOP = L.svg()

# ---- fork pipeline ---------------------------------------------------------------------------------------------------------------------
f1 = Box(["fw id 39990-TVA,A16?", "read over UDS F181"])
f2 = Box(["angle control", "steerControlType = angle"])
f3 = Box(["angle limiter", "rate 120 deg/s · jerk"])
f4 = Box(["error clip", "4.5–17° by speed"])
f5 = Box(["0xE4 packing", "raw = −10·θ · field = 2 every frame"])
f6 = Box(["EPS angle loop", "V300"])
fx = Box(["turn-initiation lead", "not applied under angle control", "(the measured hunting cause)"], "cross")
F = Diagram([[f1, f2, f3], [f4, f5, f6, fx]],
            "Fork pipeline: firmware id detection, angle mode, limiter, error clip, 0xE4 packing with the interlock field, and the turn-lead branch that is not taken",
            "Fork side, one line per step. The crossed branch is the turn-initiation lead the fork does not apply under angle control; the drive read of 2026-10-15 found the high-angle back-and-forth fork-sourced (the setpoint itself moves).")
F.arrow(f1, f2, "match"); F.arrow(f2, f3, "θ_des"); F.arrow(f3, f4, "θ_lim"); F.arrow(f4, f5, "θ_cmd"); F.arrow(f5, f6, "CAN bus 1")
F.arrow(f2, fx, "", dashed=True)
FORK = F.svg().replace('</svg>', '<line x1="%d" y1="%d" x2="%d" y2="%d" class="xmark"/><line x1="%d" y1="%d" x2="%d" y2="%d" class="xmark"/></svg>' % (
    fx.x + 6, fx.y + 6, fx.x + fx.w - 6, fx.y + fx.h - 6, fx.x + 6, fx.y + fx.h - 6, fx.x + fx.w - 6, fx.y + 6))

# ---- timing (computed ticks) -------------------------------------------------------------------------------------------------------------
TW = 1000; TX0 = 20; TPX = (TW - 40) / 40.0
rows_t = [("slot 0, 1 ms: FUN_00041464 (fresh rate op) → FUN_00028ea6 lane + cave", [t for t in range(41)], "s2"),
          ("slot 4, every 10th tick (c mod 10 == 4): writes θ gp-0x6a00 and the wire rate → seen 1–10 ms old", [t for t in range(41) if t % 10 == 4], "s1"),
          ("slot 3, every 5th tick: 0xE4 RX poll → gp-0x69ae (openpilot sends 0xE4 every 10 ms)", [t for t in range(41) if t % 5 == 2], "s3")]
tsvg = ['<figure><svg viewBox="0 0 %d 170" role="img" aria-label="Timeline of 40 ms: 1 kHz lane ticks, 100 Hz angle writes, 200 Hz CAN polls" class="diag">' % TW]
for i, (lab, ticks, col) in enumerate(rows_t):
    y = 24 + i * 44
    tsvg.append('<text x="%d" y="%d" class="sm">%s</text>' % (TX0, y, html.escape(lab)))
    tsvg.append("".join('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="tk %s"/>' % (TX0 + t * TPX, y + 6, TX0 + t * TPX, y + 22, col) for t in ticks))
tsvg.append('<line x1="%d" y1="150" x2="%d" y2="150" class="axis"/>' % (TX0, TW - 20) + "".join('<text x="%.1f" y="165" class="tick" text-anchor="middle">%d ms</text>' % (TX0 + t * TPX, t) for t in range(0, 41, 10)))
tsvg.append('</svg><figcaption>Who runs when (TCB table 0xBB920, dispatcher FUN_00014be4). Slot 0 has the highest priority; switching is cooperative, so a lane tick is never torn.</figcaption></figure>')
TIMING = "".join(tsvg)

# ---- risk cards with mini SVGs ----------------------------------------------------------------------------------------------------------
E = '<span class="tag e" title="evidence, method given">E</span>'; B = '<span class="tag b" title="belief">B</span>'


def bars(pairs, unit, W=260, H=92):
    """pairs: [(label, value, cls)], scaled to max; computed geometry."""
    m = max(v for _, v, _ in pairs); bw = 70; gap = 30; x0 = 20
    o = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s" class="mini">' % (W, H, html.escape("; ".join("%s %s %s" % (l, v, unit) for l, v, _ in pairs)))]
    for i, (l, v, c) in enumerate(pairs):
        h = max(3, 54 * v / m); x = x0 + i * (bw + gap); y = 66 - h
        o.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" rx="3" class="%s"/><text x="%d" y="%.1f" class="val" text-anchor="middle">%s</text><text x="%d" y="82" class="lab" text-anchor="middle">%s</text>' % (x, y, bw, h, c, x + bw // 2, y - 4, v, x + bw // 2, html.escape(l)))
    o.append('<text x="%d" y="82" class="lab" text-anchor="start">%s</text></svg>' % (x0 + 2 * (bw + gap) - 10, unit))
    return "".join(o)


def badge2(items, W=260, H=92):
    o = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s" class="mini">' % (W, H, html.escape("; ".join("%s: %s" % (a, s) for a, s in items)))]
    for i, (a, s) in enumerate(items):
        y = 18 + i * 34
        o.append('<rect x="12" y="%d" width="52" height="22" rx="11" class="%s"/><text x="38" y="%d" class="val" text-anchor="middle">%s</text><text x="74" y="%d" class="lab">%s</text>' % (y, "off" if s == "OFF" else "on", y + 15, s, y + 15, html.escape(a)))
    o.append('</svg>'); return "".join(o)


def minicurve(X, Ys, Yv, labs, W=260, H=92):
    x0, x1, y0, y1 = 16, W - 12, 12, 70
    lo, hi = min(Ys + Yv), 0
    sx = lambda x: x0 + (x1 - x0) * x / max(X); sy = lambda y: y1 - (y1 - y0) * (y - lo) / (hi - lo)
    o = ['<svg viewBox="0 0 %d %d" role="img" aria-label="damper Y rows stock %s vs kept %s" class="mini">' % (W, H, Ys, Yv)]
    for Y, c in ((Ys, "s1"), (Yv, "s2")):
        o.append('<polyline points="%s" class="ln %s"/>' % (" ".join("%.1f,%.1f" % (sx(x), sy(y)) for x, y in zip(X, Y)), c))
    o.append('<text x="%d" y="86" class="lab">%s</text><text x="%d" y="86" class="lab" text-anchor="end">%s</text></svg>' % (x0, html.escape(labs[0]), x1, html.escape(labs[1])))
    return "".join(o)


def tile(big, small, W=260, H=92):
    return '<svg viewBox="0 0 %d %d" role="img" aria-label="%s %s" class="mini"><text x="%d" y="52" class="big" text-anchor="middle">%s</text><text x="%d" y="78" class="lab" text-anchor="middle">%s</text></svg>' % (W, H, html.escape(big), html.escape(small), W // 2, html.escape(big), W // 2, html.escape(small))


cards = [
 ("Lane authority stays 6× Honda's", "Rail %d T = 15360 × 0.990 × 254/256 × 5346 ≫ 15. Stock: × 891 under a 512 clamp = 410 T. Unchanged since V282; the loop's P/I/D were sized on it." % RAIL, bars([("stock", 410, "s1"), ("V300", RAIL, "s2")], "T"), E),
 ("EME protection ≈ 5× looser, all driving", "Honda's excessive-effort ladder 1024 → 5120 (corridor ±5.0 / floor 5.0, int + float) is a kept ×6 cell. Permissive only; V38…V267 flew with it on Honda's banks.", bars([("stock", 1024, "s1"), ("V300", 5120, "s2")], "counts"), E + B),
 ("Two Honda interlocks stay off", "The V36/V37 package disables the driver-torque-transient STEER_STATUS trip and the DTC-0x49 over-torque counter (stock 0xC64B4..B8 = 112/96/54/64/112 → 255), as on every flown build since V37.", badge2([("STEER_STATUS transient trip", "OFF"), ("DTC 0x49 counter", "OFF")]), E),
 ("Hands-on feel returns to Honda's", "Damper banks, Coulomb relay knee/K1 and the biquad are stock again after ≈ 6 weeks on modified banks. One lane is kept: DampAxis (curve). Magnitude of the feel change is a belief.", minicurve(dX, dYs, dYv, ["stock Y %s" % dYs, "kept %s" % dYv]), E + B),
 ("GATE 2 re-score: DampAxis kept", "Reverting the DampAxis lane drops GM at 3 m/s from 20 to 5.2 dB (peak +5.4 dB, Ms 1.26 → 2.68), so rev 2 keeps its 13 bytes. The r24 gate/arm revert passes (ΔPM −0.7…+0.1°, GM ≥ 20 dB).", tile("20 → 5.2 dB", "GM at 3 m/s if reverted · KEPT"), E),
 ("Stock camera: lane inert, not stock LKAS", "With a stock camera the field is never 2, so E′ = 0: V300 is Honda base assist only. A stock camera cannot steer through this firmware.", badge2([("camera field 2 seen", "NEVER"), ("lane with stock camera", "OFF")]), E),
 ("No ramp-out on request drop", "A2 skips the PID on the first request-0 tick: lane torque goes to 0 at once through the 5 Hz lag, instead of Honda's 0.5 s ramp-out (arm 2).", bars([("stock", 500, "s1"), ("V300", 0, "s2")], "ms ramp-out"), E),
 ("Loop live below 5 km/h", "The low-speed lockout 0xC62EA is 0 (stock 320 ≈ 5 km/h). Kept by decision: the goal says every speed.", bars([("stock", 320, "s1"), ("V300", 0, "s2")], "lockout counts"), E),
 ("Hand fade, direction-2 arm", "The fork's field = 2 selects arm 2; its record 0xE54FC carries arm 0's curve (0.86 at 1200 counts, floor 0.30 above 2048). The cave's 1229 freeze is Honda's hands-on level.", tile("0.30 floor", "above 2048 counts · freeze at 1229"), E),
 ("Nothing on the wire but F181", "0x14A byte 4 bits 3–7 and byte 7 bits 6–7 are no longer forced; the 0x1AB torque tap is gone. Only the fw id identifies the build.", tile(F181, "the only build identifier"), E + B),
]
RISK = '<div class="cards">' + "".join('<div class="card"><h4>%s %s</h4>%s<p>%s</p></div>' % (html.escape(t), tg, svg, html.escape(s)) for t, s, svg, tg in cards) + '</div>'

# ---- widest unbreakable token per table (the no-horizontal-scroll check) ----------------------------------------------------------------
import re as _re


def widest_token(html_fragment):
    cells = _re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', html_fragment, _re.S)
    toks = [t for c in cells for t in _re.sub(r'<[^>]+>', ' ', c).split()]
    return max(toks, key=len) if toks else ""


# ---- the page ----------------------------------------------------------------------------------------------------------------------------
GLANCE_T1 = '''<div class="tw"><table><thead><tr><th>V300 vs stock, every run grouped</th><th>B</th><th>what it is</th></tr></thead><tbody>
<tr><td class=mono>0x28F4E 0x29A50 0x29A56 0x29D6A 0x29D76 0x29EE0 0x2A1F0</td><td>20</td><td>the in-place lane edits</td></tr>
<tr><td class=mono>0xC4C00–0xC4D03</td><td>260</td><td>the cave</td></tr>
<tr><td class=mono>0xC63E6..EB · 0xC62E4..E7 · 0xC61BB</td><td>11</td><td>Ki 40, a 0, b 8192, DB 0, C 65535, ICL 8192</td></tr>
<tr><td class=mono>0xC6CD0 · 0xC61B3 · 0xC61B5</td><td>4</td><td>6× authority chain: gain 5346, clamps 3072</td></tr>
<tr><td class=mono>0xC659A…0xC65CE · 0xC674F…0xC676E</td><td>21</td><td>EME corridor/floor ladder, int + float</td></tr>
<tr><td class=mono>0xC61C0..C5 · 0xC64B4..B8</td><td>11</td><td>STEER_STATUS debounce + DTC-0x49 gate (V36/V37)</td></tr>
<tr><td class=mono>0xC62EA</td><td>2</td><td>low-speed lockout off</td></tr>
<tr><td class=mono>0xD7A5C..61 · 0xD7A6C..71 · 0xC40DC</td><td>13</td><td>DampAxis lane kept at V299: Y −29490/−17202/−16000, α2 14</td></tr>
<tr><td class=mono>Kp Y ×28 · Kd Y ×28 (pages 0xE4–0xE8)</td><td>392</td><td>112 flat / 48 flat on every slot</td></tr>
<tr><td class=mono>0xE54FE..0xE5515</td><td>22</td><td>fadeB2 (arm 2) := fadeB</td></tr>
<tr><td class=mono>0x1310D · 0x13109</td><td>2</td><td>F181 39990-TVA,A16C</td></tr>
<tr><td class=mono>8 CRC trailers</td><td>32</td><td>recomputed</td></tr>
</tbody></table></div>'''
GLANCE_T2 = '''<div class="tw"><table><thead><tr><th>V300 vs V299: removed, stock again</th><th>what it was</th></tr></thead><tbody>
<tr><td class=mono>0x55C0E hook · 0xC4B34 cave · 0x55DF2 packer</td><td>telemetry: 0x14A byte-4 bits 3–7 and byte-7 bits 6–7 rungs, the 0x1AB torque tap</td></tr>
<tr><td>×6 assist map ×28 · LIM 16384 ×28</td><td>rate-setpoint map and ceiling, bypassed by E4</td></tr>
<tr><td class=mono>0x3AA96 · 0xC6446</td><td>r24 lane gate and its flat engaged arm 2048</td></tr>
<tr><td class=mono>0xC649B + 0x35A08/12/18 · 0xC40BC/D2 · 0xC64DE</td><td>biquad arm, Coulomb relay knee/K1, square-wave hold</td></tr>
<tr><td class=mono>0xCE000–0xD9FFF (979 of 992 B)</td><td>base-assist damper banks, all but the 13 DampAxis bytes</td></tr>
<tr><td class=mono>0x454FE · 0x14120</td><td>inert selector byte; dead id-string copy</td></tr>
<tr><td>Kp/Kd on the 27 non-selected records</td><td>960 / 0 → 112 / 48 (slot 7 unchanged)</td></tr>
</tbody></table></div>'''
EDITS_T = '''<div class="tw"><table><thead><tr><th>id</th><th>addr</th><th>stock → V300</th><th>instruction</th><th>why</th></tr></thead><tbody>
<tr><td>E1</td><td class=mono>0x28F4E</td><td class=mono>aa 95 → 00 96</td><td class=mono>ld.h -0x6a56[gp],r7 → ld.h -0x6a00[gp],r7</td><td>filter operand := θ</td></tr>
<tr><td>B2</td><td class=mono>0x29A50</td><td class=mono>e2 47 00 00 → e0 df 34 43</td><td class=mono>setfe r8 → cmovne r0,r27,r8</td><td>r8 = request ? bVar2 : 0</td></tr>
<tr><td>A2</td><td class=mono>0x29A56</td><td class=mono>da → b2</td><td class=mono>bne 0x29A60 → be 0x29A5C</td><td>PID runs only when ramp ≠ 0 and r8</td></tr>
<tr><td>E4</td><td class=mono>0x29D6A</td><td class=mono>08 80 ed 80 → 24 87 52 96</td><td class=mono>mov r8,r16 ; mulh r13,r16 → ld.h -0x69ae[gp],r16</td><td>sp := the raw command (the map path has 1.61° steps)</td></tr>
<tr><td>HOOK</td><td class=mono>0x29D76</td><td class=mono>c5 82 ba 81 → 89 37 8a ae</td><td class=mono>shl 0x5,r16 ; sub r26,r16 → jarl 0xC4C00,r6</td><td>enter the cave, return 0x29D7A</td></tr>
<tr><td>OPH</td><td class=mono>0x29EE0</td><td class=mono>10 40 bb 41 → 1a 40 00 00</td><td class=mono>mov r16,r8 ; sub r27,r8 → mov r26,r8 ; nop</td><td>D operand := op</td></tr>
<tr><td>GAIN</td><td class=mono>0x2A1F0</td><td class=mono>6c 74 → d0 7c</td><td class=mono>ld.h 0x746c[tp],r7 → ld.h 0x7cd0[tp],r7</td><td>lane gain from the private cell 0xC6CD0 = 5346 (6.0× the shared 891)</td></tr>
<tr><td>V1</td><td class=mono>0x1310D</td><td class=mono>30 → 43</td><td class=mono>F181 "39990-TVA,A160" → "…A16C"</td><td>the fork's firmware fingerprint (UDS F181 is the only reader)</td></tr>
</tbody></table></div>'''
CALS_T = f'''<div class="tw"><table><thead><tr><th>cell</th><th>addr</th><th>V300 [stock]</th><th>role</th></tr></thead><tbody>
<tr><td>a</td><td class=mono>0xC63E8</td><td class=mono>{cal['a'][1]} [{cal['a'][0]}]</td><td>fb filter pole; 0 ⇒ pure 2-tap sum</td></tr>
<tr><td>b</td><td class=mono>0xC63EA</td><td class=mono>{cal['b'][1]} [{cal['b'][0]}]</td><td>fb filter input gain ⇒ s_new = 8θ</td></tr>
<tr><td>C</td><td class=mono>0xC62E6</td><td class=mono>{cal['C'][1]} [{cal['C'][0]}]</td><td>r26 clamp ⇒ |θ| ≤ 409.6°</td></tr>
<tr><td>DB</td><td class=mono>0xC62E4</td><td class=mono>{cal['DB'][1]} [{cal['DB'][0]}]</td><td>I deadband on e5</td></tr>
<tr><td>Ki</td><td class=mono>0xC63E6</td><td class=mono>{cal['Ki'][1]} [{cal['Ki'][0]}]</td><td>integral gain (Honda ships 0)</td></tr>
<tr><td>ICL</td><td class=mono>0xC61BA</td><td class=mono>{cal['ICL'][1]} [{cal['ICL'][0]}]</td><td>I≫7 ceiling, S counts</td></tr>
<tr><td>PCL / DCL / SCL</td><td class=mono>0xC61BC / B6 / BE</td><td class=mono>{cal['PCL'][1]} / {cal['DCL'][1]} / {cal['SCL'][1]} [same]</td><td>P, D, sum clamps</td></tr>
<tr><td>lag</td><td class=mono>0xC63EC / EE</td><td class=mono>{cal['lag_a'][1]} / {cal['lag_b'][1]} [same]</td><td>output lag 5.05 Hz, DC 0.990</td></tr>
<tr><td>gain</td><td class=mono>0xC6CD0</td><td class=mono>{cal['gain'][1]} [0xFFFF unused]</td><td>lane torque gain read by the repointed 0x2A1F0 (stock read 0xC646C = {cal['k_stock'][0]})</td></tr>
<tr><td>rail / arb clamp</td><td class=mono>0xC61B4 / B2</td><td class=mono>{cal['rail'][1]} / {cal['arb'][1]} [{cal['rail'][0]} / {cal['arb'][0]}]</td><td>5346·512/891 = 3072 exactly</td></tr>
<tr><td>Kp Y</td><td class=mono>0xE5384 (rec 0xE5378) + 27 records</td><td class=mono>112 ×5 [{', '.join(map(str, KpYs))}]</td><td>X 0, 68, 112, 136, 208 unchanged</td></tr>
<tr><td>Kd Y</td><td class=mono>0xE5126 (rec 0xE511C) + 27 records</td><td class=mono>48 ×4 [128 ×4]</td><td>X 0, 11, 22, 32</td></tr>
<tr><td>fadeB2</td><td class=mono>0xE54FC</td><td class=mono>X {fB2Xv} Y {fB2Yv} [X {fB2Xs} Y {fB2Ys}]</td><td>the live hand fade under arm 2, set equal to arm 0's record 0xE564C</td></tr>
<tr><td>ramps (arm 2)</td><td class=mono>0xC63FC / FA</td><td class=mono>{cal['rampin2'][1]} / {cal['rampout2'][1]} [same]</td><td>0.10 s in, 0.50 s out, live because the fork sends field 2</td></tr>
<tr><td>sign-hold</td><td class=mono>0xC64A3 / 0xC61B8</td><td class=mono>{cal['shg'][1] & 0xFF} / {cal['dz'][1]} [same]</td><td>gate enable / dead zone</td></tr>
<tr><td>DampAxis</td><td class=mono>0xD7A5C..61, 0xD7A6C..71 (records 0xD7A54/64, X 0/1280/5760) · 0xC40DC</td><td class=mono>Y −29490/−17202/−16000 [−9830/−5734/−1966] · α2 14 [22]</td><td>the motor-rate inertia lane gp-0x6b26, V299's values kept (GATE 2)</td></tr>
<tr><td>lockout</td><td class=mono>0xC62EA</td><td class=mono>{cal['lockout'][1]} [{cal['lockout'][0]}]</td><td>low-speed LKAS lockout disabled (kept by decision)</td></tr>
<tr><td>debounce / DTC</td><td class=mono>0xC61C0/C2/C4, 0xC64B4..B8</td><td class=mono>0xFFFF ×3, 0xFF ×5 [1600/896/1280, 112/96/54/64/112]</td><td>STEER_STATUS gentle-EME debounce + DTC-0x49 gate</td></tr>
<tr><td>EME ladder</td><td class=mono>0xC659A…0xC65CE (f32), 0xC674F…0xC676E (s16)</td><td class=mono>walls ±5.0, floor 5.0 [±1.0, 0/1.5/2.0]</td><td>matched int/float pairs for the lockstep monitor</td></tr>
<tr><td>F181</td><td class=mono>0x13100</td><td class=mono>{F181} [39990-TVA-A160]</td><td>version string</td></tr>
</tbody></table></div>'''
YIELD_T = f'''<div class="tw"><table><thead><tr><th>mechanism</th><th>where</th><th>what happens</th><th></th></tr></thead><tbody>
<tr><td>camera interlock</td><td class=mono>cave C4C5A, C4CC8</td><td>a 0xE4 whose byte-2 bits 3:2 ≠ 2 (every stock-camera frame ever logged) makes the lane inert: E′ = 0, D = 0, I decays to 0 within a few ticks</td><td>{E}</td></tr>
<tr><td>hard hand freeze</td><td class=mono>cave C4C5E–C4C68</td><td>|hand| &gt; 1229 raw (Honda's 1200 on the wire): I frozen; P and D keep running against the fade</td><td>{E}</td></tr>
<tr><td>hand fade</td><td class=mono>0x29F08–0x2A0C2</td><td>the whole sum × f: 0.99 at 600 counts, 0.86 at 1200, 0.70 at 1536, floor 0.30 above 2048; no fork-side override by ruling</td><td>{E}</td></tr>
<tr><td>A3 bound</td><td class=mono>cave C4C6A–C4CBA</td><td>I cannot wind past 16|θ|+1250 S (caps 4096 / 6144) in the error's direction, nor past 1250 S toward centre</td><td>{E} bytes · {B} lurch sizes</td></tr>
<tr><td>ramp-in freeze</td><td class=mono>cave C4CBC</td><td>no integration until the ramp is full (0.10 s under arm 2)</td><td>{E}</td></tr>
<tr><td>request drop</td><td class=mono>SM 2 → 4; A2/B2</td><td>ramp −66/tick (0.50 s); the PID is skipped on the first request-0 tick (S := 0, I := 0); torque decays through the lag</td><td>{E}</td></tr>
<tr><td>0xE4 timeout / fault</td><td class=mono>sentinel after 510 ms</td><td>bVar2 false ⇒ the PID is skipped; stock's 2 s railed pulse cannot occur; the last setpoint is held ≈ 0.5 s first</td><td>{E} bytes · {B} trigger</td></tr>
<tr><td>invalid rate</td><td class=mono>cave op-skip → 0x2A164</td><td>op = 0x7FFF routes to Honda's own skip epilogue: I := 0, sentinel, S := 0</td><td>{E}</td></tr>
<tr><td>sign-hold gate</td><td class=mono>0x2A198–0x2A1E4</td><td>while released: T := 0 if |y| ≤ 102 or y opposes the last delivered sign</td><td>{E}</td></tr>
<tr><td>assist substate</td><td class=mono>gp-0x67fe ≠ 2</td><td>θ reads 0 next pass; not gated in the cave (declared; never observed in 2.3 M frames)</td><td>{E} mechanism · {B} frequency</td></tr>
</tbody></table></div>'''
CAVE_T = '<div class="tw scroll"><table class="cave"><thead><tr><th>addr</th><th>bytes</th><th>V850E2</th><th>effect</th><th>Python</th><th>design term</th></tr></thead><tbody>' + CAVE_TABLE + '</tbody></table></div>'
WIDEST = {n: widest_token(t) for n, t in [("glance-1", GLANCE_T1), ("glance-2", GLANCE_T2), ("edits", EDITS_T), ("cals", CALS_T), ("yield", YIELD_T)]}

PAGE = f"""<title>Accord EPS Angle-Loop Codepath</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* layout: a technical datasheet, one column ≤ 1120 px; diagrams scale to the column; only the cave listing may scroll inside its own frame */
:root {{
  --bg:#f7f6f2; --fg:#1b1d22; --mut:#5c6270; --line:#d9d6cd; --panel:#ffffff; --panel2:#efede6;
  --acc:#b4451b; --acc-soft:#f6e3d8; --cave:#e8eef9; --cave-line:#2a78d6;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --e:#1f7a3a; --b:#8a5a00; --off:#c43b2f; --on:#1f7a3a;
  --sans:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif; --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#17181c; --fg:#e8e6e0; --mut:#a6a9b3; --line:#34373f; --panel:#1f2127; --panel2:#262932;
  --acc:#f0875a; --acc-soft:#3a271d; --cave:#1d2634; --cave-line:#3987e5;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --e:#4fc47a; --b:#e0a63a; --off:#ef6a5e; --on:#4fc47a; color-scheme:dark }} }}
:root[data-theme="dark"] {{
  --bg:#17181c; --fg:#e8e6e0; --mut:#a6a9b3; --line:#34373f; --panel:#1f2127; --panel2:#262932;
  --acc:#f0875a; --acc-soft:#3a271d; --cave:#1d2634; --cave-line:#3987e5;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --e:#4fc47a; --b:#e0a63a; --off:#ef6a5e; --on:#4fc47a; color-scheme:dark }}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font:15px/1.55 var(--sans);padding-block:20px 60px;padding-inline:max(16px,calc(50% - 560px));overflow-x:hidden}}
h1{{font-size:1.8rem;line-height:1.15;font-weight:600;margin:.2rem 0 .4rem;text-wrap:balance}}
h2{{font-size:1.25rem;font-weight:600;margin:2.2rem 0 .6rem;padding-top:.9rem;border-top:1px solid var(--line);text-wrap:balance}}
h3{{font-size:1.02rem;font-weight:600;margin:1.4rem 0 .4rem}}
p,li{{max-width:78ch}} p{{margin:.5rem 0}} .lede{{color:var(--mut);max-width:84ch}}
code{{font-family:var(--mono);font-size:.86em;overflow-wrap:anywhere}}
pre{{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:12px 14px;overflow-x:auto;font:12.5px/1.5 var(--mono);margin:.8rem 0}}
.toc{{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.82rem;padding:8px 0;margin:.4rem 0 1rem}}
.toc a{{color:var(--acc);text-decoration:none;white-space:nowrap}} a{{color:var(--acc)}} a:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.kv{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:1rem 0}}
.kv div{{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:10px 12px;min-width:0}}
.kv b{{display:block;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);font-weight:500}}
.kv span{{font-family:var(--mono);font-size:.88rem;overflow-wrap:anywhere}}
.tw{{margin:.8rem 0;border:1px solid var(--line);border-radius:4px;background:var(--panel);max-width:100%}}
.tw.scroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums;table-layout:auto}}
th,td{{text-align:left;vertical-align:top;padding:6px 9px;border-bottom:1px solid var(--line);overflow-wrap:anywhere;word-break:break-word}} th{{background:var(--panel2);font-weight:600}}
tr:last-child td{{border-bottom:0}} td.mono{{font-family:var(--mono);font-size:.8rem}}
table.cave td.mono{{white-space:nowrap}} table.cave{{min-width:860px}}
.tag{{display:inline-block;font:600 .68rem/1 var(--mono);padding:3px 5px;border-radius:3px;vertical-align:middle;margin-left:4px}}
.tag.e{{color:var(--e);border:1px solid var(--e)}} .tag.b{{color:var(--b);border:1px solid var(--b)}}
figure{{margin:1rem 0;max-width:100%;overflow-x:auto}} figure svg{{max-width:100%;height:auto;display:block}} figure svg.diag{{min-width:640px}} .chart svg{{min-width:0}} figcaption{{font-size:.82rem;color:var(--mut);margin-top:.4rem;max-width:90ch}}
.diag{{color:var(--fg);font:11.5px var(--sans);background:var(--panel);border:1px solid var(--line);border-radius:4px}}
.diag .box rect{{fill:var(--panel2);stroke:var(--line)}} .diag .box.mod rect{{fill:var(--acc-soft);stroke:var(--acc)}} .diag .box.cave rect{{fill:var(--cave);stroke:var(--cave-line);stroke-width:1.5}}
.diag .box.sum rect{{fill:var(--panel);stroke:var(--fg)}} .diag .box.cross rect{{fill:var(--panel);stroke:var(--mut);stroke-dasharray:4 3}}
.diag text{{fill:var(--fg)}} .diag .t{{font-weight:600}} .diag .sm{{font-size:10.5px;fill:var(--mut)}}
.diag .arrows line,.diag .arrows path{{stroke:currentColor;stroke-width:1.3;fill:none;marker-end:url(#ar)}} .diag .arrows .dash{{stroke-dasharray:4 3;stroke:var(--mut)}}
.diag .lbl-bg{{fill:var(--panel);stroke:none}} .diag .lbl{{font-size:10.5px;fill:var(--mut)}} .diag .xmark{{stroke:var(--off);stroke-width:2.5}}
.diag .tk.s1{{stroke:var(--s1);stroke-width:2.5}} .diag .tk.s2{{stroke:var(--s2);stroke-width:1.5}} .diag .tk.s3{{stroke:var(--s3);stroke-width:2}} .diag .axis{{stroke:var(--line)}} .diag .tick{{fill:var(--mut);font-size:10px}}
.legend-row{{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.82rem;color:var(--mut);margin:.2rem 0 .6rem}} .legend-row i{{display:inline-block;width:14px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle;border:1px solid var(--line)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin:.8rem 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:12px 14px;min-width:0;display:flex;flex-direction:column;gap:6px}}
.card h4{{margin:0;font-size:.95rem;font-weight:600;text-wrap:balance}} .card p{{margin:0;font-size:.84rem;color:var(--mut)}}
.mini{{width:100%;max-width:280px;height:auto;font-family:var(--sans)}} .mini .s1{{fill:var(--s1)}} .mini .s2{{fill:var(--s2)}} .mini .val{{font-size:11px;font-weight:600;fill:var(--fg)}} .mini .lab{{font-size:10px;fill:var(--mut)}}
.mini .ln{{fill:none;stroke-width:2.5}} .mini .ln.s1{{stroke:var(--s1)}} .mini .ln.s2{{stroke:var(--s2)}} .mini .off{{fill:var(--off)}} .mini .on{{fill:var(--on)}} .mini .off+text,.mini .on+text{{fill:#fff}} .mini .big{{font-size:22px;font-weight:600;fill:var(--fg)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}} .grid2 > *{{min-width:0}}
.chart svg{{background:var(--panel);border:1px solid var(--line);border-radius:4px;font-family:var(--sans)}}
.chart .ct{{font-size:12.5px;font-weight:600;fill:var(--fg)}} .chart .tick{{font-size:10.5px;fill:var(--mut)}} .chart .grid{{stroke:var(--line);stroke-width:.7}} .chart .axis{{stroke:var(--mut)}}
.chart .ref{{stroke:var(--mut);stroke-dasharray:3 3}} .chart .ref-t{{font-size:10px;fill:var(--mut)}} .chart .dl{{font-size:10.5px;font-weight:500}}
.chart .xh{{stroke:var(--fg);stroke-width:.8;stroke-dasharray:2 2}} .chart .tt{{fill:var(--panel);stroke:var(--line)}} .chart .ttx{{font-size:10.5px;fill:var(--fg)}}
.legend i{{display:inline-block;width:12px;height:3px;margin:0 5px 3px 10px;vertical-align:middle}}
@media (prefers-reduced-motion: reduce){{*{{transition:none!important}}}}
</style>

<h1>2020 Accord EPS firmware: the angle-loop release, read from the image</h1>
<p class="lede">What this is: the LKAS code path of the Renesas V850E2 image <code>39990-TVA-A160</code>, stock and as modified by the release V300 rev 2 (fw id <code>{F181}</code>). openpilot sends a steering-angle setpoint on CAN 0xE4; a 1 kHz loop in the EPS closes on the measured angle through a 260-byte code cave and Honda's own PID, with Honda's hand fade as the only override. Every number on this page was read from the stock dump and the release image; {E} = evidence with its method, {B} = belief.</p>
<nav class="toc"><a href="#loop">control view</a><a href="#flow">firmware flow</a><a href="#glance">release tiles</a><a href="#risk">risk</a><a href="#fork">fork side</a><a href="#timing">timing</a><a href="#stock">stock path</a><a href="#mod">edits</a><a href="#cave">cave</a><a href="#cals">cals</a><a href="#curves">curves</a><a href="#yield">how it yields</a></nav>

<h2 id="loop">1. The control loop</h2>
{LOOP}

<h2 id="flow">2. The firmware signal flow</h2>
<div class="legend-row"><span><i style="background:var(--acc-soft);border-color:var(--acc)"></i>★ stage edited by the release</span><span><i style="background:var(--cave);border-color:var(--cave-line)"></i>the cave (new code)</span><span><i style="background:var(--panel2)"></i>stock Honda</span></div>
{FLOW_A}
{FLOW_B}

<h2 id="glance">3. The release, at a glance</h2>
<div class="kv">
<div><b>release image</b><span>V300 rev 2 · F181 {F181} · sha256 {V300_SHA[:16]}…</span></div>
<div><b>differs from stock</b><span>{DIFF} bytes, 207 runs, 8 CRC blocks</span></div>
<div><b>removed vs V299</b><span>2,110 bytes back to stock: telemetry, ×6 map, LIM, r24 arm, biquad, relay, banks</span></div>
<div><b>cave 0xC4C00</b><span>260 B · sha {CAVE_SHA[:16]}… · identical to V299</span></div>
<div><b>lane rail</b><span>{RAIL} T = 15360 × 0.990 × 254/256 × {cal['gain'][1]} ≫ 15</span></div>
<div><b>loop tuning</b><span>Kp 112 · Kd 48 · Ki 40 · ICL 8192 · G(v) 559…2188 · freeze 1229 · caps 4096 / 6144 (unchanged from V299)</span></div>
</div>
{GLANCE_T1}
{GLANCE_T2}

<h2 id="risk">4. Risk, before the drive</h2>
{RISK}

<h2 id="fork">5. Fork side</h2>
{FORK}

<h2 id="timing">6. Who runs when</h2>
{TIMING}

<h2 id="stock">7. The stock path, stage by stage</h2>
<h3>7.1 0xE4 reception, FUN_00052676</h3>
<pre>raw      = s16((b0 &lt;&lt; 8) | b1)                 # STEER_TORQUE, big-endian; under the mod this IS the angle setpoint: θ_sp = −raw (0.1°)
gp_69ae  = clamp(−4·raw, −0x4000, 0x4000)      # st.h @0x526F2
gp_6803  = (b2 &lt;&lt; 28) &gt;&gt; 30   # byte 2 bits 3:2  (logical shr @0x526F6) — the camera-interlock field
gp_6805  = b2 &gt;&gt; 7            # byte 2 bit 7 = STEER_TORQUE_REQUEST
gp_6804  = (b2 &lt;&lt; 25) &gt;&gt; 31 ; gp_6802 = b2 &amp; 3 ; gp_67f3 = b3 &gt;&gt; 7 (debounced)
sentinel (fault status, or 500 ms without a frame): gp_69ae = 0x7FFF, gp_6805 = gp_6803 = … = 0xFF   # re-asserted every 5 ms</pre>
<p>The sentinel lands 510–514 ms after the last frame; until then the last setpoint and request are held. The stock camera sends bits 3:2 ∈ {{0, 1}} on 6.9 M logged frames and never 2. {E}</p>
<h3>7.2 The feedback-operand filter, 0x28F4C–0x28FC6 (runs every valid tick)</h3>
<pre>x     = ld.h(gp-0x6a56)  # stock: the wire rate      ★E1 (0x28F4E aa95→0096): x = ld.h(gp-0x6a00) = θ
s_new = ((b·x) &gt;&gt; 10) + ((a·s_old) &gt;&gt; 10)          # b 0xC63EA, a 0xC63E8: stock 1560 / 923 → ★ 8192 / 0
r26   = s_old + s_new                               # 0x28FA4 add r9,r26 (stock and V300)
r26   = clamp(r26, ±C)                              # C 0xC62E6: stock 7680 → ★ 65535
# stock: a 16.5 Hz LPF on the rate, DC gain 30.89.  V300: s_new = 8θ exactly ⇒ r26 = 8θ[n] + 8θ[n−1] = 16θ, no pole</pre>
<h3>7.3 The guard, 0x29A48–0x29A64</h3>
<pre>stock:  run the PID iff ramp ≠ 0  OR  request == 1        (0x29A56 bne ; 0x29A5A bne ; 0x29A5C jr 0x2A164)
V300:   ★B2 0x29A50 setfe r8 → cmovne r0,r27,r8   r8 = request ? bVar2 : 0     (r27 = bVar2, dominates every path)
        ★A2 0x29A56 bne 0x29A60 → be 0x29A5C       run iff ramp ≠ 0 AND r8
# removes the override-latch wind-up (integrating at ramp 0 with request still 1) and the 0xE4 sentinel pulse (bVar2 is false on 0x7FFF)</pre>
<h3>7.4 The setpoint stage, 0x28FC8–0x29D6C</h3>
<pre>cmd = ld.h(gp-0x69ae) ; r22 = clamp(cmd, ±LIM(v))                        # LIM record 0xE51A8, 15360 flat (stock = V300)
vv  = (65025·r22) &gt;&gt; 16 &gt;&gt; 6 ; idx = min(|vv|, 240)                        # 16.13 wire counts per idx step
sp  = sign · LERP(map record 0xE502C, idx)       # 0x29D6A mov r8,r16 ; 0x29D6C mulh r13,r16  → stock max 172 = a RATE setpoint
                                                 ★E4 (0x29D6A 0880ed80→24875296): sp = ld.h(gp-0x69ae) — map, LIM, taper, 240 clamp bypassed
E   = (sp &lt;&lt; 5) − r26                            # 0x29D76 shl 5 ; 0x29D78 sub r26  ★HOOK (c582ba81→89378aae): jarl 0xC4C00, r6
# gp-0x682f = min(|gp-0x4f60| &gt;&gt; 5, 255) is the DRIVER torque key of the fade/arb stages, not a map output (0x29068)</pre>
<h3>7.5 Honda's PID, fade and output, 0x29D7A–0x2A23C</h3>
<pre>e5 = E &gt;&gt; 5 ; exc = deadband(e5, DB 0xC62E4)                          # DB stock 4 → ★ 0
I  = clamp((8I &gt;&gt; 3) + ((exc·Ki) &gt;&gt; 3), ±(ICL &lt;&lt; 10 &gt;&gt; 3))               # Ki 0xC63E6 stock 0 (!) → ★ 40 ; ICL 0xC61BA 10240 → ★ 8192 ; cell gp-0x6dd0 holds 8I
P  = clamp((E·Kp) &gt;&gt; 8, ±15360)                                        # Kp = LERP(record 0xE5378, idx): stock 248…696 → ★ 112 flat
D  = clamp((Kd·dE) &gt;&gt; 3, ±DCL)        # stock dE = E − E_prev ; ★OPH (0x29EE0 1040bb41→1a400000): operand = r26 = op (fresh rate) ; Kd 128 → ★ 48
S  = (I &gt;&gt; 7) + P + D                                                  # 0x29F18–0x29F24
f  = ((A(grab)·B(|hand|)) &amp; 0xFFFF) &gt;&gt; 8                                 # arm 2 records 0xE55A4 / 0xE54FC (★ = arm 0's values); 254 hands off, floor 76
S  = clamp((S·f) &gt;&gt; 8, ±15360)
y  = lag_5Hz(S) ; sign-hold gate while released ; y = (y·ramp) &gt;&gt; 15      # 0x2A174–0x2A1EC, cals 992 / 507, 0xC64A3 = 1, dead zone 102
T  = clamp((pol · k · y) &gt;&gt; 15, ±0xC61B4)     # k: stock ld.h 0xC646C = 891 → ★GAIN (0x2A1F0 6c74→d07c) ld.h 0xC6CD0 = 5346 ; clamp 512 → ★ 3072
st.h(gp-0x6b38, T) ; gp-0x6b3c = T if gp-0x67a4 ∈ {{2,3}}                 # rail 2461 T at S = 15360 (stock chain: 410 T under 512)</pre>
<p>Downstream (diagram b): limit/pack <code>FUN_0002b422</code> ±<code>0xC61B2</code> (★3072) → distribute → mixer → <code>gp-0x6b4c</code> → aggregator <code>FUN_0003aa2c</code>, which adds Honda's base-assist, friction, return-centre and r24 lanes (stock; r24 = <code>pol·deadband(G(v)·gp-0x4f62, 3)</code> on 0.5·(T[n]−T[n−4])) and the ★ DampAxis lane <code>gp-0x6b26</code> (motor rate → EMA → Δ → EMA with K2 = <code>0xC40DC</code> = 14 → ×Y(v) record <code>0xD7A54</code> → ±511, kept at V299's values) → governor → EME shaper (★ ladder) → FOC. No consumer of the 0xE4 fault cells sits on that path. {E}</p>

<h2 id="mod">8. The release's in-place edits (vs stock) ★</h2>
{EDITS_T}
<p>Stock <code>0x28FA4</code> is already <code>add r9,r26</code>; V294/V295 had changed it and V298 restored it, so against stock it is not an edit. The telemetry hook <code>0x55C0E</code>, the 0x1AB packer, <code>0x3AA96</code>, <code>0x454FE</code> and <code>0x14120</code> read stock in V300. {E}</p>

<h2 id="cave">9. The cave at 0xC4C00, instruction by instruction</h2>
<p>Entry from the hook with r16 = sp, r26 = 16θ, r25 = (field == 2), r14 = ramp. The cave writes no RAM. Exits: DONE <code>jmp [r6]</code> → 0x29D7A with r16 = E′ and r26 = op; FRZ/CAM <code>jr 0x29D7E</code> with r6 preset so Honda's <code>e5 := r6</code>; op-skip <code>jr 0x2A164</code>. The listing is the GhidraMCP dry-run of the built cave; this generator re-asserts every row's bytes against the V300 image. {E} (This listing is the one table on the page that scrolls inside its own frame.)</p>
{CAVE_T}
<div class="kv"><div><b>then Honda's PID on the DONE path</b><span>I += ((E′≫5)·40)≫3, |I≫7| ≤ 8192 · P = (E′·112)≫8 ≤ 15360 · D = (48·op)≫3 ≤ 10240 · S = (I≫7)+P+D → fade → ±15360 → lag → ×ramp → ×pol·5346≫15 → ±3072. pol = −1 ⇒ D opposes wheel motion. 51.6 / 24.5 / 95.8 T per degree of error at ≤ 3.1 / 11.75 / ≥ 26.9 m/s.</span></div></div>

<h2 id="cals">10. Calibration and record cells the loop uses (V300, stock in brackets)</h2>
{CALS_T}

<h2 id="curves">11. The curves, read from the images</h2>
<div class="grid2">{c_g}{c_kp}{c_kd}{c_b}{c_f}{c_t}{c_d}{c_m}{c_l}</div>

<h2 id="yield">12. How the loop yields</h2>
{YIELD_T}
<p class="lede">Full text with the Python mirrors, the removal table and the verified-vs-carried list: <code>docs/FIRMWARE-CODEPATH.md</code>. Generated by <code>analysis-2020accord/figures/codepath/make_codepath_page.py</code>; every diagram is laid out from computed box geometry.</p>

<script>
(function(){{
  document.querySelectorAll('svg[data-chart]').forEach(function(svg){{
    var cfg=JSON.parse(document.getElementById(svg.dataset.chart).textContent);
    var hov=svg.querySelector('.hover'),xh=hov.querySelector('.xh'),tt=hov.querySelector('.tt'),tx=hov.querySelector('.ttx');
    function pt(ev){{var r=svg.getBoundingClientRect();var vb=svg.viewBox.baseVal;return {{x:(ev.clientX-r.left)*vb.width/r.width,y:(ev.clientY-r.top)*vb.height/r.height}};}}
    svg.addEventListener('mousemove',function(ev){{
      var p=pt(ev);if(p.x<cfg.L||p.x>cfg.L+cfg.pw){{hov.hidden=true;return;}}
      var xv=cfg.x0+(p.x-cfg.L)/cfg.pw*(cfg.x1-cfg.x0);var lines=[];
      cfg.s.forEach(function(s){{var best=null;s.pts.forEach(function(q){{if(best===null||Math.abs(q[0]-xv)<Math.abs(best[0]-xv))best=q;}});if(best)lines.push(s.label.split(' (')[0].slice(0,34)+': '+(+best[1].toFixed(2)));}});
      hov.hidden=false;xh.setAttribute('x1',p.x);xh.setAttribute('x2',p.x);
      tx.textContent='';var y0=cfg.T+12;var w=0;
      lines.unshift('x = '+(+xv.toFixed(2)));
      lines.forEach(function(l,i){{var t=document.createElementNS('http://www.w3.org/2000/svg','tspan');t.setAttribute('x',0);t.setAttribute('dy',i?13:0);t.textContent=l;tx.appendChild(t);w=Math.max(w,l.length*6.2);}});
      var left=p.x+10+w>cfg.L+cfg.pw;var bx=left?p.x-14-w:p.x+10;
      tt.setAttribute('x',bx-4);tt.setAttribute('y',y0-11);tt.setAttribute('width',w+8);tt.setAttribute('height',lines.length*13+6);
      tx.setAttribute('transform','translate('+bx+','+y0+')');
    }});
    svg.addEventListener('mouseleave',function(){{hov.hidden=true;}});
  }});
}})();
</script>
"""
out = os.path.join(KIT, "docs", "FIRMWARE-CODEPATH.html")
open(out, "w", encoding="utf-8").write(PAGE)
print("wrote", out, "%.1f KB" % (os.path.getsize(out)/1024), "in %.1f s" % (time.time()-t0))
COLL = sum(len(d.check(n)) for d, n in ((A, "flow A"), (Bd, "flow B"), (L, "loop"), (F, "fork")))
assert COLL == 0, "diagram collisions"
print("diagram widths (viewBox px): A %d x %d, B %d x %d, loop %d x %d, fork %d x %d" % (A.W, A.H, Bd.W, Bd.H, L.W, L.H, F.W, F.H))
print("widest unbreakable token per wrapping table:", {k: (v.encode("ascii", "replace").decode(), len(v)) for k, v in WIDEST.items()})
