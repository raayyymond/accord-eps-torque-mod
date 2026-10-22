# -*- coding: utf-8 -*-
"""Launch-jerk reader (StarPilot accord-PTM 311c4cc0, Honda Bosch openpilot long, 2020 Accord 2.0T 10AT).

usage:  python long_launch_jerk_read.py <route> [<route> ...] [--rebuild] [--plot] [--proposed]
        --proposed: open-loop replay of the learner variants in VARIANTS on every full launch
        --learn-speed=N --rail-freeze: replay the episodes with THAT learner (use the deployed settings on a drive
        flown with the proposed learner; the replay-vs-wire error is the deployment check)
        e.g. python long_launch_jerk_read.py 000000b9--d974cafee9 000000b8--ba643cd6f1 --plot

Each segment is extracted ONCE (parallel) to _scratch/cache/<route>/launch_seg<N>.npz with the fork's cereal at
311c4cc0 (same cache dir / ensure_cereal as long_pingpong_read.py).  Everything after is vectorised numpy.

Signals: carState vEgo/aEgo/gasPressed/brakePressed (100 Hz), carControl longActive/actuators.accel/pitch/
longControlState (100 Hz), longitudinalPlan aTarget (20 Hz), selfdriveState experimentalMode, radarState leadOne,
sendcan ACC_CONTROL 0x1DF GAS_COMMAND/ACCEL_COMMAND/BRAKE_REQUEST (50 Hz), can bus 1 POWERTRAIN_DATA 0x17C
ENGINE_RPM + PEDAL_GAS, can bus 1 GEARBOX_AUTO 0x1A3 TRANS_TARGET_GEAR + TRANS_SHIFT_ACTIVITY (_gearbox_common.dbc;
the car is transmissionType automatic, 0x188/0x191 are absent on the wire), userBookmark @93 / bookmarkButton @148.

GAS-FACTOR LEARNER, re-run offline exactly as carcontroller.py (311c4cc0, non-MVL Bosch branch), every 20 ms:
    force  = clip(accel, -3.5, 2.0) + sin(pitch)*9.81 + wind_mps2(v)*wind_factor
    if lcs == pid and not gasPressed and force > -0.2:  factor = clip(factor + (accel_c - aEgo)/50*force, 0.1, 3.0)
    if force >= 2.0: factor = min(factor, factor_before_gasmax) else factor_before_gasmax = factor
    gas = min(interp(force*factor, [-0.2, 2.0], [0, 1600]), max(60, last_gas + 60))
The simulated gas is checked against the logged GAS_COMMAND; the factor is seeded from the inverse lookup.
wind_factor is assumed 1.0 (BELIEF; it learns at 1/1000 per frame and the wind term is < 0.05 m/s^2 below 13 m/s).
"""
import io, json, os, sys, glob, subprocess, time
from multiprocessing import Pool
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "_scratch", "cache")
CEREAL = os.path.join(CACHE, "cereal_311c4cc0")
FIGS = os.path.join(KIT, "analysis-2020accord", "figures")
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
COMMIT = "311c4cc0"
DONGLE = "75604b0a432fdc89"
CACHE_VERSION = 1
ACC_CONTROL, PT_DATA, GEARBOX = 0x1DF, 0x17C, 0x1A3
WIND_V, WIND_M = [0.0, 13.4, 22.4, 31.3, 40.2], [0.0, 0.049, 0.136, 0.267, 0.441]
FS = 100.0
PID, STOPPING, STARTING = 1, 2, 3
LEARN = dict(speed=50.0, rail_freeze=False)   # replay learner settings; --learn-speed=N / --rail-freeze override     # LongCtrlState raw: off 0, pid 1, stopping 2, starting 3


def ensure_cereal():
  if os.path.exists(os.path.join(CEREAL, "log.capnp")):
    return
  os.makedirs(os.path.join(CEREAL, "include"), exist_ok=True)
  for dst, src in (("log.capnp", "cereal/log.capnp"), ("custom.capnp", "cereal/custom.capnp"),
                   ("legacy.capnp", "cereal/legacy.capnp"), ("car.capnp", "opendbc_repo/opendbc/car/car.capnp"),
                   ("include/c++.capnp", "cereal/include/c++.capnp")):
    out = subprocess.run(["git", "-C", FORK, "show", f"{COMMIT}:{src}"], capture_output=True, check=True).stdout
    with open(os.path.join(CEREAL, dst), "wb") as fh:
      fh.write(out)


