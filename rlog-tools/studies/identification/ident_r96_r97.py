#!/usr/bin/env python3
r"""CHEAP, DECISIVE build-identity discriminator for routes 96 and 97.

Reads ONE (or a few) segments per route and reports FOUR independent discriminators:

  D1  0x14A src==1 byte7[7:6] identity code    V102 = 3.  A stock ECU cannot emit a nonzero code
                                               unless Honda's own byte7 happens to carry bits there.
  D2  0x14A src==1 byte4[7:3] cave field       V102's cave writes b7/b6/b5/b4 and CLEARS b3.
                                               Stock leaves Honda's own byte4 content.
  D3  0x1AB (427) payload                      V102 repoints the 427 magnitude lane to gp-0x6b4c
                                               with `clamp(|x|*5>>6, 0, 0x3FF)`.  Stock 0x1AB is
                                               Honda content -- almost always static/near-constant.
  D4  LKAS authority                           delivered |wheel rate| per unit of openpilot command
                                               at the 4096 rail.  6x vs 1x is a ~6x difference.

Usage:  python studies/identification/ident_r96_r97.py [nseg]
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
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import rlog_parse  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RLOGS = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {
    "96": "75604b0a432fdc89_00000096--57f5183b32",
    "97": "75604b0a432fdc89_00000097--489d7896b3",
}
# a known-V102-free control and a known-V101 control, for calibration of the discriminators
CTRL = {
    "95(V101 8x)": "75604b0a432fdc89_00000095--6d7c6deef5",
}


def scan(prefix, segs):
    b7hi = Counter(); b4fld = Counter(); n14 = 0
    ab = Counter(); nab = 0; ab_src = Counter()
    ab_code = []
    t_e4, e4, t_ang, ang, t_eng, eng = [], [], [], [], [], []
    for s in segs:
        p = RLOGS / f"{prefix}--{s}--rlog.zst"
        if not p.exists():
            print(f"   (missing {p.name})"); continue
        try:
            for evt in rlog_parse.read_messages(str(p)):
                w = evt.which()
                if w == "can":
                    tm = evt.logMonoTime * 1e-9
                    for m in evt.can:
                        a, src = int(m.address), int(m.src)
                        if a == 0x14A and src == 1:
                            d = bytes(m.dat)
                            if len(d) >= 8:
                                n14 += 1
                                b7hi[(d[7] >> 6) & 3] += 1
                                b4fld[(d[4] >> 3) & 0x1F] += 1
                        elif a == 0x1AB:
                            d = bytes(m.dat)
                            nab += 1; ab_src[src] += 1
                            if len(d) >= 2:
                                ab[(d[0], d[1])] += 1
                                ab_code.append(((d[0] << 8) | d[1]))
                        elif a == 0xE4 and src == 0 and len(bytes(m.dat)) >= 3:
                            d = bytes(m.dat)
                            v = (d[0] << 8) | d[1]
                            if v >= 32768: v -= 65536
                            t_e4.append(tm); e4.append(v)
                elif w == "carState":
                    cs = evt.carState
                    t_ang.append(evt.logMonoTime * 1e-9); ang.append(cs.steeringAngleDeg)
                elif w == "controlsState":
                    pass
                elif w == "selfdriveState":
                    t_eng.append(evt.logMonoTime * 1e-9); eng.append(bool(evt.selfdriveState.active))
        except Exception as exc:
            print(f"   ⚠ truncated {p.name}: {str(exc).splitlines()[0]}")
    return dict(b7hi=b7hi, b4fld=b4fld, n14=n14, ab=ab, nab=nab, ab_src=ab_src,
                ab_code=np.array(ab_code, float),
                t_e4=np.array(t_e4), e4=np.array(e4, float),
                t_ang=np.array(t_ang), ang=np.array(ang, float),
                t_eng=np.array(t_eng), eng=np.array(eng, bool))


def report(name, r):
    print(f"\n{'='*90}\n{name}\n{'='*90}")
    print(f"  0x14A src1 frames: {r['n14']:,}")
    tot = max(r['n14'], 1)
    print("  D1  byte7[7:6] histogram: " +
          "  ".join(f"{k}:{v:,} ({v/tot:.4f})" for k, v in sorted(r['b7hi'].items())))
    top = r['b4fld'].most_common(12)
    print(f"  D2  byte4[7:3] alphabet ({len(r['b4fld'])} distinct): " +
          "  ".join(f"{k}:{v/tot:.3f}" for k, v in top))
    print(f"  D3  0x1AB frames: {r['nab']:,}  src={dict(r['ab_src'])}  "
          f"distinct (b0,b1)={len(r['ab'])}")
    if len(r['ab_code']):
        c = r['ab_code']
        print(f"      (b0<<8|b1)  p0={np.percentile(c,0):.0f} p50={np.percentile(c,50):.0f} "
              f"p90={np.percentile(c,90):.0f} p99={np.percentile(c,99):.0f} max={c.max():.0f}  "
              f"nonzero frac={np.mean(c!=0):.4f}")
        print(f"      top (b0,b1): {r['ab'].most_common(5)}")
    if len(r['t_eng']):
        # engaged seconds via selfdriveState.active
        te, ee = r['t_eng'], r['eng']
        dt = np.diff(te, append=te[-1])
        dt = np.clip(dt, 0, 0.1)
        print(f"  engaged (selfdriveState.active): {float(dt[ee].sum()):.1f} s of "
              f"{float(dt.sum()):.1f} s")
    if len(r['t_e4']) and len(r['t_ang']) > 10:
        # D4: wheel-rate response at the command rail
        t0 = max(r['t_e4'][0], r['t_ang'][0]); t1 = min(r['t_e4'][-1], r['t_ang'][-1])
        tg = np.arange(t0, t1, 0.01)
        a = np.interp(tg, r['t_ang'], r['ang'])
        e = np.interp(tg, r['t_e4'], r['e4'])
        rate = np.gradient(a, 0.01)
        if len(r['t_eng']):
            en = np.interp(tg, r['t_eng'], r['eng'].astype(float)) > 0.5
        else:
            en = np.ones(len(tg), bool)
        m = en & (np.abs(e) >= 3500)
        print(f"  D4  |e4 cmd|>=3500 & engaged: n={int(m.sum())} ({m.sum()*0.01:.1f} s)")
        if m.sum() > 50:
            print(f"      |wheel rate| p50={np.percentile(np.abs(rate[m]),50):.1f} "
                  f"p90={np.percentile(np.abs(rate[m]),90):.1f} deg/s")
        m2 = en & (np.abs(e) >= 1000)
        if m2.sum() > 50:
            print(f"      |cmd|>=1000: n={int(m2.sum())}  |wheel rate| p50="
                  f"{np.percentile(np.abs(rate[m2]),50):.1f} p90="
                  f"{np.percentile(np.abs(rate[m2]),90):.1f} deg/s")
        if en.sum() > 50:
            print(f"      engaged all: |cmd| p50={np.percentile(np.abs(e[en]),50):.0f} "
                  f"p90={np.percentile(np.abs(e[en]),90):.0f}  rail(>=4096) duty="
                  f"{np.mean(np.abs(e[en])>=4096):.4f}")


if __name__ == "__main__":
    nseg = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    for rt, pfx in ROUTES.items():
        report(f"ROUTE 0x{rt}  ({pfx})  segments 0..{nseg-1}", scan(pfx, range(nseg)))
    for nm, pfx in CTRL.items():
        report(f"CONTROL route {nm}  segments 0..{min(nseg,5)-1}", scan(pfx, range(min(nseg, 5))))
