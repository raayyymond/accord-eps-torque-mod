# -*- coding: utf-8 -*-
r"""s2b_washout_instrument.py -- D5-architect.  Can the EXISTING wire (0x1AB tap + 0x18F rate) see (a)'s washout D?
On V298's route-79 wire, replay V298's lane twice -- plain D and washout D (D on abe - EMA_2^-9(abe)) -- with every other
term identical, and compare R^2 against the measured tap, pooled and on slew frames (|rate| > 30 deg/s).  If the two
replays do not separate here, a V299-(a) drive could not attribute its own edit (the build would be uninterpretable).
Reuses s2_replay_tap's loaded state (imports it; ~2.3 s).  Wall printed."""
import contextlib, io, sys, time
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
t0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
with contextlib.redirect_stdout(io.StringIO()):
    import s2_replay_tap as S  # noqa: E402
L = S.L0
abt = np.empty((L["m"], 10), np.int64)
kn = np.minimum(L["F"] + 1, S.n - 1)
abt[:, :9] = S.abe[L["F"]][:, None]
abt[:, 9] = S.abe[kn]
abt = abt.ravel().astype(float)
lp = np.zeros_like(abt)
for a_, b_ in zip(*S.runs(L["run"] | L["rs"])):
    lp[a_:b_] = lfilter([2.0 ** -9], [1, -(1 - 2.0 ** -9)], abt[a_:b_], zi=[abt[a_] * (1 - 2.0 ** -9)])[0]
Dw = np.clip(np.round(6.0 * (abt - lp)), -10240, 10240).astype(np.int64)
Tw, _, _, _ = S.run_variant(L, L["c1"] | L["c2"] | L["c4"], D=Dw)
jj = S.j2
mt = S.mt
w18 = np.nan_to_num(S.W["w18"])
for nm, extra in (("pooled hands-off settled", np.ones(S.n, bool)), ("slews |rate|>30", np.abs(w18) > 30),
                  ("slews |rate|>60", np.abs(w18) > 60)):
    m = mt & extra[jj]
    print("%-26s n %6d  R^2 plain-D %.3f  washout-D %.3f" % (nm, m.sum(), S.r2(S.Ttap[m] / 8, S.T_R0[jj[m]] / 8),
                                                             S.r2(S.Ttap[m] / 8, Tw[jj[m]] / 8)))
print("wall %.1f s" % (time.time() - t0))