def extract_segment(args):
  path, out = args
  import zstandard as zstd, capnp
  capnp.remove_import_hook()
  L = capnp.load(os.path.join(CEREAL, "log.capnp"))
  data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(open(path, "rb").read())).read()
  cs, cc, sd, rs, lp, gas, pt, gb, bm = [], [], [], [], [], [], [], [], []
  t_first = None
  for e in L.Event.read_multiple_bytes(data):
    w = e.which()
    t = e.logMonoTime * 1e-9
    if t_first is None:
      t_first = t
    if w == "carState":
      c = e.carState
      cs.append((t, c.vEgo, c.aEgo, c.gasPressed, c.brakePressed, c.standstill))
    elif w == "carControl":
      c = e.carControl
      o = c.orientationNED
      cc.append((t, c.longActive, c.actuators.accel, o[1] if len(o) == 3 else np.nan, c.actuators.longControlState.raw))
    elif w == "selfdriveState":
      s = e.selfdriveState
      sd.append((t, s.experimentalMode, s.enabled))
    elif w == "radarState":
      l = e.radarState.leadOne
      rs.append((t, l.status, l.dRel, l.vLead))
    elif w == "longitudinalPlan":
      lp.append((t, e.longitudinalPlan.aTarget))
    elif w == "sendcan":
      for m in e.sendcan:
        if m.address == ACC_CONTROL:
          d = m.dat
          if len(d) >= 5:
            g = (d[0] << 8) | d[1]
            g = g - 65536 if g & 0x8000 else g
            a = (d[3] << 3) | (d[4] >> 5)
            a = a - 2048 if a & 0x400 else a
            gas.append((t, g, a * 0.01, (d[4] >> 2) & 1))
          break
    elif w == "can":
      for m in e.can:
        if m.src != 1:
          continue
        if m.address == PT_DATA:
          d = m.dat
          pt.append((t, (d[2] << 8) | d[3], d[0]))
        elif m.address == GEARBOX:
          d = m.dat
          gb.append((t, d[1] & 0x0F, d[0]))
    elif w in ("userBookmark", "bookmarkButton"):
      bm.append((t, 0 if w == "userBookmark" else 1))
  f = lambda x, n: np.array(x, dtype=float) if x else np.zeros((0, n))
  np.savez(out, v=CACHE_VERSION, t_first=t_first or np.nan, cs=f(cs, 6), cc=f(cc, 5), sd=f(sd, 3), rs=f(rs, 4),
           lp=f(lp, 2), gas=f(gas, 4), pt=f(pt, 3), gb=f(gb, 3), bm=f(bm, 2))
  return out


KEYS = ("cs", "cc", "sd", "rs", "lp", "gas", "pt", "gb", "bm")


def segs_of(route):
  return sorted(glob.glob(os.path.join(RLOGS, f"{DONGLE}_{route}--*--rlog.zst")), key=lambda p: int(p.rsplit("--", 2)[-2]))


def load_routes(routes, rebuild=False):
  jobs, plan = [], {}
  for route in routes:
    segs = segs_of(route)
    if not segs:
      sys.exit(f"no rlogs for {route}")
    cdir = os.path.join(CACHE, route)
    os.makedirs(cdir, exist_ok=True)
    outs = []
    for p in segs:
      out = os.path.join(cdir, "launch_seg%s.npz" % p.rsplit("--", 2)[-2])
      outs.append((int(p.rsplit("--", 2)[-2]), out))
      if rebuild or not os.path.exists(out) or int(np.load(out)["v"]) != CACHE_VERSION:
        jobs.append((p, out))
    plan[route] = outs
  if jobs:
    ensure_cereal()
    with Pool(min(len(jobs), os.cpu_count() or 4)) as pool:
      pool.map(extract_segment, jobs)
  R = {}
  for route, outs in plan.items():
    parts = [(n, np.load(o)) for n, o in outs]
    D = {}
    for k in KEYS:
      xs = [z[k] for _, z in parts if len(z[k])]
      D[k] = np.concatenate(xs) if xs else np.zeros((0, 2))
    # segment start = its first carState (the first event's logMonoTime is a boot-time stamp in every segment)
    D["seg_t"] = [(n, float(z["cs"][0, 0])) for n, z in parts if len(z["cs"])]
    D["t0"] = D["seg_t"][0][1]
    D["nseg"] = len(parts)
    R[route] = D
  return R, len(jobs)


def hold(ts, xs, tg):
  i = np.searchsorted(ts, tg, side="right") - 1
  return np.where(i >= 0, xs[np.clip(i, 0, None)], np.nan)


def runs(mask, min_len=1):
  m = np.concatenate(([0], mask.astype(np.int8), [0]))
  d = np.diff(m)
  s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
  k = (e - s) >= min_len
  return list(zip(s[k], e[k]))


def zigzag(x, h):
  """turning points of x with hysteresis h: list of (index, +1 max / -1 min)"""
  tp = []
  if len(x) < 3 or not np.any(np.isfinite(x)):
    return tp
  x = np.where(np.isfinite(x), x, np.nanmean(x))
  d, hi, lo, ie = 0, 0, 0, 0
  for i in range(1, len(x)):
    if d == 0:
      if x[i] > x[hi]: hi = i
      if x[i] < x[lo]: lo = i
      if x[hi] - x[lo] > h:
        if hi > lo:
          tp.append((lo, -1)); d = 1; ie = hi
        else:
          tp.append((hi, 1)); d = -1; ie = lo
    elif d == 1:
      if x[i] > x[ie]: ie = i
      elif x[ie] - x[i] > h:
        tp.append((ie, 1)); d = -1; ie = i
    else:
      if x[i] < x[ie]: ie = i
      elif x[i] - x[ie] > h:
        tp.append((ie, -1)); d = 1; ie = i
  return tp


