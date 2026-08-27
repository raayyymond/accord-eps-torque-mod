#!/usr/bin/env python3
r"""1-second time-domain panels of the operator's elicitation events, ENGAGED vs DISENGAGED.

For every panel the three signals he asked for, each on its own axis (never two scales on one):
    1. driver torque       CAN 0x18F bytes 0:1  STEER_TORQUE_SENSOR  (counts; the extractor flips
                           the sign so + is the same direction as + STEER_ANGLE)
    2. LKAS torque command CAN 0x0E4 bytes 0:1  STEER_TORQUE_REQUEST (counts, rails at +-4096)
    3. steering angle      CAN 0x14A bytes 0:1  STEER_ANGLE          (deg)
plus a fourth, subordinate row: the 6-9 Hz band-passed component of (1) and its envelope, in the
same counts -- the instrument, drawn separately so it cannot be mistaken for the raw signal.

🛑 EVERY ROW SHARES ONE Y-SCALE ACROSS ALL COLUMNS.  Per-panel autoscaling makes a 30 ct wiggle
look like a 1500 ct oscillation; that is the single easiest way to lie with this figure.

MATCHING.  Each DISENGAGED panel is chosen to match an ENGAGED panel on median |driver torque|
and on speed, inside the same route, so the pair differs in engagement and as little else as the
drive allows.  The residual mismatch is printed and written out -- a pair whose torque or speed is
far off is NOT a control and must not be read as one.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from v96_elicitation_finder import load, band_env, mmss, FS, BAND  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "analysis-2020accord" / "figures/r7e_r7f"
OUT.mkdir(parents=True, exist_ok=True)

C_TQ, C_CMD, C_ANG = "#2a78d6", "#eb6834", "#1baf7a"
C_INK, C_MUTED = "#0b0b0b", "#52514e"
SURF, GRID = "#fcfcfb", "#e6e5e2"
WIN = 1.0
HALF = int(WIN * FS / 2)


def bandpass(x, lo=BAND[0], hi=BAND[1], fs=FS):
    sos = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return sosfiltfilt(sos, x - np.mean(x))


def style(a):
    a.set_facecolor(SURF)
    a.grid(True, color=GRID, lw=0.8)
    a.set_axisbelow(True)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
    a.tick_params(colors=C_MUTED, labelsize=8)


def peak_freq(x, fs=FS, lo=3.0, hi=30.0):
    x = x - x.mean()
    F = np.fft.rfft(x * np.hanning(len(x)))
    f = np.fft.rfftfreq(len(x), 1 / fs)
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(np.abs(F[m]))]) if m.any() else float("nan")


def wstats(D, env, k):
    sl = slice(k - HALF, k + HALF)
    return dict(t_c=float(D["t"][k]), eng=bool(D["lat"][sl].mean() > 0.5),
                v=float(D["v"][sl].mean()),
                tq_absmed=float(np.median(np.abs(D["tq"][sl]))),
                tq_p2p=float(D["tq"][sl].max() - D["tq"][sl].min()),
                ang_p2p=float(D["ang"][sl].max() - D["ang"][sl].min()),
                cmd_med=float(np.median(D["cmd"][sl])),
                cmd_rail=float(np.mean(np.abs(D["cmd"][sl]) >= 4090)),
                env_med=float(np.median(env[sl])), env_max=float(env[sl].max()),
                band_p2p=float(np.ptp(bandpass(D["tq"][slice(k - HALF - 30, k + HALF + 30)])[30:-30])),
                f_peak=float(peak_freq(D["tq"][sl])))


def pick_engaged(D, env, blocks_, n, sep_s=1.6):
    t, lat = D["t"], D["lat"]
    ok = np.zeros(len(t), bool)
    for b in blocks_:
        ok |= (t >= b["t0"]) & (t <= b["t1"])
    ok &= lat
    ok[:HALF + 40] = ok[-(HALF + 40):] = False
    cand = np.where(ok)[0]
    chosen = []
    for k in cand[np.argsort(-env[cand])]:
        if all(abs(t[k] - t[j]) > sep_s for j in chosen):
            chosen.append(int(k))
        if len(chosen) == n:
            break
    return sorted(chosen)


def pick_matched_manual(D, env, blocks_, targets, sep_s=1.6):
    t, lat = D["t"], D["lat"]
    ok = np.zeros(len(t), bool)
    for b in blocks_:
        ok |= (t >= b["t0"]) & (t <= b["t1"])
    ok &= ~lat
    ok[:HALF + 40] = ok[-(HALF + 40):] = False
    cand = np.where(ok)[0][::5]
    stats = [wstats(D, env, int(k)) for k in cand]
    tqs = np.array([s["tq_absmed"] for s in stats])
    vs = np.array([s["v"] for s in stats])
    out, used = [], []
    for tgt in targets:
        cost = (np.abs(tqs - tgt["tq_absmed"]) / max(tgt["tq_absmed"], 200.0)
                + np.abs(vs - tgt["v"]) / max(tgt["v"], 3.0))
        for j in np.argsort(cost):
            k = int(cand[j])
            if all(abs(t[k] - u) > sep_s for u in used):
                used.append(t[k])
                out.append((k, float(cost[j])))
                break
    return out


def pair_figure(r, D, env, pairs, name):
    """4 rows x (2*npairs) columns.  Row-shared y-limits; ylabels on column 0 only."""
    npair = len(pairs)
    ncol = 2 * npair
    fig, ax = plt.subplots(4, ncol, figsize=(2.9 * ncol + 1.2, 8.6), sharex=True,
                           gridspec_kw=dict(hspace=0.14, wspace=0.10,
                                            left=0.085, right=0.995, top=0.855, bottom=0.075))
    fig.patch.set_facecolor(SURF)
    ax = np.atleast_2d(ax)
    ks = [k for p in pairs for k in (p[0], p[1])]

    lim = [[np.inf, -np.inf] for _ in range(4)]
    series = []
    for k in ks:
        sl = slice(k - HALF, k + HALF)
        bp = bandpass(D["tq"][slice(k - HALF - 30, k + HALF + 30)])[30:-30]
        rows = [D["tq"][sl], D["cmd"][sl], D["ang"][sl] - np.median(D["ang"][sl]), bp]
        series.append((sl, rows, env[sl]))
        for i, y in enumerate(rows):
            lim[i][0] = min(lim[i][0], float(np.min(y)))
            lim[i][1] = max(lim[i][1], float(np.max(y)))
    lim[3][0] = min(lim[3][0], -float(np.max([np.max(s[2]) for s in series])))
    lim[3][1] = max(lim[3][1], float(np.max([np.max(s[2]) for s in series])))
    for i in range(4):
        pad = 0.08 * (lim[i][1] - lim[i][0] + 1e-9)
        lim[i] = [lim[i][0] - pad, lim[i][1] + pad]
    lim[1] = [-4500, 4500]

    ylabs = ["driver torque\n0x18F counts", "LKAS command\n0x0E4 counts",
             "steering angle\ndeg (centred)", f"driver torque\n{BAND[0]:.0f}-{BAND[1]:.0f} Hz, counts"]
    colors = [C_TQ, C_CMD, C_ANG, C_TQ]
    for c, k in enumerate(ks):
        sl, rows, e = series[c]
        ms = (D["t"][sl] - D["t"][k]) * 1000.0
        s = wstats(D, env, k)
        for i in range(4):
            a = ax[i, c]
            style(a)
            a.set_ylim(*lim[i])
            a.axhline(0, color=C_MUTED, lw=0.7)
            if i == 3:
                a.fill_between(ms, -e, e, color=C_TQ, alpha=0.16, lw=0)
            a.plot(ms, rows[i], lw=1.5, color=colors[i], solid_capstyle="round")
            if c:
                a.set_yticklabels([])
            else:
                a.set_ylabel(ylabs[i], fontsize=8.5, color=C_MUTED)
        eng = s["eng"]
        ax[0, c].set_title(("LKAS ENGAGED" if eng else "LKAS OFF") + f"\n{mmss(s['t_c'])}",
                           fontsize=10, color=(C_INK if eng else C_MUTED),
                           fontweight=("bold" if eng else "normal"), pad=16)
        ax[0, c].text(0.5, 1.005,
                      f"{s['v']:.0f} km/h · |tq| {s['tq_absmed']:.0f} · "
                      f"6-9 Hz {s['env_med']:.0f} ct",
                      transform=ax[0, c].transAxes, ha="center", va="bottom",
                      fontsize=7.5, color=C_MUTED)
        ax[3, c].set_xlabel("ms", fontsize=8, color=C_MUTED)
        if eng:
            for i in range(4):
                ax[i, c].set_facecolor("#fdf6e6")
    fig.suptitle(f"route {r} — 1 s elicitation windows.  LKAS ENGAGED (shaded) vs LKAS OFF, "
                 f"matched pairwise on driver torque and speed.  Every row shares one y-scale.",
                 color=C_INK, fontsize=12, y=0.975)
    p = OUT / f"{name}.png"
    fig.savefig(p, dpi=130, facecolor=SURF)
    plt.close(fig)
    print(f"  {p.name}")


if __name__ == "__main__":
    rep = json.loads((ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_elicitations.json").read_text())
    manifest = {}
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        eng_k = pick_engaged(D, env, rep[r], n=6)
        tgt = [wstats(D, env, k) for k in eng_k]
        man = pick_matched_manual(D, env, rep[r], tgt)
        pairs = [(ke, km, c) for ke, (km, c) in zip(eng_k, man)]
        rows = []
        print(f"route {r}: {len(pairs)} matched pairs")
        for ke, km, c in pairs:
            se, sm = wstats(D, env, ke), wstats(D, env, km)
            rows.append(dict(engaged=se, manual=sm, match_cost=c))
            print(f"  ENG {mmss(se['t_c']):>9} v{se['v']:5.1f} |tq|{se['tq_absmed']:6.0f} "
                  f"env{se['env_med']:6.0f} bp_p2p{se['band_p2p']:6.0f} f{se['f_peak']:5.1f} "
                  f"rail{se['cmd_rail']:.2f}  ||  MAN {mmss(sm['t_c']):>9} v{sm['v']:5.1f} "
                  f"|tq|{sm['tq_absmed']:6.0f} env{sm['env_med']:6.0f} "
                  f"bp_p2p{sm['band_p2p']:6.0f} f{sm['f_peak']:5.1f}   cost {c:.2f}")
        manifest[r] = rows
        pair_figure(r, D, env, pairs[:3], f"zoom_r{r}_A")
        pair_figure(r, D, env, pairs[3:6], f"zoom_r{r}_B")
    (ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_zoom_manifest.json").write_text(
        json.dumps(manifest, indent=1))
