#!/usr/bin/env python3
r"""Whole-route overview figures for `7e` / `7f`, plus the route-time offset measured from the
raw segment logs (so the timestamps handed to the operator match comma connect's timeline).

Outputs PNGs into `analysis-2020accord/_plots_r7e_r7f/`.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

OUT = ROOT / "analysis-2020accord" / "_plots_r7e_r7f"
OUT.mkdir(parents=True, exist_ok=True)

ROUTE_PREFIX = {"7e": "75604b0a432fdc89_0000007e--e5f2d1465f",
                "7f": "75604b0a432fdc89_0000007f--2bb30756e7"}
CACHE = {r: ROOT / "analysis-2020accord" / f"_cache_r{r}" / f"r{r}.npz" for r in ROUTE_PREFIX}

# dataviz reference palette, categorical slots 1/2/3 (light mode)
C_TQ, C_CMD, C_ANG = "#2a78d6", "#eb6834", "#1baf7a"
C_SPD, C_INK, C_MUTED = "#4a3aa7", "#0b0b0b", "#52514e"
C_ENG = "#eda100"


def measure_route_offset(r):
    """t=0 of the cache is the first 0x14A row.  Comma connect's route clock starts at the first
    log message of segment 0.  Measure the gap directly rather than assuming it."""
    import rlog_parse
    p = ROOT / "analysis-2020accord" / "rlogs" / f"{ROUTE_PREFIX[r]}--0--rlog.zst"
    first_any = None
    first_14a = None
    for evt in rlog_parse.read_messages(p):
        tm = evt.logMonoTime * 1e-9
        if first_any is None:
            first_any = tm
        try:
            if evt.which() == "can":
                for m in evt.can:
                    if int(m.src) == 1 and int(m.address) == 0x14A and len(bytes(m.dat)) >= 7:
                        first_14a = tm
                        break
        except Exception:
            continue
        if first_14a is not None:
            break
    return dict(first_log_mono=first_any, first_14a_mono=first_14a,
                offset_s=float(first_14a - first_any))


def overview(r, off):
    z = np.load(CACHE[r], allow_pickle=True)
    t = np.asarray(z["t"], float) + off
    v = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    lat = np.asarray(z["cc_lat"], float) > 0.5
    ang = np.asarray(z["ang"], float)
    tq = np.asarray(z["tq"], float)
    cmd = np.asarray(z["e4tq"], float)

    fig, ax = plt.subplots(4, 1, figsize=(16, 9), sharex=True,
                           gridspec_kw=dict(height_ratios=[1.1, 1, 1, 1], hspace=0.12))
    fig.patch.set_facecolor("#fcfcfb")

    # engaged shading on every axis
    edges = np.diff(lat.astype(int))
    st = list(np.where(edges == 1)[0] + 1)
    en = list(np.where(edges == -1)[0] + 1)
    if lat[0]:
        st = [0] + st
    if lat[-1]:
        en = en + [len(lat) - 1]
    for a in ax:
        a.set_facecolor("#fcfcfb")
        for s, e in zip(st, en):
            a.axvspan(t[s], t[e], color=C_ENG, alpha=0.13, lw=0)
        a.grid(True, color="#e6e5e2", lw=0.8)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)

    ax[0].plot(t, v, lw=1.0, color=C_SPD)
    ax[0].set_ylabel("speed\nkm/h", color=C_MUTED, fontsize=9)
    ax[0].axhline(10, color=C_MUTED, lw=0.7, ls=":")
    ax[1].plot(t, ang, lw=0.8, color=C_ANG)
    ax[1].set_ylabel("steering angle\ndeg", color=C_MUTED, fontsize=9)
    ax[1].axhline(0, color=C_MUTED, lw=0.7)
    ax[2].plot(t, tq, lw=0.6, color=C_TQ)
    ax[2].set_ylabel("driver torque\n0x18F counts", color=C_MUTED, fontsize=9)
    ax[2].axhline(0, color=C_MUTED, lw=0.7)
    ax[3].plot(t, cmd, lw=0.6, color=C_CMD)
    ax[3].set_ylabel("LKAS command\n0x0E4 counts", color=C_MUTED, fontsize=9)
    ax[3].axhline(0, color=C_MUTED, lw=0.7)
    ax[3].set_xlabel("route time (s)  —  amber = LKAS engaged (latActive)", color=C_MUTED)

    for a in ax:
        a.tick_params(colors=C_MUTED, labelsize=8)
    sec = np.arange(0, t[-1] + 60, 60)
    ax[3].set_xticks(sec)
    ax[3].set_xticklabels([f"{int(s)//60}:{int(s)%60:02d}" for s in sec])
    ax[0].set_title(f"route {r}  —  whole-drive overview   ({t[-1]:.0f} s, "
                    f"{100*lat.mean():.0f}% LKAS engaged)",
                    color=C_INK, fontsize=12, loc="left", pad=10)
    fig.savefig(OUT / f"overview_r{r}.png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  wrote overview_r{r}.png   route-time offset {off:+.2f} s")


if __name__ == "__main__":
    offs = {}
    for r in ("7e", "7f"):
        o = measure_route_offset(r)
        offs[r] = o
        print(f"route {r}: first log msg -> first 0x14A gap = {o['offset_s']:+.3f} s")
        overview(r, o["offset_s"])
    (ROOT / "analysis-2020accord" / "_r7e_r7f_route_offsets.json").write_text(
        json.dumps(offs, indent=1))
