"""Print the reference tables from s1_results.json."""
import json, sys
R = json.load(open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/s1_results.json'))
C = R['cells']
def cell(g, vb, band, t='all'):
    for c in C:
        if c['group']==g and c['vb']==vb and c['band']==band and c['terc']==t: return c
GR=["V282","V282old","T64","T64B","T5","T4"]; VB=["2-8","8-15","15-22",">22"]
BA=["0.05-0.15","0.15-0.3","0.3-0.6","0.6-1.2","1.2-2.5"]
key = sys.argv[1] if len(sys.argv)>1 else 'G_pL'
terc = sys.argv[2] if len(sys.argv)>2 else 'all'
print("metric", key, "terc", terc)
for vb in VB:
    print("speed", vb)
    for ba in BA:
        row=f"  {ba:10s}"
        for g in GR:
            c=cell(g,vb,ba,terc)
            if c is None: row+=f" {g:>7s}: {'-':>22s}"; continue
            ci=c.get(key+'_ci',[float('nan')]*2)
            row+=f" {g:>7s}:{c[key]:6.3f}[{ci[0]:5.2f},{ci[1]:5.2f}]{c['sec']:5.0f}s"
        print(row)
