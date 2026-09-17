"""Same err_late (2-3.5s build-up error) as v2, but with explicit speed x peak-angle STRATIFIED matching
(reusing the same strat_diff formula s3_stats.py used for hold/build/unwind errors), to check whether the
finding's OWN pipeline's failure to stratify this particular metric was hiding a demand-amplitude confound,
or whether matching just confirms the unmatched null."""
import pickle
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
E = pickle.load(open(OUT + 'ensemble.pkl', 'rb'))
g = E['grid']
GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}

rows = []
for e in E['ens']:
    tr = e['tr']['i']
    m2 = (g >= 2.0) & (g < 3.5)
    err_late = float(np.nanmean((tr['aa'] - tr['ad'])[m2]))
    rows.append(dict(rk=e['rk'], group=e['group'], G=GM[e['group']], v=e['v'], P=e['P'], err_late=err_late))

def strata(r):
    vb = 0 if r['v'] < 5 else (1 if r['v'] < 8 else 2)
    pb = 0 if r['P'] < 60 else (1 if r['P'] < 150 else 2)
    return vb, pb

VB = ["2.5-5","5-8","8-15"]; PB=["25-60","60-150","150+"]
rng = np.random.default_rng(13); NB=3000

def strat_diff(A,B,k):
    cells={}
    for r in A: cells.setdefault(strata(r),[[],[]])[0].append(r.get(k,np.nan))
    for r in B: cells.setdefault(strata(r),[[],[]])[1].append(r.get(k,np.nan))
    use={c:(np.array(a,float),np.array(b,float)) for c,(a,b) in cells.items()}
    use={c:(a[np.isfinite(a)],b[np.isfinite(b)]) for c,(a,b) in use.items()}
    use={c:ab for c,ab in use.items() if len(ab[0])>=2 and len(ab[1])>=2}
    if not use: return None
    w={c:min(len(a),len(b)) for c,(a,b) in use.items()}; W=sum(w.values())
    def est(smp): return sum(w[c]*(np.mean(smp(b))-np.mean(smp(a))) for c,(a,b) in use.items())/W
    e0=est(lambda x:x)
    bs=[est(lambda x: x[rng.integers(0,len(x),len(x))]) for _ in range(NB)]
    return dict(diff=float(e0), ci=[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],
                cells={f"{VB[c[0]]}|{PB[c[1]]}":[len(a),len(b)] for c,(a,b) in use.items()}, n=W)

V282full=[r for r in rows if r['G']=='V282']
V282loro=[r for r in rows if r['G']=='V282' and r['rk']!='0000006c--2bc842dbac']
TQ=[r for r in rows if r['G']=='TQ']
T64=[r for r in rows if r['group'] in ('T64','T64B')]

print("=== speed x peak STRATIFIED matched diff of MEANS, err_late (2-3.5s build error) ===")
for name,A,B in [("TQall-V282(full)",V282full,TQ), ("TQall-V282(LORO)",V282loro,TQ),
                  ("T64only-V282(full)",V282full,T64), ("T64only-V282(LORO)",V282loro,T64)]:
    c = strat_diff(A,B,'err_late')
    if c is None:
        print(f"  {name:24s} NO MATCHED CELLS"); continue
    print(f"  {name:24s} diff={c['diff']:+.4f} ci={c['ci']} n_matched={c['n']} cells={c['cells']}")
