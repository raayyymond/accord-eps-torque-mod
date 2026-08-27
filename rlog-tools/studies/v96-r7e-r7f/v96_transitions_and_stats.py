#!/usr/bin/env python3
r"""Two deliverables:

(A) ENGAGEMENT-TRANSITION figures.  Inside the operator's elicitation blocks, find the moments
    LKAS engages or disengages while he is already working the wheel, and plot ~12 s around them.
    These are the strongest form of the comparison available in this data: the driver, the
    surface, the speed and the manoeuvre are continuous across the edge; only LKAS changes.

(B) The matched-pair statistics behind the figures, with an EPISODE bootstrap (never a window
    bootstrap -- see `feedback-episodes-not-windows`), plus the oscillation frequency estimated
    on the raw torque with a long window, and the 427 lane's phase against the torque sensor.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert, welch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
from v96_elicitation_finder import load, band_env, mmss, FS, BAND  # noqa: E402
from v96_probe_vs_ratchet import signed_lane, bp, band_rms  # noqa: E402

OUT = ROOT / "analysis-2020accord" / "figures/r7e_r7f"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = {r: ROOT / "analysis-2020accord" / f"r{r}" / f"r{r}.npz" for r in ("7e", "7f")}

C_TQ, C_CMD, C_ANG, C_LANE = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
C_INK, C_MUTED, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e2"


def style(a):
    a.set_facecolor(SURF)
    a.grid(True, color=GRID, lw=0.8)
    a.set_axisbelow(True)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
    a.tick_params(colors=C_MUTED, labelsize=8)


# ---------------------------------------------------------------- (A) transitions
def transitions(D, blocks_, guard=3.0):
    """LKAS edges that fall inside an elicitation block with `guard` s of block on both sides."""
    t, lat = D["t"], D["lat"]
    e = np.where(np.diff(lat.astype(np.int8)) != 0)[0] + 1
    out = []
    for k in e:
        for b in blocks_:
            if b["t0"] + guard <= t[k] <= b["t1"] - guard:
                out.append((int(k), bool(lat[k])))
                break
    return out


def transition_fig(r, D, env, lane_t, lane_y, k, on, half=6.0):
    t = D["t"]
    m = (t >= t[k] - half) & (t <= t[k] + half)
    tt = t[m] - t[k]
    ml = (lane_t >= t[k] - half) & (lane_t <= t[k] + half)
    fig, ax = plt.subplots(5, 1, figsize=(13.5, 10.2), sharex=True,
                           gridspec_kw=dict(hspace=0.12, height_ratios=[1, 1, 1, 1, 1]))
    fig.patch.set_facecolor(SURF)
    for a in ax:
        style(a)
        if on:
            a.axvspan(0, half, color="#eda100", alpha=0.15, lw=0)
        else:
            a.axvspan(-half, 0, color="#eda100", alpha=0.15, lw=0)
        a.axvline(0, color=C_INK, lw=1.2)
    ax[0].plot(tt, D["tq"][m], lw=1.0, color=C_TQ)
    ax[0].axhline(0, color=C_MUTED, lw=0.7)
    ax[0].set_ylabel("driver torque\n0x18F counts", fontsize=9, color=C_MUTED)
    ax[1].plot(tt, D["cmd"][m], lw=1.2, color=C_CMD)
    ax[1].axhline(0, color=C_MUTED, lw=0.7)
    ax[1].set_ylim(-4400, 4400)
    ax[1].set_ylabel("LKAS command\n0x0E4 counts", fontsize=9, color=C_MUTED)
    ax[2].plot(tt, D["ang"][m], lw=1.2, color=C_ANG)
    ax[2].set_ylabel("steering angle\ndeg", fontsize=9, color=C_MUTED)
    ax[3].plot(lane_t[ml] - t[k], lane_y[ml], lw=1.0, color=C_LANE)
    ax[3].axhline(0, color=C_MUTED, lw=0.7)
    ax[3].set_ylabel("gp-0x6b70 (V96 probe)\ncounts", fontsize=9, color=C_MUTED)
    ax[4].plot(tt, env[m], lw=1.4, color=C_TQ)
    ax[4].set_ylabel("driver torque\n6-9 Hz envelope", fontsize=9, color=C_MUTED)
    ax[4].set_xlabel(f"seconds either side of LKAS {'ENGAGING' if on else 'DISENGAGING'}"
                     f"   (amber = engaged)", color=C_MUTED)
    ax[4].set_xlim(-half, half)
    ax[0].set_title(f"route {r} — LKAS {'engages' if on else 'disengages'} at "
                    f"{mmss(t[k])}, mid-manoeuvre, {D['v'][k]:.0f} km/h",
                    fontsize=12, color=C_INK, loc="left", pad=10)
    pre = env[(t >= t[k] - half) & (t < t[k])]
    post = env[(t > t[k]) & (t <= t[k] + half)]
    ax[4].text(0.01, 0.92, f"6-9 Hz envelope median:  before {np.median(pre):.0f} ct   "
                           f"after {np.median(post):.0f} ct   "
                           f"({np.median(post)/max(np.median(pre),1e-9):.1f}x)",
               transform=ax[4].transAxes, fontsize=9, color=C_INK, va="top")
    p = OUT / f"transition_r{r}_{'on' if on else 'off'}_{int(t[k])}.png"
    fig.savefig(p, dpi=125, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print(f"    {p.name}   before {np.median(pre):7.1f} -> after {np.median(post):7.1f} ct")
    return dict(t=float(t[k]), on=bool(on), v=float(D["v"][k]),
                env_before=float(np.median(pre)), env_after=float(np.median(post)))


# ---------------------------------------------------------------- (B) statistics
def episode_stats(D, env, blocks_, lane_t, lane_y):
    """One row per contiguous (block x engagement-state) episode >= 1.5 s."""
    t, lat = D["t"], D["lat"]
    inb = np.zeros(len(t), bool)
    for b in blocks_:
        inb |= (t >= b["t0"]) & (t <= b["t1"])
    rows = []
    state = None
    start = None
    for i in range(len(t)):
        s = (bool(inb[i]), bool(lat[i]))
        if s != state:
            if state is not None and state[0] and start is not None and t[i] - t[start] >= 1.5:
                rows.append(_episode(D, env, lane_t, lane_y, start, i, state[1]))
            state, start = s, i
    return [r for r in rows if r is not None]


def _episode(D, env, lane_t, lane_y, a, b, eng):
    t = D["t"]
    ml = (lane_t >= t[a]) & (lane_t <= t[b - 1])
    return dict(t0=float(t[a]), t1=float(t[b - 1]), dur=float(t[b - 1] - t[a]), eng=bool(eng),
                v=float(D["v"][a:b].mean()),
                tq_absmed=float(np.median(np.abs(D["tq"][a:b]))),
                tq_band_rms=float(band_rms(D["tq"][a:b], FS)),
                env_med=float(np.median(env[a:b])),
                lane_band_rms=float(band_rms(lane_y[ml], 50.0)) if ml.sum() > 64 else float("nan"),
                cmd_absmed=float(np.median(np.abs(D["cmd"][a:b]))),
                cmd_rail=float(np.mean(np.abs(D["cmd"][a:b]) >= 4090)),
                f_peak=float(_fpeak(D["tq"][a:b])))


def _fpeak(x, fs=FS, lo=4.0, hi=20.0):
    if len(x) < int(fs * 1.5):
        return float("nan")
    f, P = welch(x - x.mean(), fs=fs, nperseg=min(len(x), int(fs * 4)))
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(P[m])]) if m.any() else float("nan")


def boot_ratio(a, b, n=20000, seed=3):
    """Bootstrap the ratio of medians over EPISODES."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan"), (float("nan"), float("nan"))
    rs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(n)]
    return float(np.median(a) / np.median(b)), (float(np.percentile(rs, 2.5)),
                                                float(np.percentile(rs, 97.5)))


