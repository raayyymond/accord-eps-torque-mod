import numpy as np

def load(path):
    return dict(np.load(path))

def analyze(tag, path, vlo_kph, vhi_kph):
    d = load(path)
    t = d['t']
    rate = d['rate_c']  # CAN 0x14A x -1.0, column STEER_ANGLE_RATE deg/s; sign(gp-0x6abe) = -sign(rate_c)
    v_kph = d['cs_v'] * 3.6  # cs_v assumed m/s (openpilot convention)
    eng = d['cs_eng'] > 0.5

    dt = np.diff(t)
    print(f"--- {tag} ---  n={len(t)}  dt median={np.median(dt):.4f}s  v_kph range [{np.nanmin(v_kph):.1f},{np.nanmax(v_kph):.1f}]")

    mask_all = np.isfinite(rate) & np.isfinite(v_kph)
    mask_eng = mask_all & eng
    mask_hwy_eng = mask_eng & (v_kph >= vlo_kph) & (v_kph <= vhi_kph)
    mask_city_eng = mask_eng & (v_kph < 35)

    def flip_stats(mask, label):
        idx = np.where(mask)[0]
        if len(idx) < 10:
            print(f"  {label}: insufficient samples ({len(idx)})")
            return
        # only count consecutive-in-time pairs (guard against segment gaps): require dt small
        r = rate[idx]
        tt = t[idx]
        dtt = np.diff(tt)
        sgn = np.sign(r)
        sgn[sgn == 0] = 1  # treat exact zero as no flip trigger
        flips = (sgn[1:] != sgn[:-1]) & (dtt < 0.05)  # exclude cross-segment/gap pairs
        total_time = np.sum(dtt[dtt < 0.05])
        n_flip = np.sum(flips)
        rate_hz = n_flip / total_time if total_time > 0 else float('nan')
        # also |rate| stats in this mask, for context
        absr = np.abs(r)
        print(f"  {label}: n={len(idx)} time={total_time:.1f}s flips={n_flip} flip_rate={rate_hz:.3f}/s "
              f"(period={1/rate_hz:.3f}s -> {rate_hz/2:.3f}Hz full-cycle)  |rate| p50={np.nanpercentile(absr,50):.1f} p90={np.nanpercentile(absr,90):.1f} deg/s")
        return rate_hz

    r_all = flip_stats(mask_eng, "ENGAGED, all speeds")
    r_hwy = flip_stats(mask_hwy_eng, f"ENGAGED, {vlo_kph}-{vhi_kph} km/h")
    r_city = flip_stats(mask_city_eng, "ENGAGED, <35 km/h")
    return r_hwy

r97 = analyze("STOCK route 97", "_scratch/cache/r97/r97.npz", 40, 70)
r9e = analyze("V103 (6x) route 9e", "_scratch/cache/r9e/r9e.npz", 40, 70)

if r97 and r9e:
    print(f"\nRATIO (V103/stock) sign-flip rate, 40-70km/h engaged: {r9e/r97:.3f}x")
