"""Adversarial CONFOUND re-test of finding s1 'importance-highway-mid-band'.

Claim under test: matched on demand size, ~55% of rev 6.4 (T64)'s excess tracking-error energy over V282
sits above 15 m/s in 0.15-0.6 Hz, and that excess is ~45-47% of T64's own total error energy.

This is a FRESH, independent re-derivation from v282cmp.load() (raw per-route cache), NOT a reuse of
s1_reduce.py/s1_analyze.py's Hilbert/tercile machinery. For each route, band and speed bin we:
  - take usable(v>=vmin) runs (>=8s, no cross-gap concat, matches v282cmp.runs default),
  - zero-phase bandpass BOTH the model (x) and each achieved channel (la_pose / la_act / la_yaw) per run,
    trim 0.5/f1 seconds off each end of the run to kill filter transients,
  - delay-align y to x at the ROUTE's own median lat_delay (the 'on schedule' comparison, same idea as
    rE_pD in the original),
  - accumulate Sxx = sum(x^2) and SSE = sum((y_aligned - x)^2) per (route, band, vbin, channel),
  - rE^2 = SSE/Sxx  (relative error energy fraction, matches the original's rE_pD^2 definition up to the
    demand-tercile matching, which this script does NOT reproduce -- see caveat below).

CONFOUND checks run on top of that table:
  1. POOLED (all routes, no leave-out) importance share of {15-22,>22} x {0.15-0.3,0.3-0.6} in T64's total
     excess vs V282 -- a sanity replication of s1's headline number, computed by an independent estimator.
  2. LEAVE-ONE-ROUTE-OUT on the V282 baseline: recompute using only (64,65) [drops the 62-segment
     2bc842dbac route that holds most of V282's highway seconds] and using only 2bc842dbac alone.
  3. PER-ROUTE T64: recompute using only 68c6e94b17 and only 05e83bb04f (T64 is only 2 routes -- does one
     route carry the whole "excess" claim?).
  4. CHANNEL SWAP: repeat the whole computation with la_act and with la_yaw substituted for la_pose.
  5. Also report V282old vs its own two long routes, and per-route V282 rE, as an independent look at
     whether V282's own highway routes agree with each other (homogeneity check on the reference side).

CAVEAT (recorded, not hidden): this script's rE is delay-aligned-only, NOT demand-amplitude-tercile-
matched the way s1_reduce/s1_analyze compute it (equal-group-weight terciles per speed x band, computed
from the Hilbert envelope of the bandpassed model). If a demand-amplitude confound exists (routes/speeds
differing systematically in how hard the model demands), this script's shares can differ from s1's for
that reason alone, and cell 5 below (per-route mean |model| in each vbin) is reported so that confound can
be read off directly.

Run: python verify_importance.py   (loads each cached route once, never two in RAM at a time)
"""
import sys, json
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

BANDS = [(0.15, 0.30), (0.30, 0.60)]
VB = [(2.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
VBN = ["2-8", "8-15", "15-22", ">22"]

ROUTES = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64",
    "0000006e--6ca3e014fd": "T64B", "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4",
}
CHANS = ["la_pose", "la_act", "la_yaw"]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=V.FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def vbin_idx(v):
    b = np.full(len(v), -1, int)
    for k, (a, c) in enumerate(VB):
        b[(v >= a) & (v < c)] = k
    return b


def process_route(route):
    """Returns list of dicts: one per (band, vbin, chan) with Sxx, SSE, sec, mean_abs_model."""
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
    LD = int(round(ld * V.FS))
    model_all = np.nan_to_num(S["model"])
    chan_all = {c: np.nan_to_num(S[c]) for c in CHANS}
    vb_all = vbin_idx(v)
    runs = V.runs(m, t, min_s=8.0)
    out = []
    for f1, f2 in BANDS:
        trim = int(round(0.5 / f1 * V.FS))
        acc = {}  # (vbi, chan) -> [Sxx, SSE, n, sum_absx]
        for (i0, i1) in runs:
            n = i1 - i0
            if n <= 2 * trim + LD + 50:
                continue
            x = bp(model_all[i0:i1], f1, f2)
            vb_r = vb_all[i0:i1]
            valid = np.zeros(n, bool)
            valid[trim: n - trim - LD] = True
            for c in CHANS:
                y = bp(chan_all[c][i0:i1], f1, f2)
                y_al = np.concatenate([y[LD:], np.full(LD, y[-1])])  # y[t+LD] vs x[t]: "on schedule"
                for vbi in range(4):
                    sel = valid & (vb_r == vbi)
                    if sel.sum() < 20:
                        continue
                    key = (vbi, c)
                    a = acc.setdefault(key, [0.0, 0.0, 0, 0.0])
                    a[0] += float(np.sum(x[sel] ** 2))
                    a[1] += float(np.sum((y_al[sel] - x[sel]) ** 2))
                    a[2] += int(sel.sum())
                    a[3] += float(np.sum(np.abs(x[sel])))
        for (vbi, c), (Sxx, SSE, n, sabs) in acc.items():
            out.append(dict(route=route, group=ROUTES[route], band=f"{f1}-{f2}", vb=VBN[vbi], chan=c,
                             Sxx=Sxx, SSE=SSE, sec=n / V.FS, mean_abs_x=sabs / max(n, 1)))
    del S
    return out


def main():
    rows = []
    for route in ROUTES:
        print("processing", route, flush=True)
        rows += process_route(route)
    json.dump(rows, open("verify_importance_raw.json", "w"), indent=1)
    print("wrote verify_importance_raw.json,", len(rows), "rows")


if __name__ == "__main__":
    main()
