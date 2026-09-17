"""Step 4 extension: code-exact model->setpoint transfer function for candidate toggle values on the rev 6.4 chain
(4 Hz jerk LP, liveDelay 0.30), vs the V282 chain.  Lag (s) and |H| at band centres and at the 2-2.7 Hz closed-loop wheel mode."""
import json, numpy as np
from lagmod import chain_H, phase_lag
f = np.array([0.1, 0.225, 0.45, 0.85, 1.2, 2.0, 2.35, 2.7])
rows = {}
for nm, ld, fc, rc in (("V282 chain (ld .20, 1.2 Hz, no ref)", 0.20, 1.2, 0.0),
                       ("rev6.4 as flown (ld .30, 4 Hz, ref .06)", 0.30, 4.0, 0.06),
                       ("rev6.4 AccordRefFilter 0.03", 0.30, 4.0, 0.03),
                       ("rev6.4 AccordRefFilter 0.0 (off)", 0.30, 4.0, 0.0),
                       ("rev6.4 ref .06, SteerDelay .20 (UseAuto off)", 0.20, 4.0, 0.06),
                       ("rev5/rev4 (ld .285, 1.2 Hz, ref .12)", 0.285, 1.2, 0.12)):
    H = chain_H(f, ld, fc, rc)
    rows[nm] = dict(f=f.tolist(), lag=phase_lag(H, f).round(4).tolist(), mag=np.abs(H).round(4).tolist())
    print(f"{nm:46s} lag " + " ".join(f"{x:+.3f}" for x in phase_lag(H, f)) + " | |H| " + " ".join(f"{x:.2f}" for x in np.abs(H)))
print("f (Hz):", f)
json.dump(rows, open("s07_toggle_tf.json", "w"), indent=1)