def learner_replay(acc, pitch, lcs, gasp, aego, v, gcmd, longa, seed_at=0):
  """re-run the Bosch gas-factor learner on the 50 Hz ACC_CONTROL grid (carcontroller.py 311c4cc0, non-MVL Bosch).
  Seed = inverse lookup at the first CLEAN frame (gas 20..1580, force > 0.3, not rate-limited) at/after seed_at;
  frames before it hold the seed. Returns force, inverse-lookup factor (clean frames only), replayed factor, replayed gas."""
  accel_c = np.clip(acc, -3.5, 2.0)
  force = accel_c + np.sin(np.nan_to_num(pitch)) * 9.81 + np.interp(v, WIND_V, WIND_M)
  x_inv = gcmd / 1600.0 * 2.2 - 0.2
  steady = np.concatenate(([False], np.abs(np.diff(gcmd)) < 59))
  clean = (gcmd > 20) & (gcmd < 1580) & (force > 0.3) & steady
  inv = np.where(clean, x_inv / np.where(force != 0, force, np.nan), np.nan)
  n = len(gcmd)
  fac = np.full(n, np.nan); gsim = np.full(n, np.nan)
  ic = np.flatnonzero(clean & (np.arange(n) >= seed_at))
  if len(ic) == 0:
    return force, inv, fac, gsim
  k0 = ic[0]
  f = float(inv[k0]); f_bg = f
  last = float(gcmd[k0 - 1]) if k0 > 0 and gcmd[k0 - 1] > -1000 else 0.0
  fac[:k0] = f
  for k in range(k0, n):
    if not longa[k]:
      last = 0.0; fac[k] = f; gsim[k] = 0.0; continue
    if k > k0 and lcs[k] == PID and not gasp[k] and force[k] > -0.2 and         not (LEARN["rail_freeze"] and force[k] * f >= 2.0):
      f = min(max(f + (accel_c[k] - aego[k]) / LEARN["speed"] * force[k], 0.1), 3.0)
    if force[k] >= 2.0:
      f = min(f, f_bg)
    else:
      f_bg = f
    g = (min(max(force[k] * f, -0.2), 2.0) + 0.2) * (1600.0 / 2.2)
    g = min(g, max(60.0, last + 60.0))
    last = g
    fac[k] = f; gsim[k] = g
  return force, inv, fac, gsim


