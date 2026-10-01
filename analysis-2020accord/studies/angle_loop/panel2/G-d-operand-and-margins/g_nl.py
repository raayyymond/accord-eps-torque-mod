# -*- coding: utf-8 -*-
r"""g_nl.py -- the round-2 NONLINEAR refuter's own instruments, run on designer G's rate-operand implementations, so the
tracking price of each table is measured WITH the integrator clamp and friction (finding F1 of REFUTE-C2-r2-nonlinear):
  realref   nl_realref.main: the goal's tracking metric (0.5 Hz LPF, OLS slope) on route r71b's own engaged angle paths,
            per band 8-15 / 15-22 / >22 m/s, members nominal / bc / F_hi / b_lo*J_hi and the friction-free twins
  turnhold  nl_turnhold's experiment (re-stated here: that file is a script with no main guard): hold ratio over the last
            2 s of an 8 s hold at a_lat 0.5 / 1.0 / 1.5 / 2.0 m/s^2, ages native and +h10
EXTENSION, not a fork: nl_sim's IMPL / ROWS / GLUT registries are extended with these implementations' (kind, Kd, table);
the lane, plant, sensors and metric code are the refuter's, unchanged.  rev2-A P2 is re-run in the same batch as the
positive control (the refuter published 0.85-0.86 at 15-22 m/s and 0.89-0.92 at 8-15).  box10 (iii) and Ki != 56 are not
expressible in nl_sim and are not run here.  ANALYSIS ONLY.
usage: python g_nl.py realref|turnhold <impl> ...   -> g_nl_<what>.txt"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
NLDIR = X.AL / "refute_c2r2_nonlinear"
sys.path.insert(0, str(NLDIR))
import nl_sim as S  # noqa: E402
import nl_cave as NC  # noqa: E402


def register(iids):
    imps = json.loads((X.OUT / "g_impls.json").read_text())
    out = []
    for iid in iids:
        if iid in ("P2", "F2", "D2a", "B0r"):
            out.append(iid)
            continue
        im = imps[iid]
        assert im["dkind"] in ("fresh", "held") and im.get("ki", 56) == 56, iid
        rows = [tuple(r) for r in im["rows"]]
        S.IMPL[iid] = (im["dkind"], int(im["kd"]))
        S.ROWS[iid] = rows
        S.GLUT[iid] = np.array([NC.walk_G(rows, v) for v in range(0, 12001)], np.int64)
        out.append(iid)
    return tuple(out)


def realref(iids):
    import nl_realref as NR
    NR.IMPLS = register(iids)
    NR.OUT = X.OUT
    NR.main(frz=False)
    txt = (X.OUT / "realref.txt").read_text()
    (HERE / "g_nl_realref.txt").write_text(txt, encoding="utf-8")


def turnhold(iids):
    IM = register(iids)
    speeds = (8.0, 10.0, 11.9, 13.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 24.0, 26.9, 30.0)
    alat = (1.0, 1.5, 2.0)
    lines = ["# turn-hold vs lateral acceleration (hold ratio = mean wheel angle / target over the last 2 s of an 8 s hold; "
             "th_sw = a_lat L SR / v^2, L 2.83 m, SR 16 -- the refuter's nl_turnhold experiment); '*' = I at its clamp"]
    for mem in ("nominal", "bc", "b_lo*J_hi", "nominal_nf"):
        cols = [dict(impl=i, member=mem, v=v, age=0, alat=al) for v in speeds for al in alat for i in IM]
        tgt = np.array([c["alat"] * 2.83 * 16.0 / c["v"] ** 2 * 180 / np.pi for c in cols])
        scn = S.Scn(dur=11.0, ref=lambda t, tgt=tgt: tgt * np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1]))
        r = S.run(cols, scn)
        th = r["th"].astype(float)
        tt = np.arange(th.shape[0]) * 1e-3
        w = (tt >= 9.0) & (tt < 11.0)
        ratio = th[w].mean(0) / tgt
        Isat = (np.abs(r["I"][w]) >= 4096).mean(0)
        for al in alat:
            for im in IM:
                idx = [j for j, c in enumerate(cols) if c["alat"] == al and c["impl"] == im]
                cells = " ".join(f"{cols[j]['v']:g}:{ratio[j]:.2f}{'*' if Isat[j] > 0.5 else ''}" for j in idx)
                lines.append(f"{mem:11s} a_lat {al:.1f} {im:8s} {cells}")
        print("\n".join(lines[-len(alat) * len(IM):]), flush=True)
    (HERE / "g_nl_turnhold.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def small(iids):
    """nl_small's experiment (re-stated: a script with no main guard): +-0.3 deg 0.1 Hz / +-0.5 deg 0.2 Hz / +-1 deg 0.3 Hz
    corrections at 8-26.9 m/s, dwell-then-jump events (count, largest jump), wire gain, stuck %."""
    import nl_lens as L
    IM = register(iids)
    SP = (8.0, 9.0, 10.0, 11.0, 11.75, 12.25, 13.0, 14.0, 15.0, 16.0, 17.0, 19.0, 21.75, 26.9)
    MEM = ("nominal", "bc", "F_hi", "nominal_nf")
    lines = ["# small corrections (nl_small's experiment): per band, dwell-then-jump events summed over the speeds in it "
             "(largest jump deg) | min wire gain | max stuck %"]
    for scn_name in ("mic03", "mic05", "mic10"):
        cols = [dict(impl=i, member=m, v=v, age=0) for m in MEM for v in SP for i in IM]
        scn, meta = L.scenario(scn_name, cols)
        r = S.run(cols, scn)
        m = L.metrics(scn_name, meta, r, cols)
        lines.append(f"## {scn_name} (amp {meta.get('amp')} deg, f {meta['f']} Hz)")
        for mem in MEM:
            for im in IM:
                cells = []
                for lo, hi in ((8.0, 10.0), (10.25, 12.5), (12.75, 15.0), (15.25, 30.0)):
                    jj = [k for k, c in enumerate(cols) if c["member"] == mem and c["impl"] == im and lo <= c["v"] <= hi]
                    dj = int(sum(m["dj"][k] for k in jj))
                    mx = max(m["dj_max"][k] for k in jj)
                    g = min(m["gain"][k] for k in jj)
                    st = max(m["stick_pct"][k] for k in jj)
                    cells.append(f"{lo:g}-{hi:g}: dj {dj} ({mx:.2f}) g {g:.2f} st {st:.0f}%")
                lines.append(f"{im:8s} {mem:11s} " + " | ".join(cells))
        print(chr(10).join(lines[-(len(MEM) * len(IM) + 1):]), flush=True)
    (HERE / "g_nl_small.txt").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")


if __name__ == "__main__":
    what = sys.argv[1]
    iids = sys.argv[2:]
    {"realref": realref, "turnhold": turnhold, "small": small}[what](iids)
