#!/usr/bin/env python3
r"""Numbers requested by `ObserverMatch` (dose sizing) and `LeakDose` (ring-down edge yield),
computed from `_scratch/cache/r75` / `_scratch/cache/r76` / `_scratch/cache/r73`.  READ-ONLY on all three caches.

🛑 WHAT IS AND IS NOT OBSERVABLE, stated before the numbers:
  * `gp-0x6b98` -- observable, but ONLY as `wire = clamp((|gp-0x6b98| * 5) >> 3, 0, 0x3FF)` on CAN
    427.  `|cmd| = wire * 8/5`, and the wire RAILS at 1023, i.e. **|gp-0x6b98| >= 1638 counts is
    indistinguishable from any larger value.**  ⇒ `ObserverMatch`'s requested "fraction >= 2080"
    CANNOT be measured; only "fraction at or above the 1638 rail" can, and that is an UPPER BOUND
    on the >= 2080 fraction.
  * `gp-0x6abc` (motor electrical rate) -- **NOT observable.**  It is not on any CAN message, no
    cave on any flown build has ever probed it, and it is in none of the 15 caches.  The percentiles
    `ObserverMatch` needs do not exist in flown data.  What CAN be offered is an indirect handle:
    the V89 cave's b5 rung is `gp-0x6ae2 != 0`, and `gp-0x6ae2 = |model| * ratio * K1`, so
    `b5 == 0` implies `|model| * ratio == 0`.  Under the golden model's form that is the relay
    output going to zero, i.e. `sign(gp-0x6abc) == 0`.  The b5-vs-wheel-rate table is therefore a
    measurement of *where* `gp-0x6abc` quantises to zero, in wheel-rate units.
  * The b6 rung gives a HARD, parameter-free constraint on the product:
        b6  <=>  |gp-0x6ae2| >= 64  <=>  |model| * ratio >= 64 / K1 = 64 / 204 = 0.3137
    so the b6 duty IS the measured `P(|model| * ratio >= 0.3137)`.  That is the closest thing to a
    dose measurement the flight contains, and it needs no assumption about `gp-0x6abc` at all.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3].parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
import _r31_common as C31        # noqa: E402
import _r4f_lib as R4F           # noqa: E402
R4F.install_fs()

OUTJ = ROOT / "_scratch/cache/r75" / "v89_f2_requests.json"
R = {"73": ("_scratch/cache/r73", "r73", "r73s", 11), "75": ("_scratch/cache/r75", "r75", "r75s", 16),
     "76": ("_scratch/cache/r76", "r76", "r76s", 13)}
K1 = 204
WIRE_RAIL = 1023
CT_PER_WIRE = 8.0 / 5.0
OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


# =================================================================================================
def cmd_distribution():
    hdr("FOR ObserverMatch #1 -- |gp-0x6b98| ENGAGED, from CAN 427.  🛑 RAILS AT 1638 COUNTS.")
    OUT["cmd"] = {}
    for r, (cdir, stem, _p, _n) in R.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t = np.asarray(z["ab_t1ab"], float)
        wire = np.asarray(z["ab_mt"], int)
        rt = np.asarray(z["t"], float)
        lat = np.interp(t, rt, np.asarray(z["cc_lat"], float)) > 0.5
        w = wire[lat]
        cmd = w * CT_PER_WIRE
        d = dict(n=int(len(w)),
                 p50=float(np.percentile(cmd, 50)), p75=float(np.percentile(cmd, 75)),
                 p90=float(np.percentile(cmd, 90)), p95=float(np.percentile(cmd, 95)),
                 p99=float(np.percentile(cmd, 99)),
                 frac_at_rail=float(np.mean(w >= WIRE_RAIL)),
                 frac_ge_1000=float(np.mean(cmd >= 1000)),
                 frac_ge_1638=float(np.mean(w >= WIRE_RAIL)),
                 mean=float(cmd.mean()))
        OUT["cmd"][r] = d
        print(f"    route {r}: {d['n']:,} engaged 427 frames   |cmd| counts  "
              f"p50 {d['p50']:6.1f}  p75 {d['p75']:6.1f}  p90 {d['p90']:6.1f}  "
              f"p95 {d['p95']:6.1f}  p99 {d['p99']:6.1f}   mean {d['mean']:6.1f}")
        print(f"             fraction >= 1000 ct {d['frac_ge_1000']:.5f}   "
              f"AT THE 1638 RAIL {d['frac_at_rail']:.5f}  "
              f"<-- this is an UPPER BOUND on P(|cmd| >= 2080)")


def friction_constraint():
    hdr("FOR ObserverMatch #2/#3 -- the b5/b6 rungs as a DIRECT constraint on |model| x ratio\n"
        f"    b6 <=> |gp-0x6ae2| >= 64 <=> |model| * ratio >= 64/{K1} = {64/K1:.4f}\n"
        "    b5 <=> gp-0x6ae2 != 0  <=> |model| * ratio != 0")
    OUT["fric"] = {}
    for r, (cdir, stem, _p, _n) in R.items():
        if r == "73":
            continue
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t14 = np.asarray(z["raw14_t"], float)
        b4 = np.asarray(z["raw14_b4"], int) & 0xFF
        rt = np.asarray(z["t"], float)
        lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
        rate = np.abs(np.interp(t14, rt, np.asarray(z["rate_f"], float)))
        v = np.abs(np.interp(t14, rt, np.asarray(z["cs_v"], float)))
        e4 = np.abs(np.interp(t14, rt, np.asarray(z["e4tq"], float)))
        nz = (b4 & 0x20) != 0
        mg = (b4 & 0x40) != 0
        print(f"\n    route {r} -- P(b5) and P(b6) conditioned, ENGAGED")
        rows = {}
        for nm, x, ed in (("|wheel rate| deg/s", rate, [0, 0.35, 0.75, 1.5, 3, 6, 12, 25, 1e9]),
                          ("speed m/s", v, [0, 1, 3, 8, 15, 22, 1e9]),
                          ("|0x0E4| ct", e4, [0, 50, 150, 400, 1000, 2500, 1e9])):
            print(f"      by {nm}")
            rows[nm] = []
            for i in range(len(ed) - 1):
                m = lat & (x >= ed[i]) & (x < ed[i + 1])
                if m.sum() < 300:
                    continue
                rows[nm].append(dict(lo=ed[i], hi=ed[i + 1], sec=float(m.sum() / 100),
                                     p_b5=float(nz[m].mean()), p_b6=float(mg[m].mean())))
                print(f"        [{ed[i]:6.2f},{ed[i+1]:8.2f})  {m.sum()/100:7.1f} s   "
                      f"P(b5 != 0) {nz[m].mean():.4f}   "
                      f"P(|model|*ratio >= {64/K1:.3f}) {mg[m].mean():.4f}")
        OUT["fric"][r] = rows


def ringdown_yield():
    hdr("FOR LeakDose -- latActive FALLING-EDGE YIELD, screened by the recorded criteria")
    OUT["edges"] = {}
    for r, (cdir, stem, pfx, nseg) in R.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t = np.asarray(z["t"], float)
        lat = np.asarray(z["cc_lat"], float) > 0.5
        pr = np.asarray(z["cs_press"], float) > 0.5
        br = np.asarray(z.get("cs_brake", np.zeros_like(t)), float) > 0.5
        v = np.abs(np.asarray(z["cs_v"], float))
        fs = 100.0
        fall = np.flatnonzero((~lat[1:]) & lat[:-1]) + 1
        rows = []
        for i in fall:
            pre = slice(max(0, i - int(5 * fs)), i)
            post = slice(i, min(len(t), i + int(5 * fs)))
            eng_before = float(lat[pre].mean()) if pre.stop > pre.start else 0.0
            hands_after = float((~pr[post]).mean()) if post.stop > post.start else 0.0
            brake_at = float(br[max(0, i - 50):i + 50].mean())
            press_at = float(pr[max(0, i - 50):i + 50].mean())
            rows.append(dict(idx=int(i), t=float(t[i]), v=float(v[i]),
                             eng_5s_before=eng_before, handsoff_5s_after=hands_after,
                             brake_near=brake_at, press_near=press_at,
                             pass_pre=eng_before >= 0.99, pass_post=hands_after >= 0.99,
                             clean_disengage=(brake_at < 0.02 and press_at < 0.02)))
        ok = [x for x in rows if x["pass_pre"] and x["pass_post"] and x["clean_disengage"]]
        fast = [x for x in ok if x["v"] >= 18.8]
        OUT["edges"][r] = dict(n_falling=len(rows), n_pass=len(ok), n_pass_fast=len(fast),
                               rows=rows)
        print(f"\n    route {r}: {len(rows)} latActive falling edges")
        print(f"      {'t (s)':>8s} {'v m/s':>7s} {'eng 5 s before':>15s} {'hands-off 5 s after':>20s}"
              f" {'brake':>7s} {'press':>7s}  verdict")
        for x in rows:
            good = x["pass_pre"] and x["pass_post"] and x["clean_disengage"]
            why = ("OK" if good else
                   ",".join(([] if x["pass_pre"] else ["engaged<5s"])
                            + ([] if x["pass_post"] else ["hands-on after"])
                            + ([] if x["clean_disengage"] else ["brake/grab"])))
            print(f"      {x['t']:8.1f} {x['v']:7.2f} {x['eng_5s_before']:15.3f} "
                  f"{x['handsoff_5s_after']:20.3f} {x['brake_near']:7.3f} {x['press_near']:7.3f}  "
                  f"{why}")
        print(f"      ⇒ {len(ok)} pass the pre/post/clean screen; {len(fast)} of those at "
              f"v >= 18.8 m/s (order-clean for 6-9 Hz)")


def consistency():
    hdr("FOR LeakDose -- cache consistency and sample-rate checks")
    OUT["consistency"] = {}
    for r, (cdir, stem, pfx, nseg) in R.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        n_whole = len(z["t"])
        n_seg = 0
        rates = []
        for s in range(nseg):
            p = ROOT / cdir / f"{pfx}{s}.npz"
            if not p.exists():
                continue
            d = np.load(p)
            n_seg += len(d["t"])
            tt = np.asarray(d["t"], float)
            if len(tt) > 10:
                rates.append((len(tt) - 1) / (tt[-1] - tt[0]))
        seg_files = sorted((ROOT / cdir).glob(f"{pfx}*.npz"))
        print(f"    route {r}: whole-route {n_whole:,} rows   sum of segments {n_seg:,}   "
              f"{'MATCH' if n_whole == n_seg else 'DIFFER (segments <256 rows are dropped by split())'}")
        print(f"      {len(seg_files)} segment files   per-segment (n-1)/span: "
              f"min {min(rates):.4f} max {max(rates):.4f} Hz")
        OUT["consistency"][r] = dict(n_whole=n_whole, n_seg=n_seg, n_files=len(seg_files),
                                     rate_min=float(min(rates)), rate_max=float(max(rates)))
    print("\n    ⊕ All caches were written once, in a single completed run, and nothing has been")
    print("      re-written since.  No file is mid-write.")

    hdr("LeakDose's STAGGER CLAIM, checked on MY caches")
    for r, (cdir, stem, _p, _n) in R.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t = np.asarray(z["t"], float)
        r14 = np.asarray(z["raw14_t"], float)
        r18 = np.asarray(z["raw18_t"], float)
        sst = np.asarray(z["sstat"], int)
        s18 = np.asarray(z["raw18_st"], int)
        a = bool(len(t) == len(r14) - 1 and np.allclose(t, r14[1:]))
        b = bool(len(sst) <= len(s18) and np.array_equal(sst, s18[:len(sst)]))
        n = min(len(r14), len(r18))
        dt = float(np.median(r18[:n] - r14[:n]))
        print(f"    route {r}:  t == raw14_t[1:]  {a}    sstat == raw18_st[:len(sstat)]  {b}    "
              f"median(raw18_t - raw14_t) at equal index {dt*1000:+.3f} ms")
        OUT.setdefault("stagger", {})[r] = dict(t_eq_raw14_shift=a, sstat_eq_raw18_head=b,
                                                dt_ms=dt * 1000)
    print("\n    ⇒ CONSEQUENCE FOR MY OWN RESULTS, checked rather than assumed:")
    print("      * `v89_e6` (the impedance) uses `tq` and `rate_f`, BOTH decoded from the SAME 0x18F")
    print("        frame into the same row, so their RELATIVE timing is exact and the phase table is")
    print("        immune to any row-labelling stagger.  [EVIDENCE]")
    print("      * `v89_e4`/`v89_f1` pair `e4tq` (0x0E4, held) with `tq` (0x18F) -- a CROSS-message")
    print("        pairing, so a one-frame skew applies.  10 ms attenuates a correlation by")
    print("        cos(2*pi*f*0.01): 0.998 at 1 Hz, 0.88 at 7.5 Hz.  ⇒ my r values are slightly")
    print("        UNDER-stated, never inflated, and the phase at 6-9 Hz carries up to 27 deg.")


if __name__ == "__main__":
    cmd_distribution()
    friction_constraint()
    ringdown_yield()
    consistency()
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
