# -*- coding: utf-8 -*-
"""Generate the 2026-09-09 close-out artifact (V289 flew; V290 pending adjudication).
Every number on the page comes from one of these files, each produced from the built images or the wire caches:
  _scratch/out/v290_closeout_delta.json      (v290_closeout_delta_from_images.py: cells, banks, byte diffs, sha256)
  _scratch/out/v290_closeout_marks.json      (v290_closeout_bookmark_timelines.py: band envelopes around each bookmark)
  rlog-tools/studies/grind/_scratch/v290page_psd.json  (pooled Welch PSD per route, marks62's crux recipe)
  _scratch/out/h1_figdata_2026-09-09.json    (h1fig2: map staircase, step/LSB, |dcmd| histograms, amplitude budget)
  _scratch/out/v289_page_data.json           (lerps: fb-lag / notch curves decoded from the V289 image)
  _scratch/out/ledger_v38_to_v289.json       (ledger_v38_to_v289_bytes.py: 26 images)
plus numbers quoted from the named study reports (marked on the page).  Output: _scratch/out/artifact_v290_closeout_2026-09-09.html"""
import json, math, os, cmath
KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPO = os.path.abspath(os.path.join(KIT, ".."))
OUTD = os.path.join(KIT, "_scratch", "out")
OUT = os.path.join(OUTD, "artifact_v290_closeout_2026-09-09.html")
J = lambda p: json.load(open(p, encoding="utf-8"))
DELTA = J(os.path.join(OUTD, "v290_closeout_delta.json"))
MARKS = J(os.path.join(OUTD, "v290_closeout_marks.json"))
PSD = J(os.path.join(REPO, "rlog-tools", "studies", "grind", "_scratch", "v290page_psd.json"))
H1 = J(os.path.join(OUTD, "h1_figdata_2026-09-09.json"))
P289 = J(os.path.join(OUTD, "v289_page_data.json"))
LED = J(os.path.join(OUTD, "ledger_v38_to_v289.json"))
# ---- section 5 inputs (the V290 adjudication) ----
GR = os.path.join(REPO, "rlog-tools", "studies", "grind", "_scratch")
S5 = J(os.path.join(OUTD, "v290_closeout_s5_demand.json"))          # v290_closeout_s5_demand_hist.py: demand-index histograms off the wire
DOSE = J(os.path.join(GR, "basepick_delivered_dose.json"))          # basepick_delivered_dose.py: every column at the DELIVERED Kd
POLES = J(os.path.join(GR, "basepick_v290_table.json"))["table"]    # basepick_v290.py table: closed-loop pole census, 87 burst-consistent fits
PLACE = J(os.path.join(GR, "reconcile_v290_table.json"))["table"]   # reconcile_v290.py: the forward-vs-feedback placement pair

# plain-image census (denominator for "N images" prose) — counted at render time so it can't drift
FW_ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", os.path.join(REPO, "..", "accord-firmwares"))
_fw_dir = os.path.join(FW_ROOT, "analysis-2020accord")
PLAIN_IMAGE_COUNT = len([f for f in os.listdir(_fw_dir) if f.endswith("_plain_image.bin")]) if os.path.isdir(_fw_dir) else None

# V288/V282 bookmark f0 marks (V289-MARKS-R62-R63-2026-09-09.md §2, "like for like" table) — no JSON for this
# report exists, so the range is computed here from the quoted per-mark f0 values rather than hand-typed as a range.
_V288_V282_MARK_F0 = {"V288 m1": 19.73, "V288 m2": 20.04, "V288 m3": 18.85, "V282 r39 m1": 20.09, "V282 r39 m2": 20.08}
MARK_F0_LO, MARK_F0_HI = min(_V288_V282_MARK_F0.values()), max(_V288_V282_MARK_F0.values())
MARK_F0_N = len(_V288_V282_MARK_F0)

# ------------------------------------------------------------------ svg helpers
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class Chart:
    """one-scale line/step/bar chart; x linear or log; y linear or log; theme via CSS classes"""
    def __init__(self, w=560, h=260, L=54, R=14, T=16, Bm=38, xlog=False, ylog=False, title=""):
        self.w, self.h, self.L, self.R, self.T, self.B = w, h, L, R, T, Bm
        self.xlog, self.ylog, self.title = xlog, ylog, title
        self.s = []
    def scales(self, x0, x1, y0, y1):
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        return self
    def X(self, v):
        a, b = (math.log10(self.x0), math.log10(self.x1)) if self.xlog else (self.x0, self.x1)
        vv = math.log10(max(v, 1e-12)) if self.xlog else v
        return self.L + (self.w - self.L - self.R) * (vv - a) / (b - a)
    def Y(self, v):
        a, b = (math.log10(self.y0), math.log10(self.y1)) if self.ylog else (self.y0, self.y1)
        vv = math.log10(max(v, 1e-12)) if self.ylog else v
        vv = max(a, min(b, vv))
        return (self.h - self.B) - (self.h - self.B - self.T) * (vv - a) / (b - a)
    def axes(self, xticks, yticks, xlabel, ylabel, xfmt=str, yfmt=str):
        s = self.s; yb, yt = self.h - self.B, self.T; xl, xr = self.L, self.w - self.R
        for v in xticks:
            x = self.X(v); s.append(f'<line class="grid" x1="{x:.1f}" y1="{yt}" x2="{x:.1f}" y2="{yb}"/><text x="{x:.1f}" y="{yb+14}" text-anchor="middle">{xfmt(v)}</text>')
        for v in yticks:
            y = self.Y(v); s.append(f'<line class="grid" x1="{xl}" y1="{y:.1f}" x2="{xr}" y2="{y:.1f}"/><text x="{xl-6}" y="{y+3.5:.1f}" text-anchor="end">{yfmt(v)}</text>')
        s.append(f'<line class="ax" x1="{xl}" y1="{yb}" x2="{xr}" y2="{yb}"/><line class="ax" x1="{xl}" y1="{yt}" x2="{xl}" y2="{yb}"/>')
        s.append(f'<text x="{(xl+xr)/2:.0f}" y="{self.h-4}" text-anchor="middle">{esc(xlabel)}</text>')
        s.append(f'<text transform="translate(12 {(yt+yb)/2:.0f}) rotate(-90)" text-anchor="middle">{esc(ylabel)}</text>')
        return self
    def vline(self, x, cls="mark", label=None, dy=0):
        xx = self.X(x); self.s.append(f'<line class="{cls}" x1="{xx:.1f}" y1="{self.T}" x2="{xx:.1f}" y2="{self.h-self.B}"/>')
        if label: self.s.append(f'<text class="{cls}t" x="{xx+4:.1f}" y="{self.T+10+dy}">{esc(label)}</text>')
        return self
    def hline(self, y, cls="mark", label=None):
        yy = self.Y(y); self.s.append(f'<line class="{cls}" x1="{self.L}" y1="{yy:.1f}" x2="{self.w-self.R}" y2="{yy:.1f}"/>')
        if label: self.s.append(f'<text class="{cls}t" x="{self.w-self.R-4}" y="{yy-4:.1f}" text-anchor="end">{esc(label)}</text>')
        return self
    def band(self, xa, xb, cls="bandfill"):
        self.s.append(f'<rect class="{cls}" x="{self.X(xa):.1f}" y="{self.T}" width="{self.X(xb)-self.X(xa):.1f}" height="{self.h-self.B-self.T}"/>')
        return self
    def line(self, xs, ys, cls, width=2, dash=None, step=False):
        pts = []; last = None
        for x, y in zip(xs, ys):
            if y is None or (self.ylog and y <= 0) or (self.xlog and x <= 0): continue
            if x < self.x0 or x > self.x1: continue
            px, py = self.X(x), self.Y(y)
            if step and last is not None: pts.append(f"{px:.1f},{last:.1f}")
            pts.append(f"{px:.1f},{py:.1f}"); last = py
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.s.append(f'<polyline class="{cls}" fill="none" stroke-width="{width}"{d} points="{" ".join(pts)}"/>')
        return self
    def dots(self, xs, ys, cls, r=3):
        for x, y in zip(xs, ys):
            self.s.append(f'<circle class="{cls}" cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" r="{r}"/>')
        return self
    def bars(self, xs, ys, cls, wpx):
        yb = self.h - self.B
        for x, y in zip(xs, ys):
            if y is None or (self.ylog and y <= 0): continue
            py = self.Y(y); self.s.append(f'<rect class="{cls}" x="{self.X(x)-wpx/2:.1f}" y="{py:.1f}" width="{wpx:.2f}" height="{yb-py:.1f}"/>')
        return self
    def text(self, x, y, t, cls="", anchor="start"):
        self.s.append(f'<text class="{cls}" x="{self.X(x):.1f}" y="{self.Y(y):.1f}" text-anchor="{anchor}">{esc(t)}</text>'); return self
    def rawtext(self, px, py, t, cls="", anchor="start"):
        self.s.append(f'<text class="{cls}" x="{px:.1f}" y="{py:.1f}" text-anchor="{anchor}">{esc(t)}</text>'); return self
    def svg(self):
        return f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(self.title)}">' + "\n".join(self.s) + "</svg>"

def fig(svg, caption, legend=None, cls=""):
    lg = f'<div class="legend">{legend}</div>' if legend else ""
    return f'<figure class="{cls}">{svg}{lg}<figcaption>{caption}</figcaption></figure>'

def leg(*items):  # (cls, label)
    return "".join(f'<span class="{c}">{esc(l)}</span>' for c, l in items)

EV = '<span class="tag ev">EVIDENCE</span>'; BEL = '<span class="tag bel">BELIEF</span>'; MOD = '<span class="tag bel">MODEL</span>'
QUO = '<span class="tag quo">QUOTED</span>'

# ------------------------------------------------------------------ filters from the decoded cells (1 kHz tick, BELIEF per the record)
FS = 1000.0
def Hz(f, num, den):  # polynomial in z^-1
    z = cmath.exp(-2j * math.pi * f / FS)
    return sum(c * z**i for i, c in enumerate(num)) / sum(c * z**i for i, c in enumerate(den))
def fb_lag(a, b): return lambda f: Hz(f, [b / 1024, b / 1024], [1, -a / 1024])
def out_lag(a=992, b=507): return lambda f: Hz(f, [b / 1024, b / 1024], [1, -a / 1024])
NC = P289["notch_coeffs_decoded"]
def notch(f): return Hz(f, [NC["b0"] / 16384, NC["b1"] / 16384, NC["b2"] / 16384], [1, NC["a1"] / 16384, NC["a2"] / 16384])
def deg(c): return math.degrees(cmath.phase(c))
def db(x): return 20 * math.log10(max(abs(x), 1e-9))
fb282 = fb_lag(923, 1560); fb289 = fb_lag(875, 2301); olag = out_lag()

# Option C's notch: 21.5 Hz Q1.5, the Q14 integers a build would round to (basepick §5; identical to the
# coefficients instr290's telemetry rungs are written against — DESIGN-V290-TELEMETRY §2).
CN = {"b0": 15680, "b1": -31074, "b2": 15680, "a1": -31074, "a2": 14976}
def notchC(f): return Hz(f, [CN["b0"] / 16384, CN["b1"] / 16384, CN["b2"] / 16384], [1, CN["a1"] / 16384, CN["a2"] / 16384])

def fb_at(fhz):
    """the (a, b) pair for a two-sample-sum lag pole at fhz that HOLDS the DC gain at V282's 30.891.
    Rule validated against both real cells: 16.53 Hz -> (923, 1560) and 25.03 Hz -> (875, 2301), the exact
    bytes in the V282 and V289 images. Option C specifies a 40 Hz pole; this is what that costs in cells."""
    a = round(1024 * math.exp(-2 * math.pi * fhz / FS))
    dc = 2 * 1560 / (1024 - 923)
    return a, round(dc * (1024 - a) / 2)
FB40_A, FB40_B = fb_at(40.0)
fb40 = fb_lag(FB40_A, FB40_B)

# ------------------------------------------------------------------ section 1: PSD figure
def psd_panel(field, ylabel, title):
    c = Chart(560, 270, xlog=False, ylog=True, title=title).scales(10, 30, 0.3, 40)
    c.band(13, 17.5, "bandA").band(18, 22.5, "bandB")
    c.axes([10, 15, 20, 25, 30], [0.5, 1, 2, 5, 10, 20], "Hz (pooled Welch, engaged runs >= 4 s, nperseg 512)", ylabel, yfmt=lambda v: f"x{v:g}")
    order = [("r39", "v282"), ("r3a", "v282b"), ("r3c", "v282b"), ("r5e_v288", "v288"), ("r62_v289", "v289"), ("r63_v289", "v289b")]
    for tag, cls in order:
        r = PSD[tag]; c.line(r["f"], r[field], cls, width=2 if cls in ("v289", "v289b", "v282", "v288") else 1.2)
    c.rawtext(c.X(15.2), c.T + 12, "13–17.5 Hz", "bandt"); c.rawtext(c.X(20.2), c.T + 12, "18–22.5 Hz", "bandt")
    return c.svg()

