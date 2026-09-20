"""Adversarial check of finding B1 (rev64 observer share of below-8 m/s shake feed).

Reproduces b07_rank's per-bin b_eq(term) at tau=30ms directly from b02_rows.json (rev64=T64+T64B
group) and compares B1's hand-built "total feed" denominator (ffwd + dob_log + hyst, which
double-counts hyst since ffwd := hold+move+hyst+rl_ff+p_sp per b02_beq.py) against the two REAL
net-command measures already in the same table: u_log (P_log+I_log+F_log, the logged PID sum) and
u_e4 (the actual wire command). Both are avaiable at the same tau/weights B1 used.

Result: at 3-8 m/s the real net command is far smaller than B1's ad hoc "-8.9e-4" denominator
(u_log=-0.51e-4, u_e4=-1.78e-4, vs B1's -8.9e-4 -- 5-17x smaller), because ffwd's feed is nearly
cancelled by fbk's damping (fbk excluded from B1's denominator entirely). Against the REAL net
command, the observer's share is NOT 13%: subtracting dob_log's own b_eq from u_log FLIPS ITS SIGN
(feed -0.51 -> damp +0.61); subtracting it from u_e4 removes 63% of that command's net feed
(-1.78 -> -0.65). Per-route (6c, 6d net-damping already; 6e net-feeding), the observer's swing is
comparable to or larger than the route's own net command in 2 of 3 routes.

This does not predict what ARM-D will measure on-car (that would be exactly the open-loop /
closed-loop-fixed predictor the brief forbids) -- it only shows B1's own "13%, cannot be the main
lever below 8 m/s" arithmetic used an inconsistent, non-physical denominator instead of the u_log/
u_e4 columns sitting in the same b07 table, and that the correct comparison undermines the
conclusion drawn from it.
"""
import json

rows = json.load(open('../../b_shake/out/b02_rows.json'))
GR = ('T64', 'T64B')


def est(sub, k):
    rr = sum(r['rr'] for r in sub)
    return -sum(r[k][1] for r in sub) / rr


print("Pooled rev64 (T64+T64B), tau=30ms, x1e-4:")
print(f"{'bin':6s} {'u_log':>8s} {'u_e4':>8s} {'dob':>8s} {'ffwd':>8s} {'fbk':>8s} {'hyst':>8s} "
      f"{'u_log_wo_obs':>13s} {'u_e4_wo_obs':>12s}")
for mb, bins in [('<3', ['<3']), ('3-6', ['3-6']), ('6-8', ['6-8']), ('3-8', ['3-6', '6-8']), ('8-15', ['8-15'])]:
    sub = [r for r in rows if r['g'] in GR and r['bin'] in bins]
    if not sub:
        continue
    u_log, u_e4, dob, ffwd, fbk, hyst = (est(sub, k) for k in ('u_log', 'u_e4', 'dob_log', 'ffwd', 'fbk', 'hyst'))
    print(f"{mb:6s} {u_log*1e4:+8.2f} {u_e4*1e4:+8.2f} {dob*1e4:+8.2f} {ffwd*1e4:+8.2f} {fbk*1e4:+8.2f} "
          f"{hyst*1e4:+8.2f} {(u_log-dob)*1e4:+13.2f} {(u_e4-dob)*1e4:+12.2f}")

print()
print("B1's constructed 'total feed' at 3-8 m/s: ffwd(-7.4, ALREADY includes hyst per b02_beq.py's")
print("D['ffwd']=hold+move+hyst+rl_ff+p_sp) + dob(-1.1) + hyst(-0.4) again = -8.9  <- double-counts hyst,")
print("and entirely omits fbk(+7.2), which is what actually cancels ffwd's feed in the real command.")
print()
print("Per-route (3-6+6-8 pooled), x1e-4:")
for route in ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']:
    sub = [r for r in rows if r['route'] == route and r['bin'] in ('3-6', '6-8')]
    secs = sum(r['secs'] for r in sub)
    if secs < 15:
        continue
    u_log, u_e4, dob = (est(sub, k) for k in ('u_log', 'u_e4', 'dob_log'))
    print(f"{route}: secs={secs:.0f} u_log={u_log*1e4:+.2f} u_e4={u_e4*1e4:+.2f} dob={dob*1e4:+.2f} "
          f"u_log_wo={(u_log-dob)*1e4:+.2f} u_e4_wo={(u_e4-dob)*1e4:+.2f}")