def analyse(route, D, bm_window=30.0):
  cs, cc, lp, gas, pt, gb, sd, rs = (D[k] for k in ("cs", "cc", "lp", "gas", "pt", "gb", "sd", "rs"))
  t0 = D["t0"]
  tg = cs[:, 0]
  G = dict(v=cs[:, 1], a=cs[:, 2], gp=cs[:, 3], bp=cs[:, 4],
           long=hold(cc[:, 0], cc[:, 1], tg), acc=hold(cc[:, 0], cc[:, 2], tg), lcs=hold(cc[:, 0], cc[:, 4], tg),
           aT=hold(lp[:, 0], lp[:, 1], tg), rpm=hold(pt[:, 0], pt[:, 1], tg), ped=hold(pt[:, 0], pt[:, 2], tg),
           gear=hold(gb[:, 0], gb[:, 1], tg), shift=hold(gb[:, 0], gb[:, 2], tg),
           exp=hold(sd[:, 0], sd[:, 1], tg), lead=hold(rs[:, 0], rs[:, 1], tg), dRel=hold(rs[:, 0], rs[:, 2], tg),
           vLead=hold(rs[:, 0], rs[:, 3], tg))
  tz = gas[:, 0]
  Z = dict(g=gas[:, 1], brk=gas[:, 3], acc=hold(cc[:, 0], cc[:, 2], tz), pitch=hold(cc[:, 0], cc[:, 3], tz),
           lcs=hold(cc[:, 0], cc[:, 4], tz), gp=hold(tg, G["gp"], tz) == 1, a=hold(tg, G["a"], tz),
           v=hold(tg, G["v"], tz), longa=hold(cc[:, 0], cc[:, 1], tz) == 1)
  G.update(gcmd=hold(tz, Z["g"], tg), brk=hold(tz, Z["brk"], tg),
           fac=np.full(len(tg), np.nan), inv=np.full(len(tg), np.nan), force=np.full(len(tg), np.nan),
           gsim=np.full(len(tg), np.nan))
  out = dict(route=route, nseg=D["nseg"], minutes=round((tg[-1] - tg[0]) / 60, 1), bookmarks=[], launches=[])
  seg_t = D["seg_t"]
  for tb, kind in D["bm"]:
    seg = max(n for n, ts in seg_t if ts <= tb + 1e-6)
    out["bookmarks"].append(dict(kind=["userBookmark", "bookmarkButton"][int(kind)], t_route_s=round(tb - t0, 2),
                                 seg=seg, t_in_seg_s=round(tb - dict(seg_t)[seg], 2), t_abs=tb))
  on = (G["long"] == 1) & (G["v"] < 3.0) & (G["aT"] > 0.5)
  starts = np.flatnonzero(on[1:] & ~on[:-1]) + 1
  ons, lastt = [], -1e9
  for s in starts:
    if tg[s] - lastt > 15.0:
      ons.append(s); lastt = tg[s]

  def episode(ta, tb_, tag, ref):
    idx = np.flatnonzero((tg >= ta) & (tg <= tb_))
    if len(idx) < 200:
      return None
    zi = np.flatnonzero((tz >= ta) & (tz <= tb_))
    force, inv, fac, gsim = learner_replay(Z["acc"][zi], Z["pitch"][zi], Z["lcs"][zi], Z["gp"][zi], Z["a"][zi],
                                           Z["v"][zi], Z["g"][zi], Z["longa"][zi],
                                           seed_at=int(np.searchsorted(tz[zi], ref)))
    for k_, x_ in (("fac", fac), ("inv", inv), ("force", force), ("gsim", gsim)):
      G[k_][idx] = hold(tz[zi], x_, tg[idx])
    live = Z["longa"][zi] & (Z["g"][zi] > -1000) & np.isfinite(gsim) & (tz[zi] >= ref)
    rerr = np.abs(gsim - Z["g"][zi])[live]
    tt = tg[idx] - ref
    a, aT, gc, fc = G["a"][idx], G["aT"][idx], G["gcmd"][idx], G["fac"][idx]
    gear, rpm = G["gear"][idx], G["rpm"][idx]
    eng = (G["long"][idx] == 1) & (tt >= 0)
    err = a - aT
    dgear = np.flatnonzero(np.diff(gear) != 0) + 1
    up = dgear[gear[dgear] > gear[dgear - 1]]
    # over -> under cycles: a run with err > +0.4, then within 3 s of its peak a run with err < -0.4 (engaged)
    cyc = []
    over = runs(eng & (err > 0.4)); under = runs(eng & (err < -0.4))
    i_last = -1
    for s0, e0 in over:
      if s0 < i_last:
        continue
      pk = s0 + int(np.argmax(err[s0:e0]))
      nxt = [(s1, e1) for s1, e1 in under if s1 > pk and tt[s1] - tt[pk] <= 3.0]
      if not nxt:
        continue
      s1, e1 = nxt[0]
      tr = s1 + int(np.argmin(err[s1:e1]))
      i_last = e1
      sl = slice(pk, tr + 1)
      g_seg = np.where(gc[sl] > -1000, gc[sl], 0)
      up_near = [int(gear[k]) for k in up if tt[pk] - 0.3 <= tt[k] <= tt[tr] + 0.3]
      up_t = [round(float(tt[k]), 2) for k in up if tt[pk] - 0.3 <= tt[k] <= tt[tr] + 0.3]
      ig = pk + int(np.argmin(g_seg))
      fz = G["force"][idx]
      # gas-cut onset: last frame in [peak - 1 s, gas-min] where gas is within 50 counts of that window's max
      w0 = max(pk - 100, 0)
      gw = np.where(gc[w0:ig + 1] > -1000, gc[w0:ig + 1], 0)
      i_cut = w0 + int(np.flatnonzero(gw >= gw.max() - 50)[-1])
      # gas = (clip(force*factor) + 0.2)*1600/2.2: split the gas drop peak->gas-min into force vs factor shares (log)
      fp, fm, kp_, km_ = fz[pk], fz[ig], fc[pk], fc[ig]
      share = None
      if fp > 0.05 and fm > 0.05 and kp_ > 0 and km_ > 0 and abs(np.log(fp * kp_ / (fm * km_))) > 1e-3:
        share = round(float(np.log(kp_ / km_) / np.log(fp * kp_ / (fm * km_))), 2)
      cyc.append(dict(t_peak=round(float(tt[pk]), 2), t_trough=round(float(tt[tr]), 2),
                      err_peak=round(float(err[pk]), 2), err_trough=round(float(err[tr]), 2),
                      aT_change=round(float(aT[tr] - aT[pk]), 2), aEgo_drop=round(float(a[pk] - a[tr]), 2),
                      gas_at_peak=int(gc[pk]) if gc[pk] > -1000 else -1, gas_min=int(g_seg.min()),
                      fac_peak=round(float(fc[pk]), 2), fac_min=round(float(np.nanmin(fc[sl])), 2),
                      rpm_peak=int(rpm[pk]), gear_peak=int(gear[pk]), upshift_to=up_near, upshift_t=up_t,
                      t_gas_min=round(float(tt[ig]), 2), t_gas_cut=round(float(tt[i_cut]), 2), force_peak=round(float(fp), 2), force_gas_min=round(float(fm), 2),
                      factor_share_of_gas_drop=share,
                      brake_in=bool(np.any(G["brk"][idx][sl] == 1))))
    gm = np.where(gc > -1000, gc, np.nan)
    ok = np.isfinite(gm) & eng
    lag_ms = lag_r = None
    if ok.sum() > 300:
      x = np.where(ok, gm, 0.0); x[ok] -= x[ok].mean(); y = np.where(ok, a - a[ok].mean(), 0.0)
      x = x - np.convolve(x, np.ones(201) / 201, "same"); y = y - np.convolve(y, np.ones(201) / 201, "same")
      L_ = np.arange(0, 151)
      r = np.array([np.dot(x[:len(x) - k], y[k:]) for k in L_]) / np.sqrt(np.dot(x, x) * np.dot(y, y) + 1e-12)
      k = int(np.argmax(r)); lag_ms, lag_r = int(L_[k] * 10), round(float(r[k]), 2)
    tp_T = zigzag(np.where(eng, aT, np.nan), 0.3)
    fe = fc[eng & np.isfinite(fc)]
    dfac = np.concatenate((np.abs(fc[20:] - fc[:-20]) / 0.2, np.full(19, np.nan)))   # slew over 0.2 s (the 50 Hz learner held at 100 Hz)
    ep = dict(tag=tag, t_route_s=round(ref - t0, 1), dur_s=round(tb_ - ref, 1),
              v_start=round(float(G["v"][idx][tt >= 0][0]), 1), v_end=round(float(G["v"][idx[-1]]), 1),
              v_max=round(float(np.nanmax(G["v"][idx])), 1),
              exp_mode=round(float(np.nanmean(G["exp"][idx][eng])), 2) if eng.any() else None,
              lead_frac=round(float(np.nanmean(G["lead"][idx][eng] == 1)), 2) if eng.any() else None,
              engaged_frac=round(float(eng[tt >= 0].mean()), 2),
              n_cycles=len(cyc), aT_reversals=max(len(tp_T) - 1, 0),
              aT_max=round(float(np.nanmax(aT[eng])), 2) if eng.any() else None,
              err_min_max=[round(float(err[eng].min()), 2), round(float(err[eng].max()), 2)] if eng.any() else None,
              fac_min_max=[round(float(fe.min()), 2), round(float(fe.max()), 2)] if len(fe) else None,
              fac_slew_max_per_s=round(float(np.nanmax(np.where(eng[1:], dfac, np.nan))), 2)
              if np.isfinite(np.where(eng[1:], dfac, np.nan)).any() else None,
              fac_floor_hit=bool(len(fe) and fe.min() <= 0.1001),
              inv_fac_p10_p90=[round(float(np.nanpercentile(G["inv"][idx][eng], q)), 3) for q in (10, 90)]
              if np.isfinite(G["inv"][idx][eng]).sum() >= 20 else None,
              err_mean_0_4s=round(float(np.mean(err[eng & (tt < 4.0)])), 2) if (eng & (tt < 4.0)).any() else None,
              gas_rail_frac=round(float(np.mean(gm[ok] >= 1599)), 2) if ok.any() else None,
              replay_err=[round(float(np.percentile(rerr, 50)), 1), round(float(np.percentile(rerr, 90)), 1)]
              if len(rerr) > 20 else None,
              lag_aEgo_vs_gas_ms=lag_ms, lag_r=lag_r,
              gear_seq=[int(gear[0])] + [int(gear[k]) for k in dgear] if np.isfinite(gear[0]) else None,
              cycles=cyc)
    return ep

  for s in ons:
    off = np.flatnonzero(G["long"][s:] != 1)
    e = s + off[0] if len(off) else len(tg) - 1
    ep = episode(tg[s] - 2.0, min(tg[s] + 25.0, tg[e]), "launch", ref=tg[s])
    if ep:
      out["launches"].append(ep)
  for b in out["bookmarks"]:
    b["episode"] = episode(b["t_abs"] - bm_window, b["t_abs"] + bm_window, "bookmark", ref=b["t_abs"] - bm_window)
  return out, G