def lane_phase(D, lane_t, lane_y, blocks_, f0=7.8):
    """Phase of gp-0x6b70 relative to driver torque at the ratchet line, engaged elicitation.
    🛑 The CAN join is worth +-10 ms == +-28 deg at 7.8 Hz; only a LARGE lag is interpretable."""
    t, lat = D["t"], D["lat"]
    tq50 = np.interp(lane_t, t, D["tq"])
    lat50 = np.interp(lane_t, t, lat.astype(float)) > 0.5
    inb = np.zeros(len(lane_t), bool)
    for b in blocks_:
        inb |= (lane_t >= b["t0"]) & (lane_t <= b["t1"])
    m = inb & lat50
    sos = butter(4, [(f0 - 1.5) / 25.0, (f0 + 1.5) / 25.0], btype="band", output="sos")
    ph, w = [], []
    d = np.diff(m.astype(np.int8))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if m[0]:
        s = [0] + s
    if m[-1]:
        e = e + [len(m)]
    for a, bb in zip(s, e):
        if bb - a < 200:
            continue
        x = hilbert(sosfiltfilt(sos, lane_y[a:bb] - lane_y[a:bb].mean()))
        y = hilbert(sosfiltfilt(sos, tq50[a:bb] - tq50[a:bb].mean()))
        z = x * np.conj(y)
        ph.append(np.angle(z.sum()))
        w.append(np.abs(z).sum())
    if not ph:
        return float("nan"), 0
    v = np.sum(np.array(w) * np.exp(1j * np.array(ph)))
    return float(np.degrees(np.angle(v))), len(ph)


