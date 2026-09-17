"""Figures + limit-cycle discriminators for the straight-road weave. python fsr_figs.py S2 256
Panels: (A) phasor diagram in 0.08-0.25 Hz relative to the car's measured lateral accel (la_pose): angle = phase,
radius = coherence; (B) Bode |H| and phase of model demand -> achieved (la_pose), 0.02-1 Hz; (C) per-run weave-band
rms achieved vs demanded; (D) pooled PSD of achieved and demanded.
Also writes results/fsr_limitcycle_<tier>.json: per-group demand-free floor, incoherent share, I/observer share, dwell.
"""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TIER = sys.argv[1] if len(sys.argv) > 1 else "S2"
NPS = int(sys.argv[2]) if len(sys.argv) > 2 else 256
sys.argv = [sys.argv[0], TIER, str(NPS)]
import fsr_analyze as A

COL = dict(V282="#2a78d6", T64="#eb6834", V282old="#1baf7a", T5="#eda100", T64B="#e87ba4")
INK = "#0b0b0b"; MUTED = "#52514e"; GRID = "#e4e3df"
R = A.load_runs()
groups = ["V282", "V282old", "T64", "T5", "T64B"]
G = {g: [r for r in R if r["group"] == g and r["vbin"] is not None] for g in groups}
f = R[0]["f"]

def pooled(rr, x, y):
    k = f"{x}>{y}"
    rr = [r for r in rr if k in r["csd"]]
    if not rr: return None
    Pxy = sum(r["csd"][k] for r in rr); Pxx = sum(r["psd"][x] for r in rr); Pyy = sum(r["psd"][y] for r in rr)
    return Pxy, Pxx, Pyy, sum(r["sec"] for r in rr)

fig = plt.figure(figsize=(13, 10), facecolor="#fcfcfb")
# (A) phasors
sigs = [("ad", "demand a_d"), ("e", "error a-a_d"), ("sa", "wheel angle"), ("psi", "heading to lane"),
        ("out", "command torque"), ("I", "integrator I"), ("dob", "observer DOB")]
s = (f >= A.W[0]) & (f < A.W[1])
axA = [fig.add_subplot(3, 3, i + 1, projection="polar") for i in range(3)]
for ax, g in zip(axA, ["V282", "T64", "T5"]):
    rr = [r for r in G[g] if ("psi" not in (r["psd"]) or r["lane_ok"] >= 0.8)]
    for j, (k, lbl) in enumerate(sigs):
        p = pooled(rr, "apose", k)
        if p is None: continue
        Pxy, Pxx, Pyy, _ = p
        ph = np.angle(Pxy[s].sum()); coh = float(np.average(np.abs(Pxy[s]) ** 2 / (Pxx[s] * Pyy[s]), weights=Pxx[s]))
        c = plt.cm.tab10(j) if False else ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"][j]
        ax.annotate("", xy=(ph, coh), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=c, lw=2))
        ax.text(ph, 1.08 + 0.13 * (j % 3), f"{lbl} {np.degrees(ph):+.0f}° (coh {coh:.2f})", color=c, fontsize=6.5,
                ha="center", fontweight="bold")
    ax.set_ylim(0, 1.5); ax.set_yticks([0.5, 1.0]); ax.set_yticklabels(["coh .5", "1"], fontsize=6, color=MUTED)
    ax.tick_params(labelsize=7, colors=MUTED)
    ax.set_title(f"{g}: phase vs achieved lat accel\n0.08-0.25 Hz, radius = coherence", fontsize=9, color=INK)
# (B) bode
axB1 = fig.add_subplot(3, 3, 4); axB2 = fig.add_subplot(3, 3, 7)
band = (f >= 0.02) & (f <= 1.0)
for g in ["V282", "V282old", "T64", "T5"]:
    p = pooled(G[g], "ad", "apose")
    if p is None: continue
    Pxy, Pxx, Pyy, sec = p
    H = np.abs(Pxy) / Pxx; coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    ok = band & (coh > 0.5)
    axB1.plot(f[ok], H[ok], "-o", ms=3, lw=2, color=COL[g], label=f"{g} ({sec:.0f} s)")
    axB2.plot(f[ok], np.degrees(np.angle(Pxy[ok])), "-o", ms=3, lw=2, color=COL[g])