def make_plot(route, tag, tt, idx, G):
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  fig, ax = plt.subplots(6, 1, figsize=(12, 13), sharex=True)
  g = lambda k: G[k][idx]
  ax[0].plot(tt, g("aT"), label="longitudinalPlan.aTarget", color="#3b6fd8")
  ax[0].plot(tt, g("acc"), label="actuators.accel", color="#7a7a7a", ls="--")
  ax[0].plot(tt, g("a"), label="carState.aEgo", color="#d8543b")
  ax[0].set_ylabel("m/s²"); ax[0].legend(loc="upper right", fontsize=8); ax[0].grid(alpha=.3)
  gc = g("gcmd"); gcp = np.where(gc > -1000, gc, np.nan)
  ax[1].plot(tt, gcp, label="ACC_CONTROL GAS_COMMAND (logged)", color="#2a9d5c")
  ax[1].plot(tt, g("gsim"), label="replayed learner gas", color="#000", lw=.7, ls=":")
  ax[1].fill_between(tt, 0, 1600, where=g("brk") == 1, color="#d8543b", alpha=.15, label="BRAKE_REQUEST")
  ax[1].set_ylabel("counts"); ax[1].legend(loc="upper right", fontsize=8); ax[1].grid(alpha=.3)
  ax[2].plot(tt, g("fac"), label="replayed gas factor", color="#8a4bd8")
  ax[2].plot(tt, g("inv"), ".", ms=2, label="inverse-lookup factor", color="#c9a0f0")
  ax[2].plot(tt, g("force"), label="gas_pedal_force (m/s²)", color="#999", lw=.8)
  ax[2].set_ylabel("factor"); ax[2].legend(loc="upper right", fontsize=8); ax[2].grid(alpha=.3)
  ax[3].plot(tt, g("rpm"), color="#444"); ax[3].set_ylabel("engine rpm"); ax[3].grid(alpha=.3)
  ax[3].axhspan(1800, 2500, color="#f0c040", alpha=.15)
  ax[4].step(tt, g("gear"), where="post", color="#444"); ax[4].set_ylabel("target gear"); ax[4].grid(alpha=.3)
  ax[5].plot(tt, g("v"), color="#444", label="vEgo"); ax[5].plot(tt, g("ped"), color="#2a9d5c", lw=.7, label="PEDAL_GAS (raw)")
  ax[5].set_ylabel("m/s | raw"); ax[5].legend(loc="upper right", fontsize=8); ax[5].grid(alpha=.3)
  ax[5].set_xlabel("s from %s" % ("bookmark" if tag == "bookmark" else "launch onset"))
  for a_ in ax:
    a_.axvline(0, color="k", lw=.6)
  fig.suptitle(f"{route} {tag}")
  fig.tight_layout()
  os.makedirs(FIGS, exist_ok=True)
  p = os.path.join(FIGS, f"long_launch_jerk_{route}_{tag}_{int(round(G['_t0rel'][idx[0]]))}.png")
  fig.savefig(p, dpi=90); plt.close(fig)
  return os.path.relpath(p, KIT)


def cycle_class(c):
  if c["gear_peak"] == 1 and c["rpm_peak"] < 1000:
    return "release_lurch"
  if c["brake_in"] or c["gas_at_peak"] < 0:
    return "gas_brake"
  return "gas_cut"


