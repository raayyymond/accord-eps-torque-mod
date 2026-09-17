"""Phase-aligned ensemble figures (median + IQR) per group: build-up aligned at the build start, unwind aligned at the unwind start."""
import pickle, json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
E = pickle.load(open(OUT + 'ensemble.pkl', 'rb'))
grid = E["grid"]
GM = {"V282": "V282", "V282old": "V282old", "T64": "torque (rev 4-6.4)", "T64B": "torque (rev 4-6.4)", "T5": "torque (rev 4-6.4)", "T4": "torque (rev 4-6.4)"}
COL = {"V282": "#2a78d6", "torque (rev 4-6.4)": "#eb6834", "V282old": "#1baf7a"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
groups = ["V282", "V282old", "torque (rev 4-6.4)"]


def stack(anchor, key, G):
    xs = [e["tr"][anchor][key] for e in E["ens"] if GM[e["group"]] == G]
    return np.array(xs, float)


def band(ax, x, Y, c, label):
    with np.errstate(all="ignore"):
        ok = np.isfinite(Y).sum(0) >= max(3, 0.3 * len(Y))
        med = np.nanmedian(Y, 0); q1 = np.nanpercentile(Y, 25, 0); q3 = np.nanpercentile(Y, 75, 0)
    med[~ok] = np.nan; q1[~ok] = np.nan; q3[~ok] = np.nan
    ax.fill_between(x, q1, q3, color=c, alpha=0.15, lw=0)
    ax.plot(x, med, color=c, lw=2, label=label)


def style(ax):
    ax.grid(True, color=GRID, lw=0.8); ax.tick_params(colors=INK2, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.axvline(0, color=INK2, lw=0.8, ls=":")


summary = {}
fig, axs = plt.subplots(5, 2, figsize=(12, 15), sharex="col")
for col, (anchor, title) in enumerate([("i", "aligned at BUILD-UP start (desired leaves 10% of peak)"),
                                       ("h1", "aligned at UNWIND start (desired drops below 80% of peak)")]):
    for G in groups:
        n = sum(1 for e in E["ens"] if GM[e["group"]] == G)
        c = COL[G]
        AD = stack(anchor, "ad", G); AA = stack(anchor, "aa", G); AP = stack(anchor, "ap", G)
        band(axs[0, col], grid, AA, c, f"{G} (n={n})")
        axs[0, col].plot(grid, np.nanmedian(AD, 0), color=c, lw=1, ls="--")
        band(axs[1, col], grid, AA - AD, c, G)
        band(axs[2, col], grid, AP - AD, c, G)
        band(axs[3, col], grid, stack(anchor, "sr", G), c, G)
        band(axs[4, col], grid, stack(anchor, "out", G), c, G)
        summary[f"{anchor}_{G}"] = dict(n=n)
    axs[0, col].set_title(title, fontsize=10, color=INK)
    axs[0, col].set_ylabel("wheel angle / peak desired\n(dashed = desired, same colour)", fontsize=8, color=INK2)
    axs[1, col].set_ylabel("angle error / peak\n(+ = more turn than asked)", fontsize=8, color=INK2)
    axs[2, col].set_ylabel("yaw-curvature error / peak\n(livePose, + = more turn)", fontsize=8, color=INK2)
    axs[3, col].set_ylabel("steering rate deg/s\n(+ = into the turn)", fontsize=8, color=INK2)
    axs[4, col].set_ylabel("command (sign-normalised, NEGATIVE = into turn)\nV282: rate reference; torque: torque", fontsize=8, color=INK2)
    axs[4, col].set_xlabel("s from anchor (achieved advanced by the route's learned lateral delay)", fontsize=8, color=INK2)
    for ax in axs[:, col]:
        style(ax)
    axs[1, col].axhline(0, color=INK2, lw=0.8); axs[2, col].axhline(0, color=INK2, lw=0.8)
axs[0, 0].legend(fontsize=8, frameon=False)
fig.suptitle("Large-angle turns (desired >= 25 deg wheel-equivalent, 2.5-15 m/s): median and IQR per group\n"
             "EVIDENCE: 27 V282 / 22 V282old / 32 torque-mode events; pressed frames masked in the error rows", fontsize=11, color=INK)
fig.tight_layout()
fig.savefig(OUT + 's3_turn_ensemble.png', dpi=110)
plt.close(fig)

# zoom on steering-rate texture: detrended rate (minus its own 1 Hz lowpass) at the unwind anchor
from scipy import signal
sos = signal.butter(2, 1.5, btype="high", fs=100, output="sos")
fig, axs = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
rng = np.random.default_rng(0)
for ax, G in zip(axs, groups):
    SR = stack("h1", "sr", G)
    pick = rng.choice(len(SR), min(8, len(SR)), replace=False)
    for k, p in enumerate(pick):
        y = SR[p].copy(); m = np.isfinite(y)
        if m.sum() < 100:
            continue
        yy = np.full_like(y, np.nan); yy[m] = signal.sosfiltfilt(sos, y[m])
        ax.plot(grid, yy + 40 * k, color=COL[G], lw=1)
    ax.set_title(f"{G}: steering rate > 1.5 Hz, 8 random unwinds (offset)", fontsize=9, color=INK)
    style(ax); ax.set_xlabel("s from unwind start", fontsize=8, color=INK2)
axs[0].set_ylabel("deg/s (+40 per trace)", fontsize=8, color=INK2)
fig.tight_layout(); fig.savefig(OUT + 's3_unwind_texture.png', dpi=110); plt.close(fig)

# PSD figure
P2 = json.load(open(OUT + 's3_pass2.json'))
fig, ax = plt.subplots(figsize=(7, 4))
merge = {}
for G, a in P2["psd"].items():
    g = GM[G]
    m = merge.setdefault(g, [np.zeros(len(a["p"])), 0.0, np.array(a["f"])])
    m[0] += np.array(a["p"]) * a["sec"]; m[1] += a["sec"]
for g in groups:
    p, sec, f = merge[g]
    ax.semilogy(f, p / sec, color=COL[g], lw=2, label=f"{g} ({sec:.0f} s)")
ax.set_xlim(0, 15); ax.set_xlabel("Hz", fontsize=8, color=INK2); ax.set_ylabel("steering-rate PSD (deg/s)^2/Hz", fontsize=8, color=INK2)
ax.set_title("Steering-rate spectrum inside large-angle turn windows (hands-off frames)", fontsize=10, color=INK)
style(ax); ax.axvline(0, alpha=0); ax.legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT + 's3_turn_psd.png', dpi=110); plt.close(fig)

# numeric: command around unwind start
for G in groups:
    O = stack("h1", "out", G); F = stack("h1", "f", G); PI = stack("h1", "pi", G); AD = stack("h1", "ad", G)
    def at(X, t0, t1):
        m = (grid >= t0) & (grid < t1)
        return float(np.nanmedian(np.nanmean(X[:, m], 1)))
    print(G, " out  hold[-1,0] %.3f  unwind[0,1] %.3f  late[1,2] %.3f  ret[2,4] %.3f" % (at(O, -1, 0), at(O, 0, 1), at(O, 1, 2), at(O, 2, 4)),
          "| pi %.3f %.3f %.3f %.3f" % (at(PI, -1, 0), at(PI, 0, 1), at(PI, 1, 2), at(PI, 2, 4)),
          "| frac of events with out<0 in [0,2]: %.2f" % float(np.mean(np.nanmin(O[:, (grid >= 0) & (grid < 2)], 1) < 0)))
print("figures written")
