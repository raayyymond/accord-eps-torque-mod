#!/usr/bin/env python3
r"""The operator-facing timestamp table: every elicitation episode in routes `7e` / `7f`, in
comma-connect route time, split ENGAGED vs LKAS-OFF, with the instrument reading beside it.

Route time == the cache's `t`.  Verified: the first 0x14A frame is within 40 ms of the first log
message of segment 0 on both routes (`v96_r7e_r7f_overview.measure_route_offset`), so no offset is
applied.  Segment boundaries are printed too, because segment 0 is 61.6 s / 62.4 s long on these
two routes and a naive `60 * segment` mapping is therefore off by ~1.6 s / ~2.4 s from segment 1
onward.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
from v96_elicitation_finder import load, band_env, FS  # noqa: E402
from v96_ratchet_character import brms, episodes  # noqa: E402

CACHE = {r: ROOT / "analysis-2020accord" / f"_cache_r{r}" / f"r{r}.npz" for r in ("7e", "7f")}


def ms(x):
    return f"{int(x)//60}:{x%60:04.1f}"


def seg_of(z, t):
    sb = np.asarray(z["seg_bounds"], float)
    for s, a, b in sb:
        if a <= t <= b:
            return int(s), t - a
    return -1, float("nan")


if __name__ == "__main__":
    bl_all = json.loads((ROOT / "analysis-2020accord" / "_r7e_r7f_elicitations.json").read_text())
    zoom = json.loads(
        (ROOT / "analysis-2020accord" / "_r7e_r7f_zoom_manifest.json").read_text())
    out = {}
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        z = np.load(CACHE[r], allow_pickle=True)
        print("=" * 108)
        print(f"ROUTE {r}   ({'7e' if r == '7e' else '7f'} = "
              f"75604b0a432fdc89_000000{r})   {D['t'][-1]:.0f} s")
        print(f"{'#':>3} {'from':>8} {'to':>8} {'dur':>6}  {'state':<10} {'seg':>4} "
              f"{'in-seg':>7}  {'km/h':>5} {'|tq|':>6} {'6-9Hz':>7} {'15-22':>7}  what")
        rows = []
        for i, (a, b, eng) in enumerate(episodes(D, bl_all[r], min_sec=1.5)):
            t0, t1 = float(D["t"][a]), float(D["t"][b - 1])
            s0, o0 = seg_of(z, t0)
            rec = dict(i=i, t0=t0, t1=t1, dur=t1 - t0, eng=bool(eng), seg=s0, in_seg=o0,
                       v=float(D["v"][a:b].mean()),
                       tq_absmed=float(np.median(np.abs(D["tq"][a:b]))),
                       b69=float(brms(D["tq"][a:b], FS, 6, 9)),
                       b1522=float(brms(D["tq"][a:b], FS, 15, 22)),
                       env_med=float(np.median(env[a:b])), env_max=float(env[a:b].max()))
            where = ("START of route" if t0 < 120 else
                     "END of route" if t0 > D["t"][-1] - 200 else "mid-route")
            rows.append(rec)
            print(f"{i:>3} {ms(t0):>8} {ms(t1):>8} {rec['dur']:6.1f}  "
                  f"{'LKAS ENGAGED' if eng else 'LKAS off':<10} {s0:>4} {o0:>6.1f}s  "
                  f"{rec['v']:5.1f} {rec['tq_absmed']:6.0f} {rec['b69']:7.1f} "
                  f"{rec['b1522']:7.1f}  {where}")
        out[r] = rows
        print(f"\n  1 s windows plotted for route {r}:")
        for p in zoom[r]:
            e, m = p["engaged"], p["manual"]
            print(f"    ENGAGED  {ms(e['t_c']):>8}  (seg {seg_of(z, e['t_c'])[0]}, "
                  f"+{seg_of(z, e['t_c'])[1]:.1f}s)   {e['v']:.0f} km/h  "
                  f"6-9 Hz {e['env_med']:.0f} ct  line {e['f_peak']:.1f} Hz")
            print(f"    LKAS off {ms(m['t_c']):>8}  (seg {seg_of(z, m['t_c'])[0]}, "
                  f"+{seg_of(z, m['t_c'])[1]:.1f}s)   {m['v']:.0f} km/h  "
                  f"6-9 Hz {m['env_med']:.0f} ct  line {m['f_peak']:.1f} Hz")
    (ROOT / "analysis-2020accord" / "_r7e_r7f_timestamps.json").write_text(
        json.dumps(out, indent=1, default=float))
