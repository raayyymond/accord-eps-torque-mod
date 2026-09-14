# -*- coding: utf-8 -*-
"""v293_ident_h.py -- THE RATCHET: is the operator's "snaps between angles" STICK-SLIP?
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Operator's words on route 70: "I did not experience any classic grinding or stuttering" and "steering
felt ratchety, like the wheel did not move smoothly but only snapped between angles rather than
smoothly moving between them."  Later: "sometimes loose, sometimes oversteer, on hard transients it
would overshoot then correct slightly."

HYPOTHESIS UNDER TEST (not assumed): with the EPS rate loop open, column/rack static friction is no
longer linearised by the rate servo, so the outer loop winds torque up until breakaway, the wheel
jumps, and it sticks again.  Signature: a BIMODAL |rate| distribution (a mass at zero plus a slip
lobe), dwell-then-jump run structure, a breakaway torque above the running torque, and a snap
amplitude that does not scale with the commanded step.

EVERY STATISTIC IS RUN IDENTICALLY ON V282 REFERENCES (r6c, r39) so the contrast is like-for-like.
That is the whole point: the same road, the same instruments, a closed rate loop instead of an open one.

🛑 INSTRUMENT NOTE.  The 0x14A angle quantises at 0.1 deg, so the ANGLE looks staircased at low rates
whatever the plant does.  The 0x18F rate is a separate field at 0.125 deg/s and is NOT a difference of
the quantised angle (a difference would come in multiples of 10 deg/s at 100 Hz).  Every dwell/slip
statistic below is therefore computed on the RATE, and the angle quantiser is measured as a control.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = L.KIT
V280 = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
OUT = []
pr = L.pr_factory(OUT)
FS = 100.0
DT = 1.0 / FS
CPD = 8.0
RES = {}

ROUTES = [("r70_v293", "V293", "route 70, the drive being scored"),
          ("r6c", "V282", "nearest-in-time V282 reference"),
          ("r39", "V282", "the V282 read route")]
BANDS = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
BNAME = ["0-5", "5-10", "10-20", ">20"]


def load(tag):
    d = dict(np.load(os.path.join(V280, tag + ".npz")))
    t0 = d["t18"][0]
    t1 = min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1])
    tg = np.arange(0.0, t1 - t0, DT)
    ta = tg + t0
    g = dict(t=tg, tag=tag)
    g["bar"] = L.zoh(ta, d["t18"], d["tq"])
    g["wire"] = L.zoh(ta, d["t18"], d["rate"])
    g["sca"] = L.zoh(ta, d["t18"], d["sca"])
    g["ang"] = L.zoh(ta, d["t14"], d["ang"])
    g["cmd"] = L.zoh(ta, d["te4"], d["cmd"])
    g["req"] = L.zoh(ta, d["te4"], d["req"])
    g["T"] = L.zoh(ta, d["t1ab"], L.tap_decode(d["b0"], d["b1"]))
    g["v"] = L.zoh(ta, d["tcs"], d["vego"])
    g["press"] = L.zoh(ta, d["tcs"], d["cs_press"]) if "cs_press" in d else np.zeros(len(tg))
    g["has_press"] = "cs_press" in d
    g["rate"] = g["wire"] / CPD                       # deg/s, LSB 0.125
    g["eng"] = (g["req"] > 0.5) & (g["sca"] > 0.5)
    return g


pr("=" * 108)
pr("V293 -- THE RATCHET: stick-slip test on route 70, against V282 references")
pr("=" * 108)

G = {}
for tag, build, note in ROUTES:
    try:
        G[tag] = load(tag)
        G[tag]["build"] = build
    except Exception as ex:
        pr("  %s: could not load (%s)" % (tag, str(ex)[:80]))

# ------------------------------------------------------------------------------------------------
pr("\nH0. THE MASK -- and why the driver-torque bar CANNOT stand in for steeringPressed [EVIDENCE]")
pr("    r70 carries carState.steeringPressed; r6c and r39 do not.  The obvious substitute, a")
pr("    threshold on the 0x18F bar, FAILS: on this car the bar reads the TWIST the EPS itself puts")
pr("    into the torsion bar, not the driver (the kit's own standing result -- grinding is a")
pr("    hands-off phenomenon and the bar signal is twist).  Measured on r70, where both exist:")
g = G["r70_v293"]
e = g["eng"]
pr("    %-14s %10s %14s %14s %14s"
   % ("threshold", "% of eng", "P(<th | off)", "P(<th | ON)", "balanced acc"))
for th in (50, 100, 200, 300, 500, 800):
    off = e & (g["press"] < 0.5); on = e & (g["press"] > 0.5)
    a_ = float(np.mean(np.abs(g["bar"][off]) < th)); b_ = float(np.mean(np.abs(g["bar"][on]) < th))
    pr("    |bar| < %-6d %9.1f%% %14.3f %14.3f %14.3f"
       % (th, 100 * (e & (np.abs(g["bar"]) < th)).sum() / max(e.sum(), 1), a_, b_,
          0.5 * (a_ + (1 - b_))))
pr("    => no threshold separates them.  EVERY CROSS-ROUTE STATISTIC BELOW THEREFORE USES ALL")
pr("       LATERALLY ENGAGED FRAMES on all three routes, like-for-like.  r70's hands-off and")
pr("       hands-on strata are compared against each other in H7, where steeringPressed exists.")


def hands_off(g):
    return g["eng"]


# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H1. IS |rate| BIMODAL?  the distribution of the wheel rate on laterally engaged frames.")
pr("    A linear plant driven by a smooth command gives a smooth unimodal |rate|.  Stick-slip gives")
pr("    a spike at zero plus a separated slip lobe.  Bin edges are in RATE LSBs (0.125 deg/s).")
pr("=" * 108)
EDGES = np.array([0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 9.0, 15.0, 30.0, 1e9])
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    m = hands_off(g)
    pr("\n    %-10s (%s)  %s" % (tag, build, note))
    pr("    %-8s %8s %8s" % ("band", "sec", "P(|rate|=0)") +
       "".join("%7s" % ("<%.3g" % x) for x in EDGES[1:8]))
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        if s.sum() < 500:
            continue
        r = np.abs(g["rate"][s])
        h, _ = np.histogram(r, bins=EDGES)
        h = h / h.sum()
        pr("    %-8s %8.0f %8.3f" % (BNAME[k], s.sum() * DT, float(np.mean(r < 1e-9)))
           + "".join("%7.3f" % x for x in h[:7]))
        RES.setdefault("hist", {}).setdefault(tag, {})[BNAME[k]] = dict(
            sec=s.sum() * DT, zero=float(np.mean(r < 1e-9)), hist=[float(x) for x in h])

pr("\n    the same as a single discriminator -- the share of laterally engaged time with the wheel")
pr("    EXACTLY STILL (rate field == 0), which is the stick fraction:")
pr("    %-10s %-6s" % ("route", "build") + "".join("%10s" % b for b in BNAME) + "%10s" % "all")
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    row = []
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        row.append(float(np.mean(g["wire"][s] == 0)) if s.sum() > 500 else np.nan)
    pr("    %-10s %-6s" % (tag, build) + "".join("%10.3f" % x for x in row)
       + "%10.3f" % float(np.mean(g["wire"][m] == 0)))

pr("\n    🛑 THE CONTROL THAT MATTERS: is the wheel STICKING, or merely MOVING SLOWER?  A slower wheel")
pr("    shifts the whole distribution down; a sticking wheel puts an EXCESS SPIKE AT EXACTLY ZERO.")
pr("    The discriminator is the ratio  P(rate == 0) / P(0 < |rate| <= 0.25 deg/s)  -- the spike")
pr("    against its own immediate neighbourhood, which is insensitive to how fast the wheel moves.")
pr("    rms|rate| is printed beside it to show the distributions are not simply shifted.")
pr("\n    %-10s %-6s %-8s %10s %10s %12s %12s"
   % ("route", "build", "band", "P(rate=0)", "P(0,0.25]", "SPIKE RATIO", "rms |rate|"))
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        if s.sum() < 500:
            continue
        r = np.abs(g["rate"][s])
        p0 = float(np.mean(r < 1e-9))
        p1 = float(np.mean((r > 1e-9) & (r <= 0.25)))
        pr("    %-10s %-6s %-8s %10.4f %10.4f %12.3f %12.3f"
           % (tag, build, BNAME[k], p0, p1, p0 / max(p1, 1e-9), float(np.sqrt(np.mean(r ** 2)))))
        RES.setdefault("spike", {}).setdefault(tag, {})[BNAME[k]] = dict(
            p0=p0, p1=p1, ratio=p0 / max(p1, 1e-9), rms=float(np.sqrt(np.mean(r ** 2))))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H2. DWELL / SLIP RUN STRUCTURE")
pr("    dwell = |rate| <= 0.25 deg/s (2 LSB) for >= 0.10 s.  slip = the motion between two dwells.")
pr("    'snap' is the ANGLE CHANGE across one slip, in degrees -- the operator's step size.")
pr("=" * 108)
DWELL_TH, DWELL_MIN = 0.25, int(0.10 * FS)


def runs_of(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


pr("\n    %-10s %-6s %-8s %8s %9s %9s %9s %9s %9s %9s"
   % ("route", "build", "band", "sec", "dwell %", "slips/s", "snap p50", "snap p90",
      "dwell p50", "peakrate"))
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        if s.sum() < 800:
            continue
        # work inside contiguous engaged, in-band stretches only
        segs = runs_of(s, int(2 * FS))
        if not segs:
            continue
        dw_frac, snaps, dwl, nslip, tot, peaks = 0, [], [], 0, 0, []
        for (a, b) in segs:
            r = g["rate"][a:b]; ang = g["ang"][a:b]
            still = np.abs(r) <= DWELL_TH
            dws = runs_of(still, DWELL_MIN)
            dw_frac += sum(j - i for i, j in dws)
            tot += (b - a)
            for q in range(len(dws) - 1):
                i0, j0 = dws[q]
                i1, j1 = dws[q + 1]
                if i1 <= j0:
                    continue
                snaps.append(abs(ang[i1] - ang[j0 - 1]))
                peaks.append(float(np.max(np.abs(r[j0:i1]))))
                nslip += 1
            dwl += [(j - i) * DT for i, j in dws]
        if tot == 0 or nslip < 4:
            continue
        pr("    %-10s %-6s %-8s %8.0f %9.3f %9.3f %9.3f %9.3f %9.3f %9.2f"
           % (tag, build, BNAME[k], tot * DT, dw_frac / tot, nslip / (tot * DT),
              np.percentile(snaps, 50), np.percentile(snaps, 90), np.percentile(dwl, 50),
              np.percentile(peaks, 50)))
        RES.setdefault("dwell", {}).setdefault(tag, {})[BNAME[k]] = dict(
            sec=tot * DT, dwell_frac=dw_frac / tot, slips_per_s=nslip / (tot * DT),
            snap_p50=float(np.percentile(snaps, 50)), snap_p90=float(np.percentile(snaps, 90)),
            dwell_p50=float(np.percentile(dwl, 50)), peak_p50=float(np.percentile(peaks, 50)))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H3. BREAKAWAY vs RUNNING TORQUE -- the friction band, in delivered 427 counts and in openpilot")
pr("    output units (1.0 = 4096 counts of 0xE4 = 2489 delivered counts, measured in part B).")
pr("    🛑 measured on the 100 Hz 0xE4 COMMAND mapped to delivered counts, NOT on the 427 tap: the")
pr("    tap is 50 Hz and quantised at 8 counts, and a dwell lasts only ~0.12 s, so the tap cannot")
pr("    resolve the event.  On V293 the map is exact (|tap| = 0.6077*|cmd|, R2 0.966) so the command")
pr("    IS the torque; on V282 the same factor is used, which is an APPROXIMATION there (its lane")
pr("    carries a rate-feedback term), so the V282 rows are indicative only.")
pr("    For every dwell >= 0.10 s: the torque at the last dwell frame (HOLD), at the frame motion")
pr("    starts (BREAKAWAY), and when the next dwell begins (the torque at which motion STOPS).")
pr("=" * 108)
pr("\n    %-10s %-6s %-8s %7s %11s %11s %11s %11s %11s"
   % ("route", "build", "band", "n", "hold |tap|", "breakaway", "stop |tap|", "brk-hold", "brk in u"))
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        segs = runs_of(s, int(2 * FS))
        hold, brk, stop = [], [], []
        for (a, b) in segs:
            r = g["rate"][a:b]; T = np.abs(g["cmd"][a:b]) * 0.6077
            dws = runs_of(np.abs(r) <= DWELL_TH, int(0.10 * FS))
            for q in range(len(dws)):
                i0, j0 = dws[q]
                hold.append(float(np.median(T[i0:j0])))
                if j0 < len(T):
                    brk.append(float(T[min(j0 + 1, len(T) - 1)]))
                if q + 1 < len(dws):
                    stop.append(float(T[dws[q + 1][0]]))
        if len(brk) < 6:
            continue
        pr("    %-10s %-6s %-8s %7d %11.1f %11.1f %11.1f %11.1f %11.4f"
           % (tag, build, BNAME[k], len(brk), np.median(hold), np.median(brk), np.median(stop),
              np.median(brk) - np.median(hold), (np.median(brk) - np.median(hold)) / 2489.0))
        RES.setdefault("breakaway", {}).setdefault(tag, {})[BNAME[k]] = dict(
            n=len(brk), hold=float(np.median(hold)), brk=float(np.median(brk)),
            stop=float(np.median(stop)))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H4. IS THE COMMAND STEPPING, OR THE WHEEL?  ruling out a stepwise 0xE4 as the cause")
pr("    Each signal is scored by its own quantiser: the fraction of 10 ms frames in which it does")
pr("    NOT change at all, and the ratio of the rms of its second difference to the rms of its")
pr("    first difference (a staircase has a large second difference relative to its first).")
pr("=" * 108)
pr("\n    %-10s %-6s %-8s %9s %9s %9s %9s %9s %9s"
   % ("route", "build", "band", "cmd hold", "ang hold", "rate hold", "cmd d2/d1", "ang d2/d1",
      "rate d2/d1"))


def steppiness(x):
    d1 = np.diff(x); d2 = np.diff(d1)
    hold = float(np.mean(d1 == 0))
    ratio = float(np.sqrt(np.mean(d2 ** 2)) / max(np.sqrt(np.mean(d1 ** 2)), 1e-12))
    return hold, ratio


for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        segs = runs_of(s, int(5 * FS))
        if not segs:
            continue
        vals = {}
        dcm = [np.sqrt(np.mean(np.diff(g["cmd"][a:b]) ** 2)) for (a, b) in segs]
        for nm, arr in (("cmd", g["cmd"]), ("ang", g["ang"]), ("rate", g["wire"])):
            hs, rs, w = [], [], []
            for (a, b) in segs:
                h, r_ = steppiness(arr[a:b])
                hs.append(h); rs.append(r_); w.append(b - a)
            vals[nm] = (float(np.average(hs, weights=w)), float(np.average(rs, weights=w)))
        pr("    %-10s %-6s %-8s %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f"
           % (tag, build, BNAME[k], vals["cmd"][0], vals["ang"][0], vals["rate"][0],
              vals["cmd"][1], vals["ang"][1], vals["rate"][1])
           + "  rms dcmd %6.2f" % float(np.mean(dcm)))
pr("\n    NOTE the 0x14A angle quantiser is 0.1 deg, so 'ang hold' is high on EVERY build whenever")
pr("    the wheel is slow -- it is a control, not a result.  The discriminator is 'rate hold' and")
pr("    'rate d2/d1', because the 0x18F rate field is an independent 0.125 deg/s measurement.")

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H5. DOES THE 1-4 Hz LINE COINCIDE WITH THE SLIPS?")
pr("    the slip-event train (a unit impulse at each breakaway) is spectrally analysed and compared")
pr("    with the 1-4 Hz angle line the scorer flagged at 0-5 m/s.")
pr("=" * 108)
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]; m = hands_off(g)
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        s = m & (g["v"] >= lo) & (g["v"] < hi)
        segs = runs_of(s, 512)
        if not segs:
            continue
        trainP = angP = None
        nn = 0
        for (a, b) in segs:
            r = g["rate"][a:b]
            dws = runs_of(np.abs(r) <= DWELL_TH, DWELL_MIN)
            tr = np.zeros(b - a)
            for q in range(len(dws) - 1):
                if dws[q][1] < len(tr):
                    tr[dws[q][1]] = 1.0
            if tr.sum() < 3:
                continue
            f, p1 = signal.welch(tr - tr.mean(), fs=FS, nperseg=512, noverlap=256)
            _, p2 = signal.welch(signal.detrend(g["ang"][a:b]), fs=FS, nperseg=512, noverlap=256)
            trainP = p1 * (b - a) if trainP is None else trainP + p1 * (b - a)
            angP = p2 * (b - a) if angP is None else angP + p2 * (b - a)
            nn += (b - a)
        if trainP is None:
            continue
        trainP /= nn; angP /= nn
        sel = (f >= 0.5) & (f <= 6.0)
        ft = f[sel][int(np.argmax(trainP[sel]))]
        fa = f[sel][int(np.argmax(angP[sel]))]
        a14 = np.sqrt(np.sum(angP[(f >= 1) & (f < 4)]) * (f[1] - f[0]))
        pr("    %-10s %-6s %-8s  slip-train peak %5.2f Hz | angle peak %5.2f Hz | angle 1-4 Hz amp %7.4f deg"
           % (tag, build, BNAME[k], ft, fa, a14))
        RES.setdefault("line", {}).setdefault(tag, {})[BNAME[k]] = dict(
            slip_peak=float(ft), ang_peak=float(fa), ang_1_4=float(a14))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H6. DOES THE COMMAND RAMP BETWEEN SNAPS?  (integrator winding into a stiction band)")
pr("    For every dwell >= 0.10 s: the slope of the commanded torque across the dwell, in delivered")
pr("    counts per second, and its change over the 0.2 s AFTER breakaway (wind-up-then-release shows")
pr("    a positive ramp during the dwell and a drop after).")
pr("=" * 108)
pr("\n    %-10s %-6s %-8s %7s %14s %16s %14s"
   % ("route", "build", "band", "n", "ramp cnt/s", "drop after brk", "hands-on ramp"))
for tag, build, note in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    for use_ho in (True,):
        m = hands_off(g)
        for k in range(len(BANDS)):
            lo, hi = BANDS[k]
            s = m & (g["v"] >= lo) & (g["v"] < hi)
            segs = runs_of(s, int(2 * FS))
            ramps, drops = [], []
            for (a, b) in segs:
                r = g["rate"][a:b]; T = np.abs(g["cmd"][a:b]) * 0.6077
                for (i0, j0) in runs_of(np.abs(r) <= DWELL_TH, int(0.10 * FS)):
                    n = j0 - i0
                    if n < 5:
                        continue
                    x = np.arange(n) * DT
                    sl = np.polyfit(x, T[i0:j0], 1)[0]
                    ramps.append(sl)
                    k2 = min(j0 + 20, len(T) - 1)
                    drops.append(T[k2] - T[j0])
            if len(ramps) < 6:
                continue
            pr("    %-10s %-6s %-8s %7d %14.1f %16.1f %14s"
               % (tag, build, BNAME[k], len(ramps), np.median(ramps), np.median(drops), "-"))
            RES.setdefault("ramp", {}).setdefault(tag, {})[BNAME[k]] = dict(
                n=len(ramps), ramp=float(np.median(ramps)), drop=float(np.median(drops)))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("H7. DOES A HAND ON THE WHEEL SUPPRESS IT?  the same dwell statistics with the driver pressing")
pr("=" * 108)
g = G["r70_v293"]
pr("\n    %-14s %8s %9s %9s %9s" % ("stratum", "sec", "dwell %", "slips/s", "snap p50"))
for nm, m in (("hands-off", g["eng"] & (g["press"] < 0.5)),
              ("hands-ON", g["eng"] & (g["press"] > 0.5)),
              ("disengaged", (~g["eng"]) & (g["v"] > 3))):
    segs = runs_of(m, int(2 * FS))
    dw, snaps, nslip, tot = 0, [], 0, 0
    for (a, b) in segs:
        r = g["rate"][a:b]; ang = g["ang"][a:b]
        dws = runs_of(np.abs(r) <= DWELL_TH, DWELL_MIN)
        dw += sum(j - i for i, j in dws); tot += (b - a)
        for q in range(len(dws) - 1):
            i1 = dws[q + 1][0]; j0 = dws[q][1]
            if i1 > j0:
                snaps.append(abs(ang[i1] - ang[j0 - 1])); nslip += 1
    if tot < 500 or nslip < 4:
        pr("    %-14s %8.0f  (too little)" % (nm, tot * DT)); continue
    pr("    %-14s %8.0f %9.3f %9.3f %9.3f"
       % (nm, tot * DT, dw / tot, nslip / (tot * DT), np.percentile(snaps, 50)))

with open(os.path.join(L.SCRATCH, "v293_ident_h.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_h.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_h.txt / .json")
