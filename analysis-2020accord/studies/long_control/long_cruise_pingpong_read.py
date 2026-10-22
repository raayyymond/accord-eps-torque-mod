# -*- coding: utf-8 -*-
"""Cruise (NO-LEAD) speed ping-pong reader for one route (StarPilot accord-PTM, Honda Bosch openpilot long).

usage:  python long_cruise_pingpong_read.py <route> [--rebuild] [--dump] [--trace]

Each segment is extracted once to _scratch/cache/<route>/cruise_seg<N>.npz (fork cereal, see long_pingpong_read.py),
then everything is vectorised numpy.  Reports, for openpilot-long-engaged time with NO lead and v > 8 m/s:
  * vEgo - vCruise: mean, p10/p50/p90, band-passed (4-40 s) envelope, dominant period
  * what cycles with it: aTarget, the ACC_CONTROL accel/gas/brake, the planner's own speed target
  * per-dip table (--dump) and a 1 s trace of the longest episode (--trace)
"""
import io, os, sys, glob, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from long_pingpong_read import ensure_cereal, hold, runs, CEREAL, RLOGS, CACHE, DONGLE, ACC_CONTROL, _s16

T0 = time.time()
CV = 1
FS = 20.0
MPH = 2.23694


def extract_segment(args):
  path, out = args
  import zstandard as zstd, capnp
  capnp.remove_import_hook()
  L = capnp.load(os.path.join(CEREAL, "log.capnp"))
  data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(open(path, "rb").read())).read()
  cs, cc, lp, sp, rs, gas, co = [], [], [], [], [], [], []
  for e in L.Event.read_multiple_bytes(data):
    w = e.which()
    t = e.logMonoTime * 1e-9
    if w == "carState":
      c = e.carState
      cs.append((t, c.vEgo, c.aEgo, c.cruiseState.speed, c.gasPressed, c.brakePressed, c.standstill, c.vCruise))
    elif w == "carControl":
      c = e.carControl
      o = c.orientationNED
      cc.append((t, c.longActive, c.actuators.accel, o[1] if len(o) == 3 else np.nan, c.actuators.longControlState.raw))
    elif w == "carOutput":
      co.append((t, e.carOutput.actuatorsOutput.accel))
    elif w == "longitudinalPlan":
      q = e.longitudinalPlan
      sp0 = q.speeds; ac = q.accels
      lp.append((t, q.aTarget, q.hasLead, sp0[0] if len(sp0) else np.nan, ac[0] if len(ac) else np.nan,
                 sp0[-1] if len(sp0) else np.nan, q.shouldStop))
    elif w == "starpilotPlan":
      p = e.starpilotPlan
      sp.append((t, p.vCruise, p.experimentalMode, p.maxAcceleration, p.minAcceleration))
    elif w == "radarState":
      l = e.radarState.leadOne
      rs.append((t, l.status, l.dRel))
    elif w == "sendcan":
      for m in e.sendcan:
        if m.address == ACC_CONTROL:
          d = m.dat
          if len(d) >= 5:
            acc = ((d[3] << 3) | (d[4] >> 5))
            acc = acc - 2048 if acc & 0x400 else acc
            gas.append((t, _s16(d[0], d[1]), acc * 0.01, (d[4] >> 2) & 1))
          break
  f = lambda x, n: np.array(x, dtype=float) if x else np.zeros((0, n))
  np.savez(out, v=CV, cs=f(cs, 8), cc=f(cc, 5), lp=f(lp, 7), sp=f(sp, 5), rs=f(rs, 3), gas=f(gas, 4), co=f(co, 2))
  return out


def load_route(route, rebuild=False):
  segs = sorted(glob.glob(os.path.join(RLOGS, f"{DONGLE}_{route}--*--rlog.zst")), key=lambda p: int(p.rsplit("--", 2)[-2]))
  cdir = os.path.join(CACHE, route); os.makedirs(cdir, exist_ok=True)
  if not segs:
    # no local rlogs: use whatever cache exists (e.g. tables decoded ON the device with device_extract.py)
    cached = sorted(glob.glob(os.path.join(cdir, "cruise_seg*.npz")), key=lambda p: int(os.path.basename(p)[10:-4]))
    if not cached:
      sys.exit(f"no rlogs and no cache for {route}")
    parts = [np.load(c) for c in cached]
    cat = lambda k: np.concatenate([z[k] for z in parts if len(z[k])]) if any(len(z[k]) for z in parts) else np.zeros((0, 1))
    return {k: cat(k) for k in ("cs", "cc", "lp", "sp", "rs", "gas", "co")}, len(cached), 0
  jobs = []
  for p in segs:
    out = os.path.join(cdir, "cruise_seg%s.npz" % p.rsplit("--", 2)[-2])
    if rebuild or not os.path.exists(out) or int(np.load(out)["v"]) != CV:
      jobs.append((p, out))
  if jobs:
    ensure_cereal()
    with Pool(min(len(jobs), os.cpu_count() or 4)) as pool:
      pool.map(extract_segment, jobs)
  parts = [np.load(os.path.join(cdir, "cruise_seg%s.npz" % p.rsplit("--", 2)[-2])) for p in segs]
  cat = lambda k: np.concatenate([z[k] for z in parts if len(z[k])]) if any(len(z[k]) for z in parts) else np.zeros((0, 1))
  return {k: cat(k) for k in ("cs", "cc", "lp", "sp", "rs", "gas", "co")}, len(segs), len(jobs)


