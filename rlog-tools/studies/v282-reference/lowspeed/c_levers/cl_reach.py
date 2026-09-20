"""c_levers stage 2: each existing lever's quantity inside the low-speed stick-slip and shake situations, as LOGGED
(reconstruction validated in cl_recon.validate: corr 0.9998 with logged pid.f, median residual 0.0004 torque).

Situations (hands-off, fill_lowspeedlarg HO mask: usable & ~dilate(pressed, 0.5 s) & 2.5 <= v < 15):
  DWELL  stick-slip episodes, s4/fill_lowspeedlarg definition (10-frame |rate| < 0.75 deg/s for >= 0.12 s, same-sign
         angle travel >= 0.5 deg in the 0.5 s before and after); jump = |angle(end+0.3 s) - angle(end)|.
  SHAKE  1.8-3.5 Hz band of every term vs the steering rate, b_eq = -<T(t - tau), rate>/<rate, rate> (> 0 damps).
  TRANS  frames with |desired wheel rate| >= 40 deg/s (reconstructed angle_des rate).
"""
import sys, json, gc
from pathlib import Path
import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cl_recon as C
V = C.V

TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob', 'out']
VB = [2.5, 5.0, 8.0, 15.0]
MODE = 'ho'   # 'ho' = hands-off 2.5-15 (fill_lowspeedlarg); 'us' = V.usable 0.3-15 (s4 mask, includes creep)