if __name__ == "__main__":
    blocks_all = json.loads(
        (ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_elicitations.json").read_text())
    result = {}
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        z = np.load(CACHE[r], allow_pickle=True)
        lt, ly, _ = signed_lane(z)
        bl = blocks_all[r]
        print(f"\n=== route {r} ===")
        print("  transitions inside elicitation blocks:")
        trs = [transition_fig(r, D, env, lt, ly, k, on) for k, on in transitions(D, bl)]

        ep = episode_stats(D, env, bl, lt, ly)
        E = [e for e in ep if e["eng"]]
        M = [e for e in ep if not e["eng"]]
        print(f"\n  episodes: {len(E)} engaged ({sum(e['dur'] for e in E):.0f} s)  "
              f"{len(M)} manual ({sum(e['dur'] for e in M):.0f} s)")
        stats = {}
        for key, lab in (("tq_band_rms", "driver torque 6-9 Hz RMS"),
                         ("env_med", "driver torque 6-9 Hz envelope"),
                         ("lane_band_rms", "gp-0x6b70 6-9 Hz RMS")):
            ra, ci = boot_ratio([e[key] for e in E], [e[key] for e in M])
            stats[key] = dict(engaged_median=float(np.nanmedian([e[key] for e in E])),
                              manual_median=float(np.nanmedian([e[key] for e in M])),
                              ratio=ra, ci=ci)
            print(f"    {lab:<34} engaged {stats[key]['engaged_median']:8.1f}  "
                  f"manual {stats[key]['manual_median']:7.1f}  ratio {ra:6.1f}x "
                  f"[{ci[0]:.1f}, {ci[1]:.1f}]")
        for key, lab in (("v", "speed km/h"), ("tq_absmed", "median |driver torque|")):
            print(f"    control  {lab:<25} engaged {np.median([e[key] for e in E]):8.1f}  "
                  f"manual {np.median([e[key] for e in M]):7.1f}")
        fp = [e["f_peak"] for e in E if np.isfinite(e["f_peak"])]
        print(f"    oscillation line, engaged episodes: median {np.median(fp):.2f} Hz  "
              f"range {np.min(fp):.2f}-{np.max(fp):.2f} Hz  (n={len(fp)})")
        pha, npha = lane_phase(D, lt, ly, bl)
        print(f"    gp-0x6b70 phase vs driver torque @7.8 Hz: {pha:+.0f} deg over {npha} runs "
              f"(+-28 deg of CAN-join uncertainty)")
        result[r] = dict(transitions=trs, stats=stats, n_eng=len(E), n_man=len(M),
                         f_peak_median=float(np.median(fp)), lane_phase_deg=pha,
                         episodes=ep)
    (ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_stats.json").write_text(
        json.dumps(result, indent=1, default=float))