def main(argv):
  route = argv[1]
  D, nseg, nnew = load_route(route, "--rebuild" in argv)
  from scipy.signal import butter, sosfiltfilt, hilbert
  cs, cc, lp, sp, rs, gas, co = (D[k] for k in ("cs", "cc", "lp", "sp", "rs", "gas", "co"))
  tg = lp[:, 0]; t0 = tg[0]
  v = hold(cs[:, 0], cs[:, 1], tg); a = hold(cs[:, 0], cs[:, 2], tg); vcr = hold(cs[:, 0], cs[:, 3], tg)
  gasp = hold(cs[:, 0], cs[:, 4], tg); brkp = hold(cs[:, 0], cs[:, 5], tg)
  longon = hold(cc[:, 0], cc[:, 1], tg) == 1; cmd = hold(cc[:, 0], cc[:, 2], tg); pitch = hold(cc[:, 0], cc[:, 3], tg)
  lead = hold(rs[:, 0], rs[:, 1], tg); aT = lp[:, 1]; hasLead = lp[:, 2]; v0 = lp[:, 3]; vN = lp[:, 5]
  spv = hold(sp[:, 0], sp[:, 1], tg) if len(sp) > 1 else np.full(len(tg), np.nan)
  g = hold(gas[:, 0], gas[:, 1], tg); acmd = hold(gas[:, 0], gas[:, 2], tg); brk = hold(gas[:, 0], gas[:, 3], tg)
  # cruiseState.speed is 0 under openpilot long; carState.vCruise (km/h) is the set speed
  vcr = hold(cs[:, 0], cs[:, 7], tg) / 3.6
  cruise = longon & (lead == 0) & (hasLead == 0) & (v > 8.0) & np.isfinite(vcr) & (vcr < 100) & (gasp == 0) & (brkp == 0)
  err = v - vcr
  print(f"route {route}: {nseg} segs ({nnew} new), engaged {longon.sum()/FS/60:.1f} min, cruise-no-lead {cruise.sum()/FS/60:.1f} min  [{time.time()-T0:.1f} s]")
  # PRE-REGISTERED READOUT (brake-threshold fix 038103ddd4): brake entries/min, coast duty, sag per entry
  brk_e = np.flatnonzero(cruise[1:] & cruise[:-1] & (brk[1:] == 1) & (brk[:-1] == 0)) + 1
  coast = cruise & (brk == 0) & (g <= 5)
  sags = []
  for i in brk_e:
    j = i
    while j < len(brk) and brk[j] == 1:
      j += 1
    sags.append((v[i] - v[i:min(j + int(10 * FS), len(v))].min()) * MPH)
  print(f"  READOUT: brake entries in no-lead cruise {len(brk_e)} = {len(brk_e) / max(cruise.sum() / FS / 60, 1e-9):.1f}/min "
        f"(route bb before the fix: 4.2/min) | coast duty (gas 0, no brake) {coast.sum() / max(cruise.sum(), 1):.0%} (before: 0 %) | "
        f"speed sag per entry p50 {np.median(sags) if sags else float('nan'):.1f} mph (before: 4.9) | brake duty {np.nanmean(brk[cruise]):.0%} (before: 37 %)")
  if cruise.sum() < 20 * FS:
    print("  too little no-lead cruise"); return
  sos = butter(2, [1 / 40.0, 1 / 4.0], btype="band", fs=FS, output="sos")
  env = np.full(len(tg), np.nan); bp = np.full(len(tg), np.nan)
  eps = []
  for s, e in runs(cruise, int(30 * FS)):
    x = err[s:e]; y = sosfiltfilt(sos, x - x.mean()); bp[s:e] = y; env[s:e] = np.abs(hilbert(y)); eps.append((s, e))
  ok = np.isfinite(env)
  if ok.sum() == 0:
    print("  no cruise episode >= 30 s"); return
  print(f"  episodes >= 30 s: {len(eps)}, {ok.sum()/FS/60:.1f} min; vCruise values: "
        + ", ".join(f"{k*MPH:.0f}mph" for k in np.unique(np.round(vcr[ok], 1))[:8]))
  print(f"  vEgo - vCruise: mean {np.mean(err[ok])*MPH:+.2f} mph, p10/p50/p90 {np.percentile(err[ok],10)*MPH:+.2f}/{np.percentile(err[ok],50)*MPH:+.2f}/{np.percentile(err[ok],90)*MPH:+.2f} mph")
  zc = np.count_nonzero(np.diff(np.sign(bp[ok])) != 0); per = 2 * ok.sum() / FS / zc if zc else np.nan
  print(f"  band 4-40 s: envelope median {np.nanmedian(env[ok])*MPH:.2f} mph, p90 {np.nanpercentile(env[ok],90)*MPH:.2f} mph; mean period {per:.1f} s")
  print(f"  aTarget p10/p50/p90 {np.percentile(aT[ok],10):+.2f}/{np.percentile(aT[ok],50):+.2f}/{np.percentile(aT[ok],90):+.2f}; "
        f"max|cmd-aTarget| {np.nanmax(np.abs(cmd[ok]-aT[ok])):.3f}; planner speeds[0]-vEgo p50 {np.nanmedian(v0[ok]-v[ok])*MPH:+.2f} mph; "
        f"starpilotPlan.vCruise - cruiseState.speed p50 {np.nanmedian(spv[ok]-vcr[ok])*MPH:+.2f} mph")
  print(f"  brake-request duty {np.nanmean(brk[ok]):.1%}; gas p10/p50/p90 {np.nanpercentile(g[ok],10):.0f}/{np.nanpercentile(g[ok],50):.0f}/{np.nanpercentile(g[ok],90):.0f}; "
        f"acmd p10/p50/p90 {np.nanpercentile(acmd[ok],10):+.2f}/{np.nanpercentile(acmd[ok],50):+.2f}/{np.nanpercentile(acmd[ok],90):+.2f}; pitch p50 {np.degrees(np.nanmedian(pitch[ok])):+.2f} deg")

  def bpf(x):
    out = np.full(len(tg), np.nan)
    for s, e in eps:
      xx = np.nan_to_num(x[s:e]); out[s:e] = sosfiltfilt(sos, xx - xx.mean())
    return out
  be, ba, bg, bc = bp, bpf(aT), bpf(g), bpf(acmd)
  rr = lambda x, y: np.corrcoef(x[ok], y[ok])[0, 1]
  print(f"  band corr(err, aTarget) {rr(be,ba):+.2f}  corr(err, gas) {rr(be,bg):+.2f}  corr(err, accel cmd) {rr(be,bc):+.2f}  corr(err, brake) {rr(be,bpf(brk)):+.2f}")
  lags = np.arange(-200, 201, 5)
  c = [np.corrcoef(np.roll(be, k)[ok], ba[ok])[0, 1] for k in lags]
  k = int(np.argmin(c)); print(f"  most negative corr(err shifted, aTarget) {c[k]:+.2f} at err leading aTarget by {lags[k]/FS:+.1f} s")
  if "--dump" in argv:
    for s, e in eps:
      y = bp[s:e]
      mins = [i for i in range(1, len(y) - 1) if y[i] < y[i-1] and y[i] <= y[i+1] and y[i] < -0.3]
      print(f"  episode {(tg[s]-t0):.0f}-{(tg[e-1]-t0):.0f} s, vCruise {np.nanmedian(vcr[s:e])*MPH:.0f} mph, {len(mins)} dips > 0.7 mph")
      for i in mins[:12]:
        j = s + i; w0, w1 = max(s, j - int(10 * FS)), min(e, j + int(10 * FS))
        print(f"    t {tg[j]-t0:6.0f}s dip {err[j]*MPH:+.1f} mph (raw), 20 s window: err {err[w0:w1].min()*MPH:+.1f}..{err[w0:w1].max()*MPH:+.1f}, "
              f"aT {aT[w0:w1].min():+.2f}..{aT[w0:w1].max():+.2f}, gas {np.nanmin(g[w0:w1]):.0f}..{np.nanmax(g[w0:w1]):.0f}, brake {np.nanmean(brk[w0:w1]):.0%}, acmd min {np.nanmin(acmd[w0:w1]):+.2f}")
  if "--trace" in argv:
    s, e = max(eps, key=lambda p: p[1] - p[0])
    print("  TRACE longest episode every 1 s: t, err mph, aT, acmd, gas, brk, v0-v mph, aEgo")
    for j in range(s, e, int(FS)):
      print(f"    {tg[j]-t0:6.0f} {err[j]*MPH:+5.1f} {aT[j]:+5.2f} {acmd[j]:+5.2f} {g[j]:5.0f} {int(brk[j])} {(v0[j]-v[j])*MPH:+5.2f} {a[j]:+5.2f}")
  print(f"  [{time.time()-T0:.1f} s]")


if __name__ == "__main__":
  main(sys.argv)