def dil(m, n=50):
    return ndimage.binary_dilation(m, structure=np.ones(2 * n + 1, bool))


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def analyse(D):
    t, v, n = D['t'], D['v'], len(D['t'])
    hyst = D['cfg']['hyst']
    base = D['active'] & D['csact'] & (v >= 2.0)
    rawmove_abs = np.abs(D['cfg']['ffr'] * D['rate_des'] / np.interp(v, C.G_BP, C.G_V))
    if MODE == 'ho':
        HO = base & ~dil(D['pressed']) & (v >= VB[0]) & (v < VB[-1])
    else:
        HO = D['active'] & D['csact'] & ~D['pressed'] & (v >= VB[0]) & (v < VB[-1])
    gate = np.clip(1.0 - np.abs(D['out']) / C.DITHER_REF, 0, 1)
    lim = np.interp(v, C.MOVE_LIM_BP, C.MOVE_LIM_V)
    raw_move = D['cfg']['ffr'] * D['rate_des'] / np.interp(v, C.G_BP, C.G_V)
    clamp = np.abs(raw_move) >= lim - 1e-9
    dout = np.abs(np.diff(D['out'], prepend=D['out'][0]))
    ratelim = dout >= 0.0295
    fade = np.interp(v, C.DOB_FADE, [0, 1])
    sb = np.clip(np.searchsorted(VB, v, side='right') - 1, 0, len(VB) - 2)
    DW = []
    NBIN = len(VB) - 1
    SH = {k: {tau: dict(num={x: 0.0 for x in TERMS}, den=0.0) for tau in (0, 3, 6)} for k in range(NBIN)}
    SHrms = {k: dict(sec=0.0, **{x: 0.0 for x in TERMS + ['sr']}) for k in range(NBIN)}
    for a, b in V.runs(HO, t, min_s=2.0):
        m_ = b - a
        rsm = smooth(np.abs(D['sr'][a:b]), 10); low = rsm < 0.75; aa = D['sa'][a:b]
        i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            if j - i + 1 >= 12 and i - 50 >= 0 and j + 50 < m_:
                pre = aa[i] - aa[i - 50]; post = aa[j + 50] - aa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    s = np.sign(post); gi, gj = a + i, a + j
                    r = dict(v=float(v[gj]), sb=int(sb[gj]), dwell_s=(j - i + 1) / 100, jump=float(abs(aa[min(j + 30, m_ - 1)] - aa[j])),
                             ang=float(abs(aa[j])), dem_rate=float(np.mean(np.abs(D['rate_des'][gi:gj + 1]))),
                             err_deg=float(s * (D['angle_des'][gj] - D['sa'][gj])),
                             z_sat=float(np.mean(s * D['z'][gi:gj + 1] >= 0.99 * hyst)), z_end=float(s * D['z'][gj] / hyst),
                             gate_end=float(gate[gj]), gate_med=float(np.median(gate[gi:gj + 1])),
                             out_end=float(abs(D['out'][gj])), clamp=float(np.mean(clamp[gi:gj + 31])),
                             ratelim=float(np.mean(ratelim[gi:gj + 31])), lsf=float(D['lsf'][gj]), fade=float(fade[gj]),
                             sign_ok=float(np.sign(D['out'][gj] - D['out'][gi]) == s))
                    for x in TERMS:
                        r['b_' + x] = float(s * (D[x][gj] - D[x][gi]))
                        r['l_' + x] = float(s * D[x][gj])
                    DW.append(r)
            i = j + 1
        # shake band (and the 3.5-6 Hz pumping band, stored under tau keys 'p0','p3','p6')
        srb = C.bp_run(D['sr'][a:b], 1.8, 3.5)
        Tb = {x: C.bp_run(D[x][a:b], 1.8, 3.5) for x in TERMS}
        srp = C.bp_run(D['sr'][a:b], 3.5, 6.0)
        Tp = {x: C.bp_run(D[x][a:b], 3.5, 6.0) for x in ('P', 'move', 'rate_t', 'out', 'dob', 'hold')}
        kk = int(np.bincount(sb[a:b]).argmax())
        for tau in (0, 3, 6):
            d_ = SH[kk].setdefault('p%d' % tau, dict(num={}, den=0.0))
            rr = srp[tau:]; d_['den'] += float(np.dot(rr, rr))
            for x in Tp:
                d_['num'][x] = d_['num'].get(x, 0.0) + float(np.dot(Tp[x][:len(Tp[x]) - tau], rr))
        k = int(np.bincount(sb[a:b]).argmax())
        for tau in (0, 3, 6):
            rr = srb[tau:]
            SH[k][tau]['den'] += float(np.dot(rr, rr))
            for x in TERMS:
                SH[k][tau]['num'][x] += float(np.dot(Tb[x][:len(Tb[x]) - tau], rr))
        SHrms[k]['sec'] += m_ / 100
        SHrms[k]['sr'] += float(np.sum(srb ** 2))
        for x in TERMS:
            SHrms[k][x] += float(np.sum(Tb[x] ** 2))
    # frame-level duty per speed bin
    FR = {}
    for k in range(NBIN):
        mk = HO & (sb == k)
        tr = mk & (np.abs(D['rate_des']) >= 40)
        turn = mk & (np.abs(D['angle_des']) >= 15)
        FR[k] = dict(sec=float(mk.sum() / 100), trans_sec=float(tr.sum() / 100), turn_sec=float(turn.sum() / 100),
                     gate_med=float(np.median(gate[mk])) if mk.any() else None,
                     gate_med_turn=float(np.median(gate[turn])) if turn.any() else None,
                     gate_med_trans=float(np.median(gate[tr])) if tr.any() else None,
                     gate_gt05=float(np.mean(gate[mk] > 0.5)) if mk.any() else None,
                     zsat=float(np.mean(np.abs(D['z'][mk]) >= 0.99 * hyst)) if mk.any() else None,
                     zsat_trans=float(np.mean(np.abs(D['z'][tr]) >= 0.99 * hyst)) if tr.any() else None,
                     clamp=float(np.mean(clamp[mk])) if mk.any() else None,
                     clamp_trans=float(np.mean(clamp[tr])) if tr.any() else None,
                     ratelim=float(np.mean(ratelim[mk])) if mk.any() else None,
                     ratelim_trans=float(np.mean(ratelim[tr])) if tr.any() else None,
                     move2x_clamp_trans=float(np.mean(2 * rawmove_abs[tr] >= lim[tr])) if tr.any() else None,
                     move2x_clamp=float(np.mean(2 * rawmove_abs[mk] >= lim[mk])) if mk.any() else None,
                     rawmove_p99=float(np.percentile(rawmove_abs[mk], 99)) if mk.any() else None,
                     lsf_med=float(np.median(D['lsf'][mk])) if mk.any() else None,
                     fade_med=float(np.median(fade[mk])) if mk.any() else None,
                     **{f'rms_{x}': float(np.sqrt(np.mean(D[x][mk] ** 2))) if mk.any() else None for x in TERMS},
                     **{f'rms_{x}_trans': float(np.sqrt(np.mean(D[x][tr] ** 2))) if tr.any() else None for x in TERMS})
    return DW, SH, SHrms, FR


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'us':
        MODE = 'us'; VB[:] = [0.3, 2.5, 5.0, 8.0, 15.0]
    ALL = {}
    for rk in C.CFG:
        D = C.reconstruct(rk)
        DW, SH, SHrms, FR = analyse(D)
        ALL[rk] = dict(g=D['g'], DW=DW, SH=SH, SHrms=SHrms, FR=FR)
        print(rk, D['g'], 'dwells', len(DW), 'HO sec', [round(FR[k]['sec']) for k in FR], flush=True)
        del D; gc.collect()
    json.dump(ALL, open(C.OUT / ('reach.json' if MODE == 'ho' else 'reach_us.json'), 'w'), default=float)