def psd_ratio_table():
    rows = []
    for tag, build in (("r39", "V282"), ("r3a", "V282"), ("r3c", "V282"), ("r5e_v288", "V288 r2"), ("r62_v289", "V289 r1"), ("r63_v289", "V289 r1")):
        r = PSD[tag]; f = r["f"]
        def pk(arr, lo, hi):
            m = [(v, ff) for v, ff in zip(arr, f) if lo <= ff <= hi]; v, ff = max(m); return ff, v
        def power(arr, lo, hi):
            return sum(v for v, ff in zip(arr, f) if lo <= ff <= hi)
        fa, va = pk(r["wire"], 13, 17.5); fb, vb = pk(r["wire"], 18, 22.5)
        ratio = power(r["wire"], 13, 17.5) / power(r["wire"], 18, 22.5)
        fba, vba = pk(r["bar"], 13, 17.5); fbb, vbb = pk(r["bar"], 18, 22.5)
        hl = ' class="hl"' if "v289" in tag else ""
        rows.append(f"<tr{hl}><td class='mono'>{tag}</td><td>{build}</td><td>{r['engaged_s']:.0f}</td><td>{fa:.2f} Hz ×{va:.1f}</td><td>{fb:.2f} Hz ×{vb:.1f}</td><td><b>{ratio:.2f}</b></td><td>{fba:.2f} Hz ×{vba:.1f}</td><td>{fbb:.2f} Hz ×{vbb:.1f}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>route</th><th>build</th><th>engaged s</th><th>wheel rate: peak 13–17.5 Hz</th><th>peak 18–22.5 Hz</th><th>power 13–17.5 : 18–22.5</th>"
            "<th>bar: peak 13–17.5 Hz</th><th>peak 18–22.5 Hz</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

# ------------------------------------------------------------------ section 1: bookmark timelines
def mark_panel(key, mi, label):
    m = MARKS[key]["marks"][mi]; t = m["t_rel"]
    ymax = 1500
    c = Chart(560, 230, L=50, R=14, T=16, Bm=36, title=f"{label}: bar band envelopes before the press").scales(-25, 3, 0, ymax)
    c.axes([-25, -20, -15, -10, -5, 0], [0, 500, 1000, 1500], "seconds before the operator's bookmark (0 = press)", "bar envelope (raw × 1.024)")
    c.vline(0, "markline")
    # capped-frame shading (fraction >= 0.5 in the 20 Hz bin)
    for tt, cp in zip(t, m["cap"]):
        if cp >= 0.5: c.s.append(f'<rect class="capfill" x="{c.X(tt)-1.4:.1f}" y="{c.T}" width="2.8" height="{c.h-c.B-c.T}"/>')
    c.line(t, m["b5_12"], "s7", 1.6).line(t, m["b13_18"], "s16", 2.2).line(t, m["b18_22"], "s20", 2.2)
    for k, cls in (("b5_12", "s7t"), ("b13_18", "s16t"), ("b18_22", "s20t")):
        c.rawtext(c.X(m[k + "_pk_t"]) + 3, c.Y(min(m[k + "_pk"], ymax)) - 3, f"{m[k+'_pk']:.0f} @ {m[k+'_pk_t']:+.1f} s", cls)
    return c.svg()

# ------------------------------------------------------------------ section 2: notch curves + phase budget
def notch_curves():
    fs = [10 ** (math.log10(3) + i * (math.log10(60) - math.log10(3)) / 240) for i in range(241)]
    c = Chart(560, 260, xlog=True, title="Notch N and the notched-out path 1−N, magnitude").scales(3, 60, -50, 8)
    c.band(16.98, 23.64, "bandB")
    c.axes([3, 5, 10, 16.5, 20, 30, 50], [0, -3, -10, -20, -30, -40, -50], "Hz (log)", "dB")
    c.line(fs, [db(notch(f)) for f in fs], "v289", 2).line(fs, [db(1 - notch(f)) for f in fs], "s16", 2, dash="5 3")
    c.vline(16.5, "line16", "16.5 Hz: the new line", 0).vline(20.3, "line20", "20.3 Hz", 14)
    p = Chart(560, 260, xlog=True, title="Notch N and 1−N, phase").scales(3, 60, -100, 100)
    p.band(16.98, 23.64, "bandB")
    p.axes([3, 5, 10, 16.5, 20, 30, 50], [-90, -45, 0, 45, 90], "Hz (log)", "phase (deg)")
    p.line(fs, [deg(notch(f)) for f in fs], "v289", 2).line(fs, [deg(1 - notch(f)) for f in fs], "s16", 2, dash="5 3")
    p.vline(16.5, "line16").vline(20.3, "line20")
    return c.svg(), p.svg()

def budget_table():
    rows = []
    for f in (16.5, 20.3):
        items = [
            ("fb lag pole 0xC63E8/EA (two-sample sum)", deg(fb282(f)), deg(fb289(f)), EV),
            ("output lag 0xC63EC/EE (two-sample sum, >>5)", deg(olag(f)), deg(olag(f)), EV),
            ("notch cave 0xC4C00 (V289 only)", 0.0, deg(notch(f)), EV),
            ("one 1 kHz tick", -360 * f / FS, -360 * f / FS, BEL),
        ]
        for name, a, b, tag in items:
            rows.append(f"<tr><td>{f} Hz</td><td>{name}</td><td>{a:+.1f}°</td><td>{b:+.1f}°</td><td>{b-a:+.1f}°</td><td>{tag}</td></tr>")
        n = notch(f)
        rows.append(f"<tr class='sub'><td>{f} Hz</td><td>notch |N| / |1−N|</td><td>—</td><td>{db(n):+.1f} dB / {db(1-n):+.1f} dB</td><td>|N| = {abs(n):.3f}</td><td>{EV}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>f</th><th>element (from the image cells)</th><th>V282 phase</th><th>V289 phase</th><th>Δ</th><th>grade</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")

# ------------------------------------------------------------------ section 3: H1 figures
MC = H1["map_curves"]; SP = H1["step_per_lsb"]; WD = H1["wire_dcmd"]; AB = H1["amplitude_budget"]; RT = H1["record_table"]
# residual-vs-torque ratio, band_from_spec_median method (same recipe the h1_budget() captions above use) —
# computed here so the §3 synthesis paragraph can quote it by the SAME method instead of a differently-derived number
_BSM_RATIO_GRIND = {tag: AB[tag]["strata"]["grind"]["band_from_spec_median"]["T"] / AB[tag]["strata"]["grind"]["band_from_spec_median"]["q6"] for tag in ("r39", "r5e_v288")}
BSM_RATIO_LO, BSM_RATIO_HI = min(_BSM_RATIO_GRIND.values()), max(_BSM_RATIO_GRIND.values())
def h1_map():
    st, v6 = MC["builds"]["stock"], MC["builds"]["V282"]
    c = Chart(560, 280, title="Assist map, stock vs 6x linear: setpoint vs 0xE4 command with the index staircase").scales(0, 4096, 0, 140)
    c.axes([0, 1024, 2048, 3072, 4096], [0, 25, 50, 75, 100, 125], "0xE4 steer command (raw counts, 0–4096)", "rate setpoint (deg/s)")
    for b, cls in ((st, "stock"), (v6, "v289")):
        xs, ys = [], []
        for lo, hi, y in zip(b["stair_cmd_lo"], b["stair_cmd_hi"], b["stair_sp_degs"]):
            xs += [lo, hi]; ys += [y, y]
        c.line(xs, ys, cls, 1.6)
        c.dots(b["knot_cmd"], b["knot_sp_degs"], cls + "d", 3.2)
    c.rawtext(c.X(2500), c.Y(122), "V282 / V289 (6x linear, slope 4.30 sp/idx)", "v289t")
    c.rawtext(c.X(2500), c.Y(35), "stock (saturating, top 172 sp)", "stockt")
    c.rawtext(c.X(60), c.Y(133), "dots = the 10 LERP knots (same X on every image)", "muted")
    # zoom inset: 0..400 counts
    z = Chart(560, 200, title="zoom: the first 400 counts").scales(0, 400, 0, 16)
    z.axes([0, 100, 200, 300, 400], [0, 4, 8, 12, 16], "0xE4 command (raw counts) — one index LSB = 16.13 counts", "setpoint (deg/s)")
    for b, cls in ((st, "stock"), (v6, "v289")):
        xs, ys = [], []
        for lo, hi, y in zip(b["stair_cmd_lo"][:26], b["stair_cmd_hi"][:26], b["stair_sp_degs"][:26]):
            xs += [lo, hi]; ys += [y, y]
        z.line(xs, ys, cls, 2, step=False)
        z.line(b["cont_cmd"][:101], b["cont_sp_degs"][:101], cls, 1, dash="3 3")
    z.vline(122.88, "capline", "slew cap 123 counts/frame = 7.6 LSB")
    return c.svg(), z.svg()

def h1_step():
    c = Chart(560, 250, title="Setpoint step per index LSB, stock vs 6x, per knot interval").scales(0, 240, 0, 0.75)
    c.axes([0, 60, 120, 180, 240], [0, 0.25, 0.5, 0.75], "index (0–240); each tread is one knot interval of the map", "deg/s per index LSB (interval mean)")
    for key, cls in (("V282", "v289"), ("stock", "stock")):
        xs, ys = [], []
        for iv in SP["per_interval"]:
            xs += [iv["idx_lo"], iv["idx_hi"]]; ys += [iv[key]["dsp_degs"], iv[key]["dsp_degs"]]
        c.line(xs, ys, cls, 2.2)
    ms = SP["builds"]["stock"]["step_multiset"]; m6 = SP["builds"]["V282"]["step_multiset"]
    c.rawtext(c.X(120), c.Y(0.70), f"6x: every index step is 4 or 5 sp counts ({m6.get('4')} + {m6.get('5')} of 240) — never stalls", "v289t", "middle")
    c.rawtext(c.X(120), c.Y(0.40), f"stock: {ms.get('0')} of 240 index steps move the setpoint by ZERO (steps of 0/1/2/3 counts)", "stockt", "middle")
    return c.svg()

def h1_hist():
    out = []
    for tag, label in (("r39", "r39 (V282, 79 episodes)"), ("r5e_v288", "r5e (V288 r2, 46 episodes)")):
        w = WD[tag]; g = w["strata"]["grind"]; q = w["strata"]["quiet"]
        xs = list(range(0, 201))
        c = Chart(560, 250, ylog=True, title=f"|Δcmd| per 100 Hz frame, grinding vs quiet, {label}").scales(0, 200, 1e-4, 0.3)
        c.axes([0, 50, 100, 122.88, 150, 200], [1e-4, 1e-3, 1e-2, 1e-1], "|Δ 0xE4 command| between consecutive frames (raw counts; last bin = ≥200)", "fraction of frames",
               xfmt=lambda v: "cap 123" if v == 122.88 else f"{v:g}")
        c.line(xs, q["hist"], "quiet", 1.6).line(xs, g["hist"], "grind", 1.8)
        c.vline(122.88, "capline")
        c.rawtext(c.X(4), c.Y(0.2), f"±1 alternation p50: grind {g['alt_frac']['p50']:.3f} · quiet {q['alt_frac']['p50']:.3f}", "muted")
        c.rawtext(c.X(4), c.Y(0.11), f"100 ms on exactly two cmd values: grind {g['two_c']['p50']:.3f} · quiet {q['two_c']['p50']:.3f}", "muted")
        c.rawtext(c.X(4), c.Y(0.06), f"frames that change: grind {g['chg_frac']['p50']:.3f} · quiet {q['chg_frac']['p50']:.3f}", "muted")
        c.rawtext(c.X(126), c.Y(0.2), f"capped: grind {g['hist_pooled_groups']['cap_ge122']:.3f} · quiet {q['hist_pooled_groups']['cap_ge122']:.3f}", "capt")
        out.append((c.svg(), tag))
    return out

def h1_budget():
    out = []
    for tag, label in (("r39", "r39 (V282)"), ("r5e_v288", "r5e (V288 r2)")):
        a = AB[tag]; f100 = a["f100"]; f50 = a["f50"]; g = a["strata"]["grind"]; q = a["strata"]["quiet"]
        c = Chart(560, 290, ylog=True, title=f"Amplitude budget at the line: quantisation residual vs delivered torque, {label}").scales(2, 50, 0.1, 300)
        c.band(18, 22, "bandB")
        c.axes([5, 10, 20, 30, 40, 50], [0.1, 1, 10, 100], "Hz (0.5 Hz bins; the 427 tap is a 50 Hz stream and is drawn only to 25 Hz)", "median amplitude per bin (output torque counts)")
        c.line(f100, q["spec_median"]["q6"], "quiet", 1.4, dash="4 3").line(f100, g["spec_median"]["q6"], "grind", 1.8, dash="4 3")
        c.line(f50, q["specT_median"], "quiet", 1.6).line(f50, g["specT_median"], "grind", 2.2)
        i20 = f50.index(20.0); j20 = f100.index(20.0)
        c.rawtext(c.X(20.6), c.Y(g["specT_median"][i20]) - 6, f"tap, grinding: {g['specT_median'][i20]:.1f}", "grindt")
        c.rawtext(c.X(20.6), c.Y(q["specT_median"][i20]) + 12, f"tap, quiet: {q['specT_median'][i20]:.1f}", "quiett")
        c.rawtext(c.X(20.6), c.Y(g["spec_median"]["q6"][j20]) - 6, f"residual: {g['spec_median']['q6'][j20]:.2f} (both strata)", "grindt")
        c.rawtext(c.X(26), c.Y(200), "solid = 427 torque tap · dashed = 6x map quantisation residual through P and gain", "muted")
        bt = g["band_from_spec_median"]; bq = q["band_from_spec_median"]
        out.append((c.svg(), tag, bt, bq))
    return out

def h1_signal_path():
    # 2 rows of boxes, quantiser highlighted
    boxes = [
        ("openpilot 0xE4", "100 Hz · 0..4096 raw · slew cap 123/frame", "box"),
        ("CAN decode", "S = −4·cmd · clamp ±16384", "box"),
        ("× taper × speedF", "255 × 255 (live arms) · & 0xFFFF", "box"),
        ("QUANTISER", "»16 »6 · |·| · clamp 240", "hot"),
        ("assist map LERP", "10 knots · 0xE502C · divq floors", "box"),
        ("setpoint sp", "1 count = 0.1295 deg/s", "box"),
        ("Σ  E = 32·sp − fb", "fb = two-sample sum, DC 30.89", "box"),
        ("P + D", "Kp 248 · Kd 128 · Ki 0", "box"),
        ("sum + fades · clamp ±15360", "0xC61BE", "box"),
        ("V289 notch cave", "20.04 Hz Q3 · 0xC4C00 (V289 only)", "cave"),
        ("output lag 5.05 Hz", "0xC63EC/EE", "box"),
        ("× gain »15 · clamp ±3072", "0xC6CD0 = 5346 · 0xC61B4", "box"),
        ("EME → FOC/PWM → motor", "0x18F wheel rate closes back on E", "box"),
    ]
    W, H, gap, per = 168, 58, 22, 5
    rows = [boxes[i:i + per] for i in range(0, len(boxes), per)]
    width = per * W + (per - 1) * gap + 20; height = len(rows) * (H + 46) + 40
    s = [f'<svg viewBox="0 0 {width} {height}" class="dg" role="img" aria-label="LKAS demand path from the 0xE4 command to the motor with the index quantiser highlighted">',
         '<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>']
    pos = {}
    for r, row in enumerate(rows):
        for k, (t1, t2, cls) in enumerate(row):
            x = 10 + k * (W + gap); y = 12 + r * (H + 46)
            pos[len(pos)] = (x, y)
            s.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{W}" height="{H}" rx="3"/>')
            s.append(f'<text x="{x+W/2}" y="{y+22}" text-anchor="middle" font-weight="600">{esc(t1)}</text><text class="sm" x="{x+W/2}" y="{y+40}" text-anchor="middle">{esc(t2)}</text>')
    n = len(boxes)
    for i in range(n - 1):
        x, y = pos[i]; x2, y2 = pos[i + 1]
        if y == y2: s.append(f'<path class="arrow" d="M{x+W} {y+H/2} H{x2}"/>')
        else: s.append(f'<path class="arrow" d="M{x+W/2} {y+H} V{y+H+23} H{x2+W/2} V{y2}"/>')
    qx, qy = pos[3]
    s.append(f'<text class="hott" x="{qx+W/2}" y="{qy-4}" text-anchor="middle">1 LSB = 16.13 raw counts — IDENTICAL on every build (0xC64F0 = 240 on all four images)</text>')
    s.append(f'<text class="sm" x="{qx+W/2}" y="{qy+H+14}" text-anchor="middle">sign-asymmetric near centre: idx 1 at cmd +1 vs −17 (sar = floor)</text>')
    # feedback arrow from motor back to Σ
    mx, my = pos[12]; sx, sy = pos[6]
    s.append(f'<path class="arrowfb" d="M{mx+W/2} {my+H} V{my+H+22} H{sx+W/2} V{sy+H}"/>')
    s.append(f'<text class="sm" x="{(mx+sx)/2+W/2}" y="{my+H+36}" text-anchor="middle">0x18F wheel rate → fb (the loop)</text>')
    s.append("</svg>")
    return "\n".join(s)

def h1_record_table():
    rows = "".join(f"<tr><td>{r['build']}</td><td>{esc(r['map'])}</td><td>{esc(r['Kp'])}</td><td>{r['f0']:.2f} [{r['f0_lo']:.2f}–{r['f0_hi']:.2f}]</td><td>{r['n']}</td><td><b>{r['presence_pct']:.1f} %</b></td></tr>" for r in RT["rows"])
    return ("<div class='tw'><table><thead><tr><th>build</th><th>map</th><th>Kp</th><th>f0 Hz [p10–p90]</th><th>n windows</th><th>presence</th></tr></thead><tbody>" + rows + "</tbody></table></div>")

# ------------------------------------------------------------------ section 4: delta table + LERPs
def delta_table():
    rows = []
    for s in DELTA["scalars"]:
        if not (s["changed_v282"] or s["changed_v289"]): continue
        cls = " class='hl'" if s["changed_v289"] else ""
        rows.append(f"<tr{cls}><td class='mono'>{s['addr']}</td><td>{s['stock']}</td><td>{s['V282']}</td><td>{'<b>'+str(s['V289'])+'</b>' if s['changed_v289'] else s['V289']}</td><td>{esc(s['what'])}</td><td>{esc(s['does'])}</td><td>{esc(s['introduced'])}</td></tr>")
    for c in DELTA["code"]:
        if c["stock"] == c["V282"] == c["V289"]: continue
        cls = " class='hl'" if c["V282"] != c["V289"] else ""
        rows.append(f"<tr{cls}><td class='mono'>{c['addr']}</td><td class='mono'>{c['stock']}</td><td class='mono'>{c['V282']}</td><td class='mono'>{'<b>'+c['V289']+'</b>' if c['V282']!=c['V289'] else c['V289']}</td><td>{esc(c['what'])}</td><td>code / instrument</td><td>—</td></tr>")
    bk = DELTA["banks"]
    for name, lab in (("assist_map_0xC9A88", "assist map slot 7, Y knots (X 0…240 unchanged)"), ("kp_0xCB994", "Kp slot 7, Y knots"), ("kd_0xCB7D4", "Kd slot 7, Y knots")):
        b = bk[name]
        if b["stock"]["Y"] != b["V282"]["Y"]:
            rows.append(f"<tr><td class='mono'>{name.split('_')[-1]}</td><td class='mono'>{b['stock']['Y']}</td><td class='mono'>{b['V282']['Y']}</td><td class='mono'>same as V282</td><td>{lab}</td><td>the rate-loop reference (map) / proportional gain schedule</td><td>V280 r2 (map) · V281 r3 (Kp)</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>address</th><th>stock</th><th>V282</th><th>V289</th><th>what it physically is</th><th>what it does</th><th>introduced</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

def lerp_plots():
    bk = DELTA["banks"]; degs = MC["sp_count_in_degs"]
    m = bk["assist_map_0xC9A88"]
    c = Chart(560, 250, title="Assist map slot 7, stock vs V282/V289, from the images").scales(0, 240, 0, 140)
    c.axes([0, 60, 120, 180, 240], [0, 25, 50, 75, 100, 125], "index (0–240; 1 idx = 16.13 raw 0xE4 counts)", "rate setpoint (deg/s)")
    c.line(m["stock"]["X"], [y * degs for y in m["stock"]["Y"]], "stock", 2).dots(m["stock"]["X"], [y * degs for y in m["stock"]["Y"]], "stockd", 3)
    c.line(m["V282"]["X"], [y * degs for y in m["V282"]["Y"]], "v289", 2).dots(m["V282"]["X"], [y * degs for y in m["V282"]["Y"]], "v289d", 3)
    c.rawtext(c.X(150), c.Y(100), "V282 = V289: linear to 1032 sp (133.6 deg/s)", "v289t"); c.rawtext(c.X(150), c.Y(30), "stock: saturating, top 172 sp (22.3 deg/s)", "stockt")
    k = bk["kp_0xCB994"]
    p = Chart(560, 220, title="Kp slot 7 vs index, stock vs V282/V289").scales(0, 240, 0, 800)
    p.axes([0, 68, 112, 136, 208, 240], [0, 248, 512, 696], "index", "Kp (E·Kp»8)")
    p.line(k["stock"]["X"], k["stock"]["Y"], "stock", 2).dots(k["stock"]["X"], k["stock"]["Y"], "stockd", 3)
    p.line(k["V282"]["X"], k["V282"]["Y"], "v289", 2).dots(k["V282"]["X"], k["V282"]["Y"], "v289d", 3)
    p.rawtext(p.X(120), p.Y(300), "V282/V289: flat 248 (KP.FLAT.Y0, V281 r3)", "v289t"); p.rawtext(p.X(80), p.Y(760), "stock: 248 → 696 rising with index", "stockt")
    d = bk["kd_0xCB7D4"]
    q = Chart(560, 200, title="Kd slot 7 vs index, all three images").scales(0, 32, 0, 200)
    q.axes([0, 11, 22, 32], [0, 64, 128, 192], "index", "Kd")
    q.line(d["stock"]["X"], d["stock"]["Y"], "stock", 4).line(d["V282"]["X"], d["V282"]["Y"], "v289", 2, dash="6 4")
    q.rawtext(q.X(16), q.Y(150), "128 flat on stock, V282 and V289 — never moved on the flight line (V287's 7680 D clamp was a different cell)", "muted", "middle")
    ts, to = bk["taper_same_0xCB924"], bk["taper_opp_0xCB8B4"]; fa = bk["fadeA_0xCBA04"]
    t = Chart(560, 220, title="Override taper arms and the post-PID fade, from the images").scales(0, 120, 0, 270)
    t.axes([0, 32, 42, 70, 80, 112], [0, 64, 128, 192, 255], "X (taper: |bar| /32 raw; fade: its own index)", "Y (/255)")
    t.line(ts["V282"]["X"], ts["V282"]["Y"], "v289", 2).dots(ts["V282"]["X"], ts["V282"]["Y"], "v289d", 3)
    t.line(to["V282"]["X"], to["V282"]["Y"], "s16", 2, dash="5 3").dots(to["V282"]["X"], to["V282"]["Y"], "s16d", 3)
    t.line(fa["V282"]["X"], fa["V282"]["Y"], "s7", 2).dots(fa["V282"]["X"], fa["V282"]["Y"], "s7d", 3)
    t.rawtext(t.X(2), t.Y(262), "taper same-sign 0xCB924 (solid) / opposite-sign 0xCB8B4 (dashed): 255 flat to X 80, 0 at 112 — the CLIFF", "muted")
    t.rawtext(t.X(2), t.Y(240), "post-PID fade 0xCBA04 (slot 7): 254 → 0 over X 70–80", "s7t")
    t.rawtext(t.X(2), t.Y(218), "stock == V282 == V289 for all four records (byte-identical)", "muted")
    return c.svg(), p.svg(), q.svg(), t.svg()

def delivered_table():
    """steady P-only torque at the sum node per command, from the image cells: T = clamp(sp·32·Kp/256 · gain/32768, ±out_clamp)"""
    im = H1["images"]; st, v6 = MC["builds"]["stock"], MC["builds"]["V282"]
    def T_of(build, key, cmd):
        b = MC["builds"][key]; i = min(range(len(b["stair_cmd_lo"])), key=lambda j: abs(b["stair_cmd_lo"][j] - cmd))
        sp = b["stair_sp"][i]; kp = im[build]["kp_Y"][0] if build != "stock" else None
        # stock Kp is a LERP 248..696 over index: use the knot value at this index (linear between kp_X knots)
        if build == "stock":
            kx, ky = im["stock"]["kp_X"], im["stock"]["kp_Y"]; idx = b["stair_idx"][i]
            kp = ky[-1]
            for a, bb in zip(range(len(kx) - 1), range(1, len(kx))):
                if kx[a] <= idx <= kx[bb]: kp = ky[a] + (ky[bb] - ky[a]) * (idx - kx[a]) / max(1, kx[bb] - kx[a]); break
        raw = sp * 32 * kp / 256 * im[build]["gain"] / 32768
        return sp, b["stair_sp_degs"][i], min(raw, im[build]["out_clamp"]), raw > im[build]["out_clamp"]
    rows = []
    for cmd in (256, 512, 1024, 2048, 3072, 4096):
        s_sp, s_d, s_T, s_c = T_of("stock", "stock", cmd); v_sp, v_d, v_T, v_c = T_of("V282", "V282", cmd)
        rows.append(f"<tr><td>{cmd}</td><td>{s_sp:.0f} sp / {s_d:.1f} deg/s</td><td>{s_T:.0f}{' (clamp 512)' if s_c else ''}</td><td>{v_sp:.0f} sp / {v_d:.1f} deg/s</td><td>{v_T:.0f}{' (clamp 3072)' if v_c else ''}</td><td>{v_T/max(s_T,1e-9):.1f}×</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>0xE4 command</th><th>stock setpoint</th><th>stock steady T (counts)</th><th>V282 / V289 setpoint</th><th>V282 / V289 steady T</th><th>ratio</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

# ------------------------------------------------------------------ section 6: cross-build matrix
def matrix():
    order = LED["order"]
    cols = "".join(f"<th class='rot'><span>{b}</span></th>" for b in order)
    rows = []
    for s in LED["scalars"]:
        vals = s["vals"]; stock = vals["STOCK"]
        if all(v == stock for v in vals.values()): continue
        cells = "".join(f"<td class='{'chg' if vals[b]!=stock else ''}'>{vals[b] if vals[b]!=stock else '·'}</td>" for b in order)
        rows.append(f"<tr><td class='mono'>{s['addr']}</td><td>{esc(s['label'])}</td>{cells}</tr>")
    for b in LED["banks"]:
        vals = b["vals"]; stock = vals["STOCK"]
        def short(v):
            if v == stock: return "·"
            if len(set(v)) == 1: return f"flat {v[0]}"
            return f"{v[0]}…{v[-1]}"
        cells = "".join(f"<td class='{'chg' if vals[x]!=stock else ''}'>{short(vals[x])}</td>" for x in order)
        rows.append(f"<tr><td class='mono'>{b['ptr']}</td><td>{esc(b['label'])} (stock {stock[0]}…{stock[-1]})</td>{cells}</tr>")
    return f"<div class='tw'><table class='matrix'><thead><tr><th>cell</th><th>what</th>{cols}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"

# ================================================================== section 5: the two objects
POLE_BY_KEY = {r["key"]: r for r in POLES}
DOSE_BY_TAG = {r["lab"].split()[0]: r for r in DOSE}
PLACE_BY_LAB = [(r["lab"].strip(), r) for r in PLACE]

def band_of(key, lo_hi):
    for c in POLE_BY_KEY[key]["census"]:
        if c["band"] == lo_hi: return c
    return None

POLE_ROWS = [("V282", "V282 as flown · the base being reverted to", "v282"),
             ("V289", "V289 rev 1 · on the car since 2026-09-08", "v289"),
             ("A'", "S′ · V282 + Kd (112,112,112,128)", "s7"),
             ("A", "S · V282 + Kd (96,96,96,128)", "s7"),
             ("C40", "C · V282 + fb-operand notch + fb 40 Hz", "s16"),
             ("D40", "D · C + the Kd schedule", "s16"),
             ("B", "B · V289 + the Kd schedule", "stock")]

MEASURED_POLE = {"V282": (19.96, 17.90, 20.28), "V289": (16.63, 16.30, 17.08)}

def pole_map():
    """one row per candidate; a dot at each band's median pole, area proportional to poles-per-fit."""
    n = len(POLE_ROWS)
    ROW = 48
    W, L, R, T, Bm = 620, 250, 16, 40, 44
    H = T + 24 + ROW * (n - 1) + 26 + Bm
    c = Chart(W, H, L=L, R=R, T=T, Bm=Bm, title="Closed-loop poles 12-30 Hz for every V290 candidate, 87 burst-consistent plant fits")
    c.scales(12, 30, 0, 1)
    ypos = lambda i: T + 24 + i * ROW          # rows are categories, not a scale
    c.band(15, 18, "bandA").band(18, 22, "bandB")
    c.axes([12, 15, 16.6, 18, 20, 22, 26, 30], [], "Hz — model closed-loop pole frequency", "")
    c.rawtext(c.X(16.5), T - 22, "the 16 Hz CROSSING", "s16t", "middle")
    c.rawtext(c.X(20.0), T - 22, "the 20 Hz PLANT MODE", "s20t", "middle")
    for i, (key, lab, cls) in enumerate(POLE_ROWS):
        y = ypos(i)
        c.s.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}"/>')
        head, tail = (lab.split(" · ", 1) + [""])[:2]
        c.rawtext(L - 10, y + 1, head, cls + "t", "end")
        if tail: c.rawtext(L - 10, y + 13, tail, "muted", "end")
        m = MEASURED_POLE.get(key)
        if m:
            f, lo, hi = m
            c.s.append(f'<line class="meas" x1="{c.X(f):.1f}" y1="{y-17:.1f}" x2="{c.X(f):.1f}" y2="{y+17:.1f}"/>')
            c.rawtext(L - 10, y + 25, f"measured {f:.2f} Hz, ζ 0.029", "meast", "end")
        for cc in POLE_BY_KEY[key]["census"]:
            f, frac, z = cc["f_med"], cc["frac"], cc["z_med"]
            if f < 12 or f > 30: continue
            live = z < 0.15                       # a resonance you could hear; z_med ~0.4-0.8 means "nothing rings there"
            r = 4 + 8 * math.sqrt(min(frac, 1.5) / 1.5)
            c.s.append(f'<circle class="{"polelive" if live else "poledead"}" cx="{c.X(f):.1f}" cy="{y:.1f}" r="{r:.1f}"/>')
            if live:
                c.rawtext(c.X(f), y - r - 4, f"ζ {z:.3f}", "polet", "middle")
                c.rawtext(c.X(f), y + r + 10, f"{frac:.2f}/fit", "muted", "middle")
    c.rawtext(L - 10, ypos(n - 1) + 40, "vertical bar = the MEASURED line on that build", "meast", "end")
    return c.svg()

def margin_ledger():
    """how much loop phase each element spends, frequency by frequency, against V282's measured 30 deg margin."""
    fs = [10 + i * 20 / 200 for i in range(201)]
    c = Chart(600, 300, T=18, Bm=40, title="Loop phase spent by each element, and V282's 30 deg margin at 16.63 Hz")
    c.scales(10, 30, -70, 25)
    c.band(15, 18, "bandA").band(18, 22, "bandB")
    c.axes([10, 13, 16.63, 20, 24, 30], [-60, -45, -30, -15, 0, 15], "Hz", "phase added to the loop (deg)",
           xfmt=lambda v: "16.63" if abs(v - 16.63) < .01 else f"{v:g}")
    c.hline(0, "zeroline")
    c.line(fs, [deg(notch(f)) for f in fs], "v289", 2.4)
    c.line(fs, [deg(notchC(f)) for f in fs], "s16", 2.4, dash="6 3")
    c.line(fs, [deg(fb289(f)) - deg(fb282(f)) for f in fs], "v282", 2)
    c.line(fs, [deg(fb40(f)) - deg(fb282(f)) for f in fs], "s7", 2, dash="4 3")
    c.line(fs, [deg(notch(f)) + deg(fb289(f)) - deg(fb282(f)) for f in fs], "net", 3)
    c.hline(-30, "budget", "V282's whole phase margin at the crossing: 30°")
    x0 = c.X(16.63)
    c.s.append(f'<line class="line16" x1="{x0:.1f}" y1="{c.T}" x2="{x0:.1f}" y2="{c.h-c.B}"/>')
    net = deg(notch(16.63)) + deg(fb289(16.63)) - deg(fb282(16.63))
    c.rawtext(x0 + 5, c.Y(net) + 4, f"V289 net at 16.63 Hz: {net:+.1f}°", "nett")
    c.rawtext(x0 + 5, c.Y(deg(notchC(16.63))) - 5, f"C's notch alone: {deg(notchC(16.63)):+.1f}°", "s16t")
    return c.svg()

def two_objects_diagram():
    return r'''
<svg viewBox="0 0 1180 400" class="dg" role="img" aria-label="The two objects: a 20 Hz plant mode the loop de-damps, and the 16 Hz gain crossing, and what a notch does to each">
<defs><marker id="ah3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>
<text x="14" y="20" font-weight="600">OBJECT 1 — the 20 Hz line: a plant mode, and the loop is what un-damps it</text>
<rect class="plant" x="14" y="34" width="196" height="70" rx="3"/><text x="112" y="58" text-anchor="middle">column / rack / motor</text><text class="sm" x="112" y="76" text-anchor="middle">a lightly damped mode at 19.9–20.1 Hz</text><text class="sm" x="112" y="91" text-anchor="middle">plant ζ on its own ≈ 0.05</text>
<path class="arrow" d="M210 69 H262"/><text class="sm" x="236" y="60" text-anchor="middle">rings</text>
<rect class="box" x="262" y="34" width="168" height="70" rx="3"/><text x="346" y="58" text-anchor="middle">rate loop, |L| ≈ 0.4–0.6</text><text class="sm" x="346" y="76" text-anchor="middle">feeds phase-lagged gain back</text><text class="sm" x="346" y="91" text-anchor="middle">into the mode: ζ 0.05 → 0.029</text>
<path class="arrowr" d="M346 104 V126 H112 V104"/>
<text class="sm" x="230" y="142" text-anchor="middle">de-damping — measured: ζ falls as Kp rises, f stays pinned 20.03–20.08 Hz across Kp 248→696</text>
<rect class="cave" x="470" y="34" width="230" height="70" rx="3"/><text x="585" y="58" text-anchor="middle" font-weight="600">V289's notch, 20.04 Hz Q3</text><text class="sm" x="585" y="76" text-anchor="middle">|N| = 0.011 (−39.3 dB) at 20 Hz</text><text class="sm" x="585" y="91" text-anchor="middle">the loop stops feeding the mode</text>
<path class="arrowf" d="M700 69 H744"/>
<rect class="ok" x="744" y="34" width="240" height="70" rx="3"/><text x="864" y="58" text-anchor="middle" font-weight="600">RESULT: the band is EMPTY</text><text class="sm" x="864" y="76" text-anchor="middle">0 of 1414 present V289 windows in 18–22 Hz</text><text class="sm" x="864" y="91" text-anchor="middle">prevalence ×34 down · the notch WORKED</text>
<line class="sep" x1="14" y1="168" x2="1166" y2="168"/>
<text x="14" y="196" font-weight="600">OBJECT 2 — the 16 Hz line: the loop's own gain crossing, which V282 already carried</text>
<rect class="box" x="14" y="210" width="230" height="82" rx="3"/><text x="129" y="234" text-anchor="middle">V282's loop at 16.63 Hz</text><text class="sm" x="129" y="252" text-anchor="middle">|L| = 1.13 at ∠ −150°</text><text class="sm" x="129" y="267" text-anchor="middle">→ 30° of phase margin</text><text class="sm" x="129" y="282" text-anchor="middle">quiet: nothing rings here on V282</text>
<path class="arrow" d="M244 251 H296"/>
<rect class="hot" x="296" y="210" width="248" height="82" rx="3"/><text x="420" y="234" text-anchor="middle" font-weight="600">the notch's SKIRT spends that margin</text><text class="sm" x="420" y="252" text-anchor="middle">V289 notch at 16.63 Hz: −41.6°</text><text class="sm" x="420" y="267" text-anchor="middle">fb pole 16.5 → 25 Hz gives back: +11.5°</text><text class="sm" x="420" y="282" text-anchor="middle">net −30.1° of the 30° available — all of it</text>
<path class="arrow" d="M544 251 H596"/>
<rect class="fail" x="596" y="210" width="252" height="82" rx="3"/><text x="722" y="234" text-anchor="middle" font-weight="600">the crossing goes marginal</text><text class="sm" x="722" y="252" text-anchor="middle">measured on r62/r63: 16.63 Hz, ζ 0.029</text><text class="sm" x="722" y="267" text-anchor="middle">bursts in trains, ~3× the envelope of the</text><text class="sm" x="722" y="282" text-anchor="middle">20 Hz line it replaced</text>
<path class="arrow" d="M848 251 H900"/>
<rect class="hot" x="900" y="210" width="266" height="82" rx="3"/><text x="1033" y="234" text-anchor="middle" font-weight="600">AND IT IS STRUCTURAL</text><text class="sm" x="1033" y="252" text-anchor="middle">any filter that kills loop gain at 20 Hz</text><text class="sm" x="1033" y="267" text-anchor="middle">drops the crossing into 15–17 Hz.</text><text class="sm" x="1033" y="282" text-anchor="middle">Option C re-creates it in 100 % of fits.</text>
<text class="sm" x="14" y="322">Measured ζ is 0.029 on V282 AND 0.029 on V289 (73 and 114 free-decay fits, demand-gated). The frequency moved; the damping did not.</text>
<text class="sm" x="14" y="340">The two objects are separated by an LKAS DEMAND gate, not by speed or amplitude: a third line at 12.4–13.8 Hz lives at idx &lt; 5, is identical on every build, and is road, not loop.</text>
<text class="sm" x="14" y="358">The plant point behind object 2 is EVIDENCE (∠ −80.3° ± 9.1, |G| 70.8e−3 deg/s per torque count, corroborated by the 427 tap to 4–8°). The plant point at 20 Hz is CONDITIONAL — do not size a build on it.</text>
<text class="sm" x="14" y="376">Sources: MODE-NATURE-V289-RECENSUS-2026-09-09.md §1, §3, §5e (modenat2, 11 routes, 14 678 windows) · V290-BASE-DECISION-2026-09-09.md §1 (basepick).</text>
</svg>'''

def placement_diagram():
    return r'''
<svg viewBox="0 0 1180 340" class="dg" role="img" aria-label="The same notch placed in the forward path versus on the feedback operand: identical return ratio, different command path">
<text x="14" y="20" font-weight="600">FORWARD placement — what V289 shipped (hook 0x2A174, cave 0xC4C00, filter on the clamped sum S)</text>
<rect class="box" x="14" y="34" width="120" height="52" rx="3"/><text x="74" y="55" text-anchor="middle">setpoint sp</text><text class="sm" x="74" y="72" text-anchor="middle">from the assist map</text>
<path class="arrow" d="M134 60 H176"/>
<circle class="box" cx="194" cy="60" r="17"/><text x="194" y="64" text-anchor="middle">Σ</text>
<path class="arrow" d="M211 60 H252"/>
<rect class="box" x="252" y="34" width="112" height="52" rx="3"/><text x="308" y="55" text-anchor="middle">P + D</text><text class="sm" x="308" y="72" text-anchor="middle">Kp 248 · Kd 128</text>
<path class="arrowf" d="M364 60 H406"/>
<rect class="cave" x="406" y="30" width="150" height="60" rx="3"/><text x="481" y="54" text-anchor="middle" font-weight="600">NOTCH N</text><text class="sm" x="481" y="72" text-anchor="middle">on S, inside fwd()</text>
<path class="arrow" d="M556 60 H598"/>
<rect class="box" x="598" y="34" width="128" height="52" rx="3"/><text x="662" y="55" text-anchor="middle">lag · gain · clamp</text><text class="sm" x="662" y="72" text-anchor="middle">→ motor → wheel</text>
<path class="arrowr" d="M662 86 V116 H194 V77"/>
<rect class="fb" x="330" y="96" width="180" height="40" rx="3"/><text x="420" y="121" text-anchor="middle">fb: two-sample sum + lag pole</text>
<rect class="hot" x="770" y="26" width="396" height="68" rx="3"/><text x="968" y="50" text-anchor="middle" font-weight="600">N is in the COMMAND path as well as the loop</text><text class="sm" x="968" y="69" text-anchor="middle">a capped 0xE4 step has to climb through the notch: capped-step peak rate</text><text class="sm" x="968" y="84" text-anchor="middle">pkR 0.805 median, 0.745 worst fit — the loss no calibration recovers</text>
<line class="sep" x1="14" y1="152" x2="1166" y2="152"/>
<text x="14" y="180" font-weight="600">FEEDBACK-OPERAND placement — option C (hook 0x28F4C, cave 0xC4C90, filter on the rate feedback)</text>
<rect class="box" x="14" y="194" width="120" height="52" rx="3"/><text x="74" y="215" text-anchor="middle">setpoint sp</text><text class="sm" x="74" y="232" text-anchor="middle">from the assist map</text>
<path class="arrow" d="M134 220 H176"/>
<circle class="box" cx="194" cy="220" r="17"/><text x="194" y="224" text-anchor="middle">Σ</text>
<path class="arrow" d="M211 220 H252"/>
<rect class="box" x="252" y="194" width="112" height="52" rx="3"/><text x="308" y="215" text-anchor="middle">P + D</text><text class="sm" x="308" y="232" text-anchor="middle">Kp 248 · Kd 128</text>
<path class="arrow" d="M364 220 H406"/>
<rect class="box" x="406" y="194" width="150" height="52" rx="3"/><text x="481" y="215" text-anchor="middle">lag · gain · clamp</text><text class="sm" x="481" y="232" text-anchor="middle">nothing added here</text>
<path class="arrow" d="M556 220 H598"/>
<rect class="box" x="598" y="194" width="128" height="52" rx="3"/><text x="662" y="215" text-anchor="middle">→ motor → wheel</text><text class="sm" x="662" y="232" text-anchor="middle">0x18F rate comes back</text>
<path class="arrowr" d="M662 246 V282 H556"/>
<rect class="cave" x="406" y="256" width="150" height="52" rx="3"/><text x="481" y="277" text-anchor="middle" font-weight="600">NOTCH N</text><text class="sm" x="481" y="294" text-anchor="middle">on the fb operand</text>
<path class="arrowr" d="M406 282 H194 V237"/>
<rect class="ok" x="770" y="186" width="396" height="68" rx="3"/><text x="968" y="210" text-anchor="middle" font-weight="600">Identical return ratio L = C·G·N — different command path</text><text class="sm" x="968" y="229" text-anchor="middle">poles, ζ, Ms, the 7 Hz gate and the noise ratio match to machine precision;</text><text class="sm" x="968" y="244" text-anchor="middle">pkR 0.971 / 0.928 instead of 0.814 / 0.670. The loop pays the phase; the driver does not.</text>
<text class="sm" x="14" y="326">🛑 V289's design scored the FEEDBACK row and the build shipped the FORWARD one. No blocker for the feedback placement is recorded anywhere in the design memo — it was a placement that was never revisited, not a trade that was made.</text>
</svg>'''

def placement_table():
    """PLACE is emitted as [FB row, its FORWARD twin] adjacent pairs; pair by position, never by label."""
    def row_html(r, show, cls):
        return (f"<tr class='{cls}'><td>{esc(show)}</td><td>{r['place']}</td><td>{r['S_z_w']:+.4f}</td><td>{r['S_z_med']:+.4f}</td>"
                f"<td>{r['S_Ms_w']:.2f}</td><td>{r['gate']:.4f}</td><td>{r['noise']:.2f}×</td>"
                f"<td><b>{r['S_pkR_med']:.3f}</b></td><td><b>{r['S_pkR_w']:.3f}</b></td><td>{r['S_t90_med']:.0f} ms</td></tr>")
    v289 = [r for r in PLACE if r["lab"].startswith("V289 as flown")][0]
    rows = [row_html(v289, "V289 rev 1 as flown — notch 20.04 Hz Q3 on the loop output", "")]
    pairs = []
    for i, r in enumerate(PLACE):
        if r["lab"].strip().startswith("advnull") and r["place"] == "feedback":
            twin = PLACE[i + 1]
            assert "FORWARD" in twin["lab"] and twin["place"] == "forward", twin["lab"]
            assert abs(twin["S_z_med"] - r["S_z_med"]) < 1e-12 and abs(twin["gate"] - r["gate"]) < 1e-12
            fb = "40" if "fb 40" in r["lab"] else "50"
            pairs.append((int(fb), r, twin))
    for fbhz, r, twin in sorted(pairs):
        c = " (option C)" if fbhz == 40 else ""
        rows.append(row_html(r, f"notch 21.5 Hz Q1.5 + fb pole {fbhz} Hz — FEEDBACK operand{c}", "hl"))
        rows.append(row_html(twin, "↳ the SAME element, forward-placed", "sub"))
    return ("<div class='tw'><table><thead><tr><th>candidate</th><th>where the filter sits</th><th>ζ worst</th><th>ζ median</th><th>Ms worst</th>"
            "<th>7 Hz gate</th><th>motor noise</th><th>capped-step pkR med</th><th>pkR worst</th><th>t90</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")

def candidate_table():
    rows = []
    def pole16(key):
        c = band_of(key, "15-18")
        if c is None or c["z_med"] > 0.15: return "<span class='ok'>none</span>"
        return f"<b class='bad'>{c['f_med']:.1f} Hz, ζ {c['z_med']:.3f}</b>, {c['frac']:.2f}/fit"
    def pole20(key):
        c = band_of(key, "18-22")
        if c is None: return "—"
        st = "emptied" if c["z_med"] > 0.10 else f"ζ {c['z_med']:.3f}"
        return f"{c['f_med']:.1f} Hz, {st}, {c['frac']:.2f}/fit"
    spec = [
        ("base", "V282", "V282 as flown — the base", "0", "—", "1.0028", "1.000 / 1.000", "V282", ""),
        ("S'", "A'", "S′ · V282 + Kd (112,112,112,128)", "6 cal + a cave for readability", "120.4", "1.0100", "0.995 / ≈0.99", "V282", "hl"),
        ("S", "A", "S · V282 + Kd (96,96,96,128)", "6 cal", "112.8", "1.0171", "0.990 / ≈0.98", "V282", ""),
        ("M1", "Ap", "M1 · V282 + Kd (96,96,112,128)", "6 cal", "113.8", "1.0139", "0.992 / —", "V282", ""),
    ]
    for tag, pkey, lab, byt, dose, gate, pkr, base, cls in spec:
        d = [r for r in DOSE if r["lab"].split()[0] == tag][0]
        ratio = DOSE[0]["ring_ms"] / d["ring_ms"]
        gk = "ok" if float(gate) <= 1.0100001 else "bad"
        dosecell = esc(dose) if tag == "base" else f"{esc(dose)} <span class='muted'>(×{d['kd289'] / 128:.3f})</span>"
        vs = "—" if tag == "base" else f"×{ratio:.2f}"
        rows.append(f"<tr class='{cls}'><td>{esc(lab)}</td><td>{esc(base)}</td><td>{esc(byt)}</td><td>{dosecell}</td>"
                    f"<td>{d['z_w']:+.4f}</td><td><b>{d['ring_ms']:.0f} ms</b> ({d['ring_cyc']:.1f} cyc)</td>"
                    f"<td>{vs}</td><td class='{gk}'>{gate}</td><td>{pkr}</td>"
                    f"<td>{pole16(pkey)}</td><td>{pole20(pkey)}</td></tr>")
    # option C and D: dose-independent (the notch acts on every episode), quoted from the same run
    cring = 387.0; dring = 321.0
    rows.append(f"<tr class='hl'><td>C · V282 + fb-operand notch 21.5 Q1.5 + fb 40 Hz</td><td>V282</td><td>4 cal + <b>cave</b>, 3 CRC trailers</td>"
                f"<td>n/a — acts on every episode</td><td>+0.0349</td><td><b>387 ms</b> (6.4 cyc)</td><td>×{DOSE[0]['ring_ms']/cring:.2f}</td>"
                f"<td class='ok'>1.0092</td><td><b class='bad'>0.971 / 0.928</b></td><td>{pole16('C40')}</td><td>{pole20('C40')}</td></tr>")
    rows.append(f"<tr><td>D · C + the Kd schedule (S)</td><td>V282</td><td>10 cal + cave</td><td>112.8 <span class='muted'>(×0.882)</span></td>"
                f"<td>+0.0453</td><td>321 ms (5.2 cyc)</td><td>×{DOSE[0]['ring_ms']/dring:.2f}</td><td class='bad'>1.0237</td><td class='bad'>0.963 / 0.92</td>"
                f"<td>{pole16('D40')}</td><td>{pole20('D40')}</td></tr>")
    rows.append(f"<tr class='sub'><td>B · <b>V289</b> + the Kd schedule — the only option that keeps the flown base</td><td>V289</td><td>6 cal</td><td>112.8</td>"
                f"<td>+0.0347</td><td>—</td><td>—</td><td class='bad'>1.012–1.020</td><td class='bad'>0.806 at every Kd</td>"
                f"<td>{pole16('B')}</td><td>{pole20('B')}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>option</th><th>base</th><th>cost</th><th>delivered Kd in grinding</th><th>ζ at the delivered dose</th>"
            "<th>ring to 10 %</th><th>vs V282</th><th>7 Hz gate<br><span class='th2'>≤ 1.010</span></th><th>capped-step pkR<br><span class='th2'>med / worst, ≥ 0.95</span></th>"
            "<th>16 Hz object</th><th>20 Hz object</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

def nominal_vs_delivered():
    q = [("S′  Y = (112,112,112,128)", 112, 360, 1.0377, 120.4, 448, 1.0100),
         ("S   Y = (96,96,96,128)", 96, 257, 1.0731, 112.8, 367, 1.0171)]
    rows = ""
    for l, n, nr, ng, d, dr, dg in q:
        gk = "ok" if dg <= 1.0100001 else "bad"
        rows += (f"<tr><td>{esc(l)}</td><td>{n}</td><td>{nr} ms</td><td class='bad'>{ng:.4f}</td><td><b>{d:.1f}</b></td>"
                 f"<td><b>{dr} ms</b></td><td class='{gk}'>{dg:.4f}</td>"
                 f"<td>improvement overstated <b>×{dr / nr:.2f}</b> · gate cost overstated <b>×{(ng - 1) / (dg - 1):.1f}</b></td></tr>")
    return ("<div class='tw'><table><thead><tr><th>record</th><th>nominal Kd (Y₀)</th><th>nominal ring</th><th>nominal 7 Hz gate</th>"
            "<th>DELIVERED Kd</th><th>DELIVERED ring</th><th>DELIVERED gate</th><th>size of the error</th></tr></thead><tbody>" + rows + "</tbody></table></div>")

def kd_lerp_fig():
    """delivered Kd vs demand index, with the MEASURED grinding-episode index histogram underneath."""
    R = S5["records"]; g = S5["pool"]["grind"]["v289"]; edges = S5["edges"]
    c = Chart(600, 250, L=54, R=16, T=18, Bm=30, title="Kd delivered against the demand index")
    c.scales(0, 240, 0, 140)
    c.axes([0, 11, 22, 32, 60, 120, 180, 240], [0, 32, 64, 96, 112, 128], "", "Kd (the D gain the loop actually uses)")
    c.band(0, 32, "bandKnot")
    for name, cls, w in (("base", "stock", 3), ("S'", "v289", 2.4), ("S", "s16", 2.2), ("M1", "s7", 2)):
        r = R[name]
        c.line(r["idx"], r["kd"], cls, w)
        c.dots(r["X"], r["Y"], cls + "d", 3.2)
    c.rawtext(c.X(120), c.Y(133), "base / V282 / V289: Kd 128 flat — every build on the flight line", "stockt", "middle")
    c.rawtext(c.X(150), c.Y(120), "above idx 32 EVERY schedule record is byte-identical to base", "muted", "middle")
    c.rawtext(c.X(2), c.Y(104), "S′ 112", "v289t"); c.rawtext(c.X(2), c.Y(88), "S 96 · M1 96", "s16t")
    h = Chart(600, 190, L=54, R=16, T=16, Bm=46, title="Where grinding actually sits on that axis")
    mx = max(g["frac"]) * 1.15
    h.scales(0, 240, 0, mx)
    h.axes([0, 11, 22, 32, 60, 120, 180, 240], [0, 0.05, 0.10, 0.15], "LKAS demand index (0–240) — the Kd record's own X axis",
           "share of grinding seconds", yfmt=lambda v: f"{v*100:.0f} %")
    h.band(0, 32, "bandKnot")
    xs = [(edges[i] + min(edges[i + 1], 245)) / 2 for i in range(len(edges) - 1)]
    h.bars(xs[:-1], g["frac"][:-1], "grindbar", (600 - 54 - 16) * 5 / 240 - 1)
    h.vline(32, "capline")
    h.rawtext(h.X(36), h.Y(mx * 0.92), f"{g['frac_gt32']*100:.0f} % of grinding seconds sit ABOVE the top knot, where the bytes are unchanged", "capt")
    h.rawtext(h.X(36), h.Y(mx * 0.80), f"grinding idx p10/p50/p90 = {g['p10']:.0f} / {g['p50']:.0f} / {g['p90']:.0f}   (n = {g['n']} samples = {g['secs']:.1f} s)", "muted")
    st, lk = S5["pool"]["step"]["all"], S5["pool"]["lock"]["all"]
    h.rawtext(h.X(36), h.Y(mx * 0.68), f"capped-step p50 {st['p50']:.0f} ({st['frac_gt32']*100:.0f} % above 32) · full-lock turn p50 {lk['p50']:.0f} ({lk['frac_gt32']*100:.0f} %) — the two authority yardsticks are protected by construction", "muted")
    return c.svg(), h.svg()

def frontier_fig():
    c = Chart(600, 320, L=58, R=18, T=18, Bm=42, title="The Kd-schedule frontier: ring time bought against 7 Hz gate spent")
    c.scales(0.999, 1.065, 240, 580)
    c.axes([1.00, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06], [250, 300, 350, 400, 450, 500, 550],
           "7 Hz strong-turn gate at the delivered dose (the operator's limit is 1.010)", "ring to 10 % at the delivered dose (ms)",
           xfmt=lambda v: f"{v:.3f}")
    yonly = sorted([r for r in DOSE if r["prot"]], key=lambda r: r["gate"])
    xrec = sorted([r for r in DOSE if not r["prot"]], key=lambda r: r["gate"])
    c.line([r["gate"] for r in yonly], [r["ring_ms"] for r in yonly], "v289", 2.2)
    c.dots([r["gate"] for r in yonly], [r["ring_ms"] for r in yonly], "v289d", 4)
    c.line([r["gate"] for r in xrec], [r["ring_ms"] for r in xrec], "s16", 2, dash="5 3")
    c.dots([r["gate"] for r in xrec], [r["ring_ms"] for r in xrec], "s16d", 4)
    c.vline(1.010, "capline")
    c.rawtext(c.X(1.0105), c.T + 12, "the operator's 7 Hz gate", "capt")
    c.rawtext(c.X(1.0105), c.T + 24, "everything right of this line FAILS", "capt")
    base, s0 = DOSE[0], [r for r in DOSE if r["lab"].startswith("S0")][0]
    c.hline(s0["ring_ms"], "budget", f"×{base['ring_ms']/s0['ring_ms']:.1f} — the class's ceiling at INFINITE dose (Kd = 0 below the knot)")
    for r in DOSE:
        nm = r["lab"].split()[0]
        if nm in ("base", "S'", "S", "M1", "S80", "S64", "S0", "X64", "X240"):
            c.rawtext(c.X(r["gate"]) + 6, c.Y(r["ring_ms"]) - 6, nm, "v289t" if r["prot"] else "s16t")
    return c.svg()

def notchC_fig():
    fs = [10 ** (math.log10(5) + i * (math.log10(60) - math.log10(5)) / 240) for i in range(241)]
    c = Chart(600, 250, xlog=True, T=16, Bm=40, title="Option C's notch against V289's, magnitude")
    c.scales(5, 60, -45, 6)
    c.band(15, 18, "bandA").band(18, 22, "bandB")
    c.axes([5, 10, 16.6, 21.5, 30, 50], [0, -10, -20, -30, -40], "Hz (log)", "dB", xfmt=lambda v: f"{v:g}")
    c.line(fs, [db(notch(f)) for f in fs], "v289", 2.2)
    c.line(fs, [db(notchC(f)) for f in fs], "s16", 2.2, dash="6 3")
    c.rawtext(c.X(6), c.Y(-36), f"at 16.6 Hz — V289 {db(notch(16.63)):.1f} dB / {deg(notch(16.63)):+.0f}°   ·   C {db(notchC(16.63)):.1f} dB / {deg(notchC(16.63)):+.0f}°", "muted")
    c.rawtext(c.X(6), c.Y(-41), "C's skirt at the crossing is WORSE, not better — it survives on PLACEMENT, not on shape", "muted")
    return c.svg()

# ------------------------------------------------------------------ loop diagram (section 2)
def loop_diagram():
    return r'''
<svg viewBox="0 0 1180 420" class="dg" role="img" aria-label="LKAS rate loop with the V289 notch and feedback pole placed where they act, and the new 16 Hz line marked below the notch band">
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>
<rect class="box" x="14" y="60" width="120" height="56" rx="3"/><text x="74" y="83" text-anchor="middle">openpilot 0xE4</text><text class="sm" x="74" y="100" text-anchor="middle">100 Hz · slew cap 123/frame</text>
<path class="arrow" d="M134 88 H172"/>
<rect class="box" x="172" y="60" width="128" height="56" rx="3"/><text x="236" y="83" text-anchor="middle">assist map</text><text class="sm" x="236" y="100" text-anchor="middle">slot 7 · 6x linear · unchanged</text>
<path class="arrow" d="M300 88 H338"/>
<circle class="box" cx="356" cy="88" r="18"/><text x="356" y="92" text-anchor="middle">Σ</text><text class="sm" x="356" y="52" text-anchor="middle">E = 32·sp − fb</text><text class="sm" x="342" y="122">+</text><text class="sm" x="362" y="122">−</text>
<path class="arrow" d="M374 88 H412"/>
<rect class="box" x="412" y="48" width="150" height="80" rx="3"/><text x="487" y="72" text-anchor="middle">P + D  (Ki = 0)</text><text class="sm" x="487" y="90" text-anchor="middle">Kp 248 flat · Kd 128</text><text class="sm" x="487" y="106" text-anchor="middle">D clamp 10240</text><text class="sm" x="487" y="121" text-anchor="middle">sum clamp ±15360 (0xC61BE)</text>
<path class="arrowf" d="M562 88 H600"/>
<rect class="cave" x="600" y="40" width="176" height="96" rx="3"/><text x="688" y="62" text-anchor="middle" font-weight="600">V289 notch cave</text><text class="sm" x="688" y="80" text-anchor="middle">hook 0x2A174 → 0xC4C00 (140 B)</text><text class="sm" x="688" y="95" text-anchor="middle">20.04 Hz · Q 3.0 · −3 dB 17.0–23.6 Hz</text><text class="sm" x="688" y="110" text-anchor="middle">|N| at 16.5 Hz = 0.76 (−2.4 dB), ∠N −40°</text><text class="sm" x="688" y="125" text-anchor="middle">the 16 Hz line PASSES the notch</text>
<path class="arrowf" d="M776 88 H808"/>
<rect class="box" x="808" y="60" width="130" height="56" rx="3"/><text x="873" y="83" text-anchor="middle">output lag 5.05 Hz</text><text class="sm" x="873" y="100" text-anchor="middle">0xC63EC/EE 992/507 · unchanged</text>
<path class="arrow" d="M938 88 H976"/>
<rect class="box" x="976" y="60" width="90" height="56" rx="3"/><text x="1021" y="83" text-anchor="middle">× gain »15</text><text class="sm" x="1021" y="100" text-anchor="middle">5346 · clamp ±3072</text>
<path class="arrow" d="M1066 88 H1104"/>
<rect class="box" x="1104" y="60" width="66" height="56" rx="3"/><text x="1137" y="83" text-anchor="middle">motor</text><text class="sm" x="1137" y="100" text-anchor="middle">via EME</text>
<path class="arrow" d="M1137 116 V210 H620"/>
<rect class="plant" x="470" y="176" width="150" height="68" rx="3"/><text x="545" y="199" text-anchor="middle">column + rack + motor</text><text class="sm" x="545" y="216" text-anchor="middle">carries a mode at 20.0 Hz (plant ζ ≈ 0.05)</text><text class="sm" x="545" y="231" text-anchor="middle">and is flat, no bump, at 16.6 Hz</text>
<path class="arrow" d="M470 210 H402"/>
<rect class="box" x="272" y="182" width="130" height="56" rx="3"/><text x="337" y="205" text-anchor="middle">0x18F wheel rate</text><text class="sm" x="337" y="222" text-anchor="middle">gp-0x6a56 · 8 counts/deg/s</text>
<path class="arrowr" d="M272 210 H190"/>
<rect class="fb" x="40" y="176" width="150" height="68" rx="3"/><text x="115" y="198" text-anchor="middle" font-weight="600">fb lag pole (cal)</text><text class="sm" x="115" y="215" text-anchor="middle">0xC63E8/EA 923/1560 → 875/2301</text><text class="sm" x="115" y="230" text-anchor="middle">16.5 → 25.0 Hz · DC 30.89 held</text>
<path class="arrow" d="M115 176 V88 H338"/>
<text class="sm" x="128" y="150">fb = s_old + s_new (two-sample sum) · clamp ±46080</text>
<path class="arrowf" d="M688 136 V300"/>
<rect class="cave" x="560" y="300" width="256" height="62" rx="3"/><text x="688" y="322" text-anchor="middle" font-weight="600">0x14A byte 4 tail (100 Hz)</text><text class="sm" x="688" y="339" text-anchor="middle">b5 = sign(S − y) · b7 = |S − y| ≥ |y|</text><text class="sm" x="688" y="354" text-anchor="middle">b7 read 0.03–0.15 in the loud cores: the notched-out part is SMALL</text>
<text class="sm" x="14" y="300">1 kHz LKAS rate PID (FUN_00028ea6). V289 changed two things inside the loop: the notch on the clamped sum S, and the feedback pole. Nothing on the reference side moved.</text>
<text class="sm" x="14" y="318">What the two drives say: at 20 Hz the loop's gain is gone (|L| 0.013) and so is the line — the band is EMPTY. The ring now sits at 15–17 Hz, where |N| is 0.70–0.84 and the notch RETARDS the loop phase by 33–45° (the fb pole gives back 11–12°).</text>
<text class="sm" x="14" y="336">These are two different objects: the 20 Hz mode belongs to the plant and the loop was un-damping it; the 16.6 Hz pole is the loop's own gain crossing, which V282 already carried quietly at |L| 1.13 with 30° of margin.</text>
<text class="sm" x="14" y="354">The notch spent that margin. §5(a) draws both objects and shows that every notch-class option re-creates the second one — it is what the class does, not a defect of this tuning.</text>
<text class="sm" x="14" y="372">Not drawn: the 7 Hz strong-turn lane (r24, 0xC6446) and openpilot's 3.9 Hz outer loop — outside the notched path; their gates in the design memo read 1.005 and +0.6°.</text>
</svg>'''

# ------------------------------------------------------------------ assemble
psd_wire = psd_panel("wire", "PSD ÷ its 10–30 Hz median floor", "Pooled wheel-rate PSD, six routes, 10–30 Hz")
psd_bar = psd_panel("bar", "PSD ÷ its 10–30 Hz median floor", "Pooled driver-torque PSD, six routes, 10–30 Hz")
nmag, nph = notch_curves()
mapsvg, zoomsvg = h1_map()
hists = h1_hist(); budgets = h1_budget()
lerp_map, lerp_kp, lerp_kd, lerp_taper = lerp_plots()
polemap_svg = pole_map(); ledger_svg = margin_ledger(); kd_svg, kdhist_svg = kd_lerp_fig()
frontier_svg = frontier_fig(); notchC_svg = notchC_fig()
GRIND_POOL = S5["pool"]["grind"]["v289"]
S0ROW = [r for r in DOSE if r["lab"].startswith("S0")][0]
SPROW = [r for r in DOSE if r["lab"].startswith("S'")][0]
CEIL = DOSE[0]["ring_ms"] / S0ROW["ring_ms"]
sha = DELTA["sha256"]; dd = DELTA["diffs"]

CSS = r'''
:root{
  --ground:#F1F2EE; --surface:#FFFFFF; --ink:#181C1F; --muted:#5A6470; --line:#D5D9D4; --soft:#F7F8F5;
  --v289:#2a78d6; --v282:#eb6834; --v288:#1baf7a; --stock:#8a94a0; --s7:#4a3aa7; --s16:#e34948; --s20:#2a78d6;
  --grind:#eb6834; --quiet:#2a78d6; --cap:#a16207;
  --ev:#1F7A4D; --bel:#A16207; --fail:#B42318; --quo:#4a3aa7;
  --evbg:#E4F3EA; --belbg:#FBF0D5; --failbg:#FBE3E0; --quobg:#ECE8F7; --hotbg:#FBE3E0; --cavebg:#E1EEFB; --fbbg:#FBE9DF; --plantbg:#EEF0EA;
  --bandA:rgba(227,73,72,.10); --bandB:rgba(42,120,214,.10); --capfill:rgba(161,98,7,.18); --bandKnot:rgba(74,58,167,.09);
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --ground:#121517; --surface:#1A1E22; --ink:#E7EAEC; --muted:#9AA4AE; --line:#2C333A; --soft:#20262B;
  --v289:#3987e5; --v282:#f0865a; --v288:#26c48a; --stock:#8a94a0; --s7:#9085e9; --s16:#e66767; --s20:#3987e5;
  --grind:#f0865a; --quiet:#3987e5; --cap:#e2b94b;
  --ev:#5CC48A; --bel:#E2B94B; --fail:#F08A80; --quo:#B39BE0;
  --evbg:#173225; --belbg:#3A2E10; --failbg:#3D1D1A; --quobg:#2A2340; --hotbg:#3D1D1A; --cavebg:#12303B; --fbbg:#3C2418; --plantbg:#232A2E;
  --bandA:rgba(230,103,103,.14); --bandB:rgba(57,135,229,.14); --capfill:rgba(226,185,75,.20); --bandKnot:rgba(144,133,233,.13);
}}
:root[data-theme="dark"]{
  --ground:#121517; --surface:#1A1E22; --ink:#E7EAEC; --muted:#9AA4AE; --line:#2C333A; --soft:#20262B;
  --v289:#3987e5; --v282:#f0865a; --v288:#26c48a; --stock:#8a94a0; --s7:#9085e9; --s16:#e66767; --s20:#3987e5;
  --grind:#f0865a; --quiet:#3987e5; --cap:#e2b94b;
  --ev:#5CC48A; --bel:#E2B94B; --fail:#F08A80; --quo:#B39BE0;
  --evbg:#173225; --belbg:#3A2E10; --failbg:#3D1D1A; --quobg:#2A2340; --hotbg:#3D1D1A; --cavebg:#12303B; --fbbg:#3C2418; --plantbg:#232A2E;
  --bandA:rgba(230,103,103,.14); --bandB:rgba(57,135,229,.14); --capfill:rgba(226,185,75,.20); --bandKnot:rgba(144,133,233,.13);
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;margin:0;padding-inline:20px;padding-block:0}
main{max-width:1140px;margin:0 auto;padding-block:28px 80px}
h1,h2,h3{font-family:"IBM Plex Sans Condensed","IBM Plex Sans",system-ui,sans-serif;text-wrap:balance;margin:0}
h1{font-size:34px;font-weight:600;line-height:1.1}
h2{font-size:23px;font-weight:600;margin-top:52px;padding-top:14px;border-top:2px solid var(--line)}
h3{font-size:16.5px;font-weight:600;margin-top:26px}
p,li{max-width:76ch}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace;font-size:.92em;overflow-wrap:anywhere}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500}
.lede{margin-top:10px;font-size:16.5px;max-width:80ch}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}
.chip{font-family:"IBM Plex Mono",monospace;font-size:12px;padding:3px 9px;border-radius:3px;border:1px solid var(--line);background:var(--surface)}
.chip.ev{background:var(--evbg);color:var(--ev);border-color:transparent}.chip.bel{background:var(--belbg);color:var(--bel);border-color:transparent}
.chip.fail{background:var(--failbg);color:var(--fail);border-color:transparent}.chip.v289{background:var(--cavebg);color:var(--v289);border-color:transparent}
.tag{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.04em;padding:1px 6px;border-radius:2px;vertical-align:middle;white-space:nowrap}
.tag.ev{background:var(--evbg);color:var(--ev)}.tag.bel{background:var(--belbg);color:var(--bel)}.tag.fail{background:var(--failbg);color:var(--fail)}.tag.quo{background:var(--quobg);color:var(--quo)}
.card{background:var(--surface);border:1px solid var(--line);padding:18px 20px;margin-top:18px}
.card.op{border-left:4px solid var(--v289)}.card.risk{border-left:4px solid var(--bel)}.card.fail{border-left:4px solid var(--fail)}.card.pending{border:2px dashed var(--bel);background:var(--soft)}
.quote{font-family:"IBM Plex Sans Condensed",sans-serif;font-size:26px;font-weight:500;line-height:1.2;margin:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;margin-top:16px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:16px}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;font-size:14px;margin:0}.kv dt{color:var(--muted)}.kv dd{margin:0}
table{border-collapse:collapse;width:100%;font-size:13.2px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:500;color:var(--muted);font-size:11.5px;letter-spacing:.04em;text-transform:uppercase}
tr.hl td{background:var(--cavebg)}tr.sub td{color:var(--muted)}
.tw{overflow-x:auto;margin-top:12px;background:var(--surface);border:1px solid var(--line)}
.matrix td,.matrix th{padding:4px 6px;font-size:11.5px;white-space:nowrap}.matrix td.chg{background:var(--belbg);font-weight:500}
.matrix th.rot span{writing-mode:vertical-rl;transform:rotate(180deg);display:inline-block}
figure{margin:0;background:var(--surface);border:1px solid var(--line);padding:12px 12px 8px;min-width:0}
figure svg{width:100%;height:auto;display:block}
figcaption{font-size:12.5px;color:var(--muted);margin-top:8px;line-height:1.45}
svg text{font-family:"IBM Plex Mono",monospace;font-size:10.5px;fill:var(--muted)}
svg .ax{stroke:var(--line)}svg .grid{stroke:var(--line);stroke-dasharray:2 3}
svg .v289{stroke:var(--v289)}svg .v289b{stroke:var(--v289);opacity:.55}svg .v282{stroke:var(--v282)}svg .v282b{stroke:var(--v282);opacity:.45}svg .v288{stroke:var(--v288)}svg .stock{stroke:var(--stock)}
svg .s7{stroke:var(--s7)}svg .s16{stroke:var(--s16)}svg .s20{stroke:var(--s20)}svg .grind{stroke:var(--grind)}svg .quiet{stroke:var(--quiet)}
svg .v289d{fill:var(--v289)}svg .stockd{fill:var(--stock)}svg .s16d{fill:var(--s16)}svg .s7d{fill:var(--s7)}
span.muted,dd .muted{color:var(--muted)}svg .muted{fill:var(--muted)}
svg .v289t{fill:var(--v289)}svg .v282t{fill:var(--v282)}svg .stockt{fill:var(--stock)}svg .grindt{fill:var(--grind)}svg .quiett{fill:var(--quiet)}svg .s7t{fill:var(--s7)}svg .s16t{fill:var(--s16)}svg .s20t{fill:var(--s20)}svg .capt{fill:var(--cap)}svg .bandt{fill:var(--muted);font-size:9.5px}
svg .mark{stroke:var(--muted);stroke-dasharray:4 3}svg .markline{stroke:var(--ink);stroke-width:1.5}svg .capline{stroke:var(--cap);stroke-dasharray:4 3}svg .caplinet{fill:var(--cap)}
svg .line16{stroke:var(--s16);stroke-dasharray:4 3}svg .line16t{fill:var(--s16)}svg .line20{stroke:var(--s20);stroke-dasharray:4 3}svg .line20t{fill:var(--s20)}
svg .bandA{fill:var(--bandA)}svg .bandB{fill:var(--bandB)}svg .capfill{fill:var(--capfill)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin-top:6px}
.legend span::before{content:"";display:inline-block;width:18px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor}
.legend .v289{color:var(--v289)}.legend .v282{color:var(--v282)}.legend .v288{color:var(--v288)}.legend .stock{color:var(--stock)}.legend .s7{color:var(--s7)}.legend .s16{color:var(--s16)}.legend .s20{color:var(--s20)}.legend .grind{color:var(--grind)}.legend .quiet{color:var(--quiet)}.legend .cap{color:var(--cap)}
.diagram{overflow-x:auto;background:var(--surface);border:1px solid var(--line);padding:10px;margin-top:16px}
.diagram svg{min-width:960px;width:100%;height:auto;color:var(--muted)}
.dg text{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:11.5px;fill:var(--ink)}
.dg .sm{font-family:"IBM Plex Mono",monospace;font-size:9.5px;fill:var(--muted)}
.dg .box{fill:var(--soft);stroke:var(--line)}.dg .cave{fill:var(--cavebg);stroke:var(--v289);stroke-width:1.5}.dg .fb{fill:var(--fbbg);stroke:var(--v282);stroke-width:1.5}.dg .plant{fill:var(--plantbg);stroke:var(--muted);stroke-width:1.2}
.dg .hot{fill:var(--hotbg);stroke:var(--s16);stroke-width:2}.dg .hott{fill:var(--s16);font-weight:600;font-size:11px}
.dg .arrow{stroke:var(--muted);fill:none;marker-end:url(#ah)}.dg .arrowf{stroke:var(--v289);fill:none;marker-end:url(#ah);stroke-width:1.5}.dg .arrowr{stroke:var(--v282);fill:none;marker-end:url(#ah);stroke-width:1.5}.dg .arrowfb{stroke:var(--v282);fill:none;marker-end:url(#ah2);stroke-width:1.2;stroke-dasharray:5 3}
.dg .arrow,.dg .arrowf,.dg .arrowr{marker-end:url(#ah)}
.note{font-size:13px;color:var(--muted)}ul{padding-left:20px}a{color:var(--v289)}
/* --- section 5: poles, placement, the Kd axis --- */
svg .polelive{fill:var(--s16);fill-opacity:.75;stroke:var(--s16)}svg .poledead{fill:var(--stock);fill-opacity:.16;stroke:var(--stock);stroke-dasharray:2 2}
svg .polet{fill:var(--s16);font-weight:600}svg .meas{stroke:var(--ink);stroke-width:2.5}svg .measd{fill:var(--ink)}svg .meast{fill:var(--ink);font-size:9.5px}
svg .net{stroke:var(--fail);stroke-width:3}svg .nett{fill:var(--fail);font-weight:600}
svg .budget{stroke:var(--ink);stroke-dasharray:7 4}svg .budgett{fill:var(--ink)}svg .zeroline{stroke:var(--line)}svg .zerolinet{fill:var(--muted)}
svg .bandKnot{fill:var(--bandKnot)}svg .grindbar{fill:var(--grind);fill-opacity:.62}
svg .v282d{fill:var(--v282)}svg .netd{fill:var(--fail)}
td.ok,b.ok,span.ok{color:var(--ev);font-weight:600}td.bad,b.bad,span.bad{color:var(--fail);font-weight:600}
th .th2{display:block;text-transform:none;letter-spacing:0;font-weight:400;opacity:.8}
.dg .ok{fill:var(--evbg);stroke:var(--ev);stroke-width:1.5}.dg .fail{fill:var(--failbg);stroke:var(--fail);stroke-width:1.5}
.dg .sep{stroke:var(--line);stroke-width:1}
.card.done{border-left:4px solid var(--ev)}.card.spec{border-left:4px solid var(--s7)}
dl.spec{display:grid;grid-template-columns:max-content 1fr;gap:5px 18px;margin:12px 0 0;font-size:13.5px}
dl.spec dt{color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:12px}dl.spec dd{margin:0}
.verdict{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.verdict>div{flex:1 1 240px;background:var(--soft);border:1px solid var(--line);padding:12px 14px}
.verdict b{display:block;font-family:"IBM Plex Sans Condensed",sans-serif;font-size:15px;margin-bottom:4px}
.three{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:14px}
.three .card{margin-top:0}
.big{font-family:"IBM Plex Sans Condensed",sans-serif;font-size:30px;font-weight:600;line-height:1;margin:0}
.big small{display:block;font:500 12px/1.3 "IBM Plex Sans",sans-serif;color:var(--muted);margin-top:6px;letter-spacing:.02em}
@media (prefers-reduced-motion: no-preference){}
'''

def mark_block(key, mi, label, who):
    return fig(mark_panel(key, mi, label), who, leg(("s7", "5–12 Hz (the 7.5 Hz strong-turn ring)"), ("s16", "13–18 Hz (the V289 line)"), ("s20", "18–22 Hz (the V282/V288 line)"), ("cap", "shaded: slew-capped 0xE4 frames")))

html = []
A = html.append
A(f'<title>The Ring That Moved</title>')
A('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')
A(f'<style>{CSS}</style><main>')
A('<div class="eyebrow">2020 Accord EPS · 39990-TVA-A160 · close-out 2026-09-09 · no build cut this session</div>')
A('<h1>V289\'s notch worked. It emptied the 20 Hz band — and uncovered a second pole at 16 Hz</h1>')
A('<p class="lede">The 18–22 Hz band is <b>empty</b> on both V289 routes: 0 of 1414 present windows, against 501 on V282, a ×34 drop in prevalence. The notch annihilated the loop gain feeding a genuine plant mode, exactly as designed. What it also did was spend V282\'s 30° of phase margin at a <i>different</i>, pre-existing pole at 16.6 Hz, which now rings in trains and is what the operator hears. Measured damping is 0.029 on V282 and 0.029 on V289 — the frequency moved, the damping did not. This page carries the two drives, the two objects, a placement finding that explains V289\'s authority loss, the colleague\'s torque-table hypothesis falsified, the full non-stock delta of the recommended base read from the images, and the V290 candidates with the operator\'s decision on them.</p>')
A('<div class="chips"><span class="chip v289">flown: V289 rev 1, r62 + r63, confirmed from the tap</span><span class="chip ev">notch target: MET — 18–22 Hz band empty, ×34</span><span class="chip fail">revert signature: MET — a 15–17 Hz line in trains</span>'
  f'<span class="chip">stock {sha["stock"][:12]}… · V282 {sha["V282"][:12]}… · V289 {sha["V289"][:12]}…</span><span class="chip">V282→V289: {dd["V282_vs_V289"]["bytes"]} bytes · stock→V282: {dd["stock_vs_V282"]["bytes"]} bytes</span>'
  '<span class="chip bel">V290: NOT BUILT — operator reverted to V282</span></div>')

# ---------------------------------------------------------------- 1
A('<h2>1 · What the two V289 drives showed</h2>')
A('<section class="card op"><p class="quote">"Grinding is still an issue."</p><p class="note" style="margin:8px 0 0">The operator, after routes 62 and 63 on 2026-09-09. One bookmark per route: r62 at 917.8 s (segment 15), r63 at 684.3 s (segment 11). Both presses came on the exit of a full-lock intersection turn at 2–3 m/s with the 0xE4 command swinging rail to rail at openpilot\'s slew cap — the same manoeuvre as the V288 marks 2 and 3 and the V282 r39 mark 2.</p></section>')
A('<div class="three">'
  f'<div class="card"><p class="big">15.9 / 15.1 Hz<small>dominant bar line in the 10 s before each press (r62 / r63); V288 and V282 marks read {MARK_F0_LO:.2f}–{MARK_F0_HI:.2f} Hz across {MARK_F0_N} marks</small></p></div>'
  '<div class="card"><p class="big">×9.6 / ×23<small>route-wide wheel-rate PSD peak at 16.5–17.0 Hz above the band floor; the 18–22.5 Hz peak is gone (×3.0 / ×3.7 at the band edge, no peak)</small></p></div>'
  '<div class="card"><p class="big">725–826 raw<small>loudest V289 episodes (r63) vs V288\'s loudest 640 and V282\'s route-wide census max of 402 (its own two bookmarks read 360 and 263): not quieter</small></p></div></div>')
A('<h3>The pooled spectrum, six routes on one scale ' + EV + '</h3>')
A('<p>Pooled Welch PSD of the 0x18F wheel rate and of the driver-torque bar over every laterally-engaged run of 4 s or more, each route divided by its own 10–30 Hz median floor so routes of different length and roughness sit on one axis. This is marks62\'s crux instrument, re-run here (script <code>v290page_psd_dump.py</code>), independent of the bookmark code and of the census gate.</p>')
A('<div class="grid2">' + fig(psd_wire, "Wheel rate. Every V282 and V288 route has one line at 19.9–20.1 Hz and nothing at 13–17.5 Hz; both V289 routes have no 20 Hz peak and a 16.5–17.0 Hz line stronger, relative to its floor, than the 20 Hz line ever was.", leg(("v289", "r62 · r63 (V289 r1)"), ("v288", "r5e (V288 r2)"), ("v282", "r39 · r3a · r3c (V282)")))
  + fig(psd_bar, "Driver torque (the bar). Same picture; r63's bar peaks at the same 16.50 Hz as its wheel rate. The broad 13.0–13.8 Hz content at ×5–8 on the V282 routes is present on every build and is not the grind line.", leg(("v289", "V289 r1"), ("v288", "V288 r2"), ("v282", "V282"))) + '</div>')
A(psd_ratio_table())
A('<p class="note">The 13–17.5 : 18–22.5 band-power ratio flips by 15–20× between the V282/V288 routes and the V289 routes. Read from <code>v290page_psd.json</code>; the marks62 report quotes 4.9 / 9.9 vs 0.32–0.62 on the same recipe.</p>')

A('<h3>What was on the wire before each press ' + EV + '</h3>')
A('<p>Hilbert envelopes of the bar in three bands, 25 s before and 3 s after each bookmark, from the route caches (script <code>v290_closeout_bookmark_timelines.py</code>). The two V289 presses are shown against the V288 mark 3 and the V282 r39 mark 1, same code. In both V289 windows the last loud thing before the press is the <b>7.5 Hz strong-turn ring at 1300–1400 raw, 2.4–2.6 s before the press</b>; the 15–16 Hz burst peaked 4.6 / 8.6 s before it. Which of the two the operator calls grinding is his to say — both are present before both presses. ' + BEL + ' for that reading.</p>')
_r62m0, _r63m0 = MARKS["r62_v289"]["marks"][0], MARKS["r63_v289"]["marks"][0]
A('<div class="grid2">' + mark_block("r62_v289", 0, "r62 (V289) bookmark 917.8 s", f"r62, V289 rev 1: full-lock right turn at an intersection, 2–3 m/s, blinker + laneChange flag, brake then release; the 16 Hz burst (13–18 Hz, red) fires as the wheel starts to unwind, decays with τ 0.49 s; the 7.6 Hz ring (violet) peaks at {_r62m0['b5_12_pk']:.0f} raw {abs(_r62m0['b5_12_pk_t']):.1f} s before the press; 18–22 Hz (blue) stays under 105 raw the whole window.")
  + mark_block("r63_v289", 0, "r63 (V289) bookmark 684.3 s", f"r63, V289 rev 1: hard right to −390° at 2–3 m/s with 2400–3300 raw on the wheel; the 15.1 Hz burst peaks 8.6 s before the press and dies with τ 0.12 s; the 7.5 Hz ring peaks at {_r63m0['b5_12_pk']:.0f} raw {abs(_r63m0['b5_12_pk_t']):.1f} s before the press; 18–22 Hz under 98 raw.")
  + mark_block("r5e_v288", 2, "r5e (V288 r2) bookmark 820.1 s", "V288 rev 2 mark 3, for contrast: here the 18–22 Hz line (blue) is the loud one, 591 raw 1.5 s before the press, with the 13–18 Hz band a bystander.")
  + mark_block("r39", 0, "r39 (V282) bookmark 689.7 s", "V282 r39 mark 1: 18–22 Hz at 334 raw and 13–18 Hz at 328 raw ten seconds before the press, the 7.5 Hz ring at 1056 raw.") + '</div>')

A('<h3>Episodes, like for like — and why the V282 yardstick under-reads V289 ' + EV + '</h3>')
A('<p>Three counts of the same two routes. The first is the V282 census recipe (15–26 Hz prominence ≥ 8 <i>and</i> bar 18–22 Hz ≥ 40 raw): it reads V289 as a 3× improvement in episodes per hour, and that number is <b>void</b> — its amplitude gate sits in the band the line has left, so it sees only the tails of the loudest bursts. The second is the same census with the search and gate moved to 12–18 Hz. The third is the frequency-agnostic census (12–25 Hz peak-tracked). Quoted from census62\'s <code>grind1_census_v289_r62_r63.txt</code> and <code>grind1_census_v289_agnostic.txt</code>; the marks62 report reproduces the r39 yardstick exactly (1742 / 364 / 79).</p>')
A('''<div class="tw"><table><thead><tr><th>route</th><th>build</th><th>engaged s</th><th>yardstick 18–22 Hz gate: present % · episodes (/h)</th><th>f0 of present windows</th><th>episode env peak p50 / max (raw)</th><th>12–18 Hz re-census: present %</th><th>agnostic 12–25 Hz: present % · f0 p50</th></tr></thead><tbody>
<tr><td class="mono">r39</td><td>V282</td><td>880</td><td>20.9 % · 79 (323)</td><td>20.05 ± 1.03</td><td>114 / 402</td><td>9.0 %</td><td>42.5 % · 15.6 Hz</td></tr>
<tr><td class="mono">r5e_v288</td><td>V288 r2</td><td>642</td><td>15.6 % · 46 (258)</td><td>19.84 ± 1.40</td><td>126 / 640</td><td>22.4 %</td><td>52.3 % · 14.7 Hz</td></tr>
<tr class="hl"><td class="mono">r62_v289</td><td>V289 r1</td><td>619</td><td>2.1 % · 12 (70) — <b>gate blind</b></td><td><b>16.54 ± 2.32</b></td><td><b>306 / 631</b></td><td><b>24.6 %</b></td><td>52.3 % · 13.2 Hz (&lt; 8 m/s: 16.3 Hz)</td></tr>
<tr class="hl"><td class="mono">r63_v289</td><td>V289 r1</td><td>588</td><td>2.2 % · 15 (92) — <b>gate blind</b></td><td><b>16.19 ± 0.77</b></td><td><b>457 / 780</b></td><td><b>35.0 %</b></td><td>66.9 % · 13.4 Hz (&lt; 8 m/s: 16.4 Hz)</td></tr>
</tbody></table></div>''')
A('<p class="note">Every V289 event is a decaying burst (contiguous time above half-peak 0.30–0.90 s, τ 0.08–0.49 s, ζ_eff 0.02–0.13) but they come in trains: on r63 at 290–298 s the 16.5 Hz bar rings 500–826 raw every 1.5–2 s for 10 s, hands off, wheel held at −60° at 12.3 m/s. Decay-rate ratio V289 pool / V282 pool = 1.02 [0.42, 2.79] — the predicted ×1.7 faster decay is not seen. Mann-Whitney on episode envelope peak, V289 vs V282 pooled: p = 2×10⁻⁷ (louder).</p>')

A('<h3>Build identity, from the tap — not the label ' + EV + '</h3>')
A('''<div class="tw"><table><thead><tr><th>0x14A byte-4 statistic</th><th>r62</th><th>r63</th><th>r5e (V288)</th><th>r39 (V282)</th><th>V289 expectation</th></tr></thead><tbody>
<tr><td>b5 duty, engaged (V289: sign(S − y), zero-mean)</td><td><b>0.500</b></td><td><b>0.500</b></td><td>0.412</td><td>0.134</td><td>≈ 0.50</td></tr>
<tr><td>b5 spectrum peak 3–45 Hz / 18–22 Hz share (flat = 0.095)</td><td>19.9 Hz / 0.271</td><td>16.8 Hz / 0.249</td><td>3.1 Hz / 0.052</td><td>3.1 Hz / 0.087</td><td>≫ 0.10</td></tr>
<tr><td>b7 duty, SCA = 0 more than 3 s after SCA fell (V289: 0 ≥ 0 reads 1)</td><td><b>0.999</b></td><td><b>1.000</b></td><td>0.000</td><td>0.000</td><td>1.000</td></tr>
<tr><td>b7 duty engaged → in grinding episodes</td><td>0.164 → 0.30</td><td>0.177 → 0.24</td><td>0.559 → 0.41</td><td>0.507 → 0.49</td><td>0.10 → 0.12–0.37 (met)</td></tr>
<tr><td>b7 in the loud 2 s cores at 15–17 Hz</td><td>0.03–0.05</td><td>0.025–0.15</td><td>—</td><td>—</td><td>0.12–0.37 for a 20 Hz ring: LOW — the line is outside the notch band</td></tr>
<tr><td>bits 0–2 / b4 / b3 (stock Honda / r24 controls)</td><td>1.000 / 0.389 / 0.463</td><td>1.000 / 0.433 / 0.471</td><td>1.000 / 0.404 / 0.471</td><td>1.000 / 0.404 / 0.479</td><td>as V282</td></tr>
</tbody></table></div>''')
A('<p class="note">Both routes are V289 rev 1 and the notch cave was live (qlive62). Also new: after lateral control drops, b5 keeps toggling for 1–3 s and b7 climbs to 1.000 only after ~3 s — Honda\'s rate PID keeps executing through a disengage fade. Score b7 engaged-only.</p>')
A('<div class="grid2">'
  '<section class="card done"><b>The notch\'s own target — MET, completely.</b> V289 was aimed at the 20 Hz line. On the demand-gated census over 11 routes the 18–22 Hz band is <b>EMPTY on V289</b>: 1 window in the 18 Hz bin and zero in 19 / 20 / 21, out of 1414 present windows, against 501 on V282 — prevalence down <b>×34</b>. Independently, with no census gate at all, the pooled wheel-rate spectrum peaks at 19.92 Hz on V282 and V288 and at 16.80 Hz on V289. <b>The notch did not shift the 20 Hz line; it removed it.</b> ' + EV + ' — <code>MODE-NATURE-V289-RECENSUS-2026-09-09.md</code> §1a, 14 678 windows.</section>'
  '<section class="card fail"><b>Its pre-registered revert signature — also MET.</b> V289\'s pre-registration named: <i>a new line at 14–17 Hz or 22–24 Hz; a sustained lower-pitch ~16 Hz grind; any new straight-road vibration.</i> The 14–17 Hz line is present on both routes as the dominant grind line (bar 13–17 Hz 145 / 101 raw in the 10 s before the marks vs 17 / 30 at 18–22 Hz; route-wide PSD ×10–23 at 16.5–17.0 Hz). "Sustained" is met in kind by the r63 trains. 22–24 Hz: one 0.3 s burst on a road jolt, not a line. <b>A mixed result, not a failure: the target was hit and a second object was uncovered.</b> ' + EV + '</section></div>')

# ---------------------------------------------------------------- 2
A('<h2>2 · What V289 changed, element by element</h2>')
A('<p>V289 changed two things inside the 1 kHz rate loop and nothing outside it: a notch on the clamped loop output S, and the feedback lag pole. The diagram places both where they act. Read this section as the mechanism; §5 draws the consequence — that the two edits act on <i>two different objects</i>, removing one and de-stabilising the other.</p>')
A('<div class="diagram">' + loop_diagram() + '</div>')
A('<div class="grid2">' + fig(nmag, "Notch N (solid) and the notched-out path 1−N (dashed), magnitude, computed from the coefficients decoded out of the V289 image (b = [16048, −31842, 16048], a = [16384, −31842, 15712], Q14). At the new line, 16.5 Hz, |N| = 0.76: three quarters of the loop's action passes. The shaded band is the notch's −3 dB width, 16.98–23.64 Hz.", leg(("v289", "N (what the loop keeps)"), ("s16", "1−N (what the notch removes)")))
  + fig(nph, "Phase. N contributes −40° at 16.5 Hz and +86° at 20.3 Hz; 1−N swings through ±90° across the band. Below the notch the loop's phase is retarded, not advanced — the opposite of what damps a resonance that has slid down there.", leg(("v289", "∠N"), ("s16", "∠(1−N)"))) + '</div>')
A('<h3>Loop-phase budget at the new line and at the old one</h3>')
A('<p>Element by element from the image cells (filters at the 1 kHz tick, which is itself ' + BEL + ' per the record). This is a linear element-wise sum, not a closed-loop stability re-derivation. The D-lead contribution is deliberately left out: the record carries two incompatible modelled values for it (+3.7° in the LERP reader, +62° in the loopshape memo, both BELIEF), and the difference is the size of the effect being explained.</p>')
A(budget_table())
A('<p>Return ratio of the loop from the design memo\'s model (' + MOD + ', byte-read electronics × a fitted plant; ordering robust across six plant fits, absolute values swing ×2): at 17 Hz V282 1.97 ∠−67° → V289 1.65 ∠−101°; at 20.3 Hz V282 1.74 ∠−73° → V289 0.17 ∠+25°. The notch removed the loop\'s gain at 20 Hz and <i>added</i> 34° of lag at 17 Hz. On the smooth-plant branch the memo\'s own adversary B found V289 Nyquist-marginal at ~16 Hz <b>before the drive</b> — the memo\'s §12 table lists "V289 (reference): UNSTABLE (the 16 Hz relocation)". The relocation was predictable from the notch skirt, and was predicted; it was not weighted.</p>')
A('<section class="card done"><b>Settled during this session — the two facts are not in tension, they are two objects.</b> (1) f was pinned at 20.03–20.08 Hz on five builds while Kp ran 248 → 696 — the signature of a plant mode, and the re-census confirms it model-free at matched load while falsifying the clamp explanation. (2) A phase-only change moved the ring by 3.3 Hz — but not by dragging the 20 Hz line down: it <b>deleted</b> the 20 Hz line and exposed a second pole the loop already had at 16.63 Hz with 30° of margin. Both facts hold, of different objects. The single-LTI-plant model is what broke, not the classification. ' + EV + ' — see §5(a).</section>')

# ---------------------------------------------------------------- 3
A('<h2>3 · Colleague hypothesis H1 — "OP just switches between two points on the torque table; scaling it loses resolution" — FALSE</h2>')
A('<p>Tested by <code>hyptable</code> (report <code>docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md</code>) and re-derived for these figures by <code>h1fig2</code> from the built images and the wire caches (<code>h1_figdata_2026-09-09.json</code>). Every number in the plots is ' + EV + ' from the images or the wire; the record rows are quotations from named files.</p>')
A('<h3>(a) Where the resolution is set — and that it never changed</h3>')
A('<div class="diagram">' + h1_signal_path() + '</div>')
A('<p class="note">The quantiser sits <i>before</i> the map. It turns the 0…4096 command into 241 index values, 16.13 raw counts per step, and no build has ever touched it. Scaling the map does not change how finely the command is resolved; it changes how much setpoint each index step is worth. One setpoint count = 0.1295 deg/s = 5.06 output counts through P (Kp 248, gain 5346).</p>')
A('<h3>(b) The map curves, with the staircase visible</h3>')
A('<div class="grid2">' + fig(mapsvg, "Setpoint vs command, stock and the 6x linear map, drawn as the staircase the ECU actually computes (241 treads). Knots are slope changes, never jumps. The 6x map is a straight line to 133.6 deg/s at index 240; stock saturates at 22.3 deg/s.", leg(("v289", "V282 / V289 (byte-identical)"), ("stock", "stock (true dump, = _v83a at 0xE502C)")))
  + fig(zoomsvg, "The first 400 counts. Solid: the staircase; dashed: the same LERP with both floors removed. One slew-capped frame (123 counts) crosses 7.6 treads; the quantiser's tread is 30× smaller than the step the cap itself makes.", leg(("v289", "6x staircase / continuous"), ("stock", "stock staircase / continuous"), ("cap", "openpilot slew cap"))) + '</div>')
A('<h3>(c) What one index step is worth</h3>')
A(fig(h1_step(), "Setpoint step per index LSB. The 6x map alternates between 4 and 5 sp counts (0.52–0.65 deg/s) and never stalls; the stock map is the one with a genuine staircase — 104 of its 240 index steps move the setpoint by nothing. Relative resolution (step ÷ value) is essentially identical on both maps: 0.17 vs 0.19 at index 6, 0.006 vs 0.006 at index 200.", leg(("v289", "V282 / V289 (6x)"), ("stock", "stock"))))
A('<h3>(d) Does the command dwell on two values? No.</h3>')
A('<div class="grid2">' + "".join(fig(svg, f"Pooled |Δcmd| between consecutive 100 Hz frames, grinding windows vs matched quiet windows ({'r39, V282' if tag=='r39' else 'r5e, V288 rev 2'}). The ±1 alternation fraction and the share of 100 ms windows sitting on exactly two command values are 0.000 in grinding on both routes: nothing dwells. What IS enriched in grinding is the slew-capped frame (≥ 122 counts): 0.13 vs 0.02 on r39, 0.21 vs 0.09 on r5e.", leg(("grind", "grinding windows"), ("quiet", "quiet windows"), ("cap", "slew cap 122.88 = 0.03 × 4096"))) for svg, tag in hists) + '</div>')
A('<h3>(e) The decisive amplitude budget</h3>')
A('<div class="grid2">' + "".join(fig(svg, f"Median spectrum per 2 s census window, {'r39 (V282, 311 grinding / 771 quiet windows)' if tag=='r39' else 'r5e (V288 r2, 171 / 245 windows)'}. Dashed: the 6x map's quantisation residual (staircase minus continuous, through P and the gain) — flat at ~0.7–0.9 counts per bin from 3 to 50 Hz and identical in grinding and quiet. Solid: the 427 torque tap on its native 50 Hz clock. The tap has a 4× peak at 20 Hz that exists only when the car is grinding; at the 20 Hz bin it is ~32× the residual. Band 18–22 Hz: residual {bt['q6']:.2f} (grind) vs {bq['q6']:.2f} (quiet); tap {bt['T']:.1f} vs {bq['T']:.1f}. Even crediting the whole closed-loop resonance peak (Ms 3.8) to the residual leaves a 4.8–5.3× gap.", leg(("grind", "grinding"), ("quiet", "quiet"))) for svg, tag, bt, bq in budgets) + '</div>')
A('<h3>(f) The record: a coarser map was MORE present; finer steps changed nothing ' + QUO + '</h3>')
A(h1_record_table())
A('<p class="note">Quoted from <code>loopshape20_mode_nature.txt</code> (9 routes, 5 builds). Kp is confounded with map scale across these rows (the ×2 and ×6 LERP-Kp rows carry the highest presence); the within-corpus bins separate them and the direction stays wrong for H1. V288 rev 2 made every per-tick setpoint step ~11× finer (setpoint pre-filter) and cut D-clamp binds ×0.03; grinding was unchanged (258 vs 239 episodes/h, f 20.06 vs 20.03 Hz, envelope p50 126 vs 127) — <code>GRIND1-CENSUS-V288-R5E-2026-09-08.md</code>. The stock-map era named the same 18–22 Hz band (V62) — <code>GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md</code>.</p>')
A(f'<section class="card"><b>For the colleague, in three sentences.</b> The hypothesis predicts that a scaled table makes the command hop between two coarser setpoints and that the hop is the excitation, so the grinding should grow with table scale, dwell on two values, and shrink when the steps are made finer. The wire shows the command changing on 96–99 % of frames with zero two-value dwell, a quantisation residual smaller than the torque line in the 18–22 Hz band — {BSM_RATIO_LO:.1f}–{BSM_RATIO_HI:.1f}× by the <code>band_from_spec_median</code> recipe the figures above use, 18.1–20.1× by the native-tap band method in <code>H1-FIGURES-README-2026-09-09.md</code> §"the decisive amplitude budget" and up to 32× at the single 20 Hz bin — and a residual value itself essentially identical in grinding and quiet, a coarser ×2 table that was <i>more</i> present than the ×6 one, and steps made 11× finer (V288) that changed nothing. The kernel of truth: the map\'s scale <i>is</i> the loop gain — a steeper table is a higher-gain rate loop, and the mode loses damping with gain (ζ 0.036 → 0.019 as Kp rose) — so the colleague is right that scaling the table made it worse, and wrong about why.</section>')
A('<section class="card"><b>H2 ("the 20 Hz stair-step command held for 4 frames and sent at 100 Hz") — also not what the wire shows.</b> The 0xE4 command changes on 96–99 % of 100 Hz frames in grinding windows (94.5 % of gaps are one frame); it is not a 4-frame staircase. It <i>is</i> slew-capped at 123 counts per frame by openpilot, and capped frames are 7–60× enriched in grinding episodes; the command\'s own 20 Hz line is an echo of the wheel ring through openpilot\'s unfiltered 100 Hz angle measurement (open-loop share of the torque line ~9 %). ' + EV + '</section>')

# ---------------------------------------------------------------- 4
A('<h2>4 · The cumulative non-stock delta of V282 — the base the car goes back to</h2>')
A('<p>V282 is not a proposal: it is what the operator chose, so this is the delta that will be on the car. Everything below is <b>cumulative against true stock</b>, not one session\'s changes, and the V289 column is shown alongside only so the revert is legible. A companion enumeration re-read the same images independently and ran an <b>attribution census as an assertion</b>: all <b>1 984</b> differing bytes map to exactly one named row across 26 rows, and the script aborts on any orphan — it does not abort. Three groups carry the honest label: <code>0xC61C0/C2/C4</code> (no lineage entry), <code>0xC40BC/D2/DC</code> (riding the V255→V112 rebase; K1 measured NULL) and <code>0xC64DE</code> (validated under a label later found wrong). ' + QUO + ' from <code>docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md</code>.</p>')
A(f'<p>Raw little-endian byte reads of the true stock dump (<code>stock_fw_dump/code.bin</code>, sha256 {sha["stock"][:12]}…), the V282 plain image ({sha["V282"][:12]}…) and the V289 plain image ({sha["V289"][:12]}…) by <code>v290_closeout_delta_from_images.py</code> — no build-script constant is used. Full-window diff [0x13000, 0x100000): stock→V282 <b>{dd["stock_vs_V282"]["bytes"]} bytes</b> in {dd["stock_vs_V282"]["runs"]} runs (gap ≤ 2 merged); V282→V289 <b>{dd["V282_vs_V289"]["bytes"]} bytes</b> in {dd["V282_vs_V289"]["runs"]} runs; stock→V289 {dd["stock_vs_V289"]["bytes"]} bytes. Rows shaded blue are V289\'s own additions. The "what it does" column is the lineage\'s reading (<code>V288-CUMULATIVE-NONSTOCK-DELTA-2026-09-07.md</code>); the values are this pass\'s bytes. ' + EV + ' for every value.</p>')
A(delta_table())
A('<p class="note">Not in the table because they are table families rather than cells: the V268 rate-lane / boost flatten (0xCE000–0xD9FFF and the 0xCBF5C / 0xCA4F4 families, ~1 KB, "inert below 85 deg/s"), the V38 setpoint-ceiling raise (0xCB844 records, 15360 → 16384) and the per-page CRC trailers. Three groups remain "not clean deliberate choices" per the lineage: 0xC61C0/C2/C4 (no lineage entry), 0xC40BC/D2/DC (ride the V255→V112 rebase; K1 measured NULL), 0xC64DE (validated under a label later found wrong). The V289 telemetry tail and notch cave (0xC4BDC–0xC4C8B) publish bits and filter S; they write no calibration cell (adversary D, GATE 1 census of the 12-byte state run).</p>')
A('<h3>Every relevant LERP, stock vs current, on the same axes ' + EV + '</h3>')
A('<div class="grid2">' + fig(lerp_map, "Assist map slot 7 (pointer table 0xC9A88 → record 0xE502C), the rate-loop REFERENCE. Y read from all three images; V289 == V282 byte for byte. Converted to deg/s with 1 sp = 0.1295 deg/s (32 / (fb_DC · 8), fb_DC from the image).", leg(("v289", "V282 / V289"), ("stock", "stock")))
  + fig(lerp_kp, "Kp slot 7 (0xCB994 → 0xE5378). Stock rises 248 → 696 with the demand index; V281 rev 3 flattened it to 248 and V282/V289 carry that.", leg(("v289", "V282 / V289"), ("stock", "stock")))
  + fig(lerp_kd, "Kd slot 7 (0xCB7D4 → 0xE511C): 128 flat on every image read. The D clamp 0xC61B6 = 10240 on all three as well.", leg(("stock", "stock"), ("v289", "V282 / V289")))
  + fig(lerp_taper, "The override taper arms (0xCB924 same-sign, 0xCB8B4 opposite-sign, slot 7) and the post-PID fade (0xCBA04). All three images identical: the taper is 255 flat to X 80 and 0 at X 112 (the cliff the record documents; the 0xE4 byte-2 field openpilot sends as 0 selects the live arm), the fade runs 254 → 0 over 70–80.", leg(("v289", "taper same-sign"), ("s16", "taper opposite-sign"), ("s7", "post-PID fade A"))) + '</div>')
A('<h3>Delivered-surface consequence, steady state, from the image cells</h3>')
A('<p>Steady P-only torque at the output clamp for a held 0xE4 command: setpoint from each image\'s own map staircase, then sp · 32 · Kp/256 · gain/32768, clamped at each image\'s own output clamp (stock: Kp LERP 248→696, gain 891 at 0xC646C, clamp 512; V282/V289: Kp 248 flat, gain 5346 at 0xC6CD0, clamp 3072). The kit\'s steady-state convention (Ki = 0, feedback at its DC value is what the setpoint is tracked against, so this is the ceiling the P path can present, not the delivered torque during a turn). V289 == V282 on every one of these cells: the notch has DC gain exactly 1 (254/254) and the moved fb pole changes DC by −0.017 %. ' + EV + ' for the cells; the convention is the kit\'s.</p>')
A(delivered_table())
A('<section class="card risk"><b>Risk statement for the base the car goes back to — stated before the flash.</b> V282 is the flown, characterised reference (r39, r3a, r3c): 6× forward gain with clamps tracking it, ±5 EME interlock quad, Lever B live at 5244, LKAS active at creep, Kp flat 248, map linear to 1032. <b>Its known symptom returns with it</b> — the 20 Hz grinding in low-speed loaded turns (presence 8–21 %, episodes 97–323/h across three routes) — and by the operator\'s own report that was the <i>quieter</i> of the two symptoms. Reverting V289 → V282 changes <b>185 bytes in 6 runs</b>: the 0x14A hook, the notch cave, the feedback-pole cells and two CRC trailers. <b>No authority cell moves; steady-state authority is ×1.000 either way.</b> Nothing on this page raises authority anywhere. ⚠ Naming a file here is not a flash instruction — the flash stays gated on the operator naming the file and the bus himself.</section>')

# ---------------------------------------------------------------- 5
A('<h2>5 · What V290 turned out to be: two objects, a placement finding, and a decision not to build</h2>')
A('<p class="lede">Four independent agents adjudicated the V290 question and converged. There are <b>two</b> objects in the band, not one, and V289 traded the first for the second. Every option that removes the 20 Hz object re-creates the 16 Hz one — that is what the class does, not a defect in V289\'s tuning. Of everything designed, exactly one candidate passes every constraint the operator set, and its delivered effect is ×1.22 on ring time, read through a contrast whose own error bar is 2.6× wider than that. The candidate with a real effect fails the transient-authority floor on its worst plant fit, 0.928 against 0.95. <b>Shown that table, the operator chose to revert to V282 and stop here. No V290 was built.</b></p>')

A('<h3>(a) The two objects ' + EV + '</h3>')
A('<p>The 2026-09-08 classification of the 20 Hz line as a plant mode the loop de-damps <b>survives</b> the V289 drives — the Kp pinning is now confirmed model-free at matched load, and the one competing explanation (clamp-limited effective Kp) is falsified by direct measurement. What V289 falsified is not the classification but the inference drawn the morning after it flew: that a phase-only edit moving the line proves the line was the crossover. It did not move the line. It <b>removed</b> it, and uncovered a second pole that was there all along.</p>')
A('<div class="diagram">' + two_objects_diagram() + '</div>')
A('<div class="grid2">' + fig(polemap_svg, "Every candidate's closed-loop poles between 12 and 30 Hz, over the 87 plant fits that are consistent with both the measured V282 line and V289's measured burst decay. Filled dots are resonances (ζ below 0.15); hollow dots are over-damped — no ring there. Dot area is poles per fit. Read the 15–18 Hz column: V282 and both Kd-schedule rows are empty; V289, C, D and B all carry one, in essentially 100 % of fits. Source: <code>basepick_v290.py table</code>.", leg(("s16", "a resonance (ζ < 0.15)"), ("stock", "over-damped — nothing rings")))
  + fig(ledger_svg, "Where V289's phase went. Curves computed from the filter coefficients read out of the built images (and, for option C and the 40 Hz pole, from the integers a build would round to). At the 16.63 Hz crossing the notch skirt costs −41.6° and the moved feedback pole gives back +11.5° — both reproduced here from the image bytes to 0.05° — for a net −30.1° against the 30° of margin V282 had there. (The recensus prints −28.9° for that sum; the two rungs it cites add to −30.1°. Either way the whole margin is spent.) Option C's shallower, lower-Q notch has a WORSE skirt at 16.6 Hz, not a better one.", leg(("v289", "V289 notch 20.04 Q3, ∠N"), ("s16", "option C notch 21.5 Q1.5, ∠N"), ("v282", "fb pole 16.5→25 Hz, Δ∠"), ("s7", "fb pole 16.5→40 Hz, Δ∠"))) + '</div>')
A('<section class="card"><b>The structural point, stated once.</b> Killing loop gain at 20 Hz drops the gain crossover into 15–17 Hz, where the plant carries more lag and the notch\'s own skirt retards the loop further. That is why <b>every notch-class option re-creates the 16 Hz object</b> — option C puts a pole at 16.53 Hz, ζ 0.057, in 100 % of the surviving fits; V289 measured 16.63 Hz at ζ 0.029. C is a better-damped version of the thing the operator has just told us he can hear. It is not a tuning error to be fixed by re-aiming: the re-aimed rows (notch at 16–17.5 Hz) all blow the 7 Hz gate to 1.03–1.08 or destabilise fits outright. ' + MOD + ' for the fit family; ' + EV + ' for the measured poles and the filter phases.</section>')

A('<h3>(b) The placement finding — the same filter, in two places ' + EV + ' (model, one input)</h3>')
A('<p>V289\'s notch cost 19–26 % of capped-step transient authority, and <b>no calibration edit on the V289 base recovers it</b> — pkR sits at 0.799–0.807 at every Kd from 64 to 128, because the filter is in <code>fwd()</code>, the reference transfer, not only in the loop. Move the identical element onto the feedback operand and the return ratio is unchanged to machine precision — same poles, same ζ, same Ms, same 7 Hz gate, same motor-noise ratio — while the command path is clean.</p>')
A('<div class="diagram">' + placement_diagram() + '</div>')
A(placement_table())
A('<p class="note">Rows re-read at render time from <code>reconcile_v290_table.json</code> (agent <code>reconcile</code>), SUB family = the 87 burst-consistent fits. The paired rows differ <b>only</b> in the two command-path columns — capped-step pkR and the step-response t90 (13 ms placed on the feedback operand, 19 ms placed forward). Every loop column is identical to the printed precision. 🛑 <b>V289\'s own design memo scored the feedback row; the build shipped the forward one, and no blocker for the feedback placement is recorded anywhere.</b> That is the most transferable finding of the session and it is a process finding, not a physics one.</p>')

A('<h3>(c) The candidates, at the DELIVERED dose ' + EV + '</h3>')
A('<p>The Kd record\'s X axis is the <b>LKAS demand index</b>, and its top knot is at index 32. A schedule that writes Y₀ = 96 does not give the car Kd 96 — it gives it whatever the demand index was during the seconds that matter. Every column below is read at the Kd that regime actually delivers, measured off the wire through <code>reqaxis</code>\'s byte-exact demand mirror over the r62+r63 grinding pool (2 553 samples = 25.5 s). ' + BEL + ' for substituting a regime-mean Kd into a curve that is near-linear in Kd; ' + EV + ' for the curve and for the delivered means.</p>')
A(candidate_table())
A('<p class="note">Ring = time for the ring to decay to 10 %, at the median fit, at that row\'s delivered dose. "16 Hz object" and "20 Hz object" are the pole census of the same 87 fits. C and D carry a cave; every row that carries a cave carries three CRC trailers. Row B is the only option that keeps V289 as its base, and it is the one that fails hardest.</p>')
A('<h4 style="margin-top:22px;font-size:14.5px">Why the earlier tables read differently — and by how much</h4>')
A(nominal_vs_delivered())
A('<p class="note">Two large errors pointing in opposite directions: the nominal reading flatters the effect and exaggerates the cost. Both earlier V290 memos scored the schedule nominally, and on those numbers row S looked like a hard 7 Hz FAIL at 1.073 and a ×2.1 win. It is neither. ' + QUO + ' from <code>basepick_delivered_dose.txt</code>.</p>')

A('<h3>(d) The Kd LERP, and where grinding actually sits on its axis ' + EV + '</h3>')
A('<p>The one plot that decides the schedule class. Above: the D gain each record delivers across the demand index, read from the record\'s own knots. Below: the measured distribution of that index over the grinding episodes on the two V289 routes, from the census cache through the same demand mirror — the histogram is what makes the curve above readable.</p>')
A('<div class="grid2" style="grid-template-columns:1fr">' + fig(kd_svg + kdhist_svg, f"Delivered Kd against demand index for base, S′, S and M1, over the measured grinding-episode index histogram. {GRIND_POOL['frac_gt32']*100:.0f} % of grinding seconds sit above index 32, where every Y-only record is byte-identical to the base — so the record that writes a 25 % cut (Y₀ = 96) delivers {(1-112.8/128)*100:.0f} %, and the one that writes 12.5 % (Y₀ = 112) delivers {(1-SPROW['kd289']/128)*100:.0f} %. The same protection is what keeps the two authority yardsticks intact: the capped-step and full-lock regimes live at index p50 {S5['pool']['step']['all']['p50']:.0f} and {S5['pool']['lock']['all']['p50']:.0f}. Data: <code>v290_closeout_s5_demand.json</code> (this pass, off the wire); delivered means reproduce basepick's 120.4 / 112.8 / 113.8 exactly.",
       leg(("stock", "base / V282 / V289 — Kd 128 flat"), ("v289", "S′ (112,112,112,128)"), ("s16", "S (96,96,96,128)"), ("s7", "M1 (96,96,112,128)"), ("grind", "share of grinding seconds"))) + '</div>')

A('<h3>(e) The schedule class is capped — and moving the knot is dominated ' + EV + '</h3>')
A('<div class="grid2">' + fig(frontier_svg, f"Every schedule record on one frontier: what it buys in ring time against what it spends on the 7 Hz strong-turn gate, both at the delivered dose. Solid line: records that only change Y, so the authority regimes stay byte-identical to base. Dashed: records that push the top knot X outward to reach further — they are dominated everywhere, because an X extension buys reach by spending precisely the full-lock protection it was chosen to preserve. Deleting the D term entirely below the knot (S0, an absurd build) reaches only ×{CEIL:.1f} and blows the gate to {S0ROW['gate']:.4f}: that is the class's ceiling at infinite dose.", leg(("v289", "Y-only records — protection intact"), ("s16", "X moved — protection SPENT"), ("cap", "the operator's 7 Hz gate, 1.010")))
  + fig(notchC_svg, "Option C's notch (21.5 Hz, Q 1.5) against V289's (20.04 Hz, Q 3.0), both at the Q14 integers a build would round to. C is shallower and wider: −13.4 dB at 20 Hz where V289 had −39.3 dB, and a deeper null at its own 21.5 Hz centre. At the 16.6 Hz crossing C attenuates MORE and retards MORE. Its advantage is placement, not shape.", leg(("v289", "V289, forward-placed"), ("s16", "option C, feedback-placed"))) + '</div>')
A(f'<p class="note">Under the operator\'s own 7 Hz gate of 1.010, exactly one schedule record qualifies — S′ (Y₀ = 112), sitting <i>at</i> the limit at {SPROW["gate"]:.4f} — and it delivers ring {DOSE[0]["ring_ms"]:.0f} → {SPROW["ring_ms"]:.0f} ms, ×{DOSE[0]["ring_ms"]/SPROW["ring_ms"]:.2f}. Row S itself reads 1.0171: a FAIL, as does every deeper variant.</p>')

A('<h3>(f) What was designed and not built: option C, in full</h3>')
A('<p>C is the build the analysis actually endorses on effect, and the one the operator declined on risk. It is specified to the byte here because the next session should not have to re-derive it — and because the pre-registered signature below is what makes it worth a drive at all.</p>')
A('<div class="grid2"><section class="card spec"><b>Option C — V282 + a feedback-operand notch</b>'
  '<dl class="spec">'
  '<dt>base</dt><dd>a fresh image from the V282 plain image — not derived from V289; reverting a 107-byte cave in place is strictly more risk than not writing it</dd>'
  '<dt>filter</dt><dd>biquad notch, 21.5 Hz, Q 1.5, on the <b>rate-feedback operand</b> (not on the loop output)</dd>'
  '<dt>Q14 integers</dt><dd class="mono">b = [15680, −31074, 15680] · a = [16384, −31074, 14976]</dd>'
  f'<dt>hook / cave</dt><dd class="mono">0x28F4C → 0xC4C90</dd>'
  f'<dt>fb lag pole</dt><dd>16.5 → 40 Hz · <span class="mono">0xC63E8/EA</span> {FB40_A} / {FB40_B}, holding the DC gain at 30.891 (the same rule that reproduces V282\'s 923/1560 and V289\'s 875/2301 exactly)</dd>'
  '<dt>cost</dt><dd>4 cal bytes + the cave · <b>3</b> CRC trailers (0xC4FFC, 0xC6FFC, and the cave page)</dd>'
  '<dt>effect</dt><dd>20 Hz object emptied (ζ_med +0.113) · ring 545 → 387 ms (×1.41) · ζ_w +0.0349, ×2.7 the base</dd>'
  '<dt>7 Hz gate</dt><dd class="ok">1.0092 — passes, with 0.0008 of the allowance left, which is why no schedule composes with it</dd>'
  '<dt>capped-step pkR</dt><dd><b class="bad">0.971 median, 0.928 worst fit</b> — the median passes, the worst fit does not</dd>'
  '<dt>motor noise</dt><dd>rms |R| 30–500 Hz ×1.91 · new 10–14 Hz sensitivity peak 2.0× V282\'s</dd>'
  '</dl>'
  '<p class="note" style="margin-top:12px">🛑 <b>NOT VERIFIED:</b> the hook\'s reachability, RAM ownership and register liveness at <code>0x28F4C</code> were not re-derived; C\'s dynamics were scored through a placement model. <b>BELIEF that C is implementable.</b> It would need its own adversarial pass and GATE 1 / GATE 2 before anything is written to disk.</p></section>'
  '<section class="card"><b>Its telemetry payload — and it fits exactly</b>'
  '<p class="note" style="margin-top:8px">0x14A byte 4 carries five bits we own. <code>instr290</code>\'s design allocates them against C\'s own coefficients — the Q14 integers in that memo are the identical ones above, so the instrument was designed for this build and no other.</p>'
  '<div class="tw" style="margin-top:10px"><table><thead><tr><th>bit</th><th>what it publishes</th><th>what it settles</th></tr></thead><tbody>'
  '<tr><td class="mono">b0–2</td><td>stock Honda, untouched</td><td>—</td></tr>'
  '<tr><td class="mono">b3</td><td>|d2| &gt; |d|</td><td>the second-difference rung</td></tr>'
  '<tr><td class="mono">b4, b6</td><td><b>held</b> — V282\'s r24 comparators, marked "must not move"</td><td>the cross-build control against V282 and V289; spending them destroys the comparison</td></tr>'
  '<tr><td class="mono">b5</td><td>sign(n), n = the removed component</td><td>LIVENESS. n has exactly zero DC gain, so its sign duty cannot be driven by any regime. Predicted 0.40–0.46 engaged, 0.18–0.32 disengaged, ≈0.49 symptomatic; the spectrum of 2·b5−1 must peak near 21.5 Hz. Sustained toggling while disengaged is a V290-only signature — V289\'s hook was inside the engaged path.</td></tr>'
  '<tr><td class="mono">b7</td><td>|n| ≥ 16 raw counts</td><td>DOSE. Symptom-to-quiet contrast 5.9–12.3× on the three yardstick routes. ⚠ Read the direction correctly: if C works, b7\'s symptomatic duty <b>falls</b> below r39\'s 0.68 — a falling b7 with a healthy b5 is the success signature, not a dead cave.</td></tr>'
  '</tbody></table></div>'
  '<p class="note">This is why option D — C plus the Kd schedule — is not buildable as one interpretable image: it needs five rungs and has three, and the only way to find two more is to spend b4/b6. It also blows the 7 Hz gate to 1.016–1.024. ' + QUO + ' from <code>DESIGN-V290-TELEMETRY-2026-09-09.md</code> §2.</p></section></div>')
A('<section class="card risk"><b>Pre-registered revert signature for C — written before any drive, and the reason C is the one worth flying.</b> C re-creates the 16 Hz object: a pole at 16.5 Hz, ζ_med +0.057, in 100 % of surviving fits — 1.7× better damped than V289\'s, but <b>inside the burst range (ζ_eff 0.02–0.13) the operator has already rejected</b>. Watch for: a 15–18 Hz line in trains; grinding lower-pitched than V282\'s; a new 10–14 Hz line; audible motor hiss. 🛑 <b>If C\'s 16.5 Hz pole is audible, the entire loop-shaping class is closed</b> — both notch placements, both bases, and the Kd schedule with them — and V291 must come from outside it. That is the most valuable thing C can tell us.</section>')

A('<h3>(g) The operator\'s decision</h3>')
A('<section class="card op"><p class="quote">"Revert to V282 and stop here."</p>'
  '<p style="margin:12px 0 0">Shown the re-scored table, the operator declined both surviving builds. <b>No V290 was built, and nothing was written to disk.</b> This is his call on a trade the analysis could not resolve for him, and it is recorded here as the session\'s outcome, not as a pending item.</p>'
  '<div class="verdict">'
  f'<div><b>Keep every constraint → S′</b>A ×{DOSE[0]["ring_ms"]/SPROW["ring_ms"]:.2f} ring improvement, at the gate limit, on half the grinding population. Two independent findings say it cannot be read from one short drive: the delivered effect is ×1.22, and the within-drive stratified contrast\'s own CI is ×0.34–2.01 — <b>2.6× wider than the effect</b> — with the two operator-facing channels confounded in the flattering direction. A build that cannot observe its own edit\'s effect does not get a drive.</div>'
  '<div><b>Relax pkR on the worst fit → C</b>×2.7 damping on the 20 Hz object, acting on every episode rather than half of them, for a ~7 % transient peak-rate loss on the least favourable plant fit (0.928 against the 0.95 floor; the median is 0.971). V289\'s 0.91 was accepted once and explicitly is not the new floor.</div>'
  '<div><b>What he chose</b>Neither. Revert to V282 — the flown, characterised base — and spend no drive on a ×1.22 effect that cannot be read, nor on a build whose own pre-registration says it re-creates the object he is complaining about.</div>'
  '</div>'
  '<p class="note" style="margin-top:14px">Reverting V289 → V282 changes 185 bytes in 6 runs (hook, cave, fb-pole cells, two CRC trailers). No authority cell moves; steady-state authority is unchanged at ×1.000. Nothing in this section raises authority anywhere.</p></section>')
A('<section class="card"><b>What is now closed, and what is not.</b><ul style="margin:10px 0 0">'
  '<li><b>Closed — the reference side.</b> V288 rev 2 made every per-tick setpoint step ~11× finer and cut D-clamp binds ×0.03; grinding was unchanged. The excitation is not on the reference side.</li>'
  '<li><b>Closed — the added post-lag damping term, either sign.</b> (1−N)/8 bypasses the 5 Hz output lag and re-injects exactly the 20 Hz content the notch removed; minus drives the 16.4 Hz pole to ζ −0.041…−0.082, plus removes it but the crossover reappears at 26.9 Hz at ζ +0.006.</li>'
  '<li><b>Closed — proportional rate feedback in any form.</b> Sweeping a scalar loop-gain multiplier over the V289 loop drives ζ negative on 8 of 8 fits: at this crossing it is a phase-lag de-damper, not a spring.</li>'
  '<li><b>Closed — the Kd-schedule X lever.</b> Deepening Y weakly dominates extending X along the whole frontier.</li>'
  '<li><b>Open — the feedback-operand placement (option C).</b> Designed, scored, instrumented, not verified at the hook and not built.</li>'
  '<li><b>Open — outside the loop entirely.</b> A fork-side lever in the StarPilot Accord path removes ~9 % of the torque line\'s drive; it is not a cure and does not touch ζ, but it stands regardless of which physics picture holds.</li>'
  '<li><b>Open — the 7.5 Hz strong-turn ring.</b> On both V289 bookmarks it was the last loud thing before the press, 2.4–2.6 s ahead of it, at 1277 and 1412 raw. Nothing in the V290 family addresses it, and which of the two objects the operator calls grinding is his to say. ' + BEL + '</li>'
  '</ul></section>')
A('<p class="note">🛑 <b>Nothing in this section was built, flashed or sent.</b> Option C\'s numbers are model figures over a plant family conditioned on measured poles; its hook is unverified. Expected-telemetry duties are printed only for C, and only because they are computed on measured operands from three routes.</p>')

# ---------------------------------------------------------------- 6
A('<h2>6 · Cross-build matrix, V38 → V289, read from 26 images ' + EV + '</h2>')
A('<p><code>ledger_v38_to_v289_bytes.py</code> reads the same cells from every flight-line plain image (anchors: 0xC646C = 891 and 0x454FE = 0xBA on stock). A dot means "equal to stock"; shaded cells differ. Banks are shown as their Y-knot extremes. The output-lag pole (992/507) and the three PID clamps (10240 / 15360 / 15360) are constant across all 26 images and are omitted.</p>')
A(matrix())
_img_count_txt = f"{PLAIN_IMAGE_COUNT} images (every <code>*_plain_image.bin</code> in accord-firmwares, counted at render time)" if PLAIN_IMAGE_COUNT is not None else "an uncounted set of images (accord-firmwares not found at render time)"
A(f'<p class="note">Class against the arc: V38–V52 authority, filters, poles, caves · V53–V61 probes · V62–V73 the rate lane · V74–V84 the damper · V87–V124 gain steps and the assist-lane notches (a different, always-on loop) · V235–V268 damper cells back to Honda · V276–V285 the REFERENCE and the rate PID\'s gains · V288 the reference pre-filter (outside the loop, flown inert) · V289 the first in-loop filter on the LKAS rate loop\'s own output and the first move of the fb pole in {_img_count_txt} — flown; its target met and its revert signature met. The line stops here: <b>no V290 was cut.</b></p>')

A('<h2 style="font-size:16px;margin-top:40px">Sources</h2><ul class="note" style="max-width:none">'
  '<li>Drives: <code>rlog-tools/studies/grind/V289-QLIVE-R62-R63-2026-09-09.md</code> (qlive62), <code>V289-MARKS-R62-R63-2026-09-09.md</code> (marks62), <code>_scratch/grind1_census_v289_r62_r63.txt</code> + <code>grind1_census_v289_agnostic.txt</code> (census62). PSD: <code>_scratch/v290page_psd.json</code>; timelines: <code>_scratch/out/v290_closeout_marks.json</code>.</li>'
  '<li>Notch / fb-pole curves: <code>_scratch/out/v289_page_data.json</code> (decoded from the V289 image by <code>_v289_lerp_reader.py</code>); loop model rows: <code>docs/specs/design/DESIGN-V290-2026-09-09.md</code>.</li>'
  '<li>H1: <code>_scratch/out/h1_figdata_2026-09-09.json</code> + <code>docs/review/H1-FIGURES-README-2026-09-09.md</code> (h1fig2); <code>docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md</code> (hyptable).</li>'
  '<li>Delta and LERPs: <code>_scratch/out/v290_closeout_delta.json</code> (this pass, from the images); the independent cumulative enumeration and its attribution census in <code>docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md</code>; lineage readings from <code>V288-CUMULATIVE-NONSTOCK-DELTA-2026-09-07.md</code> and <code>V289-LERPS-FROM-IMAGE-2026-09-08.md</code>. Matrix: <code>_scratch/out/ledger_v38_to_v289.json</code>.</li>'
  '<li>The two objects and the plant back-out: <code>rlog-tools/studies/grind/MODE-NATURE-V289-RECENSUS-2026-09-09.md</code> (modenat2). Candidates, poles, delivered dose: <code>docs/review/V290-BASE-DECISION-2026-09-09.md</code> + its ADDENDUM (basepick), rendered here from <code>_scratch/basepick_v290_table.json</code> and <code>_scratch/basepick_delivered_dose.json</code>. Placement: <code>_scratch/reconcile_v290_table.json</code> (reconcile). Demand-index histograms: <code>_scratch/out/v290_closeout_s5_demand.json</code> (this pass, <code>v290_closeout_s5_demand_hist.py</code>). Telemetry: <code>docs/specs/design/DESIGN-V290-TELEMETRY-2026-09-09.md</code> (instr290). Readability and parametric hazard: <code>V290-ROWS-READABILITY-2026-09-09.md</code> (powerS), <code>V290-PARAMETRIC-HAZARD-2026-09-09.md</code> (paramod).</li>'
  '</ul>')
A('</main>')

open(OUT, "w", encoding="utf-8").write("\n".join(html))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