def summarise(outs, od):
  rows, cyc = [], []
  for o in outs:
    for e in o["launches"]:
      cl = [cycle_class(c) for c in e["cycles"]]
      full = e["v_start"] < 1.0 and e["v_max"] > 10.0
      ng = cl.count("gas_cut")
      fm = e["fac_min_max"] or [np.nan, np.nan]
      rows.append(dict(route=o["route"][:8], t=e["t_route_s"], full=full, aT_max=e["aT_max"], n_gas_cut=ng,
                       n_brake=cl.count("gas_brake"), n_lurch=cl.count("release_lurch"),
                       fac_ratio=fm[1] / fm[0] if fm[0] > 0 else np.nan, fac_swing=fm[1] - fm[0], rail=e["gas_rail_frac"]))
      for c, k in zip(e["cycles"], cl):
        c = dict(c); c["cls"] = k; c["full"] = full; c["route"] = o["route"][:8]; c["t_launch"] = e["t_route_s"]
        cyc.append(c)
  print()
  print("POPULATION (launch = longActive, v < 3 m/s, aTarget crosses 0.5; full = from < 1 m/s to > 10 m/s)")
  F = [r for r in rows if r["full"]]
  print(f"  launches {len(rows)} (full {len(F)}); with >= 1 gas-cut cycle: all {sum(r['n_gas_cut'] > 0 for r in rows)}, "
        f"full {sum(r['n_gas_cut'] > 0 for r in F)}")
  for r in rows:
    print("   %s t=%7.1f full=%d aTmax %.2f gas_cut %d brake %d lurch %d fac swing %.2f (x%.1f) rail %.2f"
          % (r["route"], r["t"], r["full"], r["aT_max"], r["n_gas_cut"], r["n_brake"], r["n_lurch"], r["fac_swing"],
             r["fac_ratio"], r["rail"] or 0))
  if len(rows) > 3:
    n = np.array([r["n_gas_cut"] for r in rows], float)
    for k in ("fac_swing", "aT_max", "rail"):
      x = np.array([r[k] or 0 for r in rows], float)
      print(f"  corr(n_gas_cut, {k}) = {np.corrcoef(n, x)[0, 1]:+.2f} (n={len(rows)})")
  G_ = [c for c in cyc if c["cls"] == "gas_cut"]
  if G_:
    q = lambda k: np.array([c[k] for c in G_ if c[k] is not None], float)
    up = [c for c in G_ if c["upshift_t"]]
    dts = np.array([c["upshift_t"][0] - c["t_gas_min"] for c in up])
    dtc = np.array([c["upshift_t"][0] - c["t_gas_cut"] for c in up])
    dpk = np.array([c["t_gas_cut"] - c["t_peak"] for c in G_])
    print(f"  upshift minus gas-cut ONSET median {np.median(dtc):+.2f} s [p10 {np.percentile(dtc,10):+.2f}, p90 {np.percentile(dtc,90):+.2f}]; "
          f"gas-cut onset minus aEgo-overshoot peak median {np.median(dpk):+.2f} s [p10 {np.percentile(dpk,10):+.2f}, p90 {np.percentile(dpk,90):+.2f}]")
    print(f"  GAS-CUT cycles {len(G_)}: upshift inside peak..trough +-0.3 s in {len(up)}; "
          f"median |aT change| {np.median(np.abs(q('aT_change'))):.2f} vs aEgo drop {np.median(q('aEgo_drop')):.2f} m/s2; "
          f"err peak/trough median {np.median(q('err_peak')):+.2f}/{np.median(q('err_trough')):+.2f}; "
          f"gas drop median {np.median(q('gas_at_peak') - q('gas_min')):.0f} counts; "
          f"factor share of the gas drop median {np.median(q('factor_share_of_gas_drop')):.2f} "
          f"[p10 {np.percentile(q('factor_share_of_gas_drop'), 10):.2f}]; "
          f"rpm at overshoot peak median {np.median(q('rpm_peak')):.0f} [{q('rpm_peak').min():.0f}-{q('rpm_peak').max():.0f}]; "
          f"peak->trough {np.median(q('t_trough') - q('t_peak')):.2f} s; "
          f"upshift minus gas-min time median {np.median(dts):+.2f} s [p10 {np.percentile(dts,10):+.2f}, p90 {np.percentile(dts,90):+.2f}]")
  with open(os.path.join(od, "population.json"), "w", encoding="utf-8") as fh:
    json.dump(dict(rows=rows, cycles=cyc), fh, indent=1, default=float)


# ---------------------------------------------------------------------------------------------------------------
# --proposed : OPEN-LOOP counterfactual replay of the gas-factor learner on the full launches.
# The logged aEgo / accel / pitch / lcs are fed to a learner with different settings; the plant is NOT re-simulated,
# so the result is "what the factor (and the factor's share of the gas) would have done given the SAME car response".
# ---------------------------------------------------------------------------------------------------------------
VARIANTS = (  # name, gas_learn_speed, rail freeze, seed
  ("A_cruise", 50.0, False, "cruise"),     # 311c4cc0 learner, cruise seed
  ("B_cruise", 2000.0, True, "cruise"),    # proposed: learn speed 50 -> 2000 + no learning while force*factor >= 2.0
  ("B_logged", 2000.0, True, "logged"),    # proposed, seeded with the logged start value
  ("Bspeed_only", 2000.0, False, "cruise"),  # attribution: speed change alone
  ("Bfreeze_only", 50.0, True, "cruise"),    # attribution: rail freeze alone
)


def learner_cf(acc, pitch, lcs, gasp, aego, v, longa, f0, k0, learn_speed=50.0, rail_freeze=False):
  """carcontroller.py 311c4cc0 non-MVL Bosch learner with a configurable learn speed and an optional freeze while the
  gas lookup is saturated (force*factor >= 2.0). Starts at frame k0 with factor f0. Returns force, factor, gas, freezes."""
  accel_c = np.clip(acc, -3.5, 2.0)
  force = accel_c + np.sin(np.nan_to_num(pitch)) * 9.81 + np.interp(v, WIND_V, WIND_M)
  n = len(acc)
  fac = np.full(n, np.nan); gcf = np.full(n, np.nan)
  fac[:k0] = f0
  f, f_bg, last, nfrz = f0, f0, 0.0, 0
  for k in range(k0, n):
    if not longa[k]:
      last = 0.0; fac[k] = f; gcf[k] = 0.0; continue
    learn = lcs[k] == PID and not gasp[k] and force[k] > -0.2
    if learn and rail_freeze and force[k] * f >= 2.0:
      learn = False; nfrz += 1
    if learn:
      f = min(max(f + (accel_c[k] - aego[k]) / learn_speed * force[k], 0.1), 3.0)
    if force[k] >= 2.0:
      f = min(f, f_bg)
    else:
      f_bg = f
    g = (min(max(force[k] * f, -0.2), 2.0) + 0.2) * (1600.0 / 2.2)
    g = min(g, max(60.0, last + 60.0))
    last = g
    fac[k] = f; gcf[k] = g
  return force, fac, gcf, nfrz