for ax in (axB1, axB2):
    ax.axvspan(*A.W, color=GRID, alpha=0.6, lw=0); ax.set_xscale("log"); ax.grid(color=GRID, lw=0.6)
    ax.tick_params(labelsize=7, colors=MUTED)
axB1.axhline(1, color=MUTED, lw=1, ls="--"); axB1.set_ylabel("|H| demand->achieved", fontsize=8)
axB1.legend(fontsize=7, frameon=False); axB1.set_title("Model demand -> car (la_pose), straights >=15 m/s\nshaded = weave band; bins with coh>0.5", fontsize=9)
axB2.set_ylabel("phase deg (neg = car lags)", fontsize=8); axB2.set_xlabel("Hz", fontsize=8)
# (C) per-run scatter
axC = fig.add_subplot(3, 3, 5)
lc = {}
for g in ["V282", "V282old", "T64", "T5", "T64B"]:
    x = np.array([r["rms"]["ad"] for r in G[g]]); y = np.array([r["rms"]["apose"] for r in G[g]])
    sec = np.array([r["sec"] for r in G[g]])
    if len(x) == 0: continue
    axC.scatter(x, y, s=10 + sec / 8, color=COL[g], alpha=0.8, label=g, edgecolor="#fcfcfb", lw=1)
    # power regression y^2 = g^2 x^2 + floor^2 (weighted by sec)
    Xm = np.vstack([x ** 2, np.ones_like(x)]).T
    if len(x) >= 3:
        coef = np.linalg.lstsq(Xm * np.sqrt(sec)[:, None], y ** 2 * np.sqrt(sec), rcond=None)[0]
    else:
        coef = [float(np.sum(sec * y ** 2) / np.sum(sec * x ** 2)), float("nan")]
    lc[g] = dict(n_runs=int(len(x)), gain_through_fit=float(np.sqrt(max(coef[0], 0))), floor_rms=float(np.sign(coef[1]) * np.sqrt(abs(coef[1]))) if np.isfinite(coef[1]) else None)
m = 0.3; axC.plot([0, m], [0, m], color=MUTED, lw=1, ls="--")
axC.set_xlim(0, m); axC.set_ylim(0, m); axC.grid(color=GRID, lw=0.6); axC.tick_params(labelsize=7, colors=MUTED)
axC.set_xlabel("demand a_d band rms (m/s²)", fontsize=8); axC.set_ylabel("achieved band rms (m/s²)", fontsize=8)
axC.set_title("Per straight run, 0.08-0.25 Hz. A friction/integrator\nlimit cycle would leave a floor at low demand", fontsize=9)
axC.legend(fontsize=7, frameon=False)
# (D) PSD
axD = fig.add_subplot(3, 3, 8)
for g in ["V282", "T64"]:
    for k, ls in (("apose", "-"), ("ad", ":")):
        rr = G[g]; P = sum(r["psd"][k] for r in rr) / sum(r["sec"] for r in rr)
        axD.plot(f[band], P[band], ls, lw=2, color=COL[g], label=f"{g} {'achieved' if k=='apose' else 'demand'}")
axD.axvspan(*A.W, color=GRID, alpha=0.6, lw=0); axD.set_xscale("log"); axD.set_yscale("log")
axD.grid(color=GRID, lw=0.6); axD.tick_params(labelsize=7, colors=MUTED); axD.legend(fontsize=7, frameon=False)
axD.set_xlabel("Hz", fontsize=8); axD.set_ylabel("PSD (m/s²)²/Hz", fontsize=8)
axD.set_title("Lateral accel spectrum on straights (speed-pooled)", fontsize=9)
# (E) command composition in band
axE = fig.add_subplot(3, 3, 6)
names = ["out", "Ft", "Pt", "I", "dob"]
xs = np.arange(len(names)); wdt = 0.25
for j, g in enumerate(["T64", "T5", "T64B"]):
    rr = G[g]
    vals = [np.sqrt(sum(r["rms"][k] ** 2 * r["sec"] for r in rr if k in r["rms"]) / max(sum(r["sec"] for r in rr if k in r["rms"]), 1e-9)) if rr else 0 for k in names]
    axE.bar(xs + (j - 1) * wdt, vals, wdt - 0.03, color=COL[g], label=g)
