# -*- coding: utf-8 -*-
"""advB3b_v293_b4578.py -- ADVERSARY B, criteria B4 / B5 / B7(band) / B8 on the BUILT V293.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY -- reads images and rlog caches, writes one text file.

WHAT THE DESIGN'S OWN SCRIPTS DO NOT DO, and this does:
  B4  F7 (the 2-8 Hz rate-envelope trip rate per 100 s) at BOTH candidate arms and BOTH kappa.
      v293_s4 reports rip/level only; F7 is half the pre-registered clause and was never scored.
  B5  the STOCK leg.  The prereg gates the 5-9 Hz rise on BOTH "vs V282 >= 1.6" AND "vs STOCK >= 1.2";
      v293_s4 scored only vs V282, so the gate could not fire or clear.  Stock is replayed with
      stock's OWN cells, at BOTH readings of its r24 arm (the 0x3AA96 = 0xC5 gate question).
      Also: is the rise a RESONANT LINE or BROADBAND?  (spectral peakiness inside 5-9 Hz.)
  B7  the 13-17 Hz band ratio explicitly (s2 reports 9-18 pooled and a 12-17 "sel band" on r6c only).
  B8  the forced 18-22 Hz response with the loop open, sized against V282's ring, on r39 AND r6c.
  everywhere: Kp 120 (the BYTE value) as well as the design's 119.

Run: python advB3b_v293_b4578.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\advB3b"
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                       # noqa: E402
import design290b_candidates as D                   # noqa: E402
import grind_incident_r35 as GI                     # noqa: E402
import v292_replay_lib as R                         # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_lib as L                                # noqa: E402
import v293_s2_replay as S293                       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K, CPD = 100.0, 1000.0, 8.0
STOCK = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin"
NAMED = [225, 215, 38, 117]
OUT = []
RES = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def load_route(tag, img):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    c = GI.read_cells(img)
    g["cells"] = c
    g["idx_live"], g["sgn_live"] = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    g["sp_live"] = g["sgn_live"] * GI.lerp(c["map_X"], c["map_Y"], np.round(g["idx_live"]))
    g["f0"] = 20.0
    return g


def windows(g, kind, n=6, half=150):
    """kind 'b5'  : engaged, |angle| >= 30 deg, HANDS-LIGHT (|bar| <= 400)
       kind 'b4'  : engaged, |angle| >= 30 deg, LOADED (|bar| >= 800)   -- the strong-turn stratum
    """
    ang = np.abs(g["ang"]) if "ang" in g else np.full(len(g["t"]), np.nan)
    bar = np.abs(g["bar"])
    if kind == "b5":
        m = g["eng"] & (ang >= 30.0) & (bar <= 400.0)
    else:
        m = g["eng"] & (ang >= 30.0) & (bar >= 800.0)
    dens = np.convolve(m.astype(float), np.ones(2 * half) / (2 * half), mode="same")
    order = np.argsort(-dens)
    out, used = [], []
    for p0 in order:
        if dens[p0] < 0.50:
            break
        if p0 - half < 60 or p0 + half > len(g["t"]) - 20:
            continue
        if any(abs(p0 - q) < 2 * half for q in used):
            continue
        if not g["eng"][p0 - half:p0 + half].all():
            continue
        out.append((int(p0 - half), int(p0 + half), int(p0)))
        used.append(p0)
        if len(out) >= n:
            break
    return out


def f7_duty(wire1k, thr=103.0, fs=FS1K):
    """THE F7 DETECTOR'S OWN FRONT END, as far as a 3 s window can carry it.

    The record's F7 (`strongturn_r32_r33.fixed_thr_episodes`, thr 103, band 2-8 Hz) is an episode
    counter over a WHOLE ROUTE: engaged runs >= 1 s whose 2-8 Hz Hilbert rate envelope exceeds 103
    raw wire counts, merged if < 1 s apart, then filtered to |angle| >= 30 and fdom >= 6 Hz, and
    expressed per 100 s of engaged HIGH-ANGLE time.

    🛑 A 3 s replay window CANNOT produce a per-100-s episode rate; that is a route-level statistic.
    What a window CAN carry, with the same threshold and the same band, is the DUTY -- the fraction
    of the window whose envelope is above 103 -- and the envelope's p90.  V282 is run through the
    identical function on the identical windows, so the RATIO is transferable; the record's own
    on-car V282 F7 (0.51 /100 s) then converts it to a predicted rate.  Declared, not hidden.
    """
    from scipy.signal import butter, filtfilt, hilbert
    b, a = butter(2, [2.0 / (fs / 2), 8.0 / (fs / 2)], btype="band")
    env = np.abs(hilbert(filtfilt(b, a, np.asarray(wire1k, float))))
    return float(np.mean(env > thr)), float(np.percentile(env, 90))


def peakiness(x, lo=5.0, hi=9.0, fs=FS1K):
    """peak PSD inside the band / median PSD inside the band -- a resonant line reads high."""
    x = np.asarray(x, float)
    x = x - x.mean()
    n = len(x)
    w = np.hanning(n)
    P = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / fs)
    m = (f >= lo) & (f <= hi)
    if m.sum() < 4:
        return np.nan
    return float(np.max(P[m]) / np.median(P[m]))


def ripple_level(T, lo=6.0, hi=8.5):
    amp = R.band_amp(np.asarray(T, float), lo, hi)
    lev = float(np.median(np.abs(np.asarray(T, float))))
    return amp, lev, (amp / lev if lev > 1e-9 else np.nan)


# ================================================================================================
def main():
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    named = [D.mkplant(byid[i]) for i in NAMED]

    c282 = L.read_cells(L.IMG282)
    c293 = L.read_cells(L.IMG293) if hasattr(L, "IMG293") else None
    cST = GI.read_cells(STOCK)
    pr("=" * 126)
    pr("ADVERSARY B -- B4 / B5 / B7(band) / B8 on the BUILT V293.   agent advB3b, 2026-09-13. ANALYSIS ONLY")
    pr("=" * 126)
    pr("cells read LE from the images:")
    pr("  V282  fb_clamp %d  Kp[0] %s  Kd[0] %s  r24 eng %d  gain %d  t_clamp %d  map top %d"
       % (c282["fb_clamp"], c282["kp_Y"][0], c282["kd_Y"][0], c282["r24_arm"], c282["gain"],
          c282["t_clamp"], c282["map_Y"][-1]))
    pr("  STOCK fb_clamp %d  Kp[0] %s  Kd[0] %s  r24 eng %s  gain %d  t_clamp %d  map top %d"
       % (cST.get("fb_clamp", -1), cST["kp_Y"][0], cST.get("kd_Y", ["?"])[0], "512 or 2048 (gate 0xC5)",
          cST["gain"], cST["t_clamp"], cST["map_Y"][-1]))
    pr()

    routes = [("r39", L.IMG282, "V282"), ("r35", L.IMG282, "V281r3"), ("r6c", L.IMG282, "V282")]
    G = {}
    for tag, img, bld in routes:
        try:
            G[tag] = load_route(tag, img)
        except Exception as e:                                    # noqa: BLE001
            pr("  !! route %s unavailable: %s" % (tag, e))

    # --------------------------------------------------------------------------------------------
    for KP in (120, 119):
        cTM = L.torque_mode(c282, kp=KP)
        pr("=" * 126)
        pr("Kp = %d  (%s)" % (KP, "the BYTE value in the built image" if KP == 120 else "as the design modelled it"))
        pr("=" * 126)

        for tag in ("r39", "r35", "r6c"):
            if tag not in G:
                continue
            g = G[tag]
            for kind, label in (("b5", "B5  HANDS-LIGHT  |angle|>=30, |bar|<=400"),
                                ("b4", "B4  LOADED TURN  |angle|>=30, |bar|>=800")):
                wins = windows(g, kind)
                if not wins:
                    pr("  %s / %s : no window survives the gate" % (tag, label))
                    continue
                pr("-" * 126)
                pr("  %s  %s   %d windows x 3.0 s" % (tag, label, len(wins)))
                pr("-" * 126)
                pr("   Columns: each band is the CANDIDATE's absolute band amplitude, then the median")
                pr("   of the per-window ratio to V282.  rip/lev/f7-duty are the candidate's absolutes;")
                pr("   'f7 x' is the median per-window ratio of the >103 envelope duty to V282's.")
                hdr = ("        arm   kap |  W 5-9    x282 |  W 13-17   x282 |  W 18-22   x282 | "
                       " 6-8.5rip   level  rip/lev |  f7duty   f7 x | pk5-9")
                pr(hdr)
                acc = {}
                for arm, kap in ((2048, 0.4487), (2048, 1.45), (4451, 0.4487), (4451, 1.45),
                                 ("STOCK-512", None), ("STOCK-2048", None)):
                    rows = []
                    for (a0, b0, p0) in wins:
                        for fit in named:
                            pl = fit
                            if isinstance(arm, str):
                                cS = dict(cST)
                                s_arm = 512 if arm.endswith("512") else 2048
                                W = R.prep_window(g, a0, b0, c282)
                                el = R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True)
                                d, _ = R.invert_d(el, R.PlantIIR(pl), W, W["wire1k"])
                                A = R.closed_run(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True),
                                                 R.PlantIIR(pl), W, d)
                                WS = R.prep_window(g, a0, b0, cS)

                                def run_s(ex, cS=cS, WS=WS, pl=pl, d=d):
                                    return R.closed_run(
                                        R.Elec(cS, fb=(cS["fb_a"], cS["fb_b"]), ef=False,
                                               two_floor=True, kd=float(cS["kd_Y"][0])),
                                        R.PlantIIR(pl), WS, d, extra_T=ex)
                                B = run_s(None)
                                if s_arm != 5244:
                                    H = (lambda f, s_arm=s_arm:
                                         R.r24_delta_response(f, arm_from=5244, arm_to=s_arm))
                                    ex = np.zeros(WS["n"])
                                    for _ in range(4):
                                        ex = R.apply_fr(B["wire"], H)
                                        B = run_s(ex)
                            else:
                                old = R.KAPPA
                                R.KAPPA = kap
                                try:
                                    rr = S293.replay_tm(g, a0, b0, c282, cTM, pl, arm=arm)
                                finally:
                                    R.KAPPA = old
                                A, B = rr["A"], rr["B"]
                            sk = 800
                            row = {}
                            for nm, (lo, hi) in (("w59", (5.0, 9.0)), ("w1317", (13.0, 17.0)),
                                                 ("w1822", (18.0, 22.0))):
                                wa = R.band_amp(A["wire"][sk:], lo, hi)
                                wb = R.band_amp(B["wire"][sk:], lo, hi)
                                row[nm] = (wa, wb, wb / wa if wa > 0 else np.nan)
                            ra, la_, rla = ripple_level(A["T"][sk:])
                            rb, lb_, rlb = ripple_level(B["T"][sk:])
                            row["rip"] = (ra, rb, rb / ra if ra > 0 else np.nan)
                            row["lev"] = (la_, lb_, lb_ / la_ if la_ > 0 else np.nan)
                            row["riplev"] = (rla, rlb, rlb / rla if rla > 0 else np.nan)
                            fa = f7_duty(A["wire"][sk:])
                            fb_ = f7_duty(B["wire"][sk:])
                            row["f7d"] = (fa[0], fb_[0], (fb_[0] / fa[0]) if fa[0] > 0 else np.nan)
                            row["f7p"] = (fa[1], fb_[1], (fb_[1] / fa[1]) if fa[1] > 0 else np.nan)
                            row["pk"] = (peakiness(A["wire"][sk:]), peakiness(B["wire"][sk:]),
                                         np.nan)
                            rows.append(row)
                    md = lambda k, i: float(np.nanmedian([r[k][i] for r in rows]))   # noqa: E731
                    KEYS = ("w59", "w1317", "w1822", "rip", "lev", "riplev", "f7d", "f7p", "pk")
                    rec = {}
                    for k in KEYS:
                        rec["A_" + k] = md(k, 0)      # V282 absolute
                        rec["B_" + k] = md(k, 1)      # candidate absolute
                        rec["R_" + k] = md(k, 2)      # median of per-window ratios
                    rec["n"] = len(rows)
                    acc[str(arm) + "|" + str(kap)] = rec
                    pr("  %10s %5s | %7.2f %6.3f | %7.2f %6.3f | %7.2f %6.3f | %8.1f %7.1f %8.3f | %7.3f %6.2f | %6.1f"
                       % (str(arm)[:10], ("%.2f" % kap) if kap else "-",
                          rec["B_w59"], rec["R_w59"], rec["B_w1317"], rec["R_w1317"],
                          rec["B_w1822"], rec["R_w1822"],
                          rec["B_rip"], rec["B_lev"], rec["B_riplev"],
                          rec["B_f7d"], rec["R_f7d"], rec["B_pk"]))
                a0r = acc[list(acc)[0]]
                pr("  %10s %5s | %7.2f %6.3f | %7.2f %6.3f | %7.2f %6.3f | %8.1f %7.1f %8.3f | %7.3f %6.2f | %6.1f   <- V282, the recording's own build (ABSOLUTES; ratio column = 1 by definition)"
                   % ("V282", "-", a0r["A_w59"], 1.0, a0r["A_w1317"], 1.0, a0r["A_w1822"], 1.0,
                      a0r["A_rip"], a0r["A_lev"], a0r["A_riplev"], a0r["A_f7d"], 1.0, a0r["A_pk"]))
                RES["%s|%s|kp%d" % (tag, kind, KP)] = acc
                pr()

    pr("=" * 126)
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b4578.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(RES, open(os.path.join(OUTDIR, "b4578.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