def cruise_seed(Z, tz, ref):
  """implied steady factor = median inverse lookup over clean frames in the 30 s before the launch; the window is
  widened (60/120/300 s) until >= 25 clean frames exist. Returns (seed, window_s, n_frames)."""
  g = Z["g"]
  force = np.clip(Z["acc"], -3.5, 2.0) + np.sin(np.nan_to_num(Z["pitch"])) * 9.81 + np.interp(Z["v"], WIND_V, WIND_M)
  steady = np.concatenate(([False], np.abs(np.diff(g)) < 59))
  clean = (g > 20) & (g < 1580) & (force > 0.3) & steady & Z["longa"] & (Z["lcs"] == PID)
  inv = (g / 1600.0 * 2.2 - 0.2) / np.where(force != 0, force, np.nan)
  for w in (30.0, 60.0, 120.0, 300.0):
    m = clean & (tz >= ref - w) & (tz < ref)
    if m.sum() >= 25:
      return float(np.median(inv[m])), w, int(m.sum())
  return np.nan, None, 0


def proposed_replay(route, D, out):
  cs, cc, gas = D["cs"], D["cc"], D["gas"]
  tg, tz = cs[:, 0], gas[:, 0]
  Z = dict(g=gas[:, 1], acc=hold(cc[:, 0], cc[:, 2], tz), pitch=hold(cc[:, 0], cc[:, 3], tz),
           lcs=hold(cc[:, 0], cc[:, 4], tz), gp=hold(tg, cs[:, 3], tz) == 1, a=hold(tg, cs[:, 2], tz),
           v=hold(tg, cs[:, 1], tz), longa=hold(cc[:, 0], cc[:, 1], tz) == 1)
  t0 = D["t0"]
  rows = []
  for e in out["launches"]:
    if not (e["v_start"] < 1.0 and e["v_max"] > 10.0):
      continue
    ref = t0 + e["t_route_s"]
    zi = np.flatnonzero((tz >= ref - 2.0) & (tz <= ref + e["dur_s"]))
    tt = tz[zi] - ref
    k0 = int(np.searchsorted(tt, 0.0))
    seed_c, w_c, n_c = cruise_seed(Z, tz, ref)
    # logged seed = inverse lookup at the first clean frame at/after onset (as the baseline replay)
    _, inv_l, _, _ = learner_replay(Z["acc"][zi], Z["pitch"][zi], Z["lcs"][zi], Z["gp"][zi], Z["a"][zi], Z["v"][zi],
                                    Z["g"][zi], Z["longa"][zi], seed_at=k0)
    il = np.flatnonzero(np.isfinite(inv_l) & (np.arange(len(zi)) >= k0))
    seed_l = float(inv_l[il[0]]) if len(il) else np.nan
    cyc = [c for c in e["cycles"] if cycle_class(c) == "gas_cut"]
    glog = Z["g"][zi]
    log_drop = sum(max(float(glog[np.searchsorted(tt, c["t_peak"])] - glog[np.searchsorted(tt, c["t_gas_min"])]), 0.0)
                   for c in cyc)
    row = dict(route=route[:8], t=e["t_route_s"], aT_max=e["aT_max"], n_gas_cut=len(cyc), seed_cruise=round(seed_c, 3),
               seed_cruise_window_s=w_c, seed_cruise_frames=n_c, seed_logged=round(seed_l, 3),
               logged_gas_cut_sum=round(log_drop),
               logged_gas_mean_0_4s=round(float(np.mean(np.clip(glog[(tt >= 0) & (tt < 4.0)], 0, None)))),
               logged_gas_mean_4_12s=round(float(np.mean(np.clip(glog[(tt >= 4.0) & (tt < 12.0)], 0, None)))))
    for name, ls, frz, sk in VARIANTS:
      f0 = seed_c if sk == "cruise" else seed_l
      if not np.isfinite(f0):
        row[name] = None; continue
      force, fac, gcf, nfrz = learner_cf(Z["acc"][zi], Z["pitch"][zi], Z["lcs"][zi], Z["gp"][zi], Z["a"][zi], Z["v"][zi],
                                         Z["longa"][zi], f0, k0, ls, frz)
      fe = fac[k0:]
      slew = np.abs(fe[10:] - fe[:-10]) / 0.2 if len(fe) > 10 else np.array([0.0])
      cf_drop = sum(max(float(gcf[np.searchsorted(tt, c["t_peak"])] - gcf[np.searchsorted(tt, c["t_gas_min"])]), 0.0)
                    for c in cyc)
      row[name] = dict(fac_min=round(float(np.nanmin(fe)), 3), fac_max=round(float(np.nanmax(fe)), 3),
                       swing=round(float(np.nanmax(fe) - np.nanmin(fe)), 3), slew_max_per_s=round(float(np.nanmax(slew)), 3),
                       cf_gas_cut_sum=round(cf_drop),
                       cut_share_removed=round(1 - cf_drop / log_drop, 2) if log_drop > 0 else None,
                       freeze_frames=nfrz, rail_frames=int(np.sum(gcf[k0:] >= 1599)),
                       gas_mean_0_4s=round(float(np.nanmean(gcf[(tt >= 0) & (tt < 4.0)]))),
                       gas_mean_4_12s=round(float(np.nanmean(gcf[(tt >= 4.0) & (tt < 12.0)]))))
    rows.append(row)
  return rows