axE.axhline(0.015, color=MUTED, ls="--", lw=1); axE.text(4.4, 0.0155, "AccordFrictionHyst 0.015", fontsize=6, color=MUTED, ha="right")
axE.axhline(0.011, color=MUTED, ls=":", lw=1); axE.text(4.4, 0.0085, "plant Coulomb F ~0.011", fontsize=6, color=MUTED, ha="right")
axE.set_xticks(xs); axE.set_xticklabels(["total cmd", "feedfwd F", "P", "I", "observer"], fontsize=7)
axE.tick_params(labelsize=7, colors=MUTED); axE.grid(axis="y", color=GRID, lw=0.6); axE.legend(fontsize=7, frameon=False)
axE.set_title("Torque-mode command, 0.08-0.25 Hz rms (output units)\n(F includes the observer)", fontsize=9)
axF = fig.add_subplot(3, 3, 9); axF.axis("off")
axF.text(0, 1, "EVIDENCE vs BELIEF on this page\n\n"
         "EVIDENCE: |H| a_d->la_pose, coherence, phases,\nband rms, per-run scatter (methods in fsr_analyze.py).\n"
         "Frames fixed by a kinematic positive control\n(fsr_kinecheck.py): lane heading lags la_pose\nby -90..-105 deg as psi' = a/v requires.\n\n"
         "Lane OFFSET y FAILED its control (coh 0.16-0.28)\nand is not used for any conclusion.\n\n"
         f"tier {TIER}, nperseg {NPS} (df {10/NPS:.3f} Hz).", fontsize=8, va="top", color=INK)
fig.tight_layout()
(HERE / "figs").mkdir(exist_ok=True)
out = HERE / "figs" / f"fsr_phase_diagram_{TIER}_n{NPS}.png"
fig.savefig(out, dpi=130)
# dwell + incoherent share
for g in lc:
    rr = G[g]
    p = pooled(rr, "ad", "apose"); Pxy, Pxx, Pyy, sec = p
    coh = np.abs(Pxy[s]) ** 2 / (Pxx[s] * Pyy[s])
    lc[g]["incoherent_share_of_achieved_power"] = float(np.sum((1 - coh) * Pyy[s]) / np.sum(Pyy[s]))
    lc[g]["dwell_frac"] = float(sum(r["dwell"] * r["sec"] for r in rr) / sum(r["sec"] for r in rr))
    for k in ("I", "dob", "Pt", "Ft"):
        num = sum(r["rms"][k] ** 2 * r["sec"] for r in rr if k in r["rms"]); den = sum(r["rms"]["out"] ** 2 * r["sec"] for r in rr if k in r["rms"])
        lc[g][f"{k}_rms_over_out_rms"] = float(np.sqrt(num / den)) if den > 0 else None
    # low-demand half of runs
    xs_ = sorted(r["rms"]["ad"] for r in rr); med = np.median(xs_) if xs_ else np.nan
    lo = [r for r in rr if r["rms"]["ad"] <= med]
    if lo:
        lc[g]["low_demand_half"] = dict(n=len(lo), ad_rms=float(np.sqrt(np.mean([r["rms"]["ad"] ** 2 for r in lo]))),
                                         apose_rms=float(np.sqrt(np.mean([r["rms"]["apose"] ** 2 for r in lo]))))
json.dump(lc, open(HERE / "results" / f"fsr_limitcycle_{TIER}_n{NPS}.json", "w"), indent=1)
print(out); print(json.dumps(lc, indent=1))
