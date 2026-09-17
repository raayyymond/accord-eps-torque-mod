"""Windows-adapted from rev64-goal/scripts/rev64_09_configdiff.py: what ACTUALLY differed on the car
between the V282 reference route and the T64 (rev 6.4) routes -- initData params, not commit-message claims.
Answers: is the V282-vs-T64 comparison confounded by a fork LAF/Kp/rate-plant-FF difference on top of the
EPS-mode difference?"""
import sys, glob
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
from rlog_parse import read_messages

def params(route_glob):
    p = sorted(glob.glob(route_glob))[0]
    out = {}
    n = 0
    for evt in read_messages(p):
        try:
            w = evt.which()
        except Exception:
            continue
        n += 1
        if w == 'initData':
            d = evt.initData
            out['__gitCommit'] = str(d.gitCommit)
            try:
                for e in d.params.entries:
                    k = e.key if isinstance(e.key, str) else e.key.decode('utf8', 'ignore')
                    v = e.value
                    v = v.decode('utf8', 'ignore') if isinstance(v, (bytes, bytearray)) else str(v)
                    if len(v) < 80:
                        out[k] = v
            except Exception as ex:
                print('param err', ex)
            break
        if n > 5000:
            break
    return out

R = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs/'
routes = {
    'V282-64': R + '75604b0a432fdc89_00000064--ce6b0b0ebb--0--rlog.zst',
    'V282-65': R + '75604b0a432fdc89_00000065--b9f78988bd--0--rlog.zst',
    'V282-6c': R + '75604b0a432fdc89_0000006c--2bc842dbac--0--rlog.zst',
    'T64-6c': R + '75604b0a432fdc89_0000006c--68c6e94b17--0--rlog.zst',
    'T64-6d': R + '75604b0a432fdc89_0000006d--05e83bb04f--0--rlog.zst',
}
P = {}
for name, f in routes.items():
    import os
    if not os.path.exists(f):
        print(f"MISSING: {name} {f}")
        continue
    P[name] = params(f)
    print(f"{name}: commit {P[name].get('__gitCommit','?')[:12]}  ({len(P[name])} params)")

print()
print("=" * 110)
print("EVERY PARAM DIFFERENCE, V282 ROUTES vs T64 ROUTES (lateral-control relevant marked *)")
print("=" * 110)
keys = sorted(set().union(*[set(p) for p in P.values()]))
ndiff = 0
for k in keys:
    if k.startswith('__'):
        continue
    vals = {name: P[name].get(k, '<absent>') for name in P}
    if len(set(vals.values())) == 1:
        continue
    ndiff += 1
    star = ' *' if any(s in k for s in ('ccord', 'Lane', 'Steer', 'Torque', 'LatAccel', 'Friction', 'Kp', 'Ki', 'Kd', 'LAF')) else ''
    row = "  ".join(f"{name}={vals[name][:22]}" for name in P)
    print(f"  {k[:38]:38s} {row}{star}")
print(f"\n  {ndiff} parameters differ across these 5 routes.")

print()
print("=" * 110)
print("DID THE TWO T64 ROUTES DIFFER FROM EACH OTHER, OR THE THREE V282 ROUTES FROM EACH OTHER?")
print("=" * 110)
v282_names = [n for n in P if n.startswith('V282')]
t64_names = [n for n in P if n.startswith('T64')]
for group_names, label in [(v282_names, 'V282'), (t64_names, 'T64')]:
    d = [k for k in keys if not k.startswith('__') and len(set(P[n].get(k, '<absent>') for n in group_names)) > 1]
    print(f"  within-{label} differences: {d if d else 'none -- internally consistent'}")