def print_proposed(rows, od):
  print()
  print("PROPOSED REPLAY (open loop: logged aEgo; full launches only)")
  hdr = "  %-8s %7s %5s %3s | seed cruise(win,n) logged | " % ("route", "t", "aTmax", "cut")
  print(hdr + " | ".join(v[0] for v in VARIANTS) + "   [each: min-max swing slew/s cut-removed freeze]")
  for r in rows:
    s = "  %-8s %7.1f %5.2f %3d | %.2f(%s,%d) %.2f | " % (r["route"], r["t"], r["aT_max"], r["n_gas_cut"], r["seed_cruise"],
                                                         r["seed_cruise_window_s"], r["seed_cruise_frames"], r["seed_logged"])
    parts = []
    for name, *_ in VARIANTS:
      x = r[name]
      parts.append("—" if x is None else "%.2f-%.2f %.2f %.2f %s %d" % (x["fac_min"], x["fac_max"], x["swing"],
                                                                        x["slew_max_per_s"], x["cut_share_removed"],
                                                                        x["freeze_frames"]))
    print(s + " | ".join(parts) + "  (logged cut sum %d)" % r["logged_gas_cut_sum"])
  for name, *_ in VARIANTS:
    xs = [r[name] for r in rows if r[name]]
    if not xs:
      continue
    sw = np.array([x["swing"] for x in xs]); sl = np.array([x["slew_max_per_s"] for x in xs])
    cr = np.array([x["cut_share_removed"] for x in xs if x["cut_share_removed"] is not None])
    print(f"  {name:13s} swing median {np.median(sw):.3f} max {sw.max():.3f}; swing < 0.1 in {int((sw < 0.1).sum())}/{len(sw)}; "
          f"slew max median {np.median(sl):.3f}/s; cut share removed median {np.median(cr):.2f} [min {cr.min():.2f}]; "
          f"freeze frames total {sum(x['freeze_frames'] for x in xs)}; mean gas 0-4 s / 4-12 s vs logged: "
          + ", ".join(f"{x['gas_mean_0_4s']}/{x['gas_mean_4_12s']}" for x in xs))
  print("  logged mean gas 0-4 s / 4-12 s: " + ", ".join(f"{r['logged_gas_mean_0_4s']}/{r['logged_gas_mean_4_12s']}" for r in rows))
  with open(os.path.join(od, "proposed_replay.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1, default=float)


def main(argv):
  routes = [a for a in argv[1:] if not a.startswith("--")]
  if not routes:
    sys.exit(__doc__)
  for a in argv:
    if a.startswith("--learn-speed="):
      LEARN["speed"] = float(a.split("=", 1)[1])
  LEARN["rail_freeze"] = "--rail-freeze" in argv
  R, nnew = load_routes(routes, rebuild="--rebuild" in argv)
  tl = time.time() - T0
  od = os.path.join(KIT, "_scratch", "out", "long_launch_jerk")
  os.makedirs(od, exist_ok=True)
  R_out, P_rows = {}, []
  for route in routes:
    D = R[route]
    D_t = D["cs"][:, 0]
    plot = "--plot" in argv
    out, G = analyse(route, D)
    if plot and out["bookmarks"]:
      G["_t0rel"] = D_t - D["t0"]
      for b in out["bookmarks"]:
        m = (D_t >= b["t_abs"] - 30) & (D_t <= b["t_abs"] + 30)
        idx = np.flatnonzero(m)
        if b["episode"] is not None:
          b["episode"]["png"] = make_plot(route, "bookmark", D_t[idx] - b["t_abs"], idx, G)
    for b in out["bookmarks"]:
      b.pop("t_abs", None)
    R_out[route] = out
    if "--proposed" in argv:
      P_rows += proposed_replay(route, D, out)
    with open(os.path.join(od, route + ".json"), "w", encoding="utf-8") as fh:
      json.dump(out, fh, indent=1)
    L = out["launches"]
    print(f"== {route}: {out['nseg']} seg, {out['minutes']} min")
    for b in out["bookmarks"]:
      e = b["episode"] or {}
      print(f"  BOOKMARK {b['kind']} t={b['t_route_s']} s (seg {b['seg']} +{b['t_in_seg_s']} s) "
            f"engaged {e.get('engaged_frac')} png {e.get('png')}")
    print(f"  launches {len(L)}; with >=1 over->under cycle {sum(1 for e in L if e['n_cycles'])}")
    for e in L:
      print("  L t=%7.1f v %4.1f->%4.1f(max %4.1f) exp %.2f lead %.2f aTmax %s aTrev %d cyc %d err %s fac %s slew %s floor %s rail %s replay %s lag %s/%s gears %s"
            % (e["t_route_s"], e["v_start"], e["v_end"], e["v_max"], e["exp_mode"] or 0, e["lead_frac"] or 0, e["aT_max"],
               e["aT_reversals"], e["n_cycles"], e["err_min_max"], e["fac_min_max"], e["fac_slew_max_per_s"],
               e["fac_floor_hit"], e["gas_rail_frac"], e["replay_err"], e["lag_aEgo_vs_gas_ms"], e["lag_r"], e["gear_seq"]))
      for c in e["cycles"]:
        print("      " + json.dumps(c))
  summarise([R_out[r] for r in routes], od)
  if "--proposed" in argv:
    print_proposed(P_rows, od)
  print(f"wall {time.time()-T0:.1f} s (load {tl:.1f} s, {nnew} segments newly extracted)")


if __name__ == "__main__":
  main(sys.argv)
